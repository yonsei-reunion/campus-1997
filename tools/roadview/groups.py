# The four 「연세인」 groups around the eagle: positions relative to the pillar from bearing differences
# (group centre - pillar centre, same shot, so the heading cancels), with the pano positions from statues.py.
# Result 2026-11-08: A 246° · 4.9 m, B 330° · 4.6 m, C 150° · 4.3 m, D 56° · 4.6 m; facing 194.7 ± 2.0 deg.
#   uv run --with numpy --with scipy python groups.py
# Group centre = middle of the group's white mass / base, read by eye on 2.5-5x crops (+-5 px).
import math, itertools
import numpy as np
from scipy.optimize import least_squares
import bearings as fb
import statues as fit

G2011, GPAST = fb.G2011, fb.GPAST
SIG = 0.37     # deg (5 px)


def solve_past(nm, o, use=None):
    PT = {'E': o['E'], 'F': o['F'], **{k: np.array(v) for k, v in fb.L.items()}}
    d = fb.PAST2[nm]
    obs = [ob for ob in d['obs'] if use is None or ob[0] in use]

    def res(q):
        r = [fit.wrap(fb.bearing(pan, px) - q[2] - fit.az(q[:2], PT[k])) / sg for k, pan, px, sg in obs]
        if d.get('dist') and (use is None or 'dist' in use):
            r.append((np.linalg.norm(PT['E'] - q[:2]) - d['dist'][0]) / d['dist'][1])
        return np.array(r)
    return least_squares(res, np.array([*d['start'], 0.0])).x[:2]


def setup():
    o = fit.solve('two', jit=0.5, quiet=True)
    E = o['E']
    P = {i: o['pos'](o['q'], i) for i in o['ids']}
    # 2010@172 from C12 + E + F (exact), with E, F above
    P['2010@172'] = solve_past('2010@172', o)
    return E, P


def bdiff(pan, x, xe):
    return fb.bearing(pan, x) - fb.bearing(pan, xe)


def solve(E, P, views, drop=()):
    obs = []
    for v, pan, xe, d in views:
        for g, x in d.items():
            if (v, g) not in drop:
                obs.append((v, g, bdiff(pan, x, xe)))
    gs = sorted({g for _, g, _ in obs})

    def res(q):
        off = {g: q[2 * j:2 * j + 2] for j, g in enumerate(gs)}
        return np.array([fit.wrap(b - (fit.az(P[v], E + off[g]) - fit.az(P[v], E))) / SIG for v, g, b in obs])
    q0 = np.concatenate([4.4 * np.array([math.sin(math.radians(a)), math.cos(math.radians(a))]) for a in [240, 330, 148, 70][:len(gs)]])
    r = least_squares(res, q0)
    J = r.jac
    dof = max(1, len(r.fun) - len(q0))
    chi = r.fun @ r.fun / dof
    C = np.linalg.pinv(J.T @ J) * max(1, chi)
    out = {}
    for j, g in enumerate(gs):
        x, y = r.x[2 * j:2 * j + 2]
        cxy = C[2 * j:2 * j + 2, 2 * j:2 * j + 2]
        rr = math.hypot(x, y); az = math.degrees(math.atan2(x, y)) % 360
        # bearing sd from the covariance
        gvec = np.array([y, -x]) / rr ** 2
        saz = math.degrees(math.sqrt(gvec @ cxy @ gvec))
        ur = np.array([x, y]) / rr
        sr = math.sqrt(ur @ cxy @ ur)
        out[g] = (az, saz, rr, sr)
    resid = {(v, g): f * SIG for (v, g, _), f in zip(obs, r.fun)}
    return out, chi, dof, resid


def axis(out):
    # each group's bearing minus its diagonal (A 225, B 315, C 135, D 45 from the facing direction 180 + k):
    # facing = mean(az_g - offset_g) with offsets A +45+180... -> facing f gives diagonals f-45 (C), f+45 (A), f+135 (B), f-135 (D)
    offs = dict(C=-45, A=45, B=135, D=-135)
    vals = {g: (out[g][0] - offs[g]) % 360 for g in out}
    w = {g: 1 / out[g][1] ** 2 for g in out}
    s = sum(w[g] * math.sin(math.radians(vals[g])) for g in out); c = sum(w[g] * math.cos(math.radians(vals[g])) for g in out)
    f = math.degrees(math.atan2(s, c)) % 360
    sf = math.sqrt(1 / sum(w.values()))
    return f, sf, vals


if __name__ == '__main__':
    E, P = setup()
    views = G2011 + GPAST
    out, chi, dof, resid = solve(E, P, views)
    print('eagle pillar', E.round(2), ' chi2/dof %.2f (dof %d, sigma %.2f deg)' % (chi, dof, SIG))
    for g in 'ABCD':
        if g in out:
            print('  %s: bearing %6.1f ± %.1f deg, %.2f ± %.2f m' % (g, *out[g]))
    f, sf, vals = axis(out)
    print('  facing from each group (az - diagonal):', {g: round(v, 1) for g, v in vals.items()})
    print('  weighted mean facing %.1f ± %.1f (scatter sd %.1f)' % (f, sf, np.std(list(vals.values()), ddof=1)))
    # pairs: A-D and B-C diagonals through the pillar
    def dirn(g):
        return np.array([math.sin(math.radians(out[g][0])), math.cos(math.radians(out[g][0]))]) * out[g][2]
    for a, b, off in (('A', 'D', 45), ('B', 'C', 135)):
        v = dirn(a) - dirn(b)
        ang = math.degrees(math.atan2(v[0], v[1])) % 360
        print('  diagonal %s->%s: %.1f -> facing %.1f' % (b, a, ang, (ang - off) % 360))
    print('  residuals (deg):', ' '.join('%s%s %+.2f' % (v, g, r) for (v, g), r in resid.items()))
    # leave one view out
    print('  leave-one-view-out:')
    for v, *_ in views:
        o2, *_ = solve(E, P, [w for w in views if w[0] != v])
        f2, _, _ = axis(o2)
        print('    without %s: facing %.1f  ' % (v, f2) + ' '.join('%s %.0f/%.1f' % (g, o2[g][0], o2[g][2]) for g in 'ABCD' if g in o2))
