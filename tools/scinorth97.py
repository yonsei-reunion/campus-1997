"""과학관 북쪽 길 · 연구관 서쪽 마당 · 과학관 서쪽 길 가의 1997년 땅과 포장 (#152; reference/고증/2.10_세운_차.md 「과학관 북쪽
길 · 연구관 서쪽 마당」, 3.10 「북쪽 길」, 3.15-3.17 「연구관」).  tools/build_campus.py 가 부른다.

    took, info = scinorth97.grade(Hn, X, Y, FIXED, keep, fill)   # 심기가 끝난 뒤(과학관 남쪽 공터 블록 다음, 북서쪽 골짜기 앞)
    scinorth97.paint()                                            # 아스팔트 다각형
    scinorth97.move_off(trees, shrubs, props, halls)              # 새 포장 위의 것을 가장자리로(목록 제자리), 세운 차를 넣기 전에

Frames: campus metres, x east, y north.  Every absolute height here is 해발; the build lays the ground on its working
datum (해발 + datum.tilt) and takes the tilt out where it writes the ground.

What the game had (the 5 m grid from the elevation model, the 연구관 yard levelled flat in jk_grade):
- the road north of 과학관's east wing at 53 - 56 m in its middle, 4 - 4.6 m over the 1997 road, OSM's 6 m asphalt
  along the wall and lawn north of it;
- the yard west of 연구관 flat at 48.3 m out to 16 m from the bar's middle line, the cars' rows on a lawn strip
  between a road and a strip of pavers along the bar.
What the scans have (1997-07-28 26/15 · 26/16, the only frames here, with the leafless 1996-12-23 pair, 1998-10-08
26/15 · 26/16 · 26/17 and 1999-05-31 26/16 · 26/17 · 27/16 · 27/17; each pair by itself, 1.5 m windows, corr 0.8 or
more; each pair's heights taken to 1997's by its median offset on the common points, then +BIAS):
- ROAD (SCI frame, u along the wing east-south-east from its south-east corner, v out of its north face): lined bays
  for parking along both sides (white lines in 1997, 1998 and 1999), the road between, a steep wooded cut bank on
  its north side.  Its height ROAD_Z along u (at v ROAD_V0) with ROAD_CROSS per metre of v: 657 points from seven
  pairs, rms 0.48 m (one pair's point); each year's points within 0.2 m of the other years' profile
- YARD (JK frame of build_campus.py: u along 연구관's bar north-north-east, v out of its west face): one sheet of
  asphalt from the planted bed before 과학관's east end to the trees along the bar, rising to the north-north-east
  and to the west, and on as the road north-north-east past the bar's north block to 광복관's bench (tools/
  kwangbok97.py REGION, which stays): YARD_PLANE, 186 points where two flights agree within 0.4 m, rms 0.30 m.
The 1:5000 survey's spots round it (2006 · 2024 on the roads south and west of 과학관) and the 과학관 court (50.2 m)
read the 1997 pair 0.1 - 0.45 m low: BIAS, as tools/gymnorth97.py.

Laid: the nodes in GROUND (the yard and the bed before 과학관's east end) on the plane, those in ROAD on its profile,
from the profile to the plane over JOIN_U m where the road comes round the wing's end; the nodes inside 과학관 within
HALL_IN m of its north face and of its east end, and inside 연구관 within HALL_IN m of its west faces, on the height at
the face (the walls' feet clean: the halls' floors stand under the ground on these sides); the nodes of the cells
under the 1997 cars (car_cells) on their place's surface; RING m round them filled smoothly, but for `keep` (the other
blocks' ground and the halls' feet), the cut bank north of the road (as it was: steep, as the leafless 1996 pair has
it, 54 m 4 m off the road's edge, 56 m at 6 m), the terrace east of 연구관's line and the road on south past the bar's
end.  Nothing here draws from build_campus.py's `rng`.
"""
import math

import numpy as np
import shapely
from shapely.geometry import Point, Polygon
from shapely.ops import nearest_points, unary_union

import datum

