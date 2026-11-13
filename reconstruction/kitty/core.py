"""Tables 1–5, pp.205–208. Event updates occur only on accepted steps."""
import math
import cmath
from dataclasses import dataclass

# Tables 3–5. Shared constants need not be copied into each leg.
H, M1, M2, FIVE_M, EPSILON = .75, 1., 15., 2., .001
ORDER = ('right_rear', 'right_front', 'left_rear', 'left_front')


def speed(t, stop=True):
    """Inferred schedule: cruise 4 s, cosine deceleration until 12 s."""
    if not stop or t <= 4:
        return .554, 0.
    if t >= 12:
        return 0., 0.
    q = math.pi * (t - 4) / 8
    return .277 * (1 + math.cos(q)), -.277 * math.pi / 8 * math.sin(q)


@dataclass
class Leg:
    name: str
    state: list
    previous_dx: float
    k: list
    front: bool
    length: float = 1.05  # Omitted by paper; shared with the shape solver.
    branch: int = 1
    landing_end: float = None
    event: str = None
    guards: int = 0


def initial_legs(length=1.05):
    # x, y, x', y' from table 4; K1/K2 from table 5.
    states = ((.3, 0., .554, 0.), (-.2, 0., .554, 0.),
              (-.2, .22, -.45, -.1), (.3, .22, -.45, .1))
    previous = (.554, .554, -.451, -.449)
    return [Leg(name, list(states[i]), previous[i],
                [0., 0., 0., 0., 0., 0., 0., 0.] if i < 2
                else [0., 1/3, .6, 0., 0., 0., 0., 0.],
                bool(i % 2), length) for i, name in enumerate(ORDER)]


def phase_errors(legs):
    """Least-squares chord-distance fit on S1, with the published leg order.

    The leg due to lift next lags by pi/2. Negative error means lagging.
    Unlike arithmetic angle averaging, this is continuous across 2*pi.
    """
    phases = []
    for leg in legs:
        x, y, dx, dy = leg.state
        a = math.sqrt(leg.length**2 - H**2)
        phases.append(math.pi/2 + math.pi*x/(2*a) if dx >= 0
                      else 3*math.pi/2 - math.pi*x/(2*a))
    offsets = [-i*math.pi/2 for i in range(4)]
    s = sum(math.sin(p-o) for p, o in zip(phases, offsets))
    c = sum(math.cos(p-o) for p, o in zip(phases, offsets))
    base = math.atan2(s, c) if math.hypot(s, c) > 1e-12 else phases[0]
    return [math.atan2(math.sin(p-base-o), math.cos(p-base-o))
            for p, o in zip(phases, offsets)]


def select(leg, t, v, repaired=True):
    x, y, dx, dy = leg.state
    leg.event = None
    # Explicit reconstruction repair: terminate a landing at its cubic endpoint.
    # Otherwise a sampled integrator can miss the double root y=0 entirely.
    if repaired and leg.landing_end is not None and t >= leg.landing_end:
        y, dx, dy = 0., v, 0.
        leg.landing_end = None
        leg.event = 'touchdown'
    if y <= 0:
        if repaired:
            dx, dy = v, 0.
        y = 0.
        branch = 1 if abs(x) < (.3 if leg.front else .4) or x < 0 or v == 0 else 2
    else:
        k = leg.k
        if dx <= 0 < leg.previous_dx:
            k[1], k[2], k[3] = dy/x, abs(x), dy*dy/(2*y)
            leg.event = 'rear reversal'
        if dx >= 0 > leg.previous_dx:
            duration = abs(x)/FIVE_M
            k[3], k[4], k[5] = dy*dy/(2*y), -v/y, t
            k[6] = (dy*duration + 2*y)/duration**3
            k[7] = -(2*dy*duration + 3*y)/duration**2
            leg.landing_end = t + duration
            leg.event = 'front reversal'
        # Repeatedly zeroing velocities below epsilon can pin the leg forever
        # at small dt. The repaired solver uses true sign crossings instead.
        epsilon = 0. if repaired else EPSILON
        if dx <= -epsilon:
            branch = 3 if abs(x) < (.4 if leg.front else .3) else 5
        elif dx >= epsilon:
            branch = 6 if x < 0 else 2
        else:
            dx = 0.
            branch = 4 if v == 0 else (6 if x < 0 else 3)
    leg.state = [x, y, dx, dy]
    leg.branch = branch


