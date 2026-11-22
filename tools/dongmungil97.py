"""연대동문길(한국어학당 앞을 지나 대신동 쪽으로 내려가는 찻길)의 가로수: 백합나무(튤립나무) 두 줄
(reference/고증/3.27_한국어학당.md 「연대동문길의 가로수」).

1996년 겨울(잎이 진) 원본 스캔 27/15 · 27/16 · 27/17 을 길을 따라 편 띠(땅 높이: 그 세 장으로 잰 노면)로 읽은 밑동:
세 장에서 같은 자리의 어두운 점(줄기 밑)이고, 27/15 와 27/17 에서는 그 점에서 서로 반대쪽으로 줄기가 눕고(카메라가
길의 북쪽 · 남쪽 하늘), 거의 바로 위에서 찍은 27/16 에서는 가지가 방사로 퍼진 수관이 그 위에 있는 것만 넣었다.
BASES 는 그 밑동의 자리(세 장의 평균, 게임 좌표)와 길의 어느 쪽인지. 세 장 사이의 흩어짐은 동쪽 줄 0.0 ~ 0.33 m,
서쪽 줄 0.17 ~ 0.87 m.

1996년 띠에서 두 줄은 어두운 연석선(줄기 그림자와 겹침) 위에 서고, 그 두 선 사이(차도)는 8 m 남짓이다. 게임의 길
(service, 폭 6 m)은 그보다 좁고 가운데가 1 m 남짓 서쪽이라, 밑동을 길의 축에 수직으로 옮겨 길 가장자리에서 0.45 m
바깥에 세운다(길을 따른 자리는 스캔대로). 옮긴 거리는 동쪽 줄 1.5 ~ 1.8 m, 서쪽 줄 0.3 ~ 1.3 m: 카메라 블록의 평면
정밀도(1.5 m 안팎)와 같은 크기여서, 한 사진 안에서 잰 「연석과 줄기의 사이」를 따랐다.

    trees = dongmungil97.trees(out['paths'], out['trees'])   # build_campus.py 맨 끝: 나무 목록의 끝에 더함
"""
import math
import random

from shapely.geometry import LineString, Point

# (x, y, 쪽): 1996년 겨울 세 장으로 읽은 밑동(게임 좌표, m), 'E' 는 한국어학당 쪽, 'W' 는 청송대 쪽
BASES = (
    (458.98, 127.67, 'E'), (460.56, 123.24, 'E'), (461.91, 119.48, 'E'), (463.42, 114.92, 'E'),
    (465.13, 109.80, 'E'), (466.83, 105.31, 'E'), (469.92, 95.37, 'E'),
    (466.82, 79.04, 'W'), (471.55, 64.81, 'W'), (479.46, 41.13, 'W'), (481.01, 36.69, 'W'), (503.31, -18.76, 'W'),
)
SPECIES = 'tulip'                    # blender/vegetation.py SPECIES['tulip'], tools/make_textures.py leaf_tulip*
OUT = 0.45                           # 길 가장자리에서 줄기까지(m)
PROBES = ((445.0, 154.0), (476.0, 60.0), (490.0, 20.0))    # 게임의 그 길(service)을 찾는 점


def road(paths):
    """게임의 연대동문길: PROBES 셋에 모두 2 m 안인 service 길(선, 폭)"""
    for p in paths:
        if p.get('kind') != 'service' or len(p['pts']) < 2:
            continue
        line = LineString([q[:2] for q in p['pts']])
        if all(line.distance(Point(*q)) < 2.0 for q in PROBES):
            return line, float(p['w'])
    raise ValueError('연대동문길(service) not found')


def trees(paths, old_trees=()):
    """campus.json trees 항목들. 나무 목록의 맨 끝에 붙인다(웹은 목록 차례로 모델을 고름).
    old_trees 에서 새 줄기 1.5 m 안의 나무가 있으면 알린다(옮기지 않음)"""
    line, w = road(paths)
    rnd = random.Random(231)
    out = []
    for x, y, side in BASES:
        s = line.project(Point(x, y))
        a, b = line.interpolate(max(0.0, s - 1.0)), line.interpolate(min(line.length, s + 1.0))
        tx, ty = b.x - a.x, b.y - a.y
        n = math.hypot(tx, ty)
        nx, ny = -ty / n, tx / n                      # 길의 왼쪽
        q = line.interpolate(s)
        sign = 1.0 if (x - q.x) * nx + (y - q.y) * ny > 0 else -1.0
        assert (sign > 0) == ((nx > 0) == (side == 'E')), (x, y, side)
        dd = sign * (w / 2 + OUT)
        px, py = q.x + nx * dd, q.y + ny * dd
        out.append([SPECIES, round(px, 2), round(py, 2), round(rnd.uniform(0.92, 1.06), 2), round(rnd.uniform(0, 6.28), 2)])
    near = [(t[0], t[1], t[2], round(math.dist(t[1:3], o[1:3]), 2)) for t in out for o in old_trees
            if math.dist(t[1:3], o[1:3]) < 1.5]
    return out, near
