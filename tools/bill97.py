"""빌링슬리관(가정관) 동쪽 면 곁의 1997년 찻길과 둑 (#189; reference/고증/3.12 「동쪽 면 곁의 찻길과 둑」). tools/build_campus.py 가
부른다.

    took, info = bill97.grade(Hn, X, Y, FIXED, keep, fill)      # 심기가 끝난 뒤, annex97 다음
    bill97.OLD_STRIP · NEW_STRIP                                 # (칠: 걷어 낼 아스팔트, 새 아스팔트)
    moved = bill97.clear(items)                                  # (새 아스팔트 위의 나무 · 관목 · 소품 · 차를 목록의 제자리에서 비킴)
    DAEWOO['bank'] = bill97.bank_pts()                           # (상뜰 바위 둑을 1997년 동쪽 연석 뒤로)

Frames: campus metres, x east, y north; s along OSM's line of 연희관 서쪽 옆길 (tools/gyoyuk97.py DRIVE, from 연희관 앞길's
west end), v across it, west +.  Every absolute height is above sea level (해발), taken up to the working datum at its own
place where it is read.

On the 1997-07-28 scans the drive beside 빌링슬리관's east face is not on OSM's line: profiles across it in the three east
frames (27/15 · 27/16 · 27/17, which see the face's foot; their kerb lines agree within 0.2 m) put its west kerb 0.8 -
1.0 m east of that line from the footway's node (s 62) to s 84 and 1.1 - 2.0 m east of it south of there (s 48 - 58),
its east kerb 6.3 - 6.4 m east of it (s 66 - 82: the 상뜰's south-west lawn's kerb, the same curve in the west frames):
the drive 5.4 m wide with its middle 3.6 m east of OSM's.  West of the west kerb, 4.5 - 5.5 m of planted ground (dark in
every frame) up to the face, which stands on the lawn's level (the floor 60.4 m; the drive 56.2 - 59.0 m beside it).
The game had OSM's line, 6 m of asphalt from the face's foot (1 - 1.5 m off it): its west kerb on the 5 m grid's slope
from the drive up to the hall's nodes (the kerb waving 1 - 2 m up and down) and the hall's foundation bared 1.6 m at
its south-east corner; and the 상뜰's bank (gyoyuk97's DRIVE_BANK, 4 - 8.5 m east of OSM's line) over the drive's east
half.

- OLD_STRIP: OSM's asphalt west of the 1997 west kerb, s 46 - 86, taken up (lawn: the planted strip)
- bank_pts: the 상뜰's boulder bank (build_campus.py DAEWOO['bank'], from the 2008 roadview) behind the 1997 east kerb
  instead of 3.2 m out of OSM's line
- NEW_STRIP: the drive between its 1997 kerbs, asphalt (s 61 - 86 its east half where the bank was; s 46 - 61 to 5.5 m east)
- heights: the drive's nodes between its kerbs (and the strip's first 2.5 m west of the west kerb, under its kerb) at
  gyoyuk97's profile (the scans along OSM's line; along the 1997 middle line they read within 0.3 m of it: 55.6 at s
  46, 56.8 at 62, 58.85 at 70, 59.5 at 74, 60.1 at 78, 60.6 at 82 m); the 상뜰's bank east of it from the east kerb's
  foot (6.6 m east of OSM's line) to its top (gyoyuk97's TOP) 11 m east of it; the planted strip a bank from 2.5 m west
  of the west kerb up to just under the hall's floor (BANK_W: never lower than it stood); nodes within 2 m of the hall,
  the 상뜰 and keep stay

Nothing here draws from build_campus.py's `rng`; the list items moved off the new asphalt keep their places in the lists.
"""
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon
from shapely.ops import substring, unary_union

import datum
import gyoyuk97

DRIVE = gyoyuk97.DRIVE
S_A, S_B = 46.0, 86.0                     # (the stretch beside the hall: from abreast of 연희관's north-west corner to past the hall)
S_NEW = 61.0                              # (the new asphalt from the footway's node north)
# (s, v of the west kerb: the scans, east frames)
KERB_W = [(46.0, -2.0), (50.0, -1.8), (54.0, -1.5), (58.0, -1.1), (62.0, -0.9), (86.0, -0.9)]
KERB_E = -6.4                             # (v of the east kerb, s 66 - 82; the lawn's curve meets the footway south of it)
OLD_W = 3.4                               # (v: OSM's asphalt to here, 6 m wide and its edge)
# (빌링슬리관's east pavilion as the 1997 scans have it: build_campus.py BILL_UV's pav, u 38.2 - 47, v 2.3 - 16.8)
HALL_E = Polygon([(51.62, 410.29), (60.13, 408.03), (63.85, 422.05), (55.34, 424.31)])
BANK = (6.6, 11.0)                        # (m east of OSM's line: the 상뜰's bank's foot and top beside the 1997 drive)
VERGE = 2.5                               # (m west of the west kerb at the drive's level: the strip under the kerb)
BANK_W = (OLD_W + 1.0, 60.0)              # (the planted strip's bank up to the hall: v of its top, 해발 just under the floor's 60.4)


