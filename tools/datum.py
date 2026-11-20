"""게임 높이의 기준면 (reference/고증/2.8.1_측량_표고.md).

게임의 높이는 해발이다: 국토지리정보원 1:5000 수치지형도의 표고점 107곳(2006 · 2024년 측량)과 rms 0.35 m.

2026-11-15 까지 게임은 1997년 항공사진 블록이 묶인 옛 찻길의 기울어진 면 위에 있었다.

    옛 높이 = 해발 + 2.0 + tilt(x, y),    tilt = 0.052 + 0.522 · x/100 + 0.248 · y/100 m   (동쪽 0.52 %, 북쪽 0.25 %: 0.33°)

상수 2.0 m 는 먼저 뺐다(tools/build_campus.py SURFACE_DZ). 기울기는 이렇게 뺀다.

- 작업면: tools/build_campus.py 와 blender/ 는 지금도 「해발 + 기울기」인 면(작업면) 위에서 땅을 깔고 메시를 짓는다. 1997년 사진이
  평평하다고 잰 땅, 길의 단면, 무작위 심기의 판단이 모두 그 면 위에서 정해졌기 때문이다. 내보낼 때 기울기를 뺀다.
- 땅과 땅에 붙은 것(지형 칸, 데크 · 계단 · 옹벽 · 길의 꼭짓점, 점으로 놓인 것)은 제 자리의 값을 뺀다.
- 건물은 기울이지 않는다: 건물마다(한 건물의 맞닿은 동은 한 묶음) 한 값(campus.json 의 tilt: 묶음 가운데의 값)을 빼고, 그 발치 PAD m 안의 땅도
  건물과 같은 값을 뺀다(문턱 · 계단 · 테라스가 땅과 어긋나지 않게). 그 밖 EASE m 에 걸쳐 제 자리의 값으로 이어진다.
  수평이 생명인 것(코트 · 객석 · 분수 · 정문 담 · 로터리의 큰 건물)도 같은 식의 틀이다(campus.json datum.zones).
- 소스에 적는 절대 높이는 해발이다. 작업면에서 쓰는 곳에서 up(x, y, z) 로 올린다(읽을 때 한 번).

- tilt(x, y): 그 면. 측량으로 확인한 범위(가까운 지형 격자 ±800 m 와 남쪽 · 북쪽 조각: CORE) 안에서는 면 그대로,
  그 밖(먼 땅 ±8 km)에서는 가장자리 값에서 FADE m 에 걸쳐 0 으로 사그라진다(면을 그대로 늘이면 8 km 밖에서 60 m 가 됨).
- Field: 틀을 넣은 값의 밭. 지형 격자 마디마다의 값이고, 마디 사이는 웹이 지형을 그리는 두 삼각형으로 잇는다
  (그래야 메시와 지형의 높이차가 작업면에서와 꼭 같다). 격자 밖은 tilt.
- to_sea / to_work: campus.json 의 절대 높이를 해발로 / 작업면으로(같은 자리 규칙이라 서로 역이다).

numpy 만 쓴다(blender/common.py 도 읽음).
"""
import math

import numpy as np

TILT = (0.052, 0.522, 0.248)                 # (m, 동쪽 100 m 마다, 북쪽 100 m 마다)
CORE = (-800.0, -1200.0, 800.0, 1280.0)      # (x0, y0, x1, y1): 가까운 격자, 신촌 로터리 조각, 무악학사 · 북문 조각
FADE = 1600.0
PAD = 7.5                                    # 틀의 발치: 외곽선에서 이만큼(5 m 격자 한 칸의 대각선 7.1 m 보다 넓게)
EASE = 15.0                                  # 그 밖에서 제 자리의 값으로 이어지는 거리


def tilt(x, y):
    """작업면 − 해발 (m). 배열도 받음"""
    x, y = np.asarray(x, float), np.asarray(y, float)
    xc, yc = np.clip(x, CORE[0], CORE[2]), np.clip(y, CORE[1], CORE[3])
    t = np.clip(np.hypot(x - xc, y - yc) / FADE, 0.0, 1.0)
    out = (TILT[0] + TILT[1] * xc / 100.0 + TILT[2] * yc / 100.0) * (1.0 - t * t * (3.0 - 2.0 * t))
    return float(out) if out.ndim == 0 else out


