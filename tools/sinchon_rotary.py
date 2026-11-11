"""신촌 로터리: 굴다리에서 연세로를 따라 신촌 로터리(신촌오거리)까지 (reference/고증/4.10_신촌_로터리.md).
tools/build_campus.py 가 부른다.

    Hs = sinchon_rotary.patch(raw, Hn, half, step)          # the near terrain's patch south of the 5 m grid
    geo = sinchon_rotary.streets(town_plan)                   # 연세로 and the five-way junction: carriageways, walks
    sinchon_rotary.level(Hn, Hs, half, step, geo)             # their beds levelled across, smoothed along
    ext = sinchon_rotary.layout(geo, town, extras, ground)    # after gate_town.layout: what campus.json gains

Frame: campus metres, x east, y north.  The 5 m grid of the campus ends at y -800; the junction (y -975) and the
streets round it stand on a patch of its own (SOUTH) laid against the grid's south edge, from the same elevation
model the same way.  Nothing here draws from build_campus.py's `rng` or gate_town's stream: random.Random(4802).

Where things stand (고증 4.10):
- The streets' middle lines are OSM's (data/raw/osm_rotary.json, tools/fetch_rotary_osm.py): 연세로 as one line, the
  others the middle between their two carriageways.  Today's 신촌로 has its buses in the middle and 연세로 is a
  transit mall (2014); the 1997 widths and lane counts are reckoned, not measured (남은 한계).
- The shops along 연세로 stand wall to wall behind a 3.75 m walk, broken where OSM's side streets come in: near the
  junction as the 1996 photos show them, the rest from their mix, signs standing out from the walls (yro_ functions at
  the end); the corners of the junction carry OSM's big outlines.
"""
import json, math, os, random
import numpy as np
from scipy import ndimage
from shapely.geometry import Polygon, LineString, Point, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
import shapely
from PIL import Image, ImageDraw
import gate_town as gt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SOUTH = dict(x0=-600.0, y0=-1200.0, step=5.0, nx=201, ny=81)          # x -600 .. 400, y -1200 .. -800
TSPLAT = dict(x0=-420.0, y0=-1200.0, x1=220.0, y1=-550.0, res=0.5)    # the town's own ground map (web/src/terrain.js)
JC = (-100.0, -975.0)          # the junction's middle
REACH = 125.0                  # how far from it the walks are open along each street

# the streets' middle lines from the junction outward (OSM: 연세로 way 383312033; the middles of 신촌로's, 서강로's
# two carriageways; 백범로 near the junction one-way today, its line).  half: the carriageway's half width, walk:
# the sidewalk's width, lanes: each way
ARMS = {
    'yonsei': dict(half=7.0, walk=5.0, lanes=2, pts=[(-101.5, -962.0), (-101.5, -945.0), (-101.0, -925.0), (-100.0, -890.0),
                                                     (-99.0, -853.0), (-98.0, -809.0), (-96.0, -753.0), (-96.0, -740.0),
                                                     (-96.0, -455.0)]),
    'sinchon_w': dict(half=14.0, walk=5.5, lanes=4, pts=[(-100.4, -971.6), (-114.8, -970.2), (-125.4, -966.7), (-139.7, -962.1),
                                                         (-153.8, -957.5), (-167.1, -951.8), (-193.8, -939.5), (-221.0, -927.0),
                                                         (-262.1, -908.1), (-303.2, -889.8), (-344.9, -871.8), (-398.4, -849.8),
                                                         (-460.0, -824.0)]),
    'sinchon_e': dict(half=14.0, walk=5.5, lanes=4, pts=[(-100.4, -971.6), (-85.7, -972.3), (-70.9, -971.3), (-56.8, -968.0),
                                                         (-44.6, -964.1), (-32.1, -958.8), (9.6, -941.6), (79.3, -913.3),
                                                         (148.8, -885.1), (217.9, -856.5), (275.6, -833.5), (320.0, -826.1),
                                                         (364.9, -822.4)]),
    'seogang': dict(half=10.0, walk=4.5, lanes=3, pts=[(-99.5, -990.0), (-117.9, -1002.2), (-141.6, -1019.5), (-165.4, -1037.3),
                                                       (-201.0, -1064.9), (-236.3, -1092.5), (-272.4, -1119.8), (-308.3, -1146.8),
                                                       (-342.3, -1174.1), (-373.3, -1206.4)]),
    'baekbeom': dict(half=7.5, walk=4.5, lanes=2, pts=[(-102.0, -985.0), (-101.0, -1011.0), (-98.0, -1028.0), (-96.0, -1044.0),
                                                       (-94.0, -1059.0), (-92.0, -1077.0), (-86.0, -1120.0), (-80.0, -1168.0),
                                                       (-75.0, -1205.0)]),
}
CORNER_R = 9.0                 # the kerbs' rounding at the corners
# the rotary's round island in the middle (서울연구원 1995 · 1996 photos from the roof of 그레이스백화점, 52142 · 52145 ·
# 52158 · 52187).  52158's camera solved from the bed's outline and two city buses (고증 4.10 「옥상 사진의 카메라」):
# the lawn's edge 15.2 m across (r 7.6 +- 0.15), the kerb's outside 7.8; the white ring of short dashes just outside
# it, r 8.4 (the ring over the bed 1.10 there, 1.14 in 52142); the bed's rings from the middle out (BED: outer radius,
# what grows there); a tall signal pole on its north edge, its mast arm out to the north-east; no lamp in the middle
ISLAND = dict(c=(-100.0, -976.0), r=7.8, ring=8.45)
BED = [(2.5, 'lawn'), (4.3, 'yellow'), (5.6, 'dark'), (6.1, 'white'), (7.6, 'lawn')]
ROT_POLE = dict(at=(-99.6, -968.9), face=325.0, reach=9.0)          # bearing the lamps face; the arm to their right
# 「연세대」 on the road north of the island (52158; the same white block in 52142 · 52145): its middle, the bearing its
# top points along (the drivers who read it head that way), letters 1.1 m across and 3.9 m long
ROT_LETTERS = dict(c=(-102.3, -964.0), up=122.0, w=1.1, h=3.9)
# 연세로's crossing between the junction and the bridge (51979: a zebra with its own signals a third of the way up)
MID_CROSS_Y = -790.0
# the junction's landmarks (the photos 52095 · 52108, 서울연구원 labels; 연세춘추, 위키백과): OSM outline (a point in
# it), storeys, wall band (blender/town.py), the sign cell of sign_sinchon2 and its height
LANDMARKS = [
    dict(name='그레이스백화점', at=(-190.0, -875.0), lv=10, wall=1, sign=12, sign_h=2.6),     # 1992, 현대 from 1998
    dict(name='그랜드백화점', at=(-176.0, -997.0), lv=10, wall=1, sign=13, sign_h=2.6),       # 1994
    dict(name='외환은행', at=(-119.0, -1054.0), lv=13, wall=2, sign=15, sign_h=2.0),          # the south wedge's tower
]
LANE_W = 3.25
# 연세로's side streets (OSM: 명물길, 연세로4길, 연세로2길 on the east; 연세로5길, 연세로 (to 신촌로), on the west):
# where its shop rows break, y of the gap's two sides
GAPS = {1: [(-695.0, -703.0), (-738.0, -747.0), (-771.0, -779.0), (-885.0, -893.0)],
        -1: [(-736.0, -746.0), (-779.0, -787.0), (-884.0, -892.0)]}
Y_ROWS = -640.0                # gate_town's rows end here; ours start
MODERN = set()                 # OSM outlines (osm_rotary.json) that are later than 1997: left out

# ---- 연세로's shop rows from y -640 to the junction, their sidewalks, wall signs and the festival's banner
# (고증 4.10 「연세로의 건물과 나무」; the yro_ functions at the end of this file).
# The sidewalk: OSM's front walls today stand 10.3 m (west) and 11.2 m (east) from 연세로's line here (medians, the
# parcels did not move when the street became a transit mall in 2014), 21.5 m wall to wall; the 1996 photo from 노고산동
# (52006) has walk : carriageway : walk = 0.20 : 0.55 : 0.25 at the junction's mouth; 서울시 2013 has 3 - 4 m walks.
# With the 14 m carriageway of four lanes kept, 3.75 m.  North of y -640 (gate_town, 4.8) OSM's walls are 23.5 m apart
# and gate_town's 5 m stays.
YRO_WALK = 3.75
YRO_OLD_WALK = 5.0             # (the walk the rows had before: the old rows are still drawn, unused, for the streams)
ARMS['yonsei']['walk'] = YRO_WALK


def _xy(lat, lon):
    return ((lon - gt.LON0) * 111320 * math.cos(math.radians(gt.LAT0)), (lat - gt.LAT0) * 110574)


class Arm(gt.Line):
    """an arm's middle line from the junction outward, its left normal at each point (gate_town.Line)"""
    def __init__(self, name, d):
        super().__init__(gt._resample(gt._chaikin(d['pts'], 2), 2.0))
        self.name = name
        self.half, self.walk, self.lanes = d['half'], d['walk'], d['lanes']

    def at(self, s):
        k = int(np.clip(np.searchsorted(self.cum, s), 1, len(self.cum) - 1))
        f = (s - self.cum[k - 1]) / max(1e-9, self.cum[k] - self.cum[k - 1])
        p = self.P[k - 1] + (self.P[k] - self.P[k - 1]) * f
        t = self.T[k - 1] + (self.T[k] - self.T[k - 1]) * f
        t = t / np.linalg.norm(t)
        return p, t, np.array([-t[1], t[0]])

    def poly(self, o0, o1, s0=0.0, s1=None):
        """the strip between offsets o0 and o1 (left +) from s0 to s1"""
        s1 = self.cum[-1] if s1 is None else s1
        ss = np.arange(s0, s1, 2.0).tolist() + [s1]
        a = [tuple(self.at(s)[0] + self.at(s)[2] * o0) for s in ss]
        b = [tuple(self.at(s)[0] + self.at(s)[2] * o1) for s in ss[::-1]]
        return Polygon(a + b).buffer(0)


