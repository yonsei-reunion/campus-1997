"""루스채플 남쪽 마당 (reference/고증/2.10 「루스채플 남쪽 마당의 땅」)과 루스채플 · 그 앞 (reference/고증/3.25).

1997년 7월 원본 스캔(26/16 · 27/17, 0.06 m/화소로 다시 투영)에서 채플 앞 둥근 잔디 둘(채플 쪽으로 2 ~ 4 m 오르는 둑)의 남쪽
연석과 남쪽 나무 띠 사이는 한 장의 아스팔트 마당이다. 잔디 연석을 따라 부채꼴로 선 차 줄, 가운데 굽은 찻길, 나무 띠 앞에
비스듬히 선 차 줄이 있다. 땅은 거의 평평하다(가운데 찻길 서른 점, 짝 다섯 ~ 여섯: 해발 36.5 m(서쪽) → 36.9 m(동쪽 끝)).
게임은 이 둘레가 고도 자료를 따른 한 비탈(서쪽 35.1 → 동쪽 39.4 m)에 잔디, 그 위로 폭 6 m 의 찻길(OSM)이었다.

- YARD: 마당의 윤곽. 북쪽은 잔디 연석(사진에서 읽은 자리), 남쪽 · 끝은 사진의 차(tools/cars97_new.json 의 루스채플 구역)를
  0.6 m 씩 둘러싼 칸과 가운데 찻길을 이어 메운 것
- grade: 마당 안 5 m 격자 마디를 찻길 단면(PROF, 해발)으로, 둘레 RING m 의 남은 마디를 매끈하게
- 무작위 심기가 끝난 뒤의 늦은 블록에서 부른다(나무 · 관목은 땅을 읽은 뒤). 마당 위의 관목은 제자리에서 옮긴다
- east_grade: 마당 동쪽 끝에서 심장혈관병원 북쪽 주차장으로 오르는 찻길(OSM 의 찻길, 둥근 잔디 동쪽 가와 심장혈관병원 서쪽 주차장
  사이)과 마당 남동쪽 끝. 사진(짝 여섯, 2 × 1.5 m 창)의 찻길은 s 24 ~ 44 에서 14 ~ 15 % 로 오르는데(37.2 → 39.9 m) 게임은
  고도 자료의 비탈이 0.6 ~ 1.8 m 높았다(마디는 의료원 주차장 셋(med97)의 둘레 고르기가 그 높이로 고정해 둔 것). 마당 남동쪽 끝
  (x 90 ~ 100, y −125 ~ −135)도 사진은 마당과 한 높이(36.8 ~ 37.4 m)인데 게임은 심장혈관병원 OSM 외곽(2011년 동, 1997년에는
  주차장)의 발치라 2.1 ~ 2.6 m 높았다. 그 마디들만 사진 높이로(EAST_NODES): 찻길 남쪽의 생울타리 줄 마디와 그 너머 주차장은
  심장혈관병원 서쪽 주차장의 차가 읽는 땅이라 그대로(찻길 남쪽 반이 그쪽으로 오름)
- 채플과 그 앞(아래 「루스채플과 그 앞」): 1997년 외곽(PARTS) · 바닥(FLOOR) · 남쪽 단(PORCH) · 두 잔디 사이 계단(STAIR)과
  잔디 둑의 마디(FRONT_NODES, front_grade). 외곽 · 바닥은 build_campus.py 의 LATE_FOOTPRINT_1997 · BASE_1997, 모양은
  blender/landmarks.py chapel
"""
import json
import math
import os

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, unary_union

import datum

HERE = os.path.dirname(os.path.abspath(__file__))
# 잔디 연석(사진: 바큇살마다 연석의 밝은 줄이 처음 나오는 곳, 두 장이 0.6 m 안인 것), 서 -> 동
LAWN_W = [(52.0, -90.0), (52.18, -94.30), (53.93, -98.45), (54.68, -99.32), (56.46, -100.77), (57.44, -101.37), (58.37, -102.08),
          (59.31, -102.90), (60.47, -103.18), (61.63, -103.47), (62.76, -104.12), (64.00, -104.55), (66.69, -105.24),
          (68.08, -105.21), (69.49, -105.08), (71.0, -104.9)]
