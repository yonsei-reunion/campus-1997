"""중앙도서관 서쪽 길과 북서쪽 굽은 길 (reference/고증/2.10 「중앙도서관 서쪽 길 · 북서쪽 굽은 길」, 3.2-3.3 「뒤쪽 땅」).

1997년 7월 원본 스캔에서 도서관 서쪽 면과 장기원 기념관 쪽 나무 띠 사이는 포장한 길이다. 서쪽 가에 차가 길에 직각으로
머리를 넣은 줄(흰 칸 선), 도서관 서쪽 면을 따라 길 따라 선 줄, 그 사이 통로. 길은 남쪽 끝에서 도서관 남쪽 길로 나가고,
북쪽 끝에서 두 단으로 갈린다.
- 아랫단(LOWER): 서쪽 길 · 도서관 북서쪽 모퉁이의 자재 마당 · 도서관 북쪽 면 앞 띠. 사진(서쪽 코스 짝 26/16 + 26/15 와 1996년
  겨울 26/15 + 26/16, 동쪽 코스 장은 도서관 지붕에 가림)의 땅은 해발 33.15 ~ 33.35 m 로 거의 평평(58점, 면에서 rms 0.14 m).
  게임은 도서관 발치를 둘러 34.24 m(바닥 높이)였고 서쪽 · 북쪽으로 오르는 비탈이라 1 ~ 2 m 높았음
- 윗단(UPPER): 자재 마당을 돌아 북쪽 찻길로 가는 굽은 길. 아랫단보다 1.6 ~ 2.8 m 높고 동쪽으로 내려감(36.05 → 34.96 m, 73점,
  rms 0.18 m). 두 단 사이(STEP)는 굽은 길 안쪽 가의 어두운 띠(벽 · 둑). 굽은 길의 서쪽 다리는 자재 마당 서쪽을 따라 남쪽으로
  내려가 서쪽 길에 닿음(y −16 ~ 6 의 비탈길: 사진의 높이가 남쪽으로 36.6 → 34.9 m)
높이는 사진의 면 그대로(dz 0: 도서관 서쪽 발치 33.31 m 와 사진의 길 33.25 m, 남쪽 끝의 도서관 남쪽 길 33.11 m 와 33.17 m 가 맞음).
도서관의 화강석 기단은 바닥보다 4 m 아래까지 내려가 있어, 그 둘레 땅을 바닥(34.24 m)보다 1 m 낮추어도 틈이 생기지 않는다.
build_campus.py 가 무작위 심기 뒤에 grade 를 부르고, 칠(paint) · 나무 비키기(move_off)는 땅 지도 · 목록을 쓸 때.
"""
import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, unary_union

import datum

O = np.array([-85.44, -71.08])          # 도서관 정면 틀(libsouth97 과 같음): 남동 모서리, s 북쪽, o 동쪽
T = np.array([0.25441, 0.9671])
N = np.array([0.9671, -0.25441])
LIB = 163525865


def so(s, o):
    return tuple(float(v) for v in O + T * s + N * o)


# 두 단 사이(굽은 길 안쪽 가)와 비탈길 동쪽 가: 남쪽(비탈길 발치)에서 북쪽 찻길까지
# (사진의 어두운 띠는 (−124.0, 12.5) · (−121.5, 17.8) · (−116.5, 21.8) · (−111.0, 24.4): 그 가에 선 차가 5 m 격자의 두 단 사이 칸에
# 걸치지 않게 자재 마당 쪽으로 2.5 ~ 3.5 m 옮겨 둠)
STEP = [(-128.0, -16.0), (-127.0, -4.0), (-125.5, 4.0), (-121.0, 10.0), (-117.0, 15.0), (-112.5, 19.5), (-108.5, 23.0),
        (-104.0, 26.0), (-96.0, 26.8), (-90.0, 27.0)]
UPPER = Polygon([(-132.3, -16.0)] + STEP + [(-90.0, 36.4), (-101.0, 36.6), (-110.5, 35.8), (-118.5, 33.8), (-124.6, 30.5),
                                             (-128.6, 25.5), (-130.6, 20.0), (-131.4, 12.0), (-131.6, 0.0)])
# 아랫단: 서쪽 길(포장은 서쪽 가 o −56.5 = 직각 줄의 뒤끝까지, 땅은 그 뒤 생울타리 o −58.5 까지 평평), 동쪽 가 o −44.5(도서관 벽에서
# 1.2 m), 자재 마당, 도서관 북쪽 면 앞 띠
PAVE_W = -56.5
LOWER = Polygon([so(-13.0, -58.5), so(40.0, -58.5)] + STEP + [(-89.7, 10.57), (-107.5, 15.16), so(-13.0, -44.5)])
LOWER_PLANE = (33.1540, -0.0014, 0.0027)          # 해발 = a + b·x + c·y
UPPER_PLANE = (33.2451, -0.0232, -0.0163)
UPPER_Y0 = 6.0           # 이 북쪽만 윗단의 면(그 남쪽 비탈길은 아랫단 · 윗단 사이를 매끈하게: 사진은 나무에 가려 띄엄띄엄)
RING = 8.0


