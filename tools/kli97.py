"""한국어학당 (언어연구교육원 건물, 1991년 4월 준공) in 1997 (#230; reference/고증/3.27_한국어학당.md).
tools/build_campus.py reads the outline, plan(), grade() and the painted places; blender/landmarks.py kli builds the
hall and its terrace from the plan.

Frame: O the south-west front wall's north-west corner, u south-east along the front (ANG), v north-east into the
hall.  The scans' frame in the record (origin the eaves' south-east corner, u north-west) is u_s = 79.7 - u,
v_s = v + 0.3: the walls stand 0.3 m inside the eaves' coping line.

- The outline, the roofs' heights and the places of the gabled bay, the porch, the tower, the dormers, the rear wing
  and the two rear bays are the 1996 - 1999 scans' (each edge on its own height's plane in seven to ten frames) and
  the 1:5000 survey's of 2006; the walls (storeys, window counts, the granite storeys, the porch's openings) are the
  two photos of 2004 (reference/동문_이중윤/2004-09_한국어학당_정면.jpg, 2004_한국어학당_남동쪽_끝에서.jpg).
- The ground round it (grade): the paved car park before the south-east half of the front a storey and a half under
  the entrance terrace, the terrace a slab over the car park's level along its retaining wall, the yard south-west of
  it, the garden before the north-west half, the back down to the lane behind it, the yard at the south-east end.
  Late: after the planting, cars and decals, which keep their draws.
- Heights written here are 해발 (FLOOR, the *_Z tables) or metres over the entrance floor; plan() lifts the floor to
  the working datum at the outline's middle, grade() each node at its own place (tools/datum.py).
"""
import math

import numpy as np
import shapely
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

import datum

