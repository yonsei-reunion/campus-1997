"""북쪽 땅(대우관 북쪽 숲 ~ 무악학사 · 북문)의 1997년 땅 (reference/고증/3.21_무악학사_북문.md 「땅의 높이」).
tools/build_campus.py 가 부른다.

    took, info = north97.grade(Hn, X, Y, FIXED, halls, fill)     # 격자 안(y 600 ~ 800): 심기가 끝난 뒤, 무악학사 길 바로 앞
    HN = muak.patch(raw, Hn, half, step, far, ground=north97.grid_z)    # 격자 북쪽 조각(muak.NORTH)
    muak.pads(HN, courts + north97.PADS, fixed, north97.pad_levels(...))   # 정구장 셋, 우유처리장 동쪽 주차장, 농업개발원 앞마당,
                                                                         # 2학사 앞마당, 2학사 서쪽 날개 윗단
    muak.draw_map(north97.paint97(gm))                              # 그 둘의 칠(그리기만)

Frame: campus metres, x east, y north.  Every absolute height written here is above sea level (해발), taken up
to the working datum (해발 + tilt: tools/datum.py) where it is read, each at its place: GRID's nodes are (GRID_X0 + 5 i, GRID_Y0 + 5 j).

- The ground north of 대우관 was the surface model's (Copernicus), which reads crowns and roofs as ground and cuts the
  ridges: against the 1:5000 survey (국토지리정보원 수치지형도 「서울078」, surveyed 2006) + T it stood 3 - 5 m high round 북문
  and the road down to it, 2.4 - 4.4 m low round 무악학사, 5 - 13 m low on the wooded ridge the road crosses at y 690 -
  760.  The 1997-07-28 scans agree with the survey + T where they see the ground (1,469 points on 26/14 · 27/15 ·
  27/16 · 26/15: median +0.45 m, 16 - 84 % -0.4 .. +1.75), so the model was the one off (3.21 「땅의 높이」).
- GRID (tools/north97_ground.json, centimetres): the ground at the 5 m nodes x -100 .. 400, y 440 .. 1300 (the rows
  south of y 560 were made the same way on 2026-11-15 for MOUND below; the rows from y 560 north are the first ones).
  - to the survey sheet's north edge (y 1215): the 2006 edition's contours (5 m) filled between (harmonic) and
    smoothed 2.5 m, its spot heights' residuals spread over 12 m (the 2024 edition's spots too where the two editions'
    contours agree within 1.5 m), + T
  - past the sheet's edge the surface model, the difference at the edge faded out over 60 m
  - nudged to the 1997 scans where they see the ground: 2.5 m lattice, 3 m windows, the pairs that agree within
    0.6 m (north of y 1000 the one east-west pair 26/14 - 27/15, correlation 0.78 or more), off the halls, within 4 m of
    the survey, locally plane (rms 0.3 m over 6.5 m); spread over 5 m.  This is where the ground of July 1997 differs
    from the survey's of 2006 (the 3 · 4학사 site, the terraces the contours smooth over)
  - the table against the survey's spots: 2006 34 spots rms 0.33 m, 2024 23 spots rms 0.72 m; against the photo
    points rms 0.46 m
- REGION: where GRID is laid inside the game's 5 m grid: the wooded ridge and the road's sides from y 600 (east of
  the road's first leg) and y 690 (west of it: 서울외국인학교's halls and yards south of that stay) to the grid's north edge,
  eased out round it (harmonic) into the ground as it stays; the halls' feet kept.  North of the grid GRID is the patch.
- STRIP: east of the road from y 570, where tools/east97.py's wood ends, to REGION (the ring between the two had left
  it 2 - 4 m off the survey), the corner's roads and walks as they were.
- MOUND: the wood west and north-west of 대우관 (between its back yard, 서울외국인학교 and 연희관's hall): the surface
  model's ground stood 3 - 9 m under the survey there (the mound's top cut with the halls taken out of the model; the
  2006 spot (47.6, 575.0) 82.04 m, the 2006 and 2024 editions' 80 m contours round the same mound), and in the two
  clearings the 1997 frames see on it (28, 540) · (28, 548) six pairs agree with the survey within 0.3 m.  GRID there,
  the built nodes (FIXED: the back yard, its roads) and the halls' feet kept, eased over MOUND_RING only (the school's
  yard west of it stays level).
- PADS: the level terraces the 5 m contours cannot hold, on the 1997 scans: the three 정구장, the car park east of
  우유처리장 (LOT97, a plane), the yard south of 농업개발원 (AGRI_YARD, a plane), the yard in front of 2학사 (DORM_YARD,
  a quadric) and the terrace along its west wing (NW_TERRACE, level); the last two paved in the drawn map only (paint97).
- Nothing here draws from build_campus.py's `rng`.
"""
import json
import math
import os

