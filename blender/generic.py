"""Procedural facade generator for the non-landmark buildings (footprint extrusion
with real recessed windows, sills, floor bands, parapets, roofs and rooftop clutter)."""
import math, random
from mathutils import Vector, Matrix
from common import MeshBuilder, ground, ground_top, offset_poly, min_area_rect, poly_area
import windows, backs

STYLE = {
    #          wall            window frame     bay   win_w  sill  head  band      found
    'modern': dict(wall='concrete', alt='concrete_warm', glass='glass', frame='frame_dark', bay=3.6, ww=0.78, sill=1.0, head=0.45, band=True, depth=0.28, mull=2),
    'white':  dict(wall='plaster_white', alt='plaster_cream', glass='glass', frame='frame_dark', bay=3.2, ww=0.55, sill=0.95, head=0.6, band=False, depth=0.22, mull=1),
    'stone':  dict(wall='stone_rubble', alt='stone_rubble', glass='glass', frame='frame_white', bay=3.0, ww=0.42, sill=0.9, head=0.7, band=False, depth=0.32, mull=1, trim='stone_trim'),
    'house':  dict(wall='plaster_cream', alt='brick_red', glass='glass', frame='frame_white', bay=3.0, ww=0.45, sill=0.95, head=0.65, band=False, depth=0.18, mull=1),
    'gym':    dict(wall='concrete', alt='concrete', glass='glass', frame='frame_dark', bay=4.5, ww=0.8, sill=4.6, head=0.4, band=False, depth=0.2, mull=3),
    # 1997 halls from the university's building photos (yonsei.ac.kr/sc/349): red brick (알렌관 · 언어연구교육원;
    # 광복관, once here, was granite: blender/landmarks.py kwangbok), tan tile (국제학사), pale grey rubble with dressed-stone trim and a slate roof (빌링슬리관: the 1996
    # 의류환경학과 album photo on its front, reference/고증.md)
    'brick':  dict(wall='brick_red', alt='concrete', glass='glass', frame='frame_white', bay=3.0, ww=0.5, sill=0.95, head=0.6, band=False, depth=0.22, mull=1, trim='stone_trim'),
    'tile':   dict(wall='tile_facade', alt='concrete', glass='glass', frame='frame_silver', bay=3.2, ww=0.5, sill=0.95, head=0.6, band=False, depth=0.2, mull=1),
    # (빌링슬리관 only) a group of three tall lights a bay, 4.1 m: window_group; ww is the group's share of the bay
    'stone_pale': dict(wall='stone_rubble_gray', alt='stone_rubble_gray', glass='glass', frame='wood_dark', bay=4.1, ww=0.62, sill=1.0, head=0.75, band=False, depth=0.3, mull=1, trim='stone_trim', lights=3),
    'city':   dict(wall='brick_red', alt='plaster_cream', glass='glass', frame='frame_silver', bay=3.0, ww=0.5, sill=0.95, head=0.6, band=False, depth=0.15, mull=1),
}
FH = {'modern': 3.8, 'white': 3.6, 'stone': 4.2, 'house': 3.4, 'gym': 6.5, 'city': 3.0, 'brick': 3.6, 'tile': 3.4, 'stone_pale': 4.0}


