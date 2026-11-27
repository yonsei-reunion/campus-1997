"""The faces of the people as a few drawn lines: one small atlas that all of them share.

blender/characters.py lays the front of every face (a 15 cm square about the eyes) on its own cell of this atlas and
points everything else of the person at the blank cell, so a person stays one mesh with one material.  A cell holds
factors of the skin's light, not colours: the game (web/src/characters.js) multiplies the vertex colour with the
picture's colour, so 1 leaves the skin as it is, the lids' and the mouth's lines darken it and a brow is the brow's
colour over the skin's - whatever skin a person of the crowd gets, the lines stay lines.  Only the white of the eye
cannot be made of skin: the picture's alpha is how much of the skin (times the colour) shows, the rest is white.

The manner: few lines, a round and friendly face (reference/고증 4.9) - an upper lid drawn as one stroke, a large
dark iris with a spot of light on the white of the eye, a brow as one stroke, a small mouth as one line whose
corners turn up.  The eyes stand where they stand on a person and are a little larger than life.  A person's own
look is the slant of the eyes, the weight and the angle of the brows and the corners of the mouth (the `face` of
PEOPLE in characters.py).

A second, smaller atlas of the same cells (faces_rims.png) holds the glasses as drawn lines: how much of each pixel a
rim covers.  Rims of geometry a few millimetres thin are thinner than a pixel from a few metres off and, where nothing
smooths the edges (phones: no anti-aliasing), they glitter on and off from frame to frame; so from there on the game
draws the glasses of whoever wears them from this picture instead (web/src/characters.js), and the mip maps fade them.

    blender -b --factory-startup --python blender/characters.py -- faces       # only the atlases

Needs numpy only (Blender's Python has it), so the same code runs outside Blender.
"""
import struct
import zlib

import numpy as np

GRID = 5                   # cells a side (25: the people's faces, then free ones, the prints' and the blank one)
CELL = 256                 # pixels a cell
HALF = 0.075               # the frame of a cell on the face, in the source's units (men x 0.93, women x 0.90 in the
TOP = 0.042                # game): HALF either side of the nose, from TOP over the eye line down to TOP - 2 HALF
BLANK = GRID * GRID - 1    # the cell everything but a face points at: left white
PRINT = BLANK - 1          # the cell of what is printed on clothes (see PRINTS)
MARGIN = 0.004             # nothing is drawn, and no face of the mesh is mapped, this close to a cell's edge
RIM_CELL = 128             # pixels a cell of faces_rims.png
RIM_T = 0.0024             # the glasses: the rims' thickness (characters.py face_glasses builds them by the same)
RIM_DZ = -0.001            # the rims' middle under the eye line (characters.py checks it on the heads)
GLASSES = {'umc': (1.36, 1.02), 'women': (1.26, .92)}     # a rim's half width and height, of the eye's half width

# The features, as lengths on the face in the source's units (reference/고증 4.9 has them in the game's).
#   eye: half width, opening below the middle; lid: opening above the middle by the kind of eyelid (mono 홑꺼풀, inner
#   속쌍꺼풀, double 쌍꺼풀); iris: radius; gap: between the inner corners; slant: the outer corner higher (of the half
#   width); brow: height over the eye line, thickness at the head and at the tail, arch; mouth: half width, the line's
#   thickness; mouth_dz, nose_dz: the mouth and the underside of the nose under the eye line (measured on the heads:
#   characters.py checks them); lash: the upper lid's line at its thickest; lip: the lower lip's depth
#   chin: the jaw's length from the nose down, scaled, and cheek: the lower face's width, scaled (the packs' faces
#   are long, with a narrow jaw: characters.py head_clean makes them rounder)
FACE = {
    'umc': dict(eye=(.0168, .0046), lid=dict(mono=.0068, inner=.0078, double=.0088), iris=.0064, gap=.0384, slant=.07,
                brow=(.0246, .0056, .0026, .0028), mouth=(.0215, .0016), mouth_dz=-.0747, nose_dz=-.0521, lash=.0030,
                lip=.0054, chin=.87, chin0=.74, cheek=1.18),
    'women': dict(eye=(.0174, .0048), lid=dict(mono=.0074, inner=.0085, double=.0096), iris=.0068, gap=.0376, slant=.09,
                  brow=(.0242, .0056, .0028, .0040), mouth=(.0195, .0015), mouth_dz=-.0793, nose_dz=-.0595, lash=.0036,
                  lip=.0052, chin=1.05, chin0=.78, cheek=1.16),
}
# what the lines do to the skin's (linear) light
INK = (.030, .022, .022)           # the upper lid and the pupil
IRIS = (.085, .045, .030)          # the iris round the pupil: dark brown
WHITE = (.84, .83, .80)            # the white of the eye (linear light): the game's EYE_WHITE is the same
BLUSH = ((1.0, .80, .78), .30)     # a young woman's cheeks: tint, strength
LINE = (.42, .27, .24)             # the lower lid, the crease of a double eyelid, the lines of an older face
MOUTH = (.26, .11, .10)            # the line between the lips
LIP = {'umc': ((.88, .70, .68), .55), 'women': ((.86, .50, .50), .75)}     # the lower lip: tint, strength


