"""Bronze statues of the 1997 campus, modelled from photographs.

언더우드 동상 (Horace G. Underwood, the 1955 statue at the entrance of the Underwood courtyard; photos: Wikimedia
Commons, Category:Statue of Horace Grant Underwood, 2009 - 2019, and the 2010 roadview): a balding man with a full
moustache in a morning coat with tails over a waistcoat of six buttons, both arms held out in front of him, palms up,
on a bronze plate on a tapering light granite pedestal (a cavetto cap, the inscribed plaque on the front, a base block
with a sloped wash) standing on an octagonal slab, an octagon of rock-faced blocks and a round platform in a curb ring.
The figure is sculpted densely and baked onto a light mesh (blender/sculpt.py); its head and hands start from the
Blender Foundation's CC0 "Human Base Meshes".

독수리상 (unveiled 9 May 1970; Yonsei: "12.3m high with a 2.5t bronze eagle on a rectangular prism tower. The eagle is
2.6m tall and 5.2m wide ... the statue of Yonseian carved on all four sides"; photos: 2024 campus photo, the 1997 aerial
photo, the 2024 virtual campus): a bronze eagle with its wings raised in a wide V, primaries spread like fingers,
gripping a rock on top of a tall white square column that stands on a pedestal with figures carved on its four faces.

Both return Blender objects in their local frame (front = -Y, ground at z = 0); blender/build.py places them.
"""
import math
import os
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

import sculpt
from common import MeshBuilder, material, ROOT


# ----------------------------------------------------------------------------- helpers
def _bake(ob):
    """Apply every modifier (and an armature deform) into a new plain mesh object."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=False, depsgraph=dg)
    out = bpy.data.objects.new(ob.name + '_baked', me)
    out.matrix_world = ob.matrix_world.copy()
    bpy.context.scene.collection.objects.link(out)
    return out


def loft(mb, rings, mat, cap0=True, cap1=True, tag=None):
    """Connect rings of points (same count, consistent winding) with quads; optional flat end caps."""
    tag = tag or 'loft%d' % len(mb.faces)
    n = len(rings[0])
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            mb.face([a[i], a[j], b[j], b[i]], mat, smooth=tag)
    if cap0:
        mb.face(list(reversed(rings[0])), mat)
    if cap1:
        mb.face(list(rings[-1]), mat)


# name -> the function that sculpts a bronze, bakes it onto its light mesh and saves both (blender/sculpt.py,
# `blender/build.py -- statues`); the statue builders below read the light mesh back with sculpt.load(name)
SCULPTS = {}


# ============================================================================= 언더우드 동상
# The 1955 statue (the third; reference/고증.md 4.2), as in the photos of 2009 - 2019 (Wikimedia Commons, Category:Statue
# of Horace Grant Underwood) and the 2010 roadview of the courtyard: a balding man with a full moustache, in a morning
# coat (wide peaked lapels, one button at the waist, the fronts cut away over the hips to tails at the backs of the
# knees) over a waistcoat of six buttons, a high collar and tie, both arms held out in welcome with the palms up.
# The figure is sculpted densely here (underwood_sculpt) and baked onto a light mesh (blender/sculpt.py); its head and
# hands start from the Blender Foundation's CC0 "Human Base Meshes" (assets_src/blender-human-base-meshes).
UW_H = 2.45                    # the figure, soles to crown
UW_PED = 0.94                  # the pedestal and platform, drawn below at their measured proportions, to scale: the
#                                figure is 0.92 of the pedestal's height (1990s telephoto, reference/용재관.jpg)
UW_PLATE = 3.87 * UW_PED       # top of the bronze plate under his feet
UW_WALK = ((3.85 * UW_PED, 0.30 * UW_PED), (3.25 * UW_PED, 0.34 * UW_PED))   # (radius, height): the curb ring with its
#                                gravel, the round slab (blender/build.py makes them walkable)
HBM = os.path.join(ROOT, 'assets_src', 'blender-human-base-meshes', 'human-base-meshes-bundle-v1.4.1',
                   'human_base_meshes_bundle.blend')
HBM_HEAD = 'GEO-head_sculpting_realistic'
HBM_HAND = 'Hand  - Realistic'


def _capsule(mb, p0, p1, r, seg=18, k=6, r1=None):
    """A round-ended rod from p0 to p1, radius r (tapering to r1 at p1)."""
    p0, p1 = Vector(p0), Vector(p1)
    r1 = r if r1 is None else r1
    d = p1 - p0
    L = d.length
    R = Vector((1, 0, 0)).rotation_difference(d.normalized() if L > 1e-6 else Vector((1, 0, 0))).to_matrix()
    prof = [(-r * math.cos(math.pi / 2 * i / k), r * math.sin(math.pi / 2 * i / k)) for i in range(1, k + 1)]
    prof += [(L + r1 * math.sin(math.pi / 2 * i / k), r1 * math.cos(math.pi / 2 * i / k)) for i in range(k)]
    rings = [[p0 + R @ Vector((x, rho * math.cos(2 * math.pi * i / seg), rho * math.sin(2 * math.pi * i / seg)))
              for i in range(seg)] for x, rho in prof]
    tag = 'c%d' % len(mb.faces)
    loft(mb, rings, 'bronze_patina', cap0=False, cap1=False, tag=tag)
    a, b = p0 + R @ Vector((-r, 0, 0)), p0 + R @ Vector((L + r1, 0, 0))
    for i in range(seg):
        j = (i + 1) % seg
        mb.face([a, rings[0][j], rings[0][i]], 'bronze_patina', smooth=tag)
        mb.face([b, rings[-1][i], rings[-1][j]], 'bronze_patina', smooth=tag)


def _solids(name, elems):
    """Closed solids for sculpt.union: ('cap', p0, p1, r[, r1]) round-ended rods."""
    mb = MeshBuilder(name)
    for e in elems:
        _capsule(mb, e[1], e[2], e[3], r1=e[4] if len(e) > 4 else None)
    return mb.build()


def _lerp_table(T, x):
    """Piecewise linear lookup in [(x, y), ...] (x ascending), clamped at the ends."""
    if x <= T[0][0]:
        return T[0][1]
    for (xa, ya), (xb, yb) in zip(T[:-1], T[1:]):
        if x <= xb:
            return ya + (yb - ya) * (x - xa) / (xb - xa)
    return T[-1][1]


def _hbm(names, sub=0):
    """Objects of the Human Base Meshes bundle as plain meshes in world coordinates (their sculpt levels applied and
    `sub` more subdivisions)."""
    with bpy.data.libraries.load(HBM) as (src, dst):
        dst.objects = list(names)
    for o in dst.objects:
        bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    out = []
    for o in dst.objects:
        for m in o.modifiers:
            if m.type == 'MULTIRES':
                m.levels = m.total_levels
        if sub:
            s = o.modifiers.new('sub', 'SUBSURF')
            s.levels = s.render_levels = sub
        b = _bake(o)
        b.data.transform(b.matrix_world)
        b.matrix_world = Matrix()
        out.append(b)
    for o in dst.objects:
        bpy.data.objects.remove(o, do_unlink=True)
    return out


def _cut(ob, co, no):
    """Cut the mesh off on the side of the plane that `no` points to, and close the cut."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_outer=True)
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def _tree(ob):
    """The object's surface, for rays and nearest points."""
    me = ob.data
    return BVHTree.FromPolygons([tuple(v.co) for v in me.vertices], [tuple(p.vertices) for p in me.polygons])


def _onto(tree, pts, lift=0.0):
    """The points moved onto the surface (and `lift` off it along its normal)."""
    out = []
    for p in pts:
        loc, nrm, _, _ = tree.find_nearest(Vector(p))
        out.append(tuple(loc + nrm * lift))
    return out


