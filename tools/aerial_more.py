"""1997년 7월 비행(자료 Q) 밖의 항공사진 원본 스캔 — 다른 해 · 다른 비행 — 의 카메라를 맞추고, tools/aerial97.py 의
명령(정사 조각 · 표면 높이)을 그 사진들로 돌린다.

사진은 저장소에 넣지 않는다(reference/고증/1.5_저장소_밖_자료.md 「이용 조건」). 원본 스캔은 그 파일의 「목록」 표대로
assets_src/aerial_other/ngii_<사업코드>_c<코스>_n<번호>.tif(1997년 7월 비행의 26/13 은 assets_src/aerial_1997/)에 두고,
이 도구가 풀어 둔 것(npy · 미리보기 · SIFT · 이음점)은 그 폴더의 cache/ 에.

비행(FLIGHTS)
  1996     서울특별시청 1996년 2차(199612A0302). 잎 없는 겨울: 코스 26 = 1996-12-23 10:55쯤, 코스 27 = 1996-11-28 11:08쯤
           (자료 띠의 날짜 · 시계와 메타데이터). Zeiss RMK(자료 띠에 「C 152,54」 「Nr 21183」, Zeiss Aerotopo 시계):
           초점 거리 152.54 mm, 지표는 네 변 가운데의 흰 점 넷(±113 mm)
  1997     1997년 7월 비행(자료 Q)의 북쪽 장 26/13. 여섯 장과 같은 카메라(WILD 15/4 UAG-S No 13230, 152.85 mm). aerial97 의
           기본 비행('1997')에 들어가 register() 뒤에는 frames_at · surface_z 가 여섯 장과 함께 씀
  1997.10  1997년 2차(199710A0302, 1997-10-13) 코스 25. WILD 15/4 UAG Nr 13032, 153.40 mm, 지표는 네 귀의 동그라미 속 X(±106 mm)
  1998     1998년 2차(199810A0208, 1998-10-08). 1997년 7월과 같은 카메라(No 13230, 152.85 mm), 지표 여덟(aerial97_fit.FID)
  1999     1999년 1차(199905A0101, 1999-05-31, 잎이 난 늦봄). 코스 26 = 14:25쯤, 코스 27 = 14:30쯤(자료 띠의 시계: 그림자는
           북동쪽으로). 자료 띠에 「WILD 15/4 UAG-S No 13230 152.85」: 1997년 7월 · 1998년과 같은 카메라, 지표 여덟.
           1997년 7월처럼 코스 26 은 자료 띠가 아래(서쪽으로 날며), 27 은 위(동쪽으로). y 700 m 북쪽은 26/15 · 27/15 두 장뿐이고
           26/15 의 동쪽 끝이 x 205 m 쯤이라, 그 동쪽(북문 가는 길 s 0 ~ 360 m)은 27/15 한 장

카메라를 맞추는 순서(비행마다, 결과는 tools/aerial_more.json)
  .venv/bin/python tools/aerial_more.py io <비행>      지표 -> 화소를 사진 좌표(mm)로 바꾸는 아핀, 원본을 미리보기 크기로 줄여 둠
  PYTHONPATH=<opencv> .venv/bin/python tools/aerial_more.py ties <비행>   이음점(SIFT): 그 비행의 사진끼리 + 1997년 7월의 고정된 사진들과
  .venv/bin/python tools/aerial_more.py fit <비행>     번들 조정: 그 비행의 카메라만 풀고(사진마다 여섯 값) 1997년 것은 고정
  .venv/bin/python tools/aerial_more.py list           맞춘 사진들과 잔차

- 1997년 7월의 여섯 장(tools/aerial97_cam.json)과 27/18 · 27/19(tools/aerial_resect.json)의 카메라는 고정하고, 이음점마다
  그 점이 찍힌 모든 사진(고정 + 새 것)의 광선으로 삼각측량해 재투영 오차를 줄인다. 그래서 새 카메라는 1997년 블록과 같은
  좌표 · 높이 기준(해발 + aerial97.block_dz)에 놓이고, aerial97.to_px · ray 가 그대로 해발을 낸다.
- 겨울 사진과 여름 사진 사이의 이음점은 지붕 · 길의 선에만 생기고(나무 · 그림자는 다름) 그 비행 안의 이음점이 훨씬 많다.
  json 의 ties97 이 1997년 사진과 이어진 궤적의 수: 이것이 적은 장은 이웃 장을 거쳐서만 묶인 것이다.
- 화소 좌표는 aerial97 과 같이 「미리보기 단위」(원본 스캔 화소 = 미리보기 × 4.25 + 1.625). 미리보기는 국토정보맵의 JPG 가 아니라
  원본을 그 규칙으로 줄인 것(cache/<사업코드>_c<코스>_n<번호>_pv.png)을 쓴다: 사이트 미리보기와 원본의 맞물림을 따로 확인하지 않아도 됨.
- 이음점은 assets_src/aerial_other/cache/ties_<비행>.json (git 밖. 영상에서 다시 만들 수 있음). 한 번 fit 한 뒤
  `ties <비행> guided` 로 고정된 사진과의 짝을 다시 찾으면(광선 토막을 따라: _match_guided) 계절이 다른 짝에도 이음점이 붙는다

재기(aerial97.py 의 명령을 그 비행의 사진으로)
  .venv/bin/python tools/aerial_more.py <비행> z <x> <y> [창 반쪽 m] [아래 m] [위 m]
  .venv/bin/python tools/aerial_more.py <비행> crop <x> <y> <반쪽 m> <out.png> [frame] [zoom] [z]
  .venv/bin/python tools/aerial_more.py <비행> where|px|xyz ...        (frame 은 26/15 처럼)

다른 도구에서
  import aerial97 as A, aerial_more
  aerial_more.register()                       # A.FRAMES 에 (1996, 2615) 같은 키로 더함(26/13 은 (26, 13)). A.ALIAS[('1996', (26, 15))] 가 그 키
  A.surface_z(x, y, 3.0, -8, 8, flight='1996') # 그 비행의 사진끼리 잰 표면 높이(해발). frames=[...] 로 짝을 고를 수도
  A.frames_at(x, y, z, flight='1996'), A.to_px(key, x, y, z), A.sample(key, px, py), A.ortho(key, ...)
  겨울 사진은 잎이 없어 나무 밑 땅이 보인다: 같은 코스의 이웃 장끼리(같은 날 몇 초 사이, 그림자가 같음) 짝지으면 숲 바닥의 높이가 나온다.
  코스 26 과 27 은 찍은 날이 달라(25일) 그림자가 조금 다르고, 1997년 7월 장과는 숲에서 짝지어지지 않는다(수관과 맨땅).
"""
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
OUT = os.path.join(ROOT, 'tools/aerial_more.json')
SCALE = 4.25
PIX = 0.089295                # 미리보기 한 화소(mm): aerial97_cam.json 의 pix_mm
# 비행: 사업코드, 폴더, 파일 이름 꼴, 초점 거리(mm), 지표의 종류, 사진 면의 반쪽(mm, 지표 안쪽),
# 맞출 사진들(영상이 있는 것만 씀), 이어 볼 고정된 사진들('26/15' = 1997년 7월 여섯 장, '1997_27_18' = aerial_resect)
FLIGHTS = {
    '1996': dict(zone='199612A0302', dir='assets_src/aerial_other', f=152.54, fid='zeiss4', half_mm=109.0,
                 frames=['26/14', '26/15', '26/16', '26/17', '27/15', '27/16', '27/17', '27/18'],
                 known=['26/14', '26/15', '26/16', '27/15', '27/16', '27/17', '1997_27_18', '1997_27_19']),
    # 1997년 7월 비행(자료 Q)의 북쪽 장: 여섯 장과 같은 카메라(WILD 15/4 UAG-S No 13230), 같은 비행으로 셈(flight '1997')
    '1997': dict(zone='199705A0301', dir='assets_src/aerial_1997', stem='ngii_1997_%s_c%s_n%s', cache='c%s_n%s',
                 f=152.85, fid='wild8', half_mm=104.0, frames=['26/13'], known=['26/14', '26/15', '27/15', '27/16']),
    # 1997년 2차(1997-10-13): WILD 15/4 UAG Nr 13032, 초점 거리 153.40 mm, 지표는 네 귀의 동그라미 속 X
    '1997.10': dict(zone='199710A0302', dir='assets_src/aerial_other', f=153.40, fid='wild4x', half_mm=104.0,
                    frames=['25/16', '25/17'], known=['26/14', '26/15', '26/16']),
    # 1998년 2차(1998-10-08): 1997년 7월과 같은 카메라(WILD 15/4 UAG-S No 13230, 152.85 mm), 자료 띠는 위
    '1998': dict(zone='199810A0208', dir='assets_src/aerial_other', f=152.85, fid='wild8', half_mm=104.0,
                 frames=['26/15', '26/16', '26/17', '27/16', '27/17'],
                 known=['26/14', '26/15', '26/16', '27/15', '27/16', '27/17', '1997_27_18', '1997_27_19']),
    # 1999년 1차(1999-05-31): 같은 카메라(No 13230, 152.85 mm). 원본은 여섯 장 모두 11,240 x 11,732 화소로 잘려 옴
    '1999': dict(zone='199905A0101', dir='assets_src/aerial_other', f=152.85, fid='wild8', half_mm=104.0,
                 frames=['26/15', '26/16', '26/17', '27/15', '27/16', '27/17'],
                 known=['26/14', '26/15', '26/16', '27/15', '27/16', '27/17', '1997_27_18', '1997_27_19']),
}
# 지표의 명목 자리(mm, 화소 방향으로 x 오른쪽 · y 위)
#   zeiss4: 네 변 가운데의 흰 점(왼 · 오른 · 위 · 아래)
#   wild8: 네 귀 (±106, ±106) 와 네 변 가운데 (±112, 0) · (0, ±112) 의 동그라미(aerial97_fit.FID 와 같은 차례)
#   wild4x: 네 귀 (±106, ±106) 의 동그라미 속 X (변 가운데에는 작은 세모 홈뿐)
FID = {'zeiss4': [(-113.0, 0.0), (113.0, 0.0), (0.0, 113.0), (0.0, -113.0)],
       'wild8': [(-106, 106), (0, 112), (106, 106), (-112, 0), (112, 0), (-106, -106), (0, -112), (106, -106)],
       'wild4x': [(-106, 106), (106, 106), (-106, -106), (106, -106)]}


