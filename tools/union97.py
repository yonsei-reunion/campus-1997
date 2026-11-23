"""학생회관 남쪽 북동 찻길과 남동 모퉁이 (reference/고증/3.2-3.3 「학생회관 남쪽 찻길과 남동 모퉁이의 땅」, 2.10).

1997년 7월 원본 스캔(26/16 · 26/15 · 27/17 · 27/16)과 잎 없는 1996년 겨울 장에서 학생회관 남쪽에는 백주년기념관 북쪽에서
북동쪽으로 올라 학생회관 남동 모퉁이의 포장 마당에 닿는 찻길이 있다. 폭 6.8 m, 북쪽 가에 연석(밝은 줄), 그 안쪽에 길 따라
선 차 줄, 남쪽 가 흰 줄 너머로 길 따라 선 차 줄. 게임은 그 자리가 잔디 위의 보도(OSM)였고 땅이 사진보다 0.4 ~ 1.3 m 낮았다.
학생회관 남동 모퉁이에서 루스채플 남쪽 마당으로 이어지는 포장 마당도 사진이 게임보다 0.7 ~ 1.4 m 높다.

- 틀: 찻길의 줄 A -> B, s 는 그 줄을 따라(남서 -> 북동), o 는 그 왼쪽(북서쪽)
- PROF: 찻길의 높이(해발). 북쪽 연석 줄이 동서 코스 두 장에서 같은 자리에 오는 높이, 두 줄 사이 맨 아스팔트, 차 지붕 높이 − 1.15 m
  (s 32 ~ 60 은 차가 빽빽해 차 지붕과 맨 아스팔트를 함께 씀)
- SE: 남동 모퉁이 마당의 면(해발). 사진 서른여섯 점(1997년 7월, 비는 곳은 1996년 겨울)에 맞춘 평면, rms 0.19 m
- grade: 찻길 띠(BAND_O: 차가 걸친 5 m 칸의 마디까지)와 남동 마당의 마디를 그 높이로, 북쪽(학생회관 쪽) 둘레 RING m 의 남은
  마디를 매끈하게. 그보다 남쪽은 사진에서 게임보다 낮은 나무 띠 · 잔디라 손대지 않음(둑이 됨). 학생회관 발치 안쪽 1.5 m 까지만
  함께 올림
- 무작위 심기가 끝난 뒤의 늦은 블록에서 부른다. 찻길 위의 나무 · 관목 · 소품은 제자리에서 옮긴다(clear)

서쪽(reference/고증/3.2-3.3 「학생회관 바닥과 서쪽 앞마당」): 1997년 7월 원본 스캔과 1997 · 2009 · 2025년 사진에서 본동의
바닥(1층, 유리 벽과 현관)은 해발 36.6 m 이고 그 앞 서쪽 면을 따라 난간을 두른 덱이 있다. 덱 밑은 앞마당 높이의 낮은 층,
가운데에 앞마당(34.1 m)에서 덱으로 오르는 넓은 계단. 본동은 1층 위에 세 층(게임은 네 층이었다). 그 남쪽 앞마당은 백양로
동쪽 보도(30.9 m)에서 동쪽으로 오르는 포장 길로 이어진다.

- 틀: 본동의 1997년 외곽(사진 네 장의 지붕, 3.3)의 (u, v): 원점은 남쪽 동 남서 모서리 O97, u 북쪽 · v 동쪽. 본동 서쪽 면은 v 7.2
- FLOOR: 바닥(해발). DECK: 덱 앞 난간의 바깥 줄(v)과 덱의 남 · 북 끝(u), 난간 높이. STAIR: 계단의 가운데(u) · 폭 · 단 수 · 디딤판
- WEST_PTS: 앞마당 · 남쪽 앞마당의 높이(해발): 서쪽 × 동쪽 코스 짝 둘 넘게 0.4 m 안에서 맞는 점을 4 m 칸마다 모은 것.
  PATH: 보도에서 남쪽 앞마당으로 드는 길(x 를 따라 해발), 그 띠 PATH_Y
- west_grade: WEST_ZONE(덱 앞 앞마당 · 남쪽 앞마당 · 드는 길)의 마디를 그 높이로, 둘레 RING m 를 매끈하게(백양로의 보도 · 띠는 뺌)
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, unary_union

import datum

A = np.array([0.0, -172.0])
B = np.array([43.7, -116.0])
T = (B - A) / np.linalg.norm(B - A)
N = np.array([-T[1], T[0]])                   # (north-west, the side towards 학생회관)
ROAD_O = (-5.4, 1.4)                          # 남쪽 가(남쪽 차 줄의 뒤) .. 북쪽 연석
ROAD_S = (9.0, 68.0)                          # 남서 끝(그 너머는 백주년기념관 북쪽 길) .. 남동 마당
GRADE_S0 = 11.0                               # 여기부터 PROF 로(그 남서쪽 s 9 ~ 11 은 사진과 게임이 0.3 m 안: 둘레가 이음)
PROF = [(11.0, 33.25), (18.0, 33.75), (24.0, 34.25), (32.0, 34.45), (45.0, 35.0), (54.0, 35.55), (60.0, 35.75), (66.0, 36.0),
        (72.0, 36.15)]
SE_PLANE = (37.922, 0.02084, 0.02297)        # 해발 = c0 + c1 x + c2 y (남동 마당)
SE_BOX = (29.0, -127.0, 46.0, -94.0)          # (x0, y0, x1, y1): 그 마디들(학생회관 발치 안쪽 1.5 m 까지)
UNION = 1444448640
BAND_O = (-8.5, 3.6)                          # 고르는 마디: 남쪽 차 줄의 칸 너머 · 북쪽 차 줄의 칸 너머까지(차가 걸친 칸이 기울지 않게)
RING = 10.0


def so(s, o):
    return tuple(float(v) for v in A + T * s + N * o)


def sxy(X, Y):
    dx, dy = np.asarray(X) - A[0], np.asarray(Y) - A[1]
    return dx * T[0] + dy * T[1], dx * N[0] + dy * N[1]


def road():
    """찻길의 아스팔트(띠)"""
    return Polygon([so(ROAD_S[0], ROAD_O[0]), so(ROAD_S[1], ROAD_O[0]), so(ROAD_S[1], ROAD_O[1]), so(ROAD_S[0], ROAD_O[1])])


def prof_z(s):
    return np.interp(s, *zip(*PROF))


def se_z(x, y):
    return SE_PLANE[0] + SE_PLANE[1] * np.asarray(x) + SE_PLANE[2] * np.asarray(y)


def grade(Hn, X, Y, FIXED, union_fp, keep, fill):
    """찻길 띠(1 m 밖까지)와 남동 마당의 마디를 사진의 높이로(작업면), 북쪽 둘레 RING m 의 남은 마디를 매끈하게.
    union_fp: 학생회관의 외곽(그 안쪽 1.5 m 보다 깊은 마디는 그대로), keep: 그대로 둘 마디(다른 건물 발치).
    돌려주는 것: (정한 마디, 요약)"""
    s, o = sxy(X, Y)
    inner = shapely.contains_xy(union_fp.buffer(-1.5), X, Y)
    band = (s >= GRADE_S0) & (s <= ROAD_S[1] + 4.0) & (o >= BAND_O[0]) & (o <= BAND_O[1]) & ~keep & ~inner
    x0, y0, x1, y1 = SE_BOX
    se = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1) & ~band & ~keep & ~inner
    h0 = Hn.copy()
    zb = np.array([datum.up(x_, y_, float(prof_z(s_)), None) for x_, y_, s_ in zip(X[band], Y[band], s[band])])
    Hn[band] = zb
    zs = np.array([datum.up(x_, y_, float(se_z(x_, y_)), None) for x_, y_ in zip(X[se], Y[se])])
    Hn[se] = zs
    zone = band | se
    near = shapely.contains_xy(unary_union([road().buffer(RING), Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]).buffer(RING)]), X, Y)
    ring = near & ~zone & ~FIXED & ~keep & ~inner & (o >= BAND_O[0]) & (s >= 8.0)
    if ring.any():
        fill(ring)
    d = Hn - h0
    return zone | ring, dict(band=int(band.sum()), band_dz=(round(float(d[band].min()), 2), round(float(d[band].max()), 2)),
                             se=int(se.sum()), se_dz=(round(float(d[se].min()), 2), round(float(d[se].max()), 2)) if se.any() else 0,
                             ring=int(ring.sum()), ring_dz=(round(float(d[ring].min()), 2), round(float(d[ring].max()), 2)) if ring.any() else 0)


def paint():
    """땅 지도의 아스팔트: 찻길"""
    return [road()]


def clear(items, pad=0.5):
    """찻길 위(가에서 pad 안쪽까지)에 놓인 것(나무 · 관목 · 소품)을 목록의 제자리에서 찻길 밖 0.8 m 로. 돌려주는 것: [(차례, 전, 후)]"""
    rd = road()
    zone, edge = rd.buffer(pad), rd.buffer(0.8)
    moved = []
    for i_, t_ in enumerate(items):
        p_ = Point(t_[1], t_[2])
        if not zone.contains(p_):
            continue
        q_ = nearest_points(edge.exterior, p_)[0]
        moved.append((i_, (t_[1], t_[2]), (round(q_.x, 2), round(q_.y, 2))))
        t_[1], t_[2] = round(q_.x, 2), round(q_.y, 2)
    return moved


# ----------------------------------------------------------------------------- 서쪽: 바닥 · 덱 · 앞 계단 · 앞마당 · 드는 길
O97 = np.array([4.45, -110.95])                # 본동 · 남쪽 동의 1997년 외곽의 틀(3.3 「지붕 외곽선」): 남쪽 동 남서 모서리
U97 = np.array([6.01, 23.09]) / math.hypot(6.01, 23.09)
V97 = np.array([U97[1], -U97[0]])
FACE_V = 7.2                                   # 본동 서쪽 면(사진의 지붕 가, u 26.2 ~ 83.0)
FLOOR = 36.6                                   # 본동 바닥(해발): 덱 · 현관
BASE = FLOOR - 0.3                             # (blender/landmarks.py union: 바닥은 기단 윗면, 건물의 base 위 0.3 m)
STOREYS = dict(n=3, g=4.6, fh=3.9)             # 1층(유리 벽) 위 세 층(1997 · 2009 · 2025년 사진: 뾰족창 세 줄)
DECK = dict(v=0.9, u0=24.0, u1=84.0, parapet=0.7)   # 난간 바깥 줄 v(서쪽 면에서 6.3 m), 덱의 남 · 북 끝 u, 난간 높이
STAIR = dict(u=55.1, w=12.0, risers=18, tread=0.34, landing=0.4)   # 앞마당에서 덱으로: 가운데 u, 폭, 단 수, 디딤판
PLAZA_Z = 34.1                                 # 계단 발치의 앞마당(해발)
WEST_PTS = [(-8.5, -106.0, 32.29), (-9.5, -102.0, 32.33), (-10.6, -98.4, 32.22), (-10.6, -94.8, 32.25), (-6.2, -102.4, 32.44),
            (-7.2, -99.5, 32.39), (-2.2, -104.9, 32.55), (-2.2, -102.3, 32.70), (-3.0, -90.7, 32.39), (1.8, -102.2, 32.88),
            (1.3, -99.0, 32.38), (2.5, -94.0, 32.69), (5.4, -93.9, 32.64), (5.0, -90.2, 32.64), (5.0, -86.8, 32.76),
            (10.5, -79.8, 33.31), (8.5, -70.5, 33.12), (9.5, -66.1, 33.79), (10.1, -62.1, 34.04), (10.6, -59.0, 34.06),
            (9.8, -53.9, 33.91), (10.0, -51.5, 33.89), (9.6, -42.8, 34.01), (10.3, -38.6, 33.97), (10.6, -34.9, 33.92),
            (13.7, -66.0, 33.59), (13.4, -54.2, 34.11), (13.2, -50.8, 34.14), (13.9, -46.9, 34.32), (13.4, -42.3, 34.13),
            (13.6, -38.6, 34.14), (13.9, -34.5, 34.10), (14.4, -30.8, 34.11), (17.4, -46.9, 34.35), (17.0, -42.0, 34.01),
            (16.8, -38.4, 34.00), (17.6, -34.4, 33.87), (17.4, -31.0, 33.95), (21.0, -35.0, 33.88), (22.0, -30.5, 33.75)]
PATH = [(-24.0, 30.85), (-16.6, 31.7), (-9.0, 32.25)]   # (x, 해발): 보도 · 흰 차 XW 밑(지붕 32.9 m − 1.2 m) · 남쪽 앞마당 가
PATH_Y = (-112.5, -104.0)                      # 길의 두 가(양쪽 나무 화단의 연석)
RING_W = 10.0

# 외곽(reference/고증/3.2-3.3 「본동 · 남쪽 낮은 동 · 옥탑의 외곽과 높이」): 1997년 7월 원본 스캔 네 장(서쪽 코스 둘 · 동쪽 코스
# 둘)을 지붕 높이의 면에 다시 투영해, 네 장이 0.2 m 안에서 같은 자리에 놓는 가(갓돌 바깥 줄). 기울기가 반대인 두 코스가 함께
# 맞으므로 그 높이도 ±0.2 m. 높이는 해발. OSM 은 남쪽 동과 본동을 한 L 로 그려 본동이 3 ~ 4 m 좁고 서쪽으로 밀려 있었다
MAIN97 = dict(u=(26.5, 82.6), v=(7.45, 34.0))  # 본동(뾰족창 스크린의 갓돌, 53.4 m)
# 남쪽 낮은 동: 어두운 지붕(40.7 m)의 네 가. 그 남쪽 끝 u 1 ~ 8.4 는 덕트가 놓인 띠. 2008년 8월 로드뷰(2381266 · 2381269 ·
# 2381272)의 흰 칠 벽 두 층, 띠창 두 줄, 갓 밑 갈색 띠, 동쪽 끝의 철문(floor: 서쪽 앞마당 쪽 아래층 바닥)
SOUTH97 = dict(u=(1.0, 21.7), v=(0.9, 33.3), top=40.7, floor=33.2, storey=3.5)
# 남쪽 동과 본동 사이 낮은 이음 동: 본동 남쪽 면 앞 4.8 m. 지붕은 짝이 맞지 않아(본동 그늘 · 기울기에 가림) 남쪽 동이 그 위에
# 드리운 그림자의 폭(0.4 ~ 0.5 m)으로 어림한 38.7 m. 동쪽 찻길(36 ~ 36.5 m) 위 한 층
LINK97 = dict(u=(21.7, 26.5), v=(7.45, 33.3), top=38.7)
# 옥탑: 본동 지붕(판 52.5 m) 위 큰 상자 둘과 그 북쪽 계단실. 네 장이 그 높이의 면에서 같은 자리(56.1 m), 남쪽 반은 53.7 ~ 55.9 m
# 로 갈려 가운데 값
PENT97 = [dict(u=(51.4, 69.6), v=(9.0, 33.5), top=56.1), dict(u=(39.4, 51.4), v=(9.0, 33.5), top=54.6),
          dict(u=(69.6, 72.8), v=(15.8, 24.6), top=56.1)]
BAY97 = 0.99                                   # 스크린의 한 칸(2025년 정면: 57.5 칸이 57 m)


def uv97(u, v):
    return tuple(float(c) for c in O97 + U97 * u + V97 * v)


def to_uv97(x, y):
    dx, dy = np.asarray(x, float) - O97[0], np.asarray(y, float) - O97[1]
    return dx * U97[0] + dy * U97[1], dx * V97[0] + dy * V97[1]


def uv_box(u0, u1, v0, v1):
    return Polygon([uv97(u0, v0), uv97(u1, v0), uv97(u1, v1), uv97(u0, v1)])


def stair_foot_v():
    return DECK['v'] - STAIR['landing'] - (STAIR['risers'] - 1) * STAIR['tread']


def deck_poly():
    """덱(난간 바깥 줄에서 본동 서쪽 면 안쪽 3 m 까지)과 앞 계단(디딤판의 발치까지)"""
    hw = STAIR['w'] / 2 + 0.5
    return unary_union([uv_box(DECK['u0'], DECK['u1'], DECK['v'], FACE_V + 3.0),
                        uv_box(STAIR['u'] - hw, STAIR['u'] + hw, stair_foot_v(), DECK['v'] + 0.1)])


def path_poly():
    return Polygon([(PATH[0][0] - 1.5, PATH_Y[0]), (PATH[-1][0], PATH_Y[0]), (PATH[-1][0], PATH_Y[1]), (PATH[0][0] - 1.5, PATH_Y[1])])


def west_zone():
    """고르는 넓이: 덱 앞 앞마당(난간 바깥에서 21 m 까지 · 그 밑까지), 남쪽 앞마당, 드는 길"""
    plaza = uv_box(20.0, 86.0, FACE_V - 21.0, DECK['v'] + 1.0)
    fore = Polygon([(-12.5, -91.0), uv97(20.0, -3.0), uv97(20.0, -0.8), uv97(-1.0, -0.8), (-12.5, -112.5)])
    return unary_union([plaza, fore, path_poly()])


def path_z(x):
    return np.interp(x, [p[0] for p in PATH], [p[1] for p in PATH])


def west_z(X, Y):
    """앞마당 · 남쪽 앞마당 · 길의 높이(해발): 사진 점(WEST_PTS), 계단 발치의 줄, 길의 단면을 잇는 삼각형 면(밖은 가장 가까운 점)"""
    from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
    pts = list(WEST_PTS)
    fv = stair_foot_v() - 0.3
    for du in (-7.0, -3.5, 0.0, 3.5, 7.0):                       # (계단 발치: 앞마당의 높이)
        pts.append((*uv97(STAIR['u'] + du, fv), PLAZA_Z))
    for x in np.arange(PATH[0][0] - 1.5, PATH[-1][0] + 0.1, 2.5):
        for y in (PATH_Y[0] + 0.3, (PATH_Y[0] + PATH_Y[1]) / 2, PATH_Y[1] - 0.3):
            pts.append((float(x), y, float(path_z(x))))
    P = np.array(pts)
    lin = LinearNDInterpolator(P[:, :2], P[:, 2])
    near = NearestNDInterpolator(P[:, :2], P[:, 2])
    z = lin(np.asarray(X, float), np.asarray(Y, float))
    bad = ~np.isfinite(z)
    if np.any(bad):
        z = np.where(bad, near(np.asarray(X, float), np.asarray(Y, float)), z)
    return z


def west_grade(Hn, X, Y, FIXED, keep, fill, road_d, walk_out, road_half):
    """WEST_ZONE 의 마디(백양로의 보도 밖)를 사진의 높이로(작업면), 둘레 RING_W m 의 남은 마디(백양로의 보도 · 띠, 다른 건물 발치,
    정한 마디 밖)를 매끈하게. road_d: 백양로 중심선에서의 거리, walk_out · road_half: 보도의 바깥 가 · 띠의 바깥 가.
    돌려주는 것: (정한 마디, 요약)"""
    zone = shapely.contains_xy(west_zone(), X, Y) & (road_d > walk_out) & ~keep
    h0 = Hn.copy()
    zz = west_z(X[zone], Y[zone])
    Hn[zone] = [datum.up(x_, y_, float(z_), None) for x_, y_, z_ in zip(X[zone], Y[zone], zz)]
    ring = shapely.contains_xy(west_zone().buffer(RING_W), X, Y) & ~zone & ~FIXED & ~keep & (road_d > road_half + 0.5)
    if ring.any():
        fill(ring)
    d = Hn - h0
    return zone | ring, dict(zone=int(zone.sum()), zone_dz=(round(float(d[zone].min()), 2), round(float(d[zone].max()), 2)),
                             ring=int(ring.sum()), ring_dz=(round(float(d[ring].min()), 2), round(float(d[ring].max()), 2)) if ring.any() else 0)


def west_paint():
    """땅 지도의 포장(앞마당과 같은 보도 블록): 백양로 보도에서 남쪽 앞마당으로 드는 길"""
    return [path_poly()]


def west_clear(items, kind, pad=0.4):
    """덱 · 앞 계단 위(가에서 pad 밖까지)와 드는 길 위에 놓인 것: 나무는 목록 제자리에서 그 넓이 밖 0.8 m 로 옮기고
    (kind 'tree'), 관목은 뺀다. 소품은 계단 · 길 위의 것만 뺀다(덱 위의 것은 덱의 걷는 면에 선다: 공중전화 부스).
    돌려주는 것: 옮기거나 뺀 것"""
    hw = STAIR['w'] / 2 + 0.8
    stair = uv_box(STAIR['u'] - hw, STAIR['u'] + hw, stair_foot_v() - 0.8, DECK['v'])
    zone = unary_union([stair, path_poly().buffer(-0.2)] + ([] if kind == 'prop' else [deck_poly().buffer(pad)]))
    edge = zone.buffer(0.8)
    out = []
    if kind == 'tree':
        for i_, t_ in enumerate(items):
            p_ = Point(t_[1], t_[2])
            if zone.contains(p_):
                q_ = nearest_points(edge.boundary, p_)[0]
                out.append((i_, (t_[1], t_[2]), (round(q_.x, 2), round(q_.y, 2))))
                t_[1], t_[2] = round(q_.x, 2), round(q_.y, 2)
        return out
    out = [s for s in items if zone.contains(Point(s[1], s[2]))]
    items[:] = [s for s in items if not zone.contains(Point(s[1], s[2]))]
    return out


# 공중전화 부스 셋(build_campus.py: OSM 서쪽 면 가운데 3 m 밖)은 덱의 난간 줄 · 계단 머리에 걸려, 목록 제자리에서 앞마당의
# 백양로 쪽으로(앞이 백양로 쪽인 것은 그대로). 가운데가 2010년 12월 로드뷰 네 장(1016786013 ~ 016)으로 푼 부스 줄의 자리
# (-2.5, -76.5) ± 1.5 m. 그 전 자리(계단 남쪽 덱 앞벽 곁, u 44 ~ 47)는 1997년 7월 스캔에서 나무 두 그루의 화단
# (reference/고증/3.2-3.3 「학생회관 앞 공중전화 부스」)
PAYPHONES = [(32.79, -15.4), (31.59, -15.4), (30.39, -15.4)]


def west_payphones(props):
    """덱 · 계단 둘레(1 m 안)의 'payphone' 을 차례대로 PAYPHONES 로. 돌려주는 것: [(전, 후)]"""
    zone = deck_poly().buffer(1.0)
    free = [uv97(*q) for q in PAYPHONES]
    out = []
    for p_ in props:
        if p_[0] == 'payphone' and free and zone.contains(Point(p_[1], p_[2])):
            q = free.pop(0)
            out.append(((p_[1], p_[2]), (round(q[0], 2), round(q[1], 2))))
            p_[1], p_[2] = round(q[0], 2), round(q[1], 2)
    return out


def box_corners(u, v):
    """(u0, u1) x (v0, v1) 의 네 모서리(남서 · 북서 · 북동 · 남동), 캠퍼스 (x, y)"""
    return [list(uv97(u[0], v[0])), list(uv97(u[1], v[0])), list(uv97(u[1], v[1])), list(uv97(u[0], v[1]))]


def outline():
    """건물의 외곽(본동 · 이음 동 · 남쪽 동을 합친 것, 반시계): campus.json footprint(벽에 부딪히는 선)"""
    from shapely.geometry.polygon import orient
    p = unary_union([Polygon(box_corners(d['u'], d['v'])).buffer(0.01, join_style=2) for d in (MAIN97, LINK97, SOUTH97)])
    p = p.buffer(-0.01, join_style=2).simplify(0.05)
    return [[round(x, 2), round(y, 2)] for x, y in list(orient(p, 1.0).exterior.coords)[:-1]]


def landmark():
    """blender/landmarks.py union 이 쓰는 것(campus.json buildings[] 'union97'): 높이는 바닥에서의 m, 자리는 캠퍼스 (x, y)"""
    hw = STAIR['w'] / 2
    rel = lambda z: round(z - BASE, 2)                  # (해발 -> 건물 base(바닥 0.3 m 밑)에서의 높이)
    return dict(storeys=STOREYS, parapet=DECK['parapet'], bay=BAY97,
                main=box_corners(MAIN97['u'], MAIN97['v']),
                south=dict(c=box_corners(SOUTH97['u'], SOUTH97['v']), top=rel(SOUTH97['top']), floor=rel(SOUTH97['floor']),
                           storey=SOUTH97['storey']),
                link=dict(c=box_corners(LINK97['u'], LINK97['v']), top=rel(LINK97['top'])),
                pent=[dict(c=box_corners(d['u'], d['v']), top=rel(d['top'])) for d in PENT97],
                deck=[list(uv97(DECK['u0'], DECK['v'])), list(uv97(DECK['u1'], DECK['v']))],
                stair=dict(a=list(uv97(STAIR['u'] - hw, DECK['v'])), b=list(uv97(STAIR['u'] + hw, DECK['v'])),
                           risers=STAIR['risers'], tread=STAIR['tread'], landing=STAIR['landing']))
