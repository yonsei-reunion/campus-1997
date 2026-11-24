"""아펜젤러관 뒤 동쪽 찻길의 서쪽 가 (reference/고증/3.5_옛_석조관.md 「아펜젤러관 뒤 땅」).  tools/build_campus.py 가 부른다.

    appen97.WALK_OUT                      # 심기가 끝난 뒤 잔디로 칠함(OSM 의 보도를 걷어 냄)
    appen97.SHOULDER                      # 찻길 서쪽 가: 아스팔트 끝 줄에서 연석 뒤까지의 밝은 띠(포장)
    appen97.pull_paint(lines)             # 그 구간의 노란 가장자리 선을 아스팔트 끝 줄 안으로
    appen97.bollards()                    # ['bollard_stone', x, y, rot] 목록: props 끝에
    appen97.payphone()                    # ['payphone', x, y, rot] 하나: 남쪽 박공벽 앞 마당의 공중전화 부스
    appen97.walk(xy, far)                 # 건물 앞 길의 남쪽 끝(끝벽 너머): 흙길로 칠할 다각형
    appen97.bank_grade(...) · bank_h(...) # 마당 동쪽 둑: 발치 선에서 찻길 가까지의 비탈(격자 위의 덱)
    appen97.south_z(x, y)                 # 잔디 터 남쪽 광장의 높이
    appen97.east_z(x, y)                  # 건물 앞 단의 동쪽(끝벽 너머): 마당 · 잔디 터 · 광장의 높이
    appen97.repath(paths)                 # 그 길을 따라 걷는 선(campus.json paths)을 길 가운데로

Frame: campus metres, x east, y north; along the east road the survey's middle line (tools/roadview/roads/adopt.py
`at('E', s, o)`: s from the 삼거리, o to the left = west, m).  The road's west kerb is at o +3.0 there.

- The 1996 winter scans (2차, 1996-11-28 · 1996-12-23: five frames, both courses) have the road's west edge as a bright
  line at o +2.9 .. +3.1 at the survey's road height, and where the road lies in the sun (s 96 - 115) a row of short
  posts 0.5 m behind it (o +3.45): their shadows, dashes pointing north-north-west, every 1.50 - 1.60 m (27/15, 27/16,
  27/17, 26/15), 0.68 m long at the sun's 28.7 deg (about 0.4 - 0.5 m high).  The paved surface ends 1 m past the
  line (o 3.6 - 4.7 in the east frames); the ground beyond is half as bright: no walk.  Kakao roadview 2010-12
  (1016786075) has the same: a kerb and a row of square concrete bollards on the bank's top, no walk.
- The game had OSM's walk there (2.6 m of block paving 1.3 m off the kerb, o 4.3 - 7.1): WALK_OUT is lawn again over
  the hall's back (s 90 - 132; the walk stays south and north of it, which no photo settles).  The walk the game reads
  (campus.json paths) stays: the crowd may still go along the bank's top.
- Only the posts the scans show are put in (s 97.4 - 114.5): in the shade the row cannot be counted.
"""
import math
import os
import sys

import numpy as np
from shapely.geometry import LineString, Polygon

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'roadview', 'roads'))
import adopt                      # noqa: E402

S0, S1 = 90.0, 132.0              # (along the hall's back wall, s 90 - 125, and a little past its north end)
O0, O1 = 3.25, 7.6                # (from just behind the kerb out past OSM's walk)
WALK_OUT = Polygon([tuple(float(v) for v in adopt.at('E', s, O0)) for s in np.arange(S0, S1 + 0.1, 2.0)] +
                   [tuple(float(v) for v in adopt.at('E', s, O1)) for s in np.arange(S1, S0 - 0.1, -2.0)])
POST_O = 3.45                     # (the posts' line, 0.45 m behind the kerb)
POST_S = [100.5 + 1.55 * k for k in range(-2, 10)]      # (s 97.4 - 114.45: where the sun shows them, 1.55 m apart)


def bollards():
    """the concrete posts behind the kerb: props ['bollard_stone', x, y, rot] (rot: the campus heading of the road)"""
    out = []
    for s in POST_S:
        x, y = (float(v) for v in adopt.at('E', s, POST_O))
        (xa, ya), (xb, yb) = adopt.at('E', s - 0.5, POST_O), adopt.at('E', s + 0.5, POST_O)
        out.append(['bollard_stone', round(x, 2), round(y, 2), round(math.atan2(float(yb - ya), float(xb - xa)), 3)])
    return out


