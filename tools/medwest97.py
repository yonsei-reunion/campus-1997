"""의료원 서쪽, 1997: 외래진료소 앞의 올린 주차장(데크)과 두 경사로 · 보행 경사로, 안 · 이비인후과병원 남쪽 단과 계단,
그 둘레의 땅 (reference/고증/3.1.2 「외래진료소 서쪽」, 2.10, 2.3.4).  tools/build_campus.py 가 부른다.

    took, info = medwest97.grade(Hn, X, Y, FIXED, halls, harmonic_fill, road_ls, road_hw)   # 심기가 끝난 뒤, 지형을 쓰기 앞
    clear, asphalt, pavers = medwest97.paint()                    # 땅 지도에만(늦게)
    out['med_west'] = medwest97.build(Hn, half, step, halls)      # 올린 면 · 벽 · 난간 · 계단(blender/landmarks.py med_west)
    medwest97.move_off(trees, shrubs, props, halls)               # 나무는 목록 제자리에서 1997년 나무 자리로
    medwest97.walks(out['paths']); medwest97.zebra()              # 게임이 읽는 길, 건널목의 흰 줄
    buildings += medwest97.halls()                                # 외래진료소의 낮은 동 · 둥근 끝 날개(건물 목록 끝)
    (tools/cars97_new.json 「외래진료소 서쪽 데크 주차장」: snap_cars · stall_lines 로 줄에 맞춘 51대)

Source: the 1997-07-28 scans (자료 Q), frames 26/16 · 27/17 · 27/18 (26/15 north of y -340), every pair on its own.
Frame: the forecourt's own (u, v), o (25, -352), u 42.2 deg north of east (towards 외래진료소), v to its left
(north-west); the edges read where the frames from both flight lines agree on the surface's own plane (0.2 m), the
heights where two pairs or more agree (0.3 - 0.5 m).  Kakao's 2008 skyview has the same forecourt, ramps and walls.

What stood there (the game had today's lawn, walks and roundabout on one slope from 24 to 31 m):
- 외래진료소 앞마당 (the "deck"): a paved forecourt 50 x 42 m raised on walls over the garden south-west of it
  (5.5 m) and the hospital's entrance road, in three levels stepping up to the hall: the south-west row and aisle,
  the middle double row split along its middle (1.5 m), the north-east row a step under the drive along the hall.
  (Whether it stood hollow, a lower level under it, the vertical frames cannot tell: PAVE_UV.)
- a car ramp along its north-west side (14 %, banded) with a walk beside it on the same slope, and a second ramp along
  its south-east side on a wall of its own (its face in the frames from the east and south-east only, a planted
  strip at the road's level at its foot); both from the entrance road up to the drive before the hall.
- 안 · 이비인후과병원 남쪽: the hall's entrance terrace, a curved platform 7 m over the car park west of it, a flight
  of 2 m down its south front to a zebra crossing on the drive (the "steps" of the earlier reading were the
  crossing's bars: level within 0.2 m in three frames), the drive rising along a brick wall with a row of stalls.

Every height here is above sea level (해발), taken up to the working datum the ground is laid on (해발 + tilt:
tools/datum.py) where it is read, each at its own place: the plates' tables at their (u, v) in the frame above
(datum.up(*xy(u, v), z) · up_uv), GROUND_PTS at their (x, y), the halls' floors at the middle of 외래진료소's frame.
"""
import math
import random

import numpy as np
import datum
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import triangulate, unary_union

O = (25.0, -352.0)
ANG = 42.2
_C, _S = math.cos(math.radians(ANG)), math.sin(math.radians(ANG))


def xy(u, v):
    return (O[0] + u * _C - v * _S, O[1] + u * _S + v * _C)


def uv(x, y):
    dx, dy = np.asarray(x, float) - O[0], np.asarray(y, float) - O[1]
    return dx * _C + dy * _S, -dx * _S + dy * _C


