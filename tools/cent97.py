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
shrubs_off() 로 뺀다. 나무는 옮기지 않는다(그 자리에 게임 나무가 없음; 남서쪽 띠의 소나무 하나만 찻길에 섬).
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


def shrubs_off(shrubs, areas, pad=0.3):
    """아스팔트 위(가에서 pad 안쪽)의 관목을 뺀다(관목은 목록 순서로 뽑지 않음). 돌려주는 것: 뺀 것"""
    zone = unary_union(areas).buffer(-pad)
    gone = [s for s in shrubs if zone.contains(Point(s[1], s[2]))]
    shrubs[:] = [s for s in shrubs if not zone.contains(Point(s[1], s[2]))]
    return gone
