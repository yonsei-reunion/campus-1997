"""무악학사 · 북문으로 가는 길 (reference/고증/3.21_무악학사_북문.md). tools/build_campus.py 가 부른다.

    line = muak.road()                                   # 1997년 7월 항공사진의 가운데 선: s, 점, 왼쪽 법선
    muak.grade(Hn, X, Y, FIXED, line, sample0)           # 그 노면 높이로 땅을 고름(심기가 끝난 뒤, 저장 바로 앞)
    muak.takeup(paths_out)                               # OSM 의 옛 선(찻길 · 보도)이 깔던 아스팔트 · 포장
    muak.paint(line, s1)                                 # 새 찻길 · 서쪽 보도의 다각형
    muak.trees(line, trees, halls, s1)                   # 길가 나무(목록 끝에 더함)

Frame: campus metres, x east, y north.  The road runs from the bend north-east of 대우관 (road's TR_E, 77.6 m) north
over the crest (y 760) and down round the hairpin (y 892) to the fork before 북문 (62, 965).

- The line: the 2008 skyview survey's middle line (tools/roadview/muak/proposal_roads.json, +-1 m), moved left by what
  the 1997-07-28 frames show (OFF97): the middle line agrees within 0.3 m in four frames (27/15, 27/16, 26/15, 26/14)
  at s 5 - 100, 2.0 m and 1.2 m left of the survey's; 2.7 m at s 125 - 170 and 0.8 m at s 188 - 200 (two frames, the rest
  under the crowns); 0.5 m at s 282 - 298.  OSM's line is 2 - 3 m east of the survey's.
- Its width: 6.0 m between the kerbs (the photos' east kerb and west edge at s 30 - 100), the walk on the west 2.5 m.
- Its height (Z97): the road surface measured on the photos (corr >= 0.7), the bend as the road there has it.
Nothing here draws from build_campus.py's `rng`: random.Random(15991) for the trees.
"""
# (every absolute height written in this file's code is above sea level, 해발: datum.up · up3 · up_at · up_plane take it
# up to the working datum the ground is laid on, 해발 + tilt, where it is read: tools/datum.py.  The heights quoted
# in the comments are 해발 too)
import json, math, os, random
import numpy as np
import datum
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union, nearest_points
import shapely

import north97

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
_P = json.load(open(os.path.join(ROOT, 'tools/roadview/muak/proposal_roads.json')))
# the 1997 middle line left of the survey's (the survey's s, m): measured at s 5 - 100, 125 - 200, 282 - 298 and s 500 -
# 600 (26/14: the road between +4 and -1); in between and past them eased
OFF97 = [(0, 2.0), (50, 2.0), (60, 1.2), (100, 1.2), (125, 2.7), (170, 2.7), (190, 0.8), (200, 0.8), (290, 0.5),
         (420, 0.5), (500, 1.5), (600, 1.5), (630, 0.0)]
HALF = 3.0                      # half the carriageway
WALK = (3.25, 5.75)             # the west walk, left of the middle line (s 8 on: past the corner's mouth)
# the road's surface (the survey's s, m; 해발 at that s of the line, road()): the 1997 frames (corr >= 0.7), the bend
# north-east of 대우관 as the east road has it (reference/고증/3.6.2), s 195 the drive into the yard east of the crest
# (four frames, 0.91 - 0.96).  Under the crowns the 1:5000 survey's spot heights on the road + T (reference/고증/3.21
# 「길의 높이」): s 127 (223.9, 691.9), s 225 (241.6, 787.8, on its east verge), s 284 (248.8, 845.6 · 246.7, 847.2, with
# the frames' 91.2 - 91.5 there), s 488 (116.2, 836.8).  From the hairpin to the fork one fall of 10 - 12 %: the frames'
# 77 - 79 m at s 430 - 462 was the crowns over the road (the pairs that see the road under them: 75.6 at s 427, 73.1
# at s 448, 70.6 at s 469, 68.7 at s 483, within 0.8 m of the survey's contours)
Z97 = datum.up_at([(-14.0, 77.46), (10.0, 80.73), (50.0, 86.26), (90.0, 90.56), (127.0, 93.78), (195.0, 95.46), (225.0, 94.15),
       (284.0, 90.56), (301.0, 90.05), (329.0, 86.48), (343.0, 84.73), (413.0, 77.05), (448.0, 73.04), (488.0, 68.07),
       (525.0, 64.28), (558.0, 60.87), (602.0, 55.95), (630.0, 53.23)],
                  [(189.3, 563.9), (207.3, 579.4), (223.5, 613.7), (224.2, 653.6), (222.3, 690.5), (231.7, 758.1),
                   (237.8, 787.4), (247.2, 844.9), (241.5, 860.8), (224.9, 882.9), (213.5, 890.3), (178.5, 834.0),
                   (149.6, 815.6), (115.9, 835.5), (99.3, 868.8), (86.1, 899.1), (69.5, 939.8), (61.8, 964.8)])
S_GRID = 238.0                  # where the line leaves the 5 m grid (y 800)


def _pchip(xs, ys, x):
    from scipy.interpolate import PchipInterpolator
    return PchipInterpolator(np.asarray(xs, float), np.asarray(ys, float), extrapolate=True)(x)