def cell_origin(index):
    """The top left corner of a cell, as fractions of the atlas (x right, y down)."""
    return (index % GRID) / GRID, (index // GRID) / GRID


def uv(index, x, dz):
    """Where the point x (the person's left is +), dz (over the eye line) of a face lies on the atlas: (u, v) with v
    down from the top, as glTF counts it (Blender's v is 1 - v)."""
    u0, v0 = cell_origin(index)
    return u0 + (x + HALF) / (2 * HALF) / GRID, v0 + (TOP - dz) / (2 * HALF) / GRID


def in_frame(x, dz):
    return abs(x) < HALF - MARGIN and TOP - 2 * HALF + MARGIN < dz < TOP - MARGIN


def _linear(hex_):
    out = []
    for i in (1, 3, 5):
        c = int(hex_[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return np.array(out)


def _smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


class Canvas:
    """One cell: the factors of the skin's light at every pixel, drawn on in the face's own lengths."""

    def __init__(self, n=CELL):
        self.n = n
        self.px = 2 * HALF / n
        xs = -HALF + (np.arange(n) + 0.5) * self.px
        zs = TOP - (np.arange(n) + 0.5) * self.px
        self.X, self.Z = np.meshgrid(xs, zs)
        self.rgb = np.ones((n, n, 3))
        self.white = np.zeros((n, n))      # how much of the pixel is the white of the eye, not skin

    def ink(self, cover, tint, strength=1.0):
        """Darken (tint) the skin where `cover`; ink lies over the white of the eye."""
        c = np.clip(cover, 0.0, 1.0) * strength
        a = c[..., None]
        self.rgb *= 1 - a + a * np.asarray(tint)
        self.white *= 1 - c

    def whiten(self, cover):
        self.white = np.maximum(self.white, np.clip(cover, 0.0, 1.0))

    def stroke(self, pts, half, soft=1.0, window=False):
        """Coverage of a line through pts [(x, z)], `half` thick either side at each point; round ends; `soft`: the
        edge's blur in pixels.  window: only the rows and columns it lies in, as (rows, columns, coverage)."""
        pts, half = np.asarray(pts, float), np.asarray(half, float) * np.ones(len(pts))
        seg = np.hypot(*np.diff(pts, axis=0).T)
        s = np.concatenate([[0.0], np.cumsum(seg)])
        t = np.linspace(0.0, s[-1], max(2, int(s[-1] / (0.3 * self.px)) + 1))
        cx, cz, r = np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1]), np.interp(t, s, half)
        pad = r.max() + (soft + 1) * self.px
        i0 = max(0, int((cx.min() - pad + HALF) / self.px))
        i1 = min(self.n, int((cx.max() + pad + HALF) / self.px) + 2)
        j0 = max(0, int((TOP - cz.max() - pad) / self.px))
        j1 = min(self.n, int((TOP - cz.min() + pad) / self.px) + 2)
        X, Z = self.X[j0:j1, i0:i1], self.Z[j0:j1, i0:i1]
        d = np.full(X.shape, 1e9)
        for x, z, rr in zip(cx, cz, r):
            np.minimum(d, np.hypot(X - x, Z - z) - rr, out=d)
        cover = np.clip(0.5 - d / (soft * self.px), 0.0, 1.0)
        if window:
            return slice(j0, j1), slice(i0, i1), cover
        out = np.zeros((self.n, self.n))
        out[j0:j1, i0:i1] = cover
        return out

    def disc(self, x, z, r, soft=1.0):
        return np.clip(0.5 - (np.hypot(self.X - x, self.Z - z) - r) / (soft * self.px), 0.0, 1.0)

    def below(self, fn, soft=1.0):
        """Coverage of everything under the curve z = fn(x)."""
        return np.clip(0.5 + (fn(self.X) - self.Z) / (soft * self.px), 0.0, 1.0)


def eye_curves(f, face, sx):
    """The lids of one eye (sx: +1 the person's left): the middle's x, the half width, and the upper and the lower
    edge as z over t = -1 (the inner corner) .. 1 (the outer).  characters.py sets the glasses by the same."""
    k = face.get('eye', 1.0)
    wide = face.get('eye_open', 1.0)                        # (how far the lids part, of the kind's: narrow eyes less)
    hw, lo, up = f['eye'][0] * k, f['eye'][1] * k * wide, f['lid'][face.get('lid', 'inner')] * k * wide
    slant = face.get('slant', f['slant'])
    ex = sx * (f['gap'] / 2 + face.get('eyes_apart', 0.0) + hw)

    def top(t):
        t = np.clip(t, -1.0, 1.0)
        return up * (1 - t * t) ** 0.72 * (1 - 0.12 * t) + slant * hw * t

    def bot(t):
        t = np.clip(t, -1.0, 1.0)
        return -lo * (1 - t * t) ** 0.85 * (1 + 0.15 * t) + slant * hw * t

    return ex, hw, top, bot


# A brow is hairs on skin, not a band: at its head (over the inner corner of the eye) the hairs stand upright and
# apart, so the skin shows between them and the brow begins softly (`head`: over so much of its length, from
# `head_ink` of its weight); the body is densest; the tail thins to a point (`tail`: from there on, losing `point` of
# its thickness).  Seen from far it is not the hair's colour but hair and skin mixed (`far`: of the brow's colour);
# from near, a faint ground (`ground`) under the hairs themselves (`hairs`: so many a brow of weight 1).
BROW = dict(head=0.24, head_ink=0.48, tail=0.74, point=0.80, far=0.92, ground=0.76, hairs=400)


def brow_line(f, face, hw, slant):
    """A brow's middle line and its thickness along it: t (as eye_curves counts it along the eye), z over the eye
    line, the thickness."""
    bh, bt0, bt1, arch = f['brow']
    arch *= face.get('arch', 1.0)
    ts = np.linspace(0.0, 1.0, 33)
    t0 = -1.22 + face.get('brow_gap', 0.0) / hw
    t1 = -1.22 + 2.72 * face.get('brow_len', 1.0)
    length = (t1 - t0) * hw
    peak, corner = face.get('brow_peak', 0.62), face.get('brow_corner', False)
    tilt = face.get('brow_tilt', 0.0) + 0.15 * slant - 0.01
    rise = np.minimum(1.0, ts / peak)
    rise = rise if corner else np.sin(np.pi * rise / 2)
    fall = (np.maximum(0.0, ts - peak) / (1 - peak)) ** (1.15 if corner else 1.5)
    bz = bh + face.get('brow_up', 0.0) + arch * (0.35 + 0.65 * rise) \
        - arch * 1.35 * face.get('brow_drop', 1.0) * fall + tilt * (ts - 0.5) * length
    taper = face.get('brow_taper', 1.0)
    th = (bt0 + (bt1 * taper - bt0) * ts ** 1.3) * face.get('brow', 1.0) * (0.72 + 0.28 * _smooth(0.0, 0.12, ts)) \
        * (1 - BROW['point'] * _smooth(BROW['tail'], 1.0, ts))
    return t0 + (t1 - t0) * ts, bz, th


def brow_dense(ts):
    """How much of the skin a brow covers along it (ts: 0 the head .. 1 the tail): the hairs of the head stand apart."""
    return BROW['head_ink'] + (1 - BROW['head_ink']) * _smooth(0.0, BROW['head'], np.clip(ts, 0.0, 1.0))


def draw_face(rig, face, skin, brow):
    """A person's cell: `face` as in PEOPLE (characters.py), skin and brow colours as sRGB hex."""
    f = FACE[rig]
    cv = Canvas()
    woman = rig == 'women'
    kind = face.get('lid', 'inner')
    age = face.get('age')
    k = face.get('eye', 1.0)
    lash = f['lash'] * face.get('lash', 1.0)
    for sx in (1, -1):
        ex, hw, top, bot = eye_curves(f, face, sx)
        slant = face.get('slant', f['slant'])
        at = lambda t: ex + sx * hw * t                     # noqa: E731
        t_of = lambda x: (x - ex) / (sx * hw)               # noqa: E731
        # the white of the eye between the lids, and on it the iris: large and dark, cut off a little by both lids
        under = cv.below(lambda x: top(t_of(x)))
        over = 1 - cv.below(lambda x: bot(t_of(x)))
        inside = under * over * (np.abs(t_of(cv.X)) < 1.0)
        cv.whiten(inside)
        r = f['iris'] * k
        iz = (top(0.0) + bot(0.0)) / 2 + 0.0006
        cv.ink(cv.disc(ex, iz, r) * inside, IRIS)
        cv.ink(cv.disc(ex, iz, r * 0.56) * inside, INK)
        # the upper lid: one stroke along the top of the eye, heaviest over the iris and outwards of it, carried a
        # little past the outer corner (a woman's lashes: further, and turned up)
        ts = np.linspace(-1.0, 1.0, 41)
        w = lash / 2 * (0.42 + 0.58 * (1 - ts * ts) ** 0.5) * (1 + 0.18 * ts)
        pts = [(at(t), top(t) + 0.35 * wi) for t, wi in zip(ts, w)]
        halves = list(w)
        tail = 0.20 if woman else 0.10
        rise = (0.55 if woman else 0.10) + slant
        for q in (0.5, 1.0):
            pts.append((at(1 + tail * q), top(1.0) + 0.35 * w[-1] + rise * hw * tail * q))
            halves.append(w[-1] * (1 - 0.8 * q))
        cv.ink(cv.stroke(pts, halves), INK)
        # the light in the eye: a white spot on the iris, up and to one side
        cv.whiten(cv.disc(ex - 0.36 * r, iz + 0.34 * r, 0.27 * r) * inside)
        # the lower lid: a faint line, from under the iris out
        ts = np.linspace(-0.15, 0.96, 16)
        cv.ink(cv.stroke([(at(t), bot(t) - 0.0003) for t in ts], 0.00034 * (0.5 + 0.5 * _smooth(-0.15, 0.3, ts))), LINE,
               0.8 if age != 'old' else 0.95)
        # the crease of a double eyelid: over the whole eye, or (inner) only showing towards the outer corner
        if kind != 'mono':
            gap = (0.0030 if kind == 'double' else 0.0020) * k * face.get('crease', 1.0)
            ts = np.linspace(-0.72 if kind == 'double' else 0.15, 1.0, 20)
            cr = [(at(t), top(t) + lash * 0.75 + gap * (0.55 + 0.45 * (1 - t * t))) for t in ts]
            cv.ink(cv.stroke(cr, 0.00028), LINE, 0.7 if kind == 'double' else 0.5)
        if age == 'old':                                    # the fold under an older eye
            ts = np.linspace(-0.55, 0.75, 14)
            cv.ink(cv.stroke([(at(t), bot(t) - 0.0042 - 0.0012 * (1 - t * t)) for t in ts], 0.0003), LINE, 0.5)
        # the brow: one stroke from over the inner corner out past the eye, thinning to the tail.  A person's own:
        # how heavy it is (brow) and how far its tail keeps that weight (brow_taper), how long (brow_len), how far
        # from the other (brow_gap, m), how high (brow_up, m), how much it arches (arch) and where its top is
        # (brow_peak, of its length), whether it turns there in a corner (brow_corner: 각진 눈썹) or in a curve, how
        # far the tail falls after it (brow_drop), the tail higher or lower than the head (brow_tilt), and how hard
        # its edge is (brow_soft, pixels: bushy brows are soft)
        tb, bz, th = brow_line(f, face, hw, slant)
        tint = np.clip(_linear(brow) / _linear(skin), 0.0, 1.0)
        along = brow_dense(((cv.X - ex) / (sx * hw) - tb[0]) / (tb[-1] - tb[0]))
        cv.ink(cv.stroke([(at(t), z) for t, z in zip(tb, bz)], th / 2, soft=face.get('brow_soft', 1.8)) * along,
               tint, BROW['far'] * face.get('brow_ink', 1.0))
    # the mouth: one line, its corners a little up, a dot's weight at each corner; under it the lower lip (a man's: a
    # light tint and a short shadow under it, a woman's: tinted)
    mw, mt = f['mouth']
    mw *= face.get('mouth', 1.0)
    mz = f['mouth_dz']
    smile = face.get('smile', 0.0024)
    ts = np.linspace(-1.0, 1.0, 41)
    curve = lambda t: mz + smile * np.abs(t) ** 2.0 - 0.0004 * np.exp(-(t / 0.2) ** 2)         # noqa: E731
    tint, strength = LIP[rig]
    tint = face.get('lip_tint', tint)                       # (a person's own colour of the lips)
    strength = min(1.0, strength * face.get('lip_ink', 1.0))
    mt *= face.get('mouth_line', 1.0)
    lip = f['lip'] * face.get('lip', 1.0)
    tx = cv.X / mw
    lower = cv.below(lambda x: curve(x / mw), soft=1.5) \
        * (1 - cv.below(lambda x: curve(x / mw) - lip * np.maximum(0.0, 1 - (x / (0.82 * mw)) ** 2) ** 0.7, soft=2.5)) \
        * (np.abs(tx) < 0.82)
    cv.ink(lower, tint, strength)
    if woman:                                               # the upper lip: thinner, with its dip in the middle
        upper = (1 - cv.below(lambda x: curve(x / mw), soft=1.5)) * cv.below(
            lambda x: curve(x / mw) + face.get('lip_up', 0.55) * lip * np.maximum(0.0, 1 - (x / (0.9 * mw)) ** 2) ** 0.6
            * (1 - 0.3 * np.exp(-(x / (0.16 * mw)) ** 2)), soft=2.5) * (np.abs(tx) < 0.9)
        cv.ink(upper, tint, strength * 0.8)
    else:
        ts2 = np.linspace(-0.36, 0.36, 12)
        cv.ink(cv.stroke([(mw * t, mz - lip * 1.12 + 0.0012 * t * t / 0.13) for t in ts2], 0.0004, soft=1.5), LINE, 0.45)
    half = mt / 2 * (0.55 + 0.45 * (1 - ts * ts) ** 0.5)
    cv.ink(cv.stroke([(mw * t, curve(t)) for t in ts], half), MOUTH)
    for sx in (1, -1):
        cv.ink(cv.disc(sx * mw, curve(1.0) + 0.0002, mt * 0.62), MOUTH, 0.9)
    if woman and not age:                                   # a little colour on the cheeks
        tint, strength = BLUSH
        for sx in (1, -1):
            d = np.hypot((cv.X - sx * 0.043) / 0.017, (cv.Z - (f['nose_dz'] + 0.012)) / 0.011)
            cv.ink(_smooth(1.0, 0.25, d), tint, strength)
    if age:                                                 # the lines from the nose to the corners of the mouth
        nz = f['nose_dz']
        for sx in (1, -1):
            ts = np.linspace(0.0, 1.0 if age == 'old' else 0.6, 16)
            fold = [(sx * (0.0185 + 0.0125 * t ** 0.8 + 0.002 * np.sin(np.pi * t)), nz + 0.008 + (mz + 0.004 - nz - 0.008) * t)
                    for t in ts]
            cv.ink(cv.stroke(fold, 0.00034 * (0.4 + 0.6 * np.sin(np.pi * ts / ts[-1]) ** 0.5), soft=1.5), LINE,
                   0.7 if age == 'old' else 0.45)
    # nothing may reach the cell's edge (the neighbours, and the faces of the mesh just outside the frame)
    edge = MARGIN / cv.px
    n = cv.n
    idx = np.arange(n)
    keep = (np.minimum(idx, n - 1 - idx) >= edge - 1)
    if not np.all(cv.rgb[~keep, :, :] == 1.0) or not np.all(cv.rgb[:, ~keep, :] == 1.0):
        raise SystemExit('a face is drawn over the edge of its cell')
    w = cv.white[..., None]
    return np.concatenate([cv.rgb * (1 - w) + w, 1 - w], axis=2)        # (colour, how much of it is skin)


def rim_frame(rig, face):
    """The glasses of a face: the eye's half width, a rim's middle from the nose, a rim's half width and height."""
    hw = FACE[rig]['eye'][0] * face.get('eye', 1.0)
    gw, gh = GLASSES[rig]
    return hw, FACE[rig]['gap'] / 2 + hw, hw * gw, hw * gh


def draw_rims(rig, face, n=RIM_CELL, ss=4):
    """A face's glasses seen from the front, as coverage (0 .. 1) on a cell n pixels a side: the two rims (rounded
    rectangles, as face_glasses makes them), the bridge, and the temples as far as the face reaches.  Drawn ss times
    finer and averaged."""
    hw, ex, W, H = rim_frame(rig, face)
    m = n * ss
    px = 2 * HALF / m
    X, Z = np.meshgrid(-HALF + (np.arange(m) + 0.5) * px, TOP - (np.arange(m) + 0.5) * px)
    ez = RIM_DZ
    on = np.zeros((m, m), bool)
    for sx in (1, -1):
        rho = ((np.abs(X - sx * ex) / W) ** 2.6 + (np.abs(Z - ez) / H) ** 2.6) ** (1 / 2.6)
        on |= (rho >= 1.0) & (rho <= 1.0 + RIM_T / H)
        x0, z0 = ex + W * 0.98, ez + H * 0.45                      # the temple: from the rim's outer top corner back
        t = np.clip((sx * X - x0) / 0.02, 0.0, 1.0)
        on |= (sx * X >= x0) & (sx * X <= HALF - MARGIN - 0.001) & (Z >= z0 + 0.006 * t) & (Z <= z0 + 0.006 * t + RIM_T)
    xi = ex - W                                                     # the bridge
    on |= (np.abs(X) <= xi) & (Z >= ez + H * 0.25) & (Z <= ez + H * 0.25 + RIM_T)
    return on.reshape(n, ss, n, ss).mean(axis=(1, 3))


def write_rims(path, people):
    """faces_rims.png: people [(rig, face)] in the order of their cells; grey, white where a rim covers it all."""
    img = np.zeros((GRID * RIM_CELL, GRID * RIM_CELL))
    for i, (rig, face) in enumerate(people):
        x, y = (i % GRID) * RIM_CELL, (i // GRID) * RIM_CELL
        img[y:y + RIM_CELL, x:x + RIM_CELL] = draw_rims(rig, face)
    g8 = np.round(img * 255).astype(np.uint8)
    h, w = g8.shape
    raw = b''.join(b'\x00' + g8[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    with open(path, 'wb') as fh:
        fh.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0))
                 + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    return img


def _srgb8(lin):
    lin = np.clip(lin, 0.0, 1.0)
    s = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    return np.round(s * 255).astype(np.uint8)


def write_png(path, rgb8):
    """An 8 bit image (h, w, 4: RGBA, or h, w, 3: RGB)."""
    h, w, c = rgb8.shape
    raw = b''.join(b'\x00' + rgb8[y].tobytes() for y in range(h))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    with open(path, 'wb') as fh:
        fh.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6 if c == 4 else 2, 0, 0, 0))
                 + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


