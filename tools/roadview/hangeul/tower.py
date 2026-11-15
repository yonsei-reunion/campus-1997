# 연세한글탑 (1992 - 2013 on the round paving south of 중앙도서관): where it stood, from the pre-rebuild roadview, as a
# check on the 1997 aerial scans (reference/고증/4.14_연세한글탑.md 「자리의 교차검증」).  Heading-free: every pano has its own unknown
# heading, Kakao's positions are only starting points (README.md).  Landmarks: ../north/lm2.py (unchanged OSM corners).
#   cd tools/roadview/hangeul && uv run --with numpy --with scipy python tower.py [--model free|line] [--loo]
#        [--drop C12,uSW,...] [--lm 0.5]
# T = the middle of the head's outline (the head is a barrel with a level bore, its outline symmetric about the tower's
# axis from every side), read at zoom 3 in 5x crops; pans are the whole degrees rv.mjs printed.
# Models: free = each pano its own (x, y, heading), only panos with three landmarks or more; line = one straight line
# per drive (bearing, offset), each pano a place along it and a heading (as ../north/joint.py), so panos with two
# landmarks count too.
import argparse, math, os, sys
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'north'))
from lm2 import L

F = 783.0
AERIAL_TOP = (-63.7, -111.0)       # the top where four 1997 scans agree
AERIAL_DISC = (-63.2, -110.9)      # the middle of the round paving in the 1997 scans (radius 7.6 m)
# (pan, x[, sd px]) per pano; landmarks as in ../north/readings.py (2010-12) and readings2011.py / run2011.py (2011-04)
D = {
    '2011': {
        176: dict(start=(-45.3, -154.6), obs={'libSE': (333, 729.5, 3), 'libNE': (351, 734.4, 2.5), 'C12': (129, 670.0), 'T': (335, 735.8)}),
        178: dict(start=(-38.6, -135.5), obs={'libSE': (323, 750.5, 3), 'libNE': (348, 727.3), 'C12': (148, 663.0, 2), 'T': (314, 762.4)}),
        179: dict(start=(-36.6, -127.9), obs={'libSE': (319, 737.5, 3), 'libNE': (347, 740.3, 2), 'C12': (154, 701.5, 4), 'T': (302, 739.5)}),
        181: dict(start=(-32.6, -112.7), obs={'libSE': (308, 702.5, 3), 'libNE': (343, 723.1, 2), 'uSW': (87, 739.2, 2), 'uSW#2': (95, 634.0, 2),
                                              'uSE': (95, 734.0, 2.5), 'T': (273, 678.1)}),
        182: dict(start=(-30.6, -105.2), obs={'libSE': (301, 684.5, 3), 'libNE': (341, 709.0, 2), 'T': (260, 651.7, 2.5)}),
        184: dict(start=(-25.8, -86.0), obs={'libSE': (284, 675.2), 'libNE': (335, 696.0), 'uSW': (129, 767.6), 'uNW': (47, 724.5),
                                             'bySE': (0, 712.5), 'T': (236, 700.0, 3)}),
    },
    '2010': {
        176: dict(start=(-42.6, -151.4), obs={'libSE': (333, 698.0, 3), 'libNE': (351, 724.0, 2.5), 'T': (335, 660.5, 2)}),
        177: dict(start=(-40.2, -142.2), obs={'libSE': (328, 712.0, 6), 'libNE': (350, 722.2, 2), 'C12': (141, 752.0), 'T': (325, 641.7, 2.5)}),
        178: dict(start=(-37.8, -133.1), obs={'libSW': (310, 689.0, 3), 'libSE': (323, 694.0, 3), 'libNE': (348, 727.1), 'bySE': (4, 723.0, 4),
                                              'uSW': (60, 728.5), 'C12': (148, 764.5), 'T': (314, 614.4, 2)}),
        179: dict(start=(-35.4, -123.9), obs={'libSW': (306, 679.0, 3), 'libSE': (319, 665.5, 3), 'libNE': (347, 711.3, 2), 'uGN': (49, 757.6, 2.5),
                                              'uSW': (67, 771.0), 'C12': (154, 781.6, 3), 'T': (302, 553.7, 2.5)}),
        181: dict(start=(-33.0, -114.7), obs={'libSW': (298, 712.0, 3), 'libSE': (308, 711.5, 3), 'libNE': (343, 729.0, 3), 'bySE': (3, 716.0, 3),
                                              'uNW': (38, 697.1), 'uSW': (87, 678.3), 'uSE': (87, 805.0, 2.5), 'C12': (162, 725.0, 3),
                                              'T': (273, 734.2, 2)}),
        184: dict(start=(-25.8, -86.4), obs={'libSE': (284, 693.5), 'libNE': (335, 678.3), 'uSW': (129, 715.7), 'uNW': (34, 867.5),
                                             'bySE': (0, 703.0), 'T': (236, 735.0, 2)}),
    },
}
ap = argparse.ArgumentParser()
ap.add_argument('--model', default='free', choices=['free', 'line']); ap.add_argument('--loo', action='store_true')
ap.add_argument('--drop', default=''); ap.add_argument('--lm', type=float, default=0.5); ap.add_argument('--px', type=float, default=1.5)
ap.add_argument('--quiet', action='store_true')
a = ap.parse_args()
DROP = set(filter(None, a.drop.split(',')))


