"""정문 밖 (campus.json `town`, tools/gate_town.py; reference/고증/4.8_정문_밖.md): 성산로's kerbs, lane paint and bus
shelters, the 경의선's bank with its two tracks and the bridge over 연세로, and the low town south of it.

The town's houses are boxes drawn with one atlas (material `town_far`, tools/make_textures.py town_atlas: a band of the
texture is one storey of a wall, tiling along it), so that a thousand of them are a few draw calls; nobody walks
there.  The bank's slopes are drawn with the ground's own shading (`terrain_drape`) and walked on by the trees the
web app stands on them (web/src/main.js takes the meshes named town_bank for its ground).
1997: the 경의선 here was a diesel line (electrified with the double-tracking to 문산, 2009): no masts or wires, only
the line poles of the photos."""
import math, random
from mathutils import Vector
from common import MeshBuilder, CAMPUS, ground, ground_top

T = CAMPUS.get('town')
ATLAS = 'town_far'
NB = 8                       # bands of the atlas, top to bottom
GUARD = 6 / 1024             # kept off a band's edges (mip bleed)
B_BRICK, B_CREAM, B_GREY, B_TILE, B_SHOP, B_PLAIN, B_ROOF, B_TRACK = range(8)
BAY = 3.0                    # metres a bay (a quarter of the atlas across), and a storey
# cells of the plain band (eighths): wall colours, then gravel, concrete, the tanks' yellow and blue
P_GRAVEL, P_CONC, P_YELLOW, P_BLUE = 4, 5, 6, 7
STOREY = 3.0


def band(k):
    return 1 - (k + 1) / NB + GUARD, 1 - k / NB - GUARD


def cell_uv(k, cell, n=8):
    """a patch inside cell `cell` of n across band k: (u0, v0, u1, v1)"""
    v0, v1 = band(k)
    return (cell + 0.2) / n, v0 + 0.01, (cell + 0.8) / n, v1 - 0.01


def flat(mb, pts, k, cell, n=8):
    """a face in one plain colour: its corners spread over the cell's patch"""
    u0, v0, u1, v1 = cell_uv(k, cell, n)
    m = len(pts)
    uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)] if m == 4 else [(u0, v0), (u1, v0), ((u0 + u1) / 2, v1)][:m]
    if m > 4:
        uv = [(u0 + (u1 - u0) * (i % 2), v0 + (v1 - v0) * (i / (m - 1))) for i in range(m)]
    mb.face(pts, ATLAS, uvs=uv)


def wall(mb, a, b, z0, z1, k, rnd, bays=None):
    """one storey of wall from a to b (the outside on the right going a -> b), band k tiling along it"""
    w = math.hypot(b[0] - a[0], b[1] - a[1])
    nb = bays or max(1, round(w / BAY))
    u0 = rnd.randrange(4) / 4
    v0, v1 = band(k)
    mb.face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], ATLAS,
            uvs=[(u0, v0), (u0 + nb / 4, v0), (u0 + nb / 4, v1), (u0, v1)])


def house(mb, b, rnd):
    cx, cy, L, W, ang, base, lv, wk, roof, hip, kind, tank = b[:12]
    # (a 13th field: metres a storey, for 신촌 로터리's landmarks whose tops the 1997 photos give: the same storeys and
    # draws, taller: tools/sinchon_rotary.py LM_TOP)
    sh = b[12] if len(b) > 12 else STOREY
    c, s = math.cos(ang), math.sin(ang)
    P = lambda u, v: (cx + u * c - v * s, cy + u * s + v * c)
    q = [P(-L / 2, -W / 2), P(L / 2, -W / 2), P(L / 2, W / 2), P(-L / 2, W / 2)]        # counter-clockwise
    z = base
    for f in range(lv):
        z1 = base + 0.3 + sh * (f + 1)
        k = B_SHOP if (f == 0 and kind) else wk
        for i in range(4):
            wall(mb, q[i], q[(i + 1) % 4], z, z1, k, rnd)
        z = z1
    zt = z
    if hip == 1:                                   # a tiled hipped roof, its ridge along the long side
        o = 0.45
        e = [P(-L / 2 - o, -W / 2 - o), P(L / 2 + o, -W / 2 - o), P(L / 2 + o, W / 2 + o), P(-L / 2 - o, W / 2 + o)]
        r = max(0.0, L / 2 - W / 2)
        zr = zt + (W / 2 + o) * 0.42
        r0, r1 = P(-r, 0), P(r, 0)
        E = [(p[0], p[1], zt) for p in e]
        R0, R1 = (r0[0], r0[1], zr), (r1[0], r1[1], zr)
        flat(mb, [E[0], E[1], R1, R0], B_ROOF, roof, 4)
        flat(mb, [E[2], E[3], R0, R1], B_ROOF, roof, 4)
        flat(mb, [E[1], E[2], R1], B_ROOF, roof, 4)
        flat(mb, [E[3], E[0], R0], B_ROOF, roof, 4)
        flat(mb, [E[3], E[2], E[1], E[0]], B_PLAIN, wk)          # (the eaves from below)
        return
    if hip == 2:                                   # the church (창천교회): a gabled nave, two spires at the west front
        zr = zt + W / 2 * 0.8
        r0, r1 = P(-L / 2, 0), P(L / 2, 0)
        E = [(p[0], p[1], zt) for p in q]
        R0, R1 = (r0[0], r0[1], zr), (r1[0], r1[1], zr)
        flat(mb, [E[0], E[1], R1, R0], B_ROOF, 1, 4)
        flat(mb, [E[2], E[3], R0, R1], B_ROOF, 1, 4)
        flat(mb, [E[1], E[2], R1], B_PLAIN, 0)
        flat(mb, [E[3], E[0], R0], B_PLAIN, 0)
        # (the square tower it had: its sixteen walls still drawn from the stream, into nothing, so that the houses
        # after it keep their looks)
        scrap, tw = MeshBuilder('town_scrap'), 4.2
        t = [P(-L / 2 - tw, -tw / 2), P(-L / 2, -tw / 2), P(-L / 2, tw / 2), P(-L / 2 - tw, tw / 2)]
        for f in range(4):
            for i in range(4):
                wall(scrap, t[i], t[(i + 1) % 4], 0.0, 3.3, B_BRICK, rnd, bays=1)
        # the 1996 photos 52004 · 52006: dark brick towers at the west face's two corners, a tall slender spire on each
        # (the tops about 26 m and the tips about 39 m over the ground, against the bridge's deck in 52006: 고증 4.8)
        rt = random.Random(5240)
        tw, top, tip = 5.0, base + 26.0, base + 39.0
        for side in (-1, 1):
            u0, v0 = -L / 2, side * (W / 2 - tw / 2)
            t = [P(u0, v0 - tw / 2), P(u0 + tw, v0 - tw / 2), P(u0 + tw, v0 + tw / 2), P(u0, v0 + tw / 2)]
            zz, nf = base, 8
            for f in range(nf):
                z1 = base + (top - base) * (f + 1) / nf
                for i in range(4):
                    if f < nf - 1:
                        wall(mb, t[i], t[(i + 1) % 4], zz, z1, B_BRICK, rt, bays=1)
                    else:                          # the belfry: plain dark brick
                        a_, b_ = t[i], t[(i + 1) % 4]
                        flat(mb, [(a_[0], a_[1], zz), (b_[0], b_[1], zz), (b_[0], b_[1], z1), (a_[0], a_[1], z1)], B_PLAIN, 0)
                zz = z1
            tc = P(u0 + tw / 2, v0)
            for i in range(4):
                flat(mb, [(t[i][0], t[i][1], top), (t[(i + 1) % 4][0], t[(i + 1) % 4][1], top), (tc[0], tc[1], tip)], B_ROOF, 1, 4)
        return
    flat(mb, [(p[0], p[1], zt) for p in q], B_ROOF, roof, 4)
    if lv >= 3 and rnd.random() < 0.55:            # the stair head
        hx, hy = rnd.uniform(-L / 4, L / 4), rnd.uniform(-W / 5, W / 5)
        h = [P(hx - 1.6, hy - 1.4), P(hx + 1.6, hy - 1.4), P(hx + 1.6, hy + 1.4), P(hx - 1.6, hy + 1.4)]
        for i in range(4):
            flat(mb, [(h[i][0], h[i][1], zt), (h[(i + 1) % 4][0], h[(i + 1) % 4][1], zt), (h[(i + 1) % 4][0], h[(i + 1) % 4][1], zt + 2.4),
                      (h[i][0], h[i][1], zt + 2.4)], B_PLAIN, wk)
        flat(mb, [(p[0], p[1], zt + 2.4) for p in h], B_PLAIN, P_CONC)
    if tank and min(L, W) > 5:                     # the yellow or blue water tank of every Seoul roof
        tx, ty = P(rnd.uniform(-L / 3, L / 3), rnd.uniform(-W / 3, W / 3))
        col = P_YELLOW if rnd.random() < 0.6 else P_BLUE
        ring = [(tx + 0.8 * math.cos(a), ty + 0.8 * math.sin(a)) for a in (i * math.pi / 3 for i in range(6))]
        for i in range(6):
            a_, b_ = ring[i], ring[(i + 1) % 6]
            flat(mb, [(a_[0], a_[1], zt + 0.5), (b_[0], b_[1], zt + 0.5), (b_[0], b_[1], zt + 2.0), (a_[0], a_[1], zt + 2.0)], B_PLAIN, col)
        flat(mb, [(p[0], p[1], zt + 2.0) for p in ring], B_PLAIN, col)


def houses():
    """the town's blocks, a mesh per 300 m square (so the web app can cull them)"""
    rnd = random.Random(1997)
    cells = {}
    gone = MeshBuilder('town_gone')          # (blocks that went for 신촌 로터리's streets: b[6] = -storeys; their
    lm = {d['block'] for d in T.get('landmarks', [])}      # random looks still drawn, so the blocks after them keep
    for i, b in enumerate(T['blocks']):                    # theirs; so too the landmarks' boxes: landmarks() draws them)
        if b[6] < 0:
            house(gone, b[:6] + [-b[6]] + b[7:], rnd)
            continue
        if i in lm:
            house(gone, b, rnd)
            continue
        key = (int(b[0] // 300), int(b[1] // 300))
        mb = cells.setdefault(key, MeshBuilder('town_houses_%d_%d' % key))
        house(mb, b, rnd)
    return list(cells.values())


# ----------------------------------------------------------------------------- 신촌 로터리's corner landmarks
# tools/sinchon_rotary.py LM_SHAPE (town['landmarks']): outlines and tops from the 1997 frames 27/18 · 27/19, the looks
# from the 1995 · 1996 photos (reference/고증/4.10.2_게임에_옮긴_것.md 「로터리 모퉁이」).  Nothing here draws from a
# random stream.
def _ccw(pts):
    a = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1]))
    return pts if a > 0 else pts[::-1]


def _side(o, i):
    """side i of outline o (from o[i] to o[i + 1]): start, unit way, outward normal (right of a counter-clockwise
    outline), length"""
    p0, p1 = Vector((o[i][0], o[i][1], 0)), Vector((o[(i + 1) % len(o)][0], o[(i + 1) % len(o)][1], 0))
    L = (p1 - p0).length
    t = (p1 - p0) / L
    return p0, t, Vector((t.y, -t.x, 0)), L


def _quad(mb, a, b, z0, z1, mat, out=0.0, n=None, **kw):
    """an upright face from a to b (2D) between z0 and z1, facing right of a -> b, moved out along n by `out`"""
    if out and n is not None:
        a, b = (a[0] + n.x * out, a[1] + n.y * out), (b[0] + n.x * out, b[1] + n.y * out)
    mb.face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat, **kw)


def _flat(mb, loops, z, mat, down=False):
    """a level face over the first loop with the others as holes (mathutils' tessellation)"""
    from mathutils.geometry import tessellate_polygon
    vs = [Vector((p[0], p[1], z)) for lp in loops for p in lp]
    for tri in tessellate_polygon([[Vector((p[0], p[1], z)) for p in lp] for lp in loops]):
        q = [vs[k] for k in tri]
        up = (q[1] - q[0]).cross(q[2] - q[0]).z > 0
        if up == down:
            q = q[::-1]
        mb.face([tuple(v) for v in q], mat)


def _inset(o, d):
    """a convex outline moved in by d (its sides' lines moved, met again)"""
    S = [_side(o, i) for i in range(len(o))]
    out = []
    for i in range(len(o)):
        p0, t0, n0, _ = S[i - 1]
        p1, t1, n1, _ = S[i]
        a, b = p0 - n0 * d, p1 - n1 * d
        den = t0.x * t1.y - t0.y * t1.x
        s = ((b.x - a.x) * t1.y - (b.y - a.y) * t1.x) / den
        out.append((a.x + t0.x * s, a.y + t0.y * s))
    return out


def _arc(c, r, a0, a1, n):
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * k / n), c[1] + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


def _roof_boxes(mb, d, z):
    for x, y, L, W, ang, h in d.get('boxes', []):
        mb.box((x, y, z + h / 2), (L, W, h), 'plaster_white', rotz=ang, mats={'top': 'roof_flat'}, skip=('bottom',))
    for x, y, r, h in d.get('tanks', []):
        mb.cylinder((x, y), r, z, z + h, 'metal', seg=12)


