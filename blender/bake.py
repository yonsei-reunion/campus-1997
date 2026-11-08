"""Per-corner shading data for the halls and landmarks, read by web/src/materials.js (MaterialLibrary.baked).

One float colour attribute, exported as COLOR_0:
  R  ambient occlusion: how much of the hemisphere over the surface the buildings leave open within AO_DIST (a
     Cycles bake).  Only buildings occlude: the open ground already lights the walls through the hemisphere light's
     ground colour (web/src/main.js), and counting the terrain would darken the lower storeys of every wall.  A face
     looking down (a soffit, the ceiling of a pilotis or a porch) does see the ground under it close by, in the
     building's own shade: that share is added from its height over the terrain.
  G  depth under the ledge above (a sill, a coping, a band) in fade lengths, / D_RANGE   } rain streaks running
  B  position along that ledge, -1..1 under it, (u + U_RANGE) / (2 U_RANGE)             } down from the ledge, over
                                                                                         } the faces below it to
                                                                                         } the next opening
  A  the sun's light on the face's side towards the sun (the fixed sun of web/public/data/sky.json): 1 sunlit, 0 in
     the shadow of a hall or landmark (these and the other GLB's) or, partly, of a tree's crown.  Rays cast to the
     sun; the phones' only sun shadow above the ground (web/src/bakedshadow.js), the desktop draws its shadow map.
White (1, 1, 1, 1) reads as open, under no ledge and sunlit: what the web app gives a mesh without the attribute.
A second corner attribute, `_edge` (exported as _EDGE, a VEC4 of floats; Draco keeps EDGE_RANGE / 2^16): the distances
in metres, along the face, to up to four of its arrises (the convex edges where the next face turns away behind it),
EDGE_RANGE where it has none.  The distance to a line is linear over a planar face, so the corners carry it exactly
however large the face; the web app wears the stone and the concrete off within a few centimetres of the nearest
(web/src/walltone.js edgeWear).
(The height over the ground, for the soil splashed up the walls, the web app reads from its own terrain.)  Leaf
faces (the ivy) take none of it: their corners keep the mesh's own corner colour, the wind data of
landmarks.ivy_patch.

G and B are linear in position over a face, so the corners carry them exactly.  The occlusion is not: a large flat
quad (a 60 m band of glass behind the piers of 중앙도서관, the soffit of 학생회관's pilotis) is split into a grid of
about STEP for the bake and thinned back to the fewest grid lines that reproduce it and the sun's shadow on it (an open
wall: its corners only).  A large flat n-gon (a roof inside its parapets) takes one value from points inside it.
"""
import bpy, math, os, json, time
import numpy as np
import common
from common import MATS

AO_DIST = 10.0         # m: occluders farther than this do not count
AO_SAMPLES = 128       # rays per vertex
SPLIT = 4.0            # m: a flat quad longer than this is split for the bake (the halls' bays and storeys are not)
STEP = 1.5             # m: into a grid this fine
AO_TOL = 0.08          # thin a grid while its coarser cells stay this close to every node
DOWN_W = 0.6           # share of a downward face's light that the shaded ground under it takes away
D_RANGE, U_RANGE = 16.0, 8.0
REACH = 2.5            # m: how far the streaks under a ledge run down at most (else to the opening below it; the
                       # photos agree, their darkness per material is materials.json `streak`: reference/고증.md 3.19)
QUANT = (64, 256, 256, 32)  # levels per channel
LEDGE_DEPTH = 0.65     # m: deepest upward face that still counts as a ledge (sills, copings, bands, treads)
EDGE_RANGE = 128.0     # m: an edge channel's value where the face has no arris for it (and its largest distance)
EDGE_BEND = 0.85       # cos of the least turn between two faces that makes their shared edge an arris (32 deg)
# halls that were new in 1997 (bid -> share of their materials' weathering, exported as the object's extras):
# 대우관 was finished in 1996, 제3공학관 and 제2인문관 were going up
AGE = {'242897922': 0.1, '224955691': 0.15, '246156119': 0.15}


def _front_only(name):
    """Materials the web app draws one-sided (glass, frames): their face is always the side that counts."""
    d = MATS.get(name.split('.')[0], {})
    return not ('tex' in d or 'leaf' in d or d.get('side') == 'double')


def _is_leaf(name):
    return 'leaf' in MATS.get(name.split('.')[0], {})


def _ground(x, y):
    """common.ground over arrays"""
    T, TH, TS = common._T, common._TH, common._TS
    fx = np.clip((x + TH) / TS, 0, T.shape[1] - 1.001)
    fy = np.clip((y + TH) / TS, 0, T.shape[0] - 1.001)
    i, j = fx.astype(np.int64), fy.astype(np.int64)
    ax, ay = fx - i, fy - j
    return (T[j, i] * (1 - ax) * (1 - ay) + T[j, i + 1] * ax * (1 - ay)
            + T[j + 1, i] * (1 - ax) * ay + T[j + 1, i + 1] * ax * ay)