# ---------- 파일 ----------
def _stem(flight, fr):
    fl = FLIGHTS[flight]
    return fl.get('stem', 'ngii_%s_c%s_n%s') % (fl['zone'], *fr.split('/'))


def tif(flight, fr):
    return os.path.join(ROOT, FLIGHTS[flight]['dir'], _stem(flight, fr) + '.tif')


def _cache(flight, fr, tail):
    fl = FLIGHTS[flight]
    d = os.path.join(ROOT, fl['dir'], 'cache')
    os.makedirs(d, exist_ok=True)
    c, n = fr.split('/')
    return os.path.join(d, (fl['cache'] % (c, n) if 'cache' in fl else '%s_c%s_n%s' % (fl['zone'], c, n)) + tail)


def frames(flight):
    """그 비행에서 원본 스캔이 있는 사진들"""
    return [fr for fr in FLIGHTS[flight]['frames'] if os.path.exists(tif(flight, fr))]


def key(flight, fr):
    """aerial97.FRAMES 의 키: 1997년 7월 비행은 (코스, 번호), 다른 비행은 (비행의 숫자, 코스 * 100 + 번호), 보기 (1996, 2615)"""
    c, n = (int(v) for v in fr.split('/'))
    return (c, n) if flight == '1997' else (int(flight.replace('.', '')), c * 100 + n)


def scan(flight, fr):
    """원본 스캔(8비트 회색)을 메모리 사상으로. 처음 한 번 cache/ 에 npy 로 풀어 둠"""
    npy = _cache(flight, fr, '.npy')
    if not os.path.exists(npy):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        im = Image.open(tif(flight, fr))
        a = np.asarray(im if im.mode in ('P', 'L') and (im.mode == 'L' or im.getpalette()[:9] == [0, 0, 0, 1, 1, 1, 2, 2, 2]) else im.convert('L'))
        tmp = npy[:-4] + '.%d.tmp.npy' % os.getpid()
        np.save(tmp, np.ascontiguousarray(a, np.uint8))
        os.replace(tmp, npy)
    return np.load(npy, mmap_mode='r')


def preview(flight, fr):
    """원본을 4.25배 줄인 미리보기(화소 i 의 가운데 = 원본 화소 4.25 i + 1.625)의 파일. 없으면 만듦"""
    p = _cache(flight, fr, '_pv.png')
    if not os.path.exists(p):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        a = scan(flight, fr)
        h, w = int(a.shape[0] / SCALE), int(a.shape[1] / SCALE)
        Image.fromarray(np.asarray(a)).resize((w, h), Image.BOX, box=(0, 0, w * SCALE, h * SCALE)).save(p)
    return p


def data():
    return json.load(open(OUT)) if os.path.exists(OUT) else {}