def _grace(mb, d):
    """그레이스백화점 (1992): a white-tiled box with a parapet round its roof; the south-east corner cut back from the
    second floor to the roof for a round green glass shaft under the parapet's band; five steel pipes with crowns up
    the east face and three square frames over each; three green window bands on the south face by the corner; the
    shop windows round the ground floor (52097 · 52130 · 52114)"""
    o, base, top, deck = _ccw([tuple(p) for p in d['outline']]), d['base'], d['top'], d['deck']
    k, cut = d['glass']
    zg0, zg1 = base + 7.6, deck                       # (the shaft: over the entrance's two floors, up to the roof)
    pc = Vector((o[k][0], o[k][1], 0))
    _, tin, _, _ = _side(o, k - 1)
    _, tout, _, _ = _side(o, k)
    A, B = pc - tin * cut, pc + tout * cut              # (where the cut leaves each face)
    for i in range(len(o)):
        p0, t, n, L = _side(o, i)
        a, b = o[i], o[(i + 1) % len(o)]
        _quad(mb, a, b, base, base + 0.4, 'tile_white')
        _quad(mb, a, b, base + 0.4, base + 5.2, 'glass', panes=(max(1, round(L / 3.2)), 1)) if i in (k - 1, k) else \
            _quad(mb, a, b, base + 0.4, base + 5.2, 'tile_white')
        _quad(mb, a, b, base + 5.2, zg0, 'tile_white')
        _quad(mb, a, b, zg1, top, 'tile_white')
        if i == k - 1:
            _quad(mb, a, (A.x, A.y), zg0, zg1, 'tile_white')
        elif i == k:
            _quad(mb, (B.x, B.y), b, zg0, zg1, 'tile_white')
        else:
            _quad(mb, a, b, zg0, zg1, 'tile_white')
    # the glass shaft: an arc from A to B bowing out towards the corner, 1.2 m short of it
    M = (A + B) / 2
    c_ = (B - A).length
    s_ = (pc - M).length - 1.2
    R = (c_ * c_ / 4 + s_ * s_) / (2 * s_)
    w = (pc - M).normalized()
    C = M - w * (R - s_)
    a0, a1 = math.atan2(A.y - C.y, A.x - C.x), math.atan2(B.y - C.y, B.x - C.x)
    a1 = a0 + (a1 - a0 + math.pi) % (2 * math.pi) - math.pi      # (the short way round C, through the bow)
    arc = _arc((C.x, C.y), R, a0, a1, 8)
    fl = max(1, round((zg1 - zg0) / 4.6))
    for p, q in zip(arc[:-1], arc[1:]):
        _quad(mb, p, q, zg0, zg1, 'glass_green', panes=(1, fl), smooth='grace_glass')
    rec = [(A.x, A.y), (pc.x, pc.y), (B.x, B.y)] + arc[::-1][1:-1]
    _flat(mb, [rec], zg0, 'tile_white')
    _flat(mb, [rec], zg1, 'tile_white', down=True)
    # the line under the top storey's band (52097), the parapet and the roof inside it, the cooling towers along its
    # north side
    for i in range(len(o)):
        p0, t, n, L = _side(o, i)
        a, b = o[i], o[(i + 1) % len(o)]
        _quad(mb, a, b, zg1 - 0.35, zg1, 'plaster_grey', out=0.06, n=n)
    inn = _inset(o, d['parapet'])
    _flat(mb, [o, inn[::-1]], top, 'concrete')
    for i in range(len(inn)):
        _quad(mb, inn[(i + 1) % len(inn)], inn[i], deck, top, 'tile_white')
    _flat(mb, [inn], deck, 'roof_flat')
    _roof_boxes(mb, d, deck)
    # the east face: pipes, crowns, the frames over them
    p0, t, n, L = _side(o, d['pipes'])
    for j in range(5):
        s = cut + (L - cut) * (j + 1) / 6
        q = p0 + t * s
        a, b = q - t * 0.5, q + t * 0.5
        zp0, zp1 = base + 12.0, top - 15.6
        _quad(mb, (a.x, a.y), (b.x, b.y), zp0, zp1, 'trim_black', out=0.03, n=n)
        e = q + n * 0.6
        mb.cylinder((e.x, e.y), 0.26, zp0, zp1, 'chrome', seg=8, cap_top=False)
        mb.cylinder((e.x, e.y), 0.26, zp1, zp1 + 1.5, 'metal_dark', seg=8, r1=0.85)
        for zc in (top - 5.6, top - 9.0, top - 12.4):
            for (u0, u1, v0, v1) in ((-1.3, 1.3, 0.95, 1.3), (-1.3, 1.3, -1.3, -0.95), (-1.3, -0.95, -0.95, 0.95), (0.95, 1.3, -0.95, 0.95)):
                g0, g1 = q + t * u0, q + t * u1
                _quad(mb, (g0.x, g0.y), (g1.x, g1.y), zc + v0, zc + v1, 'plaster_grey', out=0.04, n=n)
    # the south face by the corner: three green window bands, the round red mark under the parapet's top
    p0, t, n, L = _side(o, d['bands'])
    for zc in (top - 11.5, top - 15.0, top - 18.5):
        a, b = p0 + t * (L - cut - 9.5), p0 + t * (L - cut - 1.0)
        _quad(mb, (a.x, a.y), (b.x, b.y), zc - 1.1, zc + 1.1, 'glass_green', out=0.03, n=n, panes=(5, 1))
    q = p0 + t * (L - 3.0) + n * 0.06
    ring = [(q.x + t.x * 1.5 * math.cos(a_), q.y + t.y * 1.5 * math.cos(a_), top - 2.3 + 1.5 * math.sin(a_))
            for a_ in (i * math.pi / 6 for i in range(12))]
    mb.face(ring, 'banner_red')


def _grand(mb, d):
    """그랜드백화점 (1994; 그랜드마트 신촌점 on its sign by 1996): white tile round its outline with the round north-east
    face, the top floor a ring round a roof garden; shop windows round the ground floor, the video screen on the round
    face, a dark glass strip up the south end of the south-east face (52114 · 52119 · 52135)"""
    o, base, top, deck = _ccw([tuple(p) for p in d['outline']]), d['base'], d['top'], d['deck']
    court = _ccw([tuple(p) for p in d['court']])
    # (the round faces shaded smooth: a run of sides between corners that turn 45 deg or more)
    m = len(o)

    def turn(i):
        a, b, c = o[i - 1], o[i], o[(i + 1) % m]
        d_ = math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(b[1] - a[1], b[0] - a[0])
        return abs((d_ + math.pi) % (2 * math.pi) - math.pi)
    run, tags = 0, []
    for i in range(m):
        if turn(i) >= math.radians(45):
            run += 1
        tags.append('grand%d' % run)
    for i in range(m):
        p0, t, n, L = _side(o, i)
        a, b = o[i], o[(i + 1) % m]
        _quad(mb, a, b, base, base + 0.4, 'stone_granite', smooth=tags[i])
        _quad(mb, a, b, base + 0.4, base + 5.0, 'glass', panes=(max(1, round(L / 3.2)), 1), smooth=tags[i])
        _quad(mb, a, b, base + 5.0, top, 'tile_grand', smooth=tags[i])
    _flat(mb, [o, court[::-1]], top, 'roof_flat')
    for i in range(len(court)):
        _quad(mb, court[(i + 1) % len(court)], court[i], deck, top, 'tile_grand')
    _flat(mb, [court], deck, 'roof_flat')
    side, w, h, below = d['screen']
    p0, t, n, L = _side(o, side)
    q = p0 + t * (L / 2) + n * 0.7
    zc = top - below
    mb.box((q.x, q.y, zc), (w + 0.6, 0.5, h + 0.6), 'metal_dark', rotz=math.atan2(t.y, t.x))
    a, b = q - t * (w / 2) + n * 0.26, q + t * (w / 2) + n * 0.26
    mb.face([(a.x, a.y, zc - h / 2), (b.x, b.y, zc - h / 2), (b.x, b.y, zc + h / 2), (a.x, a.y, zc + h / 2)], 'glass_car')
    side, s, w = d['strip']
    p0, t, n, L = _side(o, side)
    a, b = p0 + t * (s - w / 2), p0 + t * (s + w / 2)
    _quad(mb, (a.x, a.y), (b.x, b.y), base + 5.4, top - 1.2, 'glass', out=0.03, n=n, panes=(1, round((top - base - 6.6) / 4.5)))
    # (2026-11-16) what 1996's photos have on the round face (52135 · 52119, 52095 in 1995; 고증 4.10.7): the red mark
    # and 「그랜드마트 신촌점」 straight on the tiles over the screen, the sale banners down it either side, the poster
    # under the screen, the dark green fascia over the shop windows
    p0, t, n, L = _side(o, d['screen'][0])
    _board(mb, p0 + t * (L / 2), t, n, top - 4.8, 15.0, 15.0 * 330 / 1024, 'gm_logo', off=1.1, rim=None)
    for side_, piece in d.get('banners', []):
        p0, t, n, L = _side(o, side_)
        _board(mb, p0 + t * (L / 2), t, n, top - 9.6, 1.7, 11.0, piece, off=0.3, rim=None)
    if d.get('poster'):
        side_, w_, h_, below = d['poster']
        p0, t, n, L = _side(o, side_)
        _board(mb, p0 + t * (L / 2), t, n, top - below, w_, h_, 'gm_poster', off=0.6)
    for i in d.get('fascia', []):
        p0, t, n, L = _side(o, i)
        _board(mb, p0 + t * (L / 2), t, n, base + 5.6, L + 0.1, 1.0, 'gm_fascia', off=0.3, rim=None)
    # the cooling towers' screen on the roof's south end (tools/sinchon_rotary.py GRAND_PEN; 52119 · 31662): a white box
    # open to the sky, a blue band round its foot, standing out over a foot set back under it; the towers inside and
    # beside it
    pen = d.get('pen')
    if pen:
        po = _ccw([tuple(p) for p in pen['outline']])
        zb0, zb1, zt = top + pen['band'][0], top + pen['band'][1], top + pen['top']
        foot, inn = _inset(po, 1.05), _inset(po, pen['wall'])
        for i in range(len(po)):
            a, b = po[i], po[(i + 1) % len(po)]
            _quad(mb, foot[i], foot[(i + 1) % len(po)], top, zb0, 'plaster_grey')
            _quad(mb, a, b, zb0, zb1, 'paint_blue')
            _quad(mb, a, b, zb1, zt, 'tile_white')
            _quad(mb, inn[(i + 1) % len(po)], inn[i], top + 0.05, zt, 'plaster_grey')
        _flat(mb, [po, foot[::-1]], zb0, 'plaster_grey', down=True)
        _flat(mb, [po, inn[::-1]], zt, 'concrete')
        _flat(mb, [inn], top + 0.05, 'roof_flat')
        for x, y, r, h in pen['towers']:
            mb.cylinder((x, y), r, deck, top + h, 'metal', seg=16, mat_cap='metal_dark')
            mb.cylinder((x, y), r * 1.06, top + h - 0.5, top + h - 0.3, 'paint_white', seg=16, cap_top=False)
        _roof_boxes(mb, pen, top)


def _kexim(mb, d):
    """외환은행 (아주생명보험's building): black glass, a dark band under each storey's windows, a solid dark band at
    the top with the signs; a pale fascia over the ground floor's bank; the machine room, stair head and tank on the
    roof (52108 · 52119 · 52135)"""
    o, base, top = _ccw([tuple(p) for p in d['outline']]), d['base'], d['top']
    nf = d['floors']
    z1, ztb = base + 0.3 + 4.2, top - 2.8
    hf = (ztb - z1 - 0.7) / (nf - 1)
    for i in range(len(o)):
        p0, t, n, L = _side(o, i)
        a, b = o[i], o[(i + 1) % len(o)]
        cols = max(1, round(L / 1.6))
        _quad(mb, a, b, base, base + 0.3, 'trim_black')
        _quad(mb, a, b, base + 0.3, z1, 'glass', panes=(max(1, round(L / 3.0)), 1))
        _quad(mb, a, b, z1, z1 + 0.7, 'paint_white')
        for f in range(nf - 1):
            zf = z1 + 0.7 + hf * f
            _quad(mb, a, b, zf, zf + hf * 0.36, 'trim_black')
            _quad(mb, a, b, zf + hf * 0.36, zf + hf, 'glass', panes=(cols, 1))
        _quad(mb, a, b, ztb, top, 'trim_black')
    _flat(mb, [o], top, 'roof_flat')
    _roof_boxes(mb, d, top)


# ----------------------------------------------------------------------------- 연세로's mouth (2026-11-16, 고증 4.10.7)
# The boards of sign_mouth.png (tools/make_textures.py mouth_signs): each piece's rectangle in data/sign_mouth_uv.json
_MOUTH_UV = None


def _muv(name):
    global _MOUTH_UV
    if _MOUTH_UV is None:
        import json, os
        _MOUTH_UV = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'sign_mouth_uv.json')))
    return _MOUTH_UV[name]


def _board(mb, q, t, n, z, w, h, piece, off=0.12, u=(0.0, 1.0), rim='metal_dark'):
    """a flat board of sign_mouth on a wall: its middle at q (2D) z, along t, facing n, w x h, `off` out from the
    wall (the edges dark between); u: the part of the piece's width it shows (a band laid over several sides)"""
    u0, v0, u1, v1 = _muv(piece)
    ua, ub = u0 + (u1 - u0) * u[0], u0 + (u1 - u0) * u[1]
    c = Vector((q[0], q[1], 0)) + n * off
    a, b = c - t * (w / 2), c + t * (w / 2)
    mb.face([(a.x, a.y, z - h / 2), (b.x, b.y, z - h / 2), (b.x, b.y, z + h / 2), (a.x, a.y, z + h / 2)], 'sign_mouth',
            uvs=[(ua, v0), (ub, v0), (ub, v1), (ua, v1)])
    if off > 0.03 and rim:
        a0, b0 = a - n * off, b - n * off
        _quad(mb, (a0.x, a0.y), (a.x, a.y), z - h / 2, z + h / 2, rim)
        _quad(mb, (b.x, b.y), (b0.x, b0.y), z - h / 2, z + h / 2, rim)
        mb.face([(a0.x, a0.y, z + h / 2), (a.x, a.y, z + h / 2), (b.x, b.y, z + h / 2), (b0.x, b0.y, z + h / 2)], rim)
        mb.face([(a.x, a.y, z - h / 2), (a0.x, a0.y, z - h / 2), (b0.x, b0.y, z - h / 2), (b.x, b.y, z - h / 2)], rim)


