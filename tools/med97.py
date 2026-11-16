"""의료원 둘레 주차장 셋의 1997년 땅 (#189; reference/고증/2.10_세운_차.md 「의료원 주차장 셋의 땅」, 3.1.2).
tools/build_campus.py 가 부른다.

    took, info = med97.grade(Hn, X, Y, FIXED, halls, harmonic_fill, road_ls, road_hw)   # 심기가 끝난 뒤, 저장 바로 앞
    med97.paint()               # 땅 지도에만(늦게): 새 아스팔트 · 둑의 잔디
    med97.trees_aside(trees)    # 새 주차장 안에 무작위로 심긴 나무를 목록 제자리에서 가장자리 밖으로

Frame: campus metres, x east, y north.  Heights: the 1997-07-28 scans (자료 Q), every pair of the four frames that see
the place (27/17 · 27/16 · 26/16 · 26/15) on its own, a point kept where two pairs or more agree (correlation 0.7 or
more, spread under 0.4 m).  Near these lots the photos stand on the game's roads (치과대학병원 남쪽 길 −0.4 m, 동쪽 주차장
북서 칸 +0.1 m), so their heights go in as they are.  Every absolute height written here is above sea level (해발,
taken up to the working datum where it is read: tools/datum.py): EAST_Z, NE_PROF, HEART_Z, DENT_Z.

- 동쪽 큰 주차장 (EAST_LOT): one paved platform at 40.5 m (a plane through 134 points, rms 0.45 m, 0.9 % up to the
  north) where the game's ground fell from 45 m at its north end to 31 m at its south (the 2005 hospital's site, painted
  asphalt).  Along its north-east side the road down to 성산로 falls 47 → 34 m past it (NE_PROF: across-road profiles
  every 5 m), 3.5 m under the lot at s 30 and 7 m at s 60: the lot is held up by a wall, its south-east edge by a wooded
  bank 10 m down to 성산로.  The 5 m grid makes both a steep bank one cell wide (grass: BANK).  The road's lower
  end eases to the ground it meets beyond 성산로's east end (since 2026-11-15 gate_town has the road on the same
  photos to its end and tools/town97.py its run on north-east: 0.2 m off the profile; 3 - 5 m before).  Where
  성산로's kerb lane passes the bank's foot, the nodes of the cells it crosses stand at the road's height (KERB_LANE).
- 심장혈관병원 북쪽 (HEART_LOT): paved, three rows and a row along the east, 44 → 46 m to the north (5 %); the game had
  a lawn rising to 45.1 m.
- 치과대학병원 서쪽 · 음악대학 동쪽 (DENT_LOT): paved, the long double row of slanting stalls and the rows along both
  sides, 60 → 53 m to the south (7.7 %); the game had lawn and paths at about the same heights.
- Nothing here draws from build_campus.py's `rng`.
"""
# (every absolute height written in this file's code is above sea level, 해발: datum.up · up3 · up_at · up_plane take it
# up to the working datum the ground is laid on, 해발 + tilt, where it is read: tools/datum.py.  The heights quoted
# in the comments are 해발 too)
import math

import numpy as np
import datum
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, unary_union


def plane(c, x, y):
    return c[0] + c[1] * (np.asarray(x) - 300.0) + c[2] * (np.asarray(y) + 200.0)


# 동쪽 큰 주차장: the paved platform's edge on the scans (26/16 · 27/17 at its own height), the cars' rows inside
EAST_LOT = Polygon([(292.0, -150.0), (306.0, -152.0), (318.0, -168.8), (348.5, -214.6), (350.8, -217.8), (311.5, -251.0),
                    (300.0, -254.0), (296.0, -252.0), (285.5, -225.0), (290.5, -205.0), (289.5, -180.0), (288.0, -160.0)])
EAST_Z = datum.up_plane((40.65, -0.0087, 0.0055), 300.0, -200.0)
# the road down to 성산로 north-east of it: s along the line from NE_O (heading NE_T), left = north-east
NE_O, NE_T = np.array([314.8, -152.8]), np.array([0.5694, -0.8221])
NE_N = np.array([-NE_T[1], NE_T[0]])
NE_PROF = datum.up_at([(0.0, 41.38), (5.0, 40.78), (10.0, 40.07), (20.0, 38.46), (25.0, 37.96), (30.0, 37.56), (35.0, 36.65), (40.0, 35.95),
           (45.0, 35.64), (50.0, 34.94), (55.0, 34.23), (60.0, 33.63), (65.0, 33.12), (70.0, 32.82), (75.0, 31.51), (80.0, 30.71),
           (85.0, 30.5), (90.0, 30.6), (95.0, 30.39)],
                      [(314.8, -152.8), (317.6, -156.9), (320.5, -161.0), (326.2, -169.2), (329.0, -173.4), (331.9, -177.5),
                       (334.7, -181.6), (337.6, -185.7), (340.4, -189.8), (343.3, -193.9), (346.1, -198.0), (349.0, -202.1),
                       (351.8, -206.2), (354.7, -210.3), (357.5, -214.5), (360.4, -218.6), (363.2, -222.7), (366.0, -226.8),
                       (368.9, -230.9)])
NE_SIDE = (-4.0, 12.0)            # its bed across (the lot's wall at -6.5 m, the far sidewalk's back)
SE_EDGE = ((350.8, -217.8), (300.0, -254.0))   # the lot's south-east edge (the wooded bank's top)
NE_S = (8.0, 88.0)                # graded from here to where 성산로's bed begins
# 심장혈관병원 북쪽 · 치과대학병원 서쪽: the paved yards' edges on the scans (the cars' rows 0.8 m in or more)
HEART_LOT = Polygon([(134.0, -55.0), (158.0, -59.0), (167.0, -69.0), (181.0, -83.0), (186.0, -95.0), (174.0, -105.0),
                     (116.0, -104.0), (115.0, -97.0), (124.0, -80.0), (131.0, -62.0)])
HEART_Z = datum.up_plane((43.91, 0.0333, 0.03), 300.0, -200.0)
DENT_LOT = Polygon([(287.0, 29.0), (331.0, 29.0), (330.0, 8.0), (324.0, -25.0), (314.0, -65.0), (276.0, -65.0), (275.0, -55.0),
                    (282.0, -25.0), (285.0, 0.0)])
DENT_Z = datum.up_plane((39.66, -0.0264, 0.0711), 300.0, -200.0)
LOTS = [('동쪽 큰 주차장', EAST_LOT, EAST_Z, 3.0), ('심장혈관병원 북쪽', HEART_LOT, HEART_Z, 2.0),
        ('치과대학병원 서쪽', DENT_LOT, DENT_Z, 2.0)]
RING = 18.0                       # the ground eased in (harmonic) this far out of each lot
HALL_PAD = 7.0                    # the halls' feet stay as they were (their bases read the ground under their corners)
BANK = []                         # (set by grade: the east lot's wall and bank, for paint)


def ne_sd(x, y):
    dx, dy = np.asarray(x) - NE_O[0], np.asarray(y) - NE_O[1]
    return dx * NE_T[0] + dy * NE_T[1], dx * NE_N[0] + dy * NE_N[1]