def road(key='main_corner_to_junction', off=OFF97, s0=-14.0):
    """the middle line every metre from s0 (before the survey's first point, along its first leg) to its end:
    dict(s, p (n, 2), n (n, 2) left normals, ls)"""
    pts = np.array(_P[key], float)
    for _ in range(2):                                   # (Chaikin: the survey's corners rounded)
        q = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            q += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        pts = np.array(q + [pts[-1]])
    L0 = LineString([tuple(p) for p in pts])
    d0 = (pts[1] - pts[0]) / np.linalg.norm(pts[1] - pts[0])
    ss = np.arange(s0, L0.length + 1e-6, 1.0)
    P = np.array([pts[0] + d0 * s if s < 0 else np.array(L0.interpolate(s).coords[0]) for s in ss])
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    N = np.stack([-T[:, 1], T[:, 0]], 1)
    from scipy import ndimage
    o = ndimage.gaussian_filter1d(np.interp(ss, *zip(*off)), 6.0, mode='nearest')
    P = P + N * o[:, None]
    for _ in range(4):
        P[1:-1] = (P[:-2] + 2 * P[1:-1] + P[2:]) / 4
    ls = LineString([tuple(p) for p in P])
    # every metre along the moved line again (s: still the survey's, as the measurements name it)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    N = np.stack([-T[:, 1], T[:, 0]], 1)
    return dict(s=ss, p=P, n=N, ls=ls, z=_pchip(*zip(*Z97), ss))


def at(line, s, off=0.0):
    k = float(np.clip(s - line['s'][0], 0, len(line['s']) - 1))
    i = min(int(k), len(line['s']) - 2)
    f = k - i
    p = line['p'][i] * (1 - f) + line['p'][i + 1] * f
    n = line['n'][i] * (1 - f) + line['n'][i + 1] * f
    return p + n / np.linalg.norm(n) * off


def strip(line, s0, s1, o0, o1, step=1.0):
    """the polygon between offsets o0 .. o1 (left +) from s0 to s1"""
    ss = list(np.arange(s0, s1, step)) + [s1]
    return Polygon([tuple(at(line, s, o0)) for s in ss] + [tuple(at(line, s, o1)) for s in ss[::-1]]).buffer(0)


def project(line, x, y):
    """(s, offset left +) of points (arrays) off the line"""
    pts = shapely.points(np.stack([np.ravel(x), np.ravel(y)], 1))
    d = shapely.line_locate_point(line['ls'], pts)
    s = line['s'][0] + d
    k = np.clip(np.round(d).astype(int), 0, len(line['s']) - 1)
    v = np.stack([np.ravel(x), np.ravel(y)], 1) - line['p'][k]
    # (the offset's size is the distance to the line: past its ends the side's component alone would be small)
    o = np.where((v * line['n'][k]).sum(1) >= 0, 1.0, -1.0) * shapely.distance(line['ls'], pts)
    return s.reshape(np.shape(x)), o.reshape(np.shape(x))


def grade(Hn, X, Y, FIXED, line, s1=S_GRID + 12.0, ramp=(0.0, 18.0)):
    """the road's bed on its own profile, level across, the walk 12 cm over it; eased into the ground over 10 m past
    the walk and the east verge; from nothing at the corner (ramp: the east road's bend and the bank by 대우관's east
    wing stay) to whole 18 m on.  Nodes another rule set (FIXED) stay.  Returns the nodes it took (to be FIXED)."""
    m = (X > line['p'][:, 0].min() - 20) & (X < line['p'][:, 0].max() + 20) & (Y > line['p'][:, 1].min() - 20) & \
        (Y < line['p'][:, 1].max() + 20)
    sx, ox = project(line, X[m], Y[m])
    zs = np.interp(sx, line['s'], line['z']) + np.where((ox > WALK[0]) & (ox < WALK[1] + 0.5), 0.12, 0.0)
    a = np.abs(ox)
    core = np.where(ox > 0, WALK[1] + 0.5, HALF + 1.0)
    w = np.clip(1.0 - (a - core) / 10.0, 0, 1)
    w = w * w * (3 - 2 * w)
    r = np.clip((sx - ramp[0]) / (ramp[1] - ramp[0]), 0, 1)
    r = r * r * (3 - 2 * r)
    e = np.clip((s1 - sx) / 6.0, 0, 1)
    w = w * r * e * (sx > line['s'][0] + 0.5)
    w[FIXED[m]] = 0.0
    h0 = Hn[m]
    Hn[m] = h0 * (1 - w) + zs * w
    took = np.zeros(X.shape, bool)
    took[m] = (w > 0.999) & (a <= core)
    return took, int((w > 0).sum()), float(np.abs(Hn[m] - h0).max())


def takeup(paths_out):
    """OSM's road north of the corner and its walk west of it: (their lines, the polygons their paving covered)"""
    old = []
    for p_ in paths_out:
        L = LineString(p_['pts'])
        if p_['kind'] == 'service' and math.dist(p_['pts'][-1], (226.3, 709.9)) < 1.0:
            cut = L.intersection(Polygon([(150, 573.5), (300, 573.5), (300, 900), (150, 900)]))
            old.append((cut, 6.0))
        elif p_['kind'] == 'footway' and math.dist(p_['pts'][0], (223.4, 725.9)) < 1.0:
            old.append((L, p_['w']))
    return old


