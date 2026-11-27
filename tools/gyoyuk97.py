"""교육관 북쪽 마당, 그 동쪽 마당, 연희관 서쪽 옆길과 상뜰 서쪽 길, 상뜰 남쪽 보도의 1997년 땅 (#189; reference/고증/3.5.1
「1997년 7월 원본 스캔으로 다시 잰 띠의 서쪽」 · 「옆길 북쪽과 상뜰 남쪽 보도」, 3.18 「교육관」, 2.8 「삼거리에서 연희관까지」).
tools/build_campus.py 가 부른다.

    took, info = gyoyuk97.grade(Hn, X, Y, FIXED, halls, fill, sample, keep, flight)   # 심기가 끝난 뒤, jonghap97 다음

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
- DRIVE (연희관 서쪽 옆길 and on beside the 상뜰 to 대우관's terrace: campus.json path 36, OSM's service road): read in
  windows laid along it (5 m along, 1.6 - 2.4 m across, at its middle and 1.2 - 1.5 m either side), the 1997 frames
  and, where 빌링슬리관's shadow or the trees hide it, the leafless 1996 winter frames (which read the 상뜰's open
  paving 0.0 - 0.3 m over the July ones): 55.0 - 55.4 m from the south end of 연희관's west wing to abreast of its
  north end (the 2024 survey's spot (58.6, 383.4) 55.15 m), 55.5 - 56.0 m on to y 403, then up 57.25 m at the
  footway's node (66.6, 414.3), 60.1 at y 432, 62.6 at y 445, 64.6 at y 457 (the survey's 65 m contour, 2006 and 2024,
  crosses it at y 457 - 458; its spots by it at y 463 - 464 65.5 · 66.2 m), 66.0 - 66.6 m from y 467 where 대우관's
  terrace drive leaves it, 67.0 m at y 476 as the game has it.  The game had it 3.1 - 3.6 m over that at the
  footway, 2 - 2.5 m beside the 상뜰 and 0.5 - 1 m by the terrace (DRIVE_PROF; from S_PROF to S_JOIN one grade to the
  ground 3.6 laid along the west wing, which stays).  The terrace's west corner, whose nodes stand in the drive's
  east edge (u -12.7 of the hall's frame), goes with the drive: the scans 65.2 - 66.2 m there (x 79 - 82, y 461 - 467)
- FOOTWAY (상뜰 남쪽 보도, path 65): 57.25 m at the drive, 57.9 - 58.0 m on to the foot of the 상뜰's south flight
  (the flight's foot, 3.6.1, stays: 58.27 m on the scans), then up to 59.2 m at its east end, where the 2024 survey
  has 59.32 m at (139.5, 396.0).  The game ran it from 61.1 m down to the flight's foot and up to 60.75 m again
- EAST_LINK (path 221, from the car park behind 연희관 up to the footway's east end) and the last metres of the road
  behind 연희관 (BACK_END, path 72): the car park 55.4 - 55.6 m to its east end (both flights), the link 56.9 · 57.5 ·
  58.1 m a third, a half, two thirds of the way up (the 1996 frames).  The game had the road climbing 2.5 m in its
  last 10 m to the link (58.3 m); the road's first metres off the drive (BACK_START) 55.5 m where the game had 57.7
- (the drive past 대우관 별관's front, from the footway's end on: tools/annex97.py, after this)

Nothing here draws from build_campus.py's `rng`; the trees, the paths and the cars stay where they are.
"""
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon
from shapely.ops import substring, unary_union

import datum

# the drive's middle, campus.json path 36 (OSM), from 연희관 앞길's west end past the 상뜰 to 대우관's west wing
DRIVE = LineString([(51.7, 354.5), (50.7, 363.9), (54.7, 378.7), (61.7, 398.7), (66.6, 414.3), (71.8, 436.3),
                    (75.2, 453.9), (76.9, 462.7), (83.8, 485.7)])
DRIVE_HALF = 5.0                          # nodes this near its middle take its profile (6 m of asphalt and the verges)
S0 = 6.0                                  # (the drive before this, by 연희관 앞길: 54.8 - 55.0 m, as the scans)
S_FOOT = 62.32                            # (s of the footway's node)
# (s along DRIVE, 해발): the scans (1997, the 1996 winter frames where those see nothing), the survey's 65 m contour
DRIVE_PROF = [(6.0, 54.95), (24.8, 55.2), (34.0, 55.4), (46.0, 55.7), (52.0, 55.95), (58.0, 56.6), (S_FOOT, 57.25),
              (66.0, 57.95), (68.0, 58.3), (72.0, 58.95), (76.0, 59.6), (80.0, 60.1), (84.0, 60.9), (88.0, 61.6),
              (94.0, 62.6), (100.0, 63.5), (106.0, 64.6), (110.0, 65.2), (114.0, 65.8), (118.0, 66.1), (122.0, 66.45)]
