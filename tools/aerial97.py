"""1997년 7월 28일 항공사진(서울특별시청 1997년 1차, 1:5,000) 여섯 장을 게임 좌표로 보고 재는 도구.

사진은 저장소에 넣지 않는다(공공누리 유형 표시가 없음, reference/고증/1_자료.md 「자료 Q」). assets_src/aerial_1997/ (git 밖)에
두며, 없으면 assets_src/aerial_1997/README.md 의 순서로 국토정보플랫폼에서 다시 받는다.

  .venv/bin/python tools/aerial97.py crop <x> <y> <반쪽 m> <out.png> [frame] [zoom] [z]
      게임 좌표 (x, y) 둘레를 북쪽이 위인 정사 조각으로(땅 높이에서 다시 투영). 10 m 격자와 건물 외곽선(발치 노랑, 지붕 주황)
      frame 은 26/15 처럼, 「-」 면 카메라 바로 아래에 가장 가까운 사진. zoom 3 이면 0.18 m/화소
      땅 높이는 게임 지형에 그 둘레에서 사진으로 잰 차이(중앙값)를 더한 것. z 를 주면 그 높이의 수평면(지붕을 잴 때)
  .venv/bin/python tools/aerial97.py where <x> <y> [z]
      그 점이 찍힌 사진과 화소
  .venv/bin/python tools/aerial97.py z <x> <y> [창 반쪽 m] [아래 m] [위 m]
      그 평면 자리의 표면 높이. 겹쳐 찍힌 사진들을 높이마다 수평면에 다시 투영해 서로 가장 잘 겹치는 높이를 찾음
  .venv/bin/python tools/aerial97.py xyz <frame> <px> <py> [창 반쪽 m]
      한 사진의 화소에 찍힌 점을 다른 사진에서 찾아 게임 좌표 (x, y, z)로
  .venv/bin/python tools/aerial97.py px <frame> <px> <py> [z]
      한 사진의 화소 -> 게임 좌표(땅, 또는 높이 z 의 수평면과 만나는 점)

원본 스캔: 화소 값은 원본 스캔(assets_src/aerial_1997/*.tif, 1210 dpi, 미리보기의 4.25배, 약 0.13 m/화소)에서 읽는다.
처음 한 번 TIF 를 assets_src/aerial_1997/cache/c<코스>_n<번호>.npy 로 풀어 두고 메모리 사상으로 연다(한 장 약 134 MB).
화소 좌표(px, py, to_px · frames_at · xyz 의 입출력)는 늘 미리보기 화소 단위이고, 스캔 화소 = 미리보기 화소 × 4.25 + 1.625.
AERIAL97_SRC=preview 로 미리보기 JPG(0.54 m/화소)를 쓸 수 있다(지난 측정을 되풀이할 때). crop 의 zoom 4 = 0.135 m/화소.

카메라는 tools/aerial97_fit.py 가 여섯 장을 한꺼번에 맞춘 값(tools/aerial97_cam.json)이다. 평면은 기준 건물 30동의 지붕과
1.4 · 0.7 m(중앙절대) 안에서 맞고, 높이는 지형(data/terrain_near.npy)에 묶여 있다. 사진은 정사영상이 아니라서 높이 h 인
점은 카메라 바로 아래 점에서 멀어지는 쪽으로 거리 · h / 900 만큼 밀려 찍힌다. crop 은 땅 높이로 그것을 되돌리므로 땅 위의
것(길 · 선 · 차 · 화단)은 제자리에, 지붕은 밀린 채로 보인다. 게임 지형이 실제와 다른 곳(언더우드관 둘레는 4 m 낮음)에서는
게임 지형 높이로 되돌리면 그만큼 어긋나므로, crop 은 둘레 스물다섯 점의 높이를 사진에서 재어 지형과의 차이를 먼저 더한다.

높이의 정밀도: 평평한 운동장에서 점마다 0.3 m(rms). 나무 밑 · 무늬 없는 지붕 · 창이 지붕과 땅에 걸친 곳은 상관이 낮거나
봉우리가 둘이니 상관 0.7 아래는 버리고 둘레 여러 점을 함께 본다.
"""
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'assets_src/aerial_1997')
ZONE = '199705A0301'          # 사업코드: 지자체 공간정보(서울특별시청1997년1차), 촬영일자 1997-07-28
_C = json.load(open(os.path.join(ROOT, 'tools/aerial97_cam.json')))
F_MM = _C['f_mm']             # 초점 거리(사진 테두리의 「152.85」)
GSD = 0.54                    # 땅 위 한 화소(m, 캠퍼스 가운데: 카메라가 땅 위 약 930 m)
# (코스, 사진 번호): M 은 화소 -> 사진 좌표(mm) 아핀(지표 여덟 개), cam 은 카메라 자리(게임 x, y, z)와 돎(ω, φ, κ rad)
FRAMES = {tuple(int(v) for v in k.split('/')): dict(M=np.array(f['M']), cam=np.array(f['cam'])) for k, f in _C['frames'].items()}
SCALE = 4.25                  # 원본 스캔 화소 = 미리보기 화소 × SCALE + (SCALE - 1) / 2
SRC = os.environ.get('AERIAL97_SRC', 'scan')
_H = None
_IM = {}
_SC = {}
_R = {}


