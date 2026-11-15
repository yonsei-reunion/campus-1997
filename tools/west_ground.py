"""서쪽 · 남쪽 땅을 1997년 7월 항공사진 원본 스캔의 높이로 (#189 의 서쪽 · 남쪽 구역).  tools/build_campus.py 가 부른다.

    west_ground.field_sw(Hn, X, Y, FIXED, ...)       # 성산로 서쪽 끝 너머 길 · 대운동장 남서쪽 둑 · 야구장 (gate_town.plan 바로 뒤)
    west_ground.valley(Hn, X, Y, FIXED, halls)       # 과학관 북서쪽 골짜기의 공사 마당 (저장 바로 앞)
    west_ground.eagle_yard(Hn, X, Y, FIXED, halls, fill)    # 독수리상 서쪽 맨땅 마당 (저장 바로 앞)
    west_ground.move_off(trees, shrubs, props)       # 마당의 나무는 가장자리로(목록 제자리), 관목 · 소품은 뺌

Frame: campus metres, x east, y north.  All of it runs after the random planting (the trees, the decals and the cars
have read the ground as it was), and nothing here draws from build_campus.py's `rng`: the lists keep their order.

Heights are the photos' surface (tools/aerial97.py surface_z, 3 m windows, frame pairs one by one, correlation 0.7 and
over), carried to the game by the difference from ground that stays (reference/고증/4.8.2, 4.12, 3.22, 4.5.2).  All
heights here are the game's (게임 기준).  The survey's spot heights (1:5000 수치지형도, 2006 · 2024: #134), once their
tilt against the photos' datum is taken out (2.05 + 0.522 x/100 + 0.248 y/100 m), agree with the photos to 0.3 - 0.4 m
where they fall on open ground (the 야구장 1.95 m under the 대운동장, the photos 2.21 m).
"""
# (every absolute height written in this file's code is above sea level, 해발: datum.up · up3 · up_at · up_plane take it
# up to the working datum the ground is laid on, 해발 + tilt, where it is read: tools/datum.py.  Heights quoted in
# comments written before 2026-11-15 are on the old datum: 2.0 m and the tilt at their place higher)
import numpy as np
import datum
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, unary_union


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------------------------------------
# 성산로 서쪽 끝 너머 (the road runs on north-west past gate_town's west end at (-461.7, -297.6), round the 대운동장's
# south-west side and past 학군단 towards 연희 IC): the photos (26/16 · 26/15 · 1998 26/17, 8 m apart along it, 0 - 12 m
# north-east of this line) have it flat at 29.2 - 30.0 m where the game had the surface model's 35 - 39 m (the trees of
# its two banks); the survey's spot on it (-510.9, -243.3) 31.42 m (30.20 m once its tilt against the photos' datum is
# taken out).  NW_LINE runs from 20 m inside gate_town's road (which ssr_west puts on the same photos and datum) round
# past the grid's west edge; the road's bed every 16 m: (s, the photos' height, three stations' mean), on them +
# gate_town.SSR_W_DATUM (게임 기준).  Past the photos' last station (s 200, x -575: out of the ground map) the bed holds
# that height on to x -640 and is eased back into the surface model's ground beyond, so that the road does not end in
# a 7 m bank seen from the campus
NW_LINE = [(-440.6, -321.6), (-461.7, -297.6), (-516.0, -235.0), (-575.0, -170.0), (-640.0, -100.0)]
NW_Z97 = datum.up_at([(0.0, 29.8), (32.0, 30.35), (48.0, 30.52), (64.0, 30.75), (80.0, 30.82), (96.0, 31.15), (112.0, 31.07),
          (128.0, 31.1), (144.0, 31.12), (160.0, 30.75), (176.0, 30.28), (192.0, 30.2), (200.0, 30.17)],
                     [(-440.6, -321.6), (-461.7, -297.6), (-472.2, -285.5), (-482.7, -273.4), (-493.2, -261.3), (-503.7, -249.2),
                      (-514.1, -237.1), (-524.9, -225.2), (-535.6, -213.4), (-546.4, -201.6), (-557.1, -189.7), (-567.9, -177.9),
                      (-573.2, -171.9)])
