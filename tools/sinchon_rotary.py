"""신촌 로터리: 굴다리에서 연세로를 따라 신촌 로터리(신촌오거리)까지 (reference/고증/4.10_신촌_로터리.md).
tools/build_campus.py 가 부른다.

    Hs = sinchon_rotary.patch(raw, Hn, half, step)          # the near terrain's patch south of the 5 m grid
    geo = sinchon_rotary.streets(town_plan)                   # 연세로 and the five-way junction: carriageways, walks
    sinchon_rotary.level(Hn, Hs, half, step, geo)             # their beds levelled across, smoothed along
    ext = sinchon_rotary.layout(geo, town, extras, ground)    # after gate_town.layout: what campus.json gains

Frame: campus metres, x east, y north.  The 5 m grid of the campus ends at y -800; the junction (y -975) and the
streets round it stand on a patch of its own (SOUTH) laid against the grid's south edge, from the same elevation
model the same way.  Nothing here draws from build_campus.py's `rng` or gate_town's stream: random.Random(4802).

Where things stand (고증 4.10):
- The streets' middle lines are OSM's (data/raw/osm_rotary.json, tools/fetch_rotary_osm.py): 연세로 as one line, the
  others the middle between their two carriageways.  Today's 신촌로 has its buses in the middle and 연세로 is a
  transit mall (2014).  From the 1997 scans of 27/18 · 27/19 (고증 4.10.4 「다섯 길과 노면 표시」): 1997년 서강로's
  line, width and lanes (BB_C), the painted middles of 양화로 and 신촌로 (mid_of), the paint at the mouths; the
  wedges' hatched triangles and the south-west arm's width are not (남은 한계).
- The shops along 연세로 stand wall to wall behind a 3.75 m walk, broken where OSM's side streets come in: near the
  junction as the 1996 photos show them, the rest from their mix, signs standing out from the walls (yro_ functions at
  the end); the corners of the junction carry OSM's big outlines.
"""
# (every absolute height written in this file's code is above sea level, 해발: datum.up · up3 · up_at · up_plane take it
# up to the working datum the ground is laid on, 해발 + tilt, where it is read: tools/datum.py.  The heights quoted
# in the comments are 해발 too)
import json, math, os, random
import numpy as np
import datum
from scipy import ndimage
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
import shapely
from PIL import Image, ImageDraw
import gate_town as gt
import yro97

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SOUTH = dict(x0=-600.0, y0=-1200.0, step=5.0, nx=201, ny=81)          # x -600 .. 400, y -1200 .. -800
TSPLAT = dict(x0=-420.0, y0=-1200.0, x1=220.0, y1=-550.0, res=0.5)    # the town's own ground map (web/src/terrain.js)
JC = (-100.0, -975.0)          # the junction's middle
REACH = 125.0                  # how far from it the walks are open along each street

# the streets' middle lines from the junction outward (OSM: 연세로 way 383312033; the middles of 신촌로's, 서강로's
# two carriageways; 백범로 near the junction one-way today, its line).  half: the carriageway's half width, walk:
# the sidewalk's width, lanes: each way
ARMS = {
    'yonsei': dict(half=6.5, walk=5.0, lanes=2, pts=[(-98.6, -962.0), (-98.4, -945.0), (-98.25, -912.0), (-97.5, -885.0),
                                                     (-96.4, -850.0), (-95.2, -810.0), (-94.3, -780.0), (-94.4, -740.0),
                                                     (-94.0, -700.0), (-94.0, -455.0)]),
    'sinchon_w': dict(half=14.0, walk=5.5, lanes=5, mid=-0.75, pts=[(-100.4, -971.6), (-114.8, -970.2), (-125.4, -966.7), (-139.7, -962.1),
                                                         (-153.8, -957.5), (-167.1, -951.8), (-193.8, -939.5), (-221.0, -927.0),
                                                         (-262.1, -908.1), (-303.2, -889.8), (-344.9, -871.8), (-398.4, -849.8),
                                                         (-460.0, -824.0)]),
    'sinchon_e': dict(half=14.0, walk=5.5, lanes=4, pts=[(-100.4, -971.6), (-85.7, -972.3), (-70.9, -971.3), (-56.8, -968.0),
                                                         (-44.6, -964.1), (-32.1, -958.8), (9.6, -941.6), (79.3, -913.3),
                                                         (148.8, -885.1), (217.9, -856.5), (275.6, -833.5), (320.0, -826.1),
                                                         (364.9, -822.4)]),
    'seogang': dict(half=10.0, walk=4.5, lanes=3, pts=[(-99.5, -990.0), (-117.9, -1002.2), (-141.6, -1019.5), (-165.4, -1037.3),
                                                       (-201.0, -1064.9), (-236.3, -1092.5), (-272.4, -1119.8), (-308.3, -1146.8),
                                                       (-342.3, -1174.1), (-373.3, -1206.4)]),
    'baekbeom': dict(half=7.5, walk=4.5, lanes=2, pts=[(-102.0, -985.0), (-101.0, -1011.0), (-98.0, -1028.0), (-96.0, -1044.0),
                                                       (-94.0, -1059.0), (-92.0, -1077.0), (-86.0, -1120.0), (-80.0, -1168.0),
                                                       (-75.0, -1205.0)]),
}
# 1997년 서강로 (baekbeom) as the scans of 27/18 and 27/19 have it (2026-11-14, 고증 4.10.4 「다섯 길과 노면 표시」): its double
# yellow middle line (both frames within 0.1 m, reprojected on the road's own heights 20.2 - 25.8 m), 3 - 6 m east of
# OSM's line above; the kerbs 9.0 m west of it (the crossing's west end, a bus at the kerb) and 6.5 m east (the
# pavement's edge in both frames, the stop line's end): 15.5 m of carriageway, three lanes out (south) with two dashed
# lines 3.05 and 6.0 m west of the middle, two in (north) with a solid line 3.15 m east of it; north of the crossing the
# same middle line runs on to the junction, the lanes in beside it, the junction's open asphalt west of it.
# ARMS keeps the carriageway's middle (half 7.75) and 'mid' says where the painted middle is from it (+n: east)
BB_C = [(-97.7, -985.0), (-95.21, -1002.27), (-90.86, -1031.95), (-88.14, -1056.85), (-86.01, -1072.71), (-83.26, -1092.52),
          (-80.85, -1112.38), (-78.98, -1127.26), (-76.66, -1142.09), (-74.59, -1156.95), (-73.07, -1171.88), (-71.45, -1186.78),
          (-69.83, -1201.7), (-69.4, -1206.0)]
BB_KERB_W, BB_KERB_E = 9.0, 6.5
# the painted lines off the middle (m, +east): dashed white out, solid white in; north of the crossing (y > -1042) the
# two lines in beside the middle are solid (3.3, 6.65; the third, 10.0, is the U-turn loop's edge, ROT_D)
BB_LINES_S = [(-3.05, 'white_dash'), (-6.0, 'white_dash'), (3.15, 'white')]
BB_LINES_N = [(3.3, 'white'), (6.65, 'white')]
# its line before 2026-11-14 (OSM's): what the random streams decide along it is still decided round it (YONSEI_RNG_PTS)
BAEKBEOM_RNG = dict(ARMS['baekbeom'])
# 신촌로 (the east arm, sinchon_e): the painted middle (a band of two lines 0.9 m apart near the junction) south of OSM's line
# by 3.0 m at 26 m out, 2.35 at 50, 1.7 from 65 on (both scans, eleven windows within 0.15 m); the kerbs stay (the
# north one within 0.5 m of the scans', the south one near the junction: SE_KERB below)
SINCHON_E_MID = [(0.0, -3.0), (26.0, -3.0), (38.0, -2.7), (50.0, -2.35), (65.0, -1.75), (80.0, -1.7), (101.0, -1.75),
                 (119.0, -1.5), (143.0, -1.2), (167.0, -0.85), (197.0, -0.7), (221.0, -0.5), (263.0, -0.5), (275.0, -0.7),
                 (287.0, -1.1), (299.0, -1.4), (311.0, -1.65), (329.0, -2.0), (353.0, -1.7), (371.0, -1.45), (383.0, -1.15),
                 (401.0, -0.65), (425.0, -0.5), (443.0, -0.55), (467.0, -1.1), (1000.0, -1.1)]
# (2026-11-21, 고증 4.10.4.3 「신촌로(동)의 남쪽 연석」: past s 80 the band's brighter north line every 6 m in both scans,
# 0.4 m north of the band's middle where both are read: the middle wanders 1.5 m about OSM's line out to the arm's end)
# Its south lanes as the scans paint them, from the junction to the crossing at s 278 (both scans' dashes within
# 0.1 - 0.3 m): two dashed lines, solid the last 6 - 12 m to the stop line (SE_STOP); the third dashed to the side
# street, then the bus lane's blue line (52204, 1996.6); the stop's dashed line in front of 한일은행; a solid line
# 2.9 m off the kerb from behind the stop to s 220 (2026-11-21 둘째: the scans' -12.2 .. -13.0, which the frames of
# 1996 have with a bus south of it).  [(s, m off the arm's line)] and the [s0, s1] spans painted with each kind
SE_LINES = [([(45.0, -5.13), (55.0, -4.67), (64.0, -4.55), (72.0, -4.48), (88.0, -4.36), (103.0, -4.21), (126.0, -3.94),
              (143.0, -3.73), (152.0, -3.6), (170.0, -3.42), (197.0, -3.1), (216.0, -2.94), (236.0, -2.84), (276.0, -2.8)],
             [(45.0, 263.3, 'white_dash'), (263.3, 275.0, 'white')]),
            ([(45.0, -7.6), (60.0, -7.45), (77.0, -7.27), (84.0, -7.18), (100.0, -6.96), (114.0, -6.79), (130.0, -6.63),
              (148.0, -6.45), (166.0, -6.25), (184.0, -6.04), (212.0, -5.72), (240.0, -5.64), (261.0, -5.77), (276.0, -5.8)],
             [(45.0, 269.0, 'white_dash'), (269.0, 275.0, 'white')]),
            ([(53.0, -10.67), (64.0, -10.51), (80.0, -10.51), (98.0, -10.6)], [(53.0, 98.0, 'white_dash')]),
            ([(100.0, -10.4), (112.0, -10.0), (130.0, -9.85), (148.0, -9.6), (160.0, -9.4), (195.0, -9.1), (276.0, -9.2)],
             [(100.0, 275.0, 'blue')]),
            ([(98.0, -15.6), (125.0, -15.6)], [(98.0, 125.0, 'white_dash')]),
            ([(130.0, -12.95), (146.0, -12.75), (170.0, -12.45), (194.0, -12.2), (206.0, -12.05), (220.0, -11.9)],
             [(130.0, 220.0, 'white')])]
# The crossing at s 278 (2026-11-21 둘째, 고증 4.10.4.3 「신촌로(동)의 건널목과 바깥 차로」): two columns of bars s 278.4 -
# 281.9 and 282.1 - 285.75 from the south kerb to 1.25 m short of the north one (o -14.85 .. +12.75), the stop line of
# the way out 3.25 m before it (s 275.15), of the way in 4.1 m past it (s 289.85); both scans within 0.1 m.  No signals
SE_CROSS = dict(cols=[(278.4, 281.9), (282.1, 285.75)], o=(-14.85, 12.75), stop_out=275.15, stop_in=289.85)
# and past it both halves' lines as the scans have them (both frames within 0.1 - 0.2 m, every 6 m to s 477): three
# each way, solid for 12 - 18 m from the crossing, the outer one solid all the way (south: the bus lane's blue line,
# on from before the crossing; north: white, its colour not known).  The rule's lanes no more on this arm
SE_FAR_LINES = [([(286.0, -3.5), (297.0, -3.8), (309.0, -4.1), (321.0, -4.4), (345.0, -4.4), (357.0, -3.95), (369.0, -3.75),
                  (387.0, -3.4), (399.0, -3.3), (423.0, -2.9), (441.0, -2.9), (453.0, -3.2), (465.0, -3.5), (500.0, -3.5)],
                 [(286.0, 303.0, 'white'), (303.0, 489.0, 'white_dash')]),
                ([(286.0, -6.4), (303.0, -6.7), (321.0, -7.1), (333.0, -7.0), (363.0, -7.0), (375.0, -6.7), (387.0, -6.2),
                  (399.0, -6.0), (411.0, -5.8), (435.0, -5.8), (447.0, -6.0), (459.0, -6.2), (471.0, -6.4), (500.0, -6.4)],
                 [(286.3, 298.0, 'white'), (298.0, 489.0, 'white_dash')]),
                ([(286.0, -9.3), (303.0, -9.8), (321.0, -10.1), (351.0, -9.6), (369.0, -10.1), (381.0, -9.8), (393.0, -9.15),
                  (411.0, -9.15), (417.0, -8.9), (441.0, -8.9), (459.0, -9.45), (500.0, -9.45)], [(286.0, 489.0, 'blue')]),
                ([(290.0, 1.9), (297.0, 1.8), (309.0, 1.5), (321.0, 1.35), (339.0, 1.35), (351.0, 1.55), (363.0, 1.85),
                  (375.0, 2.05), (387.0, 2.35), (399.0, 2.55), (411.0, 2.7), (423.0, 2.85), (441.0, 2.85), (453.0, 2.45),
                  (465.0, 2.3), (500.0, 2.3)], [(290.3, 302.5, 'white'), (302.5, 489.0, 'white_dash')]),
                ([(290.0, 4.9), (297.0, 4.6), (309.0, 4.4), (321.0, 4.25), (333.0, 4.25), (345.0, 4.4), (357.0, 4.6), (369.0, 4.8),
                  (381.0, 4.95), (393.0, 5.4), (411.0, 5.4), (429.0, 5.6), (447.0, 5.3), (459.0, 5.0), (500.0, 5.0)],
                 [(290.3, 308.0, 'white'), (308.0, 489.0, 'white_dash')]),
                ([(290.0, 7.5), (345.0, 7.5), (357.0, 7.75), (369.0, 7.9), (387.0, 7.9), (399.0, 8.25), (411.0, 8.25),
                  (423.0, 8.9), (435.0, 8.9), (441.0, 8.1), (453.0, 8.2), (500.0, 8.2)], [(290.3, 489.0, 'white')])]
# Its north lanes from the taxis' band (ROT_LANE_FROM) to the crossing, as both scans have them (6 m windows, 0.1 m
# apart; 2026-11-21 둘째): two dashed lines and a solid one by the bus lane from s 94 (its colour not known).  Before:
# the rule's three dashed lines, 0.6 - 1.7 m further out
NE_LINES = [([(47.0, 2.0), (58.0, 2.0), (64.0, 1.7), (100.0, 1.5), (124.0, 1.7), (142.0, 1.9), (160.0, 2.2), (184.0, 2.5),
              (202.0, 2.6), (220.0, 2.75), (262.0, 2.75), (274.0, 2.5), (278.0, 2.5)], [(47.0, 278.0, 'white_dash')]),
            ([(47.0, 4.4), (64.0, 4.35), (100.0, 4.35), (112.0, 4.55), (130.0, 4.7), (148.0, 4.9), (166.0, 5.1), (184.0, 5.3),
              (202.0, 5.5), (226.0, 5.65), (250.0, 5.8), (278.0, 5.7)], [(47.0, 278.0, 'white_dash')]),
            ([(94.0, 7.5), (124.0, 7.75), (142.0, 7.95), (160.0, 8.23), (184.0, 8.4), (208.0, 8.53), (226.0, 8.78),
              (278.0, 8.7)], [(94.0, 278.0, 'white')])]
# Its south kerb (2026-11-21, 고증 4.10.4.3 「신촌로(동)의 남쪽 연석」): 16.3 m south of the arm's line, not 14, from the
# island's turning lane to the bus stop in front of 한일은행 (s 125).  52204 (1996.6, from 외환은행's roof) across one row
# through the stop: the yellow middle, the two dashed lines, the blue bus lane's line and the dark pavement behind the
# kerb (the scans' -1.7, -4.2, -6.9, -10.0 and -16.8) put the kerb's brown line at -16.26 and the stop's dashed line at
# -15.57 (the scans' bright line -15.6), 0.08 m off at most; 27/18 · 27/19 both have the gutter's dark line at -16.2
# either side of the side street (s 86, 98) and a car at -13.4 .. -15 (s 78); stair 5's roof (-16.4 .. -20.4, s 58 ..
# 68) stands at the kerb.  On out (2026-11-21 둘째): -15.5 under the trees (s 140 - 185: the leaf-off frames of 1996,
# 26/17 · 27/18, where the asphalt meets the paving, less the 0.25 m those frames read south of 1997's on the painted
# line beside it), -15.2 from s 205 (1997's paving edge in both frames wherever no crown hides it, s 218 - 330),
# back to the arm's -14 by s 360 (s 341 -14.6, s 359 - 383 -14.0 .. -14.4).  [(s, m off the line)]: the asphalt the
# game adds south of -half
SE_KERB = [(40.0, -16.3), (125.0, -16.3), (140.0, -15.5), (185.0, -15.5), (205.0, -15.2), (330.0, -15.2), (345.0, -14.6),
           (360.0, -14.0)]


def se_kerb(s):
    """신촌로 (동)'s south kerb, m off the arm's line (-: south), s m out"""
    t = np.array(SE_KERB)
    return float(np.interp(s, t[:, 0], t[:, 1])) if s <= t[-1, 0] else -ARMS['sinchon_e']['half']
# 양화로 (sinchon_w, ARMS above: lanes 5, mid -0.75): its painted middle 0.75 m north of the arm's line, five lanes of
# 2.75 - 2.9 m each way between kerbs 13.75 m either side of it (both scans, nine windows: lines 2.85, 5.65, 8.75 and
# 11.3 m south of the middle, 2.85, 5.75, 8.75 and 10.9 north; 1995's 52145: four rows of cars and the buses' lane in);
# the kerbs stay where they were (0.5 and 1.0 m off)
# 연세로's line before 2026-11-14 (OSM's today, the 2014 transit mall's): what the random streams decide along it is
# still decided round it (layout: the old rows' draws, the blocks kept clear of the streets; the ginkgos' draws), so
# that nothing away from 연세로 moves.  The line above is the 1990s' road (고증 4.10.1): x -94 from the
# bridge to y -780 (the bridge's opening, the 1997 frames' centre line, the 2008 · 2010 skyview's yellow line and
# kerbs), then bending west to the kerbs' middle at y -885 (-97.5, 2008 · 2010) and -930 (-97.8, 2010) and on into
# the junction 1.4 m east of the island's middle
YONSEI_RNG_PTS = [(-101.5, -962.0), (-101.5, -945.0), (-101.0, -925.0), (-100.0, -890.0), (-99.0, -853.0), (-98.0, -809.0),
                  (-96.0, -753.0), (-96.0, -740.0), (-96.0, -455.0)]
CORNER_R = 9.0                 # the kerbs' rounding at the corners
# the rotary's round island in the middle (서울연구원 1995 · 1996 photos from the roof of 그레이스백화점, 52142 · 52145 ·
# 52158 · 52187).  52158's camera solved from the bed's outline and two city buses (고증 4.10 「옥상 사진의 카메라」):
# the lawn's edge 15.2 m across (r 7.6 +- 0.15), the kerb's outside 7.8; the white ring of short dashes just outside
# it, r 8.4 (the ring over the bed 1.10 there, 1.14 in 52142); the bed's rings from the middle out (BED: outer radius,
# what grows there); a tall signal pole on its north edge, its mast arm out to the north-east; no lamp in the middle
# Where it stood (2026-11-14, 고증 4.10 「1997년 7월 항공사진」): not at the five streets' middle (OSM's lines meet at
# (-100, -976) today; 52158's camera had been solved with the island pinned there) but 37 m south-east of it, in the
# wedge between 신촌로 and 서강로: the 1997-07-28 frame 27/18 (the same flight's next frame south of the six) and the
# 1998-10-08 frame 26/17 show its ring of beds (dark middle, bright yellow band, dark band, pale rim; 15.6 m across)
# at (-73.4, -1001.3) and (-73.8, -1002.3), cameras from the east and the north-west; the scans of 27/18 and 27/19
# (the same flight's, 0.13 m/px) agree at (-73.3, -1000.9) on ground 20.5 m (0.2 m apart).  The pole and 「연세대」:
# below (52158 solved again, the scans)
ISLAND = dict(c=(-73.3, -1000.9), r=7.8, ring=8.45)
# The bed in summer (2026-11-17): 52127 (August 1996, from 그레이스's roof) has a clipped dark-green mound in the middle,
# a wide band of flowers of three colours mixed round it (scarlet, yellow and violet) and a lawn outside: the rings of
# the July 1997 scans (a dark disc to r 2.3, a bright band to about 5, then darker, the lawn), not May 1996's (52158:
# lawn, a yellow band of pansies, a dark band, white flowers).  BED_MAY is that one, as it was laid until then
BED = [(2.3, 'mound'), (5.0, 'dark'), (7.6, 'lawn')]
BED_MAY = [(2.5, 'lawn'), (4.3, 'yellow'), (5.6, 'dark'), (6.1, 'white'), (7.6, 'lawn')]
# its planting: the mound seven clipped domes (topiary_dome, 2.2 m across, one in the middle and six round it at
# ISLAND_MOUND_R), the band rings of the summer bed's lengths (summer_bed, 1.96 x 0.72 m: blender/shrubs.py) laid
# along it [radius, how many]; the ground under the band painted dark leaves (BED 'dark': web/src/terrain.js)
ISLAND_MOUND_R = 1.3
ISLAND_FLOWER_RINGS = [(2.75, 9), (3.45, 11), (4.15, 13), (4.7, 15)]
# The bed is a low mound (2026-11-15, 고증 4.10.2 「가운데 섬」): the scans of 27/18 and 27/19 (windows of 2.5 m every 20°
# round rings of 1.5 .. 7.4 m, correlation 0.9 - 0.99) have its top over the plane of the road round it (34 points
# 2 - 4 m outside the kerb, rms 0.09 m; it rises 2.9 % to the north) by 0.76 m at 1.5 m from the middle, 0.70 at 2.5,
# 0.60 at 3.4, 0.48 at 4.3, 0.41 at 5.0, 0.30 at 5.6, 0.14 at 6.2, 0.03 at 6.9 and 0.01 at 7.4 (medians; the
# quartiles 0.05 - 0.08 either side): a dome, h (1 - (r / r0)^2) under them by the flowers' few cm.
# h: m over the ground at its middle, r: where it meets the ground, inside the lawn's edge.
# blender/town.py island() draws it; the 5 m grid under it stays flat
ISLAND_MOUND = dict(h=0.72, r=7.0)
# BED goes out as campus.json town.island.bed: the ground's shader (web/src/terrain.js) paints its dark band round
# the island's middle under the flowers (painting keeps every planting draw); the mound and the flowers are shrubs
# (layout: shrubs, the first 23 in the 23 places May 1996's pansy border had, the rest at the shrubs' end)
# 52158 solved again (2026-11-14, 고증 4.10.3): its camera stood on 그랜드백화점's roof, west of the island, not on
# 그레이스's.  Through it the pole's foot is 6.7 m north-north-west of the island's middle (bearing 331°), its mast
# arm about 6 m up; the scans of 27/18 and 27/19 put the arm's far end at (-74.6, -984.5), 6.85 m up (the two
# frames' rays 0.02 m apart): the arm reaches north (bearing 10°), 10.5 m, the lamps facing west (the arm to their
# right).  (Before: (-72.9, -993.8), the arm north-east, from the camera solved on 그레이스's roof)
ROT_POLE = dict(at=(-76.55, -995.0), face=280.0, reach=10.5)        # bearing the lamps face; the arm to their right
# 「연세대」 on the road north-west of the island (the scans of 27/18 and 27/19: a block of three letters stacked north to
# south, each long east - west, (-82.1 .. -79.1, -991.4 .. -994.3) in both; 52158 on its camera solved again from the
# scan's paint puts it 0.5 m off; 52142 · 52145 have the same white block): its middle, the bearing its top points along
# (the drivers who read it head that way: east, 52158), letters 0.95 m across and 3.0 m long
ROT_LETTERS = dict(c=(-80.65, -993.0), up=88.0, w=0.95, h=3.0)
# The wedge round the island (27/18, 1997-07): road, not a corner.  On it a U-turn loop round the island (the scans'
# arrows: in on its east side heading south, round its south, out up its west side heading north), its outer edge a
# yellow line from the west side's straight run along 서강로's lanes round to the top, a hatched triangle at its
# north-east and a small one in its southern tip; east of it a turning lane from 신촌로 down into 서강로, its kerb past a
# white kiosk to the crossing in front of 외환은행.  ROT_APRON: the road the wedge adds to the arms' (the turning lane's
# kerb on its east); ROT_D the loop's yellow edge (an open line), ROT_D_TRI its triangles, ROT_D_ARROWS the arrows
ROT_APRON = [(-95.0, -975.0), (-44.0, -975.0), (-44.0, -983.5), (-49.5, -990.0), (-50.0, -1000.0), (-53.0, -1008.0),
             (-58.0, -1016.0), (-65.0, -1025.0), (-73.0, -1034.0), (-79.0, -1040.0), (-79.5, -1052.0), (-95.0, -1052.0)]
ROT_APRON_WALK = 4.0           # the sidewalk east of the turning lane
# (the west side's run: 10.0 m east of 서강로's middle line and leaning with it, from -85.8 at its top; -83.1 straight
# down before 2026-11-14)
ROT_D = [(-85.8, -996.9), (-83.5, -1013.0), (-82.2, -1024.0), (-81.3, -1029.9), (-77.0, -1025.5), (-72.0, -1020.6),
         (-66.6, -1015.2), (-62.4, -1009.8), (-59.7, -1004.4), (-59.1, -1000.8), (-59.7, -996.0), (-61.3, -992.4),
         (-63.6, -989.4), (-66.0, -987.6)]
ROT_D_TRI = [[(-66.0, -987.6), (-53.4, -984.9), (-57.9, -996.6)], [(-81.2, -1020.6), (-76.8, -1020.6), (-80.0, -1026.0)]]
# [x, y of the head, the way it points (deg, compass)]
ROT_D_ARROWS = [(-63.0, -1001.5, 180.0), (-71.0, -1011.3, 270.0), (-82.7, -1000.0, 0.0)]
# The rest of the junction's paint (27/18 · 27/19, 2026-11-14, 고증 4.10.4 「노면 표시」; the same in 1995's 52142 · 52145):
# the yellow triangles (outline, the one inside), where they stand on the arms' asphalt as the game has it: 양화로's,
# north of its middle at the mouth, its tip outward.  (The wedges' hatched ones lie beyond the game's corners: 남은 한계.)
# Before 2026-11-14 every arm had one on its middle past its mouth, and a straight arrow in every lane coming in
ROT_TRI = [([(-115.0, -962.5), (-105.75, -963.5), (-105.75, -968.75)], [(-109.75, -964.5), (-107.0, -964.75), (-107.0, -966.5)])]
# the arrows [x, y of the head, bearing]: 서강로's lane in between its two solid lines heading north, the one west of
# the island heading west
ROT_ARROWS = [(-86.6, -1003.0, 356.0), (-77.9, -992.0, 262.0)]
# the turning guides of short dashes over the junction: 양화로 straight on east, 양화로 round south into 서강로's lanes,
# 1997년 신촌로 north-east across
ROT_GUIDES = [[(-115.0, -970.75), (-109.5, -973.0), (-102.0, -975.0), (-92.0, -977.0)],
              [(-113.5, -972.0), (-108.0, -976.5), (-104.0, -981.0), (-101.0, -986.0), (-98.0, -992.0), (-96.0, -998.0), (-95.6, -1000.3)],
              [(-120.5, -999.5), (-109.5, -991.0), (-101.0, -986.25), (-92.0, -983.0)]]