KLI = 371403603
O = (460.88, 179.41)
ANG = -58.30                       # degrees: u, along the front to the south-east
L, W = 79.4, 14.55                 # the walls (the eaves' coping line: 80.0 x 15.3 m)
FLOOR = 58.7                       # 해발: the entrance floor (the terrace 58.0 m, five risers under it)
F1, FU, FB, FB2 = 4.1, 3.85, 5.3, 3.9   # storeys: the entrance storey, the three brick ones, the two under the entrance floor
EAVES = 16.55                      # over the floor: the top of the granite band under the eaves (해발 75.25)
RIDGE, RIDGE_MID = 20.9, 21.4      # (79.6; the middle block's 80.1)
GABLES = (21.7, 21.3)              # the end gables' copings: north-west (80.4), south-east (80.0)
MID = (24.23, 37.68, 0.3)          # the middle block: along the front, how far out of the wall
UC = 30.95                         # the glazed bay's, the porch's and the cross gable's axis
BAY = dict(w=9.2, d=1.15, sh=18.6, apex=21.2, ridge=20.7)     # the granite frame: out of the wall; shoulders, apex, the roof behind
PORCH = dict(w=9.35, d=5.53, top=4.1, ridge=4.9, apex=5.4)
STAIR = (39.38, 44.07, 0.89, 7.0, 23.3, 24.75)                # the brick tower: u0, u1, v0, v1, eaves, ridge
REAR = (35.16, 43.89, 8.7, 16.9, 19.3, 22.0)                  # the rear wing (hipped at its far end)
NWIN = (11, 19)                    # windows of the walls either side of the middle block (one more in each of its flanks)
PROJ = (9, 11, 0.65)               # the bay of the south-east wall standing out: from window, to window, how far
DORMER = (18.3, 19.7)              # the dormers' cheeks and ridges (77.0, 78.4)
DORMERS_F = ((11.07, 4.8), (19.86, 4.8), (50.52, 4.8), (59.64, 4.4), (68.06, 4.8))     # (middle, width); the fourth on PROJ
DORMERS_B = ((11.05, 4.7), (28.55, 4.7), (50.42, 4.7), (68.26, 4.7))
REAR_BAYS = ((18.2, 22.16, 1.9), (57.59, 61.6, 2.5))          # u0, u1, how far out of the back wall
REAR_PORCH = (5.4, 5.4, -1.7, -0.3)                            # width, depth past the bay, eaves, ridge (57.0, 58.4)
BALCONY = (7.3, 4.3, 1.4)          # the end walls' balconies: middle (v), width, how far out
# the terrace before the porch: u0, u1 (its paving), the planter's far edge (the retaining wall), its outer edge v
TERRACE = (22.1, 38.1, 40.0, -16.5)
TERRACE_Z = 58.0
YARD_V, YARD_Z = -24.0, 57.5       # the yard south-west of it, down to the road
LOT = (42.3, 86.0, -23.5, -3.6)    # the paved car park: u0, u1, v0, v1
LOT_Z = 53.0
NWF_U, NWF_Z = (-8.0, 0.0, 10.0, 20.0, 22.1), (57.35, 57.3, 58.2, 58.4, 58.0)       # before the north-west half (v -8 .. 0)
BACK_U = (-8.0, -0.1, 9.9, 19.9, 29.9, 39.9, 49.9, 59.9, 69.9, 79.9)                        # the lane behind (v 22 .. 35)
BACK_Z = (55.2, 54.4, 53.5, 52.6, 51.6, 50.6, 50.0, 49.1, 48.25, 47.3)
BACK_FOOT = 0.8                    # the planted strip under the back wall over the lane's level
SE_D, SE_Z = (0.0, 6.5, 10.5), (50.5, 49.5, 48.6)                                      # the yard at the south-east end, by distance
RING = 15.0
HALL_PAD = 3.0
# ---- round it, read again off the scans (#233, 2026-11-22; reference/고증/3.27 「둘레의 차 · 길 · 울」).  Cars only where
# both frames of 1997-07-28 (27/16 · 27/17, each on its own) have one in the same place (tools/cars97.py's rule); a car
# here: (u, v, heading in the frame: degrees from +u towards +v, the nose's way; size, shade as in cars97)
WALL_END = -26.0                   # the terrace's retaining wall (u = TERRACE[2]) runs on past the slab to the yard's end
BANK_V, BANK_Z = (-21.5, -24.0, -26.5, -30.0), (53.0, 54.9, 57.2, 57.0)  # east of it past the middle row: the planted island
# the car park before the south-east half: the row along the wall's planter and the middle row (each car nose in), lined;
# (the first line's u, the pitch, the stalls, the stalls' back and front v)
WALL_ROW = (42.84, 2.28, 16, -4.3, -8.5)
MID_ROW = (42.34, 2.32, 14, -14.5, -19.2)
FRONT_CARS = [(53.05, -6.4, 90, None, 'w'), (57.6, -6.45, 90, 'm', 'd'), (73.6, -6.35, 90, 'm', 'w'), (75.9, -6.5, 90, 'm', 'w'),
              (78.6, -6.0, 90, 'm', 'w')] + \
             [(u_, -16.65, -90, 'm', w_) for u_, w_ in ((45.75, 'd'), (50.2, 'd'), (52.7, 'w'), (55.2, 'w'), (57.75, 'w'), (60.0, 'w'),
                                                       (64.1, 'w'), (66.6, 'w'), (68.95, None), (71.25, 'w'), (73.6, 'd'))] + \
             [(83.5, -14.15, -3, 'm', 'w'), (84.1, -16.6, 8, 'm', 'w'), (84.55, -18.65, 12, 'm', 'd'), (85.35, -21.15, 17, 'm', 'w'),
              (85.35, -23.25, 17, 'm', 'w'), (86.2, -25.2, 12, 'm', 'w'), (86.15, -29.75, 10, 'm', 'w'), (86.4, -31.7, 10, 'm', 'w'),
              (86.15, -34.0, 5, 'm', 'w'),                                  # (along the lot's south-east edge, unlined)
              (74.0, -27.9, 5, 'm', 'w'), (74.0, -30.35, 0, 'm', 'w'), (68.0, -30.2, -90, 'm', 'd'), (70.2, -30.3, -90, 'm', 'd')]
