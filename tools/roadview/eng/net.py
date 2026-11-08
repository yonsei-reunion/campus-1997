# 제1공학관's south-east corner before the 2014 - 2015 extension (issue #82, 2026-11-08), from 2008-08, 2010-12 and 2011-04
# panos round the gate's side road.  Bundle adjustment of bearings: unknown pano (x, y, heading offset), unknown points; known points fixed.
#   uv run --with numpy --with scipy python net.py [--face S] [--kprior S] [--drop pano:target] [--free Q] [--loo]
# Result: T (-123.9 ± 0.4, -280.3 ± 0.6), 26 m north of OSM's slanted tip E, neither FOOTPRINT_1997's A nor E; on the
# east face and the west wing's south face line within 0.3 m (reference/고증.md 3.8, 2.2).
import argparse, math, sys
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from readings import READ, KAKAO, KNOWN, F
E_TIP = np.array([-130.98, -305.37]); U = np.array([math.sin(math.radians(15.2)), math.cos(math.radians(15.2))])
NRM = np.array([U[1], -U[0]])                       # east normal of the east face
V9, V11 = np.array([-151.15, -273.24]), np.array([-137.84, -276.66])
A_FP, E_OSM = np.array([-127.6, -296.97]), E_TIP
def az(p, q): return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))
def wrap(d): return (d + 180) % 360 - 180
def bearing(pan, x): return math.floor(pan + 1e-9) + math.degrees(math.atan((x - 694) / F))
def run(read, known, face=None, kprior=None, quiet=False, start=None):
    panos = sorted({r[0] for r in read}); pts = sorted({('rock' if r[1].startswith('rock') else r[1]) for r in read if r[1] not in known})
    # need >= 3 obs per pano
    cnt = {p: sum(1 for r in read if r[0] == p) for p in panos}
    panos = [p for p in panos if cnt[p] >= 3]; read = [r for r in read if r[0] in panos]
    n = len(panos)
    guess = {'rock': (-110, -318), 'T': (-124, -282), 'gN': (-166, -330), 'gS': (-180, -385), 'Q': tuple(KNOWN['Q']), 'C12': KNOWN['C12']}
    q0 = []
    for p in panos:
        q0 += [*KAKAO[p], 0.0]
    for t in pts:
        q0 += list(guess[t])
    if 'rock' in pts: q0 += [2.0]
    q0 = np.array(q0, float)
    if start is not None: q0 = start
    def unpack(q):
        P = {p: (q[3 * i:3 * i + 2], q[3 * i + 2]) for i, p in enumerate(panos)}
        X = dict(known); X = {k: np.array(v) for k, v in X.items()}
        for j, t in enumerate(pts): X[t] = q[3 * n + 2 * j:3 * n + 2 * j + 2]
        if 'rock' in pts: X['rock_r'] = q[3 * n + 2 * len(pts)]
        return P, X
    def res(q):
        P, X = unpack(q); r = []
        for p, t, pan, x, s in read:
            sdeg = math.degrees(math.atan(s / F))
            if t.startswith('rock'):
                c = X['rock']; d = np.linalg.norm(c - P[p][0]); w = math.degrees(math.asin(min(0.99, abs(X['rock_r']) / d)))
                pred = az(P[p][0], c) + (-w if t == 'rockL' else w)
            else:
                pred = az(P[p][0], X[t])
            r.append(wrap(bearing(pan, x) - P[p][1] - pred) / sdeg)
        if face is not None and 'T' in X:
            r.append(((X['T'] - E_TIP) @ NRM) / face)
        if kprior is not None:
            for p in panos: r += list((P[p][0] - np.array(KAKAO[p])) / kprior)
        return np.array(r)
    sol = least_squares(res, q0)
    J = sol.jac; dof = max(1, len(sol.fun) - len(q0))
    s2 = sol.fun @ sol.fun / dof
    C = np.linalg.pinv(J.T @ J) * max(1.0, s2)
    P, X = unpack(sol.x)
    out = dict(P=P, X=X, chi2=s2, dof=dof, C=C, panos=panos, pts=pts, fun=sol.fun, x=sol.x, read=read)
    if not quiet:
        print('chi2/dof %.2f (dof %d)' % (s2, dof))
        for i, p in enumerate(panos):
            sd = np.sqrt(np.diag(C)[3 * i:3 * i + 3])
            print('  %s (%.1f, %.1f) ±(%.1f, %.1f) head %+.2f ±%.2f   kakao (%+.1f, %+.1f)' % (p, *P[p][0], sd[0], sd[1], P[p][1], sd[2], *(P[p][0] - np.array(KAKAO[p]))))
        for j, t in enumerate(pts):
            k = 3 * n + 2 * j; c = C[k:k + 2, k:k + 2]
            print('  %-3s (%.2f, %.2f) ± (%.2f, %.2f)' % (t, *X[t], *np.sqrt(np.diag(c))))
        if 'rock' in X: print('  rock radius %.2f m' % X['rock_r'])
        if 'T' in X:
            T = X['T']; j = pts.index('T'); k = 3 * n + 2 * j; c = C[k:k + 2, k:k + 2]
            a = (T - E_TIP) @ U; e = (T - E_TIP) @ NRM
            print('  T: along the OSM east face %.2f m north of E (±%.2f), %.2f m east of it (±%.2f)' % (a, math.sqrt(U @ c @ U), e, math.sqrt(NRM @ c @ NRM)))
            d9 = V11 - V9; d9 /= np.linalg.norm(d9); n9 = np.array([d9[1], -d9[0]])
            print('     off the v9-v11 facade line %.2f m (+ = south); from A %.1f m, from E %.1f m' % (-(T - V9) @ np.array([-d9[1], d9[0]]), np.linalg.norm(T - A_FP), np.linalg.norm(T - E_OSM)))
        rr = iter(sol.fun)
        print('  residuals (sigma units):', ' '.join('%s:%s %+.1f' % (p[-3:], t, next(rr)) for p, t, *_ in read))
    return out
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--face', type=float); ap.add_argument('--kprior', type=float)
    ap.add_argument('--drop', nargs='*', default=[]); ap.add_argument('--free', nargs='*', default=[])
    ap.add_argument('--loo', action='store_true'); ap.add_argument('--only', default='')
    a = ap.parse_args()
    known = {k: v for k, v in KNOWN.items() if k not in a.free}
    read = [r for r in READ if '%s:%s' % (r[0][-3:], r[1]) not in a.drop and (not a.only or r[0].startswith(a.only))]
    base = run(read, known, a.face, a.kprior)
    if a.loo:
        print('\nleave-one-out (T along / east):')
        vals = []
        for i, r in enumerate(read):
            o = run(read[:i] + read[i + 1:], known, a.face, a.kprior, quiet=True)
            if 'T' not in o['X']: continue
            T = o['X']['T']; al = (T - E_TIP) @ U; e = (T - E_TIP) @ NRM; vals.append((al, e))
            print('  -%s:%s  T (%.2f, %.2f) along %.2f east %.2f chi2 %.2f' % (r[0], r[1], *T, al, e, o['chi2']))
        v = np.array(vals); print('  range along %.2f..%.2f, east %.2f..%.2f' % (v[:, 0].min(), v[:, 0].max(), v[:, 1].min(), v[:, 1].max()))
