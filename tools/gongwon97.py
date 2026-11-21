"""공학원 공사장의 1997년 7월 구덩이: 바닥판 · 흙막이 · 복공 · 자재 (#181; reference/고증/4.4_정구장과_공학원_공사장.md
「원본 스캔으로 다시 읽은 구덩이」). tools/build_campus.py 가 부른다.

    took, cells, poly, top, info = gongwon97.dig(Hn, X, Y, sample, step, half)    # 심기가 끝난 뒤, 공사장 둘레의 땅을 다 고른 다음
    gongwon97.walls(top, foot)                                        # 흙막이(엄지말뚝 · 토류판 · 띠장)와 서쪽 판의 면
    gongwon97.pieces(up)                                              # 바닥판 · 올라온 판 · 복공 · 자재(campus.json)

.venv/bin/python tools/gongwon97.py stuff    자재 더미를 원본 스캔 26/16 에서 다시 읽어 tools/gongwon97_stuff.json 으로

Frames: the site's own (u, v) (tools/build_campus.py TENNIS: origin (-222, -392), turned -13 deg; u along the site, v up
its slope), x east, y north.  Every absolute height is above sea level (해발), taken up to the working datum where read.

What the 1997-07-28 scans give (26/16 x 26/15 on a 1 m grid with 1.25 m windows, the median of each level; 26/16 x
27/17 across the courses on the east part):

- DECKS: no storey over the ground yet, but the pit is not one level.  The deck (the first basement's floor, its columns'
  stubs up) at 25.03 m over the north part, 24.64 m along the south and 24.52 m along the east side; over an L (the
  south band and a column up the east third) a slab on its shoring at 28.97 m (the cross-course pair: 29.3 - 29.5 m),
  a little over the ground round the site (28.2 - 28.6 m): the ground floor's slab being formed.  The west 25 m is the
  slab at the ground's height (28.24 m) as before (build_campus.py GW_SLAB)
- RIM: the dig reaches the hoarding on the south and the east: there the hoarding stands on the soldier piles' heads.
  Its south face read in both course-26 frames as one face 26.5 - 31.1 m high (the lagging's top over the deck, the
  hoarding's panels over it); the piles 1.82 m apart in both frames' rows.  On the north the dig's edge is 3 m inside
  the hoarding (a strip at the ground's height between), and at its west end the hoarding steps 4.5 m north round a
  steel deck (복공) over the dig with two framed openings
- the stuff on the decks: rebar bundles, stacks of forms and lumber (stuff(): blobs off the deck's own brightness)

Nothing here draws from build_campus.py's `rng`.
"""
import json
import math
import os
import sys

import numpy as np
import shapely
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import datum

O, ROT = (-222.0, -392.0), math.radians(-13.0)
_C, _S = math.cos(ROT), math.sin(ROT)


def xy(u, v):
    return O[0] + u * _C - v * _S, O[1] + u * _S + v * _C


def uv(x, y):
    dx, dy = x - O[0], y - O[1]
    return dx * _C + dy * _S, -dx * _S + dy * _C


def poly(pts):
    return Polygon([xy(u, v) for u, v in pts])


# the dig's edge (the lagging's face), counter-clockwise from its south-west corner: the south side under the hoarding
# (its step north at u 10.4 and its corner cut to the east side), the east side under the hoarding, the north side 3 m
# inside it, the pocket under the steel deck at its west end; the west side the slab's edge
RIM_UV = [(-55.5, -4.4), (10.4, -4.4), (10.4, -1.2), (36.7, -1.2), (53.8, 4.9), (53.8, 76.9), (-28.0, 76.9), (-28.0, 84.3),
          (-55.0, 84.3), (-55.0, 76.9), (-55.5, 76.9)]
RIM = poly(RIM_UV)
WEST_U = -55.5                       # (the slab's edge: its face concrete, not lagging)
# the deck's levels (해발) and where each holds (u0, u1, v0, v1), cut to the rim; the first that holds wins
DECK_LEVELS = [('north', (-56.0, 21.0, 34.0, 85.0), 25.03), ('east', (39.0, 54.0, 7.0, 77.0), 24.52),
               ('column', (21.0, 39.0, 34.0, 77.0), 25.03), ('south', (-56.0, 54.0, -5.0, 34.0), 24.64)]