# The asphalt's west edge beside the yard and the hall's back (3.5.5 「찻길(둑 머리)」, #246): the 1996 - 1999 scans
# (four years, both courses, 4 - 14 frames a station, +-0.05 - 0.3 m) have the dark asphalt end at a thin bright line
# that bends in from the kerb's line (o 3.0) at s 76 to o 1.2 - 1.45 at s 86 - 98 and back out by s 114; west of it
# a band brighter than the asphalt (5 - 30 % in 1996, 1.5 - 2 times in 1998) out to o 3.0 - 3.6, the posts in it.  Not
# a shadow's or a crown's edge (the same o in four suns and from both sides).  Whether the line is a kerb or a change
# of surface does not show (a kerb's 18 cm is under a pixel): the band is laid as paving flush with the road.
# EDGE97: (s, o) of the line; SHOULDER: the band from it to the kerb's back
EDGE97 = [(74.0, 3.0), (76.0, 2.58), (78.0, 2.3), (80.0, 2.25), (82.0, 2.09), (84.0, 1.81), (86.0, 1.46), (88.0, 1.43),
          (90.0, 1.35), (92.0, 1.25), (94.0, 1.27), (96.0, 1.23), (98.0, 1.18), (100.0, 1.59), (102.0, 1.82),
          (104.0, 2.09), (106.0, 2.17), (108.0, 2.49), (110.0, 2.52), (112.0, 2.69), (114.0, 2.94), (115.0, 3.0)]


# 공중전화 부스 south of the south gable (reference/고증/3.5.6_아펜젤러관_남쪽_공중전화_부스.md): the 1996 - 2000
# autumn photo (reference/문집/2025_22쪽_…) has a booth to the right of the gable's east corner, the callers' queue
# beside it; the original scans of 1996 - 1999 have a white box the size of a booth on the yard, the same place in all
# four years: its top's middle (86.47, 186.37) in July 1997 (six rays) and (86.57, 186.26) in May 1999 (four), 0.12 m.
# The photo's camera, solved again on the gable's lights (the three-light group's jambs and mullions, the two-light
# group's mullion, the sills of both floors and the sashes' rails: 25 readings, the focal length free), stands at
# (76.0, 184.5) on the east edge of the walk before the hall, the optical axis 62.6 degrees east of north, 47 degrees
# off the gable's normal (the first fit, on the middle group's width and the corner only, had it 7 m further south and
# 25 degrees off): from there the box falls where the photo has the booth, within 0.5 m across the line of sight (the
# camera's own uncertainty), its top at the photo's row with a booth 2.4 m high; the hedge across the photo's foreground
# is the lawn's north hedge (PLOT below) seen from the south.  So the box is the booth.
# PHONE_ALONG, PHONE_OUT: m east of the east corner along the gable's line (GABLE: its west and east corners,
# campus.json), m south of that line.
# Kakao's 2008 winter and 2010 summer skyview and the December 2010 roadview (1016786661 - 663, three bearings) have a
# booth of the same make at (87.0, 186.3) +- 0.5: it never stood by the corner.
# Its open front looks west-north-west, 298 degrees from north (PHONE_TURN from the gable's normal, south, towards the
# west): from the photo's camera (the booth to it: 258 degrees) the front, 1.1 m across, is 94 px of 1000 wide where a
# face-on one would be 123, so 40 degrees off, the near side to its right; the 2010 roadview has it 295 - 300 (face on
# from 661, 38 degrees off from 662); the scans' top lies square with the gable within 10 degrees (285).
GABLE = ((79.65, 194.79), (92.1, 191.41))      # (the east corner 12.9 m from the front: 3.5.4, tools/build_campus.py HALL_DEPTH)
PHONE_ALONG, PHONE_OUT = -4.04, 6.37       # ((86.52, 186.32): the scans' box, the middle of the 1997 and the 1999 solves)
PHONE_TURN = math.radians(103)


def payphone():
    """props ['payphone', x, y, rot] (rot: the campus heading its open front faces)"""
    (xa, ya), (xb, yb) = GABLE
    ln = math.hypot(xb - xa, yb - ya)
    ux, uy = (xb - xa) / ln, (yb - ya) / ln
    nx, ny = uy, -ux                       # (the gable's outward normal: south)
    x, y = xb + ux * PHONE_ALONG + nx * PHONE_OUT, yb + uy * PHONE_ALONG + ny * PHONE_OUT
    c, s = math.cos(PHONE_TURN), math.sin(PHONE_TURN)
    fx, fy = nx * c - ux * s, ny * c - uy * s
    return [['payphone', round(x, 2), round(y, 2), round(math.atan2(fy, fx), 3)]]