def arms():
    return {k: Arm(k, d) for k, d in ARMS.items()}


# ----------------------------------------------------------------------------- the ground
def patch(raw, Hn, half, step):
    """The near terrain south of the 5 m grid: raw(xs, ys) -> the ground on that grid as build_campus.py makes Hn
    (the 10 m model, cubic, smoothed the same way, over a block reaching 40 m into the grid so the smoothing sees the
    same ground).  Its top row is the grid's bottom row; the rows below take the difference over 30 m."""
    S = SOUTH
    xs = S['x0'] + np.arange(S['nx']) * S['step']
    ys = S['y0'] + np.arange(-6, S['ny'] + 8) * S['step']           # (6 rows south, 8 north of the patch)
    G = raw(xs, ys)
    Hs = G[6:6 + S['ny']].copy()
    i0 = int(round((S['x0'] + half) / step))
    edge = Hn[0, i0:i0 + S['nx']]
    d = edge - Hs[-1]
    f = np.clip(1.0 - (S['ny'] - 1 - np.arange(S['ny'])) * S['step'] / 30.0, 0, 1)
    Hs += d[None, :] * (f * f * (3 - 2 * f))[:, None]
    Hs[-1] = edge
    return Hs


def sample_s(Hs, x, y):
    S = SOUTH
    fx = (x - S['x0']) / S['step']
    fy = (y - S['y0']) / S['step']
    return float(ndimage.map_coordinates(Hs, [[fy], [fx]], order=1, mode='nearest')[0])


def in_patch(x, y):
    S = SOUTH
    return y < S['y0'] + (S['ny'] - 1) * S['step'] and S['x0'] <= x <= S['x0'] + (S['nx'] - 1) * S['step']


def streets(pl):
    """연세로 and the junction: the carriageways' union with its corners rounded, the sidewalks round it, the arms.
    pl: gate_town.plan's dict (성산로's south kerb: where 연세로 begins)."""
    A = arms()
    road_ = pl['road']
    ks = road_.off(-gt.HW)
    y_top = float(np.interp(gt.YONSEI_X, ks[:, 0], ks[:, 1])) + 1.0        # (gate_town.layout's 연세로)
    s_top = float(A['yonsei'].ls.project(Point(gt.YONSEI_X, y_top)))
    s_kerb = float(A['yonsei'].ls.project(Point(gt.YONSEI_X, y_top - 1.2)))      # (성산로's south kerb)
    cw, walks = {}, {}
    for k, a in A.items():
        cw[k] = a.poly(-a.half, a.half, 0.0, s_top if k == 'yonsei' else a.cum[-1])
        walks[k] = yro_walk_poly(a, s_kerb) if k == 'yonsei' else a.poly(-a.half - a.walk, a.half + a.walk, 0.0, a.cum[-1])
    road = unary_union(list(cw.values()))
    road = road.buffer(CORNER_R, join_style=1).buffer(-CORNER_R, join_style=1).union(road)
    # (the corners rounded: closing the union fills the wedges between the arms)
    street = unary_union([road] + list(walks.values()))
    street = street.buffer(4.0, join_style=1).buffer(-4.0, join_style=1).union(street)
    walk = street.difference(road)
    cross_streets = unary_union([w for k, w in walks.items() if k != 'yonsei'])
    return dict(arms=A, road=road, street=street, walk=walk, cw=cw, walks=walks, y_top=y_top, cross_streets=cross_streets)


def level(Hn, Hs, half, step, geo, sample_n):
    """The streets' bed: level across each arm, its height along it the ground smoothed over 60 m (the 5 m model
    carries the roofs of the tall blocks along 연세로 as humps of 2 - 4 m), the junction at its middle's; eased out
    over 10 m past the sidewalks.  Not north of y -492 (the bridge and 성산로, gate_town.plan)."""
    S = SOUTH
    A = geo['arms']
    i0 = int(round((S['x0'] + half) / step))
    nx = S['nx']
    k1 = int(round((-400.0 + half) / step)) + 1                          # Hn rows up to y -400
    C = np.vstack([Hs[:-1], Hn[:k1, i0:i0 + nx]])
    ys = S['y0'] + np.arange(C.shape[0]) * step
    xs = S['x0'] + np.arange(nx) * step
    X, Y = np.meshgrid(xs, ys)
    Cs = ndimage.gaussian_filter(C, 3.0)
    smp = lambda x, y: float(ndimage.map_coordinates(Cs, [[(y - S['y0']) / step], [(x - S['x0']) / step]], order=1)[0])
    zj = smp(*JC)
    prof = {}
    for k, a in A.items():
        z = np.array([smp(*p) for p in a.P])
        z = ndimage.gaussian_filter1d(z, 30.0 / 2.0, mode='nearest')           # (2 m stations: 60 m)
        # from the junction's level at its middle, into the arm's own over 40 m
        f = np.clip(a.cum / 40.0, 0, 1)
        f = f * f * (3 - 2 * f)
        z = zj * (1 - f) + z * f
        # no steeper than 4 % out of the junction (the model's 7 - 8 % up 신촌로's east arm and the south arm in their
        # first 100 m is the tall blocks at the corners)
        for i in range(1, len(z)):
            ds = a.cum[i] - a.cum[i - 1]
            z[i] = min(max(z[i], z[i - 1] - 0.04 * ds), z[i - 1] + 0.04 * ds)
        if k == 'yonsei':
            # an even climb from the junction to the ground under the bridge (gate_town's bed): the model's humps along
            # it (2 - 6 m at y -870, over the tall blocks there) are roofs; the junction is the low ground of the
            # valley and the street climbs about 1 % to the gate (고증 4.10)
            zb = sample_n(gt.YONSEI_X, -492.0)
            sb = float(a.ls.project(Point(gt.YONSEI_X, -492.0)))
            f = np.clip(a.cum / sb, 0, 1)
            z = zj + (zb - zj) * (f * 0.85 + 0.15 * f * f * (3 - 2 * f))
            z = np.where(a.cum > sb, zb, z)
        prof[k] = z
    P = shapely.points(np.stack([X.ravel(), Y.ravel()], 1))
    tgt = np.zeros(X.size)
    wsum = np.zeros(X.size)
    for k, a in A.items():
        d = shapely.distance(P, a.ls)
        s = shapely.line_locate_point(a.ls, P)
        zz = np.interp(s, a.cum, prof[k])
        wk = 1.0 / (np.maximum(d - a.half, 0.0) ** 2 + 1.0)
        wk[d > a.half + a.walk + 30.0] = 0.0
        tgt += zz * wk
        wsum += wk
    tgt = np.where(wsum > 0, tgt / np.maximum(wsum, 1e-9), C.ravel()).reshape(X.shape)
    dist = shapely.distance(P, geo['street']).reshape(X.shape)
    w = 1.0 - np.clip(dist / 10.0, 0, 1)
    w = w * w * (3 - 2 * w)
    w *= np.where(wsum.reshape(X.shape) > 0, 1.0, 0.0)
    nf = np.clip((-492.0 - Y) / 25.0, 0, 1)
    w *= nf * nf * (3 - 2 * nf)
    C2 = C * (1 - w) + tgt * w
    Hs[:-1] = C2[:S['ny'] - 1]
    Hn[:k1, i0:i0 + nx] = C2[S['ny'] - 1:]
    Hs[-1] = Hn[0, i0:i0 + nx]
    return dict(z_junction=round(zj, 2), z_yonsei=[round(float(v), 2) for v in prof['yonsei'][::25]],
                arms={k: [round(float(v), 1) for v in prof[k][:80:20]] for k in prof})


# ----------------------------------------------------------------------------- the town
def _osm_rotary():
    p = os.path.join(ROOT, 'data/raw/osm_rotary.json')
    return json.load(open(p))['elements'] if os.path.exists(p) else []


def _poly_osm(e):
    return Polygon([_xy(p['lat'], p['lon']) for p in e['geometry']]).buffer(0)


def _box(b):
    return gt._rect(b)


