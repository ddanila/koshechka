"""Alternative readings of the cross fit; never imported by production code."""
import itertools
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'reconstruction'))
from kitty.core import initial_legs, phase_fit, select, derivative, speed, step

TAU = 2*math.pi
OFFSETS = tuple(-i*math.pi/2 for i in range(4))


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def fit(phases, method='chord'):
    """Return signed errors and assignment, with deterministic tie breaking."""
    best = None
    assignments = itertools.permutations(OFFSETS) if method == 'unrestricted' else [OFFSETS]
    for offsets in assignments:
        adjusted = [p-o for p, o in zip(phases, offsets)]
        if method == 'angular':
            # Each choice of circular cut defines a quadratic interval. Its mean
            # is a candidate; evaluating wrapped cost handles boundary minima.
            angles = sorted(a % TAU for a in adjusted)
            bases = [sum(angles[j:]+[a+TAU for a in angles[:j]])/4 for j in range(4)]
        else:
            s = sum(math.sin(a) for a in adjusted)
            c = sum(math.cos(a) for a in adjusted)
            bases = [math.atan2(s,c) if math.hypot(s,c)>1e-12 else phases[0]]
        for base in bases:
            errors = [wrap(p-base-o) for p,o in zip(phases,offsets)]
            cost = sum(e*e if method == 'angular' else 2-2*math.cos(e) for e in errors)
            if best is None or cost < best[0]-1e-14:
                best = cost, errors, offsets
    return best[1:]


def advance(legs, t, dt, method, stop=True, coupling=True):
    """Experimental RK4, checked against production step for the chord method."""
    for leg in legs:
        select(leg,t,speed(t,stop)[0])
    errors, _ = fit(phase_fit(legs)[0],method)
    for leg,error in zip(legs,errors):
        if not coupling: error=0.
        state=leg.state[:]
        a=derivative(leg,state,t,error,stop,True)
        b=derivative(leg,[x+dt*d/2 for x,d in zip(state,a)],t+dt/2,error,stop,True)
        c=derivative(leg,[x+dt*d/2 for x,d in zip(state,b)],t+dt/2,error,stop,True)
        d=derivative(leg,[x+dt*z for x,z in zip(state,c)],t+dt,error,stop,True)
        leg.previous_dx=state[2]
        leg.state=[x+dt*(aa+2*bb+2*cc+dd)/6 for x,aa,bb,cc,dd in zip(state,a,b,c,d)]
        if not all(math.isfinite(x) and abs(x)<1e5 for x in leg.state):
            raise ArithmeticError('Unstable experimental trajectory')


def study():
    report={}
    for scenario,stop,coupling in [('default',True,True),('cruise',False,True),('uncoupled',True,False)]:
        for method in ('chord','angular','unrestricted'):
            legs, reference=initial_legs(),initial_legs()
            events=[]; max_delta=0.; max_jump=0.; assignment_changes=0
            chord_cost=angular_cost=0.; previous=None; previous_assignment=None
            result={'events':events}
            try:
                for i in range(16000):
                    t=i*.001
                    advance(legs,t,.001,method,stop,coupling)
                    step(reference,t,.001,stop=stop,coupling=coupling)
                    events.extend([t,l.name,l.event] for l in legs if l.event)
                    max_delta=max(max_delta,max(abs(a-b) for l,r in zip(legs,reference) for a,b in zip(l.state,r.state)))
                    errors,assignment=fit(phase_fit(legs)[0],method)
                    # Quotient out global quarter-turn relabeling of the cross.
                    assignment=tuple(round((o-assignment[0])/(math.pi/2))%4 for o in assignment)
                    chord_cost+=sum(2-2*math.cos(e) for e in errors)
                    angular_cost+=sum(e*e for e in errors)
                    if previous:
                        max_jump=max(max_jump,max(abs(wrap(a-b)) for a,b in zip(errors,previous)))
                        assignment_changes+=assignment!=previous_assignment
                    previous,previous_assignment=errors,assignment
                result.update(max_state_difference=max_delta,max_error_jump_radians=max_jump,
                              mean_chord_cost=chord_cost/16000,mean_angular_cost=angular_cost/16000,
                              assignment_changes=assignment_changes,final_states=[l.state for l in legs])
            except (ArithmeticError,ValueError,ZeroDivisionError) as exc:
                result.update(failure=str(exc),failure_time=t)
            report[scenario+'/'+method]=result
    report['edge_cases']={name:{method:fit(phases,method) for method in ('chord','angular','unrestricted')}
                          for name,phases in [('wrap',[.001-i*math.pi/2 for i in range(4)]),('degenerate',[0.]*4)]}
    return report


if __name__=='__main__':
    print(json.dumps(study(),indent=2))
