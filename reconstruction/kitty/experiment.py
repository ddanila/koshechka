"""Optional history/diagnostic collection; not part of the simulation core."""
import math
from .core import initial_legs, step, speed, phase_fit


def simulate(duration=16., fps=24, dt=.001, stop=True, repaired=True, coupling=True, length=1.05):
    legs = initial_legs(length)
    frames, traces = [], []
    events = {leg.name: [] for leg in legs}
    event_records = []
    t, distance = 0., 0.
    for frame in range(round(duration*fps)+1):
        target = frame/fps
        while t < target-1e-12:
            delta = min(dt, target-t)
            v0, _ = speed(t, stop)
            heights = [leg.state[1] for leg in legs]
            step(legs, t, delta, stop, repaired, coupling)
            for i, leg in enumerate(legs):
                if leg.event:
                    events[leg.name].append((t, leg.event))
                    event_records.append(dict(leg=leg.name, kind=leg.event, t=t, frame=max(0,math.ceil(t*fps-1e-9))))
                if heights[i] <= 0 < leg.state[1]:
                    # Observed at the accepted endpoint, not an interpolated root.
                    event_records.append(dict(leg=leg.name, kind='lift-off', t=t+delta, frame=max(0,math.ceil((t+delta)*fps-1e-9))))
            v1, _ = speed(t+delta, stop)
            distance += delta*(v0+v1)/2
            t += delta
        phases, targets, errors = phase_fit(legs)
        frames.append({'t': target, 'distance': distance, 'speed': speed(t,stop)[0],
                       'legs': [leg.state[:] for leg in legs], 'branches': [leg.branch for leg in legs],
                       'analysis': dict(phases=phases, targets=targets, errors=errors)})
        traces.extend({'t': target, 'leg':leg.name, 'branch':leg.branch,
                       **dict(zip(('x','y','dx','dy'),leg.state))} for leg in legs)
    diagnostics = {'events': events, 'event_records': event_records,
                   'singularity_guard_calls':sum(leg.guards for leg in legs),
                   'max_height':max(r['y'] for r in traces),
                   'min_sampled_height':min(r['y'] for r in traces),
                   'final_states':{leg.name:leg.state for leg in legs}}
    return frames, traces, diagnostics
