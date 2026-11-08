# least-squares camera fit to control features (game 3D <-> photo pixels), residual table, split-half cross-validation
#   point:  {"n", "ref"|"X", "px", "w": [wx, wy]}                      pixel = projection of a 3D point
#   vedge:  {"n", "type": "vedge", "ref": "b:<id>:<k>", "px", "w"}     pixel lies on the projected vertical through a
#           footprint corner (insensitive to the building's height)
#   line:   {"n", "type": "line", "A", "B", "px", "w"}                  pixel lies on the projected 3D segment A-B
import json, math, sys
import numpy as np
from scipy.optimize import least_squares
import scene, cam

DZ_S = [(0, 10.0), (292, 8.3), (420, 7.5), (550, 2.4), (591, -0.1), (615, 0.7)]     # game − Copernicus along 백양로 (고증 2.8)


def dz_terrain(x, y):
    """how much the game ground stands over Copernicus GLO-30 near (x, y), by its 백양로 s (rough, for sensitivity)"""
    s, off = scene.s_off(x, y)
    return float(np.interp(s, [a for a, _ in DZ_S], [b for _, b in DZ_S]))


def resolve_ref(ref):
    parts = ref.split(':')
    bid, k = int(parts[1]), int(parts[2])
    fp, top, base = scene.corners(bid)
    lvl = parts[3] if len(parts) > 3 else 'top'
    z = {'top': top[k], 'base': base[k]}.get(lvl)
    if z is None:
        z = float(lvl)
    return np.array([fp[k][0], fp[k][1], z]), top[k], base[k]


def resolve(pt, lower=False):
    """3D anchor(s) of a feature: (A, B) — B is None for points"""
    t = pt.get('type', 'point')
    if t == 'width':
        return np.zeros(3), np.zeros(3)
    if t == 'vedge' and 'X' in pt:
        x, y, z0, z1 = pt['X']
        A, B = np.array([x, y, z0], float), np.array([x, y, z1], float)
    elif t == 'vedge':
        X, top, base = resolve_ref(pt['ref'])
        A = np.array([X[0], X[1], base])
        B = np.array([X[0], X[1], (top if np.isfinite(top) else base + 10)])
    elif t == 'line':
        A = np.array(pt['A'], float) if not isinstance(pt['A'], str) else resolve_ref(pt['A'])[0]
        B = np.array(pt['B'], float) if not isinstance(pt['B'], str) else resolve_ref(pt['B'])[0]
    else:
        A = np.array(pt['X'], float) if 'X' in pt else resolve_ref(pt['ref'])[0]
        B = None
    d = np.array(pt.get('dX', [0, 0, 0]), float)
    A = A + d
    B = None if B is None else B + d
    if lower:
        A = A.copy()
        A[2] -= dz_terrain(A[0], A[1])
        if B is not None:
            B = B.copy()
            B[2] -= dz_terrain(B[0], B[1])
    return A, B


