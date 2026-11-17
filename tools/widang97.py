"""제2인문관(위당관) 공사장의 1997년 7월 땅 (#189; reference/고증/3.12_빌링슬리관.md 「잔디 남쪽의 둑과 제2인문관 공사장」).
tools/build_campus.py 가 부른다.

    took, core, info = widang97.grade(Hn, X, Y, FIXED, halls, fill)   # 심기가 끝난 뒤, jonghap97.grade 바로 앞(core 는 그대로, 둘레는 그쪽이 다시 이음)
    widang97.WORKS · BANK                                        # 맨땅(둑은 잔디)으로 칠하고, 그 위를 지나던 지금의 길 · 보행로를 걷어 냄
    widang97.cut_paths(paths) · trees_aside(trees, halls)        # 게임이 읽는 길에서 · 나무를 목록 제자리에서

Frames: campus metres, x east, y north.  Every absolute height is above sea level (해발), taken up to the working
datum (해발 + tilt: tools/datum.py) at its own place where it is read.

The hall broke ground on 1997-05-29 (준공 1998-08-24, 3.1.1); on the 1997-07-28 scans (six frames, heights frame pair by
frame pair on a 4 m grid, the median of two to six pairs over 0.7) the whole of its site between 종합관's low block,
빌링슬리관's lawn and 교육관 is a bare works yard dug down to the level of the ground west and north of 교육관:

- YARD: 130 points 55.2 - 56.4 m (16 - 84 %), median 55.63 m, from the road along the low block's north wall (60.5 m, a
  storey over it within 4 m: the dig's edge) north to the foot of the bank under 빌링슬리관's lawn (the lawn 60.3 - 60.4
  m, the fence along its edge: 3.12) and from x -20 east to 교육관 and the yard north of it (55.0 - 55.9 m there, the
  2006 · 2024 surveys' 55 m too).  The game had a slope from 61 - 63 m at x -18 down to 54 - 56 m at x 10 - 18
  (OSM's later outline of the hall with its apron, lawns and the roads round it)
- BENCH: west of the yard a shelf at 61.44 m (24 points, 60.8 - 62.0 m), then the wooded slope up to the hill
  (tools/jonghap97.py HILL)

The dig's edges and what stood on the yard (2026-11-17, 3.12 「흙막이와 둑, 마당 위의 것」; the six scans and the leafless
1996 winter frames):

- CUT: along the south (the road on 종합관's low block's north side, 60.45 m) and the west (the shelf, 61.44 m) the
  yard ends at a row of soldier piles, the ground 4.8 - 5.8 m under within 1.5 - 2 m: a retained cut.  The nodes on
  either side take their own level and a deck carries the high side over the cells the line crosses (cut_grade,
  build_campus.py's dwb_deck: the 5 m grid made a 5 - 8 m slope of it); the piles, the timber lagging between them
  and a pipe railing on top (cut_walls), invisible guards along it
- the bank under 빌링슬리관's lawn: no wall in the frames from the south (weeds on it, not a face): the lawn (60.0 -
  60.3 m) holds to BANK_TOP, then 3.5 m of bank down to 56.7 m and a slope to the yard (bank_grade).  The fence of
  white posts and a rail along the lawn's edge (FENCE)
- DRIVE_W: the drive along 교육관's west side 3 - 7 m out of its wall stands at 55.0 - 55.5 m (1996: 55.5 - 56.2 m at
  its north end), not at the hall's floor (53.84 m, its FORECOURTS): the hall's feet stay, the drive comes up to it over
  the next cell (drive_grade)
- PIT: west of 교육관 a square pit 2 - 3 m under the yard: the nodes of its cells down to its floor, a deck over the
  rest of them, its lagged sides (pit_grade, pit_walls)
- on the yard (site()): the prefab office (white; the dark L by it is a flat stack of plates, its height the ground's)
  north of 교육관 and the hoarding along the yard's east side, the rubble heaps on its west half, the stack of long
  piles west of 교육관, an excavator and a crawler crane; on 종합관's yard north of the slab the rubble of 1996
  (JH_RUBBLE).  The truck by the office: tools/cars97_new.json

Nothing here draws from build_campus.py's `rng`.
"""
import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

import datum

YARD = Polygon([(-20.0, 331.0), (-14.0, 329.0), (-7.0, 327.5), (12.0, 327.5), (12.0, 350.0), (16.0, 358.0), (21.0, 362.5),
                (34.0, 362.5), (34.0, 385.0), (22.0, 386.5), (6.0, 387.0), (-6.0, 387.0), (-12.0, 385.0), (-20.0, 383.0)])
