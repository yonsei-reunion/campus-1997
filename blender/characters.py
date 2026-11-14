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
colour materials only, texture coordinates into faces.png, the vertex attributes _OCC: how shut in a vertex is, and
_LEG: its place on a trouser leg), faces(_rims).png and rig-umc.glb / rig-women.glb with the
clips idle walk sprint sit emote-yes emote-no interact-right and glTF extras walk_speed / run_speed (m/s of the feet
in the walk / run cycle).

Most clips are motion capture retargeted by blender/mocap.py (its CLIPS: walk, idle, sprint, sit over the pack's, and
walk-slow walk-fast idle-shift idle-look idle-fold talk phone sit-talk), from the takes that
tools/fetch_mocap.py puts in assets_src/mocap/. The rig's extras also carry 'speeds': {clip: m/s} of every cycle.
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
import mocap  # noqa: E402
faces_mod = faces              # (the module, inside functions that have a list of faces)
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
LIMIT = {'person': 400 * 1024, 'rig': 400 * 1024}   # base64 bytes

# engine clip name -> source action (None: made here)
CLIPS = {
    'umc': {'idle': 'Idle_Neutral', 'walk': 'Walk', 'sprint': 'Run', 'sit': None, 'emote-yes': 'Wave', 'emote-no': None,
            'interact-right': 'Interact'},
    'women': {'idle': 'Idle_Neutral', 'walk': 'Walk', 'sprint': 'Run', 'sit': None, 'emote-yes': 'Wave', 'emote-no': None,
              'interact-right': 'Interact'},
}
for _rig, _clips in CLIPS.items():       # the clips of blender/mocap.py: new names here, the others replace the pack's
    _clips.update({_c: None for _c in mocap.CLIPS[_rig] if _c not in _clips})
RIG_SOURCE = {'rig-umc': 'Suit', 'rig-women': 'Casual'}     # the outfit file whose animations make the rig

# ---------- the people ----------
# colours are sRGB hex. A key 'Mat' recolours that material everywhere, 'part:Mat' only on that part (head, body, legs, feet).
SKIN = {'a': '#f0c9a4', 'b': '#e6b991', 'c': '#d9a77d', 'd': '#c99168',         # East Asian skin tones
        'fair': '#f7ddc8', 'tan': '#b9825a'}                                    # and one fair, one tanned (가무잡잡)
HAIR = {'black': '#141110', 'dark': '#2b1f18', 'brown': '#5a3a24', 'dyed': '#7a4a26', 'grey': '#8e8b88'}
# denim of 1997, told apart from across a lawn: dark (진청, hardly washed), mid, light (연청, stone-washed) and black
# (블랙진, washed to charcoal).  web/src/characters.js JEANS / WASH has the same four
JEANS = {'mid': '#44628f', 'dark': '#1e2b4a', 'light': '#8fabcc', 'black': '#26272b'}
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


def trainers(rig, upper):
    """`paint` for a pair of trainers of 1997 on the packs' plain shoes (material `upper`): two bars down the outer
    side and a tab at the heel in the colour 'feet:Bar', the laces over the instep ('feet:Lace'); the women's shoes,
    which come without one, a sole ('feet:Sole').  Boxes in the source's T pose: the toes at y -0.29 (women -0.27),
    a foot's middle at x 0.134 (women 0.090)."""
    if rig == 'umc':
        return [dict(of=(upper,), to='Bar', x=(.134, None), y=(-.188, -.166), z=(.032, .072)),
                dict(of=(upper,), to='Bar', x=(.134, None), y=(-.150, -.128), z=(.032, .078)),
                dict(of=(upper,), to='Bar', y=(-.034, None), z=(.052, .118)),
                dict(of=(upper,), to='Lace', x=(.112, .155), y=(-.218, -.122), z=(.062, None))]
    return [dict(of=(upper,), to='Sole', z=(None, .020)),
            dict(of=(upper,), to='Bar', x=(.090, None), y=(-.176, -.157), z=(.024, .050)),
            dict(of=(upper,), to='Bar', x=(.090, None), y=(-.142, -.123), z=(.024, .056)),
            dict(of=(upper,), to='Bar', y=(-.022, None), z=(.040, .090)),
            dict(of=(upper,), to='Lace', x=(.070, .112), y=(-.205, -.112), z=(.050, None))]


def canvas(upper, rubber):
    """`paint` for the men's canvas shoes: a rubber toe cap and the laces in the sole's material `rubber`."""
    return [dict(of=(upper,), to=rubber, y=(None, -.246)),
            dict(of=(upper,), to=rubber, x=(.114, .153), y=(-.222, -.130), z=(.058, None))]


