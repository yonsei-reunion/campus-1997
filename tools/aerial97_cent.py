"""1997년 7월 항공사진(자료 Q)으로 백주년기념관 원통 서쪽 발치의 낮은 몸체를 재는 도구 (reference/고증/3.4 「낮은 몸체의 윤곽」).

몸체의 틀 (u, v)로 봄: 원점은 #164 전의 게임 몸체 모서리 (-26.43, -256.11)(백양로 쪽 면 선에서 1 m 서쪽, 면을 따라
북서 모서리에서 76.4 m), u 는 앞면을 따라 동쪽, v 는 백양로 쪽 면을 따라 북쪽. 면 선은 u = 1, 원통 가운데는 (17.3, 18.7).

  .venv/bin/python tools/aerial97_cent.py view <out.png> <z> <u0,u1,v0,v1> <사진> [사진 ...]
      높이 z 의 수평면에 다시 투영한 조각을 나란히(노랑: 게임 몸체, 주황: 게임 원통, 초록: 면 선)
  .venv/bin/python tools/aerial97_cent.py west <v0,v1> [v0,v1 ...]
      서쪽 지붕 끝(서쪽 어두움 → 동쪽 밝음)의 u 를 평면 높이마다, 사진 26/16 · 26/15 · 27/17 에서.
      서쪽 사진(26/16)과 동쪽 사진(27/17)의 값이 같아지는 높이가 지붕 끝의 높이(높이 1 m 에 0.72 m 벌어짐).
      27/17 은 원통 지붕에 가리지 않는 v < 10 에서만 씀
  .venv/bin/python tools/aerial97_cent.py edge <z>
      그 높이에서 서쪽 지붕 끝의 u 를 v 3 m 창마다, 호 부분은 원통 가운데에서의 반지름으로(26/16 · 26/15)

이 사진에서 원통의 서쪽 벽은 그늘이고 낮은 지붕의 바깥쪽 1 ~ 2 m 가 밝은 띠로 보임. 그 띠의 서쪽 끝이 지붕 끝.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aerial97 as A                                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_C = json.load(open(os.path.join(ROOT, 'web/public/data/campus.json')))
_K = _C['centennial_block']
TF, TS = np.array(_K['t_front']), np.array(_K['t_side'])
C0 = np.array([-26.43, -256.11])            # 틀의 원점(게임 몸체를 옮겨도 기록의 u, v 가 그대로이게 묶어 둠)
DRUM, R = np.array([-5.49, -242.53]), 17.0


def xy(u, v):
    return C0[0] + TF[0] * u + TS[0] * v, C0[1] + TF[1] * u + TS[1] * v


def uv(x, y):
    """게임 좌표 -> 틀(앞면과 옆면이 92° 라 빗각 틀: 내적이 아니라 연립으로 풂)"""
    u, v = np.linalg.solve(np.array([TF, TS]).T, np.array([x, y]) - C0)
    return float(u), float(v)


def grid(fr, z, u0, u1, v0, v1, res=0.1):
    us, vs = np.arange(u0, u1, res), np.arange(v1, v0, -res)
    U, V = np.meshgrid(us, vs)
    X, Y = xy(U, V)
    p = A.to_px(fr, X, Y, np.full(X.shape, z))
    return A.sample(fr, p[..., 0], p[..., 1]), us, vs


def _fr(a):
    return tuple(int(v) for v in a.split('/'))


def _edge(us, p, lo, hi):
    """lo < u < hi 에서 동쪽으로 가장 가파르게 밝아지는 곳(2차 보간)과 그 세기(밝기 / m)"""
    g = np.gradient(p)
    k = int(np.argmax(np.where((us > lo) & (us < hi), g, -1e9)))
    k = min(max(k, 1), len(g) - 2)
    a, b, c = g[k - 1], g[k], g[k + 1]
    du = us[1] - us[0]
    return us[k] + du * 0.5 * (a - c) / (a - 2 * b + c + 1e-9), g[k] / du


def _prof(fr, z, v0, v1, u0=-10.0, u1=3.0):
    from scipy.ndimage import gaussian_filter1d
    G, us, _ = grid(fr, z, u0, u1, v0, v1)
    return us, gaussian_filter1d(np.median(G, 0), 1.5)


def cmd_view(out, z, box, frs):
    from PIL import Image, ImageDraw
    u0, u1, v0, v1 = box
    res, sc, tiles = 0.1, 3, []
    for fr in frs:
        G, _, _ = grid(fr, z, u0, u1, v0, v1, res)
        lo, hi = np.percentile(G, 1), np.percentile(G, 99.5)
        im = Image.fromarray((((G - lo) / (hi - lo)).clip(0, 1) ** 0.6 * 255).astype('uint8')).convert('RGB')
        im = im.resize((im.size[0] * sc, im.size[1] * sc), Image.BICUBIC)
        d = ImageDraw.Draw(im)
        P = lambda u, v: ((u - u0) / res * sc, (v1 - v) / res * sc)        # noqa: E731
        for u in range(int(math.ceil(u0 / 5) * 5), int(u1) + 1, 5):
            for v in range(int(math.ceil(v0 / 5) * 5), int(v1) + 1, 5):
                x, y = P(u, v)
                d.line([x - 4, y, x + 4, y], fill=(0, 255, 255))
                d.line([x, y - 4, x, y + 4], fill=(0, 255, 255))
                d.text((x + 3, y + 2), '%d,%d' % (u, v), fill=(0, 255, 255))
        b = [uv(*q) for q in _K['poly']]
        d.line([P(*q) for q in b + b[:1]], fill=(255, 220, 0))
        cu, cv = uv(*DRUM)
        d.ellipse([P(cu - R, cv + R), P(cu + R, cv - R)], outline=(255, 140, 0))
        d.line([P(1, v0), P(1, v1)], fill=(0, 255, 0))
        d.text((6, 6), '%d/%d z %.1f' % (*fr, z), fill=(255, 255, 0))
        tiles.append(im)
    big = Image.new('RGB', (sum(t.size[0] for t in tiles) + 4 * (len(tiles) - 1), tiles[0].size[1]), (255, 0, 255))
    x = 0
    for t in tiles:
        big.paste(t, (x, 0))
        x += t.size[0] + 4
    big.save(out)
    print(out, big.size)


def cmd_west(wins):
    frs = [(26, 16), (26, 15), (27, 17)]
    for v0, v1 in wins:
        print('v %g ~ %g: 평면 높이, 서쪽 끝 u (세기) 26/16 · 26/15 · 27/17, 26/16 - 27/17' % (v0, v1))
        for z in np.arange(33, 42.01, 1.0):
            row = [_edge(*_prof(fr, z, v0, v1), -9, 1.5) for fr in frs]
            print('  z %.0f  ' % z + '  '.join('%5.2f (%3.0f)' % r for r in row) + '   %5.2f' % (row[0][0] - row[2][0]))


def cmd_edge(z):
    from scipy.ndimage import gaussian_filter1d
    frs = [(26, 16), (26, 15)]
    print('곧은 부분: v 창, 서쪽 끝 u (세기) 26/16 · 26/15')
    for v0 in np.arange(1, 34, 3.0):
        row = [_edge(*_prof(fr, z, v0, v0 + 3), -8, 1.5) for fr in frs]
        print('  v %4.1f ~ %4.1f   %5.2f (%3.0f)   %5.2f (%3.0f)' % (v0, v0 + 3, *row[0], *row[1]))
    TA = math.atan2(TF[1], TF[0])
    print('호 부분: 원통 가운데 둘레의 각(앞면 방향에서 잼, 180° 가 서쪽) 창, 끝의 반지름 26/16 · 26/15')
    rs = np.arange(17.5, 24, 0.1)           # (원통 지붕 테 밖에서만 찾음)
    for t0 in np.arange(130, 200, 10.0):
        row = []
        for fr in frs:
            T, Rr = np.meshgrid(np.radians(np.arange(t0, t0 + 10, 0.5)), rs)
            X, Y = DRUM[0] + Rr * np.cos(T + TA), DRUM[1] + Rr * np.sin(T + TA)       # (게임 좌표에서 돌림: 참 반지름)
            p = A.to_px(fr, X, Y, np.full(X.shape, z))
            g = np.gradient(gaussian_filter1d(np.median(A.sample(fr, p[..., 0], p[..., 1]), 1), 1.5)[::-1])
            k = int(np.argmax(g[5:-5])) + 5
            row.append(rs[::-1][k])
        print('  %3.0f ~ %3.0f°  %5.2f   %5.2f' % (t0, t0 + 10, *row))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['view']:
        cmd_view(a[1], float(a[2]), [float(v) for v in a[3].split(',')], [_fr(f) for f in a[4:]])
    elif a[:1] == ['west']:
        cmd_west([tuple(float(v) for v in w.split(',')) for w in a[1:]] or [(2.5, 6.5), (6.0, 10.0)])
    elif a[:1] == ['edge']:
        cmd_edge(float(a[1]))
    else:
        print(__doc__)
