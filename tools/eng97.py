"""제1공학관 안뜰과 그 남쪽 땅, 공학원 공사장의 땅을 1997년 7월 항공사진 원본 스캔의 높이로 (#189 · #151).
tools/build_campus.py 가 부른다. 근거와 잰 값은 reference/고증/3.8_제1공학관.md 「안뜰과 남쪽 땅」 · 4.4.

    eng97.north_grade(Hn, X, Y, FIXED, halls, fill)   # 제2공학관 북쪽 길 · 공학관 사이 윗단 (grade 바로 앞)
    eng97.grade(Hn, X, Y, FIXED, halls, fill, site_o, site_rot, pit, slab)   # 땅 (저장 바로 앞, 심기가 끝난 뒤)
    eng97.deck_parts(G, gx, step)        # 서쪽 옹벽 윗단의 데크가 덮을 칸과 그 평면
    eng97.walls(low, up)                 # 옹벽의 줄 [x, y, 발치, 윗단 땅]
    eng97.outline(eng97.NORTH_1997)      # 제1공학관 세 동(EAST_1997 · SOUTH_1997 · NORTH_1997)의 1997년 외곽, 게임 좌표로
    eng97.north_paved()                  # 제2공학관 북쪽 길 · 공학관 사이 윗단 · 골목의 포장
    eng97.move_off(trees, shrubs, props) # 안뜰 건물 자리의 나무는 1997년에 나무가 있던 곳으로(목록 제자리), 관목 · 소품은 뺌
    eng97.south_paint()                  # 제3공학관 남쪽: 걷어 낼 것, 맨땅, 테라스의 포장 (3.8 「제3공학관 남쪽」)
    eng97.garden_paint()                 # 남쪽 동 남동쪽 정원: 잔디, 대각선 길
    eng97.south_walks(paths)             # 그 자리의 뒷날 보행로 · 진입로를 빼고 정원의 대각선 길을 넣음
    eng97.move_off_south(trees, shrubs, props)   # 제3공학관 남쪽의 나무는 정원의 나무 자리로(목록 제자리), 관목 · 소품은 뺌
    eng97.s3_floor(base)                 # 제3공학관: 테라스에서 지붕까지 여섯 층 (levels, fh)

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
- The three blocks (#201): the 2006 survey's outline fits every roof edge of the 1997 scans once moved u +1.47,
  v -0.78 (the survey's frame against the scans' block here); the faces read on their own above agree with it within
  0.5 m.  EAST_1997 · SOUTH_1997 · NORTH_1997 are that outline.

- 제3공학관 남쪽 (the third round; 26/16 · 26/15 alone reach it): the hall's roof deck 54.5 m (two rows of points along
  it), where the game's five storeys ended at 52.4 m.  South of it a terrace, its tile-paved east part (u -65.5 .. -43,
  v -61.3 .. -42.5) at 31.0 m; a flight 16 m wide (u -92 .. -76) climbs from the yard at v -64.5 to the hall's door
  under a canopy (32.8 m at v -61, 35.3 m at v -55), stepped planters either side, a raised lawn west of it (its kerb
  32.5 - 32.8 m), sunk courts between: only the tile deck's level and the ground round it go into the game.  The yard
  west and south of the hall and the track along it are level at 31.3 - 31.5 m west of u -78 (the game 32.5 - 33.0 m),
  the track falling east to 28.1 m at u -30; bare earth all of it, no tree.  Along 공학원's north hoarding a bench
  3 - 4 m wide at 28.3 - 28.6 m, the yard's edge over it a retaining wall with a bright cap at the yard's own height
  (31.0 - 31.3 m on the cap's plane, the two frames within 0.05 m; v -81.9 .. -82.6 west of u -81, v -77 .. -79.6 east
  of it): 2.9 m at its west end, where a ramp comes down to the bench, nothing by u -40.
- The garden south-east of the south wing (26/16 · 27/17): a lawn u 26.8 .. 51.2, v -58.3 .. -32.6 with trees, one walk
  2 m wide across it from its north-east corner to its south-west one.
- The north block's west court (between its west and middle wings): level with the yard's south road and the lane
  (27.5 - 27.8 m, nine points; sheds and stores on it), where the game had a lawn climbing to 33 m.

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
NORTH_END_U, NORTH_BANK_V = -43.5, 75.2     # (the coping's return; the bank's deck north to the grid's cells' edge)
NORTH_PATH = [(-47.0, 73.6), (-44.0, 73.4), (-41.0, 74.8), (-38.5, 76.6), (-36.0, 78.2)]     # (the footpath, u v; width 1.4)
# The wall's details (reference/고증/3.8 「서쪽 옹벽의 세부」, 2026-11-17), on the coping's plane of the 1997 scans 26/16 ·
# 27/17 and the leaf-off 1996 26/16 (33.2 m), and on the terrace's of 26/16 · 26/15 · 1998 26/16 (31.4 m):
# - BAY: at v 0 the coping bows out east over v -2.1 .. 3.6, 1.55 - 2.0 m at its apex, the planted strip's ground inside
#   it (no flight): its middle v, half its chord, how far it bows out
# - PLANTER: south of 제3공학관's south face the wall over the lot is the east side of the terrace's long planter, its
#   rims bright on the terrace's plane: u -43.2 .. -38.9 (two years within 0.2 m), v -62.2 .. -43.8, a cross rim at
#   v -56; on the lot's line (u -38.9), not 2 m west of it on the deck's edge (u -40.9) as the game had it.  PLANTER_TOP:
#   its soil over the tile deck's level (S3_DECK_Z); the strip between the hall's south-east corner and its north rim
#   paved at the deck's level
BAY = (0.75, 2.85, 1.75)
PLANTER_UV, PLANTER_CROSS_V, PLANTER_TOP = (-43.2, -38.9, -62.2, -43.8), -56.0, 0.4


def bay_line(n=10):
    """the bay's coping line (u, v), north to south"""
    vc, h, b = BAY
    r = (h * h + b * b) / (2 * b)
    cu = -38.88 + b - r
    a = math.asin(h / r)
    return [(round(cu + r * math.cos(t), 3), round(vc + r * math.sin(t), 3)) for t in np.linspace(a, -a, n + 1)]


