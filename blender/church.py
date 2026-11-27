"""창천교회 (연세로 동쪽, 굴다리 남동쪽: reference/고증/4.8_정문_밖.md 「창천교회」): the red-brick hall as it stood in 1997
and stands now, in place of the town's box with a gable and two plain towers.

Where it stands, how long and wide it is and how high its copings are come from the scans of 1997-07-28 (four frames,
the white copings and the crosses solved as rays: tools/gate_town.py CHURCH is the box from the towers' west faces to
the east gable and over the towers' outer faces).  What it looks like is read off the oblique air photo of the 1990s
(reference/1990년대_캠퍼스_항공사진_어제의_신촌캠퍼스.jpg), the 1996 photos from 노고산동 (52004 · 52006) and the Kakao
roadview of 2008-08-03, 2008-11-12 and 2009-03-02 (looked at, not kept: reference/출처.txt), levelled by their upright
edges; the heights between the scans' are the roadview's west view scaled by the front's width:
- the west front: a tower 5.7 m square on each corner, clasping buttresses up its corners, two string courses, small
  white-framed lancets in pairs and three under the top; over the shaft four corner turrets with white caps round a
  narrower, taller lantern with an open arch each way and four small pinnacles, a slender slate spire and a white
  cross, its arm across the front.  Between the towers the gable wall, in it a great white stone arch with a rose of
  blue glass over two tall dark lancets, a slit in the gable; before it a shallow white stone porch of three pointed
  arches, wider than the gap between the towers, its parapet cut in crossing diagonals, four white pinnacles on it
- the long walls: seven bays, a brick pier between each two and on the east corner (5.57 m apart, the first 4.5 m
  from the tower) that rises over the parapet as a small capped pinnacle (the air photo's white dots along the
  eaves), a lower post between each two; in every bay two tall lancets in white frames, three slits under the
  parapet over each, a pierced brick panel under each sill, the ground floor's barred windows under them.  The
  north wall the same (the roadview of 2026-07, the only one of that side); the east wall a plain brick gable
- the roof: grey-green slates, the ridge along the hall
Nothing here draws from a random stream (blender/town.py house() still takes the old box's draws)."""
import math
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

BR, ST, SL, GL, DK = 'brick_church97', 'stone_white', 'slate_church97', 'church97', 'trim_black'
LANCET_RISE = 0.9            # a lancet's arch rises this much of its width (tools/make_textures.py church97_tex)
CELLS = dict(nave=(0, 0, 192, 768), west=(192, 0, 256, 768), rose=(448, 0, 256, 256), low=(448, 256, 256, 192),
             door=(704, 0, 192, 384), parapet=(448, 448, 576, 128))        # (make_textures.py CHURCH97_CELLS)

# heights over the front yard (m; the yard 21.2 m over the sea in the scans).  From the scans: the long walls' coping
# 22.65, the gables' coping 28.4, the towers' rim 28.2, the crosses' arms 47.25, the ridge 27.1 (26.3 - 27.8).  The rest
# from the roadview's two levelled west views (2009-03 and 2008-08, 0.1 - 0.6 m apart), which give the scans' three
# within 0.4 m with the camera 2.5 m over the road
Z_STR1, Z_STR2, Z_SHAFT = 12.0, 22.0, 28.4          # the towers' two string courses and the cornice on the shaft
Z_TURRET, Z_LANT, Z_TIP, Z_ARM, Z_CROSS = 31.2, 35.2, 45.6, 47.25, 48.0
Z_PAR = 22.65                                       # the long walls' parapet
Z_RIDGE, Z_GABLE, Z_GABLE0 = 27.6, 28.4, 23.1       # the ridge; the gables' coping at the point and at the corners
TOW_V, TOW_U = 5.7, 5.8                             # a tower across the front and along the hall
FRONT_IN = 1.15                                     # the gable wall behind the towers' west faces
NAVE_IN = 0.575                                     # the long walls behind the towers' outer faces (0.7 north, 0.45 south)
BAYS, BAY0, PITCH = 7, 4.5, 5.57                    # the piers: the first from the tower's east face, then apart
WIN = (7.6, 15.9, 1.75, 1.1)                        # the nave's lancets: sill, point, width over the frame, off the bay's middle
ROWS = ((7.4, 10.3), (12.3, 15.3), (17.6, 20.5))    # the towers' pairs of small lancets; three more under the cornice
ROW3 = (22.7, 26.2, 26.7)
PORCH = dict(out=1.25, w=14.0, arch=(3.3, 3.0, 5.4), roof=6.3, par=8.5, pin=10.1)
ARCH = dict(w=9.8, z0=6.3, spring=18.2, top=24.3)   # the great white arch
BIG = (9.0, 18.3, 3.4, 0.75)                        # its two lancets: sill, point, width, the stone between them
ROSE = (19.9, 1.4)                                  # the rose: middle, radius of the glass


