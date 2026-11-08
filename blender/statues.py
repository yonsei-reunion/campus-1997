"""Bronze statues of the 1997 campus, modelled from photographs.

언더우드 동상 (Horace G. Underwood, at the entrance of the Underwood courtyard; photos: Wikimedia Commons
"Horace_Grant_Underwood_statue_in_Yonsei_Univ_main_campus.jpg", "Underwood_statue.JPG"): a man in a morning coat with
tails and a buttoned waistcoat, both arms held out in front of him, palms up, on a bronze plate on a tapering light
granite pedestal with a moulded cap, a bronze plaque on the front and a broad base.  The figure is the CC0 Quaternius
"Ultimate Modular Men" Suit character, posed and frozen in bronze.

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
def _rotate_bone_to(arm, pb, target):
    """Turn a pose bone about its head so its axis points along `target`, a world direction (Blender Z-up;
    the imported glTF armature itself is rotated from Y-up, so convert into armature space first)."""
    bpy.context.view_layer.update()
    M = pb.matrix.copy()
    cur = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    want = (arm.matrix_world.to_3x3().inverted() @ target).normalized()
    q = cur.rotation_difference(want)
    h = M.translation.copy()
    pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ M
    bpy.context.view_layer.update()


def _twist_bone(pb, deg):
    """Roll a pose bone about its own axis."""
    bpy.context.view_layer.update()
    M = pb.matrix.copy()
    ax = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    h = M.translation.copy()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, ax) @ Matrix.Translation(-h) @ M
    bpy.context.view_layer.update()


def underwood_figure(height=2.45):
    """The posed Quaternius Suit man as one bronze mesh, feet at z=0, facing -Y."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SUIT, merge_vertices=True, import_shading='SMOOTH')
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE')
    meshes = [o for o in new if o.type == 'MESH' and o.name.startswith('Suit_')]
    # start from the relaxed idle pose, then hold the arms out in welcome (both photos)
    arm.animation_data_create()
    arm.animation_data.action = bpy.data.actions.get('Idle_Neutral')
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    basis = {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones}
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis = basis[pb.name]
    bpy.context.view_layer.update()
    # armature space: the character faces -Y, its left (.L) is +X
    for side, sx in (('L', 1), ('R', -1)):
        P = arm.pose.bones
        _rotate_bone_to(arm, P['UpperArm.' + side], Vector((0.34 * sx, -0.42, -0.84)))
        _rotate_bone_to(arm, P['LowerArm.' + side], Vector((0.36 * sx, -0.93, 0.04)))
        _rotate_bone_to(arm, P['Wrist.' + side], Vector((0.34 * sx, -0.93, 0.1)))
        _twist_bone(P['LowerArm.' + side], -70 * sx)          # palms turned up
        # open hands: straighten the fingers a little
        for f in ('Index', 'Middle', 'Ring', 'Pinky'):
            for k in (1, 2, 3):
                b = P.get(f'{f}{k}.{side}')
                if b:
                    b.matrix_basis = Matrix.Identity(4)
    # a slight lift of the chin, as in the photos
    _twist_bone(arm.pose.bones['Neck'], 0)
    baked = []
    for m in meshes:
        b = _bake(m)
        b.matrix_world = m.matrix_world.copy()
        baked.append(b)
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    ob = _join(baked, 'underwood_figure')
    # normalise: feet on z=0, centred, scaled to the statue's height
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    z0, z1 = min(v.z for v in bb), max(v.z for v in bb)
    cx = (min(v.x for v in bb) + max(v.x for v in bb)) / 2
    s = height / (z1 - z0)
    me = ob.data
    feet_y = 0.0
    for v in me.vertices:
        z = (v.co.z - z0) / (z1 - z0)
        fat = 1.0 + 0.16 * math.exp(-((z - 0.55) / 0.2) ** 2)     # fuller chest and waist under the coat
        p = Vector(((v.co.x - cx) * fat, v.co.y * fat, v.co.z - z0))
        if z > 0.84:                                              # a smaller head: an adult, not the stylised youth
            pivot = Vector((0, 0, 0.84 * (z1 - z0)))
            p = pivot + (p - pivot) * 0.84
        v.co = p * s
    _set_material(ob, 'bronze_patina')
    return ob, s


