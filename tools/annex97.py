"""상대별관(대우관 별관) 앞 찻길과 대우관 테라스 찻길의 동쪽 어귀의 1997년 땅 (#189; reference/고증/3.6.6 「1997년 7월 원본 스캔으로
잰 찻길」, 3.6.3 「테라스 찻길의 동쪽 어귀」). tools/build_campus.py 가 부른다.

    took, info = annex97.grade(Hn, X, Y, FIXED, frame, dh, terrace, halls, keep, fill)   # 심기가 끝난 뒤, gyoyuk97 다음

Frames: campus metres, x east, y north.  frame = (o, t, f): the annex's own, as build_campus.py's 「대우관 별관 앞」 block
(_af_*): u northwards along its front from the door's axis, v out of the front (west).  dh = (DH_U, DH_V): 대우관's
frame at the grid's nodes (u east along the front from its west end, v from the front wall back; the terrace drive
v -18.3 .. -10.4).  Every absolute height is above sea level (해발), taken up to the working datum (해발 + tilt:
tools/datum.py) at its own place where it is read.

The drive before the annex (OSM's service road from the footway's east end past the door to the terrace drive) on the
1997-07-28 scans: profiles across it (the kerbs, 5.3 and 11 m out of the wall abreast of the door, bright lines in all
six frames), averaged 3 - 4 m along it, matched between frames of the two flight lines (26 x 27: across a north-south
road that pair is the one that sees the kerbs move with height), the median of the pairs over 0.7 (two windows, kerb
to kerb and 4 - 12.5 m out, within 0.1 - 0.3 m of each other):

- PROF: 59.6 m at the footway's end (u -22), 12 - 14 % up to the door's axis (62.4 - 62.6 m), 15 % on to u 18
  (64.55 m), 17 % to u 24 (65.6 m), then 65.7 - 65.9 m where the terrace drive comes in (u 25 - 33) and up again to
  66.45 m at its north kerb.  The 1996 winter frames see the drive only in the annex's shadow (no kerbs): not used.
  The 2024 survey's spot at the footway's end (139.5, 396.0) 59.32 m, and by the annex's north-west corner (154, 443:
  u 26, 4 m out) 65.22 (2006) · 65.63 m (2024)
- the game had the drive from a ramp south of the door (59.3 m at u -16 to 62.4 at u -8, the footway's link at the
  1996 frames' 59.25 - 59.95 m south of it: tools/gyoyuk97.py, now taken out) and the apron levelled before the door
  (62.6 - 62.7 m from u -6 to 2), then one grade up to the terrace drive's level (66.58 m at u 28): 0.4 - 0.8 m under
  the scans at u -20 .. -14, 0.5 - 0.95 m over them at u -10 .. -4 and 0.4 - 0.7 m over them from u 6 to 30
- the door's apron (DOOR: the two flights, the threshold, 3.6.6 「두 계단과 찻길」) stays as it is (0.1 - 0.3 m over
  the scans' 62.35 - 62.64 m), eased into PROF by 9 m either side.  The hall's floor (eight risers over it) stays
- STRIP: between the wall and the drive's east kerb the ground goes to the drive's height abreast (as the block before
  the planting laid it from u -13 to 13), from the south-west corner to the north-west one
- MOUTH: the terrace drive comes down to the drive over its last 3 m (the scans, its south kerb: 66.47 · 66.38 · 66.31
  m at 대우관's u 52 · 54 · 56, 65.78 · 65.48 at 58 · 60, where the drive's middle is; its north kerb 66.35 - 66.5 m to
  the drive): its nodes from 12.5 m out of the annex's wall (the drive's west kerb 11 m) to the drive's middle, eased
  from the terrace's level (66.58 m) to PROF

Nothing here draws from build_campus.py's `rng`; the trees, the paths and the cars stay where they are.
"""
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

import datum

V_MID = 8.0                              # (the drive's middle, m out of the wall: OSM's line 7.0 - 8.1, the kerbs 5.3 - 11.0)
BAND = (3.4, 11.5)                       # (v: nodes between these take its profile, the asphalt and its kerbs; west of it the
                                         # 상뜰's lawn and the terrace's bank stay)
