"""tilt.py <pano> ...  -- the true 'up' in each equirect from its near-vertical line segments (LSD): the plane through
the camera and a vertical edge holds 'up', so its normal is perpendicular to it.  Robust fit; writes up.json."""
import os
import sys, json, math, numpy as np, cv2
D = os.environ.get('ST_WORK', '/tmp/stimson_rv')
def ray(c, r):
    az = 2 * math.pi * (c + 0.5) / 4096; el = math.pi / 2 - math.pi * (r + 0.5) / 2048
    return np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)])
try: UP = json.load(open(f'{D}/up.json'))
except Exception: UP = {}
for pano in sys.argv[1:]:
    g = cv2.imread(f'{D}/st/tiles/eq/{pano}.jpg', cv2.IMREAD_GRAYSCALE)
    R0, R1 = 640, 1400
    lsd = cv2.createLineSegmentDetector()
    segs = lsd.detect(g[R0:R1])[0].reshape(-1, 4)
    N, Wt, A = [], [], []
    for x1, y1, x2, y2 in segs:
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 45 or abs(x2 - x1) > 0.35 * abs(y2 - y1): continue
        n = np.cross(ray(x1, y1 + R0), ray(x2, y2 + R0)); n /= np.linalg.norm(n)
        N.append(n); Wt.append(L * L); A.append((x1 + x2) / 2)
    N = np.array(N); Wt = np.array(Wt); A = np.array(A)
    up = np.array([0, 0, 1.0]); w = Wt.copy()
    for it in range(30):
        # minimise sum w (n.up)^2 with |up| = 1  -> smallest eigenvector of sum w n n^T
        M = (N * w[:, None]).T @ N
        ev, V = np.linalg.eigh(M); up = V[:, 0] * np.sign(V[2, 0])
        res = np.degrees(np.arcsin(np.clip(N @ up, -1, 1)))     # angle of the plane off vertical
        thr = [8, 6, 4, 3, 2.5, 2.0, 1.5][min(it, 6)]
        s = 1.4826 * np.median(np.abs(res[np.abs(res) < thr])) if (np.abs(res) < thr).any() else thr
        w = Wt * (np.abs(res) < thr)
    tilt = math.degrees(math.acos(up[2])); toward = math.degrees(math.atan2(up[0], up[1])) % 360
    # spread of the inlier segments in azimuth (column -> deg)
    az = (A[w > 0] * 360 / 4096) % 360
    hist = np.histogram(az, bins=12, range=(0, 360))[0]
    print(f'{pano} segs {len(N)} inliers {int((w>0).sum())} res-sd {s:.3f} deg  tilt {tilt:.2f} deg toward col-az {toward:.1f}  az-bins {hist.tolist()}')
    UP[str(pano)] = up.tolist()
json.dump(UP, open(f'{D}/up.json', 'w'), indent=1)
