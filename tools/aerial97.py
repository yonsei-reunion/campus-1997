"""1997년 7월 28일 항공사진(서울특별시청 1997년 1차, 1:5,000)을 게임 좌표로 보는 도구.

사진은 저장소에 넣지 않는다(라이선스 유형을 확인하지 못함). assets_src/aerial_1997/ (git 밖)에 두며, 없으면
assets_src/aerial_1997/README.md 의 순서로 국토정보플랫폼에서 다시 받는다.

  .venv/bin/python tools/aerial97.py crop <x> <y> <반쪽 m> <out.png> [frame] [zoom]
      게임 좌표 (x, y) 둘레를 잘라 10 m 격자와 건물 외곽선을 겹쳐 그림(저장소 밖에 쓸 것)
  .venv/bin/python tools/aerial97.py where <x> <y>
      그 점이 찍힌 사진과 화소

자리는 국토정보플랫폼이 사진마다 주는 범위(EPSG:5179 의 네모)에 사진을 그대로 편 1차 근사다. 사진은 정사영상이
아니라서(초점 거리 152.85 mm, 땅 위 약 765 m) 높이 h 인 점은 사진 주점에서 멀어지는 쪽으로 r · h / 765 만큼 밀린다.
잴 때는 둘레의 바뀌지 않은 건물 발치 · 길 모서리로 그 자리의 어긋남을 먼저 재서 뺀다.
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'assets_src/aerial_1997')
ZONE = '199705A0301'          # 사업코드: 지자체 공간정보(서울특별시청1997년1차), 촬영일자 1997-07-28
# 코스, 사진 번호: 범위 (minx, miny, maxx, maxy; EPSG:5179), 화소 크기
FRAMES = {
    (26, 14): ((949480.4583, 1951651.8687, 950835.4960, 1953092.0979), (2643, 2811)),
    (26, 15): ((949471.9824, 1951186.0799, 950827.0195, 1952626.3084), (2643, 2811)),
    (26, 16): ((949464.5, 1950718.7, 950821.1, 1952160.5), (2646, 2814)),
    (27, 15): ((950103.2, 1951641.0, 951458.2, 1953081.8), (2643, 2812)),
    (27, 16): ((950079.8, 1951198.8, 951434.9, 1952639.1), (2643, 2811)),
    (27, 17): ((950055.5, 1950755.6, 951410.5, 1952196.4), (2643, 2812)),
}
LON0, LAT0 = 126.938, 37.564                      # 게임 원점 (tools/build_campus.py xy())
KX, KY = 111320 * math.cos(math.radians(LAT0)), 110574


def tm5179(lat, lon):
    """위경도(GRS80) -> EPSG:5179 (UTM-K: 원점 38N 127.5E, 축척 0.9996, 가산 1,000,000 / 2,000,000)"""
    a, f = 6378137.0, 1 / 298.257222101
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    k0, lon0, lat0 = 0.9996, math.radians(127.5), math.radians(38.0)

    def M(p):
        return a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * p - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * p)
                    + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * p) - (35 * e2 ** 3 / 3072) * math.sin(6 * p))
    p, l = math.radians(lat), math.radians(lon)
    N = a / math.sqrt(1 - e2 * math.sin(p) ** 2)
    T, C, A = math.tan(p) ** 2, ep2 * math.cos(p) ** 2, (l - lon0) * math.cos(p)
    x = k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T * T + 72 * C - 58 * ep2) * A ** 5 / 120)
    y = k0 * (M(p) - M(lat0) + N * math.tan(p) * (A * A / 2 + (5 - T + 9 * C + 4 * C * C) * A ** 4 / 24
                                                    + (61 - 58 * T + T * T + 600 * C - 330 * ep2) * A ** 6 / 720))
    return 1000000.0 + x, 2000000.0 + y


def game_to_5179(x, y):
    return tm5179(LAT0 + y / KY, LON0 + x / KX)


# 맞춘 카메라(reference/고증/1_자료.md 「자료 Q」): 사진 주점을 영상 가운데로, 고도를 815 m 로 두고 연직 사진으로 봄.
# (x0, y0): 카메라 바로 아래의 게임 좌표, k: 사진 위쪽이 북에서 시계 방향으로 돈 각(rad), f: 초점 거리(화소)
CAM = {
    (26, 15): dict(x0=-273.84, y0=234.14, k=0.03691, f=1414.71, hc=815.0),
}
_H = None


def ground(x, y):
    """그 점의 땅 높이(data/terrain_near.npy, 5 m 격자)"""
    global _H
    import numpy as np
    if _H is None:
        _H = np.load(os.path.join(ROOT, 'data/terrain_near.npy'))
    fx, fy = (x + 800) / 5.0, (y + 800) / 5.0
    i, j = max(0, min(_H.shape[1] - 2, int(fx))), max(0, min(_H.shape[0] - 2, int(fy)))
    u, v = fx - i, fy - j
    return float(_H[j, i] * (1 - u) * (1 - v) + _H[j, i + 1] * u * (1 - v) + _H[j + 1, i] * (1 - u) * v + _H[j + 1, i + 1] * u * v)


def to_px(frame, x, y, z=None):
    """게임 좌표 -> 화소. 카메라를 맞춘 사진은 높이 z(없으면 땅)까지 넣어 투영하고, 아니면 사이트의 범위에 편다."""
    (x0, y0, x1, y1), (w, h) = FRAMES[frame]
    c = CAM.get(frame)
    if c:
        z = ground(x, y) if z is None else z
        dx, dy, dz = x - c['x0'], y - c['y0'], z - c['hc']
        ck, sk = math.cos(c['k']), math.sin(c['k'])
        return w / 2 - c['f'] * (ck * dx + sk * dy) / dz, h / 2 + c['f'] * (-sk * dx + ck * dy) / dz
    e, n = game_to_5179(x, y)
    return (e - x0) / (x1 - x0) * w, (y1 - n) / (y1 - y0) * h


def frames_at(x, y, margin=120):
    out = []
    for fr, (_, (w, h)) in FRAMES.items():
        px, py = to_px(fr, x, y)
        if margin < px < w - margin and margin < py < h - margin:
            out.append((0 if fr in CAM else 1, math.hypot(px - w / 2, py - h / 2), fr, px, py))      # (맞춘 사진, 주점에 가까운 것부터)
    return [o[1:] for o in sorted(out)]


def path(frame):
    return os.path.join(DIR, 'ngii_1997_%s_c%d_n%d.jpg' % (ZONE, *frame))


if __name__ == '__main__':
    cmd = sys.argv[1]
    x, y = float(sys.argv[2]), float(sys.argv[3])
    if cmd == 'where':
        for d, fr, px, py in frames_at(x, y):
            print('코스 %d 사진 %d: 화소 (%.0f, %.0f), 주점에서 %.0f px, %s' % (*fr, px, py, d, path(fr)))
    elif cmd == 'crop':
        from PIL import Image, ImageDraw, ImageEnhance
        half, out = float(sys.argv[4]), sys.argv[5]
        fr = tuple(int(v) for v in sys.argv[6].split('/')) if len(sys.argv) > 6 and sys.argv[6] != '-' else frames_at(x, y)[0][1]
        zoom = float(sys.argv[7]) if len(sys.argv) > 7 else 3.0
        im = Image.open(path(fr)).convert('RGB')
        cpx = to_px(fr, x, y)
        hp = half / (0.54 if fr in CAM else 0.513)
        box = tuple(int(round(v)) for v in (cpx[0] - hp, cpx[1] - hp, cpx[0] + hp, cpx[1] + hp))
        c = ImageEnhance.Contrast(im.crop(box)).enhance(1.2)
        c = c.resize((int(c.width * zoom), int(c.height * zoom)), Image.LANCZOS)
        d = ImageDraw.Draw(c)
        P = lambda gx, gy: tuple((v - o) * zoom for v, o in zip(to_px(fr, gx, gy), box[:2]))
        campus = json.load(open(os.path.join(ROOT, 'web/public/data/campus.json')))
        for bd in campus['buildings']:                       # 발치(노랑)와 지붕(주황: 바닥 + 높이)
            f = bd['footprint']
            if any(abs(q[0] - x) < half and abs(q[1] - y) < half for q in f):
                zb = bd.get('base', ground(*f[0]))
                d.line([tuple((v - o) * zoom for v, o in zip(to_px(fr, q[0], q[1], zb), box[:2])) for q in f + [f[0]]], fill=(255, 220, 0), width=1)
                d.line([tuple((v - o) * zoom for v, o in zip(to_px(fr, q[0], q[1], zb + bd.get('height', 0)), box[:2])) for q in f + [f[0]]], fill=(255, 120, 0), width=1)
        g = 10 if half <= 80 else 50
        for gx in range(int((x - half) // g * g), int(x + half) + 1, g):
            for gy in range(int((y - half) // g * g), int(y + half) + 1, g):
                p = P(gx, gy)
                d.line([p[0] - 4, p[1], p[0] + 4, p[1]], fill=(0, 255, 255))
                d.line([p[0], p[1] - 4, p[0], p[1] + 4], fill=(0, 255, 255))
                if gx % (2 * g) == 0 and gy % (2 * g) == 0:
                    d.text((p[0] + 3, p[1] + 2), '%d,%d' % (gx, gy), fill=(0, 255, 255))
        c.save(out)
        print(out, c.size, '사진 %d/%d' % fr)
