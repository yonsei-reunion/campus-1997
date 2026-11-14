"""The cars on Seoul streets in 1997, modelled procedurally in Blender.

Each body is *lofted*: cross-sections (rounded rectangles with tumblehome) are sampled every few centimetres along
the car and joined into one smooth quad skin, so the wheel arches, hood line, plan-view rounding and greenhouse all
come out as continuous surfaces.  Window glass, black rubber/pillars and paint are assigned per face from the
window outlines of each model.  Bumpers are lofted too, so they wrap round the corners; lamps are strips laid on
the body surface, so flush wrap-around lamps follow the plan-view rounding.  Details: grilles of the period,
rub strips, door seams and handles, mirrors, wipers, antenna, pre-2004 Korean two-line licence plates, a simple
interior seen through tinted glass, and four separate wheels (tyre with shoulders + full wheel cover or steel rim)
whose origins sit on the axle so the game can spin them.

The proportions are the real cars' (overall length x width x height, wheelbase, overhangs and tyre sizes of each
maker's figures; the belt line and the glass by photographs of the cars side on): the body side from the sill to the
belt is about 0.73 m of a 1.4 m saloon and the side glass 0.37 m, the roof 0.1 m over it.  The window outlines are
cut into the lofted skin (split_poly), so the pillars lean with the windscreen and the rear window, and the glass
keeps a margin of body below the roof and over the belt.

Models (car-local frame: +X forward, +Y left, +Z up, ground at z=0), each in the manner of (not a copy of) a car
that filled 1997 Seoul:
  sedan   — rounded mid-size saloon of 1993-97 (쏘나타Ⅱ type): body-coloured wrap-around bumpers with a rub band,
            slim flush headlamps wrapping into amber corners, a low narrow grille, a full-width tail-lamp band
  sedan2  — square older mid-size saloon (프린스 type): upright chrome grille with vertical bars between
            rectangular lamps, chrome window surrounds and bumper strips, grey bumpers
  hatch   — boxy 5-door compact (프라이드 type): near-vertical tailgate, black bumpers, steel wheels
  tico    — the tiny 800 cc car (티코 type): short round nose, tall glasshouse, 12-inch wheels
  taxi    — the sedan with a roof sign "개인" and yellow commercial plates
  van     — one-box passenger van (그레이스 type)
"""
import math
from mathutils import Vector, Matrix
from common import MeshBuilder


