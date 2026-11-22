"""연대동문길(한국어학당 앞을 지나 대신동 쪽으로 내려가는 찻길)의 1997년 자리 · 폭 · 노면 높이와 가로수
(reference/고증/3.27_한국어학당.md 「연대동문길의 가로수」 · 「연대동문길의 자리와 노면」). tools/build_campus.py 가 부른다.

    took, info = dongmungil97.grade(Hn, X, Y, FIXED, keep)         # 노면 높이 (심기가 끝난 뒤, kli97.grade 다음)
    old, new, walk = dongmungil97.strips()                         # 칠: 걷어 낼 OSM 의 아스팔트, 1997년 차도, 동쪽 보도
    dongmungil97.repath(paths)                                     # 길 목록의 그 길을 1997년 가운데 선으로(지도 · 사람)
    moved = dongmungil97.clear(items)                              # 새 차도 위의 나무 · 관목 · 소품 · 차를 목록의 제자리에서 비킴
    first, more, near = dongmungil97.trees(old_trees)              # 가로수: 열둘은 전의 자리에, 나머지는 목록의 맨 끝에
    dongmungil97.CARS                                              # 1996년 겨울 서쪽 연석에 줄지어 선 차

Frames: campus metres (x east, y north).  s runs along OSM's line of the road (OLD) southwards from its node
(425.9, 199.7), negative north of it; d across it, east +.  Heights are above sea level (해발), taken up to the working
datum where they are laid (datum.tilt).

The road as the scans have it (the three frames of the 1996 winter flight, 27/15 · 27/16 · 27/17, re-projected on the
road's own height; the summer frames of 1997 - 1999 where the crowns leave it open):
- its two rows of trees stand 8.0 - 8.4 m apart, their middle 1.0 m east of OSM's line from s 60 to 230 and up to 5 m
  east of it at OSM's node (s 0): the real road runs straight on north-north-west there, back on OSM's line by s -70
  (the 2006 and 2024 surveys' kerbs have the same course);
- the kerbs: west 0.7 m inside the west row (the survey's kerb 1.0 - 1.3 m inside it; the photo of 2004 has the trunks
  just behind the kerb), east 0.5 m inside the east row where its bright edge is not read directly: a carriageway of
  about 7 m (the 2006 survey 6.8 - 7.3 m, the 2024 one 7.0 - 7.4 m).  The game had OSM's line, 6 m wide;
- the road's height (each frame pair by itself, windows of 1.25 and 2 m half-width, correlation over 0.7; the pairs
  mostly within 0.45 m; four spot heights of the 1:5000 survey on the road within -0.14 .. +0.07 m): the game's ground
  stood 0.5 - 1.6 m over it north of s 70 and south of s 150;
- a walk behind the east row from s 77 to 104 (bright in the three winter frames, d +5.4 .. +6.5);
- cars along the west kerb from s 165 to 240 in the 1996 winter frames (CARS: those at one place in all three).

The trees (백합나무: the leaves of the two photos of 2004).  BASES_1996: the twelve read off the three 1996 winter frames
(a dark point at one place in all three, the trunk's image lying opposite ways in 27/15 and 27/17, the radial crown
over it in 27/16).  BASES_MORE: where two sources that do not depend on each other have a trunk at one place within
about 1 m -- the 1996 frames' trunk images in two frames (too weak by themselves) and the Kakao skyview's winter aerial
of 2008 (0.4 - 0.5 m sharp; a dark point and the trunk lying away from it; registered on the six clearest of the
twelve, the east kerb line then within 0.2 m of 1996's) -- and, in the east row from s 121 to 177, the 2008 row itself
(every 4.4 - 6.6 m): the 1996 frames cannot see single trunks there (evergreens and shade), but the July 1997 crowns
cover that stretch without a break and the roadview of August 2008 has trunks of one girth (0.4 - 0.55 m) every 3.5 -
5 m between the kerb and the fence.  Each stands at its own place (the road is laid where the scans have it now); one
that the read kerb would leave on the carriageway steps 0.5 m behind it.
"""
import math
import random

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