def save(d, flight=None):
    """json 을 쓴다. flight 를 주면 파일을 다시 읽어 그 비행만 바꿔 씀(여러 비행을 함께 맞출 때 서로 덮어쓰지 않게)"""
    if flight is not None:
        cur = data()
        cur[flight] = d[flight]
        d = {k: cur[k] for k in sorted(cur, key=lambda k: list(FLIGHTS).index(k) if k in FLIGHTS else 99)}
    tmp = OUT + '.%d.tmp' % os.getpid()
    with open(tmp, 'w') as fp:
        fp.write('{\n')
        fl = []
        for name, v in d.items():
            head = ['  "%s": %s' % (k, json.dumps(x, ensure_ascii=False)) for k, x in v.items() if k != 'frames']
            frs = ['   "%s": %s' % (fr, json.dumps(c)) for fr, c in v.get('frames', {}).items()]
            fl.append(' "%s": {\n%s,\n  "frames": {\n%s\n  }\n }' % (name, ',\n'.join(head), ',\n'.join(frs)))
        fp.write(',\n'.join(fl) + '\n}\n')
    os.replace(tmp, OUT)


# ---------- io: 지표 ----------
def _dot(a, x0, y0, r=260):
    """(x0, y0) 둘레 ±r 원본 화소 안에서, 어두운 바탕 위의 둥근 흰 점(지름 10 화소쯤)의 무게중심.
    둘레가 온통 어두운 점을 먼저 찾고, 없으면 티끌 하나쯤은 봐 준다"""
    try:
        return _dot1(a, x0, y0, r, 100)
    except SystemExit:
        return _dot1(a, x0, y0, r, 97)


def _dot1(a, x0, y0, r, pct):
    from scipy import ndimage as ndi
    xa, ya = max(int(x0) - r, 0), max(int(y0) - r, 0)
    w = np.asarray(a[ya:int(y0) + r, xa:int(x0) + r], np.float32)
    lab, n = ndi.label(w > 110)
    best = None
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        area = int((lab[sl] == i).sum())
        if not (6 <= hh <= 16 and 6 <= ww <= 16 and abs(hh - ww) <= 3 and area > 0.6 * hh * ww):
            continue
        cy, cx = (sl[0].start + sl[0].stop) // 2, (sl[1].start + sl[1].stop) // 2
        if min(cy, cx) < 30 or cy > w.shape[0] - 30 or cx > w.shape[1] - 30:
            continue
        box = w[cy - 30:cy + 31, cx - 30:cx + 31]
        if box.shape != (61, 61):
            continue
        yy, xx = np.mgrid[-30:31, -30:31]
        ring = box[(np.hypot(xx, yy) > 12) & (np.hypot(xx, yy) < 24)]
        if ring.mean() > 25 or np.percentile(ring, pct) > 80:  # (둘레가 어두워야: 지표의 검은 턱 안. 턱의 V 홈 · 티끌이 곁에 오기도 함)
            continue
        sc = area - abs(area - 95)
        if best is None or sc > best[0]:
            m = np.hypot(xx, yy) <= 9
            g = np.clip(box - ring.mean(), 0, None) * m
            best = (sc, xa + cx + (g * xx).sum() / g.sum(), ya + cy + (g * yy).sum() / g.sum())
    if best is None:
        raise SystemExit('지표를 찾지 못함: (%d, %d) 둘레' % (x0, y0))
    return best[1], best[2]


def _fid_zeiss(a):
    """네 변 가운데의 흰 점(왼 · 오른 · 위 · 아래)의 원본 화소. 자료 띠가 위인지 아래인지는 어두운 줄의 수로"""
    H, W = a.shape
    top = (np.asarray(a[100:560:8, 800:W - 800:8]) < 30).mean() > (np.asarray(a[H - 560:H - 100:8, 800:W - 800:8]) < 30).mean()
    cx, cy, h = 5614.0, 5620.0, 5379.0                       # (1996년 2차 26/15 에서 읽은 가운데와 반거리, 띠가 아래일 때)
    if top:
        cx, cy = W - cx, H - cy
    # (스캔마다 테두리를 자른 폭이 달라 사진 면이 100 화소쯤 옮겨진다: 왼 · 오른 점을 넓게 찾고, 그 가운데로 위 · 아래를)
    lt, rt = _dot(a, cx - h, cy, 700), _dot(a, cx + h, cy, 700)
    cx, cy = (lt[0] + rt[0]) / 2, (lt[1] + rt[1]) / 2
    ux, uy = (rt[0] - lt[0]) / 2, (rt[1] - lt[1]) / 2       # (가운데에서 오른 점으로: 위 · 아래 점은 이것을 90° 돌린 곳)
    return [lt, rt, _dot(a, cx + uy, cy - ux, 300), _dot(a, cx - uy, cy + ux, 300)], top