# 1997년 신촌로's crossing (both scans: one row of bars 6.8 m deep, 30 m out, its middle here) and the stop lines the scans
# put elsewhere than behind a crossing: 서강로's south of its crossing, 1997년 신촌로's 17 m short of its crossing
ROT_SW_CROSS = dict(c=(-141.0, -1016.2), depth=6.8)
ROT_STOP_AT = {'baekbeom': (-85.0, -1053.9), 'seogang': (-120.9, -1005.3)}
# 서강로's crossing in front of 외환은행 (27/18 and 26/17 of 1998: the one zebra of the junction's south side, 25 m further
# out than the mouth the game's rule gives, across the lanes and the turning lane's end; the scan: two rows of bars):
# its middle, depth, its two ends
ROT_S_CROSS = dict(y=-1046.75, depth=9.3, x=(-97.7, -81.6))
# the corner in front of 외환은행 between 서강로 and 1997년 신촌로 (27/18 · 27/19, the same arc in both within 0.3 m): its
# kerb round from 서강로's west kerb at the crossing to y -1031 and west along the forecourt's trees and parking, the
# asphalt of the junction out to it (ROT_S_FILL closes it through the road; ROT_S_CUT: what is behind it)
ROT_S_KERB = [(-98.15, -1047.0), (-98.6, -1045.0), (-99.1, -1043.2), (-100.5, -1039.0), (-102.6, -1034.8), (-104.5, -1032.6),
              (-106.5, -1031.6), (-111.0, -1031.0), (-118.0, -1030.6), (-124.0, -1028.5), (-130.0, -1025.5)]
ROT_S_FILL = [(-128.0, -1015.0), (-110.0, -1005.0), (-92.0, -1030.0), (-92.0, -1047.0)]
ROT_S_CUT = [(-98.7, -1049.0), (-131.0, -1046.0), (-131.0, -1026.0)]
ROT_S_WALK = 4.5
# ---- The three corners that were road in 1997 (2026-11-15, 고증 4.10.4.1 「쐐기의 연석」).  The game had rounded every
# corner's kerb (CORNER_R); the scans of 27/18 and 27/19 have the kerbs of the north-west (금강제화), north-east (the
# corner lot) and south-west (그랜드백화점) corners cut back straight behind a wedge of asphalt: lanes turning right
# round the corner, a hatched triangle between them and the through lanes, the bus stops' flat roofs along the kerb.
#   kerb: where the asphalt ends (the granite kerb's road face: a bright line 0.3 - 0.5 m wide with the gutter's dark
#     line at its foot, read across the kerb every 6 m; both scans within 0.1 m along the north-west corner's middle
#     18 m, the north-east one's east half and the stop in front of 그랜드, 1998's 26/17 within 0.4 m, the 1995 roof
#     photos 52142 · 52145 laid on the ground within 1 m), from one arm's kerb to the next arm's, the sidewalk on its
#     LEFT.  Under the trees south of 그랜드's stop (y -988 .. -999) the scans read only its two ends; there it is
#     52122's (1996.6, its camera solved 2026-11-22: 고증 4.10.4.1 「52122의 카메라」): the kerb face's foot every 20 px
#     on the road, less what the same reading gives where the scans read it (y -985 .. -988): 0.9 - 1.5 m east of the
#     line drawn before between the two ends
#   fill: closes the asphalt the wedge adds, through the road
#   walk: the sidewalk behind the kerb, m (the stops' roofs of the scans are 5 - 6 m deep on it)
#   back: m the kerb's first run is carried on backwards, so that the sidewalk's back edge meets the arm's
ROT_WEDGES = {
    'nw': dict(kerb=[(-136.47, -948.42), (-107.6, -934.25), (-105.9, -933.0), (-105.1, -931.3), (-104.83, -929.0)],
               fill=[(-100.0, -929.0), (-100.0, -962.0), (-136.0, -956.0)], walk=8.0, back=6.0),
    'ne': dict(kerb=[(-91.5, -930.56), (-70.0, -944.19), (-66.5, -946.4), (-63.0, -948.1), (-59.5, -949.1),
                     (-56.0, -949.45), (-50.0, -949.3), (-45.0, -949.05)],
               fill=[(-45.0, -958.0), (-96.0, -962.0), (-96.0, -930.56)], walk=8.0, back=6.0),
    'sw': dict(kerb=[(-143.96, -1005.81), (-142.3, -1004.0), (-143.3, -1001.0), (-144.6, -999.2),
                     (-145.2, -995.6), (-145.9, -993.3), (-145.95, -991.0), (-146.35, -988.2), (-146.2, -986.6), (-146.2, -981.0), (-146.6, -978.0),
                     (-147.6, -975.8), (-149.2, -973.9), (-151.0, -973.14)],
               fill=[(-150.0, -968.0), (-125.0, -975.0), (-112.0, -990.0), (-130.0, -1012.0)], walk=6.0, back=0.0),
}
# Their paint (27/19, the same in 27/18 where it sees them; 1995's 52142 · 52145 have the same shapes, the triangles
# and chevrons yellow, the rest white; 고증 4.10.4 「노면 표시」).  [kind, width, points]; closed shapes repeat their first
# point.  ROT_WEDGE_ARROWS: [x, y of the head, bearing], ROT_WEDGE_DASH: lines of 3 m dashes
_T = lambda *p: list(p) + [p[0]]
ROT_WEDGE_PAINT = [
    # north-west: the triangle between 양화로's lanes out and the two lanes turning into them from 연세로, the one inside
    # it, the thick line on from its west tip to the kerb's side, the two lanes' line (solid at its end)
    ('yellow', 0.4, _T((-121.7, -951.0), (-105.26, -952.8), (-104.94, -943.3))),
    ('yellow', 0.3, _T((-115.86, -950.08), (-107.28, -951.04), (-107.18, -946.72))),
    ('white', 0.45, [(-131.44, -946.72), (-121.7, -951.0)]),
    ('white', 0.15, [(-126.7, -948.4), (-119.54, -945.34)]),
    # north-east: the triangle between 연세로's lanes north and the lane turning into them from 신촌로, a line and a
    # small one inside it; the turning lane's outer line (the bus bay's edge) solid, dashed from where the bay opens
    ('yellow', 0.4, _T((-87.12, -943.2), (-86.88, -953.72), (-70.8, -953.2))),
    ('yellow', 0.3, [(-86.88, -947.32), (-78.0, -952.48)]),
    ('yellow', 0.3, _T((-84.92, -950.72), (-80.2, -952.6), (-84.92, -952.72))),
    ('white', 0.4, [(-86.1, -938.6), (-86.3, -941.0), (-87.12, -943.2)]),
    ('white', 0.15, [(-81.8, -940.72), (-78.0, -943.0), (-74.0, -945.6), (-70.0, -947.72), (-68.2, -948.48)]),
    # the taxis' stand south of it: three lanes behind a slanted line at their heads, the band of chevrons between
    # them and 신촌로's lanes in (its outline; the chevrons: ROT_NE_CHEVRONS)
    ('white', 0.4, [(-86.88, -953.72), (-85.0, -963.8)]),
    ('white', 0.15, [(-84.8, -958.0), (-62.4, -956.6)]),
    ('white', 0.15, [(-84.0, -961.0), (-66.8, -959.92)]),
    ('yellow', 0.3, _T((-85.0, -963.8), (-56.0, -962.0), (-83.6, -970.0))),
    # south-west (그랜드 앞): the triangle between 양화로's lanes in and the three lanes that leave them south-east (its
    # side to the junction doubled), the one inside it; the three lanes' lines and their stop line; the V between them
    # and the lane turning into 1997년 신촌로; that lane's stop line from the kerb
    ('yellow', 0.4, _T((-136.0, -978.1), (-114.8, -984.3), (-121.3, -989.9))),
    ('yellow', 0.3, [(-115.5, -984.95), (-121.65, -990.2)]),
    ('yellow', 0.3, _T((-127.8, -982.4), (-119.05, -984.85), (-122.0, -987.1))),
    ('white', 0.15, [(-135.57, -982.45), (-125.81, -990.25)]),
    ('white', 0.15, [(-139.07, -983.46), (-127.9, -992.38)]),
    ('white', 0.45, [(-123.6, -989.05), (-130.6, -994.3)]),
    ('yellow', 0.3, _T((-137.6, -988.35), (-128.7, -995.9), (-133.05, -999.4))),
    ('white', 0.45, [(-142.7, -1000.6), (-134.1, -995.4)]),
]
ROT_WEDGE_DASH = [[(-115.28, -943.36), (-105.58, -939.1)],                          # (north-west: the two lanes' line)
                  [(-67.6, -948.8), (-63.5, -949.9), (-58.5, -949.85)]]             # (north-east: the bay's mouth)
ROT_WEDGE_ARROWS = [(-126.22, -946.3, 251.0), (-122.42, -948.7, 251.0),              # north-west: into 양화로
                    (-84.0, -942.2, 307.0),                                         # north-east: into 연세로
                    (-127.8, -987.2, 128.6), (-129.8, -989.2, 128.6), (-131.8, -991.4, 128.6),      # south-west
                    (-138.6, -996.4, 173.0)]                                        # and into 1997년 신촌로
# the chevrons of the north-east band, their points (east): each two strokes back to the band's edges
ROT_NE_CHEVRONS = [(-81.4, -966.2), (-78.2, -965.6), (-75.4, -964.8), (-72.4, -964.4), (-69.6, -963.9), (-66.6, -963.5)]
# the painted island beside 그랜드's stop (an almond 10 m long, four bars across it), between the kerb's lane and the
# lane into 1997년 신촌로: its two tips, its width
ROT_SW_ALMOND = dict(a=(-142.8, -987.3), b=(-140.2, -997.3), w=1.75)
# 양화로's and 신촌로's stop lines in (27/19: the thick lines at the heads of their queues, at 그랜드's triangle and at
# the taxis' stand): a point on each
ROT_STOP_AT.update({'sinchon_w': (-115.3, -975.0), 'sinchon_e': (-82.6, -972.0)})
ROT_STOP_PAINTED = {'sinchon_w', 'sinchon_e'}
# the lamps the scans have at the wedges' kerbs (their posts' feet where 27/18 and 27/19 agree, the arms seen leaning):
# [x, y, the prop's turn]: where 양화로's north kerb bends into the north-west wedge, at 연세로's east kerb before the
# north-east one.  (The rule's lamps along the arms that stood in the wedges are left out, layout)
ROT_LAMPS97 = [(-140.4, -945.6, 5.97), (-91.3, -926.5, 4.707)]
ROT_WEDGE_PAINT += [('white', 0.45, [(-114.8, -984.3), (-115.8, -969.8)]),          # 양화로's stop line (in)
                    ('white', 0.45, [(-83.6, -970.0), (-81.6, -974.6)]),            # 신촌로's, south of the chevrons
                    # (and the line between 신촌로's two lanes in beside the band: 1.6 m north of the arm's line in both scans)
                    ('white_dash', 0.12, [(-76.0, -970.0), (-73.4, -969.65), (-67.76, -968.87), (-60.1, -967.1), (-56.5, -966.0)])]
# (2026-11-22, 고증 4.10.4.1 「52122의 카메라」) the yellow double triangle at 1997년 신촌로's mouth, north-east of its
# north-west kerb's corner: 52122 (1996.6) has it, both scans the same outline (west and north corners and the inner
# one's within 0.2 m; the south-east corner under a parked bus in both, where the two sides' lines meet)
ROT_WEDGE_PAINT += [('yellow', 0.4, _T((-122.8, -1014.8), (-115.5, -1010.2), (-111.8, -1018.0))),
                    ('yellow', 0.3, _T((-116.95, -1012.8), (-119.7, -1014.4), (-115.45, -1015.66)))]
# (arm, side): the rule's lane lines begin this far out (신촌로's north half: the taxis' stand and the chevrons' band)
ROT_LANE_FROM = {('sinchon_e', 1): 47.0}
# 신촌로's three lanes in at their heads: [m off the painted middle, s of the lane's end]: two south of the band, the
# third the taxis' south lane up to the slanted line
ROT_E_LANES = [(0.9, 17.0), (3.6, 17.0), (12.7, 14.5)]
# and through to 양화로 (2026-11-15, the cars run for half an hour: 고증 4.10.2 「신호와 차」): the double triangle at its mouth
# (ROT_TRI: 1.6 - 6.8 m north of the painted middle from s 5.6 to its tip at s 16.5) stood across the second of the
# three lanes and the first one's side.  [m north of the painted middle at the mouth, s on 양화로 to which it holds
# that, s from which it is on its own lane again]: the first passes between the triangle and the middle line, the
# other two north of it, and they spread to their lanes beyond its tip.  ROT_W_OUT: s where their points on 양화로 begin
ROT_W_MOUTH = [(0.7, 12.0, 20.0), (8.5, 18.0, 30.0), (11.6, 18.0, 30.0)]
ROT_W_OUT = 2.0
# the lanes turning right through the wedges: [s where the lane leaves its arm, the turning lane's middle (27/19: between
# its painted lines; the last but one point its stop), s where it joins the arm out].  (e_n's last point, past its stop:
# where its smoothed line rounds the kerb's corner at (-91.5, -930.56) 1.6 m off it, as it keeps off 연세로's kerb on to
# its outer lane; at (-92.9, -929.0) before 2026-11-15 the line passed 0.6 m from the corner, a car's side over it)
ROT_TURNS = {
    'w_sw': (50.0, [(-147.0, -972.6), (-143.5, -976.0), (-140.5, -981.5), (-139.4, -987.0), (-138.9, -992.0), (-138.6, -997.5),
                    (-139.6, -1002.0)], 46.0),
    'e_n': (58.0, [(-53.0, -952.7), (-60.0, -951.7), (-66.0, -950.6), (-70.0, -950.0), (-74.0, -948.0), (-78.0, -945.6),
                   (-81.5, -943.3), (-84.3, -941.0), (-87.0, -937.2), (-90.6, -933.0), (-94.4, -931.0)], 36.0),
    'n_w': (34.0, [(-104.2, -933.0), (-105.6, -936.6), (-109.0, -938.6), (-115.0, -940.9), (-121.8, -944.3), (-126.2, -946.3),
                   (-131.0, -948.4), (-136.0, -950.6)], 46.0),
}
# no zebra across 연세로's, 양화로's or 신촌로's mouths in July 1997 (27/18: their empty halves bare; 1998-10 has one
# across 연세로): the walkers went under, by 신촌역's passages
ROT_NO_ZEBRA = {'yonsei', 'sinchon_w', 'sinchon_e'}
ROT_STOP_E = 59.0              # 신촌로's south bus stop, m out along it (rot_stops): east of the wedge
# 연세로's crossing between the junction and the bridge, with its own signals (고증 4.10.1 「건널목」): the 1997-07-28
# scan of 26/16, with 1996-11-28 27/17 · 27/18 and 1998-10-08 26/17 within 0.2 - 0.6 m: two rows of bars, y -786.9 ..
# -778.8 with 0.6 m between them; the stop lines (0.5 m, each from its south edge) of the cars going south y -775.8,
# west half, and of those going north y -790.9, east half.  MID_CROSS_Y_RNG: the crossing the game had till then
# (y -790 .. -785.5, from 52006 · 51979), what the 연세로 row's trees are decided round
MID_CROSS = dict(y=(-786.9, -778.8), gap=0.6, stop_n=-775.8, stop_s=-790.9)
MID_CROSS_Y_RNG = -790.0
GRAND_YARD_BOX = (-178.0, -1012.0, -142.0, -972.0)     # the 그랜드백화점's forecourt the walker may cross (layout)
# the junction's landmarks (the photos 52095 · 52108, 서울연구원 labels; 연세춘추, 위키백과): OSM outline (a point in
# it), storeys, wall band (blender/town.py), the sign cell of sign_sinchon2 and its height
LANDMARKS = [
    dict(name='그레이스백화점', at=(-190.0, -875.0), lv=10, wall=1, sign=12, sign_h=2.6),     # 1992, 현대 from 1998
    dict(name='그랜드백화점', at=(-176.0, -997.0), lv=10, wall=1, sign=13, sign_h=2.6),       # 1994
    dict(name='외환은행', at=(-119.0, -1054.0), lv=13, wall=2, sign=15, sign_h=2.0),          # the south wedge's tower
]
# Their tops and outlines from the 1997 frames (고증 4.10.5): the scans of 27/18 and 27/19 (the same day's light) and
# 1998's 26/17 resampled at the roof's height, an edge's height where its picture
# stands still from frame to frame (the frames that see past it), a roof's where the windows match.
# - 그레이스: its walls' top 74.1 m (the parapet round the roof, south side 74.1 - 74.6 in three frames, west 73.5),
#   the roof inside 69.9; the outline the parapet's (north 1.75 m inside the old foot line, the west turned 2.2 deg,
#   the east OSM's).  Its north end was its car park in 1997 (painted bays in 27/18).  No upper floor set back
# - 그랜드: OSM's outline (그랜드플라자, its round north-east side) the ring of its top floor, 69.6 m, round a roof
#   garden 64.3 m (GRAND_COURT)
# - 외환은행: OSM's outline (「144」), its walls' top 55.2 m (the north edge where three frames meet, the roof 55.7); the
#   machine room over it 58.2 (what 58.0 was), the stair head 61.2, a round tank
# The blocks keep their storeys (their walls' draws from blender/town.py's stream; the 13th field stretches a storey to
# the top) but are drawn as LM_SHAPE in blender/town.py landmarks() (town['landmarks']), not as boxes
LM_TOP = {'그레이스백화점': datum.up(-191.03, -882.35, 74.13), '그랜드백화점': datum.up(-175.37, -996.2, 69.63), '외환은행': datum.up(-118.81, -1053.76, 55.18)}
GRACE_1997 = [(-225.27, -896.16), (-179.28, -917.39), (-157.10, -865.66), (-203.55, -849.16)]
# (the old outline, 2026-11-14: the walls' feet in 27/18 and 1998's 26/17)
GRACE_1997_OLD = [(-227.8, -895.6), (-179.5, -917.9), (-158.5, -863.3), (-203.0, -847.5)]
# (OSM's, its spike taken out; and, 2026-11-15, the bump on its south-west side, (-191 .. -181, -1005 .. -1016): no roof
# at the ring's height there in the scans of 27/18 · 27/19 (the windows match 0.84 - 0.87 on the ring, under 0.4 on the
# bump, what lies below it leaning two ways), the side straight from (-190.3, -999.0) to the south corner)
GRAND_1997 = [(-188.0, -989.7), (-190.3, -999.0),
              (-175.1, -1020.4), (-159.4, -1008.5), (-163.9, -1002.7), (-160.1, -1000.5), (-160.7, -996.1), (-161.4, -992.6),
              (-162.9, -989.3), (-163.3, -988.4), (-167.6, -982.2), (-168.3, -981.1), (-171.2, -978.1), (-173.9, -975.8),
              (-177.0, -973.3), (-180.9, -976.4), (-182.7, -979.0), (-183.8, -978.6), (-186.5, -978.6), (-188.6, -979.7),
              (-189.7, -982.1), (-191.0, -985.4), (-190.2, -987.6), (-189.2, -989.3)]
# What stands on its roof's south end (고증 4.10.5 「그랜드백화점의 옥상 상자」): the cooling towers' screen, a white box
# with a blue band round its foot (서울연구원 52119, 1996.6, and 31662, 1999.7, from the east: both faces, the box
# standing out over the walls below).  From the scans of 27/18 · 27/19 and 1998's 26/17: its walls' top 7.9 m over the
# ring's roof (the white faces' upper edge where three frames meet, 7.7 - 8.4), the white down to 4.4 m over it (their
# lower edge, 4.2 - 4.6), the blue band under that to 2.4 m (52119 · 31662: white 3.7 m, blue 2.0 m); its outline at the
# top (it hangs 0.45 m out over the south-east wall and 1.0 m over the south-west one, as the photos show); inside it
# a round cooling tower, and a larger one north-west of it on the roof (their rims 4.7 and 6.6 m over the roof)
GRAND_PEN = dict(outline=[(-175.50, -1021.52), (-168.37, -1016.12), (-177.46, -1004.12), (-184.60, -1009.53)],
                 top=7.9, band=(2.4, 4.4), wall=0.25,
                 towers=[(-176.7, -1011.0, 2.1, 4.7), (-183.0, -1002.6, 3.1, 6.6)],     # [x, y, r, rim over the roof]
                 boxes=[(-172.5, -1014.6, 3.0, 3.0, 0.6486, 6.9)])                      # (a white box inside it)
GRAND_COURT = [(-186.8, -988.5), (-176.0, -988.8), (-172.0, -991.0), (-168.5, -994.0), (-166.8, -998.5), (-167.5, -1003.0),
               (-173.0, -1008.5), (-178.0, -1007.0), (-186.5, -999.0)]                 # (27/18 · 27/19 at 63 m)
KEXIM_1997 = [(-130.2, -1059.9), (-114.7, -1062.7), (-102.4, -1061.3), (-103.8, -1048.7), (-107.1, -1048.0), (-127.4, -1043.7),
              (-137.7, -1052.6)]                                                       # (OSM 「144」, counter-clockwise)
# What blender/town.py draws of each (the 1995 · 1996 photos 52095 · 52097 · 52130 · 52114 · 52119 · 52135, 서울연구원):
# - 그레이스: white tile; at its south-east corner a round green glass shaft from the second floor to the roof (`glass`:
#   the corner and how far it is cut back along each side), five steel pipes with crowns up the east face (`pipes`: the
#   side, from the corner), three rows of square frames over them, three green window bands on the south face near the
#   corner (`bands`), the cooling towers along the roof's north side (`boxes`)
# - 그랜드: white tile, the video screen on the round face (`screen`: on side i, w, h, m below the top to its middle;
#   10 x 8 m as the paper had it when 그랜드마트 신촌점 opened, 「정문 위에는 가로 10m, 세로 8m 짜리 대형
#   아스트로비전」 경향 1995-09-29: 12 x 8.5 before 2026-11-17), a dark glass strip up the south end of the
#   south-east face (`strip`: side, m along it, width)
# - 외환은행: black glass storeys with dark bands (`floors`), the machine room, stair head and tank on the roof
# Sides: side i runs from outline[i] to outline[i + 1].  boxes: [x, y, L, W, angle, height over the roof]; tanks: [x,
# y, r, height]; signs: the cell of sign_sinchon2 on side i, m along it to its middle (None: the side's middle), width,
# height, its middle `top` m below the top or `up` m over the ground, `off` m out from the side's line (a flat sign on
# a round face stands off by the bulge).  front: points on the walk before its doors (그레이스: its south-east corner on
# 양화로; 그랜드: the round face; 외환은행: the north face's east half and the corner) whose ground sets its floor
LM_SHAPE = {
    '그레이스백화점': dict(kind='grace', outline=GRACE_1997, deck=datum.up(-191.03, -882.35, 69.93), parapet=1.0, glass=(1, 5.5), pipes=1, bands=0,
                     front=[(-183.5, -918.2), (-178.0, -915.2)],
                     boxes=[(-188.8, -865.0, 46.0, 4.5, -0.333, 2.2)],
                     signs=[dict(cell=12, side=1, at=15.0, w=14.3, h=2.6, top=2.1)]),
    '그랜드백화점': dict(kind='grand', outline=GRAND_1997, court=GRAND_COURT, deck=datum.up(-175.37, -996.2, 64.33), screen=(9, 10.0, 8.0, 19.0),
                    strip=(2, 2.5, 2.5), pen=GRAND_PEN, signs=[],
                    # (2026-11-16: the mark and words on the tiles, the banners, the poster [side, w, h, its middle m
                    # below the top] and the fascia's sides, blender/town.py _grand; 52135 · 52119 · 52095)
                    banners=[(7, 'gm_ban0'), (12, 'gm_ban1'), (13, 'gm_ban2')], poster=(11, 5.6, 7.6, 29.0),
                    fascia=[5, 6, 7, 9, 11, 12, 13],
                    front=[(-159.8, -998.0), (-161.6, -990.0), (-165.9, -983.3)]),
    '외환은행': dict(kind='kexim', outline=KEXIM_1997, floors=10, front=[(-110.0, -1046.4), (-102.9, -1052.0)],
                 boxes=[(-114.5, -1053.7, 13.5, 3.6, -0.207, 3.0), (-113.5, -1059.0, 6.5, 4.0, -0.207, 6.0)],
                 tanks=[(-127.2, -1052.5, 1.9, 3.5)],
                 signs=[dict(cell=14, side=4, at=12.7, w=12.0, h=2.0, top=1.3), dict(cell=15, side=4, at=12.7, w=8.5, h=1.7, up=9.6)]),
}
# ---- 연세로's mouth, its two corners and the lot east of them (2026-11-16, 고증 4.10.7), drawn as the landmarks are:
# - 금강제화 (north-west): the scans of 27/18 · 27/19 have one flat roof 32 - 35 m (four storeys over the 20 m walk)
#   from x -137 to -107 between y -914 and -928, along 양화로 (the 1996 photos 52206 · 52006: its long south face, the
#   shoe shop's maroon arch over the ground floor, clinics', a 법무사's and 바둑's boards up the floors, a round drum on the
#   roof's west end, 34 - 35 m in the scans); OSM 356215992's outline from x -137.5 east.  The row box (20 m along
#   연세로) it was keeps its draws
# - 홍익문고 (north-east): its row box (OSM 356219103), six storeys (52004 · 52006: five rows of windows over the
#   ground floor), the sign along the top of the south face.  Its parapet's top 37.45 m (2026-11-17): the leaf-off
#   scans of 1996 (26/17 · 27/18), taken before the tower south of it rose, see its roof's west edge meet there from
#   both sides, and their windows on the roof give 37.5 - 37.9; 1999's 39.3 (26/17 · 27/17) is the blue shed on its
#   roof in 31669 (고증 4.10.7 「홍익문고의 높이」)
# - the lot south of it: the tower going up in July 1997 (엘리트 빌딩 now, 1998's 삼성증권 · 맥도날드 신촌점 1999.7
#   31669 · 33000): OSM 356219104's outline, 15 storeys; the scans have its frame's roof at 74.5 m (27/18 · 27/19,
#   27/18 · 27/20 and 27/19 · 27/20 agree to 0.5 m: 56 m over the ground, 15 storeys of 3.65 m), a ring over the
#   cylinder by 연세로 about 83 m, and a crane's jib about 80 - 88 m out over 홍익문고 and 연세로
KUMKANG_1997 = [(-137.5, -913.4), (-115.9, -913.4), (-115.9, -913.9), (-109.6, -913.9), (-109.5, -923.6), (-110.3, -925.0),
                (-121.2, -927.7), (-132.5, -932.2), (-137.5, -923.4)]
