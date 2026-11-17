"""서쪽 · 남쪽 땅을 1997년 7월 항공사진 원본 스캔의 높이로 (#189 의 서쪽 · 남쪽 구역).  tools/build_campus.py 가 부른다.

    west_ground.field_sw(Hn, X, Y, FIXED, ...)       # 성산로 서쪽 끝 너머 길 · 대운동장 남서쪽 둑 · 야구장 (gate_town.plan 바로 뒤)
    west_ground.valley(Hn, X, Y, FIXED, halls)       # 과학관 북서쪽 골짜기의 공사 마당 (저장 바로 앞)
    west_ground.eagle_yard(Hn, X, Y, FIXED, halls, fill)    # 독수리상 서쪽 맨땅 마당 (저장 바로 앞)
    west_ground.move_off(trees, shrubs, props)       # 마당의 나무는 가장자리로(목록 제자리), 관목 · 소품은 뺌

Frame: campus metres, x east, y north.  All of it runs after the random planting (the trees, the decals and the cars
have read the ground as it was), and nothing here draws from build_campus.py's `rng`: the lists keep their order.

Heights are the photos' surface (tools/aerial97.py surface_z, 3 m windows, frame pairs one by one, correlation 0.7 and
over), carried to the game by the difference from ground that stays (reference/고증/4.8.2, 4.12, 3.22, 4.5.2).  All
heights written here are above sea level (해발: tools/datum.py).  The survey's spot heights (1:5000 수치지형도, 2006 ·
2024: #134) agree with the photos to 0.3 - 0.4 m
where they fall on open ground (the 야구장 1.95 m under the 대운동장, the photos 2.21 m).
"""
# (every absolute height written in this file's code is above sea level, 해발: datum.up · up3 · up_at · up_plane take it
# up to the working datum the ground is laid on, 해발 + tilt, where it is read: tools/datum.py.  The heights quoted
# in the comments are 해발 too)
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
# north-east of this line) have it flat at 30.4 - 31.2 m where the game had the surface model's 36 - 40 m (the trees of
# its two banks); the survey's spot on it (-510.9, -243.3) 31.42 m.
# NW_LINE runs from 20 m inside gate_town's road (which ssr_west puts on the same photos and datum) round
# past the grid's west edge; the road's bed every 16 m: (s, the photos' height, three stations' mean), on them +
# gate_town.SSR_W_DATUM.  Past s 200 (x -575, out of the ground map) the scans go on seeing the road falling north-west
# to its end at x -640 (2026-11-17: 1998-10 26/16 · 26/17 every 8 m, the 1997-07 and 1996-12 pairs where they hit it,
# within 0.3 m of each other; four offsets across the road, 3 m windows): 30.2 m at s 208, 27.5 m at s 296.  It used
# to hold the height of s 200 on to its end, 2.6 m over them at s 288, against the surface model's ground beside it;
# that ground is the survey's now (tools/yeonhui97.py: 0.9 - 1.3 m under the scans' road there), which the bed's end
# eases into
NW_LINE = [(-440.6, -321.6), (-461.7, -297.6), (-516.0, -235.0), (-575.0, -170.0), (-640.0, -100.0)]
NW_Z97 = datum.up_at([(0.0, 29.8), (32.0, 30.35), (48.0, 30.52), (64.0, 30.75), (80.0, 30.82), (96.0, 31.15), (112.0, 31.07),
          (128.0, 31.1), (144.0, 31.12), (160.0, 30.75), (176.0, 30.28), (192.0, 30.2), (200.0, 30.17), (208.0, 30.16),
          (224.0, 29.53), (240.0, 28.96), (256.0, 28.65), (272.0, 28.3), (288.0, 27.61), (296.0, 27.5)],
                     [(-440.6, -321.6), (-461.7, -297.6), (-472.2, -285.5), (-482.7, -273.4), (-493.2, -261.3), (-503.7, -249.2),
                      (-514.1, -237.1), (-524.9, -225.2), (-535.6, -213.4), (-546.4, -201.6), (-557.1, -189.7), (-567.9, -177.9),
                      (-573.2, -171.9), (-578.7, -166.0), (-589.6, -154.3), (-600.4, -142.6), (-611.3, -130.9), (-622.2, -119.2),
                      (-633.1, -107.4), (-638.5, -101.6)])