# 1997 campus fashion (reference/고증 4.11): baggy stone-washed jeans and wide trousers, big tees and hoodies, a collared
# tee in broad stripes, a jumper with a dark collar, a blazer over cotton trousers, the Yonsei-blue cheer jacket, a white
# knit over a black skirt, a cropped tee, a pastel cardigan, a professor in a grey suit, staff in work vests.
# Hair (the first name, see HAIR_STYLES) and faces as students wore and had them about 1997 (reference/고증 4.9): most
# of them plain, a few the cuts of the year.  Optional: flip (the parting on the other side), bridge (bleached locks:
# [(azimuth, half width)]), face: what makes the one shared face a person's own.  Of the skull: jaw, chin (scales).
# Of the drawn lines (faces.py): lid (mono 홑꺼풀, inner 속쌍꺼풀, double 쌍꺼풀), slant (the outer corner of the eye
# higher, of the eye's half width), eye, brow, mouth, lash, lip (scales), brow_tilt (the tail higher), arch (of the
# brow, a scale), smile (the corners of the mouth up, m), age ('mid', 'old': the lines of an older face).  glasses:
# who wears them as the model is (everybody has a pair: the game shows or hides it, web/src/characters.js).  prints:
# lettering on a part (see 'what is printed' below).  Of the
# brows also brow_len, brow_gap, brow_up, brow_peak, brow_corner, brow_drop, brow_taper, brow_soft (faces.py), of the
# nose nose, bridge, nose_curve, nose_w, nose_up (NOSE below).  paint: parts of the outfit in colours of their own
# (see '1997 wardrobe').
PEOPLE = {
    # 승민 (the film 건축학개론, 2012: a first-year of 1996 in the knock-off sweatshirt): a long, quiet face with narrow
    # single-lidded eyes under straight heavy brows, a straight nose, a mouth that does not smile
    'man-tee': man('fringe', 'Casual_2', 'Casual_2', 'Casual_2',
                   {'LightBrown': '#f1efe8', 'LightBlue': JEANS['light'], 'Red_Dark': '#e8e6e0', 'feet:White': '#c9c6be',
                    'feet:Bar': '#27345a', 'feet:Lace': '#cfccc4', 'Skin': SKIN['b'], 'Hair': HAIR['black']},
                   'white long-sleeved tee with the GEUSS triangle, baggy light jeans, white trainers; short hair, the '
                   'fringe down over the forehead',
                   paint={'body': [dict(of=('Skin',), to='LightBrown', x=(0, .592))], 'feet': trainers('umc', 'Red_Dark')},
                   prints={'body': [dict(name='geuss', of=('LightBrown',), w=.28, z=1.33)]}, cut='wide',
                   face=dict(lid='mono', slant=.07, eye=.94, jaw=.94, chin=1.06, brow=1.3, brow_tilt=-.03, arch=.4, brow_len=1.02,
                             brow_taper=1.3, brow_soft=1.6, smile=.0004, mouth=.94, nose=1.04, bridge=.38, nose_curve=1.1,
                             nose_w=.94)),
    'man-check': man('short', 'Casual_2', 'Casual_2', 'Casual_2',
                     {'LightBrown': '#1f2f55', 'Stripe': '#1f8580', 'Stripe2': '#d8742c', 'Collar': '#ece8dc',
                      'LightBlue': JEANS['dark'], 'Red_Dark': '#3a2c24', 'Skin': SKIN['c'], 'Hair': HAIR['black']},
                     'collared tee in broad navy, teal and orange stripes, wide dark jeans (진청); neat short hair, metal glasses',
                     paint={'body': bands('Stripe', ('LightBrown',), [(1.085, 1.150), (1.280, 1.345)], x=(0, .21))
                            + bands('Stripe2', ('LightBrown',), [(1.185, 1.245), (1.380, 1.440)], x=(0, .21))
                            + [dict(of=('LightBrown',), to='Collar', x=(0, .10), z=(1.495, None))]}, cut='wide',
                     face=dict(lid='mono', slant=.10, jaw=1.04, eye=.96, smile=.0016, mouth=.96, glasses=True, brow=1.3, arch=.4,
                               brow_len=.86, brow_taper=1.6, nose=.84, bridge=.24, nose_w=1.10)),
    'man-hoodie': man('up', 'Casual_Hoodie', 'Casual_2', 'Casual_Hoodie',
                      {'Purple': '#23345e', 'LightBlue': '#a8946a', 'feet:White': '#e8e6e0', 'Skin': SKIN['tan'],
                       'Hair': HAIR['black'], 'Brow': '#0e0b0a'},
                      'oversized navy hoodie, wide khaki cargo trousers, canvas shoes; short hair swept up and back, the sides '
                      'and the back run over with clippers (the scalp shows through), tanned',
                      paint={'feet': canvas('Purple', 'White')},
                      face=dict(lid='mono', slant=.14, jaw=.97, eye=.98, smile=.0027, mouth=1.08, brow=1.5, brow_tilt=.09,
                                brow_corner=True, brow_peak=.70, brow_drop=1.2, brow_taper=1.3, brow_soft=1.4, nose=1.04,
                                bridge=.40, nose_curve=1.3)),
    # 성구 (the maker's request: the look of an actor and singer born in 1978, from memory): a long face with a firm
    # jaw, large eyes with double lids under heavy straight brows set low, a high straight nose, a wide ready smile
    'man-cheer': man('two-block', 'Casual_Hoodie', 'Casual_2', 'Casual_2',
                     {'Purple': '#1d3fa0', 'LightBlue': JEANS['black'], 'Red_Dark': '#f2f2ee', 'feet:Bar': '#1d3fa0',
                      'feet:Lace': '#d6d3cc', 'Skin': SKIN['c'], 'Hair': HAIR['black']},
                     'Yonsei-blue jumper, YONSEI in white across the chest, black jeans, white trainers; a two-block cut, '
                     'the long top swept from a 7:3 parting',
                     paint={'feet': trainers('umc', 'Red_Dark')}, cut='wide',
                     prints={'body': [dict(name='yonsei', of=('Purple',), w=.27, z=1.36)]},
                     face=dict(lid='double', slant=.0, jaw=1.03, chin=1.09, eye=1.04, mouth=1.15, smile=.0034, lip=1.1,
                               brow=1.6, arch=.75, brow_len=1.1, brow_peak=.6, brow_up=-.0014, brow_taper=1.5, brow_soft=1.5,
                               nose=1.13, bridge=.45, nose_curve=1.15, nose_w=1.02)),
    'man-grey': man('curtain-64', 'Casual_Hoodie', 'Casual_2', 'Casual_Hoodie',
                    {'Purple': '#e8e0b0', 'Collar': '#3b3a3c', 'LightBlue': JEANS['mid'],
                     'feet:Purple': '#2a2a2e', 'Skin': SKIN['b'], 'Hair': HAIR['dyed'], 'Brow': '#1c1410'},
                    'pale yellow jumper with a dark collar, jeans; brown-dyed hair parted 6:4',
                    paint={'body': [dict(of=('Purple',), to='Collar', x=(0, .10), z=(1.495, None))],
                           'feet': canvas('Purple', 'White')},
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
    'woman-tee': woman('half', 'Casual', 'Casual', 'Casual',
                       {'White': '#f4f1e8', 'Orange': JEANS['light'], 'Grey': '#e8e6e0', 'feet:Bar': '#b3262e', 'feet:Lace': '#cfccc4',
                        'feet:Sole': '#c9c6be', 'Skin': SKIN['a'], 'Hair': HAIR['black']},
                       'loose white tee with YONSEI in blue across the chest, wide light jeans (연청), white trainers; long '
                       'black hair, the top half tied back',
                       paint={'feet': trainers('women', 'Grey')}, cut='wide',
                       prints={'body': [dict(name='yonsei_ink', of=('White',), w=.22, z=1.40)]},
                       face=dict(lid='inner', slant=.07, eye=1.03, jaw=1.03, smile=.0030, brow=.9, arch=1.35, brow_peak=.58, brow_len=1.05, brow_up=-.002, brow_soft=1.3,
                                 nose=.80, bridge=.28, nose_w=.96, nose_up=.001)),
    'woman-pink': woman('tuck', 'Casual', 'Casual', 'Casual',
                        {'White': '#e7a7b6', 'Orange': '#cdb994', 'Grey': '#f0eee8', 'feet:Bar': '#8d8f92', 'feet:Lace': '#d6d3cc',
                         'feet:Sole': '#cfccc4', 'Skin': SKIN['fair'], 'Hair': HAIR['dark']},
                        'pink knit, wide beige trousers, white trainers; short bob, one side behind the ear',
                        paint={'feet': trainers('women', 'Grey')},
                        face=dict(lid='inner', slant=.03, jaw=1.04, brow_tilt=-.04, smile=.0030, mouth=.96, brow=1.25, arch=.4, brow_len=.88, brow_taper=1.5,
                                  nose=.72, bridge=.24, nose_w=1.02, nose_up=.002)),
    # 서연 (the film 건축학개론, 2012: a first-year of the college of music in 1996): a round, soft face, large eyes with
    # double lids, straight soft brows, a small nose, a ready smile; long straight hair worn down
    'woman-dress': woman('long', 'Formal', 'Formal', 'Formal',
                         {'LimeGreen': '#f1ede1', 'Skirt': '#1f1f24', 'feet:Red': '#1c1c1f', 'Skin': SKIN['fair'],
                          'Hair': HAIR['black']},
                         'white knit with long sleeves, black skirt, black shoes; long straight black hair',
                         paint={'body': [dict(of=('Skin',), to='LimeGreen', x=(0, .585)),       # (a round neck, at the neck's foot)
                                         dict(of=('Gold',), to='Skirt')],
                                'legs': [dict(of=('LimeGreen',), to='Skirt')]},
                         face=dict(lid='double', slant=.04, eye=1.12, lash=1.15, jaw=1.03, brow=.95, arch=.35, brow_len=1.05,
                                   brow_soft=2.0, smile=.0031, mouth=.98, lip=1.15, nose=.74, bridge=.26, nose_w=.94,
                                   nose_up=.0015)),
    'woman-dress-blue': woman('shoulder', 'Punk', 'Casual', 'Casual',
                              {'Pink': '#a9c6e6', 'Orange': JEANS['black'], 'Grey': '#1f1f24', 'Skin': SKIN['b'],
                               'Hair': HAIR['brown'], 'Bridge': '#9c6c3a', 'Brow': HAIR['dark']},
                              'tight sky-blue cropped tee (배꼽티), wide black jeans; brown-dyed hair to the shoulders, bleached locks',
                              bridge=[(-18, 3.5), (46, 3.5)],
                              paint={'body': [dict(of=('Pink',), to='Skin', z=(None, 1.20)),
                                              dict(of=('Black',), to='Skin', x=(.30, None)),
                                              dict(of=('Black',), to='Skin', x=(0, .09), z=(1.47, None)),
                                              dict(of=('Black',), to='Pink')]}, cut='wide',
                              face=dict(lid='double', slant=.10, eye=.99, jaw=.98, smile=.0022, brow=.85, arch=1.6, brow_tilt=.05, brow_up=-.0015, brow_corner=True,
                                        brow_peak=.68, brow_drop=1.0, brow_soft=1.3, nose=.84, bridge=.32, nose_w=.95)),
    'woman-cardigan': woman('pixie', 'Suit', 'Casual', 'Casual',
                            {'Black': '#ecdf9e', 'White': '#f2efe6', 'Orange': JEANS['dark'], 'Grey': '#f0eee8', 'feet:Bar': '#27345a',
                             'feet:Lace': '#d6d3cc', 'feet:Sole': '#cfccc4', 'Skin': SKIN['c'], 'Hair': HAIR['black']},
                            'pastel yellow cardigan over a white tee, dark jeans (진청), white trainers; a short cut swept back over '
                            'the ears, metal glasses',
                            paint={'feet': trainers('women', 'Grey')},
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
# A hand at rest is half closed. The packs' relaxed hand is a flat one with the fingers spread: each finger is bent
# further at the knuckle, the middle and the last joint (bones 2-4: bone 1 is the metacarpal, from the wrist to the
# knuckle, and bending it folds the palm), the little finger most, the thumb a little in under the palm.
FINGER_CURL = (20, 34, 22)                   # degrees
FINGER_MORE = {'Index': .8, 'Middle': 1.0, 'Ring': 1.12, 'Pinky': 1.25, 'Thumb': .45}
# The packs' build is a doll's: narrow shoulders (the joints 28 cm apart on the men, 21 cm on the women, where grown
# people have about 33 and 29 cm), short arms (span 1.56 m at 1.71 m of height) and the men's hip joints wide apart
# (22 cm for about 17).  Metres in the game's scale, each side: the shoulder joints out, the hip joints (and the feet
# under them) in; the upper arm and the forearm longer by `arm`.
# Hands like gloves (a middle finger of 11.4 cm, 2.7 cm thick at its root, where a man's is about 8 by 2): the hand
# smaller about the wrist by `hand`, every finger again about its knuckle by `finger`.
# A neck 8.7 cm wide (men; 7 cm women) for about 11.5 and 9.5: wider by `neck` at its foot, less under the jaw (the
# head keeps its size).  The women's waist 21 cm wide under hips of 30: wider by `waist`, clothes and skin alike.
# The shoulders are a level board with the neck stood on it (from the neck's foot the outline runs out 8 cm in the
# first centimetre down): no trapezius.  `trap` raises what lies round the neck's foot, at its sides and behind it
# (not in front, where the collarbones are): by (m, the source's units) at the neck's own radius, easing to nothing
# at the outer radius (short of the shoulder joint: what the upper arm holds is left alone, or it would swing out
# with the arm), so the shoulder line runs up into the neck in a curve and less of the neck stands free.
BUILD = {'umc': dict(shoulder=.020, hip=-.022, arm=1.06, hand=.88, finger=.88, neck=.25, waist=0.0, trap=(.030, .056, .140)),
         'women': dict(shoulder=.030, hip=0.0, arm=1.06, hand=.88, finger=.88, neck=.38, waist=.14, trap=(.030, .048, .112))}
# The packs' clips hold the arms away from the body (the standing, walking and sitting clips are motion capture now,
# blender/mocap.py; the pack's wave and reach are kept).  The arm that is not gesturing in toward the body, as the
# standing clips hold it: clip -> the side, degrees in, degrees the forearm is turned about its length
ARMS_IN = {'umc': {'emote-yes': ('R', 7, 0), 'interact-right': ('L', 7, 0)},
           'women': {'emote-yes': ('R', 9, 45), 'interact-right': ('L', 9, 45)}}


def is_umc_finger(name):
    return name.startswith(UMC_FINGERS)


def _shift(pb, v):
    pb.matrix = Matrix.Translation(v) @ pb.matrix
    bpy.context.view_layer.update()


def relax_fingers(arm, meshes, rig, s):
    """Make the fingers' pose in the first idle frame (a relaxed hand), bent further (FINGER_CURL), their rest pose, and
    the build of BUILD the rest of the shoulders, arms, hips and feet: in the meshes and the bones.  The clips need no
    finger channels (the rig drops them), and the rig and every person of it do the same, so they match.
    s: the scale the rig is baked to afterwards (BUILD is in the game's metres)."""
    idle = bpy.data.actions.get(CLIPS[rig]['idle'])
    if idle is None:
        raise SystemExit('no idle action for the fingers')
    use_action(arm, idle)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    basis = {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones if is_umc_finger(pb.name)}
    use_action(arm, None)
    # (a connected bone takes no translation in a pose: the ones moved below let go of their parents' tails)
    moved = [n + side for n in ('UpperArm.', 'LowerArm.', 'Wrist.', 'UpperLeg.') for side in 'LR']
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for n in moved:
        arm.data.edit_bones[n].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in arm.pose.bones:
        pb.matrix_basis = basis.get(pb.name, Matrix.Identity(4))
    bpy.context.view_layer.update()
    P = arm.pose.bones
    for pb in P:                                   # (parents first)
        if not is_umc_finger(pb.name):
            continue
        finger = next(f for f in UMC_FINGERS if pb.name.startswith(f))
        k = int(pb.name[len(finger)]) - 2
        if k < 0 or k > 2:
            continue
        side = 1 if pb.name.endswith('L') else -1
        deg = FINGER_CURL[k] * FINGER_MORE[finger]
        # the T pose, palms down: the fingers bend down about the model's front-back axis, the thumb in about the upright
        rotate_about_head(pb, 'Z' if finger == 'Thumb' else 'Y', (-side if finger == 'Thumb' else side) * deg)
    b = BUILD[rig]
    for side, sx in (('L', 1), ('R', -1)):
        ua, la, wr = P['UpperArm.' + side], P['LowerArm.' + side], P['Wrist.' + side]
        upper, fore = la.head - ua.head, wr.head - la.head          # (before anything moves)
        _shift(ua, Vector((sx * b['shoulder'] / s, 0, 0)))
        _shift(la, upper * (b['arm'] - 1))
        _shift(wr, fore * (b['arm'] - 1))
        if b['hip']:
            for n in ('UpperLeg.', 'Foot.', 'PT.'):
                if P.get(n + side):
                    _shift(P[n + side], Vector((sx * b['hip'] / s, 0, 0)))
        wr.scale = (b['hand'],) * 3                                   # (after the shifts: they set the whole matrix)
        for finger in UMC_FINGERS:
            P[f'{finger}2.{side}'].scale = (b['finger'],) * 3
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
    bpy.ops.pose.armature_apply(selected=False)          # (every other bone is at rest)
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)


def shape_body(ob, arm, rig):
    """The neck, the trapezius and the waist of BUILD on one part of a person, in the source's T pose: the bones stay where they
    are.  Both by place alone (the height, and for the neck how far from its axis), so that the head's neck, the neck's
    foot on the body, the collar round it and the hair on it move as one: by the bones' weights the neck stood out
    over its own foot (a step half way up) and through the rim of a tee's collar."""
    b = BUILD[rig]
    me, mw = ob.data, ob.matrix_world.copy()
    inv = mw.inverted()
    head = lambda name: arm.matrix_world @ arm.data.bones[name].head_local
    cn, zh = head('Neck'), head('Head').z
    zn = cn.z
    zw, sw = (head('Abdomen').z + head('Torso').z) / 2, 0.09
    tr = b.get('trap')
    arms = {g.index for g in ob.vertex_groups if g.name.startswith(('UpperArm.', 'LowerArm.', 'Wrist.'))}
    for v in me.vertices:
        c = mw @ v.co
        if b['waist'] and abs(c.x) < .3:
            f = b['waist'] * math.exp(-((c.z - zw) / sw) ** 2)
            c.x *= 1 + f
            c.y = cn.y + (c.y - cn.y) * (1 + .3 * f)
        if b['neck'] and zn - .05 < c.z < zh + .02:
            # all of it from the collarbone up, less under the jaw (the head keeps its size), nothing a hand's width out
            up = _smooth(zn - .05, zn - .015, c.z) * (1 - .7 * _smooth((zn + zh) / 2, zh, c.z)) * (1 - _smooth(zh, zh + .02, c.z))
            f = b['neck'] * up * (1 - _smooth(.075, .11, math.hypot(c.x, c.y - cn.y)))
            c.x *= 1 + f
            c.y = cn.y + (c.y - cn.y) * (1 + .5 * f)
        if tr and zn - .08 < c.z < zh + .03:
            r = math.hypot(c.x, c.y - cn.y)
            if r < tr[2]:
                # (full from the collarbones up to the neck's foot, fading up the neck so slowly that nothing folds)
                up = _smooth(zn - .08, zn - .035, c.z) * (1 - _smooth(zn, zh + .03, c.z)) * _smooth(-.055, -.012, c.y - cn.y)
                held = sum(g.weight for g in v.groups if g.group in arms)
                c.z += tr[0] * (1 - _smooth(tr[1], tr[2], r)) * up * (1 - min(1.0, held))
        v.co = inv @ c


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
                              export_cameras=False, export_lights=False, export_def_bones=False, export_leaf_bone=False,
                              export_attributes=not animations)          # (the people's _OCC)


# ---------- people ----------

def mesh_name(rig, outfit, part):
    return MESH_NAME.get((rig, outfit, part)) or MESH_PREFIX.get(outfit, outfit) + PART_MESH[part]


# ---------- 1997 cut: oversized tops ----------
# Late-90s Korean campus fashion: wide hip-hop jeans and roomy pleated trousers that pile up on the shoes, big
# sweatshirts, hoodies and tees.  The source outfits are slim, so the tops are loosened around each limb's own centre
# line (skin, i.e. hands and faces, is never touched; long dresses are left alone); the trousers are cut anew
# (cut_trousers below).
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


# The collar stays with the neck: loosened with the rest of a top it gaped a finger's width off it all round (a hood
# may).  The packs' tees have a rim standing 3 - 4 cm up the neck, level all round: COLLAR brings it down (the share
# of its height that is left) and dips it at the front (m, the source's units), as a round neck lies.
OPEN_NECK = ('Casual_Hoodie',)
COLLAR = {'Casual_2': (.45, .010), 'Worker': (.45, .010)}


def loosen(ob, part, outfit, arm):
    """Widen the top (body) of one outfit part, in world space."""
    F = ROOMY.get(outfit, 1.0) if part == 'body' else 1.0
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
    cn = arm.matrix_world @ arm.data.bones['Neck'].head_local
    keep, low = outfit not in OPEN_NECK, COLLAR.get(outfit)
    for i, c in co.items():
        a = _smooth(torso_w * 0.8, torso_w * 1.25, abs(c.x))     # 0 torso .. 1 sleeve
        h = (c.z - zb) / H
        r = math.hypot(c.x, c.y - cn.y)
        collar = (1 - _smooth(.085, .12, r)) * _smooth(cn.z - .03, cn.z, c.z) if keep else 0.0
        if a < 1 and tkey(c) in tcen:
            tx, ty, _ = tcen[tkey(c)]
            ft = 1 + (F - 1) * (1 - a) * (0.8 + 0.3 * (1 - h)) * (1 - collar)    # a little roomier toward the hem
            c.x = tx + (c.x - tx) * ft if abs(c.x) < torso_w else c.x
            c.y = ty + (c.y - ty) * ft
        if a > 0 and akey(c) in acen:
            _, ay, az = acen[akey(c)]
            fa = 1 + (F - 1) * 1.2 * a
            c.y = ay + (c.y - ay) * fa
            c.z = az + (c.z - az) * fa
        if low and collar > 0 and c.z > cn.z:
            c.z -= ((c.z - cn.z) * (1 - low[0]) + low[1] * max(0.0, -(c.y - cn.y) / max(r, 1e-4))) * collar
    for v in me.vertices:
        if v.index in co:
            v.co = inv @ co[v.index]


# ---------- 1997 cut: wide trousers ----------
# The packs' trousers are tights (the women's) or narrow tubes (the men's).  Scaled up about each leg's centre line
# they were wide enough for 1997 but hung from nothing: the waistband and the seat kept the pack's width, and the
# thighs under them stood out 3 - 5 cm a side further than the hips.  Cloth hangs from the widest place down, so the
# trousers are cut by their four outlines - outside, inside (below the crotch), front, back - each the body's own
# outline pulled tight (`hang`: 1 a taut string over the hips, the seat and the knee, 0 the body) plus an ease given at
# the waist, the hip joints, the crotch, the knee and the hem.  A cross-section of a leg (of the hips, above the
# crotch) is fitted between the four.  The outside falls nearly straight from the hips; the legs narrow to the knee
# and the hem on their inside, so the two read apart.  Done on the built rest pose (after BUILD has moved the legs).
# Lengths in the source's units (x 0.93 men, 0.90 women in the game):
#   waist, hip: ease of the outside at the top, and from the hip joints down to the crotch
#   seat, front: ease of the back and the front from the hip joints down to the crotch
#   knee, hem: half the width and half the depth of a leg there;  fwd: the hem pushed forward by the shoe
#   floor, rise: how high the hem ends over the ground at the back, and how much higher at the front (it rests on the
#   shoe there): the leg is drawn out from the knee down
# The cuts, by rig: `regular` the jeans and cotton trousers, `slacks` a suit's, and `wide` the wide jeans of 1997
# (reference/고증 4.11: 긴 일자바지, 힙합바지): wide all the way down, a hem as wide as the
# shoe is long that covers the ankle and all of the shoe but its toes and nearly sweeps the ground behind the heel.
# Who wears the wide ones: PEOPLE's `cut` (about half the students).
CUTS = {
    'umc': {
        'regular': dict(waist=.0, hip=.014, seat=.012, front=.008, knee=(.078, .084), hem=(.076, .092), fwd=.012, hang=.85,
                        floor=.092, rise=.0),
        'wide': dict(waist=.0, hip=.020, seat=.018, front=.012, knee=(.094, .100), hem=(.100, .112), fwd=.020, hang=.9,
                     floor=.030, rise=.046),
        'slacks': dict(waist=.0, hip=.008, seat=.008, front=.006, knee=(.066, .074), hem=(.060, .076), fwd=.008, hang=.8,
                       floor=.110, rise=.0),
    },
    'women': {
        'regular': dict(waist=-.003, hip=.006, seat=.008, front=.006, knee=(.076, .080), hem=(.076, .088), fwd=.010, hang=.85,
                        floor=.105, rise=.0),
        'wide': dict(waist=-.003, hip=.010, seat=.012, front=.008, knee=(.088, .094), hem=(.096, .106), fwd=.016, hang=.9,
                     floor=.028, rise=.040),
        'slacks': dict(waist=-.003, hip=.004, seat=.006, front=.005, knee=(.066, .072), hem=(.062, .078), fwd=.008, hang=.75,
                       floor=.113, rise=.0),
    },
}
TROUSERS = {'Casual_2': 'regular', 'Casual': 'regular', 'Suit': 'slacks'}       # by the outfit of the legs
APART = 0.008                 # half the space between the hems of wide legs (their middles move out for it)
LEG = '_LEG'                  # the vertex attribute of a trouser leg's own coordinates (see cut_trousers)
LEG_TOP = 1.25                # the attribute's height runs 0 (hem) .5 (knee) 1 (hip joint) 1.2 (waistband), kept / LEG_TOP
GAP = 0.004                   # half the space between the legs at the crotch


def _hull(vals, sign):
    """Evenly spaced samples pulled tight from above (sign 1: the least concave curve over them) or below (-1)."""
    pts = []
    for i, v in enumerate(vals):
        v *= sign
        while len(pts) >= 2 and (pts[-1][1] - pts[-2][1]) * (i - pts[-2][0]) <= (v - pts[-2][1]) * (pts[-1][0] - pts[-2][0]):
            pts.pop()
        pts.append((i, v))
    out, k = [], 0
    for i in range(len(vals)):
        while k + 2 < len(pts) and pts[k + 1][0] <= i:
            k += 1
        (i0, v0), (i1, v1) = pts[k], pts[min(k + 1, len(pts) - 1)]
        out.append(sign * (v0 if i1 == i0 else v0 + (v1 - v0) * (i - i0) / (i1 - i0)))
    return out


def _lerp_at(vals, f):
    f = max(0.0, min(len(vals) - 1.0, f))
    i = min(int(f), len(vals) - 2)
    return vals[i] + (vals[i + 1] - vals[i]) * (f - i)


def cut_trousers(ob, arm, C):
    """Give the trousers of `ob` (the legs of a built person, in the rest pose) the cut C (one of CUTS), and every
    vertex of theirs its place on the leg in the attribute LEG: which way it faces round the leg (x: 1 the front, -1
    the back; y: 1 the outside, -1 the inside, a unit vector), its height (LEG_TOP) and 1, each as 0..1.  The game
    draws the denim's wash, the seams, the pockets and the hem by these (web/src/characters.js)."""
    me, mw = ob.data, ob.matrix_world.copy()
    inv = mw.inverted()
    skin = _skin_verts(me)
    co = {v.index: mw @ v.co for v in me.vertices if v.index not in skin}
    names = {g.index: g.name for g in ob.vertex_groups}
    side = {}
    for v in me.vertices:
        if v.index not in co:
            continue
        d = sum((1 if names[g.group].endswith('L') else -1) * g.weight for g in v.groups
                if names.get(g.group, '').startswith(('UpperLeg.', 'LowerLeg.', 'Foot.')))
        x = co[v.index].x
        side[v.index] = (1 if d > 0 else -1) if abs(d) > .2 else 0 if abs(x) < .02 else 1 if x > 0 else -1
    zb, zt = min(c.z for c in co.values()), max(c.z for c in co.values())
    H = zt - zb
    dz = 0.01
    n = int(math.ceil(H / dz)) + 1
    zs = [zb + j * dz for j in range(n)]
    # the cross-sections of either side: [inside, outside, front, back] (x from the middle outward)
    ext = {k: [[9.0, -9.0, 9.0, -9.0] for _ in zs] for k in (1, -1)}
    for e in me.edges:
        a, b = e.vertices
        if a not in co or b not in co:
            continue
        pa, pb = co[a], co[b]
        lo, hi = min(pa.z, pb.z), max(pa.z, pb.z)
        for j in range(max(0, int(math.ceil((lo - zb) / dz))), min(n - 1, int(math.floor((hi - zb) / dz))) + 1):
            t = 0.5 if hi - lo < 1e-9 else (zs[j] - pa.z) / (pb.z - pa.z)
            x, y = pa.x + (pb.x - pa.x) * t, pa.y + (pb.y - pa.y) * t
            for k in (1, -1):
                if side[a] != -k and side[b] != -k:
                    E = ext[k][j]
                    E[0] = min(E[0], x * k); E[1] = max(E[1], x * k); E[2] = min(E[2], y); E[3] = max(E[3], y)
    src = []
    for q in range(4):                              # (the two sides alike; a height nothing crosses takes its neighbour's)
        whole = lambda E: E[1] - E[0] > .04 and E[3] - E[2] > .05          # (not the tip of a slanting waistband or hem)
        col = [(ext[1][j][q] + ext[-1][j][q]) / 2 if whole(ext[1][j]) and whole(ext[-1][j]) else None for j in range(n)]
        for j in range(1, n):
            col[j] = col[j - 1] if col[j] is None else col[j]
        for j in range(n - 2, -1, -1):
            col[j] = col[j + 1] if col[j] is None else col[j]
        src.append(col)
    xi, xo, yf, yb = src
    bone = lambda name: (arm.matrix_world @ arm.data.bones[name].head_local)
    z_knee, z_hip = bone('LowerLeg.L').z, bone('UpperLeg.L').z
    mid = [co[i].z for i in co if side[i] == 0]
    z_c = min(mid) if mid else min(max(co[a].z, co[b].z) for a, b in (e.vertices for e in me.edges)
                                  if a in co and b in co and side[a] * side[b] < 0)
    z_c = min(z_c, z_hip - 0.04)
    at = lambda z: (z - zb) / dz
    jc = int(at(z_c))
    k = C['hang']
    mix = lambda a, h: [u + (w - u) * k for u, w in zip(a, h)]
    Mo, Mf, Mb = mix(xo, _hull(xo, 1)), mix(yf, _hull(yf, -1)), mix(yb, _hull(yb, 1))
    Mi = mix(xi[:jc + 1], _hull(xi[:jc + 1], -1)) + xi[jc + 1:]
    z_h = zb + 0.02                                  # the hem: about the ankle's own middle
    cx, cy = (_lerp_at(xi, at(z_h)) + _lerp_at(xo, at(z_h))) / 2, (_lerp_at(yf, at(z_h)) + _lerp_at(yb, at(z_h))) / 2 - C['fwd']
    cx = max(cx, C['hem'][0] + APART)
    # the waistband (its top 4 cm) keeps the pack's fit, `waist` wider: a top hangs over it or is tucked into it
    z_band = max(z_hip + 0.01, zt - 0.04)
    levels = [zb, z_knee, z_c, z_hip, z_band, zt]
    M = lambda line, z: _lerp_at(line, at(z))
    To = {zt: M(xo, zt) + C['waist'], z_band: M(xo, z_band) + C['waist'], z_hip: M(Mo, z_hip) + C['hip'], z_c: M(Mo, z_c) + C['hip'],
          zb: cx + C['hem'][0]}
    To[z_knee] = To[zb] + (To[z_c] - To[zb]) * (z_knee - zb) / (z_c - zb)
    Ti = {zt: M(Mi, zt), z_band: M(Mi, z_band), z_hip: M(Mi, z_hip), z_c: GAP, z_knee: To[z_knee] - 2 * C['knee'][0],
          zb: cx - C['hem'][0]}
    Tf = {zt: M(yf, zt) - C['waist'], z_band: M(yf, z_band) - C['waist'], z_hip: M(Mf, z_hip) - C['front'],
          z_c: M(Mf, z_c) - C['front'], z_knee: M(Mf, z_knee) - .008, zb: cy - C['hem'][1]}
    Tb = {zt: M(yb, zt) + C['waist'], z_band: M(yb, z_band) + C['waist'], z_hip: M(Mb, z_hip) + C['seat'],
          z_c: M(Mb, z_c) + C['seat'], z_knee: Tf[z_knee] + 2 * C['knee'][1], zb: cy + C['hem'][1]}

    def line(Mline, T):
        off = [T[z] - M(Mline, z) for z in levels]
        out = []
        for j, z in enumerate(zs):
            s = next((q for q in range(len(levels) - 1) if z <= levels[q + 1]), len(levels) - 2)
            t = max(0.0, min(1.0, (z - levels[s]) / (levels[s + 1] - levels[s])))
            out.append(Mline[j] + off[s] + (off[s + 1] - off[s]) * t)
        for _ in range(2):                           # (the corners at the levels rounded: 2 cm either way)
            out = [sum(out[max(0, min(n - 1, j + d))] for d in (-2, -1, 0, 1, 2)) / 5 for j in range(n)]
        return out
    Xo, Xi, Yf, Yb = line(Mo, To), line(Mi, Ti), line(Mf, Tf), line(Mb, Tb)
    Xi = [max(GAP, v) if j <= jc + 3 else v for j, v in enumerate(Xi)]
    Xi[:jc] = [max(GAP, min(v, Xo[j] - .04)) for j, v in enumerate(Xi[:jc])]
    att = me.attributes.get(LEG) or me.attributes.new(LEG, 'FLOAT_VECTOR', 'POINT')
    legs = [(0.0, 0.0, 0.0)] * len(me.vertices)
    for i, c in co.items():
        f = at(c.z)
        s = side[i] or (1 if c.x >= 0 else -1)
        a_i, a_o, a_f, a_b = (_lerp_at(q, f) for q in src)
        b_i, b_o, b_f, b_b = (_lerp_at(q, f) for q in (Xi, Xo, Yf, Yb))
        w = 0.0 if side[i] == 0 else 1 - _smooth(z_c - .03, z_c + .03, c.z)        # 1 a leg, 0 the hips
        xs = c.x * s
        leg = b_i + (xs - a_i) * (b_o - b_i) / max(a_o - a_i, 1e-4)
        hips = xs * b_o / max(a_o, 1e-4)
        xs = hips + (leg - hips) * w
        lo = b_i * w                                  # (the hips: from the middle)
        u = (xs - lo) / max(b_o - lo, 1e-4) * 2 - 1
        y = b_f + (c.y - a_f) * (b_b - b_f) / max(a_b - a_f, 1e-4)
        d = (y - b_f) / max(b_b - b_f, 1e-4) * 2 - 1
        r = math.hypot(u, d) or 1.0
        v = (0.5 * (c.z - zb) / (z_knee - zb) if c.z < z_knee else 0.5 + 0.5 * (c.z - z_knee) / (z_hip - z_knee) if c.z < z_hip
             else 1 + 0.2 * (c.z - z_hip) / max(zt - z_hip, 1e-4))
        legs[i] = (0.5 - 0.5 * d / r, 0.5 + 0.5 * u / r, v / LEG_TOP)
        c.x, c.y = xs * s, y
        if c.z < z_knee:                              # the leg drawn out from the knee to where its hem ends
            end = C['floor'] + C['rise'] * _smooth(0.0, 1.0, -d)
            c.z = z_knee - (z_knee - c.z) * (z_knee - end) / (z_knee - zb)
    for v in me.vertices:
        if v.index in co:
            v.co = inv @ co[v.index]
    att.data.foreach_set('vector', [x for q in legs for x in q])
    me.update()


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
        def reaches(f):
            """Whether the face's bounds meet the box: only those are cut (a cut right through a shoe for a bar on its
            side would leave a ring of points all round it)."""
            for k, (lo, hi) in box.items():
                vs = [abs(v.co.x) if k == 'x' else getattr(v.co, k) for v in f.verts]
                if k == 'x' and min(v.co.x for v in f.verts) < 0 < max(v.co.x for v in f.verts):
                    vs.append(0.0)
                if (lo is not None and max(vs) < lo - 1e-6) or (hi is not None and min(vs) > hi + 1e-6):
                    return False
            return True
        for co, no in planes:
            fs = [f for f in bm.faces if f.material_index in src and reaches(f)]
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


# ---------- what is printed on a chest ----------
# A person's `prints` lists, by part: the print's name (faces.py PRINTS: a band of the atlas' print cell), the
# materials it lies on, its width w and the height z of its middle (m, the source's T pose).  The front of the part
# inside that frame is cut out along the frame's sides and laid on the band, seen from the front (as face_map lays a
# face on its cell); everything else stays on the blank cell.  The game can leave a print out (the crowd does not all
# wear the same slogan): web/src/characters.js points those vertices at the blank cell.

def print_map(ob, rules):
    import bmesh
    me, mw = ob.data, ob.matrix_world
    atlas_layer(ob)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(mw)
    uv = bm.loops.layers.uv[ATLAS_UV]
    for rule in rules:
        names = [m.name.split('.')[0] if m else '' for m in me.materials]
        src = {i for i, n in enumerate(names) if n in rule['of']}
        u0, v0, u1, v1, aspect = faces.print_band(rule['name'])
        W = rule['w']
        H = W / aspect
        x0, z0, z1 = -W / 2, rule['z'] - H / 2, rule['z'] + H / 2

        def front(f):
            return f.material_index in src and f.normal.y < -0.3 and all(abs(v.co.x) < W / 2 + 0.2 for v in f.verts)

        def reaches(f):
            xs, zs = [v.co.x for v in f.verts], [v.co.z for v in f.verts]
            return max(xs) > x0 - 1e-6 and min(xs) < -x0 + 1e-6 and max(zs) > z0 - 1e-6 and min(zs) < z1 + 1e-6
        for co, no in ((Vector((x0, 0, 0)), Vector((1, 0, 0))), (Vector((-x0, 0, 0)), Vector((1, 0, 0))),
                       (Vector((0, 0, z0)), Vector((0, 0, 1))), (Vector((0, 0, z1)), Vector((0, 0, 1)))):
            fs = [f for f in bm.faces if front(f) and reaches(f)]
            geom = fs + list({e for f in fs for e in f.edges}) + list({v for f in fs for v in f.verts})
            bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no)
        n = 0
        for f in bm.faces:
            c = f.calc_center_median()
            if not (front(f) and x0 < c.x < -x0 and z0 < c.z < z1):
                continue
            n += 1
            for loop in f.loops:
                p = loop.vert.co
                loop[uv].uv = (u0 + (p.x - x0) / W * (u1 - u0), 1 - (v0 + (z1 - p.z) / H * (v1 - v0)))
        if n < 4:
            raise SystemExit(f'{ob.name}: the print {rule["name"]} lies on {n} faces')
    bm.transform(mw.inverted())
    bm.to_mesh(me)
    bm.free()


