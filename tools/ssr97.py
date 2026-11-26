"""성산로 동쪽 끝 너머 · 육교 · 경의선 철둑의 단면 · 신촌역 구내 (#189; reference/고증/4.8_정문_밖.md 「1997년 7월 수직
항공사진으로 다시 본 것」, 4.8.2 「x 300 동쪽」).  tools/build_campus.py 와 tools/gate_town.py 가 부른다.

    took = ssr97.ext_bed(Hn, X, Y, keep)        # 게임의 성산로 끝(x 346) 너머 북동쪽 길의 바닥: 심기가 끝난 뒤, 철둑 · 성산로를 놓은 뒤
    ssr97.bank_1997(secs, sample)                 # gate_town.bank_fix 의 단면에 철둑 남쪽 흰 옹벽 · 신촌역 구내의 넓은 윗면을
    ssr97.layout(town, extra, road, lanes, secs)  # gate_town.layout 끝: 그 길의 칠 · 연석 · 차로 · 막, 옹벽 위 벽, 구내의 선로 ·
                                                  # 승강장, 육교 둘, 그 자리에 들어선 동네 집은 뺌

Frame: campus metres, x east, y north.  Nothing here draws from any random stream.  Heights written here are above sea
level (해발); datum.up takes them to the working datum the build lays the ground on.

The 1997-07-28 scans (자료 Q: 27/17 · 27/18 · 26/16, and 27/19 · 27/16 where they reach; tools/aerial97.py,
aerial_resect.py) and the winter ones of 1996 (27/17 · 27/18, tools/aerial_more.py):

- 성산로 past the game's end (x 346): straight on north-east at 44.6 deg, its middle line (EXT_C0, EXT_D) a continuous
  bright line in both frames (within 0.2 m, 33 windows of 10 m), dashed lines 3.0 and 6.2 m either side of it, the
  north kerb 12.4 m out (13.2 m within 25 m of the game's end, where it meets the kerb of 2.10's KN97_UV), the south one
  11.5 m (under the street trees: 10.5 - 12.5 m).  Outside the second dashed line on either side a wide band without a
  line (north 6.4 m, south 5 m): the buses stand and run in it.  The road's surface every 10 m on six points across
  (EXT_Z: up to seven pairs of frames, spread 0.02 - 0.16 m): 29.3 m at the game's end, 2.7 % up to 37.8 m at s 340.
- Two footbridges over it (FOOTBRIDGES): the deck from sidewalk to sidewalk, at each end a flight down each way along
  the sidewalk (an H in plan); the decks' tops 34.0 m (four pairs, 33.6 - 34.1) and 41.2 m.
- The 경의선's south side west of the bridge: a white wall on the bank's edge, x -217 .. -110, 8.3 m off the south
  track east of a 4 m jog at x -155.5, 13 m west of it (WALL97).  Its top 37.0 - 37.3 m (27/17 x 27/18 and 26/16 x
  27/18, within 0.1 m), 3.4 m over the bed and 4 m over the bank's surface behind it (33.0 - 33.1 m), its south face
  down to the town: a retaining wall with a wall standing on it, panelled (the jog's face in 27/17); east of the jog
  a grass bank under it down to a lane wall (the 1996 winter pair: BANK97_*).  In the winter
  frames of 1996 the same line is at 32.6 - 34.0 m (three pairs) and in 1998-10 at 36.9 - 37.0 m: the upper wall (a
  noise wall) went up between 1996-12 and 1997-07.  East of the bridge the south slope is trees, no wall.
- 신촌역's yard, x 140 .. 540: a broad top at the rails' height, from o +34 (y -430) to o -25 (YARD_N, YARD_S: o north
  of the rails' middle line), tracks besides the two main ones (YARD_TRACKS), two island platforms (YARD_PLATFORMS,
  their tops 0.5 m over the bed: 34.4 m, three pairs).
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

import datum

# ----------------------------------------------------------------------------- 성산로, past the game's end
EXT_C0 = (318.56, -284.78)          # the 1997 middle line's start (strip s 0: the game's road at x 316.8)
EXT_D = (0.71218, 0.70199)          # its way (44.6 deg), straight
EXT_N = (-EXT_D[1], EXT_D[0])        # left of it: north-west
EXT_S0, EXT_S1 = 16.1, 425.0         # from where the game's paint ends (x 330) to the end drawn (x 621: the
#                                      ground map's east edge is x 640, build_campus.py SPLAT)
EXT_IN = (16.1, 56.0)                # the game's section eased into the 1997 one
# (s, the road's surface, 해발): the scans, s 300 (on the second footbridge's deck) left out
EXT_Z = [(10, 29.26), (20, 29.41), (30, 29.57), (40, 29.77), (50, 29.94), (60, 30.12), (70, 30.30), (80, 30.47), (90, 30.67),
         (100, 30.85), (110, 31.08), (120, 31.41), (130, 31.68), (140, 31.91), (150, 32.17), (160, 32.57), (170, 32.80),
         (180, 33.10), (190, 33.40), (200, 33.62), (210, 34.02), (220, 34.32), (230, 34.54), (240, 34.89), (250, 35.22),
         (260, 35.41), (270, 35.72), (280, 35.93), (290, 36.35), (310, 36.89), (320, 37.17), (330, 37.53), (340, 37.84),
         (350, 38.06), (360, 38.39), (370, 38.71), (380, 39.10), (390, 39.44), (400, 39.79), (410, 40.11), (420, 40.47)]
KERB_N = [(16.1, 12.75), (25.0, 13.2), (45.0, 12.4), (400.0, 12.4)]      # the north kerb's offset (KN97_UV's at x 330 first)
KERB_S97 = -11.5
LINES97 = dict(yellow=(-0.12, 0.12), north=(2.95, 6.05), south=(-3.05, -6.35))
WALK = 4.0                           # the sidewalks (the kerb to the street trees' back)
LANES97 = 5                          # the game's lanes a way, drawn in to the 1997 width (as along 의료원: 2.2 - 2.4 m)
BED_EASE = 8.0


def ext_xy(s, o):
    s, o = np.asarray(s, float), np.asarray(o, float)
    return EXT_C0[0] + s * EXT_D[0] + o * EXT_N[0], EXT_C0[1] + s * EXT_D[1] + o * EXT_N[1]


def ext_so(x, y):
    dx, dy = np.asarray(x, float) - EXT_C0[0], np.asarray(y, float) - EXT_C0[1]
    return dx * EXT_D[0] + dy * EXT_D[1], dx * EXT_N[0] + dy * EXT_N[1]


def _sm(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ext_z(s):
    """the road's surface (해발) at s"""
    return np.interp(s, *zip(*EXT_Z))


