"""1997년 7월 항공사진(자료 Q)으로 백양로 차도 · 둥근 것 · 지붕 모서리의 자리를 재는 도구 (#161, reference/고증/2.1-2.2 2.2.2).

  .venv/bin/python tools/aerial97_check.py road <s0> <s1> [창 m] [사진,사진,...]
      백양로 차도 가운데: 창마다 가로 단면(길 방향 중앙값)에 「생울타리 두 줄 + 그 사이 밝은 차도」 틀을 맞춤.
      게임 중심선에서 동쪽으로 몇 m인지와 반폭 h, 상관을 사진마다
  .venv/bin/python tools/aerial97_check.py circle <x> <y> <r 최소> <r 최대> [사진 ...]
      땅 높이 정사 조각에서 둥근 테두리(밝기가 바뀌는 원)의 가운데와 반지름. 독수리상 고리, 활천대 수반
  .venv/bin/python tools/aerial97_check.py roof <x> <y> <반쪽 m> <높이,높이,...> <r 최소> <r 최대> [사진 ...]
      그 높이의 수평면에서 둥근 지붕 테(백주년기념관 원통). 사진끼리 가운데가 모이는 높이가 테의 높이
  .venv/bin/python tools/aerial97_check.py edge <ax> <ay> <bx> <by> <t0> <t1> <높이,높이,...> [사진 ...]
      게임 선 a -> b 를 따라 t0 ~ t1 m 구간의 지붕 모서리가 선에서 오른쪽으로 몇 m인지(높이마다, 사진마다).
      사진끼리 값이 모이는 높이에서 읽음

사진은 「26/16」 꼴, 주지 않으면 26/15 · 26/16 · 27/16 · 27/17.
"""
import json
import math
import os
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aerial97 as A                                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FR0 = [(26, 15), (26, 16), (27, 16), (27, 17)]


def frames(args):
    return [tuple(int(v) for v in a.split('/')) for a in args] or FR0


def centre_line():
    from shapely.geometry import LineString
    c = json.load(open(os.path.join(ROOT, 'web/public/data/campus.json')))
    L = LineString(c['baekyangro']['pts'])

    def along(s, off):
        """중심선의 s 에서 서쪽으로 off m 인 점"""
        p = L.interpolate(s)
        p2, p0 = L.interpolate(min(L.length, s + 1)), L.interpolate(max(0.0, s - 1))
        tx, ty = p2.x - p0.x, p2.y - p0.y
        n = math.hypot(tx, ty)
        return p.x - ty / n * off, p.y + tx / n * off
    return L, along


def cmd_road(s0, s1, win, frs):
    L, along = centre_line()
    oo = np.arange(-16, 6.01, 0.1)                       # 서쪽 +
    for a in np.arange(s0, min(s1, L.length - win - 1), win):
        ss = np.arange(a, a + win, 0.3)
        XY = np.array([[along(s, o) for s in ss] for o in oo])
        X, Y = XY[..., 0], XY[..., 1]
        out = []
        for fr in frs:
            p = A.to_px(fr, X, Y, A.ground(X, Y))
            if not A.inside(fr, p[..., 0], p[..., 1], 30).all():
                out.append('%d/%d      -       ' % fr)
                continue
            pr = np.median(A.sample(fr, p[..., 0], p[..., 1]), 1)
            pr = (pr - pr.mean()) / (pr.std() + 1e-6)
            best = (-2, 0, 0)
            for cc in np.arange(-12, 2.01, 0.1):
                for h in np.arange(4.3, 5.81, 0.1):
                    t = np.zeros_like(oo)
                    t[np.abs(oo - (cc + h)) < 0.6] = -1
                    t[np.abs(oo - (cc - h)) < 0.6] = -1
                    t[np.abs(oo - cc) < h - 1.2] = 1
                    m = np.abs(oo - cc) < h + 1.5
                    r = np.corrcoef(pr[m], t[m])[0, 1]
                    if r > best[0]:
                        best = (r, cc, h)
            out.append('%d/%d %+5.2f h%.1f (%.2f)' % (*fr, -best[1], best[2], best[0]))
        print('s %3d-%3d  ' % (a, a + win) + '  '.join(out), flush=True)


