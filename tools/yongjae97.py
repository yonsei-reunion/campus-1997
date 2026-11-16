"""용재관 바닥과 둘레 땅의 1997년 높이 (#189; reference/고증/3.13_용재관.md 「바닥과 둘레 땅의 높이」).  tools/build_campus.py 가
무작위 심기가 끝난 뒤(늦은 블록) 부른다.

    dz, took, info = yongjae97.raise_pad(Hn, X, Y, FIXED, pad, ring, floor_work, cluster_xy, fill)

Frame: campus metres, x east, y north.  Every absolute height written here is above sea level (해발), taken up to the
working datum the ground is laid on (해발 + tilt: tools/datum.py) where it is read.

- The hall stood on its level ground (YJ_PAD in build_campus.py: round the walls and the car park before the north
  walls) at 해발 FLOOR, 2.2 m over the game's (which had it 6.2 m over 백양로's section abreast, by eye): the 1997-07-28
  scans read the bare asphalt of the car park 45.9 - 46.4 m (eight points, five to eight frame pairs), the ground before
  the tower's fin face 45.7 - 46.1 m (x 69 - 73) and south of the south block 45.8 - 46.2 m (y 89); the 2006 survey,
  made while the hall stood, has a spot of 45.75 m in the car park (95.1, 144.2).  Less the photos' usual 0.2 m over the
  survey: 45.9 m.  The roofs read in the same frames stand that much over it as the storeys have it (the wing's eaves
  56.6 m: three storeys of 3.6 m; the tower's slab 68.1 m).
- The 1990s ground photo (reference/용재관.jpg) agrees once its camera is solved with the statue's size free
  (reference/고증/3.13 「지상 사진의 카메라」): the camera stands on the bank north-west of the garden, 50 m from the
  statue, its lens 1.7 m over the ground there.  (The game's statue, a guess at 2.45 m, had put it 76 m off and,
  with the hall raised, under the ground: that was why the floor had stayed low.)
- Raised: the level ground's nodes by what they lack (one value), the walk down the 진달래동산 from the canopy (the
  ground along its flight on one grade from the level ground's edge to its foot, so that the flight lies in the bank
  and not on a ridge over it), the bank round them (ring, nodes no other rule holds) one smooth surface out to the
  ground that stays.  The hall's parts go up by the same value (build_campus.py).  Nothing here draws from
  build_campus.py's `rng`.
"""
import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
import datum

FLOOR = 45.9                      # 해발: the hall's floor and the level ground round it, the car park before the north walls
WALK_HALF = 3.0                   # the ground this far either side of the walk's flight follows its grade
# the car park's north-west edge by the drive to 노천극장: the white car of July 1997 stood across YJ_LOT's edge, askew
# (27/16 · 27/17: its roof at (92.4, 154.3), 57 deg), on pavement.  The one grid node beside it, which the bank's fill
# had left 0.7 m under the car park, on the car park's level (no cell the east fork's wheels use has it for a corner:
# the fork's middle runs 9.4 m off), and the asphalt 1.7 m out from the edge
LOT_NW_NODE = (90.0, 155.0)
LOT_NW_PAVE = [(89.5, 152.0), (95.0, 157.5), (93.8, 158.7), (88.3, 153.2)]
# South of the hall the level ground ran on 8 - 18 m past the walls (reference/고증/3.13 「평평한 땅의 남쪽 가」): the 1997
# scans 45.8 - 45.9 m at x 94 to y 78 and 46.2 - 47.1 m at x 96 - 100 to y 72 (rising east), 45.4 - 46.4 m south-west
# of the tower (x 68 - 74, y 94 - 98); the leafless 1996 frames 45.5 - 45.9 m at x 64 - 96, y 84 - 90; the 2006
# survey's 45 m contour runs round it a metre or two out ((66.6, 89.6), (71.1, 86.5), (81.8, 83.4), (92.0, 78.2),
# (96.9, 72.1), (100.4, 68.0)), and below it the 대강당's yard (40 m) as the scans have it.  The game had the bank from
# 3 m past the walls, 1.5 - 3.9 m under that.  SOUTH: the nodes on it (1.5 m inside the contour), at FLOOR and
# SOUTH_RISE a metre east of x 95; the ring round them (SOUTH_RING) eased again to the yard and the ground east
# (audnorth97 keeps them)
SOUTH = [(65.5, 98.0), (101.5, 88.6), (101.5, 70.0), (98.5, 72.0), (94.5, 76.5), (93.0, 79.5), (82.4, 84.8), (71.6, 88.0),
         (69.9, 88.9), (68.0, 90.6), (67.5, 92.5), (66.5, 95.0)]