def ne_band(s0=None, s1=None):
    s0, s1 = NE_S if s0 is None else (s0, s1)
    q = lambda s, o: tuple(NE_O + NE_T * s + NE_N * o)
    return Polygon([q(s0, NE_SIDE[0]), q(s1, NE_SIDE[0]), q(s1, NE_SIDE[1]), q(s0, NE_SIDE[1])])


KERB_LANE = (3.85, 0.75)          # the kerb lane's band: from (road_hw - 3.85) to (road_hw - 0.75) m off the road's middle
                                  # (gate_town: LANE_W 3.1, GUTTER 0.75)
KERB_BOX = (280.0, 380.0, -300.0, -180.0)      # (x0, x1, y0, y1): along the east lot's bank only


def _side(ls, x, y):
    """which side of the line ls the point is on (+ left)"""
    s = ls.project(Point(x, y))
    a, b = ls.interpolate(max(s - 0.5, 0.0)), ls.interpolate(min(s + 0.5, ls.length))
    return (b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x)


def _road_z(H, ls, x, y, step, half):
    """the ground on the road's middle abreast of (x, y) (gate_town levels its bed across)"""
    m = ls.interpolate(ls.project(Point(x, y)))
    fx, fy = (m.x + half) / step, (m.y + half) / step
    i, j = int(fx), int(fy)
    ax, ay = fx - i, fy - j
    return float(H[j, i] * (1 - ax) * (1 - ay) + H[j, i + 1] * ax * (1 - ay) + H[j + 1, i] * (1 - ax) * ay
                 + H[j + 1, i + 1] * ax * ay)


def _sec(road, ls, s, o, side):
    """an offset o off the road's middle at s on the section as laid (gate_town.sec_off: the north kerb along 의료원
    where the 1997 scans have it); as it is without the road's Line"""
    if road is None or side < 0 or getattr(road, 'hn', None) is None:
        return o
    import gate_town
    return float(gate_town.sec_off(o, np.interp(s, road.cum, road.hn)))


def on_road(X, Y, road_ls, road_hw, road=None, pad=2.5):
    """the grid nodes within pad m past the road's kerbs (its bed: gate_town.plan), on the north side the kerb as laid"""
    pts = shapely.points(np.stack([X.ravel(), Y.ravel()], 1))
    d = shapely.distance(pts, road_ls)
    if road is None or getattr(road, 'hn', None) is None:
        return (d <= road_hw + pad).reshape(X.shape)
    import gate_town
    s = shapely.line_locate_point(road.ls, pts)
    k = np.clip(np.searchsorted(road.cum, s), 1, len(road.cum) - 1)
    side = (X.ravel() - road.P[k, 0]) * road.N[k, 0] + (Y.ravel() - road.P[k, 1]) * road.N[k, 1]
    hw = np.where(side > 0, np.interp(s, road.cum, gate_town.bed_n(road)) - 2.5, road_hw)
    return (d <= hw + pad).reshape(X.shape)


def kerb_lane_nodes(ls, hw, shape, step, half, side, road=None):
    """the grid nodes of every cell the kerb lane's band (KERB_LANE) crosses on the given side, inside KERB_BOX"""
    out = np.zeros(shape, bool)
    x0, x1, y0, y1 = KERB_BOX
    for s in np.arange(0.0, ls.length, 0.5):
        a, b = ls.interpolate(s), ls.interpolate(min(s + 0.5, ls.length))
        t = np.array([b.x - a.x, b.y - a.y])
        if not np.any(t):
            continue
        t /= np.linalg.norm(t)
        n = np.array([-t[1], t[0]]) * side
        for o in np.arange(_sec(road, ls, s, hw - KERB_LANE[0], side), _sec(road, ls, s, hw - KERB_LANE[1], side) + 0.01, 0.5):
            x, y = a.x + n[0] * o, a.y + n[1] * o
            if x0 < x < x1 and y0 < y < y1:
                j, i = int(math.floor((y + half) / step)), int(math.floor((x + half) / step))
                out[j:j + 2, i:i + 2] = True
    return out


def grade(Hn, X, Y, FIXED, halls, fill, road_ls, road_hw, step=5.0, half=800.0, road=None):
    """The three lots on the photos' planes, the road north-east of the east lot on its profile, the ground round them
    eased in (fill: build_campus.py harmonic_fill) as far as RING out; the halls' feet (HALL_PAD), 성산로's bed
    (road_ls, road_hw: gate_town's middle line and half width, + 2.5 m) and nodes another rule set (FIXED) stay.
    Returns the nodes set (to be FIXED) and a summary."""
    H0 = Hn.copy()
    near_hall = shapely.contains_xy(unary_union([h.buffer(HALL_PAD) for h in halls]), X, Y)
    keep = FIXED | near_hall | on_road(X, Y, road_ls, road_hw, road)
    took = np.zeros(X.shape, bool)
    info = {}
    # the road north-east of the east lot: its profile, eased at the lower end to 성산로's bed as the game has it
    s, o = ne_sd(X, Y)
    band = (s >= NE_S[0]) & (s <= NE_S[1]) & (o >= NE_SIDE[0]) & (o <= NE_SIDE[1]) & ~keep
    sj = NE_S[1]
    qj = NE_O + NE_T * (sj + 2.0) + NE_N * 4.0
    zj = float(H0[int(round((qj[1] + half) / step)), int(round((qj[0] + half) / step))])
    dj = float(np.interp(sj + 2.0, *zip(*NE_PROF))) - zj
    w = np.clip((s - 20.0) / (sj + 2.0 - 20.0), 0.0, 1.0)
    zr = np.interp(s, *zip(*NE_PROF)) - dj * w
    Hn[band] = zr[band]
    took |= band
    info['ne_road'] = (int(band.sum()), round(dj, 2))
    # 성산로's kerb lane past the east lot's bank (the buses' lane, its band KERB_LANE m north of the road's middle):
    # every node of a 5 m cell that band crosses stands at the road's own height abreast of it, the lot's own nodes
    # aside.  The bank's foot stood there 1.5 - 4.6 m over the road (20 - 21 m from its middle, just past the bed
    # gate_town levels), and a bus on that lane rolled 22 deg at x 318 (now 1.2: kerb_lane_tilt in the build's line)
    ring = shapely.contains_xy(unary_union([p.buffer(pad + RING) for _, p, _, pad in LOTS] + [ne_band().buffer(10.0)]), X, Y)
    lot_side = np.sign(_side(road_ls, EAST_LOT.centroid.x, EAST_LOT.centroid.y))
    kn = kerb_lane_nodes(road_ls, road_hw, X.shape, step, half, lot_side, road) & ring & ~keep & ~band \
        & ~shapely.contains_xy(EAST_LOT.buffer(LOTS[0][3]), X, Y)
    jj, ii = np.nonzero(kn)
    zk = np.array([_road_z(H0, road_ls, X[j, i], Y[j, i], step, half) for j, i in zip(jj, ii)])
    Hn[jj, ii] = zk
    keep = keep | kn
    took |= kn
    info['kerb_lane'] = int(kn.sum())
    # the lots
    for nm, poly, c, pad in LOTS:
        m = shapely.contains_xy(poly.buffer(pad), X, Y) & ~keep & ~band
        Hn[m] = plane(c, X[m], Y[m])
        took |= m
        d = Hn[m] - H0[m]
        info[nm] = (int(m.sum()), round(float(d.min()), 1) if m.any() else 0.0, round(float(d.max()), 1) if m.any() else 0.0)
    # round them: one smooth surface out to what stays
    free = ring & ~took & ~keep
    if free.any():
        fill(free)
    info['ring'] = int(free.sum())
    # the east lot's wall and bank (1997): grass on the game's map, between the lot's edge and the road's kerb on the
    # north-east and down to 성산로's bed on the south-east (straight edges: the 5 m cells' outline would zigzag)
    BANK.clear()
    q = lambda s_, o_: tuple(NE_O + NE_T * s_ + NE_N * o_)
    ne = Polygon([q(12.0, -9.0), q(80.0, -11.0), q(80.0, NE_SIDE[0]), q(12.0, NE_SIDE[0])])
    a_, b_ = np.array(SE_EDGE[0]), np.array(SE_EDGE[1])
    t_ = (b_ - a_) / np.linalg.norm(b_ - a_)
    n_ = np.array([-t_[1], t_[0]])                      # (south-east, away from the lot)
    se = Polygon([tuple(a_ - t_ * 6.0), tuple(b_ + t_ * 4.0), tuple(b_ + t_ * 4.0 + n_ * 30.0), tuple(a_ - t_ * 6.0 + n_ * 30.0)])
    band = unary_union([ne, se]).difference(EAST_LOT.buffer(0.3)).difference(ne_band(0.0, 100.0)) \
        .difference(road_ls.buffer(road_hw))
    BANK.extend(g for g in getattr(band, 'geoms', [band]) if g.geom_type == 'Polygon' and g.area > 1.0)
    moved = np.abs(Hn - H0)
    info['moved'] = (int((moved > 0.05).sum()), round(float(moved.max()), 1))
    info['kerb_lane_tilt'] = kerb_lane_tilt(Hn, road_ls, road_hw, lot_side, step, half, road)
    return took | free, info


