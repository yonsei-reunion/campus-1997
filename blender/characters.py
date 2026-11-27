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


def neckline(of, drop=.014, half=.044, side=.090, lean=0.0, vee=0.0, to='Skin', ring=.012, lobe=2.0):
    """A paint rule (see `paint`): the top's neckline, `drop` under the neck's joint in the middle of the front
    (the top's rim stands 1 - 2 cm over the joint there: that much more skin shows).  The men's is cut out instead,
    by `drop`, `ring` and `lobe` alone (neck_bib); where the top's front lies is LIE's (lay_collar)."""
    return dict(of=of, to=to, neck=dict(drop=drop, half=half, side=side, lean=lean, vee=vee, ring=ring, lobe=lobe))


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
# tee in broad stripes, a checked shirt worn open over a tee, a blazer over cotton trousers, the Yonsei-blue cheer
# jacket, a white knit over a denim skirt, a cream sweatshirt, a pastel cardigan, a professor in a grey suit, staff in
# work vests.
# Hair (the first name, see HAIR_STYLES) and faces as students wore and had them about 1997 (reference/고증 4.9): most
# of them plain, a few the cuts of the year.  Optional: flip (the parting on the other side), bridge (bleached locks:
# [(azimuth, half width)]), face: what makes the one shared face a person's own.  Of the skull: jaw, chin (scales).
# Of the drawn lines (faces.py): lid (mono 홑꺼풀, inner 속쌍꺼풀, double 쌍꺼풀), slant (the outer corner of the eye
# higher, of the eye's half width), eye, brow, mouth, lash, lip (scales), lip_up (the upper lip, of the lower),
# lip_ink (how strongly the lips are tinted), mouth_line (the line's weight), brow_tilt (the tail higher), arch (of the
# brow, a scale), smile (the corners of the mouth up, m), age ('mid', 'old': the lines of an older face).  glasses:
# who wears them as the model is (everybody has a pair: the game shows or hides it, web/src/characters.js).  prints:
# lettering on a part (see 'what is printed' below).  Of the
# brows also brow_len, brow_gap, brow_up, brow_peak, brow_corner, brow_drop, brow_taper, brow_soft (faces.py), of the
# nose nose, bridge, nose_curve, tip_up, nose_up, tip_round, nose_w, wing (NOSE below); of the head's shape jaw (the lower face's width), chin
# (its length), cheek (the width at the cheeks), taper (the jaw narrower toward the chin).  paint: parts of the outfit in colours of their own
# (see '1997 wardrobe').  fit: how the top hangs (FIT below: a kind by name, what differs from the outfit's, or False for the
# pack's tight fit).  Of the face from near (faces.py draw_near: the picture of a person's own the game shows
# from a metre or so): aegyo, bow, socket, stubble, fold, flush, iris_tone; and of both faces crease (a double
# eyelid's fold nearer the lashes or further) and lip_tint (the lips' own colour).
PEOPLE = {
    # 승민 (the film 건축학개론, 2012: a first-year of 1996 in the knock-off sweatshirt): a long oval face, narrow
    # gentle eyes (the lids' fold only at the outer corner) under straight heavy brows that fall a little outward, a
    # straight nose, a full lower lip and a shy smile
    'p01': man('fringe', 'Casual_2', 'Casual_2', 'Casual_2',
                   {'LightBrown': '#f1efe8', 'LightBlue': JEANS['light'], 'Red_Dark': '#e8e6e0', 'feet:White': '#c9c6be',
                    'feet:Bar': '#27345a', 'feet:Lace': '#cfccc4', 'Skin': SKIN['b'], 'Hair': HAIR['black']},
                   'white long-sleeved tee with the GEUSS triangle, baggy light jeans, white trainers; short hair, the '
                   'fringe down over the forehead',
                   paint={'body': [dict(of=('Skin',), to='LightBrown', x=(0, .592)), neckline(('LightBrown',))],
                          'feet': trainers('umc', 'Red_Dark')},
                   prints={'body': [dict(name='geuss', of=('LightBrown',), w=.28, z=1.33)]}, cut='wide',
                   fit=dict(start=.19, sleeve=(.008, .014)),
                   neck=.85, shoulders=dict(square=.8, broad=-.004),
                   face=dict(lid='inner', slant=.0, eye=.96, eye_open=.80, jaw=.95, chin=1.05, taper=.06, gonial=.8, chin_out=1.1, chin_wide=-.06, brow=1.35, brow_tilt=-.05,
                             arch=.3, brow_len=1.02, brow_taper=1.3, brow_soft=1.6, brow_up=-.0012, smile=.0018, mouth=1.24,
                             lip=1.6, nose=1.04, tip_up=.95, tip_round=.9, bridge=.27, nose_w=.98,
                             aegyo=.7, lip_up=.8, lip_ink=1.7, lip_tint=(.80, .44, .45), bow=1.25, iris_tone=.8)),
    # 성훈: a beige checked shirt (체크 남방) worn open over a white tee, its long sleeves down (the pack's short-sleeved
    # shirt and the bare arms to the wrists).  The checks are not in the model: the game draws them on whatever is of
    # the material 'Check' (web/src/characters.js)
    'p02': man('short', 'Adventurer', 'Casual_2', 'Casual_Hoodie',
                     {'Check': '#d6c49c', 'LightGreen': '#f1efe8', 'LightBlue': JEANS['mid'], 'feet:Purple': '#2a2a2e',
                      'Skin': SKIN['c'], 'Hair': HAIR['black']},
                     'beige checked shirt worn open over a white tee, jeans, black canvas shoes; neat short hair, metal glasses',
                     paint={'body': [dict(of=('Green',), to='Check'),
                                     dict(of=('LightGreen',), to='Check', x=(.12, None), z=(1.2, None)),      # (the bands at the armholes)
                                     dict(of=('Skin',), to='Check', x=(.25, .592), group='sleeve'),
                                     neckline(('LightGreen',))],
                            'feet': canvas('Purple', 'White')},
                     sleeves=dict(r0=.066, r1=.044),
                     face=dict(lid='mono', slant=.10, jaw=1.04, eye=.96, smile=.0016, mouth=.96, glasses=True, brow=1.3, arch=.4,
                               brow_len=.86, brow_taper=1.6, nose=.84, nose_curve=.95, tip_up=.9, tip_round=1.3, wing=1.1, bridge=.17, nose_w=1.10)),
    'p03': man('up', 'Casual_Hoodie', 'Casual_2', 'Casual_Hoodie',
                      {'Purple': '#23345e', 'LightBlue': '#a8946a', 'feet:White': '#e8e6e0', 'Skin': SKIN['tan'],
                       'Hair': HAIR['black'], 'Brow': '#0e0b0a'},
                      'oversized navy hoodie, wide khaki cargo trousers, canvas shoes; short hair swept up and back, the sides '
                      'and the back run over with clippers (the scalp shows through), tanned',
                      paint={'body': [neckline(('Purple',), drop=.024, ring=.006, lobe=1.5)], 'feet': canvas('Purple', 'White')},
                      face=dict(lid='mono', slant=.14, jaw=.97, chin=0.98, eye=.98, smile=.0027, mouth=1.08, brow=1.5, brow_tilt=.09,
                                brow_corner=True, brow_peak=.70, brow_drop=1.2, brow_taper=1.3, brow_soft=1.4, nose=1.04, tip_up=.85,
                                bridge=.28)),
    # 성구 (the maker's request: the look of an actor and singer born in 1978; from two photographs, 2011 and 2014): a
    # long face coming down to a round chin, eyes that narrow as he smiles under heavy straight brows set low, a
    # long high nose, a wide grin
    'p04': man('two-block', 'Casual_Hoodie', 'Casual_2', 'Casual_2',
                     {'Purple': '#1d3fa0', 'LightBlue': JEANS['black'], 'Red_Dark': '#f2f2ee', 'feet:Bar': '#1d3fa0',
                      'feet:Lace': '#d6d3cc', 'Skin': SKIN['c'], 'Hair': HAIR['black']},
                     'Yonsei-blue jumper, YONSEI in white across the chest, black jeans, white trainers; a two-block cut, '
                     'the long top swept from a 7:3 parting',
                     paint={'body': [neckline(('Purple',), drop=.024, ring=.006, lobe=1.5)], 'feet': trainers('umc', 'Red_Dark')}, cut='wide',
                     prints={'body': [dict(name='yonsei', of=('Purple',), w=.27, z=1.36)]},
                     shoulders=dict(broad=.004), fit=dict(start=.16),
                     face=dict(lid='double', slant=.03, jaw=1.0, chin=1.0207, cheek=1.02, gonial=.55, taper=.14, chin_out=1.25, chin_wide=-.05, eye=1.0, eye_open=.76, mouth=1.25, smile=.0040,
                               lip=1.2, brow=1.7, arch=.55, brow_len=1.1, brow_peak=.6, brow_up=-.0022, brow_taper=1.5,
                               brow_soft=1.5, nose=1.18, tip_up=.72, tip_round=1.1, bridge=.35, nose_w=1.06,
                               socket=1.4, stubble=1.8, fold=.8, aegyo=.5, lip_up=.55, lip_ink=1.2, iris_tone=.9)),
    'p05': man('curtain-64', 'Casual_2', 'Casual_2', 'Casual_2',
                    {'LightBrown': '#1f2f55', 'Stripe': '#1f8580', 'Stripe2': '#d8742c', 'Collar': '#ece8dc',
                     'LightBlue': JEANS['dark'], 'Red_Dark': '#3a2c24', 'Skin': SKIN['b'], 'Hair': HAIR['dyed'], 'Brow': '#1c1410'},
                    'collared tee in broad navy, teal and orange stripes, wide dark jeans (진청); brown-dyed hair parted 6:4',
                    paint={'body': bands('Stripe', ('LightBrown',), [(1.085, 1.150), (1.280, 1.345)], x=(0, .21))
                           + bands('Stripe2', ('LightBrown',), [(1.185, 1.245), (1.380, 1.440)], x=(0, .21))
                           + [dict(of=('LightBrown',), to='Collar', x=(0, .10), z=(1.495, None)),
                              neckline(('Collar', 'LightBrown'), drop=.034, vee=1.3, lobe=4.0)]}, cut='wide',
                    face=dict(lid='inner', slant=.10, jaw=.97, chin=1.01, smile=.0012, mouth=.98, lip=1.35, brow=1.55, arch=.5, brow_tilt=.04,
                              brow_taper=1.7, brow_len=1.05, brow_gap=-.001, brow_up=-.001, nose=1.10, tip_up=.95, tip_round=.95, bridge=.29,
                              nose_w=1.04)),
    'p06': man('part-side', 'Suit', 'Casual_2', 'Suit',
                      {'Suit': '#27304a', 'White': '#dfe7ee', 'Tie': '#dfe7ee', 'LightBlue': '#b9a67e', 'Black': '#3a2a1f',
                       'Skin': SKIN['a'], 'Hair': HAIR['black']},
                      'navy blazer, light blue shirt, beige cotton trousers (콤비); 2:8 side parting, the fringe swept across',
                      flip=True, fit=False,          # (the maker's word, 2026-11-26: the blazer as the pack cut it)
                      face=dict(lid='inner', slant=.02, jaw=.95, chin=1.02, brow_tilt=-.05, arch=1.1, smile=.0018, brow=.8, brow_len=1.12, brow_gap=.002, brow_taper=.8,
                                nose=.98, tip_up=1.15, tip_round=.7, wing=.9, bridge=.25, nose_w=.92)),
    'p07': man('thin', 'Suit', 'Suit', 'Suit',
                         {'Suit': '#55595f', 'Tie': '#2f4a7a', 'White': '#eceae4', 'Skin': SKIN['c'], 'Hair': HAIR['grey'],
                          'Brow': '#5a5652'}, 'grey suit, blue tie, thinning grey hair, glasses',
                         face=dict(lid='inner', slant=-.02, jaw=1.05, chin=1.03, eye=.93, brow=1.05, brow_tilt=-.06, smile=.0010, age='old',
                                   glasses=True, brow_drop=1.3, brow_soft=2.4, brow_ink=.9, nose=1.0, tip_up=.8, tip_round=1.2, wing=1.1, bridge=.24, nose_w=1.12,
                                   nose_up=-.0015)),
    'p08': man('crop', 'Worker', 'Suit', 'Worker',
                     {'Worker_Vest': '#3d4f6a', 'Worker_Yellow': '#c9c3b2', 'LightBrown': '#c9c3b2', 'Suit': '#3a3f47',
                      'Skin': SKIN['d'], 'Hair': HAIR['dark']}, 'campus staff: navy vest, grey trousers',
                     paint={'body': [neckline(('LightBrown',), ring=.006)]},
                     face=dict(lid='mono', slant=.06, jaw=1.07, eye=.95, arch=.7, smile=.0012, age='mid', brow=1.4, brow_len=.92,
                               brow_taper=1.4, nose=.88, nose_curve=.9, tip_up=.95, tip_round=1.5, wing=1.15, bridge=.18, nose_w=1.14)),
    'p09': woman('half', 'Casual', 'Casual', 'Casual',
                       {'White': '#f4f1e8', 'Orange': JEANS['light'], 'Grey': '#e8e6e0', 'feet:Bar': '#b3262e', 'feet:Lace': '#cfccc4',
                        'feet:Sole': '#c9c6be', 'Skin': SKIN['a'], 'Hair': HAIR['black']},
                       'loose white tee with YONSEI in blue across the chest, wide light jeans (연청), white trainers; long '
                       'black hair, the top half tied back',
                       paint={'body': [neckline(('White',), drop=.030, half=.085, side=.06)], 'feet': trainers('women', 'Grey')}, cut='wide',
                       prints={'body': [dict(name='yonsei_ink', of=('White',), w=.22, z=1.40)]}, 
                       face=dict(lid='inner', slant=.07, eye=1.03, jaw=.99, taper=.18, gonial=.6, smile=.0030, mouth=1.28, lip=1.5, lip_up=.74, lip_ink=1.3, bow=1.2,
                                 lip_tint=(.86, .38, .34), lash=1.2, aegyo=.8, flush=1.7, brow=.9, arch=1.35, brow_peak=.58, brow_len=1.05, brow_up=-.002, brow_soft=1.3,
                                 nose=.80, nose_curve=.9, tip_up=1.2, tip_round=.95, bridge=.20, nose_w=.96, nose_up=.001)),
    'p10': woman('tuck', 'Casual', 'Casual', 'Casual',
                        {'White': '#e7a7b6', 'Orange': '#cdb994', 'Grey': '#f0eee8', 'feet:Bar': '#8d8f92', 'feet:Lace': '#d6d3cc',
                         'feet:Sole': '#cfccc4', 'Skin': SKIN['fair'], 'Hair': HAIR['dark']},
                        'pink knit, wide beige trousers, white trainers; short bob, one side behind the ear',
                        paint={'body': [neckline(('White',), drop=.030, half=.085, side=.06)], 'feet': trainers('women', 'Grey')},
                        bust=1.3, face=dict(lid='inner', slant=.03, jaw=1.01, taper=.12, gonial=.7, chin=0.97, brow_tilt=-.04, smile=.0030, mouth=1.18, lip=1.6, lip_up=.72,
                                  lip_ink=1.3, bow=1.35, lip_tint=(.84, .34, .42), lash=1.15, aegyo=1.0, flush=2.0, brow=1.25, arch=.4, brow_len=.88, brow_taper=1.5,
                                  nose=.72, nose_curve=.85, tip_up=1.45, tip_round=1.25, bridge=.17, nose_w=1.02, nose_up=.002)),
    # 서연 (the film 건축학개론, 2012: a first-year of the college of music in 1996): a round, soft face, large eyes with
    # double lids, straight soft brows, a small nose, a ready smile; long straight hair worn down
    'p11': woman('long', 'Formal', 'Formal', 'Formal',
                         {'LimeGreen': '#a3202c', 'Yoke': '#eadfc8', 'Tee': '#f3f0e8', 'Skirt': JEANS['mid'], 'feet:Red': '#1c1c1f',
                          'Skin': SKIN['fair'], 'Hair': HAIR['black'], 'Band': '#e3c443'},
                         'red knit with a cream band across the chest and the sleeves over a white tee, denim skirt to above '
                         'the knee, black shoes; long straight black hair under a yellow hairband',
                         paint={'body': [dict(of=('Skin',), to='LimeGreen', x=(0, .585)),       # (the sleeves, and a round neck)
                                         # the tee's collar in it: behind the neck a band, in front a round neck
                                         # under the knit's, and skin in that
                                         dict(of=('LimeGreen',), to='Tee', x=(0, .075), y=(-.045, None), z=(1.488, None)),
                                         neckline(('LimeGreen',), to='Tee', drop=.040, half=.085, side=.06),
                                         neckline(('Tee',), drop=.024, half=.068, side=.06),
                                         dict(of=('Gold',), to='LimeGreen'),            # (no belt: the knit hangs over the skirt)
                                         # the knit's band: across the chest, and round the sleeves where the arms, let
                                         # down, bring it level with that; a thin line under it, and one at the cuffs
                                         *bands('Yoke', ('LimeGreen',), [(1.345, 1.392), (1.312, 1.325)], x=(0, .172)),
                                         dict(of=('LimeGreen',), to='Yoke', x=(.172, .226)),
                                         dict(of=('LimeGreen',), to='Yoke', x=(.246, .259)),
                                         dict(of=('LimeGreen',), to='Yoke', x=(.553, .570))],
                                'legs': [dict(of=('LimeGreen',), to='Skirt')],
                                'head': [dict(of=('Hair',), to='Band', y=(-.090, -.062), z=(1.690, None))]},
                         skirt='denim', shoulders=dict(square=1.1),
                         face=dict(lid='double', slant=.03, eye=1.08, eye_open=.90, lash=1.25, jaw=.95, cheek=.99, chin=.98, taper=.16, gonial=.4, brow=1.3,
                                   arch=.25, brow_len=1.0, brow_soft=2.0, brow_up=-.0018, smile=.0026, mouth=1.32, mouth_line=1.3, lip=1.75,
                                   lip_up=.80, lip_ink=1.35, nose=.86, tip_up=.85, tip_round=.8, wing=.9, bridge=.23, nose_w=.90, nose_up=.0,
                                   crease=.62, aegyo=1.0, bow=1.35, flush=1.2, lip_tint=(.80, .34, .38), iris_tone=.7)),
    'p12': woman('shoulder', 'Formal', 'Casual', 'Casual',
                              {'LimeGreen': '#ece4cc', 'Rib': '#dcd2b4', 'Orange': JEANS['black'], 'Grey': '#1f1f24', 'Skin': SKIN['b'],
                               'Hair': HAIR['brown'], 'Bridge': '#9c6c3a', 'Brow': HAIR['dark']},
                              'roomy cream sweatshirt (맨투맨) with a round neck, wide black jeans; brown-dyed hair to the shoulders, '
                              'bleached locks',
                              bridge=[(-18, 3.5), (46, 3.5)],
                              # (the pack's sleeveless top and its bare arms to the wrists, cut roomy; the belt and what is
                              # under it the ribbed hem, a shade darker, as the cuffs and the neck)
                              paint={'body': [dict(of=('Skin',), to='LimeGreen', x=(0, .585)),
                                              dict(of=('Gold',), to='Rib'),
                                              dict(of=('LimeGreen',), to='Rib', x=(0, .22), z=(None, 1.178)),
                                              dict(of=('LimeGreen',), to='Rib', x=(.545, .585)),
                                              dict(of=('LimeGreen',), to='Rib', x=(0, .082), y=(-.045, None), z=(1.492, None)),
                                              neckline(('LimeGreen',), to='Rib', drop=.036, half=.085, side=.06),
                                              neckline(('Rib',), drop=.020, half=.068, side=.06)]},
                              roomy=1.16, cut='wide',
                              face=dict(lid='double', slant=.10, eye=.99, jaw=.96, taper=.22, gonial=.5, chin=0.99, smile=.0024, mouth=1.34, lip=1.5, lip_up=.78, lip_ink=1.35,
                                        bow=1.25, lip_tint=(.58, .23, .25), lash=1.35, aegyo=.4, crease=.8, flush=1.3, brow=.85, arch=1.6, brow_tilt=.05, brow_up=-.0015, brow_corner=True,
                                        brow_peak=.68, brow_drop=1.0, brow_soft=1.3, nose=.84, tip_round=.9, bridge=.22, nose_w=.95)),
    'p13': woman('pixie', 'Suit', 'Casual', 'Casual',
                            {'Black': '#ecdf9e', 'White': '#f2efe6', 'Orange': JEANS['dark'], 'Grey': '#f0eee8', 'feet:Bar': '#27345a',
                             'feet:Lace': '#d6d3cc', 'feet:Sole': '#cfccc4', 'Skin': SKIN['c'], 'Hair': HAIR['black']},
                            'pastel yellow cardigan over a white tee, dark jeans (진청), white trainers; a short cut swept back over '
                            'the ears, metal glasses',
                            paint={'body': [neckline(('White',), drop=.045, half=.058, side=.07)], 'feet': trainers('women', 'Grey')},
                            face=dict(lid='inner', slant=.05, jaw=1.0, taper=.14, gonial=.65, smile=.0026, mouth=1.24, lip=1.4, lip_up=.66, lip_ink=1.1,
                                      lip_tint=(.84, .45, .43), aegyo=.6, flush=1.5, glasses=True, brow=1.5, arch=.8, brow_taper=1.4, brow_soft=2.2,
                                      nose=.76, nose_curve=.96, tip_up=1.05, tip_round=1.3, wing=1.1, bridge=.20, nose_w=1.08)),
    'p14': woman('perm', 'Suit', 'Suit', 'Suit',
                         {'Black': '#2f3644', 'White': '#eef0f2', 'Skin': SKIN['b'], 'Hair': HAIR['dark']},
                         'office staff: navy suit, short permed hair',
                         paint={'body': [neckline(('White',), drop=.045, half=.058, side=.07)]}, face=dict(lid='inner', slant=.0, jaw=1.06, chin=1.03, eye=.95, brow_tilt=-.03, smile=.0014, age='mid',
                                                                                 brow=.9, arch=1.25, brow_len=.96, brow_soft=1.4, nose=.84, tip_up=.85, tip_round=1.1, bridge=.21, nose_w=1.10)),
    # (added last: the faces' cells go by this order)
    'p15': woman('pony', 'Formal', 'Casual', 'Casual',
                          {'LimeGreen': '#f1eee6', 'Stripe': '#27345a', 'Orange': JEANS['mid'], 'Grey': '#f0eee8', 'feet:Bar': '#b3262e',
                           'feet:Lace': '#d6d3cc', 'feet:Sole': '#cfccc4', 'Skin': SKIN['a'], 'Hair': HAIR['black'], 'Band': '#b3262e'},
                          'tight white long-sleeved tee with navy stripes (쫄티), mid-blue jeans, white trainers; a pony tail in a '
                          'red scrunchie',
                          # (the pack's sleeveless top and its bare arms to the wrists; the stripes go on down the arms
                          # at the heights the arms, let down, bring them to)
                          paint={'body': [dict(of=('Skin',), to='LimeGreen', x=(0, .585)),
                                          dict(of=('Gold',), to='LimeGreen'),
                                          *bands('Stripe', ('LimeGreen',), [(z - .013, z + .013) for z in (1.150, 1.206, 1.262, 1.318, 1.374, 1.430)],
                                                 x=(0, .172)),
                                          *[dict(of=('LimeGreen',), to='Stripe', x=(x - .013, x + .013))
                                            for x in (.193, .249, .305, .361, .417, .473, .529)],
                                          neckline(('LimeGreen',), drop=.030, half=.085, side=.06)],
                                 'feet': trainers('women', 'Grey')},
                          face=dict(lid='inner', slant=.06, eye=1.04, jaw=.98, cheek=1.02, taper=.18, gonial=.55, chin=0.98, smile=.0030, mouth=1.30, lip=1.45, lip_up=.70,
                                    lip_ink=1.3, bow=1.15, lip_tint=(.90, .40, .28), lash=1.2, aegyo=.9, flush=1.9, brow=1.0, arch=.9, brow_len=1.0,
                                    brow_soft=1.5, nose=.80, tip_up=1.38, tip_round=.7, bridge=.20, nose_w=1.0, nose_up=.001)),
    'p16': man('curtain', 'Adventurer', 'Casual_2', 'Casual_2',
                     {'Green': '#2f5a45', 'LightGreen': '#1f1f24', 'LightBlue': '#b9a67e', 'Red_Dark': '#3a2c24', 'Skin': SKIN['b'],
                      'Hair': HAIR['black']},
                     'forest-green shirt worn open over a black tee, beige cotton trousers; a long fringe parted in the middle, '
                     'metal glasses',
                     paint={'body': [neckline(('LightGreen',))]},
                     face=dict(lid='inner', slant=.04, jaw=1.0, eye=1.0, smile=.0020, mouth=1.0, glasses=True, brow=1.15, arch=.7,
                               brow_len=.98, brow_taper=1.3, nose=.96, tip_round=.9, bridge=.22, nose_w=1.0)),
    'p17': woman('bang', 'Suit', 'Casual', 'Casual',
                         {'Black': '#5d7fae', 'White': '#f2efe6', 'Orange': '#cdb994', 'Grey': '#f0eee8', 'feet:Bar': '#2f5a45',
                          'feet:Lace': '#d6d3cc', 'feet:Sole': '#cfccc4', 'Skin': SKIN['b'], 'Hair': HAIR['dark']},
                         'denim shirt (청남방) worn open over a white tee, beige cotton trousers, white trainers; hair to the '
                         'shoulders with a straight fringe',
                         paint={'body': [neckline(('White',), drop=.045, half=.058, side=.07)], 'feet': trainers('women', 'Grey')},
                         bust=1.3, face=dict(lid='double', slant=.06, eye=1.06, jaw=.97, taper=.20, gonial=.5, chin=0.99, smile=.0026, mouth=1.24, lip=1.65, lip_up=.80,
                                   lip_ink=1.3, bow=1.3, lip_tint=(.76, .32, .36), lash=1.3, aegyo=.8, crease=.75, flush=1.6, brow=.9, arch=1.1, brow_len=1.0,
                                   brow_soft=1.6, nose=.78, nose_curve=.88, tip_up=1.12, tip_round=1.05, bridge=.19, nose_w=.98, nose_up=.001)),
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
# The men's trunk is a wedge: a chest of 30 cm over a waist of 26 and a pelvis of 23 - 25 cm at the hip joints (clothes
# and all), where a young man's waist is about 29 - 30 cm across and his hips 32 - 33: a cartoon's build.  `girth`
# widens the trunk by height, [(m over the hip joints, the source's units; how much wider)], eased between; `deep` is
# the share of that the trunk also grows from front to back, `seat` how much further the buttocks stand out behind
# at the hips' height.  By place, as the rest: a tee's hem, the waistband under it and the thighs' tops move as one,
# and the trousers are cut on what comes of it (cut_trousers).  The women: wider hips and more of a seat under a
# waist left narrow (`waist` less than it was).
BUILD = {'umc': dict(shoulder=.020, hip=-.022, arm=1.06, hand=.88, finger=.88, neck=.25, waist=0.0, trap=(.030, .056, .140),
                     girth=[(-.24, 0), (-.16, .06), (-.08, .16), (-.02, .26), (.03, .26), (.08, .20), (.16, .15), (.26, .13),
                            (.34, .06), (.42, 0)], deep=.35, seat=.06),
         'women': dict(shoulder=.030, hip=0.0, arm=1.06, hand=.88, finger=.88, neck=.22, waist=.08, trap=(.024, .044, .125, 1.8),
                       girth=[(-.26, 0), (-.16, .06), (-.08, .11), (.0, .11), (.07, .05), (.13, 0)], deep=.2, seat=.20,
                       chest=(.15, .12, .09), collar=(.075, .01, .12))}
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


def hold_chest(ob, arm, C):
    """The women's pack hangs the upper chest on the collar bones (at the armpits' height 0.8 of a vertex is theirs,
    the men's far less): with the arms let down the collar bones tip down and draw the chest in (25.6 cm in the T pose,
    22.8 standing: narrower than the waist), with the arms out in talk they spread it to 28.9.  C: (below, above, floor)
    - the collar bones keep their share from `above` under the shoulder joints up and out past the joints, lose it down
    to `below` under them (all but `floor`), and what they lose goes to the spine's bones the vertex has (else Chest).
    By place, in the source's T pose."""
    if not C:
        return
    mw = ob.matrix_world
    js = arm.matrix_world @ arm.data.bones['UpperArm.L'].head_local
    col = {g.index for g in ob.vertex_groups if g.name.startswith('Shoulder.')}
    spine = {g.index for g in ob.vertex_groups if g.name in ('Chest', 'Torso', 'Abdomen', 'Neck')}
    if not col:
        return
    chest = ob.vertex_groups.get('Chest') or ob.vertex_groups.new(name='Chest')
    for v in ob.data.vertices:
        ws = {g.group: g.weight for g in v.groups if g.weight > 0}
        held = sum(w for gi, w in ws.items() if gi in col)
        if held < 1e-6:
            continue
        c = mw @ v.co
        keep = max(C[2], _smooth(js.z - C[0], js.z - C[1], c.z), _smooth(abs(js.x) - .02, abs(js.x) + .02, abs(c.x)))
        if keep >= 1:
            continue
        free = held * (1 - keep)
        rest = {gi: w for gi, w in ws.items() if gi in spine}
        tot = sum(rest.values())
        for gi in col & ws.keys():
            ob.vertex_groups[gi].add([v.index], ws[gi] * keep, 'REPLACE')
        if tot > 1e-6:
            for gi, w in rest.items():
                ob.vertex_groups[gi].add([v.index], w + free * w / tot, 'REPLACE')
        else:
            chest.add([v.index], free, 'REPLACE')


# The packs hang a top's collar partly on the arms (0.13 - 0.17 of a point 2 cm off the neck is the upper arm's, whose
# joint lies 10 cm out and 10 cm under it): with the arms let down from the T pose the sides of the collar swing 2.5 cm
# out and a round neck 13 cm across stands 19 cm wide, twice the neck's width.  HOLD: what of the top lies within
# the first radius of the neck's axis (m, the source's units, in the T pose) gives the arms' share to the chest, all
# of it, easing to none of it at the second; down to `under` below the neck's joint.
HOLD = {'umc': dict(r=(.090, .135), under=.10), 'women': dict(r=(.085, .125), under=.10)}


def hold_collar(ob, arm, C):
    cn = arm.matrix_world @ arm.data.bones['Neck'].head_local
    mw = ob.matrix_world
    arms = {g.index for g in ob.vertex_groups if g.name.startswith(('UpperArm.', 'LowerArm.'))}
    if not arms:
        return
    chest = ob.vertex_groups.get('Chest') or ob.vertex_groups.new(name='Chest')
    for v in ob.data.vertices:
        ws = {g.group: g.weight for g in v.groups if g.weight > 0}
        held = sum(w for gi, w in ws.items() if gi in arms)
        if held < 1e-6:
            continue
        c = mw @ v.co
        keep = max(_smooth(*C['r'], math.hypot(c.x - cn.x, c.y - cn.y)), 1 - _smooth(cn.z - C['under'], cn.z - C['under'] + .03, c.z))
        if keep >= 1:
            continue
        for gi in arms & ws.keys():
            ob.vertex_groups[gi].add([v.index], ws[gi] * keep, 'REPLACE')
        chest.add([v.index], ws.get(chest.index, 0.0) + held * (1 - keep), 'REPLACE')


# ---------- the women's bust ----------
# The pack's bust is a shelf across the chest whose side view is a triangle: a line down from the collarbone to a
# corner 8 cm under the shoulder joints, and a straight line back from it to the ribs at 45 degrees, on rows of
# points 2 - 4 cm apart.  Seen from the side it is a point.  The faces there are cut finer and the side view is
# redrawn, every upright section for itself: over the chest wall (the line between the surface at `top` and at
# `under`, heights under the shoulder joints) it stands as far out as the pack's did there (x `out`), at `apex`; it
# comes up to that from above as a quarter of a sine and turns back underneath in a round (`round`: 0.5 a quarter of
# an ellipse, 1 a parabola).  Across the chest the shelf is the pack's; `fade`: by the armholes nothing moves.
# A person's own `bust` makes it stand further out (between the armholes) and reach a little lower.
# Lengths in the source's units (x 0.90 in the game).
BUST = dict(top=0.0, under=0.128, apex=0.078, out=0.86, round=0.70, fade=(0.098, 0.117), cuts=2)


def round_bust(ob, arm, size=1.0):
    import bmesh
    from mathutils.bvhtree import BVHTree
    B = BUST
    me, mw = ob.data, ob.matrix_world.copy()
    inv = mw.inverted()
    head = lambda name: arm.matrix_world @ arm.data.bones[name].head_local
    js, cn = head('UpperArm.L'), head('Neck')
    top, reach = B['top'], B['fade'][1]
    under = B['under'] + 0.030 * (size - 1)
    apex = B['apex'] + 0.016 * (size - 1)
    bm = bmesh.new()
    bm.from_mesh(me)
    w = lambda v: mw @ v.co
    front = lambda c: c.y < cn.y - 0.04 and abs(c.x) < reach and top - 0.012 < js.z - c.z < under + 0.012
    faces = [f for f in bm.faces if all(front(w(v)) for v in f.verts)]
    edges = sorted({e for f in faces for e in f.edges}, key=lambda e: e.index)
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=B['cuts'], use_grid_fill=True)
    bm.verts.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    back = inv.to_3x3() @ Vector((0, 1, 0))

    def surface(x, dz):
        # the front of the top, seen from the front (three rays: one through a point of the mesh can slip between
        # the faces round it and come back with the person's back)
        ys = []
        for ox, oz in ((0.0, 0.0), (0.0004, 0.0003), (-0.0003, -0.0004)):
            hit = tree.ray_cast(inv @ Vector((x + ox, cn.y - 0.6, js.z - dz + oz)), back)[0]
            if hit:
                ys.append((mw @ hit).y)
        return min(ys) if ys else None
    n = 24
    moved = {}
    for v in bm.verts:
        c = w(v)
        dz, ax = js.z - c.z, abs(c.x)
        if not (c.y < cn.y - 0.04 and ax < reach and top < dz < under):
            continue
        col = [surface(c.x, top + (under - top) * i / n) for i in range(n + 1)]
        ys = surface(c.x, dz)
        if ys is None or None in col:
            continue
        wall = lambda d: col[0] + (col[n] - col[0]) * (d - top) / (under - top)
        out = max(wall(top + (under - top) * i / n) - col[i] for i in range(n + 1))       # (the pack's shelf here)
        mid = 1 - _smooth(*B['fade'], ax)
        out *= B['out'] + (size - 1) * mid
        t = (dz - apex) / ((apex - top) if dz < apex else (under - apex))
        h = math.cos(math.pi / 2 * t) if t < 0 else (1 - t * t) ** B['round']
        moved[v] = (wall(dz) - out * h - ys) * mid
    for v, dy in moved.items():
        c = w(v)
        c.y += dy
        v.co = inv @ c
    bm.to_mesh(me)
    bm.free()
    me.update()