def _smooth01(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# His head (2019 photo from close below; 2009 and 2018 photos from the sides), in the base head's own size with the
# origin between the eyes, facing -Y: (x half-width, y, z)
UW_SKULL = (0.0, 0.075, 0.012)          # the middle of the skull: the hair is laid out in angles about it


def underwood_head(voxel=0.0011):
    """His head at about life size (origin between the eyes, facing -Y, the neck cut off inside the collar): the base
    head made a man of fifty-six - a high bald forehead and crown, the hair kept short over the ears and round the
    back with a tuft left at the front of the crown, a strong brow over deep-set eyes, a long straight nose, a full
    moustache hiding the upper lip with its ends turned a little up, a firm round chin."""
    head, e0, e1 = _hbm((HBM_HEAD, HBM_HEAD + '.sclera.L', HBM_HEAD + '.sclera.R'), sub=1)
    c = (sum((v.co for v in e0.data.vertices), Vector()) / len(e0.data.vertices)
         + sum((v.co for v in e1.data.vertices), Vector()) / len(e1.data.vertices)) / 2
    for o in (head, e0, e1):
        o.data.transform(Matrix.Translation(-c))
    _cut(head, Vector((0, 0, -0.165)), Vector((0, 0, -1)))
    for o in (head, e0, e1):            # the eyes wider open (a statue's eyes are cut large, to read from below)
        P = sculpt.co(o)
        w = _smooth01(0.024, 0.01, np.abs(np.abs(P[:, 0]) - 0.032)) * _smooth01(0.02, 0.008, np.abs(P[:, 2]))
        w = w * (P[:, 1] < 0.012)
        P[:, 2] *= 1 + 0.3 * w
        sculpt.set_co(o, P)
    P = sculpt.co(head)                 # a slimmer neck, to stand in the collar
    w = 1 - 0.16 * _smooth01(-0.116, -0.14, P[:, 2])
    P[:, 0] *= w
    P[:, 1] = 0.103 + (P[:, 1] - 0.103) * w
    sculpt.set_co(head, P)
    tree = _tree(head)

    def front(x, z):                    # the face's surface at (x, z)
        loc, *_ = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
        return loc.y if loc is not None else 0.0

    # the moustache: a thick roll under the nose out past the corners of the mouth, the ends turned up
    E = []
    for sx in (-1, 1):
        pts = [(0.003, -0.057, 0.0068, 0.004), (0.009, -0.058, 0.0078, 0.005), (0.016, -0.0605, 0.0078, 0.005),
               (0.023, -0.063, 0.0066, 0.0045), (0.03, -0.0645, 0.0048, 0.0035), (0.036, -0.062, 0.0026, 0.002)]
        P = [(Vector((sx * x, front(sx * x, z) - off, z)), r) for x, z, r, off in pts]
        for (a, ra), (b, rb) in zip(P[:-1], P[1:]):
            E.append(('cap', a, b, ra, rb))
    ob = sculpt.union([head, e0, e1, _solids('uw_moustache', E)], voxel, smooth=2, name='uw_head')
    S = sculpt

    # -- the bones of the face
    S.push(ob, (0, -0.046, -0.036), 0.032, (0, -0.0075, -0.005))            # a longer, stronger nose
    S.strokes(ob, [([(0, -0.016, 0.004), (0, -0.03, -0.014), (0, -0.045, -0.03)], 0.011, 0.0035, (0.3, 0.2))])  # its bridge
    for sx in (-1, 1):
        S.inflate(ob, (sx * 0.017, -0.032, -0.042), 0.013, 0.003)           # the wings of the nose
        S.inflate(ob, (sx * 0.031, -0.012, 0.0095), 0.012, -0.002)          # the hollow under the brow
        S.push(ob, (sx * 0.09, 0.085, -0.02), 0.04, (sx * 0.006, 0, 0))     # ears standing out
        S.inflate(ob, (sx * 0.052, -0.004, -0.028), 0.03, 0.0025)           # cheekbones
        S.inflate(ob, (sx * 0.05, 0.02, -0.085), 0.04, 0.003)               # a heavier jaw
        S.inflate(ob, (sx * 0.03, -0.01, -0.062), 0.022, -0.002)            # the cheeks fallen in beside the mouth
        S.inflate(ob, (sx * 0.032, -0.0125, 0.0005), 0.0095, -0.0014, falloff=1.0)   # the eyeballs set back
        S.push(ob, (sx * 0.027, -0.022, -0.072), 0.013, (0, 0, 0.002))       # the corners of the mouth lifted
    S.inflate(ob, (0, -0.03, -0.103), 0.032, 0.0045)                        # the chin
    S.push(ob, (0, -0.02, 0.085), 0.09, (0, -0.004, 0.006))                 # a high forehead
    P = S.co(ob)                                                            # a broad face: the cheeks and jaw wider
    P[:, 0] *= 1 + 0.07 * _smooth01(0.06, -0.02, P[:, 1]) * _smooth01(-0.13, -0.09, P[:, 2]) * _smooth01(0.03, -0.02, P[:, 2])
    S.set_co(ob, P)
    tree = _tree(ob)
    on = lambda pts, lift=0.0: _onto(tree, pts, lift)
    st = []
    # the brow: a ridge over the eyes, drawn together over the nose
    for sx in (-1, 1):
        st.append((on([(sx * 0.008, -0.03, 0.0155), (sx * 0.024, -0.03, 0.0185), (sx * 0.042, -0.025, 0.018),
                       (sx * 0.056, -0.012, 0.011)]),
                   0.012, 0.0045, (0.2, 0.3)))
        # the bag under the eye
        st.append((on([(sx * 0.018, -0.02, -0.014), (sx * 0.032, -0.02, -0.017), (sx * 0.045, -0.015, -0.013)]), 0.006, -0.001))
        # the fold from the wing of the nose round the moustache to beside the chin
        st.append((on([(sx * 0.021, -0.03, -0.036), (sx * 0.03, -0.03, -0.05), (sx * 0.04, -0.02, -0.066),
                       (sx * 0.041, -0.02, -0.082)]),
                   0.007, -0.0028, (0.15, 0.4)))
    # the hollow between the lower lip and the chin, two lines across the forehead
    st.append((on([(-0.018, -0.03, -0.088), (0, -0.03, -0.0865), (0.018, -0.03, -0.088)]), 0.008, -0.0022))
    for z, w in ((0.04, 0.036), (0.054, 0.03)):
        st.append((on([(-w, -0.03, z - 0.002), (0, -0.03, z), (w, -0.03, z - 0.002)]), 0.0035, -0.0007))
    S.strokes(ob, st)
    _uw_hair(ob)
    # the strands of the moustache, combed down and out from under the nose; the brows' hair
    tree = _tree(ob)
    st = []
    for sx in (-1, 1):
        for i in range(7):
            f = i / 6
            x0 = 0.003 + 0.021 * f
            a = [(sx * x0, -0.06, -0.052 - 0.006 * f), (sx * (x0 + 0.003 + 0.004 * f), -0.06, -0.066 + 0.002 * f)]
            st.append((_onto(tree, a), 0.0015, -0.0008, (0.35, 0.35)))
        for i in range(7):
            f = i / 6
            x0 = 0.01 + 0.04 * f
            dz = 0.002 * math.sin(f * 2.6)
            a = [(sx * x0, -0.03, 0.0145 + dz), (sx * (x0 + 0.006), -0.03, 0.0215 + dz)]
            st.append((_onto(tree, a), 0.0014, -0.0007, (0.3, 0.3)))
    S.strokes(ob, st)
    return ob


def _uw_hair(ob):
    """The hair as a raised mass in combed locks: short over the ears and round the back of the head up to the bald
    crown, standing out a little over the ears, receding at the temples; a tuft at the front of the crown."""
    P = sculpt.co(ob)
    N = sculpt.normals(ob)
    d = P - np.asarray(UW_SKULL, np.float32)
    r = np.linalg.norm(d, axis=1)
    el = np.degrees(np.arcsin(np.clip(d[:, 2] / np.maximum(r, 1e-6), -1, 1)))
    az = np.degrees(np.arctan2(np.abs(d[:, 0]), -d[:, 1]))             # 0 in front .. 180 behind
    top = np.interp(az, [55, 68, 90, 130, 180], [14, 34, 44, 56, 62])
    low = np.interp(az, [50, 68, 80, 86, 110, 120, 180], [-6, -20, -20, 4, 4, -32, -40])
    fore = np.interp(el, [-20, 0, 15, 40], [66, 60, 60, 74])           # the hairline at the temple
    m = _smooth01(0, 18, top - el) * _smooth01(0, 7, el - low) * _smooth01(0, 6, az - fore)
    m *= _smooth01(0.012, 0.004, r - np.interp(el, [-40, 0, 40, 90], [0.097, 0.1, 0.103, 0.103]))   # (not the ears)
    # locks combed back: ridges along the lines of equal height that wander, each broken into strands of its own
    w = np.arctan2(d[:, 0], -d[:, 1])                                  # (round the head: the two sides differ)
    turn = np.radians(80) * _smooth01(110, 150, az)                    # ... and down at the back of the head
    ph = el * np.cos(turn) + 0.9 * az * np.sin(turn)
    ph = ph + 3.5 * np.sin(w * 2 + 0.4) + 2.0 * np.sin(w * 5 + np.radians(el * 4)) + 1.0 * np.sin(w * 11 - np.radians(el * 7))
    band = np.floor(ph / 7.0)
    lock = 0.5 + 0.5 * np.sin(np.radians(ph * 360 / 7.0 - 90))
    lock = lock ** 0.7 * (0.65 + 0.35 * np.sin(w * 9 + band * 2.4))
    full = 0.0035 + 0.0055 * np.exp(-((az - 95) / 35) ** 2) * np.exp(-((el - 20) / 20) ** 2)    # fuller over the ears
    h = m * (full + 0.002 * lock)
    # the tuft: where the forehead turns into the crown
    q = P - np.asarray((0.0, 0.03, 0.113), np.float32)
    rr = np.hypot(q[:, 0] / 0.017, q[:, 1] / 0.02) + 0.2 * np.sin(np.arctan2(q[:, 1], q[:, 0]) * 3 + 1)
    mt = np.clip(1 - rr * rr, 0, 1) * (q[:, 2] > -0.03)
    lock_t = 0.5 + 0.5 * np.sin(q[:, 0] / 0.006 * 2 * np.pi + 5 * np.sin(q[:, 1] / 0.012))
    h = h + mt ** 0.6 * (0.0018 + 0.0014 * lock_t)
    sculpt.set_co(ob, P + N * h[:, None])


def underwood_hand(side):
    """An open hand at life size, palm up, the fingers together and a little curled, the thumb up and out (2019 photo):
    the base hand with its fingers drawn together and bent.  Frame: wrist at the origin, x along the fingers, z out of
    the palm, y towards the thumb; side = +1 his left."""
    h, = _hbm((HBM_HAND,), sub=1)
    P = sculpt.co(h).astype(np.float64)
    # the base mesh is a right hand hanging down: fingers -Z, palm +Y, thumb +X, the wrist at z = 0.345
    Q = np.stack([0.345 - P[:, 2], -(P[:, 0] - 1.405), P[:, 1] - 0.012], axis=1)
    fing = 1 - _smooth01(-0.058, -0.068, Q[:, 1]) * _smooth01(0.115, 0.1, Q[:, 0])   # the four fingers (not the thumb)
    Q[:, 1] -= fing * 0.38 * Q[:, 1] * np.clip((Q[:, 0] - 0.095) / 0.09, 0, 1)      # ... drawn together
    for x0, ang in ((0.145, 20.0), (0.097, 16.0)):                        # ... bent at the middle joints, the knuckles
        a = np.radians(ang) * _smooth01(x0 - 0.012, x0 + 0.012, Q[:, 0]) * fing
        dx, dz = Q[:, 0] - x0, Q[:, 2] - 0.008
        Q[:, 0] = x0 + dx * np.cos(a) - dz * np.sin(a)
        Q[:, 2] = 0.008 + dx * np.sin(a) + dz * np.cos(a)
    if side > 0:
        Q[:, 1] = -Q[:, 1]
    sculpt.set_co(h, Q)
    if side > 0:
        h.data.flip_normals()
    ob = sculpt.union([h], 0.0012, smooth=1, name='uw_hand%d' % (side > 0))
    return ob


def _tube(mb, path, radii, mat, n=14, tag=None, cap0=False, cap1=True, wob=0.0, seed=0):
    """A round tube along a polyline (rings perpendicular to it, parallel-transported), radius per point."""
    rnd = random.Random(seed)
    P = [Vector(p) for p in path]
    T = []
    for i in range(len(P)):
        a, b = P[max(i - 1, 0)], P[min(i + 1, len(P) - 1)]
        T.append((b - a).normalized())
    u = T[0].cross(Vector((0, 0, 1)))
    if u.length < 1e-4:
        u = T[0].cross(Vector((1, 0, 0)))
    u.normalize()
    rings = []
    for i, (p, t) in enumerate(zip(P, T)):
        u = (u - t * u.dot(t)).normalized()
        w = t.cross(u)
        ring = []
        for k in range(n):
            ang = 2 * math.pi * k / n
            r = radii[i] * (1 + wob * rnd.uniform(-1, 1))
            ring.append(p + (u * math.cos(ang) + w * math.sin(ang)) * r)
        rings.append(ring)
    loft(mb, rings, mat, cap0=cap0, cap1=cap1, tag=tag)


def _oface(mb, q, mat, want, smooth=False):
    """Add a face wound so that its normal (Newell) points along `want`."""
    q = [Vector(p) for p in q]
    n = Vector((0, 0, 0))
    for i in range(len(q)):
        a, b = q[i], q[(i + 1) % len(q)]
        n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
    mb.face(q if n.dot(Vector(want)) >= 0 else q[::-1], mat, smooth=smooth)


def _arc(p0, p1, p2, n):
    """Points along a quadratic Bezier (a sleeve bending at the elbow)."""
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(p0 * (1 - t) ** 2 + p1 * 2 * t * (1 - t) + p2 * t * t)
    return out


def _xsection(me, z):
    """The points where the mesh's edges cross the height z."""
    out = []
    for e in me.edges:
        a, b = me.vertices[e.vertices[0]].co, me.vertices[e.vertices[1]].co
        if (a.z - z) * (b.z - z) < 0:
            out.append(a.lerp(b, (z - a.z) / (b.z - a.z)))
    return out


def _relief(ob, poly, height, soft=0.003, front=True, near=None):
    """Raise (height > 0) or sink the part of the figure's front (or back) that lies inside the outline `poly`
    ((x, z) points, seen from in front), along the surface's normals, the step `soft` wide.  near = (lo, hi): only
    what stands between lo and hi (m) outside the torso's own front, not what hangs before it."""
    P = sculpt.co(ob)
    N = sculpt.normals(ob)
    poly = np.asarray(poly, np.float32)
    lo, hi = poly.min(0) - 2 * soft, poly.max(0) + 2 * soft
    ok = (N[:, 1] < -0.2) if front else (N[:, 1] > 0.2)
    ok &= (P[:, 0] > lo[0]) & (P[:, 0] < hi[0]) & (P[:, 2] > lo[1]) & (P[:, 2] < hi[1])
    idx = np.nonzero(ok)[0]
    if near is not None and len(idx):
        off = _torso_y(P[idx, 0], P[idx, 2]) - P[idx, 1]
        idx = idx[(off > near[0]) & (off < near[1])]
    if not len(idx):
        return
    q = P[idx][:, (0, 2)]
    A, B = poly, np.roll(poly, -1, axis=0)
    d = np.full(len(q), 1e9, np.float32)
    inside = np.zeros(len(q), bool)
    for a, b in zip(A, B):
        ab = b - a
        t = np.clip(((q - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
        d = np.minimum(d, np.linalg.norm(q - (a + t[:, None] * ab), axis=1))
        cr = (a[1] > q[:, 1]) != (b[1] > q[:, 1])
        with np.errstate(divide='ignore', invalid='ignore'):
            xi = a[0] + (q[:, 1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        inside ^= cr & (q[:, 0] < xi)
    sd = np.where(inside, d, -d)
    w = _smooth01(-soft, soft, sd)
    P[idx] += N[idx] * (w * height)[:, None]
    sculpt.set_co(ob, P)


# his coat over the waistcoat, ring by ring from the waistcoat's points to the collar (z, half-width, half-depth,
# centre y), at H = 2.45: broad in the chest, a full waistcoat, sloping shoulders, and as wide at the waist as in the
# chest (2011 and 2019 photos from the front: 0.8 of the shoulders' width)
UW_TORSO = [(1.19, 0.2, 0.085, 0.0), (1.27, 0.212, 0.1, -0.006), (1.35, 0.224, 0.126, -0.016), (1.433, 0.234, 0.142, -0.012),
            (1.56, 0.232, 0.15, -0.02), (1.7, 0.232, 0.148, -0.016), (1.82, 0.236, 0.136, -0.004), (1.895, 0.232, 0.122, 0.005),
            (1.955, 0.214, 0.106, 0.009), (2.005, 0.14, 0.09, 0.011), (2.05, 0.08, 0.074, 0.012)]
UW_SE = 2.6                                      # the rings are superellipses: flatter front, back and sides
# the skirt from the front by t (0 at the waist seam, 1 at the hem), at H = 2.45: its half-width, and where the fronts'
# cut edge lies as a share of it, from the button round over the thighs to the sides at the hem (2011 photo from the
# front; 2019 photo from close below)
UW_SKIRT_W = [(0.0, 0.242), (0.15, 0.266), (0.3, 0.277), (0.55, 0.29), (0.8, 0.298), (1.0, 0.305)]
UW_CUT = [(0.0, 0.14), (0.15, 0.32), (0.3, 0.5), (0.45, 0.65), (0.6, 0.77), (0.75, 0.86), (0.9, 0.93), (1.0, 0.97)]
# a trouser leg from the front (z, inner edge x, outer edge x, half-depth, centre y), at H = 2.45: straight wide legs
# that meet at the knees and run into one another above them, the cuffs apart over the shoes (2011 photo from the
# front: the outer edge; 2019 photo)
UW_LEG = [(0.035, 0.032, 0.222, 0.112, 0.02), (0.15, 0.03, 0.225, 0.11, 0.02), (0.36, 0.022, 0.225, 0.108, 0.018),
          (0.55, 0.012, 0.235, 0.112, 0.012), (0.8, 0.0, 0.245, 0.12, 0.006), (1.0, -0.02, 0.25, 0.124, 0.0),
          (1.15, -0.05, 0.255, 0.127, 0.01), (1.25, -0.08, 0.253, 0.128, 0.013), (1.32, -0.09, 0.248, 0.124, 0.012),
          (1.42, -0.10, 0.24, 0.112, 0.012)]
UW_FOOT = (0.78 * UW_PED, 0.7 * UW_PED, 0.14 * UW_PED)   # the plate under his feet: width, depth, thickness (2011 photo)
# the tables above are drawn for a head 0.254 m wide; the head is 0.28 m (the base head at H / 6.7), so the clothes
# are made this much broader: shoulders 2.3 head widths (2019 photo 2.23, 2011 photo 2.47; reference/고증.md 4.2)
UW_BROAD = 1.09
UW_ZC = UW_TORSO[-1][0]                          # the collar's foot
UW_ZW = 0.597 * 2.45                             # the waist seam, the coat's lower button (2011 photos: 0.598, 0.600)
UW_ZB = 0.648 * 2.45                             # the lapels' foot, the coat's upper button (2011 photos: 0.647, 0.652)
UW_ZHEM = 0.27 * 2.45                            # the tails' hem, at the backs of the knees (2011 photo)


def _torso_at(z):
    """The torso's ring at height z: (half-width, half-depth, centre y), a smooth curve through UW_TORSO."""
    T = UW_TORSO
    if z <= T[0][0]:
        return T[0][1:]
    if z >= T[-1][0]:
        return T[-1][1:]
    i = max(k for k in range(len(T) - 1) if T[k][0] <= z)
    h = T[i + 1][0] - T[i][0]
    t = (z - T[i][0]) / h
    out = []
    for c in (1, 2, 3):
        def slope(k):                   # (a Hermite spline; the slope at a ring from its neighbours)
            a, b = max(k - 1, 0), min(k + 1, len(T) - 1)
            return (T[b][c] - T[a][c]) / (T[b][0] - T[a][0])
        p0, p1, m0, m1 = T[i][c], T[i + 1][c], slope(i) * h, slope(i + 1) * h
        out.append((2 * t ** 3 - 3 * t * t + 1) * p0 + (t ** 3 - 2 * t * t + t) * m0
                   + (-2 * t ** 3 + 3 * t * t) * p1 + (t ** 3 - t * t) * m1)
    return tuple(out)


def _torso_front(x, z, off=0.0):
    """The point on the torso's front at (x, z), pushed `off` further out."""
    a, b, yc = _torso_at(z)
    u = min(abs(x) / a, 0.999)
    y = yc - b * (1 - u ** UW_SE) ** (1 / UW_SE)
    return Vector((x, y - off, z))


def _torso_y(x, z):
    """The torso's front (y) at arrays of x and z."""
    zs = np.linspace(UW_TORSO[0][0], UW_TORSO[-1][0], 240)
    A, B, C = (np.array(v) for v in zip(*[_torso_at(float(q)) for q in zs]))
    a, b, yc = np.interp(z, zs, A), np.interp(z, zs, B), np.interp(z, zs, C)
    u = np.clip(np.abs(x) / a, 0, 0.999)
    return yc - b * (1 - u ** UW_SE) ** (1 / UW_SE)


def _uw_arms():
    """Shoulder, elbow and wrist of each arm (2019 photo: the upper arms down and forward, the forearms reaching out,
    the hands wide apart at the height of the waist button)."""
    J = {}
    for sx in (-1, 1):
        S = Vector((sx * 0.222, 0.0, 1.872))
        E = S + Vector((0.36 * sx, -0.42, -0.7)).normalized() * (0.155 * UW_H)
        W = E + Vector((0.3 * sx, -0.88, -0.12)).normalized() * (0.145 * UW_H)
        J[sx] = (S, E, W)
    return J


def _uw_sleeve(sx, J):
    """The line of a sleeve from inside the shoulder to the wrist, and its radius along it."""
    S, E, W = J[sx]
    S0 = S + Vector((-sx * 0.07, 0.0, -0.03))                 # (the sleeve head starts inside the shoulder)
    pts = _arc(S0, S + (E - S) * 0.15, S + (E - S) * 0.45, 10)[:-1] + _arc(S + (E - S) * 0.45, E + (E - (S + W) / 2) * 0.3, W, 28)
    n = len(pts)
    rad = [0.088 - 0.027 * (i / (n - 1)) ** 0.85 for i in range(n)]
    return pts, rad


def _uw_shoe(mb, sx):
    """A shoe under the cuff: a round toe, the vamp rising to the ankle, a welted sole."""
    c = Vector((sx * 0.128, 0.135, 0.0))                      # the back of the heel
    a = math.radians(sx * 9)                                  # toes turned out a little
    f = Vector((math.sin(a), -math.cos(a), 0))
    l = Vector((math.cos(a), math.sin(a), 0))
    L = 0.415
    W_ = [(0.0, 0.03), (0.04, 0.052), (0.2, 0.06), (0.45, 0.07), (0.66, 0.079), (0.82, 0.074), (0.93, 0.056), (0.985, 0.03),
          (1.0, 0.012)]
    H_ = [(0.0, 0.1), (0.04, 0.17), (0.3, 0.17), (0.48, 0.13), (0.66, 0.102), (0.84, 0.092), (0.95, 0.074), (1.0, 0.04)]
    n = 20
    for welt in (False, True):
        rings = []
        for i in range(25):
            s = i / 24
            w = _lerp_table(W_, s) + (0.007 if welt else 0)
            h = 0.02 if welt else _lerp_table(H_, s)
            ring = []
            for k in range(n):
                th = 2 * math.pi * k / n
                cs, sn = math.cos(th), math.sin(th)
                ring.append(c + f * (s * L + (0.006 if welt and s > 0.9 else 0)) + l * (w * math.copysign(abs(cs) ** 0.8, cs))
                            + Vector((0, 0, h / 2 + h / 2 * math.copysign(abs(sn) ** 0.55, sn))))
            rings.append(ring)
        loft(mb, rings, 'bronze_patina', tag='shoe%d%d' % (sx, welt))


def underwood_body():
    """His clothes and shoes as one dense skin (soles at z = 0, facing -Y, H = 2.45): the morning coat - its body,
    sleeves creased at the elbows, wide peaked lapels meeting the fronts at the upper button low on the chest, the
    fronts falling straight to the button at the waist, the rolled collar; the waistcoat's six buttons and its two
    points, the high collar and the tie; the skirt - its fronts cut away from the waist button in a long curve over
    the thighs, the tails hanging to the backs of the knees with a vent between them, clear of the trousers; the
    trousers' straight legs breaking over the shoes.  Returns (object, arms): shoulder / elbow / wrist per side."""
    M = 'bronze_patina'
    S_ = sculpt
    parts = []
    # -- trousers and shoes
    mb = MeshBuilder('uw_legs')
    n = 72
    for sx in (-1, 1):
        rings = []
        zs = sorted(set([z for z, *_ in UW_LEG] + [0.035 + i * 0.03 for i in range(47)]))
        for z in zs:
            xi = _lerp_table([(r[0], r[1]) for r in UW_LEG], z)
            xo = _lerp_table([(r[0], r[2]) for r in UW_LEG], z)
            b = _lerp_table([(r[0], r[3]) for r in UW_LEG], z)
            cy = _lerp_table([(r[0], r[4]) for r in UW_LEG], z)
            cx, a = (xi + xo) / 2, (xo - xi) / 2
            ring = []
            for i in range(n):
                t = 2 * math.pi * i / n
                c, s_ = math.cos(t), math.sin(t)
                ring.append(Vector((sx * (cx + a * math.copysign(abs(c) ** 0.85, c)),
                                    cy + b * math.copysign(abs(s_) ** 0.85, s_), z)))
            rings.append(ring if sx > 0 else ring[::-1])
        loft(mb, rings, M, tag='leg%d' % sx)
        _uw_shoe(mb, sx)
    legs = mb.build()
    parts.append(legs)
    mb = MeshBuilder('uw_plate')        # the bronze plate under his feet, cast with him
    w, d, h = UW_FOOT
    quad = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    rings = [[Vector((x * k, 0.02 + y * k, z)) for x, y in quad] for z, k in ((-h, 0.992), (-0.012, 1.0), (0.002, 0.985))]
    loft(mb, rings, M, tag=False)
    parts.append(mb.build())
    # -- the body of the coat
    mb = MeshBuilder('uw_coat')
    n = 96
    zz = []
    zs = [z for z, *_ in UW_TORSO]
    for za, zb in zip(zs[:-1], zs[1:]):
        zz += [za + (zb - za) * i / 12 for i in range(12)]
    zz.append(zs[-1])
    rings = []
    for z in zz:
        a, b, yc = _torso_at(z)
        rings.append([Vector((a * math.copysign(abs(math.cos(t)) ** (2 / UW_SE), math.cos(t)),
                              yc + b * math.copysign(abs(math.sin(t)) ** (2 / UW_SE), math.sin(t)), z))
                      for t in (2 * math.pi * i / n for i in range(n))])
    loft(mb, rings, M, tag='torso')
    zc, zw, zb = UW_ZC, UW_ZW, UW_ZB
    cyn = UW_TORSO[-1][3]
    # -- sleeves, the shirt cuffs at their ends
    J = _uw_arms()
    for sx in (-1, 1):
        pts, rad = _uw_sleeve(sx, J)
        _tube(mb, pts, rad, M, n=48, tag='slv%d' % sx, cap0=True, cap1=True)
        W = J[sx][2]
        d = (W - pts[-3]).normalized()
        _tube(mb, [W - d * 0.03, W + d * 0.012, W + d * 0.034, W + d * 0.04], [0.046, 0.05, 0.05, 0.045], M, n=20,
              tag='cuf%d' % sx, cap0=True, cap1=True)
    # -- the coat's collar rolled round the back of the neck, running into the lapels; the high shirt collar
    path = []
    for i in range(25):
        t = math.radians(-48 + 276 * i / 24)
        back = 0.5 - 0.5 * math.cos(2 * math.pi * i / 24)
        end = max(0.0, 1 - min(i, 24 - i) / 3)                 # (the ends sink into the lapels)
        path.append(Vector(((0.112 - 0.03 * end) * math.cos(t), cyn + (0.104 - 0.03 * end) * math.sin(t),
                            zc - 0.045 + 0.05 * back - 0.03 * end)))
    _tube(mb, path, [0.013 + 0.01 * (0.5 - 0.5 * math.cos(2 * math.pi * i / 24)) for i in range(25)], M, n=16, tag='ccol',
          cap0=True, cap1=True)
    rings = []
    for z, r, tilt in ((zc - 0.05, 0.104, 0.0), (zc + 0.02, 0.104, 0.0), (zc + 0.05, 0.103, 1.0), (zc + 0.056, 0.098, 1.0)):
        rings.append([Vector((r * math.cos(t), cyn + 0.02 + r * math.sin(t), z + tilt * 0.02 * math.sin(t)))
                      for t in (2 * math.pi * i / 64 for i in range(64))])
    loft(mb, rings, M, tag='scol')
    parts.append(mb.build())
    # -- the skirt: the fronts cut away from the button in a long curve over the thighs to the sides at the hem, the
    # tails hanging to the backs of the knees with a vent between them.  It stands off the trousers: each ring is
    # deepened where the legs would come through it.
    mb = MeshBuilder('uw_skirt')
    _, b0, cy = _torso_at(zw)
    z_top, z_hem = zw + 0.005, UW_ZHEM
    rows, cols = 32, 40
    gap, th = 0.046, 0.028              # room over the trousers, the cloth's thickness
    R = []
    for j in range(rows + 1):
        t = j / rows
        z = z_top - (z_top - z_hem) * t
        rx = _lerp_table(UW_SKIRT_W, t)
        se = UW_SE - 0.5 * min(1.0, t / 0.3)                             # rounder below the hips
        bf, bb = b0 + 0.008 + 0.03 * t, b0 + 0.008 + 0.07 * t
        for p in _xsection(legs.data, z):
            u = min(abs(p.x) / rx, 0.95)
            need = (abs(p.y - cy) + gap * min(1.0, 0.25 + t / 0.3)) / (1 - u ** se) ** (1 / se)
            if p.y < cy:
                bf = max(bf, need)
            else:
                bb = max(bb, need)
        R.append([t, z, rx, bf, bb, se])
    for i in (3, 4):                    # no kinks down the skirt
        v = [r[i] for r in R]
        for j, r in enumerate(R):
            r[i] = max(v[max(j - 3, 0):j + 4])
    for r in R:                         # it leaves the coat's body at the waist seam
        w = min(1.0, r[0] / 0.1)
        w = w * w * (3 - 2 * w)
        a_, b_, _ = _torso_at(r[1])
        r[2] = a_ + 0.003 + (r[2] - a_ - 0.003) * w
        r[3] = b_ + 0.003 + (r[3] - b_ - 0.003) * w
        r[4] = b_ + 0.003 + (r[4] - b_ - 0.003) * w
    for sx in (-1, 1):                  # each side from the cut edge round to the vent at the back
        outer_, inner_ = [], []
        for t, z, rx, bf, bb, se in R:
            a0 = -math.acos(_lerp_table(UW_CUT, t) ** (se / 2))            # (front = -90 degrees)
            a1 = math.pi / 2 - math.radians(0.3 + 3.2 * max(0.0, t - 0.25))  # the vent opens below the hips
            o_row, i_row = [], []
            for kk in range(cols + 1):
                ang = a0 + (a1 - a0) * kk / cols
                c, s_ = math.cos(ang), math.sin(ang)
                b = bf if s_ < 0 else bb
                # folds hanging from the waist, deeper towards the hem
                fold = 1 - 0.02 * t + t ** 1.5 * (0.022 * math.cos(5.0 * ang + 0.8 * sx)
                                                  + 0.014 * math.cos(11.0 * ang - 1.3 * sx + 2 * t))
                ex, ey = abs(c) ** (2 / se) * fold, math.copysign(abs(s_) ** (2 / se), s_) * fold
                zr = z + (0.04 * max(0.0, -s_) ** 2 if t == 1 else 0.0)   # the fronts' corners rounded up
                thk = th * min(1.0, 0.3 + t / 0.15)                        # (thin where it leaves the waist)
                o_row.append(Vector((sx * ex * rx, cy + ey * b, zr)))
                i_row.append(Vector((sx * ex * (rx - thk), cy + ey * (b - thk), zr)))
            outer_.append(o_row)
            inner_.append(i_row)
        tag = 'tail%d' % sx
        for j in range(rows):
            for kk in range(cols):
                q = [outer_[j][kk], outer_[j + 1][kk], outer_[j + 1][kk + 1], outer_[j][kk + 1]]
                c = sum(q, Vector()) / 4
                _oface(mb, q, M, (c.x, c.y - cy, 0), smooth=tag)
                q = [inner_[j][kk], inner_[j + 1][kk], inner_[j + 1][kk + 1], inner_[j][kk + 1]]
                _oface(mb, q, M, (-c.x, cy - c.y, 0), smooth=tag + 'i')
        for kk in range(cols):
            _oface(mb, [outer_[rows][kk], inner_[rows][kk], inner_[rows][kk + 1], outer_[rows][kk + 1]], M, (0, 0, -1), smooth=tag)
            _oface(mb, [outer_[0][kk], inner_[0][kk], inner_[0][kk + 1], outer_[0][kk + 1]], M, (0, 0, 1), smooth=tag)
        for kk in (0, cols):
            for j in range(rows):
                q = [outer_[j][kk], inner_[j][kk], inner_[j + 1][kk], outer_[j + 1][kk]]
                mid = (outer_[j][cols // 2] + inner_[j][cols // 2]) / 2
                _oface(mb, q, M, sum(q, Vector()) / 4 - mid, smooth=tag)
    parts.append(mb.build())
    ob = S_.union(parts, 0.0035, smooth=8, factor=0.5, name='uw_body')
    _uw_tailor(ob, J)
    # the clothes are as broad for the head as in the photos (UW_BROAD): everything below the collar wider, the plate
    # under his feet as it was
    P = S_.co(ob)
    P[:, 0] *= 1 + (UW_BROAD - 1) * _smooth01(2.04, 1.97, P[:, 2]) * _smooth01(-0.005, 0.004, P[:, 2])
    S_.set_co(ob, P)
    J = {sx: tuple(Vector((p.x * UW_BROAD, p.y, p.z)) for p in v) for sx, v in J.items()}
    return ob, J


def _uw_tailor(ob, J):
    """Cut the clothes into the skin: the fronts and lapels standing off the waistcoat, the shirt and tie, seams and
    pockets; then the folds, and the marks of the modelling clay over everything."""
    S_ = sculpt
    zc, zw, zb = UW_ZC, UW_ZW, UW_ZB
    B = zc - zb
    # (half-width, depth below the collar's foot): the lapels' outer edge - the collar, the notch, the peak, then
    # down to the upper button - and their inner edge, the roll line
    outer = [(0.075, 0.012), (0.12, 0.03), (0.15, 0.06), (0.135, 0.08), (0.19, 0.095), (0.175, 0.15), (0.137, 0.224),
             (0.085, 0.32), (0.05, B - 0.04), (0.03, B)]
    inner = [(0.052, 0.012), (0.055, 0.03), (0.05, 0.06), (0.045, 0.08), (0.042, 0.095), (0.034, 0.15), (0.028, 0.224),
             (0.026, 0.32), (0.026, B - 0.04), (0.026, B)]
    # the opening between the fronts: the shirt and waistcoat down to the waist button, then out under the skirt
    op = [(x, zc - d) for x, d in inner] + [(0.025, zw + 0.005), (0.04, zw - 0.04), (0.073, zw - 0.115), (0.085, zw - 0.17)]
    _relief(ob, [(-x, z) for x, z in op] + op[::-1], -0.013, soft=0.004, near=(-0.006, 0.006))
    for sx in (-1, 1):
        _relief(ob, [(sx * x, zc - d) for x, d in outer] + [(sx * x, zc - d) for x, d in inner[::-1]], 0.012, soft=0.004,
                near=(-0.006, 0.008))
    # the shirt inside the waistcoat's neck, the tie on it; the trousers under the waistcoat's two points
    wn = [(0.046, zc - 0.012), (0.03, zc - 0.07), (0.004, zc - 0.15)]
    _relief(ob, [(-x, z) for x, z in wn] + wn[::-1], -0.005, soft=0.004, near=(-0.022, -0.006))
    tie = [(0.028, zc - 0.014), (0.032, zc - 0.035), (0.016, zc - 0.058), (0.021, zc - 0.1), (0.008, zc - 0.148)]
    _relief(ob, [(-x, z) for x, z in tie] + tie[::-1], 0.009, soft=0.004, near=(-0.03, -0.006))
    wp = [(0.0, zw - 0.075), (0.036, zw - 0.112), (0.075, zw - 0.085), (0.11, zw - 0.07), (0.11, zw - 0.17)]
    _relief(ob, [(-x, z) for x, z in wp[::-1]] + wp[1:], -0.008, soft=0.004, near=(-0.022, -0.006))
    S_.smooth(ob, iterations=2, factor=0.5)
    tree = _tree(ob)
    on = lambda pts, lift=0.0: _onto(tree, pts, lift)
    F = lambda x, z, off=0.02: tuple(_torso_front(x, z, off))
    st = []
    # the waistcoat's closing; the knot's lower edge and the fold of the tie
    st.append((on([F(0.0, zc - 0.15), F(0.0, zw - 0.07)]), 0.0035, -0.002, (0.02, 0.02)))
    st.append((on([F(-0.028, zc - 0.052), F(0.0, zc - 0.06), F(0.028, zc - 0.052)]), 0.004, -0.003, (0.1, 0.1)))
    # the waist seam round the coat; buttonholes opposite the buttons; the welt of the breast pocket
    a, b, yc = _torso_at(zw)
    seam = []
    for i in range(49):
        t = math.radians(-196 + 212 * i / 48)
        seam.append((a * 1.04 * math.copysign(abs(math.cos(t)) ** (2 / UW_SE), math.cos(t)),
                     yc + (b * 1.07) * math.copysign(abs(math.sin(t)) ** (2 / UW_SE), math.sin(t)), zw + 0.004))
    for sg in (-1, 1):
        st.append((on([(sg * x, y, z) for x, y, z in seam if x >= 0.03]), 0.005, -0.0028, (0.03, 0.03)))
    for z in (zb - 0.008, zw + 0.012):
        st.append((on([F(0.05, z), F(0.082, z + 0.002)]), 0.004, -0.0025, (0.15, 0.15)))
    st.append((on([F(0.108, 1.742), F(0.19, 1.752)]), 0.011, 0.0035, (0.1, 0.1)))
    st.append((on([F(0.108, 1.752), F(0.19, 1.762)]), 0.003, -0.002, (0.1, 0.1)))
    # the back: the seam down the middle, the side seams curving in to the waist with a button on each
    Bk = lambda x, z: (x, 0.3, z)
    st.append((on([Bk(0, 2.0), Bk(0, 1.8), Bk(0, zw)]), 0.004, -0.002, (0.1, 0.02)))
    for sx in (-1, 1):
        st.append((on([Bk(sx * 0.17, 1.9), Bk(sx * 0.11, 1.72), Bk(sx * 0.075, zw)]), 0.004, -0.0018, (0.1, 0.05)))
        # the armhole seam, the seam along the shoulder
        Sj = J[sx][0]
        hole = [Sj + Vector((-sx * 0.05, 0.11 * math.cos(t), 0.115 * math.sin(t) - 0.03))
                for t in (math.radians(20 * i) for i in range(19))]
        st.append((on([tuple(p) for p in hole]), 0.0045, -0.0022, (0.0, 0.0)))
        st.append((on([(sx * 0.1, 0.02, 2.02), (sx * 0.19, 0.01, 1.975)]), 0.004, -0.0015, (0.2, 0.2)))
    # a shadow line under the lapels' edges
    for sx in (-1, 1):
        st.append((on([F(sx * (x + 0.004), zc - d, 0.0) for x, d in outer[1:]]), 0.005, -0.002, (0.0, 0.05)))
    S_.strokes(ob, st)
    # buttons: the waistcoat's six, the coat's two on his right front (at the lapels' foot and at the waist), the two
    # at the back of the waist
    tree = _tree(ob)
    for i in range(6):
        S_.inflate(ob, _onto(tree, [F(0.0, zw - 0.022 + i * 0.085, -0.013)])[0], 0.012, 0.0065, falloff=0.7)
    for z in (zb - 0.008, zw + 0.012):
        S_.inflate(ob, _onto(tree, [F(-0.068, z, 0.0)])[0], 0.018, 0.009, falloff=0.7)
    for sx in (-1, 1):
        S_.inflate(ob, _onto(tree, [Bk(sx * 0.075, zw + 0.012)])[0], 0.018, 0.008, falloff=0.7)
    _uw_folds(ob, J)
    S_.clay(ob, amp=0.003, scale=0.07, seed=3)
    S_.clay(ob, amp=0.001, scale=0.022, seed=5)


def _uw_folds(ob, J):
    """The cloth's folds: the sleeves creased inside the elbows and drawn along the arms, pulls from the coat's
    button, the trousers' creases, their break over the shoes and the folds at the knees."""
    tree = _tree(ob)
    on = lambda pts, lift=0.0: _onto(tree, pts, lift)
    rnd = random.Random(1955)
    st = []
    for sx in (-1, 1):
        pts, rad = _uw_sleeve(sx, J)
        n = len(pts)
        T = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
        ie = min(range(n), key=lambda i: (pts[i] - J[sx][1]).length)        # the elbow
        inner = (T[min(ie + 3, n - 1)] - T[max(ie - 3, 0)])                 # the inside of the bend
        inner = (inner - T[ie] * inner.dot(T[ie])).normalized()

        def ring(i, a0, a1, skew=0.0, m=9, lift=0.0):
            u, w = inner, T[i].cross(inner).normalized()
            out = []
            for k in range(m):
                a = math.radians(a0 + (a1 - a0) * k / (m - 1))
                out.append(tuple(pts[i] + (u * math.cos(a) + w * math.sin(a)) * (rad[i] + lift)
                                 + T[i] * (skew * (k / (m - 1) - 0.5))))
            return out
        # creases across the inside of the elbow, ridges between them
        for di, skew, h in ((-4, -0.07, -0.009), (0, 0.0, -0.012), (4, 0.07, -0.009), (-2, -0.03, 0.008), (2, 0.03, 0.008)):
            i = max(1, min(n - 2, ie + di))
            sp = 58 + rnd.uniform(-8, 12)
            a = ring(i, -sp, sp, skew=0.0)
            a = [tuple(Vector(p) + T[i] * (skew * (2 * abs(k / 8 - 0.5)) ** 1.5)) for k, p in enumerate(a)]
            st.append((on(a), 0.013 if h < 0 else 0.02, h, (0.3, 0.3)))
        # long folds drawn round the upper arm and the forearm
        for i0, i1, a0, a1, h in ((3, ie - 5, 150, 40, 0.008), (5, ie - 3, -150, -60, 0.007), (ie + 5, n - 5, 60, 170, 0.0075),
                                   (ie + 3, n - 7, -40, -150, 0.007), (ie + 7, n - 3, 200, 110, -0.007),
                                   (6, ie - 6, 60, -30, -0.006)):
            m = max(2, i1 - i0 + 1)
            line = []
            for k in range(m):
                i = max(0, min(n - 1, i0 + k))
                a = math.radians(a0 + (a1 - a0) * k / max(m - 1, 1))
                u, w = inner, T[i].cross(inner).normalized()
                line.append(tuple(pts[i] + (u * math.cos(a) + w * math.sin(a)) * rad[i]))
            st.append((on(line), 0.02, h, (0.3, 0.3)))
        # the sleeve's end: a turned edge
        st.append((on(ring(n - 1, 0, 360, m=19)), 0.006, 0.002, (0.0, 0.0)))
        # -- a trouser leg: the crease down the front, folds beside it, the break over the shoe, drag folds to the knee
        X = lambda z: (_lerp_table([(r[0], r[1]) for r in UW_LEG], z) + _lerp_table([(r[0], r[2]) for r in UW_LEG], z)) / 2
        fr = lambda x, z: (sx * x, -0.4, z)
        st.append((on([fr(X(z) + 0.012 * math.sin(z * 5 + sx), z) for z in (1.12, 0.95, 0.75, 0.55, 0.35, 0.2, 0.1)]),
                   0.016, 0.0045, (0.25, 0.1)))
        for dx, h, z0, z1 in ((-0.055, -0.004, 1.0, 0.25), (0.06, -0.0035, 0.9, 0.18), (0.085, 0.003, 1.15, 0.5)):
            zs = [z0 + (z1 - z0) * k / 5 for k in range(6)]
            st.append((on([fr(X(z) + dx + 0.01 * math.sin(z * 7 + dx * 40), z) for z in zs]), 0.022, h, (0.3, 0.3)))
        for z, h, w in ((0.2, -0.007, 0.03), (0.135, 0.006, 0.03), (0.3, 0.004, 0.035)):
            st.append((on([fr(X(z) - 0.085, z + 0.02), fr(X(z), z - 0.012), fr(X(z) + 0.085, z + 0.025)]), w, h, (0.2, 0.2)))
        for z0, z1, h in ((0.8, 0.62, -0.004), (0.72, 0.5, 0.0035)):
            st.append((on([fr(X(z0) - 0.08, z0), fr(X(z0) + 0.02, (z0 + z1) / 2), fr(X(z1) + 0.09, z1)]), 0.024, h, (0.3, 0.3)))
        # at the back: folds behind the knee and down the calf (seen under the tails)
        bk = lambda x, z: (sx * x, 0.4, z)
        for z, h in ((0.56, -0.005), (0.48, 0.004), (0.4, -0.004)):
            st.append((on([bk(X(z) - 0.08, z + 0.015), bk(X(z), z - 0.01), bk(X(z) + 0.08, z + 0.02)]), 0.028, h, (0.2, 0.2)))
        st.append((on([bk(X(z), z) for z in (0.6, 0.4, 0.2, 0.08)]), 0.018, 0.004, (0.2, 0.1)))
        # -- the coat: a pull from the waist button towards the hip and the shoulder, a soft fold under the arm
        Ft = lambda x, z: tuple(_torso_front(sx * x, z, 0.02))
        st.append((on([Ft(0.05, UW_ZW + 0.02), Ft(0.12, UW_ZW + 0.06), Ft(0.19, UW_ZW + 0.12)]),
                   0.03, 0.004 if sx < 0 else 0.003, (0.3, 0.4)))
        st.append((on([Ft(0.07, UW_ZW + 0.08), Ft(0.13, 1.66), Ft(0.17, 1.74)]), 0.035, -0.003, (0.3, 0.4)))
        st.append((on([Ft(0.215, 1.5), Ft(0.205, 1.62), Ft(0.19, 1.74)]), 0.03, -0.004, (0.3, 0.3)))
    # the fly
    st.append((on([(0.012, -0.4, 1.3), (0.014, -0.4, 1.2), (0.01, -0.4, 1.12)]), 0.006, -0.003, (0.1, 0.3)))
    sculpt.strokes(ob, st)


# the bronze as in the 1990s and 2009 photos: weathered grey-green all over, paler where the rain washes it, dark
# where it is sheltered (the black polish of the 2019 photo is later)
UW_LOOK = dict(verdigris=0.7, wear=0.12, base=(0.068, 0.092, 0.076), green=(0.18, 0.252, 0.208), soot=(0.021, 0.023, 0.019),
               bare=(0.2, 0.15, 0.08), rough=(0.72, 0.9, 0.45), metal=(0.3, 0.05, 0.9))


def underwood_high():
    """The dense sculpt in place (soles at z = 0, facing -Y): the clothes, the head, the hands."""
    body, J = underwood_body()
    # the head: H / 6.7 from the chin to the crown (2011 · 2009 photos: 0.14 - 0.15 of his height), the chin lifted a
    # little, the neck down in the collar
    head = underwood_head()
    P = sculpt.co(head)
    chin = P[(np.abs(P[:, 0]) < 0.012) & (P[:, 1] < 0.0) & (P[:, 2] > -0.13)][:, 2].min()
    k = (UW_H / 6.7) / (P[:, 2].max() - chin)
    neck = Vector((0, 0.103, -0.14))                           # (the middle of the neck, in the head's frame)
    R = Matrix.Translation(neck) @ Matrix.Rotation(math.radians(-6), 4, 'X') @ Matrix.Translation(-neck)
    head.data.transform(Matrix.Scale(k, 4) @ R)
    P = sculpt.co(head)
    head.data.transform(Matrix.Translation((0, UW_TORSO[-1][3] + 0.02 - neck.y * k, UW_H - P[:, 2].max())))
    out = [body, head]
    for sx, (S, E, W) in J.items():                             # hands at the wrists, palm up, tilted a little inwards
        h = underwood_hand(sx)
        d = (W - E).normalized()
        z = Vector((0, 0, 1))
        z = (z - d * z.dot(d)).normalized()
        z = Quaternion(d, math.radians(sx * 18)) @ z
        y = z.cross(d)
        Mh = Matrix((d, y, z)).transposed().to_4x4()
        h.data.transform(Matrix.Translation(W + d * 0.035) @ Mh @ Matrix.Scale(1.45, 4))
        out.append(h)
    for o in out:
        o.data.update()
    return out


def underwood_sculpt(size=1024, cache=None):
    """Sculpt the figure, bake it onto its light mesh and save both (sculpt.load('underwood')).  cache: a file to
    keep the baked masks in (to try a look with _uw_maps without baking again)."""
    body, head, *hands = underwood_high()
    sculpt.clay(head, amp=0.0012, scale=0.03, seed=7)
    for h in hands:
        sculpt.clay(h, amp=0.0012, scale=0.03, seed=9)
    # the light mesh: each part thinned to its share (the face and the hands keep more), then one layout in which
    # the head's islands are enlarged
    lows = [sculpt.lowpoly(body, 8100, 'uw_low_body'), sculpt.lowpoly(head, 2400, 'uw_low_head')]
    lows += [sculpt.lowpoly(h, 740, 'uw_low_hand') for h in hands]
    for i, o in enumerate(lows):
        a = o.data.attributes.new('part', 'INT', 'FACE')
        a.data.foreach_set('value', np.full(len(o.data.polygons), i, np.int32))
    low = sculpt.join(lows, 'underwood_low')
    sculpt.smooth_shade(low)
    sculpt.unwrap(low, margin=0.003)
    _uw_layout(low, {1: 2.1, 2: 1.35, 3: 1.35})
    # each part is baked from its own sculpt, the rays starting as far out as its light mesh strays from it: a
    # finger's breadth for the clothes (the tails' edges), hardly at all for the face
    highs = [body, head] + hands
    part = _attr(low, 'part')
    owner = _uv_owner(low, part, size)
    raw = None
    for i, (h, ex) in enumerate(zip(highs, (0.014, 0.004, 0.004, 0.004))):
        piece = low.copy()
        piece.data = low.data.copy()
        bpy.context.scene.collection.objects.link(piece)
        bm = bmesh.new()
        bm.from_mesh(piece.data)
        lay = bm.faces.layers.int['part']
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay] != i], context='FACES')
        bm.to_mesh(piece.data)
        bm.free()
        low.hide_render = True
        piece.hide_render = False
        keep = {}
        sculpt.bake(h, piece, 'underwood', size=size, extrude=ex, ray=ex * 2.5, ao_dist=0.5, look=UW_LOOK, keep=keep)
        bpy.data.objects.remove(piece)
        if raw is None:
            raw = {k: v.copy() for k, v in keep.items() if k != 'cover'}
        else:
            for k in raw:
                raw[k][owner == i] = keep[k][owner == i]
    low.hide_render = False
    if cache:
        np.savez_compressed(cache, owner=owner, **raw)
    _uw_maps(raw, owner)
    low.data.attributes.remove(low.data.attributes['part'])
    low.data.materials.clear()
    low.data.materials.append(material('bronze_underwood'))
    sculpt.save(low, 'underwood')
    return low


def _uw_maps(raw, owner):
    """Write the figure's maps from the baked masks.  The shelter mask is deepened first, and darkened in streaks
    down the upright faces where the rain runs off the patina (2009 photo), so that the folds and the tailoring
    read from the ground."""
    ao = raw['ao'].copy()
    up, cloud, run = raw['m0'][..., 1], raw['m0'][..., 2], raw['m1'][..., 0]
    streak = _smooth01(0.5, 0.66, run) * _smooth01(0.8, 0.5, up) * np.clip(0.35 + 1.3 * (cloud - 0.25), 0, 1)
    ao[..., 0] = np.clip(ao[..., 0], 0, 1) ** 1.6 * (1 - 0.45 * streak)
    m0 = raw['m0'].copy()
    m0[..., 2] = np.clip(0.5 + (cloud - 0.5) * 1.8, 0, 1)
    sculpt.write_maps('underwood', raw['nor'], ao, m0, raw['m1'], owner >= 0, UW_LOOK)


def _attr(ob, name):
    a = np.empty(len(ob.data.polygons), np.int32)
    ob.data.attributes[name].data.foreach_get('value', a)
    return a


def _uv_owner(low, part, size, grow=16):
    """Which part each texel of the layout belongs to (-1: none): the triangles drawn into a size x size grid, then
    each part grown `grow` texels into the gutters round its islands."""
    me = low.data
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 3, 2) * size - 0.5
    own = np.full((size, size), -1, np.int8)
    for T, p in zip(uv, part):
        x0, y0 = np.floor(T.min(0)).astype(int) - 1
        x1, y1 = np.ceil(T.max(0)).astype(int) + 1
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        (ax, ay), (bx, by), (cx, cy) = T
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-9:
            continue
        w0 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / d
        w1 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / d
        m = (w0 >= -0.02) & (w1 >= -0.02) & (w0 + w1 <= 1.02)
        own[y0:y1 + 1, x0:x1 + 1][m] = p
    for _ in range(grow):
        for sh, ax in ((1, 0), (-1, 0), (1, 1), (-1, 1)):
            n = np.roll(own, sh, axis=ax)
            m = (own < 0) & (n >= 0)
            own[m] = n[m]
    return own


def _uw_layout(low, scale):
    """Enlarge the UV islands of the parts in `scale` (part -> factor) and pack the layout again."""
    me = low.data
    part = np.empty(len(me.polygons), np.int32)
    me.attributes['part'].data.foreach_get('value', part)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    start = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_start', start)
    for p, f in scale.items():
        for s in start[part == p]:
            uv[s:s + 3] *= f
    me.uv_layers.active.data.foreach_set('uv', uv.ravel())
    bpy.ops.object.select_all(action='DESELECT')
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
    bpy.ops.object.mode_set(mode='OBJECT')


SCULPTS['underwood'] = underwood_sculpt


def underwood_pedestal():
    """The light granite pedestal and the round platform under it, as in the 1990s photo (reference/용재관.jpg) and
    measured on the 2011 photo (numbers below in units of a 2.3 m base block, all scaled by UW_PED): a square shaft
    tapering 1.66 -> 1.40 with the inscribed bronze plaque on the front and a small one on the back, a cap of a
    cavetto, a slab and a sloped top; under the shaft a plain base block of two stones with a sloped wash; a smooth
    octagonal slab on an octagon of rock-faced blocks, on a round stone slab inside a ring of granite curb blocks round
    a band of gravel, one stepping stone at the front."""
    mb = MeshBuilder('underwood_pedestal')
    SC = Matrix.Scale(UW_PED, 4)
    mb.xf = SC
    G, Gd, Gs, B = 'granite_light', 'stone_granite', 'stone_step', 'bronze_patina'
    rnd = random.Random(1955)
    # curb ring: 28 dressed granite blocks, 0.3 m wide and high, open joints between them
    R1, R0, HC = 3.85, 3.55, 0.30
    nb = 28
    for k in range(nb):
        a0 = 2 * math.pi * (k + 0.012) / nb
        a1 = 2 * math.pi * (k + 0.988) / nb
        h = HC + rnd.uniform(-0.012, 0.008)
        pts = [a0 + (a1 - a0) * i / 3 for i in range(4)]
        ro = [(R1 * math.cos(a), R1 * math.sin(a)) for a in pts]
        ri = [(R0 * math.cos(a), R0 * math.sin(a)) for a in pts]
        for i in range(3):
            mb.face([(*ro[i], -0.4), (*ro[i + 1], -0.4), (*ro[i + 1], h), (*ro[i], h)], G)
            mb.face([(*ri[i + 1], 0.2), (*ri[i], 0.2), (*ri[i], h), (*ri[i + 1], h)], G)
            mb.face([(*ro[i], h), (*ro[i + 1], h), (*ri[i + 1], h), (*ri[i], h)], G)
        mb.face([(*ro[0], -0.4), (*ro[0], h), (*ri[0], h), (*ri[0], 0.2)], G)
        mb.face([(*ro[3], h), (*ro[3], -0.4), (*ri[3], 0.2), (*ri[3], h)], G)
    # the gravel band and the round slab (its rim bevelled), the stepping stone across the band at the front
    n = 64
    ring = lambda r, z: [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), z) for i in range(n)]
    g0, g1 = ring(R0, 0.28), ring(3.25, 0.28)
    for i in range(n):
        j = (i + 1) % n
        mb.face([g0[i], g0[j], g1[j], g1[i]], 'dirt_pale')
    d0, d1, d2 = ring(3.3, 0.26), ring(3.3, 0.31), ring(3.24, 0.34)
    loft(mb, [d0, d1, d2], Gs, cap0=False, cap1=True, tag='disc')
    mb.box((0, -(R0 + 3.25) / 2, 0.28), (1.9, 0.62, 0.09), Gs)
    # the octagon of rock-faced blocks (across the flats 4.4 m, 0.37 m high), two or three blocks a side
    def octagon(rin, z):
        rc = rin / math.cos(math.pi / 8)
        return [(rc * math.cos(math.pi / 8 + i * math.pi / 4), rc * math.sin(math.pi / 8 + i * math.pi / 4), z) for i in range(8)]
    O = octagon(2.2, 0.0)
    z0, z1 = 0.33, 0.71
    for i in range(8):
        a, b = Vector(O[i]), Vector(O[(i + 1) % 8])
        nb_ = 3 if i % 2 == 0 else 2
        out = Vector((a.x + b.x, a.y + b.y, 0)).normalized()
        cuts = sorted([0.0, 1.0] + [(k + rnd.uniform(-0.15, 0.15)) / nb_ for k in range(1, nb_)])
        for c0, c1 in zip(cuts[:-1], cuts[1:]):
            p0, p1 = a.lerp(b, c0 + 0.004), a.lerp(b, c1 - 0.004)
            # a rough face: a 4 x 3 grid bulging out by up to 4 cm, the joints set back
            cols, rows = 4, 3
            grid = []
            for r_ in range(rows + 1):
                row = []
                for c_ in range(cols + 1):
                    p = p0.lerp(p1, c_ / cols)
                    z = z0 + (z1 - z0) * r_ / rows
                    edge = c_ in (0, cols) or r_ in (0, rows)
                    bulge = 0.0 if edge else rnd.uniform(0.015, 0.045)
                    row.append(Vector((p.x, p.y, z)) + out * bulge)
                grid.append(row)
            for r_ in range(rows):
                for c_ in range(cols):
                    mb.face([grid[r_][c_], grid[r_][c_ + 1], grid[r_ + 1][c_ + 1], grid[r_ + 1][c_]], Gd)
    mb.face([(x, y, z1) for x, y, _ in O], G)
    # the smooth octagonal slab (3.7 m across, 0.22 m)
    mb.prism([(x, y) for x, y, _ in octagon(1.85, 0)], z1, 0.93, G, mat_top=G)
    # base block of two stones, with its sloped wash
    sq = lambda w: [(-w / 2, -w / 2), (w / 2, -w / 2), (w / 2, w / 2), (-w / 2, w / 2)]
    mb.box((-0.5755, 0, 1.17), (1.141, 2.3, 0.48), G)
    mb.box((0.5755, 0, 1.17), (1.141, 2.3, 0.48), G)
    wash = [(2.3, 1.41), (2.14, 1.47), (1.97, 1.55), (1.83, 1.61)]          # a little hollow
    for (wa, za), (wb, zb) in zip(wash[:-1], wash[1:]):
        A, Bq = sq(wa), sq(wb)
        for i in range(4):
            j = (i + 1) % 4
            mb.face([(*A[i], za), (*A[j], za), (*Bq[j], zb), (*Bq[i], zb)], G)
    mb.prism(sq(1.72), 1.61, 1.65, G, mat_top=G)
    # the shaft
    zs0, zs1, w0, w1 = 1.65, 3.30, 1.66, 1.40
    A, Bq = sq(w0), sq(w1)
    for i in range(4):
        j = (i + 1) % 4
        mb.face([(*A[i], zs0), (*A[j], zs0), (*Bq[j], zs1), (*Bq[i], zs1)], G)
    def face_y(z, front=True):                     # the shaft's front (or back) face at height z
        w = w0 + (w1 - w0) * (z - zs0) / (zs1 - zs0)
        return -w / 2 if front else w / 2
    lean = math.atan2((w0 - w1) / 2, zs1 - zs0)
    for front, (pw, ph, top) in ((True, (0.71, 1.13, 3.10)), (False, (0.36, 0.48, 3.08))):
        sgn = -1 if front else 1
        zc = top - ph / 2
        yc = face_y(zc, front) + sgn * 0.012
        R = Matrix.Translation((0, yc, zc)) @ Matrix.Rotation(sgn * lean, 4, 'X')
        mb.xf = SC @ R
        mb.box((0, 0, 0), (pw, 0.024, ph), B)                                # the plate, standing a little proud
        if front:
            mb.box((0, sgn * 0.014, 0), (pw - 0.07, 0.008, ph - 0.07), B)    # its raised field
            for k in range(14):                                              # the Korean text in columns ...
                x = -0.27 + k * 0.0415
                mb.box((x, sgn * 0.02, 0.17), (0.016, 0.006, 0.6), B)
            mb.box((0, sgn * 0.02, -0.19), (0.5, 0.006, 0.012), B)           # ... a rule, the English below
        mb.xf = SC
    # the cap: a fillet, a cavetto flaring out, the slab, a steep sloped top
    mb.prism(sq(1.48), 3.30, 3.33, G, mat_top=G)
    cav = [(1.48, 3.33), (1.5, 3.38), (1.55, 3.43), (1.65, 3.47)]
    for (wa, za), (wb, zb) in zip(cav[:-1], cav[1:]):
        A, Bq = sq(wa), sq(wb)
        for i in range(4):
            j = (i + 1) % 4
            mb.face([(*A[i], za), (*A[j], za), (*Bq[j], zb), (*Bq[i], zb)], G)
    mb.prism(sq(1.65), 3.47, 3.60, G)
    A, Bq = sq(1.65), sq(1.34)
    for i in range(4):
        j = (i + 1) % 4
        mb.face([(*A[i], 3.60), (*A[j], 3.60), (*Bq[j], 3.73), (*Bq[i], 3.73)], G)
    mb.face([(*p, 3.73) for p in Bq], G)
    return mb                           # (the bronze plate under his feet belongs to the figure: UW_FOOT)


def underwood_statue():
    fig = sculpt.load('underwood')               # soles at z = 0 (underwood_sculpt, `blender/build.py -- statues`)
    fig.data.transform(Matrix.Translation((0, 0, UW_PLATE)))      # onto the bronze plate
    return [fig, underwood_pedestal().build()]


# ============================================================================= 독수리상
# As it stood in 1997 (reference/고증.md 4.1): photos of 1971 (공유마당), 1995 (reference/1995_백양로와_중앙도서관.jpg,
# right edge), the 1997 aerial photo and 2009 (reference/활천대_2009_연세춘추.jpg, before 백양로 was rebuilt), with a
# side silhouette (Flickr, 2000s) and the university's symbol page for the eagle's form.  The dark bronze eagle (gilded
# only after 2015) raises its wings in a wide V with the broad feathered faces turned back, its primaries spread like
# fingers, gripping a bronze rock on a tall white square column whose foot sweeps out concavely onto a low round
# dais (the roadview of 2008 - 2011, below); on the dais, round the foot, four groups of white figures (the
# "Yonseians").  (The wide round steps and granite wedges of the 2024 photo came with the rebuilt 백양로.)
def _to_mb(ob, mb, mat):
    """Copy a baked mesh object's faces into a MeshBuilder (metric UVs, shared smooth normals) and delete it."""
    tag = 'skin%d' % len(mb.faces)
    M = ob.matrix_world
    V = [M @ v.co for v in ob.data.vertices]
    for p in ob.data.polygons:
        mb.face([V[i] for i in p.vertices], mat, smooth=tag)
    bpy.data.objects.remove(ob)


class _Soup:
    """Closed solids as plain vertex and face lists, built into one mesh object: the raw material of the eagle's
    sculpt (a union on a voxel grid for the body, feather blades laid over one another for the plumage)."""

    def __init__(self):
        self.V, self.F = [], []

    def loft(self, rings, cap0=True, cap1=True):
        n, b = len(rings[0]), len(self.V)
        for r in rings:
            self.V.extend(tuple(p) for p in r)
        for j in range(len(rings) - 1):
            for i in range(n):
                a, a2 = b + j * n + i, b + j * n + (i + 1) % n
                self.F.append((a, a2, a2 + n, a + n))
        if cap0:
            self.F.append(tuple(b + i for i in reversed(range(n))))
        if cap1:
            self.F.append(tuple(b + (len(rings) - 1) * n + i for i in range(n)))

    def ellipsoid(self, c, r, q=None, seg=24, rings=14):
        R = (q or Quaternion()).to_matrix()
        c = Vector(c)
        P = [[c + R @ Vector((r[0] * math.sin(th) * math.cos(ph), r[1] * math.sin(th) * math.sin(ph), -r[2] * math.cos(th)))
              for ph in (2 * math.pi * i / seg for i in range(seg))]
             for th in (math.pi * (j + 0.5) / rings for j in range(rings))]
        self.loft(P)

    def capsule(self, p0, p1, r0, r1=None, seg=16, k=5):
        """A round-ended limb from p0 to p1, radius r0 tapering to r1."""
        p0, p1 = Vector(p0), Vector(p1)
        r1 = r0 if r1 is None else r1
        d = p1 - p0
        L = d.length
        R = Vector((0, 0, 1)).rotation_difference(d.normalized() if L > 1e-6 else Vector((0, 0, 1))).to_matrix()
        prof = [(-r0 * math.cos(math.pi / 2 * (i + 0.5) / k), r0 * math.sin(math.pi / 2 * (i + 0.5) / k)) for i in range(k)]
        prof += [(L + r1 * math.sin(math.pi / 2 * (i + 0.5) / k), r1 * math.cos(math.pi / 2 * (i + 0.5) / k)) for i in range(k)]
        self.loft([[p0 + R @ Vector((rho * math.cos(a), rho * math.sin(a), z))
                    for a in (2 * math.pi * i / seg for i in range(seg))] for z, rho in prof])

    def tube(self, path, radii, n=10):
        P = [Vector(p) for p in path]
        u = None
        rings = []
        for i, p in enumerate(P):
            t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
            if u is None:
                u = t.orthogonal().normalized()
            u = (u - t * u.dot(t)).normalized()
            w = t.cross(u)
            rings.append([p + (u * math.cos(a) + w * math.sin(a)) * radii[i] for a in (2 * math.pi * k / n for k in range(n))])
        self.loft(rings)

    def build(self, name):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.V, [], self.F)
        me.update()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        sculpt.smooth_shade(ob)
        return ob


def _eq(axis, deg):
    return Quaternion({'X': (1, 0, 0), 'Y': (0, 1, 0), 'Z': (0, 0, 1)}[axis], math.radians(deg))


def _sstep(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def _vane(shape, t):
    """A feather's width along its length (0 quill .. 1 tip), as a share of its greatest."""
    if shape == 'lance':                         # the hackles of the neck, the trousers: widest low, a long point
        a = min(1.0, (t / 0.3) ** 0.7)
        b = 1 - ((t - 0.3) / 0.7) ** 1.5 if t > 0.3 else 1.0
        return max(a * b, 0.07)
    a = min(1.0, (t / 0.12) ** 0.6)
    if shape == 'finger':                        # a primary: the outer part cut narrower (the emargination), a blunt point
        b = 1.0 if t < 0.42 else 1 - 0.36 * _sstep((t - 0.42) / 0.12) if t < 0.54 else \
            0.64 * max(0.0, 1 - ((t - 0.54) / 0.46) ** 2.6) ** 0.5
        return max(a * b, 0.08)
    b = max(0.0, 1 - ((t - 0.7) / 0.3) ** 2) ** 0.5 if t > 0.7 else 1.0     # 'round': coverts, secondaries, the body
    return max(a * b, 0.07)


# a feather's section, (across, up) round the shaft: a blunt edge each side, the vanes arched, the shaft a ridge above
# (index 3) and a lesser one below (index 9)
_BLADE = [(1, .35), (.6, .82), (.14, 1), (0, 1), (-.14, 1), (-.6, .82), (-1, .35), (-1, -.3), (-.5, -.55), (0, -.6),
          (.5, -.55), (1, -.3)]


def _blade(sp, C, N, W, T, roll=0.0, ridge=0.3, barb=None):
    """A feather as a closed blade: centres C along the shaft, its upper side towards N (one vector or one per
    centre), half-widths W and thicknesses T; rolled about the shaft by `roll` (one vane lifted over its neighbour).
    barb = (depth, spacing): the vanes ribbed with barbs running out and forward from the shaft."""
    n = len(C)
    rings = []
    cr, sr = math.cos(roll), math.sin(roll)
    run = 0.0
    for j in range(n):
        if j:
            run += (C[j] - C[j - 1]).length
        d = (C[min(j + 1, n - 1)] - C[max(j - 1, 0)]).normalized()
        up = N[j] if isinstance(N, list) else N
        up = up - d * up.dot(d)
        up = up.normalized() if up.length > 1e-5 else d.orthogonal().normalized()
        side = up.cross(d)
        side, up = side * cr + up * sr, up * cr - side * sr
        w, t = W[j], T[j] * 0.6
        ring = []
        for k, (x, h) in enumerate(_BLADE):
            z = (h + (ridge if k == 3 else -0.5 * ridge if k == 9 else 0.0)) * t
            if barb and x:
                z += barb[0] * math.sin(2 * math.pi * (run - abs(x) * w * 1.1) / barb[1]) * (1 if h > 0 else -0.6)
            ring.append(C[j] + side * (x * w) + up * z)
        rings.append(ring)
    sp.loft(rings)


def _quill(sp, base, d, nn, L, hw, shape='round', th=0.034, curl=0.0, roll=0.0):
    """A flight feather or covert: from `base` along d, its upper side towards nn; the tip lifts by `curl` along nn."""
    m = max(14, int(L / 0.009))
    ts = [j / m for j in range(m + 1)]
    C = [base + d * (L * t) + nn * (curl * t * t) for t in ts]
    _blade(sp, C, nn, [hw * _vane(shape, t) for t in ts], [th * (1 - 0.35 * t) for t in ts], roll, 0.35,
           barb=(0.002, 0.032))


# The eagle at its final size (metres; the talons on the rock at z = 0, front -Y, +X its left): 5.2 m across the
# wing tips and about 2.6 m high (the university's figures), 2.2 m from the beak to the end of the tail (as before;
# 1.9 - 2.3 m by the column's height in the 2024 photo from the east).  The body lies nearly level, the shoulders its highest point,
# the neck stretched forward and the head below them, looking down the avenue a little to its right (reference/고증.md
# 4.1.4; 2024 photo: the head's crown below the wings' roots).
EG_ROCK = 0.48                                   # the rock's height: the sculpt's origin is its foot
EG_HEAD = Matrix.Translation((-0.06, -0.80, 0.80)) @ Matrix.Rotation(math.radians(-28), 4, 'Z') @ \
    Matrix.Rotation(math.radians(15), 4, 'X')
EG_ARM, EG_HAND = 1.42, 0.33                     # shoulder - wrist, wrist - the end of the hand
EG_ELEV = 35.0                                   # the wings' V over the horizontal, degrees
EG_NECK_CUT = -0.60                              # (the head and neck are sculpted finer, in front of this y)


def _eg_wing(sx):
    """A wing's frame: the shoulder, and unit vectors along the arm (out and up), along the chord (back and down:
    the feathers' broad faces turn back) and out of its upper side."""
    S = Vector((0.18 * sx, -0.22, 0.93))
    a = math.radians(EG_ELEV)
    s = Vector((sx * math.cos(a), 0.06, math.sin(a))).normalized()
    c = Vector((0.12 * sx, math.cos(math.radians(22)), -math.sin(math.radians(22))))
    c = (c - s * c.dot(s)).normalized()
    n = s.cross(c).normalized()
    return S, s, c, (n if n.z > 0 else -n)


def _eg_body():
    """The trunk, the thighs and the wings' arms with the skin behind them, as one union."""
    sp = _Soup()
    sp.ellipsoid((0, -0.26, 0.74), (0.29, 0.33, 0.31))                    # breast
    sp.ellipsoid((0, 0.06, 0.69), (0.28, 0.40, 0.27))                     # belly
    sp.ellipsoid((0, -0.10, 0.86), (0.27, 0.38, 0.19))                    # mantle, between the shoulders
    sp.ellipsoid((0, 0.36, 0.67), (0.20, 0.28, 0.18))                     # rump
    sp.ellipsoid((0, 0.52, 0.615), (0.16, 0.22, 0.075), _eq('X', -28))         # the root of the tail
    sp.ellipsoid((0, 0.46, 0.53), (0.13, 0.22, 0.09), _eq('X', -20))           # under-tail coverts
    sp.capsule((0, -0.40, 0.84), (-0.02, -0.66, 0.83), 0.21, 0.17)        # neck (the head's union carries it on)
    for sx in (-1, 1):
        sp.ellipsoid((sx * 0.175, -0.02, 0.43), (0.14, 0.19, 0.27), _eq('X', -18))        # the feathered thighs
        sp.capsule((sx * 0.17, 0.05, 0.58), (sx * 0.19, -0.09, 0.27), 0.15, 0.11)
        sp.capsule((sx * 0.19, -0.09, 0.27), (sx * 0.19, -0.13, 0.1), 0.1, 0.075)     # tarsus, feathered to the toes
        S, s, c, n = _eg_wing(sx)
        E = S + s * (0.45 * EG_ARM) + c * 0.07
        Wr = S + s * EG_ARM
        Ht = Wr + s * EG_HAND + c * 0.03
        sp.ellipsoid(S + s * 0.05, (0.17, 0.2, 0.15))                      # shoulder
        sp.capsule(S, E, 0.13, 0.095)                                      # upper arm
        sp.capsule(E, Wr, 0.095, 0.07)                                     # forearm
        sp.capsule(S + s * 0.1 - c * 0.02, Wr - c * 0.01, 0.10, 0.065)     # the leading edge's skin
        sp.capsule(Wr, Ht, 0.07, 0.035)                                    # hand
        rings = []                                                         # the skin behind the arm, under the coverts
        for k in range(11):
            f = k / 10
            u = (EG_ARM + EG_HAND) * f
            ch = 0.56 - 0.2 * f - 0.14 * max(0.0, f - 0.8) / 0.2
            th = 0.115 - 0.06 * f
            le = S + s * u - c * 0.03
            ring = []
            for i in range(12):
                a = 2 * math.pi * i / 12
                v = ch * (1 - math.cos(a)) / 2
                ring.append(le + c * v + n * (th / 2 * math.sin(a) * (1 - 0.55 * v / ch)))
            rings.append(ring)
        sp.loft(rings)
    ob = sculpt.union([sp.build('eg_body')], 0.006, smooth=6, factor=0.6, name='eg_body')
    return ob


def _eg_head():
    """The head and the neck: a flat crown, the brow standing out over deep-set eyes, the cere and the deep hooked
    beak, the gape running back under the eye.  Sculpted in the head's own frame (origin the middle of the skull,
    the beak towards -Y), then set on the neck by EG_HEAD."""
    sp = _Soup()
    sp.ellipsoid((0, 0.0, 0.0), (0.115, 0.155, 0.1))                      # skull
    sp.ellipsoid((0, 0.02, 0.035), (0.095, 0.13, 0.075))                  # the flat crown
    sp.ellipsoid((0, -0.06, -0.045), (0.088, 0.13, 0.066))                # cheeks
    sp.ellipsoid((0, -0.125, 0.012), (0.062, 0.075, 0.058))               # forehead running into the beak
    sp.ellipsoid((0, 0.02, -0.075), (0.085, 0.15, 0.06))                  # throat
    sp.ellipsoid((0, -0.16, 0.02), (0.062, 0.045, 0.052))                 # cere
    for sx in (-1, 1):
        sp.ellipsoid((sx * 0.062, -0.075, 0.05), (0.05, 0.09, 0.027), _eq('Z', sx * 14) @ _eq('Y', sx * 22) @ _eq('X', 8))   # brow
        sp.ellipsoid((sx * 0.086, -0.07, 0.008), (0.03, 0.032, 0.029))     # eye
    # upper mandible: from the culmen (top) to the cutting edge (bottom), station by station round the hook
    top = [(-0.15, 0.06), (-0.19, 0.06), (-0.235, 0.048), (-0.272, 0.02), (-0.295, -0.02), (-0.304, -0.065), (-0.296, -0.108)]
    bot = [(-0.15, -0.035), (-0.19, -0.038), (-0.225, -0.043), (-0.25, -0.053), (-0.268, -0.07), (-0.282, -0.09), (-0.292, -0.108)]
    hw = [0.06, 0.055, 0.048, 0.039, 0.028, 0.017, 0.005]
    rings = []
    for (ya, za), (yb, zb), w in zip(top, bot, hw):
        a, b = Vector((0, ya, za)), Vector((0, yb, zb))
        ring = []
        for x, f in ((0.0, 0.0), (0.62, 0.1), (0.95, 0.42), (1.0, 0.78), (0.8, 1.0), (0.0, 0.94),
                     (-0.8, 1.0), (-1.0, 0.78), (-0.95, 0.42), (-0.62, 0.1)):
            ring.append(a.lerp(b, f) + Vector((x * w, 0, 0)))
        rings.append(ring)
    sp.loft(rings)
    # lower mandible, shut under it
    top = [(-0.1, -0.035), (-0.17, -0.04), (-0.22, -0.048), (-0.258, -0.062)]
    bot = [(-0.1, -0.1), (-0.17, -0.095), (-0.22, -0.082), (-0.258, -0.07)]
    hw = [0.058, 0.047, 0.034, 0.01]
    rings = []
    for (ya, za), (yb, zb), w in zip(top, bot, hw):
        a, b = Vector((0, ya, za)), Vector((0, yb, zb))
        rings.append([a.lerp(b, f) + Vector((x * w, 0, 0)) for x, f in
                      ((0.0, 0.0), (0.9, 0.05), (1.0, 0.5), (0.7, 0.95), (0.0, 1.0), (-0.7, 0.95), (-1.0, 0.5), (-0.9, 0.05))])
    sp.loft(rings)
    sp.capsule((0, 0.1, -0.02), (0, 0.26, -0.03), 0.135, 0.165)           # nape and neck, towards the body
    raw = sp.build('eg_head')
    raw.modifiers.new('sub', 'SUBSURF').levels = 2        # (round the beak's stations off)
    sculpt.apply_modifiers(raw)
    raw.data.transform(EG_HEAD)
    nk = _Soup()                                                          # the neck, as in the body's union
    nk.capsule((0, -0.40, 0.84), (-0.02, -0.66, 0.83), 0.21, 0.17)
    nk.capsule((-0.02, -0.62, 0.83), EG_HEAD @ Vector((0, 0.18, -0.02)), 0.18, 0.15)
    ob = sculpt.union([raw, nk.build('eg_neck')], 0.0035, smooth=4, factor=0.5, name='eg_head')
    # the lines of the face: the gape back from the beak under the eye, the mouth between the mandibles, the nostril,
    # the edge of the cere, a furrow under the brow
    S = []
    for sx in (-1, 1):
        g = lambda pts: [tuple(EG_HEAD @ Vector((sx * x, y, z))) for x, y, z in pts]
        S.append((g([(0.012, -0.27, -0.075), (0.03, -0.235, -0.052), (0.048, -0.19, -0.04), (0.06, -0.14, -0.037),
                     (0.078, -0.085, -0.044), (0.09, -0.04, -0.055)]), 0.007, -0.01, (0.05, 0.3)))
        S.append((g([(0.046, -0.176, 0.02), (0.053, -0.162, 0.022)]), 0.009, -0.011, (0.0, 0.0)))      # nostril
        S.append((g([(0.0, -0.186, 0.068), (0.04, -0.186, 0.046), (0.058, -0.18, 0.0), (0.054, -0.172, -0.032)]),
                  0.007, -0.005, (0.0, 0.1)))                                                          # cere
        S.append((g([(0.075, -0.13, 0.012), (0.098, -0.09, 0.032), (0.108, -0.04, 0.032)]), 0.013, -0.009, (0.2, 0.3)))
        ec = Vector((0.086, -0.07, 0.008))       # the eye: the lids' line round the ball, the pupil
        ring = [ec + Vector((0.6 * 0.031, 0.8 * 0.031 * math.cos(a), 0.8 * 0.031 * math.sin(a)))
                for a in (2 * math.pi * i / 14 for i in range(15))]
        S.append((g([tuple(p) for p in ring]), 0.0045, -0.004, (0.0, 0.0)))
        S.append((g([tuple(ec + Vector((0.031, -0.004, 0.0))), tuple(ec + Vector((0.031, 0.004, 0.0)))]), 0.007, -0.005, (0.0, 0.0)))
    sculpt.strokes(ob, S)
    return ob


def _eg_scatter(P, N, want, seed=3):
    """Pick surface points, each no nearer to those already picked than its feather's spacing: `want(p, n)` gives a
    point's (spacing, ...) or None where no feather grows.  Returns [(index, spec)]."""
    rnd = random.Random(seed)
    order = list(range(len(P)))
    rnd.shuffle(order)
    cell = 0.03
    grid = {}
    out = []
    for i in order[:min(len(order), 140000)]:
        p = P[i]
        spec = want(p, N[i])
        if spec is None:
            continue
        r = spec[0]
        key = (int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell)), int(math.floor(p[2] / cell)))
        k = int(r / cell) + 1
        ok = True
        for dx in range(-k, k + 1):
            for dy in range(-k, k + 1):
                for dz in range(-k, k + 1):
                    for q, rq in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        m = min(r, rq)
                        if (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 < m * m:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            grid.setdefault(key, []).append((p, r))
            out.append((i, spec))
    return out


def _eg_plumage(ob, want, name, seed=3):
    """Lay small feathers over the union `ob` like shingles: each lies along the flow of its place, hugging the
    surface, its quill sunk and its tip lifted over the next.  want(p, n) -> (spacing, length, half-width, shape,
    flow, thickness) or None."""
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
    P = [tuple(v) for v in sculpt.co(ob)]
    N = [tuple(v) for v in sculpt.normals(ob)]
    sp = _Soup()
    rnd = random.Random(seed + 11)
    ST = (0.0, 0.1, 0.25, 0.45, 0.65, 0.82, 0.94, 1.0)
    for i, (_, L, hw, shape, flow, th) in _eg_scatter(P, N, want, seed):
        p, n = Vector(P[i]), Vector(N[i])
        f = Vector(flow)
        t = f - n * f.dot(n)
        if t.length < 0.15:
            continue
        t.normalize()
        t = (Quaternion(n, math.radians(rnd.uniform(-9, 9))) @ t)
        L *= rnd.uniform(0.88, 1.1)
        C, U = [], []
        for u in ST:
            hit = bvh.find_nearest(p + t * (L * (u - 0.3)))
            if hit[0] is None:
                break
            C.append(hit[0] + hit[1] * (-0.004 + (0.004 + 0.11 * L) * u))
            U.append(hit[1])
        if len(C) < len(ST):
            continue
        _blade(sp, C, U, [hw * _vane(shape, u) for u in ST], [th * (1 - 0.3 * u) for u in ST],
               math.radians(rnd.uniform(-10, 10)), 0.22)
    return sp.build(name)


def _eg_body_feather(p, n):
    """What grows where on the trunk, the legs and the wings' arms."""
    x, y, z = p
    if y < EG_NECK_CUT:
        return None
    for sx in (-1, 1):
        if x * sx < 0.22:
            continue
        S, s, c, nn = _eg_wing(sx)
        rel = Vector(p) - S
        u, v, w = rel.dot(s), rel.dot(c), rel.dot(nn)
        if u > 0.2 and abs(w) < 0.22 and v > -0.3:
            if v > 0.2 or u > EG_ARM + EG_HAND - 0.03:     # under the coverts laid row by row
                return None
            small = u > EG_ARM - 0.1
            L = 0.075 if small else 0.11
            return (L * 0.46, L, L * 0.44, 'round', tuple(c + s * 0.25), 0.02)   # lesser and marginal coverts
    if z < 0.5 and abs(x) > 0.045 and y < 0.2:
        if z < 0.2:
            return (0.036, 0.085, 0.034, 'lance', (0, 0.15, -1), 0.016)          # tarsus
        return (0.05, 0.2, 0.055, 'lance', (0, 0.25, -1), 0.022)                 # the trousers
    if y < -0.38:
        return (0.05, 0.16, 0.047, 'lance', (0, 1, -0.3), 0.02)                  # the neck's hackles
    if y < -0.2 and z < 0.75:
        return (0.055, 0.125, 0.056, 'round', (0, 0.55, -0.85), 0.02)            # breast: hanging
    if y > 0.4:
        return (0.055, 0.15, 0.058, 'round', (0, 0.88, -0.47), 0.02)             # tail coverts
    if z > 0.78:
        return (0.06, 0.15, 0.064, 'round', (0, 1, -0.12), 0.022)                # mantle and back
    return (0.055, 0.13, 0.058, 'round', (0, 1, -0.3), 0.02)                     # flanks and belly


_EG_HEAD_INV = EG_HEAD.inverted()


def _eg_head_feather(p, n):
    x, y, z = p
    if y > EG_NECK_CUT + 0.02:
        return None
    q = _EG_HEAD_INV @ Vector(p)
    back = tuple(EG_HEAD.to_3x3() @ Vector((0, 1, -0.12)))
    if q.y < -0.115 or (q.y < -0.06 and -0.07 < q.z < -0.02 and abs(q.x) > 0.03):
        return None                                                               # beak, cere, the gape
    for sx in (-1, 1):
        if (q - Vector((sx * 0.086, -0.07, 0.008))).length < 0.052:
            return None                                                           # eyes
    if q.y < 0.1:
        k = 0.45 + 0.55 * _sstep((q.y + 0.11) / 0.2)                              # small on the face, longer behind
        return (0.024 * k + 0.004, 0.075 * k, 0.024 * k, 'round' if q.y < 0.0 else 'lance', back, 0.012)
    return (0.045, 0.15, 0.04, 'lance', (0, 1, -0.3), 0.02)                       # hackles down the neck


def _eg_wing_feathers(sx):
    """A wing's flight feathers and the coverts over them, above and below: eight primaries spread like fingers from
    the hand, their tips lifting; fourteen secondaries along the forearm and upper arm; a row of greater and one of
    median coverts over each, the primary coverts and the alula at the wrist."""
    sp = _Soup()
    rnd = random.Random(7 + sx)
    S, s, c, n = _eg_wing(sx)
    Wr = S + s * EG_ARM
    Ht = Wr + s * EG_HAND + c * 0.03
    lay = sx                                      # (each feather's vane towards the body lies over its neighbour)

    def along(f):
        """A feather's direction at f (0 at the shoulder .. 1 at the wrist): back along the chord, fanning out."""
        a = math.radians(-10 + 44 * f)
        return (c * math.cos(a) + s * math.sin(a)).normalized()

    # secondaries, then the greater and the median coverts over their quills (upper side) ...
    for N_, v0, L, hw, lift, th in ((14, 0.34, 0.74, 0.078, 0.0, 0.034), (15, 0.19, 0.40, 0.07, 0.032, 0.028),
                                    (14, 0.10, 0.23, 0.062, 0.05, 0.024)):
        for k in range(N_):
            f = k / (N_ - 1)
            u = 0.08 + (EG_ARM - 0.1) * f
            d = (along(f) + s * rnd.uniform(-0.03, 0.03)).normalized()
            Lk = L * (0.86 + 0.14 * math.sin(math.pi * min(1.0, f * 1.4))) * rnd.uniform(0.96, 1.04)
            _quill(sp, S + s * u + c * v0 + n * (lift + 0.004 * (k % 2)), d, n, Lk, hw, 'round', th,
                   curl=-0.035 * Lk, roll=math.radians(7) * lay)
    # ... and under the wing: the under coverts, in two rows
    for N_, v0, L, hw, lift, th in ((14, 0.2, 0.38, 0.072, 0.03, 0.026), (13, 0.1, 0.24, 0.064, 0.048, 0.024)):
        for k in range(N_):
            f = k / (N_ - 1)
            u = 0.1 + (EG_ARM - 0.14) * f
            d = (along(f) + s * rnd.uniform(-0.03, 0.03)).normalized()
            _quill(sp, S + s * u + c * v0 - n * (lift + 0.004 * (k % 2)), d, -n, L * rnd.uniform(0.95, 1.05), hw,
                   'round', th, curl=0.02 * L, roll=-math.radians(7) * lay)
    # primaries: from the end of the hand (the outermost, nearly along the arm) back to the wrist, each lying over
    # the next one out, the innermost level with the secondaries
    ang = (4, 10, 17, 25, 33, 41, 48, 54)
    Lp = (1.1, 1.24, 1.3, 1.28, 1.2, 1.1, 0.99, 0.9)
    step = lambda f: 0.01 - 0.06 * (1 - f)
    for i in range(8):
        f = i / 7
        a = math.radians(ang[i])
        d = (s * math.cos(a) + c * math.sin(a)).normalized()
        base = Ht + (Wr - Ht) * f + c * (0.05 + 0.05 * f) - d * 0.1 + n * step(f)
        _quill(sp, base, d, n, Lp[i] + 0.1, 0.082, 'finger', 0.036, curl=0.08 - 0.04 * f, roll=math.radians(9) * lay)
    for up, lift, L in ((1, 0.03, 0.44), (-1, 0.03, 0.36)):    # primary coverts, above and below
        for i in range(7):
            f = i / 6
            a = math.radians(8 + 46 * f)
            d = (s * math.cos(a) + c * math.sin(a)).normalized()
            _quill(sp, Ht + (Wr - Ht) * f + c * 0.02 + n * (step(f) + up * lift) - d * 0.04, d, n * up, L, 0.058, 'round', 0.026,
                   roll=math.radians(8) * lay * up)
    for i in range(3):                            # the alula, on the wrist's leading edge
        d = (s * 0.94 + c * (0.12 + 0.1 * i) + n * 0.05).normalized()
        _quill(sp, Wr - c * (0.05 - 0.03 * i) + n * 0.045 - s * 0.05, d, n, 0.3 - 0.05 * i, 0.04, 'round', 0.024)
    # the wing is hollow underneath and its tip lifts: bend the sheet of feathers
    V = sp.V
    for i, p in enumerate(V):
        rel = Vector(p) - S
        u, v = rel.dot(s), rel.dot(c)
        k = max(0.0, v - 0.25)
        bend = -0.11 * k * k + 0.02 * max(0.0, u - EG_ARM) ** 2
        V[i] = tuple(Vector(p) + n * bend)
    return sp.build('eg_wing%d' % (sx > 0))


def _eg_tail():
    """Twelve tail feathers fanned in a wedge, the middle pair on top, drooping behind the rock."""
    sp = _Soup()
    B = Vector((0, 0.5, 0.635))
    a0 = math.radians(28)
    d0 = Vector((0, math.cos(a0), -math.sin(a0)))
    n0 = Vector((0, math.sin(a0), math.cos(a0)))
    for k in range(12):
        i = k - 5.5
        d = (Quaternion(n0, math.radians(-4.9 * i)) @ d0 - n0 * (0.012 * abs(i))).normalized()
        base = B + Vector((0.021 * i, 0, 0)) - n0 * (0.011 * abs(i)) - d * 0.06
        _quill(sp, base, d, n0, 0.84 - 0.012 * i * i * 0.35, 0.074, 'round', 0.034, curl=-0.03,
               roll=math.radians(6) * (1 if i > 0 else -1))
    return sp.build('eg_tail')


def _eg_rock():
    """The rough bronze rock under the talons (dark with the eagle in the 1971 and 2009 photos), overhanging the
    column's cap; its top at z = 0."""
    rnd = random.Random(70)
    sp = _Soup()
    sp.ellipsoid((0, 0.02, -0.3), (0.6, 0.55, 0.32))                      # a boulder, widest half way up
    sp.ellipsoid((0, -0.1, -0.13), (0.4, 0.42, 0.13))                     # the shelf the feet stand on
    for k in range(17):                           # angular blocks round it (coarse solids keep their facets)
        a = 2 * math.pi * (k + rnd.uniform(-0.4, 0.4)) / 17
        r = rnd.uniform(0.3, 0.44)
        q = Quaternion((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)), rnd.uniform(0, 1.5))
        sp.ellipsoid((r * math.cos(a), r * 0.93 * math.sin(a), rnd.uniform(-0.42, -0.16)),
                     (rnd.uniform(0.15, 0.3), rnd.uniform(0.15, 0.3), rnd.uniform(0.12, 0.26)), q, seg=5, rings=3)
    ob = sculpt.union([sp.build('eg_rock')], 0.008, smooth=1, name='eg_rock')
    bpy.ops.object.select_all(action='DESELECT')  # its foot: cut level a little under the cap's top
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(plane_co=(0, 0, -EG_ROCK - 0.04), plane_no=(0, 0, 1), clear_inner=True, use_fill=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    sculpt.clay(ob, amp=0.06, scale=0.26, depth=3, seed=5)
    sculpt.clay(ob, amp=0.014, scale=0.09, depth=2, seed=6)
    sculpt.clay(ob, amp=0.004, scale=0.03, depth=2, seed=7)
    cracks = []
    for k in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        p0 = Vector((0.5 * math.cos(a), 0.47 * math.sin(a), rnd.uniform(-0.42, -0.25)))
        p1 = Vector((0.3 * math.cos(a + rnd.uniform(-0.7, 0.7)), 0.3 * math.sin(a + rnd.uniform(-0.7, 0.7)), rnd.uniform(-0.12, 0.0)))
        mid = (p0 + p1) / 2 + Vector((rnd.uniform(-0.08, 0.08), rnd.uniform(-0.08, 0.08), rnd.uniform(-0.05, 0.05)))
        cracks.append(([tuple(p0 * 1.3), tuple(mid * 1.25), tuple(p1 * 1.15)], 0.02, -0.02, (0.2, 0.3)))
    sculpt.strokes(ob, cracks)
    return ob


def _eg_feet(rock):
    """The feet: three toes forward and one behind on each, knuckled, laid over the rock, the talons hooked into it."""
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(rock, bpy.context.evaluated_depsgraph_get())

    def on_rock(x, y, r):
        hit = bvh.ray_cast(Vector((x, y, 1.0)), Vector((0, 0, -1)))
        return Vector((x, y, (hit[0].z if hit[0] is not None else -0.3) + r * 0.75))

    sp = _Soup()
    for sx in (-1, 1):
        A = Vector((sx * 0.19, -0.13, 0.1))
        sp.capsule(A + Vector((0, 0.01, 0.03)), on_rock(A.x, A.y - 0.01, 0.07), 0.075, 0.075)
        for (dx, dy), L in (((0.0, -1.0), 0.21), ((-sx * 0.62, -0.78), 0.18), ((sx * 0.66, -0.75), 0.18), ((sx * 0.12, 1.0), 0.13)):
            d = Vector((dx, dy, 0)).normalized()
            R = (0.052, 0.048, 0.044, 0.04)
            J = [on_rock(A.x + d.x * L * t, A.y - 0.01 + d.y * L * t, r) + Vector((0, 0, lift))
                 for t, r, lift in zip((0.1, 0.42, 0.74, 1.0), R, (0.0, 0.012, 0.018, 0.0))]
            for a_, b_, ra, rb in zip(J[:-1], J[1:], R[:-1], R[1:]):
                sp.capsule(a_, b_, ra, rb, seg=12, k=4)
            for j, r in zip(J[1:], R[1:]):
                sp.ellipsoid(j + Vector((0, 0, 0.004)), (r * 1.13,) * 3, seg=12, rings=8)        # knuckles
            e = J[-1]
            up = Vector((0, 0, 1))
            path = [e + up * 0.012, e + d * 0.06 + up * 0.032, e + d * 0.115 + up * 0.012, e + d * 0.145 - up * 0.04,
                    e + d * 0.15 - up * 0.11]
            sp.tube(path, [0.038, 0.032, 0.024, 0.014, 0.004], n=10)                             # talon
    return sculpt.union([sp.build('eg_feet')], 0.0035, smooth=3, name='eg_feet')


def _copy(ob):
    c = ob.copy()
    c.data = ob.data.copy()
    bpy.context.scene.collection.objects.link(c)
    return c


def eagle_parts():
    """The dense sculpt: the union of the trunk, the head, the feet and the rock, with the plumage laid over them
    (separate overlapping blades: what shows is the outermost).  Origin at the rock's foot.  Returns the parts and
    the scale from the frame they were drawn in (EG_*) to the published width."""
    body = _eg_body()
    head = _eg_head()
    rock = _eg_rock()
    feet = _eg_feet(rock)
    sculpt.clay(body, amp=0.004, scale=0.07, seed=2)
    parts = [body, head, rock, feet,
             _eg_plumage(body, _eg_body_feather, 'eg_plumage', 3), _eg_plumage(head, _eg_head_feather, 'eg_hackles', 4),
             _eg_wing_feathers(1), _eg_wing_feathers(-1), _eg_tail()]
    xs = [x for ob in parts if ob is not rock for x in sculpt.co(ob)[:, 0]]
    k = 5.2 / (max(xs) - min(xs))
    print('eagle: %.3f m across the wings as drawn, scaled by %.3f' % (max(xs) - min(xs), k))
    for ob in parts:
        ob.data.transform(Matrix.Translation((0, 0, EG_ROCK * k)) @ Matrix.Scale(k, 4))
        ob.data.update()
    return parts, k


# the light mesh's charts: (how much of the texture a chart gets for its size, how readily it gives up triangles)
_EG_CHART = dict(head=(2.3, 0.05), beak=(2.3, 0.05), feet=(1.5, 0.3), leg=(1.25, 0.7), body=(1.25, 0.7), wing=(1.0, 1.0),
                 tail=(1.0, 1.0), rock=(0.75, 1.0), under=(0.04, 1.0))
_EG_GIVE = 0.004                                 # (Decimate's vertex group factor: metres of error per metre of edge)


def _eg_region(p, n):
    """The chart of a point of the eagle (in the frame it was drawn in) whose surface faces n: (part, piece)."""
    x, y, z = p
    if z < -0.03:                                # the rock: its top, its foot, and its sides in four
        if n.z < -0.6:
            return ('under', 0)
        return ('rock', 4 if n.z > 0.55 else int((math.atan2(y, x) + math.pi) / (math.pi / 2)) % 4)
    if z < 0.135 and y < 0.12:                   # toes and talons, with the rock between them
        return ('feet', 0) if n.z > -0.25 else ('under', 1)
    for sx in (-1, 1):
        if x * sx > 0.24:
            S, s, c, nn = _eg_wing(sx)
            rel = Vector(p) - S
            if rel.dot(s) > 0.26 and abs(rel.dot(nn)) < 0.32 and rel.dot(c) > -0.25:
                return ('wing', (sx, n.dot(nn) > 0))
    if y > 0.6 and z < 0.74:
        return ('tail', n.dot(Vector((0, 0.47, 0.88))) > 0)
    q = _EG_HEAD_INV @ Vector(p)
    if q.y < 0.19 and y < -0.45:
        return ('beak' if q.y < -0.13 else 'head', q.x > 0)
    if z < 0.5 and abs(x) > 0.05 and y < 0.22:
        return ('leg', (x > 0, n.y > 0))
    ax = max(range(3), key=lambda i: abs(n[i]) * (1.0, 0.8, 1.0)[i])     # the trunk: the six sides of a box
    return ('body', (ax, n[ax] > 0))


def _eg_lowpoly(hull, k, tris):
    """The light mesh: the hull collapsed to `tris` triangles, the head and the feet giving up the fewest, and laid
    out in charts that follow the eagle's parts (a wing's upper and under side each one piece), the head and feet
    drawn larger in the texture than the wings."""
    import bmesh
    from collections import Counter
    inv = Matrix.Scale(1 / k, 4) @ Matrix.Translation((0, 0, -EG_ROCK * k))
    low = _copy(hull)
    low.name = 'eagle_low'
    for _ in range(6):                           # (the weights change what a ratio yields: approach the count in steps)
        n0 = sculpt.tri_count(low)
        if n0 <= tris * 1.01:
            break
        P, N = sculpt.co(low), sculpt.normals(low)
        by_w = {}
        for i in range(len(P)):
            part = _eg_region(tuple(inv @ Vector(P[i])), Vector(N[i]))[0]
            by_w.setdefault(_EG_CHART[part][1], []).append(i)
        low.vertex_groups.clear()
        g = low.vertex_groups.new(name='give')
        for w, idx in by_w.items():
            g.add(idx, w, 'REPLACE')
        m = low.modifiers.new('dec', 'DECIMATE')
        m.ratio = max(tris / n0, 0.12)
        m.vertex_group = g.name
        m.vertex_group_factor = _EG_GIVE
        low.modifiers.new('tri', 'TRIANGULATE')
        sculpt.apply_modifiers(low)
    low.vertex_groups.clear()
    sculpt.smooth_shade(low)
    bm = bmesh.new()
    bm.from_mesh(low.data)
    seen, junk = set(), []                       # crumbs the voxel grid left beside the eagle
    for v in bm.verts:
        if v in seen:
            continue
        comp, stack = [v], [v]
        seen.add(v)
        while stack:
            a_ = stack.pop()
            for e in a_.link_edges:
                o = e.other_vert(a_)
                if o not in seen:
                    seen.add(o)
                    comp.append(o)
                    stack.append(o)
        if len(comp) < 200:
            junk += comp
    bmesh.ops.delete(bm, geom=junk, context='VERTS')
    # charts
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    lab = [_eg_region(tuple(inv @ f.calc_center_median()), f.normal) for f in bm.faces]
    near = [[g_.index for e in f.edges for g_ in e.link_faces if g_ is not f] for f in bm.faces]
    for _ in range(5):                           # a face among others' joins them
        new = lab[:]
        for i, nb in enumerate(near):
            c = Counter(lab[j] for j in nb).most_common(1)
            if c and c[0][0] != lab[i] and c[0][1] >= 2:
                new[i] = c[0][0]
        lab = new
    for _ in range(3):                           # islands of a few faces join the chart round them
        seen = [False] * len(lab)
        for i in range(len(lab)):
            if seen[i]:
                continue
            comp, stack = [], [i]
            seen[i] = True
            while stack:
                a_ = stack.pop()
                comp.append(a_)
                for j in near[a_]:
                    if not seen[j] and lab[j] == lab[i]:
                        seen[j] = True
                        stack.append(j)
            if len(comp) < 14:
                c = Counter(lab[j] for a_ in comp for j in near[a_] if lab[j] != lab[i]).most_common(1)
                if c:
                    for a_ in comp:
                        lab[a_] = c[0][0]
    for e in bm.edges:
        fs = e.link_faces
        e.seam = len(fs) == 2 and lab[fs[0].index] != lab[fs[1].index]
    bm.to_mesh(low.data)
    bm.free()
    if not low.data.uv_layers:
        low.data.uv_layers.new(name='UVMap')
    bpy.ops.object.select_all(action='DESELECT')
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.002)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode='OBJECT')
    uv = low.data.uv_layers.active.data
    for poly in low.data.polygons:
        w = _EG_CHART[lab[poly.index][0]][0]
        for li in poly.loop_indices:
            uv[li].uv = uv[li].uv * w
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0025)
    bpy.ops.object.mode_set(mode='OBJECT')
    cnt = Counter(l[0] for l in lab)
    print('eagle: light mesh', sculpt.tri_count(low), 'triangles,', len(set(lab)), 'charts:', dict(cnt))
    return low


