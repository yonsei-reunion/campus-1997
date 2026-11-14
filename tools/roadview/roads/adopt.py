"""찻길 조사(proposal.json, 2008 ~ 2010년)를 1997년 7월 항공사진(자료 Q)으로 걸러 게임에 넣을 것만 adopted.json 으로.

    .venv/bin/python tools/roadview/roads/adopt.py            # adopted.json 을 다시 씀
    .venv/bin/python tools/roadview/roads/adopt.py profile E 430 500 [27/16,26/15]
        # 조사한 가운데 선을 따라 6 m마다 1997년 사진의 가로 밝기 단면에서 밝은 줄(연석 · 선)의 자리를 찍음(왼쪽 +, m)

1997년 사진으로 정한 것(reference/고증/2.9_찻길.md 「노면의 선과 길가 나무」):
 - 동쪽 길의 자리. 조사 선의 거리 s 로 0 ~ 280 m 는 조사 선 그대로(삼거리 ~ 용재관 모퉁이는 1997년 사진의 길 오른쪽
   가장자리와 1 m 안, 그 뒤는 나무에 가려 보이지 않음). 296 ~ 500 m 는 1997년 사진 세 장(27/16 · 26/15 · 27/15)의 가로
   단면에서 0.3 m 안으로 겹치는 세 줄(왼쪽 연석 · 가운데 선 · 오른쪽 연석, 아래 E97)의 가운데. 조사 선보다 0.2 ~ 3.9 m 왼쪽
 - 노면 높이(PROF): 겹쳐 찍힌 사진으로 잰 길 위의 높이. 다시 투영할 때만 쓴다(게임 지형은 그대로)
 - 가운데 선: s 296 ~ 494 m 에 보임. 횡단보도 둘 · 방지턱 둘 · 정지선 하나의 자리(삼각측량, MARKS)
 - 가운데 섬의 소나무(s 385 m), 길 왼쪽의 느티나무 두 줄
조사에서 뺀 것: 1997년에 나무에 가려 보이지 않는 횡단보도 · 방지턱 · 글자(가장자리 선만 둠), 1997년에 없는 횡단보도
(s 320 · 406 m), 2010년에만 있는 것(서쪽 길 s 138 m 뒤의 선, 대우관 북쪽 길의 둥근 화단 느티나무: 1997년에는 그 자리에
세운 차), 빗금 · 볼라드 · 화살표 · 글자.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PROP = json.load(open(os.path.join(HERE, 'proposal.json')))

# 1997년 사진의 길: 조사 선의 s(6 m 칸의 가운데) -> 왼쪽 연석, 오른쪽 연석의 자리(조사 선에서 왼쪽으로 +, m)
E97 = [(305, 4.6, -3.9), (311, 4.6, -4.1), (317, 4.0, -3.6), (323, 4.2, -3.6), (329, 4.4, -3.3), (335, 4.5, -3.0),
       (341, 4.8, -2.6), (347, 5.2, -2.5), (353, 5.4, -2.4), (359, 5.6, -1.9), (365, 5.9, -2.1), (371, 7.2, -2.0),
       (377, 7.6, -1.9), (383, 7.8, -2.2), (389, 7.8, -1.6), (395, 7.8, -1.4), (401, 7.5, -0.9), (407, 7.7, 0.0),
       (413, 7.7, -0.4), (419, 7.8, -0.8), (425, 7.2, -1.1), (431, 6.9, -1.2), (437, 6.6, -1.1), (443, 6.5, -1.2),
       (449, 6.7, -1.0), (455, 7.0, -0.7), (461, 7.1, -0.5), (467, 7.2, -0.5), (473, 7.5, -0.3), (479, 7.6, -0.6),
       (485, 7.4, -1.0), (491, 7.0, -1.4), (497, 7.4, -1.4)]
E_FROM, E_TO = 8.0, 497.0          # 조사 선의 이 구간을 게임의 길로(앞은 백양로의 어귀, 뒤는 북동쪽 모퉁이)
# 겹쳐 찍힌 사진으로 잰 노면 높이(조사 선의 s, m): 상관 0.7 넘는 점, 나무 밑은 이어서
PROF = {'E': [(0, 41.0), (12, 42.7), (16, 43.3), (24, 44.5), (32, 45.7), (40, 46.2), (48, 46.9), (184, 52.8), (196, 53.6), (208, 55.0),
              (296, 62.7), (300, 63.6), (308, 63.9), (320, 65.6), (332, 67.6), (340, 68.7), (360, 71.6), (368, 72.3), (376, 73.5),
              (388, 73.8), (396, 74.6), (404, 75.6), (412, 76.3), (420, 77.2), (428, 77.7), (436, 78.1), (448, 78.9), (464, 79.7),
              (480, 80.6), (496, 81.5), (508, 82.1), (520, 81.8), (532, 80.4), (548, 78.1), (564, 76.3), (580, 74.6), (592, 73.5)],
        'W': [(0, 41.0), (20, 40.7), (32, 41.7), (36, 43.6), (40, 45.3), (44, 46.0), (60, 47.7), (104, 51.6), (108, 52.8),
              (128, 54.4), (132, 53.4), (140, 52.8), (260, 52.8)]}
# 칠한 선: (길, 쪽 L 왼쪽 가장자리 · R 오른쪽 · C 가운데, 종류, 조사 선의 s 구간, 겹선인가, 근거)
LINES = [
    ('E', 'R', 'yellow', (4, 26), False, '2008-08'), ('E', 'R', 'yellow_dash', (26, 35), False, '2008-08 용재관 진입로 어귀'),
    ('E', 'R', 'yellow', (35, 60), True, '2008-08 돌담 쪽 겹선'), ('E', 'R', 'yellow', (78, 93), False, '2008-08'),
    ('E', 'R', 'yellow', (103, 172), False, '2008-08'), ('E', 'R', 'yellow', (180, 283), False, '2008-08'),
    ('E', 'R', 'yellow', (308, 402), False, '1997 · 2008-08'), ('E', 'R', 'yellow_dash', (404, 424), False, '1997 동쪽 비탈길 어귀'),
    ('E', 'R', 'yellow', (426, 496), False, '1997 · 2008-08'),
    ('E', 'L', 'yellow', (4, 38), False, '2008-08'), ('E', 'L', 'yellow', (58, 172), False, '2008-08'),
    ('E', 'L', 'yellow', (196, 231), False, '2008-08'), ('E', 'L', 'yellow', (240, 496), False, '2008-08, s 296 뒤는 1997'),
    ('E', 'C', 'yellow', (192, 204), True, '2008-08'), ('E', 'C', 'yellow_dash', (204, 224), False, '2008-08'),
    ('E', 'C', 'yellow', (224, 281), False, '2008-08'), ('E', 'C', 'yellow', (309, 331), False, '1997'),
    ('E', 'C', 'yellow', (336, 372), False, '1997 · 2008-08'), ('E', 'C', 'yellow', (398, 494), False, '1997 · 2008-08'),
    ('W', 'L', 'yellow', (6, 110), False, '2008-08'), ('W', 'R', 'yellow', (6, 38), False, '2008-08'),
    ('W', 'R', 'yellow', (38, 56), True, '2008-08 광장 모퉁이 겹선'), ('W', 'R', 'yellow', (70, 108), False, '2008-08')]
# 노면 표시: 1997년 사진 여러 장의 밝은 덩이를 삼각측량한 자리(게임 좌표). size 는 길을 가로질러 × 길을 따라(m)
MARKS = [
    dict(kind='zebra', xy=[202.3, 352.0], size=[6.4, 5.0], src='1997(여섯 장, ±1 m) · 2008-08 s 289'),
    dict(kind='hump', xy=[211.3, 364.8], size=[7.0, 1.8], src='1997(여섯 장, 0.1 ~ 0.9 m): 길을 가로지른 5 × 1 m 흰 띠. 2008년에는 없음'),
    dict(kind='hump', xy=[206.4, 392.3], size=[7.0, 1.8], src='1997(여섯 장) · 2008-08 s 333.5'),
    dict(kind='zebra', xy=[192.5, 557.5], size=[7.0, 3.0], src='1997(세 장: 길 폭의 흰 토막 줄) · 2008-08 s 505 방지턱'),
    dict(kind='stop', xy=[186.9, 565.3], size=[5.8, 0.45], src='1997(세 장: 대우관 북쪽 길 어귀를 가로지른 흰 줄)')]
ISLAND_S = 385.0                    # 가운데 섬(소나무 한 그루): 1997년 사진 세 장의 수관으로 (194.5, 440.5) ± 1.5 m
ISLAND = [2.4, 7.0]                 # 가로 × 길이(2008년 로드뷰의 잔디 섬 3 × 7 m)
# 더할 나무: proposal.json trees_add 의 note 머리말 -> (넣는가, 크기 배율, 1997년 근거)
TREES = [('홍단풍', 1.0, '2008 · 2010'), ('흉상 섬의 큰 소나무', 1.0, '2008-08 큰 나무, 1997 닫힌 수관'),
         ('돌담 위', 1.0, '2008-08 큰 나무, 1997 닫힌 수관'), ('아펜젤러관 · 한경관 쪽 숲 띠', 1.0, '1997 닫힌 수관(자리 어림)'),
         ('동쪽 보도 안 메타세쿼이아 줄', 1.0, '2008-08 굵은 줄기'), ('서쪽 잔디 띠 느티나무 줄', 1.0, '1997 줄지은 둥근 수관'),
         ('서쪽 난간 보도 느티나무 줄', 1.0, '1997 줄지은 둥근 수관'), ('동쪽 옹벽', 0.6, '2008-08 줄기 30 cm: 1997년에는 어린 나무'),
         ('두 길 사이 숲 정원', 1.0, '1997 닫힌 수관(자리 어림)')]


def _line(key):
    cc = np.array(PROP['centre'][key], float)
    s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(cc[:, :2], axis=0).T))])
    return cc, s


def at(key, sv, off=0.0):
    """조사 선의 s 에서 왼쪽으로 off 떨어진 점(배열도 받음)"""
    cc, s = _line(key)
    sv = np.clip(np.asarray(sv, float), 0.6, s[-1] - 0.6)
    x, y = np.interp(sv, s, cc[:, 0]), np.interp(sv, s, cc[:, 1])
    tx = np.interp(sv + 0.5, s, cc[:, 0]) - np.interp(sv - 0.5, s, cc[:, 0])
    ty = np.interp(sv + 0.5, s, cc[:, 1]) - np.interp(sv - 0.5, s, cc[:, 1])
    L = np.hypot(tx, ty)
    return x - ty / L * off, y + tx / L * off


def proj(key, x, y):
    """게임 좌표 -> 조사 선의 (s, 왼쪽으로 떨어진 거리)"""
    from shapely.geometry import LineString, Point
    cc, _ = _line(key)
    sv = LineString(cc[:, :2]).project(Point(x, y))
    (x0, y0), (x1, y1) = at(key, sv - 0.5), at(key, sv + 0.5)
    px, py = at(key, sv)
    return float(sv), float((-(x - px) * (y1 - y0) + (y - py) * (x1 - x0)) / math.hypot(x1 - x0, y1 - y0))


def mid_hw(key, sv):
    """그 s 에서 게임이 쓸 길 가운데(조사 선에서 왼쪽으로, m)와 반폭"""
    cc, s = _line(key)
    sv = np.asarray(sv, float)
    hw0 = np.interp(sv, s, cc[:, 2])
    if key != 'E':
        return np.zeros_like(sv), hw0
    t = np.array(E97, float)
    ss = np.concatenate([[280.0, 293.0], t[:, 0]])
    mid = np.concatenate([[0.0, 0.5], (t[:, 1] + t[:, 2]) / 2])
    hw = np.concatenate([[3.2, 3.3], (t[:, 1] - t[:, 2]) / 2])
    k = np.exp(-0.5 * (np.arange(-3, 4) / 1.2) ** 2)                # (판독의 ±0.2 m 흔들림을 고름: 6 m 칸 셋)
    k /= k.sum()
    sm = lambda v: np.convolve(np.pad(v, 3, mode='edge'), k, mode='valid')
    mid[2:], hw[2:] = sm(mid[2:]), sm(hw[2:])
    return np.where(sv < 280, 0.0, np.interp(sv, ss, mid)), np.where(sv < 280, hw0, np.interp(sv, ss, hw))


def adopted_xy(key, sv, off=0.0):
    """게임이 쓸 길 가운데에서 왼쪽으로 off 떨어진 점"""
    m, _ = mid_hw(key, sv)
    return at(key, sv, m + off)


def build():
    sv = np.arange(E_FROM, E_TO + 0.1, 3.0)
    m, hw = mid_hw('E', sv)
    x, y = at('E', sv, m)
    out = dict(note='tools/roadview/roads/adopt.py 가 씀: proposal.json(2008 ~ 2010년 조사)을 1997년 7월 항공사진으로 거른 것',
               E=dict(centre=[[round(float(a), 2), round(float(b), 2), round(float(c), 2)] for a, b, c in zip(x, y, hw)]),
               lines=[], marks=MARKS, trees=[])
    for road, side, kind, (s0, s1), dbl, src in LINES:
        pa, pb = adopted_xy(road, s0), adopted_xy(road, s1)
        out['lines'].append(dict(road=road, side=side, kind=kind, double=dbl, s=[s0, s1],
                                 a=[round(float(v), 2) for v in pa], b=[round(float(v), 2) for v in pb], src=src))
    ix, iy = adopted_xy('E', ISLAND_S)
    hx, hy = adopted_xy('E', ISLAND_S + 1.0)
    out['island'] = dict(xy=[round(float(ix), 2), round(float(iy), 2)], size=ISLAND,
                         heading=round(math.degrees(math.atan2(hy - iy, hx - ix)), 1),
                         src='1997(세 장의 수관: 길 가운데의 나무 한 그루) · 2008-08 잔디 섬과 기운 소나무')
    for t in PROP['trees_add']:
        rule = next((r for r in TREES if t['note'].startswith(r[0])), None)
        if rule is None:
            continue
        x, y = t['xy']
        if x > 60:                                   # 동쪽 길가: 길이 옮겨진 만큼 함께(길과의 거리를 지킴)
            s_, o_ = proj('E', x, y)
            if E_FROM < s_ < E_TO:
                x, y = (float(v) for v in adopted_xy('E', s_, o_))
        out['trees'].append([t['species'], round(x, 2), round(y, 2), round(t['scale'] * rule[1], 2), rule[0], rule[2]])
    out['trees'].append(['pine', out['island']['xy'][0], out['island']['xy'][1], 0.9, '가운데 섬의 소나무', out['island']['src']])
    json.dump(out, open(os.path.join(HERE, 'adopted.json'), 'w'), ensure_ascii=False, indent=1)
    print('adopted.json: centre E %d points (%.0f m), lines %d, marks %d, trees %d' % (
        len(out['E']['centre']), E_TO - E_FROM, len(out['lines']), len(out['marks']), len(out['trees'])))
    for s_ in (300, 350, 385, 430, 470, 497):
        print('  s %d: 조사 선에서 %.1f m 왼쪽, 반폭 %.1f m, (%.1f, %.1f)' % (s_, *(float(v) for v in mid_hw('E', s_)),
                                                                    *(float(v) for v in adopted_xy('E', s_))))


def profile(key, s0, s1, frames):
    """조사 선을 따라 6 m마다 가로 밝기 단면의 봉우리: 사진마다 「자리(밝기)」. 사진끼리 겹치면 높이(PROF)가 맞은 것"""
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import aerial97 as A
    from scipy.signal import find_peaks
    ov = np.arange(11.0, -11.05, -0.1)
    pz = np.array(PROF[key])
    for sa in np.arange(s0, s1, 6.0):
        SS, OO = np.meshgrid(np.arange(sa, sa + 6.0, 0.25), ov)
        X, Y = at(key, SS, OO)
        Z = np.interp(SS, pz[:, 0], pz[:, 1])
        row = []
        for fr in frames:
            p = A.to_px(fr, X, Y, Z)
            pr = np.median(np.nan_to_num(A.sample(fr, p[..., 0], p[..., 1])), axis=1)
            row.append(' '.join('%+.1f(%d)' % (ov[i], pr[i]) for i in find_peaks(pr, prominence=6)[0]))
        print('s %5.0f | %s' % (sa + 3, ' | '.join(row)))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'profile':
        fr = [tuple(int(v) for v in t.split('/')) for t in sys.argv[5].split(',')] if len(sys.argv) > 5 else [(27, 16), (26, 15), (27, 15)]
        profile(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), fr)
    else:
        build()
