"""The generic halls' windows (blender/generic.py wall_edge): their glass, a sash slid open now and then, and the odd
air conditioner.

A sash window -- an ordinary window of a hall or a town house, not a shop front or the gym's clerestory -- gets pane
uvs from common.SASH, and one in common.OPEN_P of them has a sash slid open: the light under the transom on the half
common.pane_open names.  The web app's glass shader (web/src/materials.js windowGlass) draws that part of the pane
without the glass (no reflection, the room dim behind it); here it is set back into the room with the reveal running
on to it, so that it has depth seen from the side.  The rest of that window is split off with its own uvs, kept clear
of the half and the transom so that the shader's test cannot flicker at their edges.

Air conditioners were still few in 1997: in one in AC_P of the sash windows of the postwar halls and the town, a
window unit stands in the foot of one light, or a split unit's outdoor box hangs on brackets under the sill (from the
second storey up) with its pipe running in over the sill.  50 x 40 x 30 cm, a fan or louvres behind a grille; drawn
in materials the halls already have (the window frames, the sills' stone, the glass's dark opening at v < 0) so that
they add no draw call.
"""
import math
from mathutils import Vector
from common import pane_cell, pane_open, pane_hash, TRANSOM, _odz

TRANSOM_AT = 0.72      # generic.wall_edge: the transom bar's height up the window
RECESS = 0.32          # m: how far the open part is set back behind the glass
AC_P = 0.015           # share of the sash windows with an air conditioner
AC_STYLES = ('modern', 'white', 'brick', 'tile', 'city')
CASE = 'stone_trim'    # the units' casing: a light grey present on nearly every hall (the sills)
DARK = (0.5, -0.5)     # glass uv of a dark opening (materials.js windowGlass: v < 0)
E = 0.03               # uv margin off the open half and the transom (Draco quantises the uvs to ~0.01)


def glass(mb, P, w0, w1, zs, zh, d, st, shop):
    """The glass of the window [w0, w1] x [zs, zh] at depth d of the wall P.  Returns the pane cell of a sash window
    (for aircon), else None."""
    name = st.get('name')
    hall = shop or name == 'gym'
    sash = not hall
    q = [P(w0, zs, -d), P(w1, zs, -d), P(w1, zh, -d), P(w0, zh, -d)]
    panes = (1, 1, hall, sash)
    if not sash:
        mb.quad(*q, st['glass'], panes=panes)
        return None
    ox, oy = pane_cell([mb.xf @ Vector(p) for p in q], panes)
    side = pane_open(ox, oy)
    if side is None:
        mb.quad(*q, st['glass'], panes=panes)
        return ox, oy
    # the lights: as wall_edge draws its mullions; one light alone slides in two halves (and gets a meeting stile)
    ww = w1 - w0
    nm = st['mull']
    lights = 1 if (nm == 1 and ww < 1.0) else nm + 1
    k = 0.5 if lights == 1 else 1.0 / lights
    zt = zs + (zh - zs) * TRANSOM_AT
    a, b = (w0, w0 + ww * k) if side == 0 else (w1 - ww * k, w1)        # the open light
    c0, c1 = (b, w1) if side == 0 else (w0, a)                           # the shut rest under the transom
    ua = (E, 0.5 - E) if side == 0 else (0.5 + E, 1 - E)                 # their uv fractions
    uc = (0.5 + E, 1 - E) if side == 0 else (E, 0.5 - E)
    vb, vt = (E, TRANSOM - E), (TRANSOM + E, 1 - E)

    def uvq(u, v):
        return [(ox + u[0], oy + v[0]), (ox + u[1], oy + v[0]), (ox + u[1], oy + v[1]), (ox + u[0], oy + v[1])]
    g = st['glass']
    mb.quad(P(w0, zt, -d), P(w1, zt, -d), P(w1, zh, -d), P(w0, zh, -d), g, uvs=uvq((E, 1 - E), vt))
    mb.quad(P(c0, zs, -d), P(c1, zs, -d), P(c1, zt, -d), P(c0, zt, -d), g, uvs=uvq(uc, vb))
    # the open light: the room set back behind it, the reveal running on to it
    r, rv = -d - RECESS, st.get('trim', st['wall'])
    mb.quad(P(a, zs, r), P(b, zs, r), P(b, zt, r), P(a, zt, r), g, uvs=uvq(ua, vb))
    mb.quad(P(a, zt, -d), P(a, zs, -d), P(a, zs, r), P(a, zt, r), rv)
    mb.quad(P(b, zt, r), P(b, zs, r), P(b, zs, -d), P(b, zt, -d), rv)
    mb.quad(P(a, zs, -d), P(b, zs, -d), P(b, zs, r), P(a, zs, r), rv)
    mb.quad(P(a, zt, r), P(b, zt, r), P(b, zt, -d), P(a, zt, -d), rv)
    if lights == 1:                                                      # the shut sash's stile
        sb, fw, dd = (b if side == 0 else a), 0.05, -d + 0.05
        box(mb, P, sb - fw, sb + fw, zs, zt, -d, dd, st['frame'],
            skip=('back', 'top', 'bottom', 'left' if side else 'right'))
    return ox, oy


