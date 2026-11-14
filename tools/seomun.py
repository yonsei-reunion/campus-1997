"""서문으로 나가는 길 (reference/고증/3.22_서문.md).  tools/build_campus.py 가 부른다.

    took = seomun.grade(Hn, X, Y, FIXED, halls, field_patch, harmonic_fill)   # 1997년 사진 높이로 땅(심기가 끝난 뒤, 저장 바로 앞)
    seomun.takeup(paths_out)          # OSM 의 선 가운데 1997년 길과 다른 토막(대운동장 북동쪽 길 끝)이 깔던 아스팔트
    asph, dirt = seomun.paint()       # 남남동 찻길 · 서문 안 갈림목 · 문 밖 골목(집 앞까지 아스팔트), 작은 건물 둘레 마당
    seomun.houses(ground)             # 골목 둘레 연희동 집(OSM 외곽선, 1997년 사진에도 있는 것) · 갈림목 남쪽 작은 건물
    seomun.gate(ground)               # 서문의 기둥 · 문짝 · 담(campus.json seomun, blender/landmarks.py seomun)

Frame: campus metres, x east, y north.  51 서문 on the 1990 and 1995 maps (57 on the 1994 map), 연희로10길's east end
where it meets the campus road west of 과학관 (OSM 2026 way 242897924 「연세대학교 서문」, -360.8, -18.4).

- The road: west of 과학관 the campus road comes down from the hall's south-west corner (48.8 m on the photos) past the
  gate (45.6 m) and on south-south-east to the 대운동장's north-east (41.7 m), the stretch 2026's OSM no longer has.
  Its middle from the 1997-07-28 scans (26/16 · 26/15: the bright band across straightened strips; 7 - 9 m between the
  wood's edge and the bare ground east, small trucks parked on its east side), its surface on their heights.
- Heights: the two frames that see it (26/15 · 26/16) give the ground 2 - 7 m under the game's (the elevation grid
  smoothed the slope down to 연희동 and to the 대운동장); here the photos' plus 0.3 m (the 과학관 corner and the road
  where it meets the game's at y -129 read 0.2 and 0.6 m under the game).  The lane outside drops from the gate
  (44.4 m) to 39.3 m 30 m west (four points at x -389 .. -392, corr 0.9) and on to about 34 m at x -425.
- Nothing here draws from build_campus.py's `rng`.
"""
# (2026-11-15: every absolute height in this file's code is on the sea-level datum, 2.0 m under the old game datum;
# heights quoted in comments written before then are 2.0 m higher: tools/build_campus.py SURFACE_DZ)
import math
import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union, nearest_points
import shapely

GATE = ((-359.9, -16.5), (-361.7, -20.3))      # OSM's gate line: the opening between the posts (4.2 m), north -> south
GATE_Z = 42.4
# the campus road, north (과학관's south-west corner) to where it meets the game's road north-east of the 대운동장:
# (x, y, surface) -- the photos' heights + 0.3 m; None: the game's ground there (the join, eased)
ROAD = [(-349.0, 4.0, 47.3), (-348.5, -5.0, 46.2), (-347.3, -15.0, 45.2), (-345.4, -23.0, 43.6), (-343.2, -31.0, 42.0),
        (-341.0, -40.5, 40.6), (-338.6, -49.5, 40.3), (-333.2, -61.0, 40.1), (-328.0, -72.5, 40.1), (-325.0, -82.0, 40.1),
        (-322.4, -90.5, 40.0), (-319.6, -98.0, 40.0), (-317.0, -105.0, 39.9), (-314.6, -111.5, 39.8), (-312.6, -117.5, 39.7),
        (-310.6, -123.8, 39.5), (-308.8, -130.2, None), (-306.4, -136.5, None), (-304.2, -141.6, None),
        (-301.6, -146.6, None)]