def kerb_lane_tilt(H, ls, hw, side, step, half, road=None):
    """the most a car leans (roll, pitch in degrees) on the kerb lane's middle inside KERB_BOX: its four tyres
    1.33 m ahead and behind, 0.72 m to either side, on the grid as web/src/life.js Path.setTracks reads it"""
    def h(x, y):
        fx, fy = (x + half) / step, (y + half) / step
        i, j = int(fx), int(fy)
        ax, ay = fx - i, fy - j
        return H[j, i] * (1 - ax) * (1 - ay) + H[j, i + 1] * ax * (1 - ay) + H[j + 1, i] * (1 - ax) * ay + H[j + 1, i + 1] * ax * ay
    x0, x1, y0, y1 = KERB_BOX
    rl = pt = 0.0
    o = hw - (KERB_LANE[0] + KERB_LANE[1]) / 2
    for s in np.arange(1.0, ls.length - 1.0, 1.0):
        a, b = ls.interpolate(s - 1.0), ls.interpolate(s + 1.0)
        t = np.array([b.x - a.x, b.y - a.y])
        t /= np.linalg.norm(t)
        n = np.array([-t[1], t[0]]) * side
        m = ls.interpolate(s)
        c = np.array([m.x, m.y]) + n * _sec(road, ls, s, o, side)
        if not (x0 < c[0] < x1 and y0 < c[1] < y1):
            continue
        q = [h(*(c + t * u + n * v)) for u, v in ((1.33, 0.72), (1.33, -0.72), (-1.33, 0.72), (-1.33, -0.72))]
        pt = max(pt, abs(math.degrees(math.atan2((q[0] + q[1] - q[2] - q[3]) / 2, 2.66))))
        rl = max(rl, abs(math.degrees(math.atan2((q[0] + q[2] - q[1] - q[3]) / 2, 1.44))))
    return round(rl, 1), round(pt, 1)


def paint():
    """(asphalt, grass): the two yards paved on the game's map; the east lot's banks grass (its asphalt was the 2005
    hospital's site)"""
    return [HEART_LOT, DENT_LOT], list(BANK)


# the yards' sides where the photos have the wood round them (the trees on them go there), not the roads past them
WOOD = {'HEART': Polygon([(105.0, -100.0), (125.0, -45.0), (200.0, -45.0), (200.0, -100.0)]),
        'DENT': Polygon([(268.0, -62.0), (268.0, 35.0), (300.0, 35.0), (300.0, 27.5), (288.0, 27.5), (280.0, -20.0), (283.0, -62.0)])}


def trees_aside(trees, halls, pad=1.5):
    """trees the random planting put on the yards (the photos have none there): each moved in its place in the list
    to the nearest point pad m outside the yard's edge on its wooded side (WOOD), clear of the halls by 2.5 m.
    Returns the moves."""
    moved = []
    hb = unary_union([h.buffer(2.5) for h in halls])
    for poly, wood in ((HEART_LOT, WOOD['HEART']), (DENT_LOT, WOOD['DENT']), (EAST_LOT, None)):
        ring = poly.buffer(pad).exterior
        spots = [ring.interpolate(d) for d in np.arange(0.0, ring.length, 0.5)]
        spots = [q for q in spots if (wood is None or wood.contains(q)) and not hb.contains(q)
                 and not any(p.buffer(0.5).contains(q) for _, p, _, _ in LOTS)]
        inside = [t for t in trees if poly.buffer(0.5).contains(Point(t[1], t[2]))]
        near = [Point(t[1], t[2]) for t in trees if t not in inside and abs(t[1] - poly.centroid.x) < 120
                and abs(t[2] - poly.centroid.y) < 120]
        spots = [q for q in spots if all(q.distance(o) > 3.0 for o in near)]       # (clear of the trees standing there)
        for t in inside:
            if not spots:
                break
            q = min(spots, key=lambda q_: q_.distance(Point(t[1], t[2])))
            moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
            t[1], t[2] = round(q.x, 2), round(q.y, 2)
            spots = [s for s in spots if s.distance(q) > 3.5]
    return moved


# =====================================================================================================================
# 의료원의 남은 줄 (#152, 2026-11-17; reference/고증/2.10_세운_차.md 「의료원의 남은 줄」, 3.1.2): the rows of the 1997 scans
# the game could not take, on the ground and paving those scans give.  Late, after med97.grade (the planting and the
# halls' first floors have read the ground as it was); the 종합관's floor and storeys and 의학도서관's outline go with
# it in build_campus.py (BASE_1997, LATE_FOOTPRINT_1997).
#
#     took, info = med97.lots_grade(Hn, X, Y, FIXED, halls, harmonic_fill, road_ls, road_hw)
#     med97.lots_paint()                      # asphalt on the game's map (late)
#     med97.lots_aside(trees, shrubs, halls)  # what the planting put on the new paving, in its place in the list
#
# Every absolute height here is above sea level (해발), taken up to the working datum where it is read.

def fr(o, ang):
    """a frame: (u, v) -> campus metres, u along ang (deg from east), v to its left"""
    a = math.radians(ang)
    c, s = math.cos(a), math.sin(a)
    return lambda u, v: (o[0] + u * c - v * s, o[1] + u * s + v * c)


def _rect(f, u0, u1, v0, v1):
    return Polygon([f(u0, v0), f(u1, v0), f(u1, v1), f(u0, v1)])