# ---------- a skirt that sits ----------
# The pack weights its clothes round the hips to the thighs well above the hip joints (a knit's hem 7 - 13 cm up is
# still 0.3 - 0.7 a thigh's) and its skirt as two trouser legs (each half all its thigh's up to the joint). Walking that
# holds; sitting (clip 'sit': the thighs 88 degrees forward) swings all a thigh holds round the joint, so the front of
# the skirt there went up into the belly, turning the panel below it inside out (a hole from above), and the knit's hem
# behind went down and out through the skirt (a white patch on the back). So for a person in a skirt:
#  - the thighs' share eases out from SKIRT_FREE[0] below the hip joints to SKIRT_FREE[1] above, and goes to the other
#    bones the vertex has (else Body, which the thighs hang from): the waistband and the knit stay on the hips
#  - the skirt gets an inner side (its faces again, turned round), so a panel the pose still turns over (at the hip
#    crease, under the lap) shows the cloth and not what is under it
SKIRT_FREE = (0.12, 0.0)          # metres (the game's scale) below, above the hip joints


def skirt_sit(arm, parts, s):
    import bmesh
    hz = sum((arm.matrix_world @ arm.data.bones['UpperLeg.' + side].head_local).z for side in 'LR') / 2
    lo, hi = hz - SKIRT_FREE[0] / s, hz + SKIRT_FREE[1] / s
    for ob in parts:
        me, mw = ob.data, ob.matrix_world
        legs = {g.index for g in ob.vertex_groups if g.name in ('UpperLeg.L', 'UpperLeg.R')}
        body = ob.vertex_groups.get('Body') or ob.vertex_groups.new(name='Body')
        for v in me.vertices:
            keep = 1 - _smooth(lo, hi, (mw @ v.co).z)
            ws = {g.group: g.weight for g in v.groups if g.weight > 0}
            free = sum(w for gi, w in ws.items() if gi in legs) * (1 - keep)
            if free < 1e-6:
                continue
            rest = {gi: w for gi, w in ws.items() if gi not in legs}
            tot = sum(rest.values())
            for gi in legs & ws.keys():
                ob.vertex_groups[gi].add([v.index], ws[gi] * keep, 'REPLACE')
            if tot > 1e-6:
                for gi, w in rest.items():
                    ob.vertex_groups[gi].add([v.index], w + free * w / tot, 'REPLACE')
            else:
                body.add([v.index], free, 'REPLACE')
        names = [m.name if m else '' for m in me.materials]
        if 'Skirt~new' not in names:
            continue
        bm = bmesh.new()
        bm.from_mesh(me)
        k = names.index('Skirt~new')
        dup = bmesh.ops.duplicate(bm, geom=[f for f in bm.faces if f.material_index == k])
        bmesh.ops.reverse_faces(bm, faces=[g for g in dup['geom'] if isinstance(g, bmesh.types.BMFace)])
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
# Everything is skinned to the bone Head (long hair shares its ends with Neck and Chest: hair_follow), so bags.js,
# which reads the build off the vertices of the other bones, and the clips see the same body as before.
# The materials are named Skin, Hair, Glasses (Band, Bridge, HairFade, HairFade2): web/src/characters.js crowdLook
# recolours them by these names and leaves the glasses out by 'Glasses'.
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
    # the top swept up and back; the sides and the back clipped (바리캉으로 올려 친 머리): the top hair ends 2.5 cm
    # over the ear and level with its top behind, and under it a second shell lies close on the scalp (`under`) in two
    # bands that let the skin show through (`fade`: the materials above and below the height dz, their colours the
    # hair's mixed with the skin's), down to the short hairline
    'up': dict(tip=[(0, .042), (24, .043), (40, .038), (50, .030), (58, .022), (70, .016), (86, .012), (100, .008),
                    (112, .000), (135, -.016), (180, -.026)],
               vol=[(0, .046), (26, .038), (48, .016), (75, .008), (180, .010)], top=.024,
               edge=[(0, .005), (40, .005), (55, .003), (180, .003)], hem=1.2, rows=9, rough=.5, ragged=.004,
               under=dict(tip=[(0, .047), (44, .040), (51, .026)] + _ear(burn=-.030, back=(-.050, -.088, -.096)),
                          vol=[(0, .0025), (180, .0025)], top=.0025, edge=.0015, rows=9, rough=.0,
                          fade=('HairFade', 'HairFade2', -.038))),
    'crop': dict(tip=[(0, .047), (28, .047), (44, .040), (51, .026)] + _MEN_EAR,
                 vol=[(0, .026), (40, .019), (70, .008), (180, .009)], top=.026,
                 edge=[(0, .010), (36, .008), (52, .004), (180, .003)], sheet=.014, rows=7, rough=.25, ragged=.003),
    'short': dict(tip=_both([(-48, .024), (-28, .014), (-8, .012), (14, .018), (34, .030), (48, .032)], _MEN_EAR),
                  vol=[(-180, .011), (-60, .008), (-20, .014), (20, .012), (60, .008), (180, .011)], top=.026, edge=.004,
                  rows=7, rough=.25, ragged=.005),
    # short all round with the fringe combed straight down to just over the brows (the film's first-year of 1996)
    'fringe': dict(tip=_both([(-50, .022), (-36, .010), (-16, .007), (6, .008), (26, .007), (40, .011), (50, .022)], _MEN_EAR),
                   vol=[(0, .017), (40, .015), (70, .009), (180, .010)], top=.027, edge=[(0, .008), (48, .006), (60, .004), (180, .004)],
                   rows=8, rough=.2, ragged=.004),
    'curtain': dict(tip=_parted(0), vol=[(0, .013), (30, .017), (60, .014), (180, .014)], top=.027, edge=.006,
                    part=(0, .010, 7), rows=8, rough=.3, ragged=.005),
    'curtain-64': dict(tip=_parted(12), vol=[(0, .014), (30, .017), (60, .014), (180, .014)], top=.027, edge=.006,
                       part=(12, .010, 7), rows=8, rough=.3, ragged=.005),
    # the two-block cut: the top left long (a fringe swept from a 7:3 parting, one length round to the back, ending
    # blunt above the ear and on the back of the head), the sides and the nape under it clipped short (`under`: a
    # second, close shell; only what shows below the long hair's hem is kept)
    'two-block': dict(tip=_parted(23, [(62, -.014), (70, -.006), (80, -.002), (100, -.002), (112, -.010), (135, -.018), (180, -.022)],
                                  k=.86),
                      vol=[(-180, .017), (-90, .014), (-25, .019), (8, .017), (30, .014), (60, .013), (90, .014), (180, .017)],
                      top=.027, edge=.010, sheet=.02, part=(23, .009, 7), rows=8, rough=.25, ragged=.004,
                      under=dict(tip=[(0, .047), (44, .040), (51, .026)] + _ear(burn=-.030, back=(-.050, -.088, -.096)),
                                 vol=[(0, .0035), (180, .0035)], top=.0035, edge=.002, rows=9, rough=.0)),
    'part-side': dict(tip=_parted(34, _ear(temple=.0), k=.70),
                      vol=[(-180, .011), (-90, .009), (-40, .015), (0, .015), (25, .013), (45, .008), (90, .008),
                           (180, .011)], top=.026, edge=.004, part=(34, .009, 8), rows=7, rough=.15, ragged=.003),
    'thin': dict(tip=_both([(-47, .050), (-22, .056), (0, .064), (20, .072), (34, .078), (47, .068)],
                           _ear(burn=-.030, back=(-.048, -.090, -.100))),
                 vol=[(-180, .007), (-90, .005), (-30, .010), (25, .008), (60, .005), (180, .007)], top=.017, edge=.003,
                 part=(34, .006, 8), rows=6, rough=.12),
    # long straight hair worn down from a parting a little off the middle, drawn back off the face: the forehead and
    # the cheeks show, the hair falls from the temples
    'long': dict(tip=[(-180, -.350), (-135, -.330), (-108, -.215), (-90, -.180), (-74, -.215), (-64, -.215), (-57, -.120),
                      (-50, -.040), (-40, .006), (-26, .032), (-10, .050), (6, .060), (20, .046), (34, .024), (44, .000),
                      (52, -.050), (58, -.130), (64, -.215), (74, -.215), (90, -.180), (108, -.215), (135, -.330), (180, -.350)],
                 vol=[(-180, .016), (-90, .015), (-45, .013), (6, .011), (45, .013), (90, .015), (180, .016)], top=.017, edge=.010,
                 part=(6, .007, 7),
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
    # a woman's short cut, the sides swept back over the ears: the hem lies over the ear's top (at -.023 on the women's
    # head, where the men's is at -.014; the hair a centimetre thick there, as the ear stands off) and comes down
    # close behind it, a sideburn's wisp before it
    'pixie': dict(tip=_both([(-48, .010), (-28, .010), (-8, .016), (14, .028), (30, .046), (46, .022)],
                            [(57, .012), (62, -.010), (67, -.040), (73, -.050), (77, -.037), (81, -.033), (96, -.033),
                             (100, -.042), (105, -.066), (112, -.080), (135, -.102), (180, -.112)]),
                  vol=[(-180, .013), (-60, .011), (-20, .017), (20, .014), (60, .011), (180, .013)], top=.024,
                  edge=[(0, .005), (70, .005), (79, .010), (98, .010), (108, .005), (180, .005)],
                  part=(30, .004, 7), rows=7, rough=.25, ragged=.004),
    'half': dict(tip=_both([(-47, .036), (-26, .030), (-6, .030), (14, .040), (30, .052), (47, .040)],
                           [(57, .022), (62, .008), (79, .008), (97, .006), (104, -.08), (111, -.22), (135, -.31), (180, -.33)]),
                 vol=[(-180, .016), (-100, .015), (-60, .008), (-20, .013), (20, .011), (60, .008), (100, .015), (180, .016)],
                 top=.016, edge=[(0, .004), (60, .004), (100, .010), (180, .010)], part=(30, .004, 7), fall=.10, sheet=.014,
                 rows=12, rough=.08, ragged=.004, tail=dict(dz=.0, length=.17, r=.022)),
    'perm': dict(tip=[(-180, -.105), (-135, -.100), (-90, -.072), (-60, -.062), (-50, -.020), (-30, .008), (0, .024),
                      (15, .038), (26, .048), (34, .026), (42, -.008), (52, -.050), (60, -.062), (90, -.072), (135, -.100), (180, -.105)],
                 vol=[(-180, .021), (-90, .021), (-30, .019), (28, .013), (60, .020), (180, .021)], top=.023, edge=.013,
                 part=(28, .006, 7), fall=.5, sheet=.018, curl=.006, rows=8, rough=.35, ragged=.003, ears=False),
}
PART_COLORS = {'Band': '#27345a', 'Glasses': '#77736c'}       # the tie of a tail, thin metal rims
FADE = (0.40, 0.62)        # clipped hair: how much of the skin shows in the upper and the lower band (the game's FADED)
ATLAS_UV = 'atlas'                                             # the UV layer into faces.png
BLANK_UV = (faces.uv(faces.BLANK, 0.0, faces.TOP - faces.HALF)[0], 1 - faces.uv(faces.BLANK, 0.0, faces.TOP - faces.HALF)[1])