FLOOR = 24.15                        # (the nodes under the decks: under the lowest)
# the slab on its shoring (the ground floor's, being formed): the south band and the column up the east third
RAISED_UV = [(-55.5, 7.5), (-5.5, 7.5), (-5.5, 10.5), (12.0, 10.5), (12.0, 12.0), (21.0, 12.0), (21.0, 16.5), (39.2, 16.5),
             (39.2, 76.9), (20.6, 76.9), (20.6, 35.0), (-16.5, 35.0), (-16.5, 28.5), (-52.5, 28.5), (-52.5, 35.5), (-55.5, 35.5)]
RAISED_Z = 28.97
# the beams' lines on the decks, as the scan's dark lines (u along the site; v up it): the columns on the 9 m grid
GRID = dict(north=dict(u=[-50.9, -41.7, -32.6, -23.6, -15.2, -6.2, 3.1, 11.9], v=[36.6, 43.7, 51.2, 57.3, 62.9, 68.9]),
            raised=dict(u=[-52.3, -43.3, -34.2, -25.2, -16.3, -7.2, 1.8, 10.8, 17.5, 29.7], v=[11.1, 16.8, 22.3, 30.4, 34.4, 40.5, 47.4,
                                                                                            52.7, 57.4, 64.9, 72.1]),
            south=dict(u=[-54.5, -42.8, -34.6, -24.8, -17.1, -9.8, 1.8, 10.7, 19.9, 29.8], v=[]),
            east=dict(u=[45.8], v=[6.7, 12.6, 17.4, 22.3, 28.9, 32.9, 39.5, 44.3, 49.9, 54.1, 63.5, 67.9, 72.1]))
# the steel deck (복공) over the pocket at the west end of the north side, at the ground's height, and its two openings
# framed in white rails (u0, u1, v0, v1)
BOKGONG = (-55.0, -28.0, 76.9, 84.3)
OPENINGS = [(-50.0, -42.5, 79.0, 82.5), (-41.0, -34.0, 79.0, 82.5)]
PILE = dict(every=1.82, w=0.3, proud=0.06, wale=(0.9,))             # (the wale's height under the top)


def deck_z(u, v):
    for _, (u0, u1, v0, v1), z in DECK_LEVELS:
        if u0 <= u <= u1 and v0 <= v <= v1:
            return z
    return DECK_LEVELS[-1][2]


def dig(Hn, X, Y, sample, step=5.0, half=800.0):
    """the pit (RIM) dug into the ground the game has laid round the site: every node of a cell the pit reaches goes
    down under the decks (FLOOR), the cells with such a node get a deck over all of them outside the pit on the ground
    as it was (build_campus.py dwb_deck, the ground's own material), as widang97.pit_grade.  Returns the nodes set, the
    cells, the deck's outline, its level (top: the ground before, working datum) and a summary"""
    H0 = Hn.copy()
    x0, y0, x1, y1 = RIM.bounds
    inner = RIM.buffer(-0.02)
    pit_cells = set()
    for j in range(int(math.floor((y0 + half) / step)) - 1, int(math.ceil((y1 + half) / step)) + 1):
        for i in range(int(math.floor((x0 + half) / step)) - 1, int(math.ceil((x1 + half) / step)) + 1):
            if box(-half + i * step, -half + j * step, -half + (i + 1) * step, -half + (j + 1) * step).intersects(inner):
                pit_cells.add((j, i))
    m = np.zeros(X.shape, bool)
    for j, i in pit_cells:
        m[j:j + 2, i:i + 2] = True
    Hn[m] = np.minimum(Hn[m], FLOOR + datum.tilt(X[m], Y[m]))
    jj, ii = np.nonzero(m)
    cells = {(j + a, i + b) for j, i in zip(jj, ii) for a in (-1, 0) for b in (-1, 0)}
    deck = unary_union([box(-half + i * step, -half + j * step, -half + (i + 1) * step, -half + (j + 1) * step)
                        for j, i in cells]).difference(RIM)

    def top(x, y):
        return sample(H0, half, step, x, y)
    dd = Hn - H0
    return m, cells, deck, top, dict(nodes=int(m.sum()), cells=len(cells), deck_m2=round(deck.area, 1), most=round(float(dd.min()), 2))


