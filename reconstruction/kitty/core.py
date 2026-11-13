"""The published controller and our leg solver; no frame history or I/O.

Source: Konstantinov, Minakhin & Ponomarenko (1974), pp. 201–209.
State is [x, y, dx, dy]: x points backwards relative to the shoulder, y is
height above the floor, and dx/dy are their time derivatives. The endpoint
is the end of segment THREE, not the toe. Length and time units are model
units; the mapping to display seconds is an assumption.

See PAPER-TO-CODE.md for the distinction between printed rules, numerical
repairs, and choices required by missing historical details.
"""
import cmath
import math
from dataclasses import dataclass
from typing import List, Optional

# Table 3. KM1/KM2 are interpreted as M1/M2; FIVE_M retains the printed value.
H, M1, M2, FIVE_M, EPSILON = .75, 1., 15., 2., .001
ORDER = ('right_rear', 'right_front', 'left_rear', 'left_front')
STANCE, REAR_REVERSAL, SWING, STOP, FRONT_REVERSAL, LANDING = range(1, 7)
BRANCH_NAMES = {
    STANCE: 'Stance', REAR_REVERSAL: 'Rear reversal / lift', SWING: 'Swing',
    STOP: 'Stop', FRONT_REVERSAL: 'Front reversal', LANDING: 'Landing',
}


def speed(t, stop=True):
    """Inferred schedule: v(0)=.554, cruise to t=4, cosine stop at t=12."""
    if not stop or t <= 4:
        return .554, 0.
    if t >= 12:
        return 0., 0.
    angle = math.pi * (t - 4) / 8
    return .277 * (1 + math.cos(angle)), -.277 * math.pi / 8 * math.sin(angle)


@dataclass
class Leg:
    """Bounded per-leg state. k[0] is unused so k[1] means the paper's K1.

    event is only the latest step's event; the optional exporter collects
    history. branch and coefficients stay fixed throughout each RK4 step.
    """
    name: str
    state: List[float]
    previous_dx: float
    k: List[float]
    front: bool
    length: float = 1.05  # Sum of first three lengths; inferred, not published.
    branch: int = STANCE
    landing_end: Optional[float] = None
    event: Optional[str] = None
    guards: int = 0


def initial_legs(length=1.05):
    """Tables 4–5, in the paper's right-rear → right-front → left-rear → left-front order."""
    states = (
        (.3, 0., .554, 0.), (-.2, 0., .554, 0.),
        (-.2, .22, -.45, -.1), (.3, .22, -.45, .1),
    )
    previous = (.554, .554, -.451, -.449)
    legs = []
    for index, name in enumerate(ORDER):
        coefficients = ([0., 0., 0., 0., 0., 0., 0., 0.] if index < 2
                        else [0., 1/3, .6, 0., 0., 0., 0., 0.])
        legs.append(Leg(name, list(states[index]), previous[index],
                        coefficients, bool(index % 2), length))
    return legs


def phase_fit(legs):
    """Return current phases, fitted cross targets and signed errors (radians).

    pp.208–209 give the phase mapping and cross fit. Squared chord distance,
    circular wrapping and the degenerate-fit fallback are our interpretations.
    Negative error denotes lag; the next leg to lift lags by pi/2.
    """
    phases = []
    for leg in legs:
        x, y, dx, dy = leg.state
        reach = math.sqrt(leg.length**2 - H**2)
        phases.append(math.pi/2 + math.pi*x/(2*reach) if dx >= 0
                      else 3*math.pi/2 - math.pi*x/(2*reach))
    offsets = [-index*math.pi/2 for index in range(4)]
    sine_sum = sum(math.sin(phase-offset) for phase, offset in zip(phases, offsets))
    cosine_sum = sum(math.cos(phase-offset) for phase, offset in zip(phases, offsets))
    base = (math.atan2(sine_sum, cosine_sum)
            if math.hypot(sine_sum, cosine_sum) > 1e-12 else phases[0])
    # Keep subtraction order: changing to phase-(base+offset) changes rounding.
    errors = [math.atan2(math.sin(phase-base-offset), math.cos(phase-base-offset))
              for phase, offset in zip(phases, offsets)]
    return phases, [base+offset for offset in offsets], errors


def phase_errors(legs):
    """Compatibility interface used by the integrator; no history is retained."""
    return phase_fit(legs)[2]


def select(leg, t, v, repaired=True):
    """Table 2: update accepted-step events and select an acceleration pair.

    This mutates state, coefficients and event metadata. Never call it from an
    RK4 trial stage. repaired=False retains the printed zero band and contact
    behavior; at small dt it can reach swing before K2 is initialized.
    """
    x, y, dx, dy = leg.state
    leg.event = None
    # Repair: terminate at the cubic's double root, which sampling can miss.
    if repaired and leg.landing_end is not None and t >= leg.landing_end:
        y, dx, dy = 0., v, 0.
        leg.landing_end = None
        leg.event = 'touchdown'

    if y <= 0:
        if repaired:
            dx, dy = v, 0.  # Enforce a stationary planted endpoint in world space.
        y = 0.
        rear_limit = .3 if leg.front else .4
        branch = STANCE if abs(x) < rear_limit or x < 0 or v == 0 else REAR_REVERSAL
    else:
        k = leg.k
        if dx <= 0 < leg.previous_dx:  # Table 1, coefficient group I.
            k[1], k[2], k[3] = dy/x, abs(x), dy*dy/(2*y)
            leg.event = 'rear reversal'
        if dx >= 0 > leg.previous_dx:  # Table 1, coefficient group II.
            duration = abs(x)/FIVE_M
            k[3], k[4], k[5] = dy*dy/(2*y), -v/y, t
            k[6] = (dy*duration + 2*y)/duration**3
            k[7] = -(2*dy*duration + 3*y)/duration**2
            leg.landing_end = t + duration
            leg.event = 'front reversal'

        # Repair: use true sign crossings; repeated epsilon-zeroing can pin a leg.
        epsilon = 0. if repaired else EPSILON
        if dx <= -epsilon:
            front_limit = .4 if leg.front else .3
            branch = SWING if abs(x) < front_limit else FRONT_REVERSAL
        elif dx >= epsilon:
            branch = LANDING if x < 0 else REAR_REVERSAL
        else:
            dx = 0.
            branch = STOP if v == 0 else (LANDING if x < 0 else SWING)
    leg.state = [x, y, dx, dy]
    leg.branch = branch