def kerb_n(s):
    return np.interp(s, *zip(*KERB_N))


def ext_walk_poly(s0, s1, side, step=4.0):
    ss = np.arange(s0, s1 + 0.01, step)
    if side > 0:
        a, b = kerb_n(ss), kerb_n(ss) + WALK
    else:
        a, b = np.full(len(ss), KERB_S97), np.full(len(ss), KERB_S97 - WALK)
    return Polygon([tuple(map(float, ext_xy(s, o))) for s, o in zip(ss, a)] + [tuple(map(float, ext_xy(s, o))) for s, o in zip(ss[::-1], b[::-1])]).buffer(0)


def ext_bed(Hn, X, Y, keep):
    """The road's bed past the game's end on the 1997 scans (EXT_Z): level across from kerb to kerb, the sidewalks
    0.12 m up, eased over BED_EASE m into the ground beyond.  keep: nodes not to move (the halls' feet).  Returns the
    nodes it laid (whole weight)."""
    s, o = ext_so(X, Y)
    on = (s > EXT_S0 - 6.0) & (s < EXT_S1 + 12.0)
    zr = datum.tilt(X, Y) + ext_z(np.clip(s, EXT_Z[0][0], EXT_Z[-1][0]))
    zs = np.where((o > kerb_n(s)) | (o < KERB_S97), zr + 0.12, zr)
    lo, hi = KERB_S97 - WALK, kerb_n(s) + WALK
    d = np.maximum(lo - o, o - hi)
    w = 1.0 - _sm(d / BED_EASE)
    # (into the game's own road bed at the start, out past the end)
    w = w * _sm((s - (EXT_S0 - 6.0)) / 10.0) * (1.0 - _sm((s - EXT_S1) / 12.0))
    w = np.where(on & ~keep, w, 0.0)
    Hn[:] = Hn * (1 - w) + zs * w
    return w > 0.999


# ----------------------------------------------------------------------------- 육교 (footbridges)
# the first over the game's road (along 의료원 종합관's car park: u 27 - 33 of 2.10's frame), the second over the run
# on north-east (s 292.8 - 298.5); per bridge: the deck's two ends (its middle line), its width, the deck's top (해발),
# and the flights: along the sidewalk from each end, [foot (x, y), head (x, y)] with the head at the deck's top
_FB1_A, _FB1_B = (258.7, -323.6), (280.2, -345.1)


def _fb2():
    s0 = 295.6
    a = tuple(map(float, ext_xy(s0, 13.8)))
    b = tuple(map(float, ext_xy(s0, -12.6)))
    fl = []
    for o in (14.6, -13.4):
        fl.append([tuple(map(float, ext_xy(s0 - 13.0, o))), tuple(map(float, ext_xy(s0 - 2.4, o)))])
        fl.append([tuple(map(float, ext_xy(s0 + 12.5, o))), tuple(map(float, ext_xy(s0 + 2.4, o)))])
    return dict(a=a, b=b, w=3.6, top=41.2, flights=fl)


def _fb1():
    # (2.10's frame: o (150, -250), u along 43 deg; the north flights on the sidewalk v -125.2, from the landing at
    # u 27.5 / 31.1 down to u 17 and u 41.5; the south ones v -160, u 28.3 -> 17.7 and 32.5 -> 41)
    a_ = math.radians(43.0)
    uv = lambda u, v: (round(150.0 + u * math.cos(a_) - v * math.sin(a_), 2), round(-250.0 + u * math.sin(a_) + v * math.cos(a_), 2))
    fl = [[uv(17.0, -125.2), uv(27.5, -125.2)], [uv(41.5, -125.2), uv(31.1, -125.2)],
          [uv(17.7, -160.0), uv(28.3, -160.0)], [uv(41.0, -160.0), uv(32.5, -160.0)]]
    return dict(a=_FB1_A, b=_FB1_B, w=3.5, top=34.0, flights=fl)


FOOTBRIDGES = [_fb1(), _fb2()]
FB_FLIGHT_W = 2.2
FB_DEEP = 0.9                        # the deck under its top


def footbridge_polys(fb, pad=0.0):
    """the deck's landings and the flights in plan (what stands on the sidewalks and the town)"""
    a, b = np.array(fb['a']), np.array(fb['b'])
    out = []
    for p, q in fb['flights']:
        out.append(LineString([p, q]).buffer(FB_FLIGHT_W / 2 + pad, cap_style='flat'))
        out.append(Point(*q).buffer(FB_FLIGHT_W / 2 + pad))
    t = (b - a) / np.linalg.norm(b - a)
    n = np.array([-t[1], t[0]])
    for e in (a, b):
        out.append(Polygon([tuple(e + n * fb['w'] / 2 + t * 1.5), tuple(e - n * fb['w'] / 2 + t * 1.5),
                            tuple(e - n * fb['w'] / 2 - t * 1.5), tuple(e + n * fb['w'] / 2 - t * 1.5)]).buffer(pad))
    return unary_union(out)