BENCH = Polygon([(-34.0, 339.0), (-24.0, 339.0), (-24.0, 375.0), (-34.0, 375.0)])
# the row of soldier piles round the dig's south-west corner, from the shelf's edge north of it (y 347.5) south and then
# east along the road on 종합관's low block's north side (the ground 61.4 / 60.4 m on one side, 55.0 - 55.6 m on the
# other within 1.5 - 2 m; the piles' heads in 27/16 · 26/15).  The high side is on the right going along it
CUT = LineString([(-24.0, 347.5), (-24.2, 344.5), (-27.2, 341.0), (-27.6, 333.5), (-23.2, 331.2), (-22.8, 328.5), (-20.0, 325.6),
                  (-12.0, 323.8), (-6.0, 323.4), (-4.5, 322.8), (-1.5, 321.0), (1.5, 320.0)])
HIGH = Polygon(list(CUT.coords) + [(1.5, 312.0), (-40.0, 312.0), (-40.0, 347.5)])
LOW = Polygon(list(CUT.coords) + [(12.0, 320.0), (12.0, 347.5)])
# (what was painted bare before the piles were read: the walks' decals taken off the yard stay as they were taken,
# build_campus.py, so that the list after them keeps its order)
WORKS0 = unary_union([YARD, BENCH, Polygon([(-24.5, 339.0), (-19.5, 339.0), (-19.5, 375.0), (-24.5, 375.0)])])
# the yard on to the piles; the shelf behind them (its south end, y 329 - 339, too)
YARD = unary_union([YARD, LOW])
BENCH = unary_union([BENCH, Polygon([(-34.0, 331.0), (-27.0, 331.0), (-27.0, 339.0), (-34.0, 339.0)])]).difference(LOW.buffer(0.3))
# what is painted bare: the yard, the shelf and the cut between them
WORKS = unary_union([YARD, BENCH, Polygon([(-24.5, 347.5), (-19.5, 347.5), (-19.5, 375.0), (-24.5, 375.0)])])
# the bank from the yard up to 빌링슬리관's lawn and its fence (3.12): lawn, not OSM's south road along its top (the road
# came with the hall; its east end past x 36, by the site offices, stays)
BANK = Polygon([(-12.0, 385.0), (-6.0, 387.0), (6.0, 387.0), (22.0, 386.5), (34.0, 385.0), (36.0, 384.5), (36.0, 389.5),
                (29.0, 390.5), (8.0, 395.5), (-4.0, 395.5), (-12.0, 394.0)])
YARD_Z = datum.up(0.0, 356.0, 55.63)
BENCH_Z = datum.up(-29.0, 357.0, 61.44)
RING = 8.0                        # eased out (harmonic) this far round them
HALL_PAD = 6.0                    # (교육관's west drive and north yard stay: its FORECOURTS)
Z_ROAD = datum.up(-4.0, 310.0, 60.45)   # the road the south piles hold up (tools/jonghap97.py Z_EAST, the same level)
CUT_SIDE = 7.5                    # nodes this near the piles take their side's level (cut_grade)
# the bank under 빌링슬리관's lawn (the frames from the south show weeds on it, no wall face): the lawn's edge (60.0 -
# 60.3 m, 1997; the game's bank started 3 - 5 m further north, the lawn 1 - 2 m under it east of x 20 and 1 m over it at
# the west end), the bank's foot 3.5 m on at 56.7 m, the yard 6 m further
BANK_TOP = LineString([(-0.9, 392.4), (15.6, 388.5), (21.4, 390.6), (46.6, 384.4)])
BANK_Z = (datum.up(25.0, 390.0, 60.15), datum.up(25.0, 383.0, 56.7))
BANK_W = (3.5, 9.5)                 # (the bank's foot, the yard's level: m out of BANK_TOP)
BANK_LAWN = 9.0                     # (the lawn's nodes this far back from it take its level)
BANK_X = (2.0, 47.0)                # (from 빌링슬리관's west end to the site offices; the lawn 0.6 m higher by x 2, up
#                                     towards the hill west of it: 60.6 m at x 5)
# the drive along 교육관's west side (gy: u north along the wall from its south-west corner, v west out of it): 55.0 -
# 55.5 m 3 - 7 m out (five points of four to fifteen frame pairs; the leafless 1996 frames 55.5 - 56.2 m at its north
# end), where the game had the hall's floor (53.84 m)
GY_O, GY_T = (17.82, 314.97), (0.25106, 0.96797)
DRIVE_W_UV = (7.0, 34.0, 2.5, 16.0)  # (u0, u1, v0, v1; west of x 12 the yard takes over)
DRIVE_Z = datum.up(15.0, 336.0, 55.3)