def kerb_w(s):
    return np.interp(s, *zip(*KERB_W))


def _side_strip(s0, s1, v0f, v1f, step=1.0):
    """the polygon between offsets v0f(s) and v1f(s) (west +) along DRIVE from s0 to s1"""
    ss = np.arange(s0, s1 + 1e-6, step)
    a, b = [], []
    for s in ss:
        p = DRIVE.interpolate(s)
        q0, q1 = DRIVE.interpolate(max(s - 0.5, 0.0)), DRIVE.interpolate(min(s + 0.5, DRIVE.length))
        t = np.array([q1.x - q0.x, q1.y - q0.y])
        t /= np.linalg.norm(t)
        w = np.array([-t[1], t[0]])        # (west, left of the line going north)
        a.append(tuple(np.array([p.x, p.y]) + w * v0f(s)))
        b.append(tuple(np.array([p.x, p.y]) + w * v1f(s)))
    return Polygon(a + b[::-1]).buffer(0)


OLD_STRIP = _side_strip(S_A, S_B, kerb_w, lambda s: OLD_W)
NEW_STRIP = _side_strip(S_A, S_B, lambda s: KERB_E if s >= S_NEW else -5.5, kerb_w)   # (the whole drive between its kerbs)


def grade(Hn, X, Y, FIXED, halls, keep, fill):
    """The drive between its 1997 kerbs and the strip under its west kerb at gyoyuk97's profile, the 상뜰's bank east of
    it from the east kerb up to gyoyuk97's TOP (over the nodes laid there before: gyoyuk97's drive and bank); the
    halls' feet (halls: [(outline, distance)]), the 상뜰 (keep) stay.  Returns the nodes set (to be FIXED) and a summary"""
    H0 = Hn.copy()
    P = shapely.points(X, Y)
    T = datum.tilt(X, Y)
    s = shapely.line_locate_point(DRIVE, P)
    v = np.sign(gyoyuk97._cross(DRIVE, s, X, Y)) * shapely.distance(DRIVE, P)     # (west +)
    stay = shapely.contains_xy(unary_union([h.buffer(k) for h, k in halls]), X, Y) | keep
    on = (s >= S_A) & (s <= S_B)
    kw = kerb_w(s)
    zj = 0.0                                                    # (gyoyuk97 drive_z needs the join's level past S_PROF: not reached)
    zd = gyoyuk97.drive_z(np.clip(s, gyoyuk97.S0, gyoyuk97.S_PROF), zj)
    east = np.where(s >= S_NEW, BANK[0], 5.5)
    road = on & (v >= -east) & (v <= kw + VERGE) & ~stay
    Hn[road] = zd[road] + T[road]
    bank = on & (s >= S_NEW) & (v < -BANK[0]) & (v >= -BANK[1] - 1.0) & ~stay
    zt = gyoyuk97.top_z(X[bank], Y[bank])
    k = np.clip((-v[bank] - BANK[0]) / (BANK[1] - BANK[0]), 0.0, 1.0)
    Hn[bank] = np.minimum(zd[bank] + (zt - zd[bank]) * k, zt) + T[bank]
    # the planted strip west of the drive: a bank from the strip under the kerb up to the hall's foot (south of the hall's
    # south-east corner the node there stood at the drive's level, baring the foundation's corner)
    bw = on & (v > kw + VERGE) & (v <= BANK_W[0]) & ~stay
    kb = np.clip((v[bw] - kw[bw] - VERGE) / (BANK_W[0] - kw[bw] - VERGE), 0.0, 1.0)
    zb = zd[bw] + (BANK_W[1] - zd[bw]) * kb
    Hn[bw] = np.maximum(Hn[bw] - T[bw], zb) + T[bw]
    took = road | bank | bw
    d = Hn - H0
    return took, dict(road=int(road.sum()), bank=int(bank.sum()), strip_bank=int(bw.sum()),
                      moved=(int((np.abs(d) > 0.05).sum()), round(float(d.min()), 2), round(float(d.max()), 2)))


