"""알렌관과 그 둘레의 1997년 땅 (#189; reference/고증/3.23_청송대.md 「알렌관의 생김새와 둘레의 땅」).
tools/build_campus.py 가 부른다.

    took, decks, info = allen97.grade(Hn, X, Y, FIXED, fill)    # 심기가 끝난 뒤, east97 바로 뒤
    (decks: dwb_deck 으로; med_west 고리에서 allen97.terrace_walls · hill_walls 가 옹벽 · 난간 · 막)
    asph, pave = allen97.paint()                                  # 땅 지도에만(늦게)
    allen97.south_block(osm_record); buildings += allen97.halls() # 건물 목록 끝에
    allen97.trees_aside(items, halls)                             # 새 자리의 나무 · 관목 · 소품을 목록 제자리에서

Frame AL: o (365.16, 33.92) on the south-west corner of OSM's outline, u east along its south face (-17.5 deg), v north
across it.  Every absolute height written here is above sea level (해발); the ground is laid on the working datum
(해발 + datum.tilt), so they are taken up where they are set.

The place (1996-11-28 · 1997-07-28 · 1999-05-31 scans, course 27 only: 27/15 · 27/16 · 27/17; 1998-10 27/17 and the 1999
frames from the west for the end walls).  The hall and its ground did not change 1996 - 1999 (the stall lines, the roofs),
so each flight's pairs measure the same surfaces: 1996's three same-day pairs, 1997's one, 1999's three, each on its own.
- 알렌관 (1987) is not OSM's one flat block but a hall on two levels of ground:
  - C, the south block: one storey, flat roof 60.55 m (60.4 - 60.7 in all three years, corr 0.8 - 0.9), a low coping
    0.3 m over it; u 1.4 .. 30.4, v -0.6 .. 10.6 (its edges where the frames that do not see that wall agree), a bow 1.95
    m out of the middle of its east end
  - B, the middle block over it: gabled, its ridge along u 64.75 m (1996's pairs 64.7, corr 0.99), eaves 62.7; u 4.1 ..
    21.0, v ~11 .. 21
  - A, the north range: gabled, ridged along u, in three lengths: u -2.1 .. 14.3 (eaves v 27.1 / 38.4, ridge 69.35),
    14.3 .. 26.5 (26.4 / 36.1, ridge 69.45), 26.5 .. 33.3 (28.4 / 36.1, ridge 68.7); eaves 67.2
  - W, a lower gabled bay at A's west end: u -6.5 .. -2.1, eaves 64.2, ridge 65.95
  - R, a round-ended flat-roofed bay at B's west end: u -1.4 .. 4.1, v 13.4 .. 19.2, roof 60.25
- The ground: the court east of B and north of C at 56.95 m (1996's pairs: 56.94 - 56.95, corr 1.0); between B and A and
  east of A an upper level at 61.3 m (the terrace: 1997 umbrellas on it, a 4.3 m wall down to the court and to the west
  yard), going round A's east end into a trench along A's north wall (61.1); north of the trench a wall up to the hill
  (63.5 m, rising to the works yard's 68.5 m 8 m further north); west of the hall the yard and the drive at 55.8 - 57.2
  (2024 survey spot (365.1, 44.3) 56.48); south of C a strip at 55.5 - 55.9 down from the car park's platform (56.0).
- GRID: the 5 m nodes from x 340, y -5: per node the 35th percentile of the points within 3.2 m where the scans see the
  ground (1996's pairs agreeing, the 1997 pair; on the works yard the 1997 pair, which 1996's leafless frames match to
  -0.15 m (median of 133 points)), points on the halls left out, a node 2.5 m over its neighbours' median dropped (a
  crown).  '.' none: eased.
- Nothing here draws from build_campus.py's `rng`.
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import datum

AL_O = np.array([365.16, 33.92])
AL_T = np.array([0.9538, -0.3005])
AL_N = np.array([0.3005, 0.9538])


def xy(u, v):
    return (float(AL_O[0] + AL_T[0] * u + AL_N[0] * v), float(AL_O[1] + AL_T[1] * u + AL_N[1] * v))


def uv(x, y):
    dx, dy = np.asarray(x, float) - AL_O[0], np.asarray(y, float) - AL_O[1]
    return dx * AL_T[0] + dy * AL_T[1], dx * AL_N[0] + dy * AL_N[1]


def P(pts):
    return Polygon([xy(u, v) for u, v in pts])


# --- the hall (walls; a gable's roof sails `over` past them) --------------------------------------------------------
ALLEN = 472512289                  # (OSM's 알렌관: now its south block, C, flat-roofed as it was: blender's looks stream keeps)
OVER = 0.3
FLOOR = 56.9                       # (the court's level, A · B: the lower storey opens on it and on the west yard)
C_UV = [(1.4, -0.6), (30.4, -0.6)] + [(30.4 + 1.95 * math.sin(math.pi * k / 8) if 0 < k < 8 else 30.4,
                                       1.0 + 7.8 * k / 8) for k in range(9)] + [(30.4, 10.6), (1.4, 10.6)]
C_ROOF, C_COPE, C_BASE = 60.55, 0.3, 56.3
B_UV = [(4.4, 11.2), (20.7, 11.2), (20.7, 20.6), (4.4, 20.6)]
A1_UV = [(-1.8, 27.4), (14.3, 27.4), (14.3, 38.1), (-1.8, 38.1)]
A2_UV = [(14.3, 26.7), (26.5, 26.7), (26.5, 35.8), (14.3, 35.8)]
A3_UV = [(26.5, 28.7), (33.0, 28.7), (33.0, 35.8), (26.5, 35.8)]
W_UV = [(-6.2, 30.0), (-1.8, 30.0), (-1.8, 38.0), (-6.2, 38.0)]
R_C, R_R = (1.5, 16.3), 2.9          # (the round end's middle and radius)
R_UV = [(4.6, 13.4)] + [(R_C[0] + R_R * math.cos(math.radians(a)), R_C[1] + R_R * math.sin(math.radians(a)))
                        for a in range(270, 89, -15)] + [(4.6, 19.2)]
R_ROOF, R_COPE, R_BASE = 60.25, 0.3, 56.6
# (id, outline, base, storeys, the roof's south edge, the ridge, the ridge's v)
GABLES = [(990091, B_UV, FLOOR, 2, 62.7, 64.75, None), (990092, A1_UV, FLOOR, 3, 67.2, 69.35, None),
          (990093, A2_UV, FLOOR, 3, 67.2, 69.45, 32.5), (990094, A3_UV, FLOOR, 3, 67.2, 68.7, None),
          (990095, W_UV, 57.0, 2, 64.2, 65.95, None)]
R_ID = 990096
HALLS_UV = [C_UV, B_UV, A1_UV, A2_UV, A3_UV, W_UV, R_UV]
DOOR_UV = ((16.0, -0.6), (0.0, -1.0))          # (C's door in its south face, where OSM's was)


def hall_polys():
    return [shapely.geometry.polygon.orient(P(q).buffer(0), 1.0) for q in HALLS_UV]


def _fp(q):
    p = shapely.geometry.polygon.orient(P(q).buffer(0), 1.0)
    return [[round(x, 2), round(y, 2)] for x, y in list(p.exterior.coords)[:-1]]


def south_block(b):
    """OSM's record made C: its outline, floor, storey, coping (blender/generic.py draws a flat roof as before)"""
    c = xy(16.0, 5.0)
    base = datum.up(*c, C_BASE)
    fh = round(C_ROOF - C_BASE, 3)
    b.update(footprint=_fp(C_UV), base=base, levels=1, fh=fh, height=round(fh + C_COPE, 2), parapet=C_COPE,
             top_ground=datum.up(*c, 56.95))
    (du, dv), (nu, nv) = DOOR_UV
    p = xy(du, dv)
    n = (nu * AL_T[0] + nv * AL_N[0], nu * AL_T[1] + nv * AL_N[1])
    b['entry'] = dict(p=[round(p[0], 2), round(p[1], 2)], n=[round(n[0], 4), round(n[1], 4)], floor=0)
    return b


