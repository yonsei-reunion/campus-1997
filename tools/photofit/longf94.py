# 1994 aerial photo: force long focal lengths (roll free) to see how far the road can be pushed east and what the
# eagle and the left-out 대강당 points do meanwhile.  Same run line as roll94.py.
import json, copy, math
import os
HERE = os.path.dirname(os.path.abspath(__file__))
import numpy as np
from scipy.optimize import least_squares
import fit, road, cam, scene
spec = json.load(open(os.path.join(HERE, 'a94.json'))); E = json.load(open(os.path.join(HERE, 'e94.json')))
for p_ in spec['pts']:
    if p_.get('off'):
        p_.pop('off'); p_['w'] = [0.0, 0.0]; p_['chk'] = True
EAG = np.array([-66.5, -161.0]); EAG_OBS = np.array([1307.0, 1195.0])
def eagle_off(p):
    s0, _ = scene.s_off(*EAG); a = scene.heading(s0)
    t = np.array([math.cos(a), math.sin(a)]); n = np.array([math.sin(a), -math.cos(a)])
    r = least_squares(lambda q: cam.project(p, [*(EAG + n * q[0] + t * q[1]), float(scene.terrain(*(EAG + n * q[0]))[0]) + 0.4], 3000, 1907)[0] - EAG_OBS, [0, 0])
    return r.x[0]
prev = [-235, -831, 185, 17.5, -7.9, 2.0, 2804]
for f in [None, 3500, 4000, 4400, 5000, 6000]:
    sp = copy.deepcopy(spec); sp['fix'] = {} if f is None else {'6': f}
    sp['p0'] = list(prev); sp['p0'][6] = f or 2804
    if f: sp['p0'][1] = -831 - (f - 2804) * 0.30; sp['p0'][0] = -235 - (f - 2804) * 0.07; sp['p0'][2] = 185 + (f - 2804) * 0.06
    ph = fit.Photo(sp); p, C, s = ph.fit()
    R = road.measure(dict(size=sp['size'], p=list(p), seam=sp['seam'], offR=sp['offR']), E)
    m = np.array([r['mid'] for r in R]); ss = np.array([r['s'] for r in R])
    chk = ['%s %+.1f px (%+.1f m)' % (pt['n'].replace(' 앞면', ''), *[ (lambda e, d: (e[0], d[0]))(*ph.ground_res(p, i)) ][0]) for i, pt in enumerate(ph.pts) if pt.get('chk')]
    # rms over control points only (exclude zero-weight checks)
    print('f %-5s rms %.2f | road s 250-310: %s | eagle %+.2f | %s' % (f or '%.0f' % p[6], s, np.round(m[:2], 2).tolist(), eagle_off(p), '; '.join(chk[:2])))
    if f is None: prev = list(p)
