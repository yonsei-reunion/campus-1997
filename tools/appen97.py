"""아펜젤러관 뒤 동쪽 찻길의 서쪽 가 (reference/고증/3.5_옛_석조관.md 「아펜젤러관 뒤 땅」).  tools/build_campus.py 가 부른다.

    appen97.WALK_OUT                      # 심기가 끝난 뒤 잔디로 칠함(OSM 의 보도를 걷어 냄)
    appen97.bollards()                    # ['bollard_stone', x, y, rot] 목록: props 끝에

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
from shapely.geometry import Polygon

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