def eagle_sculpt(size=1024):
    """Sculpt the eagle on its rock, bake it onto a light mesh and write both (blender/sculpt.py)."""
    import time
    t0 = time.time()
    parts, k = eagle_parts()
    print('eagle: sculpt %.0f s' % (time.time() - t0))
    hull = sculpt.union([_copy(p) for p in parts], 0.007 * k, smooth=2, name='eagle_hull')
    low = _eg_lowpoly(hull, k, 15500)
    bpy.data.objects.remove(hull)
    print('eagle: light mesh %.0f s' % (time.time() - t0))
    sculpt.bake(parts, low, 'eagle', size=size, extrude=0.03, ray=0.07, ao_dist=0.5, look=EAGLE_LOOK)
    sculpt.save(low, 'eagle')
    print('eagle: baked %.0f s' % (time.time() - t0))
    return low


# the eagle in 1997: dark bronze (ungilded until the avenue was rebuilt), a little verdigris in the feathers' hollows
# and on what faces the sky, the ridges of the feathers rubbed a shade brighter
EAGLE_LOOK = dict(base=(0.07, 0.055, 0.038), green=(0.10, 0.16, 0.13), verdigris=0.15, wear=0.7, bare=(0.26, 0.18, 0.085),
                  rough=(0.5, 0.85, 0.34), metal=(0.8, 0.1, 1.0))
