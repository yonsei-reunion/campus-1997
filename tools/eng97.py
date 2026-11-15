"""제1공학관 안뜰과 그 남쪽 땅, 공학원 공사장의 땅을 1997년 7월 항공사진 원본 스캔의 높이로 (#189 · #151).
tools/build_campus.py 가 부른다. 근거와 잰 값은 reference/고증/3.8_제1공학관.md 「안뜰과 남쪽 땅」 · 4.4.

    eng97.north_grade(Hn, X, Y, FIXED, halls, fill)   # 제2공학관 북쪽 길 · 공학관 사이 윗단 (grade 바로 앞)
    eng97.grade(Hn, X, Y, FIXED, halls, fill, site_o, site_rot, pit, slab)   # 땅 (저장 바로 앞, 심기가 끝난 뒤)
    eng97.deck_parts(G, gx, step)        # 서쪽 옹벽 윗단의 데크가 덮을 칸과 그 평면
    eng97.walls(low, up)                 # 옹벽의 줄 [x, y, 발치, 윗단 땅]
    eng97.nb_outline(fp)                 # 제1공학관 북쪽 동의 1997년 외곽(서쪽 날개의 서쪽 면 · 북쪽 끝, 가운데 날개의 북쪽 끝)
    eng97.north_paved()                  # 제2공학관 북쪽 길 · 공학관 사이 윗단 · 골목의 포장
    eng97.move_off(trees, shrubs, props) # 안뜰 건물 자리의 나무는 1997년에 나무가 있던 곳으로(목록 제자리), 관목 · 소품은 뺌

What the scans (26/16 · 26/15 · 27/17, each pair by itself, 1.5 - 3 m windows) and the 2006 survey have:
- The three wings stand on one nearly level platform: the court between them 27.9 m (north alley) to 27.2 m (south
  alley and the west lot's south end; the survey's spot (-197.7, -242.5) 26.0 m), the lane west of the south wing and
  the yard between its two arms 27.1 - 27.4 m, the garden south-east of it 27.5 - 28.1 m, the service road south of
  it 27.2 m, climbing west of the wings to 30.8 m.  The game's ground climbed west across it from 28 m to 32.0 m.
- The "lawn in a bright kerb" in the court (#151) is a one-storey hall's flat roof: its parapet 33.5 m (north, south
  and west edges in three frames within 0.15 m on that plane, 1.3 - 5 m apart on the ground's), the roof 33.1 m, a
  raised strip along its middle 34.7 m, a small porch on its north side; the Kakao skyview of 2008 and 2010 has the
  same roof.  HALL_UV: its outline on the parapet's plane.
- West of the lot a retaining wall, its bright coping at 33.5 m (three frames within 0.15 m), the ground behind it
  31.8 - 32.4 m (제3공학관's terrace): the wall's face 5 - 6 m over the lot.  The 5 m grid cannot hold it: the nodes
  just behind it go down to the lot's level and a deck carries the upper ground to the wall (deck_parts; drawn with
  the wall by blender/landmarks.py eng_hall).
- 공학원's building site: its ground 27.8 - 28.3 m all across (the row along its north hoarding, the slab on its west
  side), the deck in the pit 24.3 - 25.1 m; the game had the site climbing west to 32.1 m and the pit at 28.1 m.
- North of the lot the wall runs on (공학관 사이, between the north block and 제2공학관's upper ground) to v 72: its
  bright line at u -39.7 on the plane 33.2 m (26/16 · 26/15 within 0.05 m, v 33 - 60), a dark planted strip behind it,
  the lane under it level with the court's north alley and the yard (27.6 - 28.6 m), the upper ground behind it 32.0 m
  along the wall (v -21 .. 38), up a ramp to 34.1 m by v 50, where 제2공학관's north road meets it.  The road north of
  제2공학관 falls from 37.0 m (the 2006 · 2024 survey's spot at its west end, 37.15 · 37.18 m) to 34.1 m: the game had
  it and the gap's upper ground 1.4 - 2.7 m higher (the 2006 · 2024 35 m contours across it agree).  The north block's
  west wing ends 2.1 m east of OSM's face (u -28.6) and 2.3 m north of it (v 60.0; the middle wing v 60.4), where the
  cars parked along the lane and nose in to the north wall have it (four frames on the roof's plane, within 0.3 m).

All heights written here are above sea level (해발); CTRL is the one table of absolute heights, each taken up to
the working datum the ground is laid on at its own place (datum.up3: tools/datum.py).  Nothing here draws from build_campus.py's `rng`.
"""
import math