# ----------------------------------------------------------------------------- 철둑 (the rails' bank)
# the wall's line (west -> east, the jog at x -155.5) and its top (해발); the bank's surface behind it under the bed's top
WALL97 = [(-217.0, -505.4), (-155.5, -503.4), (-155.5, -499.4), (-110.0, -497.8)]
WALL97_TOP = [37.0, 37.0, 37.2, 37.2]
WALL97_BENCH = 0.7
# east of the jog the wall's foot is no retaining wall down to the town but a grass bank (고증 4.8.4 「벽 남쪽의
# 비탈」): the leafless 1996-11/12 pair 26/16 x 26/17 (24 points at 0.71 - 0.99, x -115 .. -145) falls from 32.4 m 2 - 4 m
# out of the wall's line to 26.5 m 10 - 12 m out (17 points on the plane below: median +0.5 m, rms 1.1 m, a little
# fuller up top), the 1998-10 pair the same where no crowns stand; the 2008-08 and 2010-10 roadview the same, a grass
# bank down to a low wall over the lane (연세로13길).  (x0, x1) along the wall, how far out its toe is, its height there
# (해발); the lane wall down from it to the town.  West of the jog (x -165 .. -210: 29 - 30 m out to 9 m, roofs or a
# bank) it stays a wall down to the ground
BANK97_X = (-150.0, -117.0)
BANK97_D, BANK97_TOE = 12.0, 26.4
BANK97_DROP = 0.1                    # the bank's top at the wall's line under the bench
# 신촌역's yard: how far the top reaches north (+) and south (-) of the rails' middle line, (x, o)
YARD_N = [(285.0, 0.0), (295.0, 12.6), (330.0, 31.0), (360.0, 34.0), (480.0, 34.0), (520.0, 30.0), (555.0, 12.6), (565.0, 0.0)]
YARD_S = [(132.0, 0.0), (150.0, -22.0), (160.0, -25.0), (360.0, -25.0), (400.0, -21.0), (440.0, -18.0), (500.0, -18.0),
          (540.0, -14.0), (560.0, 0.0)]
# the tracks besides the two main ones (x0, x1, o) and the island platforms (x0, x1, o0, o1), their tops over the bed
YARD_TRACKS = [(250.0, 505.0, 11.0), (125.0, 500.0, 2.8), (150.0, 520.0, -11.6), (160.0, 375.0, -22.0)]
YARD_PLATFORMS = [(125.0, 493.0, 0.9, -5.0), (158.0, 325.0, -13.4, -19.4)]
PLATFORM_UP = 0.5
# the level crossing from the station's back over the side track and the south main line to the first island platform
# (고증 4.8.4 「역사에서 승강장으로 건너는 길」): x 414.4 - 419.4 in the leafless 1996 frames 27/17 · 27/18 (a bright strip),
# 1997-07 27/17 · 27/18 · 27/19 (the platform's south edge broken x 414.75 - 419.75 in all three, the strip's edges over
# the tracks) and 1999-05 27/16 · 27/17 (painted round): (x0, x1, the platform it reaches), its top over the bed, how
# far the ramp cuts into the platform, how far the ramp down to the forecourt runs out of the yard's south edge
YARD_CROSSING = (414.4, 419.4, 0)
CROSS_UP, CROSS_RAMP, CROSS_FORE = 0.06, 2.0, 2.5
# the wagons standing on the north siding (o +11) on 1997-07-28 (x0, x1 of each body): roofs 3.7 m over the bed (38.0 m,
# 27/17 and 27/18 within 0.3 m on that plane), light grey but the two at x 437 - 464 darker; a covered wagon stands there
# in 1996 too (서울연구원 52044 · 52045: dark brown, from the bridge in 이화여대).  The yard took goods till 2005 (무연탄
# from 1971)
YARD_WAGONS = [(378.0, 391.0), (392.0, 405.0), (406.0, 419.0), (437.0, 450.0), (451.0, 464.0), (465.0, 478.0), (479.0, 492.0)]
WAGON_O, WAGON_TOP = 11.0, 3.7
# the rest of the yard on 1997-07-28 (고증 4.8.4 「신촌역 구내」): (x0, x1, y0, y1) at the height of its top, where 27/17,
# 27/18 and 26/16 lie on each other, and its top (해발; drawn from the game's yard surface or platform top up to it)
# - a low shed north of the siding: a gridded roof 38.0 m (37.6 - 38.2, three points, 27/17 x 27/18 x 27/19 at 0.77 - 0.87),
#   the yard 34.3 m at its east foot
# - a flat-topped heap north-west of it: a white top at 38.2 - 38.9 m (six points, 0.6 - 0.93) strewn with black rings
#   (tyres weighing a cover down, as on the covered heaps of the 1996 photos 52044 · 52045 · 52074 · 52090), the yard
#   35.0 m west of it
# - four small white roofs on the island platform (37.0 - 37.2 m, 0.80 - 0.92): 2.65 m over the platform's top (34.45 m)
YARD_SHED = (417.0, 430.0, -450.0, -436.5, 38.0)
YARD_HEAP = (367.0, 402.0, -451.5, -441.5, 38.6)
YARD_SHELTERS = [(375.5, 380.5), (382.5, 387.5), (390.0, 395.0), (397.0, 402.5)]
SHELTER_Y, SHELTER_TOP = (-470.0, -466.3), 37.1


def _yard_things(secs):
    """[kind, cx, cy, L, W, ang, base, h]: base = the yard's surface (the section's top less 0.05) or the platform's top
    (the top + PLATFORM_UP) at the section nearest cx, working datum like the sections; h from it to the measured top"""
    out = []

    def one(kind, x0, x1, y0, y1, top, up):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        r = min(secs, key=lambda s: abs(s[0] - cx))
        ang = math.atan2(-r[2], r[3])
        out.append([kind, round(cx, 2), round(cy, 2), round(x1 - x0, 2), round(y1 - y0, 2), round(ang, 4),
                    round(r[11] + up, 2), round(datum.up(cx, cy, top) - (r[11] + up), 2)])
    one('shed', *YARD_SHED, -0.05)
    one('heap', *YARD_HEAP, -0.05)
    for x0, x1 in YARD_SHELTERS:
        one('shelter', x0, x1, *SHELTER_Y, SHELTER_TOP, PLATFORM_UP)
    return out