KUMKANG_TOP = (-123.0, -920.0, 33.0)            # (x, y, 해발 of its parapet's top)
KUMKANG_FRONT = [(-112.0, -927.6), (-121.0, -930.3)]
HONGIK_FLOORS = 6
HONGIK_TOP = (-83.0, -909.3, 37.45)             # (x, y, 해발 of its parapet's top)
# its back (east) wall (2026-11-17): the leaf-off 1996 26/17, which does not see that wall, has the roof end at x -74.2
# .. -75.4 at its measured top; 1999's 26/17 · 27/17 -73.4 .. -74.0; the 2005 survey's outline -74.0 .. -75.9.  The row
# box ended at -77.6 (OSM 356219103, 11 m deep).  Its front stays the row's (고증 4.10.1 「집마다 다른 앞벽」)
HONGIK_BACK_X = -74.5
TOWER97 = dict(outline=[(-68.9, -908.5), (-54.8, -919.1), (-61.3, -926.9), (-62.1, -926.4), (-67.9, -933.5), (-70.9, -931.3),
                        (-85.0, -921.2), (-85.5, -918.9), (-85.0, -916.8), (-84.0, -914.8), (-81.5, -913.7), (-79.4, -913.7),
                        (-77.2, -914.9), (-75.4, -916.4)],
               top=(-70.0, -921.0, 74.5), floors=15, front=[(-86.8, -923.6)],
               cyl=(-80.6, -918.9, 4.9),               # (the round end by 연세로: OSM's arc)
               crown=(5.0, 3.4, 8.5, 6.0),             # (its stair drum's height over the roof and radius, the ring's height and radius)
               crane=(-65.5, -921.5, 295.0, 38.0, 13.0, 11.5))   # (x, y, the jib's bearing, jib, counter-jib, its top over the roof)
# ---- 2호선 신촌역's stairs as they stood in July 1997 (2026-11-15, 고증 4.10.2 「지하철 출입구의 지붕」).  The white roofs
# of the scans 27/18 · 27/19 at the four corners (five of 11 x 5 m and the 「white kiosk」 east of the island) are the
# stairs' canopies, not bus shelters or kiosks: 서울연구원 52206 (1996.6, from 외환은행's roof: a tiled stairwell walled to
# the hip under a flat white roof on posts, someone going down, a black sign box on the roof's street end), 52146
# (1995.10: both of 양화로's north walk, the buses pulled in at the kerb beside them), 52141 · 52105 (the north-east
# pair), 52204 (1996.6: two before 한일은행, a small eight-sided kiosk between them), 52145 (before 그랜드백화점).
# The roofs resampled at their own height in both scans (within 0.3 m of each other): [number: the roof's middle, the
# way from its closed end to its open end where the sign box stands (deg, from east counter-clockwise), the roof's
# length and width].  The numbers are OSM's of today (EXITS in layout: the four north ones 2 - 6 m from OSM's nodes);
# 8's (2026-11-17) on 양화로's south walk off 그랜드백화점's north tip, 3.5 m from OSM's node: the same white roof with
# its dark sign box at the west-north-west end in 27/18 · 27/19 and in 1996's 26/17 and 1998's 26/17 (the four
# within 0.9 m), its top 21.45 m (27/18 · 27/19, 0.95 - 0.97).  Their tops 2.8 - 3.1 m over the road (the scans'
# windows, 0.86 - 0.99)
ENT97 = {1: ((-130.8, -941.9), 205.7, 10.8, 4.5), 2: ((-112.8, -932.6), 26.4, 10.4, 4.65),
         3: ((-81.55, -933.6), 151.4, 10.25, 4.4), 4: ((-63.7, -943.7), -27.6, 10.3, 4.9),
         5: ((-31.3, -978.4), 21.4, 10.0, 4.0), 6: ((-45.6, -994.6), -98.8, 10.35, 5.6),
         7: ((-150.45, -984.75), -90.0, 9.8, 5.8), 8: ((-164.6, -970.15), 160.4, 9.6, 3.9)}
ENT97_LATE = {8}               # (found after the lamps were set: a lamp under it moves, none goes)
ENT97_ROOF = 2.9               # the canopy's top over the walk (m)
ENT97_KIOSK = (-38.8, -982.95, 2.4)    # the eight-sided kiosk between 5 and 6 (52204: a green hipped roof; the scan: 4.8 m across)
# Over 연세로's mouth (52206 · 52141 · 52140, 1996.6 - 8; the scan of 27/19 has the east arm, (-88.8, -928.4) to
# (-97.6, -929.1)): from a pole on the north-east corner an arm west over the lanes coming up from 서강로, 6.0 m over
# the road, two signal heads on it (x -95.9, -92.8) and the junction's name plate; from a pole on the north-west
# corner, behind the kiosk east of stairs 2, an arm east with the blue direction sign of three panels, 「양화대교 ← ·
# 연희IC 연세대 ↑ · 아현교차로 →」, 5.3 x 1.25 m, its foot about 5 m up (its depth, so its height, +- 2 m: 52140 has it
# beyond the signal arm).  Both face south.  52007 (1996.8, from the ground south of the mouth: 고증 4.10.6) reads the
# panels and has the heads of four lamps (red, amber, the left arrow, green: `heads`' 7th field) and between them a
# plate 「좌회신호시 / 동교동 창전로」 (lplate: x, w, h; its middle at the arm, 5.9 m up as the web hangs the arm)
MOUTH_SIGNAL = dict(pole=(-88.8, -928.4), heads=(-95.9, -92.8), plate=(-90.3, 1.5, 0.7), h=6.0, lplate=(-94.45, 1.17, 0.8))
MOUTH_SIGN = dict(pole=(-104.2, -925.5), x=(-102.9, -97.6), h=1.25, z0=5.0)
# The same make for the cars that cross the junction from 양화로 into 신촌로 (2026-11-17, 52208, 1996.8, from the roof
# of 외환은행 east along 신촌로: 고증 4.10.6): a pole on the corner of the walk east of the turning lane, west of the
# kiosk, its arm out north-west with two heads facing west and the 「신촌로터리」 plate.  The pole: the arm's root
# back-projected at 6.0 m over the road (the camera solved from stairs 5's roof corners, 4 px; +-0.5 m in that height
# moves it 1.3 m along the ray from the south-west); the arm's reach from its length in the photo (about 7 m)
FAR_E_SIGNAL = dict(pole=(-45.0, -983.4), face=180.0, reach=7.0)
# And for the cars from 신촌로(동) on the far side, in front of 그랜드 (2026-11-22, 고증 4.10.4.1 「52122의 카메라」):
# 52122 (1996.6, telephoto, from the same roof south-east of the island as 52114; solved on the south-west wedge's
# paint, the island and 그랜드's corners, 4 px) has two poles on 그랜드's walk, each an arm with two heads of four
# lamps facing east (both red).  pole: the foot (52122's ray; the south one where it crosses 0.65 m behind
# 1997년 신촌로's north-west kerb, 52139's foot at the crossing's end; the north one from its foot over the kerb in
# 52122), face: compass bearing the lamps face, heads: m along the arm to each head (+: to the lamps' right, -: left)
GRAND_SIGNALS = [dict(pole=(-153.4, -1012.0), face=53.7, heads=(4.0, 6.4)),     # arm south-east over the lanes out
                 dict(pole=(-147.9, -991.9), face=78.0, heads=(-3.8, -6.9))]    # arm north over the wedge's lanes
# And on 양화로's north kerb at its mouth, where the north-west wedge's kerb begins (2026-11-22 셋째, 고증 4.10.4.1 「양화로
# 어귀 북쪽의 신호 기둥」): the scans of 27/18 · 27/19 have a pole with a straight arm 10.3 m long reaching south-south-west
# over 양화로's lanes out, 5.9 m up (its root and end where both frames agree within 0.15 m), 3 m east of the lamp
# (ROT_LAMPS97); 서울연구원 52115 (1996.6) · 52128 (1996.8) show it with three heads of four lamps facing east-south-east
# (red with 그랜드's) and a 「신촌로터리」 plate by the pole: 신촌로(동)'s cars' far-side signal, as 그랜드's.  reach: the
# arm's length; heads: m along it to each head (the photos' heads on the arm)
YH_SIGNAL = dict(pole=(-137.5, -946.6), face=106.3, reach=10.3, heads=(3.8, 7.05, 10.0))
LANE_W = 3.25
# 연세로's two lanes each way, their middles m off its line (2026-11-15): 4.10.1's 13 m of carriageway, two lanes of
# 3.2 - 3.3 m a way (the scan of 27/19 at the mouth: the southbound queue's two rows 1.4 and 4.4 m west of the
# painted middle, the line between them 2.7 - 2.85 m).  The other arms' rule (0.3 + LANE_W (k + 0.5): 1.925, 5.175)
# put a bus's side 0.1 m from 연세로's kerbs and the cars turning into 1997년 신촌로 against the paint at 양화로's mouth
YRO_LANES = (1.7, 4.85)
# 연세로's side streets (OSM: 명물길, 연세로4길, 연세로2길 on the east; 연세로5길, 연세로 (to 신촌로), on the west):
# where its shop rows break, y of the gap's two sides
GAPS = {1: [(-695.0, -703.0), (-738.0, -747.0), (-771.0, -779.0), (-885.0, -893.0)],
        -1: [(-736.0, -746.0), (-779.0, -787.0), (-884.0, -892.0)]}
Y_ROWS = -640.0                # gate_town's rows end here; ours start
MODERN = set()                 # OSM outlines (osm_rotary.json) that are later than 1997: left out

# ---- 연세로's shop rows from y -640 to the junction, their sidewalks, wall signs and the festival's banner
# (고증 4.10 「연세로의 건물과 나무」; the yro_ functions at the end of this file).
# The sidewalk: OSM's front walls today stand 10.3 m (west) and 11.2 m (east) from 연세로's line here (medians, the
# parcels did not move when the street became a transit mall in 2014), 21.5 m wall to wall; the 1996 photo from 노고산동
# (52006) has walk : carriageway : walk = 0.20 : 0.55 : 0.25 at the junction's mouth; 서울시 2013 has 3 - 4 m walks.
# With the 14 m carriageway of four lanes kept, 3.75 m.  North of y -640 (gate_town, 4.8) OSM's walls are 23.5 m apart
# and gate_town's 5 m stays.
YRO_WALK = 3.75               # (the walk of the old line, 2026-11-11 .. 14: for the streams' decisions)
YRO_OLD_WALK = 5.0             # (the walk the rows had before: the old rows are still drawn, unused, for the streams)
# 2026-11-14 (고증 4.10.1): 13 m of carriageway (ARMS half 6.5), the fronts 10.5 m west and 9.5 m east
# of its middle (the 2008 · 2010 skyview's crossings and kerbs, 52006's mouth, 홍익문고's outline)
YRO_WALK_W, YRO_WALK_E = 4.0, 3.0
ARMS['yonsei']['walk'] = (YRO_WALK_W + YRO_WALK_E) / 2
# 연세로's lanes are not painted: only the double yellow middle line between the junction and the bridge, two cars
# abreast each way (1996: 51979 · 52006; Kakao roadview 2008-08 · 2009-03, 고증 4.10.1 「로드뷰로 잰 차도 폭」, which
# also counted the 13 m between the kerbs on a crossing's 1 m bars).  A solid white line between the two lanes only
# on the last stretch into the junction (52006's mouth, the 2008 roadview at y -945)
YRO_LANE_SOLID = 25.0


def _xy(lat, lon):
    return ((lon - gt.LON0) * 111320 * math.cos(math.radians(gt.LAT0)), (lat - gt.LAT0) * 110574)


class Arm(gt.Line):
    """an arm's middle line from the junction outward, its left normal at each point (gate_town.Line)"""
    def __init__(self, name, d):
        super().__init__(gt._resample(gt._chaikin(d['pts'], 2), 2.0))
        self.name = name
        self.half, self.walk, self.lanes = d['half'], d['walk'], d['lanes']
        self.walk_l = d.get('walk_l', d['walk'])           # (the walk on the +n side where it differs: 1997년 신촌로)

    def at(self, s):
        k = int(np.clip(np.searchsorted(self.cum, s), 1, len(self.cum) - 1))
        f = (s - self.cum[k - 1]) / max(1e-9, self.cum[k] - self.cum[k - 1])
        p = self.P[k - 1] + (self.P[k] - self.P[k - 1]) * f
        t = self.T[k - 1] + (self.T[k] - self.T[k - 1]) * f
        t = t / np.linalg.norm(t)
        return p, t, np.array([-t[1], t[0]])

    def poly(self, o0, o1, s0=0.0, s1=None):
        """the strip between offsets o0 and o1 (left +) from s0 to s1"""
        s1 = self.cum[-1] if s1 is None else s1
        ss = np.arange(s0, s1, 2.0).tolist() + [s1]
        a = [tuple(self.at(s)[0] + self.at(s)[2] * o0) for s in ss]
        b = [tuple(self.at(s)[0] + self.at(s)[2] * o1) for s in ss[::-1]]
        return Polygon(a + b).buffer(0)


def arms():
    return {k: Arm(k, d) for k, d in ARMS.items()}


def _bb_arm():
    """서강로's arm on the scans' line: the carriageway's middle 1.25 m west of the painted one (BB_C), half 7.75"""
    c = Arm('c', dict(half=1, walk=1, lanes=1, pts=BB_C))
    o = (BB_KERB_W - BB_KERB_E) / 2
    pts = []
    for q in BB_C:
        p, t, n = c.at(float(c.ls.project(Point(*q))))
        pts.append((round(float(q[0] - n[0] * o), 2), round(float(q[1] - n[1] * o), 2)))
    return dict(half=(BB_KERB_W + BB_KERB_E) / 2, walk=4.5, lanes=2, pts=pts, mid=o)


ARMS['baekbeom'] = _bb_arm()
# 1997년 신촌로 (남서) as the 1996 photos 52110 · 52111 · 52139 have its kerbs (2026-11-17, 고증 4.10.4.3 「1997년 신촌로(남서)의
# 두 연석」): their cameras solved on the paint of the 1997 scans (the crossing's bars and edges, the yellow middle, the
# lane lines; 52111's and 52139's apart came out at one place 0.6 m apart), the kerbs read off them to the road's own
# heights: the north-west one 12.4 m north-west of OSM's line (the arm's till then) from the crossing to s 75 (12.6 to
# s 92), the south-east one 4.5 - 5.2 m south-east of it (s 48 - 115): 17 - 17.8 m of carriageway, where the game had
# 20 m round the line.  The scans' painted middle runs 3.6 - 5.3 m north-west of the line (SG_MID, off the new one), the
# lane lines either side of it (SG_LINES): three lanes in (south-east), two out.  SEOGANG_RNG: the arm as it was, for
# what the random streams decide (the rule's mouths, the lamps' stations, the entrances' first places).  Its walks
# reach where the old ones did (north-west 2.05 m, south-east 9.9 m: the houses behind stay); nearer the junction than
# the crossing (SG_CORNER_S) the old asphalt south-east of the line stays (the scans' lanes in and turning lane there)
SEOGANG_RNG = dict(ARMS['seogang'])
SG_KERB_NW, SG_KERB_SE = 12.45, 4.6           # m off the old line
SG_CORNER_S = 45.8                            # (the south-east kerb's corner at the crossing's near edge: 52110)
SG_MID = [(0.0, 0.33), (57.0, 0.33), (63.0, 0.22), (69.0, 0.18), (75.0, 0.08), (81.0, 0.03), (87.0, -0.18), (93.0, -0.28),
          (99.0, -0.43), (105.0, -0.53), (111.0, -0.63), (117.0, -0.78), (123.0, -0.88), (129.0, -0.98), (135.0, -1.18),
          (141.0, -1.38), (1000.0, -1.38)]
# [(s, m off the painted middle), kind]: the scans' cross profiles (27/18 · 27/19, every 6 m from s 54 to 144)
SG_LINES = [([(0.0, 3.05), (54.0, 3.05), (102.0, 3.2), (1000.0, 3.2)], 'white_dash'),
            ([(0.0, 6.15), (46.0, 6.15), (54.0, 5.25), (99.0, 6.25), (141.0, 6.45), (1000.0, 6.45)], 'white_dash'),
            ([(0.0, -3.4), (57.0, -3.4), (99.0, -3.25), (141.0, -3.1), (1000.0, -3.1)], 'white_dash')]


def _sg_arm():
    """1997년 신촌로's arm on the photos' kerbs: the old line moved by the carriageway's middle"""
    c = Arm('c', dict(half=1, walk=1, lanes=1, pts=SEOGANG_RNG['pts']))
    o = (SG_KERB_SE - SG_KERB_NW) / 2
    pts = []
    for q in SEOGANG_RNG['pts']:
        p_, t_, n_ = c.at(float(c.ls.project(Point(*q))))
        pts.append((round(float(q[0] + n_[0] * o), 2), round(float(q[1] + n_[1] * o), 2)))
    half = (SG_KERB_SE + SG_KERB_NW) / 2
    return dict(half=half, walk=14.5 - SG_KERB_NW, walk_l=14.5 - SG_KERB_SE, lanes=2, pts=pts)


ARMS['seogang'] = _sg_arm()


def mid_of(k, s):
    """where arm k's painted middle line is, m off its line (+: its left of the outward way), s m out"""
    if k in ('sinchon_e', 'seogang'):
        t = np.array(SINCHON_E_MID if k == 'sinchon_e' else SG_MID)
        return float(np.interp(s, t[:, 0], t[:, 1]))
    return float(ARMS[k].get('mid', 0.0))


# ----------------------------------------------------------------------------- the ground
def patch(raw, Hn, half, step):
    """The near terrain south of the 5 m grid: raw(xs, ys) -> the ground on that grid as build_campus.py makes Hn
    (the 10 m model, cubic, smoothed the same way, over a block reaching 40 m into the grid so the smoothing sees the
    same ground).  Its top row is the grid's bottom row; the rows below take the difference over 30 m."""
    S = SOUTH
    xs = S['x0'] + np.arange(S['nx']) * S['step']
    ys = S['y0'] + np.arange(-6, S['ny'] + 8) * S['step']           # (6 rows south, 8 north of the patch)
    G = raw(xs, ys)
    Hs = G[6:6 + S['ny']].copy()
    i0 = int(round((S['x0'] + half) / step))
    edge = Hn[0, i0:i0 + S['nx']]
    d = edge - Hs[-1]
    f = np.clip(1.0 - (S['ny'] - 1 - np.arange(S['ny'])) * S['step'] / 30.0, 0, 1)
    Hs += d[None, :] * (f * f * (3 - 2 * f))[:, None]
    Hs[-1] = edge
    return Hs


def sample_s(Hs, x, y):
    S = SOUTH
    fx = (x - S['x0']) / S['step']
    fy = (y - S['y0']) / S['step']
    return float(ndimage.map_coordinates(Hs, [[fy], [fx]], order=1, mode='nearest')[0])


def in_patch(x, y):
    S = SOUTH
    return y < S['y0'] + (S['ny'] - 1) * S['step'] and S['x0'] <= x <= S['x0'] + (S['nx'] - 1) * S['step']


def streets(pl):
    """연세로 and the junction: the carriageways' union with its corners rounded, the sidewalks round it, the arms.
    pl: gate_town.plan's dict (성산로's south kerb: where 연세로 begins).  geo['rng']: the same with 연세로 on its old
    line (YONSEI_RNG_PTS), for what the random streams decide"""
    geo = _streets(pl, arms())
    A0 = arms()
    A0['yonsei'] = Arm('yonsei', {**ARMS['yonsei'], 'pts': YONSEI_RNG_PTS, 'half': 7.0, 'walk': YRO_WALK})
    A0['baekbeom'] = Arm('baekbeom', BAEKBEOM_RNG)
    A0['seogang'] = Arm('seogang', SEOGANG_RNG)
    geo['rng'] = _streets(pl, A0, gt.YONSEI_X_RNG, old=True)
    return geo


def se_widen(a):
    """the asphalt between 신촌로 (동)'s arm (-half) and its 1997 south kerb (SE_KERB)"""
    ss = np.arange(SE_KERB[0][0], SE_KERB[-1][0], 1.0).tolist() + [SE_KERB[-1][0]]
    out = [tuple(a.at(s)[0] + a.at(s)[2] * se_kerb(s)) for s in ss]
    back = [tuple(a.at(s)[0] - a.at(s)[2] * (a.half - 0.2)) for s in ss[::-1]]
    return Polygon(out + back).buffer(0)


def wedge_back(w, d=0.0, area=False):
    """a wedge's sidewalk (ROT_WEDGES): the line `walk + d` m behind its kerb, or (area) the strip between the two;
    the kerb's first run carried on backwards by `back` m"""
    k = [np.array(q) for q in w['kerb']]
    if w.get('back'):
        u = (k[0] - k[1]) / np.linalg.norm(k[0] - k[1])
        k = [k[0] + u * w['back']] + k
    ls = LineString([tuple(q) for q in k])
    return ls.buffer(w['walk'] + d, single_sided=True) if area else ls.offset_curve(w['walk'] + d)


def _streets(pl, A, yx=None, old=False):
    yx = gt.YONSEI_X if yx is None else yx
    road_ = pl['road']
    ks = road_.off(-gt.HW)
    y_top = float(np.interp(yx, ks[:, 0], ks[:, 1])) + 1.0        # (gate_town.layout's 연세로)
    s_top = float(A['yonsei'].ls.project(Point(yx, y_top)))
    s_kerb = float(A['yonsei'].ls.project(Point(yx, y_top - 1.2)))      # (성산로's south kerb)
    cw, walks = {}, {}
    for k, a in A.items():
        cw[k] = a.poly(-a.half, a.half, 0.0, s_top if k == 'yonsei' else a.cum[-1])
        walks[k] = yro_walk_poly(a, s_kerb, yx, old) if k == 'yonsei' else a.poly(-a.half - a.walk, a.half + a.walk_l, 0.0, a.cum[-1])
    road = unary_union(list(cw.values()))
    road = road.buffer(CORNER_R, join_style=1).buffer(-CORNER_R, join_style=1).union(road)
    # (the corners rounded: closing the union fills the wedges between the arms)
    if not old:
        # the island's wedge (1997: ROT_APRON) and the sidewalk east of its turning lane
        apron = Polygon(ROT_APRON)
        road = road.union(apron)
        kerb_e = LineString(ROT_APRON[2:11])
        walks['apron'] = kerb_e.buffer(ROT_APRON_WALK, single_sided=True).difference(road)
        # the corner in front of 외환은행 (ROT_S_KERB): asphalt out to its kerb, its forecourt behind it
        ks = LineString(ROT_S_KERB)
        road = road.union(Polygon(ROT_S_KERB + ROT_S_FILL)).difference(Polygon(ROT_S_KERB[::-1] + ROT_S_CUT).buffer(0))
        walks['s_corner'] = ks.buffer(ROT_S_WALK, single_sided=True).difference(road)
        # 1997년 신촌로 short of its crossing: the old asphalt south-east of its line (the lanes in, the turning lane)
        road = road.union(Arm('seogang', SEOGANG_RNG).poly(0.0, SEOGANG_RNG['half'], 0.0, SG_CORNER_S))
        # 신촌로 (동)'s south kerb near the junction (SE_KERB): the asphalt out to it
        road = road.union(se_widen(A['sinchon_e']))
        # the three corners that were road in 1997 (ROT_WEDGES): asphalt out to their kerbs, a sidewalk behind each
        wedges = unary_union([Polygon(w['kerb'] + w['fill']).buffer(0) for w in ROT_WEDGES.values()])
        road = road.union(wedges)
        for kk, w in ROT_WEDGES.items():
            walks[kk] = wedge_back(w, 0.0, True).difference(road)
    street = unary_union([road] + list(walks.values()))
    street = street.buffer(4.0, join_style=1).buffer(-4.0, join_style=1).union(street)
    walk = street.difference(road)
    cross_streets = unary_union([w for k, w in walks.items() if k != 'yonsei'])
    if not old:                                    # (연세로's rows end clear of the wedges' asphalt too: yro_rows)
        cross_streets = cross_streets.union(wedges)
    return dict(arms=A, road=road, street=street, walk=walk, cw=cw, walks=walks, y_top=y_top, cross_streets=cross_streets)


# 연세로 · 로터리의 다섯 길의 높이 (#189; 고증 4.10.4 「길의 높이」), 해발.  The 1997-07-28 scans (27/18 · 27/19, north of
# y -620 26/16 · 27/17 too; every pair of frames on its own, windows of 3 m at five points across the carriageway every
# 4 - 5 m, correlation 0.7 or more; roofs, buses and the shop houses' awnings that the narrow street's windows catch
# thrown out against a 24 m running median) and the 1:5000 survey's spot heights on the roads (2006 · 2024, #134).
# The game's junction (20.7 m) stands 0.3 m over the photos' reading there (20.34 m, every arm's first 15 m) as 백양로
# north of s 150 does: the profiles are the photos' + 0.3 m (and the survey's spots their difference from the
# junction's spots, 20.07 · 20.30 m, added to the game's junction).  The model had every arm and 연세로 climbing out of
# the junction; 1997 had 연세로 down in the 창천 valley (17.8 - 18 m at y -730 .. -795, the survey's spots 17.53 ·
# 17.58), up to a crest at y -870 .. -890 and down 0.5 m to the junction, and 양화로 · the 1997 신촌로 (south-west)
# falling 4 - 6 m away from it.
# YRO97: (y, z) along 연세로 from under the bridge (its north end eased into 성산로's bed at the south kerb).
YRO97 = datum.up_at([(-470.0, 23.2), (-500.0, 22.93), (-518.0, 22.82), (-530.0, 22.05), (-542.0, 20.43), (-554.0, 20.51), (-566.0, 20.44),
         (-578.0, 20.07), (-600.0, 19.33), (-630.0, 18.4), (-657.0, 18.82), (-692.0, 18.6), (-734.0, 18.06), (-770.0, 18.35),
         (-794.0, 18.36), (-866.0, 20.84), (-890.0, 20.9)],
                    [(-94.0, -470.0), (-94.0, -500.0), (-94.0, -518.0), (-94.0, -530.0), (-94.0, -542.0), (-94.0, -554.0),
                     (-94.0, -566.0), (-94.0, -578.0), (-94.0, -600.0), (-94.0, -630.0), (-94.0, -657.0), (-94.0, -692.0),
                     (-94.0, -734.0), (-94.0, -770.0), (-94.0, -794.0), (-94.0, -866.0), (-94.0, -890.0)])
