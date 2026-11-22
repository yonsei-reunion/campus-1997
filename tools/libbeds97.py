"""중앙도서관 앞마당의 돋운 화단 (reference/고증/3.2-3.3 3.2.1 「돋운 화단」).

1996년 겨울 · 1997년 7월 · 1999년 5월 원본 스캔에서 앞마당의 화단 조각은 둘레 포장(가운데 광장, 비스듬한 길, 관목 띠를 따르는
찻길, 화단 바깥 길)보다 0.3 ~ 0.8 m 높은 돋운 화단이다. 가는 돌 옹벽이 아니라 가파른 잔디 둔덕(수평 폭 0.5 ~ 2 m)이고, 용재 동상
앞 포장 띠는 화단보다 조금 더 높아 광장에서 네 단 계단으로 오른다. 5 m 격자로는 이 둔덕이 칸 하나의 비탈이 되므로, 땅 격자는
그대로 두고(지금 게임의 땅은 둘레 포장 높이) 화단을 그 위의 판(땅의 재질, 걷는 면)으로 덮고, 판의 가에서 둘레 포장까지 둔덕을
면으로 내린다(장기원 기념관 동쪽 띠 jk97 와 같은 꼴: build_campus.py 의 med_west top · quads · walk · plates 로 나감).

틀: 도서관 정면 틀(build_campus.py _lf0 · _lfu · _lfn, libsouth97 와 같음): s 는 정면을 따라 북쪽, o 는 백양로 쪽.
높이: 면은 사진 값(해발)이고, 게임에는 DZ(광장에서 잰 사진 − 게임)를 더해 놓는다. 작업면으로는 datum.tilt 를 더한다.

    res = libbeds97.build(ground)     # ground(x, y): 땅(작업면). 돌려주는 것: top(v, f), quads, walk, plates, info
"""
import math

import numpy as np
import shapely
from shapely.geometry import Polygon, box
from shapely.ops import triangulate

import datum

O = np.array([-85.44, -71.08])
T = np.array([0.25441, 0.9671])
N = np.array([0.9671, -0.25441])
DZ = -0.22                         # 사진 − 게임 = +0.22(광장 북쪽 s 39 ~ 46 의 면: 1996 · 1997 · 1999년 32.98 · 32.98 · 33.00, 게임 32.76)


def xy(s, o):
    p = O + T * s + N * o
    return float(p[0]), float(p[1])


def so(x, y):
    d = np.array([x, y], float) - O
    return float(d @ T), float(d @ N)


# 비스듬한 길(폭 4 m)의 중심선: 북쪽 (85.6, 41.6) -> (47.3, 21.0), 남쪽 (−9.2, 41.6) -> (29.1, 21.0) (3.2.1 표)
def _walk_edge(a, b, side, s_or_o):
    """중심선 a -> b 에서 side 쪽(+1: (s, o) 틀에서 진행 방향의 (−d_o, d_s) 쪽, 북쪽 길에서는 서쪽 조각)으로 2 m 떨어진 가가 s = 값 또는 o = 값 인 줄과 만나는 점"""
    a, b = np.array(a, float), np.array(b, float)
    d = (b - a) / np.linalg.norm(b - a)
    n = np.array([-d[1], d[0]]) * side * 2.0
    p0 = a + n
    k, v = s_or_o
    t = (v - p0[k]) / d[k]
    return tuple(float(c) for c in p0 + d * t)


