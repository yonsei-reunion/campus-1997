"""Street furniture, statues, the main gate, 1990s Korean cars and pedestrians."""
import math, random
from mathutils import Vector, Matrix
from common import MeshBuilder
from landmarks import arch_fill, rod


# ----------------------------------------------------------------------------- 쌍등 가로등 (double-globe lamp, 1997 library photo)
def lamp_double():
    mb = MeshBuilder('lamp_double')
    mb.box((0, 0, 0.25), (0.5, 0.5, 0.5), 'metal_dark')
    mb.cylinder((0, 0), 0.12, 0.5, 4.2, 'metal_dark', seg=10, r1=0.07)
    mb.cylinder((0, 0), 0.16, 0.5, 1.0, 'metal_dark', seg=10, r1=0.12)
    for s in (-1, 1):
        pts = [Vector((0, 0, 3.9)), Vector((s * 0.35, 0, 4.15)), Vector((s * 0.6, 0, 4.05))]
        for i in range(2):
            a, b = pts[i], pts[i + 1]
            d = (b - a)
            c = (a + b) / 2
            mb.box(tuple(c), (d.length, 0.06, 0.06), 'metal_dark', rotz=0)
        mb.cylinder((s * 0.6, 0), 0.05, 4.0, 4.12, 'metal_dark', seg=8)
        mb.sphere((s * 0.6, 0, 4.36), 0.25, 'globe', seg=14, rings=10)
    mb.cylinder((0, 0), 0.05, 4.2, 4.45, 'metal_dark', seg=8)
    mb.sphere((0, 0, 4.48), 0.07, 'metal_dark', seg=8, rings=6)
    return mb


# ----------------------------------------------------------------------------- 백양로 양팔 가로등 (1997 aerial photo)
def lamp_arm():
    """Two-armed street lamp with flat box luminaires.  Local +X points away from the road (over the sidewalk),
    -X over the carriageway."""
    mb = MeshBuilder('lamp_arm')
    mb.box((0, 0, 0.3), (0.42, 0.42, 0.6), 'metal_dark')
    mb.cylinder((0, 0), 0.11, 0.6, 7.6, 'metal_dark', seg=10, r1=0.065)
    for sx, L_ in ((-1, 1.7), (1, 1.05)):
        # slightly rising arm, then the luminaire box hanging from its tip
        p0, p1 = Vector((0, 0, 7.25)), Vector((sx * L_, 0, 7.55))
        c = (p0 + p1) / 2
        d = p1 - p0
        mb.box(tuple(c), (d.length, 0.07, 0.07), 'metal_dark')
        mb.box((sx * (L_ + 0.25), 0, 7.5), (0.75, 0.32, 0.16), 'lamp_housing')
        mb.box((sx * (L_ + 0.25), 0, 7.41), (0.6, 0.24, 0.02), 'globe')
    mb.cylinder((0, 0), 0.05, 7.6, 7.8, 'metal_dark', seg=8)
    return mb


# ----------------------------------------------------------------------------- 흰 세로 깃발 (sidewalk flags near the gate)
def flag_white():
    """A white cloth hung from a slim pole by the hedge, as the three on the west side of 백양로 north-east of the
    화단섬 in the 1997 aerial photo (reference/1997_백양로_항공사진.jpg, x 740 - 795, y 928 - 1033): about 1 m wide and
    2.3 m long, its foot a metre off the ground, the cloth stirring in the breeze (a few soft vertical folds)."""
    mb = MeshBuilder('flag_white')
    mb.cylinder((0, 0), 0.035, 0.0, 3.5, 'metal_dark', seg=8)
    mb.box((-0.55, 0, 3.32), (1.1, 0.035, 0.035), 'metal_dark')
    # the cloth: strips across and rows down it, so that the wind (web/src/flags.js) can bend it; u from the pole,
    # v up; the folds flatten towards the bar
    n, m = 8, 8
    P = lambda x, y, u, v: (x, y * (1 - 0.6 * v), (1.0 - 0.06 * u) * (1 - v) + 3.3 * v)
    for k in range(n):
        u0, u1 = k / n, (k + 1) / n
        x0, x1 = -0.08 - 1.0 * u0, -0.08 - 1.0 * u1
        y0, y1 = 0.09 * math.sin(u0 * 2 * math.pi * 1.5), 0.09 * math.sin(u1 * 2 * math.pi * 1.5)
        for j in range(m):
            v0, v1 = j / m, (j + 1) / m
            mb.face([P(x0, y0, u0, v0), P(x1, y1, u1, v0), P(x1, y1, u1, v1), P(x0, y0, u0, v1)], 'flag_cloth',
                    uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    return mb


# ----------------------------------------------------------------------------- 공중전화 부스
def payphone_booth():
    """공중전화 부스 as on a 1990s campus: 95 x 95 cm, 2.2 m high, a grey steel frame with clear panels on three sides,
    an open front, a lit sign on the roof and a shelf under the phone (the phone itself, Poly Haven's Korean payphone,
    is added in build.py).  The front faces -Y."""
    mb = MeshBuilder('payphone_booth')
    w = d = 0.95
    h = 2.2
    mb.box((0, 0, 0.04), (w + 0.1, d + 0.1, 0.08), 'concrete')                         # base slab
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * (w / 2 - 0.03), sy * (d / 2 - 0.03), h / 2), (0.06, 0.06, h), 'frame_silver')
    for sx in (-1, 1):                                                                 # clear side panels, mid rail
        mb.box((sx * (w / 2 - 0.03), 0, 1.2), (0.03, d - 0.1, 1.9), 'glass_door')
        mb.box((sx * (w / 2 - 0.03), 0, 1.0), (0.05, d - 0.06, 0.05), 'frame_silver')
    mb.box((0, d / 2 - 0.03, 1.2), (w - 0.1, 0.03, 1.9), 'glass_door')                 # back panel: lower half solid
    mb.box((0, d / 2 - 0.03, 0.55), (w - 0.06, 0.05, 0.9), 'plastic_grey')
    mb.box((0, -d / 2 + 0.03, 2.05), (w - 0.06, 0.06, 0.2), 'frame_silver')            # front head rail
    mb.box((0, 0, h + 0.05), (w + 0.12, d + 0.12, 0.1), 'frame_silver')                # roof
    mb.box((0, -d / 2 - 0.02, h + 0.27), (w * 0.9, 0.12, 0.34), 'light_white')         # lit sign
    mb.box((0, -d / 2 - 0.09, h + 0.27), (w * 0.9 - 0.12, 0.02, 0.2), 'sign_blue')
    mb.box((0, d / 2 - 0.2, 0.86), (0.5, 0.3, 0.04), 'metal')                          # shelf under the phone
    return mb