# ARM97: (s out of the junction, z) along the other four (s 0: the junction's own level); past the last the
# difference to the arm's old profile fades out over ARM97_FADE m
ARM97 = {
    # 양화로: the photos to s 110, the survey's spots at s 143 · 152 (15.87 · 16.00), 220 (16.04), 326 (16.91)
    'sinchon_w': datum.up_at([(10.0, 20.36), (20.0, 20.12), (30.0, 19.77), (40.0, 19.56), (50.0, 19.24), (60.0, 19.09), (70.0, 18.82),
                  (80.0, 18.4), (90.0, 18.04), (100.0, 17.68), (110.0, 17.46), (147.0, 17.02), (220.0, 17.38), (326.0, 18.66)],
                             [(-110.3, -970.6), (-120.1, -968.4), (-129.6, -965.3), (-139.1, -962.3), (-148.6, -959.2),
                              (-158.0, -955.7), (-167.2, -951.7), (-176.3, -947.6), (-185.4, -943.4), (-194.4, -939.2),
                              (-203.5, -935.0), (-237.2, -919.6), (-303.7, -889.6), (-401.4, -848.5)]),
    # 1997년 신촌로 (남서): the photos to s 140, the spots at s 86 (17.61) and 166 · 167 (14.81 · 14.33), the survey's
    # contours past it (both editions within 0.1 m: 12.98 · 12.99 at s 200, 12.54 · 12.56 at s 250)
    'seogang': datum.up_at([(10.0, 20.36), (20.0, 19.9), (30.0, 19.67), (45.0, 19.14), (55.0, 19.14), (86.0, 18.41), (100.0, 17.94),
                (110.0, 17.64), (120.0, 17.37), (130.0, 17.11), (140.0, 16.66), (166.0, 16.01), (200.0, 14.65), (250.0, 14.49)],
                           [(-107.8, -995.5), (-116.1, -1001.1), (-124.3, -1006.9), (-136.4, -1015.7), (-144.5, -1021.7),
                            (-169.2, -1040.3), (-180.3, -1048.9), (-188.2, -1055.0), (-196.1, -1061.1), (-204.0, -1067.3),
                            (-211.9, -1073.4), (-232.4, -1089.4), (-259.4, -1110.0), (-299.3, -1140.1)]),
    # 1997년 서강로 (남): the photos to s 140 and at y -1173 (s 190, 고증 4.10.4), the spot at s 124 (22.38)
    'baekbeom': datum.up_at([(10.0, 20.71), (20.0, 20.4), (45.0, 20.23), (60.0, 20.22), (70.0, 20.58), (90.0, 21.45), (100.0, 21.73),
                 (120.0, 22.72), (140.0, 23.56), (190.0, 26.05)],
                            [(-97.5, -995.1), (-96.1, -1005.0), (-92.5, -1029.7), (-90.7, -1044.6), (-89.6, -1054.5),
                             (-87.0, -1074.4), (-85.7, -1084.3), (-83.1, -1104.1), (-80.6, -1124.0), (-74.1, -1173.5)]),
    # 신촌로 (동): the photos to s 300, the spots at s 90 (21.74), 191 (26.23), 289 (30.54), 393 (34.93), 491 (39.51)
    'sinchon_e': datum.up_at([(15.0, 20.91), (30.0, 21.07), (45.0, 21.14), (60.0, 21.34), (75.0, 21.59), (90.0, 21.98), (105.0, 22.19),
                  (120.0, 22.74), (135.0, 23.15), (150.0, 23.73), (165.0, 24.36), (180.0, 25.0), (195.0, 25.69), (210.0, 26.27),
                  (225.0, 27.05), (240.0, 27.6), (255.0, 28.3), (270.0, 28.82), (285.0, 29.27), (300.0, 29.83),
                  (392.0, 33.24), (490.0, 37.3)],
                             [(-85.4, -972.1), (-70.5, -970.9), (-55.9, -967.6), (-41.6, -962.8), (-27.8, -957.0),
                              (-13.9, -951.3), (-0.1, -945.6), (13.8, -939.9), (27.7, -934.3), (41.6, -928.6), (55.5, -923.0),
                              (69.4, -917.3), (83.3, -911.7), (97.2, -906.0), (111.1, -900.4), (125.0, -894.8), (138.9, -889.1),
                              (152.8, -883.4), (166.6, -877.7), (180.5, -872.0), (265.9, -837.9), (362.5, -822.6)]),
}
ARM97_FADE = 60.0
LEVEL_EASE = 30.0              # (the ground eased into the streets' bed this far past the sidewalks: the shop houses on it)
# the junction's own level (the photos' 20.34 m + 0.3, as the surface model happened to have it smoothed at its
# middle): held, now that the town round it lies on the survey's surface (tools/town97.py)
JC_Z = datum.up(-100.0, -975.0, 20.67)                   # @ JC (-100, -975)


def level(Hn, Hs, half, step, geo, sample_n, keep=None):
    """The streets' bed: level across each arm, its height along it the 1997 photos' (YRO97, ARM97; past them the
    ground smoothed over 60 m: since 2026-11-15 the survey's surface, tools/town97.py, which carries the arms' outer
    ends on its spot heights), the junction at JC_Z; eased out over LEVEL_EASE m past the sidewalks.  North of y -505 only under the bridge, to 성산로's
    south kerb (gate_town.plan's bed); keep: what stays as it is (the banks' footprint)."""
    S = SOUTH
    A = geo['arms']
    i0 = int(round((S['x0'] + half) / step))
    nx = S['nx']
    k1 = int(round((-400.0 + half) / step)) + 1                          # Hn rows up to y -400
    C = np.vstack([Hs[:-1], Hn[:k1, i0:i0 + nx]])
    ys = S['y0'] + np.arange(C.shape[0]) * step
    xs = S['x0'] + np.arange(nx) * step
    X, Y = np.meshgrid(xs, ys)
    Cs = ndimage.gaussian_filter(C, 3.0)
    # (off the patch's south edge, where 1997년 신촌로(남서)'s and 서강로's last few metres run, the nearest node's
    # ground: till 2026-11-16 a constant -2.0 m there, which pulled their profiles' last 60 m down by up to 3 m once the
    # rim kept their beds, tools/town97.py street_hold)
    smp = lambda x, y: float(ndimage.map_coordinates(Cs, [[(y - S['y0']) / step], [(x - S['x0']) / step]], order=1, mode='nearest')[0])
    zj = JC_Z
    prof = {}
    for k, a in A.items():
        z = np.array([smp(*p) for p in a.P])
        z = ndimage.gaussian_filter1d(z, 30.0 / 2.0, mode='nearest')           # (2 m stations: 60 m)
        # from the junction's level at its middle, into the arm's own over 40 m
        f = np.clip(a.cum / 40.0, 0, 1)
        f = f * f * (3 - 2 * f)
        z = zj * (1 - f) + z * f
        # no steeper than 4 % out of the junction (the model's 7 - 8 % up 신촌로's east arm and the south arm in their
        # first 100 m is the tall blocks at the corners)
        for i in range(1, len(z)):
            ds = a.cum[i] - a.cum[i - 1]
            z[i] = min(max(z[i], z[i - 1] - 0.04 * ds), z[i - 1] + 0.04 * ds)
        if k == 'yonsei':
            # the photos' profile from the junction up to the bridge, its north end into the bed of 성산로 at the south
            # kerb (gate_town.plan, on the same photos) over 15 m; smoothed over 16 m (σ 8 m)
            yt = geo['y_top'] - 1.0
            zb = sample_n(gt.YONSEI_X, yt)
            sb = float(a.ls.project(Point(gt.YONSEI_X, yt)))
            ty, tz = zip(*([(JC[1] + 13.0, zj)] + YRO97[::-1]))
            z = ndimage.gaussian_filter1d(np.interp(a.P[:, 1], ty, tz), 4.0, mode='nearest')
            f = np.clip((a.cum - (sb - 15.0)) / 15.0, 0, 1)
            z = z * (1 - f) + zb * f
        elif k in ARM97:
            # the photos' profile, past its last station the old one's shape, the difference fading out
            ts, tz = zip(*([(0.0, zj)] + ARM97[k]))
            z97 = ndimage.gaussian_filter1d(np.interp(a.cum, ts, tz), 4.0, mode='nearest')
            dz = z97 - z
            dz = np.where(a.cum <= ts[-1], dz, np.interp(ts[-1], a.cum, dz) * np.clip(1 - (a.cum - ts[-1]) / ARM97_FADE, 0, 1))
            z = z + dz
        prof[k] = z
    P = shapely.points(np.stack([X.ravel(), Y.ravel()], 1))
    tgt = np.zeros(X.size)
    wsum = np.zeros(X.size)
    for k, a in A.items():
        d = shapely.distance(P, a.ls)
        s = shapely.line_locate_point(a.ls, P)
        zz = np.interp(s, a.cum, prof[k])
        wk = 1.0 / (np.maximum(d - a.half, 0.0) ** 2 + 1.0)
        wk[d > a.half + a.walk + 30.0] = 0.0
        tgt += zz * wk
        wsum += wk
    tgt = np.where(wsum > 0, tgt / np.maximum(wsum, 1e-9), C.ravel()).reshape(X.shape)
    dist = shapely.distance(P, geo['street']).reshape(X.shape)
    w = 1.0 - np.clip(dist / LEVEL_EASE, 0, 1)
    w = w * w * (3 - 2 * w)
    w *= np.where(wsum.reshape(X.shape) > 0, 1.0, 0.0)
    # north of y -505 only in the bridge's opening (eased over 3 m inside its abutments), up to 성산로's south kerb
    bx = np.clip(np.minimum(X - gt.BRIDGE[0], gt.BRIDGE[1] - X) / 3.0, 0, 1)
    nf = np.maximum(np.clip((-500.0 - Y) / 10.0, 0, 1), bx * np.clip((geo['y_top'] - 1.0 - Y) / 5.0, 0, 1))
    w *= nf * nf * (3 - 2 * nf)
    if keep is not None:                       # (the banks: their slopes' feet were set on the ground as it was)
        dk = shapely.distance(P, keep).reshape(X.shape)
        fk = np.clip((dk - 2.0) / 6.0, 0, 1)
        w *= fk * fk * (3 - 2 * fk)
    C2 = C * (1 - w) + tgt * w
    Hs[:-1] = C2[:S['ny'] - 1]
    Hn[:k1, i0:i0 + nx] = C2[S['ny'] - 1:]
    Hs[-1] = Hn[0, i0:i0 + nx]
    return dict(z_junction=round(zj, 2), z_yonsei=[round(float(v), 2) for v in prof['yonsei'][::25]],
                arms={k: [round(float(v), 1) for v in prof[k][:80:20]] for k in prof})


# ----------------------------------------------------------------------------- the town
def _osm_rotary():
    p = os.path.join(ROOT, 'data/raw/osm_rotary.json')
    return json.load(open(p))['elements'] if os.path.exists(p) else []


def _poly_osm(e):
    return Polygon([_xy(p['lat'], p['lon']) for p in e['geometry']]).buffer(0)


def _box(b):
    return gt._rect(b)


def _storey(b):
    """metres a storey of block b (the landmarks' 13th field, LM_TOP; blender/town.py STOREY else)"""
    return b[12] if len(b) > 12 else 3.0


