"""Sculpted bronzes: a dense sculpt baked onto a light mesh (blender/statues.py, `blender/build.py -- statues`).

A statue is first built as a dense sculpt (overlapping solids joined on a voxel grid, then pushed about: folds, the
marks of the modelling clay, feathers).  The game draws a light mesh of some ten thousand triangles instead, with the
sculpt's relief in a normal map and the bronze's weathering - verdigris where the rain stands and runs, soot in the
hollows, bare metal on the worn ridges - in a colour and an occlusion / roughness / metalness map:

    web/public/assets/textures/statues/<name>_col.jpg   colour (sRGB)
                                       <name>_nor.jpg   tangent-space normal (OpenGL, as glTF)
                                       <name>_orm.jpg   R occlusion, G roughness, B metalness (as glTF)
    data/statues/<name>.npz                             the light mesh: verts, tris, a UV per corner

The sculpt and the bake take a minute or two per statue, so they run only on `blender/build.py -- statues`; the
landmarks build reads the light mesh back (`load`) and binds the material `bronze_<name>` (blender/materials.json
`maps`).  Both are written together: after changing a sculpt, run `-- statues` and then `-- landmarks`.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Vector

from common import ROOT, material

TEX_DIR = os.path.join(ROOT, 'web', 'public', 'assets', 'textures', 'statues')
MESH_DIR = os.path.join(ROOT, 'data', 'statues')


# ----------------------------------------------------------------------------- mesh access
def co(ob):
    a = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get('co', a)
    return a.reshape(-1, 3)


def set_co(ob, a):
    ob.data.vertices.foreach_set('co', np.ascontiguousarray(a, np.float32).ravel())
    ob.data.update()


def normals(ob):
    a = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get('normal', a)
    return a.reshape(-1, 3)


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def apply_modifiers(ob):
    """Bake the object's modifiers into its mesh, in place."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    return ob


def smooth_shade(ob):
    ob.data.polygons.foreach_set('use_smooth', np.ones(len(ob.data.polygons), bool))
    ob.data.update()