import numpy as np
import datum
import shapely
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from scipy.ndimage import binary_dilation
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import nearest_points, unary_union

# the wings' frame: o, u east-south-east along the wings, v north-north-east
O, ANG = (-163.0, -238.0), math.radians(-15.4)
_C, _S = math.cos(ANG), math.sin(ANG)
HALL_ID = 990070
HALL_UV = (-22.9, 31.3, -12.1, 14.9)        # the low hall in the court: u0, u1, v0, v1 (the parapet's outer edge)
HALL_TOP = 6.1                              # its parapet over the lowest ground at its foot (33.5 m over 27.32 - 27.82 m)
HALL_ROOF = -0.45                           # the roof's deck under the parapet's top
MONITOR_UV = (-18.3, 29.5, -1.0, 4.3, 1.2)  # the raised strip along the roof: u0, u1, v0, v1, its top over the parapet's
PORCH_UV = (0.2, 5.0, 14.9, 19.6, 3.2)      # the porch on the north side: u0, u1, v0, v1, height
# the retaining wall west of the lot (the coping's line; the upper ground west of it): two runs, (u, v) and the top
# over the upper ground (the coping 1.2 m over it where the scans have it; none along 제3공학관's own wall)
WALL_RUNS = [(1.2, [(-38.85, 30.0), (-38.9, -22.0)]),
             (0.05, [(-38.9, -22.0), (-40.6, -22.0), (-40.6, -41.3)]),
             (1.2, [(-40.6, -41.3), (-40.9, -62.0)]),
             # (공학관 사이: the wall on north of the lot to the yard; its top in the scans is about level with the planted
             # strip behind it, the parapet is the game's, as the lot's; at its north end a return west along the deck's
             # edge, its low side north: (du, dv) of the low side)
             (1.2, [(-39.7, 72.0), (-39.7, 31.0), (-38.85, 30.0)]),
             (1.2, [(-52.0, 72.0), (-39.7, 72.0)], (0.0, 0.8)),
             # (and at the deck's south end, over the service road south of the wings: 제3공학관's terrace edge)
             (1.2, [(-40.9, -62.0), (-52.0, -62.0)], (0.0, -0.8))]
WALL_UP = 8.0                               # (how far behind the wall a node may be pulled down)
GAP_N = 72.0                                # (the wall's north end, its return: the deck behind it ends there)
# the lane under it: from the court's north alley (v 30) to the yard (v 66; west_ground.LOT_Z there), 해발
LANE_V, LANE_Z = (30.0, 66.0), (27.9, 28.7)
# the north block's west wing in 1997 (its roof's edges on the roof's plane): the west face, the north ends
NB_ID, NB_WEST_U, NB_NORTH_V, NB_MID_NORTH_V = 1451926793, -28.6, 60.0, 60.4
# 제2공학관 북쪽 길 (the road north of 제2공학관, its two rows of cars, from the 체육관 junction at its west end to the gap):
# level across from the hall's north face to v 62, its height along u (해발): the scans' pair 26/16 · 26/15 on the
# aisle (v 47 - 56, 2 m windows, medians), the survey's spot at the west end
NROAD_V = (38.85, 62.0)
NROAD_U = [(-152.0, 37.0), (-140.0, 36.8), (-125.0, 36.7), (-110.0, 36.1), (-100.0, 36.0), (-95.0, 35.7), (-88.0, 35.1),
           (-80.0, 34.9), (-70.0, 34.6), (-62.0, 34.3), (-54.8, 34.1)]
# the gap's upper ground behind the wall (u -48.5 to the wall from v -22, the gap's width from v 40): along v, 해발;
# west of u -48.5 at its south end (the foot of 제2공학관's east face) no lower than GAP_FOOT
GAP_UP_V = [(-22.0, 32.3), (0.0, 32.2), (38.0, 32.1), (41.0, 32.7), (44.0, 33.5), (47.0, 33.8), (50.0, 34.0), (53.0, 34.1),
            (76.0, 34.1)]