def paint(line, s1):
    """the carriageway (from 6 m back into the corner's asphalt) and the west walk (past the corner's mouth)"""
    return strip(line, -6.0, s1, -HALF, HALF), strip(line, 8.0, s1, WALK[0], WALK[1])


def trees(line, trees_, halls, s0=14.0, s1=S_GRID, seed=15991):
    """the closed crowns over the road (1997 frames: s 0 - 300 is under them): a row either side, behind the walk on
    the west (8 m) and on the bank on the east (5 m), about 9 m apart, oaks and zelkovas (the species are not known)"""
    rd = random.Random(seed)
    out = []
    pts0 = [(t[1], t[2]) for t in trees_]
    for side, o in ((1, 8.0), (-1, -5.0)):
        s = s0 + rd.uniform(0, 4)
        while s < s1:
            q = at(line, s, o + rd.uniform(-0.8, 0.8))
            sp = 'oak' if rd.random() < 0.6 else 'zelkova'
            sc, rot = round(rd.uniform(0.85, 1.15), 2), round(rd.uniform(0, 6.28), 2)
            s += rd.uniform(7.5, 11.0)
            if halls.contains(Point(*q)) or any(math.dist(q, p) < 3.5 for p in pts0 + [(t[1], t[2]) for t in out]):
                continue
            out.append([sp, round(float(q[0]), 2), round(float(q[1]), 2), sc, rot])
    return out


# ----------------------------------------------------------------------------- the patch north of the grid
# The near terrain's 5 m patch north of the grid (as tools/sinchon_rotary.py's SOUTH): x -100 .. 400, y 800 .. 1300, its
# bottom row the grid's top row.  Its heights are tools/north97.py's GRID (the 1:5000 survey's surface + T, nudged to
# the 1997 frames where they see the ground; past the survey sheet's north edge, y 1215, the elevation model): the
# model alone stood 3 - 5 m high round 북문 and 2.4 - 4.4 m low round 무악학사 (reference/고증/3.21 「땅의 높이」).  The
# roads' beds and the courts' pads are levelled on it.
NORTH = dict(x0=-100.0, y0=800.0, step=5.0, nx=101, ny=101)      # (on the far ring's 100 m cells: its hole)
NSPLAT = dict(x0=-60.0, y0=800.0, x1=340.0, y1=1280.0, res=0.5)     # its ground map (packed beside the town's)
_OSM = None


def osm():
    """OSM's ways north of the grid (data/raw/osm_north.json, or the survey's assets_src/handover_2026-11-12/osm_north.json)"""
    global _OSM
    if _OSM is None:
        D = []
        for p in ('data/raw/osm_north.json', 'assets_src/handover_2026-11-12/osm_north.json'):
            f = os.path.join(ROOT, p)
            if os.path.exists(f):
                D = json.load(open(f))['elements']
                break
        nodes = {e['id']: e for e in D if e['type'] == 'node'}
        lat0, lon0 = 37.5640, 126.9380
        xy = lambda la, lo: ((lo - lon0) * 111320 * math.cos(math.radians(lat0)), (la - lat0) * 110574)
        _OSM = {}
        for e in D:
            if e['type'] != 'way':
                continue
            if 'geometry' in e:
                g = [xy(p['lat'], p['lon']) for p in e['geometry']]
            else:
                g = [xy(nodes[n]['lat'], nodes[n]['lon']) for n in e.get('nodes', []) if n in nodes]
            if len(g) >= 2:
                _OSM[e['id']] = (e.get('tags', {}), g)
    return _OSM


def patch(raw, Hn, half, step, far=None, ground=None):
    """the patch from ground(X, Y) (tools/north97.py grid_z; without it the elevation model, raw(xs, ys) as
    build_campus.py makes Hn), its bottom row the grid's top row, the difference eased out over 30 m; its other three
    edges on the far ring's ground (far(x, y): the web's 100 m terrain as it draws it), eased in over 40 m, so that no
    step stands where the far ring takes over"""
    S = NORTH
    xs = S['x0'] + np.arange(S['nx']) * S['step']
    ys = S['y0'] + np.arange(-8, S['ny'] + 6) * S['step']
    if ground is not None:
        Hs = np.asarray(ground(*np.meshgrid(xs, ys[8:8 + S['ny']])), float).copy()
    else:
        Hs = raw(xs, ys)[8:8 + S['ny']].copy()
    if far is not None:
        X, Y = np.meshgrid(xs, ys[8:8 + S['ny']])
        d = np.minimum(np.minimum(X - xs[0], xs[-1] - X), ys[8 + S['ny'] - 1] - Y)
        w = np.clip(1.0 - d / 40.0, 0, 1)
        w = w * w * (3 - 2 * w)
        Hs = Hs * (1 - w) + far(X, Y) * w
    i0 = int(round((S['x0'] + half) / step))
    edge = Hn[-1, i0:i0 + S['nx']]
    f = np.clip(1.0 - np.arange(S['ny']) * S['step'] / 30.0, 0, 1)
    Hs += (edge - Hs[0])[None, :] * (f * f * (3 - 2 * f))[:, None]
    Hs[0] = edge
    return Hs


