"""스쿠터: the 50 cc scooter students rode about the campus in the 1990s (in the manner of 대림 택트 and its kind, not a
copy of one): 1.65 m long on a 1.16 m wheelbase, 10-inch wheels, a flat step-through floor behind a leg shield, the
headlamp in the handlebar cowl, a long black seat over a painted rear body, a small rack, the belt case on the left
of the rear wheel and the silencer on the right.  No number plate: a moped under 50 cc carried none till 2012.

Frame as blender/cars.py: +X forward, +Y left, +Z up, the ground at z = 0, the origin under the middle of the
wheelbase.  The paint is `car_paint` (web/src: coloured per scooter), the two wheels separate objects named wheel_F
and wheel_R with their origins on the axles (the game spins them), the centre stand an object named `stand` (down:
the parked ones stand on it; the game hides it on those that are ridden).

web/src/life.js seats the rider by SEAT, GRIP and FLOOR below.
"""
import math
from mathutils import Vector
from common import MeshBuilder
from cars import interp, section, loft, stations

R_WHEEL, AXLE_F, AXLE_R = 0.205, 0.59, -0.57
SEAT = (-0.42, 0.742)                # where the rider sits: x, the seat's top
GRIP = (0.17, 0.29, 0.985)           # the left grip's middle (the right one at -y)
FLOOR = 0.302                        # the floor's top


def rod(mb, a, b, r, mat, seg=6, caps=True):
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    u = d.cross(Vector((0, 0, 1)))
    if u.length < 1e-4:
        u = Vector((1, 0, 0))
    u.normalize()
    v = d.cross(u)
    ring = lambda c: [c + (u * math.cos(2 * math.pi * k / seg) + v * math.sin(2 * math.pi * k / seg)) * r for k in range(seg)]
    A, B = ring(a), ring(b)
    tag = 'rod%d' % len(mb.faces)
    for k in range(seg):
        k2 = (k + 1) % seg
        mb.face([tuple(A[k2]), tuple(A[k]), tuple(B[k]), tuple(B[k2])], mat, smooth=tag)
    if caps:
        mb.face([tuple(p) for p in A], mat)
        mb.face([tuple(p) for p in B[::-1]], mat)


def skin(mb, rings, mat_fn, tag, cap0=None, cap1=None):
    """quads between consecutive closed rings of points (the same count in each), facing away from the rings' middles"""
    cs = [sum((Vector(p) for p in r), Vector()) / len(r) for r in rings]
    n = len(rings[0])
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        axis = (cs[i] + cs[i + 1]) / 2
        for k in range(n):
            k2 = (k + 1) % n
            q = [Vector(A[k]), Vector(A[k2]), Vector(B[k2]), Vector(B[k])]
            nrm = (q[1] - q[0]).cross(q[3] - q[0])
            if nrm.length < 1e-10:
                nrm = (q[2] - q[1]).cross(q[3] - q[1])
            if nrm.length < 1e-10:
                continue
            c = sum(q, Vector()) / 4
            if nrm.dot(c - axis) < 0:
                q = q[::-1]
                nrm = -nrm
            mb.face([tuple(v) for v in q], mat_fn(c, nrm.normalized()), smooth=tag)
    for ring, c, other, mat in ((rings[0], cs[0], cs[1], cap0), (rings[-1], cs[-1], cs[-2], cap1)):
        if not mat:
            continue
        pts = [Vector(p) for p in ring]
        nrm = sum(((pts[k] - c).cross(pts[(k + 1) % n] - c) for k in range(n)), Vector())
        mb.face([tuple(p) for p in (pts if nrm.dot(c - other) > 0 else pts[::-1])], mat)


def arc_guard(mb, cx, r, a0, a1, half_w, mat, tag, n=9, thick=0.012, drop=0.03):
    """a mudguard round the axle at (cx, R_WHEEL): from angle a0 to a1 (degrees, 0 = forward, 90 = up)"""
    rings = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        ca, sa = math.cos(a), math.sin(a)
        P = lambda rad, y: (cx + rad * ca, y, R_WHEEL + rad * sa)
        rings.append([P(r - drop, -half_w), P(r, -half_w + 0.018), P(r, half_w - 0.018), P(r - drop, half_w),
                      P(r - drop - thick, half_w - 0.008), P(r - thick, half_w - 0.022), P(r - thick, -half_w + 0.022),
                      P(r - drop - thick, -half_w + 0.008)])
    skin(mb, rings, lambda c, nrm: mat, tag, cap0=mat, cap1=mat)


def bike_wheel(name, x, r=R_WHEEL, w=0.092):
    """a 3.00-10 tyre on a pressed-steel rim with a drum hub, the same on both sides; built round the origin (the axle)"""
    mb = MeshBuilder(name)
    seg = 18
    hw = w / 2
    prof = [(r * 0.62, -hw * 0.8), (r * 0.80, -hw), (r * 0.93, -hw * 0.9), (r, -hw * 0.4), (r, hw * 0.4), (r * 0.93, hw * 0.9),
            (r * 0.80, hw), (r * 0.62, hw * 0.8)]
    ring = lambda rad, y, a: (rad * math.cos(a), y, rad * math.sin(a))
    for k in range(seg):
        a0, a1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        for (r0, y0), (r1, y1) in zip(prof[:-1], prof[1:]):
            mb.face([ring(r0, y0, a0), ring(r1, y1, a0), ring(r1, y1, a1), ring(r0, y0, a1)], 'rubber', smooth='tyre')
        for side in (1, -1):                          # rim, dished disc, hub
            rim = [(r * 0.62, hw * 0.8), (r * 0.56, hw * 0.55), (r * 0.30, hw * 0.45), (r * 0.26, hw * 0.75), (0.0, hw * 0.8)]
            for i, ((r0, y0), (r1, y1)) in enumerate(zip(rim[:-1], rim[1:])):
                q = [ring(r0, side * y0, a0), ring(r1, side * y1, a0), ring(r1, side * y1, a1), ring(r0, side * y0, a1)]
                mb.face(q if side > 0 else q[::-1], 'metal' if i < 2 else 'metal_dark', smooth='rim%d%d' % (i, side))
    mb.wheel_pos = (x, 0.0, r)
    return mb


def scooter():
    """-> (body MeshBuilder, [wheel MeshBuilders], stand MeshBuilder)"""
    mb = MeshBuilder('scooter')
    paint = lambda c, n: 'car_paint'

    # ---------------- rear body under the seat, and the seat
    hw_b = [(-0.81, 0.085), (-0.72, 0.135), (-0.42, 0.172), (-0.10, 0.165), (0.03, 0.135)]
    zb_b = [(-0.81, 0.51), (-0.62, 0.405), (-0.32, 0.35), (0.03, 0.30)]
    zt_b = [(-0.81, 0.665), (-0.60, 0.67), (-0.10, 0.64), (0.03, 0.60)]
    xs = stations(-0.81, 0.03, 0.04)
    loft(mb, xs, lambda x: section(interp(hw_b, x), interp(zb_b, x), interp(zt_b, x), 0.05, 0.045, tumble=0.022, n_arc=3, n_top=3),
         paint, 'rear')
    hw_s = [(-0.75, 0.095), (-0.62, 0.15), (-0.25, 0.145), (-0.03, 0.10)]
    zt_s = [(-0.75, 0.75), (-0.52, 0.755), (-0.22, 0.74), (-0.03, 0.705)]
    xs = stations(-0.75, -0.03, 0.04)
    loft(mb, xs, lambda x: section(interp(hw_s, x), interp(zt_b, x) - 0.012, interp(zt_s, x), 0.012, 0.04, tumble=0.012, crown=0.008,
                                   n_arc=3, n_top=3), lambda c, n: 'rubber', 'seat')

    # ---------------- floor: the painted tray with its rubber mat, the frame and battery box under it
    mb.box((0.20, 0, FLOOR - 0.026), (0.42, 0.34, 0.05), 'car_paint', mats={'top': 'rubber'})
    mb.box((0.14, 0, 0.20), (0.52, 0.17, 0.10), 'trim_black')

    # ---------------- leg shield: behind the front wheel at its foot, round the steering column above it
    xf = [(0.26, 0.375), (0.42, 0.365), (0.53, 0.425), (0.64, 0.42), (0.87, 0.305)]
    xb = [(0.26, 0.335), (0.45, 0.305), (0.64, 0.275), (0.87, 0.195)]
    wz = [(0.26, 0.17), (0.40, 0.205), (0.62, 0.20), (0.80, 0.135), (0.87, 0.105)]
    rings = []
    for z in [0.26 + 0.61 * i / 12 for i in range(13)]:
        f, b, w = interp(xf, z), interp(xb, z), interp(wz, z)
        ys = [-w + 2 * w * k / 8 for k in range(9)]
        rings.append([(b + (f - b) * math.sqrt(max(0.0, 1 - (y / w) ** 2)), y, z) for y in ys] +
                     [(b - 0.012, w * 0.5, z), (b - 0.012, -w * 0.5, z)])
    skin(mb, rings, lambda c, n: 'plastic_grey' if n.x < -0.6 else 'car_paint', 'shield', cap1='car_paint')
    for s in (-1, 1):                                                           # front indicators on the shield
        mb.box((interp(xf, 0.70) - 0.045, s * 0.155, 0.70), (0.035, 0.05, 0.036), 'light_amber')

    # ---------------- handlebar cowl with the headlamp, the bars, levers and mirrors
    hw_c = [(0.12, 0.10), (0.21, 0.15), (0.31, 0.135), (0.355, 0.095)]
    zb_c = [(0.12, 0.885), (0.355, 0.85)]
    zt_c = [(0.12, 0.99), (0.22, 1.005), (0.355, 0.96)]
    xs = stations(0.12, 0.355, 0.03)
    loft(mb, xs, lambda x: section(interp(hw_c, x), interp(zb_c, x), interp(zt_c, x), 0.03, 0.04, tumble=0.015, crown=0.006,
                                   n_arc=3, n_top=3), paint, 'cowl')
    mb.box((0.358, 0, 0.905), (0.012, 0.15, 0.078), 'chrome')
    mb.box((0.366, 0, 0.905), (0.008, 0.132, 0.062), 'light_white')
    mb.box((0.118, 0, 0.94), (0.008, 0.15, 0.07), 'trim_black')                 # the speedometer
    gx, gy, gz = GRIP
    for s in (-1, 1):
        inner, outer = (0.215, s * 0.12, 0.965), (gx - 0.012, s * (gy + 0.055), gz + 0.004)
        mid = tuple(Vector(inner).lerp(Vector(outer), 0.52))
        rod(mb, inner, mid, 0.011, 'metal_dark')
        rod(mb, mid, outer, 0.017, 'rubber')                                    # the grip
        rod(mb, (0.235, s * 0.20, 0.972), (gx + 0.035, s * (gy + 0.05), gz + 0.002), 0.005, 'chrome', seg=4)   # brake lever
        rod(mb, (0.20, s * 0.165, 0.975), (0.175, s * 0.275, 1.165), 0.0055, 'chrome', seg=4)
        mb.box((0.172, s * 0.295, 1.185), (0.022, 0.105, 0.066), 'trim_black')
        mb.box((0.159, s * 0.295, 1.185), (0.004, 0.09, 0.052), 'chrome')

    # ---------------- front wheel: mudguard and fork
    arc_guard(mb, AXLE_F, R_WHEEL + 0.03, 12, 172, 0.072, 'car_paint', 'fguard')
    for s in (-1, 1):
        rod(mb, (AXLE_F, s * 0.066, R_WHEEL), (0.455, s * 0.066, 0.47), 0.016, 'metal')
        rod(mb, (AXLE_F, s * 0.05, R_WHEEL), (AXLE_F, s * 0.085, R_WHEEL), 0.03, 'metal_dark')

    # ---------------- rear wheel: mudguard, belt case and shock on the left, silencer on the right, engine
    arc_guard(mb, AXLE_R, R_WHEEL + 0.025, 120, 200, 0.062, 'trim_black', 'rguard', n=6)
    mb.box((-0.34, 0.108, 0.215), (0.56, 0.075, 0.15), 'metal')
    mb.box((-0.30, 0.150, 0.215), (0.30, 0.012, 0.09), 'metal_dark')
    mb.box((-0.24, 0.10, 0.325), (0.26, 0.08, 0.07), 'trim_black')            # air cleaner
    rod(mb, (AXLE_R + 0.01, 0.112, 0.25), (-0.50, 0.112, 0.50), 0.02, 'metal_dark')
    rod(mb, (AXLE_R + 0.01, 0.112, 0.30), (-0.52, 0.112, 0.45), 0.027, 'chrome', seg=8)
    rod(mb, (-0.22, -0.13, 0.205), (-0.76, -0.14, 0.275), 0.05, 'metal_dark', seg=8)
    rod(mb, (-0.30, -0.172, 0.24), (-0.66, -0.178, 0.285), 0.03, 'chrome', seg=6)      # its heat shield
    rod(mb, (-0.02, -0.07, 0.20), (-0.22, -0.13, 0.205), 0.02, 'metal_dark')
    mb.box((-0.08, 0, 0.24), (0.22, 0.19, 0.15), 'metal_dark')

    # ---------------- tail: lamp, indicators, rack
    mb.box((-0.815, 0, 0.605), (0.03, 0.15, 0.062), 'light_red')
    for s in (-1, 1):
        mb.box((-0.775, s * 0.115, 0.575), (0.05, 0.03, 0.036), 'light_amber')
        rod(mb, (-0.66, s * 0.095, 0.70), (-0.93, s * 0.095, 0.74), 0.008, 'metal_dark', seg=4)
    for x in (-0.93, -0.84, -0.76):
        rod(mb, (x, -0.095, 0.70 + (-0.66 - x) * 0.148), (x, 0.095, 0.70 + (-0.66 - x) * 0.148), 0.007, 'metal_dark', seg=4)

    # ---------------- centre stand (down)
    st = MeshBuilder('stand')
    for s in (-1, 1):
        rod(st, (-0.20, s * 0.06, 0.20), (-0.31, s * 0.13, 0.012), 0.011, 'metal_dark', seg=5)
    rod(st, (-0.31, -0.15, 0.012), (-0.31, 0.15, 0.012), 0.011, 'metal_dark', seg=5)
    return mb, [bike_wheel('wheel_F', AXLE_F), bike_wheel('wheel_R', AXLE_R)], st
