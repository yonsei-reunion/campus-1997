"""Street furniture, statues, the main gate, 1990s Korean cars and pedestrians."""
import math, random
from mathutils import Matrix, Quaternion, Vector
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


# ----------------------------------------------------------------------------- 네 구 가로등 (중앙도서관 앞, 1997 photo)
def lamp_quad():
    """The lamps in the shrubs before 중앙도서관 (reference/1997_중앙도서관.jpg): a dark brown post with a white band
    at eye height, a cross of four short arms at the top and a white globe hanging under the tip of each, a finial
    over the middle; the globes about 4 m up."""
    mb = MeshBuilder('lamp_quad')
    mb.box((0, 0, 0.25), (0.46, 0.46, 0.5), 'metal_dark')
    mb.cylinder((0, 0), 0.11, 0.5, 4.45, 'metal_dark', seg=10, r1=0.07)
    mb.cylinder((0, 0), 0.115, 1.75, 1.95, 'plaster_white', seg=10)
    for a in range(4):
        c, s = round(math.cos(a * math.pi / 2)), round(math.sin(a * math.pi / 2))
        mb.box((c * 0.29, s * 0.29, 4.32), (0.58 if c else 0.05, 0.05 if c else 0.58, 0.05), 'metal_dark')
        mb.cylinder((c * 0.56, s * 0.56), 0.035, 4.06, 4.33, 'metal_dark', seg=8)
        mb.sphere((c * 0.56, s * 0.56, 3.86), 0.22, 'globe', seg=14, rings=10)
    mb.cylinder((0, 0), 0.05, 4.45, 4.62, 'metal_dark', seg=8)
    mb.sphere((0, 0, 4.66), 0.07, 'metal_dark', seg=8, rings=6)
    return mb


# ----------------------------------------------------------------------------- 백양로 양팔 가로등 (1997 aerial photo)
def lamp_arm():
    """Two-armed street lamp with flat box luminaires.  Local +X points away from the road (over the sidewalk),
    -X over the carriageway.  Standing in the verge (reference/고증.md 2.3), the head on the road's side over the kerb
    and the other over the sidewalk: in photo A the heads 1.2 - 1.3 m from the pole on the road's side, 1.4 - 1.9 m on
    the sidewalk's (1.95 and 1.3 m before, when the pole stood on the sidewalk)"""
    mb = MeshBuilder('lamp_arm')
    mb.box((0, 0, 0.3), (0.42, 0.42, 0.6), 'metal_dark')
    mb.cylinder((0, 0), 0.11, 0.6, 7.6, 'metal_dark', seg=10, r1=0.065)
    for sx, L_ in ((-1, 1.05), (1, 1.4)):
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
# The booth of the 1996 - 2000 autumn photo by 아펜젤러관's south gable (2025 기념문집 22쪽, reference/문집/
# 2025_22쪽_가을_아펜젤러관_남쪽_박공벽과_공중전화_부스.jpg; reference/고증/3.5.6): a sky-blue painted
# frame whose front is a hoop with rounded top corners, under its top a royal-blue sign band with white lettering either
# side of a round mark and a pale strip below it, the front open (no door), each side two panes of glass over a rail at
# waist height with a narrower blue band along its top.  Sizes: 1.1 m across, 1.0 m deep, 2.4 m high (the photo: its
# top 0.62 m over the camera's eye and 0.7 m over the head of the man queueing beside it, the front 94 px of 1000 seen
# 40 degrees off at 112 px a metre; the December 2010 roadview of the same booth face on: 0.46 times as wide as high;
# the 1996 - 1999 scans' box: 2.1 - 2.3 m, its top a metre square).  The parts' heights (2026-11-24) are the photo's
# rows under the booth's top at 112 px a metre (the booth 10.5 m from the camera: tools/appen97.py); the first ones
# were read at 97 px a metre, the foot taken to show where the hedge hides its lowest 0.45 m.  web/src/main.js walls
# the walker by the same numbers (BOOTH_WALLS there).
BOOTH_W, BOOTH_D, BOOTH_H = 1.10, 1.00, 2.40
BOOTH_PHONE_Y = BOOTH_D / 2 - 0.07          # the phone's back on the board of the back wall (build.py hangs it there)


def _booth_hoop(mb, y, w, h, t, dy, mat, r=0.14, ri=0.05, seg=5):
    """A portal frame in the XZ plane at depth y (dy thick): two posts t wide and a head, the top corners rounded
    (outer radius r, inner ri)."""
    def path(hw, top, rad):
        pts = [(-hw, 0.0)]
        for k in range(seg + 1):
            a = math.pi - k * (math.pi / 2) / seg
            pts.append((-hw + rad + rad * math.cos(a), top - rad + rad * math.sin(a)))
        for k in range(seg + 1):
            a = math.pi / 2 - k * (math.pi / 2) / seg
            pts.append((hw - rad + rad * math.cos(a), top - rad + rad * math.sin(a)))
        pts.append((hw, 0.0))
        return pts
    out, inn = path(w / 2, h, r), path(w / 2 - t, h - t, ri)
    y0, y1 = y - dy / 2, y + dy / 2
    for i in range(len(out) - 1):
        (ax, az), (bx, bz), (cx, cz), (ex, ez) = out[i], out[i + 1], inn[i + 1], inn[i]
        mb.face([(ax, y0, az), (ex, y0, ez), (cx, y0, cz), (bx, y0, bz)], mat)             # front (-Y)
        mb.face([(ax, y1, az), (bx, y1, bz), (cx, y1, cz), (ex, y1, ez)], mat)             # back
        mb.face([(ax, y0, az), (bx, y0, bz), (bx, y1, bz), (ax, y1, az)], mat)             # outer
        mb.face([(ex, y0, ez), (ex, y1, ez), (cx, y1, cz), (cx, y0, cz)], mat)             # inner