# ----------------------------------------------------------------------------- mesh arrays
class _Mesh:
    """A mesh as plain arrays: co (V,3), ls (loop start per face), lv (vertex per loop), mi, sm, uv (L,2) or None"""

    def __init__(self, co, ls, lv, mi, sm, uv):
        self.co, self.ls, self.lv, self.mi, self.sm, self.uv = co, ls, lv, mi, sm, uv
        self.lt = np.diff(np.append(ls, len(lv)))
        self.lf = np.repeat(np.arange(len(ls)), self.lt)          # face of every loop

    @staticmethod
    def read(me):
        nv, nl, nf = len(me.vertices), len(me.loops), len(me.polygons)
        co = np.empty(nv * 3, np.float32)
        me.vertices.foreach_get('co', co)
        ls = np.empty(nf, np.int32)
        me.polygons.foreach_get('loop_start', ls)
        lv = np.empty(nl, np.int32)
        me.loops.foreach_get('vertex_index', lv)
        mi = np.empty(nf, np.int32)
        me.polygons.foreach_get('material_index', mi)
        sm = np.empty(nf, bool)
        me.polygons.foreach_get('use_smooth', sm)
        uv = None
        if me.uv_layers:
            uv = np.empty(nl * 2, np.float32)
            me.uv_layers[0].data.foreach_get('uv', uv)
            uv = uv.reshape(-1, 2)
        order = np.argsort(ls, kind='stable')                     # (faces are stored in loop order already)
        return _Mesh(co.reshape(-1, 3).astype(np.float64), ls[order], lv, mi[order], sm[order], uv)

    def write(self, name, mats, col=None, edge=None):
        me = bpy.data.meshes.new(name)
        me.vertices.add(len(self.co))
        me.vertices.foreach_set('co', self.co.astype(np.float32).ravel())
        me.loops.add(len(self.lv))
        me.loops.foreach_set('vertex_index', self.lv.astype(np.int32))
        me.polygons.add(len(self.ls))
        me.polygons.foreach_set('loop_start', self.ls.astype(np.int32))
        me.update(calc_edges=True)
        for m in mats:
            me.materials.append(m)
        me.polygons.foreach_set('material_index', self.mi.astype(np.int32))
        me.polygons.foreach_set('use_smooth', self.sm.astype(bool))
        if self.uv is not None:
            me.uv_layers.new(name='UVMap').data.foreach_set('uv', self.uv.astype(np.float32).ravel())
        if col is not None:
            ca = me.color_attributes.new('bake', 'FLOAT_COLOR', 'CORNER')
            ca.data.foreach_set('color', col.astype(np.float32).ravel())
            me.color_attributes.active_color = ca
            me.color_attributes.render_color_index = me.color_attributes.active_color_index
        if edge is not None:            # (a quaternion: four floats that the glTF exporter writes as they are)
            me.attributes.new('_edge', 'QUATERNION', 'CORNER').data.foreach_set('value', edge.astype(np.float32).ravel())
        me.validate(clean_customdata=False)
        me.update()
        return me

    def normals(self, co):
        """unit face normals (Newell) for vertex positions co"""
        p = co[self.lv]
        nxt = np.arange(len(self.lv)) + 1
        last = self.ls + self.lt - 1
        nxt[last] = self.ls
        q = p[nxt]
        n = np.zeros((len(self.ls), 3))
        for k, (a, b) in enumerate(((1, 2), (2, 0), (0, 1))):
            n[:, k] = np.bincount(self.lf, (p[:, a] - q[:, a]) * (p[:, b] + q[:, b]), len(self.ls))
        return n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]


# ----------------------------------------------------------------------------- 1. split large flat faces
def _newell(c):
    n = np.zeros(3)
    for p, q in zip(c, np.roll(c, -1, 0)):
        n += ((p[1] - q[1]) * (p[2] + q[2]), (p[2] - q[2]) * (p[0] + q[0]), (p[0] - q[0]) * (p[1] + q[1]))
    ln = np.linalg.norm(n)
    return n / ln if ln > 1e-12 else None


def _probes(c, nrm):
    """Up to 9 points inside the flat polygon c, 5 mm off its face, each as a tiny triangle facing as it does"""
    ax = c[1] - c[0]
    ax /= max(np.linalg.norm(ax), 1e-9)
    ay = np.cross(nrm, ax)
    q = np.column_stack(((c - c[0]) @ ax, (c - c[0]) @ ay))
    lo, hi = q.min(0), q.max(0)
    g = np.linspace(0.12, 0.88, 4)
    cand = lo + (hi - lo) * np.array([(x, y) for x in g for y in g])
    inside = np.zeros(len(cand), bool)                     # even-odd rule
    for (x0, y0), (x1, y1) in zip(q, np.roll(q, -1, 0)):
        cross = (y0 > cand[:, 1]) != (y1 > cand[:, 1])
        xs = x0 + (cand[:, 1] - y0) * (x1 - x0) / np.where(y1 != y0, y1 - y0, 1e-12)
        inside ^= cross & (cand[:, 0] < xs)
    pts = cand[inside][::2][:9] if inside.any() else q.mean(0)[None]
    p = c[0] + pts[:, :1] * ax + pts[:, 1:] * ay + nrm * 0.005
    return np.stack((p, p + ax * 0.02, p + ay * 0.02), 1).reshape(-1, 3)


