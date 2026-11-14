"""level a pano from line segments: verticals -> tilt (pitch, roll about the pano axes); facade horizontals
   parallel to the road -> the uniform elevation offset de and their direction psi_b.
   python lev2.py <pano> <psi0_deg> [--de0] [--save]
   segments: LSD on 8 perspective renders (f=500).  prints pitch, roll, de, psi_b and their spread."""
import sys, json, os
import cv2
import numpy as np
from scipy.optimize import least_squares
import eq

args = sys.argv[1:]
pano, psi0 = int(args[0]), float(args[1])
img = eq.load(pano)
f = 500.0; Wv, Hv = 1600, 1200; cx, cy = Wv / 2, Hv / 2
xs, ys = np.meshgrid(np.arange(Wv) + 0.0, np.arange(Hv) + 0.0)
x = (xs - cx) / f; y = (ys - cy) / f
dv = np.stack([x, np.ones_like(x), -y], -1)
lsd = cv2.createLineSegmentDetector(0)
segs = []        # (a1, e1, a2, e2, view az, kind)
for az0 in range(0, 360, 45):
    c, s = np.cos(np.radians(az0)), np.sin(np.radians(az0))
    dw = np.stack([dv[..., 0] * c + dv[..., 1] * s, -dv[..., 0] * s + dv[..., 1] * c, dv[..., 2]], -1)
    a, e = eq.ae_of(dw / np.linalg.norm(dw, axis=-1, keepdims=True))
    v = eq.sample(img, *eq.cr_of(a, e))
    g = cv2.cvtColor(np.clip(v, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    L = lsd.detect(g)[0].reshape(-1, 4)
    ln = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1])
    L = L[(ln > 50)]
    # central part of each view only (the views overlap)
    xm = (L[:, 0] + L[:, 2]) / 2
    L = L[np.abs(xm - cx) < f * np.tan(np.radians(24))]
    for x1, y1, x2, y2 in L:
        def ray(px, py):
            d = np.array([(px - cx) / f, 1.0, -(py - cy) / f])
            d = np.array([d[0] * c + d[1] * s, -d[0] * s + d[1] * c, d[2]])
            return eq.ae_of(d / np.linalg.norm(d))
        a1, e1 = ray(x1, y1); a2, e2 = ray(x2, y2)
        vert = abs(x2 - x1) < 0.12 * abs(y2 - y1)
        horiz = abs(y2 - y1) < 0.6 * abs(x2 - x1)
        if vert and min(e1, e2) > np.radians(-5):
            segs.append((a1, e1, a2, e2, az0, 0))
        elif horiz and min(e1, e2) > np.radians(2):
            segs.append((a1, e1, a2, e2, az0, 1))
S = np.array(segs)
V = S[S[:, 5] == 0]; Hz = S[S[:, 5] == 1]
print('verticals', len(V), 'horizontals', len(Hz))


def normals(T, R, de):
    d1 = eq.dir_of(T[:, 0], T[:, 1] + np.radians(de)) @ R.T
    d2 = eq.dir_of(T[:, 2], T[:, 3] + np.radians(de)) @ R.T
    n = np.cross(d1, d2)
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def resid(q, fit_de=True):
    pitch, roll, de, psib = q
    R = eq.rot(pitch, roll)
    nv = normals(V, R, de)
    rv = nv[:, 2]                                         # vertical line: plane normal is horizontal
    nh = normals(Hz, R, de)
    t = np.array([np.sin(np.radians(psib)), np.cos(np.radians(psib)), 0.0])
    rh = nh @ t
    return np.r_[rv, rh * (1.0 if fit_de else 0.0)]


q0 = [0.0, 0.0, 0.0, psi0]
fit_de = '--de0' not in args
lo = [-6, -6, -6 if fit_de else -1e-6, psi0 - 8]; hi = [6, 6, 6 if fit_de else 1e-6, psi0 + 8]
r = least_squares(resid, q0, bounds=(lo, hi), loss='cauchy', f_scale=0.004)
res = resid(r.x)
nV = len(V)
inV = np.abs(res[:nV]) < 0.006; inH = np.abs(res[nV:]) < 0.006
# refit on inliers with linear loss, estimate errors by bootstrap
Vin, Hin = V[inV], Hz[inH]
V0, H0 = V, Hz
V, Hz = Vin, Hin
r2 = least_squares(resid, r.x, bounds=(lo, hi))
boot = []
rng = np.random.default_rng(1)
for _ in range(60):
    V = Vin[rng.integers(0, len(Vin), len(Vin))]; Hz = Hin[rng.integers(0, len(Hin), len(Hin))]
    boot.append(least_squares(resid, r2.x, bounds=(lo, hi)).x)
boot = np.array(boot)
out = dict(pano=pano, pitch=round(r2.x[0], 3), roll=round(r2.x[1], 3), de=round(r2.x[2], 3), psi_b=round(r2.x[3], 3),
           sd=[round(v, 3) for v in boot.std(0)], nV=int(inV.sum()), nH=int(inH.sum()))
print(json.dumps(out))
if '--save' in args:
    db = {}
    fn = f'{eq.D}/level.json'
    if os.path.exists(fn):
        db = json.load(open(fn))
    db[str(pano)] = out
    json.dump(db, open(fn, 'w'), indent=0)