ROAD_HALF = 3.25
# 연희로10길 out of the gate, west then north-west (OSM 2026 ways 421415361, the 1997 scans: the same line between the
# same houses); surface: the gate, the photos at x -389 .. -396 (39.3 m) and -423 .. -425 (34.2 m, corr 0.7), between
# them evenly
LANE = [(-360.8, -18.4, 42.4), (-366.0, -17.6, 41.5), (-375.0, -16.6, 39.8), (-385.0, -15.8, 38.2), (-392.0, -15.3, 37.3),
        (-400.0, -14.8, 36.1), (-407.0, -12.8, 34.9), (-415.0, -8.7, 33.6), (-424.4, -2.9, 32.2), (-428.9, 2.9, 31.6)]
LANE_HALF = 2.3
LANE_EDGE = 1.0                                 # (the asphalt on to the houses' fronts either side: the 2010 roadview)
# the lane south from the gate along the campus wall (OSM 876166677; the 1997 scans' pale path round the wooded knoll):
# level with the gate (the photos: 44.5 - 45.1 m along it)
ARC = [(-362.6, -18.6, 42.4), (-366.0, -25.5, 42.5), (-369.7, -33.3, 42.6), (-372.8, -39.8, 42.7), (-376.6, -44.0, 42.8)]
ARC_HALF = 1.6
# the side alley between houses 80 and 82 (OSM 379198897) down to the south
ALLEY = [(-389.8, -15.4, 38.0), (-394.3, -24.0, 39.0), (-399.0, -33.3, 40.0)]
ALLEY_HALF = 1.3
# the paved mouth inside the gate: from the posts to the road's west edge (the scans: one pale surface from the lane's end
# to the road, the big tree's crown north of it)
APRON = [(-359.9, -16.5), (-355.5, -15.6), (-349.6, -16.5), (-348.3, -21.0), (-347.9, -25.8), (-352.5, -25.6), (-357.0, -23.4),
         (-361.7, -20.3)]
# the yard west of the hedge, round the small building (the scans: bare and pale, 44 - 45 m)
YARD = [(-357.5, -26.0), (-348.6, -26.4), (-346.8, -33.0), (-344.8, -41.0), (-344.0, -50.5), (-352.0, -51.5), (-356.0, -44.0),
        (-360.5, -30.0)]
