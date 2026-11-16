"""중앙도서관 북쪽 찻길 (reference/고증/3.2-3.3 「북쪽 찻길과 그 둘레 (2026-11-17)」).

1997년 7월 원본 스캔(26/16 · 26/15 · 27/17 · 27/16)과 잎 없는 1996년 겨울 장에서 도서관 북쪽 찻길은 한 장의 아스팔트다:
남쪽 가는 화단 · 바깥 길 머리의 연석(s 85.5), 그 북쪽에 길 따라 선 차 줄(s 86 ~ 88), 가운데 차로, 북쪽 가에 머리를 북쪽
나무 띠로 넣은 직각 줄(s 92.3 ~ 97.7). 게임은 그 넓이를 이미 아스팔트로 깔았으나(LIB97_NORTH 와 OSM 의 길) 두 곳이 다르다.
- 화단 북쪽 끝: 게임은 s 82.4(LIB97 beds)에서 아스팔트가 시작했으나, 1997년의 연석은 s 85.5. 화단과 비스듬한 길 · 바깥 길이
  그 연석까지 이어짐. 화단 북쪽 가에는 둥근 상록 관목이 다섯(1996년 겨울 네 장, 1997년 7월 네 장에서 같은 자리)
- 테라스 북쪽 띠 너머와 테라스 서쪽 옹벽 앞(o −27 ~ 13.4): 게임은 잔디와 지금의 보행로였으나, 1997년에는 찻길의 서쪽 끝이
  북쪽 계단 발치와 도서관 북쪽 면 앞 띠 · 굽은 길(libwest97)까지 이어진 아스팔트이고, 그 위에 길 따라 선 차 둘
  (tools/cars97_new.json 끝 「중앙도서관 북쪽 찻길 서쪽 끝」)
높이는 게임 그대로: 연석(s 85.5)의 높이 해발 33.5 ± 0.15 m(같은 코스 짝의 시차)와 길가 차 줄의 차 밑 33.2 ~ 33.4 m 가 게임과
0.1 m 안, 서쪽 끝 차로 33.5 m 는 게임보다 0.15 m 낮을 뿐이라 고르지 않는다.
build_campus.py 가 무작위 심기 뒤의 칠(paint) · 목록을 쓸 때 부른다(땅의 높이는 바꾸지 않음).
"""
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

O = (-85.44, -71.08)                     # 도서관 정면 틀(libsouth97 · libwest97 과 같음): 남동 모서리, s 북쪽, o 동쪽
T = (0.25441, 0.9671)
N = (0.9671, -0.25441)


def so(s, o):
    return (O[0] + T[0] * s + N[0] * o, O[1] + T[1] * s + N[1] * o)


def rect(s0, s1, o0, o1):
    return Polygon([so(s0, o0), so(s1, o0), so(s1, o1), so(s0, o1)])


BEDS_N_GAME = 82.4                       # 게임 화단의 북쪽 끝(build_campus.py LIB97 beds: 무작위 심기가 읽은 것이라 그대로)
KERB = 85.5                              # 1997년 화단 · 바깥 길 머리의 북쪽 연석(s)
BED_O = (21.0, 41.6)                     # 화단(관목 띠를 따르는 찻길 동쪽 가 ~ 바깥 길)
OUTER_O = (41.6, 45.2)                   # 화단 바깥 길
SLANT = ((85.6, 41.6), (47.3, 21.0))     # 북쪽 비스듬한 길의 가운데 선(LIB97 slant), 폭 4 m
SLANT_W = 4.0
# 화단 북쪽 가의 둥근 상록 관목(s, o): 1996년 겨울 26/15 · 26/16 · 27/16 · 27/17 과 1997년 7월 네 장의 어두운 덩이(0.3 ~ 0.7 m 안)
SHRUBS = [(84.4, 22.3), (84.4, 27.0), (84.4, 30.6), (84.4, 33.6), (84.5, 35.9)]
# 찻길의 서쪽 끝: 테라스 북쪽 띠(s 85.4 ~ 87.6, o −16 ~ 13.4) 북쪽, 북쪽 계단 발치(o −20 ~ −16.4)는 테라스 끝(s 85.4)부터, 테라스
# 서쪽 옹벽(o −20.5)과 서쪽 길 · 자재 마당의 아랫단(libwest97.LOWER, 동쪽 가 o −25 ~ −29) 사이도(26/15: 차가 선 북쪽 면 앞 띠와 한 포장)
WEST = Polygon([so(77.0, -27.0), so(77.0, -20.6), so(85.4, -20.6), so(85.4, -16.2), so(87.6, -16.2), so(87.6, 13.4),
                so(92.8, 13.4), so(92.8, -30.0)])