def az(p, q): return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))
def wrap(d): return (d + 180) % 360 - 180
def brg(v): return math.floor(v[0] + 1e-9) + math.degrees(math.atan((v[1] - 694) / F))


def fit(drive, skip=None, quiet=False):
    P = {i: d for i, d in D[drive].items() if i != skip}
    obs = {i: {k: v for k, v in d['obs'].items() if k.split('#')[0] not in DROP} for i, d in P.items()}
    if a.model == 'free':
        obs = {i: o for i, o in obs.items() if len([k for k in o if k != 'T']) >= 3}
    ids = sorted(obs)
    n = len(ids)
    u0 = np.array([math.sin(math.radians(15.1)), math.cos(math.radians(15.1))])
    P0 = np.array([-38.0, -133.0])

    def cams(q):
        if a.model == 'free':
            return [q[3 * j:3 * j + 2] for j in range(n)], [q[3 * j + 2] for j in range(n)], q[3 * n:3 * n + 2]
        th, c = q[0], q[1]
        u = np.array([math.sin(math.radians(th)), math.cos(math.radians(th))]); e = np.array([u[1], -u[0]])
        return [P0 + q[2 + j] * u + c * e for j in range(n)], list(q[2 + n:2 + 2 * n]), q[2 + 2 * n:4 + 2 * n]

    def res(q):
        C, h, T = cams(q)
        r = []
        for j, i in enumerate(ids):
            for k, v in obs[i].items():
                X = T if k == 'T' else np.array(L[k.split('#')[0]])
                sp = v[2] if len(v) > 2 else a.px
                sg = math.degrees(sp / F) if k == 'T' else math.hypot(math.degrees(sp / F), math.degrees(a.lm / math.dist(C[j], X)))
                r.append(wrap(brg(v) - h[j] - az(C[j], X)) / sg)
        return np.array(r)

    h0 = [np.mean([wrap(brg(v) - az(P[i]['start'], L[k.split('#')[0]])) for k, v in obs[i].items() if k != 'T']) for i in ids]
    if a.model == 'free':
        q0 = np.concatenate([np.concatenate([P[i]['start'], [h0[j]]]) for j, i in enumerate(ids)] + [np.array(AERIAL_DISC) + (3.0, 3.0)])
    else:
        q0 = np.array([15.1, 0.0] + [(np.array(P[i]['start']) - P0) @ u0 for i in ids] + h0 + [AERIAL_DISC[0] + 3, AERIAL_DISC[1] + 3])
    r = least_squares(res, q0)
    dof = max(1, len(r.fun) - len(r.x))
    chi2 = r.fun @ r.fun
    Cv = np.linalg.pinv(r.jac.T @ r.jac) * max(1.0, chi2 / dof)
    C, h, T = cams(r.x)
    sd = np.sqrt(np.diag(Cv)[-2:])
    if not quiet:
        print('%s %s: T (%.2f, %.2f) ± (%.2f, %.2f), chi2 %.1f/%d; from the aerial top %+.2f east %+.2f north, from the disc %+.2f %+.2f' % (
            drive, a.model, *T, *sd, chi2, dof, T[0] - AERIAL_TOP[0], T[1] - AERIAL_TOP[1], T[0] - AERIAL_DISC[0], T[1] - AERIAL_DISC[1]))
        k = 0
        for j, i in enumerate(ids):
            rs = []
            for kk, v in obs[i].items():
                sp = v[2] if len(v) > 2 else a.px
                X = T if kk == 'T' else np.array(L[kk.split('#')[0]])
                rs.append('%s %+.2f' % (kk, wrap(brg(v) - h[j] - az(C[j], X))))
                k += 1
            if not a.quiet:
                print('   %d cam (%.2f, %.2f) h %+.2f, %.1f m from T, T seen from az %.0f | resid deg: %s' % (
                    i, *C[j], h[j], math.dist(C[j], T), az(T, C[j]) % 360, ' '.join(rs)))
    return T, sd, chi2, dof


res_all = {}
for drive in D:
    T, sd, chi2, dof = fit(drive)
    res_all[drive] = (T, sd)
    if a.loo:
        for i in D[drive]:
            try:
                T2, *_ = fit(drive, skip=i, quiet=True)
                print('   without %d: T (%.2f, %.2f)' % (i, *T2))
            except Exception as e:
                print('   without %d: -' % i)
(T1, s1), (T2, s2) = res_all['2011'], res_all['2010']
w1, w2 = 1 / s1 ** 2, 1 / s2 ** 2
Tm = (T1 * w1 + T2 * w2) / (w1 + w2)
print('two drives apart by (%.2f, %.2f) m; weighted mean (%.2f, %.2f) ± (%.2f, %.2f); aerial top (%.1f, %.1f), disc (%.1f, %.1f)' % (
    *(T1 - T2), *Tm, *(1 / np.sqrt(w1 + w2)), *AERIAL_TOP, *AERIAL_DISC))
