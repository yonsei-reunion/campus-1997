"""장기원 기념관의 몸체와 남쪽 끝 (reference/고증/3.15-3.17 「3.16」 「몸체의 외곽선과 남쪽 끝」).

1996년 겨울(잎이 진) 원본 스캔 26/15 · 26/16 을 몸체의 틀에서 난간 높이(45.2 m) 수평면으로 읽은 것:
- 몸체: 지붕 44.4 m(서쪽 단과 같은 높이), 그 가의 난간 0.9 m. 남쪽 끝이 처음 외곽선보다 3.7 m 남쪽, 북쪽 끝이 2.3 m 남쪽,
  서쪽 면이 1.45 m 서쪽이다(35.4 × 10.95 m). 처음에는 남쪽 끝의 지붕을 단으로 읽어 남쪽 벽 밖에 44 m 둔덕이 있었다
- 남쪽 면 앞: 원통 둘레 마당과 같은 높이의 화단(깊이 3.5 m), 그 남쪽 가에 낮은 옹벽, 그 아래 마당(1.1 ~ 1.4 m 아래).
  연세춘추 2007년 사진의 붉은 벽돌 옹벽(흰 갓) · 벽돌 기둥 사이 돌계단이 이것이다

동쪽 발치(「장기원 기념관 동쪽 발치의 띠와 도서관 뒤 길」, 1996년 겨울 · 1997년 7월 · 1998 · 1999년 원본 스캔):
- 동쪽 띠(화단 단): 동쪽 면에서 옹벽의 면(v 12.16, 도서관 틀 o −68.3)까지 7.4 m, 37.1 ~ 37.8 m(북쪽으로 오름, 1996년 96점의
  면). 남쪽 가는 s 4.8(u −22.7): 화단의 옹벽은 남동 모서리에서 북쪽으로 꺾여 거기까지, 띠의 남쪽 가 · 동쪽 가를 따라
  옹벽(1996년 겨울 네 장). 띠 위에 큰 나무 둘(1997년 7월 수관, 줄기는 1996년 겨울 네 장). 동쪽 면을 따라 포장 길.
  동쪽 문 맞은편 옹벽 발치의 7.5 × 2 m 덩이는 1997년 7월에만 있어(1996년 11 · 12월, 1998년 10월, 1999년 5월에 없음) 계단으로 넣지 않음
- 그 동쪽 길: 옹벽 발치에서 동쪽 연석(v 20.46, o −60)까지 8.3 m, 35.85 m 로 평평(113점, rms 0.12 m). 1996년 겨울 · 1999년
  봄에는 양쪽 가에 길 따라 선 차, 1997년 7월 28일에는 빈 길. 남쪽 끝이 옹벽 아래 마당으로 이어짐
- 연석 동쪽: 상록 관목 줄과 둑(v 22.96, o −57.5)이 도서관 서쪽 길(33.2 m)로 내려감

틀: 원점 C(처음 외곽선의 가운데), u 는 몸체를 따라 북북동(중앙도서관의 긴 축), v 는 가로질러 동쪽.
5 m 격자로는 옹벽이 한 칸의 비탈이 되므로, 옹벽이 지나는 칸의 화단 쪽 마디를 마당 높이로 내리고 화단 · 마당을 그 위의
판(build_campus.py dwb_deck)으로 덮은 뒤 옹벽 · 기둥 · 계단을 면으로 세운다(tools/audnorth97.py isle_wall_* 와 같은 꼴).
동쪽 띠는 너비가 칸보다 좁아 띠의 마디를 모두 길 높이로 내리고 띠 전체를 판으로, 길은 연석 동쪽 둑이 칸 하나의 비탈이
되지 않게 길의 마디를 둑 발치 높이로 내리고 길 · 둑을 둘째 판(LOW)으로 덮는다.

    took, cells, polys, hfuns, info = jk97.grade(Hn, X, Y, halls)   # 맨 끝(JK_SW97 뒤): 땅을 읽은 것이 모두 끝난 뒤
    deck = dwb_deck(cells, polys['raised'], hfuns['raised'])        # build_campus (길: 'low')
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
# 동쪽 발치
EAST_V = 12.16                              # 동쪽 띠의 가 = 동쪽 옹벽의 면(턱의 가운데 o −68.4 · −67.4, 남쪽 반을 씀)
BAND_S_U = -22.7                            # 동쪽 띠의 남쪽 가(s 4.8): 화단의 옹벽은 남동 모서리(WALL_V[1])에서 북쪽으로 꺾여 여기까지
CURB_V = 20.46                              # 길의 동쪽 연석(1997년 7월 26/15 · 26/16 의 곧은 검은 줄)
BANK_V = 22.96                              # 연석 동쪽 둑의 발치(도서관 서쪽 길의 높이: tools/libwest97.py)
WALL_N = 26.0                               # 동쪽 옹벽을 그리는 북쪽 끝(띠와 길의 차가 0.12 m 밑인 곳은 그리지 않음)
BAND_DOWN_U = BLOCK[1]                      # 띠의 판 밑 마디를 내리는 북쪽 끝(몸체 북쪽 끝)
LANE_DOWN_U = (-29.0, 24.0)                 # 길의 판 밑 마디를 내리는 남쪽 · 북쪽 끝
SET_U = (-36.0, 28.0)                       # 그 밖에서 마디를 길 · 띠 · 북쪽 땅의 높이로 놓는 끝
NORTH_Z = (40.0, 0.1)                       # 몸체 북쪽 끝 너머 서쪽 땅: v 1.5 에서 40.0 m, 서쪽으로 1 m 에 0.1 m(1996년 겨울 39.4 ~ 41.5 m)
WALK_W = 2.0                                # 동쪽 면을 따라 띠 위의 포장 길(연세춘추 2007년 사진: 계단 위에서 동쪽 면을 따라 북쪽으로)
# 띠 위 큰 나무 둘(1997년 7월 수관 o −79 ~ −66, s 5 ~ 32): 1996년 겨울 네 장(26/15 · 26/16 = 12월 23일, 27/16 · 27/17 =
# 11월 28일)의 줄기 · 줄기 그림자를 띠의 면에 맞대어 읽은 밑동(다섯 줄의 최소제곱, rms 0.3 m, 두 코스 사이 0.3 ~ 0.8 m).
# 수종은 못 가려 느티나무로, 크기는 1997년 수관(반지름 6.5 ~ 7 m)에 맞춤: (u, v, 크기, 돌림)
EAST_TREES = ((-14.85, 8.8, 1.15, 1.9), (-1.4, 8.45, 1.15, 4.4))


def _uv(x, y):
    d = np.stack(np.broadcast_arrays(np.asarray(x, float) - C[0], np.asarray(y, float) - C[1]), -1)
    return d @ U, d @ V


def band_h(x, y):
    """동쪽 띠의 면(해발): 1996년 겨울 원본 스캔 26/15 · 26/16 의 96점(rms 0.28 m)"""
    u, v = _uv(x, y)
    return 37.650 + 0.0156 * u - 0.0334 * v


def lane_h(x, y):
    """띠 동쪽 길의 면(해발): 1996년 겨울 113점(rms 0.12 m). 1998년 35.81, 1999년 35.94 m"""
    u, v = _uv(x, y)
    return 35.85 - 0.0134 * (v - 16.96)


def raised_h(x, y):
    """옹벽 위(화단 · 동쪽 띠 · 몸체 북쪽 끝 너머)의 면(해발). 화단은 원통 둘레 마당의 면(court_h), 동쪽 띠는 band_h, 그 사이는
    화단에서 3 m 안에서 잇고, 몸체 북쪽 끝 너머는 v 4.5 에서 서쪽으로 3 m 안에 그 서쪽 땅(NORTH_Z)으로"""
    u, v = _uv(x, y)
    z = band_h(x, y)
    d = np.hypot(np.maximum(v - WALL_V[1], 0.0), np.maximum(u - BLOCK[0], 0.0))
    z = np.where((u < BLOCK[0] + 3.0) & (v < WALL_V[1] + 3.0), z + (court_h(x, y) - z) * np.clip(1.0 - d / 3.0, 0, 1), z)
    zn = NORTH_Z[0] + NORTH_Z[1] * np.maximum(1.5 - v, 0.0)
    z = np.where(u > BLOCK[1], z + (zn - z) * np.clip((4.5 - v) / 3.0, 0, 1), z)
    return z


def low_h(x, y, foot):
    """길 · 둑 · 남쪽 옹벽 아래 마당의 동쪽(해발). foot(u): 둑 발치의 높이(해발). 마당은 화단 동쪽 모서리 v 3.85 의 YARD_Z 에서
    길 쪽으로 이음"""
    u, v = _uv(x, y)
    z = lane_h(x, y)
    z = np.where(u < BAND_S_U, z + (YARD_Z - z) * np.clip((EAST_V - v) / (EAST_V - WALL_V[1]), 0, 1), z)
    return np.where(v > CURB_V, z + (foot(u) - z) * np.clip((v - CURB_V) / (BANK_V - CURB_V), 0, 1), z)


def _bil(H, x, y, step=5.0, half_=800.0):
    fx, fy = (np.asarray(x, float) + half_) / step, (np.asarray(y, float) + half_) / step
    i, j = np.floor(fx).astype(int), np.floor(fy).astype(int)
    ax, ay = fx - i, fy - j
    return H[j, i] * (1 - ax) * (1 - ay) + H[j, i + 1] * ax * (1 - ay) + H[j + 1, i] * (1 - ax) * ay + H[j + 1, i + 1] * ax * ay


def xy(u, v):
    p = C + U * u + V * v
    return float(p[0]), float(p[1])


def xya(u, v):
    """xy 의 배열판"""
    u, v = np.asarray(u, float), np.asarray(v, float)
    return C[0] + U[0] * u + V[0] * v, C[1] + U[1] * u + V[1] * v


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
    """남쪽 면 앞 화단(옹벽 위)과 옹벽 둘레: 연석을 두지 않는 곳(옹벽이 가)"""
    return unary_union([Polygon([xy(WALL_U, WALL_V[0]), xy(WALL_U, WALL_V[1]), xy(BLOCK[0], WALL_V[1]), xy(BLOCK[0], WALL_V[0])]),
                        LineString([xy(*q) for q in east_line()]).buffer(0.4)])


def wall_line():
    """처음의 옹벽의 면: 서쪽 끝 -> 남동 모서리 -> 남쪽 면(화단이 왼쪽). 화단 밑 마디를 내리는 칸은 이것으로 고른다"""
    return [(WALL_U, WALL_V[0]), (WALL_U, WALL_V[1]), (BLOCK[0], WALL_V[1])]


def east_line():
    """옹벽의 면(지금): 서쪽 끝 -> 화단의 남동 모서리 -> 북쪽으로 띠의 남쪽 가 -> 동쪽으로 띠의 가까지 -> 북쪽으로 꺾여 띠의
    가(옹벽 위가 왼쪽)"""
    return [(WALL_U, WALL_V[0]), (WALL_U, WALL_V[1]), (BAND_S_U, WALL_V[1]), (BAND_S_U, EAST_V), (WALL_N, EAST_V)]


def _box(u0, u1, v0, v1):
    return Polygon([xy(u0, v0), xy(u0, v1), xy(u1, v1), xy(u1, v0)])


def raised_region():
    """옹벽 위: 화단(처음의 _raised)과 동쪽 띠, 몸체 북쪽 끝 너머(판 칸이 닿는 곳까지)"""
    return unary_union([_raised(), _box(BAND_S_U, 40.0, -12.0, EAST_V)])


def low_region():
    """옹벽 아래 판(LOW): 남쪽 옹벽 아래 마당의 화단 동쪽 모서리 동쪽, 띠 동쪽 길, 연석 동쪽 둑(발치까지)"""
    return _box(-45.0, 40.0, WALL_V[1], BANK_V).difference(raised_region())


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
    # 동쪽 발치: 띠의 마디(몸체 북쪽 끝까지)는 길 높이 조금 밑으로, 길 · 둑의 마디는 둑 발치 동쪽 땅(도서관 서쪽 길)의 높이로
    # 내리고 판 둘로 덮는다. 몸체 안 동쪽 반의 마디는 띠의 판 밑으로(벽 곁의 땅이 판 위로 솟지 않게)
    Du, Dv = d_ @ U, d_ @ V
    tl = datum.tilt(X, Y)
    inh = shapely.contains_xy(hb, X, Y)
    band = (Du >= BAND_S_U) & (Du <= BAND_DOWN_U) & (Dv >= WALL_V[1]) & (Dv < EAST_V) & ~inh & ~down
    Hn[band] = lane_h(X[band], Y[band]) - 0.1 + tl[band]
    clamp = inh & (Du > BLOCK[0]) & (Du < BLOCK[1]) & (Dv > 0.0)
    Hn[clamp] = np.minimum(Hn[clamp], raised_h(X[clamp], Y[clamp]) - 0.3 + tl[clamp])
    foot0 = lambda u: _bil(h0, *xya(u, BANK_V + 2.0)) - datum.tilt(*xya(u, BANK_V + 2.0))  # (해발: the road's side, before)
    lane = (Du >= LANE_DOWN_U[0]) & (Du <= LANE_DOWN_U[1]) & (Dv >= EAST_V) & (Dv <= BANK_V) & ~inh
    for j_, i_ in zip(*np.nonzero(lane)):
        Hn[j_, i_] = foot0(Du[j_, i_]) - 0.05 + tl[j_, i_]
    # (beyond the decks, the ground itself on the surfaces: the yard east of the bed, the lane, the band and the ground west
    # of it past the block's north end)
    near = (Du >= SET_U[0]) & (Du <= SET_U[1]) & ~inh & ~down & ~band & ~lane
    yd = near & (Du < BAND_S_U) & (Dv >= WALL_V[1]) & (Dv < EAST_V)
    ln_ = near & (Dv >= EAST_V) & (Dv <= CURB_V)
    nb = near & (Du > BAND_DOWN_U) & (Dv >= -9.0) & (Dv < EAST_V)
    Hn[yd] = low_h(X[yd], Y[yd], foot0) + tl[yd]
    Hn[ln_] = lane_h(X[ln_], Y[ln_]) + tl[ln_]
    Hn[nb] = raised_h(X[nb], Y[nb]) + tl[nb]
    took = down | band | lane | clamp | yd | ln_ | nb
    foot = lambda u: _bil(Hn, *xya(u, BANK_V)) - datum.tilt(*xya(u, BANK_V))                # (해발: the bank's foot, now)
    hw = lambda x, y: float(raised_h(x, y)) + float(datum.tilt(x, y))
    hl = lambda x, y: float(low_h(x, y, lambda u: float(foot(u)))) + float(datum.tilt(x, y))
    jj, ii = np.nonzero(down | band | lane)
    deck_cells = {(j + a, i + b) for j, i in zip(jj, ii) for a in (-1, 0) for b in (-1, 0)}
    # (the flight: from the bed at its head down to the yard)
    xf, yf = xy(WALL_U - 0.3, sum(FLIGHT_V) / 2)
    zf = _bil(Hn, xf, yf, step, half_)
    _N[0] = flight_n(hw(*xy(WALL_U + 2.0, sum(FLIGHT_V) / 2)), float(zf))
    cu = unary_union([shapely.geometry.box(-half_ + i * step, -half_ + j * step, -half_ + (i + 1) * step, -half_ + (j + 1) * step)
                      for j, i in deck_cells])
    keep = lambda p: unary_union([g for g in getattr(p, 'geoms', [p]) if g.geom_type == 'Polygon' and g.area > 0.05])
    poly = keep(cu.intersection(raised_region()).difference(hb.buffer(0.02)).difference(_notch(_N[0])))
    lpoly = keep(cu.intersection(low_region()).difference(hb.buffer(0.02)))
    d = Hn - h0
    q = lambda m: [(float(x_), float(y_), round(float(v_), 2)) for x_, y_, v_ in zip(X[m], Y[m], d[m])]
    info = dict(yard=q(yard), down=q(down), band=q(band), lane=q(lane), clamp=q(clamp), set=q(yd | ln_ | nb),
                deck_cells=len(deck_cells), deck_m2=round(poly.area, 1), low_m2=round(lpoly.area, 1), risers=_N[0])
    return took, deck_cells, dict(raised=poly, low=lpoly), dict(raised=hw, low=hl), info


_CORNERS = ((WALL_U, WALL_V[1]), (BAND_S_U, WALL_V[1]), (BAND_S_U, EAST_V))


def _inside(u, v):
    """옹벽 위 판 안쪽으로 조금 들인 자리(모서리에서 판의 가에 걸리지 않게): 화단(띠의 남쪽 가 남쪽)은 v WALL_V[1] 안, 띠는 EAST_V 안"""
    u = max(u, WALL_U + 0.06)
    v = min(v, EAST_V - 0.06)
    return (u, min(v, WALL_V[1] - 0.06)) if u < BAND_S_U + 0.04 else (u, v)


def walls(top, foot, step=0.5):
    """붉은 벽돌 옹벽(흰 갓), 계단 양쪽 벽돌 기둥, 돌계단: [재질, 네 점], 막을 곳(다각형), 걷는 면(계단의 비탈).
    top(x, y): 화단의 윗면(판 밖은 땅), foot(x, y): 땅(작업면)"""
    quads, guards, walk = [], [], []
    R = lambda p, z: [round(float(p[0]), 3), round(float(p[1]), 3), round(float(z), 3)]
    n = _N[0]
    f0, f1 = FLIGHT_V
    runs = [[(WALL_U, WALL_V[0]), (WALL_U, f0 - PIER)],                       # 서쪽 끝 -> 서쪽 기둥
            [(WALL_U, WALL_V[1]), (BAND_S_U, WALL_V[1])],                     # 동쪽 기둥(화단의 남동 모서리) -> 북쪽으로 띠의 남쪽 가
            [(BAND_S_U, WALL_V[1]), (BAND_S_U, EAST_V)],                      # -> 띠의 남쪽 가를 따라 동쪽으로
            [(BAND_S_U, EAST_V), (WALL_N, EAST_V)]]                           # -> 띠의 동쪽 가를 따라 북쪽으로
    for run in runs:
        (ua, va), (ub, vb) = run
        L = math.hypot(ub - ua, vb - va)
        k_n = max(1, int(math.ceil(L / step)))
        tu, tv = (ub - ua) / L, (vb - va) / L
        nu, nv = tv, -tu                              # (towards the bed: (u north, v east), left of the run)
        S = [(ua + (ub - ua) * k / k_n, va + (vb - va) * k / k_n) for k in range(k_n + 1)]
        k_n = len(S) - 1
        # (the top sampled just inside the raised side: at the corner the point on the run lies on the deck's edge)
        zt = [top(*xy(*_inside(u + nu * 0.05, v + nv * 0.05))) for u, v in S]
        zb = [foot(*xy(u - nu * 0.1, v - nv * 0.1)) - 0.05 for u, v in S]
        on = [max(zt[k] - zb[k], zt[k + 1] - zb[k + 1]) >= 0.12 for k in range(k_n)]
        for k in range(k_n):
            if not on[k]:
                continue
            for e, last in ((0, k == 0 or not on[k - 1]), (1, k == k_n - 1 or not on[k + 1])):
                (ue, ve) = S[k + e]
                if not last or zt[k + e] - zb[k + e] < 0.3 or (ue, ve) in _CORNERS + ((WALL_U, f0 - PIER), (WALL_U, f1 + PIER)):
                    continue
                # (a wall that stops at full height: its end closed, the brick and the coping's end, both ways round)
                a_, b_ = xy(ue - nu * COPE_O, ve - nv * COPE_O), xy(ue + nu * (WALL_T + COPE_O), ve + nv * (WALL_T + COPE_O))
                we = zt[k + e] + WALL_H
                for q in ([R(a_, zb[k + e]), R(b_, zb[k + e]), R(b_, we), R(a_, we)], [R(a_, we), R(b_, we), R(b_, we + COPE_T), R(a_, we + COPE_T)]):
                    quads.append(['brick_red' if q[0][2] < we - 1e-6 else 'stone_white', q])
                    quads.append(['brick_red' if q[0][2] < we - 1e-6 else 'stone_white', [list(c) for c in q[::-1]]])   # (own points: datum moves each once)
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


LANE_PAINT_U = (-36.0, 28.0)                 # 길 · 띠를 칠하는 남쪽 · 북쪽 끝(그 밖은 그대로)


def east_paint():
    """동쪽 발치의 (지울 곳, 아스팔트, 포장): 지금 지도의 보도 · 계단과 그 둘레 포장을 띠 · 길 · 둑에서 지우고(잔디), 길과 남쪽
    옹벽 아래 마당의 동쪽을 아스팔트로, 동쪽 면을 따라 띠 위의 길(WALK_W)을 포장으로"""
    u0, u1 = LANE_PAINT_U
    clear = [_box(WALL_U, u1, BLOCK[3] - 0.3, EAST_V + 0.3), _box(u0, u1, EAST_V, BANK_V + 0.3),
             _box(WALL_U - 6.0, WALL_U, WALL_V[1] + 4.4, EAST_V)]
    asph = [_box(u0, u1, EAST_V, CURB_V), _box(WALL_U - 6.0, WALL_U, WALL_V[1] + 4.4, EAST_V), _box(WALL_U, BAND_S_U, WALL_V[1], EAST_V)]
    pave = [_box(BAND_S_U, BLOCK[1], BLOCK[3] - 0.3, BLOCK[3] + WALK_W)]
    return clear, asph, pave


def east_paths(paths):
    """게임이 읽는 길(campus.json paths: 작은 지도 · 걷는 사람들)에서 띠 · 길 · 둑 위의 지금 지도 보도 · 계단을 빼고(목록 제자리에
    가장 긴 남은 토막, 2 m 밑이면 뺌), 길(찻길)과 띠 위의 포장 길을 끝에 더함. 돌려주는 것: (자른 수, 뺀 수)"""
    zone = unary_union(east_paint()[0])
    cut = gone = 0
    for p in list(paths):
        if p['kind'] not in ('footway', 'path', 'pedestrian', 'steps') or len(p['pts']) < 2:
            continue
        ln = LineString(p['pts'])
        if not ln.intersects(zone):
            continue
        rest = ln.difference(zone)
        rest = max(getattr(rest, 'geoms', [rest]), key=lambda g: g.length, default=None) if not rest.is_empty else None
        if rest is None or rest.length < 2.0:
            paths[:] = [q for q in paths if q is not p]
            gone += 1
        else:
            p['pts'] = [[round(x, 1), round(y, 1)] for x, y in rest.coords]
            cut += 1
    vm = (EAST_V + CURB_V) / 2
    paths.append(dict(kind='service', w=round(CURB_V - EAST_V, 1),
                      pts=[[round(c, 1) for c in xy(u, vm)] for u in (LANE_PAINT_U[0], LANE_PAINT_U[1])]))
    paths.append(dict(kind='footway', w=WALK_W, pts=[[round(c, 1) for c in xy(u, BLOCK[3] + WALK_W / 2)] for u in (BAND_S_U, BLOCK[1])]))
    return cut, gone


def east_decals(decals):
    """지금 지도의 보도 위에 놓였던 얼룩 · 금(campus.json decals)이 띠 · 둑의 잔디에 남은 것: 길 위로(목록 제자리). 돌려주는 것: 옮긴 수"""
    n = 0
    for d in decals:
        u, v = uv(d[1], d[2])
        if LANE_PAINT_U[0] <= u <= LANE_PAINT_U[1] and (BLOCK[3] + WALK_W <= v < EAST_V or CURB_V <= v < BANK_V):
            d[1], d[2] = (round(c, 2) for c in xy(u, (EAST_V + CURB_V) / 2))
            n += 1
    return n


def east_clear(items, kind):
    """띠 위 · 길 위의 나무 · 관목(목록 제자리): 길 위의 것은 둑(연석 동쪽 1 m)으로, 옹벽에 걸린 것은 띠 쪽으로 비킴.
    items: campus.json 의 trees / shrubs([종, x, y, ...]). 돌려주는 것: 옮긴 수"""
    n = 0
    for t in items:
        u, v = uv(t[1], t[2])
        if not (LANE_PAINT_U[0] <= u <= LANE_PAINT_U[1]):
            continue
        if EAST_V - 0.8 <= v < CURB_V + 0.8:
            v2 = CURB_V + 1.0 if v > EAST_V + 1.5 else EAST_V - 1.2
            t[1], t[2] = (round(c, 2) for c in xy(u, v2))
            n += 1
    return n


def east_trees():
    """띠 위 큰 나무(EAST_TREES)의 campus.json trees 항목. 나무 목록의 맨 끝에 붙인다(웹은 목록 차례로 모델을 고름)"""
    return [['zelkova', *(round(c, 2) for c in xy(u, v)), sc, rot] for u, v, sc, rot in EAST_TREES]