def _upright(mb, q, n, z0, z1, out, piece, th=0.16):
    """a board standing out from a wall at q (2D) along its outward way n, `out` m, from z0 to z1, both faces
    reading down (sign_mouth's upright pieces)"""
    t = Vector((-n.y, n.x, 0))
    u0, v0, u1, v1 = _muv(piece)
    P = lambda a, b, z: (q[0] + n.x * a + t.x * b, q[1] + n.y * a + t.y * b, z)
    a0, a1 = 0.1, 0.1 + out
    mb.face([P(a1, th, z0), P(a0, th, z0), P(a0, th, z1), P(a1, th, z1)], 'sign_mouth', uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    mb.face([P(a0, -th, z0), P(a1, -th, z0), P(a1, -th, z1), P(a0, -th, z1)], 'sign_mouth', uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    mb.face([P(a1, -th, z0), P(a1, th, z0), P(a1, th, z1), P(a1, -th, z1)], 'metal_dark')
    mb.face([P(a0, -th, z1), P(a1, -th, z1), P(a1, th, z1), P(a0, th, z1)], 'metal_dark')
    mb.face([P(a0, th, z0), P(a1, th, z0), P(a1, -th, z0), P(a0, -th, z0)], 'metal_dark')
    for zz in (z0 + 0.3, z1 - 0.3):                   # (its two brackets to the wall)
        mb.box((q[0] + n.x * 0.06, q[1] + n.y * 0.06, zz), (0.12, 0.08, 0.08), 'metal_dark', rotz=math.atan2(n.y, n.x))


def _kumkang(mb, d):
    """금강제화 (52206 · 52006, 1996.6 - 8): four storeys of pale grey tile along 양화로, the shoe shop's windows round
    the ground floor under its white band (the maroon arch with 「금강제화」, 「Kumkang」), three floors of window bands
    between pilasters, the clinics' and academies' boards over the windows of the top two, the red-and-white upright
    on the corner over 연세로, a round drum on the roof's west end and a dark steel frame on its east half"""
    o, base, top = _ccw([tuple(p) for p in d['outline']]), d['base'], d['top']
    zg, zb = base + 3.1, base + 4.6                       # (the shop windows' head, the band's top: the first floor's)
    zp = top - 0.9                                        # (the parapet's foot)
    hf = (zp - zb) / 3
    sides = [_side(o, i) for i in range(len(o))]
    front = lambda n: n.y < -0.55 or n.x > 0.7            # (양화로's face and 연세로's)
    for i, (p0, t, n, L) in enumerate(sides):
        a, b = o[i], o[(i + 1) % len(o)]
        if front(n) and L > 1.5:
            _quad(mb, a, b, base, base + 0.35, 'stone_granite')
            _quad(mb, a, b, base + 0.35, zg, 'glass', panes=(max(1, round(L / 2.4)), 1))
            k = max(1, round(L / 4.2))
            for j in range(k + 1):                         # (the striped piers between the windows)
                q = p0 + t * (0.35 + (L - 0.7) * j / k) + n * 0.12
                mb.box((q.x, q.y, (base + zg) / 2), (0.7, 0.24, zg - base), 'tile_white', rotz=math.atan2(t.y, t.x))
            _quad(mb, a, b, zg, zb, 'paint_white')
        else:
            _quad(mb, a, b, base, zb, 'tile_white')
        for f in range(3):                                 # (each floor: a tiled sill band, a window band, a head)
            z0 = zb + hf * f
            _quad(mb, a, b, z0, z0 + 0.95, 'tile_white')
            if L > 2.5 and (front(n) or f % 2 == 0):
                _quad(mb, a, b, z0 + 0.95, z0 + hf - 0.5, 'glass', panes=(max(1, round(L / 1.7)), 1))
            else:
                _quad(mb, a, b, z0 + 0.95, z0 + hf - 0.5, 'tile_white')
            _quad(mb, a, b, z0 + hf - 0.5, z0 + hf, 'tile_white')
        _quad(mb, a, b, zp, top, 'tile_white')
        _quad(mb, a, b, zp - 0.12, zp + 0.05, 'plaster_grey', out=0.05, n=n)
        if front(n) and L > 3.0:                           # (the pilasters up the floors)
            k = max(1, round(L / 3.4))
            for j in range(k + 1):
                q = p0 + t * (0.2 + (L - 0.4) * j / k) + n * 0.1
                mb.box((q.x, q.y, (zb + zp) / 2), (0.45, 0.2, zp - zb), 'tile_white', rotz=math.atan2(t.y, t.x))
    # the band: along the south faces as one strip (the arch where the photos have it), the east face's own
    south = [i for i, (p0, t, n, L) in enumerate(sides) if n.y < -0.55]
    run = sum(sides[i][3] for i in south)
    acc = 0.0
    for i in sorted(south, key=lambda i: (sides[i][0].x)):
        p0, t, n, L = sides[i]
        _board(mb, p0 + t * (L / 2), t, n, (zg + zb) / 2 + 0.02, L, zb - zg - 0.1, 'kk_band', off=0.25, u=(acc / run, (acc + L) / run))
        acc += L
    east = max(range(len(sides)), key=lambda i: sides[i][2].x * sides[i][3])
    p0, t, n, L = sides[east]
    _board(mb, p0 + t * (L / 2), t, n, (zg + zb) / 2 + 0.02, L, zb - zg - 0.1, 'kk_band_e', off=0.25)
    # the corner's upright over 연세로, near the south end of the east face (it runs north from p0); the boards over the top two floors' windows
    _upright(mb, p0 + t * 1.2, n, zb + 0.6, zp + 0.4, 1.0, 'kk_up')
    big = max(south, key=lambda i: sides[i][3])
    for row, (f, cells) in enumerate(((2, ('kk_b0', 'kk_b1', 'kk_b2')), (1, ('kk_b3', 'kk_b4', 'kk_b5', 'kk_b6')))):
        z = zb + hf * f + hf - 0.25
        for i in south:
            p0, t, n, L = sides[i]
            k = max(1, int(L // 4.6))
            for j in range(k):
                cell = cells[(j + i * 2 + row) % len(cells)]
                _board(mb, p0 + t * (L * (j + 0.5) / k), t, n, z, 3.9, 0.92, cell, off=0.14)
    p0, t, n, L = sides[east]
    for f, cell in ((2, 'kk_b7'), (1, 'kk_b5')):
        _board(mb, p0 + t * (L * 0.45), t, n, zb + hf * f + hf - 0.25, 3.9, 0.92, cell, off=0.14)
    # the roof: inside the parapet, the drum at its west end (34 - 35 m in the scans), the steel frame
    _flat(mb, [o], top, 'roof_flat')
    x_w = min(p[0] for p in o)
    west = [p for p in o if p[0] < x_w + 6.0]
    dc = (x_w + 3.9, sum(p[1] for p in west) / len(west))    # (the drum: 34 - 35 m at (-136 .. -130, -920 .. -926))
    mb.cylinder(dc, 2.9, top, top + 1.5, 'plaster_cream', seg=24, mat_cap='roof_cement')
    mb.cylinder(dc, 3.05, top + 1.25, top + 1.55, 'paint_white', seg=24, cap_top=False)
    e_ = max(range(len(o)), key=lambda i: o[i][0])
    fc = (o[e_][0] - 7.0, o[e_][1] + 2.0)
    for dx in (-3.2, 3.2):
        for dy in (-1.8, 1.8):
            mb.box((fc[0] + dx, fc[1] + dy, top + 0.6), (0.18, 0.18, 2.7), 'metal_dark')
    for dy in (-1.8, 1.8):
        mb.box((fc[0], fc[1] + dy, top + 1.95), (6.6, 0.16, 0.16), 'metal_dark')
    for dx in (-2.0, 0.0, 2.0):
        mb.box((fc[0] + dx, fc[1], top - 0.15), (1.3, 1.6, 1.4), 'metal_dark')


def _hongik(mb, d):
    """홍익문고 (52004 · 52006 · 52206): six storeys; the south face over the corner lot a blank wall of cream tiles
    in a grid of darker bands, a column of small windows at its east end, the white board with the green ring and the
    red 「홍익문고」 along its top; the west face on 연세로 framed in teal blue round its window bays, the black
    upright, the shop under its blue fascia"""
    o, base, top, nf = _ccw([tuple(p) for p in d['outline']]), d['base'], d['top'], d['floors']
    z1 = base + 3.6
    hf = (top - 0.4 - z1) / (nf - 1)
    for i in range(len(o)):
        p0, t, n, L = _side(o, i)
        a, b = o[i], o[(i + 1) % len(o)]
        ang = math.atan2(t.y, t.x)
        if n.x < -0.7:                                     # (연세로's face)
            _quad(mb, a, b, base, base + 0.3, 'stone_granite')
            _quad(mb, a, b, base + 0.3, z1 - 1.1, 'glass', panes=(max(1, round(L / 2.4)), 1))
            _board(mb, p0 + t * (L / 2), t, n, z1 - 0.55, L - 0.4, 0.9, 'hk_shop', off=0.18)
            _quad(mb, a, b, z1 - 1.1, z1, 'paint_blue')
            for f in range(nf - 1):
                z0 = z1 + hf * f
                _quad(mb, a, b, z0, z0 + 0.8, 'paint_blue')
                _quad(mb, a, b, z0 + 0.8, z0 + hf, 'glass', panes=(3, 1))
            _quad(mb, a, b, top - 0.4, top, 'paint_blue')
            for s_ in (0.3, L - 0.3):                      # (the teal piers at its two corners, standing out)
                q = p0 + t * s_ + n * 0.15
                mb.box((q.x, q.y, (z1 + top) / 2), (0.6, 0.3, top - z1), 'paint_blue', rotz=ang)
            _upright(mb, p0 + t * (L - 0.9), n, z1 + 1.2, z1 + 1.2 + 5.6, 1.15, 'hk_up')
            continue
        _quad(mb, a, b, base, z1, 'plaster_grey' if n.y < -0.7 else 'tile_cream')
        _quad(mb, a, b, z1, top, 'tile_cream')
        if n.y < -0.7:                                     # (the corner lot's face)
            for f in range(nf - 1):                        # (the grid's bands: each floor, three columns)
                z0 = z1 + hf * f
                _quad(mb, a, b, z0 - 0.12, z0 + 0.12, 'stone_ashlar', out=0.04, n=n)
            for s_ in (L * 0.36, L * 0.7):
                q = p0 + t * s_ + n * 0.04
                mb.box((q.x, q.y, (z1 + top - 2.8) / 2), (0.24, 0.08, top - 2.8 - z1), 'stone_ashlar', rotz=ang)
            for f in range(nf - 2):                        # (the small windows in its east column)
                q = p0 + t * (L * 0.86) + n * 0.03
                z0 = z1 + hf * f + hf * 0.45
                a_, b_ = q - t * 0.4, q + t * 0.4
                mb.face([(a_.x, a_.y, z0), (b_.x, b_.y, z0), (b_.x, b_.y, z0 + 0.85), (a_.x, a_.y, z0 + 0.85)], 'glass', panes=(2, 1))
            _board(mb, p0 + t * (L / 2), t, n, top - 1.55, L, 2.5, 'hk_top', off=0.15)
        elif n.y > 0.7 or n.x > 0.7:
            for f in range(nf - 1):
                z0 = z1 + hf * f
                q = p0 + t * (L / 2) + n * 0.03
                a_, b_ = q - t * 0.6, q + t * 0.6
                mb.face([(a_.x, a_.y, z0 + 0.9), (b_.x, b_.y, z0 + 0.9), (b_.x, b_.y, z0 + 2.2), (a_.x, a_.y, z0 + 2.2)], 'glass', panes=(2, 1))
    _flat(mb, [o], top, 'roof_flat')
    c = (sum(p[0] for p in o) / len(o), sum(p[1] for p in o) / len(o))
    mb.box((c[0] + 2.0, c[1] + 0.8, top + 1.2), (3.0, 2.6, 2.4), 'plaster_cream', mats={'top': 'concrete'})
    mb.cylinder((c[0] - 2.6, c[1] - 1.2), 0.8, top, top + 1.6, 'paint_blue', seg=10)


def _tower97(mb, d):
    """The tower going up on the corner lot south of 홍익문고 in July 1997 (엘리트 빌딩 now; 1998's 삼성증권 and
    맥도날드 신촌점): fifteen storeys of bare concrete frame up to its roof (74.5 m in the scans of 27/18 · 27/19 ·
    27/20), the slabs' edges and the columns light, the bays between them open and dark, no glass yet; the round end by
    연세로 carrying its stair drum and the ring over it; a tower crane climbing in its east part, the jib out over
    홍익문고 and 연세로 (the scans' 80 - 88 m)"""
    o, base, top, nf = _ccw([tuple(p) for p in d['outline']]), d['base'], d['top'], d['floors']
    z1 = base + 4.5
    hf = (top - z1) / (nf - 1)
    cyl = d['cyl']
    for i in range(len(o)):
        p0, t, n, L = _side(o, i)
        a, b = o[i], o[(i + 1) % len(o)]
        at = lambda s_: (p0.x + t.x * s_, p0.y + t.y * s_)
        _quad(mb, a, b, base, z1 - 0.6, 'trim_black')     # (the ground floor: open, behind the hoarding)
        _quad(mb, a, b, z1 - 0.6, z1, 'concrete')
        cols = max(1, round(L / 3.6))
        for f in range(1, nf):
            z0 = z1 + hf * (f - 1)
            ze, zs, zh = z0 + hf, z0 + 1.1, z0 + hf - 0.6
            _quad(mb, a, b, z0, zs, 'concrete')           # (the sill wall over the slab)
            _quad(mb, a, b, zh, ze, 'concrete')           # (the beam and the next slab's edge)
            for j in range(cols):                          # (the bays: a pier each side, the opening between, no glass)
                s0, s1 = L * j / cols, L * (j + 1) / cols
                if s1 - s0 < 1.6:
                    _quad(mb, at(s0), at(s1), zs, zh, 'concrete')
                    continue
                _quad(mb, at(s0), at(s0 + 0.5), zs, zh, 'concrete')
                _quad(mb, at(s0 + 0.5), at(s1 - 0.5), zs, zh, 'trim_black')
                _quad(mb, at(s1 - 0.5), at(s1), zs, zh, 'concrete')
    _flat(mb, [o], top, 'roof_flat')
    h_dr, r_dr, h_ring, r_ring = d['crown']
    mb.cylinder((cyl[0], cyl[1]), r_dr, top, top + h_dr, 'concrete', seg=20, mat_cap='roof_flat')
    for k in range(6):                                     # (the ring's posts)
        a_ = 2 * math.pi * k / 6 + 0.3
        q = (cyl[0] + (r_ring - 0.4) * math.cos(a_), cyl[1] + (r_ring - 0.4) * math.sin(a_))
        mb.box((q[0], q[1], top + h_dr + (h_ring - h_dr) / 2), (0.45, 0.45, h_ring - h_dr), 'concrete')
    ring_o = _arc((cyl[0], cyl[1]), r_ring, 0.0, 2 * math.pi, 32)[:-1]
    ring_i = _arc((cyl[0], cyl[1]), r_ring - 1.1, 0.0, 2 * math.pi, 32)[:-1]
    _flat(mb, [ring_o, ring_i[::-1]], top + h_ring + 0.6, 'concrete')
    _flat(mb, [ring_o, ring_i[::-1]], top + h_ring, 'concrete', down=True)
    for lp, inward in ((ring_o, False), (ring_i, True)):
        for k in range(len(lp)):
            p, q = lp[k], lp[(k + 1) % len(lp)]
            if inward:
                p, q = q, p
            _quad(mb, p, q, top + h_ring, top + h_ring + 0.6, 'concrete', smooth='ring%d' % inward)
    # the tower crane: a lattice mast from the roof (it climbs inside the frame), the slewing deck, the cab, the A-frame,
    # the jib's triangular truss and the counter-jib with its weights, the two ties
    mx, my, brg, jib, cjib, over = d['crane']
    zt = top + over
    yel = 'paint_yellow'
    s_ = 0.8
    corners = [(mx - s_, my - s_, 0), (mx + s_, my - s_, 0), (mx + s_, my + s_, 0), (mx - s_, my + s_, 0)]
    for cx_, cy_, _ in corners:
        _bar(mb, (cx_, cy_, top - 0.5), (cx_, cy_, zt), 0.16, yel)
    zz = top
    while zz < zt - 0.5:
        z2 = min(zt, zz + 1.8)
        for k in range(4):
            (ax, ay, _), (bx, by, _) = corners[k], corners[(k + 1) % 4]
            _bar(mb, (ax, ay, z2), (bx, by, z2), 0.08, yel)
            _bar(mb, (ax, ay, zz), (bx, by, z2), 0.07, yel)
        zz = z2
    u = Vector((math.sin(math.radians(brg)), math.cos(math.radians(brg)), 0))
    v = Vector((-u.y, u.x, 0))
    ang = math.atan2(u.y, u.x)
    m0 = Vector((mx, my, 0))
    mb.box((mx, my, zt + 0.4), (2.6, 2.6, 0.8), yel, rotz=ang)
    cab = m0 + u * 1.6 + v * 1.5
    mb.box((cab.x, cab.y, zt + 1.6), (1.6, 1.4, 1.8), 'paint_white', rotz=ang)
    P = lambda along, side, z: tuple(m0 + u * along + v * side + Vector((0, 0, z)))
    for side in (-0.6, 0.6):                               # (the jib's two lower chords)
        _bar(mb, P(0.0, side, zt + 0.9), P(jib, side, zt + 0.9), 0.14, yel)
    _bar(mb, P(0.0, 0.0, zt + 2.3), P(jib, 0.0, zt + 2.3), 0.14, yel)       # (its top chord)
    k = int(jib // 2.0)
    for j in range(k):                                     # (the web: two diagonals and a strut each 2 m)
        a0, a1 = 2.0 * j, 2.0 * (j + 1)
        for side in (-0.6, 0.6):
            _bar(mb, P(a0, side, zt + 0.9), P(a1, 0.0, zt + 2.3), 0.06, yel)
        _bar(mb, P(a1, -0.6, zt + 0.9), P(a1, 0.6, zt + 0.9), 0.06, yel)
    for side in (-0.5, 0.5):                               # (the counter-jib)
        _bar(mb, P(0.0, side, zt + 0.9), P(-cjib, side, zt + 0.9), 0.24, yel)
    w_ = P(-(cjib - 2.0), 0.0, zt + 0.2)
    mb.box(w_, (3.0, 2.0, 2.0), 'concrete', rotz=ang)
    _bar(mb, (mx, my, zt + 0.8), (mx, my, zt + 6.8), 0.45, yel)            # (the A-frame's mast)
    for along, z in ((jib * 0.62, zt + 2.3), (-(cjib - 1.0), zt + 1.0)):   # (the ties to the jib and the weights' end)
        _bar(mb, (mx, my, zt + 6.8), P(along, 0.0, z), 0.06, 'metal_dark')


def _bar(mb, p, q, w, mat):
    """a thin square bar from p to q (3D), w across"""
    p, q = Vector(p), Vector(q)
    a = q - p
    if a.length < 1e-6:
        return
    a.normalize()
    r = a.cross(Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((1, 0, 0))).normalized() * (w / 2)
    s = a.cross(r).normalized() * (w / 2)
    c = [r + s, -r + s, -r - s, r - s]
    for k in range(4):
        e0, e1 = c[k], c[(k + 1) % 4]
        mb.face([tuple(p + e0), tuple(p + e1), tuple(q + e1), tuple(q + e0)], mat)


def landmarks():
    mb = MeshBuilder('town_landmarks')
    for d in T.get('landmarks', []):
        dict(grace=_grace, grand=_grand, kexim=_kexim, kumkang=_kumkang, hongik=_hongik, tower97=_tower97)[d['kind']](mb, d)
        # (its walls down from the floor, which is the front walk's, to the ground's lowest corner behind: `foot`)
        if d.get('foot', d['base']) < d['base'] - 0.02:
            o = _ccw([tuple(p) for p in d['outline']])
            for i in range(len(o)):
                _quad(mb, o[i], o[(i + 1) % len(o)], d['foot'], d['base'], 'trim_black' if d['kind'] == 'kexim' else 'tile_white')
    return mb


def signs():
    mb = MeshBuilder('town_signs')
    for x, y, z, ang, w, idx in T['signs']:
        nx, ny = math.cos(ang), math.sin(ang)          # the way the sign faces
        tx, ty = -ny, nx
        u0, v0 = (idx % 2) / 2, 1 - (idx // 2 + 1) / 8
        h = min(1.25, w / 4)
        a = (x - tx * w / 2, y - ty * w / 2)
        b = (x + tx * w / 2, y + ty * w / 2)
        mb.face([(a[0], a[1], z - h / 2), (b[0], b[1], z - h / 2), (b[0], b[1], z + h / 2), (a[0], a[1], z + h / 2)], 'sign_sinchon',
                uvs=[(u0, v0), (u0 + 0.5, v0), (u0 + 0.5, v0 + 0.125), (u0, v0 + 0.125)])
    return mb


def signs2():
    """신촌 로터리 (tools/sinchon_rotary.py): the shop signs on 연세로 south of the side streets and the landmarks' over
    their tops, sign_sinchon2 (2 x 8 cells): [x, y, z of its middle, the way it faces, width, height, cell]"""
    mb = MeshBuilder('town_signs2')
    for x, y, z, ang, w, h, idx in T.get('signs2', []):
        nx, ny = math.cos(ang), math.sin(ang)
        tx, ty = -ny, nx
        u0, v0 = (idx % 2) / 2, 1 - (idx // 2 + 1) / 8
        a = (x - tx * w / 2, y - ty * w / 2)
        b = (x + tx * w / 2, y + ty * w / 2)
        mb.face([(a[0], a[1], z - h / 2), (b[0], b[1], z - h / 2), (b[0], b[1], z + h / 2), (a[0], a[1], z + h / 2)], 'sign_sinchon2',
                uvs=[(u0, v0), (u0 + 0.5, v0), (u0 + 0.5, v0 + 0.125), (u0, v0 + 0.125)])
        # (a shallow box behind it: the sign stands off the wall)
        d = 0.18
        for p_, q_ in ((a, b),):
            pa = (p_[0] - nx * d, p_[1] - ny * d)
            pb = (q_[0] - nx * d, q_[1] - ny * d)
            for c0, c1 in ((pa, p_), (q_, pb)):
                mb.face([(c0[0], c0[1], z - h / 2), (c1[0], c1[1], z - h / 2), (c1[0], c1[1], z + h / 2), (c0[0], c0[1], z + h / 2)], 'metal_dark')
            mb.face([(p_[0], p_[1], z + h / 2), (q_[0], q_[1], z + h / 2), (pb[0], pb[1], z + h / 2), (pa[0], pa[1], z + h / 2)], 'metal_dark')
    return mb


def yro_signs():
    """연세로 (tools/sinchon_rotary.py yro_wall_signs): the signs standing out from the shops' walls up the floors, a board
    with its two faces along the street (sign_yonseiro, 8 x 2 cells over the banner's strip), dark edges.
    [x, y, z of its middle, the wall's outward way, out, height, cell]"""
    mb = MeshBuilder('town_yro_signs')
    V0 = 88 / 1024                               # (the banner's strip under the cells)
    for x, y, z, ang, w, h, cell in T.get('vsigns', []):
        ox, oy = math.cos(ang), math.sin(ang)
        tx, ty = -oy, ox
        th = 0.14
        u0, u1 = (cell % 8) / 8 + 0.004, (cell % 8 + 1) / 8 - 0.004
        v1 = 1 - (cell // 8) * (1 - V0) / 2 - 0.002
        v0 = v1 - (1 - V0) / 2 + 0.004
        P = lambda a, b, dz: (x + ox * a + tx * b, y + oy * a + ty * b, z + dz)
        zb, zt = -h / 2, h / 2
        # the face towards +t reads from the outer edge to the wall, the one towards -t from the wall out
        mb.face([P(w / 2, th, zb), P(-w / 2, th, zb), P(-w / 2, th, zt), P(w / 2, th, zt)], 'sign_yonseiro',
                uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
        mb.face([P(-w / 2, -th, zb), P(w / 2, -th, zb), P(w / 2, -th, zt), P(-w / 2, -th, zt)], 'sign_yonseiro',
                uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
        mb.face([P(w / 2, -th, zb), P(w / 2, th, zb), P(w / 2, th, zt), P(w / 2, -th, zt)], 'metal_dark')        # (outer edge)
        mb.face([P(-w / 2, -th, zt), P(w / 2, -th, zt), P(w / 2, th, zt), P(-w / 2, th, zt)], 'metal_dark')     # (top)
        mb.face([P(-w / 2, th, zb), P(w / 2, th, zb), P(w / 2, -th, zb), P(-w / 2, -th, zb)], 'metal_dark')     # (bottom)
    return mb


def yro_banner():
    """제5회 신촌문화축제's banner over 연세로 (1996.5): white cloth between two slim poles behind the kerbs, both faces
    reading right (banner_yonseiro: sign_yonseiro.png's bottom strip).  [x0, y0, x1, y1, z road, bottom, height]"""
    mb = MeshBuilder('town_yro_banner')
    b = T.get('banner')
    if not b:
        return mb
    x0, y0, x1, y1, zr, bot, hh = b
    za, zb_ = zr + bot, zr + bot + hh
    V1 = 88 / 1024 - 0.002
    mb.face([(x0, y0, za), (x1, y1, za), (x1, y1, zb_), (x0, y0, zb_)], 'banner_yonseiro',
            uvs=[(0.0, 0.002), (1.0, 0.002), (1.0, V1), (0.0, V1)])
    mb.face([(x1, y1, za), (x0, y0, za), (x0, y0, zb_), (x1, y1, zb_)], 'banner_yonseiro',
            uvs=[(0.0, 0.002), (1.0, 0.002), (1.0, V1), (0.0, V1)])
    for px, py in ((x0, y0), (x1, y1)):
        g = ground(px, py)
        mb.box((px, py, (g + zb_ + 0.4) / 2), (0.1, 0.1, zb_ + 0.4 - g), 'metal')
    return mb


def entrances():
    """2호선 신촌역's stairs down at the junction's corners: a stairwell walled on three sides to the hip with a rail on
    top, open at the end towards the street's way; the flight goes 3 m down into it; a pole with the line's green
    sign at the open end.  [x, y, the long side's way (rad), length, width, number, ground z]
    Where July 1997's scans have its roof (tools/sinchon_rotary.py ENT97; 서울연구원 52206 · 52146 · 52204): three more
    fields, the roof's length, width and its top over the walk: a flat white roof on posts over the stairwell, a black
    sign box on it at the open end; no sign pole.  town.kiosks: the eight-sided kiosk before 한일은행 (52204)."""
    mb = MeshBuilder('town_subway')
    for e in T.get('entrances', []):
        x, y, ang, L, W, no, z = e[:7]
        c, s_ = math.cos(ang), math.sin(ang)
        P = lambda u, v, dz: (x + u * c - v * s_, y + u * s_ + v * c, z + dz)
        t = 0.2
        # the walls: two long sides and the closed end (u = -L/2), 1.0 m over the walk, down 3.2 m inside
        for (u0, v0, u1, v1) in ((-L / 2, -W / 2, L / 2, -W / 2 + t), (-L / 2, W / 2 - t, L / 2, W / 2), (-L / 2, -W / 2, -L / 2 + t, W / 2)):
            cx, cy = (u0 + u1) / 2, (v0 + v1) / 2
            q = P(cx, cy, 0.0)
            mb.box((q[0], q[1], z + (1.0 - 3.2) / 2), (u1 - u0, v1 - v0, 4.2), 'curb_road', rotz=ang)
            mb.box((q[0], q[1], z + 1.06), (u1 - u0 + 0.04, max(0.08, v1 - v0) + 0.04, 0.12), 'metal_dark', rotz=ang)
        # the flight: from the walk at the open end (u = L/2) down 3 m to the closed end, 0.3 m treads
        n = 12
        for i in range(n):
            ua = L / 2 - (i + 1) * (L - t) / n
            ub = L / 2 - i * (L - t) / n
            zz = -3.0 * (i + 1) / n
            mb.face([P(ub, -W / 2 + t, zz), P(ub, W / 2 - t, zz), P(ua, W / 2 - t, zz), P(ua, -W / 2 + t, zz)][::-1], 'curb_road')
            mb.face([P(ub, -W / 2 + t, zz + 3.0 / n), P(ub, W / 2 - t, zz + 3.0 / n), P(ub, W / 2 - t, zz), P(ub, -W / 2 + t, zz)], 'curb_road')
        if len(e) > 9 and e[9]:
            RL, RW, rh = e[7:10]
            q = P(0.0, 0.0, 0.0)
            mb.box((q[0], q[1], z + rh - 0.14), (RL, RW, 0.28), 'paint_white', rotz=ang, mats={'top': 'concrete'})
            for u in (-L / 2 + 0.1, 0.0, L / 2 - 0.1):
                for v in (-W / 2 + 0.1, W / 2 - 0.1):
                    q = P(u, v, 0.0)
                    mb.box((q[0], q[1], z + (1.0 + rh - 0.28) / 2), (0.16, 0.16, rh - 0.28 - 1.0), 'paint_white', rotz=ang)
            q = P(RL / 2 - 1.3, 0.0, 0.0)
            mb.box((q[0], q[1], z + rh + 0.55), (1.0, 1.0, 1.1), 'paint_black', rotz=ang, skip=('bottom',))
            continue
        # the sign: a pole at the open end's corner, a box with the line's green
        q = P(L / 2 - 0.2, W / 2 + 0.35, 0.0)
        mb.box((q[0], q[1], z + 1.4), (0.08, 0.08, 2.8), 'metal', rotz=ang)
        mb.box((q[0], q[1], z + 2.95), (0.5, 0.16, 0.5), 'metal_green', rotz=ang)
    for x, y, r, z in T.get('kiosks', []):
        ring = lambda rr, zz, a0=math.pi / 8: [(x + rr * math.cos(a0 + k * math.pi / 4), y + rr * math.sin(a0 + k * math.pi / 4), zz) for k in range(8)]
        lo, mid, hi, top = ring(r, z), ring(r, z + 0.95), ring(r, z + 2.0), ring(r, z + 2.45)
        for k in range(8):
            j = (k + 1) % 8
            mb.face([lo[k], lo[j], mid[j], mid[k]], 'paint_white')
            mb.face([mid[k], mid[j], hi[j], hi[k]], 'glass', panes=(1, 1))
            mb.face([hi[k], hi[j], top[j], top[k]], 'paint_white')
        eave = ring(r + 0.45, z + 2.45)
        mb.face(eave[::-1], 'paint_white')
        for k in range(8):
            mb.face([eave[k], eave[(k + 1) % 8], (x, y, z + 3.5)], 'metal_green')
    return mb


# ----------------------------------------------------------------------------- the bank
def _track_y(pts, x):
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def bank():
    """The bank between the sections of campus.json town.rail (tools/gate_town.py bank_fix): the gravel top with the two
    tracks, the slopes down to their feet, a concrete wall where the foot is held up over 성산로's sidewalk; open at
    the bridge.  Named town_bank_<k>: the web app stands the banks' trees on them."""
    R = T['rail']
    S = R['sections']
    x0b, x1b = T['bridge']['x'][0], T['bridge']['x'][1]
    mbs = []
    cum = 0.0
    CH = 60
    v0, v1 = band(B_TRACK)
    for c0 in range(0, len(S) - 1, CH):
        mb = MeshBuilder('town_bank_%d' % (c0 // CH))
        for k in range(c0, min(c0 + CH, len(S) - 1)):
            a, b = S[k], S[k + 1]
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            if a[0] >= x0b - 0.05 and b[0] <= x1b + 0.05:
                cum += seg
                continue                          # (the bridge)
            ta, tb = a[11], b[11]                  # (the top at each section: level over the valley)
            pa = lambda o, z, s=a: (s[0] + s[2] * o, s[1] + s[3] * o, z)
            pb = lambda o, z, s=b: (s[0] + s[2] * o, s[1] + s[3] * o, z)
            # the top: gravel, and a strip of track along each side's line
            lines = []
            for s_ in (a, b):
                hw = s_[4]
                tr = hw - R['shoulder']
                lines.append([hw, tr + 1.6, tr - 1.6, -tr + 1.6, -tr - 1.6, -hw])
            la, lb = lines
            for i in range(5):
                q = [pa(la[i + 1], ta), pb(lb[i + 1], tb), pb(lb[i], tb), pa(la[i], ta)]
                if i in (1, 3):
                    u0, u1 = cum / (4 * BAY), (cum + seg) / (4 * BAY)
                    mb.face(q, ATLAS, uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
                else:
                    flat(mb, q, B_PLAIN, P_GRAVEL)
            # the slopes (the ground's own shading), and the wall under a held-up foot
            for side, i0 in ((1, 5), (-1, 8)):
                da, za, wa = a[i0], a[i0 + 1], a[i0 + 2]
                db, zb, wb = b[i0], b[i0 + 1], b[i0 + 2]
                if da < 0.05 and db < 0.05:
                    continue
                ea, eb = pa(side * a[4], ta), pb(side * b[4], tb)
                fa, fb = pa(side * (a[4] + da), za), pb(side * (b[4] + db), zb)
                mb.face([ea, eb, fb, fa] if side > 0 else [eb, ea, fa, fb], 'terrain_drape')
                if wa is not None or wb is not None:
                    ga = (wa if wa is not None else za) - 0.5
                    gb = (wb if wb is not None else zb) - 0.5
                    wq = [(fa[0], fa[1], ga), (fb[0], fb[1], gb), fb, fa]
                    flat(mb, wq if side < 0 else wq[::-1], B_PLAIN, P_CONC)
            cum += seg
        if mb.faces:
            mbs.append(mb)
    return mbs



def _slab(mb, p, q, w, zb, zt, cell=P_CONC, ends=True, bottom=True):
    """a box along p -> q (plan), w across, its underside zb and top zt at each end (pairs (at p, at q): a sloped one
    for a flight's cheek), every face outward, in one plain cell"""
    d = Vector((q[0] - p[0], q[1] - p[1]))
    if d.length < 1e-6:
        return
    n = Vector((-d.y, d.x)).normalized() * (w / 2)
    zb0, zb1 = zb if isinstance(zb, (tuple, list)) else (zb, zb)
    zt0, zt1 = zt if isinstance(zt, (tuple, list)) else (zt, zt)
    L = lambda c, s, z: (c[0] + n.x * s, c[1] + n.y * s, z)
    flat(mb, [L(p, -1, zt0), L(q, -1, zt1), L(q, 1, zt1), L(p, 1, zt0)], B_PLAIN, cell)                 # top
    if bottom:
        flat(mb, [L(p, 1, zb0), L(q, 1, zb1), L(q, -1, zb1), L(p, -1, zb0)], B_PLAIN, cell)
    flat(mb, [L(p, -1, zb0), L(q, -1, zb1), L(q, -1, zt1), L(p, -1, zt0)], B_PLAIN, cell)              # right side
    flat(mb, [L(q, 1, zb1), L(p, 1, zb0), L(p, 1, zt0), L(q, 1, zt1)], B_PLAIN, cell)                  # left side
    if ends:
        flat(mb, [L(p, 1, zb0), L(p, -1, zb0), L(p, -1, zt0), L(p, 1, zt0)], B_PLAIN, cell)
        flat(mb, [L(q, -1, zb1), L(q, 1, zb1), L(q, 1, zt1), L(q, -1, zt1)], B_PLAIN, cell)


def _at_x(S, x):
    """the section nearest x along the rails (campus.json town.rail.sections)"""
    return min(S, key=lambda r: abs(r[0] - x))


def yard():
    """신촌역's yard (tools/ssr97.py, the 1997 scans; 고증 4.8): the tracks besides the two main ones on its level top and
    its two island platforms, their tops PLATFORM_UP over the bed; and the wall standing on the white retaining wall
    south of the bank west of the bridge (its top 3.4 m over the bed: a noise wall, up between 1996-12 and 1997-07)"""
    R = T['rail']
    S = R['sections']
    Y = R.get('yard')
    mb = MeshBuilder('town_yard')
    v0, v1 = band(B_TRACK)
    if Y:
        for x0, x1, o in Y['tracks']:
            run = [r for r in S if x0 <= r[0] <= x1]
            cum = 0.0
            for a, b in zip(run[:-1], run[1:]):
                seg = math.hypot(b[0] - a[0], b[1] - a[1])
                pa = lambda off, s_=a: (s_[0] + s_[2] * off, s_[1] + s_[3] * off, s_[11] + 0.012)
                pb = lambda off, s_=b: (s_[0] + s_[2] * off, s_[1] + s_[3] * off, s_[11] + 0.012)
                u0, u1 = cum / (4 * BAY), (cum + seg) / (4 * BAY)
                mb.face([pa(o - 1.6), pb(o - 1.6), pb(o + 1.6), pa(o + 1.6)], ATLAS, uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
                cum += seg
        for x0, x1, oa, ob, up in Y['platforms']:
            run = [r for r in S if x0 <= r[0] <= x1]
            for i, (a, b) in enumerate(zip(run[:-1], run[1:])):
                P = lambda s_, off, z: (s_[0] + s_[2] * off, s_[1] + s_[3] * off, z)
                ta, tb = a[11] + up, b[11] + up
                ba, bb = a[11] - 0.1, b[11] - 0.1
                flat(mb, [P(a, ob, ta), P(b, ob, tb), P(b, oa, tb), P(a, oa, ta)], B_PLAIN, P_CONC)
                flat(mb, [P(a, oa, ba), P(a, oa, ta), P(b, oa, tb), P(b, oa, bb)], B_PLAIN, P_CONC)      # (its north edge)
                flat(mb, [P(b, ob, bb), P(b, ob, tb), P(a, ob, ta), P(a, ob, ba)], B_PLAIN, P_CONC)
                for s_, z_, e in ((a, ta, i == 0), (b, tb, i == len(run) - 2)):
                    if e:
                        q_ = [P(s_, oa, s_[11] - 0.1), P(s_, ob, s_[11] - 0.1), P(s_, ob, z_), P(s_, oa, z_)]
                        flat(mb, q_ if s_ is a else q_[::-1], B_PLAIN, P_CONC)
    for x0, x1, o, top in (Y or {}).get('wagons', []):      # (the covered wagons on the north siding: 1997 scans, 52044)
        a_, b_ = _at_x(S, x0), _at_x(S, x1)
        ca, cb = (x0, a_[1] + a_[3] * o), (x1, b_[1] + b_[3] * o)
        ang = math.atan2(cb[1] - ca[1], cb[0] - ca[0])
        c = ((ca[0] + cb[0]) / 2, (ca[1] + cb[1]) / 2)
        z0 = (a_[11] + b_[11]) / 2
        L = math.hypot(cb[0] - ca[0], cb[1] - ca[1]) - 0.6
        mb.box((c[0], c[1], z0 + 0.55), (L - 2.0, 2.2, 0.7), 'metal_dark', rotz=ang)
        mb.box((c[0], c[1], z0 + (0.9 + top - 0.15) / 2), (L, 2.8, top - 0.15 - 0.9), 'wagon_brown', rotz=ang)
        mb.box((c[0], c[1], z0 + top - 0.075), (L + 0.1, 2.9, 0.15), 'roof_metal', rotz=ang)
    W = R.get('wall97') or []
    for a, b in zip(W[:-1], W[1:]):
        _slab(mb, a[:2], b[:2], 0.3, (a[2] - 0.4, b[2] - 0.4), (a[3], b[3]), ends=(a is W[0] or b is W[-1]), bottom=False)
    return mb


def footbridges():
    """육교 (tools/ssr97.py, the 1997 scans; 고증 4.8): a concrete deck from sidewalk to sidewalk under a parapet, at each
    end a flight down each way along the sidewalk (an H in plan) and a pier under each landing and one mid-way"""
    mb = MeshBuilder('town_footbridges')
    for fb in T.get('footbridges', []):
        a, b = fb['a'], fb['b']
        za, zb = fb['top']
        deep, w, fw = fb['deep'], fb['w'], fb['fw']
        _slab(mb, a, b, w, (za - deep, zb - deep), (za, zb))
        d = Vector((b[0] - a[0], b[1] - a[1])).normalized()
        n = Vector((-d.y, d.x))
        for sg in (1, -1):                                   # the parapets
            o = sg * (w / 2 - 0.08)
            pa_, pb_ = (a[0] + n.x * o, a[1] + n.y * o), (b[0] + n.x * o, b[1] + n.y * o)
            _slab(mb, pa_, pb_, 0.16, (za, zb), (za + 1.1, zb + 1.1))
        tops = {}
        for p, q in fb['flights']:
            end = a if math.hypot(q[0] - a[0], q[1] - a[1]) < math.hypot(q[0] - b[0], q[1] - b[1]) else b
            zt = za if end is a else zb
            zg = ground(*p)
            rise = zt - zg
            if rise <= 0.3:
                continue
            nst = max(2, int(round(rise / 0.16)))
            dv = Vector((q[0] - p[0], q[1] - p[1]))
            L = dv.length
            dn = dv.normalized()
            for i in range(nst):                              # the steps
                f0, f1 = i / nst, (i + 1) / nst
                c0 = (p[0] + dn.x * L * f0, p[1] + dn.y * L * f0)
                c1 = (p[0] + dn.x * L * f1, p[1] + dn.y * L * f1)
                _slab(mb, c0, c1, fw, zg - 0.2 + rise * f0, zg + rise * f1, ends=True, bottom=False)
            nn = Vector((-dn.y, dn.x))
            for sg in (1, -1):                               # the cheeks and their parapets
                o = sg * (fw / 2 + 0.08)
                ca, cb = (p[0] + nn.x * o, p[1] + nn.y * o), (q[0] + nn.x * o, q[1] + nn.y * o)
                _slab(mb, ca, cb, 0.16, (zg - 0.3, zt - 0.4), (zg + 1.0, zt + 1.1))
            tops.setdefault(id(end), []).append((q, zt, end))
        for lst in tops.values():                            # the landing between a deck end's two heads, its pier
            if len(lst) < 2:
                continue
            (q0, zt, end), (q1, _, _) = lst[0], lst[1]
            _slab(mb, q0, q1, fw + 0.3, zt - deep, zt)
            c = ((q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2)
            g = ground(*c)
            mb.box((c[0], c[1], (g - 0.3 + zt - deep) / 2), (0.7, 0.7, zt - deep - g + 0.3), ATLAS)
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        g = ground(*m)
        mb.box((m[0], m[1], (g - 0.3 + (za + zb) / 2 - deep) / 2), (0.8, 0.8, (za + zb) / 2 - deep - g + 0.3), ATLAS)
    u0, vv0, u1, vv1 = cell_uv(B_PLAIN, P_CONC)
    mb.faces = [(f[0], f[1], f[2] if f[2] is not None else [(u0, vv0), (u1, vv0), (u1, vv1), (u0, vv1)][:len(f[0])], f[3]) for f in mb.faces]
    return mb


def station97():
    """옛 신촌역 역사 (tools/ssr97.py ST_*, the 1997 scans; 고증 4.8.4 「옛 신촌역 역사」): the 1920 wooden station on the
    yard's south edge.  The waiting hall under a steep gable to the forecourt, its tip folded back at both ends (a half
    hip), white boards along the gable's edges, a door under a small hood between two tall windows, a band of three
    windows and the name board above; the office west of it under a hipped roof ridged along the rails, a lean-to of
    green sheet over its front, a gable bay to the platform; cream walls over a grey plinth, dark blue-green tiles, two
    brick chimneys (서울연구원 52232 - 52250, 1996).  The outbuilding west of it on its own: a long low box of stores
    under a green sheet roof, doors along its front.  Nothing here draws from a random stream."""
    st = T.get('station97')
    mb = MeshBuilder('town_station97')
    if not st:
        return mb
    o, a, base = st['o'], math.radians(st['a']), st['base']
    ca, sa = math.cos(a), math.sin(a)
    P = lambda u, v, z: (o[0] + u * ca - v * sa, o[1] + u * sa + v * ca, base + z)
    WALL, PLINTH, ROOF, TRIM, SHEET = 'plaster_station', 'plaster_grey', 'roof_tile_teal', 'frame_white', 'metal_green'
    foot = -0.35                                          # (the walls down into the ground)

    def walls(u0, u1, v0, v1, z1, skip=()):
        """four walls of a box (counter-clockwise from the south-west corner), each with a plinth"""
        c = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        for i in range(4):
            if i in skip:
                continue
            (pu, pv), (qu, qv) = c[i], c[(i + 1) % 4]
            mb.face([P(pu, pv, 0.45), P(qu, qv, 0.45), P(qu, qv, z1), P(pu, pv, z1)], WALL)
            mb.face([P(pu, pv, foot), P(qu, qv, foot), P(qu, qv, 0.45), P(pu, pv, 0.45)], PLINTH)

    def opening(side, s0, s1, z0, z1, mat='glass', out=0.03):
        """a window or door on a wall: side (fixed coordinate, 'u' or 'v', value, outward sign), s0 .. s1 along it"""
        ax, val, sg = side
        if ax == 'v':                                     # a wall facing south (sg -1) or north (+1)
            pts = [P(s0, val + sg * out, z0), P(s1, val + sg * out, z0), P(s1, val + sg * out, z1), P(s0, val + sg * out, z1)]
            if sg > 0:
                pts = pts[::-1]
        else:                                             # facing west (sg -1) or east (+1)
            pts = [P(val + sg * out, s0, z0), P(val + sg * out, s1, z0), P(val + sg * out, s1, z1), P(val + sg * out, s0, z1)]
            if sg < 0:
                pts = pts[::-1]
        if mat == 'glass':                                # (a white frame round the glass)
            ax2 = 0.09
            if ax == 'v':
                fr = [P(s0 - ax2, val + sg * out * 0.5, z0 - ax2), P(s1 + ax2, val + sg * out * 0.5, z0 - ax2),
                      P(s1 + ax2, val + sg * out * 0.5, z1 + ax2), P(s0 - ax2, val + sg * out * 0.5, z1 + ax2)]
                if sg > 0:
                    fr = fr[::-1]
            else:
                fr = [P(val + sg * out * 0.5, s0 - ax2, z0 - ax2), P(val + sg * out * 0.5, s1 + ax2, z0 - ax2),
                      P(val + sg * out * 0.5, s1 + ax2, z1 + ax2), P(val + sg * out * 0.5, s0 - ax2, z1 + ax2)]
                if sg < 0:
                    fr = fr[::-1]
            mb.face(fr, TRIM)
        mb.face(pts, mat)

    # ------------------------------------------------------------------ the waiting hall
    h = st['hall']
    (u0, u1), (v0, v1) = h['u'], h['v']
    ze, za, fold, ov = h['eaves'], h['apex'], h['fold'], h['over']
    hw = (u1 - u0) / 2
    uc = (u0 + u1) / 2
    s = (za - ze) / hw                                    # the roof's slope
    og, dh = 0.6, 0.9                                     # the gable's overhang, how far back the folded tip runs
    zf = za - fold
    uf = fold / s
    zo = ze - s * ov                                      # (the eaves' edge, out past the wall)
    walls(u0, u1, v0, v1, ze)
    for vg, sg in ((v0, -1), (v1, 1)):                    # the gable walls up to the fold
        q = [P(u0, vg, ze), P(u1, vg, ze), P(uc + uf, vg, zf), P(uc - uf, vg, zf)]
        mb.face(q if sg < 0 else q[::-1], WALL)
    ga, gb = v0 - og, v1 + og
    for sd in (-1, 1):                                    # the two slopes
        ue = uc + sd * (hw + ov)
        q = [P(ue, ga, zo), P(ue, gb, zo), P(uc + sd * uf, gb, zf), P(uc, gb - dh - og, za), P(uc, ga + dh + og, za),
             P(uc + sd * uf, ga, zf)]
        mb.face(q[::-1] if sd < 0 else q, ROOF)
        mb.face(q if sd < 0 else q[::-1], ROOF)           # (from below)
    for vg, vr, sg in ((ga, ga + dh + og, -1), (gb, gb - dh - og, 1)):     # the folded tips
        q = [P(uc - uf, vg, zf), P(uc + uf, vg, zf), P(uc, vr, za)]
        mb.face(q if sg < 0 else q[::-1], ROOF)
        mb.face(q[::-1] if sg < 0 else q, ROOF)
        for sd in (-1, 1):                                # the white boards along the gable's edges and the fold
            _bar(mb, P(uc + sd * (hw + ov), vg - sg * 0.04, zo - 0.12), P(uc + sd * uf, vg - sg * 0.04, zf - 0.12), 0.22, TRIM)
        _bar(mb, P(uc - uf, vg - sg * 0.04, zf - 0.12), P(uc + uf, vg - sg * 0.04, zf - 0.12), 0.22, TRIM)
    _bar(mb, P(uc, ga + dh + og, za + 0.08), P(uc, gb - dh - og, za + 0.08), 0.3, ROOF)   # (the ridge's capping)
    # the front (south): a door under a hood between two tall windows, three windows in a band, the name board
    opening(('v', v0, -1), uc - 0.95, uc + 0.95, 0.12, 2.75, mat='glass')
    opening(('v', v0, -1), uc - 0.95, uc + 0.95, 2.82, 3.3)
    mb.box(P(uc, v0 - 0.45, 3.42), (2.6, 0.9, 0.14), TRIM, rotz=a)
    for du in (-2.55, 2.55):
        opening(('v', v0, -1), uc + du - 0.45, uc + du + 0.45, 0.95, 2.95)
    opening(('v', v0, -1), uc - 1.85, uc - 0.7, 4.25, 4.95)
    opening(('v', v0, -1), uc - 0.6, uc + 0.6, 4.25, 5.05)
    opening(('v', v0, -1), uc + 0.7, uc + 1.85, 4.25, 4.95)
    mb.box(P(uc, v0 - 0.06, 5.75), (2.4, 0.1, 1.05), TRIM, rotz=a)
    mb.face([P(uc - 1.15, v0 - 0.12, 5.275), P(uc + 1.15, v0 - 0.12, 5.275), P(uc + 1.15, v0 - 0.12, 6.225),
             P(uc - 1.15, v0 - 0.12, 6.225)], 'sign_station', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])   # (tools/make_textures.py)
    # the back (north, the platform): the same door, two windows
    opening(('v', v1, 1), uc - 0.95, uc + 0.95, 0.12, 2.75, mat='glass')
    for du in (-2.55, 2.55):
        opening(('v', v1, 1), uc + du - 0.45, uc + du + 0.45, 0.95, 2.95)
    for vv in (2.2, 6.8):                                 # the east side
        opening(('u', u1, 1), vv - 0.5, vv + 0.5, 0.95, 2.95)
    opening(('u', u0, -1), 0.9, 1.9, 0.95, 2.95)         # (the west side, in front of the office)
    # ------------------------------------------------------------------ the office
    f = st['office']
    (fu0, fu1), (fv0, fv1) = f['u'], f['v']
    fe, fr_, fo = f['eaves'], f['ridge'], f['over']
    fhw = (fv1 - fv0) / 2
    fvc = (fv0 + fv1) / 2
    fs = (fr_ - fe) / fhw
    fzo = fe - fs * fo
    walls(fu0, fu1, fv0, fv1, fe, skip=(1,))
    mb.face([P(fu1, fv1, 0.45), P(fu1, max(fv0, v1), 0.45), P(fu1, max(fv0, v1), fe), P(fu1, fv1, fe)][::-1], WALL)   # (east, past the hall)
    uh = fu0 - fo + (fhw + fo)                            # where the hip meets the ridge
    ux = uc - (za - fr_) / s                              # where the ridge runs into the hall's slope (the valley's top)
    gb_ = v1                                              # (north of the hall the office's roof ends at its own wall)
    zg = fr_ - fs * (gb_ - fvc)
    ug = uh - (gb_ - fvc)                                 # (the hip's line at that v)
    E0, E3 = P(fu0 - fo, fv0 - fo, fzo), P(fu0 - fo, fv1 + fo, fzo)
    R0, Rx = P(uh, fvc, fr_), P(ux, fvc, fr_)
    roof = [[E0, P(ux, fv0 - fo, fzo), Rx, R0],                                 # south, on into the hall's roof
            [P(ug, gb_, zg), P(ux, gb_, zg), Rx, R0][::-1],                     # north, as far as the hall's back
            [E3, P(ug, gb_, zg), P(fu1, gb_, zg), P(fu1, fv1 + fo, fzo)][::-1],  # north, past it
            [E3, E0, R0]]                                                       # the hip
    for q in roof:
        mb.face(q, ROOF)
        mb.face(q[::-1], ROOF)
    mb.face([P(fu1, gb_, fe), P(fu1, fv1, fe), P(fu1, gb_, zg)], WALL)          # (its end past the hall, east)
    _bar(mb, (R0[0], R0[1], R0[2] + 0.08), (Rx[0], Rx[1], Rx[2] + 0.08), 0.3, ROOF)
    for uu in (-13.4, -10.9, -8.4):                       # the front's windows, under the lean-to
        opening(('v', fv0, -1), uu - 0.6, uu + 0.6, 0.9, 2.35)
    opening(('v', fv0, -1), -6.2, -5.1, 0.12, 2.35, mat='glass')
    opening(('u', fu0, -1), fvc - 0.6, fvc + 0.6, 0.9, 2.35)
    for uu in (-13.4, -11.4, -4.9):
        opening(('v', fv1, 1), uu - 0.5, uu + 0.5, 0.9, 2.35)
    # the gable bay to the platform
    b = st['bay']
    (bu0, bu1), (bv0, bv1), br = b['u'], b['v'], b['ridge']
    bc, bhw = (bu0 + bu1) / 2, (bu1 - bu0) / 2
    bs = (br - fe) / bhw
    walls(bu0, bu1, bv0 - 0.3, bv1, fe, skip=(0,))
    q = [P(bu0, bv1, fe), P(bu1, bv1, fe), P(bc, bv1, br)]
    mb.face(q[::-1], WALL)
    vb = fvc + (fr_ - br) / fs                            # (its ridge runs back into the office's roof)
    for sd in (-1, 1):
        ue = bc + sd * (bhw + 0.3)
        q = [P(ue, vb, fe - bs * 0.3), P(ue, bv1 + 0.4, fe - bs * 0.3), P(bc, bv1 + 0.4, br), P(bc, vb, br)]
        mb.face(q[::-1] if sd < 0 else q, ROOF)
        mb.face(q if sd < 0 else q[::-1], ROOF)
        _bar(mb, P(ue, bv1 + 0.36, fe - bs * 0.3 - 0.1), P(bc, bv1 + 0.36, br - 0.1), 0.2, TRIM)
    opening(('v', bv1, 1), bc - 0.9, bc + 0.9, 0.9, 2.6)
    # the lean-to over the office's front, on three posts
    ln = st['lean']
    (lu0, lu1), (lv0, lv1), (lz1, lz0) = ln['u'], ln['v'], ln['z']
    q = [P(lu0, lv0, lz0), P(lu1, lv0, lz0), P(lu1, lv1, lz1), P(lu0, lv1, lz1)]
    mb.face(q, SHEET)
    mb.face(q[::-1], SHEET)
    for uu in (lu0 + 0.15, (lu0 + lu1) / 2, lu1 - 0.15):
        _bar(mb, P(uu, lv0 + 0.12, foot), P(uu, lv0 + 0.12, lz0), 0.1, 'metal_dark')
    # the chimneys
    for cu, cv, ct in st['chimneys']:
        c = P(cu, cv, 0.0)
        mb.box((c[0], c[1], base + (fe + ct) / 2), (0.62, 0.62, ct - fe), 'brick_red', rotz=a)
    # ------------------------------------------------------------------ the outbuilding
    n = st['annex']
    (cx, cy), L, W, ne, nr = n['c'], n['L'], n['W'], n['eaves'], n['ridge']
    Q = lambda u, v, z: (cx + u * ca - v * sa, cy + u * sa + v * ca, base + z)
    c4 = [(-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2)]
    for i in range(4):
        (pu, pv), (qu, qv) = c4[i], c4[(i + 1) % 4]
        mb.face([Q(pu, pv, 0.45), Q(qu, qv, 0.45), Q(qu, qv, ne), Q(pu, pv, ne)], WALL)
        mb.face([Q(pu, pv, foot), Q(qu, qv, foot), Q(qu, qv, 0.45), Q(pu, pv, 0.45)], PLINTH)
    for sd in (-1, 1):                                    # the gable ends
        q = [Q(sd * L / 2, -W / 2, ne), Q(sd * L / 2, W / 2, ne), Q(sd * L / 2, 0.0, nr)]
        mb.face(q if sd > 0 else q[::-1], WALL)
    ns = (nr - ne) / (W / 2)
    for sd in (-1, 1):
        q = [Q(-L / 2 - 0.3, sd * (W / 2 + 0.4), ne - ns * 0.4), Q(L / 2 + 0.3, sd * (W / 2 + 0.4), ne - ns * 0.4),
             Q(L / 2 + 0.3, 0.0, nr), Q(-L / 2 - 0.3, 0.0, nr)]
        mb.face(q if sd < 0 else q[::-1], SHEET)
        mb.face(q[::-1] if sd < 0 else q, SHEET)
    for k in range(7):                                    # doors along the front (the 1977 plan's rooms)
        uu = -L / 2 + 1.6 + k * (L - 3.2) / 6
        d = [Q(uu - 0.5, -W / 2 - 0.03, 0.1), Q(uu + 0.5, -W / 2 - 0.03, 0.1), Q(uu + 0.5, -W / 2 - 0.03, 2.2),
             Q(uu - 0.5, -W / 2 - 0.03, 2.2)]
        mb.face(d, 'wood_dark')
    return mb


def bridge():
    """The two decks over 연세로 (the 1995 photo: a concrete deck for each track on abutments faced with concrete, a row of
    piers in the middle of the road), and the abutments: the bank's own section as a wall each side of the opening.
    (The rails 10.5 m over 성산로 before the gate, tools/gate_town.py RAIL97: 9.15 m clear over 연세로; the 1996 photo
    51979 has the pier 170 px where the opening's 30 m would be 550, some 9.3 m.)"""
    R, B = T['rail'], T['bridge']
    S = R['sections']
    x0, x1 = B['x']
    # (the bed climbs east, 0.2 m across the opening: tools/gate_town.py RAIL97; each abutment at its section's top,
    # the decks from the one to the other)
    ta, tb = (min(S, key=lambda q: abs(q[0] - xb))[11] for xb in (x0, x1))
    top_at = lambda x: ta + (tb - ta) * (x - x0) / (x1 - x0)
    DEEP = 1.9 - (R['z'] - R['top'])               # the deck's underside under the bed's top
    mb = MeshBuilder('town_bridge')
    for xb, face in ((x0, 1), (x1, -1)):
        s = min(S, key=lambda q: abs(q[0] - xb))
        top = s[11]
        P = lambda o, z: (s[0] + s[2] * o, s[1] + s[3] * o, z)
        gz = min(ground(*P(o, 0)[:2]) for o in (-s[4] - s[8], 0.0, s[4] + s[5])) - 0.6
        prof = [P(s[4] + s[5], gz), P(s[4] + s[5], s[6]), P(s[4], top), P(-s[4], top), P(-s[4] - s[8], s[9]), P(-s[4] - s[8], gz)]
        # the abutment: 0.8 m proud of the bank's end, so the bank's own end face is never seen
        q = [(p[0] + face * 0.8, p[1], p[2]) for p in prof]
        flat(mb, q if face > 0 else q[::-1], B_PLAIN, P_CONC)
        for i in range(len(prof) - 1):
            a_, b_, c_, d_ = prof[i], prof[i + 1], q[i + 1], q[i]
            flat(mb, [a_, b_, c_, d_] if face > 0 else [d_, c_, b_, a_], B_PLAIN, P_CONC)
    v0, v1 = band(B_TRACK)
    for name in ('n', 's'):
        ya, yb = _track_y(R[name], x0), _track_y(R[name], x1)
        hw = 2.3                                    # (the 1996 photo 51979: a deck 2.6 m deep under its railing)
        xa, xb = x0 - 0.3, x1 + 0.3
        za, zb_ = top_at(xa), top_at(xb)            # (the bed's top at the deck's two ends)
        zs = lambda x_: za if x_ < (xa + xb) / 2 else zb_
        zb = lambda x_: zs(x_) - DEEP
        c = [(xa, ya - hw), (xb, yb - hw), (xb, yb + hw), (xa, ya + hw)]
        for i in range(4):                         # the girder's sides and ends
            p_, q_ = c[i], c[(i + 1) % 4]
            flat(mb, [(p_[0], p_[1], zb(p_[0])), (q_[0], q_[1], zb(q_[0])), (q_[0], q_[1], zs(q_[0])), (p_[0], p_[1], zs(p_[0]))],
                 B_PLAIN, P_CONC)
        flat(mb, [(p_[0], p_[1], zb(p_[0])) for p_ in c[::-1]], B_PLAIN, P_CONC)
        u1 = (xb - xa) / (4 * BAY)
        mb.face([(xa, ya - 1.6, za + 0.01), (xb, yb - 1.6, zb_ + 0.01), (xb, yb + 1.6, zb_ + 0.01), (xa, ya + 1.6, za + 0.01)], ATLAS,
                uvs=[(0, v0), (u1, v0), (u1, v1), (0, v1)])
        for sg in (-1, 1):                         # ballast shoulders and the low side walls
            y0a, y0b = ya + sg * 1.6, yb + sg * 1.6
            y1a, y1b = ya + sg * hw, yb + sg * hw
            q_ = [(xa, y0a, za), (xb, y0b, zb_), (xb, y1b, zb_), (xa, y1a, za)]
            flat(mb, q_ if sg > 0 else q_[::-1], B_PLAIN, P_GRAVEL)
            for yo, flip in ((hw, sg > 0), (hw - 0.25, sg < 0)):
                w_ = [(xa, ya + sg * yo, za), (xb, yb + sg * yo, zb_), (xb, yb + sg * yo, zb_ + 0.9), (xa, ya + sg * yo, za + 0.9)]
                flat(mb, w_[::-1] if flip else w_, B_PLAIN, P_CONC)
            flat(mb, [(xa, ya + sg * hw, za + 0.9), (xb, yb + sg * hw, zb_ + 0.9), (xb, yb + sg * (hw - 0.25), zb_ + 0.9),
                      (xa, ya + sg * (hw - 0.25), za + 0.9)][::(1 if sg < 0 else -1)], B_PLAIN, P_CONC)
        # the pier under it
        px = B['pier']
        py = _track_y(R[name], px)
        g = ground(px, py) - 0.5
        zp = top_at(px) - DEEP
        mb.box((px, py, (g + zp) / 2), (0.9, 2 * hw - 0.6, zp - g), ATLAS)
    # (the box's faces get auto UVs: put them in the concrete cell)
    u0, vv0, u1, vv1 = cell_uv(B_PLAIN, P_CONC)
    mb.faces = [(f[0], f[1], f[2] if f[2] is not None else [(u0, vv0), (u1, vv0), (u1, vv1), (u0, vv1)][:len(f[0])], f[3]) for f in mb.faces]
    return mb


def poles():
    """line poles along the north track (the 1995 photo: a wooden pole every 40 - 50 m, two cross arms; no catenary)"""
    R = T['rail']
    mb = MeshBuilder('town_poles')
    acc = 30.0
    S = R['sections']
    x0b, x1b = T['bridge']['x']
    for a, b in zip(S[:-1], S[1:]):
        acc += math.hypot(b[0] - a[0], b[1] - a[1])
        if acc < 46.0 or x0b - 6 < a[0] < x1b + 6 or not (-480 < a[0] < 420):
            continue
        acc = 0.0
        o = a[4] - 0.7
        x, y = a[0] + a[2] * o, a[1] + a[3] * o
        mb.box((x, y, a[11] + 3.6), (0.22, 0.22, 7.6), 'wood_dark')
        for dz in (6.6, 5.9):
            mb.box((x, y, a[11] + dz), (0.12, 1.7, 0.1), 'wood_dark', rotz=math.atan2(a[3], a[2]) + math.pi / 2)
    return mb


# ----------------------------------------------------------------------------- 성산로
def _ribbon(mb, pts, w, mat, dz=0.035, dash=None):
    acc = 0.0
    for p, q in zip(pts[:-1], pts[1:]):
        d = Vector((q[0] - p[0], q[1] - p[1]))
        seg = d.length
        if seg < 1e-6:
            continue
        mid = acc + seg / 2
        acc += seg
        if dash and (mid % (dash[0] + dash[1])) > dash[0]:
            continue
        n = Vector((-d.y, d.x)).normalized() * (w / 2)
        c = [(p[0] - n.x, p[1] - n.y), (q[0] - n.x, q[1] - n.y), (q[0] + n.x, q[1] + n.y), (p[0] + n.x, p[1] + n.y)]
        mb.face([(x, y, ground_top(x, y) + dz) for x, y in c], mat)


def road():
    """lane paint draped on the levelled ground (tools/gate_town.py plan), the crossing before the gate, the kerbs"""
    mb = MeshBuilder('town_road')
    for ln in T['paint']:
        pts = ln['pts']
        if ln['kind'] == 'white_dash':            # 4 m steps: every other one painted, halved
            fine = []
            for p, q in zip(pts[:-1], pts[1:]):
                fine += [p, ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)]
            _ribbon(mb, fine + [pts[-1]], ln['w'], 'paint_white', dash=(3.0, 5.0))
        else:
            _ribbon(mb, pts, ln['w'], 'paint_yellow' if ln['kind'] == 'yellow' else 'paint_white')
    for z in T['zebra']:
        (xa, ya), (xb, yb), (xc, yc), (xd, yd) = z
        n = max(1, int(max(abs(xb - xa), abs(yd - ya)) / 3.0))
        for i in range(n):
            f0, f1 = i / n, (i + 1) / n
            L = lambda f, t: (xa + (xb - xa) * f + (xd - xa) * t, ya + (yb - ya) * f + (yd - ya) * t)
            if abs(xb - xa) >= abs(yd - ya):
                c = [L(f0, 0), L(f1, 0), L(f1, 1), L(f0, 1)]
            else:
                c = [L(0, f0), L(1, f0), L(1, f1), L(0, f1)]
            c = [(x, y, ground_top(x, y) + 0.035) for x, y in c]
            a_ = (Vector(c[1]) - Vector(c[0])).cross(Vector(c[2]) - Vector(c[0]))
            mb.face(c if a_.z > 0 else c[::-1], 'paint_white')
    # granite kerbs, 0.2 m across and 0.16 m over the asphalt (u along: the joints of web/src/kerbjoints.js)
    for run in T['kerbs']:
        acc = 0.0
        for p, q in zip(run[:-1], run[1:]):
            d = Vector((q[0] - p[0], q[1] - p[1]))
            seg = d.length
            n = Vector((-d.y, d.x)).normalized() * 0.1
            zp, zq = ground_top(*p), ground_top(*q)
            for (o0, h0), (o1, h1) in (((-1, -0.05), (-1, 0.16)), ((-1, 0.16), (1, 0.16)), ((1, 0.16), (1, -0.05))):
                mb.face([(p[0] + n.x * o0, p[1] + n.y * o0, zp + h0), (q[0] + n.x * o0, q[1] + n.y * o0, zq + h0),
                         (q[0] + n.x * o1, q[1] + n.y * o1, zq + h1), (p[0] + n.x * o1, p[1] + n.y * o1, zp + h1)], 'curb_road',
                        uvs=[(acc, 0), (acc + seg, 0), (acc + seg, 0.2), (acc, 0.2)])
            acc += seg
    return mb


def stops():
    """bus shelters at the kerb west of the gate (the 1995 photo: two long green roofs on posts), a bench under each
    and the stop's round sign"""
    mb = MeshBuilder('town_stops')
    for st in T['stops']:
        x, y, ang, L = st[:4]
        roof = st[4] if len(st) > 4 else 'metal_green'     # (신촌 로터리's: pale flat roofs, tools/sinchon_rotary.py)
        c, s = math.cos(ang), math.sin(ang)
        z = ground_top(x, y)
        P = lambda u, v, dz: (x + u * c - v * s, y + u * s + v * c, z + dz)
        for u in (-L / 2 + 0.4, -L / 6, L / 6, L / 2 - 0.4):
            for v in (-0.9, 0.9):
                q = P(u, v, 1.25)
                mb.box(q, (0.09, 0.09, 2.5), 'metal_dark', rotz=ang)
        mb.box(P(0, 0, 2.56), (L, 2.5, 0.12), roof, rotz=ang)
        mb.box(P(0, 0.75, 0.43), (L - 2.0, 0.4, 0.06), 'wood_bench', rotz=ang)
        for u in (-L / 2 + 1.4, L / 2 - 1.4):
            mb.box(P(u, 0.75, 0.2), (0.08, 0.36, 0.4), 'metal_dark', rotz=ang)
        q = P(L / 2 + 1.2, -0.8, 1.3)
        mb.box(q, (0.07, 0.07, 2.6), 'metal', rotz=ang)
        mb.box(P(L / 2 + 1.2, -0.8, 2.75), (0.06, 0.6, 0.6), 'sign_blue', rotz=ang)
    return mb


def rot_dirsign():
    """신촌 로터리: the blue direction sign over 연세로's northbound lanes (tools/sinchon_rotary.py rot_dirsign, the 1996
    photo 51979): a pole on the kerb, an arm over the lanes, the panel (sign_rotary) with a dark back"""
    mb = MeshBuilder('town_rot_sign')
    ds = T.get('dirsign')
    if not ds:
        return mb
    (px, py), (cx, cy), w, h, z0 = ds['pole'], ds['c'], ds['w'], ds['h'], ds['z0']
    fx, fy = math.cos(ds['face']), math.sin(ds['face'])
    tx, ty = -fy, fx                                          # (along the panel, to its right seen from the front)
    zp = ground_top(px, py)
    top = zp + z0 + h + 0.3
    mb.box((px, py, (zp + top) / 2), (0.26, 0.26, top - zp), 'metal', rotz=ds['face'])
    # the arm from the pole out past the panel's far edge, a little behind it
    ex, ey = cx + (cx - px) / max(1e-6, math.hypot(cx - px, cy - py)) * (w / 2 + 0.3), cy + (cy - py) / max(1e-6, math.hypot(cx - px, cy - py)) * (w / 2 + 0.3)
    for dz in (z0 + h * 0.25, z0 + h * 0.75):
        mx, my = (px + ex) / 2 - fx * 0.2, (py + ey) / 2 - fy * 0.2
        mb.box((mx, my, zp + dz), (math.hypot(ex - px, ey - py), 0.14, 0.14), 'metal', rotz=math.atan2(ey - py, ex - px))
    a = (cx - tx * w / 2, cy - ty * w / 2)
    b = (cx + tx * w / 2, cy + ty * w / 2)
    z1, z2 = zp + z0, zp + z0 + h
    # (sign_rotary.png, tools/make_textures.py rot_signs: this panel its top 704 of 1024 rows, the mouth's sign the
    # 240 under it, the name plate the left 170 px of the last 80)
    V_T, V_M = 1 - 704 / 1024, 1 - 944 / 1024
    mb.face([(a[0], a[1], z1), (b[0], b[1], z1), (b[0], b[1], z2), (a[0], a[1], z2)], 'sign_rotary',
            uvs=[(0, V_T), (1, V_T), (1, 1), (0, 1)])
    d = 0.08
    a2, b2 = (a[0] - fx * d, a[1] - fy * d), (b[0] - fx * d, b[1] - fy * d)
    mb.face([(b2[0], b2[1], z1), (a2[0], a2[1], z1), (a2[0], a2[1], z2), (b2[0], b2[1], z2)], 'metal_dark')
    for p_, q_ in ((a2, a), (b, b2)):
        mb.face([(p_[0], p_[1], z1), (q_[0], q_[1], z1), (q_[0], q_[1], z2), (p_[0], p_[1], z2)], 'metal_dark')
    mb.face([(a[0], a[1], z2), (b[0], b[1], z2), (b2[0], b2[1], z2), (a2[0], a2[1], z2)], 'metal_dark')
    # over 연세로's mouth, both facing south (tools/sinchon_rotary.py MOUTH_SIGN · MOUTH_SIGNAL; 52206 · 52141 · 52140):
    # the north-west corner's pole and arm with the direction sign of three panels; the junction's name plate on the
    # north-east pole's signal arm (the pole, the arm and its heads are the web's: town.heads)
    mo = ds.get('mouth')
    if mo:
        (px, py), (x0, x1), h, z0 = mo['pole'], mo['x'], mo['h'], mo['z0']
        zp = ground_top(px, py)
        top = zp + z0 + h + 0.5
        mb.box((px, py, (zp + top) / 2), (0.26, 0.26, top - zp), 'metal')
        mb.box(((px + x1 + 0.2) / 2, py, zp + z0 + h + 0.2), (x1 + 0.2 - px, 0.16, 0.16), 'metal')
        ys = py - 0.14
        mb.face([(x0, ys, zp + z0), (x1, ys, zp + z0), (x1, ys, zp + z0 + h), (x0, ys, zp + z0 + h)], 'sign_rotary',
                uvs=[(0, V_M), (1, V_M), (1, V_T), (0, V_T)])
        mb.face([(x1, ys + 0.06, zp + z0), (x0, ys + 0.06, zp + z0), (x0, ys + 0.06, zp + z0 + h), (x1, ys + 0.06, zp + z0 + h)], 'metal_dark')
        pl = mo['plate']
        zq = ground_top(*pl['pole']) + pl['z']
        xa, xb, yq = pl['x'] - pl['w'] / 2, pl['x'] + pl['w'] / 2, pl['pole'][1] - 0.1
        mb.face([(xa, yq, zq - pl['h'] / 2), (xb, yq, zq - pl['h'] / 2), (xb, yq, zq + pl['h'] / 2), (xa, yq, zq + pl['h'] / 2)], 'sign_rotary',
                uvs=[(0, 0), (170 / 1024, 0), (170 / 1024, V_M), (0, V_M)])
        mb.face([(xb, yq + 0.04, zq - pl['h'] / 2), (xa, yq + 0.04, zq - pl['h'] / 2), (xa, yq + 0.04, zq + pl['h'] / 2), (xb, yq + 0.04, zq + pl['h'] / 2)], 'metal_dark')
    return mb


def rot_fence():
    """신촌 로터리: the fence round the empty lot at the north-east corner (tools/sinchon_rotary.py rot_fence, 52005 ·
    52006): grey panels 2.2 m high on posts every 2 m, a yellow banner along their top half facing the street"""
    mb = MeshBuilder('town_rot_fence')
    pts = T.get('rot_fence') or []
    for p, q in zip(pts[:-1], pts[1:]):
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        if L < 0.05:
            continue
        ang = math.atan2(dy, dx)
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        z = min(ground_top(*p), ground_top(*q))
        mb.box((mx, my, z + 1.1), (L, 0.06, 2.2), 'metal', rotz=ang)
        # (the banner on the street side: the street is to the right of the line's way, as rot_fence draws it)
        nx, ny = math.sin(ang), -math.cos(ang)
        mb.box((mx + nx * 0.05, my + ny * 0.05, z + 1.75), (L, 0.02, 0.8), 'paint_yellow', rotz=ang)
        mb.box((p[0], p[1], z + 1.15), (0.09, 0.09, 2.3), 'metal_dark', rotz=ang)
    return mb


def island():
    """신촌 로터리: the round island's bed as the low mound the 1997 frames have (tools/sinchon_rotary.py ISLAND_MOUND,
    campus.json town.island.mound: [its height at the middle, the radius where it meets the ground]; 고증 4.10.2 「가운데
    섬」), which the 5 m terrain grid cannot hold.  A mesh of its own named town_bank_island with the material
    terrain_drape: web/src/town.js keeps the meshes named town_bank* apart and draws them with the ground's material
    (so the bed's painted bands lie on it, web/src/terrain.js uIsland), and main.js stands on them what grows and
    stands there (the pansies, the signal pole).  Its rim dips under the ground just inside the kerb's ring"""
    mb = MeshBuilder('town_bank_island')
    I = T.get('island') or {}
    if not I.get('mound'):
        return mb
    (cx, cy), (H, R0) = I['c'], I['mound']
    n = 48
    rs = [R0 * k / 12 for k in range(13)] + [R0 + 0.25]

    def P(r, k):
        a = 2 * math.pi * k / n
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        dz = H * max(0.0, 1.0 - (r / R0) ** 2) + 0.02 if r <= R0 else -0.08
        return (x, y, ground_top(x, y) + dz)

    for k in range(n):                                   # (counter-clockwise seen from above: the faces look up)
        mb.face([P(0.0, 0), P(rs[1], k), P(rs[1], k + 1)], 'terrain_drape', smooth=True)
        for r0, r1 in zip(rs[1:-1], rs[2:]):
            mb.face([P(r0, k), P(r1, k), P(r1, k + 1), P(r0, k + 1)], 'terrain_drape', smooth=True)
    return mb


def build():
    if not T:
        return []
    return houses() + [landmarks(), signs(), signs2(), entrances(), bridge(), poles(), road(), stops(), yard(), footbridges(), station97(), rot_dirsign(), rot_fence()] + bank() + [island(), yro_signs(), yro_banner()]


# ----------------------------------------------------------------------------- the city bus
def bus():
    """A Seoul city bus of the 1990s (the 1995 photo: white buses with a coloured band on 성산로), a box with rounded
    shoulders 10.6 m long.  Car frame as blender/cars.py: +X forward, +Y left, the ground at z = 0; the band is
    `car_paint` (the web app colours it), the wheels separate objects named wheel_* with their origins on the axles.
    Returns (body MeshBuilder, [wheel MeshBuilder with .wheel_pos])."""
    mb = MeshBuilder('body')
    L, W = 10.6, 2.46
    xf, xr = L / 2, -L / 2
    hw = W / 2
    Z0, Z1, Z2, Z3, Z4, ZR = 0.42, 1.02, 1.52, 2.52, 2.86, 3.08          # skirt, band, sill, window head, cornice, roof
    sh = 0.22                                                             # the roof's rounded shoulder

    def ring(z, inset=0.0):
        return [(xf - inset, -hw + inset, z), (xf - inset, hw - inset, z), (xr + inset, hw - inset, z), (xr + inset, -hw + inset, z)]

    def skin(z0, z1, mat, i0=0.0, i1=0.0):
        a, b = ring(z0, i0), ring(z1, i1)
        for i in range(4):
            mb.face([a[i], a[(i + 1) % 4], b[(i + 1) % 4], b[i]], mat)

    skin(Z0, Z1, 'paint_white')
    skin(Z1, Z2, 'car_paint')
    skin(Z3, Z4, 'paint_white')
    skin(Z4, ZR, 'paint_white', 0.0, sh)
    mb.face(ring(ZR, sh), 'paint_white')
    mb.face(ring(Z0)[::-1], 'trim_black')
    # the window band: black pillars, the panes a little in front of them
    skin(Z2, Z3, 'trim_black', 0.02, 0.02)
    n = 8
    for sgn in (-1, 1):
        for i in range(n):
            x0 = xr + 0.55 + i * (L - 1.5) / n
            x1 = x0 + (L - 1.5) / n - 0.14
            q = [(x0, sgn * hw, Z2 + 0.1), (x1, sgn * hw, Z2 + 0.1), (x1, sgn * hw, Z3 - 0.08), (x0, sgn * hw, Z3 - 0.08)]
            mb.face(q if sgn < 0 else q[::-1], 'glass_car')
    mb.face([(xf, -hw + 0.12, Z1 + 0.32), (xf, hw - 0.12, Z1 + 0.32), (xf, hw - 0.12, Z3 - 0.05), (xf, -hw + 0.12, Z3 - 0.05)], 'glass_car')
    q = [(xr, -hw + 0.35, Z2 + 0.15), (xr, hw - 0.35, Z2 + 0.15), (xr, hw - 0.35, Z3 - 0.1), (xr, -hw + 0.35, Z3 - 0.1)]
    mb.face(q[::-1], 'glass_car')
    # the route board over the windscreen, lamps, bumpers, the two doors on the right (kerb) side
    mb.face([(xf + 0.005, -0.8, Z3 + 0.03), (xf + 0.005, 0.8, Z3 + 0.03), (xf + 0.005, 0.8, Z4 - 0.03), (xf + 0.005, -0.8, Z4 - 0.03)], 'paint_black')
    for sgn in (-1, 1):
        y0, y1 = sgn * (hw - 0.55), sgn * (hw - 0.18)
        q = [(xf + 0.005, min(y0, y1), 0.66), (xf + 0.005, max(y0, y1), 0.66), (xf + 0.005, max(y0, y1), 0.9), (xf + 0.005, min(y0, y1), 0.9)]
        mb.face(q, 'light_white')
        q = [(xr - 0.005, min(y0, y1), 0.8), (xr - 0.005, max(y0, y1), 0.8), (xr - 0.005, max(y0, y1), 1.0), (xr - 0.005, min(y0, y1), 1.0)]
        mb.face(q[::-1], 'light_red')
    mb.box((xf + 0.05, 0, 0.5), (0.14, W + 0.04, 0.2), 'trim_black')
    mb.box((xr - 0.05, 0, 0.5), (0.14, W + 0.04, 0.2), 'trim_black')
    for x0 in (xf - 1.75, -0.9):
        q = [(x0, -hw - 0.004, Z0 + 0.05), (x0 + 1.0, -hw - 0.004, Z0 + 0.05), (x0 + 1.0, -hw - 0.004, Z3 - 0.05), (x0, -hw - 0.004, Z3 - 0.05)]
        mb.face(q, 'glass_car')
        mb.box((x0 + 0.5, -hw - 0.004, (Z0 + Z3) / 2), (0.05, 0.02, Z3 - Z0 - 0.1), 'trim_black')
    wheels = []
    r, ww = 0.5, 0.3
    for name, x, sgn in (('wheel_fl', xf - 2.3, 1), ('wheel_fr', xf - 2.3, -1), ('wheel_rl', xr + 2.9, 1), ('wheel_rr', xr + 2.9, -1)):
        w = MeshBuilder(name)
        seg = 14
        ring_ = [(r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
        for i in range(seg):
            (ax, az), (bx, bz) = ring_[i], ring_[(i + 1) % seg]
            w.face([(ax, -ww / 2, az), (bx, -ww / 2, bz), (bx, ww / 2, bz), (ax, ww / 2, az)][::-1], 'rubber', smooth=True)
        for y_, flip in ((-ww / 2, False), (ww / 2, True)):
            cap = [(x_, y_, z_) for x_, z_ in ring_]
            w.face(cap[::-1] if flip else cap, 'rubber')
            hub = [(x_ * 0.55, y_ + (0.01 if flip else -0.01), z_ * 0.55) for x_, z_ in ring_]
            w.face(hub[::-1] if flip else hub, 'metal')
        w.wheel_pos = (x, sgn * (hw - ww / 2 - 0.03), r)
        wheels.append(w)
    return mb, wheels