GAP_W, GAP_FOOT = -54.8, 33.6
BYEOLDONG = 324328471                       # (별동연구동, north of the road: its floor on the road at its door)
SOUTH_WING, SITE_DROP = 1451926787, 3.0     # (the south wing; the pit under the site's ground)
BOX = Polygon([(-330, -420), (-90, -420), (-90, -180), (-330, -180)])
# The 1997 ground (x, y, z 해발): the court's alleys and the west lot, the lane west of the south wing and the yard
# between its arms, the garden south-east of it, the service road south of the wings (west to east), the site's north
# row and its ground
CTRL = datum.up3([
    (-190.3, -201.4, 27.89), (-184.5, -203.0, 27.86), (-192.9, -211.1, 27.78), (-182.3, -214.0, 27.73), (-167.9, -218.0, 27.72),
    (-148.6, -223.3, 27.63), (-126.4, -229.4, 27.48), (-196.1, -222.7, 27.62), (-185.5, -225.6, 27.58), (-131.2, -246.8, 27.44),
    (-201.3, -241.6, 27.45), (-190.7, -244.5, 27.35), (-202.5, -245.8, 27.36), (-182.2, -251.4, 27.32), (-158.1, -258.0, 27.31),
    (-136.0, -264.1, 27.41), (-205.7, -257.4, 27.36), (-211.0, -276.6, 27.39), (-213.9, -287.2, 27.53), (-178.8, -280.3, 27.48),
    (-182.3, -292.9, 27.38), (-134.0, -283.3, 27.9), (-125.4, -289.8, 27.82), (-137.7, -296.8, 27.8), (-148.9, -300.0, 27.77),
    (-130.2, -307.2, 27.39), (-208.7, -290.8, 27.56), (-179.7, -298.7, 27.38), (-155.6, -305.4, 27.42), (-131.5, -312.0, 27.31),
    (-266.4, -282.1, 31.44), (-258.7, -284.2, 31.3), (-243.3, -288.5, 30.43), (-235.6, -290.6, 30.1), (-224.0, -293.8, 29.25),
    (-220.2, -294.9, 29.13), (-216.3, -295.9, 28.61), (-212.4, -297.0, 28.09), (-200.9, -300.2, 27.74), (-181.6, -305.5, 27.4),
    (-162.3, -310.8, 27.27), (-143.0, -316.1, 27.18), (-127.6, -320.4, 27.31), (-281.1, -292.2, 28.84), (-257.7, -297.6, 28.53),
    (-226.5, -304.8, 28.39), (-203.1, -310.2, 27.98), (-179.7, -315.6, 28.07), (-156.3, -321.0, 27.76), (-144.6, -323.6, 27.21),
    (-291.0, -335.0, 28.8), (-259.8, -342.2, 28.55), (-213.0, -353.0, 28.24), (-166.2, -363.8, 27.92), (-298.6, -368.2, 28.92),
    (-267.4, -375.4, 28.67), (-220.7, -386.2, 28.36), (-173.9, -397.0, 28.04),
])
# where the trees of the court go (the scans' own trees: the clump in the lot's south-west corner, the garden south-east
# of the south wing), (u, v)
TREE_SPOTS = [(-33.0, -13.5), (-36.5, -18.5), (-31.5, -19.5), (33.0, -40.0), (39.0, -36.0), (46.0, -38.0), (40.0, -45.0),
              (48.0, -48.0), (35.0, -54.0)]


def xy(u, v):
    return O[0] + u * _C - v * _S, O[1] + u * _S + v * _C


def uv(x, y):
    dx, dy = np.asarray(x, float) - O[0], np.asarray(y, float) - O[1]
    return dx * _C + dy * _S, -dx * _S + dy * _C


def poly(pts):
    return Polygon([xy(u, v) for u, v in pts])


def hall_poly():
    u0, u1, v0, v1 = HALL_UV
    return poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def _west(v):
    """the wall's line: u of the lot's (and north of it the lane's) west edge at v"""
    v = np.asarray(v)
    return np.where(v > 30.5, -39.7, np.where(v > -22.0, -38.9, -40.75))


def surface():
    """the 1997 ground: CTRL's triangles, the nearest point's height outside them"""
    p = np.array(CTRL)
    lin, near = LinearNDInterpolator(p[:, :2], p[:, 2]), NearestNDInterpolator(p[:, :2], p[:, 2])

    def f(x, y):
        z = lin(x, y)
        return np.where(np.isnan(z), near(x, y), z)
    return f


