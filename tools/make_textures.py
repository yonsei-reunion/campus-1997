"""Procedurally paint foliage atlases, 1990s shop signs and the main-gate plaque.

Outputs (web/public/assets/textures):
  leaf_<species>[_<season>].png   2x2 atlas of leaf-cluster cards, RGBA (alpha-tested)
  litter_ginkgo.png               fallen ginkgo leaves, seamless tile, alpha = each leaf's rank
  litter_petals.png               fallen cherry petals, the same
  sign_shops.png                  4x4 atlas of 1997 Sinchon storefront signboards
  sign_gate.png                   延世大學校 gate plaque
  banner_halls.png                the cloth banners on 백주년기념관's museum porch and over 대우관's door
Run: .venv/bin/python tools/make_textures.py
"""
import json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage
from webp_textures import to_webp

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'web/public/assets/textures')
os.makedirs(OUT, exist_ok=True)
SS = 2                     # supersampling
ONLY = set(sys.argv[1:])     # optional: only rebuild these atlases, e.g. `make_textures.py azalea_red`
CELL = 512                 # final cell size, atlas = 2x2 cells


def jitter(c, rnd, amt=0.12):
    return tuple(int(max(0, min(255, v * (1 + rnd.uniform(-amt, amt)) + rnd.uniform(-8, 8)))) for v in c)


def rot(pts, a, cx, cy, s=1.0):
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + (x * ca - y * sa) * s, cy + (x * sa + y * ca) * s) for x, y in pts]


# ---------------------------------------------------------------- leaf outlines (unit, stem at origin, tip toward -y)
def shape_ginkgo(rnd):
    pts = [(0, 0)]
    spread = math.radians(rnd.uniform(55, 75))
    r = 1.0
    for i in range(25):
        a = -math.pi / 2 - spread + 2 * spread * i / 24
        rr = r * (1 - 0.18 * math.exp(-((i - 12) / 1.6) ** 2))      # centre notch
        rr *= 1 + 0.03 * math.sin(i * 2.3)
        pts.append((rr * math.cos(a) * 0.95, rr * math.sin(a) * 0.95 - 0.35))
    return [(x, y) for x, y in pts], 0.35


def shape_ovate(rnd, serr=0.0, w=0.42, lo=1.0):
    pts = []
    n = 34
    for i in range(n + 1):
        t = i / n
        y = -t * lo
        x = w * math.sin(math.pi * t ** 0.85) * (1 - 0.15 * t)
        if serr and i % 2:
            x *= 1 + serr
        pts.append((x, y))
    return pts + [(-x, y) for x, y in reversed(pts)], 0.1


def shape_maple(rnd):
    pts = []
    lobes = [(-90, 1.0), (-35, 0.85), (20, 0.55), (160, 0.55), (215, 0.85)]
    n = 80
    for i in range(n):
        a = 2 * math.pi * i / n
        deg = math.degrees(a) - 270
        r = 0.25
        for c, L in [(-90, 1.0), (-145, 0.85), (-35, 0.85), (-190, 0.5), (10, 0.5)]:
            d = abs(((math.degrees(a) - 180) - c + 540) % 360 - 180)
            r = max(r, L * math.exp(-(d / 16) ** 2))
        pts.append((r * math.cos(a), r * math.sin(a) - 0.1))
    return pts, 0.15


def shape_oak(rnd):
    pts = []
    n = 40
    for i in range(n + 1):
        t = i / n
        x = 0.33 * math.sin(math.pi * t ** 0.9) * (1 + 0.28 * math.sin(t * math.pi * 9))
        pts.append((x, -t))
    return pts + [(-x, y) for x, y in reversed(pts)], 0.08


def shape_ivy(rnd):
    pts = []
    n = 60
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 0.45
        for c, L in [(-90, 0.95), (-150, 0.7), (-30, 0.7), (-200, 0.5), (20, 0.5)]:
            d = abs(((math.degrees(a)) - c + 540) % 360 - 180)
            r = max(r, L * math.exp(-(d / 28) ** 2))
        pts.append((r * math.cos(a), r * math.sin(a) - 0.05))
    return pts, 0.1


def shape_obovate(rnd, w=0.36):
    """목련: broadest beyond the middle, a short blunt point"""
    pts = []
    n = 34
    for i in range(n + 1):
        t = i / n
        x = w * math.sin(math.pi * t ** 1.3) ** 0.8 * (1 - 0.1 * t)
        pts.append((x, -t))
    return pts + [(-x, y) for x, y in reversed(pts)], 0.12


def shape_poplar(rnd):
    """은백양: a broad leaf of three to five shallow lobes with coarse teeth"""
    pts = []
    n = 72
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 0.42
        for c, L in [(-90, 0.9), (-140, 0.68), (-40, 0.68), (-190, 0.5), (10, 0.5)]:
            d = abs((math.degrees(a) - c + 540) % 360 - 180)
            r = max(r, L * math.exp(-(d / 30) ** 2))
        r *= 1 + 0.05 * math.sin(a * 11)
        pts.append((r * math.cos(a), r * math.sin(a) - 0.1))
    return pts, 0.18


def shape_tepal(rnd):
    """one tepal of a magnolia flower (tip toward -y): narrow at the base, broad and rounded at the tip"""
    w = 0.3 * rnd.uniform(0.85, 1.1)
    right = [(w * math.sin(math.pi * (i / 20) ** 1.6) ** 0.8, -i / 20) for i in range(21)]
    return right + [(-x, y) for x, y in reversed(right[1:])], 0.0


def draw_leaf(d, shape, cx, cy, ang, size, col, rnd, vein=True):
    pts, stem = shape
    P = rot(pts, ang, cx, cy, size)
    base = jitter(col, rnd)
    d.polygon(P, fill=base + (255,))
    # light/dark half for a fake midrib fold
    half = [p for p in pts if p[0] >= 0] + [(0, pts[0][1])]
    if len(half) > 3:
        d.polygon(rot(half, ang, cx, cy, size), fill=tuple(int(v * 0.86) for v in base) + (255,))
    if vein:
        tip = min(pts, key=lambda p: p[1])
        a0 = rot([(0, 0)], ang, cx, cy, size)[0]
        a1 = rot([(0, tip[1] * 0.85)], ang, cx, cy, size)[0]
        d.line([a0, a1], fill=tuple(min(255, int(v * 1.15)) for v in base) + (255,), width=max(1, int(size * 0.04)))
    s0 = rot([(0, 0)], ang, cx, cy, size)[0]
    s1 = rot([(0, stem)], ang, cx, cy, size)[0]
    d.line([s0, s1], fill=(70, 60, 30, 255), width=max(1, int(size * 0.05)))