SCULPTS['eagle'] = eagle_sculpt


# The four groups of white figures (the "Yonseians"; the university's symbol page: 「네 귀퉁이에는 … 연세인의 형상이
# 조각되어 있습니다」) stand near the dais' diagonals, 4.3 - 4.9 m out on its edge (Kakao roadview 2008-08, 2010-12 and
# 2011-04 from six points round it, the groups triangulated; the same four were set on granite wedges by the rebuilt
# 백양로, 2024 photo).
# Abstract white figures, the bodies and broad bands of drapery flowing into one another with holes between them (one
# metaball surface each), on a low white wedge rising towards the column; about 2 m over the dais.  In group space
# (x right as seen from outside, y back towards the column, z up from the dais, facing -y):
#  A (south-west): crouching, leaning back, one arm straight out from the column; a hooded loop over the head and
#    broad drapery falling behind
#  B (north-west): standing, both arms flung up in a wide V, a hollow ring in the breast, the robe flaring to the base
#  C (south-east): kneeling in a robe, the left arm raised high, the right forearm across the breast, a ring of
#    drapery low at the side
#  D (north-east): leaning far back towards the column, one arm raised, the drapery swept from the knees up past the
#    head in bands crossing into leaf-shaped holes (seen from the sides)
_META_K = 0.57 * 1.35    # a lone ellipsoid's surface lies at 0.57 x radius x size; a row of them merges wider