def plane(c, X, Y):
    return c[0] + c[1] * X + c[2] * Y


def sxy(X, Y):
    return (X - O[0]) * T[0] + (Y - O[1]) * T[1], (X - O[0]) * N[0] + (Y - O[1]) * N[1]


def grade(Hn, X, Y, FIXED, keep, fill, lib):
    """아랫단 · 윗단의 마디를 사진의 면으로, 비탈길과 둘레 RING m 는 매끈하게(fill). keep: 건드리지 않을 마디(건물 발치). 다만 도서관
    서쪽 면과 북쪽 면 서쪽 반(정면 테라스가 두르지 않는 곳)은 바깥 3 m 와 안쪽 한 줄(5 m)을 길의 높이로: 그 곁에 선 차가 기울지
    않게(벽 안은 보이지 않고, 화강석 기단이 바닥 4 m 아래까지). lib: 도서관 외곽선. 돌려주는 것: (옮긴 마디, 요약)"""
    s, o = sxy(X, Y)
    west = (s >= 2.0) & (s <= 79.0) & (o >= -50.5) & (o <= -38.3)                  # (서쪽 면 바깥 7 m · 안 5 m)
    north = (s >= 71.6) & (s <= 84.0) & (o >= -50.5) & (o <= -24.0)                # (북쪽 면 서쪽 반)
    # (도서관 둘레 6 m 는 「뒤쪽 땅」(build_campus.py LIB_FLOOR)이 바닥 높이로 고정해 둔 것: 서쪽 · 북쪽 면은 길의 높이로 다시)
    libn = (west | north) & shapely.contains_xy(lib.buffer(7.0), X, Y)
    kp = keep & ~libn
    free = ~FIXED | libn
    lo = (shapely.contains_xy(LOWER.buffer(1.0), X, Y) | libn) & free & ~kp
    up = shapely.contains_xy(UPPER.buffer(2.5), X, Y) & ~FIXED & ~kp & ~lo & (Y >= UPPER_Y0)
    ramp = shapely.contains_xy(UPPER.buffer(1.0), X, Y) & ~FIXED & ~kp & ~lo & ~up
    H0 = Hn.copy()
    Hn[lo] = plane(LOWER_PLANE, X[lo], Y[lo]) + datum.tilt(X[lo], Y[lo])
    Hn[up] = plane(UPPER_PLANE, X[up], Y[up]) + datum.tilt(X[up], Y[up])
    took = lo | up
    if ramp.any():
        fill(ramp)
    took |= ramp
    zone = unary_union([LOWER, UPPER])
    ring = shapely.contains_xy(zone.buffer(RING), X, Y) & ~took & ~FIXED & ~keep
    if ring.any():
        fill(ring)
    d = Hn - H0
    return took, dict(lower=int(lo.sum()), upper=int(up.sum()), ramp=int(ramp.sum()), hall_side=int(libn.sum()), ring=int(ring.sum()),
                      lo=round(float(d[took].min()), 2), hi=round(float(d[took].max()), 2))


def paint():
    """아스팔트: 서쪽 길 · 자재 마당 · 도서관 북쪽 면 앞 띠(아랫단, 서쪽 가는 직각 줄의 뒤끝 PAVE_W), 굽은 길과 비탈길(윗단)"""
    return [LOWER.intersection(Polygon([so(-20.0, PAVE_W), so(90.0, PAVE_W), so(90.0, 10.0), so(-20.0, 10.0)])).union(
        LOWER.difference(Polygon([so(-20.0, -70.0), so(40.0, -70.0), so(40.0, 10.0), so(-20.0, 10.0)]))), UPPER]


def move_off(trees, shrubs, props, lib):
    """새 포장 위에 심긴 것: 나무 · 관목 · 소품은 포장 가장자리 밖(도서관 쪽이 아닌 가)으로 비킴(목록 제자리: 목록의 길이와 차례가
    그대로). lib: 도서관 외곽선. 돌려주는 것: (옮긴 관목 수, 옮긴 소품 수, 옮긴 나무)"""
    zone = unary_union(paint()).buffer(0.5)
    block = unary_union([zone, lib.buffer(3.0)])
    moved, ns, npr = [], 0, 0
    for lst, pad in ((trees, 1.0), (shrubs, 0.6), (props, 0.6)):
        b = block.buffer(pad)
        edge = unary_union([g.exterior for g in (b.geoms if hasattr(b, 'geoms') else [b])])
        for t in lst:
            if zone.contains(Point(t[1], t[2])):
                q = nearest_points(edge, Point(t[1], t[2]))[0]
                if lst is trees:
                    moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
                elif lst is shrubs:
                    ns += 1
                else:
                    npr += 1
                t[1], t[2] = round(q.x, 2), round(q.y, 2)
    return ns, npr, moved