# the curved drive before the north-west half: two by its inner kerb, one by the outer
CURVE_CARS = [(11.5, -14.5, -72, None, 'w'), (14.3, -12.7, -65, None, 'w'), (14.65, -19.5, -85, None, None)]
# behind: a row of stalls at right angles to the lane, nose to the hall, broken by the flight down to the north-west rear
# porch and the paved way to the south-east one; the lane past it
BACK_ROW = (-11.5, 78.0, 21.8, 26.6)
BACK_V = 24.2
BACK_CARS = [(-9.4, 'd'), (-7.0, 'w'), (-4.65, 'w'), (0.15, 'd'), (2.55, 'd'), (5.25, 'w'), (7.65, 'w'), (10.05, 'w'), (12.45, 'w'),
             (25.1, 'd'), (29.15, 'w'), (31.4, 'w'), (33.8, 'w'), (36.15, 'w'), (38.4, 'd'), (40.75, 'w'), (42.95, 'd'), (45.55, 'w'),
             (47.8, 'w'), (50.2, 'd'), (52.55, 'w'), (54.75, 'w'), (64.35, 'w'), (66.55, 'w'), (69.0, 'd'), (71.5, 'w')]
BACK_EMPTY = (-2.25, 14.85, 27.1, 73.9, 76.2)
LANE = [(-42.0, 28.6), (-11.5, 28.0), (-11.5, BACK_ROW[3]), (78.0, BACK_ROW[3]), (80.0, 28.6), (100.0, 28.6), (100.0, 34.6),
        (-42.0, 34.6)]
# the north-west rear porch's flight: down from the lane between two retaining walls (u), under the porch roof to the
# door of the lowest storey; the south-east porch on the lane's level
PIT = dict(walls=(17.5, 22.5), t=0.25, top_v=25.8, top_z=52.6, floor=49.5, tread=0.32, end_v=26.0)
REAR_FLOOR = (49.5, 49.55)         # 해발: the two rear porches' floors (doors of the lowest storey)
# the north-west car park: an aisle from the drive up to the lane, a lined row either side (cars nose in) and a short
# third row beside the plant yard; (the aisle side's u, the far side's u, the first line's v, the pitch, the stalls)
NW_AISLE = (-28.0, -20.4, -6.0, 28.6)
NW_ROWS = [(-28.0, -33.3, -3.2, 2.3636, 11), (-20.4, -15.6, -3.8, 2.48, 10), (-10.0, -14.2, -1.4, 2.4, 5)]
NW_CARS = [(-30.45, v_, 180, 'm', w_) for v_, w_ in ((21.7, 'd'), (17.2, 'w'), (12.4, 'w'), (10.1, 'w'), (7.8, 'd'), (5.3, None),
                                                    (2.7, 'w'), (0.2, 'w'), (-2.1, None))] + \
          [(-17.65, v_, 0, 'm', w_) for v_, w_ in ((17.2, 'd'), (14.5, 'd'), (12.1, 'w'), (9.7, 'w'), (7.1, 'w'), (4.7, None), (2.3, None),
                                                  (-0.1, None), (-2.7, 'w'))] + \
          [(-11.9, v_, 180, None, w_) for v_, w_ in ((4.7, None), (2.3, None), (-0.1, 'd'))]
# the ground there (the aisle's own heights, 1996 - 1999 pairs; the rows' carry the cars' roofs), and between the plant
# yard and the hall's north-west end down to the lane: 해발 on (NW_GU, NW_GV)
NW_GU = (-34.0, -24.4, -12.0, -8.0, -4.0, 0.0)
NW_GV = (-6.0, 2.0, 8.0, 14.0, 20.0, 26.0, 32.0)
NW_GZ = ((59.0, 58.6, 58.4, 58.3, 57.9, 57.5, 57.5), (58.8, 58.3, 58.2, 58.1, 57.6, 56.7, 56.8), (57.8, 58.1, 58.0, 57.5, 56.8, 55.8, 55.7),
         (57.6, 57.5, 57.3, 56.6, 55.6, 55.3, 55.2), (57.4, 57.3, 57.1, 56.3, 55.4, 55.0, 54.8), (57.3, 57.3, 57.0, 56.0, 55.2, 54.6, 54.4))