import datum

# OSM's line of the road, north to south (build_campus.py's service road through (425.9, 199.7))
OLD = [(394.1, 270.4), (406.0, 259.2), (410.6, 253.4), (415.5, 243.1), (425.9, 199.7), (444.9, 154.5), (465.7, 91.9),
       (468.1, 84.9), (476.4, 60.5), (488.7, 22.8), (489.6, 20.5), (510.4, -30.6), (534.8, -52.0)]
OLD_LINE = LineString(OLD)
S0 = OLD_LINE.project(Point(425.9, 199.7))
OLD_W = 6.0
# (s, west kerb d, east kerb d) as read, s -70 .. 250: the summer frames' asphalt edges (s -70 .. -40, 250), the rows of
# 1996 (west row + 1.1 m, east row - 0.5 m: s -35 .. 90), the bright edges of 1996 and 1998 (east, s 100 .. 230)
KERBS = [(-70, -3.80, 4.35), (-65, -3.50, 4.70), (-60, -3.20, 5.06), (-55, -2.90, 5.41), (-50, -2.60, 5.20), (-45, -2.30, 4.59),
         (-40, -2.05, 5.25), (-35, -1.49, 5.30), (-30, -0.91, 5.70), (-25, -0.56, 6.11), (-20, -0.07, 6.45), (-15, 0.41, 7.10),
         (-10, 0.78, 7.16), (-5, 1.35, 8.12), (0, 1.58, 8.35), (5, 1.28, 7.87), (10, 1.15, 7.53), (15, 0.74, 7.23),
         (20, 0.31, 6.83), (25, 0.22, 6.30), (30, -0.46, 5.96), (35, -1.10, 5.63), (40, -1.26, 5.41), (45, -1.59, 5.16),
         (50, -1.84, 4.91), (55, -1.85, 4.66), (60, -1.90, 4.55), (70, -1.92, 4.57), (80, -1.86, 4.32), (90, -1.99, 4.56),
         (100, -2.06, 4.80), (110, -1.99, 4.95), (120, -2.00, 4.70), (130, -2.03, 4.60), (140, -2.25, 4.45), (150, -2.12, 4.15),
         (160, -2.14, 4.75), (170, -1.90, 4.75), (180, -2.00, 4.90), (190, -3.00, 4.40), (200, -2.70, 4.60), (210, -2.60, 4.00),
         (220, -2.00, 4.00), (230, -2.30, 4.50), (240, -2.60, 4.50), (250, -2.95, 4.30)]
WEST_IN = (-35.0, 180.0, 0.4)            # (from s, to s: the west kerb 0.4 m further west there: 0.7 m inside the row)
# the road's height along its 1997 middle (s, 해발): the pairs' medians (s 180 and 230 between their neighbours, where
# parked cars leave no pair), then smoothed 1-2-1 (profile()); s 260 - 277.5 on the way down to 36.9 m at s 280
ROAD_Z = [(-80, 66.95), (-70, 65.72), (-60, 64.46), (-50, 63.44), (-40, 62.93), (-30, 62.57), (-20, 62.05), (-10, 61.69),
          (0, 61.28), (10, 60.95), (20, 60.34), (30, 59.79), (40, 59.32), (50, 58.87), (60, 58.06), (70, 57.45), (80, 56.55),
          (90, 55.80), (100, 54.94), (110, 54.16), (120, 53.16), (130, 52.14), (140, 51.07), (150, 49.82), (160, 48.77),
          (170, 47.10), (180, 46.30), (190, 45.72), (200, 44.10), (210, 43.03), (220, 42.02), (230, 40.95), (240, 39.89),
          (250, 39.33), (260, 38.52), (270, 37.71), (277.5, 37.1)]