def layout(geo, town, extras, ground, taken_z):
    """What campus.json gains (into gate_town's town dict and its extras, in place):
    - the shop rows along 연세로 from y -640 to the junction and the junction's corner blocks, the town south of the
      campus grid's edge (OSM's outlines and the fill of low houses); gate_town's blocks that stand in the streets go
      (b[6] = -storeys: blender/town.py still draws their random looks, so the others keep theirs)
    - kerbs, lane paint, crossings and stop lines; the cars' lanes through the junction with their signals
    - the walker's barrier round the walks open to them (연세로's two sidewalks, the junction's corners and crossings)
    - lamps, the subway's entrances, the town's ground map.
    ground(x, y): the terrain as saved; taken_z: the campus's outlines (unused south of the rails)."""
    rnd = random.Random(4802)
    A, road, street, walk = geo['arms'], geo['road'], geo['street'], geo['walk']
    R2 = lambda a: [[round(float(x), 2), round(float(y), 2)] for x, y in a]
    ya = A['yonsei']
    blocks = town['blocks']
    new = []
    # ---- 연세로's shop rows as they were (wall to wall, three to five storeys, as gate_town's, behind a 5 m walk): still
    # drawn from the stream and kept as gone blocks (b[6] < 0), so that everything after them keeps its looks; the rows
    # that stand now are yro_rows' (from the 1996 photos), appended at the end of the blocks
    corner_cut = geo['cross_streets'].buffer(1.0)
    shapely.prepare(corner_cut)
    old_fronts = {1: [], -1: []}
    for side in (1, -1):                         # +1 east, -1 west
        segs, y0 = [], Y_ROWS
        for g0, g1 in GAPS[side]:
            segs.append((y0, g0))
            y0 = g1
        segs.append((y0, None))
        for ya_, yb_ in segs:
            # (the arm runs from the junction north: s falls going south)
            s = float(ya.ls.project(Point(gt.YONSEI_X, ya_)))
            stop = float(ya.ls.project(Point(gt.YONSEI_X, yb_))) if yb_ is not None else 0.0
            while s > stop + 4.0:
                wdt = rnd.uniform(6.0, 11.5)
                if s - wdt < stop + 6.0:
                    wdt = s - stop
                dep = rnd.uniform(10.0, 15.0)
                p, t, n = ya.at(s - wdt / 2)
                # n: left of the arm's way north, i.e. west; the east side is at -n
                c = p - n * side * (ya.half + YRO_OLD_WALK + dep / 2)
                ang = math.atan2(-n[1] * side, -n[0] * side)          # (L, the depth, away from the street)
                bb = [round(float(c[0]), 2), round(float(c[1]), 2), round(dep, 2), round(wdt - 0.15, 2), round(ang, 4), 0.0,
                      3 + int(rnd.random() * 2.6), rnd.choice([0, 1, 2, 3, 3]), 3 if rnd.random() < 0.6 else 2, 0, 2,
                      int(rnd.random() < 0.7)]
                rr = _box(bb)
                s -= wdt
                if yb_ is None and shapely.intersects(corner_cut, rr):
                    break                                              # (the junction's corner)
                bb[5] = round(min(ground(x_, y_) for x_, y_ in list(rr.exterior.coords)[:4]) - 0.3, 2)
                new.append(bb)
                old_fronts[side].append(bb)
    rows_poly = unary_union([_box(b) for b in new])
    for bb in new:
        bb[6] = -bb[6]
    # (the street as it was with the 5 m walk, for what is cleared and placed round the old rows: the same blocks and
    # the same draws; what stands in the new rows goes in yro_rows)
    street_b = street.union(ya.poly(-ya.half - YRO_OLD_WALK, ya.half + YRO_OLD_WALK, 0.0, float(ya.ls.project(Point(gt.YONSEI_X, Y_ROWS)))))
    # ---- what stands in the streets or where the rows go now goes (gate_town's blocks south of its own rows)
    clear = unary_union([street_b.buffer(-0.3), rows_poly.buffer(-0.3)])
    shapely.prepare(clear)
    n_gone = 0
    for b in blocks:
        if b[1] < Y_ROWS + 30.0 and b[6] > 0 and shapely.intersects(clear, _box(b)):
            b[6] = -b[6]
            n_gone += 1
    # ---- the corners of the junction and the town south of the grid: OSM's outlines as boxes (osm_rotary.json),
    # the same rules as gate_town's; where it has none, the low houses on a loose grid
    els = _osm_rotary()
    zone = box(SOUTH['x0'] + 2.0, SOUTH['y0'] + 2.0, SOUTH['x0'] + (SOUTH['nx'] - 1) * SOUTH['step'] - 2.0, -795.0)
    zone = zone.union(box(-320.0, -800.0, 120.0, Y_ROWS))                # (and along 연세로 down from gate_town's rows)
    busy_g = unary_union([street_b.buffer(1.0), rows_poly.buffer(1.5)])
    busy = busy_g
    shapely.prepare(busy)
    old = unary_union([_box(b) for b in blocks if b[6] > 0])
    shapely.prepare(old)
    corner = []
    for e in els:
        if 'building' not in e['tags'] or e['id'] in MODERN or len(e['geometry']) < 4:
            continue
        pg = _poly_osm(e)
        if pg.geom_type == 'MultiPolygon':          # (a ring that crosses itself: its biggest part)
            pg = max(pg.geoms, key=lambda g_: g_.area)
        if pg.is_empty or pg.geom_type != 'Polygon' or pg.area < 22:
            continue
        cx, cy = pg.centroid.x, pg.centroid.y
        lm = next((m for m in LANDMARKS if pg.buffer(2.0).contains(Point(*m['at']))), None)
        if lm:                                      # (a landmark keeps what of it stands clear of the streets)
            pg = pg.difference(busy_g.buffer(0.5))
            pg = max(getattr(pg, 'geoms', [pg]), key=lambda g_: g_.area)
            cx, cy = pg.centroid.x, pg.centroid.y
        if not zone.contains(Point(cx, cy)) or shapely.intersects(busy, pg) or shapely.intersects(old, pg.buffer(-0.5)):
            continue
        rr = list(pg.minimum_rotated_rectangle.exterior.coords)[:4]
        ex, ey = np.array(rr[1]) - np.array(rr[0]), np.array(rr[3]) - np.array(rr[0])
        L, W = float(np.linalg.norm(ex)), float(np.linalg.norm(ey))
        ang = math.atan2(ex[1], ex[0])
        if W > L:
            L, W, ang = W, L, ang + math.pi / 2
        if W < 3.2:
            continue
        fill = pg.area / (L * W)
        L, W = L * (0.82 + 0.16 * fill) - 0.3, W * (0.82 + 0.16 * fill) - 0.3
        mc = pg.minimum_rotated_rectangle.centroid
        area = L * W
        r = rnd.random()
        near_j = math.hypot(mc.x - JC[0], mc.y - JC[1]) < 170.0 and street_b.distance(Point(mc.x, mc.y)) < 30.0
        on_main = street_b.distance(Point(mc.x, mc.y)) < 22.0
        if lm:
            lv = lm['lv']
        elif near_j and area > 600:                # the junction's big blocks
            lv = 5 + int(r * 3)
        elif on_main:
            lv = 3 + int(r * 2.4)
        elif area < 95:
            lv = 1 + (r < 0.62)
        elif area < 260:
            lv = 2 + (r < 0.45)
        else:
            lv = 3 + int(r * 2.2)
        hip = lv <= 2 and area < 170 and rnd.random() < 0.72
        roof = (0 if rnd.random() < 0.62 else 1 if rnd.random() < 0.7 else 2) if hip else (3 if rnd.random() < 0.55 else 2)
        wall = rnd.choice([0, 0, 0, 1, 1, 2, 2, 3])
        hs = [ground(*q) for q in rr]
        b = [round(mc.x, 2), round(mc.y, 2), round(L, 2), round(W, 2), round(ang, 4), round(min(hs) - 0.3, 2), lv,
             lm['wall'] if lm else wall, 2 if lm else roof, 0 if lm else int(hip), 1 if lm else int(on_main),
             int(rnd.random() < 0.6)]
        new.append(b)
        if lm:
            corner.append((lm, b))
    streets_osm = unary_union([LineString([_xy(q['lat'], q['lon']) for q in e['geometry']]).buffer(
        {'primary': 13.0, 'secondary': 9.0, 'tertiary': 7.0}.get(e['tags']['highway'].replace('_link', ''), 3.6))
        for e in els if 'highway' in e['tags'] and len(e['geometry']) > 1 and
        e['tags']['highway'].replace('_link', '') in ('primary', 'secondary', 'tertiary', 'residential', 'living_street',
                                                       'unclassified', 'service', 'pedestrian')])
    used = unary_union([_box(b).buffer(2.2) for b in new] + [old.buffer(2.2), streets_osm, busy])
    shapely.prepare(used)
    keep = zone.buffer(-1.0)
    shapely.prepare(keep)
    n_fill = 0
    for gy in np.arange(SOUTH['y0'] + 6.0, -795.0, 11.5):
        for gx in np.arange(SOUTH['x0'] + 6.0, SOUTH['x0'] + (SOUTH['nx'] - 1) * SOUTH['step'] - 6.0, 11.5):
            cx, cy = gx + rnd.uniform(-1.6, 1.6), gy + rnd.uniform(-1.6, 1.6)
            L, W, ang = rnd.uniform(7.0, 10.0), rnd.uniform(6.0, 8.2), rnd.choice([0.0, math.pi / 2]) + rnd.uniform(-0.12, 0.12)
            b = [round(cx, 2), round(cy, 2), round(L, 2), round(W, 2), round(ang, 4), 0.0, 1 + (rnd.random() < 0.55),
                 rnd.choice([0, 0, 1, 1, 2, 3]), 0 if rnd.random() < 0.66 else 1 if rnd.random() < 0.6 else 2, 1, 0, 0]
            if rnd.random() < 0.22:
                b[6], b[8], b[9], b[11] = 2 + (rnd.random() < 0.4), 3 if rnd.random() < 0.5 else 2, 0, int(rnd.random() < 0.6)
            r_ = _box(b)
            cs_ = np.array(r_.exterior.coords)
            if not shapely.contains_xy(keep, cs_[:, 0], cs_[:, 1]).all() or shapely.intersects(used, r_):
                continue
            b[5] = round(min(ground(x_, y_) for x_, y_ in cs_[:4]) - 0.3, 2)
            new.append(b)
            n_fill += 1
    blocks += new
    fronts, n_yro_gone = yro_rows(geo, blocks, ground)           # (연세로's rows from the 1996 photos, at the end)
    # ---- kerbs: the carriageways' edge (gate_town's 연세로 north of y -560 has its own), lane paint, crossings
    kerbs, paint, zebra = [], [], []
    rings = [road] if road.geom_type == 'Polygon' else list(road.geoms)
    for pg in rings:
        for lr in [pg.exterior] + list(pg.interiors):
            ls = LineString(lr.coords)
            pts = [ls.interpolate(d).coords[0] for d in np.arange(0, ls.length, 1.5)]
            run = []
            for q in pts:
                if q[1] > -489.0 or any(math.hypot(q[0] - a.P[-1][0], q[1] - a.P[-1][1]) < a.half + 2.5 for a in A.values()):
                    if len(run) > 1:
                        kerbs.append(R2(run))
                    run = []
                else:
                    run.append(q)
            if len(run) > 1:
                kerbs.append(R2(run))
    # each arm: where it leaves the junction (its kerbs clear of the others'), a crossing there, a stop line behind it
    xs = {}
    for k, a in A.items():
        others = unary_union([c for kk, c in geo['cw'].items() if kk != k and not ({k, kk} <= {'sinchon_w', 'sinchon_e'})])
        s = 4.0
        while s < a.cum[-1] - 10:
            p, t, n = a.at(s)
            cut = LineString([tuple(p + n * (a.half + 0.5)), tuple(p - n * (a.half + 0.5))])
            if not cut.intersects(others):
                break
            s += 1.0
        xs[k] = s + CORNER_R * 0.6 + 1.5
    for k, a in A.items():
        s_x = xs[k]
        # the crossing: 4.5 m wide, white bars 0.45 m across the walk's direction (the 1990s' plain bars)
        for o in np.arange(-a.half + 0.5, a.half - 0.4, 0.95):
            c = [a.at(s_x)[0] + a.at(s_x)[2] * o, a.at(s_x + 4.5)[0] + a.at(s_x + 4.5)[2] * o,
                 a.at(s_x + 4.5)[0] + a.at(s_x + 4.5)[2] * (o + 0.45), a.at(s_x)[0] + a.at(s_x)[2] * (o + 0.45)]
            zebra.append(R2(c))
        # stop line on the inbound half (traffic on the right: going in is going against s, on the arm's right of
        # its outward direction... inbound cars drive towards the junction, s falling: their right is +n)
        s_stop = s_x + 6.0
        c = [a.at(s_stop)[0] + a.at(s_stop)[2] * 0.3, a.at(s_stop + 0.5)[0] + a.at(s_stop + 0.5)[2] * 0.3,
             a.at(s_stop + 0.5)[0] + a.at(s_stop + 0.5)[2] * (a.half - 0.3), a.at(s_stop)[0] + a.at(s_stop)[2] * (a.half - 0.3)]
        zebra.append(R2(c))
        # lane paint from the stop line out (연세로: to where gate_town's begins its own at the bridge... none there)
        s_end = a.cum[-1] - 3.0 if k != 'yonsei' else float(a.ls.project(Point(gt.YONSEI_X, -492.0)))
        ss = np.arange(s_stop + 1.0, s_end, 2.0)
        if len(ss) < 2:
            continue
        ssy = ss[ss >= s_x + ROT_HATCH[0] + ROT_HATCH[1]]          # (the centre line from the painted triangle's base)
        for sgn in (1, -1):
            if len(ssy) > 1:
                paint.append(dict(kind='yellow', w=0.12, pts=R2([a.at(s)[0] + a.at(s)[2] * sgn * 0.16 for s in ssy])))
            for kk in range(1, a.lanes):
                o = sgn * (0.3 + (a.half - 0.3) / a.lanes * kk)
                paint.append(dict(kind='white_dash', w=0.12, pts=R2([a.at(s)[0] + a.at(s)[2] * o for s in ss[2:]])))
    # 연세로's crossing between the junction and the bridge, with stop lines either side
    s_mid = float(ya.ls.project(Point(gt.YONSEI_X, MID_CROSS_Y)))
    for o in np.arange(-ya.half + 0.5, ya.half - 0.4, 0.95):
        c = [ya.at(s_mid)[0] + ya.at(s_mid)[2] * o, ya.at(s_mid + 4.5)[0] + ya.at(s_mid + 4.5)[2] * o,
             ya.at(s_mid + 4.5)[0] + ya.at(s_mid + 4.5)[2] * (o + 0.45), ya.at(s_mid)[0] + ya.at(s_mid)[2] * (o + 0.45)]
        zebra.append(R2(c))
    for s_, o0, o1 in ((s_mid + 6.0, 0.3, ya.half - 0.3), (s_mid - 2.0, -ya.half + 0.3, -0.3)):
        zebra.append(R2([ya.at(s_)[0] + ya.at(s_)[2] * o0, ya.at(s_ + 0.5)[0] + ya.at(s_ + 0.5)[2] * o0,
                         ya.at(s_ + 0.5)[0] + ya.at(s_ + 0.5)[2] * o1, ya.at(s_)[0] + ya.at(s_)[2] * o1]))
    # the island: its kerb a ring, the white ring of short dashes round it (52158: some 0.6 m long, as long apart)
    ic, ir = np.array(ISLAND['c']), ISLAND['r']
    kerbs.append(R2([tuple(ic + ir * np.array([math.cos(a_), math.sin(a_)])) for a_ in np.linspace(0, 2 * math.pi, 49)]))
    nd = int(round(2 * math.pi * ISLAND['ring'] / 1.2))
    for i in range(nd):
        a0, a1 = 2 * math.pi * i / nd, 2 * math.pi * (i + 0.5) / nd
        paint.append(dict(kind='white', w=0.25, pts=R2([tuple(ic + ISLAND['ring'] * np.array([math.cos(a_), math.sin(a_)]))
                                                        for a_ in np.linspace(a0, a1, 3)])))
    paint += rot_letters()
    paint += rot_hatches(A, xs)
    paint += rot_arrows(A, xs)
    # the crossing over 성산로 before the bridge is gate_town's
    # ---- the cars' lanes through the junction, each with the signal phase it waits for at its stop line
    lanes = []

    def lane_pts(k, o, s0, s1, step=3.0):
        a = A[k]
        ss = np.arange(s0, s1, step if s1 > s0 else -step).tolist() + [s1]
        return [tuple(a.at(s)[0] + a.at(s)[2] * o) for s in ss]

    def curve(p0, d0, p1, d1, n=10):
        """a smooth turn from p0 heading d0 to p1 heading d1 (cubic Bezier)"""
        L = float(np.linalg.norm(np.array(p1) - np.array(p0))) * 0.45
        c0, c1 = np.array(p0) + np.array(d0) * L, np.array(p1) - np.array(d1) * L
        out = []
        for i in range(1, n):
            t = i / n
            q = (1 - t) ** 3 * np.array(p0) + 3 * (1 - t) ** 2 * t * c0 + 3 * (1 - t) * t * t * c1 + t ** 3 * np.array(p1)
            out.append(tuple(q))
        return out

    def route(k_in, o_in, k_out, o_out, phase, s_far_in=None, s_far_out=None):
        """in along arm k_in (towards the junction) at offset o_in, out along k_out at o_out"""
        ai, ao = A[k_in], A[k_out]
        si0 = ai.cum[-1] - 2.0 if s_far_in is None else s_far_in
        so1 = ao.cum[-1] - 2.0 if s_far_out is None else s_far_out
        a_in = lane_pts(k_in, o_in, si0, xs[k_in] + 5.5)
        a_out = lane_pts(k_out, o_out, xs[k_out] + 1.0, so1)
        d_in = -ai.at(xs[k_in] + 5.5)[1]
        d_out = ao.at(xs[k_out] + 1.0)[1]
        mid = curve(a_in[-1], d_in, a_out[0], d_out, 24)
        mid = round_island(a_in[-1], mid, a_out[0])
        pts = a_in + mid + a_out
        ls = LineString(pts)
        stops = [[round(float(ls.project(Point(a_in[-1]))) - 0.5, 1), 0, phase]]
        # 연세로's crossing: northbound cars stop south of it, southbound north of it (group 1: 0 cars go, 1 walkers)
        if k_in == 'yonsei':
            q = ya.at(s_mid + 6.0)[0] + ya.at(s_mid + 6.0)[2] * o_in
            stops.insert(0, [round(float(ls.project(Point(*q))) - 0.5, 1), 1, 0])
        if k_out == 'yonsei':
            q = ya.at(s_mid - 2.0)[0] + ya.at(s_mid - 2.0)[2] * o_out
            stops.append([round(float(ls.project(Point(*q))) - 0.5, 1), 1, 0])
        return dict(kind='car', pts=R2(pts), stops=stops)

    def round_island(p0, mid, p1):
        """the turn's points pushed out of the island's ring, passing it with the island on the left"""
        out = []
        P_ = [np.array(p0)] + [np.array(q) for q in mid] + [np.array(p1)]
        R_ = ISLAND['ring'] + 2.0
        for i in range(1, len(P_) - 1):
            q, d = P_[i], P_[i + 1] - P_[i - 1]
            d = d / max(1e-9, np.linalg.norm(d))
            v = q - ic
            if np.linalg.norm(v) < R_:
                right = np.array([d[1], -d[0]])
                v = v + right * R_ * 0.9
                q = ic + v / np.linalg.norm(v) * R_
            out.append(q)
        for _ in range(3):                                  # (smoothed: the push leaves corners)
            out = [out[0]] + [(out[j - 1] + out[j] * 2 + out[j + 1]) / 4 for j in range(1, len(out) - 1)] + [out[-1]]
        return [tuple(q) for q in out]

    s_bridge = float(ya.ls.project(Point(gt.YONSEI_X, -480.0)))
    s_bridge2 = float(ya.ls.project(Point(gt.YONSEI_X, -488.0)))
    L1, L2 = LANE_W / 2 + 0.3, LANE_W * 1.5 + 0.3
    # (inbound on an arm: going against its s, the right-hand side is +n (left of the outward direction))
    lanes.append(route('yonsei', L1, 'baekbeom', -L1, 0, s_far_in=s_bridge))           # 연세로 south, on into 백범로
    lanes.append(route('yonsei', L2, 'seogang', -L2, 0, s_far_in=s_bridge))            # and right into 서강로
    lanes.append(route('baekbeom', L1, 'yonsei', -L1, 0, s_far_out=s_bridge2))         # 백범로 north into 연세로
    lanes.append(route('seogang', L1, 'yonsei', -L2, 2, s_far_out=s_bridge2))          # 서강로 into 연세로
    for kk in (0, 1, 2):
        o = 0.3 + LANE_W * (kk + 0.5)
        lanes.append(route('sinchon_w', o, 'sinchon_e', -o, 1))                          # 신촌로 east
        lanes.append(route('sinchon_e', o, 'sinchon_w', -o, 1))                          # and west
    lanes.append(route('sinchon_w', 0.3 + LANE_W * 3.5, 'seogang', -(0.3 + LANE_W * 2.5), 1))   # (the kerb lanes:
    lanes.append(route('sinchon_e', 0.3 + LANE_W * 3.5, 'yonsei', -L2, 1, s_far_out=s_bridge2))  #  turning off)
    # signals: group 0 the junction (phases 0 연세로 · 백범로, 1 신촌로 · 양화로, 2 the south-west arm), group 1
    # 연세로's crossing (0 cars, 1 walkers): green s each, then amber and all red
    signals = dict(groups=[dict(green=[26.0, 30.0, 14.0]), dict(green=[45.0, 18.0])], amber=3.0, red=3.0)
    # the signal heads: one at the far side of each arm's mouth facing the inbound traffic, and one at its stop line
    # [x, y of the pole, the way the lamps face (rad), group, phase, the mast arm's reach over the lanes]
    heads = []
    for k, ph in (('yonsei', 0), ('baekbeom', 0), ('seogang', 2), ('sinchon_w', 1), ('sinchon_e', 1)):
        a = A[k]
        p, t, n = a.at(xs[k] + 6.5)
        q = p + n * (a.half + 0.8)                       # at the stop line, on the inbound side's kerb
        heads.append([round(float(q[0]), 2), round(float(q[1]), 2), round(math.atan2(t[1], t[0]), 4), 0, ph, round(a.half * 0.75, 1)])
    for sgn, s_ in ((1, s_mid + 6.5), (-1, s_mid - 2.5)):
        p, t, n = ya.at(s_)
        q = p + n * sgn * (ya.half + 0.8)
        heads.append([round(float(q[0]), 2), round(float(q[1]), 2), round(math.atan2(t[1] * sgn, t[0] * sgn), 4), 1, 0,
                      round(ya.half * 0.75, 1)])
    # the island's own pole (52158 · 52145 · 52142: on its north edge, the arm out over the lanes to the north-east)
    fb = math.radians(ROT_POLE['face'])
    heads.append([ROT_POLE['at'][0], ROT_POLE['at'][1], round(math.atan2(math.cos(fb), math.sin(fb)), 4), 0, 1, ROT_POLE['reach']])
    # ---- the walks open to the walker: 연세로's two sidewalks from 성산로, the junction's corners within REACH, the
    # crossings; a barrier of thin boxes round them (not along 성산로's north kerb, where gate_town's barrier now runs
    # unbroken over its crossing too: the walker stays on the campus's side, and these walls are out of reach)
    near = Point(*JC).buffer(REACH)
    W_parts = [walk.intersection(near)]
    yw = walk.intersection(Polygon([(-140, geo['y_top'] + 3.0), (-50, geo['y_top'] + 3.0), (-50, JC[1] - 10), (-140, JC[1] - 10)]))
    W_parts.append(yw)
    for k, a in A.items():
        s_x = xs[k]
        W_parts.append(a.poly(-a.half - 0.5, a.half + 0.5, s_x - 0.25, s_x + 4.75))
    W_parts.append(ya.poly(-ya.half - 0.5, ya.half + 0.5, s_mid - 0.25, s_mid + 4.75))
    cx0, cx1, cy0, cy1 = extras['cross_box']          # (gate_town's crossing over 성산로, kerb to kerb)
    W_parts.append(box(cx0, cy0 - 0.5, cx1, cy1 + 0.8))
    W_parts.append(extras['walk_s'].intersection(box(-135.0, -480.0, -60.0, -440.0)))
    Wk = unary_union(W_parts).buffer(0.05).buffer(-0.05)
    barrier = []
    y_open = cy1 + 0.1                             # (north of this: the campus's side of 성산로)
    for pg in (Wk.geoms if hasattr(Wk, 'geoms') else [Wk]):
        if pg.geom_type != 'Polygon' or pg.area < 4.0:
            continue
        pg = orient(pg, 1.0)
        for lr in [pg.exterior] + list(pg.interiors):
            c = list(lr.coords)
            for p, q in zip(c[:-1], c[1:]):
                p, q = np.array(p), np.array(q)
                d = q - p
                L = float(np.linalg.norm(d))
                if L < 1e-3:
                    continue
                nrm = np.array([d[1], -d[0]]) / L                 # (outward: right of a counter-clockwise ring)
                m = max(1, int(math.ceil(L / 1.5)))
                for i in range(m):
                    a_, b_ = p + d * (i / m), p + d * ((i + 1) / m)
                    if (a_[1] + b_[1]) / 2 > y_open:
                        continue
                    barrier.append(R2([a_ - nrm * 0.05, b_ - nrm * 0.05, b_ + nrm * 0.85, a_ + nrm * 0.85]))
    # ---- lamps along the kerbs (every 30 m, both sides; none in a crossing), the subway's entrances at the corners
    props = []
    for k, a in A.items():
        s0 = xs[k] + 12.0
        s1 = min(a.cum[-1] - 5.0, REACH + 60.0) if k != 'yonsei' else float(ya.ls.project(Point(gt.YONSEI_X, geo['y_top'] - 12.0)))
        for s in np.arange(s0, s1, 30.0):
            p, t, n = a.at(s)
            for sgn in (1, -1):
                q = p + n * sgn * (a.half + 0.7)
                if k == 'yonsei' and q[1] > -508.0:          # (south of the baked sun shadow's edge)
                    continue
                rot = math.atan2(t[1], t[0]) + (math.pi if sgn < 0 else 0.0)
                props.append(['lamp_arm', round(float(q[0]), 2), round(float(q[1]), 2), round(rot, 3)])
    # 2호선 신촌역 (1984): eight stairs down from the corners (OSM's entrance nodes; 1997 numbering not known)
    EXITS = [(1, -137.0, -942.0), (2, -110.0, -930.0), (3, -88.0, -930.0), (4, -63.0, -945.0), (5, -28.0, -976.0),
             (6, -56.0, -1011.0), (7, -149.0, -995.0), (8, -172.0, -968.0)]
    entrances, coll = [], []
    for no, x, y in EXITS:
        # set on the walk 1.2 m in from its back edge, its long side along the street it stands on
        best = min(A.values(), key=lambda a: a.ls.distance(Point(x, y)))
        s = float(best.ls.project(Point(x, y)))
        p, t, n = best.at(s)
        side = 1 if float((np.array([x, y]) - p) @ n) > 0 else -1
        q = p + n * side * (best.half + best.walk - 2.0)
        ang = math.atan2(t[1], t[0])
        L, Wd = 7.4, 2.6
        e = [round(float(q[0]), 2), round(float(q[1]), 2), round(ang, 4), L, Wd, no, round(ground(*q), 2)]
        entrances.append(e)
        coll.append(R2(_box([q[0], q[1], L + 0.2, Wd + 0.2, ang]).exterior.coords[:4]))
    # ---- 연세로's ginkgo rows (51979 · 52106, 1996: both walks from the junction to the bridge, a crown to every
    # shop front; 52108 the same down the south arm), 1.1 m in from the kerb, none at the crossings, the side
    # streets' mouths, the subway's stairs or under the bridge; new trees go at the end of campus.json's list
    trees = []
    busy_t = unary_union([Polygon(c_) .buffer(1.5) for c_ in coll] +
                         [a.poly(-a.half - 6, a.half + 6, xs[k] - 3.0, xs[k] + 8.0) for k, a in A.items()] +
                         [ya.poly(-ya.half - 6, ya.half + 6, s_mid - 3.0, s_mid + 8.0)])
    s_top_t = float(ya.ls.project(Point(gt.YONSEI_X, -508.0)))           # (south of the baked sun shadow's edge)
    for k, s0, s1 in (('yonsei', xs['yonsei'] + 9.0, s_top_t), ('baekbeom', xs['baekbeom'] + 9.0, A['baekbeom'].cum[-1] - 20.0)):
        a = A[k]
        for side in (1, -1):
            gaps = GAPS[-side] if k == 'yonsei' else []          # (+n is west on 연세로: side +1 west)
            for s in np.arange(s0 + (2.0 if side > 0 else 5.5), s1, 7.0):
                p, t, n = a.at(s)
                q = p + n * side * (a.half + 1.1) + t * rnd.uniform(-0.4, 0.4)
                if any(g1 - 4.0 < q[1] < g0 + 4.0 for g0, g1 in gaps) or busy_t.contains(Point(*q)):
                    continue
                trees.append(['ginkgo', round(float(q[0]), 2), round(float(q[1]), 2), round(rnd.uniform(0.62, 0.78), 2),
                              round(rnd.uniform(0, 6.28), 2)])
    # the island's bed (52158, May 1996): the yellow band (BED, r 2.5 - 4.3) two rows of the pansy border round the
    # inner lawn; the dark and the white bands and the outer lawn are the ground's grass
    shrubs = []
    for rr_, nn in ((3.0, 10), (3.85, 13)):
        for i in range(nn):
            a_ = 2 * math.pi * (i + 0.5 * (rr_ < 3.5)) / nn
            shrubs.append(['pansy_bed', round(float(ic[0] + rr_ * math.cos(a_)), 2), round(float(ic[1] + rr_ * math.sin(a_)), 2),
                           0.9, round(a_ + math.pi / 2, 2)])
    # ---- 신촌 로터리's bus stops (52145 · 52142: flat pale roofs at the kerb, buses pulled in and people waiting on
    # 양화로's south walk at the 그랜드백화점 corner; 52145 · 52187: on 신촌로's south walk in front of 한일은행)
    stops_r, waiting = rot_stops(A)
    town['stops'] = town.get('stops', []) + stops_r
    # ---- signs: the shops on the rows' ground floors (2019 · 2021 문집의 신촌 약도 have the rows north of the side
    # street at y -552; these are the next ones down towards the junction, sign_sinchon2)
    # (the names are of the kinds of shop the 1990s photos show along it, not of real shops; but 홍익문고, the east
    # corner's bookshop since 1978, 연세로 2: 서울시 미디어허브)
    names = {1: ['레코드', '안경원', '분식', '당구장', '커피숍', '홍익문고'], -1: ['약국', '서점', '호프', '노래방', '경양식', '제과점']}
    signs2 = []
    for side in (1, -1):
        fr = fronts[side]
        pick = [fr[j] for j in np.linspace(1, len(fr) - 3, 5).astype(int)] + [fr[-1]] if side > 0 else \
            [fr[j] for j in np.linspace(1, len(fr) - 2, 6).astype(int)]
        if side > 0:
            fr[-1][6] = 5                                  # (홍익문고: five storeys)
        for i, b in enumerate(pick):
            n_ = np.array([math.cos(b[4]), math.sin(b[4])])                 # (L axis: away from the street)
            c = np.array(b[:2]) - n_ * (b[2] / 2 + 0.14)
            face = math.atan2(-n_[1], -n_[0])
            signs2.append([round(float(c[0]), 2), round(float(c[1]), 2), round(b[5] + 0.3 + 3.3, 2), round(face, 4),
                           round(min(b[3] - 0.6, 6.4), 2), 1.1, (0 if side > 0 else 6) + i])
    # the landmarks' signs over their tops, facing the junction
    for lm, b in corner:
        c, sn = math.cos(b[4]), math.sin(b[4])
        v = np.array(ISLAND['c']) - np.array(b[:2])
        # the face nearest the junction: of the four, the one whose outward normal points most at it
        faces = [(np.array([c, sn]), b[2] / 2, b[3]), (-np.array([c, sn]), b[2] / 2, b[3]),
                 (np.array([-sn, c]), b[3] / 2, b[2]), (-np.array([-sn, c]), b[3] / 2, b[2])]
        nrm, off, wid = max(faces, key=lambda f_: float(f_[0] @ v))
        q = np.array(b[:2]) + nrm * (off + 0.2)
        top = b[5] + 0.3 + 3.0 * b[6]
        signs2.append([round(float(q[0]), 2), round(float(q[1]), 2), round(top - lm['sign_h'] / 2 - 0.6, 2),
                       round(math.atan2(nrm[1], nrm[0]), 4), round(min(wid - 2.0, lm['sign_h'] * 5.5), 2), lm['sign_h'], lm['sign']])
    # ---- the ground map round the walks (web/src/terrain.js: past the campus's map): the town's ground asphalt as
    # gate_town paints it, the sidewalks paved
    # (the island's lawn left unpainted: the ground's grass; the stairwells cut out of the ground, B: web/src/terrain.js)
    holes = [_box([e[0], e[1], e[3] - 0.25, e[4] - 0.45, e[2]]) for e in entrances]
    paints = dict(asphalt=[box(TSPLAT['x0'], TSPLAT['y0'], TSPLAT['x1'], TSPLAT['y1']).difference(
                      Point(*ISLAND['c']).buffer(ISLAND['r'] - 0.1))],
                  pavers=[walk, unary_union([Polygon(e_).buffer(0.6) for e_ in [[(x_, y_) for x_, y_ in c_] for c_ in coll]])],
                  hole=holes)
    town['blocks'] = blocks
    town['kerbs'] += kerbs
    town['paint'] += paint
    town['zebra'] += zebra
    town['lanes'] += lanes
    town['signals'] = signals
    town['heads'] = heads
    town['entrances'] = entrances
    town['signs2'] = signs2
    town['names2'] = names[1] + names[-1]
    town['vsigns'] = yro_wall_signs(blocks)                    # (연세로's wall signs and banner: yro_)
    town['banner'] = yro_banner(geo, ground)
    print('연세로: rows %d + %d, gone %d, wall signs %d' % (len(fronts[1]), len(fronts[-1]), n_yro_gone, len(town['vsigns'])))
    town['rotary'] = dict(c=list(JC), reach=REACH, arms={k: dict(half=a.half, walk=a.walk, cross=round(xs[k], 1))
                                                          for k, a in A.items()})
    paths = [dict(kind='primary', w=2 * A[k].half, pts=[[round(float(x), 1), round(float(y), 1)] for x, y in A[k].P[::4]])
             for k in ('sinchon_w', 'sinchon_e', 'seogang')] + \
            [dict(kind='secondary', w=2 * A['baekbeom'].half, pts=[[round(float(x), 1), round(float(y), 1)] for x, y in A['baekbeom'].P[::4]]),
             dict(kind='tertiary', w=2 * ya.half, pts=[[round(float(x), 1), round(float(y), 1)] for x, y in ya.P[::4]
                                                       if y < -630.0])]
    # the walkers' sidewalks (web: a crowd of its own on 연세로): each side's middle, the bridge to the corner
    walks_ = []
    for side in (1, -1):
        o = side * (ya.half + ya.walk / 2)
        s1 = float(ya.ls.project(Point(gt.YONSEI_X, geo['y_top'] - 3.0)))
        walks_.append(R2(lane_pts('yonsei', o, s1, xs['yonsei'] + 7.0, 3.0)))
    town['walks'] = walks_
    print('신촌 로터리: blocks +%d (rows %d, fill %d, gone %d), kerbs %d, lanes %d, barrier %d, lamps %d' % (
        len(new), sum(len(v) for v in fronts.values()), n_fill, n_gone, len(kerbs), len(lanes), len(barrier), len(props)))
    town['island'] = dict(c=list(ISLAND['c']), r=ISLAND['r'])
    # people standing about (web/src/main.js: the town's crowd) and the blue sign over 연세로 (blender/town.py)
    waiting['groups'] += rot_waiting(fronts[1][-1], corner, A, waiting['singles'])
    town['waiting'] = waiting
    town['dirsign'] = rot_dirsign(ya, s_mid)
    town['rot_fence'] = rot_fence(A)
    # the names over them (campus.json markers: the walk's tags, the bird's-eye pins, the map)
    hk = fronts[1][-1]
    top = lambda b: round(b[5] + 0.3 + 3.0 * b[6] + 1.0, 1)
    markers = [dict(name=lm['name'], pos=[b[0], b[1]], top=top(b)) for lm, b in corner] + [
        dict(name='홍익문고', pos=[hk[0], hk[1]], top=top(hk)),
        dict(name='신촌 로터리', pos=list(ISLAND['c']), top=round(ground(*ISLAND['c']) + 9.0, 1)),
        dict(name='신촌역 (2호선)', pos=[entrances[1][0], entrances[1][1]], top=round(entrances[1][6] + 5.0, 1))]
    return dict(markers=markers, props=props, colliders=barrier + coll, paints=paints, paths=paths, corner=corner, trees=trees, shrubs=shrubs)


