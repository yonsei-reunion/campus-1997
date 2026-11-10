"""The backs and feet of the generic halls (blender/generic.py): what a wall has besides its windows.

From the photos (reference/고증/3.20_일반_건물_뒷면.md):
  - rain-water downpipes.  A flat roof drains through its parapet into a hopper head and down a 10 cm pipe to a shoe
    over the paving: dark on the grey annex beside 학생회관 in 1997 (reference/1997_학생회관.jpg, at its corner),
    painted as the wall between the window columns of 국제학사 and at 체육교육관's corner.  A pitched roof has an
    eaves gutter and dark pipes with a swan neck back to the wall (reference/2003_가을_교육관_서쪽면.jpg).
  - a plinth: a band at the wall's foot standing a little proud of it, with a chamfered top.
  - a back door: a steel leaf in a plain frame under a small concrete canopy, a step or two down to the paving.
  - louvred vents in the plinth, and a TV aerial on the town's roofs and the campus houses (학생회관's roof has one
    in the 1997 photo), all pointing at the Namsan transmitter.

Everything is drawn in materials the halls already have, so the merged mesh gets no new draw call, and nothing here
draws from generic.py's random stream: each hall has its own random.Random seeded with its id (build.py's ghost
halls, `at` in their dict, get nothing).  Pipes and plinths are not colliders; a back door's steps are walked on like
the front flights (landmarks.stair_flight) but are not listed in entrances.json (the title card's start places and
the shrubs moved off the front steps go by that list), so a back door is only put where nothing is planted.
"""
import math, random
from mathutils import Vector, Matrix
from common import CAMPUS, ground, ground_top, offset_poly
import windows

PIPE_R = 0.05              # m: a 100 mm downpipe
PIPE_OFF = 0.11            # its axis off the wall (clear of the plinth); past a floor band where the hall has them
PIPE_EVERY = 30.0          # m of wall to a pipe on the campus halls
PLINTH_D = 0.05            # how far the plinth stands out, and its chamfer
HALLS_WITH_DOOR = ('modern', 'white', 'brick', 'tile', 'gym')
NAMSAN = math.atan2(-1.55, 4.4)     # the bearing of the Namsan transmitter from the campus (x east, y north)

# plinth per style: (material, height); the town's by its own draw
PLINTH = {'modern': ('concrete_dark', 0.55), 'gym': ('concrete_dark', 0.55), 'white': ('concrete_dark', 0.5),
          'tile': ('stone_granite', 0.6), 'brick': ('stone_granite', 0.6), 'house': ('concrete_dark', 0.4)}
# downpipes per style, most likely first: ivory PVC (frame_white), galvanised sheet (frame_silver), dark paint
PIPES = {'modern': ('metal_dark', 'frame_silver'), 'gym': ('frame_silver', 'metal_dark'),
         'white': ('frame_white', 'frame_white', 'metal_dark'), 'tile': ('frame_white',), 'brick': ('metal_dark', 'frame_white'),
         'house': ('frame_white', 'frame_silver'), 'stone': ('metal_dark',), 'stone_pale': ('metal_dark',),
         'city': ('frame_white', 'frame_silver', 'frame_white', 'metal_dark')}
PITCH = {'house': 0.55, 'stone': 0.75, 'stone_pale': 0.75}      # generic.build_generic's hip roofs (over 0.5)
EAVE = 0.5

COUNT = {'pipes': 0, 'doors': 0, 'vents': 0, 'aerials': 0, 'plinth_m': 0.0}     # what the last build placed
_others = None


def back_others():
    """the outlines a wall can stand against: every hall and landmark, and the colliders outside the outlines"""
    global _others
    if _others is None:
        _others = []
        for bid, fp in [(b['id'], b['footprint']) for b in CAMPUS['buildings']] + [(None, c) for c in CAMPUS.get('colliders', [])]:
            xs, ys = [p[0] for p in fp], [p[1] for p in fp]
            _others.append((bid, min(xs), min(ys), max(xs), max(ys), [tuple(p) for p in fp]))
    return _others