SHED = [(-351.7, -40.4), (-346.3, -39.5), (-345.0, -48.4), (-350.4, -49.5)]    # its roof on the scans, 44.9 m
SHED_TOP = 42.9 + 0.3
# the walls either side of the gate: north, the boundary along the lane's end and up past house 83 (a granite wall in
# the 2010 · 2011 roadview, the campus behind it a storey over the lane by 83); south, the campus wall along the lane
# round the knoll (OSM 2026's fence)
WALL_N = [(-361.6, -15.2), (-359.5, -4.0), (-357.0, 11.0)]
WALL_S = [(-361.7, -20.3), (-366.0, -29.2), (-370.5, -38.5), (-375.4, -48.7)]
# 연희동's houses by the lane (OSM 2026 outlines, simplified 0.25 m; all on the 1997 scans): (OSM id, its name (the
# house number), storeys, roof)
HOUSES = [
    (1353895460, '83', 4, None, ((-362.5, -3.9), (-363.4, -13.0), (-386.1, -10.6), (-385.1, -1.5))),
    (1353895468, '79-6', 3, None, ((-362.5, 13.8), (-362.8, 5.2), (-380.7, 5.7), (-380.5, 14.3))),
    (1353885818, '77', 2, None, ((-400.7, -8.2), (-403.2, -12.1), (-411.1, -7.0), (-407.2, -1.0), (-402.3, -4.1))),
    (1494517992, '75', 2, None, ((-423.9, 1.1), (-412.7, 9.8), (-407.0, 2.4), (-408.8, 1.0), (-408.4, 0.5), (-409.5, -0.4),
                                 (-409.2, -0.8), (-410.1, -1.5), (-409.6, -2.1), (-411.7, -3.7), (-414.4, -0.3), (-419.6, -4.3))),
    (1353885815, '79-19', 2, None, ((-403.1, 6.4), (-396.5, 13.3), (-391.5, 8.6), (-398.0, 1.7))),
    (1353885816, '79-15', 2, None, ((-402.6, 19.4), (-397.5, 15.0), (-404.6, 6.7), (-409.8, 11.1))),
    (1353885819, '73', 2, None, ((-421.2, 20.8), (-414.2, 11.1), (-418.4, 8.1), (-421.1, 12.0), (-427.7, 7.4), (-431.9, 13.2))),
    (1353885817, '79-13', 3, None, ((-419.6, 28.2), (-413.2, 35.3), (-403.2, 26.3), (-409.6, 19.2))),
    (1353885821, '69', 2, None, ((-426.3, 40.4), (-419.6, 35.7), (-430.6, 20.4), (-437.1, 25.0), (-433.2, 30.4), (-434.5, 31.3),
                                 (-431.1, 35.9), (-430.0, 35.2))),
    (1353885842, '', 3, None, ((-442.1, 20.0), (-432.4, 5.1), (-437.2, 0.2), (-439.5, 3.8), (-446.0, -0.3), (-454.4, 12.5))),
    (1353895467, '80', 2, None, ((-400.5, -18.0), (-394.3, -21.6), (-398.8, -29.2), (-405.0, -25.6))),
    (1441567924, '82', 2, None, ((-390.6, -21.0), (-383.2, -24.6), (-387.3, -35.6), (-396.3, -32.2))),
    (1353895462, '86', 1, 'giwa', ((-380.8, -22.0), (-374.3, -24.3), (-375.1, -26.5), (-370.7, -28.1), (-373.3, -35.3),
                                   (-376.5, -34.2), (-378.3, -39.2), (-386.1, -36.5))),
    (1353895463, '88-6', 2, None, ((-392.6, -34.9), (-378.3, -46.0), (-380.1, -47.7), (-377.7, -50.0), (-392.7, -61.9),
                                   (-395.6, -58.9), (-384.9, -49.3), (-396.6, -38.9))),
    (1353895469, '78', 3, None, ((-417.5, -10.6), (-406.8, -16.2), (-409.2, -20.8), (-410.6, -20.1), (-413.0, -24.6),
                                 (-416.4, -22.8), (-418.3, -26.4), (-424.2, -23.3))),
    (1353895470, '38', 2, None, ((-429.7, -3.3), (-418.8, -8.6), (-426.0, -23.5), (-437.0, -18.2))),
    (1353895466, '30-14', 2, None, ((-405.0, -26.7), (-401.3, -32.1), (-408.2, -36.7), (-411.9, -31.3))),
    (1353895464, '82-9', 2, None, ((-399.0, -36.9), (-392.2, -46.5), (-399.5, -51.3), (-402.2, -47.0), (-398.3, -44.1),
                                   (-402.1, -39.1))),
    (1353895465, '30-12', 2, None, ((-412.7, -35.7), (-410.4, -40.5), (-420.1, -45.1), (-422.5, -40.2))),
    (1353895474, '30-11', 1, None, ((-430.5, -28.1), (-421.6, -31.0), (-424.0, -34.5), (-432.1, -31.7), (-432.1, -28.7))),
    (1353885843, '', 2, None, ((-448.7, -0.6), (-439.8, -0.2), (-438.1, -3.7), (-443.2, -7.7), (-441.6, -9.1), (-448.5, -14.9),
                               (-455.4, -3.9))),
]
HOUSE_ID0 = 993000
SHED_ID = 993100
# ground points on the 1997-07-28 scans (26/15 · 26/16, 3 m grid, corr >= 0.85, off the roofs of OSM's houses and the
# halls, off the 대운동장's patch, outliers against their neighbours out): (x, y, the photos' height + 0.3 m)
ZPTS = [
    (-344, -80, 38.4), (-329, -80, 40.2), (-323, -80, 40), (-311, -80, 40.8), (-305, -80, 40.4), (-302, -80, 40.9),
    (-293, -80, 42.6), (-284, -80, 42), (-344, -77, 38.5), (-332, -77, 40.1), (-323, -77, 40.3), (-320, -77, 40.8),
    (-311, -77, 40.7), (-305, -77, 41), (-290, -77, 42.7), (-344, -74, 38.6), (-341, -74, 38.7), (-335, -74, 38.9),
    (-332, -74, 40.3), (-323, -74, 40.6), (-320, -74, 40.9), (-317, -74, 40.9), (-314, -74, 40.7), (-305, -74, 41.7),
    (-302, -74, 41.8), (-299, -74, 42.3), (-290, -74, 42.7), (-287, -74, 42.9), (-344, -71, 38.8), (-341, -71, 38.8),
    (-338, -71, 38.8), (-335, -71, 39.1), (-332, -71, 40.1), (-323, -71, 40.7), (-320, -71, 40.7), (-317, -71, 40.7),
    (-314, -71, 40.5), (-305, -71, 41.7), (-302, -71, 42.1), (-293, -71, 42.7), (-290, -71, 42.7), (-347, -68, 38.9),
    (-344, -68, 38.9), (-341, -68, 38.9), (-338, -68, 39), (-335, -68, 39.5), (-332, -68, 40.2), (-320, -68, 40.6),
    (-317, -68, 40.7), (-314, -68, 40.8), (-311, -68, 41.3), (-308, -68, 41.6), (-305, -68, 41.8), (-302, -68, 42.1),
    (-299, -68, 42.3), (-296, -68, 42.8), (-293, -68, 43), (-344, -65, 39.2), (-338, -65, 39.3), (-335, -65, 39.6),
    (-332, -65, 40.1), (-317, -65, 40.8), (-314, -65, 41), (-311, -65, 41.3), (-308, -65, 41.6), (-305, -65, 41.7),
    (-302, -65, 42.1), (-299, -65, 42.3), (-338, -62, 39.4), (-335, -62, 39.8), (-332, -62, 39.9), (-326, -62, 41.7),
    (-323, -62, 40.8), (-320, -62, 41), (-317, -62, 41), (-305, -62, 41.5), (-302, -62, 42.2), (-299, -62, 42.4),
    (-296, -62, 42.9), (-287, -62, 44.6), (-338, -59, 40), (-335, -59, 39.9), (-332, -59, 40.1), (-329, -59, 39.9),
    (-317, -59, 41.2), (-302, -59, 43), (-299, -59, 43.1), (-287, -59, 45), (-431, -56, 41.6), (-428, -56, 41.8),
    (-341, -56, 40.7), (-338, -56, 40.4), (-335, -56, 40), (-332, -56, 40.2), (-323, -56, 40.7), (-320, -56, 41),
    (-317, -56, 41.1), (-434, -53, 41.6), (-431, -53, 41.5), (-404, -53, 43.1), (-341, -53, 40.4), (-338, -53, 40.2),
    (-335, -53, 40), (-332, -53, 40.3), (-329, -53, 40.5), (-296, -53, 45), (-434, -50, 41.7), (-428, -50, 41.4),
    (-341, -50, 39.9), (-338, -50, 40.1), (-335, -50, 40.1), (-332, -50, 40.6), (-299, -50, 44.9), (-287, -50, 45.7),
    (-407, -47, 42.6), (-341, -47, 40.3), (-338, -47, 40.2), (-335, -47, 40.3), (-332, -47, 40.9), (-314, -47, 44.4),
    (-311, -47, 44.5), (-308, -47, 44.7), (-305, -47, 44.4), (-302, -47, 44.9), (-299, -47, 45.1), (-296, -47, 45.4),
    (-287, -47, 45.4), (-422, -44, 40.2), (-404, -44, 42.6), (-401, -44, 42.8), (-344, -44, 40), (-338, -44, 40.3),
    (-335, -44, 40.4), (-314, -44, 44.9), (-308, -44, 45), (-305, -44, 45), (-299, -44, 45.3), (-296, -44, 45.6),
    (-293, -44, 45.6), (-290, -44, 45.6), (-284, -44, 45.7), (-431, -41, 38), (-344, -41, 40.1), (-338, -41, 40.6),
    (-335, -41, 40.7), (-323, -41, 44.7), (-317, -41, 45.1), (-314, -41, 45.2), (-311, -41, 45.3), (-305, -41, 45.3),
    (-299, -41, 45.6), (-296, -41, 45.6), (-293, -41, 45.5), (-440, -38, 40.8), (-422, -38, 40), (-410, -38, 40),
    (-347, -38, 40.9), (-341, -38, 40.7), (-338, -38, 40.8), (-320, -38, 45.2), (-317, -38, 45.1), (-314, -38, 45.2),
    (-308, -38, 45.5), (-305, -38, 45.6), (-302, -38, 45.7), (-299, -38, 45.7), (-296, -38, 45.7), (-293, -38, 45.4),
    (-347, -35, 40.3), (-344, -35, 40.6), (-341, -35, 41), (-338, -35, 41.4), (-326, -35, 45), (-323, -35, 45.1),
    (-317, -35, 45.4), (-314, -35, 45.3), (-308, -35, 45.6), (-305, -35, 45.6), (-371, -32, 42.8), (-368, -32, 42.2),
    (-350, -32, 40.8), (-344, -32, 41.3), (-341, -32, 41.9), (-329, -32, 44.7), (-323, -32, 45.3), (-317, -32, 45.5),
    (-365, -29, 41.6), (-347, -29, 41.5), (-344, -29, 41.9), (-341, -29, 42.3), (-338, -29, 42.5), (-329, -29, 44.6),
    (-323, -29, 45.5), (-320, -29, 45.5), (-305, -29, 45.5), (-410, -26, 39.6), (-407, -26, 39.8), (-347, -26, 42.6),
    (-344, -26, 43.1), (-326, -26, 45.2), (-323, -26, 45.4), (-320, -26, 45.5), (-350, -23, 42.4), (-344, -23, 43.3),
    (-335, -23, 44.1), (-329, -23, 45), (-323, -23, 45.3), (-338, -20, 44.4), (-332, -20, 44.2), (-392, -17, 37.3),
    (-440, -14, 32.8), (-392, -14, 37.2), (-389, -14, 37.5), (-350, -14, 45.2), (-392, -11, 38.7), (-389, -11, 38.5),
    (-353, -11, 45.8), (-350, -11, 45.4), (-398, -8, 39.2), (-392, -8, 39.1), (-353, -8, 46.1), (-350, -8, 45.8),
    (-347, -8, 45.7), (-392, -5, 39.2), (-353, -5, 46.2), (-350, -5, 46.2), (-401, -2, 40.7), (-395, -2, 40.4),
    (-353, -2, 47.6), (-312, -128, 40.1), (-308, -128, 39.7), (-312, -124, 39.4), (-292, -120, 42.3), (-284, -100, 42.1),
    (-308, -96, 40), (-324, -92, 39.9), (-316, -92, 40.5), (-312, -92, 40.4), (-304, -92, 41.4), (-284, -92, 40.8),
    (-344, -88, 38.1), (-328, -88, 40.5), (-320, -88, 40.3), (-304, -88, 41.2), (-348, -84, 37.9), (-344, -84, 38.3),
    (-340, -84, 38.7), (-336, -84, 38.9), (-332, -84, 39.1), (-328, -84, 39.7), (-320, -84, 40.7), (-304, -84, 40.5),
    (-300, -84, 41.4),
]