def is_flat(x, side, hw):
    """whether bank_1997 has made that side of the section at x level to a wall (the white wall's stretch on the
    south, the yard): what gate_town.layout plants on the slope then stands past its foot"""
    if side < 0 and WALL97[0][0] <= x <= WALL97[-1][0]:
        return True
    return abs(_o_at(YARD_N if side > 0 else YARD_S, x)) > hw + 0.5


def trees_off(trees, step=0.4):
    """trees standing on a footbridge's flight or landing: along the flight out past it and 3 m clear of the trees
    round it, in their places in the list.  Returns the moved"""
    moved = []
    for fb in FOOTBRIDGES:
        g = footbridge_polys(fb, 0.6)
        for t in trees:
            if not g.contains(Point(t[1], t[2])):
                continue
            p, q = min(fb['flights'], key=lambda f: LineString(f).distance(Point(t[1], t[2])))
            d = np.array(p, float) - np.array(q, float)
            d /= np.linalg.norm(d)
            x, y = t[1], t[2]
            others = [(o[1], o[2]) for o in trees if o is not t and abs(o[1] - x) < 40 and abs(o[2] - y) < 40]
            for _ in range(120):
                clear = min((math.hypot(ox - x, oy - y) for ox, oy in others), default=99.0) >= 3.0
                if not g.contains(Point(x, y)) and clear:
                    break
                x, y = x + d[0] * step, y + d[1] * step
            moved.append((t[0], t[1], t[2], round(float(x), 2), round(float(y), 2)))
            t[1], t[2] = round(float(x), 2), round(float(y), 2)
    return moved


def _o_at(tab, x):
    xs, os_ = zip(*tab)
    return float(np.interp(x, xs, os_, left=0.0, right=0.0))


_BANK97 = []                         # bank_1997 -> rail_extras: [section, toe out of the wall's foot, its height, the lane's]


def bank_1997(secs, sample):
    """bank_fix's sections (rows [x, y, nx, ny, hw, dN, zN, wallN, dS, zS, wallS, top], in place): the south side west
    of the bridge on the white wall's line, its foot on the town's ground; 신촌역's yard level out to YARD_N / YARD_S,
    a wall down to the ground where it stands lower"""
    wl = LineString(WALL97)
    del _BANK97[:]
    for k, r in enumerate(secs):
        x, y, nx, ny, hw, top = r[0], r[1], r[2], r[3], r[4], r[11]
        p, n = np.array([x, y]), np.array([nx, ny])
        if WALL97[0][0] <= x <= WALL97[-1][0]:
            ray = LineString([tuple(p - n * hw), tuple(p - n * 40.0)])
            hit = ray.intersection(wl)
            if not hit.is_empty:
                q = hit if hit.geom_type == 'Point' else min(getattr(hit, 'geoms', [hit]), key=lambda g: g.distance(Point(*p)))
                ow = float(np.hypot(q.x - x, q.y - y))
                foot = p - n * (ow + 0.6)
                r[8], r[9], r[10] = round(max(0.5, ow - hw), 2), round(top - WALL97_BENCH, 2), round(float(sample(*foot)), 2)
                if BANK97_X[0] <= x <= BANK97_X[1]:          # (the grass bank below it: rail_extras bank97)
                    r[10] = round(top - WALL97_BENCH - BANK97_DROP, 2)
                    toe = p - n * (hw + r[8] + BANK97_D)
                    _BANK97.append([k, BANK97_D, datum.up(x, y, BANK97_TOE),
                                    round(float(sample(*(toe - n * 0.6))), 2)])
        for side, tab, i0 in ((1, YARD_N, 5), (-1, YARD_S, 8)):
            o = abs(_o_at(tab, x))
            if o <= hw + 0.5:
                continue
            e = p + n * side * (o + 0.6)
            g = float(sample(*e))
            r[i0], r[i0 + 1] = round(o - hw, 2), round(top - 0.05, 2)
            r[i0 + 2] = round(g, 2) if g < top - 0.35 else None
    for b in (_BANK97[:1] + _BANK97[-1:] if len(_BANK97) > 2 else []):   # (its ends run into the wall down to the town)
        b[1], b[2] = 0.5, round(secs[b[0]][10] - 0.3, 2)
    return secs


def _densify(pts, step):
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, int(math.ceil(L / step)))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(1, k + 1)]
    return out


def rail_extras(secs, rail_bed):
    """campus.json town.rail's additions: wall97 [[x, y, the bank's surface, the wall's top], ...] along the wall's line
    (heights on the working datum), yard: the tracks [[x0, x1, o]] and platforms [[x0, x1, o0, o1, up]] of 신촌역"""
    pts = []
    for (a, za), (b, zb) in zip(zip(WALL97[:-1], WALL97_TOP[:-1]), zip(WALL97[1:], WALL97_TOP[1:])):
        seg = _densify([a, b], 6.0)
        for k, q in enumerate(seg):
            if pts and k == 0:
                continue
            f = k / max(1, len(seg) - 1)
            bench = float(rail_bed(q[0])) - WALL97_BENCH
            pts.append([round(q[0], 2), round(q[1], 2), round(bench, 2), datum.up(q[0], q[1], za + (zb - za) * f)])
    return dict(wall97=pts, bank97=[list(b) for b in _BANK97],
                yard=dict(tracks=[list(t) for t in YARD_TRACKS],
                          platforms=[list(p) + [PLATFORM_UP] for p in YARD_PLATFORMS],
                          wagons=[[a, b, WAGON_O, WAGON_TOP] for a, b in YARD_WAGONS],
                          things=_yard_things(secs), crossings=[_crossing(secs)]))