BIAS = 0.25
# --- frames (as build_campus.py SCI and JK_O / JK_A / JK_V)
SC_O = np.array([-218.78, 7.32]); _sa = math.radians(-15.06)
SC_T = np.array([math.cos(_sa), math.sin(_sa)]); SC_N = np.array([-SC_T[1], SC_T[0]])
JK_O = np.array([-179.75, 15.0]); _ja = math.radians(63.4)
JK_A = np.array([math.cos(_ja), math.sin(_ja)]); JK_V = np.array([-math.sin(_ja), math.cos(_ja)])
SCI_ID, JK_ID, JK_N_ID = 222843398, 990010, 990014


def sc(u, v):
    return tuple(round(float(c), 2) for c in SC_O + SC_T * u + SC_N * v)


def jk(u, v):
    return tuple(round(float(c), 2) for c in JK_O + JK_A * u + JK_V * v)


def sc_xy(u, v):
    u, v = np.asarray(u, float), np.asarray(v, float)
    return SC_O[0] + SC_T[0] * u + SC_N[0] * v, SC_O[1] + SC_T[1] * u + SC_N[1] * v


def sc_uv(x, y):
    dx, dy = np.asarray(x, float) - SC_O[0], np.asarray(y, float) - SC_O[1]
    return dx * SC_T[0] + dy * SC_T[1], dx * SC_N[0] + dy * SC_N[1]


def jk_uv(x, y):
    dx, dy = np.asarray(x, float) - JK_O[0], np.asarray(y, float) - JK_O[1]
    return dx * JK_A[0] + dy * JK_A[1], dx * JK_V[0] + dy * JK_V[1]


# --- the yard west of 연구관 and the road on north-north-east (JK frame): from the bar's west face (v 5) and the north
# block's (v 8.5) to the planted bed before 과학관's east end (v 23.3, u -26 .. -3.5: the yard's west edge) and the wood's
# edge round the curve to the north road and along the road on (the cars there stand at that edge); south to u -26 (the
# trees at the bar's south end and the road on south past 과학관's east end); north-north-east to 광복관's bench
# (kwangbok97.REGION from u 34).  YARD is its asphalt; GROUND also the bed, out to 과학관's east face
YARD = Polygon([jk(-26, 6), jk(20, 6), jk(20, 9.5), jk(34, 9.5), jk(34, 20.2), jk(30, 20.3), jk(22, 21.0), jk(16, 23.3),
                jk(12, 25.4), jk(8.5, 27.6), jk(5, 32), jk(2.5, 36), jk(0.5, 41.5), jk(-4.0, 41.5), jk(-3.5, 23.3),
                jk(-26, 23.3)])
GROUND = YARD.union(Polygon([jk(-26, 23.0), jk(-3.0, 23.0), jk(-4.0, 41.5), jk(-6.2, 34.4), jk(-24.0, 30.6), jk(-26, 30.2)]))
YARD_PLANE = (47.26, 0.0496, 0.0648)          # 해발 = a + b·u + c·v (JK frame)
# --- the road north of the east wing (SCI frame): from the wing's north face (v 18.4) to the back of the north bays
# (v 29.5); west to where it meets the yard north-west of the link (u -72), east round the wing's end into YARD
ROAD = Polygon([sc(-72, 18.4), sc(6, 18.4), sc(10, 22), sc(10, 29.5), sc(-72, 29.5)])
ROAD_U = [-72.0, -60.0, -48.0, -36.0, -24.0, -12.0, 0.0, 10.0]
ROAD_Z = [51.15, 51.55, 51.66, 51.51, 51.31, 50.71, 49.88, 48.91]     # (해발 at v ROAD_V0)
ROAD_V0, ROAD_CROSS = 24.0, 0.092
SCI_FACE_V, JK_FACE_V, JK_N_FACE_V = 18.4, 5.0, 8.5
HALL_IN = 5.0
JOIN_U = 12.0
RING = 8.0


def yard_z(x, y):
    u, v = jk_uv(x, y)
    return YARD_PLANE[0] + YARD_PLANE[1] * u + YARD_PLANE[2] * v


def road_z(x, y):
    u, v = sc_uv(x, y)
    return np.interp(u, ROAD_U, ROAD_Z) + ROAD_CROSS * (np.clip(v, SCI_FACE_V, 29.5) - ROAD_V0)