def payphone_booth():
    """공중전화 부스 (the 1996 - 2000 photo above); the phone itself, Poly Haven's Korean payphone, is added in
    build.py.  The open front faces -Y, the origin is the middle of the floor."""
    mb = MeshBuilder('payphone_booth')
    w, d, h = BOOTH_W, BOOTH_D, BOOTH_H
    t = 0.09                                    # the frame's width
    F, G, S = 'booth_skyblue', 'glass_door', 'payphone_sign'
    yf, yb = -d / 2 + 0.04, d / 2 - 0.04        # the front and the back hoops' middles
    mb.box((0, 0, 0.012), (w - 0.02, d - 0.02, 0.024), 'metal_dark')                   # floor plate
    # a concrete footing under it, down into the ground: where the ground falls away under a corner (the booth stands
    # level at the height of the ground under its middle) the footing shows instead of a gap
    mb.box((0, 0, -0.2), (w + 0.06, d + 0.06, 0.4), 'concrete', skip=('bottom',))
    _booth_hoop(mb, yf, w, h, t, 0.08, F)
    _booth_hoop(mb, yb, w, h, t, 0.08, F)
    # the roof: a shallow cap between the hoops, its long edges the sides' top rails; a lamp under it
    mb.box((0, 0, h - 0.045), (w, d - 0.16, 0.09), F)
    mb.box((0, 0.05, h - 0.115), (0.42, 0.2, 0.05), 'light_white')
    # the front's sign band and the pale strip under it (the doorway's head 2.04 m up)
    z1 = h - t
    sb, ps = 0.20, 0.07                         # the sign band's and the pale strip's heights
    mb.face([(-w / 2 + t, yf - 0.02, z1 - sb), (w / 2 - t, yf - 0.02, z1 - sb), (w / 2 - t, yf - 0.02, z1),
             (-w / 2 + t, yf - 0.02, z1)], S, uvs=[(0, 1 / 3), (1, 1 / 3), (1, 1), (0, 1)])
    mb.box((0, yf + 0.005, z1 - sb / 2), (w - 2 * t, 0.05, sb), F, skip=('front',))
    mb.box((0, yf, z1 - sb - ps / 2), (w - 2 * t, 0.06, ps), F)
    # the sides: a blue band along the top, two panes over a rail 1.0 - 1.09 m up, a sill; thin posts at the panes' ends
    r0, r1, s1 = 1.0, 1.09, 0.13                # the rail, the sill's top
    p1 = z1 - 0.23                              # the upper pane's top
    ys = (yf + 0.04, yb - 0.04)
    L = ys[1] - ys[0]
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.03)
        xo = sx * (w / 2 - 0.004)
        q = [(xo, ys[0], z1 - 0.15), (xo, ys[1], z1 - 0.15), (xo, ys[1], z1 - 0.02), (xo, ys[0], z1 - 0.02)]
        mb.face(q if sx > 0 else q[::-1], S, uvs=[(0, 0), (1, 0), (1, 1 / 3), (0, 1 / 3)] if sx > 0 else [(0, 1 / 3), (1, 1 / 3), (1, 0), (0, 0)])
        mb.box((x, 0, z1 - 0.085), (0.05, L, 0.17), F, skip=('right',) if sx > 0 else ('left',))
        mb.box((x, 0, z1 - 0.2), (0.05, L, 0.06), F)                                   # under the band
        mb.box((x, 0, (r0 + r1) / 2), (0.05, L, r1 - r0 + 0.02), F)                    # the rail
        mb.box((x, 0, s1 / 2), (0.05, L, s1), F)                                       # the sill
        mb.box((x, 0, (r1 + p1) / 2), (0.012, L, p1 - r1 + 0.03), G)                   # upper pane
        mb.box((x, 0, (s1 + r0) / 2), (0.012, L, r0 - s1 + 0.03), G)                   # lower pane
    # the back: the same rails and panes, and a board in the middle the phone hangs on
    xb = w - 2 * t
    mb.box((0, yb, z1 - 0.115), (xb, 0.05, 0.23), F)
    mb.box((0, yb, (r0 + r1) / 2), (xb, 0.05, r1 - r0 + 0.02), F)
    mb.box((0, yb, s1 / 2), (xb, 0.05, s1), F)
    mb.box((0, yb, (r1 + p1) / 2), (xb, 0.012, p1 - r1 + 0.03), G)
    mb.box((0, yb, (s1 + r0) / 2), (xb, 0.012, r0 - s1 + 0.03), G)
    mb.box((0, yb - 0.015, 1.3), (0.5, 0.03, 0.88), F)                                 # the phone's board
    mb.box((0, yb - 0.17, 0.87), (0.5, 0.28, 0.03), 'metal')                           # shelf under the phone
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


# ----------------------------------------------------------------------------- 백양로 주차 요금정산소 (1996 - 1999)
# The campus's parking toll booth on 백양로's centre line (reference/고증/2.3.2 「정산소와 방지턱」): the 1996 - 1999 scans
# give its place (s 154.6, tools/build_campus.py I219_*), a flat roof 3.0 x 1.5 m some 2.5 m over the road and the arms
# lowered at its north-east and south-west corners; the autumn 1997 school-site photo (reference/학교홈페이지/bakyang.jpg)
# its make: yellow walls, a big dark window over a yellow lower panel, a flat roof with a white sign board on a post, a
# yellow ticket post at its south-east corner for the northbound lane and the southbound arm's post at the south-west
# corner on a yellow frame.  On a low island with a kerb in yellow and black blocks.
# Frame: origin at the booth's centre on the road, local -Y up the road (north, +s), +X west.  BOOTH_ARMS are the arm
# pivots (x, y, z) in that frame and the side each arm points to; tools/build_campus.py places them the same way.
BOOTH_ISLAND = (-0.95, 0.95, -2.75, 2.55)                # x0, x1, y0 (north end), y1 (south nose)
BOOTH_ARMS = ((0.82, 2.2, 1.0, 1), (-0.82, -2.45, 1.0, -1))
ARM_LEN = 2.6


def guard_booth():
    mb = MeshBuilder('guard_booth')
    x0, x1, y0, y1 = BOOTH_ISLAND
    kh = 0.15

    def side(ax, ay, bx, by, za, zb, mat, o=0.0):
        """an upright quad on the edge a -> b (corners counter-clockwise seen from above: outward is to the right)"""
        Le = math.hypot(bx - ax, by - ay)
        tx, ty = (bx - ax) / Le, (by - ay) / Le
        mb.quad((ax + ty * o, ay - tx * o, za), (bx + ty * o, by - tx * o, za), (bx + ty * o, by - tx * o, zb),
                (ax + ty * o, ay - tx * o, zb), mat)

    mb.box(((x0 + x1) / 2, (y0 + y1) / 2, kh / 2), (x1 - x0, y1 - y0, kh), 'concrete', skip=('bottom',))
    # the island kerb painted in yellow and black blocks
    n = int(round((y1 - y0) / 0.5))
    for k in range(n):
        ya, yb = y0 + k * (y1 - y0) / n, y0 + (k + 1) * (y1 - y0) / n
        m = 'paint_yellow' if k % 2 else 'trim_black'
        side(x1, ya, x1, yb, 0.0, kh, m, o=0.01)                       # west side
        side(x0, yb, x0, ya, 0.0, kh, m, o=0.01)                       # east side
    side(x1, y1, x0, y1, 0.0, kh, 'paint_yellow', o=0.01)              # south nose
    side(x0, y0, x1, y0, 0.0, kh, 'paint_yellow', o=0.01)              # north end
    # the booth, 1.5 x 3.0 m and 2.5 m over the road: a yellow lower panel, dark glass all round between yellow
    # corner posts and mullions, a yellow head band and a flat roof slab
    w, d = 1.5, 3.0
    zp, zw, zh, zr = 1.05, 2.15, 2.36, 2.48
    mb.box((0, 0, (kh + zp) / 2), (w, d, zp - kh), 'paint_yellow', skip=('bottom',))
    mb.box((0, 0, (zp + zw) / 2), (w - 0.06, d - 0.06, zw - zp), 'glass_car', skip=('bottom', 'top'))
    mb.box((0, 0, (zp + zw) / 2), (w - 0.3, d - 0.3, zw - zp), 'trim_black', skip=('bottom', 'top'))     # (the dark inside)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * (w / 2 - 0.06), sy * (d / 2 - 0.06), (zp + zw) / 2), (0.13, 0.13, zw - zp), 'paint_yellow', skip=('bottom', 'top'))
        mb.box((sx * (w / 2 - 0.04), 0, (zp + zw) / 2), (0.09, 0.1, zw - zp), 'paint_yellow', skip=('bottom', 'top'))
    mb.box((0, 0, zp + 0.025), (w + 0.04, d + 0.04, 0.05), 'paint_yellow')                     # sill
    mb.box((0, 0, (zw + zh) / 2), (w, d, zh - zw), 'paint_yellow', skip=('bottom', 'top'))
    mb.box((0, 0, (zh + zr) / 2), (w + 0.16, d + 0.16, zr - zh), 'paint_yellow')                # the roof slab
    mb.box((0, 0, zr + 0.01), (w + 0.12, d + 0.12, 0.02), 'roof_metal', skip=('bottom',))
    # on the roof: a white sign board on a post over the south-west corner, a slim white pole at the east
    mb.cylinder((0.45, 1.2), 0.03, zr, zr + 0.45, 'paint_white', seg=6)
    mb.box((0.45, 1.25, zr + 0.62), (0.55, 0.06, 0.4), 'paint_white')
    mb.cylinder((-0.5, 0.9), 0.025, zr, zr + 0.75, 'paint_white', seg=6)
    # the ticket post before the booth's south-east corner, its blue plate towards the northbound lane (east, -X)
    tx_, ty_ = -0.62, 1.95
    mb.box((tx_, ty_, kh + 0.62), (0.4, 0.36, 1.24), 'paint_yellow', skip=('bottom',))
    mb.box((tx_ - 0.205, ty_, kh + 1.0), (0.02, 0.26, 0.12), 'sign_blue')
    mb.box((tx_ - 0.205, ty_, kh + 0.75), (0.02, 0.16, 0.1), 'trim_black')
    # barrier posts: yellow boxes with a black band; the arms (barrier_arm) pivot on their sides.  The southbound one
    # stands on a low yellow frame of tubes (the photo)
    for ax, ay, az, sd in BOOTH_ARMS:
        px = ax - sd * 0.17
        mb.box((px, ay, (kh + az + 0.12) / 2), (0.3, 0.3, az + 0.12 - kh), 'paint_yellow', skip=('bottom',))
        mb.box((px, ay, az - 0.3), (0.31, 0.31, 0.12), 'trim_black')
        if sd > 0:
            for dy in (-0.22, 0.22):
                mb.box((px - 0.1, ay + dy, kh + 0.06), (0.7, 0.06, 0.06), 'paint_yellow')
            mb.box((px - 0.42, ay, kh + 0.06), (0.06, 0.5, 0.06), 'paint_yellow')
    return mb