def grid_xy():
    S = NORTH
    return np.meshgrid(S['x0'] + np.arange(S['nx']) * S['step'], S['y0'] + np.arange(S['ny']) * S['step'])


def sample_n(Hs, x, y):
    from scipy import ndimage
    S = NORTH
    return float(ndimage.map_coordinates(Hs, [[(y - S['y0']) / S['step']], [(x - S['x0']) / S['step']]], order=1, mode='nearest')[0])


def in_patch(x, y):
    S = NORTH
    return S['y0'] < y <= S['y0'] + (S['ny'] - 1) * S['step'] and S['x0'] <= x <= S['x0'] + (S['nx'] - 1) * S['step']


def _line_of(pts, step=1.0):
    """a polyline resampled every metre: dict(s, p, n, ls) as road() (s from 0)"""
    ls = LineString(pts)
    ss = np.arange(0.0, ls.length + 1e-6, step)
    P = np.array([ls.interpolate(s).coords[0] for s in ss])
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    return dict(s=ss, p=P, n=np.stack([-T[:, 1], T[:, 0]], 1), ls=LineString([tuple(p) for p in P]))


def lanes():
    """the other roads of 1997 north of the grid (1997 frames: the loop through 북문 within 1 m of OSM's, the west road
    along the construction site's hoarding within 1.5 m of OSM's, the east road under its rows of trees):
    (name, line, half width, walk or None)"""
    # (through 북문 on to 연희로26길: OSM's line to (26, 919), then between the two frames as the 1997 frames have them,
    # 4 m north of OSM's end, which runs through the south frame)
    loop = _line_of([q for q in _P['gate_loop_osm'] if q[1] > 919.0] +
                    [(21.0, 916.3), (15.0, 914.9), (9.0, 914.0), (3.0, 912.3), (-6.0, 909.0)])
    west = _line_of(_P['dorm_west_osm'])
    east = _line_of(_P['dorm_east_osm'])
    return [('loop', loop, 3.25, None), ('west', west, 2.0, None), ('east', east, 2.0, None)]


LANE_SMOOTH = 8.0               # the lanes' beds: the ground along them smoothed this far (sigma, m)


def level(Hs, line, roads):
    """the roads' beds on the patch: the main road on its own profile (line['z']), the others on the ground smoothed
    along them (LANE_SMOOTH: the ground is the survey's and the frames' now, which the 1997 lanes lie on within 0.6 m
    where the frames see them) from the main road's surface where they leave it, level across; eased into the ground
    over 10 m.  The bottom row stays (the grid's).  Returns ({name: (s, z)}, the nodes the roads took)"""
    from scipy import ndimage
    X, Y = grid_xy()
    fixed = np.zeros(X.shape, bool)
    fixed[0] = True
    H0 = Hs.copy()
    out = {}
    todo = [('main', line, HALF, WALK, line['z'])]
    for nm, ln, hw, wk in roads:
        z = ndimage.gaussian_filter1d(np.array([sample_n(H0, *p) for p in ln['p']]), LANE_SMOOTH, mode='nearest')
        if line['ls'].distance(Point(*ln['p'][0])) < 8.0:
            s0, _ = project(line, np.array([ln['p'][0][0]]), np.array([ln['p'][0][1]]))
            k = np.clip(1.0 - ln['s'] / 25.0, 0, 1)
            z = z * (1 - k) + float(np.interp(s0[0], line['s'], line['z'])) * k
        todo.append((nm, ln, hw, wk, z))
    for nm, ln, hw, wk, z in todo:
        sx, ox = project(ln, X, Y)
        zs = np.interp(sx, ln['s'], z)
        a = np.abs(ox)
        core = np.where(ox > 0, wk[1] + 0.5, hw + 1.0) if wk else np.full(ox.shape, hw + 1.0)
        w = np.clip(1.0 - (a - core) / 10.0, 0, 1)
        w = w * w * (3 - 2 * w)
        w *= (sx > ln['s'][0] - 2.0) & (sx < ln['s'][-1] + 2.0)
        if nm == 'main':
            w *= sx > S_GRID - 8.0
        w[fixed] = 0.0
        Hs[:] = Hs * (1 - w) + zs * w
        fixed |= (w > 0.999) & (a <= core)
        out[nm] = (ln['s'], z)
    return out, fixed


def pads(Hs, polys, fixed, levels=None):
    """level pads (the courts, the car park): each at its level (levels: a height, or a plane as a function of x, y:
    tools/north97.py pad_levels; without one the ground's mean along its edge), eased out over 8 m"""
    X, Y = grid_xy()
    pts = shapely.points(np.stack([X.ravel(), Y.ravel()], 1))
    zs = []
    for k, poly in enumerate(polys):
        z = levels[k] if levels else float(np.mean([sample_n(Hs, *q) for q in poly.exterior.coords]))
        zz = z(X, Y) if callable(z) else z
        d = shapely.distance(poly, pts).reshape(X.shape)
        w = np.clip(1.0 - (d - 1.0) / 8.0, 0, 1)
        w = w * w * (3 - 2 * w)
        w[fixed] = 0.0
        Hs[:] = Hs * (1 - w) + zz * w
        fixed |= d <= 1.0
        zs.append(round(float(z(*poly.centroid.coords[0])) if callable(z) else z, 2))
    return zs