VERGE = 1.5                              # (m past the kerbs at the road's level)
RING = 10.0                              # (m past that eased into the ground as it stands)
EAST_WALK = (77.0, 104.0, 5.2, 6.5)      # (s from, to, d from, to: the walk behind the east row)
# (x, y, side): 1996년 겨울 세 장으로 읽은 밑동(게임 좌표, m), 'E' 는 한국어학당 쪽, 'W' 는 청송대 쪽
BASES_1996 = (
    (458.98, 127.67, 'E'), (460.56, 123.24, 'E'), (461.91, 119.48, 'E'), (463.42, 114.92, 'E'),
    (465.13, 109.80, 'E'), (466.83, 105.31, 'E'), (469.92, 95.37, 'E'),
    (466.82, 79.04, 'W'), (471.55, 64.81, 'W'), (479.46, 41.13, 'W'), (481.01, 36.69, 'W'), (503.31, -18.76, 'W'),
)
# (x, y, side): 1996년 두 장의 줄기 상과 2008년 겨울 스카이뷰가 함께 가리키는 밑동, 동쪽 s 121 ~ 177 은 2008년의 줄
BASES_MORE = (
    (445.30, 170.18, 'E'), (446.88, 165.42, 'E'),                                           # s 35 · 40
    (472.62, 87.90, 'E'), (474.58, 81.57, 'E'), (476.23, 76.33, 'E'), (478.13, 71.90, 'E'), (479.33, 67.24, 'E'),
    (482.21, 58.02, 'E'), (483.30, 53.54, 'E'), (485.25, 48.49, 'E'), (487.07, 43.72, 'E'), (488.07, 39.42, 'E'),
    (489.99, 34.78, 'E'),                                                                   # s 121 .. 177
    (445.23, 144.00, 'W'), (446.52, 139.79, 'W'), (454.47, 116.51, 'W'), (457.58, 107.01, 'W'), (462.33, 92.36, 'W'),
    (463.98, 88.03, 'W'), (465.50, 83.69, 'W'), (468.73, 72.96, 'W'), (476.13, 51.02, 'W'), (482.46, 32.26, 'W'),
    (485.41, 22.59, 'W'),                                                                   # s 59 .. 187
)
BASES = BASES_1996 + BASES_MORE
SPECIES = 'tulip'                    # blender/vegetation.py SPECIES['tulip'], tools/make_textures.py leaf_tulip*
BEHIND = 0.5                         # 읽은 연석이 줄기를 차도에 두면 연석 뒤로 이만큼(m)
# 1996년 겨울 세 장에서 같은 자리인 차(차 지붕 높이로 다시 투영): (x, y, 방향 °, 크기, 색). 서쪽 연석에 붙은 한 줄
# (27/17 에서 흐린 (488.88, 19.23)의 차는 앞 차와 4.4 m 라 게임의 차 길이로는 겹쳐서 뺌)
CARS = [(482.43, 38.30, -71.9, 'm', 'w'), (485.75, 28.12, -71.9, 's', 'w'), (487.34, 23.27, -71.7, 'm', 'w'),
        (491.08, 13.81, -67.9, 's', 'w'), (494.61, 5.15, -67.9, 'm', 'w'),
        (500.70, -9.81, -67.9, 'm', 'w'), (504.48, -19.12, -67.9, 'v', 'w')]


def at(s, d=0.0):
    """(x, y) of (s, d) in OSM's line's frame"""
    a = S0 + s
    p, q0, q1 = OLD_LINE.interpolate(a), OLD_LINE.interpolate(a - 0.5), OLD_LINE.interpolate(a + 0.5)
    tx, ty = q1.x - q0.x, q1.y - q0.y
    n = math.hypot(tx, ty)
    return p.x - ty / n * d, p.y + tx / n * d


def kerbs():
    """the two kerbs (west, east) and the middle line, lists of (x, y) from s -70 to 250"""
    w, e, m = [], [], []
    for s, wd, ed in KERBS:
        if WEST_IN[0] <= s <= WEST_IN[1]:
            wd -= WEST_IN[2]
        w.append(at(s, wd))
        e.append(at(s, ed))
        m.append(at(s, (wd + ed) / 2))
    return w, e, m