WALL_RUNS = [(1.2, [(-38.85, 30.0), (-38.88, BAY[0] + BAY[1])]),
             (1.2, bay_line(), (0.8, 0.0), 'bay'),
             (1.2, [(-38.88, BAY[0] - BAY[1]), (-38.9, -22.0)]),
             (0.05, [(-38.9, -22.0), (-40.6, -22.0), (-40.6, -41.3)]),
             # (the planter's east side and the paved strip north of it: their top over the deck's level)
             (1.2, [(-40.6, -41.3), (-38.9, -41.3)], (0.0, 0.8), 'deck'),
             (1.2, [(-38.9, -41.3), (PLANTER_UV[1], PLANTER_UV[2])], (0.8, 0.0), 'deck'),
             # (공학관 사이: the wall on north of the lot to the yard; its top in the scans is about level with the planted
             # strip behind it, the parapet is the game's, as the lot's; at its north end a return west along the deck's
             # edge, its low side north: (du, dv) of the low side)
             (1.2, [(-39.7, 72.0), (-39.7, 31.0), (-38.85, 30.0)]),
             # (its north end, 2026-11-17: the 1996-12 and 1997-07 scans have the coping turn west at v 71.5 for the
             # planted strip's width, to u -43.5, and north of it a wooded bank with a footpath down to the yard; the
             # deck carries that bank, NORTH_BANK, over the grid's cells round the nodes pulled down behind the wall,
             # and the wall's toe runs on north along the bank's foot to the cells' edge, flush with it)
             (1.2, [(NORTH_END_U, 72.0), (-39.7, 72.0)], (0.0, 0.8)),
             (0.05, [(-39.7, 72.0), (-39.7, NORTH_BANK_V)], (0.8, 0.0)),
             # (and at the deck's south end, over the service road south of the wings: 제3공학관's terrace edge)
             (1.2, [(PLANTER_UV[1], PLANTER_UV[2]), (-52.0, PLANTER_UV[2])], (0.0, -0.8))]
# (제3공학관 남쪽: the wall along the yard's south edge over the bench, STEP_LINE below: added after it)
WALL_UP = 8.0                               # (how far behind the wall a node may be pulled down)
GAP_N = 72.0                                # (the wall's north end, its return: the deck behind it ends there)
# the lane under it: from the court's north alley (v 30) to the yard (v 66; west_ground.LOT_Z there), 해발 (the scans
# have the lane, the alley and the yard on one level: 27.6 - 28.6 m)
LANE_V, LANE_Z = (30.0, 66.0), (27.9, 28.0)
# the north block's west wing in 1997 (its roof's edges on the roof's plane): the west face, the north ends
NB_ID, NB_WEST_U, NB_NORTH_V, NB_MID_NORTH_V = 1451926793, -28.6, 60.0, 60.4
# The three blocks in 1997 (#201, reference/고증/3.8.1): the 2006 survey's outline of the hall
# (1:5000 「서울078」: before the 2007 storey and the 2014 - 2015 wings) moved onto the 1997 scans' roofs, u +1.47 m,
# v -0.78 m (26/15 · 26/16 · 27/17 on the roofs' plane 47.6 m 해발, within 0.1 m of each other, turned under 0.1°),
# split where the game splits the hall: the east wing (blender/landmarks.py engineering), the south block and the north
# block, each up to the east wing's west face.  OSM had them 1.5 - 2 m west, the north block's south face 3.2 m south
EAST_1997 = [(35.32, -29.52), (34.52, 33.78), (49.67, 33.87), (50.4, -29.33)]
SOUTH_1997 = [(-27.43, -57.13), (-27.43, -21.51), (22.38, -20.84), (22.44, -26.12), (35.28, -25.94), (35.32, -29.52),
              (22.19, -29.69), (22.49, -56.42), (7.56, -56.6), (7.49, -33.76), (8.21, -33.76), (8.2, -30.99), (3.97, -31.01),
              (3.97, -30.16), (-12.11, -30.08), (-12.3, -56.94)]