# ----------------------------------------------------------------------------- 원형 화분 (white round planters at the gate)
def planter():
    mb = MeshBuilder('planter')
    mb.cylinder((0, 0), 0.42, 0.0, 0.12, 'plaster_white', seg=18, r1=0.46, cap_top=False)
    mb.cylinder((0, 0), 0.46, 0.12, 0.55, 'plaster_white', seg=18, r1=0.5, cap_top=False)
    mb.cylinder((0, 0), 0.43, 0.5, 0.52, 'soil', seg=18)
    mb.sphere((0, 0, 0.75), 0.36, 'shrub_green', seg=10, rings=7, sz=0.8)
    return mb


# ----------------------------------------------------------------------------- 자연석 표지석
def stone_marker():
    import random as _r
    rnd = _r.Random(7)
    mb = MeshBuilder('stone_marker')
    seg, rings = 14, 9
    rad = [[1 + rnd.uniform(-0.08, 0.08) for i in range(seg)] for j in range(rings + 1)]
    P = []
    for j in range(rings + 1):
        th = math.pi * j / rings
        row = []
        for i in range(seg):
            ph = 2 * math.pi * i / seg
            r = rad[j][i] * (0.85 + 0.15 * math.cos(ph * 2))
            z = 1.15 * math.cos(th)
            row.append((0.85 * r * math.sin(th) * math.cos(ph), 0.45 * r * math.sin(th) * math.sin(ph), 1.1 + z * (1.0 if z > 0 else 0.95)))
        P.append(row)
    for j in range(rings):
        for i in range(seg):
            k = (i + 1) % seg
            mb.face([P[j][i], P[j + 1][i], P[j + 1][k], P[j][k]], 'stone_marker', smooth='rock')
    mb.box((0, 0, 0.08), (2.0, 1.2, 0.16), 'stone_granite')
    return mb


# ----------------------------------------------------------------------------- 백양로 가운데 초소 (1997 aerial photo)
# Measured in reference/1997_백양로_항공사진.jpg (x 1020 - 1049, y 841 - 906) with the photo's fitted camera, the foot
# on the road profile: the booth stands on the centre line ~132 m in from the gate, 1.4 m across, its yellow lower
# half with black stripes up to 1.46 m, a band of dark windows to 2.68 m, a white cap to 3.16 m and a slim pole with a
# lamp to ~3.6 m.  A red-and-white barrier arm runs west across the outgoing lane from beside it (s ~134) and another
# east across the incoming lane a few metres further on (s ~138); an orange cone stands at the island's nose.
# Frame: origin at the booth's centre on the road, local -Y up the road (north, +s), +X west.  BOOTH_ARMS are the arm
# pivots (x, y, z) in that frame and the side each arm points to; tools/build_campus.py places them the same way.
BOOTH_ISLAND = (-0.85, 0.85, -6.0, 1.6)                  # x0, x1, y0 (north end), y1 (south nose)
BOOTH_ARMS = ((0.82, -1.5, 1.0, 1), (-0.82, -5.5, 1.0, -1))
ARM_LEN = 2.6