def wall_edge(mb, a, b, z0, z1, nfloors, fh, st, rnd, skip_windows=False, ground_floor_shop=False, door=None,
              found=True, back=None):
    """door: (s along the edge, style, options) -- the ground-floor bay(s) there are left open for porch() to fill.
    found: the dark foundation under z0 (not for a storey standing on a lower roof)
    back: a back door in one ground-floor bay instead of its window (blender/backs.py back_pick_door)"""
    a2, b2 = a, b
    a, b = Vector((*a, 0)), Vector((*b, 0))
    t = b - a
    L = t.length
    if L < 0.05:
        return
    t /= L
    n = Vector((t.y, -t.x, 0))          # outward for CCW polygons
    wall, glass, frame = st['wall'], st['glass'], st['frame']

    def P(s, z, d=0.0):
        p = a + t * s + n * d
        return (p.x, p.y, z)

    # foundation (hidden under terrain on slopes; flagged smooth so that the bake leaves it one face: with a plinth
    # standing in front of its top, blender/backs.py, bake.py would keep a grid of it for the occlusion nobody sees)
    if found:
        mb.quad(P(0, z0 - 4), P(L, z0 - 4), P(L, z0), P(0, z0), 'concrete_dark', smooth='fd%d' % len(mb.faces))
    bays = int(round(L / st['bay']))
    if L < 2.6 or bays < 1 or skip_windows:
        mb.quad(P(0, z0), P(L, z0), P(L, z1), P(0, z1), wall)
        return
    bw = L / bays
    zt = z0 + nfloors * fh
    kd = min(bays - 1, max(0, int(door[0] / bw))) if door else -1
    span = min(bays, door[2].get('span', 1)) if door else 1
    if span > 1:
        kd = min(bays - span, max(0, kd - span // 2))
    fd = 0
    if door:
        # on a slope the door is on the storey the ground in front of it reaches (과학관's courtyard front)
        pm = a + t * ((kd + span / 2) * bw) + n * 1.5
        fd = max(0, min(nfloors - 1, int((ground(pm.x, pm.y) + 0.3 - z0) / fh)))
        fd = door[2].get('floor', fd)
    for f in range(nfloors):
        zf = z0 + f * fh
        shop = ground_floor_shop and f == 0
        for k in range(bays):
            s0, s1 = k * bw, (k + 1) * bw
            if f == fd and kd <= k < kd + span:
                if k == kd:
                    porch(mb, a2, b2, s0, s0 + span * bw, zf, fh, st, door[1], door[2])
                continue
            if back and f == back['floor'] and k == back['bay']:
                backs.back_door(mb, a2, b2, s0, s1, zf, fh, st, back)
                continue
            mid = a + t * ((s0 + s1) / 2) + n * 0.6
            g = ground(mid.x, mid.y)
            sill = 0.25 if shop else st['sill']
            head = 0.35 if shop else st['head']
            if g > zf + sill - 0.15 or (f == 0 and st is STYLE['gym'] and False):
                mb.quad(P(s0, zf), P(s1, zf), P(s1, zf + fh), P(s0, zf + fh), wall)
                continue
            if st.get('lights'):                # three lights in one dressed-stone frame (빌링슬리관)
                window_group(mb, P, s0, s1, zf, fh, st)
                continue
            ww = bw * (0.92 if shop else st['ww'])
            w0 = s0 + (bw - ww) / 2
            w1 = w0 + ww
            zs, zh = zf + sill, zf + fh - head
            d = st['depth']
            # surround
            mb.quad(P(s0, zf), P(s1, zf), P(s1, zs), P(s0, zs), wall)
            mb.quad(P(s0, zh), P(s1, zh), P(s1, zf + fh), P(s0, zf + fh), wall)
            mb.quad(P(s0, zs), P(w0, zs), P(w0, zh), P(s0, zh), wall)
            mb.quad(P(w1, zs), P(s1, zs), P(s1, zh), P(w1, zh), wall)
            # reveals
            rv = st.get('trim', wall)
            mb.quad(P(w0, zs, 0), P(w0, zs, -d), P(w1, zs, -d), P(w1, zs, 0), rv)
            mb.quad(P(w1, zh, 0), P(w1, zh, -d), P(w0, zh, -d), P(w0, zh, 0), rv)
            mb.quad(P(w0, zh, 0), P(w0, zh, -d), P(w0, zs, -d), P(w0, zs, 0), rv)
            mb.quad(P(w1, zs, 0), P(w1, zs, -d), P(w1, zh, -d), P(w1, zh, 0), rv)
            # glass + frame: one room behind the window (a shop or the gym's hall instead: common.py pane_uv), now and
            # then a sash slid open (blender/windows.py)
            cell = windows.glass(mb, P, w0, w1, zs, zh, d, st, shop)
            fw = 0.06
            nm = st['mull'] if not shop else 3
            dd = -d + 0.05
            if not (nm == 1 and ww < 1.0):
                for m in range(1, nm + 1):
                    sm = w0 + ww * m / (nm + 1)
                    mb.quad(P(sm - fw, zs, dd), P(sm + fw, zs, dd), P(sm + fw, zh, dd), P(sm - fw, zh, dd), frame)
            zt_ = zs + (zh - zs) * 0.72
            mb.quad(P(w0, zt_ - fw, dd), P(w1, zt_ - fw, dd), P(w1, zt_ + fw, dd), P(w0, zt_ + fw, dd), frame)
            if not shop:
                tm = st.get('trim', 'stone_trim' if st['wall'] != 'concrete' else 'concrete')
                mb.quad(P(w0 - 0.08, zs - 0.08, 0.1), P(w1 + 0.08, zs - 0.08, 0.1), P(w1 + 0.08, zs, 0.1), P(w0 - 0.08, zs, 0.1), tm)
                mb.quad(P(w0 - 0.08, zs, 0.1), P(w1 + 0.08, zs, 0.1), P(w1 + 0.08, zs, 0), P(w0 - 0.08, zs, 0), tm)
            windows.aircon(mb, P, w0, w1, zs, zh, d, st, cell, f)
        # floor band (projecting slab edge) for modern blocks
        if st['band'] and f > 0:
            zb = zf - 0.18
            mb.quad(P(0, zb, 0.14), P(L, zb, 0.14), P(L, zb + 0.4, 0.14), P(0, zb + 0.4, 0.14), st['alt'])
            mb.quad(P(0, zb + 0.4, 0.14), P(L, zb + 0.4, 0.14), P(L, zb + 0.4, 0), P(0, zb + 0.4, 0), st['alt'])
            mb.quad(P(0, zb, 0), P(L, zb, 0), P(L, zb, 0.14), P(0, zb, 0.14), st['alt'])
    if z1 > zt:
        mb.quad(P(0, zt), P(L, zt), P(L, z1), P(0, z1), wall)


# ----------------------------------------------------------------------------- front doors
# What the hall doors were like, from the 1996 graduation-album photos of the departments on their halls' steps
# (2022 재상봉 기념문집 「25년 전 우리는」, reference/고증.md): the postwar halls a pair or four leaves of
# aluminium-framed glass under a transom (백주년기념관, 음악관), a flat concrete canopy over them (음악관's deep one), a
# granite flight down to the walk with low granite side walls and steel handrails once it is high (과학관,
# 백주년기념관); the old stone halls a
# Tudor-arched door deep in the wall, dark steel-framed glass over a solid lower panel, rubble cheek walls with a pale
# coping (아펜젤러관, 빌링슬리관 -- whose door is in a shallow porch, a bay and a half wide, under a low gable coped with
# dressed stone); the houses a plain door and a step or two.
ENTRY = {
    'modern':     dict(kind='glass', w=3.0, h=2.6, top=0.6, canopy=2.2, rec=0.45, step='stone_step', side='stone_granite'),
    'white':      dict(kind='glass', w=2.6, h=2.5, top=0.5, canopy=1.8, rec=0.4, step='stone_step', side='stone_granite'),
    'tile':       dict(kind='glass', w=2.6, h=2.5, top=0.5, canopy=1.6, rec=0.35, step='stone_step', side='stone_granite'),
    'brick':      dict(kind='glass', w=2.4, h=2.5, top=0.5, canopy=1.6, rec=0.4, step='stone_step', side='stone_trim'),
    'gym':        dict(kind='glass', w=3.6, h=2.7, top=0.9, canopy=2.6, rec=0.5, step='stone_step', side='stone_granite'),
    'stone':      dict(kind='arch', w=1.9, spring=2.35, rec=0.6, step='stone_step', side='stone_rubble'),
    'stone_pale': dict(kind='arch', w=2.3, spring=2.5, rec=0.7, step='stone_step', side='stone_rubble', porch=0.6),
    'house':      dict(kind='house', w=1.0, h=2.1, canopy=1.0, rec=0.15, step='concrete', side='concrete'),
}
MUSIC_CANOPY = 3.6    # 음악관's landing under the canopy, out to the columns' front
MUSIC_ARC = (5.0, 3.9)    # the canopy's half-round front: half its width at the wall, its depth in the middle


def music_canopy(mb, P, sc, w, zc, ang, zd):
    """음악관's porch (기악과's 1996 album photo; 신관's door, Kakao roadview 2008 · 2010 and skyview): a deep flat
    canopy with a half-round front, its soffit lined with slim white slats running out from the wall, a thick white
    fascia, carried near its front on two round white columns either side of the doors."""
    import landmarks as LM
    cd = MUSIC_CANOPY
    r0, h = MUSIC_ARC
    c = (h * h - r0 * r0) / (2 * h)                     # (the arc's circle: through the wall at +-r0 and h out)
    rr = h - c
    dep = lambda x: c + math.sqrt(max(rr * rr - x * x, 0.0))
    xs = [-r0 + 2 * r0 * k / 24 for k in range(25)]
    zt = zc + 0.6
    top = [P(sc + x, zt, dep(x)) for x in xs]
    bot = [P(sc + x, zc, dep(x)) for x in xs]
    mb.face(top, 'plaster_white')
    mb.face(bot[::-1], 'plaster_white')
    for k in range(24):                                                     # the fascia, and its drip edge
        mb.quad(bot[k], bot[k + 1], top[k + 1], top[k], 'plaster_white')
        q = [P(sc + x, z, dep(x) + 0.03) for x, z in ((xs[k], zt - 0.1), (xs[k + 1], zt - 0.1), (xs[k + 1], zt + 0.02),
                                                      (xs[k], zt + 0.02))]
        mb.quad(*q, 'concrete_dark')
    for k in range(int(2 * r0 / 0.32) + 1):                                 # the slatted soffit
        s = -r0 + 0.16 + k * 0.32
        if s > r0 - 0.16:
            break
        LM.bar(mb, P, sc + s - 0.045, zc - 0.07, sc + s + 0.045, zc - 0.07, 0.07, 0.05,
               min(dep(s - 0.045), dep(s + 0.045)) - 0.08, 'frame_silver', ends=True)
    # the columns: 0.44 m thick, 2.37 m either side of the doors' middle, on the landing's front (fitted to the 1996
    # photo with the doors' frame, reference/고증/3.11_음악관.md)
    for sg in (-1, 1):
        x, y, _ = P(sc + sg * (w / 2 - 0.3), 0, cd - 0.55)
        mb.cylinder((x, y), 0.22, zd - 0.3, zc, 'plaster_white', seg=20)
        mb.cylinder((x, y), 0.28, zd - 0.3, zd + 0.08, 'stone_granite', seg=20)


def music_planters(mb, fw, y_foot, gfn):
    """the white-tiled planters either side of 음악관's steps, waist high on the landing, with shrubs in them and a
    steel rail along the right one (local frame of the flight)"""
    for sg in (-1, 1):
        x0, x1 = fw / 2 + 0.1, fw / 2 + 1.5
        xc = sg * (x0 + x1) / 2
        y0, y1 = 0.3, y_foot - 0.4
        zb = min(gfn(xc, y0), gfn(xc, y1), gfn(xc, (y0 + y1) / 2)) - 0.4
        zt = 0.95
        mb.box((xc, (y0 + y1) / 2, (zt + zb) / 2), (x1 - x0, y0 - y1, zt - zb), 'tile_white', mats={'top': 'tile_white'})
        mb.box((xc, (y0 + y1) / 2, zt - 0.05), (x1 - x0 - 0.3, y0 - y1 - 0.3, 0.12), 'soil')
        for k in range(3):
            yy = y0 - 0.9 - k * (y0 - y1 - 1.6) / 2
            mb.sphere((xc, yy, zt + 0.35), 0.55, 'hedge_boxwood', seg=10, rings=7, sz=0.75)
        if sg > 0:
            for yy in (y0 - 0.2, y1 + 0.2):
                mb.box((xc - 0.3, yy, zt + 0.45), (0.05, 0.05, 0.9), 'chrome')
            mb.box((xc - 0.3, (y0 + y1) / 2, zt + 0.9), (0.06, y0 - y1 - 0.4, 0.06), 'chrome')


def lamp5(mb, x, y, z):
    """the five-globe lamp at the head of 과학관's flight (the 1996 photos): a dark post, a cross of arms, a white globe
    on each arm and one on top"""
    mb.cylinder((x, y), 0.2, z, z + 0.6, 'metal_dark', seg=10, r1=0.13)
    mb.cylinder((x, y), 0.1, z + 0.6, z + 3.9, 'metal_dark', seg=10, r1=0.07)
    for dx, dy in ((0.55, 0), (-0.55, 0), (0, 0.55), (0, -0.55)):
        mb.box((x + dx / 2, y + dy / 2, z + 3.85), (abs(dx) + 0.05, abs(dy) + 0.05, 0.05), 'metal_dark')
        mb.cylinder((x + dx, y + dy), 0.05, z + 3.85, z + 3.97, 'metal_dark', seg=8)
        mb.sphere((x + dx, y + dy, z + 4.17), 0.22, 'globe', seg=12, rings=8)
    mb.cylinder((x, y), 0.05, z + 3.9, z + 4.25, 'metal_dark', seg=8)
    mb.sphere((x, y, z + 4.47), 0.24, 'globe', seg=12, rings=8)


DOORS = []            # world-space zones of the generic halls' flights (merged into web/public/data/entrances.json)


def window_group(mb, P, s0, s1, zf, fh, st):
    """One bay [s0, s1] of a storey of 빌링슬리관's wall (the 1996 album photo, reference/빌링슬리관_현관_1996.jpg; and
    reference/학교연혁_빌링슬리관_옛생활과학관.jpg): three tall lights side by side in one dressed-stone frame, stone
    mullions between them, a lintel over them and a sill running on past them, each light a dark wooden sash with a
    meeting rail."""
    import landmarks as LM
    wall, trim, frame, d, n = st['wall'], st.get('trim', 'stone_trim'), st['frame'], st['depth'], st['lights']
    mw = 0.2                                             # stone mullion
    gw = (s1 - s0) * st['ww']
    w0 = (s0 + s1 - gw) / 2
    w1 = w0 + gw
    zs, zh = zf + st['sill'], zf + fh - st['head']
    LM.wall_holes(mb, P, s0, s1, zf, zf + fh, wall, [(w0, w1, zs, zh)])
    LM.reveal(mb, P, w0, w1, zs, zh, d, trim)
    lw = (gw - (n - 1) * mw) / n
    for k in range(1, n):
        c = w0 + k * (lw + mw) - mw / 2
        LM.bar(mb, P, c, zs, c, zh, mw, -d, 0.0, trim)
    fw, zm = 0.08, zs + (zh - zs) * 0.6
    for k in range(n):
        a = w0 + k * (lw + mw)
        b = a + lw
        # the sash frame in the glass's own plane (one standing in front would shade the glass's corners in the
        # occlusion bake, blender/bake.py), a room behind each light, the meeting rail across it
        LM.wall_holes(mb, P, a, b, zs, zh, frame, [(a + fw, b - fw, zs + fw, zh - fw)], d=-d)
        mb.quad(P(a + fw, zs + fw, -d), P(b - fw, zs + fw, -d), P(b - fw, zh - fw, -d), P(a + fw, zh - fw, -d),
                st['glass'], panes=(1, 1))
        mb.quad(P(a + fw, zm - 0.045, -d + 0.04), P(b - fw, zm - 0.045, -d + 0.04), P(b - fw, zm + 0.045, -d + 0.04),
                P(a + fw, zm + 0.045, -d + 0.04), frame)
    # the dressed stone standing a little proud of the rubble
    for s in (w0 - 0.1, w1 + 0.1):
        LM.bar(mb, P, s, zs, s, zh, 0.2, 0.0, 0.04, trim)
    LM.bar(mb, P, w0 - 0.24, zh + 0.13, w1 + 0.24, zh + 0.13, 0.26, 0.0, 0.06, trim, ends=True)
    LM.bar(mb, P, w0 - 0.32, zs - 0.07, w1 + 0.32, zs - 0.07, 0.14, 0.0, 0.12, trim, ends=True)


def porch_gable(mb, P, Pw, fa, fb, sc, zb, zw, zg, proj, s0, s1, zt, wall):
    """빌링슬리관's porch over [fa, fb] (P: its face, proj m out from the hall's wall Pw): the low gable over its face, the
    dressed-stone coping along it that turns level at the ends and roofs the porch back to the wall, its sides, and the
    hall's wall from the eaves zw up to the storey's top zt"""
    import landmarks as LM
    k = 0.35                                     # the level returns of the coping at the eaves
    mb.face([P(fa + k, zw), P(fb - k, zw), P(sc, zg)], wall)
    m, ex = (zg - zw) / (sc - fa - k), 0.05      # (the slopes run on a little past the apex, closing the joint)
    for sa, za, sb, zb_, ends in ((fa - 0.1, zw, fa + k + 0.1, zw, True), (fa + k, zw, sc + ex, zg + m * ex, False),
                                  (sc - ex, zg + m * ex, fb - k, zw, False), (fb - k - 0.1, zw, fb + 0.1, zw, True)):
        LM.bar(mb, P, sa, za, sb, zb_, 0.22, -proj, 0.08, 'stone_trim', ends=ends)
    mb.quad(P(fa, zb, -proj), P(fa, zb, 0), P(fa, zw, 0), P(fa, zw, -proj), wall)          # sides
    mb.quad(P(fb, zb, 0), P(fb, zb, -proj), P(fb, zw, -proj), P(fb, zw, 0), wall)
    if zw < zt:
        LM.flat_wall(mb, Pw, s0, s1, zw, zt, wall)


def porch(mb, a, b, s0, s1, zf, fh, st, style, opts=None):
    """Fill the ground-floor bay [s0, s1] of the wall a->b with the hall's front door: the wall round a recessed
    opening, its glazing and a lit hall behind it (the shells have no rooms), a canopy (or 빌링슬리관's gabled porch),
    and the flight down to the ground in front (walkable, landmarks.stair_flight)."""
    import landmarks as LM
    opts = opts or {}
    E = dict(ENTRY[style])
    span = opts.get('span', 1)
    if span > 1:                     # a door of several bays (과학관): glass the width of the bays less a pier each side
        E['w'] = (s1 - s0) - 1.2
        E['canopy'] = opts.get('canopy', E.get('canopy', 2.0))
    P, L, t, n = LM.edge_P(a, b)
    wall = st['wall']
    sc = (s0 + s1) / 2
    w = min(E['w'], s1 - s0 - 0.5)
    o0, o1 = sc - w / 2, sc + w / 2
    zt = zf + fh
    fa, fb, zb = s0, s1, zf                     # the face the door is in
    proj = E.get('porch', 0.0)
    if proj:
        # 빌링슬리관 (the 1996 album photo): the door is in a porch standing out from the wall, wider than the bay by
        # half a pier each side; the door, its flight and the dressed stone go on the porch's face
        Pw = P
        P = lambda s, z, d=0.0: Pw(s, z, d + proj)
        fa, fb, zb = s0 - 0.3, s1 + 0.3, zf - 1.0
    g = max(ground(*P(sc + u, 0, k)[:2]) for u in (-w / 2, 0.0, w / 2) for k in (0.6, 1.6))
    zd = max(zf + 0.12, g + (0.16 if style == 'house' else 0.32))     # threshold: a riser or two over the ground
    if E['kind'] == 'arch':
        zs = zd + E['spring']
        apex = max(z for _, z in LM.arch_points(o0, o1, zs, 'tudor', 14))
        zd = min(zd, zt - 0.35 - (apex - zd))
        zs = zd + E['spring']
        zo = max(z for _, z in LM.arch_points(o0, o1, zs, 'tudor', 14))
    else:
        # (a door on rising ground gets lower, rather than cutting into the storey above; where the ground would then
        # cover the landing at the flight's ends, as on a cross slope before 특별병동 and 국제학사, the transom over the
        # door thins, down to 0.1 m, for the sill to clear it by 0.1 m)
        top = E.get('top', 0.0)
        cap = zt - 0.25 - 2.15 - top
        if zd > cap and top > 0.1:
            fw_ = opts.get('stair_w', w + 0.9)
            ld_ = MUSIC_CANOPY if opts.get('music') else opts.get('landing', 1.6)
            ge = max(ground_top(*P(sc + u, 0, k)[:2]) for u in (-fw_ / 2, fw_ / 2) for k in (0.3, ld_ / 2, ld_))
            thin = min(top - 0.1, ge + 0.1 - cap) if ge > cap - 0.02 else 0.0
            top, cap = top - thin, cap + thin
        zd = min(zd, cap)
        zo = zd + min(E['h'], zt - 0.25 - zd - top) + top
    rec = E['rec']
    zw = zt                                     # the top of the face round the door
    if proj:
        # the porch's gable: its eaves over the arch's dressed stone, its apex under the sill of the window above
        zw = zo + 0.5
        zg = max(zw + 0.15, min(zw + 0.25 * ((fb - fa) / 2 - 0.35), zt + st['sill'] - 0.35))
    # wall round the opening, and the reveals
    LM.flat_wall(mb, P, fa, o0, zb, zw, wall)
    LM.flat_wall(mb, P, o1, fb, zb, zw, wall)
    LM.flat_wall(mb, P, o0, o1, zb, zd, wall)
    rv = st.get('trim', wall) if E['kind'] != 'glass' else 'concrete'
    if E['kind'] == 'arch':
        LM.arch_fill(mb, P, o0, o1, zs, zw, rec, wall, 'tudor', 14, intrados_mat='stone_trim')
        for s, sg in ((o0, 1), (o1, -1)):
            q = [P(s, zd, 0), P(s, zd, -rec), P(s, zs, -rec), P(s, zs, 0)]
            mb.face(q if sg < 0 else q[::-1], 'stone_trim')
        LM.glazed_door(mb, P, o0, o1, zd, zs, 'tudor', -rec, style='panel')
        # dressed stone round the arch
        pts = LM.arch_points(o0 - 0.22, o1 + 0.22, zs, 'tudor', 14)
        for (sa, za), (sb, zb_) in zip(pts, pts[1:]):
            LM.bar(mb, P, sa, za, sb, zb_, 0.26, 0.0, 0.05, 'stone_trim')
        for s in (o0 - 0.11, o1 + 0.11):
            LM.bar(mb, P, s, zd, s, zs, 0.22, 0.0, 0.05, 'stone_trim')
        if proj:
            porch_gable(mb, P, Pw, fa, fb, sc, zb, zw, zg, proj, s0, s1, zt, wall)
        LM.vestibule(mb, P, o0, o1, zd, zo + 0.05, -rec - 0.03, 2.4, lights=1)
    else:
        mb.quad(P(o0, zo, 0), P(o1, zo, 0), P(o1, zt, 0), P(o0, zt, 0), wall)
        mb.quad(P(o1, zo, 0), P(o0, zo, 0), P(o0, zo, -rec), P(o1, zo, -rec), rv)        # head
        for s, sg in ((o0, 1), (o1, -1)):
            q = [P(s, zd, 0), P(s, zd, -rec), P(s, zo, -rec), P(s, zo, 0)]
            mb.face(q if sg < 0 else q[::-1], rv)
        if E['kind'] == 'house':
            mb.quad(P(o0, zd, -rec), P(o1, zd, -rec), P(o1, zo, -rec), P(o0, zo, -rec), 'wood_dark')
            LM.bar(mb, P, o1 - 0.12, zd + 0.95, o1 - 0.12, zd + 1.05, 0.05, -rec, -rec + 0.06, 'frame_silver', ends=True)
        else:
            LM.shopfront(mb, P, o0, o1, zd, zo, -rec, bays=4 if opts.get("music") else 4 * span, door_h=min(E['h'], zo - zd - top) - 0.15)
            LM.vestibule(mb, P, o0, o1, zd, zo, -rec - 0.03, 2.8, lights=1)
        # a flat canopy over the door: a cantilevered slab with a thin fascia
        cd = E['canopy']
        ang = math.atan2(t.y, t.x)
        zc = zo + 0.12
        if opts.get('music'):
            music_canopy(mb, P, sc, w, zc, ang, zd)
        else:
            ct = opts.get('canopy_t', 0.22)          # (경영학교실단's thick flat canopy: 0.4)
            c = P(sc, zc + ct / 2, cd / 2)
            mb.box(c, (w + (1.6 if style != 'house' else 0.5), cd, ct), 'concrete', rotz=ang)
            if style != 'house':
                c2 = P(sc, zc + ct + 0.05, cd - 0.05)
                mb.box(c2, (w + 1.6, 0.1, 0.12), 'concrete_dark', rotz=ang)
    # the flight down to the ground: in a frame at the door (local -y outwards, x along the wall, z from the sill)
    ang = math.atan2(t.y, t.x)
    o = P(sc, zd, 0)
    mb.xf = Matrix.Translation(Vector(o)) @ Matrix.Rotation(ang, 4, 'Z')
    gfn = LM.local_ground(mb)
    drop = -min(gfn(u, -k) for u in (-w / 2, 0, w / 2) for k in (2.0, 3.5))
    fw = opts.get('stair_w', w + (0.9 if style != 'house' else 0.5))
    big = drop > 0.95
    n0 = len(LM.ENTRANCES)
    music = opts.get('music')
    # (options where the photos give them: the counted risers and their tread, the landing's depth, the side walls)
    landing = MUSIC_CANOPY if music else opts.get('landing', 1.6 if style != 'house' else 1.0)
    y_foot = LM.stair_flight(mb, 0.0, 0.0, fw, 0.0, landing=landing, tread=opts.get('tread', 0.34), flare=0.25 if big else 0.1,
                             cheek=(0.45 if 'stair_w' in opts else 0.32) if big and style != 'house' and not music else 0.0,
                             cheek_mat=opts.get('side', E['side']), newel=big and E['kind'] == 'arch',
                             rail=drop > 1.3 and E['kind'] == 'glass', gfn=gfn, mat=E['step'], maxrise=0.17,
                             risers=opts.get('risers'))
    if music:
        music_planters(mb, fw, y_foot, gfn)
    if opts.get('lamp5'):
        lamp5(mb, fw / 2 - 1.3, -0.9, 0.0)
    DOORS.extend(LM.ENTRANCES[n0:])
    del LM.ENTRANCES[n0:]
    mb.xf = Matrix.Identity(4)


def entry_edge(poly, entry):
    """the edge of poly (CCW) that the door point of build_campus.py lies on, and how far along it"""
    if not entry:
        return None
    p, nn = Vector(entry['p']), Vector(entry['n'])
    best = None
    for i in range(len(poly)):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % len(poly)])
        t = b - a
        L = t.length
        if L < 3.0:
            continue
        t /= L
        n = Vector((t.y, -t.x))
        if n.dot(nn) < 0.8:
            continue
        d = abs((p - a).dot(n))
        s = (p - a).dot(t)
        if d > 4.0 or s < -1.0 or s > L + 1.0:
            continue
        if best is None or d < best[0]:
            best = (d, i, min(max(s, 1.5), L - 1.5))
    return best and (best[1], best[2])


