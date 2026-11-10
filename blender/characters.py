"""1997 Yonsei students, professors and staff from Quaternius' CC0 modular character packs.

Adapted from the user's sim-office project (tools/office-characters.py). Same build: parts of several outfits on
the shared 62-bone 'CharacterArmature', recoloured, fingers relaxed, scale baked in; animation clips live in two
shared rig files (rig-umc, rig-women) and every person only carries its skinned mesh.  The heads are made over here
(see '1997 heads'): the pack's face softened, hair of the late 1990s grown on the skull, and the eyes, brows and mouth
a few drawn lines (blender/faces.py: one atlas for everybody, the faces laid on its cells).

    blender -b --factory-startup --python blender/characters.py               # every person, both rigs, the faces
    blender -b --factory-startup --python blender/characters.py -- men rigs   # only these ('men', 'women', 'rigs', ids)
    blender -b --factory-startup --python blender/characters.py -- faces      # only the atlas of the faces
    blender -b --factory-startup --python blender/characters.py -- --list

Sources (CC0, quaternius.com), copied to assets_src/quaternius/:
- ultimate-modular-characters/<Outfit>.gltf  "Ultimate Modular Men"  https://quaternius.com/packs/ultimatemodularmen.html
- ultimate-modular-women/<Outfit>.glb        "Ultimate Modular Women" https://quaternius.com/packs/ultimatemodularwomen.html
  (the women are the pack's FBX converted by poly.pizza; normalize_fbx() undoes the converter's scale and timing)

Output: web/public/assets/models/people/<id>.glb  (feet at y=0, facing +Z, real-world height in metres,
colour materials only, texture coordinates into faces.png), faces.png, and rig-umc.glb / rig-women.glb with the
clips idle walk sprint sit emote-yes emote-no interact-right and glTF extras walk_speed / run_speed (m/s of the feet
in the walk / run cycle).
"""
import base64
import json
import math
import os
import struct
import sys
import tempfile

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import faces  # noqa: E402
from faces import FACE  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
UMC = os.path.join(ROOT, 'assets_src', 'quaternius', 'ultimate-modular-characters')
WOMEN = os.path.join(ROOT, 'assets_src', 'quaternius', 'ultimate-modular-women')
OUT = os.path.join(ROOT, 'web', 'public', 'assets', 'models', 'people')

SRC = {'umc': (UMC, '.gltf'), 'women': (WOMEN, '.glb')}     # rig -> source folder and file type
HEIGHT = {'umc': 1.73, 'women': 1.61}      # metres: 1997 Korean students (top of the hair)
TOP = {'umc': 1.856, 'women': 1.797}       # top of the hair in the source (Suit / Casual head, Blender units); the
#                                            hair grown here ends within 1.5 cm of it (shorter cuts lower)
FBX_FPS = 24 / 30                          # women: the FBX2glTF keys' time scale (see normalize_fbx)
SEAT = 0.24                              # seat height of the Kenney chairs and benches (chair, chairDesk, bench)
HIP_OVER_SEAT = 0.05                     # hip joint above the seat when sitting
LIMIT = {'person': 400 * 1024, 'rig': 400 * 1024}   # base64 bytes

# engine clip name -> source action (None: made here)
CLIPS = {
    'umc': {'idle': 'Idle_Neutral', 'walk': 'Walk', 'sprint': 'Run', 'sit': None, 'emote-yes': 'Wave', 'emote-no': None,
            'interact-right': 'Interact'},
    'women': {'idle': 'Idle_Neutral', 'walk': 'Walk', 'sprint': 'Run', 'sit': None, 'emote-yes': 'Wave', 'emote-no': None,
              'interact-right': 'Interact'},
}
RIG_SOURCE = {'rig-umc': 'Suit', 'rig-women': 'Casual'}     # the outfit file whose animations make the rig

# ---------- the people ----------
# colours are sRGB hex. A key 'Mat' recolours that material everywhere, 'part:Mat' only on that part (head, body, legs, feet).
SKIN = {'a': '#f0c9a4', 'b': '#e6b991', 'c': '#d9a77d', 'd': '#c99168',         # East Asian skin tones
        'fair': '#f7ddc8', 'tan': '#b9825a'}                                    # and one fair, one tanned (가무잡잡)
HAIR = {'black': '#141110', 'dark': '#2b1f18', 'brown': '#5a3a24', 'dyed': '#7a4a26', 'grey': '#8e8b88'}
JEANS = {'mid': '#46638f', 'dark': '#2b3c5c', 'light': '#7f9cc0', 'stone': '#8fa8c8'}     # 1997: stone-washed denim
HEAD_BASE = {'umc': 'Worker', 'women': 'Adventurer'}      # the heads with a whole skull (see '1997 heads' below)


def man(hair, body, legs, feet, colors=None, note='', **more):
    return dict({'rig': 'umc', 'hair': hair, 'parts': {'head': HEAD_BASE['umc'], 'body': body, 'legs': legs, 'feet': feet},
                 'colors': colors or {}, 'note': note}, **more)


def woman(hair, body, legs, feet, colors=None, note='', **more):
    return dict({'rig': 'women', 'hair': hair, 'parts': {'head': HEAD_BASE['women'], 'body': body, 'legs': legs, 'feet': feet},
                 'colors': colors or {}, 'note': note}, **more)


def bands(to, of, zs, **box):
    """Stripes for `paint` (see '1997 wardrobe' below): one box a band (z from, to)."""
    return [dict(of=of, to=to, z=z, **box) for z in zs]


