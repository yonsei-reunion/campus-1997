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
                lip=.0054, chin=.74, cheek=1.18),
    'women': dict(eye=(.0174, .0048), lid=dict(mono=.0074, inner=.0085, double=.0096), iris=.0068, gap=.0376, slant=.09,
                  brow=(.0262, .0056, .0028, .0040), mouth=(.0195, .0015), mouth_dz=-.0793, nose_dz=-.0595, lash=.0036,
                  lip=.0052, chin=.78, cheek=1.16),
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

    def stroke(self, pts, half, soft=1.0):
        """Coverage of a line through pts [(x, z)], `half` thick either side at each point; round ends; `soft`: the
        edge's blur in pixels."""
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
        out = np.zeros((self.n, self.n))
        out[j0:j1, i0:i1] = np.clip(0.5 - d / (soft * self.px), 0.0, 1.0)
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
    hw, lo, up = f['eye'][0] * k, f['eye'][1] * k, f['lid'][face.get('lid', 'inner')] * k
    slant = face.get('slant', f['slant'])
    ex = sx * (f['gap'] / 2 + face.get('eyes_apart', 0.0) + hw)

    def top(t):
        t = np.clip(t, -1.0, 1.0)
        return up * (1 - t * t) ** 0.72 * (1 - 0.12 * t) + slant * hw * t

    def bot(t):
        t = np.clip(t, -1.0, 1.0)
        return -lo * (1 - t * t) ** 0.85 * (1 + 0.15 * t) + slant * hw * t

    return ex, hw, top, bot


def draw_face(rig, face, skin, brow):
    """A person's cell: `face` as in PEOPLE (characters.py), skin and brow colours as sRGB hex."""
    f = FACE[rig]
    cv = Canvas()
    woman = rig == 'women'
    kind = face.get('lid', 'inner')
    age = face.get('age')
    k = face.get('eye', 1.0)
    lash = f['lash'] * face.get('lash', 1.0)
    bh, bt0, bt1, arch = f['brow']
    arch *= face.get('arch', 1.0)
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
            gap = (0.0030 if kind == 'double' else 0.0020) * k
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
            * (1 - 0.45 / taper * _smooth(0.82, 1.0, ts))
        tint = np.clip(_linear(brow) / _linear(skin), 0.0, 1.0)
        cv.ink(cv.stroke([(at(t0 + (t1 - t0) * t), z) for t, z in zip(ts, bz)], th / 2, soft=face.get('brow_soft', 1.8)),
               tint, face.get('brow_ink', 1.0))
    # the mouth: one line, its corners a little up, a dot's weight at each corner; under it the lower lip (a man's: a
    # light tint and a short shadow under it, a woman's: tinted)
    mw, mt = f['mouth']
    mw *= face.get('mouth', 1.0)
    mz = f['mouth_dz']
    smile = face.get('smile', 0.0024)
    ts = np.linspace(-1.0, 1.0, 41)
    curve = lambda t: mz + smile * np.abs(t) ** 2.0 - 0.0004 * np.exp(-(t / 0.2) ** 2)         # noqa: E731
    tint, strength = LIP[rig]
    lip = f['lip'] * face.get('lip', 1.0)
    tx = cv.X / mw
    lower = cv.below(lambda x: curve(x / mw), soft=1.5) \
        * (1 - cv.below(lambda x: curve(x / mw) - lip * np.maximum(0.0, 1 - (x / (0.82 * mw)) ** 2) ** 0.7, soft=2.5)) \
        * (np.abs(tx) < 0.82)
    cv.ink(lower, tint, strength)
    if woman:                                               # the upper lip: thinner, with its dip in the middle
        upper = (1 - cv.below(lambda x: curve(x / mw), soft=1.5)) * cv.below(
            lambda x: curve(x / mw) + 0.55 * lip * np.maximum(0.0, 1 - (x / (0.9 * mw)) ** 2) ** 0.6
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
    """An 8 bit RGBA image (h, w, 4)."""
    h, w, _ = rgb8.shape
    raw = b''.join(b'\x00' + rgb8[y].tobytes() for y in range(h))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    with open(path, 'wb') as fh:
        fh.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
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