MED = fr((150.0, -250.0), 43.0)         # the quarter's frame (3.1.2 「1997년 7월 수직 항공사진」)
# 의료원 종합관 남동쪽 주차장: between the hall's south-east face (v -96.7 .. -97.7) and the planted strip along 성산로
# (v -121), three rows of slanting stalls (the hall's row seen from course 27 only: the roof leans over it in 26/16)
# and two aisles, ONE level: the aisles 31.07 (v -114, sixteen points) and 31.16 m (v -106, twelve), two or three pairs
# within 0.05 - 0.45 m each, the cars' roofs 32.0 - 32.5 m.  The game had 33.6 - 35.0 m by the hall falling to 29.5 m
# at the far row (today's lawn bank).  The plane: 31.1 m at v -109, 0.012 m up per metre towards the hall
JH_LOT = Polygon([(218.06, -318.75), (279.45, -262.89), MED(86.5, -97.75), MED(86.5, -121.0), MED(-0.6, -121.0),
                  MED(-0.6, -96.6)])            # (u -0.6: 0.9 m off 의과대학 신관's north-east face, the first stall's line at u 0.6)
JH_HALL = Polygon([(218.06, -318.75), (279.45, -262.89), (266.79, -248.98), (205.4, -304.84)])   # (종합관, 990032)
JH_IN = Polygon([(218.06, -318.75), (279.45, -262.89), MED(85.9, -91.2), MED(2.9, -90.2)])  # (under the hall, by the face)
JH_DOOR = MED(26.0, -97.05)                  # (its door on that face, where the scans' hatched strip crosses the hall's row)
JH_Z = datum.up_plane((31.15, -0.00818, 0.00878), 250.0, -300.0)
JH_BASE = datum.up(248.75, -290.8, 31.24)    # (the hall's floor: the lot at the middle of its face)
JH_RING, JH_PAD = 10.0, 1.0                  # (eased round it; the other halls' feet: 의과대학 신관's floor is pinned)
# 동문회관 북서쪽 길: the stall row south-east of the road (twelve stalls 2.3 m, nine cars) and the road beside it level
# at 44.85 m (course 27 only: three pairs within 0.05 - 0.35 m on the bare stalls and the road; the leaf-off 1996 and
# 1999 frames 44.7 - 44.9 m), where the game's road rose 0.8 m to the north-east and its lawn fell 0.7 - 1.3 m under
# the stalls.  Frame: o (380, -100), u along the road 45 deg, v to its left (north-west)
DM = fr((380.0, -100.0), 45.0)
DM_ZONE = _rect(DM, -1.5, 30.0, -5.4, 6.8)
DM_Z = datum.up_plane((44.85, 0.0, 0.0), 385.0, -95.0)
DM_RING, DM_PAD = 8.0, None                  # (raised only: the halls' feet, 동문회관's north corner too, go under it)
# the paving the scans have under the rows (the game: lawn), asphalt on the game's map
MU = fr((278.59, -99.86), 42.0)          # (음악대학 남쪽 · 재활병원 동쪽: the south-east row's first stall, along the row)
WC = fr((274.0, -31.0), 75.0)            # (음악대학 동쪽 큰 주차장 서쪽 빈 칸 줄: along the row)


def _carbox(x, y, h, pad=0.0, L=4.7, W=1.8):
    t, n = np.array([math.cos(math.radians(h)), math.sin(math.radians(h))]), np.array([-math.sin(math.radians(h)), math.cos(math.radians(h))])
    c = np.array([x, y])
    return Polygon([tuple(c + t * a * (L / 2 + pad) + n * b * (W / 2 + pad)) for a, b in ((1, 1), (1, -1), (-1, -1), (-1, 1))])


PAVE_MORE = {
    '종합관 남동쪽 주차장': JH_LOT.intersection(_rect(MED, -5.0, 95.0, -120.8, -90.0)),
    '동문회관 북서쪽 칸 줄': _rect(DM, 0.3, 28.5, -5.15, 0.0),
    '음악대학 남쪽 칸 줄': unary_union([_rect(MU, -2.0, 14.0, -2.75, 9.0), _rect(MU, 5.6, 8.2, -5.3, -2.7)]),
    '음악대학 남쪽 굽은 길 가': unary_union([_carbox(278.4, -71.7, -48.0, 0.5), _carbox(279.85, -69.9, -35.0, 0.5)]).convex_hull,
    '특별병동 남동쪽': unary_union([_carbox(204.58, -129.28, 40.0, 0.7), _carbox(205.72, -132.51, 40.0, 0.7),
                              _carbox(208.93, -129.03, 40.0, 0.7)]).convex_hull,
    '종합관 북서 마당 서쪽 셋': _rect(MED, 35.0, 40.4, -42.0, -34.0),
    '종합관 북서 마당 칸 줄': _rect(MED, 43.4, 57.7, -46.5, -41.0),
    '의학도서관 북동쪽 칸 줄': _rect(MED, 34.6, 41.0, -62.5, -47.0),
    '음악대학 동쪽 큰 주차장 서쪽 칸 줄': _rect(WC, -17.0, 27.0, -1.8, 3.0),
    '광혜관 남쪽 마당': _rect(MED, -75.0, -57.0, 50.0, 74.5),
    # (2026-11-17 다섯째, md) cars of the 1997 rows the game's paving left half on the lawn (the scans: asphalt under them):
    # 특별병동 남동 주차장's car at the south-west end by the hall's south-east face and two at the north row's east end,
    # 음악대학 남쪽's second of the row heading west-north-west
    '특별병동 남동 주차장 차 밑': unary_union([_carbox(193.23, -152.39, 40.0, 0.5), _carbox(213.67, -128.06, 130.0, 0.5),
                                       _carbox(219.53, -123.14, 130.0, 0.5)]),
    '음악대학 남쪽 서북서 줄 둘째 차 밑': _carbox(247.7, -60.5, 160.0, 0.5),
}
# 의학도서관 (OSM 324328456): its roof in four frames (27/17 · 26/16 · 27/18 · 26/15, on the roof's plane 49.3 m) ends at
# u 28.6 (28.4 - 28.7), 8.6 m short of OSM's north-east face; the ground beyond is the yard's (38.3 - 38.5 m, five
# pairs at u 33), with the row of six cars nose to a kerb at u 34.7.  The other three faces stay OSM's (within 0.5 -
# 1.5 m of the frames')
LIB_ID = 324328456
LIB_1997 = [(196.93, -295.97), MED(28.6, -65.80), MED(28.6, -48.06), (184.68, -283.35)]


