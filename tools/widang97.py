"""제2인문관(위당관) 공사장의 1997년 7월 땅 (#189; reference/고증/3.12_빌링슬리관.md 「잔디 남쪽의 둑과 제2인문관 공사장」).
tools/build_campus.py 가 부른다.

    took, core, info = widang97.grade(Hn, X, Y, FIXED, halls, fill)   # 심기가 끝난 뒤, jonghap97.grade 바로 앞(core 는 그대로, 둘레는 그쪽이 다시 이음)
    widang97.YARD · BENCH · BANK                                 # 맨땅(둑은 잔디)으로 칠하고, 그 위를 지나던 지금의 길 · 보행로를 걷어 냄
    widang97.cut_paths(paths) · trees_aside(trees, halls)        # 게임이 읽는 길에서 · 나무를 목록 제자리에서

Frames: campus metres, x east, y north.  Every absolute height is above sea level (해발), taken up to the working
datum (해발 + tilt: tools/datum.py) at its own place where it is read.

The hall broke ground on 1997-05-29 (준공 1998-08-24, 3.1.1); on the 1997-07-28 scans (six frames, heights frame pair by
frame pair on a 4 m grid, the median of two to six pairs over 0.7) the whole of its site between 종합관's low block,
빌링슬리관's lawn and 교육관 is a bare works yard dug down to the level of the ground west and north of 교육관:

- YARD: 130 points 55.2 - 56.4 m (16 - 84 %), median 55.63 m, from the road along the low block's north wall (60.5 m, a
  storey over it within 4 m: the dig's edge) north to the foot of the bank under 빌링슬리관's lawn (the lawn 60.3 - 60.4
  m, the fence along its edge: 3.12) and from x -20 east to 교육관 and the yard north of it (55.0 - 55.9 m there, the
  2006 · 2024 surveys' 55 m too).  The game had a slope from 61 - 63 m at x -18 down to 54 - 56 m at x 10 - 18
  (OSM's later outline of the hall with its apron, lawns and the roads round it)
- BENCH: west of the yard a shelf at 61.44 m (24 points, 60.8 - 62.0 m), then the wooded slope up to the hill
  (tools/jonghap97.py HILL)

Not put in: the prefab offices, the trucks and cars on the yard north-east of 교육관, the rubble heaps, the retaining
piles along the dig's edges (3.12 「남은 한계」).  Nothing here draws from build_campus.py's `rng`.
"""
import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

import datum

YARD = Polygon([(-20.0, 331.0), (-14.0, 329.0), (-7.0, 327.5), (12.0, 327.5), (12.0, 350.0), (16.0, 358.0), (21.0, 362.5),
                (34.0, 362.5), (34.0, 385.0), (22.0, 386.5), (6.0, 387.0), (-6.0, 387.0), (-12.0, 385.0), (-20.0, 383.0)])
BENCH = Polygon([(-34.0, 339.0), (-24.0, 339.0), (-24.0, 375.0), (-34.0, 375.0)])
# the bank from the yard up to 빌링슬리관's lawn and its fence (3.12): lawn, not OSM's south road along its top (the road
# came with the hall; its east end past x 36, by the site offices, stays)
BANK = Polygon([(-12.0, 385.0), (-6.0, 387.0), (6.0, 387.0), (22.0, 386.5), (34.0, 385.0), (36.0, 384.5), (36.0, 389.5),
                (29.0, 390.5), (8.0, 395.5), (-4.0, 395.5), (-12.0, 394.0)])
YARD_Z = datum.up(0.0, 356.0, 55.63)
BENCH_Z = datum.up(-29.0, 357.0, 61.44)
RING = 8.0                        # eased out (harmonic) this far round them
HALL_PAD = 6.0                    # (교육관's west drive and north yard stay: its FORECOURTS)


def grade(Hn, X, Y, FIXED, halls, fill):
    """YARD and BENCH level, eased round them (fill: harmonic_fill); the halls' feet and the nodes laid before
    (FIXED) stay.  Returns the nodes set (to be FIXED), the level ones among them (for jonghap97.grade to keep: it lays
    its roads over the ring and eases its own ring into them) and a summary"""
    H0 = Hn.copy()
    stay = FIXED | (shapely.contains_xy(unary_union([h.buffer(HALL_PAD) for h in halls]), X, Y) if halls else False)
    yard = shapely.contains_xy(YARD, X, Y) & ~stay
    bench = shapely.contains_xy(BENCH, X, Y) & ~stay
    Hn[yard] = YARD_Z
    Hn[bench] = BENCH_Z
    took = yard | bench
    free = shapely.contains_xy(unary_union([YARD, BENCH]).buffer(RING), X, Y) & ~took & ~stay
    if free.any():
        fill(free)
    d = Hn - H0
    return took | free, took, dict(yard=int(yard.sum()), bench=int(bench.sum()), eased=int(free.sum()),
                             moved=(int((np.abs(d) > 0.05).sum()), round(float(d.min()), 1), round(float(d.max()), 1)))


def cut_paths(paths):
    """the walks and drives the game reads (the minimap, the crowd) that ran across the yard (OSM's, after the hall):
    each keeps its longest stretch off the yard (5 m or more) in its place in the list, or goes.  Returns (cut, gone)"""
    zone = unary_union([YARD, BENCH, BANK]).buffer(1.0)
    n = [0, 0]
    for p in list(paths):
        if len(p['pts']) < 2:
            continue
        ls = LineString(p['pts'])
        if ls.intersection(zone).length <= 1.0:
            continue
        d = ls.difference(zone)
        pcs = [g for g in getattr(d, 'geoms', [d]) if g.geom_type == 'LineString' and g.length >= 5.0]
        if pcs:
            p['pts'] = [[round(x, 1), round(y, 1)] for x, y in max(pcs, key=lambda g: g.length).coords]
            n[0] += 1
        else:
            paths[:] = [q for q in paths if q is not p]
            n[1] += 1
    return tuple(n)


def trees_aside(trees, halls, pad=2.0):
    """trees the random planting put on the yard and the shelf (the scans have none): each moved in its place in the list
    to the nearest free point pad m outside them, clear of the halls by 2.5 m and of the trees there by 3 m.
    Returns the moves"""
    clear = unary_union([YARD, BENCH])
    hb = unary_union([h.buffer(2.5) for h in halls])
    rings = [g.exterior for g in getattr(clear.buffer(pad), 'geoms', [clear.buffer(pad)])]
    spots = [r.interpolate(d) for r in rings for d in np.arange(0.0, r.length, 0.5)]
    spots = [q for q in spots if not hb.contains(q)]
    inside = [t for t in trees if clear.buffer(0.5).contains(Point(t[1], t[2]))]
    near = [Point(t[1], t[2]) for t in trees if not any(t is i for i in inside) and abs(t[1]) < 80 and abs(t[2] - 357.0) < 70]
    spots = [q for q in spots if all(q.distance(o) > 3.0 for o in near)]
    moved = []
    for t in inside:
        if not spots:
            break
        q = min(spots, key=lambda q_: q_.distance(Point(t[1], t[2])))
        moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
        t[1], t[2] = round(q.x, 2), round(q.y, 2)
        spots = [s for s in spots if s.distance(q) > 3.5]
    return moved
