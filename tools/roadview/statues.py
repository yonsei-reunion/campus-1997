# Heading-free resection of the 2011 panos 169-187 (+ past panos), solving the eagle pillar E and the 활천대 pillar F
# (the second pass of 2026-11-08: bearings.py READ_SOUTH, PAST2).
#   uv run --with numpy --with scipy python statues.py --jit 0.5 --past 2010@175 --drop 2010@175:F --loo
#   [--model two|three|drift|one] [--old] [--lm 1.0]
# Every pano gets a free heading.  Kakao positions only through a shared shift per group (model).  Landmarks (OSM
# corners) get a prior of --lm metres (OSM vs skyview "within 1 m"); 0 fixes them.  --old uses bearings.py's south
# readings instead of the new ones.  --jit gives each pano its own small shift (sd in m): without it the south group's
# one shift leaves C12 and E off by 1.4 deg at 175 and 176 (chi2/dof 60), with 0.5 m chi2/dof is 1.0.
# Output: + east of the game line / the game's first spots for the statues, along = 백양로 direction.
# Result 2026-11-08: fountain 3.2 ± 1.3 m west, eagle 5.1 ± 0.9 m west; the fountain moved 2.0 ± 0.6 m less than the
# eagle (1994 photo 2.4 m, tools/photofit/fountain94.py).  The game took eagle 4.2 m (resect.py, 1994 photo, photo A)
# and fountain 4.2 - 2.0 = 2.2 m west (reference/고증.md 4.1.4, 4.3).
import argparse, math
import numpy as np
from scipy.optimize import least_squares
import bearings as fb

ROAD = np.array([0.2554, 0.9668]); EAST = np.array([0.9668, -0.2554]); WEST = -EAST
EG, FG = np.array([-66.5, -161.0]), np.array([-80.7, -203.2])
G = EG + EAST * 16.18
LMK = {k: np.array(v) for k, v in fb.L.items()}


def az(p, q):
    return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))


def wrap(d):
    return (d + 180) % 360 - 180


def build(model, old=False, past=(), drop=(), lm=1.0, extra=(), jit=0.0):
    reads = (fb.READ_SOUTH_FIRST if old else fb.READ_SOUTH) + fb.READ_NORTH + list(extra)
    reads = [r for r in reads if (r[0], r[1]) not in drop]
    ids = sorted({r[0] for r in reads})
    if model == 'two':
        grp = {i: (0 if i <= 177 else 1) for i in ids}
    elif model == 'three':
        grp = {i: (0 if i <= 172 else 1 if i <= 177 else 2) for i in ids}
    elif model == 'one':
        grp = {i: 0 for i in ids}
    elif model == 'drift':
        grp = {i: 0 for i in ids}
    ng = max(grp.values()) + 1
    lms = sorted({r[1] for r in reads if r[1] in LMK} | {k for nm in past for k, *_ in fb.PAST2[nm]['obs'] if k in LMK})
    names = []
    names += ['g%d_%s' % (g, c) for g in range(ng) for c in 'ea']
    if model == 'drift':
        names += ['drift']
    if jit > 0:
        names += ['j%d_%s' % (i, c) for i in ids for c in 'ea']
    names += ['h%d' % i for i in ids] + ['Ex', 'Ey', 'Fx', 'Fy'] + ['L%s_%s' % (k, c) for k in lms for c in 'xy']
    for nm in past:
        names += ['P%s_%s' % (nm, c) for c in 'xyh']
    ix = {n: j for j, n in enumerate(names)}
    S_OF = {i: 243.1 + (np.array(fb.XY[i]) - np.array(fb.XY[175])) @ ROAD for i in ids}

    def pos(q, i):
        g = grp[i]
        e, a = q[ix['g%d_e' % g]], q[ix['g%d_a' % g]]
        if model == 'drift':
            e = e + q[ix['drift']] * (S_OF[i] - 270) / 100
        if jit > 0:
            e, a = e + q[ix['j%d_e' % i]], a + q[ix['j%d_a' % i]]
        return np.array(fb.XY[i]) + EAST * e + ROAD * a

    def pt(q, k):
        if k == 'E':
            return q[[ix['Ex'], ix['Ey']]]
        if k == 'F':
            return q[[ix['Fx'], ix['Fy']]]
        return q[[ix['L%s_x' % k], ix['L%s_y' % k]]]

    def res(q):
        r = []
        for i, k, pan, px, sg in reads:
            P = pos(q, i)
            r.append(wrap(fb.bearing(pan, px) - q[ix['h%d' % i]] - az(P, pt(q, k))) / sg)
        for i, (dd, ds) in fb.DIST_2011.items():
            if i in ids and (i, 'dist') not in drop:
                r.append((np.linalg.norm(pt(q, 'E') - pos(q, i)) - dd) / ds)
        for nm in past:
            d = fb.PAST2[nm]
            P = q[[ix['P%s_x' % nm], ix['P%s_y' % nm]]]
            for k, pan, px, sg in d['obs']:
                if (nm, k) in drop:
                    continue
                r.append(wrap(fb.bearing(pan, px) - q[ix['P%s_h' % nm]] - az(P, pt(q, k))) / sg)
            if d.get('dist') and (nm, 'dist') not in drop:
                dd, ds = d['dist']
                r.append((np.linalg.norm(pt(q, 'E') - P) - dd) / ds)
        if jit > 0:
            r += [q[ix['j%d_%s' % (i, c)]] / jit for i in ids for c in 'ea']
        for k in lms:
            dv = pt(q, k) - LMK[k]
            if lm > 0:
                r += list(dv / lm)
            else:
                r += list(dv / 1e-3)
        return np.array(r)

    q0 = np.zeros(len(names))
    q0[[ix['Ex'], ix['Ey']]] = EG; q0[[ix['Fx'], ix['Fy']]] = FG
    for k in lms:
        q0[[ix['L%s_x' % k], ix['L%s_y' % k]]] = LMK[k]
    for nm in past:
        q0[[ix['P%s_x' % nm], ix['P%s_y' % nm]]] = fb.PAST2[nm]['start']
    return names, ix, res, q0, pos, ids, grp


