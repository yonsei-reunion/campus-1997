"""Bronze statues of the 1997 campus, modelled from photographs.

언더우드 동상 (Horace G. Underwood, the 1955 statue at the entrance of the Underwood courtyard; photos: Wikimedia
Commons, Category:Statue of Horace Grant Underwood, 2009 - 2019, and the 2010 roadview): a balding man with a full
moustache in a morning coat with tails over a waistcoat of six buttons, both arms held out in front of him, palms up,
on a bronze plate on a tapering light granite pedestal (a cavetto cap, the inscribed plaque on the front, a base block
with a sloped wash) standing on an octagonal slab, an octagon of rock-faced blocks and a round platform in a curb ring.
Trousers, shoes and torso are the CC0 Quaternius "Ultimate Modular Men" Suit character; head, hands, sleeves and coat
are sculpted here.

독수리상 (unveiled 9 May 1970; Yonsei: "12.3m high with a 2.5t bronze eagle on a rectangular prism tower. The eagle is
2.6m tall and 5.2m wide ... the statue of Yonseian carved on all four sides"; photos: 2024 campus photo, the 1997 aerial
photo, the 2024 virtual campus): a bronze eagle with its wings raised in a wide V, primaries spread like fingers,
gripping a rock on top of a tall white square column that stands on a pedestal with figures carved on its four faces.

Both return Blender objects in their local frame (front = -Y, ground at z = 0); blender/build.py places them.
"""
import math
import os
import random

import bpy
from mathutils import Matrix, Quaternion, Vector

from common import MeshBuilder, material, ROOT

SUIT = os.path.join(ROOT, 'assets_src', 'quaternius', 'ultimate-modular-characters', 'Suit.gltf')


# ----------------------------------------------------------------------------- helpers
def _bake(ob):
    """Apply every modifier (and an armature deform) into a new plain mesh object."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=False, depsgraph=dg)
    out = bpy.data.objects.new(ob.name + '_baked', me)
    out.matrix_world = ob.matrix_world.copy()
    bpy.context.scene.collection.objects.link(out)
    return out


def _join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return ob


def _set_material(ob, name):
    ob.data.materials.clear()
    ob.data.materials.append(material(name))
    for p in ob.data.polygons:
        p.material_index = 0


def _skin(name, verts, edges, radii, root=0, levels=2):
    """A skin-modifier tube (organic limbs and bodies) with subdivision, baked to a mesh."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], edges, [])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    sk = ob.modifiers.new('skin', 'SKIN')
    sk.branch_smoothing = 0.6
    sk.use_smooth_shade = True
    for i, r in enumerate(radii):
        me.skin_vertices[0].data[i].radius = r if isinstance(r, (tuple, list)) else (r, r)
        me.skin_vertices[0].data[i].use_root = (i == root)
    sub = ob.modifiers.new('sub', 'SUBSURF')
    sub.levels = levels
    sub.render_levels = levels
    baked = _bake(ob)
    bpy.data.objects.remove(ob)
    for p in baked.data.polygons:
        p.use_smooth = True
    return baked


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


# ============================================================================= 언더우드 동상
# The 1955 statue (the third; reference/고증.md 4.2), as in the photos of 2009 - 2019 (Wikimedia Commons, Category:Statue
# of Horace Grant Underwood) and the 2010 roadview of the courtyard: a balding man with a full moustache, in a morning
# coat (wide notched lapels, one button at the waist, the fronts cut away over the hips to tails at the backs of the
# knees) over a waistcoat of six buttons, a high collar and tie, both arms held out in welcome with the palms up.  The
# trousers, shoes and torso are the CC0 Quaternius Suit character; head, hands, sleeves and the coat are modelled here.
UW_H = 2.45                    # the figure, soles to crown
UW_PED = 0.94                  # the pedestal and platform, drawn below at their measured proportions, to scale: the
#                                figure is 0.92 of the pedestal's height (1990s telephoto, reference/용재관.jpg)
UW_PLATE = 3.87 * UW_PED       # top of the bronze plate under his feet
UW_WALK = ((3.85 * UW_PED, 0.30 * UW_PED), (3.25 * UW_PED, 0.34 * UW_PED))   # (radius, height): the curb ring with its
#                                gravel, the round slab (blender/build.py makes them walkable)


def _ellipsoid(mb, c, abc, q=None, seg=32, rings=18):
    R = (q or Quaternion()).to_matrix()
    c = Vector(c)
    P = []
    for j in range(rings + 1):
        th = math.pi * j / rings
        row = []
        for i in range(seg):
            ph = 2 * math.pi * i / seg
            v = Vector((abc[0] * math.sin(th) * math.cos(ph), abc[1] * math.sin(th) * math.sin(ph), abc[2] * math.cos(th)))
            row.append(c + R @ v)
        P.append(row)
    tag = 'e%d' % len(mb.faces)                      # (shared vertices: a closed solid for the remesher)
    for j in range(rings):
        for i in range(seg):
            k = (i + 1) % seg
            if j == 0:
                q = [P[0][0], P[1][i], P[1][k]]
            elif j == rings - 1:
                q = [P[j][i], P[rings][0], P[j][k]]
            else:
                q = [P[j][i], P[j + 1][i], P[j + 1][k], P[j][k]]
            mb.face(q, 'bronze_patina', smooth=tag)