def cars_1997():
    """the 1997 cars of this part put in (tools/cars97_new.json, the sections on, labels res-* and sci-* but the road west
    of the south-west wing):
    (x, y, heading rad, label)"""
    import json
    import os
    d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cars97_new.json'), encoding='utf-8'))
    out = []
    for z in d.values():
        if not z.get('on'):
            continue
        for c in z.get('cars', []):
            if len(c) > 5 and isinstance(c[5], str) and c[5][:4] in ('res-', 'sci-') and not c[5].startswith('sci-W'):
                out.append((c[0], c[1], math.radians(c[2]), c[5]))
    return out


def car_cells(X, Y, step=5.0, half=800.0):
    """the grid nodes of the cells under each of cars_1997(): set on the place's own surface, so that a car along the
    wood's edge does not lean with the cut bank beside it (as tools/kwangbok97.py)"""
    m = np.zeros(X.shape, bool)
    for x, y, h, lab in cars_1997():
        t, n = (math.cos(h), math.sin(h)), (-math.sin(h), math.cos(h))
        cells = {(int(math.floor((y + t[1] * a + n[1] * b + half) / step)), int(math.floor((x + t[0] * a + n[0] * b + half) / step)))
                 for a in (-2.35, -0.8, 0.8, 2.35) for b in (-0.9, 0.9)}
        for j, i in {(j + a, i + b) for j, i in cells for a in (0, 1) for b in (0, 1)}:
            m[j, i] = True
    return m


def grade(Hn, X, Y, FIXED, keep, fill, dump=None):
    """keep: nodes left as they are (the other blocks' ground, the other halls' feet).  Returns (nodes laid or
    eased, summary)"""
    H0 = Hn.copy()
    su, sv = sc_uv(X, Y)
    ju, jv = jk_uv(X, Y)
    in_y = shapely.contains_xy(GROUND.buffer(1.0), X, Y) & ~keep
    in_r = shapely.contains_xy(ROAD.buffer(1.0), X, Y) & ~keep & ~in_y
    # (inside the halls: 과학관's east wing within HALL_IN of its north face and of its east end, 연구관's bar and north
    # block within HALL_IN of their west faces)
    sci_in = (su > -72.4) & (su < 0.6) & (sv < SCI_FACE_V) & (sv > SCI_FACE_V - HALL_IN) & ~keep & ~in_y & ~in_r
    sci_e = (su > 0.6 - HALL_IN) & (su < 0.6) & (sv > 0.3) & (sv < SCI_FACE_V) & ~keep & ~in_y & ~in_r & ~sci_in
    jk_in = (((ju > -24.75) & (ju < 21.0) & (jv < JK_FACE_V) & (jv > JK_FACE_V - HALL_IN)) |
             ((ju >= 21.0) & (ju < 37.0) & (jv < JK_N_FACE_V) & (jv > JK_N_FACE_V - HALL_IN))) & ~keep & ~in_y & ~in_r
    t = datum.tilt(X, Y)
    Hn[in_y] = yard_z(X[in_y], Y[in_y]) + t[in_y]
    Hn[in_r] = road_z(X[in_r], Y[in_r]) + t[in_r]
    # (where the road comes round the wing's end into the yard: from the road's profile at the wing's end (u 0) to the
    # yard's plane 12 m on; the plane is the yard's, the profile measured along the road)
    both = in_y & shapely.contains_xy(ROAD.buffer(1.0), X, Y)
    w = np.clip((JOIN_U - su[both]) / JOIN_U, 0.0, 1.0)
    Hn[both] = w * road_z(X[both], Y[both]) + (1.0 - w) * yard_z(X[both], Y[both]) + t[both]
    Hn[sci_in] = road_z(X[sci_in], Y[sci_in]) + t[sci_in]
    eu, ev = sc_xy(0.6, sv[sci_e])                    # (the east face's foot: the yard's plane there)
    Hn[sci_e] = yard_z(eu, ev) + t[sci_e]
    ju_c, jv_c = ju[jk_in], np.where(ju[jk_in] < 21.0, JK_FACE_V, JK_N_FACE_V)
    Hn[jk_in] = YARD_PLANE[0] + YARD_PLANE[1] * ju_c + YARD_PLANE[2] * jv_c + t[jk_in]
    # (the cells under the 1997 cars: on the yard's plane, or the road's profile north of the east wing)
    lot = car_cells(X, Y) & ~keep & ~in_y & ~in_r & ~sci_in & ~sci_e & ~jk_in
    on_r = shapely.contains_xy(ROAD.buffer(4.0), X, Y) & ~shapely.contains_xy(GROUND.buffer(1.0), X, Y)
    lr, ly = lot & on_r, lot & ~on_r
    Hn[lr] = road_z(X[lr], Y[lr]) + t[lr]
    Hn[ly] = yard_z(X[ly], Y[ly]) + t[ly]
    core = in_y | in_r | sci_in | sci_e | jk_in | lot
    # (the ring: free nodes, and those build_campus.py jk_grade had levelled at 48.3 m west of the bar beyond GROUND;
    # not the cut bank north of the road (as it was: steep, as the leafless 1996 pair has it), nor east of the bar's
    # line (the terrace east of it, 44.3 m))
    jk_flat = (jv > 3.0) & (jv < 30.0) & (ju > -28.0) & (ju < 45.0)
    bank = (su < 4.0) & (sv > 30.5)
    # (nor south of u -30: the road on south past the bar's end falls away to 체육관, as it was)
    ring = shapely.contains_xy(unary_union([GROUND, ROAD]).buffer(RING), X, Y) & ~core & (~FIXED | jk_flat) & ~keep & ~bank & \
        (jv > 3.0) & (ju > -30.0)
    if dump:
        np.savez(dump, H0=H0, FIXED=FIXED, keep=keep, core=core, ring=ring, X=X, Y=Y)
    if ring.any():
        fill(ring)
    d = Hn - H0
    took = core | ring
    return took, dict(yard=int(in_y.sum()), road=int(in_r.sum()), hall_side=int(sci_in.sum() + sci_e.sum() + jk_in.sum()), cars=int(lot.sum()), ring=int(ring.sum()),
                      lo=round(float(d[took].min()), 2), hi=round(float(d[took].max()), 2))