def solve(model='two', old=False, past=(), drop=(), lm=1.0, extra=(), quiet=False, jit=0.0):
    names, ix, res, q0, pos, ids, grp = build(model, old, past, drop, lm, extra, jit)
    r = least_squares(res, q0)
    J = r.jac
    nlm = sum(1 for n in names if n.startswith('L')) if lm > 0 else 0
    dof = max(1, len(r.fun) - len(q0))
    chi = r.fun @ r.fun / dof
    C = np.linalg.pinv(J.T @ J) * max(1.0, chi)
    q = r.x
    E, Fp = q[[ix['Ex'], ix['Ey']]], q[[ix['Fx'], ix['Fy']]]
    ce = C[np.ix_([ix['Ex'], ix['Ey']], [ix['Ex'], ix['Ey']])]
    cf = C[np.ix_([ix['Fx'], ix['Fy']], [ix['Fx'], ix['Fy']])]
    out = dict(E=E, F=Fp, eW=(E - EG) @ WEST, eA=(E - EG) @ ROAD, fW=(Fp - FG) @ WEST, fA=(Fp - FG) @ ROAD,
               seW=math.sqrt(WEST @ ce @ WEST), seA=math.sqrt(ROAD @ ce @ ROAD), sfW=math.sqrt(WEST @ cf @ WEST),
               sfA=math.sqrt(ROAD @ cf @ ROAD), chi=chi, dof=dof, q=q, ix=ix, C=C, r=r, pos=pos, ids=ids)
    if not quiet:
        print('model %s%s%s, lm %.1f m, jitter %.1f m: chi2/dof %.2f (dof %d)' % (model, ' old-south' if old else '', ' past ' + ','.join(past) if past else '', lm, jit, chi, dof))
        for g in sorted(set(grp.values())):
            print('  group %d shift: east %+.2f ± %.2f  along %+.2f ± %.2f' % (g, q[ix['g%d_e' % g]], math.sqrt(C[ix['g%d_e' % g]] [ix['g%d_e' % g]]),
                                                                          q[ix['g%d_a' % g]], math.sqrt(C[ix['g%d_a' % g]][ix['g%d_a' % g]])))
        if jit > 0:
            print('  jitter (e, a):', ' '.join('%d %+.1f/%+.1f' % (i, q[ix['j%d_e' % i]], q[ix['j%d_a' % i]]) for i in ids))
        if 'drift' in ix:
            print('  drift %+.2f per 100 m' % q[ix['drift']])
        print('  eagle    (%.2f, %.2f): %+.2f ± %.2f m west of game, %+.2f ± %.2f along' % (*E, out['eW'], out['seW'], out['eA'], out['seA']))
        print('  fountain (%.2f, %.2f): %+.2f ± %.2f m west of game, %+.2f ± %.2f along' % (*Fp, out['fW'], out['sfW'], out['fA'], out['sfA']))
        ii = [ix['Ex'], ix['Ey'], ix['Fx'], ix['Fy']]
        Cs = C[np.ix_(ii, ii)]
        Dm = np.array([[-1, 0, 1, 0], [0, -1, 0, 1]])
        cd = Dm @ Cs @ Dm.T
        dv = (Fp - E) - (FG - EG)
        out['rW'], out['rA'] = dv @ WEST, dv @ ROAD
        out['srW'], out['srA'] = math.sqrt(WEST @ cd @ WEST), math.sqrt(ROAD @ cd @ ROAD)
        print('  eagle-fountain %.2f m (game %.2f); fountain minus eagle shift: west %+.2f ± %.2f, along %+.2f ± %.2f' % (
            np.linalg.norm(E - Fp), np.linalg.norm(EG - FG), out['rW'], out['srW'], out['rA'], out['srA']))
        for nm in past:
            P = q[[ix['P%s_x' % nm], ix['P%s_y' % nm]]]
            print('  %s at (%.2f, %.2f), %+.2f m east of game line, heading off %+.2f' % (nm, *P, (P - G) @ EAST, q[ix['P%s_h' % nm]]))
    return out


