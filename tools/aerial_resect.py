"""여섯 장(tools/aerial97_cam.json) 밖의 항공사진 한 장의 카메라를, 여섯 장의 카메라를 고정하고 이음점으로 맞춘다(후방 교회).

신촌 로터리(reference/고증/4.10.4_1997년_7월_항공사진.md)는 원본 스캔 여섯 장 밖이라, 같은 비행의 27/18 · 27/19
(원본 스캔도 받음)과 1998년 2차 26/17 의 미리보기(0.54 m/화소, 국토정보맵에서 로그인 없이 받음: reference/고증/1.5_저장소_밖_자료.md)를
이것으로 맞췄다. 27/19 는 먼저 맞춘 27/18 에도 잇는다. 사진은 저장소에 넣지 않는다(1.1.1 「이용 조건」). 결과 카메라는 tools/aerial_resect.json.

  .venv/bin/python tools/aerial_resect.py io <이름>       지표 여덟 개 -> 화소를 사진 좌표(mm)로 바꾸는 아핀
  PYTHONPATH=<opencv> .venv/bin/python tools/aerial_resect.py ties <이름>   이음점(SIFT, PHOTOS 의 known 과: 여섯 장 · 먼저 맞춘 것)
  .venv/bin/python tools/aerial_resect.py fit <이름>      그 사진의 자리 · 기울기 여섯 값(다른 카메라는 고정)
  .venv/bin/python tools/aerial_resect.py check <이름>    원본 스캔이 미리보기 × 4.25 + 1.625 인지 다섯 곳에서 견줌

다른 도구에서: `import aerial_resect; aerial_resect.register()` 하면 aerial97.FRAMES 에 KEY 의 프레임이 더해져
aerial97.to_px · sample · ortho 를 그대로 쓴다(1997년 것은 원본 스캔에서, 1998년 것은 미리보기에서).
이음점은 tools/aerial_resect_<이름>.ties.json (AERIAL_RESECT_TIES 로 다른 폴더에, git 밖에 두어도 됨)"""
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import aerial97_fit as F  # noqa: E402

OUT = os.path.join(ROOT, 'tools/aerial_resect.json')
# 이름: 영상, 자료 띠가 위(top: 사진 면이 168 화소 아래) / 아래, 처음 카메라 자리, 이음점을 찾을 여섯 장, aerial97 에 더할 키
PHOTOS = {
    '1997_27_18': dict(img='assets_src/aerial_1997/ngii_1997_199705A0301_c27_n18.jpg', top=True, xy=(400.0, -560.0),
                       known=['26/16', '27/17', '27/16', '26/15'], key=(27, 18)),
    '1998_26_17': dict(img='assets_src/aerial_other/ngii_199810A0208_c26_n17.jpg', top=True, xy=(-250.0, -560.0),
                       known=['26/15', '26/16', '27/16', '27/17'], key=(98, 2617)),
    # (the next one south: the rotary near its nadir; tied to 27/18 fitted first, and to the six where they reach)
    '1997_27_19': dict(img='assets_src/aerial_1997/ngii_1997_199705A0301_c27_n19.jpg', top=True, xy=(380.0, -1010.0),
                       known=['1997_27_18', '27/17', '26/16'], key=(27, 19)),
    # (and the one after: the rotary at the north-west corner of its face, 760 m off, seen from the south-south-east;
    # preview only, tied to 27/19 and 27/18: 고증 4.10.5)
    '1997_27_20': dict(img='assets_src/aerial_1997/ngii_1997_199705A0301_c27_n20.jpg', top=True, xy=(292.0, -1555.0),
                       known=['1997_27_19', '1997_27_18'], key=(27, 20)),
}


def _known(f):
    """a frame to tie to: one of the six ('26/16') or a photo fitted here before ('1997_27_18'):
    (camera, pixel -> mm affine, image file, data strip at the top)"""
    if f in PHOTOS:
        c = json.load(open(OUT))[f]
        return np.array(c['cam']), np.array(c['M']), _img(f), PHOTOS[f]['top']
    c = json.load(open(F.CAMJ))['frames'][f]
    return np.array(c['cam']), np.array(c['M']), F.path(f), f.startswith('27')