def hex_mix(a, b, t):
    return '#' + ''.join('%02x' % round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t) for i in (1, 3, 5))


def hex_fade(hair, skin, t):
    """Stubble over skin: the hair's colour with t of the skin's, half way to grey (black hair over warm skin mixes
    to a brown that reads as dyed hair; clipped hair looks cooler).  web/src/characters.js fadeHex is the same."""
    ch = [int(hair[i:i + 2], 16) * (1 - t) + int(skin[i:i + 2], 16) * t for i in (1, 3, 5)]
    grey = 0.3 * ch[0] + 0.59 * ch[1] + 0.11 * ch[2]
    return '#' + ''.join('%02x' % round((c + grey) / 2) for c in ch)


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
    follow = [hair_follow(C, p) for p in pts]
    tail = st.get('tail')
    band = []
    if tail:
        tp, tf, band = hair_tail(surf, st, tail, len(pts))
        band = [len(faces) + i for i in band]
        pts += tp
        faces += tf
        follow += [(0.6 * _smooth(C.z - 0.10, C.z - 0.30, p.z), 0.0) for p in tp]       # (tied to the head)
    return pts, faces, follow, (cols, ends), band, streak


def hair_follow(C, p):
    """How much of the hair at the point p follows the neck and the chest rather than the head: (neck, chest).  Hair
    that hangs below the jaw lies on the back and the shoulders and stays there as the head turns (a shake, a seated
    person looking round to a bench mate): its ends follow the neck and the chest alone, the hair above them twists.
    Behind the ears that starts higher, by the nape (the hair over the shoulders turned with the head and the shoulders
    showed through it); beside the face lower, under the jaw (the locks there keep with the cheeks).  The neck keeps
    the larger share of the two everywhere, so the main bone of every point of the hair is still the head or the neck
    (bags.js leaves those out of the build it fits a bag to)."""
    back = _smooth(80.0, 130.0, abs(math.degrees(math.atan2(p.x - C.x, -(p.y - C.y)))))
    off = _smooth(C.z - 0.17 + 0.07 * back, C.z - 0.36, p.z)
    chest = 0.45 * _smooth(C.z - 0.22, C.z - 0.36, p.z)
    return off - chest, chest


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


