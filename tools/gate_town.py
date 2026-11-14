"""정문 밖: 성산로, 경의선 철둑과 굴다리, 창천동 (reference/고증/4.8_정문_밖.md).  tools/build_campus.py 가 부른다.

    plan = gate_town.plan(Hn, half, step, gate, heading, wall)     # before the terrain is saved: levels the ground
    town = gate_town.layout(plan, ground, taken)                   # after the planting: what campus.json carries

Frame: campus metres, x east, y north.  Nothing here draws from build_campus.py's `rng`: the planting on the banks,
the town's blocks and their looks come from random.Random streams of their own.

Where things stand (고증 4.8):
- The rails and 연세로 are OSM's as fetched by tools/fetch_gate_osm.py (two tracks of the 경의선, 10 m apart at the
  bridge; the 1995 aerial photo has the two decks).  The vertical aerial photos of 28 July 1997 (자료 Q, tools/
  aerial97.py; frames 26/16 and 27/17) have the two tracks 2.5 m south of OSM's from 300 m west of the bridge to 150 m
  east (the line was laid again for the 2009 double track), their rails 10.8 m over 성산로 before the gate (two frames'
  stereo: the decks at 34.5 m where the box junction is at 23.7 m), the bridge's opening from x -108.5 to -78.5.
- The gate stands where the 2010 skyview and the pre-rebuild roadview have its pillars, y -396 on 백양로's centre
  line (tools/build_campus.py GATE_C; 고증 4.8 「정문의 남북 자리」).  From its wall to 성산로's north kerb runs its
  mouth, a fan of asphalt (the 1995 photo: the west wall rounding off, the east one running out at a slant), some
  16 m deep at its east end and 31 m at its west.
- 성산로 is OSM's, the middle between its two carriageways, ten lanes (the 1995 photo: 30 - 35 m, four or more dashed
  lines a side).  The 1997 vertical photos have it 2.7 m south of that middle before the gate (the south kerb at
  y -455.4 at x -137, as in Kakao's 2008 skyview; the north kerb at -420: today's north kerb, -413, is the 2000s'
  widening for the bus lanes in the middle), 35.4 m from kerb to kerb: five lanes of 3.1 m each way either side of a
  2.7 m hatched strip (SHIFT, LANE_W, MID, GUTTER).  Their zebra crosses it east of the junction's box (x -75 .. -61.5,
  the 2008 skyview's too), another crosses 연세로's mouth.
"""
import json, math, os, random
import numpy as np
from scipy import ndimage
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
import shapely

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
LAT0, LON0 = 37.5640, 126.9380

# OSM 성산로: the centre lines of its two carriageways, west -> east (ways 516728240 · 516365912 · 246158664, and
# 204778124 · 516372147 · 618545800 · 219839090)
RD_N = [(-516, -224), (-458, -289), (-415, -339), (-400, -355), (-387, -367), (-375, -376), (-358, -385), (-335, -394),
        (-319, -400), (-298, -405), (-280, -411), (-266, -413), (-234, -416), (-156, -421), (-122, -424), (-99, -425),
        (139, -420), (146, -419), (159, -415), (168, -411), (178, -406), (188, -402), (200, -393), (209, -385),
        (242, -351), (252, -340), (267, -324), (322, -271), (342, -252), (376, -218)]
RD_S = [(-468, -303), (-450, -323), (-444, -330), (-423, -352), (-410, -365), (-399, -377), (-368, -404), (-347, -421),
        (-335, -430), (-318, -442), (-303, -450), (-290, -452), (-98, -446), (-19, -445), (27, -444), (74, -443),
        (118, -440), (145, -438), (155, -436), (177, -427), (197, -418), (223, -396), (241, -380), (255, -365),
        (277, -337), (288, -318), (317, -291), (352, -246)]
# OSM 경의선, its two main tracks west -> east (ways 405594551 · 405594547 · 405594548 · 1471545534 · 405594538, and
# 405594549 · 405594550 · 405594539 · 405594535; east of x 288 they run under the 2006 station deck now)
TRACK_N = [(-576, -365), (-559, -381), (-531, -402), (-495, -426), (-453, -447), (-399, -466), (-372, -473),
           (-350, -477), (-329, -480), (-302, -482), (-265, -482), (-218, -482), (-124, -477), (-113, -477),
           (-79, -475), (196, -465), (211, -465), (220, -463), (230, -463), (288, -462), (432, -457), (517, -454),
           (711, -446)]
TRACK_S = [(-579, -368), (-560, -386), (-535, -406), (-498, -429), (-466, -446), (-451, -454), (-413, -467),
           (-369, -480), (-321, -488), (-284, -491), (-225, -490), (-126, -487), (-113, -487), (-79, -486),
           (-68, -486), (89, -481), (207, -478), (275, -476), (288, -476), (541, -467), (751, -454)]
TRACK_DY = 2.5               # the 1997 tracks south of OSM's (the 1997 vertical photos at the rails' own height: 1.2 - 3.4 m
#                              at seven stations from x -245 to 80, both tracks; eased out past x -300 and x 150)


def _track_w(x):
    return _smooth((x + 450) / 150.0) if x < -300 else 1.0 - _smooth((x - 150) / 150.0) if x > 150 else 1.0


