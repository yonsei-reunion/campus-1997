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
- Raised: the level ground's nodes by what they lack (one value), the bank round them (ring, nodes no other rule
  holds) one smooth surface out to the ground that stays.  The hall's parts go up by the same value
  (build_campus.py).  Nothing here draws from build_campus.py's `rng`.
"""
import numpy as np
import datum

FLOOR = 45.9                      # 해발: the hall's floor and the level ground round it, the car park before the north walls


def raise_pad(Hn, X, Y, FIXED, pad, ring, floor_work, cluster_xy, fill):
    """pad: the level ground's nodes (on floor_work, the working datum's floor build_campus.py laid them on); ring: the
    nodes the bank may take.  FLOOR is read at cluster_xy (the middle of the hall's joined parts: the floor goes out at
    its tilt there).  Returns the rise (m), the nodes set (to be FIXED) and a summary."""
    dz = round(datum.up(cluster_xy[0], cluster_xy[1], FLOOR) - floor_work, 2)
    h0 = Hn.copy()
    Hn[pad] = floor_work + dz
    free = ring & ~pad & ~FIXED
    if free.any():
        fill(free)
    d = Hn - h0
    info = dict(rise=dz, pad=int(pad.sum()), bank=int(free.sum()),
                bank_rise=(round(float(d[free].min()), 2), round(float(d[free].max()), 2)) if free.any() else (0.0, 0.0))
    return dz, pad | free, info