# 1997 campus fashion (reference/고증 4.11): baggy stone-washed jeans and wide trousers, big tees and hoodies, a collared
# tee in broad stripes, a jumper with a dark collar, a blazer over cotton trousers, the Yonsei-blue cheer jacket, a white
# knit over a black skirt, a cropped tee, a pastel cardigan, a professor in a grey suit, staff in work vests.
# Hair (the first name, see HAIR_STYLES) and faces as students wore and had them about 1997 (reference/고증 4.9): most
# of them plain, a few the cuts of the year.  Optional: flip (the parting on the other side), bridge (bleached locks:
# [(azimuth, half width)]), face: what makes the one shared face a person's own.  Of the skull: jaw, chin (scales).
# Of the drawn lines (faces.py): lid (mono 홑꺼풀, inner 속쌍꺼풀, double 쌍꺼풀), slant (the outer corner of the eye
# higher, of the eye's half width), eye, brow, mouth, lash, lip (scales), brow_tilt (the tail higher), arch (of the
# brow, a scale), smile (the corners of the mouth up, m), age ('mid', 'old': the lines of an older face).  glasses:
# who wears them as the model is (everybody has a pair: the game shows or hides it, web/src/characters.js).  Of the
# brows also brow_len, brow_gap, brow_up, brow_peak, brow_corner, brow_drop, brow_taper, brow_soft (faces.py), of the
# nose nose, bridge, nose_curve, nose_w, nose_up (NOSE below).  paint: parts of the outfit in colours of their own
# (see '1997 wardrobe').
PEOPLE = {
    'man-tee': man('curtain', 'Casual_2', 'Casual_2', 'Casual_2',
                   {'LightBrown': '#f1efe8', 'LightBlue': JEANS['stone'], 'Red_Dark': '#e8e6e0', 'feet:White': '#c9c6be',
                    'Skin': SKIN['b'], 'Hair': HAIR['black']},
                   'big white tee, baggy stone-washed jeans, white sneakers; long fringe parted in the middle',
                   face=dict(lid='inner', slant=.05, jaw=.97, brow=.9, brow_tilt=-.05, arch=.9, brow_len=.93, brow_soft=2.2,
                             smile=.0022, nose=.90, bridge=.28,
                             nose_w=.98)),
    'man-check': man('short', 'Casual_2', 'Casual_2', 'Casual_2',
                     {'LightBrown': '#1f2f55', 'Stripe': '#1f8580', 'Stripe2': '#d8742c', 'Collar': '#ece8dc',
                      'LightBlue': JEANS['dark'], 'Red_Dark': '#3a2c24', 'Skin': SKIN['c'], 'Hair': HAIR['black']},
                     'collared tee in broad navy, teal and orange stripes, wide dark jeans; neat short hair, metal glasses',
                     paint={'body': bands('Stripe', ('LightBrown',), [(1.085, 1.150), (1.280, 1.345)], x=(0, .21))
                            + bands('Stripe2', ('LightBrown',), [(1.185, 1.245), (1.380, 1.440)], x=(0, .21))
                            + [dict(of=('LightBrown',), to='Collar', x=(0, .10), z=(1.495, None))]},
                     face=dict(lid='mono', slant=.10, jaw=1.04, eye=.96, smile=.0016, mouth=.96, glasses=True, brow=1.3, arch=.4,
                               brow_len=.86, brow_taper=1.6, nose=.84, bridge=.24, nose_w=1.10)),
    'man-hoodie': man('up', 'Casual_Hoodie', 'Casual_2', 'Casual_Hoodie',
                      {'Purple': '#23345e', 'LightBlue': '#a8946a', 'feet:White': '#e8e6e0', 'Skin': SKIN['tan'],
                       'Hair': HAIR['black'], 'Brow': '#0e0b0a'}, 'oversized navy hoodie, wide khaki cargo trousers; short hair swept up and back, tanned',
                      face=dict(lid='mono', slant=.14, jaw=.97, eye=.98, smile=.0027, mouth=1.08, brow=1.5, brow_tilt=.09,
                                brow_corner=True, brow_peak=.70, brow_drop=1.2, brow_taper=1.3, brow_soft=1.4, nose=1.04,
                                bridge=.40, nose_curve=1.3)),
    'man-cheer': man('sweep-73', 'Casual_Hoodie', 'Casual_2', 'Casual_2',
                     {'Purple': '#1d3fa0', 'LightBlue': JEANS['mid'], 'Red_Dark': '#f2f2ee', 'Skin': SKIN['c'],
                      'Hair': HAIR['black']}, 'Yonsei-blue cheer jacket, jeans; a long fringe swept from a 7:3 parting',
                     face=dict(lid='double', slant=.04, jaw=1.02, eye=1.05, mouth=1.1, smile=.0032, brow=1.4, arch=1.7,
                               brow_len=1.06, brow_peak=.55, nose=.96, bridge=.30, nose_w=1.08, nose_up=.0015)),
    'man-grey': man('curtain-64', 'Casual_Hoodie', 'Casual_2', 'Casual_Hoodie',
                    {'Purple': '#e8e0b0', 'Collar': '#3b3a3c', 'LightBlue': JEANS['mid'],
                     'feet:Purple': '#2a2a2e', 'Skin': SKIN['b'], 'Hair': HAIR['dyed'], 'Brow': '#1c1410'},
                    'pale yellow jumper with a dark collar, jeans; brown-dyed hair parted 6:4',
                    paint={'body': [dict(of=('Purple',), to='Collar', x=(0, .10), z=(1.495, None))]},
                    face=dict(lid='inner', slant=.10, jaw=.97, smile=.0012, mouth=.98, lip=1.35, brow=1.55, arch=.5, brow_tilt=.04,
                              brow_taper=1.7, brow_len=1.05, brow_gap=-.001, brow_up=-.001, nose=1.10, bridge=.42,
                              nose_curve=1.2, nose_w=1.04)),
    'man-blazer': man('part-side', 'Suit', 'Casual_2', 'Suit',
                      {'Suit': '#27304a', 'White': '#dfe7ee', 'Tie': '#dfe7ee', 'LightBlue': '#b9a67e', 'Black': '#3a2a1f',
                       'Skin': SKIN['a'], 'Hair': HAIR['black']},
                      'navy blazer, light blue shirt, beige cotton trousers (콤비); 2:8 side parting, the fringe swept across',
                      flip=True,
                      face=dict(lid='inner', slant=.02, jaw=.95, brow_tilt=-.05, arch=1.1, smile=.0018, brow=.8, brow_len=1.12, brow_gap=.002, brow_taper=.8,
                                nose=.98, bridge=.36, nose_w=.92)),
    'man-professor': man('thin', 'Suit', 'Suit', 'Suit',
                         {'Suit': '#55595f', 'Tie': '#2f4a7a', 'White': '#eceae4', 'Skin': SKIN['c'], 'Hair': HAIR['grey'],
                          'Brow': '#5a5652'}, 'grey suit, blue tie, thinning grey hair, glasses',
                         face=dict(lid='inner', slant=-.02, jaw=1.05, eye=.93, brow=1.05, brow_tilt=-.06, smile=.0010, age='old',
                                   glasses=True, brow_drop=1.3, brow_soft=2.4, brow_ink=.9, nose=1.0, bridge=.34, nose_w=1.12,
                                   nose_up=-.0015)),
    'man-staff': man('crop', 'Worker', 'Suit', 'Worker',
                     {'Worker_Vest': '#3d4f6a', 'Worker_Yellow': '#c9c3b2', 'LightBrown': '#c9c3b2', 'Suit': '#3a3f47',
                      'Skin': SKIN['d'], 'Hair': HAIR['dark']}, 'campus staff: navy vest, grey trousers',
                     face=dict(lid='mono', slant=.06, jaw=1.07, eye=.95, arch=.7, smile=.0012, age='mid', brow=1.4, brow_len=.92,
                               brow_taper=1.4, nose=.88, bridge=.26, nose_w=1.14)),
    'woman-tee': woman('long', 'Casual', 'Casual', 'Casual',
                       {'White': '#f4f1e8', 'Orange': JEANS['stone'], 'Grey': '#e8e6e0', 'Skin': SKIN['a'], 'Hair': HAIR['black']},
                       'loose white tee, wide stone-washed jeans, long straight black hair',
                       face=dict(lid='inner', slant=.07, eye=1.03, jaw=1.03, smile=.0030, brow=.9, arch=1.35, brow_peak=.58, brow_len=1.05, brow_up=-.002, brow_soft=1.3,
                                 nose=.80, bridge=.28, nose_w=.96, nose_up=.001)),
    'woman-pink': woman('tuck', 'Casual', 'Casual', 'Casual',
                        {'White': '#e7a7b6', 'Orange': '#cdb994', 'Grey': '#f0eee8', 'Skin': SKIN['fair'], 'Hair': HAIR['dark']},
                        'pink knit, wide beige trousers; short bob, one side behind the ear',
                        face=dict(lid='inner', slant=.03, jaw=1.04, brow_tilt=-.04, smile=.0030, mouth=.96, brow=1.25, arch=.4, brow_len=.88, brow_taper=1.5,
                                  nose=.72, bridge=.24, nose_w=1.02, nose_up=.002)),
    'woman-dress': woman('tied', 'Formal', 'Formal', 'Formal',
                         {'LimeGreen': '#f1ede1', 'Skirt': '#1f1f24', 'feet:Red': '#1c1c1f', 'Skin': SKIN['a'],
                          'Hair': HAIR['black']},
                         'white knit with long sleeves, black skirt, black shoes; black hair tied back',
                         paint={'body': [dict(of=('Skin',), to='LimeGreen', x=(.10, .585)),
                                         dict(of=('Skin',), to='LimeGreen', x=(0, .10), z=(None, 1.49)),
                                         dict(of=('Skin',), to='LimeGreen', x=(.05, .10)),
                                         dict(of=('Gold',), to='Skirt')],
                                'legs': [dict(of=('LimeGreen',), to='Skirt')]}, face=dict(lid='mono', slant=.10, jaw=.96, brow_tilt=.02, smile=.0024, brow=.85,
                                                                              arch=.5, brow_len=1.1, brow_taper=.8, brow_soft=1.3, nose=.90, bridge=.38, nose_w=.90)),
    'woman-dress-blue': woman('shoulder', 'Punk', 'Casual', 'Casual',
                              {'Pink': '#a9c6e6', 'Orange': JEANS['dark'], 'Grey': '#1f1f24', 'Skin': SKIN['b'],
                               'Hair': HAIR['brown'], 'Bridge': '#9c6c3a', 'Brow': HAIR['dark']},
                              'tight sky-blue cropped tee (배꼽티), wide dark jeans; brown-dyed hair to the shoulders, bleached locks',
                              bridge=[(-18, 3.5), (46, 3.5)],
                              paint={'body': [dict(of=('Pink',), to='Skin', z=(None, 1.20)),
                                              dict(of=('Black',), to='Skin', x=(.30, None)),
                                              dict(of=('Black',), to='Skin', x=(0, .09), z=(1.47, None)),
                                              dict(of=('Black',), to='Pink')]},
                              face=dict(lid='double', slant=.10, eye=.99, jaw=.98, smile=.0022, brow=.85, arch=1.6, brow_tilt=.05, brow_up=-.0015, brow_corner=True,
                                        brow_peak=.68, brow_drop=1.0, brow_soft=1.3, nose=.84, bridge=.32, nose_w=.95)),
    'woman-cardigan': woman('pixie', 'Suit', 'Casual', 'Casual',
                            {'Black': '#ecdf9e', 'White': '#f2efe6', 'Orange': JEANS['mid'], 'Grey': '#f0eee8', 'Skin': SKIN['c'],
                             'Hair': HAIR['black']}, 'pastel yellow cardigan over a white tee, jeans, short cut, metal glasses',
                            face=dict(lid='inner', slant=.05, jaw=1.03, smile=.0024, glasses=True, brow=1.5, arch=.8, brow_taper=1.4, brow_soft=2.2,
                                      nose=.76, bridge=.28, nose_w=1.08)),
    'woman-staff': woman('perm', 'Suit', 'Suit', 'Suit',
                         {'Black': '#2f3644', 'White': '#eef0f2', 'Skin': SKIN['b'], 'Hair': HAIR['dark']},
                         'office staff: navy suit, short permed hair', face=dict(lid='inner', slant=.0, jaw=1.06, eye=.95, brow_tilt=-.03, smile=.0014, age='mid',
                                                                                 brow=.9, arch=1.25, brow_len=.96, brow_soft=1.4, nose=.84, bridge=.30, nose_w=1.10)),
}
RIGS = {'rig-umc': 'umc', 'rig-women': 'women'}
PART_MESH = {'head': '_Head', 'body': '_Body', 'legs': '_Legs', 'feet': '_Feet'}
MESH_PREFIX = {'Casual_2': 'Casual2', 'Casual_Hoodie': 'Casual'}                        # file -> mesh name prefix
MESH_NAME = {('umc', 'Farmer', 'legs'): 'Farmer_Pants', ('women', 'Formal', 'head'): 'Formad_Head'}


# ---------- Blender helpers ----------

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def srgb_to_linear(h):
    h = h.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out + [1.0]


def principled(mat):
    return next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if mat and mat.use_nodes else None


def base_color(mat):
    b = principled(mat)
    return list(b.inputs['Base Color'].default_value) if b else list(mat.diffuse_color)


def colour_material(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = principled(m)
    if b is None:
        m.node_tree.nodes.clear()
        b = m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        o = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
        m.node_tree.links.new(b.outputs[0], o.inputs[0])
    for n in list(m.node_tree.nodes):          # a plain colour: drop any texture or colour ramp feeding the BSDF
        if n.type not in ('BSDF_PRINCIPLED', 'OUTPUT_MATERIAL'):
            m.node_tree.nodes.remove(n)
    b.inputs['Base Color'].default_value = rgba
    b.inputs['Roughness'].default_value = 0.9
    b.inputs['Metallic'].default_value = 0.0
    m.diffuse_color = rgba
    return m


MADE = {}      # material name -> the clean colour material made for the person being built


def recolour(ob, part, colors):
    """Give every slot of `ob` a clean colour material named after the source material (Skin, Hair, ...), recoloured
    by colors['part:Mat'] or colors['Mat']. A part-specific colour gets its own material 'Mat-part'."""
    for slot in ob.material_slots:
        src = slot.material
        if not src:
            continue
        base = src.name.split('.')[0]
        key = f'{part}:{base}'
        name = f'{base}-{part}' if key in colors else base
        if name not in MADE:
            rgba = srgb_to_linear(colors[key] if key in colors else colors[base]) if (key in colors or base in colors) else base_color(src)
            MADE[name] = colour_material(name + '~new', rgba)
        slot.material = MADE[name]
    return ob


def tidy_materials():
    made = set(MADE.values())
    for m in list(bpy.data.materials):
        if m not in made:
            bpy.data.materials.remove(m)
    for m in list(bpy.data.materials):
        if m.name.endswith('~new'):
            m.name = m.name[:-4]
    MADE.clear()


def import_gltf(path):
    if not os.path.exists(path):
        raise SystemExit(f'missing source {path}')
    before = set(bpy.data.objects)
    acts = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path, merge_vertices=True, import_shading='SMOOTH')
    objs = [o for o in bpy.data.objects if o not in before]
    if path.endswith('.glb'):
        objs = normalize_fbx(objs, [a for a in bpy.data.actions if a not in acts])
    return objs


def import_outfit(rig, outfit):
    folder, ext = SRC[rig]
    return import_gltf(os.path.join(folder, outfit + ext))


def normalize_fbx(objs, actions):
    """An FBX2glTF file (the women) as if Quaternius had exported it: the armature at the origin at scale 1 (the RootNode's
    scale of 100 baked into the bones, the mesh and the location keys), the parts its children, the helper empties gone,
    the actions named as in the men's files and their keys at the source's speed (times x 24/30)."""
    arm = next(o for o in objs if o.type == 'ARMATURE')
    meshes = [o for o in objs if o.type == 'MESH' and o.parent is arm]
    M = arm.matrix_world.copy()
    sc = M.to_scale()
    if max(sc) - min(sc) > 1e-4:
        raise SystemExit(f'{arm.name}: non-uniform scale {tuple(sc)}')
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    arm.parent = None
    arm.matrix_world = M
    bpy.ops.object.select_all(action='DESELECT')
    for o in [arm] + meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in meshes:
        o.parent = arm
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = Matrix.Identity(4)
        for m in o.modifiers:
            if m.type == 'ARMATURE':
                m.object = arm
    for a in actions:
        a.name = a.name.split('|', 1)[-1]
        for fc in fcurves(a):
            loc = fc.data_path.endswith('.location')
            for k in fc.keyframe_points:
                for pt in (k.co, k.handle_left, k.handle_right):
                    pt.x *= FBX_FPS
                    if loc:
                        pt.y *= sc.x
    for o in objs:
        if o is not arm and o not in meshes:
            bpy.data.objects.remove(o, do_unlink=True)
    return [arm] + meshes


def fcurves(action):
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out += list(bag.fcurves)
    return out


def scale_rig(arm, s):
    """Bake a uniform scale into the bones (rest) and into every action's bone locations."""
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    ends = {eb.name: (eb.head * s, eb.tail * s, eb.roll) for eb in arm.data.edit_bones}
    for eb in arm.data.edit_bones:        # absolute values: moving a connected child's head moves its parent's tail too
        eb.head, eb.tail, eb.roll = ends[eb.name]
    bpy.ops.object.mode_set(mode='OBJECT')
    for a in bpy.data.actions:
        for fc in fcurves(a):
            if fc.data_path.endswith('.location'):
                for k in fc.keyframe_points:
                    k.co.y *= s
                    k.handle_left.y *= s
                    k.handle_right.y *= s


def clear_anim(arm):
    ad = arm.animation_data
    if ad:
        for t in list(ad.nla_tracks):
            ad.nla_tracks.remove(t)
        ad.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)


UMC_FINGERS = ('Index', 'Middle', 'Ring', 'Pinky', 'Thumb')


def is_umc_finger(name):
    return name.startswith(UMC_FINGERS)