# ----------------------------------------------------------------------------- what stood there in July 1997
def _rect(c, ang, L, W):
    a = math.radians(ang)
    t, n = np.array([math.cos(a), math.sin(a)]), np.array([-math.sin(a), math.cos(a)])
    c = np.asarray(c, float)
    return [tuple(c + t * u + n * v) for u, v in ((-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2))]


def _shift(g, d):
    return [(x + d[0], y + d[1]) for x, y in g]


def _v(ang, v):
    """v m to the left of an axis at ang degrees"""
    a = math.radians(ang)
    return (-math.sin(a) * v, math.cos(a) * v)


# 무악학사 1 · 2학사 (1989, 1993; 지하 1 · 지상 5층): four wings along 101.8 - 102 deg, as OSM's outlines have them (centre,
# length, wall width), moved across by where the 1997 frames put each roof (eaves 12.4 - 13.5 m wide: 26/14 and 27/15,
# the near eave over the facade one frame sees and the far one against the ground the other sees, on the plane where
# the two agree): 2학사 서 3.6 m, 동 3.4 m, 1학사 서 3.1 m, 동 1.2 m west-south-west of OSM's.  Each wing's eaves where
# the frames have them (the mean of its west and east eaves, at its centre: 82.4 · 83.9, 89.8 · 89.1, 94.2 ·
# 94.1, 100.3 · 101.2): on the ground as tools/north97.py lays it they stand 14.6 - 15.5 m over each wing's high side
# (five storeys) and 16.9 - 19.8 m over its low side, where the basement is out
DORM_WINGS = [  # (id, name, centre, axis deg, length, width, shift m, eaves 해발 @ centre)
    (991001, '무악학사', (93.2, 1161.75), 101.8, 55.0, 10.8, 3.6, datum.up(93.2, 1161.75, 83.13)),
    (991002, '무악학사', (119.4, 1180.9), 101.8, 55.3, 9.4, 3.4, datum.up(119.4, 1180.9, 89.25)),
    (991003, '무악학사', (150.8, 1191.9), 102.0, 55.6, 9.7, 3.1, datum.up(150.8, 1191.9, 93.75)),
    (991004, '무악학사', (183.25, 1171.7), 102.0, 54.2, 9.9, 1.2, datum.up(183.25, 1171.7, 100.24)),
]
# the low blocks between each pair (OSM 429077776's and 429077777's middle, the 식당 1452272054, 1452272055): moved as
# the pair's mean, three and two storeys
DORM_LOW = [
    (991005, [(99.1, 1163.3), (117.5, 1167.1), (114.9, 1180.0), (95.0, 1175.9)], 3.5, 3),
    (991006, [(112.8, 1190.0), (93.0, 1185.7), (95.0, 1175.9), (114.9, 1180.0)], 3.5, 2),
    (991007, [(161.2, 1171.0), (177.3, 1174.4), (175.7, 1184.8), (157.8, 1181.0)], 2.15, 3),
    (991008, [(173.3, 1196.1), (155.4, 1192.1), (157.8, 1181.0), (175.7, 1184.8)], 2.15, 2),
]
# 3 · 4학사 (completed 1998.4.30) in July 1997: frames up, no roof (4학사's west wing 68.3 m, about 12 m over the west
# road; 3학사's 89 - 92 m, 13 - 17 m over the yard): OSM's outlines (429077772, 429077773), four and five storeys
SITE_HALLS = [(991011, 429077772, 4), (991012, 429077773, 5)]
SITE = Polygon([(70.0, 1004.0), (165.0, 1020.0), (205.0, 1024.0), (201.0, 1100.0), (190.0, 1128.0), (140.0, 1142.0),
                (101.0, 1126.0), (72.0, 1078.0)])