def north_z(U, V):
    """the 1997 upper ground at (u, v) (해발): 제2공학관's north road west of GAP_W, the gap's upper ground east of it"""
    road = np.interp(U, *zip(*NROAD_U))
    gap = np.interp(V, *zip(*GAP_UP_V))
    gap = np.where((U < -48.5) & (V >= 21.0), np.maximum(gap, GAP_FOOT), gap)
    return np.where(U <= GAP_W, road, gap)


def north_zone(U, V, X, Y, byeoldong):
    """the nodes north_grade sets: the road band (not 별동연구동), the gap's upper ground behind the wall (from the hall's
    north face north to the return), the strip along the wall's back south to the lot's south end"""
    road = (U >= NROAD_U[0][0]) & (U <= GAP_W) & (V >= NROAD_V[0]) & (V <= NROAD_V[1])
    road &= ~shapely.contains_xy(byeoldong.buffer(0.5), X, Y)
    gap = (U > GAP_W) & (U <= _west(V)) & (V >= 21.0) & (V <= GAP_N)
    strip = (U > -48.5) & (U <= _west(V)) & (V >= -22.0) & (V < 21.0)
    return road | gap | strip


def north_grade(Hn, X, Y, FIXED, halls, fill, byeoldong):
    """제2공학관 북쪽 길 and the gap's upper ground on the 1997 heights (north_z), before grade: the road band and the
    upper ground behind the wall over FIXED (west_ground.eagle_yard's lane reached behind the wall's line), the ground
    round them 15 m smoothed (fill) into what stays: not the halls' feet, not what is FIXED, not the lot's side of the
    wall.  halls: [(id, outline)]; byeoldong: 별동연구동's outline.  Returns the nodes set and a summary"""
    H0 = Hn.copy()
    U, V = uv(X, Y)
    zone = north_zone(U, V, X, Y, byeoldong)
    Hn[zone] = (north_z(U, V) + datum.tilt(X, Y))[zone]
    # (별동연구동: its floor goes down with the road before its door, so its feet with it, no higher than that)
    bc = byeoldong.centroid
    feet = shapely.contains_xy(byeoldong.buffer(1.5), X, Y) & ~zone
    zd = float(north_z(*uv(bc.x, bc.y))) + float(datum.tilt(bc.x, bc.y))
    Hn[feet] = np.minimum(Hn[feet], zd)
    zone |= feet
    hp = unary_union([p.buffer(1.0) for _, p in halls])
    lot = (U > _west(V)) & (V > -64.0) & (V < GAP_N + 6.0)
    ring = binary_dilation(zone, iterations=3) & ~zone & ~FIXED & ~lot & ~shapely.contains_xy(hp, X, Y)
    ring &= V >= 21.0                   # (south of 제2공학관's face, between it and 제3공학관, as it is: the scans' 34.5 - 36 m)
    if ring.any():
        fill(ring)
    d = Hn - H0
    return zone | ring, dict(nodes=int((np.abs(d) > 0.05).sum()), most=round(float(d.min()), 2), zone=int(zone.sum()),
                             ring=int(ring.sum()), road=round(float(d[zone].mean()), 2))


def upper(h0):
    """the upper ground behind the wall for the deck and the wall's top: north_z where north_grade set it (the strip
    along the wall's back, the gap's), right up to the wall's line (the grid's cells across that line would ease it
    down to the lot's side), h0(x, y) elsewhere"""
    def f(x, y):
        u_, v_ = (float(c) for c in uv(x, y))
        w_ = float(_west(v_))
        if u_ <= w_ + 0.05 and ((-22.0 <= v_ < 21.0 and u_ > -48.5) or (21.0 <= v_ <= GAP_N and u_ > GAP_W)):
            k = min(1.0, max(0.0, (u_ - (w_ - 5.0)) / 2.5))          # (the grid's own within a cell of the wall, eased)
            return h0(x, y) + k * (float(north_z(u_, v_)) + float(datum.tilt(x, y)) - h0(x, y))
        return h0(x, y)
    return f


def nb_outline(fp):
    """the north block's 1997 outline from OSM's (fp, its vertices in OSM's order): the west wing's west face at
    NB_WEST_U, its north end at NB_NORTH_V, the middle wing's north end at NB_MID_NORTH_V"""
    out = []
    for x, y in fp:
        u_, v_ = (float(c) for c in uv(x, y))
        if abs(u_ + 30.7) < 0.5:
            u_ = NB_WEST_U
        if abs(v_ - 57.7) < 0.5 and u_ < 0.0:
            v_ = NB_NORTH_V
        elif abs(v_ - 58.0) < 0.5 and u_ > 0.0:
            v_ = NB_MID_NORTH_V
        out.append(tuple(round(c, 2) for c in xy(u_, v_)))
    return out


