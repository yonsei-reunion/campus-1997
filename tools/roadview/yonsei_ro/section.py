"""cross-section of the road in one direction of a pano, in units of the camera height (s = u / z0).
   python section.py <pano> <az_deg> [--f 650] [--v 5 20] [--tag x] [--de 0]
   az: the level-frame azimuth to look along (the road, forward or backward); tilt from level.json (lev2.py).
   The vanishing point is searched so that every line along the road (kerb faces, gutters, paint) stands straight in
   the rectified strip (rows: depth v in nominal metres for a 2.5 m camera, cols: s from -5 to +5); s of a point on
   the road plane is its lateral offset over the camera's height above that plane (z0), so read widths only as ratios
   to a ruler in the same strip (zebra bars: zrv.py, zcount.py) and check that the strip is straight (the same s for
   a line in near and far rows).  Writes $YRO_WORK/td/<pano>_<tag>_{view,strip}.png, _strip.npy, _strip.json."""
import sys, json, os
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import maximum_filter, median_filter
import eq

args = sys.argv[1:]
pano, az0 = int(args[0]), float(args[1])
f = float(args[args.index('--f') + 1]) if '--f' in args else 650.0
vmin, vmax = (float(args[args.index('--v') + 1]), float(args[args.index('--v') + 2])) if '--v' in args else (5.0, 20.0)
tag = args[args.index('--tag') + 1] if '--tag' in args else f'a{az0:.0f}'
H0 = 2.5                                   # nominal camera height (m) only to pick rows
lv = json.load(open(f'{eq.D}/level.json'))[str(pano)]
R = eq.rot(lv['pitch'], lv['roll'])
img = eq.load(pano)
Wv, Hv = 2000, 1300
cx, cy = Wv / 2, Hv * 0.3                 # the horizon high in the frame: we want the road
xs, ys = np.meshgrid(np.arange(Wv) + 0.0, np.arange(Hv) + 0.0)
c, s_ = np.cos(np.radians(az0)), np.sin(np.radians(az0))


def rays(px, py):
    x = (px - cx) / f; y = (py - cy) / f
    d = np.stack([x, np.ones_like(x), -y], -1)
    dw = np.stack([d[..., 0] * c + d[..., 1] * s_, -d[..., 0] * s_ + d[..., 1] * c, d[..., 2]], -1)
    return dw / np.linalg.norm(dw, axis=-1, keepdims=True)


dl = rays(xs, ys)                          # level frame
dp = dl @ R                                # pano frame
a, e = eq.ae_of(dp)
DE = float(args[args.index('--de') + 1]) if '--de' in args else 0.0   # the rig's uniform elevation offset (deg)
e = e - np.radians(DE)
V = eq.sample(img, *eq.cr_of(a, e))
Image.fromarray(np.clip(V, 0, 255).astype(np.uint8)).save(f'{eq.D}/td/{pano}_{tag}_view.png')
Rr, G, B = V[..., 0], V[..., 1], V[..., 2]
yel = (Rr > 120) & (G > 95) & (B < 0.65 * G) & (Rr - B > 55) & (G - B > 40)
y_lo, y_hi = cy + f * H0 / vmax, cy + f * H0 / vmin
yy, xx = np.nonzero(yel)
k = (yy > y_lo) & (yy < y_hi)
yy, xx = yy[k].astype(float), xx[k].astype(float)
xvp, yvp = cx + (float(args[args.index("--x0") + 1]) if "--x0" in args else 0), cy + (float(args[args.index("--y0") + 1]) if "--y0" in args else 0)
# VP by strip sharpness: every line along the road (kerb faces, gutters, paint, joints) must stand straight in the
# rectified strip; maximise the energy of the row-averaged lateral gradient
from scipy.ndimage import map_coordinates as _mc
Gy = V.mean(2)
_S = np.arange(-4.6, 4.6, 0.006); _vs = np.arange(vmin, vmax, 0.5)


def _score(xv, yv):
    rows = yv + f * H0 / _vs
    X = xv + _S[None, :] * (rows[:, None] - yv)
    st = _mc(Gy, [np.repeat(rows[:, None], len(_S), 1), X], order=1, mode='nearest')
    gx = np.diff(st, axis=1)
    return float((np.median(gx, 0) ** 2).sum())