def _line(V, step=1.0):
    """dict(s, p, z, ls) every `step` m along the vertices; z: None where the game's ground is to be kept"""
    P = np.array([(x, y) for x, y, _ in V], float)
    seg = np.hypot(*np.diff(P, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    ss = np.arange(0.0, cum[-1] + 1e-6, step)
    p = np.stack([np.interp(ss, cum, P[:, 0]), np.interp(ss, cum, P[:, 1])], 1)
    z = np.array([np.nan if v[2] is None else v[2] for v in V], float)
    return dict(s=ss, p=p, cum=cum, zv=z, ls=LineString([tuple(q) for q in P]))


def _z_along(L, s, ground0):
    """the line's surface at s: its own heights, eased into the game's ground (ground0) over the vertices without one"""
    zv = L['zv'].copy()
    ok = ~np.isnan(zv)
    if not ok.all():
        P = np.array(L['ls'].coords)
        for i in np.nonzero(~ok)[0]:
            zv[i] = ground0(*P[i])
    return np.interp(s, L['cum'], zv)


def _bilinear(H, x0, step):
    def f(x, y):
        fx = np.clip((np.asarray(x, float) - x0) / step, 0, H.shape[1] - 1.001)
        fy = np.clip((np.asarray(y, float) - x0) / step, 0, H.shape[0] - 1.001)
        i, j = fx.astype(int), fy.astype(int)
        ax, ay = fx - i, fy - j
        return H[j, i] * (1 - ax) * (1 - ay) + H[j, i + 1] * ax * (1 - ay) + H[j + 1, i] * (1 - ax) * ay + H[j + 1, i + 1] * ax * ay
    return f


def corridors():
    """the road, the lane, the path along the wall, the alley: [(name, line, half width)]"""
    return [('road', _line(ROAD), ROAD_HALF), ('lane', _line(LANE), LANE_HALF), ('arc', _line(ARC), ARC_HALF),
            ('alley', _line(ALLEY), ALLEY_HALF)]


def grade(Hn, X, Y, FIXED, halls, field_patch, fill, half=800.0, step=5.0, sigma=6.0, prior=0.05):
    """The ground round the gate on the 1997 photos' heights, late (the planting has read the ground as it was):
    every grid node in reach takes the photos' difference from the game's ground (ZPTS and the corridors' surfaces,
    Gaussian-weighted, sigma 6 m; far from them it fades to nothing), nodes on a corridor its surface (FIXED after),
    the mouth inside the gate between the posts' level and the road's.  The halls' feet stay (their outlines + 3 m
    count as unchanged ground), nodes another rule set (FIXED) stay.  The 대운동장's patch round the oval is then
    smoothed again (harmonic_fill) between the oval and what was changed here, north of y -150 only (성산로's bank stays).
    Returns the nodes it set (to be FIXED) and a summary."""
    H0 = Hn.copy()
    g0 = _bilinear(H0, -half, step)
    C = corridors()
    cx, cy, cd = [], [], []
    for _, L, _ in C:
        zs = _z_along(L, L['s'], g0)
        for (x, y), z in zip(L['p'][::2], zs[::2]):
            cx.append(x); cy.append(y); cd.append(z - g0(x, y))
    for x, y, z in ZPTS:
        cx.append(x); cy.append(y); cd.append(z - g0(x, y))
    # the halls' feet: unchanged
    for h in halls:
        ring = h.buffer(3.0).exterior
        for d in np.arange(0.0, ring.length, 3.0):
            q = ring.interpolate(d)
            cx.append(q.x); cy.append(q.y); cd.append(0.0)
    # the campus road north of 과학관's corner and the strip west of it stay as they are
    for y in np.arange(8.0, 36.0, 3.0):
        for x in (-357.0, -353.0, -349.0, -345.0):
            cx.append(x); cy.append(y); cd.append(0.0)
    cx, cy, cd = np.array(cx), np.array(cy), np.array(cd)
    m = (X > -470) & (X < -265) & (Y > -160) & (Y < 45) & ~FIXED
    near_hall = shapely.contains_xy(unary_union(halls).buffer(2.0), X, Y)
    m &= ~near_hall
    m &= ~shapely.contains_xy(field_patch, X, Y)
    xs, ys = X[m], Y[m]
    d2 = (xs[:, None] - cx[None]) ** 2 + (ys[:, None] - cy[None]) ** 2
    w = np.exp(-d2 / (2 * sigma * sigma))
    dz = (w * cd[None]).sum(1) / (w.sum(1) + prior)
    Hn[m] = H0[m] + dz
    # the corridors' beds: level across, their own surface
    took = np.zeros(X.shape, bool)
    for nm, L, hw in C:
        sel = (X > L['p'][:, 0].min() - 8) & (X < L['p'][:, 0].max() + 8) & (Y > L['p'][:, 1].min() - 8) & \
            (Y < L['p'][:, 1].max() + 8) & ~FIXED & ~near_hall
        if not sel.any():
            continue
        pts = shapely.points(np.stack([X[sel], Y[sel]], 1))
        dist = shapely.distance(L['ls'], pts)
        s = shapely.line_locate_point(L['ls'], pts)
        z = _z_along(L, s, g0)
        on = (dist <= hw + 1.25) & (s > 0.01) & (s < L['cum'][-1] - 0.01)
        jj, ii = np.nonzero(sel)
        Hn[jj[on], ii[on]] = z[on]
        took[jj[on], ii[on]] = True
    # the mouth: between the posts (GATE_Z) and the road's west edge
    ap = Polygon(APRON).buffer(1.0)
    sel = shapely.contains_xy(ap, X, Y) & ~FIXED & ~took
    rl = C[0][1]
    for j, i in zip(*np.nonzero(sel)):
        x, y = X[j, i], Y[j, i]
        dg = Point(x, y).distance(LineString(GATE))
        s = rl['ls'].project(Point(x, y))
        zr = float(_z_along(rl, np.array([s]), g0)[0])
        dr = max(rl['ls'].distance(Point(x, y)) - ROAD_HALF, 0.0)
        Hn[j, i] = (GATE_Z * dr + zr * dg) / (dr + dg + 1e-6)
        took[j, i] = True
    # the 대운동장's bank: smooth again from the oval out to the new ground (north half)
    fm = shapely.contains_xy(field_patch, X, Y) & ~FIXED & ~took & (Y > -150) & (X > -440)
    if fm.any():
        fill(fm)
    moved = np.abs(Hn - H0)
    return took, dict(nodes=int((moved > 0.05).sum()), most=float(moved.max()), road=int(took.sum()), bank=int(fm.sum()))


def takeup(paths_out):
    """the game's road north-east of the 대운동장 (OSM 2026, ending at -317.5, -119.6 in today's car park) north of
    where the 1997 road meets it, and a stub of that car park east of the road: (line, width, cap)"""
    old = []
    for p_ in paths_out:
        if p_['kind'] == 'service' and len(p_['pts']) > 1 and math.dist(p_['pts'][-1], (-317.5, -119.6)) < 1.0:
            L = LineString(p_['pts'])
            old.append((L.intersection(Polygon([(-330, -150), (-295, -150), (-295, -110), (-330, -110)])), p_.get('w', 6.0), 'flat'))
        elif p_['kind'] == 'road' and len(p_['pts']) > 1 and math.dist(p_['pts'][0], (-330.0, -53.5)) < 2.0:
            old.append((LineString(p_['pts']), p_.get('w', 6.0), 'round'))      # (a stub of today's car park east of the road)
    return old


def paint():
    """(asphalt, bare yard) polygons for the ground map"""
    C = corridors()
    road = C[0][1]['ls'].buffer(ROAD_HALF, cap_style='flat')
    houses = unary_union([Polygon(h[4]).buffer(0) for h in HOUSES])
    lane = C[1][1]['ls'].buffer(LANE_HALF + LANE_EDGE, cap_style='flat').difference(houses)
    arc = C[2][1]['ls'].buffer(ARC_HALF, cap_style='flat')
    alley = C[3][1]['ls'].buffer(ALLEY_HALF, cap_style='flat')
    asph = unary_union([road, lane, arc, alley, Polygon(APRON).buffer(0)])
    yard = Polygon(YARD).buffer(0).difference(asph).difference(Polygon(SHED).buffer(0.2))
    return asph, yard


def houses(ground):
    """campus.json buildings: the lane's houses (two-to-four-storey city blocks; 86 with a tiled hipped roof as on
    the scans) and the small building south of the mouth (one storey, its roof on the scans)"""
    out = []
    for k, (oid, nm, lv, roof, g) in enumerate(HOUSES):
        poly = shapely.geometry.polygon.orient(Polygon(g).buffer(0), 1.0)
        hs = [ground(x, y) for x, y in poly.exterior.coords]
        b = dict(id=HOUSE_ID0 + k, name='', style='city', levels=lv, height=round(lv * 3.0, 2), base=round(min(hs), 2),
                 top_ground=round(max(hs), 2), footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]])
        if roof == 'giwa':
            b['hip'] = dict(mat='roof_giwa', pitch=0.5, over=0.5)
        out.append(b)
    poly = shapely.geometry.polygon.orient(Polygon(SHED), 1.0)
    hs = [ground(x, y) for x, y in poly.exterior.coords]
    z0 = min(hs)
    fh = max(SHED_TOP - 0.9 - z0, 2.6)
    out.append(dict(id=SHED_ID, name='', style='white', levels=1, height=round(fh, 2), fh=round(fh, 3), base=round(z0, 2),
                    top_ground=round(max(hs), 2), footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]]))
    return out