def _densify(m, M):
    """-> (dense mesh, grids, probes).  A large flat quad becomes a grid of about STEP; every other face is copied
    with its own vertices, faces keeping their order (a grid's faces stand in its quad's place).  A large flat n-gon
    (a roof inside its parapets, whose corners all sit in the corners' shade) is sampled at a few points inside instead,
    by tiny triangles after all the faces.
    grid: dict(f, grid (nu, nv), v0 first node, k nodes, W (k, 4) node weights of the quad's corners -- linear in
    position, so they carry UVs and the streak fields exactly -- faces (local quads));  probes: {face: vertex ids}"""
    cow = m.co @ M[:3, :3].T + M[:3, 3]
    co = [m.co]
    ls, lv, mi, sm, uv, patches, probe = [], [], [], [], [], [], {}
    nv_, nl_ = len(m.co), 0
    for f in range(len(m.ls)):
        a, n = m.ls[f], m.lt[f]
        ids = m.lv[a:a + n]
        pt = None
        if not m.sm[f] and n >= 4:
            c = cow[ids]
            nrm = _newell(c)
            flat = nrm is not None and np.abs((c - c[0]) @ nrm).max() < 0.01
            if flat and n == 4:
                lu = max(np.linalg.norm(c[1] - c[0]), np.linalg.norm(c[2] - c[3]))
                lv_ = max(np.linalg.norm(c[3] - c[0]), np.linalg.norm(c[2] - c[1]))
                nu, nv = int(math.ceil(lu / STEP)), int(math.ceil(lv_ / STEP))
                if max(lu, lv_) > SPLIT:
                    s, t = np.meshgrid(np.linspace(0, 1, nu + 1), np.linspace(0, 1, nv + 1))
                    s, t = s.ravel()[:, None], t.ravel()[:, None]
                    W = np.hstack(((1 - s) * (1 - t), s * (1 - t), s * t, (1 - s) * t))
                    i, j = np.meshgrid(np.arange(nu), np.arange(nv))
                    i, j = i.ravel(), j.ravel()
                    F = np.stack((j * (nu + 1) + i, j * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i + 1,
                                  (j + 1) * (nu + 1) + i), 1)
                    pt = dict(grid=(nu, nv), W=W, faces=F)
            elif flat and (c.max(0) - c.min(0)).max() > SPLIT:
                probe[f] = _probes(m.co[ids], _newell(m.co[ids]))
        if pt is None:
            ls.append(np.array([nl_]))
            lv.append(ids)
            mi.append([m.mi[f]])
            sm.append([m.sm[f]])
            if m.uv is not None:
                uv.append(m.uv[a:a + n])
            nl_ += n
            continue
        W, F = pt['W'], pt['faces']
        pt.update(f=f, v0=nv_, k=len(W))
        patches.append(pt)
        co.append(W @ m.co[ids])
        ls.append(nl_ + 4 * np.arange(len(F)))
        lv.append((F + nv_).ravel())
        mi.append([m.mi[f]] * len(F))
        sm.append([False] * len(F))
        if m.uv is not None:
            uv.append((W @ m.uv[a:a + n])[F.ravel()])
        nv_ += len(W)
        nl_ += F.size
    for f, P in probe.items():                              # (the bake reads their first corners)
        k = len(P) // 3
        co.append(P)
        ls.append(nl_ + 3 * np.arange(k))
        lv.append(nv_ + np.arange(3 * k))
        mi.append([m.mi[f]] * k)
        sm.append([False] * k)
        if m.uv is not None:
            uv.append(np.zeros((3 * k, 2)))
        probe[f] = nv_ + 3 * np.arange(k)
        nv_ += 3 * k
        nl_ += 3 * k
    d = _Mesh(np.vstack(co), np.concatenate(ls), np.concatenate(lv), np.concatenate(mi),
              np.concatenate(sm).astype(bool), np.vstack(uv) if m.uv is not None else None)
    return d, patches, probe


# ----------------------------------------------------------------------------- 2. bake
def _bake_pass(ob, name):
    ca = ob.data.color_attributes.new(name, 'FLOAT_COLOR', 'POINT')
    ob.data.color_attributes.active_color = ca
    bpy.ops.object.bake(type='AO')
    a = np.empty(len(ob.data.vertices) * 4, np.float32)
    ob.data.color_attributes[name].data.foreach_get('color', a)
    return a.reshape(-1, 4)[:, 0].astype(np.float64)


def _bake_both_sides(meshes, scene_objs):
    """AO per vertex of every dense mesh (world space), baked as one object: Cycles syncs the whole scene for each
    object it bakes"""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = AO_SAMPLES
    if sc.world is None:
        sc.world = bpy.data.worlds.new('bake')
    sc.world.light_settings.distance = AO_DIST
    sc.render.bake.target = 'VERTEX_COLORS'
    off = np.cumsum([0] + [len(d.co) for d in meshes])
    loff = np.cumsum([0] + [len(d.lv) for d in meshes])
    allm = _Mesh(np.vstack([d.co for d in meshes]),
                 np.concatenate([d.ls + lo for d, lo in zip(meshes, loff)]),
                 np.concatenate([d.lv + o for d, o in zip(meshes, off)]),
                 np.zeros(sum(len(d.ls) for d in meshes), np.int32),
                 np.concatenate([d.sm for d in meshes]), None)
    tmp = bpy.data.objects.new('bake_tmp', allm.write('bake_tmp', []))
    sc.collection.objects.link(tmp)
    hide = [o for o in scene_objs if not o.hide_render]
    for o in hide:
        o.hide_render = True
    bpy.ops.object.select_all(action='DESELECT')
    tmp.select_set(True)
    bpy.context.view_layer.objects.active = tmp
    # the GLB faces wind either way (the web draws the walls double-sided): bake both sides, keep the open one
    front = _bake_pass(tmp, 'ao_front')
    tmp.data.flip_normals()
    back = _bake_pass(tmp, 'ao_back')
    for o in hide:
        o.hide_render = False
    me = tmp.data
    bpy.data.objects.remove(tmp)
    bpy.data.meshes.remove(me)
    return ([front[off[i]:off[i + 1]] for i in range(len(meshes))],
            [back[off[i]:off[i + 1]] for i in range(len(meshes))])