def bank97_poly(secs):
    """the grass bank's plan (bank_1997's stretch): from the wall's foot out to its toe"""
    if len(_BANK97) < 2:
        return Polygon()
    foot, toe = [], []
    for k, d2, _, _ in _BANK97:
        r = secs[k]
        p, n = np.array(r[:2]), np.array(r[2:4])
        foot.append(tuple(p - n * (r[4] + r[8])))
        toe.append(tuple(p - n * (r[4] + r[8] + d2)))
    return Polygon(foot + toe[::-1]).buffer(0)


def _crossing(secs):
    """campus.json town.rail.yard.crossings: [x0, x1, the platform's south edge o, the yard's south edge o, the deck's
    top over the bed, the ramp into the platform, the ramp down out of the yard's edge]"""
    x0, x1, i = YARD_CROSSING
    r = min(secs, key=lambda s: abs(s[0] - (x0 + x1) / 2))
    return [x0, x1, YARD_PLATFORMS[i][3], -round(r[4] + r[8], 2), CROSS_UP, CROSS_RAMP, CROSS_FORE]


def yard_poly(secs):
    """the yard's top beyond the bank's own (what the town's houses give way to)"""
    out = []
    for side, tab, i0 in ((1, YARD_N, 5), (-1, YARD_S, 8)):
        cn, ci = [], []
        for r in secs:
            o = abs(_o_at(tab, r[0]))
            if o <= r[4] + 0.5:
                if len(cn) > 1:
                    out.append(Polygon(ci + cn[::-1]).buffer(0))
                cn, ci = [], []
                continue
            cn.append((r[0] + r[2] * side * (o + 0.3), r[1] + r[3] * side * (o + 0.3)))
            ci.append((r[0], r[1]))
        if len(cn) > 1:
            out.append(Polygon(ci + cn[::-1]).buffer(0))
    return unary_union(out)


# ----------------------------------------------------------------------------- the layout
def _lane_off(pts, s):
    """a lane's offset from the 1997 middle line where it crosses s (pts: the lane's polyline)"""
    ls = LineString(pts)
    g = LineString([tuple(map(float, ext_xy(s, -40.0))), tuple(map(float, ext_xy(s, 40.0)))])
    hit = ls.intersection(g)
    if hit.is_empty:
        return None
    q = hit if hit.geom_type == 'Point' else list(hit.geoms)[0]
    return float(ext_so(q.x, q.y)[1])


def layout(town, extra, road, sec_off, HW, MID, LANE_W, LANES, R2):
    """past the game's end: the 1997 lane paint (the game's own eased into it), kerbs, the lanes' run on (the game's
    five a way drawn in to the 1997 width), the asphalt and sidewalks, the walker's barrier along the north kerb; the
    footbridges.  town / extra: gate_town.layout's two dicts, added to in place"""
    ss = np.arange(EXT_S0, EXT_S1 + 0.01, 2.0)
    w = _sm((ss - EXT_IN[0]) / (EXT_IN[1] - EXT_IN[0]))
    # the game's lines where its paint ends (x 330), as offsets from the 1997 middle line
    sx = road.P[:, 0]
    k_end = int(np.nonzero(sx < 330.0)[0][-1])
    s_end = float(ext_so(*road.P[k_end])[0])

    def game_off(o):
        q = road.offn(o)[k_end]
        return float(ext_so(*q)[1])
    g_y = [game_off(-MID / 2 + 0.08), game_off(MID / 2 - 0.08)]
    g_n = [game_off(MID / 2 + LANE_W * k) for k in (1, 2)]
    g_s = [game_off(-(MID / 2 + LANE_W * k)) for k in (1, 2)]
    line = lambda o0, o1: R2([ext_xy(s, o0 + (o1 - o0) * f) for s, f in zip(ss, w)])
    for a, b in zip(g_y, LINES97['yellow']):
        town['paint'].append(dict(kind='yellow', w=0.15, pts=line(a, b)))
    for a, b in zip(g_n + g_s, LINES97['north'] + LINES97['south']):
        town['paint'].append(dict(kind='white_dash', w=0.12, pts=line(a, b)))
    # kerbs: from the game's (its runs end at x 330) into the 1997 ones
    g_kn, g_ks = float(ext_so(*road.offn(HW)[k_end])[1]), float(ext_so(*road.off(-HW)[k_end])[1])
    kn = kerb_n(ss)
    kn = np.where(ss < KERB_N[1][0], g_kn + (kn - g_kn) * _sm((ss - EXT_S0) / (KERB_N[1][0] - EXT_S0)), kn)
    ks = g_ks + (KERB_S97 - g_ks) * w
    fb_cut = unary_union([footbridge_polys(fb, 0.3) for fb in FOOTBRIDGES])

    def runs(pts):
        out, cur = [], []
        for q in pts:
            if fb_cut.contains(Point(*q)):
                if len(cur) > 1:
                    out.append(R2(cur))
                cur = []
            else:
                cur.append(q)
        if len(cur) > 1:
            out.append(R2(cur))
        return out
    town['kerbs'] += runs([ext_xy(s, o) for s, o in zip(ss, kn)]) + runs([ext_xy(s, o) for s, o in zip(ss, ks)])
    # the lanes: cut where the game's paint ends, on along the 1997 road
    ww = (kn.min() - 0.4) / LANES97
    we = (-(KERB_S97) - 0.4) / LANES97
    n_e = n_w = 0
    for ln in town['lanes']:
        if ln['kind'] not in ('car', 'bus') or ln.get('stops'):
            continue
        P = np.array(ln['pts'], float)
        east = P[-1][0] > P[0][0]
        k = n_e if east else n_w
        if east:
            n_e += 1
        else:
            n_w += 1
        kk = k % LANES
        # (the eastbound south of the middle, kk 0 next to it)
        o97 = -(kk + 0.5) * we if east else (kk + 0.5) * ww
        o0 = _lane_off(P, EXT_S0)
        if o0 is None:
            continue
        run = [ext_xy(s, o0 + (o97 - o0) * f) for s, f in zip(ss, w)]
        keep = [tuple(q) for q in P if ext_so(*q)[0] < EXT_S0 - 1.0]          # (in the lane's own order)
        ln['pts'] = R2(keep + run) if east else R2(run[::-1] + keep)
    # the asphalt, the sidewalks
    road_poly = Polygon([tuple(map(float, ext_xy(s, o))) for s, o in zip(ss, kn)] +
                        [tuple(map(float, ext_xy(s, o))) for s, o in zip(ss[::-1], ks[::-1])]).buffer(0)
    walks = ext_walk_poly(EXT_S0 + 4.0, EXT_S1, 1).union(ext_walk_poly(EXT_S0 + 30.0, EXT_S1, -1)).difference(road_poly)
    extra['paints']['asphalt'].append(road_poly)
    extra['paints']['pavers'].append(walks)
    # the walker's barrier along the north kerb (the carriageway's side), the limit with it
    bl = [ext_xy(s, o - 0.9) for s, o in zip(ss, kn)]
    bh = [ext_xy(s, o - 0.1) for s, o in zip(ss, kn)]
    for k in range(0, len(ss) - 2, 2):
        extra['colliders'].append(R2([bl[k], bl[k + 2], bh[k + 2], bh[k]]))
    x_last = max(q[0] for q in town['limit'])
    town['limit'] += R2([q for q in bh[::3] if q[0] > x_last + 1.0])
    extra['paths'].append(dict(kind='primary', w=24.0, pts=[[round(float(v), 1) for v in ext_xy(s, 0.0)] for s in ss[::6]]))
    # the footbridges: their flights and landings on the walks are walls to the walker
    town['footbridges'] = []
    for fb in FOOTBRIDGES:
        top = datum.up(*fb['a'], fb['top'])
        top_b = datum.up(*fb['b'], fb['top'])
        town['footbridges'].append(dict(a=list(fb['a']), b=list(fb['b']), w=fb['w'], top=[top, top_b], deep=FB_DEEP,
                                        flights=[[list(p), list(q)] for p, q in fb['flights']], fw=FB_FLIGHT_W))
        for p, q in fb['flights']:
            c = LineString([p, q]).buffer(FB_FLIGHT_W / 2, cap_style='flat')
            extra['colliders'].append(R2(list(c.exterior.coords)[:-1]))
    extra['ext_poly'] = road_poly.union(walks)
    return dict(lanes_e=n_e, lanes_w=n_w, road_m2=round(road_poly.area), walk_m2=round(walks.area))


