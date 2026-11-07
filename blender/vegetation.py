"""Procedural trees and shrubs: branch skeleton grown toward leaf clusters, alpha leaf
cards from the painted atlases, canopy-spherical custom normals and baked
vertex-colour ambient occlusion (exported as COLOR_0)."""
import math, random
from mathutils import Vector
from common import MeshBuilder

SPECIES = {
    #              height  trunk_h  crown_c  rx   rz   cards  card  groups  excurrent  bark
    'ginkgo':  dict(h=9.8, th=2.6, cz=6.0, rx=2.05, rz=4.0, n=125, card=1.35, groups=11, exc=True, bark='bark', taper=0.8),
    'zelkova': dict(h=13.0, th=3.0, cz=9.0, rx=6.0, rz=4.3, n=230, card=2.1, groups=9, exc=False, bark='bark', taper=0.15),
    'cherry':  dict(h=7.5, th=1.8, cz=5.0, rx=4.3, rz=2.7, n=170, card=1.65, groups=7, exc=False, bark='bark', taper=0.1),
    'maple':   dict(h=6.5, th=1.7, cz=4.3, rx=3.2, rz=2.5, n=120, card=1.45, groups=6, exc=False, bark='bark', taper=0.2),
    'oak':     dict(h=12.5, th=3.5, cz=8.2, rx=5.0, rz=4.2, n=190, card=2.0, groups=8, exc=False, bark='bark', taper=0.2),
    'pine':    dict(h=11.0, th=4.2, cz=8.2, rx=4.0, rz=2.9, n=250, card=2.1, groups=9, exc=True, bark='bark_pine', taper=0.35),
    # 1997's young lawn trees (issue #10; reference/1997_백양로_항공사진.jpg, May): thin, upright crowns you see the sky
    # through, a few branches reaching up from a low fork, in bright new leaves (leaf_zelkova_young keeps the light
    # April atlas into May; the young cherries keep their summer leaves, April's cherry atlas being the blossom).  Natural heights as measured in the photo (zelkova ~9 m, cherry ~5 m).
    'zelkova_young': dict(h=9.0, th=2.3, cz=6.1, rx=2.9, rz=3.2, n=85, card=1.55, groups=6, exc=False, bark='bark',
                          taper=0.15, leaf='leaf_zelkova_young', spread=0.55),
    'cherry_young':  dict(h=5.4, th=1.4, cz=3.7, rx=2.2, rz=1.8, n=62, card=1.25, groups=5, exc=False, bark='bark',
                          taper=0.1, leaf='leaf_cherry_young', spread=0.6),
    # 메타세쿼이아: the row of tall narrow conifers east of 백양로 just inside the gate (bottom right of the photo):
    # a slim cone of soft light-green sprays from low down, a straight trunk to the tip
    'metasequoia':   dict(h=13.5, th=1.2, cz=7.0, rx=2.3, rz=6.4, n=300, card=1.05, groups=14, exc=True, bark='bark',
                          taper=0.92, leaf='leaf_metasequoia'),
    # 목련 (2003_봄_교육관에서_본_연희관앞정원과_성암관.jpg, 2024_봄_언더우드관_목련.jpg): a rounded crown on a short smooth
    # grey trunk that forks low into a few rising limbs; ivory flowers on the bare wood in April (leaf_magnolia_spring)
    'magnolia': dict(h=8.0, th=1.4, cz=5.1, rx=3.4, rz=2.9, n=160, card=1.55, groups=6, exc=False, bark='bark_smooth',
                     taper=0.1, lift=0.95),
    # 은백양 (2003_봄_언더우드관정원_남쪽계단_벚나무.jpg): a tall chalk-white trunk forking at 4-5 m into a few big limbs
    # that climb steeply into an upright crown; bare in mid-April (leaf_poplar_spring: twigs and buds)
    'poplar': dict(h=17.0, th=4.4, cz=11.6, rx=4.4, rz=5.4, n=200, card=2.1, groups=5, exc=False, bark='bark_poplar',
                   taper=0.2, lift=1.35),
}