NORTH_1997 = [(34.56, 30.44), (21.49, 30.26), (21.56, 24.92), (-28.11, 24.23), (-28.55, 59.8), (-13.66, 59.99), (-13.32, 33.1),
              (3.13, 33.34), (3.11, 34.46), (7.65, 34.52), (7.61, 37.46), (6.51, 37.44), (6.41, 59.9), (21.58, 59.99), (21.7, 33.71),
              (34.52, 33.78)]
# the two blocks' doors as first put (on OSM's outlines), on the same faces of the 1997 ones: the north block's on the
# north face of its link to the east wing, the south block's on the south face of its link
NB_DOOR_UV, SW_DOOR_UV = (27.35, 33.74), (28.0, -29.61)
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
TREE_SPOTS = [(-33.0, -13.5), (-36.5, -18.5), (-31.5, -19.5), (33.0, -36.5), (41.0, -34.8), (36.5, -39.5), (49.2, -41.2),
              (48.5, -52.0), (37.5, -54.5)]


# 제3공학관 남쪽 (the third round).  The ground south and west of the hall along u (해발 at (u, v -72)): the yard, level
# west of u -78, and the track along it falling east to the service road south of the wings (CTRL's, east of u -30)
S3 = 224955691
YARD_U = [(-135.0, 31.4), (-75.0, 31.4), (-72.0, 31.3), (-69.0, 31.0), (-66.0, 30.6), (-63.0, 30.55), (-60.0, 30.3),
          (-57.0, 30.2), (-54.0, 30.0), (-51.0, 29.9), (-48.0, 29.6), (-45.0, 29.5), (-42.0, 29.35), (-39.0, 29.1),
          (-36.0, 28.6), (-33.0, 28.4), (-30.0, 28.1)]
S3_WEST_U, S3_END_U = -133.0, -125.5        # (the zone's west edge; the hall's west end: north of v -46 only east of it)
S3_DECK_Z = 31.0                            # the tile-paved terrace (해발 at (-232, -279)), east of u -76, north of v -61.3
S3_DECK_UV = (-76.0, -61.3)
S3_ROOF, S3_LEVELS = 54.5, 6                # the roof's deck (해발 at (-250, -260)); the storeys from the terrace up to it
# the retaining wall along the yard's south edge over the bench by 공학원's north hoarding: the cap's line (u, v), the
# bench's height along u (해발 at (u, the line's v - 2); its west end a ramp up to the yard, its east end the track's own
# height), the wall's top over the yard (the scans' cap is about level with it: a cap, the walker kept off the edge by
# walkguard97), and how far north of the line the yard's nodes may go down to the bench (the deck over them)
STEP_LINE = [(-104.0, -82.6), (-100.0, -82.5), (-96.0, -82.1), (-93.0, -81.9), (-81.0, -81.9), (-79.5, -79.5), (-76.5, -77.9),
             (-72.0, -77.7), (-66.0, -77.2), (-55.0, -76.9), (-53.5, -77.6), (-51.0, -79.0), (-46.0, -79.6)]
BENCH_U = [(-110.0, 31.2), (-107.0, 30.2), (-104.0, 29.3), (-98.0, 28.8), (-92.0, 28.6), (-82.0, 28.5), (-70.0, 28.3),
           (-50.0, 28.3), (-46.0, 28.4), (-42.0, 28.9), (-38.0, 28.95)]