def clear_blocks(blocks, n_skip, polys):
    """the town's houses (gate_town.layout blocks after the first n_skip) that stand on the yard, the footbridges or the
    road past the game's end: b[6] < 0 (blender/town.py still draws their random looks)"""
    from gate_town import _rect
    g = unary_union(polys)
    shapely.prepare(g)
    n = 0
    for b in blocks[n_skip:]:
        if b[6] > 0 and shapely.intersects(g, _rect(b).buffer(-0.2)):
            b[6] = -b[6]
            n += 1
    return n


# ----------------------------------------------------------------------------- the small flat-roofed hut
# at the head of 의료원 종합관 남동쪽 주차장's far row, by the first footbridge's north landing (2.10's frame: u 24.5 -
# 35.5, v -120.5 .. -116): its roof 33.8 - 34.15 m in three pairs of 1997 and one of 1996, the car park 31.1 m (2.10)
HUT_ID = 990090
HUT_UV = (24.5, 35.5, -120.5, -116.0)
HUT_ROOF, HUT_FLOOR, HUT_COPING = 34.0, 31.1, 0.3


def hut():
    """for the halls' end (blender/build.py draws each hall's looks in its order)"""
    a_ = math.radians(43.0)
    uv = lambda u, v: (round(150.0 + u * math.cos(a_) - v * math.sin(a_), 2), round(-250.0 + u * math.sin(a_) + v * math.cos(a_), 2))
    u0, u1, v0, v1 = HUT_UV
    fp = [uv(u0, v0), uv(u1, v0), uv(u1, v1), uv(u0, v1)]
    c = (sum(p[0] for p in fp) / 4, sum(p[1] for p in fp) / 4)
    base = datum.up(*c, HUT_FLOOR)
    return dict(id=HUT_ID, name='', style='white', levels=1, fh=round(HUT_ROOF - HUT_COPING - HUT_FLOOR, 3),
                height=round(HUT_ROOF - HUT_FLOOR, 2), base=base, parapet=HUT_COPING, top_ground=base,
                footprint=[list(p) for p in fp])


# ----------------------------------------------------------------------------- 외래진료소's roof
# (고증 3.1.2 「외래진료소의 덩어리」; 2.10's / 3.1.2's frame: o (150, -250), u along 43 deg, v north-west of it.)  Five
# low hipped wings ridged along u side by side across v, each 12 m wide with a flat strip of 3 m at the eaves between
# them (the 1997 scans: the ridges at v -20.3, -5.2, 10.0, 25.4, 40.6, 46.4 - 46.9 m; the eaves and the strips 45.4 - 46.0 m,
# four pairs of frames on two lines across).  Wings 1 - 2 run on north-east to u -55.5 (a 2.5 m grid of heights over the
# hall and 제중관, 26/16 x 27/17 and 27/17 x 27/18: their eaves and ridge go on unbroken to there, 제중관's 47.3 - 57 m
# begins), with the flat block south of them.
CLINIC_WINGS = [(-129.0, -83.0, -26.4, -14.3), (-129.0, -83.0, -11.2, 0.8), (-129.0, -83.0, 4.0, 16.0),
                (-129.0, -55.5, 19.4, 31.4), (-129.0, -55.5, 34.6, 46.5)]
