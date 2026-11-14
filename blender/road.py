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
    # the lawn between the kerbs of the verge and of the outer planting strip (the 2008 / 2010 roadview, the 1997
    # photo): drawn in the web app with the terrain's own lawn, its blades and bare patches (web/src/verge.js)
    LAWN = 'verge_lawn'
    # the concrete gutter between the asphalt and the kerb's face (the 2008 / 2010 roadview: 0.3 m, a cross joint every
    # 1 - 2 m; reference/고증.md 2.3): the lane's last GUT m, its own material with a joint every 1.5 m of u
    # (web/src/kerbjoints.js), level with the asphalt (not falling to the kerb: the terrain lies level with the
    # asphalt under the road and would cover anything lower).  The yellow edge line, 12 cm, on the asphalt 6 cm inside
    # its edge
    GUT = R.get('gutter', 0.0)
    GUTTER = 'gutter_road'
    e_gut = e_lane - GUT
    YW, YGAP = 0.12, 0.06
    e_yel = e_gut - YGAP - YW / 2
    # where the verge breaks (crossings, side-road gaps, the openings of campus.json baekyangro breaks) its ends are
    # round, half circles of the verge's width with the kerb running round them (radius RV about the verge's middle VC;
    # the soil's half circle RD about DC inside the kerb's ring), the gutter following round to the tip; between them
    # a ramp from the gutter up to the sidewalk (the roadview: the openings at the carriageway's level)
    RV, VC = (e_verge - e_lane) / 2, (e_lane + e_verge) / 2
    RD, DC = (e_verge - 0.2 - e_curb) / 2, (e_curb + e_verge - 0.2) / 2
    walls = R.get('walls', [])          # [side, s0, s1]: no planting strip there (a retaining wall, landmarks.aud_bank)
    # [side, s0, s1]: no planting strip either, the ground beyond comes up to the sidewalk, which gets a kerb there
    # (the forecourt before 제1공학관's door)
    sbreaks = R.get('strip_breaks', [])
    mb = MeshBuilder('baekyangro')
    marks = MeshBuilder('baekyangro_paint')
    L = samples[-1][0]
    crossings = list(R.get('crossings', []))
    # the zebras' depth along the road (the July 1997 scans: about 2 m; 4 m before), the stop lines 2.5 m out from them
    CL = float(R.get('cross_len', 4.0))
    STOP = CL / 2 + 2.5
    gaps = R.get('gaps', [])
    bump = R.get('bump')
    # side-road mouths: on that side the verge, sidewalk and planting strip stop between s0 and s1 and the asphalt
    # runs flush out to the terrain; their corners at the carriageway are rounded (radius r0 / r1).  An optional sixth
    # value: the boxwood verge stops that much short of the north end, with a round end, the sidewalk paved out to
    # the carriageway's kerb in front of it (the gate's side road, 1997 photo)
    mouths = [tuple(m) + (0.0,) * (6 - len(m)) for m in R.get('mouths', [])]
    # the openings in the verge on each side, [s0, s1, turn] (turn: a side road's, the yellow line turns in round the
    # verge's end); those closer than two round ends merged
    vbreaks = {}
    for side in (-1, 1):
        lst = [[c - 3.0, c + 3.0, False] for c in crossings] + [[g - hw, g + hw, True] for g, sd, hw in gaps if sd == side] \
            + [[s0, s1, False] for sd, s0, s1 in R.get('breaks', []) if sd == side]
        lst.sort()
        out_ = []
        for br in lst:
            if out_ and br[0] < out_[-1][1] + 2 * RV + 0.3:
                out_[-1][1] = max(out_[-1][1], br[1])
                out_[-1][2] = out_[-1][2] or br[2]
            else:
                out_.append(list(br))
        vbreaks[side] = out_
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

    def at_so(s, off, dz=0.0):
        # the point at arc length s, signed offset off (+ west), dz over the road's height there
        k = max(0, min(len(frames) - 2, int(s // 2.0)))
        fa, fb = frames[k], frames[k + 1]
        t = (s - fa[0]) / (fb[0] - fa[0])
        q = fa[1].lerp(fb[1], t) + fa[3].lerp(fb[3], t) * off
        return (q.x, q.y, fa[4] + (fb[4] - fa[4]) * t + dz)

    def break_at(sa, sb, side):
        # the openings whose round ends reach into [sa, sb] (several where the verge is cut into short islands, the
        # forecourt of 학생회관), south to north
        return [br for br in vbreaks[side] if br[0] - RV - 0.5 < sb and br[1] + RV + 0.5 > sa] or None

    def ramp(o):
        # the opening's ramp from the kerb line up to the sidewalk
        return WZ * (o - e_lane) / (e_verge - e_lane)

    def break_segment(a, b, side, brs):
        """one 2 m step of the road beside openings in the verge (brs, south to north), from the gutter out to the
        sidewalk: the gutter, the verge's round kerbed ends, the gutter round them, the ramp between"""
        sa, sb = a[0], b[0]
        INF = 1e6

        def P(s, off, dz):
            t = (s - sa) / (sb - sa)
            q = a[1].lerp(b[1], t) + a[3].lerp(b[3], t) * (off * side)
            return (q.x, q.y, a[4] + (b[4] - a[4]) * t + dz)

        def quad(q, mat, uv=None):
            if side < 0:
                q = [q[1], q[0], q[3], q[2]]
                uv = [uv[1], uv[0], uv[3], uv[2]] if uv else None
            mb.face(q, mat, uvs=uv)

        def circ(r, c, o):
            return math.sqrt(max(0.0, r * r - (o - c) ** 2))

        def pieces(o, kind):
            """[(from, to, mat, z)] along the road at offset o, from the south verge piece to the north one; kind: the
            strip's band ('road': the carriageway's gutter strip, 'soil': the verge's soil, 'kerb': its kerbs).  Per
            opening six pieces (the verge before it, its kerb, gutter, ramp, gutter, kerb), then the last verge piece"""
            out, prev = [], -INF
            if kind == 'road':
                g = circ(RV + GUT, VC, o)
                for s0, s1, _ in brs:
                    out += [(prev, s0 - RV + g, GUTTER, 0.0), (s0 - RV + g, s1 + RV - g, 'asphalt', 0.0)]
                    prev = s1 + RV - g
                return out + [(prev, INF, GUTTER, 0.0)]
            v = circ(RV, VC, o)
            g = circ(RV + GUT, VC, o) if o <= VC else v
            d = circ(RD, DC, o) if kind == 'soil' else v
            z = ramp(o)
            top = LAWN if kind == 'soil' else 'curb'
            for s0, s1, _ in brs:
                out += [(prev, s0 - RV + d, top, VZ), (s0 - RV + d, s0 - RV + v, 'curb', VZ),
                        (s0 - RV + v, s0 - RV + g, GUTTER, z + 0.004), (s0 - RV + g, s1 + RV - g, 'pavers', z),
                        (s1 + RV - g, s1 + RV - v, GUTTER, z + 0.004), (s1 + RV - v, s1 + RV - d, 'curb', VZ)]
                prev = s1 + RV - d
            return out + [(prev, INF, top, VZ)]

        cuts = [(e_gut, e_lane, 3, 'road'), (e_lane, e_curb, 2, 'kerb'), (e_curb, e_verge - 0.2, 12, 'soil'),
                (e_verge - 0.2, e_verge, 2, 'kerb')]
        for o0, o1, k, kind in cuts:
            for i in range(k):
                p0, p1 = o0 + (o1 - o0) * i / k, o0 + (o1 - o0) * (i + 1) / k
                A, B = pieces(p0, kind), pieces(p1, kind)
                for (u0, v0, mat, z0), (u1, v1, _, z1) in zip(A, B):
                    u0, v0, u1, v1 = max(sa, u0), min(sb, v0), max(sa, u1), min(sb, v1)
                    if v0 - u0 < 1e-4 and v1 - u1 < 1e-4:
                        continue
                    v0, v1 = max(u0, v0), max(u1, v1)
                    uv = [(u0, p0), (v0, p0), (v1, p1), (u1, p1)] if mat in ('curb', GUTTER) else None
                    quad([P(u0, p0, z0), P(v0, p0, z0), P(v1, p1, z1), P(u1, p1, z1)], KERB if mat == 'curb' else mat, uv)
                if kind == 'road':
                    continue
                # the kerb's face round the verge's ends, from the ramp up to the verge's top
                ends = []
                for j in range(len(brs)):
                    ends += [(A[6 * j + 1][1], B[6 * j + 1][1], True), (A[6 * j + 5][0], B[6 * j + 5][0], False)]
                for e0, e1, end in ends:
                    if not (sa < e0 < sb or sa < e1 < sb):
                        continue
                    e0, e1 = min(max(e0, sa), sb), min(max(e1, sa), sb)
                    f = [P(e0, p0, ramp(p0)), P(e1, p1, ramp(p1)), P(e1, p1, VZ), P(e0, p0, VZ)]
                    uv = [(e0, ramp(p0)), (e1, ramp(p1)), (e1, VZ), (e0, VZ)]
                    quad(f if end else [f[1], f[0], f[3], f[2]], KERB, uv if end else [uv[1], uv[0], uv[3], uv[2]])
        # the kerbs' faces along the road where the verge stands: to the carriageway, and the low lip to the sidewalk
        stands, prev = [], sa
        for s0, s1, _ in brs:
            stands.append((prev, min(sb, s0 - RV)))
            prev = max(prev, s1 + RV)
        stands.append((max(sa, prev), sb))
        for off, z0_, z1_, inward in ((e_lane, 0.0, VZ, True), (e_verge, WZ, VZ, False)):
            for u, v in stands:
                if v - u > 1e-3:
                    f = [P(u, off, z0_), P(v, off, z0_), P(v, off, z1_), P(u, off, z1_)]
                    uv = [(u, z0_), (v, z0_), (v, z1_), (u, z1_)]
                    quad(f if inward else [f[1], f[0], f[3], f[2]], KERB, uv if inward else [uv[1], uv[0], uv[3], uv[2]])

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
        bands = [(e_lane, e_curb, VZ, 'curb'), (e_curb, e_verge - 0.2, VZ, LAWN), (e_verge - 0.2, e_verge, VZ, 'curb'),
                 (e_verge, e_walk, WZ, 'pavers'), (e_walk, e_walk + 0.18, WZ + 0.05, 'curb'), (e_walk + 0.18, e_strip, WZ, LAWN)]
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

    def strip_pieces(sa, sb, side, walls=walls):
        # the stretches of [sa, sb] where the outer planting strip stands: not where the bank behind a retaining wall
        # rises from the sidewalk's edge (campus.json baekyangro walls, blender/landmarks.py aud_bank)
        out = [(sa, sb)]
        for sd, w0, w1 in walls:
            if sd != side:
                continue
            nxt = []
            for u, v in out:
                if w1 <= u or w0 >= v:
                    nxt.append((u, v))
                    continue
                if w0 > u:
                    nxt.append((u, w0))
                if w1 < v:
                    nxt.append((w1, v))
            out = nxt
        return [(u, v) for u, v in out if v - u > 1e-3]

    for a, b in zip(frames[:-1], frames[1:]):
        for side in (-1, 1):
            o = lambda v: v * side
            flip = side < 0
            m_ = mouth_at(a[0], b[0], side)
            if m_ is not None:
                mb.face([pt(a, o(0), 0), pt(b, o(0), 0), pt(b, o(e_gut), 0), pt(a, o(e_gut), 0)] if not flip else
                        [pt(b, o(0), 0), pt(a, o(0), 0), pt(a, o(e_gut), 0), pt(b, o(e_gut), 0)], 'asphalt')
                if GUT > 0:
                    # the gutter (level here) where the kerb stands at the carriageway's edge, asphalt in the mouth
                    lo, hi = cut(m_, e_lane)
                    for u, v, mat in ((a[0], min(b[0], lo), GUTTER), (max(a[0], lo), min(b[0], hi), 'asphalt'),
                                      (max(a[0], hi), b[0], GUTTER)):
                        if v - u > 1e-3:
                            q = [at_so(u, o(e_gut)), at_so(v, o(e_gut)), at_so(v, o(e_lane)), at_so(u, o(e_lane))]
                            uv = [(u, e_gut), (v, e_gut), (v, e_lane), (u, e_lane)]
                            if flip:
                                q, uv = [q[1], q[0], q[3], q[2]], [uv[1], uv[0], uv[3], uv[2]]
                            mb.face(q, mat, uvs=uv if mat == GUTTER else None)
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
                mb.face(q, KERB if mat == 'curb' else mat, uvs=uv if mat in ('curb', GUTTER) else None)

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
            band(med, e_gut, 0, 0, 'asphalt')
            brs = break_at(a[0], b[0], side)
            if brs is not None:
                # an opening in the verge (a crossing, a side road, a flight's foot): round kerbed ends, a ramp between
                break_segment(a, b, side, brs)
            else:
                # the gutter, the granite curb, then the raised boxwood verge with its own kerb
                if GUT > 0:
                    band(e_gut, e_lane, 0, 0, GUTTER)
                riser(e_lane, 0, VZ, 'curb', outward=False)
                band(e_lane, e_curb, VZ, VZ, 'curb')
                band(e_curb, e_verge - 0.2, VZ, VZ, LAWN)
                band(e_verge - 0.2, e_verge, VZ, VZ, 'curb')
                riser(e_verge, WZ, VZ, 'curb', outward=True)
            band(e_verge, e_walk, WZ, WZ, 'pavers')
            # outer planting strip (ginkgo + hedge), then a skirt down to the terrain
            for rg in strip_pieces(a[0], b[0], side, walls + sbreaks):
                band(e_walk, e_walk + 0.18, WZ + 0.05, WZ + 0.05, 'curb', rg)
                riser(e_walk, WZ, WZ + 0.05, 'curb', outward=False, rng=rg)
                band(e_walk + 0.18, e_strip, WZ, WZ, LAWN, rg)
                riser(e_strip, -0.8, WZ, 'curb', outward=True, rng=rg)
            for sd, w0, w1 in sbreaks:
                u, v = max(a[0], w0), min(b[0], w1)
                if sd == side and v - u > 1e-3:
                    riser(e_walk, -0.8, WZ, 'curb', outward=True, rng=(u, v))
                for w in (w0, w1):              # the strip's ends, towards the opening (both windings)
                    if sd == side and a[0] < w < b[0]:
                        q = [at_s(w, o(e_walk), -0.8), at_s(w, o(e_strip), -0.8), at_s(w, o(e_strip), WZ), at_s(w, o(e_walk), WZ)]
                        mb.face(q, KERB)
                        mb.face(q[::-1], KERB)

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

    def ribbon(pts, w, mat, side):
        # a painted line along [(s, offset, dz)], w wide (the offset unsigned, on this side)
        W = [Vector(at_so(s_, side * o_, dz_)) for s_, o_, dz_ in pts]
        for p, q in zip(W[:-1], W[1:]):
            d = q - p
            d.z = 0.0
            if d.length < 1e-6:
                continue
            n = Vector((-d.y, d.x, 0.0)) * (w / 2 / d.length)
            marks.face([tuple(p - n), tuple(q - n), tuple(q + n), tuple(p + n)], mat)

    def surf(o):
        # the height over the road of what lies at offset o in an opening (asphalt and gutter, then the ramp)
        return 0.0 if o <= e_lane else ramp(o)

    # the yellow edge lines: solid along both kerbs (stopping before a crossing's zebra and the bump), straight on past
    # the openings people walk through (the roadview); at a side road's gap it follows the kerb round the verge's end
    # and in, to the sidewalk's edge (2008 roadview 2381296, s 344 m)
    for side in (-1, 1):
        cutl = [(c - STOP, c + STOP) for c in crossings] + ([(bump - 4.0, bump + 4.0)] if bump is not None else []) \
            + [(b0 - RV, b1 + RV) for b0, b1, turn in vbreaks[side] if turn]
        runs = [(4.0, L - 2.0)]
        for c0, c1 in cutl:
            runs = [r for u, v in runs for r in ((u, min(v, c0)), (max(u, c1), v)) if r[1] - r[0] > 0.05]
        for u, v in runs:
            ss_ = [u] + [2.0 * k for k in range(int(u // 2) + 1, int(math.ceil(v / 2)))] + [v]
            ribbon([(s_, e_yel, 0.012) for s_ in ss_], YW, 'paint_yellow', side)
        ry = VC - e_yel
        for b0, b1, turn in vbreaks[side]:
            if not turn:
                continue
            for sc, sg in ((b0 - RV, 1), (b1 + RV, -1)):
                arc = [(sc + sg * ry * math.sin(f), VC - ry * math.cos(f)) for f in np.linspace(0, math.pi / 2, 10)]
                arc += [(sc + sg * ry, VC + (e_verge - VC) * t) for t in (0.5, 1.0)]
                ribbon([(s_, o_, surf(o_) + 0.012) for s_, o_ in arc], YW, 'paint_yellow', side)

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
            quad_at(f, o, o + 0.5, -CL / 2, CL / 2, 'paint_white')
            o += 1.0
        for side in (-1, 1):
            fb = at(c - side * STOP)
            o0, o1 = (0.0, e_gut) if side > 0 else (-e_gut, 0.0)
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