_NA, _NB = (85.6, 41.6), (47.3, 21.0)
# 북쪽 화단: 길이 둘로 나눔. 각 조각: 꼭짓점(s, o, 반시계), 가마다 둔덕의 수평 폭(꼭짓점 k -> k+1 의 가), 면(사진, 해발)
#   서쪽 조각(찻길과 길 사이): 1996년 126점 33.363 − 0.0006 s + 0.0174 o (rms 0.12), 1999년 171점 33.687 − 0.0033 s + 0.0133 o
#   (rms 0.09): 두 면의 평균. 찻길 쪽은 1.5 ~ 2 m 에 0.4 ~ 0.6 m, 길 쪽은 1 m 안에 0.5 ~ 0.8 m
#   동쪽 조각(동상이 있는 세모): 1996년 171점 33.184 + 0.0107 s − 0.0054 o (rms 0.07), 1999년 118점 32.950 + 0.0167 s − 0.0094 o
#   (rms 0.12): 평균. 광장 쪽은 잔디 선 s 47.83(여덟 장 rms 0.04)에서 0.5 ~ 0.7 m 에 0.45 ~ 0.6 m, 바깥 길 쪽은 0.5 m 안에
#   0.6 ~ 0.75 m, 길 쪽은 1.5 m 에 0.35 ~ 0.45 m
LAWN_N = 47.83                     # 광장 북쪽 가의 잔디 선
LAWN_S = 28.70                     # 광장 남쪽 가의 잔디 선(o 36 ~ 39, 여덟 장 rms 0.03 ~ 0.09)
_SA, _SB = (-9.2, 41.6), (29.1, 21.0)
PIECES = {
    'north_west': dict(pts=[_walk_edge(_NA, _NB, 1, (1, 21.0)), (85.5, 21.0), _walk_edge(_NA, _NB, 1, (0, 85.5))],
                       bank=[1.75, 0.6, 1.0], plane=(33.525, -0.00195, 0.01535)),
    'north_east': dict(pts=[_walk_edge(_NA, _NB, -1, (0, LAWN_N)), (LAWN_N, 41.6), _walk_edge(_NA, _NB, -1, (1, 41.6))],
                       bank=[0.6, 0.5, 1.5], plane=(33.067, 0.0137, -0.0074)),
    # 남쪽 화단: 길(남동 (−9.2, 41.6) -> 북서 (29.1, 21.0))이 둘로 나눔
    #   서쪽 조각(찻길과 길 사이): 1996년 337점 34.947 + 0.0061 s − 0.0652 o (rms 0.085), 1999년 199점 34.611 + 0.0102 s − 0.0533 o
    #   (rms 0.12): 평균. 찻길 쪽은 1 ~ 2 m 에 0.1 ~ 0.3 m(찻길 가에 얕은 도랑), 길 쪽은 완만히 0.2 ~ 0.4 m, 남쪽 끝 길 쪽 0.4 ~ 0.7 m
    #   동쪽 조각: 1996년 154점 33.922 + 0.0210 s − 0.0380 o (rms 0.084), 1999년 48점 34.669 + 0.0115 s − 0.0557 o (rms 0.11):
    #   평균. 바깥 길 쪽은 1 m 안에 0.6 ~ 0.8 m, 광장 쪽은 잔디 선 s 28.70(o 36 ~ 39, 여덟 장)에서 0.5 m 안에 0.3 ~ 0.45 m,
    #   길 쪽은 1 ~ 1.5 m 에 0.3 ~ 0.6 m
    'south_west': dict(pts=[(-11.5, 21.0), _walk_edge(_SA, _SB, -1, (1, 21.0)), _walk_edge(_SA, _SB, -1, (0, -11.5))],
                       bank=[1.5, 2.0, 0.8], plane=(34.779, 0.00815, -0.05925)),
    'south_east': dict(pts=[_walk_edge(_SA, _SB, 1, (1, 41.6)), (LAWN_S, 41.6), _walk_edge(_SA, _SB, 1, (0, LAWN_S))],
                       bank=[0.75, 0.5, 1.25], plane=(34.2955, 0.01625, -0.04685)),
}
# 용재 동상 앞 포장 띠(3.2.1 「용재 동상」): 띠 바닥 33.83 ~ 33.95(사진), 띠 양옆 화단보다 0.15 ~ 0.3 m 높음. 그 남쪽 끝의 계단:
# 1999년 남쪽 장 둘의 디딤 앞면 줄 s 47.8 · 48.1 · 48.5, 발치 줄 47.3 (1997년 26/16 도 같은 자리): 네 단, 디딤 0.4 m
STRIP = dict(s=(48.55, 56.0), o=(33.0, 36.1), z=33.89)
FLIGHT = dict(s0=47.35, tread=0.4, n=4)
LATTICE = 1.25
# 둘레 가에는 게임의 연석(web/src/curbs.js: 잔디 쪽으로 0.15 m 폭, 0.15 m 높이)이 칠 경계를 따라 서는데, 연석은 땅 재질 메시
# (이 둔덕) 위에 얹히므로 둔덕을 연석 뒤에서 시작한다: 바깥 가를 KERB m 안으로, 그 높이는 땅 위 KERB_Z(연석 윗면 바로 밑)
KERB, KERB_Z = 0.2, 0.13


def plane_h(piece, x, y):
    """조각의 면(해발, 게임 기준)"""
    a, b, c = PIECES[piece]['plane']
    s, o = so(x, y)
    return a + b * s + c * o + DZ


def strip_h(x, y):
    return STRIP['z'] + DZ