NW_HALF, NW_EASE = 17.0, 14.0          # the road's bed either side of the line, then eased into the ground beside it
NW_END = (290.0, 340.0)                # (s: eased out back into the surface model's ground)
# 야구장 (OSM 421415364): the photos' 128 points on it lie on one level 30.54 m (rms 0.09), the 대운동장's 188 on 32.75 m
# (rms 0.10), the same frame pair: the 야구장 2.21 m under the 대운동장, 31.0 m here (the survey's 2006 spot 31.22 m, 1.95
# m under its 33.17 m).  The game had both pitches at the mean of the surface model under them (32.4 m)
BASEBALL = dict(way=421415364, z=datum.up(-341.7, -310.19, 31.5), ring=16.0)        # (z: 게임 기준, the 대운동장's 33.2 m less 2.21)


def field_sw(Hn, X, Y, FIXED, road, half_w, datum, field_patch, field_keep, pad, baseball_poly, keep, fill):
    """The road's bed north-west of gate_town's road (NW_LINE, on the photos), the 야구장 down to BASEBALL['z'], and the
    ground between the 대운동장, 학군단, the road and the 야구장 smoothed again (fill) between what stays: the oval and
    학군단's pad (FIXED; the ground within 6 m of the pad as it was), the two roads' beds, the 야구장, and `keep` (the
    campus roads' asphalt, the halls' feet, the 공학원 site).  road: gate_town's (Line), half_w its carriageway's half
    width.  Returns a summary."""
    H0 = Hn.copy()
    L = LineString(NW_LINE)
    P = shapely.points(np.stack([X.ravel(), Y.ravel()], 1))
    box = (X > -700) & (X < -400) & (Y > -350) & (Y < -40)
    d = np.full(X.shape, 1e9)
    s = np.zeros(X.shape)
    d[box] = shapely.distance(L, P.reshape(X.shape)[box])
    s[box] = shapely.line_locate_point(L, P.reshape(X.shape)[box])
    zs, zz = zip(*NW_Z97)
    tgt = np.interp(s, zs, zz) + datum
    w = _smooth(1.0 - (d - NW_HALF) / NW_EASE) * _smooth((NW_END[1] - s) / (NW_END[1] - NW_END[0])) * _smooth(s / 4.0 + 0.5)
    near_pad = shapely.contains_xy(pad.buffer(6.0), X, Y)
    w[~box | FIXED | near_pad] = 0.0
    Hn[:] = Hn * (1 - w) + tgt * w
    bed = w > 0.999
    # the 야구장
    pitch = shapely.contains_xy(baseball_poly.buffer(1.5), X, Y) & ~FIXED
    Hn[pitch] = BASEBALL['z']
    # gate_town's road's bed (its carriageway and 1 m more): kept as it was laid
    near = (X > -520) & (X < -240) & (Y > -480) & (Y < -200)
    dr = np.full(X.shape, 1e9)
    dr[near] = shapely.distance(road.ls, P.reshape(X.shape)[near])
    road_bed = dr < half_w + 1.0
    free = ((shapely.contains_xy(field_patch, X, Y) & (Y < -150.0)) |
            shapely.contains_xy(baseball_poly.buffer(BASEBALL['ring']), X, Y))
    free &= ~FIXED & ~field_keep & ~pitch & ~bed & ~road_bed & ~keep & ~near_pad
    if free.any():
        fill(free)
    moved = np.abs(Hn - H0)
    return dict(bed=int(bed.sum()), pitch=int(pitch.sum()), free=int(free.sum()), nodes=int((moved > 0.05).sum()),
                most=float(moved.max()))