SHIFT = 2.7                  # 성산로 south of the middle of OSM's two carriageways before the gate, m (shift_w)
LANES, LANE_W, MID = 5, 3.1, 2.7       # lanes each way, their width, the hatched strip between the two ways
GUTTER = 0.75                # from the kerb lane's edge line to the kerb
HW = LANES * LANE_W + MID / 2 + GUTTER  # the carriageway's half width (17.6 m)
HW_RNG = 16.45               # ... as first laid, about OSM's middle (what the campus's planting was cleared by: layout)
SW_S = 1.6                   # the south sidewalk under the bank
RAIL_UP = 10.8               # the rails over 성산로 before the gate
BALLAST = 0.25               # the rails over the top of the bank
SHOULDER = 3.6               # the top of the bank past each track's centre line
SLOPE = 1.6                  # the banks: run per rise
DMAX_N, DMAX_S = 18.0, 13.0  # how far out a slope's foot may stand (a wall holds it up from there: the south side's
#                              white wall above the town's roofs in the 1997 photos)
BRIDGE = (-108.5, -78.5)     # the opening for 연세로 (x), its piers in the middle
CROSS_X = (-75.0, -61.5)     # the zebra over 성산로, east of the junction's box
BOX_X = (-108.7, -79.5)      # the box junction's white frame before 연세로 (x; 2.9 m in from the north kerb, 1.9 m from
#                              the south one)
EAST_TURN = 22.25            # where the gate's east low wall turns south-east, along its line from its middle (m)
YZEBRA = (-459.5, -466.5)    # the zebra over 연세로's mouth (y)
YONSEI_X = -96.0
YONSEI_HALF, YONSEI_WALK = 7.0, 5.0
X0, X1 = -575.0, 700.0       # the banks are built between these
MODERN = {230178502, 628197716}        # OSM outlines that are the 2006 station building


def _xy(p):
    return ((p['lon'] - LON0) * 111320 * math.cos(math.radians(LAT0)), (p['lat'] - LAT0) * 110574)


def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


TRACK_N = [(x, round(y - TRACK_DY * _track_w(x), 2)) for x, y in TRACK_N]
TRACK_S = [(x, round(y - TRACK_DY * _track_w(x), 2)) for x, y in TRACK_S]


def shift_w(x):
    """how much of SHIFT the road is south of OSM's middle at x: all of it from x -260 to -40 (the 1997 photos: 3.3 m at
    x -185, 2.7 at -137, 2.6 at -40, 1 m at x 20), none past x -400 and x 100"""
    if x < -260:
        return _smooth((x + 400) / 140.0)
    if x > -40:
        return 1.0 - _smooth((x + 40) / 140.0)
    return 1.0


def _chaikin(pts, n=2):
    P = [np.array(p, float) for p in pts]
    for _ in range(n):
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            Q += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        P = Q + [P[-1]]
    return P


def _resample(pts, step):
    ls = LineString([tuple(p) for p in pts])
    n = max(2, int(round(ls.length / step)) + 1)
    return [ls.interpolate(d).coords[0] for d in np.linspace(0, ls.length, n)]


def _mid(A, B, step):
    """the middle line between two polylines, and their distance apart at each of its points"""
    la, lb = LineString(A), LineString(B)
    out = []
    for d in np.arange(0, lb.length + 1e-6, step):
        p = lb.interpolate(d)
        q = la.interpolate(la.project(p))
        out.append(((p.x + q.x) / 2, (p.y + q.y) / 2, math.hypot(p.x - q.x, p.y - q.y)))
    return out


def _rect(b):
    cx, cy, L, W, ang = b[:5]
    c, s = math.cos(ang), math.sin(ang)
    return Polygon([(cx + u * c - v * s, cy + u * s + v * c) for u, v in ((-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2))])


class Line:
    """a polyline with its left normal at each point (left of west -> east: north)"""
    def __init__(self, pts):
        self.P = np.array(pts, float)
        d = np.gradient(self.P, axis=0)
        d /= np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-9)[:, None]
        self.T = d
        self.N = np.stack([-d[:, 1], d[:, 0]], 1)
        self.ls = LineString([tuple(p) for p in self.P])
        self.cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(self.P, axis=0).T))])

    def off(self, o):
        o = np.broadcast_to(np.asarray(o, float), (len(self.P),))
        return self.P + self.N * o[:, None]