def guard_booth():
    mb = MeshBuilder('guard_booth')
    x0, x1, y0, y1 = BOOTH_ISLAND
    kh = 0.18

    def side(ax, ay, bx, by, za, zb, mat, o=0.0, s0=0.0, s1=None):
        """an upright quad on the edge a -> b (corners counter-clockwise seen from above: outward is to the right)"""
        Le = math.hypot(bx - ax, by - ay)
        tx, ty = (bx - ax) / Le, (by - ay) / Le
        s1 = Le if s1 is None else s1
        P = lambda s_, z_: (ax + tx * s_ + ty * o, ay + ty * s_ - tx * o, z_)
        mb.quad(P(s0, za), P(s1, za), P(s1, zb), P(s0, zb), mat)
        return P, Le, math.atan2(ty, tx)

    mb.box(((x0 + x1) / 2, (y0 + y1) / 2, kh / 2), (x1 - x0, y1 - y0, kh), 'concrete', skip=('bottom',))
    # the island kerb painted in yellow and black blocks
    n = int((y1 - y0) / 0.5)
    for k in range(n):
        ya, yb = y0 + k * (y1 - y0) / n, y0 + (k + 1) * (y1 - y0) / n
        m = 'paint_yellow' if k % 2 else 'trim_black'
        side(x1, ya, x1, yb, 0.0, kh, m, o=0.01)                       # west side
        side(x0, yb, x0, ya, 0.0, kh, m, o=0.01)                       # east side
    side(x1, y1, x0, y1, 0.0, kh, 'paint_yellow', o=0.01)              # south nose
    side(x0, y0, x1, y0, 0.0, kh, 'paint_yellow', o=0.01)              # north end
    # the booth, 1.4 x 2.0 m: yellow lower panels with black diagonal stripes, dark windows, a white cap
    w, d = 1.4, 2.0
    z0, zw, zc, zr = kh, 1.46, 2.68, 3.16
    mb.box((0, 0, (z0 + zw) / 2), (w, d, zw - z0), 'paint_yellow')
    corners = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    for i in range(4):
        (ax, ay), (bx, by) = corners[i], corners[(i + 1) % 4]
        P, Le, rz = side(ax, ay, bx, by, zw, zc, 'glass', o=-0.04, s0=0.06, s1=None)
        Lx = lambda s_, z_, o_, ax=ax, ay=ay, bx=bx, by=by, Le=Le: (
            ax + (bx - ax) / Le * s_ + (by - ay) / Le * o_, ay + (by - ay) / Le * s_ - (bx - ax) / Le * o_, z_)
        h = zw - z0
        k = -3
        while k * 0.55 < Le:                         # bands rising to the right, clipped to the panel
            sa = k * 0.55
            quad = [(sa, z0), (sa + 0.22, z0), (sa + 0.22 + h, zw), (sa + h, zw)]
            for edge, keep in ((0.0, lambda s_: s_ >= 0.0), (Le, lambda s_: s_ <= Le)):
                out = []
                for j in range(len(quad)):
                    pa, pb = quad[j], quad[(j + 1) % len(quad)]
                    if keep(pa[0]):
                        out.append(pa)
                    if keep(pa[0]) != keep(pb[0]):
                        t = (edge - pa[0]) / (pb[0] - pa[0])
                        out.append((edge, pa[1] + (pb[1] - pa[1]) * t))
                quad = out
                if not quad:
                    break
            if len(quad) >= 3:
                mb.face([Lx(s_, z_, 0.012) for s_, z_ in quad], 'trim_black')
            k += 1
        for s_ in (0.0, Le / 2, Le):                 # white posts and middle mullion
            mb.box(Lx(s_, (zw + zc) / 2, 0.0), (0.1, 0.1, zc - zw), 'paint_white', rotz=rz)
        mb.box(Lx(Le / 2, zw + 0.03, 0.03), (Le + 0.08, 0.1, 0.06), 'paint_white', rotz=rz)      # sill
    mb.box((0, 0, zc - 0.02), (w, d, 0.04), 'paint_white')
    mb.box((0, 0, (zc + zr) / 2), (w + 0.24, d + 0.24, zr - zc), 'paint_white')                 # the white cap
    mb.box((0, 0, zr + 0.02), (w + 0.1, d + 0.1, 0.04), 'roof_flat', skip=('bottom',))
    mb.cylinder((0.2, 0.3), 0.025, zr, zr + 0.38, 'metal_dark', seg=6)                          # lamp on a pole
    mb.cylinder((0.2, 0.3), 0.09, zr + 0.38, zr + 0.5, 'light_amber', seg=10)
    # a signal box with a red lamp on the south face, as in the photo
    mb.box((0, d / 2 + 0.06, 1.0), (0.36, 0.1, 0.36), 'trim_black')
    side(0.11, d / 2 + 0.115, -0.11, d / 2 + 0.115, 0.89, 1.11, 'light_red')
    # barrier posts: yellow boxes with a black band; the arms (barrier_arm) pivot on their sides
    for ax, ay, az, sd in BOOTH_ARMS:
        px = ax - sd * 0.17
        mb.box((px, ay, (kh + az + 0.12) / 2), (0.3, 0.3, az + 0.12 - kh), 'paint_yellow', skip=('bottom',))
        mb.box((px, ay, az - 0.3), (0.31, 0.31, 0.12), 'trim_black')
    # the cone at the nose
    cx, cy = -0.15, y1 + 0.35
    mb.box((cx, cy, 0.02), (0.38, 0.38, 0.04), 'trim_black')
    mb.cylinder((cx, cy), 0.15, 0.04, 0.7, 'banner_orange', seg=10, r1=0.03)
    mb.cylinder((cx, cy), 0.105, 0.33, 0.45, 'paint_white', seg=10, r1=0.083, cap_top=False)
    return mb


