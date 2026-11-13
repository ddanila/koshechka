#!/usr/bin/env python3
"""Generate a self-contained trajectory, movie, preview and diagnostic traces."""
import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from kitty.experiment import simulate
from kitty.geometry import cat,leaves,DEFAULT_MODEL
from kitty.render import render

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration',type=float,default=16.)
    parser.add_argument('--fps',type=int,default=24)
    parser.add_argument('--dt',type=float,default=.001)
    parser.add_argument('--cruise',action='store_true',help='Do not decelerate')
    parser.add_argument('--literal',action='store_true',help='Experimental printed branches, without numerical repairs; may fail')
    parser.add_argument('--no-coupling',action='store_true')
    parser.add_argument('--no-head-turn',action='store_true')
    parser.add_argument('--no-video',action='store_true')
    parser.add_argument('--model',type=Path,help='JSON model parameters, replacing the default model')
    parser.add_argument('--output',type=Path,default=ROOT/'output')
    args = parser.parse_args()
    if args.duration<=0 or args.duration>120 or args.fps<=0 or args.fps>120 or args.dt<=0 or args.dt>.02:
        parser.error('Use 0 < duration <= 120, 1 <= fps <= 120 and 0 < dt <= .02')
    model = json.loads(args.model.read_text()) if args.model else DEFAULT_MODEL
    if model['shoulder_height'] != .75:
        parser.error('shoulder_height must match the published controller constant 0.75')
    if len(model['leg_lengths']) != 3 or min(model['leg_lengths']) <= 0 or sum(model['leg_lengths']) <= .75:
        parser.error('Use three positive leg lengths with a total greater than shoulder height')
    out = args.output;out.mkdir(parents=True,exist_ok=True)
    frames,traces,diagnostics = simulate(args.duration,args.fps,args.dt,not args.cruise,
                                       not args.literal,not args.no_coupling,sum(model['leg_lengths']))
    animation=[]; max_error=0.
    for frame in frames:
        tree,error = cat(frame,model,not args.no_head_turn)
        max_error=max(max_error,error)
        solids=list(leaves(tree))
        animation.append({**frame,'solids':[[name,[[round(c,6) for c in v] for v in vertices]] for name,vertices in solids]})
    payload={'fps':args.fps,'dt':args.dt,'duration':args.duration,'model':model,
             'repaired':not args.literal,'coupling':not args.no_coupling,'frames':animation}
    (out/'animation.js').write_text('window.KITTY = '+json.dumps(payload,separators=(',',':'))+';\n')
    (out/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    with (out/'trajectory.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(traces[0]),lineterminator='\n');writer.writeheader();writer.writerows(traces)
    diagnostics.update(max_ik_endpoint_error=max_error,frames=len(frames),dt=args.dt,fps=args.fps,
                       repaired=not args.literal,coupling=not args.no_coupling,
                       branches_observed=sorted(set(r['branch'] for r in traces)))
    (out/'diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
    samples=[]
    for index in [min(len(animation)-1,round(t*args.fps)) for t in (0,.5,1,1.5,2,3,6,9,12,16)]:
        frame=animation[index]
        picture=render(frame['solids'],angle=model['view_yaw_degrees'])
        thumb=picture.resize((384,240))
        draw=ImageDraw.Draw(thumb);draw.rectangle((0,0,85,19),fill='white');draw.text((5,4),f"t = {frame['t']:.2f} s",fill='black')
        samples.append(thumb)
    sheet=Image.new('RGB',(384*2,240*5),'white')
    for i,im in enumerate(samples):sheet.paste(im,(i%2*384,i//2*240))
    sheet.save(out/'contact-sheet.jpg',quality=92)
    render(animation[24 if len(animation)>24 else 0]['solids'],angle=model['view_yaw_degrees']).save(out/'preview.png')
    # A compact animated preview; the full motion lives in MP4 and the viewer.
    gif=[render(f['solids'],angle=model['view_yaw_degrees']).resize((480,300)) for f in animation[::max(1,args.fps//8)]]
    gif[0].save(out/'kitty.gif',save_all=True,append_images=gif[1:],duration=1000*max(1,args.fps//8)/args.fps,loop=0)
    if not args.no_video:
        ffmpeg=shutil.which('ffmpeg')
        if not ffmpeg:raise SystemExit('ffmpeg missing: install it or pass --no-video; other outputs saved')
        for tracking,filename in ((True,'kitty.mp4'),(False,'kitty-travel.mp4')):
            cmd=[ffmpeg,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','960x600',
                 '-r',str(args.fps),'-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',
                 '-movflags','+faststart',str(out/filename)]
            with subprocess.Popen(cmd,stdin=subprocess.PIPE) as proc:
                for f in animation:
                    shift=0. if tracking else animation[-1]['distance']/2-f['distance']
                    proc.stdin.write(render(f['solids'],angle=model['view_yaw_degrees'],
                                            shift=shift,span=5.2 if tracking else 9.).tobytes())
                proc.stdin.close()
                if proc.wait()!=0:raise RuntimeError('ffmpeg failed')
    print(json.dumps({'output':str(out),'frames':len(frames),'max_ik_error':max_error,
                      'guard_calls':diagnostics['singularity_guard_calls']},indent=2))


if __name__=='__main__':main()