LAWN_E = [(77.6, -105.6), (78.27, -106.40), (79.20, -107.39), (80.37, -108.14), (82.24, -109.76), (84.6, -112.3),
          (86.95, -113.88), (88.24, -114.03), (91.5, -114.7), (94.65, -115.02), (97.20, -114.28), (98.70, -114.36), (100.5, -114.2)]
# 마당 가운데 찻길의 줄과 높이(사진, 해발: 그 줄 위와 양옆 1 m 의 점마다 짝 다섯 ~ 여섯의 중앙값)
LINE = LineString([(40.0, -106.0), (50.0, -108.0), (60.0, -110.0), (72.0, -112.5), (82.0, -117.0), (92.0, -125.0), (100.0, -133.0)])
PROF = [(0.0, 36.50), (20.0, 36.52), (34.0, 36.68), (44.0, 36.85), (54.0, 36.75), (62.0, 36.86), (68.0, 36.97)]
CLIP = Polygon([(46.5, -96.0), (98.5, -96.0), (98.5, -132.5), (46.5, -132.5)])   # (서 · 동 · 남쪽 끝: 그 너머는 학생회관 동쪽 보도와 의료원 쪽 찻길)
RING = 10.0
ZONES = ('루스채플',)                     # (tools/cars97_new.json 의 구역 이름에 이것이 든 차)
# 마당 동쪽 끝의 찻길(줄 (80, −136) -> (126, −90) 의 s: 사진 s 24 37.21, 28 37.59, 30 37.78, 32 38.08, 36 38.8, 40 39.37,
# 44 39.94, 48 40.19, 52 40.39) 위의 마디와 마당 남동쪽 끝의 마디: 해발(사진 1997년 7월, 그 마디 둘레 2.5 m 의 점).
# 찻길 가운데 줄의 마디는 s 29 · 36 · 43. s 29 의 마디는 그 칸에 선 M1(s 25.5)이 5 m 칸에서 덜 기울게 s 27.5 의 값
EAST_NODES = {(100.0, -115.0): 37.55, (105.0, -110.0): 38.80, (110.0, -105.0): 39.80,     # (찻길 가운데 줄)
              (100.0, -120.0): 37.10,                                                       # (찻길 남쪽 가: 둘레 셋 37.1)
              (95.0, -130.0): 36.90, (95.0, -135.0): 36.90, (90.0, -135.0): 37.20,          # (마당 남동쪽 끝)
              (100.0, -125.0): 37.40, (100.0, -130.0): 37.35, (100.0, -135.0): 37.20}


def cars():
    """사진의 차: [(x, y, 방향 도, 크기)]"""
    d = json.load(open(os.path.join(HERE, 'cars97_new.json'), encoding='utf-8'))
    return [(c[0], c[1], c[2], c[3]) for k, v in d.items() if any(z in k for z in ZONES) for c in v['cars']]


def car_box(x, y, h, size='m', pad=0.0):
    t = np.array([math.cos(math.radians(h)), math.sin(math.radians(h))])
    n = np.array([-t[1], t[0]])
    L, W = (3.6, 1.65) if size == 's' else (4.7, 1.8)
    return Polygon([tuple(np.array([x, y]) + t * a * (L / 2 + pad) + n * b * (W / 2 + pad)) for a, b in ((1, 1), (1, -1), (-1, -1), (-1, 1))])


def lawns():
    """둥근 잔디 둘(연석 안쪽)"""
    w = Polygon(LAWN_W + [(71.5, -90.0)])
    e = Polygon(LAWN_E + [(100.5, -95.0), (77.0, -95.0)])
    return w.buffer(0), e.buffer(0)


def yard():
    """마당의 아스팔트 윤곽"""
    core = unary_union([car_box(x, y, h, s, 0.6) for x, y, h, s in cars()] + [LINE.buffer(3.5)])
    yd = core.buffer(2.5, join_style=2).buffer(-2.5, join_style=2)
    lw, le = lawns()
    yd = yd.difference(lw).difference(le)
    yd = yd.intersection(CLIP)
    yd = max(getattr(yd, 'geoms', [yd]), key=lambda g: g.area)
    return yd.buffer(0.8, join_style=1).buffer(-0.8, join_style=1).simplify(0.15)


def prof_z(s):
    return float(np.interp(s, *zip(*PROF)))


def grade(Hn, X, Y, FIXED, keep, fill):
    """마당 안(1 m 밖까지)의 마디를 PROF 의 높이로(작업면), 둘레 RING m 의 남은 마디를 매끈하게. keep: 그대로 둘 마디(건물 발치).
    돌려주는 것: (정한 마디, 요약)"""
    yd = yard()
    zone = shapely.contains_xy(yd.buffer(1.0), X, Y) & ~keep
    s = shapely.line_locate_point(LINE, shapely.points(X[zone], Y[zone]))
    h0 = Hn.copy()
    Hn[zone] = [datum.up(x_, y_, prof_z(s_), None) for x_, y_, s_ in zip(X[zone], Y[zone], s)]
    ring = shapely.contains_xy(yd.buffer(RING), X, Y) & ~zone & ~FIXED & ~keep
    if ring.any():
        fill(ring)
    d = Hn - h0
    return zone | ring, dict(nodes=int(zone.sum()), lo=round(float(d[zone].min()), 2), hi=round(float(d[zone].max()), 2),
                             ring=int(ring.sum()), ring_lo=round(float(d[ring].min()), 2) if ring.any() else 0.0,
                             ring_hi=round(float(d[ring].max()), 2) if ring.any() else 0.0)


def east_grade(Hn, step=5.0, half=800.0):
    """EAST_NODES 의 마디를 그 높이로(작업면). 다른 블록이 고정해 둔 마디(의료원 둘레 고르기, 심장혈관병원 OSM 외곽의 발치)도
    바꾼다: 그 마디들은 사진의 땅이 아니라 둘레를 잇던 값. 돌려주는 것: (정한 마디의 (j, i) 목록, 요약)"""
    took, dz = [], []
    for (x_, y_), z_ in EAST_NODES.items():
        j_, i_ = int(round((y_ + half) / step)), int(round((x_ + half) / step))
        z1_ = datum.up(x_, y_, z_, None)
        dz.append(round(float(z1_ - Hn[j_, i_]), 2))
        Hn[j_, i_] = z1_
        took.append((j_, i_))
    return took, dict(nodes=len(took), lo=min(dz), hi=max(dz))


def clear(items, pad=0.5):
    """마당 위(가에서 pad 안쪽까지)에 놓인 것(나무 · 관목)을 목록의 제자리에서 마당 밖 0.8 m 로. 돌려주는 것: [(차례, 전, 후)]"""
    yd = yard()
    zone, edge = yd.buffer(pad), yd.buffer(0.8)
    moved = []
    for i_, t_ in enumerate(items):
        p_ = Point(t_[1], t_[2])
        if not zone.contains(p_):
            continue
        q_ = nearest_points(edge.exterior, p_)[0]
        moved.append((i_, (t_[1], t_[2]), (round(q_.x, 2), round(q_.y, 2))))
        t_[1], t_[2] = round(q_.x, 2), round(q_.y, 2)
    return moved