def derivative(leg, state, t, error, stop, repaired):
    x, y, dx, dy = state
    v, dv = speed(t, stop)
    k, b = leg.k, leg.branch
    if b == 1:
        ax, ay = dv, 0.
    elif b in (2, 5):
        gap = abs(leg.length - math.hypot(x, H-y))
        # Singular-force guard, counted in diagnostics, not a historical constant.
        if gap < 1e-6:
            gap = 1e-6
            leg.guards += 1
        ax = -M1*x/gap
        ay = M2*(H/8-y) if b == 2 else k[1]*dx
    elif b == 3:
        if k[2] <= 0:
            raise ArithmeticError('Swing selected before K2 was initialized')
        ax, ay = -math.pi/k[2]*v*(1-error/(2*math.pi))*x, k[1]*dx
    elif b == 4:
        ax, ay = 0., k[3] if repaired else -k[3]
    else:
        ax, ay = k[4]*dy + dv, 6*k[6]*(t-k[5]) + 2*k[7]
    return [dx, dy, ax, ay]


def step(legs, t, dt, stop=True, repaired=True, coupling=True):
    v, _ = speed(t, stop)
    for leg in legs:
        select(leg, t, v, repaired)
    errors = phase_errors(legs) if coupling else [0.]*4
    for leg, error in zip(legs, errors):
        s = leg.state[:]
        f = lambda q, at: derivative(leg, q, at, error, stop, repaired)
        a = f(s, t)
        b = f([u+dt*z/2 for u,z in zip(s,a)], t+dt/2)
        c = f([u+dt*z/2 for u,z in zip(s,b)], t+dt/2)
        d = f([u+dt*z for u,z in zip(s,c)], t+dt)
        leg.previous_dx = s[2]
        leg.state = [u+dt*(aa+2*bb+2*cc+dd)/6 for u,aa,bb,cc,dd in zip(s,a,b,c,d)]
        if not all(math.isfinite(z) and abs(z)<1e5 for z in leg.state):
            raise ArithmeticError('Unstable leg: '+leg.name)



def solve_leg(x, y, front, lengths=(.40,.36,.29), h=.75, d=1.0, foot_length=.18):
    """Signed turns beta=theta2-theta1, gamma=theta3-theta2.

    beta=c*gamma reduces endpoint IK to a scalar equation |Q(gamma)|=rho.
    The negative bend selects the elbow-back solution in the film.
    Alpha=d*y rotates segment four relative to the floor.
    """
    c = .8 if front else -1.2
    target = complex(x,max(0.,y)-h)
    rho = abs(target)
    sign = -1.  # Both front and rear bend branches verified against computed frames.
    def vector(g):
        return lengths[0]*cmath.exp(-1j*c*g)+lengths[1]+lengths[2]*cmath.exp(1j*g)
    # Search the first root; do not quietly stretch lengths for unreachable poses.
    lo, hi = 0., None
    for i in range(1,33):
        candidate = math.pi*i/32
        if abs(vector(sign*candidate)) <= rho:
            hi = candidate
            break
        lo = candidate
    if rho > sum(lengths)+1e-8 or hi is None:
        raise ValueError('Inferred leg lengths cannot reach endpoint: '+str((x,y,front,rho)))
    for _ in range(32):
        mid = (lo+hi)/2
        if abs(vector(sign*mid)) > rho: lo = mid
        else: hi = mid
    gamma = sign*(lo+hi)/2
    theta2 = cmath.phase(target)-cmath.phase(vector(gamma))
    angles = (theta2-c*gamma,theta2,theta2+gamma)
    points = [complex(0,h)]
    for length,angle in zip(lengths,angles):
        points.append(points[-1]+length*cmath.exp(1j*angle))
    alpha = d*max(0.,y)
    points.append(points[-1]-foot_length*cmath.exp(1j*alpha))
    residual = abs(points[3]-complex(x,max(0.,y)))
    return [(p.real,p.imag) for p in points], {'endpoint_error':residual,'gamma':gamma,'beta':c*gamma,'alpha':alpha}