def halls():
    """B, A's three lengths and W (gabled, slate, brick walls; blender/generic.py hip_roof with gable) and R (flat roof),
    for the halls' end (blender/build.py draws each hall's looks in its order: none after them changes its looks)"""
    out = []
    for hid, q, z0, nf, eave, ridge, rv in GABLES:
        c = datum.centroid([xy(*p) for p in q])
        vs = [p[1] for p in q]
        w = max(vs) - min(vs)                                  # (the ridge along u: the outline's depth across it)
        off = 0.0 if rv is None else rv - (max(vs) + min(vs)) / 2
        # (blender/generic.py hip_roof: the south slope's edge OVER out and OVER * its pitch under the walls' head, the
        # ridge (w/2 + off) * that pitch over it; `pitch` is the ridge's height over the head / (w/2))
        p1 = (ridge - eave) / (OVER + w / 2 + off)
        wt = round(eave + OVER * p1, 3)
        pitch = round(p1 * (w / 2 + off) / (w / 2), 3)
        base = datum.up(*c, z0)
        fh = round((wt - z0) / nf, 3)
        out.append(dict(id=hid, name='알렌관', style='brick', levels=nf, fh=fh, height=round(wt - z0, 2), base=base,
                        top_ground=base, footprint=_fp(q),
                        hip=dict(mat='roof_slate', pitch=pitch, over=OVER, gable=True, off=round(off, 2),
                                 ridge=[round(float(AL_T[0]), 4), round(float(AL_T[1]), 4)])))
    c = xy(1.0, 16.3)
    base = datum.up(*c, R_BASE)
    fh = round(R_ROOF - R_COPE - R_BASE, 3)
    out.append(dict(id=R_ID, name='알렌관', style='brick', levels=1, fh=fh, height=round(R_ROOF - R_BASE, 2), base=base,
                    parapet=R_COPE, top_ground=base, footprint=_fp(R_UV)))
    return out