class Photo:
    def __init__(self, spec, lower=False, only=None):
        self.spec = spec
        self.W, self.H = spec['size']
        self.offR = np.array(spec.get('offR', [0, 0]), float)
        self.seam = spec.get('seam')
        self.pts = [p for p in spec['pts'] if not p.get('off') and (only is None or p.get('g', 'ctl') in only)]
        self.lower = lower
        self.AB = [resolve(p, lower) for p in self.pts]
        self.U = np.array([self.orig(p['px']) for p in self.pts], float)
        self.Wt = np.array([p.get('w', [1, 1]) for p in self.pts], float)
        self.fix = spec.get('fix', {})

    def orig(self, px):
        px = np.array(px, float)
        if self.seam is not None and px[0] >= self.seam:
            px = px - self.offR
        return px

    def full(self, q):
        p = np.array(self.spec['p0'], float)
        free = [i for i in range(7) if str(i) not in self.fix]
        p[free] = q
        for k, v in self.fix.items():
            p[int(k)] = v
        return p

    def width_err(self, p, pt):
        """apparent width of a road cross-section element (two pixels on one row) against its known width in m"""
        yrow = pt['y']
        xl, xr = pt['px']
        if self.seam is not None:
            xl = xl - self.offR[0] if xl >= self.seam else xl
            xr = xr - self.offR[0] if xr >= self.seam else xr
        def row(s):
            c = scene.center(s)
            return cam.project(p, [c[0], c[1], scene.road_h(s)], self.W, self.H)[0][1] - yrow
        lo, hi = 0.0, 600.0
        flo, fhi = row(lo), row(hi)
        if flo * fhi > 0:
            return np.array([0.0, 0.0])
        for _ in range(40):
            m = (lo + hi) / 2
            fm = row(m)
            if fm * flo > 0:
                lo, flo = m, fm
            else:
                hi = m
        s = (lo + hi) / 2
        h = scene.road_h(s)
        a = scene.along(s, -pt['w0'] / 2)
        b = scene.along(s, pt['w0'] / 2)
        qa, qb = cam.project(p, [[a[0], a[1], h], [b[0], b[1], h]], self.W, self.H)
        return np.array([(qb[0] - qa[0]) - (xr - xl), 0.0])

    def err(self, p, i):
        """image error vector of feature i (px): for points (dx, dy); for edges/lines (perpendicular distance, 0)"""
        if self.pts[i].get('type') == 'width':
            return self.width_err(p, self.pts[i])
        A, B = self.AB[i]
        u = self.U[i]
        if B is None:
            return cam.project(p, A, self.W, self.H)[0] - u
        a, b = cam.project(p, np.stack([A, B]), self.W, self.H)
        t = b - a
        n = np.array([t[1], -t[0]]) / (np.hypot(*t) + 1e-12)
        return np.array([np.dot(a - u, n), 0.0])

    def res(self, q, idx=None):
        p = self.full(q)
        idx = range(len(self.pts)) if idx is None else idx
        return np.concatenate([self.err(p, i) * self.Wt[i] for i in idx])

    def fit(self, idx=None, p0=None):
        p0 = np.array(self.spec['p0'] if p0 is None else p0, float)
        free = [i for i in range(7) if str(i) not in self.fix]
        scale = np.array([20, 20, 10, 0.2, 0.2, 0.2, 50])[free]
        lo = np.array([-1e5, -1e5, 40, -400, -89, -45, 300])[free]
        hi = np.array([1e5, 1e5, 5000, 400, 10, 45, 1e5])[free]
        q0 = np.clip(p0[free], lo + 1e-6, hi - 1e-6)
        r = least_squares(lambda q: self.res(q, idx), q0, x_scale=scale, loss=self.spec.get('loss', 'linear'),
                          f_scale=self.spec.get('f_scale', 5.0), bounds=(lo, hi))
        p = self.full(r.x)
        J = r.jac
        nz = np.count_nonzero(np.abs(r.fun) > 0)
        dof = max(1, nz - len(free))
        s2 = float(r.fun @ r.fun) / dof
        try:
            cov = np.linalg.inv(J.T @ J) * s2
        except np.linalg.LinAlgError:
            cov = np.full((len(free), len(free)), np.nan)
        C = np.zeros((7, 7))
        C[np.ix_(free, free)] = cov
        return p, C, math.sqrt(s2)

    def ground_res(self, p, i):
        """image error of feature i and the same as a shift on its horizontal plane (m): (east, north) for points;
        for edges/lines the horizontal shift perpendicular to the line of sight"""
        e = self.err(p, i)
        if self.pts[i].get('type') == 'width':
            return e, np.array([np.nan, np.nan])
        A, B = self.AB[i]
        X = A if B is None else (A + B) / 2
        q = cam.project(p, X, self.W, self.H)[0]
        J = np.zeros((2, 2))
        for k in range(2):
            dX = np.zeros(3)
            dX[k] = 0.1
            J[:, k] = (cam.project(p, X + dX, self.W, self.H)[0] - q) / 0.1
        if B is None:
            try:
                return e, np.linalg.solve(J, -e)
            except np.linalg.LinAlgError:
                return e, np.array([np.nan, np.nan])
        # metres per px across the image at that depth
        mpp = 1.0 / np.hypot(*J[0])
        return e, np.array([-e[0] * mpp, np.nan])

    def table(self, p, file=sys.stdout):
        print('| 기준점 | 종류 | 사진 (px) | 잔차 (px) | 땅에서 (m) |', file=file)
        print('|---|---|---|---|---|', file=file)
        for i, pt in enumerate(self.pts):
            e, dm = self.ground_res(p, i)
            t = pt.get('type', 'point')
            if t == 'point':
                es, ds = '%+.1f, %+.1f' % tuple(e), '동 %+.1f, 북 %+.1f' % tuple(dm)
            else:
                es, ds = '%+.1f' % e[0], '가로 %+.1f' % dm[0]
            if t == 'width':
                ds = '—'
            print('| %s | %s | %d, %d | %s | %s |' % (pt['n'], {'point': '점', 'vedge': '세로 모서리', 'line': '선',
                                                               'width': '폭(px)'}[t], *pt['px'], es, ds), file=file)


def pstr(p):
    return '(%.1f, %.1f, %.1f) yaw %.2f° pitch %.2f° roll %.2f° f %.0f px' % tuple(p)


def splits(n, k=40, seed=1):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(k):
        perm = rng.permutation(n)
        out.append((np.sort(perm[:n // 2]), np.sort(perm[n // 2:])))
    return out