def plan(Hn, half, step, gate, heading, wall, sample):
    """Levels 성산로's bed and cuts the rails' bed into the ground where it stands higher (Hn in place).
    gate: the gate's middle on 백양로's centre line, heading: the road's direction there (rad), wall: the gate wall's two
    ends (west, east),
    sample(x, y): the ground as it stands."""
    gx = np.linspace(-half, half, Hn.shape[0])
    X, Y = np.meshgrid(gx, gx)
    # ---- 성산로: the middle of OSM's two carriageways, pushed south before the gate
    mid = _mid(RD_N, RD_S, 8.0)
    c = [(x, y - SHIFT * shift_w(x)) for x, y, _ in mid]
    road = Line(_resample(_chaikin(c, 2), 4.0))
    wsh = np.array([shift_w(x) for x in road.P[:, 0]])
    # its height: the ground along it, smoothed (the valley of the 창천 before the gate, up towards 금화터널 in the east)
    z = np.array([sample(x, y) for x, y in road.P])
    z = ndimage.gaussian_filter1d(z, 9.0, mode='nearest')
    P = shapely.points(np.stack([X.ravel(), Y.ravel()], 1))
    d = shapely.distance(P, road.ls).reshape(X.shape)
    s = shapely.line_locate_point(road.ls, P).reshape(X.shape)
    zr = np.interp(s, road.cum, z)
    # (eased out over 12 m on the bank's side; on the campus's side only as far as the real road's own edge, 12.5 m
    # north of the middle of OSM's north carriageway: the halls along it keep their ground)
    edge = LineString(RD_N).parallel_offset(12.5, 'left')
    kn = np.clip(np.searchsorted(road.cum, s.ravel()), 1, len(road.cum) - 1).reshape(X.shape)
    side = (X - road.P[kn, 0]) * road.N[kn, 0] + (Y - road.P[kn, 1]) * road.N[kn, 1]
    reach = np.array([max(3.0, edge.distance(Point(*q)) - HW - 2.5) for q in road.P])
    reach = np.where(side > 0, np.minimum(12.0, np.interp(s, road.cum, reach)), 12.0)
    wgt = 1.0 - np.clip((d - (HW + 2.5)) / reach, 0, 1)
    wgt = wgt * wgt * (3 - 2 * wgt)
    wgt[(s <= 0.5) | (s >= road.cum[-1] - 0.5)] = 0.0          # (not past its ends)
    # the gate keeps its ground: nothing north of the line 2 m before the wall, between its ends
    w0, w1 = np.array(wall[0], float), np.array(wall[1], float)
    wt = (w1 - w0) / np.linalg.norm(w1 - w0)
    wn = np.array([-wt[1], wt[0]])                                # north of the wall
    u = (X - w0[0]) * wt[0] + (Y - w0[1]) * wt[1]
    v = (X - w0[0]) * wn[0] + (Y - w0[1]) * wn[1]
    keep = (u > -12) & (u < np.linalg.norm(w1 - w0) + 12)
    wgt = np.where(keep, wgt * np.clip((-v - 1.0) / 5.0, 0, 1), wgt)
    Hn[:] = Hn * (1 - wgt) + zr * wgt
    # ---- the rails: the middle of the two tracks, level
    rm = _mid(TRACK_N, TRACK_S, 6.0)
    rm = [p for p in rm if X0 <= p[0] <= X1]
    for xb in BRIDGE:                               # (a section exactly at each side of the bridge's opening)
        k = next(i for i, p in enumerate(rm) if p[0] > xb)
        a, b = rm[k - 1], rm[k]
        f = (xb - a[0]) / (b[0] - a[0])
        rm.insert(k, tuple(a[i] + (b[i] - a[i]) * f for i in range(3)))
    rm = [p for i, p in enumerate(rm) if i == 0 or abs(p[0] - rm[i - 1][0]) > 1.2 or p[0] in BRIDGE]
    rail = Line([(x, y) for x, y, _ in rm])
    sep = ndimage.gaussian_filter1d(np.array([p[2] for p in rm]), 3.0, mode='nearest')
    k_gate = int(np.argmin(np.abs(road.P[:, 0] - gate[0])))
    rail_z = round(float(z[k_gate]) + RAIL_UP, 2)
    # level over the valley; past x -380 in the west and x 250 in the east (the station's yard, the rise towards 이대) the
    # bed follows the ground as it is (smoothed): the surface model there is not to be trusted with 10 m cuttings
    gr = ndimage.gaussian_filter1d(np.array([sample(x, y) for x, y in rail.P]), 12.0, mode='nearest')
    lvl = np.array([_smooth((x + 520) / 140.0) if x < 0 else 1.0 - _smooth((x - 250) / 150.0) for x in rail.P[:, 0]])
    top = (rail_z - BALLAST) * lvl + (gr + 0.2) * (1 - lvl)
    # where the ground stands higher than the bed: cut down to it, easing out over 14 m
    dr = shapely.distance(P, rail.ls).reshape(X.shape)
    sr = shapely.line_locate_point(rail.ls, P).reshape(X.shape)
    hr = np.interp(sr, rail.cum, sep / 2 + SHOULDER)
    cut = 1.0 - np.clip((dr - hr - 1.0) / 14.0, 0, 1)
    cut = cut * cut * (3 - 2 * cut)
    cut[(sr <= 0.5) | (sr >= rail.cum[-1] - 0.5)] = 0.0
    low = np.minimum(Hn, np.interp(sr, rail.cum, top) - 0.5)
    Hn[:] = Hn * (1 - cut) + low * cut
    return dict(road=road, road_z=z, wsh=wsh, rail=rail, sep=sep, rail_z=rail_z, top=top, gate=tuple(gate),
                heading=heading, wall=(tuple(w0), tuple(w1)), X=X, Y=Y)


def bank_fix(pl, Hn, sample):
    """The banks' sections (after plan): per station of the rails' middle line the top's half width and, each side,
    how far out and how high the slope's foot is.  The 5 m grid under the bank is kept below it."""
    rail, road, tops = pl['rail'], pl['road'], pl['top']
    foot_line = LineString([tuple(p) for p in road.off(-(HW + SW_S))])      # the south sidewalk's back
    secs = []
    for k, (p, n) in enumerate(zip(rail.P, rail.N)):
        hw = pl['sep'][k] / 2 + SHOULDER
        top = float(tops[k])
        row = [round(float(p[0]), 2), round(float(p[1]), 2), round(float(n[0]), 4), round(float(n[1]), 4), round(float(hw), 2)]
        for side in (1, -1):
            e = p + n * side * hw
            dmax = DMAX_N if side > 0 else DMAX_S
            wall_z = None
            if side > 0:                       # towards 성산로: no further than the back of its sidewalk
                far = LineString([tuple(e), tuple(e + n * 40.0)])
                hit = far.intersection(foot_line)
                if not hit.is_empty:
                    q = hit.geoms[0] if hasattr(hit, 'geoms') else hit
                    dmax = min(dmax, max(0.0, math.hypot(q.x - e[0], q.y - e[1]) - 0.35))
            dd, zz = 0.0, top
            g0 = sample(*e)
            if g0 < top - 0.05:
                for dd in np.arange(0.5, dmax + 0.01, 0.5):
                    zz = top - dd / SLOPE
                    q = e + n * side * dd
                    if zz <= sample(*q) + 0.02:
                        break
                else:
                    dd = dmax
                    zz = top - dd / SLOPE
                    wall_z = sample(*(e + n * side * (dd + 0.3)))      # a wall holds the foot up over the sidewalk
            row += [round(float(dd), 2), round(float(zz), 2), None if wall_z is None else round(float(wall_z), 2)]
        secs.append(row + [round(top, 2)])
    # the grid under the bank's footprint: at least 0.3 m under its surface
    X, Y = pl['X'], pl['Y']
    P = shapely.points(np.stack([X.ravel(), Y.ravel()], 1))
    dr = shapely.distance(P, rail.ls).reshape(X.shape)
    near = np.argwhere(dr < 34.0)
    arr = np.array([[r[0], r[1], r[4], r[5], r[6], r[8], r[9]] for r in secs], float)
    for j, i in near:
        q = np.array([X[j, i], Y[j, i]])
        k = int(np.argmin(np.hypot(rail.P[:, 0] - q[0], rail.P[:, 1] - q[1])))
        o = float((q - rail.P[k]) @ rail.N[k])
        _, _, hw, dN, zN, dS, zS = arr[k]
        top = float(tops[k])
        dfoot, zfoot = (dN, zN) if o > 0 else (dS, zS)
        a = abs(o)
        if a <= hw:
            surf = top
        elif a <= hw + dfoot and dfoot > 0:
            surf = top + (zfoot - top) * (a - hw) / dfoot
        else:
            continue
        Hn[j, i] = min(Hn[j, i], surf - 0.3)
    return secs


