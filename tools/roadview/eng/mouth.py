# 제1공학관 앞 진입로 (2026-11-11): where the boxwood verge opens before the hall's door, the door itself and the bollard
# row across the forecourt, from the 2008-08 (2381234, past of node 1017220165) and 2011-04 (1017220165) panos.
#   uv run --with numpy --with scipy --with shapely python tools/roadview/eng/mouth.py
# No Kakao heading or position: each pano's heading from the vanishing point of the two yellow edge lines in a view up
# the road (pan 15, zoom 3), its place across the road from their slopes (6.46 m apart, game ROAD), along it from the
# bearing to 제1공학관's pre-extension south-east corner T (net.py: (-124.0, -280.0)).  Then the verge ends' tips (on
# the verge's middle line, 4.5 m west of the centre line), the door (on the east face line) and the bollards (their
# feet's rows under the horizon, the vanishing point's row, at the camera height the yellow lines give).
# Result: verge open s 161.3 - 173.0 (2008), 161.9 - 173.4 (2011), +-0.3 for +-0.3 deg of heading; the door's middle
# 28.0 - 28.2 m from T along the face (the game 28.5); bollards 11.3 / 10.9 m west of the centre line
# Photo A (May 1997) has the verge whole over the north half of that: the game opens only the planting strip
# (reference/고증/3.8_제1공학관.md, tools/build_campus.py ENG_MOUTH).
import json, math, os
import numpy as np
from scipy.optimize import brentq
from shapely.geometry import LineString, Point

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
C = json.load(open(os.path.join(ROOT, 'web/public/data/campus.json')))
BL = LineString(C['baekyangro']['pts'])
F = 785.0                                            # zoom 3, 1388 x 900 view
T = np.array((-124.0, -280.0))
E_TIP = np.array([-130.98, -305.37])
U = np.array([math.sin(math.radians(15.2)), math.cos(math.radians(15.2))])     # along the east face


def along(s, off):
    p = BL.interpolate(s); p2 = BL.interpolate(min(BL.length, s + 1)); p0 = BL.interpolate(max(0, s - 1))
    tx, ty = p2.x - p0.x, p2.y - p0.y; n = math.hypot(tx, ty)
    return np.array([p.x - ty / n * off, p.y + tx / n * off])


def s_off(q):
    s = BL.project(Point(*q)); p = BL.interpolate(s); p2 = BL.interpolate(min(BL.length, s + 1))
    p0 = BL.interpolate(max(0, s - 1)); a = math.atan2(p2.y - p0.y, p2.x - p0.x)
    return s, (q[0] - p.x) * -math.sin(a) + (q[1] - p.y) * math.cos(a)


def bearing(pan, x):
    return math.floor(pan) + math.degrees(math.atan((x - 694) / F))


def az(p, q):
    return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1])) % 360


def dirv(b):
    return np.array([math.sin(math.radians(b)), math.cos(math.radians(b))])


def on_off(P, b, off):
    d = dirv(b)
    return P + d * brentq(lambda t: s_off(P + d * t)[1] - off, 0.1, 200)


ROAD_AZ = math.degrees(math.atan2(*(along(180, 0) - along(170, 0))))
# per pano: vanishing point column (pan 15), yellow lines' slopes dx/dy (west, east), horizon row; (pan, column) of T,
# the verge ends L (south) / R (north) and the door's middle D; bollards (pan, column); their feet (column, row)
PANOS = {
    '2008-08 2381234': dict(vp=740.9, sl=(2.566, 0.0812), yh=431.9, T=(248, 837), L=(248, 808), D=(304, 516.5), R=(304, 1099),
                            bol=[(304, x) for x in (86.7, 176.7, 266.7, 354.7, 433.3, 511.3, 658, 788.7, 852, 908.7)],
                            feet=[(354, 572.7), (433, 571.7), (511, 569.3), (658, 566)]),
    '2011-04 1017220165': dict(vp=738.8, sl=(2.0231, 0.749), yh=432.5, T=(248, 792), L=(248, 604), D=(304, 474.4), R=(304, 1052),
                               bol=[(304, x) for x in (80, 193, 290, 384, 474, 718, 791, 857, 920)],
                               feet=[(384, 582.5), (474, 581.5), (718, 574), (791, 572.5), (857, 569), (920, 566.5)]),
}
uT = (T - E_TIP) @ U
for name, P_ in PANOS.items():
    h0 = 15 + math.degrees(math.atan((P_['vp'] - 694) / F)) - ROAD_AZ
    aw, ae = P_['sl']; hc = 6.46 / (aw + ae); off0 = -(3.23 - ae * hc)
    for dh in (-0.3, 0.0, 0.3):
        h = h0 + dh
        bT = bearing(*P_['T']) - h
        s0 = brentq(lambda s: ((az(along(s, off0), T) - bT + 180) % 360) - 180, 140, 200)
        P = along(s0, off0)
        sL = s_off(on_off(P, bearing(*P_['L']) - h, 4.5))[0]
        sR = s_off(on_off(P, bearing(*P_['R']) - h, 4.5))[0]
        d = dirv(bearing(*P_['D']) - h)
        t, u = np.linalg.solve(np.array([d, -U]).T, E_TIP - P)
        print('%s heading %+.2f, %.2f m east, camera %.2f m: pano s %.1f | verge open s %.1f - %.1f (%.1f m) | door s %.1f, %.1f m from T'
              % (name, h, -off0, hc, s0, sL, sR, sR - sL, s_off(P + d * t)[0], u - uT))
        if dh:
            continue
        offs = []
        for x, yb in P_['feet']:
            fwd = hc * F / (yb - P_['yh'])
            v = dirv(304 - h); r = np.array([v[1], -v[0]])
            offs.append(s_off(P + v * fwd + r * fwd * (x - 694) / F)[1])
        om = float(np.mean(offs))
        print('   bollard feet %.1f - %.1f m west (mean %.2f); bollards s %s' % (min(offs), max(offs), om,
              [round(s_off(on_off(P, bearing(pan, x) - h, om))[0], 1) for pan, x in P_['bol']]))
