"""Pre-refactor numerical baselines. Recording is explicit, never automatic."""
import hashlib
import json
import math
import os
from pathlib import Path
import unittest

from kitty.core import initial_legs, step, speed, solve_leg
from kitty.geometry import cat, leaves
from kitty.render import render

FIXTURE = Path(__file__).with_name('fixtures') / 'core-72de796.json'
SCENARIOS = {'default': {}, 'cruise': {'stop': False}, 'uncoupled': {'coupling': False}}


def capture(options):
    legs = initial_legs()
    digest = hashlib.sha256()
    samples, events, poses, pixels = [], [], [], []
    t, distance = 0., 0.
    for frame in range(385):
        target = frame / 24
        while t < target - 1e-12:
            dt = min(.001, target - t)
            v0 = speed(t, options.get('stop', True))[0]
            step(legs, t, dt, **options)
            distance += dt * (v0 + speed(t + dt, options.get('stop', True))[0]) / 2
            state = [[leg.state, leg.k, leg.previous_dx, leg.branch,
                      leg.landing_end, leg.event, leg.guards] for leg in legs]
            digest.update(json.dumps(state, separators=(',', ':')).encode())
            events.extend([t, leg.name, leg.event] for leg in legs if leg.event)
            t += dt
        if frame % 6 == 0:
            samples.append(json.loads(json.dumps([target, distance, state if frame else
                            [[leg.state, leg.k, leg.previous_dx, leg.branch,
                              leg.landing_end, leg.event, leg.guards] for leg in legs]])))
        if frame in (0, 24, 96, 192, 288, 384):
            tree, _ = cat({'t': target, 'legs': [leg.state for leg in legs]})
            solids = list(leaves(tree))
            poses.append(solids)
            pixels.append(hashlib.sha256(render(solids).tobytes()).hexdigest())
    return {'samples': samples, 'events': events, 'poses': poses,
            'all_steps_sha256': digest.hexdigest(), 'raster_sha256': pixels}


class RegressionTests(unittest.TestCase):
    def compare(self, actual, expected):
        if isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for a, b in zip(actual, expected):
                self.compare(a, b)
        elif isinstance(expected, float):
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10),
                            (actual, expected))
        else:
            self.assertEqual(actual, expected)

    def test_pre_refactor_runs(self):
        baseline = json.loads(FIXTURE.read_text())
        for name, options in SCENARIOS.items():
            with self.subTest(scenario=name):
                actual = capture(options)
                for key in ('samples', 'events', 'poses'):
                    self.compare(actual[key], baseline[name][key])
                if os.environ.get('KOSHECHKA_STRICT_GOLDEN') == '1':
                    for key in ('all_steps_sha256', 'raster_sha256'):
                        self.assertEqual(actual[key], baseline[name][key])

    def test_literal_failure_is_preserved(self):
        legs = initial_legs()
        with self.assertRaisesRegex(ArithmeticError, 'before K2 was initialized'):
            for i in range(4000):
                step(legs, i*.001, .001, repaired=False)

    def test_unreachable_leg_is_rejected(self):
        with self.assertRaises(ValueError):
            solve_leg(2., 0., True)


if __name__ == '__main__':
    import sys
    if '--record' in sys.argv:
        if FIXTURE.exists():
            raise SystemExit('Refusing to overwrite the historical baseline')
        FIXTURE.write_text(json.dumps({name: capture(opts) for name, opts in SCENARIOS.items()},
                                     separators=(',', ':')) + '\n')
        print('Recorded baseline from the unmodified core')
    else:
        unittest.main()