def middle():
    """the 1997 middle line from OSM's line at s -80 through the read stretch and on along OSM's line to s 277.5, and the
    (distance along it, 해발) of the road's profile"""
    m = kerbs()[2]
    pts = [OLD[0]] + m + [at(260.0), at(270.0), at(277.5)]          # (OLD[0]: s -79.8, where OSM's line and the road are one)
    line = LineString(pts)
    z = profile()
    stations = [OLD[0]] + [m[[k[0] for k in KERBS].index(s)] for s, _ in ROAD_Z if -70 <= s <= 250] + [at(260.0), at(270.0), at(277.5)]
    assert len(stations) == len(z)
    return line, np.array([line.project(Point(*q)) for q in stations]), np.array(z)


def profile():
    """ROAD_Z's heights smoothed 1-2-1 (its ends as read)"""
    z = [v for _, v in ROAD_Z]
    return [z[0]] + [round(0.25 * z[i - 1] + 0.5 * z[i] + 0.25 * z[i + 1], 2) for i in range(1, len(z) - 1)] + [z[-1]]


def carriageway():
    w, e, _ = kerbs()
    return Polygon(w + e[::-1]).buffer(0)


def strips():
    """(OSM's asphalt off the 1997 carriageway, to be taken up; the 1997 carriageway; the walk behind the east row)"""
    new = carriageway()
    a, b = S0 - 68.0, S0 + 238.0
    old = shapely.ops.substring(OLD_LINE, a, b).buffer(OLD_W / 2 + 0.6, cap_style='flat').difference(new.buffer(0.05))
    s0, s1, d0, d1 = EAST_WALK
    ss = np.arange(s0, s1 + 0.01, 3.0)
    walk = Polygon([at(s, d0) for s in ss] + [at(s, d1) for s in ss[::-1]])
    return old, new, walk


def repath(paths):
    """The road's entry in a list of paths ({kind, w, pts}) follows the 1997 middle line from s 250 to -70 (the map,
    the crowd's walks); its ends stay.  Returns how many entries were changed"""
    m = kerbs()[2]
    n = 0
    for p in paths:
        pts = [tuple(q[:2]) for q in p['pts']]
        if p.get('kind') != 'service' or (425.9, 199.7) not in pts or (510.4, -30.6) not in pts:
            continue
        i, j = sorted((pts.index((510.4, -30.6)), pts.index((406.0, 259.2))))
        mid = [[round(x, 1), round(y, 1)] for x, y in (m[::-1] if pts.index((510.4, -30.6)) < pts.index((406.0, 259.2)) else m)]
        p['pts'] = [list(q) for q in p['pts'][:i]] + mid + [list(q) for q in p['pts'][j + 1:]]
        p['w'] = 7
        n += 1
    return n


