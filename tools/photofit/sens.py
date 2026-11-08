# sensitivity of the road centre offset to the camera solution: fixed focal lengths, split halves, terrain lowered
#   python sens.py <spec.json> <edges.json> [f1 f2 ...]
import json, sys, copy
import numpy as np
import fit, road

spec = json.load(open(sys.argv[1]))
E = json.load(open(sys.argv[2]))
fs = [float(a) for a in sys.argv[3:]]


def run(sp, lower=False, idx=None, p0=None):
    ph = fit.Photo(sp, lower=lower)
    p, C, s = ph.fit(idx=idx, p0=p0)
    c = dict(size=sp['size'], p=list(p))
    for k in ('seam', 'offR'):
        if k in sp:
            c[k] = sp[k]
    R = road.measure(c, E, lower=lower)
    return p, s, R, ph


def summ(R):
    m = np.array([r['mid'] for r in R])
    return m.mean(), m


p, s, R, ph = run(spec)
mu, m = summ(R)
print('base fit %s rms %.1f  centre offsets %s  mean %+.2f' % (fit.pstr(p), s, np.round(m, 2), mu))
for f in fs:
    sp = copy.deepcopy(spec)
    sp['fix'] = dict(sp.get('fix', {}))
    sp['fix']['6'] = f
    sp['p0'] = list(p)
    sp['p0'][6] = f
    # move the starting point back along the view to keep the scale
    pf, sf, Rf, _ = run(sp)
    print('f=%5.0f  %s rms %.1f  centre %s mean %+.2f' % (f, fit.pstr(pf), sf, np.round(summ(Rf)[1], 2), summ(Rf)[0]))
pl, sl, Rl, _ = run(spec, lower=True, p0=p)
print('terrain lowered (game − Copernicus): %s rms %.1f  centre mean %+.2f' % (fit.pstr(pl), sl, summ(Rl)[0]))
n = len(ph.pts)
mus = []
for a, b in fit.splits(n, 30):
    for idx in (a, b):
        try:
            pi, si, Ri, _ = run(spec, idx=idx, p0=p)
            mus.append(summ(Ri)[0])
        except Exception as e:
            pass
mus = np.array(mus)
print('split halves: centre mean %+.2f  std %.2f  range %+.2f .. %+.2f (n=%d)' % (mus.mean(), mus.std(), mus.min(), mus.max(), len(mus)))
q = np.percentile(mus, [16, 50, 84])
print('split halves robust: median %+.2f, 16-84 %% %+.2f .. %+.2f; within 10 m of base: %d / %d' % (
    q[1], q[0], q[2], np.sum(np.abs(mus - mu) < 10), len(mus)))
# leave-one-out
for i in range(n):
    idx = [j for j in range(n) if j != i]
    pi, si, Ri, _ = run(spec, idx=idx, p0=p)
    print('  without %-28s centre %+.2f  rms %.1f' % (ph.pts[i]['n'], summ(Ri)[0], si))