import numpy as np
import datum
import shapely
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

_G = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'north97_ground.json')))
GRID_X0, GRID_Y0, GRID_D = _G['x0'], _G['y0'], _G['step']      # (the table's south-west node, spacing)
GRID = np.array([[int(v) for v in r.split()] for r in _G['rows_south_to_north']], float) / 100.0    # 해발, m
# (up to the working datum, to the decimetre it was first written in: tools/datum.py)
GRID = np.round(GRID + datum.tilt(*np.meshgrid(GRID_X0 + GRID_D * np.arange(GRID.shape[1]),
                                               GRID_Y0 + GRID_D * np.arange(GRID.shape[0]))), 1)
# where GRID is laid inside the grid (the patch north of y 800 takes all of it)
REGION = Polygon([(-100.0, 800.0), (-100.0, 745.0), (-30.0, 745.0), (-30.0, 690.0), (195.0, 690.0), (195.0, 600.0),
                  (400.0, 600.0), (400.0, 800.0)])
RING = 30.0                       # eased out (harmonic) this far round REGION
# the strip east of the road between tools/east97.py's wood (to y 570) and REGION: laid after REGION's ring, eased over
# STRIP_RING east of the corner only (the corner's roads and walks keep the ground REGION's ring gives them)
STRIP = Polygon([(215.0, 570.0), (400.0, 570.0), (400.0, 600.0), (215.0, 600.0)])
STRIP_RING, STRIP_X0 = 10.0, 207.0
MOUND = Polygon([(12.0, 447.0), (12.0, 612.0), (160.0, 612.0), (160.0, 551.0), (150.0, 545.0), (100.0, 515.0), (68.0, 500.0),
                 (68.0, 447.0)])
MOUND_RING = 10.0
# the road along the back yard's north-west side (대우관 북쪽 길: the corner to the yard's west drive) and its walk stay as
# the game has them, in MOUND and its ring: the survey's contours run over its cut (the 1997 frames see the road at
# (84, 508 - 524) 1.6 - 2.7 m under them), and the cars' loop and the deck by the low court's stall lie on it
MOUND_HOLD = LineString([(201.4, 571.3), (193.1, 568.4), (179.7, 563.6), (147.1, 547.2), (123.7, 534.6), (120.8, 532.2),
                         (89.9, 506.8), (83.8, 485.7)]).buffer(5.0).union(
    LineString([(201.9, 576.9), (192.7, 573.3), (172.3, 565.2), (140.8, 546.8), (124.3, 537.4), (119.9, 533.8), (88.3, 508.0),
                (82.0, 486.2)]).buffer(3.5))
HALL_PAD = 7.1                    # the halls' feet (their floors read the nodes round their corners)
# the level terraces (1997 scans, the pairs' medians over each; 해발 at the place named)
COURT_Z = {429077768: datum.up(111.0, 962.0, 64.43),      # 서쪽 정구장 @ (111, 962): three pairs 64.2 - 64.5, rms 0.26; the 2006 spot on it 64.13
           # 동쪽 정구장 @ (187, 980): the 2024 spot on it (190.1, 996.9) 84.72; both surveys' 85 m contour runs along its
           # east (uphill) edge.  The pairs disagree by 0.8 m on its pale floor (26/14 - 27/15 85.55, 27/15 - 27/16 84.72,
           # 0.3 and 0.1 m over the spots round it): reference/고증/3.21 「땅의 높이」
           429077769: datum.up(187.0, 980.0, 84.72),
           429077775: datum.up(55.0, 1140.0, 59.58)}      # 북서 정구장 @ (55, 1140): 26/14 - 27/15 59.56, rms 0.26
# the car park east of 우유처리장 as the 1997 scans have it (the angled rows west and south-west of the aisle, the row
# along the east edge, the five stalls under the hall's south wall, its mouth on the road), and its plane: the aisle
# between the rows, 24 points where three pairs or more agree within 0.6 m (rms 0.11 m)
LOT97 = Polygon([(130.6, 879.0), (154.2, 877.5), (157.0, 877.3), (157.2, 869.5), (154.8, 842.0), (153.2, 840.5),
                 (153.0, 826.5), (141.5, 826.5), (139.5, 832.0), (136.0, 835.5), (129.6, 833.0), (110.6, 853.6),
                 (110.5, 861.9), (127.7, 859.7)])