# the plant yard off the north-west end: a walled yard (u0, u1, v0, v1; its floor and its wall's height approximations), two round
# cooling towers (u, v, radius; their tops 60.3 m in eight pairs of four years)
PLANT = dict(yard=(-14.2, -1.6, 11.2, 17.6), floor=57.0, wall=2.4, towers=[(-11.8, 14.4, 1.7), (-5.6, 14.5, 1.7)], top=60.3)


def xy(u, v):
    a = math.radians(ANG)
    return (O[0] + u * math.cos(a) - v * math.sin(a), O[1] + u * math.sin(a) + v * math.cos(a))


def uv(x, y):
    a = math.radians(ANG)
    dx, dy = np.asarray(x, float) - O[0], np.asarray(y, float) - O[1]
    return dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)


def rect(u0, u1, v0, v1):
    return Polygon([xy(u0, v0), xy(u1, v0), xy(u1, v1), xy(u0, v1)])


def outline():
    return [tuple(round(c, 2) for c in xy(u, v)) for u, v in ((0.0, 0.0), (L, 0.0), (L, W), (0.0, W))]


def hall():
    """the hall with all that stands out of its box: the frame and the porch, the rear wing, bays and porches"""
    hb, hp = BAY['w'] / 2, PORCH['w'] / 2
    return unary_union([rect(0.0, L, 0.0, W), rect(UC - hp, UC + hp, -PORCH['d'], 0.0), rect(MID[0], MID[1], -MID[2], 0.0),
                        rect(REAR[0], REAR[1], W, REAR[3])] +
                       [rect((a + b) / 2 - REAR_PORCH[0] / 2, (a + b) / 2 + REAR_PORCH[0] / 2, W, W + d + REAR_PORCH[1])
                        for a, b, d in REAR_BAYS])


TERRACE_POLY = rect(TERRACE[0] - 0.3, TERRACE[2], TERRACE[3], 0.0)
# (the car park's asphalt: not up the bank between it and the yard, round the retaining wall's end)
LOT_POLY = rect(*LOT[:2], *LOT[2:]).difference(rect(TERRACE[2], 45.5, -24.0, BANK_V[0]))
# the walk from the terrace on to the road south-west of it (the scans: a pale strip on the porch's axis)
WALK_POLY = rect(UC - 5.0, UC + 5.0, -30.0, TERRACE[3] + 0.2)
# (#233: the lot's paving on south and south-east past the lines, where the cars along its edge stood; the lane and the
# row behind; the north-west car park and the road from its aisle to the curved drive)
LOT_S = Polygon([xy(u_, v_) for u_, v_ in ((64.0, -23.5), (81.0, -10.0), (89.5, -10.0), (90.0, -37.0), (70.0, -37.0), (64.0, -30.0))])
BACK_POLY = unary_union([rect(*BACK_ROW), Polygon([xy(u_, v_) for u_, v_ in LANE])])
NW_POLY = unary_union([rect(NW_ROWS[0][1], NW_ROWS[1][1], NW_AISLE[2], 22.8), rect(NW_AISLE[0] - 0.4, NW_AISLE[1], NW_AISLE[2], NW_AISLE[3]),
                       rect(NW_ROWS[2][1], NW_ROWS[2][0], NW_AISLE[2], 10.6), rect(NW_ROWS[0][1], -8.0, -6.5, -1.4)])
WALL_EXT = rect(TERRACE[2] - 0.3, TERRACE[2], WALL_END, TERRACE[3])
PLANT_POLY = rect(*PLANT['yard'])
REGION = unary_union([rect(-8.0, 88.0, W / 2, 35.0), rect(-8.0, 41.0, -8.0, W / 2), rect(TERRACE[0], 41.0, YARD_V, 0.0),
                      rect(41.0, LOT[1], -24.0, W / 2), rect(L, L + 12.5, 0.5, W), rect(-34.0, -8.0, -8.0, 35.0),
                      rect(TERRACE[2], 45.5, -30.0, BANK_V[0])])