def _meta_ellipsoid(co, x, y, z, hx, hy, hz):
    """One metaball element: centre co, local axes x, y, z (unit), surface half-extents hx, hy, hz."""
    q = Matrix((x, y, z)).transposed().to_quaternion()
    return (Vector(co), q, (hx / _META_K, hy / _META_K, hz / _META_K))


def _figure(joints, edges, radii):
    """A solid part of a figure (body, robe, hood) as metaball ellipsoids strung along the edges between `joints`,
    each joint's radius a number or (across, front-to-back)."""
    J = [Vector(j) for j in joints]
    R = [r if isinstance(r, (tuple, list)) else (r, r) for r in radii]
    out = []
    for a, b in edges:
        e = J[b] - J[a]
        L = e.length
        e.normalize()
        x = Vector(Y_).cross(e)
        x = x.normalized() if x.length > 0.2 else Vector(X_)
        y = e.cross(x).normalized()
        n = max(2, int(L / 0.07) + 1)
        for i in range(n):
            t = i / (n - 1)
            rx = R[a][0] + (R[b][0] - R[a][0]) * t
            ry = R[a][1] + (R[b][1] - R[a][1]) * t
            out.append(_meta_ellipsoid(J[a] + e * (L * t), x, y, e, rx, ry, max(rx, ry, L / (n - 1))))
    return out