def tube(mb, pts, radii, mat, sides, rnd, col=(1, 1, 1, 1)):
    """Tapered tube along a polyline (smooth-shaded)."""
    tag = 'tube%d' % len(mb.faces)
    frames = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
        a = d.cross(up).normalized()
        b = d.cross(a).normalized()
        frames.append((p, a, b, radii[i]))
    vlen = 0.0
    for i in range(len(frames) - 1):
        p0, a0, b0, r0 = frames[i]
        p1, a1, b1, r1 = frames[i + 1]
        seglen = (p1 - p0).length
        for k in range(sides):
            t0, t1 = 2 * math.pi * k / sides, 2 * math.pi * (k + 1) / sides
            q = [p0 + (a0 * math.cos(t0) + b0 * math.sin(t0)) * r0, p0 + (a0 * math.cos(t1) + b0 * math.sin(t1)) * r0,
                 p1 + (a1 * math.cos(t1) + b1 * math.sin(t1)) * r1, p1 + (a1 * math.cos(t0) + b1 * math.sin(t0)) * r1]
            circ = 2 * math.pi * max(r0, 0.05)
            uv = [(k / sides * circ, vlen), ((k + 1) / sides * circ, vlen), ((k + 1) / sides * circ, vlen + seglen), (k / sides * circ, vlen + seglen)]
            mb.face(q, mat, uvs=uv, smooth=tag, col=col)
        vlen += seglen


def bezier(p0, p1, p2, n):
    return [p0 * (1 - t) ** 2 + p1 * 2 * t * (1 - t) + p2 * t * t for t in [i / n for i in range(n + 1)]]


def envelope(sp, z):
    """Crown radius at height z."""
    u = (z - sp['cz']) / sp['rz']
    if abs(u) >= 1:
        return 0.0
    r = sp['rx'] * math.sqrt(1 - u * u)
    if sp.get('exc'):
        r *= 1 - sp['taper'] * max(0, u) ** 1.2
    return r