def plan():
    hb = BAY['w'] / 2
    d = [[u, w, -PROJ[2] if k == 3 else 0.0, DORMER[0], DORMER[1], 'f'] for k, (u, w) in enumerate(DORMERS_F)]
    d += [[u, w, W, DORMER[0], DORMER[1], 'b'] for u, w in DORMERS_B]
    return dict(o=list(O), ang=ANG, L=L, W=W, floor=datum.up(*datum.centroid(outline()), FLOOR),
                f1=F1, fu=FU, fb=FB, fb2=FB2, z_eaves=EAVES, z_ridge=RIDGE, z_ridge_mid=RIDGE_MID, z_gables=list(GABLES),
                mid=list(MID), uc=UC, bay=dict(BAY), porch=dict(PORCH), nwin=list(NWIN), proj=list(PROJ),
                pipes=[3, 7, 13], dormers=d, stair=list(STAIR), rear=list(REAR), rear_bays=[list(q) for q in REAR_BAYS],
                rear_porch=list(REAR_PORCH), balcony=list(BALCONY),
                terrace=dict(u0=TERRACE[0], u1=TERRACE[1], wall=TERRACE[2], v0=TERRACE[3], z=round(TERRACE_Z - FLOOR, 3),
                             low=round(LOT_Z - FLOOR, 3)))


def nw_z(U, V):
    """해발 of the north-west car park and the strip off the hall's north-west end (NW_GZ, bilinear)"""
    from scipy.interpolate import RegularGridInterpolator
    f = RegularGridInterpolator((NW_GU, NW_GV), np.array(NW_GZ), bounds_error=False, fill_value=None)
    U, V = np.asarray(U, float), np.asarray(V, float)
    return f(np.stack([np.clip(U, NW_GU[0], NW_GU[-1]), np.clip(V, NW_GV[0], NW_GV[-1])], -1))


def yard_z(V):
    """해발 of the yard south-west of the terrace (and the terrace's slab at its edge)"""
    k = np.clip((TERRACE[3] - np.asarray(V, float)) / (TERRACE[3] - YARD_V), 0.0, 1.0)
    return TERRACE_Z - 0.05 + (YARD_Z - TERRACE_Z + 0.05) * k


