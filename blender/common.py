"""Shared helpers for the Yonsei-1997 Blender asset pipeline (run inside Blender).

MeshBuilder collects faces in world (or local) coordinates with per-face material
names and metric box-projected UVs, then emits a single bpy object.  All exported
GLBs carry geometry + UVs + material *names*; the web app binds the real PBR
materials from blender/materials.json, so textures are shared across every model.
"""
import bpy, bmesh, json, math, os, random
import numpy as np
from mathutils import Vector, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEX = os.path.join(ROOT, 'assets_src', 'textures')
OUT = os.path.join(ROOT, 'web', 'public', 'assets', 'models')
MATS = json.load(open(os.path.join(ROOT, 'blender', 'materials.json')))
CAMPUS = json.load(open(os.path.join(ROOT, 'data', 'campus.json')))

# ----------------------------------------------------------------------------- terrain
_T = np.load(os.path.join(ROOT, 'data', 'terrain_near.npy'))
_TH = CAMPUS['terrain']['near']['half']
_TS = CAMPUS['terrain']['near']['step']


# the patch south of the grid (tools/sinchon_rotary.py SOUTH: 신촌 로터리), its own rows and columns
_SS = CAMPUS['terrain'].get('south')
_S = np.load(os.path.join(ROOT, 'data', 'terrain_south.npy')) if _SS else None


# the patch north of it (tools/muak.py NORTH: 무악학사 · 북문), its bottom row the grid's top row
_NS = CAMPUS['terrain'].get('north')
_N = np.load(os.path.join(ROOT, 'data', 'terrain_north.npy')) if _NS else None


def _grid(x, y):
    """the grid that holds (x, y), its frame, and the fractional cell"""
    if _S is not None and y < _SS['y0'] + (_SS['ny'] - 1) * _SS['step'] and _SS['x0'] <= x <= _SS['x0'] + (_SS['nx'] - 1) * _SS['step']:
        fx = min(max((x - _SS['x0']) / _SS['step'], 0), _S.shape[1] - 1.001)
        fy = min(max((y - _SS['y0']) / _SS['step'], 0), _S.shape[0] - 1.001)
        return _S, fx, fy
    if _N is not None and y > _NS['y0'] and _NS['x0'] <= x <= _NS['x0'] + (_NS['nx'] - 1) * _NS['step']:
        fx = min(max((x - _NS['x0']) / _NS['step'], 0), _N.shape[1] - 1.001)
        fy = min(max((y - _NS['y0']) / _NS['step'], 0), _N.shape[0] - 1.001)
        return _N, fx, fy
    fx = min(max((x + _TH) / _TS, 0), _T.shape[1] - 1.001)
    fy = min(max((y + _TH) / _TS, 0), _T.shape[0] - 1.001)
    return _T, fx, fy


# Raised surfaces that are meshes over the ground (tools/medwest97.py: campus.json `med_west` plates, 외래진료소's
# forecourt and ramps, 안 · 이비인후과병원's terrace): the ground on one is its surface, so that what a builder stands
# on the ground there (a door's flight, a car park's lines, a wall's lowest windows) stands on it.  Each plate: its
# outline and holes (campus metres), a table z over (us, vs) in the frame o, ang (bilinear, clamped)
_PLATES = []
_PB = None


def _plates_load():
    global _PB
    G = CAMPUS.get('med_west')
    if not G:
        return
    c, s = math.cos(math.radians(G['ang'])), math.sin(math.radians(G['ang']))
    for p in G['plates']:
        xs, ys = [q[0] for q in p['poly']], [q[1] for q in p['poly']]
        _PLATES.append((min(xs), min(ys), max(xs), max(ys), p['poly'], p.get('holes', []), G['o'], c, s, p['us'], p['vs'], p['z']))
    _PB = (min(p[0] for p in _PLATES), min(p[1] for p in _PLATES), max(p[2] for p in _PLATES), max(p[3] for p in _PLATES))