NW_HALF, NW_EASE = 17.0, 14.0          # the road's bed either side of the line, then eased into the ground beside it
NW_END = (290.0, 340.0)                # (s: eased out back into the ground beside it, round its end)
# 야구장 (OSM 421415364): the photos' 128 points on it lie on one level 31.04 m (rms 0.09), the 대운동장's 188 on 33.23 m
# (rms 0.10), the same frame pair: the 야구장 2.21 m under the 대운동장, 31.22 m here (the survey's 2006 spot 31.22 m, 1.95
# m under its 33.17 m).  The game had both pitches at the mean of the surface model under them (32.9 m).
# (The 대운동장's group on the survey's five spots: gate_town.WEST_DZ, 31.5 -> 31.22 m)
BASEBALL = dict(way=421415364, z=datum.up(-341.7, -310.19, 31.22), ring=16.0)       # (the 대운동장's 33.40 m less 2.21)


def field_sw(Hn, X, Y, FIXED, road, half_w, dz, field_patch, field_keep, pad, baseball_poly, keep, fill):
    """The road's bed north-west of gate_town's road (NW_LINE, on the photos), the 야구장 down to BASEBALL['z'], and the
    ground between the 대운동장, 학군단, the road and the 야구장 smoothed again (fill) between what stays: the oval and
    학군단's pad (FIXED; the ground within 6 m of the pad as it was), the two roads' beds, the 야구장, and `keep` (the
    campus roads' asphalt, the halls' feet, the 공학원 site).  road: gate_town's (Line), half_w its carriageway's half
    width, dz the photos -> game offset (gate_town.SSR_W_DATUM).  Returns a summary."""
    H0 = Hn.copy()
    L = LineString(NW_LINE)
    P = shapely.points(np.stack([X.ravel(), Y.ravel()], 1))
    box = (X > -700) & (X < -400) & (Y > -350) & (Y < -40)
    d = np.full(X.shape, 1e9)
    s = np.zeros(X.shape)
    d[box] = shapely.distance(L, P.reshape(X.shape)[box])
    s[box] = shapely.line_locate_point(L, P.reshape(X.shape)[box])
    zs, zz = zip(*NW_Z97)
    tgt = np.interp(s, zs, zz) + dz
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
# within 0.2 - 0.4 m): not the slope the game had (49 - 56 m, the surface model of the built-up valley of later
# years: the survey 2006 · 2024 has 46.3 - 52.6 m on its spots there, 7 - 8.5 m under the game) but a works yard cut
# into the valley, level at 47.3 m (prefab sheds, stacked materials, a track round its north end), and north of it the
# valley floor at 42.6 - 45.0 m.  Its points (x, y, the photos' height + 0.3: the datum seomun.py found at 과학관's
# corner and the road west of it); not the dip at its south end (44.4 - 45.5 m at y 58 - 74: a pit dug for a hall's
# footings, the square pads in it, which the game does not build: left out).  Along its east side the yard's rim:
# VALLEY_BENCH, a level bench 10 - 12 m wide 4.2 m over the yard (51.0 - 52.5 m, 58 points along y 56 - 140, curving
# north-east with the track; at its north end three frame pairs, 26/14 too, within 0.13 m, and the survey's spot
# (-287.7, 145.1) 51.95 m (2006) at its end), with a shed's roof on it (55.8 m: left out).  The ground takes the
# photos' difference from the game's round them (Gaussian, 6 m; out of reach it fades to nothing), the 과학관 north
# road (y 40 - 48) and the halls' feet as they are
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
# The bench: its outline (west edge north, then east edge back south, from the 58 points and the steps either side of
# them) and its level along y, (y, the photos' median there + 0.3)
VALLEY_BENCH = Polygon([(-314.0, 54.0), (-313.5, 64.0), (-313.5, 104.0), (-310.5, 110.0), (-305.5, 122.0), (-299.5, 130.0),
                        (-292.0, 141.0), (-286.0, 142.0), (-293.5, 128.0), (-297.5, 120.0), (-298.5, 104.0), (-300.5, 84.0),
                        (-301.5, 60.0), (-304.5, 53.0)])