# ----------------------------------------------------------------------------- the 1995 · 1996 rooftop photos
# (고증 4.10 「옥상 사진의 카메라」 · 「게임에 옮긴 것」): the paint on the junction, its bus stops, people standing about
ROT_HATCH = (7.0, 12.0)        # the yellow triangle on each arm's middle: its tip past the crossing, its length
# 「연세대」 in strokes on a glyph's unit box (u across, v up the text; road lettering is drawn long along the way)
ROT_GLYPHS = [
    [[(0.28 + 0.2 * math.cos(t), 0.79 + 0.13 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 13)],      # 연: ㅇ
     [(0.74, 1.0), (0.74, 0.52)], [(0.5, 0.88), (0.74, 0.88)], [(0.5, 0.68), (0.74, 0.68)],                 #  ㅕ
     [(0.14, 0.44), (0.14, 0.08), (0.86, 0.08)]],                                                          #  ㄴ
    [[(0.34, 0.95), (0.06, 0.08)], [(0.3, 0.62), (0.56, 0.08)],                                            # 세: ㅅ
     [(0.92, 1.0), (0.92, 0.0)], [(0.74, 0.92), (0.74, 0.12)], [(0.6, 0.55), (0.74, 0.55)]],                #  ㅔ
    [[(0.52, 0.88), (0.08, 0.88), (0.08, 0.12), (0.54, 0.12)],                                             # 대: ㄷ
     [(0.94, 1.0), (0.94, 0.0)], [(0.74, 0.92), (0.74, 0.1)], [(0.74, 0.55), (0.94, 0.55)]]]                #  ㅐ