def _drapery(pts, widths, nrm=(0, 0, 1), th=0.08):
    """A flowing band (the sculptures' drapery and flat limbs) along a smooth curve through pts: half-width widths[k]
    (a list, a number, or (w0, w1) tapering), its broad face turned towards `nrm`, th thick; metaball ellipsoids."""
    pts = [Vector(p) for p in pts]
    n_ = len(pts)
    closed = (pts[0] - pts[-1]).length < 1e-3
    if isinstance(widths, (int, float)):
        widths = [widths] * n_
    elif len(widths) != n_:
        widths = [widths[0] + (widths[1] - widths[0]) * k / (n_ - 1) for k in range(n_)]
    if closed:
        ext = [pts[-2]] + pts + [pts[1]]
    else:
        ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    sp, sw = [], []
    for i in range(n_ - 1):                 # Catmull-Rom through the points, finely
        p0, p1, p2, p3 = ext[i:i + 4]
        m = max(2, int((p2 - p1).length / 0.05))
        for j in range(m):
            t = j / m
            sp.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                             + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
            sw.append(widths[i] + (widths[i + 1] - widths[i]) * t)
    sp.append(pts[-1])
    sw.append(widths[-1])
    out = []
    for k, p in enumerate(sp):
        d = (sp[min(k + 1, len(sp) - 1)] - sp[max(k - 1, 0)]).normalized()
        nv = Vector(nrm)
        nv = nv - d * nv.dot(d)
        nv = nv.normalized() if nv.length > 1e-4 else d.orthogonal().normalized()
        s = nv.cross(d).normalized()
        taper = 1.0 if closed else min(1.0, 0.45 + 0.55 * min(k, len(sp) - 1 - k) / 2)
        out.append(_meta_ellipsoid(p, s, nv, d, sw[k] * taper, th / 2, max(0.07, 0.6 * sw[k] * taper)))
    return out