# 우유처리장 as the 1997 frames have it (26/14 and 27/15 on the planes of its roofs, where the two frames put an edge
# in one place: its corners within 0.9 m): a west wing along the road (roof 78.3 m: three pairs 77.6 - 78.6) and a
# hall east of it one high storey over its car park (roof 76.5 m: 76.1 - 76.6; the car park 72.2 m), both turned 3 - 7
# deg as OSM's outline is but 1 - 2.7 m north of it.  (The wing in its place in the list; the hall goes on at the
# list's end, halls(late=True), so that blender/build.py's draws for the halls after it stay.)
MILK_WEST = [(112.8, 898.7), (109.1, 862.4), (127.65, 860.05), (130.2, 879.2), (131.6, 896.7)]
MILK_EAST = [(130.2, 879.2), (154.0, 877.7), (155.4, 894.1), (131.6, 896.7)]
# the other halls the 1997 frames show (OSM's outlines):
# 농업개발원 (two storeys, a gabled roof), 대창고, the sheds east of the road at the crest, the long hall by the school,
# the hut east of the courts, and on the athletes' dormitory's site (2004) the low hall of 1997
OTHER_HALLS = [  # (id, name, style, levels, OSM id or outline, shift, hip)
    (991021, '우유처리장', 'white', 3, MILK_WEST, (0.0, 0.0), None),
    (991022, '농업개발원', 'brick', 2, 429077770, (0.0, 0.0), dict(mat='roof_slate', pitch=0.45, over=0.6, gable=True)),
    (991023, '농업개발원', 'brick', 2, 429077771, (0.0, 0.0), dict(mat='roof_slate', pitch=0.45, over=0.6, gable=True)),
    (991024, '', 'white', 2, 429077778, (0.0, 0.0), None),
    (991025, '', 'white', 1, 429077782, (0.0, 0.0), None),
    (991026, '', 'white', 1, 1358518046, (0.0, 0.0), None),
    (991027, '', 'white', 1, 1358518047, (0.0, 0.0), None),
    (991028, '', 'white', 1, 1358518048, (0.0, 0.0), None),
    (991029, '', 'white', 1, 1358518049, (0.0, 0.0), None),
    (991030, '', 'white', 3, 429077765, (0.0, 0.0), None),
    (991031, '', 'white', 1, 1358516348, (0.0, 0.0), None),
    (991032, '', 'white', 2, [(65.0, 862.0), (80.0, 862.0), (80.0, 892.0), (65.0, 892.0)], (0.0, 0.0), None),
]
# 북문 (1997 frames 26/14, 27/15, 27/16, within 0.5 m): two concrete frames along the road, each a ㄇ that the iron
# leaf folds into, their inner faces 4.7 m apart, and on the south frame's inner side a flat-roofed lodge with a cut corner
GATE_FRAMES = [[(11.8, 917.2), (16.8, 917.2), (16.8, 920.6), (11.8, 920.6)], [(13.5, 910.1), (17.5, 910.1), (17.5, 912.5), (13.5, 912.5)]]
GATE_LODGE = [(14.5, 903.5), (23.0, 903.5), (23.0, 910.0), (16.0, 910.0), (14.5, 908.5)]
ROOF_TOP = {991021: datum.up(120.0, 878.0, 78.34),       # 우유처리장's roofs (해발): the west wing @ (120, 878)
            991033: datum.up(143.0, 886.0, 76.5)}       # ... the hall east of it @ (143, 886)
COURTS = [429077768, 429077769, 429077775]
# (OSM's car parks: 1444557748 east of 우유처리장 is tools/north97.py's LOT97 as the 1997 frames have it; 1358516368
# between the two dormitories is later, a long flat roof stood there in 1997: reference/고증/3.21 「남은 한계」)
LOTS = [north97.LOT97]
APRON = Polygon([(45.0, 955.0), (60.0, 952.0), (75.0, 960.0), (73.0, 975.0), (58.0, 977.0), (46.0, 966.0)])


def halls(ground, osm_=None, late=False):
    """campus.json buildings for what stood north of the grid in 1997 (ground(x, y): the patch's or the grid's).
    late: the halls that go on at the end of the game's list instead (우유처리장's east hall)"""
    O = osm_ or osm()
    out = []

    def add(i, nm, style, lv, g, fh=None, hip=None, top=None):
        poly = shapely.geometry.polygon.orient(Polygon(g).buffer(0), 1.0)
        hs = [ground(x, y) for x, y in poly.exterior.coords]
        b = dict(id=i, name=nm, style=style, levels=lv, base=round(min(hs), 2), top_ground=round(max(hs), 2),
                 footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]])
        fh = fh or {'white': 3.6, 'brick': 3.6}[style]
        if top is not None:                      # (the wall's top set: the storeys' height to reach it)
            fh = (top - b['base']) / lv
        b['height'] = round(lv * fh, 2)
        if abs(fh - {'white': 3.6, 'brick': 3.6}[style]) > 1e-6:
            b['fh'] = round(fh, 3)
        if hip:
            b['hip'] = hip
        out.append(b)
        return b

    for i, nm, c, ang, L, W, sh, top in DORM_WINGS:
        g = _shift(_rect(c, ang, L, W), _v(ang, sh))
        hs = [ground(x, y) for x, y in g]
        lv = max(5, int(round((top - min(hs)) / 3.1)))
        add(i, nm, 'brick', lv, g, top=top, hip=dict(mat='roof_slate', pitch=0.4, over=1.3))
    for i, g, sh, lv in DORM_LOW:
        add(i, '무악학사', 'brick', lv, _shift(g, _v(101.9, sh)), fh=3.3)
    for i, oid, lv in SITE_HALLS:
        add(i, '무악학사 3 · 4학사 (공사중)', 'white', lv, O[oid][1][:-1], fh=3.1)
    for i, nm, style, lv, src, sh, hip in OTHER_HALLS:
        g = O[src][1][:-1] if isinstance(src, int) else src
        add(i, nm, style, lv, _shift(g, sh), hip=hip, top=ROOF_TOP.get(i))
    for k, g in enumerate(GATE_FRAMES):
        add(991041 + k, '북문' if k == 0 else '', 'white', 1, g, fh=3.3)
    add(991043, '', 'white', 1, GATE_LODGE, fh=3.2)
    if late:
        out[:] = []
        add(991033, '우유처리장', 'white', 1, MILK_EAST, top=ROOF_TOP[991033])
    return out