def _rect(u0, u1, v0, v1):
    return Polygon([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def _to_xy(poly):
    """a polygon of the frame in campus metres"""
    return Polygon([xy(u, v) for u, v in poly.exterior.coords], [[xy(u, v) for u, v in r.coords] for r in poly.interiors])


# ---------------------------------------------------------------------------------------------------------------------
# the forecourt (in u, v).  Its surface: hT = fT(u) - 0.010 v (the south-east end 0.4 m up) west of the north-east
# row, level across the drive before the hall
T_U0, T_U1, T_V0, T_V1 = -16.8, 33.5, -26.6, 15.0          # (its walls' outer faces; u 33.5: under the hall's front)
ISLE = (-5.5, 0.1, 6.3, -18.3, 7.6)                        # the middle double row: west edge, the split, east edge, v
NROW = (12.8, 18.4, -21.0, 11.5)                           # the north-east row
L3_V = (-29.9, 18.9)                                       # the drive before the hall: on past both ramps' heads
HEAD = (22.4, 33.5, -6.8, 6.3)                             # 외래진료소's low front block (its roof 42.1 m: three frames)
Z_L1, Z_L2 = datum.up(*xy(-9.0, 0.0), 35.66), datum.up(*xy(9.5, 0.0), 37.13)        # the two aisles, each at its (u, v)
T_US = [-16.8, -5.5, 6.3, 12.8, 18.4, 22.0, 28.0, 33.5]
T_FZ = [Z_L1, Z_L1, Z_L2, Z_L2] + datum.up_uv(xy, T_US[4:], 0.0, [37.44, 37.67, 37.99, 38.21])
T_DV = [-0.010, -0.010, -0.010, -0.010, 0.0, 0.0, 0.0, 0.0]
# the two ramps and the walk: z along u (level across; each height at its u, the middle of its v)
RAMP_NW = dict(v=(15.0, 18.9), u=[-33.5, 14.0, 18.4])
RAMP_NW['z'] = datum.up_uv(xy, RAMP_NW['u'], 16.95, [30.32, 36.84, 37.47])
WALK_NW = dict(v=(18.9, 23.9), u=[-34.5, -33.5, 14.0, 18.4, 22.0, 28.0, 33.5])
WALK_NW['z'] = datum.up_uv(xy, WALK_NW['u'], 21.4, [30.34, 30.48, 37.0, 37.47, 37.7, 38.02, 38.24])
RAMP_SE = dict(v=(-29.9, -26.6), u=[-33.5, -28.0, 2.0, 16.0, 18.4])
RAMP_SE['z'] = datum.up_uv(xy, RAMP_SE['u'], -28.25, [29.38, 29.9, 34.83, 37.15, 37.39])
# 안 · 이비인후과병원 남쪽: the terrace (its rim an arc: outer parapet line), the flight let into its south front, the
# drive (N1: from the entrance road at u -17.5 up along the brick wall to under the link between the two halls)
Y_Z = datum.up(*xy(25.0, 55.0), 35.19)                     # (six pairs within 0.35 m)
Y_ARC = [(24.9, 46.9), (24.5, 48.4), (23.5, 52.0), (22.7, 54.0), (22.2, 56.0), (22.0, 58.0), (22.0, 60.0), (22.3, 61.8),
         (23.4, 63.6), (25.4, 66.6)]
Y_EAST = [(26.6, 66.4), (32.2, 56.1), (31.6, 55.9), (31.6, 50.28)]     # (the hall's face in the game, the link's wall)
STAIR = dict(u=(25.4, 31.6), v=(47.2, 50.28), z=(datum.up(*xy(28.5, 47.2), 33.21), Y_Z), risers=12)
N1_US = [-17.5, -2.0, 14.0, 28.0, 36.0]
N1_VS = [28.0, 34.0, 39.5, 44.0, 47.2, 54.0]
N1_Z = datum.up_uv(xy, N1_US, N1_VS, [
    [30.58, 31.20, 31.41, 31.93, 32.09],                   # v 28
    [30.79, 31.41, 31.52, 32.14, 32.30],                   # v 34
    [31.05, 31.92, 32.13, 32.55, 32.51],                   # v 39.5
    [31.26, 32.07, 32.69, 33.06, 33.06],                   # v 44
    [31.37, 32.13, 32.74, 33.21, 33.17],                   # v 47.2
    [31.48, 32.24, 33.13, 33.23, 33.18]])                  # v 54
# the brick wall's line: the upper level's edge (three pairs within 0.2 - 0.5 m: 31.9 - 32.5 m on it, 28 m 4 m out),
# 1 - 2 m outside the stalls' back walk; the 2008 skyview's band of red brick runs along it
N1_WALL = [(-18.13, 40.70), (14.28, 50.45), (14.6, 53.8), (22.9, 53.8)]
N1_SE = [(36.0, 36.9), (31.6, 36.6), (31.6, 35.2), (13.4, 35.2), (10.2, 33.4), (0.0, 32.2), (-17.5, 30.9)]
# 외래진료소's round-ended wing (roof: six pairs); its levels, the hall's and the low front block's at the hall's middle
WING = dict(u=(13.4, 33.5), v=(28.4, 35.2), z=datum.up(63.11, -315.57, 44.0), base=datum.up(63.11, -315.57, 31.6))


def _interp_rows(us, vs, Z, u, v):
    """bilinear on a rectilinear table (clamped)"""
    u, v = np.clip(u, us[0], us[-1]), np.clip(v, vs[0], vs[-1])
    i = int(np.clip(np.searchsorted(us, u, side='right') - 1, 0, len(us) - 2))
    j = int(np.clip(np.searchsorted(vs, v, side='right') - 1, 0, len(vs) - 2))
    a, b = (u - us[i]) / (us[i + 1] - us[i]), (v - vs[j]) / (vs[j + 1] - vs[j])
    return float(Z[j][i] * (1 - a) * (1 - b) + Z[j][i + 1] * a * (1 - b) + Z[j + 1][i] * (1 - a) * b + Z[j + 1][i + 1] * a * b)


def _table_u(us, zs, v0, v1, dv=None):
    """a table level across v (or tilted dv per metre of v about v = 0)"""
    dv = dv or [0.0] * len(us)
    return list(us), [v0, v1], [[z + d * v0 for z, d in zip(zs, dv)], [z + d * v1 for z, d in zip(zs, dv)]]


def _plates():
    """the raised surfaces: name, paint, polygon (u, v), table (us, vs, Z), wall material, open edges (no wall, the
    plate runs out into the ground there)"""
    P = []
    isle_w, isle_e = _rect(ISLE[0], ISLE[1], ISLE[3], ISLE[4]), _rect(ISLE[1], ISLE[2], ISLE[3], ISLE[4])
    nrow = _rect(NROW[0], NROW[1], NROW[2], NROW[3])
    head = _rect(*HEAD)
    court = unary_union([_rect(T_U0, T_U1, T_V0, T_V1), _rect(NROW[1], T_U1, L3_V[0], L3_V[1])]) \
        .difference(unary_union([isle_w, isle_e, nrow, head]))
    tT = _table_u(T_US, T_FZ, L3_V[0], L3_V[1], T_DV)
    P.append(dict(name='court', paint='asphalt', poly=court, table=tT, wall='concrete'))
    flat = lambda z: ([T_U0, T_U1], [L3_V[0], L3_V[1]], [[z + 0.010 * -L3_V[0]] * 2, [z - 0.010 * L3_V[1]] * 2])
    P.append(dict(name='isle_w', paint='asphalt', poly=isle_w, table=flat(Z_L1), wall='concrete'))
    P.append(dict(name='isle_e', paint='asphalt', poly=isle_e, table=flat(Z_L2), wall='concrete'))
    P.append(dict(name='nrow', paint='asphalt', poly=nrow, table=flat(Z_L2), wall='concrete'))
    r = RAMP_NW
    P.append(dict(name='ramp_nw', paint='asphalt', poly=_rect(r['u'][0], r['u'][-1], *r['v']), table=_table_u(r['u'], r['z'], *r['v']),
                  wall='concrete', open=[LineString([(r['u'][0], r['v'][0] - 0.5), (r['u'][0], r['v'][1] + 0.5)])]))
    r = WALK_NW
    P.append(dict(name='walk_nw', paint='pavers', poly=_rect(r['u'][0], r['u'][-1], *r['v']), table=_table_u(r['u'], r['z'], *r['v']),
                  wall='concrete', open=[LineString([(r['u'][0], r['v'][0] - 0.5), (r['u'][0], r['v'][1] + 0.5)])]))
    r = RAMP_SE
    P.append(dict(name='ramp_se', paint='asphalt', poly=_rect(r['u'][0], r['u'][-1], *r['v']), table=_table_u(r['u'], r['z'], *r['v']),
                  wall='concrete', open=[LineString([(r['u'][0], r['v'][0] - 0.5), (r['u'][0], r['v'][1] + 0.5)])]))
    # 안 · 이비인후과병원 남쪽
    st = STAIR
    terrace = Polygon(Y_ARC + Y_EAST + [(st['u'][0], st['v'][1]), (st['u'][0], Y_ARC[0][1])])
    P.append(dict(name='terrace', paint='pavers', poly=terrace, table=([20.0, 34.0], [45.0, 68.0], [[Y_Z] * 2] * 2), wall='concrete'))
    # (the flight's walked slope: through the treads' noses, from one tread before the lowest riser to the highest riser,
    # level on to the terrace; under the risers' feet the walker's rays would meet each riser's back)
    tread = (st['v'][1] - st['v'][0]) / st['risers']
    P.append(dict(name='stair', paint='pavers', poly=_rect(st['u'][0], st['u'][1], st['v'][0] - tread, st['v'][1]), stairs=True,
                  table=([st['u'][0], st['u'][1]], [st['v'][0] - tread, st['v'][1] - tread, st['v'][1]],
                         [[st['z'][0]] * 2, [st['z'][1]] * 2, [st['z'][1]] * 2]), wall='concrete'))
    drive = Polygon(N1_WALL + [Y_ARC[2], Y_ARC[1], Y_ARC[0], (st['u'][0], Y_ARC[0][1]), (st['u'][0], st['v'][0]), (st['u'][1], st['v'][0]),
                               (st['u'][1], 47.6), (36.0, 47.6)] + N1_SE)
    P.append(dict(name='drive', paint='asphalt', poly=drive, table=(N1_US, N1_VS, N1_Z), wall='brick_red',
                  open=[LineString([(-17.5, 28.0), (-18.13, 40.7)]), LineString(N1_SE[4:]), LineString([(36.0, 36.0), (36.0, 48.0)]),
                        LineString(N1_SE[:4])]))
    for p in P:
        p['poly'] = shapely.geometry.polygon.orient(p['poly'].buffer(0), 1.0)
        p.setdefault('open', [])
    return P


PLATES = _plates()
PLATE = {p['name']: p for p in PLATES}


def plate_h(p, u, v):
    us, vs, Z = p['table']
    return _interp_rows(us, vs, Z, u, v)


def surface_uv(u, v, skip=None):
    """the highest raised surface at (u, v), or None"""
    q, z = Point(u, v), None
    for p in PLATES:
        if p is skip or not p['poly'].buffer(1e-6).contains(q):
            continue
        h = plate_h(p, u, v)
        z = h if z is None else max(z, h)
    return z


# parapets (난간벽: the dotted balustrades and the walls' heads in the scans): plate, line (u, v), height, thickness,
# material.  Along the plates' edges, inside them.  (A kerb the walker is to cross stays under the lowest of the web
# app's wall rays, 0.1 m: a box of faces taller than that turns him back, as a planter's edge does.)
PARAPETS = [
    ('court', [(T_U0 + 0.15, T_V0 + 0.15), (T_U0 + 0.15, T_V1 - 0.15)], 0.95, 0.3, 'concrete'),              # south-west
    ('court', [(T_U0 + 0.15, T_V1 - 0.15), (12.5, T_V1 - 0.15)], 0.95, 0.3, 'concrete'),                     # by the car ramp
    ('court', [(T_U0 + 0.15, T_V0 + 0.15), (13.5, T_V0 + 0.15)], 0.95, 0.3, 'concrete'),                     # by the second ramp
    ('walk_nw', [(-33.0, WALK_NW['v'][1] - 0.15), (33.0, WALK_NW['v'][1] - 0.15)], 1.0, 0.3, 'concrete'),    # the walk's outer wall
    ('walk_nw', [(-33.0, WALK_NW['v'][0] + 0.1), (17.5, WALK_NW['v'][0] + 0.1)], 0.18, 0.2, 'curb'),         # the planted strip's kerb
    ('ramp_se', [(-24.0, RAMP_SE['v'][0] + 0.15), (18.4, RAMP_SE['v'][0] + 0.15)], 0.9, 0.3, 'concrete'),    # over the planted strip
    ('court', [(18.4, L3_V[0] + 0.15), (33.0, L3_V[0] + 0.15)], 0.9, 0.3, 'concrete'),
    ('court', [(NROW[1] + 0.12, NROW[2]), (NROW[1] + 0.12, NROW[3])], 0.06, 0.24, 'curb'),                   # the row's kerb (the step under it 0.36 - 0.48 m)
    ('terrace', [(u + 0.16, v) for u, v in Y_ARC[:6]] + [(Y_ARC[6][0] + 0.16, Y_ARC[6][1]), (Y_ARC[7][0] + 0.13, Y_ARC[7][1] - 0.1),
                                                           (Y_ARC[8][0] + 0.1, Y_ARC[8][1] - 0.12), (Y_ARC[9][0] + 0.05, Y_ARC[9][1] - 0.15)],
     0.95, 0.3, 'concrete'),
    ('drive', [(-17.60, 40.69), (14.49, 50.34), (14.76, 53.64), (22.7, 53.64)], 0.9, 0.3, 'brick_red'),
    ('terrace', [(31.45, 50.4), (31.45, 55.8)], 0.95, 0.3, 'concrete'),                                      # (the link's side)
    ('stair', [(31.45, STAIR['v'][0] + 0.1), (31.45, STAIR['v'][1])], 0.9, 0.3, 'concrete'),
    ('isle_e', [(ISLE[1] + 0.2, ISLE[3] + 0.1), (ISLE[1] + 0.2, ISLE[4] - 0.1)], 0.5, 0.4, 'concrete'),      # the split's head
    # (the ramps' inner sides below the forecourt's corner: the scans' balustrades run on down to the ramps' feet)
    ('ramp_nw', [(-32.5, RAMP_NW['v'][0] + 0.15), (T_U0, RAMP_NW['v'][0] + 0.15)], 0.95, 0.3, 'concrete'),
    ('ramp_se', [(-30.0, RAMP_SE['v'][1] - 0.15), (T_U0, RAMP_SE['v'][1] - 0.15)], 0.95, 0.3, 'concrete'),
]

# ---------------------------------------------------------------------------------------------------------------------
# the ground round them (in u, v): the entrance road from 성산로's gate past the garden to the drive, the road along
# the hall's south-east side, their walks; the garden and the planted banks stay lawn
_TIP = [(-12.0 + 5.75 * math.cos(math.radians(a)), -35.75 + 5.75 * math.sin(math.radians(a))) for a in range(-90, -271, -20)]
ROAD_UV = Polygon(
    [(-62.0, -30.0), (-48.0, -30.0), (-43.0, -34.5), (-38.0, -40.0), (-32.0, -45.5), (-28.0, -47.3), (72.0, -47.3), (88.0, -41.5),
     (88.0, -34.5), (72.0, -41.5)] + _TIP + [(-33.5, -29.9), (-33.5, -26.6), (-34.0, -26.3), (-34.0, 13.0), (-33.5, 15.0), (-33.5, 18.9),
                                               (-34.5, 18.9), (-34.5, 23.9), (-35.5, 25.5), (-33.0, 28.3), (-25.0, 30.0), (-17.5, 30.9),
                                               (-18.13, 40.7), (-20.0, 38.3), (-27.0, 37.0), (-35.0, 34.5), (-40.0, 31.0), (-43.5, 25.5),
                                               (-44.4, 21.0), (-44.4, 5.0), (-48.3, -2.0), (-48.3, -19.0), (-52.5, -23.5), (-62.0, -23.5)])
# (the strip between the garden and the second ramp, 4 m, at the garden's level up to the forecourt's wall: in Kakao's
# roadview of August 2008 the wall's end there stands open between pillars -- a way in under the forecourt?  Not
# measured: the wall is drawn whole)
PAVE_UV = [_rect(-34.0, T_U0, -26.4, -22.0),
           _rect(-34.0, T_U0, 13.0, 15.0),                 # ... and under the car ramp's wall
           _rect(-12.0, 72.0, -41.5, -39.3)]               # the road's walk along the hall's side
# (the walk behind the stalls along the brick wall, 1.5 m: paving on the drive's plate)
_bw = LineString(N1_WALL[:2]).buffer(-1.9, single_sided=True).intersection(PLATE['drive']['poly'])
PAVE_UV.append(max(getattr(_bw, 'geoms', [_bw]), key=lambda g_: g_.area))
GARDEN_UV = _rect(-34.0, T_U0, -22.0, 13.0)
BANK_UV = _rect(-17.0, 72.0, -39.3, -30.0)                 # the planted strip between the second ramp's wall and the road
CLEAR_UV = unary_union([
    _rect(-49.0, 34.0, -48.3, 26.0), _rect(-53.0, -48.0, -22.0, 6.0), _rect(33.0, 72.0, -48.3, -34.0), Polygon([(72.0, -48.3), (89.0, -42.5), (89.0, -33.5), (72.0, -34.0)]),
    _rect(-63.0, -48.0, -31.0, -12.0),
    Polygon([(-50.0, 24.0), (-50.0, 33.0), (-42.0, 42.0), (-30.0, 48.0), (-18.0, 48.0), (-10.0, 49.0), (-2.0, 54.5), (2.0, 56.0),
             (14.0, 55.0), (22.4, 54.6), (21.2, 57.5), (21.3, 61.2), (22.8, 64.4), (25.2, 67.3), (27.0, 67.0), (33.0, 57.0),
             (36.5, 57.0), (36.5, 24.0)]),
    # (today's drive out of the car park north-west of the brick wall: the wall stood between them)
    Polygon([tuple(float(c_) for c_ in uv(x_, y_)) for x_, y_ in LineString([(-17.5, -306.0), (-15.0, -313.0), (-6.0, -320.0),
                                                                             (-3.0, -322.0)]).buffer(4.5).exterior.coords]),
    # (today's drive from 성산로 up to the roundabout, east of the 1997 gate: no way in there in the scans)
    Polygon([tuple(float(c_) for c_ in uv(x_, y_)) for x_, y_ in LineString([(52.5, -414.5), (48.0, -412.0), (47.0, -410.0), (44.0, -405.0), (42.0, -403.0),
                                                  (42.0, -398.0)]).buffer(5.0).exterior.coords])])
# trees of the 1997 scans (crowns in two frames or more): the garden, the bank's row, the slope north of the walk
TREE_UV = [(-30.3, -16.0), (-27.5, -9.5), (-30.0, -4.5), (-25.5, -12.5), (-21.5, -19.0), (-29.0, 7.5), (-25.0, 3.5), (-22.5, 9.5),
           (-20.0, 2.0), (-19.5, -6.0), (-24.5, -17.0),
           (-9.0, -35.0), (-5.0, -35.6), (-1.0, -35.0), (3.0, -35.6), (7.0, -35.0), (11.0, -35.6), (15.0, -35.0), (19.0, -35.6),
           (23.0, -35.0), (-12.5, -36.2),
           (-6.0, 27.2), (0.0, 28.4), (5.0, 29.8), (-12.0, 26.6), (9.0, 26.4)]
# the hall's low front block and its round-ended wing (halls(): at the halls' end), the hall's own floors
HEAD_HALL = dict(id=990045, levels=1, base=datum.up(63.11, -315.57, 37.65), uv=[(HEAD[0], HEAD[2]), (HEAD[1], HEAD[2]), (HEAD[1], HEAD[3]), (HEAD[0], HEAD[3])],
                 door=((HEAD[0], -0.25), (-1.0, 0.0)))     # base: the drive before it (u 22.4, v 0)
WING_HALL = dict(id=990046, levels=3, base=WING['base'],   # base: the drive along its north-west wall (u 20, v 35.2)
                 uv=[(WING['u'][1], WING['v'][0]), (WING['u'][1], WING['v'][1]), (WING['u'][0], WING['v'][1])] +
                    [(WING['u'][0] + 3.4 * math.cos(math.radians(a)), 31.8 + 3.4 * math.sin(math.radians(a))) for a in range(110, 251, 20)] +
                    [(WING['u'][0], WING['v'][0])])
# 외래진료소's third floor (base + 2 x 3.6 = 38.02) level with the walk's head (u 31.6, v 21.4)
CLINIC_BASE = datum.up(63.11, -315.57, 30.82)
CLINIC_DOOR = (31.7, 21.4)     # (u, v): at the walk's head, on the hall's south-west face
# the ground the 1997 scans have round them, on the game's 5 m nodes (x, y, z): the median of the photo points within
# 3 m of each (two pairs or more within 0.5 m; a car's roof or a crown, 0.9 m over the lowest third round it, dropped)
GROUND_PTS = datum.up3([
    (-10, -345, 30.63), (-20, -350, 30.51), (-25, -355, 31.08), (-20, -355, 30.45), (-20, -360, 30.26),
    (0, -360, 30.52), (-20, -365, 30.13), (-10, -365, 30.17), (-5, -365, 30.31), (0, -365, 30.41), (75, -365, 30.66),
    (80, -365, 30.62), (-10, -370, 29.76), (-5, -370, 29.84), (0, -370, 30.34), (5, -370, 30.3), (60, -370, 30.45),
    (80, -370, 30.54), (-10, -375, 29.74), (0, -375, 29.56), (5, -375, 30.12), (10, -375, 30.15), (55, -375, 30.31),
    (60, -375, 30.29), (65, -375, 30.28), (70, -375, 30.33), (75, -375, 30.66), (80, -375, 30.72), (-5, -380, 29.27),
    (0, -380, 29.36), (5, -380, 29.31), (10, -380, 29.45), (60, -380, 30.12), (65, -380, 30.18), (70, -380, 30.47),
    (5, -385, 29.06), (10, -385, 29.18), (20, -385, 29.96), (25, -385, 30.24), (45, -385, 30.03), (60, -385, 30.02),
    (5, -390, 28.97), (10, -390, 28.93), (15, -390, 29.25), (20, -390, 29.76), (40, -390, 30.08), (45, -390, 29.91),
    (50, -390, 29.72), (55, -390, 29.94), (60, -390, 30.21), (-10, -395, 29.87), (5, -395, 28.67), (10, -395, 28.72),
    (15, -395, 28.92), (25, -395, 29.23), (30, -395, 29.38), (35, -395, 29.56), (40, -395, 29.79), (45, -395, 29.64),
    (50, -395, 29.7), (55, -395, 30.0), (10, -400, 28.69), (15, -400, 28.72), (20, -400, 29.28), (25, -400, 29.22),
    (30, -400, 29.36), (35, -400, 29.49), (50, -400, 29.88), (15, -405, 28.6), (20, -405, 28.68), (25, -405, 28.82),
    (30, -405, 29.02), (35, -405, 29.11), (-5, -410, 27.73), (0, -410, 27.55), (15, -410, 28.91), (20, -410, 28.85),
    (25, -410, 28.92), (30, -410, 28.99), (35, -410, 29.23), (0, -415, 27.46),
    # (the car park south-west of the entrance road, its east edge: the ground there stands 2.4 - 3.9 m over the game's)
    (-20, -395, 29.13), (-15, -395, 28.71), (-15, -400, 28.72), (-10, -400, 29.19)])
# where the game's ground is eased into the photos' (harmonic): 10 m round what is drawn again, and west of the
# entrance road as far as the wooded knoll (the scans have that ground 1 - 2.5 m over the game's too)
WEST_EASE_UV = _rect(-80.0, -49.0, -52.0, 42.0)
# north-west of the brick wall and the terrace's rim the car park's level stays (28 - 29 m in the scans and the game)
NW_KEEP_UV = Polygon([(-18.5, 41.1), (13.9, 50.85), (14.2, 54.2), (22.0, 54.2), (21.5, 57.0), (21.5, 60.5), (22.0, 62.5), (23.2, 64.2),
                      (25.0, 67.0), (20.0, 90.0), (-40.0, 90.0), (-40.0, 41.1)])
N_BANK_UV = Polygon([(-34.0, 24.4), (33.5, 24.4), (33.5, 28.4), (13.4, 28.4), (10.0, 31.8), (10.2, 33.4), (0.0, 32.2), (-17.5, 30.9),
                     (-25.0, 30.0), (-33.0, 28.3), (-35.5, 25.5)])
# the drive's run on south-west of its plate to the entrance road: the road, three stalls on its north-west side and
# a paved apron, level ground in the scans (30.4 - 30.7 m in four windows; under the crowns beyond it the bank down
# to the car park).  SW_RUN_Z @ (u -32, v 32): from there up to the plate's own height at its end (u -17.5)
SW_RUN_UV = Polygon([(-17.5, 30.9), (-18.13, 40.7), (-21.0, 40.6), (-31.5, 39.5), (-37.0, 37.0), (-42.5, 29.0), (-35.5, 25.5),
                     (-33.0, 28.3), (-25.0, 30.0)])
SW_RUN_Z = datum.up(*xy(-32.0, 32.0), 30.52)


def _wall_line():
    return LineString(N1_WALL + [Y_ARC[2], Y_ARC[1], Y_ARC[0]])


def grade(Hn, X, Y, FIXED, halls_keep, fill, road_ls, road_hw, step=5.0, half=800.0):
    """The ground round the forecourt on the photos' heights (GROUND_PTS), the slope north
    of the walk on the drive's, the rest of what is drawn again (CLEAR_UV + 10 m, WEST_EASE_UV) one
    smooth surface between them and the ground as it was (fill: build_campus.py harmonic_fill).  Under the raised
    surfaces the ground runs on low (they are meshes over it: build), but under the drive, which lies on it past
    6 m from its wall.  성산로's bed (road_ls, road_hw + 2.5 m), the halls' feet (halls_keep: 7 m round them, the insides of the two the
    surfaces stand against) and what another
    rule set (FIXED) stay.  Returns the nodes set (to be FIXED) and a summary."""
    H0 = Hn.copy()
    U, V = uv(X, Y)
    pts = shapely.points(np.stack([X.ravel(), Y.ravel()], 1))
    inside = lambda poly_uv: shapely.contains_xy(poly_uv, U, V)
    region = inside(CLEAR_UV.buffer(10.0)) | inside(WEST_EASE_UV)
    on_road = (shapely.distance(pts, road_ls) <= road_hw + 2.5).reshape(X.shape)
    mine = taken_xy(1.0)                                          # (the two halls the surfaces stand against: their insides only)
    in_hall = shapely.contains_xy(unary_union([h.buffer(-0.5 if h.intersects(mine) else 7.0) for h in halls_keep]), X, Y)
    keep = FIXED | on_road | in_hall | inside(NW_KEEP_UV)
    ctrl = np.zeros(X.shape, bool)
    for x, y, z in GROUND_PTS:
        j, i = int(round((y + half) / step)), int(round((x + half) / step))
        if region[j, i] and not keep[j, i]:
            Hn[j, i] = z
            ctrl[j, i] = True
    drive, wall = PLATE['drive'], _wall_line()
    n_drive = n_slope = 0
    for j, i in zip(*np.nonzero(region & ~keep & ~ctrl)):
        u, v = float(U[j, i]), float(V[j, i])
        q = Point(u, v)
        if drive['poly'].contains(q):
            if wall.distance(q) <= 6.0:
                continue
            Hn[j, i] = plate_h(drive, u, v) - 0.3
            n_drive += 1
        elif N_BANK_UV.contains(q) or (34.0 <= u <= 46.0 and 36.9 <= v <= 47.6):
            # the slope under the trees north of the walk, the gap by the wing, and the drive's run on under the link
            Hn[j, i] = plate_h(drive, max(u, -17.5), max(v, 31.0)) - (0.4 if u < 34.0 else 0.05)
            n_slope += 1
        elif SW_RUN_UV.contains(q):
            Hn[j, i] = SW_RUN_Z + min(1.0, max(0.0, (u + 32.0) / 14.5)) * (plate_h(drive, -17.5, v) - SW_RUN_Z)
            n_drive += 1
        else:
            continue
        ctrl[j, i] = True
    free = region & ~ctrl & ~keep
    if free.any():
        fill(free)
    d = Hn - H0
    info = dict(points=int(ctrl.sum()), drive=n_drive, slope=n_slope, eased=int(free.sum()),
                moved=int((np.abs(d) > 0.05).sum()), most=(round(float(d.min()), 1), round(float(d.max()), 1)))
    return ctrl | free, info


def paint():
    """for the game's map: (cleared to lawn, asphalt, paving) in campus metres.  Today's walks, drives and roundabout
    go; the entrance road, the road along the hall's side, the forecourt, the ramps and the drive are asphalt; the
    walks, the terrace and its flight paving"""
    asph = [ROAD_UV] + [p['poly'] for p in PLATES if p['paint'] == 'asphalt']
    pave = list(PAVE_UV) + [p['poly'] for p in PLATES if p['paint'] == 'pavers']
    return ([_to_xy(g) for g in (CLEAR_UV.geoms if hasattr(CLEAR_UV, 'geoms') else [CLEAR_UV])], [_to_xy(g) for g in asph],
            [_to_xy(g) for g in pave])


def taken_xy(pad=0.0):
    """what is paved or built again (campus metres): no tree, shrub or prop of the game's stays on it"""
    gs = [ROAD_UV] + list(PAVE_UV) + [p['poly'] for p in PLATES] + [Polygon(HEAD_HALL['uv']), Polygon(WING_HALL['uv']).buffer(0)]
    return unary_union([_to_xy(g).buffer(pad) for g in gs])


def move_off(trees, shrubs, props, halls):
    """the game's trees on what is paved or built again go, each in its place in the list, to a tree of the 1997
    scans that has none yet (TREE_UV: the garden, the planted bank, the slope north of the walk); the shrubs and props
    there go.  The scans' trees left without one are planted at the trees' end (TREE_UV: crowns in two frames or
    more; their kinds are not read: a row of 느티나무 along the second ramp's wall, young ones in the garden and on the
    slope).  Returns (trees moved, shrubs gone, props gone, trees left on it, trees added)."""
    tk = taken_xy(0.8)
    shapely.prepare(tk)
    hb = unary_union([h.buffer(1.5) for h in halls])
    spots = [Point(*xy(u, v)) for u, v in TREE_UV]
    region = _to_xy(CLEAR_UV).buffer(4.0)
    stay = [Point(t[1], t[2]) for t in trees if region.contains(Point(t[1], t[2])) and not tk.contains(Point(t[1], t[2]))]
    spots = [s for s in spots if all(s.distance(o) > 3.0 for o in stay) and not hb.contains(s)]
    moved = []
    for t in trees:
        q = Point(t[1], t[2])
        if not tk.contains(q) or not spots:
            continue
        s = min(spots, key=q.distance)
        spots.remove(s)
        moved.append((t[0], t[1], t[2], round(s.x, 2), round(s.y, 2)))
        t[1], t[2] = round(s.x, 2), round(s.y, 2)
    left = sum(1 for t in trees if tk.contains(Point(t[1], t[2])))
    rnd = random.Random(19970728)
    added = []
    for s in spots:
        row = float(uv(s.x, s.y)[1]) < -30.0                      # (the row at the foot of the second ramp's wall)
        added.append(['zelkova' if row else 'zelkova_young', round(s.x, 2), round(s.y, 2),
                      round(rnd.uniform(0.55, 0.68) if row else rnd.uniform(0.85, 1.05), 2), round(rnd.uniform(0, 6.28), 2)])
    trees.extend(added)
    ns, npr = len(shrubs), len(props)
    shrubs[:] = [s for s in shrubs if not tk.contains(Point(s[1], s[2]))]
    props[:] = [p for p in props if not tk.contains(Point(p[1], p[2]))]
    return moved, ns - len(shrubs), npr - len(props), left, added


def halls():
    """외래진료소's low front block and its round-ended wing as the 1997 scans have them (three and six pairs on each
    roof): for the halls' end (blender/build.py draws each hall's looks in its order).  Flat roofs at 42.1 and 44.0 m"""
    out = []
    for h in (HEAD_HALL, WING_HALL):
        poly = shapely.geometry.polygon.orient(Polygon([xy(u, v) for u, v in h['uv']]).buffer(0), 1.0)
        hgt = round(h['levels'] * 3.6 + 1.2, 2) if h is HEAD_HALL else round(WING['z'] - WING['base'], 2)
        b = dict(id=h['id'], name='외래진료소', style='white', levels=h['levels'], height=hgt, base=h['base'],
                 top_ground=round(h['base'] + 0.5, 2), footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]])
        if h is WING_HALL:               # (blender/generic.py: the roof's parapet 0.9 m over the top floor's ceiling)
            b['fh'] = round((WING['z'] - 0.9 - WING['base']) / h['levels'], 3)
        if 'door' in h:
            (du, dv), (nu, nv) = h['door']
            p, n = xy(du, dv), (nu * _C - nv * _S, nu * _S + nv * _C)
            b['entry'] = dict(p=[round(p[0], 2), round(p[1], 2)], n=[round(n[0], 4), round(n[1], 4)], floor=0)
        out.append(b)
    return out


