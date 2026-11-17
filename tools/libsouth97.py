"""중앙도서관 남쪽 화단의 땅 (reference/고증/2.3.4 「도서관 남쪽 화단」).

도서관 남쪽 길에서 화단 남쪽 끝 줄까지, 차가 선 서쪽 길에서 화단 바깥 길(백양로 쪽)까지의 땅. 게임은 도서관 발치와 그 둘레
땅 사이를 매끈하게 이은 면(build_campus.py 「중앙도서관」의 harmonic_fill)이라 서쪽으로 1.1 ~ 1.4 m 내려갔으나, 1997년 7월
항공사진 원본 스캔은 화단이 북쪽(도서관 쪽)으로 4 %, 서쪽으로 2.2 % 오르는 고른 면이고(91점, 면에서 rms 0.30 m) 2006년
측량의 면도 동서로 평평하다. 사진의 그 면을 놓되, 높이는 둘레에 이미 놓인 도서관 남쪽 발치 · 화단 바깥 길(3.2.1: 사진의
높이보다 0.5 ~ 0.6 m 낮게 놓인 것)에 맞춘다: 그 마디들에서 (게임 − 사진의 면)의 중앙값만큼 면 전체를 옮김.

build_campus.py 가 무작위 심기 뒤에(나무 · 관목 · 차는 땅을 읽은 뒤) grade 를 부른다. 높이는 해발로 적고 작업면으로 올린다.
"""
import json
import os

import numpy as np
import shapely

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


# ---------------------------------------------------------------------------------------------------------------------
# 화단 남쪽 ~ 독수리상 둘레의 땅 (reference/고증/2.3.4 「화단 남쪽 ~ 독수리상 둘레의 땅」). 1997년 7월 장에서는 수관 밑이라 못 쟀던
# 땅을 잎 없는 1996년 겨울 장(코스 26 = 1996-12-23, 코스 27 = 1996-11-28)으로 쟀다: 같은 날 짝 둘(26/15 + 26/16, 27/16 + 27/17)과
# 날이 다른 짝 둘이 0.4 m 안에서 맞는 점, 두 날이 1 m 넘게 갈리면(어느 하루에 선 차) 낮은 쪽. 화단(1997년 7월의 면)에서 이 점들은
# 그 면과 중앙값 +0.02 m 로 맞는다. 화단 남쪽 끝 길에서 독수리상 북쪽까지의 나무 띠는 30.2 ~ 30.9 m 로 거의 평평하고(게임은
# 화단에서 독수리상 쪽으로 1.1 m 내려가 0.8 ~ 1.4 m 낮았음), 그 남쪽 가가 마당(1997년 28.2 m)으로 2 m 남짓 떨어진다. 서쪽 화단
# (o −44 ~ −22)과 그 남쪽 나무 띠의 서쪽 끝은 1 ~ 2 m 높고, 옆길은 화단 남쪽 끝(31.0 m)에서 마당 동쪽 끝(28.4 m)까지 6 % 로 고르게
# 내려간다(게임은 나무 띠 안에서 가파르게 내려가 0.6 ~ 1.2 m 낮았음). 점(해발)은 libsouth97_belt.json.
# 높이: 화단과 같은 기준(grade 의 dz: 둘레 도서관 발치 · 바깥 길에 맞춘 것), 옆길은 남쪽으로 갈수록 마당의 기준(BELT_YARD_DZ:
# west_ground.LOT_Z 가 사진의 맨땅 위에 놓인 만큼, 2026-11-17 부터 0)으로 옮겨 가며 사진의 단면을 따름. 둘레 BELT_RING m 는 매끈하게.
# 마당(west_ground.lot)과 독수리상의 둥근 마당(반지름 BELT_EAGLE_R m), 건물 발치는 건드리지 않는다
BELT = [(-77.5, -51.0, -58.0, 50.0),       # 화단 남쪽 끝 길 ~ 마당 북쪽 가 · 독수리상 북쪽, 도서관 서쪽 길 ~ 백양로 쪽 바깥 길
        (-51.0, -12.0, -44.0, -22.0)]      # 서쪽 화단(도서관 서쪽 면의 줄 ~ 화단 구역 서쪽 끝)