def layout(geo, town, extras, ground, taken_z):
    """What campus.json gains (into gate_town's town dict and its extras, in place):
    - the shop rows along 연세로 from y -640 to the junction and the junction's corner blocks, the town south of the
      campus grid's edge (OSM's outlines and the fill of low houses); gate_town's blocks that stand in the streets go
      (b[6] = -storeys: blender/town.py still draws their random looks, so the others keep theirs)
    - kerbs, lane paint, crossings and stop lines; the cars' lanes through the junction with their signals
    - lamps, the subway's entrances, the town's ground map.
    ground(x, y): the terrain as saved; taken_z: the campus's outlines (unused south of the rails)."""
    rnd = random.Random(4802)
    A, road, street, walk = geo['arms'], geo['road'], geo['street'], geo['walk']
    R2 = lambda a: [[round(float(x), 2), round(float(y), 2)] for x, y in a]
    ya = A['yonsei']
    # (the old line's streets: what the stream decides is decided round them, see YONSEI_RNG_PTS)
    g0 = geo['rng']
    ya0, street0 = g0['arms']['yonsei'], g0['street']
    yx0 = gt.YONSEI_X_RNG
    blocks = town['blocks']
    new = []
    # ---- 연세로's shop rows as they were (wall to wall, three to five storeys, as gate_town's, behind a 5 m walk): still
    # drawn from the stream and kept as gone blocks (b[6] < 0), so that everything after them keeps its looks; the rows
    # that stand now are yro_rows' (from the 1996 photos), appended at the end of the blocks
    corner_cut = g0['cross_streets'].buffer(1.0)
    shapely.prepare(corner_cut)
    old_fronts = {1: [], -1: []}
    for side in (1, -1):                         # +1 east, -1 west
        segs, y0 = [], Y_ROWS
        for g0, g1 in GAPS[side]:
            segs.append((y0, g0))
            y0 = g1
        segs.append((y0, None))
        for ya_, yb_ in segs:
            # (the arm runs from the junction north: s falls going south)
            s = float(ya0.ls.project(Point(yx0, ya_)))
            stop = float(ya0.ls.project(Point(yx0, yb_))) if yb_ is not None else 0.0
            while s > stop + 4.0:
                wdt = rnd.uniform(6.0, 11.5)
                if s - wdt < stop + 6.0:
                    wdt = s - stop
                dep = rnd.uniform(10.0, 15.0)
                p, t, n = ya0.at(s - wdt / 2)
                # n: left of the arm's way north, i.e. west; the east side is at -n
                c = p - n * side * (ya0.half + YRO_OLD_WALK + dep / 2)
                ang = math.atan2(-n[1] * side, -n[0] * side)          # (L, the depth, away from the street)
                bb = [round(float(c[0]), 2), round(float(c[1]), 2), round(dep, 2), round(wdt - 0.15, 2), round(ang, 4), 0.0,
                      3 + int(rnd.random() * 2.6), rnd.choice([0, 1, 2, 3, 3]), 3 if rnd.random() < 0.6 else 2, 0, 2,
                      int(rnd.random() < 0.7)]
                rr = _box(bb)
                s -= wdt
                if yb_ is None and shapely.intersects(corner_cut, rr):
                    break                                              # (the junction's corner)
                bb[5] = round(min(ground(x_, y_) for x_, y_ in list(rr.exterior.coords)[:4]) - 0.3, 2)
                new.append(bb)
                old_fronts[side].append(bb)
    rows_poly = unary_union([_box(b) for b in new])
    for bb in new:
        bb[6] = -bb[6]
    # (the street as it was with the 5 m walk, for what is cleared and placed round the old rows: the same blocks and
    # the same draws; what stands in the new rows goes in yro_rows)
    street_b = street0.union(ya0.poly(-ya0.half - YRO_OLD_WALK, ya0.half + YRO_OLD_WALK, 0.0, float(ya0.ls.project(Point(yx0, Y_ROWS)))))
    # ---- what stands in the streets or where the rows go now goes (gate_town's blocks south of its own rows)
    clear = unary_union([street_b.buffer(-0.3), rows_poly.buffer(-0.3)])
    shapely.prepare(clear)
    n_gone = 0
    for b in blocks:
        if b[1] < Y_ROWS + 30.0 and b[6] > 0 and shapely.intersects(clear, _box(b)):
            b[6] = -b[6]
            n_gone += 1
    # ---- the corners of the junction and the town south of the grid: OSM's outlines as boxes (osm_rotary.json),
    # the same rules as gate_town's; where it has none, the low houses on a loose grid
    els = _osm_rotary()
    zone = box(SOUTH['x0'] + 2.0, SOUTH['y0'] + 2.0, SOUTH['x0'] + (SOUTH['nx'] - 1) * SOUTH['step'] - 2.0, -795.0)
    zone = zone.union(box(-320.0, -800.0, 120.0, Y_ROWS))                # (and along 연세로 down from gate_town's rows)
    busy_g = unary_union([street_b.buffer(1.0), rows_poly.buffer(1.5)])
    busy = busy_g
    shapely.prepare(busy)
    old = unary_union([_box(b) for b in blocks if b[6] > 0])
    shapely.prepare(old)
    corner = []
    for e in els:
        if 'building' not in e['tags'] or e['id'] in MODERN or len(e['geometry']) < 4:
            continue
        pg = _poly_osm(e)
        if pg.geom_type == 'MultiPolygon':          # (a ring that crosses itself: its biggest part)
            pg = max(pg.geoms, key=lambda g_: g_.area)
        if pg.is_empty or pg.geom_type != 'Polygon' or pg.area < 22:
            continue
        cx, cy = pg.centroid.x, pg.centroid.y
        lm = next((m for m in LANDMARKS if pg.buffer(2.0).contains(Point(*m['at']))), None)
        if lm:                                      # (a landmark keeps what of it stands clear of the streets)
            pg = pg.difference(busy_g.buffer(0.5))
            pg = max(getattr(pg, 'geoms', [pg]), key=lambda g_: g_.area)
            cx, cy = pg.centroid.x, pg.centroid.y
        if not zone.contains(Point(cx, cy)) or shapely.intersects(busy, pg) or shapely.intersects(old, pg.buffer(-0.5)):
            continue
        rr = list(pg.minimum_rotated_rectangle.exterior.coords)[:4]
        ex, ey = np.array(rr[1]) - np.array(rr[0]), np.array(rr[3]) - np.array(rr[0])
        L, W = float(np.linalg.norm(ex)), float(np.linalg.norm(ey))
        ang = math.atan2(ex[1], ex[0])
        if W > L:
            L, W, ang = W, L, ang + math.pi / 2
        if W < 3.2:
            continue
        fill = pg.area / (L * W)
        L, W = L * (0.82 + 0.16 * fill) - 0.3, W * (0.82 + 0.16 * fill) - 0.3
        mc = pg.minimum_rotated_rectangle.centroid
        area = L * W
        r = rnd.random()
        near_j = math.hypot(mc.x - JC[0], mc.y - JC[1]) < 170.0 and street_b.distance(Point(mc.x, mc.y)) < 30.0
        on_main = street_b.distance(Point(mc.x, mc.y)) < 22.0
        if lm:
            lv = lm['lv']
        elif near_j and area > 600:                # the junction's big blocks
            lv = 5 + int(r * 3)
        elif on_main:
            lv = 3 + int(r * 2.4)
        elif area < 95:
            lv = 1 + (r < 0.62)
        elif area < 260:
            lv = 2 + (r < 0.45)
        else:
            lv = 3 + int(r * 2.2)
        hip = lv <= 2 and area < 170 and rnd.random() < 0.72
        roof = (0 if rnd.random() < 0.62 else 1 if rnd.random() < 0.7 else 2) if hip else (3 if rnd.random() < 0.55 else 2)
        wall = rnd.choice([0, 0, 0, 1, 1, 2, 2, 3])
        # (its floor at the lowest corner of the box it is drawn as, not of the outline's rectangle round it, which on a
        # slope sank the house up to a metre more: 2026-11-15)
        hs = [ground(mc.x + u_ * math.cos(ang) - v_ * math.sin(ang), mc.y + u_ * math.sin(ang) + v_ * math.cos(ang))
              for u_ in (-L / 2, L / 2) for v_ in (-W / 2, W / 2)]
        b = [round(mc.x, 2), round(mc.y, 2), round(L, 2), round(W, 2), round(ang, 4), round(min(hs) - 0.3, 2), lv,
             lm['wall'] if lm else wall, 2 if lm else roof, 0 if lm else int(hip), 1 if lm else int(on_main),
             int(rnd.random() < 0.6)]
        new.append(b)
        if lm:
            corner.append((lm, b))
    streets_osm = unary_union([LineString([_xy(q['lat'], q['lon']) for q in e['geometry']]).buffer(
        {'primary': 13.0, 'secondary': 9.0, 'tertiary': 7.0}.get(e['tags']['highway'].replace('_link', ''), 3.6))
        for e in els if 'highway' in e['tags'] and len(e['geometry']) > 1 and
        e['tags']['highway'].replace('_link', '') in ('primary', 'secondary', 'tertiary', 'residential', 'living_street',
                                                       'unclassified', 'service', 'pedestrian')])
    used = unary_union([_box(b).buffer(2.2) for b in new] + [old.buffer(2.2), streets_osm, busy])
    shapely.prepare(used)
    keep = zone.buffer(-1.0)
    shapely.prepare(keep)
    n_fill = 0
    for gy in np.arange(SOUTH['y0'] + 6.0, -795.0, 11.5):
        for gx in np.arange(SOUTH['x0'] + 6.0, SOUTH['x0'] + (SOUTH['nx'] - 1) * SOUTH['step'] - 6.0, 11.5):
            cx, cy = gx + rnd.uniform(-1.6, 1.6), gy + rnd.uniform(-1.6, 1.6)
            L, W, ang = rnd.uniform(7.0, 10.0), rnd.uniform(6.0, 8.2), rnd.choice([0.0, math.pi / 2]) + rnd.uniform(-0.12, 0.12)
            b = [round(cx, 2), round(cy, 2), round(L, 2), round(W, 2), round(ang, 4), 0.0, 1 + (rnd.random() < 0.55),
                 rnd.choice([0, 0, 1, 1, 2, 3]), 0 if rnd.random() < 0.66 else 1 if rnd.random() < 0.6 else 2, 1, 0, 0]
            if rnd.random() < 0.22:
                b[6], b[8], b[9], b[11] = 2 + (rnd.random() < 0.4), 3 if rnd.random() < 0.5 else 2, 0, int(rnd.random() < 0.6)
            r_ = _box(b)
            cs_ = np.array(r_.exterior.coords)
            if not shapely.contains_xy(keep, cs_[:, 0], cs_[:, 1]).all() or shapely.intersects(used, r_):
                continue
            b[5] = round(min(ground(x_, y_) for x_, y_ in cs_[:4]) - 0.3, 2)
            new.append(b)
            n_fill += 1
    blocks += new
    # OSM's thin outlines of today's stair canopies (10 x 3 m) had been stood up as four-storey houses at stairs 4 and 7
    # (before 그랜드백화점: the forecourt's 「kiosk」): they go (b[6] < 0, their looks still drawn) for the stairs' own roofs
    for b in new:
        if b[6] > 0 and min(b[2], b[3]) < 4.5 and any(math.hypot(b[0] - c_[0], b[1] - c_[1]) < 8.0 for c_, *_ in ENT97.values()):
            b[6] = -b[6]
    # the landmarks as the 1997 frames have them (LM_TOP, LM_SHAPE), set after the fill so that what was decided round
    # them stays: each block's box on its 1997 outline, its ground under that outline, its storeys stretched to its top
    # (13th field); blender/town.py draws them as town['landmarks'] (their boxes' draws spent into nothing)
    lm_foot = {}
    for lm, b in corner:
        sh = LM_SHAPE.get(lm['name'])
        if sh:
            g_ = Polygon(sh['outline'])
            rr = list(g_.minimum_rotated_rectangle.exterior.coords)[:4]
            ex, ey = np.array(rr[1]) - np.array(rr[0]), np.array(rr[3]) - np.array(rr[0])
            L, W = float(np.linalg.norm(ex)), float(np.linalg.norm(ey))
            ang = math.atan2(ex[1], ex[0])
            if W > L:
                L, W, ang = W, L, ang + math.pi / 2
            fill = g_.area / (L * W)
            mc = g_.minimum_rotated_rectangle.centroid
            # (its floor at the walk before its front, LM_SHAPE `front`: the lowest of those points; the ground behind the
            # three is 1 - 3 m lower since the town's ground went down to the surveyed plane, 2026-11-15, and a floor set at
            # the outline's lowest corner had the shop fronts half under the walks.  `foot`: that lowest corner, down to
            # which blender/town.py landmarks() carries the walls)
            foot = round(min(ground(x_, y_) for x_, y_ in sh['outline']) - 0.3, 2)
            floor = round(min(ground(x_, y_) for x_, y_ in sh['front']) - 0.05, 2) if sh.get('front') else foot
            lm_foot[lm['name']] = min(foot, floor)
            b[:6] = [round(mc.x, 2), round(mc.y, 2), round(L * (0.95 + 0.05 * fill) - 0.3, 2), round(W * (0.95 + 0.05 * fill) - 0.3, 2),
                     round(ang, 4), max(foot, floor)]
        if lm['name'] in LM_TOP:
            b.append(round((LM_TOP[lm['name']] - b[5] - 0.3) / b[6], 3))
    lm_draw = []
    for lm, b in corner:
        sh = LM_SHAPE.get(lm['name'])
        if not sh:
            continue
        d_ = {k: v for k, v in sh.items() if k not in ('outline', 'court', 'signs', 'front')}
        d_.update(name=lm['name'], block=next(i for i, x in enumerate(blocks) if x is b), base=b[5], top=LM_TOP[lm['name']],
                  foot=lm_foot.get(lm['name'], b[5]), outline=R2(sh['outline']))
        if 'court' in sh:
            d_['court'] = R2(sh['court'])
        lm_draw.append(d_)
    # what stands in the streets where they are now (연세로 east of its old line by 2 - 3 m) goes too, b[6] < 0
    # (only what the move put in them: boxes that stood over the old streets' edges stay as they were)
    clear_now, clear_old = street.buffer(-0.3), street0.buffer(-0.3)
    shapely.prepare(clear_now)
    shapely.prepare(clear_old)
    lm_ids = {id(b) for _, b in corner}
    n_moved = 0
    for b in blocks:
        if b[6] > 0 and b[1] < Y_ROWS + 30.0 and id(b) not in lm_ids and shapely.intersects(clear_now, _box(b)) and \
                not shapely.intersects(clear_old, _box(b)):
            b[6] = -b[6]
            n_moved += 1
    fronts, n_yro_gone, yro_shops = yro_rows(geo, blocks, ground)    # (연세로's rows house by house, at the end)
    # ---- 연세로's mouth (2026-11-16): 금강제화 and 홍익문고 as landmarks on their rows' boxes, the tower going up on the
    # lot south of 홍익문고 (KUMKANG_1997, HONGIK_FLOORS, TOWER97); what stood inside their outlines goes, its draws kept
    kk_b, hk_b = fronts[-1][-1], fronts[1][-1]
    kk_pg = Polygon(KUMKANG_1997).difference(street.buffer(0.3))
    kk_pg = shapely.geometry.polygon.orient(max(getattr(kk_pg, 'geoms', [kk_pg]), key=lambda g_: g_.area).simplify(0.1), 1.0)
    # (홍익문고: its row box, the back stretched east along its axis to HONGIK_BACK_X; the front stays the row's)
    ext_ = HONGIK_BACK_X - (hk_b[0] + hk_b[2] / 2 * math.cos(hk_b[4]))
    hk_box = [hk_b[0] + ext_ / 2 * math.cos(hk_b[4]), hk_b[1] + ext_ / 2 * math.sin(hk_b[4]), hk_b[2] + ext_, hk_b[3], hk_b[4]]
    hk_pg = shapely.geometry.polygon.orient(_box(hk_box), 1.0)
    tw_pg = shapely.geometry.polygon.orient(Polygon(TOWER97['outline']), 1.0)
    idx_of = lambda b: next(i for i, x in enumerate(blocks) if x is b)

    def mouth_lm(name, kind, pg, front, top, block, **extra):
        o_ = list(pg.exterior.coords)[:-1]
        foot = round(min(ground(x_, y_) for x_, y_ in o_) - 0.3, 2)
        floor = round(min(ground(x_, y_) for x_, y_ in front) - 0.05, 2)
        d_ = dict(kind=kind, name=name, block=block, base=max(foot, floor), top=round(top, 2), foot=min(foot, floor), outline=R2(o_))
        d_.update(extra)
        return d_
    # (홍익문고's floor: the walk before its west face, 1 m out; its top: the 1996 scans' parapet, HONGIK_TOP, the upper
    # five storeys sharing what is left over a ground floor of 3.6 m: blender/town.py _hongik)
    hk_front = [(hk_b[0] - (hk_b[2] / 2 + 1.0) * math.cos(hk_b[4]), hk_b[1] - (hk_b[2] / 2 + 1.0) * math.sin(hk_b[4]))]
    lm_mouth = [mouth_lm('금강제화', 'kumkang', kk_pg, KUMKANG_FRONT, datum.up(*KUMKANG_TOP), idx_of(kk_b)),
                mouth_lm('홍익문고', 'hongik', hk_pg, hk_front, datum.up(*HONGIK_TOP), idx_of(hk_b), floors=HONGIK_FLOORS),
                mouth_lm('신축 공사장', 'tower97', tw_pg, TOWER97['front'], datum.up(*TOWER97['top']), None,
                         floors=TOWER97['floors'], cyl=list(TOWER97['cyl']), crown=list(TOWER97['crown']),
                         crane=list(TOWER97['crane']))]
    n_mouth_gone = 0
    for pg_ in (kk_pg, tw_pg):
        shapely.prepare(pg_)
        for b in blocks:
            if b[6] > 0 and b is not kk_b and b is not hk_b and shapely.intersects(pg_, _box(b).buffer(-0.5)):
                b[6] = -b[6]
                n_mouth_gone += 1
    lm_draw += lm_mouth
    # 독수리다방's own house in its lot (tools/yro97.py DOK97: as it stood in December 1996).  Not among the landmarks:
    # those are level zones of the datum (tools/build_campus.py _dz_zones), and this one leaves the ground as it is:
    # its floor is the ground at its door (the north-west corner), its walls go down to the lowest corner
    dk = yro97.DOK97
    dk_pg = shapely.geometry.polygon.orient(Polygon(dk['main']), 1.0)
    dk_o = list(dk_pg.exterior.coords)[:-1]
    dk_z = [ground(x_, y_) for x_, y_ in dk_o]
    dk_base = ground(*dk['main'][0])
    town['sites'] = [dict(kind='dok97', name='독수리다방', base=round(dk_base, 2), top=round(dk_base + dk['h'], 2),
                          foot=round(min(dk_z) - 0.3, 2), outline=R2(dk_o), tower=R2(dk['tower']),
                          tower_h=dk['tower_h'], bay=list(dk['bay']), cells=dict(yro97.DOK_CELLS))]
    print('연세로 어귀: 금강제화 · 홍익문고 · 공사장 as landmarks, %d boxes inside them gone' % n_mouth_gone)
    # ---- kerbs: the carriageways' edge (gate_town's 연세로 north of y -560 has its own), lane paint, crossings
    kerbs, paint, zebra = [], [], []
    rings = [road] if road.geom_type == 'Polygon' else list(road.geoms)
    for pg in rings:
        for lr in [pg.exterior] + list(pg.interiors):
            ls = LineString(lr.coords)
            pts = [ls.interpolate(d).coords[0] for d in np.arange(0, ls.length, 1.5)]
            run = []
            for q in pts:
                if q[1] > -489.0 or any(math.hypot(q[0] - a.P[-1][0], q[1] - a.P[-1][1]) < a.half + 2.5 for a in A.values()):
                    if len(run) > 1:
                        kerbs.append(R2(run))
                    run = []
                else:
                    run.append(q)
            if len(run) > 1:
                kerbs.append(R2(run))
    # each arm: where it leaves the junction (its kerbs clear of the others'), a crossing there, a stop line behind it
    def mouths(arms_, cw_):
        out = {}
        for k, a in arms_.items():
            others = unary_union([c for kk, c in cw_.items() if kk != k and not ({k, kk} <= {'sinchon_w', 'sinchon_e'})])
            s = 4.0
            while s < a.cum[-1] - 10:
                p, t, n = a.at(s)
                cut = LineString([tuple(p + n * (a.half + 0.5)), tuple(p - n * (a.half + 0.5))])
                if not cut.intersects(others):
                    break
                s += 1.0
            out[k] = s + CORNER_R * 0.6 + 1.5
        return out
    # (the rule's places with 서강로 on its old line: the ginkgos are still decided round them, so that the streams'
    # draws stay; A_dec: the arms as they were for those decisions)
    A_dec = {**A, 'baekbeom': geo['rng']['arms']['baekbeom'], 'seogang': geo['rng']['arms']['seogang']}
    xs_rng = mouths(A_dec, {**geo['cw'], 'baekbeom': geo['rng']['cw']['baekbeom'], 'seogang': geo['rng']['cw']['seogang']})
    xs = dict(xs_rng)                               # (the other arms' mouths stay where the rule put them)
    # 서강로's and 1997년 신촌로's crossings where the 1997 frames have them (ROT_S_CROSS, ROT_SW_CROSS), their stop lines
    # (ROT_STOP_AT; the others' behind their mouths), signals and paint following them
    xs['baekbeom'] = float(A['baekbeom'].ls.project(Point(-90.0, ROT_S_CROSS['y'] + ROT_S_CROSS['depth'] / 2)))
    xs['seogang'] = float(A['seogang'].ls.project(Point(*ROT_SW_CROSS['c']))) - ROT_SW_CROSS['depth'] / 2
    deps = {k: 4.5 for k in A}
    deps['baekbeom'], deps['seogang'] = ROT_S_CROSS['depth'], ROT_SW_CROSS['depth']
    s_stops = {}
    AT = lambda a, k, s, o: a.at(s)[0] + a.at(s)[2] * (o + mid_of(k, s))          # (o off the painted middle)

    def runs(ss, cut):
        """ss split where it passes the [s0, s1] spans in cut"""
        out, cur = [], []
        for s in ss:
            if any(s0 <= s <= s1 for s0, s1 in cut):
                if len(cur) > 1:
                    out.append(cur)
                cur = []
            else:
                cur.append(s)
        if len(cur) > 1:
            out.append(cur)
        return out
    for k, a in A.items():
        s_x, dep = xs[k], deps[k]
        # the crossing: 4.5 m wide, white bars 0.45 m across the walk's direction (the 1990s' plain bars); none
        # across three of the mouths (ROT_NO_ZEBRA); 서강로's two rows from kerb to kerb, 1997년 신촌로's 6.8 m deep
        o0, o1 = -a.half + 0.5, a.half - 0.4
        if k == 'seogang':                             # (1997: bars from 1.4 m short of the north-west kerb to the other)
            o0 = -a.half + 2.55
        rows = [(s_x, s_x + dep)]
        if k == 'baekbeom':
            p_, _, n_ = a.at(s_x + dep / 2)
            o0, o1 = (ROT_S_CROSS['x'][0] - p_[0]) / n_[0], (ROT_S_CROSS['x'][1] - p_[0]) / n_[0] - 0.45
            rows = [(s_x, s_x + dep / 2 - 0.15), (s_x + dep / 2 + 0.15, s_x + dep)]
        for o in (np.arange(o0, o1, 0.95) if k not in ROT_NO_ZEBRA else []):
            for sa, sb in rows:                            # (서강로's: two rows of bars, as the scan has it)
                c = [a.at(sa)[0] + a.at(sa)[2] * o, a.at(sb)[0] + a.at(sb)[2] * o,
                     a.at(sb)[0] + a.at(sb)[2] * (o + 0.45), a.at(sa)[0] + a.at(sa)[2] * (o + 0.45)]
                zebra.append(R2(c))
        # stop line on the inbound half, from the painted middle to the kerb (traffic on the right: inbound cars drive
        # towards the junction, s falling: their right is +n)
        s_stop = float(a.ls.project(Point(*ROT_STOP_AT[k]))) if k in ROT_STOP_AT else s_x + 6.0 + (dep - 4.5)
        s_stops[k] = s_stop
        m0 = mid_of(k, s_stop)
        c = [a.at(s_stop)[0] + a.at(s_stop)[2] * (m0 + 0.3), a.at(s_stop + 0.5)[0] + a.at(s_stop + 0.5)[2] * (m0 + 0.3),
             a.at(s_stop + 0.5)[0] + a.at(s_stop + 0.5)[2] * (a.half - 0.3), a.at(s_stop)[0] + a.at(s_stop)[2] * (a.half - 0.3)]
        if k not in ROT_STOP_PAINTED:                  # (양화로's and 신촌로's: skewed, drawn with the wedges' paint)
            zebra.append(R2(c))
        # lane paint from the stop line out (연세로: to where gate_town's begins its own at the bridge... none there),
        # broken at a crossing; the double yellow middle on the painted middle (mid_of)
        s_end = a.cum[-1] - 3.0 if k != 'yonsei' else float(a.ls.project(Point(gt.YONSEI_X, -492.0)))
        if k == 'baekbeom':
            # 서강로 as the scans have it (BB_LINES_N / _S): the middle and the two lines in, from the junction's guide
            # line to the crossing; beyond it the middle, the two lines out and the one in
            s_j = float(a.ls.project(Point(*BB_C[1]))) - 2.0
            mids = [(0.16, 'yellow'), (-0.16, 'yellow')]
            for ss_, lines in ((np.arange(s_j, s_x - 0.3, 2.0).tolist() + [s_x - 0.3], mids + BB_LINES_N),
                               (np.arange(s_x + dep + 0.3, s_end, 2.0).tolist(), mids),
                               (np.arange(s_stop + 1.0, s_end, 2.0).tolist(), BB_LINES_S)):
                for o, kind in lines:
                    paint.append(dict(kind=kind, w=0.12, pts=R2([AT(a, k, s, o) for s in ss_])))
            continue
        ss = np.arange(s_stop + 1.0, s_end, 2.0)
        if len(ss) < 2:
            continue
        cut = [(s_x - 0.3, s_x + dep + 0.3)] if s_stop < s_x else []
        if k == 'sinchon_e':                           # (its crossing at s 278: SE_CROSS)
            cut.append((SE_CROSS['cols'][0][0] - 0.2, SE_CROSS['cols'][-1][1] + 0.2))
        if k == 'seogang':
            # 1997년 신촌로 as the scans have it (SG_LINES off the painted middle, SG_MID): the double yellow middle and
            # three lines, two in and one out, from the stop line out, broken at the crossing
            for run in runs(ss, cut):
                for o, kind in [(0.16, 'yellow'), (-0.16, 'yellow')]:
                    paint.append(dict(kind=kind, w=0.12, pts=R2([AT(a, k, s, o) for s in run])))
                for tab, kind in SG_LINES:
                    t_ = np.array(tab)
                    paint.append(dict(kind=kind, w=0.12, pts=R2([AT(a, k, s, float(np.interp(s, t_[:, 0], t_[:, 1]))) for s in run])))
            continue
        for sgn in (1, -1):
            for run in runs(ss, cut):
                paint.append(dict(kind='yellow', w=0.12, pts=R2([AT(a, k, s, sgn * 0.16) for s in run])))
            for kk in range(1, a.lanes):
                if k == 'yonsei':
                    o = sgn * (0.3 + (a.half - 0.3) / a.lanes * kk)
                    sl = ss[ss <= s_stop + YRO_LANE_SOLID]
                    paint.append(dict(kind='white', w=0.12, pts=R2([a.at(s)[0] + a.at(s)[2] * o for s in sl])))
                    continue
                s_r = ss[2:][ss[2:] >= ROT_LANE_FROM.get((k, sgn), 0.0)]
                if k == 'sinchon_e':                 # (the scans' lanes: SE_LINES, NE_LINES, SE_FAR_LINES)
                    s_r = s_r[:0]
                for run in runs(s_r, cut):
                    pts = []
                    for s in run:
                        hs = a.half - sgn * mid_of(k, s)                 # (the half on that side of the painted middle)
                        pts.append(AT(a, k, s, sgn * (0.3 + (hs - 0.3) / a.lanes * kk)))
                    paint.append(dict(kind='white_dash', w=0.12, pts=R2(pts)))
    ae_ = A['sinchon_e']
    SO = lambda s, o: ae_.at(s)[0] + ae_.at(s)[2] * o
    for tab, spans in SE_LINES + NE_LINES + SE_FAR_LINES:         # (신촌로's lanes, 1997)
        t_ = np.array(tab)
        for s0_, s1_, kind in spans:
            sl = np.arange(s0_, s1_, 2.0).tolist() + [s1_]
            paint.append(dict(kind=kind, w=0.12, pts=R2([SO(s, float(np.interp(s, t_[:, 0], t_[:, 1]))) for s in sl])))
    # its crossing at s 278 (SE_CROSS): two columns of 0.45 m bars, and the two stop lines (from the painted middle to
    # the kerbs: the south one SE_KERB's, the north one where the bars end)
    for sa, sb in SE_CROSS['cols']:
        for o in np.arange(SE_CROSS['o'][0], SE_CROSS['o'][1] - 0.4, 0.95):
            zebra.append(R2([SO(sa, o), SO(sb, o), SO(sb, o + 0.45), SO(sa, o + 0.45)]))
    for s_, o0, o1 in ((SE_CROSS['stop_out'], se_kerb(SE_CROSS['stop_out']) + 0.3, mid_of('sinchon_e', SE_CROSS['stop_out']) - 0.3),
                       (SE_CROSS['stop_in'], mid_of('sinchon_e', SE_CROSS['stop_in']) + 0.3, SE_CROSS['o'][1])):
        zebra.append(R2([SO(s_, o0), SO(s_ + 0.5, o0), SO(s_ + 0.5, o1), SO(s_, o1)]))
    # 연세로's crossing between the junction and the bridge, with stop lines either side (MID_CROSS: s_mid its south
    # edge, mid_dep its depth, s_stop_n / s_stop_s where its stop lines begin)
    s_mid = float(ya.ls.project(Point(gt.YONSEI_X, MID_CROSS['y'][0])))
    mid_dep = MID_CROSS['y'][1] - MID_CROSS['y'][0]
    s_stop_n = float(ya.ls.project(Point(gt.YONSEI_X, MID_CROSS['stop_n'])))
    s_stop_s = float(ya.ls.project(Point(gt.YONSEI_X, MID_CROSS['stop_s'])))
    s_mid_rng = float(ya.ls.project(Point(gt.YONSEI_X, MID_CROSS_Y_RNG)))
    # (and the one further up at y -690 the 1997 frames show, 4.9 m across: no signals of its own in the game)
    s_c2 = float(ya.ls.project(Point(gt.YONSEI_X, YRO_CROSS2_Y))) - 2.45
    # (its other two crossings with the signals 51979 has over them: [s of the south edge, depth]; -575 is gate_town's)
    yro_cross = [(s_c2, 4.5), (float(ya.ls.project(Point(gt.YONSEI_X, gt.YZEBRA2[1]))), gt.YZEBRA2[0] - gt.YZEBRA2[1])]
    hm = (mid_dep - MID_CROSS['gap']) / 2
    for s_z, rows, stops_ in ((s_mid, ((0.0, hm), (mid_dep - hm, mid_dep)), (s_stop_n, s_stop_s)),
                              (s_c2, ((0.0, 4.5),), (s_c2 + 6.0, s_c2 - 2.0))):
        for r0, r1 in rows:
            for o in np.arange(-ya.half + 0.5, ya.half - 0.4, 0.95):
                c = [ya.at(s_z + r0)[0] + ya.at(s_z + r0)[2] * o, ya.at(s_z + r1)[0] + ya.at(s_z + r1)[2] * o,
                     ya.at(s_z + r1)[0] + ya.at(s_z + r1)[2] * (o + 0.45), ya.at(s_z + r0)[0] + ya.at(s_z + r0)[2] * (o + 0.45)]
                zebra.append(R2(c))
        for s_, o0, o1 in ((stops_[0], 0.3, ya.half - 0.3), (stops_[1], -ya.half + 0.3, -0.3)):
            zebra.append(R2([ya.at(s_)[0] + ya.at(s_)[2] * o0, ya.at(s_ + 0.5)[0] + ya.at(s_ + 0.5)[2] * o0,
                             ya.at(s_ + 0.5)[0] + ya.at(s_ + 0.5)[2] * o1, ya.at(s_)[0] + ya.at(s_)[2] * o1]))
    # the island: its kerb a ring, the white ring of short dashes round it (52158: some 0.6 m long, as long apart)
    ic, ir = np.array(ISLAND['c']), ISLAND['r']
    kerbs.append(R2([tuple(ic + ir * np.array([math.cos(a_), math.sin(a_)])) for a_ in np.linspace(0, 2 * math.pi, 49)]))
    nd = int(round(2 * math.pi * ISLAND['ring'] / 1.2))
    for i in range(nd):
        a0, a1 = 2 * math.pi * i / nd, 2 * math.pi * (i + 0.5) / nd
        paint.append(dict(kind='white', w=0.25, pts=R2([tuple(ic + ISLAND['ring'] * np.array([math.cos(a_), math.sin(a_)]))
                                                        for a_ in np.linspace(a0, a1, 3)])))
    paint += rot_letters()
    paint += rot_marks()
    # the U-turn loop round the island: its yellow outer edge (ROT_D, smoothed through the scan's points), its two
    # triangles with a smaller one inside each, and its arrows (a straight arrow's head at the point, 2.2 m of shaft)
    paint.append(dict(kind='yellow', w=0.2, pts=R2([tuple(q) for q in gt._chaikin(ROT_D, 2)])))
    for tri in ROT_D_TRI:
        tri = np.array(tri)
        cen = tri.mean(0)
        for f in (1.0, 0.45):
            q = cen + (tri - cen) * f
            paint.append(dict(kind='yellow', w=0.2, pts=R2(list(q) + [q[0]])))
    for hx, hy, brg in ROT_D_ARROWS:
        u = np.array([math.sin(math.radians(brg)), math.cos(math.radians(brg))])
        v = np.array([-u[1], u[0]])
        h_ = np.array([hx, hy])
        paint.append(dict(kind='white', w=0.18, pts=R2([h_ - u * 1.4, h_ - u * 3.6])))
        for d_ in (-0.5, -0.25, 0.0, 0.25, 0.5):
            paint.append(dict(kind='white', w=0.22, pts=R2([h_, h_ - u * 1.5 + v * d_])))
    # the crossing over 성산로 before the bridge is gate_town's
    # ---- the cars' lanes through the junction, each with the signal phase it waits for at its stop line
    lanes = []

    def lane_pts(k, o, s0, s1, step=3.0):
        a = A[k]
        ss = np.arange(s0, s1, step if s1 > s0 else -step).tolist() + [s1]
        of = o if callable(o) else (lambda s_: o)     # (o off the painted middle; a function of s where a lane shifts)
        return [tuple(a.at(s)[0] + a.at(s)[2] * (of(s) + mid_of(k, s))) for s in ss]

    def curve(p0, d0, p1, d1, n=10):
        """a smooth turn from p0 heading d0 to p1 heading d1 (cubic Bezier)"""
        L = float(np.linalg.norm(np.array(p1) - np.array(p0))) * 0.45
        c0, c1 = np.array(p0) + np.array(d0) * L, np.array(p1) - np.array(d1) * L
        out = []
        for i in range(1, n):
            t = i / n
            q = (1 - t) ** 3 * np.array(p0) + 3 * (1 - t) ** 2 * t * c0 + 3 * (1 - t) * t * t * c1 + t ** 3 * np.array(p1)
            out.append(tuple(q))
        return out

    def route(k_in, o_in, k_out, o_out, phase, s_far_in=None, s_far_out=None, s_in=None, s_out=None):
        """in along arm k_in (towards the junction) at offset o_in, out along k_out at o_out (s_in: where the lane in
        ends, its stop line; the arm's own else. s_out: where the lane out begins; behind the arm's mouth else)"""
        ai, ao = A[k_in], A[k_out]
        si0 = ai.cum[-1] - 2.0 if s_far_in is None else s_far_in
        so1 = ao.cum[-1] - 2.0 if s_far_out is None else s_far_out
        so0 = min(xs[k_out], s_stops[k_out]) + 1.0 if s_out is None else s_out
        a_in = lane_pts(k_in, o_in, si0, s_stops[k_in] - 0.5 if s_in is None else s_in)
        a_out = lane_pts(k_out, o_out, so0, so1)
        d_in = -ai.at(s_stops[k_in] - 0.5)[1]
        d_out = ao.at(so0)[1]
        mid = curve(a_in[-1], d_in, a_out[0], d_out, 24)
        mid = round_island(a_in[-1], mid, a_out[0])
        pts = a_in + mid + a_out
        ls = LineString(pts)
        stops = [[round(float(ls.project(Point(a_in[-1]))) - 0.5, 1), 0, phase]]
        # 연세로's crossing: northbound cars stop south of it, southbound north of it (group 1: 0 cars go, 1 walkers)
        # (and at its other two, -690 and -575, as they come: yro_cross; the same group, they turn together)
        if k_in == 'yonsei':
            for s_q in [s_z + dep_ + 1.5 for s_z, dep_ in yro_cross[::-1]] + [s_stop_n]:
                q = ya.at(s_q)[0] + ya.at(s_q)[2] * o_in
                stops.insert(len(stops) - 1, [round(float(ls.project(Point(*q))) - 0.5, 1), 1, 0])
        if k_out == 'yonsei':
            for s_q in [s_stop_s] + [s_z - 2.0 for s_z, _ in yro_cross]:
                q = ya.at(s_q)[0] + ya.at(s_q)[2] * o_out
                stops.append([round(float(ls.project(Point(*q))) - 0.5, 1), 1, 0])
        return dict(kind='car', pts=R2(pts), stops=stops)

    def route_via(k_in, o_in, s_leave, via, k_out, o_out, s_join, phase, s_far_in=None, s_far_out=None):
        """a lane turning right through a wedge (ROT_WEDGES): in along k_in at o_in down to s_leave, through the via
        points (the turning lane's middle; its last but one is its stop line's place), out along k_out from s_join"""
        ai, ao = A[k_in], A[k_out]
        si0 = ai.cum[-1] - 2.0 if s_far_in is None else s_far_in
        so1 = ao.cum[-1] - 2.0 if s_far_out is None else s_far_out
        a_in = lane_pts(k_in, o_in, si0, s_leave)
        a_out = lane_pts(k_out, o_out, s_join, so1)
        mid = [tuple(q) for q in gt._resample(gt._chaikin([a_in[-1]] + list(via) + [a_out[0]], 3), 2.0)][1:-1]
        pts = a_in + mid + a_out
        ls = LineString(pts)
        stops = [[round(float(ls.project(Point(*via[-2]))), 1), 0, phase]]
        if k_in == 'yonsei':
            q = ya.at(s_stop_n)[0] + ya.at(s_stop_n)[2] * o_in
            stops.insert(0, [round(float(ls.project(Point(*q))) - 0.5, 1), 1, 0])
        if k_out == 'yonsei':
            q = ya.at(s_stop_s)[0] + ya.at(s_stop_s)[2] * o_out
            stops.append([round(float(ls.project(Point(*q))) - 0.5, 1), 1, 0])
        return dict(kind='car', pts=R2(pts), stops=stops)

    def round_island(p0, mid, p1):
        """the turn's points pushed out of the island's ring, passing it with the island on the left"""
        out = []
        P_ = [np.array(p0)] + [np.array(q) for q in mid] + [np.array(p1)]
        R_ = ISLAND['ring'] + 2.0
        for i in range(1, len(P_) - 1):
            q, d = P_[i], P_[i + 1] - P_[i - 1]
            d = d / max(1e-9, np.linalg.norm(d))
            v = q - ic
            if np.linalg.norm(v) < R_:
                right = np.array([d[1], -d[0]])
                v = v + right * R_ * 0.9
                q = ic + v / np.linalg.norm(v) * R_
            out.append(q)
        for _ in range(3):                                  # (smoothed: the push leaves corners)
            out = [out[0]] + [(out[j - 1] + out[j] * 2 + out[j + 1]) / 4 for j in range(1, len(out) - 1)] + [out[-1]]
        return [tuple(q) for q in out]

    s_bridge = float(ya.ls.project(Point(gt.YONSEI_X, -480.0)))
    s_bridge2 = float(ya.ls.project(Point(gt.YONSEI_X, -488.0)))
    L1, L2 = LANE_W / 2 + 0.3, LANE_W * 1.5 + 0.3
    Y1, Y2 = YRO_LANES                                  # (연세로's own)
    # (inbound on an arm: going against its s, the right-hand side is +n (left of the outward direction))
    lanes.append(route('yonsei', Y1, 'baekbeom', -L1, 0, s_far_in=s_bridge))           # 연세로 south, on into 백범로
    lanes.append(route('yonsei', Y2, 'seogang', -L2, 0, s_far_in=s_bridge))            # and right into 서강로
    lanes.append(route('baekbeom', L1, 'yonsei', -Y1, 0, s_far_out=s_bridge2))         # 백범로 north into 연세로
    lanes.append(route('seogang', L1, 'yonsei', -Y2, 2, s_far_out=s_bridge2))          # 서강로 into 연세로
    # 신촌로 in (west): two lanes past the band of chevrons to its stop line (ROT_E_LANES: m off the painted middle),
    # the third into the taxis' stand north of the band, up to the slanted line at its head
    for kk in (0, 1, 2):
        o = 0.3 + LANE_W * (kk + 0.5)
        lanes.append(route('sinchon_w', o, 'sinchon_e', -o, 1))                          # 신촌로 east
        oe, se = ROT_E_LANES[kk]
        o_e = (lambda s_, o=o, oe=oe: o + (oe - o) * float(np.clip((62.0 - s_) / 16.0, 0, 1)))
        om, sa, sb = ROT_W_MOUTH[kk]                    # (round 양화로's double triangle at its mouth)
        ease = lambda u: u * u * (3.0 - 2.0 * u)
        o_w = (lambda s_, o=o, om=om, sa=sa, sb=sb: -(o + (om - o) * ease(float(np.clip((sb - s_) / (sb - sa), 0, 1)))))
        lanes.append(route('sinchon_e', o_e, 'sinchon_w', o_w, 1, s_in=se, s_out=ROT_W_OUT))      # and west
    # the kerb lanes turning off through the wedges (ROT_TURNS: the 1997 lanes' middles): 양화로 into 1997년 신촌로
    # between the almond and the V, 신촌로 into 연세로 north of the north-east triangle
    T_ = ROT_TURNS
    lanes.append(route_via('sinchon_w', 0.3 + LANE_W * 3.5, T_['w_sw'][0], T_['w_sw'][1], 'seogang', -(0.3 + LANE_W * 1.5),
                           T_['w_sw'][2], 1))
    lanes.append(route_via('sinchon_e', 0.3 + LANE_W * 3.5, T_['e_n'][0], T_['e_n'][1], 'yonsei', -Y2, T_['e_n'][2], 1,
                           s_far_out=s_bridge2))
    # (2026-11-15, the last in the list: its cars drawn after the others') 연세로 into 양화로 by the north-west wedge
    lanes.append(route_via('yonsei', Y2, T_['n_w'][0], T_['n_w'][1], 'sinchon_w', -(0.3 + LANE_W * 3.5), T_['n_w'][2], 0,
                           s_far_in=s_bridge))
    # signals: group 0 the junction (phases 0 연세로 · 백범로, 1 신촌로 · 양화로, 2 the south-west arm), group 1
    # 연세로's crossing (0 cars, 1 walkers): green s each, then amber and all red
    signals = dict(groups=[dict(green=[26.0, 30.0, 14.0]), dict(green=[45.0, 18.0])], amber=3.0, red=3.0)
    # the signal heads: one at the far side of each arm's mouth facing the inbound traffic, and one at its stop line
    # [x, y of the pole, the way the lamps face (rad), group, phase, the mast arm's reach over the lanes(, lamps: 4 at
    # the junction, red · amber · the left arrow · green as 52007 and 52111 · 52139 have them, 1996; else three)]
    heads = []
    road_pole = road.buffer(0.6)
    for k, ph in (('yonsei', 0), ('baekbeom', 0), ('seogang', 2), ('sinchon_w', 1), ('sinchon_e', 1)):
        a = A[k]
        p, t, n = a.at(s_stops[k] + 0.5)
        q = p + n * (a.half + 0.8)                       # at the stop line, on the inbound side's kerb
        if road_pole.contains(Point(*q)):                # (where a corner's asphalt reaches on: on the far kerb)
            q = p - n * (a.half + 0.8)
            if road_pole.contains(Point(*q)):
                # (1997's wedges are asphalt on both sides of 연세로's, 양화로's, 신촌로's and 1997년 신촌로's stop lines:
                # no pole of the game's rule there; where their signals hung is not known but the island's own pole)
                continue
        heads.append([round(float(q[0]), 2), round(float(q[1]), 2), round(math.atan2(t[1], t[0]), 4), 0, ph, round(a.half * 0.75, 1), 4])
    for sgn, s_ in ((1, s_stop_n + 0.5), (-1, s_stop_s - 0.5)):
        p, t, n = ya.at(s_)
        q = p + n * sgn * (ya.half + 0.8)
        heads.append([round(float(q[0]), 2), round(float(q[1]), 2), round(math.atan2(t[1] * sgn, t[0] * sgn), 4), 1, 0,
                      round(ya.half * 0.75, 1)])
    # the island's own pole (52158 · 52145 · 52142: on its north-north-west edge, the arm out over the lanes north)
    fb = math.radians(ROT_POLE['face'])
    heads.append([ROT_POLE['at'][0], ROT_POLE['at'][1], round(math.atan2(math.cos(fb), math.sin(fb)), 4), 0, 1, ROT_POLE['reach'], 4])
    # 연세로's mouth, the far side for the cars coming up from 서강로 (MOUTH_SIGNAL: 52206 · 52141, the scan of 27/19): the
    # north-east corner's pole, its arm west over their lanes, a head over each (the web hangs a head at 0.8 of the reach)
    mx_, my_ = MOUTH_SIGNAL['pole']
    for hx_ in MOUTH_SIGNAL['heads']:
        heads.append([mx_, my_, round(-math.pi / 2, 4), 0, 0, round((mx_ - hx_) / 0.8, 2), 4])
    # (2026-11-17) and 신촌로's for the cars from 양화로 (FAR_E_SIGNAL, 52208): one head on its arm (the photo's two are
    # 2 - 3 m apart on it; the web hangs one at 0.8 of the reach), with 신촌로 · 양화로 (phase 1)
    fe = FAR_E_SIGNAL
    heads.append([fe['pole'][0], fe['pole'][1], round(math.radians(fe['face']), 4), 0, 1, fe['reach'], 4])
    # (2026-11-22) the two in front of 그랜드 (GRAND_SIGNALS, 52122), with 신촌로 · 양화로 (phase 1); a head each (the web
    # hangs it at 0.8 of the reach; a negative reach: the arm to the lamps' left)
    for gs in GRAND_SIGNALS:
        fb = math.radians(gs['face'])
        for o_ in gs['heads']:
            heads.append([gs['pole'][0], gs['pole'][1], round(math.atan2(math.cos(fb), math.sin(fb)), 4), 0, 1,
                          round(o_ / 0.8, 2), 4])
    # (2026-11-22 셋째) 양화로's north kerb, the same phase: one arm of its true length, the heads where the photos have
    # them (`heads`' 8th field: m along the arm; web/src/town.js)
    fb = math.radians(YH_SIGNAL['face'])
    for o_ in YH_SIGNAL['heads']:
        heads.append([YH_SIGNAL['pole'][0], YH_SIGNAL['pole'][1], round(math.atan2(math.cos(fb), math.sin(fb)), 4), 0, 1,
                      YH_SIGNAL['reach'], 4, o_])
    # 연세로's other two crossings (y -690 and gate_town's at -575): 51979 (1996.5) through its camera solved on the 1997
    # ground has two heads hung over the road just beyond each for the cars going north, on an arm from the east walk
    # (5.5 - 6.2 m up: y -679 .. -693 and -568 .. -580; x 1.3 m east and 0.9 m west of the middle at the near one, 0.3 and
    # 2.7 m east at the far one).  A pole each side, its head beyond the crossing for the cars it faces (the ones going
    # south: taken to mirror them); they turn with the crossing at -783 (group 1)
    for s_z, dep_ in yro_cross:
        for sgn, s_ in ((1, s_z - 2.5), (-1, s_z + dep_ + 2.5)):          # (beyond the crossing for those they face)
            p, t, n = ya.at(s_)
            q = p + n * sgn * (ya.half + 0.8)
            heads.append([round(float(q[0]), 2), round(float(q[1]), 2), round(math.atan2(t[1] * sgn, t[0] * sgn), 4), 1, 0,
                          round(ya.half * 0.75, 1)])
    # 성산로 at the gate (2026-11-16): 51995 (1995.10, 서울연구원) has a grey pole at the kerb by the crossing east of the
    # gate, a long arm over the lanes and two heads of three lamps on it.  Its own group (2: the cars 40 s, the walkers
    # 20 s); its cars stop at the lines gate_town paints (eastbound before 연세로's box, westbound past the crossing)
    s_lines = {1: gt.BOX_X[0] - 3.5, -1: gt.CROSS_X[1] + 3.5}       # (+1: eastbound, on the south side)
    for l in town['lanes']:
        if l.get('stops') is not None or l['kind'] not in ('car', 'bus'):
            continue
        P_ = np.array(l['pts'])
        way = 1 if P_[-1][0] > P_[0][0] else -1
        ls_ = LineString(P_)
        xs_ = s_lines[way]
        k_ = int(np.argmin(np.abs(P_[:, 0] - xs_)))
        l['stops'] = [[round(float(ls_.project(Point(*P_[k_]))) + (xs_ - P_[k_][0]) * way - 0.5, 1), 2, 0]]
        l['ss'] = 1                                     # (성산로's: its cars keep to their own lanes, web/src/town.js)
    for way, face in ((1, math.pi), (-1, 0.0)):
        l = next(l for l in town['lanes'] if l.get('ss') and l['kind'] == 'bus' and (l['pts'][-1][0] > l['pts'][0][0]) == (way > 0))
        P_ = np.array(l['pts'])
        k_ = int(np.argmin(np.abs(P_[:, 0] - s_lines[way])))
        d_ = P_[min(k_ + 1, len(P_) - 1)] - P_[max(k_ - 1, 0)]
        d_ = d_ / np.linalg.norm(d_)
        q = P_[k_] + np.array([d_[1], -d_[0]]) * 3.2           # (right of the way: the kerb, 0.8 m behind it)
        for reach in (8.75, 15.0):                      # (two heads on the one arm, as 51995 has them)
            heads.append([round(float(q[0]), 2), round(float(q[1]), 2), round(face, 4), 2, 0, reach])
    signals['groups'].append(dict(green=[40.0, 20.0]))
    # ---- the walkers' signals (2026-11-16, user's request): at each end of every crossing the walker may use, a grey
    # pole beside the zebra and on it a black box of two lamps, the red standing figure over the green walking one,
    # each under its hood, facing across the street to those waiting on the far side.  Their look: 서울연구원 50377
    # (1995.10, 압구정 갤러리아 앞: the pole with a pointed cap, the box on its side at 2.4 - 3.1 m) and 30197 (1996.10);
    # no photo shows those of 연세로 or the junction (고증 4.10.2 「보행 신호등」).  [x, y, the way the lamps face (rad),
    # group, phases whose green lets the walkers go (bits)]: 연세로's with its crossings' own walkers' phase, the one
    # over its mouth by 성산로 with 성산로's cars (no car turns there), 서강로's while 신촌로 · 양화로 and the
    # south-west arm go, the south-west arm's while 연세로 · 서강로 and 신촌로 · 양화로 go (who turns in yields)
    peds = []
    road_ped = road.buffer(0.45)

    def ped(p, inward, face, grp, mask):
        """a pole at p, moved back from the kerb (against `inward`) till it stands clear of the asphalt"""
        q = np.array(p, float)
        for _ in range(30):
            if not road_ped.contains(Point(*q)):
                break
            q = q - np.array(inward) * 0.1
        peds.append([round(float(q[0]), 2), round(float(q[1]), 2), round(face, 4), grp, mask])

    def ped_arm(a, s0, s1, grp, mask):
        """both ends of a zebra over arm a from s0 to s1 (outward along it): the +n end at its outer edge, the -n end
        at its inner one"""
        for sgn, s_ in ((1, s1 + 0.55), (-1, s0 - 0.55)):
            p, t, n = a.at(s_)
            q = p + n * sgn * (a.half + 0.5)
            ped(q, n * sgn * -1.0, math.atan2(-n[1] * sgn, -n[0] * sgn), grp, mask)
    ped_arm(ya, s_mid, s_mid + mid_dep, 1, 0b10)
    ped_arm(ya, s_c2, s_c2 + 4.5, 1, 0b10)
    for (y0_, y1_), grp, mask in ((gt.YZEBRA2, 1, 0b10), (gt.YZEBRA, 2, 0b01)):      # (gate_town's two over 연세로)
        xw, xe = gt.YONSEI_X - gt.YONSEI_HALF - 0.5, gt.YONSEI_X + gt.YONSEI_HALF + 0.5
        ped((xw, y1_ - 0.55), (1, 0), 0.0, grp, mask)
        ped((xe, y0_ + 0.55), (-1, 0), math.pi, grp, mask)
    ped_arm(A['seogang'], xs['seogang'], xs['seogang'] + deps['seogang'], 0, 0b011)
    yc0, yc1 = ROT_S_CROSS['y'] - ROT_S_CROSS['depth'] / 2, ROT_S_CROSS['y'] + ROT_S_CROSS['depth'] / 2
    ped((ROT_S_CROSS['x'][0] - 0.5, yc0 - 0.55), (1, 0), 0.0, 0, 0b110)            # (서강로's: 외환은행's side)
    ped((ROT_S_CROSS['x'][1] + 0.5, yc1 + 0.55), (-1, 0), math.pi, 0, 0b110)       # (and the wedge's walk)
    cx0_, cx1_, ks_, kn_ = extras['cross_box']
    ped((cx1_ + 0.55, ks_ - 0.5), (0, 1), math.pi / 2, 2, 0b10)                     # (성산로's: its south walk)
    ped((cx0_ - 0.55, kn_ + 0.5), (0, -1), -math.pi / 2, 2, 0b10)                   # (and the gate's side)
    # ---- the walks open to the walker again (2026-11-14, user's request; shut 2026-11-11): from 성산로's crossing over
    # its south walk, 연세로's two sidewalks with their three crossings, the junction's corners within REACH and the
    # crossings July 1997 had there (서강로's in front of 외환은행 and the south-west arm's: none over 연세로's,
    # 양화로's or 신촌로's mouths, so the north and the south corners only meet under the ground, by 신촌역's passages).
    # A wall of thin boxes round them (web/src/player.js Colliders reads only the 8 m cells by the walker, so the
    # 5,000 boxes that were dropped for the time they cost cost nothing now); the polygons go out as walk_open, where
    # the web may set a walker down (main.js beyondGate)
    near = Point(*JC).buffer(REACH)
    W_parts = [walk.intersection(near)]
    W_parts.append(walk.intersection(box(-140.0, JC[1] - 10.0, -50.0, geo['y_top'] + 3.0)))
    for k, a in A.items():
        if k in ROT_NO_ZEBRA:
            continue
        s_x = xs[k]
        if k == 'baekbeom':
            p_, _, n_ = a.at(s_x + ROT_S_CROSS['depth'] / 2)
            o0, o1 = (ROT_S_CROSS['x'][0] - p_[0]) / n_[0], (ROT_S_CROSS['x'][1] - p_[0]) / n_[0]
            W_parts.append(a.poly(-a.half - a.walk, o1 + ROT_APRON_WALK + 0.5, s_x - 0.25, s_x + ROT_S_CROSS['depth'] + 0.25).intersection(street))
        else:
            W_parts.append(a.poly(-a.half - a.walk, a.half + a.walk_l, s_x - 0.25, s_x + deps[k] + 0.25).intersection(street))
    for s_z, dep_ in ((s_mid, mid_dep), (s_c2, 4.5)):
        W_parts.append(ya.poly(-ya.half - 5.0, ya.half + 5.0, s_z - 0.25, s_z + dep_ + 0.25).intersection(street))
    for y0_, y1_ in (gt.YZEBRA2, gt.YZEBRA):          # (gate_town's: south of the bridge, and over 연세로's mouth)
        W_parts.append(box(gt.YONSEI_X - gt.YONSEI_HALF - gt.YONSEI_WALK, y1_ - 0.25, gt.YONSEI_X + gt.YONSEI_HALF + gt.YONSEI_WALK, y0_ + 0.25).intersection(street.union(extras['walk_s'])))
    cx0, cx1, cy0, cy1 = extras['cross_box']          # (gate_town's crossing over 성산로, kerb to kerb)
    W_parts.append(box(cx0, cy0 - 0.5, cx1, cy1 + 0.8))
    # (west to the arm lamp at x -116.8 only: past it 성산로's south walk is 1.5 m, the lamp stands in it and no walker
    # gets by, so the 18 m strip beyond was a piece of walk_open shut off from the rest)
    W_parts.append(extras['walk_s'].intersection(box(-116.2, -480.0, -55.0, -440.0)))
    # 그랜드백화점 앞마당 (2026-11-15; the 1997-07-28 scans 27/18 · 27/19): paved from the store's front out to 양화로's and
    # 1997년 신촌로's walks, west of the turning lane by the kiosk (GRAND_YARD_BOX): how one walked from the one to the
    # south-west crossing (the game's rounded corner east of it is the turning lane and its hatched wedge then, 4.10.4)
    yard = unary_union([A[k].poly(-A[k].half - A[k].walk, A[k].half + A[k].walk) for k in ('sinchon_w', 'seogang')]).intersection(
        box(*GRAND_YARD_BOX)).convex_hull.difference(road).difference(Polygon(GRAND_1997).buffer(0.3))
    W_parts.append(yard.difference(unary_union([_box(b).buffer(0.4) for b in blocks
                                                if len(b) == 12 and b[6] > 0 and _box(b).intersects(yard)])))
    # the carriageways too (2026-11-16, user's request): 연세로's from the bridge to the junction and the five arms'
    # within REACH, so the walker may step off the kerb anywhere and cross where 1997 had no zebra (연세로's, 양화로's and
    # 신촌로's mouths: the north and south corners meet over the asphalt now, not only under it).  The cars stop short of
    # the walker (web/src/town.js).  성산로's stays shut but for its crossing: its north kerb is the campus's own edge
    W_parts.append(street.intersection(near))
    W_parts.append(street.intersection(box(-140.0, JC[1] - 10.0, -50.0, geo['y_top'] - 1.0)))
    # 신촌로's south walk behind stair 5 and the kiosk (2026-11-21: the 1997 kerb, SE_KERB, leaves 0.7 m between it and
    # the stairwell; 52204 has the walk on past them to 한일은행's front): 3 m more behind the walk's back, s 46 - 80
    ae = A['sinchon_e']
    se_back = ae.poly(-ae.half - ae.walk - 3.0, -ae.half - ae.walk + 0.5, 46.0, 80.0)
    W_parts.append(se_back.difference(road).difference(unary_union([_box(b).buffer(0.4) for b in blocks
                                                                    if len(b) == 12 and b[6] > 0 and _box(b).intersects(se_back)])))
    # 성산로's too (2026-11-21, user's request: to cross where there is no zebra, from the gate to the bridge and along the
    # road): its carriageway and south walk the length gate_town lays it (x -480 .. 340), open along the north kerb
    # (the campus's walk), walled at its two ends and along the south walk's back
    W_parts.append(extras['ssr_open'])
    # 독수리다방's yard (yro97.DOK97; 2026-11-21): from 연세로's walk in to the house's walls and door and along the
    # street house's front (the lane north of it is no walk, as before)
    dk = yro97.DOK97
    # (and 창천교회's front yard north of it over the lane, yro97.CHURCH_YARD: to the church's west front)
    dk_open = unary_union([Polygon(dk['yard']), Polygon(dk['fore'])] + [Polygon(p_) for p_ in yro97.CHURCH_YARD])
    dk_walls = unary_union([Polygon(dk['main']).buffer(0.35), Point(dk['bay'][0], dk['bay'][1]).buffer(dk['bay'][2] + 0.3)]
                           + [_box(b).buffer(0.4) for b in blocks if len(b) == 12 and b[6] > 0 and _box(b).intersects(dk_open)])
    W_parts.append(dk_open.difference(dk_walls))
    Wk = unary_union(W_parts).buffer(0.05).buffer(-0.05)
    walk_open, walk_holes, barrier = [], [], []
    kn_ = extras['kerb_n'][np.argsort(extras['kerb_n'][:, 0])]
    # (no wall on 성산로's north kerb or north of it: the campus's side)
    campus_side = lambda q_: -480.5 < q_[0] < 340.5 and q_[1] > float(np.interp(q_[0], kn_[:, 0], kn_[:, 1])) - 0.4
    for pg in (Wk.geoms if hasattr(Wk, 'geoms') else [Wk]):
        if pg.geom_type != 'Polygon' or pg.area < 4.0:
            continue
        pg = shapely.geometry.polygon.orient(pg, 1.0)
        sp_ = pg.simplify(0.2)
        walk_open.append(R2(list(sp_.exterior.coords)[:-1]))
        walk_holes += [R2(list(h.coords)[:-1]) for h in sp_.interiors]       # (the carriageway between two crossings)
        for lr in [pg.exterior] + list(pg.interiors):
            c = list(lr.coords)
            for p, q in zip(c[:-1], c[1:]):
                p, q = np.array(p), np.array(q)
                d = q - p
                L = float(np.linalg.norm(d))
                if L < 1e-3:
                    continue
                nrm = np.array([d[1], -d[0]]) / L                 # (outward: right of a counter-clockwise ring)
                m = max(1, int(math.ceil(L / 1.5)))
                for i in range(m):
                    a_, b_ = p + d * (i / m), p + d * ((i + 1) / m)
                    if campus_side((a_ + b_) / 2):
                        continue
                    barrier.append(R2([a_ - nrm * 0.05, b_ - nrm * 0.05, b_ + nrm * 0.85, a_ + nrm * 0.85]))
    # ---- lamps along the kerbs (every 30 m, both sides; none in a crossing), the subway's entrances at the corners
    props = []
    ent_roofs = unary_union([_box([c_[0], c_[1], L_, W_, math.radians(a_)]).buffer(1.0) for no_, (c_, a_, L_, W_) in ENT97.items()
                             if no_ not in ENT97_LATE])
    # (a roof found later, ENT97_LATE: a lamp under it slides along the kerb out past it, keeping its place in the list)
    ent_late = unary_union([_box([c_[0], c_[1], L_, W_, math.radians(a_)]).buffer(1.0) for no_, (c_, a_, L_, W_) in ENT97.items()
                            if no_ in ENT97_LATE])
    apron_in = Polygon(ROT_APRON).buffer(-0.3)
    road_l = road.buffer(-0.2)
    shapely.prepare(road_l)
    for k, a in A.items():
        s0 = (xs[k] if k == 'baekbeom' else xs_rng[k]) + 12.0       # (the rule's mouths but 서강로's crossing)
        s1 = min(a.cum[-1] - 5.0, REACH + 60.0) if k != 'yonsei' else float(ya.ls.project(Point(gt.YONSEI_X, geo['y_top'] - 12.0)))
        for s in np.arange(s0, s1, 30.0):
            if k == 'seogang' and xs[k] - 1.5 < s < xs[k] + deps[k] + 1.5:       # (not on its crossing's landings)
                continue
            p, t, n = a.at(s)
            for sgn in (1, -1):
                o_k = -se_kerb(s) if k == 'sinchon_e' and sgn < 0 else a.half    # (신촌로's south kerb: SE_KERB)
                q = p + n * sgn * (o_k + 0.7)
                if k == 'yonsei' and q[1] > -508.0:          # (south of the baked sun shadow's edge)
                    continue
                if apron_in.contains(Point(*q)) or road_l.contains(Point(*q)):   # (the island's wedge, the corners' asphalt)
                    continue
                if shapely.intersects(ent_roofs, Point(*q)):                      # (a stair canopy of 1997: ENT97)
                    continue
                t_ = t
                if shapely.intersects(ent_late, Point(*q)):
                    c_ = np.array(ent_late.centroid.coords[0])
                    away = 1.0 if float((q - c_) @ t) >= 0 else -1.0
                    ds = 0.0
                    while shapely.intersects(ent_late, Point(*q)) and ds < 15.0:
                        ds += 0.5
                        p_, t_, n_ = a.at(s + away * ds)
                        q = p_ + n_ * sgn * (a.half + 0.7)
                rot = math.atan2(t_[1], t_[0]) + (math.pi if sgn < 0 else 0.0)
                props.append(['lamp_arm', round(float(q[0]), 2), round(float(q[1]), 2), round(rot, 3)])
    # 2호선 신촌역 (1984): eight stairs down from the corners (OSM's entrance nodes and today's numbers; 6 is the
    # same in the papers of 1995 - 99, the others' 1997 numbers not known: 고증 4.10.6)
    EXITS = [(1, -137.0, -942.0), (2, -110.0, -930.0), (3, -88.0, -930.0), (4, -63.0, -945.0), (5, -28.0, -976.0),
             (6, -56.0, -1011.0), (7, -149.0, -995.0), (8, -172.0, -968.0)]
    entrances, coll, coll_rng = [], [], []
    for no, x, y in EXITS:
        # set on the walk 1.2 m in from its back edge, its long side along the street it stands on
        for arms_ in (A_dec, A):                        # (the first places, with 서강로 on its old line; then now)
            best = min(arms_.values(), key=lambda a: a.ls.distance(Point(x, y)))
            s = float(best.ls.project(Point(x, y)))
            p, t, n = best.at(s)
            side = 1 if float((np.array([x, y]) - p) @ n) > 0 else -1
            w_ = (YRO_WALK_W if side > 0 else YRO_WALK_E) if best.name == 'yonsei' else best.walk
            q = p + n * side * (best.half + w_ - 2.0)
            ang = math.atan2(t[1], t[0])
            L, Wd = 7.4, 2.6
            if arms_ is A_dec:
                coll_rng.append(R2(_box([q[0], q[1], L + 0.2, Wd + 0.2, ang]).exterior.coords[:4]))     # (the first places)
        if best.name == 'yonsei':
            # (on 연세로's 3 - 4 m walks: 1.6 m across by the kerb, where the ginkgos leave room round the first places, so that a
            # walker passes along the shop fronts)
            Wd = 1.6
            q = p + n * side * (best.half + 0.15 + Wd / 2)
        elif best.name == 'seogang' and s < xs['seogang']:
            # (on 1997년 신촌로's walk short of its crossing, 30 m out since 2026-11-14: 1.6 m across against the walk's
            # back, so that a walker passes along the kerb to the crossing)
            Wd = 1.6
            q = p + n * side * (best.half + best.walk - 0.15 - Wd / 2)
        e = [round(float(q[0]), 2), round(float(q[1]), 2), round(ang, 4), L, Wd, no, round(ground(*q), 2)]
        if no in ENT97:
            # (where the scans of July 1997 have its roof, ENT97: the stairwell 0.6 - 0.7 m inside the roof's edge all
            # round, its open end the roof's sign end; after its 7 fields the roof's length, width and top over the walk:
            # blender/town.py entrances draws the canopy)
            c_, a_, L_, W_ = ENT97[no]
            e = [c_[0], c_[1], round(math.radians(a_), 4), round(L_ - 1.4, 2), round(W_ - 1.3, 2), no, round(ground(*c_), 2),
                 L_, W_, ENT97_ROOF]
        entrances.append(e)
        coll.append(R2(_box([e[0], e[1], e[3] + 0.2, e[4] + 0.2, e[2]]).exterior.coords[:4]))
    # (an entrance the island's wedge now covers: on the walk east of its turning lane, nearest OSM's node)
    kerb_e = LineString(ROT_APRON[2:11])
    for i, (no, x, y) in enumerate(EXITS):
        if no in ENT97 or not apron_in.intersects(Polygon(coll[i])):
            continue
        d_ = float(kerb_e.project(Point(x, y)))
        p = np.array(kerb_e.interpolate(d_).coords[0])
        t = np.array(kerb_e.interpolate(d_ + 1.0).coords[0]) - np.array(kerb_e.interpolate(d_ - 1.0).coords[0])
        t = t / np.linalg.norm(t)
        q = p + np.array([-t[1], t[0]]) * (ROT_APRON_WALK - 0.1 - 0.8)    # (east of the kerb, against the walk's back: 1.6 m across)
        ang = math.atan2(t[1], t[0])
        entrances[i] = [round(float(q[0]), 2), round(float(q[1]), 2), round(ang, 4), 7.4, 1.6, no, round(ground(*q), 2)]
        coll[i] = R2(_box([q[0], q[1], 7.6, 1.8, ang]).exterior.coords[:4])
    # (the eight-sided kiosk between stairs 5 and 6, ENT97_KIOSK: its box among the stairs', so that the trees keep clear)
    kx_, ky_, kr_ = ENT97_KIOSK
    coll.append(R2(_box([kx_, ky_, 2 * kr_, 2 * kr_, 0.0]).exterior.coords[:4]))
    town['kiosks'] = [[kx_, ky_, kr_, round(ground(kx_, ky_), 2)]]
    # ---- 연세로's ginkgo rows (51979 · 52106, 1996: both walks from the junction to the bridge, a crown to every
    # shop front; 52108 the same down the south arm), 1.1 m in from the kerb, none at the crossings, the side
    # streets' mouths, the subway's stairs or under the bridge; new trees go at the end of campus.json's list
    # (decided round the rule's crossings and the entrances' first places: xs_rng, coll_rng)
    trees = []
    busy_t = unary_union([Polygon(c_) .buffer(1.5) for c_ in coll_rng] +
                         [a.poly(-a.half - 6, a.half + 6, xs_rng[k] - 3.0, xs_rng[k] + 8.0) for k, a in A_dec.items()] +
                         [ya.poly(-ya.half - 6, ya.half + 6, s_mid_rng - 3.0, s_mid_rng + 8.0)])
    s_top_t = float(ya.ls.project(Point(gt.YONSEI_X, -508.0)))           # (south of the baked sun shadow's edge)
    # 연세로's row from its own stream (random.Random(4813)), 8 m apart (2010 skyview: the crowns' autocorrelation
    # 8.1 - 8.4 m along both walks from y -517 to -790; 7 m before); 4802 skips the draws the old row took, so that
    # 백범로's row keeps its own
    rnd_y = random.Random(4813)
    for _ in range(YRO_GINKGO_DRAWS):
        rnd.random()
    busy_t = busy_t.union(unary_union([ya.poly(-ya.half - 6, ya.half + 6, float(ya.ls.project(Point(gt.YONSEI_X, y_))) - 5.0,
                                               float(ya.ls.project(Point(gt.YONSEI_X, y_))) + 5.0) for y_ in (YRO_CROSS2_Y, gt.YZEBRA2[0] - 2.75)]))
    bb_row = []                                     # (서강로's: [index, side, the place decided, the draw along])
    for k, s0, s1, r_, step in (('yonsei', xs_rng['yonsei'] + 9.0, s_top_t, rnd_y, YRO_GINKGO_STEP),
                                ('baekbeom', xs_rng['baekbeom'] + 9.0, A_dec['baekbeom'].cum[-1] - 20.0, rnd, 7.0)):
        a = A_dec[k]
        for side in (1, -1):
            gaps = GAPS[-side] if k == 'yonsei' else []          # (+n is west on 연세로: side +1 west)
            for s in np.arange(s0 + (2.0 if side > 0 else 5.5), s1, step):
                p, t, n = a.at(s)
                j_ = r_.uniform(-0.4, 0.4)
                q = p + n * side * (a.half + 1.1) + t * j_
                if any(g1 - 4.0 < q[1] < g0 + 4.0 for g0, g1 in gaps) or busy_t.contains(Point(*q)):
                    continue
                if k == 'baekbeom':
                    bb_row.append((len(trees), side, q, j_))
                trees.append(['ginkgo', round(float(q[0]), 2), round(float(q[1]), 2), round(r_.uniform(0.62, 0.78), 2),
                              round(r_.uniform(0, 6.28), 2)])
        if k == 'yonsei':
            # (the row holds YRO_TREE_SLOTS places in campus.json's list, as the 7 m row had, so that the trees after it
            # keep their models: short of it, more trees on the banks west of the bridge beside gate_town's own, as
            # tools/build_campus.py TOWN_TREE_SLOTS does; random.Random(4814))
            assert len(trees) <= YRO_TREE_SLOTS, len(trees)
            # (decided at the bank trees' first places, their 6th field, and on the banks as they were: gate_town
            # layout's secs_rng; set down by as much from where they stand)
            rb = random.Random(4814)
            rxy_ = lambda t_: tuple(t_[5]) if len(t_) > 5 else (t_[1], t_[2])
            src = [t_ for t_ in extras['trees'] if t_[0] in ('poplar', 'zelkova', 'oak', 'zelkova_young') and rxy_(t_)[0] < gt.BRIDGE[0] - 12]
            taken_r = [rxy_(o_) for o_ in extras['trees'] + trees]
            for _ in range(4000):
                if len(trees) >= YRO_TREE_SLOTS or not src:
                    break
                t0 = rb.choice(src)
                du, dv = rb.choice((-1, 1)) * rb.uniform(3.5, 6.0), rb.uniform(-1.5, 1.5)
                q = (round(rxy_(t0)[0] + du, 2), round(rxy_(t0)[1] + dv, 2))
                if min(math.hypot(o_[0] - q[0], o_[1] - q[1]) for o_ in taken_r) < 3.0 or \
                        not extras.get('bank_rng', extras['bank']).contains(Point(*q)):
                    continue
                taken_r.append(q)
                trees.append([t0[0], round(t0[1] + du, 2), round(t0[2] + dv, 2), round(rb.uniform(0.5, 0.8), 2), round(rb.uniform(0, 6.28), 2)])
            n_bank = len(trees) - sum(1 for t_ in trees if t_[0] == 'ginkgo')
    # 서강로's row, decided on its old line (above), stands on the scans' line: each tree as far along it and on the same
    # side, 1.1 m in from the kerb; the west row north of the crossing behind the corner's kerb (ROT_S_KERB), none on
    # the crossing's landings or the subway's stairs (moved along the row), in their places in the list
    ab, ks_ = A['baekbeom'], LineString(ROT_S_KERB)
    s_cx = (xs['baekbeom'] - 1.5, xs['baekbeom'] + deps['baekbeom'] + 1.5)
    busy_b = unary_union([Polygon(c_).buffer(1.2) for c_ in coll])
    for i, side, qo, j_ in bb_row:
        s_n = float(ab.ls.project(Point(*qo)))
        for ds in (0.0, 2.5, -2.5, 5.0, -5.0):
            s_ = s_n + ds
            if s_cx[0] < s_ < s_cx[1]:
                s_ = s_cx[0] if s_n + ds < (s_cx[0] + s_cx[1]) / 2 else s_cx[1]
            p, t, n = ab.at(s_)
            q = p + n * side * (ab.half + 1.1) + t * j_
            if side < 0 and s_ < s_cx[0]:                    # (west of the lanes north of the crossing: the corner)
                d_k = float(ks_.project(Point(*q)))
                pk = np.array(ks_.interpolate(d_k).coords[0])
                tk = np.array(ks_.interpolate(min(d_k + 0.5, ks_.length)).coords[0]) - np.array(ks_.interpolate(max(d_k - 0.5, 0.0)).coords[0])
                tk = tk / np.linalg.norm(tk)
                q = pk + np.array([-tk[1], tk[0]]) * 1.1
            if not busy_b.contains(Point(*q)):
                break
        trees[i][1:3] = [round(float(q[0]), 2), round(float(q[1]), 2)]
    # (백범로's ginkgos the island's wedge now covers: moved in their places in the list to the walk east of its
    # turning lane, 1.1 m in from its kerb, 7 m apart from the crossing north, clear of the entrances)
    road_in = road.buffer(0.6)
    lost = [i for i, t_ in enumerate(trees) if i >= YRO_TREE_SLOTS and road_in.contains(Point(t_[1], t_[2]))]
    busy_e = unary_union([Polygon(c_).buffer(1.5) for c_ in coll])
    d_ = kerb_e.length - 6.0
    for i in lost:
        while d_ > 4.0:
            p = np.array(kerb_e.interpolate(d_).coords[0])
            t = np.array(kerb_e.interpolate(d_ + 1.0).coords[0]) - np.array(kerb_e.interpolate(d_ - 1.0).coords[0])
            t = t / np.linalg.norm(t)
            q = p + np.array([-t[1], t[0]]) * 1.1
            d_ -= 7.0
            if not busy_e.contains(Point(*q)) and not road_in.contains(Point(*q)):
                trees[i][1:3] = [round(float(q[0]), 2), round(float(q[1]), 2)]
                break
    # (연세로's ginkgos the north wedges' asphalt covers: in their places in the list, north along their row to where the
    # kerb is 1 m off again)
    road_t = road.buffer(1.0)
    for i, t_ in enumerate(trees[:YRO_TREE_SLOTS]):
        if t_[0] == 'ginkgo' and road_in.contains(Point(t_[1], t_[2])):
            y_ = t_[2]
            while road_t.contains(Point(t_[1], y_)) and y_ < t_[2] + 30.0:
                y_ += 0.25
            trees[i][2] = round(y_, 2)
    props += [['lamp_arm', x_, y_, r_] for x_, y_, r_ in ROT_LAMPS97]
    # (a ginkgo under a stair canopy of 1997, ENT97: moved in its place in the list out along the row to the roof's
    # nearer end, 1.5 m clear of it)
    for t_ in trees:
        if t_[0] != 'ginkgo':
            continue
        for c_, a_, L_, W_ in ENT97.values():
            u_ = np.array([math.cos(math.radians(a_)), math.sin(math.radians(a_))])
            d_ = np.array(t_[1:3]) - np.array(c_)
            du, dv = float(d_ @ u_), float(d_ @ np.array([-u_[1], u_[0]]))
            if abs(du) < L_ / 2 + 1.5 and abs(dv) < W_ / 2 + 0.8:
                q = np.array(t_[1:3]) + u_ * ((L_ / 2 + 1.5) * (1 if du >= 0 else -1) - du)
                t_[1:3] = [round(float(q[0]), 2), round(float(q[1]), 2)]
    # the island's bed in summer (52127, August 1996; BED): the clipped mound in the middle, the summer bed's lengths
    # in rings round it, the lawn outside the ground's grass.  May 1996's pansy border (52158) had 23 places in the
    # shrubs' list: the first 23 of these take them, the rest go at the shrubs' end (shrubs_late: tools/build_campus.py)
    bed_ = [['topiary_dome', round(float(ic[0]), 2), round(float(ic[1]), 2), 1.0, 0.4]]
    for i in range(6):
        a_ = 2 * math.pi * i / 6
        bed_.append(['topiary_dome', round(float(ic[0] + ISLAND_MOUND_R * math.cos(a_)), 2),
                     round(float(ic[1] + ISLAND_MOUND_R * math.sin(a_)), 2), 1.0, round(a_ + 1.1, 2)])
    for k_, (rr_, nn) in enumerate(ISLAND_FLOWER_RINGS):
        for i in range(nn):
            a_ = 2 * math.pi * (i + 0.5 * (k_ % 2)) / nn
            bed_.append(['summer_bed', round(float(ic[0] + rr_ * math.cos(a_)), 2), round(float(ic[1] + rr_ * math.sin(a_)), 2),
                         1.0, round(a_ + math.pi / 2, 2)])
    shrubs, shrubs_late = bed_[:23], bed_[23:]
    # ---- 신촌 로터리's bus stops (52145 · 52142: flat pale roofs at the kerb, buses pulled in and people waiting on
    # 양화로's south walk at the 그랜드백화점 corner; 52145 · 52187: on 신촌로's south walk in front of 한일은행)
    stops_r, waiting = rot_stops(A)
    town['stops'] = town.get('stops', []) + stops_r
    # ---- signs: the shops' boards along 연세로 are yro_rows' (tools/yro97.py: the anthologies' street maps, sign_yro97);
    # here the junction's landmarks' (sign_sinchon2: its first twelve cells, the kinds of shop that stood for the rows
    # south of the maps before 2026-11-21, are unused now)
    fronts[1][-1][6] = 5                                   # (홍익문고: five storeys)
    signs2 = []
    # the landmarks' signs where the 1995 · 1996 photos have them (LM_SHAPE); a landmark without a shape: over its top,
    # facing the junction
    for lm, b in corner:
        sh = LM_SHAPE.get(lm['name'])
        if sh:
            o_ = sh['outline']
            for sg in sh['signs']:
                p0_, p1_ = np.array(o_[sg['side']]), np.array(o_[(sg['side'] + 1) % len(o_)])
                L_ = float(np.linalg.norm(p1_ - p0_))
                t_ = (p1_ - p0_) / L_
                n_ = np.array([t_[1], -t_[0]])                  # (outward: right of a counter-clockwise outline)
                q = p0_ + t_ * (L_ / 2 if sg.get('at') is None else sg['at']) + n_ * sg.get('off', 0.25)
                z_ = LM_TOP[lm['name']] - sg['top'] if 'top' in sg else b[5] + 0.3 + sg['up']
                signs2.append([round(float(q[0]), 2), round(float(q[1]), 2), round(z_, 2), round(math.atan2(n_[1], n_[0]), 4),
                               sg['w'], sg['h'], sg['cell']])
            continue
        c, sn = math.cos(b[4]), math.sin(b[4])
        v = np.array(ISLAND['c']) - np.array(b[:2])
        # the face nearest the junction: of the four, the one whose outward normal points most at it
        faces = [(np.array([c, sn]), b[2] / 2, b[3]), (-np.array([c, sn]), b[2] / 2, b[3]),
                 (np.array([-sn, c]), b[3] / 2, b[2]), (-np.array([-sn, c]), b[3] / 2, b[2])]
        nrm, off, wid = max(faces, key=lambda f_: float(f_[0] @ v))
        q = np.array(b[:2]) + nrm * (off + 0.2)
        top = b[5] + 0.3 + _storey(b) * b[6]
        signs2.append([round(float(q[0]), 2), round(float(q[1]), 2), round(top - lm['sign_h'] / 2 - 0.6, 2),
                       round(math.atan2(nrm[1], nrm[0]), 4), round(min(wid - 2.0, lm['sign_h'] * 5.5), 2), lm['sign_h'], lm['sign']])
    # ---- the ground map round the walks (web/src/terrain.js: past the campus's map): the town's ground asphalt as
    # gate_town paints it, the sidewalks paved
    # (the island's lawn left unpainted: the ground's grass; the stairwells cut out of the ground, B: web/src/terrain.js)
    holes = [_box([e[0], e[1], e[3] - 0.25, e[4] - 0.45, e[2]]) for e in entrances]
    paints = dict(asphalt=[box(TSPLAT['x0'], TSPLAT['y0'], TSPLAT['x1'], TSPLAT['y1']).difference(
                      Point(*ISLAND['c']).buffer(ISLAND['r'] - 0.1))],
                  pavers=[walk, yard, unary_union([Polygon(e_).buffer(0.6) for e_ in [[(x_, y_) for x_, y_ in c_] for c_ in coll]])],
                  hole=holes)
    town['blocks'] = blocks
    town['kerbs'] += kerbs
    town['paint'] += paint
    town['zebra'] += zebra
    town['lanes'] += lanes
    town['signals'] = signals
    town['heads'] = heads
    town['peds'] = peds                                        # (web/src/town.js PedHeads)
    town['entrances'] = entrances
    town['signs2'] = signs2
    town['landmarks'] = lm_draw                                # (blender/town.py landmarks(), web/src/ui.js's map)
    town['shops'] = yro_shops
    town['signs'] = []            # (gate_town's sixteen boards north of y -640: the houses they hung on went, yro_rows)
    # (연세로's wall signs and banner: yro_; none on 금강제화's and 홍익문고's walls, which carry their own boards:
    # blender/town.py _kumkang, _hongik)
    own_walls = unary_union([kk_pg, hk_pg]).buffer(1.6)
    town['vsigns'] = yro97.vsign_cells([q for q in yro_wall_signs(blocks) if not own_walls.contains(Point(q[0], q[1]))])
    town['signs2'] = [q for q in town['signs2'] if not own_walls.contains(Point(q[0], q[1]))]
    town['banner'] = yro_banner(geo, ground)
    print('연세로: rows %d + %d, gone %d, wall signs %d, ginkgos %d (+ %d on the banks)' % (
        len(fronts[1]), len(fronts[-1]), n_yro_gone, len(town['vsigns']), YRO_TREE_SLOTS - n_bank, n_bank))
    town['rotary'] = dict(c=list(JC), reach=REACH, arms={k: dict(half=a.half, walk=a.walk, cross=round(xs[k], 1))
                                                          for k, a in A.items()})
    paths = [dict(kind='primary', w=2 * A[k].half, pts=[[round(float(x), 1), round(float(y), 1)] for x, y in A[k].P[::4]])
             for k in ('sinchon_w', 'sinchon_e', 'seogang')] + \
            [dict(kind='secondary', w=2 * A['baekbeom'].half, pts=[[round(float(x), 1), round(float(y), 1)] for x, y in A['baekbeom'].P[::4]]),
             dict(kind='tertiary', w=2 * ya.half, pts=[[round(float(x), 1), round(float(y), 1)] for x, y in ya.P[::4]
                                                       if y < -630.0])]
    # the walkers' sidewalks (web: a crowd of its own on 연세로): each side's middle, the bridge to the corner
    walks_ = []
    for side in (1, -1):
        o = side * (ya.half + (YRO_WALK_W if side > 0 else YRO_WALK_E) / 2)
        s1 = float(ya.ls.project(Point(gt.YONSEI_X, geo['y_top'] - 3.0)))
        s0 = xs['yonsei'] + 7.0
        while road_t.contains(Point(*(ya.at(s0)[0] + ya.at(s0)[2] * o))) and s0 < s1 - 20.0:
            s0 += 1.0                                  # (the corner's end of each: clear of the north wedges' asphalt)
        walks_.append(R2(lane_pts('yonsei', o, s1, s0, 3.0)))
    town['walks'] = walks_
    print('신촌 로터리: blocks +%d (rows %d, fill %d, gone %d + %d for the moved 연세로), kerbs %d, lanes %d, lamps %d' % (
        len(new), sum(len(v) for v in fronts.values()), n_fill, n_gone, n_moved, len(kerbs), len(lanes), len(props)))
    town['island'] = dict(c=list(ISLAND['c']), r=ISLAND['r'], bed=[[r_, k_] for r_, k_ in BED],
                          mound=[ISLAND_MOUND['h'], ISLAND_MOUND['r']])
    # people standing about (web/src/main.js: the town's crowd) and the blue sign over 연세로 (blender/town.py)
    waiting['groups'] += rot_waiting(fronts[1][-1], corner, A, waiting['singles'])
    town['waiting'] = waiting
    town['dirsign'] = rot_dirsign(ya, s_mid)
    town['rot_fence'] = rot_fence(A)
    # the names over them (campus.json markers: the walk's tags, the bird's-eye pins, the map)
    hk = fronts[1][-1]
    top = lambda b: round(b[5] + 0.3 + _storey(b) * b[6] + 1.0, 1)
    markers = [dict(name=lm['name'], pos=[b[0], b[1]], top=top(b)) for lm, b in corner] + [
        dict(name='홍익문고', pos=[hk[0], hk[1]], top=round(lm_mouth[1]['top'] + 1.0, 1)),
        dict(name='금강제화', pos=[round(kk_pg.centroid.x, 2), round(kk_pg.centroid.y, 2)], top=round(lm_mouth[0]['top'] + 1.0, 1)),
        dict(name='신촌 로터리', pos=list(ISLAND['c']), top=round(ground(*ISLAND['c']) + 9.0, 1)),
        dict(name='신촌역 (2호선)', pos=[entrances[1][0], entrances[1][1]], top=round(entrances[1][6] + 5.0, 1))]
    print('신촌 로터리: the walker\'s walks %d (holes %d), barrier %d boxes' % (len(walk_open), len(walk_holes), len(barrier)))
    # (the walkers' signals' poles: the walker goes round them)
    ped_coll = [R2([(x_ - 0.18, y_ - 0.18), (x_ + 0.18, y_ - 0.18), (x_ + 0.18, y_ + 0.18), (x_ - 0.18, y_ + 0.18)]) for x_, y_, *_ in peds]
    return dict(markers=markers, props=props, colliders=barrier + coll + ped_coll, paints=paints, paths=paths, corner=corner, trees=trees,
                shrubs=shrubs, shrubs_late=shrubs_late, walk_open=walk_open, walk_holes=walk_holes)