# ---------------------------------------------------------------------------------------------------------------------
# the meshes (blender/landmarks.py med_west draws them as they come)
def _terrain(Hn, half, step):
    """the ground as the web app draws it: each 5 m cell two triangles split along (i+1, j)-(i, j+1)"""
    def g(x, y):
        fx, fy = (x + half) / step, (y + half) / step
        i, j = int(math.floor(fx)), int(math.floor(fy))
        ax, ay = fx - i, fy - j
        a, b, c, d = Hn[j, i], Hn[j, i + 1], Hn[j + 1, i], Hn[j + 1, i + 1]
        return float(a + (b - a) * ax + (c - a) * ay if ax + ay <= 1 else d + (c - d) * (1 - ax) + (b - d) * (1 - ay))
    return g


def _lattice(us, lo, hi, pitch=2.5):
    """lines: the table's own (its kinks) and others no more than pitch apart, over lo .. hi"""
    ks = sorted({round(float(lo), 4), round(float(hi), 4)} | {round(float(u), 4) for u in us if lo < u < hi})
    out = []
    for a, b in zip(ks, ks[1:]):
        n = max(1, int(math.ceil((b - a) / pitch - 1e-9)))
        out += [a + (b - a) * k / n for k in range(n)]
    return out + [ks[-1]]