# its outline: the three south wings to u -83, the two north ones and the flat block south of them (v 7 .. 19.4, eaves'
# height with two cooling towers) on to u -55.5, where 제중관's higher roofs begin (JEJUNG_CUT: what goes off 제중관's
# OSM outline, u0, u1, v0, v1)
CLINIC_UV = [(-129.0, -26.4), (-83.0, -26.4), (-83.0, 7.0), (-55.5, 7.0), (-55.5, 46.5), (-129.0, 46.5)]
JEJUNG_CUT = (-80.0, -55.5, 0.0, 47.0)
CLINIC_EAVES, CLINIC_RIDGE = 45.6, 46.65
CLINIC_FH = 3.7                      # (four storeys from its floor, medwest97.CLINIC_BASE 30.82, to the eaves)


def clinic_roof():
    """building dict 'roof' for blender/generic.py clinic_roof"""
    rise = CLINIC_RIDGE - CLINIC_EAVES
    return dict(o=[150.0, -250.0], ang=round(math.radians(43.0), 6), wings=[list(w) for w in CLINIC_WINGS],
                pitch=round(rise / (6.0 + 0.3), 3), over=0.3)


# ----------------------------------------------------------------------------- 들어오는 길 서쪽 주차장 북서쪽 숲 비탈
# (고증 3.1.2 「들어오는 길 서쪽 주차장과 건물 둘」; medwest97's frame for it: o (-35, -385), u along -43 deg south-east
# with the stall rows, v north-east.)  Under the crowns in July 1997; the leafless winter frames of 1996 see the floor:
# 29 points on a 4 m grid (u -34 .. -14, v -10 .. 22), each 1996 26/16 x 26/17, 27/17 x 27/18 or 26/15 x 26/16 (two
# or three pairs within 0.1 - 0.4 m at 14 of them), lie on one plane z = 29.01 + 0.0613 u + 0.0259 v (해발) with rms
# 0.27 m (largest 0.91 m, a crown): 26.8 - 27.4 m at u -34, 28.2 - 28.6 m at the car park's edge (u -14).  The game's
# ground there fell 1.5 - 3.2 m lower (a bank down from the car park).
WOOD_O, WOOD_A = (-35.0, -385.0), -43.0
WOOD_PLANE = (29.01, 0.0613, 0.0259)
WOOD_UV = (-35.0, -12.0, 0.0, 20.0)   # (where two pairs or three agree; the gate's east lawn, south-west, stays)
WOOD_RING = 10.0


def wood_uv(x, y):
    a = math.radians(WOOD_A)
    dx, dy = np.asarray(x, float) - WOOD_O[0], np.asarray(y, float) - WOOD_O[1]
    return dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)


def wood_grade(Hn, X, Y, FIXED, halls_keep, fill):
    """the wood's floor north-west of the car park on the 1996 plane (nodes another rule set took, FIXED, and the
    halls' feet, 3 m, stay), the ring of WOOD_RING m round it eased (fill: build_campus.py harmonic_fill).  Returns
    (the nodes set, a summary)"""
    u, v = wood_uv(X, Y)
    u0, u1, v0, v1 = WOOD_UV
    near = shapely.contains_xy(unary_union([h.buffer(3.0) for h in halls_keep]), X, Y)
    inside = (u >= u0) & (u <= u1) & (v >= v0) & (v <= v1) & ~FIXED & ~near
    H0 = Hn.copy()
    z = WOOD_PLANE[0] + WOOD_PLANE[1] * u + WOOD_PLANE[2] * v
    Hn[inside] = z[inside] + datum.tilt(X[inside], Y[inside])
    du = np.maximum(np.maximum(u0 - u, u - u1), 0.0)
    dv = np.maximum(np.maximum(v0 - v, v - v1), 0.0)
    ring = (np.hypot(du, dv) > 0) & (np.hypot(du, dv) <= WOOD_RING) & ~FIXED & ~near
    FIXED_ = FIXED | inside
    if ring.any():
        fill(ring & ~FIXED_)
    d = Hn - H0
    return inside, dict(set=int(inside.sum()), eased=int(ring.sum()),
                        lift=(round(float(d[inside].min()), 2), round(float(d[inside].max()), 2)) if inside.any() else None)


# ----------------------------------------------------------------------------- 옛 신촌역 역사 (1997)
# (고증 4.8.4 「옛 신촌역 역사」.)  The 1920 wooden station on the south edge of the yard, facing the forecourt: the
# waiting hall (대합실) east under a steep gable to the south with its tip folded back (a half hip), the office (역무실)
# west of it under a hipped roof ridged along the rails, a lean-to over the office's front, a gable bay on its north
# side, and the outbuilding (부속건물: stores, the parcels office, toilets) west of it on its own.  Cream walls (cement
# sprayed on the boards), a grey plinth, dark blue-green tiles (서울연구원 52232 - 52250, 1996; 김종헌 2007's 1977 plan
# and 1982 photos).  Place and heights on the 1997-07-28 scans (27/17 x 27/18, 26/16 x 27/18, 26/16 x 27/17): the hall's
# ridge at x 423 (42.0 m), the office's at y -494.6 (40.0 - 40.9 m), the lean-to 36.2 m, the outbuilding's roof 37.5 m
# (x 385.5 - 406.7, y -490 .. -494.5), the forecourt 33.9 m at the door down to 33.2 m in the car park.  (In 2006 the
# hall stayed about where it was and the office went to its east side: OSM's outline is the moved one.)
# The station's frame: o the hall's front wall at its middle, u east (1 deg: the outbuilding's north edge on the
# scans, the rails 2 deg), v north.
ST_O, ST_A = (423.0, -501.5), 1.0
ST_FLOOR = 33.9                      # 해발: the forecourt at the door, and the floors
ST_HALL = dict(u=(-4.1, 4.1), v=(0.0, 9.3), eaves=4.0, apex=8.2, fold=1.1, over=0.5)
ST_OFFICE = dict(u=(-15.0, -4.1), v=(2.8, 11.0), eaves=3.4, ridge=6.5, over=0.45)
ST_BAY = dict(u=(-9.6, -5.6), v=(11.0, 12.4), ridge=6.0)
ST_LEAN = dict(u=(-14.6, -4.1), v=(0.4, 2.8), z=(2.9, 2.5))
ST_CHIMNEYS = [(-10.6, 6.9, 7.5), (-1.0, 7.8, 8.3)]          # (u, v, top over the floor)
ST_ANNEX = dict(c=(396.1, -492.25), L=21.2, W=4.5, eaves=3.0, ridge=3.9)
# the forecourt and the car park in front of it on the 1997 scans (x 383 - 432, y -484 .. -533), their ground by y
# (three pairs within 0.4 m: 34.0 by the yard, 33.9 at the door, 33.5 at y -506, 33.3 at -515, 33.0 at -525); the
# game's town ground (the 2006 survey, after the forecourt was dug for the new station) stood 1.5 - 2.5 m under it
ST_YARD = [(383.0, -486.0), (431.0, -484.0), (433.0, -504.0), (428.0, -533.0), (396.0, -533.0), (395.0, -504.0),
           (383.0, -499.0)]
