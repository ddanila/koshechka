"""Cross-language parity and bounded raster differences; no original media."""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw, ImageChops, ImageFilter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reconstruction'))
from kitty.presets import model_for
from kitty.core import initial_legs, step, speed, ORDER
from kitty.geometry import cat, leaves
from kitty.render import projected


def check(binary,preset):
    def run(*args):return subprocess.check_output([str(binary),'--preset',preset,*args])
    results={}
    for scenario,options,args in [('default',{},[]),('cruise',{'stop':False},['--cruise']),('uncoupled',{'coupling':False},['--no-coupling'])]:
        rows=list(csv.DictReader(io.StringIO(run('--trace',*args).decode())))
        vertices=list(csv.DictReader(io.StringIO(run('--vertices',*args).decode())))
        events=list(csv.DictReader(io.StringIO(run('--events',*args).decode())))
        legs=initial_legs();t=distance=0.;actual_events=[];state_error=vertex_error=0.
        for frame in range(385):
            target=frame/24
            while t<target-1e-12:
                dt=min(.001,target-t);v=speed(t,options.get('stop',True))[0]
                step(legs,t,dt,**options)
                actual_events.extend((t,i,('rear reversal','front reversal','touchdown').index(l.event)+1) for i,l in enumerate(legs) if l.event)
                distance+=dt*(v+speed(t+dt,options.get('stop',True))[0])/2;t+=dt
            for i,leg in enumerate(legs):
                row=rows[frame*4+i]
                assert int(row['branch'])==leg.branch,(scenario,frame,i,'branch')
                expected=leg.state+leg.k[1:]+[distance]
                values=[float(row[k]) for k in ('x','y','dx','dy','k1','k2','k3','k4','k5','k6','k7','distance')]
                state_error=max(state_error,max(abs(a-b) for a,b in zip(values,expected)))
            tree,_=cat({'t':target,'legs':[l.state for l in legs]},model_for(preset))
            for j,(_,solid) in enumerate(leaves(tree)):
                for k,v in enumerate(solid):
                    row=vertices[frame*29*8+j*8+k]
                    vertex_error=max(vertex_error,max(abs(float(row[axis])-x) for axis,x in zip(('x','y','z'),v)))
        assert state_error<1e-9,(scenario,'state',state_error)
        assert vertex_error<1e-8,(scenario,'vertices',vertex_error)
        assert len(events)==len(actual_events)
        event_error=0.
        for row,(t,i,event) in zip(events,actual_events):
            assert (int(row['leg']),int(row['event']))==(i,event)
            event_error=max(event_error,abs(float(row['t'])-t))
        assert event_error<=.001
        results[scenario]=dict(max_state_error=state_error,max_vertex_error=vertex_error,max_event_time_error=event_error,events=len(events))
    # Pixel centers versus Pillow's integer polygon scan conversion. Differences
    # must lie within one pixel (Chebyshev distance) of a primitive boundary.
    raw=run('--mask','--duration','1')
    header=b'P4\n160 100\n';stride=len(header)+2000
    assert len(raw)==25*stride
    legs=initial_legs();t=0.;max_diff=0
    for frame in range(25):
        target=frame/24
        while t<target-1e-12:
            dt=min(.001,target-t);step(legs,t,dt);t+=dt
        tree,_=cat(dict(t=target,legs=[l.state for l in legs]),model_for(preset))
        mask=Image.new('1',(160,100));edge=Image.new('1',(160,100))
        draw,outline=ImageDraw.Draw(mask),ImageDraw.Draw(edge)
        for _,points in projected(leaves(tree),angle=model_for(preset)['view_yaw_degrees'],width=160,height=100):
            draw.polygon(points,fill=1);outline.line(points+[points[0]],fill=1,width=1)
        # PBM 1 means black; our occupancy bits deliberately use that encoding.
        native=ImageChops.invert(Image.open(io.BytesIO(raw[frame*stride:(frame+1)*stride])).convert('L')).convert('1')
        difference=ImageChops.logical_xor(mask,native)
        allowed=edge.convert('L').filter(ImageFilter.MaxFilter(3)).convert('1')
        assert not ImageChops.logical_and(difference,ImageChops.invert(allowed.convert('L')).convert('1')).getbbox(),('raster outside edge band',frame)
        max_diff=max(max_diff,sum(bool(v) for v in difference.getdata()))
    results['raster']={'max_different_cells':max_diff,'cells':16000,'allowed':'one-cell primitive-boundary band'}
    # Validate output framing, polarity and malformed CLI input.
    paper=run('--duration','.01');ink=run('--duration','.01','--ink')
    assert paper.startswith(b'P4\n960 600\n') and len(paper)==len(ink)==72011
    assert paper!=ink
    for args in [('--dt','0'),('--fps','1.5'),('--duration','nan'),('--preset','missing')]:
        assert subprocess.run([str(binary),'--preset',preset,*args],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,default=Path('native/build/kitty'))
    args=parser.parse_args()
    print(json.dumps({preset:check(args.binary.resolve(),preset) for preset in ('baseline','fitted')},indent=2))