def _dive(p, u, v):
    """a plate's height, run 0.3 m down into the ground over the last 1.5 m before an open edge"""
    z = plate_h(p, u, v)
    if p['open']:
        d = min(ln.distance(Point(u, v)) for ln in p['open'])
        if d < 1.5:
            z -= 0.3 * (1.0 - d / 1.5)
    return z


def build(Hn, half, step, halls=()):
    """dict for campus.json `med_west`: plates (for blender/common.py ground: the ground on a raised surface is that
    surface), top (the surfaces: drawn as the ground is, walked on), walk (walked on only: the flight's slope),
    quads ([material, four points]: the walls down to what lies beside each surface, the parapets, the flight's steps)"""
    ground = _terrain(Hn, half, step)
    hb = unary_union([h.buffer(-0.3) for h in halls] + [_to_xy(Polygon(h['uv']).buffer(0)).buffer(0.3) for h in (HEAD_HALL, WING_HALL)])
    V, F, walk, quads = {}, [], [], []

    def vid(x, y, z):
        return V.setdefault((round(x, 3), round(y, 3), round(z, 3)), len(V))

    def P3(p, u, v):
        x, y = xy(u, v)
        return (round(x, 3), round(y, 3), round(_dive(p, u, v), 3))

    for p in PLATES:
        u0, v0, u1, v1 = p['poly'].bounds
        us, vs, _ = p['table']
        lu, lv = _lattice(us, u0, u1), _lattice(vs, v0, v1)
        for a0, a1 in zip(lu, lu[1:]):
            for b0, b1 in zip(lv, lv[1:]):
                pc = shapely.geometry.box(a0, b0, a1, b1).intersection(p['poly'])
                for g in (pc.geoms if hasattr(pc, 'geoms') else [pc]):
                    if g.geom_type != 'Polygon' or g.area < 1e-3:
                        continue
                    ring = list(shapely.geometry.polygon.orient(g, 1.0).exterior.coords)[:-1]
                    if len(ring) == 3:
                        tris = [ring]
                    elif len(ring) == 4 and g.convex_hull.area - g.area < 1e-6 and not g.interiors:
                        tris = [ring[:3], [ring[0], ring[2], ring[3]]]
                    else:
                        tris = [list(shapely.geometry.polygon.orient(t, 1.0).exterior.coords)[:3] for t in triangulate(g)
                                if g.buffer(1e-6).contains(t.representative_point())]
                    for t in tris:
                        q = [P3(p, u, v) for u, v in t]
                        if Polygon([c[:2] for c in q]).area < 1e-4:
                            continue
                        if p.get('stairs'):
                            walk.append([list(c) for c in q])
                        else:
                            F.append([vid(*c) for c in q])
        # the walls: along the plate's outline, from its surface down to what lies beside it there
        for ring in [p['poly'].exterior] + list(p['poly'].interiors):
            cs = list(shapely.segmentize(ring, 1.25).coords)
            ccw = ring.is_ccw
            if ring is p['poly'].exterior and not ccw:
                cs = cs[::-1]
            if ring is not p['poly'].exterior and ccw:
                cs = cs[::-1]                                     # (a hole runs clockwise: its outside is inside it)
            for (ua, va), (ub, vb) in zip(cs, cs[1:]):
                L = math.hypot(ub - ua, vb - va)
                if L < 1e-6:
                    continue
                nu, nv = (vb - va) / L, -(ub - ua) / L            # (outwards: to the right going round)
                if hb.contains(Point(*xy((ua + ub) / 2 + nu * 0.4, (va + vb) / 2 + nv * 0.4))):
                    continue                                      # (against a hall's wall)
                bot = []
                for u, v in ((ua, va), (ub, vb)):
                    zo = surface_uv(u + nu * 0.12, v + nv * 0.12, skip=p)
                    bot.append(zo if zo is not None else ground(*xy(u + nu * 0.12, v + nv * 0.12)) - 0.3)
                za, zb = _dive(p, ua, va), _dive(p, ub, vb)
                if max(za - bot[0], zb - bot[1]) < 0.04:
                    continue
                mat = p['wall']
                if p['name'] == 'drive' and LineString(N1_WALL).distance(Point((ua + ub) / 2, (va + vb) / 2)) > 0.5:
                    mat = 'concrete'
                (xa, ya), (xb, yb) = xy(ua, va), xy(ub, vb)
                quads.append([mat, [[round(xa, 3), round(ya, 3), round(min(bot[0], za), 3)], [round(xb, 3), round(yb, 3), round(min(bot[1], zb), 3)],
                                    [round(xb, 3), round(yb, 3), round(zb, 3)], [round(xa, 3), round(ya, 3), round(za, 3)]]])
    # the parapets: a wall t thick on the surface along each line (its outer face over the wall under it)
    for nm, line, hgt, t, mat in PARAPETS:
        p = PLATE[nm]
        cs = list(shapely.segmentize(LineString(line), 1.25).coords)

        def A(q, dz, p_=p):
            x, y = xy(*q)
            return [round(x, 3), round(y, 3), round(plate_h(p_, *q) + dz, 3)]
        for k, ((ua, va), (ub, vb)) in enumerate(zip(cs, cs[1:])):
            L = math.hypot(ub - ua, vb - va)
            lu, lv = -(vb - va) / L * t / 2, (ub - ua) / L * t / 2          # (half the thickness, to the left)
            aL, aR, bL, bR = (ua + lu, va + lv), (ua - lu, va - lv), (ub + lu, vb + lv), (ub - lu, vb - lv)
            quads.append([mat, [A(aR, -0.05), A(bR, -0.05), A(bR, hgt), A(aR, hgt)]])          # right face
            quads.append([mat, [A(bL, -0.05), A(aL, -0.05), A(aL, hgt), A(bL, hgt)]])          # left face
            quads.append([mat, [A(aR, hgt), A(bR, hgt), A(bL, hgt), A(aL, hgt)]])              # top
            if k == 0:
                quads.append([mat, [A(aL, -0.05), A(aR, -0.05), A(aR, hgt), A(aL, hgt)]])
            if k == len(cs) - 2:
                quads.append([mat, [A(bR, -0.05), A(bL, -0.05), A(bL, hgt), A(bR, hgt)]])
    # the flight: risers and treads across its width, the lowest riser at its foot
    st = STAIR
    n = st['risers']
    rise, tread = (st['z'][1] - st['z'][0]) / n, (st['v'][1] - st['v'][0]) / n

    def S(u, v, z):
        x, y = xy(u, v)
        return [round(x, 3), round(y, 3), round(z, 3)]
    for k in range(n):
        vk, z0_, z1_ = st['v'][0] + k * tread, st['z'][0] + k * rise, st['z'][0] + (k + 1) * rise
        quads.append(['stone_granite', [S(st['u'][0], vk, z0_), S(st['u'][1], vk, z0_), S(st['u'][1], vk, z1_), S(st['u'][0], vk, z1_)]])
        quads.append(['stone_granite', [S(st['u'][0], vk, z1_), S(st['u'][1], vk, z1_), S(st['u'][1], vk + tread, z1_), S(st['u'][0], vk + tread, z1_)]])
    plates = []
    for p in PLATES:
        us, vs, Z = p['table']
        plates.append(dict(name=p['name'], poly=[[round(c, 3) for c in xy(u, v)] for u, v in list(p['poly'].exterior.coords)[:-1]],
                           holes=[[[round(c, 3) for c in xy(u, v)] for u, v in list(r.coords)[:-1]] for r in p['poly'].interiors],
                           us=[round(float(u), 3) for u in us], vs=[round(float(v), 3) for v in vs], z=[[round(float(z), 3) for z in row] for row in Z]))
    vs_ = sorted(V, key=V.get)
    return dict(o=list(O), ang=ANG, plates=plates, top=dict(v=[list(v) for v in vs_], f=F), walk=walk, quads=quads)