def grade(Hn, X, Y, FIXED, halls, fill):
    """YARD and BENCH level, eased round them (fill: harmonic_fill); the halls' feet and the nodes laid before
    (FIXED) stay.  Returns the nodes set (to be FIXED), the level ones among them (for jonghap97.grade to keep: it lays
    its roads over the ring and eases its own ring into them) and a summary"""
    H0 = Hn.copy()
    stay = FIXED | (shapely.contains_xy(unary_union([h.buffer(HALL_PAD) for h in halls]), X, Y) if halls else False)
    yard = shapely.contains_xy(YARD, X, Y) & ~stay
    bench = shapely.contains_xy(BENCH, X, Y) & ~stay
    Hn[yard] = YARD_Z
    Hn[bench] = BENCH_Z
    took = yard | bench
    free = shapely.contains_xy(unary_union([YARD, BENCH]).buffer(RING), X, Y) & ~took & ~stay & ~((X > 1.0) & (Y < 319.0))
    if free.any():
        fill(free)
    d = Hn - H0
    return took | free, took, dict(yard=int(yard.sum()), bench=int(bench.sum()), eased=int(free.sum()),
                             moved=(int((np.abs(d) > 0.05).sum()), round(float(d.min()), 1), round(float(d.max()), 1)))


def gy_xy(u, v):
    return (GY_O[0] + GY_T[0] * u - GY_T[1] * v, GY_O[1] + GY_T[1] * u + GY_T[0] * v)


DRIVE_W = Polygon([gy_xy(DRIVE_W_UV[0], DRIVE_W_UV[2]), gy_xy(DRIVE_W_UV[1], DRIVE_W_UV[2]), gy_xy(DRIVE_W_UV[1], DRIVE_W_UV[3]),
                   gy_xy(DRIVE_W_UV[0], DRIVE_W_UV[3])]).difference(Polygon([(-30.0, 300.0), (12.0, 300.0), (12.0, 400.0), (-30.0, 400.0)]))


def _side_dist(line, X, Y):
    """signed distance of points from a line: + on its right (going along it)"""
    P = shapely.points(X, Y)
    d = shapely.distance(line, P)
    s = shapely.line_locate_point(line, P)
    q1 = shapely.line_interpolate_point(line, np.maximum(s - 0.5, 0.0))
    q2 = shapely.line_interpolate_point(line, np.minimum(s + 0.5, line.length))
    tx, ty = shapely.get_x(q2) - shapely.get_x(q1), shapely.get_y(q2) - shapely.get_y(q1)
    q = shapely.line_interpolate_point(line, s)
    left = tx * (Y - shapely.get_y(q)) - ty * (X - shapely.get_x(q))
    return np.where(left > 0, -d, d), s


def bank_grade(Hn, X, Y, FIXED, halls, fill):
    """the lawn's edge, the bank under it and the slope to the yard on their levels (BANK_TOP, BANK_Z, BANK_W), the
    lawn's nodes BANK_LAWN m back on its level, the ring beyond eased; the halls' feet stay.  Returns the nodes set and
    a summary"""
    H0 = Hn.copy()
    sd, s = _side_dist(BANK_TOP, X, Y)                 # (+: right of the line going east: south, the yard)
    stay = FIXED | (shapely.contains_xy(unary_union([h.buffer(HALL_PAD) for h in halls]), X, Y) if halls else False)
    along = (s > 0.01) & (s < BANK_TOP.length - 0.01) & (X >= BANK_X[0]) & (X <= BANK_X[1])
    band = along & (sd > -BANK_LAWN) & (sd < BANK_W[1]) & ~stay
    zl, zf = BANK_Z
    zl = zl + np.clip((8.0 - X) / 6.0, 0.0, 1.0) * 0.6
    z = np.where(sd <= 0, zl, np.where(sd < BANK_W[0], zl + (zf - zl) * sd / BANK_W[0],
                                       zf + (YARD_Z - zf) * (sd - BANK_W[0]) / (BANK_W[1] - BANK_W[0])))
    Hn[band] = z[band]
    free = (sd <= -BANK_LAWN) & (sd > -BANK_LAWN - 6.0) & along & ~stay
    if free.any():
        fill(free)
    dd = Hn - H0
    return band | free, dict(band=int(band.sum()), eased=int(free.sum()),
                             moved=(int((np.abs(dd) > 0.05).sum()), round(float(dd.min()), 1), round(float(dd.max()), 1)))


