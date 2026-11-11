"""Hand-modelled 1997 landmarks.  Every builder returns a list of MeshBuilders in
world coordinates (local frames are applied through MeshBuilder.xf)."""
import math, random
from mathutils import Vector, Matrix
from common import MeshBuilder, ground, ground_top, min_area_rect, local_frame, offset_poly, poly_area, CAMPUS
import generic

rnd = random.Random(97)


def bld(id_):
    return next(b for b in CAMPUS['buildings'] if b['id'] == id_)


def frame_for(b, front_dir, z=None):
    """OBB frame whose local -Y axis points along front_dir (world 2D)."""
    cx, cy, L, W, ang = min_area_rect([tuple(p) for p in b['footprint']])
    fy = Vector((math.sin(ang), -math.cos(ang)))
    if fy.dot(Vector(front_dir)) < 0:
        ang += math.pi
    return cx, cy, L, W, ang, (b['base'] if z is None else z)


# ----------------------------------------------------------------------------- shared pieces
def arch_points(s0, s1, zs, kind='round', seg=10):
    """Points of an arch from left springing to right springing (s, z)."""
    w = s1 - s0
    pts = []
    if kind == 'round':
        r = w / 2
        for i in range(seg + 1):
            a = math.pi - math.pi * i / seg
            pts.append((s0 + r + r * math.cos(a), zs + r * math.sin(a)))
    elif kind == 'segment':   # shallow segmental arch: rise a quarter of the span
        w = s1 - s0
        rise = w * 0.16
        r = (w * w / 4 + rise * rise) / (2 * rise)
        a0 = math.asin((w / 2) / r)
        for i in range(seg + 1):
            a = -a0 + 2 * a0 * i / seg
            pts.append((s0 + w / 2 + r * math.sin(a), zs + r * math.cos(a) - (r - rise)))
        pts.sort(key=lambda p: p[0])
        return pts
    elif kind == 'tudor':     # four-centred: tight arcs at the springings, then nearly straight to a low point
        a = w / 2
        r1, th = 0.36 * a, math.radians(66)
        na = max(3, seg // 3)
        left = [(s0 + r1 - r1 * math.cos(th * i / na), zs + r1 * math.sin(th * i / na)) for i in range(na + 1)]
        ex, ez = left[-1]
        apex = ez + (s0 + a - ex) / math.tan(th)
        nl_ = max(2, seg // 2 - na)
        for i in range(1, nl_ + 1):            # a slightly bellied line to the apex (a large-radius arc)
            t = i / nl_
            bell = 0.06 * a * math.sin(math.pi * t) * (1 - t)
            left.append((ex + (s0 + a - ex) * t, ez + (apex - ez) * t + bell))
        right = [(2 * (s0 + a) - s, z) for s, z in reversed(left[:-1])]
        return left + right
    else:   # pointed (equilateral gothic)
        r = w
        half = seg // 2
        for i in range(half + 1):          # left arc centred at s1
            a = math.pi - (math.pi / 3) * i / half
            pts.append((s1 + r * math.cos(a), zs + r * math.sin(a)))
        for i in range(1, half + 1):       # right arc centred at s0
            a = math.pi / 3 - (math.pi / 3) * i / half
            pts.append((s0 + r * math.cos(a), zs + r * math.sin(a)))
    return pts


def arch_fill(mb, P, s0, s1, zs, ztop, depth, mat, kind='round', seg=10, intrados_mat=None):
    """Fill the area between an arch and the horizontal line ztop over [s0,s1].
    P(s, z, d) -> local 3D point (d = offset along outward normal, negative = inward)."""
    pts = arch_points(s0, s1, zs, kind, seg)
    for i in range(len(pts) - 1):
        (sa, za), (sb, zb) = pts[i], pts[i + 1]
        mb.quad(P(sa, za, 0), P(sb, zb, 0), P(sb, ztop, 0), P(sa, ztop, 0), mat)                  # front
        mb.quad(P(sb, zb, -depth), P(sa, za, -depth), P(sa, ztop, -depth), P(sb, ztop, -depth), mat)  # back
        mb.quad(P(sb, zb, 0), P(sa, za, 0), P(sa, za, -depth), P(sb, zb, -depth), intrados_mat or mat)  # soffit


def edge_P(a, b, base_z=0.0):
    a, b = Vector((*a, 0)), Vector((*b, 0))
    t = (b - a)
    L = t.length
    t.normalize()
    n = Vector((t.y, -t.x, 0))

    def P(s, z, d=0.0):
        p = a + t * s + n * d
        return (p.x, p.y, base_z + z)
    return P, L, t, n


def rect(L, W):
    return [(-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2)]


def flat_wall(mb, P, s0, s1, z0, z1, mat, d=0.0, **kw):
    mb.quad(P(s0, z0, d), P(s1, z0, d), P(s1, z1, d), P(s0, z1, d), mat, **kw)


def glass_run(mb, P, s0, s1, z0, z1, d, cuts, glass='glass', hall=None):
    """Glass over [s0, s1] x [z0, z1] at depth d of a wall P, one pane (a room or a hall seen through it, common.py
    pane_uv) between each two cuts (mullions), so that the rooms change behind a mullion, not in mid-pane."""
    edges = [s0] + [c for c in cuts if s0 + 0.3 < c < s1 - 0.3] + [s1]
    for a, b in zip(edges, edges[1:]):
        mb.quad(P(a, z0, d), P(b, z0, d), P(b, z1, d), P(a, z1, d), glass, panes=(1, 1) if hall is None else (1, 1, hall))


def pane_count(n, size, target):
    """How many panes of whole bays: n bays over size metres grouped into panes about target metres (dividing n)."""
    k = max(1, min(n, round(target * n / max(size, 1e-3))))
    while n % k:
        k -= 1
    return n // k


def window_grid(mb, P, L, z0, nfl, fh, bay, mat_wall, ww=0.6, sill=0.9, head=0.6, depth=0.25,
                glass='glass', frame='frame_dark', trim=None, mull=1, s_start=0.0, s_end=None, d=0.0):
    """Punched windows on an edge segment [s_start, s_end] (local wall plane offset d)."""
    s_end = L if s_end is None else s_end
    span = s_end - s_start
    nb = max(1, int(round(span / bay)))
    bw = span / nb
    for f in range(nfl):
        zf = z0 + f * fh
        for k in range(nb):
            s0 = s_start + k * bw
            s1 = s0 + bw
            w = bw * ww
            w0, w1 = s0 + (bw - w) / 2, s0 + (bw + w) / 2
            zs, zh = zf + sill, zf + fh - head
            Q = lambda s, z, dd=0.0: P(s, z, d + dd)
            mb.quad(Q(s0, zf), Q(s1, zf), Q(s1, zs), Q(s0, zs), mat_wall)
            mb.quad(Q(s0, zh), Q(s1, zh), Q(s1, zf + fh), Q(s0, zf + fh), mat_wall)
            mb.quad(Q(s0, zs), Q(w0, zs), Q(w0, zh), Q(s0, zh), mat_wall)
            mb.quad(Q(w1, zs), Q(s1, zs), Q(s1, zh), Q(w1, zh), mat_wall)
            rv = trim or mat_wall
            mb.quad(Q(w0, zs), Q(w0, zs, -depth), Q(w1, zs, -depth), Q(w1, zs), rv)
            mb.quad(Q(w1, zh), Q(w1, zh, -depth), Q(w0, zh, -depth), Q(w0, zh), rv)
            mb.quad(Q(w0, zh), Q(w0, zh, -depth), Q(w0, zs, -depth), Q(w0, zs), rv)
            mb.quad(Q(w1, zs), Q(w1, zs, -depth), Q(w1, zh, -depth), Q(w1, zh), rv)
            mb.quad(Q(w0, zs, -depth), Q(w1, zs, -depth), Q(w1, zh, -depth), Q(w0, zh, -depth), glass)
            for m in range(mull):
                sm = w0 + (w1 - w0) * (m + 1) / (mull + 1)
                mb.quad(Q(sm - 0.04, zs, -depth + 0.06), Q(sm + 0.04, zs, -depth + 0.06),
                        Q(sm + 0.04, zh, -depth + 0.06), Q(sm - 0.04, zh, -depth + 0.06), frame)
            zt = zs + (zh - zs) * 0.7
            mb.quad(Q(w0, zt - 0.04, -depth + 0.06), Q(w1, zt - 0.04, -depth + 0.06),
                    Q(w1, zt + 0.04, -depth + 0.06), Q(w0, zt + 0.04, -depth + 0.06), frame)
            if trim:
                # protruding stone sill + hood moulding
                mb.quad(Q(w0 - 0.12, zs - 0.12, 0.1), Q(w1 + 0.12, zs - 0.12, 0.1), Q(w1 + 0.12, zs, 0.1), Q(w0 - 0.12, zs, 0.1), trim)
                mb.quad(Q(w0 - 0.12, zs, 0.1), Q(w1 + 0.12, zs, 0.1), Q(w1 + 0.12, zs, 0), Q(w0 - 0.12, zs, 0), trim)
                mb.quad(Q(w0 - 0.15, zh, 0.1), Q(w1 + 0.15, zh, 0.1), Q(w1 + 0.15, zh + 0.18, 0.1), Q(w0 - 0.15, zh + 0.18, 0.1), trim)
                mb.quad(Q(w0 - 0.15, zh + 0.18, 0.1), Q(w1 + 0.15, zh + 0.18, 0.1), Q(w1 + 0.15, zh + 0.18, 0), Q(w0 - 0.15, zh + 0.18, 0), trim)
                mb.quad(Q(w0 - 0.15, zh, 0), Q(w1 + 0.15, zh, 0), Q(w1 + 0.15, zh, 0.1), Q(w0 - 0.15, zh, 0.1), trim)


# ============================================================================= 중앙도서관
def library():
    """중앙도서관 (1979) as in reference/1997_중앙도서관.jpg and 1995_백양로와_중앙도서관.jpg: tall slender piers of pale
    stone panels from the plinth to a deep attic band, each bay closed at the top by a shallow segmental arch;
    deep in the bays, rows of windows between bronze-tan spandrel panels; panel joints over piers and attic."""
    b = bld(163525865)
    cx, cy, L, W, ang, z0 = frame_for(b, (1.0, -0.25))
    # the piers stand on a low granite base only two steps over the forecourt (1997 photo: people walk at the foot of
    # the piers; no flight up to a podium), and the ground is level all round it (tools/build_campus.py LIBRARY_APRON)
    g0 = 0.3
    z0 = lift_base(z0, cx, cy, ang, W / 2 + 2.5, g0, 0.3)
    mb = MeshBuilder('lm_library')
    mb.xf = local_frame(cx, cy, ang, z0)
    H = 23.0                     # top of attic
    # the arches spring about 5 m under the roof and their crowns come within 4 m of it, the top floor's glazing
    # filling them (the 1997 photo: the arch crown 0.15 - 0.18 of the hall's height under the roofline)
    spring, attic0 = 17.9, 19.3
    inset = 2.4
    fh, nf = 3.75, 5
    # bays about 7 m on centre: eleven along the long fronts and six across the ends (the 1997 photo counts eleven
    # arches along the 백양로 front; the 1997 aerial photo and the 1990 campus map six on the south end), the piers
    # some 1.7 m wide and the corner piers wider, a little under a third of the bay (the 1995 photo, end on)
    BAY, PIER = 7.0, 1.7
    # plinth
    mb.prism(offset_poly(rect(L, W), 0.6), -4, g0, 'stone_granite', 'stone_granite')
    # its top is the floor of the deep arcade between the piers, walked on all round to the glass
    W_ = lambda lx, ly, lz: tuple(mb.xf @ Vector((lx, ly, lz)))
    ring_o, ring_i = offset_poly(rect(L, W), 0.6), rect(L - 2 * (inset + 0.25), W - 2 * (inset + 0.25))
    for i in range(4):
        j = (i + 1) % 4
        WALK_FACES.append([W_(*ring_o[i], g0), W_(*ring_o[j], g0), W_(*ring_i[j], g0), W_(*ring_i[i], g0)])
    # the main door: the middle bay of the 백양로 front (or the two either side of its middle pier), glass doors in
    # bright frames with the lit entrance hall behind (instead of the dark glazing of the other bays)
    nb_f = max(1, int(round(L / BAY)))
    bw_f = (L - PIER) / nb_f
    mid_k = nb_f // 2
    door_bays = [(-L / 2 + k * bw_f + PIER, -L / 2 + (k + 1) * bw_f) for k in ((mid_k,) if nb_f % 2 else (mid_k - 1, mid_k))]
    # recessed wall in the bays: per floor a bronze spandrel band, then glazing split by slim mullions
    core = rect(L - 2 * inset, W - 2 * inset)
    for i in range(4):
        a, bb = core[i], core[(i + 1) % 4]
        P, Le, t, n = edge_P(a, bb)
        gaps = [(x0 - a[0] + 0.15, x1 - a[0] - 0.15) for x0, x1 in door_bays] if i == 0 else []
        cuts = [0.0] + [v for g in gaps for v in g] + [Le]
        mull = [(k + 0.5) * Le / int(Le / 2.0) for k in range(int(Le / 2.0))]
        for s0_, s1_ in zip(cuts[0::2], cuts[1::2]):                          # ground floor: dark glazing, set back
            glass_run(mb, P, s0_, s1_, g0, g0 + 3.4, -0.3, mull[1::2])        # a hall behind every two lights
        for k in range(int(Le / 2.0)):
            s = (k + 0.5) * Le / int(Le / 2.0)
            if any(g[0] - 0.1 < s < g[1] + 0.1 for g in gaps):
                continue
            mb.quad(P(s - 0.06, g0, -0.25), P(s + 0.06, g0, -0.25), P(s + 0.06, g0 + 3.4, -0.25), P(s - 0.06, g0 + 3.4, -0.25), 'frame_dark')
        for s0_, s1_ in gaps:
            shopfront(mb, P, s0_, s1_, g0, g0 + 3.3, -0.3, bays=4, door_h=2.4)
            vestibule(mb, P, s0_ - 0.1, s1_ + 0.1, g0 + 0.002, g0 + 3.25, -0.32, 6.0, lights=3)
            mb.quad(P(s0_ - 0.15, g0 + 3.3, -0.3), P(s1_ + 0.15, g0 + 3.3, -0.3), P(s1_ + 0.15, g0 + 3.4, -0.3),
                    P(s0_ - 0.15, g0 + 3.4, -0.3), 'frame_silver')
        for f in range(1, nf):
            zf = g0 + 3.4 + (f - 1) * fh
            flat_wall(mb, P, 0, Le, zf, zf + 1.35, 'panel_bronze')
            glass_run(mb, P, 0, Le, zf + 1.35, zf + fh, -0.12, [(k + 0.5) * Le / int(Le / 1.4) for k in range(1, int(Le / 1.4), 2)])
            mb.quad(P(0, zf + 1.35, 0), P(Le, zf + 1.35, 0), P(Le, zf + 1.35, -0.12), P(0, zf + 1.35, -0.12), 'panel_bronze')
            for k in range(int(Le / 1.4)):
                s = (k + 0.5) * Le / int(Le / 1.4)
                mb.quad(P(s - 0.05, zf + 1.35, -0.08), P(s + 0.05, zf + 1.35, -0.08), P(s + 0.05, zf + fh, -0.08), P(s - 0.05, zf + fh, -0.08), 'frame_dark')
        flat_wall(mb, P, 0, Le, g0 + 3.4 + (nf - 1) * fh, attic0 + 0.4, 'panel_bronze')
    # pier screen
    pier = PIER
    depth = 2.0
    outer = rect(L, W)

    def joint(P, s0, s1, z):          # a recessed horizontal panel joint
        mb.quad(P(s0, z, 0.015), P(s1, z, 0.015), P(s1, z + 0.05, 0.015), P(s0, z + 0.05, 0.015), 'concrete_dark')

    # every pier reads as two: a dark slot down the middle of its face, on up through the attic band to the roofline
    # (the 1997 photo and reference/2024_겨울_독수리상과_중앙도서관.jpg: one dark line per pier from the roof to the base,
    # darker than the panel joints)
    SLOT_W, SLOT_D = 0.12, 0.3

    def slot(P, sm, z0, z1):          # its two cheeks and its back
        w = SLOT_W / 2
        mb.quad(P(sm - w, z0, 0), P(sm - w, z0, -SLOT_D), P(sm - w, z1, -SLOT_D), P(sm - w, z1, 0), 'concrete_dark')
        mb.quad(P(sm + w, z0, -SLOT_D), P(sm + w, z0, 0), P(sm + w, z1, 0), P(sm + w, z1, -SLOT_D), 'concrete_dark')
        mb.quad(P(sm - w, z0, -SLOT_D), P(sm + w, z0, -SLOT_D), P(sm + w, z1, -SLOT_D), P(sm - w, z1, -SLOT_D), 'trim_black')

    def beside(s0, s1, slots):        # [s0, s1] less the slots
        cuts = [s0] + [v for sm in slots for v in (sm - SLOT_W / 2, sm + SLOT_W / 2)] + [s1]
        return list(zip(cuts[0::2], cuts[1::2]))

    for i in range(4):
        a, bb = outer[i], outer[(i + 1) % 4]
        P, Le, t, n = edge_P(a, bb)
        nb = max(1, int(round(Le / BAY)))
        bw = (Le - pier) / nb
        slots = []
        for k in range(nb + 1):
            s = k * bw
            pw = pier * (1.4 if k in (0, nb) else 1.0)
            s0, s1 = (s, s + pw) if k < nb else (Le - pw, Le)
            if k == 0:
                s1 = pw
            sm = (s0 + s1) / 2
            slots.append(sm)
            for p0, p1 in beside(s0, s1, [sm]):
                mb.quad(P(p0, g0, 0), P(p1, g0, 0), P(p1, attic0, 0), P(p0, attic0, 0), 'stone_panel')
                for zz in [g0 + 1.8 * q for q in range(1, int((attic0 - g0) / 1.8))]:
                    joint(P, p0, p1, zz)
            mb.quad(P(s1, g0, 0), P(s1, g0, -depth), P(s1, attic0, -depth), P(s1, attic0, 0), 'stone_panel')
            mb.quad(P(s0, g0, -depth), P(s0, g0, 0), P(s0, attic0, 0), P(s0, attic0, -depth), 'stone_panel')
            slot(P, sm, g0, H)
            if k < nb:
                a0 = s1
                a1 = (k + 1) * bw if k + 1 < nb else Le - pier * 1.4
                arch_fill(mb, P, a0, a1, spring, attic0, depth, 'stone_panel', 'segment', 10)
        # deep attic band of square panels, cut by the piers' slots
        for p0, p1 in beside(0, Le, slots):
            flat_wall(mb, P, p0, p1, attic0, H, 'stone_panel')
            for zz in (attic0 + (H - attic0) / 3, attic0 + (H - attic0) * 2 / 3):
                joint(P, p0, p1, zz)
        mb.quad(P(0, H, 0), P(Le, H, 0), P(Le, H, -depth), P(0, H, -depth), 'stone_panel')
        mb.quad(P(0, attic0, 0), P(0, attic0, -depth), P(Le, attic0, -depth), P(Le, attic0, 0), 'stone_panel')
        for sa, sb in zip(slots, slots[1:]):        # the panels' vertical joints evenly between two slots
            npn = max(1, int(round((sb - sa) / 2.1)))
            for q in range(1, npn):
                sq = sa + q * (sb - sa) / npn
                mb.quad(P(sq - 0.025, attic0, 0.015), P(sq + 0.025, attic0, 0.015), P(sq + 0.025, H, 0.015),
                        P(sq - 0.025, H, 0.015), 'concrete_dark')
        flat_wall(mb, P, 0, Le, H - 1.2, H, 'concrete', d=-depth)
    mb.face([(p[0], p[1], H - 1.2) for p in offset_poly(rect(L, W), -depth)], 'roof_flat')
    # the storey on the roof (the 1992 extension to six storeys stands behind the attic band; this block is what shows
    # over it): one white storey with a few small lights, its top 2.3 m over the attic, 15.5 m across, a little east of
    # the axis and 6.5 m in from the south end (the 1995 photo, end on: 14.2 m wide, its centre 2.8 m east of the
    # axis, 2.2 m over the attic; the 1994 aerial photo: 13.6 - 17.1 m, 1.6 - 2.0 m east; their two views put its
    # front 5 - 8 m in).  How far back it runs is not seen (reference/고증.md 3.2)
    xf_, dep_, yc_, wd_, top_ = -L / 2 + 6.5, 22.0, -2.2, 15.5, H + 2.3
    mb.box((xf_ + dep_ / 2, yc_, (H - 1.2 + top_) / 2), (dep_, wd_, top_ - H + 1.2), 'plaster_white',
           mats={'top': 'roof_flat'})
    Pr, Lr, _, _ = edge_P((xf_, yc_ + wd_ / 2), (xf_, yc_ - wd_ / 2))        # its south face, from the west corner
    for fr, ww in ((0.18, 1.5), (0.34, 0.8), (0.55, 1.5), (0.75, 1.5)):    # four lights, as in the 1995 photo
        s = fr * Lr
        mb.quad(Pr(s - ww / 2, H + 0.6, 0.02), Pr(s + ww / 2, H + 0.6, 0.02), Pr(s + ww / 2, H + 1.75, 0.02),
                Pr(s - ww / 2, H + 1.75, 0.02), 'glass')
    Pe, Le_, _, _ = edge_P((xf_, yc_ - wd_ / 2), (xf_ + dep_, yc_ - wd_ / 2))  # its east face (lights assumed)
    for k in range(5):
        s = (k + 0.5) * Le_ / 5
        mb.quad(Pe(s - 0.75, H + 0.6, 0.02), Pe(s + 0.75, H + 0.6, 0.02), Pe(s + 0.75, H + 1.75, 0.02),
                Pe(s - 0.75, H + 1.75, 0.02), 'glass')
    # two broad granite steps along the whole 백양로 front, from the forecourt up onto the base
    stair_flight(mb, 0, -W / 2 - 0.6, L + 1.2, g0, n=2, landing=0.0, tread=0.42, flare=0.0, cheek=0.0, rail=False,
                 gfn=local_ground(mb))
    return [mb]


# ============================================================================= 학생회관
def union():
    b = bld(1444448640)
    cx, cy, L, W, ang, z0 = frame_for(b, (-1.0, 0.25))
    L, W = L - 2, min(W, 24)
    mb = MeshBuilder('lm_union')
    mb.xf = local_frame(cx, cy, ang, z0)
    fh, nf = 3.9, 4
    g = 4.6                     # pilotis ground floor
    H = g + nf * fh
    mb.prism(offset_poly(rect(L, W), 0.3), -4, 0.3, 'stone_granite', 'stone_granite')
    # recessed glazed ground floor + pilotis
    core = rect(L - 4, W - 4)
    for i in range(4):
        a, bb = core[i], core[(i + 1) % 4]
        P, Le, t, n = edge_P(a, bb)
        # a room behind every light (curtains in the 2009 photo)
        glass_run(mb, P, 0, Le, 0.3, g, 0.0, [(k + 0.5) * Le / int(Le / 2.4) for k in range(int(Le / 2.4))], hall=False)
        for k in range(int(Le / 2.4)):
            s = (k + 0.5) * Le / int(Le / 2.4)
            mb.quad(P(s - 0.06, 0.3, 0.05), P(s + 0.06, 0.3, 0.05), P(s + 0.06, g, 0.05), P(s - 0.06, g, 0.05), 'frame_dark')
    outer = rect(L, W)
    for i in range(4):
        a, bb = outer[i], outer[(i + 1) % 4]
        P, Le, t, n = edge_P(a, bb)
        npil = int(Le / 7.5)
        for k in range(npil + 1):
            s = 0.6 + k * (Le - 1.2) / npil
            mb.box((P(s, 0)[0] - n.x * 1.0, P(s, 0)[1] - n.y * 1.0, g / 2 + 0.3), (0.9, 0.9, g - 0.3), 'stone_panel',
                   rotz=math.atan2(t.y, t.x), skip=('top', 'bottom'))
        # soffit of the overhang
        mb.quad(P(0, g, 0), P(0, g, -2.0), P(Le, g, -2.0), P(Le, g, 0), 'stone_panel')
        # upper floors: a precast screen of white concrete with a tall lancet window in every bay between the fins
        # (reference/학생회관_외벽상세.jpg, 학생회관_정면_2009.jpg). The bay is about a quarter of the storey wide; the
        # window, about two thirds of the bay wide and of the storey tall, sits on the sill ledge, its frame and the
        # pale green glass set well back. A hood rib springs from the fins round the window's head, and in the band
        # under the next sill a second pointed arch has its feet on the fins at the height of the window's apex.
        # The concrete is more than half of the wall: it reads white, not as dark glass behind thin ribs.
        npan = max(2, int(round(Le / 1.2)))
        pw = Le / npan
        DS, DG, DR = -0.3, -0.72, -0.2       # the screen's face, the glass, the ribs' face (fins and ledges at 0)
        for f in range(nf):
            zf = g + f * fh
            za, zb = zf + 0.3, zf + fh       # the sill ledge on the slab edge; the next floor
            flat_wall(mb, P, 0, Le, zf, za, 'stone_white')
            mb.quad(P(0, za, 0), P(Le, za, 0), P(Le, za, DS), P(0, za, DS), 'stone_white')
            mb.quad(P(0, zf, DS), P(Le, zf, DS), P(Le, zf, 0), P(0, zf, 0), 'stone_panel')
            for k in range(npan):
                s0, s1 = k * pw, (k + 1) * pw
                sm = (s0 + s1) / 2
                a0, a1 = s0 + 0.07, s1 - 0.07
                # vertical fin
                mb.quad(P(s0 - 0.07, za, 0), P(s0 + 0.07, za, 0), P(s0 + 0.07, zb, 0), P(s0 - 0.07, zb, 0), 'stone_white')
                mb.quad(P(s0 + 0.07, za, 0), P(s0 + 0.07, za, DS), P(s0 + 0.07, zb, DS), P(s0 + 0.07, zb, 0), 'stone_panel')
                mb.quad(P(s0 - 0.07, za, DS), P(s0 - 0.07, za, 0), P(s0 - 0.07, zb, 0), P(s0 - 0.07, zb, DS), 'stone_panel')
                # the screen round a lancet opening
                o0, o1 = sm - 0.34 * pw, sm + 0.34 * pw
                zap = za + 2.45                                   # the window's apex
                zs = zap - (o1 - o0) * math.sqrt(3) / 2           # its springing (equilateral arch)
                arc = arch_points(o0, o1, zs, 'pointed', 8)
                flat_wall(mb, P, a0, o0, za, zb, 'stone_white', d=DS)
                flat_wall(mb, P, o1, a1, za, zb, 'stone_white', d=DS)
                for p, q in zip(arc, arc[1:]):
                    mb.quad(P(p[0], p[1], DS), P(q[0], q[1], DS), P(q[0], zb, DS), P(p[0], zb, DS), 'stone_white')
                # the reveal (jambs and soffit), the sill, the glass and its dark frame
                rim = [(o0, za)] + arc + [(o1, za)]
                for p, q in zip(rim, rim[1:]):
                    mb.quad(P(q[0], q[1], DS), P(p[0], p[1], DS), P(p[0], p[1], DG), P(q[0], q[1], DG), 'stone_panel')
                mb.quad(P(o0, za, DS), P(o1, za, DS), P(o1, za, DG), P(o0, za, DG), 'stone_white')
                mb.face([P(o0, za, DG), P(o1, za, DG)] + [P(x, z, DG) for x, z in arc[::-1]], 'glass_green')
                dF, fw = DG + 0.03, 0.035
                for zz in (za + 0.55, za + 1.05, zs):                     # the two low sashes, the transom
                    mb.quad(P(o0, zz - fw, dF), P(o1, zz - fw, dF), P(o1, zz + fw, dF), P(o0, zz + fw, dF), 'frame_dark')
                mb.quad(P(sm - fw, za, dF), P(sm + fw, za, dF), P(sm + fw, za + 1.05, dF), P(sm - fw, za + 1.05, dF), 'frame_dark')
                # hood rib from the fins round the window's head; the band's arch above it, under the next sill
                rise = (a1 - a0) * math.sqrt(3) / 2
                for z_spring in (zap + 0.17 - rise, zb - 0.06 - rise):
                    pts = arch_points(a0, a1, z_spring, 'pointed', 6)
                    for p, q in zip(pts, pts[1:]):
                        ds_, dz_ = q[0] - p[0], q[1] - p[1]
                        ln = math.hypot(ds_, dz_)
                        ns_, nz_ = -dz_ / ln * 0.05, ds_ / ln * 0.05      # half the rib's width, across it
                        lo = ((p[0] - ns_, p[1] - nz_), (q[0] - ns_, q[1] - nz_))
                        hi = ((p[0] + ns_, p[1] + nz_), (q[0] + ns_, q[1] + nz_))
                        mb.quad(P(*lo[0], DR), P(*lo[1], DR), P(*hi[1], DR), P(*hi[0], DR), 'stone_white')
                        mb.quad(P(*lo[1], DR), P(*lo[0], DR), P(*lo[0], DS), P(*lo[1], DS), 'stone_panel')   # underside
        # a solid pier up the corner (the screens of the two faces stop short of it)
        mb.box(P(Le - 0.2, (g + H) / 2, -0.2), (0.5, 0.5, H - g), 'stone_white', rotz=math.atan2(t.y, t.x), skip=('top', 'bottom'))
        mb.quad(P(0, H, DS), P(Le, H, DS), P(Le, H, 0), P(0, H, 0), 'stone_panel')       # under the parapet
        flat_wall(mb, P, 0, Le, H, H + 1.0, 'stone_panel')
        mb.quad(P(0, H + 1.0, 0), P(Le, H + 1.0, 0), P(Le, H + 1.0, -0.9), P(0, H + 1.0, -0.9), 'stone_panel')
    mb.face([(p[0], p[1], H + 0.2) for p in offset_poly(rect(L, W), -0.9)], 'roof_flat')
    mb.box((L * 0.2, 2, H + 1.6), (8, 6, 3.0), 'stone_panel', mats={'top': 'roof_flat'})
    # long vertical cloth banners (동아리 / 총학생회 현수막) on the front facade
    banners = []
    cols = ['banner_yellow', 'banner_red', 'banner_orange', 'banner_yellow']
    bm = MeshBuilder('lm_union_banners')
    bm.xf = mb.xf
    for k, c in enumerate(cols):
        s = -6 + k * 2.6
        y = -W / 2 - 0.1
        bm.quad((s, y, g + 1.5), (s + 1.8, y, g + 1.5), (s + 1.8, y, H - 0.6), (s, y, H - 0.6), c,
                uvs=[(k * 0.25, 0), (k * 0.25 + 0.25, 0), (k * 0.25 + 0.25, 1), (k * 0.25, 1)])
    # the lower white wing in the 1997 photo (학생회관 별관 is generic) -> nothing else
    return [mb, bm]


# ============================================================================= 백주년기념관
def circle_cross(c, r, p, q):
    """Where the segment p -> q (one end inside the circle (c, r), the other outside) crosses the circle."""
    p, q, c = Vector(p).to_2d(), Vector(q).to_2d(), Vector(c).to_2d()
    d = q - p
    f = p - c
    a, b, cc = d.dot(d), 2 * f.dot(d), f.dot(f) - r * r
    disc = math.sqrt(max(0.0, b * b - 4 * a * cc))
    ts = [u for u in ((-b - disc) / (2 * a), (-b + disc) / (2 * a)) if -1e-6 <= u <= 1 + 1e-6]
    return p + d * (ts[0] if ts else 0.5)


def inside_poly(pt, poly):
    x, y = pt
    ins = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            ins = not ins
    return ins


def seg_dist(pt, a, b):
    p, a, b = Vector(pt), Vector(a), Vector(b)
    ab = b - a
    u = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-9)))
    return (p - (a + ab * u)).length


def planter(mb, poly, z0):
    """A raised granite planter of clipped box filling the polygon poly (2D, either winding) over the ground."""
    area = sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly))) / 2
    poly = [tuple(p) for p in (poly if area > 0 else poly[::-1])]
    zp = max(ground_top(*p) for p in poly) - z0 + 0.45
    mb.prism(poly, z0 - 1.0, z0 + zp, 'stone_granite')
    mb.face([(x, y, z0 + zp - 0.06) for x, y in poly], 'soil')
    edges = list(zip(poly, poly[1:] + poly[:1]))
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    gx = min(xs) + 0.4
    while gx < max(xs):
        gy = min(ys) + 0.4
        while gy < max(ys):
            if inside_poly((gx, gy), poly) and min(seg_dist((gx, gy), a_, b_) for a_, b_ in edges) > 0.45:
                mb.sphere((gx, gy, z0 + zp + 0.25), 0.55, 'hedge_boxwood', seg=10, rings=7, sz=0.75)
            gy += 0.8
        gx += 0.8


def nw_lobby(mb, c, R, arc, z0, HP, low, pockets):
    """백주년기념관's drum come down to the ground (issue #32) on the arc `arc` of the drum's circle (c, R), south of the
    museum's entrance in the 백양로 porch: the 1996 side photo of the entrance shows the big curved wall going down past the
    low wall to tall curved glass in dark upright mullions and a transom, under a band of white panels with a rough
    granite course, trees before it; today's photo of the 백양로 side the same curved row of glass by the porch.  The
    lobby behind it lit like the other halls' (window glass in hall mode, common.py pane_uv).  The sill clears the
    ground where the glass stands free (low: the arc's points there); in the outline's pockets outside it (pockets:
    polygons) raised granite planters of clipped box, in front of the glass where the ground rises past its sill."""
    gmax = max(ground_top(c[0] + (R + 0.6) * (p.x - c[0]) / R, c[1] + (R + 0.6) * (p.y - c[1]) / R) for p in low)
    zs = max(0.6, gmax - z0 + 0.2)                  # the glass's sill over the ground where nothing stands before it
    zh = HP - 1.6                                   # its head: two storeys of the lobby
    ztr = zs + (zh - zs) * 0.62                     # the transom: tall lights below, short ones above
    zg0, zg1 = zh + 0.75, zh + 1.1                  # the rough granite course in the white band
    rg, rf = R - 0.25, R + 0.05                     # the glass set back under the band
    ang = [math.atan2(p.y - c[1], p.x - c[0]) for p in arc]
    ring = lambda r, a: (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
    W = 'stone_panel_white'
    for k in range(len(arc) - 1):
        a, b = ang[k], ang[k + 1]
        A0, B0 = ring(rg, a), ring(rg, b)
        # the glass, one lobby view per mullion bay; the white band and its granite course over it; the base below
        # (faces wound like MeshBuilder.cylinder: outward for the angle increasing from A to B)
        mb.quad((*A0, z0 + zs), (*B0, z0 + zs), (*B0, z0 + zh), (*A0, z0 + zh), 'glass', panes=(1, 1, True))
        Af, Bf = ring(rf, a), ring(rf, b)
        mb.quad((*Af, z0 + zh), (*Bf, z0 + zh), (*Bf, z0 + HP + 0.9), (*Af, z0 + HP + 0.9), W)
        mb.quad((*A0, z0 + zh), (*B0, z0 + zh), (*Bf, z0 + zh), (*Af, z0 + zh), W)               # the soffit
        mb.quad((*Af, z0 + HP + 0.9), (*Bf, z0 + HP + 0.9), (*ring(R - 0.1, b), z0 + HP + 0.9), (*ring(R - 0.1, a), z0 + HP + 0.9), W)
        Ag, Bg = ring(rf + 0.07, a), ring(rf + 0.07, b)
        mb.quad((*Ag, z0 + zg0), (*Bg, z0 + zg0), (*Bg, z0 + zg1), (*Ag, z0 + zg1), 'stone_granite')
        mb.quad((*Af, z0 + zg0), (*Bf, z0 + zg0), (*Bg, z0 + zg0), (*Ag, z0 + zg0), 'stone_granite')
        mb.quad((*Ag, z0 + zg1), (*Bg, z0 + zg1), (*Bf, z0 + zg1), (*Af, z0 + zg1), 'stone_granite')
        Ab, Bb = ring(R + 0.2, a), ring(R + 0.2, b)
        mb.quad((*Ab, z0 - 0.5), (*Bb, z0 - 0.5), (*Bb, z0 + zs), (*Ab, z0 + zs), 'stone_granite')
        mb.quad((*Ab, z0 + zs), (*Bb, z0 + zs), (*B0, z0 + zs), (*A0, z0 + zs), 'stone_granite')
        # the frame: sill, transom and head rails in front of the glass
        for zz, w in ((zs + 0.05, 0.1), (ztr, 0.12), (zh - 0.05, 0.1)):
            A1, B1 = ring(rg + 0.08, a), ring(rg + 0.08, b)
            mb.quad((*A1, z0 + zz - w / 2), (*B1, z0 + zz - w / 2), (*B1, z0 + zz + w / 2), (*A1, z0 + zz + w / 2), 'frame_dark')
            mb.quad((*A1, z0 + zz + w / 2), (*B1, z0 + zz + w / 2), (*B0, z0 + zz + w / 2), (*A0, z0 + zz + w / 2), 'frame_dark')
    for k, a in enumerate(ang):                    # the upright mullions on the bay lines
        p = Vector(ring(rg + 0.05, a))
        tg = Vector((-math.sin(a), math.cos(a)))
        if k in (0, len(ang) - 1):                  # the ends: the glass returns to the walls beside it
            e0, e1 = Vector(ring(rg, a)), Vector(ring(rf + 0.07, a))
            if k:
                e0, e1 = e1, e0
            mb.quad((*e0, z0 + zs), (*e1, z0 + zs), (*e1, z0 + HP + 0.9), (*e0, z0 + HP + 0.9), W)
            continue
        mb.box((p.x, p.y, z0 + (zs + zh) / 2), (0.1, 0.16, zh - zs), 'frame_dark', rotz=math.atan2(tg.y, tg.x))
    for poly in pockets:
        planter(mb, poly, z0)


def drum_outline(c, r, arc=None, seg=192):
    """The drum's ring of radius r, angle increasing (like MeshBuilder.cylinder), with points at the ends of `arc`
    (a0, a1 in radians, a0 < a1) and, for each point, whether the segment from it to the next lies on that arc (where
    the drum's wall stops above the lobby glass at its foot: drum_band's `flat`)."""
    angs = [2 * math.pi * i / seg for i in range(seg)]
    if arc:
        a0, a1 = (a % (2 * math.pi) for a in arc)
        angs = sorted(set(round(a, 9) for a in angs + [a0, a1]))
    pts, on = [], []
    for k, a in enumerate(angs):
        pts.append(Vector((c[0] + r * math.cos(a), c[1] + r * math.sin(a))))
        if arc:
            m = (a + angs[(k + 1) % len(angs)] + (2 * math.pi if k == len(angs) - 1 else 0)) / 2
            on.append(a0 <= m % (2 * math.pi) <= a1 if a0 <= a1 else (m % (2 * math.pi) >= a0 or m % (2 * math.pi) <= a1))
        else:
            on.append(False)
    return pts, on


def drum_band(mb, pts, flat, za, zb, mat, zflat=None, tag=None):
    """Walls along the outline from za to zb; on the segments flagged in `flat` (drum_outline: from point i to the next)
    only from zflat up (the lobby glass under it)."""
    n = len(pts)
    per = sum((pts[(i + 1) % n] - pts[i]).length for i in range(n))
    u = 0.0
    for i in range(n):
        j = (i + 1) % n
        L = (pts[j] - pts[i]).length
        on_flat = flat[i]
        z1 = max(za, zflat) if (on_flat and zflat is not None) else za
        if z1 < zb:
            mb.face([(*pts[i], z1), (*pts[j], z1), (*pts[j], zb), (*pts[i], zb)], mat,
                    uvs=[(u, z1), (u + L, z1), (u + L, zb), (u, zb)], smooth=tag)
        u += L
    return per


# 백주년기념관's drum (the concert hall, reference/고증.md 3.4, issue #101): a 34 m drum at the south of the hall, at the
# 백양로 face, from the 2011 roadview (its silhouette from nine panoramas along 백양로, every heading solved on
# 백주년기념관's north-west corner and the eagle / 활천대 pillars: (-8.8, -240.8) ± 1.6 m, d 35.7 ± 3.1 m; with d 34 m:
# (-9.2, -241.7), or (-7.0, -243.2) with that corner where Kakao's base map has it), the 1994 photo (the roof rim's line
# of centres, d 31 - 33 m) and the skyview's ring less its lean (-8, -244.6): (-8.6, -241.8) ± 1.2 m, 0.7 m out past the
# outline's face line (the roadview shows the face running smoothly into it).  North of it a flat-topped box (the 1994
# photo, the 2010 north road).  Heights from photo A through PHOTO_A (tools/build_campus.py, reference/고증.md 2.2):
# the box's north-west corner 17.2 m over the hall's floor, the drum's rim 0.2 m higher (18.4 - 18.9 m through the
# other refitted cameras).
CENT_DRUM = dict(c=(-8.6, -241.8), r=17.0, top=17.4)
CENT_BOX_TOP = 16.7               # the box's walls over the hall's floor (its coping 0.5 m over)
CENT_FACE_DRUM = 54.0             # where the box's 백양로 face meets the drum, m from the north-west corner (2011 roadview)


def centennial():
    """The 1994 · 1997 aerial photos and the 2008 · 2010 · 2011 roadview (reference/고증.md 3.4): a stone drum (the
    concert hall) at the hall's south end, a flat-topped stone box over the north part, both about as high as the
    building's four storeys, a stage house standing over them north-east of the drum.  Light granite with incised
    horizontal courses.  The 백양로 face is the box's: flat, about 17 m, over a deep porch with the museum's glass entrance
    (museum_porch), running at its south end into the drum, whose foot has curved glass (nw_lobby); the north end has
    three rows of strip windows (north_box); the low block at the south-west corner (tools/build_campus.py CENT_BLOCK)
    stands before the drum's south-west quarter, and on the east the drum comes down to the ground."""
    b = bld(324328422)
    z0 = b['base']
    fp = [tuple(p) for p in b['footprint']]
    F = [Vector(p) for p in fp]
    mb = MeshBuilder('lm_centennial')
    HP = 7.0                                       # the old podium's height: joint bands, the lobby glass's band
    c, R, HD = CENT_DRUM['c'], CENT_DRUM['r'], CENT_DRUM['top']
    HB = CENT_BOX_TOP
    A_, B_ = F[3], F[4]                            # the 백양로 (west) face, north to south
    tw = (B_ - A_).normalized()
    nw = Vector((-tw.y, tw.x))                     # into the building
    # The porch under the box's face (2011 roadview: from 6.4 m south of the north-west corner, the white wall to 14.3 m,
    # glass to 29.3 m, a white cylinder, a low wall to 38.1 m; the recess about 11 m high, 5 m deep; museum_porch)
    PD, HR = 5.0, 11.2
    X_n, X_s = A_ + tw * 6.4, A_ + tw * 38.1
    N1, N2 = X_n + nw * PD, X_s + nw * PD
    # the box: the outline north of the drum, its 백양로 face to where the drum meets it, then in under the drum and
    # across to the outline's east side (the outline's south-east vertices follow the drum's leaning roof ring in the
    # skyview, not its foot)
    sc_, dc_ = (Vector(c) - A_).dot(tw), (Vector(c) - A_).dot(nw)     # the drum's centre along / into the face
    J = A_ + tw * min(CENT_FACE_DRUM, sc_ - math.sqrt(max(R * R - dc_ * dc_, 0.0)) - 0.05)   # (where the ring crosses it)
    Jin = J + nw * 4.0
    box = [F[0], F[1], F[2], F[3], X_n, X_s, J, Jin] + F[10:]
    low = [F[0], F[1], F[2], F[3], X_n, N1, N2, X_s, J, Jin] + F[10:]          # below the porch's soffit
    nb = len(box)
    ground_walls = {2, 3, 5, 6, 7} | set(range(8, nb))                           # (0, 1: north_box; 4: over the porch)
    mb.prism(offset_poly([tuple(p) for p in low], 0.3), z0 - 4, z0 + 0.4, 'stone_granite', 'stone_granite')
    for i in range(2, nb):
        p, q = box[i], box[(i + 1) % nb]
        zb_ = HR if i == 4 else 0.4
        mb.face([(p.x, p.y, z0 + zb_), (q.x, q.y, z0 + zb_), (q.x, q.y, z0 + HB), (p.x, p.y, z0 + HB)], 'stone_ashlar')
        if i in ground_walls:
            d = (q - p).normalized()
            o = Vector((d.y, -d.x)) * 0.04
            for zz in (3.2, 6.0):
                mb.face([(*(p + o), z0 + zz), (*(q + o), z0 + zz), (*(q + o), z0 + zz + 0.14), (*(p + o), z0 + zz + 0.14)],
                        'concrete_dark')
    rim = [Vector(p) for p in offset_poly([tuple(p) for p in box], 0.12)]
    for i in range(2, nb):
        p, q = rim[i], rim[(i + 1) % nb]
        mb.quad((p.x, p.y, z0 + HB), (q.x, q.y, z0 + HB), (q.x, q.y, z0 + HB + 0.5), (p.x, p.y, z0 + HB + 0.5), 'stone_ashlar')
    mb.face([(p.x, p.y, z0 + HB + 0.5) for p in rim], 'roof_flat')
    # where the drum comes down to the ground by the face, between the box and the low block: curved glass on its foot
    # (nw_lobby), a planter of clipped box between it and the face
    K = CAMPUS.get('centennial_block')
    Xw = circle_cross(c, R, J, Jin)
    a_w = math.atan2(Xw.y - c[1], Xw.x - c[0])
    if K:
        c0, tf, tsd = Vector(K['corner']), Vector(K['t_front']), Vector(K['t_side'])
        kNW = c0 + tsd * K['side']
        kN = kNW + tf * ((A_ - kNW).dot(nw) / tf.dot(nw))                     # its north side meets the face line
        Xk = circle_cross(c, R, kNW, kNW + tf * 4.0)
        a_k = math.atan2(Xk.y - c[1], Xk.x - c[0])
    else:
        a_k = a_w + 0.4
        kN = J + tw * 4.0
    narc = max(3, int(math.ceil((a_k - a_w) / (2 * math.pi / 96))))
    ring = lambda r, a: Vector((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    arc = [ring(R, a_w + (a_k - a_w) * k / narc) for k in range(narc + 1)]
    Rp = R + 0.2
    pocket = [tuple(J)] + [tuple(ring(Rp, a_w + (a_k - a_w) * k / 6)) for k in range(7)] + [tuple(kN)]
    nw_lobby(mb, c, R, arc, z0, HP, arc, [pocket])
    # the drum, with incised horizontal joints, from the ground (inside the box and the block it is hidden), above the
    # lobby glass only from the glass's band up
    joints = [j for j in (3.2, 6.0, HP + 0.9, HP + 3.9, HP + 6.9, HP + 9.9) if j < HD - 1.5]
    o0, f0 = drum_outline(c, R, (a_w, a_k))
    oj, fj = drum_outline(c, R - 0.1, (a_w, a_k))
    z = z0 - 3.0
    tag = 'drum'
    for zj in joints + [HD - 1.2]:
        drum_band(mb, o0, f0, z, z0 + zj, 'stone_ashlar', zflat=z0 + HP + 0.9, tag=tag)
        drum_band(mb, oj, fj, z0 + zj, z0 + zj + 0.12, 'concrete_dark', zflat=z0 + HP + 0.9, tag=tag + 'j')
        z = z0 + zj + 0.12
    oc, fc = drum_outline(c, R + 0.3)
    drum_band(mb, oc, fc, z0 + HD - 1.2, z0 + HD, 'stone_ashlar', tag=tag + 'c')
    oi, _ = drum_outline(c, R - 0.5)
    zr = max(HD - 1.0, HB + 0.55)                  # its roof inside the parapet (over the box's, which runs in under it)
    n_ = len(oc)
    for i in range(n_):
        j = (i + 1) % n_
        mb.quad((*oc[i], z0 + HD), (*oc[j], z0 + HD), (*oi[j], z0 + HD), (*oi[i], z0 + HD), 'stone_ashlar')
        mb.quad((*oi[j], z0 + HD), (*oi[j], z0 + zr), (*oi[i], z0 + zr), (*oi[i], z0 + HD), 'concrete')
    mb.face([(*p, z0 + zr) for p in oi], 'roof_flat')
    # stage house: a plain stone box standing over the box and the drum north-east of the drum, with a slot window
    # (photo A x 1735 - 1910 and the 1994 photo's box over the drum's east half: its corners at about (-1, -219) and
    # (12, -225.5), its top ~6 m over the drum's)
    sh = MeshBuilder('lm_centennial_stage')
    sh.xf = local_frame(6.0, -219.5, math.radians(-8), z0)
    sh.box((0, 0, (HD + 6.5) / 2), (14.0, 12.0, HD + 6.5), 'stone_ashlar', mats={'top': 'roof_flat'})
    sh.box((0, 0, HD + 6.5 + 0.45), (14.4, 12.4, 0.9), 'stone_ashlar', skip=('bottom',))
    sh.face([(-3.0, -6.03, HD + 3.0), (3.0, -6.03, HD + 3.0), (3.0, -6.03, HD + 4.2), (-3.0, -6.03, HD + 4.2)], 'glass')
    sh.box((4.5, 3.0, HD + 8.0), (3.0, 3.0, 2.2), 'concrete', mats={'top': 'roof_flat'})
    out = [mb, sh, museum_porch(tuple(X_n), tuple(X_s), z0, HR, PD), north_box(fp[0], fp[1], fp[2], z0, HB)] + centennial_terrace()
    # the low front block before the podium's south-west corner (tools/build_campus.py CENT_BLOCK, issue #9)
    if K:
        bk = MeshBuilder('lm_centennial_block')
        Hb = K['h']

        def Q(e, a, z, out_f=0.0, out_s=0.0):
            # e along the front (east), a along the side (north), out_f out of the front (south), out_s out of the side
            p = c0 + tf * e + tsd * a - tsd * out_f - tf * out_s
            return (p.x, p.y, z0 + z)
        F, S = K['front'], K['side']
        e0, e1, he = K['entrance']
        d0, d1, hd = K['door']
        # front face (south) with the wide dark entrance, recessed 2.5 m
        bk.quad(Q(0, 0, -3), Q(e0, 0, -3), Q(e0, 0, Hb), Q(0, 0, Hb), 'stone_ashlar')
        bk.quad(Q(e1, 0, -3), Q(F, 0, -3), Q(F, 0, Hb), Q(e1, 0, Hb), 'stone_ashlar')
        bk.quad(Q(e0, 0, he), Q(e1, 0, he), Q(e1, 0, Hb), Q(e0, 0, Hb), 'stone_ashlar')
        bk.quad(Q(e0, 2.5, 0), Q(e1, 2.5, 0), Q(e1, 2.5, he), Q(e0, 2.5, he), 'void_black')        # its dark back
        bk.quad(Q(e1, 0, 0), Q(e1, 2.5, 0), Q(e1, 2.5, he), Q(e1, 0, he), 'void_black')
        bk.quad(Q(e0, 2.5, 0), Q(e0, 0, 0), Q(e0, 0, he), Q(e0, 2.5, he), 'void_black')
        bk.quad(Q(e0, 0, he), Q(e0, 2.5, he), Q(e1, 2.5, he), Q(e1, 0, he), 'void_black')          # its soffit
        bk.quad(Q(e0, 0, 0.02), Q(e1, 0, 0.02), Q(e1, 2.5, 0.02), Q(e0, 2.5, 0.02), 'stone_granite')
        bk.quad(Q(e0 + 0.4, 2.45, 0.05), Q(e1 - 0.4, 2.45, 0.05), Q(e1 - 0.4, 2.45, he - 0.3), Q(e0 + 0.4, 2.45, he - 0.3), 'glass',
                panes=(1, 1, True))
        # west side with its dark door
        bk.quad(Q(0, d0, -3), Q(0, 0, -3), Q(0, 0, Hb), Q(0, d0, Hb), 'stone_ashlar')
        bk.quad(Q(0, S, -3), Q(0, d1, -3), Q(0, d1, Hb), Q(0, S, Hb), 'stone_ashlar')
        bk.quad(Q(0, d1, hd), Q(0, d0, hd), Q(0, d0, Hb), Q(0, d1, Hb), 'stone_ashlar')
        bk.quad(Q(0.6, d1, 0), Q(0.6, d0, 0), Q(0.6, d0, hd), Q(0.6, d1, hd), 'void_black')
        bk.quad(Q(0, d0, 0), Q(0.6, d0, 0), Q(0.6, d0, hd), Q(0, d0, hd), 'void_black')
        bk.quad(Q(0.6, d1, 0), Q(0, d1, 0), Q(0, d1, hd), Q(0.6, d1, hd), 'void_black')
        bk.quad(Q(0, d0, hd), Q(0.6, d0, hd), Q(0.6, d1, hd), Q(0, d1, hd), 'void_black')
        # north side (against the podium), the roof with a coping, and a band of joints like the podium's
        bk.quad(Q(0, S, -3), Q(F, S, -3), Q(F, S, Hb), Q(0, S, Hb), 'stone_ashlar')
        bk.quad(Q(F, 0, -3), Q(F, S, -3), Q(F, S, Hb), Q(F, 0, Hb), 'stone_ashlar')
        bk.face([Q(0, 0, Hb), Q(F, 0, Hb), Q(F, S, Hb), Q(0, S, Hb)], 'roof_flat')
        for (a0, a1, b0, b1) in ((0, F, 0, 0), (0, 0, 0, S)):
            bk.box(((Q(a0, b0, 0)[0] + Q(a1, b1, 0)[0]) / 2, (Q(a0, b0, 0)[1] + Q(a1, b1, 0)[1]) / 2, z0 + Hb + 0.2),
                   (math.hypot(Q(a1, b1, 0)[0] - Q(a0, b0, 0)[0], Q(a1, b1, 0)[1] - Q(a0, b0, 0)[1]) + 0.3, 0.45, 0.4),
                   'stone_ashlar', rotz=math.atan2(Q(a1, b1, 0)[1] - Q(a0, b0, 0)[1], Q(a1, b1, 0)[0] - Q(a0, b0, 0)[0]))
        bk.quad(Q(e1, 0, 2.9, 0.04), Q(F, 0, 2.9, 0.04), Q(F, 0, 3.02, 0.04), Q(e1, 0, 3.02, 0.04), 'concrete_dark')
        # the light wall stepping up from the block's west side towards the porch (photo x 1500 - 1562)
        for (a0, a1, top) in K['parapet']:
            pa_, pb_ = Q(0, a0, 0), Q(0, a1, 0)
            bk.box(((pa_[0] + pb_[0]) / 2, (pa_[1] + pb_[1]) / 2, z0 + top / 2 - 1.5), (math.hypot(pb_[0] - pa_[0], pb_[1] - pa_[1]), 0.5, top + 3.0),
                   'stone_ashlar', rotz=math.atan2(pb_[1] - pa_[1], pb_[0] - pa_[0]))
        out.append(bk)
    return out


def rod(mb, p0, p1, r, mat, seg=8, caps=False):
    """a round tube from p0 to p1 (3D, any direction)"""
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    u = ax.cross(Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))).normalized()
    v = ax.cross(u)
    ring = lambda c: [c + (u * math.cos(2 * math.pi * k / seg) + v * math.sin(2 * math.pi * k / seg)) * r for k in range(seg)]
    a, b = ring(p0), ring(p1)
    for k in range(seg):
        j = (k + 1) % seg
        mb.quad(tuple(a[k]), tuple(a[j]), tuple(b[j]), tuple(b[k]), mat, smooth=True)
    if caps:
        mb.face([tuple(q) for q in b], mat)
        mb.face([tuple(q) for q in reversed(a)], mat)


def museum_porch(A, B, z0, HR, PD):
    """백주년기념관's museum entrance in the 백양로 porch (A north end, B south end of the porch on the face; HR the
    porch's height under the drum's flat face, PD its depth), from the 1996 graduation-album photos of 화학공학 · 전기 ·
    전파 · 전자 · 건축공학 · 기계설계 · 컴퓨터과학과 taken on its steps (2022 재상봉 기념문집; reference/백주년기념관_박물관입구_
    1996_*.jpg) and the 2008 · 2010 · 2011 roadview of the same frontage (reference/고증.md 3.4): between a tall white wall
    (left, north) and a white cylinder (right, south), both in large white panels on a square grid, glass in grey
    mullions leaning out towards its top, white tubes slanting up in front of it, the museum's long white banners
    hanging there; under it a deep dark canopy on two round dark columns over a row of aluminium-framed glass doors,
    and a broad granite flight down to the forecourt.  Right of the glass the glass runs on behind the cylinder, whose
    head stands below the glass's, over a lower white wall with a rough granite band at the canopy's height and a row of
    windows at the lobby floor, to the drum's curved foot (centennial, nw_lobby)."""
    mb = MeshBuilder('lm_centennial_museum')
    P, Le, t, n = edge_P(A, B, z0)                 # s from the north end, d > 0 out of the face (west)
    zf = 2.6                                        # the lobby floor over the hall's datum (roadview: ~4 m over 백양로)
    # the glass between the white wall and the cylinder: from 14.3 m south of the north-west corner, the cylinder's
    # middle at 32.2 m (2011 roadview 172 - 175 with their headings solved, residuals 0.1 - 0.4 m; first 13 m, 33.7 m)
    S0, S1 = 7.9, 22.9
    zcb, zct = zf + 3.7, zf + 4.5                   # canopy underside / top
    g0, g1 = zct, HR                                # the leaning glass: foot (behind the canopy) and head
    dg0, dg1 = -2.4, -0.6
    dr = -3.2                                       # the doors' plane under the canopy
    ZL = HR - 2.4                                   # the low wall right of the cylinder: its top (under the glass)
    ZC = HR - 1.2                                   # the cylinder's head, below the glass's (front photos)
    zw0, zw1 = zf + 0.9, zf + 3.7                   # the low wall's row of windows
    zb0, zb1 = zct + 0.25, zct + 0.6                # its rough granite band (and the cylinder's), over the canopy
    W, D = 'stone_panel_white', 'concrete_dark'
    # the white wall left of the glass, the full height of the porch; the drum's soffit over the porch and its ends
    flat_wall(mb, P, 0.0, S0, -3.0, HR, W)
    mb.quad(P(0.0, HR, 0), P(0.0, HR, -PD), P(Le, HR, -PD), P(Le, HR, 0), D)
    for s_ in (0.0, Le):
        mb.face([P(s_, HR, 0), P(s_, HR, -PD), P(s_, 7.0, -PD), P(s_, 7.0, 0)], W)
    # the recess: its sides under the canopy, the leaning sides beside the glass
    lean = lambda s_, f: P(s_, g0 + (g1 - g0) * f, dg0 + (dg1 - dg0) * f)
    fL = (ZL - g0) / (g1 - g0)                                              # the glass where the low wall meets it
    for s_, sg in ((S0, 1), (S1, -1)):
        q = [P(s_, zf, 0), P(s_, zf, dr), P(s_, zcb, dr), P(s_, zcb, 0)]
        mb.face(q if sg > 0 else q[::-1], W)
    mb.face([P(S0, zct, 0), P(S0, g0, dg0), P(S0, g1, dg1), P(S0, g1, 0)], W)
    mb.face([P(S1, ZL, 0), lean(S1, fL), P(S1, g0, dg0), P(S1, zct, 0)], W)  # (right of it the low wall's end)
    mb.face([P(Le, ZL, 0), P(Le, g1, 0), P(Le, g1, dg1), lean(Le, fL)], W)  # the glass's end over the low wall
    # the glass: 6 x 3 large lights in grey mullions, leaning out towards the head, and on in the same bays behind the
    # cylinder and over the low wall to the drum's foot
    mb.quad(lean(S0, 0), lean(S1, 0), lean(S1, 1), lean(S0, 1), 'glass', panes=(3, 1, True))    # the museum's hall
    mb.quad(lean(S1, fL), lean(Le, fL), lean(Le, 1), lean(S1, 1), 'glass', panes=(2, 1, True))
    bay = (S1 - S0) / 6
    for k in range(7):
        s_ = S0 + bay * k
        rod(mb, lean(s_, 0), lean(s_, 1), 0.06, 'frame_silver', seg=4)
    s_ = S1 + bay
    while s_ < Le - 0.6:
        rod(mb, lean(s_, fL), lean(s_, 1), 0.06, 'frame_silver', seg=4)
        s_ += bay
    for j in range(4):
        rod(mb, lean(S0, j / 3), lean(Le if j / 3 > fL else S1, j / 3), 0.06, 'frame_silver', seg=4)
    rod(mb, lean(S1, fL + 0.01), lean(Le, fL + 0.01), 0.06, 'frame_silver', seg=4)
    # the low wall from the glass's right edge to the drum's foot: white panels, the granite band, a row of windows
    # (behind the cylinder too), a coping, and its top back to the glass
    lw = [(S1 + 0.5, Le - 0.5, zw0, zw1)]
    wall_holes(mb, P, S1, Le, -3.0, ZL, W, lw)
    for a_, b_, za_, zb_ in lw:
        reveal(mb, P, a_, b_, za_, zb_, 0.25, W)
        glazing(mb, P, a_, b_, za_, zb_, -0.25, max(2, round((b_ - a_) / 1.6)), 1, 'frame_dark', transom=zw0 + 2.1)
    bar(mb, P, S1, (zb0 + zb1) / 2, Le, (zb0 + zb1) / 2, zb1 - zb0, 0.0, 0.06, 'stone_granite')
    bar(mb, P, S1, ZL - 0.15, Le, ZL - 0.15, 0.3, 0.0, 0.12, W)
    mb.quad(P(S1, ZL, 0), P(Le, ZL, 0), lean(Le, fL), lean(S1, fL), W)
    # the lit floors seen through it: a dark room behind, a slab edge
    mb.quad(P(S0, zct, -7.0), P(S1, zct, -7.0), P(S1, g1, -7.0), P(S0, g1, -7.0), 'hall_wall')
    zz = zf + 6.0
    mb.box(P((S0 + S1) / 2, zz, (dg0 - 7.0) / 2 + (dg1 - dg0) * ((zz - g0) / (g1 - g0)) / 2), (S1 - S0, 7.0 - 1.6, 0.3), D,
           rotz=math.atan2(t.y, t.x))
    # the white tubes slanting up in front of the glass, and the museum's banners hanging between them
    for k in range(1, 6):
        s_ = S0 + (S1 - S0) * k / 6
        rod(mb, P(s_, zct, -1.6), P(s_, HR - 0.3, 0.55), 0.2, 'paint_white', seg=10, caps=True)
    for k in (1, 2, 3, 4):
        s_ = S0 + (S1 - S0) * (k + 0.5) / 6
        zt_, zb_ = g1 - 0.2, zct + 0.5
        mb.quad(P(s_ - 0.5, zb_, 0.3), P(s_ + 0.5, zb_, 0.3), P(s_ + 0.5, zt_, 0.3), P(s_ - 0.5, zt_, 0.3), 'flag_cloth')
        mb.quad(P(s_ + 0.5, zb_, 0.3), P(s_ - 0.5, zb_, 0.3), P(s_ - 0.5, zt_, 0.3), P(s_ + 0.5, zt_, 0.3), 'flag_cloth')
        for zz in (zb_ + 0.4, zt_ - 0.8):
            mb.quad(P(s_ - 0.5, zz, 0.31), P(s_ + 0.5, zz, 0.31), P(s_ + 0.5, zz + 0.12, 0.31), P(s_ - 0.5, zz + 0.12, 0.31), 'paint_blue')
        bar(mb, P, s_ - 0.55, zt_ + 0.03, s_ + 0.55, zt_ + 0.03, 0.06, 0.25, 0.36, 'metal_dark', ends=True)
    # the canopy: a deep dark slab over the doors, its fascia the whole width
    ang = math.atan2(t.y, t.x)
    mb.box(P((S0 + S1) / 2, (zcb + zct) / 2, (dr + 0.5) / 2), (S1 - S0, 0.5 - dr, zct - zcb), D, rotz=ang)
    for sx in (S0 + 2.3, S1 - 2.3):                                          # the two round dark columns
        x_, y_, _ = P(sx, 0, -0.3)
        mb.cylinder((x_, y_), 0.45, z0 + zf, z0 + zcb, 'metal_dark', seg=18)
    # the doors and the lit lobby
    mb.quad(P(S0, zf, 0), P(S1, zf, 0), P(S1, zf, dr), P(S0, zf, dr), 'stone_granite')
    shopfront(mb, P, S0 + 0.3, S1 - 0.3, zf, zcb - 0.05, dr, bays=10, door_h=2.5)
    vestibule(mb, P, S0 + 0.3, S1 - 0.3, zf, zcb - 0.05, dr - 0.03, 5.0, lights=2)
    WALK_FACES.append([P(S0, zf, dr), P(S1, zf, dr), P(S1, zf, 0.2), P(S0, zf, 0.2)])
    # the cylinder, standing half out of the face right of the glass, a cap ring at its head (the glass rises on
    # behind it, front photos), a rough granite band at the canopy's height like the low wall's
    cx, cy, _ = P(S1 + 2.9, 0, 1.2)
    mb.cylinder((cx, cy), 2.6, z0 + zf - 1.5, z0 + ZC - 0.7, W, seg=28, cap_top=False)
    mb.cylinder((cx, cy), 2.75, z0 + ZC - 0.7, z0 + ZC, W, seg=28)
    mb.cylinder((cx, cy), 2.66, z0 + zb0, z0 + zb1, 'stone_granite', seg=28, cap_top=False)
    for k in range(1, int((ZC - 0.7 - zf) / 1.2)):
        zk = zf + k * 1.2
        if not zb0 - 0.2 < zk < zb1 + 0.2:
            mb.cylinder((cx, cy), 2.62, z0 + zk, z0 + zk + 0.04, 'stone_ashlar', seg=28, cap_top=False)
    # the flights down to 백양로: the terrace before the face (centennial_terrace; before it, one flight as wide as the
    # entrance down to the forecourt)
    if not CAMPUS.get('centennial_terrace'):
        mb.xf = Matrix.Translation(Vector(P((S0 + S1) / 2, zf, 0.2))) @ Matrix.Rotation(ang, 4, 'Z')
        stair_flight(mb, 0.0, 0.0, S1 - S0 - 2.0, 0.0, landing=1.4, tread=0.36, flare=0.6, cheek=0.5, cheek_mat='stone_granite',
                     gfn=local_ground(mb), mat='stone_step', maxrise=0.16)
        mb.xf = Matrix.Identity(4)
    return mb


def centennial_terrace():
    """The terrace before 백주년기념관's 백양로 face (tools/build_campus.py CENT_TERRACE; Kakao roadview 2008-08 ·
    2010-12, reference/고증.md 3.4): from the paved apron behind the sidewalk's ginkgo row (the trees in round pits with
    a low kerb) three broad granite flights up to the museum porch's level -- six risers (five north of the doors' axis),
    a deep landing, five between two planters of clipped shrubs, a landing, five more between two planters -- with
    coped granite side walls; south of them a dressed granite retaining wall along the apron (its coping at the first
    landing, the lawn on it), north a low planter box on the apron and a tall planter bed beside the first landing.
    Laid out in the face frame: s along the face from its north-west corner (south), d out of it (west)."""
    T = CAMPUS.get('centennial_terrace')
    if not T:
        return []
    o, tv, nv = Vector((*T['o'], 0.0)), Vector((*T['t'], 0.0)), Vector((*T['n'], 0.0))
    P = lambda s, d, z: tuple(o + tv * s + nv * d + Vector((0.0, 0.0, z)))
    r, t = T['rise'], T['tread']
    mb = MeshBuilder('lm_centennial_terrace')
    G, TRIM, STEP = 'stone_granite', 'stone_trim', 'stone_step'

    def block(sd, zt, zb, top, side, walk=False, cells=False):
        """a solid block on the (s, d) quad sd (any winding), its top at zt (one value or four), sides down to zb"""
        zt = list(zt) if isinstance(zt, (list, tuple)) else [zt] * 4
        q = [P(s, d, z) for (s, d), z in zip(sd, zt)]
        if _area2([Vector(c) for c in q]) < 0:
            q = q[::-1]
        if cells:
            uw_block(mb, q, zb, top, side, walk=walk)
            return
        oface(mb, q, top, (0, 0, 1))
        for a, b in zip(q, q[1:] + q[:1]):
            oface(mb, [(a[0], a[1], zb), (b[0], b[1], zb), (b[0], b[1], b[2]), (a[0], a[1], a[2])], side, (b[1] - a[1], a[0] - b[0], 0))
        if walk:
            WALK_FACES.append(q)

    def ramp(s0, s1, d0, z0, d1, z1):
        WALK_FACES.append([P(s0, d0, z0), P(s1, d0, z0), P(s1, d1, z1), P(s0, d1, z1)])

    def zone(s0, s1, d_top, d_foot):
        """the flight's zone for the web app (main.js clearEntrances): origin at its head, u along the face, v down it"""
        c = Vector(P((s0 + s1) / 2, d_top, 0.0))
        ENTRANCES.append(dict(o=[round(c.x, 2), round(c.y, 2)], u=[round(tv.x, 4), round(tv.y, 4)], v=[round(nv.x, 4), round(nv.y, 4)],
                              hw=round((s1 - s0) / 2, 2), len=round(d_foot - d_top + 0.6, 2)))
    F = T['flights']
    pl = T['planters']
    for fi, f in enumerate(F):
        s0, s1, d0, n, z0 = f['s0'], f['s1'], f['d0'], f['n'], f['z0']
        d_top = d0 - (n - 1) * t
        for k in range(1, n + 1):
            a, b = (f['low'] if (k == 1 and f.get('low')) else (s0, s1))
            dk = d0 - (k - 1) * t
            dd = t if k == n else t + 0.03                                    # (the top one meets the landing)
            block([(a, dk), (b, dk), (b, dk - dd), (a, dk - dd)], z0 + k * r, z0 - 0.8, STEP, STEP)
        # its walked surface (north of the doors' axis the lower flight starts a riser up) and its zones between the
        # planters
        if f.get('low'):
            lo0 = f['low'][0]
            ramp(lo0, s1, d0, z0, d_top, z0 + n * r)
            ramp(s0, lo0, d0 - t, z0 + r, d_top, z0 + n * r)
        else:
            ramp(s0, s1, d0, z0, d_top, z0 + n * r)
        ramp(s0, s1, d_top, z0 + n * r, d_top - t - 0.02, z0 + n * r)       # (its top tread, up to the landing)
        cuts = sorted(p['s'] for p in pl if p['f'] == fi)
        edges = [s0] + [v for c in cuts for v in c] + [s1]
        for a, b in zip(edges[::2], edges[1::2]):
            if b - a > 0.6:
                zone(a + 0.1, b - 0.1, d_top - 0.3, d0 + 0.3)
        # the planters: granite boxes from the flight's foot to its head, their tops sloping with it, shrubs on them
        for p in pl:
            if p['f'] != fi:
                continue
            a, b = p['s']
            block([(a, d0 + 0.02), (b, d0 + 0.02), (b, d_top - 0.5), (a, d_top - 0.5)],
                  [z0 + 0.5, z0 + 0.5, z0 + n * r + 0.45, z0 + n * r + 0.45], z0 - 0.5, 'dirt', G, walk=True)
            for (u0, u1) in ((a - 0.06, a + 0.12), (b - 0.12, b + 0.06)):        # the coped rims along their sides
                block([(u0, d0 + 0.05), (u1, d0 + 0.05), (u1, d_top - 0.53), (u0, d_top - 0.53)],
                      [z0 + 0.58, z0 + 0.58, z0 + n * r + 0.53, z0 + n * r + 0.53], z0 + 0.3, TRIM, TRIM)
            block([(a - 0.06, d0 + 0.08), (b + 0.06, d0 + 0.08), (b + 0.06, d0 - 0.1), (a - 0.06, d0 - 0.1)], z0 + 0.58, z0 - 0.3,
                  TRIM, TRIM)
    # the landings and the porch's level (granite in cells), the first between the lower and the middle flight
    l1, l2, zp = T['l1'], T['l2'], T['porch']
    fL, fM, fU = F
    dl1 = fL['d0'] - (fL['n'] - 1) * t
    dm1 = fM['d0'] - (fM['n'] - 1) * t
    du1 = fU['d0'] - (fU['n'] - 1) * t
    block([(fL['s0'], dl1 - t), (fL['s1'], dl1 - t), (fL['s1'], fM['d0']), (fL['s0'], fM['d0'])], l1, l1 - 0.8, STEP, STEP, walk=True, cells=True)
    block([(fU['s0'], dm1 - t), (fM['s1'], dm1 - t), (fM['s1'], fU['d0']), (fU['s0'], fU['d0'])], l2, l2 - 0.8, STEP, STEP, walk=True, cells=True)
    block([(fU['s0'], du1 - t), (fL['s1'], du1 - t), (fL['s1'], 0.0), (fU['s0'], 0.0)], zp, zp - 0.8, STEP, STEP, walk=True, cells=True)
    # coped side walls: south of all three flights (the lawn on the wall's side rises with them), north of the upper two
    sS = fL['s1']
    prof = [(fL['d0'], l1 + 0.08), (fM['d0'] + 0.3, l1 + 0.35), (dm1, l2 + 0.4), (fU['d0'] + 0.3, l2 + 0.4), (du1, zp + 0.4), (1.0, zp + 0.4)]
    for sa, sb, pr in ((sS, sS + 0.4, prof), (fU['s0'] - 0.4, fU['s0'], [p for p in prof if p[0] <= fM['d0'] - 0.2])):
        for (da, za), (db, zb) in zip(pr[:-1], pr[1:]):
            block([(sa, da), (sb, da), (sb, db), (sa, db)], [za - 0.1, za - 0.1, zb - 0.1, zb - 0.1], l1 - 1.2, G, G)
            block([(sa - 0.04, da), (sb + 0.04, da), (sb + 0.04, db), (sa - 0.04, db)], [za, za, zb, zb], min(za, zb) - 0.14, TRIM, TRIM)
    # the retaining wall along the apron south of the flights: dressed granite, a coping, its face on the foot line;
    # stepping down by the drum's foot, and turning back into the lawn at its south end
    dW = fL['d0']
    W = T['wall']
    for w in W:
        zb = min(T['foot'], w['top'] - 0.9) - 0.4
        block([(w['s0'], dW), (w['s1'], dW), (w['s1'], dW - 0.45), (w['s0'], dW - 0.45)], w['top'] - 0.1, zb, G, G)
        block([(w['s0'], dW + 0.05), (w['s1'], dW + 0.05), (w['s1'], dW - 0.5), (w['s0'], dW - 0.5)], w['top'], w['top'] - 0.14, TRIM, TRIM)
    we = W[-1]
    block([(we['s1'] - 0.45, dW), (we['s1'], dW), (we['s1'], dW - 4.0), (we['s1'] - 0.45, dW - 4.0)], we['top'], we['top'] - 1.4, G, TRIM)
    # the lawn on the wall: a band in the ground's own material from the coping's back down to the terrain 5 m in (the
    # 5 m grid cannot step up at the wall), walked on
    BAND = (dW - 0.5, dW - 2.5, dW - 5.5)
    for w in W:
        ss = [w['s0'] + 0.4 + k * (w['s1'] - w['s0'] - 0.4) / max(1, int(w['s1'] - w['s0'])) for k in range(int(w['s1'] - w['s0']) + 1)]
        prev = None
        for s_ in ss:
            gx, gy, _ = P(s_, BAND[2], 0.0)
            zg = ground_top(gx, gy) + 0.02
            zt_ = w['top'] - 0.1
            cur = [P(s_, BAND[0], zt_), P(s_, BAND[1], max(zg, zt_ - 0.25) if zg < zt_ else zg), P(s_, BAND[2], zg)]
            if prev:
                for a0, a1, b0, b1 in zip(prev[:-1], prev[1:], cur[:-1], cur[1:]):
                    q = [a0, b0, b1, a1]
                    oface(mb, q, 'terrain_drape', (0, 0, 1))
                    WALK_FACES.append(q)
            prev = cur
    # the planter box on the apron at the north end of the lower flight, and the bed beside the first landing
    zn = T['foot'] + r
    for key, zt in (('box', zn + T['box']['h']), ('bed', l1 + T['bed']['h'])):
        (sa, sb), (da, db) = T[key]['s'], T[key]['d']
        block([(sa, da), (sb, da), (sb, db), (sa, db)], zt - 0.12, zn - 1.0, 'dirt', G, walk=True)
        for (u0, u1, v0, v1) in ((sa, sb, db - 0.25, db), (sa, sb, da, da + 0.25), (sa, sa + 0.25, da, db), (sb - 0.25, sb, da, db)):
            block([(u0 - 0.04, v0 - 0.04), (u1 + 0.04, v0 - 0.04), (u1 + 0.04, v1 + 0.04), (u0 - 0.04, v1 + 0.04)], zt, zt - 0.4, TRIM, TRIM)
    # the apron: its paving in the ground's own material (the splat paints it), walked on; the tree pits on it
    A = T['apron']
    for (sa, ca), (sb, cb) in zip(A[:-1], A[1:]):
        for (dA0, zA0), (dA1, zA1), (dB0, zB0), (dB1, zB1) in zip(ca[:-1], ca[1:], cb[:-1], cb[1:]):
            q = [P(sa, dA0, zA0), P(sb, dB0, zB0), P(sb, dB1, zB1), P(sa, dA1, zA1)]
            oface(mb, q, 'terrain_drape', (0, 0, 1))
            WALK_FACES.append(q)
    for (sa, ca) in (A[0], A[-1]):
        lo = min(z for _, z in ca) - 0.6
        for (dA0, zA0), (dA1, zA1) in zip(ca[:-1], ca[1:]):
            oface(mb, [P(sa, dA0, lo), P(sa, dA1, lo), P(sa, dA1, zA1), P(sa, dA0, zA0)], G, tuple(tv * (-1 if sa == A[0][0] else 1)))

    def lerp_xp(x, xp, fp):
        if x <= xp[0]:
            return fp[0]
        for (x0, f0), (x1, f1) in zip(zip(xp, fp), zip(xp[1:], fp[1:])):
            if x <= x1:
                return f0 + (f1 - f0) * (x - x0) / max(x1 - x0, 1e-9)
        return fp[-1]

    def apron_z(x, y):
        q = Vector((x, y, 0.0)) - o
        s, d = q.dot(tv), q.dot(nv)
        k = max(0, min(len(A) - 2, int(s - A[0][0])))
        (sa, ca), (sb, cb) = A[k], A[k + 1]
        za = lerp_xp(-d, [-v for v, _ in ca], [z for _, z in ca])
        zb_ = lerp_xp(-d, [-v for v, _ in cb], [z for _, z in cb])
        f_ = min(1.0, max(0.0, s - sa))
        return za + (zb_ - za) * f_
    for (x, y) in T.get('pits', []):
        z = apron_z(x, y)
        mb.cylinder((x, y), 0.68, z - 0.3, z + 0.08, 'curb', seg=24, cap_top=False)
        ring = [(x + rr * math.cos(2 * math.pi * k / 24), y + rr * math.sin(2 * math.pi * k / 24)) for k in range(24) for rr in (0.68,)]
        inner = [(x + 0.56 * math.cos(2 * math.pi * k / 24), y + 0.56 * math.sin(2 * math.pi * k / 24)) for k in range(24)]
        for k in range(24):
            j = (k + 1) % 24
            oface(mb, [(*ring[k], z + 0.08), (*ring[j], z + 0.08), (*inner[j], z + 0.08), (*inner[k], z + 0.08)], 'curb', (0, 0, 1))
        oface(mb, [(*p, z + 0.03) for p in inner], 'dirt', (0, 0, 1))
    return [mb]


def north_box(A, B, C, z0, ZB=10.8):
    """백주년기념관's north end (2010 roadview from the road along its north side, reference/고증.md 3.4): the north-east
    face (A -> B, towards 광혜원) and the north-north-west side (B -> C) of the box (centennial), ZB high, three rows of
    strip windows in its lower part in the same grey panels as the podium, the plain wall above."""
    mb = MeshBuilder('lm_centennial_north')
    A, B, C = Vector(A), Vector(B), Vector(C)
    W = 'stone_ashlar'
    rows = (3.4, 6.2, 9.0)                          # sills over the hall's datum (its ground there is ~2.5 m up)
    for p, q in ((A, B), (B, C)):
        P, L, t, n = edge_P(tuple(p), tuple(q), z0)
        holes = []
        nb = max(1, int((L - 2.0) / 4.4))
        w_ = (L - 2.0) / nb
        for zs_ in rows:
            for k in range(nb):
                holes.append((1.0 + w_ * k + 0.5, 1.0 + w_ * (k + 1) - 0.5, zs_, zs_ + 0.75))
        wall_holes(mb, P, 0.0, L, -3.0, ZB, W, holes)
        for a_, b_, za_, zb_ in holes:
            reveal(mb, P, a_, b_, za_, zb_, 0.25, W)
            glazing(mb, P, a_, b_, za_, zb_, -0.25, max(2, round((b_ - a_) / 1.4)), 1, 'frame_dark')
        for zz in (3.2, 6.0):                                               # the podium's joint bands carried on
            bar(mb, P, 0.0, zz + 0.07, L, zz + 0.07, 0.14, 0.0, 0.04, 'concrete_dark')
        bar(mb, P, -0.1, ZB + 0.25, L + 0.1, ZB + 0.25, 0.5, 0.0, 0.12, W)  # the coping (the box's roof: centennial)
    return mb


# ============================================================================= gothic stone halls
def win_holes(L, z0, nfl, fh, bay, ww=0.6, sill=0.9, head=0.6, s_start=0.0, s_end=None):
    """Window openings of window_grid() with the same arguments, as (s0, s1, z0, z1) rectangles."""
    s_end = L if s_end is None else s_end
    nb = max(1, int(round((s_end - s_start) / bay)))
    bw = (s_end - s_start) / nb
    out = []
    for f in range(nfl):
        zf = z0 + f * fh
        for k in range(nb):
            w = bw * ww
            w0 = s_start + k * bw + (bw - w) / 2
            out.append((w0, w0 + w, zf + sill, zf + fh - head))
    return out


def ivy_patch(iv, P, s0, s1, z0, z1, density, seedoff=0, holes=(), top=None, cover=1.0, mask=None):
    """Boston ivy (담쟁이) on a wall rectangle, as leaf cards.

    As in the photos of 언더우드관 (1990s - 2023): the vines climb from the foot of the wall in broad vertical
    strands that merge into an almost continuous mat; each strand reaches its own height (most of them the
    eaves), and the window openings stay clear (the leaves only lap over their edges).
    holes: (s0, s1, z0, z1) openings to keep clear; top(s): wall top for gables; cover: 0..1 how much of the
    wall the strands cover; mask(s, z): False where the wall stays bare (_stone_ivy_spec).

    Every corner of a card carries its wind (corner colour, which blender/bake.py keeps for the leaves; read by
    web/src/materials.js wallLeaf): R the card's phase, G 1 - how far the corner hangs below the card's stalk (m),
    times how loose the card is: the stalk sits a quarter of the card above its middle, so the lower corners
    flutter and the upper ones stay on the vine; cards farther off the wall, at the loose tips of the strands and
    higher up the wall move more."""
    r = random.Random(int(s0 * 13 + z0 * 7 + seedoff * 101))
    rw = random.Random(int(s0 * 13 + z0 * 7 + seedoff * 101) + 7919)     # (the phases: r's sequence stays the same)
    H = z1 - z0
    ph = r.uniform(0, 6.283)

    def reach(s):      # how high the strand rooted at s has climbed (fraction of the wall)
        return (0.62 + 0.55 * cover + 0.22 * math.sin(s * 0.23 + ph) + 0.12 * math.sin(s * 0.71 + 2 * ph)
                + 0.08 * math.sin(s * 1.9 + ph))

    def thick(s, z):   # gaps between strands, and thinner growth near the top of each strand
        g = 0.5 + 0.5 * math.sin(s * 1.15 + ph + 0.6 * math.sin(z * 0.3 + s * 0.2))
        return cover * (0.62 + 0.38 * g)

    hl = [(a - 0.15, b + 0.15, c - 0.15, d + 0.1) for a, b, c, d in holes]
    area = (s1 - s0) * H
    for k in range(int(area * density)):
        s = r.uniform(s0, s1)
        z = z0 + H * (r.random() ** 0.85)                  # a little denser near the ground
        zt = z1 if top is None else min(z1, top(s))
        if z > zt:
            continue
        f = (z - z0) / H
        rf = reach(s)
        if f > rf:
            continue
        edge = 1.0 - max(0.0, (f - (rf - 0.18)) / 0.18)    # strand tips thin out
        if r.random() > thick(s, z) * edge:
            continue
        if any(a < s < b and c < z < d for a, b, c, d in hl):
            continue
        if mask is not None and not mask(s, z):
            continue
        sz = r.uniform(0.5, 0.95)
        off = r.uniform(0.04, 0.2)
        a = r.uniform(0, 6.283)
        ca, sa = math.cos(a) * sz / 2, math.sin(a) * sz / 2
        cell = r.randrange(4)
        u0, v0 = (cell % 2) * 0.5, (cell // 2) * 0.5
        dz = r.uniform(-0.1, 0.1)
        rise = [-sa - ca, sa - ca, sa + ca, -sa + ca]                 # corner heights over the card's middle
        stalk = 0.5 * max(rise)
        loose = (0.75 + 1.5 * (off - 0.04)) * (1.0 + 0.6 * (1.0 - edge)) * (0.6 + 0.4 * min(1.0, max(0.0, z / 10.0)))
        phase = rw.random()
        iv.face([P(s - ca + sa, z - sa - ca, off), P(s + ca + sa, z + sa - ca, off + dz),
                 P(s + ca - sa, z + sa + ca, off), P(s - ca - sa, z - sa + ca, off - dz)], 'leaf_ivy',
                uvs=[(u0, v0), (u0 + .5, v0), (u0 + .5, v0 + .5), (u0, v0 + .5)],
                col=[(phase, 1.0 - min(1.0, max(0.0, stalk - h) * loose), 1.0, 1.0) for h in rise])


WALK_FACES = []       # world-space quads (4 points each): the smoothed surface of every flight, exported as the invisible
                      # 'walk_stairs' mesh the walker is raycast against (web/src/main.js)


def local_ground(mb):
    """Terrain height in a builder's local frame (relative to its z origin): ground_local(lx, ly).  The top of the
    bilinear and the drawn (triangulated) surface, so that what is placed on it is never buried."""
    def g(lx, ly):
        w = mb.xf @ Vector((lx, ly, 0.0))
        return ground_top(w.x, w.y) - mb.xf.translation.z
    return g


def across(gfn, x0, x1, y, n=6):
    """Highest ground along the line y from x0 to x1: a flight's foot has to clear the whole width, not just its middle
    (on a cross slope the uphill end of the bottom tread went under the grass)."""
    return max(gfn(x0 + (x1 - x0) * k / n, y) for k in range(n + 1))


def lift_base(z0, cx, cy, ang, d, zl, rise):
    """Raise a building's floor so the landing zl stands `rise` m above the ground d m in front of its wall."""
    g = ground(cx + math.sin(ang) * d, cy - math.cos(ang) * d)
    return max(z0, g - zl + rise)


def walk_mesh():
    mb = MeshBuilder('walk_stairs')
    for q in WALK_FACES:
        mb.face(q, 'concrete')
        mb.face(q[::-1], 'concrete')
    WALK_FACES.clear()
    return mb


def stair_flight(mb, x, y_face, width, zl, n=8, mat='stone_granite', landing=1.8, tread=0.36, flare=0.35,
                 cheek=0.0, cheek_mat=None, newel=False, rail=False, ground=-1.2, zbot=-0.15, gfn=None, maxrise=0.18,
                 rail_mat='metal_dark', risers=None):
    """A straight entrance flight in a builder's local frame, going down towards -y from the wall at y_face.
    zl: top of the landing in front of the door; n risers (rise = (zl - ground_level) / n, ground_level ~ -0.15);
    each tread is a solid block down to `ground`, the lowest ones a little wider (flare) like the real granite steps.
    cheek: thickness of the low sloped side walls (0 = none); newel: a squared post with a cap at the foot of each;
    rail: slim metal handrails along the flight.  risers: a counted number of risers (with gfn), whatever their rise."""
    cheek_mat = cheek_mat or mat
    if gfn is not None:
        # as many risers as the ground in front needs: the foot of the flight stands on the terrain, all across it
        hf0 = width / 2 + flare
        for n in ([risers] if risers else range(2, 19)):
            zbot = across(gfn, x - hf0, x + hf0, y_face - landing - n * tread) - 0.04
            if (zl - zbot) / n <= maxrise:
                break
        zbot = min(zbot, zl - 0.2)
        ground = min(ground, zbot - 1.0)
    rise = (zl - zbot) / n
    mb.box((x, y_face - landing / 2 + 0.6, (zl + ground) / 2), (width, landing + 1.2, zl - ground), mat,
           mats={'top': mat})                                               # landing, running into the recess
    for k in range(1, n + 1):
        top = zl - k * rise
        y1 = y_face - landing - (k - 1) * tread
        w = width + 2 * flare * (k / n)
        mb.box((x, y1 - tread / 2 + 0.02, (top + ground) / 2), (w, tread + 0.04, top - ground), mat)
    y_foot = y_face - landing - n * tread
    # walkable surface: the landing and one smooth ramp through the middle of the treads
    hw = width / 2
    W_ = lambda lx, ly, lz: tuple(mb.xf @ Vector((lx, ly, lz)))
    # (the landing runs 1.2 m on into a recessed doorway, e.g. 대우관 별관's: walked on all the way to the door)
    WALK_FACES.append([W_(x - hw, y_face + 1.15, zl), W_(x + hw, y_face + 1.15, zl), W_(x + hw, y_face - landing, zl), W_(x - hw, y_face - landing, zl)])
    hf_ = hw + flare
    WALK_FACES.append([W_(x - hw, y_face - landing, zl), W_(x + hw, y_face - landing, zl), W_(x + hf_, y_foot, zbot), W_(x - hf_, y_foot, zbot)])
    if cheek:
        for sg in (-1, 1):
            xo = x + sg * (width / 2 + flare * 0.6 + cheek / 2)
            hz0, hz1 = zl + 0.55, zbot + 0.35
            # sloped coping wall: a wedge from the landing down to the foot of the flight
            ya, yb = y_face + 0.4, y_foot - 0.1
            xa, xb = xo - cheek / 2, xo + cheek / 2
            pts = lambda yy, zz, xx: (xx, yy, zz)
            for (x0, x1) in ((xa, xb),):
                mb.quad((x0, yb, ground), (x0, ya, ground), (x0, ya, hz0), (x0, yb, hz1), cheek_mat) if sg < 0 else \
                    mb.quad((x1, ya, ground), (x1, yb, ground), (x1, yb, hz1), (x1, ya, hz0), cheek_mat)
            mb.quad((xa, yb, hz1), (xb, yb, hz1), (xb, ya, hz0), (xa, ya, hz0), cheek_mat)       # sloping top
            mb.quad((xa, yb, ground), (xa, yb, hz1), (xb, yb, hz1), (xb, yb, ground), cheek_mat)  # foot end
            mb.quad((xb, ya, ground), (xb, ya, hz0), (xa, ya, hz0), (xa, ya, ground), cheek_mat)  # wall end
            if newel:
                mb.box((xo, yb + 0.1, hz1 + 0.35), (cheek + 0.2, cheek + 0.2, 0.9), cheek_mat)
                mb.box((xo, yb + 0.1, hz1 + 0.85), (cheek + 0.35, cheek + 0.35, 0.18), 'stone_trim')
    if rail:
        for sg in (-1, 1):
            xr = x + sg * (width / 2 + 0.05)
            yb, ya = y_foot + 0.2, y_face - landing + 0.3
            hb, ha = zbot + 0.95, zl + 0.95
            nr = 12
            for j in range(nr):
                t0, t1 = j / nr, (j + 1) / nr
                mb.quad((xr - 0.025, yb + (ya - yb) * t0, hb + (ha - hb) * t0), (xr + 0.025, yb + (ya - yb) * t0, hb + (ha - hb) * t0),
                        (xr + 0.025, yb + (ya - yb) * t1, hb + (ha - hb) * t1), (xr - 0.025, yb + (ya - yb) * t1, hb + (ha - hb) * t1), rail_mat)
            for yy in (yb, ya):
                zz = hb + (ha - hb) * ((yy - yb) / (ya - yb))
                mb.box((xr, yy, zz - 0.45), (0.06, 0.06, 0.9), rail_mat)
    note_entrance(mb, width / 2 + flare + cheek + 0.6, y_face + 1.2, y_foot - 1.0, x)
    return y_foot


def lamp_post(mb, x, y, h=3.6, globe='plaster_white', z=0.0):
    """A cast-iron post with a white globe lamp, like those beside the 대우관 별관 steps (standing on z)."""
    mb.cylinder((x, y), 0.09, z - 0.6, z + h, 'metal_dark', seg=8, cap_top=False)
    mb.cylinder((x, y), 0.17, z - 0.6, z + 0.3, 'metal_dark', seg=8, cap_top=False)
    mb.cylinder((x, y), 0.2, z + h, z + h + 0.22, globe, seg=12, r1=0.3)
    mb.cylinder((x, y), 0.3, z + h + 0.22, z + h + 0.5, globe, seg=12, r1=0.2)
    mb.cylinder((x, y), 0.22, z + h + 0.5, z + h + 0.6, 'metal_dark', seg=10)


ENTRANCES = []        # world-space zones over every entrance flight (web/public/data/entrances.json): the web app
                      # moves the clipped shrubs of the building aprons off the steps


def note_entrance(mb, hw, y0, y1, x=0.0):
    """Record the zone |x' - x| <= hw, y1 <= y <= y0 (local frame, the flight going down towards -y) of a flight."""
    o = mb.xf @ Vector((x, y0, 0.0))
    u = (mb.xf.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
    v = (mb.xf.to_3x3() @ Vector((0.0, -1.0, 0.0))).normalized()
    ENTRANCES.append(dict(o=[round(o.x, 2), round(o.y, 2)], u=[round(u.x, 4), round(u.y, 4)], v=[round(v.x, 4), round(v.y, 4)],
                          hw=round(hw, 2), len=round(y0 - y1, 2)))


def bar(mb, P, sa, za, sb, zb, w, d0, d1, mat, ends=False):
    """A square-section member in a wall plane P(s, z, d) from (sa, za) to (sb, zb), w wide, from depth d0 to d1."""
    ds, dz = sb - sa, zb - za
    L = math.hypot(ds, dz) or 1e-6
    ns, nz = -dz / L * w / 2, ds / L * w / 2
    A, B, C, D = (sa + ns, za + nz), (sb + ns, zb + nz), (sb - ns, zb - nz), (sa - ns, za - nz)
    mb.quad(P(*D, d1), P(*C, d1), P(*B, d1), P(*A, d1), mat)
    mb.quad(P(*A, d1), P(*B, d1), P(*B, d0), P(*A, d0), mat)
    mb.quad(P(*C, d1), P(*D, d1), P(*D, d0), P(*C, d0), mat)
    if ends:
        mb.quad(P(*D, d0), P(*D, d1), P(*A, d1), P(*A, d0), mat)
        mb.quad(P(*B, d0), P(*B, d1), P(*C, d1), P(*C, d0), mat)


# glazing of the old halls' front doors, from the photos: 언더우드관 a pair of leaves of small square panes under a
# glazed transom (reference/언더우드관_정면_2016.jpg, 언더우드관_2024_여름_정원.jpg), 스팀슨관 and 아펜젤러관 dark leaves
# glazed above a solid lower panel (reference/스팀슨관_정면_2016.jpg, 아펜젤러관_정면_2016.jpg), 연희관 four glazed
# leaves under a transom of upright panes (reference/연희관_정면_2023.jpg),
# 대우관 plain dark-framed glass (reference/대우관_정면_전경.jpg).  All black-painted steel, none of them wooden.
DOOR_STYLES = {
    #          leaves, panes across x up per leaf (0 = one pane), solid lower panel, members, transom panes
    'grid':   dict(leaves=2, cols=3, rows=5, panel=0.22, fw=0.09, mw=0.035, tcols=3),
    'panel':  dict(leaves=2, cols=2, rows=3, panel=0.95, fw=0.1, mw=0.04, tcols=2),
    'four':   dict(leaves=4, cols=2, rows=5, panel=0.2, fw=0.08, mw=0.035, tcols=2, plain_inner=True),
    'modern': dict(leaves=4, cols=0, rows=0, panel=0.12, fw=0.07, mw=0.0, tcols=1),
}


def glazed_door(mb, P, s0, s1, zd, zs, kind, d, style='grid'):
    """Black steel-framed glass doors and transom filling an arched opening [s0, s1] at depth d of a wall P."""
    st = DOOR_STYLES[style]
    apts = arch_points(s0, s1, zs, kind, 14)

    def arch_z(s):
        for (sa, za), (sb, zb) in zip(apts, apts[1:]):
            if sa <= s <= sb:
                return za + (zb - za) * (s - sa) / max(sb - sa, 1e-6)
        return zs
    F, G, H = 'door_frame', 'glass_door', 'frame_silver'
    fw, mw = st['fw'], st['mw']
    f0, f1 = d, d + 0.07                    # frame depth: glass at the back, members standing in front
    m1 = d + 0.04
    zt = min(zd + 2.45, zs - 0.08)          # head of the leaves = transom bar
    mb.quad(P(s0, zd, d), P(s1, zd, d), P(s1, zs, d), P(s0, zs, d), G)
    for (sa, za), (sb, zb) in zip(apts, apts[1:]):
        mb.quad(P(sa, zs, d), P(sb, zs, d), P(sb, zb, d), P(sa, za, d), G)
    # outer frame: jambs, the arch, the transom bar
    bar(mb, P, s0 + fw / 2, zd, s0 + fw / 2, zs, fw, f0, f1, F)
    bar(mb, P, s1 - fw / 2, zd, s1 - fw / 2, zs, fw, f0, f1, F)
    for (sa, za), (sb, zb) in zip(apts, apts[1:]):
        bar(mb, P, sa, za - fw / 2, sb, zb - fw / 2, fw, f0, f1, F)
    bar(mb, P, s0, zt, s1, zt, fw * 1.3, f0, f1 + 0.01, F)
    nlv = st['leaves']
    lw = (s1 - s0) / nlv
    lines = []
    for k in range(nlv):
        a, b = s0 + k * lw, s0 + (k + 1) * lw
        if k:
            bar(mb, P, a, zd, a, zt, fw * 1.2, f0, f1 + 0.01, F)          # meeting stiles
        lines.append(a)
        ia, ib = a + fw / 2, b - fw / 2
        zp = zd + st['panel']
        if st['panel'] > 0.3:            # solid lower panel with a raised field
            mb.quad(P(ia, zd, m1), P(ib, zd, m1), P(ib, zp, m1), P(ia, zp, m1), F)
            mb.quad(P(ia + 0.12, zd + 0.12, m1 + 0.015), P(ib - 0.12, zd + 0.12, m1 + 0.015), P(ib - 0.12, zp - 0.12, m1 + 0.015),
                    P(ia + 0.12, zp - 0.12, m1 + 0.015), F)
        bar(mb, P, ia, zp, ib, zp, fw, f0, f1, F)                           # bottom rail
        if st['panel'] <= 0.3:
            mb.quad(P(ia, zd, m1), P(ib, zd, m1), P(ib, zp - fw / 2, m1), P(ia, zp - fw / 2, m1), F)
        cols, rows = st['cols'], st['rows']
        if st.get('plain_inner') and 0 < k < nlv - 1:
            cols, rows = 1, 2
        for c in range(1, cols):
            s = ia + (ib - ia) * c / cols
            bar(mb, P, s, zp, s, zt, mw, f0, m1 + 0.02, F)
        for r in range(1, rows):
            z = zp + (zt - zp) * r / rows
            bar(mb, P, ia, z, ib, z, mw if cols > 1 else fw, f0, m1 + 0.02, F)
        if k in (nlv // 2 - 1, nlv // 2):
            hs = b - 0.16 if k == nlv // 2 - 1 else a + 0.16
            bar(mb, P, hs, zd + 0.95, hs, zd + 1.3, 0.03, f1, f1 + 0.06, H, ends=True)   # pull handles
    lines.append(s1)
    # transom: upright bars under the arch on the leaf lines (and between them)
    tc = max(1, st['tcols'])
    for k in range(nlv):
        for c in range(tc):
            s = lines[k] + (lines[k + 1] - lines[k]) * c / tc
            if s0 + 0.05 < s < s1 - 0.05:
                bar(mb, P, s, zt, s, arch_z(s) - 0.03, mw * 1.4 if c else fw, f0, m1 + 0.02, F)


def vestibule(mb, P, s0, s1, zf, zc, d0, depth, lights=2):
    """The entrance hall behind a glazed front door (issue #5; reference/언더우드관_정면_2016.jpg and
    언더우드관_2024_여름_정원.jpg show a bright hall and its far windows through the panes, 연희관_정면_2023.jpg the lit
    lobby through an open leaf): a shallow room [s0, s1] x [zf, zc] reaching `depth` m in from the door plane d0 of the
    wall P(s, z, d) (d < 0 inwards).  Pale stone floor, plastered walls with a stone dado, a coffered ceiling with
    lamps, and a pair of dark inner doors in the back wall.  The surfaces glow a little of their own, as no sunlight
    reaches in."""
    d1 = d0 - depth
    mb.quad(P(s0, zf, d0), P(s1, zf, d0), P(s1, zf, d1), P(s0, zf, d1), 'hall_floor')
    mb.quad(P(s0, zc, d1), P(s1, zc, d1), P(s1, zc, d0), P(s0, zc, d0), 'hall_wall')
    zw = zf + 1.0                                                  # stone dado below the plaster
    for s, sg in ((s0, 1), (s1, -1)):
        a, b = (d0, d1) if sg > 0 else (d1, d0)
        mb.quad(P(s, zf, a), P(s, zf, b), P(s, zw, b), P(s, zw, a), 'hall_floor')
        mb.quad(P(s, zw, a), P(s, zw, b), P(s, zc, b), P(s, zc, a), 'hall_wall')
    mb.quad(P(s0, zf, d1), P(s1, zf, d1), P(s1, zw, d1), P(s0, zw, d1), 'hall_floor')
    mb.quad(P(s0, zw, d1), P(s1, zw, d1), P(s1, zc, d1), P(s0, zc, d1), 'hall_wall')
    sm, dw = (s0 + s1) / 2, min(1.8, (s1 - s0) * 0.45)            # inner doors further in
    zt = min(zf + 2.4, zc - 0.25)
    mb.quad(P(sm - dw / 2, zf + 0.01, d1 + 0.02), P(sm + dw / 2, zf + 0.01, d1 + 0.02), P(sm + dw / 2, zt, d1 + 0.02),
            P(sm - dw / 2, zt, d1 + 0.02), 'wood_dark')
    bar(mb, P, sm, zf, sm, zt, 0.04, d1 + 0.02, d1 + 0.05, 'door_frame')
    bar(mb, P, sm - dw / 2 - 0.06, zt + 0.03, sm + dw / 2 + 0.06, zt + 0.03, 0.12, d1 + 0.02, d1 + 0.08, 'stone_trim', ends=True)
    for k in range(lights):                                        # ceiling lamps
        dd = d0 - depth * (k + 0.5) / lights
        mb.quad(P(sm - 0.35, zc - 0.03, dd - 0.35), P(sm + 0.35, zc - 0.03, dd - 0.35), P(sm + 0.35, zc - 0.03, dd + 0.35),
                P(sm - 0.35, zc - 0.03, dd + 0.35), 'hall_light')


def shopfront(mb, P, s0, s1, z0, z1, d, bays=6, door_h=2.35, frame='frame_silver'):
    """A modern aluminium-framed glass screen filling [s0, s1] x [z0, z1] at depth d of a wall P: fixed lights, a pair
    of glass doors in the middle bay(s), a transom bar over them (대우관's door under its podium arch)."""
    G, F = 'glass_door', frame
    mb.quad(P(s0, z0, d), P(s1, z0, d), P(s1, z1, d), P(s0, z1, d), G)
    f0, f1 = d, d + 0.08
    zt = z0 + door_h
    for k in range(bays + 1):
        s = s0 + (s1 - s0) * k / bays
        bar(mb, P, s, z0, s, z1, 0.09, f0, f1, F)
    for z in (z0 + 0.05, zt, z1 - 0.05):
        bar(mb, P, s0, z, s1, z, 0.1, f0, f1, F)
    mid = [(s0 + (s1 - s0) * k / bays) for k in (bays // 2 - 1, bays // 2, bays // 2 + 1)]
    for a, b in zip(mid, mid[1:]):                                  # the two door leaves: handles and kick rails
        hs = b - 0.18 if a == mid[0] else a + 0.18
        bar(mb, P, hs, z0 + 0.85, hs, z0 + 1.5, 0.035, f1, f1 + 0.07, F, ends=True)
        bar(mb, P, a, z0 + 0.22, b, z0 + 0.22, 0.2, f0, f1, F)


def sloped_wall(mb, x0, x1, prof, gnd, wall, cap='stone_trim', ct=0.14):
    """A solid side wall between x0 < x1 whose top follows prof [(y, z), ...] (y decreasing), down to gnd, with a pale
    stone coping ct deep along its top."""
    for (ya, za), (yb, zb) in zip(prof, prof[1:]):
        for x, sg in ((x0, -1), (x1, 1)):
            q = [(x, ya, gnd), (x, yb, gnd), (x, yb, zb - ct), (x, ya, za - ct)]
            c = [(x, ya, za - ct), (x, yb, zb - ct), (x, yb, zb), (x, ya, za)]
            if sg > 0:
                q, c = q[::-1], c[::-1]
            mb.face(q, wall)
            mb.face(c, cap)
        mb.quad((x0, ya, za), (x0, yb, zb), (x1, yb, zb), (x1, ya, za), cap)
    (ya, za), (yb, zb) = prof[0], prof[-1]
    mb.quad((x1, ya, gnd), (x0, ya, gnd), (x0, ya, za), (x1, ya, za), wall)
    mb.quad((x0, yb, gnd), (x1, yb, gnd), (x1, yb, zb), (x0, yb, zb), wall)


def pedestal(mb, x, y, top, gnd, wall, w=0.64):
    """A square stone post at the ends of a flight: rubble shaft, pale cap with a low hipped top."""
    mb.box((x, y, (gnd + top - 0.3) / 2), (w, w, top - 0.3 - gnd), wall, skip=('bottom',))
    mb.box((x, y, top - 0.21), (w + 0.12, w + 0.12, 0.18), 'stone_trim', skip=('bottom',))
    h0, h1, a, b = top - 0.12, top, (w + 0.06) / 2, 0.14
    for (p, q) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
        mb.face([(x + p[0] * a, y + p[1] * a, h0), (x + q[0] * a, y + q[1] * a, h0),
                 (x + q[0] * b, y + q[1] * b, h1), (x + p[0] * b, y + p[1] * b, h1)], 'stone_trim')
    mb.face([(x - b, y - b, h1), (x + b, y - b, h1), (x + b, y + b, h1), (x - b, y + b, h1)], 'stone_trim')


def hall_steps(mb, y_face, zl, wu, gfn, wall='stone_rubble', mat='stone_step', rec=0.9, porch=1.3, tread=0.35,
               maxrise=0.16, wl=None, cheeks=True, lamps=False, zone_hw=0.0, split_at=9):
    """The entrance steps of the old stone halls, as in reference/언더우드관_정면_2016.jpg, 스팀슨관_정면_2016.jpg and
    아펜젤러관_정면_2016.jpg:
    a porch from the door out past the arch, then granite treads of ~15 cm risers and 35 cm goings; flights of nine
    risers or more break at a landing, the lower flight a little wider.  Low rubble side walls with a pale coping
    follow the flights and end in square capped posts at the porch, at the landing and at the foot.
    Local frame: the door wall faces -y at y_face (the door itself rec m back), the porch top is zl.  split_at: from
    how many risers on the flight breaks at a landing (연희관's seventeen run in one).  Returns the y of the foot."""
    wl = wl or wu + 1.4
    T = tread
    y_p = y_face - porch
    for n in range(2, 31):
        split = n >= split_at
        nl = max(3, round(n * 0.36)) if split else 0
        nu = n - nl
        mid = 1.6 if split else 0.0
        y_foot = y_p - (nu - 1) * T - mid - (nl - 1) * T if split else y_p - (n - 1) * T
        hx = (wl if split else wu) / 2 + (0.5 if cheeks else 0.0)
        zbot = across(gfn, -hx, hx, y_foot - 0.6) - 0.03
        if (zl - zbot) / n <= maxrise:
            break
    zbot = min(zbot, zl - 0.3)
    rise = (zl - zbot) / n
    gnd = min(-1.2, zbot - 1.0)
    ct = 0.5 if cheeks else 0.0
    hu, hl = wu / 2, wl / 2
    yw = y_face + rec
    mb.box((0, (yw + y_p) / 2, (zl + gnd) / 2), (wu + 2 * ct, yw - y_p, zl - gnd), mat, skip=('bottom',))   # porch
    nup = nu if split else n
    for k in range(1, nup):
        top = zl - k * rise
        mb.box((0, y_p - (k - 0.5) * T + 0.01, (top + gnd) / 2), (wu, T + 0.02, top - gnd), mat, skip=('bottom',))
    W_ = lambda lx, ly, lz: tuple(mb.xf @ Vector((lx, ly, lz)))

    def walk(x0, x1, ya, za, yb, zb):
        WALK_FACES.append([W_(x0, ya, za), W_(x1, ya, za), W_(x1, yb, zb), W_(x0, yb, zb)])
    walk(-hu, hu, yw - 0.05, zl, y_p, zl)
    xu, xl = hu + ct / 2, hl + ct / 2
    if split:
        zm = zl - nu * rise
        yb_ = y_p - (nu - 1) * T                 # back edge of the landing
        y_m = yb_ - mid                          # its nosing
        mb.box((0, (yb_ + y_m) / 2, (zm + gnd) / 2), (wl, mid, zm - gnd), mat, skip=('bottom',))
        for j in range(1, nl):
            top = zm - j * rise
            mb.box((0, y_m - (j - 0.5) * T + 0.01, (top + gnd) / 2), (wl, T + 0.02, top - gnd), mat, skip=('bottom',))
        walk(-hu, hu, y_p, zl, y_p - nu * T, zm)
        walk(-hl, hl, yb_, zm, y_m, zm)
        walk(-hl, hl, y_m, zm, y_m - nl * T, zbot)
        if cheeks:
            for sg in (-1, 1):
                x0, x1 = sorted((sg * hu, sg * (hu + ct)))
                sloped_wall(mb, x0, x1, [(y_face, zl + 0.78), (y_p, zl + 0.78), (yb_ + 0.2, zm + rise + 0.78)], gnd, wall)
                pedestal(mb, sg * xu, y_p + 0.25, zl + 1.08, gnd, wall)
                pedestal(mb, sg * xu, yb_ + 0.05, zm + 1.0, gnd, wall)
                x0, x1 = sorted((sg * hl, sg * (hl + ct)))
                sloped_wall(mb, x0, x1, [(yb_ + 0.3, zm + 0.72), (y_m, zm + 0.72), (y_foot + 0.1, zbot + rise + 0.68)], gnd, wall)
                pedestal(mb, sg * xl, y_m + 0.25, zm + 0.98, gnd, wall)
                pedestal(mb, sg * xl, y_foot + 0.25, zbot + 0.95, gnd, wall)
    else:
        walk(-hu, hu, y_p, zl, y_p - n * T, zbot)
        if cheeks:
            for sg in (-1, 1):
                x0, x1 = sorted((sg * hu, sg * (hu + ct)))
                sloped_wall(mb, x0, x1, [(y_face, zl + 0.78), (y_p, zl + 0.78), (y_foot + 0.1, zbot + rise + 0.7)], gnd, wall)
                pedestal(mb, sg * xu, y_p + 0.25, zl + 1.08, gnd, wall)
                pedestal(mb, sg * xu, y_foot + 0.25, zbot + 0.97, gnd, wall)
    if lamps:
        for sg in (-1, 1):
            lamp_post(mb, sg * (max(hu, hl if split else hu) + 1.9), y_foot - 0.5)
    note_entrance(mb, max(zone_hw, (hl if split else hu) + ct + 0.6), y_face + 0.5, y_foot - 1.0)
    return y_foot


def side_steps(mb, y_face, zl, gfn, sg, hw, y_wall, wall='stone_rubble', mat='stone_step', rec=0.5, fw=2.0, land=1.6,
               T=0.32, maxrise=0.16):
    """The front steps of a hall that stands close to the road before it (교육관's east front over the drive, seen from
    its porch in reference/2003_봄_교육관에서_본_연희관앞정원과_성암관.jpg: the coped side wall of the flight runs down
    along the wall to the north): a landing land m deep before the door, from beyond the door's other side to hw m
    past it on the side sg (+1: +x), then one flight fw m wide down along the wall that way, a solid wall between it and
    the hall's wall at y_wall, a coped side wall on the open side round the landing and the flight, capped posts.
    Local frame of stone_hall: the door's wall faces -y at y_face, the landing's top zl."""
    yo = y_face - land                              # the landing's outer edge
    yw = y_face + rec
    ya, yb = yo, yo + fw                            # the flight, between its open side and the inner wall
    x0 = sg * hw                                    # its head
    for n in range(2, 31):
        x_foot = x0 + sg * (n - 1) * T
        zbot = max(gfn(x_foot + sg * 0.6, ya + (yb - ya) * k / 4) for k in range(5)) - 0.03
        if (zl - zbot) / n <= maxrise:
            break
    zbot = min(zbot, zl - 0.3)
    rise = (zl - zbot) / n
    gnd = min(-1.2, zbot - 1.0)
    xl0 = -sg * (hw + 0.2)                          # the landing's far end
    xa, xb = sorted((xl0, x0))
    mb.box(((xa + xb) / 2, (yw + yo) / 2, (zl + gnd) / 2), (xb - xa, yw - yo, zl - gnd), mat, skip=('bottom',))
    for k in range(1, n):
        top = zl - k * rise
        mb.box((x0 + sg * (k - 0.5) * T, (ya + yb) / 2, (top + gnd) / 2), (T + 0.02, fw, top - gnd), mat, skip=('bottom',))
    x_end = x0 + sg * (n - 1) * T
    W_ = lambda lx, ly, lz: tuple(mb.xf @ Vector((lx, ly, lz)))
    WALK_FACES.append([W_(xa, yw - 0.05, zl), W_(xb, yw - 0.05, zl), W_(xb, yo, zl), W_(xa, yo, zl)])
    WALK_FACES.append([W_(x0, ya, zl), W_(x0, yb, zl), W_(x0 + sg * n * T, yb, zbot), W_(x0 + sg * n * T, ya, zbot)])
    if yb < y_wall - 0.05:                          # the solid wall between the flight and the hall
        xi = sg * (hw - 0.45)                       # (from the porch's side, closing the corner by it)
        uw_wall(mb, (xi, (yb + y_wall) / 2), (x_end + sg * 0.1, (yb + y_wall) / 2),
                lambda f: zl + 0.45 + (zbot + rise + 0.4 - zl - 0.45) * max(0.0, (abs(xi + (x_end - xi) * f) - abs(x0)) / max(1e-3, abs(x_end - x0))),
                gnd, gfn, t=y_wall - yb, wall=wall, clear=-9, n=6)
    xs0, xs1 = xl0 - sg * 0.16, x_end + sg * 0.15         # the open side: round the landing, then down beside the flight
    span = abs(xs1 - xs0)
    def outer_top(f):
        x = xs0 + (xs1 - xs0) * f
        g = sg * (x - x0) / max(1e-3, abs(x_end - x0))
        return zl + 0.85 if g <= 0 else zl + 0.85 + (zbot + rise + 0.8 - zl - 0.85) * min(1.0, g)
    uw_wall(mb, (xs0, yo - 0.16), (xs1, yo - 0.16), outer_top, gnd, gfn, t=0.32, wall=wall, clear=-9, n=10)
    uw_wall(mb, (xl0 - sg * 0.16, yo - 0.32), (xl0 - sg * 0.16, y_wall), lambda f: zl + 0.85, gnd, gfn, t=0.32, wall=wall, clear=-9, n=2)
    for x_, top in ((xl0 - sg * 0.16, zl + 1.15), (x0, zl + 1.15), (x_end + sg * 0.25, zbot + rise + 1.1)):
        pedestal(mb, x_, yo - 0.16, top, gnd, wall, w=0.5)
    note_entrance(mb, span / 2 + 0.6, y_face + 0.5, yo - 1.0, x=(xs0 + xs1) / 2)
    return yo


def flat_portal(mb, W, plinth, fh, wall, bw=7.4, gfn=None):
    """대우관 별관's front door (reference/대우관_별관_정면_현관.jpg): a squared, slightly projecting central bay
    in pale stone, a rectangular glass double door deep in a recess under a flat lintel carrying a round medallion,
    stepped pilasters, red diamond tiles beside it, rusticated blocks on the wall corners, and two flights of steps with
    stone planters and round shrubs.  Local frame: front is -y, the wall plane is y = -W/2."""
    y0, pj = -W / 2, 1.3
    yf = y0 - pj
    zb = plinth + fh + 1.4                      # top of the bay
    ow, zo = 3.5, plinth + 3.7                  # opening width / top
    zd = plinth - 0.1                           # threshold
    for sg in (-1, 1):                          # piers either side of the opening
        xc = sg * (ow + (bw - ow) / 2) / 2 + sg * ow / 4 * 0
        mb.box((sg * (ow / 2 + (bw - ow) / 4), y0 - pj / 2, (zb - 0.5) / 2), ((bw - ow) / 2, pj, zb + 0.5), wall)
        mb.box((sg * (bw / 2 - 0.2), yf - 0.1, (zb + zd) / 2), (0.4, 0.2, zb - zd), 'stone_trim')       # stepped pilaster
    mb.box((0, y0 - pj / 2, (zb + zo) / 2), (ow, pj, zb - zo), wall)                                 # lintel
    mb.box((0, yf - 0.1, zb + 0.12), (bw + 0.5, pj + 0.25, 0.26), 'stone_trim')                       # cornice
    mb.box((0, yf - 0.05, zo - 0.08), (ow + 0.3, 0.12, 0.16), 'stone_trim')
    # back of the recess with the glass double door and a glazed transom
    yb = y0 - 0.03
    mb.quad((-ow / 2, yb, zd), (ow / 2, yb, zd), (ow / 2, yb, zo), (-ow / 2, yb, zo), wall)
    dw, dh = 2.9, 3.0
    mb.quad((-dw / 2, yb - 0.02, zd), (dw / 2, yb - 0.02, zd), (dw / 2, yb - 0.02, zd + dh), (-dw / 2, yb - 0.02, zd + dh), 'glass', panes=(1, 1, True))
    mb.quad((-dw / 2, yb - 0.02, zd + dh + 0.1), (dw / 2, yb - 0.02, zd + dh + 0.1), (dw / 2, yb - 0.02, zo - 0.15), (-dw / 2, yb - 0.02, zo - 0.15), 'glass', panes=(1, 1, True))
    for x in (-dw / 2, 0.0, dw / 2):
        mb.box((x, yb - 0.05, (zd + zo - 0.15) / 2), (0.1, 0.06, zo - 0.15 - zd), 'frame_dark')
    for z in (zd + dh + 0.05, zd + 0.05, zo - 0.15):
        mb.box((0, yb - 0.05, z), (dw + 0.1, 0.06, 0.1), 'frame_dark')
    for sg in (-1, 1):
        mb.box((sg * (ow / 2 - 0.05), y0 - pj / 2, (zd + zo) / 2), (0.1, pj, zo - zd), 'stone_trim')    # reveals
    # round medallion over the door
    cz, r = (zo + zb) / 2 + 0.02, 0.5
    ring = [(r * math.cos(2 * math.pi * i / 16), cz + r * math.sin(2 * math.pi * i / 16)) for i in range(16)]
    mb.face([(x, yf - 0.02, z) for x, z in ring][::-1], 'stone_trim')
    ring2 = [(0.72 * x, cz + 0.72 * (z - cz)) for x, z in ring]
    mb.face([(x, yf - 0.05, z) for x, z in ring2][::-1], 'plaster_cream')
    # red diamond tiles and rusticated corner blocks on the wall either side of the bay
    for sg in (-1, 1):
        dx, dz = sg * (bw / 2 + 2.1), zb - 0.1
        mb.face([(dx, y0 - 0.03, dz - 0.32), (dx + 0.32, y0 - 0.03, dz), (dx, y0 - 0.03, dz + 0.32), (dx - 0.32, y0 - 0.03, dz)][::-1], 'brick_red')
        for k in range(5):
            mb.box((sg * (bw / 2 + 0.7), y0 - 0.05, plinth + 0.5 + k * 0.62), (0.8 if k % 2 else 0.55, 0.12, 0.5), 'stone_trim')
    # two flights: a narrow one to the door between planters, then a wide one with handrails
    zl = plinth - 0.1
    zm = zl / 2 + 0.05
    y1 = stair_flight(mb, 0, yf, ow + 1.1, zl, n=4, landing=1.2, tread=0.38, flare=0.0, zbot=zm)
    for sg in (-1, 1):
        px = sg * (ow / 2 + 0.55 + 0.9)
        ph = zl - zm + 0.85
        mb.box((px, (yf + y1) / 2, zm - 0.1 + ph / 2 - 0.05), (1.6, yf - y1 + 1.2, ph), 'stone_trim', mats={'top': 'soil'})
        for dxy, rr in (((0.0, 0.2), 0.85), ((0.0, -1.2), 0.6)):
            c = (px + dxy[0], (yf + y1) / 2 + dxy[1])
            mb.cylinder(c, rr, zm + ph - 0.15, zm + ph + 0.35, 'shrub_green', seg=10, r1=rr * 0.9)
            mb.cylinder(c, rr * 0.85, zm + ph + 0.35, zm + ph + 0.62, 'shrub_green', seg=10, r1=rr * 0.5)
    y2 = stair_flight(mb, 0, y1, 9.5, zm, n=5, landing=2.2, tread=0.36, flare=0.3, rail=True, gfn=gfn)
    for sg in (-1, 1):                                       # a round shrub at each side of the lower flight
        c = (sg * 6.4, y1 - 2.0)
        mb.cylinder(c, 1.0, -0.3, 0.7, 'shrub_green', seg=12, r1=1.05)
        mb.cylinder(c, 1.0, 0.7, 1.15, 'shrub_green', seg=12, r1=0.5)
    return y2


def stone_base(mb, poly, plinth, wall, gap=None):
    """The basement storey of the stone halls: the wall's own stone down into the ground (dark granite under the white
    halls), and a pale water table where the ground floor starts.  gap: (side, s0, s1, z) a doorway cut through both
    from z up, on the side poly[side] -> poly[side + 1] (s along it; a rectangle's)."""
    if wall == 'stone_white':
        # (the white stone carried on down where the ground falls away -- 대우관's wings, reference/대우관_측면_2012.jpg
        # -- over a granite course at the foot of the ground floor)
        mb.prism(offset_poly(poly, 0.25), -4, plinth - 0.35, 'stone_white')
        mb.prism(offset_poly(poly, 0.3), plinth - 0.35, plinth, 'stone_granite', 'stone_granite')
        return
    if gap is None:
        mb.prism(offset_poly(poly, 0.25), -4, plinth - 0.3, wall)
        mb.prism(offset_poly(poly, 0.33), plinth - 0.3, plinth, 'stone_trim', 'stone_trim')
        return
    k, s0, s1, zg = gap
    for off, za, zb, mat, top in ((0.25, -4, plinth - 0.3, wall, None), (0.33, plinth - 0.3, plinth, 'stone_trim', 'stone_trim')):
        q = offset_poly(poly, off)
        cap = []
        for i in range(len(q)):
            a, b = q[i], q[(i + 1) % len(q)]
            cap.append(a)
            if i != k:
                mb.face([(a[0], a[1], za), (b[0], b[1], za), (b[0], b[1], zb), (a[0], a[1], zb)], mat)
                continue
            P, Le, t, n = edge_P(a, b)
            g0, g1, z_ = s0 + off, s1 + off, max(za, zg)    # (the mitred corner adds off at each end of the side)
            mb.quad(P(0, za), P(g0, za), P(g0, zb), P(0, zb), mat)
            mb.quad(P(g1, za), P(Le, za), P(Le, zb), P(g1, zb), mat)
            if z_ > za:
                mb.quad(P(g0, za), P(g1, za), P(g1, z_), P(g0, z_), mat)
            cap += [P(g0, 0)[:2], P(g0, 0, -off)[:2], P(g1, 0, -off)[:2], P(g1, 0)[:2]]
        if top:
            mb.face([(p[0], p[1], zb) for p in cap], top)


def basement_windows(mb, P, s0, s1, bay, plinth, gfn, wall, ww=0.5):
    """Low windows of the half-sunk basement (반지하층 of 스팀슨관, 지하층 of 언더우드관 and 아펜젤러관), one under each
    ground-floor window, wherever the ground leaves them clear."""
    if wall == 'stone_white' or s1 - s0 < 1.0:
        return
    nb = max(1, int(round((s1 - s0) / bay)))
    bw = (s1 - s0) / nb
    z0, z1, d = plinth - 1.15, plinth - 0.45, 0.27
    for k in range(nb):
        sc, w = s0 + (k + 0.5) * bw, bw * ww
        g = [gfn(*P(sc + o, 0, 1.0)[:2]) for o in (-w / 2, w / 2)]
        if max(g) > z0 - 0.12:
            continue
        mb.quad(P(sc - w / 2, z0, d), P(sc + w / 2, z0, d), P(sc + w / 2, z1, d), P(sc - w / 2, z1, d), 'glass')
        bar(mb, P, sc, z0, sc, z1, 0.07, d, d + 0.05, 'frame_dark')
        bar(mb, P, sc - w / 2 - 0.1, z0 - 0.06, sc + w / 2 + 0.1, z0 - 0.06, 0.12, 0.25, d + 0.08, 'stone_trim', ends=True)
        bar(mb, P, sc - w / 2 - 0.06, z1 + 0.07, sc + w / 2 + 0.06, z1 + 0.07, 0.14, 0.25, d + 0.05, 'stone_trim', ends=True)


def gothic(name, b, front, floors, tower_w=8.5, tower_extra=8.0, ivy=1.0, wings=True, fh=4.1, wall='stone_rubble',
           dormers=True, stairs=None, portal=None, door=None, z_floor=None, rear=None, tower_floors=None):
    # tower_floors: the tower's storeys when it has more than the hall (연희관: one in the hall's roof); default floors
    cx, cy, L, W, ang, z0 = frame_for(b, front)
    stairs = dict(dict(width=None, wl=None, rise=1.3, cheeks=True, lamps=False, none=False, split=9, maxrise=0.16),
                  **(stairs or {}))
    door = dict(dict(w=3.0, arch='tudor', spring=2.55, style='grid'), **(door or {}))
    # the floor stands on the ground in front of the door, not at the lowest corner of the footprint (the halls sit on
    # slopes: 대우관 별관's front is ~3 m above that corner and would bury the whole flight); `rise` is how high the
    # porch stands over the ground just in front of the hall.  z_floor: the door threshold given outright (대우관, whose
    # front ground build_campus.py has reshaped round its podium)
    if z_floor is None:
        z0 = lift_base(z0, cx, cy, ang, W / 2 + (1.8 if portal == 'flat' else 3.3), 1.2, stairs['rise'])
    else:
        z0 = z_floor - 1.2
    mb = MeshBuilder('lm_' + name)
    iv = MeshBuilder('lm_' + name + '_ivy')
    mb.xf = iv.xf = local_frame(cx, cy, ang, z0)
    plinth = 1.3
    Hw = plinth + floors * fh + 0.6
    pitch = 0.9
    gl = local_ground(mb)
    # --- main block walls
    body = rect(L, W)
    stone_base(mb, body, plinth, wall)
    for i in range(4):
        a, bb = body[i], body[(i + 1) % 4]
        P, Le, t, n = edge_P(a, bb)
        if Le < W + 0.1:          # gable ends
            window_grid(mb, P, Le, plinth, floors, fh, 3.4, wall, ww=0.42, trim='stone_trim', mull=1)
            basement_windows(mb, P, 0, Le, 3.4, plinth, gl, wall, ww=0.42)
            flat_wall(mb, P, 0, Le, plinth + floors * fh, Hw, wall)
            # gable triangle + coping
            hz = Hw + (Le / 2) * pitch
            mb.face([P(0, Hw), P(Le, Hw), P(Le / 2, hz)], wall)
            mb.quad(P(-0.2, Hw, 0.25), P(Le / 2, hz + 0.35, 0.25), P(Le / 2, hz + 0.35, -0.2), P(-0.2, Hw, -0.2), 'stone_trim')
            mb.quad(P(Le / 2, hz + 0.35, 0.25), P(Le + 0.2, Hw, 0.25), P(Le + 0.2, Hw, -0.2), P(Le / 2, hz + 0.35, -0.2), 'stone_trim')
            if ivy:
                ivy_patch(iv, P, 0, Le, 0, hz - 0.4, 5.5, i, cover=ivy,
                          holes=win_holes(Le, plinth, floors, fh, 3.4, ww=0.42),
                          top=lambda s, Le=Le: Hw + (Le / 2 - abs(s - Le / 2)) * pitch - 0.4)
        else:
            front_side = (i == 0)
            if not front_side and rear is not None:
                rear(mb, P, Le, plinth, floors, fh, Hw, wall)      # a back of its own (대우관), no buttresses
                continue
            if front_side:
                tw = tower_w
                s_t0, s_t1 = Le / 2 - tw / 2, Le / 2 + tw / 2
                if portal == 'flat':
                    window_grid(mb, P, Le, plinth, floors, fh, 3.3, wall, ww=0.55, trim='stone_trim', mull=2)
                else:
                    window_grid(mb, P, Le, plinth, floors, fh, 3.3, wall, ww=0.5, trim='stone_trim', mull=2, s_start=0, s_end=s_t0)
                    window_grid(mb, P, Le, plinth, floors, fh, 3.3, wall, ww=0.5, trim='stone_trim', mull=2, s_start=s_t1, s_end=Le)
                    flat_wall(mb, P, s_t0, s_t1, plinth, Hw, wall)
                    for (a_, b_) in ((0, s_t0), (s_t1, Le)):
                        if wings:      # the end pavilions stand in front of the outer bays
                            a_, b_ = max(a_, 8.0 if a_ == 0 else a_), min(b_, Le - 8.0 if b_ == Le else b_)
                        basement_windows(mb, P, a_, b_, 3.3, plinth, gl, wall)
            else:
                window_grid(mb, P, Le, plinth, floors, fh, 3.3, wall, ww=0.5, trim='stone_trim', mull=2)
                basement_windows(mb, P, 0, Le, 3.3, plinth, gl, wall)
            flat_wall(mb, P, 0, Le, plinth + floors * fh, Hw, wall)
            # buttresses
            nbut = int(round(Le / 6.6))
            for k in range(1, nbut):
                s = k * Le / nbut
                if front_side and abs(s - Le / 2) < tower_w / 2 + 1:
                    continue
                c = P(s, 0, 0.3)
                mb.box((c[0], c[1], plinth + (Hw - plinth - 1.5) / 2), (0.7, 0.6, Hw - plinth - 1.5), wall,
                       rotz=math.atan2(t.y, t.x), mats={'top': 'stone_trim'})
                if ivy:        # the vines climb the buttress fronts too
                    ivy_patch(iv, lambda ss, zz, dd=0.0: P(ss, zz, dd + 0.6), s - 0.4, s + 0.4, 0, Hw - 1.2, 5.5,
                              i * 3 + k * 17, cover=ivy)
            # parapet with battlements along the eaves
            nm = int(Le / 1.6)
            for k in range(nm):
                if k % 2 == 0:
                    c = P((k + 0.5) * Le / nm, Hw + 0.45, 0.0)
                    mb.box(c, (Le / nm, 0.45, 0.9), 'stone_trim', rotz=math.atan2(t.y, t.x), skip=('bottom',))
            if ivy:
                if front_side:
                    # (none behind the tower: hidden there anyway, and it would grow into the entrance hall)
                    holes = (win_holes(Le, plinth, floors, fh, 3.3, ww=0.5, s_end=s_t0)
                             + win_holes(Le, plinth, floors, fh, 3.3, ww=0.5, s_start=s_t1)
                             + ([(s_t0 - 0.3, s_t1 + 0.3, -1.0, Hw + 1.0)] if portal != 'flat' else []))
                else:
                    holes = win_holes(Le, plinth, floors, fh, 3.3, ww=0.5)
                ivy_patch(iv, P, 0, Le, 0, Hw + 0.3, 5.5, i * 3, cover=ivy, holes=holes)
    # --- slate roof (gable along L)
    hz = Hw + (W / 2) * pitch
    A, B, C, D = (-L / 2, -W / 2 - 0.3, Hw - 0.3 * pitch), (L / 2, -W / 2 - 0.3, Hw - 0.3 * pitch), (L / 2, W / 2 + 0.3, Hw - 0.3 * pitch), (-L / 2, W / 2 + 0.3, Hw - 0.3 * pitch)
    R1, R2 = (-L / 2, 0, hz), (L / 2, 0, hz)
    mb.face([A, B, R2, R1], 'roof_slate')
    mb.face([C, D, R1, R2], 'roof_slate')
    mb.box((0, 0, hz + 0.1), (L, 0.35, 0.3), 'metal_dark')
    # dormers on the front roof slope
    for k in (range(-2, 3) if dormers else ()):
        if k == 0:
            continue
        x = k * L / 6
        zb_ = Hw + 0.8
        mb.box((x, -W / 4 + 0.4, zb_ + 1.0), (1.8, 1.6, 2.0), wall, mats={'front': 'glass'})
        mb.face([(x - 1.0, -W / 4 - 0.5, zb_ + 2.0), (x + 1.0, -W / 4 - 0.5, zb_ + 2.0), (x, -W / 4 - 0.5, zb_ + 3.0)], 'stone_trim')
        mb.face([(x - 1.0, -W / 4 - 0.5, zb_ + 2.0), (x, -W / 4 - 0.5, zb_ + 3.0), (x, -W / 4 + 1.2, zb_ + 3.0), (x - 1.0, -W / 4 + 1.2, zb_ + 2.0)][::-1], 'roof_slate')
        mb.face([(x + 1.0, -W / 4 - 0.5, zb_ + 2.0), (x + 1.0, -W / 4 + 1.2, zb_ + 2.0), (x, -W / 4 + 1.2, zb_ + 3.0), (x, -W / 4 - 0.5, zb_ + 3.0)][::-1], 'roof_slate')
    # --- end pavilions projecting forward with front gables
    if wings:
        for sgn in (-1, 1):
            pw = 8.0
            x0 = sgn * (L / 2 - pw / 2)
            proj = 1.6
            yb = -W / 2 - proj
            P, Le, t, n = edge_P((x0 - pw / 2, yb), (x0 + pw / 2, yb))
            window_grid(mb, P, Le, plinth, floors, fh, 4.0, wall, ww=0.55, trim='stone_trim', mull=2)
            basement_windows(mb, P, 0, Le, 4.0, plinth, gl, wall, ww=0.55)
            flat_wall(mb, P, 0, Le, plinth + floors * fh, Hw, wall)
            ghz = Hw + pw / 2 * 1.1
            mb.face([P(0, Hw), P(Le, Hw), P(Le / 2, ghz)], wall)
            mb.quad(P(-0.2, Hw, 0.25), P(Le / 2, ghz + 0.35, 0.25), P(Le / 2, ghz + 0.35, -0.2), P(-0.2, Hw, -0.2), 'stone_trim')
            mb.quad(P(Le / 2, ghz + 0.35, 0.25), P(Le + 0.2, Hw, 0.25), P(Le + 0.2, Hw, -0.2), P(Le / 2, ghz + 0.35, -0.2), 'stone_trim')
            # sides of the projection
            for (sx, ex) in ((x0 - pw / 2, -1), (x0 + pw / 2, 1)):
                pa, pb = ((sx, -W / 2), (sx, yb)) if ex < 0 else ((sx, yb), (sx, -W / 2))
                P2, Le2, _, _ = edge_P(pa, pb)
                flat_wall(mb, P2, 0, Le2, -4, Hw, wall)
            stone_base(mb, [(x0 - pw / 2, yb), (x0 + pw / 2, yb), (x0 + pw / 2, -W / 2), (x0 - pw / 2, -W / 2)], plinth, wall)
            # little gable roof over the projection
            mb.face([(x0 - pw / 2 - 0.3, yb - 0.3, Hw - 0.2), (x0, yb - 0.3, ghz), (x0, -W / 4, ghz), (x0 - pw / 2 - 0.3, -W / 4, Hw - 0.2)][::-1], 'roof_slate')
            mb.face([(x0 + pw / 2 + 0.3, yb - 0.3, Hw - 0.2), (x0 + pw / 2 + 0.3, -W / 4, Hw - 0.2), (x0, -W / 4, ghz), (x0, yb - 0.3, ghz)][::-1], 'roof_slate')
            if ivy:
                ivy_patch(iv, P, 0, Le, 0, ghz - 0.4, 5.5, sgn * 7, cover=ivy,
                          holes=win_holes(Le, plinth, floors, fh, 4.0, ww=0.55),
                          top=lambda s, Le=Le: Hw + (Le / 2 - abs(s - Le / 2)) * 1.1 - 0.4)
    if portal == 'flat':
        flat_portal(mb, W, plinth, fh, wall, bw=tower_w + 0.4, gfn=local_ground(mb))
        mb.z_base = z0
        return [mb, iv]
    # --- central tower
    tw = tower_w
    tproj = 3.0
    Ht = Hw + tower_extra
    ty0 = -W / 2 - tproj
    tower = [(-tw / 2, ty0), (tw / 2, ty0), (tw / 2, ty0 + tw), (-tw / 2, ty0 + tw)]
    stone_base(mb, tower, plinth, wall)
    for i in range(4):
        a, bb = tower[i], tower[(i + 1) % 4]
        P, Le, t, n = edge_P(a, bb)
        if i == 0:
            # entrance: a moulded four-centred (Tudor) arch over glazed steel doors set back in the reveal, then a
            # mullioned window for each floor above, as on the tower fronts in the photos; clock-less belfry openings
            ow = door['w']
            e0, e1 = Le / 2 - ow / 2, Le / 2 + ow / 2
            zd = plinth - 0.1
            kind = door['arch']
            zs = zd + door['spring']
            apts = arch_points(e0, e1, zs, kind, 14)
            zap = max(z for _, z in apts)
            rec, band = 0.9, 0.3
            zt = zap + band + 0.15
            flat_wall(mb, P, 0, e0 - band, -0.5, Ht, wall)
            flat_wall(mb, P, e1 + band, Le, -0.5, Ht, wall)
            flat_wall(mb, P, e0 - band, e1 + band, zt, Ht, wall)
            flat_wall(mb, P, e0, e1, -0.5, zd, wall)
            for (a_, b_) in ((e0 - band, e0), (e1, e1 + band)):              # stone jambs of the surround
                flat_wall(mb, P, a_, b_, -0.5, zt, 'stone_trim', d=0.05)
                mb.quad(P(a_, -0.5, 0), P(a_, -0.5, 0.05), P(a_, zt, 0.05), P(a_, zt, 0), 'stone_trim')
                mb.quad(P(b_, -0.5, 0.05), P(b_, -0.5, 0), P(b_, zt, 0), P(b_, zt, 0.05), 'stone_trim')
            arch_fill(mb, lambda s_, z_, d_=0.0: P(s_, z_, d_ + 0.05), e0 - band, e1 + band, zs, zt, 0.05, 'stone_trim', kind, 14)
            arch_fill(mb, lambda s_, z_, d_=0.0: P(s_, z_, d_ + 0.08), e0 - band, e1 + band, zs + band * 0.2, zt, 0.001, wall, kind, 14)
            mb.quad(P(e0 - band, zt, 0.05), P(e1 + band, zt, 0.05), P(e1 + band, zt, 0), P(e0 - band, zt, 0), 'stone_trim')
            arch_fill(mb, P, e0, e1, zs, zt, rec, 'stone_trim', kind, 14)     # soffit of the deep reveal
            mb.quad(P(e0, zd, 0), P(e0, zd, -rec), P(e0, zs, -rec), P(e0, zs, 0), 'stone_trim')
            mb.quad(P(e1, zd, -rec), P(e1, zd, 0), P(e1, zs, 0), P(e1, zs, -rec), 'stone_trim')
            glazed_door(mb, P, e0, e1, zd, zs, kind, -rec + 0.02, door['style'])
            # the entrance hall seen through the glass: as deep as the tower stands out from the main wall
            vestibule(mb, P, e0 - 0.5, e1 + 0.5, zd, min(zap + 0.3, zd + 4.4), -rec - 0.01, tproj - rec - 0.05)
            wins = []
            for f in range(1, tower_floors or floors):
                w0, w1 = Le / 2 - min(1.3, tw * 0.15), Le / 2 + min(1.3, tw * 0.15)
                zw0, zw1 = plinth + f * fh + 0.9, plinth + (f + 1) * fh - 0.6
                if zw0 < zt + 0.3:          # a tall door (대우관's pointed arch) takes the first window's place
                    continue
                wins.append((w0, w1, zw0, zw1))
                mb.quad(P(w0, zw0, 0.02), P(w1, zw0, 0.02), P(w1, zw1, 0.02), P(w0, zw1, 0.02), 'glass')
                for sm in (w0 + (w1 - w0) / 3, w0 + 2 * (w1 - w0) / 3):
                    bar(mb, P, sm, zw0, sm, zw1, 0.14, 0.02, 0.1, 'stone_trim')
                bar(mb, P, w0, zw0 + (zw1 - zw0) * 0.7, w1, zw0 + (zw1 - zw0) * 0.7, 0.1, 0.02, 0.08, 'stone_trim')
                for (a_, b_, za_, zb_) in ((w0 - 0.18, w0, zw0 - 0.18, zw1 + 0.2), (w1, w1 + 0.18, zw0 - 0.18, zw1 + 0.2),
                                          (w0 - 0.18, w1 + 0.18, zw0 - 0.18, zw0), (w0 - 0.28, w1 + 0.28, zw1, zw1 + 0.22)):
                    bar(mb, P, a_, (za_ + zb_) / 2, b_, (za_ + zb_) / 2, zb_ - za_, 0.0, 0.12, 'stone_trim', ends=True)
        else:
            flat_wall(mb, P, 0, Le, -0.5 if i != 2 else Hw, Ht, wall)
        # belfry louvres
        bw0, bw1 = Le / 2 - 0.9, Le / 2 + 0.9
        mb.quad(P(bw0, Ht - 4.5, 0.03), P(bw1, Ht - 4.5, 0.03), P(bw1, Ht - 1.5, 0.03), P(bw0, Ht - 1.5, 0.03), 'metal_dark')
        arch_fill(mb, P, bw0, bw1, Ht - 1.5, Ht - 0.4, 0.0001, 'stone_trim', 'pointed', 6)
        # string course
        mb.quad(P(-0.15, Hw, 0.18), P(Le + 0.15, Hw, 0.18), P(Le + 0.15, Hw + 0.3, 0.18), P(-0.15, Hw + 0.3, 0.18), 'stone_trim')
        # battlements
        nm = 5
        for k in range(nm):
            if k % 2 == 0:
                c = P((k + 0.5) * Le / nm, Ht + 0.55, 0.05)
                mb.box(c, (Le / nm, 0.55, 1.1), 'stone_trim', rotz=math.atan2(t.y, t.x), skip=('bottom',))
        if ivy:
            holes = [(bw0, bw1, Ht - 4.5, Ht - 0.4)]
            if i == 0:
                holes += [(e0 - band - 0.25, e1 + band + 0.25, -1.0, zt + 0.3)] + [(a_ - 0.35, b_ + 0.35, za_ - 0.3, zb_ + 0.35) for a_, b_, za_, zb_ in wins]
            ivy_patch(iv, P, 0, Le, Hw if i == 2 else 0, Ht - 0.5, 5.5, 11 + i, cover=ivy * 0.95, holes=holes)
    mb.face([(p[0], p[1], Ht) for p in tower], 'roof_flat')
    # corner pinnacles
    for (px_, py_) in tower:
        mb.box((px_, py_, Ht + 0.9), (0.9, 0.9, 1.8), 'stone_trim', skip=('bottom',))
        mb.face([(px_ - .45, py_ - .45, Ht + 1.8), (px_ + .45, py_ - .45, Ht + 1.8), (px_, py_, Ht + 3.2)], 'stone_trim')
        mb.face([(px_ + .45, py_ - .45, Ht + 1.8), (px_ + .45, py_ + .45, Ht + 1.8), (px_, py_, Ht + 3.2)], 'stone_trim')
        mb.face([(px_ + .45, py_ + .45, Ht + 1.8), (px_ - .45, py_ + .45, Ht + 1.8), (px_, py_, Ht + 3.2)], 'stone_trim')
        mb.face([(px_ - .45, py_ + .45, Ht + 1.8), (px_ - .45, py_ - .45, Ht + 1.8), (px_, py_, Ht + 3.2)], 'stone_trim')
    # entrance steps: porch, granite flights with a landing, rubble side walls and capped posts
    sw = stairs['width'] or min(tw * 0.5, 4.4)
    if not stairs['none']:
        hall_steps(mb, ty0, plinth - 0.1, sw, local_ground(mb), wall=wall, wl=stairs['wl'], cheeks=stairs['cheeks'],
                   lamps=stairs['lamps'], split_at=stairs['split'], maxrise=stairs['maxrise'])
    mb.tower_front = ty0
    mb.tower_info = (ty0, tw, Ht)
    mb.z_base = z0
    return [mb, iv]


def underwood():
    # the porch stands ~2.5 m over the garden walk (about 16 risers in the 2016 photo: five, a landing, then the rest)
    return gothic('underwood', bld(246156115), (0.27, -1.0), 3, tower_w=9.0, tower_extra=9.5, ivy=1.0,
                  stairs=dict(width=4.2, wl=5.8, rise=2.45), door=dict(w=3.0, style='grid'))


# ============================================================================= 스팀슨관 (1920) · 아펜젤러관 (1924)
# Two storeys over a half-sunk basement under a long slate roof with coped gable ends: no tower, battlements, buttresses
# or dormers (reference/스팀슨관_정면_2016.jpg, 아펜젤러관_정면_2016.jpg, 학교연혁_*.jpg; in the 1994 aerial photo both are
# low halls beside 언더우드관's garden showing it their gable ends).  Tall double-hung lights side by side in threes
# between stone mullions, a stone sill under each group and a flat lintel over it, rubble wall between the groups.
# Heights read off the two photos (~37 - 40 px/m at the walls): the ground-floor lights 0.8 - 2.75 m over the floor,
# the upper ones 0.75 - 3.15 m, 3.3 m storeys, the wall top ~7.4 m over the water table; the roof rises ~3.6 m over
# its 7.3 m half width (pitch ~0.5, from where the coped gables' tops fall in the photos' perspective).
LIGHTS = ((0.8, 2.75), (0.75, 3.15))      # sill and head of the lights over each floor


def oface(mb, pts, mat, nrm):
    """A planar face whose winding is chosen so that it faces nrm (local coordinates)."""
    n = Vector()
    for p, q in zip(pts, pts[1:] + pts[:1]):
        n += Vector(((p[1] - q[1]) * (p[2] + q[2]), (p[2] - q[2]) * (p[0] + q[0]), (p[0] - q[0]) * (p[1] + q[1])))
    mb.face(pts if n.dot(Vector(nrm)) >= 0 else pts[::-1], mat)


def split_lights(g0, g1, n, mw=0.2, ratios=None):
    """n lights over [g0, g1] between mullions mw wide, as (s0, s1); ratios: their relative widths."""
    ratios = ratios or [1.0] * n
    w = (g1 - g0 - mw * (len(ratios) - 1)) / sum(ratios)
    out, s = [], g0
    for r in ratios:
        out.append((s, s + w * r))
        s += w * r + mw
    return out


def light_group(mb, P, g0, g1, zs, zh, n, mw=0.2, ratios=None, depth=0.3, trim='stone_trim', frame='frame_dark'):
    """n tall lights side by side in one opening [g0, g1] x [zs, zh] of a wall P(s, z, d) (the wall round it is
    wall_holes'): stone mullions and reveals, a projecting sill under the group, a flat lintel over it and slim stone
    jambs; dark double-hung sashes with small panes in the upper one.  One glass pane behind the whole group: one room
    seen through its lights (common.py pane_uv)."""
    lights = split_lights(g0, g1, n, mw, ratios)
    reveal(mb, P, g0, g1, zs, zh, depth, trim)
    mb.quad(P(g0, zs, -depth), P(g1, zs, -depth), P(g1, zh, -depth), P(g0, zh, -depth), 'glass', panes=(1, 1))
    for (_, b), (c, _) in zip(lights, lights[1:]):
        bar(mb, P, (b + c) / 2, zs, (b + c) / 2, zh, c - b, -depth, 0.0, trim)
    f0, f1 = -depth + 0.005, -depth + 0.06
    zm = zs + (zh - zs) * 0.56                                    # the meeting rails of the sashes
    for a, b in lights:
        fw = min(0.06, (b - a) * 0.12)
        for s in (a + fw / 2, b - fw / 2):
            bar(mb, P, s, zs, s, zh, fw, f0, f1, frame)
        for z in (zs + fw / 2, zh - fw / 2):
            bar(mb, P, a, z, b, z, fw, f0, f1, frame)
        bar(mb, P, a, zm, b, zm, 0.07, f0, f1 + 0.02, frame)
        for k in (1, 2):                                          # upper sash: 3 x 2 panes, lower: two tall ones
            s = a + (b - a) * k / 3
            bar(mb, P, s, zm, s, zh, 0.03, f0, f1 - 0.015, frame)
        bar(mb, P, a, (zm + zh) / 2, b, (zm + zh) / 2, 0.03, f0, f1 - 0.015, frame)
        bar(mb, P, (a + b) / 2, zs, (a + b) / 2, zm, 0.03, f0, f1 - 0.015, frame)
    bar(mb, P, g0 - 0.14, zs - 0.08, g1 + 0.14, zs - 0.08, 0.16, 0.0, 0.12, trim, ends=True)       # sill
    bar(mb, P, g0 - 0.12, zh + 0.14, g1 + 0.12, zh + 0.14, 0.28, 0.0, 0.035, trim, ends=True)      # lintel
    for s in (g0 - 0.06, g1 + 0.06):
        bar(mb, P, s, zs, s, zh, 0.12, 0.0, 0.035, trim)


def hall_door(mb, P, sc, zd, door, depth, wall='stone_rubble'):
    """A Tudor-arched doorway centred at sc in a wall P, as in reference/스팀슨관_정면_2016.jpg: ashlar jambs and an
    arch ring standing a little proud of the rubble, a deep reveal, the black steel glazed doors (glazed_door) and the
    lit hall behind (vestibule, depth m in).  Returns the opening to leave out of the wall, (s0, s1, top), and the
    ivy's hole."""
    ow = door['w']
    e0, e1 = sc - ow / 2, sc + ow / 2
    kind, zs = door['arch'], zd + door['spring']
    zap = max(z for _, z in arch_points(e0, e1, zs, kind, 14))
    rec, band = door['rec'], 0.35
    zt = zap + band + 0.15
    for (a_, b_) in ((e0 - band, e0), (e1, e1 + band)):              # stone jambs of the surround
        flat_wall(mb, P, a_, b_, zd - 0.2, zt, 'stone_trim', d=0.05)
        mb.quad(P(a_, zd - 0.2, 0), P(a_, zd - 0.2, 0.05), P(a_, zt, 0.05), P(a_, zt, 0), 'stone_trim')
        mb.quad(P(b_, zd - 0.2, 0.05), P(b_, zd - 0.2, 0), P(b_, zt, 0), P(b_, zt, 0.05), 'stone_trim')
    arch_fill(mb, lambda s_, z_, d_=0.0: P(s_, z_, d_ + 0.05), e0 - band, e1 + band, zs, zt, 0.05, 'stone_trim', kind, 14)
    arch_fill(mb, lambda s_, z_, d_=0.0: P(s_, z_, d_ + 0.08), e0 - band, e1 + band, zs + band * 0.2, zt, 0.001, wall, kind,
              14)                                              # (the rubble spandrels over the arch ring)
    mb.quad(P(e0 - band, zt, 0.05), P(e1 + band, zt, 0.05), P(e1 + band, zt, 0), P(e0 - band, zt, 0), 'stone_trim')
    arch_fill(mb, P, e0, e1, zs, zt, rec, 'stone_trim', kind, 14)      # soffit of the reveal
    mb.quad(P(e0, zd, 0), P(e0, zd, -rec), P(e0, zs, -rec), P(e0, zs, 0), 'stone_trim')
    mb.quad(P(e1, zd, -rec), P(e1, zd, 0), P(e1, zs, 0), P(e1, zs, -rec), 'stone_trim')
    glazed_door(mb, P, e0, e1, zd, zs, kind, -rec + 0.02, door['style'])
    vestibule(mb, P, e0 - 0.5, e1 + 0.5, zd, min(zap + 0.3, zd + 4.4), -rec - 0.01, depth)
    return (e0 - band, e1 + band, zt), (e0 - band - 0.25, e1 + band + 0.25, -1.0, zt + 0.3)


def _stone_ivy_spec(ivy, walls, w):
    """The ivy of one wall of a stone_hall, (cover, z top, mask), as the photos of each wall show it (reference/
    고증.md 3.5): walls {key: cover, or dict(cover=, zmax=, ends=(a, b))}, key 0 the front, 1 / 3 the ends (1 the +x
    one), 2 the back, 'porch', 'bays', 'end_bay'; walls not named take the hall's ivy.  zmax: the strands climb only
    that high over the plinth's foot (their tips thinning as on a full wall), ends: they grow only within a m of the
    wall's first corner and b m of its last, the edge wavering by ~0.5 m.  w: (key, the wall's length)."""
    if not ivy:
        return 0.0, None, None
    key, Le = w if w else (None, 0.0)
    spec = (walls or {}).get(key, ivy)
    if not isinstance(spec, dict):
        return spec, None, None
    ends = spec.get('ends')
    mask = None
    if ends:
        def mask(s, z):
            d = 0.35 * math.sin(z * 1.3 + s) + 0.2 * math.sin(z * 3.7)
            return s < ends[0] + d or s > Le - ends[1] - d
    return spec.get('cover', ivy), spec.get('zmax'), mask


def stone_hall(name, b, front, groups, ivy=1.0, fh=3.3, wall='stone_rubble', pitch=0.5, door_group=None, porch=None,
               bays=None, back=(), chimney=None, door=None, stairs=None, floors=2, plinth=1.3, basement=True,
               dormers=(), end_wins=None, z0=None, rect_fp=None, extra=None, attic=None, end_bay=None, rear=None,
               ivy_walls=None):
    """스팀슨관 · 아펜젤러관 (see above), 성암관 and 교육관.  groups: the front's window groups (s0, s1, lights) on every
    floor, s along the front from its left end seen from outside; door_group: the one whose ground-floor place the front
    door takes; porch: a central entrance bay standing forward to a flat parapet a little over the eaves (스팀슨관,
    성암관), or, with top under the eaves, a lower one the wall above it carries on over (교육관); bays: canted bays
    standing forward through both floors to curved coped parapets (아펜젤러관); back: extra groups of the back wall
    (in the place of the porch or bays); chimney: dict(at=(x, y) local, h=its top over the ridge, sky=(x, y): a
    skylight on the back slope).  floors over a
    plinth (basement: a half-sunk storey with low windows under it), dormers: long shed dormers (x0, x1, lights) in
    the local x on both slopes, end_wins: {edge: [(g0, g1, lights, floor)]} for the gable ends (1: the +x end, 3: the
    -x end; g along the edge from its first corner), attic: {edge: (g, width, z0, z1)} a single light in the gable
    (z over the wall top), end_bay: a canted bay standing out of a gable end (스팀슨관's south end), rear: the stair
    window over the back door in the middle of the back wall (스팀슨관, 아펜젤러관), z0: the floor level, rect_fp: the
    main block's corners when the outline takes in a bay, extra(mb, iv, frame): further parts in the local frame,
    ivy_walls: the ivy of single walls (_stone_ivy_spec)."""
    cx, cy, L, W, ang, z0_ = frame_for(dict(b, footprint=rect_fp) if rect_fp else b, front)
    stairs = dict(dict(width=3.6, wl=None, rise=1.3, cheeks=True, lamps=False), **(stairs or {}))
    door = dict(dict(w=2.2, arch='tudor', spring=1.9, style='panel', rec=0.6), **(door or {}))
    z0 = lift_base(z0_ if z0 is None else z0, cx, cy, ang, W / 2 + 3.3, plinth - 0.1, stairs['rise'])
    mb = MeshBuilder('lm_' + name)
    iv = MeshBuilder('lm_' + name + '_ivy')
    mb.xf = iv.xf = local_frame(cx, cy, ang, z0)
    gl = local_ground(mb)
    zd = plinth - 0.1                          # door threshold = top of the entrance porch
    Hw = plinth + floors * fh + 0.8            # wall top
    hz = Hw + W / 2 * pitch                    # ridge
    eave = 0.4
    fl = [(plinth + f * fh + LIGHTS[min(f, 1)][0], plinth + f * fh + LIGHTS[min(f, 1)][1]) for f in range(floors)]
    body = rect(L, W)
    rd = None
    if rear:
        # the back door, in the middle of the back wall (s from its +x end), at the stair's landing half a storey
        # under the ground floor, a riser or two over the yard behind
        P2 = edge_P(body[2], body[3])[0]
        dw, dh = rear['door']
        g = max(gl(*P2(L / 2 + o, 0, 1.0)[:2]) for o in (-dw / 2 - 0.4, 0.0, dw / 2 + 0.4))
        zr0 = min(max(plinth + rear['zd'], g + 0.03), plinth - 0.35)
        rd = (L / 2 - dw / 2, L / 2 + dw / 2, zr0, zr0 + dh, g)
    stone_base(mb, body, plinth, wall, gap=(2, rd[0], rd[1], rd[2]) if rd else None)
    rz = lambda t: math.atan2(t.y, t.x)

    def windows(P, wins, holes, s0=-1e9, s1=1e9):
        """wins: (g0, g1, lights, floor[, ratios, mullion]); adds their openings (and the ivy's) to holes"""
        for w in wins:
            g0, g1, nl, f = w[:4]
            if g1 <= s0 or g0 >= s1:
                continue
            ratios = w[4] if len(w) > 4 else None
            mw = w[5] if len(w) > 5 else 0.2
            light_group(mb, P, g0, g1, fl[f][0], fl[f][1], nl, mw=mw, ratios=ratios)
            if f == 0 and basement:
                basement_windows(mb, P, g0, g1, (g1 - g0) / nl, plinth, gl, wall, ww=0.62)
            holes.append((g0, g1, fl[f][0], fl[f][1]))

    def profile_wall(P, prof, zb, d=0.0, inner=None, cope=True):
        """A wall face over zb whose top follows prof [(s, z), ...]; inner: the depth of its back face (a parapet),
        cope: a stone coping along the top"""
        for (sa, za), (sb, zb_) in zip(prof, prof[1:]):
            for dd, sg in ((d, 1), (inner, -1)):
                if dd is None:
                    continue
                pts = [P(sa, zb, dd), P(sb, zb, dd)] + [P(s_, z_, dd) for s_, z_ in ((sb, zb_), (sa, za)) if z_ > zb + 1e-4]
                if len(pts) > 2:
                    mb.face(pts if sg > 0 else pts[::-1], wall)
            if cope:
                bar(mb, P, sa, za + 0.05, sb, zb_ + 0.05, 0.14, (inner if inner is not None else -0.3) - 0.04, d + 0.08,
                    'stone_trim')

    def ivy_wall(P, s0, s1, z1, holes, seed, top=None, w=None):
        cover, zmax, mask = _stone_ivy_spec(ivy, ivy_walls, w)
        if cover:
            ivy_patch(iv, P, s0, s1, 0, min(z1, zmax or z1), 5.5, seed, cover=cover, holes=holes, top=top, mask=mask)

    def rear_middle(P, holes, ivh):
        """The middle of the back wall (the 2013 survey's rear elevations, in 안대환 2016): the stair's lights, three
        tall ones at the landing between the floors (and on 아펜젤러관 three low ones under the eaves at the next),
        over the back door; a small window either side of the door under one lintel; steps down to the yard."""
        a, b, zr0, zr1, g = rd
        c, hw = (a + b) / 2, rear['w'] / 2
        for zs, zh in rear['lights']:
            light_group(mb, P, c - hw, c + hw, plinth + zs, plinth + zh, 3)
            holes.append((c - hw, c + hw, plinth + zs, plinth + zh))
        sw, sh = rear['side']
        for s in (a - 0.3 - sw, b + 0.3):
            light_group(mb, P, s, s + sw, zr1 - sh, zr1, 1, depth=0.25)
            holes.append((s, s + sw, max(zr1 - sh, plinth), zr1))
        holes.append((a, b, plinth, zr1))
        ivh.append((c - hw - 0.3, c + hw + 0.3, -1.0, plinth + rear['lights'][-1][1] + 0.3))
        reveal(mb, lambda s, z, d=0.0: P(s, z, d + 0.33), a, b, zr0, zr1, 0.63, 'stone_trim')
        for s0_, s1_ in ((a - 0.2, a - 0.002), (b + 0.002, b + 0.2)):           # the door's stone jambs
            bar(mb, P, (s0_ + s1_) / 2, zr0 - 0.05, (s0_ + s1_) / 2, zr1, s1_ - s0_, 0.0, 0.34, 'stone_trim')
        bar(mb, P, a - 0.45 - sw, zr1 + 0.16, b + 0.45 + sw, zr1 + 0.16, 0.3, 0.0, 0.36, 'stone_trim', ends=True)
        zt = zr1 - 0.42                                     # a boarded door under a transom light
        mb.quad(P(a, zr0, -0.3), P(b, zr0, -0.3), P(b, zt, -0.3), P(a, zt, -0.3), 'wood_dark')
        mb.quad(P(a, zt, -0.3), P(b, zt, -0.3), P(b, zr1, -0.3), P(a, zr1, -0.3), 'glass', panes=(1, 1))
        bar(mb, P, a, zt, b, zt, 0.08, -0.3, -0.24, 'frame_dark')
        for k in range(1, 4):
            s = a + (b - a) * k / 4
            bar(mb, P, s, zr0 + 0.05, s, zt - 0.04, 0.025, -0.3, -0.285, 'frame_dark')
        n = int(math.ceil((zr0 - g - 0.08) / 0.17))
        ang_ = rz(Vector(P(1, 0)) - Vector(P(0, 0)))
        for k in range(n):                                  # (granite steps, each one tread further out)
            zt_, zb_ = zr0 - k * (zr0 - g) / n, g - 0.25
            dd = 0.34 + 0.32 * (k + 1)
            mb.box(P(c, (zt_ + zb_) / 2, dd / 2), (b - a + 0.7, dd, zt_ - zb_), 'stone_step', rotz=ang_, skip=('bottom',))

    # --- the four walls
    hidden = []                                # front spans the porch or the bays stand in front of
    low_porch = bool(porch) and porch.get('top') is not None and porch['top'] < Hw
    if porch and not low_porch:
        hidden.append((porch['s0'], porch['s1']))
    for s0, s1 in (bays or {}).get('at', ()):
        hidden.append((s0, s1))
    for i in range(4):
        P, Le, t, n = edge_P(body[i], body[(i + 1) % 4])
        holes, ivh = [], []
        if Le < W + 0.1:                       # gable ends: two pairs of lights a floor, a coped gable over the roof
            wins = (end_wins or {}).get(i) or [(Le / 2 + a, Le / 2 + b, 2, f) for a, b in ((-4.4, -2.2), (2.2, 4.4))
                                               for f in range(floors)]
            windows(P, wins, holes)
            wall_holes(mb, P, 0, Le, plinth, Hw, wall, holes)
            rl = lambda s, Le=Le: Hw + (Le / 2 - abs(s - Le / 2)) * pitch        # the roof's top over the wall line
            pr = 0.32                                                            # the parapet over the roof
            if (attic or {}).get(i):
                # a single light high in the gable (the attic storey's, or a vent), the gable round it in pieces
                g, aw, za, zb = attic[i]
                a_, b_, za, zb = g - aw / 2, g + aw / 2, Hw + za, Hw + zb
                sl = lambda z: (z - Hw - pr) / pitch                             # where the coping line is at z
                light_group(mb, P, a_, b_, za, zb, 1)
                holes.append((a_, b_, za, zb))
                mb.face([P(0, Hw), P(Le, Hw), P(Le, Hw + pr), P(Le - sl(za), za), P(sl(za), za), P(0, Hw + pr)], wall)
                mb.face([P(sl(za), za), P(a_, za), P(a_, zb), P(sl(zb), zb)], wall)
                mb.face([P(b_, za), P(Le - sl(za), za), P(Le - sl(zb), zb), P(b_, zb)], wall)
                mb.face([P(sl(zb), zb), P(Le - sl(zb), zb), P(Le / 2, hz + pr)], wall)
            else:
                mb.face([P(0, Hw), P(Le, Hw), P(Le, Hw + pr), P(Le / 2, hz + pr), P(0, Hw + pr)], wall)
            mb.quad(P(Le / 2, hz, -0.42), P(0, Hw, -0.42), P(0, Hw + pr, -0.42), P(Le / 2, hz + pr, -0.42), wall)
            mb.quad(P(Le, Hw, -0.42), P(Le / 2, hz, -0.42), P(Le / 2, hz + pr, -0.42), P(Le, Hw + pr, -0.42), wall)
            ce = eave * pitch
            bar(mb, P, -0.45, Hw + pr + 0.07 - 0.45 * pitch, Le / 2, hz + pr + 0.07, 0.2, -0.5, 0.1, 'stone_trim')
            bar(mb, P, Le / 2, hz + pr + 0.07, Le + 0.45, Hw + pr + 0.07 - 0.45 * pitch, 0.2, -0.5, 0.1, 'stone_trim')
            for s in (-0.15, Le + 0.15):       # kneelers at the foot of the copings, over the ends of the eaves
                kb, kt = Hw - ce - 0.1, Hw + pr + 0.12
                mb.box(P(s, (kb + kt) / 2, -0.2), (0.55, 0.5, kt - kb), 'stone_trim', rotz=rz(t))
            ivy_wall(P, 0, Le, hz - 0.4, holes, i, top=lambda s, rl=rl: rl(s) - 0.4, w=(i, Le))
            continue
        front_side = (i == 0)
        if front_side:
            wins = [(g0, g1, nl, f) for k, (g0, g1, nl) in enumerate(groups) for f in range(floors)
                    if not (f == 0 and k == door_group)]
            spans, s = [], 0.0
            for a, b_ in sorted(hidden):
                spans.append((s, a))
                s = b_
            spans.append((s, Le))
            if door_group is not None:         # the door in the front wall itself (아펜젤러관)
                g0, g1, _ = groups[door_group]
                dh, dhole = hall_door(mb, P, (g0 + g1) / 2, zd, door, 3.0, wall)
                holes.append((dh[0], dh[1], -1.0, dh[2]))
                ivh.append(dhole)
        else:
            wins = [(g0, g1, nl, f) for g0, g1, nl in list(groups) + list(back) for f in range(floors)
                    if not (rd and i == 2 and g1 > rd[0] - 0.5 and g0 < rd[1] + 0.5)]
            spans = [(0.0, Le)]
            if rd and i == 2:
                rear_middle(P, holes, ivh)
        for s0, s1 in spans:
            windows(P, wins, holes, s0, s1)
        for s0, s1 in spans:
            wall_holes(mb, P, s0, s1, plinth, Hw, wall, [h for h in holes if h[1] > s0 and h[0] < s1])
            ivy_wall(P, s0, s1, Hw + 0.3, holes + ivh, i * 3 + int(s0), w=(i, Le))
        bar(mb, P, -0.05, Hw - 0.15, Le + 0.05, Hw - 0.15, 0.3, 0.0, 0.12, 'stone_trim', ends=True)   # cornice
    # --- slate roof (gable along L), plain eaves with a gutter
    ze = Hw - eave * pitch
    A, B, C, D = (-L / 2, -W / 2 - eave, ze), (L / 2, -W / 2 - eave, ze), (L / 2, W / 2 + eave, ze), (-L / 2, W / 2 + eave, ze)
    R1, R2 = (-L / 2, 0, hz), (L / 2, 0, hz)
    mb.face([A, B, R2, R1], 'roof_slate')
    mb.face([C, D, R1, R2], 'roof_slate')
    mb.box((0, 0, hz + 0.05), (L, 0.32, 0.16), 'roof_slate', skip=('bottom',))       # ridge tiles
    for sg in (-1, 1):
        mb.box((0, sg * (W / 2 + eave - 0.04), ze - 0.05), (L, 0.08, 0.12), 'roof_slate')      # fascia
        oface(mb, [(-L / 2, sg * W / 2, ze - 0.02), (L / 2, sg * W / 2, ze - 0.02), (L / 2, sg * (W / 2 + eave), ze - 0.02),
                   (-L / 2, sg * (W / 2 + eave), ze - 0.02)], 'stone_trim', (0, 0, -1))         # soffit
    if chimney:
        # 스팀슨관's dressed-stone chimney astride the ridge, left of the porch (reference/스팀슨관_정면_2016.jpg and
        # 스팀슨관_측면_2016.jpg; from the back road its foot meets the ridge, the 2010 / 2011 roadview; 10.5 m from the
        # south end in the 2013 survey's attic plan): a broad base on the ridge, a square shaft, a moulded cap and a
        # low domed top, its top ~3 m over the ridge
        x, y = chimney['at']
        zt_ = hz + chimney['h']
        zb_ = hz - (0.6 + abs(y)) * pitch - 0.15
        z1, z2 = hz + 0.45, zt_ - 0.85
        mb.box((x, y, (zb_ + z1) / 2), (1.2, 1.2, z1 - zb_), 'stone_trim', skip=('bottom',))
        mb.box((x, y, (z1 + z2) / 2), (0.8, 0.8, z2 - z1), 'stone_trim', skip=('bottom', 'top'))
        mb.box((x, y, z2 + 0.06), (0.92, 0.92, 0.12), 'stone_trim', skip=('bottom',))
        mb.box((x, y, z2 + 0.25), (1.05, 1.05, 0.26), 'stone_trim', skip=('bottom',))
        ring = [(0.0, 0.46), (0.17, 0.42), (0.33, 0.3), (0.43, 0.14), (0.48, 0.0)]     # the dome: (rise, radius)
        oc = [(math.cos(math.pi / 8 + math.pi / 4 * k), math.sin(math.pi / 8 + math.pi / 4 * k)) for k in range(8)]
        zd_ = z2 + 0.38
        for (h0_, r0_), (h1_, r1_) in zip(ring, ring[1:]):
            for (c0, s0_), (c1, s1_) in zip(oc, oc[1:] + oc[:1]):
                mb.face([(x + r0_ * c0, y + r0_ * s0_, zd_ + h0_), (x + r0_ * c1, y + r0_ * s1_, zd_ + h0_),
                         (x + r1_ * c1, y + r1_ * s1_, zd_ + h1_), (x + r1_ * c0, y + r1_ * s0_, zd_ + h1_)][:4 if r1_ else 3],
                        'stone_trim', smooth='chimney_dome')
        if chimney.get('sky'):                 # a small skylight on the back slope below it
            sx, sy = chimney['sky']
            zr_ = lambda yy: hz - yy * pitch + 0.06
            mb.face([(sx - 0.35, sy - 0.45, zr_(sy - 0.45)), (sx + 0.35, sy - 0.45, zr_(sy - 0.45)),
                     (sx + 0.35, sy + 0.45, zr_(sy + 0.45)), (sx - 0.35, sy + 0.45, zr_(sy + 0.45))], 'metal_dark')
            mb.face([(sx - 0.28, sy - 0.38, zr_(sy - 0.38) + 0.01), (sx + 0.28, sy - 0.38, zr_(sy - 0.38) + 0.01),
                     (sx + 0.28, sy + 0.38, zr_(sy + 0.38) + 0.01), (sx - 0.28, sy + 0.38, zr_(sy + 0.38) + 0.01)],
                    'glass_reflect')
    y_face = -W / 2
    if porch:
        # 스팀슨관's entrance bay: rubble, the door in an ashlar surround, three lights over it (a wide one between two
        # narrow), a flat parapet ~0.9 m over the eaves with a low rise in the middle of its coping
        # 성암관's: wider and deeper, five lights over the door (its oriel seen from the garden); 교육관's: a narrow
        # bay of pale dressed stone, two storeys, the wall carrying on over it (top under the eaves)
        p0, p1, pp = porch['s0'] - L / 2, porch['s1'] - L / 2, porch['proj']
        pwall = porch.get('wall', wall)
        yf = -W / 2 - pp
        y_face = yf
        ztp = porch['top'] if porch.get('top') is not None else Hw + porch.get('parapet', 0.8)
        zr = (ztp - 0.45) if low_porch else Hw + 0.4                # its flat roof
        y_r = -W / 2 if low_porch else -W / 2 + (zr - Hw) / pitch + 0.05   # where the main roof comes up to it
        stone_base(mb, [(p0, yf), (p1, yf), (p1, -W / 2), (p0, -W / 2)], plinth, wall)
        P, Le, t, n = edge_P((p0, yf), (p1, yf))
        sc = Le / 2
        dh, dhole = hall_door(mb, P, sc, zd, door, pp + 2.4, pwall)
        holes = [(dh[0], dh[1], -1.0, dh[2])]
        ww_, rat = porch['win']
        windows(P, [(sc - ww_ / 2, sc + ww_ / 2, len(rat), 1, rat, 0.18)], holes)
        wall_holes(mb, P, 0, Le, plinth, ztp, pwall, holes)
        mb.quad(P(Le, zr, -0.35), P(0, zr, -0.35), P(0, ztp, -0.35), P(Le, ztp, -0.35), pwall)
        if porch.get('hump', True):
            hump = [(0, ztp), (sc - 1.25, ztp), (sc - 0.75, ztp + 0.2), (sc + 0.75, ztp + 0.2), (sc + 1.25, ztp), (Le, ztp)]
            profile_wall(P, hump[1:5], ztp, inner=-0.35)
            for a_, b_ in ((-0.04, sc - 1.25), (sc + 1.25, Le + 0.04)):
                bar(mb, P, a_, ztp + 0.05, b_, ztp + 0.05, 0.14, -0.39, 0.08, 'stone_trim', ends=True)
        else:
            bar(mb, P, -0.04, ztp + 0.05, Le + 0.04, ztp + 0.05, 0.14, -0.39, 0.08, 'stone_trim', ends=True)
        for s in (0.22, Le - 0.22):                                 # the raised ends of the coping
            bar(mb, P, s - 0.25, ztp + 0.16, s + 0.25, ztp + 0.16, 0.16, -0.39, 0.1, 'stone_trim', ends=True)
        if pwall == wall:
            ivy_wall(P, 0, Le, ztp - 0.15, holes + [dhole], 41, w=('porch', Le))
        for pa, pb, sg in (((p1, yf), (p1, -W / 2), 1), ((p0, -W / 2), (p0, yf), -1)):   # its sides
            P2, Le2, t2, _ = edge_P(pa, pb)
            flat_wall(mb, P2, 0, Le2, plinth, ztp, pwall)
            mb.quad(P2(Le2, zr, -0.35), P2(0, zr, -0.35), P2(0, ztp, -0.35), P2(Le2, ztp, -0.35), pwall)
            bar(mb, P2, -0.04, ztp + 0.05, Le2 + 0.04, ztp + 0.05, 0.14, -0.39, 0.08, 'stone_trim', ends=True)
            if pwall == wall:
                ivy_wall(P2, 0, Le2, ztp - 0.15, [], 43 + sg, w=('porch', Le2))
            if low_porch:
                continue
            xi = (p1 - 0.35) if sg > 0 else (p0 + 0.35)
            xo = p1 if sg > 0 else p0
            oface(mb, [(xi, -W / 2, Hw), (xo, -W / 2, Hw), (xo, -W / 2, ztp), (xi, -W / 2, ztp)], wall, (0, 1, 0))
            oface(mb, [(xi, -W / 2, Hw), (xi, -W / 2, zr), (xi, y_r, zr)], wall, (sg, 0, 0))
        mb.face([(p0 + 0.35, yf + 0.35, zr), (p1 - 0.35, yf + 0.35, zr), (p1 - 0.35, y_r, zr), (p0 + 0.35, y_r, zr)], 'roof_flat')
    for s0, s1 in (bays or {}).get('at', ()):
        # 아펜젤러관's end bays: canted, a pair of lights in front and one in each angled side on both floors, standing
        # through the eaves to a coped parapet that rises in a low curve over the front (reference/아펜젤러관_정면_2016.jpg)
        x0, x1 = s0 - L / 2, s1 - L / 2
        xc, fw, pj = (x0 + x1) / 2, bays['front'], bays['proj']
        ztf, ztw, zr = Hw + 0.8, Hw + 0.45, Hw + 0.3
        y_r = -W / 2 + (zr - Hw) / pitch + 0.05
        Q = [(x0, -W / 2), (xc - fw / 2, -W / 2 - pj), (xc + fw / 2, -W / 2 - pj), (x1, -W / 2)]
        stone_base(mb, Q, plinth, wall)
        for k in range(3):
            P, Le, t, n = edge_P(Q[k], Q[k + 1])
            holes = []
            if k == 1:
                m_ = (Le - 2 * 0.95 - 0.45) / 2
                windows(P, [(m_, Le - m_, 2, f, None, 0.45) for f in (0, 1)], holes)
                prof = [(Le * j / 8, ztf + 0.18 * math.sin(math.pi * j / 8)) for j in range(9)]
            else:
                windows(P, [(Le / 2 - 0.26, Le / 2 + 0.26, 1, f) for f in (0, 1)], holes)
                prof = [(0, ztw), (Le, ztf)] if k == 0 else [(0, ztf), (Le, ztw)]
            zlo = min(z for _, z in prof)
            wall_holes(mb, P, 0, Le, plinth, zlo, wall, holes)
            profile_wall(P, prof, zlo, inner=-0.3)
            mb.quad(P(Le, zr, -0.3), P(0, zr, -0.3), P(0, zlo, -0.3), P(Le, zlo, -0.3), wall)
            ivy_wall(P, 0, Le, ztf, holes, 51 + k + int(x0), w=('bays', Le),
                     top=lambda s, prof=prof: prof[0][1] + (prof[-1][1] - prof[0][1]) * s / max(prof[-1][0], 1e-3) - 0.25)
        inset = offset_poly(Q, -0.3)
        inset[0] = (inset[0][0], y_r)
        inset[3] = (inset[3][0], y_r)
        mb.face([(p[0], p[1], zr) for p in inset], 'roof_flat')
        for xi, xo, sg in ((inset[0][0], x0, -1), (inset[3][0], x1, 1)):
            oface(mb, [(xi, -W / 2, Hw), (xo, -W / 2, Hw), (xo, -W / 2, ztw), (xi, -W / 2, ztw)], wall, (0, 1, 0))
            oface(mb, [(xi, -W / 2, Hw), (xi, -W / 2, zr), (xi, y_r, zr)], wall, (sg, 0, 0))
    if end_bay:
        # 스팀슨관's south end (reference/스팀슨관_측면_2016.jpg, the 2010 roadview, the 2013 survey's plans): a canted
        # bay in the middle of the gable through both floors, two lights in front and one in each angled side, a
        # moulded band over the upper lights and a coped parapet about the height of the eaves, a carved shield on
        # its front; the flat roof behind it runs back to the gable
        eb = end_bay
        sg = 1 if eb['edge'] == 1 else -1
        xw, h0, h1, fw, pj = sg * L / 2, -eb['span'] / 2, eb['span'] / 2, eb['front'] / 2, eb['proj']
        Q = ([(xw, h0), (xw + pj, -fw), (xw + pj, fw), (xw, h1)] if sg > 0 else
             [(xw, h1), (xw - pj, fw), (xw - pj, -fw), (xw, h0)])
        zt, zr, zb = Hw + eb.get('top', 0.1), Hw - 0.45, Hw - 0.8
        stone_base(mb, Q, plinth, wall)
        for k in range(3):
            P, Le, t, n = edge_P(Q[k], Q[k + 1])
            holes = []
            if k == 1:
                m_ = (Le - 2 * eb['light'] - 0.3) / 2
                windows(P, [(m_, Le - m_, 2, f, None, 0.3) for f in range(floors)], holes)
            else:
                windows(P, [(Le / 2 - eb['side'] / 2, Le / 2 + eb['side'] / 2, 1, f) for f in range(floors)], holes)
            wall_holes(mb, P, 0, Le, plinth, zt, wall, holes)
            mb.quad(P(Le, zr, -0.3), P(0, zr, -0.3), P(0, zt, -0.3), P(Le, zt, -0.3), wall)     # (the parapet's inside)
            bar(mb, P, -0.06, zt + 0.06, Le + 0.06, zt + 0.06, 0.16, -0.36, 0.08, 'stone_trim')  # coping
            bar(mb, P, -0.06, zb, Le + 0.06, zb, 0.24, 0.0, 0.12, 'stone_trim')                  # the band
            if k == 1:                                      # the shield
                sh = [(-0.24, -0.05), (0.0, -0.32), (0.24, -0.05), (0.24, 0.28), (-0.24, 0.28)]   # (anticlockwise)
                zc_ = (zb + zt) / 2 + 0.03
                mb.face([P(Le / 2 + u, zc_ + v, 0.07) for u, v in sh], 'stone_trim')
                for p, q in zip(sh, sh[1:] + sh[:1]):
                    mb.quad(P(Le / 2 + q[0], zc_ + q[1], 0.07), P(Le / 2 + p[0], zc_ + p[1], 0.07),
                            P(Le / 2 + p[0], zc_ + p[1], 0.0), P(Le / 2 + q[0], zc_ + q[1], 0.0), 'stone_trim')
            ivy_wall(P, 0, Le, zb, holes, 61 + k, w=('end_bay', Le))
        inset = offset_poly(Q, -0.3)
        inset[0], inset[3] = (xw, inset[0][1]), (xw, inset[3][1])
        mb.face([(p[0], p[1], zr) for p in inset], 'roof_flat')
    # entrance steps: porch, granite flights with a landing, rubble side walls and capped posts
    if stairs.get('side'):                     # a landing before the door and one flight down along the wall
        side_steps(mb, y_face, zd, gl, stairs['side'], (porch['s1'] - porch['s0']) / 2 + 0.4 if porch else stairs['width'] / 2 + 0.6,
                   -W / 2, wall=wall, rec=door['rec'], fw=stairs['width'])
    else:
        hall_steps(mb, y_face, zd, stairs['width'], gl, wall=wall, wl=stairs['wl'], cheeks=stairs['cheeks'],
                   lamps=stairs['lamps'], rec=door['rec'])
    for x0, x1, nl in dormers:
        for sg in (-1, 1):
            shed_dormer(mb, x0, x1, nl, sg, W, hz, pitch)
    if extra:
        extra(mb, iv, dict(L=L, W=W, plinth=plinth, fh=fh, Hw=Hw, hz=hz, pitch=pitch, wall=wall, gl=gl, ivy=ivy))
    mb.z_base = z0
    return [mb, iv]


def shed_dormer(mb, x0, x1, nl, sg, W, hz, pitch, hd=1.15, p2=0.12, inset=0.9):
    """A long shed dormer on the slope facing sg (-1: the front, -y), as on 교육관 (reference/학교연혁_유억겸기념관_옛
    교육관.jpg, two on the front slope; 2003_가을_교육관_서쪽면.jpg, a row on the back): its front set back `inset` from
    the wall line, nl small lights in a dark frame, slate cheeks and a flatter slate roof back up into the main roof."""
    a0 = W / 2 - inset
    zf0 = hz - a0 * pitch                         # the main roof at the dormer's front
    zf1 = zf0 + hd
    am = a0 - hd / (pitch - p2)                   # where the dormer's roof meets the main roof
    zm = hz - am * pitch
    yd, ym = sg * a0, sg * am
    oface(mb, [(x0, yd, zf0 - 0.05), (x1, yd, zf0 - 0.05), (x1, yd, zf1), (x0, yd, zf1)], 'frame_dark', (0, sg, 0))
    lw = (x1 - x0) / nl
    for k in range(nl):
        a, b = x0 + k * lw + lw * 0.16, x0 + (k + 1) * lw - lw * 0.16
        oface(mb, [(a, yd + sg * 0.02, zf0 + 0.22), (b, yd + sg * 0.02, zf0 + 0.22), (b, yd + sg * 0.02, zf1 - 0.2),
                   (a, yd + sg * 0.02, zf1 - 0.2)], 'glass', (0, sg, 0))
        mb.box(((a + b) / 2, yd + sg * 0.04, (zf0 + zf1) / 2 + 0.02), (0.05, 0.04, zf1 - zf0 - 0.42), 'frame_white')
    mb.box(((x0 + x1) / 2, yd + sg * 0.05, zf0 + 0.15), (x1 - x0 + 0.1, 0.1, 0.08), 'stone_trim')     # its sill
    for x, nx in ((x0, -1), (x1, 1)):                                                          # the cheeks
        oface(mb, [(x, yd, zf0 - 0.05), (x, yd, zf1), (x, ym, zm)], 'roof_slate', (nx, 0, 0))
    oface(mb, [(x0 - 0.12, yd + sg * 0.14, zf1 + 0.06), (x1 + 0.12, yd + sg * 0.14, zf1 + 0.06), (x1 + 0.12, ym, zm + 0.03),
               (x0 - 0.12, ym, zm + 0.03)], 'roof_slate', (0, sg * p2, 1))


def profile_wall(mb, ya, yb, xs, tops, bots, wall, cap='stone_trim', ct=0.14):
    """A wall between ya < yb across a builder's local x stations xs (increasing), its top following tops and its
    underside bots (z at each station), the top ct m in a pale coping, closed at both ends: the parapets of a flight
    that stands free over open ground (교육관's north flight)."""
    for i in range(len(xs) - 1):
        xa, xb, ta, tb, ba, bb = xs[i], xs[i + 1], tops[i], tops[i + 1], bots[i], bots[i + 1]
        ma, mbz = max(ba, ta - ct), max(bb, tb - ct)
        for y, out in ((ya, False), (yb, True)):
            q = [(xa, y, ba), (xb, y, bb), (xb, y, mbz), (xa, y, ma)]
            c = [(xa, y, ma), (xb, y, mbz), (xb, y, tb), (xa, y, ta)]
            if out:
                q, c = q[::-1], c[::-1]
            mb.face(q, wall)
            mb.face(c, cap)
        mb.quad((xa, ya, ta), (xb, ya, tb), (xb, yb, tb), (xa, yb, ta), cap)
        mb.quad((xa, yb, ba), (xb, yb, bb), (xb, ya, bb), (xa, ya, ba), wall)
    for i, sg in ((0, -1), (len(xs) - 1, 1)):
        x, t, bt = xs[i], tops[i], bots[i]
        q = [(x, yb, bt), (x, ya, bt), (x, ya, t), (x, yb, t)]
        mb.face(q if sg < 0 else q[::-1], wall)


def gyoyuk_north_flight(mb, iv, f, s0, s1, bd=2.4, fw=2.3, pt=0.35, ld=2.0, T=0.3, maxrise=0.21):
    """교육관's north end: a square stone bay standing out from the gable near its west corner, a pointed-arched door
    in its north face a storey up and a plain door under it at the ground; before the upper door a landing, and from
    it a straight granite flight down to the yard, square to the gable (out along +x, the bay's axis), between solid
    parapets of the wall's stone with a pale coping that end at the foot in square capped posts.  The landing and the
    upper flight stand free, the ground running on under them to the lower door; lower down, where its underside
    comes within 1.4 m of the ground, it is walled in down to it.  The west parapet runs on past the foot as a low wall to a lower post.
    reference/2003_가을_연희관앞정원과_교육관_북쪽계단.jpg (from the north-west, above: the flight coming down towards the
    yard, grass and leaves under it, the lower door under the landing), 2003_가을_교육관_서쪽면.jpg (the landing's west
    side flush with the bay's, the lower door straight under the upper one) and the Kakao roadview from the yard
    (Aug. 2008 pano 2381727, June 2026 1212397962: the same flight, its side parapets and the posts at its foot).  It
    had been drawn running east along the gable from a landing beside the bay, over a solid wedge of wall.
    Local frame of stone_hall: the end at x = L/2, s along it from the front corner (y = s - W/2)."""
    L, W, plinth, fh, wall, gl = f['L'], f['W'], f['plinth'], f['fh'], f['wall'], f['gl']
    xe = L / 2
    y0, y1 = s0 - W / 2, s1 - W / 2
    yc = (y0 + y1) / 2
    zl = plinth + fh - 0.1                        # the landing: the first floor's threshold
    zt = plinth + 2 * fh - 0.25                   # the bay's top, under the second floor's lights
    xf, xs = xe + bd, xe + bd + ld                # the bay's north face, the landing's edge (the flight's head)
    ya, yb = yc - fw / 2, yc + fw / 2             # the flight between its parapets
    yA, yB = ya - pt, yb + pt
    gnd_at = lambda x: max(gl(x, yA + (yB - yA) * k / 6) for k in range(7))
    zb = gnd_at(xf + 0.6) - 0.02                  # the ground under the landing, at the lower door
    gnd = min(gl(xf + 0.5, yc), gl(xs + 5.0, yc), zb) - 0.6     # footings
    # the bay, its base opened for the lower door
    dl = 1.1                                      # the lower door
    stone_base(mb, [(xe - 0.2, y0), (xf, y0), (xf, y1), (xe - 0.2, y1)], plinth, wall,
               gap=(1, (y1 - y0) / 2 - dl / 2, (y1 - y0) / 2 + dl / 2, zb))
    faces = (((xf, y0), (xf, y1)), ((xf, y1), (xe, y1)), ((xe, y0), (xf, y0)))
    for k, (pa, pb) in enumerate(faces):
        P, Le, t, n = edge_P(pa, pb)
        holes = []
        if k == 0:                                # the upper door, in the north face
            dw, rw = 1.2, 0.25                     # (its apex and the ring's stay under the bay's top)
            e0, e1 = Le / 2 - dw / 2, Le / 2 + dw / 2
            zs = zl + 1.5
            for (a_, b_) in ((e0 - rw, e0), (e1, e1 + rw)):
                flat_wall(mb, P, a_, b_, zl, zs + 0.2, 'stone_trim', d=0.04)
            arch_fill(mb, lambda s_, z_, d_=0.0: P(s_, z_, d_ + 0.04), e0 - rw, e1 + rw, zs, zs + dw + 0.3, 0.04,
                      'stone_trim', 'pointed', 12)
            arch_fill(mb, P, e0, e1, zs, zs + dw + 0.3, 0.4, 'stone_trim', 'pointed', 12)
            mb.quad(P(e0, zl, -0.4), P(e1, zl, -0.4), P(e1, zs, -0.4), P(e0, zs, -0.4), 'frame_dark')
            pts = [(s_, z_) for s_, z_ in arch_points(e0, e1, zs, 'pointed', 12)]
            mb.face([P(e0, zs, -0.39)] + [P(s_, z_, -0.39) for s_, z_ in pts[1:-1]] + [P(e1, zs, -0.39)], 'glass', panes=(2, 1))
            for s_ in (e0, e1):                   # the reveal's sides
                mb.quad(P(s_, zl, 0), P(s_, zl, -0.4), P(s_, zs, -0.4), P(s_, zs, 0), 'stone_trim')
            holes.append((e0 - rw, e1 + rw, zl, zs + dw + 0.3))
            # the lower door, straight under it in the shade of the landing: a plain opening with a dark leaf
            a_, b_, zh = Le / 2 - dl / 2, Le / 2 + dl / 2, zl - 0.75
            mb.quad(P(a_, zb, -0.3), P(b_, zb, -0.3), P(b_, zh, -0.3), P(a_, zh, -0.3), 'frame_dark')
            reveal(mb, P, a_, b_, zb, zh, 0.3, 'stone_trim')
            holes.append((a_, b_, -2.0, zh))
        wall_holes(mb, P, 0, Le, plinth, zt, wall, holes)
        bar(mb, P, -0.05, zt + 0.12, Le + 0.05, zt + 0.12, 0.24, -0.1, 0.12, 'stone_trim', ends=True)
        if f['ivy']:
            ivy_patch(iv, P, 0, Le, 0, zt, 5.5, 71 + k, cover=f['ivy'] * 0.9, holes=holes)
    # its cap: a low pyramid of slate over a coping
    xc = xe + bd / 2
    hb, hy = bd / 2 + 0.12, (y1 - y0) / 2 + 0.12
    for (p, q) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
        mb.face([(xc + p[0] * hb, yc + p[1] * hy, zt + 0.24), (xc + q[0] * hb, yc + q[1] * hy, zt + 0.24),
                 (xc, yc, zt + 1.1)], 'roof_slate')
    # the flight: as many risers as reach the yard at its foot, none over maxrise
    for n in range(4, 40):
        x_end = xs + (n - 1) * T                  # the last nosing; the ground beyond it
        zbot = gnd_at(x_end + 0.5) - 0.03
        if (zl - zbot) / n <= maxrise:
            break
    rise = (zl - zbot) / n
    ts, hp, hs = 0.5, 0.95, 1.4                   # the slab's depth, the parapets over the nosings, the open height
    soffit = lambda x: zl - ts - (x - xs) * rise / T
    x_p = xs + (zl - ts - (zb + hs)) * T / rise   # from here on the flight is walled in down to the ground
    # the landing slab, the treads (each down to the soffit, or to the ground where it is walled in) and the soffit.
    # Their tops and fronts are cut in three across: the bake shades a face from its corners, and a tread's four all
    # stand in the angle of a parapet (blender/bake.py), which left the whole flight dark
    cuts = [ya, ya + 0.45, yb - 0.45, yb]

    def across_(x0, x1, z0, z1, up):
        for y_a, y_b in zip(cuts, cuts[1:]):
            if up:
                mb.quad((x0, y_a, z0), (x1, y_a, z0), (x1, y_b, z0), (x0, y_b, z0), 'stone_step')
            else:
                mb.quad((x1, y_a, z0), (x1, y_b, z0), (x1, y_b, z1), (x1, y_a, z1), 'stone_step')
    # (each riser from the tread below it up: a corner buried in the next tread bakes black)
    for x0, x1 in ((xf, (xf + xs) / 2), ((xf + xs) / 2, xs)):
        across_(x0, x1, zl, zl, True)
        mb.quad((x0, yb, zl - ts), (x1, yb, zl - ts), (x1, ya, zl - ts), (x0, ya, zl - ts), 'stone_step')
    across_(xf, xs, zl - rise, zl, False)
    for k in range(1, n):
        top, xa_ = zl - k * rise, xs + (k - 1) * T
        across_(xa_, xa_ + T, top, top, True)
        across_(xa_, xa_ + T, top - rise, top, False)
    xg = min(x_p, x_end)
    mb.quad((xs, yb, zl - ts), (xg, yb, soffit(xg)), (xg, ya, soffit(xg)), (xs, ya, zl - ts), 'stone_step')
    mb.quad((xg, ya, soffit(xg)), (xg, yb, soffit(xg)), (xg, yb, gnd), (xg, ya, gnd), wall)
    # the parapets, round the landing and down the flight: free over the open ground, then walled to the ground
    xst = [xf, xs] + [xs + (xg - xs) * k / 4 for k in range(1, 5)]
    tops = [zl + hp, zl + hp] + [zl + hp - (x - xs) * rise / T for x in xst[2:]]
    bots = [zl - ts, zl - ts] + [soffit(x) for x in xst[2:]]
    wp = 0.55                                     # the posts at the foot (the parapets stop at their faces)
    x_q = x_end + 0.12 - wp / 2
    for (p0, p1) in ((yA, ya), (yb, yB)):
        profile_wall(mb, p0, p1, xst, tops, bots, wall)
        if x_q > xg:
            xw = [xg, (xg + x_q) / 2, x_q]
            profile_wall(mb, p0, p1, xw, [zl + hp - (x - xs) * rise / T for x in xw], [gnd] * 3, wall)
    for y in ((yA + ya) / 2, (yb + yB) / 2):
        pedestal(mb, x_end + 0.12, y, zbot + rise + hp + 0.3, gnd, wall, w=wp)
    # the west parapet runs on past the foot as a low coped wall to a lower post
    ym = (yb + yB) / 2
    gw = gl(x_end + 1.0, ym) - 0.03
    gx = min(gl(x_end + 0.35 + 0.4 * k, ym) for k in range(6)) - 0.4      # (the yard falls away past the foot)
    xw = [x_end + 0.12 + wp / 2, x_end + 1.2, x_end + 2.1 - 0.25]           # (post face to post face)
    profile_wall(mb, yb + 0.03, yB - 0.03, xw, [gw + 0.75] * 3, [gx] * 3, wall)
    pedestal(mb, x_end + 2.1, ym, gw + 1.0, gx, wall, w=0.5)
    W_ = lambda lx, ly, lz: tuple(mb.xf @ Vector((lx, ly, lz)))
    WALK_FACES.append([W_(xf, ya, zl), W_(xs, ya, zl), W_(xs, yb, zl), W_(xf, yb, zl)])
    WALK_FACES.append([W_(xs, ya, zl), W_(xs + n * T, ya, zbot), W_(xs + n * T, yb, zbot), W_(xs, yb, zl)])
    # the zone over the flight (note_entrance takes flights going down towards -y: this one goes out along +x)
    o = mb.xf @ Vector((xf, yc, 0.0))
    u = (mb.xf.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    v = (mb.xf.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
    ENTRANCES.append(dict(o=[round(o.x, 2), round(o.y, 2)], u=[round(u.x, 4), round(u.y, 4)], v=[round(v.x, 4), round(v.y, 4)],
                          hw=round((yB - yA) / 2 + 0.6, 2), len=round(x_end + 2.4 - xf, 2)))
    print('교육관 north flight: %d risers of %.3f m, landing %.2f m over the yard, foot %.1f m out of the gable'
          % (n, rise, zl - zbot, x_end - xe))


def seongam():
    """성암관, from reference/학교연혁_성암관.jpg (its front, towards the garden: a wide centre standing forward to a
    parapet over the eaves, the pointed-arched door at the head of a short flight, an oriel over it) and the 2003 photos
    across 연희관 앞 정원 (2003_가을_연희관앞정원과_교육관_북쪽계단.jpg, 2003_봄_교육관에서_본_연희관앞정원과_성암관.jpg:
    two storeys over a half-sunk basement under a long grey-tiled roof, coped gable ends, red ivy).  The OSM outline
    takes in the centre bay (11.3 m wide, 3.6 m out); the hall itself is the 33.3 x 13.2 m block behind it.  Its floor
    puts the porch a short flight over the drive before it (tools/build_campus.py SEONGAM_FLOOR)."""
    b = bld(246156117)
    main = [(116.69, 289.28), (129.55, 286.12), (137.57, 318.39), (124.32, 321.63)]
    front = (-0.97, 0.24)
    L = frame_for(dict(b, footprint=main), front)[2]
    groups = []
    for sc in (2.0, 5.2, 8.4, L - 8.4, L - 5.2, L - 2.0):
        groups.append((sc - 1.0, sc + 1.0, 2))
    return stone_hall('seongam', b, front, groups, ivy=0.7, pitch=0.62, rect_fp=main, z0=CAMPUS.get('seongam_floor'),
                      porch=dict(s0=10.2, s1=21.5, proj=3.6, parapet=1.0, win=(4.8, [1.0] * 5)),
                      back=[(L / 2 - 1.6, L / 2 + 1.6, 3), (L / 2 - 4.8, L / 2 - 3.0, 2), (L / 2 + 3.0, L / 2 + 4.8, 2)],
                      stairs=dict(width=3.2, wl=4.2, rise=0.0 if 'seongam_floor' in CAMPUS else 1.3),
                      door=dict(w=2.0, arch='pointed', spring=1.7, style='panel', rec=0.6))


def gyoyuk():
    """교육관 (지금 유억겸기념관), from reference/학교연혁_유억겸기념관_옛교육관.jpg (its front to the east, over 연희관
    앞 정원: three storeys of paired lights in pale grey rubble, a narrow bay of white dressed stone in the middle with
    the pointed-arched door at the ground and a parapet under the top floor's lights, a slate roof with coped gable
    ends and two long shed dormers) and the 2003 photos: the west side (2003_가을_교육관_서쪽면.jpg) three full storeys
    over the drive and a row of dormers on the back slope, the north end (2003_가을_연희관앞정원과_교육관_북쪽계단.jpg)
    a stone bay with an outside flight up to its first-floor door (gyoyuk_north_flight).  The floor stands at the drive
    to the west and the yard to the north (tools/build_campus.py levels both, GYOYUK_FLOOR)."""
    b = bld(246156111)
    front = (0.97, -0.25)
    L = frame_for(b, front)[2]
    groups = [(sc - 0.95, sc + 0.95, 2) for sc in (2.7, 6.4, 10.1, 13.8, L / 2, L - 13.8, L - 10.1, L - 6.4, L - 2.7)]
    plinth, fh = 0.6, 3.4
    ends = {1: [(2.4, 4.4, 2, 0), (2.4, 4.4, 2, 1), (2.4, 4.4, 2, 2), (7.6, 9.6, 2, 2), (13.1, 15.1, 2, 2)],
            3: [(Le_ + a, Le_ + b_, 2, f_) for Le_ in (8.95,) for a, b_ in ((-5.4, -3.2), (3.2, 5.4)) for f_ in range(3)]}
    return stone_hall('gyoyuk', b, front, groups, ivy=0.9, fh=fh, wall='stone_rubble_gray', pitch=0.72, floors=3,
                      plinth=plinth, basement=False, z0=GYOYUK_FLOOR, end_wins=ends,
                      porch=dict(s0=L / 2 - 2.2, s1=L / 2 + 2.2, proj=1.3, top=plinth + 2 * fh + 0.35, hump=False,
                                 wall='stone_trim', win=(1.6, [1.0, 1.0])),
                      dormers=[(-13.7, -5.9, 5), (5.9, 13.7, 5)],
                      stairs=dict(width=2.0, wl=3.4, rise=0.5, side=1),
                      door=dict(w=1.7, arch='pointed', spring=1.6, style='panel', rec=0.5),
                      extra=lambda mb, iv, f: gyoyuk_north_flight(mb, iv, f, 12.4, 16.2))


GYOYUK_FLOOR = CAMPUS.get('gyoyuk_floor', 53.0)     # 교육관's floor: the drive along its west side and the yard north of it
# (tools/build_campus.py GYOYUK_FLOOR)


def stimson():
    """스팀슨관 (1920), from reference/스팀슨관_정면_2016.jpg (~36.7 px/m along its 32.5 m front): three groups of three
    lights either side of a 5.6 m entrance bay standing 0.9 m forward, 1.15 m of wall between the groups.  The back
    and the ends from reference/스팀슨관_측면_2016.jpg, the Dec. 2010 / Apr. 2011 roadview (panoramas 1016786678 -
    1016786685 on the walk past the front and the ends, 1016786048 - 1016786051 on the road behind) and the 2013
    survey's plans and rear elevation (in 안대환 2016, reference/고증.md 3.5): the back has the front's groups and, in
    the porch's place, the stair's tall lights over the back door; the south end a canted bay in the middle with a
    single light either side on both floors and a vent over the bay, the north end a light in the middle and one
    2.6 m from each corner on the ground floor (two on the upper, the hall's) and a tall narrow light in the gable;
    the chimney astride the ridge 10.5 m from the south end, ~3 m over it."""
    b = bld(246156118)
    L, W = frame_for(b, (1.0, -0.27))[2:4]
    gw, pier, gap, pw = 3.15, 1.15, 0.35, 5.6
    groups = []
    for sg in (-1, 1):
        for k in range(3):
            a = pw / 2 + gap + k * (gw + pier)
            g = sorted((L / 2 + sg * a, L / 2 + sg * (a + gw)))
            groups.append((g[0], g[1], 3))
    groups.sort()
    one = lambda g, f: (g - 0.5, g + 0.5, 1, f)                    # a single light, 1 m wide
    ends = {1: [one(2.6, 0), one(W / 2, 0), one(W - 2.6, 0), one(2.6, 1), one(W - 2.6, 1)],
            3: [one(g, f) for g in (2.5, W - 2.5) for f in (0, 1)]}
    # the ivy (reference/고증.md 3.5): the porch a mat to its parapet (a 1996 - 2000 summer photo, the Dec. 2010
    # roadview, 2016), the north end covered to its gable (2010); the south end bare stone but for low growth at its
    # corners (April 2003 from 백양로's end, 2010, 2016), the back only up to the ground floor (the Aug. 2008 roadview)
    ivy_walls = {'porch': 1.15, 1: 1.0, 3: dict(cover=0.6, zmax=3.3, ends=(1.2, 1.6)), 'end_bay': 0,
                 2: dict(cover=0.6, zmax=4.3)}
    return stone_hall('stimson', b, (1.0, -0.27), groups, ivy=0.8, ivy_walls=ivy_walls,
                      porch=dict(s0=L / 2 - pw / 2, s1=L / 2 + pw / 2, proj=0.9, parapet=0.8, win=(2.3, [0.45, 1.0, 0.45])),
                      chimney=dict(at=(-5.8, 0.0), h=3.0, sky=(-5.8, 2.3)), end_wins=ends,
                      attic={1: (W / 2, 0.7, 0.4, 1.75), 3: (W / 2, 0.75, 0.35, 1.2)},
                      end_bay=dict(edge=3, span=4.9, front=3.0, proj=0.95, light=0.95, side=0.62, top=0.1),
                      rear=dict(w=3.3, lights=[(3.05, 6.45)], door=(0.95, 2.4), zd=-0.94, side=(0.85, 1.15)),
                      stairs=dict(width=3.6, wl=4.8), door=dict(w=2.2, spring=1.9, style='panel', rec=0.5))


def appenzeller():
    """아펜젤러관 (1924), from reference/아펜젤러관_정면_2016.jpg (~40 px/m along its 34.6 m front): five groups of three
    lights 0.6 m apart in the middle, the front door under the middle one; canted bays 4.3 m wide, 2.3 m in from the
    ends.  The back and the ends from the Dec. 2010 roadview (panoramas 1016786661 - 1016786668 and 1016786076,
    reference/아펜젤러관_측면_2016.jpg) and the 2013 survey's plans and rear elevation (in 안대환 2016, reference/고증.md
    3.5): the back has the front's five groups with the stair's lights and the back door in the middle one's place,
    and a group 4 m from each end; each end two lights, three and two on both floors and a tall light in the gable
    (the attic storey's)."""
    b = bld(246156116)
    L, W = frame_for(b, (-1.0, 0.27))[2:4]
    gw, pier = 3.2, 0.6
    s0 = L / 2 - (5 * gw + 4 * pier) / 2
    groups = [(s0 + k * (gw + pier), s0 + k * (gw + pier) + gw, 3) for k in range(5)]
    at = [(2.3, 6.6), (L - 6.6, L - 2.3)]
    end = [w for f in (0, 1) for w in ((W / 2 - 5.05, W / 2 - 2.95, 2, f), (W / 2 - 1.6, W / 2 + 1.6, 3, f),
                                        (W / 2 + 2.95, W / 2 + 5.05, 2, f))]
    # the ivy (reference/고증.md 3.5): the front a mat round the door (a 1996 group photo) and the north end (2010,
    # 2016) as before; the south end (1: the +x one) strands up the piers and a band under the upper lights (a 1996 -
    # 2000 autumn photo, the telephone box at its corner); the back bare but near its north end (the Dec. 2010 roadview)
    ivy_walls = {1: 1.0, 2: dict(cover=0.6, ends=(0.0, 3.5))}
    return stone_hall('appenzeller', b, (-1.0, 0.27), groups, ivy=1.1, door_group=2, ivy_walls=ivy_walls,
                      bays=dict(at=at, front=3.0, proj=0.75),
                      back=[(c - gw / 2, c + gw / 2, 3) for c in (4.0, L - 4.0)], end_wins={1: end, 3: end},
                      attic={1: (W / 2, 0.9, 0.4, 2.0), 3: (W / 2, 0.9, 0.4, 2.0)},
                      rear=dict(w=3.2, lights=[(2.55, 4.65), (5.6, 6.5)], door=(0.97, 2.5), zd=-1.08, side=(0.84, 0.65)),
                      stairs=dict(width=3.8, wl=5.0), door=dict(w=2.2, spring=1.9, style='panel', rec=0.6))


# ============================================================================= 대강당
def wall_holes(mb, P, s0, s1, z0, z1, mat, holes, d=0.0):
    """A wall P(s, z, d) over [s0, s1] x [z0, z1] with the rectangular openings holes [(a, b, za, zb), ...] left out."""
    zs = sorted({z0, z1} | {z for h in holes for z in (h[2], h[3]) if z0 < z < z1})
    for za, zb in zip(zs, zs[1:]):
        zm = (za + zb) / 2
        s = s0
        for a, b in sorted((h[0], h[1]) for h in holes if h[2] <= zm <= h[3]):
            if a > s:
                flat_wall(mb, P, s, a, za, zb, mat, d=d)
            s = max(s, b)
        if s < s1:
            flat_wall(mb, P, s, s1, za, zb, mat, d=d)


def reveal(mb, P, a, b, za, zb, depth, mat):
    """The sill, head and jambs of an opening [a, b] x [za, zb] in a wall plane P, depth m deep."""
    mb.quad(P(a, za, 0), P(a, za, -depth), P(b, za, -depth), P(b, za, 0), mat)
    mb.quad(P(b, zb, 0), P(b, zb, -depth), P(a, zb, -depth), P(a, zb, 0), mat)
    mb.quad(P(a, zb, 0), P(a, zb, -depth), P(a, za, -depth), P(a, za, 0), mat)
    mb.quad(P(b, za, 0), P(b, za, -depth), P(b, zb, -depth), P(b, zb, 0), mat)


def glazing(mb, P, a, b, za, zb, d, cols, rows, frame, glass='glass', fw=0.07, transom=None):
    """A pane over [a, b] x [za, zb] at depth d of a wall P, divided cols x rows by slim bars (and a transom bar)."""
    # the rooms behind it change at bars, about a bay wide and a storey tall (common.py pane_uv)
    mb.quad(P(a, za, d), P(b, za, d), P(b, zb, d), P(a, zb, d), glass,
            panes=(pane_count(cols, b - a, 3.4), pane_count(rows, zb - za, 3.6)))
    for k in range(cols + 1):
        x = a + (b - a) * k / cols
        bar(mb, P, x, za, x, zb, fw if 0 < k < cols else fw * 1.5, d, d + 0.06, frame)
    for k in range(rows + 1):
        z = za + (zb - za) * k / rows
        bar(mb, P, a, z, b, z, fw if 0 < k < rows else fw * 1.5, d, d + 0.06, frame)
    if transom is not None:
        bar(mb, P, a, transom, b, transom, fw * 1.6, d, d + 0.08, frame)


def lattice_rail(mb, a, b, z, h=1.0, mat='frame_silver'):
    """A steel railing from a to b (local 2D) standing on z: posts, a top and a bottom rail, and between two slimmer
    rails a band of square lattice (the porch railings of the 대강당 in the 2009 photos)."""
    a, b = Vector((*a, 0)), Vector((*b, 0))
    t = b - a
    Le = t.length
    t.normalize()
    rz = math.atan2(t.y, t.x)
    at = lambda s, zz: (a.x + t.x * s, a.y + t.y * s, zz)
    nseg = max(1, int(round(Le / 1.6)))
    for k in range(nseg + 1):
        mb.box(at(k * Le / nseg, z + h / 2), (0.07, 0.07, h), mat, rotz=rz)
    for zz, w in ((z + h - 0.03, 0.06), (z + 0.1, 0.04), (z + 0.32, 0.03), (z + h - 0.22, 0.03)):
        mb.box(at(Le / 2, zz), (Le, w, w), mat, rotz=rz)
    nsq = max(1, int(Le / 0.42))
    for k in range(nsq + 1):
        mb.box(at(k * Le / nsq, z + 0.21 + (h - 0.32) / 2), (0.025, 0.025, h - 0.54), mat, rotz=rz)
    for k in range(nsq):                                            # a smaller square in each, on its corner
        c = at((k + 0.5) * Le / nsq, z + 0.21 + (h - 0.32) / 2)
        r = min(0.12, (h - 0.54) / 3)
        for sx, sz in ((-1, 0), (1, 0)):
            mb.box((c[0] + t.x * sx * r * 0.5, c[1] + t.y * sx * r * 0.5, c[2]), (0.02, 0.02, r * 1.4), mat, rotz=rz)
        for sz in (-1, 1):
            mb.box((c[0], c[1], c[2] + sz * r * 0.7), (r, 0.02, 0.02), mat, rotz=rz)


def hip_roof(mb, poly, z, rise, mat, eave=0.5):
    """A hipped roof over a rectangle poly (4 corners, CCW) at eaves height z: the ridge along its long axis."""
    pts = [Vector((*p, 0)) for p in poly]
    e0, e1 = pts[1] - pts[0], pts[2] - pts[1]
    if e0.length < e1.length:
        pts = pts[1:] + pts[:1]
        e0, e1 = e1, e0
    c = sum(pts, Vector()) / 4
    la, lb = e0.normalized(), e1.normalized()
    A, B = e0.length / 2 + eave, e1.length / 2 + eave
    q = [c - la * A - lb * B, c + la * A - lb * B, c + la * A + lb * B, c - la * A + lb * B]
    r0, r1 = c - la * max(0.1, A - B), c + la * max(0.1, A - B)
    zr = z + rise
    P3 = lambda v, zz: (v.x, v.y, zz)
    mb.face([P3(q[0], z), P3(q[1], z), P3(r1, zr), P3(r0, zr)], mat)
    mb.face([P3(q[1], z), P3(q[2], z), P3(r1, zr)], mat)
    mb.face([P3(q[2], z), P3(q[3], z), P3(r0, zr), P3(r1, zr)], mat)
    mb.face([P3(q[3], z), P3(q[0], z), P3(r0, zr)], mat)


def grid_window(mb, P, a, b, za, zb, d, cols, rows, frame='frame_dark', glass='glass_reflect', vents=(), vent_glass='glass',
                fw=0.06, hall=False):
    """A steel window over [a, b] x [za, zb] at depth d of a wall P: a grid of cols x rows lights on slim bars, the rows
    in `vents` (counted from the top) hopper sashes whose glass reads darker (대강당: the first and fourth rows of its
    tall windows in reference/대강당_2009_정면.jpg)."""
    rh = (zb - za) / rows
    k = 0
    while k < rows:                                    # one glass face per run of rows of the same kind
        vent = k in vents
        j = k
        while j + 1 < rows and ((j + 1) in vents) == vent:
            j += 1
        z1, z0 = zb - k * rh, zb - (j + 1) * rh
        mb.quad(P(a, z0, d), P(b, z0, d), P(b, z1, d), P(a, z1, d), vent_glass if vent else glass,
                panes=(max(1, round((b - a) / 1.5)), max(1, round((z1 - z0) / 2.6)), hall))
        k = j + 1
    for c in range(cols + 1):
        x = a + (b - a) * c / cols
        bar(mb, P, x, za, x, zb, fw if 0 < c < cols else fw * 1.6, d, d + 0.06, frame)
    for r in range(rows + 1):
        heavy = r in (0, rows) or (rows - r) in vents or (rows - r - 1) in vents
        bar(mb, P, a, za + rh * r, b, za + rh * r, fw * 1.6 if heavy else fw, d, d + 0.06, frame)


def diamond_grille(mb, P, a, b, za, zb, d, pitch=0.32, w=0.022, mat='frame_dark'):
    """A lattice of diagonal bars over [a, b] x [za, zb] in front of a window at depth d (대강당's lobby windows)."""
    H = zb - za
    s0 = a - H
    while s0 < b:
        sa_, sb_ = max(a, s0), min(b, s0 + H)
        if sb_ - sa_ > 0.03:
            bar(mb, P, sa_, za + sa_ - s0, sb_, za + sb_ - s0, w, d, d + 0.03, mat)
            bar(mb, P, sa_, zb - (sa_ - s0), sb_, zb - (sb_ - s0), w, d, d + 0.03, mat)
        s0 += pitch


def auditorium():
    """대강당 (finished December 1958 as a hall of 2,300 seats, four storeys of reinforced concrete: 연세대학교 건물의
    역사, 자료 G), from the 2009 photos (reference/대강당_2009_정면.jpg, 대강당_2009_측면.jpg, 대강당_2009_앞길_계단.jpg) and
    the school's own photo (reference/학교연혁_대강당.jpg).  A hall clad in pale granite courses whose gable faces
    백양로, a wall of panels with a small cross near the top; the gable's shoulders stand 1.6 m in from the outer faces
    of the end towers, over a knee of wall above their tops.  Under it a clerestory of small windows, one over each
    tall window, a deep band, and five bays of 3.7 m between broad pilasters: in each a recessed frame holding a pair of
    tall steel windows (2 x 10 lights of pale green glass on dark bars, a darker row of hoppers) parted by a strip of
    stone.  At the foot the lobby: three bays of glass doors in brass frames, a grilled window in each outer bay,
    lanterns on the pilasters.  The end towers, two bays wide, stand a little forward with stepped returns, each with a
    recessed panel of two tall windows (2 x 16 lights).
    Proportions: the widths share the OSM front (34 m) out as the school's frontal photo does (towers 7.7 m, bays
    3.7 m); the heights are that photo's times 0.765: a camera fitted to the 2009 front photo (17 corners, 6 px rms)
    finds the school's image stretched upright by 1.3, and so do its stone courses (0.5 m) and window shapes.
    The lobby floor is a raised porch ten risers over the forecourt: a broad flight before the three door bays with
    steel handrails, lattice railings round the rest.  Lower wings fill the rest of the OSM outline: two storeys with
    hipped roofs at the front, flat-roofed blocks at the back."""
    b = bld(371403811)
    fp = b['footprint']
    fa, fb = Vector(fp[1]), Vector(fp[0])            # the main hall's 34 m front, south -> north
    v = (fb - fa).normalized()
    u = Vector((v.y, -v.x))                          # into the hall (east, away from 백양로)
    m = (fa + fb) / 2
    # local frame: x along the front from north to south, y into the hall: the gable plane at y = 0, the porch at -y
    ang = math.atan2(-v.y, -v.x)
    zf = max(ground(*(m - u * 4.0 + v * s_)) for s_ in (-14.0, -7.0, 0.0, 7.0, 14.0))     # the forecourt
    mb = MeshBuilder('lm_auditorium')
    mb.xf = local_frame(m.x, m.y, ang, zf)
    gl = local_ground(mb)
    loc = lambda p: ((Vector(p) - m).dot(-v), (Vector(p) - m).dot(u))
    W_ = lambda lx, ly, lz: tuple(mb.xf @ Vector((lx, ly, lz)))

    def bx(xa, xb, ya, yb, za, zb_, mat, **kw):
        mb.box(((xa + xb) / 2, (ya + yb) / 2, (za + zb_) / 2), (xb - xa, yb - ya, zb_ - za), mat, **kw)

    def courses(P, s0, s1, z0, z1, head=None, holes=(), d=0.012, jw=0.012):
        """joints of the granite cladding on a wall P: beds every 0.5 m (from the porch), heads every `head` m from
        s0 (stack bond), round the openings `holes`"""
        def runs(a, b, cuts):
            for c0, c1 in sorted(cuts):
                if c0 > a:
                    yield a, min(c0, b)
                a = max(a, c1)
            if a < b:
                yield a, b
        z = Zp + 0.5
        while z < z1 - 0.1:
            if z > z0 + 0.1:
                for a_, b_ in runs(s0, s1, [(h[0], h[1]) for h in holes if h[2] < z < h[3]]):
                    mb.quad(P(a_, z - jw, d), P(b_, z - jw, d), P(b_, z + jw, d), P(a_, z + jw, d), 'concrete_dark')
            z += 0.5
        if head:
            n_ = max(1, round((s1 - s0) / head))
            for k in range(1, n_):
                x = s0 + (s1 - s0) * k / n_
                for a_, b_ in runs(z0, z1, [(h[2], h[3]) for h in holes if h[0] < x < h[1]]):
                    mb.quad(P(x - jw, a_, d), P(x + jw, a_, d), P(x + jw, b_, d), P(x - jw, b_, d), 'concrete_dark')

    def side(x, ya, yb, za, zb_, facing):
        """a wall in the plane x = const from y = ya to yb, facing +x (facing > 0) or -x"""
        P, L, _, _ = edge_P((x, ya), (x, yb)) if facing > 0 else edge_P((x, yb), (x, ya))
        flat_wall(mb, P, 0, L, za, zb_, wall)
    wall = 'stone_panel_wide'
    hx = (fb - fa).length / 2
    D = max(loc(p)[1] for p in fp)
    Zp = 1.6                     # the porch and lobby floor: ten risers over the forecourt
    He = Zp + 11.75              # the cornice under the gable, the tops of the end towers
    Hk = Zp + 12.42              # the hall's eaves: a knee of gable wall over the towers
    Hr = Zp + 16.9               # its ridge
    hb = hx - 1.6                # the gable's half width (the hall's upper walls stand in from the towers)
    T, pp = 7.72, 0.9            # end towers: width, how far their face stands out of the gable plane
    x0 = -hx + T                 # the recessed middle between the towers: five bays (x0 < 0, mirrored at -x0)
    pb = (2 * hx - 2 * T) / 5    # bay pitch (3.72 m)
    pl = 0.86                    # pilaster face
    yP_, yB = -0.45, -0.2        # the faces of the pilasters and the band; the wall of the bays behind them
    zL, zS, zW0, zW1 = Zp + 2.45, Zp + 3.2, Zp + 3.8, Zp + 9.5     # lobby top, its lintel band, the tall windows
    zH, zC0, zC1 = Zp + 9.95, Zp + 10.75, Zp + 11.58               # bay heads, the band over them, the clerestory
    zb = -9.0                    # the walls go on down into the slope (the back stands ~11 m higher)
    cs = [x0 + (k + 0.5) * pb for k in range(5)]                   # bay centres
    ww, ws = 1.03, 0.55          # tall window width, the stone strip between a pair
    wins = [(c + sg * (ws + ww) / 2 - ww / 2, c + sg * (ws + ww) / 2 + ww / 2) for c in cs for sg in (-1, 1)]
    ret = [(0.30, -pp), (0.15, -0.72), (0.0, -0.58)]               # tower returns: (how far out from the bays a
    X0 = -x0                                                       #  face's inner edge is, its y)
    XR = X0 + ret[0][0]                                            # the towers' faces end at x = -XR and XR
    xr = -XR
    # --- side and back walls up to the cornice: a row of small clerestory windows high up the long sides
    body = [(-hx, 0.0), (hx, 0.0), (hx, D), (-hx, D)]
    for i in (1, 2, 3):
        P, Le, t, n = edge_P(body[i], body[(i + 1) % 4])
        holes = []
        if i in (1, 3):
            for k in range(int((Le - 16.0) / 3.4)):
                s_ = 12.0 + k * 3.4
                s_ = s_ if i == 1 else Le - s_
                holes.append((s_ - 0.6, s_ + 0.6, He - 2.2, He - 1.3))
        wall_holes(mb, P, 0, Le, zb, He, wall, holes)
        for a_, b_, za_, zb_ in holes:
            reveal(mb, P, a_, b_, za_, zb_, 0.2, wall)
            glazing(mb, P, a_, b_, za_, zb_, -0.2, 1, 1, 'frame_dark')
        bar(mb, P, -0.2, He - 0.1, Le + 0.2, He - 0.1, 0.2, 0.0, 0.2, 'stone_trim', ends=True)
    for sg in (-1, 1):
        # the flat strip over each side wall outside the gable, the stone cap of each tower in front of it
        xa, xb = sorted((sg * hb, sg * hx))
        mb.quad((xa, 0.0, He), (xb, 0.0, He), (xb, D, He), (xa, D, He), 'roof_flat')
        xa, xb = sorted((sg * hx, sg * XR))
        mb.quad((xa, -pp, He), (xb, -pp, He), (xb, 0.0, He), (xa, 0.0, He), 'stone_trim')
        # --- the end towers: a recessed panel with two tall windows (offset outwards a little, as in the photos)
        xa, xb = sorted((sg * hx, sg * XR))
        Pt, Lt, _, _ = edge_P((xa, -pp), (xb, -pp))                # s from the north end, d outwards
        out = (lambda off: off) if sg < 0 else (lambda off, Lt=Lt: Lt - off)
        pa_, pb2 = sorted((out(1.38), out(5.75)))
        pz0, pz1 = Zp + 0.88, zH
        wall_holes(mb, Pt, 0, Lt, zb, He, wall, [(pa_, pb2, pz0, pz1)])
        reveal(mb, Pt, pa_, pb2, pz0, pz1, 0.12, wall)
        Pr = lambda s, z, d=0.0, Pt=Pt: Pt(s, z, d - 0.12)
        pc = (pa_ + pb2) / 2
        tw = [(pc + q * 1.2 - 0.64, pc + q * 1.2 + 0.64, Zp + 1.17, zW1) for q in (-1, 1)]
        wall_holes(mb, Pr, pa_, pb2, pz0, pz1, wall, tw)
        for a_, b_, za_, zb_ in tw:
            reveal(mb, Pr, a_, b_, za_, zb_, 0.15, wall)
            grid_window(mb, Pr, a_, b_, za_, zb_, -0.15, 2, 16, vents=(0, 6, 15))
        bar(mb, Pt, pa_ - 0.04, pz0, pb2 + 0.04, pz0, 0.08, -0.12, 0.06, 'stone_trim', ends=True)   # the panel's sill
        courses(Pt, 0.05, Lt - 0.05, Zp, He - 0.05, head=Lt / 7, holes=[(pa_ - 0.03, pb2 + 0.03, pz0 - 0.1, pz1 + 0.03)])
        side(sg * hx, -pp, 0.0, zb, He, sg)                        # the outer side back to the side wall
        # the inner return: two steps back to the pilasters' face up to the band, then plain to the gable plane
        for k, (off, yf) in enumerate(ret):
            yn = ret[k + 1][1] if k + 1 < len(ret) else yP_
            side(sg * (X0 + off), yf, yn, Zp - 0.2, zC0, -sg)
            if k + 1 < len(ret):                                   # the next step's face and its top at the band
                xa, xb = sorted((sg * (X0 + off), sg * (X0 + ret[k + 1][0])))
                Pq, Lq, _, _ = edge_P((xa, yn), (xb, yn))
                flat_wall(mb, Pq, 0, Lq, Zp - 0.2, zC0, wall)
                mb.quad((xa, yn, zC0), (xb, yn, zC0), (xb, 0.0, zC0), (xa, 0.0, zC0), wall)
        side(sg * XR, -pp, 0.0, zC0, He, -sg)
    # --- the middle: the clerestory in the gable plane, the band, pilasters, the bays' wall and windows, the lobby
    Pg, _, _, _ = edge_P((-hx, 0.0), (hx, 0.0))                    # s = x + hx, d outwards
    Pb, _, _, _ = edge_P((-hx, yB), (hx, yB))
    S = lambda x: x + hx
    clere = [(S(a_), S(b_), zC0 + 0.2, zC1 - 0.02) for a_, b_ in wins]
    wall_holes(mb, Pg, S(xr), S(-xr), zC0, He, wall, clere)
    for a_, b_, za_, zb_ in clere:
        reveal(mb, Pg, a_, b_, za_, zb_, 0.15, wall)
        grid_window(mb, Pg, a_, b_, za_, zb_, -0.15, 3, 1)
    for k in range(6):                                             # two thin fins at each pilaster over the band
        x = x0 + k * pb
        for sf in (-1, 1):
            if (k == 0 and sf < 0) or (k == 5 and sf > 0):
                continue
            bx(x + sf * 0.36 - 0.06, x + sf * 0.36 + 0.06, -0.2, 0.0, zC0, zC1, wall, skip=('bottom', 'back'))
    bx(xr, -xr, -0.12, 0.0, zC1, He, 'stone_trim', skip=('back',))                # the cornice under the gable
    bx(x0, -x0, yP_, 0.0, zH + 0.12, zC0, wall, skip=('back',))                    # the deep band over the bays
    bx(x0, -x0, yP_ - 0.06, yB, zH, zH + 0.12, 'stone_trim', skip=('back',))     # its drip ledge
    holes = [(S(a_), S(b_), zW0, zW1) for a_, b_ in wins]                        # the bays' wall and the windows
    wall_holes(mb, Pb, S(x0), S(-x0), zS, zH, wall, holes)
    for a_, b_, za_, zb_ in holes:
        reveal(mb, Pb, a_, b_, za_, zb_, 0.15, wall)
        grid_window(mb, Pb, a_, b_, za_, zb_, -0.15, 2, 10, vents=(0, 3))
    for c in cs:                                                   # a sill under each pair
        bar(mb, Pb, S(c - pb / 2 + pl / 2), zW0, S(c + pb / 2 - pl / 2), zW0, 0.07, -0.02, 0.09, 'stone_trim')
    bx(x0, -x0, -0.38, yB, zL, zS, wall, skip=('back',))                        # the lintel band over the lobby
    Pp, _, _, _ = edge_P((-hx, yP_), (hx, yP_))
    for k in range(6):                                             # pilasters from the porch to the band
        x = x0 + k * pb
        bx(x - pl / 2, x + pl / 2, yP_, yB, Zp - 0.2, zH, wall, skip=('bottom', 'back'))
        courses(Pp, S(max(x - pl / 2, x0)) + 0.02, S(min(x + pl / 2, -x0)) - 0.02, Zp, zH)
    # the lobby: brass-framed glass doors in the three middle bays, a grilled window in each outer bay
    for k, c in enumerate(cs):
        sa, sb = S(c - pb / 2 + pl / 2), S(c + pb / 2 - pl / 2)
        door = 0 < k < 4
        za_ = Zp if door else Zp + 0.7
        wall_holes(mb, Pb, sa, sb, Zp - 0.2, zL, wall, [(sa, sb, za_, zL)])
        reveal(mb, Pb, sa, sb, za_, zL, 0.2, wall)
        if door:
            # (dark glass mirroring the trees in the photos: the lobby behind it unlit)
            grid_window(mb, Pb, sa, sb, za_, zL, -0.2, 4, 1, frame='bronze', fw=0.07, hall=True)
            for zz in (Zp + 1.95, Zp + 0.92):                       # transom, and a rail over the handles
                bar(mb, Pb, sa, zz, sb, zz, 0.08 if zz > Zp + 1.5 else 0.05, -0.2, -0.13, 'bronze')
            hs = (sa + sb) / 2
            for sg in (-1, 1):
                bar(mb, Pb, hs + sg * 0.1, Zp + 0.8, hs + sg * 0.1, Zp + 1.4, 0.03, -0.13, -0.08, 'bronze', ends=True)
        else:
            glazing(mb, Pb, sa, sb, za_, zL, -0.2, 6, 3, 'frame_dark', glass='glass_reflect')
            diamond_grille(mb, Pb, sa, sb, za_, zL, -0.12)
    for k in range(1, 5):                                          # lanterns on the inner pilasters
        x = x0 + k * pb
        mb.box((x, yP_ - 0.1, zL + 0.15), (0.2, 0.2, 0.4), 'metal_green')
        mb.box((x, yP_ - 0.12, zL + 0.12), (0.14, 0.14, 0.24), 'light_amber')
    # --- the gable: a knee of wall over the cornice and the triangle, front and back; the small cross near the top
    for yg, sgn in ((-0.02, 1), (D + 0.02, -1)):
        xa, xb = (-hb, hb) if sgn > 0 else (hb, -hb)
        mb.quad((xa, yg, He), (xb, yg, He), (xb, yg, Hk), (xa, yg, Hk), wall)
        mb.face([(xa, yg, Hk), (xb, yg, Hk), (0.0, yg, Hr)], wall)
    for sg in (-1, 1):                                             # the knee walls along the sides, under the eaves
        side(sg * hb, 0.0, D, He, Hk, sg)
    jy, jw = -0.035, 0.017                                         # the front gable's joints: panels 0.8 x 0.5 m
    rake = lambda x: Hk + (Hr - Hk) * (1 - abs(x) / hb)
    z = He + 0.5
    while z < Hr - 0.25:
        hw_ = (hb if z <= Hk else hb * (1 - (z - Hk) / (Hr - Hk))) - 0.06
        mb.quad((-hw_, jy, z - jw), (hw_, jy, z - jw), (hw_, jy, z + jw), (-hw_, jy, z + jw), 'concrete_dark')
        z += 0.5
    for k in range(1, int(hb / 0.8) + 1):
        for x in (-k * 0.8 + 0.4, k * 0.8 - 0.4):
            if abs(x) < hb - 0.1:
                mb.quad((x - jw, jy, He + 0.12), (x + jw, jy, He + 0.12), (x + jw, jy, rake(x) - 0.1),
                        (x - jw, jy, rake(x) - 0.1), 'concrete_dark')
    zc = Hr - 1.68                                                 # the cross: a ring over a T
    mb.box((0.0, -0.07, zc - 0.25), (0.07, 0.07, 1.15), 'metal_dark')
    mb.box((0.0, -0.07, zc + 0.12), (0.66, 0.07, 0.06), 'metal_dark')
    for k in range(12):
        a_ = 2 * math.pi * k / 12
        mb.box((0.16 * math.cos(a_), -0.07, zc + 0.5 + 0.16 * math.sin(a_)), (0.08, 0.07, 0.05), 'metal_dark',
               rotz=0.0)
    # --- the roof, its ridge front to back: grey standing-seam metal, green flashing along the eaves and the rakes
    e = hb + 0.45
    mb.face([(-e, -0.45, Hk - 0.15), (0.0, -0.45, Hr + 0.1), (0.0, D + 0.45, Hr + 0.1), (-e, D + 0.45, Hk - 0.15)], 'roof_metal')
    mb.face([(e, D + 0.45, Hk - 0.15), (0.0, D + 0.45, Hr + 0.1), (0.0, -0.45, Hr + 0.1), (e, -0.45, Hk - 0.15)], 'roof_metal')
    for sg in (-1, 1):
        mb.box((sg * e, D / 2, Hk - 0.25), (0.14, D + 0.9, 0.22), 'metal_green')
    mb.box((0.0, D / 2, Hr + 0.18), (0.3, D + 0.9, 0.18), 'metal_green')
    Pfr, _, _, _ = edge_P((-hx, -0.45), (hx, -0.45))
    Pbk, _, _, _ = edge_P((hx, D + 0.45), (-hx, D + 0.45))
    for P_, Sx in ((Pfr, lambda x: x + hx), (Pbk, lambda x: hx - x)):
        for sg in (-1, 1):
            bar(mb, P_, Sx(sg * e), Hk - 0.18, Sx(0.0), Hr + 0.08, 0.16, -0.02, 0.05, 'metal_green', ends=True)
    # --- the porch: from the towers' faces out to the flight, and between them up to the doors
    yP = -5.6
    mb.box((0.0, (yP - pp) / 2, (Zp - 2.0) / 2), (2 * hx, -pp - yP, Zp + 2.0), 'stone_granite', mats={'top': 'stone_step'},
           skip=('bottom',))
    mb.box((0.0, -pp / 2, (Zp - 2.0) / 2), (-2 * xr, pp, Zp + 2.0), 'stone_granite', mats={'top': 'stone_step'},
           skip=('bottom',))
    mb.box((0.0, yP + 0.12, Zp + 0.02), (2 * hx + 0.1, 0.3, 0.06), 'stone_trim')                 # nosing along its edge
    WALK_FACES.append([W_(-hx, yP, Zp), W_(hx, yP, Zp), W_(hx, -pp, Zp), W_(-hx, -pp, Zp)])
    WALK_FACES.append([W_(x0, -pp, Zp), W_(-x0, -pp, Zp), W_(-x0, 0.3, Zp), W_(x0, 0.3, Zp)])
    fw = 3 * pb                                                    # the flight: as wide as the three door bays
    stair_flight(mb, 0.0, yP, fw, Zp, n=10, mat='stone_step', landing=0.0, tread=0.33, flare=0.0, rail=True, gfn=gl,
                 maxrise=0.165)
    for sg in (-1, 1):                                             # lattice railings round the rest of the porch
        lattice_rail(mb, (sg * (fw / 2 + 0.1), yP + 0.15), (sg * (hx - 0.1), yP + 0.15), Zp)
        lattice_rail(mb, (sg * (hx - 0.1), yP + 0.15), (sg * (hx - 0.1), -pp - 0.05), Zp)
    # --- the lower wings round the hall (the rest of the OSM outline)
    lp = [loc(p) for p in fp]
    wings = [[lp[2], lp[3], lp[4], lp[5]], [lp[15], lp[14], lp[13], lp[12]],
             [lp[6], lp[7], lp[8], (lp[6][0], D)], [lp[11], lp[10], lp[9], (lp[11][0], D)]]
    for wi, wp in enumerate(wings):
        area = sum(wp[i][0] * wp[(i + 1) % 4][1] - wp[(i + 1) % 4][0] * wp[i][1] for i in range(4))
        if area < 0:
            wp = wp[::-1]
        gs = [gl(*p) for p in wp]
        top = max(min(He - 3.5, max(gs) + 7.8), max(gs) + 1.2)     # (the blocks at the back stand up the slope)
        base = min(gs) - 1.5
        for i in range(4):
            a2, b2 = wp[i], wp[(i + 1) % 4]
            mx, my = (a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2
            if abs(mx) < hx + 0.8 and -0.4 < my < D + 0.4:
                continue                                           # against the hall's own wall
            P, Le, t, n = edge_P(a2, b2)
            zg = max(gl(*a2), gl(*b2), gl(mx, my))
            nfl = max(0, min(2, int((top - zg - 0.6) / 3.6)))
            flat_wall(mb, P, 0, Le, base, zg + 0.3, wall)
            if nfl:
                window_grid(mb, P, Le, zg + 0.3, nfl, 3.6, 3.2, wall, ww=0.5, trim='stone_trim', mull=1)
            flat_wall(mb, P, 0, Le, zg + 0.3 + nfl * 3.6, top, wall)
        if wi < 2:
            mb.face([(p[0], p[1], top) for p in wp], 'roof_flat')
            hip_roof(mb, wp, top, 2.4, 'roof_slate', eave=0.6)
        else:
            mb.face([(p[0], p[1], top) for p in wp], 'roof_flat')
            for i in range(4):
                P, Le, t, n = edge_P(wp[i], wp[(i + 1) % 4])
                mb.quad(P(0, top, 0), P(Le, top, 0), P(Le, top + 0.8, 0), P(0, top + 0.8, 0), wall)
                mb.quad(P(Le, top + 0.8, 0), P(0, top + 0.8, 0), P(0, top + 0.8, -0.3), P(Le, top + 0.8, -0.3), 'stone_trim')
    return [mb]


# ============================================================================= 루스채플
def chapel():
    b = bld(429249499)
    cx, cy, L, W, ang, z0 = frame_for(b, (-1.0, 0.25))
    mb = MeshBuilder('lm_chapel')
    mb.xf = local_frame(cx, cy, ang, z0)
    L, W = min(L, 34), min(W * 0.75, 18)
    H = 8.0
    body = rect(L, W)
    mb.prism(offset_poly(body, 0.3), -4, 0.6, 'stone_granite', 'stone_granite')
    for i in range(4):
        a, bb = body[i], body[(i + 1) % 4]
        P, Le, t, n = edge_P(a, bb)
        flat_wall(mb, P, 0, Le, 0.6, H, 'brick_red')
        nf = int(Le / 2.6)
        for k in range(1, nf):
            s = k * Le / nf
            mb.quad(P(s - 0.35, 1.6, 0.02), P(s + 0.35, 1.6, 0.02), P(s + 0.35, H - 0.8, 0.02), P(s - 0.35, H - 0.8, 0.02), 'glass')
            mb.quad(P(s - 0.45, 1.5, 0.05), P(s + 0.45, 1.5, 0.05), P(s + 0.45, 1.6, 0.05), P(s - 0.45, 1.6, 0.05), 'stone_trim')
        if Le < W + 0.1:
            hz = H + W / 2 * 1.25
            mb.face([P(0, H), P(Le, H), P(Le / 2, hz)], 'brick_red')
    hz = H + W / 2 * 1.25
    mb.face([(-L / 2 - 0.6, -W / 2 - 0.6, H - 0.75), (L / 2 + 0.6, -W / 2 - 0.6, H - 0.75), (L / 2 + 0.6, 0, hz), (-L / 2 - 0.6, 0, hz)], 'roof_slate')
    mb.face([(L / 2 + 0.6, W / 2 + 0.6, H - 0.75), (-L / 2 - 0.6, W / 2 + 0.6, H - 0.75), (-L / 2 - 0.6, 0, hz), (L / 2 + 0.6, 0, hz)], 'roof_slate')
    # slim bell tower with cross at the front corner
    tx, ty = -L / 2 + 2.0, -W / 2 - 2.5
    mb.box((tx, ty, 8.5), (2.4, 2.4, 17.0), 'concrete', mats={'top': 'concrete'})
    mb.box((tx, ty - 1.21, 13.5), (1.0, 0.02, 4.0), 'metal_dark')
    mb.box((tx, ty, 17.0 + 2.0), (0.25, 0.25, 4.0), 'metal')
    mb.box((tx, ty, 17.0 + 2.8), (1.6, 0.25, 0.25), 'metal')
    # entrance porch
    mb.box((-L / 2 - 1.5, 0, 3.5), (3.0, 6.0, 0.4), 'concrete')
    flat = edge_P((-L / 2, -2.0), (-L / 2, 2.0))
    return [mb]


# ============================================================================= 제1공학관 (front slab on 백양로)
def engineering():
    b = bld(205583531)
    cx, cy, L, W, ang, z0 = frame_for(b, (1.0, -0.25))
    z0 = lift_base(z0, cx, cy, ang, max(W, 13) / 2 + 2.5, 0.4, 0.6)
    mb = MeshBuilder('lm_engineering')
    mb.xf = local_frame(cx, cy, ang, z0)
    W = max(W, 13)
    fh, nf = 3.7, 5
    H = nf * fh + 0.6
    body = rect(L, W)
    mb.prism(offset_poly(body, 0.2), -4, 0.4, 'stone_granite')
    st = dict(generic.STYLE['modern'])
    # windows as in the 1997 aerial photo (reference/1997_백양로_항공사진.jpg): five rows on the 백양로 front, 14 wide
    # sliding windows a row across the 62 m (a 4.4 m bay, narrow piers between them), and deep plain spandrels: the
    # glass is under half the storey height
    st.update(wall='plaster_white', alt='plaster_white', ww=0.88, bay=L / 14.0, sill=1.0, head=1.05, mull=1)
    for i in range(4):
        a, bb = body[i], body[(i + 1) % 4]
        P, Le, t, n = edge_P(a, bb)
        if Le < W + 0.1:
            flat_wall(mb, P, 0, Le, 0.4, H + 0.9, 'stone_rubble_gray')   # grey rubble-granite end walls (1997 photo)
        else:
            # use local coordinates for the generic edge builder via a temporary identity xf
            pass
    # long facades through the generic wall builder in world space
    xf = mb.xf
    world = [tuple((xf @ Vector((p[0], p[1], 0)))[:2]) for p in body]
    mbw = MeshBuilder('lm_engineering_fac')
    rnd_ = random.Random(5)
    for i in (0, 2):
        generic.wall_edge(mbw, world[i], world[(i + 1) % 4], z0 + 0.4, z0 + H + 0.9, nf, fh, st, rnd_)
    generic.parapet_and_roof(mbw, world, z0 + H, st, rnd_)
    # the hall is the 1997 one (tools/build_campus.py LATE_FOOTPRINT_1997: 62 m, before the 2014 - 2015 wings).  As
    # photo A shows it through its camera (reference/고증.md 3.8): a white rooftop storey over the south 25 m (the
    # sixth floor was only built out in 2007), 2.2 m over the parapet, with two windows on the 백양로 side 11 and 19 m
    # from the south end; and a flat canopy on columns along the 백양로 front from 25 to 45 m (its north front corner
    # in the photo stops short of the hall's north end), the entrance doors at its south end
    mb.box((-L / 2 + 12.45, 0.3, H + 1.55), (24.9, W - 0.6, 3.1), 'plaster_white', mats={'top': 'roof_flat'})
    for s_ in (11.0, 19.3):
        mb.box((-L / 2 + s_, -W / 2 + 0.57, H + 1.15), (2.0, 0.08, 1.1), 'glass')
    x0c, x1c = -L / 2 + 25.1, -L / 2 + 45.1
    mb.box(((x0c + x1c) / 2, -W / 2 - 2.2, 4.0), (x1c - x0c, 4.4, 0.45), 'concrete', mats={'top': 'roof_flat'})
    for k in range(6):
        mb.cylinder((x0c + 0.6 + k * (x1c - x0c - 1.2) / 5, -W / 2 - 4.0), 0.22, 0.4, 3.8, 'concrete', seg=8, cap_top=False)
    xe = x0c + 3.4
    # concrete flight with handrails under the canopy, glass double doors behind a landing
    stair_flight(mb, xe, -W / 2, 6.4, 0.4, n=4, mat='stone_granite', landing=1.8, tread=0.4, flare=0.6, rail=True, gfn=local_ground(mb))
    mb.quad((xe - 2.6, -W / 2 - 0.02, 0.4), (xe + 2.6, -W / 2 - 0.02, 0.4), (xe + 2.6, -W / 2 - 0.02, 3.4), (xe - 2.6, -W / 2 - 0.02, 3.4), 'glass', panes=(1, 1, True))
    mb.box((xe, -W / 2 - 0.03, 3.5), (5.4, 0.08, 0.16), 'frame_dark')
    mb.box((xe, -W / 2 - 0.03, 0.4 + 1.5), (0.1, 0.08, 3.0), 'frame_dark')
    return [mb, mbw]


# ============================================================================= 광혜원 (traditional hanok)
def hanok():
    b = bld(429249496)
    cx, cy, L, W, ang, z0 = frame_for(b, (-1.0, 0.2))
    z0 = lift_base(z0, cx, cy, ang, 8.4 / 2 + 2.4, 0.9, 0.6)
    mb = MeshBuilder('lm_hanok')
    mb.xf = local_frame(cx, cy, ang, z0)
    L, W = 15.0, 8.4
    plat = 0.9
    mb.prism(offset_poly(rect(L + 2.4, W + 2.4), 0), -3, plat, 'stone_granite', 'stone_granite')
    WALK_FACES.append([tuple(mb.xf @ Vector((x_, y_, plat))) for x_, y_ in rect(L + 2.4, W + 2.4)])   # the 기단 is walked on
    stair_flight(mb, 0, -(W + 2.4) / 2, 3.0, plat, n=3, landing=0.3, tread=0.35, flare=0.25, gfn=local_ground(mb), maxrise=0.2)
    colh = 3.3
    nx, ny = 5, 3
    xs = [-L / 2 + L * i / nx for i in range(nx + 1)]
    ys = [-W / 2 + W * j / ny for j in range(ny + 1)]
    for x in xs:
        for y in (ys[0], ys[-1]):
            mb.cylinder((x, y), 0.2, plat, plat + colh, 'wood_red', seg=8, cap_top=False)
    for y in ys[1:-1]:
        for x in (xs[0], xs[-1]):
            mb.cylinder((x, y), 0.2, plat, plat + colh, 'wood_red', seg=8, cap_top=False)
    # infill walls: white plaster lower, lattice doors (창호)
    body = rect(L, W)
    for i in range(4):
        a, bb = body[i], body[(i + 1) % 4]
        P, Le, t, n = edge_P(a, bb, plat)
        flat_wall(mb, P, 0, Le, 0, 0.7, 'plaster_white', d=-0.08)
        flat_wall(mb, P, 0, Le, 0.7, colh - 0.6, 'wood_dark' if i == 0 else 'plaster_white', d=-0.1)
        flat_wall(mb, P, 0, Le, colh - 0.6, colh, 'wood_red', d=-0.05)
        if i == 0:
            for k in range(int(Le / 0.5)):
                s = k * 0.5
                mb.quad(P(s, 0.7, -0.06), P(s + 0.05, 0.7, -0.06), P(s + 0.05, colh - 0.6, -0.06), P(s, colh - 0.6, -0.06), 'paint_white')
            for zz in [0.7 + 0.45 * k for k in range(6)]:
                mb.quad(P(0, zz, -0.06), P(Le, zz, -0.06), P(Le, zz + 0.04, -0.06), P(0, zz + 0.04, -0.06), 'paint_white')
    # 팔작지붕 roof: curved eaves with upturned corners
    zr0 = plat + colh + 0.4
    ov = 1.6
    Lr, Wr = L / 2 + ov, W / 2 + ov
    ridge = zr0 + 3.0
    rl = L / 2 - 1.5
    N = 10

    def roof_z(u, v):
        """u in [-1,1] along L, v in [0,1] from eave (0) to ridge (1)."""
        sag = 0.35 * math.sin(math.pi * v)          # concave curve
        lift = 0.6 * (abs(u) ** 6) * (1 - v)          # corner upturn (처마 곡선)
        return zr0 + (ridge - zr0) * v - sag + lift
    for side in (-1, 1):
        for i in range(N):
            for j in range(N):
                u0, u1 = -1 + 2 * i / N, -1 + 2 * (i + 1) / N
                v0, v1 = j / N, (j + 1) / N

                def pt(u, v):
                    x = u * (Lr * (1 - v) + rl * v)
                    y = side * Wr * (1 - v)
                    return (x, y, roof_z(u, v))
                q = [pt(u0, v0), pt(u1, v0), pt(u1, v1), pt(u0, v1)]
                if side < 0:
                    mb.face(q, 'roof_giwa', smooth='roofA')
                else:
                    mb.face(q[::-1], 'roof_giwa', smooth='roofB')
    for side in (-1, 1):            # hip ends (triangular with gable 합각)
        for j in range(N):
            v0, v1 = j / N, (j + 1) / N

            def pt2(w, v):
                x = side * (Lr * (1 - v) + rl * v)
                y = w * Wr * (1 - v)
                return (x, y, roof_z(side, v))
            q = [pt2(-1, v0), pt2(1, v0), pt2(1, v1), pt2(-1, v1)]
            mb.face(q if side > 0 else q[::-1], 'roof_giwa')
        mb.face([(side * rl, -0.01, ridge), (side * rl, 0.01, ridge), (side * rl, 0, ridge - 0.01)], 'roof_giwa')
    mb.box((0, 0, ridge + 0.25), (2 * rl + 0.6, 0.6, 0.5), 'roof_giwa')
    for sx in (-1, 1):
        mb.box((sx * (rl + 0.3), 0, ridge + 0.55), (0.6, 0.7, 0.9), 'roof_giwa')
    # eave underside (서까래 colour)
    mb.face([(-Lr, -Wr, zr0 - 0.12), (Lr, -Wr, zr0 - 0.12), (L / 2, -W / 2, zr0 - 0.3), (-L / 2, -W / 2, zr0 - 0.3)][::-1], 'wood_red')
    mb.face([(Lr, Wr, zr0 - 0.12), (-Lr, Wr, zr0 - 0.12), (-L / 2, W / 2, zr0 - 0.3), (L / 2, W / 2, zr0 - 0.3)][::-1], 'wood_red')
    mb.box((0, 0, plat + colh + 0.2), (L + 0.4, W + 0.4, 0.4), 'wood_red', skip=('top',))
    return [mb]


# ============================================================================= 구 노천극장 (1933 - 1997)
def amphitheater():
    """The old 노천극장 in its last photo (reference/1997_구노천극장_마지막모습.jpg, April 1997; reference/고증.md 3.14):
    grass terraces round a pale earth floor, a thin line of stone along the top of each grass riser, a stone kerb
    round the floor and a dashed ring of stones laid in it; at the open west end a low stage of the same earth behind
    a straight dark stone wall, and a flight of steps up beside each end of the seats (two to a row).  In the local
    frame of tools/build_campus.py AMPH (u east, v north).  All of it is walked on (web/src/main.js)."""
    A = CAMPUS['amphitheater']
    mb = MeshBuilder('lm_amphitheater')
    mb.xf = local_frame(A['cx'], A['cy'], A['rot'], 0)
    rx, ry, h0 = A['arena_rx'], A['arena_ry'], A['arena_h']
    rows, rd, rh = A['rows'], A['row_d'], A['row_h']
    te = math.radians(A['seat_end'])
    nseg = 80

    def E(t, d):
        return ((rx + d) * math.cos(t), (ry + d) * math.sin(t))

    def T(i, n=nseg):
        return -te + 2 * te * i / n
    # the floor, a skirt under its edge where the ground beyond is lower (the open end)
    ring = [E(2 * math.pi * i / 72, 0) for i in range(72)]
    mb.face([(x, y, h0 + 0.02) for x, y in ring], 'dirt_pale')
    for i in range(72):
        a, b = ring[i], ring[(i + 1) % 72]
        mb.quad((*a, h0 - 1.4), (*b, h0 - 1.4), (*b, h0 + 0.02), (*a, h0 + 0.02), 'dirt_pale')
    # the kerb along the foot of the seats, and the ring of stones 1.5 m in from it
    for i in range(nseg):
        t0, t1 = T(i), T(i + 1)
        a0, a1, b0, b1 = E(t0, -0.3), E(t1, -0.3), E(t0, 0.0), E(t1, 0.0)
        mb.quad((*a1, h0 + 0.12), (*a0, h0 + 0.12), (*b0, h0 + 0.12), (*b1, h0 + 0.12), 'stone_marker')
        mb.quad((*a1, h0 + 0.02), (*a0, h0 + 0.02), (*a0, h0 + 0.12), (*a1, h0 + 0.12), 'stone_marker')
        for k in range(2):
            s0, s1 = t0 + (t1 - t0) * (k * 0.5 + 0.08), t0 + (t1 - t0) * (k * 0.5 + 0.42)
            c0, c1, e0, e1 = E(s0, -1.75), E(s1, -1.75), E(s0, -1.5), E(s1, -1.5)
            mb.quad((*c1, h0 + 0.035), (*c0, h0 + 0.035), (*e0, h0 + 0.035), (*e1, h0 + 0.035), 'concrete_dark')
    # the terraces: a grass bank, a thin stone face at its top (seen only from across the bowl, as in the photo; from
    # above the seats are all grass), then the grass tread back to the next bank
    for r in range(rows):
        d0, d1 = r * rd, (r + 1) * rd
        z0, z1 = h0 + r * rh, h0 + (r + 1) * rh
        prof = [(d0, max(z0, h0 + 0.12)), (d0 + 0.3, z1 - 0.1), (d0 + 0.3, z1), (d1, z1)]
        mats = ('grass', 'stone_marker', 'grass')
        for i in range(nseg):
            t0, t1 = T(i), T(i + 1)
            for k in range(3):
                (da, za), (db, zb) = prof[k], prof[k + 1]
                mb.quad((*E(t1, da), za), (*E(t0, da), za), (*E(t0, db), zb), (*E(t1, db), zb), mats[k])
        # the row's end, facing the flight beside it
        for sg in (-1, 1):
            end = [(d0, z0 - 0.45), (d1, z0 - 0.45), (d1, z1), (d0 + 0.3, z1), prof[0]]
            pts = [(*E(sg * te, d), z) for d, z in end]
            mb.face(pts[::-1] if sg > 0 else pts, 'grass')
    # a flight up beside each end of the seats, two steps to a row, a stone cheek wall along its outer side
    W, D = 1.6, rows * rd
    for sg in (-1, 1):
        t = sg * te
        n = (-sg * math.sin(t), sg * math.cos(t))           # out from the seat end, toward the open end

        def P(d, o, z):
            p = E(t, d)
            return (p[0] + n[0] * o, p[1] + n[1] * o, z)
        for k in range(2 * rows):
            da, db = k * rd / 2, (k + 1) * rd / 2
            za, zb = h0 + k * rh / 2, h0 + (k + 1) * rh / 2
            q = [P(da, 0.05, za), P(da, W, za), P(da, W, zb), P(da, 0.05, zb)]
            mb.face(q[::-1] if sg > 0 else q, 'stone_step')
            q = [P(da, 0.05, zb), P(da, W, zb), P(db, W, zb), P(db, 0.05, zb)]
            mb.face(q[::-1] if sg > 0 else q, 'stone_step')
        top = lambda d: h0 + d / rd * rh + 0.3
        o0, o1 = W, W + 0.25
        side = [(P(0, o, top(0)), P(D, o, top(D)), P(D, o, top(D) - 1.6), P(0, o, top(0) - 1.6)) for o in (o0, o1)]
        mb.face(side[0][::-1] if sg > 0 else side[0], 'stone_rubble_gray')
        mb.face(side[1] if sg > 0 else side[1][::-1], 'stone_rubble_gray')
        q = [P(0, o0, top(0)), P(0, o1, top(0)), P(D, o1, top(D)), P(D, o0, top(D))]
        mb.face(q[::-1] if sg > 0 else q, 'stone_marker')
        for d in (0, D):
            q = [P(d, o0, top(d) - 1.6), P(d, o1, top(d) - 1.6), P(d, o1, top(d)), P(d, o0, top(d))]
            mb.face(q[::-1] if (d == 0) == (sg > 0) else q, 'stone_rubble_gray')
    # the stage: the same earth, level with the ground behind it, a dark stone wall along its straight front
    su, sd, sw, sh = A['stage_u'], A['stage_d'], A['stage_w'], A['stage_h']
    mb.box((su - sd / 2, 0, h0 + (sh - 0.4) / 2), (sd, sw, sh + 0.4), 'stone_rubble_brown', mats={'top': 'dirt_pale'},
           skip=('bottom',))
    mb.box((su - 0.15, 0, h0 + sh + 0.03), (0.34, sw + 0.04, 0.08), 'stone_marker', skip=('bottom',))
    return [mb]


# ============================================================================= 대우관 (1984)
def gable_hall(mb, u0, u1, v0, v1, floors, fh, wall, pitch=1.3, plinth=1.0, bay=3.3, iv=None, ivy=0.0, seed=0, gothic_trim=False):
    """A stone hall in the builder's local frame whose ridge runs along v, with steep gables on its two v ends
    (the end pavilions of 대우관: their gables face the forecourt)."""
    W = u1 - u0
    Hw = plinth + floors * fh + 0.6
    hz = Hw + W / 2 * pitch
    body = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    stone_base(mb, body, plinth, wall)
    gl = local_ground(mb)
    for i in range(4):
        P, Le, t, n = edge_P(body[i], body[(i + 1) % 4])
        window_grid(mb, P, Le, plinth, floors, fh, bay, wall, ww=0.5, trim='stone_trim', mull=2)
        if plinth > 1.2:
            basement_windows(mb, P, 0, Le, bay, plinth, gl, wall)
        flat_wall(mb, P, 0, Le, plinth + floors * fh, Hw, wall)
        if gothic_trim and i in (1, 3):
            # as on the old stone halls (언더우드관): buttresses up the long sides and a battlemented parapet
            nbut = int(round(Le / 6.6))
            for k in range(1, nbut):
                c = P(k * Le / nbut, 0, 0.3)
                mb.box((c[0], c[1], plinth + (Hw - plinth - 1.5) / 2), (0.7, 0.6, Hw - plinth - 1.5), wall,
                       rotz=math.atan2(t.y, t.x), mats={'top': 'stone_trim'})
            nm = int(Le / 1.6)
            for k in range(0, nm, 2):
                c = P((k + 0.5) * Le / nm, Hw + 0.45, 0.0)
                mb.box(c, (Le / nm, 0.45, 0.9), 'stone_trim', rotz=math.atan2(t.y, t.x), skip=('bottom',))
        if iv is not None and ivy:
            gable = i in (0, 2)
            ivy_patch(iv, P, 0, Le, 0, (hz - 0.4) if gable else Hw + 0.3, 5.5, seed + i * 5, cover=ivy,
                      holes=win_holes(Le, plinth, floors, fh, bay, ww=0.5),
                      top=(lambda s_, Le=Le: Hw + (Le / 2 - abs(s_ - Le / 2)) * pitch - 0.4) if gable else None)
        mb.quad(P(-0.1, Hw - 0.1, 0.2), P(Le + 0.1, Hw - 0.1, 0.2), P(Le + 0.1, Hw + 0.2, 0.2), P(-0.1, Hw + 0.2, 0.2), 'stone_trim')
        if i in (0, 2):     # gable end: triangle, coping and a finial
            mb.face([P(0, Hw), P(Le, Hw), P(Le / 2, hz)], wall)
            mb.quad(P(-0.25, Hw, 0.3), P(Le / 2, hz + 0.4, 0.3), P(Le / 2, hz + 0.4, -0.2), P(-0.25, Hw, -0.2), 'stone_trim')
            mb.quad(P(Le / 2, hz + 0.4, 0.3), P(Le + 0.25, Hw, 0.3), P(Le + 0.25, Hw, -0.2), P(Le / 2, hz + 0.4, -0.2), 'stone_trim')
            c = P(Le / 2, hz + 0.9, 0.05)
            mb.box(c, (0.7, 0.7, 1.2), 'stone_trim', rotz=math.atan2(t.y, t.x), skip=('bottom',))
    uc = (u0 + u1) / 2
    e = 0.35
    A, B = (u0 - e, v0 - e, Hw - e * pitch), (u0 - e, v1 + e, Hw - e * pitch)
    C, D = (u1 + e, v1 + e, Hw - e * pitch), (u1 + e, v0 - e, Hw - e * pitch)
    R1, R2 = (uc, v0 - e, hz), (uc, v1 + e, hz)
    mb.face([A, R1, R2, B], 'roof_slate')
    mb.face([C, R2, R1, D], 'roof_slate')
    mb.box((uc, (v0 + v1) / 2, hz + 0.1), (0.35, v1 - v0, 0.3), 'metal_dark')


def daewoo_front(mb, zT, zP, u0, u1, uc=23.55, vp=-17.0):
    """대우관's terrace and podium (reference/대우관_2024_정면과_상뜰.jpg, 대우관_정면_전경.jpg, 대우관_블로그_본관_정면_상뜰.jpg,
    대우관_측면_2012.jpg), in the recess frame: u along the front from its west end, v into the hall (front wall v = 0),
    z from the hall's z0; zT the terrace, zP the plaza (the 상뜰 level) ~6 m below.
    The main door is not up a flight at all: a white stone podium stands 14 m out from the tower, 18 m wide, and the
    door is in its face at the plaza level, glass doors at the back of a deep porch under one wide low arch, a blue
    name board above, a clipped hedge along its top.  Flights climb to the terrace between high walls on either side
    of it; beyond them the front steps back, a planted tier and then the terrace wall, across the fronts of the wings.
    The tower's own pointed door opens onto the terrace three steps up."""
    hp, sw, ow = 9.0, 2.8, 8.6                   # podium half width, stair well width, arch span
    gnd = zP - 0.6
    W_ = lambda u, v, z: tuple(mb.xf @ Vector((u, v, z)))

    def walk(ua, ub, va, vb, z):
        WALK_FACES.append([W_(ua, va, z), W_(ub, va, z), W_(ub, vb, z), W_(ua, vb, z)])

    def block(ua, ub, va, vb, za, zb, mat='stone_white', top=None):
        mb.box(((ua + ub) / 2, (va + vb) / 2, (za + zb) / 2), (ub - ua, vb - va, zb - za), mat,
               mats={'top': top} if top else None, skip=('bottom',) if za <= gnd else ())

    def parapet(ua, ub, va, vb, z, h=1.0):
        block(ua, ub, va, vb, z, z + h - 0.12)
        block(ua - 0.06, ub + 0.06, va - 0.06, vb + 0.06, z + h - 0.12, z + h, 'stone_trim')

    # --- the podium, built round its porch (v from the face to -14) and the lit lobby behind the glass (to -8.5)
    pa, pb = uc - hp, uc + hp
    oa, ob = uc - ow / 2, uc + ow / 2
    zs = zP + 2.2                                # springing of the segmental arch
    zc = zs + ow * 0.16                          # its crown = the porch ceiling
    vr, vl = vp + 3.0, vp + 8.5                  # glass screen / back of the lobby
    block(pa, oa, vp, 0.0, gnd, zT, top='stone_step')
    block(ob, pb, vp, 0.0, gnd, zT, top='stone_step')
    block(oa, ob, vp, 0.0, zc, zT, top='stone_step')
    block(oa, ob, vl, 0.0, gnd, zc)
    Pf, _, _, _ = edge_P((pa, vp), (pb, vp))     # the podium face: s from its west end, d outwards (-v)
    arch_fill(mb, Pf, oa - pa, ob - pa, zs, zc + 0.01, 0.6, 'stone_white', 'segment', 16, intrados_mat='stone_trim')
    ring = arch_points(oa - pa, ob - pa, zs, 'segment', 16)
    for (sa, za), (sb, zb) in zip(ring, ring[1:]):                     # a pale moulded ring round the arch
        bar(mb, Pf, sa, za + 0.16, sb, zb + 0.16, 0.32, 0.0, 0.06, 'stone_trim')
    for s in (oa - pa - 0.16, ob - pa + 0.16):                         # and down the jambs
        bar(mb, Pf, s, zP, s, zs + 0.1, 0.32, 0.0, 0.06, 'stone_trim')
    mb.quad(Pf(oa - pa, zP + 0.02, 0.3), Pf(ob - pa, zP + 0.02, 0.3), Pf(ob - pa, zP + 0.02, -3.0), Pf(oa - pa, zP + 0.02, -3.0), 'stone_step')
    walk(oa, ob, vp - 0.3, vr, zP + 0.02)
    shopfront(mb, Pf, oa - pa + 0.05, ob - pa - 0.05, zP, zc - 0.01, -3.0)
    vestibule(mb, Pf, oa - pa + 0.03, ob - pa - 0.03, zP + 0.005, zc - 0.03, -3.02, vl - vr - 0.05, lights=3)
    zb0 = zc + 0.45                                                    # the blue name board over the arch
    mb.quad(Pf(hp - 5.2, zb0, 0.05), Pf(hp + 5.2, zb0, 0.05), Pf(hp + 5.2, zb0 + 0.62, 0.05), Pf(hp - 5.2, zb0 + 0.62, 0.05), 'sign_blue')
    bar(mb, Pf, hp - 5.3, zb0 + 0.31, hp + 5.3, zb0 + 0.31, 0.72, 0.0, 0.04, 'stone_trim', ends=True)
    mb.quad(Pf(hp - 4.2, zb0 + 0.27, 0.06), Pf(hp + 4.2, zb0 + 0.27, 0.06), Pf(hp + 4.2, zb0 + 0.35, 0.06), Pf(hp - 4.2, zb0 + 0.35, 0.06), 'paint_white')
    block(pa - 0.12, pb + 0.12, vp - 0.12, vp + 0.5, zT - 0.3, zT, 'stone_trim')        # coping band
    for k in range(6):                                                 # horizontal joints of the ashlar face
        z = zP + 0.6 + k * (zT - zP - 0.6) / 6
        if zs - 0.3 < z < zc + 1.2:
            continue
        mb.quad(Pf(0, z, 0.012), Pf(2 * hp, z, 0.012), Pf(2 * hp, z + 0.03, 0.012), Pf(0, z + 0.03, 0.012), 'stone_trim')
    # on top: a parapet with the clipped hedge behind it, the walk to the tower, side parapets over the wells
    parapet(pa, pb, vp, vp + 0.4, zT)
    block(pa + 0.4, pb - 0.4, vp + 0.4, vp + 1.6, zT, zT + 0.45, 'stone_trim', top='soil')
    mb.box((uc, vp + 1.0, zT + 0.8), (2 * hp - 1.2, 0.95, 0.75), 'shrub_green')
    walk(pa, pb, vp + 1.6, 0.0, zT)

    # --- the flights either side, two of ~18 risers with a landing between, from the plaza up to the terrace
    n1, n2, tr = 18, 19, 0.31
    rise = (zT - zP) / (n1 + n2)
    zm = zP + n1 * rise
    top_v = None
    for sg in (-1, 1):
        ux = uc + sg * (hp + sw / 2)
        yf1 = vp + 1.4 + n1 * tr
        stair_flight(mb, ux, yf1, sw, zm, n=n1, mat='stone_step', landing=1.4, tread=tr, flare=0.0, ground=gnd, zbot=zP)
        yf2 = yf1 + 1.0 + n2 * tr
        stair_flight(mb, ux, yf2, sw, zT, n=n2, mat='stone_step', landing=1.0, tread=tr, flare=0.0, ground=gnd, zbot=zm)
        top_v = yf2 + 1.2
        block(ux - sw / 2, ux + sw / 2, top_v, 0.0, gnd, zT, top='stone_step')       # the terrace behind the well
        walk(ux - sw / 2, ux + sw / 2, top_v - 0.05, 0.0, zT)
        parapet(*sorted((uc + sg * hp, uc + sg * (hp + 0.4))), vp + 0.4, top_v, zT)    # podium side over the well
    # --- beyond the wells: a planted tier, then the terrace wall, across the wings' fronts to the roads
    vA = vp + 2.5
    for ua, ub in ((u0, uc - hp - sw), (uc + hp + sw, u1)):
        block(ua, ub, vp, vA, gnd, zP + 2.8, top='soil')
        for k in range(int((ub - ua) / 2.6)):
            c = (ua + 1.3 + k * (ub - ua - 2.6) / max(1, int((ub - ua) / 2.6) - 1), vp + 1.25)
            mb.cylinder(c, 0.95, zP + 2.7, zP + 3.4, 'shrub_green', seg=10, r1=1.0)
            mb.cylinder(c, 1.0, zP + 3.4, zP + 3.8, 'shrub_green', seg=10, r1=0.45)
        block(ua - 0.1, ub + 0.1, vp - 0.1, vp + 0.25, zP + 2.65, zP + 2.85, 'stone_trim')
        block(ua, ub, vA, 0.0, gnd, zT, top='pavers')
        walk(ua, ub, vA + 0.35, 0.0, zT)
        parapet(ua, ub, vA, vA + 0.35, zT)
        inner = ub if ua < uc else ua                                  # parapet along the well
        parapet(*sorted((inner, inner + (-0.35 if ua < uc else 0.35))), vA + 0.35, top_v, zT)
        end = ua if ua < uc else ub                                    # and at the road end, up to the wing
        parapet(*sorted((end, end + (0.35 if ua < uc else -0.35))), vA + 0.35, -10.4, zT)
        # on the terrace between the wings and the stairs: a kerbed lawn along the hall with a row of clipped cones
        ba, bb = (1.4, ub - 1.3) if ua < uc else (ua + 1.3, 45.7)
        block(ba, bb, -11.8, -2.2, zT - 0.3, zT + 0.28, 'stone_trim', top='grass')
        for k in range(4):
            c = (ba + 1.2 + k * (bb - ba - 2.4) / 3, -4.0)
            mb.cylinder(c, 0.75, zT + 0.25, zT + 2.9, 'shrub_green', seg=10, r1=0.06)
            mb.cylinder((c[0], -9.6), 0.8, zT + 0.25, zT + 1.0, 'shrub_green', seg=10, r1=0.85)
            mb.cylinder((c[0], -9.6), 0.85, zT + 1.0, zT + 1.4, 'shrub_green', seg=10, r1=0.4)
    for sg in (-1, 1):                                                 # globe lamps on the plaza by the flights
        lamp_post(mb, uc + sg * (hp + sw + 1.2), vp - 1.6, h=3.4, z=zP - 0.04 * 1.6)


def sang_stone_bank(pts):
    """The bank of natural boulders along the 상뜰's west drive (tools/build_campus.py DAEWOO['bank'], Kakao roadview of
    August 2008): grey boulders 0.6 - 1.1 m long right behind the granite kerb, one course where the bank is low and a
    second set back on it where it is higher, small clipped shrubs between them, and a grass berm behind at the top,
    walked on, falling back to the lawn.  pts: [x, y behind the kerb (the lawn on the left going along), x, y of the
    drive's edge there (the bank's height is over it), height]."""
    rr = random.Random(8707)                     # (its own: the module's rnd keeps the other landmarks' draws)
    mb = MeshBuilder('lm_sang_stone_bank')
    P = [Vector((q[0], q[1])) for q in pts]
    ref = [ground_top(q[2], q[3]) for q in pts]
    L = [0.0]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + (b - a).length)

    def at(s):
        """point, left normal, top height at arc length s along the line"""
        s = min(max(s, 0.0), L[-1] - 1e-6)
        k = max(i for i in range(len(L) - 1) if L[i] <= s)
        f = (s - L[k]) / max(L[k + 1] - L[k], 1e-9)
        d = (P[k + 1] - P[k]).normalized()
        top = (ref[k] + pts[k][4]) * (1 - f) + (ref[k + 1] + pts[k + 1][4]) * f
        return P[k] + (P[k + 1] - P[k]) * f, Vector((-d.y, d.x)), top

    def boulder(c, nrm, ln, dp, z0, z1, key):
        """a rough, rounded grey boulder: c its foot's middle, long side along the line (across nrm), flattish on top"""
        yaw = rr.uniform(-0.3, 0.3)
        t0 = Vector((nrm.y, -nrm.x))
        t, nr = t0 * math.cos(yaw) + nrm * math.sin(yaw), nrm * math.cos(yaw) - t0 * math.sin(yaw)
        seg, rings = 10, 4
        jit = [[1 + rr.uniform(-0.2, 0.2) for _ in range(seg)] for _ in range(rings + 1)]
        tilt = rr.uniform(-0.15, 0.15)
        Q = []
        for j in range(rings + 1):
            th = (math.pi / 2) * j / rings                       # foot ring (sunk) -> crown
            row = []
            for i in range(seg):
                ph = 2 * math.pi * i / seg
                r = jit[j][i] * (1.0 if j < rings else 0.0) * (1.0 if j < rings - 1 else 0.8)
                cx, cy = 0.5 * ln * r * math.cos(th) * math.cos(ph), 0.5 * dp * r * math.cos(th) * math.sin(ph)
                cz = z0 + (z1 - z0) * (math.sin(th) ** 0.55) * (1 + 0.08 * (jit[j][(i + 3) % seg] - 1)) + tilt * cx
                p = c + t * cx + nr * cy
                row.append((p.x, p.y, cz))
            Q.append(row)
        for j in range(rings):
            for i in range(seg):
                k = (i + 1) % seg
                mb.face([Q[j][i], Q[j][k], Q[j + 1][k], Q[j + 1][i]], 'stone_boulder', smooth=key)

    n = 0
    s = 0.2
    while s < L[-1] - 0.3:
        ln = rr.uniform(0.6, 1.1)
        p, nrm, top = at(s + ln / 2)
        g = ground_top(p.x, p.y)
        H = max(0.35, top - g)
        dp = rr.uniform(0.5, 0.8)
        h1 = min(H + 0.06, rr.uniform(0.38, 0.58))               # the front course
        boulder(p + nrm * (0.08 + dp / 2), nrm, ln, dp, g - 0.12, g + h1, 'bk%d' % n)
        if H > h1 + 0.12:                                        # a second course, set back on it, up to the top
            n += 1
            p2, nrm2, top2 = at(s + ln * rr.uniform(0.3, 0.9))
            boulder(p2 + nrm2 * (0.45 + dp / 2), nrm2, rr.uniform(0.55, 0.95), dp * 0.9, g + h1 * 0.5 - 0.1,
                    top2 + rr.uniform(-0.04, 0.05), 'bk%d' % n)
        if rr.random() < 0.3:                                    # a small clipped shrub between the boulders
            q = p + nrm * rr.uniform(0.6, 0.95) + Vector((nrm.y, -nrm.x)) * (ln / 2)
            r = rr.uniform(0.22, 0.38)
            mb.sphere((q.x, q.y, top - 0.05 + r * 0.3), r, 'shrub_green', seg=8, rings=5, sz=0.75)
        n += 1
        s += ln * rr.uniform(0.8, 0.92)
    # the berm behind: level at the top just past the boulders, then falling back to the lawn (and walked on)
    K = max(2, int(L[-1] / 1.0))
    offs = [0.1, 0.6, 1.1, 1.7, 2.3, 2.9, 3.5, 4.1, 4.7, 5.3]

    turn = [0.0] * len(P)                                        # the radius the line bends round at each point
    for i in range(1, len(P) - 1):
        d0, d1 = (P[i] - P[i - 1]).normalized(), (P[i + 1] - P[i]).normalized()
        ang = abs(math.atan2(d0.x * d1.y - d0.y * d1.x, d0.dot(d1)))
        turn[i] = (L[i + 1] - L[i - 1]) / 2 / ang if ang > 0.02 else 1e9
    turn = [t if t else 1e9 for t in turn]

    def berm(s, o):
        p, nrm, top = at(s)
        room = min(turn[i] for i in range(len(P)) if abs(L[i] - s) < 2.0)
        far = o >= offs[-1] or o > room - 0.4                    # (the far edge on the lawn; inside a bend, short)
        q = p + nrm * min(o, max(0.6, room - 0.4))
        z = -1e9 if far else top - max(0.0, o - 1.1) * 0.55
        return (q.x, q.y, max(z, ground_top(q.x, q.y) + 0.02))
    for k in range(K):
        sa, sb = L[-1] * k / K, L[-1] * (k + 1) / K
        for oa, ob in zip(offs, offs[1:]):
            qd = [berm(sa, oa), berm(sb, oa), berm(sb, ob), berm(sa, ob)]
            if all(z - ground_top(x, y) < 0.04 for x, y, z in qd):
                continue                                         # (on the lawn already: the terrain does)
            mb.face(qd, 'grass', smooth='bank_berm')
            WALK_FACES.append([tuple(v) for v in qd])
    print('상뜰 boulder bank: %d boulders over %.1f m' % (n, L[-1]))
    return mb


def daewoo_rear(mb, P, Le, plinth, floors, fh, Hw, wall):
    """The back of 대우관 (Google Street View 2009-11, from the drive behind it; the hall dates from 1996): none of the
    buttresses and battlements of the old halls but a plain coped parapet with the slate roof behind; single windows
    in pairs; in the middle a broad tower 2.5 m out that rises a storey and a half over the parapet, its middle part
    the highest, with a row of five vent pipes on top and a back door at its foot; either side, half way out to the
    wings, a stair glazed from the ground floor to the top in one tall dark screen, a plain box over it on the roof;
    a few downpipes.  P: the back wall, s from its east end (the tower's axis at Le / 2, as the front tower's)."""
    sc = Le / 2
    tw, tp = 6.0, 2.5               # back tower: half width, projection
    st, sw = 12.6, 1.6              # stair bays: distance from the middle, half width of the glazing
    zt = plinth + floors * fh       # top of the window floors
    for a, b in ((0.0, sc - st - sw - 0.7), (sc - st + sw + 0.7, sc - tw - 0.2), (sc + tw + 0.2, sc + st - sw - 0.7),
                 (sc + st + sw + 0.7, Le)):
        window_grid(mb, P, Le, plinth, floors, fh, 3.3, wall, ww=0.42, trim='stone_trim', mull=1, s_start=a, s_end=b)
    for c in (sc - st, sc + st):
        hole = (c - sw, c + sw, plinth + 0.9, zt - 0.3)
        wall_holes(mb, P, c - sw - 0.7, c + sw + 0.7, plinth, zt, wall, [hole])
        reveal(mb, P, *hole, 0.25, wall)
        glazing(mb, P, *hole, -0.25, 3, floors * 2, 'frame_dark')
        mb.box(P(c, Hw + 1.3, -1.5), (2 * sw + 1.8, 3.0, 3.6), wall, mats={'top': 'roof_flat'})
        bar(mb, P, c - sw - 0.95, Hw + 3.12, c + sw + 0.95, Hw + 3.12, 0.16, 0.0, 0.1, 'stone_trim', ends=True)
    flat_wall(mb, P, sc - tw - 0.2, sc + tw + 0.2, plinth, zt, wall)              # (behind the tower)
    flat_wall(mb, P, 0, Le, zt, Hw, wall)
    bar(mb, P, -0.15, Hw + 0.15, Le + 0.15, Hw + 0.15, 0.3, -0.3, 0.12, 'stone_trim', ends=True)   # coping
    for s in (sc - 18.2, sc - 8.4, sc + 8.4, sc + 18.2):                              # downpipes
        bar(mb, P, s, -0.6, s, Hw, 0.14, 0.0, 0.14, 'metal_dark')
    # the tower: the flanks to ht1, the middle (|s - sc| < 3) to ht2; its upper part runs back into the roof
    T = lambda s, z, d=0.0: P(s, z, d + tp)
    ht1, ht2, mid = Hw + 3.9, Hw + 5.4, 3.0
    for a, b in ((sc - tw, sc - mid), (sc + mid, sc + tw)):
        window_grid(mb, T, Le, plinth, floors, fh, b - a, wall, ww=0.3, trim='stone_trim', mull=0, s_start=a, s_end=b)
        flat_wall(mb, T, a, b, zt, ht1, wall)
        flat_wall(mb, T, a, b, -1.0, plinth, wall)
        mb.quad(P(a, ht1, -6.0), P(b, ht1, -6.0), P(b, ht1, tp), P(a, ht1, tp), 'roof_flat')
    window_grid(mb, T, Le, plinth + fh, floors - 1, fh, 3.0, wall, ww=0.55, trim='stone_trim', mull=1,
                s_start=sc - mid, s_end=sc + mid)
    door = (sc - 1.5, sc + 1.5, 0.9, 3.5)                      # the back door, from the yard (about 1 m up here)
    wall_holes(mb, T, sc - mid, sc + mid, -1.0, plinth + fh, wall, [door])
    reveal(mb, T, *door, 0.4, wall)
    shopfront(mb, T, door[0], door[1], door[2], door[3], -0.4, bays=4, door_h=2.3)
    vestibule(mb, T, door[0] - 0.2, door[1] + 0.2, door[2] + 0.002, door[3] - 0.05, -0.42, 2.0, lights=1)
    flat_wall(mb, T, sc - mid, sc + mid, zt, ht2, wall)
    mb.quad(P(sc - mid, ht2, -6.0), P(sc + mid, ht2, -6.0), P(sc + mid, ht2, tp), P(sc - mid, ht2, tp), 'roof_flat')
    for s0, z1, z0_ in ((sc - tw, ht1, -1.0), (sc - mid, ht2, ht1)):                  # the sides (east-facing)
        mb.quad(P(s0, z0_, -6.0), P(s0, z0_, tp), P(s0, z1, tp), P(s0, z1, -6.0), wall)
    for s1, z1, z0_ in ((sc + tw, ht1, -1.0), (sc + mid, ht2, ht1)):                  # (west-facing)
        mb.quad(P(s1, z0_, tp), P(s1, z0_, -6.0), P(s1, z1, -6.0), P(s1, z1, tp), wall)
    for s0, s1, z1 in ((sc - tw, sc + tw, ht1), (sc - mid, sc + mid, ht2)):            # its back, in the roof
        mb.quad(P(s1, Hw - 0.5, -6.0), P(s0, Hw - 0.5, -6.0), P(s0, z1, -6.0), P(s1, z1, -6.0), wall)
    for s in (sc - tw, sc - mid, sc + mid, sc + tw):                                  # strips up the tower
        bar(mb, T, s, -1.0, s, (ht2 if abs(s - sc) < mid + 0.1 else ht1) + 0.25, 0.45, 0.0, 0.22, wall, ends=True)
    for a, b, z in ((sc - tw - 0.15, sc - mid, ht1), (sc + mid, sc + tw + 0.15, ht1), (sc - mid - 0.15, sc + mid + 0.15, ht2)):
        bar(mb, T, a, z + 0.12, b, z + 0.12, 0.25, -0.2, 0.3, 'stone_trim', ends=True)
    for k in range(5):                                                                # vent pipes
        c = P(sc - 2.0 + k, 0.0, tp - 1.3)
        mb.cylinder((c[0], c[1]), 0.15, ht2, ht2 + 1.6, 'metal', seg=8)
        mb.cylinder((c[0], c[1]), 0.22, ht2 + 1.6, ht2 + 1.75, 'metal', seg=8)


def daewoo_back(mb, z0):
    """The yard behind 대우관 (Street View 2009-11; levels from tools/build_campus.py DAEWOO_BACK), in the hall frame
    (u, v): the long planter in the recess between the wings, low concrete walls round soil and pointed conifers;
    the parking bays painted on the car park; the iron fence along the road to 북문 above its east side."""
    db = CAMPUS['daewoo_back']
    hy = lambda u, v: db['h0'] + db['su'] * (u - db['u0']) + db['sv'] * max(0.0, v - db['v0']) - z0
    gl = local_ground(mb)
    (u0, v0), (u1, _), (_, v1) = db['planter'][0], db['planter'][1], db['planter'][2]
    th, ht = 0.25, 0.85

    def wall_run(a, b, inward):
        """a planter wall from a to b (u, v), its inside towards `inward` (unit 2D), top following the yard"""
        a, b, nn = Vector(a), Vector(b), Vector(inward) * th
        pts = [(a, 0), (b, 0), (b, 1), (a, 1)]
        q = lambda p, k, top: (*(p + nn * k), hy(*p) + (ht if top else -0.3))
        mb.quad(q(a, 0, False), q(b, 0, False), q(b, 0, True), q(a, 0, True), 'concrete')
        mb.quad(q(b, 1, False), q(a, 1, False), q(a, 1, True), q(b, 1, True), 'concrete')
        mb.quad(q(a, 0, True), q(b, 0, True), q(b, 1, True), q(a, 1, True), 'stone_trim')
        mb.quad(q(a, 1, False), q(a, 0, False), q(a, 0, True), q(a, 1, True), 'concrete')
        mb.quad(q(b, 0, False), q(b, 1, False), q(b, 1, True), q(b, 0, True), 'concrete')

    # two planters, either side of the paved space in front of the back tower and its door
    for ua, ub in ((u0, 17.0), (30.1, u1)):
        wall_run((ua, v0), (ub, v0), (0, 1))
        wall_run((ub, v0), (ub, v1), (-1, 0))
        wall_run((ub, v1), (ua, v1), (0, -1))
        wall_run((ua, v1), (ua, v0), (1, 0))
        zs = lambda u, v: hy(u, v) + ht - 0.15
        mb.quad((ua + th, v0 + th, zs(ua, v0)), (ub - th, v0 + th, zs(ub, v0)), (ub - th, v1 - th, zs(ub, v1)),
                (ua + th, v1 - th, zs(ua, v1)), 'soil')
    # (the parking bays' white lines: parking_lines, with every other car park's)
    # the iron fence along the road to 북문, posts every 2.4 m on the ground and pickets between
    pts = [Vector(p) for p in db['fence']]
    for pa, pb in zip(pts, pts[1:]):
        d = pb - pa
        n = max(1, int(d.length / 2.4))
        for k in range(n):
            a = pa + d * (k / n)
            b = pa + d * ((k + 1) / n)
            za, zb = gl(*a) + 0.02, gl(*b) + 0.02
            mb.box((a.x, a.y, za + 0.6), (0.07, 0.07, 1.25), 'metal_dark')
            rz = math.atan2(d.y, d.x)
            for zz in (0.18, 1.08):
                m_ = (a + b) / 2
                mb.box((m_.x, m_.y, (za + zb) / 2 + zz), ((b - a).length, 0.04, 0.05), 'metal_dark', rotz=rz)
            npk = int((b - a).length / 0.16)
            for j in range(1, npk):
                p_ = a + (b - a) * (j / npk)
                zp = za + (zb - za) * (j / npk)
                mb.box((p_.x, p_.y, zp + 0.63), (0.025, 0.025, 0.9 if j % 2 else 0.72), 'metal_dark', rotz=rz)
        bpt = pts[-1]
        mb.box((bpt.x, bpt.y, gl(*bpt) + 0.62), (0.07, 0.07, 1.25), 'metal_dark')


def daewoo():
    """대우관 (1996): a six-storey hall in white stone, Collegiate Gothic like the old halls but pale
    (reference/대우관_블로그_본관_정면_상뜰.jpg): an H plan whose end pavilions stand forward with tall gables
    towards the round pine garden (상뜰), a long slate roof between them and a raised central entrance bay.
    It stands on a terrace over the 상뜰 with the main door down in the podium in front (daewoo_front); the tower
    door on the terrace is a tall pointed arch of dark glass (reference/대우관_정면_전경.jpg)."""
    b = bld(242897922)
    fp = b['footprint']
    a, bb = Vector(fp[3]), Vector(fp[4])                 # the recessed front between the pavilions
    t = (bb - a).normalized()
    nl = Vector((-t.y, t.x))                              # into the building (north); the front faces -nl
    ang = math.atan2(t.y, t.x)
    W = lambda u, v: tuple(a + t * u + nl * v)
    lv = CAMPUS['daewoo_front']                           # levels from tools/build_campus.py (DAEWOO)
    centre = dict(b, footprint=[W(0.4, 0), W(46.7, 0), W(46.7, 14.8), W(0.4, 14.8)])
    out = gothic('daewoo', centre, tuple(-nl), 6, tower_w=9.0, tower_extra=2.5, ivy=0, wings=False, fh=3.6,
                 wall='stone_white', stairs=dict(none=True), door=dict(w=3.0, arch='pointed', spring=2.45, style='modern'),
                 z_floor=lv['floor'], rear=daewoo_rear)
    z0 = out[0].z_base
    zT, zP = lv['terrace'] - z0, lv['plaza'] - z0
    # three steps from the terrace up to the tower door
    stair_flight(out[0], 0, out[0].tower_front, 6.4, 1.2, n=3, mat='stone_step', landing=1.0, tread=0.35, flare=0.4,
                 ground=zP, zbot=zT)
    mb = MeshBuilder('lm_daewoo_pavilions')
    mb.xf = local_frame(a.x, a.y, ang, z0)
    gable_hall(mb, -12.1, 0.0, -12.2, 24.5, 6, 3.6, 'stone_white')
    gable_hall(mb, 47.1, 55.5, -10.9, 24.3, 6, 3.6, 'stone_white')
    fr = MeshBuilder('lm_daewoo_front')
    fr.xf = local_frame(a.x, a.y, ang, z0)
    daewoo_front(fr, zT, zP, lv['u0'], lv['u1'], vp=lv['podium'])
    bk = MeshBuilder('lm_daewoo_back')
    bk.xf = local_frame(a.x, a.y, ang, z0)
    daewoo_back(bk, z0)
    out += [mb, fr, bk]
    # 상뜰: the round lawn in the middle of the paved circle (tools/build_campus.py SANG); the low pale kerb round it
    # is drawn with every other kerb along the paving's edge (web/src/curbs.js)
    sg = CAMPUS.get('sang')
    if sg:
        cb = MeshBuilder('lm_daewoo_sang_curb')
        (cx, cy), r = sg['c'], sg['r']
        n_ = 40
        # inside it the lawn, a low dome a little under the curb at its edge and some 0.4 m over it in the middle
        # (대우관_2024_정면과_상뜰.jpg), walked on; the tree stands on its crown
        rings, H = 7, 0.4
        edge = [ground_top(cx + r * math.cos(2 * math.pi * k / n_), cy + r * math.sin(2 * math.pi * k / n_)) + 0.1
                for k in range(n_)]
        z_mid = sum(edge) / n_ + H

        def dome(k, j):
            f = j / rings                                   # 0 at the crown .. 1 at the curb
            a = 2 * math.pi * (k % n_) / n_
            z = z_mid + (edge[k % n_] - z_mid) * f ** 2
            return (cx + r * f * math.cos(a), cy + r * f * math.sin(a), z)
        for j in range(rings):
            for k in range(n_):
                q = [dome(k, j), dome(k, j + 1), dome(k + 1, j + 1), dome(k + 1, j)] if j else \
                    [dome(k, 0), dome(k, 1), dome(k + 1, 1)]
                cb.face(q, 'grass', smooth='sang_lawn')
                WALK_FACES.append([tuple(p) for p in q])
        out.append(cb)
    # 상뜰's south flight (issue #39; reference/대우관_정면_전경.jpg): from the end of the broad walk down through the trees
    # to the footway towards 연희관, granite, 5.5 m wide like the walk, steel handrails on low kerbs both sides
    st = lv.get('stair')
    if st:
        out.append(garden_flight(st, wall='stone_granite'))
    if lv.get('bank'):                                   # the boulder bank along the 상뜰's west drive (issue #87)
        out.append(sang_stone_bank(lv['bank']))
    return out


def yeonhui():
    """연희관 (1956): a stone Gothic hall, H plan like 대우관 but in the dark rubble of the old halls, with a central
    tower and ivy over the walls (yonsei.ac.kr building history photo, reference/연희관_*.jpg)."""
    b = bld(245623759)
    fp = b['footprint']
    a, bb = Vector(fp[3]), Vector(fp[4])
    t = (bb - a).normalized()
    nl = Vector((-t.y, t.x))
    ang = math.atan2(t.y, t.x)
    W = lambda u, v: tuple(a + t * u + nl * v)
    centre = dict(b, footprint=[W(0.4, 0), W(39.9, 0), W(39.9, 14.2), W(0.4, 14.2)])
    yh = CAMPUS.get('yeonhui', {})
    # the door 2.55 m over the road before it (tools/build_campus.py YEONHUI): seventeen risers of 0.15 in one flight,
    # no landing, down to the road between rubble side walls with pale copings (Kakao roadview from the road, 2026)
    # Heights from reference/연희관_정면_2023.jpg seen through the compare/yeonhui camera (fitted to the forecourt and
    # the threshold), checked against the ratios in reference/학교연혁_연희관.jpg (reference/고증.md 3.5): three storeys
    # of 3.95 m over the half-sunk basement (window rows 1.4 - 3.7, 5.1 - 7.5, 8.9 - 11.3 m over the threshold, the
    # cornice 12.6 m) under the roof; the tower 10.5 m across its corner turrets, a fourth light over the cornice,
    # its battlements 20.6 m up; the end pavilions' storeys level with the hall's, their gables' apex 18.3 m up
    out = gothic('yeonhui', centre, tuple(-nl), 3, tower_w=10.5, tower_extra=7.3, ivy=0.85, wings=False, fh=3.95,
                 stairs=dict(width=4.8, wl=5.6, split=99, maxrise=0.152), door=dict(w=3.3, style='four'),
                 z_floor=yh.get('floor'), tower_floors=4)
    mb = MeshBuilder('lm_yeonhui_pavilions')
    iv = MeshBuilder('lm_yeonhui_pavilions_ivy')
    mb.xf = iv.xf = local_frame(a.x, a.y, ang, out[0].z_base)
    # (the OSM outline makes the two fronts 14.1 and 11.7 m wide; the photos' gables are about 9.2 m, so the pitches
    # are set for the photos' apex height rather than their 1.1)
    gable_hall(mb, -14.0, 0.0, -7.9, 28.8, 3, 3.95, 'stone_rubble', pitch=0.81, plinth=1.3, iv=iv, ivy=0.85, seed=3, gothic_trim=True)
    gable_hall(mb, 40.3, 52.0, -6.7, 30.1, 3, 3.95, 'stone_rubble', pitch=0.97, plinth=1.3, iv=iv, ivy=0.85, seed=9, gothic_trim=True)
    return out + [mb, iv] + yeonhui_garden(yh)


def garden_flight(f, wall='stone_rubble', mat='stone_step', apron=True):
    """An outdoor flight between two levels of the ground, laid out by tools/build_campus.py (flight_at): from the
    middle of its upper edge f['top'] it goes down along f['down'] -- a short landing, then f['n'] risers of granite
    treads on a solid core -- to the ground at its foot.  f['cheek'] > 0: side walls of the wall's stone with a pale
    coping that follow the flight, square capped posts at both ends; f['rails']: steel handrails on posts along both
    sides (on the side walls when there are any).  f['head']: how far the side walls run on past the top (1.2 m);
    apron=False: no paved apron round the head (a flight that rises onto a built landing)."""
    mb = MeshBuilder('lm_flight_' + f['name'])
    d = Vector(f['down']).normalized()
    mb.xf = local_frame(f['top'][0], f['top'][1], math.atan2(d.x, -d.y), 0.0)
    zt, zf, n, w = f['z_top'], f['z_foot'], f['n'], f['width']
    lnd, tr = f['landing'], f['tread']
    # the drawn ground at the head must not stand over the landing: there the 5 m grid's triangles are pulled up by
    # a node out on the drive, and the one-riser ways in from the drives along 교육관 and 성암관 lay under 0.1 -
    # 0.35 m of it, the drive running on over them.  Raise the whole flight to the drive (its foot then a little over
    # the ground).  (Lower down, where a sloping walk at the foot buries the ends of the last treads, it stays.)
    gl0 = local_ground(mb)
    lift = max(gl0(x_, y_) + 0.02 - zt for x_ in (-w / 2, -w / 4, 0.0, w / 4, w / 2) for y_ in (0.0, -lnd))
    if lift > 0.05:
        print('garden flight %s raised %.2f m over the drawn ground' % (f['name'], lift))
        zt, zf = zt + lift, zf + lift
    gnd = zf - 1.6
    stair_flight(mb, 0.0, 0.0, w, zt, n=n, mat=mat, landing=lnd, tread=tr, flare=0.0, ground=gnd, zbot=zf,
                 cheek=0.0)
    y_foot = -lnd - n * tr
    ct = f.get('cheek', 0.0)
    hw = w / 2
    rise = (zt - zf) / n
    # a paved apron round the head: the 5 m terrain grid cannot hold a level edge there, so it sags up to a metre
    # under the landing; the apron runs from the landing out over it to meet the ground (and is walked on)
    gl = local_ground(mb)
    hx, L, K = hw + ct + 1.6, 3.4, 10

    def apron_z(x, y):
        dx = max(0.0, abs(x) - (hw + ct))
        dy = max(0.0, y - 1.2)
        return min(zt, max(gl(x, y) + 0.03, zt - 0.32 * math.hypot(dx, dy)))
    xs = [-hx + 2 * hx * i / K for i in range(K + 1)]
    ys = [-lnd - 0.2 + (1.2 + L + lnd + 0.2) * j / 6 for j in range(7)]
    W_ = lambda lx, ly, lz: tuple(mb.xf @ Vector((lx, ly, lz)))
    for i in range(K if apron else 0):
        for j in range(6):
            (xa, xb), (ya, yb) = (xs[i], xs[i + 1]), (ys[j], ys[j + 1])
            if abs((xa + xb) / 2) < hw + ct and (ya + yb) / 2 < 1.2:
                continue                                       # (the landing itself)
            q = [(xa, ya, apron_z(xa, ya)), (xb, ya, apron_z(xb, ya)), (xb, yb, apron_z(xb, yb)), (xa, yb, apron_z(xa, yb))]
            if all(z - gl(x, y) < 0.06 for x, y, z in q):
                continue                                       # (already on the ground: the terrain does)
            mb.face(q, 'pavers')
            WALK_FACES.append([W_(*p) for p in q])
    if ct and f.get('plain'):
        # f['plain']: sides of the wall's own rubble, no coping, no posts (연희관's south flight, set in a gap of the
        # retaining wall along 한경길: tools/build_campus.py YEONHUI['wall']): flush with the wall's top
        # (f['wall_h'] over the foot) at the bottom, then just over the nosings up to the head
        wh = f.get('wall_h', 0.75)
        prof = [(1.2, zt + 0.06), (-lnd, zt + 0.06)]
        for k in range(1, 11):                             # (the nosing line, down the flight; y decreasing)
            y_ = -lnd + (y_foot + 0.05 + lnd) * k / 10
            z_nos = zt - (zt - (zf + rise)) * k / 10
            prof.append((y_, max(z_nos + 0.06, zf + wh)))
        prof.append((y_foot - 0.25, zf + wh))
        for sg in (-1, 1):
            x0, x1 = sorted((sg * hw, sg * (hw + ct)))
            sloped_wall(mb, x0, x1, prof, gnd, wall, cap=wall, ct=0.02)
    elif ct:
        hc = 0.55 if not f.get('rails') else 0.18          # (a kerb under handrails, a low wall otherwise)
        head = f.get('head', 1.2)
        for sg in (-1, 1):
            x0, x1 = sorted((sg * hw, sg * (hw + ct)))
            sloped_wall(mb, x0, x1, [(head, zt + hc), (-lnd, zt + hc), (y_foot + 0.05, zf + rise + hc - 0.05),
                                     (y_foot - 0.25, zf + hc - 0.05)], gnd, wall)
            if not f.get('rails'):
                pedestal(mb, sg * (hw + ct / 2), head - 0.2, zt + hc + 0.3, gnd, wall, w=ct + 0.2)
                pedestal(mb, sg * (hw + ct / 2), y_foot - 0.1, zf + hc + 0.25, gnd, wall, w=ct + 0.2)
    if f.get('rails'):
        xr = hw + (ct / 2 if ct else -0.12)
        ya, yb = 1.0, y_foot - 0.15

        def zr(y):                                         # the nosing line (and the kerb on top of the walls)
            if y >= -lnd:
                return zt + (0.18 if ct else 0.0)
            return zt - (-lnd - y) / (n * tr) * (zt - zf) + (0.18 if ct else 0.0)
        for sg in (-1, 1):
            x = sg * xr
            npost = max(2, int(round((ya - yb) / 1.6)) + 1)
            ys = [ya + (yb - ya) * k / (npost - 1) for k in range(npost)]
            for y in ys:
                rod(mb, (x, y, zr(y) - 0.05), (x, y, zr(y) + 0.95), 0.025, 'metal_dark', seg=6)
            knots = [ya, -lnd, yb]
            for y0, y1 in zip(knots, knots[1:]):
                rod(mb, (x, y0, zr(y0) + 0.95), (x, y1, zr(y1) + 0.95), 0.03, 'metal_dark', seg=6)
                rod(mb, (x, y0, zr(y0) + 0.45), (x, y1, zr(y1) + 0.45), 0.015, 'metal_dark', seg=6)
    return mb


def yeonhui_garden(yh):
    """연희관 앞 정원 (tools/build_campus.py YEONHUI): the walled flights into the garden -- the broad one down the
    bank from the road before 연희관, the one up from 한경길 behind 언더우드관 (through a gap in the retaining wall,
    plain rubble sides), the one-step ways in from the drives along 교육관 and 성암관 -- the low concrete drum of the
    round planter in the middle, its clipped yew planted in it (shrubs), the forecourt's slabs, the rubble retaining
    wall along 한경길 (yeonhui_wall) and the lamp at the south flight's head."""
    out = [garden_flight(f) for f in yh.get('flights', [])]
    pl = yh.get('planter')
    if pl:
        mb = MeshBuilder('lm_yeonhui_planter')
        (cx, cy), r, h = pl['c'], pl['r'], pl['h']
        zs = [ground_top(cx + r * math.cos(a), cy + r * math.sin(a)) for a in [k * math.pi / 8 for k in range(16)]]
        z0, z1 = min(zs) - 0.3, max(zs) + h
        mb.cylinder((cx, cy), r, z0, z1, 'concrete', seg=40, cap_top=False)
        ring = [(cx + r * math.cos(2 * math.pi * k / 40), cy + r * math.sin(2 * math.pi * k / 40)) for k in range(41)]
        rin = [(cx + (r - 0.22) * math.cos(2 * math.pi * k / 40), cy + (r - 0.22) * math.sin(2 * math.pi * k / 40)) for k in range(41)]
        for k in range(40):                                                    # its flat top and the rim's inner face
            mb.quad((*ring[k], z1), (*ring[k + 1], z1), (*rin[k + 1], z1), (*rin[k], z1), 'stone_trim')
            mb.quad((*rin[k], z1), (*rin[k + 1], z1), (*rin[k + 1], z1 - 0.12), (*rin[k], z1 - 0.12), 'concrete')
        mb.face([(x, y, z1 - 0.12) for x, y in rin[:-1]], 'soil')
        out.append(mb)
    fc = yh.get('forecourt')
    if fc:
        out.append(yeonhui_forecourt(fc))
    if yh.get('wall'):
        out.append(yeonhui_wall(yh['wall']))
    if yh.get('lamp'):
        mb = MeshBuilder('lm_yeonhui_lamp')
        _yh_lamp_globe(mb, *yh['lamp'], ground_top(*yh['lamp']))
        out.append(mb)
    return out


def yeonhui_wall(runs, t=0.4, bed=1.8, back=2.8):
    """The rubble retaining wall under 연희관 앞 정원's south edge (tools/build_campus.py YEONHUI['wall']: runs of
    [x, y, z at the foot, z at the top] along its face): uncoursed rubble from below the road up to its top, no coping;
    behind it a soil bed level with its top (bed m deep, the boxwood mounds stand on it: walked on), sloping on back
    to the lawn by `back` m.  The face looks away from the garden (towards 한경길 and the two drives)."""
    mb = MeshBuilder('lm_yeonhui_wall')
    gc = Vector(CAMPUS['yeonhui']['planter']['c'])
    for run in runs:
        P = [Vector((p[0], p[1])) for p in run]
        N = []
        for i in range(len(P)):
            tg = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
            nv = Vector((-tg.y, tg.x))
            N.append(nv if nv.dot(gc - P[i]) > 0 else -nv)       # (into the garden)
        zt = [max(p[3], ground_top(*(P[i] + N[i] * 0.2)) + 0.02) for i, p in enumerate(run)]
        gnd = [min(p[2], ground(*(P[i] - N[i] * 0.3))) - 0.6 for i, p in enumerate(run)]
        rows = []                                              # (depth into the garden, z) at each vertex
        for i in range(len(P)):
            zb = ground_top(*(P[i] + N[i] * back)) + 0.02           # (on the lawn)
            rows.append([(0.0, zt[i]), (t, zt[i]), (bed, max(zt[i], ground_top(*(P[i] + N[i] * bed)) + 0.02)), (back, zb)])
        for i in range(len(P) - 1):
            a, b = P[i], P[i + 1]
            out_n = -(N[i] + N[i + 1]).normalized()
            oface(mb, [(*a, gnd[i]), (*b, gnd[i + 1]), (*b, zt[i + 1]), (*a, zt[i])], 'stone_rubble', (*out_n, 0))
            for k in range(3):
                (da, za), (db, zb_) = rows[i][k], rows[i][k + 1]
                (dc, zc), (dd, zd) = rows[i + 1][k], rows[i + 1][k + 1]
                q = [(*(a + N[i] * da), za), (*(b + N[i + 1] * dc), zc), (*(b + N[i + 1] * dd), zd), (*(a + N[i] * db), zb_)]
                oface(mb, q, 'stone_rubble' if k == 0 else 'soil', (0, 0, 1))
                if k > 0:
                    WALK_FACES.append([tuple(v) for v in q])
        for i, sg in ((0, 1), (len(P) - 1, -1)):               # the two ends: the wall's own rubble across it
            tg = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized() * sg
            a, b = P[i], P[i] + N[i] * t
            oface(mb, [(*a, gnd[i]), (*b, gnd[i]), (*b, zt[i]), (*a, zt[i])], 'stone_rubble', (*(-tg), 0))
    return mb


def _yh_lamp_globe(mb, x, y, z):
    """the single-globe lamp at the head of 연희관 앞 정원's south flight (2008 roadview): a dark post on a low square
    foot, a collar under the head, one white globe about 4.3 m up"""
    mb.box((x, y, z + 0.2), (0.42, 0.42, 0.5), 'metal_dark')
    mb.cylinder((x, y), 0.1, z + 0.45, z + 3.95, 'metal_dark', seg=10, r1=0.06)
    mb.cylinder((x, y), 0.14, z + 0.45, z + 1.1, 'metal_dark', seg=10, r1=0.1)
    mb.cylinder((x, y), 0.09, z + 3.9, z + 4.02, 'metal_dark', seg=10)
    mb.sphere((x, y, z + 4.25), 0.25, 'globe', seg=14, rings=10)
    mb.sphere((x, y, z + 4.52), 0.05, 'metal_dark', seg=8, rings=6)


def yeonhui_forecourt(fc):
    """The forecourt at the head of the south flight (tools/build_campus.py YEONHUI['forecourt'];
    reference/연희관_정면_2023.jpg): old concrete slabs a little over the terrain's paving, dark joints radiating from a
    point between the tips of the two south beds (and the walk's centre joint on north), and across the head of the
    flight a drain of perforated concrete blocks, two rows of oval holes each."""
    from mathutils.geometry import tessellate_polygon
    mb = MeshBuilder('lm_yeonhui_forecourt')
    poly = [Vector(p) for p in fc['poly']]
    for tri in tessellate_polygon([[p for p in poly]]):
        mb.face([tuple(poly[i]) for i in tri[::-1]] if _area2([poly[i] for i in tri]) < 0 else [tuple(poly[i]) for i in tri],
                'concrete_dark')

    def strip(a, b, w, z_up, mat):
        a, b = Vector(a), Vector(b)
        d = (b - a).xy
        if d.length < 1e-3:
            return
        o = Vector((-d.y, d.x)).normalized() * (w / 2)
        mb.face([(a.x - o.x, a.y - o.y, a.z + z_up), (b.x - o.x, b.y - o.y, b.z + z_up),
                 (b.x + o.x, b.y + o.y, b.z + z_up), (a.x + o.x, a.y + o.y, a.z + z_up)], mat)
    for ray in fc['rays']:
        for a, b in zip(ray, ray[1:]):
            strip(a, b, 0.035, 0.004, 'asphalt')
    # the drain: blocks 0.6 m long and 0.42 m across, a little proud of the slabs, two rows of six holes each
    a, b = Vector(fc['drain'][0]), Vector(fc['drain'][1])
    L = (b - a).xy.length
    t = (b - a).normalized()
    t2 = Vector((t.x, t.y, 0.0)).normalized()
    o = Vector((-t2.y, t2.x, 0.0))
    nb = max(1, int(L / 0.62))
    bl = L / nb
    for k in range(nb):
        p0 = a + t * (k * bl + 0.01)
        p1 = a + t * ((k + 1) * bl - 0.01)
        q = [p0 - o * 0.21, p1 - o * 0.21, p1 + o * 0.21, p0 + o * 0.21]
        mb.face([(v.x, v.y, v.z + 0.015) for v in q], 'concrete_dark')
        for r in (-0.095, 0.095):
            for j in range(6):
                c = p0 + (p1 - p0) * ((j + 0.5) / 6) + o * r
                hx, hy = t2 * 0.035, o * 0.06
                h = [c - hx - hy, c + hx - hy, c + hx + hy, c - hx + hy]
                mb.face([(v.x, v.y, v.z + 0.019) for v in h], 'metal_dark')
    return mb


def _area2(pts):
    """twice the signed area of a polygon's xy (anticlockwise > 0)"""
    return sum(p.x * q.y - q.x * p.y for p, q in zip(pts, pts[1:] + pts[:1]))


def uw_slab(mb, corners, gnd, top, side, walk=False):
    """A solid block standing on the ground: corners [(x, y, z) x 4] of its top, anticlockwise seen from above, straight
    sides down to gnd.  walk: its top is walked on (and the shrubs planted on it stand on it)."""
    corners = list(corners)
    oface(mb, corners, top, (0, 0, 1))
    for a, b in zip(corners, corners[1:] + corners[:1]):
        oface(mb, [(a[0], a[1], gnd), (b[0], b[1], gnd), (b[0], b[1], b[2]), (a[0], a[1], a[2])], side, (b[1] - a[1], a[0] - b[0], 0))
    if walk:
        WALK_FACES.append([tuple(mb.xf @ Vector(c)) for c in corners])


def uw_wall(mb, p0, p1, ztop, gnd, gl, t=0.4, wall='stone_rubble', cap='stone_trim', clear=0.2, n=8):
    """A straight rubble wall t thick from p0 to p1 (x, y), coped with pale stone, its top at ztop(f) (f = 0 .. 1 along
    it) but never less than `clear` over the ground beside it (the 5 m terrain grid can stand a bank above the line
    the wall was drawn to)."""
    p0, p1 = Vector((*p0, 0)), Vector((*p1, 0))
    d = (p1 - p0).normalized()
    o = Vector((-d.y, d.x, 0)) * (t / 2)
    zs = []
    for k in range(n + 1):
        f = k / n
        q = p0.lerp(p1, f)
        zs.append(max(ztop(f), max(gl(*(q + o * 1.6).xy), gl(*(q - o * 1.6).xy), gl(*q.xy)) + clear))
    for k in range(n):
        a, b = p0.lerp(p1, k / n), p0.lerp(p1, (k + 1) / n)
        za, zb = zs[k], zs[k + 1]
        body = [(*(a - o).xy, za - 0.14), (*(b - o).xy, zb - 0.14), (*(b + o).xy, zb - 0.14), (*(a + o).xy, za - 0.14)]
        if (b - a).cross(o).z < 0:
            body = body[::-1]
        uw_slab(mb, body, gnd, wall, wall)
        o2 = o * (1 + 0.1 / t)
        capq = [(*(a - o2).xy, za), (*(b - o2).xy, zb), (*(b + o2).xy, zb), (*(a + o2).xy, za)]
        if (b - a).cross(o).z < 0:
            capq = capq[::-1]
        uw_slab(mb, capq, min(za, zb) - 0.16, cap, cap)


def uw_tablet(mb, cx, cy, cz, slope, hw, hh, th=0.12, tip=14.0):
    """A stone tablet lying on a lawn that rises along +y at `slope` (rad), tipped up a little more (tip degrees)."""
    tilt = slope + math.radians(tip)
    ey, ez = Vector((0, math.cos(tilt), math.sin(tilt))), Vector((0, -math.sin(tilt), math.cos(tilt)))
    C = Vector((cx, cy, cz))
    corner = lambda sx, sy, sz: tuple(C + Vector((sx * hw, 0, 0)) + ey * (sy * hh) + ez * (sz * th))
    for sz in (1, -1):
        oface(mb, [corner(-1, -1, sz), corner(1, -1, sz), corner(1, 1, sz), corner(-1, 1, sz)], 'stone_marker', tuple(ez * sz))
    for (a_, b_) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
        q = [corner(a_[0], a_[1], -1), corner(b_[0], b_[1], -1), corner(b_[0], b_[1], 1), corner(a_[0], a_[1], 1)]
        oface(mb, q, 'stone_marker', tuple(Vector((a_[0] + b_[0], 0, 0)) + ey * (a_[1] + b_[1])))


def uw_block(mb, quad, gnd, top, side, walk=False, step=0.8):
    """Like uw_slab, but the top (a planar quad [(x, y, z) x 4], anticlockwise from above) cut into cells about `step`
    across, so that the baked occlusion of its walled edges does not spread over the whole of a broad landing."""
    q = [Vector(c) for c in quad]
    nu = max(1, int(math.ceil(max((q[1] - q[0]).length, (q[2] - q[3]).length) / step)))
    nv = max(1, int(math.ceil(max((q[3] - q[0]).length, (q[2] - q[1]).length) / step)))
    P = lambda i, j: tuple(q[0].lerp(q[1], i / nu).lerp(q[3].lerp(q[2], i / nu), j / nv))
    for i in range(nu):
        for j in range(nv):
            c = [P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)]
            oface(mb, c, top, (0, 0, 1))
            if walk:
                WALK_FACES.append([tuple(mb.xf @ Vector(v)) for v in c])
    for a, b in zip(quad, quad[1:] + quad[:1]):
        oface(mb, [(a[0], a[1], gnd), (b[0], b[1], gnd), (b[0], b[1], b[2]), (a[0], a[1], a[2])], side, (b[1] - a[1], a[0] - b[0], 0))


def underwood_steps():
    """백양로 끝 계단 (tools/build_campus.py UW_STEPS; 2003_봄_언더우드관정원_남쪽계단_벚나무.jpg, Kakao roadview 2010 -
    2026): from the 삼거리 at the end of 백양로 up the bank to the square before 언더우드관 정원.  Three tiers of two
    granite flights either side of a lawn strip down the axis -- the broad bed with the crest tablet between the
    lowest, narrower above -- with a deep landing and a shorter one between the tiers and a head landing at the top;
    rubble cheek walls with sloping pale copings either side of every flight, square posts at the outer corners of the
    foot and the head, coped walls along the landings' sides (the grass banks beyond them are the terrain's, their
    clipped shrubs the shrubs list).  Laid out in the steps' frame (x across, east; y up the axis from the foot)."""
    U = CAMPUS.get('underwood_steps')
    if not U or 'tiers' not in U:
        return []
    out = []
    ct = U['cheek']
    for f in U['flights']:
        out.append(garden_flight(dict(f, cheek=0.0), apron=False))      # (the cheeks below, posts only outside)
    for f in U.get('garden', []):          # the short walled flight up into 언더우드관 정원 at its south-west corner
        out.append(garden_flight(f))
    F = U['frame']
    mb = MeshBuilder('lm_uw_steps')
    mb.xf = local_frame(F['o'][0], F['o'][1], math.atan2(F['u'][1], F['u'][0]), 0.0)
    gl = local_ground(mb)
    h0, top, tr, rs = U['h0'], U['top'], U['tread'], U['rise']
    gnd = h0 - 1.6
    T = U['tiers']
    hc = 0.55                                            # (the copings' height over the nosings)
    for k, t in enumerate(T):
        v0, v1, z0, z1, sw = t['v0'], t['v1'], t['z0'], t['z1'], t['strip']
        prof = [(v1 + 0.65, z1 + hc), (v1, z1 + hc), (v0 + 0.05, z0 + rs + hc - 0.05), (v0 - 0.25, z0 + hc - 0.05)]
        for sg in (-1, 1):
            for x0, x1, wm in ((sw, sw + ct, 'stone_trim'), (t['outer'] - ct, t['outer'], 'stone_rubble')):
                a_, b_ = sorted((sg * x0, sg * x1))
                sloped_wall(mb, a_, b_, prof, gnd, wm)              # (pale granite beside the strip)
            if k == 0:
                pedestal(mb, sg * (t['outer'] - ct / 2), v0 - 0.15, z0 + hc + 0.3, gnd, 'stone_rubble', w=ct + 0.25)
        # the lawn strip between the inner cheeks, rising with the flights, a tablet on it (the crest on the lowest)
        uw_block(mb, [(-sw, v0 - 0.2, z0 + 0.14), (sw, v0 - 0.2, z0 + 0.14), (sw, v1 + 0.6, z1 + 0.15), (-sw, v1 + 0.6, z1 + 0.15)],
                 gnd, 'grass', 'stone_trim', walk=True)
        sl = math.atan2(z1 - z0 + 0.01, v1 - v0 + 0.8)
        f_ = 0.42
        hw_, hh_ = (0.5, 0.6) if k == 0 else (0.28, 0.38)
        if sw > hw_ + 0.08:
            uw_tablet(mb, 0.0, v0 - 0.2 + (v1 - v0 + 0.8) * f_, z0 + 0.14 + (z1 - z0 + 0.01) * f_ + 0.1, sl, hw_, hh_)
    # the landings: granite, the strip carried on across them as a lawn bed that narrows to the next tier's, coped
    # walls along their outer sides against the banks
    for k, L in enumerate(U['landings']):
        v0, v1, z, ou = L['v0'], L['v1'], L['z'], L['outer']
        zs = z + 0.01                                      # (over the flights' own head landings, not level with them)
        uw_block(mb, [(-ou, v0, zs), (ou, v0, zs), (ou, v1, zs), (-ou, v1, zs)], gnd, 'stone_step', 'stone_rubble', walk=True)
        s0, s1 = L['strip']
        uw_block(mb, [(-s0, v0 + 0.6, z + 0.15), (s0, v0 + 0.6, z + 0.15), (s1, v1, z + 0.15), (-s1, v1, z + 0.15)],
                 gnd, 'grass', 'stone_trim', walk=True)
        last = k == len(U['landings']) - 1
        for sg in (-1, 1):
            uw_wall(mb, (sg * (ou + 0.2), v0 - 0.3), (sg * (ou + 0.2), v1 - (0.0 if last else 0.3)), lambda f: z + 0.5, gnd, gl, t=0.4)
            if last:
                pedestal(mb, sg * (ou + 0.2), v1 - 0.2, z + 0.95, gnd, 'stone_rubble', w=0.6)
        if last:
            uw_tablet(mb, 0.0, (v0 + v1) / 2 + 0.3, z + 0.3, 0.0, 0.26, 0.36, tip=24.0)
    out.append(mb)
    return out


def daewoo_annex():
    """대우관 별관: the same pale stone Gothic, five storeys, end gables on the front."""
    return gothic('daewoo_annex', bld(242897923), (-0.97, 0.24), 5, tower_w=7.0, tower_extra=1.5, ivy=0, wings=True,
                  fh=3.6, wall='stone_white', portal='flat')


# ============================================================================= 대강당 앞 농구장
def basketball_court():
    """The 1997 outdoor basketball court on the terrace before 대강당 (tools/build_campus.py COURT): a 28 x 15 m
    concrete slab with painted lines (FIBA rules of the time: trapezoid lanes, 6.25 m three-point arc) and two hoops
    on steel posts behind the baselines.  No photo found, so a plain standard court."""
    C = CAMPUS.get('statues', {}).get('court')
    if not C:
        return []
    L, W = C['L'], C['W']
    mb = MeshBuilder('lm_court')
    mb.xf = local_frame(C['pos'][0], C['pos'][1], C['rot'], C['h'])
    z = 0.06
    # slab on the terrace behind 백양로's bank (tools/build_campus.py AUD_BANK: at 대강당's forecourt level, the head of
    # the flight up from 백양로); its skirt goes down in mortared rubble under the ground round it
    sk = C.get('skirt', 2.0)
    mb.box((0, 0, (z - sk) / 2), (L + 2.0, W + 2.0, z + sk), 'stone_rubble_warm', mats={'top': 'asphalt'}, skip=('bottom',))
    # the slab's top is walked on (the 'walk_stairs' mesh), 6 cm over the terrace
    W_ = lambda lx, ly: tuple(mb.xf @ Vector((lx, ly, z)))
    WALK_FACES.append([W_(-L / 2 - 1.0, -W / 2 - 1.0), W_(L / 2 + 1.0, -W / 2 - 1.0), W_(L / 2 + 1.0, W / 2 + 1.0),
                       W_(-L / 2 - 1.0, W / 2 + 1.0)])
    lw = 0.05

    def line(x0, y0, x1, y1):
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy) or 1
        ox, oy = -dy / n * lw / 2, dx / n * lw / 2
        mb.face([(x0 + ox, y0 + oy, z + 0.012), (x0 - ox, y0 - oy, z + 0.012), (x1 - ox, y1 - oy, z + 0.012), (x1 + ox, y1 + oy, z + 0.012)], 'paint_white')

    def arc(cx, cy, r, a0, a1, seg=24):
        pts = [(cx + r * math.cos(a0 + (a1 - a0) * k / seg), cy + r * math.sin(a0 + (a1 - a0) * k / seg)) for k in range(seg + 1)]
        for p, q in zip(pts, pts[1:]):
            line(p[0], p[1], q[0], q[1])

    hl, hw = L / 2, W / 2
    for (x0, y0, x1, y1) in ((-hl, -hw, hl, -hw), (hl, -hw, hl, hw), (hl, hw, -hl, hw), (-hl, hw, -hl, -hw), (0, -hw, 0, hw)):
        line(x0, y0, x1, y1)
    arc(0, 0, 1.8, 0, 2 * math.pi, 32)
    for sg in (-1, 1):
        bx = sg * hl                               # baseline
        ft = bx - sg * 5.8                         # free-throw line
        # trapezoid lane: 6.0 m wide at the baseline, 3.6 m at the free-throw line
        line(bx, -3.0, ft, -1.8); line(bx, 3.0, ft, 1.8); line(ft, -1.8, ft, 1.8)
        arc(ft, 0, 1.8, -math.pi / 2, math.pi / 2, 16) if sg < 0 else arc(ft, 0, 1.8, math.pi / 2, 3 * math.pi / 2, 16)
        # three-point line: 6.25 m arc round the basket (1.575 m in from the baseline)
        hx = bx - sg * 1.575
        a = math.asin(min(1.0, (hw - 0.9) / 6.25))
        if sg < 0:
            arc(hx, 0, 6.25, -a, a, 28)
        else:
            arc(hx, 0, 6.25, math.pi - a, math.pi + a, 28)
        for yy in (-1, 1):                        # the straight bits down to the baseline
            ex = hx + (-sg) * 6.25 * math.cos(a)
            line(bx, yy * 6.25 * math.sin(a), ex, yy * 6.25 * math.sin(a))
        # hoop: post 1 m behind the baseline, arm out to the backboard 1.2 m inside it, rim at 3.05 m
        px = bx + sg * 1.0
        mb.cylinder((px, 0), 0.09, z, 3.6, 'metal_dark', seg=10)
        mb.box((px - sg * 1.1, 0, 3.45), (2.2, 0.14, 0.14), 'metal_dark')
        mb.box((bx - sg * 1.2 + sg * 0.03, 0, 3.4), (0.05, 1.8, 1.05), 'paint_white')
        mb.box((bx - sg * 1.2 - sg * 0.002, 0, 3.25), (0.01, 0.59, 0.45), 'metal_dark', skip=('bottom', 'top'))
        rc = bx - sg * 1.575
        # rim: an orange steel ring (18 straight pieces of 2 cm tube) 45 cm across at 3.05 m, bolted to the board by a bracket
        seg, rr = 18, 0.225
        for k in range(seg):
            a0 = 2 * math.pi * (k + 0.5) / seg
            mb.box((rc + rr * math.cos(a0), rr * math.sin(a0), 3.05), (0.03, 2 * math.pi * rr / seg * 1.05, 0.03), 'banner_orange',
                   rotz=a0)
        bkx = bx - sg * 1.2
        mb.box(((bkx + rc + sg * rr) / 2 if False else (bkx + (rc + sg * rr)) / 2, 0, 3.05), (abs(bkx - (rc + sg * rr)) + 0.02, 0.12, 0.03), 'banner_orange')
        mb.box((bkx - sg * 0.02, 0, 3.05), (0.04, 0.45, 0.05), 'metal_dark')
        # white net: 12 strings from the rim down to a narrower ring 40 cm below
        for k in range(12):
            a0 = 2 * math.pi * k / 12
            a1 = a0 + math.pi / 12
            top = (rc + rr * math.cos(a0), rr * math.sin(a0), 3.05)
            bot = (rc + 0.13 * math.cos(a1), 0.13 * math.sin(a1), 2.65)
            top2 = (rc + rr * math.cos(a0 + math.pi / 6), rr * math.sin(a0 + math.pi / 6), 3.05)
            for (u, v) in ((top, bot), (top2, bot)):
                dx, dy = -(v[1] - u[1]) * 0.0 + 0.007, 0.007
                q = [(u[0] - dx, u[1] - dy, u[2]), (u[0] + dx, u[1] + dy, u[2]), (v[0] + dx, v[1] + dy, v[2]), (v[0] - dx, v[1] - dy, v[2])]
                mb.face(q, 'paint_white')
                mb.face(q[::-1], 'paint_white')
        for zz, rn in ((2.9, 0.19), (2.77, 0.16)):          # cross-strings
            pts = [(rc + rn * math.cos(2 * math.pi * k / 12), rn * math.sin(2 * math.pi * k / 12), zz) for k in range(13)]
            for u, v in zip(pts, pts[1:]):
                q = [(u[0], u[1], zz - 0.008), (v[0], v[1], zz - 0.008), (v[0], v[1], zz + 0.008), (u[0], u[1], zz + 0.008)]
                mb.face(q, 'paint_white')
                mb.face(q[::-1], 'paint_white')
    return [mb]


def parking_lines():
    """The car parks' painted bays (tools/build_campus.py PARK_LOTS: campus.json `parking`, each lot's lines as
    [x0, y0, x1, y1] and its paint): a strip of the line's width cut every half metre and laid 3 cm over the ground the
    web app draws (ground_top), so that on a sloping car park it neither floats nor sinks.  One mesh for all, a draw call
    per paint."""
    mb = MeshBuilder('lm_parking_lines')
    mats = {'white': 'paint_white', 'yellow': 'paint_yellow'}
    for lot in CAMPUS.get('parking', []):
        mat = mats.get(lot.get('paint'))
        if not mat:
            continue
        hw = lot.get('w', 0.12) / 2
        for x0, y0, x1, y1 in lot['lines']:
            L = math.hypot(x1 - x0, y1 - y0)
            if L < 0.05:
                continue
            dx, dy = (x1 - x0) / L, (y1 - y0) / L
            nx, ny = -dy * hw, dx * hw                     # (half the width, to the left)
            n = max(1, int(math.ceil(L / 0.5)))
            pts = [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n + 1)]
            zs = [ground_top(x, y) + 0.03 for x, y in pts]
            for (xa, ya), (xb, yb), za, zb in zip(pts, pts[1:], zs, zs[1:]):
                mb.quad((xa - nx, ya - ny, za), (xb - nx, yb - ny, zb), (xb + nx, yb + ny, zb), (xa + nx, ya + ny, za), mat)
    return [mb] if mb.faces else []


def aud_bank():
    """The rubble wall along 백양로's east sidewalk in front of 대강당 and the bank of shrubs behind it, up to the
    terrace of the court and the forecourt (tools/build_campus.py AUD_BANK; Kakao roadview 2008 · 2011,
    reference/대강당_2009_앞길_계단.jpg).  Mortared granite rubble about 0.7 m high with a flat top, the bank's slope and
    the terrace's edge beyond it drawn in the terrain's own material ('terrain_drape': web/src/terrain.js
    drapeTerrain), so the woods' floor under the shrubs and the lawn at the top are the ground's; walked on (the
    'walk_stairs' mesh), the shrubs and the ginkgo row stand on it.  One section a metre: s, the wall face's foot
    (x, y), the heading into the bank, the sidewalk, the wall top, the bank's top, the ground beyond at the top edge,
    halfway and out, the bank's depth and how far out the ground beyond is drawn: 7 and 12.55 m behind the wall,
    less in the wedge between the wall and the drive up to the terrace (its west kerb).  The flight up to the
    forecourt (aud_flight) stands in a gap in it, B['gap']: the wall and the bank end there against its side walls."""
    B = CAMPUS.get('aud_bank')
    if not B or B.get('side', -1) != -1:          # (laid out for the east side: the bank to the right going along)
        return []
    gA, gB = B.get('gap', (1e9, 1e9))
    mb = MeshBuilder('lm_aud_bank')
    cap, top_o, ext_o = B['cap'], B['top'], B['ext']
    secs = []
    for sec in B['sections']:
        s, x, y, ang, zb, top, tp, f1, f2, f3 = sec[:10]
        # the bank's depth and how far out the ground beyond is drawn: 7 / 12.55 m, less in the wedge by the drive
        to, ex = (sec[10], sec[11]) if len(sec) > 11 else (top_o, ext_o)
        mo = (to + ex) / 2
        OS = [cap + (to - cap) * k / 6 for k in range(7)]           # the slope, then the terrace's edge
        n = (math.cos(ang), math.sin(ang))
        f_at = lambda o, to=to, mo=mo, ex=ex, f1=f1, f2=f2, f3=f3: \
            (f1 + (f2 - f1) * (o - to) / (mo - to)) if o <= mo else (f2 + (f3 - f2) * (o - mo) / (ex - mo))
        bz = lambda o, to=to: (lambda t_: top + (tp - top) * t_ * t_ * (3 - 2 * t_))(min(1.0, max(0.0, (o - cap) / (to - cap))))
        prof = [(o, bz(o) + 0.04 * (o - cap) / (to - cap)) for o in OS] + \
               [(o, f_at(o)) for o in (to + 0.26 * (ex - to), mo, ex)]
        secs.append(dict(s=s, P=lambda o, z, x=x, y=y, n=n: (x + n[0] * o, y + n[1] * o, z), zb=zb, top=top, prof=prof))
    BATTER = 0.05                                                 # the wall leans back a little
    for a, b in zip(secs[:-1], secs[1:]):
        if a['s'] <= gA + 1e-3 and b['s'] >= gB - 1e-3:
            continue                                              # (the flight)
        # the wall's face (towards the road), its flat top, the bank and the terrace's edge
        mb.face([a['P'](BATTER, a['top']), b['P'](BATTER, b['top']), b['P'](0.0, b['zb'] - 0.35), a['P'](0.0, a['zb'] - 0.35)],
                'stone_rubble_warm')
        mb.face([a['P'](BATTER, a['top']), a['P'](cap, a['top']), b['P'](cap, b['top']), b['P'](BATTER, b['top'])], 'curb')
        for (o0, z0a), (o1, z1a), (_, z0b), (_, z1b) in zip(a['prof'][:-1], a['prof'][1:], b['prof'][:-1], b['prof'][1:]):
            q = [a['P'](o0, z0a), a['P'](o1, z1a), b['P'](o1, z1b), b['P'](o0, z0b)]
            mb.face(q, 'terrain_drape')
            WALK_FACES.append(q)
    # its two ends: the wall's end in rubble; the bank runs out 3 m beyond it down to the ground, its toe 3 cm over it
    TOE = 3.0
    for sec, first in ((secs[0], True), (secs[-1], False)):
        P, lo = sec['P'], sec['zb'] - 0.35
        wall = [P(0.0, lo), P(cap, lo), P(cap, sec['top']), P(BATTER, sec['top'])]
        mb.face(wall if first else wall[::-1], 'stone_rubble_warm')
        x0, y0, _ = P(0.0, 0.0)
        nx, ny = (P(1.0, 0.0)[0] - x0), (P(1.0, 0.0)[1] - y0)
        tx, ty = (-ny, nx) if not first else (ny, -nx)            # along the road, away from the wall
        toe = lambda o, z: (lambda x, y: (x, y, min(z, ground_top(x, y) + 0.03)))(x0 + nx * o + tx * TOE, y0 + ny * o + ty * TOE)
        for (o0, z0), (o1, z1) in zip(sec['prof'][:-1], sec['prof'][1:]):
            q = [P(o0, z0), P(o1, z1), toe(o1, z1), toe(o0, z0)]
            mb.face(q[::-1] if first else q, 'terrain_drape')
            WALK_FACES.append(q)
        # under the bank's first metre the toe meets the wall's end: close the gap down to the ground
        o0, z0 = sec['prof'][0]
        q = [P(o0, z0), toe(o0, z0), (toe(o0, z0)[0], toe(o0, z0)[1], lo), P(o0, lo)]
        mb.face(q[::-1] if first else q, 'stone_rubble_warm')             # (facing the road)
    # at the flight: the wall and the bank closed in rubble, inside its side walls (they stand 5 cm further out)
    for sec in secs:
        if abs(sec['s'] - gA) > 1e-3 and abs(sec['s'] - gB) > 1e-3:
            continue
        P, lo, south = sec['P'], sec['zb'] - 0.35, abs(sec['s'] - gB) < 1e-3
        qs = [[P(0.0, lo), P(cap, lo), P(cap, sec['top']), P(BATTER, sec['top'])]]
        qs += [[P(o0, lo), P(o1, lo), P(o1, z1), P(o0, z0)] for (o0, z0), (o1, z1) in zip(sec['prof'][:-1], sec['prof'][1:])]
        for q in qs:
            mb.face(q if south else q[::-1], 'stone_rubble_warm')
    return [mb] + aud_flight()


def aud_flight():
    """The straight granite flight from 백양로's east sidewalk up to 대강당's forecourt, on the hall's axis, through the
    rubble wall and the bank (tools/build_campus.py AUD_FLIGHT; reference/대강당_2009_앞길_계단.jpg, Kakao roadview
    Aug. 2008 2381313 · Dec. 2010 1016786027 · 028 · Apr. 2011 1017220198 · 199).  24 risers of about 15 cm: eleven
    treads of 0.27 m, a landing of 1.4 m (the 12th tread) where the slope changes, eleven steeper treads of 0.215 m to
    the head.  Between side walls of mortared granite rubble under a pale granite coping that follows the flight, turns
    level over the landing for a block and over the head for one more; at the foot square granite posts in line with
    the wall's face, letters cut down their road faces.  The foot from the wall's face to the first riser is paved.
    Local frame: x up the flight from the wall's face, y across it (north +), z over the sidewalk."""
    F = CAMPUS.get('aud_flight')
    if not F:
        return []
    ax, ay = F['axis']
    mb = MeshBuilder('lm_aud_flight')
    mb.xf = local_frame(F['o'][0], F['o'][1], math.atan2(ay, ax), F['foot_z'])
    W_ = lambda lx, ly, lz: tuple(mb.xf @ Vector((lx, ly, lz)))
    hw, ch, n1, n2 = F['w'] / 2, F['cheek'], F['n1'], F['n2']
    n = n1 + n2
    r = F['rise'] / n
    xs = [F['foot']]                                  # the nosings, 1 .. n
    for i in range(1, n):
        xs.append(xs[-1] + (F['t1'] if i < n1 else F['landing'] if i == n1 else F['t2']))
    x_top = xs[-1] + 0.35                             # the head's stone, then the forecourt
    cuts = [-hw, -hw + 0.45, hw - 0.45, hw]           # (tops and fronts in three across: the bake reads corners)

    def across_(x0, x1, z0, z1, up):
        for y_a, y_b in zip(cuts, cuts[1:]):
            if up:
                mb.quad((x0, y_a, z0), (x1, y_a, z0), (x1, y_b, z0), (x0, y_b, z0), 'stone_granite')
            else:
                mb.quad((x0, y_b, z0), (x0, y_a, z0), (x0, y_a, z1), (x0, y_b, z1), 'stone_granite')
    across_(0.0, xs[0], 0.0, 0.0, True)               # (the foot, paved as the sidewalk's granite edge)
    for i in range(1, n + 1):
        x0 = xs[i - 1]
        x1 = xs[i] if i < n else x_top
        across_(x0, x0, (i - 1) * r, i * r, False)    # the riser
        across_(x0, x1, i * r, i * r, True)           # the tread
    # under the treads, down to the ground below the sidewalk (the 5 m grid is kept under it, build_campus)
    base = -0.6
    mb.quad((0.0, -hw, base), (0.0, hw, base), (x_top, hw, base), (x_top, -hw, base), 'stone_rubble_warm')
    mb.quad((x_top, -hw, base), (x_top, hw, base), (x_top, hw, F['rise']), (x_top, -hw, F['rise']), 'stone_rubble_warm')
    # the side walls: their coping from the posts' caps up the lower flight, level over the landing, up the upper
    # flight and level over the head (0.68 m over the landing's nosing, as from in front in Dec. 2010)
    hc, wp, post_top = 0.68, 0.46, 0.80
    k = n1 - 1
    prof = [(wp, post_top), (xs[k], (k + 1) * r + hc), (xs[k + 1] - 0.05, (k + 1) * r + hc),
            (xs[k + 1] - 0.05, (k + 2) * r + hc), (xs[-1], n * r + hc), (x_top + 0.6, n * r + hc)]
    sx, tops = [], []
    for (xa, za), (xb, zb) in zip(prof[:-1], prof[1:]):
        m = max(1, int(math.ceil((xb - xa) / 0.9)))
        for j in range(m):
            sx.append(xa + (xb - xa) * j / m)
            tops.append(za + (zb - za) * j / m)
    sx.append(prof[-1][0]); tops.append(prof[-1][1])
    for j in range(len(sx) - 1, 0, -1):               # (the step up at the landing's end: a vertical joint)
        if sx[j] - sx[j - 1] < 1e-6:
            sx[j] += 0.002
    for ya, yb in ((-hw - ch, -hw), (hw, hw + ch)):
        profile_wall(mb, ya, yb, sx, tops, [base] * len(sx), 'stone_rubble_warm', cap='stone_trim', ct=0.2)
    # the posts at the foot: square granite, a flat cap, letters down the face towards the road
    rnd = random.Random(1958)
    for yc in (-hw - ch / 2, hw + ch / 2):
        mb.box((wp / 2, yc, (base + post_top - 0.08) / 2), (wp, wp, post_top - 0.08 - base), 'stone_trim', skip=('bottom',))
        mb.box((wp / 2, yc, post_top - 0.04), (wp + 0.06, wp + 0.06, 0.08), 'stone_trim', skip=('bottom',))
        z = post_top - 0.2
        while z > 0.12:
            h_ = rnd.uniform(0.04, 0.07)
            mb.quad((-0.003, yc + 0.03, z - h_), (-0.003, yc - 0.03, z - h_), (-0.003, yc - 0.03, z), (-0.003, yc + 0.03, z),
                    'concrete_dark')
            z -= h_ + 0.035
    # beyond the head the forecourt's edge in the ground's own material (painted as its asphalt), over the 5 m grid
    # kept under the flight; as the bank's terrace edge either side of it (aud_bank)
    f1, f2, f3 = (v - F['foot_z'] for v in F['far'])
    yb_ = hw + ch - 0.05
    edge = [(x_top, F['rise'])] + [(x_, z_) for x_, z_ in ((7.0, f1), (9.775, f2), (12.55, f3)) if x_ > x_top + 0.3]
    for (x0, z0), (x1, z1) in zip(edge[:-1], edge[1:]):
        q = [(x0, -yb_, z0), (x1, -yb_, z1), (x1, yb_, z1), (x0, yb_, z0)]
        mb.face(q, 'terrain_drape')
        WALK_FACES.append([W_(*p) for p in q])
    # walked on: the foot, one ramp up each flight through the nosings, the landing, the head
    walk = [(0.0, 0.0), (xs[0], 0.0), (xs[k], (k + 1) * r), (xs[k + 1], (k + 1) * r), (xs[-1], n * r), (x_top, n * r)]
    for (x0, z0), (x1, z1) in zip(walk[:-1], walk[1:]):
        WALK_FACES.append([W_(x0, -hw, z0), W_(x1, -hw, z1), W_(x1, hw, z1), W_(x0, hw, z0)])
    # the zone over the flight (the web app keeps shrubs off it)
    o = mb.xf @ Vector((-0.5, 0.0, 0.0))
    u = (mb.xf.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    v = (mb.xf.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
    ENTRANCES.append(dict(o=[round(o.x, 2), round(o.y, 2)], u=[round(u.x, 4), round(u.y, 4)], v=[round(v.x, 4), round(v.y, 4)],
                          hw=round(hw + ch + 0.6, 2), len=round(x_top + 1.5, 2)))
    print('대강당 앞 돌계단: %d risers of %.3f m, landing %.2f m, head %.2f m out of the wall'
          % (n, r, F['landing'], xs[-1]))
    return [mb]


# ============================================================================= 활천대 (독수리상 옆)
# The basin before 백양로 was rebuilt (reference/고증.md 4.3): the old photo in the 2017 blog post (reference/
# 활천대_공사전_연세대블로그.jpg) and a group snapshot of about late 1999 - the early 2000s
# (reference/활천대_단체사진_*.jpg).  One round pool 8.9 m across,
# walled in rounded field stones laid in mortar with a rounded top a little lighter than the faces, the water a few
# centimetres over the ground outside and some 15 cm under the wall's top; a ring of rough flagstones 1.1 m wide round
# the wall; in the middle a low round island of the same stones carrying the sculpture.  (The thin metal ring of jets
# in the water, 6.5 m across, and its bell of water in the 2009 photo came later: none on the rim in 1997.)  Sizes:
# tools/build_campus.py FOUNTAIN, from the old photo's camera (the rings and the column, 4 px rms) and the 2011
# roadview (the column 2.29 / 2.34 m, slab top to the tips, from two solved spots).
# The sculpture, from the old photo, the snapshot and the 2017 photos of it (reference/활천대_2017_연세대블로그_*.jpg;
# the name plate reads 「활천대 기증 전기공학과 동창회 (1974년)」): a stone column of cross section, carved all over with
# abstract figures in low relief, in three drums with a dark joint between them and its four arms ending above in
# upright prongs of different heights; it stands on a square slab with a carved edge, on a lower cross-shaped pedestal
# (letters cut in its faces).  In the old photo the column is 4.14 times narrower than the wall across, its drums
# 0.65 / 0.73 / 0.91 m (with the prongs) and the slab 0.25 m thick on a pedestal 0.66 m high; seen square on (2017)
# the arms span 0.38 and the slab 0.47 of the column's height.  In the snapshot its white stone had gone grey
# with dark streaks (stone_white_old).  A jet rises from its top and falls back round it (there in 1997 too, the
# user remembers; its shape from the 2009 photo).
FOUNTAIN_COL = dict(ped=0.79, slab=1.04, j2=1.69, j1=2.42, top=3.04, tip=0.29, arm=0.43, arm_w=0.27, core=0.23,
                    slab_w=1.08, ped_l=0.74, ped_w=0.33)          # z over the flagstones; web/src/water/fountain.js
FOUNTAIN_CURTAIN = 1.05                                           # where the jet's fall meets the water (web too)


def _relief(mb, c, n, t, w, z0, z1, rnd, mat, depth=0.05):
    """carved low relief on a vertical face: c its centre line foot (x, y), n the outward normal, t the face's own
    horizontal direction, w its width; little blocks and ribs standing a few cm proud, like the 활천대 figures"""
    for _ in range(int(w * (z1 - z0) * 14)):
        u = rnd.uniform(-w / 2 + 0.03, w / 2 - 0.03)
        z = rnd.uniform(z0 + 0.04, z1 - 0.04)
        bw, bh = rnd.uniform(0.03, 0.11), rnd.uniform(0.04, 0.24)
        d = depth * rnd.uniform(0.4, 1.0)
        x, y = c[0] + t[0] * u + n[0] * d / 2, c[1] + t[1] * u + n[1] * d / 2
        mb.box((x, y, z), (bw, d, bh), mat, rotz=math.atan2(t[1], t[0]), skip=('bottom', 'back'))


def _lathe(mb, prof, mats, seg, tag, jit=None, a0=0.0, planar=False):
    """A surface of revolution round the local z axis: prof a list of (radius, z) and mats one material per band
    (prof[i] -> prof[i + 1]).  Ordered so that the side to be seen is on the left going along the profile seen from
    outside (outer face upwards, a top inwards, an inner face downwards).  jit(k, i) -> (dr, dz) roughens point i at
    the k-th of seg angles.  UVs in metres: round the ring by the arc, across it by the length along the profile
    (planar: x, y, for a flat ring)."""
    run = [0.0]
    for (ra, za), (rb, zb) in zip(prof, prof[1:]):
        run.append(run[-1] + math.hypot(rb - ra, zb - za))

    def P(k, i):
        a = a0 + 2 * math.pi * (k % seg) / seg
        dr, dz = jit(k % seg, i) if jit else (0.0, 0.0)
        r, z = prof[i][0] + dr, prof[i][1] + dz
        return (r * math.cos(a), r * math.sin(a), z)
    for k in range(seg):
        for i in range(len(prof) - 1):
            ra, rb = prof[i][0], prof[i + 1][0]
            u0a, u1a = 2 * math.pi * ra * k / seg, 2 * math.pi * ra * (k + 1) / seg
            u0b, u1b = 2 * math.pi * rb * k / seg, 2 * math.pi * rb * (k + 1) / seg
            q = [P(k, i), P(k + 1, i), P(k + 1, i + 1), P(k, i + 1)]
            uv = [(p_[0], p_[1]) for p_ in q] if planar else \
                [(u0a, run[i]), (u1a, run[i]), (u1b, run[i + 1]), (u0b, run[i + 1])]
            mb.face(q, mats[i], uvs=uv, smooth=tag)


def fountain():
    """활천대 (活泉臺, 1974): the electrical engineering alumni's fountain beside the eagle (see FOUNTAIN_COL)."""
    F = CAMPUS.get('statues', {}).get('fountain')
    if not F:
        return []
    r, R, pave = F['r'], F['rim'], F['pave']
    wall, water, floor, isl, isle = F['wall'], F['water'], F['floor'], F['island'], F['isle']
    rnd = random.Random(1974)
    mb = MeshBuilder('lm_fountain')
    mb.xf = local_frame(F['pos'][0], F['pos'][1], F.get('rot', 0.0), F['h'])      # z = 0: the flagstones (level ground)
    face_m, top_m, flag_m = 'stone_rubble_brown', 'stone_rubble_gray', 'stone_rubble'
    # the wall: an outer face from under the ground, a rounded top of lighter stones, the inner face down to the floor;
    # its stones uneven along the top, a lump every 15 - 25 cm
    seg = 160
    bumps = []
    while len(bumps) < seg:
        n_, dr, dz = rnd.randint(1, 2), rnd.uniform(-0.02, 0.02), rnd.uniform(-0.035, 0.02)
        bumps += [(dr, dz)] + [(dr * 0.5, dz * 0.4 - 0.012)] * n_
    bumps = bumps[:seg]
    cz, ch, cw = wall - 0.07, 0.07, (R - r) / 2
    cap = [((R + r) / 2 + cw * math.cos(t), cz + ch * math.sin(t)) for t in (math.pi * j / 5 for j in range(6))]
    prof = [(R, -0.35), (R + 0.01, cz - 0.03)] + cap + [(r - 0.01, cz - 0.03), (r, floor)]
    mats = [face_m, face_m] + [top_m] * (len(cap) - 1) + [face_m, face_m]
    nprof = len(prof)
    _lathe(mb, prof, mats, seg, 'fw_wall', jit=lambda k, i: bumps[k] if 1 <= i <= nprof - 2 else (0.0, 0.0))
    mb.cylinder((0, 0), r, floor - 0.05, floor, 'concrete_dark', seg=seg)          # the floor (drawn by the water's shader)
    # the flagstones: a flat ring round the wall, its outer edge ragged where the stones meet the lawn
    ring_seg = 96
    edge = [pave + rnd.uniform(-0.09, 0.07) for _ in range(ring_seg)]
    _lathe(mb, [(pave, 0.02), (R - 0.02, 0.02)], [flag_m], ring_seg, False,
           jit=lambda k, i: (edge[k] - pave, 0.0) if i == 0 else (0.0, 0.0), planar=True)
    _lathe(mb, [(pave, -0.12), (pave, 0.02)], [flag_m], ring_seg, False,          # (its edge into the turf)
           jit=lambda k, i: (edge[k] - pave, 0.0))
    # the island: the same stones, a low drum a few centimetres over the water with a rounded edge
    ib = [(rnd.uniform(-0.01, 0.01), rnd.uniform(-0.012, 0.012)) for _ in range(48)]
    _lathe(mb, [(isl, floor), (isl, isle - 0.05)] + [(isl - 0.05 + 0.05 * math.cos(t), isle - 0.05 + 0.05 * math.sin(t))
                                                      for t in (math.pi / 6 * j for j in range(4))][1:] + [(0.0, isle)],
           [face_m, top_m, top_m, top_m, top_m], 48, 'fw_isle', jit=lambda k, i: ib[k] if i in (1, 2, 3) else (0.0, 0.0))
    # the water surface (level `water`) is drawn live in the web app: web/src/water/fountain.js (Ultra Water)
    C = FOUNTAIN_COL
    stone = 'stone_white_old'
    # lower pedestal: a cross of two slabs, letters cut in its faces
    for ang in (0.0, math.pi / 2):
        mb.box((0, 0, (isle + C['ped']) / 2), (C['ped_l'], C['ped_w'], C['ped'] - isle + 0.02), stone, rotz=ang)
    for k in range(4):
        a = k * math.pi / 2
        n_, t_ = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        _relief(mb, (n_[0] * C['ped_l'] / 2, n_[1] * C['ped_l'] / 2), n_, t_, C['ped_w'], isle + 0.08, C['ped'] - 0.06, rnd,
                stone, 0.025)
    # the square slab with a carved (wavy) edge
    sw = C['slab_w']
    mb.box((0, 0, (C['ped'] + C['slab']) / 2), (sw, sw, C['slab'] - C['ped']), stone)
    for k in range(4):
        a = k * math.pi / 2
        n_, t_ = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        for j in range(9):
            u = -sw * 0.43 + j * sw * 0.86 / 8
            x, y = n_[0] * sw / 2 + t_[0] * u, n_[1] * sw / 2 + t_[1] * u
            mb.box((x, y, C['ped'] + 0.05 + 0.13 * (j % 2)), (0.08, 0.03, 0.08), stone, rotz=a + math.pi / 2, skip=('back',))
    # the column: a core and four arms, in three drums with dark joints
    jt = 0.015
    drums = [(C['slab'], C['j2'] - jt), (C['j2'] + jt, C['j1'] - jt), (C['j1'] + jt, C['top'])]
    for z0, z1 in drums:
        mb.box((0, 0, (z0 + z1) / 2), (C['core'] * 2, C['core'] * 2, z1 - z0), stone)
        for ang in (0.0, math.pi / 2):
            mb.box((0, 0, (z0 + z1) / 2), (C['arm'] * 2, C['arm_w'], z1 - z0), stone, rotz=ang)
        for k in range(4):
            a = k * math.pi / 2
            n_, t_ = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
            _relief(mb, (n_[0] * C['arm'], n_[1] * C['arm']), n_, t_, C['arm_w'], z0, z1, rnd, stone, 0.04)
            for sd in (-1, 1):          # the arm's two side faces and the core's corner faces between the arms
                o = (n_[0] * (C['core'] + (C['arm'] - C['core']) / 2) + t_[0] * sd * C['arm_w'] / 2,
                     n_[1] * (C['core'] + (C['arm'] - C['core']) / 2) + t_[1] * sd * C['arm_w'] / 2)
                _relief(mb, o, (t_[0] * sd, t_[1] * sd), n_, C['arm'] - C['core'], z0, z1, rnd, stone, 0.04)
    for z0, z1 in zip([d[1] for d in drums[:-1]], [d[0] for d in drums[1:]]):            # the dark joints
        mb.box((0, 0, (z0 + z1) / 2), (C['arm'] * 2 - 0.05, C['arm_w'] - 0.05, z1 - z0 + 0.01), 'concrete_dark')
        mb.box((0, 0, (z0 + z1) / 2), (C['arm_w'] - 0.05, C['arm'] * 2 - 0.05, z1 - z0 + 0.01), 'concrete_dark')
    # the prongs: each arm ends above in two upright blades of different heights
    for k in range(4):
        a = k * math.pi / 2
        n_, t_ = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        for j, (off, h) in enumerate(((-0.07, rnd.uniform(0.6, 1.0) * C['tip']), (0.07, rnd.uniform(0.25, 0.65) * C['tip']))):
            dd = C['arm'] - 0.1
            mb.box((n_[0] * dd + t_[0] * off, n_[1] * dd + t_[1] * off, C['top'] + h / 2), (0.16, 0.12, h), stone,
                   rotz=a, skip=('bottom',))
    mb.cylinder((0, 0), 0.06, C['top'], C['top'] + 0.1, 'metal_dark', seg=8)          # the jet's nozzle
    sp = MeshBuilder('lm_fountain_spray')
    sp.xf = mb.xf
    sp.cylinder((0, 0), 0.12, C['top'] + 0.08, C['top'] + 2.3, 'water_spray', seg=12, r1=0.04)   # the central jet
    # falling back over the column, round the island into the pool
    sp.cylinder((0, 0), FOUNTAIN_CURTAIN, water - 0.02, C['top'] + 0.45, 'water_spray', seg=24, r1=0.2, cap_top=False)
    return [mb, sp]


# ============================================================================= 용재관 (demolished)
def yongjae():
    """용재관 (1957 - 2013), white painted concrete, from reference/용재관.jpg (April, 1990s, from 언더우드관 over the
    Underwood statue: the tower's fin face running off to the right, its north side to the lens, the wing on the left
    with the canopy at its foot), the mid-1950s photo of the first library building (slc.bc.ca/yonsei: the fin face
    square on, the V reliefs of its crown, the wing's groups of three tall lights, the gabled block behind, the lower
    hipped block beyond the tower) and the 1994 / 1997 aerial photos (the tower over the south block's roof).
    - the stair tower, six storeys of 3.6 m: on its fin face (to 백양로) two narrow bays of tall steel windows, one a
      floor for five floors over a sunk panel, between three slim fins, broad blank bays either side, the top floor a
      blank crown with a V in each window bay, a thin roof slab standing out all round, a penthouse and a mast;
      on its north and south sides two columns of small windows near the fin face, two a floor
    - the north wing, three storeys under a dark hipped roof, 2.8 m back from the fin face: four bays of three tall
      lights between pilasters on its 백양로 front, a chimney box over its north end
    - the entrance in the corner: a one-storey porch with the notice board on its 백양로 side and the glass doors on
      its north side, under a flat canopy on one slim post, air-conditioner units on top; a flight down the bank
    - behind: a five-storey gabled block east of the wing, a four-storey link, a three-storey block south of the
      tower under a pale hipped roof (in the photo right of the fin face).  Footprints, floor and ground:
      tools/build_campus.py YONGJAE."""
    parts = {b['id']: b for b in CAMPUS['buildings'] if b['name'] == '용재관'}
    f = parts[990001]['frame']
    (ox, oy), a = f['o'], f['ang']
    ca, sa = math.cos(a), math.sin(a)
    U = lambda u, v, z: (ox + u * ca - v * sa, oy + u * sa + v * ca, z)
    z0 = parts[990001]['base']
    fh = parts[990001]['height'] / parts[990001]['levels']
    st = dict(generic.STYLE['white'], bay=3.4)
    rnd = random.Random(1997)
    Wm = 'plaster_white'
    out = []

    def plane(ua, va, ub, vb):
        """The wall plane along (ua, va) -> (ub, vb) of a counter-clockwise outline: P(s, z, d), d outwards."""
        L = math.hypot(ub - ua, vb - va)
        tu, tv = (ub - ua) / L, (vb - va) / L
        return (lambda s, z, d=0.0: U(ua + tu * s + tv * d, va + tv * s - tu * d, z)), L

    def outline(uv):
        u0, u1, v0, v1 = uv
        return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]

    def world2(uv):
        return [U(u, v, 0)[:2] for u, v in outline(uv)]

    def box(mb, u, v, z, su, sv, sz, mat, **kw):
        mb.box(U(u, v, z), (su, sv, sz), mat, rotz=a, **kw)

    def window(mb, P, w0, w1, zs, zh, d, cols, rows, sill=True):
        """A steel-framed window [w0, w1] x [zs, zh] in the wall P (its hole already left), d deep."""
        reveal(mb, P, w0, w1, zs, zh, d, Wm)
        glazing(mb, P, w0, w1, zs, zh, -d, cols, rows, 'frame_dark', fw=0.045)
        if sill:
            bar(mb, P, w0 - 0.08, zs - 0.05, w1 + 0.08, zs - 0.05, 0.1, -0.02, 0.1, Wm, ends=True)

    def simple_walls(mb, uv, nfl, z1, skip=()):
        pts = world2(uv)
        for i in range(4):
            if i not in skip:
                generic.wall_edge(mb, pts[i], pts[(i + 1) % 4], z0, z1, nfl, fh, st, rnd)

    # ------------------------------------------------------------------ the stair tower
    T = parts[990001]['frame']['uv']
    u0, u1, v0, v1 = T
    mb = MeshBuilder('lm_yongjae_tower')
    zr = z0 + 6 * fh                    # roof
    zp = zr + 0.85                      # top of the walls, under the roof slab
    Pw, Lw = plane(u0, v1, u0, v0)      # the fin face, s from its north corner
    Pn, Ln = plane(u1, v1, u0, v1)      # north side, s from the east
    Ps, Ls = plane(u0, v0, u1, v0)      # south side, s from the fin face
    Pe, Le = plane(u1, v0, u1, v1)
    for P, L in ((Pw, Lw), (Pn, Ln), (Ps, Ls), (Pe, Le)):
        flat_wall(mb, P, 0, L, z0 - 4.0, z0, 'concrete_dark')
    # fin face: blank bay 3.0 | windows 2.8 | windows 2.8 | blank bay 3.0, the window bays 0.1 back
    fins, rec = (3.0, 5.8, 8.6), 0.1
    flat_wall(mb, Pw, 0.0, fins[0], z0, zp, Wm)
    flat_wall(mb, Pw, fins[2], Lw, z0, zp, Wm)
    Pr = lambda s, z, d=0.0: Pw(s, z, d - rec)
    zc = z0 + 5 * fh                                           # the crown
    for b0, b1 in ((fins[0], fins[1]), (fins[1], fins[2])):
        bc = (b0 + b1) / 2
        w0, w1 = bc - 0.8, bc + 0.8
        wins = [(w0, w1, z0 + k * fh + 0.6, z0 + k * fh + 2.65) for k in range(5)]
        panels = [(w0, w1, zh + 0.25, zs - 0.2) for (_, _, _, zh), (_, _, zs, _) in zip(wins, wins[1:])]
        wall_holes(mb, Pr, b0, b1, z0, zc, Wm, wins + panels)
        for (_, _, zs, zh) in wins:
            window(mb, Pr, w0, w1, zs, zh, 0.2, 3, 4)
        for (_, _, za, zb) in panels:                          # the sunk panel under each window above
            reveal(mb, Pr, w0, w1, za, zb, 0.06, Wm)
            flat_wall(mb, Pr, w0, w1, za, zb, Wm, d=-0.06)
        # the crown: blank, a V in relief
        flat_wall(mb, Pr, b0, b1, zc, zp, Wm)
        for sg in (-1, 1):
            bar(mb, Pr, bc + sg * 1.2, zp - 0.35, bc, zc + 1.7, 0.13, 0.0, 0.07, Wm, ends=True)
    for s in fins:                                             # slim fins, the whole height
        bar(mb, Pw, s, z0, s, zp - 0.02, 0.22, -rec, 0.42, Wm, ends=True)
    # north and south sides: two columns of small windows near the fin face, two a floor (the north side's are seen
    # over the wing's roof; under it the wing and the porch stand against the wall)
    for P, L, cols in ((Pn, Ln, (Ln - 3.55, Ln - 2.1)), (Ps, Ls, (2.1, 3.55))):
        holes, wins = [], []
        for k in range(3, 6):
            zf = z0 + k * fh
            for sc in cols:
                for za, zb in ((zf + 0.85, zf + 1.65), (zf + 2.2, zf + 3.0)):
                    holes.append((sc - 0.4, sc + 0.4, za, zb))
        wall_holes(mb, P, 0.0, L, z0, zp, Wm, holes)
        for (w0, w1, za, zb) in holes:
            window(mb, P, w0, w1, za, zb, 0.16, 2, 2)
    bar(mb, Pn, Ln - 1.4, z0 + 3.7, Ln - 1.4, zp - 0.1, 0.11, 0.06, 0.17, 'metal_dark', ends=True)    # downpipe
    flat_wall(mb, Pe, 0.0, Le, z0, zp, Wm)
    # the roof slab standing out 0.35 all round, a penthouse with its own slab towards the back, a mast
    um, vm = (u0 + u1) / 2, (v0 + v1) / 2
    box(mb, um, vm, zp + 0.13, u1 - u0 + 0.7, v1 - v0 + 0.7, 0.26, Wm, mats={'top': 'roof_flat'})
    pu0, pu1, pv0, pv1 = u1 - 5.2, u1 - 0.4, v0 + 3.0, v0 + 9.0
    box(mb, (pu0 + pu1) / 2, (pv0 + pv1) / 2, zp + 0.26 + 1.4, pu1 - pu0, pv1 - pv0, 2.8, Wm, skip=('bottom',))
    box(mb, (pu0 + pu1) / 2, (pv0 + pv1) / 2, zp + 0.26 + 2.9, pu1 - pu0 + 0.4, pv1 - pv0 + 0.4, 0.2, Wm,
        mats={'top': 'roof_flat'})
    box(mb, pu0 - 0.03, (pv0 + pv1) / 2, zp + 0.26 + 1.05, 0.06, 0.95, 2.1, 'frame_dark')            # its door
    mc = U(u0 + 3.0, vm, 0)
    mb.cylinder(mc[:2], 0.05, zp + 0.26, zp + 6.8, 'metal_dark', seg=6)              # a plain mast
    out.append(mb)

    # ------------------------------------------------------------------ the north wing
    Wg = parts[990002]['frame']['uv']
    wu0, wu1, wv0, wv1 = Wg
    mb = MeshBuilder('lm_yongjae_wing')
    zt = z0 + 3 * fh
    Pf, Lf = plane(wu0, wv1, wu0, wv0)  # its front to 백양로, s from the north end
    Pt, Lt = plane(wu1, wv1, wu0, wv1)  # the north end
    flat_wall(mb, Pf, 0, Lf, z0 - 4.0, z0, 'concrete_dark')
    flat_wall(mb, Pt, 0, Lt, z0 - 4.0, z0, 'concrete_dark')

    def lights3(P, s0, s1, nfl, z1):
        """Groups of three tall lights in the bays [s0, s1] of a front, a pilaster at each bay end."""
        lw, pier = 1.1, 0.32
        holes = []
        for k in range(nfl):
            zf = z0 + k * fh
            sc = (s0 + s1) / 2
            g0 = sc - (3 * lw + 2 * pier) / 2
            for j in range(3):
                holes.append((g0 + j * (lw + pier), g0 + j * (lw + pier) + lw, zf + 0.85, zf + 3.25))
        wall_holes(mb, P, s0, s1, z0, z1, Wm, holes)
        for (w0, w1, za, zb) in holes:
            window(mb, P, w0, w1, za, zb, 0.18, 2, 4)
    nb = 4
    bw = Lf / nb
    for k in range(nb):
        lights3(Pf, k * bw, (k + 1) * bw, 3, zt)
    for k in range(nb + 1):
        bar(mb, Pf, k * bw, z0, k * bw, zt - 0.05, 0.45, 0.0, 0.12, Wm, ends=True)
    flat_wall(mb, Pf, 0, Lf, z0, z0 + 0.55, 'concrete', d=0.05)                     # plinth
    lights3(Pt, 0.0, Lt, 3, zt)
    for s in (0.0, Lt):
        bar(mb, Pt, s, z0, s, zt - 0.05, 0.45, 0.0, 0.12, Wm, ends=True)
    pts = world2(Wg)
    generic.wall_edge(mb, pts[1], pts[2], z0, zt, 3, fh, st, rnd)                  # the east side (mostly behind)
    cx, cy = U((wu0 + wu1) / 2, (wv0 + wv1) / 2, 0)[:2]
    generic.hip_roof(mb, cx, cy, wv1 - wv0, wu1 - wu0, a + math.pi / 2, zt, 'roof_slate', pitch=0.45, over=0.6)
    box(mb, (wu0 + wu1) / 2, wv1 - 2.2, zt + 2.6, 2.2, 1.6, 5.2, Wm, mats={'top': 'concrete'})    # chimney box
    out.append(mb)

    # ------------------------------------------------------------------ the entrance porch and its canopy
    Pq = parts[990006]['frame']['uv']
    qu0, qu1, qv0, qv1 = Pq
    mb = MeshBuilder('lm_yongjae_porch')
    zq = z0 + 3.4
    Pqw, Lqw = plane(qu0, qv1, qu0, qv0)           # its 백양로 side: the notice board
    Pqn, Lqn = plane(qu1, qv1, qu0, qv1)           # north side: the doors
    flat_wall(mb, Pqw, 0, Lqw, z0 - 4.0, zq, Wm)
    flat_wall(mb, Pqw, 0, Lqw, z0, z0 + 0.4, 'concrete', d=0.03)
    nb0, nb1 = 0.6, Lqw - 0.5                       # the board: green steel frame, posters
    flat_wall(mb, Pqw, nb0, nb1, z0 + 0.95, z0 + 2.35, 'metal_green', d=0.06)
    for k, (s0_, s1_) in enumerate(((nb0 + 0.1, nb0 + 1.3), (nb0 + 1.4, nb0 + 2.6), (nb0 + 2.7, nb1 - 0.1))):
        if s1_ - s0_ > 0.4:
            mb.face([Pqw(s0_, z0 + 1.05, 0.07), Pqw(s1_, z0 + 1.05, 0.07), Pqw(s1_, z0 + 2.25, 0.07), Pqw(s0_, z0 + 2.25, 0.07)],
                    'notice_posters', uvs=[(k / 3, 0), ((k + 1) / 3, 0), ((k + 1) / 3, 1), (k / 3, 1)])
    d0, d1 = 0.5, min(Lqn - 0.3, 0.5 + 2.4)        # the doors: four leaves of glass under a transom
    wall_holes(mb, Pqn, 0, Lqn, z0 - 4.0, zq, Wm, [(d0, d1, z0, z0 + 2.7)])
    reveal(mb, Pqn, d0, d1, z0, z0 + 2.7, 0.25, Wm)
    glazing(mb, Pqn, d0, d1, z0, z0 + 2.7, -0.25, 4, 2, 'frame_dark', fw=0.05, transom=z0 + 2.15)
    # the canopy: a flat slab over the porch and on out over the doors and the walk, one slim post at its corner
    cu0, cu1, cv0, cv1 = qu0 - 0.9, qu1, qv0, qv1 + 4.5
    box(mb, (cu0 + cu1) / 2, (cv0 + cv1) / 2, zq + 0.15, cu1 - cu0, cv1 - cv0, 0.3, Wm, mats={'top': 'roof_flat'})
    box(mb, cu0 + 0.35, cv1 - 0.35, z0 + zq / 2 - z0 / 2, 0.28, 0.28, zq - z0, Wm)
    for k, (uu, vv) in enumerate(((qu0 + 0.9, qv0 + 1.6), (qu0 + 0.9, qv0 + 2.7), (qu0 + 1.4, qv1 + 1.0))):
        box(mb, uu, vv, zq + 0.3 + 0.32, 0.36, 0.9, 0.64, 'plaster_white')                 # air conditioners
        box(mb, uu - 0.19, vv, zq + 0.3 + 0.32, 0.02, 0.5, 0.5, 'metal_dark')
    out.append(mb)

    # ------------------------------------------------------------------ the blocks behind
    E = parts[990003]['frame']['uv']
    mb = MeshBuilder('lm_yongjae_east')
    eu0, eu1, ev0, ev1 = E
    ze = z0 + 5 * fh
    simple_walls(mb, E, 5, ze)
    pitch, over = 0.48, 0.5
    um_, h_ = (eu0 + eu1) / 2, (eu1 - eu0) / 2 * pitch
    zre, zeo, vA, vB = ze + h_, ze - over * pitch, ev0 - 0.4, ev1 + 0.4
    mb.face([U(eu0 - over, vA, zeo), U(um_, vA, zre), U(um_, vB, zre), U(eu0 - over, vB, zeo)], 'roof_slate')
    mb.face([U(eu1 + over, vB, zeo), U(um_, vB, zre), U(um_, vA, zre), U(eu1 + over, vA, zeo)], 'roof_slate')
    mb.face([U(eu0, ev0, ze), U(eu1, ev0, ze), U(um_, ev0, zre)], Wm)
    mb.face([U(eu1, ev1, ze), U(eu0, ev1, ze), U(um_, ev1, zre)], Wm)
    out.append(mb)

    S = parts[990004]['frame']['uv']
    mb = MeshBuilder('lm_yongjae_south')
    zs_ = z0 + 3 * fh
    simple_walls(mb, S, 3, zs_)
    cx, cy = U((S[0] + S[1]) / 2, (S[2] + S[3]) / 2, 0)[:2]
    generic.hip_roof(mb, cx, cy, S[1] - S[0], S[3] - S[2], a, zs_, 'roof_cement', pitch=0.45, over=0.6)
    out.append(mb)

    K = parts[990005]['frame']['uv']
    mb = MeshBuilder('lm_yongjae_link')
    zk = z0 + 4 * fh
    simple_walls(mb, K, 4, zk + 0.9)
    generic.parapet_and_roof(mb, world2(K), zk, st, rnd, clutter=False)
    out.append(mb)

    # ------------------------------------------------------------------ the flight down the 진달래동산
    # (tools/build_campus.py YJ_WALK: from the canopy north-north-west, over the edge of the level ground)
    mb = MeshBuilder('lm_yongjae_flight')
    du, dv = -7.0, 9.0
    dl = math.hypot(du, dv)
    du, dv = du / dl, dv / dl
    tu_ = (-7.0 - (-4.0)) / du                         # where the walk leaves the level ground (u = -7)
    fu, fv = -4.0 + du * tu_, 24.0 + dv * tu_
    wx, wy = U(fu, fv, 0)[:2]
    dx, dy = du * ca - dv * sa, du * sa + dv * ca      # the walk's direction (world): local -y
    mb.xf = local_frame(wx, wy, math.atan2(dx, -dy), z0)
    stair_flight(mb, 0.0, 0.0, 2.6, 0.0, landing=1.2, tread=0.34, flare=0.15, cheek=0.3, cheek_mat='concrete',
                 mat='stone_step', gfn=local_ground(mb))
    out.append(mb)
    return out


# ============================================================================= 정구장 (tennis courts)
def tennis():
    """The two fenced blocks of courts south-west of 공학관 (tools/build_campus.py TENNIS; 1990/1995 maps no. 47, the
    1995 aerial photo): red clay to the west, green hard courts east of them, each block a level pad on the slope with
    a low kerb, three courts side by side (doubles courts 10.97 x 23.77 m with their singles lines), nets on posts, and
    a 3.6 m chain-link fence on steel posts round the block."""
    T = CAMPUS.get('statues', {}).get('tennis')
    if not T:
        return []
    out = []
    for k, pd in enumerate(T['pads']):
        mb = MeshBuilder('lm_tennis_%d' % k)
        mb.xf = local_frame(T['o'][0], T['o'][1], T['rot'], pd['h'])
        (u0, u1), (v0, v1) = pd['u'], pd['v']
        surf = 'court_clay' if pd['kind'] == 'clay' else 'court_hard'
        z = 0.08
        mb.box(((u0 + u1) / 2, (v0 + v1) / 2, (z - 1.5) / 2), (u1 - u0, v1 - v0, z + 1.5), surf, skip=('bottom',),
               mats={'sides': 'concrete'})
        mb.box(((u0 + u1) / 2, (v0 + v1) / 2, (z + 0.12 - 1.5) / 2), (u1 - u0 + 0.5, v1 - v0 + 0.5, z + 0.12 + 1.5),
               'concrete', skip=('bottom', 'top'))                                           # kerb round the pad
        lw = 0.05

        def line(x0, y0, x1, y1):
            dx, dy = x1 - x0, y1 - y0
            n = math.hypot(dx, dy) or 1
            ox, oy = -dy / n * lw / 2, dx / n * lw / 2
            mb.face([(x0 + ox, y0 + oy, z + 0.01), (x0 - ox, y0 - oy, z + 0.01), (x1 - ox, y1 - oy, z + 0.01),
                     (x1 + ox, y1 + oy, z + 0.01)], 'paint_white')
        n_ = pd['courts']
        cw = (u1 - u0) / n_
        cy = (v0 + v1) / 2
        for i in range(n_):
            cx = u0 + cw * (i + 0.5)
            hw, hs, hl, sv = 10.97 / 2, 8.23 / 2, 23.77 / 2, 6.40
            for x in (-hw, -hs, hs, hw):
                line(cx + x, cy - hl, cx + x, cy + hl)
            for y in (-hl, hl):
                line(cx - hw, cy + y, cx + hw, cy + y)
            for y in (-sv, sv):
                line(cx - hs, cy + y, cx + hs, cy + y)
            line(cx, cy - sv, cx, cy + sv)
            for y in (-hl, hl):                                       # centre marks
                line(cx, cy + y, cx, cy + y + (0.1 if y < 0 else -0.1))
            # the net: posts 0.914 m outside the doubles lines, the cord 1.07 m up sagging to 0.914 at the strap
            px = hw + 0.914
            for sg in (-1, 1):
                mb.cylinder((cx + sg * px, cy), 0.04, z, z + 1.07, 'metal_green', seg=8)
            for j in range(8):
                xa, xb = -px + 2 * px * j / 8, -px + 2 * px * (j + 1) / 8
                ha = 1.07 - 0.156 * (1 - (xa / px) ** 2)
                hb = 1.07 - 0.156 * (1 - (xb / px) ** 2)
                mb.face([(cx + xa, cy, z + 0.03), (cx + xb, cy, z + 0.03), (cx + xb, cy, z + hb - 0.06), (cx + xa, cy, z + ha - 0.06)], 'net_mesh')
                mb.face([(cx + xa, cy, z + ha - 0.07), (cx + xb, cy, z + hb - 0.07), (cx + xb, cy, z + hb), (cx + xa, cy, z + ha)], 'paint_white')
                mb.face([(cx + xa, cy, z + ha), (cx + xb, cy, z + hb), (cx + xb, cy, z + hb - 0.07), (cx + xa, cy, z + ha - 0.07)], 'paint_white')
        # the fence: posts every 3 m round the pad, rails top and bottom, chain-link between
        H = 3.6
        ring = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        for (xa, ya), (xb, yb) in zip(ring, ring[1:] + ring[:1]):
            Ls = math.hypot(xb - xa, yb - ya)
            m = max(1, int(round(Ls / 3.0)))
            for j in range(m + 1):
                x, y = xa + (xb - xa) * j / m, ya + (yb - ya) * j / m
                if j < m:
                    mb.cylinder((x, y), 0.045, z - 0.1, z + H, 'metal_green', seg=6)
            for zz in (z + 0.1, z + H - 0.05):
                mb.box(((xa + xb) / 2, (ya + yb) / 2, zz), (abs(xb - xa) + 0.05, abs(yb - ya) + 0.05, 0.05), 'metal_green')
            mb.face([(xa, ya, z + 0.05), (xb, yb, z + 0.05), (xb, yb, z + H), (xa, ya, z + H)], 'fence_mesh')
        out.append(mb)
    return out


# ============================================================================= 공학원 공사장 (1995.8 - 1999.4)
def gongwon_site():
    """The hoarding round 공학원's building site, where the 정구장 had been (tools/build_campus.py GONGWON_SITE): steel
    sheet panels 2.4 m high on posts every 2.5 m following the ground, white over a blue foot band, both faces (6 cm
    apart: coincident faces would read as fully occluded in the AO bake, black on the phones); a steel gate on the
    service road to the north."""
    G = CAMPUS.get('statues', {}).get('gongwon_site')
    if not G:
        return []
    mb = MeshBuilder('lm_gongwon_site')
    ring, (g0, g1) = G['ring'], G['gate']
    n = len(ring)
    H, foot, sink = 2.4, 0.6, 0.3
    for i in range(n):
        (xa, ya, za), (xb, yb, zb) = ring[i], ring[(i + 1) % n]
        gate = g0 <= i < g1
        bands = [(-sink, H + 0.3, 'metal')] if gate else [(-sink, foot, 'paint_blue'), (foot, H, 'paint_white')]
        L = math.hypot(xb - xa, yb - ya) or 1.0
        nx, ny = (yb - ya) / L * 0.03, -(xb - xa) / L * 0.03
        for z0, z1, mat in bands:
            for sg in (1, -1):
                a0, a1 = (xa + sg * nx, ya + sg * ny, za + z0), (xa + sg * nx, ya + sg * ny, za + z1)
                b0, b1 = (xb + sg * nx, yb + sg * ny, zb + z0), (xb + sg * nx, yb + sg * ny, zb + z1)
                mb.face([a0, b0, b1, a1] if sg > 0 else [b0, a0, a1, b1], mat)
        zt = bands[-1][1]
        mb.face([(xa + nx, ya + ny, za + zt), (xb + nx, yb + ny, zb + zt), (xb - nx, yb - ny, zb + zt), (xa - nx, ya - ny, za + zt)],
                'metal_dark')
        h = H + (0.45 if g0 <= i <= g1 else 0.1)
        mb.box((xa, ya, za + (h - sink) / 2), (0.1, 0.1, h + sink), 'metal_dark', rotz=math.atan2(yb - ya, xb - xa))
    return [mb]


# ============================================================================= 광복관 (법과대학)
# 1997's 광복관 was neither the red-brick block the generic builder made of it nor today's six-storey granite hall (its
# 2000s rebuilding, reference/학교연혁_광복관.jpg).  The 1990 and 1995 campus maps (reference/1990_캠퍼스_지도.png and
# 1995_캠퍼스_지도.jpg, no. 7) draw an L of three storeys under a hipped roof, the long south front in rows of square
# windows; the 1995 aerial photo (reference/1995_캠퍼스_항공사진_남쪽에서.jpg) shows it pale behind the library under a grey
# hipped roof, the north arm a storey higher where it meets the south one, a chimney there.  The 1996 graduation-album
# photos of 경영학과 and 법학과 on its front steps (2022 재상봉 기념문집 pp. 194-195; reference/고증.md) give the
# front: speckled grey granite between flat granite pilasters, the main floor raised over a half-sunk basement with
# barred windows, three bays of bronze-framed glass doors and screens between the pilasters, a black lantern on each,
# barred windows beside them, and a broad granite flight of ten or eleven risers the width of the three bays with
# stainless steel handrails, a band of square lattice panels on the basement wall either side.  The door is where OSM's
# walk and steps up from the library reach the south front, some 19 m from its west end.
KB = dict(fh=3.7, bay=4.25, door_s=19.0, floors_s=3, floors_n=4, lift=1.75)


def kwangbok():
    b = bld(468614722)
    fp = [Vector(p) for p in b['footprint']]
    mb = MeshBuilder('lm_kwangbok')
    tS = (fp[2] - fp[1]).normalized()
    nS = Vector((tS.y, -tS.x))
    tE = (fp[3] - fp[2]).normalized()
    dS, wN = (fp[0] - fp[1]).length, (fp[3] - fp[4]).length
    X, Y = fp[2] + tE * dS, fp[2] - tS * wN            # the south arm's hidden NE corner; where the north arm meets the front
    F = KB['fh']
    pd = fp[1] + tS * KB['door_s']
    zm = min(ground(*(pd + nS * k + tS * u)) for k in (3.5, 7.0) for u in (-5.0, 0.0, 5.0)) + KB['lift']
    zS, zN = zm + KB['floors_s'] * F, zm + KB['floors_n'] * F
    WALL, PIL = 'granite_light', 'stone_granite'

    def lantern(P, s, z, ang):
        c = Vector(P(s, z, 0.44))
        mb.box((c.x, c.y, z), (0.24, 0.24, 0.38), 'globe', rotz=ang)
        for dz in (-0.21, 0.22):
            mb.box((c.x, c.y, z + dz), (0.32, 0.32, 0.07), 'metal_dark', rotz=ang)
        mb.box((c.x, c.y, z + 0.32), (0.1, 0.1, 0.14), 'metal_dark', rotz=ang)
        k = Vector(P(s, z + 0.12, 0.3))
        mb.box((k.x, k.y, z + 0.12), (0.05, 0.3, 0.05), 'metal_dark', rotz=ang)

    def facade(a, b_, ztop, z_from=None, door=False, bars=False):
        P, L, t, n = edge_P(a, b_)
        ang = math.atan2(t.y, t.x)
        nb = max(1, int(round(L / KB['bay'])))
        bw = L / nb
        z_lo = zm if z_from is None else z_from
        k0 = max(0, min(nb - 3, int(round(KB['door_s'] / bw - 1.5)))) if door else -9
        if z_from is None:
            # the basement storey: granite down into the ground, a pale water table, low barred windows clear of it
            flat_wall(mb, P, 0, L, zm - 5.0, zm - 0.3, PIL)
            bar(mb, P, 0, zm - 0.15, L, zm - 0.15, 0.3, 0.0, 0.08, 'stone_trim', ends=True)
            for k in range(nb):
                sc = (k + 0.5) * bw
                if door and k0 - 2 <= k <= k0 + 4:
                    continue
                w = bw * 0.46
                if max(ground(*P(sc + u, 0, 1.0)[:2]) for u in (-w / 2, w / 2)) > zm - 1.6:
                    continue
                zb0, zb1 = zm - 1.45, zm - 0.55
                mb.quad(P(sc - w / 2, zb0, 0.01), P(sc + w / 2, zb0, 0.01), P(sc + w / 2, zb1, 0.01), P(sc - w / 2, zb1, 0.01), 'glass')
                for j in range(1, 9):
                    s = sc - w / 2 + w * j / 9
                    bar(mb, P, s, zb0, s, zb1, 0.025, 0.02, 0.05, 'metal_dark')
            if door:
                # square lattice panels on the basement wall either side of the flight
                for s0_, s1_ in ((max(0.0, (k0 - 2) * bw), k0 * bw - 0.2), ((k0 + 3) * bw + 0.2, min(L, (k0 + 5) * bw))):
                    za, zb = zm - 1.15, zm - 0.35
                    m = max(1, int((s1_ - s0_) / 0.4))
                    for j in range(m + 1):
                        s = s0_ + (s1_ - s0_) * j / m
                        bar(mb, P, s, za, s, zb, 0.06, 0.0, 0.05, 'stone_trim')
                    for z in (za, (za + zb) / 2, zb):
                        bar(mb, P, s0_, z, s1_, z, 0.06, 0.0, 0.05, 'stone_trim')
        nfl = int(round((ztop - z_lo) / F))
        for f in range(nfl):
            zf = z_lo + f * F
            for k in range(nb):
                s0, s1 = k * bw, (k + 1) * bw
                if f == 0 and k0 <= k < k0 + 3:
                    continue
                window_grid(mb, P, L, zf, 1, F, bw, WALL, ww=0.6, sill=0.95, head=0.75, depth=0.22, frame='frame_dark',
                            mull=2, s_start=s0, s_end=s1)
                if bars and f == 0 and z_from is None:
                    w = bw * 0.6
                    for j in range(1, 14):
                        s = s0 + (bw - w) / 2 + w * j / 14
                        bar(mb, P, s, zf + 0.95, s, zf + F - 0.75, 0.025, 0.02, 0.05, 'metal_dark')
        if door:
            for k in range(k0, k0 + 3):
                s0, s1 = k * bw, (k + 1) * bw
                o0, o1, zo = s0 + 0.42, s1 - 0.42, zm + 3.3
                flat_wall(mb, P, s0, o0, zm, zm + F, WALL)
                flat_wall(mb, P, o1, s1, zm, zm + F, WALL)
                flat_wall(mb, P, o0, o1, zo, zm + F, WALL)
                mb.quad(P(o1, zo, 0), P(o0, zo, 0), P(o0, zo, -0.4), P(o1, zo, -0.4), PIL)
                mb.quad(P(o0, zm, -0.4), P(o0, zo, -0.4), P(o0, zo, 0), P(o0, zm, 0), PIL)
                mb.quad(P(o1, zm, 0), P(o1, zo, 0), P(o1, zo, -0.4), P(o1, zm, -0.4), PIL)
                shopfront(mb, P, o0, o1, zm, zo, -0.4, bays=3, door_h=2.45, frame='panel_bronze')
                vestibule(mb, P, o0, o1, zm, zo, -0.42, 4.5, lights=2)
            for k in range(k0, k0 + 4):
                lantern(P, k * bw, zm + 2.75, ang)
        # flat granite pilasters at the bay lines, a cornice under the eaves
        for k in range(nb + 1):
            s = min(max(k * bw, 0.35), L - 0.35)
            bar(mb, P, s, (zm - 0.3) if z_from is None else z_from, s, ztop - 0.3, 0.7, 0.0, 0.2, PIL, ends=True)
        bar(mb, P, 0, ztop - 0.22, L, ztop - 0.22, 0.44, 0.0, 0.34, 'stone_trim', ends=True)
        if door:
            # the flight: from the landing in front of the glass down to the forecourt, stainless rails both sides
            sc = (k0 + 1.5) * bw
            o = P(sc, zm, 0)
            mb.xf = Matrix.Translation(Vector(o)) @ Matrix.Rotation(ang, 4, 'Z')
            stair_flight(mb, 0.0, 0.0, 3 * bw - 0.3, 0.0, mat='stone_step', landing=2.4, tread=0.33, flare=0.0, rail=True,
                         rail_mat='frame_silver', gfn=local_ground(mb), maxrise=0.165)
            mb.xf = Matrix.Identity(4)

    facade(fp[0], fp[1], zS)
    facade(fp[1], Y, zS, door=True, bars=True)
    facade(Y, fp[2], zN, bars=True)
    facade(fp[2], fp[3], zN)
    facade(fp[3], fp[4], zN)
    facade(fp[4], fp[5], zN)
    facade(fp[5], Y, zN, z_from=zS)               # the north arm's west wall over the south arm's roof
    facade(fp[5], fp[0], zS)
    # hipped grey roofs over the two arms (the north arm's, higher, takes in the corner), soffits under the eaves
    for poly, z, rise in (([fp[1], fp[2], X, fp[0]], zS, 2.7), ([Y, fp[2], fp[3], fp[4]], zN, 3.2)):
        hip_roof(mb, [tuple(p) for p in poly], z, rise, 'roof_slate', eave=0.55)
        q = offset_poly([tuple(p) for p in poly], 0.55)
        mb.face([(p[0], p[1], z) for p in q][::-1], 'stone_trim')
    c = (fp[2] + Y) / 2 + tE * 6.0 - tS * 3.0                   # chimney
    mb.box((c.x, c.y, zN + 2.4), (1.1, 0.8, 4.8), PIL, rotz=math.atan2(tS.y, tS.x))
    return [mb]


BUILDERS = {'library': library, 'union': union, 'centennial': centennial, 'underwood': underwood,
            'stimson': stimson, 'appenzeller': appenzeller, 'auditorium': auditorium, 'chapel': chapel,
            'engineering': engineering, 'hanok': hanok, 'yongjae': yongjae, 'none': lambda: [],
            'daewoo': daewoo, 'daewoo_annex': daewoo_annex, 'yeonhui': yeonhui, 'kwangbok': kwangbok,
            'seongam': seongam, 'gyoyuk': gyoyuk}