def grade(Hn, X, Y, FIXED, keep, fill, step=5.0):
    """The ground round the hall as the scans have it (the tables above), over the nodes no hall's foot (keep) or
    earlier rule (FIXED) holds, eased out RING m round them (fill: harmonic_fill).  Then the nodes go down under what
    a deck will cover (decks, later, once the ground is all laid): those of the cells the retaining wall (u = TERRACE[2],
    from the hall to WALL_END) crosses, on the slab's and the yard's side, to the level east of the wall, so that the
    wall's foot stands on level ground; and those of the cells the rear porch's flight and floor (PIT) lie in, under its
    floor.  Returns the nodes set (to be FIXED), the ground before they went down (for the decks), the nodes taken
    down for the wall and for the flight, and a summary."""
    H0 = Hn.copy()
    T = datum.tilt(X, Y)
    U, V = uv(X, Y)
    z = np.full(X.shape, np.nan)
    back = (U >= -8.0) & (U <= 88.0) & (V >= W / 2) & (V <= 35.0)
    z[back] = np.interp(U[back], BACK_U, BACK_Z) + BACK_FOOT * np.clip((22.0 - V[back]) / (22.0 - W), 0.0, 1.0)
    a_, b_, d_ = REAR_BAYS[1]                            # (#233: the south-east rear porch's floor stands on the lane's level)
    p2 = back & (U > a_ - 5.0) & (U < b_ + 5.0) & (V < W + d_ + REAR_PORCH[1] + 1.5)
    z[p2] = np.interp(U[p2], BACK_U, BACK_Z)
    nwf = (U >= -8.0) & (U < TERRACE[0]) & (V >= -8.0) & (V < W / 2)
    z[nwf] = np.interp(U[nwf], NWF_U, NWF_Z)
    # (the north-west car park, and off the hall's north-west end round the plant yard down to the lane: NW_GZ)
    nw = ((U >= NW_GU[0]) & (U < -8.0) & (V >= -8.0) & (V <= 35.0)) | ((U >= -8.0) & (U < 0.0) & (V >= 0.0) & (V < 22.0))
    z[nw] = nw_z(U[nw], V[nw])
    ter = (U >= TERRACE[0]) & (U < TERRACE[2]) & (V >= YARD_V - 3.0) & (V < W / 2)
    z[ter] = yard_z(V[ter])
    lot = (U >= TERRACE[2]) & (U <= LOT[1]) & (V >= -24.0) & (V < W / 2)
    z[lot] = LOT_Z
    isle = (U >= TERRACE[2]) & (U < 45.5) & (V >= -30.0) & (V < BANK_V[0])    # (east of the wall past the lot: the island)
    z[isle] = np.interp(V[isle], BANK_V[::-1], BANK_Z[::-1])
    se = (U > L) & (U <= L + 12.5) & (V >= 0.5) & (V < W / 2)
    z[se] = np.interp(U[se] - L, SE_D, SE_Z)
    took = ~np.isnan(z) & ~keep & ~FIXED
    Hn[took] = (z + T)[took]
    ring = shapely.contains_xy(REGION.buffer(RING), X, Y) & ~took & ~keep & ~FIXED
    if ring.any():
        fill(ring)
    Hpre = Hn.copy()
    # under the decks: the wall's cells (slab's and yard's side) to the level east of it; the porch flight's cells under it
    low = np.zeros(X.shape, bool)
    zlow = np.where(V >= BANK_V[0], LOT_Z, np.interp(V, BANK_V[::-1], BANK_Z[::-1]))
    pit = np.zeros(X.shape, bool)
    pit_poly = pit_outline().buffer(0.3)
    nj, ni = X.shape
    for j in range(nj - 1):
        for i in range(ni - 1):
            cu, cv = U[j:j + 2, i:i + 2], V[j:j + 2, i:i + 2]
            if cu.max() < -60 or cu.min() > 110 or cv.max() < -45 or cv.min() > 60:
                continue
            if cu.min() < TERRACE[2] < cu.max() and cv.max() > WALL_END and cv.min() < 0.0:
                low[j:j + 2, i:i + 2] |= (cu < TERRACE[2]) & (cu >= TERRACE[0] + 5.0) & (cv < W / 2)
            cell = shapely.geometry.box(X[j, i], Y[j, i], X[j + 1, i + 1], Y[j + 1, i + 1])
            if cell.intersects(pit_poly):
                pit[j:j + 2, i:i + 2] = True
    low &= took
    pit &= took
    Hn[low] = (zlow + T)[low]
    Hn[pit] = (PIT['floor'] - 0.4 + T)[pit]
    d = Hn - H0
    return took | ring, Hpre, low, pit, dict(nodes=int(took.sum()), low=int(low.sum()), pit=int(pit.sum()), ring=int(ring.sum()),
                                          held=int((~np.isnan(z) & (keep | FIXED)).sum()),
                                          moved=(int((np.abs(d) > 0.05).sum()), round(float(d.min()), 2), round(float(d.max()), 2)))


def pit_outline():
    """the rear porch's flight and floor between the walls' outer faces, from the back wall out to the flight's head"""
    w0, w1 = PIT['walls']
    return rect(w0 - PIT['t'] / 2, w1 + PIT['t'] / 2, W, PIT['end_v'])


