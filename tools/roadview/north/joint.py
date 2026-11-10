# s 267 - 335 m (issue #82, 2026-11-08).  Joint resection of one drive: every pano's camera on one straight line (bearing th, lateral offset c) plus its own car
# offset east of the road centre (lanes2.py); per pano: along-line position t_i and heading offset h_i (free).
# Optional: per-building shifts (library / union / 백주년 / 백양관) with a prior, heading prior from the yellow-line VP.
#   uv run --with numpy --with scipy --with shapely python joint.py [--set readings] [--only a,b] [--drop k,pano:k]
#        [--shift lib,uni,cen] [--sp 1.5] [--rd] [--th 15.1] [--loo]
# Result: 2010-12 +3.3 .. +3.9 m east of the game line, 2011-04 +0.4 .. +1.1 (bearing fixed at 15.0 deg); the two drives
# part on 백주년기념관's C12 / C14, whose OSM spots and Kakao's base-map outline differ by 3 - 4 m
# (LMSHIFT="C12:2.9:-1.6,C14:2.1:-4.0" moves them; reference/고증.md 2.2.1, 5장).
# #132 (2026-11-11): the C14 readings do not fit OSM's C12 - C14; with C12 alone (--drop C13,C14) 2011 is +1.1 .. +1.7, and
# moving C12 to the base map moves both drives 1.3 - 1.4 m east together, so their ~2.2 m gap is not C12 (../c12/net.py).
import math, argparse, importlib
import numpy as np
from scipy.optimize import least_squares
from lm2 import L
from geo import s_off, OSMLINE, bline
ap = argparse.ArgumentParser()
ap.add_argument('--set', default='readings'); ap.add_argument('--only', default=''); ap.add_argument('--drop', default='')
ap.add_argument('--shift', default=''); ap.add_argument('--sp', type=float, default=1.5)
ap.add_argument('--rd', action='store_true'); ap.add_argument('--rdsd', type=float, default=0.7)
ap.add_argument('--lm', type=float, default=0.5); ap.add_argument('--px', type=float, default=1.5)
ap.add_argument('--loo', action='store_true'); ap.add_argument('--quiet', action='store_true')
ap.add_argument('--fixth', type=float, default=None)
a = ap.parse_args()
R = importlib.import_module(a.set)
GROUP = {'lib': ('libSW', 'libSE', 'libNE'), 'uni': ('uSW', 'uSE', 'uGN', 'uNW'), 'cen': ('C12', 'C13', 'C14'), 'bya': ('bySE',)}
def az(p, q): return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))
def wrap(d): return (d + 180) % 360 - 180
def conv(v):
    b = math.floor(v[0] + 1e-9) + math.degrees(math.atan((v[1] - 694) / 783.0))
    return b, (v[2] if len(v) > 2 else a.px)
drop = set(filter(None, a.drop.split(',')))
names = [n for n in R.P if (not a.only or n in a.only.split(','))]
shifts = list(filter(None, a.shift.split(',')))
O = []   # (pano index, landmark, bearing, sd_px)
for i, n in enumerate(names):
    for k, v in R.P[n]['obs'].items():
        if k.split('#')[0] in drop or ('%s:%s' % (n, k)) in drop or k.split('#')[0] not in L: continue
        b, sp = conv(v); O.append((i, k, b, sp))
P0 = np.array([-38.0, -133.0])
def unpack(q):
    th, c = q[0], q[1]; t = q[2:2 + len(names)]; h = q[2 + len(names):2 + 2 * len(names)]
    sh = {g: q[2 + 2 * len(names) + 2 * j: 4 + 2 * len(names) + 2 * j] for j, g in enumerate(shifts)}
    return th, c, t, h, sh
def cams(th, c, t):
    u = np.array([math.sin(math.radians(th)), math.cos(math.radians(th))]); nE = np.array([u[1], -u[0]])
    return [P0 + t[i] * u + (c + R.P[n]['car']) * nE for i, n in enumerate(names)], u, nE
def lmpos(k, sh):
    p = np.array(L[k.split('#')[0]], float)
    for g, ks in GROUP.items():
        if k.split('#')[0] in ks and g in sh: p = p + sh[g]
    return p
def resid(q, obs=O):
    th, c, t, h, sh = unpack(q)
    if a.fixth is not None: th = a.fixth
    C, u, nE = cams(th, c, t)
    r = []
    for i, k, b, sp in obs:
        p = lmpos(k, sh); d = math.dist(C[i], p)
        sig = math.hypot(math.degrees(sp / 783), math.degrees(a.lm / d))
        r.append(wrap(b - h[i] - az(C[i], p)) / sig)
    if a.rd:
        for i, n in enumerate(names):
            if R.P[n].get('rd') is not None: r.append(wrap(h[i] - (R.P[n]['rd'] - th)) / a.rdsd)
    for g in shifts: r.extend(list(sh[g] / a.sp))
    return np.array(r)