STEP_TOP, STEP_DEEP = 0.15, 7.5
WALL_RUNS.append((STEP_TOP, STEP_LINE, (0.0, -0.8)))
# the garden south-east of the south wing: the lawn (u0, u1, v0, v1), the walk across it (its middle line, width),
# where the six trees from 제3공학관's terrace go (the scans' crowns, off the walk; the court's six: TREE_SPOTS)
GARDEN_UV = (26.8, 51.2, -58.3, -32.6)
GARDEN_WALK, GARDEN_WALK_W = [(28.2, -56.6), (50.9, -35.4)], 2.0
GARDEN_MORE = [(44.8, -36.2), (30.5, -47.5), (45.5, -45.5), (44.5, -50.0), (44.5, -56.3), (31.0, -57.0)]
# the north block's west court (between the west and the middle wing of NORTH_1997, open to the yard's south road): u0,
# u1, v0, v1, its ground (해발: nine points)
NB_COURT_UV, NB_COURT_Z = (-13.5, 6.45, 33.2, 60.0), 27.75
# the strip along the north block's north face (the cars' row nosed in to it, the yard's south road): one level with
# the yard west of the eagle (the scans of 1997-07, 1996-12 and 1998-10 each have the strip at v 58 - 68 and the yard's
# south part at v 75 - 97 within 0.15 m of each other, no slope between; reference/고증/3.8 「북쪽 동」), so the yard's
# level as the game has it (west_ground, at v NB_STRIP_V[1] + NB_STRIP_AT) carried south to the face, NB_STRIP_DZ under
# it at the face (v NB_STRIP_V[0]) and eased back to it by v NB_STRIP_V[1]
NB_STRIP_V, NB_STRIP_DZ, NB_STRIP_AT, NB_STRIP_IN = (64.0, 72.0), 0.15, 4.0, 3.0
# 제3공학관 남쪽: the raised lawn west of the flight (its kerb 32.5 - 32.8 m in the scans, the game's ground there as it
# is), the flight and the landing before the door (as it is), the hall's south face west and east of its porch, the
# hall's floor at the landing (해발; 32.8 - 33.0 m at its south end) and its door (u, the porch's middle)
S3_RAISED = [(-124.0, -41.6), (-93.8, -41.6), (-93.8, -46.3), (-92.0, -46.3), (-92.0, -64.0), (-103.0, -64.0), (-122.0, -49.4),
             (-124.0, -49.4)]
S3_PLAZA = [(-92.0, -46.3), (-76.0, -46.3), (-76.0, -64.5), (-92.0, -64.5)]
S3_FACE_V, S3_FLOOR, S3_DOOR_U = -41.3, 32.85, -86.5
# 공학원's north hoarding (the site's ring), the bench's south edge: (u, v)
HOARD = [(-99.5, -87.6), (-47.0, -85.4)]


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
        if v_ < S3_FACE_V and S3_WEST_U - 5.0 <= u_ <= w_ + 0.6:               # (제3공학관 남쪽: s3_grade's yard and deck,
            # its rim at the old edge too: the paved strip and the planter east of it are walked from the deck)
            return float(s3_z(u_, v_)) + float(datum.tilt(x, y))
        if u_ <= w_ + 0.05 and 21.0 <= v_ <= GAP_N and u_ > GAP_W:             # (the gap: all of it north_grade's)
            return float(north_z(u_, v_)) + float(datum.tilt(x, y))
        if u_ <= w_ + 0.05 and -22.0 <= v_ < 21.0 and u_ > -48.5:
            k = min(1.0, max(0.0, (u_ - (w_ - 5.0)) / 2.5))          # (the grid's own within a cell of the wall, eased)
            return h0(x, y) + k * (float(north_z(u_, v_)) + float(datum.tilt(x, y)) - h0(x, y))
        return h0(x, y)
    return f


def outline(uvs):
    """an outline given in the wings' frame (EAST_1997, SOUTH_1997, NORTH_1997) in game coordinates"""
    return [tuple(round(float(c), 2) for c in xy(u_, v_)) for u_, v_ in uvs]


def strip_lawn():
    """the planted strip behind the coping over the lot (the scans' dark band, u -42.3 .. -39.8, the bay in it) and the
    bay's mouth: lawn on the map, over OSM's later walk that ended at the bay"""
    return unary_union([poly([(-42.3, -22.0), (-38.85, -22.0), (-38.85, 30.0), (-42.3, 30.0)]),
                        poly([(-44.5, BAY[0] - BAY[1] - 1.0), (-38.85, BAY[0] - BAY[1] - 1.0), (-38.85, BAY[0] + BAY[1] + 1.0),
                              (-44.5, BAY[0] + BAY[1] + 1.0)])])


def north_path():
    """the footpath down the bank north of the wall's north end (bare earth): its line in game coordinates"""
    return LineString([xy(u, v) for u, v in NORTH_PATH])