def drive_grade(Hn, X, Y, FIXED, hall, fill, pad=2.5, ring=5.0):
    """the drive along 교육관's west side on its level (DRIVE_W, DRIVE_Z) over the hall's FORECOURTS: the nodes pad m
    and more out of its wall, the next ring m eased (the yard's nodes and the hall's feet stay).  Returns the nodes set
    and a summary"""
    H0 = Hn.copy()
    hp = shapely.contains_xy(hall.buffer(pad), X, Y)
    m = shapely.contains_xy(DRIVE_W, X, Y) & ~hp
    Hn[m] = DRIVE_Z
    free = shapely.contains_xy(DRIVE_W.buffer(ring), X, Y) & ~m & ~hp & ~shapely.contains_xy(YARD, X, Y) & (Y > 318.0)
    if free.any():
        fill(free)
    dd = Hn - H0
    return m | free, dict(level=int(m.sum()), eased=int(free.sum()),
                          moved=(int((np.abs(dd) > 0.05).sum()), round(float(dd.min()), 1), round(float(dd.max()), 1)))


def high_h(x, y):
    """the level the piles hold up (working datum): the road (Z_ROAD) along the south piles, the shelf (BENCH_Z) along
    the west ones, one into the other between y 326.5 and 331"""
    t = np.clip((np.asarray(y, float) - 326.5) / 4.5, 0.0, 1.0)
    return Z_ROAD + (BENCH_Z - Z_ROAD) * t


def cut_grade(Hn, X, Y, FIXED, halls, step=5.0, half=800.0):
    """after jonghap97.grade: the cells the piles cross keep all their nodes on the yard's level (so that the yard runs
    flat to the piles' foot), the nodes beyond them within CUT_SIDE m on the high side take its level (high_h); every
    cell with a node on the yard's level gets a deck over its high part (build_campus.py dwb_deck), as 간호대학 북쪽
    주차장's walls (tools/med97.py nurse_grade).  The halls' footprints (종합관's low block) are left.  Returns the nodes
    set, the deck's cells and outline, a summary"""
    import math
    H0 = Hn.copy()
    P = shapely.points(X, Y)
    near = shapely.distance(CUT, P) <= CUT_SIDE
    hb = unary_union([h.buffer(0.5) for h in halls])
    inh = shapely.contains_xy(hb, X, Y)
    x0, y0, x1, y1 = CUT.bounds
    wall = set()
    for j in range(int(math.floor((y0 + half) / step)) - 1, int(math.ceil((y1 + half) / step)) + 1):
        for i in range(int(math.floor((x0 + half) / step)) - 1, int(math.ceil((x1 + half) / step)) + 1):
            bx = shapely.geometry.box(-half + i * step, -half + j * step, -half + (i + 1) * step, -half + (j + 1) * step)
            if bx.intersection(HIGH).area > 0.02 and bx.intersection(LOW).area > 0.02 and bx.intersects(CUT):
                wall.add((j, i))
    low = np.zeros(X.shape, bool)
    for j, i in wall:
        low[j:j + 2, i:i + 2] = True
    lo = (low | (near & shapely.contains_xy(LOW, X, Y))) & ~inh
    hi = near & shapely.contains_xy(HIGH, X, Y) & ~inh & ~lo
    Hn[hi] = high_h(X[hi], Y[hi])
    Hn[lo] = YARD_Z
    # (every cell with a corner left low: those beside the wall's cells share their nodes and would dip to them)
    jj, ii = np.nonzero(lo)
    cells = {(j + a, i + b) for j, i in zip(jj, ii) for a in (-1, 0) for b in (-1, 0)}
    poly = unary_union([shapely.geometry.box(-half + i * step, -half + j * step, -half + (i + 1) * step, -half + (j + 1) * step)
                        for j, i in cells]).intersection(HIGH).difference(unary_union(list(halls)).buffer(0.05)) if cells else Polygon()
    cells = {(j, i) for j, i in cells if shapely.geometry.box(-half + i * step, -half + j * step, -half + (i + 1) * step,
                                                             -half + (j + 1) * step).intersection(poly).area > 0.02}
    dd = Hn - H0
    return hi | lo, cells, poly, dict(high=int(hi.sum()), low=int(lo.sum()), wall_cells=len(wall), cells=len(cells),
                                     deck_m2=round(poly.area, 1),
                                     moved=(int((np.abs(dd) > 0.05).sum()), round(float(dd.min()), 1), round(float(dd.max()), 1)))