def _fid_rings(flight, fr, kind):
    """Wild 카메라의 동그라미 지표(미리보기 단위 화소). 미리보기에서 동그라미 틀과 NCC, 봉우리 둘레 2차 곡면으로 부화소
    (aerial97_fit.cmd_io · aerial_resect.cmd_io 와 같음)"""
    from PIL import Image
    from scipy import ndimage as ndi, signal
    im = np.asarray(Image.open(preview(flight, fr)).convert('L'), float)

    def ring(r, w=1.3, n=31):
        y, x = np.mgrid[-(n // 2):n // 2 + 1, -(n // 2):n // 2 + 1]
        return np.exp(-((np.hypot(x, y) - r) / w) ** 2)

    def ncc(a, t):
        t = t - t.mean()
        num = signal.fftconvolve(a, t[::-1, ::-1], mode='same')
        m = ndi.uniform_filter(a, t.shape[0])
        m2 = ndi.uniform_filter(a * a, t.shape[0])
        return num / np.sqrt(np.maximum(m2 - m * m, 25.0) * t.size * (t ** 2).sum())
    rows = np.where((im > 12).mean(1) > 0.5)[0]             # (위아래는 자료 띠가 어디냐에 따라 170 화소쯤 옮겨짐)
    cx, cy, W, PAD = im.shape[1] / 2, (rows.min() + rows.max()) / 2, 110, 400   # (옆은 늘 가운데: 어두운 숲이 가에 오면 밝기로는 못 찾음)
    radii = (8.5, 9.0, 9.5) if kind == 'wild8' else (9.5, 10.0, 10.5, 11.0)
    imp = np.pad(im, PAD)

    def find(x, y, w):
        x0, y0 = int(round(x)) - w, int(round(y)) - w
        sub = imp[PAD + y0 - 20:PAD + y0 + 2 * w + 20, PAD + x0 - 20:PAD + x0 + 2 * w + 20]
        c = np.max([ncc(sub, ring(r)) for r in radii], axis=0)[20:-20, 20:-20]
        c2 = c.copy()
        c2[[0, -1], :] = c2[:, [0, -1]].min() - 1               # (창의 가에 붙은 봉우리는 버림)
        c2[:, [0, -1]] = c2.min() - 1
        j, i = np.unravel_index(c2.argmax(), c2.shape)
        j, i = min(max(j, 2), c.shape[0] - 3), min(max(i, 2), c.shape[1] - 3)
        yy, xx = np.mgrid[-2:3, -2:3]
        A_ = np.c_[np.ones(25), xx.ravel(), yy.ravel(), xx.ravel() ** 2, xx.ravel() * yy.ravel(), yy.ravel() ** 2]
        k = np.linalg.lstsq(A_, c[j - 2:j + 3, i - 2:i + 3].ravel(), rcond=None)[0]
        sp = np.linalg.solve([[2 * k[3], k[4]], [k[4], 2 * k[5]]], [-k[1], -k[2]])
        return [round(float(x0 + i + sp[0]), 3), round(float(y0 + j + sp[1]), 3)]
    nom = FID[kind]
    px = [find(cx + mx / PIX, cy - my / PIX, W) for mx, my in nom]
    # (변 가운데의 동그라미는 반원 홈 · 둘레 무늬에 잘못 붙기도 한다: 가장 어긋난 것을 빼며 아핀을 다시 맞추고,
    #  뺀 것은 나머지로 내다본 자리 ±12 화소에서 다시 찾는다)
    use = list(range(len(nom)))
    while len(use) > 4:
        M, res = fid_affine(kind, [px[i] for i in use], [nom[i] for i in use])
        e = np.hypot(*res.T)
        if e.max() < 0.06:
            break
        use.pop(int(e.argmax()))
    M, _ = fid_affine(kind, [px[i] for i in use], [nom[i] for i in use])
    for i in range(len(nom)):
        if i in use:
            continue
        q = np.linalg.solve(M[:2].T, np.array(nom[i], float) - M[2])
        px[i] = find(q[0], q[1], 12)
    return px, bool(cy > im.shape[0] / 2)


def fid_affine(kind, px, nom=None):
    """미리보기 단위 화소 -> mm 아핀(mm = [px py 1] @ M)과 지표 잔차(mm)"""
    A_ = np.c_[np.array(px, float), np.ones(len(px))]
    nom = np.array(FID[kind] if nom is None else nom, float)
    M = np.linalg.lstsq(A_, nom, rcond=None)[0]
    return M, A_ @ M - nom


def cmd_io(flight):
    fl = FLIGHTS[flight]
    d = data()
    e = d.setdefault(flight, {})
    e.update(zone=fl['zone'], f_mm=fl['f'], fid=fl['fid'], half_mm=fl['half_mm'])
    fs = e.setdefault('frames', {})
    for fr in frames(flight):
        a = scan(flight, fr)
        if fl['fid'] == 'zeiss4':
            sp, top = _fid_zeiss(a)
            px = [[round((x - (SCALE - 1) / 2) / SCALE, 3), round((y - (SCALE - 1) / 2) / SCALE, 3)] for x, y in sp]
        else:
            px, top = _fid_rings(flight, fr, fl['fid'])
        M, res = fid_affine(fl['fid'], px)
        # (네 점에 아핀은 남는 것이 둘뿐이라, 닮음 변환(직각 · 같은 배율)에서 벗어난 양도 함께 본다)
        sx, sy = np.hypot(*M[0]), np.hypot(*M[1])
        skew = math.degrees(math.asin(abs(M[0] @ M[1]) / (sx * sy)))
        c = fs.setdefault(fr, {})
        c.update(fid=px, top=bool(top), M=[[round(float(v), 9) for v in row] for row in M],
                 fid_rms_mm=round(float(np.sqrt((res ** 2).sum(1).mean())), 4), size=[int(a.shape[1]), int(a.shape[0])])
        preview(flight, fr)
        print('%s %s: 원본 %d x %d, 자료 띠 %s, 화소 %.5f · %.5f mm(미리보기 단위), 비틀림 %.3f°, 지표 잔차 rms %.4f mm' % (
            flight, fr, a.shape[1], a.shape[0], '위' if top else '아래', sx, sy, skew, c['fid_rms_mm']))
    save(d, flight)


# ---------- 사진 기하(카메라마다 초점 거리) ----------
def rot(om, ph, ka):
    co, so, cp, sp, ck, sk = math.cos(om), math.sin(om), math.cos(ph), math.sin(ph), math.cos(ka), math.sin(ka)
    Rx = np.array([[1, 0, 0], [0, co, -so], [0, so, co]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[ck, -sk, 0], [sk, ck, 0], [0, 0, 1]])
    return (Rx @ Ry @ Rz).T


def project_many(cams, fs, ci, P):
    out = np.empty((len(P), 2))
    for k in range(len(cams)):
        m = ci == k
        if m.any():
            dd = (P[m] - cams[k][:3]) @ rot(*cams[k][3:]).T
            out[m] = -fs[k] * dd[:, :2] / dd[:, 2:3]
    return out


def tri_many(cams, fs, ci, pi, ob, npt, refine=1):
    """관측(카메라 번호 ci, 점 번호 pi, 사진 좌표 ob mm)에서 모든 점을 삼각측량(aerial97_fit.tri_many 와 같음, 초점 거리만 카메라마다)"""
    dv = np.empty((len(ci), 3))
    for k in range(len(cams)):
        m = ci == k
        if m.any():
            v = np.c_[ob[m], -fs[k] * np.ones(m.sum())] @ rot(*cams[k][3:])
            dv[m] = v / np.linalg.norm(v, axis=1, keepdims=True)
    Pm = np.eye(3)[None] - dv[:, :, None] * dv[:, None, :]
    A_ = np.zeros((npt, 3, 3))
    b = np.zeros((npt, 3))
    np.add.at(A_, pi, Pm)
    np.add.at(b, pi, np.einsum('nij,nj->ni', Pm, cams[ci, :3]))
    P = np.linalg.solve(A_ + 1e-9 * np.eye(3), b[:, :, None])[:, :, 0]
    for _ in range(refine):
        r0 = project_many(cams, fs, ci, P[pi]) - ob
        J = np.empty((len(ci), 2, 3))
        for a in range(3):
            dP = np.zeros(3)
            dP[a] = 0.5
            J[:, :, a] = (project_many(cams, fs, ci, P[pi] + dP) - ob - r0) / 0.5
        JtJ = np.zeros((npt, 3, 3))
        Jtr = np.zeros((npt, 3))
        np.add.at(JtJ, pi, np.einsum('nki,nkj->nij', J, J))
        np.add.at(Jtr, pi, np.einsum('nki,nk->ni', J, r0))
        P = P - np.linalg.solve(JtJ + 1e-9 * np.eye(3), Jtr[:, :, None])[:, :, 0]
    return P


def _known(f):
    """고정된 1997년 7월 사진: (카메라, 화소 -> mm 아핀, 초점 거리, 미리보기 파일, 사진 면의 위 줄(미리보기 화소))"""
    import aerial97 as A
    if f.startswith('1997_'):
        import aerial_resect as R
        c = json.load(open(R.OUT))[f]
        return np.array(c['cam']), np.array(c['M']), A.F_MM, R._img(f), 330 if R.PHOTOS[f]['top'] else 160
    c = json.load(open(os.path.join(ROOT, 'tools/aerial97_cam.json')))['frames'][f]
    k = tuple(int(v) for v in f.split('/'))
    return np.array(c['cam']), np.array(c['M']), A.F_MM, A.path(k), 330 if f.startswith('27') else 160


# ---------- ties: 이음점 ----------
def _ties_path(flight):
    d = os.path.join(ROOT, 'assets_src/aerial_other/cache')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'ties_%s.json' % flight)


def _views(flight):
    """이음점을 찾을 사진들: 이름('n26/15' = 그 비행의 새 사진, '26/15' · '1997_27_18' = 고정된 사진) ->
    (미리보기 파일, 사진 면 가림 함수, 화소 -> mm 아핀, 초점 거리, 카메라(없으면 None))"""
    fl = FLIGHTS[flight]
    fs_ = data().get(flight, {}).get('frames', {})
    out = {}
    for fr in frames(flight):
        M = np.array(fs_[fr]['M'])

        def mask(shape, M=M):
            yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
            mm = np.stack([xx, yy], -1) @ M[:2] + M[2]
            return ((np.abs(mm[..., 0]) < fl['half_mm']) & (np.abs(mm[..., 1]) < fl['half_mm'])).astype(np.uint8) * 255
        cam = np.array(fs_[fr]['cam']) if 'cam' in fs_[fr] else None
        out['n' + fr] = (preview(flight, fr), mask, M, fl['f'], cam)
    for f in fl['known']:
        cam, M, fo, p, y0 = _known(f)

        def mask(shape, y0=y0):
            m = np.zeros(shape, np.uint8)
            m[y0:y0 + 2320, 160:2480] = 255
            return m
        out[f] = (p, mask, M, fo, cam)
    return out


def _feats(path, mask):
    """SIFT(RootSIFT) 점과 기술자. 영상 곁에 npz 로 남겨 다시 쓰지 않음(미리보기 파일이 바뀌면 다시)"""
    import cv2
    d = os.path.join(ROOT, 'assets_src/aerial_other/cache/sift')
    os.makedirs(d, exist_ok=True)
    c = os.path.join(d, os.path.basename(path).rsplit('.', 1)[0] + '_%d.npz' % int(os.path.getmtime(path)))
    if os.path.exists(c):
        z = np.load(c)
        return z['k'], z['d']
    im = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(16, 16)).apply(cv2.imread(path, cv2.IMREAD_GRAYSCALE))
    kp, ds = cv2.SIFT_create(nfeatures=60000, contrastThreshold=0.025).detectAndCompute(im, mask(im.shape))
    ds = np.sqrt(ds / (ds.sum(1, keepdims=True) + 1e-9)).astype(np.float32)          # RootSIFT
    k = np.array([q.pt for q in kp], np.float32)
    np.savez(c, k=k, d=ds)
    return k, ds


