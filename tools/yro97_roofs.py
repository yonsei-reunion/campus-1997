"""연세로 양쪽 가게 줄의 1997년 7월 지붕 높이(reference/고증/4.10.8_연세로_가게_줄.md 「잰 법」 · 「집」의 표).

    .venv/bin/python tools/yro97_roofs.py [out.json]

양쪽 줄을 따라 2.5 m 마다, 앞벽 뒤 4 m 와 8 m 에서 2.5 m 창의 표면 높이를 사진 두 장씩으로 재고(tools/aerial97.py
surface_z), tools/yro97.py ROWS 의 집마다 그 안 점들의 중앙값을 보도 위 높이로 적는다. 상관 0.6 아래와 쌍끼리 2.5 m 넘게
갈리는 점은 버린다. 사진은 저장소 밖(assets_src/aerial_1997, reference/고증/1.5).
"""
import json
import statistics as st
import sys

import numpy as np
from shapely.geometry import Point

import aerial97 as A
import aerial_resect
import gate_town as gt
import sinchon_rotary as sr
import yro97

aerial_resect.register()
YA = sr.Arm('yonsei', sr.ARMS['yonsei'])
PAIRS_N = [((26, 16), (27, 17)), ((26, 16), (27, 18)), ((27, 17), (27, 18))]              # north of y -700
PAIRS_S = [((27, 18), (27, 19)), ((27, 18), (27, 20)), ((27, 19), (27, 20)), ((26, 16), (27, 18))]


def mid_x(y):
    return gt.YONSEI_X if y > -640 else YA.ls.interpolate(YA.ls.project(Point(-97, y))).x


def front(y, side):
    return 12.0 if y > -640 else (9.5 if side > 0 else 10.5)


def survey():
    out = []
    for side in (1, -1):
        for y in np.arange(-512.0, -926.0, -2.5):
            for off in (4.0, 8.0):
                x = mid_x(y) + side * (front(y, side) + off)
                g = A.ground(x, y)
                res = []
                for pr in (PAIRS_N if y > -700 else PAIRS_S):
                    if not all(A.inside(f, *A.to_px(f, x, y, g), 60) for f in pr):
                        continue
                    pk, _ = A.surface_z(x, y, win=2.5, lo=-3.0, hi=40.0, frames=list(pr))
                    if pk:
                        res.append((round(float(pk[0][0]), 2), round(float(pk[0][1] - g), 1)))
                out.append(dict(side=side, y=float(y), off=off, x=round(x, 1), res=res))
    return out


def good(r):
    h = sorted(z for s, z in r['res'] if s >= 0.6)
    return st.median(h) if h and h[-1] - h[0] <= 2.5 else None


if __name__ == '__main__':
    R = survey()
    if len(sys.argv) > 1:
        json.dump(R, open(sys.argv[1], 'w'))
    for side in (1, -1):
        print('동쪽' if side > 0 else '서쪽')
        for yn, ys, lv, wall, dep, shops in yro97.ROWS[side]:
            hs = sorted(h for h in (good(r) for r in R if r['side'] == side and ys + 1.0 <= r['y'] <= yn - 1.0) if h is not None)
            print('  y %7.1f .. %7.1f  %d층  %s' % (yn, ys, lv, ('%.1f m (%.1f .. %.1f, %d점)' % (st.median(hs), hs[0], hs[-1], len(hs))) if hs else '읽지 못함'))