# --- the ground ----------------------------------------------------------------------------------------------------
COURT_Z, UPPER_Z, TRENCH_Z = 56.95, 61.3, 61.1
COURT_UV = [(20.7, 10.6), (37.5, 10.6), (37.5, 20.8), (20.7, 20.8)]
# the upper level: between B and A, east of A to u 42 (38.5 north of v 36), the trench north of A east of u 14
UPPER_UV = [(1.8, 20.6), (20.7, 20.6), (20.7, 20.8), (42.0, 20.8), (42.0, 31.0), (38.5, 36.0), (38.5, 40.5), (14.0, 40.5),
            (14.0, 38.1), (-1.8, 38.1), (-1.8, 27.4), (1.8, 27.4)]
# the walls, (u, v) polylines with the upper ground on their left: the terrace's west face and the court's north face
# (the upper level over the lower), the trench's north face (the hill over the trench) with short returns at its ends
TERRACE_WALL = [(1.8, 27.4), (1.8, 20.6), (4.4, 20.6)]
COURT_WALL = [(20.7, 20.8), (38.5, 20.8)]
TRENCH_WALL = [(14.0, 40.5), (38.5, 40.5)]
TRENCH_RETURNS = [[(14.0, 46.0), (14.0, 40.5)], [(38.5, 40.5), (38.5, 46.0)]]
PARAPET = (1.0, 0.25)              # (over the terrace's edge: height, thickness)
COPING = (0.3, 0.3)                # (over the trench's wall)
HILL = (63.6, 43.5, 0.95, 68.6)    # (north of the trench: a bench at 63.6 m to v 43.5, then up 0.95 m a metre to 68.6)
HILL_UV = [(14.0, 40.5), (38.5, 40.5), (38.5, 50.0), (14.0, 50.0)]
PAVE_U = 38.5                      # (the upper level paved west of this: the 1997 frames' wood east of it)
ZONE_UV = [(-17.0, -6.2), (44.0, -6.2), (44.0, 18.0), (54.0, 22.0), (50.0, 40.0), (47.0, 52.0), (-17.0, 52.0)]
RING = 10.0
GRID_X0, GRID_Y0, GRID_D = 340.0, -5.0, 5.0
GRID = np.array([[np.nan if v == '.' else int(v) / 10.0 for v in r.split()] for r in """
529 524 521 515 512 507 507 . 499 . 570 571 529 502 503 503 503 506 505 .
531 532 536 . . . . 570 570 562 560 568 570 513 518 504 . . . .
540 . 537 545 566 570 562 562 562 560 560 568 568 . . . . . . .
. 537 540 542 560 564 560 560 559 560 560 562 562 . . . . . . .
. 540 540 547 553 560 562 . 560 562 558 558 558 557 623 . . . . .
. 545 . . 555 562 563 558 558 . 557 557 557 557 . . . . 592 .
541 . 550 554 555 559 559 . . . . . 554 . . . . . 606 .
. . 560 558 557 558 . . . . . . 561 . . . . . . .
546 . 563 559 559 560 . . . . . . 569 . 636 636 . . 628 .
548 . . 564 561 563 . . . . 588 570 570 570 626 . . 641 641 .
553 . . 565 562 563 . . . . . . . 613 609 604 620 643 643 .
. . . . 566 564 . . . . . 615 . . 606 614 . 643 644 .
. . 561 . 568 566 . . . . . . . . 611 630 650 645 645 .
. . . . . 568 . . . . . . . . 629 660 652 646 645 .
. . . . 573 . . . . . . . 635 637 638 . 651 644 . .
. 622 569 . 574 595 . . . . . 633 . . 675 673 . 640 . .
672 . 582 . . 589 . . 602 . . . . 684 680 . . . . .
. . 579 . . 583 . 604 605 626 . 678 685 684 687 . . . . .
593 593 586 . . 585 594 603 625 . . 676 682 687 686 687 690 . 688 .
594 594 595 . . 596 597 616 626 . . . 681 687 687 687 686 647 646 .
. . . . . . 601 609 . . 665 666 686 . . 690 680 655 . .
. . . . . . 605 616 628 659 660 687 687 . 682 687 . . . .
. . . . . . 607 614 643 656 658 687 684 675 676 685 687 . . .
. . . . . . 612 . 641 649 685 688 686 678 683 687 682 664 . .
. . . . . . 630 . 643 . 686 687 689 688 . . . . . .
. . . . . 606 . . . 670 679 648 691 690 690 . . . . .
. . . . . . 626 . . 658 684 690 690 . 691 690 690 . . .
. . . . . . 625 637 639 662 680 690 692 692 692 688 . . . .
. . . . . . . 646 648 664 677 692 702 703 701 . . . . .
. . . . . . . 644 649 661 672 702 . . . . . . . .
. . . . . . 643 644 657 659 680 703 709 709 706 699 . . . .
. . . . . . 644 646 . 672 682 705 711 708 705 . . . . .
. . . . . . . 648 . 663 680 . 713 711 704 . . . . .
. . . . . . . . 663 . . . 679 . . . . . . .
""".strip().splitlines()])


