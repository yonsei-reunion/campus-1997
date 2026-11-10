# Issue #132: 백주년기념관's north-west corner C12 from a heading-free network (2026-11-11).
# Unknowns: every pano's heading; the 백양로 drives' cameras on one straight line each (bearing TH, lateral c free,
# along t free, the car offset of north/readings*.py east of the road centre, as north/joint.py); other panos (the
# north road) free (x, y); free tie points (eagle E, 활천대 F, C13b); C12 = OSM vertex + a free shift (dx, dy), or held.
# OSM corners of unchanged buildings get a prior of --lm m; every bearing a floor of --floor deg (stitching, tilt).
#   uv run --with numpy --with scipy --with shapely python net.py [--cent free|osm|kakao] [--drop k,pano,pano:k]
#        [--use prefixes] [--loo] [--floor 0.3] [--lm 0.5] [--c14]
# --c14 keeps the readings of the north box's tip C14 (OSM, moving with C12); without --c14 only C12 is used.
# Result (reference/고증/2.1-2.2_항공사진과_중심선.md 2.2.1): not conclusive.  Free C12 shift (-1.1 ± 1.9, -1.1 ± 2.4) m
# without the 제1공학관 readings of 956 / 957, (+1.7 ± 1.2, -3.4 ± 2.3) with them; east shift -1.3 .. +2.6 leaving one
# pano or tie out.  OSM vs the Kakao base map (+2.9, -1.6): chi2 56.7 vs 65.8 (31 dof) / 69.2 vs 69.1 (33 dof).
# With C14 the free shift runs to (+4.6, -8.0), chi2 98.5 vs 63.4: the C14 readings do not fit OSM's C12 - C14.
import argparse, math, os, sys
import numpy as np
from scipy.optimize import least_squares
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'north'))
FIX = {'libSW': (-127.33, -60.21), 'libSE': (-85.44, -71.08), 'libNE': (-65.91, 3.16), 'bySE': (-24.10, 33.19),
       'uNW': (34.00, -30.25), 'uGN': (10.46, -87.86), 'uSW': (4.45, -110.95), 'uSE': (34.70, -118.73),
       'engT': (-123.9, -280.3)}          # engT: 제1공학관's pre-extension SE corner (tools/roadview/eng)
CENT = {'C12': (-11.05, -181.26), 'C14': (16.84, -168.65)}   # 백주년기념관 way 324328422 v12, v14
KAKAO = (2.9, -1.6)                       # Kakao's base map outline at C12, from OSM
P0 = np.array([-38.0, -133.0])


def az(p, q): return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))
def wrap(d): return (d + 180) % 360 - 180


def solve(R, start, tie0, lines, car, th=15.0, lm=0.5, floor=0.3, cent='free', fixcent=(0.0, 0.0)):
    panos = sorted({r[0] for r in R})
    ties = sorted({r[1] for r in R if r[1] not in FIX and r[1] not in CENT})
    fixes = sorted({r[1] for r in R if r[1] in FIX})
    groups = sorted({lines[p] for p in panos if p in lines})
    names = []
    for p in panos: names += ([p + '.t'] if p in lines else [p + '.x', p + '.y']) + [p + '.h']
    names += [g + '.c' for g in groups] + [t + c for t in ties + fixes for c in ('.x', '.y')]
    if cent == 'free': names += ['cdx', 'cdy']
    ix = {n: i for i, n in enumerate(names)}
    U = np.array([math.sin(math.radians(th)), math.cos(math.radians(th))]); NE = np.array([U[1], -U[0]])
    def pos(q, p):
        if p in lines: return P0 + q[ix[p + '.t']] * U + (q[ix[lines[p] + '.c']] + car.get(p, 0.0)) * NE
        return q[[ix[p + '.x'], ix[p + '.y']]]
    def pt(q, k):
        if k in CENT: return np.array(CENT[k]) + (q[[ix['cdx'], ix['cdy']]] if cent == 'free' else np.array(fixcent))
        return q[[ix[k + '.x'], ix[k + '.y']]]
    def res(q):
        r = [wrap(b - q[ix[p + '.h']] - az(pos(q, p), pt(q, k))) / math.hypot(sd, floor) for p, k, b, sd in R]
        for t in fixes: r += list((q[[ix[t + '.x'], ix[t + '.y']]] - np.array(FIX[t])) / lm)
        return np.array(r)
    q0 = np.zeros(len(names))
    for p in panos:
        if p in lines: q0[ix[p + '.t']] = (np.array(start[p]) - P0) @ U
        else: q0[ix[p + '.x']], q0[ix[p + '.y']] = start[p]
    for t in ties: q0[ix[t + '.x']], q0[ix[t + '.y']] = tie0[t]
    for t in fixes: q0[ix[t + '.x']], q0[ix[t + '.y']] = FIX[t]
    for p in panos:
        bs = np.radians([wrap(b - az(pos(q0, p), pt(q0, k))) for pp, k, b, sd in R if pp == p])
        q0[ix[p + '.h']] = math.degrees(math.atan2(np.sin(bs).mean(), np.cos(bs).mean()))
    sol = least_squares(res, q0, x_scale='jac')
    C = np.linalg.pinv(sol.jac.T @ sol.jac)
    return dict(q=sol.x, C=C, chi2=float(sol.fun @ sol.fun), dof=len(sol.fun) - len(q0), ix=ix, panos=panos, ties=ties,
                groups=groups, pos=pos, fun=sol.fun, R=R)


