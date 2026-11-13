"""Numerical/structural checks, not a claim of historical equivalence."""
import math
import unittest
from kitty.experiment import simulate
from kitty.core import initial_legs,phase_errors,derivative,H
from kitty.geometry import Node,solid,leaves,solve_leg,paper_rotation,dot,cross


class ReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames,cls.trace,cls.diagnostics=simulate()

    def test_stance_is_stationary_in_world(self):
        errors=[]
        for a,b in zip(self.frames,self.frames[1:]):
            for i in range(4):
                if a['branches'][i]==b['branches'][i]==1 and a['legs'][i][1]==b['legs'][i][1]==0:
                    errors.append(abs((b['legs'][i][0]-b['distance'])-(a['legs'][i][0]-a['distance'])))
        self.assertGreater(len(errors),500)
        self.assertLess(max(errors),1e-7)

    def test_walk_stops_without_singularities(self):
        self.assertEqual(self.diagnostics['singularity_guard_calls'],0)
        for leg in self.frames[-1]['legs']:
            self.assertEqual(leg[1:], [0.,0.,0.])
        self.assertLess(self.diagnostics['max_height'],.30)
        self.assertGreaterEqual(self.diagnostics['min_sampled_height'],-1e-6)
        for events in self.diagnostics['events'].values():
            self.assertGreaterEqual(sum(kind=='rear reversal' for _,kind in events),2)

    def test_half_step_convergence(self):
        fine,_,_=simulate(dt=.0005)
        error=max(abs(a-b) for coarse,small in zip(self.frames,fine)
                  for leg1,leg2 in zip(coarse['legs'],small['legs'])
                  for a,b in zip(leg1[:2],leg2[:2]))
        self.assertLess(error,.015)  # Hybrid event timing is only first-order.

    def test_all_endpoints_and_joint_constraints(self):
        for frame in self.frames[::5]:
            for i,state in enumerate(frame['legs']):
                points,info=solve_leg(state[0],state[1],i%2==1)
                lengths=[math.dist(a,b) for a,b in zip(points,points[1:])]
                for actual,wanted in zip(lengths,(.40,.36,.29,.18)):
                    self.assertAlmostEqual(actual,wanted,places=10)
                self.assertLess(math.dist(points[3],state[:2]),1e-10)
                angles=[math.atan2(b[1]-a[1],b[0]-a[0]) for a,b in zip(points,points[1:])]
                turn=lambda a:math.atan2(math.sin(a),math.cos(a))
                beta=turn(angles[1]-angles[0]);gamma=turn(angles[2]-angles[1])
                self.assertAlmostEqual(beta,(.8 if i%2 else -1.2)*gamma,places=9)

    def test_front_elbow_bends_back(self):
        # For a foot directly below the shoulder, +x is toward the tail.
        # Both mirrored IK roots satisfy beta=c*gamma; only this root matches
        # the computed film's backward elbow. The old positive root fails.
        for y in (0., .1, .22):
            points, _ = solve_leg(0., y, True)
            self.assertGreater(points[1][0], 0.)
            self.assertGreater(points[2][0], 0.)

    def test_compact_initial_values_match_source_tables(self):
        import csv
        from pathlib import Path
        from fractions import Fraction
        source = Path(__file__).resolve().parents[2]/'article/data'
        with (source/'initial-state.csv').open() as f:
            states = {r['leg']: r for r in csv.DictReader(f)}
        with (source/'initial-coefficients.csv').open() as f:
            coefficients = {r['leg']: r for r in csv.DictReader(f)}
        for leg in initial_legs():
            self.assertEqual(leg.state, [float(states[leg.name][k]) for k in ('x','y','dx','dy')])
            self.assertEqual(leg.previous_dx, float(states[leg.name]['dx_previous']))
            self.assertEqual(leg.k[1:], [float(Fraction(coefficients[leg.name]['K'+str(i)])) for i in range(1,8)])

    def test_paper_frames_are_right_handed_even_at_poles(self):
        for psi in (0.,.2,math.pi/2,2.,math.pi):
            for omega in (0.,.5,2.):
                r=paper_rotation(psi,.8,omega)
                for i in range(3):
                    for j in range(3):self.assertAlmostEqual(dot(r[i],r[j]),float(i==j),places=12)
                self.assertAlmostEqual(dot(r[0],cross(r[1],r[2])),1.,places=12)

    def test_parent_scale_and_translation(self):
        leaf=solid('test',(0.,0.,0.),(1.,0.,0.),.2,.4)
        group=Node('parent',(2.,3.,4.),scale=2.,children=[leaf])
        vertices=list(leaves(group))[0][1]
        self.assertEqual(min(p[0] for p in vertices),2.)
        self.assertEqual(max(p[0] for p in vertices),4.)
        self.assertAlmostEqual(max(p[2] for p in vertices),4.4)

    def test_landing_cubic_boundary_conditions(self):
        # Arbitrary initial downward speed and height, not values from the model.
        y,dy,T=.23,-.17,.3
        a=(dy*T+2*y)/T**3;b=-(2*dy*T+3*y)/T**2
        self.assertAlmostEqual(a*T**3+b*T**2+dy*T+y,0.,places=12)
        self.assertAlmostEqual(3*a*T**2+2*b*T+dy,0.,places=12)

    def test_phase_fit_cross_and_wrap(self):
        legs=initial_legs();base=.01
        for i,leg in enumerate(legs):
            phase=(base-i*math.pi/2)%(2*math.pi)
            a=math.sqrt(leg.length**2-H**2)
            if phase<=math.pi:
                leg.state=[(phase-math.pi/2)*2*a/math.pi,0.,1.,0.]
            else:leg.state=[(3*math.pi/2-phase)*2*a/math.pi,.1,-1.,0.]
        self.assertLess(max(abs(x) for x in phase_errors(legs)),1e-12)

    def test_published_stop_sign_remains_selectable(self):
        leg=initial_legs()[0];leg.branch=4;leg.k[3]=2.
        self.assertEqual(derivative(leg,[0,.2,0,-.1],13,0,True,False)[3],-2.)
        self.assertEqual(derivative(leg,[0,.2,0,-.1],13,0,True,True)[3],2.)


if __name__=='__main__':unittest.main()