def fit(obs=O):
    t0 = []
    for n in names:
        s0 = np.array(R.P[n]['start']) - P0; t0.append(s0 @ np.array([math.sin(math.radians(15.1)), math.cos(math.radians(15.1))]))
    h0 = []
    for i, n in enumerate(names):
        bs = [wrap(b - az(R.P[n]['start'], L[k.split('#')[0]])) for (j, k, b, sp) in obs if j == i]
        h0.append(np.mean(bs) if bs else 0.0)
    q0 = np.array([15.1, 0.0, *t0, *h0] + [0.0] * (2 * len(shifts)))
    r = least_squares(resid, q0, args=(obs,))
    J = r.jac; Cv = np.linalg.pinv(J.T @ J)
    return r, Cv
def report(r, Cv, tag=''):
    th, c, t, h, sh = unpack(r.x)
    if a.fixth is not None: th = a.fixth
    C, u, nE = cams(th, c, t)
    chi2 = r.fun @ r.fun; dof = len(r.fun) - (len(r.x) - (1 if a.fixth is not None else 0))
    print('%s line bearing %.2f ± %.2f, chi2 %.1f/%d (x%.2f)' % (tag, th, math.sqrt(Cv[0, 0]), chi2, dof, math.sqrt(max(1, chi2 / max(dof, 1)))))
    out = {}
    for i, n in enumerate(names):
        roadc = C[i] - R.P[n]['car'] * nE
        s, e = s_off(*roadc); _, eo = s_off(*roadc, OSMLINE)
        # sd of the road centre east: derivative wrt c, th, t_i
        g = np.zeros(len(r.x)); eps = 1e-4
        for j in (0, 1, 2 + i):
            q2 = r.x.copy(); q2[j] += eps
            th2, c2, t2, *_ = unpack(q2)
            if a.fixth is not None: th2 = a.fixth
            C2, u2, n2 = cams(th2, c2, t2)
            g[j] = (s_off(*(C2[i] - R.P[n]['car'] * n2))[1] - e) / eps
        sd = math.sqrt(g @ Cv @ g)
        out[n] = (s, e, sd, eo)
        print('   %-9s s %5.1f road %+5.2f ± %.2f (OSM %+5.2f) h %+.2f cam (%.2f, %.2f)' % (n, s, e, sd, eo, h[i], *C[i]))
    for g in shifts: print('   shift %s (%.2f, %.2f) ± (%.2f, %.2f)' % (g, *sh[g], math.sqrt(Cv[2 + 2 * len(names) + 2 * shifts.index(g), 2 + 2 * len(names) + 2 * shifts.index(g)]), math.sqrt(Cv[3 + 2 * len(names) + 2 * shifts.index(g), 3 + 2 * len(names) + 2 * shifts.index(g)])))
    return out
r, Cv = fit()
base = report(r, Cv, 'ALL')
if not a.quiet:
    # residuals per landmark
    th, c, t, h, sh = unpack(r.x)
    res = {}
    for (i, k, b, sp), v in zip(O, r.fun):
        res.setdefault(k, []).append('%s:%+.1f' % (names[i][-3:], v))
    for k, v in res.items(): print('   resid/sig %-6s %s' % (k, ' '.join(v)))
if a.loo:
    for key in sorted(set(k.split('#')[0] for (_, k, _, _) in O)):
        obs = [o for o in O if o[1].split('#')[0] != key]
        r2, C2 = fit(obs)
        th, c, t, h, sh = unpack(r2.x)
        if a.fixth is not None: th = a.fixth
        Cs, u, nE = cams(th, c, t)
        vals = ['%s %+.2f' % (n[-3:], s_off(*(Cs[i] - R.P[n]['car'] * nE))[1]) for i, n in enumerate(names)]
        print('   -%-6s th %.2f chi2 %.1f | %s' % (key, th, r2.fun @ r2.fun, ' '.join(vals)))
    for i0, n0 in enumerate(names):
        obs = [o for o in O if o[0] != i0]
        r2, C2 = fit(obs)
        th, c, t, h, sh = unpack(r2.x)
        if a.fixth is not None: th = a.fixth
        Cs, u, nE = cams(th, c, t)
        vals = ['%s %+.2f' % (n[-3:], s_off(*(Cs[i] - R.P[n]['car'] * nE))[1]) for i, n in enumerate(names) if i != i0]
        print('   -%-8s th %.2f chi2 %.1f | %s' % (n0, th, r2.fun @ r2.fun, ' '.join(vals)))
