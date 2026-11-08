"""Paint the textures of the clipped shrubs and flower beds from scanned leaves and flowers.

The leaves, flowers and twigs are cut out of the scan sheet of Poly Haven's "Periwinkle Plant" (Amal Kumar, CC0:
https://polyhaven.com/a/periwinkle_plant), recoloured, scaled to the real size of each shrub's leaves and flowers
and laid shoot by shoot, deepest first, the way a clipped surface is built: the shoots' tips at the top, the old
leaves and bare twigs deep inside and dark.

Outputs (web/public/assets/textures):
  hedge_<name>.jpg, hedge_<name>_nor.jpg   the clipped surface, a seamless tile (TILE m), and its normal map: the
                                           shrub bodies take them in world space from three sides (web/src/hedges.js)
  leaf_<name>.png                          2x2 atlas of sprig cards (RGBA, alpha-tested) that stand out of the body
Names: boxwood (회양목 · 주목, all year), azalea_summer (철쭉 leaves, May and the bush), azalea (the bush in April,
magenta 영산홍), azalea_red (철쭉 in bloom), azalea_violet (진달래 in April), azalea_autumn (철쭉 · 진달래 leaves in late
October), pansy (팬지 border).
Needs the scan: python3 tools/fetch_polyhaven.py models 2k periwinkle_plant
Run: .venv/bin/python tools/make_shrub_textures.py [name ...]
"""
import math, os, random, sys, zlib
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'web/public/assets/textures')
SRC = os.path.join(ROOT, 'assets_src/models/periwinkle_plant/textures/periwinkle_plant_diff_2k.jpg')
ONLY = set(sys.argv[1:])
SS = 2                  # supersampling
SIZE = 1024             # surface tile, px
CELL = 512              # atlas cell, px (atlas = 2x2 cells)

# metres per surface tile: the leaves come out at their real size (boxwood 1.2-2 cm, azalea leaves 2.5-4 cm,
# flowers 4-5 cm, pansies 4-6 cm). web/src/hedges.js reads the same numbers.
TILE = {'boxwood': 0.5, 'azalea_summer': 0.7, 'azalea': 0.7, 'azalea_red': 0.7, 'azalea_violet': 0.7,
        'azalea_autumn': 0.7, 'pansy': 0.6}
CARD_M = {'boxwood': 0.22, 'azalea_summer': 0.32, 'azalea': 0.32, 'azalea_red': 0.32, 'azalea_violet': 0.34,
          'azalea_autumn': 0.32, 'pansy': 0.2}      # metres across a card cell (blender/shrubs.py CARDS)


def srgb2lin(c):
    c = np.asarray(c, np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055) * 255.0


# ---------------------------------------------------------------- stamps cut out of the scan sheet
class Stamp:
    """One cut-out: linear rgb, alpha, luminance detail (lum / mean) and a bulge (0 at the rim, 1 on the axis), laid
    along +x: a leaf with its stalk at x = 0, a flower centred, a twig from its thick end."""
    def __init__(self, rgb, a):
        self.rgb, self.a = rgb, a
        lum = (rgb * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1)
        m = lum[a > 0.5].mean() if (a > 0.5).any() else 1.0
        self.detail = np.clip(lum / max(m, 1e-4), 0.45, 1.6).astype(np.float32)
        d = ndimage.distance_transform_edt(a > 0.5)
        self.bulge = (d / max(d.max(), 1)).astype(np.float32)
        self.cache = {}

    def get(self, length, squash, ang):
        """resized (length px along x, width scaled by squash) and turned by ang (radians, counter-clockwise on the
        image): arrays detail, alpha, bulge and the offset of the stamp's origin (x = 0 on the axis) in them"""
        key = (int(length / 2), int(squash * 8), int((ang % (2 * math.pi)) / (2 * math.pi) * 36))
        if key in self.cache:
            return self.cache[key]
        L = key[0] * 2 + 2
        sq = (key[1] + 0.5) / 8
        a_ = (key[2] + 0.5) / 36 * 2 * math.pi
        h0, w0 = self.a.shape
        s = L / w0
        W, H = max(2, int(round(w0 * s))), max(2, int(round(h0 * s * sq)))
        chans = [self.detail, self.a, self.bulge]
        ims = [Image.fromarray(c.astype(np.float32), 'F').resize((W, H), Image.BILINEAR) for c in chans]
        # the origin (stalk end, on the axis) before turning
        ox, oy = 0.0, H / 2
        deg = math.degrees(a_)
        ims = [im.rotate(deg, resample=Image.BILINEAR, expand=True) for im in ims]
        W2, H2 = ims[0].size
        # where the origin went: PIL turns about the centre, counter-clockwise in image (y down) = clockwise visually
        cx, cy = W / 2, H / 2
        dx, dy = ox - cx, oy - cy
        ca, sa = math.cos(-a_), math.sin(-a_)
        rx, ry = dx * ca - dy * sa, dx * sa + dy * ca
        out = ([np.array(im, np.float32) for im in ims], (rx + W2 / 2, ry + H2 / 2))
        self.cache[key] = out
        return out