# ----------------------------------------------------------------------------- 3. ledges and rain streaks
def _streaks(m, cow, n_eff, wet):
    """The G and B channels per loop of the original mesh: under which ledge each wall face lies.
    A wall face right under a ledge takes it.  The faces below that one in the same wall plane -- under a sill the
    spandrel ends at the floor line, and the window head of the storey below is a face of its own -- take the ledge
    from the face above, with the position along it measured the same way, so the streaks run on across the seams.
    A ledge's fade length is how far its faces reach down under its middle (to the opening below it, or the ground),
    at most REACH: the streaks fade out at the next window head, not at the first face's foot.
    wet: per face, whether its material weathers (glass and frames neither take the streaks on nor pass them down)."""
    dep = np.ones(len(m.lv))
    along = np.ones(len(m.lv))
    cell = 4.0
    ledges, grid = [], {}
    for f in np.where(n_eff[:, 2] > 0.9)[0]:
        xy = cow[m.lv[m.ls[f]:m.ls[f] + m.lt[f]], :2]
        best = None
        for k in range(len(xy)):
            e = xy[(k + 1) % len(xy)] - xy[k]
            L = math.hypot(*e)
            if L < 1e-3:
                continue
            ax = e / L
            a, b = xy @ ax, xy @ np.array((-ax[1], ax[0]))
            ea, eb = a.max() - a.min(), b.max() - b.min()
            if best is None or ea * eb < best[0]:
                best = (ea * eb, max(ea, eb), min(ea, eb))
        if best is None or best[2] > LEDGE_DEPTH or best[1] < 0.3:
            continue
        z = cow[m.lv[m.ls[f]:m.ls[f] + m.lt[f]], 2].mean()
        li = len(ledges)
        ledges.append((z, xy))
        lo, hi = np.floor(xy.min(0) / cell).astype(int), np.floor(xy.max(0) / cell).astype(int)
        for gx in range(lo[0], hi[0] + 1):
            for gy in range(lo[1], hi[1] + 1):
                grid.setdefault((gx, gy), []).append(li)
    if not ledges:
        return dep, along
    def cells(q):                                          # the grid cells a face's corners q span
        lo, hi = np.floor(q[:, :2].min(0) / cell).astype(int), np.floor(q[:, :2].max(0) / cell).astype(int)
        return [(gx, gy) for gx in range(lo[0], hi[0] + 1) for gy in range(lo[1], hi[1] + 1)]

    walls = np.where(np.abs(n_eff[:, 2]) < 0.15)[0]
    info = {}       # wall face -> corners, top, foot, outward normal, along-the-wall axis, its offset at top and foot
    for f in walls:
        p = cow[m.lv[m.ls[f]:m.ls[f] + m.lt[f]]]
        ztop, zbot = p[:, 2].max(), p[:, 2].min()
        nf = n_eff[f, :2] / max(np.linalg.norm(n_eff[f, :2]), 1e-9)
        off = p[:, :2] @ nf
        info[f] = (p, ztop, zbot, nf, np.array((-nf[1], nf[0])), off[p[:, 2] > ztop - 0.02].mean(),
                   off[p[:, 2] < zbot + 0.02].mean())
    asg = {}        # wall face -> (ledge, its height, axis and extent along it [l0, l1] as the faces under it measure it)
    # 1. right under a ledge
    for f in walls:
        p, ztop, zbot, nf, tf, _, _ = info[f]
        fs = p[:, :2] @ tf
        best = None
        for li in {li for c in cells(p) for li in grid.get(c, ())}:
            z, xy = ledges[li]
            if not (z - 0.3 <= ztop <= z + 0.02):
                continue
            dd = (xy - p[0, :2]) @ nf
            if not (-0.03 <= dd.max() <= 0.7 and dd.min() >= -0.6):
                continue
            ls_ = xy @ tf
            ov = min(ls_.max(), fs.max()) - max(ls_.min(), fs.min())
            if ov > 0.15 and (best is None or ov > best[0]):
                best = (ov, li, z, ls_.min(), ls_.max())
        if best is not None:
            _, li, z, l0, l1 = best
            if np.abs(fs - (l0 + l1) / 2).max() <= U_RANGE * max((l1 - l0) / 2, 0.05):
                asg[f] = (li, z, tf, l0, l1)
    # 2. on down the wall: from the face above, top to bottom so that each face's is settled before it hands it on
    below = {}
    for f in asg:
        for c in cells(info[f][0]):
            below.setdefault(c, []).append(f)
    for f in sorted((f for f in walls if f not in asg and wet[f]), key=lambda f: -info[f][1]):
        p, ztop, zbot, nf, tf, otop, _ = info[f]
        fs = p[:, :2] @ tf
        best = None
        for g in {g for c in cells(p) for g in below.get(c, ())}:
            gp, _, gzb, gnf, _, _, gobot = info[g]
            if not wet[g] or abs(gzb - ztop) > 0.03 or gnf @ nf < 0.95 or abs(gobot - otop) > 0.04:
                continue
            li, z, ltf, l0, l1 = asg[g]
            gs = gp[:, :2] @ tf
            ov = min(gs.max(), fs.max()) - max(gs.min(), fs.min())
            s = p[:, :2] @ ltf
            if (ov > 0.1 and z - ztop < REACH and min(s.max(), l1) - max(s.min(), l0) > 0.05
                    and np.abs(s - (l0 + l1) / 2).max() <= U_RANGE * max((l1 - l0) / 2, 0.05)
                    and (best is None or ov > best[0])):
                best = (ov, g)
        if best is not None:
            asg[f] = asg[best[1]]
            for c in cells(p):
                below.setdefault(c, []).append(f)
    # 3. each ledge's fade length: down to the lowest foot of its faces under its middle, not into the ground
    stop = {}
    for f, (li, z, ltf, l0, l1) in asg.items():
        p, zbot = info[f][0], info[f][2]
        s = p[:, :2] @ ltf
        mid = s.min() - 0.02 <= (l0 + l1) / 2 <= s.max() + 0.02
        k = stop.get(li, (False, np.inf))
        if (mid, -zbot) > (k[0], -k[1]):
            stop[li] = (mid, zbot)
    fade = {}
    for li, (_, zs) in stop.items():
        z, xy = ledges[li]
        fade[li] = min(REACH, max(0.3, z - max(zs, _ground(xy[:, 0], xy[:, 1]).min())))
    for f, (li, z, ltf, l0, l1) in asg.items():
        a, n = m.ls[f], m.lt[f]
        p = info[f][0]
        u = (p[:, :2] @ ltf - (l0 + l1) / 2) / max((l1 - l0) / 2, 0.05)
        dep[a:a + n] = np.clip((z - p[:, 2]) / fade[li] / D_RANGE, 0, 1)
        along[a:a + n] = (u + U_RANGE) / (2 * U_RANGE)
    return dep, along


