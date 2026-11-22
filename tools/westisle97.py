"""스팀슨관 서쪽 찻길의 화단 섬과 그 남쪽 찻길 (reference/고증/2.9.3_서쪽_화단_섬과_서쪽_길.md 「서쪽 화단 섬과 서쪽 길: 1996년 겨울 사진」).  tools/build_campus.py 가 부른다.

    westisle97.LANE                      # 서쪽 찻길(TR_W)의 섬 구간 가운데 선: 심기가 끝난 뒤 이 선으로 다시 그음
    westisle97.ISLAND, .GARDEN           # 1996 · 1997년의 섬(잔디), 섬 남쪽 숲 정원의 북쪽 연석 안쪽(잔디)
    westisle97.asphalt(road)             # 섬 둘레 아스팔트: 새 찻길 선의 띠와 옛 섬 자리, 정원 · 섬 밖
    westisle97.lawn()                    # 잔디로 되돌릴 곳(섬, 정원 북쪽 끝): 정원의 보도는 남김
    westisle97.path_pts()                # campus.json paths 의 섬 남쪽 찻길(지도)

Frame: campus metres, x east, y north (the block frame of the 1997 aerial photos).  Nothing here draws from
build_campus.py's `rng`: the old line (OSM's road round the island's south, 4 m north of the 1997 one) is what the
ground was graded along and what the planting read; this is laid after the planting.

What was measured (고증 2.9.3 「서쪽 화단 섬과 서쪽 길: 1996년 겨울 사진」): the leafless scans of 1996 (26/14 · 26/15 · 26/16 of
12-23, 27/15 · 27/16 · 27/17 of 11-28) and the July 1997 scans, brightness profiles across each kerb on the plane of
the road's height (해발 50.0 m; the pairs' surface 49.6 - 50.1 m there), the kerb where five or six frames agree:
- the island: its east kerb x -23.1 (y 217 - 218.5), -23.3 (220), -23.6 (221.5), -24.1 (223) in six 1996 and four 1997
  frames (±0.3 m), its round north end's top (-25.9, 224.5) and west end (-29.1, 222.5) on 27/15 · 27/16 of 1997, its
  south tip (-24.3, 215.4) and south-west side (-26.5, 216.3) · (-27.5, 218.0) · (-28.5, 219.2) on five or six 1996
  frames (±0.4 - 0.6 m).  The 2006 survey's island is the same within 1.2 m.  The game's island stood 2 - 4 m north
  of it, its road round the island's south over the island's south half.
- the garden south of it (the wood between the two roads): its north kerb y 210.8 (x -32), 211.2 (-30), 210.85 (-28),
  210.35 (-26), 210.1 (-24), 209.55 (-22) on six frames (±0.2 - 0.7 m); the game's garden reached 4 - 5 m farther
  north.  Between the kerb and the island 5.3 m (x -24) - 7.5 m (x -28) of road, open to the road west of the island
  and to the wide paved place east of it: the cars' way round the island's south.
"""
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

ISLAND = Polygon([(-24.3, 215.4), (-26.5, 216.4), (-27.5, 217.9), (-28.6, 219.3), (-29.1, 222.5), (-28.0, 223.9), (-25.9, 224.5),
                  (-24.1, 223.0), (-23.6, 221.5), (-23.3, 220.0), (-23.1, 218.5), (-23.1, 217.0)]).buffer(0.4).buffer(-0.4)
# the garden's north kerb (west to east), then its sides as the roads' kerbs: the road west of it (OSM's line + 3 m) and
# 스팀슨관's west road (the 2008 survey's edge line + 0.35 m: the 1996 scans' bright edge at (-16.0, 201) agrees)
GARDEN_KERB = [(-34.0, 209.1), (-32.0, 210.8), (-30.0, 211.2), (-28.0, 210.85), (-26.0, 210.35), (-24.0, 210.1), (-22.0, 209.55),
               (-20.0, 208.3), (-18.45, 206.3), (-17.75, 204.3), (-16.75, 201.0)]
GARDEN = Polygon([(-36.1, 200.0), (-35.4, 203.0), (-34.9, 205.5), (-34.4, 207.6)] + GARDEN_KERB + [(-16.4, 200.0)])
# the cars' west road round the island (TR_W's raw points between (-14.5, 204.6) and (-36.1, 210.7)): the middle of the
# road between the garden's kerb and the island, so that the two lanes (1.35 m either side) keep 0.2 - 0.4 m off both;
# LANE_R the corner's radius where it meets the road west of the island (the inner lane round the garden's corner)
LANE = [(-16.6, 210.9), (-21.0, 212.3), (-24.6, 212.9), (-27.5, 213.45), (-30.5, 213.95), (-33.8, 213.3)]
LANE_R = 4.5
# the old island the game had (the gap OSM's three roads left: x -27.5 .. -23.5, y 221.7 .. 226), paved again round
# the 1997 island
OLD_ISLAND = box(-28.6, 220.5, -22.4, 227.0)
# the road's 1997 heights on the new line (해발; the 1996 pairs, 1.2 m windows, n 3 - 4 within 0.2 - 0.5 m:
# (-21, 212) 48.8, (-27, 213.3) 49.6, (-28, 213) 49.75, (-33, 212.6) 50.15), for kwangbok97.ROAD_W
ROAD_Z = [(-17.4, 210.2, 48.35), (-21.0, 212.3, 48.85), (-27.5, 213.4, 49.7), (-33.0, 212.8, 50.15)]
# the 5 m grid's nodes north of the road (y 220: on the island, west and east of it) that kwangbok97.grade lays on the
# road's height as corners of the cells the wheels cross: they go back to its GRID (the survey's surface, 0.5 - 1.3 m
# higher: the place rises 16 % to the north, as OSM's road north of it, kwangbok97.ROAD_N1)
NORTH_NODES = [(-35.0, 220.0), (-30.0, 220.0), (-25.0, 220.0), (-20.0, 220.0)]
# the garden's walk (OSM's footway down its east part: the 1996 scans' bright edge at x -21.1, y 201 - 204) stays paved
GARDEN_WALK = LineString([(-22.0, 208.4), (-22.9, 204.1), (-22.3, 198.9)])


def asphalt(road):
    """the late asphalt round the island: `road` (the new line's band, a polygon) and the old island, less the garden and
    the island"""
    return unary_union([road, OLD_ISLAND]).difference(GARDEN).difference(ISLAND.buffer(0.15)).buffer(0)


def lawn():
    """lawn again: the island, the garden's north end (where the old asphalt reached into it) but its walk"""
    g = GARDEN.intersection(box(-40.0, 203.0, -10.0, 216.0)).difference(GARDEN_WALK.buffer(1.6))
    return unary_union([ISLAND, g]).buffer(0)


def path_pts():
    """OSM's service road round the island's south (campus.json paths) on the 1997 line"""
    return [[round(x, 1), round(y, 1)] for x, y in LANE] + [[-36.1, 210.7]]


def check(lane, half=0.9):
    """(lane: one lane of the traffic loop abreast of the island, points) the least clearance of a car (half its width)
    to the island and to the garden's kerb, m"""
    ls = LineString(lane)
    return round(float(ls.distance(ISLAND)) - half, 2), round(float(ls.distance(LineString(GARDEN_KERB))) - half, 2)