def lots_grade(Hn, X, Y, FIXED, halls, fill, road_ls, road_hw, road=None):
    """The 종합관's car park and the 동문회관 row on the scans' planes (halls: every hall's outline but the 종합관's),
    the ground round them eased; 성산로's bed (road_ls, road_hw + 2.5 m), the other halls' feet (JH_PAD) and nodes
    another rule set (FIXED) stay.  Returns the nodes set and a summary"""
    H0 = Hn.copy()
    on_road_ = on_road(X, Y, road_ls, road_hw, road)
    hall_in = shapely.contains_xy(JH_HALL.difference(JH_IN), X, Y)          # (the rest under the hall stays)
    took = np.zeros(X.shape, bool)
    info = {}
    for nm, zone, c, ring, pad in (('종합관 남동쪽', JH_LOT.union(JH_IN), (JH_Z, 250.0, -300.0), JH_RING, JH_PAD),
                                   ('동문회관 북서쪽', DM_ZONE, (DM_Z, 385.0, -95.0), DM_RING, DM_PAD)):
        near_hall = shapely.contains_xy(unary_union([h.buffer(pad) for h in halls]), X, Y) if pad is not None \
            else np.zeros(X.shape, bool)
        inz = shapely.contains_xy(zone, X, Y)
        m = inz & ~FIXED & ~on_road_ & ~near_hall
        (c0, cx, cy), x0, y0 = c
        Hn[m] = c0 + cx * (X[m] - x0) + cy * (Y[m] - y0)
        took |= m
        free = shapely.contains_xy(zone.buffer(ring), X, Y) & ~inz & ~FIXED & ~on_road_ & ~near_hall & ~took & ~hall_in
        if free.any():
            fill(free)
        took |= free
        d = Hn - H0
        info[nm] = dict(nodes=int(m.sum()), kept=dict(fixed=int((inz & FIXED).sum()), road=int((inz & on_road_).sum()),
                                                      hall=int((inz & near_hall).sum())),
                        moved=(round(float(d[m].min()), 2), round(float(d[m].max()), 2)) if m.any() else None,
                        eased=(int(free.sum()), round(float(d[free].min()), 2), round(float(d[free].max()), 2)) if free.any() else None)
    return took, info


def lots_paint():
    """asphalt under the rows (the game's map, late)"""
    return list(PAVE_MORE.values())


def lots_aside(items, halls, pad=1.2):
    """trees or shrubs the planting put on the new paving: each in its place in the list to the nearest point pad m
    outside that paving, off the other new paving and clear of the halls by 2 m.  Returns the moves"""
    paved = unary_union(list(PAVE_MORE.values()))
    hb = unary_union([h.buffer(2.0) for h in halls])
    moved = []
    for t in items:
        p = Point(t[1], t[2])
        if not paved.contains(p):
            continue
        ring = paved.buffer(pad)
        ring = ring.geoms if hasattr(ring, 'geoms') else [ring]
        edge = min(ring, key=lambda g: g.distance(p)).exterior
        spots = [edge.interpolate(d) for d in np.arange(0.0, edge.length, 0.25)]
        spots = [q for q in spots if not hb.contains(q) and not paved.contains(q)]
        if not spots:
            continue
        q = min(spots, key=lambda q_: q_.distance(p))
        moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
        t[1], t[2] = round(q.x, 2), round(q.y, 2)
    return moved


# =====================================================================================================================
# 성산로 북쪽 가 (#152, 2026-11-17 다섯째; reference/고증/2.10_세운_차.md 「의료원 종합관 남동쪽 주차장의 먼 줄과 성산로
# 북쪽 가」, 3.1.2): between the 종합관's car park and 성산로 the 1997-07-28 scans (27/17 · 27/18 · 26/16, the leaf-off
# 1996 27/17 · 27/18 · 27/16) have, south of the car park's far row (its stalls' back ends at v -120.4): a planted
# strip on the car park's own level (v -120.8 .. -124.0; its tops 31.3 - 31.5 m, three 1996 pairs), a wall down to the
# sidewalk (the strip's south edge, a bright coping with posts in the 1996 frames), the sidewalk at the road's level
# (28.5 - 28.7 m at u 40 - 60, three 1996 pairs 0.94 - 0.97; 29.0 m at u 80 - 100) with a row of street trees, and the
# kerb (gate_town KN97_UV: the road's north kerb moved there).  The game's road had come over the strip to v -121.
#
#     took, cells, poly, info = med97.strip_grade(Hn, X, Y, FIXED, road, road_z)   # late, after lots_grade
#     deck = dwb_deck(cells, poly, med97.strip_h)                                  # build_campus: the strip's level
#     quads, guards = med97.strip_walls(deck_z, ground)                            # the wall's face and its coping
#     med97.strip_paint()                                                          # the strip's lawn (after the town's)
#     trees, shrubs = med97.strip_plants()                                         # at the lists' ends
#
# The 5 m grid cannot hold a 2 m wall: every node of a cell with a part of the sidewalk goes to the sidewalk's level, and
# a deck (a surface over the ground, walked and stood on) carries the car park's level over those cells north of the
# wall's face, as the terrace before 스팀슨관 does (build_campus.py dwb_deck).  The far row's cars stand on it.
SW_FACE = -124.0                 # the wall's face (v): the planted strip's south edge, the sidewalk's back
SW_LOW = (-1.9, 88.0)            # (u: the nodes set low, from 의과대학 신관's east face to the car park's way out)
SW_RUN = (-8.0, 88.0)            # (u: the deck and the wall, over every cell with such a node)
SW_WALK = (0.0, 86.0)            # (u: the sidewalk under the wall)
SW_STRIP = (-124.0, -120.8)      # the planted strip (the car park's paving ends at v -120.8)
SW_DZ = 0.12                     # the sidewalk over the road's edge
SW_COPE = (0.3, 0.25)            # the coping over the wall's top: high, thick
SW_OPEN = (17.0, 34.0)           # (u: the footbridge's stair and landing on the sidewalk: no street tree)


def strip_h(x, y):
    """the planted strip's and the far row's level: the car park's plane (JH_Z, working datum)"""
    c0, cx, cy = JH_Z
    return c0 + cx * (x - 250.0) + cy * (y + 300.0)


def _road_poly(road):
    import gate_town
    kn, ks = road.offn(gate_town.HW), road.off(-gate_town.HW)
    return Polygon([tuple(p) for p in kn] + [tuple(p) for p in ks[::-1]]).buffer(0)


def sidewalk(road):
    """the sidewalk under the wall: between the wall's face and the road's north kerb as laid"""
    return _rect(MED, SW_WALK[0], SW_WALK[1], -140.0, SW_FACE).difference(_road_poly(road))


def strip_grade(Hn, X, Y, FIXED, road, road_z, halls=(), step=5.0, half=800.0):
    """The sidewalk's nodes (every node of a 5 m cell with a part of it, but those in the road) at the road's height
    abreast + SW_DZ; the other nodes on the strip's band on the car park's plane.  Returns the nodes set, the cells a
    deck must cover (those with a node set low), the deck's outline and a summary"""
    H0 = Hn.copy()
    sw = sidewalk(road)
    rp = _road_poly(road).buffer(0.05)
    x0, y0, x1, y1 = sw.bounds
    cells = set()
    for j in range(int(math.floor((y0 + half) / step)) - 1, int(math.ceil((y1 + half) / step)) + 1):
        for i in range(int(math.floor((x0 + half) / step)) - 1, int(math.ceil((x1 + half) / step)) + 1):
            bx = shapely.geometry.box(-half + i * step, -half + j * step, -half + (i + 1) * step, -half + (j + 1) * step)
            if bx.intersection(sw).area > 0.02:
                cells.add((j, i))
    low = np.zeros(X.shape, bool)
    for j, i in cells:
        for a, b in ((0, 0), (0, 1), (1, 0), (1, 1)):
            x, y = X[j + a, i + b], Y[j + a, i + b]
            u, _ = uv_med(x, y)
            if SW_LOW[0] <= u <= SW_LOW[1] and not rp.contains(Point(x, y)):
                low[j + a, i + b] = True
    jj, ii = np.nonzero(low)
    s = shapely.line_locate_point(road.ls, shapely.points(np.stack([X[low], Y[low]], 1)))
    Hn[jj, ii] = np.interp(s, road.cum, road_z) + SW_DZ
    # the strip's band and the far row's back: the car park's plane where no cell of the sidewalk reaches
    u_, v_ = uv_med(X, Y)
    band = (u_ >= SW_LOW[0]) & (u_ <= SW_WALK[1]) & (v_ > SW_FACE) & (v_ <= -114.0) & ~low & ~FIXED
    Hn[band] = strip_h(X[band], Y[band])
    deck_cells = {(j + a, i + b) for j, i in zip(jj, ii) for a in (-1, 0) for b in (-1, 0)}
    poly = unary_union([shapely.geometry.box(-half + i * step, -half + j * step, -half + (i + 1) * step, -half + (j + 1) * step)
                        for j, i in deck_cells]).intersection(_rect(MED, SW_RUN[0], SW_RUN[1], SW_FACE, -100.0)) \
        .difference(unary_union([JH_HALL] + list(halls)).buffer(0.05))
    d = Hn - H0
    info = dict(low=int(low.sum()), low_dz=(round(float(d[low].min()), 2), round(float(d[low].max()), 2)),
                band=int(band.sum()), band_dz=(round(float(d[band].min()), 2), round(float(d[band].max()), 2)) if band.any() else None,
                deck_cells=len(deck_cells), deck_m2=round(poly.area, 1))
    return low | band, deck_cells, poly, info