# 남쪽 박공벽 앞 마당 (reference/고증/3.5.5_아펜젤러관_남쪽_마당.md): the 1996 - 2000 autumn photo (the booth's, above) has a flat
# yard of bare earth before the gable, a strip of grass along the wall's foot, the booth on it by the bank that rises to
# the east road (shrubs and trees on the bank behind the booth), and a clipped hedge across the near side.  The original
# scans of 1996 winter, July 1997, October 1998 and May 1999 (each pair of frames on its own, 1 m grid, 1.5 m windows):
#  - the yard 44.0 m, flat (1997: 53 points, quartiles 43.87 - 44.08), from the wall 7.3 m south to a hedge along it
#    ((78, 187.4) - (84, 186.0)), east to the edge of the bank's shrubs at x 91 - 92; south of the east corner as far as
#    y 181; west into the walk before the hall at x 77.5 - 78
#  - south of the hedge a lawn ringed by hedges (PLOT), 43.9 m, a 1 m path along its east side 43.8 m, the walk west of
#    it 43.6 - 43.75 m: one surface falling gently south-west (YARD_PLANE, 0.07 m rms over eleven places)
#  - the bank from x 92 up to the road's west edge (x 98 - 99, 47.3 - 48.2 m); no drive comes down it from the road
#    at y 178 - 190
# The game had the 5 m grid's ramp from the gable's foot up to the road, paved (OSM's walk along the road, the garden's
# paving run on), its node (90, 185) sunk 0.9 m.  Late (after the planting read the ground): the nodes on the plane, the
# bank between it and the road as the grid has it, the paint on the game's map only; the hedges and the bank's shrubs at
# the shrubs' very end.
YARD_PLANE = (41.4417, 0.019593, 0.0043987)       # (해발 z = a + b x + c y: 44.0 in the yard, 43.7 at the walk's edge)
# The flat ground's east edge, the bank's foot (2026-11-24, the scans again with 0.75 - 1 m windows on lines across the
# bank from the east road, every pair on its own): the level 44.0 +- 0.3 m ends 9.0 - 9.8 m west of the road's middle
# line (tools/roadview/roads/adopt.py 'E': o) all the way s 74 - 91, in 1997 and 1999 within 0.5 m of each other; the
# bare earth of the yard ends a metre or two short of it at a thicket of shrubs (the 2008 winter and 2010 summer
# skyview: SHRUB_EDGE).  FOOT: that line, o 9.3
FOOT = [(82.64, 172.0), (85.08, 175.0), (86.93, 178.0), (88.86, 181.0), (91.01, 184.0), (93.19, 187.0), (95.64, 190.0),
        (96.3, 191.2)]
SHRUB_EDGE = [(94.3, 190.8), (93.2, 189.2), (92.2, 187.8), (91.3, 186.3), (90.6, 185.0), (90.0, 183.5), (89.4, 182.0),
              (88.86, 181.0)]
YARD = Polygon([(77.6, 187.3), (88.0, 185.5), (88.0, 181.0)] + SHRUB_EDGE[::-1] + [GABLE[1], GABLE[0],
               (77.4, 194.2)])
PLOT = Polygon([(77.6, 187.3), (88.0, 185.5), (85.8, 180.0), (82.6, 172.0), (73.5, 172.0), (74.5, 176.0), (76.5, 184.0)])
PLOT_PATH = LineString([(89.0, 185.3), (86.8, 179.6), (83.6, 171.8)])     # (the 1 m path along its east side)
CORNER = Polygon([(94.3, 190.8), (96.3, 191.2), (93.2, 192.6), GABLE[1]])     # (round the south-east corner towards the back yard)
# (all that lies level: the yard, the lawn, the path east of it and the grass out to the bank's foot)
LEVEL = Polygon([(77.4, 194.2), GABLE[0], GABLE[1]] + FOOT[::-1] + [(73.5, 172.0), (74.5, 176.0),
                (76.5, 184.0), (77.6, 187.3)])
