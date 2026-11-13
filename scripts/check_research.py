"""Synthetic registration checks: no access to copyrighted research media."""
import importlib.util
from pathlib import Path
from copy import deepcopy
import numpy as np
spec=importlib.util.spec_from_file_location('fidelity',Path(__file__).resolve().parents[1]/'research/experiments/fidelity.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
m=f.model([1.,1.,.70,.71,18.]);points=f.landmarks(m)
data={'uncertainty_pixels':[12,12,10,14,14],'frames':[]}
for shot in (0,1):
    for local in range(4):
        coordinates=f.project(points,m,[200.,540.+shot*40,500.,1.],local,1.)
        data['frames'].append(dict(t=[41,66][shot]+local,shot=shot,split='calibration' if local<2 else 'held_out',points=coordinates.tolist()))
result=f.fit(data,1.,False)
assert result['normalized_landmark_error']['held_out']<1e-9,result
changed=deepcopy(data)
for frame in changed['frames']:
    if frame['split']=='held_out':frame['points']=(np.array(frame['points'])+1000).tolist()
assert f.fit(changed,1.,False)['parameters']==result['parameters'],'Held-out leakage'
print('Synthetic registration and held-out isolation passed.')
