# 제1공학관's east face in one 2011-04 pano (1017220162, pan 312, zoom 3): the window piers of the fourth-floor row,
# read from the north end back, and the face's south-east corner (T) and north end (N) in the same view (issue #83).
# With the piers evenly spaced, their bearings give the face's normal in the pano's frame (c) and each point's
# (along - a0) / D, D being the pano's distance from the face: so N - T = (u_N - u_T) D and the bays between them
# come out without the pano's heading or its place along the road.  D from the lane the car drove in.
#   uv run --with numpy --with scipy python pillars.py
import math
import numpy as np
from scipy.optimize import least_squares

F, PAN = 783.0, 312
PIERS = [1029.5, 994.5, 956.0, 916.0, 869.5, 822.5, 768.5, 715.0, 656.0, 591.0, 536.0]   # px, from the north end
X_N, X_T = 1068.0, 263.0          # the north end against the sky, the 5-storey face's south end against the sky
k = np.arange(len(PIERS))
th = np.degrees(np.arctan((np.array(PIERS) - 694) / F))


def res(q, kk=k, t=th):
    c, u1, beta = q
    return (c + np.degrees(np.arctan(u1 - kk * beta)) - t) / 0.15


best = min((least_squares(res, [c0, 1.0, 0.1]) for c0 in (-40, -25, -10)), key=lambda s: s.cost)
c, u1, beta = best.x
u = lambda x: math.tan(math.radians(math.degrees(math.atan((x - 694) / F)) - c))
uN, uT = u(X_N), u(X_T)
print('face normal at pan %+.2f deg, pier rms %.1f px, bay / D %.4f' % (c, np.sqrt(np.mean((res(best.x) * 0.15 * F * math.pi / 180) ** 2)), beta))
print('T -> N: %.2f D, %.1f bays' % (uN - uT, (uN - uT) / beta))
for D in (42.2, 43.9, 44.9, 45.7):
    print('D %.1f m: N - T %.1f m, N %.1f m along the OSM east face (T at 26.1), bay %.2f m' % (D, (uN - uT) * D, 26.1 + (uN - uT) * D, beta * D))
# D: the game's 백양로 centre is 42.2 m from the face here; the car in the northbound lane 1.65 m east of it (43.9),
# photo A's road ~1 m east of the game's (44.9, reference/고증.md 2.4); Kakao's node 45.7