def uv_med(x, y):
    """campus metres -> MED's (u, v)"""
    a = math.radians(43.0)
    dx, dy = np.asarray(x, float) - 150.0, np.asarray(y, float) + 250.0
    return dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)


def strip_walls(top, foot, step=0.5):
    """the wall along the sidewalk's back (its face south, concrete) from the deck's edge (top(x, y)) down to the
    sidewalk (foot(x, y)), and over it the coping (SW_COPE) where it stands more than half a metre; and the guards
    (campus.json colliders) along its top where it stands more than a metre: [material, four points], polygons"""
    quads, guards = [], []
    us = np.arange(SW_RUN[0], SW_RUN[1] + 1e-6, step)
    P = [MED(u, SW_FACE) for u in us]
    B = [MED(u, SW_FACE + SW_COPE[1]) for u in us]
    zt = [top(*MED(u, SW_FACE + 0.02)) for u in us]
    zb = [foot(*MED(u, SW_FACE - 0.05)) - 0.05 for u in us]
    R = lambda q, z: [round(q[0], 3), round(q[1], 3), round(float(z), 3)]
    run = []
    for k in range(len(us) - 1):
        h0, h1 = zt[k] - zb[k], zt[k + 1] - zb[k + 1]
        if max(h0, h1) < 0.1:
            continue
        cope = min(h0, h1) > 0.5
        c0, c1 = zt[k] + (SW_COPE[0] if cope else 0.0), zt[k + 1] + (SW_COPE[0] if cope else 0.0)
        quads.append(['concrete', [R(P[k], zb[k]), R(P[k + 1], zb[k + 1]), R(P[k + 1], c1), R(P[k], c0)]])      # (its face)
        if cope:
            quads.append(['concrete', [R(P[k], c0), R(P[k + 1], c1), R(B[k + 1], c1), R(B[k], c0)]])          # (top)
            quads.append(['concrete', [R(B[k], zt[k] - 0.05), R(B[k], c0), R(B[k + 1], c1), R(B[k + 1], zt[k + 1] - 0.05)]])  # (back)
        if min(h0, h1) > 1.0:
            run.append(us[k])
        elif run:
            guards.append((run[0], run[-1] + step))
            run = []
    if run:
        guards.append((run[0], run[-1] + step))
    polys = []
    for a, b in guards:                     # (in pieces of 4 m: a thin band along the coping)
        for u0 in np.arange(a, b, 4.0):
            u1 = min(u0 + 4.0, b)
            polys.append([[round(c, 3) for c in MED(u, v)] for u, v in ((u0, SW_FACE + 0.02), (u1, SW_FACE + 0.02),
                                                                       (u1, SW_FACE + 0.3), (u0, SW_FACE + 0.3))])
    return quads, polys


SW_SIN_BAND = (-80.0, -3.0, -124.0, -121.5)     # (의과대학 신관 앞: the planted band between its paved apron and the sidewalk)


def strip_paint():
    """the planted strip on the car park's level and the band before 의과대학 신관: lawn (the town's paving over them
    out, gate_town walk_n)"""
    return [_rect(MED, SW_LOW[0] + 1.0, SW_WALK[1], SW_STRIP[0] + SW_COPE[1], SW_STRIP[1]), _rect(MED, *SW_SIN_BAND)]


# the street trees on the sidewalk (u along it; the 1996 frames' trunks and their shadows 5 - 7 m apart, the 1997 crowns
# a band over the strip and the sidewalk: their kind not read, zelkovas) and before 의과대학 신관 (3.1.2 「의과대학 신관과
# 성산로 사이」: its sidewalk's row from the hall's west end), the strip's shrubs (dark clumps in the leaf-off frames)
SW_TREE_V, SW_TREE_DU = -126.6, 6.5
SW_TREES_U = [(-80.0, -6.0), (3.0, 16.0), (35.0, 85.0)]


def strip_plants(seed=15297):
    import random
    rnd = random.Random(seed)
    trees, shrubs = [], []
    for a, b in SW_TREES_U:
        n = int(round((b - a) / SW_TREE_DU))
        for k in range(n + 1):
            u = a + (b - a) * k / max(n, 1) + rnd.uniform(-0.6, 0.6)
            x, y = MED(u, SW_TREE_V + rnd.uniform(-0.3, 0.3))
            trees.append(['zelkova', round(x, 2), round(y, 2), round(rnd.uniform(0.75, 0.95), 2), round(rnd.uniform(0, 6.28), 2)])
    for u in list(np.arange(SW_SIN_BAND[0] + 1.5, SW_SIN_BAND[1] - 1.0, 2.4)) + list(np.arange(1.5, 85.0, 2.4)):
        if SW_OPEN[0] - 1.0 < u < SW_OPEN[1] + 1.0 and u > 22.0:
            continue
        x, y = MED(u + rnd.uniform(-0.4, 0.4), (-122.75 if u < 0 else -122.6) + rnd.uniform(-0.3, 0.3))
        shrubs.append([rnd.choice(['hedge_blob', 'hedge_blob', 'topiary_round']), round(x, 2), round(y, 2),
                       round(rnd.uniform(0.8, 1.1), 2), round(rnd.uniform(0, 6.28), 2)])
    return trees, shrubs