VALLEY_BENCH_Z = [(60.0, 52.18), (74.0, 52.39), (90.0, 52.04), (106.0, 51.92), (122.0, 51.76), (136.0, 51.81)]
VALLEY_BOX = (-390.0, -260.0, 40.0, 250.0)
# The pit at the yard's south end (reference/고증/4.12 「골짜기 공사 마당의 남쪽 끝과 북쪽 바닥」): the 1997 scans (26/16 ·
# 26/15, windows 1.5 and 2.5 m agreeing, every 2 m) have its floor at 45.05 m (x -342 .. -316, y 57 .. 69: 70 points,
# 10 - 90 % 44.7 .. 45.7) and 44.55 m in its north-west arm (x -342 .. -330, y 70 .. 78: 32 points), cut 7 m under 과학관's
# north road (52.2 m at y 50, the floor at y 56) and under the bench east of it (51.9 m from x -313), 2.5 m under the
# yard's slab north of it (47.5 m); west of it a terrace at 45.6 m (x -352 .. -342, y 68 .. 90) and higher ground south
# of that (48.5 m).  In December 1996 the same place was the valley's natural slope at 51 - 52 m.  VALLEY_PIT_PTS: those
# points every 4 m (+0.3, as VALLEY_PTS); VALLEY_PIT: the floor's two parts, their nodes on its level (the grid's cells
# round them make the walls)
VALLEY_PIT_PTS = datum.up3([
    (-352, 78, 45.78), (-348, 78, 45.94), (-344, 78, 46.00), (-340, 78, 44.58), (-336, 78, 45.07), (-324, 78, 47.91),
    (-320, 78, 47.85), (-316, 78, 47.90), (-352, 74, 46.11), (-348, 74, 45.89), (-344, 74, 45.89), (-340, 74, 44.72),
    (-336, 74, 44.71), (-332, 74, 45.07), (-324, 74, 47.82), (-320, 74, 47.82), (-316, 74, 47.83), (-352, 70, 46.00),
    (-348, 70, 45.92), (-344, 70, 45.85), (-340, 70, 44.90), (-336, 70, 44.76), (-332, 70, 46.04), (-320, 70, 47.92),
    (-316, 70, 47.89), (-340, 66, 45.10), (-336, 66, 45.14), (-332, 66, 45.60), (-328, 66, 45.57), (-320, 66, 45.32),
    (-316, 66, 45.35), (-348, 62, 48.57), (-340, 62, 45.03), (-336, 62, 45.06), (-332, 62, 45.27), (-328, 62, 45.57),
    (-324, 62, 45.43), (-320, 62, 45.29), (-316, 62, 45.38), (-352, 58, 49.11), (-348, 58, 48.75), (-344, 58, 48.51),
    (-336, 58, 45.79), (-332, 58, 45.84), (-328, 58, 45.57), (-324, 58, 45.28), (-320, 58, 45.52), (-352, 54, 49.45),
    (-348, 54, 49.00), (-344, 54, 48.60),
])
VALLEY_PIT = [(Polygon([(-343.0, 56.0), (-315.5, 56.0), (-315.5, 69.5), (-343.0, 69.5)]), 45.35),
              (Polygon([(-343.0, 69.5), (-329.0, 69.5), (-329.0, 78.5), (-343.0, 78.5)]), 44.85)]