S_PROF = DRIVE_PROF[-1][0]
S_JOIN = 126.0                            # (from here on 3.6's, along 대우관's west wing: the scans and the game meet there)
FOOTWAY = LineString([(66.6, 414.3), (101.2, 405.4), (137.7, 396.5)])
FOOT_HALF = 2.2
S_FLIGHT = 35.73                          # (s of the flight's foot, build_campus.py SANG_FOOT)
FOOT_PROF = [(4.0, 57.6), (8.0, 57.85), (30.0, 57.95), (42.0, 58.45), (57.0, 58.65), (63.0, 59.0), (69.0, 59.2),
             (73.3, 59.25)]               # (s along FOOTWAY, 해발; at 0 the drive's, at S_FLIGHT the flight's foot)
EAST_LINK = LineString([(132.1, 379.3), (137.7, 396.5)])
EAST_LINK_PROF = [(0.0, 55.8), (6.0, 56.9), (9.0, 57.5), (12.0, 58.1), (18.1, 59.25)]
BACK_END = LineString([(112.0, 384.9), (132.1, 379.3)])     # (path 72's last metres)
BACK_END_PROF = [(0.0, 55.3), (12.0, 55.4), (16.0, 55.55), (20.9, 55.8)]
BACK_START = LineString([(61.7, 398.7), (80.0, 393.7)])      # (and its first: 55.5 m off the drive, twelve pairs)
BACK_START_PROF = [(0.0, 55.7), (8.0, 55.5), (19.0, 55.15)]
LINK_HALF = 3.0
YARD = Polygon([(20.5, 353.5), (27.0, 351.2), (44.6, 346.7), (51.0, 348.5), (51.0, 362.0), (46.5, 364.0), (46.5, 388.0),
                (40.0, 386.5), (34.0, 385.5), (34.0, 362.5), (21.0, 362.5)])
YARD_Z = ((367.0, 377.0, 381.0, 385.0), (54.93, 55.42, 55.65, 56.3))   # (y, 해발 at x 42)
YARD_DX = -0.012                          # (m a metre east)
# between the yard's bright pad (its east edge a pale line at x 46 - 47 on the scans) and the drive: the drive's level
SIDE = Polygon([(46.5, 364.0), (51.0, 362.0), (56.0, 392.5), (50.5, 392.5), (46.5, 388.0)])
# east of where the road behind 연희관 leaves the drive: the old drive's level cross-section (build_campus.py TR_LEVEL),
# eased again between the drive and the car park behind 연희관 (the scans 56.1 - 56.3 m there)
LOOSE = Polygon([(62.5, 391.5), (72.5, 390.5), (74.5, 403.0), (71.5, 408.5), (66.5, 408.5)])
RING = 8.0                                # eased out (harmonic) this far round the yard and the drive's south part
# north of y 390 the ground the old drive, 3.6's footway and drive and the 상뜰's banks were laid on is eased again
# between the new lines, the 상뜰 (keep), the halls' feet and the car park behind 연희관, whose rows stay (CARS_KEEP)
WAYS_RING = 9.0
CARS_KEEP = Polygon([(76.0, 380.0), (121.0, 375.0), (121.0, 396.0), (76.0, 396.0)])
HALL_KEEP_BY_DRIVE = 2.0                  # (the halls' keep where the drive's nodes are: 빌링슬리관's east end stands 5 m off it)
# 연희관's west wing (its footprint's corners, build_campus.py YH_HALL): the nodes in it and round its west face, north
# end and court side (not its south front, on 앞길) are eased with the ways.  Kept as the hall's feet, the strip between
# the drive and the west face held the old drive's level, 3.6 m over the scans at the north-west corner ((65, 390):
# 59.1 m by the drive's 55.4), a paved ridge that rose 3 m in 4 m off the kerb
YH_WING = Polygon([(66.81, 393.36), (58.24, 363.56), (68.23, 360.69), (69.17, 363.96), (73.26, 378.18), (76.8, 390.48)])
YH_WING_RING = 2.5
YH_WING_FRONT = LineString([(58.24, 363.56), (68.23, 360.69)])
# The 상뜰's shoulder: west and south of the diamond the lawn is the 상뜰's own level to the top of steep banks down to
# the drive and the footway (cross sections on the scans, five-metre windows along the line: the footway's north kerb
# 1.5 m off its middle, the top 6 m off, 2.5 - 3 m up; the drive's east bank from 4 m to 8 m off, its foot the
# boulder bank).  TOP: the scans' heights on the top, (x, y, 해발); a node on a bank: the way's level rising to the top's
# (TOP by inverse distance) over the bank's width
TOP = [(84.0, 417.6, 61.03), (91.7, 415.6, 61.29), (110.7, 409.2, 61.45), (111.1, 410.7, 61.5), (118.5, 407.3, 61.35),
       (118.9, 408.8, 61.42), (126.3, 405.4, 61.44), (126.7, 406.9, 61.49), (134.4, 405.1, 61.29), (79.9, 427.3, 61.01),
       (79.4, 433.6, 61.3), (81.3, 433.1, 61.35), (80.7, 439.8, 61.6)]