def grid_at(x, y):
    """GRID's node value at (x, y) (해발), or nan off it"""
    i, j = int(round((x - GRID_X0) / GRID_D)), int(round((y - GRID_Y0) / GRID_D))
    if 0 <= j < GRID.shape[0] and 0 <= i < GRID.shape[1] and abs(x - (GRID_X0 + i * GRID_D)) < 0.01 \
            and abs(y - (GRID_Y0 + j * GRID_D)) < 0.01:
        return GRID[j, i]
    return np.nan


def zone():
    import east97
    return unary_union([P(ZONE_UV), east97.SITE97.buffer(1.5)])


def upper_h(x, y):
    """the upper level (working datum): the trench north of A a little lower"""
    u, v = uv(x, y)
    z = np.where((np.asarray(v) > 36.0) & (np.asarray(u) < 38.6), TRENCH_Z, UPPER_Z)    # (the trench: north of A)
    return z + datum.tilt(x, y)


def hill_h(x, y):
    """the hill north of the trench (working datum)"""
    u, v = uv(x, y)
    z = np.clip(HILL[0] + HILL[2] * (np.asarray(v) - HILL[1]), HILL[0], HILL[3])
    return z + datum.tilt(x, y)


def _box(j, i, step, half):
    return box(-half + i * step, -half + j * step, -half + (i + 1) * step, -half + (j + 1) * step)