def box(mb, P, s0, s1, z0, z1, d0, d1, mat, skip=()):
    """a box over [s0, s1] x [z0, z1] x [d0, d1] of the wall P (d outwards), its faces wound outwards"""
    f = {'front': [P(s0, z0, d1), P(s1, z0, d1), P(s1, z1, d1), P(s0, z1, d1)],
         'back': [P(s0, z1, d0), P(s1, z1, d0), P(s1, z0, d0), P(s0, z0, d0)],
         'top': [P(s0, z1, d1), P(s1, z1, d1), P(s1, z1, d0), P(s0, z1, d0)],
         'bottom': [P(s0, z0, d0), P(s1, z0, d0), P(s1, z0, d1), P(s0, z0, d1)],
         'left': [P(s0, z1, d0), P(s0, z0, d0), P(s0, z0, d1), P(s0, z1, d1)],
         'right': [P(s1, z1, d1), P(s1, z0, d1), P(s1, z0, d0), P(s1, z1, d0)]}
    for k, q in f.items():
        if k not in skip:
            mb.face(q, mat)


def grille(mb, P, s0, s1, z0, z1, d, bars):
    """a dark opening over [s0, s1] x [z0, z1] on the face at d with `bars` bars of the casing across it (louvres)"""
    mb.quad(P(s0, z0, d + 0.004), P(s1, z0, d + 0.004), P(s1, z1, d + 0.004), P(s0, z1, d + 0.004), 'glass',
            uvs=[DARK] * 4)
    for i in range(bars):                                                # (their front faces: a few px at most)
        z = z0 + (z1 - z0) * (i + 1) / (bars + 1)
        box(mb, P, s0, s1, z - 0.012, z + 0.012, d, d + 0.012, CASE, skip=('back', 'top', 'bottom', 'left', 'right'))


def fan(mb, P, sc, zc, r, d):
    """an outdoor unit's round fan behind its grille: a dark disc on the face at d, bars of the casing across it"""
    ring = [math.pi * (2 * k + 1) / 12 for k in range(12)]
    mb.face([P(sc + r * math.cos(a), zc + r * math.sin(a), d + 0.004) for a in ring], 'glass', uvs=[DARK] * 12)
    front = ('back', 'top', 'bottom', 'left', 'right')
    for y in (-0.5 * r, 0.0, 0.5 * r):
        w = math.sqrt(r * r - y * y) * 0.97
        box(mb, P, sc - w, sc + w, zc + y - 0.012, zc + y + 0.012, d, d + 0.012, CASE, skip=front)
    box(mb, P, sc - 0.012, sc + 0.012, zc - r * 0.97, zc + r * 0.97, d, d + 0.012, CASE, skip=front)


def aircon(mb, P, w0, w1, zs, zh, d, st, cell, floor):
    """now and then an air conditioner on the sash window [w0, w1] x [zs, zh] (pane cell from glass())"""
    if cell is None or st.get('name') not in AC_STYLES:
        return
    ox, oy = cell
    spot = P((w0 + w1) / 2, zs, 0)                                       # (by the window's own place, not its room)
    h = lambda k: pane_hash(int(round(spot[0] * 20)) * 31 + int(round((spot[2] + _odz(spot[2])) * 20)), int(round(spot[1] * 20)), k)
    if h(9) >= AC_P or pane_open(ox, oy) is not None:
        return
    ww = w1 - w0
    lights = 1 if (st['mull'] == 1 and ww < 1.0) else st['mull'] + 1
    lw = ww / (2 if lights == 1 else lights)
    W, H, D = min(0.5, lw - 0.1), 0.4, 0.3
    if W < 0.38:
        return
    left = h(10) < 0.5
    if floor > 0 and h(11) < 0.55:
        # a split unit's outdoor box on two steel brackets under the sill, its pipe in over the sill
        sc = w0 + ww * 0.25 if left else w1 - ww * 0.25
        s0, s1 = sc - W / 2, sc + W / 2
        z1 = zs - 0.11
        z0 = z1 - H
        d0, d1 = 0.04, 0.04 + D
        box(mb, P, s0, s1, z0, z1, d0, d1, CASE, skip=('back',))
        fan(mb, P, s0 + 0.035 + 0.155, (z0 + z1) / 2, 0.155, d1)
        for s in (s0 + 0.07, s1 - 0.07):                                 # triangular brackets, seen from either side
            A, B, C = P(s, z0, 0.0), P(s, z0, d1 - 0.02), P(s, z0 - 0.25, 0.0)
            mb.face([A, B, C], st['frame'])
            mb.face([A, C, B], st['frame'])
        sp = s1 - 0.08 if left else s0 + 0.08
        box(mb, P, sp - 0.025, sp + 0.025, z1, zs + 0.06, 0.13, 0.18, CASE, skip=('back', 'bottom', 'top'))
        box(mb, P, sp - 0.025, sp + 0.025, zs + 0.01, zs + 0.06, -d + 0.02, 0.13, CASE,
            skip=('bottom', 'back', 'front'))
    else:
        # a window unit standing in the foot of one light, against its side, out over the reveal
        s0 = w0 + 0.04 if left else w1 - 0.04 - W
        s1 = s0 + W
        z0, z1 = zs, zs + H
        d0, d1 = -d + 0.01, -d + 0.01 + D
        box(mb, P, s0, s1, z0, z1, d0, d1, CASE, skip=('back', 'bottom'))
        grille(mb, P, s0 + 0.04, s1 - 0.04, z0 + 0.04, z0 + 0.25, d1, 4)
        grille(mb, P, s0 + 0.04, s1 - 0.04, z0 + 0.29, z1 - 0.03, d1, 2)