def join(objs, name):
    """Join objects into one (their transforms applied)."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return ob


# ----------------------------------------------------------------------------- sculpting
def union(objs, voxel, smooth=0, factor=0.5, name='sculpt'):
    """The union of closed solids on a voxel grid: one watertight skin, the creases where they meet smoothed
    `smooth` times.  Gaps narrower than a voxel close, walls thinner than one vanish."""
    ob = join(list(objs), name)
    m = ob.modifiers.new('rm', 'REMESH')
    m.mode = 'VOXEL'
    m.voxel_size = voxel
    m.adaptivity = 0.0
    if smooth:
        s = ob.modifiers.new('sm', 'SMOOTH')
        s.factor = factor
        s.iterations = smooth
    apply_modifiers(ob)
    smooth_shade(ob)
    return ob


def smooth(ob, iterations=4, factor=0.5, weights=None):
    """Relax the surface; `weights` (per vertex, 0..1) keeps parts of it sharp."""
    m = ob.modifiers.new('sm', 'SMOOTH')
    m.factor = factor
    m.iterations = iterations
    if weights is not None:
        g = ob.vertex_groups.new(name='smooth_w')
        for i in np.nonzero(weights > 0.01)[0]:
            g.add([int(i)], float(weights[i]), 'REPLACE')
        m.vertex_group = g.name
    apply_modifiers(ob)
    return ob


def clay(ob, amp=0.004, scale=0.06, depth=2, seed=0, mask=None):
    """The marks of the modelling: push the surface in and out along its normals by a cloud noise of wavelength
    `scale` (m) and amplitude `amp` (m).  `mask` (per vertex, 0..1) spares what must stay crisp."""
    from mathutils import noise
    P = co(ob)
    N = normals(ob)
    # (a lattice of noise samples, read trilinearly: a million vertices in a second)
    lo, hi = P.min(0) - scale, P.max(0) + scale
    step = scale / 3.0
    n = np.maximum(((hi - lo) / step).astype(int) + 2, 2)
    off = Vector((seed * 13.7, seed * 7.1, seed * 3.3))
    G = np.empty(tuple(n), np.float32)
    for i in range(n[0]):
        for j in range(n[1]):
            for k in range(n[2]):
                p = Vector((lo[0] + i * step, lo[1] + j * step, lo[2] + k * step)) / scale + off
                G[i, j, k] = noise.fractal(p, 1.0, 2.0, depth)
    f = (P - lo) / step
    i0 = np.clip(f.astype(int), 0, n - 2)
    t = f - i0
    d = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (t[:, 0] if dx else 1 - t[:, 0]) * (t[:, 1] if dy else 1 - t[:, 1]) * (t[:, 2] if dz else 1 - t[:, 2])
                d = d + w * G[i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz]
    d = d * amp
    if mask is not None:
        d = d * mask
    set_co(ob, P + N * d[:, None])
    return ob


def _seg_dist(P, A, B):
    """Distance from points P (n, 3) to the nearest of the segments A[k]-B[k], and how far along the polyline (0..1)."""
    best = np.full(len(P), 1e9, np.float32)
    along = np.zeros(len(P), np.float32)
    L = np.linalg.norm(B - A, axis=1)
    cum = np.concatenate([[0], np.cumsum(L)])
    tot = max(cum[-1], 1e-9)
    for k in range(len(A)):
        ab = B[k] - A[k]
        t = np.clip(((P - A[k]) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        d = np.linalg.norm(P - (A[k] + t[:, None] * ab), axis=1)
        m = d < best
        best[m] = d[m]
        along[m] = (cum[k] + t[m] * L[k]) / tot
    return best, along


def strokes(ob, S, facing=None):
    """Sculpt ridges and furrows: each stroke (points, width, height[, taper]) raises (height > 0) or presses in the
    surface along the polyline `points` with a round profile `width` wide at half height, fading to nothing at both
    ends (taper = (t0, t1): the shares of its length over which it fades in and out; default (0.25, 0.25)).  Folds of
    cloth, the shafts of feathers, the lines of a face.  The surface moves along its own normals, as they were before
    the first stroke.  `facing` = (direction, cos): only vertices whose normal lies within that cone move."""
    P = co(ob)
    N = normals(ob).copy()
    D = np.zeros(len(P), np.float32)
    ok = None
    if facing is not None:
        ok = N @ np.asarray(facing[0], np.float32) > facing[1]
    for s in S:
        pts, width, height = np.asarray(s[0], np.float32), s[1], s[2]
        t0, t1 = s[3] if len(s) > 3 else (0.25, 0.25)
        r = width * 1.6
        box = np.all((P > pts.min(0) - r) & (P < pts.max(0) + r), axis=1)
        if ok is not None:
            box &= ok
        idx = np.nonzero(box)[0]
        if not len(idx):
            continue
        d, a = _seg_dist(P[idx], pts[:-1], pts[1:])
        prof = np.exp(-(d / (width * 0.6)) ** 2)
        fade = np.ones_like(a)
        if t0 > 0:
            fade = np.minimum(fade, np.clip(a / t0, 0, 1))
        if t1 > 0:
            fade = np.minimum(fade, np.clip((1 - a) / t1, 0, 1))
        fade = fade * fade * (3 - 2 * fade)
        D[idx] += height * prof * fade
    set_co(ob, P + N * D[:, None])
    return ob


def push(ob, centre, radius, offset, falloff=2.0):
    """Move the surface near `centre` by the vector `offset`, fading to nothing at `radius` (a grab brush)."""
    P = co(ob)
    d = np.linalg.norm(P - np.asarray(centre, np.float32), axis=1) / radius
    w = np.clip(1 - d * d, 0, 1) ** falloff
    set_co(ob, P + w[:, None] * np.asarray(offset, np.float32))
    return ob


def inflate(ob, centre, radius, amount, falloff=2.0):
    """Swell (amount > 0) or sink the surface near `centre` along its normals."""
    P = co(ob)
    N = normals(ob)
    d = np.linalg.norm(P - np.asarray(centre, np.float32), axis=1) / radius
    w = np.clip(1 - d * d, 0, 1) ** falloff
    set_co(ob, P + N * (w * amount)[:, None])
    return ob


# ----------------------------------------------------------------------------- the light mesh
def lowpoly(high, tris, name='low', planar=0.0):
    """A light copy of the sculpt: collapsed to about `tris` triangles, smooth-shaded, triangulated."""
    low = high.copy()
    low.data = high.data.copy()
    low.name = name
    bpy.context.scene.collection.objects.link(low)
    m = low.modifiers.new('dec', 'DECIMATE')
    m.ratio = min(1.0, tris / max(tri_count(low), 1))
    t = low.modifiers.new('tri', 'TRIANGULATE')
    apply_modifiers(low)
    smooth_shade(low)
    return low


def unwrap(low, angle=66.0, margin=0.004):
    """Lay the light mesh out in the unit square (Smart UV Project: islands by face angle)."""
    bpy.ops.object.select_all(action='DESELECT')
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    if not low.data.uv_layers:
        low.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return low


# ----------------------------------------------------------------------------- baking
def _mask_material(which):
    """An emitter over the sculpt that writes what the weathering is made from.
    0: R how pointed the surface is (0.5 flat, above on ridges, below in hollows), G how far it faces the sky
       (0 down .. 1 up), B a broad cloud noise
    1: R a noise drawn out downwards (where the rain runs), G a fine grain, B height (0 at the lowest point .. 1)"""
    mat = bpy.data.materials.new('sculpt_mask%d' % which)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    comb = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(comb.outputs[0], em.inputs['Color'])

    def noise(scale, detail, stretch=(1, 1, 1)):
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = stretch
        nt.links.new(geo.outputs['Position'], mp.inputs['Vector'])
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = scale
        nz.inputs['Detail'].default_value = detail
        nt.links.new(mp.outputs[0], nz.inputs['Vector'])
        return nz.outputs[0]                                   # (Fac)

    if which == 0:
        nt.links.new(geo.outputs['Pointiness'], comb.inputs[0])
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(geo.outputs['Normal'], sep.inputs[0])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = -1, 1
        nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
        nt.links.new(mr.outputs[0], comb.inputs[1])
        nt.links.new(noise(2.2, 5), comb.inputs[2])
    else:
        nt.links.new(noise(22.0, 3, (1, 1, 0.06)), comb.inputs[0])
        nt.links.new(noise(60.0, 2), comb.inputs[1])
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(geo.outputs['Position'], sep.inputs[0])
        nt.links.new(sep.outputs['Z'], comb.inputs[2])
    return mat


# the weathering of a bronze out of doors, from the baked masks (all in linear colour)
LOOK = dict(
    base=(0.060, 0.052, 0.040),     # the dark brown-olive skin of old bronze
    soot=(0.012, 0.012, 0.011),     # in the hollows
    green=(0.20, 0.30, 0.25),       # verdigris
    bare=(0.30, 0.20, 0.09),        # metal rubbed bare on the ridges
    verdigris=0.5,                  # how green: 0 none .. 1 over most of what faces the sky
    wear=0.5,                       # how much bare metal on the ridges
    rough=(0.42, 0.85, 0.30),       # roughness of the skin, the verdigris, the bare metal
    metal=(0.75, 0.10, 1.0),        # metalness of the same
)


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def weather(ao, m0, m1, look, cover=None):
    """Colour and occlusion / roughness / metalness from the baked masks (float arrays h x w [x 3])."""
    L = dict(LOOK, **(look or {}))
    point, up, cloud = m0[..., 0], m0[..., 1], m0[..., 2]
    run, grain, height = m1[..., 0], m1[..., 1], m1[..., 2]
    # (pointiness is 0.5 on a flat surface and strays from it by an amount that depends on the mesh: in units of
    # its own spread)
    sel = point[cover] if cover is not None and cover.any() else point
    point = (point - np.median(sel)) / max(float(sel.std()), 1e-6)
    ridge = _smoothstep(0.8, 2.5, point)                         # worn edges
    hollow = _smoothstep(-0.8, -2.5, point)                      # creases
    shade = 1 - ao                                               # sheltered places
    # verdigris: on what faces the sky and in streaks below it, broken by the clouds; less where sheltered from
    # the rain; it also gathers in the creases
    k = L['verdigris']
    wet = _smoothstep(0.55, 0.95, up) * 0.9 + _smoothstep(0.35, 0.7, up) * _smoothstep(0.45, 0.7, run) * 0.6
    wet = wet * (0.55 + 0.9 * (cloud - 0.5)) + 0.5 * hollow * _smoothstep(0.3, 0.6, cloud)
    wet = wet * (1 - 0.7 * _smoothstep(0.25, 0.6, shade))
    green = np.clip(_smoothstep(0.5 - 0.45 * k, 1.0 - 0.5 * k, wet + 0.25 * (grain - 0.5)), 0, 1) * min(1.0, 2 * k)
    soot = np.clip(_smoothstep(0.15, 0.6, shade) * 0.8 + hollow * 0.5, 0, 1) * (1 - green)
    bare = ridge * L['wear'] * (1 - green) * (1 - 0.6 * soot) * (0.6 + 0.8 * (grain - 0.5) + 0.4 * _smoothstep(0.3, 0.9, up))
    bare = np.clip(bare, 0, 1)
    tone = 1 + 0.5 * (cloud - 0.5) + 0.3 * (grain - 0.5)         # the skin is never one colour
    col = np.asarray(L['base'], np.float32)[None, None] * tone[..., None]
    for w, c in ((soot, L['soot']), (green, L['green']), (bare, L['bare'])):
        col = col * (1 - w[..., None]) + np.asarray(c, np.float32)[None, None] * w[..., None]
    rb, rg, rw = L['rough']
    mb, mg, mw = L['metal']
    rough = rb + 0.15 * soot
    metal = np.full_like(rough, mb)
    rough = rough * (1 - green) + rg * green
    metal = metal * (1 - green) + mg * green
    rough = rough * (1 - bare) + rw * bare
    metal = metal * (1 - bare) + mw * bare
    rough = np.clip(rough + 0.12 * (grain - 0.5), 0.05, 1)
    orm = np.stack([np.clip(0.35 + 0.65 * ao, 0, 1), rough, np.clip(metal, 0, 1)], axis=-1)
    return col, orm


def _save(arr, path, srgb):
    """Write a float array (h x w x 3, bottom row first as Blender keeps it) as a JPEG."""
    h, w = arr.shape[:2]
    a = np.clip(arr, 0, 1).astype(np.float32)
    if srgb:
        a = np.where(a <= 0.0031308, a * 12.92, 1.055 * np.power(a, 1 / 2.4) - 0.055)
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = a
    img.pixels.foreach_set(px.ravel())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc = bpy.context.scene
    s = sc.render.image_settings
    old = (s.file_format, s.quality, s.color_mode)
    s.file_format, s.quality, s.color_mode = 'JPEG', 93, 'RGB'
    vt, look = sc.view_settings.view_transform, sc.view_settings.look
    sc.view_settings.view_transform = 'Standard'
    try:
        sc.view_settings.look = 'None'
    except Exception:
        pass
    img.save_render(path, scene=sc)
    s.file_format, s.quality, s.color_mode = old
    sc.view_settings.view_transform = vt
    try:
        sc.view_settings.look = look
    except Exception:
        pass
    bpy.data.images.remove(img)


def bake(high, low, name, size=1024, extrude=0.03, ray=0.08, ao_dist=0.6, ao_samples=64, look=None, keep=None):
    """Bake the sculpt (`high`: one object or several) onto the unwrapped light mesh `low`, and write the three maps of
    `name`.  extrude / ray: how far outside the light mesh the rays start and how far in they look for the sculpt (m).
    `keep`: a dict that receives the raw masks (for look development without baking again)."""
    highs = list(high) if isinstance(high, (list, tuple)) else [high]
    sc = bpy.context.scene
    engine = sc.render.engine
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = False
    if sc.world is None:
        sc.world = bpy.data.worlds.new('World')
    sc.world.light_settings.distance = ao_dist
    img = bpy.data.images.new(name + '_bake', size, size, alpha=True, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    mat = bpy.data.materials.new('sculpt_bake_target')
    try:
        mat.use_nodes = True
    except Exception:
        pass
    node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = img
    mat.node_tree.nodes.active = node
    low.data.materials.clear()
    low.data.materials.append(mat)
    for p in low.data.polygons:
        p.material_index = 0
    bpy.ops.object.select_all(action='DESELECT')
    for h in highs:
        h.hide_render = False
        h.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low

    def run(kind, samples=1, **kw):
        sc.cycles.samples = samples
        bpy.ops.object.bake(type=kind, use_selected_to_active=True, cage_extrusion=extrude, max_ray_distance=ray,
                            margin=16, use_clear=True, **kw)
        a = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(a)
        return a.reshape(size, size, 4).copy()

    def mats(m):
        for h in highs:
            h.data.materials.clear()
            h.data.materials.append(m)
            h.data.polygons.foreach_set('material_index', np.zeros(len(h.data.polygons), np.int32))

    mats(_mask_material(0))
    nor = run('NORMAL', normal_space='TANGENT')
    ao = run('AO', samples=ao_samples)
    m0 = run('EMIT')
    mats(_mask_material(1))
    m1 = run('EMIT')
    cover = nor[..., :3].sum(-1) > 0.05          # (cleared texels are black; a normal never is)
    zs = np.concatenate([co(h)[:, 2] for h in highs])
    m1[..., 2] = (m1[..., 2] - zs.min()) / max(zs.max() - zs.min(), 1e-6)
    if keep is not None:
        keep.update(nor=nor, ao=ao, m0=m0, m1=m1, cover=cover)
    write_maps(name, nor, ao, m0, m1, cover, look)
    bpy.data.images.remove(img)
    sc.render.engine = engine
    low.data.materials.clear()
    low.data.materials.append(material('bronze_' + name))
    return low


def write_maps(name, nor, ao, m0, m1, cover, look=None):
    col, orm = weather(ao[..., 0], m0[..., :3], m1[..., :3], look, cover)
    n = nor[..., :3].copy()
    for a, fill in ((col, col[cover].mean(0) if cover.any() else 0.1), (orm, (1, 0.6, 0.5)), (n, (0.5, 0.5, 1.0))):
        a[~cover] = fill                       # (outside the islands: a neutral value for the small mip levels)
    _save(col, os.path.join(TEX_DIR, name + '_col.jpg'), True)
    _save(n, os.path.join(TEX_DIR, name + '_nor.jpg'), False)
    _save(orm, os.path.join(TEX_DIR, name + '_orm.jpg'), False)
    print('sculpt: wrote', os.path.join(TEX_DIR, name + '_{col,nor,orm}.jpg'))


# ----------------------------------------------------------------------------- the cache
def save(low, name):
    me = low.data
    V = co(low)
    T = np.empty(len(me.polygons) * 3, np.int32)
    me.polygons.foreach_get('vertices', T)
    UV = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get('uv', UV)
    os.makedirs(MESH_DIR, exist_ok=True)
    p = os.path.join(MESH_DIR, name + '.npz')
    np.savez_compressed(p, verts=V, tris=T.reshape(-1, 3), uv=np.round(UV.reshape(-1, 2), 5))
    print('sculpt: wrote', p, len(V), 'verts', len(T) // 3, 'tris', os.path.getsize(p) // 1024, 'KB')


def load(name):
    """The light mesh of `name` as a new object with its material (`bronze_<name>`)."""
    d = np.load(os.path.join(MESH_DIR, name + '.npz'))
    V, T, UV = d['verts'], d['tris'], d['uv']
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set('co', V.astype(np.float32).ravel())
    me.loops.add(T.size)
    me.loops.foreach_set('vertex_index', T.astype(np.int32).ravel())
    me.polygons.add(len(T))
    me.polygons.foreach_set('loop_start', np.arange(0, T.size, 3, dtype=np.int32))
    me.polygons.foreach_set('loop_total', np.full(len(T), 3, np.int32))
    me.polygons.foreach_set('use_smooth', np.ones(len(T), bool))
    me.update(calc_edges=True)
    uv = me.uv_layers.new(name='UVMap')
    uv.data.foreach_set('uv', UV.astype(np.float32).ravel())
    me.materials.append(material('bronze_' + name))
    me.validate()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob
