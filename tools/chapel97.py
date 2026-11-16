"""루스채플 남쪽 마당 (reference/고증/2.10 「루스채플 남쪽 마당의 땅」).

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