def shape_body(ob, arm, rig, neck=1.0):
    """The neck, the trapezius, the waist and the trunk's girth of BUILD on one part of a person, in the source's T
    pose: the bones stay where they are.  Both by place alone (the height, and for the neck how far from its axis), so that the head's neck, the neck's
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
    girth, zj = b.get('girth'), head('UpperLeg.L').z
    chest, js = b.get('chest'), head('UpperArm.L')
    hold_chest(ob, arm, b.get('collar'))
    for v in me.vertices:
        c = mw @ v.co
        if chest and abs(c.x) < .3:
            # the rib cage wider about the bust's height (not the arms: nothing past the shoulder joints)
            f = chest[0] * math.exp(-((c.z - (js.z - chest[1])) / chest[2]) ** 2) * (1 - _smooth(abs(js.x), abs(js.x) + .05, abs(c.x)))
            c.x *= 1 + f
            c.y = cn.y + (c.y - cn.y) * (1 + .25 * f)
        if girth and abs(c.x) < .3 and girth[0][0] < c.z - zj < girth[-1][0]:
            f = _cos_interp(girth, c.z - zj)
            c.x *= 1 + f
            c.y = cn.y + (c.y - cn.y) * (1 + b['deep'] * f)
            if c.y > cn.y:                          # (the buttocks: behind the middle, about the hip joints' height)
                c.y = cn.y + (c.y - cn.y) * (1 + b['seat'] * _smooth(-.20, -.06, c.z - zj) * (1 - _smooth(.02, .14, c.z - zj)))
        if b['waist'] and abs(c.x) < .3:
            f = b['waist'] * math.exp(-((c.z - zw) / sw) ** 2)
            c.x *= 1 + f
            c.y = cn.y + (c.y - cn.y) * (1 + .3 * f)
        if b['neck'] and zn - .05 < c.z < zh + .02:
            # all of it from the collarbone up, less under the jaw (the head keeps its size), nothing a hand's width out
            up = _smooth(zn - .05, zn - .015, c.z) * (1 - .7 * _smooth((zn + zh) / 2, zh, c.z)) * (1 - _smooth(zh, zh + .02, c.z))
            f = b['neck'] * neck * up * (1 - _smooth(.075, .11, math.hypot(c.x, c.y - cn.y)))
            c.x *= 1 + f
            c.y = cn.y + (c.y - cn.y) * (1 + .5 * f)
        if tr and zn - .08 < c.z < zh + .03:
            r = math.hypot(c.x, c.y - cn.y)
            if r < tr[2]:
                # (full from the collarbones up to the neck's foot, fading up the neck so slowly that nothing folds)
                up = _smooth(zn - .08, zn - .035, c.z) * (1 - _smooth(zn, zh + .03, c.z)) * _smooth(-.055, -.012, c.y - cn.y)
                held = sum(g.weight for g in v.groups if g.group in arms)
                # (tr[3]: the fall from the neck out, 1.8 steep by the neck and shallow toward the shoulder, as the
                # muscle's line is; without it an even S)
                fall = (1 - _smooth(tr[1], tr[2], r)) if len(tr) < 4 else max(0.0, 1 - (r - tr[1]) / (tr[2] - tr[1])) ** tr[3] if r > tr[1] else 1.0
                c.z += tr[0] * fall * up * (1 - min(1.0, held))
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
# may: its front is laid lower and opened by lay_collar and a neckline).  The packs' tees have a rim standing 3 - 4 cm up the neck, level all round: COLLAR brings it down (the share
# of its height that is left) and dips it at the front (m, the source's units), as a round neck lies.
OPEN_NECK = ('Casual_Hoodie',)
COLLAR = {'Casual_2': (.45, .010), 'Worker': (.45, .010)}


def loosen(ob, part, outfit, arm, roomy=None):
    """Widen the top (body) of one outfit part, in world space: by ROOMY, or a person's own `roomy`."""
    F = (roomy or ROOMY.get(outfit, 1.0)) if part == 'body' else 1.0
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


# Where a top's neck lies.  The packs' chest stands 8 cm before the neck's axis at the height of its joint, the neck's
# own front 4.5 cm: a round neck cut where the tee lies under the joint stood 3.5 cm off the throat, and the skin
# between ran out to it as a ramp, lit from above and paler than the neck.  `pull` draws the front of the top in
# toward the neck (m, the source's units: full from `band` off the neck's radius `rn` out to r[0], none past r[1] and
# none `low` under the joint), so the collar lies at the foot of the neck and the chest slopes down from it.  A hood's
# collar is a roll standing level round the neck 2 - 4 cm over its joint, a cloth across inside it: `dip` lowers the
# front of it (none of it behind the neck), down to where a hood's edges meet under the throat.
LIE = {'Casual_2': dict(pull=.018), 'Worker': dict(pull=.018),
       'Casual_Hoodie': dict(dip=.040, turn=1.5, r=(.105, .165))}
LIE_ALL = dict(pull=0.0, dip=0.0, turn=1.5, rn=.050, band=.035, r=(.095, .150), low=(.11, .04))


def lay_collar(ob, outfit, arm):
    C = dict(LIE_ALL, **LIE.get(outfit, {}))
    if not C['pull'] and not C['dip']:
        return
    me, mw = ob.data, ob.matrix_world.copy()
    inv = mw.inverted()
    skin = _skin_verts(me)
    cn = arm.matrix_world @ arm.data.bones['Neck'].head_local
    for v in me.vertices:
        if v.index in skin:
            continue
        c = mw @ v.co
        dx, dy = c.x - cn.x, c.y - cn.y
        r = math.hypot(dx, dy)
        if r > C['r'][1] or r < 1e-5 or c.z < cn.z - C['low'][0]:
            continue
        f = (1 - _smooth(*C['r'], r)) * _smooth(cn.z - C['low'][0], cn.z - C['low'][1], c.z)
        ca = -dy / r                                         # (1 in front, -1 behind)
        if C['pull']:
            d = C['pull'] * max(0.0, ca) ** C['turn'] * f * _smooth(C['rn'], C['rn'] + C['band'], r)
            c.x -= dx / r * d
            c.y -= dy / r * d
        if C['dip']:
            c.z -= C['dip'] * ((1 + ca) / 2) ** C['turn'] * f
        v.co = inv @ c


# ---------- an even arm ----------
# The men's pack models the arm as muscle under the cloth: thick at the biceps, drawn in at the elbow (4.4 cm from the
# axis on a long-sleeved tee), out again on the forearm (5.8 cm) and in to the wrist.  And the top of a sleeve runs
# out level from the shoulder for 5 cm, 10 cm over the axis, and drops to 6 cm at once: a ledge, which stands out as
# a puffed cap over a groove when the arm hangs.  A sleeve hangs as a tube, and an arm at rest is not flexed.
# The thickness along the arm, on every side of it for itself (the mean distance from the axis, shoulder joint to
# elbow to wrist, of the points within EVEN['near'] along the arm and `round` radians round it), is brought `by` of
# the way to a straight taper fitted to it beyond `cap`, and from the joint to `cap` to an even slope down from what
# the shoulder has at the joint; every point moves to or from the axis by what its place asks, cloth and bare skin
# each for themselves (a short sleeve keeps its hem off the arm).  A short sleeve has no length to fit a taper to
# (fitted to its hem alone the line ran out to a balloon at the shoulder): it goes straight from the joint to its hem.
# Nothing moves at the joint itself or by the wrist (`wrist`: m from it, where it fades and where it is nothing).
EVEN = dict(by=(1.0, 0.6), near=0.016, round=0.7, cap=0.10, wrist=(0.065, 0.025), knob=0.78, slope=0.07)    # (by: cloth, skin)