FOOT_BANK = (1.5, 6.0)                    # (m off the footway's middle, north: the bank's foot and top)
DRIVE_BANK = (4.0, 8.5)                   # (m off the drive's middle, east, from the footway's node to SHOULDER_S)
SHOULDER_S = 92.0


def _cross(ls, s, X, Y):
    """(the line's direction at s) x (the node - its foot): > 0 left of the line"""
    a = shapely.line_interpolate_point(ls, np.clip(s - 0.5, 0.0, ls.length))
    b = shapely.line_interpolate_point(ls, np.clip(s + 0.5, 0.0, ls.length))
    c = shapely.line_interpolate_point(ls, s)
    ax, ay = shapely.get_x(a), shapely.get_y(a)
    bx, by = shapely.get_x(b), shapely.get_y(b)
    return (bx - ax) * (Y - shapely.get_y(c)) - (by - ay) * (X - shapely.get_x(c))


def yard_z(x, y):
    return np.interp(y, *YARD_Z) + YARD_DX * (x - 42.0)


def drive_z(s, z_join):
    """해발 along DRIVE: DRIVE_PROF, then one grade from its end to the ground at S_JOIN"""
    s_, z_ = zip(*DRIVE_PROF)
    return np.where(s <= S_PROF, np.interp(s, s_, z_), z_[-1] + (z_join - z_[-1]) * (s - S_PROF) / (S_JOIN - S_PROF))


def top_z(x, y):
    """해발 of the 상뜰's shoulder at (x, y): TOP by inverse squared distance"""
    t = np.asarray(TOP)
    w = 1.0 / np.maximum((x[:, None] - t[:, 0]) ** 2 + (y[:, None] - t[:, 1]) ** 2, 1.0)
    return (w * t[:, 2]).sum(1) / w.sum(1)