def underwood_coat(fig, H):
    """The skirt of the morning coat: open in front, cut away over the hips, hanging to the backs of the knees.
    Sized from the figure's own hips so it sits on the body."""
    vs = [v.co for v in fig.data.vertices]
    def extent(z0, z1):
        band = [v for v in vs if z0 * H < v.z < z1 * H and abs(v.x) < 0.3 * H / 2.45]
        return (max(abs(v.x) for v in band), min(v.y for v in band), max(v.y for v in band))
    hx, hy0, hy1 = extent(0.5, 0.56)
    cy = (hy0 + hy1) / 2
    rx, ry = hx + 0.02, (hy1 - hy0) / 2 + 0.03
    mb = MeshBuilder('underwood_coat')
    mat = 'bronze_patina'
    zw = 0.585 * H                                        # waist seam
    # angle 0 = +X (his left), 90 = +Y (back), 270 = -Y (front); the front is open between 240 and 300 degrees
    angs = [math.radians(a) for a in [300 + k * 300 / 24 for k in range(25)]]
    def hem(a):
        back = max(0.0, math.cos(a - math.pi / 2))        # 1 at the back, 0 at the sides and front
        return 0.42 * H - 0.15 * H * back ** 0.6           # sides cut away higher, tails to the knees
    rows = 6
    outer, inner = [], []
    for j in range(rows + 1):
        t = j / rows
        o_row, i_row = [], []
        for a in angs:
            z = zw + (hem(a) - zw) * t
            flare = 1 + 0.32 * t
            x = math.cos(a) * rx * flare
            y = cy + math.sin(a) * ry * flare + 0.04 * t * max(0, math.sin(a))
            o_row.append(Vector((x, y, z)))
            i_row.append(Vector((x * 0.93, cy + (y - cy) * 0.9, z)))
        outer.append(o_row)
        inner.append(i_row)
    n = len(angs)
    for j in range(rows):
        for k in range(n - 1):
            mb.face([outer[j][k], outer[j + 1][k], outer[j + 1][k + 1], outer[j][k + 1]], mat, smooth='coat_o')
            mb.face([inner[j][k + 1], inner[j + 1][k + 1], inner[j + 1][k], inner[j][k]], mat, smooth='coat_i')
    for k in range(n - 1):                                 # hem edge
        mb.face([outer[rows][k], inner[rows][k], inner[rows][k + 1], outer[rows][k + 1]], mat)
    for k in (0, n - 1):                                   # front edges
        for j in range(rows):
            q = [outer[j][k], inner[j][k], inner[j + 1][k], outer[j + 1][k]]
            mb.face(q if k == 0 else q[::-1], mat)
    # the back vent between the two tails
    mb.face([Vector((0, cy + ry * 1.3, hem(math.pi / 2) - 0.01)), Vector((0.01, cy + ry * 1.32, zw - 0.25 * (zw - hem(math.pi / 2)))),
             Vector((-0.01, cy + ry * 1.32, zw - 0.25 * (zw - hem(math.pi / 2))))], mat)
    return mb


def underwood_pedestal():
    """Granite pedestal: broad base, tapering shaft with a bronze plaque, moulded cap; round steps around it."""
    mb = MeshBuilder('underwood_pedestal')
    G, Gd = 'granite_light', 'stone_granite'
    # two low round steps (the courtyard entrance)
    mb.cylinder((0, 0), 3.4, -0.6, 0.14, G, seg=48, smooth=False)
    mb.cylinder((0, 0), 2.7, 0.14, 0.28, G, seg=48, smooth=False)
    mb.box((0, 0, 0.28 + 0.3), (2.3, 2.3, 0.6), G)                  # base block
    mb.box((0, 0, 0.88 + 0.1), (2.0, 2.0, 0.2), G)                  # base moulding
    # tapering shaft 1.7 -> 1.5 m
    z0, z1, w0, w1 = 1.08, 3.0, 0.85, 0.75
    c0 = [(-w0, -w0), (w0, -w0), (w0, w0), (-w0, w0)]
    c1 = [(-w1, -w1), (w1, -w1), (w1, w1), (-w1, w1)]
    for i in range(4):
        a0, b0, a1, b1 = c0[i], c0[(i + 1) % 4], c1[i], c1[(i + 1) % 4]
        mb.face([(a0[0], a0[1], z0), (b0[0], b0[1], z0), (b1[0], b1[1], z1), (a1[0], a1[1], z1)], G)
    mb.box((0, 0, 3.06), (1.66, 1.66, 0.12), G)                     # neck band
    mb.box((0, 0, 3.27), (2.02, 2.02, 0.3), G)                      # cornice
    mb.box((0, 0, 3.47), (1.8, 1.8, 0.1), G)
    # bronze plate under the feet and the plaque on the front (-Y)
    mb.box((0, 0, 3.58), (1.0, 0.82, 0.12), 'bronze_patina')
    y = -(w0 + (w1 - w0) * 0.45) - 0.03
    mb.box((0, y, 2.0), (0.8, 0.05, 1.05), 'bronze_patina')
    return mb


def underwood_statue():
    fig, s = underwood_figure()                 # feet at z = 0
    coat = underwood_coat(fig, 2.45).build()    # measured on the figure at ground level
    for ob in (fig, coat):
        ob.data.transform(Matrix.Translation((0, 0, 3.64)))     # onto the bronze plate on the pedestal
    return [fig, coat, underwood_pedestal().build()]


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


def _ellipsoid(co, x, y, z, hx, hy, hz):
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
            out.append(_ellipsoid(J[a] + e * (L * t), x, y, e, rx, ry, max(rx, ry, L / (n - 1))))
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
        out.append(_ellipsoid(p, s, nv, d, sw[k] * taper, th / 2, max(0.07, 0.6 * sw[k] * taper)))
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