# ---------------------------------------------------------------------------------------------------------------------
# 과학관 북서쪽 골짜기 (x -350 .. -295, y 60 .. 215; the 1997 photos' 26/15 · 26/16, at y 136 - 148 the 1998 26/17 too
# within 0.2 - 0.4 m): not the slope the game had (50 - 57 m, the surface model of the built-up valley of later
# years: the survey 2006 · 2024 has 46.3 - 52.6 m on its spots there, 7 - 8.5 m under the game) but a works yard cut
# into the valley, level at 48.2 m (prefab sheds, stacked materials, a track round its north end), and north of it the
# valley floor at 43.5 - 45.9 m.  Its points (x, y, the photos' height + 0.3, 게임 기준: the datum seomun.py found at 과학관's
# corner and the road west of it); not the sheds along its east side (52 - 53 m, roofs or a bench: left out), not the
# dip at its south end (45 - 46 m at y 58 - 76, among dark sheds: left out).  The ground takes the photos' difference
# from the game's round them (Gaussian, 6 m; out of reach it fades to nothing), the 과학관 north road (y 40 - 48) and
# the halls' feet as they are
VALLEY_PTS = datum.up3([
    (-312, 154, 47.99), (-306, 154, 48.26), (-330, 148, 48.1), (-324, 148, 48.67), (-318, 148, 47.94), (-312, 148, 48.01), (-306, 148, 48.18), (-300, 148, 48.25),
    (-336, 142, 47.65), (-330, 142, 47.92), (-324, 142, 47.69), (-318, 142, 47.66), (-312, 142, 47.72), (-306, 142, 47.99), (-300, 142, 47.96), (-336, 136, 47.36),
    (-330, 136, 48.03), (-324, 136, 47.8), (-318, 136, 47.77), (-312, 136, 47.74), (-306, 136, 47.91), (-300, 136, 48.18), (-330, 130, 47.95), (-324, 130, 47.92),
    (-318, 130, 47.89), (-312, 130, 47.85), (-306, 130, 48.12), (-330, 124, 47.86), (-324, 124, 47.83), (-318, 124, 47.8), (-312, 124, 48.07), (-330, 118, 47.68),
    (-324, 118, 47.65), (-318, 118, 47.92), (-324, 112, 47.86), (-318, 112, 47.83), (-330, 106, 47.11), (-324, 106, 47.58), (-318, 106, 47.85), (-324, 100, 47.79),
    (-318, 100, 47.76), (-336, 94, 47.37), (-330, 94, 47.84), (-330, 88, 47.85), (-324, 88, 47.82), (-318, 88, 47.79), (-330, 82, 47.87), (-324, 82, 47.94),
    (-318, 82, 47.8), (-342, 214, 44.1), (-330, 214, 45.04), (-348, 208, 43.85), (-342, 208, 43.22), (-336, 208, 43.89), (-330, 208, 44.55), (-336, 202, 43.7),
    (-330, 202, 44.17), (-342, 196, 42.75), (-336, 196, 43.82), (-330, 196, 44.38),
])
VALLEY_BOX = (-390.0, -260.0, 40.0, 250.0)


def _bilinear(H, x0, step):
    def f(x, y):
        fx = np.clip((np.asarray(x, float) - x0) / step, 0, H.shape[1] - 1.001)
        fy = np.clip((np.asarray(y, float) - x0) / step, 0, H.shape[0] - 1.001)
        i, j = fx.astype(int), fy.astype(int)
        ax, ay = fx - i, fy - j
        return H[j, i] * (1 - ax) * (1 - ay) + H[j, i + 1] * ax * (1 - ay) + H[j + 1, i] * (1 - ax) * ay + H[j + 1, i + 1] * ax * ay
    return f