def _inset(pts, widths):
    """가마다 그 폭만큼 안으로 들인 다각형의 꼭짓점(반시계 다각형, 가 k: pts[k] -> pts[k+1])"""
    n = len(pts)
    P = [np.array(p, float) for p in pts]
    lines = []
    for k in range(n):
        a, b = P[k], P[(k + 1) % n]
        d = (b - a) / np.linalg.norm(b - a)
        nin = np.array([-d[1], d[0]])                  # (left of a CCW edge: inside)
        lines.append((a + nin * widths[k], d))
    Q = []
    for k in range(n):
        (p1, d1), (p2, d2) = lines[k - 1], lines[k]
        A = np.array([[d1[0], -d2[0]], [d1[1], -d2[1]]])
        t = np.linalg.solve(A, p2 - p1)
        Q.append(tuple(float(c) for c in p1 + d1 * t[0]))
    return Q


def _ccw(pts, widths):
    """xy 로 반시계(위에서 보아)인 꼭짓점과 그 가의 폭. 뒤집으면 가 j 는 원래 가 n - 2 - j"""
    n = len(pts)
    a = sum(pts[k][0] * pts[(k + 1) % n][1] - pts[(k + 1) % n][0] * pts[k][1] for k in range(n))
    if a > 0:
        return pts, list(widths)
    return pts[::-1], [widths[(n - 2 - j) % n] for j in range(n)]


def _up(q):
    """위를 보게(법선 z > 0)"""
    a, b, c = (np.array(v, float) for v in q[:3])
    return q if np.cross(b - a, c - a)[2] > 0 else q[::-1]


def _both(mat, q):
    return [[mat, q], [mat, [list(v) for v in q[::-1]]]]


def _lattice(poly, hfun, V, F):
    """다각형을 LATTICE m 격자로 잘라 세모로: 꼭짓점은 V 사전(xy -> 번호), 높이는 hfun(작업면)"""
    def vid(x, y):
        k = (round(x, 3), round(y, 3))
        if k not in V:
            V[k] = (len(V), hfun(*k))
        return V[k][0]
    x0, y0, x1, y1 = poly.bounds
    for i in range(int(math.floor(x0 / LATTICE)), int(math.ceil(x1 / LATTICE))):
        for j in range(int(math.floor(y0 / LATTICE)), int(math.ceil(y1 / LATTICE))):
            sq = box(i * LATTICE, j * LATTICE, (i + 1) * LATTICE, (j + 1) * LATTICE)
            pc = sq.intersection(poly)
            for g in (pc.geoms if hasattr(pc, 'geoms') else [pc]):
                if g.geom_type != 'Polygon' or g.area < 1e-3:
                    continue
                tris = [g] if len(g.exterior.coords) == 4 else \
                    [t for t in triangulate(g) if g.buffer(1e-6).contains(t.representative_point())]
                for t in tris:
                    c = list(shapely.geometry.polygon.orient(t, 1.0).exterior.coords)[:3]
                    if Polygon(c).area > 1e-4:
                        F.append([vid(*q) for q in c])