def _cell(name, u0=0.0, u1=1.0, v0=0.0, v1=1.0, pad=2.0):
    """uv box of a part of an atlas cell: u across it, v from its top down (0 .. 1 of the cell)"""
    x, y, w, h = CELLS[name]
    return ((x + pad + (w - 2 * pad) * u0) / 1024, (x + pad + (w - 2 * pad) * u1) / 1024,
            1 - (y + pad + (h - 2 * pad) * v1) / 1024, 1 - (y + pad + (h - 2 * pad) * v0) / 1024)


def _arch(s0, s1, z0, z1, rise=None, n=6):
    """a pointed opening between s0 and s1 from z0 to its point z1, counter-clockwise seen from outside"""
    w = s1 - s0
    rise = LANCET_RISE * w if rise is None else rise
    zs = z1 - rise
    R = (0.25 * w * w + rise * rise) / w
    th = math.asin(min(1.0, rise / R))
    pts = [(s0, z0), (s1, z0)]
    for k in range(n + 1):
        a = th * k / n
        pts.append((s1 - R + R * math.cos(a), zs + R * math.sin(a)))
    for k in range(1, n + 1):
        a = math.pi - th + th * k / n
        pts.append((s0 + R + R * math.cos(a), zs + R * math.sin(a)))
    return pts


def _inset(loop, d):
    """a convex loop moved in by d (each corner along its bisector)"""
    n = len(loop)
    out = []
    for i in range(n):
        p, a, b = Vector(loop[i]), Vector(loop[i - 1]), Vector(loop[(i + 1) % n])
        e0, e1 = (p - a).normalized(), (b - p).normalized()
        n0, n1 = Vector((-e0.y, e0.x)), Vector((-e1.y, e1.x))        # (to the left: inwards of a counter-clockwise loop)
        m = n0 + n1
        if m.length < 1e-6:
            m = n0
        m = m.normalized()
        out.append(tuple(p + m * (d / max(0.35, m.dot(n0)))))
    return out