def _data(name):
    p = os.path.join(os.environ.get('AERIAL_RESECT_TIES', os.path.join(ROOT, 'tools')), 'aerial_resect_%s.ties.json' % name)
    return p, (json.load(open(p)) if os.path.exists(p) else {})


def _img(name):
    """the photo's file (AERIAL_RESECT_IMGDIR: another folder with the same file names)"""
    p = PHOTOS[name]['img']
    d = os.environ.get('AERIAL_RESECT_IMGDIR')
    return os.path.join(d, os.path.basename(p)) if d else os.path.join(ROOT, p)


def cmd_io(name):
    from PIL import Image
    from scipy import ndimage as ndi, signal
    ph = PHOTOS[name]
    im = np.asarray(Image.open(_img(name)).convert('L'), float)

    def ring(r, w=1.3, n=27):
        y, x = np.mgrid[-(n // 2):n // 2 + 1, -(n // 2):n // 2 + 1]
        return np.exp(-((np.hypot(x, y) - r) / w) ** 2)

    def ncc(a, t):
        t = t - t.mean()
        num = signal.fftconvolve(a, t[::-1, ::-1], mode='same')
        m = ndi.uniform_filter(a, t.shape[0])
        m2 = ndi.uniform_filter(a * a, t.shape[0])
        return num / np.sqrt(np.maximum(m2 - m * m, 25.0) * t.size * (t ** 2).sum())
    rows = np.where((im > 40).mean(1) > 0.6)[0]                  # (사진 면의 위아래: 해마다 테두리가 달라 찾음)
    cx, cy, W, PAD = 1321.0, (rows.min() + rows.max()) / 2, 120, 400
    imp = np.pad(im, PAD)
    px = []
    for mx, my in F.FID:
        x0, y0 = int(cx + mx * 11.2) - W, int(cy - my * 11.2) - W
        sub = imp[PAD + y0 - 20:PAD + y0 + 2 * W + 20, PAD + x0 - 20:PAD + x0 + 2 * W + 20]
        c = np.max([ncc(sub, ring(r)) for r in (8.5, 9.0, 9.5)], axis=0)[20:-20, 20:-20]
        j, i = np.unravel_index(c.argmax(), c.shape)
        yy, xx = np.mgrid[-2:3, -2:3]
        A_ = np.c_[np.ones(25), xx.ravel(), yy.ravel(), xx.ravel() ** 2, xx.ravel() * yy.ravel(), yy.ravel() ** 2]
        k = np.linalg.lstsq(A_, c[j - 2:j + 3, i - 2:i + 3].ravel(), rcond=None)[0]
        s = np.linalg.solve([[2 * k[3], k[4]], [k[4], 2 * k[5]]], [-k[1], -k[2]])
        px.append((round(float(x0 + i + s[0]), 2), round(float(y0 + j + s[1]), 2)))
    M, res = F.fid_affine(px)
    print('%s 지표 잔차 rms %.4f mm, 화소 %.5f mm' % (name, np.sqrt((res ** 2).sum(1).mean()), np.hypot(*M[0])))
    p, d = _data(name)
    d['fid'] = px
    json.dump(d, open(p, 'w'))


def cmd_ties(name):
    import itertools
    import cv2
    ph = PHOTOS[name]
    sift = cv2.SIFT_create(nfeatures=40000, contrastThreshold=0.03)
    imgs = {f: (_known(f)[2], _known(f)[3]) for f in ph['known']}
    imgs['new'] = (_img(name), ph['top'])
    kps, dss = {}, {}
    for f, (p, top) in imgs.items():
        im = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(16, 16)).apply(cv2.imread(p, cv2.IMREAD_GRAYSCALE))
        mask = np.zeros(im.shape, np.uint8)
        y0 = 330 if top else 160
        mask[y0:y0 + 2320, 160:2480] = 255
        kp, ds = sift.detectAndCompute(im, mask)
        ds = ds / (np.linalg.norm(ds, axis=1, keepdims=True) + 1e-9)
        dss[f] = np.sqrt(ds / (ds.sum(1, keepdims=True) + 1e-9)).astype(np.float32)
        kps[f] = np.array([k.pt for k in kp], np.float32)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in itertools.combinations(list(imgs), 2):
        good = [(x.queryIdx, x.trainIdx) for x, y in bf.knnMatch(dss[a], dss[b], k=2) if x.distance < 0.85 * y.distance]
        back = {x[0].queryIdx: x[0].trainIdx for x in bf.knnMatch(dss[b], dss[a], k=1) if x}
        good = [(i, j) for i, j in good if back.get(j) == i]
        if len(good) < 30:
            continue
        _, inl = cv2.findFundamentalMat(kps[a][[i for i, _ in good]], kps[b][[j for _, j in good]], cv2.USAC_MAGSAC, 1.5, 0.9999, 20000)
        inl = inl.ravel().astype(bool)
        print(a, b, len(good), int(inl.sum()))
        if inl.sum() >= 25:
            for (i, j), k in zip(good, inl):
                if k:
                    parent[find((a, i))] = find((b, j))
    tracks = {}
    for k in list(parent):
        tracks.setdefault(find(k), []).append(k)
    out = [{f: [round(float(v), 2) for v in kps[f][i]] for f, i in sorted(t)} for t in tracks.values()
           if len({f for f, _ in t}) == len(t) and any(f == 'new' for f, _ in t)]
    print('이음점', len(out))
    p, d = _data(name)
    d['ties'] = out
    json.dump(d, open(p, 'w'))


def cmd_fit(name):
    from scipy.optimize import least_squares
    ph = PHOTOS[name]
    _, d = _data(name)
    Mn = F.fid_affine(d['fid'])[0]
    names = list(ph['known']) + ['new']
    ci, pi, ob, n = [], [], [], 0
    for t in d['ties']:
        if len(t) < 2:
            continue
        for f, p in t.items():
            ci.append(names.index(f))
            pi.append(n)
            ob.append(F.px2mm(Mn if f == 'new' else _known(f)[1], p)[0])
        n += 1
    ci, pi, ob = np.array(ci), np.array(pi), np.array(ob)
    kn = len(names) - 1
    cams0 = np.array([_known(f)[0] for f in ph['known']] + [[*ph['xy'], 970.0, 0.0, 0.0, 0.0]])
    rob = lambda r: r / np.sqrt(1 + r * r / 9.0)

    def mk(ci_, pi_, ob_, n_):
        def resid(x):
            c = cams0.copy()
            c[kn] = x
            P = F.tri_many(c, ci_, pi_, ob_, n_)
            return (F.project_many(c, ci_, P[pi_]) - ob_) / F.PIX / 0.5
        return resid
    res = mk(ci, pi, ob, n)
    best = None
    for ka in (0.0, -0.06, 0.06):
        r = least_squares(lambda x: rob(res(x).ravel()), [*ph['xy'], 970.0, 0.0, 0.0, ka],
                          x_scale=[20, 20, 20, 0.01, 0.01, 0.01], max_nfev=300, diff_step=1e-6)
        best = r if best is None or r.cost < best.cost else best
    for _ in range(2):                                   # (2.5 화소 넘게 어긋난 궤적을 빼고 다시)
        e = np.hypot(*(res(best.x) * 0.5).T)
        bad = np.zeros(n, bool)
        np.logical_or.at(bad, pi, e > 2.5)
        keep = ~bad[pi]
        ci, ob = ci[keep], ob[keep]
        _, pi = np.unique(pi[keep], return_inverse=True)
        n = int(pi.max()) + 1
        res = mk(ci, pi, ob, n)
        best = least_squares(lambda x: rob(res(x).ravel()), best.x, x_scale=[20, 20, 20, 0.01, 0.01, 0.01], max_nfev=300, diff_step=1e-6)
    e = np.hypot(*(res(best.x) * 0.5).T)
    print('%s: 궤적 %d, 새 사진의 재투영 잔차 중앙값 %.2f 화소, 카메라 (%.1f, %.1f, %.1f) m, ω %.3f° φ %.3f° κ %.3f°' % (
        name, n, np.median(e[ci == kn]), *best.x[:3], *np.degrees(best.x[3:])))
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    out[name] = dict(M=[[round(v, 9) for v in row] for row in Mn.tolist()], cam=[round(v, 3) for v in best.x[:3]] + [round(v, 7) for v in best.x[3:]],
                     ties=int(n), reproj_px=round(float(np.median(e[ci == kn])), 2))
    with open(OUT, 'w') as fp:
        json.dump(out, fp, indent=1)
        fp.write('\n')


def register():
    """aerial97.FRAMES 에 맞춘 사진들을 더한다(영상이 있는 것만). 돌려주는 것: {이름: 키}"""
    import aerial97 as A
    if not os.path.exists(OUT):
        return {}
    got = {}
    path0, inside0 = A.path, A.inside
    extra, top = {}, {}
    for name, c in json.load(open(OUT)).items():
        ph = PHOTOS[name]
        img = _img(name)
        if not os.path.exists(img):
            continue
        A.FRAMES[ph['key']] = dict(M=np.array(c['M']), cam=np.array(c['cam']))
        A._R.pop(ph['key'], None)
        # (the 1997 ones' scans read as aerial97 reads the six's: assets_src/aerial_1997/ngii_1997_..._c27_n18.tif,
        # cached as cache/c27_n18.npy; the 1998 one has its preview only)
        if not (name.startswith('1997_') and os.path.exists(A.scan_path(ph['key']))):
            A._SC[ph['key']] = None
        extra[ph['key']], top[ph['key']] = img, ph['top']
        got[name] = ph['key']
    A.path = lambda fr: extra.get(fr) or path0(fr)

    def inside(fr, px, py, margin=20):
        if fr not in top:
            return inside0(fr, px, py, margin)
        y0 = 328 if top[fr] else 160
        return (px > 160 + margin) & (px < 2482 - margin) & (py > y0 + margin) & (py < y0 + 2322 - margin)
    A.inside = inside
    return got


def cmd_check(name):
    """the scan against the preview at five places (scan pixel = preview pixel x 4.25 + 1.625?): the offset of the
    best match of each scan window shrunk 4.25 times, in preview pixels"""
    import aerial97 as A
    from scipy import ndimage as ndi
    register()
    key = PHOTOS[name]['key']
    hi = A.scan(key)
    if hi is None:
        print('no scan for', name)
        return
    pv = A.image(key)
    print('scan', hi.shape, 'preview', pv.shape, 'preview x 4.25', (pv.shape[0] * 4.25, pv.shape[1] * 4.25))
    for cx, cy in ((700, 900), (1900, 900), (1320, 1500), (700, 2200), (1900, 2200)):
        n = 40
        sx, sy = cx * 4.25 + 1.625, cy * 4.25 + 1.625
        win = np.asarray(hi[int(sy - n * 4.25):int(sy + n * 4.25), int(sx - n * 4.25):int(sx + n * 4.25)], np.float32)
        small = ndi.zoom(ndi.uniform_filter(win, 4), 1 / 4.25, order=1)
        best = None
        for dy in np.arange(-3, 3.01, 0.25):
            for dx in np.arange(-3, 3.01, 0.25):
                ys, xs = np.mgrid[0:small.shape[0], 0:small.shape[1]]
                ref = ndi.map_coordinates(pv, [cy - n + ys + dy, cx - n + xs + dx], order=1)
                a, b = small - small.mean(), ref - ref.mean()
                r = float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
                if best is None or r > best[0]:
                    best = (r, dx, dy)
        print('  preview (%d, %d): best match offset (%+.2f, %+.2f) px, correlation %.3f' % (cx, cy, best[1], best[2], best[0]))


if __name__ == '__main__':
    dict(io=cmd_io, ties=cmd_ties, fit=cmd_fit, check=cmd_check)[sys.argv[1]](sys.argv[2])