best = (_score(xvp, yvp), xvp, yvp)
for step, rad in ((6.0, 30), (2.0, 6), (0.5, 1.5)):
    x0_, y0_ = best[1], best[2]
    for dx in np.arange(-rad, rad + 1e-6, step):
        for dy in np.arange(-rad, rad + 1e-6, step):
            sc_ = _score(x0_ + dx, y0_ + dy)
            if sc_ > best[0]:
                best = (sc_, x0_ + dx, y0_ + dy)
xvp, yvp = best[1], best[2]
for it in range(0):
    sv = (xx - xvp) / (yy - yvp)
    hist, ed = np.histogram(sv, bins=np.arange(-6, 6.001, 0.01))
    pk = np.nonzero((hist == maximum_filter(hist, 9)) & (hist > max(40, 0.05 * hist.max())))[0]
    cen = ed[pk] + 0.005
    lab = np.full(len(sv), -1)
    for i, c0 in enumerate(cen):
        lab[np.abs(sv - c0) < 0.03] = i
    m = lab >= 0
    # x - xvp = s_i (y - yvp)  ->  x = xvp - s_i yvp + s_i y : linear in (xvp, q_i = s_i, yvp) -> solve nonlinear by
    # alternating: fixed (xvp, yvp) -> s_i;  then fixed s_i -> least squares for xvp, yvp
    si = np.array([np.median(sv[lab == i]) for i in range(len(cen))])
    A = np.c_[np.ones(m.sum()), -si[lab[m]]]
    b = xx[m] - si[lab[m]] * yy[m]
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
    xvp, yvp = sol[0], sol[1]
sv = (xx - xvp) / (yy - yvp)
hist, ed = np.histogram(sv, bins=np.arange(-6, 6.001, 0.01))
pk = np.nonzero((hist == maximum_filter(hist, 9)) & (hist > max(40, 0.05 * hist.max())))[0]
cen = ed[pk] + 0.005
lab = np.full(len(sv), -1)
for i, c0 in enumerate(cen):
    lab[np.abs(sv - c0) < 0.03] = i
lines = []
for i in range(len(cen)):
    q = sv[lab == i]
    q = q[np.abs(q - np.median(q)) < 0.03]
    lines.append(dict(s=round(float(np.median(q)), 4), n=int(len(q)), mad=round(float(np.median(np.abs(q - np.median(q)))), 4)))
print(json.dumps(dict(pano=pano, az=az0, vp=[round(xvp, 1), round(yvp, 1)], vp_el=round(float(np.degrees(np.arctan2(cy - yvp, f))), 3),
                      vp_az=round(float(az0 + np.degrees(np.arctan2(xvp - cx, f))), 3), yellow=lines)))
# rectified strip: cols s in [-5, 5] step 0.004, rows = depth bins (v = H0 / dy * f) from vmin to vmax
S = np.arange(-5, 5.0001, 0.004)
vs = np.arange(vmin, vmax, 0.05)
rows = yvp + f * H0 / vs
X = xvp + S[None, :] * (rows[:, None] - yvp)
strip = np.zeros((len(vs), len(S), 3))
for ch in range(3):
    from scipy.ndimage import map_coordinates
    strip[..., ch] = map_coordinates(V[..., ch], [np.repeat(rows[:, None], len(S), 1), X], order=1, mode='constant', cval=0)
st = Image.fromarray(np.clip(strip[::-1], 0, 255).astype(np.uint8))
dr = ImageDraw.Draw(st)
for sv_ in np.arange(-5, 5.01, 0.5):
    col = (sv_ + 5) / 0.004
    dr.line([(col, 0), (col, 10 if abs(sv_ - round(sv_)) > 0.1 else 25)], fill=(255, 0, 0) if sv_ else (0, 255, 0))
st.save(f'{eq.D}/td/{pano}_{tag}_strip.png')
np.save(f'{eq.D}/td/{pano}_{tag}_strip.npy', strip.astype(np.float32))
json.dump(dict(pano=pano, az=az0, de=DE, vp_el=float(np.degrees(np.arctan2(cy - yvp, f))), f=f, cx=cx, cy=cy, vp=[xvp, yvp], vmin=vmin, vmax=vmax, H0=H0, s0=-5, ds=0.004, dv=0.05,
               lines=lines), open(f'{eq.D}/td/{pano}_{tag}_strip.json', 'w'))