def barrier_arm():
    """The red-and-white barrier arm of the 초소 gates: pivot at the origin, the arm along +X (ARM_LEN), a short
    counterweight behind; web/src/life.js swings it up for cars."""
    mb = MeshBuilder('barrier_arm')
    n = 6
    for k in range(n):
        xa, xb = 0.05 + k * ARM_LEN / n, 0.05 + (k + 1) * ARM_LEN / n
        mb.box(((xa + xb) / 2, 0, 0), (xb - xa, 0.07, 0.08), 'banner_red' if k % 2 == 0 else 'paint_white')
    mb.box((-0.12, 0, 0), (0.24, 0.12, 0.14), 'metal_dark')
    mb.box((0.0, 0, 0), (0.08, 0.14, 0.18), 'trim_black')
    return mb


# ----------------------------------------------------------------------------- 안내판 (campus guide sign)
def sign_board():
    mb = MeshBuilder('sign_board')
    for x in (-0.85, 0.85):
        mb.box((x, 0, 1.0), (0.08, 0.08, 2.0), 'metal_dark')
    mb.box((0, 0, 1.55), (1.9, 0.08, 1.0), 'metal_dark')
    mb.face([(-0.9, -0.045, 1.08), (0.9, -0.045, 1.08), (0.9, -0.045, 2.02), (-0.9, -0.045, 2.02)], 'sign_blue')
    mb.face([(0.9, 0.045, 1.08), (-0.9, 0.045, 1.08), (-0.9, 0.045, 2.02), (0.9, 0.045, 2.02)], 'sign_blue')
    return mb