def _wall_nodes(line_uv, shape, step, half):
    """the nodes of the 5 m cells a (u, v) polyline crosses"""
    ls = LineString([xy(*q) for q in line_uv])
    x0, y0, x1, y1 = ls.bounds
    out = np.zeros(shape, bool)
    for j in range(int(math.floor((y0 + half) / step)), int(math.floor((y1 + half) / step)) + 1):
        for i in range(int(math.floor((x0 + half) / step)), int(math.floor((x1 + half) / step)) + 1):
            if _box(j, i, step, half).intersection(ls).length > 0.05:
                out[j:j + 2, i:i + 2] = True
    return out


def _deck(Hn, low, keep_poly, hfun, step, half, halls, tol=0.3):
    """every cell over the level's outline (off the halls) with a node the walls or a hall's floor left more than tol
    under the level (low): a deck carries the level over it.  Returns the deck's cells and outline (cut to them)"""
    keep = keep_poly.difference(unary_union(halls).buffer(0.05)) if halls else keep_poly
    x0, y0, x1, y1 = keep.bounds
    cells = set()
    for j in range(int(math.floor((y0 + half) / step)), int(math.floor((y1 + half) / step)) + 1):
        for i in range(int(math.floor((x0 + half) / step)), int(math.floor((x1 + half) / step)) + 1):
            if _box(j, i, step, half).intersection(keep).area < 0.02:
                continue
            xs, ys = (-half + i * step, -half + (i + 1) * step), (-half + j * step, -half + (j + 1) * step)
            if any(low[j + a, i + c] and Hn[j + a, i + c] < float(hfun(xs[c], ys[a])) - tol for a in (0, 1) for c in (0, 1)):
                cells.add((j, i))
    poly = unary_union([_box(j, i, step, half) for j, i in cells]).intersection(keep) if cells else Polygon()
    cells = {c for c in cells if _box(*c, step, half).intersection(poly).area > 0.02}
    return cells, poly