# ---------- what is printed on clothes ----------
# Lettering on a chest, as the students of 1997 wore it: the university's name in an arch, and the film 건축학개론's
# (2012) white sweatshirt with the knock-off 'GEUSS' triangle.  The prints share the cell PRINT, each a band of its
# rows; characters.py print_map lays the front of a chest on a band, and the game draws it as it draws a face: the
# cloth's colour times the picture's, and where the picture's alpha is 0 the white of the eye - so ink is a tint on
# light cloth ('geuss', 'yonsei_ink') and white letters are alpha on dark cloth ('yonsei').
PRINTS = {'geuss': (0, 144), 'yonsei': (144, 200), 'yonsei_ink': (200, 256)}       # the rows of the cell, from the top
PRINT_PAD = 4              # pixels of a band left bare all round (the neighbours, and the mip maps)
RED = (.72, .03, .05)      # ink, as factors of the cloth's (linear) light
BLUE = (.012, .05, .35)
# letters as strokes on a unit square (x to the right, y up), and how wide each is of its height
GLYPHS = {
    'Y': (.74, [[(0, 1), (.5, .5), (1, 1)], [(.5, .5), (.5, 0)]]),
    'O': (.74, [[(.28, 0), (.72, 0), (1, .25), (1, .75), (.72, 1), (.28, 1), (0, .75), (0, .25), (.28, 0)]]),
    'N': (.74, [[(0, 0), (0, 1), (1, 0), (1, 1)]]),
    'S': (.70, [[(1, .82), (.75, 1), (.25, 1), (0, .82), (0, .62), (.25, .5), (.75, .5), (1, .38), (1, .18), (.75, 0), (.25, 0),
                 (0, .18)]]),
    'E': (.64, [[(1, 1), (0, 1), (0, 0), (1, 0)], [(0, .5), (.8, .5)]]),
    'I': (.14, [[(.5, 0), (.5, 1)]]),
    'G': (.74, [[(1, .8), (.75, 1), (.27, 1), (0, .75), (0, .25), (.27, 0), (.75, 0), (1, .2), (1, .5), (.55, .5)]]),
    'U': (.74, [[(0, 1), (0, .26), (.27, 0), (.73, 0), (1, .26), (1, 1)]]),
    '?': (.62, [[(0, .74), (.22, 1), (.78, 1), (1, .8), (1, .62), (.5, .40), (.5, .27)], [(.5, .02), (.5, .03)]]),
}


def print_band(name):
    """A print's place: (u0, v0, u1, v1) on the atlas (v down from the top, as glTF counts it) and width / height."""
    r0, r1 = PRINTS[name]
    cu, cv = cell_origin(PRINT)
    px = 1.0 / (GRID * CELL)
    return (cu + PRINT_PAD * px, cv + (r0 + PRINT_PAD) * px, cu + (CELL - PRINT_PAD) * px, cv + (r1 - PRINT_PAD) * px,
            (CELL - 2 * PRINT_PAD) / (r1 - r0 - 2 * PRINT_PAD))


def _lettering(text, cx, base, size, gap=.16, arch=0.0):
    """The strokes of `text` (pixels, y down): centred on cx, standing on `base`, `size` high; arch: how much higher
    the middle stands than the ends, the letters turned along that curve."""
    widths = [GLYPHS[c][0] * size for c in text]
    total = sum(widths) + gap * size * (len(text) - 1)
    R = (total * total / 4 + arch * arch) / (2 * arch) if arch else None
    out, x = [], cx - total / 2
    for c, w in zip(text, widths):
        mid = x + w / 2
        th = (mid - cx) / R if R else 0.0
        ox, oy = (cx + R * np.sin(th), base - arch + R * (1 - np.cos(th))) if R else (mid, base)
        for line in GLYPHS[c][1]:
            pts = []
            for gx, gy in line:
                lx, ly = (gx - .5) * w, -gy * size                    # about the foot of the letter's middle
                pts.append((ox + lx * np.cos(th) - ly * np.sin(th), oy + lx * np.sin(th) + ly * np.cos(th)))
            out.append(pts)
        x += w + gap * size
    return out


