"""세운 차가 서로 · 나무 · 관목 · 건물 외곽선과 겹치는지 campus.json 만으로 본다(게임을 띄우지 않음).

  .venv/bin/python .claude/skills/walk-probe/cars.py [--near x,y,r ...] [--campus <campus.json>]

  --near    그 둘레의 차만(가운데 x,y 와 반지름 r m). 여러 번 줄 수 있다. 없으면 전부
  --campus  기본 web/public/data/campus.json

보는 것
- 차 / 차: 네모(모델의 전체 길이 × 폭)가 겹침
- 차 / 나무: 줄기(반지름 0.25 m)가 차 네모 안
- 차 / 관목: 관목 자리가 차 네모 안
- 차 / 건물: 차 네모가 건물 외곽선과 겹침
못 보는 것(게임 안에서 봐야 함: SKILL.md)
- 벽 · 옹벽 · 계단에 박힌 차: 그것들은 랜드마크 메시라 외곽선에 없다
- 기울어 누운 차: 차가 서는 면은 지형이 아니라 걷는 면(데크 · 테라스 포함)이라 지형 격자로는 틀린 값이 나온다

차의 크기는 blender/cars.py SPECS 의 전체 길이(L + 범퍼) · 폭 W 를 옮겨 적은 것이다. 모델을 고치면 여기도 고친다.
"""
import json
import math
import os
import sys

from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
SIZE = {'sedan': (4.70, 1.77), 'sedan2': (4.80, 1.72), 'hatch': (3.57, 1.605), 'tico': (3.34, 1.40), 'van': (4.70, 1.69),
        'taxi': (4.70, 1.77)}


def rect(k, x, y, a, grow=0.0):
    L, W = SIZE.get(k, (4.6, 1.75))
    c, s = math.cos(a), math.sin(a)
    h, w = L / 2 + grow, W / 2 + grow
    return Polygon([(x + u * c - v * s, y + u * s + v * c) for u, v in ((h, w), (h, -w), (-h, -w), (-h, w))])


def main(argv):
    near, campus = [], os.path.join(ROOT, 'web/public/data/campus.json')
    while argv:
        k = argv.pop(0)
        if k == '--near':
            near.append(tuple(float(v) for v in argv.pop(0).split(',')))
        elif k.startswith('--near='):
            near.append(tuple(float(v) for v in k[7:].split(',')))
        elif k == '--campus':
            campus = argv.pop(0)
        else:
            sys.exit(__doc__)
    c = json.load(open(campus))
    cars = [(i, q) for i, q in enumerate(c['cars']) if not near or any(math.hypot(q[1] - x, q[2] - y) <= r for x, y, r in near)]
    R = {i: rect(q[0], q[1], q[2], q[3]) for i, q in cars}
    tag = lambda i: '[%d] %s (%.1f, %.1f)' % (i, c['cars'][i][0], c['cars'][i][1], c['cars'][i][2])
    n = 0
    ids = list(R)
    tree = STRtree([R[i] for i in ids])
    for a, i in enumerate(ids):
        for b in tree.query(R[i]):
            j = ids[int(b)]
            if j > i and R[i].intersection(R[j]).area > 0.05:
                print('차/차   %s  x  %s  겹친 넓이 %.2f m²' % (tag(i), tag(j), R[i].intersection(R[j]).area))
                n += 1
    for name, rows, rad in (('나무', c['trees'], 0.25), ('관목', c['shrubs'], 0.0)):
        pts = [Point(t[1], t[2]) for t in rows]
        tr = STRtree(pts)
        for i in ids:
            for b in tr.query(R[i].buffer(rad)):
                if R[i].buffer(rad).contains(pts[int(b)]):
                    t = rows[int(b)]
                    print('차/%s %s  x  [%d] %s (%.1f, %.1f)' % (name, tag(i), int(b), t[0], t[1], t[2]))
                    n += 1
    fps = [(bd, Polygon(bd['footprint']).buffer(0)) for bd in c['buildings'] if len(bd.get('footprint', [])) >= 3]
    bt = STRtree([p for _, p in fps])
    for i in ids:
        for b in bt.query(R[i]):
            bd, p = fps[int(b)]
            ar = R[i].intersection(p).area
            if ar > 0.05:
                print('차/건물 %s  x  %s (%s)  겹친 넓이 %.2f m²' % (tag(i), bd.get('name') or bd.get('id'), bd.get('style'), ar))
                n += 1
    print('차 %d대 가운데 적힌 것 %d' % (len(ids), n))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