def clear(items, kind_r=None, pad=0.6):
    """List items ([kind, x, y, ...]) standing on NEW_STRIP (with pad m) moved east off it, in their places in the list:
    across the drive to 0.8 m past its east kerb.  Returns how many"""
    zone = NEW_STRIP.buffer(pad)
    n = 0
    for it in items:
        if not zone.contains(shapely.Point(it[1], it[2])):
            continue
        s = DRIVE.project(shapely.Point(it[1], it[2]))
        p = DRIVE.interpolate(s)
        q0, q1 = DRIVE.interpolate(max(s - 0.5, 0.0)), DRIVE.interpolate(min(s + 0.5, DRIVE.length))
        t = np.array([q1.x - q0.x, q1.y - q0.y])
        t /= np.linalg.norm(t)
        w = np.array([-t[1], t[0]])
        q = np.array([p.x, p.y]) + w * (KERB_E - pad - 0.8)
        it[1], it[2] = round(float(q[0]), 2), round(float(q[1]), 2)
        n += 1
    return n


def bank_pts(out=6.8, edge=6.4):
    """build_campus.py DAEWOO['bank'] (blender/landmarks.py sang_stone_bank: the 상뜰's boulder bank along its west drive,
    round the corner and on along the footway) behind the 1997 east kerb: the same course as build_campus.py lays it
    3.2 m out of OSM's line (2.8 m: the drive's edge there), `out` m (edge m)"""
    import math
    kd, ke = np.array([-0.2301, -0.9732]), np.array([0.9732, -0.2301])     # (the drive southwards, its east side)
    fd, fn = np.array([0.9685, -0.2491]), np.array([0.2491, 0.9685])       # (the footway eastwards, its north side)
    c0 = np.array([71.8, 436.3])
    f0 = np.array([66.6, 414.3]) + fn * 1.5
    a = np.linalg.solve(np.array([kd, -fd]).T, f0 - (c0 + ke * out))
    q = c0 + ke * out + kd * a[0]                                         # (where the two kerb lines meet)
    r = 2.4
    kt = r * math.tan(math.acos(float(kd @ fd)) / 2)
    o = q - kd * kt + ke * r
    pts = []
    s_end = float((q - kd * kt - c0 - ke * out) @ kd)
    for s in np.linspace(2.0, s_end, int(round(s_end - 2.0)) + 1):
        c = c0 + kd * s
        pts.append([*(c + ke * out), *(c + ke * edge), 0.6 + 0.4 * (s - 2.0) / (s_end - 2.0)])
    a0, a1 = math.atan2(*(-ke)[::-1]), math.atan2(*(-fn)[::-1])
    for k in range(1, 4):
        an = a0 + (((a1 - a0 + math.pi) % (2 * math.pi)) - math.pi) * k / 4
        p = o + r * np.array([math.cos(an), math.sin(an)])
        pts.append([*p, *(p + (p - o) / r * 0.4), 1.0])
    # on along the footway to the 상뜰 south flight's west cheek, (100.8, 407.6) at its foot (campus.json daewoo_front
    # stair): the 1997-07-28 scans have the course of boulders at the foot of the 상뜰's south bank all the way to it
    # (reference/고증/3.6.1 「1996 ~ 1997년의 나무와 남쪽 둑」)
    for t in np.linspace(0.0, FOOT_W, int(round(FOOT_W)) + 1):
        p = q + fd * (kt + t)
        pts.append([*p, *(p - fn * 0.4), 1.0])
    return [[round(float(v), 2) for v in p] for p in pts]


FOOT_W = 25.2                 # (bank_pts: along the footway from the corner's end to 0.6 m short of the flight's cheek)
FOOT_E = (27.1, 52.0)         # (bank_east_pts: from 0.6 m past the flight's east cheek to x 130, on the same line)


def bank_east_pts(out=6.8):
    """build_campus.py DAEWOO['bank_east'] (blender/landmarks.py sang_stone_bank): the course of boulders at the foot of
    the 상뜰's south bank east of its south flight, on the line bank_pts runs along the footway (the 1997-07-28 scans)"""
    import math
    kd, ke = np.array([-0.2301, -0.9732]), np.array([0.9732, -0.2301])
    fd, fn = np.array([0.9685, -0.2491]), np.array([0.2491, 0.9685])
    c0 = np.array([71.8, 436.3])
    f0 = np.array([66.6, 414.3]) + fn * 1.5
    a = np.linalg.solve(np.array([kd, -fd]).T, f0 - (c0 + ke * out))
    q = c0 + ke * out + kd * a[0]
    kt = 2.4 * math.tan(math.acos(float(kd @ fd)) / 2)
    pts = []
    for t in np.linspace(FOOT_E[0], FOOT_E[1], int(round(FOOT_E[1] - FOOT_E[0])) + 1):
        p = q + fd * (kt + 4.0 + t)
        pts.append([*p, *(p - fn * 0.4), 1.0])
    return [[round(float(v), 2) for v in p] for p in pts]