def deck_polys(gx, step, low_cells, pit_cells):
    """the decks' outlines (campus frame): over the cells whose nodes grade() took down, but not the flight's well, the
    hall, the terrace's slab (its own mesh) or the low side of the retaining wall"""
    cells = lambda cs: unary_union([shapely.geometry.box(gx[i], gx[j], gx[i] + step, gx[j] + step) for j, i in cs])
    yard = cells(low_cells).difference(rect(TERRACE[2], 200.0, WALL_END, 100.0)).difference(
        rect(TERRACE[0] - 0.3, TERRACE[2], TERRACE[3], 0.0)).difference(hall())
    core = unary_union([rect(0.0, L, 0.0, W), rect(REAR[0], REAR[1], W, REAR[3])] + [rect(a, b, W, W + d) for a, b, d in REAR_BAYS])
    back = cells(pit_cells).difference(pit_outline()).difference(core)
    return yard, back


def deck_z(x, y, pre):
    """해발 + tilt (the working datum) of a deck's top at (x, y): the yard by its table on the slab's side of the wall,
    elsewhere the ground as it was laid before the nodes went down (pre: a sampler of it)"""
    u, v = uv(x, y)
    if u < TERRACE[2] and WALL_END < v < TERRACE[3] + 0.01:
        return float(yard_z(v)) + float(datum.tilt(x, y))
    return pre(x, y)


def move_off(trees, shrubs, props):
    """Trees standing on the hall, its terrace, the walk, the car parks and the lane behind (#233: paved()), the wall on
    to the yard's end, the plant yard or the rear flight step aside, each in its place in the list (the
    web picks each tree's model by it), to the nearest ground beside them; those in the yard between the terrace and
    the road, which the photo of 2004 sees the front across, go sideways out of it (to the garden north-west of it, or
    past the retaining wall's line where the bank is).  Shrubs and props on the hall and the paved places go.  Returns
    how many shrubs and props went and the trees moved."""
    zone = unary_union([hall().buffer(1.5), TERRACE_POLY.buffer(0.8), WALK_POLY.buffer(0.5), LOT_POLY.buffer(0.3)] +
                       [p_.buffer(0.3) for p_ in paved()] + [WALL_EXT.buffer(0.8), PLANT_POLY.buffer(0.8), pit_outline().buffer(0.8)])
    block = zone.buffer(1.2)
    edge = unary_union([g.exterior for g in (block.geoms if hasattr(block, 'geoms') else [block])])
    yard = rect(TERRACE[0] - 0.3, TERRACE[2], -30.0, TERRACE[3])
    n0 = (len(shrubs), len(props))
    shrubs[:] = [s for s in shrubs if not zone.contains(Point(s[1], s[2]))]
    props[:] = [p for p in props if not zone.contains(Point(p[1], p[2]))]
    moved = []
    for t in trees:
        q, mv = Point(t[1], t[2]), False
        if zone.contains(q):
            q, mv = shapely.ops.nearest_points(edge, q)[0], True
        if yard.contains(q):
            u, v = uv(q.x, q.y)
            q = Point(xy(TERRACE[0] - 3.0 if u < (TERRACE[0] + TERRACE[2]) / 2 or v > -24.5 else TERRACE[2] + 2.5, float(v)))
            mv = True
        if mv:
            moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
            t[1], t[2] = round(q.x, 2), round(q.y, 2)
    return n0[0] - len(shrubs), n0[1] - len(props), moved


def heading(h):
    """a heading in the frame (degrees from +u towards +v) in the campus frame (radians from +x)"""
    return math.radians(ANG + h)


