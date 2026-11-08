# Heading-free resection for issue #82: where were the roadview cameras, the 1997 eagle and fountain, and the road,
# relative to unchanged OSM buildings?  Kakao's own north is never used: every pano gets a free heading offset, so
# only angles between things seen from one pano count.  Kakao positions are used only as a shared starting point:
# the panos of a group share one unknown shift (east, along the road).
#   uv run --with numpy --with scipy python resect.py [--model two|one|drift] [--past] [--drop 175:C12 ...]
#   uv run --with numpy --with scipy python resect.py p187        the single cleanest pano: library SE-NE angle at 187
# Models: two = south (169-175) and north (178-187) groups shift separately; one = a single shift; drift = the
# lateral shift changes linearly along the drive.  --past adds the 2010-12 and 2008-08 panos at node 175, each with
# its own free position and heading.  Offsets: + east of the game's 백양로 line / the game eagle.
# Result 2026-11-08 (two, --past): eagle 4.2 ± 0.5 m west, fountain 3.1 ± 1.5 m west, road at the eagle about on the
# game line (2011 +1.3, 2010 −1.7, 2008 +1.6 m); see the issue comment of that date.
import argparse, math
import numpy as np
from scipy.optimize import least_squares, brentq
from bearings import XY, L, OBS_2011, DIST_2011, PAST, CAR_2011, EAGLE_GAME, FOUNTAIN_GAME

ROAD = np.array([0.2554, 0.9668]); EAST = np.array([0.9668, -0.2554]); WEST = -EAST     # 백양로 ~14.8 deg
EG, FG = np.array(EAGLE_GAME), np.array(FOUNTAIN_GAME)
G = EG + EAST * 16.18                 # the game line abreast of the game eagle (the eagle stands 16.18 m west of it)
LM = {k: np.array(v) for k, v in L.items()}
SOUTH = {169, 172, 175}
S_OF = {i: 243.1 + (np.array(XY[i]) - np.array(XY[175])) @ ROAD for i in XY}   # rough arc length along 백양로
KAKAO_OFF_175 = 4.3                   # Kakao position of pano 175, m east of the game line


def az(p, q):
    return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))


def wrap(d):
    return (d + 180) % 360 - 180


def sig(i, k):
    return 1.0 if (k == 'NE' and i in (178, 181)) else 0.3      # far, tree-covered NE corners from 178/181


