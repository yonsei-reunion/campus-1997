"""Build every 3D asset of the Yonsei-1997 campus and export GLBs for the web app.

usage: blender -b --factory-startup --python blender/build.py -- [buildings] [statues] [landmarks] [road] [town] [veg] [shrubs] [props] [cars] [polyhaven] [preview]
(no argument = everything; add noao to skip the occlusion / weathering bake of the halls and landmarks, blender/bake.py)
"""
import sys, os, math, random, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix
import common
from common import CAMPUS, OUT, reset_scene, export_glb, tri_count, ground
import generic, landmarks, vegetation, props, road, statues, bake, shrubs, town

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ALL = not argv
BLEND = 'blend' in argv
BAKE = 'noao' not in argv
argv = [a for a in argv if a not in ('blend', 'noao')]
ALL = not argv
want = lambda k: ALL or k in argv
stats = {}


def place(mb, x, y, z, rot):
    mb.xf = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, 'Z') @ mb.xf
    return mb


def ghost_draws(i, rnd):
    """Halls left out of the 1997 campus after OSM (tools/build_campus.py GONE_1997): draw for them at their old
    place in the list as if they were built, so that the halls after them keep their colours and roof clutter."""
    for g in CAMPUS.get('rnd_ghosts', []):
        if g['at'] == i:
            generic.build_generic(g, rnd)


if want('buildings'):
    reset_scene()
    rnd = random.Random(1997)
    objs = []
    for i, b in enumerate(CAMPUS['buildings']):
        ghost_draws(i, rnd)
        if b['style'].startswith('lm:'):
            continue
        ob = generic.build_generic(b, rnd).build()
        ob['name_ko'] = b['name']
        ob['bid'] = str(b['id'])
        objs.append(ob)
    # the halls' front flights (generic.porch): walked on like the landmarks' (web/src/main.js looks for 'walk_stairs')
    objs.append(landmarks.walk_mesh().build())
    json.dump(generic.DOORS, open(os.path.join(common.ROOT, 'data', 'entrances_generic.json'), 'w'))
    if BAKE:        # (the landmarks' shadows on the halls from their last build)
        bake.bake(objs, sun_glb=os.path.join(OUT, 'campus_landmarks.glb'))
    stats['buildings'] = tri_count(objs)
    export_glb(objs, os.path.join(OUT, 'campus_buildings.glb'), colors=BAKE)

if want('statues'):         # the bronzes' sculpts, baked onto light meshes (blender/sculpt.py); the landmarks read them back
    for fn in statues.SCULPTS.values():
        reset_scene()
        fn()

if want('landmarks'):
    reset_scene()
    objs = []
    for b in CAMPUS['buildings']:
        if not b['style'].startswith('lm:'):
            continue
        key = b['style'][3:]
        for mb in landmarks.BUILDERS[key]():
            ob = mb.build()
            ob['name_ko'] = b['name']
            ob['bid'] = str(b['id'])
            objs.append(ob)
    for mb in landmarks.amphitheater() + landmarks.basketball_court() + landmarks.fountain() + landmarks.tennis() + landmarks.gongwon_site() + \
            landmarks.underwood_steps() + landmarks.aud_bank():
        objs.append(mb.build())
    objs += [mb.build() for mb in landmarks.parking_lines()]      # (the car parks' painted bays)
    # statues and the gate are modelled in their own frame (front = -Y) and placed by object transform
    # (a MeshBuilder's xf only affects vertices added after it is set)
    S = CAMPUS['statues']
    for key, fn in (('eagle', lambda: statues.eagle_statue(S['eagle'])), ('underwood_statue', statues.underwood_statue),
                    ('gate', lambda: [props.gate().build()])):
        st = S[key]
        M = Matrix.Translation((st['pos'][0], st['pos'][1], st['h'])) @ Matrix.Rotation(st['rot'], 4, 'Z')
        for ob in fn():
            ob.matrix_world = M @ ob.matrix_world
            ob.name = key + '_' + ob.name
            objs.append(ob)
    # the Underwood statue's curb ring and round slab are walked onto, not bumped into (the walker's ankle ray, 0.1 m,
    # would otherwise stop at the curb: web/src/player.js WALL_RAY_H)
    st = S['underwood_statue']
    for r_, z_ in statues.UW_WALK:
        for k in range(32):
            a0, a1 = 2 * math.pi * k / 32, 2 * math.pi * (k + 1) / 32
            landmarks.WALK_FACES.append([(st['pos'][0], st['pos'][1], st['h'] + z_),
                                         (st['pos'][0] + r_ * math.cos(a0), st['pos'][1] + r_ * math.sin(a0), st['h'] + z_),
                                         (st['pos'][0] + r_ * math.cos(a1), st['pos'][1] + r_ * math.sin(a1), st['h'] + z_)])
    # the eagle's brick ring, a step up from its walks, is walked on round the dais (the dais itself is not)
    st = S['eagle']
    if 'ring' in st:
        (r0_, _), (r1_, z_) = st['dais'], st['ring']
        for k in range(48):
            a0, a1 = 2 * math.pi * k / 48, 2 * math.pi * (k + 1) / 48
            q_ = [(st['pos'][0] + r_ * math.cos(a_), st['pos'][1] + r_ * math.sin(a_), st['h'] + z_)
                  for r_, a_ in ((r0_, a0), (r1_, a0), (r1_, a1), (r0_, a1))]
            landmarks.WALK_FACES.append(q_)
    objs.append(landmarks.walk_mesh().build())
    # where the entrance flights are, so the web app keeps the apron shrubs off the steps
    _gp = os.path.join(common.ROOT, 'data', 'entrances_generic.json')
    _gen = json.load(open(_gp)) if os.path.exists(_gp) else []
    json.dump({'entrances': landmarks.ENTRANCES + _gen}, open(os.path.join(common.ROOT, 'web/public/data/entrances.json'), 'w'))
    if BAKE:
        bake.bake(objs, sun_glb=os.path.join(OUT, 'campus_buildings.glb'))
    stats['landmarks'] = tri_count(objs)
    export_glb(objs, os.path.join(OUT, 'campus_landmarks.glb'), colors=BAKE)