# Between the yard's north end and the floor north of it (y 154 .. 202) the 1997 scans see crowns; the leaf-off ones of
# December 1996 (26/16 · 26/15) see the forest floor: VALLEY_NORTH_PTS, their points (two windows within 0.6 m, crowns
# more than 1.5 m over their neighbours' dropped, every 6 m, +0.3).  Where the 1997 and 1998 frames see the ground too
# they read 0.5 m higher (1997, 50 points: crowns' edges) and 0.2 m lower (1998, 85).  East of x -318 (a row of dark
# crowns in 1996) none is kept north of y 160
VALLEY_NORTH_PTS = datum.up3([
    (-358, 202, 40.36), (-352, 202, 41.08), (-346, 202, 41.80), (-340, 202, 42.85), (-334, 202, 43.32), (-328, 202, 44.13),
    (-322, 202, 44.94), (-352, 196, 40.61), (-346, 196, 41.39), (-340, 196, 42.55), (-334, 196, 43.66), (-328, 196, 44.50),
    (-322, 196, 45.25), (-352, 190, 40.22), (-340, 190, 42.44), (-334, 190, 43.58), (-328, 190, 44.36), (-322, 190, 45.28),
    (-352, 184, 39.69), (-346, 184, 40.92), (-340, 184, 41.94), (-334, 184, 43.25), (-328, 184, 44.20), (-322, 184, 44.84),
    (-352, 178, 39.27), (-346, 178, 40.41), (-334, 178, 42.35), (-328, 178, 43.86), (-322, 178, 44.51), (-346, 172, 39.52),
    (-340, 172, 40.77), (-334, 172, 41.25), (-346, 166, 38.70), (-334, 166, 42.11), (-346, 154, 42.54),
    (-322, 154, 47.69), (-316, 154, 47.94), (-310, 154, 48.42), (-304, 154, 48.85),
    # (the track round the yard's north end, east side: 1996 · 1997 · 1998 within 0.8 m, their median)
    (-304, 181, 47.2), (-304, 193, 48.3), (-304, 199, 49.2), (-304, 205, 49.1), (-304, 211, 47.95), (-301, 187, 49.5),
    (-301, 199, 49.6), (-298, 184, 48.4), (-298, 193, 49.8), (-298, 196, 49.8),
])
# The valley's west bank between the yard and the town's ground (tools/yeonhui97.py lays the 1:5000 survey's surface
# west of x -362): crowns in every year's scans (the points west of x -365 are the roofs and trees of the houses
# below it); the 2006 and 2024 surveys' contours on it within 0 - 2.5 m of each other (the bank did not change):
# VALLEY_BANK_PTS, their mean at the grid's nodes from x -365 to -350 (해발, as the survey), laid at those nodes after
# the points' weighting (which would pull the town's ground at the bank's foot down with them).  The leaf-off scans' points on it
# (x -358 .. -350, y 130 .. 155: 41.3 - 42.5 m) lie within 1.2 m of them.  (A 1996 point at (-358, 154), 45.7 m, 5 - 8 m
# over both surveys, was a crown: left out.)  Without them the ground there was the base terrain's ridge eased into the
# town's, a bank 9 m high in 10 m by x -365
VALLEY_BANK_PTS = datum.up3([
    (-365, 125, 39.15), (-365, 130, 38.35), (-365, 135, 37.60), (-365, 140, 36.95), (-365, 145, 36.30), (-365, 150, 35.60),
    (-365, 155, 35.90), (-365, 160, 35.70), (-365, 165, 35.90),
    (-360, 125, 41.55), (-355, 125, 43.55), (-350, 125, 45.45), (-360, 130, 41.10), (-355, 130, 42.90), (-350, 130, 44.75),
    (-360, 135, 40.70), (-355, 135, 42.45), (-350, 135, 44.25), (-360, 140, 40.35), (-355, 140, 42.00), (-350, 140, 43.65),
    (-360, 145, 39.80), (-355, 145, 41.45), (-350, 145, 43.00), (-360, 150, 38.70), (-355, 150, 40.90), (-350, 150, 42.35),
    (-360, 155, 37.50), (-355, 155, 39.95), (-350, 155, 41.45), (-360, 160, 36.30), (-355, 160, 39.15), (-350, 160, 40.40),
    (-360, 165, 37.05), (-355, 165, 38.15), (-350, 165, 39.30),
])
# where the ground stays as it was round them (difference 0): west of the north floor (x -374, beyond the points), the
# bank east of the track round the north end (x -288), and east of the bench by the pit (x -300, y 54 .. 78: the 1997
# scans 55.0 - 55.8 m, the game's 55.3 m)
VALLEY_KEEP = [(-374.0, y) for y in range(150, 216, 5)] + [(-288.0, y) for y in range(150, 231, 5)] + \
    [(-300.0, y) for y in range(54, 79, 4)]


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
    for x, y, z in VALLEY_PTS + VALLEY_PIT_PTS + VALLEY_NORTH_PTS:
        cx.append(x); cy.append(y); cd.append(z - float(g0(x, y)))
    for x, y in VALLEY_KEEP:
        cx.append(x); cy.append(y); cd.append(0.0)
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
    # the bench along the yard's east side: its nodes on its level (the grid's cells either side make the steps)
    bench = shapely.contains_xy(VALLEY_BENCH, X, Y) & ~FIXED
    by, bz = zip(*VALLEY_BENCH_Z)
    Hn[bench] = np.interp(Y[bench], by, bz) + datum.tilt(X[bench], Y[bench])
    # the west bank: its nodes on the surveys' ground (not in the weighting above: the town's foot of it stays)
    bank = np.zeros(X.shape, bool)
    for x, y, z in VALLEY_BANK_PTS:
        i, j = int(round((x + half) / step)), int(round((y + half) / step))
        if not FIXED[j, i]:
            Hn[j, i] = z
            bank[j, i] = True
    # the pit's floor at the yard's south end: its nodes on its level
    pit = np.zeros(X.shape, bool)
    for poly, z in VALLEY_PIT:
        p = shapely.contains_xy(poly, X, Y) & ~FIXED
        Hn[p] = z + datum.tilt(X[p], Y[p])
        pit |= p
    moved = np.abs(Hn - H0)
    return dict(nodes=int((moved > 0.05).sum()), most=float(moved.max()), pts=len(VALLEY_PTS) + len(VALLEY_PIT_PTS) + len(VALLEY_NORTH_PTS),
                bank=int(bank.sum()),
                bench=int(bench.sum()), pit=int(pit.sum()))