# ----------------------------------------------------------------------------- the 1995 · 1996 rooftop photos
# (고증 4.10 「옥상 사진의 카메라」 · 「게임에 옮긴 것」): the paint on the junction, its bus stops, people standing about
# 「연세대」 in strokes on a glyph's unit box (u across, v up the text; road lettering is drawn long along the way)
ROT_GLYPHS = [
    [[(0.28 + 0.2 * math.cos(t), 0.79 + 0.13 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 13)],      # 연: ㅇ
     [(0.74, 1.0), (0.74, 0.52)], [(0.5, 0.88), (0.74, 0.88)], [(0.5, 0.68), (0.74, 0.68)],                 #  ㅕ
     [(0.14, 0.44), (0.14, 0.08), (0.86, 0.08)]],                                                          #  ㄴ
    [[(0.34, 0.95), (0.06, 0.08)], [(0.3, 0.62), (0.56, 0.08)],                                            # 세: ㅅ
     [(0.92, 1.0), (0.92, 0.0)], [(0.74, 0.92), (0.74, 0.12)], [(0.6, 0.55), (0.74, 0.55)]],                #  ㅔ
    [[(0.52, 0.88), (0.08, 0.88), (0.08, 0.12), (0.54, 0.12)],                                             # 대: ㄷ
     [(0.94, 1.0), (0.94, 0.0)], [(0.74, 0.92), (0.74, 0.1)], [(0.74, 0.55), (0.94, 0.55)]]]                #  ㅐ