LOT97_PLANE = dict(o=(145.0, 855.0), z=datum.up(145.0, 855.0, 72.24), gx=0.03, gy=-0.008)      # 해발 @ (145, 855); rising east 3 % on the working datum
# the yard south of 농업개발원 (1997 frames 26/14 · 27/15 · 27/16): bare and as bright as the courts, eleven cars on it
# (eight nose in under the hall's south wall, two past its east end, one across its west end: tools/cars97_new.json
# 「농업개발원 남쪽 앞마당」), the wood south of it; its plane through 16 points where two pairs or more agree within
# 0.6 m off the cars (rms 0.13 m): 해발 83.85 m at (185, 906), rising 1.7 % east and 0.9 % north in 해발
# (datum.up_plane makes them the working datum's)
AGRI_YARD = Polygon([(174.72, 915.85), (201.29, 912.35), (201.55, 914.33), (207.01, 913.62), (205.31, 900.73), (189.38, 902.32),
                     (180.68, 905.18), (174.85, 906.86), (171.43, 907.71), (171.82, 910.68), (174.0, 910.4)])
AGRI_PLANE = dict(zip(('z', 'gx', 'gy'), datum.up_plane((83.85, 0.0169, 0.0091), 185.0, 906.0)), o=(185.0, 906.0))
# the paved terrace along 2학사's west wing (between it and the bank down to the north-west courts) as the 1997 frames
# have it: 10.5 m wide from 2.5 m off the wing's west wall, a row of stalls against the wall (white lines every 2.3 m,
# a long line 7.2 m out) and the drive beyond, four cars in it (tools/cars97_new.json 「북서 정구장 동쪽 윗단」); at its
# south end the drive turns south past the wing's corner.  Level: 26/14 x 26/13 put it at 66.0 - 66.4 m along the wing
# (the pair reads the courts 0.3 m under the east-west pairs), and the east-west pairs where the wing does not hide it
# (84 - 90, 1124 - 1136) at 66.1 - 66.4: 해발 66.3 m (reference/고증/3.21 「북서 정구장 동쪽 윗단 · 2학사 앞마당」).
# Laid in the wing's frame: the wing's south-west corner (89.4, 1135.9) as the game has it, along 102 deg
_WING = (89.4, 1135.9, 102.0)


def _wing_xy(u, v):
    """the wing's frame -> campus metres: u along the wing (north-north-west), v out of its west wall"""
    x0, y0, a = _WING
    t = (math.cos(math.radians(a)), math.sin(math.radians(a)))
    return round(x0 + t[0] * u - t[1] * v, 2), round(y0 + t[1] * u + t[0] * v, 2)


NW_TERRACE = Polygon([_wing_xy(u, v) for u, v in ((-12.0, 0.0), (-12.0, 6.5), (-4.0, 6.5), (0.0, 13.5), (44.0, 13.5),
                                                  (44.0, 2.5), (0.0, 2.5), (0.0, 0.0))])
NW_TERRACE_PLANE = dict(zip(('z', 'gx', 'gy'), datum.up_plane((66.3, 0.0, 0.0), 82.0, 1150.0)), o=(82.0, 1150.0))
# (the drive on from its south end, between the wood and the works' hoarding, down to the west road: paved, on the
# ground as it is)
NW_TERRACE_DRIVE = Polygon([(85.54, 1122.81), (86.5, 1113.0), (87.5, 1103.0), (92.5, 1104.0), (92.0, 1113.0), (91.89, 1124.16)])
# the yard in front of 2학사 (between its wings, west of the planted island, round the island's south end to the west
# road where the barrier stood): asphalt, four cars on it (tools/cars97_new.json 「2학사 앞마당」).  Its surface: the 96
# points on it (1 m apart) where two pairs or more of 26/14 x 26/13, 26/14 x 27/15, 26/13 x 27/15 agree within 0.6 m,
# off the cars, as a quadric in (u, v) = ((x - 108) / 10, (y - 1140) / 10), rms 0.15 m (the largest 0.4 m): level at
# 70.2 - 70.4 m by the wings, falling to the south-west (69.0 - 69.2 m at the yard's south end, 68.4 - 68.7 m by the
# road).  The game had it 1.5 - 1.8 m low by the west wing, rising east 9 %
DORM_YARD = Polygon([(106.5, 1127.5), (106.5, 1141.0), (100.2, 1141.0), (96.3, 1159.5), (96.0, 1162.0), (114.0, 1164.0),
                     (115.5, 1156.0), (113.2, 1153.5), (113.0, 1150.0), (114.3, 1149.0), (114.3, 1135.0), (115.5, 1132.0),
                     (120.0, 1129.5), (117.5, 1126.0), (113.0, 1126.0)])
DORM_YARD_FIT = (69.991, 0.349, 0.713, -0.302, -0.302)       # (해발 @ (108, 1140), u, v, uv, vv)


def grid_z(x, y):
    """GRID, bilinear (on the working datum); arrays or numbers"""
    from scipy.ndimage import map_coordinates
    xa, ya = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    z = map_coordinates(GRID, [(ya.ravel() - GRID_Y0) / GRID_D, (xa.ravel() - GRID_X0) / GRID_D], order=1, mode='nearest')
    return z.reshape(xa.shape) if xa.ndim else float(z[0])


