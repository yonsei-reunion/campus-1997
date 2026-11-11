# 1990 · 1994 · 1995 campus maps (reference/*_캠퍼스_지도.*) fitted to the game frame by least squares on the halls'
# south corners (reference/고증/2.3 「1997년 길과 지도」, issue #151).  The maps are drawings seen from the south sky:
# the halls stretched and squeezed by hand, so they give the walks' layout (which halls and lawns a walk joins), not
# their places (leave-one-out 8 - 15 m).
#   .venv/bin/python tools/photofit/mapfit.py fit tools/photofit/map94.json
#   .venv/bin/python tools/photofit/mapfit.py warp tools/photofit/map90.json -200,-180,-40,-20 4 /tmp/w.png
# map95.json carries the 1990 points over through the number labels both prints share (the same drawing).
import json, os, sys
import numpy as np
from scipy import ndimage
from scipy.interpolate import RBFInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
SMOOTH = 1000.0          # (the thin plate's smoothing: it bends the homography towards the corners, not through them)


def homog_fit(P, Q):
    """Q ~ H(P): normalised DLT, then Gauss-Newton on the residuals in Q"""
    def norm(X):
        m = X.mean(0)
        s = np.sqrt(2) / np.mean(np.linalg.norm(X - m, axis=1))
        return np.array([[s, 0, -s * m[0]], [0, s, -s * m[1]], [0, 0, 1]])
    Tp, Tq = norm(P), norm(Q)
    Ph = (Tp @ np.c_[P, np.ones(len(P))].T).T
    Qh = (Tq @ np.c_[Q, np.ones(len(Q))].T).T
    A = []
    for (x, y, _), (u, v, _) in zip(Ph, Qh):
        A.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        A.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    H = np.linalg.inv(Tq) @ np.linalg.svd(np.array(A))[2][-1].reshape(3, 3) @ Tp
    h = (H / H[2, 2]).ravel()[:8]
    for _ in range(20):
        r = homog_apply(np.append(h, 1).reshape(3, 3), P) - Q
        J = np.zeros((2 * len(P), 8))
        for k in range(8):
            e = 1e-7 * max(1, abs(h[k]))
            h2 = h.copy()
            h2[k] += e
            J[:, k] = ((homog_apply(np.append(h2, 1).reshape(3, 3), P) - Q) - r).ravel() / e
        dh = np.linalg.lstsq(J, -r.ravel(), rcond=None)[0]
        h += dh
        if np.abs(dh).max() < 1e-12:
            break
    return np.append(h, 1).reshape(3, 3)


def homog_apply(H, P):
    Ph = np.c_[P, np.ones(len(P))] @ H.T
    return Ph[:, :2] / Ph[:, 2:3]


class Warp:
    """src -> dst: a homography and a smoothed thin plate on what it leaves"""
    def __init__(self, src, dst, smooth=SMOOTH):
        self.H = homog_fit(src, dst)
        self.rbf = RBFInterpolator(src, dst - homog_apply(self.H, src), kernel='thin_plate_spline', smoothing=smooth)

    def __call__(self, P):
        P = np.atleast_2d(P)
        return homog_apply(self.H, P) + self.rbf(P)


def load(path):
    d = json.load(open(path))
    if 'via' in d:                      # (the same drawing in another print: its labels to the other's pixels)
        base = load(os.path.join(os.path.dirname(path), d['via']))
        A = np.array([v[0] for v in d['labels'].values()], float)
        B = np.array([v[1] for v in d['labels'].values()], float)
        H = homog_fit(A, B)
        r = homog_apply(H, A) - B
        print('%s -> %s by %d labels: rms %.1f px, max %.1f px' % (os.path.basename(path), d['via'], len(A),
                                                                   np.sqrt(np.mean(np.sum(r ** 2, 1))), np.hypot(*r.T).max()))
        M = homog_apply(np.linalg.inv(H), base[2])
        return d['map'], base[1], M, base[3]
    names = [p[0] for p in d['pts']]
    return d['map'], names, np.array([p[1] for p in d['pts']], float), np.array([p[2] for p in d['pts']], float)