def grade(Hn, X, Y, FIXED, halls, fill, sample, keep, flight):
    """YARD, DRIVE, FOOTWAY and the two links on the scans' levels (over the nodes laid before them there: the old
    drive levelled across, widang97's ring, 교육관's north forecourt, 3.6's footway and west drive), eased round them;
    the halls' feet, the 상뜰 and its flight (keep), the car park's rows and the nodes laid before outside them stay.
    halls: [(outline, the distance round it whose nodes stay)] (교육관's north strip, 빌링슬리관's east end, 연희관);
    sample(x, y): the grid's height at a point (working datum); keep: nodes that stay whatever (the 상뜰's level, under
    its south flight); flight: (top, foot, half width of the strip under it) of that flight.  Returns the nodes set (to
    be FIXED) and a summary"""
    H0 = Hn.copy()
    P = shapely.points(X, Y)
    T = datum.tilt(X, Y)
    s = shapely.line_locate_point(DRIVE, P)
    dd = shapely.distance(DRIVE, P)
    by_drive = (dd <= DRIVE_HALF) & (s >= S_FOOT - 20.0) & (s < S_JOIN)
    hall_keep = np.where(by_drive, shapely.contains_xy(unary_union([h.buffer(min(k, HALL_KEEP_BY_DRIVE)) for h, k in halls]), X, Y),
                         shapely.contains_xy(unary_union([h.buffer(k) for h, k in halls]), X, Y))
    under = shapely.contains_xy(LineString(flight[:2]).buffer(flight[2], cap_style='flat'), X, Y)
    stay = hall_keep | keep | under
    z_join = sample(*DRIVE.interpolate(S_JOIN).coords[0]) - datum.tilt(*DRIVE.interpolate(S_JOIN).coords[0])
    fx, fy = FOOTWAY.interpolate(S_FLIGHT).coords[0]
    z_flight = sample(fx, fy) - datum.tilt(fx, fy)          # (the flight's foot as 3.6 laid it)
    dr = ((dd <= DRIVE_HALF) | shapely.contains_xy(SIDE, X, Y)) & (s >= S0) & (s < S_JOIN) & ~stay
    yd = shapely.contains_xy(YARD, X, Y) & ~dr & ~stay
    Hn[yd] = yard_z(X[yd], Y[yd]) + T[yd]
    # the footway: nodes nearer it than the drive's
    sf = shapely.line_locate_point(FOOTWAY, P)
    df = shapely.distance(FOOTWAY, P)
    fw = (df <= FOOT_HALF) & (sf > 0.5) & ~stay & ~shapely.contains_xy(CARS_KEEP, X, Y)
    dr &= ~(fw & (df < shapely.distance(DRIVE, P)))
    Hn[dr] = drive_z(s[dr], z_join) + T[dr]
    fp = [(0.0, float(drive_z(np.array(S_FOOT), z_join)))] + [q for q in FOOT_PROF if q[0] < S_FLIGHT] + \
        [(S_FLIGHT, z_flight)] + [q for q in FOOT_PROF if q[0] > S_FLIGHT]
    fw &= ~dr
    Hn[fw] = np.interp(sf[fw], *zip(*fp)) + T[fw]
    took = yd | dr | fw
    links = {}
    for nm, ls, prof in (('east_link', EAST_LINK, EAST_LINK_PROF), ('back_end', BACK_END, BACK_END_PROF),
                         ('back_start', BACK_START, BACK_START_PROF)):
        sl = shapely.line_locate_point(ls, P)
        m = (shapely.distance(ls, P) <= LINK_HALF) & (sl > 0.0) & (sl < ls.length) & ~stay & ~took
        if nm == 'back_end':
            m &= ~shapely.contains_xy(CARS_KEEP.buffer(-0.01), X, Y) | (X > 121.0)
        Hn[m] = np.interp(sl[m], *zip(*prof)) + T[m]
        took |= m
        links[nm] = int(m.sum())
    # the 상뜰's shoulder and its banks down to the footway (north of it) and the drive (east of it)
    fz = lambda q: np.interp(q, *zip(*fp))
    side_f = np.sign(_cross(FOOTWAY, sf, X, Y))             # (+1: left of the footway going east, the 상뜰's side)
    side_d = np.sign(_cross(DRIVE, s, X, Y))                # (-1: right of the drive going north, the 상뜰's side)
    nf = (side_f > 0) & (df > FOOT_HALF) & (sf > 0.5) & (sf < FOOTWAY.length) & (df < FOOT_BANK[1] + 4.0)
    nd = (side_d < 0) & (dd > DRIVE_HALF) & (s > S_FOOT - 1.0) & (s < SHOULDER_S) & (dd < DRIVE_BANK[1] + 4.0)
    sh = (nf | nd) & ~stay & ~took
    zt = top_z(X[sh], Y[sh])
    kf = np.clip((df[sh] - FOOT_BANK[0]) / (FOOT_BANK[1] - FOOT_BANK[0]), 0.0, 1.0)
    kd = np.clip((dd[sh] - DRIVE_BANK[0]) / (DRIVE_BANK[1] - DRIVE_BANK[0]), 0.0, 1.0)
    zf = np.where(nf[sh], fz(sf[sh]) + (zt - fz(sf[sh])) * kf, np.inf)
    zd = np.where(nd[sh], drive_z(s[sh], z_join) + (zt - drive_z(s[sh], z_join)) * kd, np.inf)
    Hn[sh] = np.minimum(zf, zd) + T[sh]
    took |= sh
    near = shapely.contains_xy(unary_union([h.buffer(1.0) for h, _ in halls]), X, Y)
    old_free = (shapely.contains_xy(unary_union([YARD, substring(DRIVE, 0.0, S_FOOT).buffer(DRIVE_HALF)]).buffer(RING), X, Y)
                & ~FIXED) | shapely.contains_xy(LOOSE, X, Y)
    ways = unary_union([substring(DRIVE, 34.0, S_JOIN).buffer(DRIVE_HALF + WAYS_RING, cap_style='flat'),
                        FOOTWAY.buffer(FOOT_HALF + WAYS_RING - 2.0), EAST_LINK.buffer(LINK_HALF + 5.0)])
    new_free = shapely.contains_xy(ways, X, Y) & ~shapely.contains_xy(CARS_KEEP, X, Y)
    wing = shapely.contains_xy(YH_WING.buffer(YH_WING_RING).difference(YH_WING_FRONT.buffer(YH_WING_RING, cap_style='square'))
                               .union(YH_WING), X, Y) & ~took & ~keep & ~shapely.contains_xy(CARS_KEEP, X, Y)
    free = ((old_free | new_free) & ~took & ~near & ~stay) | wing
    if free.any():
        fill(free)
    d = Hn - H0
    return took | free, dict(yard=int(yd.sum()), drive=int(dr.sum()), footway=int(fw.sum()), **links, shoulder=int(sh.sum()),
                             eased=int(free.sum()), yh_wing=int(wing.sum()),
                             join=round(float(z_join), 2), flight_foot=round(float(z_flight), 2),
                             moved=(int((np.abs(d) > 0.05).sum()), round(float(d.min()), 1), round(float(d.max()), 1)))
