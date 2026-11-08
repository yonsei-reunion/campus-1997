# back-project road-edge pixels to the 백양로 surface through a fitted camera; s and offset (+ east of the game line)
#   python road.py <cam.json> <edges.json> [--mc N] [--lower]
# edges.json: {"pairs": [{"y": row, "W": [px, py], "E": [px, py], "kind": "curb"}, ...], "singles": [...]}
import json, math, sys
import numpy as np
import scene, cam, fit


def hroad(x, y):
    s, off = scene.s_off(x, y)
    if abs(off) < 14:
        return float(scene.road_h(s))
    return float(scene.terrain(x, y)[0])


def back(p, px, W, H, offR=None, seam=None, lower=False):
    px = np.array(px, float)
    if seam is not None and px[0] >= seam:
        px = px - np.array(offR, float)
    hf = (lambda x, y: hroad(x, y) - fit.dz_terrain(x, y)) if lower else hroad
    X = cam.ground(p, px[0], px[1], W, H, hf, z0=40.0)
    s, off = scene.s_off(X[0], X[1])
    return X, s, off


def measure(c, E, lower=False, p=None):
    p = np.array(c['p'] if p is None else p, float)
    W, H = c['size']
    out = []
    for pr in E['pairs']:
        Xw, sw, ow = back(p, pr['W'], W, H, c.get('offR'), c.get('seam'), lower)
        Xe, se, oe = back(p, pr['E'], W, H, c.get('offR'), c.get('seam'), lower)
        out.append(dict(kind=pr.get('kind', ''), sw=sw, ow=ow, se=se, oe=oe, s=(sw + se) / 2, mid=(ow + oe) / 2,
                        width=math.hypot(*(Xe[:2] - Xw[:2]))))
    return out


if __name__ == '__main__':
    c = json.load(open(sys.argv[1]))
    E = json.load(open(sys.argv[2]))
    lower = '--lower' in sys.argv
    res = measure(c, E, lower)
    for r in res:
        print('%-8s s %6.1f  W %+6.2f  E %+6.2f  centre %+6.2f  width %5.2f' % (r['kind'], r['s'], r['ow'], r['oe'], r['mid'], r['width']))