def parapet_and_roof(mb, poly, zt, st, rnd, roof_mat='roof_flat', clutter=True):
    inner = offset_poly(poly, -0.3)
    zp = zt + 0.9
    # coping
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ia, ib = inner[i], inner[(i + 1) % n]
        mb.quad((a[0], a[1], zp), (b[0], b[1], zp), (ib[0], ib[1], zp), (ia[0], ia[1], zp), 'concrete')
        mb.quad((ib[0], ib[1], zt), (ia[0], ia[1], zt), (ia[0], ia[1], zp), (ib[0], ib[1], zp), st['wall'] if st['wall'] != 'stone_rubble' else 'concrete')
    mb.face([(p[0], p[1], zt) for p in inner], roof_mat)
    if not clutter:
        return
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    area = abs(poly_area(poly))
    if area > 200:
        # stair penthouse
        _, _, L, W, ang = min_area_rect(poly)
        mb.box((cx, cy, zt + 1.6), (min(6, L * 0.3), min(4, W * 0.4), 3.2), st['wall'], rotz=ang,
               mats={'top': 'roof_flat'})
        for k in range(rnd.randint(1, 4)):
            ox, oy = rnd.uniform(-L * 0.3, L * 0.3), rnd.uniform(-W * 0.25, W * 0.25)
            x = cx + ox * math.cos(ang) - oy * math.sin(ang)
            y = cy + ox * math.sin(ang) + oy * math.cos(ang)
            mb.box((x, y, zt + 0.6), (1.6, 1.0, 1.2), 'metal', rotz=ang, skip=('bottom',))


