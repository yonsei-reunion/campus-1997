"""중앙도서관 남쪽 화단의 땅 (reference/고증/2.3.4 「도서관 남쪽 화단」).

도서관 남쪽 길에서 화단 남쪽 끝 줄까지, 차가 선 서쪽 길에서 화단 바깥 길(백양로 쪽)까지의 땅. 게임은 도서관 발치와 그 둘레
땅 사이를 매끈하게 이은 면(build_campus.py 「중앙도서관」의 harmonic_fill)이라 서쪽으로 1.1 ~ 1.4 m 내려갔으나, 1997년 7월
항공사진 원본 스캔은 화단이 북쪽(도서관 쪽)으로 4 %, 서쪽으로 2.2 % 오르는 고른 면이고(91점, 면에서 rms 0.30 m) 2006년
측량의 면도 동서로 평평하다. 사진의 그 면을 놓되, 높이는 둘레에 이미 놓인 도서관 남쪽 발치 · 화단 바깥 길(3.2.1: 사진의
높이보다 0.5 ~ 0.6 m 낮게 놓인 것)에 맞춘다: 그 마디들에서 (게임 − 사진의 면)의 중앙값만큼 면 전체를 옮김.

build_campus.py 가 무작위 심기 뒤에(나무 · 관목 · 차는 땅을 읽은 뒤) grade 를 부른다. 높이는 해발로 적고 작업면으로 올린다.
"""
import numpy as np

import datum

O = np.array([-85.44, -71.08])          # 도서관 정면 틀(build_campus.py _lf0): 백양로 쪽 정면의 남동 모서리
T = np.array([0.25441, 0.9671])          # s: 정면을 따라 북쪽
N = np.array([0.9671, -0.25441])         # o: 정면에서 밖으로(동쪽, 백양로 쪽)
PLANE = (33.83, 0.0396, -0.0221)         # 사진의 면(해발): a + b·s + c·o
ZONE = (-51.0, -15.0, -22.0, 41.0)       # s0, s1, o0, o1: 화단 남쪽 끝 줄 ~ 도서관 남쪽 길, 서쪽 길 ~ 화단 바깥 길 안쪽
RING = 12.0                              # 둘레에 이만큼 매끈하게 이음(harmonic_fill)
ANCHOR = 6.0                             # 높이를 맞출 둘레의 고정 마디: 구역에서 이만큼 안


def sxy(X, Y):
    return (X - O[0]) * T[0] + (Y - O[1]) * T[1], (X - O[0]) * N[0] + (Y - O[1]) * N[1]


def plane(X, Y):
    """사진의 면(해발)"""
    s, o = sxy(X, Y)
    return PLANE[0] + PLANE[1] * s + PLANE[2] * o


def grade(Hn, X, Y, FIXED, keep, fill):
    """구역의 마디를 사진의 면(둘레 고정 마디에 맞춘 높이)으로, 둘레 RING m 의 자유 마디를 매끈하게.
    keep: 건드리지 않을 마디(건물 발치). 돌려주는 것: (옮긴 마디, 요약)"""
    s, o = sxy(X, Y)
    s0, s1, o0, o1 = ZONE
    box = lambda m: (s >= s0 - m) & (s <= s1 + m) & (o >= o0 - m) & (o <= o1 + m)
    inside = box(0.0)
    zone = inside & ~FIXED & ~keep
    work = plane(X, Y) + datum.tilt(X, Y)
    near = box(ANCHOR) & ~inside & FIXED & ~keep
    dz = float(np.median((Hn - work)[near])) if near.any() else 0.0
    q = np.percentile((Hn - work)[near], [10, 90]) if near.any() else (0.0, 0.0)
    H0 = Hn.copy()
    Hn[zone] = work[zone] + dz
    ring = box(RING) & ~inside & ~FIXED & ~keep
    if ring.any():
        fill(ring)
    d = Hn - H0
    return zone, dict(nodes=int(zone.sum()), ring=int(ring.sum()), anchors=int(near.sum()), dz=round(dz, 2), dz_10_90=[round(float(v), 2) for v in q],
                      lo=round(float(d[zone].min()), 2), hi=round(float(d[zone].max()), 2),
                      ring_lo=round(float(d[ring].min()), 2) if ring.any() else 0.0,
                      ring_hi=round(float(d[ring].max()), 2) if ring.any() else 0.0)