def relax_fingers(arm, meshes, rig):
    """Make the fingers' pose in the first idle frame (a relaxed hand) their rest pose, in the meshes and the bones, so
    the clips need no finger channels (the rig drops them). The rig and every person of it do the same, so they match."""
    idle = bpy.data.actions.get(CLIPS[rig]['idle'])
    if idle is None:
        raise SystemExit('no idle action for the fingers')
    use_action(arm, idle)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    basis = {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones if is_umc_finger(pb.name)}
    use_action(arm, None)
    for pb in arm.pose.bones:
        pb.matrix_basis = basis.get(pb.name, Matrix.Identity(4))
    bpy.context.view_layer.update()
    for ob in meshes:
        mod = next(m for m in ob.modifiers if m.type == 'ARMATURE')
        name = mod.name
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.modifier_apply(modifier=name)
        m = ob.modifiers.new(name, 'ARMATURE')
        m.object = arm
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm.pose.bones:
        if hasattr(pb, 'select'):
            pb.select = is_umc_finger(pb.name)
        else:
            pb.bone.select = is_umc_finger(pb.name)
    bpy.ops.pose.armature_apply(selected=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)


def prune_actions(actions, drop=lambda bone: False, eps=1e-4):
    """Drop the channels of bones in `drop`, and every channel that stays at the rest value (location 0, rotation
    identity, scale 1) for the whole clip: a clip without a track leaves that bone at rest in three.js."""
    for a in actions:
        groups = {}
        for fc in fcurves(a):
            if '"' not in fc.data_path:
                continue
            bone = fc.data_path.split('"')[1]
            prop = fc.data_path.rsplit('.', 1)[-1]
            groups.setdefault((bone, prop), []).append(fc)
        for (bone, prop), fcs in groups.items():
            rest = {'location': [0, 0, 0], 'rotation_quaternion': [1, 0, 0, 0], 'scale': [1, 1, 1],
                    'rotation_euler': [0, 0, 0]}.get(prop)
            still = rest is not None and all(abs(k.co.y - rest[fc.array_index]) < eps for fc in fcs for k in fc.keyframe_points)
            if drop(bone) or still or prop == 'scale':
                for fc in fcs:
                    for layer in a.layers:
                        for strip in layer.strips:
                            for bag in strip.channelbags:
                                if fc in list(bag.fcurves):
                                    bag.fcurves.remove(fc)


def use_action(arm, act):
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    if act is not None and getattr(act, 'slots', None) and len(act.slots):
        ad.action_slot = act.slots[0]


def export_glb(path, objs, animations):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
                              export_texcoords=not animations, export_normals=True, export_tangents=False, export_materials='EXPORT',
                              export_animations=animations, export_animation_mode='ACTIONS', export_force_sampling=False,
                              export_optimize_animation_size=True, export_anim_slide_to_zero=True, export_reset_pose_bones=True,
                              export_skins=True, export_influence_nb=4, export_morph=False, export_extras=True,
                              export_cameras=False, export_lights=False, export_def_bones=False, export_leaf_bone=False)


# ---------- people ----------

def mesh_name(rig, outfit, part):
    return MESH_NAME.get((rig, outfit, part)) or MESH_PREFIX.get(outfit, outfit) + PART_MESH[part]


# ---------- 1997 cut: baggy trousers, oversized tops ----------
# Late-90s Korean campus fashion: wide hip-hop jeans and roomy pleated trousers that pile up on the shoes, big
# sweatshirts, hoodies and tees.  The source outfits are slim, so the clothing is loosened around each limb's own
# centre line (skin, i.e. hands and faces, is never touched; long dresses are left alone).
BAGGY = {'Casual_2': 1.5, 'Casual_Hoodie': 1.5, 'Casual': 1.45, 'Worker': 1.3, 'Suit': 1.2, 'Adventurer': 1.3}
ROOMY = {'Casual_2': 1.13, 'Casual_Hoodie': 1.15, 'Casual': 1.1, 'Worker': 1.06, 'Suit': 1.03, 'Adventurer': 1.06, 'Formal': 1.0}


def _smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _skin_verts(me):
    skin = set()
    for poly in me.polygons:
        m = me.materials[poly.material_index] if poly.material_index < len(me.materials) else None
        if m and m.name.startswith('Skin'):
            skin.update(poly.vertices)
    return skin


def _centres(points, key_fn):
    """Centroid of the points in each bin, averaged with the neighbouring bins (smooth centre lines)."""
    acc = {}
    for p in points:
        k = key_fn(p)
        a = acc.setdefault(k, [0.0, 0.0, 0.0, 0])
        a[0] += p[0]; a[1] += p[1]; a[2] += p[2]; a[3] += 1
    cen = {}
    for k in acc:
        sx = sy = sz = n = 0.0
        for d in (-1, 0, 1):
            kk = (k[0], k[1] + d)
            if kk in acc:
                a = acc[kk]
                sx += a[0]; sy += a[1]; sz += a[2]; n += a[3]
        cen[k] = (sx / n, sy / n, sz / n)
    return cen


def loosen(ob, part, outfit):
    """Widen trousers (legs) or tops (body) of one outfit part, in world space."""
    F = (BAGGY if part == 'legs' else ROOMY if part == 'body' else {}).get(outfit, 1.0)
    if F <= 1.0:
        return
    me = ob.data
    mw = ob.matrix_world.copy()
    inv = mw.inverted()
    skin = _skin_verts(me)
    co = {v.index: mw @ v.co for v in me.vertices if v.index not in skin}
    if not co:
        return
    zs = [c.z for c in co.values()]
    zb, zt = min(zs), max(zs)
    H = zt - zb
    if part == 'legs':
        bs = H / 45
        key = lambda c: (1 if c.x >= 0 else -1, int((c.z - zb) / bs))
        cen = _centres(co.values(), key)
        for i, c in co.items():
            h = (c.z - zb) / H
            w = 1 - _smooth(0.62, 0.9, h)                  # the waistband and seat stay fitted
            f = 1 + (F - 1) * w * (0.8 + 0.3 * (1 - h))      # widest at the hem
            cx, cy, _ = cen[key(c)]
            c.x = cx + (c.x - cx) * f
            c.y = cy + (c.y - cy) * f
            if h < 0.07:                                    # the hem breaks over the shoes
                c.z -= 0.035 * H * (1 - h / 0.07)
    else:
        # torso about its vertical centre line; sleeves (T-pose: along x) about the arm's axis
        xs = [abs(c.x) for c in co.values()]
        span = max(xs)
        torso_w = 0.27 * max(span, 0.58)                  # (a tee's sleeves end short: its span is not the arms')
        bt = H / 30
        tkey = lambda c: (0, int((c.z - zb) / bt))
        ba = span / 40
        akey = lambda c: (1 if c.x >= 0 else -1, int(abs(c.x) / ba))
        tcen = _centres([c for c in co.values() if abs(c.x) < torso_w], tkey)
        acen = _centres([c for c in co.values() if abs(c.x) >= torso_w * 0.8], akey)
        for i, c in co.items():
            a = _smooth(torso_w * 0.8, torso_w * 1.25, abs(c.x))     # 0 torso .. 1 sleeve
            h = (c.z - zb) / H
            if a < 1 and tkey(c) in tcen:
                tx, ty, _ = tcen[tkey(c)]
                ft = 1 + (F - 1) * (1 - a) * (0.6 + 0.6 * (1 - h))    # roomier toward the hem
                c.x = tx + (c.x - tx) * ft if abs(c.x) < torso_w else c.x
                c.y = ty + (c.y - ty) * ft
            if a > 0 and akey(c) in acen:
                _, ay, az = acen[akey(c)]
                fa = 1 + (F - 1) * 1.2 * a
                c.y = ay + (c.y - ay) * fa
                c.z = az + (c.z - az) * fa
    for v in me.vertices:
        if v.index in co:
            v.co = inv @ co[v.index]


# ---------- 1997 wardrobe: parts of an outfit in a colour of their own ----------
# The packs' clothes are one colour a garment.  What students wore about 1997 (reference/고증 4.11) needs a little more:
# the broad stripes of a collared tee, the dark collar of a jumper, a knit's sleeves on a sleeveless top.  A person's
# `paint` lists, by part, boxes in the source's T pose (metres; the arms lie along x, the front is -y): the faces of
# the materials `of` whose middle lies inside become the material `to` (an existing one of the part, or a new one
# with a colour of its own in `colors`), and the mesh is cut along the box's sides first, so the edge is straight.
# x is taken either side of the middle (|x|); a bound left out is open.

def paint(ob, rules):
    import bmesh
    me, mw = ob.data, ob.matrix_world
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(mw)
    for rule in rules:
        names = [m.name.split('.')[0] if m else '' for m in me.materials]
        src = {i for i, n in enumerate(names) if n in rule['of']}
        if not src:
            raise SystemExit(f'{ob.name}: nothing of {rule["of"]} to paint')
        if rule['to'] not in names:
            me.materials.append(colour_material(rule['to'], (0.5, 0.5, 0.5, 1)))
            names.append(rule['to'])
        to = names.index(rule['to'])
        box = {k: rule.get(k, (None, None)) for k in 'xyz'}
        planes = [(Vector((sx * v, 0, 0)), Vector((1, 0, 0))) for v in box['x'] if v for sx in (1, -1)]
        planes += [(Vector((0, v, 0)), Vector((0, 1, 0))) for v in box['y'] if v is not None]
        planes += [(Vector((0, 0, v)), Vector((0, 0, 1))) for v in box['z'] if v is not None]
        for co, no in planes:
            fs = [f for f in bm.faces if f.material_index in src]
            geom = fs + list({e for f in fs for e in f.edges}) + list({v for f in fs for v in f.verts})
            bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no)

        def inside(c):
            return all((lo is None or v >= lo) and (hi is None or v <= hi)
                       for v, (lo, hi) in ((abs(c.x), box['x']), (c.y, box['y']), (c.z, box['z'])))
        n = 0
        for f in bm.faces:
            if f.material_index in src and inside(f.calc_center_median()):
                f.material_index = to
                n += 1
        if not n:
            raise SystemExit(f'{ob.name}: the box of {rule["to"]} holds no face of {rule["of"]}')
    bm.transform(mw.inverted())
    bm.to_mesh(me)
    bm.free()


# ---------- 1997 heads: a softened face, calm features, hair grown here ----------
# The packs' heads are the same face under clumped anime hair (a pony tail and a beard among the men), with block
# eyes under scowling brows and no mouth.  Each person takes the pack's one head with a whole skull (men: Worker,
# women: Adventurer), which is softened (one level of subdivision), loses the doll's eyes and brows, and gets
#   - eyes, brows and a mouth drawn in a few lines: the front of the face is laid on the person's cell of the atlas
#     faces.png (face_map; the drawing and its lengths: faces.py), the rest of the person on the atlas' blank cell,
#   - glasses, thin metal rims a centimetre off the eyes (everybody has a pair; the game shows it or not),
#   - hair as a shell around the skull: columns run from the crown down to a hem whose height is given by azimuth
#     (HAIR_STYLES), lie `vol` off the scalp and hang free below it; the hanging part has an inner side.
# Lengths are in the source's units (men x 0.93, women x 0.90 in the game), heights `dz` from the brow line.
# Everything is skinned to the bone Head (long hair shares its ends with Neck), so bags.js, which reads the build
# off the vertices of the other bones, and the clips see the same body as before.
# The materials are named Skin, Hair, Glasses (Band, Bridge): web/src/characters.js crowdLook recolours them by
# these names and leaves the glasses out by 'Glasses'.
# the columns of the hair, by the styles' azimuth (either side): closer together where the hem turns quickly - the
# fringe, the temple, the sideburn and round the ear
HAIR_AZ = [0, 6, 12, 18, 24, 30, 36, 42, 46, 50, 54, 58, 62, 66, 70, 74, 78, 82, 86, 90, 95, 100, 105, 110, 116, 123, 131,
           140, 150, 160, 170, 180]
