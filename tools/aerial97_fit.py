"""1997년 7월 28일 항공사진 여섯 장(자료 Q)의 카메라를 한꺼번에 맞춘다(번들 조정).

잰 값은 tools/aerial97_fit.json, 결과는 tools/aerial97_cam.json (tools/aerial97.py 가 읽음). 기록은 reference/고증/1_자료.md 「자료 Q」.

  .venv/bin/python tools/aerial97_fit.py io       사진 테두리의 지표 여덟 개 -> 화소를 사진 좌표(mm)로 바꾸는 아핀
  .venv/bin/python tools/aerial97_fit.py ties     사진 사이 이음점(SIFT, opencv 가 있어야 함: pip install --target <폴더> opencv-python-headless 뒤 PYTHONPATH)
  .venv/bin/python tools/aerial97_fit.py roofs    기준 건물(CONTROL)의 지붕 외곽선을 사진의 가장자리에 맞춤
  .venv/bin/python tools/aerial97_fit.py ground   찻길 위의 점(열린 땅)을 겹친 사진에서 찾아 높이 기준점으로
  .venv/bin/python tools/aerial97_fit.py fit      번들 조정 -> aerial97_cam.json
  .venv/bin/python tools/aerial97_fit.py show <out.png> [json 의 건물 키 ...]   맞춘 지붕 외곽선을 사진 위에(눈으로 확인)

방법
- 내부 표정: WILD 15/4 UAG-S (초점 거리 152.85 mm). 지표는 네 귀 (±106, ±106) mm, 네 변 가운데 (±112, 0) · (0, ±112) mm.
  주점은 지표의 중심으로 두고 렌즈 왜곡은 넣지 않는다(미리보기 영상의 한 화소가 0.089 mm 라 그보다 훨씬 작음).
- 외부 표정: 사진마다 여섯(자리 X Y Z, 돎 ω φ κ). 미지수는 카메라 36개뿐이고 점은 그때그때 삼각측량해 지운다.
  - 이음점: 재투영 오차(0.5 화소)
  - 기준 건물: 지붕 꼭짓점의 평면 자리 = 게임 footprint(건물마다 1.5 m), 지붕 높이는 묶지 않음
  - 높이: 찻길 위의 점(열린 땅)의 높이 = data/terrain_near.npy (1.5 m). 이음점은 주로 지붕 · 나무 위라 높이 기준으로
    쓰지 않는다(써 보면 땅이 2 m쯤 낮게 나옴)
- roofs · ground 와 fit 은 서로의 결과를 쓰므로 두세 번 번갈아 돌린다. 처음 값은 aerial97_cam.json.
  roofs 가 붙인 외곽선은 show 로 보고, 잘못 붙은 건물(1997년에 없던 건물, 모양이 다른 건물)은 CONTROL 에서 뺀다.
"""
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'assets_src/aerial_1997')
FIT = os.path.join(ROOT, 'tools/aerial97_fit.json')
CAMJ = os.path.join(ROOT, 'tools/aerial97_cam.json')
FR = ['26/14', '26/15', '26/16', '27/15', '27/16', '27/17']
F_MM = 152.85
PIX = 0.089295                 # 한 화소(mm): 지표 사이 거리에서
# 화소 방향(x 오른쪽, y 위)으로 본 지표의 명목 자리(mm). 코스 27은 영상이 180° 돌아 있지만 지표 무늬가 대칭이라 같게 둔다
FID = [(-106, 106), (0, 112), (106, 106), (-112, 0), (112, 0), (-106, -106), (0, -112), (106, -106)]
# 기준 건물: (이름, 중심 x, 중심 y). 눈으로 지붕 맞춤을 확인한 것만
CONTROL = [
    ('학생회관 별관', 44, -19), ('핀슨관', -67, 161), ('경영학교실단', -39, 110), ('인문관', -91, 262), ('교육관', 31, 330),
    ('상대신관', 118, 477), ('상대별관', 159, 415), ('한경관', -55, 220), ('중앙도서관', -97, -29), ('언더우드관', 66, 266),
    ('연희관', 91, 368), ('가정관', 38, 421), ('종합관', -40, 296), ('알렌관', 386, 47), ('대학사택', 353, 203),
    ('대학사택', 400, 175), ('영선실', 275, 514), ('치과대학병원', 323, -107), ('미우학사', 506, 76), ('국제학사', 522, 227),
    ('한국어학당', 492, 144), ('음악대학', 175, -8), ('간호대학', 350, -30), ('체육관', -203, -96), ('체육교육관', -246, -86),
    ('별동연구동', -256, -145), ('학군단', -510, -183), ('제1공학관', -123, -249), ('제1공학관', -167, -276), ('의과대학', 192, -322),
]