def parking_booth():
    """The parking booth of the side road inside the gate (1997 aerial photo, its left edge: taken for the front of a blue
    bus before).  A booth about 1.7 x 2.3 m and 2.5 m high with a rounded glazed front, blue frames, a white skirt and a
    white cap, on a low island between the lanes; at the island's nose a yellow barrier box with its red-and-white arm
    raised and a yellow ticket machine (the 2010 roadview has the side road's booth and barriers laid out the same way).
    Frame: the front (towards 백양로) is -Y, +X is the booth's left (north side of the road); origin at the island's
    centre."""
    mb = MeshBuilder('parking_booth')
    kh = 0.15
    ix0, ix1, iy0, iy1 = -1.3, 1.3, -2.5, 2.3                     # the island (nose at -Y)
    mb.box(((ix0 + ix1) / 2, (iy0 + iy1) / 2, kh / 2), (ix1 - ix0, iy1 - iy0, kh), 'concrete',
           mats={'sides': 'paint_yellow'}, skip=('bottom',))

    def rrect(cx, cy, w, d, rf, rb, n=5):
        """a rounded rectangle, counter-clockwise from above: front corners (-Y) radius rf, back corners rb"""
        pts = []
        for (qx, qy, r, a0) in ((cx + w / 2, cy - d / 2, rf, -90), (cx + w / 2, cy + d / 2, rb, 0),
                                (cx - w / 2, cy + d / 2, rb, 90), (cx - w / 2, cy - d / 2, rf, 180)):
            ox, oy = qx - math.copysign(r, qx - cx), qy - math.copysign(r, qy - cy)
            for k in range(n + 1):
                a = math.radians(a0 + 90 * k / n)
                pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
        return pts

    bx, by, w, d = -0.25, 0.75, 1.7, 2.3
    body = rrect(bx, by, w, d, 0.55, 0.15)
    cap = rrect(bx, by, w + 0.24, d + 0.24, 0.67, 0.27)
    z0, zs, zb, zw, zh, zc = kh, 1.0, 1.1, 2.08, 2.2, 2.45
    mb.prism(body, z0, zs, 'paint_white')                         # white skirt
    mb.prism(body, zs, zb, 'paint_blue')                          # blue sill band
    mb.prism(body, zb, zw, 'glass')                               # the glazing all round
    mb.prism(body, zw, zh, 'paint_blue')                          # blue head band
    mb.prism(cap, zh, zc, 'paint_white', mat_top='roof_flat', mat_bottom='paint_white')
    # blue mullions: at the ends of the front's curves, mid-sides and the back corners
    for i in (0, 5, 6, 11, 12, 17, 18, 23):
        px, py = body[i]
        mb.box((px, py, (zb + zw) / 2), (0.08, 0.08, zw - zb), 'frame_blue')
    for px, py in ((bx + w / 2, by + 0.35), (bx - w / 2, by + 0.35)):
        mb.box((px, py, (zb + zw) / 2), (0.08, 0.08, zw - zb), 'frame_blue')
    # the barrier box at the nose (left of the booth, on the centre line) and its arm, raised
    hx, hy = 1.0, -1.6
    mb.box((hx, hy, kh + 0.5), (0.3, 0.32, 1.0), 'paint_yellow', skip=('bottom',))
    mb.box((hx, hy, kh + 0.82), (0.31, 0.33, 0.1), 'trim_black')
    piv = (hx + 0.17, hy, kh + 0.9)
    ang, L, n, r = math.radians(68), 2.8, 7, 0.035
    ca, sa = math.cos(ang), math.sin(ang)
    for k in range(n):                                            # the raised arm in red and white lengths, tilted
        t0, t1 = 0.05 + k * L / n, 0.05 + (k + 1) * L / n
        V = [(piv[0] + t * ca - v * sa, piv[1] + u, piv[2] + t * sa + v * ca)
             for t in (t0, t1) for u, v in ((-r, -r), (r, -r), (r, r), (-r, r))]
        m = 'paint_white' if k % 2 else 'light_red'
        for a_, b_, c_, d_ in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7), (3, 2, 1, 0)):
            mb.face([V[a_], V[b_], V[c_], V[d_]], m)
    # a pole with a white sign board at the nose, and the yellow ticket machine ahead of the booth
    mb.cylinder((1.15, -2.25), 0.04, kh, 2.7, 'metal_dark', seg=8)
    mb.box((1.15, -2.3, 2.45), (0.55, 0.04, 0.4), 'paint_white')
    mb.box((-0.35, -2.05, kh + 0.62), (0.42, 0.34, 1.24), 'paint_yellow', skip=('bottom',))
    mb.box((-0.35, -2.23, kh + 0.85), (0.3, 0.02, 0.36), 'trim_black')
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
# The gate as it stood in August 1996 (reference/1996_정문_철둑에서.jpg, seen square on from the rail bank) with the stones'
# make from the April 2011 roadview, which still had the east pillar: reference/고증/4.8.1_정문의_생김새.md.
# Local frame: x east along the gate's line from the carriageway's middle, y north (inside), front = -y, z from the
# ground at the gate's middle.  Along the line (m): a low rubble wall with an iron fence and stone piers, the lodge
# (-19.18 .. -12.18), the west walk's outer pillar, the walk (5.0 m), the west main pillar, the carriageway (8.8 m), the
# east main pillar, the walk, its outer pillar and the white wall, then the low wall again (turning south-east).  The main pillars stand
# on 백양로's verges (ROAD verge, 4.2 .. 5.65 m off the centre line) and the walks pass between them and the outer ones.
# The main pillars and the lodge run far back from the line (the July 1997 vertical photos: both pillars 4.3 .. 5.0 m,
# the lodge's roof 8 .. 10 m; the 1996 photo's roof and the 2008 skyview say 10 m): 고증 4.8.1 「깊이」.
# tools/build_campus.py GATE_PARTS keeps the shrubs off these footprints.
GATE_FRONT = -0.3            # the pillars' and the lodge's south faces, from the gate's line
GATE_MAIN = dict(u=5.1, w=1.46, d=4.8, fin=0.28, h=4.9, h_back=4.5, core=4.45)    # (10.2 m apart: the July 1997 scans' 10.25, 고증 4.8.1;
#   front: slab 0.28 · rubble 0.90 · slab 0.28 m in the 1600 px copy of the August 1996 photo)
# the walks' outer pillars stand symmetric, 11.5 m either side (the scans' tops; the lodge stays against the west one,
# as in the 1996 photo: 고증 4.8.1 「바깥 기둥과 흰 담을 원본 스캔에서 함께」)
GATE_SIDE = dict(u=-11.5, w=1.35, d=3.0, fin=0.34, h=3.75, h_back=3.45, core=3.4)
GATE_LODGE = dict(u0=-19.18, u1=-12.18, d=10.0, h=2.8, solid=3.75)
GATE_EAST = dict(u=11.5, w=1.05, d=3.6, fin=0.3, h=3.7, h_back=3.45, core=3.4)    # the east walk's outer pillar: a narrow core
# the white wall's line (u, v): out of the east outer pillar's front corner at 42 deg to the gate's line, then along it
# 3.3 m in front of it (the July 1997 scans at its coping's height, 고증 4.8.1 「동쪽 흰 담의 자리」); a bay each way
GATE_WALL = dict(pts=[(12.19, -0.36), (15.49, -3.31), (20.14, -3.31)], h=2.7, t=0.35)
GATE_END = 31.5              # the low wall's ends (tools/build_campus.py reads the same length for the ground)
GATE_TURN = dict(u0=20.64, v0=-3.41, to=(34.14, -10.51))   # the east low wall: south-east from the white wall's end (tools/gate_town.py EAST_TURN)
# ... on to 성산로's sidewalk 18.8 m along that line, its four piers' middles along it (the 1996-12 · 1998 · 1999 scans,
# the piers' white posts at their top's height: 4.37 m apart, 고증 4.8.1 「동쪽 낮은 담의 칸 나눔」)
GATE_TURN_LEN = 18.8
GATE_TURN_PIERS = (3.65, 8.02, 12.39, 16.76)
GATE_LEAF = 2.8              # the iron leaves' height


def _gate_ground():
    """the ground under a point of the gate's frame, from the level of its middle"""
    import common
    st = common.CAMPUS['statues']['gate']
    cs, sn = math.cos(st['rot']), math.sin(st['rot'])
    return lambda u, v=0.0: common.ground(st['pos'][0] + u * cs - v * sn, st['pos'][1] + u * sn + v * cs) - st['h']


def _gate_grille(mb, p0, p1, z0, z1, step=0.13, rails=(0.06, 0.5)):
    """an iron leaf or a run of fence from p0 to p1 (x, y): square uprights between rails, an end post either side"""
    (x0, y0), (x1, y1) = p0, p1
    ln, a = math.hypot(x1 - x0, y1 - y0), math.atan2(y1 - y0, x1 - x0)
    cx, cy, h = (x0 + x1) / 2, (y0 + y1) / 2, z1 - z0
    for f in rails + (1.0 - rails[0],):
        mb.box((cx, cy, z0 + h * f), (ln, 0.045, 0.05), 'trim_black', rotz=a)
    n = max(2, round(ln / step))
    for k in range(n + 1):
        f = k / n
        t = 0.05 if k in (0, n) else 0.024
        mb.box((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, z0 + h / 2), (t, t, h), 'trim_black', rotz=a, skip=('bottom',))


def _gate_pillar(mb, gz, u, w, d, fin, h, h_back, core, vent=()):
    """a dark rubble core between two granite slabs: the slabs stand over the core and run back the pillar's whole
    depth, their tops falling to the north; the rubble shows at both ends.  No lantern on the core's face: the 1600 px
    copy of the August 1996 photo has bare rubble there top to bottom on both main pillars (the iron lanterns are the
    2011 roadview's).  vent: the sides whose slab has the dark recess over the folded leaf (the 1995 photos: on the
    walk's side as on the carriageway's)."""
    y0, y1 = GATE_FRONT, GATE_FRONT + d
    z = gz(u, (y0 + y1) / 2)
    zb = z - 0.6
    for s in (-1, 1):
        x0, x1 = sorted((u + s * w / 2, u + s * (w / 2 - fin)))
        ring, top = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], [h, h, h_back, h_back]
        for i in range(4):
            j = (i + 1) % 4
            mb.face([(*ring[i], zb), (*ring[j], zb), (*ring[j], z + top[j]), (*ring[i], z + top[i])], 'gate_granite')
        mb.face([(*ring[i], z + top[i]) for i in range(4)], 'gate_granite')
    mb.box((u, (y0 + y1) / 2, (zb + z + core) / 2), (w - 2 * fin, d - 0.2, z + core - zb), 'gate_rubble', skip=('left', 'right', 'bottom'))
    for sd in vent or ():
        mb.box((u + sd * (w / 2 + 0.006), y0 + d * 0.54, z + 3.15), (0.012, 2.1, 0.6), 'void_black', skip=('bottom',))