def _cover(h, w, lines, half, ss=3):
    """How much of each pixel (h, w) the strokes `lines`, `half` thick either side, cover (drawn ss times finer)."""
    Y, X = (np.mgrid[0:h * ss, 0:w * ss] + 0.5) / ss
    d = np.full(X.shape, 1e9)
    for line in lines:
        pts = np.asarray(line, float)
        for a, b in zip(pts[:-1], pts[1:]):
            ab = b - a
            t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / max(float(ab @ ab), 1e-9), 0.0, 1.0)
            np.minimum(d, np.hypot(X - a[0] - t * ab[0], Y - a[1] - t * ab[1]), out=d)
    return (d <= half).reshape(h, ss, w, ss).mean(axis=(1, 3))


def draw_prints():
    """The cell PRINT: (CELL, CELL, 4), colour factors and how much of the cloth shows."""
    cell = np.ones((CELL, CELL, 4))
    W = CELL

    def ink(r0, cover, tint):
        band = cell[r0:r0 + cover.shape[0]]
        a = cover[..., None]
        band[..., :3] = band[..., :3] * (1 - a) + a * np.asarray(tint)

    # GEUSS: a triangle standing on its point, the name on a band across it, a question mark under the name
    r0, r1 = PRINTS['geuss']
    h = r1 - r0
    top, tip, half_w = 13.0, h - 9.0, 104.0
    tri = _cover(h, W, [[(W / 2 - half_w, top), (W / 2 + half_w, top), (W / 2, tip), (W / 2 - half_w, top)]], 5.0)
    b0, b1 = 34.0, 70.0                                         # the band's rows
    Y, X = np.mgrid[0:h, 0:W] + 0.5
    reach = half_w * (tip - (b0 + b1) / 2) / (tip - top) + 26   # (wider than the triangle is there)
    band = (Y > b0) & (Y < b1) & (np.abs(X - W / 2) < reach)
    tri = tri * ~band
    rules = _cover(h, W, [[(W / 2 - reach, b0), (W / 2 + reach, b0)], [(W / 2 - reach, b1), (W / 2 + reach, b1)]], 1.6)
    name = _cover(h, W, _lettering('GEUSS', W / 2, b1 - 7.5, b1 - b0 - 15.0, gap=.22), 2.6)
    mark = _cover(h, W, _lettering('?', W / 2, tip - 22.0, 32.0), 3.2)
    ink(r0, np.clip(tri + rules + name + mark, 0, 1), RED)
    # YONSEI in an arch: white on dark cloth (the picture's alpha), or blue ink on light cloth
    for key in ('yonsei', 'yonsei_ink'):
        r0, r1 = PRINTS[key]
        h = r1 - r0
        cover = _cover(h, W, _lettering('YONSEI', W / 2, h - PRINT_PAD - 5.0, 30.0, gap=.20, arch=9.0), 3.3)
        if key == 'yonsei':
            cell[r0:r1, :, 3] = 1 - cover
        else:
            ink(r0, cover, BLUE)
    for r0, r1 in PRINTS.values():                              # nothing in a band's margin
        m = np.ones((r1 - r0, W), bool)
        m[PRINT_PAD:-PRINT_PAD, PRINT_PAD:-PRINT_PAD] = False
        if not np.all(cell[r0:r1][m] == 1.0):
            raise SystemExit('a print is drawn over the edge of its band')
    return cell


def write_atlas(path, people):
    """people: [(rig, face, skin hex, brow hex)] in the order of their cells."""
    if len(people) > PRINT:
        raise SystemExit(f'{len(people)} faces do not fit the atlas')
    atlas = np.ones((GRID * CELL, GRID * CELL, 4))
    x, y = (PRINT % GRID) * CELL, (PRINT // GRID) * CELL
    atlas[y:y + CELL, x:x + CELL] = draw_prints()
    for i, (rig, face, skin, brow) in enumerate(people):
        x, y = (i % GRID) * CELL, (i // GRID) * CELL
        atlas[y:y + CELL, x:x + CELL] = draw_face(rig, face, skin, brow)
    write_png(path, np.concatenate([_srgb8(atlas[..., :3]), np.round(atlas[..., 3:] * 255).astype(np.uint8)], axis=2))
    return atlas


# ---------- the face from near ----------
# From a metre or so the drawn lines are all there is of a face, and they are lines: no shade round the eye, no
# colour in the iris, lips of one tint, brows of one stroke, and nothing of it turns to the light.  So every person has
# a picture of their own as well, four times as fine (faces/<id>.png, NEAR pixels for the same 15 cm), which the game
# fetches only for whoever stands near (web/src/characters.js `the face from near`) and fades in over the atlas' cell:
# drawn from the very curves of the far face (eye_curves, brow_line, the mouth's line), so it is the same face.
#   - the eye: a shaded white (the upper lid's shadow, pink at the inner corner), a brown iris with its fibres, a
#     darker rim and a pupil, the light in it, lashes hair by hair on a thinner lid line, the wet edge of the lower lid
#   - the brow: a soft ground and over it its hairs, upright at the head and lying over towards the tail
#   - the lips: both of them, the upper darker, the lower with its light, fine lines across; the shade at the corners
#     and under the lower lip, the groove under the nose
#   - the skin: shade in the sockets and under the eyes, a little colour on the cheeks and the nose
# A second picture (faces/<id>_n.png) is the face's relief as a normal map (red, green: x to the right, y down the
# picture) and how glossy it is (blue): the ball of the eye behind the lids, the lids over it, the lips and the groove
# between them.  The light then falls on them as on the nose.
# A person's own, beyond what the far face has (the `face` of PEOPLE): aegyo (애교살: the roll under the eye, by the
# soft line under it), bow (how deep the upper lip dips in the middle), socket (the shade beside the nose and on the
# lid), stubble (a shaved beard's shade over the lip and on the chin), fold (a young face's faint line from the nose
# towards the corner of the mouth), flush (the colour on the cheeks), iris_tone (a lighter or darker brown).  crease
# (the height of a double eyelid's fold over the lashes) is the far face's too.
# The colour is, as the atlas', a factor of the skin's light, but in the eye's opening a colour of its own.  Which it
# is the gloss says: only the eye's is over EYE_GLOSS (nothing else is glossier than LIP_GLOSS), so
# colour x mix(skin, 1, smoothstep(EYE_GLOSS .. , gloss)).  Neither picture has an alpha: a phone shrinks them, and
# shrinking a picture loses the colour wherever its alpha is 0.
NEAR = 1024                # pixels a side of a person's own picture
NEAR_DIR = 'faces'         # under the people's folder
SCLERA = (.70, .69, .68)   # the white of the eye, in the open (linear light; the far atlas' WHITE is its brightest)
SHADE = (.72, .56, .52)    # what shade does to the skin's light: darker and warmer
PINK = (.60, .36, .34)     # the inner corner of the eye
IRIS_NEAR = ((.012, .007, .006), (.058, .029, .016), (.105, .056, .028))     # the iris: its rim, its body, round the pupil
LIP_NEAR = {'umc': ((.80, .56, .54), .62), 'women': ((.84, .46, .47), .80)}  # the lips: tint, strength
LIP_UP = {'umc': .46, 'women': .55}                                         # the upper lip's height, of the lower's
EYE_GLOSS = (.62, .92)     # the gloss from which a pixel is (partly, wholly) the eye: web/src/characters.js reads the same
LIP_GLOSS = .55            # the glossiest of anything but the eye: the lower lip


def _gauss(X, Z, x0, z0, sx, sz):
    return np.exp(-((X - x0) / sx) ** 2 - ((Z - z0) / sz) ** 2)


def _blur(a, sigma):
    """`a` blurred by a Gaussian of `sigma` pixels (it wraps round the edges: keep them bare)."""
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.rfftfreq(a.shape[1])[None, :]
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * np.pi ** 2 * sigma ** 2 * (fx ** 2 + fy ** 2)), s=a.shape)