def walls(top, foot, step=1.82):
    """the dig's sides from the deck (foot) up to the ground beyond (top), facing in: timber lagging between H-piles
    1.82 m apart standing 6 cm proud of it, a wale along them (0.9 m under the top), a steel cap along the heads; the
    west side the slab's concrete edge.  [material, points] in the working datum; no guards (the hoarding is the site's collider)"""
    quads = []
    R = lambda q, z: [round(q[0], 3), round(q[1], 3), round(float(z), 3)]
    co = [xy(u, v) for u, v in RIM_UV] + [xy(*RIM_UV[0])]
    acc = 0.0
    for k_, ((xa, ya), (xb, yb)) in enumerate(zip(co, co[1:])):
        L = math.hypot(xb - xa, yb - ya)
        dx, dy = (xb - xa) / L, (yb - ya) / L
        nx, ny = -dy, dx                                  # (into the pit: the rim runs counter-clockwise)
        n = max(1, int(math.ceil(L / step)))
        S = [(xa + (xb - xa) * k / n, ya + (yb - ya) * k / n) for k in range(n + 1)]
        zt = [top(x - nx * 0.3, y - ny * 0.3) for x, y in S]
        zb = [foot(x + nx * 0.3, y + ny * 0.3) - 0.3 for x, y in S]
        west = abs(uv(xa, ya)[0] - WEST_U) < 0.1 and abs(uv(xb, yb)[0] - WEST_U) < 0.1
        for k in range(n):
            a, b = S[k], S[k + 1]
            quads.append(['concrete_dark' if west else 'wood_dark', [R(b, zb[k + 1]), R(a, zb[k]), R(a, zt[k]), R(b, zt[k + 1])]])
            if west:
                continue
            c0, c1 = (a[0] + nx * 0.02, a[1] + ny * 0.02), (b[0] + nx * 0.02, b[1] + ny * 0.02)
            i0, i1 = (a[0] - nx * 0.3, a[1] - ny * 0.3), (b[0] - nx * 0.3, b[1] - ny * 0.3)
            quads.append(['metal_dark', [R(c1, zt[k + 1] + 0.04), R(c0, zt[k] + 0.04), R(i0, zt[k] + 0.04), R(i1, zt[k + 1] + 0.04)]])
            quads.append(['metal_dark', [R(c1, zt[k + 1] - 0.3), R(c0, zt[k] - 0.3), R(c0, zt[k] + 0.04), R(c1, zt[k + 1] + 0.04)]])
            # the wales: an H-section along the piles' faces (its face and top)
            for dz in PILE['wale']:
                w0, w1 = (a[0] + nx * 0.36, a[1] + ny * 0.36), (b[0] + nx * 0.36, b[1] + ny * 0.36)
                za, zb_ = zt[k] - dz, zt[k + 1] - dz
                if za - 0.3 < zb[k] + 0.4:
                    continue
                quads.append(['metal_dark', [R(w1, zb_ - 0.15), R(w0, za - 0.15), R(w0, za + 0.15), R(w1, zb_ + 0.15)]])
                quads.append(['metal_dark', [R(w1, zb_ + 0.15), R(w0, za + 0.15), R(c0, za + 0.15), R(c1, zb_ + 0.15)]])
        if west:
            acc += L
            continue
        s = (PILE['every'] - acc % PILE['every']) % PILE['every']
        w, p = PILE['w'] / 2, PILE['proud']
        while s <= L:
            x, y = xa + dx * s, ya + dy * s
            z1 = top(x - nx * 0.3, y - ny * 0.3) - 0.02
            z0 = foot(x + nx * 0.3, y + ny * 0.3) - 0.3
            f0, f1 = (x - dx * w + nx * p, y - dy * w + ny * p), (x + dx * w + nx * p, y + dy * w + ny * p)
            b0, b1 = (x - dx * w, y - dy * w), (x + dx * w, y + dy * w)
            quads.append(['metal_dark', [R(f1, z0), R(f0, z0), R(f0, z1), R(f1, z1)]])
            quads.append(['metal_dark', [R(f0, z0), R(b0, z0), R(b0, z1), R(f0, z1)]])
            quads.append(['metal_dark', [R(b1, z0), R(f1, z0), R(f1, z1), R(b1, z1)]])
            s += PILE['every']
        acc += L
    return quads, []


def _ring(p):
    return [[round(x, 2), round(y, 2)] for x, y in list(p.exterior.coords)[:-1]]