# the square pit west of 교육관 (x 8 - 16, y 337.7 - 344.6: the same outline in both flight lines' frames, its floor
# 52.2 - 53.5 m, 2 - 3 m under the yard round it).  The 5 m grid cannot hold it: the nodes of the cells it lies in go
# down to its floor and a deck carries the yard over the rest of those cells (pit_grade, build_campus.py's dwb_deck)
PIT = Polygon([(8.0, 337.7), (16.0, 337.7), (16.0, 344.6), (8.0, 344.6)])
PIT_Z = datum.up(12.0, 341.0, 52.8)
PIT_NODES = (5.0, 15.0, 335.0, 345.0)        # (x0, x1, y0, y1: the nodes that go down to its floor)


def pit_grade(Hn, X, Y, sample, step=5.0, half=800.0):
    """after drive_grade: the nodes of PIT_NODES down to PIT_Z; the cells with such a node get a deck over all but the
    pit, on the ground as it was (top: sample of the ground before, working datum).  Returns the nodes set, the deck's
    cells, its outline, its level (a function) and a summary"""
    H0 = Hn.copy()
    m = (X >= PIT_NODES[0] - 0.01) & (X <= PIT_NODES[1] + 0.01) & (Y >= PIT_NODES[2] - 0.01) & (Y <= PIT_NODES[3] + 0.01)
    Hn[m] = PIT_Z
    jj, ii = np.nonzero(m)
    cells = {(j + a, i + b) for j, i in zip(jj, ii) for a in (-1, 0) for b in (-1, 0)}
    poly = unary_union([shapely.geometry.box(-half + i * step, -half + j * step, -half + (i + 1) * step, -half + (j + 1) * step)
                        for j, i in cells]).difference(PIT)

    def top(x, y):
        return sample(H0, x, y)
    return m, cells, poly, top, dict(nodes=int(m.sum()), cells=len(cells), deck_m2=round(poly.area, 1),
                                     dz=round(float((Hn - H0)[m].min()), 2))


def pit_walls(top, foot, step=0.5):
    """the pit's four sides from the yard (top) down to its floor (foot), timber lagging between H-piles as round the
    dig, facing in; the guards round its rim (polygons)"""
    import math
    quads, polys = [], []
    R = lambda q, z: [round(q[0], 3), round(q[1], 3), round(float(z), 3)]
    co = list(PIT.exterior.coords)               # (counter-clockwise: the inside on the left)
    for (xa, ya), (xb, yb) in zip(co, co[1:]):
        L = math.hypot(xb - xa, yb - ya)
        dx, dy = (xb - xa) / L, (yb - ya) / L
        nx, ny = -dy, dx                          # (inwards)
        n = max(1, int(math.ceil(L / step)))
        S = [(xa + (xb - xa) * k / n, ya + (yb - ya) * k / n) for k in range(n + 1)]
        zt = [top(x - nx * 0.05, y - ny * 0.05) for x, y in S]
        zb = [foot(x + nx * 0.2, y + ny * 0.2) - 0.05 for x, y in S]
        for k in range(n):
            a, b = S[k], S[k + 1]
            # (facing in, the pit on the left of the run: b, a, a's top, b's top; and the cap over the lagging)
            quads.append(['wood_dark', [R(b, zb[k + 1]), R(a, zb[k]), R(a, zt[k]), R(b, zt[k + 1])]])
            quads.append(['metal_dark', [R((a[0] - nx * 0.2, a[1] - ny * 0.2), zt[k] + 0.03), R((b[0] - nx * 0.2, b[1] - ny * 0.2), zt[k + 1] + 0.03),
                                         R(b, zt[k + 1] + 0.03), R(a, zt[k] + 0.03)]])
        for s in np.arange(0.9, L, 1.8):
            x, y = xa + dx * s, ya + dy * s
            z1, z0 = top(x - nx * 0.05, y - ny * 0.05) + 0.1, foot(x + nx * 0.2, y + ny * 0.2) - 0.05
            f0, f1 = (x - dx * 0.15 + nx * 0.06, y - dy * 0.15 + ny * 0.06), (x + dx * 0.15 + nx * 0.06, y + dy * 0.15 + ny * 0.06)
            quads.append(['metal_dark', [R(f1, z0), R(f0, z0), R(f0, z1), R(f1, z1)]])
        for u0 in np.arange(0.0, L, 4.0):
            u1 = min(u0 + 4.0, L)
            q = [(xa + dx * t - nx * w_, ya + dy * t - ny * w_) for t, w_ in ((u0, -0.02), (u1, -0.02), (u1, 0.3), (u0, 0.3))]
            polys.append([[round(c, 3) for c in p_] for p_ in q])
    return quads, polys