U0, U1 = -22.8, 34.0                     # (from the footway's east end, gyoyuk97's FOOTWAY, to the terrace drive's north kerb)
# (u, 해발) along the drive's middle: the scans' profiles, smoothed over 4 m (3.6.6)
PROF = [(-22.8, 59.3), (-20.0, 59.78), (-18.0, 60.08), (-16.0, 60.38), (-14.0, 60.63), (-12.0, 61.0), (-10.0, 61.28),
        (-8.0, 61.55), (-6.0, 61.8), (-4.0, 62.12), (-2.0, 62.3), (0.0, 62.45), (2.0, 62.52), (4.0, 62.56),
        (6.0, 62.68), (8.0, 63.04), (10.0, 63.38), (12.0, 63.68), (14.0, 63.95), (16.0, 64.22), (18.0, 64.55),
        (20.0, 64.9), (22.0, 65.28), (24.0, 65.6), (26.0, 65.72), (28.0, 65.82), (30.0, 66.02), (32.0, 66.42),
        (34.0, 66.62)]
DOOR = (3.0, 9.0)                        # (|u|: the apron as it is to 3 m, PROF from 9 m)
STRIP = (0.8, -21.6, 21.5)               # (v from, u from, u to: the wall's ends, its south-west and north-west corners)
MOUTH_DH_V = (-19.5, -9.0)               # (대우관's v: the terrace drive and its kerbs)
MOUTH_V = (9.5, 12.5)                    # (the annex's v: PROF from the first, the terrace's level from the second)
RING = 6.0                               # eased round what is laid (harmonic), where nothing else holds the nodes
DECK_U = (52.0, 56.0)                    # (대우관's u: the terrace's deck over the cells its wall crosses keeps the terrace's
                                         # level to the first, the ground's from the second: the mouth)


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def prof_z(u):
    return np.interp(u, *zip(*PROF))


def mouth_z(x, y, frame, terrace):
    """(working datum) the ground grade() lays over the terrace drive's mouth at (x, y): the terrace's level eased into
    the drive's (MOUTH_V), the drive's as PROF"""
    o, t, f = (np.asarray(q, float) for q in frame)
    u = (x - o[0]) * t[0] + (y - o[1]) * t[1]
    v = (x - o[0]) * f[0] + (y - o[1]) * f[1]
    z = float(prof_z(np.clip(u, U0, U1))) + float(datum.tilt(x, y))
    w = float(smooth((MOUTH_V[1] - v) / (MOUTH_V[1] - MOUTH_V[0])))
    return terrace + (z - terrace) * w


def deck_h(u, terrace, ground):
    """the terrace deck's level at 대우관's u (build_campus.py DAEWOO['deck']): the terrace's, eased to ground (mouth_z
    there: not the grid, whose nodes under the wall's cells are pulled down) over the drive's mouth, never over the
    terrace's"""
    w = float(smooth((u - DECK_U[0]) / (DECK_U[1] - DECK_U[0])))
    return terrace + (min(terrace, ground) - terrace) * w