def path(f):
    return os.path.join(DIR, 'ngii_1997_199705A0301_c%s_n%s.jpg' % tuple(f.split('/')))


def load(f):
    from PIL import Image
    return np.asarray(Image.open(path(f)).convert('L'), float)


def data():
    return json.load(open(FIT)) if os.path.exists(FIT) else {}


def save(d):
    with open(FIT, 'w') as fp:
        fp.write('{\n')
        parts = []
        for k, v in d.items():
            if k == 'ties':
                parts.append('"ties": [\n' + ',\n'.join(json.dumps(t, separators=(',', ':')) for t in v) + '\n]')
            elif k == 'ground':
                parts.append('"ground": [\n' + ',\n'.join(json.dumps(t, separators=(',', ':')) for t in v) + '\n]')
            elif k == 'roofs':
                parts.append('"roofs": {\n' + ',\n'.join('%s: %s' % (json.dumps(n, ensure_ascii=False), json.dumps(r, separators=(',', ':'))) for n, r in v.items()) + '\n}')
            else:
                parts.append('%s: %s' % (json.dumps(k), json.dumps(v, separators=(',', ':'))))
        fp.write(',\n'.join(parts) + '\n}\n')


def cams_load():
    c = json.load(open(CAMJ))
    return np.array([c['frames'][f]['cam'] for f in FR]), {f: np.array(c['frames'][f]['M']) for f in FR}


# ---------- 사진 기하 ----------
def px2mm(M, p):
    p = np.atleast_2d(p)
    return np.c_[p, np.ones(len(p))] @ M


def mm2px(M, m):
    return (np.atleast_2d(m) - M[2]) @ np.linalg.inv(M[:2])


def rot(om, ph, ka):
    """세계(x 동, y 북, z 위) -> 카메라(x 오른쪽, y 위, z 뒤)"""
    co, so, cp, sp, ck, sk = math.cos(om), math.sin(om), math.cos(ph), math.sin(ph), math.cos(ka), math.sin(ka)
    Rx = np.array([[1, 0, 0], [0, co, -so], [0, so, co]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[ck, -sk, 0], [sk, ck, 0], [0, 0, 1]])
    return (Rx @ Ry @ Rz).T


def project(cam, P):
    d = (P - cam[:3]) @ rot(*cam[3:]).T
    return -F_MM * d[:, :2] / d[:, 2:3]


def project_many(cams, ci, P):
    out = np.empty((len(P), 2))
    for k in range(len(cams)):
        m = ci == k
        if m.any():
            out[m] = project(cams[k], P[m])
    return out


def tri_many(cams, ci, pi, ob, npt, refine=1):
    """관측(카메라 번호 ci, 점 번호 pi, 사진 좌표 ob)에서 모든 점을 삼각측량: 광선에 가장 가까운 점, 그 뒤 재투영 오차로 가우스-뉴턴"""
    d = np.empty((len(ci), 3))
    for k in range(len(cams)):
        m = ci == k
        if m.any():
            v = np.c_[ob[m], -F_MM * np.ones(m.sum())] @ rot(*cams[k][3:])
            d[m] = v / np.linalg.norm(v, axis=1, keepdims=True)
    Pm = np.eye(3)[None] - d[:, :, None] * d[:, None, :]
    A = np.zeros((npt, 3, 3))
    b = np.zeros((npt, 3))
    np.add.at(A, pi, Pm)
    np.add.at(b, pi, np.einsum('nij,nj->ni', Pm, cams[ci, :3]))
    P = np.linalg.solve(A, b[:, :, None])[:, :, 0]
    for _ in range(refine):
        r0 = project_many(cams, ci, P[pi]) - ob
        J = np.empty((len(ci), 2, 3))
        for a in range(3):
            dP = np.zeros(3)
            dP[a] = 0.5
            J[:, :, a] = (project_many(cams, ci, P[pi] + dP) - ob - r0) / 0.5
        JtJ = np.zeros((npt, 3, 3))
        Jtr = np.zeros((npt, 3))
        np.add.at(JtJ, pi, np.einsum('nki,nkj->nij', J, J))
        np.add.at(Jtr, pi, np.einsum('nki,nk->ni', J, r0))
        P = P - np.linalg.solve(JtJ + 1e-12 * np.eye(3), Jtr[:, :, None])[:, :, 0]
    return P