def north_paved():
    """the 1997 asphalt here (the scans' pale surface with cars on it): the road band north of 제2공학관 (not 별동연구동's
    outline), the gap's upper ground up to the planted strip behind the wall, the lane under the wall"""
    road = poly([(NROAD_U[0][0], 39.3), (GAP_W, 39.3), (GAP_W, NROAD_V[1]), (NROAD_U[0][0], NROAD_V[1])])
    gap = poly([(GAP_W, 38.85), (-42.3, 38.85), (-42.3, GAP_N), (GAP_W, GAP_N)])
    lane = poly([(-39.6, 30.0), (NB_WEST_U, 30.0), (NB_WEST_U, GAP_N), (-39.6, GAP_N)])
    # (the dead-end alley along 별동연구동's east wall, between it and the kerb at the wood's edge, where a car stood:
    # 26/16 · 26/15, the same grey as the road; game coordinates.  Its ground is the grid's: reference/고증/2.10)
    alley = Polygon([(-246.6, -155.0), (-240.3, -155.0), (-240.0, -147.5), (-244.7, -147.5)])
    return [road, gap, lane, alley]


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
    top = np.where(U > 21.0, 30.5, 30.0)          # (5 - 6 m in under NORTH_1997's bar, up to its link east of it)
    yard = (V >= -64.0) & (V < top) & (U > _west(V)) & (U < east)
    road = (V < -64.0) & (V >= -74.5) & (U >= -88.0) & (U <= 56.0)
    site = (US >= -80.5) & (US <= 54.0) & (VS >= 6.0) & (VS <= 90.0)
    zone = yard | road | site
    Hn[zone] = S[zone]
    # the lane north of the lot under the wall, between it and the north block, up to the yard; the block's nodes 6 m
    # in from its west face with it, so that the row of cars along the face stands level (its floor stays: a plinth)
    lane = (V >= LANE_V[0]) & (V <= GAP_N) & (U > _west(V)) & (U < NB_WEST_U + 6.0)
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
    """the ground behind the wall (the deck's side of the line), north to the return at GAP_N and over it the bank as far
    as the cells round the pulled nodes reach (NORTH_BANK_V)"""
    return poly([(-39.7, NORTH_BANK_V + 6.0), (-39.7, 31.0), (-38.85, 30.0), (-38.9, -22.0), (-40.6, -22.0), (-40.6, -41.3), (-40.9, -62.0),
                 (-60.0, -62.0), (-60.0, NORTH_BANK_V + 6.0)])


def step_poly():
    """the yard's side of the wall over the bench (제3공학관 남쪽), as deep as the nodes s3_grade pulls down and a cell"""
    d = STEP_DEEP + 5.5
    return poly(STEP_LINE + [(STEP_LINE[-1][0], STEP_LINE[-1][1] + d), (STEP_LINE[0][0], STEP_LINE[0][1] + d)])


def deck_side():
    """where a deck may lie: behind the west wall (upper_poly), and north of the wall over the bench (step_poly)"""
    return upper_poly().union(step_poly())