def glasses_line(L):
    """The height of the glasses' middle (faces.py draws them that far under the eye line: RIM_DZ)."""
    return (L['eyes'][0][0].z + L['eyes'][0][1].z) / 2 - 0.001


def face_glasses(surf, L, rig, face):
    """Round-cornered rims a centimetre off the eyes, a bridge, and temples back to the ears: (points, faces).  The
    frame and the rims' thickness are faces.py's, which draws the same glasses for the game to show from further off."""
    pts, faces = [], []
    ez = glasses_line(L)
    ear = max(L['ears'], key=lambda box: box[1].x)
    _, ex, W, H = faces_mod.rim_frame(rig, face)
    T, N = faces_mod.RIM_T, 16
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


def head_part(name, arm, pieces, follow=None):
    """A mesh of [(material, points, faces)] skinned to the head (and, by `follow`: (neck, chest) for each point of the
    pieces in turn, to the neck and the chest)."""
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
    groups = {}
    for i in range(len(pts)):
        n, c = follow[i] if follow and i < len(follow) else (0.0, 0.0)
        for bone, w in (('Head', 1.0 - n - c), ('Neck', n), ('Chest', c)):
            if w > 0:
                if bone not in groups:
                    groups[bone] = ob.vertex_groups.new(name=bone)
                groups[bone].add([i], w, 'REPLACE')
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
    pts, faces, follow, ends, band, streak = hair_grow(pid, surf, st)
    under = None
    if st.get('under'):                                      # (the clipped hair under a two-block cut)
        u_pts, u_faces, u_follow, u_ends, _, _ = hair_grow(pid, surf, st['under'])
        C, s_eq = surf.C, HAIR_RN * math.pi / 2
        cols = ends[0]

        def shows(q):
            dz = q.z - C.z
            arc = HAIR_RN * (math.pi / 2 - math.atan2(dz, math.hypot(q.x - C.x, q.y - C.y))) if dz >= 0 else s_eq - dz
            a = math.atan2(q.x - C.x, -(q.y - C.y)) % (2 * math.pi)
            j = min(range(len(cols)), key=lambda k: abs((cols[k] - a + math.pi) % (2 * math.pi) - math.pi))
            return arc > ends[1][j] - 0.02
        kept = [f for f in u_faces if any(shows(u_pts[i]) for i in f)]
        fade = st['under'].get('fade')                       # (clipped so short that the skin shows: two bands)
        bands = {'Hair': kept}
        if fade:
            high = lambda f: sum(u_pts[i].z for i in f) / len(f) >= C.z + fade[2]         # noqa: E731
            bands = {fade[0]: [f for f in kept if high(f)], fade[1]: [f for f in kept if not high(f)]}
        under = []
        for name, fs in bands.items():
            ring = sorted({i for f in fs for i in f})
            at = {i: n for n, i in enumerate(ring)}
            under.append(((name, [u_pts[i] for i in ring], [tuple(at[i] for i in f) for f in fs]), [u_follow[i] for i in ring]))
        head_trim(head, surf, st['under'], u_ends)
    else:
        head_trim(head, surf, st, ends)
    other = set(band) | set(streak)
    pieces = [('Hair', pts, [f for i, f in enumerate(faces) if i not in other])]
    weights = list(follow)
    for piece, fol in under or ():
        pieces.append(piece)
        weights += fol
    for name, part in (('Band', band), ('Bridge', streak)):  # (these have points of their own, weighted as the hair's)
        if part:
            ring = sorted({i for b in part for i in faces[b]})
            at = {i: n for n, i in enumerate(ring)}
            pieces.append((name, [pts[i] * 1.0 for i in ring], [tuple(at[i] for i in faces[b]) for b in part]))
            weights += [follow[i] for i in ring]
    col = spec['colors']
    hair = col.get('Hair', HAIR['black'])
    skin = col.get('Skin', SKIN['b'])
    defaults = dict(PART_COLORS, Hair=hair, Bridge=hex_mix(hair, '#d9a35a', 0.5),
                    HairFade=hex_fade(hair, skin, FADE[0]), HairFade2=hex_fade(hair, skin, FADE[1]))
    for name in ('Hair', 'Band', 'Glasses', 'Bridge', 'HairFade', 'HairFade2'):
        colour_material(name, srgb_to_linear(col.get(name, defaults[name])))
    hob = head_part(pid + '-hair', arm, pieces, weights)
    fob = head_part(pid + '-glasses', arm, [('Glasses', *face_glasses(surf, L, rig, face))])
    face_map(head, surf, L, face, rig, list(PEOPLE).index(pid))
    if abs(glasses_line(L) - eye_line(L, face) - faces_mod.RIM_DZ) > 0.0005:
        raise SystemExit(f'{pid}: the glasses are {glasses_line(L) - eye_line(L, face):.4f} under the eyes; faces.py '
                         f'draws them at {faces_mod.RIM_DZ}')
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
        if part in spec.get('prints', {}):
            print_map(ob, spec['prints'][part])
        recolour(ob, part, spec['colors'])
        shape_body(ob, arm, rig)                 # (the neck is the head's, the waist the body's and the legs')
        loosen(ob, part, outfit, arm)
        atlas_layer(ob)
        ob.name = f'{pid}-{part}'
        parts.append(ob)
    if any(m and m.name == 'Skirt~new' for o in parts for m in o.data.materials):         # (recolour's names)
        skirt_sit(arm, [o for o in parts if o.name.endswith(('-body', '-legs'))], s)
    keep = set(parts) | {arm}
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    clear_anim(arm)
    relax_fingers(arm, parts, rig, s)
    cut = spec.get('cut') or TROUSERS.get(spec['parts']['legs'])
    if cut:
        cut_trousers(next(o for o in parts if o.name.endswith('-legs')), arm, CUTS[rig][cut])
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    return finish_person(pid, arm, parts, s, 'rig-' + rig, bool(spec.get('face', {}).get('glasses')))


OCC = '_OCC'                  # the vertex attribute of the shade below (glTF: a custom attribute)
OCC_FAR = 0.28                # metres: what is further away shades nothing
OCC_RAYS = 24


def occlude(mesh):
    """How much of the sky each vertex sees past the rest of the person (the hair over the brow and the neck, the chin
    over the throat, sleeves, hems, the legs beside each other): 0 open, 1 shut in, kept on the vertices for the game
    to shade by (web/src/characters.js).  Rays over the hemisphere of the vertex's normal in the rest pose, a hit
    counting less the further off it is; the glasses shade nothing (not everybody wears theirs), and neither does one
    leg the other: side by side at rest, they part at every stride, and the shade between them would stay on the
    inside of the thighs as a dark streak."""
    from mathutils.bvhtree import BVHTree
    me = mesh.data
    glass = {i for i, m in enumerate(me.materials) if m and m.name.split('~')[0] == 'Glasses'}
    # which leg a vertex belongs to (1 the left, 2 the right, 0 neither: a skirt hangs from both)
    names = {g.index: g.name for g in mesh.vertex_groups}
    leg = []
    for v in me.vertices:
        w = [0.0, 0.0]
        for g in v.groups:
            n = names.get(g.group, '')
            if n.startswith(('UpperLeg.', 'LowerLeg.', 'Foot.')):
                w[n.endswith('R')] += g.weight
        leg.append(1 if w[0] > 0.6 else 2 if w[1] > 0.6 else 0)
    cos = [v.co.copy() for v in me.vertices]
    polys = [p for p in me.polygons if p.material_index not in glass]
    side = [max(leg[v] for v in p.vertices) if len({leg[v] for v in p.vertices} - {0}) < 2 else 0 for p in polys]
    trees = {0: BVHTree.FromPolygons(cos, [tuple(p.vertices) for p in polys])}
    for k in (1, 2):                              # (what a vertex of the left leg sees: everything but the right leg)
        trees[k] = BVHTree.FromPolygons(cos, [tuple(p.vertices) for p, sd in zip(polys, side) if sd != 3 - k])
    dirs = []
    for i in range(OCC_RAYS):                # cosine-weighted, on a spiral
        u = (i + 0.5) / OCC_RAYS
        r, th = math.sqrt(u), i * 2.399963
        dirs.append((r * math.cos(th), r * math.sin(th), math.sqrt(1 - u)))
    att = me.attributes.get(OCC) or me.attributes.new(OCC, 'FLOAT', 'POINT')
    normals = [v.normal.copy() for v in me.vertices]
    vals = []
    for i, v in enumerate(me.vertices):
        n = normals[i]
        t = (Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))).cross(n).normalized()
        b = n.cross(t)
        spin = (i * 0.61803 % 1) * 2 * math.pi
        cs, sn = math.cos(spin), math.sin(spin)
        o = v.co + n * 0.004
        shut = 0.0
        for x, y, z in dirs:
            d = n * z + t * (x * cs - y * sn) + b * (x * sn + y * cs)
            hit = trees[leg[i]].ray_cast(o, d, OCC_FAR)
            if hit[0] is not None:
                shut += 1 - hit[3] / OCC_FAR
        vals.append(min(1.0, shut / OCC_RAYS * 1.5))
    att.data.foreach_set('value', vals)


def weld_skin(mesh):
    """The parts are the pack's modules: where skin runs from one into the next (the neck into a low neckline, a wrist
    into a hand), each ends in a rim of its own.  Lit by its own faces alone, each rim shades a little differently, and
    the join shows as a line: the points the rims of skin share are made one.  (The head's neck has been subdivided,
    so it shares only some of its rim's points with the body's: a faint line stays there.)"""
    import bmesh
    me = mesh.data
    skin = {i for i, m in enumerate(me.materials) if m and m.name.split('~')[0].split('.')[0] == 'Skin'}
    bm = bmesh.new()
    bm.from_mesh(me)
    rim = [v for v in bm.verts if v.is_boundary and v.link_faces and all(f.material_index in skin for f in v.link_faces)]
    bmesh.ops.remove_doubles(bm, verts=rim, dist=0.0008)
    bm.to_mesh(me)
    bm.free()


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
    weld_skin(mesh)
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
    occlude(mesh)
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


def arms_in(arm, act, sides, add, twist):
    """The upper arms (of `sides`) of a clip turned in toward the body about the model's front-back axis by `add`
    degrees, the forearms turned about their own length by `twist` (ARMS_IN): at every key of theirs."""
    use_action(arm, act)
    for side, sx in (('L', 1), ('R', -1)):
        if side not in sides:
            continue
        for name, turn in (('UpperArm.' + side, lambda pb: rotate_about_head(pb, 'Y', sx * add)),
                           ('LowerArm.' + side, lambda pb: setattr(pb, 'matrix_basis', pb.matrix_basis @ Matrix.Rotation(math.radians(sx * twist), 4, 'Y')))):
            if not (add if name.startswith('Upper') else twist):
                continue
            path = f'pose.bones["{name}"].rotation_quaternion'
            frames = sorted({k.co.x for fc in fcurves(act) if fc.data_path == path for k in fc.keyframe_points})
            pb = arm.pose.bones[name]
            pb.rotation_mode = 'QUATERNION'
            keys = []
            for f in frames:
                bpy.context.scene.frame_set(int(f), subframe=f - int(f))
                bpy.context.view_layer.update()
                turn(pb)
                bpy.context.view_layer.update()
                q = pb.rotation_quaternion.copy()
                if keys and keys[-1][1].dot(q) < 0:
                    q.negate()
                keys.append((f, q))
            for fc in fcurves(act):
                if fc.data_path == path:
                    for k in fc.keyframe_points:
                        v = next(q for f, q in keys if f == k.co.x)[fc.array_index]
                        k.handle_left.y += v - k.co.y
                        k.handle_right.y += v - k.co.y
                        k.co.y = v
                    fc.update()
    use_action(arm, None)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)