def _match_free(ka, da, kb, db, ratio):
    """서로 가장 가까운 짝(비율 시험) -> 기본 행렬 MAGSAC 의 안쪽"""
    import cv2
    fm = cv2.FlannBasedMatcher(dict(algorithm=1, trees=4), dict(checks=96))
    good = [(x.queryIdx, x.trainIdx) for x, y in fm.knnMatch(da, db, k=2) if x.distance < ratio * y.distance]
    back = {x[0].queryIdx: x[0].trainIdx for x in fm.knnMatch(db, da, k=1) if x}
    return [(i, j) for i, j in good if back.get(j) == i]


def _match_guided(va, ka, da, vb, kb, db, lo=-6.0, hi=45.0, tol=2.5):
    """카메라를 대강 아는 두 사진: a 의 점마다 광선 위 높이 (땅 + lo) ~ (땅 + hi) 의 토막을 b 에 투영하고,
    그 토막 ±tol 화소 안의 b 점들 가운데서만 가장 가까운 기술자를 고른다(비율 0.9). 계절이 달라 기술자가 흐린 짝(겨울 · 여름)에도
    지붕 · 길의 점이 많이 붙는다"""
    import aerial97_fit as F
    from scipy.spatial import cKDTree
    _, _, Ma, fa, ca = va
    _, _, Mb, fb, cb = vb
    mm = np.c_[ka, np.ones(len(ka))] @ Ma
    dv = np.c_[mm, -fa * np.ones(len(ka))] @ rot(*ca[3:])
    z = np.full(len(ka), 60.0)
    for _ in range(4):
        q = ca[:3] + dv * ((z - ca[2]) / dv[:, 2])[:, None]
        z = F.dem(q[:, 0], q[:, 1])
    ends = []
    for h in (lo, hi):
        P = ca[:3] + dv * ((z + h - ca[2]) / dv[:, 2])[:, None]
        dd = (P - cb[:3]) @ rot(*cb[3:]).T
        m2 = -fb * dd[:, :2] / dd[:, 2:3]
        ends.append(np.linalg.solve(Mb[:2].T, (m2 - Mb[2]).T).T)
    e0, e1 = ends
    mid, half = (e0 + e1) / 2, np.hypot(*(e1 - e0).T) / 2
    u = (e1 - e0) / np.maximum(half * 2, 1e-6)[:, None]
    tree = cKDTree(kb)
    W, H = 2700, 2900
    ok = (mid[:, 0] > -50) & (mid[:, 0] < W) & (mid[:, 1] > -50) & (mid[:, 1] < H)
    out = {}
    idx = np.where(ok)[0]
    if len(idx) < 300:                                       # (겹치지 않는 짝)
        return []
    lists = tree.query_ball_point(mid[idx], half[idx] + tol)
    for i, cand in zip(idx, lists):
        if len(cand) < 1:
            continue
        cand = np.array(cand)
        r = kb[cand] - mid[i]
        along = r @ u[i]
        perp = np.abs(r[:, 0] * u[i][1] - r[:, 1] * u[i][0])
        cand = cand[(perp <= tol) & (np.abs(along) <= half[i] + tol)]
        if len(cand) == 0:
            continue
        dist = np.linalg.norm(db[cand] - da[i], axis=1)
        o = np.argsort(dist)
        if (len(o) > 1 and dist[o[0]] < 0.9 * dist[o[1]]) or (len(o) == 1 and dist[o[0]] < 0.35):
            j = int(cand[o[0]])
            if j not in out or out[j][1] > dist[o[0]]:
                out[j] = (i, float(dist[o[0]]))
    return [(i, j) for j, (i, _) in out.items()]