def _meta_mesh(name, elems, res=0.035, tris=4500):
    """Polygonise metaball elements into one smooth mesh object (decimated to about `tris` triangles)."""
    mball = bpy.data.metaballs.new(name)
    mball.resolution = mball.render_resolution = res
    mball.threshold = 0.6
    ob = bpy.data.objects.new(name, mball)
    bpy.context.scene.collection.objects.link(ob)
    for co, q, size in elems:
        e = mball.elements.new(type='ELLIPSOID')
        e.co, e.rotation, e.radius, e.stiffness = co, q, 1.0, 2.0
        e.size_x, e.size_y, e.size_z = size
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mball)
    out = bpy.data.objects.new(name + '_mesh', me)
    bpy.context.scene.collection.objects.link(out)
    nt = sum(len(p.vertices) - 2 for p in me.polygons)
    if nt > tris:
        dec = out.modifiers.new('dec', 'DECIMATE')
        dec.ratio = tris / nt
        baked = _bake(out)
        bpy.data.objects.remove(out)
        out = baked
    return out


def _ring_pts(c, r, axis_u, axis_v, a0=0.0, a1=360.0, n=14, squash=1.0):
    """Points round an (elliptical) arc centred at c in the plane of axis_u, axis_v (degrees)."""
    c, u, v = Vector(c), Vector(axis_u), Vector(axis_v)
    return [c + u * (r * math.cos(math.radians(a0 + (a1 - a0) * k / (n - 1))))
            + v * (r * squash * math.sin(math.radians(a0 + (a1 - a0) * k / (n - 1)))) for k in range(n)]