_DEM = None


def dem(x, y):
    global _DEM
    from scipy.ndimage import map_coordinates
    if _DEM is None:
        _DEM = np.load(os.path.join(ROOT, 'data/terrain_near.npy'))
    return map_coordinates(_DEM, [(np.asarray(y) + 800) / 5.0, (np.asarray(x) + 800) / 5.0], order=1, mode='nearest')


# ---------- io: 지표 ----------
def cmd_io():
    from scipy import ndimage as ndi, signal

    def ring(r, w=1.3, n=27):
        y, x = np.mgrid[-(n // 2):n // 2 + 1, -(n // 2):n // 2 + 1]
        return np.exp(-((np.hypot(x, y) - r) / w) ** 2)

    def ncc(im, t):
        t = t - t.mean()
        num = signal.fftconvolve(im, t[::-1, ::-1], mode='same')
        m = ndi.uniform_filter(im, t.shape[0])
        m2 = ndi.uniform_filter(im * im, t.shape[0])
        return num / np.sqrt(np.maximum(m2 - m * m, 25.0) * t.size * (t ** 2).sum())
    d = data()
    d['fid'] = {}
    for f in FR:
        im = load(f)
        dy = 0 if f.startswith('26') else 168          # 코스 27은 자료 띠가 위에 있어 사진 면이 168 화소 아래
        px = []
        for mx, my in FID:
            x0, y0 = int(1321 + mx * 11.2) - 40, int(1321 + dy - my * 11.2) - 40
            sub = im[y0 - 20:y0 + 100, x0 - 20:x0 + 100]
            c = np.max([ncc(sub, ring(r)) for r in (8.5, 9.0, 9.5)], axis=0)[20:-20, 20:-20]
            j, i = np.unravel_index(c.argmax(), c.shape)
            yy, xx = np.mgrid[-2:3, -2:3]                 # 봉우리 둘레 5 x 5 의 2차 곡면으로 부화소
            A = np.c_[np.ones(25), xx.ravel(), yy.ravel(), xx.ravel() ** 2, xx.ravel() * yy.ravel(), yy.ravel() ** 2]
            k = np.linalg.lstsq(A, c[j - 2:j + 3, i - 2:i + 3].ravel(), rcond=None)[0]
            s = np.linalg.solve([[2 * k[3], k[4]], [k[4], 2 * k[5]]], [-k[1], -k[2]])
            px.append((round(x0 + i + s[0], 2), round(y0 + j + s[1], 2)))
        d['fid'][f] = px
        M, res = fid_affine(px)
        c0 = np.linalg.solve(M[:2].T, -M[2])
        print('%s 주점 (%.2f, %.2f) 화소, 화소 크기 %.5f mm, 지표 잔차 rms %.4f mm' % (f, c0[0], c0[1], np.hypot(*M[0]), np.sqrt((res ** 2).sum(1).mean())))
    save(d)


def fid_affine(px):
    A = np.c_[np.array(px), np.ones(8)]
    M = np.linalg.lstsq(A, np.array(FID, float), rcond=None)[0]          # mm = [px py 1] @ M
    return M, A @ M - np.array(FID, float)


# ---------- ties: 이음점 ----------
def cmd_ties():
    import itertools
    import cv2
    sift = cv2.SIFT_create(nfeatures=40000, contrastThreshold=0.03)
    kps, dss = {}, {}
    for f in FR:
        im = cv2.imread(path(f), cv2.IMREAD_GRAYSCALE)
        mask = np.zeros(im.shape, np.uint8)
        y0 = 160 if f.startswith('26') else 330        # 사진 면 안쪽만(지표 · 테두리 · 자료 띠를 뺌)
        mask[y0:y0 + 2320, 160:2480] = 255
        kp, ds = sift.detectAndCompute(im, mask)
        ds = ds / (np.linalg.norm(ds, axis=1, keepdims=True) + 1e-9)
        dss[f] = np.sqrt(ds / (ds.sum(1, keepdims=True) + 1e-9)).astype(np.float32)        # RootSIFT
        kps[f] = np.array([k.pt for k in kp], np.float32)
        print(f, len(kp), flush=True)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in itertools.combinations(FR, 2):
        good = [(x.queryIdx, x.trainIdx) for x, y in bf.knnMatch(dss[a], dss[b], k=2) if x.distance < 0.8 * y.distance]
        back = {x[0].queryIdx: x[0].trainIdx for x in bf.knnMatch(dss[b], dss[a], k=1) if x}
        good = [(i, j) for i, j in good if back.get(j) == i]
        if len(good) < 30:
            continue
        _, inl = cv2.findFundamentalMat(kps[a][[i for i, _ in good]], kps[b][[j for _, j in good]], cv2.USAC_MAGSAC, 1.5, 0.9999, 20000)
        inl = inl.ravel().astype(bool)
        print(a, b, len(good), int(inl.sum()), flush=True)
        if inl.sum() >= 25:
            for (i, j), k in zip(good, inl):
                if k:
                    parent[find((a, i))] = find((b, j))
    tracks = {}
    for k in list(parent):
        tracks.setdefault(find(k), []).append(k)
    out = []
    for t in tracks.values():
        if len({f for f, _ in t}) == len(t):               # 한 사진에 두 점이 걸린 궤적은 버림
            out.append({f: [round(float(v), 2) for v in kps[f][i]] for f, i in sorted(t)})
    out.sort(key=lambda t: (-len(t), sorted(t.items())))
    # 세 장 넘게 이어진 것은 모두, 두 장짜리는 셋에 하나
    two = [t for t in out if len(t) == 2]
    out = [t for t in out if len(t) > 2] + two[::3]
    print('궤적', len(out))
    d = data()
    d['ties'] = out
    save(d)


# ---------- roofs: 지붕 외곽선 ----------
R, STEP = 10.0, 0.5
DS = np.arange(-R, R + STEP / 2, STEP)
_GR = {}


def grad(f):
    from scipy import ndimage as ndi
    if f not in _GR:
        g = ndi.gaussian_filter(load(f), 1.0)
        _GR[f] = (ndi.sobel(g, axis=1) / 8, ndi.sobel(g, axis=0) / 8)
    return _GR[f]


def inside(f, px, m=40):
    y0 = 160 if f.startswith('26') else 330
    return (px[:, 0] > 160 + m).all() and (px[:, 0] < 2480 - m).all() and (px[:, 1] > y0 + m).all() and (px[:, 1] < y0 + 2320 - m).all()


def score_map(f, poly):
    """외곽선을 (du, dv) 화소 옮겼을 때 변을 따라 변에 수직인 밝기 기울기의 평균"""
    from scipy import ndimage as ndi
    gx, gy = grad(f)
    pts, nrm = [], []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        L = np.hypot(*(b - a))
        if L < 4:
            continue
        t = np.arange(1.5, L - 1.5, 0.7) / L
        pts.append(a + t[:, None] * (b - a))
        nrm.append(np.tile(np.array([-(b - a)[1], (b - a)[0]]) / L, (len(t), 1)))
    pts, nrm = np.concatenate(pts), np.concatenate(nrm)
    DU, DV = np.meshgrid(DS, DS)
    X = pts[None, None, :, 0] + DU[:, :, None]
    Y = pts[None, None, :, 1] + DV[:, :, None]
    g = ndi.map_coordinates(gx, [Y, X], order=1) * nrm[:, 0] + ndi.map_coordinates(gy, [Y, X], order=1) * nrm[:, 1]
    return np.abs(g).mean(-1)


def cmd_roofs():
    from scipy import ndimage as ndi
    cams, Ms = cams_load()
    campus = json.load(open(os.path.join(ROOT, 'web/public/data/campus.json')))
    d = data()
    d['roofs'] = {}
    for name, cx, cy in CONTROL:
        bd = min((b for b in campus['buildings'] if b.get('name') == name), key=lambda b: math.hypot(np.mean([p[0] for p in b['footprint']]) - cx, np.mean([p[1] for p in b['footprint']]) - cy))
        fp = np.array(bd['footprint'], float)
        zr = bd.get('base', 0) + bd.get('height', 0)
        P = np.c_[fp, np.full(len(fp), zr)]
        c0 = P.mean(0)
        fr = {}
        for k, f in enumerate(FR):
            px = mm2px(Ms[f], project(cams[k], P))
            if not inside(f, px):
                continue
            p0 = mm2px(Ms[f], project(cams[k], c0[None]))[0]
            J = np.array([mm2px(Ms[f], project(cams[k], (c0 + e)[None]))[0] - p0 for e in np.eye(3)]).T      # 화소 / m
            sc = score_map(f, px)
            fr[f] = (px, J, sc / sc.max())
        # 건물마다 (dx, dy, 지붕 높이)를 모든 사진에서 함께 찾는다
        dxs = np.arange(-4, 4.01, 0.25)
        dzs = np.arange(-16, 16.01, 0.5)
        DX, DY, DZ = np.meshgrid(dxs, dxs, dzs, indexing='ij')
        tot = np.zeros(DX.shape)
        for px, J, sc in fr.values():
            du = J[0, 0] * DX + J[0, 1] * DY + J[0, 2] * DZ
            dv = J[1, 0] * DX + J[1, 1] * DY + J[1, 2] * DZ
            tot += ndi.map_coordinates(sc, [(dv + R) / STEP, (du + R) / STEP], order=1, mode='constant', cval=0)
        i, j, l = np.unravel_index(tot.argmax(), tot.shape)
        best = np.array([dxs[i], dxs[j], dzs[l]])
        # 사진마다 그 둘레(±1.5 화소)에서 봉우리를 다시 찾아 그 사진의 관측으로
        obs = {}
        for f, (px, J, sc) in fr.items():
            p = J @ best
            m = (np.abs(DS[None, :] - p[0]) <= 1.5) & (np.abs(DS[:, None] - p[1]) <= 1.5)
            m[0] = m[-1] = False
            m[:, 0] = m[:, -1] = False
            if not m.any():
                continue
            jj, ii = np.unravel_index(np.where(m, sc, -1).argmax(), sc.shape)

            def sp(a, b, c):
                q = a - 2 * b + c
                return 0.5 * (a - c) / q if q < 0 else 0.0
            du = DS[ii] + sp(sc[jj, ii - 1], sc[jj, ii], sc[jj, ii + 1]) * STEP
            dv = DS[jj] + sp(sc[jj - 1, ii], sc[jj, ii], sc[jj + 1, ii]) * STEP
            obs[f] = (px + [du, dv]).round(2).tolist()
        key = '%s (%d, %d)' % (name, cx, cy)
        d['roofs'][key] = dict(fp=fp.round(2).tolist(), obs=obs)
        print('%-22s 사진 %d  함께 찾은 옮김 (%+.2f, %+.2f) m, 지붕 높이 %+.1f m (게임 %.1f)' % (key, len(obs), best[0], best[1], best[2], zr))
    save(d)


# ---------- ground: 열린 땅의 높이 기준점 ----------
def cmd_ground():
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import aerial97 as A
    campus = json.load(open(os.path.join(ROOT, 'web/public/data/campus.json')))
    pts = []
    for p in campus['paths']:                              # 차가 다니는 길의 중심선을 40 m마다
        if p['kind'] not in ('service', 'residential', 'primary', 'secondary', 'tertiary', 'living_street', 'road') or p.get('w', 0) < 5:
            continue
        q = np.array(p['pts'], float)
        s = np.r_[0, np.cumsum(np.hypot(*np.diff(q, axis=0).T))]
        for sv in np.arange(20, s[-1], 40):
            x, y = np.interp(sv, s, q[:, 0]), np.interp(sv, s, q[:, 1])
            if abs(x) < 780 and abs(y) < 780 and all(math.hypot(x - a, y - b) > 25 for a, b in pts):
                pts.append((x, y))
    out = []
    for x, y in pts:
        pk, frs = A.surface_z(x, y, 3.0, -9.0, 9.0)
        if not pk or pk[0][0] < 0.7 or (len(pk) > 1 and pk[1][0] > pk[0][0] - 0.15):
            continue                                        # 흐리거나 봉우리가 둘인 곳(나무 밑, 길가 건물)은 버림
        z = pk[0][1]
        out.append(dict(p=[round(x, 1), round(y, 1), round(A.ground(x, y), 2)], obs={'%d/%d' % f: [round(v, 2) for v in A.to_px(f, x, y, z)] for f in frs}))
    print('길 위의 점 %d 가운데 %d' % (len(pts), len(out)))
    d = data()
    d['ground'] = out
    save(d)


# ---------- fit: 번들 조정 ----------
def observations(d, Ms):
    ci, pi, ob = [], [], []
    n = 0
    for tr in d['ties']:
        for f, p in tr.items():
            ci.append(FR.index(f))
            pi.append(n)
            ob.append(px2mm(Ms[f], p)[0])
        n += 1
    nt = n
    cxy, cw, cb = [], [], []
    for b, r in enumerate(d['roofs'].values()):
        nv = len(r['fp'])
        for v in range(nv):
            for f, o in r['obs'].items():
                ci.append(FR.index(f))
                pi.append(n)
                ob.append(px2mm(Ms[f], o[v])[0])
            cxy.append(r['fp'][v])
            cw.append(1.0 / (1.5 * math.sqrt(nv)))        # 한 건물의 꼭짓점들은 같은 오차를 나눠 가지므로 건물마다 1.5 m
            cb.append(b)
            n += 1
    nc = n
    gz = []
    for g in d['ground']:
        for f, o in g['obs'].items():
            ci.append(FR.index(f))
            pi.append(n)
            ob.append(px2mm(Ms[f], o)[0])
        gz.append(g['p'][2])
        n += 1
    return np.array(ci), np.array(pi), np.array(ob), nt, nc, n, np.array(cxy), np.array(cw), np.array(cb), np.array(gz)


def cmd_fit():
    from scipy.optimize import least_squares
    d = data()
    Ms = {f: fid_affine(d['fid'][f])[0] for f in FR}
    cams0 = cams_load()[0]
    ci, pi, ob, nt, nc, n, cxy, cw, cb, gz = observations(d, Ms)
    print('이음점 %d, 지붕 꼭짓점 %d (건물 %d), 땅 높이 점 %d, 관측 %d' % (nt, nc - nt, len(d['roofs']), n - nc, len(ci)))

    def rob(r):                       # 코시형: 큰 잔차(잘못 이어진 점, 지붕 · 나무 위의 점)를 누름
        return r / np.sqrt(1 + r * r / 9.0)

    def parts(x):
        c = x.reshape(6, 6)
        P = tri_many(c, ci, pi, ob, n)
        rp = (project_many(c, ci, P[pi]) - ob) / PIX / 0.5
        rz = (P[nc:, 2] - gz) / 1.5
        rc = (P[nt:nc, :2] - cxy) * cw[:, None]
        return c, P, rp, rz, rc

    def fun(x):
        c, P, rp, rz, rc = parts(x)
        return np.r_[rob(rp.ravel()), rob(rz * 1.5) / 1.5 * 2, rob(rc.ravel() * 3) / 3 * 4]
    res = least_squares(fun, cams0.ravel(), x_scale=np.tile([20, 20, 20, 0.01, 0.01, 0.01], 6), method='trf', max_nfev=60, diff_step=1e-6)
    c, P, rp, rz, rc = parts(res.x)
    e = np.hypot(*(rp[:np.searchsorted(pi, nt)] * 0.5).T)
    print('이음점 재투영: 중앙값 %.2f 화소, 90%% %.2f, 3 화소 넘는 것 %d / %d' % (np.median(e), np.percentile(e, 90), (e > 3).sum(), len(e)))
    T = P[:nt]
    ins = (np.abs(T[:, 0]) < 790) & (np.abs(T[:, 1]) < 790)
    dz = T[ins, 2] - dem(T[ins, 0], T[ins, 1])
    print('이음점 높이 - 지형: 중앙값 %+.2f m, 16 ~ 84%% %+.2f ~ %+.2f m (지붕 · 나무 위의 점이 많음)' % (np.median(dz), *np.percentile(dz, [16, 84])))
    gd = P[nc:, 2] - gz
    G = np.c_[P[nc:, :2] / 100, np.ones(n - nc)]
    kk = np.linalg.lstsq(G[np.abs(gd) < 3], gd[np.abs(gd) < 3], rcond=None)[0]
    print('땅 높이 점(사진) - 지형(게임): 중앙값 %+.2f m, 16 ~ 84%% %+.2f ~ %+.2f m, 3 m 넘는 것 %d / %d, 남은 기울기 동서 %+.2f · 남북 %+.2f m/100 m' % (
        np.median(gd), *np.percentile(gd, [16, 84]), (np.abs(gd) > 3).sum(), len(gd), kk[0], kk[1]))
    dd = P[nt:nc, :2] - cxy
    bm = []
    print('기준 건물의 지붕(사진) - footprint(게임):')
    for b, key in enumerate(d['roofs']):
        m = cb == b
        bm.append(dd[m].mean(0))
        print('  %-22s dx %+5.2f dy %+5.2f m, 지붕 높이 %5.1f m, 사진 %d' % (key, *bm[-1], P[nt:nc][m, 2].mean(), len(d['roofs'][key]['obs'])))
    bm = np.array(bm)
    print('건물 평균 차: rms dx %.2f dy %.2f m, 중앙절대 %.2f · %.2f m' % (*np.sqrt((bm ** 2).mean(0)), *np.median(np.abs(bm), 0)))
    out = dict(f_mm=F_MM, pix_mm=PIX, frames={})
    for k, f in enumerate(FR):
        out['frames'][f] = dict(M=[[round(v, 9) for v in row] for row in Ms[f].tolist()], cam=[round(v, 3) for v in c[k, :3]] + [round(v, 7) for v in c[k, 3:]])
        print('%s 카메라 (%.1f, %.1f, %.1f) m, ω %+.3f° φ %+.3f° κ %+.3f°' % (f, *c[k, :3], *np.degrees(c[k, 3:])))
    with open(CAMJ, 'w') as fp:
        json.dump(out, fp, indent=1)
        fp.write('\n')


def cmd_show(out, keys):
    from PIL import Image, ImageDraw, ImageEnhance
    d = data()
    keys = keys or list(d['roofs'])
    T, cols = 260, 6
    M = Image.new('RGB', (cols * T, ((len(keys) + cols - 1) // cols) * T))
    for n, k in enumerate(keys):
        o = d['roofs'][k]['obs']
        f = '26/15' if '26/15' in o else sorted(o)[0]
        poly = np.array(o[f])
        c = (poly.max(0) + poly.min(0)) / 2
        h = max(np.ptp(poly, 0).max() / 2 + 8, 25)
        b0 = np.array([int(c[0] - h), int(c[1] - h)])
        t = ImageEnhance.Contrast(Image.open(path(f)).convert('RGB').crop((*b0, int(c[0] + h), int(c[1] + h)))).enhance(1.3).resize((T, T), Image.BICUBIC)
        dr = ImageDraw.Draw(t)
        pts = [tuple((p - b0 + 0.5) * T / (2 * h)) for p in poly]
        dr.line(pts + [pts[0]], fill=(0, 255, 0), width=1)
        dr.text((4, 4), '%d %s' % (n, f), fill=(255, 255, 0))
        M.paste(t, ((n % cols) * T, (n // cols) * T))
    M.save(out)
    for n, k in enumerate(keys):
        print(n, k)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'show':
        cmd_show(sys.argv[2], sys.argv[3:])
    else:
        dict(io=cmd_io, ties=cmd_ties, roofs=cmd_roofs, ground=cmd_ground, fit=cmd_fit)[cmd]()
