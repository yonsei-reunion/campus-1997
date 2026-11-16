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