# each group: its wedge base (footprint, height at the front and at the back) and its parts:
#   ('body', joints, edges, radii)  solid part;  ('band', pts, widths, nrm)  band of drapery or a flat limb
X_, Y_, Z_ = (1, 0, 0), (0, 1, 0), (0, 0, 1)
YONSEIANS = {
    'A': dict(base=([(-0.5, -0.5), (0.45, -0.52), (0.62, 0.05), (0.42, 0.55), (-0.45, 0.52), (-0.62, 0.0)], 0.12, 0.36),
              parts=[
                  # crouching on the folded legs, the robe spread over the wedge, the body leaning back
                  ('body', [(0, 0.0, 0.0), (0, 0.08, 0.32), (0, 0.18, 0.58)], [(0, 1), (1, 2)],
                   [(0.3, 0.24), (0.2, 0.16), (0.13, 0.11)]),
                  ('body', [(0, 0.15, 0.3), (0, 0.32, 0.85), (0, 0.38, 1.12), (0, 0.4, 1.27), (0, -0.3, 0.3), (0, -0.12, 0.06)],
                   [(0, 1), (1, 2), (2, 3), (0, 4), (4, 5)], [(0.22, 0.18), (0.18, 0.13), 0.07, 0.11, 0.16, 0.12]),
                  # the hood: a loop from the brow up over the head and down the back
                  ('band', [(0, 0.26, 1.36), (0, 0.42, 1.56), (0.02, 0.66, 1.6), (0.04, 0.84, 1.4), (0.04, 0.82, 1.04),
                            (0.02, 0.6, 0.74)], (0.12, 0.17), X_),
                  # the arm held straight out from the column, a flat blade with a broad angular hand
                  ('band', [(-0.16, 0.28, 1.02), (-0.12, -0.08, 0.96), (-0.08, -0.4, 0.9), (-0.05, -0.62, 0.84)],
                   [0.08, 0.085, 0.09, 0.1], Z_),
                  # drapery falling behind, and the robe over the knees
                  ('band', [(0.18, 0.3, 1.0), (0.3, 0.55, 0.76), (0.35, 0.68, 0.45), (0.28, 0.6, 0.08)], (0.18, 0.25), X_),
                  ('band', [(-0.2, 0.05, 0.62), (-0.27, -0.25, 0.44), (-0.3, -0.48, 0.16)], (0.2, 0.24), (1, 0, 0.3)),
              ]),
    'B': dict(base=([(-0.45, -0.45), (0.45, -0.45), (0.55, 0.25), (0.0, 0.55), (-0.55, 0.25)], 0.2, 0.48),
              parts=[
                  ('body', [(0, 0.02, 0.0), (0, 0.02, 0.38), (0, 0.02, 0.66)], [(0, 1), (1, 2)],
                   [(0.24, 0.19), (0.13, 0.1), 0.07]),
                  ('body', [(0, 0.02, 0.2), (0, 0.02, 0.75), (0, 0.03, 1.2), (0, 0.03, 1.42), (0, 0.03, 1.56)],
                   [(0, 1), (1, 2), (2, 3), (3, 4)], [(0.22, 0.16), 0.09, (0.13, 0.1), 0.06, 0.1]),
                  # the arms flung up in a wide V, the left (seen right) higher and longer
                  ('band', [(0.12, 0.03, 1.3), (0.28, 0.05, 1.52), (0.44, 0.07, 1.78), (0.54, 0.09, 1.98)], (0.12, 0.06), Y_),
                  ('band', [(-0.12, 0.03, 1.3), (-0.26, 0.05, 1.5), (-0.38, 0.07, 1.7), (-0.45, 0.09, 1.86)], (0.11, 0.05), Y_),
                  # the hollow ring in the breast
                  ('band', _ring_pts((0, -0.05, 1.08), 0.2, X_, Z_, n=16, squash=1.2), 0.065, Y_),
                  # the robe flaring down to the base, a sweep of drapery up one side
                  ('band', [(0.05, 0.0, 0.8), (0.2, 0.05, 0.5), (0.36, 0.1, 0.22), (0.45, 0.14, 0.04)], (0.13, 0.24), Y_),
                  ('band', [(-0.05, 0.0, 0.8), (-0.2, 0.05, 0.5), (-0.36, 0.1, 0.22), (-0.45, 0.14, 0.04)], (0.13, 0.22), Y_),
                  ('band', [(-0.38, 0.12, 0.15), (-0.45, 0.08, 0.6), (-0.37, 0.05, 0.95), (-0.2, 0.03, 1.18)], (0.1, 0.05), Y_),
              ]),
    'C': dict(base=([(-0.55, -0.5), (0.52, -0.52), (0.64, 0.08), (0.36, 0.55), (-0.5, 0.55), (-0.66, 0.04)], 0.12, 0.35),
              parts=[
                  # kneeling: the robe a broad mass from the knees to the hips, the upright breast, the hooded head
                  ('body', [(0, -0.02, 0.0), (0, 0.04, 0.28)], [(0, 1)], [(0.32, 0.24), (0.22, 0.16)]),
                  ('body', [(0, 0.15, 0.4), (0, 0.08, 0.92), (0, 0.05, 1.15), (0, 0.03, 1.29), (0, -0.3, 0.25)],
                   [(0, 1), (1, 2), (2, 3), (0, 4)], [(0.3, 0.2), (0.17, 0.13), 0.07, 0.11, (0.28, 0.16)]),
                  # the left arm raised high, a little out
                  ('band', [(0.18, 0.06, 1.1), (0.27, 0.02, 1.34), (0.34, -0.02, 1.56), (0.38, -0.04, 1.74)], (0.09, 0.055), Y_),
                  # the right forearm across the breast
                  ('band', [(-0.2, 0.05, 1.06), (-0.26, -0.15, 0.92), (0.0, -0.26, 0.9), (0.3, -0.28, 0.88)], 0.06, Z_),
                  # a ring of drapery low at the right side, and the drapery falling behind
                  ('band', _ring_pts((-0.3, 0.18, 0.5), 0.24, Y_, Z_, n=16), 0.07, X_),
                  ('band', [(0.25, 0.25, 0.9), (0.38, 0.38, 0.6), (0.4, 0.36, 0.25), (0.34, 0.28, 0.05)], (0.12, 0.22), X_),
              ]),
    'D': dict(base=([(-0.5, -0.95), (0.5, -0.95), (0.58, 0.2), (0.35, 0.62), (-0.35, 0.62), (-0.58, 0.2)], 0.1, 0.4),
              parts=[
                  # leaning far back towards the column, the knees out over the long low end of the wedge
                  ('body', [(0, -0.35, 0.0), (0, -0.12, 0.3), (0, 0.08, 0.5)], [(0, 1), (1, 2)],
                   [(0.26, 0.3), (0.18, 0.17), (0.12, 0.1)]),
                  ('body', [(0, -0.1, 0.35), (0, 0.25, 0.85), (0, 0.38, 1.1), (0, 0.45, 1.25), (0, -0.5, 0.45), (0, -0.8, 0.12)],
                   [(0, 1), (1, 2), (2, 3), (0, 4), (4, 5)], [(0.2, 0.17), (0.16, 0.12), 0.07, 0.11, 0.13, 0.1]),
                  # one arm raised up and out
                  ('band', [(0.15, 0.25, 1.0), (0.2, 0.12, 1.26), (0.22, 0.0, 1.5), (0.2, -0.06, 1.66)], (0.08, 0.05), Y_),
                  # drapery swept from the knees up past the head in bands crossing into leaf-shaped holes (seen from
                  # the sides)
                  ('band', [(-0.05, -0.85, 0.15), (0, -0.5, 0.75), (0.02, -0.1, 1.1), (0.04, 0.3, 1.45), (0.05, 0.6, 1.7)],
                   (0.11, 0.07), X_),
                  ('band', [(0.05, -0.6, 0.2), (0.06, -0.2, 0.45), (0.07, 0.2, 0.75), (0.08, 0.6, 1.1), (0.08, 0.85, 1.35)],
                   (0.12, 0.07), X_),
                  ('band', [(-0.06, -0.3, 1.0), (-0.05, 0.05, 0.75), (-0.04, 0.4, 0.62), (-0.03, 0.75, 0.7)], (0.08, 0.06), X_),
              ]),
}


def yonseian_group(k, size=1.1, broad=1.55):
    """Group k (A-D) of the white figures on its wedge, in group space (facing -y, outward; the column at +y).
    The table is drawn about 2 m tall; `size` scales the whole and `broad` widens the bands and the bodies (the
    roadview shows heavy white masses with a few holes rather than slender limbs)."""
    spec = YONSEIANS['ABCD'[k]]
    mb = MeshBuilder(f'yonseian_{k}')
    W = 'stone_panel'
    poly, h_front, h_back = spec['base'][:3]
    poly = [(x * size, y * size) for x, y in poly]
    ax = Vector(spec['base'][3] if len(spec['base']) > 3 else (0, 1)).normalized()      # the way the wedge rises
    ys = [ax.x * x + ax.y * y for x, y in poly]
    y0, y1 = min(ys), max(ys)
    zt = [h_front + (h_back - h_front) * (y - y0) / (y1 - y0) for y in ys]
    for i in range(len(poly)):          # (the walls reach 0.25 m below the dais top: the outer end stands on the ring)
        j = (i + 1) % len(poly)
        mb.face([(*poly[i], -0.25), (*poly[j], -0.25), (*poly[j], zt[j]), (*poly[i], zt[i])], W)
    mb.face([(*p, z) for p, z in zip(poly, zt)], W)
    zb = (h_front + h_back) / 2 - 0.04          # the figures stand in the wedge
    bw = broad ** 0.5                           # (bodies widen less than the bands)
    elems = []
    for part in spec['parts']:
        if part[0] == 'body':
            _, J, E, R = part
            elems += _figure(J, E, [tuple(c * bw for c in r) if isinstance(r, tuple) else r * bw for r in R])
        else:
            _, P, wd, nrm = part
            wd = [w * broad for w in wd] if isinstance(wd, (list, tuple)) else wd * broad
            elems += _drapery(P, wd, nrm, th=0.13)
    ob = _meta_mesh(f'ymeta{k}', elems)
    ob.data.transform(Matrix.Translation((0, 0, zb)) @ Matrix.Scale(size, 4))
    _to_mb(ob, mb, W)
    return mb


# The dais and its precinct (Kakao roadview 2008-08 and 2010-12 / 2011-04; the 1995 aerial photo shows the ring of
# beds broken by the walks): a low round dais of light stone on a ring of brick paving a step above the walks; four
# brick walks between low kerbs through four quadrant beds of clipped azaleas (planted by tools/build_campus.py) out to
# a round kerb.  The walks run along the statue's axes; the east one meets 백양로's sidewalk, which bounds the beds.
EAGLE_SITE = dict(dais=[4.6, 0.4], ring=[5.6, 0.2], beds=9.5, walk=3.0, walk_edge=99.0)
PLATFORM_Z = EAGLE_SITE['dais'][1]


def eagle_tower(site=EAGLE_SITE):
    """The round dais on its brick ring, the column's foot sweeping out concavely onto it, the tall tapering white
    shaft and its cap."""
    mb = MeshBuilder('eagle_tower')
    W, Wd = 'stone_white', 'granite_light'
    (rd, zd), (rr, zr) = site['dais'], site['ring']
    mb.cylinder((0, 0), rr, -0.8, zr, 'curb', seg=64, cap_top=False, smooth=False)     # (runs into the ground)
    for k in range(64):                 # the ring's top as an annulus (a disc would take its baked light from under the dais)
        a0, a1 = 2 * math.pi * k / 64, 2 * math.pi * (k + 1) / 64
        mb.face([(r_ * math.cos(a_), r_ * math.sin(a_), zr) for r_, a_ in ((rd - 0.05, a0), (rr, a0), (rr, a1), (rd - 0.05, a1))],
                'pavers')
    mb.cylinder((0, 0), rd, zr - 0.05, zd, 'stone_step', seg=56, mat_cap=Wd, smooth=False)
    z0 = zd
    # the flaring foot: each face curves out concavely onto the dais, then the shaft tapers to the cap
    zf, z1 = z0 + 2.6, 9.3
    prof = []
    for k in range(11):
        t = k / 10
        prof.append((z0 + (zf - z0) * t, 0.36 + (1.25 - 0.36) * (1 - t) ** 2.8))
    prof.append((z1, 0.34))             # 0.72 -> 0.68 m (reference/고증.md 4.1.1: 0.68 - 0.70 m at 5 - 7.5 m, 2011 roadview)
    rings = [[(-w, -w, z), (w, -w, z), (w, w, z), (-w, w, z)] for z, w in prof]
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            mb.face([a[i], a[j], b[j], b[i]], W)
    # the cap: a thin lip a little wider than the shaft
    mb.box((0, 0, z1 + 0.06), (0.8, 0.8, 0.12), W)
    mb.box((0, 0, z1 + 0.16), (0.72, 0.72, 0.08), W)
    # a dark tablet leaning on a low block before the foot's front (the 2010 roadview from the south)
    yb = -1.6
    blk = [(-0.55, yb - 0.3), (0.55, yb - 0.3), (0.55, yb + 0.3), (-0.55, yb + 0.3)]
    zt = [z0 + 0.08, z0 + 0.08, z0 + 0.42, z0 + 0.42]
    for i in range(4):
        j = (i + 1) % 4
        mb.face([(*blk[i], z0 - 0.02), (*blk[j], z0 - 0.02), (*blk[j], zt[j]), (*blk[i], zt[i])], Wd)
    mb.face([(*p, z + 0.012) for p, z in zip([(-0.5, yb - 0.26), (0.5, yb - 0.26), (0.5, yb + 0.26), (-0.5, yb + 0.26)],
                                            [z0 + 0.1, z0 + 0.1, z0 + 0.41, z0 + 0.41])], 'bronze_patina')
    mb.face([(*p, z) for p, z in zip(blk, zt)], Wd)
    return mb, z1 + 0.2


def eagle_kerbs(site=EAGLE_SITE):
    """The low concrete kerb round the four beds' outer edge, cut by the walks and where the beds meet 백양로's
    sidewalk (local +x, `walk_edge` from the centre).  (The walks' own edges get the campus-wide kerbs that
    tools/build_campus.py lays along every paved edge.)"""
    mb = MeshBuilder('eagle_kerbs')
    K = 'curb'
    R, hw, xe = site['beds'], site['walk'] / 2, site['walk_edge']
    kw, kh = 0.15, 0.25

    def seg(a, b, h=kh):
        a, b = Vector((*a, 0)), Vector((*b, 0))
        d = (b - a)
        if d.length < 0.05:
            return
        d.normalize()
        mb.box(tuple((a + b) / 2 + Vector((0, 0, (h - 0.4) / 2))), ((b - a).length, kw, h + 0.4), K,
               rotz=math.atan2(d.y, d.x), skip=('bottom',))

    for q in range(4):
        a = math.radians(90 * q)
        # the round edge of the bed between this walk and the next
        a0 = a + math.asin((hw + kw) / R)
        a1 = a + math.pi / 2 - math.asin((hw + kw) / R)
        n = 9
        pts = [Vector((R * math.cos(a0 + (a1 - a0) * i / n), R * math.sin(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
        for p, p2 in zip(pts[:-1], pts[1:]):
            if p.x > xe - 0.2 and p2.x > xe - 0.2:
                continue
            if p2.x > xe - 0.2:
                p2 = p + (p2 - p) * ((xe - 0.2 - p.x) / (p2.x - p.x))
            if p.x > xe - 0.2:
                p = p2 + (p - p2) * ((xe - 0.2 - p2.x) / (p.x - p2.x))
            seg(tuple(p), tuple(p2))
    # where the beds meet the sidewalk
    if xe < R:
        y_ = math.sqrt(R ** 2 - (xe - 0.2) ** 2)
        for sg in (-1, 1):
            seg((xe - 0.2, sg * (hw + kw)), (xe - 0.2, sg * y_))
    return mb


def eagle_statue(site=None):
    site = dict(EAGLE_SITE, **(site or {}))
    tower, top = eagle_tower(site)
    eagle = sculpt.load('eagle')                 # the eagle on its rock (eagle_sculpt), the rock's foot on the cap
    eagle.data.transform(Matrix.Translation((0, 0, top - 0.04)))
    out = [tower.build(), eagle, eagle_kerbs(site).build()]
    # the four groups at the diagonals, facing out: A south-west, B north-west, C south-east, D north-east (the statue
    # faces -y, south-south-west; +x is east-south-east, towards 백양로)
    # Each at its measured bearing and distance (site['groups'], tools/build_campus.py EAGLE_GROUPS: 4.3 - 4.9 m, on
    # the dais' edge, the wedge's outer end down on the brick ring); without them the diagonals at 4.6 m
    zd = site['dais'][1]
    rot = site.get('rot', math.radians(-14))
    groups = site.get('groups') or [(math.degrees(math.pi / 2 - rot) - d, 4.6) for d in (-135, 135, -45, 45)]
    for k, (brg, r) in enumerate(groups):
        a = math.pi / 2 - math.radians(brg) - rot          # compass bearing -> the statue frame's angle
        g = yonseian_group(k).build()
        g.matrix_world = Matrix.Translation((r * math.cos(a), r * math.sin(a), zd)) @ \
            Matrix.Rotation(a + math.pi / 2, 4, 'Z')
        bpy.context.view_layer.update()
        out.append(g)
    return out