def cmd_ties(flight, guided=False):
    """이음점. guided: 그 비행의 카메라를 한 번 맞춘 뒤, 고정된 사진과의 짝은 광선 토막을 따라 다시 찾는다"""
    import itertools
    import cv2
    vs = _views(flight)
    kps, dss = {}, {}
    for name, v in vs.items():
        kps[name], dss[name] = _feats(v[0], v[1])
        print(name, len(kps[name]), flush=True)
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in itertools.combinations(list(vs), 2):
        if not (a.startswith('n') or b.startswith('n')):
            continue                                         # (고정된 사진끼리는 잇지 않음)
        cross = not (a.startswith('n') and b.startswith('n'))
        if cross and not a.startswith('n'):
            a, b = b, a
        how = 'free'
        if guided and vs[a][4] is not None and vs[b][4] is not None:
            good = _match_guided(vs[a], kps[a], dss[a], vs[b], kps[b], dss[b], tol=float(os.environ.get('AERIAL_MORE_TOL', '2.5')))
            how = 'guided'
        else:
            good = _match_free(kps[a], dss[a], kps[b], dss[b], 0.9 if cross else 0.8)
        if len(good) < 30:
            print(a, b, how, len(good), flush=True)
            continue
        _, inl = cv2.findFundamentalMat(kps[a][[i for i, _ in good]], kps[b][[j for _, j in good]], cv2.USAC_MAGSAC, 1.5, 0.9999, 50000)
        inl = inl.ravel().astype(bool) if inl is not None else np.zeros(len(good), bool)
        print(a, b, how, len(good), int(inl.sum()), flush=True)
        if inl.sum() >= 20:
            for (i, j), k in zip(good, inl):
                if k:
                    parent[find((a, i))] = find((b, j))
    tracks = {}
    for k in list(parent):
        tracks.setdefault(find(k), []).append(k)
    out = [{f: [round(float(v), 2) for v in kps[f][i]] for f, i in sorted(t)} for t in tracks.values()
           if len({f for f, _ in t}) == len(t) and any(f.startswith('n') for f, _ in t)]
    print('궤적 %d (고정된 사진과 이어진 것 %d)' % (len(out), sum(any(not f.startswith('n') for f in t) for t in out)))
    json.dump(dict(ties=out), open(_ties_path(flight), 'w'))


def _resect(f, mm, P, c0):
    """땅 위 점 P(세계)와 그 사진 좌표 mm 에서 카메라 여섯 값(처음 값 c0, κ 는 여러 곳에서 시작)"""
    from scipy.optimize import least_squares

    def res(c):
        return (project_many(c[None], np.array([f]), np.zeros(len(P), int), P) - mm).ravel()
    best = None
    for k0 in np.radians(np.arange(0, 360, 45)):
        c = np.array([*c0[:3], 0.0, 0.0, k0])
        r = least_squares(lambda v: res(v) / np.sqrt(1 + (res(v) / 2.0) ** 2), c, x_scale=[50, 50, 50, 0.01, 0.01, 0.1])
        if best is None or r.cost < best.cost:
            best = r
    e = np.hypot(*res(best.x).reshape(-1, 2).T)
    return best.x, e


def cmd_init(flight):
    """처음 카메라: 고정된 사진 하나와의 호모그래피(SIFT, 비율 0.8, 허용 10 화소)로 새 사진의 격자를 그 사진에 옮기고,
    그 사진의 광선이 땅(게임 지형 + 블록 면)과 만나는 점에 후방 교회. 계절이 달라 이음점의 궤적으로는 처음 값이 서지 않을 때.
    격자의 땅 점은 건물 · 나무 높이만큼 어긋나므로(수 m) 이것은 `ties <비행> guided` 의 실마리일 뿐이다"""
    import cv2
    import aerial97_fit as F
    fl = FLIGHTS[flight]
    d = data()
    fs_ = d[flight]['frames']
    vs = _views(flight)
    feats = {n: _feats(v[0], v[1]) for n, v in vs.items()}
    for fr in frames(flight):
        a = 'n' + fr
        ka, da = feats[a]
        best = None
        c, nn = (int(v) for v in fr.split('/'))

        def near(b):                                         # (같은 코스 · 같은 번호의 고정된 사진부터)
            bc, bn = (int(v) for v in b.replace('1997_', '').replace('_', '/').split('/'))
            return (bc != c) * 10 + abs(bn - nn)
        for b in sorted(fl['known'], key=near):
            if best is not None and best[0] >= 40:
                break
            kb, db = feats[b]
            g = _match_free(ka, da, kb, db, 0.8)
            if len(g) < 30:
                continue
            H, inl = cv2.findHomography(ka[[i for i, _ in g]], kb[[j for _, j in g]], cv2.USAC_MAGSAC, 10.0, maxIters=50000, confidence=0.9999)
            n = int(inl.sum()) if inl is not None else 0
            print('  %s -> %s: 짝 %d, 호모그래피 안쪽 %d' % (fr, b, len(g), n), flush=True)
            if H is not None and (best is None or n > best[0]):
                best = (n, b, H)
        if best is None or best[0] < 40:
            # (옆 코스의 사진처럼 겹침이 좁고 보는 쪽이 반대면 전체 호모그래피가 서지 않는다: 겹칠 반쪽끼리만, 비율 0.9,
            #  닮음 변환을 25 화소 허용으로. 1997년 2차 25/16 · 25/17 이 그랬음)
            half = {'right': lambda k: k[:, 0] > 2643 * 0.45, 'left': lambda k: k[:, 0] < 2643 * 0.55,
                    'bottom': lambda k: k[:, 1] > 2811 * 0.45, 'top': lambda k: k[:, 1] < 2811 * 0.55}
            for b in sorted(fl['known'], key=near)[:3]:
                kb, db = feats[b]
                for ha, hb in (('right', 'left'), ('left', 'right'), ('bottom', 'top'), ('top', 'bottom')):
                    ia, ib = np.where(half[ha](ka))[0], np.where(half[hb](kb))[0]
                    g = _match_free(ka[ia], da[ia], kb[ib], db[ib], 0.9)
                    if len(g) < 30:
                        continue
                    S, inl = cv2.estimateAffinePartial2D(ka[ia][[i for i, _ in g]], kb[ib][[j for _, j in g]], method=cv2.RANSAC,
                                                         ransacReprojThreshold=25.0, maxIters=20000)
                    n = int(inl.sum()) if inl is not None else 0
                    print('  %s(%s) -> %s(%s): 짝 %d, 닮음 변환 안쪽 %d' % (fr, ha, b, hb, len(g), n), flush=True)
                    if S is not None and n >= 30 and (best is None or n > best[0]):
                        best = (n, b, np.r_[S, [[0, 0, 1]]])
        if best is None or best[0] < 20:
            print('%s: 처음 값을 놓지 못함' % fr)
            continue
        n, b, H = best
        Ma = vs[a][2]
        _, _, Mb, fb, cb = vs[b]
        uu = np.linspace(-85, 85, 15)
        mm = np.array([(u, v) for u in uu for v in uu])
        px = np.linalg.solve(Ma[:2].T, (mm - Ma[2]).T).T
        q = cv2.perspectiveTransform(px.reshape(-1, 1, 2).astype(np.float64), H).reshape(-1, 2)
        mb = np.c_[q, np.ones(len(q))] @ Mb
        dv = np.c_[mb, -fb * np.ones(len(q))] @ rot(*cb[3:])
        z = np.full(len(q), 60.0)
        for _ in range(6):
            P = cb[:3] + dv * ((z - cb[2]) / dv[:, 2])[:, None]
            z = F.dem(P[:, 0], P[:, 1])
        P = cb[:3] + dv * ((z - cb[2]) / dv[:, 2])[:, None]
        inside = (q[:, 0] > 160) & (q[:, 0] < 2480) & (q[:, 1] > 160) & (q[:, 1] < 2650)
        mm, P = mm[inside], P[inside]
        sc = np.median(np.hypot(*(P[1:, :2] - P[:-1, :2]).T) / np.maximum(np.hypot(*(mm[1:] - mm[:-1]).T), 1e-6))
        c0 = np.array([P[:, 0].mean(), P[:, 1].mean(), np.median(P[:, 2]) + sc * fl['f']])
        cam, e = _resect(fl['f'], mm, P, c0)
        fs_[fr]['cam'] = [round(float(v), 3) for v in cam[:3]] + [round(float(v), 7) for v in cam[3:]]
        fs_[fr]['init'] = dict(known=b, homography_inliers=n, resect_mm=round(float(np.median(e)), 3))
        print('%s: %s 에 호모그래피(안쪽 %d), 격자 %d점 후방 교회 잔차 중앙값 %.2f mm, 카메라 (%.0f, %.0f, %.0f) m, ω %.2f° φ %.2f° κ %.1f°' % (
            fr, b, n, len(P), np.median(e), *cam[:3], *np.degrees(cam[3:])), flush=True)
    save(d, flight)