def hip_roof(mb, cx, cy, L, W, ang, zt, mat, pitch=0.6, over=0.5, fascia='frame_white', gable=None):
    """A hipped roof over the L x W rectangle at (cx, cy), its ridge along ang; gable: the end walls' material, for a
    gabled roof instead (the ridge runs the whole length, the end walls go up to it, the roof sails `over` past them)"""
    L2, W2 = L / 2 + over, W / 2 + over
    h = W2 * pitch
    c, s = math.cos(ang), math.sin(ang)

    def P(x, y, z):
        return (cx + x * c - y * s, cy + x * s + y * c, z)
    r = L2 if gable else max(0.0, L2 - W2)
    z0 = zt - over * pitch
    A, B, C, D = P(-L2, -W2, z0), P(L2, -W2, z0), P(L2, W2, z0), P(-L2, W2, z0)
    zr = z0 + h
    R1, R2 = P(-r, 0, zr), P(r, 0, zr)
    mb.face([A, B, R2, R1], mat)
    mb.face([C, D, R1, R2], mat)
    if gable:
        for x in (-L / 2, L / 2):                    # the gables
            q = [P(x, -W / 2, zt), P(x, W / 2, zt), P(x, 0, zr)]
            mb.face(q if x > 0 else q[::-1], gable)
        mb.face([R1, R2, B, A], 'plaster_white')      # the undersides (seen under the verges and the eaves)
        mb.face([R2, R1, D, C], 'plaster_white')
        for p, q in ((A, B), (C, D), (B, R2), (R2, C), (D, R1), (R1, A)):
            mb.quad(p, q, (q[0], q[1], q[2] - 0.25), (p[0], p[1], p[2] - 0.25), fascia)
        return
    mb.face([B, C, R2], mat)
    mb.face([D, A, R1], mat)
    # soffit + fascia
    mb.face([D, C, B, A], 'plaster_white')
    for p, q in ((A, B), (B, C), (C, D), (D, A)):
        mb.quad(p, q, (q[0], q[1], q[2] - 0.25), (p[0], p[1], p[2] - 0.25), fascia)