def stuff_list():
    """the stuff on the decks read off the scan (tools/gongwon97_stuff.json, stuff() below): [u, v, L, W, deg, kind]"""
    f = os.path.join(ROOT, 'tools/gongwon97_stuff.json')
    return json.load(open(f))['piles'] if os.path.exists(f) else []


def pieces(up):
    """what blender/landmarks.py gongwon_site draws in the pit (working datum: up(x, y, z) takes a height 해발 up):
    decks: [{ring, z, kind, u, v}] the deck's pieces at their levels cut to the rim, the slab on its shoring, the
    beams' lines (u, v of the site's frame); bokgong: {ring, holes, z: None (the ground's: build_campus)}; stuff:
    [x, y, z, L, W, ang, h, kind]"""
    raised = poly(RAISED_UV).intersection(RIM)
    decks, taken = [], raised
    for name, (u0, u1, v0, v1), z in DECK_LEVELS:
        p = poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)]).intersection(RIM).difference(taken)
        taken = taken.union(p)
        for g in getattr(p, 'geoms', [p]):
            if g.geom_type == 'Polygon' and g.area > 1.0:
                c = g.centroid
                gr = GRID.get(name, dict(u=[], v=[]))
                decks.append(dict(ring=_ring(g), z=round(float(up(c.x, c.y, z)), 3), kind='deck', u=gr['u'], v=gr['v']))
    for g in getattr(raised, 'geoms', [raised]):
        c = g.centroid
        # (under it: its shoring's props in two rows along its open edges, 1.2 m apart, and the dark of the rest)
        props = []
        for off in (0.5, 1.7):
            r = g.buffer(-off, join_style=2)
            for e in getattr(r, 'geoms', [r]):
                if e.geom_type != 'Polygon':
                    continue
                ln = e.exterior
                for t in np.arange(0.0, ln.length, 1.2):
                    q = ln.interpolate(t)
                    if RIM.buffer(-0.8).contains(q):
                        props.append([round(q.x, 2), round(q.y, 2)])
        inner = g.buffer(-2.3, join_style=2)
        decks.append(dict(ring=_ring(g), z=round(float(up(c.x, c.y, RAISED_Z)), 3), kind='raised', u=GRID['raised']['u'],
                          v=GRID['raised']['v'], floor=round(float(up(c.x, c.y, DECK_LEVELS[-1][2])), 3), props=props,
                          inner=[_ring(e) for e in getattr(inner, 'geoms', [inner]) if e.geom_type == 'Polygon' and e.area > 1.0]))
    st = []
    rp = poly(RAISED_UV)
    bk = poly([(BOKGONG[0], BOKGONG[2]), (BOKGONG[1], BOKGONG[2]), (BOKGONG[1], BOKGONG[3]), (BOKGONG[0], BOKGONG[3])])
    inner = RIM.buffer(-1.0)
    for u, v, L, W, deg, kind in stuff_list():
        x, y = xy(u, v)
        P = shapely.Point(x, y)
        if not inner.contains(P) or bk.buffer(0.5).contains(P):
            continue
        z = RAISED_Z if rp.contains(P) else deck_z(u, v)
        h = dict(rebar=0.35, lumber=0.45).get(kind, min(1.2, max(0.4, 0.25 + 0.1 * L * W)))
        st.append([round(x, 2), round(y, 2), round(float(up(x, y, z)), 3), round(L, 2), round(W, 2), round(math.radians(deg) + ROT, 4),
                   round(h, 2), kind])
    return dict(decks=decks, stuff=st,
                bokgong=dict(ring=_ring(bk), holes=[_ring(poly([(a, c), (b, c), (b, d), (a, d)])) for a, b, c, d in OPENINGS]))


# ---------------------------------------------------------------- reading the stuff off the scan
def _zplane(u, v):
    return RAISED_Z if poly(RAISED_UV).contains(shapely.Point(*xy(u, v))) else deck_z(u, v)