NOSE_LENGTH = 0.042        # the packs' noses run from the brow down: this long at most
# the nose, a wedge on the face, as everybody has it unless their `face` says otherwise: how far it stands out (of the
# pack's), how much of that is left of the bridge between the eyes, and the profile between them (1: a straight
# bridge, less: a scooped one with the tip standing out, more: a high bridge).  Also of a face: nose_w (the wings'
# width, a scale), nose_up (the tip higher, m)
NOSE = dict(nose=0.92, bridge=0.30, nose_curve=1.0)
HAIR_RN = 0.115            # nominal radius of the head of hair: arc length on the scalp = HAIR_RN x angle from the crown


def _ear(burn=-.036, over=-.008, back=(-.052, -.094, -.104), temple=.012):
    """The hem from the temple round the ear to the nape: down the temple (`temple`: where the fringe hands over) to a
    sideburn close before the ear (its square end at `burn`), up and `over` the ear (its top is at -.014), down
    behind it, `back`: behind the ear, low on the neck, the nape."""
    return [(57, temple), (62, -.012 if temple > 0 else (temple + burn) / 2), (66, burn + .002), (76, burn),
            (81, over - .006), (86, over), (100, over), (106, over - .018), (112, back[0]), (135, back[1]), (180, back[2])]


def _both(front, ear):
    """A hem with a front of its own (signed azimuths) and the same sides and back on either side."""
    return [(-a, v) for a, v in reversed(ear)] + front + ear


# a long fringe parted in the middle, by the angle from the parting; and that cut's sides (the hair over the ear's top)
_CURTAIN = [(9, .034), (20, .006), (32, -.008), (44, -.016), (56, -.024)]
_CURTAIN_SIDE = [(66, -.030), (76, -.030), (82, -.016), (88, -.012), (100, -.012), (106, -.030), (112, -.058), (135, -.102),
                 (180, -.112)]


def _parted(p, side=_CURTAIN_SIDE, k=1.0, apex=.058):
    """A fringe falling from a parting at azimuth p to either temple: the curtain's hem, drawn out on the wide side
    and gathered on the narrow one.  p: 0 parts 5:5, 12 6:4, 23 7:3, 34 2:8 (of the forehead from temple to temple);
    k: how far the fringe falls (1: to the brows' tails)."""
    front = [(p, apex)]
    for sgn in (-1, 1):
        w = (56 - sgn * p) / 56
        front += [(p + sgn * d * w, apex - (apex - v) * k) for d, v in _CURTAIN]
    return _both(sorted(front), side)


_MEN_EAR = _ear()
HAIR_STYLES = {
    # tip: [(azimuth, dz)] the hem; azimuth in degrees, 0 = front, 90 = the ear, 180 = back (signed: + is the
    #      person's left; unsigned lists are mirrored).  vol: [(azimuth, m)] off the scalp, `top` at the crown,
    #      `edge` at the hem.  part: (azimuth, depth, width in degrees).  fall: how fast free hair may close in on
    #      the neck (m per m).  curl: the hem turns in.  sheet: thickness of hanging hair.  rough, ragged: how uneven
    #      the volume and the hem are from lock to lock.  The cuts and what they were taken from: reference/고증 4.9.
    'up': dict(tip=[(0, .042), (24, .043), (40, .038), (50, .026)] + _MEN_EAR,
               vol=[(0, .046), (26, .038), (48, .016), (75, .008), (180, .010)], top=.024,
               edge=[(0, .005), (40, .005), (55, .003), (180, .003)], hem=1.2, rows=9, rough=.5, ragged=.004),
    'crop': dict(tip=[(0, .047), (28, .047), (44, .040), (51, .026)] + _MEN_EAR,
                 vol=[(0, .026), (40, .019), (70, .008), (180, .009)], top=.026,
                 edge=[(0, .010), (36, .008), (52, .004), (180, .003)], sheet=.014, rows=7, rough=.25, ragged=.003),
    'short': dict(tip=_both([(-48, .024), (-28, .014), (-8, .012), (14, .018), (34, .030), (48, .032)], _MEN_EAR),
                  vol=[(-180, .011), (-60, .008), (-20, .014), (20, .012), (60, .008), (180, .011)], top=.026, edge=.004,
                  rows=7, rough=.25, ragged=.005),
    'curtain': dict(tip=_parted(0), vol=[(0, .013), (30, .017), (60, .014), (180, .014)], top=.027, edge=.006,
                    part=(0, .010, 7), rows=8, rough=.3, ragged=.005),
    'curtain-64': dict(tip=_parted(12), vol=[(0, .014), (30, .017), (60, .014), (180, .014)], top=.027, edge=.006,
                       part=(12, .010, 7), rows=8, rough=.3, ragged=.005),
    'sweep-73': dict(tip=_parted(23, _ear(temple=-.016), k=.86),
                     vol=[(-180, .010), (-60, .009), (-25, .019), (8, .017), (30, .013), (60, .008), (180, .010)], top=.027,
                     edge=.005, part=(23, .009, 7), rows=8, rough=.25, ragged=.004),
    'part-side': dict(tip=_parted(34, _ear(temple=.0), k=.70),
                      vol=[(-180, .011), (-90, .009), (-40, .015), (0, .015), (25, .013), (45, .008), (90, .008),
                           (180, .011)], top=.026, edge=.004, part=(34, .009, 8), rows=7, rough=.15, ragged=.003),
    'thin': dict(tip=_both([(-47, .050), (-22, .056), (0, .064), (20, .072), (34, .078), (47, .068)],
                           _ear(burn=-.030, back=(-.048, -.090, -.100))),
                 vol=[(-180, .007), (-90, .005), (-30, .010), (25, .008), (60, .005), (180, .007)], top=.017, edge=.003,
                 part=(34, .006, 8), rows=6, rough=.12),
    'long': dict(tip=[(0, .056), (10, .034), (20, .014), (30, -.008), (40, -.050), (50, -.130), (58, -.215), (72, -.215),
                      (90, -.180), (108, -.215), (135, -.330), (180, -.350)],
                 vol=[(0, .011), (45, .013), (90, .015), (180, .016)], top=.017, edge=.010, part=(0, .007, 7),
                 fall=.10, sheet=.014, rows=12, rough=.08, ragged=.004, ears=False),
    'shoulder': dict(tip=[(-180, -.205), (-135, -.20), (-90, -.175), (-60, -.185), (-52, -.10), (-42, -.035), (-22, .006),
                          (0, .024), (15, .038), (26, .048), (33, .030), (40, -.012), (49, -.10), (58, -.185), (90, -.175), (135, -.20),
                          (180, -.205)],
                     vol=[(-180, .017), (-90, .016), (-30, .014), (28, .012), (60, .015), (180, .017)], top=.019, edge=.011,
                     part=(28, .007, 7), fall=.10, sheet=.015, curl=.010, rows=10, rough=.08, ragged=.0015, ears=False),
    'tuck': dict(tip=[(-180, -.146), (-90, -.146), (-60, -.146), (-52, -.10), (-42, -.035), (-22, .006), (0, .024),
                      (15, .038), (26, .048), (36, .034), (48, .018), (62, .006), (79, .006), (97, .004), (106, -.09),
                      (116, -.146), (180, -.146)],
                 vol=[(-180, .018), (-90, .017), (-30, .015), (28, .012), (55, .008), (97, .008), (114, .016), (180, .018)],
                 top=.020, edge=.010, part=(28, .007, 7), fall=.06, sheet=.016, curl=.014, rows=9, rough=.08, ragged=.0015,
                 ears='left'),
    'pixie': dict(tip=_both([(-48, .010), (-28, .010), (-8, .016), (14, .028), (30, .046), (46, .022)],
                            _ear(burn=-.044, over=-.010, back=(-.060, -.102, -.112))),
                  vol=[(-180, .013), (-60, .011), (-20, .017), (20, .014), (60, .011), (180, .013)], top=.024, edge=.005,
                  part=(30, .004, 7), rows=7, rough=.25, ragged=.004),
    'tied': dict(tip=_both([(-47, .036), (-26, .030), (-6, .030), (14, .040), (30, .052), (47, .040)],
                           _ear(burn=-.026, over=-.004, back=(-.040, -.080, -.090))),
                 vol=[(-180, .011), (-60, .008), (-20, .013), (20, .011), (60, .008), (180, .011)], top=.015, edge=.004,
                 part=(30, .004, 7), rows=6, rough=.08, ragged=.003, tail=dict(dz=-.040, length=.20, r=.027), nape=False),
    'perm': dict(tip=[(-180, -.105), (-135, -.100), (-90, -.072), (-60, -.062), (-50, -.020), (-30, .008), (0, .024),
                      (15, .038), (26, .048), (34, .026), (42, -.008), (52, -.050), (60, -.062), (90, -.072), (135, -.100), (180, -.105)],
                 vol=[(-180, .021), (-90, .021), (-30, .019), (28, .013), (60, .020), (180, .021)], top=.023, edge=.013,
                 part=(28, .006, 7), fall=.5, sheet=.018, curl=.006, rows=8, rough=.35, ragged=.003, ears=False),
}
PART_COLORS = {'Band': '#27345a', 'Glasses': '#77736c'}       # the tie of a tail, thin metal rims
GLASSES = {'umc': (1.36, 1.02), 'women': (1.26, .92)}          # the rims' half width and height, of the eye's half width
ATLAS_UV = 'atlas'                                             # the UV layer into faces.png
BLANK_UV = (faces.uv(faces.BLANK, 0.0, faces.TOP - faces.HALF)[0], 1 - faces.uv(faces.BLANK, 0.0, faces.TOP - faces.HALF)[1])


def hex_mix(a, b, t):
    return '#' + ''.join('%02x' % round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t) for i in (1, 3, 5))


def _cos_interp(pts, x):
    """Through the control points [(x, y)] (sorted), easing in and out of each; held beyond the ends."""
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + (y1 - y0) * (0.5 - 0.5 * math.cos(math.pi * t))
    return pts[-1][1]


def _by_azimuth(pts, a):
    """A style's list by azimuth (degrees, signed): mirrored when it only has the 0 .. 180 half."""
    return _cos_interp(pts, a if pts[0][0] < 0 else abs(a))


def _bbox(pts):
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def head_islands(bm):
    seen, out = set(), []
    for f in bm.faces:
        if f in seen:
            continue
        seen.add(f)
        stack, comp = [f], []
        while stack:
            x = stack.pop()
            comp.append(x)
            for e in x.edges:
                for y in e.link_faces:
                    if y not in seen:
                        seen.add(y)
                        stack.append(y)
        out.append(comp)
    return out