SOUTH_RISE = 0.15
SOUTH_RING = 8.0


def raise_pad(Hn, X, Y, FIXED, pad, ring, floor_work, cluster_xy, fill, pad_poly=None, walk=None, bank=None):
    """pad: the level ground's nodes (on floor_work, the working datum's floor build_campus.py laid them on); ring: the
    nodes the bank may take.  FLOOR is read at cluster_xy (the middle of the hall's joined parts: the floor goes out at
    its tilt there).  walk: the walk down the bank (points, the first on the level ground), pad_poly the level ground:
    the ground along the walk outside it on one grade from the floor to the walk's foot.  bank: nodes of the bank the
    raise may take though an earlier block set them (the 진달래동산 between the level ground and the east fork's own
    cells: the east road's easing had laid it from the old floor).  Returns the rise (m), the nodes set (to be FIXED)
    and a summary."""
    bank = np.zeros(X.shape, bool) if bank is None else bank
    open_ = ~FIXED | bank
    dz = round(datum.up(cluster_xy[0], cluster_xy[1], FLOOR) - floor_work, 2)
    h0 = Hn.copy()
    Hn[pad] = floor_work + dz
    along = np.zeros(X.shape, bool)
    if walk is not None:
        ls = LineString(walk).difference(pad_poly)
        ls = max(getattr(ls, 'geoms', [ls]), key=lambda g: g.length)
        a, b = ls.coords[0], ls.coords[-1]
        if Point(walk[0]).distance(Point(b)) < Point(walk[0]).distance(Point(a)):
            a, b = b, a
        ls = LineString([a, b])
        jb, ib = np.unravel_index(np.argmin((X - b[0]) ** 2 + (Y - b[1]) ** 2), X.shape)
        z0, z1 = floor_work + dz, float(Hn[jb, ib])
        pts = shapely.points(X, Y)
        along = (shapely.distance(ls, pts) <= WALK_HALF) & ~pad & open_
        s = shapely.line_locate_point(ls, pts) / ls.length
        Hn[along] = (z0 + (z1 - z0) * np.clip(s, 0.0, 1.0))[along]
    free = (ring | bank) & ~pad & ~along & open_
    if free.any():
        fill(free)
    d = Hn - h0
    info = dict(rise=dz, pad=int(pad.sum()), walk=int(along.sum()), bank=int(free.sum()),
                bank_rise=(round(float(d[free].min()), 2), round(float(d[free].max()), 2)) if free.any() else (0.0, 0.0))
    return dz, pad | along | free, info


def south_edge(Hn, X, Y, FIXED, pad, keep, fill, floor_work_at, bank):
    """SOUTH's nodes (but those of the level ground already, pad, and keep: the halls' feet) at FLOOR rising SOUTH_RISE a
    metre east of x 95, on the working datum (floor_work_at(x, y): FLOOR there); the ring round them that no other
    rule holds (not FIXED, or the bank raise_pad laid) eased.  Returns (the nodes set, the ring eased, a summary)"""
    P = Polygon(SOUTH)
    zone = shapely.contains_xy(P, X, Y) & ~pad & ~keep
    h0 = Hn.copy()
    Hn[zone] = floor_work_at(X[zone], Y[zone]) + SOUTH_RISE * np.maximum(X[zone] - 95.0, 0.0)
    ring = shapely.contains_xy(P.buffer(SOUTH_RING), X, Y) & ~zone & ~pad & ~keep & (~FIXED | bank)
    if ring.any():
        fill(ring)
    d = Hn - h0
    return zone, ring, dict(nodes=int(zone.sum()), rise=(round(float(d[zone].min()), 2), round(float(d[zone].max()), 2)) if zone.any() else (0, 0),
                            ring=int(ring.sum()))
