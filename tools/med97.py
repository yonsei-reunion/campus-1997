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


def kerb_lane_nodes(ls, hw, shape, step, half, side):
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
        for o in np.arange(hw - KERB_LANE[0], hw - KERB_LANE[1] + 0.01, 0.5):
            x, y = a.x + n[0] * o, a.y + n[1] * o
            if x0 < x < x1 and y0 < y < y1:
                j, i = int(math.floor((y + half) / step)), int(math.floor((x + half) / step))
                out[j:j + 2, i:i + 2] = True
    return out


def grade(Hn, X, Y, FIXED, halls, fill, road_ls, road_hw, step=5.0, half=800.0):
    """The three lots on the photos' planes, the road north-east of the east lot on its profile, the ground round them
    eased in (fill: build_campus.py harmonic_fill) as far as RING out; the halls' feet (HALL_PAD), 성산로's bed
    (road_ls, road_hw: gate_town's middle line and half width, + 2.5 m) and nodes another rule set (FIXED) stay.
    Returns the nodes set (to be FIXED) and a summary."""
    H0 = Hn.copy()
    near_hall = shapely.contains_xy(unary_union([h.buffer(HALL_PAD) for h in halls]), X, Y)
    pts = shapely.points(np.stack([X.ravel(), Y.ravel()], 1))
    on_road = (shapely.distance(pts, road_ls) <= road_hw + 2.5).reshape(X.shape)
    keep = FIXED | near_hall | on_road
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
    kn = kerb_lane_nodes(road_ls, road_hw, X.shape, step, half, lot_side) & ring & ~keep & ~band \
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
    info['kerb_lane_tilt'] = kerb_lane_tilt(Hn, road_ls, road_hw, lot_side, step, half)
    return took | free, info


def kerb_lane_tilt(H, ls, hw, side, step, half):
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
        c = np.array([m.x, m.y]) + n * o
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