def grade(Hn, X, Y, FIXED, frame, dh, terrace, halls, keep, fill):
    """The drive before the annex, the strip between it and the wall, and the terrace drive's last metres on the
    scans' levels (over the nodes laid before: the apron before the door, 3.6's drive up to the terrace, gyoyuk97's
    link at the footway's end); the door's apron, the halls' feet (halls: outlines and the distance round each whose
    nodes stay) and keep stay; the ring round them eased where no block before held it.  terrace: the terrace's
    level (working datum, build_campus.py DAEWOO['terrace']).  Returns the nodes set (to be FIXED) and a summary"""
    o, t, f = (np.asarray(q, float) for q in frame)
    dhu, dhv = dh
    H0 = Hn.copy()
    T = datum.tilt(X, Y)
    U = (X - o[0]) * t[0] + (Y - o[1]) * t[1]
    V = (X - o[0]) * f[0] + (Y - o[1]) * f[1]
    hall_keep = shapely.contains_xy(unary_union([h.buffer(k) for h, k in halls]), X, Y)
    stay = hall_keep | keep
    band = (V >= BAND[0]) & (V <= BAND[1]) & (U >= U0) & (U <= U1)
    strip = (V >= STRIP[0]) & (V < BAND[0]) & (U >= STRIP[1]) & (U <= STRIP[2])
    mouth = (dhv >= MOUTH_DH_V[0]) & (dhv <= MOUTH_DH_V[1]) & (V >= BAND[0]) & (V <= MOUTH_V[1] + 5.0) & (U <= U1)
    door = smooth((np.abs(U) - DOOR[0]) / (DOOR[1] - DOOR[0]))          # (0 at the apron: as it is; 1: PROF)
    m = (band | strip | mouth) & ~stay
    z = prof_z(np.clip(U[m], U0, U1)) + T[m]
    z = H0[m] + (z - H0[m]) * door[m]
    wm = np.where(mouth[m], smooth((MOUTH_V[1] - V[m]) / (MOUTH_V[1] - MOUTH_V[0])), 1.0)
    z = terrace + (z - terrace) * wm if np.ndim(terrace) == 0 else z
    Hn[m] = z
    took = m
    near = shapely.contains_xy(unary_union([h.buffer(max(k, 2.0)) for h, k in halls]), X, Y)   # (the ring leaves the halls' feet)
    ring = (V >= BAND[0] - RING) & (V <= BAND[1] + RING) & (U >= U0 - RING) & (U <= U1 + RING) & ~took & ~FIXED & ~near & ~stay
    if ring.any():
        fill(ring)
    d = Hn - H0
    sel = took & band & ~mouth
    return took | ring, dict(drive=int((band & took).sum()), strip=int((strip & took).sum()), mouth=int((mouth & took).sum()),
                             eased=int(ring.sum()),
                             moved=(int((np.abs(d) > 0.05).sum()), round(float(d.min()), 2), round(float(d.max()), 2)),
                             drive_dz=(round(float(d[sel].min()), 2), round(float(d[sel].max()), 2)) if sel.any() else None)


# --- 세모 숲과 별관 동쪽 마당 (reference/고증/3.6.3 「테라스 찻길의 동쪽 어귀」 · 「세모 숲의 오솔길」): between the drive past
# the annex's north end, 북문 가는 길's boulder bank and the annex, a wood with two bare paths (the 1997 scans: light bands
# 1.5 - 2 m wide in 27/15 and 26/14, within 0.5 - 1 m of each other with the frames' lean), the ground under it flat
# at the drive's level (66.5 - 67.1 m; the game's smooth slope stood 0.3 - 1.7 m over it), and east of the annex a low
# bare yard (64.8 - 65.7 m, the game 1 - 3 m over it) the southern path runs down into, to OSM's walk round the annex.
# (x, y): campus metres.  WOOD_Z: the scans' heights there (x, y, 해발; windows 3 m, the median of the pairs over 0.7,
# three to nine pairs, crowns left out)
TRAILS = [[(161.0, 453.0), (162.8, 452.3), (166.5, 450.6), (169.8, 448.6), (171.8, 446.3), (172.9, 443.6)],
          [(160.5, 445.0), (162.6, 444.6), (166.5, 443.9), (170.0, 443.6), (173.0, 443.2), (176.0, 441.8), (178.5, 439.6),
           (180.4, 436.5), (181.2, 433.0), (181.8, 429.0), (181.8, 425.0), (180.5, 421.8), (177.4, 419.3)]]