def _capsule(mb, p0, p1, r, seg=18, k=6):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    R = Vector((1, 0, 0)).rotation_difference(d.normalized() if L > 1e-6 else Vector((1, 0, 0))).to_matrix()
    prof = [(-r * math.cos(math.pi / 2 * i / k), r * math.sin(math.pi / 2 * i / k)) for i in range(1, k + 1)]
    prof += [(L + r * math.sin(math.pi / 2 * i / k), r * math.cos(math.pi / 2 * i / k)) for i in range(k)]
    rings = [[p0 + R @ Vector((x, rho * math.cos(2 * math.pi * i / seg), rho * math.sin(2 * math.pi * i / seg)))
              for i in range(seg)] for x, rho in prof]
    tag = 'c%d' % len(mb.faces)
    loft(mb, rings, 'bronze_patina', cap0=False, cap1=False, tag=tag)
    a, b = p0 + R @ Vector((-r, 0, 0)), p0 + R @ Vector((L + r, 0, 0))
    for i in range(seg):
        j = (i + 1) % seg
        mb.face([a, rings[0][j], rings[0][i]], 'bronze_patina', smooth=tag)
        mb.face([b, rings[-1][i], rings[-1][j]], 'bronze_patina', smooth=tag)


def _blob(name, elems, voxel, smooth=4, factor=0.6):
    """Sculpt an organic form from overlapping solids: their union is remeshed on a voxel grid and the creases where
    they meet are smoothed.  elems: ('ell', c, (a, b, c)[, quat]) | ('ball', c, r) | ('cap', p0, p1, r)."""
    mb = MeshBuilder(name)
    for e in elems:
        if e[0] == 'ell':
            _ellipsoid(mb, e[1], e[2], e[3] if len(e) > 3 else None)
        elif e[0] == 'ball':
            _ellipsoid(mb, e[1], (e[2],) * 3, None, seg=20, rings=12)
        else:
            _capsule(mb, e[1], e[2], e[3])
    ob = mb.build()
    m = ob.modifiers.new('rm', 'REMESH')
    m.mode = 'VOXEL'
    m.voxel_size = voxel
    m.adaptivity = 0.0
    if smooth:
        sm = ob.modifiers.new('sm', 'SMOOTH')
        sm.factor = factor
        sm.iterations = smooth
    out = _bake(ob)
    bpy.data.objects.remove(ob)
    for p in out.data.polygons:
        p.use_smooth = True
    return out


def _decimate(ob, ratio):
    m = ob.modifiers.new('dec', 'DECIMATE')
    m.ratio = ratio
    out = _bake(ob)
    bpy.data.objects.remove(ob)
    for p in out.data.polygons:
        p.use_smooth = True
    return out


def _qx(deg):
    return Quaternion((1, 0, 0), math.radians(deg))


def _qy(deg):
    return Quaternion((0, 1, 0), math.radians(deg))


def _qz(deg):
    return Quaternion((0, 0, 1), math.radians(deg))


def underwood_head():
    """His head at life size (eye level at z = 0, facing -Y), to be scaled up: a high balding crown with the hair kept
    short over the ears and the back, a tuft at the front of the crown, deep-set eyes under a strong brow, a straight
    nose, a full moustache turned up at the ends, a rounded chin, ears standing a little out (2019 photo)."""
    E = [
        ('ell', (0, 0.012, 0.026), (0.077, 0.1, 0.09)),                      # cranium, high and bald on top
        ('ell', (0, -0.035, 0.042), (0.068, 0.062, 0.056)),                  # forehead
        ('ell', (0, -0.04, -0.038), (0.066, 0.064, 0.058)),                  # cheeks and upper jaw
        ('ell', (0, -0.03, -0.075), (0.063, 0.06, 0.042)),                   # jaw
        ('ell', (0, -0.076, -0.1), (0.03, 0.023, 0.02)),                     # chin
        ('cap', (0, -0.097, 0.008), (0, -0.112, -0.028), 0.0075),            # nose
        ('ell', (0, -0.112, -0.034), (0.011, 0.011, 0.01)),                  # its tip
        ('ell', (0, -0.096, -0.068), (0.016, 0.007, 0.006)),                 # lower lip under the moustache
        ('ell', (0, 0.064, 0.022), (0.064, 0.05, 0.07)),                     # hair at the back
        ('ell', (0, -0.04, 0.102), (0.02, 0.026, 0.008), _qx(30)),           # the tuft at the front of the crown
        ('cap', (0, 0.012, -0.06), (0, 0.02, -0.2), 0.052),                  # neck
    ]
    for sx in (-1, 1):
        E += [
            ('ell', (sx * 0.047, -0.07, -0.012), (0.018, 0.02, 0.014)),       # cheekbones
            ('ell', (sx * 0.03, -0.091, 0.018), (0.028, 0.014, 0.01), _qy(sx * 10)),    # brow ridge
            ('ball', (sx * 0.031, -0.079, 0.0), 0.0098),                      # eyes
            ('ell', (sx * 0.011, -0.104, -0.038), (0.008, 0.008, 0.007)),     # wings of the nose
            ('ell', (sx * 0.017, -0.107, -0.049), (0.02, 0.01, 0.008), _qy(sx * 15)),   # moustache under the nose
            ('ell', (sx * 0.038, -0.099, -0.056), (0.016, 0.009, 0.006), _qy(sx * 30)),  # ... out to the corners
            ('ball', (sx * 0.053, -0.089, -0.053), 0.005),                    # ... the ends turned up
            ('ell', (sx * 0.075, 0.022, -0.012), (0.01, 0.025, 0.033), _qy(sx * -8) @ _qx(-12)),    # ears
            ('ell', (sx * 0.07, 0.035, 0.03), (0.012, 0.05, 0.035)),         # hair over the ears
        ]
    return _blob('uwhead', E, 0.0026, smooth=10, factor=0.6)