def fit(model='two', past=False, drop=()):
    ids = list(XY)
    pasts = [n for n in PAST if n.endswith('@175')] if past else []
    n = len(ids)
    # q: shift params (4), headings (n), eagle (2), fountain (2), per past pano (x, y, h)
    def unpack(q):
        sh, h, E, Fp = q[:4], dict(zip(ids, q[4:4 + n])), q[4 + n:6 + n], q[6 + n:8 + n]
        P = {nm: (q[8 + n + 3 * j:10 + n + 3 * j], q[10 + n + 3 * j]) for j, nm in enumerate(pasts)}
        return sh, h, E, Fp, P

    def pos(i, sh):
        if model == 'two':
            e, a = (sh[0], sh[1]) if i in SOUTH else (sh[2], sh[3])
        elif model == 'one':
            e, a = sh[2], sh[3]
        else:                                   # drift: e0 + e1 (s - 270) / 100, one along shift
            e, a = sh[0] + sh[1] * (S_OF[i] - 270) / 100, sh[3]
        return np.array(XY[i]) + EAST * e + ROAD * a

    def res(q):
        sh, h, E, Fp, P = unpack(q)
        r = []
        for i in ids:
            Pi = pos(i, sh)
            for k, b in OBS_2011[i].items():
                if (i, k) in drop:
                    continue
                X = E if k == 'E' else Fp if k == 'F' else LM[k]
                r.append(wrap(b - h[i] - az(Pi, X)) / sig(i, k))
            if i in DIST_2011 and (i, 'dist') not in drop:
                dd, ds = DIST_2011[i]
                r.append((np.linalg.norm(E - Pi) - dd) / ds)
        for nm, (Pp, hp) in P.items():
            for k, b in PAST[nm]['obs'].items():
                r.append(wrap(b - hp - az(Pp, E if k == 'E' else LM[k])) / 0.3)
            if PAST[nm].get('dist'):
                dd, ds = PAST[nm]['dist']
                r.append((np.linalg.norm(E - Pp) - dd) / ds)
        return np.array(r)

    q0 = np.concatenate([np.zeros(4), np.zeros(n), EG, FG] + [np.concatenate([np.array(XY[175]) + EAST * 3, [0]]) for _ in pasts])
    r = least_squares(res, q0)
    J = r.jac
    free = np.abs(J).sum(0) > 1e-9
    dof = max(1, len(r.fun) - free.sum())
    Cf = np.linalg.pinv(J[:, free].T @ J[:, free]) * max(1, r.fun @ r.fun / dof)
    C = np.zeros((len(q0),) * 2)
    C[np.ix_(free, free)] = Cf
    sd = np.sqrt(np.diag(C))
    sh, h, E, Fp, P = unpack(r.x)
    ce = C[4 + n:6 + n, 4 + n:6 + n]
    cf = C[6 + n:8 + n, 6 + n:8 + n]
    print('model %s%s, chi2/dof %.2f (dof %d)' % (model, ' + past panos' if past else '', r.fun @ r.fun / dof, dof))
    if model == 'two':
        print('  pano shift south 169-175: east %+.2f ± %.2f, along %+.2f ± %.2f' % (sh[0], sd[0], sh[1], sd[1]))
    if model in ('two', 'one'):
        print('  pano shift %s: east %+.2f ± %.2f, along %+.2f ± %.2f' % ('north 178-187' if model == 'two' else 'all', sh[2], sd[2], sh[3], sd[3]))
    if model == 'drift':
        print('  lateral shift e(s) = %+.2f %+.2f per 100 m (sd %.2f, %.2f), along %+.2f' % (sh[0], sh[1], sd[0], sd[1], sh[3]))
    d = E - EG
    print('  eagle   (%.2f, %.2f): %+.2f ± %.2f m west of the game eagle, %+.2f along' % (*E, d @ WEST, math.sqrt(WEST @ ce @ WEST), d @ ROAD))
    d = Fp - FG
    print('  fountain (%.2f, %.2f): %+.2f ± %.2f m west of the game fountain, %+.2f along' % (*Fp, d @ WEST, math.sqrt(WEST @ cf @ WEST), d @ ROAD))
    p175 = pos(175, sh)
    road = (p175 - G) @ EAST - CAR_2011
    print('  road centre at the eagle (2011, from pano 175): %+.2f m east of the game line; eagle-road %.2f m' % (road, (p175 - G) @ EAST - CAR_2011 + 16.18 + (E - EG) @ WEST))
    for nm, (Pp, hp) in P.items():
        off = (Pp - G) @ EAST
        car = PAST[nm].get('car')
        print('  %s pano (%.1f, %.1f): %+.2f m east of the game line%s' % (nm, *Pp, off, '' if car is None else '; road centre %+.2f (car %.2f m east of it)' % (off - car, car)))
    print('  headings (Kakao - true):', {i: round(v, 2) for i, v in h.items()})
    return r


def p187():
    K = np.array(XY[187])
    ang = lambda p: (az(p, LM['NE']) - az(p, LM['SE'])) % 360
    obs = OBS_2011[187]['NE'] - OBS_2011[187]['SE']
    print('pano 187: library SE-NE angle %.2f, predicted at the Kakao position %.2f' % (obs, ang(K)))
    for al in (-3, 0, 3):
        e = brentq(lambda e: ang(K + EAST * e + ROAD * al) - obs, -30, 30)
        print('  along %+d m -> %+.2f m east of Kakao' % (al, e))
    for nm in ('2010@187',):
        o = PAST[nm]['obs']
        a10 = o['NE'] - o['SE']
        e = brentq(lambda e: ang(K + EAST * e) - a10, -30, 30)
        print('  %s: angle %.2f -> %+.2f m east of the 2011 Kakao position (a different track)' % (nm, a10, e))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', nargs='?', default='fit')
    ap.add_argument('--model', default='two', choices=['two', 'one', 'drift'])
    ap.add_argument('--past', action='store_true')
    ap.add_argument('--drop', nargs='*', default=[], help='pano:kind, e.g. 175:C12 175:dist')
    a = ap.parse_args()
    if a.cmd == 'p187':
        p187()
    else:
        fit(a.model, a.past, {(int(x.split(':')[0]), x.split(':')[1]) for x in a.drop})