def valley(Hn, X, Y, FIXED, halls, half=800.0, step=5.0, sigma=6.0, prior=0.05):
    """The valley north-west of 과학관 on VALLEY_PTS: every node in VALLEY_BOX takes the Gaussian-weighted difference
    between them and the game's ground (the north road and the halls' feet count as unchanged).  Returns a summary"""
    H0 = Hn.copy()
    g0 = _bilinear(H0, -half, step)
    cx, cy, cd = [], [], []
    for x, y, z in VALLEY_PTS:
        cx.append(x); cy.append(y); cd.append(z - float(g0(x, y)))
    # between the yard's north end and the floor north of it (y 154 .. 196) the photos see only crowns: their difference
    # from the game's ground carried across the gap, from the one row to the other (the survey's 2024 spot in it,
    # (-313.2, 181.2) 46.31 m, is 7.3 m under the game: more than this)
    dzs = np.mean([d for (x, y, _), d in zip(VALLEY_PTS, cd) if 148 <= y <= 154])
    dzn = np.mean([d for (x, y, _), d in zip(VALLEY_PTS, cd) if 196 <= y <= 202])
    for y in np.arange(160.0, 192.0, 6.0):
        for x in np.arange(-342.0, -305.0, 6.0):
            cx.append(x); cy.append(y); cd.append(dzs + (dzn - dzs) * (y - 154.0) / 42.0)
    for x in np.arange(-356.0, -280.0, 4.0):           # (과학관's north road and the ground by it: as it is)
        for y in (40.0, 44.0, 48.0):
            cx.append(x); cy.append(y); cd.append(0.0)
    for h in halls:
        ring = h.buffer(3.0).exterior
        for t in np.arange(0.0, ring.length, 3.0):
            q = ring.interpolate(t)
            cx.append(q.x); cy.append(q.y); cd.append(0.0)
    cx, cy, cd = map(np.array, (cx, cy, cd))
    x0, x1, y0, y1 = VALLEY_BOX
    m = (X > x0) & (X < x1) & (Y > y0) & (Y < y1) & ~FIXED
    if halls:
        m &= ~shapely.contains_xy(unary_union(halls).buffer(2.0), X, Y)
    xs, ys = X[m], Y[m]
    w = np.exp(-((xs[:, None] - cx[None]) ** 2 + (ys[:, None] - cy[None]) ** 2) / (2 * sigma * sigma))
    Hn[m] = H0[m] + (w * cd[None]).sum(1) / (w.sum(1) + prior)
    moved = np.abs(Hn - H0)
    return dict(nodes=int((moved > 0.05).sum()), most=float(moved.max()), pts=len(VALLEY_PTS))


# ---------------------------------------------------------------------------------------------------------------------
# 독수리상 서쪽 마당 (reference/고증/4.5.2, 2.10): in the 1997-07-28 scans (26/16 · 27/17 · 26/15 ·
# 27/16) a level bare yard without a tree from the 제1공학관 road north to a curved row of trees, portable hoops on it
# and cars along its south edge and the road; the road itself and the lane west of the halls on the same level.  63
# points on the yard lie on 29.22 m (rms 0.5), 68 on the road and its rows on 29.19 m (rms 0.4); the ground round
# 백양로 and the side road there reads as the game's (0 .. +0.4 m; the survey's spot (-48.0, -170.6) +0.4 with its tilt out).  West of x -188 the ground stands a storey higher
# (34.5 - 35.0 m, the 제2공학관 road: a wall between, 29.0 m at x -182, 34.8 m at x -191).  The game had a lawn
# climbing from 29.6 m at the side road to 36 m at x -195, walks across it and trees.
# YARD: the bare earth; LOT: the yard, the road and its two rows, the lane along the halls' west end (G rows), level
# at LOT_Z (29.4 m); round it the ground is smoothed (fill) out to EAGLE_RING m, the halls' feet and the side road as they are
YARD = Polygon([(-186.0, -160.0), (-182.0, -153.0), (-175.0, -147.0), (-163.0, -143.0), (-150.0, -140.5), (-140.0, -139.0),
                (-128.0, -140.0), (-115.0, -144.0), (-104.0, -148.0), (-99.0, -152.0), (-97.5, -160.0), (-97.5, -185.8),
                (-109.0, -182.0), (-119.9, -178.7), (-143.1, -172.0), (-171.1, -164.3), (-177.2, -163.5), (-186.0, -164.0)])