# ----------------------------------------------------------------------------- 루스채플과 그 앞 (reference/고증/3.25)
# 1997년 7월 원본 스캔 네 장(26/15 · 26/16 · 27/16 · 27/17)과 잎 없는 1996년 겨울 네 장으로 잰 채플과 그 앞. 높이는 해발.
# 채플의 틀: O 에서 u 는 남쪽 면을 따라 동남동(T), v 는 그에 직각으로 북북동(N). 게임 외곽(OSM 남쪽의 45.4 × 24.5 m)이 이 틀의
# u ±22.7, v ±12.25 이다
CHAPEL = 429249499
O = (87.97, -78.2)
T = tuple(float(v_) for v_ in np.array([0.9672, -0.2543]) / math.hypot(0.9672, -0.2543))   # (게임 외곽 남쪽 면의 방향)
N = (-T[1], T[0])
FLOOR = 41.65                  # (바닥 = 남쪽 단: 단의 가 · 서쪽 끝 네모의 테 41.6 ~ 41.8, 1996년 41.8. 동쪽 땅 41.5 ~ 42.3)
# 지붕(평지붕, 그 가의 높이)과 평면(u0, u1, v0, v1). 본당은 네 장의 지붕 가가 ±0.25 m 안(50.9 m 면)
PARTS = dict(hall=((-23.3, 21.65, -13.75, 8.25), 50.9),      # (본당: 줄무늬 지붕 · 네 칸 · 검은 테)
             north=((-23.3, 21.65, 8.25, 13.0), 44.9),     # (북쪽 낮은 띠)
             east=((21.65, 29.95, -9.0, 3.4), 47.4),       # (동쪽 상자)
             wing=((-16.0, 2.5, 13.0, 27.5), 45.9))        # (북쪽 동: 채광창 넷)
PORCH = (-17.0, 5.7, -19.36, -13.75)       # (남쪽 단: 바닥 높이)
PLANTER = (-17.0, -11.5, -17.3, -13.75)    # (단 서쪽 끝, 흰 테를 두른 네모)
# 두 잔디 사이 계단: 폭 5 m, 단의 가에서 0.30 m 단 열둘로 층계참(39.55 m)까지, 층계참 2.76 m, 0.30 m 단 열셋으로 마당 가(37.2 m)까지
STAIR = dict(u=-5.5, width=5.0, top_v=-19.36, upper=12, landing_z=39.55, mid=2.76, lower=13, foot_z=37.2, tread=0.30)
# 무작위 심기 뒤에 고치는 5 m 격자 마디(해발): 잔디 둑 · 단 밑 · 계단 밑 · 서쪽 벽 발치. 마디마다 둘레 2.6 m 의 1997년 7월 ·
# 1996년 겨울 높이(창 1.2 m, 짝 둘 넘게 0.7 넘고 1 m 안에서 맞는 점)의 중앙값을 두 해가 맞는 데서 고르고, 단 · 계단 밑은
# 그 겉보다 낮게. 마당 칸(yard 의 1 m 안)과 찻길 · 동쪽 끝 마디는 그대로. 동쪽 잔디 남서쪽 끝 (80, −105) · (85, −110) 은
# 연석에 머리를 댄 차 줄의 칸에 걸려 잰 값(38.3 · 37.7)보다 낮게(그 칸의 차가 7° 까지 기울었음). 층계참 동쪽 곁 (80, −100) 도 층계참
# 높이로(잰 값 39.7 ~ 40.6: 5 m 칸이 층계참 위로 올라왔음)
FRONT_NODES = {
    (55.0, -90.0): 37.5, (60.0, -90.0): 38.9, (65.0, -90.0): 40.2,                       # (서쪽 잔디 북서쪽)
    (70.0, -90.0): 41.3, (75.0, -90.0): 41.3, (80.0, -90.0): 41.3,                       # (단 밑)
    (55.0, -95.0): 37.6, (60.0, -95.0): 39.1, (65.0, -95.0): 39.8, (70.0, -95.0): 40.4,  # (서쪽 잔디)
    (75.0, -95.0): 40.8, (80.0, -95.0): 41.3, (85.0, -95.0): 41.3,                       # (계단 머리 서쪽 곁, 단 밑)
    (90.0, -95.0): 41.0, (95.0, -95.0): 41.0,                                            # (동쪽 잔디: 남쪽 면 곁)
    (60.0, -100.0): 37.6, (65.0, -100.0): 39.1, (70.0, -100.0): 39.0,                    # (서쪽 잔디 남쪽)
    (75.0, -100.0): 39.3,                                                                # (층계참 밑)
    (80.0, -100.0): 39.4, (85.0, -100.0): 40.6, (90.0, -100.0): 41.2, (95.0, -100.0): 41.0,
    (100.0, -100.0): 40.8, (105.0, -100.0): 40.5,                                        # (동쪽 잔디 북쪽)
    (80.0, -105.0): 37.7, (85.0, -105.0): 38.9, (90.0, -105.0): 39.55, (95.0, -105.0): 39.95,
    (100.0, -105.0): 40.5,                                                               # (동쪽 잔디 가운데)
    (85.0, -110.0): 37.4, (90.0, -110.0): 38.9, (95.0, -110.0): 38.7, (100.0, -110.0): 39.2,   # (동쪽 잔디 남쪽)
    (60.0, -70.0): 38.0, (60.0, -75.0): 38.1, (60.0, -80.0): 37.9, (60.0, -85.0): 38.5,  # (서쪽 둑)
    (65.0, -70.0): 38.7,                                                                 # (서쪽 벽 발치)
}