PILE = dict(every=1.8, w=0.3, proud=0.06, cap=0.25, rail=(1.1, 0.55), post=2.0)


def cut_walls(top, foot, step=0.5):
    """the piles round the dig (CUT): timber lagging from the yard (foot) up to the high side's level (top), H-piles
    every 1.8 m standing 6 cm proud of it, a steel cap along their heads and a pipe railing over it on the high side
    ([material, points]), and the guards along it (polygons: campus.json colliders)"""
    import math
    quads, polys = [], []
    R = lambda q, z: [round(q[0], 3), round(q[1], 3), round(float(z), 3)]
    co = list(CUT.coords)
    acc = 0.0
    for (xa, ya), (xb, yb) in zip(co, co[1:]):
        L = math.hypot(xb - xa, yb - ya)
        dx, dy = (xb - xa) / L, (yb - ya) / L
        nx, ny = dy, -dx                                  # (right of the run: the high side)
        n = max(1, int(math.ceil(L / step)))
        S = [(xa + (xb - xa) * k / n, ya + (yb - ya) * k / n) for k in range(n + 1)]
        zt = [top(x + nx * 0.05, y + ny * 0.05) for x, y in S]
        zb = [foot(x - nx * 0.1, y - ny * 0.1) - 0.05 for x, y in S]
        for k in range(n):
            a, b = S[k], S[k + 1]
            # the lagging, seen from the yard (left of the run), the cap's top and face along the heads
            quads.append(['wood_dark', [R(b, zb[k + 1]), R(a, zb[k]), R(a, zt[k]), R(b, zt[k + 1])]])
            c0, c1 = (a[0] - nx * 0.02, a[1] - ny * 0.02), (b[0] - nx * 0.02, b[1] - ny * 0.02)
            i0, i1 = (a[0] + nx * PILE['cap'], a[1] + ny * PILE['cap']), (b[0] + nx * PILE['cap'], b[1] + ny * PILE['cap'])
            quads.append(['metal_dark', [R(c1, zt[k + 1] + 0.05), R(c0, zt[k] + 0.05), R(i0, zt[k] + 0.05), R(i1, zt[k + 1] + 0.05)]])
            quads.append(['metal_dark', [R(c1, zt[k + 1] - 0.25), R(c0, zt[k] - 0.25), R(c0, zt[k] + 0.05), R(c1, zt[k + 1] + 0.05)]])
            # the railing's two pipes (thin strips, both faces)
            p0, p1 = (a[0] + nx * 0.15, a[1] + ny * 0.15), (b[0] + nx * 0.15, b[1] + ny * 0.15)
            for hz in PILE['rail']:
                ab = [R(p1, zt[k + 1] + hz - 0.025), R(p0, zt[k] + hz - 0.025), R(p0, zt[k] + hz + 0.025), R(p1, zt[k + 1] + hz + 0.025)]
                quads.append(['metal', ab])
                quads.append(['metal', ab[::-1]])
        # the H-piles and the railing's posts along this run
        s = (PILE['every'] - acc % PILE['every']) % PILE['every']
        w, p = PILE['w'] / 2, PILE['proud']
        while s <= L:
            x, y = xa + dx * s, ya + dy * s
            z1 = top(x + nx * 0.05, y + ny * 0.05) + 0.1
            z0 = foot(x - nx * 0.1, y - ny * 0.1) - 0.05
            f0, f1 = (x - dx * w - nx * p, y - dy * w - ny * p), (x + dx * w - nx * p, y + dy * w - ny * p)
            b0, b1 = (x - dx * w, y - dy * w), (x + dx * w, y + dy * w)
            quads.append(['metal_dark', [R(f1, z0), R(f0, z0), R(f0, z1), R(f1, z1)]])
            quads.append(['metal_dark', [R(f0, z0), R(b0, z0), R(b0, z1), R(f0, z1)]])
            quads.append(['metal_dark', [R(b1, z0), R(f1, z0), R(f1, z1), R(b1, z1)]])
            s += PILE['every']
        s = (PILE['post'] - acc % PILE['post']) % PILE['post']
        while s <= L:
            x, y = xa + dx * s + nx * 0.15, ya + dy * s + ny * 0.15
            z1 = top(x, y)
            zh = z1 + PILE['rail'][0] + 0.03
            for ex, ey in ((dx, dy), (nx, ny)):
                e0, e1 = (x - ex * 0.03, y - ey * 0.03), (x + ex * 0.03, y + ey * 0.03)
                quads.append(['metal', [R(e0, z1), R(e1, z1), R(e1, zh), R(e0, zh)]])
                quads.append(['metal', [R(e1, z1), R(e0, z1), R(e0, zh), R(e1, zh)]])
            s += PILE['post']
        acc += L
        # the guards: on the high side, along the run in 4 m pieces
        for u0 in np.arange(0.0, L, 4.0):
            u1 = min(u0 + 4.0, L)
            q = [(xa + dx * t + nx * w_, ya + dy * t + ny * w_) for t, w_ in ((u0, -0.02), (u1, -0.02), (u1, 0.3), (u0, 0.3))]
            polys.append([[round(c, 3) for c in p_] for p_ in q])
    return quads, polys