def barrel_roof(mb, cx, cy, L, W, ang, zt, rise=0.22, seg=12):
    """체육관 (1960): a reinforced-concrete arched (barrel-vaulted) roof spanning the short side, with arched end walls."""
    c, s = math.cos(ang), math.sin(ang)
    P = lambda x, y, z: (cx + x * c - y * s, cy + x * s + y * c, z)
    h = W * rise
    prof = [(-W / 2 + W * k / seg, zt + h * math.sin(math.pi * k / seg)) for k in range(seg + 1)]
    for (y0, z0), (y1, z1) in zip(prof, prof[1:]):
        mb.quad(P(-L / 2 - 0.4, y0, z0), P(-L / 2 - 0.4, y1, z1), P(L / 2 + 0.4, y1, z1), P(L / 2 + 0.4, y0, z0), 'metal')
    for x in (-L / 2, L / 2):           # arched gable ends
        for (y0, z0), (y1, z1) in zip(prof, prof[1:]):
            mb.quad(P(x, y0, zt), P(x, y1, zt), P(x, y1, z1), P(x, y0, z0), 'concrete')


# ----------------------------------------------------------------------------- rooftop features the outlines cannot say
def dome_tower(mb, c, ang, zt, st, T, Ht, R, seg, rings, slit, drum, win, seam=0.04, phase=0.0):
    """A square tower T a side and Ht over the roof zt at c (its sides along ang), with a window (half width, sill and
    head over the roof) in three faces, carrying a silver dome R in radius on a white drum `drum` tall: gores of the
    shell, the gores `slit` dark (the observing slit, running up over the top), raised seams between every other two."""
    zb = zt + Ht
    mb.box((c.x, c.y, zt + Ht / 2), (T, T, Ht), st['wall'], rotz=ang, mats={'top': 'roof_flat'}, skip=('bottom',))
    mb.box((c.x, c.y, zb + 0.12), (T + 0.3, T + 0.3, 0.24), 'concrete', rotz=ang, skip=('bottom',))   # coping
    cs, sn = math.cos(ang), math.sin(ang)
    L = lambda u, v, z: (c.x + u * cs - v * sn, c.y + u * sn + v * cs, z)     # u along ang, v to its right
    hw, z0, z1 = win
    for (u, v, nu, nv) in ((0, T / 2, 0, 1), (-T / 2, 0, -1, 0), (T / 2, 0, 1, 0)):
        tu, tv = -nv, nu
        p = lambda s, z, d=0.02: L(u + tu * s + nu * d, v + tv * s + nv * d, z)
        mb.quad(p(-hw, zt + z0), p(hw, zt + z0), p(hw, zt + z1), p(-hw, zt + z1), st['glass'])
    mb.cylinder((c.x, c.y), R + 0.1, zb + 0.24, zb + 0.24 + drum, 'paint_white', seg=seg, cap_top=False)
    za = zb + 0.24 + drum
    a_ = ang + phase
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        dark = i in slit
        for j in range(rings):
            t0, t1 = math.pi / 2 * j / rings, math.pi / 2 * (j + 1) / rings
            q = lambda a, t: (c.x + R * math.cos(t) * math.cos(a + a_), c.y + R * math.cos(t) * math.sin(a + a_),
                              za + R * math.sin(t))
            mb.face([q(a0, t0), q(a1, t0), q(a1, t1), q(a0, t1)], 'metal_dark' if dark else 'lamp_housing',
                    smooth='obs_dome' if not dark else False)
    for i in range(0, seg, 2):
        a = 2 * math.pi * i / seg + a_
        for j in range(rings):
            t0, t1 = math.pi / 2 * j / rings, math.pi / 2 * (j + 1) / rings
            r0 = r1 = R + 0.03
            p0 = (c.x + r0 * math.cos(t0) * math.cos(a), c.y + r0 * math.cos(t0) * math.sin(a), za + r0 * math.sin(t0))
            p1 = (c.x + r1 * math.cos(t1) * math.cos(a), c.y + r1 * math.cos(t1) * math.sin(a), za + r1 * math.sin(t1))
            dx, dy = -math.sin(a) * seam, math.cos(a) * seam
            mb.quad((p0[0] - dx, p0[1] - dy, p0[2]), (p0[0] + dx, p0[1] + dy, p0[2]),
                    (p1[0] + dx, p1[1] + dy, p1[2]), (p1[0] - dx, p1[1] - dy, p1[2]), 'frame_silver')