# ---------------------------------------------------------------------------------------------------------------------
# 독수리상 서쪽 마당 (reference/고증/4.5.2, 2.10): in the 1997-07-28 scans (26/16 · 27/17 · 26/15 ·
# 27/16) a level bare yard without a tree from the 제1공학관 road north to a curved row of trees, portable hoops on it
# and cars along its south edge and the road; the road itself and the lane west of the halls on the same level.  63
# points on the yard lie on 28.27 m (rms 0.5), 68 on the road and its rows on 28.24 m (rms 0.4); the ground round
# 백양로 and the side road there reads as the game's (0 .. +0.4 m; the survey's spot (-48.0, -170.6) +0.4 with its tilt out).  West of x -188 the ground stands a storey higher
# (33.5 - 34.0 m, the 제2공학관 road: a wall between, 28.0 m at x -182, 33.8 m at x -191).  The game had a lawn
# climbing from 28.6 m at the side road to 35 m at x -195, walks across it and trees.
# YARD: the bare earth; LOT: the yard, the road and its two rows, the lane along the halls' west end (G rows), level
# at LOT_Z (28.4 m); round it the ground is smoothed (fill) out to EAGLE_RING m, the halls' feet and the side road as they are
YARD = Polygon([(-186.0, -160.0), (-182.0, -153.0), (-175.0, -147.0), (-163.0, -143.0), (-150.0, -140.5), (-140.0, -139.0),
                (-128.0, -140.0), (-115.0, -144.0), (-104.0, -148.0), (-99.0, -152.0), (-97.5, -160.0), (-97.5, -185.8),
                (-109.0, -182.0), (-119.9, -178.7), (-143.1, -172.0), (-171.1, -164.3), (-177.2, -163.5), (-186.0, -164.0)])
EAGLE_ROAD = [(-188.0, -167.4), (-181.5, -167.2), (-177.2, -166.6), (-171.1, -167.4), (-143.1, -175.1), (-119.9, -181.8),
              (-109.0, -185.1), (-96.0, -189.2)]      # (the game's road, OSM's: where the scans have it)
LANE_W = Polygon([(-189.0, -166.0), (-182.0, -166.0), (-181.0, -197.0), (-189.0, -197.0)])     # (the G2 row's lane)
LOT_Z = datum.up(-134.94, -159.0, 28.45)               # (the photos' 28.2 m + 0.2, as the ground by 백양로 there reads, 0 .. +0.4)
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