# --- what stood on the yard and round it on 1997-07-28 (site(): campus.json `jh_site`, blender/landmarks.py jh_site) ---
# the prefab office north of 교육관: a white box 2.5 m high (its roof 57.7 m in fifteen frame pairs, the ground 55.2 m)
# (x0, x1, y0, y1, height); the dark L west and north of it and the dark box east of that read the ground's own height
# in every pair (55.0 - 55.8 m): flat stacks of plates and formwork, not the second office first read there
SHEDS = [(45.5, 49.75, 372.75, 379.5, 2.5)]
STACKS = [(30.0, 33.5, 372.0, 380.0, 0.35), (34.0, 42.0, 377.5, 382.2, 0.35), (42.0, 46.5, 379.5, 382.2, 0.3)]
# the stack of long piles west of 교육관 (their tops 55.6 - 56.3 m, the ground 55.3 - 55.6): ~12 m long members lying
# north-north-west, (cx, cy, length, width, angle deg, height)
PILE_STACK = (9.5, 330.5, 11.0, 5.5, -50.0, 0.6)
# the rubble and spoil heaps on the yard's west half (56.2 - 57.5 m on the yard's 55.6): (x, y, rx, ry, height, angle
# deg); the round pale one (sand) south-east of them
HEAPS = [(-6.5, 369.0, 5.0, 3.5, 1.6, 20.0), (-8.0, 359.0, 5.0, 4.0, 1.9, -10.0), (-12.5, 348.5, 3.0, 5.0, 1.2, 0.0),
         (-12.0, 337.5, 3.0, 4.0, 1.0, 0.0), (-4.0, 362.5, 2.8, 2.8, 0.7, 0.0)]
HEAP_PALE = {4}
# the machines in both flight lines' frames: an excavator, its arm to the west; a crawler crane west of 교육관, its boom
# to the east-north-east (x, y, heading deg, kind)
MACHINES = [(-10.0, 375.0, 180.0, 'excavator'), (11.0, 354.0, 22.0, 'crane')]
# the fence along 빌링슬리관's lawn: white posts about 2.5 m apart with a rail (the frames from the south and the north)
FENCE = LineString([(2.8, 398.6), (51.1, 385.8)])
FENCE_STEP = 2.5
# along the yard's east side, by the drive west of 연희관: a hoarding, its top a pale band in every frame (the east
# frames see its west face): white sheet over a blue foot, as 공학원's
HOARD = LineString([(52.5, 386.0), (49.0, 361.0)])
# 종합관's yard north of the slab (tools/jonghap97.py frame (u, v)): the rubble of 1996's occupation and fire, heaps up to
# 1.3 m over the paving (72.2 - 73.4 m on 72.1) between u 20 and 31, v 23 and 34
JH_RUBBLE = [(22.0, 31.0, 2.2, 1.6, 0.9, 10.0), (25.5, 32.5, 1.8, 1.4, 0.7, -20.0), (28.5, 30.0, 2.4, 2.0, 1.2, 30.0),
             (24.0, 27.5, 2.6, 2.0, 1.1, 0.0), (27.5, 25.5, 2.0, 1.6, 0.8, 15.0), (30.0, 27.0, 1.4, 1.2, 0.6, 0.0),
             (21.0, 25.0, 1.6, 1.4, 0.5, 40.0), (23.0, 33.5, 1.2, 1.0, 0.4, 0.0)]


