"""Clipped shrubs, hedges and flower beds (campus.json `shrubs`).

Each is a body with the clipped outline plus sprig cards standing out of it:
- body (material hedge_*, opaque): a rounded box (the hedges and the pansy border: flat top, straight sides, rounded
  arrises, a battered face tucked in at the foot), or a solid of revolution (the round boxwood, the cone, the azalea
  mounds). The web app lays the clipped-surface texture on it from three sides in world space (web/src/hedges.js), so
  pieces set in a row read as one hedge: their faces carry one continuous leaf pattern. A hedge piece is 3.5 % lower
  and narrower at its +x end than at its -x end, so where it overlaps the next piece of the row the next one's face is
  in front (no z-fighting of two coincident faces).
- cards (material leaf_*, alpha-tested 2x2 atlas, tools/make_shrub_textures.py): sprigs anchored a few cm inside the
  body and leaning out of it, which break the outline into leaves wherever it is seen edge on; they take the body's
  normal at their foot (they shade like the face they grow from) and its occlusion.
Vertex colour: occlusion. The foot of every body is dark (the shade under the clipped face, bare stems).
The shapes are seeded from the kind's name (zlib.crc32), so every build is the same.
"""
import bisect, math, random, zlib
from mathutils import Vector
from common import MeshBuilder

# card cell size in metres across (tools/make_shrub_textures.py CARD_M: the leaves come out at their real size)
CARD_M = {'boxwood': 0.22, 'azalea_summer': 0.32, 'azalea': 0.32, 'azalea_red': 0.32, 'azalea_violet': 0.34,
          'azalea_autumn': 0.32, 'pansy': 0.2}


class ShrubBuilder(MeshBuilder):
    """A MeshBuilder with a normal for every face corner (custom split normals), and the body's surface kept as
    triangles (point, normal, occlusion at each corner) to seat the cards on."""
    def __init__(self, name):
        super().__init__(name)
        self.cn = []
        self.surf = []

    def face(self, pts, mat, uvs=None, smooth=False, col=None, panes=None, normals=None):
        n0 = len(self.faces)
        super().face(pts, mat, uvs=uvs, smooth=smooth, col=col, panes=panes)
        if len(self.faces) > n0:
            self.cn.append(normals)

    def build(self, collection=None):
        ob = super().build(collection)
        me = ob.data
        try:
            base = [tuple(c.vector) for c in me.corner_normals]
        except AttributeError:          # (before Blender 4.1)
            me.calc_normals_split()
            base = [tuple(l.normal) for l in me.loops]
        out = []
        for poly, ns in zip(me.polygons, self.cn):
            for k, li in enumerate(poly.loop_indices):
                out.append(tuple(ns[k]) if ns else base[li])
        me.normals_split_custom_set(out)
        return ob


def _ss(e0, e1, x):
    if e1 <= e0:
        return 1.0 if x >= e1 else 0.0
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def _normal_of(F, a, b, eps=1e-4):
    """unit normal of a parametric surface F(a, b) by central differences (a around, b up: outward for CCW a)"""
    da = (F(a + eps, b) - F(a - eps, b))
    db = (F(a, b + eps) - F(a, b - eps))
    n = da.cross(db)
    return n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))


def _quad(mb, P, N, C, mat, tag):
    """a body quad (or triangle when two corners coincide) with its normals and occlusion; kept for the cards"""
    pts, ns, cs = [], [], []
    for p, n, c in zip(P, N, C):
        if pts and (p - pts[-1]).length < 1e-6:
            continue
        pts.append(p); ns.append(n); cs.append(c)
    if len(pts) > 3 and (pts[0] - pts[-1]).length < 1e-6:
        pts.pop(); ns.pop(); cs.pop()
    if len(pts) < 3:
        return
    mb.face(pts, mat, smooth=tag, col=[(c, c, c, 1) for c in cs], normals=ns)
    for k in range(1, len(pts) - 1):
        mb.surf.append(((pts[0], pts[k], pts[k + 1]), (ns[0], ns[k], ns[k + 1]), (cs[0], cs[k], cs[k + 1])))


