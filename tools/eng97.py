"""제1공학관 안뜰과 그 남쪽 땅, 공학원 공사장의 땅을 1997년 7월 항공사진 원본 스캔의 높이로 (#189 · #151).
tools/build_campus.py 가 부른다. 근거와 잰 값은 reference/고증/3.8_제1공학관.md 「안뜰과 남쪽 땅」 · 4.4.

    eng97.grade(Hn, X, Y, FIXED, halls, fill, site_o, site_rot, pit, slab)   # 땅 (저장 바로 앞, 심기가 끝난 뒤)
    eng97.deck_parts(G, gx, step)        # 서쪽 옹벽 윗단의 데크가 덮을 칸과 그 평면
    eng97.walls(low, up)                 # 옹벽의 줄 [x, y, 발치, 윗단 땅]
    eng97.move_off(trees, shrubs, props) # 안뜰 건물 자리의 나무는 1997년에 나무가 있던 곳으로(목록 제자리), 관목 · 소품은 뺌

What the scans (26/16 · 26/15 · 27/17, each pair by itself, 1.5 - 3 m windows) and the 2006 survey have:
- The three wings stand on one nearly level platform: the court between them 26.4 m (north alley) to 25.7 m (south
  alley and the west lot's south end; the survey's spot (-197.7, -242.5) 26.0 m), the lane west of the south wing and
  the yard between its two arms 25.6 - 25.9 m, the garden south-east of it 26.0 - 26.6 m, the service road south of
  it 25.7 m, climbing west of the wings to 29.3 m.  The game's ground climbed west across it from 27 m to 30.5 m.
- The "lawn in a bright kerb" in the court (#151) is a one-storey hall's flat roof: its parapet 32.0 m (north, south
  and west edges in three frames within 0.15 m on that plane, 1.3 - 5 m apart on the ground's), the roof 31.6 m, a
  raised strip along its middle 33.2 m, a small porch on its north side; the Kakao skyview of 2008 and 2010 has the
  same roof.  HALL_UV: its outline on the parapet's plane.
- West of the lot a retaining wall, its bright coping at 32.0 m (three frames within 0.15 m), the ground behind it
  30.3 - 30.9 m (제3공학관's terrace): the wall's face 5 - 6 m over the lot.  The 5 m grid cannot hold it: the nodes
  just behind it go down to the lot's level and a deck carries the upper ground to the wall (deck_parts; drawn with
  the wall by blender/landmarks.py eng_hall).
- 공학원's building site: its ground 26.2 - 26.7 m all across (the row along its north hoarding, the slab on its west
  side), the deck in the pit 22.7 - 23.5 m; the game had the site climbing west to 30.5 m and the pit at 26.5 m.

All heights here are the game's (게임 기준 = 해발 + T, tools/aerial97.py survey_dz); CTRL is the one table of absolute
heights, each with its place.  Nothing here draws from build_campus.py's `rng`.
"""
import math

import numpy as np
import shapely
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from scipy.ndimage import binary_dilation
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

# the wings' frame: o, u east-south-east along the wings, v north-north-east
O, ANG = (-163.0, -238.0), math.radians(-15.4)
_C, _S = math.cos(ANG), math.sin(ANG)
HALL_ID = 990070
HALL_UV = (-22.9, 31.3, -12.1, 14.9)        # the low hall in the court: u0, u1, v0, v1 (the parapet's outer edge)
HALL_TOP = 6.1                              # its parapet over the lowest ground at its foot (32.0 m over 25.85 - 26.35 m)
HALL_ROOF = -0.45                           # the roof's deck under the parapet's top
MONITOR_UV = (-18.3, 29.5, -1.0, 4.3, 1.2)  # the raised strip along the roof: u0, u1, v0, v1, its top over the parapet's
PORCH_UV = (0.2, 5.0, 14.9, 19.6, 3.2)      # the porch on the north side: u0, u1, v0, v1, height
# the retaining wall west of the lot (the coping's line; the upper ground west of it): two runs, (u, v) and the top
# over the upper ground (the coping 1.2 m over it where the scans have it; none along 제3공학관's own wall)
WALL_RUNS = [(1.2, [(-38.85, 30.0), (-38.9, -22.0)]),
             (0.05, [(-38.9, -22.0), (-40.6, -22.0), (-40.6, -41.3)]),
             (1.2, [(-40.6, -41.3), (-40.9, -62.0)])]