def even_arms(ob, arm):
    me, mw = ob.data, ob.matrix_world.copy()
    inv = mw.inverted()
    head = lambda name: arm.matrix_world @ arm.data.bones[name].head_local
    skin = _skin_verts(me)
    E = EVEN
    for side in ('L', 'R'):
        held = {g.index for g in ob.vertex_groups if g.name in ('UpperArm.' + side, 'LowerArm.' + side)}
        a, b, c = head('UpperArm.' + side), head('LowerArm.' + side), head('Wrist.' + side)
        la, lb = (b - a).length, (c - b).length

        def place(p):
            """How far along the arm p is, the point of the axis there and how far p is from it."""
            best = None
            for p0, p1, s0, lo, hi in ((a, b, 0.0, -1.0, 1.0), (b, c, la, 0.0, 1.0)):
                t = max(lo, min(hi, (p - p0).dot(p1 - p0) / (p1 - p0).length_squared))
                q = p0.lerp(p1, t)
                if best is None or (p - q).length < best[2]:
                    best = (s0 + t * (p1 - p0).length, q, (p - q).length)
            return best
        # the shoulder's top: the joint lies 9.5 cm under it, so what the arm carries of it swings out as a knob when
        # the arm hangs.  Lower toward the joint (to `knob` of its height over the axis, on the upper side only)
        near = held | {g.index for g in ob.vertex_groups if g.name == 'Shoulder.' + side}
        d = (b - a).normalized()
        for v in me.vertices:
            if sum(g.weight for g in v.groups if g.group in near) < 0.15:
                continue
            p = mw @ v.co
            sv = (p - a).dot(d)
            q = a + d * sv
            up = (p.z - q.z) / max((p - q).length, 1e-6)
            if -E['slope'] < sv < E['cap'] and up > 0:
                f = 1 - (1 - E['knob']) * up * _smooth(-E['slope'], 0.0, sv)
                v.co = inv @ (q + (p - q) * f)
        pts = {}
        for v in me.vertices:
            w = sum(g.weight for g in v.groups if g.group in held)
            if w < 0.3:
                continue
            p = mw @ v.co
            sv, q, r = place(p)
            if 0 < sv < la + lb and r > 1e-4:
                pts[v.index] = (sv, q, r, _smooth(0.3, 0.55, w), math.atan2(p.z - q.z, p.y - q.y))
        for kind in (True, False):
            mine = {i: x for i, x in pts.items() if (i in skin) == kind}
            if len(mine) < 12:
                continue
            ss = [x[0] for x in mine.values()]
            s0, s1 = min(ss), max(ss)
            if s1 - s0 < 0.10:
                continue
            short = not kind and s1 < la + 0.02          # (a short sleeve: the cloth ends before the elbow)
            out = {}
            for i, (sv, q, r, w, th) in mine.items():
                # the others by how nearly they lie on this point's side of the arm (the top, the front ...)
                rnd = [(math.exp(-(((x[4] - th + math.pi) % (2 * math.pi) - math.pi) / E['round']) ** 2), x[0], x[2])
                       for x in mine.values()]

                def here(at):
                    wts = [(g * math.exp(-((x - at) / E['near']) ** 2), y) for g, x, y in rnd]
                    tot = sum(g for g, _ in wts)
                    return sum(g * y for g, y in wts) / tot if tot > 1e-9 else None
                if short:
                    # no length of arm to fit a taper to: straight from what the shoulder has at the joint to the hem
                    a0, a1 = here(s0), here(s1)
                    if a0 is None or a1 is None:
                        continue
                    goal = a0 + (a1 - a0) * (sv - s0) / (s1 - s0)
                    out[i] = q + (mw @ me.vertices[i].co - q) * (1 + (goal / here(sv) - 1) * E['by'][kind] * w)
                    continue
                # the straight taper of that side: least squares on what lies between the shoulder's cap and the wrist
                fit = [(g, x, y) for g, x, y in rnd if E['cap'] < x < la + lb - E['wrist'][1]]
                n = sum(g for g, _, _ in fit)
                if n < 1e-6:
                    continue
                ms, mr = sum(g * x for g, x, _ in fit) / n, sum(g * y for g, _, y in fit) / n
                var = sum(g * (x - ms) ** 2 for g, x, _ in fit)
                k = sum(g * (x - ms) * (y - mr) for g, x, y in fit) / var if var > 1e-9 else 0.0
                line = lambda at: mr + k * (at - ms)
                top = here(s0) if s0 < 0.03 else None        # (what the shoulder stands over the taper at the joint)
                goal = line(sv) + (max(0.0, top - line(s0)) * (1 - _smooth(s0, E['cap'], sv)) if top else 0.0)
                m = E['by'][kind] * w * (1 - _smooth(la + lb - E['wrist'][0], la + lb - E['wrist'][1], sv))
                out[i] = q + (mw @ me.vertices[i].co - q) * (1 + (goal / here(sv) - 1) * m)
            for i, p in out.items():
                me.vertices[i].co = inv @ p
    me.update()


# ---------- a shirt's long sleeves ----------
# A long-sleeved shirt is the pack's short-sleeved one with the bare arms painted as its cloth (PEOPLE's `paint`, the
# rule's group 'sleeve'): a wide sleeve to the elbow with a rolled hem, and out of it an arm's shape, tight and thin.
# A person's `sleeves` (the sleeve's radius at the shoulder and at the cuff, the source's units) makes one sleeve of
# the two, a straight taper about the arm's axis (the shoulder joint to the wrist): the pack's sleeve is drawn in or
# out by what brings its outline to that, and every point of the painted arm is put on it, just inside the hem it
# comes out of.  The last centimetres before the wrist close in on it again, as a buttoned cuff does.
SLEEVE = 'sleeve'


def long_sleeves(ob, arm, r0, r1, cuff=0.03):
    me, mw = ob.data, ob.matrix_world.copy()
    inv = mw.inverted()
    group = ob.vertex_groups.get(SLEEVE)
    if group is None:
        raise SystemExit(f"{ob.name}: no arms painted for the sleeves (a paint rule's group '{SLEEVE}')")
    painted = {v.index for v in me.vertices if any(g.group == group.index and g.weight > 0.5 for g in v.groups)}
    mats = {me.polygons[p].material_index for p in range(len(me.polygons)) if painted.issuperset(me.polygons[p].vertices)}
    cloth = {v for p in me.polygons if p.material_index in mats for v in p.vertices}
    co = {i: mw @ me.vertices[i].co for i in cloth}
    head = lambda name: arm.matrix_world @ arm.data.bones[name].head_local
    for side in ('L', 'R'):
        a, b = head('UpperArm.' + side), head('Wrist.' + side)
        d = (b - a).normalized()
        sx = 1 if a.x > 0 else -1

        def place(c):
            t = (c - a).dot(d)
            return t, (c - a - d * t).length
        mine = [i for i in cloth if co[i].x * sx > abs(a.x) * 0.9]
        end = max(place(co[i])[0] for i in mine if i in painted)
        # the pack's sleeve: its outline, the greatest radius in every centimetre along the arm (the edges' points, not
        # the vertices alone)
        n = int(end / 0.01) + 2
        env = [0.0] * n
        for e in me.edges:
            i, j = e.vertices
            if i in painted or j in painted or i not in co or j not in co or co[i].x * sx < abs(a.x) * 0.9:
                continue
            for k in range(5):
                t, r = place(co[i].lerp(co[j], k / 4))
                if 0 <= t < n * 0.01 and r < 0.13:
                    env[int(t / 0.01)] = max(env[int(t / 0.01)], r)
        hem = max(k for k in range(n) if env[k])
        for k in range(1, n):
            env[k] = env[k] or env[k - 1]
        env = [max(env[max(0, k - 1):k + 2]) for k in range(n)]
        env = [sum(env[max(0, k - 1):k + 2]) / len(env[max(0, k - 1):k + 2]) for k in range(n)]
        for i in mine:
            c = co[i]
            t, r = place(c)
            if r > 0.13 or r < 1e-5 or t < 0.05:
                continue
            want = r0 + (r1 - r0) * min(1.0, t / end)
            if i in painted:
                shut = _smooth(end - cuff, end - 0.002, t)
                f = want * (0.97 + 0.03 * _smooth(hem * 0.01, hem * 0.01 + 0.05, t)) / r * (1 - shut) + shut
            else:
                f = 1 + (want / max(_lerp_at(env, t / 0.01 - 0.5), 1e-4) - 1) * _smooth(0.05, 0.14, t)
            axis = a + d * t
            co[i] = axis + (c - axis) * f
    for i in cloth:
        me.vertices[i].co = inv @ co[i]
    ob.vertex_groups.remove(group)


# ---------- how a top hangs ----------
# The packs' tops are the body with a colour on it: the cloth follows the chest, the bust and the hollow of the back,
# is drawn in at the waist and ends at the waistband, and a sleeve is the arm.  Loosened about its middle (ROOMY) it is
# the same shape a size larger: it still reads as a tight top (쫄티).  Cloth hangs: from the widest place over it
# straight down, across a hollow and not into it.
# hang_top, on the built rest pose after the trousers are cut: the outline of the trunk (the top, and the trousers
# under its hem) round its upright axis, every centimetre of height; pulled tight round (the hull of every level:
# across the hollow between the breasts and down the spine) and then from above (the hull of every upright line from
# the armpits down: from the bust or the shoulder blades to the hips).  The top goes `hang` of the way out to that,
# and `ease` further (m: at the armpits, at the hem; `side` of it at the sides, where the arms hang), every point
# by what the outermost cloth at its place moves (a tee under an open shirt stays under it).  Its hem is let down
# to `hem` over the hip joints (the cloth slides down the body from `start` under the shoulder joints: stripes
# stretch evenly, what is printed on the chest stays as it is) and turned in by `turn`, so that nobody looks up into
# it.  Nothing moves from the armpits up.  Lengths in the source's units (x 0.93 men, 0.90 women in the game).
# A person's own `fit`: one of these by name, a dict of what differs from the outfit's, or False: the pack's tight
# fit.
FIT = {
    'tee': dict(hang=1.0, ease=(.008, .022), side=.5, hem=-.020, start=.07, turn=.022, sleeve=(.006, .024)),
    'shirt': dict(hang=1.0, ease=(.008, .024), side=.5, hem=-.035, start=.07, turn=.022, sleeve=(.004, .018)),
    'hood': dict(hang=.6, ease=(.0, .004), side=.5, hem=None, start=.07, turn=.020, sleeve=None, cap=False),
    'jacket': dict(hang=.8, ease=(.004, .016), side=.5, hem=-.050, start=.09, turn=.020, sleeve=(.002, .008)),
    'vest': dict(hang=.8, ease=(.004, .012), side=.5, hem=-.010, start=.07, turn=.020, sleeve=(.004, .016)),
}
# The men's tops only.  The women's were hung the same way for a day (2026-11-26: tees, knits, a sweatshirt and
# cardigans, the values in reference/고증 4.11) and taken back at the maker's word (「여자 캐릭터들은 이전 핏이 나은 것
# 같다」): they keep the pack's fit.
FITS = {('umc', 'Casual_2'): 'tee', ('umc', 'Adventurer'): 'shirt', ('umc', 'Casual_Hoodie'): 'hood', ('umc', 'Suit'): 'jacket',
        ('umc', 'Worker'): 'vest'}
HANG_RAYS = 96                # directions round the trunk
HANG_ARM = (0.3, 0.7)         # what the arms hold so much of is a sleeve: none of it moves with the trunk


def fit_of(spec):
    own = spec.get('fit')
    kind = own if isinstance(own, str) else FITS.get((spec['rig'], spec['parts']['body']))
    if own is False or kind is None:
        return None
    C = dict(FIT[kind])
    if isinstance(own, dict):
        C.update(own)
    return C


def _round_hull(rs):
    """Radii in evenly spaced directions round a middle, pulled tight: the radii of the convex hull of their points."""
    n = len(rs)
    pts = sorted((r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i, r in enumerate(rs))
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    half = []
    for seq in (pts, pts[::-1]):
        h = []
        for q in seq:
            while len(h) >= 2 and cross(h[-2], h[-1], q) <= 0:
                h.pop()
            h.append(q)
        half.append(h[:-1])
    hull = half[0] + half[1]
    out = []
    for i, r in enumerate(rs):
        dx, dy = math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)
        best = r
        for (x0, y0), (x1, y1) in zip(hull, hull[1:] + hull[:1]):
            ex, ey = x1 - x0, y1 - y0
            den = dx * ey - dy * ex
            if abs(den) < 1e-12:
                continue
            t = (x0 * ey - y0 * ex) / den
            u = (x0 * dy - y0 * dx) / den
            if t > 0 and -1e-9 <= u <= 1 + 1e-9:
                best = max(best, t)
        out.append(best)
    return out


def hang_top(body, legs, arm, C):
    import bmesh
    from mathutils.bvhtree import BVHTree
    me, mw = body.data, body.matrix_world.copy()
    inv = mw.inverted()
    head = lambda name: arm.matrix_world @ arm.data.bones[name].head_local
    js, zj = head('UpperArm.L'), head('UpperLeg.L').z
    skin = _skin_verts(me)
    arms = {g.index for g in body.vertex_groups if g.name.startswith(('UpperArm.', 'LowerArm.', 'Wrist.'))}
    held = [sum(g.weight for g in v.groups if g.group in arms) for v in me.vertices]
    co = [mw @ v.co for v in me.vertices]
    cloth = [i for i in range(len(co)) if i not in skin and held[i] < HANG_ARM[1]]
    trunk = [i for i in cloth if held[i] < HANG_ARM[0] and abs(co[i].x) < abs(js.x) + .03]
    z_top = js.z - .055                             # the armpits
    z_was = min(co[i].z for i in trunk)             # the hem
    z_hem = z_was if C['hem'] is None else min(z_was, zj + C['hem'])
    z_from = js.z - C['start']
    low = [co[i] for i in trunk if co[i].z < z_top]
    cy = (min(c.y for c in low) + max(c.y for c in low)) / 2
    # the outline: rays in toward the axis, on the trunk of the top (not its sleeves) and on the legs
    # (a sleeve: what the arms hold, and whatever lies out past the shoulder joints at their height - the collar
    # bones and the chest hold the top of some packs' sleeves)
    sleeve = lambda c: abs(c.x) > abs(js.x) + .01 and c.z > js.z - .11
    polys = [tuple(p.vertices) for p in me.polygons if all(held[v] < HANG_ARM[1] and not sleeve(co[v]) for v in p.vertices)]
    tb = BVHTree.FromPolygons(co, polys)
    lw = legs.matrix_world
    tl = BVHTree.FromPolygons([lw @ v.co for v in legs.data.vertices], [tuple(p.vertices) for p in legs.data.polygons])
    dz, n = 0.01, HANG_RAYS
    z0 = z_hem - 0.02
    m = int(math.ceil((z_top + .04 - z0) / dz)) + 1
    dirs = [(math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)) for i in range(n)]

    def reach(tree, i, z):
        dx, dy = dirs[i]
        hit = tree.ray_cast(Vector((dx, cy + dy, z)), Vector((-dx, -dy, 0)), 1.0)
        return 1 - hit[3] if hit[0] is not None else 0.0
    Eb = [[reach(tb, i, z0 + j * dz) for i in range(n)] for j in range(m)]
    El = [[reach(tl, i, z0 + j * dz) for i in range(n)] for j in range(m)]
    jt = min(m - 1, int(round((z_top - z0) / dz)))  # (the hull from above begins at the armpits)
    Ec = [list(row) for row in Eb]
    if C.get('cap', True):
        # (the packs' tops widen to their hems, and are widened more there by ROOMY: a top hangs from the chest, the
        # bust or the shoulder blades, so under them it is no wider than there - but where the hips are)
        jc = max(0, int((z_top - .12 - z0) / dz))
        for i in range(n):
            most = max(Eb[j][i] for j in range(jc, jt + 1))
            for j in range(jc):
                Ec[j][i] = min(Eb[j][i], most)
    E = [[max(a, b) for a, b in zip(ra, rb)] for ra, rb in zip(Ec, El)]
    # (under the hem the top's own outline is what it is at the hem: a ray there misses, or finds the lid some packs
    # shut a jacket with from below, well inside its edge - the edge then went out by that much, a brim)
    for i in range(n):
        for j in range(min(m - 2, int((z_was + .03 - z0) / dz)), -1, -1):
            if Eb[j][i] < Eb[j + 1][i] - .012:
                Eb[j][i] = Eb[j + 1][i]
    for j in range(m):                               # (a ray that slipped through takes its neighbours')
        for i in range(n):
            if E[j][i] < .02:
                E[j][i] = max(E[j][i - 1], E[j][(i + 1) % n], E[max(0, j - 1)][i], E[min(m - 1, j + 1)][i])
    R = [_round_hull(row) for row in E]
    G = [list(row) for row in R]
    for i in range(n):
        col = _hull([R[j][i] for j in range(jt + 1)], 1)
        for j in range(jt + 1):
            G[j][i] = col[j]
    for j in range(m):
        z = z0 + j * dz
        t = max(0.0, min(1.0, (z_top - z) / max(z_top - z_hem, 1e-4)))
        for i in range(n):
            ease = (C['ease'][0] + (C['ease'][1] - C['ease'][0]) * t) * (C['side'] + (1 - C['side']) * abs(dirs[i][1]))
            G[j][i] = E[j][i] + (G[j][i] - E[j][i]) * C['hang'] + ease

    for _ in range(2):                               # (no crease where the string leaves the body: 2 cm either way)
        G = [[sum(G[max(0, min(m - 1, j + q))][i] for q in (-2, -1, 0, 1, 2)) / 5 for i in range(n)] for j in range(m)]
    # (and clear of the trousers by more than a broad face of the top sags between its corners over a round seat)
    G = [[max(g, l + .012) if l > .02 else g for g, l in zip(rg, rl)] for rg, rl in zip(G, El)]

    def at(grid, th, z):
        fi = (th / (2 * math.pi) * n) % n
        fj = max(0.0, min(m - 1.001, (z - z0) / dz))
        i, j = int(fi), int(fj)
        a, b = fi - i, fj - j
        i1 = (i + 1) % n
        return (grid[j][i] * (1 - a) + grid[j][i1] * a) * (1 - b) + (grid[j + 1][i] * (1 - a) + grid[j + 1][i1] * a) * b
    drop = z_was - z_hem
    moved = {}
    for i in cloth:
        c = co[i]
        if c.z > z_top + .02:
            continue
        w = (1 - _smooth(*HANG_ARM, held[i])) * (1 - _smooth(z_top - .04, z_top + .02, c.z))
        if w <= 0 or sleeve(c):
            continue
        th, r = math.atan2(c.y - cy, c.x), math.hypot(c.x, c.y - cy)
        z = c.z - drop * max(0.0, min(1.0, (z_from - c.z) / max(z_from - z_was, 1e-4))) * (1 - _smooth(*HANG_ARM, held[i]))
        # (where the outermost cloth is at this very place: a ray of its own, as the grid's rows, a centimetre apart,
        # round a sharp fold off - under the bust's shelf a point was taken for 1 cm inside the cloth and left there)
        hit = tb.ray_cast(Vector((math.cos(th), cy + math.sin(th), c.z)), Vector((-math.cos(th), -math.sin(th), 0)), 1.0)
        was = 1 - hit[3] if hit[0] is not None else at(Eb, th, c.z)
        if was < r - 1e-4:                            # (the point itself is the outermost: a ray can slip past an edge)
            was = r if r - was < .03 else was
        if c.z < z_was + .03:                        # (a shirt's tail under a vest's hem is under it, not the outermost)
            was = max(was, at(Eb, th, c.z))
        if was < .02:
            was = at(E, th, c.z)
        w *= 1 - _smooth(.02, .05, r - was)          # (what stands off the trunk is a sleeve, whatever holds it)
        if w <= 0:
            continue
        r2 = max(.01, r + (at(G, th, z) - was) * w)
        moved[i] = Vector((r2 * math.cos(th), cy + r2 * math.sin(th), z))
    for i, c in moved.items():
        me.vertices[i].co = inv @ c
    me.update()
    if not C.get('turn'):
        return
    # the hem turned in: a strip from its edge in toward the body, facing down
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    rim = [e for e in bm.edges if e.is_boundary and all(v.index in moved and (mw @ v.co).z < z_hem + .05 for v in e.verts)
           and e.link_faces[0].material_index < len(me.materials)
           and not me.materials[e.link_faces[0].material_index].name.startswith('Skin')]
    if rim:
        out = bmesh.ops.extrude_edge_only(bm, edges=rim)
        new = [g for g in out['geom'] if isinstance(g, bmesh.types.BMVert)]
        for v in new:
            c = mw @ v.co
            r = math.hypot(c.x, c.y - cy)
            f = max(.02, r - C['turn']) / max(r, 1e-6)
            v.co = inv @ Vector((c.x * f, cy + (c.y - cy) * f, c.z + .004))
        for f in {f for v in new for f in v.link_faces}:
            f.normal_update()
            if (mw.to_3x3() @ f.normal).z > 0:
                f.normal_flip()
    bm.to_mesh(me)
    bm.free()
    me.update()