# ---------------------------------------------------------------------------------------------------------------------
# 공학원 공사장의 서쪽 · 남쪽 가 (reference/고증/4.4 「서쪽 가림막 밖의 띠」 · 「남쪽 가의 땅」; #189), after eng97.grade has
# laid the site's own ground, before the hoarding is set on it.  In the site's frame (build_campus.py TENNIS: u along
# its south side, v north-north-west):
# - West of the west hoarding (u -80.5) the 1997 scans (26/16 · 26/15, the one pair that sees it) have a level band at
#   the site's ground, 67 points on 28.94 m (sd 0.37; u -96 .. -80.5, v 30 .. 80), and a step up at u -97 .. -100 to
#   the ground west of it (47 points on 31.33 m, the game's 31.35 m).  The game ran eng97's ring across it as a ramp
#   from 29 to 31.3 m, up to 2.2 m over the band.  SITE_BAND: the band's u, v (eased in over v 18 .. 30: south of v 30
#   it is in one frame only) and its level.
# - Between the south hoarding and 성산로's bed the game kept the surface model's ground: a ridge of 30 - 32.4 m along
#   the row of trees there (the canopy in the model), 3 - 4 m over both the site's ground and the road's side.  The
#   scans see only the crowns (the same row stands in the 1998 frame); the survey (2006 · 2024) has no 30 m contour
#   between x -290 and -165 and its 2024 spot at the hoarding's line, (-237.8, -388.7), reads 29.84 m.  What the ground
#   under the trees did between those is not known (a smooth fill from the site to the road would put that spot 1.9 m
#   low): SITE_STRIP takes the ridge down to the spot's level, top, and leaves its sides as they were (between the
#   hoarding and the road's bed, gate_town's carriageway and 2.5 m)
# The leaf-off scans of December 1996 (26/16 · 26/17 · 26/15: reference/고증/4.4 「서쪽 가림막 밖의 띠」 · 「남쪽 가의 땅」):
# - the band north of v 30 on the same level as in July (1996 - 1997: +0.1 .. +0.25 m), and its south end, which the
#   1997 pair does not reach, rising to the site's south-west corner: v 25 29.0, v 20 29.4, v 15 - 5 29.9, v 0 30.1 m
#   (8 - 10 points every 5 m of v, u -95 .. -83).  SITE_BAND z_v: that profile, (v, 해발)
# - under the row of trees south of the site (then inside the hoarding, which stood at the pavement's north edge) a
#   terrace 0.85 - 1.15 m over the pavement, falling east with it: SITE_STRIP top_u, the ridge's top along u where the
#   1996 pair reads that ground (5 - 7 points every 8 m of u, v -13 .. -4); east of u -24 (the hoarding's top, no ground
#   read) the 2024 survey's spot height as before
SITE_BAND = dict(u=(-96.0, -80.5), v=(-4.0, 0.0, 80.0), z=28.95,
                 z_v=[(0.0, 30.1), (5.0, 29.95), (10.0, 29.9), (15.0, 29.9), (20.0, 29.4), (25.0, 29.0), (30.0, 28.9), (40.0, 28.95)])
SITE_STRIP = dict(u=(-80.0, 52.0), v=(-45.0, 6.0), top=29.84,
                  top_u=[(-88.0, 30.25), (-80.0, 29.8), (-56.0, 29.65), (-48.0, 29.45), (-40.0, 29.1), (-32.0, 29.2), (-24.0, 29.84)])


def site_band(site_o, site_rot):
    """the band west of the west hoarding as ground to paint (bare earth: the scans' bright band, a road or a yard)"""
    c, s = np.cos(site_rot), np.sin(site_rot)
    (u0, u1), (va, vb, vc) = SITE_BAND['u'], SITE_BAND['v']
    return Polygon([(site_o[0] + u * c - v * s, site_o[1] + u * s + v * c)
                    for u, v in ((u0 + 1.0, va + 4.0), (u1, va + 4.0), (u1, vc + 2.0), (u0 + 2.0, vc + 2.0))])


def site_edges(Hn, X, Y, FIXED, site_o, site_rot, road, half_w):
    """The band west of the 공학원 site down to SITE_BAND's level and the ridge south of it down to SITE_STRIP's top.
    road: gate_town's (Line), half_w its carriageway's half width.  Returns the nodes taken (to keep) and a summary"""
    H0 = Hn.copy()
    c, s = np.cos(site_rot), np.sin(site_rot)
    U = (X - site_o[0]) * c + (Y - site_o[1]) * s
    V = -(X - site_o[0]) * s + (Y - site_o[1]) * c
    (u0, u1), (va, vb, vc) = SITE_BAND['u'], SITE_BAND['v']
    w = ((U >= u0) & (U <= u1) & (V >= va) & (V <= vc) & ~FIXED) * _smooth((V - va) / (vb - va))
    zv, zz = zip(*SITE_BAND['z_v'])
    Hn[:] = Hn * (1 - w) + (np.interp(V, zv, zz) + datum.tilt(X, Y)) * w
    band = w > 0.999
    (su0, su1), (sv0, sv1) = SITE_STRIP['u'], SITE_STRIP['v']
    box = (U >= su0) & (U <= su1) & (V >= sv0) & (V < sv1)
    d = np.full(X.shape, 1e9)
    d[box] = shapely.distance(road.ls, shapely.points(X[box], Y[box]))
    tu, tz = zip(*SITE_STRIP['top_u'])
    top = np.interp(U, tu, tz) + datum.tilt(X, Y)
    strip = box & (d > half_w + 2.5) & ~FIXED & ~band & (Hn > top)
    Hn[strip] = top[strip]
    moved = Hn - H0
    return band | strip, dict(band=int(band.sum()), strip=int(strip.sum()), nodes=int((np.abs(moved) > 0.05).sum()),
                              band_most=float(moved[w > 0].min()) if (w > 0).any() else 0.0,
                              strip_most=float(moved[strip].min()) if strip.any() else 0.0)


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