def underwood_hand(side):
    """An open hand at life size, palm up, the fingers together and a little curled, the thumb up and out (2019 photo).
    Frame: wrist at the origin, x along the fingers, z out of the palm, y towards the thumb; side = +1 his left."""
    E = [('ell', (0.048, 0, -0.002), (0.05, 0.04, 0.015)),                    # palm
         ('ell', (0.03, 0.022, -0.004), (0.026, 0.017, 0.016)),               # ball of the thumb
         ('cap', (-0.045, 0, 0), (0.01, 0, -0.002), 0.024)]                   # wrist
    for y, L in ((0.028, 0.08), (0.0095, 0.088), (-0.0095, 0.082), (-0.027, 0.066)):
        a = Vector((0.09, y, 0.0))
        b = a + Vector((L * 0.45, 0, L * 0.05))
        c = b + Vector((L * 0.3, 0, L * 0.15))
        d = c + Vector((L * 0.22, 0, L * 0.2))
        E += [('cap', a, b, 0.0092), ('cap', b, c, 0.0084), ('cap', c, d, 0.0075)]
    t0, t1 = Vector((0.022, 0.034, -0.004)), Vector((0.05, 0.06, 0.014))
    t2 = t1 + Vector((0.022, 0.012, 0.03))
    E += [('cap', t0, t1, 0.012), ('cap', t1, t2, 0.0098)]
    ob = _blob('uwhand%d' % (side > 0), E, 0.0022, smooth=3, factor=0.5)
    if side < 0:                                   # the thumb on the outer side of each hand
        for v in ob.data.vertices:
            v.co.y = -v.co.y
        ob.data.flip_normals()
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


def underwood_figure(H=UW_H):
    """Trousers and shoes: the Quaternius Suit character's legs in its relaxed stance, as one bronze mesh, soles at
    z = 0, facing -Y (the character's jacket, short arms and mitten hands are not used)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SUIT, merge_vertices=True, import_shading='SMOOTH')
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE')
    keep = [o for o in new if o.type == 'MESH' and o.name in ('Suit_Legs', 'Suit_Feet')]
    arm.animation_data_create()
    arm.animation_data.action = bpy.data.actions.get('Idle_Neutral')
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    y0 = (arm.matrix_world @ arm.pose.bones['Hips'].head).y
    baked = []
    for m in keep:
        b = _bake(m)
        b.matrix_world = m.matrix_world.copy()
        baked.append(b)
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    ob = _join(baked, 'underwood_legs')
    s = 1.344 * H / 2.45                         # (the character's collar under his chin)
    z0 = min(v.co.z for v in ob.data.vertices)
    for v in ob.data.vertices:                   # wide trousers
        v.co = Vector((v.co.x * s * 1.25, (v.co.y - y0) * s * 1.15, (v.co.z - z0) * s))
    ob.data.update()
    _set_material(ob, 'bronze_patina')
    return ob


# his coat over the waistcoat, ring by ring from the hips to the collar (z, half-width, half-depth, centre y), at
# H = 2.45: broad in the chest, a full waistcoat, sloping shoulders (2011 and 2019 photos)
UW_TORSO = [(1.28, 0.19, 0.13, 0.0), (1.433, 0.198, 0.136, 0.0), (1.56, 0.21, 0.148, -0.014),
            (1.7, 0.228, 0.148, -0.01), (1.82, 0.236, 0.136, 0.0), (1.895, 0.232, 0.122, 0.004),
            (1.955, 0.214, 0.106, 0.008), (2.005, 0.14, 0.09, 0.01), (2.05, 0.08, 0.074, 0.012)]
UW_SE = 2.6                                      # the rings are superellipses: flatter front, back and sides


def _torso_at(z, H):
    k = H / 2.45
    T = [(a * k, b * k, c * k, d * k) for a, b, c, d in UW_TORSO]
    if z <= T[0][0]:
        return T[0][1:]
    for (za, *pa), (zb, *pb) in zip(T[:-1], T[1:]):
        if z <= zb:
            t = (z - za) / (zb - za)
            t = t * t * (3 - 2 * t)
            return tuple(u + (v - u) * t for u, v in zip(pa, pb))
    return T[-1][1:]


def _torso_front(x, z, H, off=0.0):
    """The point on the torso's front at (x, z), pushed `off` further out."""
    a, b, yc = _torso_at(z, H)
    u = min(abs(x) / a, 0.999)
    y = yc - b * (1 - u ** UW_SE) ** (1 / UW_SE)
    return Vector((x, y - off, z))


