# camera of one school-site photo (reference/학교홈페이지/, 자료 R) from its control points in r96/<name>.json
#   uv run --with numpy --with scipy --with shapely --with pillow --with DracoPy python tools/photofit/r96fit.py <name> [--save]
# points are game 3D (해발) <-> photo pixels; the 3D side is a footprint corner (campus.json), a statue / prop position or
# a ray cast into the running game at the same feature. Besides fit.py's point / vedge / line: "circles" (a round kerb:
# centre, radius, level), "eye" (a standing photographer: camera 1.6 m over the ground, sigma in m). Prints the camera, the residual table, the 1-sigma of the position from the fit and the
# leave-one-out spread (and with "along": [lo, hi] the span on the line of sight where the rms stays within 10 %);
# --save writes them back into the json under "result" (with the snapshot-style camera "cam").
import json, math, os, sys
import numpy as np
from scipy.optimize import least_squares
import fit, scene

HERE = os.path.dirname(os.path.abspath(__file__))
# f: film lenses 24 mm and longer on a 36 mm frame (f >= 0.66 x photo width); set "f_lo" in the spec to change
LO = np.array([-1e4, -1e4, 0, -720, -60, -20, 80])
HI = np.array([1e4, 1e4, 400, 720, 60, 20, 6000])
SCALE = np.array([5, 5, 2, 1, 1, 0.5, 30])


def eye_z(ph, p):
    """standing photographer: eye 1.6 m over the ground under the camera (spec "eye": [dz, sigma_m], or "eye_z")"""
    if 'eye_z' in ph.spec:
        return ph.spec['eye_z']
    return float(scene.terrain(p[0], p[1])[0]) + ph.spec.get('eye', [1.6, 0.5])[0]


def circle_err(ph, p, c):
    """pixel distance from a photo point to the projected circle (centre C, radius r, level z): round kerbs"""
    t = np.linspace(0, 2 * math.pi, 721)
    X = np.stack([c['C'][0] + c['r'] * np.sin(t), c['C'][1] + c['r'] * np.cos(t), np.full_like(t, c['C'][2])], -1)
    C0, d = np.array(p[:3]), None
    import cam
    _, dvec, _, _, _ = cam.basis(p)
    X = X[(X - C0) @ dvec > 1.0]
    if not len(X):
        return 50.0
    q = cam.project(p, X, ph.W, ph.H)
    return float(np.min(np.hypot(*(q - np.array(c['px'])).T)))


def resid(ph, v, idx):
    r = ph.res(v, idx)
    if ph.spec.get('circles'):
        p = ph.full(v)
        r = np.append(r, [circle_err(ph, p, c) * c.get('w', 1.0) for c in ph.spec['circles']])
    if ph.spec.get('eye') or 'eye_z' in ph.spec:
        p = ph.full(v)
        sig = ph.spec.get('eye', [1.6, 0.5])[1]
        r = np.append(r, (p[2] - eye_z(ph, p)) / sig)
    return r


def solve(ph, idx=None, p0=None, starts=6):
    free = [i for i in range(7) if str(i) not in ph.fix]
    base = np.array(ph.spec['p0'] if p0 is None else p0, float)
    LO[6] = ph.spec.get('f_lo', 0.66 * ph.W)
    best = None
    rng = np.random.default_rng(1)
    for k in range(starts):
        q = base.copy()
        if k:
            q = q + rng.normal(0, 1, 7) * np.array([6, 6, 1.5, 4, 2, 0.5, 60])
        q0 = np.clip(q[free], LO[free] + 1e-6, HI[free] - 1e-6)
        try:
            r = least_squares(lambda v: resid(ph, v, idx), q0, x_scale=SCALE[free], bounds=(LO[free], HI[free]))
        except Exception:
            continue
        if best is None or r.cost < best.cost:
            best = r
    p = ph.full(best.x)
    nz = np.count_nonzero(np.abs(best.fun) > 0)
    dof = max(1, nz - len(free))
    s2 = float(best.fun @ best.fun) / dof
    try:
        cov = np.linalg.inv(best.jac.T @ best.jac) * s2
    except np.linalg.LinAlgError:
        cov = np.full((len(free), len(free)), np.nan)
    C = np.zeros((7, 7))
    C[np.ix_(free, free)] = cov
    return p, C, math.sqrt(s2)