def rot_letters():
    """「연세대」 north of the island (ROT_LETTERS): white strokes, 0.2 m wide"""
    L = ROT_LETTERS
    b = math.radians(L['up'])
    ev = np.array([math.sin(b), math.cos(b)])                 # (up the text: the way its readers drive)
    eu = np.array([ev[1], -ev[0]])                            # (along a line of it: to their right)
    c = np.array(L['c'])
    out = []
    for i, glyph in enumerate(ROT_GLYPHS):
        u0 = (i - 1) * (L['w'] + 0.1) - L['w'] / 2
        for st in glyph:
            pts = [tuple(c + eu * (u0 + u * L['w']) + ev * ((v - 0.5) * L['h'])) for u, v in st]
            out.append(dict(kind='white', w=0.2, pts=[[round(float(x), 2), round(float(y), 2)] for x, y in pts]))
    return out


def rot_hatches(A, xs):
    """the yellow triangles on each arm's middle past its crossing, a smaller one inside it and a third in that
    (52158: sides of 13 - 15 m, the inner ones about a half and a fifth; 52145 · 52142: one at every arm's mouth)"""
    out = []
    for k, a in A.items():
        s_t = xs[k] + ROT_HATCH[0]
        s_b = s_t + ROT_HATCH[1]
        hw = min(0.4 * a.half, 3.0)
        tip = a.at(s_t)[0]
        pb, _, nb = a.at(s_b)
        tri = np.array([tip, pb + nb * hw, pb - nb * hw])
        cen = tri.mean(0)
        for f in (1.0, 0.52, 0.2):
            q = cen + (tri - cen) * f
            out.append(dict(kind='yellow', w=0.2, pts=[[round(float(x), 2), round(float(y), 2)] for x, y in list(q) + [q[0]]]))
    return out