# ----------------------------------------------------------------------------- bodies
def rounded_box(mb, A, B, H, R, mat, ao, taper=0.0, batter=0.0, tuck=(0.0, 0.12), z0=-0.05, segs=(2, 2, 2)):
    """A clipped block: half length A (x), half width B (y), from z0 up to H, its arrises rounded with radii
    R = (rx, ry, rz) (rz: the top arrises), no bottom face. taper: how much lower and narrower the +x end is;
    batter: how much wider the foot is than the top; tuck = (inset, height): the face drawn in at the foot.
    segs: segments across each half of a rounded arris along x, y, z."""
    rx, ry, rz = R
    lo = (-A + rx, -B + ry, z0)          # the core box (the foot is not rounded: it goes into the ground)
    hi = (A - rx, B - ry, H - rz)
    rr = (rx, ry, rz)

    def coords(E, r, ns):
        """grid coordinates along one axis of the cube: the flat face, then ns steps across each rounded arris"""
        up = [E - r] + [E - r * (1 - (k + 1) / ns) for k in range(ns - 1)] + [E]
        return [-v for v in reversed(up)] + up

    def deform(p):
        x, y, z = p
        f = 1 - taper * (x / A + 1) / 2
        zz = z0 + (z - z0) * f
        h = (zz - z0) / (H - z0)
        s = (1 + batter * (1 - h)) * (1 - tuck[0] * (1 - _ss(0.0, tuck[1], zz - z0)))
        return Vector((x, y * s * f, zz))

    def surf(v):
        """cube point v -> rounded-box point (before deform), and its normal"""
        q = [min(hi[i], max(lo[i], v[i])) for i in range(3)]
        d = Vector([(v[i] - q[i]) / rr[i] for i in range(3)])
        if d.length < 1e-9:
            d = Vector((0, 0, 1))
        n = d.normalized()
        p = Vector(q) + Vector((n.x * rx, n.y * ry, n.z * rz))
        g = Vector((n.x / rx, n.y / ry, n.z / rz))
        return p, g.normalized()

    def point(v):
        p, n = surf(v)
        q = deform(p)
        # the deformed normal: J^-T n by finite differences
        e = 1e-4
        J = [(deform(p + Vector(ax) * e) - deform(p - Vector(ax) * e)) / (2 * e) for ax in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
        # columns J[0..2]; normal = cross of two tangents of the deformed surface
        t1 = n.orthogonal().normalized()
        t2 = n.cross(t1)
        dt1 = J[0] * t1.x + J[1] * t1.y + J[2] * t1.z
        dt2 = J[0] * t2.x + J[1] * t2.y + J[2] * t2.z
        nn = dt1.cross(dt2)
        if nn.dot(n) < 0:
            nn = -nn
        return q, nn.normalized(), ao(q, nn.normalized())

    xs = coords(A, rx, segs[0])
    ys = coords(B, ry, segs[1])
    zt = [z0 + tuck[1] * 0.5, z0 + tuck[1]] if tuck[0] > 0 else []
    zs = [z0] + zt + [H - rz] + [H - rz * (1 - (k + 1) / segs[2]) for k in range(segs[2] - 1)] + [H]
    tag = 'box%d' % len(mb.faces)
    grid = {}

    def G(v):
        k = (round(v.x, 5), round(v.y, 5), round(v.z, 5))
        if k not in grid:
            grid[k] = point(v)
        return grid[k]

    def sheet(U, V, f):
        for i in range(len(U) - 1):
            for j in range(len(V) - 1):
                cs = [f(U[i], V[j]), f(U[i + 1], V[j]), f(U[i + 1], V[j + 1]), f(U[i], V[j + 1])]
                P = [G(c) for c in cs]
                _quad(mb, [p[0] for p in P], [p[1] for p in P], [p[2] for p in P], mat, tag)
    sheet(xs, ys, lambda u, v: Vector((u, v, H)))                       # top (CCW from above)
    sheet(xs, zs, lambda u, v: Vector((u, -B, v)))                      # -y face
    sheet(list(reversed(xs)), zs, lambda u, v: Vector((u, B, v)))       # +y face
    sheet(ys, zs, lambda u, v: Vector((A, u, v)))                       # +x end
    sheet(list(reversed(ys)), zs, lambda u, v: Vector((-A, u, v)))      # -x end


def revolve(mb, prof, mat, ao, seg=16, plan=None, lift=None, z0=-0.05, off=(0.0, 0.0)):
    """A solid of revolution: prof(t) -> (r, z) for t 0 (foot) .. 1 (top, r = 0); plan(a) -> radius factor at azimuth a
    (an irregular outline), applied less toward the top; lift(a) -> height factor at azimuth a (an uneven top); off:
    its axis' place (x, y)."""
    rings = len(prof) - 1
    tag = 'rev%d' % len(mb.faces)

    def F(a, t):
        k = min(rings - 1e-9, max(0.0, t * rings))
        j = int(k)
        f = k - j
        r0, z0_ = prof[j]
        r1, z1_ = prof[min(j + 1, rings)]
        r, z = r0 + (r1 - r0) * f, z0_ + (z1_ - z0_) * f
        w = plan(a) if plan else 1.0
        w = 1 + (w - 1) * (1 - 0.5 * t)
        if lift and z > 0:
            z *= 1 + (lift(a) - 1) * min(1.0, t * 1.5) * (1 - t * t)
        return Vector((off[0] + r * w * math.cos(a), off[1] + r * w * math.sin(a), z))

    P, N, Cc = {}, {}, {}
    for j in range(rings + 1):
        t = j / rings
        for i in range(seg):
            a = 2 * math.pi * i / seg
            p = F(a, t)
            if j == rings:
                n = Vector((0, 0, 1))
            else:
                n = _normal_of(F, a, min(max(t, 1e-3), 1 - 1e-3), 1e-3)
            P[(i, j)], N[(i, j)], Cc[(i, j)] = p, n, ao(p, n)
    for j in range(rings):
        for i in range(seg):
            k = (i + 1) % seg
            ids = [(i, j), (k, j), (k, j + 1), (i, j + 1)]
            if j == rings - 1:
                ids = [(i, j), (k, j), (0, rings)]
                P[(0, rings)] = F(0, 1.0)
            _quad(mb, [P[c] for c in ids], [N[c] for c in ids], [Cc[c] for c in ids], mat, tag)


# ----------------------------------------------------------------------------- cards
def cards(mb, rnd, n, mat, cell_m, W=(0.8, 1.2), Hf=(0.55, 0.8), tilt=(15, 60), depth=0.04, weight=None,
          bright=1.12):
    """n sprig cards seated on the body (area-weighted, weight(p, normal) -> 0..1 thins them), each a cell of the
    atlas cell_m metres across scaled by W, its height Hf of its width, sunk depth into the body and leaning tilt
    degrees off the face's normal"""
    tris = mb.surf
    areas = []
    tot = 0.0
    for (a, b, c), _, _ in tris:
        tot += ((b - a).cross(c - a)).length / 2
        areas.append(tot)
    made = 0
    tries = 0
    while made < n and tries < n * 20:
        tries += 1
        k = bisect.bisect_left(areas, rnd.uniform(0, tot))
        (a, b, c), (na, nb, nc), (ca, cb, cc) = tris[min(k, len(tris) - 1)]
        u, v = rnd.random(), rnd.random()
        if u + v > 1:
            u, v = 1 - u, 1 - v
        p = a + (b - a) * u + (c - a) * v
        nrm = (na * (1 - u - v) + nb * u + nc * v).normalized()
        occ = ca * (1 - u - v) + cb * u + cc * v
        if weight and rnd.random() > weight(p, nrm):
            continue
        made += 1
        w0 = nrm.orthogonal().normalized()
        ang = rnd.uniform(0, 2 * math.pi)
        t0 = nrm.cross(w0)
        w0 = (w0 * math.cos(ang) + t0 * math.sin(ang)).normalized()     # the card's width axis, in the face
        t = nrm.cross(w0)                                               # the way it leans
        tl = math.radians(rnd.uniform(*tilt))
        up = (nrm * math.cos(tl) + t * math.sin(tl)).normalized()
        wd = cell_m * rnd.uniform(*W)
        ht = wd * rnd.uniform(*Hf)
        base = p - nrm * depth
        q = [base - w0 * wd / 2, base + w0 * wd / 2, base + w0 * wd / 2 + up * ht, base - w0 * wd / 2 + up * ht]
        cell = rnd.randrange(4)
        u0, v0 = (cell % 2) * 0.5, (cell // 2) * 0.5
        # the cell is cropped to the card's height: its sprig stands on the cell's bottom edge
        vt = v0 + 0.5 * min(1.0, ht / wd)
        uv = [(u0, v0), (u0 + 0.5, v0), (u0 + 0.5, vt), (u0, vt)]
        ntip = (nrm * 0.8 + up * 0.2).normalized()
        cb_, ct_ = occ * 0.95, min(1.0, occ * bright)
        mb.face(q, mat, uvs=uv, col=[(cb_, cb_, cb_, 1), (cb_, cb_, cb_, 1), (ct_, ct_, ct_, 1), (ct_, ct_, ct_, 1)],
                normals=[nrm, nrm, ntip, ntip])


# ----------------------------------------------------------------------------- the kinds
def _ao_box(H, foot=0.16, lo=0.3, side=0.86):
    """occlusion of a clipped block: dark at the foot, the faces a little darker than the top"""
    def f(p, n):
        z = p.z
        o = lo + (1 - lo) * _ss(-0.05, foot + 0.12, z)
        o *= side + (1 - side) * max(0.0, n.z)
        return max(0.2, min(1.0, o))
    return f


def _ao_round(H, foot=0.35, lo=0.28, side=0.84):
    def f(p, n):
        o = lo + (1 - lo) * _ss(-0.05, foot, p.z)
        o *= side + (1 - side) * max(0.0, n.z)
        o *= 0.9 + 0.1 * min(1.0, max(0.0, p.z / H))
        return max(0.2, min(1.0, o))
    return f


def _wobble(rnd, amp, lobes=(2, 5)):
    """an irregular outline: a few soft lobes round the plan"""
    terms = [(rnd.randint(*lobes), rnd.uniform(0, 2 * math.pi), rnd.uniform(0.4, 1.0)) for _ in range(3)]
    s = sum(t[2] for t in terms)
    return lambda a: 1 + amp * sum(w * math.sin(k * a + ph) for k, ph, w in terms) / s


def _tier_pad(mb, rnd, z0, z1, r, rt, mat, lo=0.32, off=(0.0, 0.0), wob=0.06):
    """One clipped pad of a tiered conifer (향나무 · 주목 trained in tiers): a cushion from z0 to z1, r across at its
    widest, its underside drawn in to the trunk (radius rt) and shaded, the top domed. Seated on mb.surf for the cards."""
    h = z1 - z0
    prof = [(rt, z0 + 0.16 * h), (0.5 * r, z0 + 0.03 * h), (0.82 * r, z0 + 0.1 * h), (0.97 * r, z0 + 0.27 * h),
            (1.0 * r, z0 + 0.45 * h), (0.94 * r, z0 + 0.65 * h), (0.78 * r, z0 + 0.83 * h), (0.52 * r, z0 + 0.95 * h),
            (0.24 * r, z0 + 0.995 * h), (0.0, z1)]

    def ao(p, n):
        o = lo + (1 - lo) * _ss(z0 - 0.02, z0 + 0.6 * h, p.z)
        o *= 0.62 + 0.38 * _ss(-0.7, 0.4, n.z)                # the underside in the pad's own shade
        o *= 0.88 + 0.12 * min(1.0, max(0.0, p.z / max(z1, 0.5)))
        return max(0.18, min(1.0, o))
    revolve(mb, prof, mat, ao, seg=14, plan=_wobble(rnd, wob), off=off)


def _bough(mb, pts, r0, r1, mat, sides=6, shade=(0.45, 0.7)):
    """a bare trunk or bough along the points (x, y, z), r0 thick at its first and r1 at its last (bark, as _tier_trunk)"""
    P = [Vector(q) for q in pts]
    n = len(P)
    rings = []
    for k in range(n):
        tg = (P[min(k + 1, n - 1)] - P[max(k - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(tg.z) < 0.9 else Vector((1, 0, 0))
        u = ref.cross(tg).normalized()
        v = tg.cross(u)
        r = r0 + (r1 - r0) * k / (n - 1)
        rings.append([P[k] + (u * math.cos(2 * math.pi * i / sides) + v * math.sin(2 * math.pi * i / sides)) * r for i in range(sides)])
    vl = 0.0
    for k in range(n - 1):
        sl = (P[k + 1] - P[k]).length
        ra = r0 + (r1 - r0) * k / (n - 1)
        circ = 2 * math.pi * max(ra, 0.05)
        c0, c1 = (shade[0] + (shade[1] - shade[0]) * j / (n - 1) for j in (k, k + 1))
        for i in range(sides):
            j = (i + 1) % sides
            q = [rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]]
            uv = [(i / sides * circ, vl), ((i + 1) / sides * circ, vl), ((i + 1) / sides * circ, vl + sl), (i / sides * circ, vl + sl)]
            mb.face(q, mat, uvs=uv, smooth='trunk', col=[(c0, c0, c0, 1), (c0, c0, c0, 1), (c1, c1, c1, 1), (c1, c1, c1, 1)])
        vl += sl


def _tier_trunk(mb, z1, r0, r1, mat, sides=6):
    """the bare trunk that shows below and between the pads (bark, UV along it as blender/vegetation.py tube)"""
    pts = [(0.0, -0.1), (0.015, z1 * 0.5), (-0.01, z1)]
    rr = [r0, (r0 + r1) / 2, r1]
    vl = 0.0
    for k in range(len(pts) - 1):
        (xa, za), (xb, zb) = pts[k], pts[k + 1]
        sl = math.hypot(xb - xa, zb - za)
        for i in range(sides):
            a0, a1 = 2 * math.pi * i / sides, 2 * math.pi * (i + 1) / sides
            q = [Vector((xa + rr[k] * math.cos(a0), rr[k] * math.sin(a0), za)), Vector((xa + rr[k] * math.cos(a1), rr[k] * math.sin(a1), za)),
                 Vector((xb + rr[k + 1] * math.cos(a1), rr[k + 1] * math.sin(a1), zb)), Vector((xb + rr[k + 1] * math.cos(a0), rr[k + 1] * math.sin(a0), zb))]
            circ = 2 * math.pi * max(rr[k], 0.05)
            uv = [(i / sides * circ, vl), ((i + 1) / sides * circ, vl), ((i + 1) / sides * circ, vl + sl), (i / sides * circ, vl + sl)]
            c0, c1 = 0.45 + 0.25 * min(1.0, za / z1), 0.45 + 0.25 * min(1.0, zb / z1)
            mb.face(q, mat, uvs=uv, smooth='trunk', col=[(c0, c0, c0, 1), (c0, c0, c0, 1), (c1, c1, c1, 1), (c1, c1, c1, 1)])
        vl += sl


def make_shrub(kind, seed=0):
    rnd = random.Random(zlib.crc32(kind.encode()) + seed)
    mb = ShrubBuilder(f'shrub_{kind}')
    if kind == 'hedge_low':
        # one 1.84 m piece of the low clipped boxwood hedge (백양로's planting strips, the 정문 island, the garden
        # beds), local x along the hedge: 0.8 m wide, 0.56 m high, flat top, straight battered faces
        rounded_box(mb, 0.92, 0.39, 0.58, (0.07, 0.08, 0.08), 'hedge_boxwood', _ao_box(0.58), taper=0.035,
                    batter=0.05, tuck=(0.08, 0.2), segs=(1, 2, 2))
        cards(mb, rnd, 52, 'leaf_boxwood', CARD_M['boxwood'], W=(0.7, 1.05), Hf=(0.5, 0.75), tilt=(10, 65),
              depth=0.035, weight=lambda p, n: 0.15 if p.z < 0.12 else 0.55 + 0.45 * max(0.0, n.z))
    elif kind == 'hedge_blob':
        # a clipped block of boxwood (연희관's garden): 2.0 x 1.36 x 0.95 m, the arrises rounder
        rounded_box(mb, 1.0, 0.68, 0.95, (0.16, 0.16, 0.15), 'hedge_boxwood', _ao_box(0.95, foot=0.2), taper=0.035,
                    batter=0.05, tuck=(0.07, 0.16), segs=(2, 2, 2))
        cards(mb, rnd, 96, 'leaf_boxwood', CARD_M['boxwood'], W=(0.75, 1.1), Hf=(0.5, 0.78), tilt=(10, 65),
              depth=0.035, weight=lambda p, n: 0.15 if p.z < 0.15 else 0.55 + 0.45 * max(0.0, n.z))
    elif kind == 'topiary_round':
        # 둥근 회양목 · 주목 (reference/2003_봄_언더우드관정원_남쪽계단_벚나무.jpg): a dome wider than high, the clipped
        # face drawn in under its widest part to a narrow, shaded foot
        prof = [(0.40, -0.05), (0.51, 0.07), (0.64, 0.18), (0.73, 0.32), (0.77, 0.46), (0.75, 0.62), (0.68, 0.78),
                (0.56, 0.92), (0.39, 1.03), (0.2, 1.1), (0.0, 1.13)]
        revolve(mb, prof, 'hedge_boxwood', _ao_round(1.13, foot=0.4), seg=16, plan=_wobble(rnd, 0.025))
        cards(mb, rnd, 84, 'leaf_boxwood', CARD_M['boxwood'], W=(0.7, 1.05), Hf=(0.5, 0.75), tilt=(10, 65),
              depth=0.035, weight=lambda p, n: 0.2 if p.z < 0.2 else 0.5 + 0.5 * max(0.0, n.z))
    elif kind == 'topiary_cone':
        # 원뿔 향나무 (연희관 · 언더우드관 gardens): a clipped cone with a slight swell, its foliage down to the ground
        prof = [(0.5, -0.05), (0.66, 0.08), (0.74, 0.25), (0.72, 0.5), (0.65, 0.85), (0.55, 1.2), (0.43, 1.55),
                (0.3, 1.9), (0.17, 2.2), (0.06, 2.42), (0.0, 2.48)]
        revolve(mb, prof, 'hedge_boxwood', _ao_round(2.48, foot=0.3), seg=14, plan=_wobble(rnd, 0.03))
        cards(mb, rnd, 84, 'leaf_boxwood', CARD_M['boxwood'], W=(0.7, 1.05), Hf=(0.5, 0.75), tilt=(15, 60),
              depth=0.035, weight=lambda p, n: 0.25 if p.z < 0.15 else 0.7 + 0.3 * max(0.0, n.z))
    elif kind == 'juniper_tiers':
        # 향나무 clipped in two tiers on a bare trunk (백양로's boxwood verges: the April 2011 roadview, every verge
        # from the gate to the library; the May 1997 photo's flat-topped pads with a darker skirt under some): a broad
        # cushion low on the trunk, a gap where the trunk shows, a smaller domed one over it; 1.45 m high, 1.25 m across
        _tier_trunk(mb, 1.3, 0.06, 0.035, 'bark_pine')
        for (z0, z1, r) in ((0.36, 0.74, 0.63), (0.86, 1.45, 0.5)):
            _tier_pad(mb, rnd, z0, z1, r, 0.05, 'hedge_boxwood')
        cards(mb, rnd, 110, 'leaf_boxwood', CARD_M['boxwood'], W=(0.7, 1.05), Hf=(0.5, 0.75), tilt=(10, 65),
              depth=0.035, weight=lambda p, n: 0.12 if n.z < -0.25 else 0.45 + 0.55 * max(0.0, n.z))
    elif kind == 'yew_tiers':
        # 주목 · 향나무 clipped in stacked tiers (연희관 앞 정원: the December 2010 roadview from 한경길, the 2008 and
        # 2026 ones from the drives; the 2003 spring photo): five rounded pads narrowing upwards, the trunk showing in
        # the gaps between them, a small dome on top; 2.75 m high, 1.2 m across at the foot
        _tier_trunk(mb, 2.55, 0.08, 0.04, 'bark_pine')
        tiers = ((0.08, 0.66, 0.6), (0.72, 1.22, 0.51), (1.28, 1.7, 0.43), (1.76, 2.12, 0.35), (2.18, 2.47, 0.26), (2.52, 2.75, 0.15))
        for k, (z0, z1, r) in enumerate(tiers):
            _tier_pad(mb, rnd, z0, z1, r * rnd.uniform(0.94, 1.06), 0.06 if k < 3 else 0.045, 'hedge_boxwood',
                      lo=0.4 if k == 0 else 0.32)
        cards(mb, rnd, 150, 'leaf_boxwood', CARD_M['boxwood'], W=(0.7, 1.05), Hf=(0.5, 0.75), tilt=(10, 65),
              depth=0.035, weight=lambda p, n: 0.12 if n.z < -0.25 else 0.45 + 0.55 * max(0.0, n.z))
    elif kind == 'pine_cloud':
        # 다듬은 조경 소나무 (대우관 상뜰: reference/대우관_2024_정면과_상뜰.jpg, 대우관_블로그_본관_정면_상뜰.jpg): a leaning
        # trunk that bends back over its foot, its boughs trained level and clipped into separate cushions of needles,
        # broad ones on the long low boughs, smaller ones up the trunk, a domed one on top; 4.5 m high, 5 m across
        bend = [(0.0, 0.0, -0.1), (0.22, 0.04, 1.1), (0.58, 0.02, 2.2), (0.42, -0.04, 3.1), (0.22, 0.0, 3.8)]
        _bough(mb, bend, 0.17, 0.07, 'bark_pine', sides=7)

        def at(z):
            for (xa, ya, za), (xb, yb, zb) in zip(bend, bend[1:]):
                if z <= zb:
                    f = (z - za) / (zb - za)
                    return (xa + (xb - xa) * f, ya + (yb - ya) * f, z)
            return bend[-1]
        pads = [(1.75, 0.3, 1.7, 2.35, 1.3), (-1.05, 1.0, 1.9, 2.5, 1.1), (-0.4, -1.4, 2.05, 2.65, 1.05), (1.55, -1.0, 2.5, 3.1, 1.0),
                (-0.7, 0.3, 2.85, 3.45, 1.0), (1.05, 0.85, 3.1, 3.65, 0.85), (0.25, -0.05, 3.55, 4.5, 1.25)]
        for (px, py, z0, z1, r) in pads:
            a = at(z0 - 0.35)
            _bough(mb, [a, ((a[0] + px) / 2, (a[1] + py) / 2, z0 - 0.12), (px, py, z0 + 0.12)], 0.065, 0.035, 'bark_pine', sides=5,
                   shade=(0.5, 0.6))
            _tier_pad(mb, rnd, z0, z1, r, 0.05, 'hedge_boxwood', lo=0.36, off=(px, py), wob=0.1)
        cards(mb, rnd, 230, 'leaf_boxwood', CARD_M['boxwood'], W=(0.75, 1.1), Hf=(0.5, 0.75), tilt=(10, 65),
              depth=0.035, weight=lambda p, n: 0.1 if n.z < -0.25 else 0.45 + 0.55 * max(0.0, n.z))
    elif kind == 'bush':
        # a free-grown azalea bush round the halls (영산홍: magenta in April, green in May): an uneven mound,
        # its outline all leaves
        prof = [(0.5, -0.05), (0.62, 0.1), (0.7, 0.28), (0.7, 0.48), (0.62, 0.68), (0.46, 0.85), (0.24, 0.95), (0.0, 0.98)]
        revolve(mb, prof, 'hedge_azalea', _ao_round(0.98, foot=0.38), seg=14, plan=_wobble(rnd, 0.12),
                lift=_wobble(rnd, 0.1, (2, 4)))
        cards(mb, rnd, 120, 'leaf_azalea', CARD_M['azalea'], W=(0.75, 1.15), Hf=(0.55, 0.85), tilt=(10, 70),
              depth=0.06, weight=lambda p, n: 0.3 if p.z < 0.15 else 0.6 + 0.4 * max(0.0, n.z))
    elif kind == 'azalea_red':
        # 철쭉 massed in the beds (the 정문 island, the May 1997 photo; round the eagle, the April 2011 roadview): low
        # clipped mounds with a flat top, set about a metre apart so that a bed closes up into one flat-topped mass
        # with rounded edges, not a heap of balls; small trusses of flowers on the shoots' tips in May
        prof = [(0.66, -0.05), (0.77, 0.08), (0.82, 0.2), (0.8, 0.34), (0.72, 0.47), (0.58, 0.57), (0.38, 0.63),
                (0.18, 0.655), (0.0, 0.66)]
        revolve(mb, prof, 'hedge_azalea_red', _ao_round(0.66, foot=0.26), seg=14, plan=_wobble(rnd, 0.05))
        cards(mb, rnd, 100, 'leaf_azalea_red', CARD_M['azalea_red'], W=(0.7, 1.0), Hf=(0.45, 0.7), tilt=(15, 55),
              depth=0.06, weight=lambda p, n: 0.3 if p.z < 0.12 else 0.55 + 0.45 * max(0.0, n.z))
    elif kind == 'azalea_violet':
        # 진달래 on 용재관's bank (reference/용재관.jpg, April): a loose rounded mound of violet bloom on thin twigs,
        # taller than the clipped 철쭉, its outline open
        prof = [(0.5, -0.05), (0.64, 0.12), (0.72, 0.32), (0.71, 0.54), (0.62, 0.76), (0.45, 0.94), (0.22, 1.05), (0.0, 1.08)]
        revolve(mb, prof, 'hedge_azalea_violet', _ao_round(1.08, foot=0.3, lo=0.45), seg=14, plan=_wobble(rnd, 0.18),
                lift=_wobble(rnd, 0.12, (2, 4)))
        cards(mb, rnd, 136, 'leaf_azalea_violet', CARD_M['azalea_violet'], W=(0.8, 1.2), Hf=(0.6, 0.9),
              tilt=(10, 70), depth=0.07, weight=lambda p, n: 0.3 if p.z < 0.15 else 0.6 + 0.4 * max(0.0, n.z))
    elif kind == 'pansy_bed':
        # one 1.96 m length of the pansy border on top of the banks by the steps up to 언더우드관 정원 (the 2003
        # spring photo): a low cushion of leaves and flowers (local x along the border)
        rounded_box(mb, 0.98, 0.36, 0.13, (0.08, 0.1, 0.07), 'hedge_pansy', _ao_box(0.13, foot=0.04, lo=0.55),
                    taper=0.03, tuck=(0.0, 0.0), z0=-0.1, segs=(1, 2, 1))
        cards(mb, rnd, 46, 'leaf_pansy', CARD_M['pansy'], W=(0.7, 1.0), Hf=(0.7, 0.95), tilt=(0, 35), depth=0.05,
              weight=lambda p, n: 0.15 + 0.85 * max(0.0, n.z))
    return mb


def far_version(ob, cards_kept=3, body_ratio=0.4):
    """The shrub seen from afar (web/src/main.js SHRUB_FAR): split by material, one card in cards_kept left and the
    body (not a tier trunk) collapsed to body_ratio of its faces. Returns the objects; ob is left as it was."""
    import bpy, bmesh
    far = ob.copy()
    far.data = ob.data.copy()
    bpy.context.scene.collection.objects.link(far)
    bpy.ops.object.select_all(action='DESELECT')
    far.select_set(True)
    bpy.context.view_layer.objects.active = far
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.mode_set(mode='OBJECT')
    parts = list(bpy.context.selected_objects)
    for p in parts:
        name = p.data.materials[0].name
        if name.startswith('leaf_'):
            bm = bmesh.new()
            bm.from_mesh(p.data)
            bm.faces.ensure_lookup_table()
            drop = [f for i, f in enumerate(bm.faces) if i % cards_kept]
            bmesh.ops.delete(bm, geom=drop, context='FACES')
            bm.to_mesh(p.data)
            bm.free()
        elif not name.startswith('bark'):
            d = p.modifiers.new('far', 'DECIMATE')
            d.decimate_type = 'COLLAPSE'
            d.ratio = body_ratio
            d.use_collapse_triangulate = True
    return parts
