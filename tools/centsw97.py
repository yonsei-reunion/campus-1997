"""백주년기념관 남서쪽 로비 앞의 계단식 화단과 두 계단 (reference/고증/3.4 「남서쪽 로비 앞의 계단식 화단과 두 계단」).

자료 R `100-1.jpg`(1996년 봄 전)에서 곡면 유리 로비 앞은 철쭉 · 회양목 · 원뿔꼴 상록수를 심은 화강석 화단 단이고, 그 왼쪽(북서쪽)
보도에 짧은 계단 넷, 오른쪽 모서리 몸체 앞면 출입구에 계단 하나. 1997년 7월 원본 스캔(26/16 · 26/15 · 27/16 · 27/17)과
카카오 스카이뷰 2008 · 2010년이 화단 단의 평면을 보여 준다.

- 화단 단(TIERS): 건물 백양로 쪽 면의 틀(s: 북서 모서리에서 면을 따라 남쪽, d: 면에서 서쪽, build_campus.py ct_xy)에서
  면과 나란한 곧은 벽(d 15 · 12 · 8.75 · 5)과 둥근 앞마당(CENT_SW_C)의 가운데를 도는 호(반지름 10.1 · 12.1 · 15.2 m)로
  네 단. 북서쪽 끝은 단마다 면에 직각인 짧은 벽과 45° 모서리(스캔 26/16 의 갓돌 판독, ±0.3 m)
- 높이(건물 바닥 위): 0.8 · 1.4 · 2.0 · 2.6 m. 앞마당은 사진 28.0 m(바닥 위 0.2 m), 맨 윗단은 유리 굽(바닥 위 2.9 m) 아래.
  앞단 벽 0.6 m 는 100-1.jpg 의 오른쪽 계단(챌판 열)과 견준 값. 화단 흙은 스캔에서 관목에 가려 재지 못함
- 보도(STRIP): 앞마당에서 북동쪽으로 오르는 폭 약 5 m 의 포장. 스캔의 가로 띠(챌판 그늘) 넷이 계단, 그 사이 단의 높이는
  스캔(창 0.6 m, 상관 0.9 넘음): 앞마당 27.9 ~ 28.1, 첫 단 28.89 ~ 28.94, 둘째 단 29.33 ~ 29.49, 셋째 단 30.2 ~ 30.6(상관 0.6 ~ 0.7)
- 모서리 몸체 앞면 출입구(PORTAL, CENT_BLOCK): 2010년 12월 로드뷰 1016763194 정면 화면 · 100-1.jpg 의 오른쪽 계단:
  깊지 않은 높은 문틀 안에 돌 벽, 그 서쪽 끝에 문(가운데 유리문 · 양옆 나무 문짝)과 그 위 띠 창, 동쪽에 네모 기둥 둘,
  앞에 챌판 열의 계단. 게임은 2.7 m 높이 2.5 m 깊이의 어두운 입구였다
"""
import math

import numpy as np
from shapely.geometry import Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

# 화단 단의 바깥 가(보도 쪽 갈짓자, (s, d)): 앞마당 호와 d 15 의 만남 → 단마다 북서쪽 끝 → 맨 윗단 북쪽 끝(유리 호가 면에 닿는 곳)
EDGE = [(69.74, 15.0), (64.55, 15.03), (62.3, 13.1), (62.07, 12.15), (59.98, 12.0), (58.18, 10.37), (57.93, 8.76),
        (54.96, 8.69), (53.02, 6.45), (49.1, 5.5), (47.4, 3.0), (47.9, 0.4)]
LINES = [15.0, 12.0, 8.75, 5.0]           # 면과 나란한 벽(d)
ARCS = [10.1, 12.1, 15.2]                 # 앞마당 가운데를 도는 벽(반지름)
TOPS = [0.8, 1.4, 2.0, 2.6]               # 단 윗면(흙, 건물 바닥 위 m)
T4_S = (57.5, 65.3)                       # 맨 윗단: 곧은 유리 벽 앞의 좁은 띠(스캔의 d 5 벽이 s 58.2 ~ 63.1)
GAP = 0.15                                # 건물 벽 · 유리 굽과의 틈

