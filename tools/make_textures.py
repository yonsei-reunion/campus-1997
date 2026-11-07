"""Procedurally paint foliage atlases, 1990s shop signs and the main-gate plaque.

Outputs (web/public/assets/textures):
  leaf_<species>[_<season>].png   2x2 atlas of leaf-cluster cards, RGBA (alpha-tested)
  litter_ginkgo.png               fallen ginkgo leaves, seamless tile, alpha = each leaf's rank
  litter_petals.png               fallen cherry petals, the same
  sign_shops.png                  4x4 atlas of 1997 Sinchon storefront signboards
  sign_gate.png                   延世大學校 gate plaque
Run: .venv/bin/python tools/make_textures.py
"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

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
atlas('boxwood', 'boxwood', [(45, 82, 32), (55, 95, 36), (38, 70, 28)])
atlas('azalea', 'azalea', [(55, 90, 35), (65, 100, 40)], flowers=((225, 60, 150), 380, (0.045, 0.06)))
atlas('azalea_summer', 'azalea', [(55, 90, 35), (65, 100, 40)])
atlas('azalea_red', 'azalea', [(50, 85, 32), (60, 95, 38)], flowers=((200, 32, 48), 300, (0.04, 0.055)))
# the flower border along the top of the banks by the steps up to 언더우드관 정원 (the 2003 spring photo): yellow
# pansies with a few white and purple ones among small leaves
atlas('pansy', 'pansy', [(60, 100, 40), (72, 112, 46), (52, 88, 34)],
      flowers=[((246, 206, 40), 560, (0.034, 0.048), (60, 40, 20)), ((250, 246, 236), 40, (0.032, 0.044), (230, 190, 40)),
               ((120, 70, 150), 22, (0.032, 0.044), (240, 200, 60))])


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
# 4.6 (1 - 0.14) / (one leaf's share of the tile): the coverage above rank t is then 1 - exp(-4.6 (1 - t)).
def litter(name, kind, palette, n, size, seed=0):
    if ONLY and name not in ONLY:
        return
    rnd = random.Random(seed)
    S = CELL * SS
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    rank = Image.new('L', (S, S), 0)
    d, dk = ImageDraw.Draw(img), ImageDraw.Draw(rank)
    shape_fn = {'ginkgo': shape_ginkgo, 'petal': shape_petal}[kind]
    leaves = sorted((rnd.uniform(0.14, 1.0), rnd.uniform(0, S), rnd.uniform(0, S), rnd.uniform(0, 2 * math.pi),
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
    out.save(os.path.join(OUT, f'{name}.png'), optimize=True)
    al = np.array(out)[..., 3] / 255
    print('litter', name, 'cover above rank 0.14 / 0.5 / 0.8: %.2f %.2f %.2f (1 - exp(-4.6 (1 - t)): 0.98 0.90 0.60)'
          % ((al > 0.14).mean(), (al > 0.5).mean(), (al > 0.8).mean()))


litter('litter_ginkgo', 'ginkgo', [(240, 200, 40), (230, 185, 30), (250, 215, 70), (215, 170, 30), (200, 180, 50),
                                   (236, 196, 52), (190, 150, 40), (175, 130, 45)], 1500, (0.036, 0.052), seed=18)
# Somei-yoshino petals 1.1-1.5 cm long, near white with a blush of pink, a few going brown
litter('litter_petals', 'petal', [(246, 206, 218), (248, 216, 226), (250, 226, 233), (244, 198, 212), (252, 236, 240),
                                  (240, 190, 205), (247, 222, 228), (236, 214, 208)], 8200, (0.0275, 0.0375), seed=35)

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