# ---------- the face's relief as geometry ----------
# Eyes and a mouth that are only drawn lie on the skull like a print: from the side the lips are a flat line, from
# three quarters the eyes sit on the cheek's own round, and no light falls into a socket.  So the head's mesh takes
# the larger forms of them (blender/characters.py head_face lets two finer sheets into the face, their rows along the
# lids and the lips, and moves every point of them in depth by forms() below; the drawn face is laid on from the
# front, so nothing of it moves):
#   - the sockets: the skin round each eye lies behind the brow, the cheek and the bridge of the nose, deepest
#     beside the nose (`socket`, `inner`); the lids swell over the ball of the eye (`dome`); in the opening the ball
#     lies behind the lids' edges, most under the upper one (`ball`), with the cornea's rise; the lower lid's roll
#   - the lips: the skin over the upper lip leans forward down to the lip's edge (`slope`), both lips are rolls
#     (`lip_u`, `lip_l`: no more than a share of the lip's own height, so thin lips stay thin) with the line between
#     them drawn in (`line`) and the corners drawn in (`corner`); the hollow under the lower lip (`sulcus`), the
#     groove under the nose (`groove`)
# The relief picture of the near face (draw_near) keeps only what the mesh is too coarse for: the same forms less
# their blur over FORMS_MESH, and the fine lines.
FORMS = {
    'umc': dict(socket=.0027, inner=.0015, dome=.0020, ball=.0010, roll=.0003, slope=.0010, lip_u=.0021, lip_l=.0025,
                sulcus=.0016, line=.0007, corner=.0007, groove=.0005, chin=.0135),
    'women': dict(socket=.0023, inner=.0012, dome=.0019, ball=.0010, roll=.0003, slope=.0010, lip_u=.0023, lip_l=.0026,
                  sulcus=.0014, line=.0007, corner=.0006, groove=.0005, chin=.0120),
}
FORMS_TOP, FORMS_BOT = 0.036, -0.024      # the eyes' sheet: from so far over the eye line down to so far under it
#                                          (over the brows: the forehead's own faces reach out of the atlas' cell
#                                          and point at the blank one, so a brow on them was cut off)
SOCKET_TOP = 0.026                        # the socket's skin begins to fall back so far over the eye line
SOCKET_OUT = 0.0075                       # and so far beyond the outer corner
FORMS_NOSE = 0.0075                       # the mouth's sheet begins so far under the nose's foot
#                                          and ends `chin` under the lower lip (a woman's chin is shorter), or higher
#                                          where the face turns under the jaw before that (sheets' `floor`)
FORMS_MESH = 0.0010                       # what the sheets hold: forms no finer than about this (the blur's sigma, m)
EYE_COLS = (-1.62, -1.30, -1.06, -0.85, -0.55, -0.20, 0.15, 0.50, 0.80, 1.02)    # of the eye's half width, from its middle
EYE_OUT = (0.0035, 0.0075, 0.0120)         # then, beyond the outer corner: m (the last under the brow's tail)
MOUTH_COLS = (0.0, 0.12, 0.27, 0.45, 0.63, 0.80, 0.93, 1.04)      # of the mouth's half width; then, beyond the corner:
MOUTH_OUT = (0.0035, 0.0065, 0.0100)                               # m


def lip_edges(rig, face, X):
    """The mouth at the places X across the face: (tx: X in half widths of the mouth, the line between the lips, the
    upper lip's upper edge, the lower lip's lower edge) as heights over the eye line, and (half width, the lower
    lip's height, the upper lip's, the line's height at the corners)."""
    f = FACE[rig]
    mw = f['mouth'][0] * face.get('mouth', 1.0)
    mz = f['mouth_dz']
    smile = face.get('smile', 0.0024)
    curve = lambda t: mz + smile * np.abs(t) ** 2.0 - 0.0004 * np.exp(-(t / 0.2) ** 2)         # noqa: E731
    lip = f['lip'] * face.get('lip', 1.0)
    hu = lip * face.get('lip_up', LIP_UP[rig])
    tx = np.asarray(X, float) / mw
    cz = curve(np.clip(tx, -1.0, 1.0))
    bow = face.get('bow', 1.0)
    up_edge = cz + hu * np.maximum(0.0, 1 - (tx / 0.9) ** 2) ** 0.6 * (1 - min(0.6, 0.3 * bow) * np.exp(-(tx / 0.16) ** 2)) \
        * (1 + 0.10 * (bow - 1) * np.exp(-((np.abs(tx) - 0.27) / 0.13) ** 2))
    lo_edge = cz - lip * np.maximum(0.0, 1 - (tx / 0.82) ** 2) ** 0.7
    return tx, cz, up_edge, lo_edge, (mw, lip, hu, curve(1.0))


def forms(rig, face, X, Z):
    """The relief of the face that the mesh holds (see FORMS): how far each place (X across the face, Z over the eye
    line; arrays) stands off the smooth skull, m; forward is positive."""
    f, F = FACE[rig], FORMS[rig]
    X, Z = np.asarray(X, float), np.asarray(Z, float)
    h = np.zeros(X.shape)
    k = face.get('eye', 1.0)
    deep = (0.6 + 0.4 * face.get('socket', 1.0)) * face.get('deep', 1.0)
    for sx in (1, -1):
        ex, hw, top, bot = eye_curves(f, face, sx)
        T = (X - ex) / (sx * hw)
        zt, zb = top(T), bot(T)
        zc = (top(0.0) + bot(0.0)) / 2
        # the socket: all of the skin round the eye, from under the brow down to the cheek, and beside the nose
        bx = _smooth(-1.72, -1.02, T) * _smooth(1.0 + (SOCKET_OUT - 0.001) / hw, 0.55, T)
        # (under the eye it runs out slowly into the cheek: a slope there looks up and takes the sky's light as a
        # pale band)
        bz = _smooth(SOCKET_TOP - 0.002, 0.010, Z) * _smooth(FORMS_BOT + 0.001, float(bot(0.0)) + 0.001, Z)
        h -= F['socket'] * deep * bx * bz
        h -= F['inner'] * deep * _gauss(X, Z, ex - sx * 1.10 * hw, 0.0035, 0.0060, 0.0085)
        # the lids over the ball; a single eyelid is full up to the brow
        d2 = ((X - ex) / (1.02 * hw)) ** 2 + ((Z - zc) / 0.0118) ** 2
        h += F['dome'] * np.maximum(0.0, 1 - d2) ** 1.5
        if face.get('lid', 'inner') == 'mono':
            h += 0.0007 * bx * _gauss(X, Z, ex, top(0.0) + 0.0055, 0.95 * hw, 0.0050)
        # the opening: the ball behind the lids' edges, the cornea
        edge = 0.0005
        inside = np.clip((zt - Z) / edge, 0.0, 1.0) * np.clip((Z - zb) / edge, 0.0, 1.0) * (np.abs(T) < 1.0)
        v = np.clip((Z - zb) / np.maximum(zt - zb, 1e-6), 0.0, 1.0)
        di = np.hypot(X - ex, Z - (zc + 0.0006)) / (f['iris'] * k)
        h += inside * (-F['ball'] * (0.35 + 0.65 * v) + 0.0004 * np.maximum(0.0, 1 - di * di))
        # the lower lid's roll (애교살: more of it)
        q = zb - Z
        h += (F['roll'] + 0.0004 * face.get('aegyo', 0.0)) * np.exp(-((q - 0.0013 * k) / 0.0011) ** 2) * (q > 0) \
            * _smooth(1.0, 0.7, np.abs(T))
    # the mouth
    tx, cz, ue, le, (mw, lip, hu, zcorner) = lip_edges(rig, face, X)
    nz = f['nose_dz']
    ax = np.abs(tx)
    ztop = nz - FORMS_NOSE
    s = np.clip((ztop - Z) / np.maximum(ztop - ue, 1e-6), 0.0, 1.0)
    vu = np.clip((Z - cz) / np.maximum(ue - cz, 1e-6), 0.0, 1.0)
    vl = np.clip((cz - Z) / np.maximum(cz - le, 1e-6), 0.0, 1.0)
    lean = F['slope'] * _smooth(mw + 0.009, 0.70 * mw, np.abs(X))
    over, on_up, on_lo = Z >= ue, (Z < ue) & (Z >= cz), (Z < cz) & (Z > le)
    h += over * lean * s * s * (3 - 2 * s)
    up = min(F['lip_u'], 0.55 * hu) * np.maximum(0.0, 1 - (tx / 0.95) ** 2) ** 0.5
    lo = min(F['lip_l'], 0.46 * lip) * np.maximum(0.0, 1 - (tx / 0.86) ** 2) ** 0.5
    h += on_up * (lean * vu ** 0.6 + up * (4 * vu * (1 - vu)) ** 0.75)
    h += on_lo * lo * (0.8 * (4 * vl * (1 - vl)) ** 0.6 + 0.2 * vl)
    h += (Z <= le) * 0.2 * lo * np.exp(-np.maximum(le - Z, 0.0) / 0.0025)
    h -= F['sulcus'] * np.exp(-((le - Z - 0.40 * F['chin']) / (0.28 * F['chin'])) ** 2) * np.exp(-(X / (0.75 * mw)) ** 2)
    h -= F['line'] * np.exp(-((Z - cz) / 0.0008) ** 2) * _smooth(1.08, 0.90, ax)
    for sx in (1, -1):
        h -= F['corner'] * _gauss(X, Z, sx * 1.03 * mw, zcorner, 0.0026, 0.0026)
    under = _smooth(ztop, ztop - 0.003, Z) * (Z > ue)
    h += (-F['groove'] * np.exp(-(X / 0.0034) ** 2) + 0.00018 * np.exp(-((np.abs(X) - 0.0052) / 0.0022) ** 2)) * under
    return h