def lot_z(x, y, p=LOT97_PLANE):
    """the car park's plane (on the working datum); p: another plane (AGRI_PLANE)"""
    return p['z'] + p['gx'] * (np.asarray(x, float) - p['o'][0]) + p['gy'] * (np.asarray(y, float) - p['o'][1])


def agri_z(x, y):
    """the yard south of 농업개발원 (on the working datum)"""
    return lot_z(x, y, AGRI_PLANE)


def terrace_z(x, y):
    """the terrace along 2학사's west wing (on the working datum)"""
    return lot_z(x, y, NW_TERRACE_PLANE)


def yard_z(x, y):
    """the yard in front of 2학사 (on the working datum): DORM_YARD_FIT, held at its edge past the points it was fitted on"""
    u = (np.clip(np.asarray(x, float), 100.0, 118.0) - 108.0) / 10.0
    v = (np.clip(np.asarray(y, float), 1126.0, 1162.0) - 1140.0) / 10.0
    c = DORM_YARD_FIT
    return c[0] + c[1] * u + c[2] * v + c[3] * u * v + c[4] * v * v + datum.tilt(x, y)


def paint97(gm):
    """the patch's ground map as drawn (muak.draw_map): gm with the terrace by 2학사's west wing and its drive paved and
    the yard in front of 2학사 asphalt.  The map's other uses (the halls' and houses' taken ground, the far forest's
    clear and woods: web/src/terrain.js draws their crowns in order) keep gm as it was, so that nothing moves"""
    asph = gm['asphalt'].union(DORM_YARD)
    pav = gm['pavers'].union(unary_union([NW_TERRACE, NW_TERRACE_DRIVE])).difference(asph)
    done = asph.union(pav)
    return dict(gm, asphalt=asph, pavers=pav, dirt=gm['dirt'].difference(done), woods=gm['woods'].difference(done))


def grade(Hn, X, Y, FIXED, halls, fill):
    """GRID inside REGION, STRIP and MOUND (the halls' feet and the nodes another rule set stay), eased out round each
    (fill: harmonic_fill).  Returns the nodes set (not to be FIXED: the road is graded on them next) and a summary."""
    H0 = Hn.copy()
    near_hall = shapely.contains_xy(unary_union([h.buffer(HALL_PAD) for h in halls]), X, Y)
    inr = shapely.contains_xy(REGION, X, Y) & ~near_hall & ~FIXED
    inr |= (Y >= 800.0 - 1e-6) & (X >= -100.0 - 1e-6) & (X <= 400.0 + 1e-6) & ~near_hall & ~FIXED     # (its north edge)
    Hn[inr] = grid_z(X[inr], Y[inr])
    ring = shapely.contains_xy(REGION.buffer(RING), X, Y) & ~inr & ~near_hall & ~FIXED
    if ring.any():
        fill(ring)
    ins = shapely.contains_xy(STRIP, X, Y) & ~inr & ~near_hall & ~FIXED
    Hn[ins] = grid_z(X[ins], Y[ins])
    rings = shapely.contains_xy(STRIP.buffer(STRIP_RING), X, Y) & ~inr & ~ins & ~near_hall & ~FIXED & (X >= STRIP_X0)
    if rings.any():
        fill(rings)
    hold = shapely.contains_xy(MOUND_HOLD, X, Y)
    inm = shapely.contains_xy(MOUND, X, Y) & ~near_hall & ~FIXED & ~inr & ~ring & ~hold
    Hn[inm] = grid_z(X[inm], Y[inm])
    ringm = shapely.contains_xy(MOUND.buffer(MOUND_RING), X, Y) & ~inr & ~inm & ~ring & ~near_hall & ~FIXED & ~hold
    if ringm.any():
        fill(ringm)
    d = (Hn - H0)[inr]
    dm = (Hn - H0)[inm]
    moved = np.abs(Hn - H0)
    return inr | ins | inm, dict(nodes=int(inr.sum()), ring=int(ring.sum()), lo=round(float(d.min()), 1),
                                 hi=round(float(d.max()), 1), strip=int(ins.sum()), strip_ring=int(rings.sum()),
                                 mound=int(inm.sum()), mound_ring=int(ringm.sum()), mound_lo=round(float(dm.min()), 1),
                                 mound_hi=round(float(dm.max()), 1), moved=int((moved > 0.05).sum()))


def pad_levels(court_ids):
    """(levels for muak.pads) the courts' in the order given, then the car park's plane, the yard's south of 농업개발원,
    the yard's in front of 2학사 and the terrace's by its west wing (PADS)"""
    return [COURT_Z[i] for i in court_ids] + [lot_z, agri_z, yard_z, terrace_z]


PADS = [LOT97, AGRI_YARD, DORM_YARD, NW_TERRACE]       # (after the courts: muak.pads, in pad_levels' order)
