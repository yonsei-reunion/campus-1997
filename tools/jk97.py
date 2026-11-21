"""장기원 기념관의 몸체와 남쪽 끝 (reference/고증/3.15-3.17 「3.16」 「몸체의 외곽선과 남쪽 끝」).

1996년 겨울(잎이 진) 원본 스캔 26/15 · 26/16 을 몸체의 틀에서 난간 높이(45.2 m) 수평면으로 읽은 것:
- 몸체: 지붕 44.4 m(서쪽 단과 같은 높이), 그 가의 난간 0.9 m. 남쪽 끝이 처음 외곽선보다 3.7 m 남쪽, 북쪽 끝이 2.3 m 남쪽,
  서쪽 면이 1.45 m 서쪽이다(35.4 × 10.95 m). 처음에는 남쪽 끝의 지붕을 단으로 읽어 남쪽 벽 밖에 44 m 둔덕이 있었다
- 남쪽 면 앞: 원통 둘레 마당과 같은 높이의 화단(깊이 3.5 m), 그 남쪽 가에 낮은 옹벽, 그 아래 마당(1.1 ~ 1.4 m 아래).
  연세춘추 2007년 사진의 붉은 벽돌 옹벽(흰 갓) · 벽돌 기둥 사이 돌계단이 이것이다

틀: 원점 C(처음 외곽선의 가운데), u 는 몸체를 따라 북북동(중앙도서관의 긴 축), v 는 가로질러 동쪽.
5 m 격자로는 옹벽이 한 칸의 비탈이 되므로, 옹벽이 지나는 칸의 화단 쪽 마디를 마당 높이로 내리고 화단 · 마당을 그 위의
판(build_campus.py dwb_deck)으로 덮은 뒤 옹벽 · 기둥 · 계단을 면으로 세운다(tools/audnorth97.py isle_wall_* 와 같은 꼴).

    took, cells, poly, hfun, info = jk97.grade(Hn, X, Y, halls)   # 맨 끝(JK_SW97 뒤): 땅을 읽은 것이 모두 끝난 뒤
    deck = dwb_deck(cells, poly, hfun)                            # build_campus
    quads, guards, walk = jk97.walls(top, foot)
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

import datum

ID = 990011
C = np.array([-156.25, -24.0])
U = np.array([0.2544, 0.9671])
V = np.array([U[1], -U[0]])
BLOCK = (-20.7, 14.7, -6.2, 4.75)          # 몸체: u 남쪽 끝 · 북쪽 끝, v 서쪽 면 · 동쪽 면
FH, PARAPET = 3.3, 0.9                      # 층 높이(바닥 37.82 -> 지붕 44.4 m), 난간
WALL_U = -24.2                              # 옹벽의 면(남쪽 면에서 3.5 m)
WALL_V = (-7.6, 3.85)                       # 옹벽의 서쪽 끝(마당과 높이가 같아지는 곳) · 동쪽 모서리(북쪽으로 꺾여 남쪽 면까지)
FLIGHT_V = (0.45, 3.35)                     # 계단(두 기둥 사이)
TREAD, MAXRISE = 0.30, 0.175
PIER, PIER_H = 0.5, 0.45                    # 기둥의 한 변, 화단 위 높이
WALL_T, WALL_H, COPE_T, COPE_O = 0.3, 0.10, 0.08, 0.04   # 옹벽 두께, 화단 위 높이, 갓의 두께 · 넘침
YARD_Z = 36.3                               # 옹벽 아래 마당(해발, 1996년 겨울 (−166 ~ −158, −50) 36.0 ~ 36.6 m)


def xy(u, v):
    p = C + U * u + V * v
    return float(p[0]), float(p[1])


def uv(x, y):
    d = np.array([x, y], float) - C
    return float(d @ U), float(d @ V)


def court_h(x, y):
    """원통 둘레 마당의 면(해발, build_campus.py JK_SW97): 화단도 이 면 위"""
    return 38.31 + 0.118 * (np.asarray(y, float) + 40.7)


def centre():
    u0, u1, v0, v1 = BLOCK
    return xy((u0 + u1) / 2, (v0 + v1) / 2)


def half():
    u0, u1, v0, v1 = BLOCK
    return (u1 - u0) / 2, (v1 - v0) / 2


def block():
    u0, u1, v0, v1 = BLOCK
    return Polygon([xy(u0, v0), xy(u0, v1), xy(u1, v1), xy(u1, v0)])


def court_poly():
    """마당 다각형(JK_COURT97)이 몸체 남서쪽 발치까지: 마디 (−165, −40) 이 마당 높이로(서쪽 면이 발치까지 드러남)"""
    return Polygon([(-186.0, -50.0), (-168.0, -50.0), (-168.0, -46.0), (-164.5, -46.0), (-164.5, -39.5), (-167.5, -36.0),
                    (-172.0, -31.0), (-175.0, -28.0), (-186.0, -29.0)])


def bed():
    """남쪽 면 앞 화단(옹벽 위): 연석을 두지 않는 곳"""
    return Polygon([xy(WALL_U, WALL_V[0]), xy(WALL_U, WALL_V[1]), xy(BLOCK[0], WALL_V[1]), xy(BLOCK[0], WALL_V[0])])


def wall_line():
    """옹벽의 면: 서쪽 끝 -> 남동 모서리 -> 남쪽 면(화단이 왼쪽)"""
    return [(WALL_U, WALL_V[0]), (WALL_U, WALL_V[1]), (BLOCK[0], WALL_V[1])]


def flight_n(z_top, z_foot):
    return max(1, int(math.ceil((z_top - z_foot) / MAXRISE - 0.1)))


def _notch(n):
    """계단이 파고든 자리(화단에서 뺌): 맨 아래 챌판이 옹벽의 면, 맨 위 챌판 위가 화단"""
    return Polygon([xy(WALL_U - 0.5, FLIGHT_V[0]), xy(WALL_U - 0.5, FLIGHT_V[1]), xy(WALL_U + (n - 1) * TREAD, FLIGHT_V[1]),
                    xy(WALL_U + (n - 1) * TREAD, FLIGHT_V[0])])


def _raised():
    """옹벽 위(화단 · 마당 쪽): 옹벽의 면 북쪽, 동쪽 모서리 서쪽"""
    return Polygon([xy(WALL_U, WALL_V[0]), xy(WALL_U, WALL_V[1]), xy(BLOCK[0] + 8.0, WALL_V[1]), xy(BLOCK[0] + 8.0, WALL_V[0] - 6.0),
                    xy(WALL_U, WALL_V[0] - 6.0)])


_N = [None]


def grade(Hn, X, Y, halls, step=5.0, half_=800.0):
    """옹벽이 지나는 5 m 칸의 마디 가운데 화단 쪽의 것을 마당 높이(YARD_Z)로 내린다. 그 마디를 나누는 칸의 화단 · 마당을
    덮을 판의 칸과 다각형(건물과 계단 자리를 뺌), 판의 높이 함수(작업면), 요약을 돌려준다. halls: 판에서 뺄 건물 외곽선"""
    ln = LineString([xy(*q) for q in wall_line()])
    raised = _raised()
    cells = set()
    x0, y0, x1, y1 = ln.bounds
    for j in range(int(math.floor((y0 + half_) / step)), int(math.ceil((y1 + half_) / step))):
        for i in range(int(math.floor((x0 + half_) / step)), int(math.ceil((x1 + half_) / step))):
            bx = shapely.geometry.box(-half_ + i * step, -half_ + j * step, -half_ + (i + 1) * step, -half_ + (j + 1) * step)
            if bx.intersection(ln).length > 0.05:
                cells.add((j, i))
    low = np.zeros(X.shape, bool)
    for j, i in cells:
        low[j:j + 2, i:i + 2] = True
    hb = unary_union([h.buffer(0) for h in halls])
    bed = Polygon([xy(WALL_U, WALL_V[0]), xy(WALL_U, WALL_V[1]), xy(BLOCK[0] + 8.0, WALL_V[1]), xy(BLOCK[0] + 8.0, WALL_V[0])])
    down = low & shapely.contains_xy(bed, X, Y) & ~shapely.contains_xy(hb, X, Y)     # (not west of the wall's end)
    h0 = Hn.copy()
    Hn[down] = YARD_Z + datum.tilt(X[down], Y[down])
    # (the yard's own nodes under the wall: up to the photos' yard where the surface model ran lower)
    d_ = np.stack([X - C[0], Y - C[1]], -1)
    yard = low & ~down & (d_ @ U < WALL_U) & (d_ @ V > WALL_V[0]) & (d_ @ V < WALL_V[1])
    Hn[yard] = np.maximum(Hn[yard], YARD_Z + datum.tilt(X[yard], Y[yard]))
    jj, ii = np.nonzero(down)
    deck_cells = {(j + a, i + b) for j, i in zip(jj, ii) for a in (-1, 0) for b in (-1, 0)}
    hw = lambda x, y: float(court_h(x, y)) + float(datum.tilt(x, y))
    # (the flight: from the bed at its head down to the yard)
    xf, yf = xy(WALL_U - 0.3, sum(FLIGHT_V) / 2)
    fx, fy = (xf + half_) / step, (yf + half_) / step
    i, j = int(fx), int(fy)
    ax, ay = fx - i, fy - j
    zf = Hn[j, i] * (1 - ax) * (1 - ay) + Hn[j, i + 1] * ax * (1 - ay) + Hn[j + 1, i] * (1 - ax) * ay + Hn[j + 1, i + 1] * ax * ay
    _N[0] = flight_n(hw(*xy(WALL_U + 2.0, sum(FLIGHT_V) / 2)), float(zf))
    poly = unary_union([shapely.geometry.box(-half_ + i * step, -half_ + j * step, -half_ + (i + 1) * step, -half_ + (j + 1) * step)
                        for j, i in deck_cells]).intersection(raised).difference(hb.buffer(0.02)).difference(_notch(_N[0]))
    poly = unary_union([g for g in getattr(poly, 'geoms', [poly]) if g.geom_type == 'Polygon' and g.area > 0.05])
    d = Hn - h0
    info = dict(yard=[(float(x_), float(y_), round(float(v_), 2)) for x_, y_, v_ in zip(X[yard], Y[yard], d[yard])], down=[(float(x_), float(y_), round(float(v_), 2)) for x_, y_, v_ in zip(X[down], Y[down], d[down])],
                deck_cells=len(deck_cells), deck_m2=round(poly.area, 1), risers=_N[0])
    return down, deck_cells, poly, hw, info


def walls(top, foot, step=0.5):
    """붉은 벽돌 옹벽(흰 갓), 계단 양쪽 벽돌 기둥, 돌계단: [재질, 네 점], 막을 곳(다각형), 걷는 면(계단의 비탈).
    top(x, y): 화단의 윗면(판 밖은 땅), foot(x, y): 땅(작업면)"""
    quads, guards, walk = [], [], []
    R = lambda p, z: [round(float(p[0]), 3), round(float(p[1]), 3), round(float(z), 3)]
    n = _N[0]
    f0, f1 = FLIGHT_V
    runs = [[(WALL_U, WALL_V[0]), (WALL_U, f0 - PIER)],                       # 서쪽 끝 -> 서쪽 기둥
            [(WALL_U, WALL_V[1]), (BLOCK[0], WALL_V[1])]]                     # 남동 모서리 -> 남쪽 면
    for run in runs:
        (ua, va), (ub, vb) = run
        L = math.hypot(ub - ua, vb - va)
        k_n = max(1, int(math.ceil(L / step)))
        tu, tv = (ub - ua) / L, (vb - va) / L
        nu, nv = tv, -tu                              # (towards the bed: (u north, v east), left of the run)
        S = [(ua + (ub - ua) * k / k_n, va + (vb - va) * k / k_n) for k in range(k_n + 1)]
        zt = [top(*xy(min(u + nu * 0.05, BLOCK[0] - 0.15), v + nv * 0.05)) for u, v in S]    # (not under the block's wall)
        zb = [foot(*xy(u - nu * 0.1, v - nv * 0.1)) - 0.05 for u, v in S]
        for k in range(k_n):
            if max(zt[k] - zb[k], zt[k + 1] - zb[k + 1]) < 0.12:
                continue
            (u0, v0), (u1, v1) = S[k], S[k + 1]
            F = [xy(u0, v0), xy(u1, v1)]                                      # the face
            B = [xy(u0 + nu * WALL_T, v0 + nv * WALL_T), xy(u1 + nu * WALL_T, v1 + nv * WALL_T)]
            Fo = [xy(u0 - nu * COPE_O, v0 - nv * COPE_O), xy(u1 - nu * COPE_O, v1 - nv * COPE_O)]
            Bo = [xy(u0 + nu * (WALL_T + COPE_O), v0 + nv * (WALL_T + COPE_O)), xy(u1 + nu * (WALL_T + COPE_O), v1 + nv * (WALL_T + COPE_O))]
            w0, w1 = zt[k] + WALL_H, zt[k + 1] + WALL_H
            c0, c1 = w0 + COPE_T, w1 + COPE_T
            # (seen from the yard the run goes left to right: the face, the back over the bed, the coping)
            quads.append(['brick_red', [R(F[0], zb[k]), R(F[1], zb[k + 1]), R(F[1], w1), R(F[0], w0)]])
            quads.append(['brick_red', [R(B[0], zt[k] - 0.05), R(B[0], w0), R(B[1], w1), R(B[1], zt[k + 1] - 0.05)]])
            quads.append(['stone_white', [R(Fo[0], w0), R(Fo[1], w1), R(Fo[1], c1), R(Fo[0], c0)]])
            quads.append(['stone_white', [R(Fo[0], c0), R(Fo[1], c1), R(Bo[1], c1), R(Bo[0], c0)]])
            quads.append(['stone_white', [R(Bo[0], w0), R(Bo[0], c0), R(Bo[1], c1), R(Bo[1], w1)]])
            if min(zt[k] - zb[k], zt[k + 1] - zb[k + 1]) > 0.6:
                guards.append([[round(c, 3) for c in p] for p in (Fo[0], Fo[1], Bo[1], Bo[0])])
    # the flight: n risers up into the bed from the wall's face, between the piers
    z_top = top(*xy(WALL_U + (n - 1) * TREAD + 0.1, (f0 + f1) / 2))
    z_foot = min(foot(*xy(WALL_U - 0.3, v_)) for v_ in np.linspace(f0, f1, 5))
    rise = (z_top - z_foot) / n
    for k in range(n):
        u_ = WALL_U + k * TREAD
        za, zb_ = z_foot + k * rise - (0.3 if k == 0 else 0.0), z_foot + (k + 1) * rise
        quads.append(['stone_step', [R(xy(u_, f0), za), R(xy(u_, f1), za), R(xy(u_, f1), zb_), R(xy(u_, f0), zb_)]])
        if k < n - 1:
            quads.append(['stone_step', [R(xy(u_, f0), zb_), R(xy(u_, f1), zb_), R(xy(u_ + TREAD, f1), zb_), R(xy(u_ + TREAD, f0), zb_)]])
    ua, ub = WALL_U - TREAD, WALL_U + (n - 1) * TREAD + 0.05
    walk.append([R(xy(ua, f0), z_foot), R(xy(ua, f1), z_foot), R(xy(ub, f1), z_top + 0.03), R(xy(ub, f0), z_top + 0.03)])
    # the notch's side walls (brick, under the bed's edge) and the low walls over them back to the bed
    for v_, s_ in ((f0, 1.0), (f1, -1.0)):           # (s_: the flight's side of the wall, +v or -v)
        a, b = xy(WALL_U, v_), xy(WALL_U + (n - 1) * TREAD, v_)
        zc = z_top + WALL_H
        q = [R(a, z_foot - 0.3), R(b, z_foot - 0.3), R(b, zc), R(a, zc)]
        quads.append(['brick_red', q if s_ > 0 else q[::-1]])
        ao, bo = xy(WALL_U, v_ - s_ * WALL_T), xy(WALL_U + (n - 1) * TREAD, v_ - s_ * WALL_T)
        q = [R(ao, z_top - 0.05), R(bo, z_top - 0.05), R(bo, zc), R(ao, zc)]
        quads.append(['brick_red', q[::-1] if s_ > 0 else q])
        quads.append(['stone_white', [R(a, zc), R(b, zc), R(bo, zc), R(ao, zc)] if s_ > 0 else [R(ao, zc), R(bo, zc), R(b, zc), R(a, zc)]])
        guards.append([[round(c, 3) for c in p] for p in (a, b, bo, ao)])
    # the piers at the flight's foot: brick, a white cap
    for va, vb in ((f0 - PIER, f0), (f1, f1 + PIER)):
        cs = [xy(WALL_U - 0.05, va), xy(WALL_U - 0.05, vb), xy(WALL_U - 0.05 + PIER, vb), xy(WALL_U - 0.05 + PIER, va)]
        zb_ = min(foot(*c) for c in cs) - 0.1
        zp = z_top + PIER_H
        for a, b in zip(cs, cs[1:] + cs[:1]):
            quads.append(['brick_red', [R(a, zb_), R(b, zb_), R(b, zp), R(a, zp)]])
        co = [xy(WALL_U - 0.05 - COPE_O, va - COPE_O), xy(WALL_U - 0.05 - COPE_O, vb + COPE_O),
              xy(WALL_U - 0.05 + PIER + COPE_O, vb + COPE_O), xy(WALL_U - 0.05 + PIER + COPE_O, va - COPE_O)]
        for a, b in zip(co, co[1:] + co[:1]):
            quads.append(['stone_white', [R(a, zp), R(b, zp), R(b, zp + COPE_T), R(a, zp + COPE_T)]])
        quads.append(['stone_white', [R(c, zp + COPE_T) for c in co]])
        guards.append([[round(c, 3) for c in p] for p in cs])
    return quads, guards, walk


def paint():
    """(잔디, 아스팔트): 화단 가운데 계단 뒤 포장을 뺀 곳, 옹벽 아래 마당"""
    lawn = Polygon([xy(WALL_U, WALL_V[0]), xy(WALL_U, FLIGHT_V[0] - PIER), xy(BLOCK[0], FLIGHT_V[0] - PIER), xy(BLOCK[0], WALL_V[0])])
    asph = Polygon([xy(WALL_U - 6.0, WALL_V[0]), xy(WALL_U - 6.0, WALL_V[1] + 4.4), xy(WALL_U, WALL_V[1] + 4.4), xy(WALL_U, WALL_V[0])])
    return [lawn], [asph]