def up(x, y, z, nd=2):
    """소스에 적힌 해발 z 를 작업면의 높이로. nd 자리에서 반올림한다: 작업면에서 처음 적힌 값(cm)이 그대로 되살아나
    땅과 심기가 한 칸도 달라지지 않는다. nd=None 이면 그대로"""
    v = z + tilt(x, y)
    return v if nd is None else round(float(v), nd)


def up3(pts, nd=2, f=None):
    """[(x, y, 해발), ...] -> [(x, y, 작업면 높이), ...] (높이가 None 인 점은 그대로). f 를 주면 점은 제 틀의 (u, v, 해발)이고
    f(u, v) 가 그 자리 (x, y) 다"""
    at = f or (lambda a, b: (a, b))
    return [(p[0], p[1], None if p[2] is None else up(*at(p[0], p[1]), p[2], nd)) + tuple(p[3:]) for p in pts]


def up_uv(f, us, vs, zs, nd=2):
    """제 틀 f(u, v) -> (x, y) 안에 적은 해발의 줄이나 표 -> 작업면 높이. 한 줄이면 us · vs 가운데 하나가 목록이고(다른
    하나는 값 하나), 표면 zs[j][i] 가 (us[i], vs[j]) 의 높이다"""
    if isinstance(zs[0], (list, tuple)):
        assert len(zs) == len(vs) and all(len(r) == len(us) for r in zs)
        return [[up(*f(u, v), z, nd) for u, z in zip(us, r)] for v, r in zip(vs, zs)]
    if isinstance(us, (list, tuple)):
        assert len(us) == len(zs)
        return [up(*f(u, vs), z, nd) for u, z in zip(us, zs)]
    assert len(vs) == len(zs)
    return [up(*f(us, v), z, nd) for v, z in zip(vs, zs)]


def up_at(table, places, nd=2):
    """[(s, 해발), ...] 꼴의 단면과 그 점들의 자리 [(x, y), ...] -> [(s, 작업면 높이), ...]"""
    assert len(table) == len(places), (len(table), len(places))
    return [(q[0], up(p[0], p[1], q[1], nd)) + tuple(q[2:]) for q, p in zip(table, places)]


def up_plane(c, x0, y0, nd=(2, 4)):
    """해발인 면 c[0] + c[1] (x − x0) + c[2] (y − y0) 의 계수 -> 작업면에서의 계수(면에 면을 더함)"""
    return (round(c[0] + tilt(x0, y0), nd[0]), round(c[1] + TILT[1] / 100.0, nd[1]), round(c[2] + TILT[2] / 100.0, nd[1]))


def centroid(poly):
    """다각형의 넓이 중심"""
    p = np.asarray(poly, float)
    q = np.roll(p, -1, 0)
    a = p[:, 0] * q[:, 1] - q[:, 0] * p[:, 1]
    if abs(a.sum()) < 1e-9:
        return float(p[:, 0].mean()), float(p[:, 1].mean())
    return float(((p[:, 0] + q[:, 0]) * a).sum() / (3 * a.sum())), float(((p[:, 1] + q[:, 1]) * a).sum() / (3 * a.sum()))


def poly_dist(px, py, poly):
    """점들에서 다각형까지의 거리(안은 0)"""
    px, py = np.asarray(px, float).ravel(), np.asarray(py, float).ravel()
    V = np.asarray(poly, float)
    W = np.roll(V, -1, 0)
    dx, dy = W[:, 0] - V[:, 0], W[:, 1] - V[:, 1]
    t = np.clip(((px[:, None] - V[:, 0]) * dx + (py[:, None] - V[:, 1]) * dy) / np.maximum(dx * dx + dy * dy, 1e-12), 0.0, 1.0)
    d = np.hypot(px[:, None] - (V[:, 0] + t * dx), py[:, None] - (V[:, 1] + t * dy)).min(1)
    with np.errstate(divide='ignore', invalid='ignore'):
        xi = dx * (py[:, None] - V[:, 1]) / np.where(dy == 0, np.nan, dy) + V[:, 0]
        cross = ((V[:, 1] > py[:, None]) != (W[:, 1] > py[:, None])) & (px[:, None] < xi)
    return np.where(cross.sum(1) % 2 == 1, 0.0, d)