def path(frame):
    return os.path.join(DIR, 'ngii_1997_%s_c%d_n%d.jpg' % (ZONE, *frame))


def scan_path(frame):
    return os.path.join(DIR, 'ngii_1997_%s_c%d_n%d.tif' % (ZONE, *frame))


def scan(frame):
    """원본 스캔(8비트 회색, 팔레트 번호 = 밝기)을 메모리 사상으로. 없으면(또는 AERIAL97_SRC=preview) None"""
    if frame not in _SC:
        npy = os.path.join(DIR, 'cache', 'c%d_n%d.npy' % frame)
        if SRC != 'scan' or not (os.path.exists(npy) or os.path.exists(scan_path(frame))):
            _SC[frame] = None
            return None
        if not os.path.exists(npy):
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = None
            im = Image.open(scan_path(frame))
            a = np.asarray(im if im.mode in ('P', 'L') and im.getpalette()[:9] == [0, 0, 0, 1, 1, 1, 2, 2, 2] else im.convert('L'))
            os.makedirs(os.path.dirname(npy), exist_ok=True)
            tmp = npy[:-4] + '.%d.tmp.npy' % os.getpid()
            np.save(tmp, np.ascontiguousarray(a, np.uint8))
            os.replace(tmp, npy)
        _SC[frame] = np.load(npy, mmap_mode='r')
    return _SC[frame]


def image(frame):
    """미리보기 JPG(0.54 m/화소) 전체. 재는 데는 sample 을 쓸 것(원본 스캔에서 읽음)"""
    if frame not in _IM:
        from PIL import Image
        _IM[frame] = np.asarray(Image.open(path(frame)).convert('L'), np.float32)
    return _IM[frame]


def ground(x, y):
    """땅 높이(data/terrain_near.npy, 5 m 격자, 가장자리 밖은 가장자리 값). 배열도 받음"""
    global _H
    from scipy.ndimage import map_coordinates
    if _H is None:
        _H = np.load(os.path.join(ROOT, 'data/terrain_near.npy'))
    xa, ya = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    z = map_coordinates(_H, [(ya.ravel() + 800) / 5.0, (xa.ravel() + 800) / 5.0], order=1, mode='nearest').reshape(xa.shape)
    return float(z) if z.ndim == 0 else z


def rot(frame):
    """세계(x 동, y 북, z 위) -> 카메라(x 오른쪽, y 위, z 뒤)"""
    if frame not in _R:
        om, ph, ka = FRAMES[frame]['cam'][3:]
        co, so, cp, sp, ck, sk = math.cos(om), math.sin(om), math.cos(ph), math.sin(ph), math.cos(ka), math.sin(ka)
        Rx = np.array([[1, 0, 0], [0, co, -so], [0, so, co]])
        Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
        Rz = np.array([[ck, -sk, 0], [sk, ck, 0], [0, 0, 1]])
        _R[frame] = (Rx @ Ry @ Rz).T
    return _R[frame]


def to_px(frame, x, y, z=None):
    """게임 좌표 -> 화소. z 가 없으면 땅 높이. 배열도 받음(그때는 (n, 2))"""
    fr = FRAMES[frame]
    z = ground(x, y) if z is None else z
    P = np.stack(np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float), np.asarray(z, float)), -1)
    d = (P - fr['cam'][:3]) @ rot(frame).T
    mm = -F_MM * d[..., :2] / d[..., 2:3]
    px = (mm - fr['M'][2]) @ np.linalg.inv(fr['M'][:2])
    return (float(px[0]), float(px[1])) if px.ndim == 1 else px