def residuals(o, model, old, past, lm):
    names, ix, res, q0, pos, ids, grp = build(model, old, past, (), lm)
    rr = res(o['q'])
    return rr


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='two')
    ap.add_argument('--old', action='store_true')
    ap.add_argument('--past', nargs='*', default=[])
    ap.add_argument('--lm', type=float, default=1.0)
    ap.add_argument('--loo', action='store_true')
    ap.add_argument('--drop', nargs='*', default=[])
    ap.add_argument('--jit', type=float, default=0.0)
    a = ap.parse_args()
    drop = set()
    for d in a.drop:
        p, k = d.split(':')
        drop.add((int(p) if p.isdigit() else p, k))
    o = solve(a.model, a.old, a.past, drop, a.lm, jit=a.jit)
    reads = (fb.READ_SOUTH_FIRST if a.old else fb.READ_SOUTH) + fb.READ_NORTH
    names, ix, res, q0, pos, ids, grp = build(a.model, a.old, a.past, drop, a.lm, jit=a.jit)
    rr = res(o['q'])
    rl = [r for r in reads if (r[0], r[1]) not in drop]
    print('  residuals (deg):', ' '.join('%d%s %+.2f' % (r[0], r[1], v * r[4]) for r, v in zip(rl, rr)))
    if a.loo:
        keys = [(r[0], r[1]) for r in rl] + [(i, 'dist') for i in fb.DIST_2011]
        for nm in a.past:
            keys += [(nm, k) for k, *_ in fb.PAST2[nm]['obs']] + ([(nm, 'dist')] if fb.PAST2[nm].get('dist') else [])
        vals = []
        for key in keys:
            oo = solve(a.model, a.old, a.past, drop | {key}, a.lm, quiet=True, jit=a.jit)
            vals.append((key, oo['fW'], oo['fA'], oo['eW'], oo['fW'] - oo['eW']))
        fw = [v[1] for v in vals]; ew = [v[3] for v in vals]; fa = [v[2] for v in vals]
        rw = [v[4] for v in vals]
        print('  leave-one-out: fountain west %.2f .. %.2f, along %.2f .. %.2f; eagle west %.2f .. %.2f; fountain-eagle west %.2f .. %.2f' % (min(fw), max(fw), min(fa), max(fa), min(ew), max(ew), min(rw), max(rw)))
        for v in sorted(vals, key=lambda v: abs(v[1] - o['fW']))[-4:]:
            print('    drop %s: fountain west %+.2f along %+.2f, eagle west %+.2f' % (v[0], v[1], v[2], v[3]))
