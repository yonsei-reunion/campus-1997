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
BACK_U = (-0.1, 9.9, 19.9, 29.9, 39.9, 49.9, 59.9, 69.9, 79.9)                        # the lane behind (v 22 .. 35)
BACK_Z = (54.4, 53.5, 52.6, 51.6, 50.6, 50.0, 49.1, 48.25, 47.3)
BACK_FOOT = 0.8                    # the planted strip under the back wall over the lane's level
SE_D, SE_Z = (0.0, 6.5, 10.5), (50.5, 49.5, 48.6)                                      # the yard at the south-east end, by distance
RING = 15.0
HALL_PAD = 3.0


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
LOT_POLY = rect(*LOT[:2], *LOT[2:]).difference(rect(TERRACE[2], 45.5, -24.0, -14.5))
# the walk from the terrace on to the road south-west of it (the scans: a pale strip on the porch's axis)
WALK_POLY = rect(UC - 5.0, UC + 5.0, -30.0, TERRACE[3] + 0.2)
REGION = unary_union([rect(-8.0, 88.0, W / 2, 35.0), rect(-8.0, 41.0, -8.0, W / 2), rect(TERRACE[0], 41.0, YARD_V, 0.0),
                      rect(41.0, LOT[1], -24.0, W / 2), rect(L, L + 12.5, 0.5, W)])


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


def grade(Hn, X, Y, FIXED, keep, fill, step=5.0):
    """The ground round the hall as the scans have it (the tables above), over the nodes no hall's foot (keep) or
    earlier rule (FIXED) holds, eased out RING m round them (fill: harmonic_fill).  Under the terrace's slab the nodes
    of the cells its retaining wall crosses go down to the car park, so that the wall's foot stands on level ground.
    Returns the nodes set (to be FIXED) and a summary."""
    H0 = Hn.copy()
    T = datum.tilt(X, Y)
    U, V = uv(X, Y)
    z = np.full(X.shape, np.nan)
    back = (U >= -8.0) & (U <= 88.0) & (V >= W / 2) & (V <= 35.0)
    z[back] = np.interp(U[back], BACK_U, BACK_Z) + BACK_FOOT * np.clip((22.0 - V[back]) / (22.0 - W), 0.0, 1.0)
    nwf = (U >= -8.0) & (U < TERRACE[0]) & (V >= -8.0) & (V < W / 2)
    z[nwf] = np.interp(U[nwf], NWF_U, NWF_Z)
    end = nwf & (U < 0.0) & (V > 0.0)                    # (round the north-west end, down to the back's level)
    zb = np.interp(U[end], BACK_U, BACK_Z) + BACK_FOOT
    z[end] = z[end] + (zb - z[end]) * np.clip(V[end] / W, 0.0, 1.0)
    ter = (U >= TERRACE[0]) & (U < TERRACE[2]) & (V >= YARD_V) & (V < W / 2)
    k = np.clip((TERRACE[3] - V[ter]) / (TERRACE[3] - YARD_V), 0.0, 1.0)
    z[ter] = TERRACE_Z - 0.05 + (YARD_Z - TERRACE_Z + 0.05) * k
    lot = (U >= TERRACE[2]) & (U <= LOT[1]) & (V >= -24.0) & (V < W / 2)
    z[lot] = LOT_Z
    se = (U > L) & (U <= L + 12.5) & (V >= 0.5) & (V < W / 2)
    z[se] = np.interp(U[se] - L, SE_D, SE_Z)
    # under the slab: the nodes of the cells the retaining wall (u = TERRACE[2], v from the slab's outer edge to the
    # hall) runs through, on the slab's side, at the car park's level
    low = np.zeros(X.shape, bool)
    jj, ii = np.nonzero(ter)
    for j in range(jj.min() - 1, jj.max() + 1):
        for i in range(ii.min() - 1, ii.max() + 1):
            cu, cv = U[j:j + 2, i:i + 2], V[j:j + 2, i:i + 2]
            if cu.min() < TERRACE[2] < cu.max() and cv.max() > TERRACE[3] and cv.min() < 0.0:
                # (not within 3 m of the slab's open outer edge: the yard beyond it stays level with it but at its
                # south corner, where the bank between the yard and the car park comes round the wall's end)
                m = (cu < TERRACE[2]) & (cu >= TERRACE[0] + 5.0) & (cv > TERRACE[3] + 3.0) & (cv < W / 2)
                low[j:j + 2, i:i + 2] |= m
    low &= ter
    z[low] = LOT_Z
    took = ~np.isnan(z) & ~keep & ~FIXED
    Hn[took] = (z + T)[took]
    ring = shapely.contains_xy(REGION.buffer(RING), X, Y) & ~took & ~keep & ~FIXED
    if ring.any():
        fill(ring)
    d = Hn - H0
    return took | ring, dict(nodes=int(took.sum()), low=int(low.sum()), ring=int(ring.sum()), held=int((~np.isnan(z) & (keep | FIXED)).sum()),
                             moved=(int((np.abs(d) > 0.05).sum()), round(float(d.min()), 2), round(float(d.max()), 2)))


def move_off(trees, shrubs, props):
    """Trees standing on the hall, its terrace, the walk or the car park step aside, each in its place in the list (the
    web picks each tree's model by it), to the nearest ground beside them; those in the yard between the terrace and
    the road, which the photo of 2004 sees the front across, go sideways out of it (to the garden north-west of it, or
    past the retaining wall's line where the bank is).  Shrubs and props on the hall and the paved places go.  Returns
    how many shrubs and props went and the trees moved."""
    zone = unary_union([hall().buffer(1.5), TERRACE_POLY.buffer(0.8), WALK_POLY.buffer(0.5), LOT_POLY.buffer(0.3)])
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