class Church:
    def __init__(self, mb, b, ground):
        self.mb = mb
        cx, cy, self.L, self.W, ang, self.base = b[:6]
        self.c, self.s, self.ang = math.cos(ang), math.sin(ang), ang
        self.o = (cx, cy)
        self.ground = ground
        # the front yard's level: the ground 2 - 6 m before the west front
        self.zf = sum(ground(*self.xy(-self.L / 2 - d, v)) for d in (2.0, 6.0) for v in (-6.0, 0.0, 6.0)) / 6

    # -- the frame: u east along the hall, v north across it, z over the front yard
    def xy(self, u, v):
        return self.o[0] + u * self.c - v * self.s, self.o[1] + u * self.s + v * self.c

    def P(self, u, v, z):
        x, y = self.xy(u, v)
        return (x, y, self.zf + z)

    def zb(self):
        return self.base - self.zf - 0.2            # (the walls' feet: under the lowest corner's ground)

    # -- a wall's plane: from a to b (u, v), the outside on the right; s runs from a, `out` off the plane outwards
    def plane(self, a, b):
        a, b = Vector(a), Vector(b)
        L = (b - a).length
        t = (b - a) / L
        n = Vector((t.y, -t.x))
        return lambda s, z, out=0.0: self.P(a.x + t.x * s + n.x * out, a.y + t.y * s + n.y * out, z), L

    def poly(self, pl, loops, mat, out=0.0, uv=None, back=False):
        """a flat face in the plane pl over the first loop of (s, z) with the others as holes; uv(s, z) or metric"""
        vs = [Vector((p[0], p[1], 0)) for lp in loops for p in lp]
        for tri in tessellate_polygon([[Vector((p[0], p[1], 0)) for p in lp] for lp in loops]):
            q = [vs[k] for k in tri]
            ccw = (q[1] - q[0]).cross(q[2] - q[0]).z > 0
            if ccw == back:
                q = q[::-1]
            self.mb.face([pl(p.x, p.y, out) for p in q], mat, uvs=[uv(p.x, p.y) for p in q] if uv else None)

    def facing(self, pts, c, toward):
        """the face turned to look at the point c (or away from it)"""
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(pts)):                                       # (Newell)
            p, q = Vector(pts[i]), Vector(pts[(i + 1) % len(pts)])
            n += Vector(((p.y - q.y) * (p.z + q.z), (p.z - q.z) * (p.x + q.x), (p.x - q.x) * (p.y + q.y)))
        m = sum((Vector(p) for p in pts), Vector()) / len(pts)
        return pts if (n.dot(Vector(c) - m) > 0) == toward else pts[::-1]

    def rim(self, pl, loop, o0, o1, mat, closed=True, inward=True):
        """the strip between a loop at depth o0 and the same loop at o1: a reveal looking into the loop, or an edge
        looking out of it"""
        n = len(loop)
        c = pl(sum(p[0] for p in loop) / n, sum(p[1] for p in loop) / n, (o0 + o1) / 2)
        for i in range(n if closed else n - 1):
            p, q = loop[i], loop[(i + 1) % n]
            f = [pl(p[0], p[1], o0), pl(p[0], p[1], o1), pl(q[0], q[1], o1), pl(q[0], q[1], o0)]
            self.mb.face(self.facing(f, c, inward), mat)

    def glazed(self, pl, loop, cell, frame=0.14, proud=0.05, rec=0.22, part=None, frame_mat=ST):
        """a window in the plane: returns its hole for the wall; lays the stone frame round it standing `proud` of the
        wall, the reveal behind it and the glass `rec` in, the glass taking the atlas cell (part: only so much of the
        cell from its top as keeps the panes' shape, for the small lancets)"""
        inner = _inset(loop, frame)
        self.poly(pl, [loop, inner[::-1]], frame_mat, out=proud)
        self.rim(pl, loop, proud, 0.0, frame_mat, inward=False)
        self.rim(pl, inner, proud, -rec, frame_mat)
        s0, s1 = min(p[0] for p in inner), max(p[0] for p in inner)
        z0, z1 = min(p[1] for p in inner), max(p[1] for p in inner)
        x, y, w, h = CELLS[cell]
        vmax = min(1.0, (z1 - z0) / (s1 - s0) * w / h) if part else 1.0
        u0, u1, v0, v1 = _cell(cell, v1=vmax)
        self.mb.face([pl(p[0], p[1], -rec) for p in inner], GL,
                     uvs=[(u0 + (u1 - u0) * (p[0] - s0) / (s1 - s0), v0 + (v1 - v0) * (p[1] - z0) / (z1 - z0)) for p in inner])
        return inner

    def box(self, u, v, z0, z1, su, sv, mat, **kw):
        x, y = self.xy(u, v)
        self.mb.box((x, y, self.zf + (z0 + z1) / 2), (su, sv, z1 - z0), mat, rotz=self.ang, **kw)

    def pyramid(self, u, v, z0, z1, hu, hv, mat):
        c = [(u - hu, v - hv), (u + hu, v - hv), (u + hu, v + hv), (u - hu, v + hv)]
        for i in range(4):
            a, b = c[i], c[(i + 1) % 4]
            self.mb.face([self.P(a[0], a[1], z0), self.P(b[0], b[1], z0), self.P(u, v, z1)], mat)

    def pinnacle(self, u, v, z0, z1, half, cap, mat=BR, cap_mat=ST):
        """a square post with a pyramid cap on a thin slab"""
        self.box(u, v, z0, z1, 2 * half, 2 * half, mat, skip=('bottom', 'top'))
        self.box(u, v, z1, z1 + 0.12, 2 * half + 0.16, 2 * half + 0.16, cap_mat, skip=('bottom',))
        self.pyramid(u, v, z1 + 0.12, z1 + 0.12 + cap, half, half, cap_mat)

    # ------------------------------------------------------------------ the towers
    def tower(self, side):
        L, W = self.L, self.W
        u0, u1 = -L / 2, -L / 2 + TOW_U
        v0, v1 = (W / 2 - TOW_V, W / 2) if side > 0 else (-W / 2, -W / 2 + TOW_V)
        zb = self.zb()
        corners = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]             # counter-clockwise: south, east, north, west faces
        outer = {3, 2 if side > 0 else 0}                              # (the west face and the one away from the hall)
        for i in range(4):
            a, b = corners[i], corners[(i + 1) % 4]
            pl, Lw = self.plane(a, b)
            holes = []
            mid = Lw / 2
            if i in outer:
                for z0, z1 in ROWS:
                    for k in (-1, 1):
                        m = mid + k * 1.25
                        holes.append(self.glazed(pl, _arch(m - 0.44, m + 0.44, z0, z1), 'nave', frame=0.1, proud=0.04,
                                                 rec=0.15, part=True))
            if i in outer or i == 1:                                   # (three under the cornice, the middle one taller)
                for k in (-1, 0, 1):
                    m = mid + k * 1.25
                    holes.append(self.glazed(pl, _arch(m - 0.42, m + 0.42, ROW3[0], ROW3[2] if k == 0 else ROW3[1]), 'nave',
                                             frame=0.1, proud=0.04, rec=0.15, part=True))
            self.poly(pl, [[(0, zb), (Lw, zb), (Lw, Z_SHAFT), (0, Z_SHAFT)]] + [h[::-1] for h in holes], BR)
        uc, vc = (u0 + u1) / 2, (v0 + v1) / 2
        # the clasping buttresses, the string courses and the cornice over them, the deck
        for cu, cv in corners:
            du, dv = (1 if cu > uc else -1), (1 if cv > vc else -1)
            self.box(cu - du * 0.35, cv - dv * 0.35, zb, Z_SHAFT, 1.1, 1.1, BR, skip=('bottom', 'top'))
            self.pinnacle(cu - du * 0.35, cv - dv * 0.35, Z_SHAFT, Z_TURRET, 0.45, 1.5)
        for z, h, o in ((Z_STR1 - 0.08, 0.16, 0.28), (Z_STR2 - 0.08, 0.16, 0.28), (Z_SHAFT - 0.3, 0.4, 0.34)):
            self.box(uc, vc, z, z + h, TOW_U + 2 * o, TOW_V + 2 * o, ST)
        # the lantern: an open arch each way, a small pinnacle on each corner, the spire and the cross
        hl = 1.75
        lc = [(uc - hl, vc - hl), (uc + hl, vc - hl), (uc + hl, vc + hl), (uc - hl, vc + hl)]
        for i in range(4):
            pl, Lw = self.plane(lc[i], lc[(i + 1) % 4])
            op = _arch(Lw / 2 - 0.7, Lw / 2 + 0.7, Z_SHAFT + 0.9, Z_LANT - 1.4)
            self.poly(pl, [[(0, Z_SHAFT), (Lw, Z_SHAFT), (Lw, Z_LANT), (0, Z_LANT)], op[::-1]], BR)
            self.rim(pl, op, 0.0, -0.3, BR)
            self.mb.face([pl(p[0], p[1], -0.3) for p in op], DK)
            self.pinnacle(*lc[i], Z_LANT - 1.6, Z_LANT + 0.4, 0.26, 1.0)
        self.box(uc, vc, Z_LANT, Z_LANT + 0.18, 2 * hl + 0.3, 2 * hl + 0.3, ST, skip=('bottom',))
        r, n = 1.4, 8
        ring = [(uc + r * math.cos(2 * math.pi * (k + 0.5) / n), vc + r * math.sin(2 * math.pi * (k + 0.5) / n)) for k in range(n)]
        for k in range(n):
            a, b = ring[k], ring[(k + 1) % n]
            self.mb.face([self.P(a[0], a[1], Z_LANT + 0.18), self.P(b[0], b[1], Z_LANT + 0.18), self.P(uc, vc, Z_TIP)], SL)
        self.box(uc, vc, Z_TIP - 0.6, Z_CROSS, 0.16, 0.16, 'paint_white', skip=('bottom',))
        self.box(uc, vc, Z_ARM - 0.08, Z_ARM + 0.08, 0.16, 1.1, 'paint_white')

    # ------------------------------------------------------------------ the long walls and the roof
    def nave(self):
        L, W = self.L, self.W
        zb = self.zb()
        ut = -L / 2 + TOW_U
        ve = W / 2 - NAVE_IN
        piers = [ut + BAY0 + PITCH * k for k in range(BAYS)]             # (the last on the east corner)
        piers[-1] = min(piers[-1], L / 2 - 0.6)
        mids = [(a_ + b_) / 2 for a_, b_ in zip([ut] + piers[:-1], piers)]            # (u of each bay's middle)
        mids[0] = ut + (BAY0 - 0.65) / 2 + 0.05                         # (the first bay: narrower, its two windows closer)
        z0w, z1w, ww, off = WIN
        for side in (-1, 1):
            a, b = ((ut, -ve), (L / 2, -ve)) if side < 0 else ((L / 2, ve), (ut, ve))
            pl, Lw = self.plane(a, b)
            holes = []
            for su in mids:
                mid = su - ut if side < 0 else L / 2 - su
                # (the ground floor's windows sit over the ground where they are: the lane climbs east)
                g = self.ground(*self.xy(su, side * (ve + 1.0))) - self.zf
                o_ = 0.92 if su == mids[0] else off
                for m in (mid - o_, mid + o_):
                    holes.append(self.glazed(pl, _arch(m - ww / 2, m + ww / 2, z0w, z1w), 'nave'))
                    lo = [(m - 0.85, g + 1.8), (m + 0.85, g + 1.8), (m + 0.85, g + 3.1), (m - 0.85, g + 3.1)]
                    if g + 3.1 < z0w - 3.0:
                        holes.append(self.glazed(pl, lo, 'low', frame=0.1, proud=0.04, rec=0.15))
                    for r in range(11):                                # (the pierced brick panel under the sill)
                        for c_ in range(3):
                            if (r + c_) % 2:
                                continue
                            s0, zz = m - 0.27 + 0.2 * c_, z0w - 2.6 + 0.19 * r
                            self.mb.face([pl(s0, zz, 0.02), pl(s0 + 0.14, zz, 0.02), pl(s0 + 0.14, zz + 0.13, 0.02), pl(s0, zz + 0.13, 0.02)], DK)
                    for j in (-1, 0, 1):                               # (the slits under the parapet)
                        sl = [(m + j * 0.28 - 0.06, Z_PAR - 1.4), (m + j * 0.28 + 0.06, Z_PAR - 1.4), (m + j * 0.28 + 0.06, Z_PAR - 0.6), (m + j * 0.28 - 0.06, Z_PAR - 0.6)]
                        self.mb.face([pl(p[0], p[1], 0.02) for p in sl], DK)
            self.poly(pl, [[(0, zb), (Lw, zb), (Lw, Z_PAR), (0, Z_PAR)]] + [h[::-1] for h in holes], BR)
            # the parapet's back and coping; the piers with their caps, a lower post between each two
            pb, _ = self.plane(b, a)
            self.poly(pb, [[(0, Z_PAR - 0.9), (Lw, Z_PAR - 0.9), (Lw, Z_PAR), (0, Z_PAR)]], BR, out=0.3)
            um = (ut + L / 2) / 2
            self.box(um, side * (ve - 0.15), Z_PAR, Z_PAR + 0.14, Lw, 0.5, ST, skip=('bottom',))
            for su in piers:
                self.box(su, side * (ve + 0.05), zb, Z_PAR, 1.3, 0.6, BR, skip=('bottom', 'top'))
                self.pinnacle(su, side * (ve + 0.05), Z_PAR, Z_PAR + 0.8, 0.42, 0.7, cap_mat=ST)
            for su in mids:
                self.box(su, side * (ve - 0.12), Z_PAR + 0.14, Z_PAR + 0.6, 0.5, 0.5, BR, skip=('bottom',), mats={'top': ST})
        # the roof: slates from the gutters behind the parapets to the ridge
        ug, vr, ze = -L / 2 + FRONT_IN, ve - 0.3, Z_PAR - 0.9
        self.mb.face([self.P(ug, -vr, ze), self.P(L / 2, -vr, ze), self.P(L / 2, 0, Z_RIDGE), self.P(ug, 0, Z_RIDGE)], SL)
        self.mb.face([self.P(L / 2, vr, ze), self.P(ug, vr, ze), self.P(ug, 0, Z_RIDGE), self.P(L / 2, 0, Z_RIDGE)], SL)
        # the east wall: a plain brick gable between the corner piers (no photo shows it)
        pl, Lw = self.plane((L / 2, -ve), (L / 2, ve))
        zg = Z_GABLE0 - 0.16
        self.poly(pl, [[(0, zb), (Lw, zb), (Lw, zg), (Lw / 2, Z_GABLE - 0.16), (0, zg)]], BR)
        self.gable_coping(L / 2, ve, zg, out=1)

    def gable_coping(self, u, ve, zg, out):
        """a stone coping up the two rakes of the gable wall at u, `out` the way the wall looks along u (1 east, -1 west)"""
        ua, ub = u + out * 0.06, u - out * 0.45
        for sgn in (-1, 1):
            a, b = Vector((sgn * ve, zg)), Vector((0.0, Z_GABLE - 0.16))
            t = (b - a).normalized()
            up = Vector((-t.y, t.x))
            if up.y < 0:
                up = -up
            q = [a, b, b + up * 0.16, a + up * 0.16]                    # (v, z): the rake's top edge and 0.16 m over it
            c = self.P((ua + ub) / 2, (a.x + b.x) / 2, (a.y + b.y) / 2 + 0.08)
            for uu in (ua, ub):
                self.mb.face(self.facing([self.P(uu, p.x, p.y) for p in q], c, False), ST)
            for i, j in ((3, 2), (0, 3), (1, 2)):
                f = [self.P(ua, q[i].x, q[i].y), self.P(ua, q[j].x, q[j].y), self.P(ub, q[j].x, q[j].y), self.P(ub, q[i].x, q[i].y)]
                self.mb.face(self.facing(f, c, False), ST)

    # ------------------------------------------------------------------ the west front between the towers
    def front(self):
        L, W = self.L, self.W
        zb = self.zb()
        ug = -L / 2 + FRONT_IN
        vt = W / 2 - TOW_V                                              # (the towers' inner faces)
        pl, Lw = self.plane((ug, vt), (ug, -vt))                        # (seen from the west: s runs south)
        mid = Lw / 2
        # the great arch: white stone set 0.25 m into the brick, the rose over two lancets in it
        A = ARCH
        big = _arch(mid - A['w'] / 2, mid + A['w'] / 2, A['z0'], A['top'], rise=A['top'] - A['spring'], n=10)
        ve = W / 2 - NAVE_IN
        zg = Z_GABLE - 0.16 - (Z_GABLE - Z_GABLE0) * vt / ve                # (the rake where it meets the towers)
        slit = _arch(mid - 0.28, mid + 0.28, 25.0, 26.4)
        self.poly(pl, [[(0, zb), (Lw, zb), (Lw, zg), (mid, Z_GABLE - 0.16), (0, zg)], big[::-1], slit[::-1]], BR)
        self.rim(pl, slit, 0.0, -0.2, BR)
        self.mb.face([pl(p[0], p[1], -0.2) for p in slit], DK)
        self.rim(pl, big, 0.0, -0.25, ST)
        z0, z1, w, gap = BIG
        holes = []
        for k in (-1, 1):
            m = mid + k * (gap + w) / 2
            holes.append(self.glazed(lambda s, z, out=0.0: pl(s, z, out - 0.25), _arch(m - w / 2, m + w / 2, z0, z1), 'west',
                                     frame=0.12, proud=0.06, rec=0.25))
        zr, rr = ROSE
        circ = [(mid + (rr + 0.32) * math.cos(2 * math.pi * k / 24), zr + (rr + 0.32) * math.sin(2 * math.pi * k / 24)) for k in range(24)]
        inner = [(mid + rr * math.cos(2 * math.pi * k / 24), zr + rr * math.sin(2 * math.pi * k / 24)) for k in range(24)]
        self.poly(pl, [circ, inner[::-1]], ST, out=-0.19)
        self.rim(pl, circ, -0.19, -0.25, ST, inward=False)
        self.rim(pl, inner, -0.19, -0.5, ST)
        u0, u1, v0, v1 = _cell('rose', pad=4.0)
        self.mb.face([pl(p[0], p[1], -0.5) for p in inner], GL,
                     uvs=[((u0 + u1) / 2 + (u1 - u0) / 2 * 0.96 * (p[0] - mid) / rr, (v0 + v1) / 2 + (v1 - v0) / 2 * 0.96 * (p[1] - zr) / rr) for p in inner])
        self.poly(pl, [big, inner[::-1]] + [h[::-1] for h in holes], ST, out=-0.25)
        self.gable_coping(ug, vt, zg, out=-1)
        # the doors under the porch
        for k in (-1, 0, 1):
            m = mid + k * PORCH['w'] / 3
            d = [(m - 1.1, 0.04), (m + 1.1, 0.04), (m + 1.1, 3.5), (m - 1.1, 3.5)]
            u0, u1, v0, v1 = _cell('door')
            self.mb.face([pl(p[0], p[1], 0.05) for p in d], GL, uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
            self.box(ug - 0.08, -(m - mid), 3.5, 3.72, 0.16, 2.6, ST)
        self.porch(ug)

    def porch(self, ug):
        """the porch: a front wall of three arches 1.25 m before the towers' faces, wider than the gap between them,
        a short wall at each end back to the tower's face; its roof, the parapet over it, the pinnacles"""
        L = self.L
        p = PORCH
        hw, uw, ut = p['w'] / 2, -L / 2 - p['out'], -L / 2
        aw, zs, za = p['arch']
        th = 0.5                                                        # (the walls' thickness)

        def arcade(pl, Lw, mids, w, back=False, out=0.0):
            """a wall from the floor to the parapet's top with pointed openings down to the floor"""
            loop = [(0, 0.0)]
            ops = []
            for m in mids:
                op = _arch(m - w / 2, m + w / 2, 0.0, za, rise=za - zs)
                ops.append(op)
                loop += [op[0]] + op[:1:-1] + [op[1]]
            loop += [(Lw, 0.0), (Lw, p['par']), (0, p['par'])]
            self.poly(pl, [loop], ST, out=out, back=back)
            return ops

        faces = [((uw, hw), (uw, -hw), [p['w'] * (k + 0.5) / 3 for k in range(3)], 3),           # west
                 ((uw, -hw), (ut, -hw), [], 1), ((ut, hw), (uw, hw), [], 1)]
        for a, b, mids, n in faces:
            pl, Lw = self.plane(a, b)
            ops = arcade(pl, Lw, mids, aw)
            arcade(pl, Lw, mids, aw, back=True, out=-th)
            for op in ops:
                self.rim(pl, op[1:] + op[:1], 0.0, -th, ST, closed=False)
            for k in range(n):                                          # (the parapet's cut stone: the atlas cell over each bay)
                s0, s1 = Lw * k / n + 0.2, Lw * (k + 1) / n - 0.2
                u0, u1, v0, v1 = _cell('parapet', u0=k / 3 + 0.01, u1=(k + (1 if n == 3 else 0.27)) / 3 - 0.01)
                self.mb.face([pl(s0, p['roof'] + 0.35, 0.03), pl(s1, p['roof'] + 0.35, 0.03), pl(s1, p['par'] - 0.2, 0.03), pl(s0, p['par'] - 0.2, 0.03)],
                             GL, uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
        um = (uw + ug) / 2
        self.box(um, 0.0, p['roof'] - 0.2, p['roof'], ug - uw - 0.1, p['w'] - 0.1, ST)                     # (the roof and the ceiling)
        # (the floor: stone flush with the yard, so that the walker's feet stay on it; tools/yro97.py church_porch_piers
        # keeps the walker out of the piers)
        self.box(um - 0.3, 0.0, -0.5, 0.04, ug - uw + 0.6, p['w'] + 0.5, ST, skip=('bottom',))
        for z0, z1, o in ((p['roof'] - 0.12, p['roof'] + 0.12, 0.12), (p['par'], p['par'] + 0.14, 0.1)):     # (the cornice, the coping)
            self.box(uw + th / 2, 0.0, z0, z1, th + 2 * o, p['w'] + 2 * o, ST)
            for sgn in (-1, 1):
                self.box((uw + th + ut) / 2, sgn * (hw - th / 2), z0, z1, ut - uw - th, th + 2 * o, ST)
        for k in range(4):                                              # (the four pinnacles over the piers)
            self.pinnacle(uw + th / 2, -hw + 0.3 + (p['w'] - 0.6) * k / 3, p['par'] - 0.4, p['par'] + 0.45, 0.33, p['pin'] - p['par'] - 0.57, mat=ST)

    def build(self):
        self.tower(-1)
        self.tower(1)
        self.nave()
        self.front()


def church97(mb, b, ground):
    Church(mb, b, ground).build()