# The lawn's south-east corner (reference/고증/3.12 「남동 귀퉁이와 연희관 서쪽 옆길의 계단」): between widang97.bank_grade
# (its band stops at x 47) and grade above (from s 46) the nodes kept the slope of OSM's days, the corner dropping to the
# drive's level 4 m inside the lawn and a ramp north of it, the asphalt at the corner's kerb lifted by nodes 1 - 2 m
# behind it.  The scans (1996-12 leafless and 1997-07): the lawn's head rounds in towards the south-east (HEAD), a bank
# 2.5 m down to a shelf (57.4 m, x 49 - 53) and 2 m on the yard (55.1 m).
# The game's kerb round the corner (campus.json curbs, the lawn on its left going along): the south road's north kerb, the
# drive's west kerb, the corner, the 1997 west kerb north
KERB_C = LineString([(44.5, 384.9), (46.1, 384.4), (47.0, 384.1), (49.3, 383.5), (51.1, 382.9), (52.3, 382.5), (52.7, 382.5),
                     (53.0, 382.9), (53.9, 385.3), (55.4, 389.5), (56.6, 393.1), (57.9, 396.5), (58.6, 398.9), (59.0, 399.4),
                     (59.7, 399.4), (61.2, 398.9), (63.3, 398.2), (63.8, 398.9), (64.4, 401.3), (65.1, 404.4)])
CORNER = Polygon(list(KERB_C.coords) + [(56.0, 404.4), (47.5, 404.4), (47.5, 380.0)]).buffer(0)
CORNER_X = 47.5                    # (west of here widang97's band)
HEAD = LineString([(44.0, 387.5), (46.0, 390.0), (47.5, 394.0), (48.5, 397.0), (48.0, 400.0), (52.0, 402.5), (56.0, 405.0)])
LAWN_Z = 60.1                      # (해발: the lawn west of HEAD, 60.0 - 60.2 m)
HEAD_FALL = (2.5, 2.7)             # (the bank under HEAD: m out, m down)
SHELF_Z = 57.4                     # (해발: the shelf, 56.9 - 57.7 m)
CORNER_W = (2.5, 5.0)              # (m behind the game's kerb: the drive's level to here, the scans' ground from here)


def corner_grade(Hn, X, Y, halls):
    """The corner's nodes on the lawn's side of KERB_C east of CORNER_X: the scans' ground (the lawn west of HEAD, its
    bank down to the shelf) CORNER_W[1] m behind the game's kerb and on, the drive's level (gyoyuk97's profile at the
    kerb's foot on DRIVE) CORNER_W[0] m behind it, eased between; the halls' feet stay.  Returns the nodes set and a
    summary"""
    H0 = Hn.copy()
    P = shapely.points(X, Y)
    T = datum.tilt(X, Y)
    stay = shapely.contains_xy(unary_union([h.buffer(k) for h, k in halls]), X, Y)
    on = shapely.contains_xy(CORNER, X, Y) & (X >= CORNER_X) & ~stay
    d = shapely.distance(KERB_C, P)
    foot = shapely.line_interpolate_point(KERB_C, shapely.line_locate_point(KERB_C, P))
    zd = gyoyuk97.drive_z(np.clip(shapely.line_locate_point(DRIVE, foot), gyoyuk97.S0, gyoyuk97.S_PROF), 0.0)
    out = np.where(shapely.contains_xy(Polygon(list(HEAD.coords) + [(56.0, 380.0), (44.0, 380.0)]), X, Y),
                   shapely.distance(HEAD, P), 0.0)          # (m out of HEAD on the drive's side)
    zg = np.maximum(LAWN_Z - out / HEAD_FALL[0] * HEAD_FALL[1], SHELF_Z)
    k = np.clip((d - CORNER_W[0]) / (CORNER_W[1] - CORNER_W[0]), 0.0, 1.0)
    Hn[on] = (zd + (zg - zd) * k)[on] + T[on]
    dd = Hn - H0
    return on, dict(nodes=int(on.sum()), moved=(int((np.abs(dd) > 0.05).sum()), round(float(dd.min()), 2),
                                                round(float(dd.max()), 2)))