WALL_UP = 8.0                               # (how far behind the wall a node may be pulled down)
SOUTH_WING, SITE_DROP = 1451926787, 3.0     # (the south wing; the pit under the site's ground)
BOX = Polygon([(-330, -420), (-90, -420), (-90, -180), (-330, -180)])
# The 1997 ground (x, y, z 게임 기준): the court's alleys and the west lot, the lane west of the south wing and the yard
# between its arms, the garden south-east of it, the service road south of the wings (west to east), the site's north
# row and its ground
CTRL = [
    (-190.3, -201.4, 26.45), (-184.5, -203.0, 26.45), (-192.9, -211.1, 26.30), (-182.3, -214.0, 26.30), (-167.9, -218.0, 26.35),
    (-148.6, -223.3, 26.35), (-126.4, -229.4, 26.30), (-196.1, -222.7, 26.10), (-185.5, -225.6, 26.10), (-131.2, -246.8, 26.20),
    (-201.3, -241.6, 25.85), (-190.7, -244.5, 25.80), (-202.5, -245.8, 25.75), (-182.2, -251.4, 25.80), (-158.1, -258.0, 25.90),
    (-136.0, -264.1, 26.10), (-205.7, -257.4, 25.70), (-211.0, -276.6, 25.65), (-213.9, -287.2, 25.75), (-178.8, -280.3, 25.90),
    (-182.3, -292.9, 25.75), (-134.0, -283.3, 26.55), (-125.4, -289.8, 26.50), (-137.7, -296.8, 26.40), (-148.9, -300.0, 26.30),
    (-130.2, -307.2, 26.00), (-208.7, -290.8, 25.80), (-179.7, -298.7, 25.75), (-155.6, -305.4, 25.90), (-131.5, -312.0, 25.90),
    (-266.4, -282.1, 29.40), (-258.7, -284.2, 29.30), (-243.3, -288.5, 28.50), (-235.6, -290.6, 28.20), (-224.0, -293.8, 27.40),
    (-220.2, -294.9, 27.30), (-216.3, -295.9, 26.80), (-212.4, -297.0, 26.30), (-200.9, -300.2, 26.00), (-181.6, -305.5, 25.75),
    (-162.3, -310.8, 25.70), (-143.0, -316.1, 25.70), (-127.6, -320.4, 25.90), (-281.1, -292.2, 26.70), (-257.7, -297.6, 26.50),
    (-226.5, -304.8, 26.50), (-203.1, -310.2, 26.20), (-179.7, -315.6, 26.40), (-156.3, -321.0, 26.20), (-144.6, -323.6, 25.70),
    (-291.0, -335.0, 26.50), (-259.8, -342.2, 26.40), (-213.0, -353.0, 26.30), (-166.2, -363.8, 26.20), (-298.6, -368.2, 26.50),
    (-267.4, -375.4, 26.40), (-220.7, -386.2, 26.30), (-173.9, -397.0, 26.20),
]
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
    """the wall's line: u of the lot's west edge at v"""
    return np.where(np.asarray(v) > -22.0, -38.9, -40.75)


def surface():
    """the 1997 ground: CTRL's triangles, the nearest point's height outside them"""
    p = np.array(CTRL)
    lin, near = LinearNDInterpolator(p[:, :2], p[:, 2]), NearestNDInterpolator(p[:, :2], p[:, 2])

    def f(x, y):
        z = lin(x, y)
        return np.where(np.isnan(z), near(x, y), z)
    return f


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
    lv = {}
    for key, (u0, u1, v0, v1), dz in (('pit', pit, -SITE_DROP), ('slab', slab, 0.0)):
        m = (US >= u0) & (US <= u1) & (VS >= v0) & (VS <= v1)
        lv[key] = round(float(np.median(S[m])) + dz, 2)
        Hn[m] = lv[key]
        zone |= m
    # behind the wall: the upper nodes of every cell the lot reaches go down to the lot's level
    up = (U <= _west(V)) & (U > _west(V) - WALL_UP) & (V > -62.0) & (V < 30.0)
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
    keep = shapely.contains_xy(hp, X, Y) | FIXED | ((U <= _west(V)) & (V > -64.0) & (V < 36.0))
    keep |= (VS < -2.0) & (US > -100.0) & (US < 110.0)          # (성산로's side of the site's south hoarding: gate_town's)
    ring = binary_dilation(zone, iterations=3) & ~zone & ~pulled & ~keep
    if ring.any():
        fill(ring)
    FIXED[zone | pulled] = True
    d = Hn - H0
    return dict(H0=H0, zone=zone, pulled=pulled, pit=lv['pit'], slab=lv['slab'], nodes=int((np.abs(d) > 0.05).sum()),
                most=float(d.min()), ring=int(ring.sum()), n_pulled=int(pulled.sum()))


def upper_poly():
    """the ground behind the wall (the deck's side of the line)"""
    return poly([(-38.85, 30.0), (-38.9, -22.0), (-40.6, -22.0), (-40.6, -41.3), (-40.9, -62.0), (-60.0, -62.0), (-60.0, 30.0)])


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
    for top, pts in WALL_RUNS:
        ls = LineString([xy(u, v) for u, v in pts])
        n = max(1, int(round(ls.length)))
        row = []
        for k in range(n + 1):
            q = ls.interpolate(k / n, normalized=True)
            u_, v_ = uv(q.x, q.y)
            e, w = xy(float(u_) + 0.8, float(v_)), xy(float(u_) - 0.8, float(v_))
            row.append([round(q.x, 2), round(q.y, 2), round(float(low(*e)) - 0.5, 2), round(float(up(*w)), 2)])
        out.append([top, row])
    return out


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
