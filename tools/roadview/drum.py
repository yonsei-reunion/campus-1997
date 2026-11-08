# Issue #101: 백주년기념관's drum (concert hall) from the 2011-04 백양로 panos, heading-free (reference/고증.md 3.4).
# Every pano has a free heading; positions are Kakao + one shift for the south group (163-177) + a small jitter per
# pano (as statues.py --jit 0.5); the eagle E and 활천대 F are free, OSM corners have a 1 m prior.  The drum's south-west
# silhouette seen from each pano is a line tangent to the circle (cx, cy, R): bearing = az(P, C) + asin(R / |C - P|).
#   uv run --with numpy --with scipy python drum.py [--fixR 17.0] [--loo] [--c12 osm|kakao|drop] [--south]
# --c12 kakao moves 백주년's north-west corner to Kakao's base map (+2.9, -1.6 m), drop leaves its readings out;
# --south adds the 2010-12 south road panos 1016763192 - 194 (free positions, weak).
# Result 2026-11-09: (-8.84, -240.83) ± (1.6, 2.0), d 35.7 ± 3.1 m, chi2/dof 1.20; with d 34 m (-9.19, -241.72);
# C12 at the base map (-7.04, -243.21); without C12 R is free (34 m: (-5.76, -240.40) ± (4.4, 3.3)).
import sys, math, os
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bearings as fb

ROAD = np.array([0.2554, 0.9668]); EAST = np.array([0.9668, -0.2554])
F3 = 783.0
XY = dict(fb.XY)
XY.update({163: (-76.4, -278.1), 165: (-72.0, -259.8), 167: (-66.5, -240.3)})
LMK = {k: np.array(v) for k, v in fb.L.items()}
C12MODE = sys.argv[sys.argv.index('--c12') + 1] if '--c12' in sys.argv else 'osm'
if C12MODE == 'kakao':                      # the Kakao base map's outline: (+2.9, -1.6) m from OSM at C12
    LMK['C12'] = np.array([-11.05 + 2.9, -181.26 - 1.6])
# readings of landmarks: statues.py's own (169-187) + the C12 corner from 163 / 165 / 167 (this pass)
reads = list(fb.READ_SOUTH) + list(fb.READ_NORTH) + [(163, 'C12', 34, 709.2, .1), (165, 'C12', 38, 742.7, .15),
                                                     (167, 'C12', 43, 746.9, .1)]
# the drum's right-hand silhouette (zoom 3, whole-degree pans): per row the strongest light step, median over the rows
# where the edge is upright (163, 165 by eye: trees in front)
DRUM = [(163, 77, 657.0, .2), (165, 92, 693.0, .15), (167, 111, 676.0, .1), (169, 131, 673.4, .1), (170, 140, 672.0, .1),
        (171, 147, 683.0, .1), (172, 153, 663.3, .1), (173, 158, 688.9, .1), (174, 162, 696.5, .1)]


def bearing(pan, px):
    return math.floor(pan + 1e-9) + math.degrees(math.atan((px - 694) / F3))


def az(p, q):
    return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))


def wrap(d):
    return (d + 180) % 360 - 180


# 2010-12 south road (1016763192 - 194): free position (Kakao +- 10 m), free heading; the low block's south-west
# corner (skyview coping end) and the hospital's NW corner (OSM, +- 3 m: its outline is off the roof) and the drum's
# left (DL) and right (DR) silhouettes
SXY = {192: (-10.9, -276.9), 193: (-21.3, -274.1), 194: (-31.7, -272.1)}
SREF = {'BLK': ((-28.6, -254.5), 1.0), 'HOS': ((-2.1, -269.0), 3.0)}
SOUTH = [(192, 'BLK', 345, 583.0, .2), (192, 'DR', 40, 613.0, .2), (192, 'HOS', 40, 790.0, .2),
         (193, 'BLK', 0, 561.0, .2), (193, 'DL', 0, 748.5, .15), (193, 'DR', 50, 670.7, .15), (193, 'HOS', 50, 775.0, .2),
         (194, 'BLK', 5, 700.7, .2), (194, 'DL', 5, 809.6, .15)]
USE_SOUTH = '--south' in sys.argv