def stuff(frame='26/16', res=0.1):
    """the stuff on the decks: the scan resampled on the decks' planes (26/16, 200 m from its camera: a metre of height
    moves a thing 0.1 - 0.25 m), less its own median over 3 m; the dark and bright blobs off the beams' lines (long
    runs along u or v taken out), 0.5 - 30 m2, filled at least 40 %, 0.9 - 10 m long, not on the tower crane (its jib
    and mast cross the decks in this frame).  Elongated and dark: rebar bundles; elongated and bright: lumber; the rest
    stacks of forms (dark) or of boards (bright)"""
    from scipy import ndimage as ndi
    import aerial97 as A
    U0, U1, V0, V1 = -56.0, 54.0, -5.0, 85.0
    us = U0 + np.arange(int((U1 - U0) / res) + 1) * res
    vs = V1 - np.arange(int((V1 - V0) / res) + 1) * res
    UU, VV = np.meshgrid(us, vs)
    XX, YY = O[0] + UU * _C - VV * _S, O[1] + UU * _S + VV * _C
    Z = np.vectorize(_zplane)(UU, VV)
    p = A.to_px(tuple(int(t) for t in frame.split('/')), XX, YY, Z)
    im = A.sample(tuple(int(t) for t in frame.split('/')), p[..., 0], p[..., 1])
    d = im - ndi.median_filter(im, size=31)
    dark, bright = d < -22, d > 30
    lines = ndi.binary_opening(dark, structure=np.ones((1, 61))) | ndi.binary_opening(dark, structure=np.ones((61, 1)))
    lines |= ndi.binary_opening(bright, structure=np.ones((1, 81))) | ndi.binary_opening(bright, structure=np.ones((81, 1)))
    obj = ndi.binary_opening(ndi.binary_closing((dark | bright) & ~ndi.binary_dilation(lines, iterations=2), iterations=2), iterations=1)
    # the crane in this frame: the mast from the deck up and the jib at its height, on the decks' planes
    fr = tuple(int(t) for t in frame.split('/'))
    cx, cy, H, brg, jib = -258.0, -337.3, 48.7, 140.0, 50.0
    crane = []
    a = math.radians(90.0 - brg)
    for t in np.arange(-12.0, jib + 0.1, 0.5):
        crane.append((cx + t * math.cos(a), cy + t * math.sin(a), H))
    for z in np.arange(25.0, H, 0.5):
        crane.append((cx, cy, z))
    cuv = []
    for q in crane:
        px, py = A.to_px(fr, *q)
        g = A.to_game(fr, px, py, 25.0)
        cuv.append(uv(g[0], g[1]))
    cuv = np.array(cuv)
    lab, _ = ndi.label(obj)
    out = []
    for k, sl in enumerate(ndi.find_objects(lab)):
        mk = lab[sl] == k + 1
        area = mk.sum() * res * res
        if area < 0.5 or area > 30:
            continue
        yy, xx = np.nonzero(mk)
        pu, pv = U0 + (xx + sl[1].start) * res, V1 - (yy + sl[0].start) * res
        mu, mv = pu.mean(), pv.mean()
        w, e = np.linalg.eigh(np.cov(np.vstack([pu - mu, pv - mv])))
        L, W = 2 * math.sqrt(3 * max(w[1], 1e-6)), 2 * math.sqrt(3 * max(w[0], 1e-6))
        if W < 0.25 or L > 10 or L < 0.9 or area / (L * W) < 0.4:
            continue
        if np.min(np.hypot(cuv[:, 0] - mu, cuv[:, 1] - mv)) < 1.5 or not RIM.buffer(-0.5).contains(shapely.Point(*xy(mu, mv))):
            continue
        tone = float(np.median(d[sl][mk]))
        kind = ('rebar' if tone < 0 else 'lumber') if L / W >= 3.5 else ('stack' if tone < 0 else 'boards')
        out.append([round(float(mu), 2), round(float(mv), 2), round(L, 2), round(W, 2),
                    round(math.degrees(math.atan2(e[1, 1], e[0, 1])), 1), kind])
    return out


if __name__ == '__main__':
    if sys.argv[1:2] == ['stuff']:
        P = stuff()
        with open(os.path.join(ROOT, 'tools/gongwon97_stuff.json'), 'w') as f:
            f.write('{"source": "1997-07-28 26/16 원본 스캔 (tools/gongwon97.py stuff)", "fields": "u, v, L, W, deg (site frame), kind",\n'
                    ' "piles": [\n' + ',\n'.join('  ' + json.dumps(q, ensure_ascii=False) for q in P) + '\n]}\n')
        from collections import Counter
        print(len(P), 'piles', Counter(p[5] for p in P))