def underwood_coat(H=UW_H):
    """The morning coat and what shows of the waistcoat: the body of the coat, sleeves with cuffs, wide notched lapels
    rolling down to the one button at the waist, the waistcoat's six buttons between them, the high collar and tie,
    and the skirt - its fronts cut away from the waist button over the hips, the tails hanging to the backs of the
    knees with a vent between them.  Returns (MeshBuilder, joints): shoulder / elbow / wrist per side, the neck."""
    mb = MeshBuilder('underwood_coat')
    M = 'bronze_patina'
    k = H / 2.45
    # -- the body of the coat
    n = 28
    rings = []
    zs = [z for z, *_ in UW_TORSO]
    zz = []
    for za, zb in zip(zs[:-1], zs[1:]):
        zz += [za + (zb - za) * i / 3 for i in range(3)]
    zz.append(zs[-1])
    for z in zz:
        a, b, yc = _torso_at(z * k, H)
        ring = []
        for i in range(n):
            t = 2 * math.pi * i / n
            c, s_ = math.cos(t), math.sin(t)
            ring.append(Vector((a * math.copysign(abs(c) ** (2 / UW_SE), c),
                                yc + b * math.copysign(abs(s_) ** (2 / UW_SE), s_), z * k)))
        rings.append(ring)
    loft(mb, rings, M, cap0=False, cap1=True, tag='torso')
    zc = UW_TORSO[-1][0] * k                     # the collar's foot
    zw = 0.585 * H                               # the waist seam, the coat's button
    J = {'neck': Vector((0, UW_TORSO[-1][3] * k, zc)), 'top': zc + 0.06 * k, 'waist': zw, 'arms': {}}
    # -- sleeves: from the shoulders down and forward to the elbows, the forearms reaching out (2019 photo: hands wide
    # apart at the height of the waist button, palms up); loose, a turned cuff, the shirt cuff under it
    for sx in (-1, 1):
        S = Vector((sx * 0.222 * k, 0.0, 1.872 * k))
        E = S + Vector((0.42 * sx, -0.42, -0.7)).normalized() * (0.155 * H)
        W = E + Vector((0.4 * sx, -0.88, -0.12)).normalized() * (0.145 * H)
        J['arms'][sx] = (S, E, W)
        S0 = S + Vector((-sx * 0.07, 0.0, -0.03)) * k             # (the sleeve head starts inside the shoulder)
        pts = _arc(S0, S + (E - S) * 0.15, S + (E - S) * 0.45, 4)[:-1] + _arc(S + (E - S) * 0.45, E + (E - (S + W) / 2) * 0.3, W, 9)
        rad = [(0.092 - 0.025 * min(1.0, i / 12)) * k for i in range(len(pts))]
        _tube(mb, pts, rad, M, n=16, tag='slv%d' % sx, cap0=False, cap1=False, wob=0.025, seed=3 + sx)
        d = (W - pts[-2]).normalized()
        _tube(mb, [W - d * 0.055 * k, W - d * 0.05 * k, W, W + d * 0.004], [0.062 * k, 0.069 * k, 0.069 * k, 0.06 * k],
              M, n=16, tag='cuf%d' % sx)
        _tube(mb, [W, W + d * 0.03 * k], [0.05 * k, 0.047 * k], M, n=12, tag='sc%d' % sx)
    # -- lapels (his left = +X; mirrored): from behind the collar out to the notch and the peak, rolling down to the
    # waist button; each stands off the coat by its thickness
    L = zc - zw
    outer = [(0.07, 0.0), (0.105, 0.07), (0.128, 0.13), (0.114, 0.152), (0.152, 0.166), (0.138, 0.24),
             (0.105, 0.34), (0.062, (L - 0.12) / k), (0.022, (L - 0.01) / k)]
    inner = [(0.05, 0.0), (0.06, 0.07), (0.068, 0.13), (0.068, 0.152), (0.068, 0.166), (0.06, 0.24),
             (0.046, 0.34), (0.026, (L - 0.12) / k), (0.008, (L - 0.01) / k)]
    P = lambda x, d, off: _torso_front(x * k, zc - d * k, H, off * k)
    for sx in (-1, 1):
        tag = 'lap%d' % sx
        for (xa, da), (xb, db), (xc, dc), (xd, dd) in zip(outer[:-1], outer[1:], inner[1:], inner[:-1]):
            q = [P(sx * xa, da, 0.012), P(sx * xb, db, 0.012), P(sx * xc, dc, 0.016), P(sx * xd, dd, 0.016)]
            _oface(mb, q, M, (sx * 0.3, -1, 0.1), smooth=tag)
        for (xa, da), (xb, db) in zip(outer[:-1], outer[1:]):
            q = [P(sx * xa, da, 0.012), P(sx * xb, db, 0.012), P(sx * xb, db, -0.004), P(sx * xa, da, -0.004)]
            _oface(mb, q, M, (sx, -0.4, 0.3))
        for (xa, da), (xb, db) in zip(inner[:-1], inner[1:]):
            q = [P(sx * xa, da, 0.016), P(sx * xb, db, 0.016), P(sx * xb, db, -0.004), P(sx * xa, da, -0.004)]
            _oface(mb, q, M, (-sx, -0.4, 0))
        # the waistcoat's edge inside the lapel, from the collar down to its points below the last button
        wv = [(0.03, 0.06), (0.042, 0.2), (0.034, 0.36), (0.024, (L - 0.06) / k), (0.03, (L + 0.03) / k), (0.0, (L + 0.07) / k)]
        for (xa, da), (xb, db) in zip(wv[:-1], wv[1:]):
            q = [P(sx * xa, da, 0.006), P(sx * xb, db, 0.006), P(sx * xb, db, -0.003), P(sx * xa, da, -0.003)]
            _oface(mb, q, M, (-sx, -0.4, 0))
    # the coat's collar standing round the back of the neck, running into the lapels at the front
    cyn = J['neck'].y
    crings = []
    for z, r in ((zc - 0.05 * k, 0.118 * k), (zc + 0.0, 0.104 * k), (zc + 0.05 * k, 0.098 * k), (zc + 0.068 * k, 0.096 * k)):
        crings.append([Vector((r * math.cos(t), cyn + r * 0.9 * math.sin(t), z))
                       for t in (math.radians(-55 + 290 * i / 20) for i in range(21))])
    for a_, b_ in zip(crings[:-1], crings[1:]):
        for i in range(20):
            q = [a_[i], a_[i + 1], b_[i + 1], b_[i]]
            c = sum(q, Vector()) / 4
            _oface(mb, q, M, (c.x, c.y - cyn, 0), smooth='ccol')
    top = crings[-1]
    for i in range(20):                                                      # its thickness along the top
        q = [top[i], top[i + 1], Vector((top[i + 1].x * 0.86, cyn + (top[i + 1].y - cyn) * 0.86, top[i + 1].z)),
             Vector((top[i].x * 0.86, cyn + (top[i].y - cyn) * 0.86, top[i].z))]
        _oface(mb, q, M, (0, 0, 1))
    # the waistcoat's six buttons and the coat's own button at the waist
    for i in range(6):
        p = _torso_front(0.0, zc - 0.16 * k - i * (zc - 0.16 * k - zw - 0.05 * k) / 5, H, 0.005 * k)
        mb.sphere(tuple(p), 0.0105 * k, M, seg=8, rings=5, sz=0.7)
    p = _torso_front(0.0, zw + 0.012 * k, H, 0.02 * k)
    mb.sphere(tuple(p), 0.017 * k, M, seg=10, rings=6, sz=0.8)
    # the high collar with its turned points, the knot of the tie under them
    cy = J['neck'].y
    mb.cylinder((0, cy), 0.086 * k, zc - 0.02 * k, zc + 0.085 * k, M, seg=20, cap_top=False, r1=0.08 * k)
    for sx in (-1, 1):
        _oface(mb, [(sx * 0.006 * k, cy - 0.084 * k, zc + 0.07 * k), (sx * 0.055 * k, cy - 0.066 * k, zc + 0.015 * k),
                    (sx * 0.006 * k, cy - 0.09 * k, zc + 0.01 * k)], M, (0, -1, 0))
    t = _torso_front(0.0, zc - 0.02 * k, H, 0.0)
    mb.box((0, t.y - 0.008 * k, zc - 0.012 * k), (0.042 * k, 0.03 * k, 0.04 * k), M)
    # -- the skirt
    a, b, cy = _torso_at(zw, H)
    rx, ry = a + 0.016 * k, b + 0.018 * k
    z_hem = 0.27 * H                    # the backs of the knees (2011 photo, from the front: 0.27 of his height)
    rows = 9
    for sx in (-1, 1):                  # each tail from the front edge round to the vent at the back
        outer_, inner_ = [], []
        for j in range(rows + 1):
            t = j / rows
            z = zw + 0.03 * k - (zw + 0.03 * k - z_hem) * t
            open_ = math.radians(6 + 52 * min(1.0, t / 0.4) ** 0.75)       # the front cut away over the hips
            a0 = -math.pi / 2 + open_                                        # (front = -90 degrees)
            a1 = math.pi / 2 - math.radians(0.6 + 2.5 * max(0.0, t - 0.4))  # the vent opens below the hips
            o_row, i_row = [], []
            for kk in range(13):
                ang = a0 + (a1 - a0) * kk / 12
                flare = 1 + 0.3 * t ** 1.1 + 0.06 * t * max(0.0, math.sin(ang))
                c, s_ = math.cos(ang), math.sin(ang)
                x = sx * math.copysign(abs(c) ** (2 / UW_SE), c) * rx * flare
                y = cy + math.copysign(abs(s_) ** (2 / UW_SE), s_) * ry * flare + 0.05 * k * t * max(0.0, s_)
                zr = z + (0.03 * k * t * max(0.0, -s_) if j == rows else 0.0)
                o_row.append(Vector((x, y, zr)))
                i_row.append(Vector((x * 0.94, cy + (y - cy) * 0.92, zr)))
            outer_.append(o_row)
            inner_.append(i_row)
        tag = 'tail%d' % sx
        for j in range(rows):
            for kk in range(12):
                q = [outer_[j][kk], outer_[j + 1][kk], outer_[j + 1][kk + 1], outer_[j][kk + 1]]
                c = sum(q, Vector()) / 4
                _oface(mb, q, M, (c.x, c.y - cy, 0), smooth=tag)
                q = [inner_[j][kk], inner_[j + 1][kk], inner_[j + 1][kk + 1], inner_[j][kk + 1]]
                _oface(mb, q, M, (-c.x, cy - c.y, 0), smooth=tag + 'i')
        for kk in range(12):
            _oface(mb, [outer_[rows][kk], inner_[rows][kk], inner_[rows][kk + 1], outer_[rows][kk + 1]], M, (0, 0, -1))
        for kk in (0, 12):
            for j in range(rows):
                q = [outer_[j][kk], inner_[j][kk], inner_[j + 1][kk], outer_[j + 1][kk]]
                mid = (outer_[j][6] + inner_[j][6]) / 2
                _oface(mb, q, M, sum(q, Vector()) / 4 - mid)
    return mb, J


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
    # the bronze plate under his feet
    mb.box((0, 0.02, 3.8), (0.78, 0.7, 0.14), B)
    return mb