def rot_letters():
    """「연세대」 north of the island (ROT_LETTERS): white strokes, 0.2 m wide"""
    L = ROT_LETTERS
    b = math.radians(L['up'])
    ev = np.array([math.sin(b), math.cos(b)])                 # (up the text: the way its readers drive)
    eu = np.array([ev[1], -ev[0]])                            # (along a line of it: to their right)
    c = np.array(L['c'])
    out = []
    for i, glyph in enumerate(ROT_GLYPHS):
        u0 = (i - 1) * (L['w'] + 0.1) - L['w'] / 2
        for st in glyph:
            pts = [tuple(c + eu * (u0 + u * L['w']) + ev * ((v - 0.5) * L['h'])) for u, v in st]
            out.append(dict(kind='white', w=0.2, pts=[[round(float(x), 2), round(float(y), 2)] for x, y in pts]))
    return out


def rot_marks():
    """the junction's paint as the 1997 scans have it (27/18 · 27/19, the same places within 0.2 m; 1995's 52142 · 52145
    have them too): the triangles (ROT_TRI, an outline and the smaller one inside), the arrows (ROT_ARROWS: a straight
    arrow's head at the point, 2.2 m of shaft behind) and the turning guides of short dashes (ROT_GUIDES)"""
    out = []
    R2_ = lambda pts: [[round(float(x), 2), round(float(y), 2)] for x, y in pts]
    for tri, inner in ROT_TRI:
        for t_ in [tri] + ([inner] if inner else []):
            out.append(dict(kind='yellow', w=0.2, pts=R2_(list(t_) + [t_[0]])))
    for hx, hy, brg in ROT_ARROWS:
        u = np.array([math.sin(math.radians(brg)), math.cos(math.radians(brg))])
        v = np.array([-u[1], u[0]])
        h_ = np.array([hx, hy])
        out.append(dict(kind='white', w=0.18, pts=R2_([h_ - u * 1.4, h_ - u * 3.6])))
        for d_ in (-0.5, -0.25, 0.0, 0.25, 0.5):
            out.append(dict(kind='white', w=0.22, pts=R2_([h_, h_ - u * 1.5 + v * d_])))
    for g in ROT_GUIDES:                                     # (dashes 1 m long, 1 m apart)
        ls = LineString(gt._chaikin(g, 2))
        for d0 in np.arange(0.0, ls.length - 0.5, 2.0):
            out.append(dict(kind='white', w=0.15, pts=R2_([ls.interpolate(d0).coords[0], ls.interpolate(min(d0 + 1.0, ls.length)).coords[0]])))
    return out + rot_wedge_marks()


def rot_wedge_marks():
    """the paint of the three corners that were road (ROT_WEDGE_PAINT and the lists after it): outlines and lines, the
    dashed runs, the arrows, the chevrons of the north-east band, the almond beside 그랜드's stop"""
    out = []
    R2_ = lambda pts: [[round(float(x), 2), round(float(y), 2)] for x, y in pts]

    def dense(pts, step=1.0):
        """the line with a point every step m at most (blender/town.py drapes each piece on the ground by its ends:
        a long one dips under the 5 m grid's folds)"""
        q = [np.array(pts[0], float)]
        for a_, b_ in zip(pts[:-1], pts[1:]):
            a_, b_ = np.array(a_, float), np.array(b_, float)
            m = max(1, int(math.ceil(float(np.linalg.norm(b_ - a_)) / step)))
            q += [a_ + (b_ - a_) * (i / m) for i in range(1, m + 1)]
        return q

    for kind, w_, pts in ROT_WEDGE_PAINT:
        out.append(dict(kind=kind, w=w_, pts=R2_(dense(pts, 2.0 if kind == 'white_dash' else 1.0))))
    for g, (on, step) in zip(ROT_WEDGE_DASH, ((3.0, 7.6), (1.7, 2.4))):
        ls = LineString(g)
        for d0 in np.arange(0.0, ls.length - on * 0.5, step):
            d1 = min(d0 + on, ls.length)
            out.append(dict(kind='white', w=0.15, pts=R2_([ls.interpolate(d).coords[0] for d in np.linspace(d0, d1, 3)])))
    for hx, hy, brg in ROT_WEDGE_ARROWS:                     # (as rot_marks': the head at the point, a shaft behind)
        u = np.array([math.sin(math.radians(brg)), math.cos(math.radians(brg))])
        v = np.array([-u[1], u[0]])
        h_ = np.array([hx, hy])
        out.append(dict(kind='white', w=0.18, pts=R2_(dense([h_ - u * 1.4, h_ - u * 4.4]))))
        for d_ in (-0.5, -0.25, 0.0, 0.25, 0.5):
            out.append(dict(kind='white', w=0.22, pts=R2_([h_, h_ - u * 1.5 + v * d_])))
    # the chevrons: from each point back west to the band's two edges (its outline is ROT_WEDGE_PAINT's)
    (ax, ay), (tx, ty), (bx, by) = (-85.0, -963.8), (-56.0, -962.0), (-83.6, -970.0)
    for cx, cy in ROT_NE_CHEVRONS:
        xb = cx - 2.7
        top = (xb, ay + (xb - ax) * (ty - ay) / (tx - ax) - 0.15)
        bot = (xb + 0.5, by + (xb + 0.5 - bx) * (ty - by) / (tx - bx) + 0.15)
        out.append(dict(kind='yellow', w=0.3, pts=R2_(dense([top, (cx, cy), bot]))))
    # the almond: two arcs between its tips, four bars across
    a, b = np.array(ROT_SW_ALMOND['a']), np.array(ROT_SW_ALMOND['b'])
    n = np.array([-(b - a)[1], (b - a)[0]]) / np.linalg.norm(b - a)
    hw = lambda t: ROT_SW_ALMOND['w'] / 2 * math.sin(math.pi * t)
    ts = np.linspace(0.0, 1.0, 13)
    side = lambda sg: [a + (b - a) * t + n * sg * hw(t) for t in ts]
    out.append(dict(kind='white', w=0.2, pts=R2_(side(1) + side(-1)[::-1][1:])))
    for t in (0.2, 0.4, 0.6, 0.8):
        c = a + (b - a) * t
        out.append(dict(kind='white', w=0.2, pts=R2_([c + n * hw(t), c - n * hw(t)])))
    return out