EAGLE_ROAD = [(-188.0, -167.4), (-181.5, -167.2), (-177.2, -166.6), (-171.1, -167.4), (-143.1, -175.1), (-119.9, -181.8),
              (-109.0, -185.1), (-96.0, -189.2)]      # (the game's road, OSM's: where the scans have it)
LANE_W = Polygon([(-189.0, -166.0), (-182.0, -166.0), (-181.0, -197.0), (-189.0, -197.0)])     # (the G2 row's lane)
LOT_Z = datum.up(-134.94, -159.0, 28.45)               # (게임 기준: the photos' 29.2 m + 0.2, as the ground by 백양로 there reads, 0 .. +0.4)
EAGLE_RING = 22.0
EAGLE_EAST = -97.0          # (east of it, the side road and 백양로's west side: as they are)
EAGLE_WEST = -189.5         # (west of it, the upper level: 제2공학관's road, the middle round's)


def lot():
    road = LineString(EAGLE_ROAD).buffer(4.5, cap_style='flat')
    return unary_union([YARD, road, LANE_W]).buffer(0)


def road_south():
    """the paved margin south of the road where the scans have cars parked across it (T, S4 rows): 2.5 - 6 m out"""
    L = LineString([q for q in EAGLE_ROAD if q[0] > -166.0])          # (west -> east: its right side is the south)
    return L.buffer(-6.0, cap_style="flat", single_sided=True).difference(L.buffer(2.5, cap_style='flat'))


def eagle_yard(Hn, X, Y, FIXED, halls, fill):
    """The yard, the road and the lane level at LOT_Z, the ground round them smoothed (fill) out to EAGLE_RING m.  A
    hall's nodes (its outline and 1.5 m round it) within 6 m of the lot go to its floor (no lower: the walls stand on
    it; the game had 제1공학관's north block buried 5 m on its north side), its others stay.  halls: [(outline, base)].
    Returns a summary"""
    H0 = Hn.copy()
    LOT = lot()
    m = shapely.contains_xy(LOT, X, Y) & ~FIXED
    Hn[m] = LOT_Z
    feet = np.zeros(X.shape, bool)
    near_lot = shapely.contains_xy(LOT.buffer(6.0), X, Y) & ~FIXED
    for poly, base in halls:
        f = shapely.contains_xy(poly.buffer(1.5), X, Y) & (X > EAGLE_WEST - 30) & (X < EAGLE_EAST + 10) & (Y > -260) & (Y < -100)
        Hn[f & near_lot] = max(base, LOT_Z)
        Hn[f & ~near_lot & (Hn < base)] = base
        feet |= f
    ring = shapely.contains_xy(LOT.buffer(EAGLE_RING), X, Y) & ~m & ~FIXED & ~feet & (X < EAGLE_EAST) & (X > EAGLE_WEST)
    if ring.any():
        fill(ring)
    moved = np.abs(Hn - H0)
    return dict(lot=int(m.sum()), ring=int(ring.sum()), nodes=int((moved > 0.05).sum()), most=float(moved.max()))


def move_off(trees, shrubs, props):
    """what stood on the yard: trees step aside to its north edge, among the curved row of trees the scans have there
    (in their places in the list), shrubs and props go"""
    sh = YARD.buffer(0.6)
    n0 = (len(shrubs), len(props))
    shrubs[:] = [s for s in shrubs if not sh.contains(Point(s[1], s[2]))]
    props[:] = [p for p in props if not sh.contains(Point(p[1], p[2]))]
    north = LineString(list(YARD.exterior.coords)[1:10])          # (from its north-west corner round to the east end)
    e = north.offset_curve(2.1)                                   # (left of west -> east: north of the edge)
    moved = []
    for t in trees:
        if sh.buffer(0.3).contains(Point(t[1], t[2])):
            q = nearest_points(e, Point(t[1], t[2]))[0]
            moved.append((t[0], t[1], t[2]))
            t[1], t[2] = round(q.x, 2), round(q.y, 2)
    return n0[0] - len(shrubs), n0[1] - len(props), moved
