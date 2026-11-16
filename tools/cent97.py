"""백주년기념관 둘레의 1997년 아스팔트 (reference/고증/2.10 「백주년기념관 둘레」, 3.4).

1997년 7월 원본 스캔(26/16 · 27/17 · 26/15, 0.04 ~ 0.06 m/화소로 그 자리 높이의 면에 다시 투영)에서 게임이 잔디로 둔 두 곳이
한 장의 아스팔트이고 차가 서 있다. 1996년 겨울 · 1998년 10월 · 1999년 5월 장에도 같은 자리에 차.

- 남서쪽(SW): 정문 동쪽 주차장의 북쪽 찻길이 둥근 앞마당(CENT_SW_PAVE)의 남쪽 · 서쪽을 돌아, 서쪽은 백양로 식재대까지,
  동쪽은 낮은 몸체 남쪽의 밝은 포장 띠(벽에서 5.6 m) 앞을 따라 안 · 이비인후과병원 앞까지. 게임은 주차장 북쪽 가(LOT_C_LOT,
  v 48.5)와 그 둘 사이가 잔디 띠였다. 땅 높이는 게임과 같다(사진 27.6 ~ 27.9 m, 게임 27.8 m; 둥근 앞마당 서쪽은 게임이
  0.3 m 낮으나 그대로)
  - BAND: 밝은 띠의 남쪽 가. 세 장에서 밝기 단면이 꺾이는 곳 일곱(x −30 ~ −8)에 맞춘 곧은 줄(rms 0.06 m, 벽과 1.2° 안)
- 북쪽(N): 백양로 보도에서 건물 북쪽 면 앞 포장 띠까지, 테라스 북쪽 끝의 둥근 단과 북쪽 잔디 사이의 마당과 그것이 북동쪽
  길로 이어지는 곳. 사진의 높이는 한 면(PLANE_N, 해발): 동쪽으로 8.75 % 오르고 남북으로는 거의 평평(13점, rms 0.14 m).
  게임의 땅은 그 면과 마당 북쪽 줄(y −170)에서 0.5 m 안이나, 건물 북서 모서리 발치(7 m 안)는 1.4 ~ 2.8 m 낮은 비탈이다.
  발치는 고치지 않으므로 여기서는 칠만 한다(그 비탈에 걸린 차는 tools/cars97_new.json 「백주년 북쪽 칸 · 넣지 않음」)
  - LAWN_N: 북쪽 잔디의 가. 세 장의 밝기 단면이 꺾이는 곳(x −22 ~ 0은 두 장 넘게 0.3 m 안)
  - 북동쪽 끝은 y −163 에서 자름(그 너머는 「학생회관 남쪽 북동 찻길」)

build_campus.py 가 무작위 심기 뒤의 늦은 칠(정문 동쪽 주차장의 LOT_C_LOT 곁)에서 asphalt() 를 _ga 로 칠하고, 그 위의 관목을
shrubs_off() 로 뺀다. 그 위의 나무(남서쪽 찻길의 소나무 하나: 사진에는 없음)는 trees_off() 로 목록 제자리에서 TREE_SPOTS 로.
"""
import math

import numpy as np
import shapely
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

# 남서쪽: 낮은 몸체 남쪽 밝은 띠의 가 y = BAND[0] + BAND[1] · x
BAND = (-268.895, -0.25555)
SW_EAST = -5.3                           # (동쪽 끝: 그 동쪽 병원 앞은 그늘이라 못 읽음, 게임의 포장 그대로)
SW_NORTH = -242.0                        # (둥근 앞마당 서쪽: 앞마당 포장이 보도로 나가는 곳까지)

# 북쪽 마당의 면(해발): z = a + b·x + c·y
PLANE_N = (28.88, 0.0875, -0.0181)
LAWN_N = [(-24.5, -164.3), (-22.0, -166.3), (-20.0, -166.9), (-18.0, -167.1), (-16.0, -167.75), (-14.0, -168.25),
          (-12.0, -168.6), (-10.0, -168.6), (-8.0, -168.4), (-6.0, -168.1), (-4.0, -167.2), (-2.0, -166.9),
          (0.0, -166.5), (0.9, -164.0), (1.6, -163.0)]
TERRACE_N = ((-21.4, -180.8), 7.8)       # 테라스 북쪽 끝 둥근 단과 그 가의 화단(사진, 0.04 m/화소): 칠하지 않음
HALL_BAND = 4.5                          # 건물 북쪽 면 앞의 밝은 포장 띠(화분 줄이 그 가에)
# 아스팔트 위에 심긴 나무가 비킬 자리: 가장 가까운 잔디인 둥근 앞마당 가운데 화단(반지름 5.1 m)의 남동쪽, 화단 가에서 2 m 안쪽.
# 1996년 겨울 장(26/16)에서 잎 없는 가지가 모이는 곳 곁(1997년 7월에는 화단을 덮는 수관 하나). 둘레 차 · 길에서 3 m 넘게
TREE_SPOTS = [(-37.3, -258.7)]


def band_y(x):
    return BAND[0] + BAND[1] * x


def plane_n(x, y):
    return PLANE_N[0] + PLANE_N[1] * np.asarray(x) + PLANE_N[2] * np.asarray(y)