# ---------- fit: 번들 조정 ----------
def _start(flight, fr, M, f, solved, ties):
    """처음 값: 이미 아는 사진(solved: 이름 -> (cam, M, f))의 광선이 땅과 만나는 점과 새 사진의 사진 좌표 사이의 닮음 변환"""
    import aerial97_fit as F
    src, dst = [], []
    for t in ties:
        if 'n' + fr not in t:
            continue
        for g, p in t.items():
            if g in solved:
                cam, Mg, fg = solved[g]
                mm = np.array([p[0], p[1], 1.0]) @ Mg
                dv = np.array([mm[0], mm[1], -fg]) @ rot(*cam[3:])
                z = 60.0
                for _ in range(6):
                    q = cam[:3] + dv * (z - cam[2]) / dv[2]
                    z = float(F.dem(np.array([q[0]]), np.array([q[1]]))[0])
                src.append(np.array([*t['n' + fr], 1.0]) @ M)
                dst.append(q)
                break
    if len(src) < 8:
        return None, len(src)
    src, dst = np.array(src), np.array(dst)
    best = None
    rng = np.random.default_rng(1)
    for _ in range(400):                                     # (RANSAC: 두 점으로 닮음 변환)
        i, j = rng.choice(len(src), 2, replace=False)
        a = complex(*(src[j] - src[i]))
        b = complex(*(dst[j, :2] - dst[i, :2]))
        if abs(a) < 5:
            continue
        s = b / a
        e = np.abs((src[:, 0] + 1j * src[:, 1] - complex(*src[i])) * s + complex(*dst[i, :2]) - (dst[:, 0] + 1j * dst[:, 1]))
        n = int((e < 15).sum())
        if best is None or n > best[0]:
            best = (n, s, complex(*dst[i, :2]) - complex(*src[i]) * s, e < 15)
    n, s, t0, inl = best
    return np.array([t0.real, t0.imag, abs(s) * f + float(np.median(dst[inl, 2])), 0.0, 0.0, math.atan2(s.imag, s.real)]), n