# 지금의 보행로가 1997년 찻길 · 직각 줄을 가로지르는 곳(이 안에 길이의 70 % 넘게 든 보행로는 지도 · 사람의 길에서 뺌)
WALK_CUT = rect(84.5, 99.0, -22.5, 13.4)


def bed_ext():
    """게임의 아스팔트(LIB97_NORTH)에서 뺄 곳: 화단 북쪽 끝에서 1997년 연석까지(화단 · 바깥 길 폭)"""
    return rect(BEDS_N_GAME - 0.05, KERB, BED_O[0], OUTER_O[1])


def walks():
    """비스듬한 길의 머리와 바깥 길을 연석까지(보도블록)"""
    a, b = so(*SLANT[0]), so(*SLANT[1])
    d = ((b[0] - a[0]), (b[1] - a[1]))
    n = (d[0] ** 2 + d[1] ** 2) ** 0.5
    u = (d[0] / n, d[1] / n)
    line = LineString([(a[0] - u[0] * 3.0, a[1] - u[1] * 3.0), b])
    slant = line.buffer(SLANT_W / 2, cap_style=2).intersection(bed_ext())
    return [unary_union([slant, rect(BEDS_N_GAME - 0.05, KERB, OUTER_O[0], OUTER_O[1])])]


def west():
    """찻길 서쪽 끝의 아스팔트"""
    return [WEST]


def shrubs():
    """화단 북쪽 가의 관목(목록 끝에 더함: 다른 관목은 그대로)"""
    return [['topiary_round', *(round(c, 2) for c in so(s, o)), 1.2, round(0.7 * k, 2)] for k, (s, o) in enumerate(SHRUBS)]


def move_off(trees, shrubs_, props):
    """새 아스팔트(WEST) 위에 심긴 것: 나무는 가까운 가장자리 밖으로(목록 제자리), 관목 · 소품은 뺌. 돌려주는 것: (나무, 관목, 소품)"""
    from shapely.ops import nearest_points
    zone = WEST.buffer(0.6)
    edge = zone.buffer(0.6).exterior
    moved = []
    for t in trees:
        if zone.contains(Point(t[1], t[2])):
            q = nearest_points(edge, Point(t[1], t[2]))[0]
            moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
            t[1], t[2] = round(q.x, 2), round(q.y, 2)
    ns, npr = len(shrubs_), len(props)
    shrubs_[:] = [s for s in shrubs_ if not zone.contains(Point(s[1], s[2]))]
    props[:] = [p for p in props if not zone.contains(Point(p[1], p[2]))]
    return moved, ns - len(shrubs_), npr - len(props)


def walks_cut(paths):
    """지도 · 사람이 읽는 보행로에서 WALK_CUT 안의 것을 뺌. 돌려주는 것: 뺀 수"""
    n = len(paths)
    paths[:] = [p for p in paths if not (p['kind'] in ('footway', 'path') and len(p['pts']) > 1
                                         and LineString(p['pts']).intersection(WALK_CUT).length > 0.7 * LineString(p['pts']).length)]
    return n - len(paths)
