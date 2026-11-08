# same fit with roll free and one radial distortion term k1 (image coords normalised by f), applied in cam.project / cam.ray
import json, copy, math
import os
HERE = os.path.dirname(os.path.abspath(__file__))
import numpy as np
from scipy.optimize import least_squares
import cam, fit, road, scene
K1 = [0.0]
_proj, _ray = cam.project, cam.ray
def project(p, X, W, H, off=(0.0, 0.0)):
    q = _proj(p, X, W, H, off)
    c = np.array([W / 2 + off[0], H / 2 + off[1]]); f = p[6]
    u = (q - c) / f; r2 = (u ** 2).sum(-1, keepdims=True)
    return c + u * (1 + K1[0] * r2) * f
def ray(p, px, py, W, H, off=(0.0, 0.0)):
    c = np.array([W / 2 + off[0], H / 2 + off[1]]); f = p[6]
    ud = (np.array([px, py]) - c) / f; u = ud.copy()
    for _ in range(20):
        u = ud / (1 + K1[0] * (u ** 2).sum())
    q = c + u * f
    return _ray(p, q[0], q[1], W, H, off)
cam.project, cam.ray = project, ray
spec = json.load(open(os.path.join(HERE, 'a94.json'))); spec['fix'] = {}; E = json.load(open(os.path.join(HERE, 'e94.json')))
EAG = np.array([-66.5, -161.0]); EAG_OBS = np.array([1307.0, 1195.0])
def eagle_off(p):
    s0, _ = scene.s_off(*EAG); a = scene.heading(s0)
    t = np.array([math.cos(a), math.sin(a)]); n = np.array([math.sin(a), -math.cos(a)])
    r = least_squares(lambda q: cam.project(p, [*(EAG + n * q[0] + t * q[1]), float(scene.terrain(*(EAG + n * q[0]))[0]) + 0.4], 3000, 1907)[0] - EAG_OBS, [0, 0])
    return r.x[0]
for k in [-0.15, -0.10, -0.05, 0.0, 0.05, 0.10]:
    K1[0] = k
    sp = copy.deepcopy(spec); sp['p0'] = [-235, -831, 185, 17.5, -7.9, 2.0, 2804]
    ph = fit.Photo(sp); p, C, s = ph.fit()
    R = road.measure(dict(size=sp['size'], p=list(p), seam=sp['seam'], offR=sp['offR']), E)
    m = np.array([r['mid'] for r in R]); ss = np.array([r['s'] for r in R])
    print('k1 %+.2f: %s rms %.2f | road s %s -> %s (slope %.2f m/100 m) mean %+.2f | eagle %+.2f' % (
        k, fit.pstr(p), s, np.round(ss).astype(int).tolist(), np.round(m, 2).tolist(), 100 * np.polyfit(ss, m, 1)[0], m.mean(), eagle_off(p)))
