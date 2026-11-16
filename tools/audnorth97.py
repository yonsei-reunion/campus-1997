"""대강당 북쪽 날개 둘레의 땅과 백양로 북쪽 끝 삼거리 (reference/고증/4.5.1 「북쪽 날개 둘레」, 2.8 「삼거리의 땅」).

1. 대강당 북쪽 날개 둘레 (grade): 1997년 7월 항공사진 원본 스캔에서 대강당 앞 윗단의 밝은 마당은 북쪽 날개의 서쪽 벽까지,
   날개 북쪽으로는 벽에서 5 ~ 6 m 띠(차 한 대가 섬)까지 한 높이로 이어진다(날개 서쪽 · 북쪽 열두 점이 윗단과 0.2 m 안,
   2006년 측량의 면도 0.3 m 안). 게임은 5 m 격자가 그 자리에서 3 ~ 4 m 꺼져 있었고 날개가 그 땅에 섰다. YARD 의 마디를
   윗단 높이로 고르고, 둘레 RING m 를 용재관의 평평한 땅 · 윗단 · 동쪽 마당 사이에 매끈하게 잇는다. 북쪽 날개는 땅을 읽어
   서므로(blender/landmarks.py auditorium 의 wings) 다음 landmarks 빌드에 윗단 위 두 층으로 선다.
   윗단 북쪽 끝(y 95.5) 너머의 길 · 잔디 섬은 이 grade 가 건드리지 않고(NORTH_KEEP) 아래 3(isle)이 맡는다.

2. 백양로 북쪽 끝 삼거리 (junction): 삼거리의 찻길 높이는 원본 스캔에서 백양로 단면(build_campus.py PROF_Q)대로인데
   (s 570 ~ 580 m 에서 38.2 ~ 38.5 m), 「삼거리에서 연희관까지」의 사진 점 하나(HILL_Q 의 (28, 128))가 미리보기로 재어
   0.45 m 낮아 그 둘레 격자가 찻길 메시보다 0.2 ~ 0.45 m 낮았다(메시 가장자리가 떠 보임). 찻길 띠의 마디를 단면 높이로
   올리고, 끝 계단(UW_STEPS) 발치 앞의 마디(계단 밑이라고 0.7 m 내렸던 것)를 발치 높이로 올린다.

3. 윗단 북쪽 끝 너머 (isle: reference/고증/4.5.1 「윗단 북쪽 끝 너머」, 3.13 「삼거리에서 대강당 쪽으로 가는 곁길」): 1997년 7월
   원본 스캔 네 장(26/15 · 26/16 · 27/16 · 27/17)에서 그곳은 윗단에서 삼거리로 내려가는 아스팔트 길(쐐기꼴), 그 동쪽의
   길쭉한 삼각 잔디 섬(남서쪽 가는 그늘진 낮은 옹벽, 북쪽 가는 동쪽 갈림길의 연석), 섬 동쪽 가를 따라 윗단 북동쪽 모퉁이의
   계단에서 동쪽 갈림길까지 가는 폭 3.3 ~ 3.6 m 의 밝은 포장 보도다. 게임은 지금 OSM 대로 섬이 서쪽(x 42 ~ 53)에, 그 동쪽에
   폭 6 m 의 아스팔트 길(living_street)이 있었다.
   - 땅: 섬 · 보도 · 길 위 5 m 격자 마디(ISLE_NODES)를 사진 높이로 고르고 둘레를 잇는다. 게임의 윗단이 사진보다 0.75 m
     낮으므로(4.5.1 「윗단과 백양로의 높이 차」) 사진 높이에서 그만큼을 빼되, 북쪽(동쪽 갈림길 · 삼거리: 사진과 게임이
     0.25 m 안)으로 가며 그 차를 줄인다(isle_off). 보도 동쪽의 진달래동산 비탈은 그대로
   - 칠(build_campus.py 의 늦은 칠): 섬은 잔디(옛 길의 아스팔트를 걷음), 길은 아스팔트, 보도와 계단 자리는 포장
   - 계단: 윗단 북동쪽 모퉁이에서 보도로 오르는 계단(ISLE_FLIGHT, blender/landmarks.py aud_north)
   - 무작위 심기가 끝난 뒤라 다른 곳의 나무 · 관목은 그대로이고, 새 포장 위에 놓인 관목만 제자리에서 옮긴다(isle_shrubs)

build_campus.py 가 무작위 심기 뒤에 부른다(나무 · 관목 · 차는 땅을 읽은 뒤). 높이는 그 자리의 땅(작업면)을 받아 쓴다.
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, unary_union

import datum

# 윗단이 이어지는 땅: 윗단의 동쪽 가(x 50) ~ 날개 서쪽 벽, 날개 밑, 날개 북쪽 띠(1997년 수관의 남쪽 가까지), 날개 동쪽 벽 앞 2.5 m.
# 남쪽 변은 대강당 북쪽 벽 안쪽(건물 밑)
YARD = Polygon([(50.0, 57.0), (50.0, 93.5), (54.5, 93.5), (58.0, 87.5), (63.0, 83.5), (68.0, 81.5), (86.0, 79.5), (86.0, 69.0),
                (83.0, 54.5), (59.0, 60.0)])
RING = 12.0
NORTH_KEEP = (57.0, 96.0)           # x 이 값보다 서쪽이고 y 이 값보다 북쪽인 마디는 그대로(윗단 북쪽 끝 너머의 길 · 섬)
# 포장: 윗단의 포장이 날개 서쪽 벽과 날개 북쪽 띠까지(윗단 쪽은 이미 포장된 곳과 겹침, 건물 밑은 build_campus.py 가 뺌).
# 날개 동쪽 마당(사진: 쌓아 둔 것들이 놓인 맨땅)은 그대로
PAVE = Polygon([(48.0, 57.5), (48.0, 93.5), (54.0, 93.5), (57.5, 87.5), (62.5, 83.5), (68.0, 81.0), (84.5, 79.2), (84.5, 71.0),
                (83.2, 70.2), (79.0, 56.0), (59.5, 60.0)])

JN_S0 = 559.0                       # 삼거리: 이 호 길이부터 찻길 끝까지
JN_HALF = 10.5                      # 중심선에서 이만큼(찻길 메시와 그 어귀)
JN_OVER = 0.0                       # 찻길 띠의 격자는 찻길 메시와 같은 높이(백양로의 hline 처럼: 높으면 노면 표시 0.012 m 를 덮음)
JN_FLAT_S = 576.0                   # 여기서 찻길 끝까지 단면을 끝 계단 발치 높이로 고르게
FOOT_U, FOOT_V = 9.0, (-2.5, 1.0)   # 끝 계단 발치 앞(UW_STEPS 틀: u 가로, v 계단 위쪽)


def grade(Hn, X, Y, FIXED, keep, bank, fill, z):
    """YARD 의 마디를 z(윗단의 작업면 높이)로, 둘레 RING m 를 매끈하게. keep: 건드리지 않을 마디(건물 발치 · 용재관의 평평한
    땅), bank: 앞 블록이 놓았지만 다시 이어도 되는 마디(용재관 둘레 비탈). 돌려주는 것: (정한 마디, 요약)"""
    zone = shapely.contains_xy(YARD, X, Y)
    ring = shapely.contains_xy(YARD.buffer(RING), X, Y) & ~zone & ~keep & ~((X < NORTH_KEEP[0]) & (Y > NORTH_KEEP[1]))
    free = ring & (~FIXED | bank)
    h0 = Hn.copy()
    Hn[zone] = z
    if free.any():
        fill(free)
    d = Hn - h0
    return zone | free, dict(z=round(float(z), 2), nodes=int(zone.sum()), lo=round(float(d[zone].min()), 2),
                             hi=round(float(d[zone].max()), 2), ring=int(free.sum()),
                             ring_lo=round(float(d[free].min()), 2) if free.any() else 0.0,
                             ring_hi=round(float(d[free].max()), 2) if free.any() else 0.0)


def junction(Hn, X, Y, s, d, prof_h, end_s, stu, stv, foot_z):
    """찻길 띠(중심선에서 JN_HALF, s JN_S0 ~ end_s)의 마디를 단면 높이 + JN_OVER 로 올리고(내리지는 않음), 끝 계단 발치 앞
    마디를 foot_z + JN_OVER 로 올린다. s, d: 마디의 호 길이와 중심선까지 거리. 돌려주는 것: (올린 마디, 요약)"""
    band = (d <= JN_HALF) & (s >= JN_S0) & (s <= end_s + 0.5)
    want = np.full(X.shape, -1e9)
    want[band] = np.array([prof_h(v) for v in s[band]]) + JN_OVER
    foot = (np.abs(stu) < FOOT_U) & (stv > FOOT_V[0]) & (stv < FOOT_V[1])
    want[foot] = np.maximum(want[foot], foot_z + JN_OVER)
    up = want > Hn + 1e-6
    h0 = Hn.copy()
    Hn[up] = want[up]
    dz = (Hn - h0)[up]
    return up, dict(nodes=int(up.sum()), lo=round(float(dz.min()), 2) if up.any() else 0.0,
                    hi=round(float(dz.max()), 2) if up.any() else 0.0,
                    at=[(float(x_), float(y_), round(float(v_), 2)) for x_, y_, v_ in zip(X[up], Y[up], dz)])


# ---------------------------------------------------------------------------------------------------------------------
# 3. 윗단 북쪽 끝 너머 (isle).  자리는 1997년 7월 원본 스캔 네 장을 그 자리의 사진 높이에 다시 투영해 읽은 것(네 장이 0.1 ~
# 0.2 m 안: 고증 4.5.1 「윗단 북쪽 끝 너머」)
# 섬의 남서쪽 가(그늘진 낮은 옹벽): 곧은 줄. 북서쪽 끝은 둥글게 북쪽 가(동쪽 갈림길의 연석)로 돌아 보도 서쪽 가에서 끝남
ISLE_KERB = [(52.54, 96.86), (43.62, 112.50)]
ISLE_NORTH = [(43.3, 114.2), (43.6, 115.2), (44.6, 116.9), (46.7, 118.6), (49.1, 119.9), (50.6, 120.4), (52.0, 121.0),
              (53.4, 121.5), (54.7, 122.2), (56.1, 122.9), (57.4, 123.6), (58.6, 124.5)]
ISLE_TIP = (61.48, 126.66)                          # (북쪽 가가 보도 서쪽 가와 만나는 곳)
# 보도의 두 가: x = a y + b (열다섯 · 열세 자리에 맞춘 곧은 줄, 잔차 rms 0.06 · 0.14 m)
WALK_W, WALK_E = (0.25354, 29.36788), (0.27255, 30.72928)
WALK_END = (64.2, 125.2)                            # (보도 동쪽 가의 북쪽 끝: 그 북쪽은 동쪽 갈림길의 아스팔트)
# 계단: 발치 가운데(섬의 남서쪽 가를 남동쪽으로 늘인 줄 위), 오르는 쪽(북동, 섬의 가에 직각), 폭(가 따라), 디딤판
ISLE_FLIGHT = dict(foot=(53.89, 93.54), up=(0.8687, 0.4955), width=4.4, tread=0.30, landing=0.6, maxrise=0.165)
ISLE_WALK_S = 41.2                                  # (보도 남쪽 끝, 계단 머리의 사진 높이 해발: 넷째 ~ 여섯째 점 40.9 ~ 41.25)
# 격자 마디: (x, y, 사진 높이 해발, 무엇). 사진 높이는 그 마디에서 짝 여섯을 따로 잰 중앙값(창 ±1.25 m, 상관 0.7 넘는 짝),
# 나무에 가린 마디는 둘레 점에서 이은 값(i), 보도 동쪽 가 마디는 보도 서쪽 가의 높이(동쪽 가는 무늬 없는 띠 끝이라 0.6 m
# 높게 읽힘)
ISLE_NODES = [(45, 100, 39.80, 'road'), (50, 100, 40.30, 'road'), (55, 100, 41.26, 'walk'),
              (45, 105, 40.00, 'road i'), (50, 105, 40.55, 'isle'), (55, 105, 41.39, 'isle'), (60, 105, 41.45, 'walk'),
              (45, 110, 39.55, 'road'), (50, 110, 41.08, 'isle'), (55, 110, 41.29, 'isle'), (60, 110, 41.50, 'walk'),
              (45, 115, 39.04, 'isle'), (50, 115, 40.30, 'isle i'), (55, 115, 41.20, 'isle i'), (60, 115, 41.55, 'walk'),
              (50, 120, 39.34, 'road'), (55, 120, 40.17, 'isle'), (60, 120, 41.58, 'walk'), (60, 125, 41.23, 'walk')]
ISLE_TERRACE = [(45, 95), (50, 95)]                 # (윗단의 북쪽 끝 줄: 윗단 높이 그대로)
ISLE_RING = 8.0


def walk_x(y, edge):
    a, b = edge
    return a * y + b


def isle_off(y):
    """사진 높이 − 게임 높이: 윗단(y 96 남쪽)에서 0.75 m, 동쪽 갈림길 · 삼거리 쪽(y 120 북쪽)에서 0.25 m, 그 사이는 곧게"""
    return 0.75 - 0.5 * min(1.0, max(0.0, (y - 96.0) / 24.0))


def isle_flight_n(z_top, z_foot):
    return int(math.ceil((z_top - z_foot) / ISLE_FLIGHT['maxrise'] - 0.1))


def isle_flight_poly(n):
    """계단(맨 위 쉼터까지)의 바닥 자리"""
    f, d, w = np.array(ISLE_FLIGHT['foot']), np.array(ISLE_FLIGHT['up']), ISLE_FLIGHT['width'] / 2
    a = np.array([-d[1], d[0]])
    run = ISLE_FLIGHT['landing'] + n * ISLE_FLIGHT['tread']
    return Polygon([tuple(f + a * w), tuple(f - a * w), tuple(f - a * w + d * run), tuple(f + a * w + d * run)])


def isle_geom(n):
    """(섬, 보도와 계단의 포장, 길의 아스팔트, 옛 길의 아스팔트를 걷을 곳). n: 계단의 챌판 수"""
    fl = isle_flight_poly(n)
    f, d = np.array(ISLE_FLIGHT['foot']), np.array(ISLE_FLIGHT['up'])
    a = np.array([-d[1], d[0]])
    nw = f + a * ISLE_FLIGHT['width'] / 2                           # (계단 북서쪽 옆: 섬의 남쪽 끝이 여기에 닿음)
    t = (walk_x(nw[1], WALK_W) - nw[0]) / (d[0] - WALK_W[0] * d[1])
    se = tuple(nw + d * t)                                          # (그 옆이 보도 서쪽 가와 만나는 곳)
    isle = Polygon([tuple(nw), ISLE_KERB[0], ISLE_KERB[1]] + ISLE_NORTH + [ISLE_TIP, se]).buffer(0)
    walk = Polygon([(walk_x(94.0, WALK_W), 94.0), ISLE_TIP, WALK_END, (walk_x(94.0, WALK_E), 94.0)])
    pave = unary_union([walk, fl]).difference(isle)
    box = Polygon([(42.0, 95.7), (52.75, 95.7), tuple(nw), se, ISLE_TIP, (56.0, 124.5), (40.0, 123.0), (40.0, 103.5), (41.6, 103.0),
                   (41.6, 99.0)])   # (x 40 - 41.6 north of y 103.5: the old island's west edge, the 삼거리's asphalt in 1997)
    road = box.difference(isle).difference(pave.buffer(0.05))
    return isle, pave, road


def isle_old_street(paths_out):
    """OSM 의 living_street 가운데 윗단 북쪽 끝(y 95.7) 너머 섬 동쪽으로 가던 토막: (그 줄, 폭). 게임의 아스팔트를 걷을 곳"""
    for p_ in paths_out:
        if p_['kind'] == 'living_street' and any(math.dist(q_[:2], (56.8, 107.5)) < 0.3 for q_ in p_['pts']):
            ln = LineString([q_[:2] for q_ in p_['pts']])
            cut = ln.intersection(Polygon([(40, 95.7), (70, 95.7), (70, 130), (40, 130)]))
            return cut, p_['w']
    return None, 0.0


def isle_grade(Hn, X, Y, FIXED, fill, z_terrace, n_flight, z_flight_foot):
    """ISLE_NODES 를 사진 높이 − isle_off 로(작업면), 윗단 북쪽 끝 줄을 윗단 높이로, 계단 밑 마디(55, 95)는 발치 높이 + 0.3 m
    (디딤판 밑), 둘레 ISLE_RING m 의 남은 마디를 매끈하게. 보도 동쪽 가 1 m 너머(진달래동산 비탈)와 x 41 서쪽(삼거리 ·
    백양로 둑)은 그대로. 돌려주는 것: (정한 마디, 요약)"""
    h0 = Hn.copy()
    zone = np.zeros(X.shape, bool)
    want = {}
    for x_, y_, zp_, _ in ISLE_NODES:
        want[(x_, y_)] = datum.up(x_, y_, zp_ - isle_off(y_), None)
    for x_, y_ in ISLE_TERRACE:
        want[(x_, y_)] = z_terrace
    want[(55, 95)] = z_flight_foot + 0.3
    for (x_, y_), z_ in want.items():
        k = (np.abs(X - x_) < 0.1) & (np.abs(Y - y_) < 0.1)
        assert k.sum() == 1, (x_, y_)
        Hn[k] = z_
        zone |= k
    near = np.zeros(X.shape, bool)
    for x_, y_ in want:
        near |= np.hypot(X - x_, Y - y_) <= ISLE_RING
    ring = near & ~zone & ~FIXED & (X >= 41.0) & (X <= WALK_E[0] * Y + WALK_E[1] + 1.0) & (Y <= 132.0)
    if ring.any():
        fill(ring)
    d = Hn - h0
    return zone | ring, dict(nodes=int(zone.sum()), lo=round(float(d[zone].min()), 2), hi=round(float(d[zone].max()), 2),
                            ring=int(ring.sum()), ring_lo=round(float(d[ring].min()), 2) if ring.any() else 0.0,
                            ring_hi=round(float(d[ring].max()), 2) if ring.any() else 0.0,
                            at=[(float(x_), float(y_), round(float(v_), 2)) for x_, y_, v_ in zip(X[zone | ring], Y[zone | ring], d[zone | ring])])


def isle_shrubs(shrubs, paved):
    """새 포장(보도 · 계단 · 길) 위에 놓인 관목을 목록의 제자리에서 포장 밖 0.7 m 로(가장 가까운 쪽: 섬이나 보도 동쪽 비탈).
    돌려주는 것: [(차례, 전 x, 전 y, 새 x, 새 y)]"""
    zone = paved.buffer(0.4)
    edge = paved.buffer(0.9)
    moved = []
    for i_, s_ in enumerate(shrubs):
        p_ = Point(s_[1], s_[2])
        if not zone.contains(p_):
            continue
        q_ = nearest_points(edge.exterior if edge.geom_type == 'Polygon' else edge.boundary, p_)[0]
        moved.append((i_, s_[1], s_[2], round(q_.x, 2), round(q_.y, 2)))
        s_[1], s_[2] = round(q_.x, 2), round(q_.y, 2)
    return moved


def isle_paths(paths, n_flight):
    """게임이 읽는 길(out['paths']: 지도 · 사람): 섬 위를 지나던 OSM 길 토막을 윗단 북쪽 끝에서 자르고, 1997년의 길 · 보도 ·
    계단을 더한다. 돌려주는 것: 바꾼 수"""
    isle, pave, road = isle_geom(n_flight)
    n = 0
    for p_ in list(paths):
        if len(p_['pts']) < 2:
            continue
        ls_ = LineString([q_[:2] for q_ in p_['pts']])
        if ls_.intersection(isle.buffer(-0.3)).length < 0.5:
            continue
        rest_ = ls_.difference(isle.buffer(0.2))
        pcs_ = [g_ for g_ in getattr(rest_, 'geoms', [rest_]) if g_.geom_type == 'LineString' and g_.length >= 2.0]
        if pcs_:
            p_['pts'] = [[round(x, 1), round(y, 1)] for x, y in max(pcs_, key=lambda g_: g_.length).coords]
        else:
            paths.remove(p_)
        n += 1
    f, d = np.array(ISLE_FLIGHT['foot']), np.array(ISLE_FLIGHT['up'])
    top = f + d * (ISLE_FLIGHT['landing'] + n_flight * ISLE_FLIGHT['tread'])
    mid = lambda y_: [round(0.5 * (walk_x(y_, WALK_W) + walk_x(y_, WALK_E)), 1), round(y_, 1)]
    paths += [dict(kind='service', w=6, pts=[[47.5, 96.5], [44.6, 105.0], [42.2, 113.0], [39.8, 121.9]]),
              dict(kind='steps', w=ISLE_FLIGHT['width'], pts=[[round(f[0], 1), round(f[1], 1)], [round(top[0], 1), round(top[1], 1)]]),
              dict(kind='footway', w=3.4, pts=[[round(top[0], 1), round(top[1], 1)], mid(100.0), mid(124.0)])]
    return n
