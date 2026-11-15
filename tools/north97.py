"""북쪽 땅(대우관 북쪽 숲 ~ 무악학사 · 북문)의 1997년 땅 (reference/고증/3.21_무악학사_북문.md 「땅의 높이」).
tools/build_campus.py 가 부른다.

    took, info = north97.grade(Hn, X, Y, FIXED, halls, fill)     # 격자 안(y 600 ~ 800): 심기가 끝난 뒤, 무악학사 길 바로 앞
    HN = muak.patch(raw, Hn, half, step, far, ground=north97.grid_z)    # 격자 북쪽 조각(muak.NORTH)
    muak.pads(HN, polys, fixed, north97.pad_levels(...))          # 정구장 셋과 우유처리장 동쪽 주차장

Frame: campus metres, x east, y north.  Every absolute height written here is above sea level (해발), taken up
to the working datum (해발 + tilt: tools/datum.py) where it is read, each at its place: GRID's nodes are (GRID_X0 + 5 i, GRID_Y0 + 5 j).

- The ground north of 대우관 was the surface model's (Copernicus), which reads crowns and roofs as ground and cuts the
  ridges: against the 1:5000 survey (국토지리정보원 수치지형도 「서울078」, surveyed 2006) + T it stood 3 - 5 m high round 북문
  and the road down to it, 2.4 - 4.4 m low round 무악학사, 5 - 13 m low on the wooded ridge the road crosses at y 690 -
  760.  The 1997-07-28 scans agree with the survey + T where they see the ground (1,469 points on 26/14 · 27/15 ·
  27/16 · 26/15: median +0.45 m, 16 - 84 % -0.4 .. +1.75), so the model was the one off (3.21 「땅의 높이」).
- GRID (tools/north97_ground.json, decimetres): the ground at the 5 m nodes x -100 .. 400, y 560 .. 1300.
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
- PADS: the level terraces the 5 m contours cannot hold, on the 1997 scans: the three 정구장 and the car park east of
  우유처리장 (LOT97, a plane).
- Nothing here draws from build_campus.py's `rng`.
"""
import json
import os

import numpy as np
import datum
import shapely
from shapely.geometry import Polygon
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
HALL_PAD = 7.1                    # the halls' feet (their floors read the nodes round their corners)
# the level terraces (1997 scans, the pairs' medians over each; 해발 at the place named)
COURT_Z = {429077768: datum.up(111.0, 962.0, 64.43),      # 서쪽 정구장 @ (111, 962): three pairs 64.2 - 64.5, rms 0.26; the 2006 spot on it 67.14
           429077769: datum.up(187.0, 980.0, 85.74),       # 동쪽 정구장 @ (187, 980): 26/14 - 27/15, windows 3 - 7 m 85.7 - 85.89
           429077775: datum.up(55.0, 1140.0, 59.58)}      # 북서 정구장 @ (55, 1140): 26/14 - 27/15 59.56, rms 0.26
# the car park east of 우유처리장 as the 1997 scans have it (the angled rows west and south-west of the aisle, the row
# along the east edge, the five stalls under the hall's south wall, its mouth on the road), and its plane: the aisle
# between the rows, 24 points where three pairs or more agree within 0.6 m (rms 0.11 m)
LOT97 = Polygon([(130.6, 879.0), (154.2, 877.5), (157.0, 877.3), (157.2, 869.5), (154.8, 842.0), (153.2, 840.5),
                 (153.0, 826.5), (141.5, 826.5), (139.5, 832.0), (136.0, 835.5), (129.6, 833.0), (110.6, 853.6),
                 (110.5, 861.9), (127.7, 859.7)])
LOT97_PLANE = dict(o=(145.0, 855.0), z=datum.up(145.0, 855.0, 72.24), gx=0.03, gy=-0.008)      # 해발 @ (145, 855); rising east 3 % on the working datum


def grid_z(x, y):
    """GRID, bilinear (on the working datum); arrays or numbers"""
    from scipy.ndimage import map_coordinates
    xa, ya = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    z = map_coordinates(GRID, [(ya.ravel() - GRID_Y0) / GRID_D, (xa.ravel() - GRID_X0) / GRID_D], order=1, mode='nearest')
    return z.reshape(xa.shape) if xa.ndim else float(z[0])


def lot_z(x, y):
    """the car park's plane (on the working datum)"""
    p = LOT97_PLANE
    return p['z'] + p['gx'] * (np.asarray(x, float) - p['o'][0]) + p['gy'] * (np.asarray(y, float) - p['o'][1])


def grade(Hn, X, Y, FIXED, halls, fill):
    """GRID inside REGION (the halls' feet and the nodes another rule set stay), eased out round it (fill:
    harmonic_fill).  Returns the nodes set (not to be FIXED: the road is graded on them next) and a summary."""
    H0 = Hn.copy()
    near_hall = shapely.contains_xy(unary_union([h.buffer(HALL_PAD) for h in halls]), X, Y)
    inr = shapely.contains_xy(REGION, X, Y) & ~near_hall & ~FIXED
    inr |= (Y >= 800.0 - 1e-6) & (X >= -100.0 - 1e-6) & (X <= 400.0 + 1e-6) & ~near_hall & ~FIXED     # (its north edge)
    Hn[inr] = grid_z(X[inr], Y[inr])
    ring = shapely.contains_xy(REGION.buffer(RING), X, Y) & ~inr & ~near_hall & ~FIXED
    if ring.any():
        fill(ring)
    d = (Hn - H0)[inr]
    moved = np.abs(Hn - H0)
    return inr, dict(nodes=int(inr.sum()), ring=int(ring.sum()), lo=round(float(d.min()), 1), hi=round(float(d.max()), 1),
                     moved=int((moved > 0.05).sum()))


def pad_levels(court_ids):
    """(levels for muak.pads) the courts' in the order given, then the car park's plane"""
    return [COURT_Z[i] for i in court_ids] + [lot_z]