def zones(c):
    """campus.json 의 틀: [(외곽선, 값)] — 건물(buildings 의 tilt)과 datum.zones. 캠퍼스 밖 동네의 집('city')은 기초가 땅속으로
    내려간 상자라 발치의 땅을 따로 잡지 않는다(집은 제 값 하나로 내려가고 땅은 제 자리의 값으로)"""
    out = [(b['footprint'], b['tilt']) for b in c['buildings'] if 'tilt' in b and b['style'] != 'city']
    out += [(z['poly'], z['t']) for z in c.get('datum', {}).get('zones', [])]
    return out


class Field:
    """틀을 넣은 「작업면 − 해발」. terr: campus.json 의 terrain(near · south · north 의 자리), zs: zones()"""

    def __init__(self, terr, zs):
        n = terr['near']
        self.grids = [('near', -n['half'], -n['half'], n['step'], n['n'], n['n'])]
        for k in ('south', 'north'):
            if terr.get(k):
                g = terr[k]
                self.grids.append((k, g['x0'], g['y0'], g['step'], g['nx'], g['ny']))
        self.D = {}
        for name, x0, y0, st, nx, ny in self.grids:
            X, Y = np.meshgrid(x0 + np.arange(nx) * st, y0 + np.arange(ny) * st)
            T = tilt(X, Y)
            # a frame holds the ground inside it and PAD m round it (w 1), easing out over EASE m.  Where two frames
            # reach the same ground each has it at its own foot and they meet half way (by the cube of the distance)
            num, den, out_ = np.zeros(X.shape), np.zeros(X.shape), np.ones(X.shape)
            for poly, t0 in zs:
                P = np.asarray(poly, float)
                r = PAD + EASE
                i0, i1 = int(math.floor((P[:, 0].min() - r - x0) / st)), int(math.ceil((P[:, 0].max() + r - x0) / st)) + 1
                j0, j1 = int(math.floor((P[:, 1].min() - r - y0) / st)), int(math.ceil((P[:, 1].max() + r - y0) / st)) + 1
                i0, i1, j0, j1 = max(i0, 0), min(i1, nx), max(j0, 0), min(j1, ny)
                if i0 >= i1 or j0 >= j1:
                    continue
                d = poly_dist(X[j0:j1, i0:i1], Y[j0:j1, i0:i1], P).reshape(j1 - j0, i1 - i0)
                w = np.clip(1.0 - np.maximum(d - PAD, 0.0) / EASE, 0.0, 1.0)
                w = w * w * (3.0 - 2.0 * w)
                k = w / (1e-3 + d ** 3)
                num[j0:j1, i0:i1] += k * t0
                den[j0:j1, i0:i1] += k
                out_[j0:j1, i0:i1] *= 1.0 - w
            self.D[name] = np.where(den > 0, (1.0 - out_) * num / np.maximum(den, 1e-30) + out_ * T, T)

    def _which(self, x, y):
        """점마다 그 점을 가진 격자의 번호(blender/common.py _grid 와 같은 순서: 남쪽, 북쪽, 가까운 격자), 없으면 -1"""
        k = np.full(x.shape, -1)
        g = {name: (x0, y0, st, nx, ny) for name, x0, y0, st, nx, ny in self.grids}
        x0, y0, st, nx, ny = g['near']
        k[(x >= x0) & (x <= x0 + (nx - 1) * st) & (y >= y0) & (y <= y0 + (ny - 1) * st)] = 0
        for i, name in ((1, 'south'), (2, 'north')):
            if name in g:
                x0, y0, st, nx, ny = g[name]
                inx = (x >= x0) & (x <= x0 + (nx - 1) * st)
                k[inx & ((y < y0 + (ny - 1) * st) & (y >= y0) if name == 'south' else (y > y0) & (y <= y0 + (ny - 1) * st))] = i
        return k

    def at(self, x, y):
        """자리 (x, y) 의 값. 배열도 받음"""
        xa, ya = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        xf, yf = xa.ravel(), ya.ravel()
        out = np.asarray(tilt(xf, yf), float).reshape(xf.shape).copy()
        which = self._which(xf, yf)
        for gi, (name, x0, y0, st, nx, ny) in enumerate(self.grids):
            idx = {'near': 0, 'south': 1, 'north': 2}[name]
            m = which == idx
            if not m.any():
                continue
            D = self.D[name]
            fx = np.clip((xf[m] - x0) / st, 0, nx - 1.000001)
            fy = np.clip((yf[m] - y0) / st, 0, ny - 1.000001)
            i, j = fx.astype(int), fy.astype(int)
            ax, ay = fx - i, fy - j
            a, b, cc, d = D[j, i], D[j, i + 1], D[j + 1, i], D[j + 1, i + 1]
            # (each cell two triangles split along (i+1, j)-(i, j+1), as web/src/terrain.js draws the ground)
            out[m] = np.where(ax + ay <= 1.0, a + (b - a) * ax + (cc - a) * ay, d + (cc - d) * (1.0 - ax) + (b - d) * (1.0 - ay))
        out = out.reshape(xa.shape)
        return float(out) if out.ndim == 0 else out