def parking():
    """The car parks round the hall for campus.json `parking` and their cars (#233): [(name, paint, stalls [(x, y, heading
    rad)], lines [[x0, y0, x1, y1]])] and [(x, y, heading rad, size, shade)]"""
    seg = lambda u0, v0, u1, v1: [round(c, 2) for c in (*xy(u0, v0), *xy(u1, v1))]
    lots = []
    # the car park before the south-east half: the two lined rows (the cars there and along its edge: FRONT_CARS)
    st, ln = [], []
    for (u0, p, n, va, vb), h in ((WALL_ROW, 90), (MID_ROW, -90)):
        for k in range(n + 1):
            ln.append(seg(u0 + p * k, va, u0 + p * k, vb))
        for vv in ((vb,) if h > 0 else (va, vb)):
            ln.append(seg(u0, vv, u0 + p * n, vv))
        st += [(*xy(u0 + p * (k + 0.5), (va + vb) / 2), heading(h)) for k in range(n)]
    lots.append(('한국어학당 앞', 'white', st, ln))
    # behind: the row along the lane, a stall for each car and the empty ones, lines between them
    us = sorted([u for u, _ in BACK_CARS] + list(BACK_EMPTY))
    st = [(*xy(u, (BACK_ROW[2] + BACK_ROW[3]) / 2), heading(90)) for u in us]
    ends = sorted({round(e, 2) for a, b in zip(us[:-1], us[1:]) if b - a < 3.2 for e in ((a + b) / 2,)} |
                  {round(u + s * 1.2, 2) for k, u in enumerate(us) for s in (-1, 1)
                   if not any(abs(u + s * 1.2 - (u + w) / 2) < 0.6 for w in us if w != u and abs(w - u) < 3.2)})
    ln = [seg(e, BACK_ROW[2], e, BACK_ROW[3]) for e in ends]
    lots.append(('한국어학당 뒤', 'white', st, ln))
    # the north-west car park: three rows, a line along each row's aisle side
    st, ln = [], []
    for ua, ub, v0, p, n in NW_ROWS:
        h = 180 if ub < ua else 0
        for k in range(n + 1):
            ln.append(seg(ua, v0 + p * k, ub, v0 + p * k))
        ln.append(seg(ua, v0, ua, v0 + p * n))
        st += [(*xy((ua + ub) / 2, v0 + p * (k + 0.5)), heading(h)) for k in range(n)]
    lots.append(('한국어학당 북서쪽', 'white', st, ln))
    cars = [(*xy(u, v), heading(h), s, w) for u, v, h, s, w in FRONT_CARS + CURVE_CARS + NW_CARS]
    cars += [(*xy(u, BACK_V), heading(90), 'm', w) for u, w in BACK_CARS]
    return lots, cars


def paved():
    """(#233) the asphalt the scans have round the hall past the car park before it: its south and south-east edge, the
    lane and the row behind, the north-west car park"""
    return [LOT_S.difference(rect(TERRACE[2], 45.5, -40.0, BANK_V[0])), BACK_POLY, NW_POLY]


def plan_round():
    """what blender/landmarks.py kli draws round the hall (#233): the retaining wall on to the yard's end, the rear
    porches' floors and the north-west one's flight down from the lane, the plant yard.  Heights over the entrance floor"""
    return dict(wall_end=WALL_END, yard_v=YARD_V, yard_z=round(YARD_Z - FLOOR, 3), bank_v=list(BANK_V),
                bank_z=[round(z - FLOOR, 3) for z in BANK_Z],
                rear_floor=[round(z - FLOOR, 3) for z in REAR_FLOOR],
                pit=dict(walls=list(PIT['walls']), t=PIT['t'], top_v=PIT['top_v'], top_z=round(PIT['top_z'] - FLOOR, 3),
                         floor=round(PIT['floor'] - FLOOR, 3), tread=PIT['tread'], end_v=PIT['end_v'],
                         wall_top=round(53.35 - FLOOR, 3)),
                plant=dict(yard=list(PLANT['yard']), wall=PLANT['wall'], towers=[list(t) for t in PLANT['towers']],
                           top=round(PLANT['top'] - FLOOR, 3), floor=round(PLANT['floor'] - FLOOR, 3)))


def guards():
    """(#233) invisible walking guards (campus.json colliders) along the coping of the retaining wall past the slab and
    on the rear flight's two walls: drops of 3 m that no photo shows a rail on (tools/walkguard97.py's rule); the walled
    plant yard"""
    w0, w1 = PIT['walls']
    rs = [rect(TERRACE[2] - 0.3, TERRACE[2], WALL_END, TERRACE[3])] + \
         [rect(w - PIT['t'] / 2, w + PIT['t'] / 2, W, PIT['end_v'] - 0.6) for w in (w0, w1)] + [PLANT_POLY]
    return [[[round(x, 3), round(y, 3)] for x, y in list(r.exterior.coords)[:-1]] for r in rs]