def ease_sleeves(ob, arm, C):
    """A modelled sleeve wider (FIT's `sleeve`: m at the shoulder's end of it, and at its hem or its cuff): every
    point of its cloth away from the arm's axis, the under side all of it and the top a quarter (the arm let down, a
    sleeve lies on the outside of the arm and hangs off the inside).  Arms painted as sleeves go with them.  (Tried
    and dropped: every sleeve a round tube of its own about the arm.  It stood off the shoulder as a pad and hung
    under the forearm as a bag.)"""
    if not C.get('sleeve'):
        return
    e0, e1 = C['sleeve']
    me, mw = ob.data, ob.matrix_world.copy()
    inv = mw.inverted()
    skin = _skin_verts(me)
    head = lambda name: arm.matrix_world @ arm.data.bones[name].head_local
    for side in ('L', 'R'):
        held = {g.index for g in ob.vertex_groups if g.name in ('UpperArm.' + side, 'LowerArm.' + side)}
        a, b = head('UpperArm.' + side), head('Wrist.' + side)
        d = (b - a).normalized()
        pts = {}
        for v in me.vertices:
            if v.index in skin:
                continue
            w = sum(g.weight for g in v.groups if g.group in held)
            if w < 0.3:
                continue
            p = mw @ v.co
            t = (p - a).dot(d)
            q = a + d * t
            if t > .02 and 1e-4 < (p - q).length < .14:
                pts[v.index] = (t, q, p, _smooth(0.3, 0.6, w))
        if len(pts) < 8:
            continue
        end = max(x[0] for x in pts.values())
        long = end > (b - a).length - .08            # (to the wrist: its cuff stays on it)
        for i, (t, q, p, w) in pts.items():
            u = (p - q).normalized()
            e = (e0 + (e1 - e0) * _smooth(.03, end, t)) * _smooth(.02, .10, t) * (.35 + .65 * (1 - u.z) / 2) * w
            if long:
                e *= 1 - .7 * _smooth(end - .04, end, t)
            me.vertices[i].co = inv @ (p + u * e)
    me.update()


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
# the broad stripes of a collared tee, a shirt's long sleeves, a knit's sleeves on a sleeveless top.  A person's
# `paint` lists, by part, boxes in the source's T pose (metres; the arms lie along x, the front is -y): the faces of
# the materials `of` whose middle lies inside become the material `to` (an existing one of the part, or a new one
# with a colour of its own in `colors`), and the mesh is cut along the box's sides first, so the edge is straight.
# x is taken either side of the middle (|x|); a bound left out is open.
# `group`: the painted faces' points are also put in the vertex group of that name (long_sleeves reads 'sleeve').
# `neck` (in place of a box): a neckline.  The packs' tops begin at the foot of the neck, as a turtleneck does; a
# round-necked tee or a V neck lies lower and shows the skin between the neck and the chest.  What of the top's front
# lies over a line, seen from the front, becomes `to`: the line hangs `drop` under the neck's joint in the middle and
# rises (as a cube: a flat bottom and steep sides) by `side` at `half` from the middle, so it closes at the sides of
# the neck (wider, it ran out over the shoulders, whose tops stand as high as the neck's foot); `vee` (m a m to
# either side) makes it a V; `lean` raises it toward the neck (m a m back from the front of the chest: the line then
# follows the chest's round, and its hollows).  neckline() (above PEOPLE) writes such a rule.

def paint(ob, rules, arm=None, bib=False):
    import bmesh
    me, mw = ob.data, ob.matrix_world
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(mw)
    for rule in rules:
        if rule.get('neck'):
            _paint_neck(ob, bm, rule, arm.matrix_world @ arm.data.bones['Neck'].head_local, bib)
            continue
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
        group = None
        if rule.get('group'):                        # (the points of what is painted, kept for a later step)
            group = (ob.vertex_groups.get(rule['group']) or ob.vertex_groups.new(name=rule['group'])).index
            dl = bm.verts.layers.deform.verify()
        for f in bm.faces:
            if f.material_index in src and inside(f.calc_center_median()):
                f.material_index = to
                n += 1
                if group is not None:
                    for v in f.verts:
                        v[dl][group] = 1.0
        if not n:
            raise SystemExit(f'{ob.name}: the box of {rule["to"]} ({box}) holds no face of {rule["of"]}')
    bm.transform(mw.inverted())
    bm.to_mesh(me)
    bm.free()


def _paint_neck(ob, bm, rule, cn, bib=False):
    """A neckline (see paint): the front faces of `of` over the line become `to`, cut along it first.  `bib` (the
    men, whose bared skin is the neck's own: neck_bib): a line with a `ring` is only marked, for neck_bib to cut."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    me = ob.data
    N = rule['neck']
    names = [m.name.split('.')[0] if m else '' for m in me.materials]
    src = {i for i, n in enumerate(names) if n in rule['of']}
    if not src:
        raise SystemExit(f'{ob.name}: nothing of {rule["of"]} for a neckline')
    if rule['to'] not in names:
        me.materials.append(colour_material(rule['to'], (0.5, 0.5, 0.5, 1)))
        names.append(rule['to'])
    to = names.index(rule['to'])
    if bib and N.get('ring') and rule['to'] == 'Skin':
        dl = bm.verts.layers.deform.verify()
        round_ = (ob.vertex_groups.get(ROUND) or ob.vertex_groups.new(name=ROUND)).index
        # (and the top's own skin there, an open collar's: the neck's takes its place)
        own = src | {i for i, n in enumerate(names) if n == 'Skin'}
        for f in bm.faces:
            if f.material_index in own and all(math.hypot(v.co.x, v.co.y - cn.y) < 0.13 and v.co.z > cn.z - 0.06 for v in f.verts):
                for v in f.verts:
                    v[dl][round_] = 1.0
        return
    zc = cn.z - N['drop']
    hit = BVHTree.FromBMesh(bm).ray_cast(Vector((0.0004, cn.y - 0.6, zc)), Vector((0, 1, 0)))[0]
    if hit is None or hit.y > cn.y - 0.02:
        raise SystemExit(f'{ob.name}: no chest {N["drop"]} m under the neck for a neckline')
    lean = N['lean']
    # over the surface z >= zc + lean (y - the chest's) + side |x / half|^3 + vee |x| (a round neck's bottom is
    # flat and its sides steep): cut and tested by its tangent planes (it is convex: what lies over it lies over
    # all of them)
    half, side, vee = N['half'], N['side'], N['vee']
    sides = []
    for t in (-1.1, -.9, -.7, -.5, -.25, .25, .5, .7, .9, 1.1):
        x0, sx = half * t, (1 if t > 0 else -1)
        sides.append((Vector((x0, hit.y, zc + side * abs(t) ** 3 + vee * abs(x0))),
                      Vector((-sx * (3 * side * t * t / half + vee), -lean, 1))))
    if not vee:                                            # (the bottom itself: level)
        sides.append((Vector((0, hit.y, zc)), Vector((0, -lean, 1))))
    over = lambda c: c.y < cn.y and all((c - co).dot(no) >= 0 for co, no in sides)        # noqa: E731
    near = lambda f: all(abs(v.co.x) < 0.15 and v.co.z > zc - 0.03 for v in f.verts)      # noqa: E731
    for co, no in sides + [(Vector((0, cn.y, 0)), Vector((0, 1, 0)))]:
        fs = [f for f in bm.faces if f.material_index in src and near(f)]
        geom = fs + list({e for f in fs for e in f.edges}) + list({v for f in fs for v in f.verts})
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no)
    n = 0
    bare = None
    if rule['to'] == 'Skin':                               # (what is bared: neck_bib makes the men's of the neck itself)
        bare = (ob.vertex_groups.get(BARE) or ob.vertex_groups.new(name=BARE)).index
        dl = bm.verts.layers.deform.verify()
    for f in bm.faces:
        if f.material_index in src and near(f) and over(f.calc_center_median()):
            f.material_index = to
            n += 1
            if bare is not None:
                for v in f.verts:
                    v[dl][bare] = 1.0
    if not n:
        raise SystemExit(f'{ob.name}: the neckline of {rule["to"]} holds no face of {rule["of"]}')


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


# ---------- a skirt's cut ----------
# The pack's skirt is a bell: at its hem it stands 9 cm before the thighs and 7 cm behind them.  Its halves hang on
# the thighs, so on somebody sitting all of it turns forward with them: the front then floats those 9 cm over the lap
# and the back hangs under the knees, before the bench.  A denim skirt of 1997 falls nearly straight from the hips: the
# skirt is drawn in from the hip joints down to a hem that keeps `front` / `back` of ease off the thighs there and is
# `flare` wider a side than the hips, and let down to `hem` over the knee joint (the pack's hem is higher behind than
# in front).  Seated it lies on the thighs, its back between them and the seat.
# It also gets the trousers' coordinates (LEG), so the game draws it as denim: the side seams, the pockets, the wash on
# the front and the seat.  Its hem is `top` of a trouser leg's height (0 a trouser hem, 0.5 the knee, 1 the hip joint),
# so no knee is worn pale on it; `back_turn`: how much further round a leg the back of a half of the skirt goes than
# round itself.  Lengths in the source's units.
# `back` is all but nothing: seated, what the hem stands off the back of the thighs hangs under them, before the bench
# and into it.  And the hem is closed by a dark face just inside it (`inside`: its colour), looking down: from the
# front of somebody sitting one saw up the skirt to the inside of its back and the bench through it; now a shadow.
SKIRTS = {'denim': dict(hem=0.075, front=0.016, back=0.026, flare=0.008, top=0.60, back_turn=1.58, inside='#0e1118')}


def cut_skirt(ob, arm, C):
    me, mw = ob.data, ob.matrix_world.copy()
    inv = mw.inverted()
    names = [m.name if m else '' for m in me.materials]
    k = names.index('Skirt~new')
    sk, body = set(), set()
    for p in me.polygons:
        (sk if p.material_index == k else body).update(p.vertices)
    body -= sk
    head = lambda name: arm.matrix_world @ arm.data.bones[name].head_local
    zj = (head('UpperLeg.L').z + head('UpperLeg.R').z) / 2
    zk = (head('LowerLeg.L').z + head('LowerLeg.R').z) / 2
    co = {i: mw @ me.vertices[i].co for i in sk}
    zt = max(c.z for c in co.values())
    # the hem: the skirt's open edge below the hips
    edges = {}
    for p in me.polygons:
        if p.material_index == k:
            for e in p.edge_keys:
                edges[e] = edges.get(e, 0) + 1
    at_hem = {i for e, n in edges.items() if n == 1 for i in e if co[i].z < zj - 0.1}
    z_low = sum(co[i].z for i in at_hem) / len(at_hem)
    hem = zk + C['hem']
    ext = lambda cs: (max(abs(c.x) for c in cs), min(c.y for c in cs), max(c.y for c in cs))
    (x0, f0, b0), (x1, f1, b1) = ext([c for c in co.values() if abs(c.z - zj) < 0.035]), ext([co[i] for i in at_hem])
    # (the legs under the hem; behind, as far back as the thighs come anywhere over the hem's lower third)
    thigh = [c for c in (mw @ me.vertices[i].co for i in body) if abs(c.z - hem) < 0.045]
    hams = [c for c in (mw @ me.vertices[i].co for i in body) if hem - 0.02 < c.z < hem + (zj - hem) * 0.4]
    X1, F1, B1 = x0 + C['flare'], min(c.y for c in thigh) - C['front'], max(c.y for c in hams) + C['back']
    att = me.attributes.get(LEG) or me.attributes.new(LEG, 'FLOAT_VECTOR', 'POINT')
    legs = [0.0] * (3 * len(me.vertices))
    att.data.foreach_get('vector', legs)
    for i, c in co.items():
        t = 1.0 if i in at_hem else max(0.0, min(1.0, (zj - c.z) / (zj - z_low)))
        xa, fa, ba = x0 + (x1 - x0) * t, f0 + (f1 - f0) * t, b0 + (b1 - b0) * t
        xb, fb, bb = x0 + (X1 - x0) * t, f0 + (F1 - f0) * t, b0 + (B1 - b0) * t
        if t > 0:
            c.x *= xb / xa
            c.y = fb + (c.y - fa) / (ba - fa) * (bb - fb)
            c.z = zj - t * (zj - hem)
        # round a half of the skirt as round a trouser leg: the front and the side seam where a leg has them, the
        # back drawn out (the middle of the back a leg's back and inside), so each half has its pocket in its middle
        a = math.atan2(abs(c.x) / xb, -((c.y - fb) / (bb - fb) * 2 - 1))
        a = a if a < math.pi / 2 else math.pi / 2 + (a - math.pi / 2) * C['back_turn']
        v = C['top'] + (1 - C['top']) * (1 - t) if c.z <= zj else 1 + 0.2 * (c.z - zj) / max(zt - zj, 1e-4)
        legs[3 * i:3 * i + 3] = (0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a), v / LEG_TOP)
        me.vertices[i].co = inv @ c
    att.data.foreach_set('vector', legs)
    # Each half is all its own thigh's below the hip joints.  The pack leaves a tenth of the middle of a half's back
    # to the other thigh and the hips: walking, that much of it stayed behind the thigh swinging back (3 cm at the
    # hem, more than the ease there), and the thigh came out through the cloth.
    own = {1: ob.vertex_groups['UpperLeg.L'], -1: ob.vertex_groups['UpperLeg.R']}
    lent = [g for g in (own[1], own[-1], ob.vertex_groups.get('Body')) if g]
    for i, c in co.items():
        if c.z >= zj or abs(c.x) < 1e-4:
            continue
        mine = own[1 if c.x > 0 else -1]
        ws = {g.group: g.weight for g in me.vertices[i].groups}
        back = sum(ws.get(g.index, 0.0) for g in lent if g is not mine)
        if back > 0:
            mine.add([i], ws.get(mine.index, 0.0) + back, 'REPLACE')
            for g in lent:
                if g is not mine and g.index in ws:
                    g.remove([i])
    me.update()
    # The two halves hang on a thigh each, but the points down the middle, front and back, were half one's and half
    # the other's: walking, the leg that swings back (or forward) came out through the cloth beside them.  So the
    # middle is slit from under the hip joints down, each side's points all its own thigh's, and the slit is closed
    # by a gusset: nothing wide standing, cloth drawn across from one thigh to the other as they part.
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    dl = bm.verts.layers.deform.verify()
    uvl = bm.loops.layers.uv.get(ATLAS_UV)
    world = lambda v: mw @ v.co
    is_mid = lambda v: abs(world(v).x) < 1e-4 and world(v).z < zj
    skirt_faces = [f for f in bm.faces if f.material_index == k]
    seam = sorted({e for f in skirt_faces for e in f.edges if all(is_mid(v) for v in e.verts)}, key=lambda e: e.index)
    cy = sum(c.y for c in co.values()) / len(co)
    bmesh.ops.split_edges(bm, edges=seam)
    gl, gr = ob.vertex_groups['UpperLeg.L'].index, ob.vertex_groups['UpperLeg.R'].index
    sides = {}                                             # (front or back, height) -> {side: the vertex}
    for v in bm.verts:
        if not is_mid(v) or not any(f.material_index == k for f in v.link_faces):
            continue
        xs = [f.calc_center_median().x for f in v.link_faces]
        if min(xs) < 0 < max(xs):                          # (the slit's upper end: still both sides')
            continue
        sd = 1 if (mw @ Vector((sum(xs) / len(xs), 0, 0))).x > 0 else -1
        own, other = (gl, gr) if sd > 0 else (gr, gl)
        w = v[dl].get(own, 0.0) + v[dl].get(other, 0.0)
        if other in v[dl]:
            del v[dl][other]
        v[dl][own] = w
        c = world(v)
        sides.setdefault((c.y > cy, round(c.z, 4)), {})[sd] = v
    for back in (False, True):
        col = sorted((z, d) for (b_, z), d in sides.items() if b_ == back and len(d) == 2)
        used = {v for _, d in col for v in d.values()}
        ends = [v for v in bm.verts if v not in used and abs(world(v).x) < 1e-4 and (world(v).y > cy) == back and col
                and col[-1][0] - 1e-3 < world(v).z < zj + 0.12 and any(f.material_index == k for f in v.link_faces)]
        made = []
        if col and ends:
            apex = min(ends, key=lambda v: world(v).z)
            made.append(bm.faces.new((apex, col[-1][1][1], col[-1][1][-1])))
        for (z0, lo), (z1, hi) in zip(col, col[1:]):
            made.append(bm.faces.new((lo[1], hi[1], hi[-1], lo[-1])))
        for f in made:
            f.material_index = k
            f.smooth = True
            if uvl is not None:
                for lp in f.loops:
                    lp[uvl].uv = BLANK_UV
    if C.get('inside'):
        if 'SkirtIn' not in MADE:
            MADE['SkirtIn'] = colour_material('SkirtIn~new', srgb_to_linear(C['inside']))
        me.materials.append(MADE['SkirtIn'])
        edges = {}
        for f in bm.faces:
            if f.material_index == k:
                for e in f.edges:
                    edges[e] = edges.get(e, 0) + 1
        bm.verts.index_update()
        ring = sorted({v for e, n in edges.items() if n == 1 for v in e.verts if world(v).z < zj - 0.1}, key=lambda v: v.index)
        mid = sum((v.co for v in ring), Vector()) / len(ring)
        ring.sort(key=lambda v: (round(math.atan2(v.co.y - mid.y, v.co.x - mid.x), 3), v.co.x, v.index))
        up = (inv.to_3x3() @ Vector((0, 0, 1))).normalized()
        lift = up * 0.012                                # (just inside the hem: the hem's own edge stays the skirt's)
        new = []
        for v in ring:
            n = bm.verts.new(v.co + lift)
            for g, w in v[dl].items():
                n[dl][g] = w
            new.append(n)
        c = bm.verts.new(mid + lift)
        tot = {}
        for v in ring:
            for g, w in v[dl].items():
                tot[g] = tot.get(g, 0.0) + w / len(ring)
        for g, w in tot.items():
            c[dl][g] = w
        k_in = len(me.materials) - 1
        for a, b in zip(new, new[1:] + new[:1]):
            if (a.co - b.co).length < 1e-6:
                continue
            f = bm.faces.new((c, a, b))
            f.normal_update()
            if f.normal.dot(up) > 0:                     # (it looks down, out of the skirt)
                f.normal_flip()
            f.material_index = k_in
            f.smooth = True
            if uvl is not None:                          # (nothing of it on a face's cell of the atlas)
                for lp in f.loops:
                    lp[uvl].uv = BLANK_UV
    bm.to_mesh(me)
    bm.free()
    me.update()


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
#   - the relief of the eyes and the mouth: two finer sheets let into the face, moved in depth by the drawing's own
#     curves (head_face; faces.py FORMS: the sockets, the lids over the ball, the lips), and the nose (head_nose),
#   - glasses, thin metal rims a centimetre off the eyes (everybody has a pair; the game shows it or not),
#   - hair as a shell around the skull: columns run from the crown down to a hem whose height is given by azimuth
#     (HAIR_STYLES), lie `vol` off the scalp and hang free below it; the hanging part has an inner side.  The strands
#     themselves, their gloss and their ends at the hem are the game's to draw (TIP_FAR below).
# Lengths are in the source's units (men x 0.93, women x 0.90 in the game), heights `dz` from the brow line.
# Everything is skinned to the bone Head (long hair shares its ends with Neck and Chest: hair_follow), so bags.js,
# which reads the build off the vertices of the other bones, and the clips see the same body as before.
# The materials are named Skin, Hair, Glasses (Band, Bridge, HairFade, HairFade2): web/src/characters.js crowdLook
# recolours them by these names and leaves the glasses out by 'Glasses'.
# the columns of the hair, by the styles' azimuth (either side): closer together where the hem turns quickly - the
# fringe, the temple, the sideburn and round the ear
HAIR_AZ = [0, 6, 12, 18, 24, 30, 36, 42, 46, 50, 54, 58, 62, 66, 70, 74, 78, 82, 86, 90, 95, 100, 105, 110, 116, 123, 131,
           140, 150, 160, 170, 180]
# the nose: the pack's is a wedge stuck on the face, which the easing of the face (head_clean, head_soften) left
# standing up to a centimetre off it.  It is taken away and one sheet is let into the skin instead (head_nose): from
# between the brows down the bridge, over a round tip and under it back to the lip, with a wing either side.
# Of a face, what its line from the side is made of: nose (how far the tip stands off the face, of NOSE_TIP), bridge
# (how much of that is left between the eyes), nose_curve (the bridge between them: 1 straight, less: a scooped one
# with the tip standing out, and only a little; never more: a bridge that is high half way down made the nose a lump), tip_up (how
# steeply the underside rises from the lip to the tip, about NOSE_TILT: more is a turned-up tip that shows its
# underside, less a drooping one), nose_up (the tip higher still, m), tip_round (how blunt the tip is, the radius
# of its round: more is a round one, less a fine one).  From the front: nose_w (the wings' width, a scale), wing (how full they are)
NOSE = dict(nose=0.92, bridge=0.21, nose_curve=1.0, tip_up=1.0, tip_round=1.0, wing=1.0)
# The line of a Korean nose from the side, as measured on a thousand people in their twenties (Bae et al. 2009:
# reference/고증 4.9.3): the forehead and the bridge meet at 135 (men) to 140 degrees (women) in a hollow between the
# eyes, the bridge leaves the face's plane at 30 degrees, the underside meets the lip at 95, the tip stands 17 mm
# off its foot.  The packs' heads have a child's face: the forehead out, everything under the eyes drawn back, the
# chin most of all; a bridge laid on that stood nearly upright against the face (7 to 9 degrees off it), one line
# with the forehead, and the underside had to climb to the tip.  So
#   - the face under the eyes is brought forward (head_profile, FACE_FWD: in depth only, most at the nose's foot and
#     from there down to the chin),
#   - the bridge between the eyes is low (NOSE_RADIX of a person's `bridge`) and ends a little over the eye line
#     (NOSE_ROOT): the hollow,
#   - the underside leaves the lip nearly level (NOSE_TILT) and the tip is a round lying on it (NOSE_BALL), which
#     the bridge leaves as a straight line (nose_shape).
FACE_FWD = {'umc': 0.0075, 'women': 0.0095}       # how far the face comes forward at the nose's foot (a face's `fwd`)
FACE_EYE = 0.010           # the face stays as it is down to this far under the eye line
FACE_SIDE = (0.018, 0.062)                         # all of it within so far of the middle, none of it from there
FACE_DEEP = (0.030, 0.070)                         # and so far behind the upper lip (the throat, the jaw's corners)
# The mouth against the nose's foot.  On the packs' faces the skin under the nose leans back down to the lip (the
# women's by 10 degrees: with an underside that rises 8 to 12 the two met at 112, the men's at 103; measured on
# Koreans in their twenties they meet at 96).  LIP_FWD: the mouth comes forward of the nose's foot, evenly from
# nothing at the foot down to the upper lip's edge (so the skin there leans forward a little, as on a face), all of
# it on both lips, and away again under the lower lip over LIP_UNDER (the hollow over the chin is the deeper for
# it); all of it within LIP_SIDE[0] of the middle, none of it from LIP_SIDE[1] (a face's `lip_fwd`)
LIP_FWD = {'umc': 0.0, 'women': 0.0055}
LIP_UNDER = 0.012
LIP_SIDE = (0.012, 0.046)
# The jaw (reference/고증 4.9.4).  The packs' lower face is a bowl: from the cheeks it narrows evenly to a small round
# chin (at the height of the jaw's corners 0.77 of the width over the cheekbones on the men, 0.73 on the women; a
# grown face keeps about 0.8 and more: a rough figure of the human build, no survey was found), and it runs into the
# neck without an edge: no corner under the ear, the chin 3 mm behind the lips, the skin under it falling away to the
# throat.  head_jaw draws the jaw's lower edge as a line seen from the side: from under the chin back to the corner
# (`rise` over the chin's foot, `back` of the ears' front edge), from there up to the ear (`ramus` degrees off
# level).  What lies on that line and just over it is made wider (`wide`: most at the corner, nothing at the chin or
# over the cheekbones), so that from the front the outline has a corner and the jaw stands off the neck; the chin
# comes forward (`chin`) and is a little broader (`square`), and the skin behind it under the jaw is lifted
# (`under`).  A face's own `gonial` and `chin_out` scale `wide` and `chin`, its `chin_wide` is added to `square`.
JAW = {'umc': dict(rise=0.024, back=0.004, ramus=72, wide=0.085, chin=0.005, square=0.10, under=0.005),
       'women': dict(rise=0.022, back=0.004, ramus=72, wide=0.06, chin=0.0095, square=0.0, under=0.004)}
NOSE_RADIX = 0.4
NOSE_TIP = {'umc': 0.0165, 'women': 0.0212}       # (the packs' wedges stood 0.0145, 0.0188 off the face)
NOSE_ROOT = 0.006          # the bridge dies away this far over the eye line (and only there: it is straight up to it)
NOSE_UNDER = 0.0085        # (a nostril is as deep as it is when the tip stands this far over the nose's foot)
NOSE_LOW = 0.0055          # (and no lower than this: the nostrils need the room)
NOSE_EASE = 8              # how often the profile is eased (its joins, the foot)
NOSE_BALL = 0.0056         # the round of the tip: its radius (a tip_round of 1)
NOSE_TILT_MIN = math.radians(2.5)
NOSE_TILT, NOSE_TILT_UP = 8.0, 7.0      # the underside's rise from the lip, degrees; and so much more for a tip_up of 2
# half the bridge's foot on the face: between the eyes, at the tip (a woman's narrower between the eyes: seen from
# the front the lit ridge was one band of the same width from the brows to the tip)
NOSE_RIDGE = {'umc': (0.0120, 0.0120), 'women': (0.0082, 0.0120)}
NOSE_WING = dict(x=0.0098, rx=0.0072, z=0.0058, up=0.0135, tall=0.52)   # a wing: its middle from the nose's and
#                         over the underside, its half width, how far up the side it dies away, its height of the tip's
NOSE_HOLE = dict(x=0.0055, rx=0.0032, h=0.42, rh=0.30, deep=0.0022)     # a nostril: its middle from the nose's, its
#                         half width, its middle and half depth as heights off the face (of the tip's), how deep it is
NOSE_GRID = (22, 7)        # rows down the nose, columns either side of the ridge
NOSE_APRON = 0.004         # the strip of the face round the nose that is made with it
# what the locks of a person's hair are drawn from (hair_grow: how uneven the volume and the hem are from lock to
# lock): a number of each person's own, kept when the ids became numbers so that nobody's hair changed
HAIR_SEED = {'p01': 3059047122, 'p02': 3446908966, 'p03': 3174642879, 'p04': 4282558304, 'p05': 3363147059,
             'p06': 2181258891, 'p07': 3529059030, 'p08': 3012818855, 'p09': 1345948937, 'p10': 341991820,
             'p11': 1663235077, 'p12': 4110200170, 'p13': 1745548507, 'p14': 3387443816, 'p15': 4178735585,
             'p16': 2052646949, 'p17': 3902518138}
HAIR_RN = 0.115            # nominal radius of the head of hair: arc length on the scalp = HAIR_RN x angle from the crown
# What the game draws a head of hair by (web/src/characters.js: the strands' ends, the gloss): every point of the shell
# carries, in the attribute LEG (a head has no trousers), how far it is from its strand's end (x, of TIP_FAR), how
# glossy the hair is there (y: 1 grown hair, GLOSS_CLIP hair clipped to a few millimetres) and how far up from the
# hem single strands end (z, of WISP_FAR: a style's `wisp`, WISP by default).  The game lets each strand end
# within that of the hem, so a hem is strands' ends and a hairline single hairs, not the shell's edge.
# Only where the hem is the strands' ends, though: where it runs along the strands (the edge of a fringe swept to one
# side, of a curtain, of long hair beside the cheek: the hem's height changes quickly from column to column) it is
# the side of a lock and stays the clean line it is.  WISP_RUN: the hem's slope (its drop over the way round the
# head) at which half the raggedness is left.
TIP_FAR, WISP_FAR = 0.06, 0.04
HEM_STEEP = 2.0           # (head_trim: a hem dropping faster than this between two columns, m per m)
# hair that hangs free; a cut that lies on the head: its fringe, and (by azimuth) its sides and nape, where the short
# hair painted on the skin under the hem must not come out from under it; clipped hair
WISP = dict(hang=0.022, cut=[(0, 0.006), (50, 0.006), (72, 0.004), (180, 0.004)], clip=0.004)
WISP_RUN = 0.6
HAIR_HEM = 0.003
HAIR_ROW = (0.024, 0.045)  # rows of the shell: so far apart on the round of the head (corners in its outline), hanging
GLOSS_CLIP = 0.35


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
# hair drawn back and tied: over the forehead the shell's edge is where the hair grows from, not where strands end, so
# it is a line and not a cut's raggedness (2 mm of it left: single hairs; from the temples back as any cut)
_TIED = [(0, .002), (50, .002), (62, .004)]
HAIR_STYLES = {
    # tip: [(azimuth, dz)] the hem; azimuth in degrees, 0 = front, 90 = the ear, 180 = back (signed: + is the
    #      person's left; unsigned lists are mirrored).  vol: [(azimuth, m)] off the scalp, `top` at the crown,
    #      `edge` at the hem.  part: (azimuth, depth, width in degrees).  fall: how fast free hair may close in on
    #      the neck (m per m).  curl: the hem turns in.  sheet: thickness of hanging hair.  rough, ragged: how uneven
    #      the volume and the hem are from lock to lock.  rows: at least so many down a column (HAIR_ROW asks for
    #      more).  wisp: how far up from the hem single strands end, m or [(azimuth, m)] (WISP).  gloss: 0 .. 1.
    #      The cuts and what they were taken from: reference/고증 4.9; how the game draws the hair: 4.9.2.
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
    # short all round, the fringe combed down over the forehead and across it to the person's right (the film's
    # first-year of 1996): its ends on the right brow, a little higher towards the left, and open over the left
    # eye, where the locks part (the notch at 24)
    'fringe': dict(tip=_both([(-50, .015), (-42, .002), (-30, .000), (-18, .001), (-6, .003), (6, .006), (12, .009), (18, .016),
                              (24, .029), (30, .013), (36, .010), (42, .012), (50, .022)], _MEN_EAR),
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
    # long straight hair worn down from a parting a little to the person's right of the middle: from the parting it
    # falls down either side of the forehead to the brows' tails and on beside the cheeks (the film's still)
    'long': dict(tip=[(-180, -.350), (-135, -.330), (-108, -.215), (-90, -.180), (-74, -.215), (-64, -.215), (-58, -.140),
                      (-52, -.060), (-46, -.014), (-38, .004), (-28, .022), (-18, .042), (-8, .060), (6, .048), (18, .030),
                      (30, .014), (40, .000), (47, -.022), (53, -.075), (59, -.145), (64, -.215), (74, -.215), (90, -.180),
                      (108, -.215), (135, -.330), (180, -.350)],
                 vol=[(-180, .016), (-90, .015), (-45, .013), (6, .011), (45, .013), (90, .015), (180, .016)], top=.017, edge=.010,
                 part=(-8, .007, 7),
                 fall=.10, sheet=.014, rows=12, rough=.08, ragged=.004, ears=False),
    # hair to the shoulders with a straight fringe to just over the brows, no parting (일자 앞머리)
    'bang': dict(tip=[(-180, -.205), (-135, -.20), (-90, -.175), (-60, -.185), (-53, -.10), (-47, -.020), (-41, .007), (-20, .005),
                      (0, .006), (20, .005), (41, .007), (47, -.020), (53, -.10), (60, -.185), (90, -.175), (135, -.20), (180, -.205)],
                 vol=[(-180, .017), (-90, .016), (-40, .016), (0, .017), (40, .016), (90, .016), (180, .017)], top=.021, edge=.011,
                 fall=.10, sheet=.015, curl=.010, rows=10, rough=.08, ragged=.002, ears=False),
    'shoulder': dict(tip=[(-180, -.205), (-135, -.20), (-90, -.175), (-60, -.185), (-52, -.10), (-42, -.035), (-22, .006),
                          (0, .024), (15, .038), (26, .048), (33, .030), (40, -.012), (49, -.10), (58, -.185), (90, -.175), (135, -.20),
                          (180, -.205)],
                     vol=[(-180, .017), (-90, .016), (-30, .014), (28, .012), (60, .015), (180, .017)], top=.019, edge=.011,
                     part=(28, .007, 7), fall=.10, sheet=.015, curl=.010, rows=10, rough=.08, ragged=.0015, ears=False),
    # a bob, one side tucked behind the ear: there the hair comes down the temple to the ear's top (the women's: -.023),
    # lies over it and goes down behind it, a wisp before the ear (as `pixie`: with the hem up at the brows' height
    # all the way back, three centimetres of bare skin stood over the ear)
    'tuck': dict(tip=[(-180, -.146), (-90, -.146), (-60, -.146), (-52, -.10), (-42, -.035), (-22, .006), (0, .024),
                      (15, .038), (26, .048), (36, .034), (48, .016), (57, .002), (62, -.014), (68, -.032), (74, -.036),
                      (79, -.029), (84, -.027), (97, -.027), (102, -.052), (106, -.10), (116, -.146), (180, -.146)],
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
    # long hair, the top half tied back: the sides drawn back over the ears' tops (not above them: see `tuck`)
    # all of it drawn back into one tail (포니테일): the sides over the ears' tops as `half`, the back up to the nape's
    # hairline, a tail from the back of the head to the shoulders
    'pony': dict(tip=_both([(-47, .034), (-36, .046), (-20, .055), (0, .059), (20, .055), (36, .046), (47, .034)],
                           [(57, .016), (62, -.004), (67, -.028), (73, -.036), (78, -.029), (82, -.027), (97, -.027),
                            (101, -.046), (105, -.066), (112, -.080), (135, -.102), (180, -.110)]),
                 vol=[(-180, .010), (-100, .009), (-60, .008), (-20, .012), (20, .010), (60, .008), (100, .009), (180, .010)],
                 top=.015, edge=[(0, .004), (60, .004), (100, .006), (180, .005)], part=(30, .004, 7), rows=8, rough=.08,
                 ragged=.003, wisp=_TIED, tail=dict(dz=.012, length=.25, r=.034)),
    'half': dict(tip=_both([(-47, .030), (-35, .042), (-18, .052), (0, .057), (10, .059), (24, .054), (37, .043), (47, .030)],
                           [(57, .016), (62, -.004), (67, -.028), (73, -.036), (78, -.029), (82, -.027), (97, -.027),
                            (101, -.048), (104, -.09), (111, -.22), (135, -.31), (180, -.33)]),
                 vol=[(-180, .016), (-100, .015), (-60, .008), (-20, .013), (20, .011), (60, .008), (100, .015), (180, .016)],
                 top=.016, edge=[(0, .004), (60, .004), (100, .010), (180, .010)], part=(30, .004, 7), fall=.10, sheet=.014,
                 rows=12, rough=.08, ragged=.004, wisp=_TIED + [(104, .004), (111, WISP['hang']), (180, WISP['hang'])],
                 tail=dict(dz=.0, length=.17, r=.022)),
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
    """The head as one skull with its ears: the doll's eyes and brows, its nose (a wedge stuck on the face: head_nose
    makes another), the hat and the moustache go (where they were is returned), the cap painted on the scalp becomes
    the material 'Hair'."""
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
                L['nose'] = box                             # (goes: head_nose makes another)
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
            # (a person's own: fuller at the cheeks, 3 cm under the eyes, and the jaw drawn in from the mouth down to
            # the chin: an egg's line, where `jaw` alone makes the face widest at the mouth)
            p.x *= 1 + (face.get('cheek', 1.0) - 1) * math.exp(-((p.z - (cheek - 0.03)) / 0.028) ** 2)
            p.x *= 1 - face.get('taper', 0.0) * _smooth(nb - 0.015, chin, p.z) * _smooth(chin - 0.04, chin - 0.005, p.z)
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
        if abs(sum((mw @ v.co).x for v in vs) / len(vs)) < 0.04:            # the skull
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


def head_profile(ob, L, face, rig):
    """The face's own line from the side (see FACE_FWD): the face under the eyes brought forward, the more the lower,
    and all of it from the nose's foot to the chin; only in depth, so seen from the front nothing moves (the eyes,
    the drawn face's place on the atlas).  It dies away to the sides (the cheekbones, the jaw's corners), into the
    head (the throat under the chin) and under the chin."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    fwd = face.get('fwd', FACE_FWD[rig])
    mw = ob.matrix_world
    inv = mw.inverted()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    cos = [mw @ v.co for v in bm.verts]
    tree = BVHTree.FromPolygons(cos, [[v.index for v in f.verts] for f in bm.faces])
    ez, nb = eye_line(L, face), L['nose'][0].z
    # the chin's foot: down the middle of the face, where its line turns back under the chin
    zc = _chin_foot(tree, nb)
    y0 = tree.ray_cast(Vector((0, -0.6, nb - 0.012)), Vector((0, 1, 0)))[0].y          # (the upper lip)
    lip = face.get('lip_fwd', LIP_FWD[rig])
    _, _, ue, le, _ = faces_mod.lip_edges(rig, face, [0.0])
    zu, zl = ez + float(ue[0]), ez + float(le[0])           # (the lips' upper and lower edge, in the middle)
    for v, p in zip(bm.verts, cos):
        w = _smooth(ez - FACE_EYE, nb, p.z) if p.z > nb else _smooth(zc - 0.035, zc - 0.004, p.z)
        w *= 1 - _smooth(FACE_SIDE[0], FACE_SIDE[1], abs(p.x))
        deep = 1 - _smooth(y0 + FACE_DEEP[0], y0 + FACE_DEEP[1], p.y)
        g = 0.0
        if lip and zl - LIP_UNDER < p.z < nb:
            g = (nb - p.z) / (nb - zu) if p.z > zu else 1 - _smooth(zl, zl - LIP_UNDER, p.z)
            g *= 1 - _smooth(LIP_SIDE[0], LIP_SIDE[1], abs(p.x))
        d = (fwd * w + lip * g) * deep
        if d > 0:
            v.co = inv @ Vector((p.x, p.y - d, p.z))
    bm.to_mesh(ob.data)
    bm.free()


