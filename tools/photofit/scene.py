# the game's 3D scene for photo fitting: terrain, 백양로 centre line and profile, building outlines, landmark vertices
import json, math, os
import numpy as np
A = os.path.dirname(os.path.abspath(__file__))
WT = os.path.normpath(os.path.join(A, '..', '..'))      # repo root
C = json.load(open(WT + '/web/public/data/campus.json'))
TN = np.fromfile(WT + '/web/public/data/terrain_near.bin', dtype=np.float32).reshape(321, 321).astype(np.float64)
HALF, STEP = 800.0, 5.0
BY = C['baekyangro']
BPTS = np.array(BY['pts'], float)[:, :2]
PS, PH = np.array(BY['profile_s']), np.array(BY['profile_h'])
_seg = np.diff(BPTS, axis=0)
_len = np.hypot(*_seg.T)
_cum = np.concatenate([[0], np.cumsum(_len)])


def terrain(x, y):
    from scipy import ndimage
    x, y = np.atleast_1d(x).astype(float), np.atleast_1d(y).astype(float)
    return ndimage.map_coordinates(TN, [(y + HALF) / STEP, (x + HALF) / STEP], order=1, mode='nearest')


def center(s):
    s = np.clip(s, 0, _cum[-1])
    i = np.clip(np.searchsorted(_cum, s) - 1, 0, len(_seg) - 1)
    t = (s - _cum[i]) / _len[i]
    p = BPTS[i] + _seg[i] * t[..., None] if np.ndim(s) else BPTS[i] + _seg[i] * t
    return p


def heading(s, ds=10.0):
    a, b = center(np.maximum(s - ds, 0)), center(np.minimum(s + ds, _cum[-1]))
    d = b - a
    return np.arctan2(d[..., 1], d[..., 0])


def s_off(x, y):
    """arc length along the game centre line and signed offset, + = EAST (note: build_campus uses + west)"""
    P = np.array([x, y], float)
    best = (1e9, 0, 0)
    for i in range(len(_seg)):
        t = np.clip(np.dot(P - BPTS[i], _seg[i]) / _len[i] ** 2, 0, 1)
        q = BPTS[i] + _seg[i] * t
        dd = np.hypot(*(P - q))
        if dd < best[0]:
            cr = _seg[i][0] * (P - BPTS[i])[1] - _seg[i][1] * (P - BPTS[i])[0]     # >0 = left (west)
            best = (dd, _cum[i] + t * _len[i], -np.sign(cr) * dd)
    return best[1], best[2]


def road_h(s):
    return np.interp(s, PS, PH)


def along(s, off_east):
    s = np.asarray(s, float)
    p = center(s)
    a = heading(s)
    # east-normal of a heading a (direction (cos a, sin a)) is (sin a, -cos a)
    return p + np.stack([np.sin(a), -np.cos(a)], -1) * np.asarray(off_east)[..., None] if np.ndim(s) else p + np.array([math.sin(a), -math.cos(a)]) * off_east


BLD = {b['id']: b for b in C['buildings']}
FH = {'modern': 3.8, 'white': 3.6, 'stone': 4.2, 'house': 3.4, 'gym': 6.5, 'city': 3.0, 'brick': 3.6, 'tile': 3.4, 'stone_pale': 4.0}


FH_AT = {222843398: 4.1}                     # 과학관's 4.1 m storeys (blender/generic.py FH_AT)
WING_UP = {222843398: (0, 1, 2, 14)}         # footprint corners of its east wing, one storey higher (generic.py _science_wing)


def roof_z(b):
    return b['base'] + b['levels'] * FH_AT.get(b['id'], FH.get(b['style'], 4.0))


def lm_verts():
    os.makedirs(A + '/.cache', exist_ok=True)
    f = A + '/.cache/lm_verts.npz'      # delete after regenerating campus_landmarks.glb
    if not os.path.exists(f):
        import glb
        d = glb.load(WT + '/web/public/assets/models/campus_landmarks.glb')
        np.savez_compressed(f, **{k: v for k, v in d.items()})
    return dict(np.load(f))


LMNODE = {163525865: 'lm_library', 1444448640: 'lm_union', 324328422: 'lm_centennial', 246156115: 'lm_underwood',
          246156116: 'lm_appenzeller', 246156118: 'lm_stimson', 371403811: 'lm_auditorium', 429249499: 'lm_chapel',
          205583531: 'lm_engineering', 468614722: 'lm_kwangbok', 245623759: 'lm_yeonhui', 242897922: 'lm_daewoo',
          242897923: 'lm_daewoo_annex', 246156117: 'lm_seongam', 246156111: 'lm_gyoyuk', 429249496: 'lm_hanok'}
_V = None


def corners(bid):
    """footprint corners with the top height at each (max model z within 2 m), and the base"""
    global _V
    b = BLD[bid]
    fp = np.array(b['footprint'], float)
    if bid in LMNODE:
        if _V is None:
            _V = lm_verts()
        V = _V[LMNODE[bid]]
        if bid == 324328422:
            V = np.concatenate([V, _V['lm_centennial_block'], _V['lm_centennial_museum']])
        tops = []
        for c in fp:
            m = np.hypot(V[:, 0] - c[0], V[:, 1] - c[1]) < 2.0
            tops.append(V[m, 2].max() if m.any() else np.nan)
        tops = np.array(tops)
    else:
        tops = np.full(len(fp), roof_z(b) + (0 if b['style'] in ('stone', 'house', 'stone_pale') else 0.9))
        for k in WING_UP.get(bid, ()):
            tops[k] += FH_AT.get(bid, FH.get(b['style'], 4.0))
    base = np.array([terrain(x, y)[0] for x, y in fp])
    return fp, tops, base
