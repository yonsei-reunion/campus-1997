"""1997 백양로 (reference/1997_백양로_항공사진.jpg aerial photo): two-lane asphalt road without a median, raised boxwood
verges, wide paver sidewalks, an outer planting strip for the ginkgo row, lane paint, zebra crossings and the
painted speed bump inside the gate."""
import math
import numpy as np
from mathutils import Vector
from common import MeshBuilder, CAMPUS


def smooth_line(pts, step=2.0, iters=3):
    P = [Vector((x, y)) for x, y in pts]
    for _ in range(iters):           # Chaikin, keep endpoints
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            Q += [a.lerp(b, 0.25), a.lerp(b, 0.75)]
        Q.append(P[-1])
        P = Q
    # resample uniformly
    seg = [(P[i + 1] - P[i]).length for i in range(len(P) - 1)]
    total = sum(seg)
    out = []
    s = 0.0
    i, acc = 0, 0.0
    while s <= total:
        while i < len(seg) - 1 and acc + seg[i] < s:
            acc += seg[i]
            i += 1
        t = (s - acc) / seg[i] if seg[i] > 0 else 0
        out.append((s, P[i].lerp(P[i + 1], min(1, t))))
        s += step
    return out


def build():
    R = CAMPUS['baekyangro']
    ps, ph = np.array(R['profile_s']), np.array(R['profile_h'])
    # the profile was computed on the raw polyline; arc length is close enough after smoothing
    samples = smooth_line(R['pts'])
    med, lane, curb = R['median'], R['lane'], R['curb']
    verge, walk, strip = R.get('verge', 0.0), R['walk'], R.get('strip', 0.0)
    e_lane = med + lane
    e_curb = e_lane + curb
    e_verge = e_curb + verge
    e_walk = e_verge + walk
    e_strip = e_walk + strip
    # verge planter top, sidewalk top (above the asphalt): the kerbs stood some 15 - 18 cm over the carriageway (the 1997
    # photo, the 2010 / 2011 roadview before the rebuilding: the verge's soil level with its kerbs, a low lip on the
    # sidewalk side); a 32 cm planter wall before
    VZ, WZ = 0.18, 0.15
    # the granite kerbs: their own material, whose shader draws a joint every metre of u (web/src/kerbjoints.js; the
    # 2010 / 2011 roadview: stones about 1 m long), u running along the road
    KERB = 'curb_road'
    mb = MeshBuilder('baekyangro')
    marks = MeshBuilder('baekyangro_paint')
    L = samples[-1][0]
    crossings = list(R.get('crossings', []))
    gaps = R.get('gaps', [])
    bump = R.get('bump')
    # side-road mouths: on that side the verge, sidewalk and planting strip stop between s0 and s1 and the asphalt
    # runs flush out to the terrain; their corners at the carriageway are rounded (radius r0 / r1).  An optional sixth
    # value: the boxwood verge stops that much short of the north end, with a round end, the sidewalk paved out to
    # the carriageway's kerb in front of it (the gate's side road, 1997 photo)
    mouths = [tuple(m) + (0.0,) * (6 - len(m)) for m in R.get('mouths', [])]
    frames = []
    for k, (s, p) in enumerate(samples):
        q0 = samples[max(0, k - 1)][1]
        q1 = samples[min(len(samples) - 1, k + 1)][1]
        t = (q1 - q0).normalized()
        n = Vector((-t.y, t.x))          # left normal
        h = float(np.interp(s, ps, ph))
        frames.append((s, p, t, n, h))

    def pt(f, off, dz):
        s, p, t, n, h = f
        q = p + n * off
        return (q.x, q.y, h + dz)

    def in_cross(s, pad=0.0):
        return any(abs(s - c) < 3.0 + pad for c in crossings)

    def in_gap(s, side):
        return any(sd == side and abs(s - g) < hw for g, sd, hw in gaps)

    def fillet(o, r):
        # how far the corner of radius r cuts back along the road at offset o
        u = o - e_lane
        return r - math.sqrt(max(0.0, r * r - (r - u) ** 2)) if 0 <= u < r else (r if u < 0 else 0.0)

    def cut(m, o, verge=False):
        # the stretch [lo, hi] of road (arc length) where nothing stands at offset o (verge: where no boxwood stands)
        sd, s0, s1, r0, r1, vb = m
        hi = s1 + fillet(o, r1)
        if verge and vb > 0:
            half = (e_verge - e_lane) / 2
            u = min(1.0, abs(o - (e_lane + half)) / half)
            hi = s1 + vb + half * (1 - math.sqrt(max(0.0, 1 - u * u)))
        return s0 - fillet(o, r0), hi

    def mouth_at(sa, sb, side):
        for m in mouths:
            if m[0] == side and sb > m[1] - m[3] - 0.01 and sa < m[2] + m[4] + m[5] + 1.1:
                return m
        return None

    def mouth_segment(a, b, side, m):
        """one 2 m step of the road beside a mouth: every band of the cross-section clipped to where it stands"""
        sa, sb = a[0], b[0]
        sgn = side

        def P(s, off, dz):
            t = (s - sa) / (sb - sa)
            q = a[1].lerp(b[1], t) + a[3].lerp(b[3], t) * (off * sgn)
            return (q.x, q.y, a[4] + (b[4] - a[4]) * t + dz)

        def quad(q):
            mb.face(q if side > 0 else [q[1], q[0], q[3], q[2]], q_mat[0])

        q_mat = [None]
        # (o0, o1, z, mat) bands standing beside the road, as in the plain cross-section
        bands = [(e_lane, e_curb, VZ, 'curb'), (e_curb, e_verge - 0.2, VZ, 'dirt'), (e_verge - 0.2, e_verge, VZ, 'curb'),
                 (e_verge, e_walk, WZ, 'pavers'), (e_walk, e_walk + 0.18, WZ + 0.05, 'curb'), (e_walk + 0.18, e_strip, WZ, 'dirt')]
        for o0, o1, z, mat in bands:
            k = max(1, int(math.ceil((o1 - o0) / 0.4)))
            vg = o1 <= e_verge + 1e-6                     # a band of the boxwood verge
            for i in range(k):
                p0, p1 = o0 + (o1 - o0) * i / k, o0 + (o1 - o0) * (i + 1) / k
                (l0, h0), (l1, h1) = cut(m, p0, vg), cut(m, p1, vg)
                if vg and m[5] > 0:
                    # in front of the verge's end the sidewalk's paving, out to the carriageway, its kerb facing the mouth
                    (_, f0), (_, f1) = cut(m, p0), cut(m, p1)
                    u0, v0, u1, v1 = max(sa, f0), min(sb, h0), max(sa, f1), min(sb, h1)
                    if v0 - u0 > 1e-4 or v1 - u1 > 1e-4:
                        v0, v1 = max(u0, v0), max(u1, v1)
                        q_mat[0] = 'pavers'
                        quad([P(u0, p0, WZ), P(v0, p0, WZ), P(v1, p1, WZ), P(u1, p1, WZ)])
                        if sa < u0 < sb or sa < u1 < sb:
                            q_mat[0] = KERB
                            f = [P(u0, p0, 0), P(u1, p1, 0), P(u1, p1, WZ), P(u0, p0, WZ)]
                            quad([f[1], f[0], f[3], f[2]])
                for (u0, v0), (u1, v1), edge in (((sa, min(sb, l0)), (sa, min(sb, l1)), 'end'),
                                                 ((max(sa, h0), sb), (max(sa, h1), sb), 'start')):
                    if u0 >= v0 - 1e-4 and u1 >= v1 - 1e-4:
                        continue
                    v0, v1 = max(u0, v0), max(u1, v1)
                    q_mat[0] = mat
                    quad([P(u0, p0, z), P(v0, p0, z), P(v1, p1, z), P(u1, p1, z)])
                    # the kerb face where the band stops, towards the mouth
                    e0, e1 = (v0, v1) if edge == 'end' else (u0, u1)
                    if sa < e0 < sb or sa < e1 < sb:
                        q_mat[0] = KERB
                        f = [P(e0, p0, 0), P(e1, p1, 0), P(e1, p1, z), P(e0, p0, z)]
                        quad(f if edge == 'end' else [f[1], f[0], f[3], f[2]])
        # kerbs along the road (carriageway edge, verge, strip edges), where they stand; f faces the centre line
        for off, z0_, z1_, outward in ((e_lane, 0, VZ, False), (e_verge, WZ, VZ, True), (e_walk, WZ, WZ + 0.05, False),
                                       (e_strip, -0.8, WZ, True)):
            lo, hi = cut(m, off, off <= e_verge + 1e-6)
            for u, v in ((sa, min(sb, lo)), (max(sa, hi), sb)):
                if v - u > 1e-3:
                    q_mat[0] = KERB
                    f = [P(u, off, z0_), P(v, off, z0_), P(v, off, z1_), P(u, off, z1_)]
                    quad([f[1], f[0], f[3], f[2]] if outward else f)
            if off == e_lane and m[5] > 0:
                # the low kerb of the paving in front of the verge's end
                u, v = max(sa, cut(m, off)[1]), min(sb, hi)
                if v - u > 1e-3:
                    q_mat[0] = KERB
                    quad([P(u, off, 0), P(v, off, 0), P(v, off, WZ), P(u, off, WZ)])
        # the flush asphalt of the mouth, out past the strip onto the terrain's own asphalt, with a skirt beneath
        k = int(math.ceil((e_strip + 0.6 - e_lane) / 0.4))
        for i in range(k):
            p0, p1 = e_lane + (e_strip + 0.6 - e_lane) * i / k, e_lane + (e_strip + 0.6 - e_lane) * (i + 1) / k
            (l0, h0), (l1, h1) = cut(m, p0), cut(m, p1)
            u0, v0, u1, v1 = max(sa, l0), min(sb, h0), max(sa, l1), min(sb, h1)
            if v0 - u0 < 1e-4 and v1 - u1 < 1e-4:
                continue
            v0, v1 = max(u0, v0), max(u1, v1)
            q_mat[0] = 'asphalt'
            quad([P(u0, p0, 0), P(v0, p0, 0), P(v1, p1, 0), P(u1, p1, 0)])
        lo, hi = cut(m, e_strip + 0.6)
        u, v = max(sa, lo), min(sb, hi)
        if v - u > 1e-3:
            q_mat[0] = 'asphalt'
            f = [P(u, e_strip + 0.6, -0.8), P(v, e_strip + 0.6, -0.8), P(v, e_strip + 0.6, 0), P(u, e_strip + 0.6, 0)]
            quad([f[1], f[0], f[3], f[2]])

    for a, b in zip(frames[:-1], frames[1:]):
        sm = (a[0] + b[0]) / 2
        cross = in_cross(sm)
        for side in (-1, 1):
            o = lambda v: v * side
            flip = side < 0
            m_ = mouth_at(a[0], b[0], side)
            if m_ is not None:
                mb.face([pt(a, o(0), 0), pt(b, o(0), 0), pt(b, o(e_lane), 0), pt(a, o(e_lane), 0)] if not flip else
                        [pt(b, o(0), 0), pt(a, o(0), 0), pt(a, o(e_lane), 0), pt(b, o(e_lane), 0)], 'asphalt')
                mouth_segment(a, b, side, m_)
                continue

            def at_s(s, off, dz):
                # a point of the cross-section between frames a and b, at arc length s
                t = (s - a[0]) / (b[0] - a[0])
                q = a[1].lerp(b[1], t) + a[3].lerp(b[3], t) * off
                return (q.x, q.y, a[4] + (b[4] - a[4]) * t + dz)

            def band(o0, o1, z0, z1, mat, rng=None):
                u, v = rng or (a[0], b[0])
                q = [at_s(u, o(o0), z0), at_s(v, o(o0), z0), at_s(v, o(o1), z1), at_s(u, o(o1), z1)]
                # the kerbs' stones: u = metres along the road (a joint every metre, web/src/kerbjoints.js)
                uv = [(u, o0), (v, o0), (v, o1), (u, o1)]
                if flip:
                    q, uv = [q[1], q[0], q[3], q[2]], [uv[1], uv[0], uv[3], uv[2]]
                mb.face(q, KERB if mat == 'curb' else mat, uvs=uv if mat == 'curb' else None)

            def riser(off, z0, z1, mat, outward=True, rng=None):
                # vertical face along the road at offset `off`; outward=True faces away from the centre line
                u, v = rng or (a[0], b[0])
                q = [at_s(u, o(off), z0), at_s(v, o(off), z0), at_s(v, o(off), z1), at_s(u, o(off), z1)]
                uv = [(u, z0), (v, z0), (v, z1), (u, z1)]
                if outward != flip:
                    q, uv = [q[1], q[0], q[3], q[2]], [uv[1], uv[0], uv[3], uv[2]]
                mb.face(q, KERB if mat == 'curb' else mat, uvs=uv if mat == 'curb' else None)

            if med > 0:
                band(0, med, 0, 0, 'asphalt')
            band(med, e_lane, 0, 0, 'asphalt')
            if cross or in_gap(sm, side):
                # pedestrian crossing / side-road entrance: the verge is paved flush with the sidewalk
                riser(e_lane, 0, WZ, 'curb', outward=False)
                band(e_lane, e_verge, WZ, WZ, 'pavers')
            else:
                # granite curb, then the raised boxwood verge with its own kerb
                riser(e_lane, 0, VZ, 'curb', outward=False)
                band(e_lane, e_curb, VZ, VZ, 'curb')
                band(e_curb, e_verge - 0.2, VZ, VZ, 'dirt')
                band(e_verge - 0.2, e_verge, VZ, VZ, 'curb')
                riser(e_verge, WZ, VZ, 'curb', outward=True)
            band(e_verge, e_walk, WZ, WZ, 'pavers')
            # outer planting strip (ginkgo + hedge), then a skirt down to the terrain
            band(e_walk, e_walk + 0.18, WZ + 0.05, WZ + 0.05, 'curb')
            riser(e_walk, WZ, WZ + 0.05, 'curb', outward=False)
            band(e_walk + 0.18, e_strip, WZ, WZ, 'dirt')
            riser(e_strip, -0.8, WZ, 'curb', outward=True)

    # paint ---------------------------------------------------------------
    def strip_(s0, s1, off, width, mat, dz=0.012):
        fa = min(frames, key=lambda f: abs(f[0] - s0))
        fb = min(frames, key=lambda f: abs(f[0] - s1))
        if fa is fb:
            return
        q = [pt(fa, off - width / 2, dz), pt(fb, off - width / 2, dz), pt(fb, off + width / 2, dz), pt(fa, off + width / 2, dz)]
        marks.face(q, mat)

    def at(s):
        return min(frames, key=lambda f: abs(f[0] - s))

    def blank(s, pad):
        return in_cross(s, pad) or (bump is not None and abs(s - bump) < 2.5 + pad)
    # white dashed centre line, solid yellow edge lines along both curbs
    s = 6.0
    while s < L - 6:
        if not blank(s, 2) and not blank(s + 3, 2):
            strip_(s, s + 3.0, 0.0, 0.15, 'paint_white')
        s += 8.0
    for side in (-1, 1):
        s = 4.0
        while s < L - 4:
            if not blank(s, 1.5) and not in_gap(s, side):
                strip_(s, s + 2.0, side * (e_lane - 0.35), 0.15, 'paint_yellow')
            s += 2.0

    def quad_at(f, o0, o1, t0, t1, mat):
        s, p, t, n, h = f
        q0 = p + n * o0 + t * t0
        q1 = p + n * o1 + t * t0
        q2 = p + n * o1 + t * t1
        q3 = p + n * o0 + t * t1
        marks.face([(q0.x, q0.y, h + 0.012), (q3.x, q3.y, h + 0.012), (q2.x, q2.y, h + 0.012), (q1.x, q1.y, h + 0.012)], mat)

    # zebra crossings + stop lines
    for c in crossings:
        f = at(c)
        o = -e_lane + 0.5
        while o < e_lane - 0.4:
            quad_at(f, o, o + 0.5, -2.0, 2.0, 'paint_white')
            o += 1.0
        for side in (-1, 1):
            fb = at(c - side * 4.5)
            o0, o1 = (0.0, e_lane) if side > 0 else (-e_lane, 0.0)
            quad_at(fb, o0, o1, -0.2, 0.2, 'paint_white')
    def hump(f, o0, o1, mat, half=0.9, flat=0.5, rise=0.09):
        # a real raised bump: flat top with sloping sides (a 9 cm rise over 1.8 m), stripes painted on it
        s, p, t, n, h = f
        P = lambda o, d, z: (lambda q: (q.x, q.y, h + z))(p + n * o + t * d)
        prof = [(-half, 0.012), (-flat, rise), (flat, rise), (half, 0.012)]
        for (d0, z0), (d1, z1) in zip(prof, prof[1:]):
            marks.face([P(o0, d0, z0), P(o0, d1, z1), P(o1, d1, z1), P(o1, d0, z0)], mat)
    # speed bump near the gate, raised, with alternating yellow / white blocks across the road (1997 photo)
    if bump is not None:
        f = at(bump)
        o, k = -e_lane, 0
        while o < e_lane - 0.01:
            hump(f, o, min(e_lane, o + 0.9), 'paint_yellow' if k % 2 else 'paint_white')
            o += 0.9
            k += 1
        # ◇ "crossing ahead" diamonds and lane arrows beyond the bump
        for side in (-1, 1):
            s0, p0, t0, n0, h0 = at(bump + (26 if side > 0 else 40))
            c0 = p0 + n0 * (-side * lane * 0.5)
            dia = [c0 - t0 * 1.6, c0 + n0 * 0.9, c0 + t0 * 1.6, c0 - n0 * 0.9]
            inner = [c0 - t0 * 1.3, c0 + n0 * 0.65, c0 + t0 * 1.3, c0 - n0 * 0.65]
            for i in range(4):
                a0, a1, b1, b0 = dia[i], dia[(i + 1) % 4], inner[(i + 1) % 4], inner[i]
                marks.face([(v.x, v.y, h0 + 0.012) for v in (b0, b1, a1, a0)], 'paint_white')
    # lane paint on the asphalt apron the side road opens into (draped on the terrain heights from build_campus)
    for ln in R.get('apron_paint', []):
        pts = [Vector(p) for p in ln['pts']]
        dash = ln['kind'].endswith('_dash')
        acc = 0.0
        for p, q in zip(pts[:-1], pts[1:]):
            d = (q - p)
            seg = d.xy.length
            mid = acc + seg / 2
            acc += seg
            if dash and (mid % 6.5) > 2.5:          # 2.5 m dashes, 4 m apart
                continue
            n = Vector((-d.y, d.x, 0)).normalized() * 0.075
            marks.face([tuple(p - n + Vector((0, 0, 0.05))), tuple(q - n + Vector((0, 0, 0.05))),
                        tuple(q + n + Vector((0, 0, 0.05))), tuple(p + n + Vector((0, 0, 0.05)))], 'paint_yellow')
    return [mb, marks], crossings