def rot_arrows(A, xs):
    """a straight-on arrow in every lane coming in, just behind its stop line (52145 · 52158)"""
    out = []
    R2_ = lambda pts: [[round(float(x), 2), round(float(y), 2)] for x, y in pts]
    for k, a in A.items():
        s0 = xs[k] + 8.0                                     # (the head's tip; the tail 4.6 m further out)
        for j in range(a.lanes):
            o = 0.3 + (a.half - 0.3) / a.lanes * (j + 0.5)
            P = lambda s, oo: a.at(s)[0] + a.at(s)[2] * oo
            out.append(dict(kind='white', w=0.18, pts=R2_([P(s0 + 1.5, o), P(s0 + 4.6, o)])))
            for d_ in (-0.5, -0.25, 0.0, 0.25, 0.5):
                out.append(dict(kind='white', w=0.22, pts=R2_([P(s0, o), P(s0 + 1.6, o + d_)])))
    return out


def rot_stops(A):
    """the rotary's four bus stops, [x, y, the way along, length, the roof's material] (blender/town.py stops), and the
    people waiting at them: {groups: [[x, y]], singles: [[x, y, facing x, facing y]]}.
    52142 · 52145 (1995.10): 양화로's south walk at the 그랜드백화점 corner, 신촌로's south walk before 한일은행;
    52005 (1996.8, from the 외환은행 roof): flat white roofs on 양화로's north walk before 금강제화 and on 신촌로's north
    walk before the fenced corner lot, people under them"""
    stops, wait = [], dict(groups=[], singles=[])
    rnd = random.Random(4811)
    # (the side: +1 the arm's left of its outward way (+n), -1 its right; 양화로 (sinchon_w) runs west, 신촌로 east)
    for k, s, side in (('sinchon_w', 40.0, 1), ('sinchon_e', 52.0, -1), ('sinchon_w', 28.0, -1), ('sinchon_e', 24.0, 1)):
        a = A[k]
        p, t, n = a.at(s)
        q = p + n * side * (a.half + 2.2)
        tt = t * side
        stops.append([round(float(q[0]), 2), round(float(q[1]), 2), round(math.atan2(tt[1], tt[0]), 4), 9.0, 'metal'])
        for u in (-2.6, -0.9, 0.7, 2.4):
            m = q + tt * (u + rnd.uniform(-0.3, 0.3)) - n * side * rnd.uniform(0.1, 0.6)
            ang = rnd.uniform(-0.5, 0.5)
            f = -n * side
            f = np.array([f[0] * math.cos(ang) - f[1] * math.sin(ang), f[0] * math.sin(ang) + f[1] * math.cos(ang)])
            wait['singles'].append([round(float(m[0]), 2), round(float(m[1]), 2), round(float(f[0]), 3), round(float(f[1]), 3)])
        g = q + n * side * 1.6 + tt * rnd.uniform(-3, 3)
        wait['groups'].append([round(float(g[0]), 2), round(float(g[1]), 2)])
    return stops, wait