def sw_area(sw_pave, sw_c, sw_r, road_keep, halls, lot):
    """남서쪽 아스팔트(캠퍼스 m). sw_pave: 둥근 앞마당 포장(CENT_SW_PAVE), sw_c · sw_r: 그 고리의 가운데와 바깥 반지름,
    road_keep: 백양로 메시와 식재대(빼는 곳), halls: 건물 외곽선, lot: 이미 칠한 정문 동쪽 주차장(LOT_C_LOT)"""
    poly = Polygon([(-66.0, SW_NORTH), (-49.0, SW_NORTH), (-49.0, -250.0), tuple(sw_c), (-31.3, band_y(-31.3)),
                    (SW_EAST, band_y(SW_EAST)), (SW_EAST, -278.0), (-66.0, -266.0)])
    return poly.difference(unary_union([sw_pave, Point(sw_c).buffer(sw_r, quad_segs=24), road_keep, lot] +
                                       [h.buffer(1.0) for h in halls]))


def n_area(road_keep, hall):
    """북쪽 마당의 아스팔트(캠퍼스 m). hall: 백주년기념관 외곽선"""
    poly = Polygon([(-40.0, -164.3)] + LAWN_N + [(17.5, -163.0), (17.5, -172.0), (2.0, -181.0), (-8.0, -180.5),
                                                   (-14.0, -180.5), (-29.0, -178.5), (-40.0, -178.5)])
    return poly.difference(unary_union([Point(TERRACE_N[0]).buffer(TERRACE_N[1], quad_segs=24), road_keep,
                                        hall.buffer(HALL_BAND)]))


def asphalt(sw_pave, sw_c, sw_r, road_keep, halls, hall, lot):
    """두 곳의 아스팔트(_ypaint 에 넘길 다각형들)"""
    out = []
    for g in (sw_area(sw_pave, sw_c, sw_r, road_keep, halls, lot), n_area(road_keep, hall)):
        out += [p for p in getattr(g, 'geoms', [g]) if p.geom_type == 'Polygon' and p.area > 1.0]
    return out


def trees_off(trees, areas, pad=0.5):
    """아스팔트 위(가에서 pad 밖까지)에 심긴 나무를 목록의 제자리에서 TREE_SPOTS 의 가까운 빈 자리로(목록의 길이 · 차례 그대로).
    돌려주는 것: [(종류, 전 x, 전 y, 후 x, 후 y)]"""
    zone = unary_union(areas).buffer(pad)
    free = list(TREE_SPOTS)
    moved = []
    for t in trees:
        if not free or not zone.contains(Point(t[1], t[2])):
            continue
        q = min(free, key=lambda s: math.dist(s, (t[1], t[2])))
        free.remove(q)
        moved.append((t[0], t[1], t[2], q[0], q[1]))
        t[1], t[2] = q
    return moved


def shrubs_off(shrubs, areas, pad=0.3):
    """아스팔트 위(가에서 pad 안쪽)의 관목을 뺀다(관목은 목록 순서로 뽑지 않음). 돌려주는 것: 뺀 것"""
    zone = unary_union(areas).buffer(-pad)
    gone = [s for s in shrubs if zone.contains(Point(s[1], s[2]))]
    shrubs[:] = [s for s in shrubs if not zone.contains(Point(s[1], s[2]))]
    return gone


# 북쪽 마당의 건물 발치(3.4 「북쪽 면의 창 띠와 발치」): 북서 모서리 · 북쪽 모서리 발치 7 m 안의 마디가
# PLANE_N 보다 1.4 ~ 2.8 m 낮은 비탈이었다(고도 자료가 건물 덩어리를 번진 것). 2010년 12월 북쪽 길 로드뷰(1016786960, 줌 0)에서 북북서 면의
# 발치는 앞 포장 띠(1997년 스캔 32.3 ~ 32.6 m)와 한 높이이고, 맨 아래 창 띠의 밑이 그 위 3.0 m(blender/landmarks.py north_box rows).
# FOOT: 그 면으로 올릴 마디의 넓이(마당 · 북서 모서리 발치 · 북쪽 모서리 발치. 그 동쪽 동쪽 앞마당 CENT_NE 은 사진 29.5 ~ 30.9 m 로
# 게임 30.46 m 와 같아 그대로)
FOOT = Polygon([(-16.0, -176.0), (-16.0, -183.5), (-6.0, -183.5), (2.0, -186.5), (12.0, -179.0), (16.5, -172.5),
                (16.5, -166.0), (8.0, -165.0), (-4.0, -168.0)])
FOOT_TOL = 0.3                           # 면보다 이만큼 넘게 낮은 마디만


def foot_grade(Hn, X, Y, FIXED, up):
    """FOOT 안에서 PLANE_N 보다 FOOT_TOL 넘게 낮은 마디를 그 면으로(작업면: up(x, y, 해발)). 돌려주는 것: (정한 마디, 요약)"""
    inside = shapely.contains_xy(FOOT, X, Y) & ~FIXED
    pz = Hn.copy()
    pz[inside] = [up(x_, y_, float(plane_n(x_, y_)), None) for x_, y_ in zip(X[inside], Y[inside])]
    low = inside & (Hn < pz - FOOT_TOL)
    d = np.where(low, pz - Hn, 0.0)
    Hn[low] = pz[low]
    return low, dict(n=int(low.sum()), dz=(round(float(d[low].min()), 2), round(float(d[low].max()), 2)) if low.any() else 0,
                     at=[(float(x_), float(y_)) for x_, y_ in zip(X[low], Y[low])])
