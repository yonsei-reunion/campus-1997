# 1994 aerial photo (the same original as the 1995 scan, reference/고증/1_자료.md 1.2): refit the camera with points
# near its bottom (the eagle's and 활천대's pillar feet as the roadview measured them, the two tracks on the bridge over
# 연세로, 연세로 south of it), check each fit on the points left out, then put the gate pillars' feet (1360 / 1410, 1497
# px) on the ground (reference/고증/4.8_정문_밖.md 「정문의 남북 자리」).
#   uv run --with numpy --with scipy --with shapely --with pillow --with DracoPy python tools/photofit/gate94.py [rail_z]
# Result (2026-11-11): 2.2.1's fit as it is -373 (the rails drawn 136 - 158 px low); with the rails -404 ~ -410 for rail
# tops at 30 - 33 m, but rms 2.5 -> 6 px and the focal length up 1.3 - 1.5 times: ± 8 m or more.
import json, copy, math, sys, os
PF = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PF)
import numpy as np
import fit, cam, scene

RZ = float(sys.argv[1]) if len(sys.argv) > 1 else 31.5
spec = json.load(open(PF + '/a94.json'))
spec['fix'] = {}
spec['p0'] = [-228, -818, 196, 17.4, -9.0, 1.05, 2753]
T = lambda x, y: float(scene.terrain(x, y)[0])
add = [
    # roadview-measured statue feet (reference/고증/4.1, 4.3); the photofit README's pixels
    dict(n='독수리상 기둥 발치', X=[-70.9, -159.8, T(-70.9, -159.8) + 0.4], px=[1307, 1195], g='near'),
    dict(n='활천대 기둥 발치', X=[-83.1, -202.6, T(-83.1, -202.6) + 0.3], px=[1299.6, 1243], g='near'),
]
rails = [
    # the two tracks on the bridge over 연세로 (OSM ways 405594547 / 405594550), the dark ballast lines either side of
    # the north deck, read at x 1700 (right of the spread's gutter), rail top RZ
    dict(n='북쪽 선로 굴다리', type='line', A=[-113.5, -476.6, RZ], B=[-79.2, -475.0, RZ], px=[1700, 1582], g='rail'),
    dict(n='남쪽 선로 굴다리', type='line', A=[-113.3, -486.7, RZ], B=[-79.2, -485.9, RZ], px=[1700, 1594], g='rail'),
]
road = [
    dict(n='연세로 굴다리 남쪽', type='line', A=[-92.0, -500.0, T(-92, -500)], B=[-96.2, -556.1, T(-96.2, -556.1)], px=[1785, 1720], g='road', w=[0.5, 0.5]),
]


def run(sp, label):
    ph = fit.Photo(sp)
    best = None
    for p0 in ([-228, -818, 196, 17.4, -9.0, 1.05, 2753], [-300, -1100, 280, 16.5, -9.5, 1.0, 3500], [-180, -700, 160, 17.5, -9, 1, 2300]):
        try:
            out = ph.fit(p0=p0)
        except Exception as e:
            continue
        if best is None or out[2] < best[2]:
            best = out
    p, C, s = best
    print('== %s: %s rms %.2f  sd(y)=%.1f sd(z)=%.1f' % (label, fit.pstr(p), s, math.sqrt(C[1, 1]), math.sqrt(C[2, 2])))
    return p, ph


def gate_ground(p, px):
    q = cam.ground(p, px[0], px[1], 3000, 1907, T, z0=26.0)
    return q


def check(p, pts):
    for d in pts:
        if d.get('type') == 'line':
            A, B = np.array(d['A']), np.array(d['B'])
            a, b = cam.project(p, np.stack([A, B]), 3000, 1907)
            u = np.array(d['px'], float)
            if u[0] >= 1505: u = u - [136, 0]
            t = b - a; nrm = np.array([t[1], -t[0]]) / np.hypot(*t)
            print('   held-out %-14s perp %+6.1f px' % (d['n'], (a - u) @ nrm))
        else:
            q = cam.project(p, d['X'], 3000, 1907)[0]
            u = np.array(d['px'], float)
            if u[0] >= 1505: u = u - [136, 0]
            print('   held-out %-14s %+6.1f %+6.1f px' % (d['n'], *(q - u)))


GATE_PX = {'W 기둥 발치': (1360, 1497), 'E 기둥 발치': (1410, 1497), '가운데': (1385, 1497)}
for label, extra, held in [('기존 기준점만', [], add + rails + road),
                           ('+ 조형물', add, rails + road),
                           ('+ 조형물 + 선로', add + rails, road),
                           ('+ 조형물 + 선로 + 연세로', add + rails + road, []),
                           ('+ 선로 + 연세로', rails + road, add)]:
    sp = copy.deepcopy(spec)
    sp['pts'] = sp['pts'] + extra
    p, ph = run(sp, label)
    check(p, held)
    for k, px in GATE_PX.items():
        g = gate_ground(p, px)
        print('   %s (%d, %d) -> (%.1f, %.1f, %.1f)' % (k, *px, *g))