def site(ground):
    """the things on the yards for blender/landmarks.py jh_site, each [x, y, z (해발 at export: tools/datum.py), ...]
    on the ground as saved (ground: working datum)"""
    import math
    import jonghap97
    R = lambda v: round(float(v), 3)
    out = dict(sheds=[], stacks=[], piles=[], heaps=[], machines=[], posts=[], rubble=[], hoard=[])
    for x0, x1, y0, y1, h in SHEDS:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        z = min(ground(x, y) for x in (x0, x1) for y in (y0, y1))
        out['sheds'].append([R(cx), R(cy), R(z), R(y1 - y0), R(x1 - x0), R(math.pi / 2), h])
    for x0, x1, y0, y1, h in STACKS:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        out['stacks'].append([R(cx), R(cy), R(ground(cx, cy)), R(x1 - x0), R(y1 - y0), 0.0, h])
    cx, cy, L, W, a, h = PILE_STACK
    out['piles'].append([cx, cy, R(ground(cx, cy)), L, W, R(math.radians(a)), h])
    for k, (x, y, rx, ry, h, a) in enumerate(HEAPS):
        out['heaps'].append([x, y, R(ground(x, y)), rx, ry, h, R(math.radians(a)), 'dirt_pale' if k in HEAP_PALE else 'dirt'])
    for x, y, a, kind in MACHINES:
        out['machines'].append([x, y, R(ground(x, y)), R(math.radians(a)), kind])
    for d in np.arange(0.0, FENCE.length + 0.01, FENCE_STEP):
        q = FENCE.interpolate(d)
        out['posts'].append([R(q.x), R(q.y), R(ground(q.x, q.y))])
    for d in np.linspace(0.0, HOARD.length, int(round(HOARD.length / 2.5)) + 1):
        q = HOARD.interpolate(d)
        out['hoard'].append([R(q.x), R(q.y), R(ground(q.x, q.y))])
    for u, v, rx, ry, h, a in JH_RUBBLE:
        x, y = jonghap97.xy(u, v)
        out['rubble'].append([R(x), R(y), R(ground(x, y)), rx, ry, h, R(math.radians(a) + math.atan2(jonghap97.TU[1], jonghap97.TU[0]))])
    return out


def site_clear():
    """where the site's things stand (for the trees, shrubs and props there)"""
    cs = [Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]) for x0, x1, y0, y1, _ in SHEDS + STACKS]
    cs += [Point(x, y).buffer(max(rx, ry)) for x, y, rx, ry, _, _ in HEAPS]
    cs += [Point(x, y).buffer(4.0) for x, y, _, _ in MACHINES]
    return unary_union(cs)


def cut_paths(paths):
    """the walks and drives the game reads (the minimap, the crowd) that ran across the yard (OSM's, after the hall):
    each keeps its longest stretch off the yard (5 m or more) in its place in the list, its other stretches of 10 m or
    more at the list's end; one with none goes.  Returns (cut, gone, added)"""
    zone = unary_union([WORKS, BANK]).buffer(1.0)
    n, more = [0, 0], []
    for p in list(paths):
        if len(p['pts']) < 2:
            continue
        ls = LineString(p['pts'])
        if ls.intersection(zone).length <= 1.0:
            continue
        d = ls.difference(zone)
        pcs = sorted([g for g in getattr(d, 'geoms', [d]) if g.geom_type == 'LineString' and g.length >= 5.0],
                     key=lambda g: -g.length)
        if pcs:
            p['pts'] = [[round(x, 1), round(y, 1)] for x, y in pcs[0].coords]
            more += [dict(p, pts=[[round(x, 1), round(y, 1)] for x, y in g.coords]) for g in pcs[1:] if g.length >= 10.0]
            n[0] += 1
        else:
            paths[:] = [q for q in paths if q is not p]
            n[1] += 1
    paths += more
    return n[0], n[1], len(more)


def trees_aside(trees, halls, pad=2.0):
    """trees the random planting put on the yard and the shelf (the scans have none): each moved in its place in the list
    to the nearest free point pad m outside them, clear of the halls by 2.5 m and of the trees there by 3 m.
    Returns the moves"""
    clear = unary_union([YARD, BENCH])
    hb = unary_union([h.buffer(2.5) for h in halls])
    rings = [g.exterior for g in getattr(clear.buffer(pad), 'geoms', [clear.buffer(pad)])]
    spots = [r.interpolate(d) for r in rings for d in np.arange(0.0, r.length, 0.5)]
    spots = [q for q in spots if not hb.contains(q)]
    inside = [t for t in trees if clear.buffer(0.5).contains(Point(t[1], t[2]))]
    near = [Point(t[1], t[2]) for t in trees if not any(t is i for i in inside) and abs(t[1]) < 80 and abs(t[2] - 357.0) < 70]
    spots = [q for q in spots if all(q.distance(o) > 3.0 for o in near)]
    moved = []
    for t in inside:
        if not spots:
            break
        q = min(spots, key=lambda q_: q_.distance(Point(t[1], t[2])))
        moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
        t[1], t[2] = round(q.x, 2), round(q.y, 2)
        spots = [s for s in spots if s.distance(q) > 3.5]
    return moved