def _gate_pier(mb, gz, u0, u1, posts=(True, True), h=2.1, t=0.5):
    """a pier of the low wall: a rubble panel between two slim granite posts (1.7 m across with both)"""
    z = gz((u0 + u1) / 2)
    a, b = u0 + (0.2 if posts[0] else 0.0), u1 - (0.2 if posts[1] else 0.0)
    mb.box(((a + b) / 2, 0, z + h / 2 - 0.3), (b - a, t - 0.1, h + 0.6), 'gate_rubble', mats={'top': 'gate_granite'}, skip=('bottom',))
    mb.box(((a + b) / 2, 0, z + h + 0.03), (b - a + 0.02, t, 0.06), 'gate_granite')            # the coping
    for on, x in zip(posts, (u0 + 0.1, u1 - 0.1)):
        if on:
            mb.box((x, 0, z + (h + 0.1) / 2 - 0.3), (0.2, t, h + 0.7), 'gate_granite', skip=('bottom',))


def _gate_fence(mb, gz, u0, u1, plinth=0.5, top=1.9):
    """a bay of the low wall: a rubble plinth with a granite coping and the iron fence on it, stepped with the ground"""
    n = max(1, round(abs(u1 - u0) / 3.2))
    for k in range(n):
        a, b = u0 + (u1 - u0) * k / n, u0 + (u1 - u0) * (k + 1) / n
        z = min(gz(a), gz(b))
        mb.box(((a + b) / 2, 0, z + plinth / 2 - 0.4), (abs(b - a), 0.4, plinth + 0.8), 'gate_rubble', skip=('bottom', 'top'))
        mb.box(((a + b) / 2, 0, z + plinth + 0.04), (abs(b - a), 0.46, 0.08), 'gate_granite')
        _gate_grille(mb, (min(a, b) + 0.03, 0), (max(a, b) - 0.03, 0), z + plinth + 0.08, z + top, rails=(0.05, 0.85))