def observatory(mb, b, zt, st):
    """과학관's two domes on its east wing (zt: the wing's roof).  The observatory (reference/학교연혁_과학관.jpg,
    top right; reference/활천대_2009_연세춘추.jpg, far left): a square white tower near the east end carrying a
    silver dome with an observing slit.  Measured (reference/고증.md 3.10): the 1994 aerial photo with its fitted
    camera (tools/photofit) has the dome 5.6 m across at half brightness, its centre 10 m west of the east face, the
    tower's top 4.7 m over the parapet; three 2010 roadview panoramas from the south (1016786788 · 7072 · 7073) 5.1 -
    5.4 m, the dome 0.83 - 0.86 of the tower as seen.  So a 5.4 m dome on a 5.6 m tower, its top 8.5 m over the roof.
    And near the junction with the front block a small tower with a small silver dome (학교연혁_과학관.jpg, x 213
    y 55 in the 454 px print; the 2010 roadview from the south, a dome of 1.5 - 2 m 1 - 5 m west of the junction; the
    1994 photo, a narrow white post 2.2 - 2.6 m wide 7 m west of it, and a white tower with a rounded top 17 m west):
    the old proportions to the large one (3.6 m on a 4.4 m tower against 7.6 on 9) scaled with it, 2.6 m on a 2.8 m
    tower, 4.5 m west of the junction."""
    fp = b['footprint']
    e0, e1 = Vector(fp[0]), Vector(fp[1])                # the east face of the east wing (south -> north)
    w = (Vector(fp[14]) - e0).normalized()               # along the wing, westwards
    ang = math.atan2(w.y, w.x)
    # (the slit two gores wide, facing south-west: u westwards, v southwards)
    dome_tower(mb, (e0 + e1) / 2 + w * 10.0, ang, zt, st, T=5.6, Ht=5.0, R=2.7, seg=24, rings=7, slit=(5, 6),
               drum=0.51, win=(0.4, 2.2, 3.6))
    # the small one west of the junction with the front block (whose east face meets the wing 49.5 m from its east
    # face), its slit one gore wide, the same way
    dome_tower(mb, (e0 + e1) / 2 + w * ((Vector(fp[14]) - e0).length + 4.5), ang, zt, st, T=2.8, Ht=4.4, R=1.3,
               seg=16, rings=5, slit=(4,), drum=0.25, win=(0.25, 1.8, 3.1), seam=0.02, phase=-math.pi / 16)