EASE_SOUTH, EASE_EAST = 5.0, 1.5     # (m over which the nodes outside come back to their own: little towards the bank)
WALL_STRIP = 2.8                     # (the grass along the gable's foot: the photo's kerb line lies 2.7 - 3.3 m off the wall from the camera above)
# (no hedge along the lawn's west side, the walk's edge: there the scans' edge stands 0.1 - 0.25 m over the walk, a kerb
# or the turf's own step, and the ground 0.6 - 2.5 m inside it is the lawn's, 43.6 - 44.1 m, in 1997 and 1999; a hedge
# would read 0.9 m higher.  The north hedge is the one across the foreground of the 1996 - 2000 photo)
# (the north one ends at the booth, which stands in the hedge's north-east corner: the 2008 - 2010 skyview and roadview)
HEDGES = [[(77.6, 187.3), (85.75, 185.89)], [(88.0, 185.5), (85.8, 180.0), (82.6, 172.0)]]
# The bank from its foot up to the east road's west kerb (o 3.0; the kerb's back o 3.3): grass, shrubs and trees, no
# wall, steps or drive down it at y 176 - 192 (the scans' crowns in every year; the 2008 and 2010 roadview: a grass
# slope under cherries and maples, the thicket along its foot behind the booth).  BANK_S: along the road, where the
# slope is laid (eased in over 3 m at the south end, out over 4 m at the north one, where the ground behind the hall
# stays as it was); BANK: what is lawn again (OSM's walk along the kerb goes: none in 2008 - 2010, crowns before)
BANK_S = (72.0, 96.5)
FOOT_O, TOP_O = 9.3, 3.3
BANK = Polygon([tuple(float(v) for v in adopt.at('E', s_, FOOT_O + 0.2)) for s_ in np.arange(70.0, 97.6, 1.5)] +
               [tuple(float(v) for v in adopt.at('E', s_, TOP_O)) for s_ in np.arange(97.0, 69.9, -1.5)])
SHOULDER = Polygon([tuple(float(v) for v in adopt.at('E', s_, o_)) for s_, o_ in EDGE97] +
                   [tuple(float(v) for v in adopt.at('E', s_, TOP_O)) for s_, _ in EDGE97[::-1]])
# (the line itself: no kerb along it, the band flush with the road -- the lanes' wheels run 2.2 m off the middle)
EDGE_LINE = LineString([tuple(float(v) for v in adopt.at('E', s_, o_)) for s_, o_ in EDGE97 if o_ < 2.7])


def pull_paint(lines):
    """the yellow edge line (2008 roadview, 0.35 m inside the kerb) moved in onto the asphalt where the band is:
    0.35 m inside the line; returns the points moved"""
    es, eo = np.array([e[0] for e in EDGE97]), np.array([e[1] for e in EDGE97])
    n = 0
    for l_ in lines:
        if l_['kind'] not in ('yellow', 'yellow_dash'):
            continue
        for q_ in l_['pts']:
            s_, o_ = _so(q_[0], q_[1])
            if not (es[0] <= s_ <= es[-1]) or o_ < 0.0:
                continue
            ot_ = float(np.interp(s_, es, eo)) - 0.35
            if o_ > ot_:
                q_[0], q_[1] = (round(float(v), 2) for v in adopt.at('E', s_, ot_))
                n += 1
    return n


def yard_z(x, y):
    a, b, c = YARD_PLANE
    return a + b * x + c * y


def yard_shrubs():
    """the hedges round the lawn south of the yard, the thicket along the bank's foot behind the booth, the round
    shrubs off the lawn's south end: [kind, x, y, scale, rot]"""
    out = []
    for line in HEDGES:
        for (xa, ya), (xb, yb) in zip(line, line[1:]):
            n = max(1, int(round(math.hypot(xb - xa, yb - ya) / 1.9)))
            a = round(math.atan2(yb - ya, xb - xa), 3)
            out += [['hedge_blob', round(xa + (xb - xa) * (k + 0.5) / n, 2), round(ya + (yb - ya) * (k + 0.5) / n, 2), 1.0, a]
                    for k in range(n)]
    # (the thicket: the 1996 - 2000 photo's shrubs behind the queue, to twice a man's height with the bank under them;
    # the 2010 roadview: bare twigs 1.5 m high from the gable's corner to behind the booth; the skyview's edge of the
    # bare earth SHRUB_EDGE, the scans' foot FOOT.  Two rows, one before the foot and one on the slope's first metre)
    # (the way round the hall's south-east corner to the yard behind it stays open: 2 m clear of the corner)
    out += [['bush', x, y, sc, r] for x, y, sc, r in (
        (93.9, 188.7, 1.35, 2.1), (93.0, 187.2, 1.3, 4.0), (92.0, 185.7, 1.4, 5.2),
        (91.2, 184.3, 1.25, 1.3), (96.7, 188.9, 1.4, 3.3), (95.1, 187.8, 1.3, 0.2), (94.1, 186.1, 1.45, 2.7),
        (93.0, 184.5, 1.3, 4.6), (90.4, 182.8, 1.1, 5.9))]
    # (the lawn's south end, y 172: a row of three or four round clipped shrubs 1.5 - 2 m across in the 1996 winter
    # frames 27/15 - 27/17, x 73.5 - 80)
    out += [['topiary_round', x, 171.3, sc, r] for x, sc, r in ((74.4, 1.0, 0.4), (76.3, 1.1, 2.2), (78.2, 1.0, 3.9), (80.0, 1.05, 5.1))]
    return out