if want('road'):
    reset_scene()
    mbs, crossings = road.build()
    objs = [m.build() for m in mbs]
    stats['road'] = tri_count(objs)
    export_glb(objs, os.path.join(OUT, 'baekyangro.glb'))
    json.dump({'crossings': crossings}, open(os.path.join(common.ROOT, 'web/public/data/road_meta.json'), 'w'))

if want('town'):          # 정문 밖 (blender/town.py): 성산로, the 경의선's bank and bridge, the town south of it; the city bus
    reset_scene()
    objs = [m.build() for m in town.build()]
    if objs:
        stats['town'] = tri_count(objs)
        export_glb(objs, os.path.join(OUT, 'campus_town.glb'))
    reset_scene()
    mb, wheels = town.bus()
    objs = [mb.build()]
    for w in wheels:
        o = w.build()
        o.location = w.wheel_pos
        objs.append(o)
    stats['bus'] = tri_count(objs)
    export_glb(objs, os.path.join(OUT, 'props', 'bus.glb'))

if want('veg'):
    for sp in vegetation.SPECIES:
        for v in range(2):
            reset_scene()
            mb = vegetation.make_tree(sp, v)
            ob = mb.build()
            vegetation.apply_canopy_normals(ob, mb.leaf_center, mb.leaf_radii)
            stats[f'{sp}_{v}'] = tri_count([ob])
            export_glb([ob], os.path.join(OUT, 'veg', f'{sp}_{v}.glb'), colors=True)

if want('veg') or want('shrubs'):       # (`shrubs` alone: the clipped shrubs without the trees, blender/shrubs.py)
    for k in ('topiary_round', 'topiary_cone', 'hedge_blob', 'bush', 'hedge_low', 'azalea_red', 'azalea_violet', 'pansy_bed',
              'juniper_tiers', 'yew_tiers'):
        reset_scene()
        ob = vegetation.make_shrub(k).build()
        stats[k] = tri_count([ob])
        export_glb([ob], os.path.join(OUT, 'veg', f'{k}.glb'), colors=True)
        # farther than 25 m (web/src/main.js): a third of the cards, the body collapsed to 40 %
        export_glb(shrubs.far_version(ob), os.path.join(OUT, 'veg', f'{k}_far.glb'), colors=True)

if want('props'):
    for name, fn in (('lamp_double', props.lamp_double), ('motorbike', props.motorbike), ('lamp_arm', props.lamp_arm),
                     ('lamp_quad', props.lamp_quad), ('flag_white', props.flag_white), ('planter', props.planter),
                     ('stone_marker', props.stone_marker), ('sign_board', props.sign_board), ('guard_booth', props.guard_booth),
                     ('barrier_arm', props.barrier_arm), ('bollard', props.bollard), ('tent_kiosk', props.tent_kiosk),
                     ('notice_board', props.notice_board), ('haetae', props.haetae), ('bench', props.bench),
                     ('recycle_bin', props.recycle_bin), ('parking_booth', props.parking_booth)):
        reset_scene()
        ob = fn().build()
        stats[name] = tri_count([ob])
        export_glb([ob], os.path.join(OUT, 'props', f'{name}.glb'))