# =====================================================================================================================
# 간호대학 북쪽 주차장 (#152, 2026-11-17 다섯째; reference/고증/2.10_세운_차.md 「간호대학 북쪽 주차장」): between 간호대학
# and 알렌관 the 1997-07-28 scans (course 27 only: 27/16 · 27/17 · 27/18; the leaf-off 1996 27/15 · 27/16 · 27/17 and
# 1999 27/15 · 27/16 · 27/17) have a lined car park on a platform: its aisle at 56.0 m (nine pairs of the three
# flights within 55.8 - 56.1 m at u 0, 55.9 - 56.1 at u 18), the forecourt south of it (간호대학's north side) and the
# ground east of it at 50.0 - 50.9 m, with a parapet along its south edge 1.2 m over it (56.98 - 57.45, four pairs).
# The game had a lawn and a walk at 51.2 - 52.1 m.  Frame NL: o (380, 7), u along the rows (-17.9 deg), v to their
# left (north).  Two rows of white-lined stalls 2.5 m apart (the lines in 27/17 and 27/16 within 0.05 - 0.15 m): the
# north row's fifteen (v 5.2 .. 10.2), the south row's sixteen (v -1.1 .. -5.8), the aisle between; on 28 July one
# car (27/17; under the trees in 27/16), in a stall: the one-course rule takes it.
#
#     took, cells, poly, info = med97.nurse_grade(Hn, X, Y, FIXED, halls, fill)    # late, with the strip
#     deck = dwb_deck(cells, poly, med97.nurse_h)                                  # the platform over the walls' cells
#     quads, guards = med97.nurse_walls(top, foot)
#     med97.nurse_paint()
#     med97.nurse_aside(trees, halls)                                              # the planting off the platform
NL = fr((380.0, 7.0), -17.9)
NL_LOT = _rect(NL, -26.0, 21.9, -7.2, 11.2)            # the platform: its south and east faces walls
NL_RAISE = _rect(NL, -31.0, 21.9, -7.2, 15.0)          # (the nodes raised: the platform and on west and north, where
#                                                        the ground meets it without a wall: 53.5 m at the road west
#                                                        of it, 55.5 m by the trees north of it)
NL_LOW = unary_union([_rect(NL, -40.0, 34.0, -20.0, -7.2), _rect(NL, 21.9, 34.0, -20.0, 20.0)])   # (below the walls)
NL_Z = datum.up_plane((56.0, 0.0, 0.0), 380.0, 7.0)
NL_RING = 8.0
NL_PARAPET = (1.2, 0.3)                                 # (its height over the platform, thickness)
NL_ISLAND = Polygon([NL(u, v) for u, v in ((-26.0, -6.6), (-22.6, -6.6), (-22.6, 0.6), (-24.3, 1.1), (-26.0, 0.6))])


def nurse_h(x, y):
    """the platform's level (working datum)"""
    c0, cx, cy = NL_Z
    return c0 + cx * (np.asarray(x) - 380.0) + cy * (np.asarray(y) - 7.0)


def nurse_grade(Hn, X, Y, FIXED, halls, fill, step=5.0, half=800.0):
    """The platform's nodes on its level, those of the cells its walls cross left as they are (the deck carries the
    platform over them), the ground on west and north eased to it.  Returns the nodes set, the deck's cells and
    outline, a summary"""
    H0 = Hn.copy()
    hb = unary_union([h.buffer(HALL_PAD) for h in halls])
    x0, y0, x1, y1 = NL_RAISE.bounds
    wall_cells = set()
    for j in range(int(math.floor((y0 + half) / step)) - 1, int(math.ceil((y1 + half) / step)) + 1):
        for i in range(int(math.floor((x0 + half) / step)) - 1, int(math.ceil((x1 + half) / step)) + 1):
            bx = shapely.geometry.box(-half + i * step, -half + j * step, -half + (i + 1) * step, -half + (j + 1) * step)
            if bx.intersection(NL_LOT).area > 0.02 and bx.intersection(NL_LOW).area > 0.02:
                wall_cells.add((j, i))
    low = np.zeros(X.shape, bool)
    for j, i in wall_cells:
        low[j:j + 2, i:i + 2] = True
    near_hall = shapely.contains_xy(hb, X, Y)
    up = shapely.contains_xy(NL_RAISE.buffer(0.5), X, Y) & ~low & ~near_hall & ~FIXED
    Hn[up] = nurse_h(X[up], Y[up])
    keep = FIXED | near_hall | low | up | shapely.contains_xy(NL_LOW, X, Y)
    free = shapely.contains_xy(NL_RAISE.buffer(NL_RING), X, Y) & ~keep
    if free.any():
        fill(free)
    # (every cell with a node left low: those beside the walls' cells share their nodes and would dip to them)
    jj, ii = np.nonzero(low)
    deck_cells = {(j + a, i + b) for j, i in zip(jj, ii) for a in (-1, 0) for b in (-1, 0)}
    poly = unary_union([shapely.geometry.box(-half + i * step, -half + j * step, -half + (i + 1) * step, -half + (j + 1) * step)
                        for j, i in deck_cells]).intersection(NL_LOT).difference(unary_union(list(halls)).buffer(0.05)) \
        if deck_cells else Polygon()
    d = Hn - H0
    info = dict(raised=int(up.sum()), dz=(round(float(d[up].min()), 2), round(float(d[up].max()), 2)) if up.any() else None,
                low=int(low.sum()), eased=int(free.sum()), deck_cells=len(deck_cells), deck_m2=round(poly.area, 1))
    return up | free, deck_cells, poly, info


def nurse_walls(top, foot, step=0.5):
    """the platform's south and east walls (concrete, their faces out) from its edge (top) down to what lies below
    (foot), the parapet along them (NL_PARAPET) and the guards along it: [material, four points], polygons"""
    quads, polys = [], []
    R = lambda q, z: [round(q[0], 3), round(q[1], 3), round(float(z), 3)]
    ph, pt = NL_PARAPET
    for (ua, va), (ub, vb), (nu, nv) in (((-26.0, -7.2), (21.9, -7.2), (0.0, -1.0)), ((21.9, -7.2), (21.9, 11.2), (1.0, 0.0))):
        L = math.hypot(ub - ua, vb - va)
        n = max(1, int(math.ceil(L / step)))
        S = [(ua + (ub - ua) * k / n, va + (vb - va) * k / n) for k in range(n + 1)]
        P = [NL(u, v) for u, v in S]
        B = [NL(u - nu * pt, v - nv * pt) for u, v in S]
        zt = [top(*NL(u - nu * 0.02, v - nv * 0.02)) for u, v in S]
        zb = [foot(*NL(u + nu * 0.05, v + nv * 0.05)) - 0.05 for u, v in S]
        for k in range(n):
            if max(zt[k] - zb[k], zt[k + 1] - zb[k + 1]) < 0.1:
                continue
            c0, c1 = zt[k] + ph, zt[k + 1] + ph
            # (seen from outside the run goes left to right on both walls: the face, the parapet's top, its back)
            quads.append(['concrete', [R(P[k], zb[k]), R(P[k + 1], zb[k + 1]), R(P[k + 1], c1), R(P[k], c0)]])
            quads.append(['concrete', [R(P[k], c0), R(P[k + 1], c1), R(B[k + 1], c1), R(B[k], c0)]])
            quads.append(['concrete', [R(B[k], zt[k] - 0.05), R(B[k], c0), R(B[k + 1], c1), R(B[k + 1], zt[k + 1] - 0.05)]])
        for u0 in np.arange(0.0, L, 4.0):
            u1 = min(u0 + 4.0, L)
            q = [NL(ua + (ub - ua) * t / L - nu * w, va + (vb - va) * t / L - nv * w) for t, w in ((u0, -0.02), (u1, -0.02), (u1, pt), (u0, pt))]
            polys.append([[round(c, 3) for c in p] for p in q])
    return quads, polys