def sheets(rig, face, floor=None):
    """The two sheets of the face's relief as rows [[(x, z, height), ...], ...] (as characters.py nose_shape: from
    the top down, every row from the person's right to their left; the outermost rows and columns lie on the face):
    the eyes' (one sheet across both, its rows along the lids), the mouth's (its rows along the lips; floor(x): the
    height over the eye line under which the face at x turns away under the jaw: the sheet ends there)."""
    f = FACE[rig]
    # the eyes: by column, the heights of the lids there (beyond the corners the two keep a little apart, so that no
    # row meets another)
    cols = []
    ex, hw, top, bot = eye_curves(f, face, 1)
    for t in EYE_COLS + tuple(1 + d / hw for d in EYE_OUT):
        zt, zb = float(top(t)), float(bot(t))
        mid, half = (zt + zb) / 2, max((zt - zb) / 2, 0.0009)
        cols.append((ex + hw * t, mid + half, mid - half))
    mid, half = cols[0][1:]
    cols = [(-x, a, b) for x, a, b in reversed(cols)] + [(0.0, cols[0][1], cols[0][2])] + cols
    ups, ins, downs = (0.80, 0.60, 0.42, 0.27, 0.15, 0.05), (0.22, 0.50, 0.78), (0.06, 0.18, 0.34, 0.52, 0.70, 0.86)
    rows = [[(x, FORMS_TOP) for x, _, _ in cols]]
    rows += [[(x, a + (FORMS_TOP - a) * q) for x, a, _ in cols] for q in ups]
    rows += [[(x, a) for x, a, _ in cols]]
    rows += [[(x, a - (a - b) * q) for x, a, b in cols] for q in ins]
    rows += [[(x, b) for x, _, b in cols]]
    rows += [[(x, b - (b - FORMS_BOT) * q) for x, _, b in cols] for q in downs]
    rows += [[(x, FORMS_BOT) for x, _, _ in cols]]
    eyes = rows
    # the mouth: by column, the line and the lips' edges (kept apart likewise)
    mw = f['mouth'][0] * face.get('mouth', 1.0)
    xs = [mw * t for t in MOUTH_COLS] + [mw + d for d in MOUTH_OUT]
    xs = [-x for x in reversed(xs[1:])] + xs
    _, cz, ue, le, (_, lip, _, _) = lip_edges(rig, face, np.array(xs))
    zt, zb = f['nose_dz'] - FORMS_NOSE, f['mouth_dz'] - lip - FORMS[rig]['chin']
    cols = [(x, float(c), float(max(u, c + 0.0008)), float(min(l, c - 0.0008)), max(zb, floor(x)) if floor else zb)
            for x, c, u, l in zip(xs, cz, ue, le)]
    if any(l - e < 0.003 for _, _, _, l, e in cols):
        raise SystemExit('the face turns under the jaw less than 3 mm under the lower lip')
    rows = [[(x, zt) for x, *_ in cols]]
    rows += [[(x, u + (zt - u) * q) for x, _, u, _, _ in cols] for q in (0.55, 0.22)]
    rows += [[(x, u) for x, _, u, _, _ in cols], [(x, (c + u) / 2) for x, c, u, _, _ in cols], [(x, c) for x, c, *_ in cols]]
    rows += [[(x, c - (c - l) * q) for x, c, _, l, _ in cols] for q in (0.40, 0.75)]
    rows += [[(x, l) for x, _, _, l, _ in cols]]
    rows += [[(x, l - (l - e) * q) for x, _, _, l, e in cols] for q in (0.10, 0.25, 0.45, 0.70)]
    rows += [[(x, e) for x, *_, e in cols]]
    mouth = rows
    out = []
    for rows in (eyes, mouth):
        X, Z = np.array([[p[0] for p in row] for row in rows]), np.array([[p[1] for p in row] for row in rows])
        H = forms(rig, face, X, Z)
        H[0, :] = H[-1, :] = H[:, 0] = H[:, -1] = 0.0
        if rows is mouth and floor:                         # (where the sheet ends early, what is left of the hollow eases out)
            for c in range(H.shape[1]):
                cut = Z[-1, c] - zb
                if cut > 0:
                    H[9:, c] *= np.clip((Z[9:, c] - Z[-1, c]) / max(Z[8, c] - Z[-1, c], 1e-6), 0.0, 1.0) ** 0.5 if cut > 0.002 else 1.0
        out.append([[(float(x), float(z), float(h)) for x, z, h in zip(*r)] for r in zip(X, Z, H)])
    return out