# 보도: 북서쪽 가의 곧은 줄(스캔), u 북동쪽, n 화단 쪽
STRIP_P0 = (-48.0, -242.0)
STRIP_U = (0.79201, 0.61051)
# 계단: (첫 챌판의 s, 챌판 수, 챌판 높이). 앞마당 바닥 위 0.2 m 에서, 단은 바닥 위 1.1 · 1.58 · 2.18 · 2.6 m
FLIGHTS = [(9.2, 6, 0.15), (14.6, 3, 0.16), (20.2, 4, 0.15), (27.4, 3, 0.14)]
TREAD = 0.32
PLAZA = 0.2
STRIP_END = 30.4                          # 맨 윗단의 끝(그 너머는 게임의 땅으로 내려가는 비탈, RAMP m)
RAMP = 2.2

# 모서리 몸체 앞면 출입구 (CENT_BLOCK 의 틀: e 앞면을 따라 동쪽, 바닥 위 m). 1016763194 화면의 비례(문짝 2.06 m 로 둠)
PORTAL = dict(depth=1.2, pier_d=0.5, top=5.2, risers=10, rise=0.145, tread=0.33, stairs=[0.3, 10.1],
              doors=[0.83, 4.5], door_h=2.06, transom=2.61, window=[3.92, 5.16], piers=[[6.03, 7.17], [7.70, 8.97]])


def strip_xy(s, w):
    return (STRIP_P0[0] + STRIP_U[0] * s + STRIP_U[1] * w, STRIP_P0[1] + STRIP_U[1] * s - STRIP_U[0] * w)


def strip_sw(x, y):
    q = (x - STRIP_P0[0], y - STRIP_P0[1])
    return q[0] * STRIP_U[0] + q[1] * STRIP_U[1], q[0] * STRIP_U[1] - q[1] * STRIP_U[0]


def walk_z(s):
    """보도 윗면(건물 바닥 위 m): 계단은 챌판마다, 단은 평평"""
    z = PLAZA
    for s0, n, r in FLIGHTS:
        if s < s0:
            return z
        k = min(n, int((s - s0) / TREAD) + 1)
        if k < n:
            return z + k * r
        z += n * r
    return z


def _disk(c, r):
    return Point(c).buffer(r, quad_segs=48)


def tiers(ct_xy, ct_sd, plaza_c, cdr, ctr):
    """네 단의 다각형(게임 x, y)과 윗면 높이. ct_xy / ct_sd: build_campus.py 의 면 틀, plaza_c: CENT_SW_C,
    cdr · ctr: 낮은 몸체의 호(원통 가운데, 반지름 19.1 m)"""
    C = np.array(ct_sd(*plaza_c))
    D = np.array(ct_sd(*cdr))
    big = 60.0
    hp = lambda d0, d1, s0=0.0, s1=120.0: Polygon([(s0, d0), (s1, d0), (s1, d1), (s0, d1)])
    # 화단 전체: 보도 쪽 갈짓자 · 앞마당 호 · 모서리 몸체 서쪽 면(d 4.5) · 곧은 유리 벽(d 2.83) · 유리 호
    outer = Polygon(EDGE + [(EDGE[-1][0], -5.0), (90.0, -5.0), (90.0, 20.0), (EDGE[0][0], 20.0)])
    beds = outer.intersection(hp(-5.0, 15.1, 0.0, 75.15)).difference(_disk(C, ARCS[0]))
    hall = unary_union([hp(-big, 4.5 + GAP, 65.25, 90.0), hp(-big, 2.83 + GAP, 0.0, 65.25 + 0.01),
                        _disk(D, ctr + GAP)])
    beds = beds.difference(hall).buffer(0)
    t1 = beds.intersection(hp(LINES[1], big).union(_disk(C, ARCS[1])))
    t2 = beds.intersection(hp(LINES[2], big).union(_disk(C, ARCS[2]))).difference(t1)
    t4 = beds.intersection(hp(-big, LINES[3], *T4_S)).difference(t1.union(t2))
    t3 = beds.difference(unary_union([t1, t2, t4]))
    out = []
    for g, top in zip((t1, t2, t3, t4), TOPS):
        for p in getattr(g, 'geoms', [g]):
            if p.geom_type == 'Polygon' and p.area > 0.5:
                p = p.simplify(0.02)
                q = orient(Polygon([tuple(ct_xy(s, d)[:2]) for s, d in list(p.exterior.coords)[:-1]]), 1.0)   # (anticlockwise)
                out.append(dict(top=top, poly=[[round(x, 3), round(y, 3)] for x, y in list(q.exterior.coords)[:-1]]))
    return out, Polygon([tuple(ct_xy(s, d)[:2]) for s, d in list(beds.exterior.coords)[:-1]])