def solve(drop=(), fixR=None, jit=0.5, verbose=True):
    rd = [r for r in reads if (r[0], r[1]) not in drop and not (C12MODE == 'drop' and r[1] == 'C12')]
    dr = [r for r in DRUM if (r[0], 'D') not in drop]
    so = [r for r in SOUTH if USE_SOUTH and (r[0], r[1]) not in drop]
    sids = sorted({r[0] for r in so})
    ids = sorted({r[0] for r in rd} | {r[0] for r in dr})
    grp = {i: (0 if i <= 177 else 1) for i in ids}
    lms = sorted({r[1] for r in rd if r[1] in LMK})
    names = ['g0e', 'g0a', 'g1e', 'g1a'] + ['j%d%s' % (i, c) for i in ids for c in 'ea'] + ['h%d' % i for i in ids] + \
        ['Ex', 'Ey', 'Fx', 'Fy'] + ['L%s%s' % (k, c) for k in lms for c in 'xy'] + ['cx', 'cy', 'R'] + \
        ['S%d%s' % (i, c) for i in sids for c in 'xyh'] + (['%s%s' % (k, c) for k in SREF for c in 'xy'] if so else [])
    ix = {n: j for j, n in enumerate(names)}

    def pos(q, i):
        g = grp[i]
        e = q[ix['g%de' % g]] + q[ix['j%de' % i]]
        a = q[ix['g%da' % g]] + q[ix['j%da' % i]]
        return np.array(XY[i]) + EAST * e + ROAD * a

    def pt(q, k):
        if k in ('E', 'F'):
            return q[[ix[k + 'x'], ix[k + 'y']]]
        return q[[ix['L%sx' % k], ix['L%sy' % k]]]

    def res(q):
        r = []
        for i, k, pan, px, sg in rd:
            r.append(wrap(bearing(pan, px) - q[ix['h%d' % i]] - az(pos(q, i), pt(q, k))) / sg)
        for i, (dd, ds) in fb.DIST_2011.items():
            if i in ids:
                r.append((np.linalg.norm(pt(q, 'E') - pos(q, i)) - dd) / ds)
        C = q[[ix['cx'], ix['cy']]]
        R = fixR if fixR else q[ix['R']]
        for i, pan, px, sg in dr:
            P = pos(q, i)
            d = np.linalg.norm(C - P)
            r.append(wrap(bearing(pan, px) - q[ix['h%d' % i]] - (az(P, C) + math.degrees(math.asin(min(1, R / d))))) / sg)
        r += [q[ix['j%d%s' % (i, c)]] / jit for i in ids for c in 'ea']
        for k in lms:
            r += list((pt(q, k) - LMK[k]) / 1.0)
        for i, k, pan, px, sg in so:
            P = q[[ix['S%dx' % i], ix['S%dy' % i]]]
            if k in SREF:
                pred = az(P, q[[ix[k + 'x'], ix[k + 'y']]])
            else:
                d = np.linalg.norm(C - P)
                pred = az(P, C) + (1 if k == 'DR' else -1) * math.degrees(math.asin(min(1, R / d)))
            r.append(wrap(bearing(pan, px) - q[ix['S%dh' % i]] - pred) / sg)
        for i in sids:
            r += list((q[[ix['S%dx' % i], ix['S%dy' % i]]] - np.array(SXY[i])) / 10.0)
        if so:
            for k, (X, s) in SREF.items():
                r += list((q[[ix[k + 'x'], ix[k + 'y']]] - np.array(X)) / s)
        return np.array(r)

    q0 = np.zeros(len(names))
    q0[[ix['Ex'], ix['Ey']]] = (-71.2, -159.4); q0[[ix['Fx'], ix['Fy']]] = (-83.4, -203.2)
    for k in lms:
        q0[[ix['L%sx' % k], ix['L%sy' % k]]] = LMK[k]
    q0[[ix['cx'], ix['cy'], ix['R']]] = (-8, -245, fixR or 17)
    for i in sids:
        q0[[ix['S%dx' % i], ix['S%dy' % i]]] = SXY[i]
    if so:
        for k, (X, s) in SREF.items():
            q0[[ix[k + 'x'], ix[k + 'y']]] = X
    sol = least_squares(res, q0)
    q = sol.x
    dof = max(1, len(sol.fun) - len(q0))
    chi = sol.fun @ sol.fun / dof
    Cv = np.linalg.pinv(sol.jac.T @ sol.jac) * max(1.0, chi)
    sd = np.sqrt(np.diag(Cv))
    out = dict(c=(q[ix['cx']], q[ix['cy']]), R=fixR or q[ix['R']], sd=(sd[ix['cx']], sd[ix['cy']], sd[ix['R']]), chi=chi)
    if verbose:
        print('chi2/dof %.2f (dof %d)  drum centre (%.2f ± %.2f, %.2f ± %.2f)  R %.2f ± %.2f (d %.1f)' % (
            chi, dof, q[ix['cx']], sd[ix['cx']], q[ix['cy']], sd[ix['cy']], out['R'], sd[ix['R']], 2 * out['R']))
        print('  shift south: east %+.2f along %+.2f' % (q[ix['g0e']], q[ix['g0a']]))
        Cc = np.array(out['c'])
        for i, pan, px, sg in dr:
            P = pos(q, i)
            d = np.linalg.norm(Cc - P)
            pred = az(P, Cc) + math.degrees(math.asin(out['R'] / d))
            e = wrap(bearing(pan, px) - q[ix['h%d' % i]] - pred)
            print('  %d  pos (%.1f, %.1f) heading off %+.2f  drum tangent res %+.3f deg (%.2f m at %.0f m)' % (
                i, *P, q[ix['h%d' % i]], e, math.radians(e) * d, d))
        for i in sids:
            print('  south %d at (%.1f, %.1f) heading off %+.1f' % (i, q[ix['S%dx' % i]], q[ix['S%dy' % i]], q[ix['S%dh' % i]]))
        if so:
            print('  block corner (%.1f, %.1f), hospital NW (%.1f, %.1f)' % (q[ix['BLKx']], q[ix['BLKy']], q[ix['HOSx']], q[ix['HOSy']]))
            nres = len(rd) + len(dr)
            print('  south residuals (sigma units):', ' '.join('%d%s %+.2f' % (r[0], r[1], v) for r, v in zip(so, sol.fun[-(len(so) + 2 * len(sids) + 4):])))
    return out


if __name__ == '__main__':
    fixR = float(sys.argv[sys.argv.index('--fixR') + 1]) if '--fixR' in sys.argv else None
    base = solve(fixR=fixR)
    if '--loo' in sys.argv:
        for i, *_ in DRUM:
            o = solve(drop=((i, 'D'),), fixR=fixR, verbose=False)
            print('  drop %d: centre (%.2f, %.2f) R %.2f' % (i, *o['c'], o['R']))