def draw_near(rig, face, skin, brow, seed=0, n=NEAR):
    """A person's face from near: (colour (n, n, 3): factors of the skin's light, in the eye a colour of its own,
    relief (n, n, 3): the normal's x and y (-1 .. 1) and the gloss (0 .. 1; the eye's says where the eye is))."""
    f = FACE[rig]
    cv = Canvas(n)
    X, Z, px = cv.X, cv.Z, cv.px
    rnd = np.random.RandomState(1997 + seed)
    woman = rig == 'women'
    kind = face.get('lid', 'inner')
    age = face.get('age')
    k = face.get('eye', 1.0)
    lash = f['lash'] * face.get('lash', 1.0)
    fine = n / CELL                                         # (a blur of so many of the atlas' pixels, in this one's)
    mul = np.ones((n, n, 3))                                # the skin's light
    ink = np.ones((n, n, 3))                                # lines over everything, the eye too
    eye = np.zeros((n, n))                                  # how much of a pixel is the eye's opening
    col = np.zeros((n, n, 3))                               # the colour there
    h = np.zeros((n, n))                                    # the relief: height over the face, m
    gloss = np.zeros((n, n))

    def tint(layer, cover, to, strength=1.0):
        if isinstance(cover, tuple):                        # (a stroke in its window)
            layer, cover = layer[cover[0], cover[1]], cover[2]
        a = (np.clip(cover, 0.0, 1.0) * strength)[..., None]
        layer *= 1 - a + a * np.asarray(to)

    def hair(pts, half, soft=1.0):
        return cv.stroke(pts, half, soft=soft, window=True)

    nz = f['nose_dz']
    for sx in (1, -1):
        ex, hw, top, bot = eye_curves(f, face, sx)
        slant = face.get('slant', f['slant'])
        at = lambda t: ex + sx * hw * t                     # noqa: E731
        T = (X - ex) / (sx * hw)
        zt, zb = top(T), bot(T)
        zc = (top(0.0) + bot(0.0)) / 2
        beside = _smooth(1.30, 0.92, np.abs(T))             # (over and under the eye, not beyond its corners)
        inside = np.clip(0.5 + (zt - Z) / px, 0.0, 1.0) * np.clip(0.5 + (Z - zb) / px, 0.0, 1.0) \
            * np.clip((1.0 - np.abs(T)) * hw / px + 0.5, 0.0, 1.0)
        # the skin round the eye: shade in the socket beside the nose and on the lid towards the lashes, and under
        # the eye
        deep = face.get('socket', 1.0)
        tint(mul, _gauss(X, Z, ex - sx * 0.95 * hw, 0.0045, 0.0075, 0.0120), SHADE, min(0.6, 0.34 * deep))
        tint(mul, np.exp(-np.maximum(Z - zt, 0.0) / 0.0034) * (Z > zt - px) * beside, SHADE, min(0.5, 0.30 * deep))
        v = np.maximum(zb - Z, 0.0)
        tint(mul, (1 - np.exp(-v / 0.0012)) * np.exp(-v / 0.0050) * beside, (.82, .70, .70), 0.13 if age != 'old' else 0.36)
        # the white of the eye: in the upper lid's shadow, darker into the corners, pink at the inner one
        du = np.maximum(zt - Z, 0.0)
        shade = 1 - 0.50 * np.exp(-du / 0.0019) - 0.18 * np.abs(T) ** 3
        pink = (0.55 * np.exp(-((T + 1.0) / 0.34) ** 2) + 0.20 * np.exp(-((T - 1.0) / 0.22) ** 2))[..., None]
        ball = (np.asarray(SCLERA) * (1 - pink) + np.asarray(PINK) * pink) * shade[..., None]
        zi = (top(-0.9) + bot(-0.9)) / 2
        car = cv.disc(at(-0.93), zi, 0.0010 * k, soft=3.0)[..., None]
        ball = ball * (1 - car) + np.asarray(PINK) * 0.85 * car
        # the iris: fibres running out from the pupil, a paler ring round it, a dark rim; lighter below, where the
        # light that came in above comes out
        r = f['iris'] * k
        iz = zc + 0.0006
        dx, dz = X - ex, Z - iz
        d = np.hypot(dx, dz) / r
        th = np.arctan2(dz, dx)
        fib = sum(a * np.sin(m * th + ph) for m, a, ph in
                  zip((13, 23, 37, 59, 97), (.30, .28, .22, .14, .08), rnd.uniform(0, 2 * np.pi, 5)))
        c_rim, c_mid, c_in = (np.asarray(c) * face.get('iris_tone', 1.0) for c in IRIS_NEAR)
        w_rim = _smooth(0.74, 1.0, d)[..., None]
        w_in = (0.7 * np.exp(-((d - 0.52) / 0.13) ** 2))[..., None]
        ic = (c_mid * (1 - w_rim) + c_rim * w_rim) * (1 - w_in) + c_in * w_in
        ic = ic * (1 + 0.55 * fib * _smooth(0.42, 0.62, d) * _smooth(1.0, 0.8, d))[..., None]
        ic = ic * (1 + 0.55 * np.clip(-dz / r, -1.0, 1.0))[..., None]
        pupil = np.clip((0.43 - d) / 0.04 + 0.5, 0.0, 1.0)[..., None]
        ic = ic * (1 - pupil) + np.asarray((.004, .004, .005)) * pupil
        ic = ic * (1 - 0.50 * np.exp(-du / 0.0028))[..., None]
        on = np.clip((1.02 - d) / 0.07 + 0.5, 0.0, 1.0)[..., None]
        ball = ball * (1 - on) + ic * on
        # the light in the eye: the sky's, up and to one side, and a small one across from it; the wet edge of the
        # lower lid
        for lx, lz, lr, ls in ((-0.34, 0.36, 0.21, 0.95), (0.38, -0.40, 0.08, 0.30)):
            spot = (np.clip((lr - np.hypot(dx / r - lx, dz / r - lz)) / 0.06 + 0.5, 0.0, 1.0) * ls)[..., None]
            ball = ball * (1 - spot) + spot
        wet = (0.07 * np.exp(-((Z - zb - 0.00042) / 0.00024) ** 2) * _smooth(-0.8, -0.4, T) * _smooth(0.95, 0.6, T))[..., None]
        ball = ball * (1 - wet) + wet
        col = col * (1 - inside[..., None]) + ball * inside[..., None]
        eye = np.maximum(eye, inside)
        # the upper lid's line: thinner than the far face's stroke, with a soft shade over it as wide as that was;
        # and the lashes, hair by hair, fanning outwards (a woman's longer and turned up)
        ts = np.linspace(-1.0, 1.0, 81)
        w = lash / 2 * (0.42 + 0.58 * (1 - ts * ts) ** 0.5) * (1 + 0.18 * ts)
        pts = [(at(t), top(t) + 0.35 * wi) for t, wi in zip(ts, w)]
        halves = list(w)
        tail = 0.20 if woman else 0.10
        rise = (0.55 if woman else 0.10) + slant
        for q in (0.5, 1.0):
            pts.append((at(1 + tail * q), top(1.0) + 0.35 * w[-1] + rise * hw * tail * q))
            halves.append(w[-1] * (1 - 0.8 * q))
        tint(ink, cv.stroke(pts, halves, soft=1.5 * fine), INK, 0.50)
        tint(ink, cv.stroke([(x, z - 0.12 * hv) for (x, z), hv in zip(pts, halves)], np.asarray(halves) * 0.80, soft=1.5), INK, 0.96)
        nl = 30 if woman else 22
        for i in range(nl):
            t = -0.78 + 1.83 * (i + rnd.uniform(-0.3, 0.3)) / (nl - 1)
            tw = 0.42 + 0.58 * max(0.0, 1 - min(1.0, abs(t)) ** 2) ** 0.5
            x0, z0 = at(min(t, 1.02)), top(min(t, 1.0)) + 0.30 * lash / 2 * tw
            out = 0.15 + 0.75 * np.clip((t + 0.3) / 1.3, 0.0, 1.0) + rnd.uniform(-0.12, 0.12)       # how far it leans outwards
            ln = (0.0024 if woman else 0.0013) * face.get('lash', 1.0) * (0.55 + 0.45 * np.clip((t + 1) / 1.6, 0.0, 1.0)) \
                * rnd.uniform(0.75, 1.1)
            curl = (0.35 if woman else 0.15) * ln
            ss = np.linspace(0.0, 1.0, 7)
            dirx, dirz = sx * out, 1.0
            nn = np.hypot(dirx, dirz)
            dirx, dirz = dirx / nn, dirz / nn
            strand = [(x0 + ln * s * dirx + sx * curl * s * s * dirz * 0.5, z0 + ln * s * dirz + curl * s * s * 0.5) for s in ss]
            tint(ink, hair(strand, 0.00011 * (1 - 0.75 * ss)), INK, 0.85)
        for i in range(12):                                 # the lower lashes: a few, short, from the middle outwards
            t = -0.2 + 1.1 * (i + rnd.uniform(-0.3, 0.3)) / 11
            x0, z0 = at(t), bot(t) - 0.0002
            ln = (0.0011 if woman else 0.0007) * rnd.uniform(0.7, 1.1)
            out = 0.2 + 0.6 * np.clip(t, 0.0, 1.0)
            ss = np.linspace(0.0, 1.0, 4)
            tint(ink, hair([(x0 + sx * out * ln * s, z0 - ln * s) for s in ss], 0.00008 * (1 - 0.7 * ss)), INK, 0.45)
        # the lower lid: a faint line, from under the iris out
        ts = np.linspace(-0.15, 0.96, 24)
        tint(ink, cv.stroke([(at(t), bot(t) - 0.0003) for t in ts], 0.00030 * (0.5 + 0.5 * _smooth(-0.15, 0.3, ts)), soft=2.5),
             LINE, 0.55 if age != 'old' else 0.8)
        # 애교살: the roll under the eye is there by the soft line under it (and a little relief, further down)
        aegyo = face.get('aegyo', 0.0)
        if aegyo:
            ts = np.linspace(-0.72, 0.85, 28)
            under = [(at(t), bot(t) - 0.0033 * k * (0.7 + 0.3 * (1 - t * t))) for t in ts]
            tint(mul, cv.stroke(under, 0.00045 * (0.4 + 0.6 * (1 - ts * ts) ** 0.5), soft=7.0), SHADE, min(0.5, 0.30 * aegyo))
        # the crease of a double eyelid
        crease = None
        if kind != 'mono':
            gap = (0.0030 if kind == 'double' else 0.0020) * k * face.get('crease', 1.0)
            ts = np.linspace(-0.72 if kind == 'double' else 0.15, 1.0, 30)
            crease = [(at(t), top(t) + lash * 0.75 + gap * (0.55 + 0.45 * (1 - t * t))) for t in ts]
            tint(ink, cv.stroke(crease, 0.00026, soft=2.5), LINE, 0.75 if kind == 'double' else 0.55)
        if age == 'old':                                    # the fold under an older eye
            ts = np.linspace(-0.55, 0.75, 14)
            tint(ink, cv.stroke([(at(t), bot(t) - 0.0042 - 0.0012 * (1 - t * t)) for t in ts], 0.0003, soft=3.0), LINE, 0.5)
        # the relief: the crease's fine line (the socket, the lids over the ball and the ball behind them are the
        # mesh's: forms)
        if crease:
            h -= 0.00022 * cv.stroke(crease, 0.0007, soft=6.0) * (1 - inside)
                # the brow: a soft ground, lighter than the far face's one stroke, and its hairs over it: at the head they
        # stand up, further out those of the lower edge lean up and those of the upper edge down, towards the tail
        tb, bz, bth = brow_line(f, face, hw, slant)
        to = np.clip(_linear(brow) / _linear(skin), 0.0, 1.0)
        weight = face.get('brow_ink', 1.0)
        line = [(at(t), z) for t, z in zip(tb, bz)]
        along = brow_dense(((X - ex) / (sx * hw) - tb[0]) / (tb[-1] - tb[0]))
        tint(mul, cv.stroke(line, bth / 2 * 0.90, soft=face.get('brow_soft', 1.8) * fine * 1.7) * along, to, BROW['ground'] * weight)
        bx = np.array([p[0] for p in line])
        ss = np.linspace(0.0, 1.0, len(line))
        nh = int(BROW['hairs'] * (0.75 + 0.25 * face.get('brow', 1.0)) * face.get('brow_len', 1.0))
        for i in range(nh):
            s = (i + rnd.uniform(0, 1)) / nh
            o = rnd.uniform(-1.0, 1.0)
            if rnd.uniform(0, 1) > float(brow_dense(s)) ** 0.7:            # (the head's hairs stand apart)
                continue
            x0, z0, t0 = np.interp(s, ss, bx), np.interp(s, ss, bz), np.interp(s, ss, bth)
            x1, z1 = np.interp(min(1.0, s + 0.04), ss, bx), np.interp(min(1.0, s + 0.04), ss, bz)
            x9, z9 = np.interp(max(0.0, s - 0.04), ss, bx), np.interp(max(0.0, s - 0.04), ss, bz)
            ax, az = x1 - x9, z1 - z9
            an = np.hypot(ax, az)
            ax, az = ax / an, az / an                       # along the brow, towards the tail
            lean = np.radians((72 - 60 * _smooth(0.0, 0.3, s)) * (1 if o < 0.3 else 0.4) - (16 * _smooth(0.15, 0.5, s) if o > 0.3 else 0)
                              + rnd.uniform(-9, 9))
            side = sx * (1 if ax * sx > 0 else -1)          # (turning up from the brow's own direction, on either side)
            gx, gz = ax * np.cos(lean) - side * az * np.sin(lean), az * np.cos(lean) + side * ax * np.sin(lean)
            if s < 0.3 and gz < 0:
                gz = -gz
            ln = (0.0030 + 0.0016 * rnd.uniform(0, 1)) * (1 - 0.45 * s) * (0.8 + 0.2 * face.get('brow', 1.0))
            p0 = (x0 - sx * 0.0 + (-az) * 0.0, z0 + o * t0 / 2 * 0.92)
            ps = np.linspace(0.0, 1.0, 5)
            strand = [(p0[0] + gx * ln * q + ax * ln * 0.25 * q * q, p0[1] + gz * ln * q * (1 - 0.35 * q)) for q in ps]
            edge = 1 - 0.5 * abs(o) ** 2
            tint(mul, hair(strand, 0.00014 * (1 - 0.6 * ps), soft=1.2), to, 0.86 * weight * edge * (1 - 0.4 * _smooth(0.85, 1.0, s)))
    # the mouth: the line between the lips as the far face draws it, thinner, in its shade; over it the upper lip with
    # its dip, under it the lower lip
    mt = f['mouth'][1] * face.get('mouth_line', 1.0)
    mz = f['mouth_dz']
    to, strength = LIP_NEAR[rig]
    to = face.get('lip_tint', to)
    strength = min(1.0, strength * face.get('lip_ink', 1.0))
    tx, cz, up_edge, lo_edge, (mw, lip, hu, _) = lip_edges(rig, face, X)
    curve = lambda t: lip_edges(rig, face, mw * np.asarray(t, float))[1]                       # noqa: E731
    bow = face.get('bow', 1.0)
    upper = np.clip(0.5 + (up_edge - Z) / (4.0 * px), 0.0, 1.0) * np.clip(0.5 + (Z - cz) / (1.5 * px), 0.0, 1.0) * (np.abs(tx) < 0.9)
    lower = np.clip(0.5 + (cz - Z) / (1.5 * px), 0.0, 1.0) * np.clip(0.5 + (Z - lo_edge) / (8.0 * px), 0.0, 1.0) * (np.abs(tx) < 0.82)
    vu = np.clip((Z - cz) / np.maximum(up_edge - cz, 1e-5), 0.0, 1.0)
    vl = np.clip((cz - Z) / np.maximum(cz - lo_edge, 1e-5), 0.0, 1.0)
    fan = tx * (1 + 0.5 * (Z - cz) / max(lip, 1e-5))
    lines = sum(a * np.sin(m * fan + ph) for m, a, ph in zip((47, 83, 131), (.5, .3, .2), rnd.uniform(0, 2 * np.pi, 3)))
    base = 1 - strength + strength * np.asarray(to)
    shade_u = (0.80 + 0.12 * vu) * (1 + 0.035 * lines)
    shade_l = (0.93 + 0.20 * np.exp(-((vl - 0.36) / 0.22) ** 2) * np.exp(-(tx / 0.45) ** 2) - 0.10 * _smooth(0.6, 1.0, vl)) * (1 + 0.045 * lines)
    for cover, shade in ((upper, shade_u), (lower, shade_l)):
        a = cover[..., None]
        mul *= 1 - a + a * np.clip(base * shade[..., None], 0.0, 1.2)
    ts = np.linspace(-1.0, 1.0, 81)
    half = mt / 2 * (0.55 + 0.45 * (1 - ts * ts) ** 0.5)
    mouth = [(mw * t, curve(t)) for t in ts]
    tint(ink, cv.stroke(mouth, half, soft=1.5 * fine), MOUTH, 0.45)
    tint(ink, cv.stroke(mouth, half * 0.5, soft=2.0), MOUTH, 0.9)
    for sx in (1, -1):
        tint(ink, cv.disc(sx * mw, curve(1.0) + 0.0002, mt * 0.40, soft=4.0), MOUTH, 0.45)
        tint(mul, _gauss(X, Z, sx * mw * 1.06, curve(1.0), 0.0022, 0.0024), SHADE, 0.30)
    # the shade under the lower lip and under the nose, the groove between the nose and the upper lip
    low0 = mz - lip
    tint(mul, _gauss(X, Z, 0.0, low0 - 0.0040, 0.60 * mw, 0.0030), SHADE, 0.32)
    tint(mul, _gauss(X, Z, 0.0, nz - 0.0030, 0.0110, 0.0040), SHADE, 0.12)
    # a little colour on the cheeks and the nose (a young woman's cheeks more, as on the far face)
    for sx in (1, -1):
        if woman and not age:
            to2, s2 = BLUSH
            dd = np.hypot((X - sx * 0.043) / 0.017, (Z - (nz + 0.012)) / 0.011)
            tint(mul, _smooth(1.0, 0.25, dd), to2, s2)
        tint(mul, _gauss(X, Z, sx * 0.040, nz + 0.012, 0.020, 0.015), (1.0, .88, .86), min(0.6, (0.20 if woman else 0.26) * face.get('flush', 1.0)))
    tint(mul, _gauss(X, Z, 0.0, nz + 0.009, 0.012, 0.010), (1.0, .88, .86), 0.22)
    # a shaved beard's shade: over the upper lip and on the chin, cool and a little uneven
    stubble = face.get('stubble', 0.0)
    if stubble:
        grain = 0.75 + 0.5 * _blur(rnd.uniform(0.0, 1.0, (n, n)), 1.2)
        lip_top = mz + hu
        over = np.exp(-((Z - (lip_top + 0.0050)) / 0.0048) ** 2) * (Z > up_edge) * _smooth(1.45 * mw, 0.95 * mw, np.abs(X))
        chin = _smooth(low0 - 0.0015, low0 - 0.0085, Z) * np.exp(-(X / (1.55 * mw)) ** 2)
        tint(mul, np.maximum(over, chin) * grain, (.78, .79, .84), min(0.5, 0.20 * stubble))
    fold = face.get('fold', 0.0)
    if fold and not age:                                    # a young face's line from the nose towards the mouth: faint and soft
        for sx in (1, -1):
            ts = np.linspace(0.0, 0.75, 20)
            line = [(sx * (0.0185 + 0.0125 * t ** 0.8 + 0.002 * np.sin(np.pi * t)), nz + 0.008 + (mz + 0.004 - nz - 0.008) * t) for t in ts]
            tint(mul, cv.stroke(line, 0.0005 * np.sin(np.pi * ts / ts[-1]) ** 0.5, soft=9.0), SHADE, min(0.5, 0.26 * fold))
    if age:                                                 # the lines from the nose to the corners of the mouth
        for sx in (1, -1):
            ts = np.linspace(0.0, 1.0 if age == 'old' else 0.6, 24)
            fold = [(sx * (0.0185 + 0.0125 * t ** 0.8 + 0.002 * np.sin(np.pi * t)), nz + 0.008 + (mz + 0.004 - nz - 0.008) * t)
                    for t in ts]
            wide = 0.00034 * (0.4 + 0.6 * np.sin(np.pi * ts / ts[-1]) ** 0.5)
            tint(ink, cv.stroke(fold, wide, soft=1.5 * fine), LINE, 0.6 if age == 'old' else 0.4)
            h -= 0.0005 * cv.stroke(fold, wide * 2.5, soft=2.0 * fine)
            if age == 'old':                                # (and at the outer corners of the eyes)
                ex, hw, top, bot = eye_curves(f, face, sx)
                for a in (-0.35, 0.0, 0.35):
                    x0, z0 = ex + sx * hw * 1.12, top(1.0)
                    crow = [(x0 + sx * 0.0060 * q, z0 + 0.0060 * q * a - 0.0006 * q * q) for q in np.linspace(0.0, 1.0, 8)]
                    tint(ink, cv.stroke(crow, 0.00022, soft=3.0), LINE, 0.4)
    # the lips' gloss
    # (the lips' rolls, the groove between them and the hollows are the mesh's: forms; here what is finer than it)
    form = forms(rig, face, X, Z)
    h += form - _blur(form, FORMS_MESH / px)
    gloss = np.maximum(gloss, LIP_GLOSS * lower * (0.6 + 0.4 * np.exp(-((vl - 0.36) / 0.25) ** 2)))
    gloss = np.maximum(gloss, 0.30 * upper)
    gloss = np.maximum(gloss, 0.22 * _gauss(X, Z, 0.0, nz + 0.014, 0.0060, 0.0150))
    # (and where the skin lies tight over bone and is a little oily: the brow's middle, the cheekbones, the chin)
    gloss = np.maximum(gloss, 0.16 * _gauss(X, Z, 0.0, 0.030, 0.026, 0.012))
    for sx in (1, -1):
        gloss = np.maximum(gloss, 0.14 * _gauss(X, Z, sx * 0.041, nz + 0.024, 0.013, 0.008))
    gloss = np.maximum(gloss, 0.10 * _gauss(X, Z, 0.0, mz - lip - 0.013, 0.010, 0.006))
    # bare at the cell's edge: the faces of the mesh just outside the frame have none of it
    edge = np.minimum(np.minimum(X + HALF, HALF - X), np.minimum(TOP - Z, Z - (TOP - 2 * HALF)))
    win = _smooth(MARGIN, MARGIN + 0.005, edge)
    mul = 1 + (mul - 1) * win[..., None]
    h *= win
    gloss *= win
    if eye[edge < MARGIN].max() > 0 or ink[edge < MARGIN].min() < 1:
        raise SystemExit('a face from near is drawn over the edge of its picture')
    # the eye's opening as gloss: from the one end of EYE_GLOSS to the other up its soft edge
    lo, hi = EYE_GLOSS
    gloss = np.where(eye > 0, np.maximum(gloss, lo + (hi - lo) * eye), gloss)
    e = eye[..., None]
    rgb = (mul * (1 - e) + col * e) * ink
    hb = _blur(h, 1.6)
    gy, gx = np.gradient(hb, px)                            # (down the picture, to the right; m per m)
    inv = 1 / np.sqrt(gx ** 2 + gy ** 2 + 1)
    return rgb, np.stack([-gx * inv, -gy * inv, gloss], axis=2)


def write_near(folder, rows, only=None):
    """rows: [(id, rig, face, skin hex, brow hex)] in the order of the atlas' cells: <id>.png and <id>_n.png for each
    (only: for these ids)."""
    import os
    os.makedirs(folder, exist_ok=True)
    for i, (pid, rig, face, skin, brow) in enumerate(rows):
        if only is not None and pid not in only:
            continue
        colour, relief = draw_near(rig, face, skin, brow, seed=i)
        write_png(os.path.join(folder, pid + '.png'), _srgb8(colour))
        rel = np.round(np.clip(relief * (.5, .5, 1) + (.5, .5, 0), 0.0, 1.0) * 255).astype(np.uint8)
        write_png(os.path.join(folder, pid + '_n.png'), rel)