def head_clean(ob, style, face, rig):
    """The head as one skull with its ears and nose: the doll's eyes and brows, the hat and the moustache go (where
    the eyes were is returned), the cap painted on the scalp becomes the material 'Hair'.  The nose, a wedge stuck on
    the face, is made lower and a little wider."""
    import bmesh
    me = ob.data
    mw = ob.matrix_world
    names = [m.name.split('.')[0] if m else '' for m in me.materials]
    me.materials.append(colour_material('Hair', (0, 0, 0, 1)))
    hair = len(me.materials) - 1
    bm = bmesh.new()
    bm.from_mesh(me)
    isl = head_islands(bm)
    main = max(isl, key=len)
    L = {'eyes': [], 'ears': [], 'nose': None}
    kill = []
    soft = [v for f in main for v in f.verts]
    for comp in isl:
        if comp is main:
            continue
        box = _bbox([mw @ v.co for f in comp for v in f.verts])
        mats = {names[f.material_index] for f in comp}
        if mats == {'Skin'}:
            if abs(box[0].x + box[1].x) > 0.08:
                L['ears'].append(box)
                keep = style.get('ears', True)              # (True, False, or 'left': only the person's left ear shows)
                if keep is True or keep == 'left' and box[0].x > 0:
                    continue
            else:
                L['nose'] = box
                inv = mw.inverted()
                tip, bridge, curve = (face.get(k, NOSE[k]) for k in ('nose', 'bridge', 'nose_curve'))
                for v in {v for f in comp for v in f.verts}:
                    p = mw @ v.co
                    h = (p.z - box[0].z) / (box[1].z - box[0].z)            # 0 at the tip's underside .. 1 at the brow
                    p.y = box[1].y + (p.y - box[1].y) * tip * (1 - (1 - bridge) * h ** curve)
                    p.z = box[0].z + (p.z - box[0].z) * min(1.0, NOSE_LENGTH / (box[1].z - box[0].z)) \
                        + face.get('nose_up', 0.0) * (1 - h) ** 2
                    p.x *= (1.1 - 0.3 * h) * (1 + (face.get('nose_w', 1.0) - 1) * (1 - h) ** 0.7)
                    v.co = inv @ p
                soft += [v for f in comp for v in f.verts]
                continue
        elif mats <= {'Eye', 'Brown'}:
            L['eyes'].append(box)
        kill += comp
    for f in main:
        if names[f.material_index] != 'Skin':
            f.material_index = hair
    if len(L['eyes']) != 2 or len(L['ears']) != 2 or not L['nose']:
        raise SystemExit(f'{ob.name}: the head is not the one expected (eyes {len(L["eyes"])}, ears {len(L["ears"])})')
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    # the lower face: the packs' is long with a narrow jaw. Rounder: fuller (most at the mouth, by the person's own
    # jaw too), and the jaw shorter
    jaw, short = face.get('jaw', 1.0) * FACE[rig]['cheek'], 1 - FACE[rig]['chin'] * face.get('chin', 1.0)
    nb = L['nose'][0].z
    chin, cheek = nb - 0.085, (L['eyes'][0][0].z + L['eyes'][0][1].z) / 2 - 0.012
    inv = mw.inverted()
    zb = min((mw @ v.co).z for f in main for v in f.verts)       # (the neck's lower edge stays where the body has it)
    for v in {v for f in main for v in f.verts}:
        p = mw @ v.co
        if p.y < L['ears'][0][1].y + 0.01:
            p.x *= 1 + (jaw - 1) * _smooth(cheek, cheek - 0.05, p.z) * _smooth(chin - 0.035, chin + 0.01, p.z)
            if p.z < nb:
                p.z += (nb - p.z) * short * _smooth(chin - 0.05, chin - 0.005, p.z) * _smooth(zb + 0.002, zb + 0.03, p.z)
            v.co = inv @ p
    # the pack's faces are a few flat planes: ease them before and after the subdivision (head_soften)
    soft = list({v for v in soft if v.is_valid and not v.is_boundary})
    L['top'] = max((mw @ v.co).z for v in bm.verts)
    for _ in range(2):
        bmesh.ops.smooth_vert(bm, verts=soft, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmesh.ops.join_triangles(bm, faces=bm.faces[:], cmp_materials=True, angle_face_threshold=math.radians(40),
                             angle_shape_threshold=math.radians(40))
    bm.to_mesh(me)
    bm.free()
    return L


def head_soften(ob, L):
    """One level of subdivision (the vertex groups come along), then the planes eased once more; not the ears.
    Easing shrinks: the skull is scaled back to its height (the person's height is that of the pack's head)."""
    import bmesh
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    mod = ob.modifiers.new('soften', 'SUBSURF')
    mod.levels = 1
    bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mw = ob.matrix_world
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    soft = set()
    for comp in head_islands(bm):
        vs = {v for f in comp for v in f.verts}
        if abs(sum((mw @ v.co).x for v in vs) / len(vs)) < 0.04:            # the skull and the nose
            soft |= {v for v in vs if not v.is_boundary}
    bmesh.ops.smooth_vert(bm, verts=list(soft), factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    zc = L['top'] - 0.106
    pts = [mw @ v.co for v in soft]
    c = Vector((0, (min(p.y for p in pts if p.z > zc) + max(p.y for p in pts if p.z > zc)) / 2, zc))
    k = (L['top'] - zc) / (max(p.z for p in pts) - zc)
    inv = mw.inverted()
    for v in bm.verts:
        p = mw @ v.co
        v.co = inv @ (c + (p - c) * (1 + (k - 1) * _smooth(zc - 0.04, zc + 0.02, p.z)))
    bm.to_mesh(ob.data)
    bm.free()


class HeadSurface:
    """The head (and the shoulders under it) as the hair and the features see it: rays from outside in."""

    def __init__(self, head, body, L):
        import bmesh
        from mathutils.bvhtree import BVHTree
        self.trees = []
        for ob in (head, body):
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bm.transform(ob.matrix_world)
            self.trees.append(BVHTree.FromBMesh(bm))
            bm.free()
        self.head, self.body = self.trees
        cz = L['top'] - 0.106
        f = self.head.ray_cast(Vector((0, -0.5, cz + 0.03)), Vector((0, 1, 0)))[0]
        b = self.head.ray_cast(Vector((0, 0.5, cz + 0.03)), Vector((0, -1, 0)))[0]
        self.C = Vector((0, (f.y + b.y) / 2, cz))
        ear = max(L['ears'], key=lambda box: box[1].x)
        self.a_ear = math.degrees(math.atan2((ear[0].x + ear[1].x) / 2, self.C.y - (ear[0].y + ear[1].y) / 2))

    def style_azimuth(self, a):
        """A direction (degrees, 0 = front, signed) as the styles count it: the ear at 90."""
        s, a = (1 if a >= 0 else -1), abs(a)
        return s * (a * 90 / self.a_ear if a <= self.a_ear else 90 + (a - self.a_ear) * 90 / (180 - self.a_ear))

    def from_style(self, ap):
        """The direction (degrees) of a style's azimuth: the inverse of style_azimuth."""
        s, ap = (1 if ap >= 0 else -1), abs(ap)
        return s * (ap * self.a_ear / 90 if ap <= 90 else self.a_ear + (ap - 90) * (180 - self.a_ear) / 90)

    def sph(self, d):
        """Distance from the centre to the outermost skin along d."""
        hit = self.head.ray_cast(self.C + d * 0.4, -d, 0.4)
        return 0.4 - hit[3] if hit[0] else HAIR_RN - 0.012

    def cyl(self, a, z):
        """Horizontal distance from the head's axis to the outermost surface at height z in direction a (radians)."""
        d = Vector((math.sin(a), -math.cos(a), 0))
        o = Vector((self.C.x, self.C.y, z))
        best = None
        hit = self.head.ray_cast(o + d * 0.3, -d, 0.3)
        if hit[0]:
            best = 0.3 - hit[3]
        if z < self.C.z - 0.12:                                        # clothes: coarse and loose, so a margin and a look around
            for da, dz in ((0, 0), (0, 0.02), (0, -0.02), (0.08, 0), (-0.08, 0)):
                d2 = Vector((math.sin(a + da), -math.cos(a + da), 0))
                o2 = Vector((self.C.x, self.C.y, z + dz))
                hit = self.body.ray_cast(o2 + d2 * 0.26, -d2, 0.26)
                if hit[0]:
                    r = 0.26 if hit[1].dot(d2) < 0 else 0.26 - hit[3] + 0.007     # (a back face: the start was inside an arm)
                    best = r if best is None else max(best, r)
        return best

    def front(self, x, z):
        """The face seen from the front at (x, z): the point and the normal."""
        hit = self.head.ray_cast(Vector((x, self.C.y - 0.4, z)), Vector((0, 1, 0)))
        return hit[0], hit[1]


def hair_grow(pid, surf, st):
    """The head of hair as (points, faces, neck weights, ...): see the notes above HAIR_STYLES."""
    import random
    import zlib
    rnd = random.Random(zlib.crc32(pid.encode()))
    cols = [math.radians(surf.from_style(a)) for a in HAIR_AZ]
    cols += [2 * math.pi - a for a in reversed(cols[1:-1])]             # (round the head, 0 = the front, the left first)
    NA, NR = len(cols), st.get('rows', 7)
    C, Rn = surf.C, HAIR_RN
    s_eq = Rn * math.pi / 2
    fall, sheet, curl = st.get('fall', 1.5), st.get('sheet', 0.012), st.get('curl', 0.0)
    noise = [rnd.uniform(-1, 1) for _ in range(NA)]
    noise = [(noise[j - 1] + 2 * noise[j] + noise[(j + 1) % NA]) / 4 for j in range(NA)]
    lock = [rnd.uniform(-1, 1) for _ in range(NA)]
    lock = [(lock[j - 1] + 2 * lock[j] + lock[(j + 1) % NA]) / 3 for j in range(NA)]       # (locks a few columns wide)
    pts, faces = [C.copy()], []
    streak, aps = [], []        # faces of the bleached locks (style 'bridge': [(azimuth, half width)]); azimuth by column
    grid = {}                  # (column, row) -> vertex
    inner = {}                 # (column, row) -> vertex of the inner side
    ends = []                  # per column: arc length of the hem
    top_r = []
    for j in range(NA):
        a = cols[j]
        deg = math.degrees(a if a <= math.pi else a - 2 * math.pi)
        ap = surf.style_azimuth(deg)
        aps.append(ap)
        dz_tip = _by_azimuth(st['tip'], ap) + st.get('ragged', 0) * lock[j]
        s_end = Rn * (math.pi / 2 - math.asin(min(1.0, dz_tip / Rn))) if dz_tip >= 0 else s_eq - dz_tip
        ends.append(s_end)
        zone = _by_azimuth(st['vol'], ap)
        edge = st['edge'] if isinstance(st['edge'], float) else _by_azimuth(st['edge'], ap)
        part = st.get('part')
        prev = None
        hang = dz_tip < -0.08
        for i in range(1, NR):
            u = i / (NR - 1)
            s = s_end * u
            t = st['top'] + (zone - st['top']) * _smooth(0.0, 0.55, s / max(s_end, 0.16))
            t *= 1 + st.get('rough', 0) * noise[j] * _smooth(0.05, 0.3, u)
            if part:
                t -= part[1] * math.exp(-((ap - part[0]) / part[2]) ** 2) * _smooth(0.1, 0.3, u)
            t = max(0.0015, t + (edge - t) * u ** st.get('hem', 4))
            if s <= s_eq:
                e = math.pi / 2 - s / Rn
                d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
                p = C + d * (surf.sph(d) + t)
                rho, z = math.hypot(p.x - C.x, p.y - C.y), p.z
                rs = rho - t * math.cos(e)
            else:
                z = C.z - (s - s_eq)
                rs = surf.cyl(a, z)
                if rs is None:
                    rs = prev[2] if prev else 0.0
                rho = rs + t
            if prev:
                drop = prev[1] - z
                rho = max(rho, prev[0] - fall * drop)                       # free hair hangs: it closes in slowly
                if z < C.z - 0.10:
                    rho = min(rho, prev[0] + st.get('flare', 0.12) * drop)     # and does not ride out over a shoulder (T pose)
            if curl:
                rho = max(rs + 0.003, rho - curl * _smooth(0.62, 1.0, u) ** 2)
            prev = (rho, z, rs)
            grid[j, i] = len(pts)
            pts.append(Vector((C.x + rho * math.sin(a), C.y - rho * math.cos(a), z)))
            if i == 1:
                top_r.append((rho, z))
            if hang and z < C.z - 0.03 or i == NR - 1:
                ri = min(rho - 0.002, max(rs + (0.0008 if z > C.z - 0.12 else 0.003), rho - sheet))
                inner[j, i] = len(pts)
                pts.append(Vector((C.x + ri * math.sin(a), C.y - ri * math.cos(a), z + (0.0 if i < NR - 1 else 0.0005))))
    pts[0] = Vector((C.x, C.y, max(z for _, z in top_r) + 0.0045))             # the crown: a little over the first ring

    def split(a, b, c, d):
        """The quad a b c d as two triangles, creased along the diagonal that lies further out: a twisted quad (where
        hanging hair meets hair on the scalp) creased the other way dips into the head and lets skin through."""
        def out(p):
            return math.hypot(p.x - C.x, p.y - C.y) if p.z < C.z else (p - C).length
        if out((pts[a] + pts[c]) / 2) >= out((pts[b] + pts[d]) / 2):
            return [(a, b, c), (a, c, d)]
        return [(a, b, d), (b, c, d)]

    for j in range(NA):
        k = (j + 1) % NA
        first = len(faces)
        faces.append((0, grid[k, 1], grid[j, 1]))
        for i in range(1, NR - 1):
            faces += split(grid[j, i], grid[k, i], grid[k, i + 1], grid[j, i + 1])
        faces.append((grid[j, NR - 1], grid[k, NR - 1], inner[k, NR - 1], inner[j, NR - 1]))      # the hem
        if any(abs(aps[j] - c) <= w for c, w in st.get('bridge', ())):
            streak += range(first + 3, len(faces))            # (a lock: from below the crown to the hem)
        for i in range(1, NR - 1):
            if (j, i) in inner and (k, i) in inner:
                faces.append((inner[j, i + 1], inner[k, i + 1], inner[k, i], inner[j, i]))
    # faces were listed for a normal pointing out when the columns run clockwise seen from above: check one
    a, b, c = (pts[i] for i in faces[0])
    if (b - a).cross(c - a).z < 0:
        faces = [tuple(reversed(f)) for f in faces]
    neck = [0.7 * _smooth(C.z - 0.17, C.z - 0.36, p.z) for p in pts]
    tail = st.get('tail')
    band = []
    if tail:
        tp, tf, band = hair_tail(surf, st, tail, len(pts))
        band = [len(faces) + i for i in band]
        pts += tp
        faces += tf
        neck += [0.6 * _smooth(C.z - 0.10, C.z - 0.30, p.z) for p in tp]
    return pts, faces, neck, (cols, ends), band, streak


def hair_tail(surf, st, tail, base):
    """A tied tail from the back of the head down the neck: a six-sided tube, its first ring the band."""
    C = surf.C
    z0 = C.z + tail['dz']
    r, n = tail['r'], tail['length']
    y0 = C.y + (surf.cyl(math.pi, z0) or HAIR_RN) + 0.004
    path = [(y0 - 0.012, z0, 0.55 * r), (y0 + 0.008, z0 - 0.004, 0.58 * r), (y0 + 0.022, z0 - 0.012, 0.62 * r),
            (y0 + 0.040, z0 - 0.045, 1.0 * r), (y0 + 0.038, z0 - 0.45 * n, 0.95 * r), (y0 + 0.026, z0 - 0.8 * n, 0.7 * r),
            (y0 + 0.020, z0 - n, 0.18 * r)]
    pts, faces, band = [], [], []
    for k, (y, z, rad) in enumerate(path):
        # keep off the neck and the back
        back = surf.cyl(math.pi, z)
        if k > 2 and back is not None:
            y = max(y, C.y + back + rad * 0.9)
        dy, dz = (path[min(k + 1, len(path) - 1)][0] - path[max(k - 1, 0)][0]), (path[min(k + 1, len(path) - 1)][1] - path[max(k - 1, 0)][1])
        ln = math.hypot(dy, dz) or 1.0
        ny, nz = -dz / ln, dy / ln                 # across the path, in the y-z plane
        for q in range(6):
            w = 2 * math.pi * q / 6
            pts.append(Vector((rad * 1.15 * math.cos(w), y + ny * rad * 0.85 * math.sin(w), z + nz * rad * 0.85 * math.sin(w))))
    for k in range(len(path) - 1):
        for q in range(6):
            f = (base + k * 6 + q, base + k * 6 + (q + 1) % 6, base + (k + 1) * 6 + (q + 1) % 6, base + (k + 1) * 6 + q)
            faces.append(f)
            if k == 1:
                band.append(len(faces) - 1)
    faces.append(tuple(base + (len(path) - 1) * 6 + q for q in range(6)))
    a, b, c = (pts[i - base] for i in faces[0][:3])
    if (b - a).cross(c - a).dot(a - Vector((0, path[0][0], path[0][1]))) < 0:
        faces[:] = [tuple(reversed(f)) for f in faces]
    return pts, faces, band


def atlas_layer(ob):
    """The UV layer into faces.png alone on the mesh; made (all of it on the blank cell) where there is none."""
    me = ob.data
    for layer in [l for l in me.uv_layers if l.name != ATLAS_UV]:
        me.uv_layers.remove(layer)
    if not me.uv_layers:
        layer = me.uv_layers.new(name=ATLAS_UV)
        for d in layer.data:
            d.uv = BLANK_UV
    return me.uv_layers[ATLAS_UV]


def eye_line(L, face):
    return sum((b[0].z + b[1].z) / 2 for b in L['eyes']) / 2 + face.get('eyes_up', 0.0)


def face_map(head, surf, L, face, rig, cell):
    """The front of the face on the person's cell of the atlas (faces.py draws it there): seen from the front, x and
    the height over the eye line.  Faces of the mesh that are not skin, look away, lie behind the front of the ears or
    reach out of the cell's frame stay on the blank cell.  The drawing has the mouth and the nose at heights measured
    once on these heads: checked here."""
    f = FACE[rig]
    ez0 = eye_line(L, face)
    nz = L['nose'][0].z
    z, last = nz - 0.03, None
    while z > nz - 0.14:                                   # down the profile to where it turns back under the chin
        p = surf.front(0, z)[0]
        if p is None or (last is not None and p.y > last + 0.004):
            break
        last = p.y
        z -= 0.002
    mz = z + (nz - z) * 0.53                               # the mouth: between the nose and the chin
    if abs(mz - ez0 - f['mouth_dz']) > 0.002 or abs(nz - ez0 - f['nose_dz']) > 0.002:
        raise SystemExit(f'{head.name}: the mouth is {mz - ez0:.4f}, the nose {nz - ez0:.4f} under the eyes; faces.py '
                         f'draws them at {f["mouth_dz"]}, {f["nose_dz"]}')
    me = head.data
    mw = head.matrix_world
    rot = mw.to_3x3()
    layer = atlas_layer(head)
    skin = {i for i, m in enumerate(me.materials) if m and m.name.split('.')[0] == 'Skin'}
    front = min(b[0].y for b in L['ears']) - 0.004
    n = 0
    for poly in me.polygons:
        pts = [mw @ me.vertices[v].co for v in poly.vertices]
        on = (poly.material_index in skin and (rot @ poly.normal).y < -0.05
              and all(p.y < front and faces.in_frame(p.x, p.z - ez0) for p in pts))
        n += on
        for li, p in zip(poly.loop_indices, pts):
            if on:
                u, v = faces.uv(cell, p.x, p.z - ez0)
                layer.data[li].uv = (u, 1 - v)
            else:
                layer.data[li].uv = BLANK_UV
    if n < 60:
        raise SystemExit(f'{head.name}: only {n} faces of the mesh lie on the drawn face')


def face_glasses(surf, L, hw, ex, glasses):
    """Round-cornered rims a centimetre off the eyes, a bridge, and temples back to the ears: (points, faces)."""
    pts, faces = [], []
    ez = (L['eyes'][0][0].z + L['eyes'][0][1].z) / 2 - 0.001
    ear = max(L['ears'], key=lambda box: box[1].x)
    gw, gh = glasses
    W, H, T, N = hw * gw, hw * gh, 0.0024, 16
    for box in L['eyes']:
        sx = 1 if box[0].x + box[1].x > 0 else -1
        y = surf.front(sx * ex, ez)[0].y - 0.011
        base = len(pts)
        for q in range(N):
            w = 2 * math.pi * q / N
            cx, cz = math.cos(w), math.sin(w)
            k = (abs(cx) ** 2.6 + abs(cz) ** 2.6) ** (-1 / 2.6)          # a rounded rectangle
            for r in (1.0, 1.0 + T / H):
                x = ex + W * k * cx * r
                pts.append(Vector((sx * x, y + 0.10 * max(0.0, x - ex), ez + H * k * cz * r)))
        for q in range(N):
            a, b = base + 2 * q, base + 2 * ((q + 1) % N)
            faces.append((a, b, b + 1, a + 1) if sx > 0 else (a, a + 1, b + 1, b))
        # the temple, from the rim's outer top corner to over the ear
        x0, x1 = ex + W * 1.02, ear[0].x + 0.006
        y1 = (ear[0].y + ear[1].y) / 2
        z0 = ez + H * 0.45
        base = len(pts)
        pts += [Vector((sx * x0, y + 0.10 * W, z0)), Vector((sx * x0, y + 0.10 * W, z0 + T)),
                Vector((sx * (x1 + 0.004), y1, z0 + 0.006 + T)), Vector((sx * (x1 + 0.004), y1, z0 + 0.006))]
        faces.append((base, base + 1, base + 2, base + 3) if sx < 0 else (base + 3, base + 2, base + 1, base))
    # the bridge
    xi = ex - W
    y = surf.front(xi, ez)[0].y - 0.011
    base = len(pts)
    pts += [Vector((-xi, y, ez + H * 0.25)), Vector((xi, y, ez + H * 0.25)), Vector((xi, y, ez + H * 0.25 + T)), Vector((-xi, y, ez + H * 0.25 + T))]
    faces.append((base, base + 1, base + 2, base + 3))
    for i, fc in enumerate(faces):                           # the rims and the bridge face the front, the temples out
        n = (pts[fc[1]] - pts[fc[0]]).cross(pts[fc[2]] - pts[fc[0]])
        c = sum((pts[k] for k in fc), Vector()) / len(fc)
        if (n.y > 0) if abs(n.y) > abs(n.x) else (n.x * c.x < 0):
            faces[i] = tuple(reversed(fc))
    return pts, faces


def head_trim(ob, surf, st, ends):
    """Scalp that the hair covers goes (nothing sees it); the old cap's paint is skin wherever the new hair does not
    cover it, from the forehead round to behind the ears, or all round (it ends in whole faces: a stepped hairline;
    a man's nape keeps it as short hair)."""
    import bmesh
    me = ob.data
    mw = ob.matrix_world
    import bisect
    C, Rn = surf.C, HAIR_RN
    s_eq = Rn * math.pi / 2
    cols, ends = ends
    NA = len(ends)
    hair = next(i for i, m in enumerate(me.materials) if m and m.name.split('.')[0] == 'Hair')
    skin = next(i for i, m in enumerate(me.materials) if m and m.name.split('.')[0] == 'Skin')

    def where(p):
        a = math.atan2(p.x - C.x, -(p.y - C.y))
        dz = p.z - C.z
        s = Rn * (math.pi / 2 - math.atan2(dz, math.hypot(p.x - C.x, p.y - C.y))) if dz >= 0 else s_eq - dz
        w = a % (2 * math.pi)
        j = bisect.bisect_right(cols, w) - 1
        t = (w - cols[j]) / ((cols[j + 1] if j + 1 < NA else 2 * math.pi) - cols[j])
        near = [ends[(j + d) % NA] for d in (-1, 0, 1, 2)]
        return math.degrees(a), dz, s, min(near), near[1] + (near[2] - near[1]) * t           # (.., least, here)

    back = 118 if st.get('ears', True) is True else 100     # (hair over the ears hides the sides of the head too)
    bm = bmesh.new()
    bm.from_mesh(me)
    kill = []
    for f in bm.faces:
        info = [where(mw @ v.co) for v in f.verts]
        if all(s < lo - 0.03 and (dz > 0.0 or (abs(surf.style_azimuth(a)) > back and dz > -0.07)) for a, dz, s, lo, _ in info):
            kill.append(f)
        elif f.material_index == hair:
            a = where(mw @ f.calc_center_median())[0]             # (a face any corner of which shows)
            if (abs(surf.style_azimuth(a)) < 104 or not st.get('nape', True)) and any(s > here - 0.002 for _, _, s, _, here in info):
                f.material_index = skin
        elif all(s < here - 0.006 and dz > -0.03 for _, dz, s, _, here in info):
            f.material_index = hair                               # (skin under the hair: if it pokes through, as hair)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(me)
    bm.free()


def head_part(name, arm, pieces, neck=None):
    """A mesh of [(material, points, faces)] skinned to the head (and, by `neck` per point of the first piece, the neck)."""
    me = bpy.data.meshes.new(name)
    pts, faces, mats = [], [], []
    for mname, p, fs in pieces:
        base = len(pts)
        pts += p
        if mname not in mats:
            mats.append(mname)
        faces += [(tuple(base + i for i in f), mats.index(mname)) for f in fs]
    me.from_pydata([tuple(p) for p in pts], [], [f for f, _ in faces])
    for m in mats:
        me.materials.append(bpy.data.materials.get(m) or colour_material(m, (0, 0, 0, 1)))
    for poly, (_, mi) in zip(me.polygons, faces):
        poly.material_index = mi
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = arm
    head, nk = ob.vertex_groups.new(name='Head'), ob.vertex_groups.new(name='Neck')
    for i in range(len(pts)):
        w = neck[i] if neck and i < len(neck) else 0.0
        head.add([i], 1.0 - w, 'REPLACE')
        if w > 0:
            nk.add([i], w, 'REPLACE')
    ob.modifiers.new('Armature', 'ARMATURE').object = arm
    return ob


def head_1997(pid, head, body, arm, spec):
    """The pack's head made over (see above); returns the one head mesh."""
    rig = spec['rig']
    st = HAIR_STYLES[spec['hair']]
    if spec.get('flip'):                                    # the same cut, parted on the other side
        st = dict(st, tip=[(-a, v) for a, v in reversed(st['tip'])] if st['tip'][0][0] < 0 else st['tip'],
                  vol=[(-a, v) for a, v in reversed(st['vol'])] if st['vol'][0][0] < 0 else st['vol'],
                  part=(-st['part'][0],) + tuple(st['part'][1:]) if st.get('part') else None)
    face = spec.get('face', {})
    L = head_clean(head, st, face, rig)
    head_soften(head, L)
    surf = HeadSurface(head, body, L)
    if spec.get('bridge'):
        st = dict(st, bridge=spec['bridge'])
    pts, faces, neck, ends, band, streak = hair_grow(pid, surf, st)
    head_trim(head, surf, st, ends)
    other = set(band) | set(streak)
    pieces = [('Hair', pts, [f for i, f in enumerate(faces) if i not in other])]
    for name, part in (('Band', band), ('Bridge', streak)):  # (these have points of their own)
        if part:
            ring = sorted({i for b in part for i in faces[b]})
            at = {i: n for n, i in enumerate(ring)}
            pieces.append((name, [pts[i] * 1.0 for i in ring], [tuple(at[i] for i in faces[b]) for b in part]))
    col = spec['colors']
    hair = col.get('Hair', HAIR['black'])
    defaults = dict(PART_COLORS, Hair=hair, Bridge=hex_mix(hair, '#d9a35a', 0.5))
    for name in ('Hair', 'Band', 'Glasses', 'Bridge'):
        colour_material(name, srgb_to_linear(col.get(name, defaults[name])))
    hob = head_part(pid + '-hair', arm, pieces, neck)
    hw = FACE[rig]['eye'][0] * face.get('eye', 1.0)
    fob = head_part(pid + '-glasses', arm, [('Glasses', *face_glasses(surf, L, hw, FACE[rig]['gap'] / 2 + hw, GLASSES[rig]))])
    face_map(head, surf, L, face, rig, list(PEOPLE).index(pid))
    for o in (hob, fob):
        atlas_layer(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in (hob, fob, head):
        o.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.join()
    return head


def build_person(pid, spec):
    rig = spec['rig']
    s = HEIGHT[rig] / TOP[rig]
    arm = None
    parts = []
    loaded = {}
    for part in ('body', 'head', 'legs', 'feet'):
        outfit = spec['parts'][part]
        if outfit not in loaded:
            loaded[outfit] = import_outfit(rig, outfit)
        objs = loaded[outfit]
        want = mesh_name(rig, outfit, part)
        ob = next((o for o in objs if o.type == 'MESH' and o.name.split('.')[0] == want), None)
        if ob is None:
            raise SystemExit(f'{pid}: no mesh {want} in {outfit}{SRC[rig][1]}')
        if arm is None:
            arm = next(o for o in objs if o.type == 'ARMATURE')
        mw = ob.matrix_world.copy()
        ob.parent = arm
        ob.matrix_world = mw
        for m in ob.modifiers:
            if m.type == 'ARMATURE':
                m.object = arm
        if part == 'head':
            ob = head_1997(pid, ob, parts[0], arm, spec)
        if part in spec.get('paint', {}):
            paint(ob, spec['paint'][part])
        recolour(ob, part, spec['colors'])
        loosen(ob, part, outfit)
        atlas_layer(ob)
        ob.name = f'{pid}-{part}'
        parts.append(ob)
    keep = set(parts) | {arm}
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    clear_anim(arm)
    relax_fingers(arm, parts, rig)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    return finish_person(pid, arm, parts, s, 'rig-' + rig, bool(spec.get('face', {}).get('glasses')))


def finish_person(pid, arm, parts, s, rig, glasses):
    tidy_materials()
    # one mesh, smooth shaded, scale baked in
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    mesh = bpy.context.view_layer.objects.active
    for m in list(mesh.modifiers):
        if m.type != 'ARMATURE':
            mesh.modifiers.remove(m)
    me = mesh.data
    atlas_layer(mesh)
    for a in list(me.color_attributes):
        me.color_attributes.remove(a)
    for a in list(me.attributes):
        if a.name in ('sharp_face', 'sharp_edge'):
            me.attributes.remove(a)
    if me.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    me.shade_smooth()
    # bake the object transforms, then the scale
    for o in (arm, mesh):
        if any(abs(v) > 1e-6 for v in o.location) or any(abs(v) > 1e-6 for v in o.rotation_euler) or any(abs(v - 1) > 1e-6 for v in o.scale):
            raise SystemExit(f'{pid}: {o.name} is not at the origin')
    me.transform(Matrix.Scale(s, 4))
    scale_rig(arm, s)
    mesh.name = me.name = pid + '-mesh'
    arm.name = pid
    arm.data.name = pid
    arm['rig'] = rig
    arm['glasses'] = int(glasses)          # whether the person wears the pair as the model is
    return [arm, mesh]


# ---------- rigs: the shared animations ----------

def arm_space_follow(pb):
    """The armature-space matrix of pb when its own pose is the rest pose (it only follows its parent)."""
    if pb.parent is None:
        return pb.bone.matrix_local.copy()
    return pb.parent.matrix @ pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local


def rotate_about_head(pb, axis, deg):
    M = pb.matrix.copy()
    h = M.translation.copy()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h) @ M
    bpy.context.view_layer.update()


def pose_from(arm, act, frame):
    use_action(arm, act)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones}


def set_pose(arm, basis):
    use_action(arm, None)
    for pb in arm.pose.bones:
        pb.matrix_basis = basis.get(pb.name, Matrix.Identity(4))
    bpy.context.view_layer.update()


def key_pose(arm, act, frame):
    use_action(arm, act)
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.keyframe_insert('location', frame=frame, group=pb.name)
        pb.keyframe_insert('rotation_quaternion', frame=frame, group=pb.name)


def new_action(arm, name, keys):
    """keys: list of (frame, {bone: matrix_basis}). The action holds every bone at every key."""
    act = bpy.data.actions.new(name)
    for frame, basis in keys:
        set_pose(arm, basis)
        key_pose(arm, act, frame)
    use_action(arm, None)
    return act


def sit_pose(arm, base, s, poles=None, arms=(-14, -38)):
    """From a standing pose (bone -> matrix_basis): the body down so the hips are SEAT + HIP_OVER_SEAT high, thighs
    forward, shins straight down, the feet (bones of their own under the root) under the knees, forearms on the thighs.
    Both rigs name these bones alike: Body, UpperLeg.L/R, LowerLeg.L/R, Foot.L/R, UpperArm.L/R, LowerArm.L/R."""
    set_pose(arm, base)
    pb = arm.pose.bones
    hip_now = (pb['UpperLeg.L'].head.z + pb['UpperLeg.R'].head.z) / 2
    pb['Body'].matrix = Matrix.Translation((0, 0, (SEAT + HIP_OVER_SEAT) / s - hip_now)) @ pb['Body'].matrix
    bpy.context.view_layer.update()
    for side in 'LR':
        ul, ll, ft = pb['UpperLeg.' + side], pb['LowerLeg.' + side], pb['Foot.' + side]
        out = 4 if side == 'L' else -4           # knees a little apart
        ul.matrix = (Matrix.Translation(ul.matrix.translation) @ Matrix.Rotation(math.radians(out), 4, 'Z')
                     @ Matrix.Rotation(math.radians(-88), 4, 'X') @ ul.bone.matrix_local.to_3x3().to_4x4())
        bpy.context.view_layer.update()
        knee = ll.matrix.translation.copy()
        ll.matrix = Matrix.Translation(knee) @ Matrix.Rotation(math.radians(-4), 4, 'X') @ ll.bone.matrix_local.to_3x3().to_4x4()
        bpy.context.view_layer.update()
        ankle = ll.matrix @ Vector((0, ll.bone.length, 0))
        rest_ankle = ll.bone.tail_local
        ft.matrix = Matrix.Translation(ankle - rest_ankle) @ ft.bone.matrix_local
        if poles and pb.get(poles + side):
            pt = pb[poles + side]
            pt.matrix = Matrix.Translation(ankle - rest_ankle + Vector((0, -0.3 / s * 0.05, 0.3 / s * 0.05))) @ pt.bone.matrix_local
        bpy.context.view_layer.update()
        rotate_about_head(pb['UpperArm.' + side], 'X', arms[0])
        rotate_about_head(pb['LowerArm.' + side], 'X', arms[1])
    return {b.name: b.matrix_basis.copy() for b in pb}


def head_shake(arm, base, head='Head', neck='Neck'):
    """Shake the head (a 'no'): yaw about the head bone's own axis (it points up)."""
    keys = []
    for f, a in [(0, 0), (6, 24), (13, -24), (20, 20), (27, -14), (33, 0), (40, 0)]:
        b = dict(base)
        q = Quaternion((0, 1, 0), math.radians(a * 0.7))
        b[head] = base[head] @ q.to_matrix().to_4x4()
        qn = Quaternion((0, 1, 0), math.radians(a * 0.3))
        b[neck] = base[neck] @ qn.to_matrix().to_4x4()
        keys.append((f, b))
    return keys


def foot_speed(arm, act, foot, fps):
    """Ground speed of an in-place cycle: how fast the foot moves back while it is down."""
    use_action(arm, act)
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    pts = []
    for f in range(f0, f1 + 1):
        bpy.context.scene.frame_set(f)
        p = arm.matrix_world @ arm.pose.bones[foot].head
        pts.append((p.y, p.z))
    low = min(z for _, z in pts)
    v = [abs(pts[i + 1][0] - pts[i][0]) * fps for i in range(len(pts) - 1)
         if pts[i][1] < low + 0.02 * (max(z for _, z in pts) - low + 1e-6) + 0.01 and pts[i + 1][1] < low + 0.05]
    v.sort()
    use_action(arm, None)
    return v[len(v) // 2] if v else 0.0


def build_rig(rid):
    rig = RIGS[rid]
    objs = import_outfit(rig, RIG_SOURCE[rid])
    arm = next(o for o in objs if o.type == 'ARMATURE')
    for o in list(bpy.data.objects):
        if o is not arm:
            bpy.data.objects.remove(o, do_unlink=True)
    clear_anim(arm)
    relax_fingers(arm, [], rig)
    s = HEIGHT[rig] / TOP[rig]
    fps = bpy.context.scene.render.fps
    acts = {}
    for clip, src in CLIPS[rig].items():
        if src:
            a = bpy.data.actions.get(src)
            if a is None:
                raise SystemExit(f'{rid}: no action {src}')
            acts[clip] = a
    idle0 = pose_from(arm, acts['idle'], 0)
    sit = sit_pose(arm, idle0, s, poles='PT.')
    acts['sit'] = new_action(arm, 'sit', [(0, sit), (1, sit)])
    acts['emote-no'] = new_action(arm, 'emote-no', head_shake(arm, idle0))
    meta = {'walk_speed': foot_speed(arm, acts['walk'], 'Foot.L', fps) * s,
            'run_speed': foot_speed(arm, acts['sprint'], 'Foot.L', fps) * s,
            'seat': SEAT}
    prune_actions(acts.values(), drop=is_umc_finger)
    for a in acts.values():
        for fc in fcurves(a):
            for k in fc.keyframe_points:
                k.interpolation = 'LINEAR'
    return finish_rig(rid, arm, acts, s, meta)


def finish_rig(rid, arm, acts, s, meta):
    for a in list(bpy.data.actions):
        if a not in acts.values():
            bpy.data.actions.remove(a)
    for clip, a in acts.items():
        a.name = clip
        a.use_fake_user = True
    clear_anim(arm)
    scale_rig(arm, s)
    arm.name = rid
    arm.data.name = rid
    for k, v in meta.items():
        arm[k] = round(v, 3)
    # the exporter takes the actions that fit the armature; give each a slot bound to it
    for a in acts.values():
        use_action(arm, a)
    use_action(arm, None)
    return [arm]


# ---------- the written .glb: smaller skin weights ----------

def write_glb(path, j, bin_):
    js = json.dumps(j, separators=(',', ':')).encode('utf8')
    js += b' ' * (-len(js) % 4)
    bin_ += b'\0' * (-len(bin_) % 4)
    with open(path, 'wb') as fh:
        fh.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_)))
        fh.write(struct.pack('<II', len(js), 0x4E4F534A) + js)
        fh.write(struct.pack('<II', len(bin_), 0x004E4942) + bin_)