def derivative(leg, state, t, error, stop, repaired):
    """Table 1: [x', y', x'', y''] for the already selected branch.

    Only the singularity diagnostic counter can change here. event, k and
    branch do not change between integration stages.
    """
    x, y, dx, dy = state
    v, dv = speed(t, stop)
    k, branch = leg.k, leg.branch
    if branch == STANCE:
        ax, ay = dv, 0.
    elif branch in (REAR_REVERSAL, FRONT_REVERSAL):
        gap = abs(leg.length - math.hypot(x, H-y))
        if gap < 1e-6:  # Reconstruction guard; not a printed constant.
            gap = 1e-6
            leg.guards += 1
        ax = -M1*x/gap
        ay = M2*(H/8-y) if branch == REAR_REVERSAL else k[1]*dx
    elif branch == SWING:
        if k[2] <= 0:
            raise ArithmeticError('Swing selected before K2 was initialized')
        ax, ay = -math.pi/k[2]*v*(1-error/(2*math.pi))*x, k[1]*dx
    elif branch == STOP:
        # Printed -K3; +K3 brakes an already descending endpoint.
        ax, ay = 0., k[3] if repaired else -k[3]
    else:
        ax, ay = k[4]*dy + dv, 6*k[6]*(t-k[5]) + 2*k[7]
    return [dx, dy, ax, ay]


def step(legs, t, dt, stop=True, repaired=True, coupling=True):
    """Advance all four legs with RK4; commit events once, before trial stages.

    p.201 permits RK4 but does not specify the historical integration scheme.
    Coefficients, branches and phase corrections are frozen within this step.
    """
    v, _ = speed(t, stop)
    for leg in legs:
        select(leg, t, v, repaired)
    errors = phase_errors(legs) if coupling else [0.]*4

    for leg, error in zip(legs, errors):
        state = leg.state[:]

        def evaluate(trial, at):
            return derivative(leg, trial, at, error, stop, repaired)

        stage1 = evaluate(state, t)
        stage2 = evaluate([value+dt*slope/2 for value, slope in zip(state, stage1)], t+dt/2)
        stage3 = evaluate([value+dt*slope/2 for value, slope in zip(state, stage2)], t+dt/2)
        stage4 = evaluate([value+dt*slope for value, slope in zip(state, stage3)], t+dt)
        leg.previous_dx = state[2]
        leg.state = [value+dt*(a+2*b+2*c+d)/6
                     for value, a, b, c, d in zip(state, stage1, stage2, stage3, stage4)]
        if not all(math.isfinite(value) and abs(value) < 1e5 for value in leg.state):
            raise ArithmeticError('Unstable leg: '+leg.name)


def solve_leg(x, y, front, lengths=(.40, .36, .29), h=.75, d=1.0, foot_length=.18):
    """Reconstruct the joints from the third-segment endpoint (figure 8/p.202).

    Signed turns: beta=theta2-theta1, gamma=theta3-theta2; beta=c*gamma.
    The scalar equation |Q(gamma)|=rho gives the bend, then a rigid rotation
    aims the three segments at the endpoint. The negative root matches the
    film's elbow-back front legs. Alpha=d*y sets the fourth segment's angle.

    The constraints are published; this root solver, bend choice and default
    lengths/d are reconstruction choices. No segment is stretched to fit.
    """
    c = .8 if front else -1.2
    target = complex(x, max(0., y)-h)
    rho = abs(target)
    sign = -1.

    def vector(gamma):
        return (lengths[0]*cmath.exp(-1j*c*gamma) + lengths[1]
                + lengths[2]*cmath.exp(1j*gamma))

    # Bracket the first admissible root; retain the original 32-part search.
    lo, hi = 0., None
    for index in range(1, 33):
        candidate = math.pi*index/32
        if abs(vector(sign*candidate)) <= rho:
            hi = candidate
            break
        lo = candidate
    if rho > sum(lengths)+1e-8 or hi is None:
        raise ValueError('Inferred leg lengths cannot reach endpoint: '+str((x, y, front, rho)))

    for _ in range(32):
        mid = (lo+hi)/2
        if abs(vector(sign*mid)) > rho:
            lo = mid
        else:
            hi = mid
    gamma = sign*(lo+hi)/2
    theta2 = cmath.phase(target)-cmath.phase(vector(gamma))
    angles = (theta2-c*gamma, theta2, theta2+gamma)
    points = [complex(0, h)]
    for length, angle in zip(lengths, angles):
        points.append(points[-1]+length*cmath.exp(1j*angle))

    alpha = d*max(0., y)
    points.append(points[-1]-foot_length*cmath.exp(1j*alpha))
    residual = abs(points[3]-complex(x, max(0., y)))
    return [(point.real, point.imag) for point in points], {
        'endpoint_error': residual, 'gamma': gamma, 'beta': c*gamma, 'alpha': alpha,
    }