TRAIL_W = 1.5
WOOD = Polygon([(158.5, 456.5), (166.0, 456.5), (170.5, 452.5), (175.0, 446.0), (178.0, 441.0), (173.0, 438.5), (160.0, 439.5)])
YARD = Polygon([(173.0, 438.5), (178.0, 441.0), (181.5, 437.0), (184.5, 430.0), (186.5, 420.0), (186.0, 413.0), (173.0, 413.0)])
WOOD_Z = [(161.0, 452.0, 67.09), (164.0, 452.0, 66.66), (167.0, 452.0, 67.05), (167.0, 449.0, 66.87), (170.0, 449.0, 67.04),
          (167.0, 446.0, 66.76), (170.0, 446.0, 66.80), (164.0, 443.0, 66.47), (170.0, 443.0, 66.48), (161.0, 440.0, 66.10),
          (167.0, 440.0, 66.65), (170.0, 440.0, 66.74), (163.8, 451.9, 66.67), (169.1, 449.0, 67.02), (171.2, 447.0, 66.89),
          (172.6, 444.4, 67.01), (166.4, 443.9, 66.65), (172.4, 443.3, 66.50), (167.0, 437.0, 65.69),
          (176.0, 437.0, 65.38), (179.0, 437.0, 65.41), (179.0, 434.0, 64.89), (182.0, 428.0, 64.99), (182.0, 425.0, 64.83),
          (176.0, 422.0, 64.84), (185.0, 422.0, 64.90), (176.0, 419.0, 64.88), (179.0, 419.0, 64.89), (179.0, 416.0, 65.02),
          (173.0, 416.0, 65.42), (179.7, 421.2, 64.95)]
WOOD_RING = 5.0


def wood_z(x, y):
    """해발 by inverse squared distance from WOOD_Z"""
    t = np.asarray(WOOD_Z)
    w = 1.0 / np.maximum((np.asarray(x)[:, None] - t[:, 0]) ** 2 + (np.asarray(y)[:, None] - t[:, 1]) ** 2, 1.0)
    return (w * t[:, 2]).sum(1) / w.sum(1)


def wood_grade(Hn, X, Y, FIXED, halls, fill):
    """WOOD and YARD on the scans' levels (WOOD_Z), the ring round them eased where no block before held it; the halls'
    feet (halls: [(outline, distance)]) stay.  Returns the nodes set and a summary"""
    H0 = Hn.copy()
    stay = shapely.contains_xy(unary_union([h.buffer(k) for h, k in halls]), X, Y)
    m = shapely.contains_xy(unary_union([WOOD, YARD]), X, Y) & ~stay
    Hn[m] = wood_z(X[m], Y[m]) + datum.tilt(X[m], Y[m])
    near = shapely.contains_xy(unary_union([h.buffer(max(k, 2.0)) for h, k in halls]), X, Y)
    ring = shapely.contains_xy(unary_union([WOOD, YARD]).buffer(WOOD_RING), X, Y) & ~m & ~FIXED & ~near
    if ring.any():
        fill(ring)
    d = Hn - H0
    return m | ring, dict(wood=int(m.sum()), eased=int(ring.sum()),
                          moved=(int((np.abs(d) > 0.05).sum()), round(float(d.min()), 2), round(float(d.max()), 2)))


def trail_polys():
    return [LineString(t).buffer(TRAIL_W / 2, cap_style='flat') for t in TRAILS]


def trail_clear(items, clear=1.3):
    """trees standing on a path ([kind, x, y, ...]) moved aside to `clear` m off its middle, in their places in the list"""
    moved = []
    for it in items:
        p = shapely.Point(it[1], it[2])
        for t in TRAILS:
            ls = LineString(t)
            d = ls.distance(p)
            if d < clear:
                q = ls.interpolate(ls.project(p))
                v = np.array([it[1] - q.x, it[2] - q.y])
                if np.linalg.norm(v) < 1e-6:
                    a, b = ls.interpolate(max(ls.project(p) - 0.5, 0.0)), ls.interpolate(min(ls.project(p) + 0.5, ls.length))
                    v = np.array([-(b.y - a.y), b.x - a.x])
                v = v / np.linalg.norm(v)
                it[1], it[2] = round(float(q.x + v[0] * clear), 2), round(float(q.y + v[1] * clear), 2)
                moved.append(it[0])
                break
    return moved