def ray(frame, px, py):
    """화소 -> (카메라 자리, 세계 방향)"""
    fr = FRAMES[frame]
    mm = np.array([px, py, 1.0]) @ fr['M']
    d = np.array([mm[0], mm[1], -F_MM]) @ rot(frame)
    return fr['cam'][:3], d / np.linalg.norm(d)


def to_game(frame, px, py, z=None):
    """화소 -> 게임 좌표. z 를 주면 그 높이의 수평면, 아니면 땅(지형)과 만나는 점"""
    c, d = ray(frame, px, py)
    zz = 60.0 if z is None else z
    for _ in range(1 if z is not None else 12):
        p = c + d * (zz - c[2]) / d[2]
        if z is None:
            zz = ground(p[0], p[1])
    p = c + d * (zz - c[2]) / d[2]
    return float(p[0]), float(p[1]), float(zz)


def inside(frame, px, py, margin=20):
    """사진 면(지표 안쪽) 안인가. 코스 27은 자료 띠가 위에 있어 사진 면이 168 화소 아래"""
    y0 = 160 if frame[0] == 26 else 328
    return (px > 160 + margin) & (px < 2482 - margin) & (py > y0 + margin) & (py < y0 + 2322 - margin)


def frames_at(x, y, z=None, margin=20):
    """그 점이 찍힌 사진들: (카메라 아래 점에서의 거리 m, frame, px, py), 가까운 것부터"""
    out = []
    for fr, f in FRAMES.items():
        px, py = to_px(fr, x, y, z)
        if inside(fr, px, py, margin):
            out.append((math.hypot(x - f['cam'][0], y - f['cam'][1]), fr, px, py))
    return sorted(out)


def sample(frame, px, py):
    """미리보기 화소 좌표 (px, py)의 밝기(0 ~ 255, 선형 보간). 원본 스캔이 있으면 거기서, 없으면 미리보기에서"""
    from scipy.ndimage import map_coordinates
    hi = scan(frame)
    if hi is None:
        return map_coordinates(image(frame), [py, px], order=1, mode='nearest')
    qx, qy = np.broadcast_arrays(np.asarray(px, float) * SCALE + (SCALE - 1) / 2, np.asarray(py, float) * SCALE + (SCALE - 1) / 2)
    ok = np.isfinite(qx) & np.isfinite(qy)
    out = np.full(qx.shape, np.nan, np.float32)
    if not ok.any():
        return out
    h, w = hi.shape
    qx, qy = np.clip(qx[ok], 0, w - 1), np.clip(qy[ok], 0, h - 1)
    x0, y0 = int(qx.min()), int(qy.min())
    x1, y1 = min(int(qx.max()) + 2, w), min(int(qy.max()) + 2, h)
    win = np.asarray(hi[y0:y1, x0:x1], np.float32)
    out[ok] = map_coordinates(win, [qy - y0, qx - x0], order=1, mode='nearest')
    return out


def ortho(frame, x, y, half, res, z=None, dz=0.0):
    """(x, y) 둘레 ±half m 를 res m/화소로 다시 투영한 영상(북쪽이 위). z 가 없으면 게임 지형 + dz"""
    n = int(round(2 * half / res)) + 1
    gx, gy = np.meshgrid(x - half + np.arange(n) * res, y + half - np.arange(n) * res)
    p = to_px(frame, gx, gy, ground(gx, gy) + dz if z is None else z)
    return sample(frame, p[..., 0], p[..., 1])


def ground_offset(x, y, half, n=5):
    """(x, y) 둘레 ±half m 의 n x n 점에서 사진으로 잰 땅 높이 - 게임 지형의 중앙값(m)과 쓴 점의 수. 잴 수 없으면 (0, 0)"""
    d = []
    for gx in np.linspace(x - half * 0.8, x + half * 0.8, n):
        for gy in np.linspace(y - half * 0.8, y + half * 0.8, n):
            pk, _ = surface_z(gx, gy, 3.0, -9.0, 9.0)
            if pk and pk[0][0] >= 0.7 and (len(pk) < 2 or pk[1][0] < pk[0][0] - 0.15):
                d.append(pk[0][1] - ground(gx, gy))
    return (float(np.median(d)), len(d)) if len(d) >= 3 else (0.0, 0)