def along(ph, p, lo, hi, step=1.0):
    """the fit with the camera held at points on its horizontal line of sight (m, + = forward) between lo and hi:
    the span where the rms stays within 10 % of the best. For photos whose points sit on one face (distance and focal
    length trade off), with the range cut to where the photo's view is not blocked (spec "along": [lo, hi], reason in
    its "what")"""
    a = math.radians(p[3])
    d = np.array([math.sin(a), math.cos(a)])
    fix0 = dict(ph.fix)
    prof = []
    for k in np.arange(lo, hi + 1e-9, step):
        ph.fix = dict(fix0, **{'0': float(p[0] + d[0] * k), '1': float(p[1] + d[1] * k)})
        q0 = np.array(p, float)
        q0[:2] = [ph.fix['0'], ph.fix['1']]
        _, _, s = solve(ph, p0=q0, starts=1)
        prof.append((float(k), s))
    ph.fix = fix0
    best = min(s for _, s in prof)
    ok = [k for k, s in prof if s <= best * 1.1]
    return prof, (min(ok), max(ok))


def snapcam(p, W, H):
    """snapshots.json-style camera: position, a target 30 m ahead, vertical fov"""
    C = np.array(p[:3])
    yaw, pit = math.radians(p[3]), math.radians(p[4])
    d = np.array([math.sin(yaw) * math.cos(pit), math.cos(yaw) * math.cos(pit), math.sin(pit)])
    T = C + 30 * d
    fov = 2 * math.degrees(math.atan(H / 2 / p[6]))
    r = lambda v: round(float(v), 2)
    return dict(x=r(C[0]), y=r(C[1]), h=r(C[2]), tx=r(T[0]), ty=r(T[1]), th=r(T[2]), fov=r(fov), roll=r(p[5]))


def main():
    name = sys.argv[1]
    path = os.path.join(HERE, 'r96', name + '.json')
    spec = json.load(open(path))
    ph = fit.Photo(spec)
    p, C, s = solve(ph)
    sig = np.sqrt(np.maximum(np.diag(C), 0))
    print(spec['photo'], '  %d points' % len(ph.pts))
    print('camera', fit.pstr(p), '  rms %.2f px' % s)
    print('1-sigma x %.2f y %.2f z %.2f m, yaw %.2f pitch %.2f roll %.2f deg, f %.0f px' % tuple(sig))
    ph.table(p)
    loo = []
    for i in range(len(ph.pts)):
        idx = [j for j in range(len(ph.pts)) if j != i]
        q, _, _ = solve(ph, idx=idx, p0=p, starts=2)
        loo.append(q[:3] - p[:3])
        print('  without %-28s  shift (%+.2f, %+.2f, %+.2f) m' % (ph.pts[i]['n'], *loo[-1]))
    loo = np.array(loo)
    lmax = float(np.max(np.hypot(loo[:, 0], loo[:, 1])))
    # jackknife standard error of the horizontal position
    n = len(loo)
    jk = math.sqrt((n - 1) / n * float(np.sum((loo[:, :2] - loo[:, :2].mean(0)) ** 2)))
    unc = max(lmax, 2 * math.hypot(sig[0], sig[1]), 2 * jk)
    span = None
    if 'along' in spec:
        _, span = along(ph, p, *spec['along'])
        unc = max(unc, -span[0], span[1])
        print('along the line of sight (rms within 10 %%): %+.0f ~ %+.0f m' % span)
    print('leave-one-out: max horizontal shift %.2f m, jackknife s.e. %.2f m  -> uncertainty ~%.1f m' % (lmax, jk, unc))
    if '--save' in sys.argv:
        W, H = spec['size']
        spec['result'] = dict(p=[round(float(v), 3) for v in p], rms_px=round(s, 2),
                              sigma=[round(float(v), 3) for v in sig], loo_max_m=round(lmax, 2), jackknife_m=round(jk, 2),
                              uncertainty_m=round(unc, 1), cam=snapcam(p, W, H))
        if span is not None:
            spec['result']['along_m'] = [round(span[0], 1), round(span[1], 1)]
        txt = json.dumps(spec, ensure_ascii=False, indent=1)
        open(path, 'w').write(txt + '\n')
        print('saved', path)


if __name__ == '__main__':
    main()