def gate(ground):
    """campus.json 「seomun」: the posts (centres, the line's direction), the leaves, the walls with their tops and feet
    every metre (blender/landmarks.py seomun draws them)"""
    a, b = np.array(GATE[0]), np.array(GATE[1])
    t = (b - a) / np.linalg.norm(b - a)
    n = np.array([-t[1], t[0]])                      # (into the campus: east-south-east)
    posts = [a - t * 0.4, b + t * 0.4]

    def run(V, kind):
        L = LineString(V)
        q = []
        for d in np.arange(0.0, L.length + 1e-6, 1.0):
            p = L.interpolate(d)
            p1 = L.interpolate(min(d + 0.5, L.length)); p0 = L.interpolate(max(d - 0.5, 0.0))
            tt = np.array([p1.x - p0.x, p1.y - p0.y]); tt /= np.linalg.norm(tt)
            nn = np.array([-tt[1], tt[0]])
            ga, gb = ground(p.x + nn[0] * 1.2, p.y + nn[1] * 1.2), ground(p.x - nn[0] * 1.2, p.y - nn[1] * 1.2)
            q.append([round(p.x, 2), round(p.y, 2), round(min(ga, gb, ground(p.x, p.y)) - 0.4, 2),
                      round(max(ga, gb, ground(p.x, p.y)), 2)])
        return dict(kind=kind, pts=q)
    return dict(posts=[[round(float(p[0]), 2), round(float(p[1]), 2), round(ground(*p), 2)] for p in posts],
                t=[round(float(t[0]), 4), round(float(t[1]), 4)], n=[round(float(n[0]), 4), round(float(n[1]), 4)],
                z=round(ground(*(a + b) / 2), 2), width=round(float(np.linalg.norm(b - a)), 2),
                walls=[run(WALL_N, 'granite'), run(WALL_S, 'block')])