def main():
    import rd_c12 as rd
    from geo import s_off
    ap = argparse.ArgumentParser()
    ap.add_argument('--use', default='2010@17,2010@18,2011@175,2011@176,2011@178,2011@179,2011@181,2011@182,n956,n957')
    ap.add_argument('--drop', default=''); ap.add_argument('--cent', default='free')
    ap.add_argument('--lm', type=float, default=0.5); ap.add_argument('--floor', type=float, default=0.3)
    ap.add_argument('--c14', action='store_true'); ap.add_argument('--loo', action='store_true')
    a = ap.parse_args()
    use = {p for u in a.use.split(',') for p in rd.START if p.startswith(u)}
    drop = set(filter(None, a.drop.split(',')))
    def pick(extra=()):
        return [r for r in rd.R if r[0] in use and (a.c14 or r[1] != 'C14') and r[0] not in drop | set(extra)
                and r[1] not in drop | set(extra) and '%s:%s' % r[:2] not in drop | set(extra)]
    lines = {p: p[:4] for p in rd.START if p[:4] in ('2010', '2011') and 175 <= int(p[5:]) <= 187}
    car = dict(rd.CAR); car.update({p: 0.9 if p.startswith('2011') else 1.15 for p in lines if p not in car})
    cent = 'free' if a.cent == 'free' else 'fix'
    fixc = {'osm': (0.0, 0.0), 'kakao': KAKAO, 'free': (0.0, 0.0)}[a.cent]
    o = solve(pick(), rd.START, rd.TIE0, lines, car, lm=a.lm, floor=a.floor, cent=cent, fixcent=fixc)
    q, C, ix = o['q'], o['C'], o['ix']; sc = math.sqrt(max(1.0, o['chi2'] / max(1, o['dof'])))
    print('chi2 %.1f / %d (x%.2f), C12 %s' % (o['chi2'], o['dof'], sc, a.cent))
    if cent == 'free':
        i, j = ix['cdx'], ix['cdy']
        print('C12 shift from OSM (%+.2f, %+.2f) ± (%.2f, %.2f) -> (%.2f, %.2f)' % (
            q[i], q[j], sc * math.sqrt(abs(C[i, i])), sc * math.sqrt(abs(C[j, j])), CENT['C12'][0] + q[i], CENT['C12'][1] + q[j]))
    for t in o['ties']:
        i, j = ix[t + '.x'], ix[t + '.y']
        print('  %s (%.2f, %.2f) ± (%.2f, %.2f)' % (t, q[i], q[j], sc * math.sqrt(abs(C[i, i])), sc * math.sqrt(abs(C[j, j]))))
    for p in o['panos']:
        P = o['pos'](q, p)
        rs = ' '.join('%s %+.2f' % (k, v * math.hypot(sd, a.floor)) for (pp, k, b, sd), v in zip(o['R'], o['fun']) if pp == p)
        road = ' road %+.2f (s %.0f)' % (s_off(*P)[1] - car.get(p, 0.0), s_off(*P)[0]) if p in lines else ''
        print('  %-9s (%.2f, %.2f)%s | %s' % (p, P[0], P[1], road, rs))
    if a.loo and cent == 'free':
        for x in sorted({r[0] for r in pick()}) + ['E', 'F', 'engT']:
            o2 = solve(pick((x,)), rd.START, rd.TIE0, lines, car, lm=a.lm, floor=a.floor)
            print('  -%-9s shift (%+.2f, %+.2f) chi2 %.1f/%d' % (x, o2['q'][o2['ix']['cdx']], o2['q'][o2['ix']['cdy']], o2['chi2'], o2['dof']))


if __name__ == '__main__':
    main()