def deck_parts(G, gx, step):
    """the cells with a node pulled down behind the wall, and the part of them behind the wall: build_campus.py's
    dwb_deck lays the upper ground over it"""
    jj, ii = np.nonzero(G['pulled'])
    n = len(gx) - 1
    cells = {(j + a, i + b) for j, i in zip(jj, ii) for a in (-1, 0) for b in (-1, 0) if 0 <= j + a < n and 0 <= i + b < n}
    # (and every cell across the wall's line: one whose nodes behind the wall all lie north of the return at GAP_N
    # was left out, a hole down to the lane's level by the deck's north-east corner)
    side = deck_side()
    band = LineString([xy(u, v) for u, v in ((-39.7, GAP_N), (-39.7, 31.0), (-38.85, 30.0), (-38.9, -22.0), (-40.6, -22.0),
                                             (-40.6, -41.3), (-40.9, -62.0))]).buffer(2.0).intersection(upper_poly())
    band = band.union(LineString([xy(u, v) for u, v in STEP_LINE]).buffer(2.0).intersection(step_poly()))
    x0, y0, x1, y1 = band.bounds
    for j in range(max(0, int((y0 - gx[0]) // step)), min(n, int((y1 - gx[0]) // step) + 1)):
        for i in range(max(0, int((x0 - gx[0]) // step)), min(n, int((x1 - gx[0]) // step) + 1)):
            if box(gx[i], gx[j], gx[i] + step, gx[j] + step).intersection(band).area > 0.05:
                cells.add((j, i))
    # (their neighbours wholly off the deck's side, the lane's and north of the return, count as the deck's for dwb_deck:
    # along an edge shared with a cell that is not, it takes the ground's height, here the lane's or the bank's, not
    # the upper ground's; they get no triangles)
    up_ = side
    for j, i in list(cells):
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                q = (j + a, i + b)
                if q not in cells and 0 <= q[0] < n and 0 <= q[1] < n and \
                        box(gx[q[1]], gx[q[0]], gx[q[1]] + step, gx[q[0]] + step).intersection(up_).area < 0.05:
                    cells.add(q)
    area = unary_union([box(gx[i], gx[j], gx[i] + step, gx[j] + step) for j, i in cells]).intersection(side)
    area = unary_union([g for g in getattr(area, 'geoms', [area]) if g.geom_type == 'Polygon' and g.area > 0.05])
    return cells, area


def walls(low, up):
    """the retaining wall's runs for blender/landmarks.py _wall_run: [top over the upper ground, [[x, y, foot, the upper
    ground], ...]] every metre; low(x, y), up(x, y): the ground as saved, the ground as it was"""
    out = []
    for run in WALL_RUNS:
        top, pts = run[:2]
        du, dv = run[2] if len(run) > 2 else (0.8, 0.0)
        kind = run[3] if len(run) > 3 else None
        ls = LineString([xy(u, v) for u, v in pts])
        n = max(1, int(round(ls.length)))
        row = []
        for k in range(n + 1):
            q = ls.interpolate(k / n, normalized=True)
            u_, v_ = uv(q.x, q.y)
            e, w = xy(float(u_) + du, float(v_) + dv), xy(float(u_) - du, float(v_) - dv)
            if kind == 'bay':                       # (the upper ground at the straight line's back)
                w = xy(-39.7, float(v_))
            elif kind == 'deck':                    # (the tile deck's level on the deck behind the old edge)
                w = xy(-41.8, max(min(float(v_) - 1.0, -42.0), -61.0))
            row.append([round(q.x, 2), round(q.y, 2), round(float(low(*e)) - 0.5, 2), round(float(up(*w)), 2)])
        out.append([top, row])
    return out


def bay_top(up):
    """the bay's ground (the planted strip's, at the straight line's back): its outline [x, y, z] (z working datum)"""
    ring = bay_line() + [(-38.88, BAY[0] - BAY[1])]
    return [[round(float(c), 2) for c in xy(u, v)] + [round(float(up(*xy(-39.7, v))), 3)] for u, v in ring]


def planter(up):
    """the terrace's planter and the paved strip north of it: [outline [x, y], top z], the cross rim's ends, the strip's
    outline and z (z working datum; up(x, y): the deck's ground)"""
    u0, u1, v0, v1 = PLANTER_UV
    zd = float(up(*xy(-41.8, -52.0)))
    box = [[round(float(c), 2) for c in xy(u, v)] for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
    strip = [[round(float(c), 2) for c in xy(u, v)] for u, v in ((-40.9, v1), (u1, v1), (u1, -41.3), (-40.9, -41.3))]
    cross = [[round(float(c), 2) for c in xy(u, PLANTER_CROSS_V)] for u in (u0, u1)]
    return dict(box=box, top=round(zd + PLANTER_TOP, 3), deck=round(zd, 3), cross=cross, strip=strip)


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


# ----------------------------------------------------------------------------------------- 제3공학관 남쪽 (the third round)
def step_v(U):
    """the wall's line over the bench: its v at u"""
    return np.interp(U, *zip(*STEP_LINE))


def bench_z(U):
    """the bench along 공학원's north hoarding (해발) at u: its ramp up to the yard at the west end"""
    return np.interp(U, *zip(*BENCH_U))


def s3_z(U, V):
    """the 1997 ground south and west of 제3공학관 (해발): the yard and the track along it (YARD_U along u), the tile deck"""
    yard = np.interp(U, *zip(*YARD_U))
    return np.where((U >= S3_DECK_UV[0]) & (V >= S3_DECK_UV[1]), S3_DECK_Z, yard)


def _hoard_v(U):
    return np.where(U < HOARD[0][0], -90.0, np.interp(U, *zip(*HOARD)))


def s3_region():
    """the ground s3_grade lays (the hall, the raised lawn and the landing taken out by the caller): from the hall's west
    end to the lane west of the south wing, the hall's south face down to the wall over the bench, the bench to the
    hoarding, and west of the wall's end over the ramp"""
    south = [(-46.0, -79.6), (-46.0, -85.4)] + [(u, float(_hoard_v(u))) for u in (-60.0, -80.0, -99.5)] + \
        [(-113.5, -86.0), (S3_WEST_U, -86.0)]       # (south of it west_ground.site_edges' band, and the yard as it is)
    return poly([(S3_WEST_U, S3_FACE_V), (-40.9, S3_FACE_V), (-40.9, -64.0), (-46.0, -64.0)] + south)


def s3_grade(Hn, X, Y, FIXED, G, hall, fill, avoid):
    """제3공학관 남쪽, after grade (the planting has read the ground as it was): the yard west and south of the hall and the
    track along it on the 1997 heights (s3_z), the tile deck at S3_DECK_Z, the bench along 공학원's hoarding (bench_z);
    the yard's nodes in the cells across the wall over the bench down to the bench (deck_parts lays the yard over them);
    the raised lawn and the landing before the door as they are; the ground round it smoothed (fill) into what stays.
    hall: 제3공학관's outline.  G: grade's (zone and pulled grow).  avoid: nodes another block keeps (the site's west band)"""
    H0 = Hn.copy()
    U, V = uv(X, Y)
    T = datum.tilt(X, Y)
    keep = shapely.contains_xy(poly(S3_RAISED), X, Y) | shapely.contains_xy(poly(S3_PLAZA), X, Y) | G['pulled'] | avoid
    inr = shapely.contains_xy(s3_region(), X, Y) & ~keep
    inh = shapely.contains_xy(hall, X, Y)
    sv = step_v(U)
    wall = (U >= STEP_LINE[0][0]) & (U <= STEP_LINE[-1][0])
    bench = inr & (U >= BENCH_U[0][0]) & (U <= STEP_LINE[-1][0]) & (V < np.where(wall, sv, -82.6)) & (V > _hoard_v(U) - 1.0)
    yard = inr & ~bench & ~inh
    Hn[yard] = (s3_z(U, V) + T)[yard]
    Hn[bench] = (bench_z(U) + T)[bench]
    # (under the hall within a cell of its south face: the deck's level east of the landing, so that the ground meets
    # the face level)
    under = inh & (V < S3_FACE_V + 5.5) & (U >= S3_DECK_UV[0]) & (U <= -40.9) & ~keep
    Hn[under] = (S3_DECK_Z + T)[under]
    zone = yard | bench | under
    # the wall over the bench: the yard's nodes in a cell with a bench node, within STEP_DEEP of the line, go down
    cell = bench[:-1, :-1] | bench[:-1, 1:] | bench[1:, :-1] | bench[1:, 1:]
    touch = np.zeros(bench.shape, bool)
    touch[:-1, :-1] |= cell
    touch[:-1, 1:] |= cell
    touch[1:, :-1] |= cell
    touch[1:, 1:] |= cell
    pulled = yard & wall & touch & (V >= sv) & (V < sv + STEP_DEEP)
    Hn[pulled] = (bench_z(U) + T)[pulled]
    # the ring: 15 m round it, not the raised lawn, the landing, the hall, the other halls' feet or what is fixed
    ring = binary_dilation(zone, iterations=3) & ~zone & ~keep & ~inh & ~FIXED
    if ring.any():
        fill(ring)
    FIXED[zone] = True
    G['zone'] = G['zone'] | zone
    G['pulled'] = G['pulled'] | pulled
    d = Hn - H0
    return dict(nodes=int((np.abs(d) > 0.05).sum()), most=round(float(d.min()), 2), up=round(float(d.max()), 2),
                yard=int(yard.sum()), bench=int(bench.sum()), pulled=int(pulled.sum()), ring=int(ring.sum()))


def nb_grade(Hn, X, Y, FIXED, nb):
    """the north block's west court at its 1997 ground (NB_COURT_Z: the game had a lawn climbing to 33 m in it), the
    nodes under the wings within a cell of it with it; the strip along the block's north face on the level of the yard
    west of the eagle as the game has it (NB_STRIP_*).  nb: the block's outline"""
    H0 = Hn.copy()
    U, V = uv(X, Y)
    T = datum.tilt(X, Y)
    u0, u1, v0, v1 = NB_COURT_UV
    court = (U >= u0 - 5.0) & (U <= u1 + 5.0) & (V >= v0 - 5.0) & (V <= v1)
    court &= shapely.contains_xy(nb.buffer(0.5), X, Y) | shapely.contains_xy(poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)]), X, Y)
    court &= (U > NB_WEST_U + 6.0)                  # (the lane's, west of it: grade)
    Hn[court] = NB_COURT_Z + T[court]
    # (and the nodes under the block within a cell of its north face, which eagle_yard left at its old floor, 29.1 m: the
    # cars nosed in to the face stood on their cells, 8 - 10 degrees up)
    north = (V > v1 - NB_STRIP_IN) & (V <= NB_STRIP_V[1]) & (U > NB_WEST_U + 6.0) & (U < 21.0) & ~court
    from scipy.ndimage import map_coordinates
    gx, gy = X[0, :], Y[:, 0]
    st = gx[1] - gx[0]
    yx, yy = xy(U, np.full(U.shape, NB_STRIP_V[1] + NB_STRIP_AT))
    zy = map_coordinates(H0 - T, [(yy - gy[0]) / st, (yx - gx[0]) / st], order=1, mode='nearest')   # (the yard, 해발)
    zn = zy - NB_STRIP_DZ * np.clip((NB_STRIP_V[1] - V) / (NB_STRIP_V[1] - NB_STRIP_V[0]), 0.0, 1.0)
    Hn[north] = (zn + T)[north]
    FIXED[court | north] = True
    d = Hn - H0
    return dict(court=int(court.sum()), north=int(north.sum()), most=round(float(d.min()), 2))


def s3_paint():
    """제3공학관 남쪽 in 1997: bare earth all round (the yard, the track, the bench), the tile deck and the landing paved;
    and the area to clear first (OSM's later lawn, walks and asphalt there).  Returns (clear, bare, paved)"""
    deck = poly([(S3_DECK_UV[0], S3_FACE_V), (-40.9, S3_FACE_V), (-40.9, S3_DECK_UV[1]), (S3_DECK_UV[0], S3_DECK_UV[1])])
    plaza = poly(S3_PLAZA)
    region = s3_region()
    # (cut through the region's north edge under the hall, so that the bare ground has no hole: _ypaint draws outlines)
    cut = unary_union([deck, plaza, poly(S3_RAISED), poly([(-124.0, -42.0), (-40.9, -42.0), (-40.9, -40.0), (-124.0, -40.0)])])
    bare = region.difference(cut)
    assert all(not g.interiors for g in getattr(bare, 'geoms', [bare])), 's3_paint: a hole'
    return region, bare, deck.union(plaza)


def garden():
    """the garden south-east of the south wing: its lawn and the walk across it"""
    u0, u1, v0, v1 = GARDEN_UV
    return poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)]), [xy(u, v) for u, v in GARDEN_WALK]


def south_walks(paths):
    """the map's walks: the later ones across the yard south of 제3공학관 and across the garden out (OSM's paths there:
    the terrace's walks and flights, the garden's; the drives down into 공학원's site across the wall), the walk across
    the garden in (the flight to the hall's door stays).  Returns (out, in)"""
    lawn, walk = garden()
    clear = s3_region().union(poly(S3_RAISED)).buffer(0.5)
    wall = LineString([xy(u, v) for u, v in STEP_LINE])
    n0 = len(paths)
    keep = []
    for p in paths:
        if p['kind'] == 'service' and len(p['pts']) > 1 and LineString([q[:2] for q in p['pts']]).crosses(wall):
            continue
        if p['kind'] in ('footway', 'path', 'steps', 'pedestrian') and len(p['pts']) > 1:
            ls = LineString([q[:2] for q in p['pts']])
            if clear.contains(ls) or lawn.buffer(0.3).contains(ls):
                continue
            if lawn.buffer(-1.0).intersection(ls).length > 1.0:          # (one crossing the lawn: cut where it does)
                parts = ls.difference(lawn.buffer(-0.5))
                for g in getattr(parts, 'geoms', [parts]):
                    if g.length > 1.0:
                        keep.append({**p, 'pts': [[round(x, 2), round(y, 2)] for x, y in g.coords]})
                continue
        keep.append(p)
    paths[:] = keep
    w = dict(kind='footway', w=GARDEN_WALK_W, pts=[[round(x, 2), round(y, 2)] for x, y in walk])
    paths.append(w)
    return n0 - len(paths) + 1, 1


def move_off_south(trees, shrubs, props):
    """what the planting put on the yard, the terrace and the landing south of 제3공학관 (bare earth and paving in the
    scans, no tree): trees go, each in its place in the list, to the garden's crowns (GARDEN_MORE, the nearest free one);
    shrubs and props go.  On the garden's lawn the motorbikes of photo A (its depth along the view is loose) stand at
    its east edge, on the paving.  Returns (trees moved, shrubs out, props out, motorbikes moved)"""
    zone = s3_region().union(poly(S3_RAISED)).union(poly(S3_PLAZA))
    spots = [xy(u, v) for u, v in GARDEN_MORE]
    moved = []
    for t in trees:
        if zone.contains(Point(t[1], t[2])) and spots:
            q = min(spots, key=lambda q_: math.hypot(q_[0] - t[1], q_[1] - t[2]))
            spots.remove(q)
            moved.append((t[0], t[1], t[2]))
            t[1], t[2] = round(q[0], 2), round(q[1], 2)
    n0 = (len(shrubs), len(props))
    shrubs[:] = [s for s in shrubs if not zone.contains(Point(s[1], s[2]))]
    props[:] = [p for p in props if not zone.contains(Point(p[1], p[2]))]
    lawn, _ = garden()
    mb = 0
    for p in props:
        if p[0] == 'motorbike' and lawn.buffer(0.4).contains(Point(p[1], p[2])):
            u_, v_ = (float(c) for c in uv(p[1], p[2]))
            p[1], p[2] = (round(c, 2) for c in xy(GARDEN_UV[1] + 0.9, v_))
            mb += 1
    return moved, n0[0] - len(shrubs), n0[1] - len(props), mb


def s3_hall(b):
    """제3공학관 as the scans have it: its floor at the landing (S3_FLOOR), its roof's deck at S3_ROOF, five storeys between
    (지상 5층 in the record), its door at the head of the flight.  b: its campus.json entry (work-datum heights)"""
    cx, cy = xy(-83.0, -34.0)
    base = datum.up(cx, cy, S3_FLOOR)
    lv = b['levels']
    fh = round((S3_ROOF - S3_FLOOR) / lv, 3)
    b.update(base=base, fh=fh, height=round(lv * fh + 1.2, 2))
    if b.get('entry'):
        b['entry'].update(p=[round(c, 2) for c in xy(S3_DOOR_U, -46.3)], n=[round(_S, 4), round(-_C, 4)])
    return base, fh