ST_YARD_Z = [(-536.0, 32.9), (-525.0, 33.05), (-515.0, 33.3), (-506.0, 33.5), (-500.0, 33.9), (-486.0, 34.0)]
ST_RING = 8.0


def st_xy(u, v):
    a = math.radians(ST_A)
    return (ST_O[0] + u * math.cos(a) - v * math.sin(a), ST_O[1] + u * math.sin(a) + v * math.cos(a))


def _st_rect(u0, u1, v0, v1):
    return [st_xy(u0, v0), st_xy(u1, v0), st_xy(u1, v1), st_xy(u0, v1)]


def station_polys(pad=0.0):
    """the station's and the outbuilding's outlines (with the eaves), and the car park in front: what the town's
    houses give way to"""
    h, o, b = ST_HALL, ST_OFFICE, ST_BAY
    g = unary_union([Polygon(_st_rect(h['u'][0], h['u'][1], h['v'][0] - h['over'], h['v'][1] + h['over'])),
                     Polygon(_st_rect(o['u'][0] - o['over'], o['u'][1], ST_LEAN['v'][0], o['v'][1] + o['over'])),
                     Polygon(_st_rect(b['u'][0], b['u'][1], b['v'][0], b['v'][1]))])
    a = math.radians(ST_A)
    c, L, W = ST_ANNEX['c'], ST_ANNEX['L'], ST_ANNEX['W']
    ann = Polygon([(c[0] + u * math.cos(a) - v * math.sin(a), c[1] + u * math.sin(a) + v * math.cos(a))
                   for u, v in ((-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2))])
    park = Polygon([(398.0, -503.0), (426.0, -503.0), (426.0, -533.0), (398.0, -533.0)])
    return unary_union([g.buffer(pad), ann.buffer(pad), park])


def station_grade(Hn, X, Y, FIXED, fill):
    """the forecourt and the car park on the 1997 scans' ground (ST_YARD, ST_YARD_Z by y), a ring of ST_RING m round
    them eased (fill: build_campus.py harmonic_fill).  Late: the planting has read the ground as it was; before the
    rails' bank is laid (its south edge in the yard meets this ground, no wall).  Returns (the nodes set, a summary)"""
    poly = Polygon(ST_YARD)
    inside = shapely.contains_xy(poly, X, Y) & ~FIXED
    ys, zs = zip(*ST_YARD_Z)
    H0 = Hn.copy()
    z = np.interp(Y, ys, zs) + datum.tilt(X, Y)
    Hn[inside] = z[inside]
    d = shapely.distance(poly, shapely.points(X, Y))
    ring = (d > 0) & (d <= ST_RING) & ~FIXED & ~inside
    if ring.any():
        fill(ring)
    dd = Hn - H0
    return inside, dict(set=int(inside.sum()), eased=int(ring.sum()),
                        lift=(round(float(dd[inside].min()), 2), round(float(dd[inside].max()), 2)) if inside.any() else None)


def station97():
    """campus.json town.station97 (blender/town.py station97 draws it): the frame, the floor (on the working datum)
    and the parts in the station's frame"""
    return dict(o=list(ST_O), a=ST_A, at=list(st_xy(0.0, 4.6)), base=datum.up(*st_xy(0.0, 4.6), ST_FLOOR),
                hall=ST_HALL, office=ST_OFFICE, bay=ST_BAY, lean=ST_LEAN, chimneys=[list(c) for c in ST_CHIMNEYS],
                annex=dict(ST_ANNEX, c=list(ST_ANNEX['c'])))


def station_clear(blocks, n_skip):
    """the town's houses (after the first n_skip) on the station, the outbuilding or the car park: one the station
    cuts across but leaves 3.5 m of goes short along its length on the far side (the low white house east of the hall
    in 52250 · 52234), the rest b[6] < 0 (blender/town.py still draws their random looks).  Returns (gone, shortened)"""
    from gate_town import _rect
    g = station_polys(0.3)
    shapely.prepare(g)
    gone = cut = 0
    for b in blocks[n_skip:]:
        if b[6] <= 0:
            continue
        r = _rect(b)
        if not shapely.intersects(g, r.buffer(-0.2)):
            continue
        cx, cy, L, W, ang = b[:5]
        c, s_ = math.cos(ang), math.sin(ang)
        ov = r.intersection(g)
        us = [(x - cx) * c + (y - cy) * s_ for x, y in ov.exterior.coords] if ov.geom_type == 'Polygon' else []
        keep = None
        if us:
            lo, hi = min(us), max(us)
            a_, b_ = (-L / 2, lo) if lo + L / 2 > L / 2 - hi else (hi, L / 2)
            if b_ - a_ >= 3.5 and ov.area < 0.6 * r.area:
                keep = (a_, b_)
        if keep is None:
            b[6] = -b[6]
            gone += 1
            continue
        m = (keep[0] + keep[1]) / 2
        b[0], b[1], b[2] = round(cx + m * c, 2), round(cy + m * s_, 2), round(keep[1] - keep[0], 2)
        cut += 1
    return gone, cut