def grade(Hn, X, Y, FIXED, fill, step=5.0, half=800.0):
    """GRID over the zone (whatever set its nodes before yields: the hall round here is this module's), the halls'
    insides on their floors, the court, the upper level and the trench on theirs, the nodes of the cells the walls cross
    on the low side's level (decks carry the upper level and the hill over them), the hill north of the trench; the
    rest of the zone and a ring round it eased.  Returns the nodes set (to be FIXED), the decks {name: (cells, outline,
    hfun)} and a summary"""
    H0 = Hn.copy()
    T = datum.tilt(X, Y)
    Z = zone()
    inz = shapely.contains_xy(Z, X, Y)
    U, V = uv(X, Y)
    G = np.full(X.shape, np.nan)
    for j, i in zip(*np.nonzero(inz)):
        G[j, i] = grid_at(X[j, i], Y[j, i])
    have = inz & np.isfinite(G)
    Hn[have] = G[have] + T[have]
    done = have.copy()
    # the halls' insides: their floors (A but its west end on the upper level)
    hp = hall_polys()
    for p, z in ((hp[0], C_BASE), (hp[1], COURT_Z), (hp[5], 57.5), (hp[6], R_BASE)):
        m = shapely.contains_xy(p, X, Y)
        Hn[m] = z + T[m]
        done |= m
    a_in = shapely.contains_xy(unary_union(hp[2:5]), X, Y)
    a_w = a_in & (U < 3.5)
    Hn[a_in & ~a_w] = upper_h(X, Y)[a_in & ~a_w]
    Hn[a_w] = 57.5 + T[a_w]
    done |= a_in
    halls_in = shapely.contains_xy(unary_union(hp), X, Y)
    court = shapely.contains_xy(P(COURT_UV).buffer(0.5), X, Y) & ~halls_in
    Hn[court] = COURT_Z + T[court]
    done |= court
    # the terrace's and the court's walls: the nodes of their cells on the low side's level, the court's or the yard's
    low_u = (_wall_nodes(TERRACE_WALL, X.shape, step, half) | _wall_nodes(COURT_WALL, X.shape, step, half)
             | _wall_nodes([B_UV[3], B_UV[2]], X.shape, step, half)) & ~halls_in
    upper = shapely.contains_xy(P(UPPER_UV), X, Y) & ~halls_in & ~low_u
    Hn[upper] = upper_h(X, Y)[upper]
    done |= upper
    lc = low_u & (U > 19.0)
    Hn[lc] = COURT_Z + T[lc]
    ly = low_u & ~lc
    Hn[ly] = np.where(np.isfinite(G[ly]), G[ly], 57.0) + T[ly]
    done |= low_u
    # the trench's wall: the hill's nodes of its cells down to the trench; the hill north of it
    low_h = _wall_nodes(TRENCH_WALL, X.shape, step, half) & ~halls_in
    Hn[low_h] = TRENCH_Z + T[low_h]
    done |= low_h
    hill = shapely.contains_xy(P(HILL_UV), X, Y) & ~low_h
    Hn[hill] = hill_h(X, Y)[hill]
    done |= hill
    free = inz & ~done
    if free.any():
        fill(free)
    ring = shapely.contains_xy(Z.buffer(RING), X, Y) & ~inz & ~FIXED
    if ring.any():
        fill(ring)
    cu, pu = _deck(Hn, low_u | halls_in, P(UPPER_UV), upper_h, step, half, hp)
    ch, ph = _deck(Hn, low_h, P(HILL_UV), hill_h, step, half, hp)
    d = Hn - H0
    info = dict(nodes=int(inz.sum()), from_grid=int(have.sum()), eased=int(free.sum()), ring=int(ring.sum()),
                yielded=int((inz & FIXED).sum()), up=round(float(d[inz].max()), 1), down=round(float(d[inz].min()), 1),
                median=round(float(np.median(d[inz])), 2), terrace_deck=(len(cu), round(pu.area, 1)),
                hill_deck=(len(ch), round(ph.area, 1)))
    return inz, dict(allen_terrace=(cu, pu, upper_h), allen_hill=(ch, ph, hill_h)), info


def _walls(lines, top, foot, ph, pt, step=0.5):
    """concrete walls along (u, v) polylines with the upper ground on their left, from its edge (top) down to what lies
    below (foot), a parapet (ph high, pt thick) along their top; guards where the drop is over 1 m: quads, polygons"""
    quads, guards = [], []
    R = lambda q, z: [round(q[0], 3), round(q[1], 3), round(float(z), 3)]
    for line in lines:
        for (ua, va), (ub, vb) in zip(line[:-1], line[1:]):
            L = math.hypot(ub - ua, vb - va)
            n = max(1, int(math.ceil(L / step)))
            tu, tv = (ub - ua) / L, (vb - va) / L
            nu, nv = -tv, tu                           # (towards the upper ground)
            S = [(ua + (ub - ua) * k / n, va + (vb - va) * k / n) for k in range(n + 1)]
            Pp = [xy(u, v) for u, v in S]
            Bk = [xy(u + nu * pt, v + nv * pt) for u, v in S]
            zt = [top(*xy(u + nu * 0.02, v + nv * 0.02)) for u, v in S]
            zb = [foot(*xy(u - nu * 0.05, v - nv * 0.05)) - 0.05 for u, v in S]
            for k in range(n):
                if max(zt[k] - zb[k], zt[k + 1] - zb[k + 1]) < 0.1:
                    continue
                c0, c1 = zt[k] + ph, zt[k + 1] + ph
                # (seen from the low side the run goes left to right: the face, the parapet's top, its back)
                quads.append(['concrete', [R(Pp[k], zb[k]), R(Pp[k + 1], zb[k + 1]), R(Pp[k + 1], c1), R(Pp[k], c0)]])
                quads.append(['concrete', [R(Pp[k], c0), R(Pp[k + 1], c1), R(Bk[k + 1], c1), R(Bk[k], c0)]])
                quads.append(['concrete', [R(Bk[k], zt[k] - 0.05), R(Bk[k], c0), R(Bk[k + 1], c1), R(Bk[k + 1], zt[k + 1] - 0.05)]])
                if min(zt[k] - zb[k], zt[k + 1] - zb[k + 1]) > 1.0:
                    q = [xy(u_ - nu * 0.02, v_ - nv * 0.02) for u_, v_ in (S[k], S[k + 1])] + \
                        [xy(u_ + nu * pt, v_ + nv * pt) for u_, v_ in (S[k + 1], S[k])]
                    guards.append([[round(c, 3) for c in p] for p in q])
    return quads, guards


