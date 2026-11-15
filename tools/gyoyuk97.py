"""교육관 북쪽 마당, 그 동쪽 마당, 연희관 서쪽 옆길의 1997년 7월 땅 (#189; reference/고증/3.5.1 「1997년 7월 원본 스캔으로
다시 잰 띠의 서쪽」, 3.18 「교육관」, 2.8 「삼거리에서 연희관까지」).  tools/build_campus.py 가 부른다.

    took, info = gyoyuk97.grade(Hn, X, Y, FIXED, halls, fill, sample)   # 심기가 끝난 뒤, widang97 · jonghap97 다음

Frames: campus metres, x east, y north.  Every absolute height is above sea level (해발), taken up to the working
datum (해발 + tilt: tools/datum.py) at its own place where it is read.

On the 1997-07-28 scans (six frames, heights frame pair by frame pair on a 2 m grid, the median of the pairs over 0.7,
cross-course pairs first) the ground from 교육관's north end east to 연희관's west wing is one low yard, level with
the works yard west of it (widang97, 55.63 m) and the car park behind 연희관 (HILL_Q, 55.2 - 56.4 m), where the game
had kept a ridge between the two (56 - 59 m) and had 교육관's floor (53.84 m) for the yard north of the hall:

- YARD (x 21 - 49, y 351 - 389): 54.8 - 55.0 m up to y 367 (the median of each 2 m row, eight to eleven points),
  55.4 at y 377, 55.7 at y 381, then the foot of the bank under 빌링슬리관's lawn (56.3 m at y 385; the lawn 60.0 m
  from y 388); 0.012 m a metre lower to the east.  10 - 13 m out of 교육관's north gable 54.9 - 55.0 m (four to nine
  pairs a point): the foot of the hall's north flight, whose landing stays a storey over the floor (3.18).  The strip
  along the gable, under the flight's landing, the hall's shadow and the site office of 제2인문관's works, is not
  read: it stays at the hall's feet (KEEP) and the yard comes up to it over the next grid cell
- DRIVE (연희관 서쪽 옆길: campus.json path 36, OSM's service road): 55.0 - 55.4 m from the south end of 연희관's west
  wing to abreast of its north end (the 2024 survey's spot (58.6, 383.4) 55.15 m), 55.5 - 55.9 m on to y 401, then up
  about 15 % past the 상뜰 (59.6 - 60.0 m at y 424 - 430).  The game climbed from y 365 at 10 %, 2 - 4 m over it.
  North of y 389 it is held by 3.6's ground: the footway along the 상뜰's south edge leaves it at (66.6, 414.3) on the
  level laid there (61.1 m; the scans 57.5 - 57.9 m) and the drive on beside the 상뜰 meets 대우관's (3.6 「상뜰 옆 두
  길의 높이」).  So the drive keeps the scans' level to abreast of the wing's north end (DRIVE_FLAT) and from there
  goes up one grade to that node, which stays (3.5.1 「남은 한계」 「연희관 서쪽 옆길과 상뜰 서쪽 길의 높이」)

Nothing here draws from build_campus.py's `rng`; the trees, the paths and the cars stay where they are.
"""
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

import datum

# the drive's middle, campus.json path 36 (OSM), from 연희관 앞길's west end to where the 상뜰's footway leaves it
DRIVE = LineString([(51.7, 354.5), (50.7, 363.9), (54.7, 378.7), (61.7, 398.7), (66.6, 414.3)])
DRIVE_HALF = 5.0                          # nodes this near its middle take its profile (6 m of asphalt and the verges)
S0 = 6.0                                  # (the drive before this, by 연희관 앞길: 54.8 - 55.0 m, as the scans)
DRIVE_FLAT = [(6.0, 54.95), (24.8, 55.2), (34.0, 55.4)]     # (s along DRIVE, 해발)
FOOTWAY = LineString([(66.6, 414.3), (101.2, 405.4)])        # (3.6's strip, which stays: build_campus.py fix_strip, 1.8 m)
YARD = Polygon([(20.5, 353.5), (27.0, 351.2), (44.6, 346.7), (51.0, 348.5), (51.0, 362.0), (46.5, 364.0), (46.5, 388.0),
                (40.0, 386.5), (34.0, 385.5), (34.0, 362.5), (21.0, 362.5)])
