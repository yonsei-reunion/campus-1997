# Issue #82 (road), s 260 - 335 m: heading-free resection of each 2010-12 / 2011-04 pano on unchanged OSM corners
# (lm2.py), road centre = camera - car offset (lanes2.py on the yellow edge lines).
#   uv run --with numpy --with scipy --with shapely python south.py [--rd] [--drop k,k] [--only name,name] [--lm 0.7]
# --rd adds the heading prior of final.py (road direction from the yellow-line VP = bearing 15.1 deg, sd 0.7 deg).
import math, sys, argparse
import numpy as np
from scipy.optimize import least_squares
from lm2 import L
from geo import s_off, OSMLINE
import importlib, os; readings = importlib.import_module(os.environ.get('RSET', 'readings'))
ap = argparse.ArgumentParser()
ap.add_argument('--rd', action='store_true'); ap.add_argument('--rdtrue', type=float, default=15.1)
ap.add_argument('--drop', default=''); ap.add_argument('--only', default='')
ap.add_argument('--lm', type=float, default=0.7); ap.add_argument('--px', type=float, default=1.5)
ap.add_argument('--quiet', action='store_true')
a = ap.parse_args()
EAST = np.array([0.9668, -0.2554])
def az(p, q): return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))
def wrap(d): return (d + 180) % 360 - 180

def conv(v):
    if isinstance(v, tuple):
        b = math.floor(v[0] + 1e-9) + math.degrees(math.atan((v[1] - 694) / 783.0))
        return b, (v[2] if len(v) > 2 else a.px)
    return v, a.px
def solve(d, drop=(), rd=None):
    raw = {k: conv(v) for k, v in d['obs'].items() if k not in drop and k.split('#')[0] in L}
    obs = {k: v[0] for k, v in raw.items()}
    def sig(k, p): return math.hypot(math.degrees(raw[k][1] / 783), math.degrees(a.lm / math.dist(p, L[k.split('#')[0]])))
    def res(q):
        r = [wrap(obs[k] - q[2] - az(q[:2], L[k.split('#')[0]])) / sig(k, q[:2]) for k in obs]
        if rd is not None: r.append(wrap(q[2] - (rd - a.rdtrue)) / 0.7)
        return np.array(r)
    h0 = np.mean([wrap(obs[k] - az(d['start'], L[k.split('#')[0]])) for k in obs])
    r = least_squares(res, np.array([*d['start'], h0]))
    C = np.linalg.pinv(r.jac.T @ r.jac)
    dof = len(r.fun) - 3
    resid = {k: r.fun[i] * sig(k, r.x[:2]) for i, k in enumerate(obs)}
    return r.x, math.sqrt(EAST @ C[:2, :2] @ EAST), float(r.fun @ r.fun), dof, resid, obs

drop0 = tuple(filter(None, a.drop.split(',')))
out = {}
for name, d in readings.P.items():
    if a.only and name not in a.only.split(','): continue
    drop = tuple(k for k in d['obs'] if k in drop0 or k.split('#')[0] in drop0 or ('%s:%s' % (name, k)) in drop0)
    rd = d.get('rd') if a.rd else None
    if a.rd and rd is None: continue
    x, sd, chi2, dof, resid, obs = solve(d, drop, rd)
    car = d.get('car', 0.0)
    s, e = s_off(*x[:2]); _, eo = s_off(*x[:2], OSMLINE)
    scale = math.sqrt(max(1.0, chi2 / dof)) if dof > 0 else 1.0
    loo = {}
    if len(obs) >= 4:
        for k in obs:
            x2, *_ = solve(d, drop + (k,), rd); loo[k] = s_off(*x2[:2])[1] - car
    out[name] = dict(s=s, road=e - car, sd=sd, scale=scale, chi2=chi2, dof=dof, loo=loo, osm=eo - car, cam=x[:2], h=x[2])
    lo = ('%+.2f..%+.2f' % (min(loo.values()), max(loo.values()))) if loo else '-'
    print('%-9s s %5.1f cam (%.2f, %.2f) | road %+5.2f ± %.2f (x%.2f) OSM %+5.2f | chi2 %5.2f/%d | h %+.2f | LOO %s | n %d' % (
        name, s, *x[:2], e - car, sd, scale, eo - car, chi2, dof, x[2], lo, len(obs)))
    if not a.quiet:
        print('     resid(deg) ' + ' '.join('%s %+.2f' % kv for kv in resid.items()))
        if loo: print('     LOO        ' + ' '.join('-%s %+.2f' % kv for kv in loo.items()))