def terrace_walls(top, foot):
    """the terrace's west face and the court's north face, the parapet along the terrace's edge"""
    return _walls([TERRACE_WALL, COURT_WALL], top, foot, *PARAPET)


def hill_walls(top, foot):
    """the trench's north face up to the hill and its returns, the coping"""
    return _walls([TRENCH_WALL] + TRENCH_RETURNS, top, foot, *COPING)


def paint():
    """(asphalt, paving): the west yard and the drive along it; the court, the terrace and the trench"""
    asph = [P([(-15.0, -6.2), (1.0, -6.2), (1.0, 12.5), (-1.6, 12.5), (-1.6, 30.0), (-6.5, 30.0), (-15.0, 30.0)]).difference(
        unary_union(hall_polys()).buffer(0.2))]
    pave = [P(COURT_UV), P(UPPER_UV).intersection(P([(-5.0, 15.0), (PAVE_U, 15.0), (PAVE_U, 45.0), (-5.0, 45.0)])).difference(
        unary_union(hall_polys()).buffer(0.05))]
    return asph, pave


def site():
    """the hall's outlines, the court, the upper level and the trench's wall: nothing planted stands there"""
    return unary_union(hall_polys() + paint()[1] + [LineString([xy(*q) for q in TRENCH_WALL]).buffer(1.5)]).buffer(0.8)


def trees_aside(items, halls, pad=1.5):
    """trees the planting put in the halls' new outlines, the court, the terrace, the trench or the walls' line: each in
    its place in the list to the nearest point pad m outside them, clear of the halls by 2.5 m and of the other trees
    by 3 m (none goes onto the yard's asphalt)"""
    site_ = site()
    hb = unary_union([h.buffer(2.5) for h in halls] + [p.buffer(2.5) for p in hall_polys()])
    asph = unary_union(paint()[0])
    ring = site_.buffer(pad)
    rings = [ring.exterior] if ring.geom_type == 'Polygon' else [g.exterior for g in ring.geoms]
    spots = [r.interpolate(d) for r in rings for d in np.arange(0.0, r.length, 0.5)]
    spots = [q for q in spots if not hb.contains(q) and not asph.contains(q) and zone().contains(q)]
    inside = [t for t in items if site_.contains(Point(t[1], t[2]))]
    others = [Point(t[1], t[2]) for t in items if not any(t is s for s in inside) and site_.buffer(15.0).contains(Point(t[1], t[2]))]
    spots = [q for q in spots if all(q.distance(o) > 3.0 for o in others)]
    moved = []
    for t in inside:
        if not spots:
            break
        q = min(spots, key=lambda q_: q_.distance(Point(t[1], t[2])))
        moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
        t[1], t[2] = round(q.x, 2), round(q.y, 2)
        spots = [s for s in spots if s.distance(q) > 3.0]
    return moved