def _chin_foot(tree, nb):
    """Down the middle of the face, the height where its line turns back under the chin."""
    z, last = nb - 0.02, None
    while z > nb - 0.12:
        hit = tree.ray_cast(Vector((0, -0.6, z)), Vector((0, 1, 0)))[0]
        if hit is None or (last is not None and hit.y > last + 0.004):
            return z
        last, z = hit.y, z - 0.002
    return nb - 0.07


def head_jaw(ob, L, face, rig):
    """The jaw's edge, its corners under the ears and the chin (see JAW); every point of the head by its place, the
    ears with the skin they stand on."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    J = JAW[rig]
    mw = ob.matrix_world
    inv = mw.inverted()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    cos = [mw @ v.co for v in bm.verts]
    tree = BVHTree.FromPolygons(cos, [[v.index for v in f.verts] for f in bm.faces])
    nb = L['nose'][0].z
    zc = _chin_foot(tree, nb)
    y0 = tree.ray_cast(Vector((0, -0.6, nb - 0.012)), Vector((0, 1, 0)))[0].y          # (the upper lip)
    yc = y0 + 0.014                                             # under the chin: where the edge sets out
    yg, zg = sum(b[0].y for b in L['ears']) / len(L['ears']) + J['back'], zc + J['rise']
    up = math.tan(math.radians(J['ramus']))
    wide, chin = J['wide'] * face.get('gonial', 1.0), J['chin'] * face.get('chin_out', 1.0)

    def edge(y):
        return zc + J['rise'] * max(0.0, (y - yc) / (yg - yc)) ** 1.15 if y <= yg else zg + (y - yg) * up
    for v, p in zip(bm.verts, cos):
        x, y, z = p
        t = z - edge(y)
        ax = abs(x)
        # the corner and the edge running to it: wider on the line and just over it, nothing 3 cm over it (the
        # cheeks); what is under the line (the neck) and behind the corner stays
        x *= 1 + wide * _smooth(yc + 0.008, yg - 0.018, y) * _smooth(-0.012, -0.002, t) * (1 - _smooth(0.004, 0.028, t))
        # the chin: its front out under the lip's hollow, its foot a little broader
        front = 1 - _smooth(y0 + 0.020, y0 + 0.045, y)
        knob = _smooth(zc - 0.012, zc + 0.004, z) * (1 - _smooth(zc + 0.010, zc + 0.022, z)) * front
        y -= chin * knob * (1 - _smooth(0.016, 0.040, ax))
        x *= 1 + (J['square'] + face.get('chin_wide', 0.0)) * knob * (1 - _smooth(0.030, 0.050, ax))
        # under the chin: the skin between it and the throat lifted toward the jaw's edge
        z += (J['under'] * _smooth(yc + 0.006, yc + 0.020, y) * (1 - _smooth(yc + 0.032, yc + 0.050, y)) * (1 - _smooth(0.020, 0.045, ax))
              * (1 - _smooth(-0.004, 0.004, t)) * _smooth(zc - 0.035, zc - 0.018, z))
        v.co = inv @ Vector((x, y, z))
    bm.to_mesh(ob.data)
    bm.free()


def _inside(poly, x, z):
    """Whether (x, z) lies in the polygon [(x, z), ...]."""
    n, hit = len(poly), False
    for i in range(n):
        (x0, z0), (x1, z1) = poly[i], poly[(i + 1) % n]
        if (z0 > z) != (z1 > z) and x < x0 + (z - z0) / (z1 - z0) * (x1 - x0):
            hit = not hit
    return hit


def _crosses(a, b, c, d):
    """Whether the segments a-b and c-d (2D) cross."""
    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return side(a, b, c) * side(a, b, d) < 0 and side(c, d, a) * side(c, d, b) < 0


def nose_shape(fy, ez, nb, face, rig):
    """The nose as heights off the face: rows [[(x, z, height), ...], ...] from over the eye line (ez) down to the
    underside (nb), every row from the person's right to their left; the first two and the last two rows and both
    ends of every row lie on the face (height 0).  fy(x, z) is the face seen from the front."""
    tip, bridge, curve, tip_up, blunt, full = (face.get(k, NOSE[k]) for k in (
        'nose', 'bridge', 'nose_curve', 'tip_up', 'tip_round', 'wing'))
    wide = face.get('nose_w', 1.0)
    T = NOSE_TIP[rig] * tip
    z1 = ez + NOSE_ROOT
    W, H = NOSE_WING, NOSE_HOLE
    # The profile, as how far forward the nose's line is at each height (u: the face's own is -fy):
    #   - the underside leaves the lip at the nose's foot rising only NOSE_TILT (more for a turned-up tip: tip_up),
    #   - the tip is a round of the radius NOSE_BALL (tip_round) lying on that line, its foremost point T before the
    #     chord of the face (the straight line from the face at the tip's height to the face at the eye line),
    #   - the bridge is the straight line from that round up to the hollow between the eyes, where bridge x
    #     NOSE_RADIX of T is left of it (nose_curve under 1: sagging between them), and dies away over the eye line.
    # Sampled every half millimetre and eased a little (the foot, the joins).
    R = NOSE_BALL * (0.55 + 0.45 * blunt)
    tilt = max(NOSE_TILT_MIN, math.radians(NOSE_TILT + NOSE_TILT_UP * (tip_up - 1)))
    u = lambda z: -fy(0, z)                                    # noqa: E731
    us = u(nb)
    zt = nb + NOSE_LOW
    for _ in range(4):                                         # (the round's middle: its height hangs on the face there)
        uc = u(zt) + T - R
        # (nose_up moves the tip, and the underside's line with it; never under the least rise: the foot is the foot)
        zt = nb + max(((uc - us) * math.sin(tilt) + R) / math.cos(tilt) + face.get('nose_up', 0.0),
                      ((uc - us) * math.sin(NOSE_TILT_MIN) + R) / math.cos(NOSE_TILT_MIN))
    uc = u(zt) + T - R
    tilt = math.acos(min(1.0, R / math.hypot(zt - nb, uc - us))) - math.atan2(uc - us, zt - nb)
    foot = (zt - R * math.cos(tilt), uc + R * math.sin(tilt))   # where the underside's line meets the round (z, u)
    root = (ez, u(ez) + bridge * NOSE_RADIX * T)                # the bridge between the eyes
    dz, du = zt - root[0], uc - root[1]
    far = math.hypot(dz, du)
    turn = math.asin(min(1.0, R / far))
    a0 = math.atan2(du, dz) - turn                              # (the tangent that passes before the round)
    run = math.sqrt(max(0.0, far * far - R * R))
    top = (root[0] + run * math.cos(a0), root[1] + run * math.sin(a0))      # where the bridge leaves the round
    N = int(round((z1 - nb) / 0.0005))
    zs = [z1 - (z1 - nb) * i / N for i in range(N + 1)]
    M = []
    for z in zs:
        if z >= top[0]:
            h = (z - top[0]) / (root[0] - top[0])
            line = top[1] + (root[1] - top[1]) * h - 0.5 * (1 - curve) * T * math.sin(math.pi * min(h, 1.0))
            m = (line - u(z)) * (1 - _smooth(ez, z1, z))
        elif z >= foot[0]:
            m = uc + math.sqrt(max(0.0, R * R - (z - zt) ** 2)) - u(z)
        else:
            m = us + (foot[1] - us) * (z - nb) / max(1e-6, foot[0] - nb) - u(z)
        M.append(max(0.0, m))
    M[0] = M[N] = 0.0
    for _ in range(NOSE_EASE):
        M = [M[0]] + [(M[i - 1] + 2 * M[i] + M[i + 1]) / 4 for i in range(1, N)] + [M[N]]
    k = T / max(M)
    M = [m * k for m in M]
    # rows: closer together where the profile turns (the tip and the underside)
    arc = [0.0]
    for i in range(N):
        arc.append(arc[-1] + math.hypot(zs[i + 1] - zs[i], M[i + 1] - M[i]) * (2.0 if zs[i] < zt + 0.008 else 1.0))
    NR, NC = NOSE_GRID
    za, xa, rx = nb + W['z'], W['x'] * wide, W['rx'] * wide ** 0.5
    rows, i = [], 0
    for r in range(NR + 1):
        a = arc[-1] * r / NR
        while i < N - 1 and arc[i + 1] < a:
            i += 1
        t = (a - arc[i]) / max(1e-9, arc[i + 1] - arc[i])
        z, m = zs[i] + (zs[i + 1] - zs[i]) * t, M[i] + (M[i + 1] - M[i]) * t
        if r in (0, NR):
            z, m = (z1, 0.0) if r == 0 else (nb, 0.0)
        g = _smooth(ez, zt, z)                                # 0 between the eyes .. 1 at the tip and under it
        w = NOSE_RIDGE[rig][0] + (NOSE_RIDGE[rig][1] * (wide * blunt) ** 0.5 - NOSE_RIDGE[rig][0]) * g
        dz = (z - za) / (W['up'] if z > za else za - nb)
        X = max(w, xa + rx * math.sqrt(max(0.0, 1 - dz * dz)))
        row = []
        for c in range(-NC, NC + 1):
            x = X * c / NC
            ridge = m * max(0.0, 1 - (abs(x) / w) ** 2) ** (1.9 - 0.7 * g)      # (fuller at the tip)
            d2 = ((abs(x) - xa) / rx) ** 2 + dz * dz
            wing = W['tall'] * full * T * max(0.0, 1 - d2) ** 1.1
            h = 0.0 if abs(c) == NC or r in (0, NR) else (ridge ** 4 + wing ** 4) ** 0.25
            # a nostril: the underside drawn up either side of the middle
            up = 0.0
            if z < zt and h > 0:
                up = H['deep'] * min(1.0, (zt - nb) / NOSE_UNDER) * max(0.0, 1 - ((abs(x) - H['x'] * wide) / H['rx']) ** 2 - ((h / T - H['h']) / H['rh']) ** 2)
            row.append((x, z + up, h))
        rows.append([(row[0][0] - NOSE_APRON, z, 0.0)] + row + [(row[-1][0] + NOSE_APRON, z, 0.0)])
    # a strip of the face round the nose belongs to the sheet too: the shade under the nose ends on it
    return [[(x, z1 + NOSE_APRON, 0.0) for x, _, _ in rows[0]]] + rows + [[(x, nb - NOSE_APRON, 0.0) for x, _, _ in rows[-1]]]


def sheet_in(ob, shape, name, deep=0.01):
    """A sheet of heights off the face let into the skin: shape(fy) gives its rows [[(x, z, height), ...], ...] from
    the top down, every row from the person's right to their left, the outermost rows and columns on the face
    (fy(x, z): the face seen from the front).  The faces of the skull under it go, and the ring between the hole and
    the sheet's rim is filled with triangles: one skin, shaded as one.  Returns (the faces made, the mesh's matrix,
    the bmesh: the caller checks them and writes the mesh)."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    from mathutils.geometry import delaunay_2d_cdt
    me = ob.data
    mw = ob.matrix_world
    inv = mw.inverted()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    cos = [mw @ v.co for v in bm.verts]
    tree = BVHTree.FromPolygons(cos, [[v.index for v in f.verts] for f in bm.faces])

    def fy(x, z):
        return tree.ray_cast(Vector((x, -0.6, z)), Vector((0, 1, 0)))[0].y
    rows = shape(fy)
    NR, NC = len(rows) - 1, (len(rows[0]) - 1) // 2
    grid = [[Vector((x, fy(x, z) - h, z)) for x, z, h in row] for row in rows]
    # the rim, round the sheet, and the faces of the skull that reach under it (a little more than it)
    ring = [(r, 0) for r in range(NR)] + [(NR, c) for c in range(2 * NC)] + [(r, 2 * NC) for r in range(NR, 0, -1)] \
        + [(0, c) for c in range(2 * NC, 0, -1)]
    rim = [(grid[r][c].x, grid[r][c].z) for r, c in ring]
    cx, cz = 0.0, sum(z for _, z in rim) / len(rim)
    out = [(x + 0.0015 * (x - cx) / math.hypot(x - cx, z - cz), z + 0.0015 * (z - cz) / math.hypot(x - cx, z - cz))
           for x, z in rim]
    x0, x1 = min(x for x, _ in out), max(x for x, _ in out)
    z0, z1 = min(z for _, z in out), max(z for _, z in out)
    front = min(p.y for row in grid for p in row) - 0.01, max(p.y for row in grid for p in row) + deep
    gone = []
    for f in bm.faces:
        ps = [cos[v.index] for v in f.verts]
        if (mw.to_3x3() @ f.normal).y > -0.2 or not all(front[0] < p.y < front[1] for p in ps):
            continue
        q = [(p.x, p.z) for p in ps]
        if max(x for x, _ in q) < x0 or min(x for x, _ in q) > x1 or max(z for _, z in q) < z0 or min(z for _, z in q) > z1:
            continue
        if (any(_inside(out, x, z) for x, z in q) or any(_inside(q, x, z) for x, z in out)
                or any(_crosses(q[i], q[(i + 1) % len(q)], out[j], out[(j + 1) % len(out)])
                       for i in range(len(q)) for j in range(len(out)))):
            gone.append(f)
    if not gone:
        raise SystemExit(f'{ob.name}: no face of the skull under the {name}')
    mat = gone[0].material_index
    dead = set(gone)
    edge = [e for f in gone for e in f.edges if any(g not in dead for g in e.link_faces)]
    edge = sorted(set(edge), key=lambda e: e.index)
    nxt = {}
    for e in edge:
        for v in e.verts:
            nxt.setdefault(v, []).append(e)
    if any(len(es) != 2 for es in nxt.values()):
        raise SystemExit(f'{ob.name}: the hole for the {name} is not one loop')
    hole, e = [edge[0].verts[0]], edge[0]
    while True:
        v = e.other_vert(hole[-1])
        if v is hole[0]:
            break
        hole.append(v)
        e = next(x for x in nxt[v] if x is not e)
    if len(hole) != len(edge):
        raise SystemExit(f'{ob.name}: the hole for the {name} is not one loop')
    bmesh.ops.delete(bm, geom=gone, context='FACES')
    dl = bm.verts.layers.deform.verify()
    hp = [mw @ v.co for v in hole]

    def new_vert(p):
        v = bm.verts.new(inv @ p)
        src = min(range(len(hole)), key=lambda i: (hp[i] - p).length_squared)
        for g, w in hole[src][dl].items():
            v[dl][g] = w
        return v
    gv = [[new_vert(p) for p in row] for row in grid]
    made = []

    def new_face(vs):
        f = bm.faces.new(vs)
        f.normal_update()
        if (mw.to_3x3() @ f.normal).y > 0:
            f.normal_flip()
        f.material_index = mat
        f.smooth = True
        made.append(f)
    for r in range(NR):
        for c in range(2 * NC):
            new_face([gv[r][c], gv[r][c + 1], gv[r + 1][c + 1], gv[r + 1][c]])
    # the ring between the hole and the rim, seen from the front
    rv = [gv[r][c] for r, c in ring]
    pts = [(p.x, p.z) for p in hp] + rim
    nh, nr = len(hole), len(rim)
    loops = [(i, (i + 1) % nh) for i in range(nh)] + [(nh + i, nh + (i + 1) % nr) for i in range(nr)]
    res = delaunay_2d_cdt([Vector(p) for p in pts], loops, [], 0, 1e-7)
    if len(res[0]) != len(pts):
        raise SystemExit(f'{ob.name}: the hole for the {name} crosses its rim')
    both = hole + rv
    for tri in res[2]:
        x, z = (sum(pts[i][k] for i in tri) / 3 for k in (0, 1))
        if _inside(pts[:nh], x, z) and not _inside(rim, x, z):
            new_face([both[i] for i in tri])
    bmesh.ops.recalc_face_normals(bm, faces=made)
    return made, fy, bm


