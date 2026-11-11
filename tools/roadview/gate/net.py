# 1997년 정문의 자리 (reference/고증/4.8_정문_밖.md 「정문의 남북 자리」): Kakao roadview bearings round the gate,
# bundle-adjusted with the eng/ network (tools/roadview/eng/readings.py: the panos up 백양로 that see 제1공학관's old
# south-east corner T, the concave corner Q and 공학원's tower tops gS / gN).
# bearing = floor(pan) + atan((x - 694) / 783) in each pano's own frame (zoom 3, whole-degree pans); unknown pano
# (x, y, heading offset), unknown tie points; priors on T, Q and 창천교회's spires (the west face's corners in OSM).
#   uv run --with numpy --with scipy python tools/roadview/gate/net.py [--kprior 3] [--gS -183.3 -387.6 2] [--face 2]
# Result (2026-11-11): the east pillar's middle (-102.6, -398.8) ± (1.5, 3.8), chi2/dof 1.46; tied to Kakao's places
# (± 3 m) -397.3 ± 1.5; gS held to the skyview's tower -398.3.  2010/916 has only three readings and wanders: ignore it.
# Readings: 2011-04-16 drive 1017220149 - 152, zoom-3 shots at pans 0, 45 .. 315 (rv.mjs shots).  EP_* = the east
# pillar's corners (white frame, black stone face, 2.2 m across): SW / SE seen from the south, NE / NW from the north.
import argparse, math, os, sys
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'eng'))
import readings as ENG

F = 783.0
E_TIP = np.array([-130.98, -305.37]); U = np.array([math.sin(math.radians(15.2)), math.cos(math.radians(15.2))])
NRM = np.array([U[1], -U[0]])

KAKAO = dict(ENG.KAKAO)
KAKAO.update({'2011/149': (-101.5, -411.7), '2011/150': (-105.1, -402.9), '2011/151': (-105.1, -393.3),
              '2011/152': (-103.5, -383.8)})
# (pano, target, pan, x, sigma px)
GATE = [
    ('2011/149', 'gS', 270, 847.0, 1.5), ('2011/149', 'gS', 315, 169.3, 1.5), ('2011/149', 'gN', 315, 689.0, 1.5),
    ('2011/149', 'T', 315, 1115.0, 3), ('2011/149', 'CL', 135, 851.0, 2), ('2011/149', 'CR', 135, 891.0, 2),
    ('2011/149', 'EP_SW', 0, 565.0, 2), ('2011/149', 'EP_SE', 0, 667.0, 2), ('2011/149', 'EP_NE', 0, 695.0, 3),
    ('2011/150', 'gS', 270, 870.8, 1.5), ('2011/150', 'gN', 315, 760.0, 1.5), ('2011/150', 'T', 0, 577.3, 3),
    ('2011/150', 'CL', 135, 978.0, 2), ('2011/150', 'CR', 135, 1018.0, 2), ('2011/150', 'CL', 180, 331.0, 2), ('2011/150', 'CR', 180, 372.0, 2),
    ('2011/150', 'EP_NW', 45, 315.0, 4), ('2011/150', 'EP_SW', 45, 390.0, 4), ('2011/150', 'EP_SE', 45, 647.0, 4),
    ('2011/151', 'gN', 315, 636.0, 4), ('2011/151', 'T', 0, 497.5, 3),
    ('2011/152', 'gS', 270, 699.3, 1.5), ('2011/152', 'gN', 315, 636.3, 1.5), ('2011/152', 'T', 0, 546.7, 3),
    ('2011/152', 'CL', 180, 405.0, 2), ('2011/152', 'CR', 180, 435.0, 2),
    ('2011/152', 'EP_NE', 180, 597.0, 2), ('2011/152', 'EP_NW', 180, 723.0, 2), ('2011/152', 'EP_SW', 180, 777.0, 3),
]
# priors: name -> (x, y, sigma)
PRIOR = {'T': (-124.0, -280.0, 0.6), 'Q': (-151.15, -273.24, 0.5),
         'CL': (-50.7, -523.2, 2.5), 'CR': (-49.1, -545.7, 2.5)}
GUESS = {'gS': (-182, -387), 'gN': (-173, -330), 'rock': (-110, -318), 'EP_SW': (-104, -397), 'EP_SE': (-102, -397),
         'EP_NE': (-102, -395), 'EP_NW': (-104, -395), 'N': (-108.5, -222.0)}