def build(ground):
    """ground(x, y): 땅(작업면). 판(조각마다 둔덕 안쪽, 띠), 둔덕 · 띠의 옆면 · 계단의 면, 걷는 면, 높이 표(plates)"""
    V, F, quads, walk, plates = {}, [], [], [], []
    R = lambda x, y, z: [round(float(x), 3), round(float(y), 3), round(float(z), 3)]
    info = {}
    work = lambda f: (lambda x, y: float(f(x, y)) + float(datum.tilt(x, y)))
    for name, P in PIECES.items():
        pts, widths = _ccw([xy(s, o) for s, o in P['pts']], P['bank'])
        inner = _inset(pts, widths)
        outer = _inset(pts, [KERB] * len(pts))
        hw = work(lambda x, y, n_=name: plane_h(n_, x, y))
        poly = Polygon(inner)
        _lattice(poly, hw, V, F)
        # 둔덕: 가마다 판의 가(안) -> 연석 뒤 바깥 가, 0.5 m 마다 잘라 땅을 따름
        lo = []
        for k in range(len(pts)):
            a, b, qa, qb = outer[k], outer[(k + 1) % len(pts)], inner[k], inner[(k + 1) % len(pts)]
            m = max(1, int(math.ceil(math.dist(a, b) / 0.5)))
            for t in range(m):
                f0, f1 = t / m, (t + 1) / m
                o0 = (a[0] + (b[0] - a[0]) * f0, a[1] + (b[1] - a[1]) * f0)
                o1 = (a[0] + (b[0] - a[0]) * f1, a[1] + (b[1] - a[1]) * f1)
                i0 = (qa[0] + (qb[0] - qa[0]) * f0, qa[1] + (qb[1] - qa[1]) * f0)
                i1 = (qa[0] + (qb[0] - qa[0]) * f1, qa[1] + (qb[1] - qa[1]) * f1)
                zt0, zt1 = hw(*i0), hw(*i1)
                zb0, zb1 = min(ground(*o0) + KERB_Z, zt0 - 0.02), min(ground(*o1) + KERB_Z, zt1 - 0.02)
                lo.append(zt0 - zb0)
                q = _up([R(*o0, zb0), R(*o1, zb1), R(*i1, zt1), R(*i0, zt0)])
                quads.append(['terrain_drape', q])
                walk.append([list(v) for v in q])          # (own points: datum.heights moves each list once)
        # 판이 땅보다 얼마나 높은지(마디를 보지 않으므로 땅이 판 위로 솟으면 안 됨): 1 m 마다
        bx0, by0, bx1, by1 = poly.bounds
        cl = [hw(x, y) - ground(x, y) for x in np.arange(bx0, bx1, 1.0) for y in np.arange(by0, by1, 1.0)
              if poly.contains(shapely.geometry.Point(x, y))]
        info[name] = dict(m2=round(poly.area, 1), bank=[round(min(lo), 2), round(max(lo), 2)], clear=round(min(cl), 2))
        plates.append(dict(name='lib_bed_' + name, poly=[list(p) for p in inner], hfun=hw))
    # 띠: 화단 판 위의 판(조금 높음)과 옆면(화강석 연석), 남쪽 끝 계단
    hs = work(strip_h)
    s0, s1 = STRIP['s']
    o0, o1 = STRIP['o']
    sp = shapely.geometry.polygon.orient(Polygon([xy(s0, o0), xy(s0, o1), xy(s1, o1), xy(s1, o0)]), 1.0)
    _lattice(sp, hs, V, F)
    under = work(lambda x, y: plane_h('north_east', x, y))
    sides = [((s0, o1), (s1, o1)), ((s1, o1), (s1, o0)), ((s1, o0), (s0, o0))]       # (east, north, west; outward to the right)
    for (sa, oa), (sb, ob) in sides:
        m = max(1, int(math.ceil(math.hypot(sb - sa, ob - oa) / 1.0)))
        for t in range(m):
            p0 = xy(sa + (sb - sa) * t / m, oa + (ob - oa) * t / m)
            p1 = xy(sa + (sb - sa) * (t + 1) / m, oa + (ob - oa) * (t + 1) / m)
            quads += _both('stone_granite', [R(*p0, under(*p0) - 0.1), R(*p1, under(*p1) - 0.1), R(*p1, hs(*p1)), R(*p0, hs(*p0))])
    plates.append(dict(name='lib_bed_strip', poly=[list(p) for p in list(sp.exterior.coords)[:-1]], hfun=hs))
    # 계단: 광장(발치)에서 띠까지 n 단, 디딤 tread. 챌판은 땅 밑까지, 양옆은 막음
    n, tr, fs = FLIGHT['n'], FLIGHT['tread'], FLIGHT['s0']
    zf = min(ground(*xy(fs - 0.2, o)) for o in np.linspace(o0, o1, 5))
    zt = hs(*xy(s0 + 0.2, (o0 + o1) / 2))
    rise = (zt - zf) / n
    zbot = zf - 0.3
    for k in range(n):
        sk = fs + k * tr
        z_ = zf + (k + 1) * rise
        quads += _both('stone_step', [R(*xy(sk, o0), zbot), R(*xy(sk, o1), zbot), R(*xy(sk, o1), z_), R(*xy(sk, o0), z_)])
        se = sk + tr if k < n - 1 else s0 + 0.02
        quads.append(['stone_step', _up([R(*xy(sk, o0), z_), R(*xy(sk, o1), z_), R(*xy(se, o1), z_), R(*xy(se, o0), z_)])])
        for o_ in (o0, o1):
            quads += _both('stone_granite', [R(*xy(sk, o_), zbot), R(*xy(se, o_), zbot), R(*xy(se, o_), z_), R(*xy(sk, o_), z_)])
    walk.append(_up([R(*xy(fs - 0.2, o0), zf + 0.02), R(*xy(fs - 0.2, o1), zf + 0.02), R(*xy(s0 + 0.05, o1), zt + 0.02),
                     R(*xy(s0 + 0.05, o0), zt + 0.02)]))
    info['flight'] = dict(risers=n, rise=round(rise, 3), foot=round(zf - float(datum.tilt(*xy(fs, 34.5))), 2),
                          top=round(zt - float(datum.tilt(*xy(s0, 34.5))), 2))
    vs = sorted(V.values(), key=lambda t: t[0])
    keys = sorted(V, key=lambda k: V[k][0])
    top = dict(v=[[k[0], k[1], round(float(h), 3)] for k, (_, h) in zip(keys, vs)], f=F)
    return dict(top=top, quads=quads, walk=walk, plates=plates, info=info)