def underwood_statue():
    coat, J = underwood_coat()                   # soles at z = 0
    parts = [underwood_figure(), coat.build()]
    # head: scaled from life size so that it is H / 6.7 from the chin to the crown, the chin lifted a little
    head = underwood_head()
    vs = head.data.vertices
    zt, zb = max(v.co.z for v in vs), min(v.co.z for v in vs if abs(v.co.y + 0.07) < 0.03 and abs(v.co.x) < 0.02)
    k = (UW_H / 6.7) / (zt - zb)
    head = _decimate(head, 0.06)
    R = Matrix.Rotation(math.radians(-7), 4, 'X')
    nk = J['neck']
    head.data.transform(Matrix.Translation((0, nk.y - 0.012, UW_H - zt * k)) @ Matrix.Scale(k, 4) @ R)
    _set_material(head, 'bronze_patina')
    parts.append(head)
    # hands at the wrists, palm up (tilted a little in towards him)
    hk = 1.45
    for sx, (S, E, W) in J['arms'].items():
        h = _decimate(underwood_hand(sx), 0.07)
        d = (W - E).normalized()
        z = Vector((0, 0, 1))
        z = (z - d * z.dot(d)).normalized()
        z = Quaternion(d, math.radians(sx * 18)) @ z
        y = z.cross(d)
        Mh = Matrix((d, y, z)).transposed().to_4x4()
        h.data.transform(Matrix.Translation(W + d * 0.012) @ Mh @ Matrix.Scale(hk, 4))
        _set_material(h, 'bronze_patina')
        parts.append(h)
    for ob in parts:
        ob.data.transform(Matrix.Translation((0, 0, UW_PLATE)))      # onto the bronze plate
    return parts + [underwood_pedestal().build()]


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