# ---------------------------------------------------------------------------------------------------------------------
def walks(paths):
    """the walks the game reads (the minimap): today's inside what is drawn again go (one that runs on out of it keeps
    its longest stretch outside, 8 m or more), the 1997 ones come.  In place; returns (cut, gone, added)"""
    clear = _to_xy(CLEAR_UV)
    shapely.prepare(clear)
    cut = gone = 0
    for p in list(paths):
        if len(p['pts']) < 2:
            continue
        ls = LineString([q[:2] for q in p['pts']])
        if not ls.intersects(clear):
            continue
        rest = ls.difference(clear)
        parts = [g for g in (rest.geoms if hasattr(rest, 'geoms') else [rest]) if g.geom_type == 'LineString' and g.length >= 8.0]
        if not parts:
            paths.remove(p)
            gone += 1
            continue
        g = max(parts, key=lambda g_: g_.length)
        if g.length < ls.length - 0.05:
            p['pts'] = [[round(x, 1), round(y, 1)] for x, y in g.coords]
            cut += 1

    def L(kind, w, pts):
        return dict(kind=kind, w=w, pts=[[round(c, 1) for c in xy(u, v)] for u, v in pts])
    new = [L('service', 6.0, [(-62.0, -26.8), (-48.0, -26.8), (-41.0, -20.0), (-39.5, 0.0), (-39.5, 22.0), (-37.5, 28.0), (-30.0, 32.5),
                              (-17.5, 34.5), (0.0, 36.5), (14.0, 39.0), (28.0, 40.5), (36.0, 41.5)]),
           L('service', 6.0, [(-41.0, -24.0), (-36.0, -35.0), (-28.0, -43.5), (-14.0, -44.4), (72.0, -44.4), (88.0, -38.0)]),
           L('service', 4.0, [(-36.0, 17.0), (14.0, 17.0), (22.0, 16.0), (26.0, 8.0), (26.0, -20.0), (22.0, -27.5), (14.0, -28.2),
                              (-34.0, -28.2)]),
           L('service', 5.0, [(9.5, 11.5), (9.5, -22.0), (-8.3, -22.0), (-8.3, 11.5), (9.5, 11.5)]),
           L('footway', 3.0, [(-36.0, 21.4), (31.5, 21.4)]),
           L('footway', 3.0, [(28.5, 39.5), (28.5, 47.2)]),
           L('steps', 6.0, [(28.5, 47.2), (28.5, 50.3)]),
           L('footway', 3.0, [(28.5, 50.3), (28.5, 58.0)])]
    paths.extend(new)
    return cut, gone, len(new)