def rot_waiting(hk, corner, A, singles):
    """「홍익문고 앞에서 만나」: people waiting on the walk in front of 홍익문고 and of 그레이스백화점, looking out for
    someone (singles, appended) and a few in twos and threes (the groups returned)"""
    rnd = random.Random(4812)
    groups = []

    def row(c, n_, t_, us, d, gs):
        for u in us:
            m = c + n_ * (d + rnd.uniform(-0.3, 0.4)) + t_ * (u + rnd.uniform(-0.3, 0.3))
            ang = rnd.uniform(-0.9, 0.9)
            f = np.array([n_[0] * math.cos(ang) - n_[1] * math.sin(ang), n_[0] * math.sin(ang) + n_[1] * math.cos(ang)])
            singles.append([round(float(m[0]), 2), round(float(m[1]), 2), round(float(f[0]), 3), round(float(f[1]), 3)])
        for u, dd in gs:
            g = c + n_ * dd + t_ * u
            groups.append([round(float(g[0]), 2), round(float(g[1]), 2)])

    # 홍익문고: its front on 연세로 (the block's L axis points away from the street)
    na = np.array([math.cos(hk[4]), math.sin(hk[4])])
    row(np.array(hk[:2]) - na * (hk[2] / 2), -na, np.array([-na[1], na[0]]), (-3.4, -2.1, -0.6, 1.0, 2.6), 1.4,
        [(-1.2, 3.0), (2.2, 3.1)])
    # 그레이스백화점: its face towards 양화로, the east half of it
    for lm, b in corner:
        if lm['name'] != '그레이스백화점':
            continue
        c, sn = math.cos(b[4]), math.sin(b[4])
        faces = [(np.array([c, sn]), b[2] / 2, b[3]), (-np.array([c, sn]), b[2] / 2, b[3]),
                 (np.array([-sn, c]), b[3] / 2, b[2]), (-np.array([-sn, c]), b[3] / 2, b[2])]
        ctr = np.array(b[:2])
        near = np.array(A['sinchon_w'].ls.interpolate(A['sinchon_w'].ls.project(Point(*ctr))).coords[0])
        v = near - ctr
        nrm, off, wid = max(faces, key=lambda f_: float(f_[0] @ v) / np.linalg.norm(v))
        t_ = np.array([-nrm[1], nrm[0]])
        if float(t_ @ (np.array(JC) - ctr)) < 0:
            t_ = -t_                                           # (t_ towards the junction's end of the face)
        cf = ctr + nrm * off + t_ * (wid * 0.25)
        row(cf, nrm, t_, (-2.8, -1.2, 0.6, 2.4), 1.8, [(-0.2, 3.4), (3.6, 3.0)])
    return groups


def rot_fence(A):
    """the fence round the empty corner lot south of 홍익문고 (52005 · 52006, 1996.8: grey panels with yellow banners
    along their tops, at the back of 연세로's east walk and of 신촌로's north walk; today 엘리트 빌딩): its line, from
    홍익문고's south wall (y -912.6, tools/sinchon_rotary.py yro_rows) to the corner and east along 신촌로 for 36 m"""
    ya, ae = A['yonsei'], A['sinchon_e']
    out = []
    s0 = float(ya.ls.project(Point(gt.YONSEI_X, -912.4)))
    for s in np.linspace(s0, 0.0, 30):
        p, t, n = ya.at(s)
        out.append(p - n * (ya.half + ya.walk + 0.15))                  # (east: -n on 연세로)
    east = [ae.at(s)[0] + ae.at(s)[2] * (ae.half + ae.walk + 0.15) for s in np.linspace(0.0, 60.0, 61)]
    line_e = LineString([tuple(q) for q in east])
    # the corner where the two back edges meet; the 연세로 line stops there, the 신촌로 one starts there
    cut = None
    for i in range(1, len(out)):
        seg = LineString([tuple(out[i - 1]), tuple(out[i])])
        if seg.intersects(line_e):
            cut = (i, seg.intersection(line_e))
            break
    if cut is None:
        return []
    i, x = cut
    xc = np.array(x.coords[0]) if x.geom_type == 'Point' else np.array(x.centroid.coords[0])
    pts = out[:i] + [xc]
    se = float(line_e.project(Point(*xc)))
    pts += [np.array(line_e.interpolate(d).coords[0]) for d in np.arange(se + 2.0, se + 36.0, 2.0)]
    return [[round(float(q[0]), 2), round(float(q[1]), 2)] for q in pts]


def rot_dirsign(ya, s_mid):
    """the blue direction sign over 연세로's northbound lanes (51979: 「모래내 ← · → 독립문」, a pole on the east kerb
    with an arm, just north of the crossing in the middle): its pole, the panel's middle, the way it faces, w, h,
    the panel's foot over the road"""
    s = s_mid + 14.0
    p, t, n = ya.at(s)
    pole = p - n * (ya.half + 0.6)
    c = p - n * (ya.half * 0.48)
    return dict(pole=[round(float(pole[0]), 2), round(float(pole[1]), 2)], c=[round(float(c[0]), 2), round(float(c[1]), 2)],
                face=round(math.atan2(-t[1], -t[0]), 4), w=4.4, h=2.2, z0=5.2)


def town_splat(paints, path):
    """the town's ground map (TSPLAT): R asphalt, G paving, B the woods' floor (none), each drawn at four times the
    resolution and averaged (as build_campus.py's splat_aa), row 0 north"""
    S = TSPLAT
    k = 4
    W, H = int(round((S['x1'] - S['x0']) / S['res'])), int(round((S['y1'] - S['y0']) / S['res']))
    P = lambda x, y: ((x - S['x0']) / S['res'] * k, (S['y1'] - y) / S['res'] * k)
    out = []
    for layer in ('asphalt', 'pavers', 'hole'):
        im = Image.new('L', (W * k, H * k), 0)
        d = ImageDraw.Draw(im)
        for g in paints[layer]:
            for pg in (g.geoms if hasattr(g, 'geoms') else [g]):
                if pg.geom_type != 'Polygon' or pg.is_empty:
                    continue
                d.polygon([P(x, y) for x, y in pg.exterior.coords], fill=255)
                for h in pg.interiors:
                    d.polygon([P(x, y) for x, y in h.coords], fill=0)
        a = np.array(im, np.float32).reshape(H, k, W, k).mean(axis=(1, 3))
        out.append(a)
    a, p, h = out
    a = np.minimum(a, 255.0 - p)
    rgb = np.stack([a, p, h], -1)
    Image.fromarray(np.clip(rgb + 0.5, 0, 255).astype(np.uint8), 'RGB').save(path, optimize=True)
    return (W, H)