def _science_wing(b, poly):
    """과학관's east wing stands a storey over the front block (reference/고증.md 3.10: seven rows of windows at its east
    end in the 1994 aerial photo and the 2008 · 2010 roadview, six on the front block's south face, two of the wing's
    rows over the front block's roof at the junction in the 1994 photo).  The wing: a slab from the east face
    (footprint[0] -> [1]) west to footprint[2], as deep as the east face is long.  Returns the outline's edges that
    run its full height (as vertex pairs), the wing's own outline (CCW) and its two walls over the lower roof."""
    fp = [tuple(p) for p in b['footprint']]
    e0, e1, nw, j = Vector(fp[0]), Vector(fp[1]), Vector(fp[2]), Vector(fp[14])
    w = (j - e0).normalized()                            # westwards along the wing
    n = Vector((-w.y, w.x))                              # northwards across it
    if n.dot(e1 - e0) < 0:
        n = -n
    sw = nw - n * (nw - e0).dot(n)                       # its south-west corner, on the south face's line
    sw = (sw.x, sw.y)
    full = {frozenset((fp[14], fp[0])), frozenset((fp[0], fp[1])), frozenset((fp[1], fp[2]))}
    return full, [fp[0], fp[1], fp[2], sw], [(fp[2], sw), (sw, fp[14])]


ROOF_EXTRAS = {222843398: observatory}
# 과학관: cream square glazed tiles, about ten to a window bay (the 1996 album photos reference/과학관_계단_1996_*.jpg;
# the 2008 roadview, 200 mm tiles); 음악관 신관: white square tiles with grey joints (기악과's 1996 album photo at its
# door; reference/학교연혁_음악관.jpg still shows them); 구관: smooth white panels (the 2008 roadview, 2381382 - 2381391)
WALL = {222843398: 'tile_cream', 429077789: 'panel_white', 429077790: 'tile_white'}
WALL.update({990021: 'plaster_white', 990022: 'plaster_white'})   # (경영학교실단's south wing and front: as its north wing)
FRAME = {429077789: 'frame_blue', 429077790: 'frame_blue'}      # (and blue window frames in the 1996 photo)
# per hall: its storey height and window heights instead of its style's, and a wing a storey higher (_science_wing).
# 과학관: 4.1 m storeys (the 1994 aerial photo's camera: 4.06 - 4.13 m a row; the 2008 roadview square on to the east
# face, 2.1 window bays a storey), windows 1.8 m high (0.44 of the storey in the 2008 roadview)
FH_AT = {222843398: 4.1}
SILL_AT = {222843398: dict(sill=1.0, head=1.3)}
WING_UP = {222843398: _science_wing}
# 학생회관 별관 (1997 photo reference/1997_학생회관.jpg; tools/build_campus.py ANNEX_1997): two 3.8 m storeys of pale
# grey concrete, each a band of broad lights between plain piers (the shops and the bank of the 2008 roadview below,
# the same band above), a plain parapet.  (Its colour draw is still made: the halls after it keep theirs.)
WALL[1444448646] = 'concrete'
FH_AT[1444448646] = 3.8
# 심장혈관병원 · 특별병동 (ten storeys each): their roofs in the 1997 aerial photos stand 34.3 m and 32 m over the car
# parks beside them (tools/build_campus.py FLOOR_H_AT; reference/고증/3.1.2)
FH_AT.update({324328481: 3.55, 990036: 3.3})
SILL_AT[1444448646] = dict(bay=4.2, ww=0.84, sill=0.85, head=0.55, mull=2, depth=0.3)
# 연합신학대학원 (1964 - 2003; tools/build_campus.py UTS, reference/고증/3.1 「3.1.1」): the 1997 aerial photos have
# one pale roof, a ridge down its middle from end to end (the east half lighter in every frame), the eaves 6.7 m over
# the ground and the ridge 2.5 - 3 m over them: a low gabled roof (the 1990 and 1994 maps draw a gable), two storeys
# of 3.4 m.  (Like the hipped roof it had, it draws nothing from rnd.)
ROOF_AT = {246156121: dict(mat='roof_cement', pitch=0.45, gable=True)}
FH_AT[246156121] = 3.4