# (No benches: the July 1997 scans have two or three white bars along the north side of the lawn's hedge, (79.5 - 85,
# 186.5 - 187.4), and the 2008 - 2010 skyview and roadview two benches there; but nothing stands over the hedge in the
# 1996 - 2000 photo where a bench's back would, so they were low and backless, and the game's bench is neither.)


# 둑의 비탈 (3.5.5 「둑」): the 5 m grid had the bank's foot 0.3 - 2.6 m west of the scans' line or 1.5 m east of it
# from one row of nodes to the next, the ground at the foot 0.5 - 2 m high.  The nodes on the slope go down to the
# yard's level and the slope is a deck over their cells (tools/build_campus.py dwb_deck: a 1.25 m lattice), level out
# to the foot, straight from there up to the ground at the kerb's back as it was; the road's part of those cells as it
# was.  The slope's own shape is not known (crowns in every year): a straight one, 26 - 34 degrees.
def _so(x, y):
    s_, o_ = adopt.proj('E', float(x), float(y))
    return float(s_), float(o_)


def _bank_w(s_):
    return float(np.clip(min((s_ - BANK_S[0]) / 3.0, (BANK_S[1] - s_) / 4.0), 0.0, 1.0))


def bank_h(x, y, h0, plane):
    """the bank's surface at (x, y): h0(x, y) the ground before (the road, the ground behind the hall), plane(x, y)
    the yard's plane, both on the builder's work plane"""
    s_, o_ = _so(x, y)
    w = _bank_w(s_)
    g = float(h0(x, y))
    if w <= 0.0 or o_ <= TOP_O:
        return g
    if o_ >= FOOT_O:
        r = float(plane(x, y))
    else:
        (xf, yf), (xt, yt) = adopt.at('E', s_, FOOT_O), adopt.at('E', s_, TOP_O)
        zf, zt = float(plane(float(xf), float(yf))), float(h0(float(xt), float(yt)))
        r = zf + (zt - zf) * (FOOT_O - o_) / (FOOT_O - TOP_O)
    return g + (r - g) * w


def bank_grade(Hn, X, Y, plane):
    """the nodes on the slope (over a metre from the kerb's back) down to just under the yard's plane; returns the
    (j, i) of the nodes and the cells round them (the deck's)"""
    m = (np.abs(X - 93.0) < 16.0) & (np.abs(Y - 182.0) < 16.0)
    nodes = []
    for j, i in zip(*np.nonzero(m)):
        s_, o_ = _so(X[j, i], Y[j, i])
        if _bank_w(s_) > 0.0 and TOP_O + 1.0 < o_ < FOOT_O:
            nodes.append((int(j), int(i)))
            Hn[j, i] = min(Hn[j, i], plane(X[j, i], Y[j, i]) - 0.05)
    cells = {(j + a, i + b) for j, i in nodes for a in (-1, 0) for b in (-1, 0)}
    return nodes, cells


# 잔디 터 남쪽 (3.5.5 「잔디 터 남쪽」): south of the lawn (y 172) the walk opens into a square of bare earth under a
# great tree (x 62 - 79, y 153 - 172: the 1996 winter frames and the 2008 winter skyview; summer crowns hide it), the
# trunk at (71.5, 163) +- 1 m.  Its heights only in the 1996 winter pairs (3 - 13 pairs a point, correlation 0.8 - 0.9):
# 43.0 - 43.4 m over x 70 - 78, y 158 - 170, which on the open walk read 0.1 - 0.25 m under 1997 and 1999; the game's
# ground rose east from 43.0 to 44.3 m there (0.4 - 1.0 m over them).  SOUTH_PLANE: 43.3 m at (74, 164), up to 43.6 m
# at the lawn's south-east corner (1999: 43.55 - 43.8 m at (78 - 80, 170 - 172)); the bank up to the road's kerb east of
# it as the grid has it.  SQUARE: what is bare earth (the walk west of it is walk())
SOUTH = Polygon([(73.0, 171.8), (81.0, 171.8), (81.0, 166.5), (79.0, 161.0), (77.0, 157.0), (72.0, 157.0)])
SOUTH_EASE = 3.0
SQUARE = Polygon([(73.4, 172.0), (79.6, 172.0), (79.6, 166.0), (78.0, 160.0), (76.5, 157.2), (67.3, 157.2), (69.4, 165.0),
                  (71.2, 172.0)])