def head_nose(ob, L, face, rig):
    """The nose (see NOSE): a sheet of heights off the face, let into the skin (sheet_in), so the nose is shaded with
    the face and nothing shows where it begins."""
    mw = ob.matrix_world
    made, fy, bm = sheet_in(ob, lambda fy: nose_shape(fy, eye_line(L, face), L['nose'][0].z, face, rig), 'nose')
    # every face of it looks away from the inside of the head (a point behind the bridge; the underside is nearly
    # level and a nostril's front wall looks back and down, so `forward` is no test)
    ez, nb = eye_line(L, face), L['nose'][0].z
    core = Vector((0, fy(0, ez) + 0.03, (ez + nb) / 2))
    for f in made:
        if (mw.to_3x3() @ f.normal).dot(mw @ f.calc_center_median() - core) < 0:
            raise SystemExit(f'{ob.name}: a face of the nose looks in')
    bm.to_mesh(ob.data)
    bm.free()


def head_face(ob, L, face, rig):
    """The eyes' and the mouth's relief (faces.py FORMS): two sheets let into the face before the nose is, their rows
    along the lids and the lips, every point moved in depth only (the drawn face is laid on from the front: it stays
    where it is).  Returns how far the eyes' middles now lie behind the smooth face (the glasses stay where they were)."""
    ez = eye_line(L, face)
    rot = ob.matrix_world.to_3x3()

    def shape(fy, i):
        def floor(x):
            # down from the mouth: where the face leans back more than 45 degrees, or turns from the front by 58
            z, step = ez + FACE[rig]['mouth_dz'], 0.001
            while z > ez + FACE[rig]['mouth_dz'] - 0.04:
                try:
                    dz = (fy(x, z - step) - fy(x, z)) / step
                    dx = (fy(x + step, z) - fy(x - step, z)) / (2 * step)
                except AttributeError:                       # (past the face)
                    break
                if dz > 1.0 or math.hypot(dx, dz) > 1.6:
                    break
                z -= step
            return z + 0.002 - ez
        return [[(x, ez + z, h) for x, z, h in row] for row in faces_mod.sheets(rig, face, floor)[i]]
    for i, name in enumerate(('eyes', 'mouth')):
        made, fy, bm = sheet_in(ob, lambda fy: shape(fy, i), name, deep=0.03)
        for f in made:
            if (rot @ f.normal).y > -0.02:
                raise SystemExit(f'{ob.name}: a face of the {name} looks away')
        bm.to_mesh(ob.data)
        bm.free()
    _, ex, _, _ = faces_mod.rim_frame(rig, face)
    return float(faces_mod.forms(rig, face, [ex], [glasses_line(L) - ez])[0])


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
    rnd = random.Random(HAIR_SEED[pid])
    cols = [math.radians(surf.from_style(a)) for a in HAIR_AZ]
    cols += [2 * math.pi - a for a in reversed(cols[1:-1])]             # (round the head, 0 = the front, the left first)
    NA = len(cols)
    C, Rn = surf.C, HAIR_RN
    s_eq = Rn * math.pi / 2
    # rows: close together over the round of the head (N1 of them down to the level of the centre), further apart
    # below; a column that ends above that level has them all evenly
    longest = max(Rn * (math.pi / 2 - math.asin(min(1.0, v / Rn))) if v >= 0 else s_eq - v for _, v in st['tip'])
    N1 = math.ceil(min(longest, s_eq) / HAIR_ROW[0])
    NR = max(st.get('rows', 7), N1 + math.ceil(max(0.0, longest - s_eq) / HAIR_ROW[1]) + 1)
    N2 = NR - 1 - N1
    NR += 1         # (and one row HAIR_HEM over the hem: the hem's points, which the hem's own face turns down, light
    #                 only that much of the shell wrongly, and the game takes the gloss off the strands' very ends)
    fall, sheet, curl = st.get('fall', 1.5), st.get('sheet', 0.012), st.get('curl', 0.0)
    noise = [rnd.uniform(-1, 1) for _ in range(NA)]
    noise = [(noise[j - 1] + 2 * noise[j] + noise[(j + 1) % NA]) / 4 for j in range(NA)]
    lock = [rnd.uniform(-1, 1) for _ in range(NA)]
    lock = [(lock[j - 1] + 2 * lock[j] + lock[(j + 1) % NA]) / 3 for j in range(NA)]       # (locks a few columns wide)
    pts, faces = [C.copy()], []
    clip = st.get('vol') and max(v for _, v in st['vol']) < 0.005       # (clipped: the close shell under a longer cut)
    gloss = st.get('gloss', GLOSS_CLIP if clip else 1.0)
    tips = [(1.0, gloss, 1 / 255)]      # by point, for the game: (to the strand's end, gloss, how ragged the ends), 0 .. 1
    streak, aps = [], []        # faces of the bleached locks (style 'bridge': [(azimuth, half width)]); azimuth by column
    grid = {}                  # (column, row) -> vertex
    inner = {}                 # (column, row) -> vertex of the inner side
    ends = []                  # per column: arc length of the hem
    top_r = []

    def hem_arc(a):
        dz = _by_azimuth(st['tip'], surf.style_azimuth(math.degrees(a if a <= math.pi else a - 2 * math.pi)))
        return Rn * (math.pi / 2 - math.asin(min(1.0, dz / Rn))) if dz >= 0 else s_eq - dz
    # how much of the raggedness a column keeps: by the hem's slope either side of it (the style's own line, without
    # the locks' unevenness)
    hems = [hem_arc(a) for a in cols]
    keep = []
    for j in range(NA):
        run = 0.0
        for k in (j - 1, (j + 1) % NA):
            way = Rn * max(0.4, math.sin(min(hems[j], hems[k], s_eq) / Rn)) * abs((cols[j] - cols[k] + math.pi) % (2 * math.pi) - math.pi)
            run = max(run, abs(hems[j] - hems[k]) / max(way, 1e-4))
        keep.append(1 / (1 + (run / WISP_RUN) ** 2))
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
        wisp = st.get('wisp', WISP['clip' if clip else 'hang' if hang else 'cut'])
        wisp = (wisp if isinstance(wisp, float) else _by_azimuth(wisp, ap)) * keep[j]
        tip = lambda s: (min(1.0, (s_end - s) / TIP_FAR), gloss, max(1 / 255, min(1.0, wisp / WISP_FAR)))    # noqa: E731
        for i in range(1, NR):
            if i == NR - 1:
                s = s_end
            elif i == NR - 2:
                s = s_end - min(HAIR_HEM, 0.3 * s_end / (N1 + N2))
            else:
                s = s_end * i / (N1 + N2) if s_end <= s_eq else s_eq * i / N1 if i <= N1 else s_eq + (s_end - s_eq) * (i - N1) / N2
            u = s / s_end
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
            tips.append(tip(s))
            if i == 1:
                top_r.append((rho, z))
            if hang and z < C.z - 0.03 or i == NR - 1:
                ri = min(rho - 0.002, max(rs + (0.0008 if z > C.z - 0.12 else 0.003), rho - sheet))
                inner[j, i] = len(pts)
                pts.append(Vector((C.x + ri * math.sin(a), C.y - ri * math.cos(a), z + (0.0 if i < NR - 1 else 0.0005))))
                tips.append(tip(s))
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
        tips += [(1.0, gloss, 1 / 255)] * len(tp)
    return pts, faces, follow, (cols, ends), band, streak, tips


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
    # (the heights were measured on heads with a chin of `chin0`; a person's own is longer or shorter under the mouth)
    z = nz - (nz - z) / (face.get('chin', 1.0) * f['chin'] / f['chin0'])
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


def face_glasses(surf, L, rig, face, sunk=0.0):
    """Round-cornered rims a centimetre off the eyes, a bridge, and temples back to the ears: (points, faces).  The
    frame and the rims' thickness are faces.py's, which draws the same glasses for the game to show from further off.
    sunk: how far the eyes lie in their sockets (head_face; negative): the rims stand off the smooth face as before."""
    pts, faces = [], []
    ez = glasses_line(L)
    ear = max(L['ears'], key=lambda box: box[1].x)
    _, ex, W, H = faces_mod.rim_frame(rig, face)
    T, N = faces_mod.RIM_T, 16
    for box in L['eyes']:
        sx = 1 if box[0].x + box[1].x > 0 else -1
        y = surf.front(sx * ex, ez)[0].y - 0.011 - sunk
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


def head_trim(ob, surf, st, ends, shells=()):
    """Scalp that the hair covers goes (nothing sees it); the old cap's paint is skin wherever the new hair does not
    cover it, from the forehead round to behind the ears, or all round (it ends in whole faces: a stepped hairline;
    a man's nape keeps it as short hair).  shells: [(points, faces, tips)] of the hair grown (hair_grow)."""
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
        """(azimuth, dz, arc length down from the crown, the least hem near, the hem here, the shorter of the two
        columns either side, how steeply the hem drops between them)."""
        a = math.atan2(p.x - C.x, -(p.y - C.y))
        dz = p.z - C.z
        s = Rn * (math.pi / 2 - math.atan2(dz, math.hypot(p.x - C.x, p.y - C.y))) if dz >= 0 else s_eq - dz
        w = a % (2 * math.pi)
        j = bisect.bisect_right(cols, w) - 1
        span = (cols[j + 1] if j + 1 < NA else 2 * math.pi) - cols[j]
        t = (w - cols[j]) / span
        near = [ends[(j + d) % NA] for d in (-1, 0, 1, 2)]
        slope = abs(near[2] - near[1]) / (Rn * max(0.4, math.sin(min(near[1], near[2], s_eq) / Rn)) * span)
        return math.degrees(a), dz, s, min(near), near[1] + (near[2] - near[1]) * t, min(near[1:3]), slope

    back = 118 if st.get('ears', True) is True else 100     # (hair over the ears hides the sides of the head too)
    bm = bmesh.new()
    bm.from_mesh(me)
    info = {f: [where(mw @ v.co) for v in f.verts] for f in bm.faces}
    kill = [f for f in bm.faces
            if all(s < lo - 0.03 and (dz > 0.0 or (abs(surf.style_azimuth(a)) > back and dz > -0.07))
                   for a, dz, s, lo, _, _, _ in info[f])]
    gone = set(kill)
    # Where the hem drops steeply between two columns (the temples of hair worn down), the line drawn between
    # them is not the shell's edge, and from near the game leaves out the strands' ends (the last `wisp` before a
    # strand's end, tips) and the hem's own face: there a face is drawn as hair only if the hair hides it, or it
    # pokes through or lies in the shell.  Painted where it could be seen, it showed as a dark block with straight
    # sides, or a speck beside the eye.
    from mathutils.bvhtree import BVHTree
    sp, sf, solid = [], [], []
    for q, fs, tp in shells:
        base = len(sp)
        sp += [tuple(p) for p in q]
        for f in fs:
            sf.append(tuple(base + i for i in f))
            solid.append(all(tp[i][0] * TIP_FAR > tp[i][2] * WISP_FAR + 0.001 for i in f))
    shell = BVHTree.FromPolygons(sp, sf)
    close = BVHTree.FromPolygons(sp, [f for f, k in zip(sf, solid) if k])
    head = BVHTree.FromPolygons([tuple(mw @ v.co) for v in bm.verts],
                                [tuple(v.index for v in f.verts) for f in bm.faces if f not in gone])
    looks = {}
    for y in range(-90, 91, 5):
        for t in range(-30, 31, 10):
            y_, t_ = math.radians(y), math.radians(t)
            looks[y, t] = Vector((math.sin(y_) * math.cos(t_), -math.cos(y_) * math.cos(t_), math.sin(t_)))

    def through(p, d, far):
        """How the ray from p along d gets past the hair within far: None if the solid hair stops it, 'open' if it
        meets no hair, 'ends' if the first hair it meets, close over the skin, is strands' ends, 'crack' if it
        meets them only further on (out between two pieces of the shell first)."""
        way, gone_by = 'open', 0.0
        while far > 0:
            hit, _, i, t = shell.ray_cast(p, d, far)
            if hit is None:
                return way
            if solid[i]:
                return None
            if way == 'open':
                way = 'ends' if gone_by + t < 0.025 else 'crack'
            p, far, gone_by = hit + d * 0.0002, far - t - 0.0002, gone_by + t + 0.0002
        return way

    def hidden(f):
        """Hidden by the hair, poking through it or lying in it.  Under both columns' hems it is seen only through
        the strands' ends right over it; nearer the hem also beside the shell."""
        deep = all(i[2] < i[5] - 0.006 for i in info[f])
        n = (mw.to_3x3() @ f.normal).normalized()
        vs = [mw @ v.co for v in f.verts]
        for p in vs + [(a + b) / 2 for a, b in zip(vs, vs[1:] + vs[:1])] + [sum(vs, Vector()) / len(vs)]:
            if through(p, ((C if p.z > C.z else Vector((C.x, C.y, p.z))) - p).normalized(), 0.02) is None or \
                    close.find_nearest(p, 0.002)[0] is not None:
                return True
        # seen: from some way of looking, and past the hair every way 5 degrees beside it and 10 above and below,
        # with no hair behind it (then it would stand out of the hair)
        for p in vs + [sum(vs, Vector()) / len(vs)]:
            p = p + n * 0.0005
            seen = {}

            def sees(k):
                if k not in seen:
                    d = looks.get(k)
                    w = None if d is None else through(p, d, 0.5)
                    seen[k] = None if w is None or head.ray_cast(p + d * 0.0005, d, 0.5)[0] is not None else w
                return seen[k]
            for (y, t), d in looks.items():
                if d.dot(n) > 0.02 and sees((y, t)) in (('ends',) if deep else ('open', 'ends')) and \
                        all(sees((y + dy, t + dt)) in ('open', 'ends') for dy in (-5, 0, 5) for dt in (0, -10, 10)) \
                        and through(p, -d, 0.03) is not None:
                    return False
        return True

    for f in bm.faces:
        if f in gone:
            continue
        steep = any(i[6] > HEM_STEEP for i in info[f])
        if f.material_index == hair:
            a = where(mw @ f.calc_center_median())[0]             # (a face any corner of which shows)
            if (abs(surf.style_azimuth(a)) < 104 or not st.get('nape', True)) and (
                    any(s > here - 0.002 for _, _, s, _, here, _, _ in info[f]) or steep and not hidden(f)):
                f.material_index = skin
        elif all(s < here - 0.006 and dz > -0.03 for _, dz, s, _, here, _, _ in info[f]) and (not steep or hidden(f)):
            f.material_index = hair                               # (skin under the hair: if it pokes through, as hair)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(me)
    bm.free()


