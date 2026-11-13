"""Fit estimated shape to reviewed landmarks; private media stay outside the repo.

The deliberately conservative promotion gate includes held-out silhouette scores.
Missing or unreliable masks prevent promotion; landmarks alone cannot pass it.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
from scipy.optimize import least_squares
from scipy.ndimage import binary_closing, binary_fill_holes, label
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'reconstruction'))
from kitty.geometry import BASELINE_MODEL, cat, leaves, hull

ROOT=Path(__file__).resolve().parents[2]


def model(parameters):
    """Fit only identifiable upper-body quantities; no invented leg labels."""
    m=deepcopy(BASELINE_MODEL)
    length,height,tail_y,tail_z,angle=parameters
    for key in ('body_start','body_end'):
        m[key][1]*=length
    m['body_height']=[v*height for v in m['body_height']]
    m['tail_start'][1]*=length
    m['tail_end'][1]=m['tail_start'][1]+tail_y
    m['tail_end'][2]=m['tail_start'][2]+tail_z
    m['view_yaw_degrees']=angle
    return m


def landmarks(m):
    # These landmarks are independent of leg phase. Geometry is evaluated with
    # the published initial states and an unturned head.
    from kitty.core import initial_legs
    tree,_=cat(dict(t=0.,legs=[l.state for l in initial_legs()]),m,False)
    solids={name:np.array(v) for name,v in leaves(tree)}
    return np.array([solids['body'][[1,2]].mean(axis=0),solids['body'][[5,6]].mean(axis=0),
                     solids['tail'][4:].mean(axis=0),
                     np.concatenate([solids['ear_-1'][4:],solids['ear_1'][4:]]).mean(axis=0),
                     solids['muzzle'][4:].mean(axis=0)])


def project(points,m,registration,time,aspect):
    scale,tx,ty,rate=registration
    angle=math.radians(m['view_yaw_degrees'])
    xy=np.column_stack([np.sin(angle)*points[:,0]+np.cos(angle)*points[:,1],-points[:,2]])
    xy[:,0]-=.554*rate*time
    xy=xy*scale+[tx,ty]
    # Registration is isotropic in the hypothesized display, not file pixels.
    xy[:,0]/=aspect
    return xy


def fit(data,aspect,fitted):
    initial=[1.,1.,.70,.71,18.,200.,540.,500.,1.,200.,580.,500.,1.]
    low=[.75,.6,.25,.4,-20.,80.,250.,350.,.2,80.,250.,350.,.2]
    high=[1.3,1.5,1.,1.2,50.,350.,850.,700.,1.6,350.,850.,700.,1.6]
    train=[f for f in data['frames'] if f['split']=='calibration']
    uncertainty=np.array(data['uncertainty_pixels'])[:,None]
    def residual(x):
        full=x if fitted else initial[:5]+list(x)
        m=model(full[:5]);points=landmarks(m);result=[]
        for f in train:
            shot=f['shot'];reg=full[5+shot*4:9+shot*4]
            predicted=project(points,m,reg,f['t']-[41,66][shot],aspect)
            result.extend(((predicted-f['points'])/uncertainty).ravel())
        return result
    start=initial if fitted else initial[5:]
    result=least_squares(residual,start,bounds=(low if fitted else low[5:],high if fitted else high[5:]),
                         max_nfev=200,xtol=1e-10,ftol=1e-10,gtol=1e-10)
    parameters=result.x.tolist() if fitted else initial[:5]+result.x.tolist()
    m=model(parameters[:5]);points=landmarks(m);scores={}
    for split in ('calibration','held_out'):
        errors=[]
        for f in data['frames']:
            if f['split']!=split:continue
            reg=parameters[5+f['shot']*4:9+f['shot']*4]
            predicted=project(points,m,reg,f['t']-[41,66][f['shot']],aspect)
            # Normalize by observed back length, not a fitted scale.
            size=np.linalg.norm(np.array(f['points'][0])-f['points'][1])
            errors.extend(np.linalg.norm(predicted-f['points'],axis=1)/size)
        scores[split]=float(np.mean(errors))
    return dict(parameters=parameters,model=m,normalized_landmark_error=scores,
                solver_success=bool(result.success),evaluations=result.nfev)


def reference_mask(f,archive,threshold=9):
    im=Image.open(archive/'media/frames-1fps'/f"frame-{f['t']+1:03}.png").convert('L')
    smooth=np.asarray(im.filter(ImageFilter.GaussianBlur(4)),dtype=float)
    background=np.asarray(im.filter(ImageFilter.GaussianBlur(45)),dtype=float)
    signal=(background-smooth) if f['shot']==0 else (smooth-background)
    mask=signal>threshold
    # Restrict extraction to the observed subject; film-frame borders otherwise
    # merge with the white cat. ROI uses annotations, never model predictions.
    points=np.array(f['points'])
    x0=max(20,int(points[:,0].min()-100));x1=min(700,int(points[:,0].max()+65))
    y0=max(20,int(points[:,1].min()-30))
    mask[:y0]=False;mask[550:]=False;mask[:,:x0]=False;mask[:,x1:]=False
    mask=binary_fill_holes(binary_closing(mask,iterations=5))
    if not mask.any():return mask
    components,_=label(mask)
    seed=np.mean(points[:2],axis=0)+[0,40]
    component=components[int(seed[1]),int(seed[0])]
    if component==0:
        counts=np.bincount(components.ravel());counts[0]=0;component=counts.argmax()
    return components==component


def silhouette_scores(data,archive,fit_result,aspect):
    from kitty.experiment import simulate
    frames,_,_=simulate(duration=10,fps=48,stop=False)
    m=fit_result['model'];params=fit_result['parameters']
    references={f['t']:reference_mask(f,archive) for f in data['frames']}
    def prediction(f,offset):
        shot=f['shot'];local=f['t']-[41,66][shot];reg=params[5+shot*4:9+shot*4]
        at=offset+reg[3]*local
        frame=frames[min(len(frames)-1,max(0,round(at*48)))]
        tree,_=cat(frame,m,False);mask=Image.new('1',(720,576));draw=ImageDraw.Draw(mask)
        for _,vertices in leaves(tree):
            points=project(np.array(vertices),m,reg,local,aspect)
            draw.polygon(hull([tuple(p) for p in points]),fill=1)
        return np.asarray(mask,dtype=bool)
    def iou(a,b):return float(np.logical_and(a,b).sum()/max(1,np.logical_or(a,b).sum()))
    offsets=[]
    for shot in (0,1):
        train=[f for f in data['frames'] if f['shot']==shot and f['split']=='calibration']
        offsets.append(max(np.linspace(0,4,81),key=lambda offset:sum(iou(prediction(f,offset),references[f['t']]) for f in train)))
    records=[]
    for f in data['frames']:
        predicted=prediction(f,offsets[f['shot']])
        records.append(dict(t=f['t'],split=f['split'],iou=iou(predicted,references[f['t']]),
                            threshold_sensitivity=[iou(predicted,reference_mask(f,archive,threshold)) for threshold in (6,12)]))
    return dict(phase_offsets=offsets,frames=records,
                held_out_mean=float(np.mean([r['iou'] for r in records if r['split']=='held_out'])),
                interpretation='Approximate printer-envelope overlap, not exact film pixels; thin whiskers and blurred white boundaries are uncertain.')


def media_review(data,archive):
    rows=[]
    for f in data['frames']:
        path=archive/'media/frames-1fps'/f"frame-{f['t']+1:03}.png"
        rows.append(dict(t=f['t'],sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return dict(frames=rows,exact_duplicate_count=len(rows)-len({r['sha256'] for r in rows}),
                reuse_warning='Different hashes do not rule out rephotographed, resized or polarity-inverted repetitions.',
                mask_review='Dark silhouettes mostly coherent; white boundaries and thin whiskers are less reliable. Threshold sensitivity is reported.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();data=json.loads((ROOT/'research/landmarks.json').read_text())
    results={label:{name:fit(data,aspect,name=='fitted') for name in ('baseline','fitted')}
             for label,aspect in [('square_pixels',1.),('display_4_3',16/15)]}
    for label,result in results.items():
        aspect=1. if label=='square_pixels' else 16/15
        for name in ('baseline','fitted'):
            result[name]['silhouette']=silhouette_scores(data,args.archive,result[name],aspect)
        result['landmark_improvement']=1-result['fitted']['normalized_landmark_error']['held_out']/result['baseline']['normalized_landmark_error']['held_out']
    checks={}
    for label,result in results.items():
        baseline,candidate=result['baseline'],result['fitted']
        checks[label]=dict(landmarks=result['landmark_improvement']>=.10,
                          silhouette=candidate['silhouette']['held_out_mean']>=baseline['silhouette']['held_out_mean'],
                          threshold_sensitivity=all(
                              sum(f['threshold_sensitivity'][i] for f in candidate['silhouette']['frames'] if f['split']=='held_out') >=
                              sum(f['threshold_sensitivity'][i] for f in baseline['silhouette']['frames'] if f['split']=='held_out') for i in (0,1)))
    from kitty.experiment import simulate
    candidate=results['square_pixels']['fitted']['model']
    frames,_,_=simulate()
    max_error=max(cat(frame,candidate)[1] for frame in frames)
    geometry_ok=max_error<1e-8 and candidate['leg_lengths']==BASELINE_MODEL['leg_lengths']
    accepted=geometry_ok and all(all(check.values()) for check in checks.values())
    report=dict(results=results,media_review=media_review(data,args.archive),
                promotion=dict(accepted=accepted,checks=checks,max_ik_error=max_error,geometry_and_unchanged_contact=geometry_ok,
                               preset='fitted' if accepted else 'baseline',
                               reason='Relative held-out improvement only: absolute registration error remains large, and original-film contact timing is not identified.'),
                limitations=['Upper-body landmarks do not identify leg-length ratios, shoulder placement, gait phase or contact timing.',
                             'Temporal blocks within possibly repeated shots do not establish independent generalization.',
                             'One constant image velocity per shot is an estimated registration, not the recovered speed schedule.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