def back_inside(x, y, poly):
    c = False
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def back_bays(L, st, shop=False):
    """generic.wall_edge's bays on an edge L long: (bays, bay width, half a pier), bays 0 where it has no windows"""
    bays = int(round(L / st['bay']))
    if L < 2.6 or bays < 1:
        return 0, L, L / 2
    bw = L / bays
    ww = 0.92 if shop else st['ww']
    half = bw * (1 - ww) / 2 - (0.32 if st.get('lights') else 0.0)
    return bays, bw, half


class BackEdge:
    def __init__(self, i, a, b):
        self.i = i
        self.a, self.b = Vector((*a, 0)), Vector((*b, 0))
        t = self.b - self.a
        self.L = t.length
        self.t = t / max(self.L, 1e-9)
        self.n = Vector((self.t.y, -self.t.x, 0))
        self.top = 0.0             # roof level (flat roofs) or the eaves (pitched)
        self.door = None           # the front door's (s, half width kept clear)
        self.back = None           # a back door: dict(bay, s0, s1, w, ...)
        self.runs = []             # plinth runs (back_feet)
        self.gaps = []             # [s0, s1] kept clear of it: the front flight

    def P(self, s, z, d=0.0):
        p = self.a + self.t * s + self.n * d
        return (p.x, p.y, z)

    def xy(self, s, d=0.0):
        p = self.a + self.t * s + self.n * d
        return p.x, p.y


class BackPlan:
    def __init__(self):
        self.edges = []
        self.on = False