def _coarsest(g, gs=None):
    """The fewest grid lines (index arrays along u and v, ends included) whose bilinear cells reproduce every node of
    the grid g (nv+1, nu+1) within AO_TOL, and of the sun's grid gs (the same shape) within SUN_TOL"""
    nv, nu = g.shape[0] - 1, g.shape[1] - 1

    def lines(n, k):
        return np.unique(np.r_[np.arange(0, n, k), n])

    def interp(idx, n):                                       # fine index -> (cell start, cell end, weight)
        c = np.clip(np.searchsorted(idx, np.arange(n + 1), side='right') - 1, 0, len(idx) - 2)
        return idx[c], idx[c + 1], (np.arange(n + 1) - idx[c]) / (idx[c + 1] - idx[c])

    steps = lambda n: sorted({n} | {2 ** e for e in range(int(math.log2(max(n, 1))) + 1)}, reverse=True)
    best = None
    for ku in steps(nu):
        for kv in steps(nv):
            iu, jv = lines(nu, ku), lines(nv, kv)
            if best is not None and len(iu) * len(jv) >= len(best[0]) * len(best[1]):
                continue
            u0, u1, wu = interp(iu, nu)
            v0, v1, wv = interp(jv, nv)
            wu, wv = wu[None, :], wv[:, None]
            err = lambda G: np.abs(G[np.ix_(v0, u0)] * (1 - wu) * (1 - wv) + G[np.ix_(v0, u1)] * wu * (1 - wv)
                                   + G[np.ix_(v1, u1)] * wu * wv + G[np.ix_(v1, u0)] * (1 - wu) * wv - G).max()
            if err(g) < AO_TOL and (gs is None or err(gs) < SUN_TOL):
                best = (iu, jv)
    return best if best is not None else (np.arange(nu + 1), np.arange(nv + 1))


def _edges(m, cow, n_eff, wear):
    """The `_edge` attribute per loop of the original mesh (see the module doc): for each face whose material weathers
    (wear), the in-plane distances of its corners to its longest arrises, at most four.  Edges are matched by their
    rounded end points, either winding; an edge is an arris where a face sharing it turns by more than EDGE_BEND and
    lies behind the open side (n_eff); an edge no other face shares (a T-junction) stays sharp."""
    out = np.full((len(m.lv), 4), EDGE_RANGE)
    P = np.round(cow / 0.005).astype(np.int64)
    key = lambda i, j: (tuple(P[i]), tuple(P[j])) if tuple(P[i]) < tuple(P[j]) else (tuple(P[j]), tuple(P[i]))
    faces_of, cent = {}, np.zeros((len(m.ls), 3))
    for f in range(len(m.ls)):
        vs = m.lv[m.ls[f]:m.ls[f] + m.lt[f]]
        cent[f] = cow[vs].mean(0)
        for k in range(len(vs)):
            faces_of.setdefault(key(vs[k], vs[(k + 1) % len(vs)]), []).append(f)
    for f in np.where(wear)[0]:
        a, n = m.ls[f], m.lt[f]
        vs = m.lv[a:a + n]
        nf = n_eff[f]
        found = []
        for k in range(n):
            i, j = vs[k], vs[(k + 1) % n]
            e = cow[j] - cow[i]
            L = np.linalg.norm(e)
            if L < 0.02:
                continue
            nb = [g for g in faces_of[key(i, j)] if g != f]
            if not nb or not all(n_eff[g] @ nf < EDGE_BEND and (cent[g] - cow[i]) @ nf < -0.005 for g in nb):
                continue
            inward = np.cross(nf, e / L)
            if (cent[f] - cow[i]) @ inward < 0:
                inward = -inward
            found.append((L, cow[i], inward))
        for c, (_, p0, inward) in enumerate(sorted(found, key=lambda t: -t[0])[:4]):
            out[a:a + n, c] = np.clip((cow[vs] - p0) @ inward, 0, EDGE_RANGE)
    return out


def _own_colour(me, verts):
    """The leaves take no occlusion or weathering: their corners keep the mesh's own colour instead (the ivy's wind,
    landmarks.ivy_patch), white where it has none.  verts: original vertex ids (a leaf card is never split)."""
    out = np.ones((len(verts), 4))
    ca = me.color_attributes.get('Col')
    if ca is None:
        return out
    c = np.empty(len(ca.data) * 4, np.float32)
    ca.data.foreach_get('color', c)
    c = c.reshape(-1, 4).astype(np.float64)
    if ca.domain == 'CORNER':
        lv = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get('vertex_index', lv)
        v = np.ones((len(me.vertices), 4))
        v[lv] = c
        c = v
    ok = verts < len(c)
    out[ok] = np.round(c[verts[ok]] * 64) / 64                   # (the wind needs no finer: packs smaller)
    return out


# ----------------------------------------------------------------------------- 4. the sun's shadow
SUN_RAYS = 4           # shadow rays per corner, spread over the sun's disc
SUN_ANGLE = 1.5        # deg: the sun's disc and a little more (the soft edges of the web's shadows)
SUN_TOL = 0.3          # a split quad keeps the grid lines its shadow edges need, to within this
SUN_LIFT = 0.02        # m: the rays leave this far off the face, a centimetre in from its edges
CROWN_PASS = 0.55      # light each side of a crown lets through: about 0.3 through a whole crown, as the dappled
                       # shade of the leaf cards on the ground (web/public/assets/textures/sun_shadow.png)


def sun_dir():
    """The fixed sun (blender/sky_bake.py: the HDRI's brightest texel, web/public/data/sky.json) as web/src/main.js
    turns it into the light's direction, in the campus frame (x east, y north, z up; three's z is -north)"""
    s = json.load(open(os.path.join(common.ROOT, 'web', 'public', 'data', 'sky.json')))
    phi, el = (s['sun_u'] - 0.5) * 2 * math.pi, (s['sun_v'] - 0.5) * math.pi
    return np.array((math.cos(el) * math.cos(phi), -math.cos(el) * math.sin(phi), math.sin(el)))