def head_part(name, arm, pieces, follow=None, tips=None):
    """A mesh of [(material, points, faces)] skinned to the head (and, by `follow`: (neck, chest) for each point of the
    pieces in turn, to the neck and the chest).  tips: what the game draws hair by (hair_grow), for each point in turn."""
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
    if tips:
        att = me.attributes.new(LEG, 'FLOAT_VECTOR', 'POINT')
        for i, t in enumerate(tips):
            att.data[i].vector = t
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
    head_profile(head, L, face, rig)
    head_jaw(head, L, face, rig)
    sunk = head_face(head, L, face, rig)
    head_nose(head, L, face, rig)
    surf = HeadSurface(head, body, L)
    if spec.get('bridge'):
        st = dict(st, bridge=spec['bridge'])
    pts, faces, follow, ends, band, streak, tips = hair_grow(pid, surf, st)
    under = None
    if st.get('under'):                                      # (the clipped hair under a two-block cut)
        u_pts, u_faces, u_follow, u_ends, _, _, u_tips = hair_grow(pid, surf, st['under'])
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
            under.append(((name, [u_pts[i] for i in ring], [tuple(at[i] for i in f) for f in fs]), [u_follow[i] for i in ring],
                          [u_tips[i] for i in ring]))
        head_trim(head, surf, st['under'], u_ends, ((pts, faces, tips), (u_pts, u_faces, u_tips)))
    else:
        head_trim(head, surf, st, ends, ((pts, faces, tips),))
    other = set(band) | set(streak)
    pieces = [('Hair', pts, [f for i, f in enumerate(faces) if i not in other])]
    weights, marks = list(follow), list(tips)
    for piece, fol, tp in under or ():
        pieces.append(piece)
        weights += fol
        marks += tp
    for name, part in (('Band', band), ('Bridge', streak)):  # (these have points of their own, weighted as the hair's)
        if part:
            ring = sorted({i for b in part for i in faces[b]})
            at = {i: n for n, i in enumerate(ring)}
            pieces.append((name, [pts[i] * 1.0 for i in ring], [tuple(at[i] for i in faces[b]) for b in part]))
            weights += [follow[i] for i in ring]
            marks += [tips[i] for i in ring]
    col = spec['colors']
    hair = col.get('Hair', HAIR['black'])
    skin = col.get('Skin', SKIN['b'])
    defaults = dict(PART_COLORS, Hair=hair, Bridge=hex_mix(hair, '#d9a35a', 0.5),
                    HairFade=hex_fade(hair, skin, FADE[0]), HairFade2=hex_fade(hair, skin, FADE[1]))
    for name in ('Hair', 'Band', 'Glasses', 'Bridge', 'HairFade', 'HairFade2'):
        colour_material(name, srgb_to_linear(col.get(name, defaults[name])))
    hob = head_part(pid + '-hair', arm, pieces, weights, marks)
    fob = head_part(pid + '-glasses', arm, [('Glasses', *face_glasses(surf, L, rig, face, sunk))])
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


# ---------- the neck's foot ----------
# The packs' neck is a post: the men's stands in the closed top of a tee, the women's on the rim of the body's own
# skin, meeting it at an angle.  Skin painted on the tee's top under a neckline (paint) lay there as a tray, lit from
# above and paler than the neck that stood in it; and the women's two rims, the head's subdivided, shared only some of
# their points: a line round the neck, a tone either side of it.
# Men (neck_bib): a neckline is not painted but cut out of the top, as one round line: `ring` off the neck all
# round (the packs' rim, which stands up the neck there, goes with it) and in front out to where the top lies `drop`
# under the neck's joint, drawn in to the sides by cos^`lobe`; a top's own skin there (an open collar's wedge of
# chest) goes too.  The line is then eased (`line`: within that of what went, so many times): cut by planes it has
# corners, and where it runs into a pack's own V it has steps.  The neck itself, cut off `top` over its joint (under
# the chin: lower, the pack's neck is drawn in like a waist, and the new skin turned out from it at a crease), is
# drawn out from there to under the edge of the cloth: down its own line, then out in a curve to end `slope` degrees
# off upright `under` below where the cloth's edge was, and on for `past` beneath the cloth (`sink` under the lowest
# cloth there: a shirt may lie over the tee).  One skin from the chin to the collar; where nothing is cut the neck
# goes down into the collar on the line of the pack's own (`tube`: the collars were made to it; narrower, a vest's
# collar stood a finger's width off it and the ground showed between).  The new points move with the neck above and
# with the top's own bones at the cloth's edge.
# The game draws a face from its front alone: past the neck, in the gap a collar leaves as the head turns, the
# ground showed through the back of the top.  `liner`: the cloth that reaches within that of the neck's axis and no
# lower than that under its joint is there twice, the second time turned and a hair inside the first (lying in it,
# it shaded it in specks).
# Women (neck_cut, neck_seam): the neck is cut off level `lift` over the body's rim (its own foot is turned in under
# itself in front: over a low rim that showed as a slot) and joined to the rim by new faces: one surface, lit as one.
# The skin within `band` of the join is then eased `ease` times, most at the join and little over it (`up`: the
# jaw is close), so that the corner becomes a hollow curve.
BARE = 'bare'                 # the vertex group of what a neckline bared (paint)
ROUND = 'round'               # and of the top's faces about the neck that may go for the collar's ring
FOOT = dict(top=0.058, slope=25, under=0.0025, past=0.010, sink=0.005, rings=6, tube=0.08, line=(0.008, 8), liner=(0.095, 0.045, 0.002), lift=0.005, band=0.032, up=(0.004, 0.014), ease=14, fold=(0.008, 0.016))


def _ring(edges):
    """The points of a closed loop of edges, in order round it (None if they are not one loop)."""
    at = {}
    for e in edges:
        for v in e.verts:
            at.setdefault(v, []).append(e)
    if not edges or any(len(es) != 2 for es in at.values()):
        return None
    e = min(edges, key=lambda e: e.index)
    v = min(e.verts, key=lambda v: v.index)
    ring, seen = [v], {e}
    while True:
        v = e.other_vert(v)
        if v is ring[0]:
            break
        ring.append(v)
        e = next((x for x in at[v] if x not in seen), None)
        if e is None:
            return None
        seen.add(e)
    return ring if len(ring) == len(edges) else None


def neck_bib(head, body, arm, ring_w=0.0, drop=0.0, lobe=2.0):
    """The men's neck drawn out to under a neckline's edge, and what was bared cut out of the top (see above)."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    from mathutils.kdtree import KDTree
    group, round_ = body.vertex_groups.get(BARE), body.vertex_groups.get(ROUND)
    if group is None and round_ is None:
        return
    F = FOOT
    cn = arm.matrix_world @ arm.data.bones['Neck'].head_local
    is_skin = lambda m: bool(m) and m.name.split('~')[0].split('.')[0] == 'Skin'          # noqa: E731
    bones = {b.name for b in arm.data.bones}
    # the neck: cut level, what is under the cut goes
    names = {g.index: g.name for g in body.vertex_groups}
    for n in sorted(set(names.values()) & bones):
        if head.vertex_groups.get(n) is None:
            head.vertex_groups.new(name=n)
    hnames = {g.index: g.name for g in head.vertex_groups}
    hindex = {n: i for i, n in hnames.items()}
    hb = bmesh.new()
    hb.from_mesh(head.data)
    hb.transform(head.matrix_world)
    hl = hb.verts.layers.deform.verify()
    uv = hb.loops.layers.uv.verify()
    hskin = {i for i, m in enumerate(head.data.materials) if is_skin(m)}
    z1 = cn.z + F['top']
    neck = lambda f: f.material_index in hskin and all(math.hypot(v.co.x, v.co.y - cn.y) < 0.11 and v.co.z < z1 + 0.05 for v in f.verts)   # noqa: E731
    fs = [f for f in hb.faces if neck(f)]
    geom = fs + sorted({e for f in fs for e in f.edges}, key=lambda e: e.index) + sorted({v for f in fs for v in f.verts}, key=lambda v: v.index)
    bmesh.ops.bisect_plane(hb, geom=geom, dist=1e-5, plane_co=Vector((0, 0, z1)), plane_no=Vector((0, 0, 1)))
    hb.verts.index_update()
    low = [f for f in hb.faces if neck(f) and f.calc_center_median().z < z1]
    # (the post that goes: where no neckline is cut the new neck keeps its line, which the collars were made to)
    post = BVHTree.FromPolygons([v.co.copy() for v in hb.verts], [[v.index for v in f.verts] for f in low])
    bmesh.ops.delete(hb, geom=low, context='FACES')
    hb.verts.index_update()
    hb.edges.index_update()
    ring = _ring([e for e in hb.edges if e.is_boundary and all(abs(v.co.z - z1) < 1e-4 for v in e.verts)])
    if ring is None:
        raise SystemExit(f'{head.name}: the neck is not one ring {F["top"]} m over its joint')
    n = len(ring)
    cx, cy = sum(v.co.x for v in ring) / n, sum(v.co.y for v in ring) / n
    # (which way the faces over the cut run round it: the new ones run with them)
    e0 = next(e for e in ring[0].link_edges if e.other_vert(ring[0]) is ring[1])
    if e0.link_loops[0].vert is ring[0]:
        ring.reverse()
    # the top, with what was bared still on it: where its surface lies, seen from above
    bb = bmesh.new()
    bb.from_mesh(body.data)
    bb.transform(body.matrix_world)
    bl = bb.verts.layers.deform.verify()
    skin = {i for i, m in enumerate(body.data.materials) if is_skin(m)}
    held_by = lambda f, g: g is not None and all(v[bl].get(g.index, 0.0) > 0.5 for v in f.verts)          # noqa: E731
    if round_ is not None:
        # the collar: what of the top lies within `ring` of the neck all round goes too (the packs' rim stands up the
        # neck there: cut by a neckline, its ends stood either side of the throat as two points), and in front out
        # to where the top lies `drop` under the neck's joint, drawn in to the sides (cos^lobe): one round line
        az = [(math.atan2(v.co.x - cx, cy - v.co.y), math.hypot(v.co.x - cx, v.co.y - cy)) for v in ring]
        R_at = lambda a: min(az, key=lambda q: abs(math.remainder(q[0] - a, math.tau)))[1]                # noqa: E731
        first = BVHTree.FromBMesh(bb)
        reach, r = 0.0, R_at(0.0)
        while r < 0.16:
            hit = first.ray_cast(Vector((cx + 0.00013, cy - r, cn.z + 0.2)), Vector((0, 0, -1)))
            if hit[0] is not None and hit[0].z <= cn.z - drop:
                reach = r - R_at(0.0) - ring_w
                break
            r += 0.001
        planes = []
        for j in range(24):
            a = math.tau * j / 24
            d = Vector((math.sin(a), -math.cos(a), 0))
            planes.append((Vector((cx, cy, 0)) + d * (R_at(a) + ring_w + max(0.0, reach) * max(0.0, math.cos(a)) ** lobe), d))
        cand = lambda f: f.material_index not in skin and held_by(f, round_)                              # noqa: E731
        mid = Vector((cx, cy))
        for co, no in planes:                              # (each cuts only what lies before it)
            fs = [f for f in bb.faces if cand(f) and any((q.to_2d() - mid).normalized().dot(no.to_2d()) > 0.8
                                                         for q in [f.calc_center_median()] + [v.co for v in f.verts])]
            geom = fs + sorted({e for f in fs for e in f.edges}, key=lambda e: e.index) + sorted({v for f in fs for v in f.verts}, key=lambda v: v.index)
            bmesh.ops.bisect_plane(bb, geom=geom, dist=1e-5, plane_co=co, plane_no=no)
            bb.verts.index_update()
            bb.edges.index_update()
            bb.faces.index_update()
        within = lambda f: all((f.calc_center_median() - co).dot(no) <= 0 for co, no in planes)           # noqa: E731
    else:
        cand = within = lambda f: False                                                                   # noqa: E731
    bb.faces.ensure_lookup_table()
    bb.faces.index_update()
    bare = [(f.material_index in skin and (held_by(f, group) or held_by(f, round_))) or (cand(f) and within(f)) for f in bb.faces]
    if not any(bare):
        raise SystemExit(f'{body.name}: nothing bared for the neck to run to')
    # the neckline eased: the cut's corners (it is cut by planes), and a pack's own open collar that the cut runs
    # into (a V with a notch at its foot, steps where the two meet)
    kept = lambda f: not bare[f.index] and cand(f)                                                        # noqa: E731
    near = KDTree(sum(len(f.verts) for f, b in zip(bb.faces, bare) if b))
    for i, v in enumerate(v for f, b in zip(bb.faces, bare) if b for v in f.verts):
        near.insert(v.co, i)
    near.balance()
    at = {}
    for e in bb.edges:
        if sum(1 for f in e.link_faces if kept(f)) == 1 and all(kept(f) or bare[f.index] for f in e.link_faces):
            a, b = e.verts
            if all(near.find(v.co)[2] < F['line'][0] for v in (a, b)):
                at.setdefault(a, []).append(b)
                at.setdefault(b, []).append(a)
    line = sorted((v for v, vs in at.items() if len(vs) == 2), key=lambda v: v.index)
    for _ in range(F['line'][1]):
        to = {v: (at[v][0].co + at[v][1].co) / 2 for v in line}
        for v in line:
            v.co = v.co.lerp(to[v], 0.5)
    tree = BVHTree.FromBMesh(bb)
    # (a shirt worn over the tee, or what is left of its rim, may hang over the opening: the opening is measured on
    # what was bared alone)
    cos = [v.co.copy() for v in bb.verts]
    gone = BVHTree.FromPolygons(cos, [[v.index for v in f.verts] for f, b in zip(bb.faces, bare) if b])
    cloth = BVHTree.FromPolygons(cos, [[v.index for v in f.verts] for f, b in zip(bb.faces, bare) if not b and f.material_index not in skin])

    def cap(p):
        hit = gone.ray_cast(Vector((p[0] + 0.00013, p[1] + 0.00007, cn.z + 0.2)), Vector((0, 0, -1)))
        return hit[0].z if hit[0] is not None else None

    def lowest(p, z):
        """The lowest cloth over p within 3 cm of the height z (a shirt over a tee: the lower of the two)."""
        o, low = Vector((p[0] + 0.00013, p[1] + 0.00007, z + 0.03)), None
        for _ in range(6):
            hit = cloth.ray_cast(o, Vector((0, 0, -1)), o.z - (z - 0.03))
            if hit[0] is None:
                break
            low, o = hit[0].z, hit[0] - Vector((0, 0, 0.0004))
        return low

    def held(p):
        """The bones of the top's nearest point."""
        f = bb.faces[tree.find_nearest(p)[2]]
        v = min(f.verts, key=lambda v: ((v.co - p).length, v.index))
        w = {names[g]: x for g, x in v[bl].items() if names[g] in bones and x > 0}
        t = sum(w.values()) or 1.0
        return {k: x / t for k, x in w.items()}

    K, ta = F['rings'], math.tan(math.radians(F['slope']))
    cols = []
    for v in ring:
        dx, dy = v.co.x - cx, v.co.y - cy
        R = math.hypot(dx, dy)
        dx, dy = dx / R, dy / R
        at = lambda r: (cx + dx * r, cy + dy * r)                                         # noqa: E731
        rh, r = None, R - 0.006
        while r < 0.17:
            if cap(at(r)) is not None:
                rh = r
            r += 0.002
        own = {hnames[g]: x for g, x in v[hl].items() if x > 0}
        luv = next(l[uv].uv.copy() for l in v.link_loops)
        pts = []
        if rh is not None and rh > R:
            zq = cap(at(rh)) - F['under']
            z0 = min(z1 - 0.004, zq + (rh - R) / ta)                  # (the corner the curve rounds, on the neck's line)
            for k in range(1, K):
                t = k / (K - 1)
                pts.append((R + (rh - R) * t * t, z1 * (1 - t) ** 2 + z0 * 2 * t * (1 - t) + zq * t * t, t))
            re = rh + F['past']
            ze = lowest(at(re), zq)
            pts.append((re, min(zq - F['past'] / ta, zq if ze is None else ze - F['sink']), 1.0))
        else:
            r = R
            for k in range(1, K + 1):
                z = z1 - F['tube'] * k / K
                hit = post.ray_cast(Vector((cx, cy, z)), Vector((dx, dy, 0)), 0.12)
                if hit[0] is not None and 0.75 * R < hit[3] < 1.35 * R:     # (not the post's closed foot)
                    r = hit[3]
                pts.append((r, z, k / K))
        col = [v]
        for r, z, t in pts:
            x, y = at(r)
            nv = hb.verts.new(Vector((x, y, z)))
            f = _smooth(0.0, 0.85, t)
            their = held(nv.co)
            for name in sorted(set(own) | set(their)):
                w = own.get(name, 0.0) * (1 - f) + their.get(name, 0.0) * f
                if w > 0:
                    nv[hl][hindex[name]] = w
            col.append(nv)
        cols.append((col, luv))
    si = min(hskin)
    for i in range(n):
        (a, ua), (b, ub) = cols[i], cols[(i + 1) % n]
        for k in range(K):
            f = hb.faces.new((a[k], b[k], b[k + 1], a[k + 1]))
            f.material_index = si
            f.smooth = True
            for l in f.loops:
                l[uv].uv = ua if l.vert in a else ub
    hb.normal_update()
    hb.transform(head.matrix_world.inverted())
    hb.to_mesh(head.data)
    hb.free()
    bmesh.ops.delete(bb, geom=[f for f, b in zip(bb.faces[:], bare) if b], context='FACES')
    # the collar's inside: the cloth about the opening again, turned (the game draws a face from its front alone: past
    # the neck, in the gap a collar leaves as the head turns, the ground showed through the back of the top)
    lin = [f for f in bb.faces if f.material_index not in skin
           and any(math.hypot(v.co.x - cx, v.co.y - cy) < F['liner'][0] and v.co.z > cn.z - F['liner'][1] for v in f.verts)]
    made = bmesh.ops.duplicate(bb, geom=lin)['geom']
    bmesh.ops.reverse_faces(bb, faces=[g for g in made if isinstance(g, bmesh.types.BMFace)])
    bb.normal_update()
    for v in sorted((g for g in made if isinstance(g, bmesh.types.BMVert)), key=lambda v: v.index):
        v.co += v.normal * F['liner'][2]              # (a hair inside the cloth: lying in it, it shaded it in specks)
    bb.transform(body.matrix_world.inverted())
    bb.to_mesh(body.data)
    bb.free()