def _airfoil(le, chord_dir, up, chord, th, n=8):
    """Closed ring of a thin wing section: leading edge `le`, chord along chord_dir, thickness along up."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        u = (1 - math.cos(a)) / 2                       # 0 at the leading edge, 1 at the trailing edge
        bulge = th * (1 - u) ** 0.7 * (0.35 + u) * 1.8
        pts.append(le + chord_dir * (chord * u) + up * (bulge * (1 if a < math.pi else -0.45)))
    return pts


def _feather(mb, base, d, n, L, w0, w1, mat, curl=0.0, th=0.022, segs=4):
    """One feather blade: from `base` along unit `d` for length L, its flat face across d × n, the shaft ridge
    on the n side; half-width w0 at the root to w1 before the rounded tip; the tip curls by `curl` along n."""
    side = d.cross(n).normalized()
    rings = []
    for j in range(segs + 1):
        t = j / segs
        c = base + d * (L * t) + n * (curl * t * t)
        w = (w0 + (w1 - w0) * t) * (1 - t ** 5) ** 0.5 + 0.004
        h = th * (1 - 0.6 * t)
        rings.append([c + side * w, c + n * h, c - side * w, c - n * h * 0.4])
    loft(mb, rings, mat, cap1=False)


def eagle_body():
    """Body, neck, head and the feathered legs as one skin-modifier tube, with the beak, tail and talons
    (eagle-local, about final size: front -Y, the talons at z = 0, beak to tail 2.4 m)."""
    head_turn = math.radians(-28)         # the head turned a little to its right and down (symbol page, 2009 photo)
    hr = Matrix.Rotation(head_turn, 3, 'Z')
    neck = Vector((0, -0.6, 1.02))
    V = [
        Vector((0, 0.66, 0.64)),           # 0 tail root
        Vector((0, 0.40, 0.68)),           # 1 rump
        Vector((0, 0.06, 0.74)),           # 2 belly
        Vector((0, -0.32, 0.84)),          # 3 chest
        neck,                              # 4 neck
        neck + hr @ Vector((0, -0.22, 0.1)),   # 5 head
        Vector((0.16, -0.08, 0.62)),       # 6 L thigh
        Vector((0.18, -0.16, 0.34)),       # 7 L feathered "trousers"
        Vector((0.18, -0.2, 0.15)),        # 8 L ankle
        Vector((-0.16, -0.08, 0.62)),      # 9 R thigh
        Vector((-0.18, -0.16, 0.34)),      # 10 R
        Vector((-0.18, -0.2, 0.15)),       # 11 R ankle
    ]
    E = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (2, 6), (6, 7), (7, 8), (2, 9), (9, 10), (10, 11)]
    R = [(0.2, 0.09), (0.38, 0.3), (0.46, 0.42), (0.46, 0.47), (0.27, 0.28), (0.2, 0.21),
         (0.24, 0.24), (0.17, 0.17), (0.07, 0.07), (0.24, 0.24), (0.17, 0.17), (0.07, 0.07)]
    body = _skin('eagle_body', V, E, R, root=2)
    mb = MeshBuilder('eagle_parts')
    M = 'bronze_patina'
    hd = V[5]
    fwd = hr @ Matrix.Rotation(math.radians(-12), 3, 'X') @ Vector((0, -1, 0))
    side = hr @ Vector((1, 0, 0))
    up = side.cross(fwd).normalized() * -1
    mb.sphere(tuple(hd + fwd * 0.02), 0.22, M, seg=14, rings=9, sz=0.86)          # the head
    mb.sphere(tuple(hd + fwd * 0.1 + up * 0.09), 0.17, M, seg=12, rings=6, sz=0.45)  # flat brow over the eyes
    # the big hooked beak: deep at the gape, hooking down at the tip
    rings = []
    for k in range(7):
        t = k / 6
        c = hd + fwd * (0.12 + 0.36 * t) + up * (-0.02 - 0.22 * t ** 2.2)
        w = 0.11 * (1 - t) ** 0.8 + 0.01
        h = 0.16 * (1 - t) + 0.014
        rings.append([c + side * w, c + up * (h * 0.7), c - side * w, c - up * (h * 0.55)])
    loft(mb, rings, M, cap0=False)
    # tail: a long fan of broad feathers, pointing back and down beyond the rock
    root = V[0] + Vector((0, -0.06, 0.0))
    for k in range(9):
        a = math.radians(-20 + k * 5)
        d = Vector((math.sin(a) * 0.5, math.cos(a), -0.3 - 0.12 * abs(k - 4) / 4)).normalized()
        nn = Vector((0, 0, 1))
        nn = (nn - d * nn.dot(d)).normalized()
        _feather(mb, root + nn * (0.014 * (k % 2)), d, nn, 1.0 - 0.1 * abs(k - 4) / 4, 0.1, 0.09, M, curl=-0.03, th=0.035)
    # under-tail coverts thicken the root of the fan into a wedge (side silhouette)
    for k in range(5):
        a = math.radians(-12 + k * 6)
        d = Vector((math.sin(a) * 0.5, math.cos(a), -0.62)).normalized()
        nn = (Vector((0, 0, 1)) - d * d.z).normalized()
        _feather(mb, root + Vector((0, -0.08, -0.04)), d, nn, 0.58, 0.1, 0.09, M, th=0.04)
    # talons gripping the rock: three forward toes and a hind toe on each foot
    for sx in (-1, 1):
        ank = Vector((0.17 * sx, -0.2, 0.16))
        for (dx, dy) in ((0.11 * sx, -0.22), (0.0, -0.26), (-0.09 * sx, -0.21), (0.02 * sx, 0.2)):
            rings = []
            for j in range(6):
                t = j / 5
                c = ank + Vector((dx * t * 0.8, dy * t * 0.8, -0.1 * t - 0.12 * t ** 3))
                r = 0.045 * (1 - t) + 0.008
                rings.append([c + Vector((r, 0, 0)), c + Vector((0, r, 0)), c + Vector((-r, 0, 0)), c + Vector((0, -r, 0))])
            loft(mb, rings, M, cap0=False)
    return body, mb


def eagle_wing(sx, length=3.0, elev=35.0):
    """One wing raised in the wide V (2009 photo, symbol page): the arm runs up and out from the shoulder with
    the broad feathered surface facing back and out, so it reads broad from the side (Flickr silhouette) and
    from below.  Leading-edge arm, a membrane, eleven secondaries with two rows of coverts, seven primaries
    fanned like fingers with tips curling up, and the primary coverts over their roots."""
    mb = MeshBuilder(f'eagle_wing_{sx}')
    M = 'bronze_patina'
    S = Vector((0.2 * sx, -0.26, 1.02))                     # shoulder
    a = math.radians(elev)
    s = Vector((sx * math.cos(a), 0.06, math.sin(a))).normalized()            # along the arm
    c = Vector((0.12 * sx, math.cos(math.radians(22)), -math.sin(math.radians(22))))
    c = (c - s * c.dot(s)).normalized()                                       # chord, leading -> trailing edge
    n = s.cross(c).normalized()
    if n.z < 0:
        n = -n                                                                # the upper surface
    arm = 0.5 * length                                       # shoulder -> wrist
    wrist = S + s * arm + c * 0.02
    hand_tip = wrist + s * 0.34 - c * 0.02
    # the arm: a thick leading edge, bowing forward a little at the wrist
    rings = []
    for k in range(9):
        t = k / 8
        p = S + s * (arm * t) - c * (0.06 * math.sin(t * math.pi)) + n * (0.03 * math.sin(t * math.pi))
        r = 0.13 * (1 - t) + 0.06
        rings.append([p - c * r, p + n * r * 0.8, p + c * r * 1.6, p - n * r * 0.6])
    for k in range(1, 5):
        t = k / 4
        p = wrist + (hand_tip - wrist) * t
        r = 0.06 * (1 - 0.5 * t)
        rings.append([p - c * r, p + n * r * 0.8, p + c * r * 1.6, p - n * r * 0.6])
    loft(mb, rings, M)
    # the membrane behind it, filling to the coverts
    rings = []
    for k in range(9):
        t = k / 8
        le = S + s * (arm * t) + c * 0.02
        rings.append(_airfoil(le, c, n, 0.86 - 0.3 * t, 0.08 * (1 - 0.4 * t), n=6))
    loft(mb, rings, M)
    # secondaries along the trailing edge, then the greater and median coverts over their roots
    rnd = random.Random(7 + sx)
    for row, (n_f, v0, L, w, lift) in enumerate(((15, 0.46, 0.9, 0.17, 0.0), (13, 0.26, 0.56, 0.15, 0.04),
                                                  (11, 0.08, 0.38, 0.12, 0.08))):
        for k in range(n_f):
            f = k / (n_f - 1)
            u = 0.12 + (arm - 0.16) * f
            base = S + s * u + c * v0 + n * (lift + 0.01 * (k % 2))
            d = (c + s * (0.2 * f - 0.06 + rnd.uniform(-0.04, 0.04))).normalized()
            Lk = L * (1 - 0.15 * f * (row == 0)) * rnd.uniform(0.94, 1.04)
            _feather(mb, base, d, n, Lk, w, w * 0.9, M, curl=-0.03, th=0.022)
    # under-wing coverts: from the ground the eagle is mostly seen from below
    for n_f, v0, L, w, drop in ((13, 0.24, 0.52, 0.15, 0.05), (11, 0.06, 0.36, 0.12, 0.09)):
        for k in range(n_f):
            f = k / (n_f - 1)
            u = 0.14 + (arm - 0.2) * f
            base = S + s * u + c * v0 - n * (drop + 0.01 * (k % 2))
            d = (c + s * (0.2 * f - 0.06 + rnd.uniform(-0.04, 0.04))).normalized()
            _feather(mb, base, d, -n, L * rnd.uniform(0.94, 1.04), w, w * 0.9, M, curl=0.02, th=0.02)
    # primaries: long separate feathers fanning from the hand, the outer ones nearly along the arm
    for i in range(7):
        f = i / 6
        base = hand_tip + (wrist - hand_tip) * f + c * (0.06 + 0.04 * f)
        ang = math.radians(4 + 48 * f)
        d = (s * math.cos(ang) + c * math.sin(ang)).normalized()
        L = (1.18, 1.36, 1.42, 1.38, 1.28, 1.12, 0.96)[i]
        _feather(mb, base + n * (0.014 * (i % 2)), d, n, L, 0.155, 0.085, M, curl=0.16 - 0.08 * f, th=0.026)
    # primary coverts over their roots
    for i in range(6):
        f = i / 5
        base = hand_tip + (wrist - hand_tip) * f + c * 0.02 + n * 0.04
        ang = math.radians(8 + 48 * f)
        d = (s * math.cos(ang) + c * math.sin(ang)).normalized()
        _feather(mb, base, d, n, 0.4, 0.09, 0.08, M, th=0.02)
    return mb


def eagle_rock():
    """The rough bronze rock the eagle grips, on the column's cap (dark with the eagle in the 1971 and 2009 photos)."""
    rnd = random.Random(70)
    mb = MeshBuilder('eagle_rock')
    seg, rings_n = 14, 6
    P = []
    for j in range(rings_n + 1):
        th = math.pi / 2 * j / rings_n                     # base ring -> top
        row = []
        for i in range(seg):
            ph = 2 * math.pi * i / seg
            r = 1 + rnd.uniform(-0.16, 0.16) * math.sin(th * 2 + 0.3)
            row.append(Vector((0.62 * r * math.cos(th) * math.cos(ph), 0.55 * r * math.cos(th) * math.sin(ph),
                               0.5 * math.sin(th) * (1 + rnd.uniform(-0.12, 0.12)))))
        P.append(row)
    for j in range(rings_n):
        for i in range(seg):
            k = (i + 1) % seg
            mb.face([P[j][i], P[j][k], P[j + 1][k], P[j + 1][i]], 'bronze_patina', smooth='rock')
    return mb