def move_off(trees, shrubs, props, taken):
    """what stood where the new roads, the lane and the houses are: trees step aside to the edge (in their places in
    the list), shrubs and props go"""
    sh = taken.buffer(0.6)
    shapely.prepare(sh)
    n0 = (len(shrubs), len(props))
    shrubs[:] = [s for s in shrubs if not sh.contains(Point(s[1], s[2]))]
    props[:] = [p for p in props if not sh.contains(Point(p[1], p[2]))]
    e = sh.buffer(1.0).boundary
    moved = 0
    for t in trees:
        if sh.buffer(0.3).contains(Point(t[1], t[2])):
            q = nearest_points(e, Point(t[1], t[2]))[0]
            t[1], t[2] = round(q.x, 2), round(q.y, 2)
            moved += 1
    return n0[0] - len(shrubs), n0[1] - len(props), moved


def paths():
    """the map's ways for the new road, the lane and its alleys"""
    C = corridors()
    kinds = {'road': 'service', 'lane': 'residential', 'arc': 'residential', 'alley': 'residential'}
    return [dict(kind=kinds[nm], w=round(2 * hw, 1), pts=[[round(float(x), 1), round(float(y), 1)] for x, y in L['p'][::4]] +
                 [[round(float(L['p'][-1][0]), 1), round(float(L['p'][-1][1]), 1)]]) for nm, L, hw in C]