def grade(Hn, X, Y, FIXED, keep):
    """The road at its profile across the carriageway and VERGE m past its kerbs (level across; nodes an earlier rule
    laid there go to it too: the road is read by itself now).  Round it, over RING m, the ground keeps its relief and
    takes a falling share of what the road beside it went down or up by (the difference between the profile and the
    ground along the middle line, smoothed over 30 m), but for nodes an earlier rule (FIXED) holds.  Nodes at a hall's
    foot (keep) stay.  Returns the nodes set or eased (to be FIXED) and a summary"""
    H0 = Hn.copy()
    T = datum.tilt(X, Y)
    line, cum, z = middle()
    box = line.buffer(RING + 12.0).bounds
    m = (X >= box[0]) & (X <= box[2]) & (Y >= box[1]) & (Y <= box[3])
    P = shapely.points(X[m], Y[m])
    s = shapely.line_locate_point(line, P)
    d = shapely.distance(line, P)
    # what the road goes by along its middle line (the ground there before, bilinear on the grid)
    x0, y0, st = float(X[0, 0]), float(Y[0, 0]), float(X[0, 1] - X[0, 0])
    ss = np.arange(0.0, line.length + 0.01, 5.0)

    def ground(q):
        fx, fy = (q.x - x0) / st, (q.y - y0) / st
        i, j = int(fx), int(fy)
        u, v = fx - i, fy - j
        G = H0 - T
        return G[j, i] * (1 - u) * (1 - v) + G[j, i + 1] * u * (1 - v) + G[j + 1, i] * (1 - u) * v + G[j + 1, i + 1] * u * v
    dz = np.array([np.interp(a, cum, z) - ground(line.interpolate(a)) for a in ss])
    dz = np.convolve(np.pad(dz, 3, mode='edge'), np.ones(7) / 7.0, mode='valid')
    dz[:2] *= (0.0, 0.5)                                       # (the two ends meet the ground as it stands)
    dz[-2:] *= (0.5, 0.0)
    road = carriageway().buffer(VERGE).union(shapely.ops.substring(line, cum[-4], cum[-1]).buffer(3.5 + VERGE, cap_style='flat'))
    inside = (s > 1.0) & (s < line.length - 1.0)
    on = np.zeros(X.shape, bool)
    on[m] = shapely.contains_xy(road, X[m], Y[m]) & inside
    held = on & keep
    on &= ~keep
    zz = np.zeros(X.shape)
    zz[m] = np.interp(s, cum, z)
    Hn[on] = (zz + T)[on]
    d0 = 3.5 + VERGE
    share = np.zeros(X.shape)
    share[m] = np.clip(1.0 - (d - d0) / RING, 0.0, 1.0) * np.interp(s, ss, dz)
    ring = np.zeros(X.shape, bool)
    ring[m] = (d <= d0 + RING)
    ring &= ~on & ~keep & ~FIXED
    Hn[ring] += share[ring]
    dd = Hn - H0
    return on | ring, dict(road=int(on.sum()), over_fixed=int((on & FIXED).sum()), held=int(held.sum()), ring=int(ring.sum()),
                           moved=(int((np.abs(dd) > 0.05).sum()), round(float(dd.min()), 2), round(float(dd.max()), 2)))


def clear(items, pad=0.5):
    """List items ([kind, x, y, ...]) standing on the 1997 carriageway step off it across the nearer kerb, 0.8 m past
    it, in their places in the list.  Returns those moved (kind, x, y before)"""
    new = carriageway()
    zone = new.buffer(pad)
    edge = new.buffer(pad + 0.8).exterior
    moved = []
    for it in items:
        q = Point(it[1], it[2])
        if not zone.contains(q):
            continue
        p = edge.interpolate(edge.project(q))
        moved.append((it[0], it[1], it[2]))
        it[1], it[2] = round(p.x, 2), round(p.y, 2)
    return moved


def trees(old_trees=()):
    """campus.json trees 항목들: (BASES_1996 의 열둘, BASES_MORE 의 나무, 가까운 옛 나무). 열둘은 나무 목록에서 전에 있던
    자리에, 나머지는 목록의 맨 끝에 붙인다(웹은 목록 차례로 모델을 고름).
    old_trees 에서 새 줄기 1.5 m 안의 나무가 있으면 알린다(옮기지 않음)"""
    new = carriageway()
    edge = new.buffer(BEHIND).exterior
    rnd = random.Random(231)
    out = []
    for x, y, side in BASES:
        q = Point(x, y)
        if new.buffer(BEHIND - 0.05).contains(q):
            p = edge.interpolate(edge.project(q))
            x, y = p.x, p.y
        out.append([SPECIES, round(x, 2), round(y, 2), round(rnd.uniform(0.92, 1.06), 2), round(rnd.uniform(0, 6.28), 2)])
    near = [(t[0], t[1], t[2], round(math.dist(t[1:3], o[1:3]), 2)) for t in out for o in old_trees
            if math.dist(t[1:3], o[1:3]) < 1.5]
    n = len(BASES_1996)
    return out[:n], out[n:], near
