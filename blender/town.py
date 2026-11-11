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
    cx, cy, L, W, ang, base, lv, wk, roof, hip, kind, tank = b
    c, s = math.cos(ang), math.sin(ang)
    P = lambda u, v: (cx + u * c - v * s, cy + u * s + v * c)
    q = [P(-L / 2, -W / 2), P(L / 2, -W / 2), P(L / 2, W / 2), P(-L / 2, W / 2)]        # counter-clockwise
    z = base
    for f in range(lv):
        z1 = base + 0.3 + STOREY * (f + 1)
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
    if hip == 2:                                   # the church: a gabled roof, a square tower at the west end
        zr = zt + W / 2 * 0.8
        r0, r1 = P(-L / 2, 0), P(L / 2, 0)
        E = [(p[0], p[1], zt) for p in q]
        R0, R1 = (r0[0], r0[1], zr), (r1[0], r1[1], zr)
        flat(mb, [E[0], E[1], R1, R0], B_ROOF, 1, 4)
        flat(mb, [E[2], E[3], R0, R1], B_ROOF, 1, 4)
        flat(mb, [E[1], E[2], R1], B_PLAIN, 0)
        flat(mb, [E[3], E[0], R0], B_PLAIN, 0)
        tw = 4.2
        t = [P(-L / 2 - tw, -tw / 2), P(-L / 2, -tw / 2), P(-L / 2, tw / 2), P(-L / 2 - tw, tw / 2)]
        zz = base
        for f in range(5):
            for i in range(4):
                if f < 4:
                    wall(mb, t[i], t[(i + 1) % 4], zz, zz + 3.3, B_BRICK, rnd, bays=1)
                else:                              # the belfry: plain brick
                    a_, b_ = t[i], t[(i + 1) % 4]
                    flat(mb, [(a_[0], a_[1], zz), (b_[0], b_[1], zz), (b_[0], b_[1], zz + 3.3), (a_[0], a_[1], zz + 3.3)], B_PLAIN, 0)
            zz += 3.3
        tc = P(-L / 2 - tw / 2, 0)
        for i in range(4):
            flat(mb, [(t[i][0], t[i][1], zz), (t[(i + 1) % 4][0], t[(i + 1) % 4][1], zz), (tc[0], tc[1], zz + 6.0)], B_ROOF, 2, 4)
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
    for b in T['blocks']:                    #  random looks still drawn, so the blocks after them keep theirs)
        if b[6] < 0:
            house(gone, b[:6] + [-b[6]] + b[7:], rnd)
            continue
        key = (int(b[0] // 300), int(b[1] // 300))
        mb = cells.setdefault(key, MeshBuilder('town_houses_%d_%d' % key))
        house(mb, b, rnd)
    return list(cells.values())


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
    sign at the open end.  [x, y, the long side's way (rad), length, width, number, ground z]"""
    mb = MeshBuilder('town_subway')
    for x, y, ang, L, W, no, z in T.get('entrances', []):
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
        # the sign: a pole at the open end's corner, a box with the line's green
        q = P(L / 2 - 0.2, W / 2 + 0.35, 0.0)
        mb.box((q[0], q[1], z + 1.4), (0.08, 0.08, 2.8), 'metal', rotz=ang)
        mb.box((q[0], q[1], z + 2.95), (0.5, 0.16, 0.5), 'metal_green', rotz=ang)
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


def bridge():
    """The two decks over 연세로 (the 1995 photo: a concrete deck for each track on abutments faced with concrete, a row of
    piers in the middle of the road), and the abutments: the bank's own section as a wall each side of the opening."""
    R, B = T['rail'], T['bridge']
    S = R['sections']
    top, rz = R['top'], R['z']
    x0, x1 = B['x']
    mb = MeshBuilder('town_bridge')
    for xb, face in ((x0, 1), (x1, -1)):
        s = min(S, key=lambda q: abs(q[0] - xb))
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
        hw, zb, zs = 2.3, rz - 1.45, top
        xa, xb = x0 - 0.3, x1 + 0.3
        c = [(xa, ya - hw), (xb, yb - hw), (xb, yb + hw), (xa, ya + hw)]
        for i in range(4):                         # the girder's sides and ends
            p_, q_ = c[i], c[(i + 1) % 4]
            flat(mb, [(p_[0], p_[1], zb), (q_[0], q_[1], zb), (q_[0], q_[1], zs), (p_[0], p_[1], zs)], B_PLAIN, P_CONC)
        flat(mb, [(p_[0], p_[1], zb) for p_ in c[::-1]], B_PLAIN, P_CONC)
        u1 = (xb - xa) / (4 * BAY)
        mb.face([(xa, ya - 1.6, zs + 0.01), (xb, yb - 1.6, zs + 0.01), (xb, yb + 1.6, zs + 0.01), (xa, ya + 1.6, zs + 0.01)], ATLAS,
                uvs=[(0, v0), (u1, v0), (u1, v1), (0, v1)])
        for sg in (-1, 1):                         # ballast shoulders and the low side walls
            y0a, y0b = ya + sg * 1.6, yb + sg * 1.6
            y1a, y1b = ya + sg * hw, yb + sg * hw
            q_ = [(xa, y0a, zs), (xb, y0b, zs), (xb, y1b, zs), (xa, y1a, zs)]
            flat(mb, q_ if sg > 0 else q_[::-1], B_PLAIN, P_GRAVEL)
            for yo, flip in ((hw, sg > 0), (hw - 0.25, sg < 0)):
                w_ = [(xa, ya + sg * yo, zs), (xb, yb + sg * yo, zs), (xb, yb + sg * yo, zs + 0.9), (xa, ya + sg * yo, zs + 0.9)]
                flat(mb, w_[::-1] if flip else w_, B_PLAIN, P_CONC)
            flat(mb, [(xa, ya + sg * hw, zs + 0.9), (xb, yb + sg * hw, zs + 0.9), (xb, yb + sg * (hw - 0.25), zs + 0.9),
                      (xa, ya + sg * (hw - 0.25), zs + 0.9)][::(1 if sg < 0 else -1)], B_PLAIN, P_CONC)
        # the pier under it
        px = B['pier']
        py = _track_y(R[name], px)
        g = ground(px, py) - 0.5
        mb.box((px, py, (g + zb) / 2), (0.9, 2 * hw - 0.6, zb - g), ATLAS)
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
    mb.face([(a[0], a[1], z1), (b[0], b[1], z1), (b[0], b[1], z2), (a[0], a[1], z2)], 'sign_rotary',
            uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    d = 0.08
    a2, b2 = (a[0] - fx * d, a[1] - fy * d), (b[0] - fx * d, b[1] - fy * d)
    mb.face([(b2[0], b2[1], z1), (a2[0], a2[1], z1), (a2[0], a2[1], z2), (b2[0], b2[1], z2)], 'metal_dark')
    for p_, q_ in ((a2, a), (b, b2)):
        mb.face([(p_[0], p_[1], z1), (q_[0], q_[1], z1), (q_[0], q_[1], z2), (p_[0], p_[1], z2)], 'metal_dark')
    mb.face([(a[0], a[1], z2), (b[0], b[1], z2), (b2[0], b2[1], z2), (a2[0], a2[1], z2)], 'metal_dark')
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


def build():
    if not T:
        return []
    return houses() + [signs(), signs2(), entrances(), bridge(), poles(), road(), stops(), rot_dirsign(), rot_fence()] + bank() + [yro_signs(), yro_banner()]


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