def poly_rng(b, osm_=None):
    """a hall's outline as the rows of trees were first decided on: 우유처리장's was OSM's, 1.6 m west (the 1997 frames'
    own outline since; a tree's place in the list picks its model in the web, so none is dropped for it)"""
    if b['id'] == 991021:
        return Polygon(_shift((osm_ or osm())[429077767][1][:-1], (-1.6, 0.0)))
    return Polygon(b['footprint'])


def houses(ground, taken, rd, osm_=None):
    """연희동's houses inside the patch west of the campus (OSM's outlines without a name), city blocks of two to four
    storeys; none where the 1997 roads or halls stand"""
    O = osm_ or osm()
    out = []
    for oid, (t, g) in sorted(O.items()):
        if 'building' not in t or t.get('name') or len(g) < 4:
            continue
        p = Polygon(g).buffer(0)
        c = p.centroid
        if not in_patch(c.x, c.y) or c.x > 45.0 or c.y > 1270 or p.area < 30 or p.intersects(taken):
            continue
        poly = shapely.geometry.polygon.orient(p.simplify(0.3), 1.0)
        hs = [ground(x, y) for x, y in poly.exterior.coords]
        lv = rd.choice((2, 2, 3, 3, 4))
        out.append(dict(id=992000 + len(out), name='', style='city', levels=lv, height=round(lv * 3.0, 2), base=round(min(hs), 2),
                        top_ground=round(max(hs), 2), footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]]))
    return out


def ground_map(line, roads, hall_polys):
    """the patch's ground map: {asphalt, pavers, dirt, woods} polygons"""
    O = osm()
    rd = [strip(line, S_GRID - 6.0, line['s'][-1] - 0.5, -HALF, HALF), strip(line, S_GRID - 6.0, 300.0, WALK[0], WALK[1])]
    asph = [rd[0], APRON] + [ln['ls'].buffer(hw, cap_style='flat') for _, ln, hw, _ in roads]
    asph += LOTS
    asph += [LineString(g).buffer(2.5) for t, g in O.values() if t.get('highway') == 'residential' and any(in_patch(*q) for q in g)]
    courts = [Polygon(O[i][1]).buffer(0) for i in COURTS]
    asph_u = unary_union(asph)
    pav = unary_union([rd[1]]).difference(asph_u)
    dirt = unary_union(courts + [SITE]).difference(asph_u)
    wood = unary_union([Polygon(g).buffer(0) for t, g in O.values() if (t.get('landuse') == 'forest' or t.get('natural') == 'wood')
                        and len(g) > 3] + [Polygon([(200, 800), (340, 800), (340, 1280), (200, 1280)]),
                                           Polygon([(140, 800), (260, 800), (260, 905), (140, 905)])])
    wood = wood.difference(unary_union([asph_u.buffer(1.5), pav.buffer(1.0), dirt.buffer(2.0), unary_union(hall_polys).buffer(3.0)]))
    return dict(asphalt=asph_u, pavers=pav, dirt=dirt, woods=wood, courts=courts)


def draw_map(gm, k=4):
    """the patch's ground map as an RGB array (rows north first): R asphalt, G paving, B dirt 255 / the woods' floor 170
    (as build_campus.py's splat), each drawn at k times and averaged"""
    from PIL import Image, ImageDraw
    S = NSPLAT
    W, H = int(round((S['x1'] - S['x0']) / S['res'])), int(round((S['y1'] - S['y0']) / S['res']))
    P = lambda x, y: ((x - S['x0']) / S['res'] * k, (S['y1'] - y) / S['res'] * k)
    out = {}
    for layer in ('asphalt', 'pavers', 'dirt', 'woods'):
        im = Image.new('L', (W * k, H * k), 0)
        d = ImageDraw.Draw(im)
        g = gm[layer]
        for pg in (g.geoms if hasattr(g, 'geoms') else [g]):
            if pg.geom_type != 'Polygon' or pg.is_empty:
                continue
            d.polygon([P(x, y) for x, y in pg.exterior.coords], fill=255)
            for h in pg.interiors:
                d.polygon([P(x, y) for x, y in h.coords], fill=0)
        out[layer] = np.array(im, np.float32).reshape(H, k, W, k).mean(axis=(1, 3))
    a = out['asphalt']
    p = np.minimum(out['pavers'], 255.0 - a)
    b = np.minimum(np.maximum(out['dirt'], out['woods'] * (170.0 / 255.0)), 255.0 - a - p)
    return np.stack([a, p, np.clip(b, 0, 255)], -1)