def eagle_figure(width=5.2):
    """The bronze eagle, feet at z=0, facing -Y, scaled to the published 5.2 m width."""
    body, parts = eagle_body()
    objs = [body, parts.build(), eagle_wing(1).build(), eagle_wing(-1).build()]
    ob = _join(objs, 'eagle')
    bb = [Vector(c) for c in ob.bound_box]
    w = max(v.x for v in bb) - min(v.x for v in bb)
    zmin = min(v.z for v in bb)
    s = width / w
    for v in ob.data.vertices:
        v.co = Vector((v.co.x * s, v.co.y * s, (v.co.z - zmin) * s))
    _set_material(ob, 'bronze_patina')
    return ob


# The four groups of white figures (the "Yonseians"; the university's symbol page: 「네 귀퉁이에는 … 연세인의 형상이
# 조각되어 있습니다」) stand on the dais' diagonals, 3.7 m out (Kakao roadview 2008-08, 2010-12 and 2011-04 from six
# points round it, the groups triangulated; the same four were set on granite wedges by the rebuilt 백양로, 2024 photo).
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
    for i in range(len(poly)):
        j = (i + 1) % len(poly)
        mb.face([(*poly[i], -0.05), (*poly[j], -0.05), (*poly[j], zt[j]), (*poly[i], zt[i])], W)
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
    prof.append((z1, 0.31))
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
    rock = eagle_rock().build()
    rock.data.transform(Matrix.Translation((0, 0, top - 0.04)))
    eagle = eagle_figure()
    eagle.location.z = top + 0.3
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    eagle.select_set(True)
    bpy.context.view_layer.objects.active = eagle
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    out = [tower.build(), rock, eagle, eagle_kerbs(site).build()]
    # the four groups at the diagonals, facing out: A south-west, B north-west, C south-east, D north-east (the statue
    # faces -y, south-south-west; +x is east-south-east, towards 백양로)
    zd = site['dais'][1]
    for k, (deg, yaw) in enumerate(((-135, 0), (135, 0), (-45, 0), (45, 0))):
        a = math.radians(deg)
        g = yonseian_group(k).build()
        r = 3.7
        g.matrix_world = Matrix.Translation((r * math.cos(a), r * math.sin(a), zd)) @ \
            Matrix.Rotation(a + math.pi / 2 + math.radians(yaw), 4, 'Z')
        bpy.context.view_layer.update()
        out.append(g)
    return out