def interp(pts, x):
    """piecewise-linear interpolation over [(x, y), ...] sorted by x descending or ascending."""
    p = sorted(pts)
    if x <= p[0][0]:
        return p[0][1]
    if x >= p[-1][0]:
        return p[-1][1]
    for (x0, y0), (x1, y1) in zip(p[:-1], p[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            t = t * t * (3 - 2 * t) * 0.5 + t * 0.5          # gentle easing between control points
            return y0 + (y1 - y0) * t
    return p[-1][1]


def interp_round(pts, x, r=0.07):
    """straight between the control points [(x, y), ...], their corners rounded over r either side (less between
    points close together): a screen's line stays straight from the scuttle to the roof, where interp's easing made
    it wave"""
    p = sorted(pts)

    def lin(u):
        if u <= p[0][0]:
            return p[0][1]
        if u >= p[-1][0]:
            return p[-1][1]
        for (x0, y0), (x1, y1) in zip(p[:-1], p[1:]):
            if x0 <= u <= x1:
                return y0 + (y1 - y0) * (u - x0) / (x1 - x0)
    for (xa, _), (xi, yi), (xb, _) in zip(p[:-2], p[1:-1], p[2:]):
        ri = min(r, 0.45 * (xi - xa), 0.45 * (xb - xi))
        if abs(x - xi) < ri:
            t = (x - (xi - ri)) / (2 * ri)
            return (1 - t) ** 2 * lin(xi - ri) + 2 * t * (1 - t) * yi + t * t * lin(xi + ri)
    return lin(x)


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def sec_radii(half_w, zb, zt, rb, rt):
    h = max(0.004, zt - zb)
    return min(rb, h * 0.35, half_w * 0.4), min(rt, h * 0.45, half_w * 0.4)


def section(half_w, zb, zt, rb, rt, tumble=0.0, crown=0.0, n_arc=4, n_top=6, zsplits=(), bow=0.0, n_fl=0):
    """Closed cross-section (y, z) around the car axis, counter-clockwise seen from +X.
    zsplits: extra points on the flank (so a rub band can get its own faces).
    bow, n_fl: the flank bowed out by `bow` at its middle, drawn through n_fl points (a pressed panel, not a slab)."""
    rb, rt = sec_radii(half_w, zb, zt, rb, rt)
    wt = half_w - tumble
    right = []                                    # y >= 0 half from bottom centre to top centre
    right.append((0.0, zb))
    for i in range(n_arc + 1):                    # bottom corner
        a = -math.pi / 2 + (math.pi / 2) * i / n_arc
        right.append((half_w - rb + rb * math.cos(a), zb + rb + rb * math.sin(a)))
    z0, z1 = zb + rb, zt - rt
    for z in sorted(zsplits):                     # flank, from the bottom corner up to the top corner (clamped,
        z = min(max(z, z0 + 0.002), z1 - 0.002)   # so every section of a loft has the same point count)
        right.append((half_w + (wt - half_w) * (z - z0) / max(1e-4, z1 - z0), z))
    for k in range(1, n_fl + 1):
        t = k / (n_fl + 1)
        right.append((half_w + (wt - half_w) * t + bow * 4 * t * (1 - t), z0 + (z1 - z0) * t))
    for i in range(n_arc + 1):                    # top corner
        a = (math.pi / 2) * i / n_arc
        right.append((wt - rt + rt * math.cos(a), zt - rt + rt * math.sin(a)))
    for i in range(1, n_top + 1):                 # roof / hood crown
        y = (wt - rt) * (1 - i / n_top)
        right.append((y, zt + crown * (1 - (y / max(1e-3, wt)) ** 2)))
    left = [(-y, z) for (y, z) in reversed(right[1:-1])]
    return right + left


def section_y(half_w, zb, zt, rb, rt, tumble, z, bow=0.0):
    """half-width of section() at height z (ignoring the crown); -1 outside the section."""
    if z <= zb or z >= zt:
        return -1.0
    rb, rt = sec_radii(half_w, zb, zt, rb, rt)
    wt = half_w - tumble
    if z < zb + rb:
        return half_w - rb + math.sqrt(max(0.0, rb * rb - (zb + rb - z) ** 2))
    if z > zt - rt:
        return wt - rt + math.sqrt(max(0.0, rt * rt - (z - zt + rt) ** 2))
    t = (z - zb - rb) / max(1e-4, zt - rt - zb - rb)
    return half_w + (wt - half_w) * t + bow * 4 * t * (1 - t)


def split_poly(pts, f):
    """a convex polygon cut by the scalar field f (taken as linear along its edges): the part where f >= 0 and the
    part where f < 0 (None where there is none)"""
    vals = [f(p) for p in pts]
    if min(vals) >= -1e-6:
        return pts, None
    if max(vals) <= 1e-6:
        return None, pts
    pos, neg = [], []
    n = len(pts)
    for i in range(n):
        a, b, fa, fb = pts[i], pts[(i + 1) % n], vals[i], vals[(i + 1) % n]
        (pos if fa >= 0 else neg).append(a)
        if (fa >= 0) != (fb >= 0):
            m = a + (b - a) * (fa / (fa - fb))
            pos.append(m)
            neg.append(m)
    return (pos if len(pos) >= 3 else None), (neg if len(neg) >= 3 else None)


def loft(mb, xs, sec_fn, mat_fn, tag, cap_front=True, cap_back=True, cap_mat=None, split_fn=None):
    """split_fn(q, c, nrm) -> [(points, material)]: a face cut into parts (the window outlines)"""
    secs = [[Vector((x, y, z)) for (y, z) in sec_fn(x)] for x in xs]
    n = len(secs[0])
    for i in range(len(xs) - 1):
        A, B = secs[i], secs[i + 1]
        axis = Vector((0, 0, (min(p.z for p in A) + max(p.z for p in A)) / 2))
        for k in range(n):
            k2 = (k + 1) % n
            q = [A[k], A[k2], B[k2], B[k]]
            c = sum(q, Vector()) / 4
            nrm = (q[1] - q[0]).cross(q[3] - q[0])
            if nrm.length < 1e-10:
                nrm = (q[2] - q[1]).cross(q[3] - q[1])
            if nrm.length < 1e-10:
                continue
            nrm.normalize()
            out = Vector((0, c.y, c.z - axis.z))
            if nrm.dot(out) < 0:
                q = q[::-1]
                nrm = -nrm
            if split_fn:
                for pts, mat in split_fn(q, c, nrm):
                    mb.face([tuple(v) for v in pts], mat, smooth=tag)
            else:
                mb.face([tuple(v) for v in q], mat_fn(c, nrm), smooth=tag)
    for S, sgn, do in ((secs[0], -1, cap_back), (secs[-1], 1, cap_front)):
        if not do:
            continue
        cen = sum(S, Vector()) / len(S)
        for k in range(n):
            tri = [cen, S[k], S[(k + 1) % n]]
            nrm = (tri[1] - tri[0]).cross(tri[2] - tri[0])
            if nrm.x * sgn < 0:
                tri = tri[::-1]
            mb.face([tuple(v) for v in tri], cap_mat or mat_fn(cen, Vector((sgn, 0, 0))), smooth=tag + 'cap')


def stations(x0, x1, step, extra=()):
    xs = set()
    x = x0
    while x < x1:
        xs.add(round(x, 4))
        x += step
    xs.add(round(x1, 4))
    for e in extra:
        if x0 < e < x1:
            xs.add(round(e, 4))
    return sorted(xs)


# ----------------------------------------------------------------------------- specs
# L is the body's length without the bumpers, which stand 0.06 m (body-coloured) or 0.07 m proud at either end: the
# cars' overall lengths are the makers' (쏘나타Ⅱ 4.70 m, 프린스 4.80, 프라이드 3.57, 티코 3.34, 그레이스 4.70), as
# are their widths, heights (the highest point of `roof`), wheelbases (`axles`) and tyres.
# top: the body's upper line (hood, belt, boot lid); roof: the greenhouse's, from the boot lid over the roof down to
# the scuttle; gh: where the greenhouse stands.  windshield / rear_window / side: the glass along x; the side glass
# runs from 4 cm over the belt up to 4 cm under the roof's rounding along the screens (the pillars lean with them)
# and no higher than `cant` under it on the roof (the cant rail; a van's deep roof panel).  rw_z: a tailgate's glass.
# style keys: bumper 'body' | 'grey' | 'black'; lamps 'flush' | 'box'; grille 'slot' | 'chrome' | 'slit';
# tail 'band' | 'blocks' | 'vertical'; trim (window surrounds, rub strips, handles) 'black' | 'chrome';
# wheel 'cover' | 'steel'; plan = (inset, length) of the plan-view corner rounding; body_r = flank corner radii
SPECS = {
    'sedan': dict(
        L=4.58, W=1.77, axles=(1.42, -1.28), tyre=0.314, arch=0.37, sill=0.185, bumper_z=(0.23, 0.52),
        top=[(-2.29, 0.81), (-2.20, 0.925), (-1.50, 0.93), (0.95, 0.89), (1.60, 0.83), (2.15, 0.745), (2.29, 0.69)],
        roof=[(-1.60, 0.93), (-1.28, 1.18), (-0.98, 1.37), (-0.30, 1.405), (0.14, 1.375), (0.60, 1.135), (1.03, 0.885)],
        gh=(-1.60, 1.03), roof_w=0.60, belt_w=0.815, gh_rt=0.06, cant=0.045,
        windshield=(0.17, 1.00), rear_window=(-1.56, -1.01), side=(-1.21, 0.86), pillars=[(-0.20, -0.10)],
        doors=[0.90, -0.15, -1.17], lamp_h=(0.56, 0.65), tail_h=(0.63, 0.76), grille_w=0.25, plate_rear_z=0.655,
        plan=(0.13, 0.48), body_r=(0.08, 0.10), bumper='body', lamps='flush', grille='slot', tail='band',
        trim='black', wheel='cover', rub_z=0.43, mirror='car_paint'),
    'sedan2': dict(
        L=4.66, W=1.72, axles=(1.45, -1.22), tyre=0.31, arch=0.365, sill=0.19, bumper_z=(0.25, 0.48),
        top=[(-2.33, 0.86), (-2.26, 0.93), (-1.42, 0.925), (0.86, 0.90), (1.60, 0.87), (2.24, 0.83), (2.33, 0.775)],
        roof=[(-1.46, 0.925), (-1.24, 1.19), (-1.04, 1.39), (-0.25, 1.42), (0.16, 1.395), (0.52, 1.17), (0.90, 0.90)],
        gh=(-1.46, 0.90), roof_w=0.62, belt_w=0.795, gh_rt=0.05, cant=0.05,
        windshield=(0.19, 0.87), rear_window=(-1.43, -1.08), side=(-1.13, 0.74), pillars=[(-0.20, -0.10)],
        doors=[0.78, -0.15, -1.12], lamp_h=(0.60, 0.72), tail_h=(0.66, 0.81), grille_w=0.30, plate_rear_z=0.66,
        plan=(0.07, 0.28), body_r=(0.06, 0.045), bumper='grey', lamps='box', grille='chrome', tail='blocks',
        trim='chrome', wheel='cover', rub_z=0.42, mirror='trim_black'),
    'hatch': dict(
        L=3.43, W=1.605, axles=(1.08, -1.215), tyre=0.272, arch=0.33, sill=0.185, bumper_z=(0.24, 0.45),
        top=[(-1.715, 0.86), (-1.67, 0.915), (0.62, 0.885), (1.20, 0.815), (1.64, 0.76), (1.715, 0.70)],
        roof=[(-1.70, 0.915), (-1.685, 1.22), (-1.62, 1.43), (-0.30, 1.46), (0.05, 1.44), (0.36, 1.16), (0.64, 0.885)],
        gh=(-1.70, 0.66), roof_w=0.61, belt_w=0.745, gh_rt=0.05, cant=0.075, rw_z=(1.00, 1.345),
        windshield=(0.10, 0.64), rear_window=(-1.71, -1.57), side=(-1.50, 0.52), pillars=[(-0.42, -0.33), (-1.13, -1.07)],
        doors=[0.58, -0.38, -1.10], lamp_h=(0.56, 0.675), tail_h=(0.56, 0.86), grille_w=0.24, plate_rear_z=0.60,
        plan=(0.07, 0.26), body_r=(0.06, 0.05), bumper='black', lamps='box', grille='slit', tail='vertical',
        trim='black', wheel='steel', rub_z=0.41, mirror='trim_black', hatch=True),
    'tico': dict(
        L=3.20, W=1.40, axles=(1.11, -1.225), tyre=0.26, arch=0.31, sill=0.18, bumper_z=(0.22, 0.43),
        top=[(-1.60, 0.82), (-1.555, 0.885), (0.52, 0.86), (1.00, 0.81), (1.48, 0.73), (1.60, 0.67)],
        roof=[(-1.585, 0.885), (-1.57, 1.19), (-1.50, 1.37), (-0.35, 1.395), (0.00, 1.375), (0.30, 1.12), (0.57, 0.86)],
        gh=(-1.585, 0.60), roof_w=0.53, belt_w=0.645, gh_rt=0.06, cant=0.05, rw_z=(0.98, 1.29),
        windshield=(0.05, 0.57), rear_window=(-1.60, -1.46), side=(-1.40, 0.48), pillars=[(-0.45, -0.37), (-1.06, -1.00)],
        doors=[0.53, -0.41, -1.03], lamp_h=(0.52, 0.615), tail_h=(0.55, 0.82), grille_w=0.17, plate_rear_z=0.58,
        plan=(0.14, 0.46), body_r=(0.07, 0.09), bumper='black', lamps='box', grille='slit', tail='vertical',
        trim='black', wheel='steel', rub_z=0.39, mirror='trim_black', hatch=True),
    'van': dict(
        L=4.56, W=1.69, axles=(1.13, -1.305), tyre=0.325, arch=0.39, sill=0.25, bumper_z=(0.30, 0.52),
        top=[(-2.28, 1.04), (-2.23, 1.10), (1.70, 1.10), (1.98, 1.06), (2.20, 0.94), (2.28, 0.85)],
        roof=[(-2.27, 1.10), (-2.25, 1.74), (-2.18, 1.94), (0.60, 1.97), (1.10, 1.94), (1.36, 1.87), (1.68, 1.45), (1.93, 1.10)],
        gh=(-2.27, 1.93), roof_w=0.70, belt_w=0.80, gh_rt=0.08, cant=0.17, rw_z=(1.17, 1.72),
        windshield=(1.39, 1.90), rear_window=(-2.40, -2.20), side=(-2.02, 1.64), pillars=[(0.50, 0.60), (-0.74, -0.64)],
        doors=[1.70, 0.55, -0.69], lamp_h=(0.67, 0.78), tail_h=(0.60, 0.92), grille_w=0.38, plate_rear_z=0.74,
        plan=(0.09, 0.32), body_r=(0.07, 0.06), bumper='grey', lamps='box', grille='slot', tail='vertical',
        trim='black', wheel='steel', rub_z=0.50, mirror='trim_black', van=True),
}
SPECS['taxi'] = dict(SPECS['sedan'], taxi=True)

# The cars are exported at their real sizes (till 2026-11 seven per cent larger, for a driver sitting bolt upright:
# web/src/life.js now sits the driver low and leaning back, as in a car)
CAR_SCALE = 1.0


# where the seated driver goes (car frame: x forward, y left), for web/src/life.js DRIVER
def driver_seat(kind):
    sp = SPECS[kind]
    x = 1.00 if sp.get('van') else sp['pillars'][0][0] + 0.15
    return round(x, 2), (0.36 if sp['W'] > 1.5 else 0.31)


def build_car(kind):
    sp = SPECS[kind]
    L, W = sp['L'], sp['W']
    hw = W / 2
    fa, ra = sp['axles']
    r_arch, tyre = sp['arch'], sp['tyre']
    cy_arch = tyre + 0.01
    p_in, p_len = sp['plan']
    brb, brt = sp['body_r']
    TUMBLE, BOW = 0.03, 0.014
    chrome_trim = sp['trim'] == 'chrome'
    trim_mat = 'chrome' if chrome_trim else 'trim_black'
    mb = MeshBuilder('car_' + kind)
    mb.xf = Matrix.Scale(CAR_SCALE, 4)

    def z_bot(x):
        z = sp['sill']
        z += (sp['bumper_z'][0] - sp['sill'] + 0.02) * smoothstep(L / 2 - 0.45, L / 2 - 0.15, abs(x))
        for ax in (fa, ra):
            d = abs(x - ax)
            if d < r_arch:
                z = max(z, cy_arch + math.sqrt(r_arch * r_arch - d * d) * 0.98)
        return z

    def z_top(x):
        return interp(sp['top'], x)

    def half_w(x):
        return hw - p_in * smoothstep(L / 2 - p_len, L / 2, abs(x)) ** 1.6

    def body_y(x, z):
        return section_y(half_w(x), z_bot(x), z_top(x), brb, brt, TUMBLE, z, BOW)

    def surf_x(sx, y, z):
        """|x| of the body surface at (y, z) on the front (sx=1) or back (sx=-1)."""
        hi, lo = L / 2, L / 2 - p_len - 0.1
        if body_y(sx * hi, z) >= y:
            return hi
        if body_y(sx * lo, z) < y:
            return lo
        for _ in range(28):
            m = (hi + lo) / 2
            if body_y(sx * m, z) >= y:
                lo = m
            else:
                hi = m
        return (hi + lo) / 2

    def surf_pt(sx, y, z, off):
        e = 0.004
        u0, u1 = surf_x(sx, y - e, z), surf_x(sx, y + e, z)
        t = Vector((sx * (u1 - u0), 2 * e))
        n = Vector((sx * t.y, -sx * t.x)).normalized()
        u = surf_x(sx, y, z)
        return (sx * u + n.x * off, y + n.y * off, z)

    def strip(sx, y0, y1, z0, z1, mat, off=0.004, n=None, sides=(-1, 1)):
        """a lamp/trim strip on the body surface between y0 < y1 (y >= 0), mirrored to both sides."""
        n = n or max(1, int(math.ceil((y1 - y0) / 0.04)))
        ys = [y0 + (y1 - y0) * i / n for i in range(n + 1)]
        for s in sides:
            for ya, yb in zip(ys[:-1], ys[1:]):
                q = [surf_pt(sx, ya, z0, off), surf_pt(sx, yb, z0, off), surf_pt(sx, yb, z1, off), surf_pt(sx, ya, z1, off)]
                q = [(x, s * y, z) for x, y, z in q]
                mb.face(q if s * sx > 0 else q[::-1], mat)

    def wrap_end(sx, z):
        """the y at which a wrap-around lamp ends, a little before the flank."""
        return min(body_y(sx * (L / 2 - p_len * 0.85), z), half_w(sx * (L / 2 - p_len * 0.85))) - 0.012

    # ---------------- lower body
    xs = stations(-L / 2, L / 2, 0.04, extra=[fa - r_arch, fa + r_arch, ra - r_arch, ra + r_arch])

    def body_sec(x):
        return section(half_w(x), z_bot(x), z_top(x), brb, brt, tumble=TUMBLE, crown=0.012, bow=BOW, n_fl=3)
    loft(mb, xs, body_sec, lambda c, n: 'car_paint', 'body')

    # ---------------- greenhouse
    x0, x1 = sp['gh']
    extra = [x0 + 0.006 * i for i in range(1, 18)] if sp.get('hatch') else []
    xs2 = stations(x0, x1, 0.035, extra=extra)
    belt = lambda x: z_top(x) - 0.02

    def zr(x):
        return interp_round(sp['roof'], x)
    H_roof = max(z for _, z in sp['roof'])

    def gh_dims(x):
        """the greenhouse's section at x: its foot and top, half widths at the belt and at the roof, the roof's rounding"""
        zb, zt = belt(x), max(belt(x) + 0.003, zr(x))
        wb = min(sp['belt_w'], half_w(x) - 0.02)
        h = zt - zb
        # (the sides lean in at one angle from the belt to the roof: a screen is then a trapezium, wide at the scuttle,
        # and its pillars are straight.  Before, the top was the roof's width at every height over 12 cm and flared
        # out to the belt under that: the screens' edges bent there)
        wr = wb - (wb - sp['roof_w']) * min(1.0, h / max(0.05, H_roof - zb))
        return zb, zt, wb, wr, sec_radii(wb, zb, zt, 0.01, sp['gh_rt'])[1]

    def gh_sec(x):
        zb, zt, wb, wr, _ = gh_dims(x)
        return section(wb, zb, zt, 0.01, sp['gh_rt'], tumble=wb - wr, crown=0.018)

    ws, rw, sd = sp['windshield'], sp['rear_window'], sp['side']
    PIL = 0.04                                  # body left between the glass and the roof's rounding, and over the belt
    cap = H_roof - sp['gh_rt'] - sp.get('cant', 0.045)       # the side glass's top on the roof
    rwz = sp.get('rw_z')

    def side_top(x):
        _, zt, _, _, rt = gh_dims(x)
        return min(zt - rt - PIL, cap)

    def top_lim(x):
        _, _, _, wr, rt = gh_dims(x)
        return wr - rt - PIL * 0.6

    def window(q, nrm, c, m):
        """the part of the face q inside a window drawn in by margin m (out for m < 0), and what is left of it:
        ([polygons], [polygons]).  Side glass on the flanks, the screens on top, a van's rear door glass"""
        if abs(nrm.y) > 0.55:
            band = [lambda p: p.z - (belt(p.x) + PIL + m), lambda p: side_top(p.x) - m - p.z,
                    lambda p: p.x - (sd[0] + m), lambda p: sd[1] - m - p.x]
            gaps = [(a - m, b + m) for a, b in sp['pillars'] if a - m < b + m]
        elif abs(nrm.x) > 0.6 and sp.get('van') and c.x < 0:
            band = [lambda p: p.z - (rwz[0] + m), lambda p: rwz[1] - m - p.z, lambda p: sp['roof_w'] - 0.10 - m - abs(p.y)]
            gaps = []
        elif c.x > (ws[0] + rw[1]) / 2:
            band = [lambda p: p.x - (ws[0] + m), lambda p: ws[1] - m * 0.5 - p.x, lambda p: top_lim(p.x) - m - abs(p.y)]
            gaps = []
        else:
            band = [lambda p: p.x - (rw[0] + m * 0.5), lambda p: rw[1] - m - p.x, lambda p: top_lim(p.x) - m - abs(p.y)]
            if rwz and not sp.get('van'):                                               # tailgate glass
                band += [lambda p: p.z - (rwz[0] + m), lambda p: rwz[1] - m - p.z]
            gaps = []
        ins, outs = [q], []
        for f in band:
            nxt = []
            for poly in ins:
                a, b = split_poly(poly, f)
                if a:
                    nxt.append(a)
                if b:
                    outs.append(b)
            ins = nxt
        for g0, g1 in gaps:                                                             # the pillars between the doors
            nxt = []
            for poly in ins:
                aft, rest = split_poly(poly, lambda p: g0 - p.x)
                if aft:
                    nxt.append(aft)
                if rest:
                    fore, mid = split_poly(rest, lambda p: p.x - g1)
                    if fore:
                        nxt.append(fore)
                    if mid:
                        outs.append(mid)
            ins = nxt
        return ins, outs

    # glass, its black rubber, on the older saloon a chrome surround, then the body's paint
    rings = ([(-0.042, 'car_paint'), (-0.024, 'chrome')] if chrome_trim else [(-0.026, 'car_paint')]) + [(0.0, 'trim_black')]

    def gh_split(q, c, nrm):
        out, cur = [], [q]
        for m, outside in rings:
            nxt = []
            for poly in cur:
                ins, outs = window(poly, nrm, c, m)
                nxt += ins
                out += [(o, outside) for o in outs]
            cur = nxt
        return out + [(poly, 'glass_car') for poly in cur]
    loft(mb, xs2, gh_sec, None, 'gh', cap_front=False, cap_back=False, split_fn=gh_split)

    # ---------------- wheel-well liners (hide the lofted arch tunnel) + underbody
    for ax in (fa, ra):
        mb.box((ax, 0, 0.42), (r_arch * 2 + 0.02, W - 0.36, 0.56), 'rubber', skip=('bottom',))
        for s in (-1, 1):                       # well walls
            mb.box((ax, s * (hw - 0.17), cy_arch + 0.1), (r_arch * 2, 0.02, r_arch * 1.2), 'rubber')
    mb.box((0, 0, sp['sill'] + 0.02), (L - 0.5, W - 0.2, 0.06), 'rubber', skip=('top',))

    # ---------------- bumpers: lofted, wrapping round the corners
    bz0, bz1 = sp['bumper_z']
    bmat = {'body': 'car_paint', 'grey': 'plastic_grey', 'black': 'plastic_grey'}[sp['bumper']]
    ext = 0.06 if sp['bumper'] == 'body' else 0.07
    band = (bz1 - 0.10, bz1 - 0.055)          # the rub band (black, or chrome on the older saloon)

    for sx in (1, -1):
        start = (fa + r_arch + 0.03) if sx > 0 else -(ra - r_arch - 0.03)
        xe = L / 2 + ext

        def bsec(u, sx=sx, xe=xe):
            k = smoothstep(L / 2 - p_len - 0.05, xe, u)
            wb = min(hw, half_w(sx * min(u, L / 2)) + 0.012) - 0.10 * k ** 2.2
            soft = 0.03 * smoothstep(xe - 0.07, xe, u)
            return section(wb, bz0 + soft, bz1 - soft, 0.05, 0.045, tumble=0.006, crown=0.004,
                           zsplits=band if sp['bumper'] == 'body' else ())

        us = stations(start, xe, 0.035)

        def bmat_fn(c, n):
            if sp['bumper'] == 'body' and band[0] < c.z < band[1] and abs(n.x) < 0.75:
                return 'trim_black'
            return bmat
        sub = MeshBuilder('tmp')
        loft(sub, us, bsec, bmat_fn, 'bump%d' % sx, cap_front=True, cap_back=False)
        for idx, mat, uvs, smooth in sub.faces:      # mirror the rear one by flipping x (and winding)
            pts = [tuple(sub.verts[i]) for i in idx]
            if sx < 0:
                pts = [(-x, y, z) for x, y, z in pts][::-1]
            mb.face(pts, mat, smooth=('bump%d' % sx) if smooth else False)
        xf_ = sx * (xe + 0.002)
        bw = W / 2 - 0.16                        # the band across the flat face (split round the plate)
        for y0, y1 in ((0.20, bw),):
            for s in (-1, 1):
                if sp['bumper'] == 'body':
                    mb.box((xf_, s * (y0 + y1) / 2, sum(band) / 2), (0.006, y1 - y0, band[1] - band[0]), 'trim_black')
                elif sp['trim'] == 'chrome':
                    mb.box((xf_, s * (y0 + y1) / 2, bz1 - 0.06), (0.006, y1 - y0, 0.035), 'chrome')
        if sx > 0 and sp['bumper'] == 'body':     # air intake under the plate
            mb.box((xf_ - 0.01, 0, bz0 + 0.075), (0.012, 0.90, 0.05), 'trim_black')
        if sp['trim'] == 'chrome':
            mb.box((xf_, 0, bz1 - 0.06), (0.006, 0.40, 0.035), 'chrome')

    # ---------------- fascia: lamps and grille
    xf = L / 2
    lz0, lz1 = sp['lamp_h']
    lzc = (lz0 + lz1) / 2
    gw = sp['grille_w']
    flat = body_y(xf, lzc) - 0.005             # half-width of the flat front face at lamp height
    if sp['lamps'] == 'flush':
        we = wrap_end(1, lzc)
        strip(1, gw + 0.03, we - 0.16, lz0, lz1, 'light_white', n=8)
        strip(1, we - 0.16, we, lz0, lz1, 'light_amber', n=5)
        strip(1, gw + 0.015, we + 0.008, lz0 - 0.012, lz1 + 0.012, 'trim_black', off=0.002, n=12)
        strip(1, gw + 0.03, we - 0.17, lz0 - 0.004, lz0 + 0.004, 'chrome', off=0.005, n=8)      # lens split
    else:
        y_out = min(flat - 0.07, gw + 0.03 + (0.36 if L > 4 else 0.24))
        bez = 'chrome' if chrome_trim else 'trim_black'
        strip(1, gw + 0.02, y_out + 0.015, lz0 - 0.015, lz1 + 0.015, bez, off=0.003, n=4)
        strip(1, gw + 0.035, y_out, lz0, lz1, 'light_white', off=0.006, n=4)
        if L > 4:                                 # rectangular quad-lamp look: a divider
            ym = gw + 0.035 + (y_out - gw - 0.035) * 0.55
            strip(1, ym - 0.006, ym + 0.006, lz0, lz1, bez, off=0.008, n=1)
        we = wrap_end(1, lzc)
        strip(1, y_out + 0.02, we, lz0 + 0.005, lz1 - 0.005, 'light_amber', off=0.005)
    # grille
    if sp['grille'] == 'slot':
        gz0, gz1 = lz0 + 0.01, lz1 - 0.01
        mb.box((xf - 0.01, 0, (gz0 + gz1) / 2), (0.03, gw * 2, gz1 - gz0), 'trim_black')
        for z in (gz0, gz1):
            mb.box((xf + 0.004, 0, z), (0.012, gw * 2 + 0.02, 0.01), 'chrome')
        mb.box((xf + 0.002, 0, (gz0 + gz1) / 2), (0.01, gw * 2 - 0.04, 0.008), 'chrome')
        mb.box((xf + 0.008, 0, (gz0 + gz1) / 2), (0.01, 0.09, 0.05), 'chrome')                      # oval-ish badge
    elif sp['grille'] == 'chrome':
        gz0, gz1 = lz0 - 0.01, lz1 + 0.01
        mb.box((xf + 0.005, 0, (gz0 + gz1) / 2), (0.03, gw * 2, gz1 - gz0), 'trim_black')
        for z in (gz0, gz1):
            mb.box((xf + 0.012, 0, z), (0.03, gw * 2 + 0.03, 0.022), 'chrome')
        for s in (-1, 1):
            mb.box((xf + 0.012, s * (gw + 0.005), (gz0 + gz1) / 2), (0.03, 0.02, gz1 - gz0), 'chrome')
        nb = int(gw * 2 / 0.045)
        for i in range(1, nb):
            mb.box((xf + 0.016, -gw + i * 2 * gw / nb, (gz0 + gz1) / 2), (0.01, 0.008, gz1 - gz0 - 0.02), 'chrome')
        mb.box((xf + 0.03, 0, (gz0 + gz1) / 2), (0.012, 0.07, 0.07), 'chrome')                        # badge
        mb.box((xf - 0.05, 0, z_top(xf - 0.05) + 0.02), (0.05, 0.03, 0.04), 'chrome')               # hood ornament
    else:                                        # 'slit': two thin openings in the body-coloured nose panel
        for k, z in enumerate((lzc + 0.022, lzc - 0.015)):
            mb.box((xf + 0.001, 0, z), (0.01, gw * 2 - k * 0.04, 0.018), 'trim_black')
        mb.box((xf + 0.004, 0, lzc + 0.003), (0.01, 0.07, 0.03), 'chrome')

    # ---------------- tail lamps
    tz0, tz1 = sp['tail_h']
    tzc = (tz0 + tz1) / 2
    xr = -L / 2
    if sp['tail'] == 'band':                     # full-width band; the plate sits in its centre garnish
        we = wrap_end(-1, tzc)
        strip(-1, 0.22, we, tz0 - 0.01, tz1 + 0.01, 'trim_black', off=0.002, n=14)
        strip(-1, 0.23, 0.32, tz0, tz1, 'lens_clear', n=2)
        strip(-1, 0.32, we - 0.13, tz0, tz1, 'light_red', n=8)
        strip(-1, we - 0.13, we, tz0 + (tz1 - tz0) * 0.45, tz1, 'light_amber', n=4)
        strip(-1, we - 0.13, we, tz0, tz0 + (tz1 - tz0) * 0.45, 'light_red', n=4)
        strip(-1, 0.0, 0.22, tz0 - 0.01, tz1 + 0.01, 'trim_black', off=0.002, n=4)                  # garnish round the plate
    elif sp['tail'] == 'blocks':
        we = min(wrap_end(-1, tzc), body_y(-L / 2, tzc) + 0.03)      # (to the corner's turn, not round it)
        strip(-1, 0.30, we, tz0 - 0.012, tz1 + 0.012, 'chrome', off=0.002, n=10)
        strip(-1, 0.31, 0.42, tz0, tz1, 'lens_clear', n=2)
        strip(-1, 0.42, we - 0.14, tz0, tz1, 'light_red', n=6)
        strip(-1, we - 0.14, we, tz0, tz1, 'light_amber', n=4)
        mb.box((xr - 0.004, 0, tz1 - 0.035), (0.01, 0.58, 0.05), 'trim_black')                      # garnish
    else:                                        # 'vertical': tall lamps on the rear corners
        we = min(wrap_end(-1, tzc), body_y(-L / 2, tzc) + 0.03)
        y0 = max(0.25, we - (0.20 if sp.get('van') else 0.16))
        strip(-1, y0 - 0.012, we + 0.006, tz0 - 0.012, tz1 + 0.012, 'trim_black', off=0.002, n=5)
        h3 = (tz1 - tz0) / 3
        strip(-1, y0, we, tz0 + 2 * h3, tz1, 'light_red', n=4)
        strip(-1, y0, we, tz0 + h3, tz0 + 2 * h3, 'light_amber', n=4)
        strip(-1, y0, we, tz0, tz0 + h3, 'light_red', n=4)
        strip(-1, y0 + 0.02, y0 + 0.09, tz0 + 0.02, tz0 + h3 - 0.02, 'lens_clear', off=0.006, n=1)

    # ---------------- plates (UV into the 2x2 plate atlas: 0/1 green private, 2 yellow commercial, 3 taxi roof sign)
    cell = 2 if sp.get('taxi') else (0 if kind in ('sedan', 'van', 'sedan2') else 1)
    u0, v0 = (cell % 2) * 0.5, 0.5 if cell < 2 else 0.0          # Blender UVs (v up); the glTF export flips them
    pw, ph = 0.335, 0.165
    zr_plate = sp['plate_rear_z']
    for sx, zc in ((1, (bz0 + bz1) / 2 - (0.01 if sp['bumper'] == 'body' else 0.0)), (-1, zr_plate)):
        x = sx * (L / 2 + (ext + 0.006 if sx > 0 else 0.014))
        if sx < 0:
            mb.box((-L / 2 - 0.003, 0, zc), (0.01, pw + 0.04, ph + 0.03), 'trim_black')               # plate recess
        q = [(x, -pw / 2 * sx, zc - ph / 2), (x, pw / 2 * sx, zc - ph / 2), (x, pw / 2 * sx, zc + ph / 2), (x, -pw / 2 * sx, zc + ph / 2)]
        mb.face(q, 'plate', uvs=[(u0, v0), (u0 + 0.5, v0), (u0 + 0.5, v0 + 0.5), (u0, v0 + 0.5)])

    # ---------------- sides: rub strips, door seams, handles, mirrors
    for s in (-1, 1):
        xa, xb = ra + r_arch + 0.03, fa - r_arch - 0.03
        zc = sp['rub_z']
        ys = s * (body_y((xa + xb) / 2, zc) + 0.008)
        mb.box(((xa + xb) / 2, ys, zc), (xb - xa, 0.025, 0.045), 'trim_black')
        if chrome_trim:
            mb.box(((xa + xb) / 2, ys + s * 0.013, zc + 0.012), (xb - xa, 0.004, 0.008), 'chrome')
        for dx in sp['doors']:
            za, zb_ = max(sp['sill'], z_bot(dx)) + 0.05, belt(dx) - 0.005
            for k in range(5):                                                          # (along the flank's bow)
                z0, z1 = za + (zb_ - za) * k / 5, za + (zb_ - za) * (k + 1) / 5
                y0, y1 = s * (body_y(dx, z0) + 0.002), s * (body_y(dx, z1) + 0.002)
                q = [(dx - 0.005, y0, z0), (dx + 0.005, y0, z0), (dx + 0.005, y1, z1), (dx - 0.005, y1, z1)]
                mb.face(q if s > 0 else q[::-1], 'trim_black')
        for dx in sp['doors'][:-1]:
            hx, hz = dx - 0.22, belt(dx - 0.22) - 0.10
            mb.box((hx, s * (body_y(hx, hz) + 0.004), hz), (0.13, 0.016, 0.028), trim_mat)
        mx = sd[1] - 0.04
        wb_ = gh_dims(mx)[2]
        my = s * (wb_ + 0.13)
        mz = belt(mx) + 0.09
        mb.box((mx, my, mz), (0.07, 0.15, 0.10), sp['mirror'])
        mb.box((mx - 0.036, my, mz), (0.005, 0.13, 0.085), 'chrome')
        mb.box((mx + 0.03, s * (wb_ + 0.03), belt(mx) + 0.045), (0.09, 0.07, 0.07), 'trim_black')        # sail
    # wipers & antenna
    for s in (-0.3, 0.35):
        x = ws[1] - 0.04
        mb.box((x - 0.05, s, belt(x) + 0.03), (0.04, 0.48, 0.012), 'trim_black')
    ax_ = sd[1] + 0.25
    mb.cylinder((ax_, -hw + 0.12), 0.004, z_top(ax_), z_top(ax_) + 0.75, 'metal_dark', seg=4, cap_top=True, smooth=False)

    # ---------------- interior seen through the glass
    zf = sp['sill'] + 0.12
    dx_, dy_ = driver_seat(kind)
    xd = ws[1] - 0.17                                                                         # under the windscreen base
    mb.box((xd, 0, belt(xd) - 0.10), (0.34, W - 0.30, 0.18), 'car_interior')                 # dashboard
    rows = [dx_ + 0.15, 0.10, -0.85, -1.70] if sp.get('van') else [dx_ + 0.15, dx_ - 0.75]
    seat_w = min(0.48, W / 2 - 0.22)
    for i, rx in enumerate(rows):
        for s in ((-1, 1) if i == 0 else (0,)):
            yy = s * 0.36 if W > 1.5 else s * 0.31
            wseat = seat_w if i == 0 else W - 0.42
            mb.box((rx, yy, zf + 0.02), (0.48, wseat, 0.14), 'car_interior')                 # low seats, as in a real car
            mb.box((rx - 0.24, yy, zf + 0.37), (0.12, wseat, 0.58), 'car_interior')
    # steering wheel (left-hand drive, driver on +Y)
    swx = min(dx_ + 0.50, xd - 0.22)
    swy, swz = dy_, belt(swx) + 0.02
    for k in range(10):
        a0, a1 = 2 * math.pi * k / 10, 2 * math.pi * (k + 1) / 10
        p0 = (swx + 0.05 * math.sin(a0), swy + 0.18 * math.cos(a0), swz + 0.18 * math.sin(a0))
        p1 = (swx + 0.05 * math.sin(a1), swy + 0.18 * math.cos(a1), swz + 0.18 * math.sin(a1))
        mb.box(tuple((Vector(p0) + Vector(p1)) / 2), ((Vector(p1) - Vector(p0)).length + 0.01, 0.03, 0.03), 'trim_black')

    # ---------------- taxi roof sign
    if sp.get('taxi'):
        zr0 = zr(-0.4) + 0.01
        mb.box((-0.40, 0, zr0 + 0.10), (0.26, 0.56, 0.20), 'light_amber', mats={'top': 'trim_black'})
        for s in (-1, 1):
            q = [(-0.53, s * 0.2805, zr0 + 0.02), (-0.27, s * 0.2805, zr0 + 0.02), (-0.27, s * 0.2805, zr0 + 0.18), (-0.53, s * 0.2805, zr0 + 0.18)]
            uv = [(1.0, 0.0), (0.5, 0.0), (0.5, 0.5), (1.0, 0.5)] if s > 0 else [(0.5, 0.5), (1.0, 0.5), (1.0, 0.0), (0.5, 0.0)]
            mb.face(q if s > 0 else q[::-1], 'plate', uvs=uv)

    tw = 0.165 if W < 1.5 else 0.19
    wheels = [make_wheel(f'wheel_{n}', (x, s * (hw - 0.12), tyre), tyre, tw, s, sp['wheel']) for n, x, s in
              (('FL', fa, 1), ('FR', fa, -1), ('RL', ra, 1), ('RR', ra, -1))]
    return mb, wheels


def make_wheel(name, c, r, w, side, style='steel'):
    """Tyre with rounded shoulders and either a 1990s plastic full wheel cover (silver, ring of slots) or a
    pressed-steel rim with a small chrome centre cap. Built around the origin; the caller places the object at c
    (the axle), so the game can spin it about its local Y (glTF -Z) axis."""
    mb = MeshBuilder(name)
    mb.xf = Matrix.Scale(CAR_SCALE, 4)
    seg = 22
    # lathe profile (radius, y) from inner edge, around the tyre, to the outer face
    hw = w / 2
    prof = [(r * 0.66, -hw * 0.95), (r * 0.80, -hw), (r * 0.93, -hw * 0.98), (r * 0.985, -hw * 0.8), (r, -hw * 0.45),
            (r, hw * 0.45), (r * 0.985, hw * 0.8), (r * 0.93, hw * 0.98), (r * 0.80, hw), (r * 0.66, hw * 0.95)]
    mats = ['rubber'] * (len(prof) - 1)

    def ring(rad, y, a):
        return (rad * math.cos(a), y, rad * math.sin(a))
    for k in range(seg):
        a0, a1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        for i in range(len(prof) - 1):
            (r0, y0), (r1, y1) = prof[i], prof[i + 1]
            q = [ring(r0, y0, a0), ring(r1, y1, a0), ring(r1, y1, a1), ring(r0, y0, a1)]
            mb.face(q, mats[i], smooth='tyre')
    # face of the wheel (side = +1: outer face at +Y)
    yo = side * hw * 0.92
    if style == 'cover':
        rim = [(r * 0.68, yo), (r * 0.66, yo + side * 0.008), (r * 0.56, yo + side * 0.014), (r * 0.30, yo + side * 0.012),
               (r * 0.20, yo + side * 0.016), (0.0, yo + side * 0.02)]
        rmats = ['metal', 'metal', 'metal', 'chrome', 'chrome']
    else:
        rim = [(r * 0.66, yo), (r * 0.60, yo - side * 0.02), (r * 0.40, yo - side * 0.03), (r * 0.26, yo - side * 0.025),
               (r * 0.22, yo + side * 0.01), (0.0, yo + side * 0.015)]
        rmats = ['metal_dark', 'metal_dark', 'metal_dark', 'chrome', 'chrome']
    for k in range(seg):
        a0, a1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        for i in range(len(rim) - 1):
            (r0, y0), (r1, y1) = rim[i], rim[i + 1]
            q = [ring(r0, y0, a0), ring(r1, y1, a0), ring(r1, y1, a1), ring(r0, y0, a1)]
            if side < 0:
                q = q[::-1]
            mb.face(q, rmats[i], smooth='rim%d' % i)
    if style == 'cover':                         # a ring of slots in the cover
        for k in range(12):
            a = 2 * math.pi * k / 12
            p = Vector(ring(r * 0.45, yo + side * 0.0145, a))
            t = Vector((-math.sin(a), 0, math.cos(a)))
            u = Vector((math.cos(a), 0, math.sin(a)))
            q = [p - t * 0.022 - u * 0.03, p + t * 0.022 - u * 0.03, p + t * 0.022 + u * 0.03, p - t * 0.022 + u * 0.03]
            q = [tuple(v + Vector((0, side * 0.002, 0))) for v in q]
            mb.face(q if side > 0 else q[::-1], 'trim_black')
    else:                                        # vent holes in the steel disc
        for k in range(6):
            a = 2 * math.pi * k / 6
            p = Vector(ring(r * 0.47, yo - side * 0.028, a))
            t = Vector((-math.sin(a), 0, math.cos(a)))
            u = Vector((math.cos(a), 0, math.sin(a)))
            q = [p - t * 0.02 - u * 0.018, p + t * 0.02 - u * 0.018, p + t * 0.02 + u * 0.018, p - t * 0.02 + u * 0.018]
            q = [tuple(v + Vector((0, side * 0.002, 0))) for v in q]
            mb.face(q if side > 0 else q[::-1], 'trim_black')
    # inner face disc (dark)
    yi = -side * hw * 0.92
    pts = [ring(r * 0.66, yi, 2 * math.pi * k / seg) for k in range(seg)]
    mb.face(pts if side < 0 else pts[::-1], 'trim_black')
    mb.wheel_pos = tuple(v * CAR_SCALE for v in c)
    return mb
