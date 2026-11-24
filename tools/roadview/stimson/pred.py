"""pred.py <pano> <feat> <col> [x y]  -> predicted columns of the other features (kakao position, yaw from one reading)"""
import os
import sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feat import *
pano, f0, c0 = int(sys.argv[1]), sys.argv[2], float(sys.argv[3])
xy = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else P[pano]['xy']
FF = dict(F); FF['ST_SAPEX'] = st(0, 6.5); FF['ST_NAPEX'] = st(LEN, 6.5); FF['AP_SAPEX'] = ((79.83 + 92.32) / 2, (194.74 + 191.49) / 2)
FF['AP_NAPEX'] = ((88.8 + 101.28) / 2, (229.19 + 225.94) / 2); FF['CH?'] = st(17.5, 12.0)
def b(p): return math.degrees(math.atan2(p[0] - xy[0], p[1] - xy[1]))
yaw = (c0 + 0.5) * 360 / 4096 - b(FF[f0])
for k, p in FF.items():
    c = ((b(p) + yaw) % 360) * 4096 / 360 - 0.5
    print(f'{k:9s} c {c:7.0f}  dist {math.hypot(p[0]-xy[0], p[1]-xy[1]):5.1f}')