def nurse_paint():
    """(asphalt, lawn): the platform's asphalt, the round-ended island at its west end"""
    return [NL_LOT.difference(NL_ISLAND)], [NL_ISLAND]


def nurse_aside(items, halls, pad=1.5):
    """trees the planting put on the platform: each in its place in the list to the nearest point pad m outside its
    north edge (the 1997 trees between it and 알렌관), clear of the halls by 2.5 m and of the other trees by 3 m"""
    hb = unary_union([h.buffer(2.5) for h in halls])
    edge = LineString([NL(-18.0, 11.2 + pad), NL(20.0, 11.2 + pad)])
    spots = [edge.interpolate(d) for d in np.arange(0.0, edge.length, 0.5)]
    spots = [q for q in spots if not hb.contains(q)]
    moved = []
    inside = [t for t in items if NL_LOT.buffer(0.5).contains(Point(t[1], t[2]))]
    others = [Point(t[1], t[2]) for t in items if t not in inside and NL_LOT.buffer(15.0).contains(Point(t[1], t[2]))]
    spots = [q for q in spots if all(q.distance(o) > 3.0 for o in others)]
    for t in inside:
        if not spots:
            break
        q = min(spots, key=lambda q_: q_.distance(Point(t[1], t[2])))
        moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
        t[1], t[2] = round(q.x, 2), round(q.y, 2)
        spots = [s for s in spots if s.distance(q) > 3.0]
    return moved


# =====================================================================================================================
# 음악대학 동쪽 큰 주차장 서쪽 통로 (#152, 2026-11-17 다섯째, md): the row along the lot's west edge (A1 · A2 · A4 · A5 of
# 「음악대학 동쪽 큰 주차장 서쪽 통로(나무 띠 가)」 and the 치과대학병원 서쪽 길 car at its south end) stands at the foot of
# the bank of trees west of it, which the 1997 scans have 2 - 3 m over the lot within 3 - 6 m of the cars' west wheels
# ((277, -30) 55.4 m sea level beside (283, -30) 52.2 m; music97 EAST_YARD_POLY and the bank south of it).  The 5 m grid
# ran one cell's slope from the bank's nodes under the cars' wheels: they leaned 8 - 30 deg.  The bank's nodes of the
# cells under the wheels go down to the lot's plane and a deck carries the bank's surface (the ground as it was) over
# them west of a face 1.5 m inside the lot's edge, with a low wall down to the lot.
#
#     took, cells, poly, h0 = med97.foot_grade(Hn, X, Y, cars)     # late, after the music halls and the lots
#     deck = dwb_deck(cells, poly, h0)                               # build_campus
#     quads = med97.foot_walls(top, foot)
FOOT_CARS = [(278.01, -55.62, -104.9), (279.36, -50.58, 73.4), (280.57, -45.46, 73.4), (284.08, -33.67, 73.4), (285.11, -28.5, 73.4)]
FOOT_FACE = LineString([(276.0, -65.0), (275.0, -55.0), (282.0, -25.0), (285.0, 0.0)]).parallel_offset(1.5, 'right')
FOOT_SIDE = Polygon(list(LineString([(276.0, -65.0), (275.0, -55.0), (282.0, -25.0), (285.0, 0.0)]).parallel_offset(1.5, 'right').coords)
                    + [(255.0, 0.0), (255.0, -65.0)])          # (the bank's side of the face: west)


def foot_grade(Hn, X, Y, cars=FOOT_CARS, step=5.0, half=800.0, tol=0.3):
    """The nodes of the cells under the row's wheels standing over the lot's plane by more than tol: down to it.  Returns
    them, the deck's cells (those with such a node) and outline (their part west of the face), the bank's surface as it
    was (h0(x, y), working datum) and a summary"""
    H0 = Hn.copy()
    low = np.zeros(X.shape, bool)
    for x, y, h in cars:
        t = np.array([math.cos(math.radians(h)), math.sin(math.radians(h))])
        n = np.array([-t[1], t[0]])
        for a in (1.42, -1.28):
            for b in (0.75, -0.75):
                p = np.array([x, y]) + t * a + n * b
                i, j = int(math.floor((p[0] + half) / step)), int(math.floor((p[1] + half) / step))
                for dj in (0, 1):
                    for di in (0, 1):
                        z = plane(DENT_Z, X[j + dj, i + di], Y[j + dj, i + di])
                        if Hn[j + dj, i + di] > z + tol:
                            low[j + dj, i + di] = True
    jj, ii = np.nonzero(low)
    Hn[jj, ii] = plane(DENT_Z, X[jj, ii], Y[jj, ii])
    cells = {(j + a, i + b) for j, i in zip(jj, ii) for a in (-1, 0) for b in (-1, 0)}
    poly = unary_union([shapely.geometry.box(-half + i * step, -half + j * step, -half + (i + 1) * step, -half + (j + 1) * step)
                        for j, i in cells]).intersection(FOOT_SIDE) if cells else Polygon()

    def h0(x, y):
        fx, fy = (x + half) / step, (y + half) / step
        i, j = int(fx), int(fy)
        ax, ay = fx - i, fy - j
        return float(H0[j, i] * (1 - ax) * (1 - ay) + H0[j, i + 1] * ax * (1 - ay) + H0[j + 1, i] * (1 - ax) * ay + H0[j + 1, i + 1] * ax * ay)
    d = Hn - H0
    info = dict(low=[(int(X[j, i]), int(Y[j, i]), round(float(d[j, i]), 2)) for j, i in zip(jj, ii)], cells=len(cells),
                deck_m2=round(poly.area, 1))
    return low, cells, poly, h0, info


def foot_walls(top, foot, step=0.5):
    """the low wall along the face (stone, its face east to the lot) where the deck stands over the lot, and the guards
    along its top where it stands more than a metre (campus.json colliders): [material, four points], polygons"""
    quads, guards = [], []
    R = lambda q, z: [round(q[0], 3), round(q[1], 3), round(float(z), 3)]
    L = FOOT_FACE.length
    for d in np.arange(0.0, L - 1e-6, step):
        p0, p1 = FOOT_FACE.interpolate(d), FOOT_FACE.interpolate(min(d + step, L))
        t = np.array([p1.x - p0.x, p1.y - p0.y])
        if not np.any(t):
            continue
        t /= np.linalg.norm(t)
        e = np.array([t[1], -t[0]])                      # (east: out of the bank)
        q0, q1 = (p0.x, p0.y), (p1.x, p1.y)
        a0, a1 = top(*(np.array(q0) - e * 0.02)), top(*(np.array(q1) - e * 0.02))
        b0, b1 = foot(*(np.array(q0) + e * 0.05)) - 0.05, foot(*(np.array(q1) + e * 0.05)) - 0.05
        if max(a0 - b0, a1 - b1) < 0.15:
            continue
        # (seen from the lot, east of it, q0 south on the left, q1 north on the right)
        quads.append(['stone_granite', [R(q0, b0), R(q1, b1), R(q1, a1), R(q0, a0)]])
        if min(a0 - b0, a1 - b1) > 1.0:
            guards.append([[round(c, 3) for c in p] for p in (np.array(q0) + e * 0.02, np.array(q1) + e * 0.02,
                                                              np.array(q1) - e * 0.28, np.array(q0) - e * 0.28)])
    return quads, guards