def az(p, q): return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))
def wrap(d): return (d + 180) % 360 - 180
def bearing(pan, x): return math.floor(pan + 1e-9) + math.degrees(math.atan((x - 694) / F))


def run(read, prior, face=0.5, kprior=None, quiet=False, extra_prior=None):
    read = [r for r in read if r[1] not in ('N', 'C12')]
    panos = sorted({r[0] for r in read})
    pts = sorted({('rock' if r[1].startswith('rock') else r[1]) for r in read})
    for k in prior:
        if k not in pts: pts.append(k)
    n = len(panos)
    q0 = []
    for p in panos: q0 += [*KAKAO[p], 0.0]
    for t in pts: q0 += list(prior[t][:2] if t in prior else GUESS[t])
    has_rock = 'rock' in pts
    if has_rock: q0 += [2.0]
    q0 = np.array(q0, float)
    pri = dict(prior)
    if extra_prior: pri.update(extra_prior)

    def unpack(q):
        P = {p: (q[3 * i:3 * i + 2], q[3 * i + 2]) for i, p in enumerate(panos)}
        X = {t: q[3 * n + 2 * j:3 * n + 2 * j + 2] for j, t in enumerate(pts)}
        if has_rock: X['rock_r'] = q[3 * n + 2 * len(pts)]
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
        for t, (x, y, s) in pri.items():
            if t in X: r += list((X[t] - np.array([x, y])) / s)
        if face is not None and 'T' in X:
            r.append(((X['T'] - E_TIP) @ NRM) / face)
        if kprior is not None:
            for p in panos: r += list((P[p][0] - np.array(KAKAO[p])) / kprior)
        return np.array(r)

    sol = least_squares(res, q0, x_scale=1.0)
    J = sol.jac; dof = max(1, len(sol.fun) - len(q0))
    s2 = sol.fun @ sol.fun / dof
    C = np.linalg.pinv(J.T @ J) * max(1.0, s2)
    P, X = unpack(sol.x)
    out = dict(P=P, X=X, chi2=s2, C=C, panos=panos, pts=pts, fun=sol.fun, read=read, n=n)
    if not quiet:
        print('chi2/dof %.2f (dof %d)' % (s2, dof))
        for i, p in enumerate(panos):
            sd = np.sqrt(np.diag(C)[3 * i:3 * i + 3])
            print('  %-13s (%7.1f, %7.1f) ±(%.1f, %.1f) head %+6.2f ±%.2f  - kakao (%+.1f, %+.1f)' % (p, *P[p][0], sd[0], sd[1], P[p][1], sd[2], *(P[p][0] - np.array(KAKAO[p]))))
        for j, t in enumerate(pts):
            k = 3 * n + 2 * j; c = C[k:k + 2, k:k + 2]
            print('  %-6s (%8.2f, %8.2f) ± (%.2f, %.2f)' % (t, *X[t], *np.sqrt(np.diag(c))))
        rr = iter(sol.fun)
        bad = [(p, t, v) for (p, t, *_), v in zip(read, rr) if abs(v) > 2]
        print('  residuals > 2 sigma:', ' '.join('%s:%s %+.1f' % (p[-3:], t, v) for p, t, v in bad))
    return out


def ep_centre(o):
    ks = [k for k in ('EP_SW', 'EP_SE', 'EP_NE', 'EP_NW') if k in o['X']]
    c = np.mean([o['X'][k] for k in ks], 0)
    return c


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--face', type=float, default=0.5)
    ap.add_argument('--kprior', type=float)
    ap.add_argument('--noeng', action='store_true')
    ap.add_argument('--nochurch', action='store_true')
    ap.add_argument('--gS', nargs=3, type=float)
    ap.add_argument('--drop', nargs='*', default=[])
    a = ap.parse_args()
    read = ([] if a.noeng else [r for r in ENG.READ]) + GATE
    read = [r for r in read if '%s:%s' % (r[0], r[1]) not in a.drop and r[0] not in a.drop]
    prior = dict(PRIOR)
    if a.nochurch:
        prior.pop('CL'); prior.pop('CR')
    ex = {'gS': tuple(a.gS)} if a.gS else None
    o = run(read, prior, a.face, a.kprior, extra_prior=ex)
    c = ep_centre(o)
    print('E pillar centre (%.2f, %.2f)' % tuple(c))