def pack(town_png, rgb, gutter=8):
    """the patch's map packed beside the town's in one texture (the terrain's shader samples one map for both: no new
    texture unit); returns campus.json's tsplat additions"""
    from PIL import Image
    T = np.array(Image.open(town_png).convert('RGB'), np.uint8)
    h = max(T.shape[0], rgb.shape[0])
    W = T.shape[1] + gutter + rgb.shape[1]
    A = np.zeros((h, W, 3), np.uint8)
    A[:T.shape[0], :T.shape[1]] = T
    A[:T.shape[0], T.shape[1]:T.shape[1] + gutter // 2] = T[:, -1:]
    n = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
    x0 = T.shape[1] + gutter
    A[:n.shape[0], x0:] = n
    A[:n.shape[0], x0 - gutter // 2:x0] = n[:, :1]
    A[n.shape[0]:, x0:] = n[-1:]
    Image.fromarray(A, 'RGB').save(town_png, optimize=True)
    return dict(atlas=[round(T.shape[1] / W, 6), round(T.shape[0] / h, 6), round(x0 / W, 6), round(n.shape[1] / W, 6),
                       round(n.shape[0] / h, 6)], north=[NSPLAT['x0'], NSPLAT['y0'], NSPLAT['x1'], NSPLAT['y1']])


def woods_strip(line, halls):
    """the wood the road climbs through inside the grid (1997 frames: closed crowns either side from the corner to the
    crest; OSM's wood east of it): 45 m either side from s 30 to the grid's edge, off the road, the walk and the halls"""
    s0, s1 = 30.0, S_GRID
    band = strip(line, s0, s1, -45.0, 45.0)
    clear = strip(line, s0 - 30.0, s1 + 6.0, -HALF - 1.5, WALK[1] + 1.0)
    return band.intersection(Polygon([(150, 590), (330, 590), (330, 800), (150, 800)])).difference(clear).difference(halls)


# the wooded ridge the road crosses, west of the strip above (1997 frames: closed crowns from 서울외국인학교's yards at
# y 690 to 대창고 and the long hall by the school).  Lawn in the game, out of sight until tools/north97.py raised the
# ridge 5 - 13 m to the survey's height: it stands behind 대우관 now
RIDGE = Polygon([(-28.0, 692.0), (150.0, 692.0), (178.0, 700.0), (185.0, 800.0), (-28.0, 800.0)])


def woods_ridge(strip, halls, osm_=None):
    """RIDGE off the strip along the road (woods_strip), the game's halls and this module's own (not in the game's
    list yet when the ground is painted)"""
    O = osm_ or osm()
    own = unary_union([Polygon(_shift(O[src][1][:-1] if isinstance(src, int) else src, sh)).buffer(0)
                       for _, _, _, _, src, sh, _ in OTHER_HALLS]).buffer(4.0)
    return RIDGE.difference(strip.buffer(2.0)).difference(halls).difference(own)


def woods_fill(poly, trees_, seed=15994, spacing=10.0):
    """trees on a jittered lattice in poly (oaks, pines, zelkovas, maples as the campus's woods), none within 4 m of a
    tree already there"""
    rd = random.Random(seed)
    from scipy.spatial import cKDTree
    have = cKDTree(np.array([(t[1], t[2]) for t in trees_])) if trees_ else None
    x0, y0, x1, y1 = poly.bounds
    out = []
    shapely.prepare(poly)
    for y in np.arange(y0, y1, spacing):
        for x in np.arange(x0, x1, spacing):
            q = (x + rd.uniform(-0.4, 0.4) * spacing, y + rd.uniform(-0.4, 0.4) * spacing)
            r = rd.random()
            sp = 'oak' if r < 0.5 else 'pine' if r < 0.75 else 'zelkova' if r < 0.9 else 'maple'
            sc, rot = round(rd.uniform(0.8, 1.2), 2), round(rd.uniform(0, 6.28), 2)
            if not shapely.contains_xy(poly, *q):
                continue
            if have is not None and have.query(q)[0] < 4.0:
                continue
            out.append([sp, round(float(q[0]), 2), round(float(q[1]), 2), sc, rot])
    return out


def trees_n(line, roads, taken, trees_, seed=15992):
    """the rows over the roads north of the grid: the main road's on to the fork (as trees() in the grid), the east
    road's (metasequoias in 2008-2010; the 1997 frames: a closed row), the west road's along the boundary (1997: a row
    of crowns west of it)"""
    rd = random.Random(seed)
    out = trees(line, trees_, taken, s0=S_GRID + 2.0, s1=line['s'][-1] - 12.0, seed=seed)
    pts0 = [(t[1], t[2]) for t in trees_ + out]
    for nm, ln, hw, _ in roads:
        rows = {'east': ((hw + 2.0, 'metasequoia'), (-hw - 2.0, 'metasequoia')), 'west': ((hw + 2.5, 'zelkova'),)}.get(nm, ())
        for o, sp in rows:
            s = 6.0 + rd.uniform(0, 3)
            while s < ln['s'][-1] - 6.0:
                k = int(s)
                q = ln['p'][k] + ln['n'][k] * (o + rd.uniform(-0.4, 0.4))
                sc, rot = round(rd.uniform(0.85, 1.15), 2), round(rd.uniform(0, 6.28), 2)
                s += rd.uniform(6.0, 8.0) if sp == 'metasequoia' else rd.uniform(7.5, 10.0)
                if not in_patch(*q) or taken.contains(Point(*q)) or any(math.dist(q, p) < 3.0 for p in pts0):
                    continue
                out.append([sp, round(float(q[0]), 2), round(float(q[1]), 2), sc, rot])
                pts0.append(tuple(q))
    return out