def cxy(u, v):
    """채플 틀 (u, v) -> 게임 (x, y)"""
    return (O[0] + T[0] * u + N[0] * v, O[1] + T[1] * u + N[1] * v)


def cuv(x, y):
    dx, dy = x - O[0], y - O[1]
    return (dx * T[0] + dy * T[1], dx * N[0] + dy * N[1])


def crect(u0, u1, v0, v1):
    return Polygon([cxy(u0, v0), cxy(u1, v0), cxy(u1, v1), cxy(u0, v1)])


def outline():
    """1997년 채플의 외곽(본당 · 북쪽 띠 · 동쪽 상자 · 북쪽 동): 반시계, 꼭짓점 목록"""
    p = unary_union([crect(*r).buffer(0.01, join_style=2) for r, _ in PARTS.values()]).buffer(-0.01, join_style=2).simplify(0.05)
    p = shapely.geometry.polygon.orient(p, 1.0)
    return [(round(x, 2), round(y, 2)) for x, y in list(p.exterior.coords)[:-1]]


def front_grade(Hn, X, Y, fill, step=5.0, half=800.0):
    """FRONT_NODES 를 그 높이로(작업면, 다른 블록이 고정해 둔 마디도: 잔디 둑은 마당의 둘레 고르기가 비탈로 이어 두었던 것),
    채플 외곽 안의 마디는 둘레에 맞춰 매끈하게. 돌려주는 것: (정한 마디의 (j, i) 목록, 안쪽 마디의 틀, 요약)"""
    took, dz = [], []
    zone = shapely.contains_xy(yard().buffer(1.0), X, Y)
    for (x_, y_), z_ in FRONT_NODES.items():
        j_, i_ = int(round((y_ + half) / step)), int(round((x_ + half) / step))
        assert not zone[j_, i_], ('a yard node', x_, y_)
        z1_ = datum.up(x_, y_, z_, None)
        dz.append(round(float(z1_ - Hn[j_, i_]), 2))
        Hn[j_, i_] = z1_
        took.append((j_, i_))
    inner = shapely.contains_xy(Polygon(outline()), X, Y)
    for j_, i_ in took:
        inner[j_, i_] = False
    h0 = Hn.copy()
    fill(inner)
    d = Hn - h0
    return took, inner, dict(nodes=len(took), lo=min(dz), hi=max(dz), inner=int(inner.sum()),
                             inner_lo=round(float(d[inner].min()), 2), inner_hi=round(float(d[inner].max()), 2))


def front_lawn():
    """채플 남쪽 면과 두 잔디 사이: 1997년 스캔에서 단 · 계단 밖은 잔디(게임: 건물 둘레 포장 띠와 OSM 의 보도)"""
    band = crect(-23.3, 21.65, -30.5, -13.75).union(crect(21.65, 29.95, -14.5, -9.0))
    return band.difference(yard().buffer(0.3)).difference(porch_poly().buffer(0.05)).difference(stair_poly().buffer(0.05))


def porch_poly():
    return crect(*PORCH)


def stair_poly():
    s = STAIR
    v1 = s['top_v'] - 0.3 - (s['upper'] - 1) * s['tread'] - s['tread'] - s['mid'] - s['lower'] * s['tread']
    return crect(s['u'] - s['width'] / 2 - 0.35, s['u'] + s['width'] / 2 + 0.35, v1, s['top_v'])