def strip(beds_xy):
    """보도의 단면: s 마다 화단 쪽 가의 w (화단 다각형을 만나는 곳, 없으면 5.5 m)"""
    se = []
    for s in np.arange(8.6, STRIP_END + RAMP + 0.01, 0.25):
        w_hit = 5.5
        for w in np.arange(0.0, 7.0, 0.05):
            if beds_xy.buffer(0.05).contains(Point(*strip_xy(s, w))):
                w_hit = max(0.6, w - 0.05)
                break
        se.append([round(float(s), 2), round(float(w_hit), 2)])
    return dict(p0=list(STRIP_P0), u=list(STRIP_U), tread=TREAD, plaza=PLAZA, end=STRIP_END, ramp=RAMP,
                flights=[dict(s0=s0, n=n, rise=r, z0=round(walk_z(s0 - 0.01), 3)) for s0, n, r in FLIGHTS], se=se)


def shrubs(tier_list):
    """단 위의 관목(목록 끝에, 난수 없음): 단마다 앞 가를 따라 회양목 띠, 그 안쪽에 둥근 회양목 · 철쭉 무더기, 둘째 · 셋째 단에
    원뿔꼴 상록수(100-1.jpg: 앞단 회양목 띠와 둥근 관목, 그 뒤 단에 붉은 · 분홍 철쭉과 원뿔꼴 상록수 여덟쯤)"""
    out = []
    for k, t in enumerate(tier_list):
        P = Polygon(t['poly'])
        lvl = TOPS.index(t['top'])
        inner = P.buffer(-0.45)
        if inner.is_empty:
            continue
        # the boxwood band 0.45 m in from the bed's edge (all round: against a higher bed it is hidden by that bed's wall)
        for ring in [g.exterior for g in getattr(inner, 'geoms', [inner])]:
            L = ring.length
            for j in range(int(L / 0.9)):
                a, b = ring.interpolate(j * 0.9), ring.interpolate(j * 0.9 + 0.3)
                out.append(['hedge_low', round(a.x, 2), round(a.y, 2), 0.85, round(math.atan2(b.y - a.y, b.x - a.x), 3), 1])
        core = P.buffer(-0.95)
        if core.is_empty:
            continue
        minx, miny, maxx, maxy = core.bounds
        j = 0
        for gx in np.arange(minx, maxx + 0.01, 1.25):
            for gy in np.arange(miny, maxy + 0.01, 1.25):
                q = Point(gx + 0.4 * ((j * 7) % 3 - 1), gy + 0.3 * ((j * 5) % 3 - 1))
                j += 1
                if not core.contains(q):
                    continue
                if lvl == 0:
                    kind, sc = ('topiary_round', 0.9) if j % 3 else ('azalea_red', 1.0)
                else:
                    kind, sc = (('topiary_cone', 1.1 + 0.15 * (j % 3)) if j % 4 == 1 else
                                ('azalea_red', 1.0) if j % 4 in (0, 2) else ('topiary_round', 0.95))
                out.append([kind, round(q.x, 2), round(q.y, 2), round(sc, 2), round((j * 1.37) % 6.28, 2), 1])
    return out