def build_generic(b, rnd):
    style = b['style']
    st = dict(STYLE[style])
    st['name'] = style                 # (blender/windows.py)
    poly = [tuple(p) for p in b['footprint']]
    if poly_area(poly) < 0:
        poly.reverse()
    fh = FH_AT.get(b['id'], FH[style])
    st.update(SILL_AT.get(b['id'], {}))
    z0 = b['base']
    nf = b['levels']
    mb = MeshBuilder('bld_%s' % b['id'])
    if style == 'city':
        st['wall'] = rnd.choice(['brick_red', 'brick_red', 'plaster_cream', 'tile_facade', 'plaster_grey'])
        st['frame'] = 'frame_silver'
    elif style == 'white' and rnd.random() < 0.3:
        st['wall'] = 'plaster_cream'
    if b['id'] in WALL:
        st['wall'] = WALL[b['id']]
    if b['id'] in FRAME:
        st['frame'] = FRAME[b['id']]
    pitched = style in ('stone', 'house', 'stone_pale')
    if pitched or style == 'gym':
        cx, cy, L, W, ang = min_area_rect(poly)
        c, s = math.cos(ang), math.sin(ang)
        poly = [(cx + x * c - y * s, cy + x * s + y * c) for x, y in ((-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2))]
    zt = z0 + nf * fh
    if style == 'gym':
        nf, fh = 1, nf * fh
    shop = style == 'city' and rnd.random() < 0.45
    door = entry_edge(poly, b.get('entry')) if style in ENTRY else None
    wing = WING_UP[b['id']](b, poly) if b['id'] in WING_UP else None
    ups = [1 if wing and frozenset((poly[i], poly[(i + 1) % len(poly)])) in wing[0] else 0 for i in range(len(poly))]
    # the backs and feet of the walls (blender/backs.py: its own random stream, nothing drawn from rnd)
    n_doors = len(DOORS)
    back = backs.back_plan(b, poly, st, fh, z0, zt, nf, door, shop, pitched=pitched, ups=ups,
                           tops=[zt - backs.EAVE * backs.PITCH[style] if pitched else zt + up * fh for up in ups])
    for i in range(len(poly)):
        up = ups[i]
        wall_edge(mb, poly[i], poly[(i + 1) % len(poly)], z0, (zt if pitched else zt + 0.9) + up * fh, nf + up, fh,
                  st, rnd, ground_floor_shop=shop, door=(door[1], style, b['entry']) if door and door[0] == i else None,
                  back=back.edges[i].back if back.on else None)
    if wing:
        for a_, b_ in wing[2]:          # the wing's storey over the lower roof
            wall_edge(mb, a_, b_, zt, zt + fh + 0.9, 1, fh, st, rnd, found=False)
        parapet_and_roof(mb, wing[1], zt + fh, st, rnd, clutter=False)
    if pitched and b['id'] in ROOF_AT:
        ra = ROOF_AT[b['id']]
        hip_roof(mb, cx, cy, L, W, ang, zt, ra['mat'], pitch=ra['pitch'], gable=st['wall'] if ra.get('gable') else None)
    elif pitched:
        hip_roof(mb, cx, cy, L, W, ang, zt, rnd.choice(['roof_slate', 'roof_giwa']) if style == 'house' else 'roof_slate',
                 pitch=0.55 if style == 'house' else 0.75)
    elif style == 'gym':
        barrel_roof(mb, cx, cy, L, W, ang, zt)
    else:
        roof = 'roof_green' if (style == 'city' and rnd.random() < 0.6) else 'roof_flat'
        parapet_and_roof(mb, poly, zt, st, rnd, roof_mat=roof, clutter=style != 'city')
        if b['id'] in ROOF_EXTRAS:
            ROOF_EXTRAS[b['id']](mb, b, zt + (fh if wing else 0.0), st)
        if style == 'city':
            n = len(poly)
            cx = sum(p[0] for p in poly) / n
            cy = sum(p[1] for p in poly) / n
            if rnd.random() < 0.7:     # rooftop water tank
                mb.cylinder((cx + rnd.uniform(-1, 1), cy + rnd.uniform(-1, 1)), 0.75, zt, zt + 1.5,
                            rnd.choice(['metal', 'paint_blue', 'metal_green']), seg=10)
            if shop:
                # 1990s shop sign band on the longest edge
                best = max(range(n), key=lambda i: (Vector(poly[(i + 1) % n]) - Vector(poly[i])).length)
                a, bb = Vector(poly[best]), Vector(poly[(best + 1) % n])
                t = (bb - a)
                Lb = t.length
                t.normalize()
                nn = Vector((t.y, -t.x))
                k = rnd.randrange(16)
                u0, v0 = (k % 2) / 2, 1 - (k // 2 + 1) / 8
                sw = min(Lb - 0.6, 4.4)
                if sw > 1.5:
                    mid = (a + bb) / 2
                    p0 = mid - t * sw / 2 + nn * 0.12
                    p1 = mid + t * sw / 2 + nn * 0.12
                    zs0, zs1 = z0 + fh - 0.1, z0 + fh + 1.0
                    mb.face([(p0.x, p0.y, zs0), (p1.x, p1.y, zs0), (p1.x, p1.y, zs1), (p0.x, p0.y, zs1)], 'sign_shops',
                            uvs=[(u0, v0), (u0 + 0.5, v0), (u0 + 0.5, v0 + 0.125), (u0, v0 + 0.125)])
    backs.back_finish(mb, back, DOORS[n_doors:])
    return mb
