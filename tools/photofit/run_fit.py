# python run_fit.py <spec.json> <out_cam.json> [--cv] [--lower]
import json, sys
import numpy as np
import fit, cam

spec = json.load(open(sys.argv[1]))
outp = sys.argv[2]
lower = '--lower' in sys.argv
ph = fit.Photo(spec, lower=lower)
best = None
for trial in range(spec.get('starts', 1)):
    p0 = np.array(spec['p0'], float)
    if trial:
        rng = np.random.default_rng(trial)
        p0 = p0 + rng.normal(0, 1, 7) * np.array([300, 300, 100, 2, 1, 0.5, 1500]) * spec.get('jitter', 1.0)
    try:
        p, C, s = ph.fit(p0=p0)
    except Exception as e:
        continue
    if best is None or s < best[2]:
        best = (p, C, s)
p, C, s = best
print('camera', fit.pstr(p), ' rms(weighted) %.2f px' % s)
print('1-sigma:', np.round(np.sqrt(np.diag(C)), 3))
ph.table(p)
out = dict(photo=spec['photo'], size=spec['size'], p=list(map(float, p)), C=C.tolist(), rms=s)
for k in ('seam', 'offR'):
    if k in spec:
        out[k] = spec[k]
out['marks'] = [list(map(float, a)) for a, b in ph.AB] + [list(map(float, b)) for a, b in ph.AB if b is not None]
if 'ids' in spec:
    out['ids'] = spec['ids']
json.dump(out, open(outp, 'w'), indent=1)
if '--cv' in sys.argv:
    n = len(ph.pts)
    P = []
    for a, b in fit.splits(n, spec.get('ncv', 30)):
        pa, _, sa = ph.fit(idx=a, p0=p)
        pb, _, sb = ph.fit(idx=b, p0=p)
        P += [pa, pb]
    P = np.array(P)
    print('split-half spread (std):', np.round(P.std(0), 3))
    np.save(outp.replace('.json', '_cv.npy'), P)