def gate():
    mb = MeshBuilder('gate')
    gz = _gate_ground()
    M, S, L, T, W = GATE_MAIN, GATE_SIDE, GATE_LODGE, GATE_EAST, GATE_WALL
    f0 = GATE_FRONT
    # ---- the two main pillars and the walks' outer ones; a dark recess high on either side over the folded leaves
    # (the 1995 photos)
    for s in (-1, 1):
        _gate_pillar(mb, gz, s * M['u'], M['w'], M['d'], M['fin'], M['h'], M['h_back'], M['core'], vent=(-1, 1))
        # the carriageway's leaves folded back along the slab (two a side) and the walk's one behind the other slab,
        # under the recesses
        z = gz(s * M['u'], 2.4)
        xin, xout = s * (M['u'] - M['w'] / 2), s * (M['u'] + M['w'] / 2)
        for k in (1, 2):
            _gate_grille(mb, (xin - s * 0.07 * k, f0 + 1.5), (xin - s * 0.07 * k, f0 + 1.5 + 2.15), z + 0.08, z + GATE_LEAF)
        _gate_grille(mb, (xout + s * 0.07, f0 + 1.5), (xout + s * 0.07, f0 + 1.5 + 2.25), z + 0.08, z + GATE_LEAF)
    _gate_pillar(mb, gz, S['u'], S['w'], S['d'], S['fin'], S['h'], S['h_back'], S['core'])
    _gate_pillar(mb, gz, T['u'], T['w'], T['d'], T['fin'], T['h'], T['h_back'], T['core'])
    # ---- the notice board on its two legs before the east pillar (both 1996 photos)
    z = gz(M['u'], f0 - 0.4)
    mb.box((M['u'] + 0.05, f0 - 0.42, z + 0.95), (0.9, 0.04, 1.0), 'paint_white')
    for dx in (-0.36, 0.36):
        mb.box((M['u'] + 0.05 + dx, f0 - 0.42, z + 0.23), (0.05, 0.05, 0.46), 'paint_white', skip=('top', 'bottom'))
    # ---- the lodge: granite faced, its west part a blank wall on the gate's line, its east part set back under the
    # roof's deep fascia with the door and the window band; the aerial on the roof
    u0, u1, h = L['u0'], L['u1'], L['h']
    um = u0 + L['solid']
    z = min(gz(u0, 1.5), gz(u1, 1.5))
    yb, yr = f0 + L['d'], f0 + 0.75                       # the back wall, the set back front
    mb.box(((u0 + u1) / 2, (yr + yb) / 2, z + h / 2 - 0.3), (u1 - u0, yb - yr, h + 0.6), 'gate_granite', mats={'top': 'concrete'}, skip=('bottom',))
    mb.box(((u0 + um) / 2, (f0 + yr) / 2, z + h / 2 - 0.3), (um - u0, yr - f0, h + 0.6), 'gate_granite', mats={'top': 'concrete'}, skip=('bottom', 'back'))
    mb.box(((um + u1) / 2, (f0 + yr) / 2 + 0.03, z + h - 0.26), (u1 - um, yr - f0 - 0.06, 0.52), 'gate_granite', mats={'top': 'concrete'}, skip=('back',))
    for (cx, cy, sx, sy) in (((u0 + u1) / 2, yb - 0.09, u1 - u0, 0.18), ((u0 + u1) / 2, f0 + 0.09, u1 - u0, 0.18),
                             (u0 + 0.09, (f0 + yb) / 2, 0.18, yb - f0 - 0.36), (u1 - 0.09, (f0 + yb) / 2, 0.18, yb - f0 - 0.36)):      # the parapet's coping round the roof
        mb.box((cx, cy, z + h + 0.09), (sx, sy, 0.18), 'gate_granite', skip=('bottom',))
    mb.box((um + 0.36, yr - 0.02, z + 1.03), (0.62, 0.04, 2.06), 'void_black', skip=('back', 'bottom'))                   # the door
    wa, wb = um + 0.85, u1 - 0.3
    mb.face([(wa, yr - 0.02, z + 1.2), (wb, yr - 0.02, z + 1.2), (wb, yr - 0.02, z + 2.05), (wa, yr - 0.02, z + 2.05)], 'glass', panes=(3, 1))
    for k in range(4):                                     # the window's frame
        x = wa + (wb - wa) * k / 3
        mb.box((x, yr - 0.04, z + 1.625), (0.05, 0.05, 0.9), 'trim_black', skip=('back',))
    for zz in (1.2, 2.05):
        mb.box(((wa + wb) / 2, yr - 0.04, z + zz), (wb - wa + 0.05, 0.05, 0.05), 'trim_black', skip=('back',))
    mb.box(((wa + wb) / 2, yr - 0.12, z + 1.16), (wb - wa + 0.1, 0.26, 0.06), 'gate_granite')                             # the sill
    # the aerial (the 1600 px copy of the August 1996 photo): a dark box on the roof, a thick black stand pipe out of
    # it and a thin mast with one cross bar, a T; a blue crate west of it
    mx, my = u0 + 3.6, f0 + 1.9
    mb.box((mx, my, z + h + 0.12), (0.9, 0.5, 0.24), 'trim_black', skip=('bottom',))
    rod(mb, (mx, my, z + h + 0.24), (mx, my, z + h + 0.85), 0.07, 'metal_dark', seg=8)
    rod(mb, (mx, my, z + h + 0.85), (mx, my, z + h + 2.0), 0.025, 'metal_dark', seg=6)
    rod(mb, (mx - 0.55, my, z + h + 1.95), (mx + 0.55, my, z + h + 1.95), 0.015, 'metal_dark', seg=5)
    mb.box((mx - 1.3, my - 0.3, z + h + 0.14), (0.45, 0.32, 0.28), 'sign_blue', skip=('bottom',))
    # ---- west of the lodge: the low wall, pier and fence by turns (a pier 1.7 m, a bay 3 m)
    _gate_pier(mb, gz, u0 - 1.5, u0, posts=(True, False))
    _gate_fence(mb, gz, u0 - 4.5, u0 - 1.5)
    _gate_pier(mb, gz, u0 - 6.2, u0 - 4.5)
    _gate_fence(mb, gz, u0 - 9.2, u0 - 6.2)
    _gate_pier(mb, gz, u0 - 10.9, u0 - 9.2)
    _gate_fence(mb, gz, -GATE_END, u0 - 10.9)
    # ---- east of the east walk's outer pillar: the white wall (two bays, a pilaster at the bend and an end pier; papered
    # over with the students' posters in the 1995 and 1996 photos, the name in metal letters on it in 2008 and 2011).
    # Its first bay runs out of the outer pillar's front corner at a slant, the second along the gate's line 3.5 m in
    # front of it (the July 1997 scans; seen from the south, as in the 1996 photo, the two read as one flat wall).
    # No name on it: the school site's photo of the gate from the rail bank (gate.jpg, summer 1996 or before) has the
    # wall bare of posters and of any board or letters (reference/고증/4.8.1 「자료 R 의 정문 사진」)
    P = W['pts']
    z = min(gz(u, v) for u, v in P)
    for k in range(len(P) - 1):
        (ua, va), (ub, vb) = P[k], P[k + 1]
        ln, a = math.hypot(ub - ua, vb - va), math.atan2(vb - va, ub - ua)
        cx, cy = (ua + ub) / 2, (va + vb) / 2
        mb.box((cx, cy, z + W['h'] / 2 - 0.3), (ln + W['t'] * 0.5, W['t'], W['h'] + 0.6), 'gate_granite', rotz=a, skip=('bottom',))
        mb.box((cx, cy, z + W['h'] + 0.05), (ln + W['t'] * 0.5, W['t'] + 0.1, 0.1), 'gate_granite', rotz=a)
    (u1, v1), (u2, v2) = P[1], P[2]
    a1 = math.atan2(P[1][1] - P[0][1], P[1][0] - P[0][0])
    mb.box((u1, v1, z + (W['h'] + 0.2) / 2 - 0.3), (0.36, W['t'] + 0.14, W['h'] + 0.8), 'gate_granite', rotz=a1 / 2, skip=('bottom',))
    a2 = math.atan2(v2 - v1, u2 - u1)
    mb.box((u2 + 0.25 * math.cos(a2), v2 + 0.25 * math.sin(a2), z + (W['h'] + 0.3) / 2 - 0.3), (0.5, 0.55, W['h'] + 0.9), 'gate_granite',
           rotz=a2, skip=('bottom',))
    # ---- east of the white wall: the low wall again, pier and fence by turns as in the west (the May 1996 photo
    # from the rail bank), turning south-east along the mouth's edge down to 성산로's sidewalk (its line in the July
    # 1997 vertical photos; its four piers and its end in the leafless December 1996 scans and those of 1998 · 1999).
    # Drawn in its own frame along that line.
    G = GATE_TURN
    (xa, ya), (xb, yb) = (G['u0'], G.get('v0', 0.0)), G['to']
    a = math.atan2(yb - ya, xb - xa)
    ca, sa = math.cos(a), math.sin(a)
    gz2 = lambda u, v=0.0: gz(xa + u * ca - v * sa, ya + u * sa + v * ca)
    xf0, mb.xf = mb.xf, Matrix.Translation((xa, ya, 0.0)) @ Matrix.Rotation(a, 4, 'Z')
    e0 = 0.0
    for c in GATE_TURN_PIERS:
        _gate_fence(mb, gz2, e0, c - 0.85)
        _gate_pier(mb, gz2, c - 0.85, c + 0.85)
        e0 = c + 0.85
    _gate_fence(mb, gz2, e0, GATE_TURN_LEN)
    mb.xf = xf0
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


# ----------------------------------------------------------------------------- 2003 사진의 소품 (reference/고증.md 3.18)
def bollard():
    """노랑 · 검정 볼라드 (2003_봄_언더우드관_앞길_벚나무.jpg, rows across the road before 언더우드관): a steel post
    13 cm across in yellow and black bands, a black domed cap, 0.70 m high to the cap's top (Kakao roadview 2008-08,
    2010-12 and 2011-04 at 대강당 진입로: 0.65 - 0.75 m against the row's spacing and the panoramas' distances;
    reference/고증/4.5; before 0.85 m to the cap's foot, an estimate)."""
    mb = MeshBuilder('bollard')
    r = 0.065
    z = -0.1
    k = 0.664 / 0.85                                   # (the bands as before, scaled: cap foot 0.664, top 0.70)
    for z1, m in ((0.24, 'paint_yellow'), (0.34, 'paint_black'), (0.58, 'paint_yellow'), (0.68, 'paint_black'),
                  (0.8, 'paint_yellow'), (0.85, 'paint_black')):
        mb.cylinder((0, 0), r, z, z1 * k, m, seg=12, cap_top=False)
        z = z1 * k
    mb.sphere((0, 0, 0.85 * k), r, 'paint_black', seg=12, rings=6, sz=0.55)
    return mb


def bollard_stone():
    """콘크리트 볼라드 (아펜젤러관 뒤 동쪽 찻길의 서쪽 가, tools/appen97.py; reference/고증/3.5): a square concrete post behind
    the kerb.  Kakao roadview 2010-12 (1016786075): square concrete posts in a row; the 1996 winter scans: their shadows,
    0.68 m at the sun's 28.7 deg, so about 0.45 m high.  20 cm square, its top cut off at the corners."""
    mb = MeshBuilder('bollard_stone')
    w, h, c = 0.2, 0.45, 0.03
    mb.prism([(-w / 2, -w / 2), (w / 2, -w / 2), (w / 2, w / 2), (-w / 2, w / 2)], -0.1, h - c, 'concrete')
    t = w / 2 - c                                      # (the chamfer: a smaller square on top, sloping faces between)
    lo = [(-w / 2, -w / 2, h - c), (w / 2, -w / 2, h - c), (w / 2, w / 2, h - c), (-w / 2, w / 2, h - c)]
    hi = [(-t, -t, h), (t, -t, h), (t, t, h), (-t, t, h)]
    for k in range(4):
        mb.face([lo[k], lo[(k + 1) % 4], hi[(k + 1) % 4], hi[k]], 'concrete')
    mb.face(hi, 'concrete')
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


