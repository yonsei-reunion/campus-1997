# Car offset from the yellow edge lines in a level (tilt 0) zoom-0 view along the road (see lanes.py for the model).
#   python lanes2.py <img> fwd|back [--L x0:x1:y0:y1,...] [--R ...] [--one L|R --h 2.43] [--dbg out.png]
# Two lines: d1/d2 = slope ratio, scaled by W = 6.6 m between the lines (camera height comes out).  One line: the
# camera height of the drive (from its two-line views) and the VP on the horizon row (pitch ~0 in this drive).
import math, argparse
import numpy as np
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser()
ap.add_argument('img'); ap.add_argument('dir')
ap.add_argument('--L', default='0:694:520:885'); ap.add_argument('--R', default='694:1388:520:885')
ap.add_argument('--one', default=''); ap.add_argument('--h', type=float, default=0)
ap.add_argument('--yh', type=float, default=450.0)
ap.add_argument('--f', type=float, default=458.0); ap.add_argument('--W', type=float, default=6.6)
ap.add_argument('--dbg', default='')
a = ap.parse_args()
im = np.asarray(Image.open(a.img).convert('RGB')).astype(float)
R, G, B = im[..., 0], im[..., 1], im[..., 2]
yellow = (R > 110) & (G > 85) & (R - B > 60) & (G - B > 40) & (np.abs(R - G) < 75)
cx, cy, f = 694.0, 450.0, a.f

def collect(boxes):
    m = np.zeros_like(yellow)
    for bx in boxes.split(','):
        x0, x1, y0, y1 = map(int, bx.split(':')); m[y0:y1, x0:x1] = yellow[y0:y1, x0:x1]
    P = []
    for yy in range(m.shape[0]):
        row = np.nonzero(m[yy])[0]
        if len(row) == 0: continue
        for r in np.split(row, np.nonzero(np.diff(row) > 2)[0] + 1):
            if len(r) >= 2: P.append((r.mean(), yy))
    return np.array(P, float)

def fit_line(P, it=400, tol=2.0):
    x, y = P[:, 0], P[:, 1]
    rng = np.random.default_rng(0); best = None
    for _ in range(it):
        i, j = rng.choice(len(x), 2, replace=False)
        if abs(y[i] - y[j]) < 20: continue
        q = (x[i] - x[j]) / (y[i] - y[j]); p = x[i] - q * y[i]
        inl = np.abs(x - (p + q * y)) < tol
        if best is None or inl.sum() > best.sum(): best = inl
    A = np.stack([np.ones(best.sum()), y[best]], 1)
    (p, q), *_ = np.linalg.lstsq(A, x[best], rcond=None)
    return p, q, P[best], (x[best] - (p + q * y[best])).std()

lines = {}
for k, boxes in (('L', a.L), ('R', a.R)):
    if a.one and a.one != k: continue
    P = collect(boxes)
    lines[k] = fit_line(P)
sign = 1 if a.dir == 'fwd' else -1
if len(lines) == 2:
    (pL, qL, PL, sL), (pR, qR, PR, sR) = lines['L'], lines['R']
    yv = (pR - pL) / (qL - qR); xv = pL + qL * yv
else:
    k = a.one; p, q, P, s_ = lines[k]
    yv = a.yh; xv = p + q * yv
beta = math.atan2(yv - cy, f); cb, sb = math.cos(beta), math.sin(beta)
slopes = {}
for k, (p, q, P, s_) in lines.items():
    v = np.stack([P[:, 0] - cx, P[:, 1] - cy, np.full(len(P), f)], 1)
    y2 = v[:, 1] * cb - v[:, 2] * sb; z2 = v[:, 1] * sb + v[:, 2] * cb
    X = v[:, 0] / z2 * f; Y = y2 / z2 * f
    A = np.stack([np.ones(len(Y)), Y], 1)
    (pp, qq), *_ = np.linalg.lstsq(A, X, rcond=None)
    slopes[k] = (qq, len(Y), s_)
alpha = math.atan2(xv - cx, f)
if len(lines) == 2:
    bL, bR = slopes['L'][0], slopes['R'][0]
    dL, dR = a.W * bL / (bR - bL), a.W * bR / (bR - bL)
    h = a.W / ((bR - bL) * math.cos(alpha))
    centre = (dL + dR) / 2
    extra = 'dL %.2f dR %.2f, cam height %.2f m' % (dL, dR, h)
else:
    k = a.one; b = slopes[k][0]
    d = b * a.h * math.cos(alpha)
    centre = d + a.W / 2 if k == 'L' else d - a.W / 2
    extra = 'd%s %.2f (h %.2f given)' % (k, d, a.h)
car_east = -centre * sign
print('%-28s %s VP (%.1f, %.1f) yaw %+.2f | %s | %s | car %+.2f m east of the centre' % (
    '/'.join(a.img.split('/')[-2:]), a.dir, xv, yv, math.degrees(alpha),
    ' '.join('%s b %.4f n %d sd %.2f' % (k, *v) for k, v in slopes.items()), extra, car_east))
if a.dbg:
    d_ = Image.open(a.img).convert('RGB'); D = ImageDraw.Draw(d_)
    for k, col in (('L', (255, 0, 0)), ('R', (0, 255, 255))):
        if k not in lines: continue
        p, q, P, s_ = lines[k]
        for x, y in P: D.ellipse((x - 1, y - 1, x + 1, y + 1), fill=col)
        D.line([(p + q * 900, 900), (p + q * yv, yv)], fill=col, width=1)
    d_.save(a.dbg)
