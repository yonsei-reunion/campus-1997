# Free resection of one pano: x, y, heading offset from bearings to landmarks (no Kakao heading or position used;
# Kakao position only as the start).  sigma per bearing: 1.5 px reading + 0.7 m landmark error at its distance.
import math, sys, json, itertools
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, '.')
from lm import L, bearing
from geo import s_off
EAST = np.array([0.9668, -0.2554])

def az(p, q):
    return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))
def wrap(d):
    return (d + 180) % 360 - 180

def solve(obs, start, lm_err=0.7, px_err=1.5, verbose=True, fixed_pos=None):
    """obs: {landmark: bearing (deg, pano frame)}; returns (x, y, h), cov, residuals (deg)"""
    ks = list(obs)
    def sig(k, p):
        d = math.dist(p, L[k])
        return math.hypot(math.degrees(px_err / 783), math.degrees(lm_err / d))
    def res(q):
        p = q[:2]
        return np.array([wrap(obs[k] - q[2] - az(p, L[k])) / sig(k, p) for k in ks])
    h0 = np.mean([wrap(obs[k] - az(start, L[k])) for k in ks])
    r = least_squares(res, np.array([*start, h0]))
    J = r.jac
    dof = len(ks) - 3
    C = np.linalg.pinv(J.T @ J)
    chi2 = r.fun @ r.fun
    resid = {k: r.fun[i] * sig(k, r.x[:2]) for i, k in enumerate(ks)}
    return r.x, C, resid, chi2, dof

def report(name, obs, start, car=None, lm_err=0.7):
    x, C, resid, chi2, dof = solve(obs, start, lm_err)
    p = x[:2]
    s, e = s_off(*p)
    sd_e = math.sqrt(EAST @ C[:2, :2] @ EAST)
    scale = math.sqrt(max(1.0, chi2 / dof)) if dof > 0 else 1.0
    line = '%s: pano (%.2f, %.2f) s %.1f, %+.2f ± %.2f m east of the game line (x%.2f chi2/dof %.2f/%d), heading off %+.2f; resid %s' % (
        name, *p, s, e, sd_e, scale, chi2, dof, x[2], ' '.join('%s %+.2f' % (k, v) for k, v in resid.items()))
    print(line)
    if car is not None:
        print('   road centre %+.2f m east of the game line (car %+.2f m east of the centre)' % (e - car, car))
    loo = []
    if len(obs) >= 4:
        for k in obs:
            o2 = {kk: v for kk, v in obs.items() if kk != k}
            x2, *_ = solve(o2, start, lm_err)
            loo.append((k, s_off(*x2[:2])[1]))
        print('   leave-one-out east: ' + ' '.join('-%s %+.2f' % (k, v) for k, v in loo))
    return dict(p=p, s=s, e=e, sd=sd_e * scale, h=x[2], resid=resid, loo=loo)