def north_paved():
    """the 1997 asphalt here (the scans' pale surface with cars on it): the road band north of 제2공학관 (not 별동연구동's
    outline), the gap's upper ground up to the planted strip behind the wall, the lane under the wall"""
    road = poly([(NROAD_U[0][0], 39.3), (GAP_W, 39.3), (GAP_W, NROAD_V[1]), (NROAD_U[0][0], NROAD_V[1])])
    gap = poly([(GAP_W, 38.85), (-42.3, 38.85), (-42.3, GAP_N), (GAP_W, GAP_N)])
    lane = poly([(-39.6, 30.0), (NB_WEST_U, 30.0), (NB_WEST_U, GAP_N), (-39.6, GAP_N)])
    return [road, gap, lane]


def grade(Hn, X, Y, FIXED, halls, fill, site_o, site_rot, pit, slab):
    """The platform, the service road south of it and the site on the 1997 ground; the pit SITE_DROP under the site's
    ground and the slab on it, level, as they were made; the nodes just behind the retaining wall down to the lot's
    level (the deck's); the ground round all of it smoothed (fill) into what stays.  halls: [(id, outline)];
    pit, slab: (u0, u1, v0, v1) in the site's frame.  Returns what the deck, the walls and the report ask."""
    H0 = Hn.copy()
    S = surface()(X, Y)
    U, V = uv(X, Y)
    c, s = math.cos(site_rot), math.sin(site_rot)
    US, VS = (X - site_o[0]) * c + (Y - site_o[1]) * s, -(X - site_o[0]) * s + (Y - site_o[1]) * c
    east = np.where(V > -30.6, 40.0, 50.0)
    top = np.where(U < -28.5, 30.0, 27.0)
    yard = (V >= -64.0) & (V < top) & (U > _west(V)) & (U < east)
    road = (V < -64.0) & (V >= -74.5) & (U >= -88.0) & (U <= 56.0)
    site = (US >= -80.5) & (US <= 54.0) & (VS >= 6.0) & (VS <= 90.0)
    zone = yard | road | site
    Hn[zone] = S[zone]
    # the lane north of the lot under the wall, between it and the north block, up to the yard; the block's nodes 3.5 m
    # in from its west face with it, so that the row of cars along the face stands level (its floor stays: a plinth)
    lane = (V >= LANE_V[0]) & (V <= GAP_N) & (U > _west(V)) & (U < NB_WEST_U + 3.5)
    Hn[lane] = (np.interp(V, LANE_V, LANE_Z) + datum.tilt(X, Y))[lane]
    zone |= lane
    lv = {}
    for key, (u0, u1, v0, v1), dz in (('pit', pit, -SITE_DROP), ('slab', slab, 0.0)):
        m = (US >= u0) & (US <= u1) & (VS >= v0) & (VS <= v1)
        lv[key] = round(float(np.median(S[m])) + dz, 2)
        Hn[m] = lv[key]
        zone |= m
    # behind the wall: the upper nodes of every cell the lot reaches go down to the lot's level
    up = (U <= _west(V)) & (U > _west(V) - WALL_UP) & (V > -62.0) & (V < GAP_N)
    cell = zone[:-1, :-1] | zone[:-1, 1:] | zone[1:, :-1] | zone[1:, 1:]            # (cells with a node of the zone)
    touch = np.zeros(zone.shape, bool)
    touch[:-1, :-1] |= cell
    touch[:-1, 1:] |= cell
    touch[1:, :-1] |= cell
    touch[1:, 1:] |= cell
    pulled = up & touch & ~zone
    Hn[pulled] = S[pulled]
    # the ring: 15 m round the zone, but not the upper ground behind the wall, the halls' feet or what is fixed
    hp = unary_union([p.buffer(1.0) for _, p in halls])
    keep = shapely.contains_xy(hp, X, Y) | FIXED | ((U <= _west(V)) & (V > -64.0) & (V < GAP_N + 6.0))
    keep |= (VS < -2.0) & (US > -100.0) & (US < 110.0)          # (성산로's side of the site's south hoarding: gate_town's)
    ring = binary_dilation(zone, iterations=3) & ~zone & ~pulled & ~keep
    if ring.any():
        fill(ring)
    FIXED[zone | pulled] = True
    d = Hn - H0
    return dict(H0=H0, zone=zone, pulled=pulled, pit=lv['pit'], slab=lv['slab'], nodes=int((np.abs(d) > 0.05).sum()),
                most=float(d.min()), ring=int(ring.sum()), n_pulled=int(pulled.sum()))


