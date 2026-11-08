# 1994 aerial photo (a94.json): refit the camera with roll fixed at 0 and free, at the free focal length and at
# fixed ones; print the 백양로 centre (e94.json verge pairs, back-projected) and the eagle pillar's lateral offset from
# the game eagle (pillar foot read at (1307, 1195) px).  Offsets are + east, the eagle's 'east of game eagle'.
#   uv run --with numpy --with scipy --with shapely --with pillow --with DracoPy python roll94.py
import json, copy, math, sys
import os
HERE = os.path.dirname(os.path.abspath(__file__))
import numpy as np
from scipy.optimize import least_squares
import fit, road, cam, scene
spec = json.load(open(os.path.join(HERE, 'a94.json'))); E = json.load(open(os.path.join(HERE, 'e94.json')))
EAG = np.array([-66.5, -161.0]); EAG_OBS = np.array([1307.0, 1195.0])
def eagle_off(p):
    s0, _ = scene.s_off(*EAG)
    a = scene.heading(s0); t = np.array([math.cos(a), math.sin(a)]); n = np.array([math.sin(a), -math.cos(a)])
    def f(q):
        X = EAG + n * q[0] + t * q[1]
        return cam.project(p, [X[0], X[1], float(scene.terrain(*X)[0]) + 0.4], 3000, 1907)[0] - EAG_OBS
    r = least_squares(f, [0, 0]); return r.x
def run(sp, p0=None):
    ph = fit.Photo(sp)
    p, C, s = ph.fit(p0=p0)
    c = dict(size=sp['size'], p=list(p), seam=sp['seam'], offR=sp['offR'])
    R = road.measure(c, E)
    m = np.array([r['mid'] for r in R]); ss = np.array([r['s'] for r in R])
    return p, C, s, m, ss, ph
for label, fix in [('roll fixed 0', {'5': 0.0}), ('roll free', {})]:
    for f in [None, 2400, 3100, 3500]:
        sp = copy.deepcopy(spec); sp['fix'] = dict(fix)
        if f: sp['fix']['6'] = f
        best = None
        for p0 in ([-231, -843, 190, 17.1, -8.9, 0.0, f or 2847], [-337, -1320, 335, 15.15, -11.3, 0.0, f or 5000]):
            sp['p0'] = p0
            try:
                out = run(sp)
            except Exception as e:
                print('fail', e); continue
            if best is None or out[2] < best[2]: best = out
        p, C, s, m, ss, ph = best
        e = eagle_off(p)
        print('%-13s f %-5s %s rms %.2f | road (s %s) %s mean %+.2f | eagle %+.2f m east of game eagle (ds %+.0f)' % (
            label, f or 'free', fit.pstr(p), s, np.round(ss).astype(int).tolist(), np.round(m, 2).tolist(), m.mean(), e[0], e[1]))
        if label == 'roll free' and f is None:
            print('   roll 1-sigma %.2f deg' % math.sqrt(C[5, 5]))
            ph.table(p)