def cmd_fit(flight):
    from scipy.optimize import least_squares
    fl = FLIGHTS[flight]
    d = data()
    fs_ = d[flight]['frames']
    new = [fr for fr in frames(flight) if 'M' in fs_.get(fr, {})]
    ties = json.load(open(_ties_path(flight)))['ties']
    names = list(fl['known']) + ['n' + fr for fr in new]
    kn = len(fl['known'])
    Ms = [_known(f)[1] for f in fl['known']] + [np.array(fs_[fr]['M']) for fr in new]
    fo = np.array([_known(f)[2] for f in fl['known']] + [fl['f']] * len(new))
    cams0 = np.zeros((len(names), 6))
    for k, f in enumerate(fl['known']):
        cams0[k] = _known(f)[0]
    # 처음 값: 1997년 사진과 이음점이 많은 장부터, 그 뒤는 먼저 놓은 새 장에도 기대어
    solved = {f: (cams0[k], Ms[k], fo[k]) for k, f in enumerate(fl['known'])}
    todo = list(new)
    fitted = all('reproj_px' in fs_[fr] for fr in new) and os.environ.get('AERIAL_MORE_RESTART') != '1'
    for fr in new:                                           # (한 번 맞춘 카메라가 있으면 그것에서)
        if 'cam' in fs_[fr] and os.environ.get('AERIAL_MORE_RESTART') != '1':
            k = names.index('n' + fr)
            cams0[k] = fs_[fr]['cam']
            solved['n' + fr] = (cams0[k], Ms[k], fo[k])
            todo.remove(fr)
    while todo:
        cand = [(_start(flight, fr, Ms[names.index('n' + fr)], fl['f'], solved, ties), fr) for fr in todo]
        (c0, n), fr = max(cand, key=lambda c: c[0][1])
        if c0 is None:
            raise SystemExit('처음 값을 놓지 못한 사진: %s' % ' '.join(todo))
        k = names.index('n' + fr)
        cams0[k] = c0
        solved['n' + fr] = (cams0[k], Ms[k], fo[k])
        todo.remove(fr)
        print('처음 값 %s: (%.0f, %.0f, %.0f) m, κ %.2f°, 맞는 점 %d' % (fr, *c0[:3], math.degrees(c0[5]), n))
    ci, pi, ob, n = [], [], [], 0
    # (궤적이 수만이면 번들 조정이 느리다: 사진 짝마다 많아야 CAP 개만, 고정된 사진과 이어진 궤적 · 사진이 많은 궤적부터)
    cap = int(os.environ.get('AERIAL_MORE_CAP', '600'))
    rng = np.random.default_rng(7)
    ties = [{f: p for f, p in t.items() if f in names} for t in ties]
    ties = [t for t in ties if len(t) >= 2 and any(f.startswith('n') for f in t)]
    bad = np.zeros(len(ties), bool)
    if fitted:
        # (모든 새 사진에 앞서 번들 조정한 카메라가 있으면(처음 값만이 아니라): 모든 궤적을 그 카메라로 삼각측량해 재투영이 3 화소 넘는 관측이 있는 궤적을 먼저 뺀다.
        #  이음점이 많을수록 짝 사이를 잇다가 다른 두 점이 한 궤적으로 묶이는 일이 늘고, 그런 궤적은 대개 길다)
        ci0, pi0, ob0 = [], [], []
        for j, t in enumerate(ties):
            for f, p in t.items():
                k = names.index(f)
                ci0.append(k)
                pi0.append(j)
                ob0.append(np.array([p[0], p[1], 1.0]) @ Ms[k])
        ci0, pi0, ob0 = np.array(ci0), np.array(pi0), np.array(ob0)
        P0 = tri_many(cams0, fo, ci0, pi0, ob0, len(ties))
        e0 = np.hypot(*((project_many(cams0, fo, ci0, P0[pi0]) - ob0) / PIX).T)
        np.logical_or.at(bad, pi0, e0 > 3.0)
        print('앞선 카메라로 재투영 3 화소 넘는 궤적 %d / %d 를 뺌' % (bad.sum(), len(ties)), flush=True)
    order = sorted(np.where(~bad)[0], key=lambda i: (-sum(not f.startswith('n') for f in ties[i]), rng.random()))
    used = {}
    keep = []
    for i in order:
        t = {f: p for f, p in ties[i].items() if f in names}
        if len(t) < 2 or not any(f.startswith('n') for f in t):
            continue
        prs = [(a, b) for a in t for b in t if a < b]
        if all(used.get(q, 0) >= cap for q in prs):
            continue
        for q in prs:
            used[q] = used.get(q, 0) + 1
        keep.append(t)
    print('궤적 %d 가운데 %d 를 씀(사진 짝마다 %d 까지)' % (len(ties), len(keep), cap), flush=True)
    for t in keep:
        for f, p in t.items():
            k = names.index(f)
            ci.append(k)
            pi.append(n)
            ob.append(np.array([p[0], p[1], 1.0]) @ Ms[k])
        n += 1
    ci, pi, ob = np.array(ci), np.array(pi), np.array(ob)
    nn = len(new)
    xs = np.tile([20, 20, 20, 0.01, 0.01, 0.01], nn)
    rob = lambda r: r / np.sqrt(1 + r * r / 9.0)

    def mk(ci_, pi_, ob_, n_):
        def resid(x):
            c = cams0.copy()
            c[kn:] = x.reshape(nn, 6)
            P = tri_many(c, fo, ci_, pi_, ob_, n_)
            return (project_many(c, fo, ci_, P[pi_]) - ob_) / PIX / 0.5
        return resid
    res = mk(ci, pi, ob, n)
    x = cams0[kn:].ravel()
    for it, cut in enumerate((None, 6.0, 2.5, 2.0)):
        if cut is not None:                                  # (크게 어긋난 궤적을 빼고 다시)
            e = np.hypot(*(res(x) * 0.5).T)
            bad = np.zeros(n, bool)
            np.logical_or.at(bad, pi, e > cut)
            keep = ~bad[pi]
            ci, ob = ci[keep], ob[keep]
            _, pi = np.unique(pi[keep], return_inverse=True)
            n = int(pi.max()) + 1
            res = mk(ci, pi, ob, n)
        r = least_squares(lambda v: rob(res(v).ravel()), x, x_scale=xs, max_nfev=200, diff_step=1e-6)
        x = r.x
        e = np.hypot(*(res(x) * 0.5).T)
        print('  %d회: 궤적 %d, 관측 %d, 잔차 중앙값 %.2f 화소' % (it + 1, n, len(ci), np.median(e)), flush=True)
    e = np.hypot(*(res(x) * 0.5).T)
    has97 = np.zeros(n, bool)
    np.logical_or.at(has97, pi, ci < kn)
    cams = x.reshape(nn, 6)
    for j, fr in enumerate(new):
        m = ci == kn + j
        t97 = int(has97[pi[m]].sum())
        fs_[fr].update(cam=[round(float(v), 3) for v in cams[j, :3]] + [round(float(v), 7) for v in cams[j, 3:]],
                       ties=int(m.sum()), ties97=t97, reproj_px=round(float(np.median(e[m])), 2),
                       reproj97_px=round(float(np.median(e[m & has97[pi]])), 2) if t97 else None)
        print('%s %s: 궤적 %d (1997년 사진과 %d), 재투영 잔차 중앙값 %.2f 화소 (1997년과 이어진 것 %s), 카메라 (%.1f, %.1f, %.1f) m, ω %.3f° φ %.3f° κ %.3f°' % (
            flight, fr, m.sum(), t97, np.median(e[m]), fs_[fr]['reproj97_px'], *cams[j, :3], *np.degrees(cams[j, 3:])))
    save(d, flight)


def cmd_list():
    for flight, v in data().items():
        for fr, c in v['frames'].items():
            if 'reproj_px' in c:
                print('%s %s: 카메라 (%.1f, %.1f, %.1f) m, 궤적 %d (1997년 사진과 %d), 재투영 잔차 %.2f 화소, 지표 잔차 %.4f mm%s' % (
                    flight, fr, *c['cam'][:3], c['ties'], c['ties97'], c['reproj_px'], c['fid_rms_mm'],
                    '' if os.path.exists(tif(flight, fr)) else ' (영상 없음)'))


# ---------- aerial97 에 더하기 ----------
def register(flights=None):
    """aerial97.FRAMES 에 맞춘 사진들을 더한다(원본 스캔이 있는 것만). 돌려주는 것: {(비행, '26/15'): 키}"""
    import aerial97 as A
    got = {}
    for flight, v in data().items():
        if (flights and flight not in flights) or flight not in FLIGHTS:
            continue
        for fr, c in v['frames'].items():
            if 'cam' not in c or not os.path.exists(tif(flight, fr)):
                continue
            k = key(flight, fr)
            scan(flight, fr)
            A.FRAMES[k] = dict(M=np.array(c['M']), cam=np.array(c['cam']), f=v['f_mm'], half_mm=v['half_mm'], flight=flight,
                               label='%s %s' % (flight, fr), tif=tif(flight, fr), npy=_cache(flight, fr, '.npy'), jpg=preview(flight, fr))
            A._R.pop(k, None)
            A._SC.pop(k, None)
            A._IM.pop(k, None)
            A.ALIAS[(flight, tuple(int(x) for x in fr.split('/')))] = k
            got[(flight, fr)] = k
    return got


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'list':
        cmd_list()
    elif a[0] in ('io', 'init', 'ties', 'fit'):
        dict(io=cmd_io, init=cmd_init, ties=cmd_ties, fit=cmd_fit)[a[0]](a[1], *(['guided'] if a[2:3] == ['guided'] else []))
    else:
        import aerial97 as A
        register([a[0]])
        A.FLIGHT = a[0]
        A.main(a[1:])