# ----------------------------------------------------------------------------- 연세로's rows, signs and banner (yro_)
# The shop rows from y -640 to the junction as the 1996 photos show them where they can be read (고증 4.10): from the
# junction north, the buildings of each side between its side streets.  [frontage m, storeys, wall band (blender/town.py:
# 0 red brick, 1 cream, 2 grey, 3 white tile), depth m], from the segment's south end north; the rest of a segment is
# filled from the photos' mix (YRO_MIX).  Segments: GAPS split each side, 0 = the northmost.
YRO_FIXED = {
    # east, 연세로2길 (y -893) to the junction: the brick house OSM 356219100 (3 storeys in 52004 · 52006), 홍익문고
    # (OSM 356219103: 7.2 m on 연세로, 11 m deep; its storeys are the corner's, below).  South of it the corner lot stood
    # fenced in 1996 (52005 · 52006: yellow banners on the hoarding, a bus shelter in front; 엘리트 빌딩 now)
    (1, 4): [[7.2, 5, 1, 11.0], [12.4, 3, 0, 8.5]],
    # east, 연세로2길 north: the purple-grey four storeys whose south wall faces the side street (52106), a white three,
    # a low cream two, the white four with the long window bands and 비디오 signs (52004 · 52006)
    (1, 3): [[11.0, 4, 2, 13.0], [8.0, 3, 3, 11.0], [6.0, 2, 1, 10.0], [12.0, 4, 3, 13.0]],
    # west, the junction to the side street at y -884: 금강제화 on the corner (four storeys of white tile, the shoe shop's
    # sign over the ground floor, clinics and academies above, 52005 · 52006), a cream three
    (-1, 3): [[20.0, 4, 3, 14.0], [9.0, 3, 1, 11.0]],
    # west, north of it: the white five of INDIS · 바둑 · 학원 (52006), the seven storeys of white tile with dark window
    # bands and 현대예식장's sign up its corner (52106 · 52006, 신영증권 on its roof)
    (-1, 2): [[13.0, 5, 3, 13.0], [24.0, 7, 3, 16.0]],
}
# the mix along the rest of 연세로 in 51979 · 52006 (both sides, the junction to the bridge): storeys and their share,
# frontages 5.5 - 12 m, every wall band (red brick seldom), flat roofs with tanks
YRO_MIX = dict(lv=[2, 3, 4, 5, 6, 7], p=[0.12, 0.25, 0.30, 0.18, 0.10, 0.05], w=(5.5, 12.0), dep=(10.0, 14.0),
               wall=[0, 1, 2, 2, 3, 3])
YRO_BANNER_Y = -805.0         # the festival's banner (51979 · 52106, 1996.5): just south of the crossing in the middle


def yro_walk_poly(a, s_kerb):
    """연세로's two sidewalks: YRO_WALK from the junction to y -640, gate_town's north of it (4.8)"""
    s640 = float(a.ls.project(Point(gt.YONSEI_X, Y_ROWS)))
    return unary_union([a.poly(-a.half - a.walk, a.half + a.walk, 0.0, s640 + 0.5),
                        a.poly(-a.half - gt.YONSEI_WALK, a.half + gt.YONSEI_WALK, s640, s_kerb)])


def yro_rows(geo, blocks, ground):
    """The rows from y -640 to the junction behind the YRO_WALK walk: YRO_FIXED at the segments' south ends, YRO_MIX
    for the rest (random.Random(4805)), appended to blocks; blocks that stand in them go (b[6] < 0).  Returns the
    fronts of each side, north to south (the last of the east side is 홍익문고), and how many went."""
    rnd = random.Random(4805)
    ya = geo['arms']['yonsei']
    corner_cut = geo['cross_streets'].buffer(1.0)
    shapely.prepare(corner_cut)
    face = ya.half + YRO_WALK
    S = lambda y: float(ya.ls.project(Point(gt.YONSEI_X if y > -740 else -100.0, y)))

    def mk(s_mid, wdt, lv, wall, dep, side, draw=True):
        p, t, n = ya.at(s_mid)
        c = p - n * side * (face + dep / 2)
        ang = math.atan2(-n[1] * side, -n[0] * side)
        b = [round(float(c[0]), 2), round(float(c[1]), 2), round(dep, 2), round(wdt - 0.15, 2), round(ang, 4), 0.0, int(lv),
             int(wall), (3 if rnd.random() < 0.6 else 2) if draw else 3, 0, 2, int(rnd.random() < 0.7) if draw else 0]
        b[5] = round(min(ground(x_, y_) for x_, y_ in list(_box(b).exterior.coords)[:4]) - 0.3, 2)
        return b

    def pick():
        lv = rnd.choices(YRO_MIX['lv'], YRO_MIX['p'])[0]
        return [rnd.uniform(*YRO_MIX['w']), lv, rnd.choice(YRO_MIX['wall']), rnd.uniform(*YRO_MIX['dep'])]

    fronts = {1: [], -1: []}
    for side in (1, -1):
        segs, y0 = [], Y_ROWS
        for g0, g1 in GAPS[side]:
            segs.append((y0, g0))
            y0 = g1
        segs.append((y0, None))
        for k, (yn, ys) in enumerate(segs):
            s_n = S(yn)
            if ys is not None:
                s_s = S(ys)
            elif side > 0:
                s_s = S(-912.6)                               # (홍익문고's south wall; the fenced corner lot south of it)
            else:                                             # (the corner: where a row's box clears the cross street)
                s_s = 0.0
                while shapely.intersects(corner_cut, _box(mk(s_s + 0.5, 1.0, 1, 0, 12.0, side, False))):
                    s_s += 0.5
            fixed = YRO_FIXED.get((side, k), [])
            seq, s = [], s_s
            for i, (w, lv, wall, dep) in enumerate(fixed):
                if s + w > s_n - 0.5:
                    break
                if i == len(fixed) - 1 and s_n - (s + w) < 4.0:
                    w = s_n - s                               # (the last fixed one meets the segment's end)
                seq.append((s + w / 2, w, lv, wall, dep))
                s += w
            while s < s_n - 0.5:
                w, lv, wall, dep = pick()
                if s_n - (s + w) < 5.0:
                    w = s_n - s
                seq.append((s + w / 2, w, lv, wall, dep))
                s += w
            for s_mid, w, lv, wall, dep in sorted(seq, key=lambda q: -q[0]):         # (north to south)
                fronts[side].append(mk(s_mid, w, lv, wall, dep, side))
    rows = fronts[1] + fronts[-1]
    rp = unary_union([_box(b).buffer(-0.2) for b in rows])
    shapely.prepare(rp)
    n_gone = 0
    for b in blocks:
        if b[6] > 0 and b[1] < Y_ROWS + 2.0 and shapely.intersects(rp, _box(b)):
            b[6] = -b[6]
            n_gone += 1
    blocks += rows
    return fronts, n_gone


def yro_wall_signs(blocks):
    """The signs that stand out from the shops' walls up the floors over the ground floor (51979 · 52106: every front
    on 연세로 carries one, many two or three): along both rows, the bridge to the junction (gate_town's too, kind 2).
    A board 0.7 - 0.9 m out from the wall, 2.4 - 7 m tall, its two faces along the street; random.Random(4806).
    [x, y of the board's middle, z of its middle, the wall's outward way (rad), out, height, cell of sign_yonseiro]"""
    rnd = random.Random(4806)
    out = []
    for b in blocks:
        if b[10] != 2 or b[6] < 2 or not (-950.0 < b[1] < -500.0):
            continue
        cx, cy, L, W, ang, base, lv = b[:7]
        u = np.array([math.cos(ang), math.sin(ang)])          # (L: away from the street)
        t = np.array([-u[1], u[0]])
        n_s = 1 + int(W > 6.0 and rnd.random() < 0.65) + int(W > 10.0 and rnd.random() < 0.35)
        ends = rnd.sample([-1, 1], 2) + [0]
        for k in range(n_s):
            along = ends[k] * (W / 2 - rnd.uniform(0.5, 1.4)) if ends[k] else rnd.uniform(-1.5, 1.5)
            w_ = rnd.uniform(0.7, 0.9)
            z0 = base + 0.3 + 3.0 + rnd.uniform(0.2, 0.8)
            z1 = base + 0.3 + 3.0 * lv - rnd.uniform(0.3, 1.5)
            h = min(z1 - z0, rnd.uniform(2.4, 7.0))
            cell = rnd.randrange(16)
            if h < 1.8:
                continue
            q = np.array([cx, cy]) - u * (L / 2 + 0.12 + w_ / 2) + t * along
            out.append([round(float(q[0]), 2), round(float(q[1]), 2), round(z0 + h / 2, 2), round(math.atan2(-u[1], -u[0]), 4),
                        round(w_, 2), round(h, 2), cell])
    return out


def yro_banner(geo, ground):
    """제5회 신촌문화축제's banner across 연세로 (51979: white cloth, the festival's name in blue, the show in green, the
    date 96.5.4 in red, tied over the road from the walks): [x0, y0, x1, y1 (its two poles behind the kerbs), z of the
    road, the cloth's bottom over it, its height]"""
    ya = geo['arms']['yonsei']
    p, t, n = ya.at(float(ya.ls.project(Point(-99.0, YRO_BANNER_Y))))
    a, b = p + n * (ya.half + 0.6), p - n * (ya.half + 0.6)
    return [round(float(a[0]), 2), round(float(a[1]), 2), round(float(b[0]), 2), round(float(b[1]), 2),
            round(ground(*p), 2), 4.6, 1.3]
