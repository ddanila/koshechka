"""Exporter and boundary checks independent of the recorded default run."""
import math
from pathlib import Path
import subprocess
import sys
import unittest
from kitty.core import initial_legs, phase_fit, phase_errors, select, derivative, H
from kitty.experiment import simulate
from kitty.geometry import cat, leaves
from kitty.render import render


class DiagnosticTests(unittest.TestCase):
    def test_exported_fit(self):
        frames, _, _ = simulate(duration=.2, coupling=False)
        legs = initial_legs()
        for frame in frames:
            for leg, state in zip(legs, frame['legs']):
                leg.state = state
            phases, targets, errors = phase_fit(legs)
            self.assertEqual(frame['analysis'], dict(phases=phases, targets=targets, errors=errors))
            self.assertEqual(errors, phase_errors(legs))

    def test_degenerate_cross(self):
        legs = initial_legs()
        for leg in legs:
            leg.state = [0., 0., 1., 0.]
        phases, targets, errors = phase_fit(legs)
        self.assertEqual(targets[0], phases[0])
        self.assertTrue(all(abs(e) <= math.pi for e in errors))

    def test_reversal_coefficients_and_touchdown(self):
        leg = initial_legs()[0]
        leg.state = [.2, .1, -.01, .2]
        select(leg, 1., .5)
        self.assertEqual(leg.event, 'rear reversal')
        self.assertEqual(leg.k[1:3], [1., .2])
        leg.previous_dx = -.01
        leg.state = [-.2, .1, .01, -.2]
        select(leg, 2., .5)
        self.assertEqual(leg.event, 'front reversal')
        end = leg.landing_end
        self.assertEqual(end, 2.1)
        select(leg, end, .5)
        self.assertEqual(leg.state[1:], [0., .5, 0.])
        self.assertEqual(leg.event, 'touchdown')

    def test_guard_and_zero_boundary(self):
        leg = initial_legs()[0]
        leg.branch = 2
        derivative(leg, [leg.length, H, 0., 0.], 0., 0., True, True)
        self.assertEqual(leg.guards, 1)
        leg.state = [.1, .2, 0., 0.]
        leg.previous_dx = 0.
        select(leg, 13., 0.)
        self.assertEqual(leg.branch, 3)  # Existing repaired equality order.
        select(leg, 13., 0., repaired=False)
        self.assertEqual(leg.branch, 4)

    def test_stream_matches_exporter(self):
        root = Path(__file__).resolve().parents[1]
        raw = subprocess.check_output([sys.executable, str(root/'minimal.py'), '2'])
        frames, _, _ = simulate(duration=1/24)
        expected = b''
        for frame in frames:
            tree, _ = cat(frame)
            expected += render(leaves(tree), shift=4.432/2-frame['distance'], span=9.).tobytes()
        self.assertEqual(raw, expected)