def upper_poly():
    """the ground behind the wall (the deck's side of the line), north to the return at GAP_N"""
    return poly([(-39.7, GAP_N), (-39.7, 31.0), (-38.85, 30.0), (-38.9, -22.0), (-40.6, -22.0), (-40.6, -41.3), (-40.9, -62.0),
                 (-60.0, -62.0), (-60.0, GAP_N)])


def deck_parts(G, gx, step):
    """the cells with a node pulled down behind the wall, and the part of them behind the wall: build_campus.py's
    dwb_deck lays the upper ground over it"""
    jj, ii = np.nonzero(G['pulled'])
    n = len(gx) - 1
    cells = {(j + a, i + b) for j, i in zip(jj, ii) for a in (-1, 0) for b in (-1, 0) if 0 <= j + a < n and 0 <= i + b < n}
    area = unary_union([box(gx[i], gx[j], gx[i] + step, gx[j] + step) for j, i in cells]).intersection(upper_poly())
    area = unary_union([g for g in getattr(area, 'geoms', [area]) if g.geom_type == 'Polygon' and g.area > 0.05])
    return cells, area


def walls(low, up):
    """the retaining wall's runs for blender/landmarks.py _wall_run: [top over the upper ground, [[x, y, foot, the upper
    ground], ...]] every metre; low(x, y), up(x, y): the ground as saved, the ground as it was"""
    out = []
    for run in WALL_RUNS:
        top, pts = run[:2]
        du, dv = run[2] if len(run) > 2 else (0.8, 0.0)
        ls = LineString([xy(u, v) for u, v in pts])
        n = max(1, int(round(ls.length)))
        row = []
        for k in range(n + 1):
            q = ls.interpolate(k / n, normalized=True)
            u_, v_ = uv(q.x, q.y)
            e, w = xy(float(u_) + du, float(v_) + dv), xy(float(u_) - du, float(v_) - dv)
            row.append([round(q.x, 2), round(q.y, 2), round(float(low(*e)) - 0.5, 2), round(float(up(*w)), 2)])
        out.append([top, row])
    return out


def move_off_north(trees, shrubs, props):
    """what the planting put on north_paved: trees step aside to the nearest edge (in their places in the list), shrubs
    and props go.  Returns (trees moved, shrubs out, props out)"""
    zone = unary_union(north_paved()).buffer(0.6)
    n0 = (len(shrubs), len(props))
    shrubs[:] = [s for s in shrubs if not zone.contains(Point(s[1], s[2]))]
    props[:] = [p for p in props if not zone.contains(Point(p[1], p[2]))]
    edge = zone.buffer(1.0).boundary
    moved = []
    for t in trees:
        if zone.contains(Point(t[1], t[2])):
            q = nearest_points(edge, Point(t[1], t[2]))[0]
            moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
            t[1], t[2] = round(q.x, 2), round(q.y, 2)
    return moved, n0[0] - len(shrubs), n0[1] - len(props)


def move_off(trees, shrubs, props):
    """what stood where the hall is: the trees go, each in its place in the list, to where the scans have trees
    (TREE_SPOTS, the nearest free one); shrubs and props go.  A tree in the lot's drive by the hall's corner too."""
    zone = hall_poly().buffer(3.0)
    spots = [xy(u, v) for u, v in TREE_SPOTS]
    moved = []
    for t in trees:
        if zone.contains(Point(t[1], t[2])) and spots:
            q = min(spots, key=lambda q_: math.hypot(q_[0] - t[1], q_[1] - t[2]))
            spots.remove(q)
            moved.append((t[0], t[1], t[2]))
            t[1], t[2] = round(q[0], 2), round(q[1], 2)
    n0 = (len(shrubs), len(props))
    hz = hall_poly().buffer(1.5)
    shrubs[:] = [s for s in shrubs if not hz.contains(Point(s[1], s[2]))]
    props[:] = [p for p in props if not hz.contains(Point(p[1], p[2]))]
    return moved, n0[0] - len(shrubs), n0[1] - len(props)