def make_tree(species, seed=0, leaf_mat=None):
    sp = SPECIES[species]
    rnd = random.Random(hash((species, seed)) & 0xffffff)
    s = rnd.uniform(0.92, 1.08)
    sp = dict(sp, h=sp['h'] * s, cz=sp['cz'] * s, rz=sp['rz'] * s, rx=sp['rx'] * rnd.uniform(0.9, 1.1))
    mb = MeshBuilder(f'tree_{species}_{seed}')
    leaf_mat = leaf_mat or sp.get('leaf') or f'leaf_{species}'
    young = sp.get('spread') is not None
    C = Vector((0, 0, sp['cz']))
    # --- leaf cluster positions (biased toward the crown shell)
    cards = []
    tries = 0
    while len(cards) < sp['n'] and tries < 20000:
        tries += 1
        z = sp['cz'] + rnd.uniform(-1, 1) * sp['rz']
        r_env = envelope(sp, z)
        if r_env <= 0.2:
            continue
        a = rnd.uniform(0, 2 * math.pi)
        rr = r_env * (rnd.random() ** 0.35)
        if young and rnd.random() < 0.35:
            continue                    # (gaps: the crown is a few loose clusters, not a full dome)
        if species == 'pine':
            # flat pads: quantise heights into a few layers
            z = sp['cz'] + round((z - sp['cz']) / 1.1) * 1.1 + rnd.uniform(-0.25, 0.25)
        p = Vector((math.cos(a) * rr, math.sin(a) * rr, z))
        if z < sp['th'] + 0.6:
            continue
        cards.append(p)
    # --- trunk
    lean = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * (0.06 if species != 'pine' else 0.18)
    if species == 'metasequoia':
        lean *= 0.2
    top = sp['h'] * (0.92 if sp['exc'] else 0.55)
    if not sp['exc']:
        top = sp['th'] + 1.2
    trunk = []
    nseg = 7
    for i in range(nseg + 1):
        t = i / nseg
        z = top * t
        wob = Vector((math.sin(t * 5 + seed) * 0.12, math.cos(t * 4 + seed) * 0.12, 0)) * (2.5 if species == 'pine' else 1)
        trunk.append(Vector((0, 0, z)) + lean * z + wob * t)
    r0 = 0.11 * sp['h'] ** 0.85 / 3.0 * (1.15 if species in ('zelkova', 'oak') else 1) * (0.75 if young else 1)
    trunk_r = [r0 * (1.35 - 0.35 * min(1, i / 1.0)) * (1 - 0.75 * i / nseg) for i in range(nseg + 1)]
    tube(mb, trunk, trunk_r, sp['bark'], 8, rnd, col=(0.75, 0.75, 0.75, 1))
    # root flare
    tube(mb, [Vector((0, 0, -0.3)), Vector((0, 0, 0.35))], [r0 * 1.9, r0 * 1.15], sp['bark'], 8, rnd, col=(0.6, 0.6, 0.6, 1))

    def trunk_at(z):
        z = max(0, min(top, z))
        f = z / top * nseg
        i = min(int(f), nseg - 1)
        return trunk[i].lerp(trunk[i + 1], f - i), trunk_r[i] + (trunk_r[i + 1] - trunk_r[i]) * (f - i)
    # --- group cards into main branches by azimuth/height
    G = sp['groups']
    groups = [[] for _ in range(G)]
    for p in cards:
        az = (math.atan2(p.y, p.x) + math.pi) / (2 * math.pi)
        hz = (p.z - (sp['cz'] - sp['rz'])) / (2 * sp['rz'])
        if sp['exc']:
            gi = int(hz * G * 0.999) if species != 'pine' else int(az * G * 0.999)
            gi = (gi + int(az * 3)) % G if species != 'pine' else gi
        else:
            gi = int(az * G * 0.999)
        groups[gi].append(p)
    rng_tw = random.Random(seed + 7)
    for g in groups:
        if not g:
            continue
        cen = sum(g, Vector()) / len(g)
        if sp['exc']:
            anchor_z = min(top - 0.5, max(sp['th'], cen.z - (1.2 if species != 'pine' else 0.6)))
        else:
            anchor_z = top - rnd.uniform(0.1, 0.8)
        base, tr = trunk_at(anchor_z)
        lift = sp.get('lift', 0.6 if species != 'pine' else 0.15)
        if young:
            lift = 1.0 + sp['spread']           # branches reach up rather than out (a vase, not a dome)
        if species == 'metasequoia':
            lift = 0.05                         # short level branches round the straight stem
        mid = base.lerp(cen, 0.5) + Vector((0, 0, lift * (cen - base).length * 0.35))
        end = base.lerp(cen, 0.88)
        pts = bezier(base, mid, end, 4)
        br = max(0.04, tr * 0.62)
        tube(mb, pts, [br * (1 - 0.8 * i / 4) for i in range(5)], sp['bark'], 5, rnd, col=(0.8, 0.8, 0.8, 1))
        # twigs to a subset of cards
        for p in g:
            if rng_tw.random() < 0.35:
                q0 = end.lerp(base, rng_tw.uniform(0, 0.4))
                tube(mb, [q0, q0.lerp(p, 0.55) + Vector((0, 0, 0.2)), p], [br * 0.3, br * 0.18, 0.012], sp['bark'], 3, rnd, col=(0.85, 0.85, 0.85, 1))
    # --- leaf cards with canopy normals + AO in vertex colour
    for p in cards:
        d = (p - C)
        dn = Vector((d.x / sp['rx'], d.y / sp['rx'], d.z / sp['rz']))
        shell = min(1.0, dn.length)
        out = d.normalized() if d.length > 1e-3 else Vector((0, 0, 1))
        nrm = (out * 0.6 + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 1))) * 0.55).normalized()
        if species in ('pine', 'metasequoia'):
            nrm = (Vector((0, 0, 1)) + out * 0.5 + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * 0.8).normalized()
        up = Vector((0, 0, 1))
        tang = nrm.cross(up)
        if tang.length < 1e-3:
            tang = Vector((1, 0, 0))
        tang.normalize()
        bit = tang.cross(nrm).normalized()
        sz = sp['card'] * rnd.uniform(0.8, 1.2) * (1.0 if species != 'pine' else 1.15)
        rot = rnd.uniform(-0.6, 0.6)
        ca, sa = math.cos(rot), math.sin(rot)
        t2 = tang * ca + bit * sa
        b2 = -tang * sa + bit * ca
        h = sz / 2
        q = [p - t2 * h - b2 * h, p + t2 * h - b2 * h, p + t2 * h + b2 * h, p - t2 * h + b2 * h]
        cell = rnd.randrange(4)
        u0, v0 = (cell % 2) * 0.5, (cell // 2) * 0.5
        uv = [(u0, v0), (u0 + .5, v0), (u0 + .5, v0 + .5), (u0, v0 + .5)]
        hfac = (p.z - (sp['cz'] - sp['rz'])) / (2 * sp['rz'])
        ao = max(0.3, min(1.0, 0.35 + 0.55 * shell ** 1.5 + 0.2 * hfac))
        cols = []
        for v in q:
            dv = (v - C)
            dvn = Vector((dv.x / sp['rx'], dv.y / sp['rx'], dv.z / sp['rz'])).length
            a2 = max(0.28, min(1.0, 0.3 + 0.6 * min(1, dvn) ** 1.5 + 0.2 * hfac))
            cols.append((a2, a2, a2, 1))
        mb.face(q, leaf_mat, uvs=uv, col=cols)
        mb.faces[-1] = mb.faces[-1]
    mb.leaf_center = C
    mb.leaf_radii = (sp['rx'], sp['rz'])
    return mb


def apply_canopy_normals(ob, center, radii, leaf_mat_prefix='leaf_'):
    """Bend leaf-card normals toward the crown's spherical normal (soft foliage lighting)."""
    me = ob.data
    leaf_ids = {i for i, m in enumerate(me.materials) if m and m.name.startswith(leaf_mat_prefix)}
    normals = []
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            if poly.material_index in leaf_ids:
                d = Vector(((v.x - center.x) / radii[0], (v.y - center.y) / radii[0], (v.z - center.z) / radii[1]))
                n = (d.normalized() * 0.85 + Vector(poly.normal) * 0.15).normalized()
            else:
                n = None
            normals.append(n)
    # fill non-leaf with their computed split normals
    try:
        cn = [l.normal.copy() for l in me.loops]
    except Exception:
        me.calc_normals_split()
        cn = [l.normal.copy() for l in me.loops]
    out = [tuple(n if n is not None else cn[i]) for i, n in enumerate(normals)]
    me.normals_split_custom_set(out)


# ----------------------------------------------------------------------------- shrubs
def blob(mb, c, rx, ry, rz, mat, rnd, seg=14, rings=9, noise=0.12, core_mat=None):
    tag = 'blob%d' % len(mb.faces)
    P = []
    for j in range(rings + 1):
        th = math.pi * j / rings
        row = []
        for i in range(seg):
            ph = 2 * math.pi * i / seg
            n = 1 + noise * (math.sin(ph * 3 + j) * math.cos(th * 4 + i * 0.7))
            row.append(Vector((c[0] + rx * n * math.sin(th) * math.cos(ph), c[1] + ry * n * math.sin(th) * math.sin(ph),
                               c[2] + rz * n * math.cos(th))))
        P.append(row)
    for j in range(rings):
        for i in range(seg):
            k = (i + 1) % seg
            q = [P[j][i], P[j + 1][i], P[j + 1][k], P[j][k]]
            uv = [(i / seg * 4, j / rings * 2), (i / seg * 4, (j + 1) / rings * 2), ((i + 1) / seg * 4, (j + 1) / rings * 2), ((i + 1) / seg * 4, j / rings * 2)]
            shade = [max(0.35, min(1, 0.55 + 0.45 * (v.z - c[2]) / rz)) for v in q]
            mb.face(q, mat, uvs=uv, smooth=tag, col=[(s, s, s, 1) for s in shade])


def fluff(mb, c, rx, ry, rz, mat, rnd, n=30, size=0.55):
    for k in range(n):
        th = math.acos(rnd.uniform(-0.3, 1))
        ph = rnd.uniform(0, 2 * math.pi)
        p = Vector((c[0] + rx * math.sin(th) * math.cos(ph), c[1] + ry * math.sin(th) * math.sin(ph), c[2] + rz * math.cos(th)))
        nrm = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
        t = nrm.cross(Vector((0, 0, 1)))
        if t.length < 1e-3:
            t = Vector((1, 0, 0))
        t.normalize()
        b = t.cross(nrm)
        h = size * rnd.uniform(0.7, 1.2) / 2
        q = [p - t * h - b * h, p + t * h - b * h, p + t * h + b * h, p - t * h + b * h]
        cell = rnd.randrange(4)
        u0, v0 = (cell % 2) * 0.5, (cell // 2) * 0.5
        mb.face(q, mat, uvs=[(u0, v0), (u0 + .5, v0), (u0 + .5, v0 + .5), (u0, v0 + .5)], col=(0.95, 0.95, 0.95, 1))


def make_shrub(kind, seed=0):
    rnd = random.Random(seed + hash(kind) % 1000)
    mb = MeshBuilder(f'shrub_{kind}')
    if kind == 'topiary_round':
        blob(mb, (0, 0, 0.62), 0.75, 0.75, 0.62, 'hedge_boxwood', rnd, noise=0.05)
        fluff(mb, (0, 0, 0.62), 0.72, 0.72, 0.6, 'leaf_boxwood', rnd, n=26, size=0.35)
    elif kind == 'topiary_cone':
        tag = 'cone'
        seg, rings = 14, 8
        H, R = 2.4, 0.75
        for j in range(rings):
            for i in range(seg):
                def P(jj, ii):
                    t = jj / rings
                    r = R * (1 - t) ** 0.9 + 0.02
                    a = 2 * math.pi * ii / seg
                    return Vector((r * math.cos(a), r * math.sin(a), 0.1 + H * t))
                q = [P(j, i), P(j, i + 1), P(j + 1, i + 1), P(j + 1, i)]
                uv = [(i / seg * 3, j / rings * 3), ((i + 1) / seg * 3, j / rings * 3), ((i + 1) / seg * 3, (j + 1) / rings * 3), (i / seg * 3, (j + 1) / rings * 3)]
                s = 0.55 + 0.45 * j / rings
                mb.face(q, 'hedge_boxwood', uvs=uv, smooth=tag, col=(s, s, s, 1))
        mb.cylinder((0, 0), 0.08, 0, 0.2, 'bark', seg=6)
    elif kind == 'hedge_blob':
        blob(mb, (0, 0, 0.45), 0.95, 0.7, 0.5, 'hedge_boxwood', rnd, noise=0.12)
        fluff(mb, (0, 0, 0.45), 0.9, 0.65, 0.45, 'leaf_boxwood', rnd, n=22, size=0.35)
    elif kind == 'bush':
        blob(mb, (0, 0, 0.5), 0.8, 0.8, 0.55, 'hedge_azalea', rnd, noise=0.16)
        fluff(mb, (0, 0, 0.5), 0.8, 0.8, 0.55, 'leaf_azalea', rnd, n=34, size=0.55)
    elif kind == 'hedge_low':
        # one 1.6 m segment of the low clipped hedge along 백양로's planting strip (local x = along the hedge)
        blob(mb, (0, 0, 0.28), 0.92, 0.4, 0.3, 'hedge_boxwood', rnd, noise=0.04)
        fluff(mb, (0, 0, 0.28), 0.9, 0.38, 0.28, 'leaf_boxwood', rnd, n=14, size=0.26)
    elif kind == 'pansy_bed':
        # one 1.6 m length of the flower border along the top of the banks by the steps up to 언더우드관 정원 (the
        # 2003 spring photo: yellow pansies), a low mound of leaves and flowers (local x = along the border)
        blob(mb, (0, 0, 0.02), 0.98, 0.38, 0.13, 'hedge_pansy', rnd, noise=0.06)
        fluff(mb, (0, 0, 0.03), 0.92, 0.34, 0.11, 'leaf_pansy', rnd, n=18, size=0.3)
    elif kind == 'azalea_red':
        # 철쭉 in full bloom (red), as in the 정문 flower bed of the May 1997 photo
        blob(mb, (0, 0, 0.4), 0.8, 0.8, 0.42, 'hedge_azalea', rnd, noise=0.14)
        fluff(mb, (0, 0, 0.42), 0.86, 0.86, 0.45, 'leaf_azalea_red', rnd, n=40, size=0.45)
    return mb
