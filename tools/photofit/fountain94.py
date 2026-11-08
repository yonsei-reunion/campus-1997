# 1994 photo: back-project the eagle pillar foot and the 활천대 pillar foot with the roll-free camera (as roll94.py)
# and compare the eagle->fountain vector with the game's.  Offsets: west / along 백양로 (ROAD).
import json, copy, math, os, sys
import numpy as np
from scipy.optimize import least_squares
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fit, cam, scene
spec = json.load(open(os.path.join(HERE, 'a94.json')))
ROAD = np.array([0.2554, 0.9668]); WEST = np.array([-0.9668, 0.2554])
EG, FG = np.array([-66.5, -161.0]), np.array([-80.7, -203.2])
PIX = {'E': (1307.0, 1195.0), 'F': tuple(map(float, sys.argv[1:3])) if len(sys.argv) > 2 else (1299.6, 1243.0)}
HZ = {'E': 0.4, 'F': 0.0}
def foot(p, k, X0):
    def f(q):
        X = X0 + q
        return cam.project(p, [X[0], X[1], float(scene.terrain(*X)[0]) + HZ[k]], 3000, 1907)[0] - np.array(PIX[k])
    return X0 + least_squares(f, [0, 0]).x
for label, fix in [('roll free', {}), ('roll free f 2400', {'6': 2400}), ('roll free f 3500', {'6': 3500}), ('roll 0', {'5': 0.0})]:
    best = None
    for p0 in ([-231, -843, 190, 17.1, -8.9, 0.0, 2847], [-337, -1320, 335, 15.15, -11.3, 0.0, 5000]):
        sp = copy.deepcopy(spec); sp['fix'] = dict(fix); sp['p0'] = list(p0)
        if '6' in fix: sp['p0'][6] = fix['6']
        ph = fit.Photo(sp)
        try:
            p, C, s = ph.fit(p0=sp['p0'])
        except Exception as e:
            continue
        if best is None or s < best[1]: best = (p, s)
    p, s = best
    E = foot(p, 'E', EG); F = foot(p, 'F', FG)
    d = (F - E) - (FG - EG)
    print('%-17s rms %.2f  eagle %+.2f W %+.2f along | fountain %+.2f W %+.2f along | fountain-eagle %+.2f W %+.2f along, dist %.1f' % (
        label, s, (E - EG) @ WEST, (E - EG) @ ROAD, (F - FG) @ WEST, (F - FG) @ ROAD, d @ WEST, d @ ROAD, np.linalg.norm(F - E)))