def quantize_weights(path):
    """WEIGHTS_0 as normalized unsigned bytes (core glTF) instead of floats: a quarter of the size."""
    with open(path, 'rb') as fh:
        d = fh.read()
    n = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + n])
    bin_ = d[20 + n + 8:]
    views = [bytes(bin_[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]) for v in j['bufferViews']]
    done = set()
    for m in j.get('meshes', []):
        for prim in m['primitives']:
            ai = prim['attributes'].get('WEIGHTS_0')
            if ai is None or ai in done:
                continue
            acc = j['accessors'][ai]
            if acc['componentType'] != 5126 or acc.get('byteOffset', 0) or j['bufferViews'][acc['bufferView']].get('byteStride'):
                continue
            vals = struct.unpack(f'<{acc["count"] * 4}f', views[acc['bufferView']][:acc['count'] * 16])
            out = bytearray()
            for i in range(acc['count']):
                w = vals[i * 4:i * 4 + 4]
                t = sum(w) or 1.0
                q = [int(round(x / t * 255)) for x in w]
                q[q.index(max(q))] += 255 - sum(q)       # the bytes add up to exactly 255
                out += bytes(q)
            views[acc['bufferView']] = bytes(out)
            acc['componentType'] = 5121
            acc['normalized'] = True
            acc.pop('min', None)
            acc.pop('max', None)
            done.add(ai)
    blob = bytearray()
    for v, data in zip(j['bufferViews'], views):
        blob += b'\0' * (-len(blob) % 4)
        v['byteOffset'] = len(blob)
        v['byteLength'] = len(data)
        blob += data
    j['buffers'][0]['byteLength'] = len(blob)
    write_glb(path, j, bytes(blob))


def slim_texcoords(path):
    """TEXCOORD_0 only where a part has a face on the atlas, and there as normalized unsigned shorts: the parts that
    lie wholly on the blank cell go without (web/src/characters.js puts them there)."""
    with open(path, 'rb') as fh:
        d = fh.read()
    n = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + n])
    bin_ = d[20 + n + 8:]
    views = [bytes(bin_[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]) for v in j['bufferViews']]
    drop = set()
    for m in j.get('meshes', []):
        for prim in m['primitives']:
            ai = prim['attributes'].get('TEXCOORD_0')
            if ai is None:
                continue
            acc = j['accessors'][ai]
            if acc['componentType'] != 5126 or acc.get('byteOffset', 0) or j['bufferViews'][acc['bufferView']].get('byteStride'):
                continue
            vals = struct.unpack(f'<{acc["count"] * 2}f', views[acc['bufferView']][:acc['count'] * 8])
            if all(abs(vals[i] - BLANK_UV[0]) < 1e-4 and abs(vals[i + 1] - (1 - BLANK_UV[1])) < 1e-4 for i in range(0, len(vals), 2)):
                del prim['attributes']['TEXCOORD_0']
                drop.add(ai)
                continue
            views[acc['bufferView']] = struct.pack(f'<{len(vals)}H', *(min(65535, max(0, round(v * 65535))) for v in vals))
            acc['componentType'] = 5123
            acc['normalized'] = True
            acc.pop('min', None)
            acc.pop('max', None)
    # the accessors and buffer views left without a user go, the rest are counted anew
    keep = [i for i in range(len(j['accessors'])) if i not in drop]
    amap = {old: new for new, old in enumerate(keep)}
    vkeep = sorted({j['accessors'][i]['bufferView'] for i in keep})
    vmap = {old: new for new, old in enumerate(vkeep)}
    for m in j.get('meshes', []):
        for prim in m['primitives']:
            prim['attributes'] = {k: amap[v] for k, v in prim['attributes'].items()}
            if 'indices' in prim:
                prim['indices'] = amap[prim['indices']]
    for sk in j.get('skins', []):
        if 'inverseBindMatrices' in sk:
            sk['inverseBindMatrices'] = amap[sk['inverseBindMatrices']]
    if j.get('animations') or j.get('images'):
        raise SystemExit(f'{path}: a person with animations or images')
    j['accessors'] = [dict(j['accessors'][i], bufferView=vmap[j['accessors'][i]['bufferView']]) for i in keep]
    blob = bytearray()
    out = []
    for old in vkeep:
        v = dict(j['bufferViews'][old])
        blob += b'\0' * (-len(blob) % 4)
        v['byteOffset'] = len(blob)
        v['byteLength'] = len(views[old])
        blob += views[old]
        out.append(v)
    j['bufferViews'] = out
    j['buffers'][0]['byteLength'] = len(blob)
    write_glb(path, j, bytes(blob))


# ---------- checks on the written .glb ----------

def read_glb(path):
    with open(path, 'rb') as fh:
        d = fh.read()
    n = struct.unpack('<I', d[12:16])[0]
    return json.loads(d[20:20 + n])


def check(pid, path):
    j = read_glb(path)
    problems = []
    if j.get('images'):
        problems.append('has images')
    names = [n.get('name') for n in j.get('nodes', [])]
    anims = sorted(a['name'] for a in j.get('animations', []))
    if pid in RIGS:
        want = sorted(CLIPS[RIGS[pid]])
        if anims != want:
            problems.append(f'animations {anims}, expected {want}')
        if j.get('meshes'):
            problems.append('rig has a mesh')
    else:
        if anims:
            problems.append(f'person has animations {anims}')
        if len(j.get('meshes', [])) != 1 or len(j.get('skins', [])) != 1:
            problems.append(f'{len(j.get("meshes", []))} meshes, {len(j.get("skins", []))} skins')
        if pid not in names or pid + '-mesh' not in names:
            problems.append('node names')
        prims = [prim for m in j.get('meshes', []) for prim in m['primitives']]
        if sum('TEXCOORD_0' in prim['attributes'] for prim in prims) != 1 or any('TEXCOORD_1' in prim['attributes'] for prim in prims):
            problems.append('texture coordinates (the skin alone has a face on the atlas)')
    return problems


# ---------- main ----------

def face_atlas():
    """faces.png: everybody's face in the order of PEOPLE (the cells face_map lays the faces on)."""
    rows = []
    for sp in PEOPLE.values():
        col = sp['colors']
        hair, skin = col.get('Hair', HAIR['black']), col.get('Skin', SKIN['b'])
        rows.append((sp['rig'], sp.get('face', {}), skin, col.get('Brow', hex_mix(hair, skin, 0.10))))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'faces.png')
    faces.write_atlas(path, rows)
    print(f'faces: png {os.path.getsize(path) // 1024} KB  ({len(rows)} faces, {faces.GRID * faces.CELL} px)')


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    keep = None
    if '--keep-glb' in argv:
        i = argv.index('--keep-glb')
        keep = argv[i + 1]
        del argv[i:i + 2]
    if '--list' in argv:
        for pid, sp in PEOPLE.items():
            src = ', '.join(f'{k} {v}' for k, v in sp['parts'].items()) + ', hair ' + sp['hair']
            print(f'{pid:20} rig-{sp["rig"]:6} {src:88} {sp["note"]}')
        for rid, r in RIGS.items():
            print(f'{rid:20} clips {", ".join(f"{k}<-{v or "made here"}" for k, v in CLIPS[r].items())}')
        return
    wanted = []
    for a in argv:
        if a.startswith('--'):
            continue
        wanted += ([p for p in PEOPLE if p.startswith('man-')] if a == 'men' else
                   [p for p in PEOPLE if p.startswith('woman-')] if a == 'women' else list(RIGS) if a == 'rigs' else
                   [] if a == 'faces' else [a])
    unknown = [w for w in wanted if w not in PEOPLE and w not in RIGS]
    if unknown:
        raise SystemExit('unknown id(s): ' + ', '.join(unknown))
    todo = wanted or ([] if 'faces' in argv else list(RIGS) + list(PEOPLE))
    os.makedirs(OUT, exist_ok=True)
    if 'faces' in argv or any(pid in PEOPLE for pid in todo):
        face_atlas()
    tmp = keep or tempfile.mkdtemp()
    os.makedirs(tmp, exist_ok=True)
    failed = []
    for pid in todo:
        reset()
        rig = RIGS.get(pid) or PEOPLE[pid]['rig']
        pack = {'umc': 'Quaternius Ultimate Modular Men', 'women': 'Quaternius Ultimate Modular Women'}[rig]
        if pid in RIGS:
            objs, src = build_rig(pid), f'{pack} ({RIG_SOURCE[pid]}{SRC[rig][1]} animations)'
        else:
            objs = build_person(pid, PEOPLE[pid])
            src = f'{pack} (' + ', '.join(sorted({v + SRC[rig][1] for v in PEOPLE[pid]['parts'].values()})) + ')'
        path = os.path.join(tmp, pid + '.glb')
        if os.environ.get('SO_SAVE_BLEND'):          # debugging: keep the built scene
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.environ['SO_SAVE_BLEND'], pid + '.blend'))
        export_glb(path, objs, pid in RIGS)
        if not os.environ.get("SO_NO_QUANT"):
            quantize_weights(path)
            if pid in PEOPLE:
                slim_texcoords(path)
        problems = check(pid, path)
        os.makedirs(OUT, exist_ok=True)
        import shutil
        shutil.copyfile(path, os.path.join(OUT, pid + '.glb'))
        print(f'{pid}: glb {os.path.getsize(path) // 1024} KB  ({src})' + ('' if not problems else '  PROBLEMS: ' + '; '.join(problems)))
        if problems:
            failed.append(pid)
    if failed:
        raise SystemExit('failed: ' + ', '.join(failed))


main()