# 옆길(SIDE_W, 1997년의 길 o 11 ~ 22)의 나무 띠 남쪽 끝: 마당 · 옆길 남쪽(마당의 기준에 놓인 것)과 이어지게 둘레로 둠(사진의 옆길은
# s −80 에서 29.6 m, 그 남쪽은 차가 늘 서 있어 판독이 갈림: 옆길 양쪽에 길 따라 선 차가 기울지 않게 매끈하게 이음)
BELT_CUT = [(-96.0, -70.0, 6.0, 24.0)]
BELT_EAGLE = (-67.95, -161.78)
BELT_EAGLE_R = 12.5
BELT_SIGMA = 3.0                         # 점의 가우스 무게(m)
BELT_RING = 10.0
BELT_YARD_DZ = 0.0                       # (게임 마당 28.0 m − 사진 맨땅 28.0 m: west_ground.LOT_Z, 2026-11-17)
BELT_ROAD = (-62.0, -92.0, (2.0, 8.0, 24.0, 30.0))   # 옆길의 기준을 옮기는 s 구간(화단 기준 → 마당 기준), 그 o 구간(가장자리는 서서히)
_BP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libsouth97_belt.json'), encoding='utf-8'))['pts']
BELT_PTS = np.array(_BP, float)


def belt_dz(s, o, dz):
    """그 자리의 기준(사진 → 게임): 화단 기준 dz 에서 옆길을 따라 남쪽으로 마당 기준까지"""
    sa, sb, (oa, ob, oc, od) = BELT_ROAD
    w = np.clip((sa - s) / (sa - sb), 0.0, 1.0) * np.clip(np.minimum((o - oa) / (ob - oa), (od - o) / (od - oc)), 0.0, 1.0)
    return dz + (BELT_YARD_DZ - dz) * w


def belt(Hn, X, Y, FIXED, keep, fill, dz, lot):
    """화단 남쪽 ~ 독수리상 둘레(BELT)의 마디를 겨울 장의 땅(가우스 무게 평균) + 기준(belt_dz)으로, 점이 닿지 않는 마디와 둘레
    BELT_RING m 는 매끈하게(fill). lot: 마당(그 마디는 뒤에 west_ground.eagle_yard 가 놓음). 돌려주는 것: (옮긴 마디, 요약)"""
    s, o = sxy(X, Y)
    inside = np.zeros(X.shape, bool)
    for s0, s1, o0, o1 in BELT:
        inside |= (s >= s0) & (s <= s1) & (o >= o0) & (o <= o1)
    for s0, s1, o0, o1 in BELT_CUT:
        inside &= ~((s >= s0) & (s <= s1) & (o >= o0) & (o <= o1))
    out = shapely.contains_xy(lot, X, Y) | (np.hypot(X - BELT_EAGLE[0], Y - BELT_EAGLE[1]) < BELT_EAGLE_R)
    zone = inside & ~FIXED & ~keep & ~out
    ps, po = sxy(BELT_PTS[:, 0], BELT_PTS[:, 1])
    use = ~((ps < -76.0) & (po > 22.5))              # (옆길 동쪽 가 너머 독수리상 서쪽 잔디의 점: 옆길 마디에는 쓰지 않음)
    P = BELT_PTS[use]
    xs, ys = X[zone], Y[zone]
    w = np.exp(-((xs[:, None] - P[None, :, 0]) ** 2 + (ys[:, None] - P[None, :, 1]) ** 2) / (2 * BELT_SIGMA ** 2))
    ws = w.sum(1)
    z = (w * P[None, :, 2]).sum(1) / np.maximum(ws, 1e-9)
    H0 = Hn.copy()
    got = ws >= 0.3
    zi = np.zeros(X.shape, bool)
    zi[zone] = got
    Hn[zi] = z[got] + belt_dz(s[zi], o[zi], dz) + datum.tilt(X[zi], Y[zi])
    gap = zone & ~zi
    if gap.any():
        fill(gap)
    ring = np.zeros(X.shape, bool)
    for s0, s1, o0, o1 in BELT:
        ring |= (s >= s0 - BELT_RING) & (s <= s1 + BELT_RING) & (o >= o0 - BELT_RING) & (o <= o1 + BELT_RING)
    ring &= ~inside & ~FIXED & ~keep & ~out
    if ring.any():
        fill(ring)
    d = Hn - H0
    return zone, dict(nodes=int(zi.sum()), filled=int(gap.sum()), ring=int(ring.sum()), dz=round(dz, 2),
                      lo=round(float(d[zone].min()), 2), hi=round(float(d[zone].max()), 2),
                      mean=round(float(d[zone].mean()), 2))