def finish(img):
    """downsample, dilate colour into transparent texels (no dark mip fringes)."""
    img = img.resize((img.width // SS, img.height // SS), Image.LANCZOS)
    a = np.array(img).astype(np.float32)
    alpha = a[..., 3] > 30
    rgb = a[..., :3]
    idx = ndimage.distance_transform_edt(~alpha, return_distances=False, return_indices=True)
    rgb = rgb[idx[0], idx[1]]
    out = np.concatenate([rgb, a[..., 3:4]], -1)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')


def cluster_cell(kind, palette, rnd, flowers=None):
    S = CELL * SS
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S / 2, S / 2
    # twigs
    twig_col = (85, 70, 50, 255)
    tips = []
    for k in range(rnd.randint(4, 6)):
        a = rnd.uniform(0, 2 * math.pi)
        L = rnd.uniform(0.25, 0.45) * S
        x0, y0 = cx + rnd.uniform(-0.05, 0.05) * S, S * 0.97
        x1, y1 = cx + math.cos(a) * L * 0.8, cy + math.sin(a) * L * 0.7
        d.line([(x0, y0), (x1, y1)], fill=twig_col, width=int(S * 0.008))
        tips.append((x0, y0, x1, y1))
    if kind == 'ivy_bare':
        return ivy_bare_cell(palette, rnd)
    if kind in ('twigs', 'magnolia_bloom'):
        return twig_cell(kind, palette, rnd)
    if kind == 'cherry_bloom':
        return blossom_cell(palette, rnd, flowers)
    if kind == 'pine':
        for (x0, y0, x1, y1) in tips * 3:
            for t in np.linspace(0.3, 1.0, 9):
                px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                for k in range(26):
                    a = rnd.uniform(0, 2 * math.pi)
                    L = rnd.uniform(0.05, 0.11) * S
                    c = jitter(palette[rnd.randrange(len(palette))], rnd, 0.15)
                    d.line([(px, py), (px + math.cos(a) * L, py + math.sin(a) * L * 0.8)], fill=c + (255,), width=int(S * 0.004) + 1)
        return finish(img)
    shapes = {'ginkgo': shape_ginkgo, 'zelkova': lambda r: shape_ovate(r, 0.08, 0.36), 'cherry': lambda r: shape_ovate(r, 0.05, 0.4),
              'maple': shape_maple, 'oak': shape_oak, 'ivy': shape_ivy, 'boxwood': lambda r: shape_ovate(r, 0.0, 0.55, 0.9),
              'azalea': lambda r: shape_ovate(r, 0.0, 0.33), 'magnolia': shape_obovate, 'poplar': shape_poplar,
              'pansy': lambda r: shape_ovate(r, 0.0, 0.5, 0.8)}
    size_rng = {'ginkgo': (0.055, 0.075), 'zelkova': (0.05, 0.075), 'cherry': (0.06, 0.085), 'maple': (0.06, 0.085),
                'oak': (0.07, 0.095), 'ivy': (0.06, 0.09), 'boxwood': (0.022, 0.03), 'azalea': (0.04, 0.055),
                'magnolia': (0.085, 0.115), 'poplar': (0.06, 0.085), 'pansy': (0.03, 0.042)}[kind]
    n = {'boxwood': 1500, 'azalea': 420, 'ivy': 330, 'magnolia': 150, 'pansy': 900}.get(kind, 230)
    for k in range(n):
        # leaves concentrate in an ellipse (cluster), denser in the middle; ivy: a flatter mat filling the card
        r = (rnd.random() ** (0.45 if kind == 'ivy' else 0.6)) * (0.47 if kind == 'ivy' else 0.45)
        a = rnd.uniform(0, 2 * math.pi)
        x = cx + math.cos(a) * r * S
        y = cy + math.sin(a) * r * S * 0.9
        if kind in ('boxwood', 'pansy'):
            x = rnd.uniform(0.02, 0.98) * S
            y = rnd.uniform(0.02, 0.98) * S
        elif kind == 'ivy':           # a square mat of leaves: overlapping cards close up into a continuous cover
            x = rnd.uniform(0.07, 0.93) * S
            y = rnd.uniform(0.07, 0.93) * S
        ang = math.atan2(y - cy, x - cx) + math.pi / 2 + rnd.uniform(-0.8, 0.8)
        # top of cluster brighter (sky light), bottom darker
        shade = 1.08 - 0.3 * ((y / S) - 0.2)
        col = palette[rnd.randrange(len(palette))]
        col = tuple(int(min(255, c * shade)) for c in col)
        draw_leaf(d, shapes[kind](rnd), x, y, ang, rnd.uniform(*size_rng) * S, col, rnd, vein=kind not in ('boxwood',))
    for fl in (flowers if isinstance(flowers, list) else [flowers] if flowers else []):    # (one kind, or a list)
        fcol, fn, fs = fl[:3]
        centre = fl[3] if len(fl) > 3 else (230, 200, 90)
        for k in range(fn):
            r = (rnd.random() ** 0.5) * 0.46
            a = rnd.uniform(0, 2 * math.pi)
            x = cx + math.cos(a) * r * S
            y = cy + math.sin(a) * r * S * 0.9
            if kind == 'pansy':                 # (a bed: flowers all over the card)
                x, y = rnd.uniform(0.04, 0.96) * S, rnd.uniform(0.04, 0.96) * S
            sz = rnd.uniform(*fs) * S
            c = jitter(fcol, rnd, 0.06)
            for p in range(5):
                pa = p * 2 * math.pi / 5 + rnd.uniform(0, 1)
                px, py = x + math.cos(pa) * sz * 0.55, y + math.sin(pa) * sz * 0.55
                d.ellipse([px - sz * 0.45, py - sz * 0.45, px + sz * 0.45, py + sz * 0.45], fill=c + (255,))
            d.ellipse([x - sz * 0.18, y - sz * 0.18, x + sz * 0.18, y + sz * 0.18], fill=centre + (255,))
    return finish(img)


def ivy_bare_cell(palette, rnd):
    """담쟁이 in mid-April: a web of brown woody vines stuck to the wall, the new leaves (mostly yellow-green, some
    bronze-red) opening at most of the nodes, two to four to a node: the vines still show between them
    (reference/2003_봄_*.jpg)."""
    S = CELL * SS
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    nodes = []
    for k in range(rnd.randint(5, 7)):
        # a vine wanders up across the card, forking now and then
        x, y = rnd.uniform(0.1, 0.9) * S, S * rnd.uniform(0.85, 1.0)
        a = -math.pi / 2 + rnd.uniform(-0.6, 0.6)
        w = S * rnd.uniform(0.010, 0.016)
        for step in range(rnd.randint(14, 22)):
            a += rnd.uniform(-0.45, 0.45)
            a = -math.pi / 2 + max(-1.1, min(1.1, a + math.pi / 2))
            L = S * rnd.uniform(0.03, 0.055)
            nx, ny = x + math.cos(a) * L, y + math.sin(a) * L
            c = jitter((92, 70, 50), rnd, 0.15)
            d.line([(x, y), (nx, ny)], fill=c + (255,), width=max(2, int(w)))
            if rnd.random() < 0.35:                     # side shoot
                b = a + rnd.choice((-1, 1)) * rnd.uniform(0.7, 1.3)
                L2 = S * rnd.uniform(0.04, 0.09)
                d.line([(x, y), (x + math.cos(b) * L2, y + math.sin(b) * L2)], fill=c + (255,), width=max(2, int(w * 0.6)))
                nodes.append((x + math.cos(b) * L2, y + math.sin(b) * L2))
            nodes.append((nx, ny))
            x, y = nx, ny
            w *= 0.97
            if not (0 <= x <= S and 0 <= y <= S):
                break
    for (x, y) in nodes:
        if rnd.random() < 0.2:
            continue
        col = palette[rnd.randrange(len(palette))]
        for m in range(rnd.randint(2, 4)):
            draw_leaf(d, shape_ivy(rnd), x + rnd.uniform(-12, 12), y + rnd.uniform(-12, 12), rnd.uniform(0, 6.28),
                      rnd.uniform(0.028, 0.05) * S, col, rnd, vein=False)
    return finish(img)


def twig_cell(kind, palette, rnd):
    """A bare spray of twigs (deciduous trees before the leaves, mid-April): a few shoots forking up from the bottom
    of the card, thinning, a bud at every tip.  magnolia_bloom: 백목련 in flower on the bare wood, a big ivory cup of
    tepals at most tips (palette: the tepal colours), furry grey buds at the rest."""
    S = CELL * SS
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    tips = []
    wood = (96, 84, 72) if kind == 'twigs' else (88, 76, 66)

    def branch(x, y, a, L, w, depth):
        nx, ny = x + math.cos(a) * L, y + math.sin(a) * L
        c = jitter(wood, rnd, 0.1)
        d.line([(x, y), (nx, ny)], fill=c + (255,), width=max(2, int(w)))
        if depth == 0:
            tips.append((nx, ny, a))
            return
        for k in range(rnd.choice((2, 2, 3) if kind == 'twigs' else (2, 3))):
            b = a + rnd.uniform(-0.75, 0.75)
            b = -math.pi / 2 + max(-1.3, min(1.3, b + math.pi / 2))          # (the spray grows up and out)
            branch(nx, ny, b, L * rnd.uniform(0.6, 0.78), w * 0.68, depth - 1)
    for k in range(rnd.randint(3, 4)):
        branch(S * rnd.uniform(0.3, 0.7), S * 0.99, -math.pi / 2 + rnd.uniform(-0.6, 0.6), S * rnd.uniform(0.17, 0.23),
               S * 0.016, 5 if kind == 'twigs' else 4)
    if kind == 'twigs':
        for (x, y, a) in tips:
            r = S * rnd.uniform(0.005, 0.008)
            c = jitter(palette[rnd.randrange(len(palette))], rnd, 0.1)
            d.ellipse([x - r, y - r * 1.4, x + r, y + r * 1.4], fill=c + (255,))
        return finish(img)
    rnd.shuffle(tips)
    for i, (x, y, a) in enumerate(tips):
        if i % 3 == 2:                                                       # an unopened bud: grey fur
            r = S * 0.012
            d.ellipse([x - r, y - r * 1.6, x + r, y + r * 1.2], fill=jitter((150, 140, 120), rnd, 0.1) + (255,))
            continue
        size = rnd.uniform(0.055, 0.075) * S
        a = a + rnd.uniform(-0.3, 0.3)
        k_n = 7
        order = sorted(range(k_n), key=lambda k: -abs(k - (k_n - 1) / 2))   # the outer (back) tepals first
        for k in order:
            pa = a + (k - (k_n - 1) / 2) * 0.24 + rnd.uniform(-0.08, 0.08)
            front = 1 - abs(k - (k_n - 1) / 2) / ((k_n - 1) / 2)
            col = palette[rnd.randrange(len(palette))]
            col = tuple(int(min(255, v * (0.86 + 0.16 * front))) for v in col)
            pts, _ = shape_tepal(rnd)
            d.polygon(rot(pts, pa + math.pi / 2, x, y, size * rnd.uniform(0.85, 1.05)), fill=col + (255,))
            # a faint rosy flush at the base of each tepal (백목련's ivory, now and then a blush)
            base = tuple(int(v * 0.82 + p * 0.18) for v, p in zip(col, (210, 150, 160)))
            d.polygon(rot([(px * 0.8, py * 0.3) for px, py in pts], pa + math.pi / 2, x, y, size), fill=base + (255,))
        r = S * 0.007
        d.ellipse([x - r, y - r, x + r, y + r], fill=(110, 95, 60, 255))
    return finish(img)


def blossom_cell(palette, rnd, flowers):
    """벚꽃 in full bloom (mid-April, 2003_봄_언더우드관정원_남쪽계단_벚나무.jpg): a spray of dark twigs carrying the
    blossom in clusters (송이) of a few flowers on long stalks, crowded into one mass in the middle of the card and
    breaking up into separate clusters toward its edge, so a card has no round outline and the twigs show between the
    clusters; a few small bronze-green leaves just opening.  palette: the leaves; flowers: (colour, number of
    flowers, size range[, centre colour])."""
    S = CELL * SS
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fcol, fn, fs = flowers[:3]
    centre = flowers[3] if len(flowers) > 3 else (226, 150, 120)
    cx, cy = S / 2, S / 2
    # clusters: a few overlapping in the middle, the rest spread out, smaller toward the edge
    clusters = []
    for k in range(rnd.randint(31, 35)):
        r = 0.39 * (rnd.random() ** 0.6 if k > 5 else rnd.uniform(0, 0.35))
        a = rnd.uniform(0, 2 * math.pi)
        rc = rnd.uniform(0.085, 0.125) * (1 - 0.4 * r / 0.39)
        clusters.append((cx + math.cos(a) * r * S, cy + math.sin(a) * r * S * 0.92, rc * S))
    # twigs: each cluster hangs from the nearest point already on the spray, which grows from the foot of the card
    tree = [(cx + rnd.uniform(-0.04, 0.04) * S, S * 0.98)]
    order = sorted(clusters, key=lambda c: (c[0] - tree[0][0]) ** 2 + (c[1] - tree[0][1]) ** 2)
    for (x, y, rc) in order:
        px, py = min(tree, key=lambda q: (q[0] - x) ** 2 + (q[1] - y) ** 2)
        mx, my = (px + x) / 2 + rnd.uniform(-0.03, 0.03) * S, (py + y) / 2 + rnd.uniform(-0.03, 0.03) * S
        w = max(3, int(S * 0.009 * (0.6 + 0.4 * (y / S))))
        col = jitter((74, 58, 50), rnd, 0.1) + (255,)
        d.line([(px, py), (mx, my), (x, y)], fill=col, width=w, joint='curve')
        tree += [(mx, my), (x, y)]
    # leaves first (the flowers cover most of them), then the stalks, then the flowers back to front
    for (x, y, rc) in clusters:
        for m in range(rnd.choice((0, 0, 1, 1, 2))):
            a = rnd.uniform(0, 2 * math.pi)
            lx, ly = x + math.cos(a) * rc * 0.8, y + math.sin(a) * rc * 0.8
            draw_leaf(d, shape_ovate(rnd, 0.05, 0.4), lx, ly, a + math.pi / 2 + rnd.uniform(-0.5, 0.5),
                      rnd.uniform(0.035, 0.05) * S, palette[rnd.randrange(len(palette))], rnd)
    area = sum(rc * rc for (_, _, rc) in clusters)
    blooms = []
    for (x, y, rc) in clusters:
        for m in range(max(3, round(fn * rc * rc / area))):
            a = rnd.uniform(0, 2 * math.pi)
            r = rc * rnd.random() ** 0.6
            fx, fy = x + math.cos(a) * r, y + math.sin(a) * r
            d.line([(x, y), (fx, fy)], fill=jitter((96, 104, 60), rnd, 0.1) + (255,), width=max(2, int(S * 0.003)))
            # a cluster's underside in shade, its top in the sky light
            shade = 0.93 + 0.07 * max(-1, min(1, (y - fy) / rc))
            blooms.append((rnd.random(), fx, fy, shade))
        for m in range(rnd.randint(0, 2)):                     # an unopened bud on the rim
            a = rnd.uniform(0, 2 * math.pi)
            bx, by, br = x + math.cos(a) * rc * 1.05, y + math.sin(a) * rc * 1.05, S * 0.006
            d.line([(x, y), (bx, by)], fill=(96, 104, 60, 255), width=max(2, int(S * 0.003)))
            d.ellipse([bx - br, by - br * 1.3, bx + br, by + br * 1.3], fill=jitter((236, 160, 182), rnd, 0.06) + (255,))
    for (_, x, y, shade) in sorted(blooms):
        sz = rnd.uniform(*fs) * S
        c = tuple(int(min(255, v * shade)) for v in jitter(fcol, rnd, 0.05))
        a0 = rnd.uniform(0, 2 * math.pi)
        for p in range(5):
            pa = a0 + p * 2 * math.pi / 5
            px, py = x + math.cos(pa) * sz * 0.5, y + math.sin(pa) * sz * 0.5
            d.ellipse([px - sz * 0.42, py - sz * 0.42, px + sz * 0.42, py + sz * 0.42], fill=c + (255,))
        r = sz * 0.2
        d.ellipse([x - r, y - r, x + r, y + r], fill=jitter(centre, rnd, 0.08) + (255,))
    return finish(img)


def atlas(name, kind, palette, flowers=None, seed=0):
    if ONLY and name not in ONLY:
        return
    rnd = random.Random(hash(name) & 0xffff ^ seed)
    out = Image.new('RGBA', (CELL * 2, CELL * 2))
    for i in range(4):
        out.paste(cluster_cell(kind, palette, rnd, flowers), ((i % 2) * CELL, (i // 2) * CELL))
    out.save(os.path.join(OUT, f'leaf_{name}.png'), optimize=True)
    to_webp(os.path.join(OUT, f'leaf_{name}.png'))      # the copy the game downloads (tools/webp_textures.py)
    print('leaf', name)


G = [(78, 118, 40), (95, 135, 45), (62, 100, 34), (110, 150, 55)]
atlas('ginkgo', 'ginkgo', [(120, 160, 50), (100, 145, 45), (140, 175, 60), (90, 130, 40)])
atlas('ginkgo_autumn', 'ginkgo', [(240, 200, 40), (230, 185, 30), (250, 215, 70), (215, 170, 30), (200, 180, 50)])
atlas('ginkgo_spring', 'ginkgo', [(150, 190, 70), (135, 180, 60), (165, 200, 85)])
atlas('zelkova', 'zelkova', G)
atlas('zelkova_autumn', 'zelkova', [(190, 110, 40), (170, 90, 35), (200, 140, 50), (150, 110, 40)])
atlas('zelkova_spring', 'zelkova', [(120, 165, 60), (105, 150, 50), (135, 175, 70)])
atlas('cherry', 'cherry', [(70, 110, 38), (85, 122, 42), (60, 95, 32)])
# 4월: the blossom in clusters on bare twigs, a few bronze-green leaves (blossom_cell)
atlas('cherry_spring', 'cherry_bloom', [(128, 132, 58), (150, 118, 70), (112, 140, 56)],
      flowers=((250, 218, 228), 1200, (0.024, 0.032)))
atlas('cherry_autumn', 'cherry', [(190, 80, 40), (210, 110, 40), (160, 70, 40)])
atlas('maple', 'maple', [(85, 130, 40), (100, 145, 45), (70, 115, 35)])
atlas('maple_autumn', 'maple', [(200, 40, 25), (220, 70, 30), (180, 30, 25), (230, 110, 30)])
atlas('maple_spring', 'maple', [(130, 165, 60), (150, 120, 70)])
atlas('oak', 'oak', [(70, 105, 38), (82, 118, 42), (60, 92, 32)])
atlas('oak_autumn', 'oak', [(150, 110, 50), (130, 90, 40), (165, 125, 55)])
atlas('oak_spring', 'oak', [(105, 150, 55), (95, 140, 50)])
atlas('pine', 'pine', [(40, 75, 35), (50, 88, 40), (34, 64, 30), (60, 95, 45)])
# 목련 (2003_봄_교육관에서_본_연희관앞정원과_성암관.jpg, 2024_봄_언더우드관_목련.jpg): ivory cups on the bare wood in
# April, big obovate mid-green leaves in May, dull yellow-brown in late October
atlas('magnolia', 'magnolia', [(82, 128, 46), (95, 140, 52), (70, 112, 40), (104, 146, 58)])
atlas('magnolia_spring', 'magnolia_bloom', [(250, 247, 236), (244, 240, 226), (252, 250, 244), (238, 232, 216)])
atlas('magnolia_autumn', 'magnolia', [(178, 146, 64), (150, 116, 52), (196, 168, 82), (128, 104, 50), (120, 128, 60)])
# 은백양 (the white-stemmed tree by the steps up to 언더우드관 정원, 2003_봄_언더우드관정원_남쪽계단_벚나무.jpg): bare in
# mid-April; in May dark green leaves with the white felt of their undersides turned up here and there; yellow in
# October
atlas('poplar', 'poplar', [(58, 92, 40), (68, 104, 44), (50, 82, 36), (62, 98, 42), (54, 88, 38), (176, 188, 170)])
atlas('poplar_spring', 'twigs', [(120, 104, 70), (140, 128, 84), (110, 118, 70)])
atlas('poplar_autumn', 'poplar', [(222, 190, 70), (204, 170, 60), (186, 152, 58), (196, 172, 72), (170, 150, 70)])
# 담쟁이 (Boston ivy) on the stone halls: fresh glossy green in late May (underwood_2023.jpg), crimson / orange /
# wine in late October with a few leaves still green-yellow, the vines showing with their new leaves in mid-April
atlas('ivy', 'ivy', [(54, 98, 30), (70, 116, 36), (44, 82, 26), (86, 130, 42)])
atlas('ivy_autumn', 'ivy', [(165, 34, 30), (190, 58, 32), (128, 28, 40), (205, 96, 38), (150, 100, 40), (110, 30, 45)])
atlas('ivy_spring', 'ivy_bare', [(128, 150, 58), (112, 136, 50), (140, 160, 64), (160, 92, 54), (118, 142, 52)])
# the clipped shrubs' and flower beds' atlases (boxwood, azalea*, pansy) and their bodies' surfaces are painted from
# scanned leaves by tools/make_shrub_textures.py


def shape_petal(rnd):
    """A fallen cherry petal (unit length, base at the origin, tip toward -y): narrow at the base, widest two thirds
    of the way out, the rounded tip notched in the middle.  Some lie curled and look narrower."""
    w = 0.42 * rnd.uniform(0.62, 1.0)
    notch = rnd.uniform(0.07, 0.13)
    skew = rnd.uniform(-0.08, 0.08)
    right = []
    for i in range(37):
        t = i / 36
        x = w * (t / 0.66) ** 0.65 if t < 0.66 else w * math.sqrt(max(0.0, 1 - ((t - 0.66) / 0.34) ** 2))
        right.append((x, -t))
    right = [(x, y + notch * max(0.0, 1 - x / (0.35 * w)) if t > 0.8 else y)
             for (x, y), t in zip(right, [i / 36 for i in range(37)])]
    pts = right + [(-x, y) for x, y in reversed(right[1:])]
    return [(x + skew * y * x / w, y) for x, y in pts], 0.0


def draw_petal(d, pts, cx, cy, ang, size, col, rnd):
    """pale, pinker toward the base, one half a shade darker where it curls, and a thin darker rim to tell
    overlapping petals apart"""
    base = jitter(col, rnd, 0.03)
    dark = lambda c, k: tuple(int(v * k) for v in c) + (255,)
    P = rot(pts, ang, cx, cy, size)
    d.polygon(P, fill=base + (255,))
    side = 1 if rnd.random() < 0.5 else -1
    d.polygon(rot([(0, 0)] + [(x, y) for x, y in pts if x * side > 0] + [(0, min(y for _, y in pts))], ang, cx, cy, size),
              fill=dark(base, 0.95))
    for k, mixw in ((0.5, 0.22), (0.28, 0.42)):          # the claw: pinker, in two steps (soft once downsampled)
        c = tuple(int(v * (1 - mixw) + p * mixw) for v, p in zip(base, (232, 150, 176)))
        d.polygon(rot([(x * k * 1.3, y * k) for x, y in pts], ang, cx, cy, size), fill=c + (255,))
    d.line(P + [P[0]], fill=dark(base, 0.86), width=1)


# Bark tiles that Poly Haven has none of (blender/materials.json `tex`; x round the trunk, y up it; seamless):
#  bark_poplar  은백양: chalky white with dark diamond-shaped lenticels and short dark dashes round the stem
#  bark_smooth  목련: smooth mid-grey, mottled, with fine pale dashes
# Written to assets_src/textures/<name> (Blender) and web/public/assets/textures/pbr/<name> (the web app).
def bark_tex(name, base, mottle, marks, n_marks, size_m, diamonds=False, px=1024):
    if ONLY and name not in ONLY:
        return
    rnd = random.Random(name)
    nrng = np.random.default_rng(len(name))
    S = px
    # low-frequency mottling (wrapped noise)
    noise = ndimage.gaussian_filter(nrng.normal(size=(S, S)), (S / 24, S / 14), mode='wrap')
    noise = (noise - noise.min()) / (noise.max() - noise.min())
    fine = ndimage.gaussian_filter(nrng.normal(size=(S, S)), (1.2, 2.5), mode='wrap')
    fine = fine / (np.abs(fine).max() + 1e-6)
    rgb = np.array(base, np.float32)[None, None, :] * (1 - noise[..., None]) + np.array(mottle, np.float32)[None, None, :] * noise[..., None]
    rgb *= (1 + 0.06 * fine[..., None])
    mask = Image.new('L', (S * 3, S * 3), 0)           # drawn on a 3x3 canvas, folded back: seamless
    dm = ImageDraw.Draw(mask)
    for k in range(n_marks):
        x, y = rnd.uniform(0, S), rnd.uniform(0, S)
        w = rnd.uniform(*size_m) / 1.2 * S             # (metres -> pixels for a 1.2 m tile)
        for ox in (0, S, 2 * S):
            for oy in (0, S, 2 * S):
                cx, cy = x + ox, y + oy
                if diamonds and rnd.random() < 0.35:
                    h = w * rnd.uniform(0.45, 0.7)
                    dm.polygon([(cx - w / 2, cy), (cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2)], fill=255)
                else:
                    h = max(2.0, w * rnd.uniform(0.06, 0.12))
                    dm.ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=255)
    m = np.array(mask, np.float32).reshape(3, S, 3, S).max((0, 2)) / 255.0
    m = ndimage.gaussian_filter(m, 1.0, mode='wrap')
    rgb = rgb * (1 - m[..., None]) + np.array(marks, np.float32)[None, None, :] * m[..., None]
    height = 0.6 * noise + 0.15 * fine - 0.9 * m
    gy, gx = np.gradient(ndimage.gaussian_filter(height, 1.0, mode='wrap'))
    k = 6.0
    nx, ny, nz = -gx * k, gy * k, np.ones_like(gx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nor = np.stack([nx / ln, ny / ln, nz / ln], -1) * 0.5 + 0.5
    rough = 0.82 + 0.12 * m + 0.04 * fine
    for root in (os.path.join(ROOT, 'assets_src/textures', name), os.path.join(OUT, 'pbr', name)):
        os.makedirs(root, exist_ok=True)
        Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB').save(os.path.join(root, 'diff.jpg'), quality=88)
        Image.fromarray(np.clip(nor * 255, 0, 255).astype(np.uint8), 'RGB').save(os.path.join(root, 'nor.jpg'), quality=85)
        Image.fromarray(np.clip(rough * 255, 0, 255).astype(np.uint8), 'L').save(os.path.join(root, 'rough.jpg'), quality=85)
    print('bark', name)


bark_tex('bark_poplar', (230, 230, 220), (204, 207, 194), (86, 84, 80), 240, (0.012, 0.05), diamonds=True)
bark_tex('bark_smooth', (132, 128, 120), (104, 102, 96), (170, 166, 154), 900, (0.006, 0.02))


# Fallen leaves and petals (issues #18, #35): a seamless tile of leaves or petals lying flat on the ground (ginkgo
# leaves 0.8 m and cherry petals 0.4 m of ground per tile in web/src/litter.js).  Its alpha is each leaf's rank, not
# its coverage: the shader shows the leaves whose rank clears the carpet's thinness there, so a few strewn leaves and
# a full carpet come from the one tile.  Higher ranks lie on top, so a thin strew is whole leaves.  n is about
# k (1 - r0) / (one leaf's share of the tile), ranks from r0 up: the coverage above rank t is then 1 - exp(-k (1 - t)).
# The ginkgo tile is a carpet (k 4.6); the petal tile only a strew (k about 0.2, ranks from 0), so that the few
# petals on the ground at full bloom still take the whole range of ranks (issue #74, reference/고증.md 3.18).
def litter(name, kind, palette, n, size, seed=0, r0=0.14):
    if ONLY and name not in ONLY:
        return
    rnd = random.Random(seed)
    S = CELL * SS
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    rank = Image.new('L', (S, S), 0)
    d, dk = ImageDraw.Draw(img), ImageDraw.Draw(rank)
    shape_fn = {'ginkgo': shape_ginkgo, 'petal': shape_petal}[kind]
    leaves = sorted((rnd.uniform(r0, 1.0), rnd.uniform(0, S), rnd.uniform(0, S), rnd.uniform(0, 2 * math.pi),
                     rnd.uniform(*size) * S, rnd.choice(palette), rnd.random()) for _ in range(n))
    for r, x, y, a, sz, col, sd in leaves:
        shape = shape_fn(random.Random(sd))
        pts, stem = shape
        for ox in (-S, 0, S):                   # wrap round the edges: the tile repeats seamlessly
            for oy in (-S, 0, S):
                cx, cy = x + ox, y + oy
                if not (-2 * sz < cx < S + 2 * sz and -2 * sz < cy < S + 2 * sz):
                    continue
                if kind == 'petal':
                    draw_petal(d, pts, cx, cy, a, sz, col, random.Random(sd))
                    dk.polygon(rot(pts, a, cx, cy, sz), fill=int(r * 255))
                    continue
                draw_leaf(d, shape, cx, cy, a, sz, col, random.Random(sd))     # (same colour on every copy)
                dk.polygon(rot(pts, a, cx, cy, sz), fill=int(r * 255))
                dk.line([rot([(0, 0)], a, cx, cy, sz)[0], rot([(0, stem)], a, cx, cy, sz)[0]], fill=int(r * 255),
                        width=max(1, int(sz * 0.05)))
    img.putalpha(rank)
    out = finish(img)
    if kind == 'petal':
        # the rank, not an edge's coverage, all the way to a petal's rim (the largest of the supersamples): the shader
        # cuts the strew at a rank near 1, which would otherwise shave the antialiased rims off every petal
        r = np.array(rank).reshape(S // SS, SS, S // SS, SS).max((1, 3))
        out = Image.fromarray(np.concatenate([np.array(out)[..., :3], r[..., None]], -1), 'RGBA')
    out.save(os.path.join(OUT, f'{name}.png'), optimize=True)
    to_webp(os.path.join(OUT, f'{name}.png'))
    al = np.array(out)[..., 3] / 255
    print('litter', name, 'cover above rank 0.02 / 0.14 / 0.5 / 0.8: %.3f %.3f %.3f %.3f'
          % ((al > 0.02).mean(), (al > 0.14).mean(), (al > 0.5).mean(), (al > 0.8).mean()))


litter('litter_ginkgo', 'ginkgo', [(240, 200, 40), (230, 185, 30), (250, 215, 70), (215, 170, 30), (200, 180, 50),
                                   (236, 196, 52), (190, 150, 40), (175, 130, 45)], 1500, (0.036, 0.052), seed=18)
# Somei-yoshino petals 1.1-1.5 cm long, near white with a blush of pink, a few going brown: a strew of about 400
# petals per 0.4 m tile, 2500 a square metre with every rank shown (the ground at full bloom takes a few per cent)
litter('litter_petals', 'petal', [(246, 206, 218), (248, 216, 226), (250, 226, 233), (244, 198, 212), (252, 236, 240),
                                  (240, 190, 205), (247, 222, 228), (236, 214, 208)], 400, (0.0275, 0.0375), seed=35, r0=0.0)

# 게시판 (2003_봄_언더우드관_앞길_벚나무.jpg): the board by 언더우드관's west wing pasted over with posters and 대자보,
# 1997 campus notices (blender/props.py notice_board)
def notice_posters():
    if ONLY and 'notice_posters' not in ONLY:
        return
    rnd = random.Random(1997)
    W, H = 1024, 640
    img = Image.new('RGB', (W, H), (96, 78, 58))
    d = ImageDraw.Draw(img)
    fpath = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
    fser = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'
    def fnt(path, size):
        for i in (1, 0, 2, 3):
            try:
                return ImageFont.truetype(path, size, index=i)
            except Exception:
                continue
        return ImageFont.load_default()
    heads = ['총학생회', '대동제', '연고전', '공 지', '학술제', '신입회원 모집', '동아리 연합회', '단과대 체육대회', '자보',
             '영화 상영', '독서 토론', '등록금', '정기 공연', '봉사활동', '노래패', '교지 편집위원회']
    papers = [(250, 250, 244), (248, 240, 200), (250, 220, 226), (214, 232, 246), (246, 246, 236), (236, 244, 210)]
    for k in range(17):
        w, h = rnd.randint(150, 300), rnd.randint(170, 300)
        x, y = rnd.randint(-30, W - w + 30), rnd.randint(-20, H - h + 20)
        col = papers[rnd.randrange(len(papers))]
        d.rectangle([x + 4, y + 5, x + w + 4, y + h + 5], fill=(70, 56, 42))      # (a shadow under each sheet)
        d.rectangle([x, y, x + w, y + h], fill=col)
        ink = rnd.choice([(20, 20, 24), (170, 20, 24), (20, 40, 120)])
        hd = rnd.choice(heads)
        size = max(22, min(54, int(w / max(2, len(hd)) * 0.9)))
        d.text((x + 10, y + 8), hd, font=fnt(rnd.choice([fpath, fser]), size), fill=ink)
        yy = y + 18 + size
        while yy < y + h - 14:                                                       # lines of small writing
            xx = x + 10
            while xx < x + w - 20:
                L = rnd.randint(8, 40)
                d.line([(xx, yy), (min(x + w - 12, xx + L), yy)], fill=tuple(int(c * 0.9 + 60) for c in ink) if rnd.random() < 0.2 else ink, width=3)
                xx += L + rnd.randint(4, 10)
            yy += rnd.randint(12, 16)
        for cx_, cy_ in ((x + 6, y + 6), (x + w - 6, y + 6)):                        # tape
            d.rectangle([cx_ - 9, cy_ - 4, cx_ + 9, cy_ + 4], fill=(232, 226, 200))
    img.save(os.path.join(OUT, 'notice_posters.png'), optimize=True)
    print('notice_posters')


notice_posters()


# ---------------------------------------------------------------- 정문 밖: the town's atlas and 연세로's shop signs
# town_atlas.jpg (blender/town.py, material town_far): eight bands of 128 px, each tiling along the texture.  A band is
# one storey (3 m) of a wall, four bays of 3 m across: red brick, cream plaster, grey plaster and white tile with a
# window to the bay, a shop front; then plain colours in eighths (the four walls, gravel, concrete, the roof tanks'
# yellow and blue), roofs in quarters (red tiles, blue-grey tiles, green waterproofing, grey slab) and the railway
# track (3.2 m across the band, 12 m along: sleepers every 0.6 m, the two rails).
# sign_sinchon.png: the shops of 연세로 from the bridge south as the anthologies' street maps name them (2019 문집
# 25쪽, 2021 문집 22쪽), 2 x 8 like sign_shops.png; east side first, each from the bridge on (tools/gate_town.py names).
def town_textures():
    if ONLY and not ({'town_atlas', 'sign_sinchon'} & ONLY):
        return
    rs = np.random.RandomState(4801)
    rnd = random.Random(4801)
    S, BH, BAYW = 1024, 128, 256
    A = np.zeros((S, S, 3), np.float32)

    def fill(k, x0, x1, col, noise=7.0, grain=1):
        h = rs.randn(BH // grain + 1, (x1 - x0) // grain + 1)
        h = np.kron(h, np.ones((grain, grain)))[:BH, :x1 - x0]
        A[k * BH:(k + 1) * BH, x0:x1] = np.array(col, np.float32) + h[..., None] * noise

    walls = [(146, 72, 56), (212, 200, 174), (150, 149, 144), (222, 222, 216)]
    for k, col in enumerate(walls):
        fill(k, 0, S, col, 6.0 if k else 9.0)
        y0 = k * BH
        if k == 0:                                   # brick courses
            for yy in range(y0, y0 + BH, 3):
                A[yy, :] *= 0.86
        if k == 3:                                   # tile joints
            for yy in range(y0, y0 + BH, 6):
                A[yy, :] *= 0.9
            for xx in range(0, S, 6):
                A[y0:y0 + BH, xx] *= 0.93
        A[y0:y0 + 5, :] = np.array((168, 166, 160), np.float32) * (0.9 if k == 0 else 1.0)      # the slab's edge
        A[y0 + 5, :] *= 0.75
        for b in range(4):
            x0 = b * BAYW
            wide = k == 3
            wx0, wx1 = (x0 + 28, x0 + 228) if wide else (x0 + 64, x0 + 192)
            wy0, wy1 = y0 + 34, y0 + 88
            A[wy0 - 3:wy0, wx0 - 4:wx1 + 4] *= 0.8                                   # lintel shadow
            A[wy0:wy1, wx0:wx1] = (196, 198, 200)                                    # aluminium frame
            g0, g1 = np.array((34, 44, 56), np.float32), np.array((70, 86, 102), np.float32)
            panes = 4 if wide else 2
            pw = (wx1 - wx0 - 3) // panes
            for pi in range(panes):
                px0 = wx0 + 3 + pi * pw
                shade = rnd.random()
                for yy in range(wy0 + 3, wy1 - 3):
                    f = (yy - wy0) / (wy1 - wy0)
                    c = g1 * (1 - f) + g0 * f
                    if shade < 0.3:                                                  # a curtain behind the glass
                        c = c * 0.45 + np.array((180, 172, 150), np.float32) * 0.55
                    A[yy, px0:px0 + pw - 3] = c
            A[wy1:wy1 + 4, wx0 - 6:wx1 + 6] = (176, 174, 168)                        # the sill
            A[wy1 + 4:wy1 + 6, wx0 - 6:wx1 + 6] *= 0.8
            if k != 3 and rnd.random() < 0.35:                                       # an air conditioner's box below
                A[wy1 + 8:wy1 + 24, wx1 - 34:wx1 - 4] = (205, 203, 196)
                A[wy1 + 11:wy1 + 21, wx1 - 30:wx1 - 18] = (60, 62, 66)
    # the shop front
    k = 4
    fill(k, 0, S, (150, 149, 144), 5.0)
    y0 = k * BH
    fasc = [(176, 40, 36), (24, 70, 150), (240, 196, 40), (30, 110, 70)]
    for b in range(4):
        x0 = b * BAYW
        A[y0:y0 + 5, :] = (168, 166, 160)
        A[y0 + 7:y0 + 30, x0 + 6:x0 + BAYW - 6] = fasc[b]                             # the sign's board
        xx = x0 + 22
        while xx < x0 + BAYW - 40:                                                   # (its letters, far off)
            w_ = rnd.randint(14, 26)
            A[y0 + 12:y0 + 25, xx:xx + w_] = (250, 246, 232) if b != 2 else (30, 28, 26)
            xx += w_ + rnd.randint(5, 9)
        A[y0 + 34:y0 + 118, x0 + 10:x0 + BAYW - 10] = (190, 192, 194)                # frame
        for px0, px1 in ((x0 + 14, x0 + 96), (x0 + 100, x0 + 160), (x0 + 164, x0 + BAYW - 14)):
            for yy in range(y0 + 38, y0 + 115):
                f = (yy - y0 - 38) / 77
                A[yy, px0:px1] = np.array((60, 74, 86), np.float32) * (1 - f) + np.array((36, 42, 48), np.float32) * f
        A[y0 + 60:y0 + 100, x0 + 20:x0 + 90] = np.array(rnd.choice([(200, 180, 120), (170, 60, 50), (210, 210, 200)]), np.float32) * 0.8
        A[y0 + 118:y0 + BH, x0:x0 + BAYW] = (120, 118, 112)                          # the step
    # plain colours
    plain = walls + [(122, 113, 100), (166, 164, 157), (226, 182, 44), (58, 108, 168)]
    for c, col in enumerate(plain):
        fill(5, c * 128, (c + 1) * 128, col, 14.0 if c == 4 else 5.0, 2 if c == 4 else 1)
    # roofs
    roofs = [(178, 86, 54), (94, 110, 130), (60, 122, 90), (158, 156, 150)]
    for c, col in enumerate(roofs):
        fill(6, c * 256, (c + 1) * 256, col, 7.0, 2)
        if c < 2:
            for yy in range(6 * BH, 7 * BH, 5):
                A[yy, c * 256:(c + 1) * 256] *= 0.8
    # the track
    k = 7
    fill(k, 0, S, (120, 111, 98), 15.0, 2)
    y0 = k * BH
    step = S / 20.0
    for i in range(20):
        x0 = int(round(i * step + step / 2 - 10))
        A[y0 + 14:y0 + 114, x0:x0 + 20] = np.array((72, 56, 44), np.float32) + rs.randn(100, 20, 1) * 6
    for yc in (y0 + 35, y0 + 93):
        A[yc - 3:yc + 3, :] = (104, 70, 52)
        A[yc - 1:yc + 2, :] = (176, 178, 184)
    if not ONLY or 'town_atlas' in ONLY:
        Image.fromarray(np.clip(A, 0, 255).astype(np.uint8), 'RGB').save(os.path.join(OUT, 'town_atlas.jpg'), quality=88)
        print('town_atlas')
    if ONLY and 'sign_sinchon' not in ONLY:
        return
    fb = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'

    def fnt(size):
        for i in (1, 0, 2, 3):
            try:
                return ImageFont.truetype(fb, size, index=i)
            except Exception:
                continue
        return ImageFont.load_default()
    signs = [('연세식품', (250, 248, 236), (190, 30, 30)), ('사 진 관', (20, 60, 150), (255, 255, 255)),
             ('독수리다방', (120, 60, 30), (255, 236, 190)), ('초 원 각', (190, 30, 30), (255, 226, 120)),
             ('독수리약국', (252, 252, 250), (30, 130, 70)), ('알 서 림', (40, 80, 60), (245, 240, 220)),
             ('새마을금고', (30, 110, 60), (255, 255, 255)), ('오 락 실', (20, 20, 24), (255, 90, 70)),
             ('독수리문구', (250, 210, 40), (30, 40, 120)), ('시골분식', (230, 96, 34), (255, 255, 255)),
             ('연세문화사', (30, 60, 140), (255, 255, 255)), ('상아탑분식', (250, 246, 230), (200, 40, 30)),
             ('자 뎅', (60, 36, 24), (240, 210, 150)), ('연희식당', (252, 252, 248), (30, 30, 30)),
             ('오늘의 책', (246, 240, 220), (40, 60, 50)), ('신촌반점', (180, 24, 24), (255, 220, 90))]
    img = Image.new('RGB', (1024, 1024), (200, 200, 200))
    d = ImageDraw.Draw(img)
    for i, (txt, bg, fg) in enumerate(signs):
        x0, y0 = (i % 2) * 512, (i // 2) * 128
        d.rectangle([x0, y0, x0 + 511, y0 + 127], fill=bg)
        d.rectangle([x0 + 6, y0 + 6, x0 + 505, y0 + 121], outline=tuple(int(c * 0.75) for c in fg), width=4)
        size = 96
        while True:
            f = fnt(size)
            w = d.textlength(txt, font=f)
            if w < 440 or size < 30:
                break
            size -= 4
        d.text((x0 + 256 - w / 2, y0 + 64), txt, font=f, fill=fg, anchor='lm')
    img.save(os.path.join(OUT, 'sign_sinchon.png'), optimize=True)
    print('sign_sinchon')


town_textures()


# sign_sinchon2.png: 신촌 로터리 (tools/sinchon_rotary.py): the shops on 연세로 south of the anthologies' maps (the kinds
# of shop the 1996 photos show, not their names; but 홍익문고), the junction's landmarks over their tops (the 1995 ·
# 1996 photos 52095 · 52108 · 52135: 그레이스백화점 dark grey on white; 그랜드마트 red (그랜드백화점 in 1995.10, 그랜드마트
# 신촌점 in every 1996 photo and in 1999); on the dark tower 아주생명보험 along its top and 외환은행 lower down, white)
def sinchon2_signs():
    if ONLY and 'sign_sinchon2' not in ONLY:
        return
    fb = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'

    def fnt(size):
        for i in (1, 0, 2, 3):
            try:
                return ImageFont.truetype(fb, size, index=i)
            except Exception:
                continue
        return ImageFont.load_default()
    signs = [('레 코 드', (60, 20, 100), (255, 230, 120)), ('안 경 원', (252, 252, 248), (20, 60, 150)),
             ('분식 · 떡볶이', (230, 96, 34), (255, 255, 255)), ('당 구 장', (20, 20, 24), (255, 90, 70)),
             ('커 피 숍', (80, 44, 28), (245, 225, 180)), ('홍익문고', (24, 70, 150), (255, 255, 255)),
             ('약 국', (252, 252, 250), (30, 130, 70)), ('서 점', (30, 110, 60), (255, 255, 230)),
             ('호프 · 생맥주', (120, 30, 20), (255, 220, 120)), ('노 래 방', (200, 30, 120), (255, 240, 120)),
             ('경 양 식', (250, 246, 230), (120, 40, 30)), ('제 과 점', (250, 220, 200), (150, 40, 60)),
             ('그레이스백화점', (236, 236, 232), (70, 72, 78)), ('그랜드마트', (240, 238, 234), (190, 30, 40)),
             ('아주생명보험', (24, 28, 34), (236, 236, 236)), ('외 환 은 행', (24, 28, 34), (236, 236, 236))]
    img = Image.new('RGB', (1024, 1024), (200, 200, 200))
    d = ImageDraw.Draw(img)
    for i, (txt, bg, fg) in enumerate(signs):
        x0, y0 = (i % 2) * 512, (i // 2) * 128
        d.rectangle([x0, y0, x0 + 511, y0 + 127], fill=bg)
        if i < 12:
            d.rectangle([x0 + 6, y0 + 6, x0 + 505, y0 + 121], outline=tuple(int(c * 0.75) for c in fg), width=4)
        size = 96
        while True:
            f = fnt(size)
            w = d.textlength(txt, font=f)
            if w < 450 or size < 30:
                break
            size -= 4
        d.text((x0 + 256 - w / 2, y0 + 64), txt, font=f, fill=fg, anchor='lm')
    img.save(os.path.join(OUT, 'sign_sinchon2.png'), optimize=True)
    print('sign_sinchon2')


sinchon2_signs()


# sign_yro97.png: 연세로's shops from the bridge to the junction as the anthologies' street maps name them (2019 문집
# 25쪽, 2021 문집 22 ~ 23쪽; tools/yro97.py SIGNS, blender/town.py shops): 4 x 16 cells of 512 x 128, a board each in
# the plain painted or lit-box manner of the 1996 photos (51979 · 52106: a flat ground, heavy letters, a thin frame)
def yro97_signs():
    if ONLY and 'sign_yro97' not in ONLY:
        return
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import yro97
    fb = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'

    def fnt(size):
        for i in (1, 0, 2, 3):
            try:
                return ImageFont.truetype(fb, size, index=i)
            except Exception:
                continue
        return ImageFont.load_default()
    img = Image.new('RGB', (2048, 2048), (200, 200, 200))
    d = ImageDraw.Draw(img)
    for i, (txt, bg, fg) in enumerate(yro97.SIGNS):
        x0, y0 = (i % yro97.COLS) * 512, (i // yro97.COLS) * 128
        d.rectangle([x0, y0, x0 + 511, y0 + 127], fill=bg)
        d.rectangle([x0 + 6, y0 + 6, x0 + 505, y0 + 121], outline=tuple(int(c * 0.75) for c in fg), width=4)
        size = 96
        while True:
            f = fnt(size)
            w = d.textlength(txt, font=f)
            if w < 440 or size < 30:
                break
            size -= 4
        d.text((x0 + 256 - w / 2, y0 + 64), txt, font=f, fill=fg, anchor='lm')
    # 옛 독수리다방's own cells (yro97.DOK_CELLS; the 2019 anthology's photo, 26쪽; blender/town.py _dok97): the white
    # letters on the slates of its mansard, and the coloured glass of its wide windows (four panes, a blue and a red
    # roundel by turns; the face it is laid on is 3.2 x 1.4 m, so a round one is drawn 72 x 42)
    k = yro97.DOK_CELLS['roof']
    x0, y0 = (k % yro97.COLS) * 512, (k // yro97.COLS) * 128
    d.rectangle([x0, y0, x0 + 511, y0 + 127], fill=(52, 56, 66))
    f = fnt(104)
    for i, ch in enumerate('독수리'):
        d.text((x0 + 96 + 160 * i, y0 + 62), ch, font=f, fill=(244, 244, 238), anchor='mm')
    k = yro97.DOK_CELLS['glass']
    x0, y0 = (k % yro97.COLS) * 512, (k // yro97.COLS) * 128
    d.rectangle([x0, y0, x0 + 511, y0 + 127], fill=(232, 228, 216))
    for i in range(4):
        px = x0 + 128 * i
        d.rectangle([px + 7, y0 + 9, px + 120, y0 + 118], fill=(92, 70, 44))
        d.rectangle([px + 7, y0 + 9, px + 120, y0 + 40], fill=(118, 96, 62))
        col = ((40, 60, 190), (214, 44, 40))[i % 2]
        d.ellipse([px + 28, y0 + 44, px + 100, y0 + 86], fill=(240, 236, 226))
        d.ellipse([px + 35, y0 + 48, px + 93, y0 + 82], fill=col)
    img.save(os.path.join(OUT, 'sign_yro97.png'), optimize=True)
    print('sign_yro97')


yro97_signs()


# town_yro.jpg (blender/town.py, material town_yro): the walls of 연세로's shop rows only (tools/yro97.py WALLS97), so
# that the town's own atlas (town_atlas.jpg, 창천동's houses) stays as it is.  1024 x 2048, sixteen bands of 128 px laid
# as town_atlas's (a band one storey of 3 m, four bays of a window each across, tiling along u): bands 0 - 6 a middle
# storey of each wall, 7 - 13 the top storey of each (the parapet's streaks down it), 14 the shop front, 15 plain
# colours in eighths (the seven walls, then concrete).  The 1996 photos (51979 · 52106 · 52004 · 52006; reference/고증/
# 4.10.8 「벽」): grey render and tile, white tile and cream gone grey with grime, brick red and brown, the purple-grey
# and pink renders; streaks of rain from each sill and from the parapet down, dirt under each slab's edge and at the foot.
# Every noise is periodic across the band (made in Fourier space or wrapped), so a wall tiles without a seam.
YRO_WALLS = [(132, 84, 70), (108, 88, 74), (198, 186, 162), (146, 144, 139), (178, 178, 174), (188, 156, 152), (156, 147, 158)]


def yro_walls():
    if ONLY and 'town_yro' not in ONLY:
        return
    rs = np.random.RandomState(4807)
    rnd = random.Random(4807)
    S, BH, BAYW, NBAND = 1024, 128, 256, 16
    A = np.zeros((NBAND * BH, S, 3), np.float32)

    def pnoise(h, w, scale_y, scale_x):
        """periodic in x (w) smooth noise of unit spread, its blobs about scale_y x scale_x px"""
        f = rs.randn(h, w)
        f = ndimage.gaussian_filter(f, (scale_y, scale_x), mode='wrap')
        return f / (f.std() + 1e-6)

    def streaks(h, w, n, len0, len1, wid0, wid1, xs=None):
        """darkening (0 - 1) of n rain streaks from the top of an h x w field down, fading with length; at xs if given"""
        D = np.zeros((h, w), np.float32)
        yy = np.arange(h, dtype=np.float32)[:, None]
        for i in range(n):
            x = xs[i] if xs is not None else rnd.uniform(0, w)
            wid = rnd.uniform(wid0, wid1)
            ln = rnd.uniform(len0, len1)
            a = rnd.uniform(0.5, 1.0)
            xx = (np.arange(w, dtype=np.float32)[None, :] - x + w / 2) % w - w / 2          # (wrapped)
            prof = np.exp(-(xx / wid) ** 2)
            fall = np.clip(1 - yy / ln, 0, 1) ** 1.3
            D = np.maximum(D, a * prof * fall)
        # a little ragged along their length
        return D * (0.75 + 0.25 * np.clip(pnoise(h, w, 2, 1.5), -1.5, 1.5) / 1.5)

    def wall_band(k, col, cls, top):
        y0 = k * BH
        base = np.array(col, np.float32)
        tone = pnoise(BH, S, 22, 90)[..., None]                   # broad, uneven fading
        grain = rs.randn(BH, S, 1).astype(np.float32)
        plaster = cls in (2, 3, 5, 6)
        B = base * (1 + tone * (0.045 if plaster else 0.03)) + grain * (5.0 if cls < 2 else 3.5)
        if plaster:                                              # blotches where the render was patched or washed
            B *= 1 + 0.025 * np.clip(pnoise(BH, S, 8, 14), -2, 2)[..., None]
        if cls < 2:                                              # brick courses and head joints
            for yy in range(0, BH, 3):
                B[yy] *= 0.84
            for yy in range(0, BH, 6):
                off = 0 if (yy // 6) % 2 else 5
                B[yy:yy + 3, off::10] *= 0.88
            B *= 1 + 0.06 * rs.randn(BH // 3 + 1, S // 10 + 1).repeat(3, 0).repeat(10, 1)[:BH, :S, None]
        if cls == 4:                                             # tile joints
            for yy in range(0, BH, 6):
                B[yy] *= 0.9
            B[:, ::6] *= 0.93
        if cls == 3:                                             # the formwork's faint seams in the grey
            B[::32] *= 0.94
        A[y0:y0 + BH] = B
        # the slab's edge, the dirt that gathers under it
        A[y0:y0 + 5] = np.array((150, 148, 142), np.float32) * (0.92 if cls < 2 else 1.0)
        A[y0 + 5] *= 0.72
        A[y0 + 6:y0 + 14] *= (1 - 0.10 * np.linspace(1, 0, 8))[:, None, None]
        wide = cls == 4
        sill_x = []
        for b in range(4):
            x0 = b * BAYW
            wx0, wx1 = (x0 + 28, x0 + 228) if wide else (x0 + 64, x0 + 192)
            wy0, wy1 = y0 + 34, y0 + 88
            A[wy0 - 3:wy0, wx0 - 4:wx1 + 4] *= 0.8                                   # lintel shadow
            A[wy0:wy1, wx0:wx1] = (182, 184, 186)                                    # the frame, dulled
            g0, g1 = np.array((32, 40, 50), np.float32), np.array((66, 80, 94), np.float32)
            panes = 4 if wide else 2
            pw = (wx1 - wx0 - 3) // panes
            for pi in range(panes):
                px0 = wx0 + 3 + pi * pw
                shade = rnd.random()
                for yy in range(wy0 + 3, wy1 - 3):
                    f = (yy - wy0) / (wy1 - wy0)
                    c = g1 * (1 - f) + g0 * f
                    if shade < 0.35:                                                 # a curtain or blind behind the glass
                        c = c * 0.45 + np.array((176, 168, 148), np.float32) * 0.55
                    A[yy, px0:px0 + pw - 3] = c
            A[wy1:wy1 + 4, wx0 - 6:wx1 + 6] = (164, 162, 156)                        # the sill
            A[wy1 + 4:wy1 + 6, wx0 - 6:wx1 + 6] *= 0.78
            sill_x += [wx0 - 4, wx1 + 4] + [rnd.uniform(wx0 + 8, wx1 - 8) for _ in range(2 if wide else 1)]
            if cls not in (4,) and rnd.random() < 0.3:                               # an air conditioner's box below
                A[wy1 + 8:wy1 + 24, wx1 - 34:wx1 - 4] = (196, 194, 186)
                A[wy1 + 11:wy1 + 21, wx1 - 30:wx1 - 18] = (60, 62, 66)
        # rain from the sills' ends and middles down to the slab under them (and, faint, under the slab above: the
        # bays line up storey over storey, town.py moves a wall's start by whole bays)
        dark = 0.32 if cls in (2, 4, 5) else (0.26 if cls in (3, 6) else 0.14)
        under = streaks(BH - 94, S, len(sill_x), 24, 44, 3.0, 8.0, xs=sill_x)
        A[y0 + 94:y0 + BH] *= (1 - 1.5 * dark * under)[..., None]
        above = streaks(26, S, len(sill_x), 14, 30, 3.0, 7.0, xs=sill_x)
        A[y0 + 6:y0 + 32] *= (1 - dark * 0.9 * above)[..., None]
        if top:                                                  # the parapet: its coping, the streaks from it
            A[y0:y0 + 5] = np.array((160, 158, 152), np.float32)
            A[y0 + 5] *= 0.6
            run = streaks(BH - 6, S, 40, 40, 140, 3.0, 12.0)
            band = (1 - 0.16 * np.linspace(1, 0, BH - 6) ** 2)[:, None]               # grime thickest by the top
            mask = np.ones((BH - 6, S), np.float32)
            for b in range(4):                                   # (not over the glass)
                x0 = b * BAYW
                wx0, wx1 = (x0 + 28, x0 + 228) if wide else (x0 + 64, x0 + 192)
                mask[34 - 6 + 3:88 - 6 - 3, wx0 + 3:wx1 - 3] = 0.25
            A[y0 + 6:y0 + BH] *= (band * (1 - dark * 2.0 * run * mask))[..., None]

    for cls, col in enumerate(YRO_WALLS):
        wall_band(cls, col, cls, False)
        wall_band(7 + cls, col, cls, True)
    # the shop front (town_atlas's, dirtier): the boards over the shops, glass, the wall between, the grime at its foot
    k = 14
    y0 = k * BH
    A[y0:y0 + BH] = np.array((142, 140, 134), np.float32) * (1 + 0.04 * pnoise(BH, S, 20, 80)[..., None]) + rs.randn(BH, S, 1) * 4
    fasc = [(166, 42, 38), (28, 68, 140), (226, 186, 46), (34, 104, 70)]
    for b in range(4):
        x0 = b * BAYW
        A[y0:y0 + 5, x0:x0 + BAYW] = (160, 158, 152)
        A[y0 + 7:y0 + 30, x0 + 6:x0 + BAYW - 6] = fasc[b]
        xx = x0 + 22
        while xx < x0 + BAYW - 40:
            w_ = rnd.randint(14, 26)
            A[y0 + 12:y0 + 25, xx:xx + w_] = (244, 240, 226) if b != 2 else (30, 28, 26)
            xx += w_ + rnd.randint(5, 9)
        A[y0 + 34:y0 + 118, x0 + 10:x0 + BAYW - 10] = (178, 180, 182)
        for px0, px1 in ((x0 + 14, x0 + 96), (x0 + 100, x0 + 160), (x0 + 164, x0 + BAYW - 14)):
            for yy in range(y0 + 38, y0 + 115):
                f = (yy - y0 - 38) / 77
                A[yy, px0:px1] = np.array((58, 70, 82), np.float32) * (1 - f) + np.array((34, 40, 46), np.float32) * f
        A[y0 + 60:y0 + 100, x0 + 20:x0 + 90] = np.array(rnd.choice([(200, 180, 120), (170, 60, 50), (210, 210, 200)]), np.float32) * 0.8
        A[y0 + 118:y0 + BH, x0:x0 + BAYW] = (112, 110, 104)
    # the foot: splashed dirt up the wall and the frames' bottoms, darkest at the step
    foot = np.clip((np.arange(BH, dtype=np.float32)[:, None] - (BH - 34)) / 34, 0, 1) ** 1.5
    foot = foot * (0.8 + 0.2 * np.clip(pnoise(BH, S, 3, 6), -2, 2) / 2)
    A[y0:y0 + BH] *= (1 - 0.28 * foot)[..., None]
    A[y0 + 30:y0 + 34] *= 0.85                                                       # under the boards
    # plain colours: the walls (a little dirtier than the bands' average), concrete
    plain = [tuple(c * 0.95 for c in col) for col in YRO_WALLS] + [(150, 148, 142)]
    for c, col in enumerate(plain):
        A[15 * BH:16 * BH, c * 128:(c + 1) * 128] = np.array(col, np.float32) + rs.randn(BH, 128, 1) * 4
    Image.fromarray(np.clip(A, 0, 255).astype(np.uint8), 'RGB').save(os.path.join(OUT, 'town_yro.jpg'), quality=88)
    print('town_yro')


yro_walls()


# sign_roof.png: 연세로's rooftop boards (blender/town.py yro_roofs; reference/고증/4.10.2 「지붕 위 틀 간판」): 2 x 8 cells,
# 512 x 128 each.  Cells 0 - 13 the kinds of business the 1996 photos (51979 · 52106 · 52006) and the anthologies' maps
# show on 연세로, words only (the boards stand on houses drawn at random); 14 · 15 the two read on their own houses:
# 신영증권 on the seven storeys of white tile, the white five's 「商業建築 企畫設計 | INDIS」 (52006: both on the top of the
# south face, blender/town.py ROOF_PINS)
def roof_signs():
    if ONLY and 'sign_roof' not in ONLY:
        return
    fb = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'

    def fnt(size):
        for i in (1, 0, 2, 3):
            try:
                return ImageFont.truetype(fb, size, index=i)
            except Exception:
                continue
        return ImageFont.load_default()
    W_, RED, BLUE, GRN, NAVY = (250, 250, 246), (200, 30, 36), (24, 64, 156), (24, 120, 64), (26, 34, 70)
    signs = [('외 과 의 원', W_, RED), ('내 과 의 원', W_, BLUE), ('치 과 의 원', W_, GRN), ('이비인후과', W_, RED),
             ('비뇨기과 · 피부과', NAVY, W_), ('증 권', (30, 58, 44), W_), ('예 식 장', (180, 24, 40), (255, 236, 150)),
             ('생 명 보 험', W_, RED), ('법 무 사', (22, 30, 70), W_), ('기 원', (250, 244, 220), (30, 30, 30)),
             ('바 둑', (236, 234, 228), (90, 90, 96)), ('당 구 장', (20, 20, 24), (255, 200, 60)),
             ('사 우 나', (30, 90, 160), W_), ('포켓볼전용', (200, 34, 30), W_)]
    img = Image.new('RGB', (1024, 1024), (200, 200, 200))
    d = ImageDraw.Draw(img)
    for i, (txt, bg, fg) in enumerate(signs):
        x0, y0 = (i % 2) * 512, (i // 2) * 128
        d.rectangle([x0, y0, x0 + 511, y0 + 127], fill=bg)
        # (a dirty bottom edge: the boards stood out in the weather)
        for k in range(10):
            g = 1 - 0.022 * (10 - k)
            d.line([x0, y0 + 117 + k, x0 + 511, y0 + 117 + k], fill=tuple(int(c * g) for c in bg))
        size = 100
        while True:
            f = fnt(size)
            w = d.textlength(txt, font=f)
            if w < 470 or size < 30:
                break
            size -= 4
        d.text((x0 + 256 - w / 2, y0 + 62), txt, font=f, fill=fg, anchor='lm')
    # 14: 신영증권, dark green words and its round mark on the pale grey band (52006)
    x0, y0 = 0, 7 * 128
    bg, ink = (232, 232, 226), (34, 74, 52)
    d.rectangle([x0, y0, x0 + 511, y0 + 127], fill=bg)
    d.ellipse([x0 + 40, y0 + 30, x0 + 108, y0 + 98], fill=ink)
    d.ellipse([x0 + 58, y0 + 48, x0 + 90, y0 + 80], fill=bg)
    d.text((x0 + 128, y0 + 62), '신영증권', font=fnt(84), fill=ink, anchor='lm')
    # 15: INDIS, 「商業建築 / 企畫設計」 in green on the left, 「INDIS」 in navy under its small line on the right (52006)
    x0 = 512
    d.rectangle([x0, y0, x0 + 511, y0 + 127], fill=(214, 216, 208))
    d.line([x0 + 250, y0 + 10, x0 + 250, y0 + 118], fill=(170, 172, 164), width=3)
    d.text((x0 + 18, y0 + 34), '商業建築', font=fnt(44), fill=(40, 96, 72), anchor='lm')
    d.text((x0 + 18, y0 + 92), '企畫設計', font=fnt(44), fill=(40, 96, 72), anchor='lm')
    d.text((x0 + 380, y0 + 20), 'ENTERPRISE COMMUNICATION INC.', font=fnt(14), fill=(40, 50, 90), anchor='mm')
    d.text((x0 + 380, y0 + 72), 'INDIS', font=fnt(70), fill=(30, 40, 110), anchor='mm')
    img.save(os.path.join(OUT, 'sign_roof.png'), optimize=True)
    print('sign_roof')


roof_signs()


# sign_yonseiro.png: the signs that stand out from the walls of 연세로's shops (tools/sinchon_rotary.py yro_wall_signs,
# blender/town.py yro_signs), yro97.VS_COLS x 2 cells 468 px high (2048 wide), the words stacked down: tools/yro97.py VSIGNS,
# what the 1996 photos 51979 · 52106 read (연세 비디오방, 오원당구클럽, 게임프라자, 현대예식장, 신영증권, 안재훈 서영외과,
# 복지 탁구, …), the maps' upstairs shops and the kinds both show.  Under them, 2048 x 88 px, 제5회 신촌문화축제's banner
# over the street (51979: the big green words read only as 「… 시범공연」), drawn at 1024 and stretched
def yro_signs():
    if ONLY and 'sign_yonseiro' not in ONLY:
        return
    import yro97
    fb = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'

    def fnt(size):
        for i in (1, 0, 2, 3):
            try:
                return ImageFont.truetype(fb, size, index=i)
            except Exception:
                continue
        return ImageFont.load_default()
    signs = yro97.VSIGNS
    CW, CH = 2048 // yro97.VS_COLS, 468
    img = Image.new('RGB', (2048, 1024), (200, 200, 200))
    d = ImageDraw.Draw(img)
    for i, (txt, bg, fg, top) in enumerate(signs):
        x0, y0 = round((i % yro97.VS_COLS) * 2048 / yro97.VS_COLS), (i // yro97.VS_COLS) * CH
        d.rectangle([x0, y0, x0 + CW - 1, y0 + CH - 1], fill=bg)
        d.rectangle([x0 + 5, y0 + 5, x0 + CW - 6, y0 + CH - 6], outline=tuple(int(c * 0.75) for c in fg), width=4)
        yy = y0 + 16
        if top:
            sz = 24
            while d.textlength(top, font=fnt(sz)) > CW - 16 and sz > 12:     # (the small words within the board)
                sz -= 1
            f = fnt(sz)
            w = d.textlength(top, font=f)
            d.text((x0 + CW / 2 - w / 2, yy), top, font=f, fill=fg)
            yy += 36
        chars = list(txt)
        room = y0 + CH - 18 - yy
        step = min(104, room / len(chars))
        f = fnt(int(min(96, step * 0.92)))
        yy += (room - step * len(chars)) / 2                         # (short words in the middle of the board)
        for k, ch in enumerate(chars):
            w = d.textlength(ch, font=f)
            d.text((x0 + CW / 2 - w / 2, yy + step * (k + 0.5)), ch, font=f, fill=fg, anchor='lm')
    # the banner: white cloth, the festival in blue, the show in green, when and where in red
    ban = Image.new('RGB', (1024, 1024 - 2 * CH), (244, 244, 238))
    d, y0 = ImageDraw.Draw(ban), 0
    f1, f2, f3 = fnt(26), fnt(46), fnt(18)
    d.text((60, y0 + 20), '제5회 신촌문화축제', font=f1, fill=(30, 50, 150), anchor='lm')
    d.text((640, y0 + 20), '주최: 신촌문화축제 추진위원회', font=f3, fill=(30, 50, 150), anchor='lm')
    d.text((300, y0 + 58), '시범공연', font=f2, fill=(30, 120, 70), anchor='lm')
    d.text((560, y0 + 66), '일시: 96.5.4 16:00 ~ 17:00    T. 325-6282', font=f3, fill=(200, 40, 40), anchor='lm')
    img.paste(ban.resize((2048, 1024 - 2 * CH), Image.LANCZOS), (0, 2 * CH))
    img.save(os.path.join(OUT, 'sign_yonseiro.png'), optimize=True)
    print('sign_yonseiro')


yro_signs()


# sign_rotary.png: 신촌 로터리's blue signs (tools/sinchon_rotary.py rot_dirsign, blender/town.py rot_dirsign), 1024 x 1024:
# - rows 0 - 704: the direction sign over 연세로 north of the junction (1996 photo 51979, reference/고증/4.10.2): 「모래내 ←
#   · → 독립문」 with route 64 in a small shield at each arm of the T, 「130m」 beside its stem; 1.45 : 1 as the photo has
#   it (2 : 1 before 2026-11-15); the romanisation of the time (McCune-Reischauer, 1984 - 2000)
# - rows 704 - 944: the sign of three panels over 연세로's mouth for the cars coming up from 서강로 (52206 · 52141 · 52140,
#   1996.6 - 8): 「양화대교 ←」, 「연희IC ↑ 연세대」, 「아현교차로 →」
# - rows 944 - 1024, the left 170 px: the junction's name plate on the signal arm there, 「신촌로터리」
def rot_signs():
    if ONLY and 'sign_rotary' not in ONLY:
        return
    fb = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'

    def fnt(size):
        for i in (1, 0, 2, 3):
            try:
                return ImageFont.truetype(fb, size, index=i)
            except Exception:
                continue
        return ImageFont.load_default()
    W_, H_ = 1024, 704
    blue, white = (18, 74, 160), (246, 246, 242)
    img = Image.new('RGB', (1024, 1024), blue)
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, W_ - 11, H_ - 11], outline=white, width=8)
    # the T: a stem from the foot up to a bar with an arrowhead at each end
    cx, ybar = W_ // 2, 400
    d.line([(cx, H_ - 60), (cx, ybar)], fill=white, width=30)
    d.line([(120, ybar), (W_ - 120, ybar)], fill=white, width=30)
    for sgn in (-1, 1):
        xe = cx + sgn * (cx - 70)
        d.polygon([(xe, ybar), (xe - sgn * 84, ybar - 56), (xe - sgn * 84, ybar + 56)], fill=white)
        # the route's shield, 64, on the bar
        xs_ = cx + sgn * 190
        d.rounded_rectangle([xs_ - 66, ybar - 52, xs_ + 66, ybar + 52], radius=22, fill=white, outline=blue, width=6)
        f = fnt(74)
        w = d.textlength('64', font=f)
        d.text((xs_ - w / 2, ybar), '64', font=f, fill=blue, anchor='lm')
    for txt, xa, rom in (('모래내', 70, 'Moraenae'), ('독립문', W_ - 70, 'Tongnimmun')):
        f, fr = fnt(150), fnt(50)
        w, wr = d.textlength(txt, font=f), d.textlength(rom, font=fr)
        x0 = xa if xa < cx else xa - w
        d.text((x0, 150), txt, font=f, fill=white, anchor='lm')
        d.text((x0 + (w - wr) / 2, 262), rom, font=fr, fill=white, anchor='lm')
    f = fnt(84)
    w = d.textlength('130m', font=f)
    d.text((cx - 40 - w, H_ - 110), '130m', font=f, fill=white, anchor='lm')
    # the mouth's three panels, as 서울연구원 52007 (1996.8, from the ground south of the mouth) reads them: the side
    # panels' arrows carry route 6's oval, the middle one has its arrow left of two names, each with the romanization
    # of the time under it
    y0, ph = 704, 240
    pw = 1024 / 3
    for k, (top, rom, arrow) in enumerate((('양화대교', 'Yanghwa Brdg.', 'l'), (None, None, 'u'), ('아현교차로', 'Ahyŏn Jct.', 'r'))):
        x0 = k * pw
        d.rectangle([x0 + 5, y0 + 5, x0 + pw - 6, y0 + ph - 6], outline=white, width=5)
        ax, ay = x0 + pw / 2, y0 + 176
        if arrow == 'u':
            ax = x0 + 70
            d.line([(ax, ay + 44), (ax, ay - 70)], fill=white, width=22)
            d.polygon([(ax, ay - 112), (ax - 36, ay - 64), (ax + 36, ay - 64)], fill=white)
            for txt, rom_, yy in (('연희 I.C', 'Yŏnhŭi', y0 + 48), ('연세대', 'Yŏnsei Univ.', y0 + 150)):
                f, fr = fnt(54), fnt(22)
                w, wr = d.textlength(txt, font=f), d.textlength(rom_, font=fr)
                xm = x0 + 200
                d.text((xm - w / 2, yy), txt, font=f, fill=white, anchor='lm')
                d.text((xm - wr / 2, yy + 46), rom_, font=fr, fill=white, anchor='lm')
            continue
        f, fr = fnt(58), fnt(24)
        w, wr = d.textlength(top, font=f), d.textlength(rom, font=fr)
        d.text((x0 + pw / 2 - w / 2, y0 + 62), top, font=f, fill=white, anchor='lm')
        d.text((x0 + pw / 2 - wr / 2, y0 + 112), rom, font=fr, fill=white, anchor='lm')
        sg = -1 if arrow == 'l' else 1
        d.line([(ax - sg * 120, ay), (ax + sg * 90, ay)], fill=white, width=16)
        d.polygon([(ax + sg * 128, ay), (ax + sg * 86, ay - 32), (ax + sg * 86, ay + 32)], fill=white)
        d.ellipse([ax - 44, ay - 27, ax + 44, ay + 27], fill=blue, outline=white, width=5)
        f6 = fnt(40)
        d.text((ax - d.textlength('6', font=f6) / 2, ay), '6', font=f6, fill=white, anchor='lm')
    # the name plate (52007: 「신촌로터리」 over 「Shinchon R.」)
    y0 = 944
    d.rectangle([3, y0 + 3, 166, y0 + 76], outline=white, width=3)
    f, fr = fnt(28), fnt(15)
    w, wr = d.textlength('신촌로터리', font=f), d.textlength('Shinchon R.', font=fr)
    d.text((85 - w / 2, y0 + 30), '신촌로터리', font=f, fill=white, anchor='lm')
    d.text((85 - wr / 2, y0 + 58), 'Shinchon R.', font=fr, fill=white, anchor='lm')
    # the plate between the mouth's two signal heads (52007): 「좌회신호시 / 동교동 창전로」, x 180 - 298 of the last 80
    d.rectangle([182, y0 + 3, 295, y0 + 76], outline=white, width=3)
    for txt, yy, sz in (('좌회신호시', y0 + 25, 21), ('동교동 창전로', y0 + 56, 17)):
        f = fnt(sz)
        w = d.textlength(txt, font=f)
        d.text((239 - w / 2, yy), txt, font=f, fill=white, anchor='lm')
    img.save(os.path.join(OUT, 'sign_rotary.png'), optimize=True)
    print('sign_rotary')


rot_signs()


# banner_halls.png: the cloth banners hung on two halls (blender/landmarks.py museum_porch, daewoo_front), 1024 x 1024,
# one row each (HALL_BANNERS: first row, rows; the same numbers set the UVs there):
# - 백주년기념관's long museum banners, six before the glass (the 1996 graduation photos, reference/백주년기념관_박물관입구_
#   1996_*.jpg): white cloth 1.0 x 3.4 m, 「YONSEI UNIVERSITY MUSEUM」 read downwards in each half, a blue band
#   between the halves, a green and an orange line down the left edge, the museum's small green mark at the foot.
#   Drawn lying down: x down the banner from its top, the image's top row along its right edge
# - 대우관's blue banner over the arched door (대우관_정면_전경.jpg, 대우관_블로그_본관_정면_상뜰.jpg: blue cloth, white
#   words, a mark at each end; the words of 1997 are made up: 상경대학 dates from 연희전문's 상과 of 1915), 9.2 x 0.62 m
# - the lecture's banner under the porch's canopy (박물관 강좌 「민요의 현장을 찾아서 — 한국전통민요의 이해와 감상」,
#   read off three of the four photos; the year and the number left off), 7.4 x 0.95 m
# - the exhibition's banner round the porch's white cylinder (「예학명과 중국 양자강 유역 석각」, all four photos; the
#   small print is made up), 4.7 m round x 1.4 m
HALL_BANNERS = dict(museum=(0, 301), daewoo=(304, 69), lecture=(376, 131), show=(512, 312))


def hall_banners():
    if ONLY and 'banner_halls' not in ONLY:
        return
    K = 2                                                              # drawn at twice the size, then halved

    def fnt(size, path='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'):
        for i in (1, 0, 2, 3):
            try:
                return ImageFont.truetype(path, int(size * K), index=i)
            except Exception:
                continue
        return ImageFont.load_default()

    def fit(d, txt, f_of, size, room):
        """the font of txt at size, made smaller until it is no wider than room (px of the final image)"""
        while size > 8 and d.textlength(txt, font=f_of(size)) > room * K:
            size -= 1
        return f_of(size)

    def squeezed(txt, f, fg, bg, w, h):
        """txt drawn at the font f and squeezed to w x h px (of the final image): a condensed face"""
        tw, th = int(f.getlength(txt)) + 4, int(f.size * 1.4)
        t = Image.new('RGB', (tw, th), bg)
        ImageDraw.Draw(t).text((2, th / 2), txt, font=f, fill=fg, anchor='lm')
        bb = ImageDraw.Draw(t).textbbox((2, th / 2), txt, font=f, anchor='lm')
        t = t.crop((max(0, bb[0] - 2), max(0, bb[1] - 2), min(tw, bb[2] + 2), min(th, bb[3] + 2)))
        return t.resize((int(w * K), int(h * K)), Image.LANCZOS)

    def mark(d, x, y, s, fg, bg):
        """the museum's small mark: a green square with a dark bar under it (s px of the final image)"""
        d.rectangle([x * K, y * K, (x + s) * K, (y + s * 0.62) * K], fill=(40, 140, 80))
        d.rectangle([x * K, (y + s * 0.7) * K, (x + s) * K, (y + s) * K], fill=(36, 36, 36))
        d.rectangle([(x + s * 0.18) * K, (y + s * 0.16) * K, (x + s * 0.82) * K, (y + s * 0.46) * K], fill=bg)

    W = 1024
    img = Image.new('RGB', (W * K, W * K), (240, 240, 236))
    d = ImageDraw.Draw(img)
    white, ink, green, orange, blue = (246, 246, 242), (62, 62, 66), (40, 140, 80), (226, 120, 40), (30, 72, 168)

    # the museum banner (lying down: x from its top, row 0 its right edge)
    y0, h = HALL_BANNERS['museum']
    d.rectangle([0, y0 * K, W * K, (y0 + h) * K], fill=white)
    band = 470
    d.rectangle([band * K, y0 * K, (band + 16) * K, (y0 + h) * K], fill=blue)
    for xa, xb, col in ((12, band - 6, green), (band + 22, W - 12, orange)):
        d.rectangle([xa * K, (y0 + h - 40) * K, xb * K, (y0 + h - 34) * K], fill=col)
    word = squeezed('YONSEI UNIVERSITY MUSEUM', fnt(60, '/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc'), ink, white, 410, 44)
    for xa in (36, band + 56):
        img.paste(word, (xa * K, (y0 + h - 94) * K))
    mark(d, W - 70, y0 + h - 86, 40, green, white)

    # 대우관's banner: blue cloth, white words, a round mark at each end
    y0, h = HALL_BANNERS['daewoo']
    d.rectangle([0, y0 * K, W * K, (y0 + h) * K], fill=(26, 66, 160))
    for xc in (34, W - 34):
        r = h * 0.36
        d.ellipse([(xc - r) * K, (y0 + h / 2 - r) * K, (xc + r) * K, (y0 + h / 2 + r) * K], outline=white, width=3 * K)
        d.rectangle([(xc - r * 0.45) * K, (y0 + h / 2 - r * 0.5) * K, (xc + r * 0.45) * K, (y0 + h / 2 + r * 0.5) * K], fill=white)
    txt = '상경대학 창립 82주년 기념 학술 심포지엄'
    f = fit(d, txt, fnt, 34, W - 150)
    d.text((W / 2 * K, (y0 + h / 2) * K), txt, font=f, fill=white, anchor='mm')

    # the lecture: white cloth, a green flag top left, the title in black, the subtitle in green, a green foot
    y0, h = HALL_BANNERS['lecture']
    d.rectangle([0, y0 * K, W * K, (y0 + h) * K], fill=white)
    d.polygon([(0, y0 * K), (430 * K, y0 * K), (400 * K, (y0 + 26) * K), (0, (y0 + 26) * K)], fill=green)
    d.text((24 * K, (y0 + 13) * K), '연세대학교 박물관 강좌', font=fnt(19), fill=white, anchor='lm')
    d.text((W / 2 * K, (y0 + 56) * K), '민요의 현장을 찾아서', font=fit(d, '민요의 현장을 찾아서', fnt, 50, 820), fill=(24, 24, 24), anchor='mm')
    d.text((W / 2 * K, (y0 + 96) * K), '— 한국전통민요의 이해와 감상 —', font=fnt(19), fill=green, anchor='mm')
    d.rectangle([0, (y0 + h - 20) * K, W * K, (y0 + h) * K], fill=green)
    d.text((W / 2 * K, (y0 + h - 10) * K), '▪ 곳: 백주년기념관 시청각실        ▪ 주최: 연세대학교 박물관',
           font=fnt(13), fill=white, anchor='mm')

    # the exhibition round the cylinder: white, a green and an orange line down the left, a blue line along the top,
    # the stone's name in pale grey brush strokes on the left, the title in black on the right
    y0, h = HALL_BANNERS['show']
    d.rectangle([0, y0 * K, W * K, (y0 + h) * K], fill=white)
    d.rectangle([60 * K, (y0 + 10) * K, 68 * K, (y0 + 70) * K], fill=green)
    d.rectangle([60 * K, (y0 + 70) * K, 68 * K, (y0 + h - 10) * K], fill=orange)
    d.text((86 * K, (y0 + 34) * K), '연세대학교 박물관 특별 전시', font=fnt(19), fill=ink, anchor='lm')
    d.polygon([(76 * K, (y0 + 64) * K), (W * K, (y0 + 58) * K), (W * K, (y0 + 66) * K), (76 * K, (y0 + 72) * K)], fill=blue)
    fs = fnt(66, '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc')
    for k, ch in enumerate('瘞鶴銘'):
        d.text((150 * K, (y0 + 118 + k * 66) * K), ch, font=fs, fill=(196, 196, 192), anchor='mm')
    fs = fnt(50, '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc')
    for k, ch in enumerate('鶴壽不知'):
        d.text((232 * K, (y0 + 120 + k * 52) * K), ch, font=fs, fill=(206, 206, 202), anchor='mm')
    d.text((640 * K, (y0 + 132) * K), '예학명과', font=fnt(54), fill=(24, 24, 24), anchor='mm')
    d.text((640 * K, (y0 + 208) * K), '중국 양자강 유역 석각', font=fit(d, '중국 양자강 유역 석각', fnt, 54, 600), fill=(24, 24, 24), anchor='mm')
    d.text((330 * K, (y0 + 268) * K), '전시장소: 연세대학교 박물관 (백주년기념관)', font=fnt(15), fill=ink, anchor='lm')
    d.text((330 * K, (y0 + 290) * K), '주최: 연세대학교 박물관', font=fnt(15), fill=ink, anchor='lm')
    mark(d, W - 80, y0 + h - 66, 44, green, white)

    img = img.resize((W, W), Image.LANCZOS)
    img.save(os.path.join(OUT, 'banner_halls.png'), optimize=True)
    print('banner_halls')


hall_banners()


# sign_mouth.png (RGBA, 1024 x 1024, drawn at 2048) and data/sign_mouth_uv.json (each piece's rectangle as u0, v0, u1, v1, v up):
# the boards of 연세로's mouth and 그랜드마트 as the 1995 · 1996 photos show them (고증 4.10.7, blender/town.py _kumkang,
# _hongik, _grand).  금강제화 (52206 · 52006): the white band over the ground floor, a maroon arch with 「금강제화」 in
# white and 「Kumkang」 in red; the corner's red-and-white upright; the clinics', a 법무사's and 바둑's boards up the floors.
# 홍익문고 (52004 · 52006): the white board along the top of the south face, a dark green ring with its mark and
# 「홍익문고」 in red; the black upright on the west face.  그랜드마트 (52135 · 52119 · 52095): the red mark and 「그랜드마트
# 신촌점」 straight on the tiles (transparent round them), the sale banners down the round face, the poster, the
# fascia over the shop windows.  The words of the banners and boards are what the photos let one read; the poster's
# picture is not drawn, only its words
def mouth_signs():
    if ONLY and 'sign_mouth' not in ONLY:
        return
    fb = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
    fbo = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'

    def fnt(size, path=fb):
        for i in (1, 0, 2, 3):
            try:
                return ImageFont.truetype(path, size, index=i)
            except Exception:
                continue
        return ImageFont.load_default()

    W = 2048
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    uv = {}

    def piece(name, x0, y0, w, h):
        uv[name] = [round(x0 / W, 5), round(1 - (y0 + h) / W, 5), round((x0 + w) / W, 5), round(1 - y0 / W, 5)]
        return x0, y0, w, h

    def fit(txt, size, maxw, path=fb):
        while True:
            f = fnt(size, path)
            if d.textlength(txt, font=f) <= maxw or size < 14:
                return f
            size -= 2

    def text_c(cx, cy, txt, size, maxw, fill, path=fb, spacing=0):
        f = fit(txt, size, maxw, path)
        if spacing:
            ws = [d.textlength(ch, font=f) for ch in txt]
            tot = sum(ws) + spacing * (len(txt) - 1)
            x = cx - tot / 2
            for ch, w_ in zip(txt, ws):
                d.text((x, cy), ch, font=f, fill=fill, anchor='lm')
                x += w_ + spacing
            return
        w_ = d.textlength(txt, font=f)
        d.text((cx - w_ / 2, cy), txt, font=f, fill=fill, anchor='lm')

    def vtext(cx, y0, y1, txt, size, fill, path=fb):
        f = fnt(size, path)
        step = (y1 - y0) / len(txt)
        for k, ch in enumerate(txt):
            w_ = d.textlength(ch, font=f)
            d.text((cx - w_ / 2, y0 + step * (k + 0.5)), ch, font=f, fill=fill, anchor='lm')

    white, maroon, kred = (246, 245, 240, 255), (112, 26, 26, 255), (196, 40, 36, 255)
    # 금강제화's band over the ground floor, the south face (16 : 1): Kumkang | the arch | Kumkang
    x0, y0, w, h = piece('kk_band', 0, 0, 2048, 128)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=white)
    d.line([(x0, y0 + h - 3), (x0 + w, y0 + h - 3)], fill=(200, 196, 188, 255), width=5)
    d.chord([x0 + 470, y0 + 14, x0 + 1290, y0 + 14 + 2 * (h - 14)], 180, 360, fill=maroon)     # (a low arch on the band's foot)
    text_c(x0 + 880, y0 + 78, '금강제화', 74, 520, white, spacing=26)
    text_c(x0 + 1640, y0 + 66, 'Kumkang', 70, 420, kred, path=fbo)
    text_c(x0 + 230, y0 + 66, 'Kumkang', 70, 420, kred, path=fbo)
    # the east face's (8 : 1)
    x0, y0, w, h = piece('kk_band_e', 0, 128, 1024, 128)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=white)
    d.line([(x0, y0 + h - 3), (x0 + w, y0 + h - 3)], fill=(200, 196, 188, 255), width=5)
    text_c(x0 + 512, y0 + 66, 'Kumkang', 70, 600, kred, path=fbo)
    # the corner's upright (1 : 5)
    x0, y0, w, h = piece('kk_up', 1024, 128, 128, 640)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=white)
    d.rectangle([x0 + 10, y0 + 14, x0 + w - 11, y0 + h - 15], outline=kred, width=6)
    d.ellipse([x0 + 22, y0 + 40, x0 + w - 22, y0 + 120], fill=kred)
    vtext(x0 + w / 2, y0 + 150, y0 + h - 40, '금강제화', 74, kred)
    # the boards up the floors (4 : 1 and 5 : 1): [words, ground, ink]
    boards = [('포켓볼전용', (200, 34, 30, 255), white), ('법무사', (22, 30, 70, 255), white), ('신진 바둑', (236, 234, 228, 255), (90, 90, 96, 255)),
              ('주인일 내과', (244, 242, 236, 255), (190, 30, 36, 255)), ('박비뇨기과 · 피부과', (28, 34, 82, 255), white),
              ('이비인후과의원', (244, 242, 236, 255), (196, 30, 40, 255)), ('신촌치과의원', (246, 244, 238, 255), (190, 28, 34, 255))]
    for i, (txt, bg, fg) in enumerate(boards):
        x0, y0, w, h = piece('kk_b%d' % i, 1152 + (i % 2) * 448, 128 + (i // 2) * 112, 440, 104)
        d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=bg)
        d.rectangle([x0 + 4, y0 + 4, x0 + w - 5, y0 + h - 5], outline=tuple(int(c * 0.8) for c in fg[:3]) + (255,), width=3)
        text_c(x0 + w / 2, y0 + h / 2 + 2, txt, 64, w - 40, fg)
    # 홍익문고's board along the top of the south face (4.2 : 1): the ring with its mark, 「홍익문고」 in red
    x0, y0, w, h = piece('hk_top', 0, 256, 1024, 244)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=(242, 240, 234, 255))
    gr = (30, 74, 50, 255)
    cx_, cy_, r_ = x0 + 130, y0 + h / 2, 86
    d.ellipse([cx_ - r_, cy_ - r_, cx_ + r_, cy_ + r_], outline=gr, width=13)
    d.rectangle([cx_ - 40, cy_ - 52, cx_ - 22, cy_ + 52], fill=gr)
    d.rectangle([cx_ + 22, cy_ - 52, cx_ + 40, cy_ + 52], fill=gr)
    d.rectangle([cx_ - 40, cy_ - 9, cx_ + 40, cy_ + 9], fill=gr)
    d.line([(cx_ - 64, cy_ - 52), (cx_ + 64, cy_ - 52)], fill=gr, width=12)
    d.line([(cx_ - 64, cy_ + 52), (cx_ + 64, cy_ + 52)], fill=gr, width=12)
    text_c(x0 + 600, y0 + h / 2 + 4, '홍익문고', 150, 700, (200, 40, 34, 255), path=fbo, spacing=70)
    # its upright on the west face (1 : 4.5), black with white words
    x0, y0, w, h = piece('hk_up', 1024, 768, 112, 504)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=(20, 20, 22, 255))
    vtext(x0 + w / 2, y0 + 20, y0 + h - 20, '홍익문고', 70, (240, 240, 236, 255))
    # its ground floor's fascia on 연세로 (6 : 1)
    x0, y0, w, h = piece('hk_shop', 0, 512, 768, 128)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=(22, 70, 150, 255))
    text_c(x0 + w / 2, y0 + h / 2 + 2, '홍익문고  ·  서적 · 문구', 70, w - 60, (255, 255, 255, 255))
    # 그랜드마트's mark and words on the tiles (transparent round them): the red square with its white sweep,
    # 「그랜드마트」, 「신촌점」 under it
    x0, y0, w, h = piece('gm_logo', 0, 1024, 1024, 330)
    red = (204, 32, 40, 255)
    d.rounded_rectangle([x0 + 20, y0 + 30, x0 + 190, y0 + 200], 22, fill=red)
    d.polygon([(x0 + 52, y0 + 168), (x0 + 160, y0 + 60), (x0 + 176, y0 + 80), (x0 + 74, y0 + 182)], fill=(255, 255, 255, 255))
    d.polygon([(x0 + 52, y0 + 110), (x0 + 110, y0 + 60), (x0 + 124, y0 + 76), (x0 + 70, y0 + 124)], fill=(255, 255, 255, 255))
    text_c(x0 + 600, y0 + 118, '그랜드마트', 168, 780, red, spacing=8)
    text_c(x0 + 600, y0 + 270, '신 촌 점', 96, 400, (176, 30, 36, 255))
    # the banners down the round face (1 : 6.4)
    banners = [('그랜드 파격가 총정리', (196, 30, 36, 255), (255, 255, 255, 255)),
               ('여름인기상품 창고大공개', (246, 246, 244, 255), (30, 60, 150, 255)),
               ('산지직송 가격파괴', (250, 248, 240, 255), (200, 30, 40, 255)),
               ('가격파괴', (240, 196, 40, 255), (180, 24, 30, 255))]
    for i, (txt, bg, fg) in enumerate(banners):
        x0, y0, w, h = piece('gm_ban%d' % i, 1152 + i * 160, 768, 150, 960)
        d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=bg)
        d.rectangle([x0 + 8, y0 + 8, x0 + w - 9, y0 + h - 9], outline=fg, width=4)
        chars = txt.replace(' ', '')
        vtext(x0 + w / 2, y0 + 40, y0 + h - 40, chars, min(96, int((h - 80) / len(chars) * 0.9)), fg)
    # the poster (1 : 1.35): its words only
    x0, y0, w, h = piece('gm_poster', 0, 1400, 480, 648)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=(238, 236, 228, 255))
    d.rectangle([x0, y0 + 430, x0 + w - 1, y0 + h - 1], fill=(250, 220, 60, 255))
    d.ellipse([x0 + 70, y0 + 60, x0 + 410, y0 + 400], fill=(232, 200, 176, 255))
    text_c(x0 + w / 2, y0 + 500, '가려워!', 110, w - 60, (210, 30, 40, 255))
    text_c(x0 + w / 2, y0 + 600, '그랜드마트 신촌점', 48, w - 80, (40, 40, 60, 255))
    # the fascia over the shop windows (10 : 1)
    x0, y0, w, h = piece('gm_fascia', 512, 1760, 1024, 102)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=(34, 70, 56, 255))
    text_c(x0 + w / 2, y0 + h / 2 + 2, 'GRAND MART   그랜드마트', 66, w - 80, (240, 240, 230, 255), path=fbo)
    # (drawn at twice, kept at 1024 in a palette of 128 colours: about 80 KB)
    img.resize((W // 2, W // 2), Image.LANCZOS).quantize(128, method=Image.FASTOCTREE).save(os.path.join(OUT, 'sign_mouth.png'), optimize=True)
    with open(os.path.join(ROOT, 'data/sign_mouth_uv.json'), 'w') as fp:
        json.dump(uv, fp, indent=1, ensure_ascii=False)
        fp.write('\n')
    print('sign_mouth')


mouth_signs()


# hangeul_tower.png: what is cut in 연세한글탑's granite (blender/landmarks.py hangeul_tower, reference/고증/4.14), the
# cuts dark, the rest cut away (alpha).  Left half: 「연세한글탑」 down the south slab (0.44 x 2.1 m), the letters as
# they stand in han.jpg of the school's 1996 site and the 1990s photographs.  Right half, bottom 480 px: the framed
# panel high on the east leg's south flank (0.55 x 0.95 m) with the two marks seen in the photograph from the
# south-south-east (its finer cutting does not show; not drawn).
def hangeul_tower_tex():
    if ONLY and 'hangeul_tower' not in ONLY:
        return
    W, H = 512, 1536
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ink = (58, 56, 52, 255)
    # the letters: drawn on a 256 x 1222 canvas (the quad's 0.44 x 2.1 m at one scale) and stretched to 256 x 1536
    cw, ch = 256 * SS, 1222 * SS
    col = Image.new('L', (cw, ch), 0)
    d = ImageDraw.Draw(col)
    f = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', int(226 * SS), index=1)   # (KR)
    pitch = ch / 5
    for i, ch_ in enumerate('연세한글탑'):
        d.text((cw / 2, pitch * (i + 0.5)), ch_, font=f, fill=255, anchor='mm')
    col = col.resize((256, 1536), Image.LANCZOS)
    img.paste(Image.new('RGBA', (256, 1536), ink), (0, 0), col)
    # the panel: a double frame, two marks like ㅜ side by side in its upper half (a long bar, a short stem)
    pw, ph = 256 * SS, 480 * SS
    pan = Image.new('L', (pw, ph), 0)
    d = ImageDraw.Draw(pan)
    lw = 7 * SS
    d.rectangle([lw, lw, pw - 1 - lw, ph - 1 - lw], outline=255, width=lw)
    d.rectangle([4 * lw, 4 * lw, pw - 1 - 4 * lw, ph - 1 - 4 * lw], outline=255, width=lw // 2 + 1)
    for cx in (0.33, 0.67):
        x = cx * pw
        d.line([(x - 0.15 * pw, 0.3 * ph), (x + 0.15 * pw, 0.3 * ph)], fill=255, width=lw)
        d.line([(x, 0.3 * ph), (x, 0.4 * ph)], fill=255, width=lw)
    pan = pan.resize((256, 480), Image.LANCZOS)
    img.paste(Image.new('RGBA', (256, 480), ink), (256, H - 480), pan)
    img.save(os.path.join(OUT, 'hangeul_tower.png'), optimize=True)
    print('hangeul_tower')


hangeul_tower_tex()


# yongjae_plaque.png: the black plate on the front of 용재 동상's block (blender/statues.py yongjae_statue, 0.80 x 0.61 m;
# reference/고증/3.2-3.3 「용재 동상」): 「용재 백낙준 박사상」 across its head as in the photos of 2005 and 2007, the
# inscription under it in small letters.  Of the inscription only the sentence 뉴스타파 (2019-07-19) quotes is known; it
# is set here over the lines the photos show (too small to read in them).
def yongjae_plaque_tex():
    if ONLY and 'yongjae_plaque' not in ONLY:
        return
    W, H = 512, 390
    img = Image.new('RGB', (W * SS, H * SS), (17, 18, 20))
    d = ImageDraw.Draw(img)
    ink = (176, 174, 166)
    font = lambda px: ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc', int(px * SS), index=1)   # (KR)
    f = font(40)
    x = 62 * SS
    for ch_ in '용재 백낙준 박사상':
        if ch_ != ' ':
            d.text((x, 44 * SS), ch_, font=f, fill=ink, anchor='lm')
        x += (46 if ch_ != ' ' else 22) * SS
    text = ('교육과 학문 민족봉사와 자유정신의 구현에 뜻을 두시고 일생동안 연세와 민족을 붙들고 키운 연세의 정신적 지주시며 '
            '민족교육의 스승이시며 겨레의 지도자시고 하나님의 종이시다.')
    f = font(21)
    lines, line = [], ''
    for word in text.split(' '):
        if d.textlength((line + ' ' + word).strip(), font=f) > (W - 56) * SS:
            lines.append(line)
            line = word
        else:
            line = (line + ' ' + word).strip()
    lines.append(line)
    for i, ln in enumerate(lines):
        d.text((28 * SS, (118 + i * 50) * SS), ln, font=f, fill=(150, 148, 142), anchor='lm')
    img = img.resize((W, H), Image.LANCZOS)
    img.save(os.path.join(OUT, 'yongjae_plaque.png'), optimize=True)
    print('yongjae_plaque')


yongjae_plaque_tex()


# ---------------------------------------------------------------- 옛 신촌역 역사의 이름판
# The board on the waiting hall's gable (서울연구원 52234 · 52245 · 52250, 1996): white, a thin dark rim, 「신촌역」 big,
# 「新村驛」 under it, 「Shinchon Station」 at the foot; 2.3 x 0.95 m (blender/town.py station97), drawn 1024 x 424 and
# stretched to 1024 x 512
def station_sign():
    if ONLY and 'sign_station' not in ONLY:
        return
    fb = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
    fs = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'
    fm = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'

    def fnt(path, size):
        for i in (1, 0, 2, 3):
            try:
                return ImageFont.truetype(path, size, index=i)
            except Exception:
                continue
        return ImageFont.load_default()
    W_, H_ = 1024, 424
    img = Image.new('RGB', (W_, H_), (244, 244, 238))
    d = ImageDraw.Draw(img)
    d.rectangle([6, 6, W_ - 7, H_ - 7], outline=(40, 40, 40), width=10)
    for txt, path, size, y in (('신촌역', fb, 190, 130), ('新村驛', fs, 84, 272), ('Shinchon Station', fm, 64, 362)):
        f = fnt(path, size)
        w = d.textlength(txt, font=f)
        d.text((W_ / 2 - w / 2, y), txt, font=f, fill=(22, 22, 22), anchor='lm')
    img.resize((1024, 512), Image.LANCZOS).save(os.path.join(OUT, 'sign_station.png'), optimize=True)
    print('sign_station')


station_sign()


# ---------------------------------------------------------------- 서문분식 간판
# The board over 서문분식 at 83번지's ground floor by 서문 (tools/seomun.py SHOP, reference/고증/3.22 「서문 앞 가게」):
# white with green letters (the place and the colours as an alumna/alumnus remembers them; the frame and the size like
# the shop board in that place in the 2011 roadview), drawn as 연세로's shop signs are, 512 x 128 (4 : 1)
def seomun_sign():
    if ONLY and 'sign_seomun' not in ONLY:
        return
    fb = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'

    def fnt(size):
        for i in (1, 0, 2, 3):
            try:
                return ImageFont.truetype(fb, size, index=i)
            except Exception:
                continue
        return ImageFont.load_default()
    bg, fg = (250, 250, 246), (22, 128, 62)
    img = Image.new('RGB', (512, 128), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([6, 6, 505, 121], outline=tuple(int(c * 0.75) for c in fg), width=4)
    txt = '서문분식'
    size = 96
    while True:
        f = fnt(size)
        w = d.textlength(txt, font=f)
        if w < 420 or size < 30:
            break
        size -= 4
    d.text((256 - w / 2, 64), txt, font=f, fill=fg, anchor='lm')
    img.save(os.path.join(OUT, 'sign_seomun.png'), optimize=True)
    print('sign_seomun')


seomun_sign()

if ONLY:
    raise SystemExit(0)

# ---------------------------------------------------------------- signs
FONT_B = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
FONT_S = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'


def font(path, size, idx=1):
    for i in (idx, 0, 1, 2, 3):
        try:
            return ImageFont.truetype(path, size, index=i)
        except Exception:
            continue
    return ImageFont.load_default()

SIGNS = [('독수리다방', (180, 30, 30), (255, 240, 200)), ('연세문구', (20, 60, 150), (255, 255, 255)),
         ('서점', (30, 110, 60), (255, 255, 230)), ('만화방', (250, 200, 30), (40, 30, 20)),
         ('복사·제본', (255, 255, 255), (30, 60, 160)), ('호프 · 생맥주', (120, 30, 20), (255, 220, 120)),
         ('당구장', (20, 20, 20), (255, 80, 60)), ('분식 떡볶이', (230, 90, 30), (255, 255, 255)),
         ('레코드 · 테이프', (60, 20, 100), (255, 230, 120)), ('삐삐 · 시티폰', (0, 120, 170), (255, 255, 255)),
         ('하숙 · 자취방', (255, 250, 240), (150, 30, 30)), ('노래방', (200, 20, 120), (255, 255, 120)),
         ('통닭 · 맥주', (200, 120, 20), (255, 255, 255)), ('안경원', (30, 30, 90), (220, 220, 255)),
         ('약국', (40, 130, 60), (255, 255, 255)), ('비디오 대여', (20, 20, 20), (90, 220, 255))]
S = 1024
img = Image.new('RGB', (S, S), (200, 200, 200))
d = ImageDraw.Draw(img)
for i, (txt, bg, fg) in enumerate(SIGNS):          # 2 columns x 8 rows, each sign 512x128 (4:1)
    x0, y0 = (i % 2) * 512, (i // 2) * 128
    d.rectangle([x0, y0, x0 + 511, y0 + 127], fill=bg)
    d.rectangle([x0 + 6, y0 + 6, x0 + 505, y0 + 121], outline=tuple(int(c * 0.75) for c in fg), width=4)
    size = 96
    while True:
        f = font(FONT_B, size)
        w = d.textlength(txt, font=f)
        if w < 440 or size < 30:
            break
        size -= 4
    d.text((x0 + 256 - w / 2, y0 + 64), txt, font=f, fill=fg, anchor='lm')
img.save(os.path.join(OUT, 'sign_shops.png'), optimize=True)

# gate plaque: carved granite with gilded hanja + hangul
W, H = 1024, 256
img = Image.new('RGB', (W, H), (175, 172, 165))
noise = (np.random.RandomState(3).rand(H, W) * 30 - 15)
arr = np.array(img).astype(np.float32) + noise[..., None]
img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)
f = font(FONT_S, 150, 1)
txt = '延世大學校'
w = d.textlength(txt, font=f)
d.text((W / 2 - w / 2 + 3, H / 2 + 3), txt, font=f, fill=(70, 66, 60), anchor='lm')
d.text((W / 2 - w / 2, H / 2), txt, font=f, fill=(40, 38, 34), anchor='lm')
img.save(os.path.join(OUT, 'sign_gate.png'))
print('signs ok')


# ---------------------------------------------------------------- pre-2004 Korean licence plates + taxi sign
# 2x2 atlas (512x256 each): [0] green private, [1] green private, [2] yellow commercial (taxi), [3] taxi roof sign
PW, PH = 512, 256
img = Image.new('RGB', (PW * 2, PH * 2), (0, 0, 0))
d = ImageDraw.Draw(img)
plates = [((38, 104, 64), (245, 245, 240), '서울 33', '가 1997'), ((38, 104, 64), (245, 245, 240), '서울 52', '러 4821'),
          ((236, 196, 40), (30, 40, 90), '서울 31', '바 2380')]
for i, (bg, fg, top, bottom) in enumerate(plates):
    x0, y0 = (i % 2) * PW, (i // 2) * PH
    d.rectangle([x0, y0, x0 + PW - 1, y0 + PH - 1], fill=bg)
    d.rectangle([x0 + 8, y0 + 8, x0 + PW - 9, y0 + PH - 9], outline=fg, width=6)
    f1, f2 = font(FONT_B, 72), font(FONT_B, 132)
    w1 = d.textlength(top, font=f1)
    d.text((x0 + PW / 2 - w1 / 2, y0 + 62), top, font=f1, fill=fg, anchor='lm')
    w2 = d.textlength(bottom, font=f2)
    d.text((x0 + PW / 2 - w2 / 2, y0 + 172), bottom, font=f2, fill=fg, anchor='lm')
    for bx in (40, PW - 40):
        d.ellipse([x0 + bx - 9, y0 + 30, x0 + bx + 9, y0 + 48], fill=tuple(int(c * 0.7) for c in fg))
x0, y0 = PW, PH                              # taxi roof sign
d.rectangle([x0, y0, x0 + PW - 1, y0 + PH - 1], fill=(255, 196, 30))
d.rectangle([x0 + 10, y0 + 10, x0 + PW - 11, y0 + PH - 11], outline=(40, 40, 40), width=8)
f = font(FONT_B, 150)
w = d.textlength('개인', font=f)
d.text((x0 + PW / 2 - w / 2, y0 + PH / 2 + 4), '개인', font=f, fill=(25, 25, 25), anchor='lm')
img.save(os.path.join(OUT, 'plates.png'), optimize=True)

print('plates ok')