def field(c):
    return Field(c['terrain'], zones(c))


# ----------------------------------------------------------------------------- campus.json 의 절대 높이
def _line_at(pts, s):
    """꺾은선 pts 의 s m 자리"""
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if s <= L or b is pts[-1]:
            f = s / L if L > 0 else 0.0
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        s -= L
    return tuple(pts[-1][:2])


def _fr(o, t, n=None):
    n = (-t[1], t[0]) if n is None else n
    return lambda s, d=0.0: (o[0] + t[0] * s + n[0] * d, o[1] + t[1] * s + n[1] * d)


def heights(c):
    """campus.json 의 모든 절대 높이: (담은 것, 열쇠, x, y). 건물 바닥처럼 틀의 값이 따로 있으면 (담은 것, 열쇠, 값, None)"""
    out = []
    A = lambda h, k, x, y: out.append((h, k, x, y))
    if 'amphitheater' in c:
        a = c['amphitheater']
        A(a, 'arena_h', a['cx'], a['cy'])
    for key in ('stimson_front', 'appenzeller_front'):
        F = c.get(key)
        if not F:
            continue
        xy = _fr(F['frame']['m'], F['frame']['t'], F['frame']['f'])
        dr, dg = sum(F['road']) / 2, F['frame']['walk']
        A(F, 'z0', *xy(0.0, 0.0))
        A(F, 'zr0', *xy(0.0, dr))
        A(F, 'zg0', *xy(0.0, dg))
        for q in F['zr']:
            A(q, 1, *xy(q[0], dr))
        for q in F['zg']:
            A(q, 1, *xy(q[0], dg))
        for fl in F['flights']:
            A(fl, 'zr', *xy(fl['s'], dr))
            A(fl, 'zg', *xy(fl['s'], dg))
        sf = F.get('south')            # (스팀슨관 앞 단의 남쪽 끝 계단: its head and its foot on its axis)
        if sf:
            A(sf, 'zr', *xy(sf['s'], sf['d']))
            A(sf, 'zg', *xy(sf['s'] - (sf['n'] - 1) * sf['T'], sf['d']))
    for key, dk in (('stimson_front', 'deck'), ('appenzeller_front', 'deck'), ('daewoo_front', 'deck'), ('daewoo_back', 'deck'),
                    ('daewoo_back', 'deck_nw'), ('kb_bank', 'deck')):
        d = c.get(key, {}).get(dk)
        if d:
            for v in d['v']:
                A(v, 2, v[0], v[1])
            for r in d['rim']:
                for v in r:
                    A(v, 2, v[0], v[1])
    if 'aud_bank' in c:
        b = c['aud_bank']
        for s in b['sections']:
            for k in range(4, 10):
                A(s, k, s[1], s[2])
        A(b, 'terrace', *c['aud_flight']['o'])
    if 'aud_flight' in c:
        f = c['aud_flight']
        for k in ('foot_z', 'head_z'):
            A(f, k, *f['o'])
        for k in range(len(f['far'])):
            A(f['far'], k, *f['o'])
    for fl in c.get('aud_north', {}).get('flights', []):       # (대강당 윗단 북쪽 끝 너머의 계단: tools/audnorth97.py)
        A(fl, 'z_top', *fl['top'])
        A(fl, 'z_foot', *fl['foot'])
    for fl in c.get('chapel97', {}).get('flights', []):       # (루스채플 앞 두 잔디 사이 계단: tools/chapel97.py)
        A(fl, 'z_top', *fl['top'])
        A(fl, 'z_foot', *fl['foot'])
    R = c['baekyangro']
    for i, s in enumerate(R['profile_s']):
        A(R['profile_h'], i, *_line_at(R['pts'], s))
    for ap in R.get('apron_paint', []):
        for p in ap['pts']:
            A(p, 2, p[0], p[1])
    for bn in c.get('banners', []):
        for p in [bn['a'], bn['b']] + bn['ties']:
            A(p, 2, p[0], p[1])
    for b in c['buildings']:
        for k in ('base', 'top_ground'):
            out.append((b, k, b['tilt'], None))
        for k in ('floor', 'eaves', 'tower', 'annex_top', 'yard', 'fore'):       # (광복관: tools/kwangbok97.py plan)
            if k in b.get('plan', {}):
                out.append((b['plan'], k, b['tilt'], None))
    E = c.get('eng1_yard')                       # (제1공학관 안뜰의 낮은 동과 옹벽 · 데크: tools/eng97.py)
    if E:
        ca, sa = math.cos(E['ang']), math.sin(E['ang'])
        hu, hv = (E['hall'][0] + E['hall'][1]) / 2, (E['hall'][2] + E['hall'][3]) / 2
        hc = (E['o'][0] + hu * ca - hv * sa, E['o'][1] + hu * sa + hv * ca)
        hb = min(c['buildings'], key=lambda b: math.hypot(*(np.array(centroid(b['footprint'])) - hc)))
        out.append((E, 'base', hb['tilt'], None))                     # (the hall's own floor: with the hall)
        for v in E['deck']['v']:
            A(v, 2, v[0], v[1])
        for r in E['deck']['rim']:
            for v in r:
                A(v, 2, v[0], v[1])
        for _, row in E['walls']:
            for q in row:
                A(q, 2, q[0], q[1])
                A(q, 3, q[0], q[1])
        for q in E.get('bay', []):                 # (the bay in the wall at v 0, the terrace's planter)
            A(q, 2, q[0], q[1])
        if 'planter' in E:
            P_ = E['planter']
            for k in ('top', 'deck'):
                A(P_, k, *centroid(P_['box']))
    E = c.get('eng2_plaza')                      # (제2 · 제3공학관 사이의 돔 · 피라미드 · 계단, 구름다리: tools/eng97.py plaza_parts)
    if E:
        d = E['dome']
        A(d, 3, d[0], d[1])
        A(d, 4, d[0], d[1])
        for k in ('z', 'top'):
            A(E['pyramid'], k, *centroid(E['pyramid']['rim']))
        for t in E['flight']['treads']:
            A(t, 'z', *centroid(t['q']))
        for k in ('z0', 'z1'):
            A(E['bridge'], k, *centroid(E['bridge']['q']))
    for b in c.get('rnd_ghosts', []):
        for k in ('base', 'top_ground'):
            A(b, k, *centroid(b['footprint']))
    if 'centennial_terrace' in c:
        t = c['centennial_terrace']
        xy = _fr(t['o'], t['t'], t['n'])
        mid = xy(t['flights'][0]['low'][0], t['flights'][0]['d0'] / 2)            # (the doors' axis, half way out)
        for k in ('porch', 'l1', 'l2', 'foot'):
            A(t, k, *mid)
        for fl in t['flights']:
            A(fl, 'z0', *mid)
        for w in t['wall']:
            A(w, 'top', *mid)
        for s, row in t['apron']:
            for q in row:
                A(q, 1, *xy(s, q[0]))
    for key in ('daewoo_front', 'daewoo_back'):
        F = c.get(key)
        if not F:
            continue
        df = c['daewoo_front']
        ang = df['frame']['ang']
        at = _fr(df['frame']['o'], (math.cos(ang), math.sin(ang)))(df['uc'], 0.0)      # (the hall's axis at its front wall)
        for k in ('floor', 'terrace', 'mid', 'plaza', 'tier', 'lawn', 'low', 'stage', 'top'):
            if k in F and not isinstance(F[k], (list, dict)):
                A(F, k, *at)
        for k in range(len(F.get('lot_z', []))):
            A(F['lot_z'], k, *at)
        if 'sang' in F:
            A(F['sang'], 'top', *c['sang']['c'])              # (the 상뜰's level: ground, at its round lawn)
        if 'stair' in F and 'z_top' in F['stair']:
            A(F['stair'], 'z_top', *F['stair']['top'])
            A(F['stair'], 'z_foot', *F['stair']['foot'])
    for key, bid in (('gyoyuk_floor', 246156111), ('seongam_floor', 246156117)):       # (교육관, 성암관)
        if key in c:
            b = next(b for b in c['buildings'] if b['id'] == bid)
            out.append((c, key, b['tilt'], None))
    if 'library_terrace' in c:
        t = c['library_terrace']
        at = _fr(t['o'], t['t'], t['n'])(t['len'] / 2, 0.0)
        A(t, 'floor', *at)
        A(t, 'foot', *at)
    for m in c.get('markers', []):
        A(m, 'top', *m['pos'])
    if 'seomun' in c:
        s = c['seomun']
        for p in s['posts']:
            A(p, 2, p[0], p[1])
        for w in s['walls']:
            for p in w['pts']:
                A(p, 2, p[0], p[1])
                A(p, 3, p[0], p[1])
        A(s, 'z', sum(p[0] for p in s['posts']) / len(s['posts']), sum(p[1] for p in s['posts']) / len(s['posts']))
    for p in c.get('dongmun', {}).get('deck', []):      # (봉원고가차도's surface: tools/dongmun.py FLY)
        A(p, 2, p[0], p[1])
    S = c['statues']
    for k, v in S.items():
        if isinstance(v, dict) and 'h' in v and 'pos' in v:
            A(v, 'h', *v['pos'])
    G = S.get('gongwon_site')
    if G:
        for p in G['ring']:
            A(p, 2, p[0], p[1])
        A(G['crane'], 2, G['crane'][0], G['crane'][1])
        gx = _fr(G['o'], (math.cos(G['rot']), math.sin(G['rot'])))
        for q in [G['pit'], G['slab']] + G['sheds']:
            A(q, 4, *gx((q[0] + q[1]) / 2, (q[2] + q[3]) / 2))
    J = c.get('jh_site')                         # (제2인문관 공사장 · 종합관 북쪽 마당: tools/widang97.py site)
    if J:
        for k in ('sheds', 'stacks', 'piles', 'heaps', 'machines', 'posts', 'rubble', 'hoard'):
            for q in J.get(k, []):
                A(q, 2, q[0], q[1])
    T = c.get('town')
    if T:
        b = T['banner']
        A(b, 4, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        for q in T['blocks']:
            A(q, 5, q[0], q[1])
        for q in T['entrances']:
            A(q, 6, q[0], q[1])
        for q in T.get('kiosks', []):
            A(q, 3, q[0], q[1])
        for l in T['landmarks']:
            for k in ('base', 'deck', 'top', 'foot'):
                if k in l:
                    out.append((l, k, l['tilt'], None))
        ra = T['rail']
        for s in ra['sections']:
            for k in (6, 7, 9, 10, 11):
                if s[k] is not None:
                    A(s, k, s[0], s[1])
        for p in ra.get('wall97', []):          # (철둑 남쪽 옹벽 위 벽: the bank's surface, the wall's top; tools/ssr97.py)
            A(p, 2, p[0], p[1])
            A(p, 3, p[0], p[1])
        for fb in T.get('footbridges', []):     # (육교: the deck's top at either end; tools/ssr97.py)
            A(fb['top'], 0, *fb['a'])
            A(fb['top'], 1, *fb['b'])
        if T.get('station97'):                  # (옛 신촌역 역사: its floor; tools/ssr97.py station97)
            A(T['station97'], 'base', *T['station97']['at'])
        bx = sum(T['bridge']['x']) / 2
        by = float(np.interp(bx, [p[0] for p in ra['sections']], [p[1] for p in ra['sections']]))
        A(ra, 'z', bx, by)
        A(ra, 'top', bx, by)
        for i, p in enumerate(T['road']['pts']):
            A(T['road']['z'], i, p[0], p[1])
        for k in ('signs', 'signs2', 'vsigns'):
            for q in T[k]:
                A(q, 2, q[0], q[1])
    U = c.get('underwood_steps')
    if U:
        f = U['frame']
        xy = _fr(f['o'], f['u'], f['v'])
        A(U, 'h0', *xy(0.0, 0.0))
        A(U, 'top', *xy(0.0, U['v_head']))
        for t in U['tiers']:
            A(t, 'z0', *xy(0.0, t['v0']))
            A(t, 'z1', *xy(0.0, t['v1']))
        for l in U['landings']:
            A(l, 'z', *xy(0.0, (l['v0'] + l['v1']) / 2))
        for fl in U['flights']:
            A(fl, 'z_top', *fl['top'])
            A(fl, 'z_foot', *fl['foot'])
    Yh = c.get('yeonhui')
    if Yh:
        fn = {fl['name']: fl for fl in Yh['flights']}
        A(Yh, 'garden', *fn['south']['top'])              # (the garden's level at its S node: the south flight's head)
        hm = ((Yh['hall']['a'][0] + Yh['hall']['b'][0]) / 2, (Yh['hall']['a'][1] + Yh['hall']['b'][1]) / 2)
        A(Yh, 'road', *fn['north']['top'])
        A(Yh, 'floor', *hm)
        for fl in Yh['flights']:
            A(fl, 'z_top', *fl['top'])
            A(fl, 'z_foot', *fl['foot'])
        fc = Yh['forecourt']
        A(fc['c'], 2, fc['c'][0], fc['c'][1])
        for p in fc['drain'] + fc['poly'] + [q for r in fc['rays'] for q in r]:
            A(p, 2, p[0], p[1])
        for run in Yh['wall']:
            for p in run:
                A(p, 2, p[0], p[1])
                A(p, 3, p[0], p[1])
    Mw = c.get('med_west')
    if Mw:                                                # (tools/medwest97.py: 올린 주차장 · 경사로 · 단. 표는 마디마다)
        co, si = math.cos(math.radians(Mw['ang'])), math.sin(math.radians(Mw['ang']))
        for p in Mw['plates']:
            for j, row in enumerate(p['z']):
                for i in range(len(row)):
                    u, v = p['us'][i], p['vs'][j]
                    A(row, i, Mw['o'][0] + u * co - v * si, Mw['o'][1] + u * si + v * co)
        for v in Mw['top']['v']:
            A(v, 2, v[0], v[1])
        for r in Mw['walk']:
            for v in r:
                A(v, 2, v[0], v[1])
        for q in Mw['quads']:
            for v in q[1]:
                A(v, 2, v[0], v[1])
    return out


def _move(c, f, sign, nd):
    hs = heights(c)
    pts = [(h, k, x, y) for h, k, x, y in hs if y is not None]
    d = f.at(np.array([p[2] for p in pts]), np.array([p[3] for p in pts])) if pts else []
    for (h, k, _, _), dv in zip(pts, d):
        h[k] = round(h[k] + sign * float(dv), nd)
    for h, k, t0, y in hs:
        if y is None:
            h[k] = round(h[k] + sign * t0, nd)
    return c


def to_sea(c, f=None):
    """작업면에서 지은 campus.json 의 높이를 해발로(제자리에서 고침)"""
    return _move(c, f or field(c), -1.0, 3)


def to_work(c, f=None):
    """해발인 campus.json 을 작업면으로(blender/common.py 가 읽을 때)"""
    return _move(c, f or field(c), 1.0, 6)