def _tris(m):
    """A _Mesh's faces for a BVH: triangles and quads as triangles (array), larger faces as they are (lists)"""
    tri = m.lt == 3
    quad = m.lt == 4
    a = m.ls[tri][:, None] + np.arange(3)
    q = m.ls[quad][:, None] + np.array((0, 1, 2, 0, 2, 3))
    t = np.vstack((m.lv[a], m.lv[q].reshape(-1, 3)))
    big = [m.lv[s:s + n].tolist() for s, n in zip(m.ls[m.lt > 4], m.lt[m.lt > 4])]
    return t, big


def _crowns():
    """Every tree's crown (blender/vegetation.py SPECIES envelope, where web/src/world.js plants it) as an ellipsoid:
    (vertices, triangles) of them all, or None"""
    import vegetation
    seg, ring = 12, 6
    th = np.linspace(0, math.pi, ring + 1)
    ph = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    u = np.vstack([(np.sin(t) * np.cos(ph), np.sin(t) * np.sin(ph), np.full(seg, np.cos(t))) for t in th[1:-1]]
                  ).reshape(ring - 1, 3, seg).transpose(0, 2, 1).reshape(-1, 3)
    u = np.vstack((u, (0, 0, 1), (0, 0, -1)))                 # rings, then the two poles
    top, bot = len(u) - 2, len(u) - 1
    f = []
    for r in range(ring - 2):
        for k in range(seg):
            a, b = r * seg + k, r * seg + (k + 1) % seg
            f += [(a, b, b + seg), (a, b + seg, a + seg)]
    for k in range(seg):
        f += [(top, (k + 1) % seg, k), (bot, (ring - 2) * seg + k, (ring - 2) * seg + (k + 1) % seg)]
    f = np.array(f)
    V, T = [], []
    for sp, x, y, sc, *_ in common.CAMPUS['trees']:
        s = vegetation.SPECIES.get(sp)
        if s is None:
            continue
        p = u.copy()
        r = np.where(p[:, 2] > 0, 1 - s['taper'] * np.maximum(p[:, 2], 0) ** 1.2, 1.0) if s.get('exc') else 1.0
        p[:, 0] *= s['rx'] * sc * r
        p[:, 1] *= s['rx'] * sc * r
        p[:, 2] *= s['rz'] * sc
        p += (x, y, common.ground(x, y) - 0.05 + s['cz'] * sc)
        T.append(f + len(V) * len(u))
        V.append(p)
    return (np.vstack(V), np.vstack(T)) if V else None


def _glb_tris(path):
    """The triangles of another GLB's meshes (the halls' when the landmarks bake, and the other way round), world
    space: (vertices, triangles), or None"""
    if not path or not os.path.exists(path):
        print('bake: no', path, '(its shadows left out)')
        return None
    objs0, mats0 = set(bpy.data.objects), set(bpy.data.materials)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in objs0]
    V, T, nv = [], [], 0
    for o in new:
        if o.type != 'MESH' or o.name.startswith('walk'):
            continue
        me = o.data
        c = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get('co', c)
        M = np.array(o.matrix_world)
        me.calc_loop_triangles()
        t = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get('vertices', t)
        V.append(c.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])
        T.append(t.reshape(-1, 3) + nv)
        nv += len(me.vertices)
    for o in new:
        data = o.data
        bpy.data.objects.remove(o)
        if isinstance(data, bpy.types.Mesh) and not data.users:
            bpy.data.meshes.remove(data)
    for m in [m for m in bpy.data.materials if m not in mats0]:
        bpy.data.materials.remove(m)
    return (np.vstack(V), np.vstack(T)) if V else None


def _sun_light(meshes, glb=None):
    """The sun's light on every corner (loop) of the dense meshes (world space), on the side of its face towards the
    sun (the other side is unlit whatever the shadow, so this one value serves whichever side the web app shows: it
    draws the walls double-sided).  SUN_RAYS rays over the sun's disc from just off the face, against these meshes
    and the other GLB's, and through the crowns, each side of one letting CROWN_PASS through.  1 sunlit, 0 in shadow.
    (A ray cast of our own: Cycles' shadow bake leaves the baked object out of its own shadow.)"""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    t0 = time.time()
    s = sun_dir()
    V, T, big, nv = [], [], [], 0
    for d in meshes:
        t, b = _tris(d)
        V.append(d.co)
        T.append(t + nv)
        big += [[i + nv for i in p] for p in b]
        nv += len(d.co)
    other = _glb_tris(glb)
    if other is not None:
        V.append(other[0])
        T.append(other[1] + nv)
    solid = BVHTree.FromPolygons(np.vstack(V).tolist(), np.vstack(T).tolist() + big)
    cr = _crowns()
    crowns = BVHTree.FromPolygons(cr[0].tolist(), cr[1].tolist(), all_triangles=True) if cr is not None else None
    # the points: every corner, moved in towards its face's middle and off the face on the sun's side
    co = np.vstack([d.co[d.lv] for d in meshes])
    nrm = np.vstack([d.normals(d.co)[d.lf] for d in meshes])
    cen = np.column_stack([np.concatenate([(np.bincount(d.lf, d.co[d.lv, k], len(d.ls)) / d.lt)[d.lf] for d in meshes])
                           for k in range(3)])
    tc = cen - co
    tl = np.linalg.norm(tc, axis=1)
    p = (co + tc * (np.minimum(0.01, tl * 0.3) / np.maximum(tl, 1e-9))[:, None]
         + nrm * np.where(nrm @ s >= 0, SUN_LIFT, -SUN_LIFT)[:, None])
    _, first, inv = np.unique(np.round(p / 0.005).astype(np.int64), axis=0, return_index=True, return_inverse=True)
    # the rays: SUN_RAYS directions spread evenly over the disc
    e1 = np.cross(s, (0, 0, 1))
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(s, e1)
    rad = math.radians(SUN_ANGLE) / 2
    dirs = []
    for k in range(SUN_RAYS):
        r, a = rad * math.sqrt((k + 0.5) / SUN_RAYS), k * 2.39996
        v = s + r * (math.cos(a) * e1 + math.sin(a) * e2)
        dirs.append(Vector(v / np.linalg.norm(v)))
    cast, ccast = solid.ray_cast, crowns.ray_cast if crowns is not None else None
    out = np.empty(len(first))
    for i, q in enumerate(p[first].tolist()):
        lit = 0.0
        for dv in dirs:
            if cast(q, dv)[0] is not None:
                continue
            tr = 1.0
            if ccast is not None:
                o = q
                for _ in range(8):
                    h = ccast(o, dv)[0]
                    if h is None:
                        break
                    tr *= CROWN_PASS
                    o = h + dv * 0.001
            lit += tr
        out[i] = lit / SUN_RAYS
    vis = out[inv.ravel()]
    loff = np.cumsum([0] + [len(d.lv) for d in meshes])
    print('bake: sun %.1fs (%d points, %d of the other GLB\'s triangles, %d crowns)' % (
        time.time() - t0, len(first), 0 if other is None else len(other[1]), len(common.CAMPUS['trees'])))
    return [vis[loff[i]:loff[i + 1]] for i in range(len(meshes))]