def _ncc(a, b):
    a = a - a.mean(-1, keepdims=True)
    b = b - b.mean(-1, keepdims=True)
    return (a * b).sum(-1) / np.sqrt((a * a).sum(-1) * (b * b).sum(-1) + 1e-9)


def _peaks(zs, s, n=3):
    """점수 곡선의 봉우리(부화소) 높은 것부터"""
    out = []
    for i in range(1, len(s) - 1):
        if s[i] >= s[i - 1] and s[i] > s[i + 1]:
            q = s[i - 1] - 2 * s[i] + s[i + 1]
            out.append((s[i], zs[i] + (0.5 * (s[i - 1] - s[i + 1]) / q if q < 0 else 0) * (zs[1] - zs[0])))
    return sorted(out, reverse=True)[:n]


def surface_z(x, y, win=4.0, lo=-8.0, hi=45.0, step=0.25, frames=None, grid=None):
    """평면 자리 (x, y)의 표면 높이. 높이 후보마다 그 높이의 수평 창(±win m)을 사진들에 투영해 서로의 상관을 본다.
    돌려주는 것: [(점수, 높이)] 봉우리 높은 것부터, 쓴 사진들. 창에 지붕과 땅이 함께 들면 봉우리가 둘 나온다"""
    g = ground(x, y)
    frs = frames or [f[1] for f in frames_at(x, y, g, margin=40)]
    if len(frs) < 2:
        return [], frs
    gr = grid or 0.5              # 창 안 점 사이(m). 원본 스캔에서 좁은 것(계단 · 연석)을 잴 때는 창을 줄이고 0.25 m 로
    n = int(round(2 * win / gr)) + 1
    gx, gy = np.meshgrid(x - win + np.arange(n) * gr, y + win - np.arange(n) * gr)
    zs = np.arange(g + lo, g + hi + step / 2, step)
    pat = []
    for f in frs:
        p = to_px(f, gx[None], gy[None], zs[:, None, None])           # (nz, n, n, 2)
        pat.append(sample(f, p[..., 0], p[..., 1]).reshape(len(zs), -1))
    s = np.mean([_ncc(pat[i], pat[j]) for i in range(len(frs)) for j in range(i + 1, len(frs))], axis=0)
    return _peaks(zs, s), frs


def match_xyz(frame, px, py, win=4.0, lo=-8.0, hi=45.0, step=0.25):
    """한 사진의 화소에 찍힌 점의 게임 좌표. 그 화소의 광선 위를 높이마다 따라가며 다른 사진들과의 상관이 가장 큰 곳"""
    c, d = ray(frame, px, py)
    g = to_game(frame, px, py)[2]
    zs = np.arange(g + lo, g + hi + step / 2, step)
    P = c + d * ((zs - c[2]) / d[2])[:, None]
    others = [f for f in FRAMES if f != frame and all(inside(f, *to_px(f, q[0], q[1], q[2]), 40) for q in (P[0], P[-1]))]
    if not others:
        return None
    n = int(round(2 * win / 0.5)) + 1
    ox, oy = np.meshgrid(-win + np.arange(n) * 0.5, win - np.arange(n) * 0.5)
    gx, gy, gz = P[:, 0, None, None] + ox[None], P[:, 1, None, None] + oy[None], zs[:, None, None]
    ref = to_px(frame, gx, gy, gz)
    ref = sample(frame, ref[..., 0], ref[..., 1]).reshape(len(zs), -1)
    s = []
    for f in others:
        p = to_px(f, gx, gy, gz)
        s.append(_ncc(ref, sample(f, p[..., 0], p[..., 1]).reshape(len(zs), -1)))
    pk = _peaks(zs, np.mean(s, axis=0))
    return [(sc, *(c + d * (z - c[2]) / d[2])) for sc, z in pk], others


def _frame_arg(a):
    return tuple(int(v) for v in a.split('/'))


if __name__ == '__main__':
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd == 'where':
        x, y = float(a[0]), float(a[1])
        z = float(a[2]) if len(a) > 2 else None
        print('땅 높이 %.1f m' % ground(x, y))
        for d, fr, px, py in frames_at(x, y, z):
            print('코스 %d 사진 %d: 화소 (%.1f, %.1f), 카메라 아래에서 %.0f m, %s' % (*fr, px, py, d, path(fr)))
    elif cmd == 'px':
        fr = _frame_arg(a[0])
        print('게임 좌표 (%.1f, %.1f), 높이 %.1f m' % to_game(fr, float(a[1]), float(a[2]), float(a[3]) if len(a) > 3 else None))
    elif cmd == 'z':
        x, y = float(a[0]), float(a[1])
        pk, frs = surface_z(x, y, *(float(v) for v in a[2:5]))
        print('땅(지형) %.1f m, 사진 %s' % (ground(x, y), ' '.join('%d/%d' % f for f in frs)))
        for sc, z in pk:
            print('  높이 %.1f m (상관 %.2f)' % (z, sc))
    elif cmd == 'xyz':
        fr = _frame_arg(a[0])
        r = match_xyz(fr, float(a[1]), float(a[2]), *(float(v) for v in a[3:4]))
        if r is None:
            print('겹쳐 찍힌 다른 사진이 없음')
        else:
            print('사진 %s' % ' '.join('%d/%d' % f for f in r[1]))
            for sc, x, y, z in r[0]:
                print('  (%.1f, %.1f) 높이 %.1f m (상관 %.2f)' % (x, y, z, sc))
    elif cmd == 'crop':
        from PIL import Image, ImageDraw
        x, y, half, out = float(a[0]), float(a[1]), float(a[2]), a[3]
        fr = _frame_arg(a[4]) if len(a) > 4 and a[4] != '-' else frames_at(x, y)[0][1]
        res = GSD / (float(a[5]) if len(a) > 5 else 3.0)
        zp = float(a[6]) if len(a) > 6 else None
        dz, nz = (0.0, 0) if zp is not None else ground_offset(x, y, half)
        im = ortho(fr, x, y, half, res, zp, dz)
        lo, hi = np.percentile(im, [1, 99.5])
        c = Image.fromarray(np.clip((im - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)).convert('RGB')
        d = ImageDraw.Draw(c)
        cam = FRAMES[fr]['cam']

        def P(gx, gy, gz=None):
            """게임 점이 조각에서 보이는 자리: 사진에 찍힌 화소를 다시 조각의 면(땅, 또는 z)으로 되돌림"""
            if gz is not None:
                c0, dd = ray(fr, *to_px(fr, gx, gy, gz + dz))
                zt = zp if zp is not None else ground(gx, gy) + dz          # 조각의 면(그 건물 발치의 땅)
                gx, gy = (c0 + dd * (zt - c0[2]) / dd[2])[:2]
            return (gx - (x - half)) / res, ((y + half) - gy) / res
        campus = json.load(open(os.path.join(ROOT, 'web/public/data/campus.json')))
        for bd in campus['buildings']:                       # 발치(노랑)와 지붕(주황: 바닥 + 높이)
            f = bd['footprint']
            if any(abs(q[0] - x) < half and abs(q[1] - y) < half for q in f):
                zb = bd.get('base', ground(*f[0]))
                d.line([P(q[0], q[1], zb) for q in f + [f[0]]], fill=(255, 220, 0), width=1)
                d.line([P(q[0], q[1], zb + bd.get('height', 0)) for q in f + [f[0]]], fill=(255, 120, 0), width=1)
        g = 10 if half <= 80 else 50
        for gx in range(int((x - half) // g * g), int(x + half) + 1, g):
            for gy in range(int((y - half) // g * g), int(y + half) + 1, g):
                p = P(gx, gy)
                d.line([p[0] - 4, p[1], p[0] + 4, p[1]], fill=(0, 255, 255))
                d.line([p[0], p[1] - 4, p[0], p[1] + 4], fill=(0, 255, 255))
                if gx % (2 * g) == 0 and gy % (2 * g) == 0:
                    d.text((p[0] + 3, p[1] + 2), '%d,%d' % (gx, gy), fill=(0, 255, 255))
        c.save(out)
        print(out, c.size, '사진 %d/%d, %.2f m/화소, 카메라 아래 (%.0f, %.0f), 땅 높이 = %s' % (
            *fr, res, cam[0], cam[1], '%.1f m 수평면' % zp if zp is not None else '게임 지형 %+.1f m (사진으로 잰 %d점)' % (dz, nz)))