def _circle(G, x0, y0, half, res, rlo, rhi, span=4.0, step=0.1):
    th = np.linspace(0, 2 * np.pi, 240, endpoint=False)
    gx, gy = ndi.sobel(G, 1), ndi.sobel(G, 0)
    best = (-1,)
    for cx in np.arange(x0 - span, x0 + span + 1e-6, step):
        for cy in np.arange(y0 - span, y0 + span + 1e-6, step):
            for r in np.arange(rlo, rhi + 1e-6, step):
                px = (cx + r * np.cos(th) - (x0 - half)) / res
                py = ((y0 + half) - (cy + r * np.sin(th))) / res
                v = ndi.map_coordinates(gx, [py, px], order=1) * np.cos(th) - ndi.map_coordinates(gy, [py, px], order=1) * np.sin(th)
                if abs(v.mean()) > best[0]:
                    best = (abs(v.mean()), cx, cy, r)
    return best[1:]


def cmd_circle(x0, y0, rlo, rhi, frs):
    half, res = 14.0, 0.1
    dz, _ = A.ground_offset(x0, y0, 20)
    cs = []
    for fr in frs:
        G = ndi.gaussian_filter(A.ortho(fr, x0, y0, half, res, None, dz), 2.0)
        cx, cy, r = _circle(G, x0, y0, half, res, rlo, rhi)
        cs.append((cx, cy))
        print('%d/%d 가운데 (%.2f, %.2f) 반지름 %.2f' % (*fr, cx, cy, r))
    c = np.array(cs)
    print('평균 (%.2f, %.2f), 사진끼리 표준편차 (%.2f, %.2f) m, 땅 높이 지형 %+.1f m' % (*c.mean(0), *c.std(0), dz))


def cmd_roof(x0, y0, half, zs, rlo, rhi, frs):
    res = 0.15
    for z in zs:
        cs = []
        for fr in frs:
            G = ndi.gaussian_filter(A.ortho(fr, x0, y0, half, res, z), 1.5)
            cx, cy, r = _circle(G, x0, y0, half, res, rlo, rhi, span=6.0, step=0.25)
            cs.append((cx, cy))
            print('  z %.1f %d/%d 가운데 (%.2f, %.2f) 지름 %.1f' % (z, *fr, cx, cy, 2 * r))
        c = np.array(cs)
        print('z %.1f: 평균 (%.2f, %.2f), 사진끼리 표준편차 (%.2f, %.2f) m' % (z, *c.mean(0), *c.std(0)))


def cmd_edge(ax, ay, bx, by, t0, t1, zs, frs):
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    rx, ry = uy, -ux
    T, U = np.meshgrid(np.arange(t0, t1, 0.25), np.arange(-8, 8.01, 0.1))
    X, Y = ax + ux * T + rx * U, ay + uy * T + ry * U
    for z in zs:
        row = []
        for fr in frs:
            p = A.to_px(fr, X, Y, np.full(X.shape, z))
            g = np.gradient(np.convolve(A.sample(fr, p[..., 0], p[..., 1]).mean(1), np.ones(5) / 5, 'same'))
            g[:5] = g[-5:] = 0
            i = np.argmax(np.abs(g))
            row.append('%d/%d %+.2f' % (*fr, U[i, 0]))
        print('z %.1f: ' % z + '  '.join(row))


if __name__ == '__main__':
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd == 'road':
        cmd_road(float(a[0]), float(a[1]), float(a[2]) if len(a) > 2 else 20.0, frames(a[3].split(',') if len(a) > 3 else []))
    elif cmd == 'circle':
        cmd_circle(*map(float, a[:4]), frames(a[4:]))
    elif cmd == 'roof':
        cmd_roof(float(a[0]), float(a[1]), float(a[2]), [float(v) for v in a[3].split(',')], float(a[4]), float(a[5]), frames(a[6:]))
    elif cmd == 'edge':
        cmd_edge(*map(float, a[:6]), [float(v) for v in a[6].split(',')], frames(a[7:]))