def zebra():
    """the crossings' bars (campus.json road_paint lines, white): on the drive before the terrace's flight (seven,
    level in three frames), across the entrance road at the walk's foot (six) and across the road along the hall's side"""
    out = []

    def bar(a, b, w):
        out.append(dict(kind='white', w=w, pts=[[round(c, 2) for c in xy(*a)], [round(c, 2) for c in xy(*b)]]))
    for v in (39.7, 40.55, 41.45, 42.3, 43.25, 44.1, 45.1):
        bar((25.3, v), (31.3, v), 0.5)
    for u in (-42.2, -41.0, -39.7, -38.4, -37.1, -35.9):
        bar((u, 21.3), (u, 24.3), 0.6)
    for v in (-42.5, -43.4, -44.3, -45.2, -46.1, -47.0):
        bar((-13.4, v), (-10.9, v), 0.5)
    return out


# the forecourt's rows (cars97_new.json 「외래진료소 서쪽 데크 주차장」: the stalls' pitch 2.34 m from the cars themselves):
# row's middle line u, the stalls' ends in u
ROWS = [(-14.15, (-16.5, -11.8)), (-2.85, (-5.3, -0.4)), (3.5, (1.2, 6.1)), (15.3, (13.0, 17.9))]


def snap_cars(cars):
    """the forecourt's cars as read (x, y, heading deg, size, shade, ...) put on their rows' middle lines, heads
    square to the row (the reading's rows ran 1 degree off the forecourt's own frame, 0.3 - 1.2 m off the stalls)"""
    out = []
    for c in cars:
        u, v = (float(q) for q in uv(c[0], c[1]))
        uc = min(ROWS, key=lambda r: abs(r[0] - u))[0]
        hd = (c[2] - ANG) % 360.0
        hd = 0.0 if (hd < 90.0 or hd > 270.0) else 180.0
        x, y = xy(uc, v)
        out.append([round(x, 2), round(y, 2), round((hd + ANG + 180.0) % 360.0 - 180.0, 1)] + list(c[3:5]))
    return out


def stall_lines(cars):
    """white lines for the rows' stalls (the scans have each row boxed and a line between the cars), from the cars'
    own places (after snap_cars): [[x0, y0, x1, y1]]"""
    lines = []
    for uc, (ua, ub) in ROWS:
        vs = sorted(float(uv(c[0], c[1])[1]) for c in cars if abs(float(uv(c[0], c[1])[0]) - uc) < 0.6)
        if len(vs) < 2:
            continue
        pitch = float(np.median(np.diff(vs)))
        pitch = pitch if 2.0 < pitch < 2.7 else 2.34
        edges = [vs[0] - pitch / 2]
        for a, b in zip(vs, vs[1:]):
            k = max(1, int(round((b - a) / pitch)))
            edges += [a + (b - a) * (m + 0.5) / k for m in range(k)]
        edges.append(vs[-1] + pitch / 2)
        for v in edges:
            lines.append([*(round(c, 2) for c in xy(ua, v)), *(round(c, 2) for c in xy(ub, v))])
        for u in (ua, ub):
            lines.append([*(round(c, 2) for c in xy(u, edges[0])), *(round(c, 2) for c in xy(u, edges[-1]))])
    return lines