def _in_ring(x, y, ring):
    c = False
    n = len(ring)
    for k in range(n):
        (x0, y0), (x1, y1) = ring[k], ring[(k + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (x1 - x0) * (y - y0) / (y1 - y0):
            c = not c
    return c


def plate_z(x, y):
    """the highest raised surface at (x, y), or None"""
    if _PB is None or x < _PB[0] or x > _PB[2] or y < _PB[1] or y > _PB[3]:
        return None
    best = None
    for x0, y0, x1, y1, poly, holes, o, c, s, us, vs, Z in _PLATES:
        if x < x0 or x > x1 or y < y0 or y > y1 or not _in_ring(x, y, poly) or any(_in_ring(x, y, h) for h in holes):
            continue
        dx, dy = x - o[0], y - o[1]
        u, v = min(max(dx * c + dy * s, us[0]), us[-1]), min(max(-dx * s + dy * c, vs[0]), vs[-1])
        i = max(k for k in range(len(us) - 1) if us[k] <= u)
        j = max(k for k in range(len(vs) - 1) if vs[k] <= v)
        a, b = (u - us[i]) / (us[i + 1] - us[i]), (v - vs[j]) / (vs[j + 1] - vs[j])
        z = Z[j][i] * (1 - a) * (1 - b) + Z[j][i + 1] * a * (1 - b) + Z[j + 1][i] * (1 - a) * b + Z[j + 1][i + 1] * a * b
        best = z if best is None else max(best, z)
    return best


_plates_load()


def ground(x, y):
    _T, fx, fy = _grid(x, y)
    i, j = int(fx), int(fy)
    ax, ay = fx - i, fy - j
    z = float(_T[j, i] * (1 - ax) * (1 - ay) + _T[j, i + 1] * ax * (1 - ay)
              + _T[j + 1, i] * (1 - ax) * ay + _T[j + 1, i + 1] * ax * ay)
    pz = plate_z(x, y)
    return z if pz is None else max(z, pz)


def ground_top(x, y):
    """The higher of the bilinear height and the terrain the web app draws: each 5 m cell is two triangles split along
    (i+1, j)-(i, j+1) (web/src/terrain.js), which stand up to a few tens of cm over the bilinear surface on curved
    slopes.  What a flight's foot and a porch must clear so that the grass never comes up through the stone."""
    _T, fx, fy = _grid(x, y)
    i, j = int(fx), int(fy)
    ax, ay = fx - i, fy - j
    a, b, c, d = _T[j, i], _T[j, i + 1], _T[j + 1, i], _T[j + 1, i + 1]
    tri = a + (b - a) * ax + (c - a) * ay if ax + ay <= 1 else d + (c - d) * (1 - ax) + (b - d) * (1 - ay)
    return max(float(tri), ground(x, y))            # (ground: a raised surface's too, above)


# ----------------------------------------------------------------------------- scene
_matcache = {}


def reset_scene():
    _matcache.clear()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.objects):
        for b in list(c):
            c.remove(b)


_matcache = {}


def _principled(mat):
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    return nt, next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')


def material(name):
    """Blender preview material (textures + tint) for a library name."""
    if name in _matcache:
        return _matcache[name]
    d = MATS.get(name, {'color': [1, 0, 1]})
    mat = bpy.data.materials.new(name)
    nt, bsdf = _principled(mat)
    bsdf.inputs['Roughness'].default_value = d.get('rough', 0.8)
    bsdf.inputs['Metallic'].default_value = d.get('metal', 0.0)
    if 'tex' in d:
        folder = os.path.join(TEX, d['tex'])
        tc = nt.nodes.new('ShaderNodeTexCoord')
        mp = nt.nodes.new('ShaderNodeMapping')
        s = 1.0 / d.get('tile', 2.0)
        mp.inputs['Scale'].default_value = (s, s, s)
        nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(os.path.join(folder, 'diff.jpg'), check_existing=True)
        nt.links.new(mp.outputs['Vector'], img.inputs['Vector'])
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        if 'sat' in d:
            hs = nt.nodes.new('ShaderNodeHueSaturation')
            hs.inputs['Saturation'].default_value = d['sat']
            nt.links.new(img.outputs['Color'], hs.inputs['Color'])
            nt.links.new(hs.outputs['Color'], mix.inputs[6])
        else:
            nt.links.new(img.outputs['Color'], mix.inputs[6])
        mix.inputs[7].default_value = (*d.get('tint', [1, 1, 1]), 1)
        nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
        nor = os.path.join(folder, 'nor.jpg')
        if os.path.exists(nor):
            ni = nt.nodes.new('ShaderNodeTexImage')
            ni.image = bpy.data.images.load(nor, check_existing=True)
            ni.image.colorspace_settings.name = 'Non-Color'
            nt.links.new(mp.outputs['Vector'], ni.inputs['Vector'])
            nm = nt.nodes.new('ShaderNodeNormalMap')
            nm.inputs['Strength'].default_value = 0.8
            nt.links.new(ni.outputs['Color'], nm.inputs['Color'])
            nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    elif 'maps' in d:       # a baked statue (blender/sculpt.py): colour, normal and occlusion / roughness / metalness
        base = os.path.join(ROOT, 'web', 'public', 'assets', 'textures', d['maps'])
        if os.path.exists(base + '_col.jpg'):
            img = nt.nodes.new('ShaderNodeTexImage')
            img.image = bpy.data.images.load(base + '_col.jpg', check_existing=False)
            nt.links.new(img.outputs['Color'], bsdf.inputs['Base Color'])
            ni = nt.nodes.new('ShaderNodeTexImage')
            ni.image = bpy.data.images.load(base + '_nor.jpg', check_existing=False)
            ni.image.colorspace_settings.name = 'Non-Color'
            nm = nt.nodes.new('ShaderNodeNormalMap')
            nt.links.new(ni.outputs['Color'], nm.inputs['Color'])
            nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
            oi = nt.nodes.new('ShaderNodeTexImage')
            oi.image = bpy.data.images.load(base + '_orm.jpg', check_existing=False)
            oi.image.colorspace_settings.name = 'Non-Color'
            sep = nt.nodes.new('ShaderNodeSeparateColor')
            nt.links.new(oi.outputs['Color'], sep.inputs[0])
            nt.links.new(sep.outputs[1], bsdf.inputs['Roughness'])
            nt.links.new(sep.outputs[2], bsdf.inputs['Metallic'])
        else:
            bsdf.inputs['Base Color'].default_value = (*d.get('color', [0.08, 0.08, 0.07]), 1)
    elif 'leaf' in d:
        p = os.path.join(ROOT, 'web', 'public', 'assets', 'textures', f"leaf_{d['leaf']}.png")
        if os.path.exists(p):
            img = nt.nodes.new('ShaderNodeTexImage')
            img.image = bpy.data.images.load(p, check_existing=True)
            nt.links.new(img.outputs['Color'], bsdf.inputs['Base Color'])
            nt.links.new(img.outputs['Alpha'], bsdf.inputs['Alpha'])
            try:
                mat.surface_render_method = 'DITHERED'
            except Exception:
                pass
        else:
            bsdf.inputs['Base Color'].default_value = (0.2, 0.4, 0.1, 1)
    elif 'image' in d:
        p = os.path.join(ROOT, 'web', 'public', 'assets', 'textures', d['image'])
        if os.path.exists(p):
            img = nt.nodes.new('ShaderNodeTexImage')
            img.image = bpy.data.images.load(p, check_existing=True)
            nt.links.new(img.outputs['Color'], bsdf.inputs['Base Color'])
    else:
        c = d.get('color', [0.8, 0.8, 0.8])
        bsdf.inputs['Base Color'].default_value = (*c, 1)
        if 'emissive' in d:
            bsdf.inputs['Emission Color'].default_value = (*d['emissive'], 1)
            bsdf.inputs['Emission Strength'].default_value = d.get('emissiveIntensity', 1) * 3
    _matcache[name] = mat
    return mat


# ----------------------------------------------------------------------------- mesh builder
class MeshBuilder:
    def __init__(self, name):
        self.name = name
        self.verts = []
        self.vmap = {}
        self.faces = []        # (vert indices, mat, uvs or None, smooth)
        self.colors = None     # optional per-face-corner colour list aligned to faces
        self.fcols = []
        self.panes = {}        # face index -> pane hint for window glass (pane_uv)
        self.xf = Matrix.Identity(4)
        self.uv_rot = 0.0

    # -- vertices
    def _v(self, p, share):
        p = self.xf @ Vector(p)
        if share:
            k = (round(p.x, 4), round(p.y, 4), round(p.z, 4), share)
            if k in self.vmap:
                return self.vmap[k]
            self.vmap[k] = len(self.verts)
        self.verts.append(p)
        return len(self.verts) - 1

    def face(self, pts, mat, uvs=None, smooth=False, col=None, panes=None):
        """pts in local coords (transformed by self.xf). uvs optional list of (u,v).
        panes: window glass only, (cols, rows[, hall]) panes across the face (pane_uv)."""
        if len(pts) < 3:
            return
        share = smooth if isinstance(smooth, str) else ('s' if smooth else None)
        idx = [self._v(p, share) for p in pts]
        if len(set(idx)) < 3:
            return
        if panes:
            self.panes[len(self.faces)] = panes
        self.faces.append((idx, mat, uvs, bool(smooth)))
        self.fcols.append(col)

    def quad(self, a, b, c, d, mat, **kw):
        self.face([a, b, c, d], mat, **kw)

    def box(self, c, size, mat, rotz=0.0, mats=None, skip=()):
        """Axis box centred at c (x,y,z centre), size (sx,sy,sz); rotz radians.
        mats: optional dict side->mat for 'top','bottom','sides'. skip: sides to omit."""
        sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
        cs, sn = math.cos(rotz), math.sin(rotz)

        def P(x, y, z):
            return (c[0] + x * cs - y * sn, c[1] + x * sn + y * cs, c[2] + z)
        v = [P(-sx, -sy, -sz), P(sx, -sy, -sz), P(sx, sy, -sz), P(-sx, sy, -sz),
             P(-sx, -sy, sz), P(sx, -sy, sz), P(sx, sy, sz), P(-sx, sy, sz)]
        m = mats or {}
        sides = {'bottom': [0, 3, 2, 1], 'top': [4, 5, 6, 7], 'front': [0, 1, 5, 4],
                 'right': [1, 2, 6, 5], 'back': [2, 3, 7, 6], 'left': [3, 0, 4, 7]}
        for k, ids in sides.items():
            if k in skip:
                continue
            mm = m.get(k) or (m.get('sides') if k not in ('top', 'bottom') else None) or mat
            self.face([v[i] for i in ids], mm)

    def prism(self, poly, z0, z1, mat_side, mat_top=None, mat_bottom=None, smooth=False):
        """Extrude CCW 2D polygon from z0 to z1."""
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            self.face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat_side,
                      smooth=('prism' if smooth else False))
        if mat_top:
            self.face([(p[0], p[1], z1) for p in poly], mat_top)
        if mat_bottom:
            self.face([(p[0], p[1], z0) for p in reversed(poly)], mat_bottom)

    def cylinder(self, c, r, z0, z1, mat, seg=16, cap_top=True, cap_bot=False, r1=None, mat_cap=None, smooth=True):
        r1 = r if r1 is None else r1
        pts0 = [(c[0] + r * math.cos(2 * math.pi * i / seg), c[1] + r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
        pts1 = [(c[0] + r1 * math.cos(2 * math.pi * i / seg), c[1] + r1 * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
        tag = 'cyl%d' % len(self.faces) if smooth else False
        for i in range(seg):
            j = (i + 1) % seg
            u0, u1 = i / seg * 2 * math.pi * r, (i + 1) / seg * 2 * math.pi * r
            v0, v1 = z0 + _odz(z0), z1 + _odz(z0)
            self.face([(*pts0[i], z0), (*pts0[j], z0), (*pts1[j], z1), (*pts1[i], z1)], mat,
                      uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)], smooth=tag)
        if cap_top:
            self.face([(*p, z1) for p in pts1], mat_cap or mat)
        if cap_bot:
            self.face([(*p, z0) for p in reversed(pts0)], mat_cap or mat)

    def sphere(self, c, r, mat, seg=12, rings=8, sz=1.0, smooth=True):
        tag = 'sph%d' % len(self.faces) if smooth else False
        P = []
        for j in range(rings + 1):
            th = math.pi * j / rings
            row = []
            for i in range(seg):
                ph = 2 * math.pi * i / seg
                row.append((c[0] + r * math.sin(th) * math.cos(ph), c[1] + r * math.sin(th) * math.sin(ph), c[2] + r * sz * math.cos(th)))
            P.append(row)
        for j in range(rings):
            for i in range(seg):
                k = (i + 1) % seg
                self.face([P[j][i], P[j + 1][i], P[j + 1][k], P[j][k]], mat, smooth=tag)

    # -- output
    def build(self, collection=None):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata([tuple(v) for v in self.verts], [], [f[0] for f in self.faces])
        mats = []
        for f in self.faces:
            if f[1] not in mats:
                mats.append(f[1])
        for m in mats:
            me.materials.append(material(m))
        uvl = me.uv_layers.new(name='UVMap')
        _UV_DZ[0] = HASH_DZ if self.verts and min(v.z for v in self.verts) > 5.0 else 0.0
        has_col = any(c is not None for c in self.fcols)
        if has_col:
            ca = me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
        li = 0
        for pi, (f, poly) in enumerate(zip(self.faces, me.polygons)):
            idx, mat, uvs, smooth = f
            poly.material_index = mats.index(mat)
            poly.use_smooth = smooth
            if uvs is None:
                pts = [self.verts[i] for i in idx]
                uvs = pane_uv(pts, self.panes.get(pi)) if mat in ROOM_GLASS else auto_uv(pts)
                if MATS.get(mat, {}).get('uv') == 'swap':          # a texture laid a quarter turned
                    uvs = [(b, a) for a, b in uvs]
            for k, li_ in enumerate(poly.loop_indices):
                uvl.data[li_].uv = uvs[k]
                if has_col:
                    c = self.fcols[pi]
                    if c is None:
                        c = (1, 1, 1, 1)
                    elif isinstance(c[0], (tuple, list)):
                        c = c[k]
                    ca.data[li_].color = (c[0], c[1], c[2], c[3] if len(c) > 3 else 1)
        me.validate(clean_customdata=False)
        me.update()
        ob = bpy.data.objects.new(self.name, me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        return ob


def auto_uv(pts):
    """Metric box projection: walls use (along-wall, z), floors/roofs use (x, y)."""
    a, b, c = Vector(pts[0]), Vector(pts[1]), Vector(pts[2])
    n = (b - a).cross(c - a)
    if n.length < 1e-9 and len(pts) > 3:
        n = (Vector(pts[2]) - a).cross(Vector(pts[3]) - a)
    n = n.normalized() if n.length > 0 else Vector((0, 0, 1))
    if abs(n.z) > 0.72:
        return [(p[0], p[1]) for p in pts]
    t = Vector((-n.y, n.x, 0))
    t = t.normalized() if t.length > 1e-6 else Vector((1, 0, 0))
    if abs(n.z) > 0.25:      # sloped roof: v follows the slope
        bt = n.cross(t).normalized()
        return [(Vector(p).dot(t), Vector((p[0], p[1], p[2] + _UV_DZ[0])).dot(bt)) for p in pts]
    return [(Vector(p).dot(t), p[2] + _UV_DZ[0]) for p in pts]   # (z on the old datum: the textures lie as they did)


# Window glass gets pane UVs instead of metric ones, so that every window shows a different room: u and v count the
# panes across the face (a whole number per pane, 0..1 across it) from a pseudo-random whole-number offset per face.
# The web app's glass shader (web/src/materials.js windowGlass) picks a cell of its room atlas from the whole part and
# spreads it over the fraction.  v from HALL up: a hall (lobby, stair hall) behind tall glazing instead of a room.
ROOM_GLASS = tuple(k for k, d in MATS.items() if isinstance(d, dict) and 'rooms' in d)     # glass, glass_green, ...
HALL = 32
# u from SASH: a sash window (an ordinary window of a generic hall, blender/windows.py; the shader takes u - SASH mod 24
# to pick its room, so the rooms stay those of the plain offset).  One in OPEN_P of them has a sash slid open: the
# shader takes the glass off one half of the pane under the transom (fraction of v < TRANSOM) and windows.py sets that
# part back into the room.  Both pick the window and the half by pane_open: the same hash of the pane's whole-number
# uv as the shader's paneHash.  v < 0: a dark opening with no glass and no room (an air conditioner's fan).
SASH = 64
OPEN_P = 0.07
TRANSOM = 0.715


def pane_hash(px, py, k):
    """web/src/materials.js paneHash: 0..1 from a pane's whole-number uv and a key"""
    M = 0xffffffff
    n = ((px + 4096) * 1973 + (py + 4096) * 9277 + k * 26699) & M
    n ^= n >> 16
    n = n * 0x7feb352d & M
    n ^= n >> 15
    n = n * 0x846ca68b & M
    n ^= n >> 16
    return (n >> 8) / 16777216.0


def pane_open(px, py):
    """None, or the half of the sash window at pane (px, py) whose sash is slid open: 0 left, 1 right (seen from out)"""
    if px < SASH or py >= HALL or pane_hash(px, py, 7) >= OPEN_P:
        return None
    return 0 if pane_hash(px, py, 8) < 0.5 else 1


def pane_cell(pts, panes=None):
    """the whole-number uv (ox, oy) pane_uv gives the first pane of this face"""
    return _pane_frame(pts, panes)[-2:]


def pane_uv(pts, panes=None):
    """panes: (cols, rows[, hall[, sash]]) or None -> panes about a window bay wide and a storey tall"""
    sz, s0, z0, W, H, cols, rows, ox, oy = _pane_frame(pts, panes)
    e = 0.02                                   # keep off the whole numbers (Draco quantises the UVs)
    return [(ox + e + (s - s0) / W * (cols - 2 * e), oy + e + (z - z0) / H * (rows - 2 * e)) for s, z in sz]


# The metric uvs and the window hashes read z on the datum they were drawn on before 2026-11-15, 2.0 m over today's
# sea-level one (tools/build_campus.py SURFACE_DZ), so that every texture and window lies as it did: in a mesh laid in
# campus coordinates (MeshBuilder.build: its lowest vertex over 5 m; _odz for a single height over 8 m), not in one
# built round its own origin (props, statues), whose z never moved
HASH_DZ = 2.0
_UV_DZ = [0.0]


def _odz(z):
    return HASH_DZ if z > 8.0 else 0.0


def _pane_frame(pts, panes):
    a, b, c = Vector(pts[0]), Vector(pts[1]), Vector(pts[2])
    n = (b - a).cross(c - a)
    if n.length < 1e-9 and len(pts) > 3:
        n = (Vector(pts[2]) - a).cross(Vector(pts[3]) - a)
    n = n.normalized() if n.length > 0 else Vector((0, 0, 1))
    flat = abs(n.z) > 0.72
    if flat:                                   # a skylight: x, y
        sz = [(p[0], p[1]) for p in pts]
    else:                                      # along the wall (to the right seen from outside), up the slope
        t = Vector((-n.y, n.x, 0)).normalized()
        bt = n.cross(t).normalized()
        sz = [(Vector(p).dot(t), Vector(p).dot(bt)) for p in pts]
    s0, s1 = min(p[0] for p in sz), max(p[0] for p in sz)
    z0, z1 = min(p[1] for p in sz), max(p[1] for p in sz)
    W, H = max(s1 - s0, 1e-3), max(z1 - z0, 1e-3)
    if panes:
        cols, rows = panes[0], panes[1]
        hall = panes[2] if len(panes) > 2 else H / rows > 3.0
    else:
        cols, rows = max(1, round(W / 3.4)), max(1, round(H / 3.6))
        hall = flat or H / rows > 3.0 or W / cols > 4.5
    # the same window gets the same rooms in every build: hashed on its corners as the single-precision vertices they
    # were on the old datum (a campus-coordinate z rounded back to its decimals; m.z * 50 often falls on a half)
    m = sum((Vector((p[0], p[1], round(p[2] + HASH_DZ, 4) if p[2] > 8.0 else p[2])) for p in pts), Vector()) / len(pts)
    h = (int(round(m.x * 50)) * 73856093) ^ (int(round(m.y * 50)) * 19349663) ^ (int(round(m.z * 50)) * 83492791)
    h = (h ^ (h >> 13)) * 1274126177 & 0xffffffff
    ox, oy = h % 24, (h >> 8) % 16 + (HALL if hall else 0)
    if panes and len(panes) > 3 and panes[3] and not hall:
        ox += SASH + 24 * ((h >> 20) % 4)      # (four times the panes for pane_open to choose from)
    return sz, s0, z0, W, H, cols, rows, ox, oy


# ----------------------------------------------------------------------------- 2D geometry
def poly_area(poly):
    a = 0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        a += x1 * y2 - x2 * y1
    return a / 2


def offset_poly(poly, d):
    """Miter offset of a CCW polygon (d>0 outward)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector((*poly[i - 1], 0)), Vector((*poly[i], 0)), Vector((*poly[(i + 1) % n], 0))
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((e0.y, -e0.x, 0))
        n1 = Vector((e1.y, -e1.x, 0))
        m = (n0 + n1)
        if m.length < 1e-6:
            m = n0
        m.normalize()
        cosang = max(0.35, m.dot(n1))
        q = p1 + m * (d / cosang)
        out.append((q.x, q.y))
    return out


def min_area_rect(poly):
    """Oriented bounding box -> (cx, cy, length, width, angle) ; length along angle."""
    best = None
    pts = [Vector(p) for p in poly]
    for i in range(len(pts)):
        e = pts[(i + 1) % len(pts)] - pts[i]
        if e.length < 1e-3:
            continue
        ang = math.atan2(e.y, e.x)
        c, s = math.cos(-ang), math.sin(-ang)
        xs = [p.x * c - p.y * s for p in pts]
        ys = [p.x * s + p.y * c for p in pts]
        area = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if best is None or area < best[0]:
            mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
            cx = mx * math.cos(ang) - my * math.sin(ang)
            cy = mx * math.sin(ang) + my * math.cos(ang)
            best = (area, cx, cy, max(xs) - min(xs), max(ys) - min(ys), ang)
    _, cx, cy, L, W, ang = best
    if W > L:
        L, W, ang = W, L, ang + math.pi / 2
    return cx, cy, L, W, ang


def local_frame(cx, cy, ang, z=0.0):
    return Matrix.Translation((cx, cy, z)) @ Matrix.Rotation(ang, 4, 'Z')


# ----------------------------------------------------------------------------- export
def export_glb(objs, path, draco=True, colors=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
              export_image_format='NONE', export_yup=True, export_materials='EXPORT',
              export_draco_mesh_compression_enable=draco, export_draco_mesh_compression_level=6,
              export_draco_position_quantization=16, export_draco_texcoord_quantization=14,
              export_extras=True)
    try:
        kw['export_vertex_color'] = 'ACTIVE' if colors else 'NONE'
    except Exception:
        pass
    if colors:      # the halls' `_edge` (blender/bake.py): Draco keeps 16 bits of it, 2 mm over EDGE_RANGE
        kw.update(export_attributes=True, export_draco_generic_quantization=16)
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        for k in ('export_vertex_color', 'export_attributes', 'export_draco_generic_quantization'):
            kw.pop(k, None)
        bpy.ops.export_scene.gltf(**kw)
    print('exported', path, os.path.getsize(path) // 1024, 'KB')


def tri_count(objs):
    n = 0
    for o in objs:
        for p in o.data.polygons:
            n += len(p.vertices) - 2
    return n