# ----------------------------------------------------------------------------- 정문
def gate():
    mb = MeshBuilder('gate')
    # main pillars either side of the carriageway, pedestrian pillars further out
    for sx in (-1, 1):
        for (x, w, h) in ((10.3, 1.9, 4.6), (16.8, 1.3, 3.2)):
            cx = sx * x
            mb.box((cx, 0, h / 2 - 0.5), (w, w, h + 1.0), 'stone_granite', mats={'top': 'stone_trim'})
            mb.box((cx, 0, h + 0.62), (w + 0.35, w + 0.35, 0.25), 'stone_trim')
            mb.box((cx, 0, h + 0.9), (w * 0.7, w * 0.7, 0.3), 'stone_trim')
        # low stone walls outwards
        mb.box((sx * 24.5, 0.0, 0.3), (14.0, 0.6, 1.6), 'stone_granite', mats={'top': 'stone_trim'})
    # plaque on the west main pillar (faces south = local -y)
    mb.face([(-11.15, -0.97, 3.2), (-9.45, -0.97, 3.2), (-9.45, -0.97, 3.62), (-11.15, -0.97, 3.62)], 'sign_gate',
            uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # guard booth (수위실)
    bx, by = 20.5, 3.5
    mb.box((bx, by, 1.3), (3.0, 2.6, 2.6), 'plaster_white')
    mb.box((bx, by, 2.75), (3.6, 3.2, 0.3), 'concrete')
    mb.face([(bx - 1.0, by - 1.31, 1.0), (bx + 1.0, by - 1.31, 1.0), (bx + 1.0, by - 1.31, 2.2), (bx - 1.0, by - 1.31, 2.2)], 'glass')
    return mb


def fix_gate_uv(mb):
    pass


# ----------------------------------------------------------------------------- 독수리상
def eagle_statue():
    mb = MeshBuilder('eagle_statue')
    mb.box((0, 0, 0.3), (5.0, 5.0, 1.0), 'stone_granite', mats={'top': 'stone_trim'})
    mb.box((0, 0, 1.2), (3.0, 3.0, 0.8), 'stone_granite', mats={'top': 'stone_trim'})
    mb.cylinder((0, 0), 0.75, 1.6, 12.0, 'stone_trim', seg=24, r1=0.62)
    mb.cylinder((0, 0), 0.95, 12.0, 12.5, 'stone_trim', seg=24)
    mb.cylinder((0, 0), 0.6, 12.5, 12.9, 'bronze', seg=16, r1=0.45)
    z = 13.0
    # body
    mb.sphere((0, 0.1, z + 1.0), 0.55, 'bronze', seg=14, rings=10, sz=1.7)
    mb.sphere((0, -0.35, z + 2.05), 0.33, 'bronze', seg=12, rings=8)            # head
    mb.face([(-0.1, -0.6, z + 2.1), (0.1, -0.6, z + 2.1), (0, -0.95, z + 1.9)], 'bronze')   # beak
    mb.face([(0.1, -0.6, z + 2.1), (0, -0.6, z + 1.95), (0, -0.95, z + 1.9)], 'bronze')
    mb.face([(0, -0.6, z + 1.95), (-0.1, -0.6, z + 2.1), (0, -0.95, z + 1.9)], 'bronze')
    # talons / legs
    for sx in (-0.25, 0.25):
        mb.cylinder((sx, 0.0), 0.11, z - 0.1, z + 0.6, 'bronze', seg=8)
    # tail fan
    for k in range(7):
        a = math.radians(-30 + k * 10)
        mb.face([(0, 0.55, z + 0.4), (math.sin(a) * 0.35, 0.55 + 1.3 * math.cos(a), z - 0.2),
                 (math.sin(a + 0.15) * 0.45, 0.55 + 1.35 * math.cos(a + 0.15), z - 0.18)], 'bronze')
    # wings raised in a V, primaries spread like fingers
    for s in (-1, 1):
        root = Vector((s * 0.35, 0.05, z + 1.5))
        span = 3.2
        prev_top = prev_bot = None
        nseg = 6
        for i in range(nseg + 1):
            t = i / nseg
            x = s * (0.35 + span * t)
            zt = z + 1.6 + 1.9 * t + 0.4 * math.sin(t * math.pi)
            chord = 1.25 * (1 - 0.45 * t)
            top = Vector((x, -0.3 + 0.2 * t, zt))
            bot = Vector((x, -0.3 + 0.2 * t + chord * 0.15, zt - chord))
            if prev_top is not None:
                q = [prev_top, top, bot, prev_bot] if s > 0 else [prev_bot, bot, top, prev_top]
                mb.face(q, 'bronze', smooth='wing%d' % s)
                q2 = [prev_bot, bot, top, prev_top] if s > 0 else [prev_top, top, bot, prev_bot]
                mb.face([p + Vector((0, 0.08, 0)) for p in q2], 'bronze', smooth='wingb%d' % s)
            prev_top, prev_bot = top, bot
        # primaries
        tip = prev_top
        for f in range(5):
            a = math.radians(-10 - f * 14)
            d = Vector((s * math.cos(a), 0, math.sin(a)))
            base = tip + Vector((0, 0.05 * f, -0.18 * f))
            q = [base, base + d * 1.1 + Vector((0, 0, 0.08)), base + d * 1.15, base + Vector((0, 0, -0.16))]
            mb.face(q if s > 0 else q[::-1], 'bronze')
            mb.face(q[::-1] if s > 0 else q, 'bronze')
        # wing-to-body skin
        mb.face([root, Vector((s * 0.35, -0.3, z + 1.6)), Vector((s * 0.35, -0.12, z + 0.35))] if s > 0 else
                [Vector((s * 0.35, -0.12, z + 0.35)), Vector((s * 0.35, -0.3, z + 1.6)), root], 'bronze')
    return mb


# ----------------------------------------------------------------------------- 언더우드 동상
def underwood_statue():
    mb = MeshBuilder('underwood_statue')
    mb.box((0, 0, 0.2), (3.2, 3.2, 0.6), 'stone_granite', mats={'top': 'stone_trim'})
    mb.box((0, 0, 1.6), (1.7, 1.7, 2.4), 'stone_granite', mats={'top': 'stone_trim'})
    mb.box((0, 0, 2.9), (2.0, 2.0, 0.25), 'stone_trim')
    z = 3.02
    # figure in a frock coat
    mb.cylinder((0, 0), 0.32, z, z + 1.1, 'bronze', seg=12, r1=0.28)                    # coat skirt
    mb.cylinder((-0.12, 0), 0.1, z, z + 0.25, 'bronze', seg=8)
    mb.cylinder((0, 0), 0.28, z + 1.1, z + 1.75, 'bronze', seg=12, r1=0.3)             # chest
    mb.cylinder((0, 0), 0.3, z + 1.75, z + 1.85, 'bronze', seg=12, r1=0.12)            # shoulders
    mb.cylinder((0, 0), 0.07, z + 1.85, z + 1.95, 'bronze', seg=8)
    mb.sphere((0, 0, z + 2.08), 0.14, 'bronze', seg=12, rings=8, sz=1.2)
    for s in (-1, 1):
        mb.cylinder((s * 0.34, 0), 0.075, z + 1.05, z + 1.75, 'bronze', seg=8, r1=0.085)
    mb.box((0.36, -0.12, z + 1.12), (0.12, 0.3, 0.38), 'bronze')                        # book
    return mb


# ----------------------------------------------------------------------------- wheel for the motorbike (cars: blender/cars.py)
def _wheel(mb, x, y, r, w):
    seg = 12
    for k in range(seg):
        a0, a1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        p = lambda a, yy: (x + r * math.cos(a), yy, r + r * math.sin(a))
        mb.quad(p(a0, y - w / 2), p(a1, y - w / 2), p(a1, y + w / 2), p(a0, y + w / 2), 'rubber', smooth='whl%d%d' % (int(x * 10), int(y * 10)))
    for yy, sgn in ((y - w / 2, -1), (y + w / 2, 1)):
        pts = [(x + r * math.cos(2 * math.pi * k / seg), yy, r + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
        mb.face(pts if sgn < 0 else pts[::-1], 'rubber')
        hub = [(x + r * 0.6 * math.cos(2 * math.pi * k / seg), yy + sgn * 0.005, r + r * 0.6 * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
        mb.face(hub if sgn < 0 else hub[::-1], 'chrome')


# ----------------------------------------------------------------------------- 오토바이 (delivery scooter)
def motorbike():
    mb = MeshBuilder('motorbike')
    for x in (-0.62, 0.62):
        _wheel(mb, x, 0, 0.27, 0.09)
    mb.box((0, 0, 0.5), (0.9, 0.28, 0.25), 'car_paint')
    mb.box((-0.35, 0, 0.78), (0.6, 0.26, 0.12), 'rubber')                  # seat
    mb.box((0.48, 0, 0.75), (0.14, 0.2, 0.6), 'car_paint')                 # leg shield column
    mb.box((0.55, 0, 1.08), (0.06, 0.62, 0.04), 'metal_dark')               # handlebar
    mb.box((0.6, 0, 0.98), (0.12, 0.16, 0.1), 'light_white')
    mb.box((-0.62, 0, 0.82), (0.36, 0.34, 0.1), 'metal_dark')               # rack
    return mb


# ----------------------------------------------------------------------------- 2003 사진의 소품 (reference/고증.md 3.18)
def bollard():
    """노랑 · 검정 볼라드 (2003_봄_언더우드관_앞길_벚나무.jpg, rows across the road before 언더우드관): a steel post about
    0.85 m high and 13 cm across in yellow and black bands, a black domed cap."""
    mb = MeshBuilder('bollard')
    r = 0.065
    z = -0.1
    for z1, m in ((0.24, 'paint_yellow'), (0.34, 'paint_black'), (0.58, 'paint_yellow'), (0.68, 'paint_black'),
                  (0.8, 'paint_yellow'), (0.85, 'paint_black')):
        mb.cylinder((0, 0), r, z, z1, m, seg=12, cap_top=False)
        z = z1
    mb.sphere((0, 0, 0.85), r, 'paint_black', seg=12, rings=6, sz=0.55)
    return mb


def tent_kiosk():
    """녹색 천막 매점 (2003_가을_연희관_정면.jpg, 2003_봄_언더우드관_앞길_벚나무.jpg): a green canvas tent on slim steel
    poles, 3.2 m by 2.4 m, its gable roof with a short valance; under it a counter at the open front (-Y) with drinks
    crates and boxes on it and stacked crates behind."""
    mb = MeshBuilder('tent_kiosk')
    W, D, he, hr = 3.2, 2.4, 2.15, 2.75
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cylinder((sx * W / 2, sy * D / 2), 0.025, 0.0, he, 'metal', seg=6, cap_top=False)
        mb.cylinder((sx * W / 2, 0), 0.025, 0.0, hr, 'metal', seg=6, cap_top=False)
    for sy in (-1, 1):                                       # the roof slopes and their valances (double-sided cloth)
        mb.face([(-W / 2 - 0.08, sy * (D / 2 + 0.08), he - 0.04), (W / 2 + 0.08, sy * (D / 2 + 0.08), he - 0.04),
                 (W / 2 + 0.08, 0, hr), (-W / 2 - 0.08, 0, hr)][::(1 if sy < 0 else -1)], 'canvas_green')
        mb.face([(-W / 2 - 0.08, sy * (D / 2 + 0.08), he - 0.3), (W / 2 + 0.08, sy * (D / 2 + 0.08), he - 0.3),
                 (W / 2 + 0.08, sy * (D / 2 + 0.08), he - 0.04), (-W / 2 - 0.08, sy * (D / 2 + 0.08), he - 0.04)][::(1 if sy < 0 else -1)],
                'canvas_green')
    for sx in (-1, 1):                                       # the gable ends
        mb.face([(sx * (W / 2 + 0.08), -D / 2 - 0.08, he - 0.04), (sx * (W / 2 + 0.08), D / 2 + 0.08, he - 0.04),
                 (sx * (W / 2 + 0.08), 0, hr)][::sx], 'canvas_green')
    mb.box((0, -D / 2 + 0.45, 0.42), (W - 0.4, 0.6, 0.84), 'wood_dark')               # the counter
    mb.box((0, -D / 2 + 0.45, 0.86), (W - 0.3, 0.7, 0.04), 'paint_white')
    for k, (x, m) in enumerate(((-1.0, 'banner_yellow'), (-0.45, 'paint_blue'), (0.3, 'banner_red'), (0.95, 'plastic_grey'))):
        mb.box((x, -D / 2 + 0.45, 0.88 + 0.13), (0.42, 0.32, 0.26), m)
    for k, x in enumerate((-1.0, -0.5, 0.6, 1.05)):                                    # crates stacked at the back
        for j in range(2 if k % 2 else 3):
            mb.box((x, D / 2 - 0.35, 0.14 + j * 0.29), (0.45, 0.34, 0.27), ('banner_yellow', 'paint_blue', 'banner_red')[(k + j) % 3])
    return mb


def notice_board():
    """게시판 (2003_봄_언더우드관_앞길_벚나무.jpg, by 언더우드관's west wing): a board pasted with posters and 대자보 on two
    wooden posts, braced behind like an easel, under a little green roof; the posters face -Y."""
    mb = MeshBuilder('notice_board')
    W, z0, z1 = 2.0, 0.75, 2.05
    for sx in (-1, 1):
        mb.box((sx * (W / 2 + 0.05), 0, 1.2), (0.09, 0.09, 2.4), 'wood_dark')
        # the easel brace, leaning from the post back to the ground
        rod(mb, (sx * (W / 2 + 0.05), 0.04, 1.9), (sx * (W / 2 + 0.05), 0.95, 0.0), 0.035, 'wood_dark', seg=4)
    mb.box((0, 0.03, (z0 + z1) / 2), (W, 0.05, z1 - z0), 'wood_dark')
    mb.face([(-W / 2 + 0.04, -0.0, z0 + 0.04), (W / 2 - 0.04, -0.0, z0 + 0.04), (W / 2 - 0.04, -0.0, z1 - 0.04),
             (-W / 2 + 0.04, -0.0, z1 - 0.04)], 'notice_posters', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    for sy in (-1, 1):                                      # the little roof
        mb.face([(-W / 2 - 0.2, sy * 0.42, 2.38), (W / 2 + 0.2, sy * 0.42, 2.38), (W / 2 + 0.2, 0, 2.58),
                 (-W / 2 - 0.2, 0, 2.58)][::(1 if sy < 0 else -1)], 'canvas_green')
    return mb


def _obox(mb, c, a, b, ha, hb, hn, mat, uofs=0.0):
    """box centred at c with unit axes a (length), b (width) and n = a x b, half sizes ha, hb, hn; uvs in metres with the
    grain (v) along a, the broad faces offset by uofs across (so that a plank shows one board of a plank texture)"""
    a, b, c = Vector(a), Vector(b), Vector(c)
    n = a.cross(b)
    P = lambda i, j, k: tuple(c + a * (i * ha) + b * (j * hb) + n * (k * hn))
    for k in (-1, 1):                                       # broad faces (+n: the top of a seat plank, the front of a back one)
        q = [(-1, -1), (1, -1), (1, 1), (-1, 1)][::k]
        mb.face([P(i, j, k) for i, j in q], mat, uvs=[(uofs + j * hb, i * ha) for i, j in q])
    for j in (-1, 1):                                       # long edges
        q = [(-1, -1), (-1, 1), (1, 1), (1, -1)][::j]       # (i, k)
        mb.face([P(i, j, k) for i, k in q], mat, uvs=[(uofs + k * hn, i * ha) for i, k in q])
    for i in (-1, 1):                                       # end grain
        q = [(-1, -1), (1, -1), (1, 1), (-1, 1)][::i]       # (j, k)
        mb.face([P(i, j, k) for j, k in q], mat, uvs=[(uofs + j * hb, k * hn) for j, k in q])


def bench():
    """벤치 (2003_봄_백양로끝_핀슨관길_벚나무.jpg: under the cherries by the road to 핀슨관, beside a three-bin green
    recycling box; 2003_봄_언더우드관정원_남쪽계단_벚나무.jpg: seen from behind at the top of the steps, three people to a
    bench): 1.8 m long, a seat of three broad weathered grey planks and a slightly reclined back of three more, on three
    dark frames (a post at each end and one in the middle shows behind the back).  The seat faces -Y; the origin is the
    middle of its footprint (0.62 m deep) on the ground."""
    mb = MeshBuilder('bench')
    mb.xf = Matrix.Translation((0, -0.025, 0))
    L, rec = 1.8, math.radians(12)
    up = Vector((0, math.sin(rec), math.cos(rec)))           # up the back
    back = Vector((0, math.cos(rec), -math.sin(rec)))        # out of the back, behind it
    b0 = Vector((0, 0.17, 0.43))                             # the back planks' mid plane at seat height
    for k, y in enumerate((-0.22, -0.07, 0.08)):             # seat: 13 x 4 cm planks, 2 cm apart, its top 43 cm up
        _obox(mb, (0, y, 0.41), (1, 0, 0), (0, 1, 0), L / 2, 0.065, 0.02, 'wood_bench', uofs=0.25 + 0.21 * k)
    for k, d in enumerate((0.12, 0.26, 0.40)):               # back: 12 x 3.5 cm planks, its top 88 cm up
        _obox(mb, b0 + up * d, (1, 0, 0), up, L / 2, 0.06, 0.0175, 'wood_bench', uofs=0.95 + 0.21 * k)
    post0 = b0 + back * 0.0425                               # the posts' centre line, behind the back planks
    for x in (-0.72, 0.0, 0.72):
        mb.box((x, -0.22, 0.195), (0.05, 0.06, 0.39), 'frame_dark')                 # front leg
        mb.box((x, -0.025, 0.36), (0.05, 0.49, 0.06), 'frame_dark')                 # seat bearer
        d0, d1 = -0.43 / up.z, 0.47                                                  # rear leg and back post, one piece
        _obox(mb, post0 + up * ((d0 + d1) / 2) + Vector((x, 0, 0)), up, (1, 0, 0), (d1 - d0) / 2, 0.025, 0.025, 'frame_dark')
    return mb


def _ellipsoid(mb, c, rx, ry, rz, mat, rnd, seg=12, rings=8, noise=0.06, tag=None):
    tag = tag or 'ell%d' % len(mb.faces)
    P = []
    for j in range(rings + 1):
        th = math.pi * j / rings
        row = []
        for i in range(seg):
            ph = 2 * math.pi * i / seg
            n = 1 + noise * math.sin(ph * 3 + j * 1.7 + rnd.uniform(0, 0.6)) * math.sin(th * 4)
            row.append((c[0] + rx * n * math.sin(th) * math.cos(ph), c[1] + ry * n * math.sin(th) * math.sin(ph), c[2] + rz * n * math.cos(th)))
        P.append(row)
    for j in range(rings):
        for i in range(seg):
            k = (i + 1) % seg
            mb.face([P[j][i], P[j + 1][i], P[j + 1][k], P[j][k]], mat, smooth=tag)


def haetae():
    """돌 해태상 (2003_봄_백양로끝_핀슨관길_벚나무.jpg: a pair at the edge of the drive up to 핀슨관): a weathered granite
    해태 about a metre high sitting up on its haunches, forelegs straight, a big curly-maned head with a single knob of a
    horn, on a plain granite plinth 0.5 m high and 1.8 m long; it looks along -Y."""
    rnd = random.Random(1997)
    mb = MeshBuilder('haetae')
    mb.box((0, 0.05, 0.25), (0.95, 1.8, 0.62), 'stone_haetae', skip=('bottom',))
    mb.box((0, 0.05, 0.53), (1.02, 1.86, 0.06), 'stone_haetae', skip=('bottom',))
    z = 0.56
    m = 'stone_haetae'
    E = lambda c, rx, ry, rz, **kw: _ellipsoid(mb, (c[0], c[1], c[2] + z), rx, ry, rz, m, rnd, **kw)
    E((0, 0.36, 0.3), 0.34, 0.46, 0.3)                     # haunches
    E((0, 0.02, 0.46), 0.3, 0.42, 0.32)                    # the back, low, running forward
    E((0, -0.3, 0.6), 0.29, 0.27, 0.38)                    # chest, sitting up
    E((0, -0.5, 0.94), 0.27, 0.27, 0.25)                   # head
    E((0, -0.74, 0.87), 0.17, 0.14, 0.13)                  # muzzle
    E((0, -0.8, 0.8), 0.13, 0.08, 0.06, noise=0.02)        # jaw, the mouth line under it
    for sx in (-1, 1):
        E((sx * 0.2, -0.47, 1.02), 0.13, 0.17, 0.18)       # curls of the mane round the face
        E((sx * 0.23, -0.34, 0.82), 0.11, 0.15, 0.15)
        E((sx * 0.1, -0.72, 0.98), 0.065, 0.06, 0.06, noise=0.0)  # eyes bulging over the muzzle
        E((sx * 0.16, -0.5, 0.22), 0.1, 0.1, 0.26)         # forelegs
        E((sx * 0.16, -0.62, 0.04), 0.1, 0.15, 0.06)       # front paws
        E((sx * 0.29, 0.1, 0.07), 0.12, 0.2, 0.08)         # hind paws
        E((sx * 0.3, 0.38, 0.3), 0.08, 0.34, 0.24)         # flanks of the haunches
    E((0, -0.44, 1.17), 0.19, 0.16, 0.09)                  # mane over the crown
    E((0, -0.52, 1.26), 0.05, 0.05, 0.08, noise=0.0)       # the horn
    E((0, 0.8, 0.52), 0.1, 0.09, 0.22)                     # tail curled up the back
    E((0, 0.72, 0.74), 0.12, 0.1, 0.08)
    return mb