def layout(pl, secs, ground, taken, e_curb0):
    """Everything campus.json carries of the town: the road's lines and lanes, the bridge, the blocks, the trees and
    lamps to add, the walker's barrier and the polygons the ground is painted with.
    ground(x, y): the terrain as saved, taken: the outlines already built (shapely), e_curb0: 백양로's half width."""
    road, rail, rail_z = pl['road'], pl['rail'], pl['rail_z']
    top = rail_z - BALLAST
    rnd = random.Random(4801)
    R2 = lambda a: [[round(float(x), 2), round(float(y), 2)] for x, y in a]
    kerb_n, kerb_s = road.off(HW), road.off(-HW)
    back_s = road.off(-(HW + SW_S))
    # ---- the campus side: the real road's north edge (the strip left over is sidewalk), and the gate's wall
    # (12.5 m north of the middle of OSM's north carriageway: its kerb and sidewalk, where the game's ground had its
    # 24 m stroke of asphalt end)
    edge = LineString(RD_N).parallel_offset(12.5, 'left')
    bound = np.array([edge.interpolate(edge.project(Point(*q))).coords[0] for q in road.off(HW + 4.0)])
    b_off = np.hypot(*(bound - road.P).T)
    w0, w1 = np.array(pl['wall'][0]), np.array(pl['wall'][1])
    wt = (w1 - w0) / np.linalg.norm(w1 - w0)
    for k, q in enumerate(bound):
        u = float((q - w0) @ wt)
        if -1.0 <= u <= np.linalg.norm(w1 - w0) + 1.0:
            yw = (w0 + wt * u)[1] - 0.45
            if q[1] > yw:
                bound[k] = (q[0], yw)
    # ---- the gate's mouth (고증 4.8): from under the gate's wall to the road, the 1995 photo's fan: the west wall
    # rounding off towards the road, the east one running out at a slant.  (u, v): along the wall eastwards from its
    # middle, northwards from its line; clipped at 성산로's middle.  The 2008 / 2011 roadview: asphalt from the wall's
    # foot to the lanes, no kerb between (the buses' bays and the stop's waiting cars along its west half)
    g0, a0 = np.array(pl['gate']), pl['heading']
    t = np.array([math.cos(a0), math.sin(a0)])
    nl = np.array([-t[1], t[0]])
    wc, wl = (w0 + w1) / 2, float(np.linalg.norm(w1 - w0))
    wnn = np.array([-wt[1], wt[0]])
    hw_ = wl / 2
    fan = [(-hw_, -0.4), (hw_, -0.4)] + [(hw_ + 0.62 * d, -d) for d in (8.0, 20.0, 45.0)] + \
          [(-hw_ - 12.5, -45.0), (-hw_ - 12.0, -28.0), (-hw_ - 10.5, -22.0), (-hw_ - 8.0, -17.0), (-hw_ - 4.8, -12.0),
           (-hw_ - 2.3, -7.5), (-hw_ - 0.7, -3.5)]
    north_of_road = Polygon([tuple(p) for p in road.P] + [(road.P[-1][0], road.P[-1][1] + 600), (road.P[0][0], road.P[0][1] + 600)]).buffer(0)
    mouth = Polygon([tuple(wc + wt * u + wnn * v) for u, v in fan]).buffer(0).intersection(north_of_road).buffer(0)
    # Its asphalt stops short of that in the east: the low wall turns south-east where the white wall ends and runs
    # down to 성산로's sidewalk (the July 1997 vertical photos, the 2010 skyview, the 2011 roadview: 고증 4.8.1
    # 「동쪽 흰 담과 그 동쪽」; blender/props.py GATE_TURN), lawn behind it.  The fan above still decides the kerb's
    # break, the lamps and the trees (and tools/build_campus.py GATE_OUT), so that none of them moves.
    fan_a = [(-hw_, -0.4), (EAST_TURN, -0.4)] + fan[3:]
    mouth_a = Polygon([tuple(wc + wt * u + wnn * v) for u, v in fan_a]).buffer(0).intersection(mouth).buffer(0)
    zone = Polygon([tuple(p) for p in bound] + [(road.P[-1][0] + 300, road.P[-1][1]), (720, -810), (-660, -810),
                                                 (-660, road.P[0][1])]).buffer(0).union(mouth).buffer(0)
    road_poly = Polygon([tuple(p) for p in kerb_n] + [tuple(p) for p in kerb_s[::-1]]).buffer(0)
    walk_n = Polygon([tuple(p) for p in bound] + [tuple(p) for p in kerb_n[::-1]]).buffer(0)
    walk_s = Polygon([tuple(p) for p in kerb_s] + [tuple(p) for p in back_s[::-1]]).buffer(0)
    # just inside the wall: the old game's forecourt strokes of asphalt along it go, paved like the gate's square
    # (백양로's own mesh covers its 12 m either side of the centre line)
    inside = Polygon([tuple(w0 - wt * 2.0 - wnn * 0.5), tuple(w0 + wt * (wl + 2.0) - wnn * 0.5), tuple(w0 + wt * (wl + 2.0) + wnn * 14.0),
                      tuple(w0 - wt * 2.0 + wnn * 14.0)]).difference(
        Polygon([tuple(g0 + t * d + nl * o) for o, d in ((12.6, -3.0), (12.6, 40.0), (-12.6, 40.0), (-12.6, -3.0))])).buffer(0)
    # ---- 연세로 through the bank and on south
    y_top = float(np.interp(YONSEI_X, kerb_s[:, 0], kerb_s[:, 1])) + 1.0
    yonsei = Polygon([(YONSEI_X - YONSEI_HALF, y_top), (YONSEI_X + YONSEI_HALF, y_top), (YONSEI_X + YONSEI_HALF, -640),
                      (YONSEI_X - YONSEI_HALF, -640)])
    # (its walks: 5.6 m either side down to the rows of shop houses; under the bridge and before it the whole opening,
    # wider on the east side as in the 1997 photos)
    fw = YONSEI_HALF + YONSEI_WALK + 0.6
    yonsei_walk = unary_union([
        Polygon([(YONSEI_X - fw, y_top - SW_S - 1.0), (YONSEI_X + fw, y_top - SW_S - 1.0), (YONSEI_X + fw, -640), (YONSEI_X - fw, -640)]),
        Polygon([(BRIDGE[0] + 0.4, y_top - SW_S - 1.0), (BRIDGE[1] - 0.4, y_top - SW_S - 1.0), (BRIDGE[1] - 0.4, -507.0),
                 (BRIDGE[0] + 0.4, -507.0)])]).difference(yonsei)
    # ---- the banks' footprint
    sec = np.array([[v if v is not None else np.nan for v in r] for r in secs], float)
    cn = sec[:, :2] + sec[:, 2:4] * (sec[:, 4] + sec[:, 5])[:, None]
    cs = sec[:, :2] - sec[:, 2:4] * (sec[:, 4] + sec[:, 8])[:, None]
    bank = Polygon([tuple(p) for p in cn] + [tuple(p) for p in cs[::-1]]).buffer(0)
    opening = Polygon([(BRIDGE[0], -440), (BRIDGE[1], -440), (BRIDGE[1], -530), (BRIDGE[0], -530)])
    bank_paint = bank.buffer(1.0).difference(opening)
    # ---- the town's ground: south of the rails everything; north of them where the road has left them (the yards
    # west of the traffic island, the station's side in the east)
    south = Polygon([tuple(p) for p in cs] + [(720, cs[-1][1]), (720, -810), (-660, -810), (-660, cs[0][1])]).buffer(0)
    between = zone.difference(south).difference(bank.buffer(2.0)).difference(Polygon(
        [tuple(p) for p in bound] + [tuple(p) for p in back_s[::-1]]).buffer(0)).difference(mouth.buffer(1.0))
    yards = unary_union([g for g in getattr(between, 'geoms', [between])
                         if g.geom_type == 'Polygon' and g.area > 200]).intersection(
        unary_union([Polygon([(-660, -810), (-345, -810), (-345, 0), (-660, 0)]),
                     Polygon([(128, -810), (720, -810), (720, 0), (128, 0)])]))
    ground_town = unary_union([south.difference(bank.buffer(1.0)), yards]).intersection(zone).buffer(0)
    # ---- the blocks: OSM's outlines as boxes (the streets are the 1990s', the houses on them mostly newer and
    # bigger: lower here, with the red roofs of the 1995 photo on the small ones)
    els = json.load(open(os.path.join(ROOT, 'data/raw/osm_gate_south.json')))['elements']
    keep = ground_town.buffer(-1.0)
    shapely.prepare(keep)
    # 연세로 from the bridge south: rows of three to five storey shop houses wall to wall on both sides (the 1995 photo;
    # OSM has the few big outlines of today there), broken where the side streets cross; 창천교회 by the bank east of the
    # corner (the later aerial photo, the anthologies' street maps)
    face = YONSEI_HALF + YONSEI_WALK
    rows, fronts = [], {-1: [], 1: []}
    for side in (1, -1):
        for ya, yb in ((-509.5, -552.0), (-563.0, -640.0)):
            yy = ya
            while yy - 6.0 > yb:
                wdt = min(rnd.uniform(6.0, 11.5), yy - yb)
                if yy - wdt - yb < 6.0:
                    wdt = yy - yb
                dep = rnd.uniform(10.0, 15.0)
                cx, cy = YONSEI_X + side * (face + dep / 2), yy - wdt / 2
                hs = [ground(cx + u, cy + v) for u in (-dep / 2, dep / 2) for v in (-wdt / 2, wdt / 2)]
                b = [round(cx, 2), round(cy, 2), round(dep, 2), round(wdt - 0.15, 2), 0.0, round(min(hs) - 0.3, 2),
                     3 + int(rnd.random() * 2.6), rnd.choice([0, 1, 2, 3, 3]), 3 if rnd.random() < 0.6 else 2, 0, 2,
                     int(rnd.random() < 0.7)]
                rows.append(b)
                fronts[side].append(b)
                yy -= wdt
    ch = (-50.0, -523.0, 27.0, 13.0)
    church = [ch[0], ch[1], ch[2], ch[3], 0.0, round(min(ground(ch[0] + u, ch[1] + v) for u in (-13, 13) for v in (-6, 6)) - 0.3, 2),
              3, 0, 1, 2, 0, 0]
    row_poly = unary_union([Polygon([(b[0] - b[2] / 2, b[1] - b[3] / 2), (b[0] + b[2] / 2, b[1] - b[3] / 2),
                                     (b[0] + b[2] / 2, b[1] + b[3] / 2), (b[0] - b[2] / 2, b[1] + b[3] / 2)]) for b in rows + [church]])
    busy = unary_union([p.buffer(3.0) for p in taken] + [yonsei.buffer(YONSEI_WALK - 0.5), bank.buffer(3.0), row_poly.buffer(1.5)])
    shapely.prepare(busy)
    blocks = rows + [church]
    for e in els:
        if 'building' not in e['tags'] or e['id'] in MODERN or len(e['geometry']) < 4:
            continue
        pg = Polygon([_xy(p) for p in e['geometry']]).buffer(0)
        if pg.is_empty or pg.geom_type != 'Polygon' or pg.area < 22:
            continue
        cx, cy = pg.centroid.x, pg.centroid.y
        if not (-640 < cx < 690 and cy > -795) or not shapely.contains_xy(keep, cx, cy) or shapely.intersects(busy, pg):
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
        L, W = L * (0.82 + 0.16 * fill) - 0.3, W * (0.82 + 0.16 * fill) - 0.3       # (an L or T plan: a smaller box)
        mc = pg.minimum_rotated_rectangle.centroid
        area = L * W
        r = rnd.random()
        on_main = abs(mc.x - YONSEI_X) < 45 and mc.y > -640
        if on_main:
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
             wall, roof, int(hip), int(on_main), int(rnd.random() < 0.6)]
        blocks.append(b)
    # Where OSM has no outline today (the station's plaza and car parks, the big blocks of the 2000s) the 1995 photo
    # has the same low houses wall to wall: small ones on a loose grid, off the streets, 25 m clear of the rails
    streets = unary_union([LineString([_xy(q) for q in e['geometry']]).buffer(
        {'primary': 13.0, 'secondary': 8.0, 'tertiary': 7.0}.get(e['tags']['highway'].replace('_link', ''), 3.6))
        for e in els if 'highway' in e['tags'] and len(e['geometry']) > 1])
    used = unary_union([_rect(b).buffer(2.2) for b in blocks] + [streets, rail.ls.buffer(25.0), busy])
    shapely.prepare(used)
    n_fill = 0
    for gy in np.arange(-792.0, -300.0, 11.5):
        for gx in np.arange(-650.0, 695.0, 11.5):
            cx, cy = gx + rnd.uniform(-1.6, 1.6), gy + rnd.uniform(-1.6, 1.6)
            L, W, ang = rnd.uniform(7.0, 10.0), rnd.uniform(6.0, 8.2), rnd.choice([0.0, math.pi / 2]) + rnd.uniform(-0.12, 0.12)
            b = [round(cx, 2), round(cy, 2), round(L, 2), round(W, 2), round(ang, 4), 0.0, 1 + (rnd.random() < 0.55),
                 rnd.choice([0, 0, 1, 1, 2, 3]), 0 if rnd.random() < 0.66 else 1 if rnd.random() < 0.6 else 2, 1, 0, 0]
            if rnd.random() < 0.22:
                b[6], b[8], b[9], b[11] = 2 + (rnd.random() < 0.4), 3 if rnd.random() < 0.5 else 2, 0, int(rnd.random() < 0.6)
            r_ = _rect(b)
            cs_ = np.array(r_.exterior.coords)
            if not shapely.contains_xy(keep, cs_[:, 0], cs_[:, 1]).all() or shapely.intersects(used, r_):
                continue
            b[5] = round(min(ground(x_, y_) for x_, y_ in cs_[:4]) - 0.3, 2)
            blocks.append(b)
            n_fill += 1
    # the shops on 연세로 from the bridge south, as the anthologies' street maps name them (2019 문집 25쪽, 2021 문집
    # 22쪽), a sign over each ground floor on the street's side
    names = {1: ['연세식품', '사진관', '독수리다방', '초원각', '독수리약국', '알서림', '새마을금고', '오락실'],
             -1: ['독수리문구', '시골분식', '연세문화사', '상아탑분식', '자뎅', '연희식당', '오늘의 책', '신촌반점']}
    signs, k_sign = [], 0
    for side in (1, -1):
        for i, b in enumerate(fronts[side][:len(names[side])]):
            # [x, y, z of its middle, the way it faces (rad), width, cell of the sign atlas]
            signs.append([round(b[0] - side * (b[2] / 2 + 0.14), 2), b[1], round(b[5] + 0.3 + 3.3, 2),
                          0.0 if side < 0 else round(math.pi, 4), round(min(b[3] - 0.6, 6.4), 2), (0 if side > 0 else 8) + i])
    # ---- lane paint, kerbs, the crossing before the gate
    paint = []
    sx = road.P[:, 0]
    inner = (sx > -470) & (sx < 330)
    # (the 1997 vertical photos: a strip between the two ways, hatched from 60 m west of the junction's box to it and
    # planted for 45 m west of that; three dashed lines and the kerb lane's each side; the junction's box before 연세로
    # and the gate's mouth, the zebra east of it, the stop lines before the box and east of the zebra, another zebra
    # over 연세로's mouth)
    at = lambda x, o=0.0: (x, float(np.interp(x, road.P[:, 0], road.P[:, 1])) + o)
    open_x = (BOX_X[0] - 3.5, CROSS_X[1] + 3.5)        # (no lines through the junction and the zebra)
    for a, b in ((-470.0, open_x[0]), (open_x[1], 330.0)):
        part = (sx > a) & (sx < b)
        for sgn in (1, -1):
            paint.append(dict(kind='yellow', w=0.15, pts=R2(road.off(sgn * (MID / 2 - 0.08))[part])))
            for kk in range(1, LANES):
                paint.append(dict(kind='white_dash', w=0.12, pts=R2(road.off(sgn * (MID / 2 + LANE_W * kk))[part])))
    hatch_x = (BOX_X[0] - 48.0, BOX_X[0] - 4.5)
    for x in np.arange(hatch_x[0], hatch_x[1], 3.0):   # the hatched strip's bars
        paint.append(dict(kind='yellow', w=0.3, pts=R2([at(x, -MID / 2 + 0.2), at(x + 1.6, MID / 2 - 0.2)])))
    cross_x = CROSS_X
    zebra = []
    kn = float(np.interp(sum(cross_x) / 2, kerb_n[:, 0], kerb_n[:, 1]))
    ks = float(np.interp(sum(cross_x) / 2, kerb_s[:, 0], kerb_s[:, 1]))
    yy = kn - 0.7
    while yy - 0.6 > ks + 0.5:
        zebra.append(R2([(cross_x[0], yy), (cross_x[1], yy), (cross_x[1], yy - 0.6), (cross_x[0], yy - 0.6)]))
        yy -= 1.2
    for xs, sgn in ((BOX_X[0] - 3.5, -1), (cross_x[1] + 3.5, 1)):                # stop lines: eastbound, westbound
        ya, yb = at(xs, sgn * MID / 2)[1], at(xs, sgn * (HW - GUTTER))[1]
        zebra.append(R2([(xs - 0.25, ya), (xs + 0.25, ya), (xs + 0.25, yb), (xs - 0.25, yb)]))
    bn, bs = at(sum(BOX_X) / 2, HW - 2.9)[1], at(sum(BOX_X) / 2, -(HW - 1.9))[1]
    for xa, ya, xb, yb in ((BOX_X[0], bn, BOX_X[1], bn - 0.4), (BOX_X[0], bs + 0.4, BOX_X[1], bs),
                           (BOX_X[0], bn, BOX_X[0] + 0.4, bs), (BOX_X[1] - 0.4, bn, BOX_X[1], bs)):      # the box
        zebra.append(R2([(xa, ya), (xb, ya), (xb, yb), (xa, yb)]))
    ym = sum(YZEBRA) / 2
    xx = YONSEI_X - YONSEI_HALF + 0.5
    while xx + 0.55 < YONSEI_X + YONSEI_HALF - 0.4:    # 연세로's zebra: two rows of bars
        for ya, yb in ((YZEBRA[0], ym + 0.3), (ym - 0.3, YZEBRA[1])):
            zebra.append(R2([(xx, ya), (xx + 0.55, ya), (xx + 0.55, yb), (xx, yb)]))
        xx += 1.1
    # kerbs: runs of each line, broken at the gate's mouth and at 연세로
    def runs(line, gaps):
        out, cur = [], []
        for q in line:
            if any(a <= q[0] <= b for a, b in gaps) or not (-470 < q[0] < 330):
                if len(cur) > 1:
                    out.append(R2(cur))
                cur = []
            else:
                cur.append(q)
        if len(cur) > 1:
            out.append(R2(cur))
        return out
    mx = [q[0] for q in kerb_n if mouth.buffer(0.5).contains(Point(*q))]       # (where the mouth meets the kerb's line)
    kerbs = runs(kerb_n, [(min(mx) - 1.5, max(mx) + 1.5)]) + runs(kerb_s, [(BRIDGE[0] + 0.4, BRIDGE[1] - 0.4)])
    # ---- lanes for the cars (west -> east on the south side), the kerb lanes for the buses
    lanes = []
    drive = (sx > -500) & (sx < 345)
    for sgn in (-1, 1):
        for kk in range(LANES):
            pts = road.off(sgn * (MID / 2 + LANE_W * (kk + 0.5)))[drive]
            lanes.append(dict(kind='bus' if kk == LANES - 1 else 'car', pts=R2(pts if sgn < 0 else pts[::-1])))
    # ---- the walker's barrier: along the north kerb, the carriageway side, the crossing too: the walk ends on
    # 성산로's north sidewalk outside the gate, 연세로 and 신촌 로터리 are seen but not walked to (tools/
    # sinchon_rotary.py's walls round their walks stay, out of reach).  Its north edge goes out as town.limit: the web
    # sets no walker down south of it (web/src/main.js beyondGate: the map, the bird's eye view, the start list)
    barrier = []
    bl = road.off(HW - 0.9)
    bh = road.off(HW - 0.1)
    limit = []
    for k in range(0, len(bl) - 3, 3):
        if not (-480 < bl[k][0] < 340):
            continue
        barrier.append(R2([bl[k], bl[k + 3], bh[k + 3], bh[k]]))
        limit.append(bh[k])
    # ---- bus stops (the 1995 photo: two green-roofed shelters at the kerb west of the mouth) and lamps
    stops = []
    for x in (-203.0, -184.0):
        k = int(np.argmin(np.abs(sx - x)))
        q = road.P[k] + road.N[k] * (HW + 2.1)
        stops.append([round(float(q[0]), 2), round(float(q[1]), 2), round(math.atan2(road.T[k][1], road.T[k][0]), 4), 11.0])
    props = []
    for k in range(6, len(sx) - 6, 11):
        if not (-440 < sx[k] < 300):
            continue
        a = math.atan2(road.T[k][1], road.T[k][0])
        for sgn, off, rot in ((1, HW + 0.7, a), (-1, HW + 0.7, a + math.pi)):
            q = road.P[k + (5 if sgn < 0 else 0)] + road.N[k + (5 if sgn < 0 else 0)] * sgn * off
            if mouth.buffer(2.0).contains(Point(*q)) or BRIDGE[0] - 3 < q[0] < BRIDGE[1] + 3 and sgn < 0:
                continue
            props.append(['lamp_arm', round(float(q[0]), 2), round(float(q[1]), 2), round(rot, 3)])
    # ---- trees: tall slender ones on the banks (the 1995 photo: both slopes west of the bridge), thicker and lower
    # east of it on the south slope; a row on the wide sidewalk west of the gate
    trees, shrubs = [], []
    for k in range(0, len(secs), 1):
        x, y, nx, ny, hw, dN, zN, _, dS, zS = secs[k][:10]
        if BRIDGE[0] - 9 < x < BRIDGE[1] + 9 or not (-470 < x < 215):
            continue
        west = x < BRIDGE[0]
        for side, d in ((1, dN), (-1, dS)):
            if d < 4.0:
                continue
            p_tree = (0.85 if west else 0.3) if side > 0 else (0.9 if west else 0.7)
            for row in range(2 if d > 7 else 1):
                if rnd.random() > p_tree:
                    continue
                o = hw + d * (rnd.uniform(0.3, 0.55) if row == 0 else rnd.uniform(0.6, 0.85))
                jx = rnd.uniform(-2.5, 2.5)
                q = (x + nx * side * o - ny * jx, y + ny * side * o + nx * jx)
                if rnd.random() < (0.6 if west else 0.3):
                    trees.append(['poplar', round(q[0], 2), round(q[1], 2), round(rnd.uniform(0.5, 0.8), 2), round(rnd.uniform(0, 6.28), 2)])
                else:
                    trees.append([rnd.choice(['zelkova', 'oak', 'zelkova_young']), round(q[0], 2), round(q[1], 2),
                                  round(rnd.uniform(0.45, 0.7), 2), round(rnd.uniform(0, 6.28), 2)])
            if rnd.random() < 0.7:
                o = hw + d * rnd.uniform(0.15, 0.9)
                jx = rnd.uniform(-3, 3)
                shrubs.append(['topiary_round', round(x + nx * side * o - ny * jx, 2), round(y + ny * side * o + nx * jx, 2),
                               round(rnd.uniform(0.9, 1.8), 2), round(rnd.uniform(0, 6.28), 2)])
    for k in range(4, len(sx) - 4, 3):
        if not (-400 < sx[k] < -150) or any(abs(sx[k] - s_[0]) < 9 for s_ in stops):
            continue
        wdt = b_off[k] - HW
        if wdt < 7.0:
            continue
        q = road.P[k] + road.N[k] * (HW + min(wdt - 2.0, 9.0))
        if mouth.buffer(2.0).contains(Point(*q)):
            continue
        trees.append(['ginkgo', round(float(q[0]), 2), round(float(q[1]), 2), round(rnd.uniform(0.8, 1.0), 2), round(rnd.uniform(0, 6.28), 2)])
    # along the campus's edge of the wide sidewalk west of the gate, the dark row of big trees of the 1995 photo
    for k in range(2, len(sx) - 2, 2):
        if not (-420 < sx[k] < -150) or b_off[k] - HW < 9.0:
            continue
        q = bound[k] - road.N[k] * 2.2 + road.T[k] * rnd.uniform(-1.5, 1.5)
        if mouth.buffer(2.0).contains(Point(*q)):
            continue
        trees.append([rnd.choice(['zelkova', 'zelkova', 'pine', 'oak']), round(float(q[0]), 2), round(float(q[1]), 2),
                      round(rnd.uniform(0.6, 0.85), 2), round(rnd.uniform(0, 6.28), 2)])
    # the strip between the road and the bank west of the gate (the 1995 photo's traffic island: lawn and clipped
    # shrubs between the road and the loop under the bank): shrubs on the lawn
    isl = [g for g in getattr(between, 'geoms', [between]) if g.geom_type == 'Polygon' and g.area > 200]
    for g in isl:
        g2 = g.intersection(Polygon([(-345, -620), (-125, -620), (-125, 0), (-345, 0)])).buffer(-2.5)
        if g2.is_empty:
            continue
        minx, miny, maxx, maxy = g2.bounds
        for _ in range(int(g2.area / 28)):
            q = (rnd.uniform(minx, maxx), rnd.uniform(miny, maxy))
            if g2.contains(Point(*q)):
                shrubs.append([rnd.choice(['topiary_round', 'topiary_round', 'hedge_blob']), round(q[0], 2), round(q[1], 2),
                               round(rnd.uniform(0.8, 1.3), 2), round(rnd.uniform(0, 6.28), 2)])
    # the planted strip between the two ways west of the hatched one (the 1997 photos: dark round crowns in a row,
    # 45 m): clipped shrubs
    for x in np.arange(hatch_x[0] - 45.0, hatch_x[0] - 1.0, 3.2):
        shrubs.append(['topiary_round', round(float(x), 2), round(at(float(x))[1], 2), round(rnd.uniform(0.7, 0.9), 2),
                       round(rnd.uniform(0, 6.28), 2)])
    # (the campus's list holds a fixed number of the town's trees, tools/build_campus.py TOWN_TREE_SLOTS: those
    # nearest the gate first, so that the higher banks' many trees are not all spent far west of it)
    trees.sort(key=lambda t_: abs(t_[1] - YONSEI_X))
    town = dict(
        road=dict(pts=R2(road.P), z=[round(float(v), 2) for v in pl['road_z']], half=HW, lanes=LANES, lane_w=LANE_W),
        rail=dict(z=rail_z, top=round(top, 2), n=[list(p) for p in TRACK_N if X0 <= p[0] <= X1],
                  s=[list(p) for p in TRACK_S if X0 <= p[0] <= X1], shoulder=SHOULDER, sections=secs),
        bridge=dict(x=list(BRIDGE), pier=YONSEI_X, yonsei=[YONSEI_X, YONSEI_HALF, YONSEI_WALK]),
        paint=paint, zebra=zebra, kerbs=kerbs, lanes=lanes, stops=stops, blocks=blocks, signs=signs,
        church=church[:4], names=names[1] + names[-1], filled=n_fill, limit=R2(limit))
    paints = dict(clear=[zone, inside], asphalt=[road_poly, mouth_a, yonsei, ground_town],
                  pavers=[walk_n.difference(mouth), walk_s, yonsei_walk, inside],
                  dirt=[bank_paint])
    paths = [dict(kind='primary', w=2 * HW, pts=[[round(float(x), 1), round(float(y), 1)] for x, y in road.P[::3]]),
             dict(kind='tertiary', w=2 * YONSEI_HALF, pts=[[YONSEI_X, round(y_top, 1)], [YONSEI_X, -640.0]])]       # (the map)
    return town, dict(trees=trees, shrubs=shrubs, props=props, colliders=barrier, paints=paints, zone=zone, bank=bank, paths=paths,
                      mouth=mouth,
                      road_poly=road_poly.union(walk_s), cross_box=(cross_x[0], cross_x[1], ks, kn), walk_s=walk_s)