YARD_Z = ((367.0, 377.0, 381.0, 385.0), (54.93, 55.42, 55.65, 56.3))   # (y, 해발 at x 42)
YARD_DX = -0.012                          # (m a metre east)
# between the yard's bright pad (its east edge a pale line at x 46 - 47 on the scans) and the drive: the drive's level
SIDE = Polygon([(46.5, 364.0), (51.0, 362.0), (56.0, 392.5), (50.5, 392.5), (46.5, 388.0)])
# east of where the road behind 연희관 leaves the drive: the old drive's level cross-section (build_campus.py TR_LEVEL),
# eased again between the drive and the car park behind 연희관 (the scans 56.1 - 56.3 m there)
LOOSE = Polygon([(62.5, 391.5), (72.5, 390.5), (74.5, 403.0), (71.5, 408.5), (66.5, 408.5)])
RING = 8.0                                # eased out (harmonic) this far round the two


def yard_z(x, y):
    return np.interp(y, *YARD_Z) + YARD_DX * (x - 42.0)


def drive_z(s, z_join, s_join):
    """해발 along DRIVE: the scans' level to DRIVE_FLAT's end, then one grade up to the footway's node"""
    s_, z_ = zip(*DRIVE_FLAT)
    return np.where(s <= s_[-1], np.interp(s, s_, z_), z_[-1] + (z_join - z_[-1]) * (s - s_[-1]) / (s_join - s_[-1]))


def grade(Hn, X, Y, FIXED, halls, fill, sample):
    """YARD and DRIVE on the scans' levels (over the nodes laid before them there: the old drive levelled across,
    widang97's ring, 교육관's north forecourt), eased round them; the halls' feet, 3.6's footway and the nodes laid
    before outside the two stay.  halls: [(outline, the distance round it whose nodes stay)] (교육관's north strip,
    빌링슬리관's east end); sample(x, y): the grid's height at a point (working datum).  Returns the nodes set (to be
    FIXED) and a summary"""
    H0 = Hn.copy()
    P = shapely.points(X, Y)
    stay = shapely.contains_xy(unary_union([h.buffer(k) for h, k in halls]), X, Y) | \
        (shapely.distance(FOOTWAY, P) <= 2.2)
    s_join = DRIVE.length
    z_join = sample(*DRIVE.coords[-1]) - datum.tilt(*DRIVE.coords[-1])      # (the footway's node, 해발)
    s = shapely.line_locate_point(DRIVE, P)
    dr = ((shapely.distance(DRIVE, P) <= DRIVE_HALF) | shapely.contains_xy(SIDE, X, Y)) & (s >= S0) & (s < s_join - 0.5) & ~stay
    yd = shapely.contains_xy(YARD, X, Y) & ~dr & ~stay
    Hn[yd] = yard_z(X[yd], Y[yd]) + datum.tilt(X[yd], Y[yd])
    Hn[dr] = drive_z(s[dr], z_join, s_join) + datum.tilt(X[dr], Y[dr])
    took = yd | dr
    near = shapely.contains_xy(unary_union([h.buffer(1.0) for h, _ in halls]), X, Y)
    free = ((shapely.contains_xy(unary_union([YARD, DRIVE.buffer(DRIVE_HALF)]).buffer(RING), X, Y) & ~FIXED)
            | shapely.contains_xy(LOOSE, X, Y)) & ~took & ~near & ~stay
    if free.any():
        fill(free)
    d = Hn - H0
    return took | free, dict(yard=int(yd.sum()), drive=int(dr.sum()), eased=int(free.sum()),
                             grade=round(float((z_join - DRIVE_FLAT[-1][1]) / (s_join - DRIVE_FLAT[-1][0])), 3),
                             join=round(float(z_join), 2),
                             moved=(int((np.abs(d) > 0.05).sum()), round(float(d.min()), 1), round(float(d.max()), 1)))