# where the buses' riders stand at the four corners (rot_stops): [a point 2 m behind the kerb, the way along the kerb
# (deg from east), the way from the road to the walk (deg)].  The buses pull in at the kerb beside the stairs' canopies
# (52146 · 52141 · 52204 · 52145): 양화로's south side north of stairs 7 (그랜드백화점's corner), 신촌로's south side by
# stairs 5 (한일은행), 양화로's north side between stairs 1 and 2 (금강제화), 신촌로's north side between 3 and 4
# (신촌로's south: past stair 5's open end, 2 m behind the 1997 kerb (SE_KERB); (-32.7, -975.2) before 2026-11-21)
ROT_WAIT97 = [((-152.8, -974.9), 162.0, 252.0), ((-19.97, -973.28), 23.0, 293.0),
              ((-122.4, -939.9), 26.0, 116.0), ((-71.8, -941.3), -32.4, 57.6)]


def rot_stops(A):
    """the rotary's four bus stops: no shelters (2026-11-15: the flat pale roofs the 1995 · 1996 photos and the scans
    have at the corners are the subway stairs' canopies, ENT97; the buses stop at the kerb beside them), so `stops` is
    empty; the people waiting: {groups: [[x, y]], singles: [[x, y, facing x, facing y]]}, where ROT_WAIT97 says (the
    same draws as when four 9 m roofs stood at 40 · 59 · 28 · 24 m out along the arms)"""
    stops, wait = [], dict(groups=[], singles=[])
    rnd = random.Random(4811)
    for (qx, qy), a_t, a_n in ROT_WAIT97:
        q = np.array([qx, qy])
        tt = np.array([math.cos(math.radians(a_t)), math.sin(math.radians(a_t))])
        nn = np.array([math.cos(math.radians(a_n)), math.sin(math.radians(a_n))])      # (away from the road)
        for u in (-2.6, -0.9, 0.7, 2.4):
            m = q + tt * (u + rnd.uniform(-0.3, 0.3)) - nn * rnd.uniform(0.1, 0.6)
            ang = rnd.uniform(-0.5, 0.5)
            f = -nn
            f = np.array([f[0] * math.cos(ang) - f[1] * math.sin(ang), f[0] * math.sin(ang) + f[1] * math.cos(ang)])
            wait['singles'].append([round(float(m[0]), 2), round(float(m[1]), 2), round(float(f[0]), 3), round(float(f[1]), 3)])
        g = q + nn * 1.6 + tt * rnd.uniform(-3, 3)
        wait['groups'].append([round(float(g[0]), 2), round(float(g[1]), 2)])
    return stops, wait


def rot_waiting(hk, corner, A, singles):
    """「홍익문고 앞에서 만나」: people waiting on the walk in front of 홍익문고 and of 그레이스백화점, looking out for
    someone (singles, appended) and a few in twos and threes (the groups returned)"""
    rnd = random.Random(4812)
    groups = []

    def row(c, n_, t_, us, d, gs):
        for u in us:
            m = c + n_ * (d + rnd.uniform(-0.3, 0.4)) + t_ * (u + rnd.uniform(-0.3, 0.3))
            ang = rnd.uniform(-0.9, 0.9)
            f = np.array([n_[0] * math.cos(ang) - n_[1] * math.sin(ang), n_[0] * math.sin(ang) + n_[1] * math.cos(ang)])
            singles.append([round(float(m[0]), 2), round(float(m[1]), 2), round(float(f[0]), 3), round(float(f[1]), 3)])
        for u, dd in gs:
            g = c + n_ * dd + t_ * u
            groups.append([round(float(g[0]), 2), round(float(g[1]), 2)])

    # 홍익문고: its front on 연세로 (the block's L axis points away from the street)
    na = np.array([math.cos(hk[4]), math.sin(hk[4])])
    row(np.array(hk[:2]) - na * (hk[2] / 2), -na, np.array([-na[1], na[0]]), (-3.4, -2.1, -0.6, 1.0, 2.6), 1.4,
        [(-1.2, 2.1), (2.2, 2.2)])
    # 그레이스백화점: its face towards 양화로, the east half of it
    for lm, b in corner:
        if lm['name'] != '그레이스백화점':
            continue
        c, sn = math.cos(b[4]), math.sin(b[4])
        faces = [(np.array([c, sn]), b[2] / 2, b[3]), (-np.array([c, sn]), b[2] / 2, b[3]),
                 (np.array([-sn, c]), b[3] / 2, b[2]), (-np.array([-sn, c]), b[3] / 2, b[2])]
        ctr = np.array(b[:2])
        near = np.array(A['sinchon_w'].ls.interpolate(A['sinchon_w'].ls.project(Point(*ctr))).coords[0])
        v = near - ctr
        nrm, off, wid = max(faces, key=lambda f_: float(f_[0] @ v) / np.linalg.norm(v))
        t_ = np.array([-nrm[1], nrm[0]])
        if float(t_ @ (np.array(JC) - ctr)) < 0:
            t_ = -t_                                           # (t_ towards the junction's end of the face)
        cf = ctr + nrm * off + t_ * (wid * 0.25)
        row(cf, nrm, t_, (-2.8, -1.2, 0.6, 2.4), 1.8, [(-0.2, 3.4), (3.6, 3.0)])
    return groups


def rot_fence(A):
    """the fence round the empty corner lot south of 홍익문고 (52005 · 52006, 1996.8: grey panels with yellow banners
    along their tops, at the back of 연세로's east walk and of 신촌로's north walk; today 엘리트 빌딩): its line, from
    홍익문고's south wall (y -912.6, tools/sinchon_rotary.py yro_rows) to the corner and east along 신촌로 for 36 m.
    (2026-11-15: the corner's sidewalk is the north-east wedge's, ROT_WEDGES: the fence behind it)"""
    ya = A['yonsei']
    out = []
    s0 = float(ya.ls.project(Point(gt.YONSEI_X, -912.4)))
    for s in np.linspace(s0, 0.0, 30):
        p, t, n = ya.at(s)
        out.append(p - n * (ya.half + YRO_WALK_E + 0.15))               # (east: -n on 연세로)
    line_e = wedge_back(ROT_WEDGES['ne'], 0.15)
    # the corner where the two back edges meet; the 연세로 line stops there, the 신촌로 one starts there
    cut = None
    for i in range(1, len(out)):
        seg = LineString([tuple(out[i - 1]), tuple(out[i])])
        if seg.intersects(line_e):
            cut = (i, seg.intersection(line_e))
            break
    if cut is None:
        return []
    i, x = cut
    xc = np.array(x.coords[0]) if x.geom_type == 'Point' else np.array(x.centroid.coords[0])
    pts = out[:i] + [xc]
    se = float(line_e.project(Point(*xc)))
    pts += [np.array(line_e.interpolate(d).coords[0]) for d in np.arange(se + 2.0, se + 36.0, 2.0)]
    return [[round(float(q[0]), 2), round(float(q[1]), 2)] for q in pts]


def rot_dirsign(ya, s_mid):
    """the blue direction sign over 연세로's northbound lanes (51979: 「모래내 ← · → 독립문」, a pole on the east kerb
    with an arm; DIRSIGN): its pole, the panel's middle, the way it faces, w, h, the panel's foot over the road.
    The panel is 1.45 : 1 in the photo (121 x 84 px): 3.2 m across at the 2.2 m the depth was set by, its right end
    half a metre inside the east kerb, its middle 4.4 m east of the road's (51979's camera; 4.4 m across and 3.1 m east
    of the middle before 2026-11-15).
    `mouth`: the sign and the name plate over 연세로's mouth (MOUTH_SIGN · MOUTH_SIGNAL: blender/town.py rot_dirsign
    draws them, the signal heads on the plate's arm are the web's)"""
    s = float(ya.ls.project(Point(gt.YONSEI_X, DIRSIGN[0])))
    p, t, n = ya.at(s)
    pole = p - n * (ya.half + 0.6)
    c = p - n * DIRSIGN_E
    ms, mg = MOUTH_SIGN, MOUTH_SIGNAL
    mouth = dict(pole=list(ms['pole']), x=list(ms['x']), h=ms['h'], z0=ms['z0'],
                 plate=dict(pole=list(mg['pole']), x=mg['plate'][0], w=mg['plate'][1], h=mg['plate'][2], z=mg['h'] - 0.55),
                 lplate=dict(x=mg['lplate'][0], w=mg['lplate'][1], h=mg['lplate'][2], z=5.9))
    return dict(pole=[round(float(pole[0]), 2), round(float(pole[1]), 2)], c=[round(float(c[0]), 2), round(float(c[1]), 2)],
                face=round(math.atan2(-t[1], -t[0]), 4), w=DIRSIGN_W, h=2.2, z0=DIRSIGN[1], mouth=mouth)


def town_splat(paints, path):
    """the town's ground map (TSPLAT): R asphalt, G paving, B the woods' floor (none), each drawn at four times the
    resolution and averaged (as build_campus.py's splat_aa), row 0 north"""
    S = TSPLAT
    k = 4
    W, H = int(round((S['x1'] - S['x0']) / S['res'])), int(round((S['y1'] - S['y0']) / S['res']))
    P = lambda x, y: ((x - S['x0']) / S['res'] * k, (S['y1'] - y) / S['res'] * k)
    out = []
    for layer in ('asphalt', 'pavers', 'hole'):
        im = Image.new('L', (W * k, H * k), 0)
        d = ImageDraw.Draw(im)
        for g in paints[layer]:
            for pg in (g.geoms if hasattr(g, 'geoms') else [g]):
                if pg.geom_type != 'Polygon' or pg.is_empty:
                    continue
                d.polygon([P(x, y) for x, y in pg.exterior.coords], fill=255)
                for h in pg.interiors:
                    d.polygon([P(x, y) for x, y in h.coords], fill=0)
        a = np.array(im, np.float32).reshape(H, k, W, k).mean(axis=(1, 3))
        out.append(a)
    a, p, h = out
    a = np.minimum(a, 255.0 - p)
    rgb = np.stack([a, p, h], -1)
    Image.fromarray(np.clip(rgb + 0.5, 0, 255).astype(np.uint8), 'RGB').save(path, optimize=True)
    return (W, H)


# ----------------------------------------------------------------------------- 연세로's rows, signs and banner (yro_)
# The shop rows from y -640 to the junction as the 1996 photos show them where they can be read (고증 4.10): from the
# junction north, the buildings of each side between its side streets.  [frontage m, storeys, wall (yro97.WALLS97: the
# 1996 photos' own, 고증 4.10.8 「벽」), depth m], from the segment's south end north.  Segments: GAPS split each side,
# 0 = the northmost.  blender/town.py draws a block whose wall field is YRO_WALL + a WALLS97 wall with the rows' own
# atlas (town_yro), so the town's atlas and 창천동's houses stay as they were
YRO_WALL = 8
YRO_FIXED = {
    # east, 연세로2길 (y -893) to the junction: the brick house OSM 356219100 (3 storeys in 52004 · 52006), 홍익문고
    # (OSM 356219103: 7.2 m on 연세로, 11 m deep; its storeys are the corner's, below).  South of it the corner lot stood
    # fenced in 1996 (52005 · 52006: yellow banners on the hoarding, a bus shelter in front; 엘리트 빌딩 now)
    (1, 4): [[7.2, 5, 2, 11.0], [12.4, 3, 0, 8.5]],
    # east, 연세로2길 north: the purple-grey four storeys whose south wall faces the side street (52106), a white three,
    # a low cream two, the white four with the long window bands and 비디오 signs (52004 · 52006)
    (1, 3): [[11.0, 4, 6, 13.0], [8.0, 3, 4, 11.0], [6.0, 2, 2, 10.0], [12.0, 4, 4, 13.0]],
    # west, the junction to the side street at y -884: 금강제화 on the corner (four storeys of white tile, the shoe shop's
    # sign over the ground floor, clinics, a 법무사 and 바둑 above, 52005 · 52006), a cream three
    (-1, 3): [[20.0, 4, 4, 14.0], [9.0, 3, 2, 11.0]],
    # west, north of it: the white five of INDIS · 기원 · 바둑 · 만화 (52006), the seven storeys of white tile with dark window
    # bands and 현대예식장's sign up its corner (52106 · 52006, 신영증권 on its roof)
    (-1, 2): [[13.0, 5, 4, 13.0], [24.0, 7, 4, 16.0]],
}
# the mix along the rest of 연세로 in 51979 · 52006 (both sides, the junction to the bridge): storeys and their share,
# frontages 5.5 - 12 m, every wall band (red brick seldom), flat roofs with tanks
YRO_MIX = dict(lv=[2, 3, 4, 5, 6, 7], p=[0.12, 0.25, 0.30, 0.18, 0.10, 0.05], w=(5.5, 12.0), dep=(10.0, 14.0),
               wall=[0, 1, 2, 2, 3, 3])
YRO_GINKGO_STEP = 8.0         # 연세로's ginkgos apart (2010 skyview, 고증 4.10)
YRO_TREE_SLOTS = 102          # (the places the 7 m row had in campus.json's tree list)
YRO_W_FRONTS = 28             # (the west row's fronts before 2026-11-15, its south end at the rounded corner: the signs' picks)
YRO_GINKGO_DRAWS = 327        # (the draws 4802 gave the old 7 m row on the old line: 123 places, 102 trees)
YRO_CROSS2_Y = -690.0         # the zebra over 연세로 at y -687.5 .. -692.4 (1997 frames 26/16 · 27/17), its middle
# 51979 (1996.5, from 홍익문고's roof: compare/yonsei_ro, solved again on the 1997 ground 2026-11-15, 고증 4.10.2) has the two
# crossings of the July 1997 frames (-575, -690) with a signal head hung before each; between them and the camera the
# sign and the festival's banner, set where their pixels put a 2.2 m panel 5.4 m over the road and the cloth's foot 4.6 m
# over it (they had been at -776 and -805 through the camera solved on the old ground, 10 and 9 m up on the new one)
DIRSIGN = (-720.0, 5.4)        # (y, the panel's foot over the road)
DIRSIGN_W, DIRSIGN_E = 3.2, 4.4    # its width (1.45 : 1), its middle east of the road's
# the festival's banner (1996.5): its cloth's west end tied to the lamp pole behind the west kerb in 51980 and 52106,
# their cameras solved on 연세로's 1997 paint (the crossings at -783 and -690, the yellow middle, the west kerb): its
# bottom edge there at y -741.6 · -737.9, 3.7 · 3.0 m over the road, the cloth 1.1 m high (51979 through its own camera:
# 3.2 m and 1.1 m at that depth; 고증 4.10.2 「연세로 현수막」).  -756 m, 4.6 m and 1.3 m before 2026-11-17 (51979 alone,
# its bottom's height taken).  Its east end is behind the east walk's ginkgos in all three
YRO_BANNER_Y = -740.0
YRO_BANNER_Z = (3.5, 1.1)     # (its bottom over the road, its height)


def yro_walk_poly(a, s_kerb, yx=None, old=False):
    """연세로's two sidewalks: YRO_WALK_W / _E from the junction to y -640, gate_town's north of it (4.8).
    old: as they were on the old line (YRO_WALK, gate_town's 14 m and 5 m walks), for the streams' decisions"""
    s640 = float(a.ls.project(Point(gt.YONSEI_X if yx is None else yx, Y_ROWS)))
    ww, we, wn = (YRO_WALK, YRO_WALK, 7.0 + 5.0 - a.half) if old else (YRO_WALK_W, YRO_WALK_E, gt.YONSEI_WALK)
    return unary_union([a.poly(-a.half - we, a.half + ww, 0.0, s640 + 0.5),
                        a.poly(-a.half - wn, a.half + wn, s640, s_kerb)])


def yro_rows(geo, blocks, ground):
    """연세로's rows from the bridge to the junction, house by house as the July 1997 scans, the roadview and the
    anthologies' street maps have them (tools/yro97.py ROWS; 고증 4.10.8), appended to blocks; south of the last side
    street of each side YRO_FIXED's (the 1996 photos: 홍익문고 and the brick house, 금강제화 and the cream three; east
    also the four north of 연세로2길).  gate_town's rows north of y -640 and whatever stands in the new ones or in
    독수리다방's lot go (b[6] < 0, their draws kept; the lot's street house of 1996 is added last).  Returns the fronts of each side, north to south (the last of the
    east side is 홍익문고, of the west 금강제화), how many went, and the shops' boards: [x, y, z of the board's middle,
    the way it faces (rad), width, height, cell of sign_yro97]."""
    rnd = random.Random(4805)
    ya = geo['arms']['yonsei']
    corner_cut = geo['cross_streets'].buffer(1.0)
    shapely.prepare(corner_cut)
    S = lambda y: float(ya.ls.project(Point(gt.YONSEI_X if y > -740 else -100.0, y)))
    s_rows = S(Y_ROWS)

    def face(s_mid, side):                              # (the front wall from the street's middle: side +1 east, at -n)
        if s_mid > s_rows:
            return ya.half + gt.YONSEI_WALK                 # (gate_town's walks north of y -640)
        return ya.half + (YRO_WALK_E if side > 0 else YRO_WALK_W)

    def mk(s_mid, wdt, lv, wall, dep, side, draw=True):
        p, t, n = ya.at(s_mid)
        c = p - n * side * (face(s_mid, side) + dep / 2)
        ang = math.atan2(-n[1] * side, -n[0] * side)
        b = [round(float(c[0]), 2), round(float(c[1]), 2), round(dep, 2), round(wdt - 0.15, 2), round(ang, 4), 0.0, int(lv),
             YRO_WALL + int(wall), (3 if rnd.random() < 0.6 else 2) if draw else 3, 0, 2, int(rnd.random() < 0.7) if draw else 0]
        b[5] = round(min(ground(x_, y_) for x_, y_ in list(_box(b).exterior.coords)[:4]) - 0.3, 2)
        return b

    fronts, named = {1: [], -1: []}, []
    for side in (1, -1):
        for yn, ys, lv, wall, dep, shops in yro97.ROWS[side]:
            s_n, s_s = S(yn), S(ys)
            b = mk((s_n + s_s) / 2, s_n - s_s, lv, wall, dep, side)
            fronts[side].append(b)
            named.append((b, shops))
        # the corner's segment (and, east, the one north of it): YRO_FIXED from each segment's south end
        last = len(GAPS[side])
        for k in ((last - 1, last) if side > 0 else (last,)):
            yn = GAPS[side][k - 1][1]
            s_n = S(yn)
            if k < last:
                s_s = S(GAPS[side][k][0])
            elif side > 0:
                s_s = S(-912.6)                               # (홍익문고's south wall; the tower's lot south of it)
            else:                                             # (the corner: where a row's box clears the cross street)
                s_s = 0.0
                while shapely.intersects(corner_cut, _box(mk(s_s + 0.5, 1.0, 1, 0, 12.0, side, False))):
                    s_s += 0.5
            fixed = YRO_FIXED.get((side, k), [])
            seq, s = [], s_s
            for i, (w, lv, wall, dep) in enumerate(fixed):
                if k == last and i == len(fixed) - 1 and s_n - (s + w) < 4.0:
                    w = s_n - s                               # (the last fixed one meets the segment's end)
                seq.append((s + w / 2, w, lv, wall, dep, yro97.FIXED_SHOPS.get((side, k, i), [])))
                s += w
            for s_mid, w, lv, wall, dep, shops in sorted(seq, key=lambda q: -q[0]):         # (north to south)
                b = mk(s_mid, w, lv, wall, dep, side)
                fronts[side].append(b)
                named.append((b, shops))
    rows = fronts[1] + fronts[-1]
    # 독수리다방's lot (yro97.DOK97): the street house of December 1996, its front behind the row's.  After the rows and
    # with no draw of theirs, so the other houses keep their roofs
    yn, ys, lv, wall, dep, back, shops = yro97.DOK97['house']
    s_n, s_s = S(yn), S(ys)
    p_, t_, n_ = ya.at((s_n + s_s) / 2)
    c_ = p_ - n_ * (face((s_n + s_s) / 2, 1) + back + dep / 2)
    dk_b = [round(float(c_[0]), 2), round(float(c_[1]), 2), round(dep, 2), round(s_n - s_s - 0.15, 2),
            round(math.atan2(-n_[1], -n_[0]), 4), 0.0, int(lv), YRO_WALL + int(wall), 2, 0, 2, 1]
    dk_b[5] = round(min(ground(x_, y_) for x_, y_ in list(_box(dk_b).exterior.coords)[:4]) - 0.3, 2)
    named.append((dk_b, shops))
    rp = unary_union([_box(b).buffer(-0.2) for b in rows] + [Polygon(yro97.LOT).buffer(1.0)])
    shapely.prepare(rp)
    n_gone = 0
    for b in blocks:
        if b[6] <= 0:
            continue
        if (b[10] == 2 and b[1] > Y_ROWS) or shapely.intersects(rp, _box(b)):       # (gate_town's rows; what stands here)
            b[6] = -b[6]
            n_gone += 1
    blocks += rows + [dk_b]
    # the shops' boards: over each ground floor shop its name, the frontage shared among them; a shop upstairs has its
    # board on the wall over its own floor's windows
    boards = []
    for b, shops in named:
        cx, cy, L, W, ang, base, lv = b[:7]
        u = np.array([math.cos(ang), math.sin(ang)])          # (L: away from the street)
        t = np.array([-u[1], u[0]])
        nd = t if t[1] > 0 else -t                             # (along the front, northwards: the shops are listed from the north)
        fa = math.atan2(-u[1], -u[0])
        top = base + 0.3 + 3.0 * lv
        down = [n_ for n_, f_ in shops if f_ == 1]
        for i, name in enumerate(down):
            w = min(W / len(down) - 0.5, 5.0)
            h = round(min(1.25, w / 4), 2)
            q = np.array([cx, cy]) - u * (L / 2 + 0.14) + nd * (W / 2 - W * (i + 0.5) / len(down))
            z = min(base + 0.3 + 3.3, top - h / 2 - 0.05)
            boards.append([round(float(q[0]), 2), round(float(q[1]), 2), round(z, 2), round(fa, 4), round(w, 2), h, yro97.CELL[name]])
        for name, f_ in shops:
            if f_ < 2 or f_ > lv:
                continue
            w = min(W - 1.0, 4.4)
            h = round(min(1.1, w / 4), 2)
            q = np.array([cx, cy]) - u * (L / 2 + 0.14)
            z = min(base + 0.3 + 3.0 * f_ + 0.3, top - h / 2 - 0.05)
            boards.append([round(float(q[0]), 2), round(float(q[1]), 2), round(z, 2), round(fa, 4), round(w, 2), h, yro97.CELL[name]])
    return fronts, n_gone, boards


def yro_wall_signs(blocks):
    """The signs that stand out from the shops' walls up the floors over the ground floor (51979 · 52106: every front
    on 연세로 carries one, many two or three): along both rows, the bridge to the junction (gate_town's too, kind 2).
    A board 0.7 - 0.9 m out from the wall, 2.4 - 7 m tall, its two faces along the street; random.Random(4806).
    [x, y of the board's middle, z of its middle, the wall's outward way (rad), out, height, a draw for its cell]
    (which sign: yro97.vsign_cells, after the corners' own walls are left out)"""
    rnd = random.Random(4806)
    out = []
    for b in blocks:
        if b[10] != 2 or b[6] < 2 or not (-950.0 < b[1] < -500.0):
            continue
        cx, cy, L, W, ang, base, lv = b[:7]
        u = np.array([math.cos(ang), math.sin(ang)])          # (L: away from the street)
        t = np.array([-u[1], u[0]])
        n_s = 1 + int(W > 6.0 and rnd.random() < 0.65) + int(W > 10.0 and rnd.random() < 0.35)
        ends = rnd.sample([-1, 1], 2) + [0]
        for k in range(n_s):
            along = ends[k] * (W / 2 - rnd.uniform(0.5, 1.4)) if ends[k] else rnd.uniform(-1.5, 1.5)
            w_ = rnd.uniform(0.7, 0.9)
            z0 = base + 0.3 + 3.0 + rnd.uniform(0.2, 0.8)
            z1 = base + 0.3 + 3.0 * lv - rnd.uniform(0.3, 1.5)
            h = min(z1 - z0, rnd.uniform(2.4, 7.0))
            cell = rnd.randrange(16)
            if h < 1.8:
                continue
            q = np.array([cx, cy]) - u * (L / 2 + 0.12 + w_ / 2) + t * along
            out.append([round(float(q[0]), 2), round(float(q[1]), 2), round(z0 + h / 2, 2), round(math.atan2(-u[1], -u[0]), 4),
                        round(w_, 2), round(h, 2), cell])
    return out


def yro_banner(geo, ground):
    """제5회 신촌문화축제's banner across 연세로 (51979: white cloth, the festival's name in blue, the show in green, the
    date 96.5.4 in red, tied over the road from the walks): [x0, y0, x1, y1 (its two poles behind the kerbs), z of the
    road, the cloth's bottom over it, its height]"""
    ya = geo['arms']['yonsei']
    p, t, n = ya.at(float(ya.ls.project(Point(-99.0, YRO_BANNER_Y))))
    a, b = p + n * (ya.half + 0.6), p - n * (ya.half + 0.6)
    return [round(float(a[0]), 2), round(float(a[1]), 2), round(float(b[0]), 2), round(float(b[1]), 2),
            round(ground(*p), 2), YRO_BANNER_Z[0], YRO_BANNER_Z[1]]