def fit(path):
    _, names, M, G = load(path)
    n = len(M)
    A = np.linalg.lstsq(np.c_[M, np.ones(n)], G, rcond=None)[0]
    ra = np.c_[M, np.ones(n)] @ A - G
    rh = homog_apply(homog_fit(M, G), M) - G
    lh, lt = np.zeros_like(G), np.zeros_like(G)
    for i in range(n):
        k = np.arange(n) != i
        lh[i] = homog_apply(homog_fit(M[k], G[k]), M[i:i + 1])[0] - G[i]
        lt[i] = Warp(M[k], G[k])(M[i:i + 1])[0] - G[i]
    print('%-24s %6s %6s %6s %6s   (map -> game, m)' % ('', 'affine', 'homog', 'LOO h', 'LOO h+t'))
    for i in range(n):
        print('%-24s %6.1f %6.1f %6.1f %6.1f' % (names[i], np.hypot(*ra[i]), np.hypot(*rh[i]), np.hypot(*lh[i]), np.hypot(*lt[i])))
    rms = lambda r: np.sqrt(np.mean(np.sum(r ** 2, 1)))
    d = np.hypot(*lt.T)
    print('rms: affine %.1f, homography %.1f, leave-one-out %.1f, leave-one-out + thin plate %.1f (median %.1f, 90 %% %.1f), %d points'
          % (rms(ra), rms(rh), rms(lh), rms(lt), np.median(d), np.percentile(d, 90), n))


def warp(path, box, sc, outp):
    from PIL import Image, ImageDraw
    mp, _, M, G = load(path)
    x0, y0, x1, y1 = [float(v) for v in box.split(',')]
    sc = float(sc)
    W = Warp(G, M)                                      # game -> map
    img = np.array(Image.open(os.path.join(ROOT, mp)).convert('RGB')).astype(np.float32)
    w, h = int((x1 - x0) * sc), int((y1 - y0) * sc)
    XX, YY = np.meshgrid(x0 + (np.arange(w) + 0.5) / sc, y1 - (np.arange(h) + 0.5) / sc)
    cx, cy = XX[::6, ::6], YY[::6, ::6]
    uv = W(np.c_[cx.ravel(), cy.ravel()]).reshape(cx.shape + (2,))
    U = ndimage.zoom(uv[..., 0], (h / cx.shape[0], w / cx.shape[1]), order=1)[:h, :w]
    V = ndimage.zoom(uv[..., 1], (h / cy.shape[0], w / cy.shape[1]), order=1)[:h, :w]
    out = np.stack([ndimage.map_coordinates(img[..., c], [V, U], order=1, mode='constant', cval=255) for c in range(3)], -1)
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, 'RGBA')
    T = lambda x, y: ((x - x0) * sc, (y1 - y) * sc)
    C = json.load(open(os.path.join(ROOT, 'web/public/data/campus.json')))
    for b in C['buildings']:
        dr.polygon([T(*q) for q in b['footprint']], outline=(0, 90, 255, 255))
    for p in C['paths']:
        if len(p['pts']) > 1:
            walk = p['kind'] in ('footway', 'path', 'pedestrian', 'steps')
            dr.line([T(*q) for q in p['pts']], fill=(255, 0, 0, 170) if walk else (90, 90, 90, 120), width=2)
    for gx, gy in G:
        X, Y = T(gx, gy)
        dr.ellipse([X - 4, Y - 4, X + 4, Y + 4], outline=(0, 170, 0, 255), width=2)
    im.save(outp)


if __name__ == '__main__':
    if sys.argv[1] == 'fit':
        fit(sys.argv[2])
    elif sys.argv[1] == 'warp':
        warp(*sys.argv[2:6])
