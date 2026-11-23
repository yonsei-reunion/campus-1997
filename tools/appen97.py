"""아펜젤러관 뒤 동쪽 찻길의 서쪽 가 (reference/고증/3.5_옛_석조관.md 「아펜젤러관 뒤 땅」).  tools/build_campus.py 가 부른다.

    appen97.WALK_OUT                      # 심기가 끝난 뒤 잔디로 칠함(OSM 의 보도를 걷어 냄)
    appen97.bollards()                    # ['bollard_stone', x, y, rot] 목록: props 끝에
    appen97.payphone()                    # ['payphone', x, y, rot] 하나: 남쪽 박공벽 앞 마당의 공중전화 부스

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


# 공중전화 부스 south of the south gable (reference/고증/3.5_옛_석조관.md 「아펜젤러관 남쪽 공중전화 부스」): the 1996 - 2000
# autumn photo (reference/문집/2025_22쪽_…) has a booth to the right of the gable's east corner, the callers' queue
# before it; the 2010 roadview has one by that corner too.  With the photo's camera found against the game (20 m off
# the gable's middle, 25 degrees west of its normal: the middle windows' width and the east corner fall within 3 px of
# 1300), the booth's height in the picture puts it 16 - 17 m from the camera on the bearing 60.5 degrees: on the flat
# yard at the gable's foot, just before the bank that rises to the east road (the shrubs and trees behind it in the
# photo), not on top of that bank past the corner as first placed.  PHONE_ALONG, PHONE_OUT: m east of the east corner
# along the gable's line (GABLE: its west and east corners, campus.json), m south of that line.
# Its open front looks west-south-west along the yard, where the photo has the queue: from the camera the booth's front
# is nearly face on and its far side shows to the right of it, so the front is turned PHONE_TURN from the gable's normal
# (south) towards the west
GABLE = ((79.65, 194.79), (93.63, 190.99))
PHONE_ALONG, PHONE_OUT = -2.6, 5.9         # (a metre nearer the gable than the photo's (90.3, 185.3): the flattest ground of the game's yard there)
PHONE_TURN = math.radians(65)


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
YARD = Polygon([(77.6, 187.3), (88.0, 185.5), (88.0, 181.0), (91.0, 181.0), (92.0, 186.0), (92.0, 190.6), (93.63, 190.99),
                (79.65, 194.79), (77.4, 194.2)])
PLOT = Polygon([(77.6, 187.3), (88.0, 185.5), (85.8, 180.0), (82.6, 172.0), (73.5, 172.0), (74.5, 176.0), (76.5, 184.0)])
PLOT_PATH = LineString([(89.0, 185.3), (86.8, 179.6), (83.6, 171.8)])     # (the 1 m path along its east side)
CORNER = Polygon([(92.0, 186.0), (94.5, 187.6), (96.3, 191.2), (93.63, 190.99), (92.0, 190.6)])   # (round the south-east corner
#  towards the back yard, as the May 1999 frames have the yard there: the grid's node (95, 190) stood 3.6 m over it)
LEVEL = YARD.union(PLOT).union(PLOT_PATH.buffer(0.6)).union(CORNER).union(
    Polygon([(85.8, 180.0), (88.0, 178.0), (91.0, 181.0), (88.0, 181.0)]))
EASE_SOUTH, EASE_EAST = 5.0, 1.5     # (m over which the nodes outside come back to their own: little towards the bank)
WALL_STRIP = 1.2                     # (the grass along the gable's foot)
HEDGES = [[(76.5, 184.0), (77.6, 187.3), (88.0, 185.5), (85.8, 180.0), (82.6, 172.0)],
          [(76.5, 184.0), (74.5, 176.0), (73.5, 172.0)]]
BANK = Polygon([(91.0, 181.0), (88.0, 178.0), (93.5, 176.6), (99.6, 184.9), (97.6, 191.4), (96.3, 191.2), (94.5, 187.6),
                (92.0, 186.0)])


def yard_z(x, y):
    a, b, c = YARD_PLANE
    return a + b * x + c * y


def yard_shrubs():
    """the hedges round the lawn south of the yard, the shrubs on the bank behind the booth: [kind, x, y, scale, rot]"""
    out = []
    for line in HEDGES:
        for (xa, ya), (xb, yb) in zip(line, line[1:]):
            n = max(1, int(round(math.hypot(xb - xa, yb - ya) / 1.9)))
            a = round(math.atan2(yb - ya, xb - xa), 3)
            out += [['hedge_blob', round(xa + (xb - xa) * (k + 0.5) / n, 2), round(ya + (yb - ya) * (k + 0.5) / n, 2), 1.0, a]
                    for k in range(n)]
    out += [['bush', 93.4, 184.0, 1.1, 0.6], ['bush', 93.6, 187.2, 1.25, 2.1], ['bush', 92.6, 180.6, 1.0, 4.0]]
    return out