if want('props') or want('cars'):     # (`cars` alone: the cars without the other props)
    import cars
    for k in ('sedan', 'sedan2', 'hatch', 'tico', 'taxi', 'van'):
        reset_scene()
        mb, wheels = cars.build_car(k)
        body = mb.build()
        body.name = 'body'
        try:
            body.data.set_sharp_from_angle(angle=math.radians(38))
        except Exception:
            pass
        objs = [body]
        for w in wheels:
            o = w.build()
            o.name = w.name
            o.location = w.wheel_pos
            objs.append(o)
        stats['car_' + k] = tri_count(objs)
        export_glb(objs, os.path.join(OUT, 'props', f'car_{k}.glb'))
        # the parked cars farther than 20 m (web/src/main.js): a fifth of the triangles. The 4 cm loft stations merged
        # where the panels bend less than 10 degrees (within each material, sharp edges kept: the windows, trims and
        # lamps stay as they were), the wheels collapsed to 40 %. Alike from 20 m on; at 15 m only the rims show it
        for o in objs:
            d = o.modifiers.new('far', 'DECIMATE')
            d.decimate_type = 'DISSOLVE'
            d.angle_limit = math.radians(10)
            d.delimit = {'MATERIAL', 'SHARP'}
            o.modifiers.new('tri', 'TRIANGULATE')
            if o is not body:
                c = o.modifiers.new('wheel', 'DECIMATE')
                c.decimate_type = 'COLLAPSE'
                c.ratio = 0.4
                c.use_collapse_triangulate = True
        export_glb(objs, os.path.join(OUT, 'props', f'car_{k}_far.glb'))

if want('polyhaven'):
    # CC0 Poly Haven props: decimate to game budgets, keep their own PBR textures (1k JPEG)
    PH = os.path.join(common.ROOT, 'assets_src', 'models')
    # (the bench and the bin are blender/props.py's now: the campus bench and green recycling box of the 2003 photos,
    # not this small red settle and the galvanised can)
    for name, src, ratio in (('payphone', 'korean_public_payphone_01', 0.06),):
        reset_scene()
        bpy.ops.import_scene.gltf(filepath=os.path.join(PH, src, f'{src}_1k.gltf'))
        objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        for o in objs:
            if ratio < 1:
                m = o.modifiers.new('dec', 'DECIMATE')
                m.ratio = ratio
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.convert(target='MESH')
        # normalise scale: payphone source is authored in cm
        bb = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
        hgt = max(v.z for v in bb) - min(v.z for v in bb)
        target = {'payphone': None}[name]
        if target and hgt > 0:
            s = target / hgt
            for o in objs:
                o.scale = (o.scale[0] * s, o.scale[1] * s, o.scale[2] * s)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        if name == 'payphone':
            # the phone at its real size (74 cm) hung on the back wall of a booth (95 x 95 cm, 2.2 m)
            bb = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
            cx_ = (max(v.x for v in bb) + min(v.x for v in bb)) / 2
            for o in objs:
                o.location = (o.location.x - cx_, o.location.y - max(v.y for v in bb) + 0.46, o.location.z - min(v.z for v in bb) + 0.92)
            bpy.ops.object.select_all(action='DESELECT')
            for o in objs:
                o.select_set(True)
            bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
            booth = props.payphone_booth().build()
            objs.append(booth)
            booth.select_set(True)
        for img in bpy.data.images:
            if img.size[0] > 512:
                img.scale(512, 512)
        stats[name] = tri_count(objs)
        path = os.path.join(OUT, 'props', f'{name}.glb')
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
                                  export_image_format='JPEG', export_jpeg_quality=85, export_draco_mesh_compression_enable=True)
        print('exported', path, os.path.getsize(path) // 1024, 'KB')

if BLEND:
    # One editable Blender scene of the whole 1997 campus (buildings + landmarks + 백양로 + terrain)
    import numpy as np
    reset_scene()
    rnd = random.Random(1997)
    for i, b in enumerate(CAMPUS['buildings']):
        ghost_draws(i, rnd)
        if b['style'].startswith('lm:'):
            continue
        generic.build_generic(b, rnd).build()
    for b in CAMPUS['buildings']:
        if b['style'].startswith('lm:'):
            for mb in landmarks.BUILDERS[b['style'][3:]]():
                mb.build()
    for mb in landmarks.amphitheater():
        mb.build()
    for m in road.build()[0]:
        m.build()
    H = np.load(os.path.join(common.ROOT, 'data', 'terrain_near.npy'))
    n = H.shape[0]
    half, step = CAMPUS['terrain']['near']['half'], CAMPUS['terrain']['near']['step']
    sub = range(40, n - 40)          # +-600 m around the campus
    verts = [(-half + i * step, -half + j * step, float(H[j, i])) for j in sub for i in sub]
    m = len(sub)
    faces = [(j * m + i, j * m + i + 1, (j + 1) * m + i + 1, (j + 1) * m + i) for j in range(m - 1) for i in range(m - 1)]
    me = bpy.data.meshes.new('terrain')
    me.from_pydata(verts, [], faces)
    me.materials.append(common.material('grass'))
    ob = bpy.data.objects.new('terrain', me)
    bpy.context.scene.collection.objects.link(ob)
    import preview
    preview.setup_world()
    path = os.path.join(common.ROOT, 'assets_src', 'yonsei1997_campus.blend')
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print('saved', path)

print('STATS', json.dumps(stats))