# --- 과학관 서쪽 길 (the road west of the south-west wing): its west edge, a straight kerb line at x -354.8 from y -14 to
# 16 in the leafless 1996 frames (the 1997 frames: the car parked against it at y -1), where the game's asphalt stopped
# 3 m short; the ground there as it is (the road's own, tools/seomun.py)
WEST_EDGE = Polygon([(-355.0, -8.0), (-350.5, -8.0), (-350.5, 8.0), (-355.0, 8.0)])


def paint():
    """아스팔트: 마당(연구관 쪽 나무 띠 v 9.5 까지, 남쪽 끝의 나무 무리는 빼고)과 북쪽 길, 과학관 서쪽 길의 서쪽 가"""
    yard = YARD.difference(Polygon([jk(-30, 0), jk(40, 0), jk(40, 9.5), jk(-5, 9.5), jk(-5, 12.5), jk(-30, 12.5)]))
    return [yard, ROAD, WEST_EDGE]


def move_off(trees, shrubs, props, halls):
    """새 포장 위에 심긴 것: 나무 · 관목 · 소품을 포장 가장자리 밖(건물 쪽이 아닌 가)으로(목록 제자리: 목록의 길이와 차례가
    그대로). halls: 둘레 건물 외곽선. 돌려주는 것: (옮긴 관목 수, 옮긴 소품 수, 옮긴 나무)"""
    zone = unary_union(paint()).buffer(0.5)
    block = unary_union([zone] + [h.buffer(2.0) for h in halls])
    moved, ns, npr = [], 0, 0
    for lst, pad in ((trees, 1.0), (shrubs, 0.6), (props, 0.6)):
        b = block.buffer(pad)
        edge = unary_union([g.exterior for g in (b.geoms if hasattr(b, 'geoms') else [b])])
        for t in lst:
            if zone.contains(Point(t[1], t[2])):
                q = nearest_points(edge, Point(t[1], t[2]))[0]
                if lst is trees:
                    moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
                elif lst is shrubs:
                    ns += 1
                else:
                    npr += 1
                t[1], t[2] = round(q.x, 2), round(q.y, 2)
    return ns, npr, moved