def back_plan(b, poly, st, fh, z0, zt, nf, door, shop, tops, ups, pitched=False):
    """Decide, before the walls are drawn, where this hall's back door goes (generic.wall_edge leaves that bay to
    back_door) and gather what back_finish needs.  poly: the walls' outline (CCW); door: generic.entry_edge's
    (edge, s) or None; tops: each edge's roof level."""
    plan = BackPlan()
    plan.on = 'at' not in b                    # (a ghost of build.py: drawn only for the random stream)
    if not plan.on:
        return plan
    style = st['name']
    plan.b, plan.st, plan.style, plan.fh, plan.z0, plan.zt, plan.nf = b, st, style, fh, z0, zt, nf
    plan.shop, plan.pitched, plan.poly = shop, pitched, poly
    plan.rnd = rnd = random.Random('backs:%s' % b['id'])
    plan.town = style == 'city'
    n = len(poly)
    plan.edges = [BackEdge(i, poly[i], poly[(i + 1) % n]) for i in range(n)]
    for e, top, up in zip(plan.edges, tops, ups):
        e.top, e.nf = top, nf + up
        e.bays, e.bw, e.half = back_bays(e.L, st, shop)
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    box = (min(xs) - 4, min(ys) - 4, max(xs) + 4, max(ys) + 4)
    plan.box, plan.items = box, None
    plan.near = [o[5] for o in back_others() if o[0] != b['id'] and not (o[1] > box[2] or o[3] < box[0] or o[2] > box[3] or o[4] < box[1])]
    # the front door: its bays and what its flight needs kept clear (generic.porch)
    plan.front = None
    if door:
        e = plan.edges[door[0]]
        span = min(e.bays, b['entry'].get('span', 1)) if e.bays else 1
        kd = min(e.bays - 1, max(0, int(door[1] / e.bw))) if e.bays else 0
        if span > 1:
            kd = min(e.bays - span, max(0, kd - span // 2))
        sc = (kd + span / 2) * e.bw if e.bays else door[1]
        e.door = (sc, span * e.bw / 2 + (2.7 if b['entry'].get('music') else 1.7))
        plan.front = e
    # material draws (the same count whatever is placed, so that a hall keeps its colours when its surroundings change)
    plan.pipe_mat = rnd.choice(PIPES.get(style, ('frame_white',)))
    plan.leaf_mat = rnd.choice(('metal_green', 'metal_green', 'frame_dark', 'frame_white'))
    plan.plinth = PLINTH.get(style)
    if plan.town:
        plan.plinth = (rnd.choice(('concrete', 'concrete', 'concrete_dark')), 0.2 if shop else rnd.choice((0.35, 0.45, 0.5)))
    plan.aerial = rnd.random() < (0.38 if plan.town else 0.6 if style == 'house' else 0.0)
    plan.wide = rnd.random() < (0.5 if style in ('modern', 'gym') else 0.25)
    plan.louvre = rnd.random() < 0.35
    plan.seed = rnd.random()
    if style in HALLS_WITH_DOOR:
        back_pick_door(plan)
    return plan


def back_blocked(plan, e, s, d):
    x, y = e.xy(s, d)
    return any(back_inside(x, y, fp) for fp in plan.near)


def back_planted(plan, e, s0, s1, d1):
    """whether a tree, a shrub, a prop or a car stands in front of the wall over [s0, s1] out to d1"""
    if plan.items is None:
        x0, y0, x1, y1 = plan.box
        plan.items = [(it[1], it[2], r) for key, r in (('trees', 0.6), ('shrubs', 0.9), ('props', 0.8), ('cars', 2.6))
                      for it in CAMPUS.get(key, []) if x0 - 3 < it[1] < x1 + 3 and y0 - 3 < it[2] < y1 + 3]
    for x, y, r in plan.items:
        v = Vector((x, y, 0)) - e.a
        s, d = v.dot(e.t), v.dot(e.n)
        if s0 - r < s < s1 + r and -1.0 < d < d1 + r:
            return True
    return False


def back_pick_door(plan):
    """One back door: on the long wall facing most away from the front door, in a bay whose ground is about the
    floor's, clear of other buildings and of anything planted, not an end bay."""
    rnd = plan.rnd
    order = rnd.random()
    z0 = plan.z0
    best = None
    for e in plan.edges:
        if e is plan.front or e.bays < 3 or (plan.style == 'gym' and e.i % 2):
            continue
        face = -e.n.dot(plan.front.n) if plan.front else 0.0
        for k in range(1, e.bays - 1):
            sc = (k + 0.5) * e.bw
            gs = [ground_top(*e.xy(sc + u, d)) for u in (-0.6, 0.0, 0.6) for d in (0.6, 1.6, 2.4)]
            # (on a slope the door is on the storey the ground in front of it reaches, as the front doors are)
            f = max(0, min(e.nf - 1, int((max(gs) + 0.5 - z0) / plan.fh)))
            zf = z0 + f * plan.fh
            if max(gs) > zf + 0.22 or min(gs) < zf - 0.75:
                continue
            if any(back_blocked(plan, e, sc + u, d) for u in (-1.4, 0.0, 1.4) for d in (0.6, 1.8, 3.2)):
                continue
            if back_planted(plan, e, sc - 1.4, sc + 1.4, 2.8):
                continue
            # (towards a quarter of the way along, where the stair cores of these slabs are)
            q = min(abs(sc / e.L - 0.25), abs(sc / e.L - 0.75))
            score = face * 2.0 + min(e.L, 60.0) / 60.0 - q + 0.3 * math.sin(order * 50 + e.i * 7.3 + k * 1.7)
            if best is None or score > best[0]:
                best = (score, e, k, f)
    if best is None:
        return
    _, e, k, f = best
    w = 1.7 if plan.wide and e.bw >= 3.1 else 0.95
    e.back = dict(bay=k, floor=f, s0=k * e.bw, s1=(k + 1) * e.bw, w=w, leaf=plan.leaf_mat, louvre=plan.louvre, clear=w / 2 + 0.3)


def back_door(mb, a, b, s0, s1, zf, fh, st, opts):
    """The ground-floor bay [s0, s1] of the wall a->b with a back door instead of its window: the wall round a shallow
    recess, a steel leaf (or a pair) with a small wired light, sometimes a louvre at its foot, a thin concrete canopy
    and a concrete landing with a step or two down to the ground."""
    import landmarks as LM
    P, L, t, n = LM.edge_P(a, b)
    wall = st['wall']
    w, rec = opts['w'], 0.12
    sc = (s0 + s1) / 2
    o0, o1 = sc - w / 2, sc + w / 2
    zt = zf + fh
    g = max(ground_top(*P(sc + u, 0, k)[:2]) for u in (-w / 2, 0.0, w / 2) for k in (0.6, 1.6))
    zd = max(zf + 0.12, g + 0.16)
    zo = zd + 2.1
    # (the wall in pieces whose corners are clear of the landing and the canopy: the bake shades a face from its
    # corners, and one buried in the landing would smear its dark up the whole pier)
    za, zc = zd + 0.35, zo + 0.25
    for u0, u1 in ((s0, o0), (o1, s1)):
        LM.flat_wall(mb, P, u0, u1, zf, za, wall)
        LM.flat_wall(mb, P, u0, u1, za, zt, wall)
    LM.flat_wall(mb, P, o0, o1, zf, zd, wall)
    LM.flat_wall(mb, P, o0, o1, zo, zc, wall)
    LM.flat_wall(mb, P, o0, o1, zc, zt, wall)
    fr = st['frame']                                                       # the steel frame lining the recess
    mb.quad(P(o1, zo, 0), P(o0, zo, 0), P(o0, zo, -rec), P(o1, zo, -rec), fr)
    mb.quad(P(o0, zo, 0), P(o0, zo, -rec), P(o0, zd, -rec), P(o0, zd, 0), fr)
    mb.quad(P(o1, zd, 0), P(o1, zd, -rec), P(o1, zo, -rec), P(o1, zo, 0), fr)
    leaf = opts['leaf']
    mb.quad(P(o0, zd, -rec), P(o1, zd, -rec), P(o1, zo, -rec), P(o0, zo, -rec), leaf)
    leaves = ((o0, sc), (sc, o1)) if w > 1.3 else ((o0, o1),)
    dd = -rec + 0.012
    for k, (l0, l1) in enumerate(leaves):
        hinge_left = k == 0
        sl = l1 - 0.2 if hinge_left else l0 + 0.2                          # the latch side
        # a narrow wired light at eye height, the lever under it
        p0, p1 = (sl - 0.2, sl - 0.04) if hinge_left else (sl + 0.04, sl + 0.2)
        mb.quad(P(p0, zd + 1.3, dd), P(p1, zd + 1.3, dd), P(p1, zd + 1.82, dd), P(p0, zd + 1.82, dd), 'glass',
                uvs=[windows.DARK] * 4)
        h0 = sl + (0.04 if hinge_left else -0.16)
        windows.box(mb, P, h0, h0 + 0.12, zd + 0.98, zd + 1.02, -rec, -rec + 0.05, 'frame_silver', skip=('back',))
        if opts.get('louvre'):
            windows.grille(mb, P, l0 + 0.18, l1 - 0.18, zd + 0.15, zd + 0.42, -rec + 0.004, 4)
    if len(leaves) > 1:                                                    # the meeting stiles
        mb.quad(P(sc - 0.025, zd, dd), P(sc + 0.025, zd, dd), P(sc + 0.025, zo, dd), P(sc - 0.025, zo, dd), fr)
    ang = math.atan2(t.y, t.x)
    mb.box(P(sc, zo + 0.16, 0.45), (w + 0.8, 0.9, 0.1), 'concrete', rotz=ang)        # the canopy
    o = P(sc, zd, 0)
    mb.xf = Matrix.Translation(Vector(o)) @ Matrix.Rotation(ang, 4, 'Z')
    n0 = len(LM.ENTRANCES)
    LM.stair_flight(mb, 0.0, 0.0, w + 0.5, 0.0, landing=1.0, tread=0.3, flare=0.0, gfn=LM.local_ground(mb), mat='concrete',
                    maxrise=0.18)
    del LM.ENTRANCES[n0:]              # (not a start place, and nothing is planted here: back_pick_door)
    COUNT['doors'] += 1
    mb.xf = Matrix.Identity(4)


# ----------------------------------------------------------------------------- pipes
def back_tube(mb, p0, p1, r, mat, seg=5):
    """a round tube from p0 to p1 (no caps), smooth"""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    u = ax.cross(Vector((0, 0, 1)))
    u = u.normalized() if u.length > 1e-4 else Vector((1, 0, 0))
    v = ax.cross(u)
    ring = [(u * math.cos(2 * math.pi * k / seg) + v * math.sin(2 * math.pi * k / seg)) * r for k in range(seg)]
    tag = 'bt%d' % len(mb.faces)
    for k in range(seg):
        j = (k + 1) % seg
        mb.face([tuple(p0 + ring[k]), tuple(p0 + ring[j]), tuple(p1 + ring[j]), tuple(p1 + ring[k])], mat, smooth=tag)


def back_hopper(mb, P, sc, z, pd, mat):
    """a rain-water head under a parapet outlet: a box against the wall tapering to the pipe (top at z)"""
    a0, a1, d1 = sc - 0.13, sc + 0.13, pd + 0.1
    b0, b1, e0, e1 = sc - 0.065, sc + 0.065, pd - 0.065, pd + 0.065
    zb = z - 0.24
    mb.quad(P(b0, zb, e1), P(b1, zb, e1), P(a1, z, d1), P(a0, z, d1), mat)                    # front
    mb.quad(P(a0, z, 0), P(b0, zb, e0), P(b0, zb, e1), P(a0, z, d1), mat)                     # left
    mb.quad(P(a1, z, d1), P(b1, zb, e1), P(b1, zb, e0), P(a1, z, 0), mat)                     # right
    mb.quad(P(a0, z, d1), P(a1, z, d1), P(a1, z, 0), P(a0, z, 0), mat)                        # top
    return zb


def back_pipe(mb, e, s, pd, z_top, mat, neck=None, clips=True):
    """A downpipe on the wall of edge e at s, its axis pd off the wall, from z_top down to a shoe over the ground;
    neck: (d, z) of an eaves gutter's outlet, joined by a swan neck.  One to three clips to the wall."""
    P = e.P
    g = ground_top(*e.xy(s, pd + 0.1))
    if g > z_top - 2.2:
        return False
    if neck:
        back_tube(mb, P(s, neck[1], neck[0]), P(s, z_top, pd), PIPE_R, mat)
    else:
        z_top = back_hopper(mb, P, s, z_top, pd, mat) + 0.03
    zf = g + 0.24 if clips else g - 0.1         # (the town's run into the ground: no shoe, no clips)
    back_tube(mb, P(s, zf, pd), P(s, z_top, pd), PIPE_R, mat)
    if clips:
        back_tube(mb, P(s, g + 0.07, pd + 0.16), P(s, zf + 0.03, pd), PIPE_R, mat)           # the shoe
    H = z_top - zf
    k = (1 if H < 9 else 2 if H < 20 else 3) if clips else 0
    r = PIPE_R + 0.012
    for j in range(k):
        z = zf + H * (j + 0.5) / k
        windows.box(mb, P, s - r, s + r, z - 0.02, z + 0.02, 0.0, pd + r, mat, skip=('back', 'top', 'bottom'))
    return True


def back_candidates(plan):
    """where a pipe may stand: on the piers (bay lines) and by the corners, clear of the next building, the front
    door and buried walls.  -> [(perimeter coordinate, edge, s, corner?)]"""
    out, u0 = [], 0.0
    gym = plan.style == 'gym'
    for e in plan.edges:
        ss = []
        if not (gym and e.i % 2):
            if e.bays:
                pier = 2 * e.half
                c = min(0.35, e.half / 2)
                if e.half >= 0.2:
                    ss += [(c, True), (e.L - c, True)]
                if pier >= (0.22 if plan.shop else 0.3) and e is not plan.front:
                    ss += [(k * e.bw, False) for k in range(1, e.bays)]
            elif e.L >= 1.2:
                ss.append((e.L / 2, False))
        for s, corner in ss:
            if e.door and abs(s - e.door[0]) < e.door[1]:
                continue
            if e.back and e.back['s0'] - 0.4 < s < e.back['s1'] + 0.4:
                continue
            if back_blocked(plan, e, s, 0.5) or back_blocked(plan, e, s, 1.4):
                continue
            if ground_top(*e.xy(s, 0.2)) > e.top - 2.5:
                continue
            out.append((u0 + s, e, s, corner))
        u0 += e.L
    return out, u0


def back_pipes(mb, plan):
    """The downpipes: spread evenly round the walls, on the town's houses one or two at corners."""
    cand, per = back_candidates(plan)
    if not cand:
        return 0
    rnd = plan.rnd
    pitched = plan.pitched
    if plan.town:
        cc = [c for c in cand if c[3]] or cand
        N = 1 if per < 60 else 2
    else:
        cc = cand
        N = max(2, min(12, int(round(sum(e.L for e in {c[1].i: c[1] for c in cand}.values()) / PIPE_EVERY))))
    pd = PIPE_OFF + (0.1 if plan.st.get('band') else 0.0)
    done = []
    for j in range(N):
        target = (plan.seed + j / N) * per
        best = None
        for c in cc:
            dist = abs(c[0] - target)
            dist = min(dist, per - dist) - (1.5 if c[3] else 0.0)
            if any(min(abs(c[0] - q[0]), per - abs(c[0] - q[0])) < 5.0 for q in done):
                continue
            if best is None or dist < best[0]:
                best = (dist, c)
        if best is None:
            break
        done.append(best[1])
    k = 0
    for _, e, s, _ in done:
        if pitched:
            ze = e.top                           # the eaves: the gutter's outlet, a swan neck back to the wall
            k += back_pipe(mb, e, s, pd, ze - 0.62, plan.pipe_mat, neck=(EAVE + 0.07, ze - 0.13))
        else:
            k += back_pipe(mb, e, s, pd, e.top - 0.05, plan.pipe_mat, clips=not plan.town)
    return k


def back_gutters(mb, plan):
    """the eaves gutters of a hip roof: a half-round trough hung on the fascia along every side (three faces, smooth
    over their shared edges: rounded, and left whole by the bake)"""
    for e in plan.edges:
        o, P = EAVE + 0.14, e.P
        z0, z1, s0, s1 = e.top - 0.13, e.top - 0.02, -EAVE - 0.14, e.L + EAVE + 0.14
        tag = 'gt%d' % len(mb.faces)
        mb.quad(P(s0, z0, EAVE), P(s1, z0, EAVE), P(s1, z0, o), P(s0, z0, o), plan.pipe_mat, smooth=tag)       # bottom
        mb.quad(P(s0, z0, o), P(s1, z0, o), P(s1, z1, o), P(s0, z1, o), plan.pipe_mat, smooth=tag)             # front
        mb.quad(P(s0, z1, o), P(s1, z1, o), P(s1, z1, EAVE), P(s0, z1, EAVE), plan.pipe_mat, smooth=tag)       # top


# ----------------------------------------------------------------------------- the foot of the wall
def back_feet(plan, e, hp):
    """The plinth of edge e as level runs [s0, s1, top, bottom, highest ground], stepping at the bay lines with the
    ground: the halls' floors are at the lowest ground round them, so on these slopes most walls run into the ground
    well over the floor.  A bay's plinth stands at least 0.2 m over its highest ground and under the sill of its
    lowest window above ground (generic.wall_edge leaves a buried window out); it keeps the last bay's height while
    that still fits, else takes the next 0.3 m course."""
    z0 = plan.z0
    if e.bays:
        cuts = [k * e.bw for k in range(e.bays + 1)]
    else:
        m = max(1, int(round(e.L / 3.0)))
        cuts = [e.L * j / m for j in range(m + 1)]
    runs, last = [], None
    for s0, s1 in zip(cuts, cuts[1:]):
        gs = [ground_top(*e.xy(s0 + (s1 - s0) * u, 0.25)) for u in (0.02, 0.25, 0.5, 0.75, 0.98)]
        gmin, gmax = min(gs), max(gs)
        hi = gmin + (1.4 if plan.town else 1.1)
        if e.bays:
            g = ground(*e.xy((s0 + s1) / 2, 0.6))
            for f in range(e.nf):
                sill = 0.25 if plan.shop and f == 0 else plan.st['sill']
                if g <= z0 + f * plan.fh + sill - 0.15:
                    hi = min(hi, z0 + f * plan.fh + sill - 0.13)
                    break
        lo = gmax + (0.1 if plan.town else 0.2)
        if hi < gmin + 0.12 or back_blocked(plan, e, (s0 + s1) / 2, 0.45):
            last = None
            continue
        if last is not None and lo <= last <= hi:
            top = last
        else:
            top = min(hi, z0 + hp + max(0, math.ceil((lo - z0 - hp) / 0.3 - 1e-6)) * 0.3)
        if runs and last is not None and abs(top - last) < 1e-6 and abs(runs[-1][1] - s0) < 1e-6:
            runs[-1][1] = s1
            runs[-1][3] = min(runs[-1][3], gmin - 0.4)
            runs[-1][4] = max(runs[-1][4], gmax)
        else:
            runs.append([s0, s1, top, gmin - 0.4, gmax])
        last = top
    gaps = list(e.gaps)
    if e.back:
        sc = (e.back['s0'] + e.back['s1']) / 2
        gaps.append((sc - e.back['clear'], sc + e.back['clear']))
    for g0, g1 in gaps:
        cut = []
        for r in runs:
            if g1 <= r[0] or g0 >= r[1]:
                cut.append(r)
                continue
            if g0 - r[0] > 0.15:
                cut.append([r[0], g0] + r[2:])
            if r[1] - g1 > 0.15:
                cut.append([g1, r[1]] + r[2:])
        runs = cut
    return runs


def back_plinth(mb, plan, zones):
    """The band at the foot of the walls (zones: this hall's entrance flights, generic.DOORS), and its louvred vents."""
    mat, hp = plan.plinth
    for e in plan.edges:
        e.gaps = []
    if plan.front is not None:
        e = plan.front
        music = plan.b['entry'].get('music')
        for z in zones:
            if e.n.x * z['v'][0] + e.n.y * z['v'][1] < 0.9:
                continue
            s = (Vector((z['o'][0], z['o'][1], 0)) - e.a).dot(e.t)
            hw = max(z['hw'] - 0.6, e.door[1] - (2.7 if music else 1.7) + (0.3 if plan.style == 'stone_pale' else 0.0)) + 0.03
            e.gaps.append((s - hw - (0.9 if music else 0.0), s + hw + (0.9 if music else 0.0)))   # (음악관's planters)
    for e in plan.edges:
        e.runs = back_feet(plan, e, hp) if e.L >= 0.4 else []
    # (the town's houses, seen from the campus: a plain face a little proud of the wall, no chamfer or end faces)
    c = 0.03 if plan.town else PLINTH_D
    off = offset_poly(plan.poly, c)
    n = len(plan.edges)
    same = lambda r, q: abs(r[2] - q[2]) < 1e-6
    for e in plan.edges:
        if not e.runs:
            continue
        prev, nxt = plan.edges[(e.i - 1) % n], plan.edges[(e.i + 1) % n]
        sa = (Vector((*off[e.i], 0)) - e.a).dot(e.t)
        sb = (Vector((*off[(e.i + 1) % n], 0)) - e.a).dot(e.t)
        P = e.P
        for j, r in enumerate(e.runs):
            r0, r1, zt, zb = r[:4]
            # mitred with the next wall's where they meet at one height; a face on an end that stands free or higher
            m0 = r0 < 1e-6 and prev.runs and prev.runs[-1][1] > prev.L - 1e-6 and same(prev.runs[-1], r)
            m1 = r1 > e.L - 1e-6 and nxt.runs and nxt.runs[0][0] < 1e-6 and same(nxt.runs[0], r)
            q0, q1 = (sa if m0 else r0), (sb if m1 else r1)
            COUNT['plinth_m'] += r1 - r0
            if plan.town:                  # (one face a run: flagged smooth so that the bake leaves it whole)
                mb.quad(P(q0, zb, c), P(q1, zb, c), P(q1, zt, c), P(q0, zt, c), mat, smooth='pl%d' % len(mb.faces))
                continue
            # in pieces no longer than a bay, as the walls are: the bake shades each at its corners (bake.py SPLIT)
            # the chamfer, 7 cm of it, as one face a run (flagged smooth: left whole by the bake)
            m = max(1, int(math.ceil((q1 - q0) / 3.9)))
            for i in range(m):
                a0, a1 = q0 + (q1 - q0) * i / m, q0 + (q1 - q0) * (i + 1) / m
                mb.quad(P(a0, zb, c), P(a1, zb, c), P(a1, zt - c, c), P(a0, zt - c, c), mat)
            mb.quad(P(q0, zt - c, c), P(q1, zt - c, c), P(r1, zt, 0), P(r0, zt, 0), mat, smooth='pc%d' % len(mb.faces))
            lower0 = j > 0 and abs(e.runs[j - 1][1] - r0) < 1e-6 and e.runs[j - 1][2] >= zt
            lower1 = j + 1 < len(e.runs) and abs(e.runs[j + 1][0] - r1) < 1e-6 and e.runs[j + 1][2] >= zt
            if not m0 and not lower0:
                mb.quad(P(r0, zt, 0), P(r0, zb, 0), P(r0, zb, c), P(r0, zt - c, c), mat)
            if not m1 and not lower1:
                mb.quad(P(r1, zt - c, c), P(r1, zb, c), P(r1, zb, 0), P(r1, zt, 0), mat)
        # a louvred vent in the plinth under every fourth bay of the back and side walls, where it stands high enough
        if plan.town or plan.style == 'house' or e is plan.front or not e.bays:
            continue
        for k in range(e.bays):
            if (k + e.i + int(plan.seed * 4)) % 4:
                continue
            sc = (k + 0.5) * e.bw
            r = next((r for r in e.runs if r[0] + 0.2 < sc - 0.3 and sc + 0.3 < r[1] - 0.2), None)
            if r is None:
                continue
            g = max(ground_top(*e.xy(sc + u, 0.15)) for u in (-0.3, 0.0, 0.3))
            if r[2] - g < 0.45:
                continue
            windows.grille(mb, P, sc - 0.28, sc + 0.28, g + 0.12, g + 0.36, c, 2)
            COUNT['vents'] += 1


# ----------------------------------------------------------------------------- the roof
def back_aerial(mb, plan):
    """A VHF television aerial on a mast: a boom with a reflector and five shorter elements, pointing at the Namsan
    transmitter.  On a flat roof by a corner of the parapet, on a hip roof at the ridge."""
    rnd = plan.rnd
    poly = plan.poly
    n = len(poly)
    cx, cy = sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n
    if plan.pitched:
        W = min(e.L for e in plan.edges)
        x, y = cx, cy
        z = plan.edges[0].top + (W / 2 + EAVE) * PITCH[plan.style] - 0.05
    else:
        k = rnd.randrange(n)
        x, y = cx + (poly[k][0] - cx) * 0.7, cy + (poly[k][1] - cy) * 0.7
        z = plan.zt
    h = rnd.uniform(2.2, 3.2)
    ang = NAMSAN + rnd.uniform(-0.15, 0.15)
    back_tube(mb, (x, y, z - 0.1), (x, y, z + h), 0.022, 'frame_silver', seg=4)
    fx, fy = math.cos(ang), math.sin(ang)
    a = (x - fx * 0.45, y - fy * 0.45)
    P = lambda s, zz, d=0.0: (a[0] + fx * s + fy * d, a[1] + fy * s - fx * d, zz)
    zb = z + h - 0.12
    windows.box(mb, P, 0.0, 1.15, zb - 0.012, zb + 0.012, -0.012, 0.012, 'frame_silver', skip=('left', 'right'))
    for j, (s, hl) in enumerate(((0.03, 0.62), (0.3, 0.52), (0.52, 0.47), (0.72, 0.43), (0.92, 0.4), (1.12, 0.37))):
        q = [P(s - 0.011, zb + 0.014, -hl), P(s + 0.011, zb + 0.014, -hl), P(s + 0.011, zb + 0.014, hl), P(s - 0.011, zb + 0.014, hl)]
        mb.face(q, 'frame_silver')
        mb.face(q[::-1], 'frame_silver')


def back_finish(mb, plan, zones):
    """After the walls and the roof: the plinth and its vents, the gutters and downpipes, the aerial.
    zones: the entrance flights this hall added to generic.DOORS."""
    if not plan.on:
        return
    if plan.plinth:
        back_plinth(mb, plan, zones)
    if plan.pitched:
        back_gutters(mb, plan)
    COUNT['pipes'] += back_pipes(mb, plan)
    if plan.aerial:
        back_aerial(mb, plan)
        COUNT['aerials'] += 1