def cut_stamps():
    img = np.array(Image.open(SRC).convert('RGB')).astype(np.float32)
    lin = srgb2lin(img)
    mask = img.max(-1) > 22
    mask = ndimage.binary_opening(mask, iterations=2)
    lab, n = ndimage.label(mask)
    W = img.shape[1]
    kinds = {'leaf': [], 'yellow': [], 'flower': [], 'twig': []}
    for i, sl in enumerate(ndimage.find_objects(lab)):
        if sl is None:
            continue
        m = lab[sl] == i + 1
        area = m.sum()
        h, w = m.shape
        if area < 4000 or sl[1].start < 8 or sl[1].stop > W - 8 or (sl[1].start < 0.12 * W):
            continue                                   # specks, and the bark strips along the left and right edges
        r, g, b = img[sl][m].mean(0)
        ys, xs = np.nonzero(m)
        pts = np.stack([xs - xs.mean(), ys - ys.mean()], 1).astype(np.float32)
        ev, evec = np.linalg.eigh(np.cov(pts.T))
        major = evec[:, 1]
        elong = math.sqrt(ev[1] / max(ev[0], 1e-3))
        if b > g * 1.05 and r > g * 1.3:
            kind = 'flower'
        elif elong > 6 or (r > g * 0.95 and b > 0.45 * g and area / (h * w) < 0.3):
            kind = 'twig'
        elif r > g * 1.02:
            kind = 'yellow'
        else:
            kind = 'leaf'
        # straighten along the major axis (flowers stay as they are)
        a = ndimage.gaussian_filter(m.astype(np.float32), 0.8)
        a = np.clip((a - 0.25) / 0.5, 0, 1)
        rgb = lin[sl]
        if kind != 'flower':
            ang = math.degrees(math.atan2(major[1], major[0]))
            pad = int(max(h, w) * 0.3)
            big = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
            big[pad:pad + h, pad:pad + w, :3] = rgb
            big[pad:pad + h, pad:pad + w, 3] = a
            chans = [np.array(Image.fromarray(big[..., c], 'F').rotate(ang, resample=Image.BILINEAR)) for c in range(4)]
            big = np.stack(chans, -1)
            ys, xs = np.nonzero(big[..., 3] > 0.5)
            big = big[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            # the stalk end: where the cut-out stays thin longest
            prof = (big[..., 3] > 0.5).sum(0).astype(np.float32)
            thin = prof < 0.18 * prof.max()
            k = len(prof)
            left = np.argmax(~thin[:k // 2]) if (~thin[:k // 2]).any() else 0
            right = np.argmax(~thin[::-1][:k // 2]) if (~thin[::-1][:k // 2]).any() else 0
            if kind == 'twig':          # thick end first
                if prof[:k // 4].mean() < prof[-k // 4:].mean():
                    big = big[:, ::-1]
            elif right > left:
                big = big[:, ::-1]
            rgb, a = big[..., :3], big[..., 3]
        else:
            rgb = rgb.copy()
        kinds[kind].append(Stamp(np.ascontiguousarray(rgb), np.ascontiguousarray(a)))
    return kinds


# ---------------------------------------------------------------- canvas
class Canvas:
    """Linear rgb, coverage, height and the leaves' tilt (x, y: the slope of each leaf's face) in a square, seamless
    (wrap) or not (an atlas cell)."""
    def __init__(self, size, wrap, bg=None):
        self.n, self.wrap = size, wrap
        self.rgb = np.zeros((size, size, 3), np.float32)
        if bg is not None:
            self.rgb[:] = srgb2lin(bg)
        self.a = np.full((size, size), 1.0 if bg is not None else 0.0, np.float32)
        self.h = np.zeros((size, size), np.float32)
        self.t = np.zeros((size, size, 2), np.float32)

    def line(self, x0, y0, x1, y1, w, col, h):
        """a twig: a tapering stroke, lit along one side (round in section)"""
        pad = int(w) + 3
        bx0, by0 = int(min(x0, x1)) - pad, int(min(y0, y1)) - pad
        W, H = int(max(x0, x1)) + pad - bx0, int(max(y0, y1)) + pad - by0
        im = Image.new('L', (W, H), 0)
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        n = 6
        for k in range(n):          # (a taper: thinner toward the tip)
            t0, t1 = k / n, (k + 1) / n
            ww = max(1, int(round(w * (1 - 0.5 * t0))))
            d.line([(x0 + (x1 - x0) * t0 - bx0, y0 + (y1 - y0) * t0 - by0),
                    (x0 + (x1 - x0) * t1 - bx0, y0 + (y1 - y0) * t1 - by0)], fill=255, width=ww)
        a = np.array(im, np.float32) / 255.0
        a = ndimage.gaussian_filter(a, 0.6)
        lit = 0.75 + 0.5 * np.clip(ndimage.sobel(a, 0) * -0.25, -0.5, 0.5)   # the upper side lighter
        c = srgb2lin(col)
        colimg = c * lit[..., None]
        offs = [(dx, dy) for dx in (-self.n, 0, self.n) for dy in (-self.n, 0, self.n)] if self.wrap else [(0, 0)]
        for dx, dy in offs:
            X0, Y0 = bx0 + dx, by0 + dy
            if X0 >= self.n or Y0 >= self.n or X0 + W <= 0 or Y0 + H <= 0:
                continue
            sx0, sy0 = max(0, -X0), max(0, -Y0)
            sx1, sy1 = min(W, self.n - X0), min(H, self.n - Y0)
            ds = (slice(Y0 + sy0, Y0 + sy1), slice(X0 + sx0, X0 + sx1))
            ss = (slice(sy0, sy1), slice(sx0, sx1))
            aa = a[ss]
            self.rgb[ds] = self.rgb[ds] * (1 - aa[..., None]) + colimg[ss] * aa[..., None]
            self.a[ds] = self.a[ds] + aa * (1 - self.a[ds])
            self.h[ds] = self.h[ds] * (1 - aa) + h * aa


def jit(col, rnd, amt=0.1):
    f = 1 + rnd.uniform(-amt, amt)
    return tuple(max(0, min(255, v * f * (1 + rnd.uniform(-amt / 2, amt / 2)))) for v in col)


def cavity(cv, r):
    """darken the pits: where a texel lies below the leaves round it"""
    if cv.wrap:
        blur = ndimage.gaussian_filter(cv.h, r, mode='wrap')
    else:
        blur = ndimage.gaussian_filter(cv.h, r)
    occ = np.clip(1 - (blur - cv.h) * 2.2, 0.45, 1.0)
    cv.rgb *= occ[..., None]


def normal_map(cv, strength):
    """tangent-space normal (x along +u = image right, y along +v = image down, z out), from the leaves' heights and
    tilts, as 8-bit rgb"""
    mode = 'wrap' if cv.wrap else 'nearest'
    h = ndimage.gaussian_filter(cv.h, 1.0, mode=mode)
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx = cv.t[..., 0] - gx * strength
    ny = cv.t[..., 1] - gy * strength
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / ln, ny / ln, nz / ln], -1)
    return np.clip((n * 0.5 + 0.5) * 255, 0, 255).astype(np.uint8)


def save_surface(name, cv, strength):
    rgb = lin2srgb(cv.rgb).astype(np.uint8)
    nrm = normal_map(cv, strength)
    im = Image.fromarray(rgb, 'RGB').resize((SIZE, SIZE), Image.LANCZOS)
    im.save(os.path.join(OUT, f'hedge_{name}.jpg'), quality=90)
    Image.fromarray(nrm, 'RGB').resize((SIZE, SIZE), Image.LANCZOS).save(os.path.join(OUT, f'hedge_{name}_nor.jpg'), quality=92)
    print('surface', name, 'mean srgb', np.array(im).reshape(-1, 3).mean(0).astype(int))


def finish_cell(cv):
    """downsample, dilate the colour into the transparent texels (no dark mip fringes)"""
    rgb = lin2srgb(cv.rgb)
    a = cv.a * 255
    img = Image.fromarray(np.concatenate([rgb, a[..., None]], -1).astype(np.uint8), 'RGBA')
    img = img.resize((img.width // SS, img.height // SS), Image.LANCZOS)
    arr = np.array(img).astype(np.float32)
    alpha = arr[..., 3] > 30
    idx = ndimage.distance_transform_edt(~alpha, return_distances=False, return_indices=True)
    arr[..., :3] = arr[..., :3][idx[0], idx[1]]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')


def save_atlas(name, cells):
    out = Image.new('RGBA', (CELL * 2, CELL * 2))
    for i, c in enumerate(cells):
        out.paste(finish_cell(c), ((i % 2) * CELL, (i // 2) * CELL))
    out.save(os.path.join(OUT, f'leaf_{name}.png'), optimize=True)
    print('atlas', name)


# ---------------------------------------------------------------- what each shrub is made of
LEAF = {    # sRGB leaf colours: (body, fresh tips), and how strong the scan's own shading stays (glossy boxwood, dull
            # hairy azalea leaves)
    'boxwood': ([(50, 76, 30), (58, 86, 33), (44, 68, 27), (66, 92, 36)], [(104, 124, 46), (92, 116, 42), (118, 132, 52)], 0.9),
    'azalea': ([(58, 86, 36), (66, 96, 40), (50, 76, 31), (74, 102, 44)], [(104, 132, 54), (92, 124, 50)], 0.55),
    'autumn': ([(58, 84, 36), (52, 76, 32), (66, 92, 40), (60, 80, 34), (56, 82, 34), (70, 90, 38), (118, 100, 48),
                (104, 82, 40), (160, 58, 36), (140, 42, 40)], [(170, 66, 40), (184, 96, 46)], 0.55),     # (most still green)
    'violet': ([(98, 128, 56), (112, 140, 62), (88, 118, 50)], [(126, 150, 66)], 0.55),
    'pansy': ([(56, 92, 38), (66, 104, 44), (50, 84, 34)], [(76, 112, 48)], 0.6),
}
FLOWER = {  # sRGB petals, share, and the centre (colour, inner, outer radius as a fraction of the flower's half size)
    'azalea': [((214, 66, 148), 0.6, ((176, 40, 112), 0.0, 0.3)), ((226, 92, 166), 0.4, ((188, 56, 128), 0.0, 0.3))],
    'azalea_red': [((216, 40, 60), 0.55, ((164, 22, 40), 0.0, 0.3)), ((228, 62, 84), 0.3, ((172, 30, 50), 0.0, 0.3)),
                   ((234, 90, 116), 0.15, ((184, 48, 78), 0.0, 0.3))],
    'azalea_violet': [((196, 90, 200), 0.55, ((160, 64, 168), 0.0, 0.32)), ((212, 112, 212), 0.3, ((176, 80, 180), 0.0, 0.32)),
                      ((178, 78, 188), 0.15, ((144, 56, 156), 0.0, 0.32))],
    'pansy': [((244, 204, 40), 0.84, ((58, 36, 26), 0.0, 0.42)), ((246, 242, 230), 0.08, ((96, 60, 132), 0.0, 0.3)),
              ((112, 62, 152), 0.08, ((240, 200, 60), 0.0, 0.16))],
}


def pick(rnd, opts):
    r = rnd.random()
    for o in opts:
        r -= o[1]
        if r <= 0:
            return o
    return opts[-1]


def dirang(dx, dy):
    """the stamp angle (PIL: counter-clockwise as seen) that lays a stamp's +x along (dx, dy) in image coordinates"""
    return math.atan2(-dy, dx)


class Painter:
    """Collects leaves, flowers and twigs with their heights, then lays them on a canvas deepest first."""
    def __init__(self, S, ppm, rnd):
        self.S, self.ppm, self.rnd = S, ppm, rnd
        self.items = []
        self.leaves = [s for s in S['leaf'] if s.a.shape[1] / s.a.shape[0] < 4]

    def leaf(self, x, y, d, L, h, col, tilt, squash=None, gloss=0.9, stamps=None):
        r = self.rnd
        st = r.choice(stamps or self.leaves)
        sq = squash if squash is not None else r.uniform(0.45, 1.0)
        self.items.append((h, 'stamp', (st, x, y, L * self.ppm, sq, d, col, tilt, gloss, None, False)))

    def flower(self, x, y, D, h, petal, centre, tilt=(0, 0), squash=None):
        r = self.rnd
        st = r.choice(self.S['flower'])
        sq = squash if squash is not None else r.uniform(0.7, 1.0)
        self.items.append((h, 'stamp', (st, x, y, D * self.ppm, sq, r.uniform(0, 2 * math.pi), petal, tilt, 0.7, centre, True)))

    def twig(self, x0, y0, x1, y1, w, h, col):
        self.items.append((h, 'twig', (x0, y0, x1, y1, w * self.ppm, col)))

    def paint(self, cv, shade_of, thick=0.05):
        self.items.sort(key=lambda it: it[0])
        for h, kind, p in self.items:
            if kind == 'twig':
                x0, y0, x1, y1, w, col = p
                cv.line(x0, y0, x1, y1, w, tuple(c * shade_of(h, y0) for c in col), h)
                continue
            st, x, y, L, sq, d, col, tilt, gloss, centre, centred = p
            (det, al, bu), (ox, oy) = st.get(L, sq, d)
            if centred:
                ox, oy = al.shape[1] / 2, al.shape[0] / 2
            sh = shade_of(h, y)
            hh, ww = al.shape
            x0, y0 = int(round(x - ox)), int(round(y - oy))
            c = srgb2lin(col) * sh
            colimg = c * (det[..., None] ** gloss)
            if centre is not None:
                ccol, r0, r1 = centre
                yy, xx = np.mgrid[0:hh, 0:ww]
                dd = np.hypot((xx - ww / 2) / (ww / 2), (yy - hh / 2) / (hh / 2))
                f = 1 - np.clip((dd - r0) / max(r1 - r0, 1e-3), 0, 1)
                f = f * f * (3 - 2 * f)
                cc = srgb2lin(ccol) * sh * (det[..., None] ** 0.3)
                colimg = colimg * (1 - f[..., None]) + cc * f[..., None]
            self._blit(cv, colimg, al, bu, x0, y0, h, tilt, thick)

    def _blit(self, cv, colimg, al, bu, x0, y0, h, tilt, thick):
        hh, ww = al.shape
        offs = [(dx, dy) for dx in (-cv.n, 0, cv.n) for dy in (-cv.n, 0, cv.n)] if cv.wrap else [(0, 0)]
        for dx, dy in offs:
            X0, Y0 = x0 + dx, y0 + dy
            if X0 >= cv.n or Y0 >= cv.n or X0 + ww <= 0 or Y0 + hh <= 0:
                continue
            sx0, sy0 = max(0, -X0), max(0, -Y0)
            sx1, sy1 = min(ww, cv.n - X0), min(hh, cv.n - Y0)
            ds = (slice(Y0 + sy0, Y0 + sy1), slice(X0 + sx0, X0 + sx1))
            ss = (slice(sy0, sy1), slice(sx0, sx1))
            a = al[ss]
            a3 = a[..., None]
            cv.rgb[ds] = cv.rgb[ds] * (1 - a3) + colimg[ss] * a3
            cv.a[ds] = cv.a[ds] + a * (1 - cv.a[ds])
            cv.h[ds] = cv.h[ds] * (1 - a) + (h + bu[ss] * thick) * a
            cv.t[ds] = cv.t[ds] * (1 - a3) + np.array(tilt, np.float32) * a3


def shoot(P, cx, cy, hc, rc, nl, Lr, cols, fresh, p_fresh, gloss, up=None, sqr=(0.45, 1.0)):
    """a shoot seen end on: nl leaves round its tip, stalks inward, the tip highest. up: (dx, dy) a shoot seen from
    the side instead (its leaves lean that way)"""
    r = P.rnd
    for j in range(nl):
        rr = rc * r.random() ** 0.8
        th = r.uniform(0, 2 * math.pi)
        dx, dy = math.cos(th), math.sin(th)
        if up is not None:
            dx, dy = dx * 0.6 + up[0] * 0.8, dy * 0.6 + up[1] * 0.8
            l = math.hypot(dx, dy) or 1
            dx, dy = dx / l, dy / l
        x, y = cx + dx * rr * 0.5 * P.ppm, cy + dy * rr * 0.5 * P.ppm
        f = rr / rc
        h = hc - 0.1 * f + r.uniform(-0.02, 0.02)
        col = r.choice(fresh) if (r.random() < p_fresh * (1 - f) and fresh) else r.choice(cols)
        col = jit(col, r, 0.08)
        tilt = (dx * (0.25 + 0.5 * f) + r.uniform(-0.25, 0.25), dy * (0.25 + 0.5 * f) + r.uniform(-0.25, 0.25))
        P.leaf(x, y, dirang(dx, dy) + r.uniform(-0.5, 0.5), r.uniform(*Lr), h, col, tilt, squash=r.uniform(*sqr), gloss=gloss)


def bumps(n, ppm, size_m, rnd):
    """a smooth seamless field 0..1: the dimples of a clipped face, size_m across"""
    g = np.random.default_rng(rnd.randrange(1 << 30)).random((n // 8, n // 8)).astype(np.float32)
    g = ndimage.gaussian_filter(g, size_m * ppm / 8 / 2.5, mode='wrap')
    g = (g - g.min()) / max(g.max() - g.min(), 1e-6)
    return lambda x, y: float(g[int(y / 8) % g.shape[0], int(x / 8) % g.shape[1]])


def surface_painter(name, S):
    rnd = random.Random(zlib.crc32(name.encode()))
    n = SIZE * SS
    T = TILE[name]
    ppm = n / T
    P = Painter(S, ppm, rnd)
    B = bumps(n, ppm, 0.07, rnd)
    A = T * T                                       # m^2 of the tile
    bark = [(92, 78, 60), (110, 96, 74), (78, 66, 52)]
    if name == 'boxwood':
        cols, fresh, gloss = LEAF['boxwood']
        BOX = (0.65, 1.3)                           # (rounder than the scan's leaves)
        for k in range(int(A * 900)):               # the twigs inside
            x, y, a = rnd.uniform(0, n), rnd.uniform(0, n), rnd.uniform(0, 2 * math.pi)
            L = rnd.uniform(0.03, 0.07) * ppm
            P.twig(x, y, x + math.cos(a) * L, y + math.sin(a) * L, rnd.uniform(0.002, 0.003), rnd.uniform(0.0, 0.2), rnd.choice(bark))
        for k in range(int(A * 5000)):              # old leaves deep in
            x, y = rnd.uniform(0, n), rnd.uniform(0, n)
            P.leaf(x, y, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.011, 0.016), rnd.uniform(0.05, 0.5),
                   jit(rnd.choice(cols), rnd, 0.1), (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5)),
                   squash=rnd.uniform(*BOX), gloss=gloss)
        for k in range(int(A * 2600)):              # the clipped shoots' tips
            x, y = rnd.uniform(0, n), rnd.uniform(0, n)
            shoot(P, x, y, 0.55 * rnd.random() ** 0.4 + 0.45 * B(x, y), rnd.uniform(0.014, 0.022),
                  rnd.randint(8, 13), (0.011, 0.017), cols, fresh, 0.3, gloss, sqr=BOX)
        return P, (22, 30, 15), 0.05
    leafset = {'azalea_summer': 'azalea', 'azalea': 'azalea', 'azalea_red': 'azalea', 'azalea_autumn': 'autumn',
               'azalea_violet': 'violet', 'pansy': 'pansy'}[name]
    cols, fresh, gloss = LEAF[leafset]
    if name == 'pansy':
        for k in range(int(A * 900)):               # rosettes of small round leaves
            shoot(P, rnd.uniform(0, n), rnd.uniform(0, n), rnd.random() ** 0.8 * 0.7, rnd.uniform(0.03, 0.045),
                  rnd.randint(5, 8), (0.022, 0.034), cols, fresh, 0.2, gloss)
        for k in range(int(A * 520)):               # flowers held over them, facing up and out
            petal = pick(rnd, FLOWER['pansy'])
            P.flower(rnd.uniform(0, n), rnd.uniform(0, n), rnd.uniform(0.042, 0.058), 0.72 + rnd.random() * 0.28,
                     jit(petal[0], rnd, 0.06), petal[2], (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3)))
        return P, (34, 34, 22), 0.06
    if name == 'azalea_violet':
        # 진달래 in April: a cloud of flowers in ones to threes along thin grey twigs, a few new leaves
        for k in range(int(A * 700)):
            x, y, a = rnd.uniform(0, n), rnd.uniform(0, n), rnd.uniform(0, 2 * math.pi)
            L = rnd.uniform(0.05, 0.13) * ppm
            P.twig(x, y, x + math.cos(a) * L, y + math.sin(a) * L, rnd.uniform(0.0018, 0.0035), rnd.uniform(0.0, 0.6),
                   rnd.choice([(128, 116, 100), (110, 100, 88), (140, 126, 108)]))
        for k in range(int(A * 300)):
            shoot(P, rnd.uniform(0, n), rnd.uniform(0, n), rnd.uniform(0.3, 0.8), rnd.uniform(0.015, 0.025),
                  rnd.randint(2, 4), (0.018, 0.03), cols, fresh, 0.5, gloss)
        for k in range(int(A * 560)):
            cx, cy = rnd.uniform(0, n), rnd.uniform(0, n)
            hc = 0.6 * rnd.random() ** 0.5 + 0.4 * B(cx, cy)
            for j in range(rnd.choice((1, 2, 2, 3))):
                petal = pick(rnd, FLOWER['azalea_violet'])
                a = rnd.uniform(0, 2 * math.pi)
                d = rnd.uniform(0.0, 0.025) * ppm
                P.flower(cx + math.cos(a) * d, cy + math.sin(a) * d, rnd.uniform(0.034, 0.046), hc + 0.08 + 0.04 * j,
                         jit(petal[0], rnd, 0.06), petal[2], (math.cos(a) * 0.3, math.sin(a) * 0.3))
        return P, (58, 50, 48), 0.06
    # 철쭉 · 영산홍: whorls of leaves at the shoot tips; in bloom a truss of flowers on many tips
    bloom = {'azalea_red': (0.62, (2, 3)), 'azalea': (0.29, (1, 2))}.get(name)
    for k in range(int(A * 2200)):                  # old leaves inside
        x, y = rnd.uniform(0, n), rnd.uniform(0, n)
        P.leaf(x, y, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.022, 0.034), rnd.uniform(0.05, 0.45),
               jit(rnd.choice(cols), rnd, 0.1), (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5)), gloss=gloss)
    for k in range(int(A * 1000)):
        cx, cy = rnd.uniform(0, n), rnd.uniform(0, n)
        hc = 0.6 * rnd.random() ** 0.5 + 0.4 * B(cx, cy)
        shoot(P, cx, cy, hc, rnd.uniform(0.024, 0.036), rnd.randint(6, 9), (0.024, 0.038), cols, fresh, 0.3, gloss)
        if bloom and rnd.random() < bloom[0]:
            for j in range(rnd.randint(*bloom[1])):
                petal = pick(rnd, FLOWER[name])
                a = rnd.uniform(0, 2 * math.pi)
                d = rnd.uniform(0.008, 0.02) * ppm
                P.flower(cx + math.cos(a) * d, cy + math.sin(a) * d, rnd.uniform(0.04, 0.052), hc + 0.07 + 0.03 * j,
                         jit(petal[0], rnd, 0.06), petal[2], (math.cos(a) * 0.35, math.sin(a) * 0.35))
    return P, (24, 30, 18), 0.06


def make_surface(name, S):
    P, bg, thick = surface_painter(name, S)
    cv = Canvas(SIZE * SS, True, bg=bg)
    P.paint(cv, lambda h, y: 0.3 + 0.7 * min(1.0, max(0.0, h)) ** 0.85, thick)
    cavity(cv, 5 * SS)
    save_surface(name, cv, 40.0)


# ---------------------------------------------------------------- sprig cards
def card_painter(name, S, rnd):
    """one cell: a sprig standing on the cell's bottom edge (where it leaves the body), its tips at the top"""
    n = CELL * SS
    ppm = n / CARD_M[name]
    P = Painter(S, ppm, rnd)
    bx, by = n * 0.5, n * 0.995
    bark = [(96, 80, 60), (112, 96, 72)]
    leafset = {'boxwood': 'boxwood', 'azalea_summer': 'azalea', 'azalea': 'azalea', 'azalea_red': 'azalea',
               'azalea_autumn': 'autumn', 'azalea_violet': 'violet', 'pansy': 'pansy'}[name]
    cols, fresh, gloss = LEAF[leafset]
    if name == 'pansy':
        for k in range(rnd.randint(9, 13)):          # the leaves low down
            x = bx + rnd.uniform(-0.38, 0.38) * n
            y = by - rnd.uniform(0.0, 0.3) * n
            a = rnd.uniform(-2.6, -0.5)
            P.leaf(x, y, dirang(math.cos(a), math.sin(a)), rnd.uniform(0.026, 0.038), 0.2 + 0.3 * (by - y) / n,
                   jit(rnd.choice(cols), rnd, 0.08), (math.cos(a) * 0.4, 0.2), gloss=gloss)
        for k in range(rnd.randint(3, 5)):           # flowers on short stalks
            x = bx + rnd.uniform(-0.32, 0.32) * n
            y = by - rnd.uniform(0.42, 0.78) * n
            P.twig(x + rnd.uniform(-8, 8), by - 0.15 * n, x, y, 0.0014, 0.6, (96, 132, 60))
            petal = pick(rnd, FLOWER['pansy'])
            P.flower(x, y, rnd.uniform(0.044, 0.056), 0.7 + 0.3 * (by - y) / n, jit(petal[0], rnd, 0.06), petal[2],
                     (0, -0.3), squash=rnd.uniform(0.75, 1.0))
        return P
    nsh = {'boxwood': (8, 12), 'azalea_violet': (4, 6)}.get(name, (5, 7))
    tips = []
    leafL = (0.011, 0.016) if name == 'boxwood' else (0.024, 0.036)
    sqr = (0.65, 1.3) if name == 'boxwood' else (0.45, 1.0)
    # a dense mass low down, where the sprigs leave the clipped face (진달래: twigs and flowers)
    for k in range(rnd.randint(70, 95) if name == 'boxwood' else rnd.randint(14, 20) if name == 'azalea_violet' else rnd.randint(30, 42)):
        x = bx + max(-0.33, min(0.33, rnd.gauss(0, 0.17))) * n
        y = by - min(0.42, abs(rnd.gauss(0, 0.18))) * n
        a = math.atan2(y - by - 0.1 * n, x - bx)
        P.leaf(x, y, dirang(math.cos(a), math.sin(a)) + rnd.uniform(-0.8, 0.8), rnd.uniform(*leafL),
               0.25 + 0.4 * (by - y) / n, jit(rnd.choice(cols), rnd, 0.1), (math.cos(a) * 0.4, math.sin(a) * 0.4),
               squash=rnd.uniform(*sqr), gloss=gloss)
    twigcol = [(126, 110, 90), (140, 124, 102)] if name != 'azalea_violet' else [(132, 120, 104), (146, 134, 116)]
    for k in range(rnd.randint(*nsh)):
        a = math.radians(-90 + rnd.uniform(-62, 62))  # image y down: -90 is straight up
        L = rnd.uniform(0.35, 0.78) * n * (1 - 0.25 * abs(math.cos(a)))
        tx, ty = bx + math.cos(a) * L, by + math.sin(a) * L
        P.twig(bx + rnd.uniform(-6, 6), by, tx, ty, 0.0018 if name == 'boxwood' else 0.0026, 0.15, rnd.choice(twigcol))
        tips.append((tx, ty, a, L))
    fl = {'azalea_red': (2, 3), 'azalea': (0, 2), 'azalea_violet': (1, 3)}.get(name)
    for tx, ty, a, L in tips:
        ux, uy = math.cos(a), math.sin(a)
        # leaves along the shoot (boxwood: opposite pairs), a tuft or whorl at the tip
        step = 0.009 if name == 'boxwood' else 0.016 if name != 'azalea_violet' else 0.05
        steps = int(L / (step * ppm))
        for s_ in range(steps):
            t = (s_ + 0.5) / steps
            x, y = bx + ux * L * t, by + uy * L * t
            for side in ((-1, 1) if name == 'boxwood' else (rnd.choice((-1, 1)),)):
                dx, dy = ux * 0.6 - uy * side, uy * 0.6 + ux * side
                col = rnd.choice(fresh) if rnd.random() < 0.35 * t * t else rnd.choice(cols)
                P.leaf(x, y, dirang(dx, dy) + rnd.uniform(-0.4, 0.4), rnd.uniform(*leafL) * (0.8 if name == 'azalea_violet' else 1),
                       0.3 + 0.6 * t, jit(col, rnd, 0.08), (dx * 0.4, dy * 0.4), squash=rnd.uniform(*sqr), gloss=gloss)
        if name == 'boxwood':
            shoot(P, tx, ty, 0.95, 0.018, rnd.randint(7, 10), leafL, cols, fresh, 0.5, gloss, up=(ux, uy), sqr=sqr)
            continue
        if name != 'azalea_violet':
            shoot(P, tx, ty, 0.8, 0.03, rnd.randint(6, 9), (0.026, 0.04), cols, fresh, 0.3, gloss, up=(ux, uy))
        elif rnd.random() < 0.5:
            shoot(P, tx, ty, 0.6, 0.02, rnd.randint(2, 3), (0.018, 0.028), cols, fresh, 0.5, gloss, up=(ux, uy))
        if fl:              # a truss of flowers over the tip
            for j in range(rnd.randint(*fl)):
                petal = pick(rnd, FLOWER[name])
                ang = rnd.uniform(0, 2 * math.pi)
                d = rnd.uniform(0.0, 0.022) * ppm
                D = rnd.uniform(0.042, 0.052) if name != 'azalea_violet' else rnd.uniform(0.036, 0.046)
                P.flower(tx + math.cos(ang) * d, ty + math.sin(ang) * d - 0.01 * ppm, D, 1.0 + 0.05 * j,
                         jit(petal[0], rnd, 0.06), petal[2], (math.cos(ang) * 0.3, math.sin(ang) * 0.3))
            if name == 'azalea_violet':         # flowers all along the twig
                for s_ in range(rnd.randint(3, 6)):
                    t = rnd.uniform(0.25, 0.85)
                    petal = pick(rnd, FLOWER[name])
                    o = rnd.uniform(-0.012, 0.012) * ppm
                    P.flower(bx + ux * L * t - uy * o, by + uy * L * t + ux * o, rnd.uniform(0.034, 0.044), 0.6 + 0.3 * t,
                             jit(petal[0], rnd, 0.06), petal[2])
    return P


def make_atlas(name, S):
    rnd = random.Random(zlib.crc32(('card' + name).encode()))
    cells = []
    n = CELL * SS
    for i in range(4):
        P = card_painter(name, S, rnd)
        cv = Canvas(n, False)
        # darker toward the bottom edge, where the sprig leaves the body
        P.paint(cv, lambda h, y: (0.55 + 0.45 * min(1.0, max(0.0, h)) ** 0.8) * (0.82 + 0.18 * (1 - y / n)), 0.05)
        cells.append(cv)
    save_atlas(name, cells)


NAMES = ['boxwood', 'azalea_summer', 'azalea', 'azalea_red', 'azalea_violet', 'azalea_autumn', 'pansy']

if __name__ == '__main__' and ONLY != {'__none__'}:
    S = cut_stamps()
    for nm in NAMES:
        if ONLY and nm not in ONLY:
            continue
        make_surface(nm, S)
        make_atlas(nm, S)