TREE_MOVE = ((72.09, 159.63), (71.5, 163.0))     # (the zelkova the planting put there: onto the scans' trunk, in its place in the list)


def south_z(x, y):
    return 43.3 + 0.03 * (x - 74.0) + 0.02 * (y - 164.0)


# 건물 앞 길의 남쪽 끝 (reference/고증/3.5.5_아펜젤러관_남쪽_마당.md 「건물 앞 길의 남쪽 끝」): the walk on the terrace before
# the hall (tools/build_campus.py TERR['ap']: s south along the front from the door, d out of the front wall; the end
# wall at s 17.8) runs on south past the end wall.  The 1997 scans' four frames, each edge read on the walk's own level
# and fitted over the frames (0.01 - 0.04 m rms), 1996, 1998 and 1999 the same within 0.2 m:
#  - its west edge the top of the bank, d 5.1 - 5.5 (the game's `far` within 0.15 m), the bank's foot and the walk's
#    heights the game's too (`bank` within 0.02 m, `zr` within 0.05 m at s 21 - 39)
#  - its east edge the line of the front wall, d 0.0 +- 0.1, from the lawn's north-west corner (s 25.4) to its
#    south-west corner (s 42): the lawn's own west side, nothing between them; from the end wall to s 25.4 the walk is
#    open to the yard before the gable, level with it.  5.2 +- 0.15 m wide
#  - further south (s 43 - 56) evergreen crowns cover it in every year
#  - as bright as the garden's walks (213 - 218 of 255 where they have 206 and the east road's asphalt 115 - 156)
# The game had the walk 3 m wide there (d 2.25 - 5.2, the width it has before the hall between the planted band at the
# wall's foot and the bank), asphalt, and lawn between it and the lawn's hedge.  Now bare earth like the yard it opens
# onto and the garden's walks, from the end wall south, out to the lawn's edge as far as its south-west corner and as
# wide as it was beyond.  Late, on the game's map only (the ground there is the terrace's deck and the grid at its
# level already).
WALK_S = (17.8, 42.0, 57.5)           # (s: the end wall, the lawn's south-west corner, the south end of the terrace)
WALK_D0 = 2.25                        # (the east edge the game had: TERR['ap']['road'])


def walk(xy, far):
    """the walk south of the end wall, a polygon: xy(s, d) the terrace's frame, far(s) the d of the bank's top"""
    s0, s1, s2 = WALK_S
    ss = [float(v) for v in np.arange(s0, s2 + 0.01, 0.5)]
    west = [xy(s_, far(s_) + 0.05) for s_ in ss]
    east = [xy(s_, -0.4 if s_ <= s1 else WALK_D0) for s_ in ss]
    return Polygon(west + east[::-1]).difference(PLOT)


def repath(paths, xy):
    """the walkers' line along the walk (OSM's footway, on the bank's top at d 5.3) goes down the walk's middle south
    of the end wall.  Returns how many entries were changed"""
    old = [(72.9, 190.2), (67.3, 169.7)]
    n = 0
    for p in paths:
        pts = [tuple(q[:2]) for q in p['pts']]
        if p.get('kind') != 'footway' or any(q not in pts for q in old) or len(pts) != 3:
            continue
        i = pts.index(old[0])
        mid = [[round(v, 1) for v in xy(s_, d_)] for s_, d_ in ((17.0, 4.0), (26.0, 2.7), (41.0, 2.7))]
        p['pts'] = [list(q) for q in p['pts'][:i]] + mid + [list(q) for q in p['pts'][i + 1:]]
        n += 1
    return n


def east_z(x, y):
    """the ground east of the walk south of the end wall (해발): the yard's and the lawn's plane north of the lawn's
    south end (y 172), the square's south of it, over 4 m between"""
    k = float(np.clip((y - 170.0) / 4.0, 0.0, 1.0))
    return south_z(x, y) * (1.0 - k) + yard_z(x, y) * k
