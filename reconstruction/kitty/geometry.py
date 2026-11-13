"""Tapered solids, relative similarities, and the figure-8 leg constraints.

World X is depth, Y points backwards along travel, Z is up. Projection drops X.
All dimensions below are reconstruction estimates: the original lists are lost.
"""
import math
from dataclasses import dataclass, field
from .core import solve_leg


def add(a,b): return tuple(x+y for x,y in zip(a,b))
def mul(a,s): return tuple(x*s for x in a)
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
IDENTITY = ((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))  # columns
def apply(r,v): return tuple(sum(r[j][i]*v[j] for j in range(3)) for i in range(3))
def compose(a,b): return tuple(apply(a,col) for col in b)


def paper_rotation(psi, phi, omega):
    """pp.196–197: longitudinal axis from negative Z, azimuth, then roll."""
    u = (math.sin(psi)*math.cos(phi), math.sin(psi)*math.sin(phi), -math.cos(psi))
    z0 = ((math.cos(psi)*math.cos(phi), math.cos(psi)*math.sin(phi), math.sin(psi))
          if abs(math.sin(psi)) > 1e-12 else (0.,1.,0.))
    z = add(mul(z0,math.cos(omega)),mul(cross(u,z0),math.sin(omega)))
    return (u,cross(z,u),z)


def yaw(a):
    return ((math.cos(a),math.sin(a),0.),(-math.sin(a),math.cos(a),0.),(0.,0.,1.))


@dataclass
class Node:
    name: str
    origin: tuple = (0.,0.,0.)
    rotation: tuple = IDENTITY
    scale: float = 1.
    # h_start, h_end, b_start, b_end in the normalized length-one frame.
    dimensions: tuple = None
    children: list = field(default_factory=list)


def solid(name, start, end, h0, h1, b0=None, b1=None):
    b0 = h0 if b0 is None else b0
    b1 = h1 if b1 is None else b1
    direction = add(end,mul(start,-1)); length = math.sqrt(dot(direction,direction))
    u = mul(direction,1/length)
    r = paper_rotation(math.acos(max(-1.,min(1.,-u[2]))),math.atan2(u[1],u[0]),0.)
    return Node(name,tuple(start),r,length,(h0/length,h1/length,b0/length,b1/length))


def leaves(node, origin=(0.,0.,0.), rotation=IDENTITY, scale=1.):
    o = add(origin,mul(apply(rotation,node.origin),scale))
    r, s = compose(rotation,node.rotation), scale*node.scale
    if node.children:
        for child in node.children:
            yield from leaves(child,o,r,s)
    elif node.dimensions is not None:
        h0,h1,b0,b1 = node.dimensions
        vertices = [add(o,mul(apply(r,(x,sy*b/2,sz*h/2)),s))
                    for x,h,b in ((0,h0,b0),(1,h1,b1)) for sy,sz in ((-1,-1),(-1,1),(1,1),(1,-1))]
        yield node.name, vertices


BASELINE_MODEL = {
    'leg_lengths':[.40,.36,.29], 'foot_length':.18, 'd':1.0,
    'shoulder_height':.75, 'shoulder_y':[-.62,.65], 'leg_depth':.19,
    'body_start':[0.,-.68,.83], 'body_end':[0.,.73,.87],
    'body_height':[.36,.40], 'body_width':[.37,.42],
    'tail_start':[0.,.70,.94], 'tail_end':[0.,1.40,1.65],
    'tail_thickness':[.13,.035], 'view_yaw_degrees':18.,
    'provenance':'All shape dimensions and schedules are estimates; none is a recovered model list.'
}


# Baseline remains immutable by convention; callers receive independent copies.
DEFAULT_MODEL = BASELINE_MODEL


def cat(frame, model=None, head_turn=True):
    m = DEFAULT_MODEL if model is None else model
    root = Node('cat')
    root.children += [solid('body',m['body_start'],m['body_end'],*m['body_height'],*m['body_width']),
                      solid('tail',m['tail_start'],m['tail_end'],*m['tail_thickness'])]
    errors = []
    for i,state in enumerate(frame['legs']):
        front = i%2 == 1
        depth = m['leg_depth'] * (-1 if i<2 else 1)
        group = Node(('right_' if i<2 else 'left_')+('front' if front else 'rear'),
                     (depth,m['shoulder_y'][0 if front else 1],0.))
        points, info = solve_leg(state[0],state[1],front,tuple(m['leg_lengths']),m['shoulder_height'],m['d'],m['foot_length'])
        errors.append(info['endpoint_error'])
        thickness = [.18,.13,.075,.055,.04] if not front else [.135,.105,.065,.055,.04]
        for j in range(4):
            a,b = points[j:j+2]
            group.children.append(solid(('thigh','shin','tarsus','foot')[j],(0.,*a),(0.,*b),thickness[j],thickness[j+1]))
        root.children.append(group)
    # Inferred head schedule; the paper describes turning but supplies no function.
    q = max(0.,min(1.,(frame['t']-9)/3)) if head_turn else 0.
    turn = math.radians(65)*(q*q*(3-2*q))
    neckhead = Node('head_and_neck')
    neckhead.children.append(solid('neck',(0.,-.62,.85),(0.,-.94,1.08),.29,.28,.30,.30))
    head = Node('head',(0.,-.97,1.11),yaw(turn))
    head.children += [solid('skull',(0.,.05,0.),(0.,-.30,.0),.31,.28,.33,.33),
                      solid('muzzle',(0.,-.26,-.07),(0.,-.45,-.08),.15,.12,.23,.18)]
    for side in (-1,1):
        head.children.append(solid('ear_'+str(side),(side*.12,-.12,.10),(side*.16,-.13,.37),.18,0.,.16,.012))
        for j in range(3):
            head.children.append(solid('whisker_'+str(side)+'_'+str(j),(side*.10,-.35,-.06),
                                       (side*(.42+.04*j),-.64+.07*j,-.16+.10*j),.012,.007))
    neckhead.children.append(head)
    root.children.append(neckhead)
    return root,max(errors)


def hull(points):
    """Convex hull: projection of a convex tapered primitive is convex."""
    points = sorted(set(points))
    if len(points)<=2: return points
    def turn(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lo,hi = [],[]
    for p in points:
        while len(lo)>=2 and turn(lo[-2],lo[-1],p)<=0:lo.pop()
        lo.append(p)
    for p in reversed(points):
        while len(hi)>=2 and turn(hi[-2],hi[-1],p)<=0:hi.pop()
        hi.append(p)
    return lo[:-1]+hi[:-1]