def _open_rims(bm, skin, near):
    """The loops of open edges about the neck's foot that hold an edge of skin (the body's rim may be a collar's
    band behind the neck; a head of hair and a shirt's collar have open edges there too, none of skin)."""
    open_ = [e for e in bm.edges if e.is_boundary and all(near(v) for v in e.verts)]
    at = {}
    for e in open_:
        for v in e.verts:
            at.setdefault(v, []).append(e)
    rims, todo = [], set(open_)
    for e in sorted(open_, key=lambda e: e.index):
        if e not in todo:
            continue
        todo.discard(e)
        comp, stack = [e], [e]
        while stack:
            for v in stack.pop().verts:
                for x in at[v]:
                    if x in todo:
                        todo.discard(x)
                        comp.append(x)
                        stack.append(x)
        if any(x.link_faces[0].material_index in skin for x in comp):
            rims.append(comp)
    return rims


def neck_cut(head, body, arm):
    """The women's neck cut off level, `lift` over the highest point of the body's rim of skin (neck_seam joins the
    two); returns the height, or None where the body has no such rim."""
    import bmesh
    F = FOOT
    cn = arm.matrix_world @ arm.data.bones['Neck'].head_local
    is_skin = lambda m: bool(m) and m.name.split('~')[0].split('.')[0] == 'Skin'          # noqa: E731
    near = lambda v: math.hypot(v.co.x, v.co.y - cn.y) < 0.10 and -0.03 < v.co.z - cn.z < 0.08          # noqa: E731
    bb = bmesh.new()
    bb.from_mesh(body.data)
    bb.transform(body.matrix_world)
    rims = _open_rims(bb, {i for i, m in enumerate(body.data.materials) if is_skin(m)}, near)
    z1 = max((v.co.z for e in rims[0] for v in e.verts), default=0.0) + F['lift']
    bb.free()
    if len(rims) != 1:
        return None
    hb = bmesh.new()
    hb.from_mesh(head.data)
    hb.transform(head.matrix_world)
    hskin = {i for i, m in enumerate(head.data.materials) if is_skin(m)}
    neck = lambda f: f.material_index in hskin and all(math.hypot(v.co.x, v.co.y - cn.y) < 0.11 and v.co.z < z1 + 0.03 for v in f.verts)   # noqa: E731
    fs = [f for f in hb.faces if neck(f)]
    geom = fs + sorted({e for f in fs for e in f.edges}, key=lambda e: e.index) + sorted({v for f in fs for v in f.verts}, key=lambda v: v.index)
    bmesh.ops.bisect_plane(hb, geom=geom, dist=1e-5, plane_co=Vector((0, 0, z1)), plane_no=Vector((0, 0, 1)))
    bmesh.ops.delete(hb, geom=[f for f in hb.faces if neck(f) and f.calc_center_median().z < z1], context='FACES')
    hb.verts.index_update()
    hb.edges.index_update()
    if _ring([e for e in hb.edges if e.is_boundary and all(abs(v.co.z - z1) < 1e-4 for v in e.verts)]) is None:
        raise SystemExit(f'{head.name}: the neck is not one ring {z1 - cn.z:.3f} m over its joint')
    hb.transform(head.matrix_world.inverted())
    hb.to_mesh(head.data)
    hb.free()
    return z1


def neck_seam(mesh, arm, z1):
    """The women's neck (cut at z1: neck_cut) and the body's own skin made one surface, the corner between them a
    curve (see above)."""
    import bmesh
    F = FOOT
    me = mesh.data
    cn = arm.matrix_world @ arm.data.bones['Neck'].head_local
    skin = {i for i, m in enumerate(me.materials) if m and m.name.split('~')[0].split('.')[0] == 'Skin'}
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    near = lambda v: math.hypot(v.co.x, v.co.y - cn.y) < 0.11 and -0.03 < v.co.z - cn.z < 0.08          # noqa: E731
    rims = _open_rims(bm, skin, near)
    cut = [r for r in rims if all(abs(v.co.z - z1) < 1e-4 for e in r for v in e.verts)]
    if len(rims) != 2 or len(cut) != 1:
        raise SystemExit(f'{mesh.name}: {len(rims)} open rims at the neck, {len(cut)} of them the cut')
    rim = rims[0] + rims[1]
    seam = sorted({v for e in rim for v in e.verts}, key=lambda v: v.index)
    old = set(bm.faces)
    bmesh.ops.bridge_loops(bm, edges=rim)
    made = sorted(set(bm.faces) - old, key=lambda f: f.index)
    if not made or any(e.is_boundary for e in rim if e.is_valid):
        raise SystemExit(f'{mesh.name}: the neck and the body are still apart')
    bmesh.ops.triangulate(bm, faces=[f for f in made if len(f.verts) > 3], quad_method='BEAUTY', ngon_method='BEAUTY')
    # (the new faces turned the way of the skin they join: along a shared edge the two faces run opposite ways)
    done, todo = set(old), [f for f in bm.faces if f not in old]
    for f in todo:
        f.material_index = min(skin)
        f.smooth = True
    while todo:
        rest = []
        for f in sorted(todo, key=lambda f: f.index):
            l = next((l for l in f.loops if any(x.face in done for x in l.link_loops)), None)
            if l is None:
                rest.append(f)
                continue
            if next(x for x in l.link_loops if x.face in done).vert is l.vert:
                f.normal_flip()
            done.add(f)
        if len(rest) == len(todo):
            break
        todo = rest
    for f in bm.faces:
        if f not in old:
            for l in f.loops:
                l[uv].uv = next((x[uv].uv.copy() for x in l.vert.link_loops if x.face in old and x.face.material_index in skin), l[uv].uv)
    # the corner eased: skin alone (what a cloth's edge holds stays), most at the join
    free = [v for v in bm.verts if near(v) and v.link_faces and all(f.material_index in skin for f in v.link_faces) and not v.is_boundary]
    wt = {}
    for v in free:
        near_ = min(seam, key=lambda s: ((v.co - s.co).length, s.index))
        d = (v.co - near_.co).length
        if d < F['band']:                                  # (and little above the join: the jaw is close over it)
            wt[v] = (1 - _smooth(F['band'] * 0.35, F['band'], d)) * (1 - _smooth(*F['up'], v.co.z - z1))
    for _ in range(F['ease']):
        to = {v: sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges) for v in wt}
        for v, w in wt.items():
            v.co = v.co.lerp(to[v], 0.5 * w)
    # a fold of the pack's own under the collarbones (the Suit's top: a ledge 3 mm deep whose underside lay in shade,
    # a dark line either side of the throat), eased the same way
    bm.normal_update()
    fold = sorted({v for f in bm.faces if f.material_index in skin and f.normal.z < -0.3
                   and all(near(v) and v.co.y < cn.y - 0.02 and -0.03 < v.co.z - cn.z < 0.02 for v in f.verts) for v in f.verts},
                  key=lambda v: v.index)
    wt = {}
    for v in free if fold else ():
        d = min((v.co - q.co).length for q in fold)
        if d < F['fold'][1]:
            wt[v] = 1 - _smooth(*F['fold'], d)
    for _ in range(F['ease']):
        to = {v: sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges) for v in wt}
        for v, w in wt.items():
            v.co = v.co.lerp(to[v], 0.5 * w)
    bm.to_mesh(me)
    bm.free()


# ---------- the shoulder line ----------
# With the arms down, seen from the front (reference/고증 4.13.1): the men's shoulder ran from the neck to over the
# joint, 6.9 cm above it, and fell from there at 45 degrees to the arm: a round, drooping tip (3.6 cm over the joint
# where the bone's end is, 3.5 cm outside it).  The women's fell 32 degrees from the neck to a tip 2.2 cm over the
# joint, and the arm stood out from under it: 37.5 cm across the upper arms.  A shoulder's line runs down from the
# neck in a hollow, twenty-odd degrees, to the bone's end 4 to 5 cm over the joint, and the arm's muscle rounds the
# corner under that (rough figures of the human build: no survey was found).
# The shape is set where it is seen: the arms are put down (`out` degrees off upright, as the standing clips hold
# them), every point is taken to where its bones carry it, moved there, and brought back to the T pose by the same
# bones (what the upper arm holds turns with it: a lift made in the T pose swung out as a knob).  The moves are
# `handles`: (m outside the joint, m over it; m out, m up; reach m), each fading as a bell about its place in the
# plane seen from the front, and from front to back over the shoulder's crest only (`crest`: all of it within so far
# of the joint, nothing from so far: lifted with the crest, a top's edge in front of and behind the arm stood over
# the sleeve as a shelf).  The game's metres.  A person's own `shoulders`: `square` scales what the handles raise
# (more: a leveller line, a firmer corner), `broad` is added to what they move out.
# Kept small: a lift of 1.6 cm at the corner made a jacket's shoulder a peak and a hood's seam a ledge with a dark
# groove under it, and easing the corner afterwards (by its neighbours in the mesh, or by the distance from the
# joint's axis) moved the knots of small faces at a seam through each other or pushed the shoulder's front and back
# out over the sleeve.  The pack's own seams stay as they are.
SHOULDER = {'umc': dict(out=4, crest=(0.035, 0.085),
                        handles=[(0.035, 0.035, 0.009, 0.006, 0.045), (-0.035, 0.085, 0.0, -0.008, 0.040)]),
            'women': dict(out=14, crest=(0.030, 0.075),
                          handles=[(0.030, 0.025, 0.006, 0.007, 0.045), (0.050, -0.035, 0.010, 0.0, 0.050)])}


WAS = 'shoulder_was'          # the vertex attribute of where a point was before shoulder_line, from where it is (occlude)


def shoulder_line(parts, arm, rig, s, own=None):
    S, own = SHOULDER[rig], own or {}
    handles = [(u0, h0, mu + (own.get('broad', 0.0) if u0 > 0 else 0.0), mh * (own.get('square', 1.0) if mh > 0 else 1.0), sig)
               for u0, h0, mu, mh, sig in S['handles']]
    P, aw = arm.pose.bones, arm.matrix_world
    joint = {}
    for side, sx in (('L', 1), ('R', -1)):
        ua, la = P['UpperArm.' + side], P['LowerArm.' + side]
        d = la.head - ua.head
        rotate_about_head(ua, 'Y', sx * (90 - S['out'] + math.degrees(math.atan2(d.z, abs(d.x)))))
        joint[sx] = aw @ ua.head
    bpy.context.view_layer.update()
    top = {sx: ((aw @ P['Head'].head).z - joint[sx].z) * s for sx in joint}
    M = {pb.name: pb.matrix @ pb.bone.matrix_local.inverted() for pb in P}
    reach = max(abs(h[0]) + 3 * h[4] for h in handles)
    for ob in parts:
        me = ob.data
        names = {g.index: g.name for g in ob.vertex_groups if g.name in M}
        to_arm = aw.inverted() @ ob.matrix_world
        back = to_arm.inverted()
        at = {}                                      # vertex -> [where the bones carry it, its bones' matrix, the side, u, h]
        for v in me.vertices:
            gs = [(names[g.group], g.weight) for g in v.groups if g.group in names and g.weight > 0]
            tot = sum(w for _, w in gs)
            if tot < 1e-6:
                continue
            B = Matrix.Diagonal((0, 0, 0, 0))
            for n, w in gs:
                B += M[n] * (w / tot)
            p = aw @ (B @ (to_arm @ v.co))
            sx = 1 if p.x >= 0 else -1
            u, h = (abs(p.x) - abs(joint[sx].x)) * s, (p.z - joint[sx].z) * s
            if abs(u) <= reach and abs(h) <= 0.25:
                at[v.index] = [p, B, sx, u, h]
        was = me.attributes.get(WAS) or me.attributes.new(WAS, 'FLOAT_VECTOR', 'POINT')
        for i, (p, B, sx, u, h) in at.items():
            du = dh = 0.0
            # (and nothing from under the chin up: the head keeps its shape)
            crest = (1 - _smooth(S['crest'][0], S['crest'][1], abs(p.y - joint[sx].y) * s)) * (1 - _smooth(top[sx] - 0.05, top[sx] - 0.02, h))
            for u0, h0, mu, mh, sig in handles:
                # (a lift takes all that stands over its place with it, a move outward all that lies outside it: a
                # seam's fold moves whole, where a bell on every side raised the fold's edge off the sleeve under it)
                a, b = (u - u0, min(0.0, h - h0)) if abs(mh) >= abs(mu) else (min(0.0, u - u0), h - h0)
                g = math.exp(-(a * a + b * b) / sig ** 2) * crest
                du += mu * g
                dh += mh * g
            if abs(du) + abs(dh) < 2e-5:
                continue
            q = Vector((p.x + sx * du / s, p.y, p.z + dh / s))
            old = me.vertices[i].co.copy()
            me.vertices[i].co = back @ (B.inverted() @ (aw.inverted() @ q))
            was.data[i].vector = old - me.vertices[i].co
        me.update()
    for pb in P:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


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
        if part == 'body' and rig == 'women':
            round_bust(ob, arm, spec.get('bust', 1.0))
        if part in spec.get('paint', {}):
            paint(ob, spec['paint'][part], arm, bib=rig == 'umc')
        if part in spec.get('prints', {}):
            print_map(ob, spec['prints'][part])
        recolour(ob, part, spec['colors'])
        # (the neck is the head's, the waist the body's and the legs'; a person's own `neck`: how much of the
        # rig's widening of it, for a narrow jaw over which the neck stood as wide as the face)
        shape_body(ob, arm, rig, spec.get('neck', 1.0))
        loosen(ob, part, outfit, arm, spec.get('roomy'))
        if part == 'body' and rig == 'umc':
            lay_collar(ob, outfit, arm)
        if part == 'body' and spec.get('sleeves'):
            long_sleeves(ob, arm, **spec['sleeves'])
        elif part == 'body' and rig == 'umc':
            even_arms(ob, arm)
        if part == 'body':
            hold_collar(ob, arm, HOLD[rig])
        atlas_layer(ob)
        ob.name = f'{pid}-{part}'
        parts.append(ob)
    body, head = parts[0], parts[1]
    if rig == 'umc':
        bared = [r['neck'] for r in spec.get('paint', {}).get('body', ()) if r.get('neck') and r['to'] == 'Skin']
        if bared:
            neck_bib(head, body, arm, bared[0]['ring'], bared[0]['drop'], bared[0]['lobe'])
    for name in (BARE, ROUND):
        if body.vertex_groups.get(name):
            body.vertex_groups.remove(body.vertex_groups[name])
    if spec.get('skirt'):
        cut_skirt(next(o for o in parts if o.name.endswith('-legs')), arm, SKIRTS[spec['skirt']])
    if any(m and m.name == 'Skirt~new' for o in parts for m in o.data.materials):         # (recolour's names)
        skirt_sit(arm, [o for o in parts if o.name.endswith(('-body', '-legs'))], s)
    keep = set(parts) | {arm}
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    clear_anim(arm)
    relax_fingers(arm, parts, rig, s)
    shoulder_line([o for o in parts if o.name.endswith(('-body', '-head'))], arm, rig, s, spec.get('shoulders'))
    cut = spec.get('cut') or TROUSERS.get(spec['parts']['legs'])
    if cut:
        cut_trousers(next(o for o in parts if o.name.endswith('-legs')), arm, CUTS[rig][cut])
    fit = fit_of(spec)
    if fit:
        ease_sleeves(body, arm, fit)
        hang_top(body, next(o for o in parts if o.name.endswith('-legs')), arm, fit)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    return finish_person(pid, arm, parts, s, 'rig-' + rig, bool(spec.get('face', {}).get('glasses')))


OCC = '_OCC'                  # the vertex attribute of the shade below (glTF: a custom attribute)
OCC_FAR = 0.28                # metres: what is further away shades nothing
OCC_RAYS = 24


def occlude(mesh, scale=1.0):
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
    # (the shoulders are shaped as they stand with the arms down, shoulder_line: taken back to this pose, what the
    # arm holds and what the trunk holds of a sleeve's seam lie through each other, and the shade of that stayed on
    # the seam as a dark band.  The shade is that of the shape before: `scale`, what the mesh was scaled by since)
    was = me.attributes.get(WAS)
    cos = [v.co + Vector(was.data[v.index].vector) * scale if was else v.co.copy() for v in me.vertices]
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
        o = cos[i] + n * 0.004
        shut = 0.0
        for x, y, z in dirs:
            d = n * z + t * (x * cs - y * sn) + b * (x * sn + y * cs)
            hit = trees[leg[i]].ray_cast(o, d, OCC_FAR)
            if hit[0] is not None:
                shut += 1 - hit[3] / OCC_FAR
        vals.append(min(1.0, shut / OCC_RAYS * 1.5))
    att.data.foreach_set('value', vals)
    if was:
        me.attributes.remove(was)


THIN = (0.006, 0.018)        # metres: skin this thin lets the sun behind it through, this thick none of it
THIN_HEAD = 0.27             # (only the head's: so far down from the top of the hair)


def thin_skin(mesh):
    """How thin the head's skin is (an ear; the nose a little): for the game, which lets the sun behind such skin shine
    through it red (web/src/characters.js SKIN_SUN).  A ray from each point of the skin into the head, to where it comes
    out again; kept in the attribute LEG as (0, 0, thin): a trouser leg's coordinates never have both of the first
    two 0, so the game tells them apart."""
    from mathutils.bvhtree import BVHTree
    me = mesh.data
    skin = {i for i, m in enumerate(me.materials) if m and m.name.split('.')[0] == 'Skin'}
    polys = [p for p in me.polygons if p.material_index in skin]
    tree = BVHTree.FromPolygons([v.co for v in me.vertices], [tuple(p.vertices) for p in polys])
    z0 = max(v.co.z for v in me.vertices) - THIN_HEAD
    thin = {}
    for i in {i for p in polys for i in p.vertices}:
        v = me.vertices[i]
        if v.co.z < z0:
            continue
        hit = tree.ray_cast(v.co - v.normal * 0.0008, -v.normal, 0.03)
        if hit[0] is not None and hit[1].dot(v.normal) < 0:           # (out through skin that looks the other way)
            thin[i] = 1 - _smooth(THIN[0], THIN[1], hit[3] + 0.0008)
    near = {}
    for e in me.edges:
        a, b = e.vertices
        if a in thin or b in thin:
            near.setdefault(a, []).append(b)
            near.setdefault(b, []).append(a)
    eased = {i: (thin.get(i, 0.0) + sum(thin.get(j, 0.0) for j in js) / len(js)) / 2 for i, js in near.items()}
    att = me.attributes.get(LEG) or me.attributes.new(LEG, 'FLOAT_VECTOR', 'POINT')
    for i, t in eased.items():
        if t > 0.02 and not any(att.data[i].vector):
            att.data[i].vector = (0.0, 0.0, t)


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
    cut = None
    if rig == 'rig-women':
        cut = neck_cut(next(o for o in parts if o.name.endswith('-head')), next(o for o in parts if o.name.endswith('-body')), arm)
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
    if cut is not None:
        neck_seam(mesh, arm, cut)
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
    occlude(mesh, s)
    thin_skin(mesh)
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
    likewise only on the parts with trousers, as bytes; a head of hair carries its strands' ends in the same attribute
    (TIP_FAR)."""
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
                    # (or of the shell of a head of hair: either has one of the first two; thin skin, thin_skin, has
                    # neither and is told by that)
                    q = lambda v: min(255, max(0, round(v * 255)))
                    views[acc['bufferView']] = b''.join(
                        bytes([q(vals[i]), q(vals[i + 1]), q(vals[i + 2]), 255 if any(vals[i:i + 2]) else 0])
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

def face_atlas(near=None):
    """faces.png: everybody's face in the order of PEOPLE (the cells face_map lays the faces on); faces_rims.png:
    everybody's glasses in the same cells (the game shows them on whoever wears glasses, from a few metres off);
    faces/<id>.png, faces/<id>_n.png: each face from near, four times as fine, and its relief (near: of these ids
    only; 3 s a face)."""
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
    # everybody's face from near, a picture and its relief each (the game fetches them for whoever stands near)
    folder = os.path.join(OUT, faces.NEAR_DIR)
    faces.write_near(folder, [(pid,) + row for pid, row in zip(PEOPLE, rows)], near)
    size = sum(os.path.getsize(os.path.join(folder, n)) for n in os.listdir(folder) if n.endswith('.png'))
    print(f'faces from near: {len(near) if near is not None else len(rows)} of {len(rows)} drawn, {size // 1024} KB in all  ({faces.NEAR} px; '
          f'then python tools/webp_textures.py for the copies the game fetches)')


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
        wanted += ([p for p in PEOPLE if PEOPLE[p]['rig'] == 'umc'] if a == 'men' else
                   [p for p in PEOPLE if PEOPLE[p]['rig'] == 'women'] if a == 'women' else list(RIGS) if a == 'rigs' else
                   [] if a == 'faces' else [a])
    unknown = [w for w in wanted if w not in PEOPLE and w not in RIGS]
    if unknown:
        raise SystemExit('unknown id(s): ' + ', '.join(unknown))
    todo = wanted or ([] if 'faces' in argv else list(RIGS) + list(PEOPLE))
    os.makedirs(OUT, exist_ok=True)
    if 'faces' in argv or any(pid in PEOPLE for pid in todo):
        face_atlas(None if 'faces' in argv or not wanted else [pid for pid in todo if pid in PEOPLE])
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
        if pid in PEOPLE:       # Draco (tools/draco_glb.mjs, normals at 12 bits): a person's 207 KB -> 80 KB after gzip
            import subprocess
            subprocess.run(['node', os.path.join(ROOT, 'tools', 'draco_glb.mjs'), '--normal', '12', os.path.join(OUT, pid + '.glb')], check=True)
        print(f'{pid}: glb {os.path.getsize(path) // 1024} KB  ({src})' + ('' if not problems else '  PROBLEMS: ' + '; '.join(problems)))
        if problems:
            failed.append(pid)
    if failed:
        raise SystemExit('failed: ' + ', '.join(failed))


main()