def glass_board():
    """유리 게시판 (reference/학교홈페이지/edu2.jpg, spring before 1997: two side by side at the foot of the bank before
    용재관's south block, left of the steps; reference/고증/3.13.1 「앞 둑의 게시판 둘과 벚나무 둘」): a glass-fronted case
    3.8 m long on two square posts, its frame and flat cap a pale blue-grey, three panes over the posters, the case
    0.62 - 2.18 m up and the cap's top 2.3 m (the 1997 scans put the cap 2.3 m over the road).  The panes face -Y; the
    origin is the middle of its footprint on the ground."""
    mb = MeshBuilder('glass_board')
    W, D, z0, z1, top, m = 3.8, 0.2, 0.62, 2.18, 2.3, 'frame_paleblue'
    wi, b, mu = W - 0.2, 0.07, 0.05                          # the case between the posts, its border, the mullions
    for sx in (-1, 1):
        mb.box((sx * (W / 2 - 0.05), 0, (top - 0.08) / 2), (0.1, 0.12, top - 0.08), m)          # the posts
        mb.box((sx * (wi / 2 - b / 2), 0, (z0 + z1) / 2), (b, D, z1 - z0), m)                    # the case's ends
    for z in (z0 + b / 2, z1 - b / 2):
        mb.box((0, 0, z), (wi, D, b), m)                                                         # its head and sill
    mb.box((0, D / 2 - 0.03, (z0 + z1) / 2), (wi - 2 * b, 0.06, z1 - z0 - 2 * b), m, skip=('front',))   # the back
    for k in (-1, 1):
        mb.box((k * (wi - 2 * b) / 6, -D / 2 + 0.025, (z0 + z1) / 2), (mu, 0.05, z1 - z0 - 2 * b), m)   # the mullions
    x0, x1, za, zb = -wi / 2 + b, wi / 2 - b, z0 + b, z1 - b
    mb.face([(x0, D / 2 - 0.06, za), (x1, D / 2 - 0.06, za), (x1, D / 2 - 0.06, zb), (x0, D / 2 - 0.06, zb)],
            'notice_posters', uvs=[(0, 0), (2, 0), (2, 1), (0, 1)])
    mb.face([(x0, -D / 2 + 0.03, za), (x1, -D / 2 + 0.03, za), (x1, -D / 2 + 0.03, zb), (x0, -D / 2 + 0.03, zb)], 'glass_door')
    mb.box((0, 0, top - 0.04), (W + 0.12, 0.36, 0.08), m)                                        # the flat cap
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
    """벤치 (2003_봄_백양로끝_핀슨관길_벚나무.jpg: under the cherries along the top of the steps' banks, facing the road,
    beside a three-bin green recycling box; 2003_봄_언더우드관정원_남쪽계단_벚나무.jpg: the same row seen from behind, three
    people to a bench): 1.8 m long, a seat of three broad weathered grey planks and a slightly reclined back of three more, on three
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


def recycle_bin():
    """분리수거함 (2003_봄_백양로끝_핀슨관길_벚나무.jpg: between two benches along the top of the steps up to 언더우드관
    정원, as wide as most of a bench and taller than its back; 2003_봄_언더우드관정원_남쪽계단_벚나무.jpg: its plain grey
    back in the same row; both photos put it at about 0.85 of a bench's length and a little over its back): a grey steel
    cabinet 1.55 m wide, 0.55 deep and 1.15 high on short feet under an overhanging lid, three slots under the lid and
    three dark green doors below, each with a pale label at its head and a smaller one low down.  The doors face -Y; the
    origin is the middle of its footprint on the ground."""
    mb = MeshBuilder('recycle_bin')
    W, D, H, feet = 1.55, 0.55, 1.1, 0.06
    mb.box((0, 0, (feet + H) / 2), (W, D, H - feet), 'bin_grey', skip=('bottom',))
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * (W / 2 - 0.035), sy * (D / 2 - 0.035), feet / 2), (0.05, 0.05, feet), 'bin_grey', skip=('top', 'bottom'))
    mb.box((0, 0.0, H + 0.025), (W + 0.07, D + 0.07, 0.05), 'bin_grey')            # the lid
    y0 = -D / 2
    bw = (W - 0.08) / 3

    def front(x0, x1, z0, z1, y, mat):
        mb.face([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], mat)
    for k in range(3):
        x = -W / 2 + 0.04 + bw * (k + 0.5)
        front(x - bw / 2 + 0.05, x + bw / 2 - 0.05, 0.9, 1.03, y0 - 0.002, 'paint_black')    # the slot
        mb.box((x, y0 - 0.006, 0.49), (bw - 0.035, 0.012, 0.72), 'bin_green', skip=('back',))    # the door, a little proud
        front(x - bw / 2 + 0.07, x + bw / 2 - 0.07, 0.72, 0.8, y0 - 0.0125, 'paint_white')   # its label
        front(x - bw / 2 + 0.12, x + bw / 2 - 0.12, 0.24, 0.29, y0 - 0.0125, 'paint_white')
    return mb


def _ellipsoid(mb, c, abc, q=None, seg=32, rings=18):
    """A closed ellipsoid, its rows sharing the pole vertices: a solid for the voxel union."""
    R = (q or Quaternion()).to_matrix()
    c = Vector(c)
    P = [[c + R @ Vector((abc[0] * math.sin(th) * math.cos(ph), abc[1] * math.sin(th) * math.sin(ph), abc[2] * math.cos(th)))
          for ph in (2 * math.pi * i / seg for i in range(seg))]
         for th in (math.pi * j / rings for j in range(rings + 1))]
    tag = 'e%d' % len(mb.faces)
    for j in range(rings):
        for i in range(seg):
            k = (i + 1) % seg
            if j == 0:
                q = [P[0][0], P[1][i], P[1][k]]
            elif j == rings - 1:
                q = [P[j][i], P[rings][0], P[j][k]]
            else:
                q = [P[j][i], P[j + 1][i], P[j + 1][k], P[j][k]]
            mb.face(q, 'stone_haetae', smooth=tag)


def _blob(name, elems, voxel, smooth=4, factor=0.6):
    """An organic form from overlapping solids: their union on a voxel grid, the creases where they meet smoothed
    (sculpt.union).  elems: ('ell', c, (a, b, c)[, quat]) | ('ball', c, r) | ('cap', p0, p1, r)."""
    import sculpt
    from statues import _capsule
    mb = MeshBuilder(name)
    for e in elems:
        if e[0] == 'ell':
            _ellipsoid(mb, e[1], e[2], e[3] if len(e) > 3 else None)
        elif e[0] == 'ball':
            _ellipsoid(mb, e[1], (e[2],) * 3, None, seg=20, rings=12)
        else:
            _capsule(mb, e[1], e[2], e[3])
    return sculpt.union([mb.build()], voxel, smooth=smooth, factor=factor, name=name)


def _haetae_curls(E, c, abc, angs, r, out=1.0):
    """Curls of the mane or the coat: small balls set on the surface of an ellipsoid at (azimuth, elevation) pairs."""
    for az, el in angs:
        a, e = math.radians(az), math.radians(el)
        n = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))
        p = Vector(c) + Vector((n.x * abc[0], n.y * abc[1], n.z * abc[2])) * out
        E.append(('ball', tuple(p), r))


def haetae():
    """돌 해태상 (2003_봄_백양로끝_핀슨관길_벚나무.jpg and 2003_봄_언더우드관정원_남쪽계단_벚나무.jpg: a pair either side of
    the head of the steps up from the end of 백양로, looking down them): a weathered granite 해태 about 0.8 m high sitting up on its haunches, the forelegs straight, a big
    head held high, its body covered in knobbly curls, on a plain granite plinth 0.45 m high.  The face is the usual one
    of Joseon stone 해태 (the photo is too small for it): bulging eyes under heavy brows, a broad nose, a mouth of teeth
    and two fangs, a knob of a horn; curls of the mane round the head and down the spine, a bushy tail curled up the
    back.  It looks along -Y."""
    from statues import _eq
    E = [
        ('ell', (0, 0.2, 0.2), (0.22, 0.23, 0.2)),                 # haunches
        ('ell', (0, 0.0, 0.3), (0.19, 0.27, 0.19)),                # the back, running forward
        ('ell', (0, -0.17, 0.4), (0.18, 0.14, 0.22)),              # chest, sitting up
        ('ell', (0, -0.15, 0.62), (0.22, 0.17, 0.18)),             # the mane round the neck
        ('ell', (0, -0.25, 0.7), (0.18, 0.16, 0.15)),              # head
        ('ell', (0, -0.36, 0.63), (0.12, 0.09, 0.085)),            # muzzle
        ('ell', (0, -0.44, 0.66), (0.078, 0.036, 0.044)),          # the broad nose
        ('ell', (0, -0.34, 0.56), (0.105, 0.085, 0.042)),          # lower jaw
        ('cap', (0, -0.22, 0.83), (0, -0.2, 0.9), 0.03),           # the horn
        ('cap', (0, 0.42, 0.12), (0, 0.45, 0.3), 0.05),            # tail, up the back of the haunches
        ('cap', (0, 0.45, 0.3), (0, 0.4, 0.44), 0.045),
        ('ball', (0, 0.35, 0.47), 0.06),                           # ... curled over at the top
    ]
    for sx in (-1, 1):
        E += [
            ('ell', (sx * 0.16, 0.18, 0.16), (0.085, 0.19, 0.14)),             # thighs
            ('ell', (sx * 0.17, -0.01, 0.04), (0.065, 0.11, 0.042)),           # hind paws
            ('cap', (sx * 0.12, -0.2, 0.42), (sx * 0.12, -0.26, 0.07), 0.062), # forelegs
            ('ell', (sx * 0.12, -0.3, 0.04), (0.068, 0.09, 0.042)),            # fore paws
            ('ball', (sx * 0.08, -0.37, 0.77), 0.036),                         # bulging eyes
            ('ell', (sx * 0.08, -0.36, 0.81), (0.052, 0.027, 0.021), _eq('Y', sx * -12)),   # heavy brows
            ('ball', (sx * 0.036, -0.468, 0.67), 0.021),                       # nostrils
            ('ell', (sx * 0.16, -0.2, 0.78), (0.025, 0.04, 0.055), _eq('Y', sx * 55)),     # ears, laid out sideways
            ('ell', (sx * 0.062, -0.42, 0.59), (0.017, 0.017, 0.034)),         # fangs
            ('ell', (sx * 0.11, -0.34, 0.61), (0.032, 0.052, 0.037)),          # cheeks
            ('ball', (sx * 0.035, 0.44, 0.24), 0.04),                          # the bushy tail
            ('ball', (sx * 0.04, 0.39, 0.4), 0.04),
        ]
        for t in (-0.03, 0.0, 0.03):                                           # toes
            E.append(('ball', (sx * 0.12 + t, -0.375, 0.035), 0.022))
            E.append(('ball', (sx * 0.17 + t, -0.105, 0.035), 0.02))
    for x in (-0.03, -0.01, 0.01, 0.03):                                       # the front teeth
        E.append(('ell', (x, -0.432, 0.605), (0.009, 0.01, 0.014)))
    # the mane in curls round the back and sides of the head and down the neck, a row down the spine, the coat knobbly
    _haetae_curls(E, (0, -0.15, 0.62), (0.22, 0.17, 0.18),
                  [(az, el) for el in (-10, 15, 40) for az in range(-20, 210, 26)], 0.044)
    _haetae_curls(E, (0, -0.19, 0.42), (0.18, 0.14, 0.22), [(az, -25) for az in range(210, 340, 26)], 0.03)
    _haetae_curls(E, (0, 0.0, 0.3), (0.19, 0.27, 0.19),
                  [(az, el) for el in (25, 55, 80) for az in range(-170, 180, 40)], 0.026, out=0.96)
    _haetae_curls(E, (0, 0.2, 0.2), (0.22, 0.23, 0.2),
                  [(az, el) for el in (10, 40) for az in range(-150, 180, 45)], 0.026, out=0.96)
    ob = _blob('haetae', E, 0.009, smooth=3, factor=0.5)
    m = ob.modifiers.new('dec', 'DECIMATE')
    m.ratio = 0.08
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    mb = MeshBuilder('haetae')
    z0 = 0.45
    V = [Vector((v.co.x, v.co.y, v.co.z + z0)) for v in me.vertices]
    for p in me.polygons:
        mb.face([V[i] for i in p.vertices], 'stone_haetae', smooth='body')
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    # the plinth: a plain granite block with a chamfered top edge (the photo: a little longer than the beast)
    mb.box((0, 0.02, 0.2), (0.7, 1.32, 0.42), 'stone_haetae', skip=('bottom',))
    top = [(-0.35, -0.64), (0.35, -0.64), (0.35, 0.68), (-0.35, 0.68)]
    inset = [(-0.32, -0.61), (0.32, -0.61), (0.32, 0.65), (-0.32, 0.65)]
    for i in range(4):
        j = (i + 1) % 4
        mb.face([(*top[i], 0.41), (*top[j], 0.41), (*inset[j], 0.45), (*inset[i], 0.45)], 'stone_haetae')
    mb.face([(*p, 0.45) for p in inset], 'stone_haetae')
    return mb
