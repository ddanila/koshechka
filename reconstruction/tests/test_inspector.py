"""Event alignment, independent presets and experimental fit properties."""
import importlib.util
import math
from pathlib import Path
import unittest
from kitty.experiment import simulate
from kitty.presets import model_for
from kitty.core import initial_legs, step

spec=importlib.util.spec_from_file_location('phase_experiment',Path(__file__).resolve().parents[2]/'research/experiments/phase.py')
phase=importlib.util.module_from_spec(spec);spec.loader.exec_module(phase)

class InspectorTests(unittest.TestCase):
    def test_event_frames_and_kinds(self):
        frames,_,diagnostics=simulate(duration=4)
        records=diagnostics['event_records']
        self.assertEqual({e['kind'] for e in records},{'lift-off','rear reversal','front reversal','touchdown'})
        for event in records:
            i=event['frame']
            self.assertGreaterEqual(frames[i]['t']+1e-10,event['t'])
            if i:self.assertLess(frames[i-1]['t'],event['t']+1e-10)

    def test_presets_are_independent(self):
        a=model_for();a['leg_lengths'][0]=10
        self.assertEqual(model_for()['leg_lengths'],[.4,.36,.29])

    def test_experimental_chord_matches_controller(self):
        a,b=initial_legs(),initial_legs()
        for i in range(4000):
            step(a,i*.001,.001)
            phase.advance(b,i*.001,.001,'chord')
        self.assertEqual([l.state for l in a],[l.state for l in b])

    def test_cross_objectives(self):
        for phases in ([.001-i*math.pi/2 for i in range(4)], [0.]*4, [.1,2.,4.,5.]):
            for method in ('chord','angular','unrestricted'):
                errors,assignment=phase.fit(phases,method)
                self.assertEqual(sorted(assignment),sorted(phase.OFFSETS))
                self.assertTrue(all(abs(e)<=math.pi for e in errors))
                objective=lambda base:sum(phase.wrap(p-base-o)**2 if method=='angular' else 2-2*math.cos(p-base-o) for p,o in zip(phases,assignment))
                actual=sum(e*e if method=='angular' else 2-2*math.cos(e) for e in errors)
                self.assertLessEqual(actual,min(objective(i*2*math.pi/2000) for i in range(2000))+1e-10)

    def test_fitted_pose_snapshot(self):
        import hashlib
        import json
        import os
        from kitty.geometry import cat, leaves
        from kitty.render import render
        baseline=json.loads((Path(__file__).with_name('fixtures')/'fitted-v1.json').read_text())
        model=model_for('fitted')
        self.assertEqual(model,baseline['model'])
        frames,_,_=simulate()
        for sample in baseline['samples']:
            tree,_=cat(frames[sample['index']],model)
            solids=list(leaves(tree))
            for (name,vertices),(expected_name,expected_vertices) in zip(solids,sample['solids']):
                self.assertEqual(name,expected_name)
                for point,expected in zip(vertices,expected_vertices):
                    for a,b in zip(point,expected):self.assertAlmostEqual(a,b,places=10)
            if os.environ.get('KOSHECHKA_STRICT_GOLDEN')=='1':
                self.assertEqual(hashlib.sha256(render(solids,angle=model['view_yaw_degrees']).tobytes()).hexdigest(),sample['raster_sha256'])