# ----------------------------------------------------------------------------- driver
def bake(objs, sun_glb=None):
    """Write the 'bake' colour attribute on every mesh object in objs (in place; large quads may be split).
    Objects named walk_* (invisible walk surfaces) neither receive nor occlude.  sun_glb: the other GLB of halls or
    landmarks, whose shadows fall on these too (its last build)."""
    t0 = time.time()
    hidden = [o for o in objs if o.name.startswith('walk')]
    objs = [o for o in objs if o.type == 'MESH' and o not in hidden and len(o.data.polygons)]
    for ob in objs:
        if ob.get('bid') in AGE:
            ob['weather'] = AGE[ob['bid']]
    orig, dense, world = {}, {}, []
    for ob in objs:
        m = _Mesh.read(ob.data)
        M = np.array(ob.matrix_world)
        d, patches, probe = _densify(m, M)
        orig[ob.name], dense[ob.name] = (m, M, list(ob.data.materials)), (d, patches, probe)
        w = _Mesh(d.co @ M[:3, :3].T + M[:3, 3], d.ls, d.lv, d.mi, d.sm, None)
        world.append(w)
    t1 = time.time()
    front, back = _bake_both_sides(world, objs + hidden)
    sunL = _sun_light(world, sun_glb)
    t2 = time.time()
    nv0 = nv1 = npatch = nmerge = 0
    for ob, aoF, aoB, suL in zip(objs, front, back, sunL):
        m, M, mats = orig[ob.name]
        d, patches, probe = dense[ob.name]
        R3, T3 = M[:3, :3], M[:3, 3]
        cod = d.co @ R3.T + T3
        nd = d.normals(cod)
        # the open side of every original face (a patch as a whole); one-sided materials keep their front
        pmap = {p['f']: p for p in patches}
        cnt = np.ones(len(m.ls), np.int64)
        for p in patches:
            cnt[p['f']] = len(p['faces'])
        owner = np.repeat(np.arange(len(m.ls)), cnt)              # dense face -> original face
        owner = np.concatenate([owner] + [np.full(len(v), f) for f, v in probe.items()])
        sF = np.bincount(owner[d.lf], aoF[d.lv], len(m.ls))
        sB = np.bincount(owner[d.lf], aoB[d.lv], len(m.ls))
        fwd = sF >= sB
        front_only = np.array([_front_only(x.name) for x in mats] + [True])
        fwd |= front_only[np.minimum(m.mi, len(mats))]
        sign = np.where(fwd, 1.0, -1.0)
        ao = np.where(fwd[owner[d.lf]], aoF[d.lv], aoB[d.lv])
        # average the corners that coincide (same place, same facing): a face's corners were baked apart from
        # those of its neighbours, and the noise would show as steps along the seams
        ne = nd[d.lf] * sign[owner[d.lf]][:, None]
        key = np.hstack((np.round(cod[d.lv] / 0.02), np.round(ne * 3))).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        inv = inv.ravel()
        ao = (np.bincount(inv, ao) / np.bincount(inv))[inv]
        # the sun, on the side of each face that faces it, the coinciding corners averaged the same way
        sun = suL                                                 # (per corner)
        ns = nd[d.lf] * np.where(nd[d.lf] @ sun_dir() > 0, 1.0, -1.0)[:, None]
        _, inv_s = np.unique(np.hstack((np.round(cod[d.lv] / 0.02), np.round(ns * 3))).astype(np.int64), axis=0,
                             return_inverse=True)
        inv_s = inv_s.ravel()
        sun = (np.bincount(inv_s, sun) / np.bincount(inv_s))[inv_s]
        # rain streaks, from the original faces with their open side
        com = m.co @ R3.T + T3
        n_eff = m.normals(com) * sign[:, None]
        wet = np.array([MATS.get(x.name.split('.')[0], {}).get('weather', 0) > 0 for x in mats] + [False])
        dep, along = _streaks(m, com, n_eff, wet[np.minimum(m.mi, len(mats))])
        edge = _edges(m, com, n_eff, wet[np.minimum(m.mi, len(mats))])
        # assemble: faces as they were, each grid thinned to what its corners or a coarser grid reproduce
        aov, sunv = np.zeros(len(d.co)), np.zeros(len(d.co))
        aov[d.lv] = ao                                            # (a node is shared only within its grid)
        sunv[d.lv] = sun
        for p in patches:
            nu, nv = p['grid']
            g = aov[p['v0']:p['v0'] + p['k']].reshape(nv + 1, nu + 1)
            if nu > 1 and nv > 1:                                 # soften the bake noise inside the grid
                inner = sum(g[1 + dj:nv + dj, 1 + di:nu + di] for dj in (-1, 0, 1) for di in (-1, 0, 1)) / 9
                g[1:nv, 1:nu] = 0.5 * g[1:nv, 1:nu] + 0.5 * inner
            p['ao'] = g.ravel()
            p['sun'] = sunv[p['v0']:p['v0'] + p['k']]
            p['sub'] = _coarsest(g, p['sun'].reshape(nv + 1, nu + 1))
            p['merge'] = len(p['sub'][0]) == 2 and len(p['sub'][1]) == 2
        # a probed n-gon: one value, from the more open of its probes (a roof half under 백주년기념관's drum)
        flat = {f: np.percentile((aoF if fwd[f] else aoB)[v], 70) for f, v in probe.items()}
        # and the share of its probes in the sun
        pS = np.zeros(len(d.co))
        pS[d.lv] = suL                                            # (a probe's corners are its own)
        flat_sun = {f: pS[v].mean() for f, v in probe.items()}
        co, ls, lv, mi, sm, uv, col, sa, edg = [m.co], [], [], [], [], [], [], [], []
        nl_, nv_ = 0, len(m.co)
        cnt_o = np.ones(len(m.ls), np.int64)
        dl = 0                                                    # running dense loop index
        for f in range(len(m.ls)):
            a, n = m.ls[f], m.lt[f]
            p = pmap.get(f)
            if p is None or p['merge']:
                ls.append([nl_])
                lv.append(m.lv[a:a + n])
                mi.append([m.mi[f]])
                sm.append([m.sm[f]])
                if m.uv is not None:
                    uv.append(m.uv[a:a + n])
                if f in flat:
                    r = np.full(n, flat[f])
                elif p is None:
                    r = ao[dl:dl + n]
                else:
                    nu, nv = p['grid']
                    r = p['ao'][[0, nu, p['k'] - 1, nv * (nu + 1)]]
                col.append(np.column_stack((r, dep[a:a + n], along[a:a + n], np.ones(n))))
                edg.append(edge[a:a + n])
                sa.append(np.full(n, flat_sun[f]) if f in flat else sun[dl:dl + n] if p is None
                          else p['sun'][[0, nu, p['k'] - 1, nv * (nu + 1)]])
                nl_ += n
            else:
                nu, nv = p['grid']                                # the coarser grid on a subset of the nodes
                iu, jv = p['sub']
                sel = (jv[:, None] * (nu + 1) + iu[None, :]).ravel()
                cu = len(iu)
                i, j = np.meshgrid(np.arange(cu - 1), np.arange(len(jv) - 1))
                i, j = i.ravel(), j.ravel()
                F = np.stack((j * cu + i, j * cu + i + 1, (j + 1) * cu + i + 1, (j + 1) * cu + i), 1)
                Ws = p['W'][sel]
                co.append(d.co[p['v0'] + sel])
                ls.append(nl_ + 4 * np.arange(len(F)))
                lv.append(F.ravel() + nv_)
                mi.append([m.mi[f]] * len(F))
                sm.append([False] * len(F))
                loc = F.ravel()
                if m.uv is not None:
                    uv.append((Ws @ m.uv[a:a + n])[loc])
                col.append(np.column_stack((p['ao'][sel][loc], (Ws @ dep[a:a + n])[loc], (Ws @ along[a:a + n])[loc],
                                            np.ones(F.size))))
                edg.append((Ws @ edge[a:a + n])[loc])
                sa.append(p['sun'][sel][loc])
                cnt_o[f] = len(F)
                nv_ += len(sel)
                nl_ += F.size
            dl += n if p is None else p['faces'].size
        out = _Mesh(np.vstack(co), np.concatenate(ls).astype(np.int64), np.concatenate(lv).astype(np.int64),
                    np.concatenate(mi), np.concatenate(sm).astype(bool), np.vstack(uv) if m.uv is not None else None)
        col = np.vstack(col)
        col[:, 3] = np.concatenate(sa)
        cow = out.co @ R3.T + T3
        h = cow[:, 2] - _ground(cow[:, 0], cow[:, 1])
        hl = h[out.lv]
        # the ground under a face that looks down, within reach and in the building's shade (the open side of
        # each output face is its original face's)
        nfo = out.normals(cow)
        own_o = np.repeat(np.arange(len(m.ls)), cnt_o)
        nz = nfo[out.lf, 2] * sign[own_o[out.lf]]
        down = np.clip(-nz, 0, 1) * (1 - np.clip(hl / AO_DIST, 0, 1) ** 2)
        col[:, 0] = np.minimum(col[:, 0], 1 - DOWN_W * down)
        # no finer than each channel needs: the GLB keeps them as 16-bit integers, which Draco packs losslessly, and
        # fewer distinct values pack smaller (occlusion in 1/64, the streak fields in 1/256)
        for c, q in enumerate(QUANT):
            col[:, c] = np.round(col[:, c] * q) / q
        leaf = np.array([_is_leaf(mats[i].name) if i < len(mats) else False for i in range(max(len(mats), 1))])
        edg = np.vstack(edg)
        if leaf.any():
            lf = leaf[np.minimum(out.mi[out.lf], len(leaf) - 1)]
            col[lf] = _own_colour(ob.data, out.lv[lf])
            edg[lf] = EDGE_RANGE
        old = ob.data
        ob.data = out.write(old.name, mats, col, edg)
        bpy.data.meshes.remove(old)
        nv0 += len(m.co)
        npatch += len(patches)
        nmerge += sum(p['merge'] for p in patches)
        nv1 += len(out.co)
    print('bake: %d objects, vertices %d -> %d, %d large faces split (%d merged back), split %.1fs, Cycles %.1fs, '
          'assemble %.1fs' % (len(objs), nv0, nv1, npatch, nmerge, t1 - t0, t2 - t1, time.time() - t2))