def build_rig(rid):
    rig = RIGS[rid]
    objs = import_outfit(rig, RIG_SOURCE[rid])
    arm = next(o for o in objs if o.type == 'ARMATURE')
    for o in list(bpy.data.objects):
        if o is not arm:
            bpy.data.objects.remove(o, do_unlink=True)
    clear_anim(arm)
    s = HEIGHT[rig] / TOP[rig]
    relax_fingers(arm, [], rig, s)
    fps = bpy.context.scene.render.fps
    acts = {}
    for clip, src in CLIPS[rig].items():
        if src:
            a = bpy.data.actions.get(src)
            if a is None:
                raise SystemExit(f'{rid}: no action {src}')
            acts[clip] = a
    for clip, turn in ARMS_IN[rig].items():
        arms_in(arm, acts[clip], *turn)
    meta = {'seat': SEAT}
    meta.update(mocap.build(rig, arm, acts, s, fps))        # motion capture: standing, walking, running, sitting
    acts['emote-no'] = new_action(arm, 'emote-no', head_shake(arm, pose_from(arm, acts['idle'], 0)))
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
        arm[k] = v if isinstance(v, str) else round(v, 3)
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
    """WEIGHTS_0 as normalized unsigned bytes (core glTF) instead of floats: a quarter of the size.  The shade of
    occlude() (_OCC) as bytes, 0-255."""
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
            ai = prim['attributes'].get(OCC)
            acc = j['accessors'][ai] if ai is not None and ai not in done else None
            if acc and acc['componentType'] == 5126 and not acc.get('byteOffset', 0) and not j['bufferViews'][acc['bufferView']].get('byteStride'):
                vals = struct.unpack(f'<{acc["count"]}f', views[acc['bufferView']][:acc['count'] * 4])
                # (plain bytes, 0-255: Blender's importer cannot read a normalized custom attribute)
                views[acc['bufferView']] = bytes(min(255, max(0, round(v * 255))) for v in vals)
                acc['componentType'] = 5121
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
    lie wholly on the blank cell go without (web/src/characters.js puts them there).  The trousers' coordinates (LEG)
    likewise only on the parts with trousers, as bytes."""
    with open(path, 'rb') as fh:
        d = fh.read()
    n = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + n])
    bin_ = d[20 + n + 8:]
    views = [bytes(bin_[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]) for v in j['bufferViews']]
    drop = set()
    for m in j.get('meshes', []):
        for prim in m['primitives']:
            ai = prim['attributes'].get(LEG)
            acc = j['accessors'][ai] if ai is not None else None
            if acc and acc['componentType'] == 5126 and acc['type'] == 'VEC3' and not acc.get('byteOffset', 0) \
                    and not j['bufferViews'][acc['bufferView']].get('byteStride'):
                vals = struct.unpack(f'<{acc["count"] * 3}f', views[acc['bufferView']][:acc['count'] * 12])
                if not any(vals):                              # (no trousers in this part)
                    del prim['attributes'][LEG]
                    drop.add(ai)
                else:
                    # four plain bytes a vertex (as _OCC): the three values and whether the vertex is of the trousers
                    q = lambda v: min(255, max(0, round(v * 255)))
                    views[acc['bufferView']] = b''.join(
                        bytes([q(vals[i]), q(vals[i + 1]), q(vals[i + 2]), 255 if any(vals[i:i + 3]) else 0])
                        for i in range(0, len(vals), 3))
                    acc['componentType'] = 5121
                    acc['type'] = 'VEC4'
                    acc.pop('min', None)
                    acc.pop('max', None)
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
        on = 1 + len({m for rules in PEOPLE[pid].get('prints', {}).values() for r in rules for m in r['of']})
        if sum('TEXCOORD_0' in prim['attributes'] for prim in prims) != on or any('TEXCOORD_1' in prim['attributes'] for prim in prims):
            problems.append('texture coordinates (the skin and the printed cloth alone have faces on the atlas)')
        if any(OCC not in prim['attributes'] for prim in prims):
            problems.append('no occlusion on the vertices')
        spec = PEOPLE[pid]
        if (spec.get('cut') or TROUSERS.get(spec['parts']['legs'])) and not any(LEG in prim['attributes'] for prim in prims):
            problems.append("no coordinates on the trousers' vertices")
    return problems


# ---------- main ----------

def face_atlas():
    """faces.png: everybody's face in the order of PEOPLE (the cells face_map lays the faces on); faces_rims.png:
    everybody's glasses in the same cells (the game shows them on whoever wears glasses, from a few metres off)."""
    rows = []
    for sp in PEOPLE.values():
        col = sp['colors']
        hair, skin = col.get('Hair', HAIR['black']), col.get('Skin', SKIN['b'])
        rows.append((sp['rig'], sp.get('face', {}), skin, col.get('Brow', hex_mix(hair, skin, 0.10))))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'faces.png')
    faces.write_atlas(path, rows)
    print(f'faces: png {os.path.getsize(path) // 1024} KB  ({len(rows)} faces, {faces.GRID * faces.CELL} px)')
    rims = os.path.join(OUT, 'faces_rims.png')
    faces.write_rims(rims, [(sp['rig'], sp.get('face', {})) for sp in PEOPLE.values()])
    print(f'faces_rims: png {os.path.getsize(rims) // 1024} KB  ({faces.GRID * faces.RIM_CELL} px)')


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
            took = {k: ' '.join(v['take']) for k, v in mocap.CLIPS[r].items()}
            print(f'{rid:20} clips {", ".join(f"{k}<-{took.get(k) or v or "made here"}" for k, v in CLIPS[r].items())}')
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
