"""Build the 1997 Yonsei campus dataset from OpenStreetMap + elevation data.

Inputs : data/raw/osm_campus.json (Overpass), data/terrain.json, data/terrain_far.json
Outputs: data/campus.json                (used by Blender build + web)
         web/public/data/campus.json     (same, for the browser)
         web/public/data/terrain_near.bin / terrain_far.bin (Float32, row-major south->north)
         web/public/assets/textures/ground_splat.png, ground_dry.png, ground_leaves.png
         data/debug_map.png              (top-down sanity check)

Local frame: x = east (m), y = north (m), origin lat 37.5640 / lon 126.9380.
Run with the project venv:  .venv/bin/python tools/build_campus.py
"""
import json, math, os, random
import numpy as np
from scipy import ndimage
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union, substring, linemerge, nearest_points
import shapely
import shapely.validation
from PIL import Image, ImageDraw
import gate_town
import sinchon_rotary

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
LAT0, LON0 = 37.5640, 126.9380
rng = random.Random(1997)


def xy(p):
    return ((p['lon'] - LON0) * 111320 * math.cos(math.radians(LAT0)), (p['lat'] - LAT0) * 110574)


osm = json.load(open(os.path.join(ROOT, 'data/raw/osm_campus.json')))['elements']
ways = {e['id']: e for e in osm if e.get('geometry')}

# ---------------------------------------------------------------------------
# 1997 building table.  OSM way id -> (style, levels, label override)
#   style 'lm:<builder>' = hand-modelled landmark (see blender/landmarks.py)
#   other styles = procedural facade generator (blender/generic.py)
# Buildings built after 1997 (학술정보원, 공학원, 새천년관, 경영관, 백양누리, 암병원 ...)
# are intentionally omitted.
# ---------------------------------------------------------------------------
# Names are the ones a 1997 student used (several halls were renamed in 1999, 2001 and 2013); halls built after
# May 1997 are left out, the ones going up then are marked 공사중.  Checked against the university's building history
# (yonsei.ac.kr/sc/349/subview.do), namu.wiki and OSM; three outlines once listed here are on the Ewha campus.
# A landmark's levels are the record's storeys above ground (its shape is blender/landmarks.py's); they only set the
# height of its name tag (reference/고증.md 3.1.1).
B = {
    163525865: ('lm:library', 6, '중앙도서관'),         # 1979 five storeys, six since 1992
    1444448640: ('lm:union', 4, '학생회관'),
    1444448646: ('white', 2, '학생회관 별관'),       # two storeys in 1997 (ANNEX_1997 below)
    324328422: ('lm:centennial', 4, '백주년기념관'),
    246156115: ('lm:underwood', 3, '언더우드관'),
    246156116: ('lm:appenzeller', 3, '아펜젤러관'),   # two storeys and the attic storey in the roof
    246156118: ('lm:stimson', 2, '스팀슨관'),
    371403811: ('lm:auditorium', 4, '대강당'),
    429249499: ('lm:chapel', 2, '루스채플'),
    205583531: ('lm:engineering', 5, '제1공학관'),
    246156113: ('stone', 3, '핀슨관'),
    429249496: ('lm:hanok', 1, '광혜원'),
    # engineering / science quarter
    # (제1공학관's 공AS block, 1451926794, is the 2015 north wing: a car park in the 1997 photo; see FOOTPRINT_1997)
    1451926793: ('modern', 5, '제1공학관'), 1451926787: ('modern', 5, '제1공학관'),
    256932940: ('modern', 7, '제2공학관'),
    224955691: ('modern', 5, '제3공학관 (공사중)'), 324328471: ('white', 2, '별동연구동'),
    222843398: ('white', 6, '과학관'), 468614722: ('lm:kwangbok', 4, '광복관'),   # (blender/landmarks.py kwangbok)
    256933753: ('white', 5, '경영학교실단'),    # (OSM: 백양관) the old 상경대학 hall, 「경영관」 to students; 백양관 since
                                               # June 1999 (연세춘추 1999.5.3).  Its two wings and low front: below
    421415366: ('gym', 2, '체육관'), 421415365: ('white', 4, '체육교육관'),
    # humanities / north campus
    246156112: ('modern', 6, '인문관'), 246156114: ('modern', 3, '인문관'),
    246156119: ('white', 4, '제2인문관 (공사중)'), 245623759: ('lm:yeonhui', 6, '연희관'),   # (with the tower's)
    246156121: ('stone', 2, '연합신학대학원'), 246156123: ('modern', 6, '종합관'),
    246156117: ('lm:seongam', 2, '성암관'), 246156111: ('lm:gyoyuk', 4, '교육관'),   # (blender/landmarks.py seongam, gyoyuk;
    # 교육관: three storeys and the dormered attic)
    245623193: ('stone_pale', 4, '가정관'), 413217834: ('house', 1, '논지당'),     # (빌링슬리관 since 1999)
    242897922: ('lm:daewoo', 6, '대우관'), 242897923: ('lm:daewoo_annex', 5, '대우관 별관'),
    429077789: ('white', 4, '음악대학'), 429077790: ('white', 4, '음악대학'),
    429079066: ('stone', 1, '언더우드가 사택'), 472512289: ('brick', 2, '알렌관'),
    472512292: ('white', 2, '어린이생활지도연구원'), 472965030: ('house', 2, '대학사택'),
    472987415: ('house', 2, '대학사택'), 472987419: ('house', 2, '대학사택'),
    472534641: ('house', 2, '영빈관'), 472534642: ('house', 2, '총장공관'),
    472516998: ('tile', 5, '국제학사'), 371403603: ('brick', 6, '한국어학당'),
    429077785: ('white', 1, '영선실'), 472516999: ('white', 1, '차량실'),
    722550503: ('white', 2, '행정동'),
    # medical quarter (old Severance)
    472648570: ('modern', 10, '세브란스병원'), 429249489: ('modern', 6, '의료원 종합관'),
    429249493: ('white', 5, '치과대학'), 429249490: ('modern', 7, '치과대학병원'),
    429249494: ('white', 6, '간호대학'),
    473006250: ('white', 5, '광혜관'), 473006251: ('white', 5, '제중관'),
    324328456: ('white', 3, '의학도서관'), 473014379: ('modern', 6, '임상의학연구센터'),
    1178739301: ('white', 1, '의과대학'), 1178739302: ('white', 1, '의과대학'),
    473014385: ('white', 5, '동문회관'), 429079067: ('white', 5, '재활병원'),
    324328481: ('modern', 10, '심장혈관병원'), 324328472: ('white', 5, '안·이비인후과병원'),
    # in 1997 too, missing before
    246156110: ('stone', 2, '한경관'), 429249497: ('house', 1, '수경원 정자각'), 1178743320: ('white', 3, '미우학사'),
}
# Outlines that have grown since 1997.  제1공학관: the College of Engineering added south and north wings in 2014-15
# (연세대 공과대학 연혁: 2014.6 착공, 2015.7 봉헌; yonsei.ac.kr/sc/243: 1,452평, 지상 6층) and the sixth floor in 2007.
# FOOTPRINT_1997 is the hall as first read off the 1997 aerial photo through an older camera (9 m to 74.5 m along the
# OSM hall).  The random planting, cars and decals ran with it, so it stays for them; the 1997 hall goes in after them
# (LATE_FOOTPRINT_1997 below, issue #83, reference/고증.md 3.8).
FOOTPRINT_1997 = {205583531: [(-127.6, -296.97), (-110.42, -233.76), (-124.96, -229.8), (-142.14, -293.01)]}
# Floors as of 1997 from the building history (yonsei.ac.kr/sc/349) and the colleges' and hospital's own: 제2공학관
# 지하 2층 · 지상 7층 since 1994; 한국어학당 (언어연구교육원, 1991) 지상 6층; 외솔관2 (1991) 「지하 1층, 지상 1층」 on
# the roof of the corridor between 인문관 and 종합관: three storeys with the corridor from the low east end, two over
# the car park on its west side (2010 roadview);
# 언더우드가 사택 rebuilt as one storey in 1955 (attic dormers); 재활병원 지하 1층 · 지상 6층 in 1987 (four more
# floors in 2011; five by its roof in the 1997 aerial photos, below); 동문회관 (1993) at least five (its 5층 소연회장).
# reference/고증.md 3.1.1 has the table, hall by hall.
# Two more are put right only after the random planting, cars and decals (their draws depend on every outline, as
# for 용재관: YONGJAE_SCATTER), so that the rest of the campus keeps its layout:
# - GONE_1997: 제2인문관 (위당관) broke ground on 29 May 1997 (착공 1997.5.29, 준공 1998.8.24), later than 새천년관
#   (1997.5.10), which is left out too.  Its site is bare earth with the 공사중 marker.
# - LATE_FOOTPRINT_1997: 미우학사 (1972, 지하 1층 · 지상 3층) was pulled down for the ten-storey 미우관 of 2021,
#   whose outline OSM has now; its own, from OSM as of 2018 (way 472534638 「미우관」, building:levels 3).
GONE_1997 = {246156119: '제2인문관 (공사중)'}
LATE_FOOTPRINT_1997 = {1178743320: [(482.62, 70.11), (489.63, 62.96), (493.39, 66.6), (499.74, 60.11), (496.1, 56.6),
                                    (505.76, 46.76), (516.66, 57.31), (503.76, 70.47), (510.43, 76.92), (512.31, 74.99),
                                    (514.69, 77.29), (516.59, 76.58), (523.4, 82.93), (520.97, 85.51), (522.73, 87.14),
                                    (508.59, 102.12), (503.97, 97.8), (504.74, 96.98), (492.07, 85.22), (494.02, 83.15),
                                    (481.39, 71.42)]}
# 본교 (1997 확인; reference/고증.md 3.1.1):
# - 루스채플: its own hall (1974, 「면적 329.9평」 in the building history) is the rectangle under the big hipped roof,
#   the south 45.4 x 24.5 m of OSM's outline (1,111 m2 = 336평); the low wing north of it with its glass drum is 원일한
#   홀 (2006.4 - 2006.11, 「지하 1층, 지상 3층」).  The 1990 map (no. 20) has no drum.
# - 경영학교실단: OSM's outline is the 1997 one (the 1990 map draws the low front between the wings along 백양로; 2005
#   only put floors on it, 155.6평), but only the two wings stand five storeys: with the whole of it at five the floor
#   area would be 1.8 times the 3,073평 it had before 2005.  The north wing keeps the OSM way; the south wing and the
#   one-storey front and hall between them go in with OLD_HALLS (990021, 990022).
# - 제1공학관 (FOOTPRINT_1997 above): the OSM hall north of the line of the west wing's south face, up to OSM's north
#   face.  That line meets the east face at the south-east corner the roadview of before the wings puts at
#   (-124.0, -280) (tools/roadview/eng), 26 m north of OSM's slanted tip; photo A's camera ends the 14-bay front at
#   OSM's north face (86 - 88 m along; the 2011 roadview and the 1994 photo see it 2 - 7 m short, reference/고증.md
#   5장).  The 1997-07-28 vertical aerial photos (reference/고증/3.8) end the roof 64.2 m north of that corner, three
#   frames within 0.5 m (the south end on the roadview's corner to 0.4 m): 2.6 m past OSM's north face, as every
#   north edge of the halls west of it stands 2.6 - 3 m north of OSM's there.  The hall goes on to there.
_ENG_N = 2.6
_ent = np.array([16.14, 59.49]) / 61.64                       # along the east face, south to north
ENG_FP_RNG = [(-124.14, -280.18), (-108.0, -220.69), (-121.44, -216.91), (-137.84, -276.66)]
LATE_FOOTPRINT_1997.update({
    429249499: [(62.85, -84.25), (106.77, -95.8), (113.08, -72.16), (69.16, -60.6)],
    256933753: [(-59.05, 125.82), (-13.1, 113.6), (-18.23, 94.69), (-64.14, 106.9)],
    205583531: [ENG_FP_RNG[0]] + [tuple(round(float(c_), 2) for c_ in np.array(q_) + _ent * _ENG_N) for q_ in ENG_FP_RNG[1:3]]
               + [ENG_FP_RNG[3]],
})
# 의료원 (1990 · 1995 지도, 1990년 무렵 항공 사진; reference/고증.md 3.1.2).  The new 세브란스병원 (2005.5) and
# 의료원 종합관 (2008) go; a name of None leaves the site a car park (asphalt), with no 공사중 marker: the old halls
# on it are in OLD_HALLS below.  심장혈관병원 (1991, 지상 10층): the five-storey wing of 2011 along its north-west
# side is the strip of the OSM outline north-west of the line through its east re-entrant corner, a car park in the
# 2008 roadview.
GONE_1997.update({472648570: None, 429249489: None})
# (and OSM's two outlines of the 2006 신촌역 building over the rails, tools/gate_town.py MODERN: its site is town)
GONE_1997.update({k_: None for k_ in gate_town.MODERN})
LATE_FOOTPRINT_1997.update({
    324328481: [(131.9, -123.48), (133.01, -124.74), (150.94, -107.92), (161.79, -119.1), (144.13, -135.18),
                (151.61, -142.42), (121.68, -168.17), (119.94, -166.35), (118.02, -168.03), (109.95, -158.47),
                (111.97, -156.58), (105.47, -149.2), (138.32, -116.73)],
})
# 의료원 in the vertical aerial photos of 28 July 1997 (자료 Q; reference/고증/3.1.2 「1997년 7월 수직 항공사진」): each
# roof read on its own height's plane in the frames from either side (27/17 east, 26/16 west), the roof heights where
# the two agree, against Kakao's base-map outlines and the 2008 skyview for the halls still standing.
# - 재활병원: OSM's outline lies 7.6 m off (4.0 m west, 6.5 m south of the roof in both frames, of Kakao's outline
#   and of the 2008 roof); its roof 65.3 m, 15 - 20 m over the ground round it: four storeys over the high side,
#   five from the low one (six would stand 22.8 m)
# - floors by the roofs (table B above): 의학도서관 51.7 m, 10.4 m over the yard north of it (three storeys);
#   임상의학연구센터 57.7 m over 33 m (six); 간호대학 77.5 m over 53 - 55 m (six, a penthouse block at 82 m); OSM's
#   two 「의과대학」 outlines between 본관 and 신관 are low roofs (41 m and 38 m, the east one the lecture hall under
#   the yard's level): one storey each.  The two ten-storey towers stand lower than ten of their style's storeys:
#   심장혈관병원's roof 79.0 m (34.3 m over the car park), 특별병동's 77 m (32 m): FLOOR_H_AT below
REHAB_MOVE = (4.0, 6.5)
LATE_FOOTPRINT_1997[429079067] = [(round(x_ + REHAB_MOVE[0], 2), round(y_ + REHAB_MOVE[1], 2)) for x_, y_ in (
    (191.3, -134.18), (207.04, -120.68), (212.11, -126.51), (242.71, -99.45), (232.68, -88.01), (214.36, -105.13),
    (212.58, -103.84), (218.75, -98.01), (215.52, -94.29), (209.45, -99.72), (206.82, -96.21), (208.58, -94.42),
    (204.02, -89.53), (189.68, -102.98), (196.31, -109.77), (181.08, -122.31))]
# 학생회관 별관 (ANNEX_1997; reference/고증/4.5): in the 1997 photo (reference/1997_학생회관.jpg) a flat-roofed box of
# two storeys in pale grey concrete, broad window bands, a plain parapet.  The pointed-arch arcade on its roof (「Global
# Lounge」, opened in November 2002) is in the 2008 · 2010 · 2011 roadview and the April 2009 photo, not in 1997.  OSM
# (and the skyview of 2008, 2010 and now) is the roof of the arcade: its slab runs 2 - 3 m on past the north end of the
# storeys below (the 2008 and 2010 frames from 191 and 192), so the 1997 hall's north wall stands 2.3 m south of
# OSM's.  Its south-west corner (the pylon of the lounge's banner) is OSM's within 1.5 m (six 2010 panos, held on
# 학생회관's north-west corner a few degrees off it); its west face OSM's (the roofline straight past the slab's end).
ANNEX_1997 = dict(id=1444448646, osm_nw=(31.91, -1.15), osm_ne=(63.48, -9.21), north_in=2.3, floor=3.8)
_anw, _ane = np.array(ANNEX_1997['osm_nw']), np.array(ANNEX_1997['osm_ne'])
_aw = np.array([25.68, -27.72]) - _anw
_ae = np.array([55.93, -35.41]) - _ane
LATE_FOOTPRINT_1997[ANNEX_1997['id']] = [(25.68, -27.72), (55.93, -35.41)] + [
    tuple(round(float(v_), 2) for v_ in p_ + d_ / np.linalg.norm(d_) * ANNEX_1997['north_in'])
    for p_, d_ in ((_ane, _ae), (_anw, _aw))]                        # (NE and NW moved down the east and west walls)
# 연합신학대학원 (1964.12 - 2003.1; reference/고증/3.1 「3.1.1」): OSM's outline is the 신학관 of 2005, an L of 17 x 53 m
# and a south wing.  The 1997-07-28 vertical aerial photos have one pale gabled roof where its west wing stands, on
# the same axis (within 0.3 deg): 11.9 x 30.8 m, the six frames of both flight lines within 0.15 m of each other at
# the eaves' height (68.2 m, 6.7 m over the yard south of it; blender/generic.py ROOF_AT).  In UTS_UV: u east, v north
# from the OSM outline's south-west corner along its west face.  The random planting ran with OSM's outline, which
# contains it: the hall goes in after it (the trees keep their list).
UTS = 246156121
UTS_UV = dict(o=(-129.51, 183.5), n=(13.14, 51.78), u=(3.0, 14.9), v=(7.0, 37.8))
_uo, _un = np.array(UTS_UV['o']), np.array(UTS_UV['n']) / np.linalg.norm(UTS_UV['n'])
_ut = np.array([_un[1], -_un[0]])
LATE_FOOTPRINT_1997[UTS] = [tuple(round(float(c_), 2) for c_ in _uo + _ut * u_ + _un * v_)
                            for u_, v_ in ((UTS_UV['u'][0], UTS_UV['v'][0]), (UTS_UV['u'][1], UTS_UV['v'][0]),
                                           (UTS_UV['u'][1], UTS_UV['v'][1]), (UTS_UV['u'][0], UTS_UV['v'][1]))]
FLOOR_H = {'modern': 3.8, 'white': 3.6, 'stone': 4.2, 'house': 3.4, 'gym': 6.5, 'city': 3.0, 'brick': 3.6, 'tile': 3.4, 'stone_pale': 4.0}
FLOOR_H_AT = {222843398: 3.9}        # 과학관's 3.9 m storeys (blender/generic.py FH_AT, reference/고증/3.10)
FLOOR_H_AT[ANNEX_1997['id']] = ANNEX_1997['floor']   # (학생회관 별관: its top 8.5 m over the yard in the 2008 frames)
FLOOR_H_AT.update({324328481: 3.55, 990036: 3.3})    # (심장혈관병원, 특별병동: their roofs in the 1997 aerial photos, above)
FLOOR_H_AT[UTS] = 3.4                                # (연합신학대학원: its eaves 6.7 m over the ground in the aerial photos)
# 과학관 as the 1997-07-28 vertical aerial photos have it (reference/고증/3.10; frames 26/15 and 26/16, from the north
# and the south, each roof read on its own plane where the two agree; the 2008 · 2010 skyview shows the same plan).
# OSM's outline is one mass round the yard north-west of the hall and 3 m short on the east wing's north side.  The
# hall: an east wing 18.1 m deep (OSM 14.9), a link south from its west end, a south-west wing; the link, the east
# wing and a long penthouse along the south-west wing's north side stand a storey over that wing's roof (roofs 76.5
# and 72.4 m on the photos' datum, the courtyard 50.8 m).  In the corner north-west of the link a low fan-shaped
# hall (a quarter circle of 23.2 m, its roof 57.5 m) and a low block against the south-west wing; the rest of OSM's
# outline is a yard with parked cars (52.5 m).  The frame: o the east wing's south-east corner as OSM has it, u east-
# south-east along the wing, v north-north-east.  The planting ran with OSM's outline: the hall goes in after it
# (LATE_FOOTPRINT_1997), its floor pinned (SCI['base'], the lowest corner of OSM's outline on the ground as it was).
_sa = math.radians(-15.06)
SCI = dict(o=np.array([-218.78, 7.32]), t=np.array([math.cos(_sa), math.sin(_sa)]), n=np.array([-math.sin(_sa), math.cos(_sa)]),
           base=49.22, court=50.8, yard=52.6,
           hall=[(0.6, 0.3), (0.6, 18.4), (-72.4, 18.4), (-72.4, 0.3), (-67.7, 0.3), (-67.7, -25.6), (-102.0, -25.6),
                 (-118.7, -25.6), (-118.7, -43.6), (-45.5, -43.6), (-45.5, -25.6), (-53.6, -25.6), (-53.6, 0.3)],
           # the part a storey higher: the east wing, the link, the penthouse along the south-west wing's north side
           wing=[(0.6, 0.3), (0.6, 18.4), (-72.4, 18.4), (-72.4, 0.3), (-67.7, 0.3), (-67.7, -25.6), (-102.0, -25.6),
                 (-102.0, -34.0), (-53.6, -34.0), (-53.6, -25.6), (-53.6, 0.3)],
           # the roof: the observatory's dome (5.6 m, its rim 6 m over the roof), the penthouse block where the link
           # meets the east wing (5.7 m over the roof) with a small dome on it, a round tank at the west end
           dome=(-8.8, 9.9), pent=(-64.3, -55.2, 0.5, 11.0), dome2=(-56.3, 6.2), tank=(-116.3, -36.7),
           clutter=(-82.0, -39.0),                               # (the lower roof's middle, south of the penthouse)
           fan=dict(c=(-72.6, -18.5), r=23.2, south=-21.0), annex=(-112.0, -99.0, -25.6, -18.5))


def sci_xy(u, v):
    return tuple(round(float(c_), 2) for c_ in SCI['o'] + SCI['t'] * u + SCI['n'] * v)


def sci_poly(pts):
    return Polygon([sci_xy(u_, v_) for u_, v_ in pts])


LATE_FOOTPRINT_1997[222843398] = [sci_xy(u_, v_) for u_, v_ in SCI['hall']]
# 연구관's frame (the 1997 aerial photos; OLD_HALLS below): o on the bar's middle line, a along it north-north-east, v
# across it (west-north-west); its ground 49.5 m west of it, 45.5 m east (JK_YARD, JK_TERRACE)
JK_O, _ja = np.array([-179.75, 15.0]), math.radians(63.4)
JK_A, JK_V = np.array([math.cos(_ja), math.sin(_ja)]), np.array([-math.sin(_ja), math.cos(_ja)])
JK_YARD, JK_TERRACE = 49.5, 45.5
LATE_NO_SIMPLIFY = {222843398}      # (its outline keeps the point where the penthouse's west end meets the north face)
BASE_1997 = {222843398: SCI['base']}
# 어린이생활지도연구원: OSM's hall (a curved wing with a drum) is the one built in 2001 - 2002 「어린이 교육장으로 쓰이던 두
# 건물을 헐고」 (연세춘추 제1423호); the 1997-07-28 aerial photos (frames 27/16 and 27/17) have two smaller halls on its
# site, a gabled one 18 x 13 m and a flat-roofed one 9 m square east of it, and the square hall north-west of them
# that the 2008 · 2010 skyview still shows (OSM's 「연구동」, twice too long there).  The new hall goes after the
# planting (its site lawn: GONE_LAWN), the three of 1997 go in with OLD_HALLS.
GONE_1997[472512292] = None
GONE_LAWN = {472512292}
GONE_NEW = {472512292}              # (left out since the planting was laid: the trees by them go at the list's end)

# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------
tn = json.load(open(os.path.join(ROOT, 'data/terrain.json')))
tf = json.load(open(os.path.join(ROOT, 'data/terrain_far.json')))
H10 = np.array(tn['rows_south_to_north'], dtype=np.float64)       # 10 m grid, +-1400
H10 = ndimage.gaussian_filter(H10, 1.6)                             # (tools/fetch_terrain.py opened the roofs out)
NEAR_HALF, NEAR_STEP = 800, 5.0
n_near = int(2 * NEAR_HALF / NEAR_STEP) + 1
gx = np.linspace(-NEAR_HALF, NEAR_HALF, n_near)
ii = (gx + tn['half']) / tn['step']
JJ, II = np.meshgrid(ii, ii, indexing='ij')                          # rows = y, cols = x
Hn = ndimage.map_coordinates(H10, [JJ, II], order=3)
Hn = ndimage.gaussian_filter(Hn, 1.5)
Hn_orig = Hn.copy()


def raw_grid(xs, ys):
    """the ground on another 5 m grid made as Hn is (tools/sinchon_rotary.py: the patch south of it)"""
    JJ_, II_ = np.meshgrid((np.asarray(ys, float) + tn['half']) / tn['step'], (np.asarray(xs, float) + tn['half']) / tn['step'],
                           indexing='ij')
    return ndimage.gaussian_filter(ndimage.map_coordinates(H10, [JJ_, II_], order=3), 1.5)


def sample(H, half, step, x, y):
    fx = (x + half) / step
    fy = (y + half) / step
    return float(ndimage.map_coordinates(H, [[fy], [fx]], order=1, mode='nearest')[0])


def grid_pts():
    X, Y = np.meshgrid(gx, gx)
    return X, Y

# --- 1997 백양로: OSM pedestrian way (old road alignment) + extension to the 삼거리
bys = None
for w in ways.values():
    if w.get('tags', {}).get('name') == '백양로' and w['tags'].get('highway') == 'pedestrian':
        bys = [xy(p) for p in w['geometry']]
bys = list(reversed(bys))                       # gate (south) -> north
bys = [(-108.0, -428.0)] + bys[1:] + [(33.0, 145.0), (38.0, 168.0)]
# The road was rebuilt in 2015 (백양로 재창조) and OSM follows the new walk.  The 1997 vertical aerial photos of 28 July
# 1997 (자료 Q, reference/고증/2.1-2.2 「2.2.2」: four frames from two flight lines, within 0.3 - 0.6 m of each other)
# have the carriageway's middle between the two hedges 1.1 - 1.7 m east of OSM's walk up to s 300 m and 0.5 - 1.0 m
# from there to the 삼거리; the roadview of 2008 - 2011 agrees once 백주년기념관 stands where those photos have it.
# Shift the line, easing back onto OSM at the 삼거리.  (Before #162 it ran 4 m west of OSM, from the first camera of
# photo A, an oblique view held on the corners at the photo's edges.)
_bl0 = LineString(bys)


def _west(s):
    """the shift of the line off OSM's walk, m to the west (negative: east)"""
    return -float(np.interp(s, [0.0, 300.0, 360.0, 480.0, 540.0], [1.4, 1.4, 0.8, 0.8, 0.0]))


def _west_rng(s):
    """the line as first laid (4 m west of OSM, back onto it by s 520): BLINE_RNG below"""
    return 4.0 if s <= 300 else 4.0 * max(0.0, (520 - s) / 220)


def _shift_line(pts, west):
    out_ = []
    for _x, _y in pts:
        _s = _bl0.project(Point(_x, _y))
        _p0, _p1 = _bl0.interpolate(max(0, _s - 2)), _bl0.interpolate(min(_bl0.length, _s + 2))
        _tx, _ty = _p1.x - _p0.x, _p1.y - _p0.y
        _n = math.hypot(_tx, _ty)
        out_.append((round(_x - _ty / _n * west(_s), 2), round(_y + _tx / _n * west(_s), 2)))
    return out_


# The random planting (one stream of draws, rng) still reads the line as first laid: what it asks of 백양로 (is this
# spot in a gap, on the road, how long is the row) it asks of BLINE_RNG, and what it plants along the road it puts
# along the moved line, so that moving the road keeps the campus's draws (#162); the trees the moved road then runs
# over are cleared at the end (drop_trees)
BYS_RNG = _shift_line(bys, _west_rng)
BLINE_RNG = LineString(BYS_RNG)
L_RNG = BLINE_RNG.length
bys = _shift_line(bys, _west)
# (east of the first line, the moved one runs on the inside of the bend 40 m in from the gate and is shorter by ~1 m
# past it: its south end is drawn out by as much, so that an s past the bend names the same spot on both lines and
# the places measured along the road by s before #162 (crossings, openings, mouths, banners) stay where they were)
_bl1 = LineString(bys)
_ds = float(np.median([s_ - _bl1.project(BLINE_RNG.interpolate(s_)) for s_ in np.arange(80.0, 600.0, 5.0)]))
_b0, _b1 = np.array(bys[0]), np.array(bys[1])
bys[0] = tuple(np.round(_b0 + (_b0 - _b1) / np.linalg.norm(_b0 - _b1) * _ds, 2))
GATE = bys[0]
bline = LineString(bys)
# Road cross-section, half widths from the centre line.  As in the 1997 aerial photo (reference/1997_백양로_항공사진.jpg):
# a two-lane carriageway (white dashed centre line, yellow edge lines) with no median, a raised verge of
# clipped round boxwood on each side, a paver sidewalk, and an outer planting strip carrying the ginkgo row and a low
# clipped hedge.  Widths measured in the photo at 100 m and 185 m from the gate: 6.6 m between the yellow edge lines
# (OSM's modern road is wider), the verges' outer edge 5 m out, the sidewalk to ~9.5 m.  The lane runs to the kerb's
# face; its last 0.3 m is a concrete gutter (`gutter`, blender/road.py: the 2008 / 2010 roadview, reference/고증.md 2.3)
# with the yellow edge line on the asphalt just inside it.  The kerb faces 7.3 m apart (the yellow lines 6.46 m: the
# photo's 6.3 - 6.4 m plus the roadview's gutter, gap and half line, the photo's east kerb 0.44 m out from its line);
# the verge narrower by as much (1.7 m from the kerb's face, photo A 1.3 - 1.6 m), so that the sidewalk, the strip
# and what is planted on them stay where the photo has them (before: the kerb faces 6.6 m apart, the verge 2.05 m)
ROAD = dict(median=0.0, lane=3.65, curb=0.25, verge=1.45, walk=4.6, strip=2.2, gutter=0.3)
E_CURB = ROAD['median'] + ROAD['lane'] + ROAD['curb']       # carriageway edge (curb top)
# (the ground's paint under the road mesh, the side roads' ends and the openings are drawn from the carriageway's first
# width: the random planting and the decals read them, so the rest of the campus keeps its draws; the mesh covers it)
E_CURB0 = 3.55
E_VERGE = E_CURB + ROAD['verge']                             # inner edge of the sidewalk
E_WALK = E_VERGE + ROAD['walk']                              # outer edge of the sidewalk
ROAD_HALF = E_WALK + ROAD['strip']


def s_at(x, y):
    return float(bline.project(Point(x, y)))


def along_rng(s, off):
    """along_raw on the line as first laid (BLINE_RNG)"""
    return along_raw(s, off, BLINE_RNG)


def s_off_rng(x, y):
    """s_off on the line as first laid (BLINE_RNG)"""
    s_ = float(BLINE_RNG.project(Point(x, y)))
    cx_, cy_, a_ = along_rng(s_, 0.0)
    return s_, (x - cx_) * -math.sin(a_) + (y - cy_) * math.cos(a_)


def s_off(x, y):
    """arc length along 백양로 and signed offset (+ west) of a point"""
    s_ = s_at(x, y)
    cx_, cy_, a_ = along_raw(s_, 0.0)
    return s_, (x - cx_) * -math.sin(a_) + (y - cy_) * math.cos(a_)


def along_raw(s, off, line=None):
    """point `off` m to the west (left) of the 백양로 centre line at arc length s, and the road heading there"""
    line = line or bline
    p = line.interpolate(s)
    p2 = line.interpolate(min(line.length, s + 1))
    p0 = line.interpolate(max(0, s - 1))
    tx, ty = p2.x - p0.x, p2.y - p0.y
    n_ = math.hypot(tx, ty)
    return p.x - ty / n_ * off, p.y + tx / n_ * off, math.atan2(ty, tx)

# ---------------------------------------------------------------------------
# 정문의 자리 (reference/고증/4.8_정문_밖.md 「정문의 남북 자리」).  The gate stood on the line through its pillars, at
# y -396 (± 1.5) on 백양로's centre line, not at the road's south end: Kakao's 2010 skyview has the east pillar's foot at
# (-102.4, -397.0), the pre-rebuild roadview (2011-04 drive 1017220149 - 152, headings and places unknown, tied by
# 공학원's tower tops to the panos up the road that see 제1공학관's old south-east corner) its middle at (-102.6, -398.8)
# ± 3.8 m (tied to Kakao's places: -397.3 ± 1.5); photo A, taken from over the gate, has its camera at y -395.7; the
# 1994 photo with the rails on the bridge as its nearest marks -401 ~ -411 (± 8).  The line `bys`
# and its arc length s keep their place (everything set along 백양로 by s stays where it is): s 0 .. GATE_S is now
# the gate's mouth outside it, 백양로 proper starts at the gate.  (Before: the gate at s 4, y -423.7, on the middle
# of OSM's north carriageway of 성산로, which had to be pushed 14.5 m south and narrowed to fit.)
# ---------------------------------------------------------------------------
GATE_Y = -396.0
GATE_S = float(next(s_ for s_ in np.arange(0.0, 80.0, 0.05) if bline.interpolate(s_).y >= GATE_Y))
GATE_C = along_raw(GATE_S, 0.0)[:2]           # the gate's middle, on 백양로's centre line (the opening's: 3 m east)

# Height profile along 백양로 (issue #8).  Sampled along the road, the 5 m grid smears the hall blocks and the wooded
# hill behind 언더우드관 down onto it.  The designers of the 2015 rebuilding (Annual Technical Report(지하융복합)_2023,
# 2.1: 「정문에서 본관 앞 삼거리까지 약 12m의 레벨 차가 있는 완만한 경사」, about 8 m of it over the 360 m of the
# building; 2.2: 백양로 is 550 m from the gate) drew the road before the works in their long section (그림 2.5 (a),
# reference/고증.md): its ground line, read off column by column, rises about 1.1 m in the first 50 m, runs nearly
# level to ~150 m and then climbs evenly (about 2.5 %) to the 삼거리.  So: the road gets that section, 12 m from the
# gate's height (the terrain's, ~26 m: Copernicus GLO-30 has 24.9 m on the open crossing) over B's 550 m, then on at
# its last slope to the foot of the 삼거리 steps and the end of the line.  The 1997 and 2011 1:25000 maps have the
# 30 m contour across the road at 292 m (the section: 31 m) and the 40 m one at 591 m, over the steps (38.9 m at
# their foot), reference/고증.md 2.8.  The ground around moves with it (by the difference between the section and the
# ground's trend across a 120 m band), fading out 50-230 m from the road; past the 삼거리 that lowers 언더우드관's
# quarter (the opened surface model keeps the garden's big trees in it), which carries its aprons, garden, statue and
# steps along.
L = bline.length
ss = np.arange(0, L + 0.1, 2.0)
# (the ground is read along the line as first laid, BLINE_RNG: 5 m east the 30 m grid has the gate 0.1 m lower, and
# every level set from 백양로's would follow it; the section is the road's, and s names the same spot on both lines)
_dem = np.array([sample(Hn, NEAR_HALF, NEAR_STEP, *BLINE_RNG.interpolate(s).coords[0]) for s in ss])
H_GATE = float(ndimage.gaussian_filter1d(_dem, 12)[0])
# 그림 2.5 (a): (fraction of the way to the 삼거리, rise in m) at the ground line's turning points
SECTION = [(0.0, 0.0), (0.019, 0.0), (0.083, 1.14), (0.252, 1.71), (0.359, 3.43), (0.487, 5.14), (0.592, 6.86),
           (0.656, 7.43), (0.805, 9.71), (0.910, 10.86), (1.0, 12.0)]
SECTION_LEN = 550.0
_sec_k = (SECTION[-1][1] - SECTION[-2][1]) / ((SECTION[-1][0] - SECTION[-2][0]) * SECTION_LEN)   # (2.3 %)


def section_rise(s):
    s = np.asarray(s, float)
    return np.where(s <= SECTION_LEN, np.interp(s / SECTION_LEN, [f for f, _ in SECTION], [d for _, d in SECTION]),
                    SECTION[-1][1] + _sec_k * (s - SECTION_LEN))


prof = H_GATE + section_rise(ss)
prof = ndimage.gaussian_filter1d(prof, 6, mode='nearest')
prof += (H_GATE + float(section_rise(L)) - prof[-1]) * (ss / L) ** 2      # (keep the ends where they belong after smoothing)
_band = np.array([np.mean([sample(Hn, NEAR_HALF, NEAR_STEP, *along_rng(s, o)[:2]) for o in np.arange(-60, 61, 10)])
                  for s in ss])
_shift = ndimage.gaussian_filter1d(prof - ndimage.gaussian_filter1d(_band, 15, mode='nearest'), 10, mode='nearest')
_shift *= np.clip(ss / 80.0, 0, 1) ** 2 * (3 - 2 * np.clip(ss / 80.0, 0, 1))     # (the town outside the gate stays)
# The section's north end by the vertical aerial photos of 1997-07-28 (자료 Q; reference/고증/2.8 「1997년 7월
# 항공사진으로 잰 높이」).  The carriageway's height from the overlapping frames (tools/aerial97.py z, every frame pair
# within 0.1 - 0.4 m of the others) is B's section to s 440 (0.2 - 0.5 m over it, inside the photos' datum) and
# leaves it from there: 1.1 m over it by 대강당's crossing, 2.6 m at the foot of the end steps (41.1 m; the 1:25000
# map's 40 m contour crosses at s 591).  B's drawing gives the designers' round 「약 12 m」 to the 삼거리; the photos
# have 14.7 m from the gate.  (s, photo - B's section); past the foot of the steps the line is not drawn.  The
# ground's trend round the road (_shift above) stays as B's section moved it: north of the 삼거리 the photos' own
# heights go in (HILL_Q below), and what stands along the road takes its level from the road as before.
PROF_Q = [(430.0, 0.0), (450.0, 0.4), (470.0, 0.9), (490.0, 1.1), (510.0, 1.15), (520.0, 1.5), (530.0, 1.8), (540.0, 2.0),
          (560.0, 2.3), (580.5, 2.6)]
prof = prof + np.interp(ss, [s_ for s_, _ in PROF_Q], [d_ for _, d_ in PROF_Q])


def prof_h(s):
    return float(np.interp(s, ss, prof))


# zebra crossings (arc length): 백주년기념관, 학생회관-중앙도서관, 대강당, 삼거리.  Near the gate the 1997 photo
# shows a yellow/white hatched speed bump (raised, striped) instead.  The carriageway itself stays clear of objects.
CROSS = [round(s_at(-55, -200), 1), round(s_at(-20, -62), 1), round(s_at(5, 40), 1), round(L - 30, 1)]
# --- 화단 띠가 끊기는 곳 (reference/고증/2.3_길의_단면과_길가.md, #131).  CROSS_RNG keeps the crossings where they were
# first put: the verge's and the strip's planting and the sidewalk's decals take their random draws by it, so that
# moving a crossing changes nothing away from it (strip_fill below plants the old opening from its own numbers)
CROSS_RNG = [round(float(BLINE_RNG.project(Point(*p_))), 1) for p_ in ((-55, -200), (-20, -62), (5, 40))] + [round(L_RNG - 30, 1)]
# 백주년기념관 앞: the verges' openings on both sides with their round ends, the bollard and the grates, from the
# 2008-08, 2010-12 and 2011-04 roadview at node 171 solved together (heading and tilt free; 활천대, the eagle and the
# hall's north-west corner): the east opening's tips at s 224.2 - 229.5, the west's 224.9 - 229.7 (2011 pano held at
# its position from tools/roadview/statues.py: +0.9 m; the corner at Kakao's base map: -0.9 m); photo A's white
# stripes about s 229.5.  It was at the Kakao node (235.4)
CROSS[0] = 227.4
# 학생회관 앞: the crossing in the 6 m opening between the forecourt's first two islands (VERGE_BREAKS below), east
# 375.5 - 381.5 (it was 377.7, at the Kakao node)
CROSS[1] = 378.5

X, Y = grid_pts()
pts = np.stack([X.ravel(), Y.ravel()], 1)
from shapely import points as shp_points, distance as shp_distance, line_locate_point
P = shp_points(pts)
dist = shp_distance(P, bline).reshape(X.shape)
spos = line_locate_point(bline, P).reshape(X.shape)
# (the ground's trend round the road is moved by the line as first laid, BLINE_RNG: by the moved one, 5 m east, the
# ground 50 - 230 m off would change by a few cm everywhere; the road's own band, hline below, follows the moved line)
_fade = np.clip((shp_distance(P, BLINE_RNG).reshape(X.shape) - 50.0) / 180.0, 0, 1)
Hn = Hn + np.interp(line_locate_point(BLINE_RNG, P).reshape(X.shape), ss, _shift) * (1 - _fade * _fade * (3 - 2 * _fade))
print('백양로 section: gate %.2f, 삼거리 %.2f m; ground shifted by %.1f .. %.1f m' % (prof[0], prof[-1], _shift.min(), _shift.max()))
hline = np.interp(spos, ss, prof)
w = np.clip((dist - (ROAD_HALF + 4)) / 30.0, 0, 1)
w = w * w * (3 - 2 * w)
Hn = hline * (1 - w) + Hn * w

# --- the hill north of 한경길 (연희관, 대우관, 생활과학관), 2 m down.  The elevation grid is a radar surface model at 30 m
# (Copernicus GLO-30 with the roofs opened out; AWS Terrarium before): over the wooded hill it stands over the ground.
# On Terrarium the 5 m grid had 연희관's door 19.5 m over 한경길 behind 언더우드관, with 13 m of it one 30 % slope across
# the garden between them; the photos have a level parterre a short flight over 한경길, then a bank with a broad flight
# up to the road before 연희관 and its entrance flight, some 7 - 9 m in all (reference/연희관_정면_2023.jpg,
# 학교연혁_연희관.jpg, 대우관_블로그_연희관과_대우관_원경.jpg; YEONHUI below sets them from 한경길).  In the 1997 aerial
# photo, through its fitted camera, 대우관's tower top and 연희관's stood 6 m under where the game had them, and the hill
# went 6 m down.  Copernicus has the hill 0.5 - 9 m lower than Terrarium had it (대우관's site the most), and through
# photo A's refitted camera (PHOTO_A below) the halls on it want: 생활과학관 3.5 m down, 대우관 별관 1.6 m, 대우관 4 m up
# (each +-4 m, and 3 - 4 m either way with the camera's pitch); 2 m also keeps 연희관's front corners 3 m under its door
# as before (reference/고증.md 3.5.1).  Full over the hill (G frame: e across, n up the garden's axis from its round
# planter), easing in from 한경길 to the road before 연희관 (the garden takes the step, YEONHUI below) and out into the
# woods west, east and north.
GF_C, GF_E, GF_N = np.array([78.4, 318.3]), np.array([0.968, -0.250]), np.array([0.250, 0.968])
GE = (X - GF_C[0]) * GF_E[0] + (Y - GF_C[1]) * GF_E[1]
GN = (X - GF_C[0]) * GF_N[0] + (Y - GF_C[1]) * GF_N[1]
NORTH_DROP = 2.0


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def north_drop(e, n):
    return NORTH_DROP * (_smooth((n + 22.0) / 48.0) * (1 - _smooth((n - 235.0) / 95.0))
                         * (1 - _smooth((-95.0 - e) / 50.0)) * (1 - _smooth((e - 105.0) / 45.0)))


Hn = Hn - north_drop(GE, GN)
print('north hill down %.1f m (%d grid nodes moved)' % (NORTH_DROP, int((north_drop(GE, GN) > 0.05).sum())))

# --- the hill from the 삼거리 up to 연희관 by the vertical aerial photos of 1997-07-28 (자료 Q; reference/고증/2.8
# 「삼거리에서 연희관까지」).  The ground's height read from the overlapping frames (tools/aerial97.py z: the median of
# the frame pairs that correlate over 0.75, five to fifteen pairs a point within 0.1 - 0.2 m of each other) at open
# ground: the square at the head of the end steps, the walks of 언더우드관's garden and before the three halls, the
# lawns and walks of 연희관's garden, the car park behind 연희관.  Where the photos and the game agree (백양로 s 110 -
# 440, 대우관's terrace) they do so to 0.5 m; between, B's section and its band had 언더우드관's quarter 3.4 - 5.7 m
# too low (the 1:25000 map: 언더우드관 about 46 m, as the photos), the hill's drop (NORTH_DROP, from photo A's
# camera, which the vertical photos have since shown cannot be trusted: 고증 2.2.2) 연희관's garden 3 - 4 m too low
# and its back 2 - 3 m too high (the map's 60 m contour runs behind 연희관, as the photos).
# HILL_Q: (x, y, photo height).  The ground between takes the difference from the nearest of them (a Barnes
# analysis: Gaussian-weighted means in three passes, 16 -> 6 m), inside HILL_ZONE and fading out over 30 m round it:
# the photos' heights further out are other halls' business (east of 성암관 and the road to 노천극장 1 - 4 m lower
# than the game, the drive west of 연희관 and the 상뜰's footway: 고증 2.8 「남은 한계」).
# HILL_KEEP: (x, y, difference) where the trees hide the ground.  The drive behind 스팀슨관 and 언더우드관 keeps its
# own grade between its two ends the photos do see (+2.6 m at the 삼거리, +2.4 m where it meets 한경길).
HILL_Q = [
    (25.9, 114.4, 40.3), (28, 128, 40.4), (30.4, 133.9, 41.05), (17, 134, 41.1), (20, 140, 41.1), (8, 114, 40.55),   # the 삼거리
    (6, 110, 40.4), (-10, 122, 40.9), (-14, 126, 41.3), (-10, 118, 41.4), (60, 132, 44.2),
    (34, 162, 45.1), (42, 160, 45.2), (50, 158, 45.4), (58, 156, 45.3), (30, 170, 45.3), (40, 168, 45.3),   # the square
    (52, 166, 45.1), (14, 168, 45.5), (12, 172, 46.0),
    (47, 193, 45.85), (48, 205, 45.85), (41, 200, 45.6), (54, 198, 45.85), (33, 185, 45.4), (43, 180, 45.7),   # the garden
    (57, 180, 45.65), (30, 198, 45.5), (64, 196, 45.7), (38, 214, 45.9), (58, 214, 46.05), (36, 228, 46.2),
    (50, 238, 46.3), (40, 240, 46.5), (48, 216, 45.95), (46, 186, 45.7), (66, 184, 45.55), (32, 216, 45.9), (31, 208, 45.6),
    (68, 195, 45.9), (72, 212, 46.1), (74, 224, 46.4), (70, 205, 45.9), (33, 236, 47.0), (35, 243, 47.0),   # by the side halls
    (45, 252, 47.55), (54, 249, 47.6), (62, 247, 47.9), (70, 245, 47.75), (78, 243, 47.6), (38, 250, 47.75),   # 언더우드관's front
    (84, 240, 48.2),
    (88, 300, 54.0), (100, 304, 54.45), (74.4, 303.5, 54.0), (62, 322, 54.5), (95, 314, 54.8), (82, 333, 55.1),   # 연희관's garden
    (54, 325, 54.5), (102, 312, 54.9), (60, 338, 54.9), (70, 338, 54.9), (77, 312, 54.5), (80, 325, 55.2),
    (51.5, 358, 58.15),
    (86, 395, 58.7), (90, 394, 59.5), (97, 392, 59.6), (105, 390, 58.85), (109, 389, 59.35), (117, 387, 58.9),   # behind 연희관
    (121, 386, 59.1), (90, 390, 59.8), (110, 385, 60.0),
]
HILL_KEEP = [(4.4, 143.6, 2.6), (1.6, 149.5, 2.6), (-2.0, 160.5, 2.6), (-7.9, 178.7, 2.55), (-12.9, 194.7, 2.55),
             (-14.5, 204.6, 2.5), (-8.0, 228.0, 2.5), (-2.3, 250.4, 2.5), (0.4, 254.3, 2.45), (10.0, 268.0, 2.45),
             (18.8, 281.7, 2.4), (27.1, 292.5, 2.4),
             # nothing moved where others' ground starts: the 상뜰's footway, the drive west of 연희관's back, 대우관
             # 별관's side, 한경길's east end
             (66.6, 414.3, 0.0), (78.0, 411.3, 0.0), (90.0, 408.3, 0.0), (101.2, 405.4, 0.0), (113.0, 402.5, 0.0),
             (125.0, 399.5, 0.0), (137.7, 396.5, 0.0), (55.0, 378.0, 0.0), (58.0, 388.0, 0.0), (62.0, 399.0, 0.0),
             (65.0, 408.0, 0.0), (142.0, 385.0, 0.0), (142.0, 370.0, 0.0), (138.0, 268.0, 0.0), (140.0, 280.0, 0.0),
             (138.0, 292.0, 0.0)]
HILL_ZONE = Polygon([(-24, 114), (40, 110), (66, 124), (78, 140), (96, 170), (104, 186), (106, 230), (100, 250), (108, 262),
                     (126, 262), (130, 300), (128, 330), (134, 346), (134, 398), (82, 402), (76, 384), (50, 362), (44, 350),
                     (36, 300), (22, 296), (4, 268), (-10, 252), (-24, 206), (-18, 160), (-24, 130)])


def _hill_field():
    """the photos' height less the ground's at HILL_Q (and HILL_KEEP), spread over the grid"""
    q_ = np.array([(x_, y_, z_ - sample(Hn, NEAR_HALF, NEAR_STEP, x_, y_)) for x_, y_, z_ in HILL_Q] + HILL_KEEP)
    d2_ = (X[..., None] - q_[:, 0]) ** 2 + (Y[..., None] - q_[:, 1]) ** 2
    f_ = np.zeros(X.shape)
    for sig_ in (16.0, 10.0, 6.0):
        r_ = q_[:, 2] - np.array([sample(f_, NEAR_HALF, NEAR_STEP, x_, y_) for x_, y_ in q_[:, :2]])
        w_ = np.exp(-d2_ / (2 * sig_ * sig_))
        f_ = f_ + (w_ * r_).sum(-1) / np.maximum(w_.sum(-1), 1e-9)
    r_ = q_[:, 2] - np.array([sample(f_, NEAR_HALF, NEAR_STEP, x_, y_) for x_, y_ in q_[:, :2]])
    out_ = shp_distance(P, HILL_ZONE).reshape(X.shape)
    return f_ * (1 - _smooth(out_ / 30.0)), q_, r_


_hf, _hq, _hr = _hill_field()
Hn = Hn + _hf
print('hill by the 1997 vertical photos: %d points, %.1f .. %+.1f m at them (left over: rms %.2f, max %.2f m), '
      '%d grid nodes moved, %.1f .. %+.1f m' % (len(_hq), _hq[:, 2].min(), _hq[:, 2].max(), float(np.sqrt((_hr ** 2).mean())),
                                              float(np.abs(_hr).max()), int((np.abs(_hf) > 0.05).sum()), _hf.min(), _hf.max()))

# --- 대운동장 / pitches: flatten to their mean height
for wv in ways.values():
    t = wv.get('tags', {})
    if t.get('leisure') in ('pitch', 'track', 'stadium') and len(wv['geometry']) > 3:
        poly = Polygon([xy(p) for p in wv['geometry']])
        if not poly.is_valid or poly.area < 400:
            continue
        inside = np.array([poly.contains(Point(x, y)) for x, y in pts]).reshape(X.shape)
        if inside.any():
            m = ndimage.binary_dilation(inside, iterations=2)
            soft = ndimage.gaussian_filter(m.astype(float), 1.2)
            Hn = Hn * (1 - soft) + float(Hn[inside].mean()) * soft

# --- 대강당 앞 농구장 (1997): an outdoor court on the paved terrace before 대강당 (remembered by a 1997 student; the
# 1994 aerial photo has the terrace paved and empty of cars; by 2008 it was a car park with two planted islands, Kakao
# skyview 2008 · 2010).  No photo of the court itself: a standard 28 x 15 m court, long side along the hall's front,
# south of the hall's axis so the way from the flight's head to the porch stays clear (reference/고증.md 4.5).
# COURT_OLD: where it first stood in the game, beside 학생회관 별관 on what was really the drive up to the terrace
# (AUD_RAMP below); the random planting still reads that spot (PAV_PRE, GARDEN_ZONES) so the campus keeps its draws.
COURT = dict(pos=[33.8, 28.7], rot=1.313, L=28.0, W=15.0)
COURT_OLD = dict(pos=[21.9, 2.5], rot=1.313, L=28.0, W=15.0)
# --- 활천대 (活泉臺): the fountain the electrical engineering alumni raised money for in 1974 (연세대학교 공식 블로그
# 「연세대학교의 조형물을 찾아서!! 제3탄」, 2017).  Before 백양로 was rebuilt it stood beside the eagle (연세춘추
# 「연세인도 모르는 연세대학교」, 2009.9: 「활천대는 독수리상 옆에 있는 분수대다」; since 2015 it is in front of
# 제1공학관, where its old spot became the stairs down to 백양누리).
# Where the eagle and 활천대 stood before 백양로 was rebuilt (reference/고증/2.1-2.2 「2.2.2」, 4.1.4, 4.3): the 1997
# vertical aerial photos of 28 July (자료 Q) have the eagle's brick ring (r 5.7 m) and the basin's wall (r 4.7 - 4.8 m)
# within 0.4 m in four frames from two flight lines; the eagle 22.8 m west of the carriageway's middle (1994 aerial
# photo 20.3 - 20.9 m, roadview 20.6 - 22 m, photo A 22.0 - 22.4 m), ~80 m south of where the 2015 rebuilding put it,
# in front of 중앙도서관's south end (a flower bed in 2011); 활천대's white cross column 45 m south-south-west of it.
# The roadview of 2008-08, 2010-12 and 2011-04 (tools/roadview/c12/net.py, every pano's heading unknown) puts them
# within 1 m of that with 백주년기념관's north-west corner where the aerial photos have it (BLD_MOVE).  (Before #162:
# (-70.9, -159.8) and (-83.1, -202.6), from that roadview with the corner at OSM's outline; first, from Kakao's
# headings and positions as given, 4.6 and 2.5 m further east.)  The 1995 campus map draws the same row along the
# west side of 백양로 south of the library: a round plaza, then a round basin.  Its 2009 photo
# (reference/활천대_2009_연세춘추.jpg) is then taken from the lawn 14 m south-south-east of the basin, looking
# north-north-west past it at 중앙도서관's south front, with 과학관's dome far left and the eagle on the right (the camera
# solved from the two columns and the south front's two corners: (-74.5, -218.8), 1.6 m up, heading 12.6 deg west of
# north, tilted 3.4 deg up, vertical field 36 deg; 3.6 px rms; it was (-78.6, -216.2) with the two where they stood
# before #162, tools/snapshots.json compare/hwalcheon).
# The basin before the rebuilding (reference/고증.md 4.3): the old photo in the 2017 blog post (reference/
# 활천대_공사전_연세대블로그.jpg, its camera solved from the rings and the column: 4 px rms) and a group snapshot of
# about late 1999 - the early 2000s (reference/활천대_단체사진_*.jpg) show one round pool walled in rounded field
# stones, the water up to just under their top, the column on a low round island of the same stones, a ring of rough
# flagstones round the wall and lawn beyond.  The wall is 4.14 times the column's height (slab top to the tips)
# across; the column is 2.29 / 2.34 m in the 2011 roadview from 169 / 172 (their solved spots, 27 / 30 m off), the
# wall's ends 9.4 - 9.6 m apart from 170: a wall 9.5 m across.  (The thin metal ring of jets in the water, 6.5 m,
# came later: there were no jets on the rim in 1997.)  Radii: r the water, rim the wall's outer face, pave the
# flagstones' outer edge, island the stone island under the sculpture; heights over the flagstones (level ground):
# wall the wall's top, water, floor the pool's floor, isle the island's top (blender/landmarks.py fountain,
# web/src/water/fountain.js).
EAGLE = dict(pos=[-67.95, -161.78])
FOUNTAIN = dict(pos=[-79.45, -205.03], r=4.45, rim=4.75, pave=5.85, island=0.95,
                wall=0.22, water=0.05, floor=-0.25, isle=0.13)
# the random planting keeps its lawn hole where the fountain first stood, with the first basin's size (r 2.6), so
# that the campus keeps its trees (one stream of draws, see below); the scattered trees round the moved basin are
# cleared after the draws (_FOUNTAIN_LAWN)
FOUNTAIN_SCATTER, FOUNTAIN_SCATTER_R = (-80.7, -203.2), 2.6 + 7
# where the eagle and the basin stood before the 1997 aerial photos moved them (#162): the random planting reads them
EAGLE_RNG, FOUNTAIN_RNG = (-70.9, -159.8), (-83.1, -202.6)
# the eagle on a paved round (its platform is 8.4 m square, 5.9 m to the corners) with a straight walk east to
# 백양로's sidewalk (the 2011 roadview from 백양로, between beds of azaleas)
EAGLE_R = 6.0
EAGLE_WALK = LineString([tuple(EAGLE['pos']), along_raw(s_at(*EAGLE['pos']), E_WALK - 0.3)[:2]])
EAGLE_PLAZA = Point(*EAGLE['pos']).buffer(EAGLE_R).union(EAGLE_WALK.buffer(1.5, cap_style=2))   # (the OSM cut below)
EAGLE_PLAZA_RNG = Point(*EAGLE_RNG).buffer(EAGLE_R).union(LineString([EAGLE_RNG, along_rng(
    float(BLINE_RNG.project(Point(*EAGLE_RNG))), E_WALK - 0.3)[:2]]).buffer(1.5, cap_style=2))
# Its precinct (Kakao roadview 2008-08, 2010-12 and 2011-04 from six points round it; the 1995 aerial photo): a low
# round dais of light stone (r 4.6 m, 0.4 m) on a ring of brick paving a step up from the walks (r 5.6 m, 0.2 m); four
# brick walks 3 m wide along the statue's axes through four quadrant beds of clipped azaleas (red-brown in winter,
# green in summer, about 0.8 m high) out to a low round kerb at 9.5 m.  The east walk meets 백양로's west sidewalk,
# which bounds the beds (blender/statues.py builds the dais, the ring and the beds' kerb; the beds are planted below).
EAGLE_ROT = math.radians(-14)                 # the statue faces 194 deg, down 백양로 (STATUES below)
EAGLE_DAIS, EAGLE_RING, EAGLE_BEDS_R, EAGLE_WALK_W = (4.6, 0.4), (5.6, 0.2), 9.5, 3.0
# the four 「연세인」 groups A - D (SW, NW, SE, NE): compass bearing (deg) and distance (m) of each group's centre from
# the column, solved from the 2011 / 2010 roadview (tools/roadview/groups.py, reference/고증.md 4.1.1).  They stand on
# the dais' edge, their low wedges running out onto the brick ring (blender/statues.py, web/src/main.js colliders)
EAGLE_GROUPS = ((246, 4.9), (330, 4.6), (150, 4.3), (56, 4.6))
EAGLE_EDGE = round(bline.distance(Point(*EAGLE['pos'])) - E_WALK, 2)     # the centre to the sidewalk's outer edge


def eagle_xy(u, v):
    """the statue's frame (u towards 백양로, v up its axis, the front at -v) -> campus xy"""
    c_, s_ = math.cos(EAGLE_ROT), math.sin(EAGLE_ROT)
    return (EAGLE['pos'][0] + u * c_ - v * s_, EAGLE['pos'][1] + u * s_ + v * c_)


EAGLE_WALKS = unary_union([LineString([eagle_xy(0, 0), eagle_xy(EAGLE_EDGE + 0.3, 0)]).buffer(EAGLE_WALK_W / 2, cap_style=2)] +
                          [LineString([eagle_xy(0, 0), eagle_xy(*uv_)]).buffer(EAGLE_WALK_W / 2, cap_style=2)
                           for uv_ in ((0, -EAGLE_BEDS_R - 1.0), (-EAGLE_BEDS_R - 1.0, 0), (0, EAGLE_BEDS_R + 1.0))])
EAGLE_PAVED = Point(*EAGLE['pos']).buffer(EAGLE_RING[0], 64).union(EAGLE_WALKS)
# (the same where the eagle first stood, by the line as first laid: what the clearing below asks, EAGLE_RNG)
_e_edge_rng = BLINE_RNG.distance(Point(*EAGLE_RNG)) - E_WALK
_exy_rng = lambda u, v: (EAGLE_RNG[0] + u * math.cos(EAGLE_ROT) - v * math.sin(EAGLE_ROT), EAGLE_RNG[1] + u * math.sin(EAGLE_ROT) + v * math.cos(EAGLE_ROT))
EAGLE_PAVED_RNG = Point(*EAGLE_RNG).buffer(EAGLE_RING[0], 64).union(unary_union(
    [LineString([_exy_rng(0, 0), _exy_rng(_e_edge_rng + 0.3, 0)]).buffer(EAGLE_WALK_W / 2, cap_style=2)] +
    [LineString([_exy_rng(0, 0), _exy_rng(*uv_)]).buffer(EAGLE_WALK_W / 2, cap_style=2)
     for uv_ in ((0, -EAGLE_BEDS_R - 1.0), (-EAGLE_BEDS_R - 1.0, 0), (0, EAGLE_BEDS_R + 1.0))]))
EAGLE_BEDS = Point(*EAGLE['pos']).buffer(EAGLE_BEDS_R, 64).difference(EAGLE_PAVED.buffer(0.15)) \
    .difference(bline.buffer(E_WALK + 0.2))


def court_poly(pad=0.0, C=None):
    C = C or COURT
    c_, s_ = math.cos(C['rot']), math.sin(C['rot'])
    hl, hw = C['L'] / 2 + pad, C['W'] / 2 + pad
    return Polygon([(C['pos'][0] + u * c_ - v * s_, C['pos'][1] + u * s_ + v * c_)
                    for u, v in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))])


_inside = np.array([court_poly(1.5).contains(Point(x, y)) for x, y in pts]).reshape(X.shape)
if _inside.any():
    _soft = ndimage.gaussian_filter(ndimage.binary_dilation(_inside, iterations=1).astype(float), 1.0)
    Hn = Hn * (1 - _soft) + float(Hn[_inside].mean()) * _soft
# 활천대's pool and flagstones on level ground (the water stands only 5 cm over the flagstones, and the lawn there fell
# 0.4 m across the pool): every node of the 5 m grid whose cells the flagstones reach, eased into the lawn round it
_inside = shapely.contains_xy(Point(*FOUNTAIN['pos']).buffer(FOUNTAIN['pave'] + 7.1), X, Y)
_lvl = float(Hn[shapely.contains_xy(Point(*FOUNTAIN['pos']).buffer(FOUNTAIN['pave']), X, Y)].mean())
_soft = ndimage.gaussian_filter(ndimage.binary_dilation(_inside, iterations=1).astype(float), 1.0)
_soft[_inside] = 1.0
Hn = Hn * (1 - _soft) + _lvl * _soft

# --- 정구장 (tennis courts), 1997.  The 1990 and 1995 campus maps (reference/1990_캠퍼스_지도.png, 1995_캠퍼스_지도.jpg)
# have 47 정구장 by the main road south-west of 공학관, and the 1995 aerial photo (reference/1995_캠퍼스_항공사진_남쪽에서.jpg)
# shows two fenced blocks of courts there between the road's tree row and the engineering halls: red clay courts to the
# west, green hard courts east of them, a little higher up the slope.  공학원 (2000s, left out) stands on them now, in
# the block between the service roads that is empty in the game.  Sized from the photo against 백양로 (22 m from
# planting strip to planting strip): ~50 m across each block; three courts each, their long axes up the slope.
TENNIS = dict(o=[-222.0, -392.0], rot=math.radians(-13.0),
              pads=[dict(kind='clay', u=[-64.0, -14.0], v=[8.0, 44.0], courts=3),
                    dict(kind='hard', u=[-8.0, 43.0], v=[8.0, 44.0], courts=3)])


def tennis_poly(pd, pad=0.0):
    c_, s_ = math.cos(TENNIS['rot']), math.sin(TENNIS['rot'])
    (u0, u1), (v0, v1) = pd['u'], pd['v']
    return Polygon([(TENNIS['o'][0] + u * c_ - v * s_, TENNIS['o'][1] + u * s_ + v * c_)
                    for u, v in ((u0 - pad, v0 - pad), (u1 + pad, v0 - pad), (u1 + pad, v1 + pad), (u0 - pad, v1 + pad))])


for _pd in TENNIS['pads']:          # each block a level pad on the slope, banked into the ground round it
    _inside = shapely.contains_xy(tennis_poly(_pd, 6.0), X, Y)        # (a 5 m grid cell past the kerb, or it pokes through)
    _pd['h'] = round(float(Hn[shapely.contains_xy(tennis_poly(_pd), X, Y)].mean()), 2)
    _soft = ndimage.gaussian_filter(ndimage.binary_dilation(_inside, iterations=1).astype(float), 1.0)
    _soft[_inside] = 1.0
    Hn = Hn * (1 - _soft) + _pd['h'] * _soft
print('tennis pads', [p_['h'] for p_ in TENNIS['pads']])

# --- old 노천극장 (1933 - 1997, reference/고증.md 3.14): grass terraces the students and staff dug into the ridge, a
# horseshoe round a pale earth floor, open to the west onto a low stage and the walk in from the 진입 광장 (the sun set
# behind the stage, as it does behind the new theatre built on the site in 1999).  Local frame: u east (up the middle
# of the seats), v north.  seat_end: the horseshoe's two ends, degrees round from +u; a flight runs up beside each.
AMPH = dict(cx=154.0, cy=160.0, arena_rx=15.0, arena_ry=15.5, rows=18, row_d=1.1, row_h=0.32, seat_end=118.0,
            stage_u=-8.0, stage_d=12.0, stage_w=18.0, stage_h=0.8, rot=0.0)
# The campus scatter keeps clear of this circle and the 1999 theatre's paths (OSM) are cleared inside this ellipse:
# the bowl as first modelled (rot 45°), kept as they were so that the random layout elsewhere does not move
AMPH_CLEAR = (160.0, 163.0, 43.0)
AMPH_PATHS = Polygon([(160 + 43 * math.cos(a) * math.cos(math.pi / 4) - 39 * math.sin(a) * math.sin(math.pi / 4),
                       163 + 43 * math.cos(a) * math.sin(math.pi / 4) + 39 * math.sin(a) * math.cos(math.pi / 4))
                      for a in np.linspace(0, 2 * math.pi, 64)])
amph_poly = None
for wv in ways.values():
    if wv['id'] == 180788744:
        amph_poly = Polygon([xy(p) for p in wv['geometry']]).buffer(0)


def amph_uv(x, y):
    dx, dy = x - AMPH['cx'], y - AMPH['cy']
    c, s = math.cos(AMPH['rot']), math.sin(AMPH['rot'])
    return dx * c + dy * s, -dx * s + dy * c


def amph_xy(u, v):
    c, s = math.cos(AMPH['rot']), math.sin(AMPH['rot'])
    return AMPH['cx'] + u * c - v * s, AMPH['cy'] + u * s + v * c


# the stage is level with the ground behind it (the walk in from the west), the floor a stage lower
AMPH['arena_h'] = round(sample(Hn, NEAR_HALF, NEAR_STEP, *amph_xy(AMPH['stage_u'] - AMPH['stage_d'], 0)) - AMPH['stage_h'], 2)
AMPH_DEPTH = AMPH['rows'] * AMPH['row_d']           # the floor's edge to the rim


def amph_d(x, y):
    """How far out from the floor's edge (negative on the floor) and the angle round from +u (degrees, 0 - 180), as
    blender/landmarks.py lays the rows: the point (rx + d) cos t, (ry + d) sin t."""
    u, v = amph_uv(x, y)
    rx, ry = AMPH['arena_rx'], AMPH['arena_ry']
    lo, hi = 0.05 - min(rx, ry), 400.0
    for _ in range(40):
        d = (lo + hi) / 2
        lo, hi = (d, hi) if (u / (rx + d)) ** 2 + (v / (ry + d)) ** 2 > 1 else (lo, d)
    d = (lo + hi) / 2
    return d, math.degrees(abs(math.atan2(v / (ry + d), u / (rx + d))))


def amph_height(x, y):
    """The bowl's surface, continuous (the front edges of the treads): the floor, then a row up per row_d to the rim."""
    d = min(max(amph_d(x, y)[0], 0.0), AMPH_DEPTH)
    return AMPH['arena_h'] + d / AMPH['row_d'] * AMPH['row_h']


# The 1997 photo was taken from the slope beyond the east end of the seats, looking west over the bowl (its camera
# fitted to the stage wall, the flights and the floor's edge: reference/고증.md 3.14.1).  Nothing stood between it and
# the floor but a tree at the left edge of the frame: no trunk or crown in the rest of its view on this side of the rim
AMPH_PHOTO = dict(x=211.6, y=152.4, yaw=169.7, left=15.0, right=-23.0)


def _in_photo_view(x, y, crown=4.5):
    dx, dy = x - AMPH_PHOTO['x'], y - AMPH_PHOTO['y']
    dist = math.hypot(dx, dy)
    if dist < 1.0 or dist > 32 or amph_uv(x, y)[0] < 0:
        return False
    off = (math.degrees(math.atan2(dy, dx)) - AMPH_PHOTO['yaw'] + 180) % 360 - 180
    m = math.degrees(math.atan2(crown, dist))
    return off - m < AMPH_PHOTO['left'] and off + m > AMPH_PHOTO['right']


# the bowl replaces the hillside (cut into it on the north and east, a bank on the south), easing back past the rim.
# The 5 m grid cannot follow the floor's edge or the rows: it stays under the floor and the treads (the walker
# and the trees stand on the landmark mesh), dipping 0.9 m more round the floor's edge where the slope breaks
_floor = AMPH['arena_h']
_top = _floor + AMPH['rows'] * AMPH['row_h']
_stage = _floor + AMPH['stage_h']
_back = AMPH['stage_u'] - AMPH['stage_d'] - 6.0     # the level ground behind the stage ends here
_mr = min(AMPH['arena_rx'], AMPH['arena_ry'])
for j in range(n_near):
    for i in range(n_near):
        x, y = gx[i], gx[j]
        u, v = amph_uv(x, y)
        if math.hypot(u, v) > 95:
            continue
        d, ang = amph_d(x, y)
        dip = 0.9 * _smooth(1 - abs(d) / 6.0)
        if ang <= AMPH['seat_end']:
            # the floor, the terraces, the path round the rim
            h = _floor - 0.3 - dip if d <= 0 else (amph_height(x, y) - 0.3 - dip if d <= AMPH_DEPTH else _top - 0.05)
        else:
            # the open (west) end: the floor runs on between the stage and the seat ends; the stage and the level ground
            # behind it; banks falling away from the flights beside the seat ends
            h = (_floor - (0.3 + dip if d <= 0 else 0.1)) if u > AMPH['stage_u'] - 2.5 else _stage - 0.12
            if d > 0:
                off = math.radians(ang - AMPH['seat_end']) * (_mr + d)       # metres out from the seat end
                h = max(h, amph_height(x, y) - 0.3 - dip - 0.6 * max(off - 1.8, 0.0))
        t = _smooth((d - AMPH_DEPTH - 3.0) / 14.0)
        if ang > AMPH['seat_end']:
            t = max(t, _smooth((_back - u) / 10.0))
        Hn[j, i] = h * (1 - t) + Hn[j, i] * t

# ---------------------------------------------------------------------------
# Buildings
# ---------------------------------------------------------------------------


def ground_h(x, y):
    return sample(Hn, NEAR_HALF, NEAR_STEP, x, y)


# 백주년기념관 (#162, reference/고증/3.4 and 2.1-2.2 「2.2.2」): the 1997 vertical aerial photos have its 백양로 face
# 2.5 - 2.9 m and its drum 3.7 m east-south-east of OSM's outline (the drum's rim from three frames, (-5.0, -242.8)),
# as Kakao's base map does (3.2 m out of the face) and its skyview; the same photos put the carriageway 5.4 m east, so
# that the hall's forecourt keeps the width they give it.  The hall moves 3.2 m straight out of its 백양로 face (along
# it the aerial drum and the base map differ by 0.8 m: kept).  The random planting reads the outline as it was
# (footprint(rng=True): ball_rng, the aprons of the ground it reads)
BLD_MOVE = {324328422: (3.11, -0.73)}
# 연희관's end pavilions (reference/고증/3.5 「양끝 날개」).  In the hall's frame (YH_HALL_A -> YH_HALL_B: OSM's recessed
# front, u along it eastwards, v into the hall) the vertical aerial photos of 1997-07-28 have the two pavilions' roofs
# 11.1 and 11.0 m from eave to eave (each eave read on the 73 - 76 m planes from the camera that does not see its
# wall, courses 26 and 27: u -11.3 .. -0.2 and 41.7 .. 52.7, the ridges midway at 79.4 - 79.9 m, the eaves at 73.7 -
# 74.2), their south gables 3.4 and 2.8 m in front of the main block's eave and their north ends at v 27.6 and 29.1;
# Kakao's base map draws the same plan (walls: u -11.0 .. -0.75 and 41.0 .. 51.5, v -3.3 and -2.15 to 27.5 and 28.75,
# the front between them 41.75 m).  OSM has them 14.1 and 11.7 m wide, 7.9 and 6.7 m out and 1.2 m longer behind.
# (u0, u1, v0, v1) of the walls; the random planting reads OSM's outline (footprint(rng=True)).
YH_HALL_A, YH_HALL_B = (69.75, 363.79), (108.51, 352.64)
YH_HALL = dict(main=(-0.6, 41.6, 0.0, 14.8), west=(-11.0, -0.6, -3.4, 27.6), east=(41.6, 52.0, -2.8, 29.0))


def _yh_hall_xy(u, v):
    t_ = np.array(YH_HALL_B) - np.array(YH_HALL_A)
    t_ = t_ / np.linalg.norm(t_)
    return tuple(float(c_) for c_ in np.array(YH_HALL_A) + t_ * u + np.array([-t_[1], t_[0]]) * v)


BLD_SHAPE = {245623759: [_yh_hall_xy(*q_) for q_ in (
    lambda m, w, e: [(w[0], w[3]), (w[0], w[2]), (w[1], w[2]), (m[0], m[2]), (m[1], m[2]), (e[0], e[2]), (e[1], e[2]),
                     (e[1], e[3]), (e[0], e[3]), (m[1], m[3]), (m[0], m[3]), (w[1], w[3])])(
    YH_HALL['main'], YH_HALL['west'], YH_HALL['east'])]}
FRAME_AB = {245623759: (YH_HALL_A, YH_HALL_B)}       # (frame_from: the frame things were set out in stays OSM's)


def footprint(wv, rng=False):
    pts_ = [xy(p) for p in wv['geometry']]
    if not rng and wv['id'] in BLD_MOVE:
        pts_ = [(x_ + BLD_MOVE[wv['id']][0], y_ + BLD_MOVE[wv['id']][1]) for x_, y_ in pts_]
    if not rng and wv['id'] in BLD_SHAPE:
        pts_ = list(BLD_SHAPE[wv['id']])
    if pts_[0] == pts_[-1]:
        pts_ = pts_[:-1]
    poly = Polygon(pts_).buffer(0)
    if isinstance(poly, MultiPolygon):
        poly = max(poly.geoms, key=lambda g: g.area)
    poly = poly.simplify(0.35)
    if not poly.exterior.is_ccw:
        poly = Polygon(list(poly.exterior.coords)[::-1])
    return poly


# --- 대강당 앞 돌계단: the straight granite flight from 백양로's east sidewalk up to 대강당's forecourt, on the hall's
# axis (reference/고증.md 4.5).  Counted in four frames, the 2009 photo (reference/대강당_2009_앞길_계단.jpg) and Kakao
# roadview Dec. 2010 1016786028 · Apr. 2011 1017220198 · 1017220199: 24 risers, the 12th tread a landing where the
# side walls' coping turns level for a step and the slope changes.  The profile is fitted to the nosing rows of the
# two frames from in front (0.4 - 0.6 px): treads 0.27 m below the landing, 0.21 - 0.23 m above it, the landing
# 1.3 - 1.7 m; the head 3.5 - 3.7 m over the sidewalk (the horizon from the nosings' vanishing point and the lean of
# the hall's uprights, the treads seen from the 2.5 m camera up to the 16th riser).  The forecourt, the terrace on
# the bank and the court (AUD_BANK below) stand at the head's level: the hall's front had been only 0.8 m over the
# sidewalk here (5장).  Width 4.6 m between rubble side walls (the flight's width over the camera height, and the low
# wall's 0.72 m beside the foot), the first riser 0.25 m behind the wall's face, square posts in line with it.
_AF0, _AF1 = np.array([51.13, 28.26]), np.array([59.82, 61.16])     # 대강당's front (its OSM outline, south -> north)
_afv = (_AF1 - _AF0) / np.linalg.norm(_AF1 - _AF0)
_afu = np.array([-_afv[1], _afv[0]])                                 # out of the front (west, towards 백양로)


def _aud_axis_s():
    """arc length where 대강당's axis meets the face of 백양로's east wall (the sidewalk's outer edge)"""
    m_ = (_AF0 + _AF1) / 2
    off = lambda s_: float((np.array(along_raw(s_, -E_WALK)[:2]) - m_) @ _afv)
    a_, b_ = 470.0, 530.0
    for _ in range(50):
        c_ = (a_ + b_) / 2
        a_, b_ = (c_, b_) if off(a_) * off(c_) > 0 else (a_, c_)
    return round((a_ + b_) / 2, 2)


AUD_FLIGHT = dict(s=_aud_axis_s(), w=4.6, cheek=0.42, foot=0.25, n1=12, n2=12, t1=0.27, landing=1.4, t2=0.215,
                  rise=3.55, walk_z=0.15)
AUD_FLIGHT['axis'] = [round(float(-_afu[0]), 5), round(float(-_afu[1]), 5)]       # up the flight (into the hall)
AUD_FLIGHT['foot_z'] = round(prof_h(AUD_FLIGHT['s']) + AUD_FLIGHT['walk_z'], 3)
AUD_HEAD = round(AUD_FLIGHT['foot_z'] + AUD_FLIGHT['rise'], 2)       # the forecourt's level
AUD_FLIGHT['head_z'] = AUD_HEAD
AUD_FLIGHT['run'] = round(AUD_FLIGHT['foot'] + (AUD_FLIGHT['n1'] - 1) * AUD_FLIGHT['t1'] + AUD_FLIGHT['landing']
                          + (AUD_FLIGHT['n2'] - 1) * AUD_FLIGHT['t2'], 3)            # the wall's face to the head
_afh = AUD_FLIGHT['w'] / 2 + AUD_FLIGHT['cheek']
AUD_FLIGHT['s_range'] = [round(AUD_FLIGHT['s'] - _afh, 2), round(AUD_FLIGHT['s'] + _afh, 2)]   # (its foot along 백양로)
AUD_FLIGHT['o'] = [round(v_, 3) for v_ in along_raw(AUD_FLIGHT['s'], -E_WALK)[:2]]          # (the wall's face on its axis)
print('대강당 앞 돌계단: axis at s %.2f, foot %.2f, head %.2f m (s %.2f - %.2f), run %.2f m'
      % (AUD_FLIGHT['s'], AUD_FLIGHT['foot_z'], AUD_HEAD, *AUD_FLIGHT['s_range'], AUD_FLIGHT['run']))

# --- level aprons in front of the old halls.  The 5 m terrain grid smooths the hillsides behind 스팀슨관, 아펜젤러관
# and 연희관 down across their fronts, so the ground fell 2-4 m within a few metres of the doors and the entrance flights
# grew to 16-20 risers.  The photos (reference/스팀슨관_정면_2016.jpg, 아펜젤러관_정면_2016.jpg) show 8-9 risers up
# from a level walk: each front gets a level apron at the height of the ground along its wall,
# blending back into the slope beyond.
FORECOURTS = [  # OSM way, outward front direction (None: the recess edge footprint[3] -> [4] of an H plan), depth, options
    # 언더우드관 (first, from the untouched ground): the garden walk level up to the foot of its 16 steps
    # (reference/언더우드관_정면_2016.jpg); the garden beyond is filled smoothly from here (below), so only a short blend
    # (the three halls' aprons at the heights the vertical aerial photos of 1997 give the walks before them, 고증 2.8:
    # 언더우드관 47.55 - 47.9 m at five points along its front, the walk along 스팀슨관 45.9 - 47.0, along 아펜젤러관 45.9 -
    # 46.4.  From the ground along the walls they came out a metre higher: the surface model climbs behind the fronts)
    (246156115, (0.27, -1.0), 12.0, dict(blend=8.0, level=47.7)),
    (246156118, (1.0, -0.27), 11.0, dict(level=46.3)),      # 스팀슨관
    (246156116, (-1.0, 0.27), 11.0, dict(level=46.1)),      # 아펜젤러관
    # (연희관's front: YEONHUI below, with the garden before it)
    # 대강당: the 45 m wide flight under the canopy ran across a 2 m cross slope, its north end under the grass; level
    # at the head of the flight up from 백양로 (AUD_FLIGHT)
    (371403811, (-1.0, 0.25), 13.0, dict(max_half=27.0, blend=12.0, level=AUD_HEAD)),
    # 대우관 별관: likewise the lower of its two flights (10 m wide) on the slope of the road past its front
    (242897923, (-0.97, 0.24), 9.0, dict(max_half=10.0, blend=10.0)),
    # 백주년기념관's 백양로 front: the smoothed DEM drapes the hall's own bulk over its west lawn, a 3-5 m mound
    # against its dark porch; the 1997 aerial photo shows level lawn (and parked cars) from the sidewalk to the porch.
    # Level it at the hall's floor (its lowest corner, a little over 백양로 alongside)
    (324328422, None, 30.0, dict(face=((-11.05 + 3.11, -181.26 - 0.73), (-28.82 + 3.11, -256.68 - 0.73)), max_half=40.0, blend=8.0, level='corner',
                                         inside=7.0)),              # (and under the 5 m deep porch)
]
# 광복관 (blender/landmarks.py kwangbok): the 1996 album photos show a level gravel forecourt at the foot of its broad
# flight (ten or eleven risers up to the raised main floor), where the 5 m grid had the slope from the west run
# across the front, burying the west half of the flight.  Level the 28 m of front round the door (19 m along it).
_kbp = list(footprint(ways[468614722]).exterior.coords)
_kb0, _kb1 = np.array(_kbp[1]), np.array(_kbp[2])
_kbt = (_kb1 - _kb0) / np.linalg.norm(_kb1 - _kb0)
FORECOURTS.append((468614722, None, 12.0, dict(face=(tuple(_kb0 + _kbt * 5.0), tuple(_kb0 + _kbt * 33.0)), max_half=14.0,
                                                blend=10.0, inside=1.0)))
FIXED = np.zeros(X.shape, bool)       # grid nodes a later harmonic fill must keep: the level aprons themselves
# 백주년기념관's low front block (issue #9).  In the 1997 aerial photo the hall's south-west corner is a lower block,
# its long face towards the camera (the south face) with a wide dark entrance, its short west side with a dark door,
# and above that side a light wall stepping up towards the porch.  The photo alone only gave a family of sizes; the
# 2010 roadview fixes it (reference/고증.md 3.4; the 2008 one shows the same block): triangulated from the four
# panoramas on the road south of it (their headings checked against the drum's banner, residuals 0.3 m) the corner
# stands 1.0 m west of the outline's 백양로 face and 1.1 m north of its south-west corner, the front with the entrance
# runs ~25 m east to where the drum comes down to the ground, and its top (with the coping) ~7 m over the hall's floor
# (6.3 and 7.7 m from two panoramas; the 1997 photo's corner, y 642, with its refitted camera: 7 m).
# The entrance spans 0.7 - 9.7 m from the corner (a door under a window band, then square piers).  blender/landmarks.py
# builds it from this and cuts the podium round it.
_cnw, _csw, _cse = (np.array(p_) + BLD_MOVE[324328422] for p_ in ((-11.05, -181.26), (-28.82, -256.68), (-12.33, -261.24)))
_tw = (_cnw - _csw) / np.linalg.norm(_cnw - _csw)                 # the 백양로 face, south -> north
_ts = (_cse - _csw) / np.linalg.norm(_cse - _csw)                 # the south face, west -> east
_nw = np.array([-_tw[1], _tw[0]])                                 # out of the 백양로 face (west)
_c0_rv = _csw + _nw * 1.0 + _tw * 1.1                              # (the corner as first placed, moved with the hall)
# The 1997 vertical aerial photos (reference/고증.md 3.4 「낮은 몸체의 윤곽」, tools/aerial97_cent.py; the 2008 · 2010
# skyview shows the same plan): the low part is one storey-and-a-half volume wrapped round the drum's west foot, not a
# box 19.6 m deep.  Its roof edge, read where a west and an east frame agree (36.5 - 37.1 m, 7 m over the hall's
# floor): the corner block's west side 3.5 m west of where the block stood (4.5 m out of the hall's 백양로 face: the
# OSM outline's face, which #162 moved east with the upper hall, was this low wall's) for about 11 m; north of it a
# wall 1.7 m further in, tangent to an arc of 19.1 m round the drum's centre (2.1 m outside the drum) that runs on
# to the hall's face 48 m south of its north-west corner: the curved glass wall of the 1996 side photo.
_c0 = _c0_rv - _ts * 3.5
_CBF, _CBS, _CBH = 25.0, 11.0, 6.6                                 # front, side, height (its coping 0.4 over)
_cdr = np.array([-8.6, -241.8]) + BLD_MOVE[324328422]              # the drum's centre (blender/landmarks.py CENT_DRUM)
_CTR = 19.1                                                        # the low curved wall's radius about it
_ctT = _cdr + _nw * _CTR                                           # where the arc turns into the straight wall
_ctW = _ctT - _tw * float((_ctT - (_c0 + _tw * _CBS)) @ _tw)       # the straight wall's south end, at the block
_sj = float((_cdr - _cnw) @ -_tw) - math.sqrt(_CTR ** 2 - float((_cdr - _cnw) @ _nw) ** 2)
_ctJ = _cnw - _tw * _sj                                            # the arc's north end, on the hall's face
_aJ, _aT = (math.atan2(q_[1] - _cdr[1], q_[0] - _cdr[0]) for q_ in (_ctJ, _ctT))
CENT_BLOCK = dict(corner=[round(float(v), 2) for v in _c0], t_front=[round(float(v), 4) for v in _ts],
                  t_side=[round(float(v), 4) for v in _tw], front=_CBF, side=_CBS, h=_CBH,
                  entrance=[0.7, 9.7, 2.7], door=None, parapet=[],
                  tier=dict(c=[round(float(v), 2) for v in _cdr], r=_CTR, south=[round(float(v), 2) for v in _ctW],
                            face_s=round(_sj, 2)))
CENT_BLOCK['poly'] = [[round(float(v), 2) for v in q] for q in
                      [_c0, _c0 + _ts * _CBF, _c0 + _ts * _CBF + _tw * _CBS, _ctW - _nw * 4.0, _ctJ - _nw * 1.0] +
                      [_cdr + _CTR * np.array([math.cos(a_), math.sin(a_)]) for a_ in np.linspace(_aJ, _aT, 9)] +
                      [_ctW, _c0 + _tw * _CBS]]
# (its forecourt: level at the hall's floor like the 백양로 side, so the entrance is not half buried; kept where it
# was first levelled, so the ground does not change)
FORECOURTS.append((324328422, None, 14.0, dict(face=(tuple(_c0_rv), tuple(_c0_rv + _ts * 25.0)), max_half=25.0 / 2 + 1.0,
                                                blend=8.0, level='corner', inside=1.0)))
# 백주년기념관's north-east face, towards 광혜원 and 수경원 (연세 역사의 뜰): a plain stone box with three rows of strip
# windows over a paved court (2010 roadview; blender/landmarks.py north_box).  The museum's own door, the one in the
# 1996 album photos, is in the 백양로 porch (museum_porch, CENT_MUSEUM below).  The ground there stood 3 m over the
# hall's floor (the hall's lowest corner, by 백양로); the court is levelled 2.6 m over that corner (42.7 m on the old
# terrain, 광혜원's height there).
CENT_NE = ((41.28 + 3.11, -200.97 - 0.73), (16.84 + 3.11, -168.65 - 0.73))       # the face, its outside to the right


def corner_level(wid):
    """the lowest ground under a hall's outline corners (level_forecourt's 'corner')"""
    return min(sample(Hn, NEAR_HALF, NEAR_STEP, x_, y_) for x_, y_ in footprint(ways[wid]).exterior.coords)


CENT_PLAZA_H = round(corner_level(324328422) + 2.6, 2)
FORECOURTS.append((324328422, None, 18.0, dict(face=CENT_NE, max_half=20.3, blend=10.0, level=CENT_PLAZA_H, inside=1.0)))
# the museum's doors in the 백양로 porch (blender/landmarks.py museum_porch): the 1996 album photos of 화학공학 · 전기 ·
# 전자 · 건축공학 · 기계설계 · 컴퓨터과학과 on its broad granite flight, glass between a white wall (left, north) and a
# white cylinder (right, south) - the same frontage the 2008 · 2010 · 2011 roadview shows there.  Its doors' middle on
# the face (s from the north-west corner, the porch from where the drum's ring meets the face) and the face's outward normal
CENT_MUSEUM = dict(s=21.9, door=[round(float(v), 2) for v in _cnw - _tw * 21.9], n=[round(float(v), 4) for v in _nw])
# 과학관's courtyard flight (blender/generic.py porch, ENTRY_AT): in the 1996 photos of 생물학과, 생화학과 and 지질학과
# fifteen-odd granite risers climb the whole width of the picture to the cream wall, between sloped granite side walls
# with clipped junipers on banks either side, a five-globe lamp at the top.  The 5 m grid ran the courtyard's slope
# up to the doors; the game first levelled a car park 2.8 m under doors on the third floor (5.9 m over the hall's
# lowest corner).  The 1997-07-28 aerial photos (reference/고증/3.10) have the courtyard a paved court 43 m by 39 m at
# 50.8 m, level with the road past the hall's east end to 2 - 3 m and 25.7 m under the east wing's roof: the doors
# are on the second floor (a storey over the hall's floor, 2.3 m over the court), the bank with its bushes 5 m deep
# all along the wing's south face (sci_grade below, after the other forecourts).
SCI_DOOR, SCI_N = np.array([-242.6, 13.81]), np.array([-0.2629, -0.9648])
SCI_T = np.array([-SCI_N[1], SCI_N[0]])


def sci_grade():
    """과학관: the courtyard level (SCI['court']) from the link's wall to 4 m short of the east end and 44 m out of the
    east wing's south face, running in under the flight (8.8 m either side of the door); beside the flight a bank
    from the doors' level at the wall down to the court 5.8 m out.  The yard north-west of the link (the fan-shaped
    hall and the low block on it) level at SCI['yard']."""
    U = (X - SCI['o'][0]) * SCI['t'][0] + (Y - SCI['o'][1]) * SCI['t'][1]
    V = (X - SCI['o'][0]) * SCI['n'][0] + (Y - SCI['o'][1]) * SCI['n'][1]
    D = 0.3 - V
    ud = float((SCI_DOOR - SCI['o']) @ SCI['t'])
    bank = np.clip((np.abs(U - ud) - 8.8) / 3.0, 0, 1) * np.clip((5.8 - D) / 5.0, 0, 1)
    z = SCI['court'] + (SCI['base'] + FLOOR_H_AT[222843398] - 0.1 - SCI['court']) * bank
    e = np.maximum.reduce([(-53.6 - U) / 3.0, (U + 4.0) / 6.0, (D - 44.5) / 6.0, -D / 6.0, np.zeros_like(U)])
    w = np.clip(1 - e, 0, 1)
    Hn[:] = Hn * (1 - w) + z * w
    FIXED[w > 0.999] = True
    yard = sci_poly([(-118.7, -25.6), (-121.0, -12.0), (-86.0, 15.5), (-72.4, 18.4), (-72.4, 0.3), (-67.7, 0.3), (-67.7, -25.6)])
    m = (np.abs(X + 300) < 70) & (np.abs(Y - 20) < 60)
    wy = np.zeros_like(U)
    wy[m] = np.clip(1.0 - shapely.distance(yard, shapely.points(X[m], Y[m])) / 5.0, 0, 1)
    Hn[:] = Hn * (1 - wy) + SCI['yard'] * wy
    FIXED[wy > 0.999] = True
    print('과학관: court %.2f, doors %.2f, yard %.2f' % (SCI['court'], SCI['base'] + FLOOR_H_AT[222843398], SCI['yard']))


# 빌링슬리관's south front (its door: ENTRY_AT).  The 5 m grid ran the slope from the north-west across it, 3.7 m
# along the 45 m front, so the door in its middle stood 1.6 m under the ground and the west half of the ground floor
# was buried.  reference/학교연혁_빌링슬리관_옛생활과학관.jpg, from the lawn at the west end, shows the ground floor
# standing on a level lawn all along the front: level it at the floor (its south-east corner), a riser or two under
# the threshold, banking back up into the hill at the west end (its lowest corner, 0.1 m under).
BILL_FRONT = ((14.11, 417.87), (57.73, 406.29))      # the south front, west -> east (the outside to the right)
FORECOURTS.append((245623193, None, 12.0, dict(face=BILL_FRONT, max_half=23.0, blend=10.0, side_blend=9.0,
                                                level='corner', rise=-0.1, inside=2.0)))
# 연합신학대학원 (UTS above; reference/고증/3.1 「3.1.1」): the 5 m grid runs the hillside 4.3 m up across the 1997
# hall, its north-west corner in the ground to the upper floor.  The aerial photos have the yard south of it and the
# strip along its east wall level (61.4 - 61.7 m in their datum; the grid 60.9 - 62.6 m along that wall): a level
# shelf under the hall and 5 m out of its east wall, at the ground along that wall, cut into the hill behind it.
FORECOURTS.append((UTS, None, 5.0, dict(face=(LATE_FOOTPRINT_1997[UTS][1], LATE_FOOTPRINT_1997[UTS][2]), max_half=17.0,
                                        blend=6.0, side_blend=7.0, inside=13.0)))
# 교육관 (blender/landmarks.py gyoyuk): its west side stands three full storeys over the drive below 제2인문관
# (reference/2003_가을_교육관_서쪽면.jpg, taken from there) and its north end's outside flight starts from a yard of
# parked cars at the ground floor (2003_가을_연희관앞정원과_교육관_북쪽계단.jpg).  The 5 m grid ran the hill from 종합관
# and 제2인문관 down over both: the ground stood 3-4 m over the floor at the north-west corner.  Level the drive and
# the yard at the floor, banking back up to the hill beyond.
GYOYUK_FLOOR = round(corner_level(246156111) + 2.3, 2)     # (53.0 m on the old terrain; blender/landmarks.py reads it)
FORECOURTS.append((246156111, None, 6.0, dict(face=((26.82, 349.67), (17.82, 314.97)), max_half=18.0, blend=7.0,
                                               side_blend=6.0, level=GYOYUK_FLOOR, inside=1.0)))      # the west drive
FORECOURTS.append((246156111, None, 11.0, dict(face=((44.15, 345.23), (26.82, 349.67)), max_half=9.0, blend=6.0,
                                                side_blend=5.0, level=GYOYUK_FLOOR, inside=1.0)))     # the north yard
# 외솔관2 (1991, on the corridor between 인문관 and 종합관; reference/고증.md 3.1.1): three storeys from its low east end,
# two from the car park at its west end.  Kakao roadview of June 2026 from that car park (pano 1212397635, 20 m off
# the west end): 7.5 m of wall shows over the car park's level, and 종합관's west wing stands there on its pilotis
# with four storeys over them.  The surface model keeps the woods and the halls round the car park, so the 5 m grid
# had the ground at the west end 10.9 m over the east end and the car park over the block's roof.  Level the car park
# at the block's lowest corner + 4.5 m (its 12.6 m less the 7.5 showing: 5.1; a storey: 3.8), banking back up into the
# wooded slope beyond (the face run on 9 m either way: the car park reaches 종합관's west end and 인문관's north wall);
# the passages along its sides and the service road through the car park are graded and filled (OESOL_ROAD below).
OESOL_LEVEL = round(corner_level(246156114) + 4.5, 2)
FORECOURTS.append((246156114, None, 18.0, dict(face=((-90.10, 300.95), (-97.34, 271.24)), max_half=16.0, blend=14.0,
                                                side_blend=10.0, level=OESOL_LEVEL, inside=1.0)))
# 스팀슨관 · 아펜젤러관's backs (blender/landmarks.py stone_hall rear; reference/고증.md 3.5): the 2013 survey's rear
# elevations and the 2010 roadview from the roads behind show the ground at the foot of the back walls about as low as
# in front, the half-sunk basement's windows clear and the back door a riser or two over it; the 5 m grid ran the
# hill behind down over them, 3 - 4 m up the ground floor.  Level a strip at the halls' lowest corner (behind
# 아펜젤러관 a yard of parked cars in the roadview), banking up to the roads behind.
FORECOURTS.append((246156118, None, 3.0, dict(face=((14.6, 245.96), (6.1, 214.59)), max_half=16.3, blend=9.0,
                                                side_blend=6.0, level='corner', inside=1.0)))         # 스팀슨관
FORECOURTS.append((246156116, None, 9.0, dict(face=((92.93, 188.38), (102.01, 221.82)), max_half=17.3, blend=6.0,
                                                side_blend=6.0, level='corner', inside=1.0)))         # 아펜젤러관


def level_forecourt(wid, front, depth, blend=18.0, side_blend=7.0, max_half=20.0, level=None, face=None, inside=2.0,
                    rise=0.0):
    poly = footprint(ways[wid])
    if face is not None:
        # an explicit face (two footprint corners, the outside to their right)
        (ax, ay), (bx, by) = face
        hl = math.hypot(bx - ax, by - ay)
        fx, fy = (by - ay) / hl, -(bx - ax) / hl
        mx, my, hl = (ax + bx) / 2, (ay + by) / 2, hl / 2
    elif front is None:
        (ax, ay), (bx, by) = list(poly.exterior.coords)[3], list(poly.exterior.coords)[4]
        hl = math.hypot(bx - ax, by - ay)
        fx, fy = (by - ay) / hl, -(bx - ax) / hl         # out of the courtyard between the wings
        mx, my, hl = (ax + bx) / 2, (ay + by) / 2, hl / 2
    else:
        n_ = math.hypot(*front)
        fx, fy = front[0] / n_, front[1] / n_
        rr = list(poly.minimum_rotated_rectangle.exterior.coords)[:-1]
        c_ = poly.centroid
        best = None
        for k in range(4):
            (ax, ay), (bx, by) = rr[k], rr[(k + 1) % 4]
            mx_, my_ = (ax + bx) / 2, (ay + by) / 2
            # the side whose outward normal is closest to the front (not the midpoint furthest that way, which on a
            # long hall with a slanted front vector is an end wall)
            el = math.hypot(bx - ax, by - ay)
            nx_, ny_ = (by - ay) / el, -(bx - ax) / el
            if nx_ * (mx_ - c_.x) + ny_ * (my_ - c_.y) < 0:
                nx_, ny_ = -nx_, -ny_
            sc_ = nx_ * fx + ny_ * fy
            if best is None or sc_ > best[0]:
                best = (sc_, mx_, my_, math.hypot(bx - ax, by - ay) / 2)
        _, mx, my, hl = best
    tx, ty = -fy, fx
    hw = min(hl, max_half)
    if level == 'corner':
        level = min(sample(Hn, NEAR_HALF, NEAR_STEP, x_, y_) for x_, y_ in poly.exterior.coords) + rise
    if level is None:
        level = float(np.mean([sample(Hn, NEAR_HALF, NEAR_STEP, mx + tx * s + fx, my + ty * s + fy) for s in np.linspace(-hw, hw, 7)])) + rise
    S = (X - mx) * tx + (Y - my) * ty
    D = (X - mx) * fx + (Y - my) * fy
    e = np.maximum.reduce([(np.abs(S) - hw) / side_blend, (D - depth) / blend, (-D - inside) / side_blend, np.zeros_like(S)])
    w = np.clip(1 - e, 0, 1)                    # a straight grass bank (the 5 m grid rounds its edges)
    w *= np.clip((dist - (ROAD_HALF + 4)) / 8.0, 0, 1)     # never under 백양로 and its sidewalks
    Hn[:] = Hn * (1 - w) + level * w
    FIXED[w > 0.999] = True
    print('forecourt', wid, 'level', round(level, 2))


for wid, front, depth, opt in FORECOURTS:
    level_forecourt(wid, front, depth, **opt)
sci_grade()


def jk_grade():
    """연구관 · 장기원 기념관 (the 1997-07-28 aerial photos, reference/고증/3.15-3.17): the yard west of 연구관's bar level at
    JK_YARD out to 16 m from its middle line, the ground east of it a terrace at JK_TERRACE as far as 장기원 기념관's
    block, whose east wall stands 8.5 m lower by the road past the library's back (the 5 m grid ran one slope across
    it all)."""
    jk = lambda u_, v_: tuple(JK_O + JK_A * u_ + JK_V * v_)
    mid = [jk(-30.5, -0.75), jk(21.0, -0.75), jk(37.0, -0.75)]
    west = Polygon(mid + [jk(40.0, 16.0), jk(-30.0, 16.0)])
    # (as far as the middle line of 장기원 기념관's block: its east wall stands on the low ground)
    east = Polygon(mid[::-1] + [(-173.0, -45.0), (-161.7, -45.0), (-160.6, -40.4), (-151.9, -7.6), (-146.0, -5.0),
                                (-143.0, 30.0), (-156.0, 45.0)])
    m = (np.abs(X + 170) < 70) & (np.abs(Y - 5) < 75)
    for poly_, z_ in ((west, JK_YARD), (east, JK_TERRACE)):
        w = np.zeros(X.shape)
        w[m] = np.clip(1.0 - shapely.distance(poly_, shapely.points(X[m], Y[m])) / 5.0, 0, 1)
        Hn[:] = Hn * (1 - w) + z_ * w
        FIXED[w > 0.999] = True


# (jk_grade() runs once the planting, the doors' zones and the walks are laid, just before the ground is saved: the
# old halls' doors, and with them the trees and the paving's stains, were first found on the ground without it)

# --- 음악관 (reference/고증/3.11_음악관.md).  The 1996 album photo's porch (a deep canopy on two round white columns
# over glass doors, white square tiles, blue frames) is 신관's (429077790, 1991): its main door in the middle of the
# south front under the curved stair tower, which Kakao roadview 2008-08 · 2010-12 · 2026 show unchanged and the
# skyview's half-round canopy puts 33 m along the front.  구관 (429077789, 1982) has plain doors under its first floor's
# overhang.  The 5 m grid ran the slope up across both fronts (4.9 m along 구관's 61 m, burying its ground floor towards
# the east end and the porch; 1.6 m up to 신관's door), where the roadview shows:
# - 구관: the road and the sidewalk beside it about level along the whole front, both doors five or six risers over
#   the road (three or two over the sidewalk, which is three or two over the road)
# - 신관: its door five risers over a level forecourt at the road's level
# - the glazed corridor between them leaves 구관 a storey over its doors and comes into 신관 over the open ground
#   under its west end
# The game first read that corridor as 구관's first floor into 신관's ground floor and stood 구관 a storey (3.6 m)
# lower, the road climbing 9 % between the halls.  The 1997-07-28 vertical aerial photos (reference/고증/3.11) have the
# road along 구관's front a little over 신관's forecourt, not a storey under it: 59.2 m (26 points, 58.3 - 59.6) against
# 58.6 m (61 points, 57.7 - 58.8; 58.7 between the halls) in their datum, and the roofs 1.5 m apart (72.7 and
# 74.2 m); the 2010 roadview from between the halls looks along a road about level both ways.  So 신관's floor stays
# at its lowest corner and its forecourt is levelled five risers under it; the road and sidewalk along 구관's front
# stand 0.7 m over that forecourt (falling to it between the halls) and 구관's floor 0.8 m over them (MUSIC_BASE: the
# halls' floors, set after the outlines below).  West of 구관 the photos keep that height round the hall's end and
# north along the road behind it (58 - 60 m as far as y 115), where the game's ground is 4 - 8 m lower
# (reference/고증/2.8: this side of the campus is that much low): the front eases into it past the hall's west end,
# and the road round that end climbs to it (music_grade).
MUSIC_A, MUSIC_B = 429077789, 429077790
MUSIC_B_FLOOR = round(corner_level(MUSIC_B), 2)
MUSIC_B_YARD = round(MUSIC_B_FLOOR - 0.68, 2)
MUSIC_A_ROAD = round(MUSIC_B_YARD + 0.7, 2)
MUSIC_A_FLOOR = round(MUSIC_A_ROAD + 0.8, 2)
MUSIC_BASE = {MUSIC_A: MUSIC_A_FLOOR, MUSIC_B: MUSIC_B_FLOOR}
MU_O = np.array([130.15, -8.06])                                      # 구관's south front, west -> east
MU_T = (np.array([189.49, -23.68]) - MU_O) / np.linalg.norm(np.array([189.49, -23.68]) - MU_O)
MU_N = np.array([MU_T[1], -MU_T[0]])                                  # out of it (south)
MB_O = np.array([207.41, -12.61])                                     # 신관's south front
MB_T = (np.array([261.16, -26.9]) - MB_O) / np.linalg.norm(np.array([261.16, -26.9]) - MB_O)


MU_WEST = (np.array([124.2, -6.8]), np.array([125.5, 51.8]))         # the road round 구관's west end, north behind it (OSM)


def music_grade(s_end=61.4, s_yard=100.0):
    """구관's front (S along it from its south-west corner, D out of it): level from 11 m past its west end (the road
    round that end) to 신관's forecourt (s_yard), over the road, the walk south of it and a little beyond (D 19 m), in
    front of its set-back east block too, and under the hall to 5 m behind its back wall (the ground round its west
    end and behind it stands at its front's height in the aerial photos); easing back over 15 m west, 12 m south,
    10 m north; from its east end (s_end) it falls to 신관's forecourt (s_yard).  The road north behind the hall
    (MU_WEST) keeps that level past the hall's north-west corner, then comes down to the ground it had 52 m on, a
    band 4 m either side of its middle easing out over 8 m."""
    S = (X - MU_O[0]) * MU_T[0] + (Y - MU_O[1]) * MU_T[1]
    D = (X - MU_O[0]) * MU_N[0] + (Y - MU_O[1]) * MU_N[1]
    z = MUSIC_A_ROAD + (MUSIC_B_YARD - MUSIC_A_ROAD) * np.clip((S - s_end) / (s_yard - s_end), 0, 1)
    inside = np.where(S < s_end + 12.0, 21.5 + 6.5 * np.clip((S - s_end + 3.0) / 4.0, 0, 1), 6.0)
    e = np.maximum.reduce([(-S - 11.0) / 15.0, (S - s_yard) / 6.0, (D - 19.0) / 12.0, (-D - inside) / 10.0,
                           np.zeros_like(S)])
    w = np.clip(1 - e, 0, 1) * np.clip((dist - (ROAD_HALF + 4)) / 8.0, 0, 1)
    ra, rb = MU_WEST
    rt = (rb - ra) / np.linalg.norm(rb - ra)
    z1 = sample(Hn, NEAR_HALF, NEAR_STEP, *(ra + rt * 72.0))
    Hn[:] = Hn * (1 - w) + z * w
    FIXED[w > 0.999] = True
    R = (X - ra[0]) * rt[0] + (Y - ra[1]) * rt[1]
    Q = np.abs((X - ra[0]) * rt[1] - (Y - ra[1]) * rt[0])
    zr = MUSIC_A_ROAD + (z1 - MUSIC_A_ROAD) * np.clip((R - 20.0) / 52.0, 0, 1)
    wr = np.clip(1 - (Q - 4.0) / 8.0, 0, 1) * np.clip((R + 6.0) / 6.0, 0, 1) * np.clip((78.0 - R) / 6.0, 0, 1)
    Hn[:] = Hn * (1 - wr) + zr * wr
    FIXED[wr > 0.999] = True


level_forecourt(MUSIC_B, None, 14.0, face=(tuple(MB_O + MB_T * 20.0), tuple(MB_O + MB_T * 56.5)), max_half=18.5,
                blend=8.0, side_blend=8.0, level=MUSIC_B_YARD, inside=1.0)
music_grade()
print('음악관: 신관 floor %.2f, forecourt %.2f; 구관 floor %.2f, front %.2f' % (MUSIC_B_FLOOR, MUSIC_B_YARD,
                                                                        MUSIC_A_FLOOR, MUSIC_A_ROAD))

# --- 논지당 (one storey, 1956) stands across the hillside east of 언더우드관.  The 5 m grid rose 5.4 m over its
# outline (about 1 in 4.5), more than the hall's 4.6 m, so the east end stood in the ground up to the eaves and only
# the roof showed.  Give it a level terrace at the ground before its door (the south-west front, the low side) under
# the whole outline, out to every grid node of the cells it touches, cut into the slope behind and easing back into
# it over 12 m.
_nj = footprint(ways[413217834])
NONJI_LEVEL = sample(Hn, NEAR_HALF, NEAR_STEP, 112.14 - 0.253 * 2.0, 251.72 - 0.968 * 2.0)   # 2 m out from the door
_njw = np.clip(1.0 - (shapely.distance(_nj, shapely.points(X, Y)) - 7.1) / 12.0, 0, 1)
Hn[:] = Hn * (1 - _njw) + NONJI_LEVEL * _njw
FIXED[_njw > 0.999] = True
print('논지당 terrace', round(NONJI_LEVEL, 2))


def harmonic_fill(free, iters=3000):
    """Give the `free` grid nodes the smoothest surface that meets the nodes around them (Laplace's equation, Jacobi
    iterations): no hollow, no ridge, the height difference spread evenly over the whole area instead of a bank."""
    jj, ii = np.nonzero(free)
    j0, j1, i0, i1 = jj.min() - 1, jj.max() + 2, ii.min() - 1, ii.max() + 2
    H, F = Hn[j0:j1, i0:i1].copy(), free[j0:j1, i0:i1]
    for _ in range(iters):
        avg = 0.25 * (H[:-2, 1:-1] + H[2:, 1:-1] + H[1:-1, :-2] + H[1:-1, 2:])
        inner = H[1:-1, 1:-1]
        inner[F[1:-1, 1:-1]] = avg[F[1:-1, 1:-1]]
    Hn[j0:j1, i0:i1][F] = H[F]


# --- 대운동장 (46 육상경기장 on the 1990 map), 1997 (reference/고증/4.12).  The elevation grid smooths the cut the field
# lies in into one slope from the hillside north of it (44 m) down to 성산로 (33 m), and the field stood at that
# slope's mean, 37.1 m: level with the road past its east end and 4.7 m over the 야구장.  The vertical aerial photos of
# 28 July 1997 (자료 Q, frames 26/15 · 26/16: 56 points) have the dirt oval level at 32.75 m (0.4 m rms about a plane
# that tilts under 0.7 m in 100 m): 3.65 m under the junction on that road (36.4 m in the photos, 36.9 here), 10.7 m
# under the road north-east of it, 1.75 m over the 야구장.  The roadview of December 2010 from the junction
# (1016786888: people and a goal on the field 33 - 133 m off) has it 4.1 m under the road.  The photos' heights hang
# on the game's roads campus-wide (+-1 m) and the ground round the field stands 0.3 - 0.9 m over them here, so the
# field goes 3.7 m under the junction: 33.2 m.  OSM's outline (way 205583613) is the 1997 oval to 3 m.
# Round it one smooth surface (harmonic_fill) from the oval's edge out to what stays as it was (FIELD_PATCH): the road
# past its east end (4 m short of its middle), 22 m towards the 야구장, 성산로's north edge, 25 m of the hillside
# north-west and north.  학군단, at the oval's west end, on the field's level (the photos: 31.9 - 32.4 m beside it).
# Two OSM outlines at the oval's north end (a stand's building and a tower: the generic houses' loop below takes
# them) are not in the 1997 photos, which have trees there and one framework 8 x 10 m; the 2008 skyview has both.
# They go after the random planting (GONE_1997, without a site of their own: FIELD_GONE).
FIELD = dict(way=205583613, z=33.2, pad_z=32.6)
FIELD_POLY = Polygon([xy(p) for p in ways[FIELD['way']]['geometry']]).buffer(0)
FIELD_PAD = Polygon([(-523.9, -176.1), (-514.7, -166.8), (-493.5, -188.5), (-507.0, -201.0)]).buffer(4.0)   # (학군단: OLD_HALLS)
FIELD_PATCH = Polygon([(-400.0, -90.0), (-348.0, -90.0), (-332.0, -100.0), (-322.0, -118.0), (-313.0, -139.0),
                       (-307.0, -148.0), (-300.0, -157.0), (-299.0, -164.0), (-302.0, -176.0), (-305.0, -184.0),
                       (-309.0, -191.0), (-312.0, -198.0), (-321.0, -211.0), (-326.0, -226.0), (-338.0, -240.0),
                       (-388.0, -276.0), (-410.0, -288.0), (-432.0, -292.0), (-448.7, -280.7), (-506.7, -215.7),
                       (-540.0, -178.0), (-540.0, -165.0), (-518.0, -152.0), (-482.0, -159.0), (-422.7, -107.9)])
FIELD_GONE = (1494935780, 1441572669)
GONE_1997.update({k_: None for k_ in FIELD_GONE})
_fm = shapely.contains_xy(FIELD_POLY.buffer(2.0), X, Y)
_fpd = shapely.contains_xy(FIELD_PAD, X, Y) & ~_fm
_ff = shapely.contains_xy(FIELD_PATCH, X, Y) & ~_fm & ~_fpd
_f0 = float(Hn[_fm].mean())
Hn[_fm] = FIELD['z']
Hn[_fpd] = FIELD['pad_z']
harmonic_fill(_ff)
FIXED[_fm | _fpd] = True
print('대운동장: %.2f -> %.2f m (%d grid nodes), the ground round it eased over %d' % (_f0, FIELD['z'], int(_fm.sum()), int(_ff.sum())))


def near_buildings(pad):
    """Grid nodes within pad m of a campus building's footprint (whose own ground the fills must not move)."""
    m = np.zeros(X.shape, bool)
    for wid in B:
        if wid in ways:
            m |= shapely.contains_xy(footprint(ways[wid]).buffer(pad), X, Y)
    return m


# --- 중앙도서관 (reference/고증/3.2).  The 5 m grid drapes the slope behind it (and the bulk of the 학술정보원 built
# against its back in the 2000s) over the hall: the ground stood 6 m over the front plaza at its north-west corner, so
# the back and the north end were buried past the ground floor, and the forecourt lay 1.4 - 2.2 m under 백양로.
# The vertical aerial photos of 28 July 1997 (tools/aerial97.py, four frames) show the hall on a terrace 9.8 m deep
# along its 백양로 front and round both ends (8.6 m past them; a clipped shrub band 3.6 m deep at the wall's foot),
# a flight in its middle down to a paved plaza that runs out to 백양로, a walk along the shrub band, beds with a
# slant walk each, a walk along their far side.  Their heights (the photos' minus 0.4 m, what they read over the
# game's carriageway beside the hall): the walk at the terrace's foot nearly level, 34.4 m at the south end to 35.05 m
# at the north, 0.65 - 0.8 m over the carriageway by the door, while 백양로 climbs 2.9 m past it; the walk along the
# beds' far side at the sidewalk's height; the terrace's top 35.6 - 36.2 m (its edges' parallax between the frames).
# Frame: s along the front from the south-east corner, o out of it (east).
_lib = footprint(ways[163525865])
_lf0, _lf1 = np.array([-85.44, -71.08]), np.array([-65.91, 3.16])           # the 백양로 front, south -> north
_lfn = np.array([(_lf1 - _lf0)[1], -(_lf1 - _lf0)[0]]) / np.linalg.norm(_lf1 - _lf0)   # out of it (east)
_lfu = (_lf1 - _lf0) / np.linalg.norm(_lf1 - _lf0)
LIB_LEN = float(np.linalg.norm(_lf1 - _lf0))
LIB_ROAD_O = float(bline.distance(Point(*(_lf0 + _lfu * LIB_LEN / 2))))      # 백양로's centre line: parallel to the front


def LF(s, o):
    return tuple(float(c) for c in _lf0 + _lfu * s + _lfn * o)


def lf_rect(s0, s1, o0, o1):
    return Polygon([LF(s0, o0), LF(s1, o0), LF(s1, o1), LF(s0, o1)])


LIB97 = dict(
    depth=9.8, south=-8.6, north=LIB_LEN + 8.6,                # the terrace: out of the front, its two ends along it
    south_w=-44.5, north_w=-13.3,                             # how far west its end bands run (o)
    band=13.4,                                                # the shrub band at the wall's foot, out to here
    walk=21.0, outer=(41.6, 45.2),                            # the walk along the band; the walk along the beds' far side
    plaza=(LIB_LEN / 2 - 9.8, LIB_LEN / 2 + 9.4),             # the plaza before the flight (s), out to 백양로's sidewalk
    island=(LIB_LEN / 2 - 1.5, LIB_LEN / 2 + 0.1, 23.5, 43.0),  # the hedged island down its middle (s, s, o, o)
    beds=(-11.5, 82.4),                                       # the beds' south and north ends (the walk, the drive)
    slant_w=4.0, slant=[[(-9.2, 41.6), (29.1, 21.0)], [(85.6, 41.6), (47.3, 21.0)]],   # the slant walks' centre lines
    stair_w=18.8, risers=6, rise=0.93, tread=0.30,
)
LIB_FOOT = round(prof_h(s_at(*LF(LIB_LEN / 2, LIB_ROAD_O))) + 0.80, 2)      # the plaza at the flight's foot
LIB_FLOOR = round(LIB_FOOT + LIB97['rise'], 2)                             # the terrace, the arcade's floor
LIB_FOOT_SLOPE = 0.0075                                                    # the walk at its foot rises to the north
LIBRARY_LEVEL = float(np.mean([sample(Hn, NEAR_HALF, NEAR_STEP, *(_lf0 + (_lf1 - _lf0) * f + _lfn * 3.0))
                               for f in np.linspace(0.05, 0.95, 9)]))      # (the forecourt on the 5 m grid: for the print)
_LS = (X - _lf0[0]) * _lfu[0] + (Y - _lf0[1]) * _lfu[1]
_LO = (X - _lf0[0]) * _lfn[0] + (Y - _lf0[1]) * _lfn[1]
_lzf = LIB_FOOT + LIB_FOOT_SLOPE * (np.clip(_LS, -15.0, 92.0) - LIB_LEN / 2)
_loff = dist > ROAD_HALF + 4
_lin = shapely.contains_xy(_lib.buffer(6.0, join_style=2), X, Y)
_lse, _lne = LIB97['beds'][0] - 2.0, LIB97['beds'][1] + 8.0
# the ground at the terrace's foot (the terrace itself is the hall's own mesh: blender/landmarks.py library): along
# the front out to the beds, round the south end, round the north end as far as the terrace runs
_lfoot = (((_LS >= _lse) & (_LS <= _lne) & (_LO >= -1.0) & (_LO <= LIB97['walk'] + 1.0))
          | ((_LS >= _lse) & (_LS <= 2.0) & (_LO >= LIB97['south_w'] - 1.5) & (_LO <= LIB97['walk'] + 1.0))
          | ((_LS >= LIB_LEN - 2.0) & (_LS <= _lne) & (_LO >= LIB97['north_w'] - 1.0) & (_LO <= LIB97['walk'] + 1.0))
          | (_lin & (_LO > -38.0) & (_LS > -6.0) & (_LS < LIB_LEN + 6.0))) & _loff
_lback = _lin & ~_lfoot & _loff                      # behind and north-west: level with the floor, as before
# the walk along the beds' far side: at the sidewalk's height beside it
_lout = (_LS >= _lse) & (_LS <= _lne) & (_LO >= LIB97['outer'][0] - 0.5) & (_LO < LIB_ROAD_O) & _loff
Hn[_lfoot] = _lzf[_lfoot]
Hn[_lback] = LIB_FLOOR
Hn[_lout] = np.interp(_LS[_lout] + s_at(*LF(0.0, LIB_ROAD_O)), ss, prof) + 0.15
FIXED[_lfoot | _lback | _lout] = True
# (the beds between the two walks, and the ground out to 30 m on the other sides: one smooth surface)
_lring = ((shapely.contains_xy(_lib.buffer(30.0), X, Y) | ((_LS >= _lse) & (_LS <= _lne) & (_LO > 0) & (_LO < LIB97['outer'][0])))
          & ~FIXED & _loff & ~near_buildings(1.0))
harmonic_fill(_lring)
print('library: terrace %.2f, the flight\'s foot %.2f (백양로 beside it %.2f), the 5 m grid\'s forecourt %.2f'
      % (LIB_FLOOR, LIB_FOOT, LIB_FOOT - 0.80, LIBRARY_LEVEL))
# --- 독수리상: its precinct level out to the beds' kerb and a little beyond (the walks run out level from the ring),
# easing back into the lawn by 15 m (the 5 m grid had it falling 0.8 m to the west across the beds); not under
# 백양로's sidewalk
_er = np.hypot(X - EAGLE['pos'][0], Y - EAGLE['pos'][1])
_ew = np.clip((15.0 - _er) / 4.5, 0, 1) * np.clip((dist - (ROAD_HALF + 0.5)) / 2.0, 0, 1)
EAGLE_LEVEL = sample(Hn, NEAR_HALF, NEAR_STEP, *EAGLE['pos'])
Hn[:] = Hn * (1 - _ew) + EAGLE_LEVEL * _ew
FIXED[_ew > 0.999] = True
print('eagle precinct level', round(EAGLE_LEVEL, 2))


# --- 백주년기념관 앞 테라스 (reference/고증.md 3.4; Kakao roadview 2010-12 1016785999 · 1016786000 · 1016786002 ·
# 1016786003, 2008-08 2381242 · 2381245, headings and positions solved from the eagle, 활천대 and the hall's north-west
# corner).  From the paved apron behind the sidewalk's ginkgo row three granite flights climb to the museum porch,
# symmetric about its doors (s 21.9): six risers (five north of the doors' axis), a 5.4 m landing, five risers between
# two clipped-shrub planters, a 4.3 m landing, five risers between two more planters, then the porch's own level
# 9.7 m out from the face.  Risers 0.147 m (sixteen in all), so the foot is 2.35 m under the porch floor (museum_porch
# zf, kept): the apron falls from the sidewalk to the foot.  South of the flights a dressed granite retaining wall at
# the foot line (its coping at the first landing, lawn on it), north a low planter box on the apron and a planter wall
# beside the first landing.  The face frame: s along the 백양로 face from its north-west corner (south), d out of it.
_ct0 = np.array([-11.05, -181.26]) + BLD_MOVE[324328422]
CT_T = np.array([-28.82 + 11.05, -256.68 + 181.26]) / math.hypot(-28.82 + 11.05, -256.68 + 181.26)
CT_N = np.array([CT_T[1], -CT_T[0]])                         # out of the face (west, towards 백양로)


def ct_xy(s, d):
    return [round(float(v), 3) for v in _ct0 + CT_T * s + CT_N * d]


def ct_sidewalk(s, d=33.0):
    """the sidewalk's top (blender/road.py WZ) across from face s"""
    return prof_h(s_at(*ct_xy(s, d))) + 0.15


CTS = (X - _ct0[0]) * CT_T[0] + (Y - _ct0[1]) * CT_T[1]
CTD = (X - _ct0[0]) * CT_N[0] + (Y - _ct0[1]) * CT_N[1]
_ctr, _ctt = 0.147, 0.36
_ctp = corner_level(324328422) + 2.6                          # the porch floor (blender/landmarks.py museum_porch zf)
_ctl2 = _ctp - 5 * _ctr
_ctl1 = _ctl2 - 5 * _ctr
_ctf = _ctl1 - 6 * _ctr                                      # the foot (south of the doors' axis)
CT_FOOT_D, CT_MID_D, CT_UP_D = 24.0, 16.8, 11.1               # the first riser of each flight, m out of the face
CT_SC = 21.9                                                 # the doors' axis (CENT_MUSEUM s)
CENT_TERRACE = dict(
    o=[float(v) for v in _ct0], t=[round(float(v), 5) for v in CT_T], n=[round(float(v), 5) for v in CT_N],
    rise=_ctr, tread=_ctt, porch=round(_ctp, 3), l1=round(_ctl1, 3), l2=round(_ctl2, 3), foot=round(_ctf, 3),
    # flights: s range, d of the first riser, risers, the level at the foot; 'low' the s range of the lowest riser
    flights=[dict(name='lower', s0=8.8, s1=35.2, d0=CT_FOOT_D, n=6, z0=round(_ctf, 3), low=[CT_SC, 35.2]),
             dict(name='middle', s0=10.3, s1=35.2, d0=CT_MID_D, n=5, z0=round(_ctl1, 3)),
             dict(name='upper', s0=9.6, s1=35.2, d0=CT_UP_D, n=5, z0=round(_ctl2, 3))],
    # the planters on the middle and upper flights (s ranges), from the flight's foot to its head (a wedge narrowing
    # towards the doors: the upper ones stand 0.8 m nearer the axis)
    planters=[dict(f=1, s=[13.2, 15.6]), dict(f=1, s=[28.2, 30.6]), dict(f=2, s=[14.4, 16.2]), dict(f=2, s=[27.6, 29.4])],
    box=dict(s=[6.8, 8.8], d=[23.0, 25.5], h=0.6),             # the planter box on the apron at the north end
    bed=dict(s=[2.2, 10.3], d=[17.0, 22.0], h=round(_ctl2 - _ctl1 + 0.3, 3)),   # the planter wall beside the first landing
    wall=[dict(s0=35.2, s1=53.0, top=round(_ctl1 + 0.08, 3)), dict(s0=53.0, s1=70.0, top=round(_ctl1 - 0.3, 3))],
)
# the apron: sections every metre from the walk's outer edge (in front of the flights the planting strip gives way to
# paving and tree pits; elsewhere from the strip's back edge) to the foot line, falling to the foot's level (south of
# the flights the wall's foot, never over the sidewalk); (s, [[d, z] ...])
CT_PAVED_S = (2.0, 37.0)                                     # no planting strip: the ginkgos stand in pits
_ap = []
for _s in np.arange(2.0, 70.01, 1.0):
    _xy0 = ct_xy(_s, 33.0)
    _sr = s_at(*_xy0)
    _de = bline.distance(Point(*ct_xy(_s, 0.0)))                # the face's distance from 백양로's centre line
    _dout = _de - (E_WALK if CT_PAVED_S[0] <= _s <= CT_PAVED_S[1] else ROAD_HALF)
    _zs = prof_h(_sr) + 0.15
    if _s < 8.8:
        _din, _zf = CT_FOOT_D - _ctt, _ctf + _ctr
    elif _s <= 35.2:
        _din, _zf = CT_FOOT_D, (_ctf if _s >= CT_SC + 0.5 else _ctf + _ctr * float(np.clip(CT_SC + 0.5 - _s, 0, 1)))
    else:
        _din, _zf = CT_FOOT_D, min(_ctf, _zs)
    _ap.append([round(float(_s), 2), [[round(float(_dout), 3), round(_zs, 3)], [round(float(_dout) - 0.8, 3), round(_zs - 0.02, 3)],
                                      [round(_din, 3), round(_zf, 3)]]])
CENT_TERRACE['apron'] = _ap
# the ground under the apron and the flights below their surfaces; the lawns south and north of the flights on the
# first landing's level, rising towards the face (2010 roadview: from the wall's coping to the porch's level by the
# cylinder), easing back by the drum's foot
_cta = (CTS > 1.5) & (CTS < 70.5) & (CTD > 0.5) & (CTD < 36.0) & (dist > E_WALK + 0.1)
_ctzs = np.full(X.shape, np.nan)
for _s, _sec in _ap:
    _m = _cta & (np.abs(CTS - _s) <= 0.5) & (CTD >= _sec[2][0]) & (CTD <= _sec[0][0] + 2.0)
    _ctzs[_m] = np.interp(CTD[_m], [_sec[2][0], _sec[1][0], _sec[0][0]], [_sec[2][1], _sec[1][1], _sec[0][1]])
_m = ~np.isnan(_ctzs)
Hn[_m] = np.minimum(Hn[_m], _ctzs[_m] - 0.12)
FIXED[_m] = True
_cst = _cta & (CTS > 1.5) & (CTS < 36.0) & (CTD < CT_FOOT_D + 0.3) & (CTD > 0.5)       # the flights, landings, beds
_cst &= (CTS > 8.0) | (CTD > 16.5)
_ctzc = np.where(CTD > CT_MID_D + 2.0, _ctf, np.where(CTD > CT_UP_D + 2.0, _ctl1, np.where(CTD > 7.0, _ctl2, _ctp)))
Hn[_cst] = np.minimum(Hn[_cst], _ctzc[_cst] - 0.4)
FIXED[_cst] = True
_lw = lambda d_: _ctl1 + (_ctp - 0.3 - _ctl1) * np.clip((CT_FOOT_D - d_) / (CT_FOOT_D - 2.0), 0, 1)
# (on up to the face and in under the hall, whose walls go down past it, so the lawn meets them level; not under the
# drum's glazed foot)
_ls = (CTS >= 36.0) & (CTS < 66.0) & (CTD < CT_FOOT_D - 0.4) & ((CTD > 0.5) | ((CTD > -6.0) & (CTS < 50.0)))
_lsw = np.clip((60.0 - CTS) / 8.0, 0, 1)
Hn[_ls] = Hn[_ls] * (1 - _lsw[_ls]) + _lw(CTD[_ls]) * _lsw[_ls]
FIXED[_ls] = True
_ln = (CTS > 1.5) & (CTS < 8.0) & (CTD < 16.5) & (CTD > -6.0)                           # (behind the bed)
Hn[_ln] = _ctl1 + 0.5 + (_ctl2 - _ctl1 - 0.5) * np.clip((16.5 - CTD[_ln]) / 14.5, 0, 1)
FIXED[_ln] = True
print('백주년기념관 앞 테라스: foot %.2f, landings %.2f / %.2f, porch %.2f (sidewalk %.2f .. %.2f)' % (
    _ctf, _ctl1, _ctl2, _ctp, ct_sidewalk(35.0), ct_sidewalk(8.8)))


# --- 백양로 끝 계단 (reference/고증.md 3.18; 2003_봄_언더우드관정원_남쪽계단_벚나무.jpg, Kakao roadview 2008-08 /
# 2010-12 / 2011-04 / 2026, Kakao skyview).  백양로 ended at the 삼거리 at the foot of a bank, where the drives to 핀슨관 (west)
# and 노천극장 (east) branch off; the steps go up the bank from the road to the paved square before 언더우드관 정원,
# 4.0 m higher: three tiers of two granite flights either side of a lawn strip down the axis (eight, eight and six
# risers of 0.18), a deep landing and a shorter one between them, the strip a broad bed with the crest tablet between
# the lowest flights, narrowing above, and grass banks either side set with rows of clipped round shrubs.  The skyview
# puts the foot at the road's edge (33.0, 134.8) and the head on the square 18.6 m on along the axis (bearing 11 deg),
# about 10.6 m across the walls; the roadview shows the same flights, tablet and white poplar in 2008, 2010 and 2026
# (the 2013-15 rebuilding stopped short of them).  The game had 백양로 run on 40 m to the garden's south edge and the steps
# (two short tiers) there: that end of the road is no longer drawn (BY_END_S), the square sits at the head of the
# steps, the garden falls from it to 언더우드관's front (GARDEN_FILL below).  blender/landmarks.py underwood_steps builds
# them (UW_STEPS).
_wuo = np.array([62.0, 213.0])
_wuu = np.array([0.970, -0.243]) / math.hypot(0.970, -0.243)
_wuv = np.array([-_wuu[1], _wuu[0]])                         # (WU below: u across the garden, v up its axis)


def wu_xy(u, v):
    return tuple(float(c) for c in _wuo + _wuu * u + _wuv * v)


# 언더우드 동상과 정원 (reference/고증.md 4.2).  The statue stands at the hub of eight radial walks on the axis from
# 언더우드관's tower: the 1994 aerial photo puts the parterre's centre on that axis (1.6 +- 1.5 m east of the normal to
# the front) 59 +- 5 m out from the front, the 2010 roadview (three garden panoramas, headings free) at (50.4, 196.5)
# +- (2.4, 1.7), the skyview's round platform at (49.8, 198.2) -- the same place, which is taken.  WU's axis (the
# frame the game had) ran 8.5 m east of it, the statue 26 m out from WU's origin.  UWG: u across the garden (as WU),
# v up the axis towards the tower, o the statue.  The parterre: beds between the radial walks out to u +-21, v -24 ..
# +20, a cross walk at v 22.5 to the side halls' doors, two half-round beds beyond it either side of the axis walk,
# paved walks along the side halls and before 언더우드관; the south edge a hedge at v -27.4.
UW_STATUE = (49.8, 198.2)
_ugo = np.array(UW_STATUE)


def uwg_xy(u, v):
    return tuple(float(c) for c in _ugo + _wuu * u + _wuv * v)


UW_GARDEN = Polygon([uwg_xy(-28.0, -28.5), uwg_xy(28.0, -28.5), uwg_xy(28.0, 46.0), uwg_xy(-28.0, 46.0)])
UW_RING, UW_WALK_W = 6.3, 2.6           # the gravel ring round the platform (outer radius), the radial walks' width


def underwood_beds():
    """The beds of 언더우드관 정원 (UWG): the eight between the radial walks, inside the parterre (u +-21, v -24 ..
    +20.5) and outside the ring round the statue's platform, and the two half-round ones beyond the cross walk
    either side of the axis walk."""
    G = lambda pts: Polygon([uwg_xy(u, v) for u, v in pts])
    sq = G([(-21.0, -24.0), (21.0, -24.0), (21.0, 20.5), (-21.0, 20.5)])
    walks = [Point(*UW_STATUE).buffer(UW_RING + 0.4)]
    for k in range(8):
        a = math.radians(45 * k)
        walks.append(LineString([UW_STATUE, uwg_xy(40 * math.sin(a), 40 * math.cos(a))]).buffer(UW_WALK_W / 2 + 0.4))
    radial = sq.difference(unary_union(walks))
    half = []
    for sg in (-1, 1):
        box_ = G([(sg * 2.2, 25.0), (sg * 14.2, 25.0), (sg * 14.2, 31.0), (sg * 2.2, 31.0)])
        cap = Point(*uwg_xy(sg * 8.2, 31.0)).buffer(6.0).intersection(G([(sg * 2.2, 31.0), (sg * 14.2, 31.0),
                                                                         (sg * 14.2, 40.0), (sg * 2.2, 40.0)]))
        half.append(box_.union(cap))
    return dict(radial=list(radial.geoms) if hasattr(radial, 'geoms') else [radial], half=half)


_sto = np.array([33.0, 134.8])                               # the middle of the foot, at the road's edge
_stv = np.array([math.sin(math.radians(11.0)), math.cos(math.radians(11.0))])    # up the axis
_stu = np.array([_stv[1], -_stv[0]])                         # across it, east


def st_xy(u, v):
    return tuple(float(c) for c in _sto + _stu * u + _stv * v)


STU = (X - _sto[0]) * _stu[0] + (Y - _sto[1]) * _stu[1]
STV = (X - _sto[0]) * _stv[0] + (Y - _sto[1]) * _stv[1]
_H0 = sample(Hn, NEAR_HALF, NEAR_STEP, *st_xy(0.0, -3.0))     # the 삼거리 before the foot (백양로's section)
# tiers: (v of the foot, risers, half width of the lawn strip between the inner cheeks, width of each flight); the
# flights rise onto landings 5.6 and 2.9 m deep and the head landing (treads 0.42, cheeks 0.35)
_TI = [(0.0, 8, 1.0, 3.6), (8.96, 8, 0.6, 3.8), (15.22, 6, 0.4, 3.7)]
# (the risers 0.18: the vertical aerial photos of 1997 have the square 4.0 +- 0.3 m over the road at the foot, 45.0 -
# 45.3 over 41.1 m, and in the 2003 photo the nosings stand 0.16 - 0.18 m apart by the people on the flights; 0.15 was
# a guess, reference/고증/2.8)
UW_STEPS = dict(rise=0.18, tread=0.42, cheek=0.35, h0=round(_H0, 2), v_head=18.6,
                frame=dict(o=[float(c) for c in _sto], u=[round(float(c), 5) for c in _stu], v=[round(float(c), 5) for c in _stv]))
_US = UW_STEPS
_zt, _tiers, _flights = _H0, [], []
for _k, (_v0, _n, _shw, _fw) in enumerate(_TI):
    _v1 = _v0 + _n * _US['tread']                              # the flight's head (where its landing starts)
    _z1 = _zt + _n * _US['rise']
    _uc = _shw + _US['cheek'] + _fw / 2
    _tiers.append(dict(v0=_v0, v1=round(_v1, 2), z0=round(_zt, 2), z1=round(_z1, 2), strip=_shw,
                       outer=round(_shw + 2 * _US['cheek'] + _fw, 2)))
    for _sg in (-1, 1):
        _flights.append(dict(name='uw_%d%s' % (_k, 'w' if _sg < 0 else 'e'), top=[round(c, 2) for c in st_xy(_sg * _uc, _v1 + 0.3)],
                             down=[round(-float(_stv[0]), 4), round(-float(_stv[1]), 4)],
                             foot=[round(c, 2) for c in st_xy(_sg * _uc, _v0)], z_top=round(_z1, 2), z_foot=round(_zt, 2),
                             n=_n, width=_fw, landing=0.3, tread=_US['tread'], cheek=_US['cheek']))
    _zt = _z1
_US.update(tiers=_tiers, flights=_flights, top=round(_zt, 2))
_US['landings'] = [dict(v0=_tiers[k]['v1'], v1=(_tiers[k + 1]['v0'] if k + 1 < len(_tiers) else _US['v_head']),
                        z=_tiers[k]['z1'], outer=max(_tiers[k]['outer'], _tiers[k + 1]['outer'] if k + 1 < len(_tiers) else 0),
                        strip=(_tiers[k]['strip'], _tiers[k + 1]['strip'] if k + 1 < len(_tiers) else _tiers[k]['strip']))
                   for k in range(len(_tiers))]
UW_TOP = _US['top']
# the banks either side, a straight grade from the road's edge to the head, fading into the ground beyond 18 - 26 m
# across (the drives to 핀슨관 and 노천극장 climb round their ends); the square at the head level, from the banks' top
# to the garden; the ground under the flights and landings below their treads
_reg = (np.abs(STU) < 26.0) & (STV > -0.6) & (STV < _US['v_head']) & ~near_buildings(1.5)
_tb = np.clip(STV[_reg] / _US['v_head'], 0.0, 1.0)
_wl = 1 - _smooth((np.abs(STU[_reg]) - 18.0) / 8.0)
Hn[_reg] += _wl * (_H0 + (UW_TOP - _H0) * _tb - Hn[_reg])
FIXED[_reg & (np.abs(STU) < 18.0)] = True
UW_SQUARE = Polygon([st_xy(-28.0, _US['v_head']), st_xy(34.0, _US['v_head']), (84.0, 170.0), (84.0, 176.0), (27.0, 190.0),
                     (8.0, 184.0)])
# (the garden reaches the square's north side: the square stops at its south edge, and west of it at the walk along
# 스팀슨관; east of the garden it runs on to the drive towards 노천극장 as before)
UW_SQUARE = UW_SQUARE.difference(Polygon([uwg_xy(-45.0, -28.5), uwg_xy(28.0, -28.5), uwg_xy(28.0, 60.0), uwg_xy(-45.0, 60.0)]))
_sq = shapely.contains_xy(UW_SQUARE, X, Y) & ~near_buildings(1.5)
Hn[_sq] = UW_TOP
FIXED[_sq] = True
_stp = np.hypot(X - UW_STATUE[0], Y - UW_STATUE[1]) < 6.0     # the Underwood statue in the garden, its round steps level
# (the aerial photos of 1997: the ring round the statue 45.6 - 45.9 m, 0.6 m over the square, itself 45.0 - 45.3;
# level to the eye, as the 2010 roadview has it)
UW_STATUE_Z = round(UW_TOP + 0.9, 2)
Hn[_stp] = UW_STATUE_Z
FIXED[_stp] = True
_zc = np.full(X.shape, _H0)
for _t in _tiers:
    _zc = np.where(STV > _t['v0'], _t['z0'] + (_t['z1'] - _t['z0']) * np.clip((STV - _t['v0']) / (_t['v1'] - _t['v0']), 0, 1), _zc)
_sz = (np.abs(STU) < 5.8) & (STV > -0.5) & (STV < _US['v_head'] + 0.2)
Hn[_sz] = np.minimum(Hn[_sz], _zc[_sz] - 0.7)                 # (low enough for the 5 m chords to clear)
FIXED[_sz] = True
print('백양로 끝 계단: road %.2f, landings %s, square %.2f m' % (_H0, [l_['z'] for l_ in _US['landings'][:2]], UW_TOP))
BY_END_S = round(float(bline.project(Point(*st_xy(0.0, -1.0)))), 1)     # 백양로 is drawn to here (1 m before the foot)
UW_BANK = Polygon([st_xy(-26.0, -0.4), st_xy(26.0, -0.4), st_xy(26.0, _US['v_head']), st_xy(-26.0, _US['v_head'])])
# (the paved head of the steps: from the banks' top across the walk in front of the garden, OSM's drive along it 5 m on)
UW_HEAD = UW_SQUARE.intersection(Polygon([st_xy(-30.0, _US['v_head'] - 0.1), st_xy(36.0, _US['v_head'] - 0.1),
                                          st_xy(36.0, 29.0), st_xy(-30.0, 29.0)]))
# along the head (UW_STEPS u): the benches, the recycling box and the pair of 해태 (props below; the 2003 photos)
UW_HEAD_BENCHES = (8.6, 12.8, 17.6, 21.4, -10.8, -14.0, -16.6)
UW_HEAD_BIN = 15.85
UW_HAETAE = (-5.45, 5.45)
# (in a row along the square's edge at the head line, their backs to the banks)
UW_HEAD_ROW = Polygon([st_xy(-30.0, _US['v_head'] - 1.0), st_xy(36.0, _US['v_head'] - 1.0), st_xy(36.0, _US['v_head'] + 1.0),
                       st_xy(-30.0, _US['v_head'] + 1.0)])


# --- 언더우드관 앞 정원 (issue #3).  The level aprons of 스팀슨관 (51.6 m) and 아펜젤러관 (54.3 m) face each other across
# the garden, but the 5 m grid keeps a hollow down its middle (49.4 m): each apron ended in a grass bank, 5 m over 18 m
# in front of 아펜젤러관, where the photos (reference/아펜젤러관_정면_2016.jpg, 언더우드관_2024_여름_계단에서_본_정원.jpg) show
# the garden walks running nearly level to the foot of the steps.  Fill the garden between the aprons, the foot of
# 언더우드관's flight and the statue with one smooth surface: the 2.7 m between the aprons becomes an even fall across
# the garden, the hollow goes.  Kept as they are: the aprons, 언더우드관's front (its flight is measured from it) and
# the ground under the Underwood statue (statues.underwood_statue.h).  (With the garden as it was laid out before
# the statue moved, UW_GARDEN above: its south part was the square's.)
GARDEN_FILL = Polygon([(27, 190), (84, 176), (84, 243), (44, 249)]).union(UW_GARDEN)
# The garden's west edge south of 스팀슨관 stands over the walk along that hall (the 5 m grid's hollow there): a
# short flight comes up from it (below).  Keep the edge at the square's and the apron's level, the ground falling
# to the walk outside it.
_uwe = shapely.contains_xy(Polygon([uwg_xy(-23.5, -28.5), uwg_xy(-18.5, -28.5), uwg_xy(-18.5, 4.0), uwg_xy(-23.5, 4.0)]), X, Y)
_uwe &= ~FIXED & ~near_buildings(1.5)
_uwa = sample(Hn, NEAR_HALF, NEAR_STEP, *uwg_xy(-25.0, 12.0))      # 스팀슨관's apron
Hn[_uwe] = UW_TOP + (_uwa - UW_TOP) * np.clip((((X - _ugo[0]) * _wuv[0] + (Y - _ugo[1]) * _wuv[1])[_uwe] + 28.5) / 32.5, 0, 1)
FIXED[_uwe] = True
_free = shapely.contains_xy(GARDEN_FILL, X, Y) & ~FIXED & ~near_buildings(1.5)
_free &= np.hypot(X - UW_STATUE[0], Y - UW_STATUE[1]) > 6.0   # the statue on its round steps
harmonic_fill(_free)
# The drive along 스팀슨관's front outside that edge stays six risers under it, as the surface model's hollow had it and
# the garden's south-west flight was laid (below).  The aerial photos of 1997 raise the ground all round (HILL_Q) and
# have this drive 45.8 - 46.4 m, 0.6 - 0.9 m OVER the garden's walks beside it: the flight would go down into the
# garden, not up.  Not turned round on the photos alone (the 2008 and 2010 roadview were read as a flight up into the
# garden): reference/고증/4.2 「남은 한계」.
_uvg = ((X - _ugo[0]) * _wuu[0] + (Y - _ugo[1]) * _wuu[1], (X - _ugo[0]) * _wuv[0] + (Y - _ugo[1]) * _wuv[1])
_uww = (_uvg[0] > -36.0) & (_uvg[0] < -24.0) & (_uvg[1] > -28.5) & (_uvg[1] < 6.0) & ~FIXED & ~near_buildings(1.5)
Hn[_uww] = np.minimum(Hn[_uww], UW_TOP + (_uwa - UW_TOP) * np.clip((_uvg[1][_uww] + 28.5) / 32.5, 0, 1) - 6 * 0.17)


def fix_strip(line_pts, h0, h1, half, top=False):
    """Grid nodes within half m of a polyline (not past its ends) get a straight grade from h0 to h1 along it.
    top: only lower them to it (the ground under a flight must stay below its treads)."""
    ls = LineString(line_pts)
    m = shapely.contains_xy(ls.buffer(half, cap_style='flat'), X, Y)
    z = h0 + (h1 - h0) * shapely.line_locate_point(ls, shapely.points(X[m], Y[m])) / ls.length
    Hn[m] = np.minimum(Hn[m], z) if top else z
    FIXED[m] = True
    return m


# the drive from the 삼거리 towards 노천극장 (OSM) climbs past the east end of the bank to the square's level, where it
# meets the walk in front of the garden (roadview 2010: the square, the drive and the walk at one level there)
_ed = [(51.5, 126.5), (63.3, 139.8), (69.1, 146.2)]
# (the aerial photos of 1997 have 44.1 m on it 28 m from 백양로's middle, 3.7 m over the 삼거리: it climbs the bank
# from the kerb.  One grade from 1.0 m over the road at its first node, 42.7 m there: steeper and the cars pitch
# over 9 deg at the mouth)
fix_strip(_ed, prof_h(s_at(*_ed[0])) + 1.0, UW_TOP, 4.0)
_ed0 = (41.0, 123.3)                                          # (its mouth, from the back of 백양로's sidewalk)
fix_strip([_ed0, _ed[0]], prof_h(s_at(*_ed0)), prof_h(s_at(*_ed[0])) + 1.0, 4.0)

# 외솔관2's sides (OESOL_LEVEL above): the passage to 종합관 (north, 5.5 - 6.6 m wide) and the gap to 인문관 (south,
# ~7.6 m) fall from the car park's level at the west end to the ground at the east end, a storey lower
OESOL_PASSAGES = [[(-90.46, 295.16), (-44.09, 283.35)], [(-95.1, 276.2), (-52.8, 265.8)]]
for _ln, _hw in zip(OESOL_PASSAGES, (3.0, 3.5)):
    fix_strip(_ln, OESOL_LEVEL, sample(Hn, NEAR_HALF, NEAR_STEP, *_ln[1]), _hw)
# The service road through the car park (OSM 444854948 · 444854949) stood on the same surface model, 8 - 10 m over
# the car park north-east of it along 종합관 (roadview 2026 from it, pano 1212397616: the road falls gently east and
# 종합관's north wing shows four storeys over it; the game had two).  Graded from the car park (where the roadview's
# lens stands 1.2 m over the block's west end) to its own ends, which stay: east the junction at the head of the
# steps down to 교육관, south-west up the hill.  The ground between the road, the car park and the halls, and a 15 m
# band of the woods north of the road: one smooth surface down to it.
OESOL_ROAD = [[(-103.6, 307.7), (-88.0, 318.1), (-81.6, 321.9), (-52.8, 328.0), (-40.9, 329.5), (-35.1, 329.1),
               (-6.8, 322.1), (-0.7, 321.7)], [(-103.6, 307.7), (-129.6, 290.3), (-151.1, 218.7)]]
_ocp = OESOL_LEVEL + 1.2
for _ln in OESOL_ROAD:
    fix_strip(_ln, _ocp, sample(Hn, NEAR_HALF, NEAR_STEP, *_ln[-1]), 3.5)
_oreg = unary_union([LineString(_ln).buffer(16.0) for _ln in OESOL_ROAD] +
                    [Polygon([(-126.0, 262.0), (-60.0, 262.0), (-48.0, 290.0), (-80.0, 322.0), (-126.0, 300.0)])]) \
    .intersection(Polygon([(-200.0, 150.0), (-8.0, 150.0), (-8.0, 400.0), (-200.0, 400.0)]))   # (not the junction east)
_free = shapely.contains_xy(_oreg, X, Y) & ~FIXED & (dist > ROAD_HALF + 4)
harmonic_fill(_free)
print('외솔관2: car park %.2f (road %.2f), east end %.2f m, %d nodes filled' % (OESOL_LEVEL, _ocp, corner_level(246156114),
                                                                         int(_free.sum())))


# --- 연희관 앞 정원: between 언더우드관's back and 연희관 (OSM; reference/연희관_정면_2023.jpg, 학교연혁_연희관.jpg from
# its south walk, 대우관_블로그_연희관과_대우관_원경.jpg from above to the west, the 1995 map's star-shaped garden).
# A diamond of walks round a round planter, a cross of walks through it, four beds edged with clipped boxwood.  It is
# a terrace rising some 3 % northwards, ten risers over 한경길 at its south end; to the north a planted bank with a
# broad flight between low walls (OSM 10 m) climbs to the road before 연희관, whose entrance flight (seventeen risers,
# no landing) rises from the road between the wings.  West and east, the ways in from the drives along 교육관 and
# 성암관 are a landing between low coped cheeks and one step down; along 한경길 a rubble retaining wall with boxwood
# on it (YH_WALL below).  The 5 m grid had one 30 % slope from 한경길 to the door.  The heights are the vertical
# aerial photos' of 1997-07-28 (자료 Q; reference/고증/3.5.1 「1997년 7월 항공사진으로 잰 높이」; tools/aerial97.py z,
# each from five to fifteen frame pairs within 0.2 m): 한경길 52.5 - 53.1 m all the way from the drive along 교육관 to
# the one along 성암관, the garden 54.0 (the S node) .. 55.1 (the N node), the road before 연희관 58.1 - 58.6 from end
# to end; the hall's eaves at 73.65 m put its door (12.6 m under them) at 61.0.  The risers counted in the roadview
# fit them:
#  - the south flight: ten granite risers between the rubble retaining walls along 한경길 (counted in Kakao roadview,
#    2008-08 and 2026-06: the same blocks; the photos: 1.4 m)
#  - the slope: the photos' 1.1 m from the S node to the N node (3.2 %; the planter's ground 0.7 m over the S node)
#  - the north flight: the photos' 3.3 m from the garden to the road, twenty-one risers of 0.16 (the 2008 roadview from
#    the drive along 교육관 shows twenty-odd treads from the side)
#  - 연희관's entrance: seventeen risers of 0.15 in one flight (roadview from the road before it, 2026)
# (Before: the garden on 한경길 as the surface model had it and 8 % up from a roadview camera's tilt, the road 7 m
# over the garden's side ways in, where photo A's camera had put the hall: a north flight of thirty risers.)
YH_DIAMOND = [(74.4, 302.5), (52.7, 325.4), (82.5, 335.4), (103.4, 312.1)]      # S, W, N, E nodes of the walks
YH_C = (78.4, 318.3)                                                            # the round planter (GF_C)
# 한경길 by the photos: (x, height) along it.  East of the drive along 성암관 it runs on to the road to 노천극장, where
# the photos (53.0 - 54.2 m) stand 2 - 4 m under the game: left as it was from x 113 on (고증 2.8 「남은 한계」)
HANGYEONG_Q = [(34.0, 52.4), (40.3, 52.5), (72.5, 52.7), (92.0, 52.9), (106.0, 52.6), (113.0, 52.7)]
HANGYEONG_LINES = ([(154.1, 270.8), (149.3, 272.5), (105.3, 286.1), (72.5, 295.2), (52.5, 300.2), (40.3, 301.6)],
                   [(40.3, 301.6), (52.2, 296.6), (71.4, 290.9), (104.1, 281.3), (147.7, 268.6)])
for _ln in HANGYEONG_LINES:
    _m = shapely.contains_xy(LineString(_ln).buffer(3.5, cap_style='flat'), X, Y)
    _w = _smooth((X[_m] - 113.0) / 22.0)                      # (back to the ground as it was by x 135)
    Hn[_m] = np.interp(X[_m], [q_[0] for q_ in HANGYEONG_Q], [q_[1] for q_ in HANGYEONG_Q]) * (1 - _w) + Hn[_m] * _w
    FIXED[_m] = True
hk_z = lambda x_: float(np.interp(x_, [q_[0] for q_ in HANGYEONG_Q], [q_[1] for q_ in HANGYEONG_Q]))
_zh = hk_z(73.1)                                                                # 한경길 at the foot of the S flight
YEONHUI = dict(garden=round(_zh + 10 * 0.15, 2), slope=0.032, planter=dict(c=list(YH_C), r=3.2, h=0.5))


def yh_plane(e, n):
    return YEONHUI['garden'] + YEONHUI['slope'] * (n + 16.3)          # (n = -16.3 at the S node)


def g_en(x, y):
    d_ = np.array([x, y]) - GF_C
    return float(d_ @ GF_E), float(d_ @ GF_N)


def flight_at(name, top, down, z_top, z_foot, width, landing=0.6, tread=0.30, maxrise=0.165, **kw):
    d_ = np.array(down, float) / np.linalg.norm(down)
    n_ = int(math.ceil((z_top - z_foot) / maxrise - 0.1))      # (a centimetre over whole risers, from rounding, adds none)
    foot = np.array(top) + d_ * (landing + n_ * tread)
    return dict(name=name, top=[round(float(top[0]), 2), round(float(top[1]), 2)], down=[round(float(d_[0]), 4), round(float(d_[1]), 4)],
                foot=[round(float(foot[0]), 2), round(float(foot[1]), 2)], z_top=round(float(z_top), 2), z_foot=round(float(z_foot), 2),
                n=n_, width=width, landing=landing, tread=tread, **kw)


# 언더우드관 정원 서남쪽의 작은 계단 (reference/고증.md 4.2; Kakao roadview 2008-08 from the drive along 스팀슨관, 2010-12
# from its foot, the skyview's pale landing and OSM's stub of walk there): a short walled flight from the walk along
# 스팀슨관 up into the garden (five or six risers).  blender/landmarks.py underwood_steps builds it.
_ugt = np.array(uwg_xy(-23.6, -20.6))
_ugz = sample(Hn, NEAR_HALF, NEAR_STEP, *uwg_xy(-22.6, -20.6))
_ugz = (_ugz, _ugz - 6 * 0.17 + 0.01)      # (six risers, as the ground had it before the photos' heights: _uww above)
UW_STEPS['garden'] = [flight_at('uw_garden_sw', _ugt, -_wuu, _ugz[0], _ugz[1], 3.0, landing=0.5,
                                maxrise=0.17, cheek=0.35)]
for _f in UW_STEPS['garden']:              # (the ground under it below its treads, the walk at its foot at its level)
    fix_strip([_f['top'], _f['foot']], _f['z_top'] - 0.2, _f['z_foot'], 2.3, top=True)
print('언더우드관 정원 서남쪽 계단', _ugz, [(f_['n'], f_['z_top'], f_['z_foot']) for f_ in UW_STEPS['garden']])


# the north flight: from the road's south edge on the OSM line down onto the garden's axis walk, twenty-one risers of
# 0.16 (the vertical aerial photos: the road 58.4 - 58.5 m on the axis, the garden 55.1 at its foot)
YH_NORTH_N = 21
_un = np.array([85.2 - 82.5, 345.0 - 335.4]) / math.hypot(85.2 - 82.5, 345.0 - 335.4)
_tn = np.array([85.2, 345.0]) - _un * 3.0
_fn = _tn - _un * (0.6 + YH_NORTH_N * 0.31)
YEONHUI['road'] = round(yh_plane(*g_en(*_fn)) + YH_NORTH_N * 0.16, 2)   # the road before 연희관, on the axis
for _ in range(3):                                            # (the foot moves with the number of risers)
    _zfn = yh_plane(*g_en(*_fn))
    _fn = _tn - _un * (0.6 + math.ceil((YEONHUI['road'] - _zfn) / 0.16 - 1e-6) * 0.31)
_zfn = yh_plane(*g_en(*_fn))
YEONHUI['floor'] = round(YEONHUI['road'] + 17 * 0.15, 2)      # 연희관's door (blender: gothic z_floor), 17 risers up
YEONHUI['hall'] = dict(a=list(YH_HALL_A), b=list(YH_HALL_B), **{k_: list(v_) for k_, v_ in YH_HALL.items()})   # (BLD_SHAPE)
# (the road all but level in the photos, 58.1 - 58.6 m from end to end: it fell 2.8 m eastwards)
_rw, _rc, _re = YEONHUI['road'] - 0.2, YEONHUI['road'], YEONHUI['road']             # the road's west end, axis, east end
_hw0, _he0 = hk_z(40.3), hk_z(106.6)                          # 한경길 where the west drive leaves it, and the east one
_FRONT_RD = [(51.7, 354.5), (85.2, 345.0), (118.8, 335.6)]
_W_RD = [(40.3, 301.6), (40.7, 306.0), (41.7, 310.2), (45.5, 327.4), (51.7, 354.5)]
_E_RD = [(106.6, 289.8), (111.9, 310.1), (118.8, 335.6)]
fix_strip(_FRONT_RD[:2], _rw, _rc, 3.5)
fix_strip(_FRONT_RD[1:], _rc, _re, 3.5)
_wrd, _erd = LineString(_W_RD), LineString(_E_RD)
# the side drives pass the garden's west and east corners at the garden's level: in the August 2008 roadview from the
# drive along 교육관 (2381720, 2381722) the way in is a landing between low coped cheek walls at the drive's edge and
# one step on to the garden's walk, and the drive from 한경길 up to it is all but level (its edges vanish at the
# horizon); the one from the drive along 성암관 has the same coped cheeks (2026), and in 2008 (2381704) the rubble wall
# under the garden's edge has run out by it.  So each drive climbs from 한경길 to one riser over the garden at its
# way in, and on from there to the road before 연희관 (before: one grade from 한경길 to the road, which stood the
# ways in 3.2 m and 1.7 m over the garden, flights of twenty and eleven risers)
_dw = np.array([52.7 - 45.5, 325.4 - 327.4]); _dw /= np.linalg.norm(_dw)
_tw = np.array([45.5, 327.4]) + _dw * 3.0
_de = np.array([103.4 - 111.9, 312.1 - 310.1]); _de /= np.linalg.norm(_de)
_te = np.array([111.9, 310.1]) + _de * 3.0
YH_RISE1 = 0.15


def _yh_side_drive(line, top, down, z_mouth, z_road):
    """grade a side drive in two pieces about the point by its way into the garden; returns that point's height
    and the drive's grade as (s along it, z) knots"""
    s_ = line.project(Point(*top))
    z_in = yh_plane(*g_en(*(np.array(top) + down * (0.5 + 0.30)))) + YH_RISE1      # (the foot of a one-riser flight)
    fix_strip(list(substring(line, 0.0, s_).coords), z_mouth, z_in, 3.5)
    fix_strip(list(substring(line, s_, line.length).coords), z_in, z_road, 3.5)
    return float(z_in), ([0.0, s_, line.length], [z_mouth, float(z_in), z_road])


_zw, _gw = _yh_side_drive(_wrd, _tw, _dw, _hw0, _rw)
_zeo, _ge = _yh_side_drive(_erd, _te, _de, _he0, _re)
# the garden terrace, its walks and a metre beyond
_gd = shapely.contains_xy(Polygon(YH_DIAMOND).buffer(2.0), X, Y)
Hn[_gd] = yh_plane(GE[_gd], GN[_gd])
FIXED[_gd] = True
# the court between 연희관's wings: from the foot of its walls (the floor less the 1.2 m plinth) down to the road
_ya, _yb = np.array(YH_HALL_A), np.array(YH_HALL_B)
_yt = (_yb - _ya) / np.linalg.norm(_yb - _ya)
_yn = np.array([-_yt[1], _yt[0]])
YH_U = (X - _ya[0]) * _yt[0] + (Y - _ya[1]) * _yt[1]
YH_V = (X - _ya[0]) * _yn[0] + (Y - _ya[1]) * _yn[1]
_ct = (YH_U > -14.5) & (YH_U < 52.5) & (YH_V > -10.6) & (YH_V < -0.8) & ~near_buildings(0.3)
_rd_u = np.interp(YH_U[_ct], [float((np.array(p_) - _ya) @ _yt) for p_ in _FRONT_RD], [_rw, _rc, _re])   # (its grade)
Hn[_ct] = (YEONHUI['floor'] - 1.2) + (_rd_u - (YEONHUI['floor'] - 1.2)) * np.clip(-YH_V[_ct] / 10.5, 0, 1)
FIXED[_ct] = True
# the flights (blender/landmarks.py yeonhui_garden builds them from these)
_ds = np.array([73.1 - 74.4, 297.5 - 302.5]); _ds /= np.linalg.norm(_ds)
YEONHUI['flights'] = [
    flight_at('north', _tn, -_un, YEONHUI['road'], _zfn, 5.0, landing=0.6, tread=0.31, maxrise=0.16, cheek=0.4),
    flight_at('south', YH_DIAMOND[0], _ds, yh_plane(*g_en(*YH_DIAMOND[0])), _zh, 4.0, landing=0.5, maxrise=0.15, cheek=0.35,
              plain=True),
]
_fw = flight_at('west', _tw, _dw, _zw, _zw - YH_RISE1, 3.2, landing=0.5, cheek=0.35, maxrise=0.16)      # (one riser:
_fe = flight_at('east', _te, _de, _zeo, _zeo - YH_RISE1, 3.2, landing=0.5, cheek=0.35, maxrise=0.16)     # _yh_side_drive)
YEONHUI['flights'] += [_fw, _fe]
# the rubble retaining wall under the garden's south edge (Kakao roadview 2008-08 2381704 · 2381709 · 2381711 and
# 2010-12 1016786644 · 1016786645 · 1016786650 from 한경길): uncoursed brown-grey rubble with no coping, standing
# at the road's edge from the drive along 교육관 round to the one along 성암관, the south flight going up through a
# gap in it with the wall's own rubble for its sides; on top, all along, a bank of clipped boxwood in big mounds.
# Over the road it stands about 0.7 m at the west drive, 0.75 m beside the flight (four or five of its ten risers)
# and 1.1 m at the east drive (over a parked car's roof from the roadview camera); up the two drives it runs out as the
# drive climbs (_yh_up_drive).  The lawn behind it is held at its top (the 5 m grid's nodes in a band behind
# it), the rest of the lawns down from the garden filling in between
YH_WALL_OFF = 3.6                                            # wall face from the road's centre line, m
_hk = LineString([(112.0, 284.1), (105.3, 286.1), (72.5, 295.2), (52.5, 300.2), (40.3, 301.6), (34.0, 302.3)])


def _yh_offset(line, d):
    """line offset d m to the garden's side (north of 한경길, east of the 교육관 drive, west of the 성암관 one)"""
    a_, b_ = line.offset_curve(d), line.offset_curve(-d)
    c_ = Point(*YH_C)
    return a_ if a_.distance(c_) < b_.distance(c_) else b_


_ext6 = lambda ln_: LineString([tuple(np.array(ln_[0]) - 6.0 * (np.array(ln_[1]) - np.array(ln_[0])) / math.dist(ln_[0], ln_[1]))] + ln_)
_lh, _lw, _le = _yh_offset(_hk, YH_WALL_OFF), _yh_offset(_ext6(_W_RD), YH_WALL_OFF), _yh_offset(_ext6(_E_RD), YH_WALL_OFF)
_cw, _ce = _lh.intersection(_lw), _lh.intersection(_le)
_cw, _ce = [g_ if g_.geom_type == 'Point' else g_.geoms[0] for g_ in (_cw, _ce)]
_s0, _s1 = sorted((_lh.project(_cw), _lh.project(_ce)))
_wall_h = substring(_lh, _s0, _s1)
if Point(_wall_h.coords[0]).distance(_cw) > 1.0:
    _wall_h = LineString(list(_wall_h.coords)[::-1])          # (west -> east)
_zr = lambda x_, y_: hk_z(_hk.interpolate(_hk.project(Point(x_, y_))).x)       # (한경길 abreast: HANGYEONG_Q)
_zd = lambda ln_, g_, x_, y_: float(np.interp(ln_.project(Point(x_, y_)), *g_))     # (a side drive at its grade)


def _yh_wall_top(x_):                                       # over the road, by x along 한경길 (west 0.7, flight 0.75, east 1.1)
    return float(np.interp(x_, [_cw.x, 73.5, _ce.x], [0.7, 0.75, 1.1]))


def _yh_up_drive(lc, ln, g, corner, z_top, top_flight, run=None):
    """the wall's run up a drive from its corner, `run` m of it (or to 2.5 m short of the drive's way into the
    garden): its height over the drive runs out evenly along it, its top climbing with the lawn it holds.  (The drives
    climb 2.3 - 2.4 m from 한경길 to the garden's ways in by the aerial photos of 1997, 9 - 12 %: a wall with a level
    top, as it was on the all but level drives the game had, would be gone in 7 m; the 2008 roadview has it some 11 m
    up the west drive and to just short of the way in on the east one.)  Returns (x, y, z at its foot, z at its top)"""
    s_c = lc.project(corner)
    s_f = lc.project(Point(*top_flight))
    sgn = 1.0 if s_f > s_c else -1.0
    run = abs(s_f - s_c) - 2.5 if run is None else run
    h0_ = z_top - _zd(ln, g, corner.x, corner.y)
    pts_ = []
    for k in range(1, 60):
        d_ = 0.8 * k
        if d_ > run:
            break
        q_ = lc.interpolate(s_c + sgn * d_)
        zf_ = _zd(ln, g, q_.x, q_.y)
        pts_.append((q_.x, q_.y, zf_, zf_ + h0_ + (0.12 - h0_) * d_ / run))
    return pts_


# at the two corners the top is no lower than 0.6 m and 0.8 m over the drive's mouth (한경길 runs level past both by
# the aerial photos, HANGYEONG_Q: the surface model had it fall 0.9 m in the 4 m before the east one, and the wall
# stood 1.8 m there), and along 한경길 it eases over 6 m from there to its own height
_zc_w = max(_zr(_cw.x, _cw.y) + _yh_wall_top(_cw.x), _zd(_wrd, _gw, _cw.x, _cw.y) + 0.6)
_zc_e = max(_zr(_ce.x, _ce.y) + _yh_wall_top(_ce.x), _zd(_erd, _ge, _ce.x, _ce.y) + 0.8)
_run_w = _yh_up_drive(_lw, _wrd, _gw, _cw, _zc_w, _tw, run=11.0)[::-1]   # (top of the west drive's run -> the corner)
_run_e = _yh_up_drive(_le, _erd, _ge, _ce, _zc_e, _te)
_fs = YEONHUI['flights'][1]                                  # the south flight: a gap in the wall
_fs_ax = LineString([_fs['top'], _fs['foot']])
_fs_hw = _fs['width'] / 2 + _fs['cheek']
YH_WALL = []                                                 # runs of [x, y, z at its foot, z at its top]
_run = [list(p_) for p_ in _run_w]
for s_ in np.arange(0.0, _wall_h.length + 0.01, 0.8):
    q_ = _wall_h.interpolate(min(s_, _wall_h.length))
    zf_ = _zr(q_.x, q_.y)
    if _fs_ax.distance(q_) < _fs_hw:                        # (the flight's gap)
        if _run:
            YH_WALL.append(_run)
        _run = []
        continue
    zt_ = zf_ + _yh_wall_top(q_.x)
    for c_, zc_ in ((_cw, _zc_w), (_ce, _zc_e)):
        f_ = max(0.0, 1.0 - c_.distance(q_) / 6.0)
        zt_ = max(zt_, zt_ + (zc_ - zt_) * f_)
    _run.append([q_.x, q_.y, zf_, zt_])
_run += [list(p_) for p_ in _run_e]
YH_WALL.append(_run)
YH_WALL = [[[round(float(v_), 2) for v_ in p_] for p_ in r_] for r_ in YH_WALL if len(r_) > 1]
_fs['wall_h'] = round(_yh_wall_top(_fs['foot'][0]), 2)
# the lawn behind it at its top: free nodes in a band 4.5 m deep behind each run
for r_ in YH_WALL:
    _ln = LineString([p_[:2] for p_ in r_])
    _m = shapely.contains_xy(_yh_offset(_ln, 2.25).buffer(2.25, cap_style='flat'), X, Y) & ~FIXED
    _yhs = shapely.line_locate_point(_ln, shapely.points(X[_m], Y[_m]))
    _yhk = np.cumsum([0.0] + [math.hypot(b_[0] - a_[0], b_[1] - a_[1]) for a_, b_ in zip(r_, r_[1:])])
    Hn[_m] = np.interp(_yhs, _yhk, [p_[3] for p_ in r_])
    FIXED[_m] = True
YEONHUI['wall'] = YH_WALL
YH_WALL_COLL = []                                            # (web: the player does not walk through it)
for r_ in YH_WALL:
    _ln = LineString([p_[:2] for p_ in r_])
    _g = _yh_offset(_ln, 0.25).buffer(0.25, cap_style='flat').simplify(0.05)
    for g_ in (_g.geoms if hasattr(_g, 'geoms') else [_g]):
        YH_WALL_COLL.append([[round(x_, 2), round(y_, 2)] for x_, y_ in list(g_.exterior.coords)[:-1]])
# the lamp at the head of the south flight: in 2008 a single white globe on a dark post behind the boxwood east of
# the flight's head (2381709 · 2381711: resected on the flight's four corners, both residuals under 0.6 deg, each
# reading dropped in turn moves it 0.7 m at most); by 2026 a brown one stands at the west corner instead
YEONHUI['lamp'] = [79.9, 303.6]
YH_WALL_COLL.append([[round(YEONHUI['lamp'][0] + dx_, 2), round(YEONHUI['lamp'][1] + dy_, 2)]
                     for dx_, dy_ in ((-0.25, -0.25), (0.25, -0.25), (0.25, 0.25), (-0.25, 0.25))])
for _f in YEONHUI['flights']:            # keep the ground under each flight below its treads
    if _f['name'] in ('west', 'east', 'south'):
        # ... and the banks either side of the two flights down from the side drives, past both ends too, no higher
        # than a little over their treads: the 5 m grid's bank nodes beside them (one cell is as long as the flight)
        # stood the ground up to 0.7 m over the lower treads and the coped walls
        _d = np.array(_f['down']); _o = np.array(_f['top'])
        _al = (X - _o[0]) * _d[0] + (Y - _o[1]) * _d[1]
        _pe = -(X - _o[0]) * _d[1] + (Y - _o[1]) * _d[0]
        _Lf = _f['landing'] + _f['n'] * _f['tread']
        _m = (_al > -3.0) & (_al < _Lf + 3.0) & (np.abs(_pe) < _f['width'] / 2 + 5.5)
        _line = np.interp(_al[_m], [0.0, _f['landing'], _Lf], [_f['z_top'], _f['z_top'], _f['z_foot']])
        # (under the flight well down: between grid nodes 5 m apart the ground is a straight chord, flatter than the
        # flight, so the node under its upper half has to sit low for the chord to clear the lower treads)
        _under = (np.abs(_pe[_m]) < _f['width'] / 2 + 1.6) & (_al[_m] >= 0.0) & (_al[_m] <= _Lf)
        # (beside it, the treads 3 m further down: a node's triangles reach that far along the flight)
        _side = np.interp(_al[_m] + 3.0, [0.0, _f['landing'], _Lf], [_f['z_top'], _f['z_top'], _f['z_foot']]) + 0.1
        _side = np.where(_al[_m] < 0.3, _f['z_top'] + 0.5, _side)                      # (not the drive at its head)
        _cap = np.where(_under, _line - 1.6, np.where(_al[_m] > _Lf, _f['z_foot'] + 0.25, _side))
        Hn[_m] = np.minimum(Hn[_m], _cap)
        FIXED[_m] = True
    fix_strip([_f['top'], _f['foot']], _f['z_top'] - 0.35, _f['z_foot'] - 0.25, _f['width'] / 2 + 1.6, top=True)
# the garden's level runs on north of the diamond to the foot of the bank under the road (the aerial photos: 54.8 -
# 55.1 m at four points 5 - 9 m from the road's edge): the bank is no wider than the north flight is long, not one
# slope from the diamond's edge to the road
_dfr = shp_distance(P, LineString(_FRONT_RD)).reshape(X.shape)
_dsd = np.minimum(shp_distance(P, _wrd), shp_distance(P, _erd)).reshape(X.shape)
_lawn_n = (shapely.contains_xy(Polygon(_W_RD[3:] + _FRONT_RD[1:] + [_E_RD[1]]), X, Y) & (_dfr > 3.5 + 0.6 + YH_NORTH_N * 0.31 + 1.0)
           & (_dsd > 7.0) & ~FIXED & ~near_buildings(1.0))
Hn[_lawn_n] = yh_plane(GE[_lawn_n], GN[_lawn_n])
FIXED[_lawn_n] = True
# the rest of the block (the banks, the lawns between the garden and 한경길, the verges along 교육관 and 성암관) one
# smooth surface between all that
_blk = Polygon(_W_RD + _FRONT_RD[1:] + _E_RD[::-1][1:] + [(105.3, 286.1), (72.5, 295.2), (52.5, 300.2)]).buffer(8.0)
_free = shapely.contains_xy(_blk, X, Y) & (GN > -24.0) & ~FIXED & ~near_buildings(1.0)
harmonic_fill(_free)
print('연희관 앞', {k: v for k, v in YEONHUI.items() if k not in ('flights', 'wall')},
      'wall runs', [(len(r_), r_[0][3] - r_[0][2], r_[-1][3] - r_[-1][2]) for r_ in YEONHUI['wall']],
      [(f_['name'], f_['n'], f_['z_top'], f_['z_foot']) for f_ in YEONHUI['flights']])

# --- 성암관's west front (blender/landmarks.py seongam): the pointed door opens at the head of a short flight down to
# the drive along the hall (reference/학교연혁_성암관.jpg: two risers at the door, a landing, five or more below it).
# The 5 m grid ran the hill behind the hall down across the 3 m between its porch and the drive, a 1.5 m fall, and the
# flight grew to twenty risers with a landing that ran out over the drive to the lawn beyond, in the way of the drive
# from 언더우드관 up to 대우관.  Hold the ground between the drive's east edge and the hall level across at the edge's
# height, and the porch seven risers of 0.16 over it at the door (SEONGAM_FLOOR: the floor under the porch's 1.2 m).
_sd = LineString(_E_RD)
SEONGAM_DOOR = ((115.82 + 118.54) / 2, (301.6 + 312.55) / 2)        # the middle of the porch's face (OSM)


def _sd_edge(x, y):
    """the drive's east edge (3 m from its centre line) abreast of x, y, and how far x, y lies east of the centre"""
    a_ = _sd.project(Point(x, y))
    q_ = np.array(_sd.interpolate(a_).coords[0])
    t_ = np.array(_sd.interpolate(min(a_ + 0.5, _sd.length)).coords[0]) - np.array(_sd.interpolate(max(a_ - 0.5, 0.0)).coords[0])
    t_ /= np.linalg.norm(t_)
    r_ = np.array([t_[1], -t_[0]])                                  # (the right of the way north: east)
    return q_ + r_ * 3.0, float((np.array([x, y]) - q_) @ r_)


_sm = (X > 100) & (X < 130) & (Y > 285) & (Y < 325)
_sv = []
for _j, _i in zip(*np.nonzero(_sm)):
    _e, _off = _sd_edge(X[_j, _i], Y[_j, _i])
    if 3.0 <= _off <= 11.0:
        _sv.append((_j, _i, sample(Hn, NEAR_HALF, NEAR_STEP, *_e)))
for _j, _i, _h in _sv:
    Hn[_j, _i] = _h
    FIXED[_j, _i] = True
SEONGAM_FLOOR = round(sample(Hn, NEAR_HALF, NEAR_STEP, *_sd_edge(*SEONGAM_DOOR)[0]) + 7 * 0.16 - 1.2, 2)
print('성암관 west front: %d nodes held at the drive\'s edge, floor %.2f' % (len(_sv), SEONGAM_FLOOR))

# --- 대우관 (reference/고증/3.6; reference/대우관_정면_전경.jpg, 대우관_2024_정면과_상뜰.jpg, 대우관_측면_2012.jpg, the vertical
# aerial photos of 1997-07-28 and Kakao's skyview of 2008): the hall stands at the back of a terrace 5 m over the 상뜰.
# A drive crosses the terrace before the wings' fronts, from the drive up the 상뜰's west side to the one up its east
# side; lawns with clipped cones lie between the wings either side of the paving before the tower's door.  South of
# the drive the terrace ends at a wall with a hedge along its top, and before the tower a white stone podium stands
# out from it, its ends rounded: the main door is a wide low arch in its face at the 상뜰's level, and either side of
# the door's forecourt a flight climbs outwards along the face to a landing in the rounded end and turns back up along
# the top of the face to the terrace.  Beside the podium the ground steps down in two lawn tiers to the 상뜰.
# The 5 m grid cannot hold the terrace wall's drop, so (as behind the hall, DAEWOO_BACK): every cell the wall crosses
# is level at its low side, and the terrace over those cells is a mesh of its own (`deck`, the ground's own material).
#
# The frames.  OSM's outline is 4 m short on the east and turned: the photos' roofs, the terrace's hedge lines and the
# line through the tower's lantern, the podium, the 상뜰's walk and its round lawn all stand 0.84 degrees anticlockwise
# of OSM's recessed front (DW_U / DW_V below, the frame the yard behind the hall was read in), about one axis.  So the
# hall's own frame (DH_U / DH_V, dh_xy): OSM's turned DW_ROT about (DW_UC, 0), the axis at u = DW_UC; the wings stand
# 11.5 m wide either side of it, 24.1 .. 35.6 m out, from v -10.4 back to 27.55.
_fp = list(footprint(ways[242897922]).exterior.coords)
_a, _b = np.array(_fp[3]), np.array(_fp[4])
_t = (_b - _a) / np.linalg.norm(_b - _a)
_nl = np.array([-_t[1], _t[0]])                                  # into the hall
DW_U = (X - _a[0]) * _t[0] + (Y - _a[1]) * _t[1]                 # along OSM's recessed front, from its west end
DW_V = (X - _a[0]) * _nl[0] + (Y - _a[1]) * _nl[1]              # towards the hall (OSM's front wall at v = 0)
DW_ROT, DW_UC = math.radians(0.84), 24.86
_ht = np.array([_t[0] * math.cos(DW_ROT) - _t[1] * math.sin(DW_ROT), _t[0] * math.sin(DW_ROT) + _t[1] * math.cos(DW_ROT)])
_hn = np.array([-_ht[1], _ht[0]])
_ha = _a + _t * DW_UC - _ht * DW_UC
DH_U = (X - _ha[0]) * _ht[0] + (Y - _ha[1]) * _ht[1]
DH_V = (X - _ha[0]) * _hn[0] + (Y - _ha[1]) * _hn[1]


def dh_xy(u, v, o_=_ha.copy(), t_=_ht.copy(), n_=_hn.copy()):     # (the hall's own frame as a point)
    return tuple(float(c_) for c_ in np.round(o_ + t_ * u + n_ * v, 2))


def dh_uv(p_, o_=_ha.copy(), t_=_ht.copy(), n_=_hn.copy()):       # (and back)
    d_ = np.asarray(p_, float)[:2] - o_
    return float(d_ @ t_), float(d_ @ n_)


# The levels are the photos' (tools/aerial97.py z; the terrace's asphalt 70.2 - 70.6 m in twelve places, the landings
# in the podium's ends 68.5 - 68.8, the tier beside it 68.2 - 68.4, the lower lawn 66.4 - 67.0, the 상뜰 65.0 - 65.5):
# the terrace is where the game had it (70.55), the 상뜰 1.5 m higher than it was.
DW_WI, DW_WO = 24.1, 35.6                                          # the wings' inner and outer walls from the axis
DAEWOO = dict(floor=70.9, terrace=70.45, mid=68.6, plaza=65.6, tier=68.4, lawn=66.6,
              frame=dict(o=[round(float(c_), 3) for c_ in _ha], ang=round(math.atan2(_ht[1], _ht[0]), 5)), uc=DW_UC,
              wi=DW_WI, wo=DW_WO, wing_v=(-10.4, 27.55), u0=round(DW_UC - DW_WO, 2), u1=round(DW_UC + DW_WO, 2),
              # the terrace: its drive (v), its ends (u: where its wall dies into the drives' banks)
              drive=(-18.3, -10.4), tu=(-12.2, 62.5),
              # the podium: half width, its face (v), the front of the lower flights, the forecourt's half width
              podium=dict(hw=13.0, face=-24.5, front=-28.5, court=4.0, end=-29.5))
_T, _P = DAEWOO['terrace'], DAEWOO['plaza']
_tu0, _tu1 = DAEWOO['tu']
_tv0, _tv1 = DAEWOO['drive']
_uvh = lambda pts_: Polygon([dh_xy(*q_) for q_ in pts_])
# the terrace's own ground: the drive and the lawns and paving between the wings (the hall's floor over the rest)
DW_TERR = _uvh([(_tu0, _tv0), (_tu1, _tv0), (_tu1, _tv1), (DW_UC + DW_WI, _tv1), (DW_UC + DW_WI, 0.0),
                (DW_UC - DW_WI, 0.0), (DW_UC - DW_WI, _tv1), (_tu0, _tv1)])


def dw_low(u, v):
    """the ground south of the terrace wall: the podium's own at the forecourt's level, beside it the tier under the
    wall, the lower lawn and the 상뜰's north edge"""
    return np.where((np.abs(u - DW_UC) < DAEWOO['podium']['hw'] + 0.5) & (v > DAEWOO['podium']['end']), _P,
                    np.interp(v, [-29.5, -26.5, -21.5], [_P - 0.1, DAEWOO['lawn'], DAEWOO['tier']]))


DW_TW = (_tu0 + 10.2, _tu1 - 8.0)
_m_terr = (DH_V > _tv0) & (DH_V < 15.0) & (DH_U > _tu0 - 0.5) & (DH_U < _tu1 + 0.5) & \
    ((DH_V < _tv1) | (np.abs(DH_U - DW_UC) < DW_WO))              # the terrace, and the ground the hall stands on
_m_low = (DH_V <= _tv0) & (DH_V > -30.0) & (DH_U > DW_TW[0]) & (DH_U < DW_TW[1])
Hn[_m_terr] = _T
Hn[_m_low] = dw_low(DH_U[_m_low], DH_V[_m_low])
# (every cell the terrace wall crosses, level at its low side; the drop is held from DW_TW[0], two cells off the west
# drive -- whose own cells must stay the drive's, level across for the cars -- to the east drive's west kerb: at its
# two ends the terrace comes down to the drives' banks as the grid has it)
_twall = LineString([dh_xy(DW_TW[0], _tv0), dh_xy(DW_TW[1], _tv0)])
_tcells = set()
for _k in range(int(_twall.length / 0.5) + 1):
    _q = _twall.interpolate(_k * 0.5)
    _tcells.add((int(math.floor((_q.y + NEAR_HALF) / NEAR_STEP)), int(math.floor((_q.x + NEAR_HALF) / NEAR_STEP))))
_tforced = np.zeros(X.shape, bool)
for _j, _i in _tcells:
    for _a_, _b_ in ((0, 0), (0, 1), (1, 0), (1, 1)):
        Hn[_j + _a_, _i + _b_] = float(dw_low(DH_U[_j + _a_, _i + _b_], min(DH_V[_j + _a_, _i + _b_], _tv0 - 0.01)))
        _tforced[_j + _a_, _i + _b_] = True
_cell_box0 = lambda j_, i_: shapely.geometry.box(gx[i_], gx[j_], gx[i_] + NEAR_STEP, gx[j_] + NEAR_STEP)
DW_FDECK_CELLS = {(j_ + a_, i_ + b_) for j_, i_ in zip(*np.nonzero(_tforced)) for a_ in (-1, 0) for b_ in (-1, 0)}
DW_FDECK_POLY = unary_union([_cell_box0(j_, i_) for j_, i_ in DW_FDECK_CELLS]).intersection(DW_TERR)
_court = _m_terr | _m_low | _tforced                             # (what this block sets: the smooth fills leave it)
_strip = np.zeros(X.shape, bool)
FIXED[_court] = True
# 상뜰 (issue #39; reference/대우관_정면_전경.jpg, 대우관_2024_정면과_상뜰.jpg; the same photos of 1997): a level terrace on
# the hall's axis.  Its round lawn's middle (SANG) is the photos' (five frames within 0.1 m: 1.7 m east and 1.0 m
# north of OSM's ring), its walks' ends where the photos have them: north at the podium's forecourt, south at the
# head of the flight, west and east at the two drives.  From 65.4 m at its north node it falls 1.5 % southwards and
# 1 % west of its axis.  At its south node a broad granite flight with steel handrails on both sides goes down
# through the trees to the footway (OSM 1451337739; the photos have the node at 64.8 m and the footway at 61.9: 19
# risers of 15.5 cm), which runs straight between its ends but for the foot of the flight; the bank round it and
# under the diamond's lower walks is filled smoothly (and planted, below).
# (SG: e east along the hall, n north, from the round lawn's centre.  *_RNG: as the 상뜰 was first laid out on OSM's
# ring, what the random planting read.)
SANG_RNG = (106.8, 427.1)
SG_RNG = lambda e, n: tuple(np.array(SANG_RNG) + np.array([0.964, -0.263]) * e + np.array([0.263, 0.964]) * n)
SANG_DIAMOND_RNG = [SG_RNG(-0.8, 14.2), SG_RNG(-26.5, 0.0), SG_RNG(0.0, -15.3), SG_RNG(26.6, 0.4)]
SANG = (108.5, 428.1)
SG_E = _ht.copy()
SG_N = _hn.copy()
SG = lambda e, n: tuple(np.array(SANG) + SG_E * e + SG_N * n)
SANG_NODES = dict(N=(0.0, 12.6), W=(-28.3, 0.6), S=(-0.3, -18.0), E=(31.5, 1.0))     # (e, n) of the walks' four ends
SANG_DIAMOND = [SG(*SANG_NODES[k_]) for k_ in 'NWSE']                                # N, W, S, E nodes of the walks
SANG_LV = dict(top=65.4, fall=0.015, west=0.01, east=0.0)


def sang_h(e, n):
    return SANG_LV['top'] + SANG_LV['fall'] * (n - SANG_NODES['N'][1]) - np.where(e < 0, SANG_LV['west'], SANG_LV['east']) * np.abs(e)


_SE = (X - SANG[0]) * SG_E[0] + (Y - SANG[1]) * SG_E[1]
_SN = (X - SANG[0]) * SG_N[0] + (Y - SANG[1]) * SG_N[1]
_sg = shapely.contains_xy(Polygon(SANG_DIAMOND).buffer(3.0), X, Y) & ~_court
Hn[_sg] = sang_h(_SE[_sg], _SN[_sg])
FIXED[_sg] = True
_zS = float(sang_h(*SANG_NODES['S']))
SANG_FOOT = (101.2, 405.4)                                      # (the footway under the flight, OSM)
_ds_ = np.array(SANG_FOOT) - np.array(SANG_DIAMOND[2])
DAEWOO['sang'] = SANG_LV
DAEWOO['stair'] = flight_at('sang_south', SANG_DIAMOND[2], _ds_, _zS, _zS - 19 * 0.155, 5.5, landing=0.5, tread=0.30,
                            maxrise=0.155, rails=True, cheek=0.25)
_fwW, _fwE = sample(Hn, NEAR_HALF, NEAR_STEP, 66.6, 414.3), sample(Hn, NEAR_HALF, NEAR_STEP, 137.7, 396.5)
fix_strip([(66.6, 414.3), SANG_FOOT], _fwW, DAEWOO['stair']['z_foot'], 1.8)
fix_strip([SANG_FOOT, (137.7, 396.5)], DAEWOO['stair']['z_foot'], _fwE, 1.8)
_st = DAEWOO['stair']
fix_strip([_st['top'], _st['foot']], _st['z_top'] - 0.35, _st['z_foot'] - 0.25, _st['width'] / 2 + 1.6, top=True)
print('상뜰', SANG_LV, 'S node %.2f, footway %.2f .. %.2f .. %.2f' % (_zS, _fwW, _st['z_foot'], _fwE))
_free = (DW_U > -32) & (DW_U < 80) & (DW_V > -74) & (DW_V < 4) & ~_court & ~FIXED & ~near_buildings(1.0)
harmonic_fill(_free)
# the two drives up to the terrace.  West: from abreast of the 상뜰's west node (as the ground runs there, about a
# metre over the 상뜰: the 2008 roadview has the drive 0.5 - 1.5 m over it) up to the terrace's level where the
# terrace drive leaves it.  East: the same from abreast of the east node.  (The photos' heights along both are lost
# under the trees.)
DW_WEST_RD = [dh_xy(-19.3, -46.0), dh_xy(-19.3, -38.0), dh_xy(-16.5, -26.0), dh_xy(DAEWOO['u0'] - 5.0, _tv0 + 3.9)]
DW_EAST_RD = [dh_xy(59.3, -44.0), dh_xy(59.3, _tv0 + 2.0)]
DW_RD_OWN = []                                   # (the west one's nodes: the cars' drive, levelled across again below)
for _rd in (DW_WEST_RD, DW_EAST_RD):
    _z0r = max(sample(Hn, NEAR_HALF, NEAR_STEP, *_rd[0]), SANG_LV['top'] + 0.6)
    DW_RD_OWN.append(fix_strip(_rd, _z0r, _T, 3.6))
    print('daewoo drive to the terrace: %.2f -> %.2f m over %.1f m, %.1f %%' % (
        _z0r, _T, LineString(_rd).length, 100 * (_T - _z0r) / LineString(_rd).length))
_free = (DW_U > -36) & (DW_U < 84) & (DW_V > -60) & (DW_V < 4) & ~_court & ~FIXED & ~near_buildings(1.0)
harmonic_fill(_free)
print('daewoo', {k_: v_ for k_, v_ in DAEWOO.items() if k_ not in ('stair',)}, 'terrace deck cells', len(DW_FDECK_CELLS))
# --- 대우관 뒤 (reference/고증/3.6.2): the yard behind the hall as the vertical aerial photos of 1997-07-28 have it
# (four frames; the same plan in Kakao's skyview of 2008 and 2010, in OSM's aisles and steps and in Naver's street view
# of 2010-09 from the road north of it), in the hall's frame (u along it from the west end of its recessed front, v
# from the front wall to the back; the back wall at v = 14.8).  The game had one car park of five rows on a plane.
#  - Behind the back tower a half-round open-air theatre: a paved floor (`stage`, 1.3 m over the west court) round
#    DWB_C, six stepped seats rising north and east of it (r_stage .. r_seat) to a walk round their top (.. r_walk)
#    at the upper car park's level, a hedge belt outside that (.. r_belt).
#  - West of it the low court at the road's level (`low`): the mouth of the underground car park (`portal`) in the
#    retaining wall w1 that holds up the upper level, a wall w2 running west from its north end with the lawn mound
#    banked against its other side, a wall w3 and a flight of steps (`stair`) up to the walk round the seats.
#  - North-east the upper car park (`top` at the seats' rim, rising 2 % northwards to its mouth on the road): stalls
#    fanned round the hedge belt, a short row west of its aisle, a long row along its east side under the bank of the
#    road to 북문; south of it a wall (w4) down to the areaway behind the east wing.
# The photos' heights (tools/aerial97.py z, ±0.3 m on the open asphalt): court 72.4, floor of the theatre 73.7, upper
# car park 76.0 - 76.8 m.  They are the yard's as they stand: the terrace before the hall is 70.4 m in the same photos,
# so the yard lies a storey over it (the hall's back door opens onto the theatre's floor from the storey over the
# terrace's; the 2010 street view shows that lower storey's rusticated band just over the court).  (The game first had
# them 3.0 m lower, on the guess that the back door was on the terrace's storey.)
# The 5 m grid cannot hold the walls' drops, so: every cell a wall crosses is level at its low side's height, and the
# upper level over those cells and the ones behind them is a mesh of its own (`deck`: the ground's own material, walked
# and driven on; blender/landmarks.py daewoo_back), its outer edge on cell edges whose nodes hold the same heights.


def dw_xy(u, v, o_=_a.copy(), t_=_t.copy(), n_=_nl.copy()):       # (대우관's frame, DW_U / DW_V, as a point)
    return tuple(float(c_) for c_ in np.round(o_ + t_ * u + n_ * v, 2))


def dw_uv(p_, o_=_a.copy(), t_=_t.copy(), n_=_nl.copy()):          # (and back)
    d_ = np.asarray(p_, float)[:2] - o_
    return float(d_ @ t_), float(d_ @ n_)


DWB_C = (24.4, 30.8)


def dwb_arc(r_, a0_, a1_, step_=3.0):
    """(u, v) round DWB_C at radius r_ from angle a0_ to a1_ (degrees from +u towards +v)"""
    n_ = max(2, int(abs(a1_ - a0_) / step_) + 1)
    return [(DWB_C[0] + r_ * math.cos(math.radians(a0_ + (a1_ - a0_) * k_ / (n_ - 1))),
             DWB_C[1] + r_ * math.sin(math.radians(a0_ + (a1_ - a0_) * k_ / (n_ - 1)))) for k_ in range(n_)]


_low = round(DAEWOO['floor'] + 1.4, 2)
DAEWOO_BACK = dict(
    c=DWB_C, low=_low, stage=round(_low + 1.3, 2), top=round(_low + 3.7, 2),
    r_stage=8.3, r_seat=13.6, r_walk=15.0, r_belt=18.5, tiers=6, seat_a=(0.0, 108.0), landing=(108.0, 132.0, 9.0),
    # the hall's back as the same photos' roofs have it (the plane of the parapet, four frames): the tower 8 m out and
    # 13.2 m wide, a block either side of it 5.8 m out, the wings' back ends 2.5 and 3.8 m past OSM's
    # (in the hall's own frame, DH: about its axis)
    tower=(DW_UC - 6.6, DW_UC + 6.6, 22.8), blocks=((DW_UC - 18.2, DW_UC - 6.6, 20.6), (DW_UC + 6.6, DW_UC + 18.2, 20.6)),
    wing_v=(DAEWOO['wing_v'][1], DAEWOO['wing_v'][1]),
    w1=[(24.5, 47.3), (24.5, 61.7)], portal=(50.0, 56.0), w2=[(17.0, 61.7), (24.5, 61.7)],
    w3=[(24.5, 47.3), (19.8, 45.0)], w4=[(38.64, 35.5), (61.0, 35.5)],
    stair=[(14.6, 47.0), (18.9, 43.8), 3.0],
    box=[(24.5, 61.7), (36.1, 61.7), (36.1, 67.2), (24.5, 67.2)],
    # the stalls: (name, first side line's foot (u, v), along the row, towards the nose, how many); 2.5 m by 5.0 m.
    # The fan's are laid out round DWB_C below (r_belt + 0.1 .. + 5.1, their middles 6.8 degrees apart)
    rows=[('col', (45.1, 57.2), (0.0, 1.0), (-1.0, 0.0), 5), ('east', (55.5, 36.0), (0.0, 1.0), (1.0, 0.0), 13),
          ('south', (44.5, 40.5), (1.0, 0.0), (0.0, -1.0), 4), ('w2', (17.0, 56.7), (1.0, 0.0), (0.0, 1.0), 3),
          ('wing', (-10.5, 33.2), (1.0, 0.0), (0.0, -1.0), 4)],
    # ... and the two fans, nose to the theatre: (name, from, to (degrees round c), how many, inner end's radius)
    fans=[('fan', 8.0, 78.0, 10, 18.6), ('wfan', 141.0, 185.0, 6, 17.2)], stall=2.5,
    # the upper car park's aisles (u), the turn at their south end (v) and its mouth on the road north of the hall:
    # where its middle line leaves the road's, and its heading (u, v)
    aisles=(48.6, 53.8), turn_v=46.5, mouth=((34.7, 86.0), (0.71, -0.70)),
    # the mound's kerbs along the mouth and the lawn island east of it with the round cooling tower
    mound_tip=(45.4, 72.0), island=[(46.3, 80.3), (54.8, 69.3), (61.0, 68.5)], tower_c=(52.3, 84.8),
    fence=[(74.5, 25.0), (71.5, 38.0), (67.8, 68.0), (67.2, 79.0)])
DAEWOO_BACK['o'], DAEWOO_BACK['ang'] = [round(float(c_), 3) for c_ in _a], round(math.atan2(_t[1], _t[0]), 5)   # (its frame: OSM's front)
_db = DAEWOO_BACK
# the road north of the hall: its middle line (OSM, x, y) and heights (the photos')
DWB_ROAD = [((89.9, 506.8), None), ((105.0, 517.0), _low - 0.05), ((125.0, 535.0), _low + 1.0), ((147.1, 547.2), _low + 4.1),
            ((153.6, 551.6), _low + 5.1), ((162.8, 555.6), _low + 6.2), ((171.9, 559.7), _low + 7.5), ((181.1, 563.8), _low + 8.9)]
DWB_RLS = LineString([q_ for q_, _ in DWB_ROAD])
DWB_RS = [DWB_RLS.project(Point(*q_)) for q_, _ in DWB_ROAD]
DWB_RZ = [DWB_ROAD[1][1] if z_ is None else z_ for _, z_ in DWB_ROAD]
dwb_road_z = lambda q_: float(np.interp(DWB_RLS.project(Point(*q_)), DWB_RS, DWB_RZ))      # (the road's height abreast of a point)


def dwb_lot_z(v):
    """the upper car park's plane: the walk round the seats' level at its south end, 2 % up northwards, 4 % in its mouth"""
    return DAEWOO_BACK['top'] - 0.1 + 0.0215 * (min(v, 75.0) - 40.0) + 0.04 * max(0.0, v - 75.0)


def dwb_h(x, y):
    """the upper level's surface: the car park's plane; within reach of the road north of it the road's height at its
    edge, the lawn mound rising from there at 33 % to the plane (the mouth falling to it within 6 m)"""
    zl_ = dwb_lot_z(dw_uv((x, y))[1])
    p_ = Point(x, y)
    zr_ = dwb_road_z((x, y))
    d_ = max(0.0, DWB_RLS.distance(p_) - 3.0)
    return zl_ + (zr_ - zl_) * max(0.0, 1.0 - d_ / 6.0) if zr_ >= zl_ else min(zl_, zr_ + 0.33 * d_)


def dwb_stalls(t_=_t.copy(), n_=_nl.copy()):
    """the yard's stalls: (row, i, its middle (x, y), the heading nose first, its two side lines ((x, y), (x, y)))"""
    out_ = []
    hd_ = lambda d_: math.atan2(*(t_ * d_[0] + n_ * d_[1])[::-1])
    for name_, f_, al_, ns_, k_ in DAEWOO_BACK['rows']:
        f_, al_, ns_ = np.array(f_), np.array(al_), np.array(ns_)
        for i_ in range(k_):
            a_, b_ = f_ + al_ * DAEWOO_BACK['stall'] * i_, f_ + al_ * DAEWOO_BACK['stall'] * (i_ + 1)
            out_.append((name_, i_, dw_xy(*((a_ + b_) / 2 + ns_ * 2.5)), hd_(ns_),
                         [(dw_xy(*a_), dw_xy(*(a_ + ns_ * 5.0))), (dw_xy(*b_), dw_xy(*(b_ + ns_ * 5.0)))]))
    for name_, a0_, a1_, k_, r0_ in DAEWOO_BACK['fans']:
        rad_ = lambda a_, r_: np.array(DWB_C) + r_ * np.array([math.cos(math.radians(a_)), math.sin(math.radians(a_))])
        for i_ in range(k_):
            a_, b_ = a0_ + (a1_ - a0_) * i_ / k_, a0_ + (a1_ - a0_) * (i_ + 1) / k_
            out_.append((name_, i_, dw_xy(*rad_((a_ + b_) / 2, r0_ + 2.5)), hd_(-rad_((a_ + b_) / 2, 1.0) + np.array(DWB_C)),
                         [(dw_xy(*rad_(a_, r0_)), dw_xy(*rad_(a_, r0_ + 5.0))), (dw_xy(*rad_(b_, r0_)), dw_xy(*rad_(b_, r0_ + 5.0)))]))
    return out_


# cars left along the north kerb of the road north of the hall, west of the upper car park's mouth (the 1997 photos
# have a line of them there), half on the kerb: (x, y), heading
DWB_KERB = []
_kl = LineString([dw_xy(*q_) for q_ in ((31.0, 82.6), (12.1, 64.7), (9.9, 61.6), (-13.2, 28.9))])
for _k in range(13):
    _q, _q1 = _kl.interpolate(3.0 + 5.9 * _k), _kl.interpolate(3.5 + 5.9 * _k)
    _d = np.array([_q1.x - _q.x, _q1.y - _q.y]) / 0.5
    DWB_KERB.append(((round(_q.x + _d[1] * 3.3, 2), round(_q.y - _d[0] * 3.3, 2)), math.atan2(_d[1], _d[0])))
_uvp = lambda pts_: Polygon([dw_xy(*q_) for q_ in pts_])
_st0, _st1, _stw = np.array(DAEWOO_BACK['stair'][0]), np.array(DAEWOO_BACK['stair'][1]), DAEWOO_BACK['stair'][2]
_std = (_st1 - _st0) / np.linalg.norm(_st1 - _st0)
_stn = np.array([-_std[1], _std[0]])                              # (to the flight's left going up: north-east)
DWB_STAIR_UV = [tuple(_st0 - _stn * _stw / 2), tuple(_st0 + _stn * _stw / 2), tuple(_st1 + _stn * _stw / 2), tuple(_st1 - _stn * _stw / 2)]
# the low court: from the west wing's back end round the theatre's west rim (its planter outside r_walk) to the
# flight's foot, along w3, w1 and w2, back along the road's south side (the road itself is graded with the cars' way)
DWB_COURT_UV = [(-11.3, 27.3), (0.2, 27.3)] + dwb_arc(17.0, 187.0, 126.0) + [DWB_STAIR_UV[0], DWB_STAIR_UV[1], DWB_STAIR_UV[2],
               DAEWOO_BACK['w3'][0], DAEWOO_BACK['w1'][1], DAEWOO_BACK['w2'][0], (13.0, 57.0), (5.5, 46.0), (-2.0, 35.5), (-6.5, 29.0)]
# the areaway behind the east wing, under w4
DWB_AREA_UV = [(42.6, 20.6), (48.4, 20.6), (48.4, 28.1), (61.0, 28.1), (61.0, 35.5)] + \
    dwb_arc(DAEWOO_BACK['r_walk'], 18.26, -25.0) + [(42.6, 24.5)]
# the theatre: the floor (to the hall's back), the seats and the walk round them
DWB_FLOOR_UV = [(0.2, 14.8), (48.4, 14.8), (48.4, 20.6), (42.6, 20.6), (42.6, 24.5)] + dwb_arc(DAEWOO_BACK['r_walk'], -25.0, 187.0) + [(0.2, 28.0)]
# the upper level: the mound, the terrace over the portal, the car park with the hedge belt, its mouth
DWB_HIGH_UV = [DAEWOO_BACK['w2'][0], DAEWOO_BACK['w1'][1], DAEWOO_BACK['w1'][0], DAEWOO_BACK['w3'][1]] + dwb_arc(DAEWOO_BACK['r_walk'], 105.0, 18.26) + \
    [DAEWOO_BACK['w4'][1], (61.0, 68.5), (54.8, 69.3), (46.3, 80.3), (40.8, 87.4), (33.5, 80.8), (15.2, 62.3)]
_dcourt, _darea, _dfloor, _dhigh = (_uvp(q_) for q_ in (DWB_COURT_UV, DWB_AREA_UV, DWB_FLOOR_UV, DWB_HIGH_UV))
assert all(q_.is_valid for q_ in (_dcourt, _darea, _dfloor, _dhigh)), [shapely.validation.explain_validity(q_) for q_ in (_dcourt, _darea, _dfloor, _dhigh)]
_off_road = shapely.distance(DWB_RLS, shapely.points(X, Y)) > 6.0       # (the road's own nodes: graded with the cars' way)
_m_court = shapely.contains_xy(_dcourt.union(_darea), X, Y) & _off_road
_m_floor = shapely.contains_xy(_dfloor, X, Y) & ~_m_court
_m_high = shapely.contains_xy(_dhigh, X, Y) & _off_road
Hn[_m_court] = DAEWOO_BACK['low']
Hn[_m_floor] = DAEWOO_BACK['stage'] - 0.12                                 # (under the paving, the seats and the walk: the meshes)
for _j, _i in zip(*np.nonzero(_m_high)):
    Hn[_j, _i] = dwb_h(X[_j, _i], Y[_j, _i])
# every cell a drop crosses level at its low side
_walls = [LineString([dw_xy(*q_) for q_ in l_]) for l_ in (
    [DAEWOO_BACK['w2'][0], DAEWOO_BACK['w1'][1], DAEWOO_BACK['w1'][0], DAEWOO_BACK['w3'][1], DWB_STAIR_UV[2], DWB_STAIR_UV[1]],                 # w2, w1, w3, the flight
    DAEWOO_BACK['w4'], dwb_arc(DAEWOO_BACK['r_walk'], 18.26, -25.0) + [(42.6, 24.5), (42.6, 20.6)],                         # w4 and the floor's east end
    dwb_arc(DAEWOO_BACK['r_walk'], 132.0, 187.0) + [(0.2, 28.0)],                                                    # the floor's west rim
    # the walk's rim along the hedge belt: no drop, but the nodes inside it lie under the seats, and the cells that
    # straddle it sloped down to them (a hollow up to 2 m deep in the belt at 35 - 55 degrees)
    dwb_arc(DAEWOO_BACK['r_walk'], 105.0, 18.26))]
_forced = np.zeros(X.shape, bool)
_cells = set()
for _wl, _zl in zip(_walls, [DAEWOO_BACK['low']] * len(_walls)):
    for _k in range(int(_wl.length / 0.5) + 1):
        _q = _wl.interpolate(_k * 0.5)
        _cells.add((int(math.floor((_q.y + NEAR_HALF) / NEAR_STEP)), int(math.floor((_q.x + NEAR_HALF) / NEAR_STEP))))
for _j, _i in _cells:
    if not all(_off_road[_j + _a_, _i + _b_] for _a_, _b_ in ((0, 0), (0, 1), (1, 0), (1, 1))):
        continue                                       # (w2's west end by the road: the rocks there, on the ground as it runs)
    for _a_, _b_ in ((0, 0), (0, 1), (1, 0), (1, 1)):
        Hn[_j + _a_, _i + _b_] = DAEWOO_BACK['low']
        _forced[_j + _a_, _i + _b_] = True
_m_yard = _m_court | _m_floor | _m_high | _forced
FIXED[_m_yard] = True
# the deck: the upper level over the cells whose nodes were pulled down, cut to its outline; a 1.25 m lattice (the
# cells' own edges on it), on the surface, but along the edges it shares with whole cells of the ground as the ground
# runs there (straight between their nodes)
_dk_cells = {(j_ + a_, i_ + b_) for j_, i_ in zip(*np.nonzero(_forced)) for a_ in (-1, 0) for b_ in (-1, 0)}
_cell_box = lambda j_, i_: shapely.geometry.box(gx[i_], gx[j_], gx[i_] + NEAR_STEP, gx[j_] + NEAR_STEP)
_dk_poly = unary_union([_cell_box(j_, i_) for j_, i_ in _dk_cells]).intersection(_dhigh)
DWB_DECK_CELLS, DWB_DECK_POLY = _dk_cells, _dk_poly
# (the road north of the hall west of where the cars' way leaves it, TRAFFIC below: on DWB_ROAD's grade too)
fix_strip([(128.6, 537.2), (105.0, 517.0)], dwb_road_z((128.6, 537.2)), dwb_road_z((105.0, 517.0)), 3.6)
fix_strip([(105.0, 517.0), (93.0, 509.4), (89.9, 506.8)], dwb_road_z((105.0, 517.0)), dwb_road_z((105.0, 517.0)), 3.6)
_free = (DW_U > -40) & (DW_U < 100) & (DW_V > 10) & (DW_V < 115) & ~_m_yard & ~FIXED & ~near_buildings(1.0)
harmonic_fill(_free)
print('daewoo back yard: court %.2f, floor %.2f, upper %.2f .. %.2f; nodes %d (pulled down %d), deck cells %d, %.0f m2' % (
    DAEWOO_BACK['low'], DAEWOO_BACK['stage'], dwb_lot_z(36.0), dwb_lot_z(75.0), int(_m_yard.sum()), int(_forced.sum()), len(_dk_cells), _dk_poly.area))
# 대우관's sides and back ends.  The grid nodes within a metre of a hall are left out of the smooth fills above, so
# the old surface (the elevation data still holding a little of the hall's own bulk) stayed against its walls.  The
# 2012 photo (reference/대우관_측면_2012.jpg) and Street View show the hall standing on its ground all round, the lawns
# falling away from a walk along its walls: a 3 m apron round the wings' sides and the back, blending into the ground
# over the next 7 m (not across the terrace, the yard or the other aprons).  Its height runs with the hall's two
# levels: the terrace's at the wings' fronts, the low court's at their back ends (DAEWOO_BACK: a storey higher).
DW_OUTLINE_UV = [(DW_UC - DW_WO, 27.55), (DW_UC - DW_WO, -10.4), (DW_UC - DW_WI, -10.4), (DW_UC - DW_WI, 0.0),
                 (DW_UC + DW_WI, 0.0), (DW_UC + DW_WI, -10.4), (DW_UC + DW_WO, -10.4), (DW_UC + DW_WO, 27.55),
                 (DW_UC + DW_WI, 27.55), (DW_UC + DW_WI, 14.8), (DW_UC + 18.2, 14.8), (DW_UC + 18.2, 20.6),
                 (DW_UC + 6.6, 20.6), (DW_UC + 6.6, 22.8), (DW_UC - 6.6, 22.8), (DW_UC - 6.6, 20.6), (DW_UC - 18.2, 20.6),
                 (DW_UC - 18.2, 14.8), (DW_UC - DW_WI, 14.8), (DW_UC - DW_WI, 27.55)]     # (the hall as the photos' roofs have it)
_dwp = _uvh(DW_OUTLINE_UV)
assert _dwp.is_valid
_bb = (DH_U > -40) & (DH_U < 95) & (DH_V > -10.0) & (DH_V < 60) & ~FIXED & ~_court & ~_strip
_jj, _ii = np.nonzero(_bb)
_dd = shapely.distance(_dwp, shapely.points(X[_jj, _ii], Y[_jj, _ii]))
_uu, _vv = DH_U[_jj, _ii], DH_V[_jj, _ii]
_w = np.clip(1 - (_dd - 3.0) / 7.0, 0, 1) * (((_uu < DW_UC - DW_WI) | (_uu > DW_UC + DW_WI)) * np.clip((_vv + 10.0) / 4.0, 0, 1) + (_vv > 14.0))     # (beside and under the wings)
_w = np.clip(_w, 0, 1)                         # (the nodes under the wings too, or the walls' foot dips between nodes)
DW_APRON = np.interp(_vv, [-10.4, 27.55], [DAEWOO['terrace'], DAEWOO_BACK['low']])
Hn[_jj, _ii] = Hn[_jj, _ii] * (1 - _w) + DW_APRON * _w
print('daewoo sides apron %.2f .. %.2f' % (DAEWOO['terrace'], DAEWOO_BACK['low']), 'nodes', int((_w > 0).sum()))
# 대우관 서쪽 옆길 (reference/고증/3.6 「서쪽 옆길」): the drive from the 상뜰's west side up the west wing to the back
# yard and its car park, the way the cars of 백양로 go (TRAFFIC below).  Kakao roadview of August 2008 (2381738 on the
# drive abreast of the 상뜰, 2381759 at the wing's north-west corner) has it climb evenly along the wing, a car's
# width and a low hedge strip off the wall, whose rusticated foot comes down to it, then turn along the hall's back
# into the yard.  The game had OSM's line 1.3 m off the wall (the wall stood in its east lane) and the side apron
# above start at the wing's front end, which stood the drive up 5 m in 9 m there.  So: the drive's middle DW_RD_OFF
# off the west wall, one grade from the 상뜰's drive to the yard's level at the back corner, the ground from the wall
# out to its west edge on that grade (the wall goes down to it: its base is the plaza's level), then level with the
# yard round the corner and along the lawn north of the hall's back apron to the car park's cross aisle.

DW_RD_OFF = 5.0
_ru = DAEWOO['u0'] - DW_RD_OFF
_yz_ = lambda u, v: DAEWOO_BACK['low']                       # (the low court's level)
DW_AISLE_V = 53.0                                    # (its end: the mouth of the underground car park in w1, DAEWOO_BACK)
# (its middle line; rounded off in TRAFFIC.  Along the wing in the hall's frame, DW_WEST_RD above; round the back in
# the yard's, as it was read)
_vj = DAEWOO['drive'][0] + 3.9                       # (where the terrace drive leaves it)
DW_DRIVE = [dh_xy(-16.5, -26.0), dh_xy(_ru, _vj), dh_xy(_ru, 24.8), dh_xy(_ru + 1.6, 31.0)] + \
    [dw_xy(*q_) for q_ in ((-9.0, 34.5), (2.5, 38.5), (10.5, 48.0), (16.5, 53.4), (23.5, DW_AISLE_V))]
_v0, _v1 = _vj, 24.8
_z0, _z1 = DAEWOO['terrace'], _yz_(_ru, _v1)
_side = (DH_V >= _v0) & (DH_V <= _v1) & (DH_U > _ru - 4.2) & (DH_U < np.where(DH_V < -9.9, DAEWOO['u0'] - 0.4, DAEWOO['u0'] + 5.2)) \
    & ~_court & ~_strip
Hn[_side] = _z0 + (_z1 - _z0) * (DH_V[_side] - _v0) / (_v1 - _v0)
FIXED[_side] = True
_zc = [_z1, DAEWOO_BACK['low'], DAEWOO_BACK['low']]
DW_OWN = _side | fix_strip(DW_DRIVE[2:6], _zc[0], _zc[1], 3.6) | fix_strip(DW_DRIVE[5:], _zc[1], _zc[2], 3.6) | DW_RD_OWN[0]
_free = shapely.contains_xy(LineString(DW_DRIVE).buffer(15.0), X, Y) & ~FIXED & ~near_buildings(1.0) & ~_m_yard
harmonic_fill(_free)
print('daewoo west drive along the wing %.2f -> %.2f m, %.1f %%; back %.2f -> %.2f; nodes %d, filled %d' % (
    _z0, _z1, 100 * (_z1 - _z0) / (_v1 - _v0), _zc[1], _zc[2], int(_side.sum()), int(_free.sum())))
# ---------------------------------------------------------------------------
# 찻길 (TRAFFIC, reference/고증/2.9): where 백양로's cars go on from the 삼거리.  They ran to the foot of the steps before
# 언더우드관 and vanished there.  Kakao's roadview car drove on in August 2008, December 2010 and April 2011: left at
# the 삼거리 up the drive past 스팀슨관's west side (2381781; 2011: 1017220216), north-east behind 언더우드관 to 한경길
# (2381767), up between 교육관 and 연희관's garden (2381722), past 연희관's west wing and the 상뜰's west side (2381738) and
# round 대우관's west wing (2381759) to the car park behind it, and back the same way: an asphalt drive of about 6 m with
# yellow edge lines and no centre line, two cars passing slowly.  The 2008 skyview has the same drive all the way.
# (The other fork, right at the 삼거리 past 용재관 towards 노천극장, is as real, 2381332 · 2381343; the game has 용재관's
# azalea bank over its first 30 m and unshaped ground beyond: left for later, 「남은 한계」.)
# So: one loop for the cars (web/src/main.js joins it to 백양로's two lanes at s_out): off the northbound lane, left
# through the kerb's gap, up the drive on its right-hand side, in by the car park's cross aisle, round the two aisles
# and out again, down the drive on the other side and right into the southbound lane.  The drive's middle is OSM's,
# rounded at the corners, held off the halls' walls (연희관's west wing stood 2.9 m from it) as far as the asphalt
# allows, and 대우관's west side as laid out above (DW_DRIVE).  Here its middle line (the ground under it is levelled
# across next); the lanes, the car park's round and the asphalt follow with the splat (TRAFFIC below).
# ---------------------------------------------------------------------------
def _fillet(pts, r):
    """a polyline with every corner rounded by an arc of radius r (one for all, or one for each point), as far as
    the two sides meeting there allow"""
    P_ = [np.array(q_, float) for q_ in pts]
    rr_ = list(r) if hasattr(r, '__len__') else [r] * len(P_)
    out_ = [P_[0]]
    for i_ in range(1, len(P_) - 1):
        u_, v_ = P_[i_ - 1] - P_[i_], P_[i_ + 1] - P_[i_]
        lu_, lv_ = np.linalg.norm(u_), np.linalg.norm(v_)
        u_, v_ = u_ / lu_, v_ / lv_
        ang_ = math.acos(float(np.clip(u_ @ v_, -1.0, 1.0)))             # (the angle between the two sides)
        if ang_ > math.pi - 0.02:
            out_.append(P_[i_])
            continue
        t_ = min(rr_[i_] / math.tan(ang_ / 2), 0.48 * lu_, 0.48 * lv_)
        r_ = t_ * math.tan(ang_ / 2)
        b_ = (u_ + v_) / np.linalg.norm(u_ + v_)
        o_ = P_[i_] + b_ * (r_ / math.sin(ang_ / 2))
        a0_, a1_ = (math.atan2(q_[1] - o_[1], q_[0] - o_[0]) for q_ in (P_[i_] + u_ * t_, P_[i_] + v_ * t_))
        da_ = (a1_ - a0_ + math.pi) % (2 * math.pi) - math.pi
        n_ = max(2, int(abs(da_) * r_ / 0.6) + 1)
        out_ += [o_ + r_ * np.array([math.cos(a0_ + da_ * k_ / n_), math.sin(a0_ + da_ * k_ / n_)]) for k_ in range(n_ + 1)]
    return out_ + [P_[-1]]


def _resample(pts, step):
    ls_ = LineString([tuple(q_) for q_ in pts])
    n_ = max(1, int(round(ls_.length / step)))
    return [np.array(ls_.interpolate(ls_.length * k_ / n_).coords[0]) for k_ in range(n_ + 1)]


TR_LANE, TR_LANE_BY = 1.35, ROAD['median'] + ROAD['lane'] * 0.5       # a lane's middle off the drive's, off 백양로's
TR_V = dict(by=11.0, drive=6.5, back=4.5, lot=2.8)                   # m/s: 백양로, the drive, 대우관's back, the car park
_wd = LineString([(39.8, 121.9), (34.2, 122.7), (28.2, 124.1), (24.2, 125.3), (19.6, 127.2), (14.2, 131.1)])
_jq = LineString([(24.2, 125.3), (14.2, 131.1)])                      # (the drive where it leaves the carriageway)
_jd = np.array(_jq.coords[1]) - np.array(_jq.coords[0])
_jx = LineString([tuple(np.array(_jq.coords[0]) - _jd * 2.0), _jq.coords[1]]).intersection(bline)
TR_SJ = float(bline.project(_jx))                                    # the corner of the two middle lines
TR_S0 = round(TR_SJ - 36.0, 1)                                        # the loop leaves 백양로's lanes here
_c_raw = [along_raw(TR_S0, 0.0)[:2], along_raw(TR_SJ - 16.0, 0.0)[:2], along_raw(TR_SJ + 0.4, 0.0)[:2],   # (through the kerb's gap, GAPS)
          (14.2, 131.1), (8.7, 136.9), (4.4, 143.6), (1.6, 149.5), (-2.0, 160.5), (-7.9, 178.7), (-12.9, 194.7), (-14.5, 204.6),
          (-2.3, 250.4), (0.4, 254.3), (18.8, 281.7), (27.1, 292.5), (40.0, 301.4),
          (45.5, 327.4), (51.7, 354.5), (50.7, 363.9), (54.7, 378.7), (61.7, 398.7), (66.6, 414.3), (71.8, 436.3)] + DW_DRIVE
_c_r = [14.0] * len(_c_raw)
_c_r[2] = 9.0                                                         # (the 삼거리: the inner lane turns on 7.5 m)
TR_CP = _resample(_fillet(_c_raw, _c_r), 1.0)
_halls_tr = unary_union([footprint(ways[w_], rng=w_ in BLD_SHAPE) for w_ in B if w_ in ways])   # (연희관 as the drive was laid by it)
_cls = LineString([tuple(q_) for q_ in TR_CP])
TR_KDW = int(round(_cls.project(Point(*DW_DRIVE[0]))))                 # (from here on laid out by hand: DW_DRIVE)
for k_ in range(1, TR_KDW):                                            # off the walls, at most 0.6 m (the asphalt's width)
    q_ = Point(*TR_CP[k_])
    d_ = _halls_tr.distance(q_)
    if d_ < 4.0:
        n_ = shapely.ops.nearest_points(_halls_tr, q_)[0]
        TR_CP[k_] = TR_CP[k_] + (TR_CP[k_] - np.array([n_.x, n_.y])) / max(d_, 1e-6) * min(4.0 - d_, 0.6)
for _ in range(3):                                                    # (the corners' ends and the push eased)
    TR_CP = [TR_CP[0]] + [(TR_CP[k_ - 1] + 2 * TR_CP[k_] + TR_CP[k_ + 1]) / 4 for k_ in range(1, len(TR_CP) - 1)] + [TR_CP[-1]]
TR_CP = _resample(TR_CP, 1.0)
TR_CENTRE = [tuple(np.round(q_, 2)) for q_ in TR_CP]
TR_CSS = np.arange(len(TR_CP)) * (LineString(TR_CENTRE).length / (len(TR_CP) - 1))
_ct = [(TR_CP[min(k_ + 1, len(TR_CP) - 1)] - TR_CP[max(k_ - 1, 0)]) for k_ in range(len(TR_CP))]
TR_CN = [np.array([-t_[1], t_[0]]) / np.linalg.norm(t_) for t_ in _ct]                    # (to the left)
TR_SJC = TR_SJ - TR_S0
TR_CO = np.interp(TR_CSS, [TR_SJC - 9.0, TR_SJC + 12.0], [TR_LANE_BY, TR_LANE])
TR_KBACK = int(round(LineString(TR_CENTRE).project(Point(*DW_DRIVE[2]))))               # 대우관's back corner
TR_CV = np.where(TR_CSS < TR_SJC - 12.0, TR_V['by'], np.where(np.arange(len(TR_CP)) < TR_KBACK, TR_V['drive'], TR_V['back']))
# The drive's ground, level across.  The cars stand on their four tyres (web/src/life.js Traffic: the ground under the
# two wheel tracks), and the 5 m grid laid the drive over the hillsides with the slope's own cross fall: a car leant
# 6 - 15 deg all the way up behind 스팀슨관 and 언더우드관, 22 deg at the bend behind 언더우드관, 5 - 11 deg along the
# 상뜰.  A drive is cut level across its slope: every grid node of a cell the wheel tracks pass over takes the height of
# the drive's middle abreast of it (its profile as it was, the grid's facets eased out), and the ground beside eases
# to it over the next 10 m.  The nodes others have set stay (FIXED: 한경길, the drive along 연희관's garden and the
# garden's own levels, the halls' aprons and the 상뜰), 백양로's own mesh, and the ground inside the halls' walls.
# What is left leans where such ground stands beside the drive at another height: abreast of 교육관's north yard
# (2.6 m under the drive) and 연희관's front road (1 m over it), printed below; the cars' lean is held to 7 deg there.
def tr_tilt():
    """the lean (pitch, roll in degrees) of a car on each lane along the drive, on the ground as it is now"""
    rows_ = []
    for sg_ in (-1.0, 1.0):
        for k_ in range(TR_K0, len(TR_CP) - 2):
            n_ = TR_CN[k_]
            t_ = np.array([n_[1], -n_[0]])
            c_ = TR_CP[k_] + n_ * sg_ * TR_CO[k_]
            h_ = [sample(Hn, NEAR_HALF, NEAR_STEP, *(c_ + t_ * a_ + n_ * b_)) for a_, b_ in ((1.33, 0.72), (1.33, -0.72), (-1.33, 0.72), (-1.33, -0.72))]
            rows_.append((sg_, k_, math.degrees(math.atan2((h_[0] + h_[1] - h_[2] - h_[3]) / 2, 2.66)),
                          math.degrees(math.atan2((h_[0] + h_[2] - h_[1] - h_[3]) / 2, 1.44))))
    return rows_


def tr_tilt_report(tag):
    rows_ = tr_tilt()
    rl_ = np.abs([r_[3] for r_ in rows_])
    pt_ = np.abs([r_[2] for r_ in rows_])
    print('traffic tilt (%s): roll max %.1f deg, over 4 deg on %d of %d m; pitch max %.1f deg, over 9 deg on %d m' % (
        tag, rl_.max(), int((rl_ > 4).sum()), len(rows_), pt_.max(), int((pt_ > 9).sum())))
    return rows_


TR_K0 = next(k_ for k_, q_ in enumerate(TR_CENTRE) if bline.distance(Point(*q_)) > ROAD_HALF + 1.0)     # (past 백양로's mesh)
tr_tilt_report('before')
_tz = np.array([sample(Hn, NEAR_HALF, NEAR_STEP, *q_) for q_ in TR_CENTRE[TR_K0:]])
_tzs = ndimage.gaussian_filter1d(_tz, 3.0, mode='nearest')
_te = np.clip(np.minimum(np.arange(len(_tz)), len(_tz) - 1 - np.arange(len(_tz))) / 8.0, 0, 1)       # (its ends as they are)
_tzs = _tz + (_tzs - _tz) * _te
_tls = LineString(TR_CENTRE[TR_K0:])
_cells = set()
for k_ in range(TR_K0, len(TR_CP)):
    for o_ in np.arange(-2.7, 2.71, 0.9):
        x_, y_ = TR_CP[k_] + TR_CN[k_] * o_
        _cells.add((int(math.floor((y_ + NEAR_HALF) / NEAR_STEP)), int(math.floor((x_ + NEAR_HALF) / NEAR_STEP))))
_nodes = sorted({(j_ + a_, i_ + b_) for j_, i_ in _cells for a_ in (0, 1) for b_ in (0, 1)})
_keep = (FIXED & ~DW_OWN) | near_buildings(0.3) | (dist < ROAD_HALF + 1.0)
TR_LEVEL = np.zeros(X.shape, bool)
for j_, i_ in _nodes:
    if not _keep[j_, i_]:
        Hn[j_, i_] = float(np.interp(_tls.project(Point(X[j_, i_], Y[j_, i_])), np.arange(len(_tzs)) * (_tls.length / (len(_tzs) - 1)), _tzs))
        TR_LEVEL[j_, i_] = True
FIXED[TR_LEVEL] = True
_free = shapely.contains_xy(_tls.buffer(13.0), X, Y) & ~FIXED & ~near_buildings(1.0) & (dist > ROAD_HALF + 1.0)
harmonic_fill(_free)
print('traffic: drive levelled across, nodes %d of %d (kept %d), eased beside %d' % (
    int(TR_LEVEL.sum()), len(_nodes), len(_nodes) - int(TR_LEVEL.sum()), int(_free.sum())))
TR_TILT = tr_tilt_report('after')
_run = None
for sg_, k_, pt_, rl_ in TR_TILT + [(0, 0, 0, 0)]:
    if abs(rl_) > 4 or abs(pt_) > 9:
        if _run is None or _run[0] != sg_ or k_ != _run[2] + 1:
            if _run:
                print('   lane %+d  %s .. %s  pitch %.0f .. %.0f  roll %.0f .. %.0f' % (_run[0], TR_CENTRE[_run[1]], TR_CENTRE[_run[2]], *_run[3:]))
            _run = [sg_, k_, k_, pt_, pt_, rl_, rl_]
        _run[2:] = [k_, min(_run[3], pt_), max(_run[4], pt_), min(_run[5], rl_), max(_run[6], rl_)]
    elif _run:
        print('   lane %+d  %s .. %s  pitch %.0f .. %.0f  roll %.0f .. %.0f' % (_run[0], TR_CENTRE[_run[1]], TR_CENTRE[_run[2]], *_run[3:]))
        _run = None
# ---------------------------------------------------------------------------
# 찻길, the ways the cars take (reference/고증/2.9 「바깥 길」).  The drive levelled above (behind 언더우드관, between
# 교육관 and 연희관's garden, past 연희관's west wing) is where Kakao's car drove in 2008, but not where the cars of 1997
# went: an alumnus remembers none on the drives right beside 언더우드관 and 연희관, on either side.  They went round by
# the outer roads, which the 1994 map draws as the ring round the old halls and which the 2008 skyview and Naver's
# street view car of September 2010 still have:
#  - east (TR_E): right at the 삼거리 up the fork past 용재관's north-west corner (YJ_DRIVE), between 아펜젤러관 and
#    노천극장 to the fork east of 한경길, on east of 성암관 and 대우관 별관 by the road under 청송대, and back sharp left
#    down the road along 대우관's north side to the car park behind it (Naver 2010-09: that road has a yellow centre
#    line and runs on west to the hall's north-west corner; the car park's mouths open off it);
#  - west (TR_W): left at the 삼거리 up the drive past 스팀슨관 as before, and at the island there round to the left
#    and down the road before 한경관 to the car park beside 핀슨관 (2008 skyview: a dozen cars south of the road).
# Each is a loop the game reads (TRAFFIC below): out on the right-hand side, into a stall of the car park, and back
# on the other side to 백양로 and the gate.  Here their middle lines and their ground: level across as the old drive's
# above, and along it one grade where the 5 m grid had steps (the east road rose 8 m in 15 m before the fork east of
# 한경길, and 10 m over the bend at 대우관's north-east corner, where the surface model has the wood's canopy).
# ---------------------------------------------------------------------------
def tr_line(raw, radii):
    cp_ = _resample(_fillet(raw, radii), 1.0)
    for k_ in range(1, len(cp_) - 1):                                   # off the walls, at most 0.6 m (as above)
        q_ = Point(*cp_[k_])
        d_ = _halls_tr.distance(q_)
        if d_ < 4.0 and bline.distance(q_) > ROAD_HALF + 1.0:
            n_ = shapely.ops.nearest_points(_halls_tr, q_)[0]
            cp_[k_] = cp_[k_] + (cp_[k_] - np.array([n_.x, n_.y])) / max(d_, 1e-6) * min(4.0 - d_, 0.6)
    for _ in range(3):
        cp_ = [cp_[0]] + [(cp_[k_ - 1] + 2 * cp_[k_] + cp_[k_ + 1]) / 4 for k_ in range(1, len(cp_) - 1)] + [cp_[-1]]
    cp_ = _resample(cp_, 1.0)
    ct_ = [(cp_[min(k_ + 1, len(cp_) - 1)] - cp_[max(k_ - 1, 0)]) for k_ in range(len(cp_))]
    cn_ = [np.array([-t_[1], t_[0]]) / np.linalg.norm(t_) for t_ in ct_]
    css_ = np.arange(len(cp_)) * (LineString([tuple(q_) for q_ in cp_]).length / (len(cp_) - 1))
    return cp_, cn_, css_


def tr_grade(cp_, cn_, k0, k1, grades, tag, also=None, tail=True, mine=None):
    """The ground under cp_[k0:k1] level across on the drive's own profile (as TR_LEVEL above).  grades: stretches of
    it on one grade, (point, height or None for what is there, point, height or None); also: a polygon whose nodes
    take the drive's height abreast of them too (a car park beside it); mine: a polygon in which the drive's nodes
    take its height though another rule has set them (a hall's yard or terrace levelled out as far as the drive: the
    drive keeps its grade and the bank stands between them), 4 m and more from the halls' walls."""
    seg_ = cp_[k0:k1]
    z_ = np.array([sample(Hn, NEAR_HALF, NEAR_STEP, *q_) for q_ in seg_])
    zs_ = ndimage.gaussian_filter1d(z_, 3.0, mode='nearest')
    ls_ = LineString([tuple(q_) for q_ in seg_])
    ss_ = np.arange(len(seg_)) * (ls_.length / (len(seg_) - 1))
    for pa_, za_, pb_, zb_ in grades:
        sa_, sb_ = ls_.project(Point(*pa_)), ls_.project(Point(*pb_))
        za_ = float(np.interp(sa_, ss_, zs_)) if za_ is None else za_
        zb_ = float(np.interp(sb_, ss_, zs_)) if zb_ is None else zb_
        m_ = (ss_ >= sa_ - 1e-6) & (ss_ <= sb_ + 1e-6)             # (the end nodes too, whatever the rounding)
        zs_[m_] = za_ + (zb_ - za_) * (ss_[m_] - sa_) / (sb_ - sa_)
    zs_ = ndimage.gaussian_filter1d(zs_, 2.0, mode='nearest')
    te_ = np.clip(np.minimum(np.arange(len(z_)), (len(z_) - 1 - np.arange(len(z_))) if tail else 1e9) / 8.0, 0, 1)   # (its ends as they are)
    zs_ = z_ + (zs_ - z_) * te_
    cells_ = set()
    for k_ in range(len(seg_)):
        for o_ in np.arange(-2.7, 2.71, 0.9):
            x_, y_ = seg_[k_] + cn_[k0 + k_] * o_
            cells_.add((int(math.floor((y_ + NEAR_HALF) / NEAR_STEP)), int(math.floor((x_ + NEAR_HALF) / NEAR_STEP))))
    nodes_ = {(j_ + a_, i_ + b_) for j_, i_ in cells_ for a_ in (0, 1) for b_ in (0, 1)}
    if also is not None:
        jj_, ii_ = np.nonzero(shapely.contains_xy(also, X, Y))
        nodes_ |= set(zip(jj_.tolist(), ii_.tolist()))
    keep_ = FIXED | near_buildings(0.3) | (dist < ROAD_HALF + 1.0)
    if mine is not None:
        keep_ &= ~(shapely.contains_xy(mine, X, Y) & ~near_buildings(4.0) & (dist > ROAD_HALF + 1.0))
    own_ = np.zeros(X.shape, bool)
    for j_, i_ in sorted(nodes_):
        z0_ = float(np.interp(ls_.project(Point(X[j_, i_], Y[j_, i_])), ss_, zs_))
        if not keep_[j_, i_]:
            Hn[j_, i_] = z0_
            own_[j_, i_] = True
        elif abs(Hn[j_, i_] - z0_) > 0.4 and dist[j_, i_] > ROAD_HALF + 1.0:
            print('   kept (%.0f, %.0f) at %.2f, the drive %.2f%s' % (X[j_, i_], Y[j_, i_], Hn[j_, i_], z0_,
                                                               '' if FIXED[j_, i_] else ' (a hall)'))
    FIXED[own_] = True
    free_ = shapely.contains_xy(ls_.buffer(13.0), X, Y) & ~FIXED & ~near_buildings(1.0) & (dist > ROAD_HALF + 1.0)
    harmonic_fill(free_)
    g_ = np.gradient(zs_, ss_) * 100
    print('traffic %s: %.0f m levelled across, nodes %d of %d, eased beside %d; %.2f -> %.2f m, grade %.0f .. %.0f %%' % (
        tag, ls_.length, int(own_.sum()), len(nodes_), int(free_.sum()), zs_[0], zs_[-1], g_.min(), g_.max()))
    return own_


def tr_tilt_of(cp_, cn_, co_, k0, tag):
    rl_, pt_ = [], []
    for sg_ in (-1.0, 1.0):
        for k_ in range(k0, len(cp_) - 2):
            n_ = cn_[k_]
            t_ = np.array([n_[1], -n_[0]])
            c_ = cp_[k_] + n_ * sg_ * co_[k_]
            h_ = [sample(Hn, NEAR_HALF, NEAR_STEP, *(c_ + t_ * a_ + n_ * b_)) for a_, b_ in ((1.33, 0.72), (1.33, -0.72), (-1.33, 0.72), (-1.33, -0.72))]
            pt_.append(abs(math.degrees(math.atan2((h_[0] + h_[1] - h_[2] - h_[3]) / 2, 2.66))))
            rl_.append(abs(math.degrees(math.atan2((h_[0] + h_[2] - h_[1] - h_[3]) / 2, 1.44))))
    print('traffic tilt %s: roll max %.1f deg, over 4 deg on %d of %d m; pitch max %.1f deg, over 9 deg on %d m' % (
        tag, max(rl_), int((np.array(rl_) > 4).sum()), len(rl_), max(pt_), int((np.array(pt_) > 9).sum())))
    n_ = len(cp_) - 2 - k0
    bad_ = [k_ for k_ in range(2 * n_) if rl_[k_] > 4 or pt_[k_] > 9]
    run_ = []
    for k_ in bad_ + [None]:
        if run_ and (k_ is None or k_ != run_[-1] + 1 or k_ == n_):
            a_, b_ = run_[0], run_[-1]
            print('   lane %+d  (%.0f, %.0f) .. (%.0f, %.0f)  pitch max %.0f  roll max %.0f' % (
                -1 if a_ < n_ else 1, *cp_[k0 + a_ % n_], *cp_[k0 + b_ % n_], max(pt_[a_:b_ + 1]), max(rl_[a_:b_ + 1])))
            run_ = []
        if k_ is not None:
            run_.append(k_)


# east
_ej = np.array([201.4, 571.3])                                         # the two roads' corner north-east of 대우관
_eh = (_ej - np.array([191.1, 550.1])) / math.dist((191.1, 550.1), _ej)
TR_E_AISLES = DAEWOO_BACK['aisles']                                    # the upper car park's aisles (u)
_e_raw = [along_raw(TR_S0, 0.0)[:2], along_raw(TR_SJ - 16.0, 0.0)[:2], along_raw(TR_SJ - 1.5, 0.0)[:2],
          (46.6, 124.1), (51.5, 126.5), (63.3, 139.8), (69.1, 146.2), (73.7, 151.2), (87.0, 165.7), (94.5, 174.7), (104.0, 186.3),
          (135.1, 226.6), (148.6, 257.3), (150.7, 262.1), (154.1, 270.8), (156.3, 276.3), (168.5, 306.7), (171.4, 311.7),
          (177.3, 319.7), (191.2, 335.5), (206.0, 350.2), (212.6, 356.4), (207.7, 380.7), (188.1, 440.8), (183.0, 458.5),
          (179.6, 468.6), (178.2, 492.1), (181.8, 521.8), tuple(_ej - _eh * 36.0), tuple(_ej), (147.1, 547.2), (128.6, 537.2)]
_e_r = [12.0] * len(_e_raw)
_e_r[2], _e_r[21], _e_r[-3] = 9.0, 9.0, 6.0
TR_E, TR_EN, TR_ES = tr_line(_e_raw, _e_r)
_esj = TR_SJ - 1.5 - TR_S0
TR_EO = np.interp(TR_ES, [_esj - 9.0, _esj + 12.0], [TR_LANE_BY, TR_LANE])
TR_EK0 = next(k_ for k_, q_ in enumerate(TR_E) if bline.distance(Point(*q_)) > ROAD_HALF + 1.0)
_els = LineString([tuple(q_) for q_ in TR_E])
TR_EKH = int(round(_els.project(Point(*_ej))))                           # (about the sharp bend's middle)
TR_EV = np.where(TR_ES < _esj - 12.0, TR_V['by'], np.where(np.arange(len(TR_E)) < TR_EKH - 30, TR_V['drive'], TR_V['back']))
# (the road past the hall's east wing, the bend and the road north of the hall as the 1997 aerial photos' heights have
# them, reference/고증/3.6.2: the road climbs on to the bend, 9.6 m over the low court, and falls 12 % from it; the heights
# themselves 3.0 m under the photos', as the hall's floor is)
_zh = DAEWOO_BACK['low'] + 9.6
tr_tilt_of(TR_E, TR_EN, TR_EO, TR_EK0, 'east (before)')
# (아펜젤러관's back yard and 논지당's terrace are levelled out to the grid nodes under the road: there the road wins)
_emine = LineString([tuple(q_) for q_ in TR_E[int(_els.project(Point(87.0, 165.7))):int(_els.project(Point(154.1, 270.8))) - 12]]).buffer(7.5)
tr_grade(TR_E, TR_EN, TR_EK0, len(TR_E), [
    ((69.1, 146.2), UW_TOP, (110.0, 194.0), UW_TOP + 0.05),               # along the square at its level, past 아펜젤러관's yard
    ((110.0, 194.0), UW_TOP + 0.05, (168.5, 306.7), None),               # one grade up the hillside, through the fork east of 한경길
    ((168.5, 306.7), None, (206.0, 350.2), None),
    ((183.0, 458.5), None, (179.7, 491.3), DAEWOO_BACK['low'] + 6.0),      # up past the hall's east wing
    ((179.7, 491.3), DAEWOO_BACK['low'] + 6.0, tuple(TR_E[TR_EKH]), _zh),  # to the bend
    (tuple(TR_E[TR_EKH]), _zh, (181.1, 563.8), dwb_road_z((181.1, 563.8))),
    ((181.1, 563.8), dwb_road_z((181.1, 563.8)), (153.6, 551.6), dwb_road_z((153.6, 551.6))),      # down the road north of it
    ((153.6, 551.6), dwb_road_z((153.6, 551.6)), (147.1, 547.2), dwb_road_z((147.1, 547.2))),
    ((147.1, 547.2), dwb_road_z((147.1, 547.2)), tuple(TR_E[-1]), dwb_road_z(tuple(TR_E[-1])))], 'east', tail=False, mine=_emine)
tr_tilt_of(TR_E, TR_EN, TR_EO, TR_EK0, 'east (after)')
# west
_w_raw = [along_raw(TR_S0, 0.0)[:2], along_raw(TR_SJ - 16.0, 0.0)[:2], along_raw(TR_SJ + 0.4, 0.0)[:2],
          (14.2, 131.1), (8.7, 136.9), (4.4, 143.6), (1.6, 149.5), (-2.0, 160.5), (-7.9, 178.7), (-12.9, 194.7), (-14.5, 204.6),
          (-19.6, 216.5), (-21.3, 217.4), (-24.2, 218.4), (-27.7, 218.6), (-30.1, 218.0), (-33.7, 217.2), (-36.1, 210.7),
          (-43.3, 186.0), (-52.4, 154.8), (-56.6, 145.5), (-62.2, 138.4), (-70.0, 134.0), (-101.0, 132.1), (-108.0, 130.4)]
_w_r = [12.0] * len(_w_raw)
_w_r[2] = 9.0
for k_ in range(11, 18):
    _w_r[k_] = 5.5
TR_W, TR_WN, TR_WS = tr_line(_w_raw, _w_r)
TR_WO = np.interp(TR_WS, [TR_SJC - 9.0, TR_SJC + 12.0], [TR_LANE_BY, TR_LANE])
_wls = LineString([tuple(q_) for q_ in TR_W])
TR_WK1 = int(round(_wls.project(Point(-14.5, 204.6)))) - 4               # (the drive up to the island: levelled above)
TR_WV = np.where(TR_WS < TR_SJC - 12.0, TR_V['by'], np.where(np.arange(len(TR_W)) < int(round(_wls.project(Point(-62.2, 138.4)))),
                                                             TR_V['drive'], TR_V['back']))
# its car park, south of the road beside 핀슨관: one row of stalls nose in off the road (PINSON_LOT, the row below)
_pt = np.array([-101.0 + 70.0, 132.1 - 134.0])
_pt = _pt / np.linalg.norm(_pt)                                          # along the road, westwards
_pn = np.array([-_pt[1], _pt[0]])                                        # to the left of it: south
PINSON = dict(o=np.array([-70.0, 134.0]) + _pt * 4.0, t=_pt, n=_pn, k=10, w=2.6, d=5.0, off=3.5)
PINSON_LOT = Polygon([tuple(PINSON['o'] + _pt * a_ + _pn * b_) for a_, b_ in ((-1.5, 2.0), (PINSON['k'] * 2.6 + 1.5, 2.0),
                                                                           (PINSON['k'] * 2.6 + 1.5, 9.3), (-1.5, 9.3))])
tr_tilt_of(TR_W, TR_WN, TR_WO, TR_WK1, 'west (before)')
tr_grade(TR_W, TR_WN, TR_WK1, len(TR_W), [((-16.5, 209.3), None, (-36.1, 210.7), None),         # (round the island on one grade)
                                          ((-62.2, 138.4), None, tuple(TR_W[-1]), sample(Hn, NEAR_HALF, NEAR_STEP, -62.2, 138.4) + 0.9)],
         'west', also=PINSON_LOT, tail=False)
tr_tilt_of(TR_W, TR_WN, TR_WO, TR_WK1, 'west (after)')
# 상뜰's west drive (OSM 6 m service road, (71.8, 436.3) -> (66.6, 414.3)): Kakao roadview of August 2008 (pano 2381737,
# on the drive abreast of the 상뜰's west lawn; 2026 the same stones) shows the lawn along its east side held up by a
# bank of natural boulders behind the granite kerb, shrubs between them, from the mouth of the 상뜰's west walk to the
# corner where the footway to 연희관 leaves, and on round it.  Read off the panorama (camera 2.5 m up, from a passer-by):
# 0.6 - 0.7 m high at the walk, 0.8 - 1.0 m at the corner; one or two courses of grey boulders 0.5 - 1 m long.
# The 5 m grid cannot hold a bank: blender/landmarks.py sang_stone_bank builds the boulders on the kerb line and a
# grass berm behind them at the top.  pts: [x, y on the line behind the kerb (the lawn on the left going along),
# x, y of the drive's edge there (the bank stands that high over it), height]
_kd, _ke = np.array([-0.2301, -0.9732]), np.array([0.9732, -0.2301])     # the drive southwards, its east side
_fd, _fn = np.array([0.9685, -0.2491]), np.array([0.2491, 0.9685])       # the footway eastwards, its north side
_kc0 = np.array([71.8, 436.3])                                           # the drive's middle at the walk
_kQ = np.array([70.04, 414.96])           # where the kerb lines (3.2 m out of the drive, 1.5 m out of the footway) meet
_kr = 2.4
_kt = _kr * math.tan(math.acos(float(_kd @ _fd)) / 2)                    # the corner rounded, radius _kr
_kO = _kQ - _kd * _kt + _ke * _kr                                        # (the arc's centre, on the lawn side)
_kb = []
_s_end = float((_kQ - _kd * _kt - _kc0 - _ke * 3.2) @ _kd)
for _s in np.linspace(2.0, _s_end, int(round(_s_end - 2.0)) + 1):        # along the drive, from the walk's mouth
    _c = _kc0 + _kd * _s
    _kb.append([*(_c + _ke * 3.2), *(_c + _ke * 2.8), 0.6 + 0.4 * (_s - 2.0) / (_s_end - 2.0)])
_a0, _a1 = math.atan2(*(-_ke)[::-1]), math.atan2(*(-_fn)[::-1])
for _k in range(1, 4):                                                   # round the corner
    _a = _a0 + (((_a1 - _a0 + math.pi) % (2 * math.pi)) - math.pi) * _k / 4
    _p = _kO + _kr * np.array([math.cos(_a), math.sin(_a)])
    _kb.append([*_p, *(_p + (_p - _kO) / _kr * 0.4), 1.0])
for _t in np.linspace(0.0, 4.0, 5):                                      # and on along the footway
    _p = _kQ + _fd * (_kt + _t)
    _kb.append([*_p, *(_p - _fn * 0.4), 1.0])
DAEWOO['bank'] = [[round(float(v), 2) for v in q] for q in _kb]
print('상뜰 west drive boulder bank: %d points, %.1f m'
      % (len(_kb), sum(math.dist(a_[:2], b_[:2]) for a_, b_ in zip(_kb, _kb[1:]))))

buildings = []
campus_polys = []
_cp_rng = {}           # (the halls BLD_MOVE moves, as the random planting first read them: campus_zone_rng)
for wid, (style, lv, label) in B.items():
    wv = ways.get(wid)
    if not wv:
        print('missing', wid, label)
        continue
    poly = Polygon(FOOTPRINT_1997[wid]) if wid in FOOTPRINT_1997 else footprint(wv)
    campus_polys.append(poly)
    if wid in BLD_MOVE:
        _cp_rng[len(campus_polys) - 1] = footprint(wv, rng=True)
    hs = [ground_h(x, y) for x, y in poly.exterior.coords]
    fh = FLOOR_H_AT.get(wid, FLOOR_H.get(style, 4.0))
    buildings.append(dict(id=wid, name=label, style=style, levels=lv,
                          height=round(lv * fh + (1.2 if not style.startswith('lm') else 0), 2),
                          base=round(min(hs), 2), top_ground=round(max(hs), 2),
                          footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]]))
for b_ in buildings:                    # (음악관's floors: MUSIC_BASE, from before its fronts were levelled)
    b_['base'] = MUSIC_BASE.get(b_['id'], b_['base'])
    if b_['id'] == 163525865:           # (중앙도서관: the foot of its terrace's flight; the floor is LIB_FLOOR)
        b_['base'] = LIB_FOOT

# 용재관 (1957 - 2013; 경영관 has stood on its site since 2015, so it is not in OSM; reference/고증.md 3.13).  From
# reference/용재관.jpg (April, 1990s: from 언더우드관 over the Underwood statue's back, looking SSE, a long lens), the
# mid-1950s photo of the first library building (slc.bc.ca/yonsei, from the 백양로 side) and the 1994 / 1997 aerial
# photos (from the south):
# - the stair tower, six storeys: its fin face to 백양로 (west), paired small windows on its north side
# - north of it, set back from that face, a three-storey wing, its long front to 백양로; the entrance porch and its
#   flat canopy in the corner between the two
# - east of the tower a three-storey block along the south (its roof at the wing's height), and behind the wing,
#   across a courtyard 5 m wide open to the north, a five-storey gabled block: the whole a U open to the north
# The frame is square to 백양로 (u east-south-east, v north-north-east, o the tower's south-west corner).  The plan is
# the 1997-07-28 vertical aerial photos' (reference/고증/3.13; tools/aerial97.py, two frames from the west and the
# east): each block's roof edges where the two frames agree, at the roof height that makes them agree (the tower's
# slab 71 m, the wing and the south block 59.5 m, the gabled block 65.5 m on the photos' datum), less the eaves.  The
# tower stands 8.4 m south-east of where photo A's camera had put it (its white roof in the 2008 skyview agrees to
# 2 m).  The whole stands on the azalea hill (진달래동산) 5 m over the 삼거리, as the ground photo and photo A put
# it (the terrain grid there is the 2010s dig for 경영관's basements): 6.2 m over 백양로's section abreast of where the
# tower was first put (52.0 m on the old terrain; the aerial photos give the floor 5 - 7 m over the road there).
YONGJAE = dict(o=(73.75, 98.77), ang=math.radians(-14.5), floor=round(prof_h(s_at(67.2, 104.1)) + 6.2, 2), fh=3.6, parts=[
    (990001, 'lm:yongjae', 6, (0.0, 10.5, 0.0, 10.4)),       # tower: u0, u1, v0, v1 (u0 = the fin face)
    (990002, 'lm:none', 3, (2.0, 15.7, 10.4, 43.0)),         # north wing
    (990003, 'lm:none', 5, (21.7, 37.4, 22.0, 43.0)),        # east block (gabled), behind the courtyard
    (990004, 'lm:none', 3, (15.7, 37.4, 1.9, 15.5)),         # south block, east of the tower
    (990005, 'lm:none', 3, (10.5, 15.7, 1.9, 10.4)),         # the link between the tower and the south block
    (990006, 'lm:none', 1, (-0.5, 2.0, 10.4, 14.8)),         # entrance porch
])
# (the frame as first put, by photo A's camera: the random planting's clearings are laid on it, so that the rest of
# the campus keeps its trees: YJ_PAD_RNG, YJ_BANK_RNG)
YONGJAE_RNG = dict(o=(67.2, 104.1), ang=math.radians(-15.0))


def yongjae_poly(u0, u1, v0, v1, fr=None):
    (ox, oy), a = (fr or YONGJAE)['o'], (fr or YONGJAE)['ang']
    c, s_ = math.cos(a), math.sin(a)
    return Polygon([(ox + u * c - v * s_, oy + u * s_ + v * c) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))])


def yj_xy(u, v):
    (ox, oy), a = YONGJAE['o'], YONGJAE['ang']
    return (ox + u * math.cos(a) - v * math.sin(a), oy + u * math.sin(a) + v * math.cos(a))


# its ground: level at the floor round the building (wider on the 백양로 and north sides, where the walk and the
# porch flight are), the 진달래동산 bank a smooth fill from there to the ground around (not into the old amphitheater's
# bowl, nor 백양로)
# (the 삼거리's east fork, reference/고증/2.9: the drive up past the hall's north-west corner towards 노천극장 is as old
# as the hall, on OSM's line in the 2008 and 2010 skyviews and under Naver's car of September 2010; the level ground
# stops 2 m short of its asphalt and the azalea bank comes down to it)
YJ_DRIVE = LineString([(46.6, 124.1), (51.5, 126.5), (63.3, 139.8), (69.1, 146.2), (73.7, 151.2), (87.0, 165.7)])
# (the 1997 aerial photos, reference/고증/3.13: a car park on the level ground before the north walls, nine or ten cars
# in it, entered from the drive to 노천극장 that leaves the east fork north of it (YJ_BRANCH: ground only, no traffic))
YJ_LOT = Polygon([yj_xy(0.0, 42.0), (86.5, 147.5), (90.0, 152.5), (94.5, 157.0), (99.0, 155.5), (98.5, 146.5), (106.0, 144.0),
                  (119.0, 140.5), yj_xy(39.0, 42.0)])
YJ_BRANCH = LineString([(85.5, 163.0), (92.0, 160.0), (100.0, 158.0), (108.0, 156.8), (116.0, 155.2), (122.5, 154.5)])
YJ_PAD = unary_union([yongjae_poly(-7.0, 41.0, -3.0, 46.0), YJ_LOT.buffer(1.0)]).difference(
    YJ_DRIVE.buffer(5.0)).difference(YJ_BRANCH.buffer(4.5))
YJ_PAD_RNG = unary_union([yongjae_poly(-7.0, 32.0, -2.0, 43.0, YONGJAE_RNG),
                          yongjae_poly(-1.0, 42.0, -14.5, 1.0, YONGJAE_RNG)]).difference(YJ_DRIVE.buffer(5.0))
_ypad = shapely.contains_xy(YJ_PAD, X, Y) & (dist > ROAD_HALF + 4)
Hn[_ypad] = YONGJAE['floor']
FIXED[_ypad] = True
_yring = shapely.contains_xy(YJ_PAD.buffer(15.0), X, Y) & ~_ypad & ~FIXED & (dist > ROAD_HALF + 4) & \
    ~near_buildings(1.0) & (np.hypot(X - AMPH['cx'], Y - AMPH['cy']) > 48.0)
harmonic_fill(_yring)
print('yongjae pad', YONGJAE['floor'], 'nodes', int(_ypad.sum()), 'bank', int(_yring.sum()))
YONGJAE_BUILDINGS = []
for pid, style, lv, uv in YONGJAE['parts']:
    poly = yongjae_poly(*uv)
    hs = [ground_h(x, y) for x, y in poly.exterior.coords]
    YONGJAE_BUILDINGS.append(dict(id=pid, name='용재관', style=style, levels=lv, height=round(lv * YONGJAE['fh'], 2),
                                  base=YONGJAE['floor'], top_ground=round(max(hs), 2),
                                  footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]],
                                  frame=dict(o=YONGJAE['o'], ang=round(YONGJAE['ang'], 5), uv=uv)))
# The campus's random planting, cars and pavement decals each draw from one stream, each draw depending on whether
# the spots before were clear of the halls and their aprons: till they are placed, the halls list carries
# 용재관's outline as it was before (three boxes on the old ground), so that the rest of the campus keeps its
# trees; the outline above takes its place after (YONGJAE_BUILDINGS below), with its own ground and planting.
_yo, _ya = (74.0, 124.0), math.radians(20)
YONGJAE_SCATTER = []
for _pid, _uv in ((990001, (-3.2, 3.2, -4, 3.5)), (990002, (3.2, 34, -11, 1)), (990003, (-2, 36, -27, -11))):
    _pts = [(_yo[0] + u * math.cos(_ya) - v * math.sin(_ya), _yo[1] + u * math.sin(_ya) + v * math.cos(_ya))
            for u, v in ((_uv[0], _uv[2]), (_uv[1], _uv[2]), (_uv[1], _uv[3]), (_uv[0], _uv[3]))]
    campus_polys.append(Polygon(_pts))
    YONGJAE_SCATTER.append(dict(id=_pid, name='용재관', style='lm:none', levels=3, height=10.8, base=YONGJAE['floor'],
                                top_ground=YONGJAE['floor'], footprint=[[round(x, 2), round(y, 2)] for x, y in _pts]))
buildings += YONGJAE_SCATTER
# its walk: from the canopy north-north-west down the bank to the east fork (blender/landmarks.py yongjae: its flight
# where it leaves the level ground)
_wd = np.array([-7.0, 9.0]) / math.hypot(7.0, 9.0)
_wl = LineString([yj_xy(-4.0, 22.8), yj_xy(*(np.array([-4.0, 22.8]) + _wd * 60.0))]).difference(YJ_DRIVE.buffer(3.5))
_wl = _wl.geoms[0] if hasattr(_wl, 'geoms') else _wl
YJ_WALK = [yj_xy(-1.6, 19.3), yj_xy(-4.0, 22.8), tuple(_wl.coords[-1])]


def yj_gone(p_):
    """OSM's walks over 용재관's ground (they go round the 2015 경영관; left out after the random draws)."""
    return p_['kind'] in ('footway', 'path', 'steps', 'pedestrian') and len(p_['pts']) > 1 and \
        LineString(p_['pts']).intersects(YJ_PAD.buffer(-1.0))

# Halls on the 1990 · 1994 · 1995 campus maps that OSM no longer has (reference/1990_캠퍼스_지도.png,
# 1994_캠퍼스_지도.jpg, 1995_캠퍼스_지도.jpg; reference/고증.md).  Behind (west of) 중앙도서관, where
# 삼성학술정보관 stands now: 23 어학당, a long three-storey hall curved like a bow, its convex side to the west and
# south-west, and 24 장기원 기념관, a four-storey block across the library's axis with a rounded west end and a low
# round hall at its south-west foot (the 1994 map draws both; 서울신문 1996.9.3: classes moved to the temporary rooms
# of the 기념관 "도서관 뒤쪽" that September).  The 한국어학당 left the bow-shaped hall for its own building in April
# 1991 (yonsei.ac.kr/sc/349); from 1992 it was 연구관, the three-storey home of 연세춘추 and the campus broadcasters,
# pulled down with 장기원 기념관 (1972, 「한국 최초의 교수 기념관」) when 학술정보관 broke ground in 2005 (연세춘추
# 2006.11.4).  12 청경관, a student cafeteria, low at the foot of a crescent of planting south-west of 유억겸 기념관
# and west of 언더우드관: the triangle between the three drives there (gone in the autumn of 1998, when 청경관 moved
# into 제2인문관: 연세춘추 1999.3.8).  (16 요업관, the other cafeteria, stood behind 연희관 where 대우관's 상뜰 was
# laid out in 1996.)
def arc_poly(c, r0, r1, a0, a1, n=12):
    out = [(c[0] + r1 * math.cos(math.radians(a0 + (a1 - a0) * k / n)), c[1] + r1 * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
           for k in range(n + 1)]
    inn = [(c[0] + r0 * math.cos(math.radians(a1 - (a1 - a0) * k / n)), c[1] + r0 * math.sin(math.radians(a1 - (a1 - a0) * k / n)))
           for k in range(n + 1)]
    return Polygon(out + inn)


def block_poly(c, u, hl, hw, round_end=0.0, n=8):
    """a rectangle along u (centre c, half length hl, half width hw), its -u end rounded (a half circle) if round_end"""
    u = np.array(u) / np.linalg.norm(u)
    v = np.array([-u[1], u[0]])
    c = np.array(c)
    pts = [c + u * hl - v * hw, c + u * hl + v * hw, c - u * hl + v * hw]
    if round_end:
        for k in range(1, n):
            a = math.pi / 2 + math.pi * k / n
            pts.append(c - u * hl + (u * math.cos(a) + v * math.sin(a)) * hw)
    pts.append(c - u * hl - v * hw)
    return Polygon([tuple(p) for p in pts])


def med_poly(uv, tilt=0.0):
    """의료원's halls as read off the 1997 aerial photos: corners (u, v) on a grid 43 degrees round from east about
    (150, -250), u north-east along the halls, v north-west across them; turned tilt degrees about their middle"""
    uv = np.array(uv, float)
    c_ = (uv.min(0) + uv.max(0)) / 2
    t_ = math.radians(tilt)
    uv = (uv - c_) @ np.array([[math.cos(t_), math.sin(t_)], [-math.sin(t_), math.cos(t_)]]) + c_
    a_ = math.radians(43.0)
    return Polygon([(round(150.0 + math.cos(a_) * u_ - math.sin(a_) * v_, 2), round(-250.0 + math.sin(a_) * u_ + math.cos(a_) * v_, 2))
                    for u_, v_ in uv])


def med_rect(u0, u1, v0, v1, tilt=0.0):
    return med_poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], tilt)


_lib_u = np.array([0.2544, 0.9671])                   # 중앙도서관's long axis
_med_u, _med_v = (0.755, 0.656), (-0.656, 0.755)       # 의료원's grid (its halls' long and short axes)
_jk = np.array([-150.0, -25.0])
OLD_HALLS = [
    (990010, '연구관', 'white', 3, arc_poly((-147.0, 18.0), 30.0, 40.0, 165.0, 230.0)),
    (990011, '장기원 기념관', 'white', 4, block_poly(_jk, (_lib_u[1], -_lib_u[0]), 10.0, 7.0, round_end=True)),
    (990012, '', 'white', 2, Point(*(_jk + np.array([_lib_u[1], -_lib_u[0]]) * -14.0 - _lib_u * 12.0)).buffer(7.0, 3)),
    (990013, '청경관', 'white', 2, block_poly((20.0, 266.0), (0.557, 0.830), 8.0, 4.5)),
    # 본교 (1997 확인; reference/고증.md 3.1.1): 학군단 (45 학생군사교육단 on the 1990 · 1995 maps, at the west end of the
    # 육상경기장; 1971 지하 1 · 지상 2층, the third floor 1983), still standing west of 대운동장 (brick, concrete floor bands
    # and a brick chimney in the 2010 roadview): its roof from the Kakao skyview.  The 경영학교실단 south wing and the
    # low front and hall between the wings (LATE_FOOTPRINT_1997): its one storey raised over a half-sunk one, the
    # front door at the head of a flight of thirteen risers (BK_FRONT_BASE).
    (990020, '학군단', 'brick', 3, Polygon([(-523.9, -176.1), (-514.7, -166.8), (-493.5, -188.5), (-507.0, -201.0)])),
    (990021, '경영학교실단', 'white', 5, Polygon([(-81.36, 48.43), (-24.1, 33.19), (-20.74, 45.64), (-78.0, 60.87)])),
    (990022, '경영학교실단', 'white', 2, Polygon([(-57.62, 55.45), (-20.74, 45.64), (-4.6, 105.49), (-14.58, 108.14),
                                             (-18.23, 94.69), (-45.12, 101.84)])),
    # 의료원 (1990 · 1995 지도, 1990년 무렵 항공 사진; reference/고증.md 3.1.2): 30 외래진료소 (on the 연세암병원 site),
    # 29 의학관 (의과대학 본관, standing still but not in OSM: its roof from the Kakao skyview), 54 의료원 종합관 (north-
    # east of 의과대학 신관 by 성산로, where the 2008 종합관 is), 36 선우학사 · 37 간호학관 · 38 향난숙사 (on the 2005
    # 세브란스병원 site) and 34 특별병동 (어린이병원 since 2006, 지상 10층).  On the quarter's grid (_med_u), placed with
    # the aerial photo's camera (tools/photofit), which puts the halls still standing there 35 ~ 95 px east of the photo.
    # Their outlines since from the vertical aerial photos of 28 July 1997 (med_poly; reference/고증/3.1.2 「1997년 7월
    # 수직 항공사진」), each roof on its own height's plane in the frames from both sides (27/17, 26/16):
    # - 외래진료소: the comb of four gabled wings and its head, 46 x 73 m (the 2008 skyview's roof too), 12 - 15 m
    #   south-east of the box it had
    # - 선우학사 · 간호학관: two gabled three-storey halls 54 x 18 m and 56 x 15 m, 28 m apart; 향난숙사 the short one
    #   south-east of 간호학관's east half (half under trees: 25 x 20 m, within 3 m)
    # - 의료원 종합관: the slab along 성산로 south-east of them, 83 x 19 m, its flat roof at 58.0 m: four rows of
    #   windows (3.75 m apart) over the car park north-west of it (41.5 m), a floor or two more down the slope to 성산로
    # - 특별병동: the slab 71 x 15 m, 5 - 9 m east and 2 m north of OSM's 어린이병원 (as Kakao's outline is)
    (990030, '외래진료소', 'white', 3, med_rect(-129.0, -83.0, -26.4, 46.5)),
    (990031, '의과대학', 'white', 5, block_poly((140.5, -333.75), (0.705, 0.710), 59.0, 9.0)),
    (990032, '의료원 종합관', 'white', 5, med_rect(3.0, 86.0, -97.2, -78.4, -0.7)),
    (990033, '선우학사', 'white', 3, med_rect(73.8, 127.5, -17.1, 0.6, -0.5)),
    (990034, '간호학관', 'white', 3, med_rect(73.0, 128.8, -44.6, -29.6, -0.9)),
    (990035, '향난숙사', 'white', 3, med_rect(72.5, 97.0, -74.0, -54.5, -0.7)),
    (990036, '특별병동', 'white', 10, med_rect(38.2, 108.8, 48.6, 63.85, -1.1)),
    # and in those photos, not in the game before (at the list's end: blender/build.py's draws for the rows above keep
    # their order): 의과대학 신관 (1973, four storeys under a gabled roof then; two more in 2003) along 성산로, 82 x 22 m
    # (Kakao's outline within 1 m); the two-storey block against 종합관's north-west side; the low wing at 특별병동's
    # south-west end (part of OSM's outline); an L of two storeys north of 선우학사, across the road from 재활병원
    # (on the 2005 세브란스병원 site; its name not found)
    (990037, '의과대학', 'white', 4, med_rect(-83.2, -1.4, -115.2, -93.4, -0.5)),
    (990038, '', 'white', 2, med_rect(39.0, 59.0, -78.4, -68.0, -0.7)),
    (990039, '', 'white', 1, med_rect(39.0, 59.0, 33.0, 47.5, -1.1)),
    (990040, '', 'white', 2, med_poly([(135.0, 11.0), (171.8, 11.0), (171.8, -1.8), (184.6, -1.8), (184.6, 28.6), (135.0, 28.6)])),
    # 과학관 (SCI above): the low fan-shaped hall in the corner north-west of the link and the low block against the
    # south-west wing's north face, both on the yard
    (990060, '과학관', 'white', 1, Polygon([sci_xy(SCI['fan']['c'][0] + SCI['fan']['r'] * math.cos(math.radians(a_)),
                                                 SCI['fan']['c'][1] + SCI['fan']['r'] * math.sin(math.radians(a_)))
                                          for a_ in range(90, 181, 10)]
                                         + [sci_xy(SCI['fan']['c'][0] - SCI['fan']['r'], SCI['fan']['south']),
                                            sci_xy(SCI['fan']['c'][0], SCI['fan']['south'])])),
    (990061, '과학관', 'white', 1, sci_poly([(SCI['annex'][0], SCI['annex'][2]), (SCI['annex'][1], SCI['annex'][2]),
                                            (SCI['annex'][1], SCI['annex'][3]), (SCI['annex'][0], SCI['annex'][3])])),
    # 연구관's north block (JK above), a storey over the bar
    (990014, '연구관', 'white', 4, block_poly(JK_O + JK_A * 29.0, JK_A, 8.0, 8.5)),
    # 어린이생활지도연구원 in 1997 (GONE_1997 above): the gabled hall and the small flat-roofed one on the site of the
    # 2002 hall, the square hall north-west of them
    (990050, '어린이생활지도연구원', 'house', 1, block_poly((313.0, 59.5), (0.988, 0.153), 9.0, 6.5)),
    (990051, '어린이생활지도연구원', 'white', 1, block_poly((332.5, 60.5), (0.988, 0.153), 4.5, 4.5)),
    (990052, '어린이생활지도연구원', 'white', 2, block_poly((293.5, 89.5), (0.819, 0.574), 7.5, 7.5)),
]
# (the 의료원 rows as the trees were first cleared round them, before the 1997 aerial photos: the clearing still asks
# these, so that the list of trees keeps its order; None: a hall that was not there to clear for)
MED_SITES_RNG = {
    990030: block_poly((61.0, -301.0), _med_v, 35.0, 20.0),
    990032: Polygon([(205.0, -300.0), (227.6, -325.4), (238.8, -315.4), (216.2, -290.0)]),
    990033: block_poly((224.0, -226.0), _med_u, 18.0, 6.0),
    990034: block_poly((240.4, -244.9), _med_u, 18.0, 6.0),
    990035: block_poly((256.8, -263.8), _med_u, 18.0, 6.0),
    990036: footprint(ways[324328432]),
    990037: None, 990038: None, 990039: None, 990040: None,
    429079067: None,
}
# 연구관 · 장기원 기념관 as the 1997-07-28 aerial photos have them (reference/고증/3.15-3.17; frames 26/15, 26/16 and
# 27/17, the roofs read on their own planes).  The halls above (990010 - 990012, from the maps' drawing) stay for the
# planting; these go in after it (LATE_FOOTPRINT_1997):
# - 연구관: a straight bar 11.5 m wide with a rounded south end, 51.5 m from its tip north-north-east to a square
#   block a storey higher (990014 above); its roof 56 m on the photos' datum, the yard west of it 49 - 50 m, the
#   ground east of it 45 - 46 m (three storeys on that side, as 연세춘추 has it)
# - the round hall (the maps' drum; 장기원 기념관's 원탁회의실): a roof 15 m across at 49 - 51 m, 9.5 m north of where
#   the maps' drawing had put it
# - 장기원 기념관's block: no four-storey slab; a flat roof at 46 m from the round hall's east side north and south,
#   8.5 m over the road past the library's back (two storeys on that side), under the trees' crowns east of it
# The ground between them is a terrace at 45.5 m (jk_grade), where the 5 m grid ran one slope down to the library.
LATE_FOOTPRINT_1997[990010] = list(block_poly(JK_O + JK_A * -1.875 + JK_V * -0.75, JK_A, 22.875, 5.75,
                                              round_end=True).exterior.coords)[:-1]
LATE_FOOTPRINT_1997[990011] = list(block_poly((-156.25, -24.0), _lib_u, 17.0, 4.75).exterior.coords)[:-1]
LATE_FOOTPRINT_1997[990012] = list(Point(-163.5, -24.0).buffer(7.5, 3).exterior.coords)[:-1]
LATE_LEVELS = {990011: 2, 990012: 1}
BASE_1997.update({990010: 45.2, 990014: 45.2, 990011: 39.0, 990012: 45.3, 990060: SCI['yard'], 990061: SCI['yard']})
# (the outlines and halls put back since the planting was laid, as MED_SITES_RNG's None: no clearing was made for
# them, so the trees by them step aside in their places in the list)
SITES_NEW_1997 = {222843398, 990010, 990011, 990012, 990014, 990060, 990061, 990050, 990051, 990052}
# The rows after the first four go in after the random planting, cars and decals, as LATE_FOOTPRINT_1997 (below), so
# that the rest of the campus keeps its layout
OLD_HALLS_EARLY = {990010, 990011, 990012, 990013}
for pid, nm, style, lv, poly in OLD_HALLS:
    if pid not in OLD_HALLS_EARLY:
        continue
    poly = shapely.geometry.polygon.orient(poly.simplify(0.05), 1.0)
    campus_polys.append(poly)
    hs = [ground_h(x, y) for x, y in poly.exterior.coords]
    buildings.append(dict(id=pid, name=nm, style=style, levels=lv, height=round(lv * FLOOR_H[style], 2),
                          base=round(min(hs), 2), top_ground=round(max(hs), 2),
                          footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]]))

campus_zone = unary_union([p.buffer(60) for p in campus_polys]).buffer(-20)
campus_zone_rng = unary_union([_cp_rng.get(i_, p).buffer(60) for i_, p in enumerate(campus_polys)]).buffer(-20)

# unnamed buildings: neighbourhood houses outside the campus (1990s low-rise 주택가)
n_city = 0
for wv in ways.values():
    t = wv.get('tags', {})
    if 'building' not in t or 'name' in t or wv['type'] != 'way':
        continue
    poly = footprint(wv)
    if poly.area < 25 or campus_zone.contains(poly.centroid):
        continue
    c = poly.centroid
    if bline.distance(c) < 40:
        continue
    hs = [ground_h(x, y) for x, y in poly.exterior.coords]
    lv = rng.choice([2, 2, 2, 3, 3, 4]) if poly.area < 400 else rng.choice([3, 4, 5])
    if -110 < c.x < 40 and -420 < c.y < -100:
        continue        # shops east of the gate / by the eagle: the 1997 aerial photo shows lawn and car parks there
    buildings.append(dict(id=wv['id'], name='', style='city', levels=lv, height=round(lv * 3.0 + 0.8, 2),
                          base=round(min(hs), 2), top_ground=round(max(hs), 2),
                          footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]]))
    n_city += 1
print('buildings', len(buildings), 'city', n_city)
bpolys = [Polygon(b['footprint']) for b in buildings]
ball = unary_union(bpolys)
# (the halls as the random planting first read them: BLD_MOVE)
bpolys_rng = [Polygon([[round(x_, 2), round(y_, 2)] for x_, y_ in list(footprint(ways[b['id']], rng=True).exterior.coords)[:-1]])
              if b['id'] in BLD_MOVE or b['id'] in BLD_SHAPE else bp_ for bp_, b in zip(bpolys, buildings)]
ball_rng = unary_union(bpolys_rng)

# --- 대강당 앞: the rubble wall and the bank of shrubs along 백양로's east sidewalk (issue #84).  Kakao roadview of
# August 2008 (2381303) and April 2011 (1017220192 - 1017220198), reference/대강당_2009_앞길_계단.jpg: from the drive
# up to 대강당 (south) to the broad granite flight up to its forecourt (north) a low wall of mortared granite rubble with
# a flat top stands at the sidewalk's outer edge, about 0.7 m high (0.72 m by the pano heights, about the flight's 4th
# riser in the 2009 photo); behind it a bank of shrubs, the ginkgo row standing on it a metre behind the wall, climbs
# to a clipped hedge along the top, and the terrace there (the court, the forecourt) is out of sight from the street.
# The wall's south end: (2.85, -10.3) and (2.9, -11.2) from two panos, s 433.  It runs on north past the flight
# (AUD_FLIGHT, which stands in a gap in it between its posts) with the bank behind it (Dec. 2010 1016786030 · 034,
# Aug. 2008 2381323) to where it turns into the side road below 용재관 (s ~555), beyond the hall's north end.  The bank's
# top edge 7 m behind the wall, at the flight's head (the 1994 aerial photo's paved terrace begins 20 - 22 m east of
# the centre line, the court 17.4 m).  The terrace is the forecourt's level, the head of the flight 3.55 m over the
# sidewalk (AUD_HEAD; before, 대강당's forecourt stood only 0.8 m over it here, reference/고증.md 4.5, 5).  The wall
# and the bank are a mesh (blender/landmarks.py aud_bank, its slope drawn with the terrain's own material:
# web/src/terrain.js drapeTerrain); the 5 m grid under it is kept below it, and below the sidewalk in front of the
# wall, and under the flight below the sidewalk.
# 대강당 북쪽 곁길 어귀 (용재관 아래, reference/고증/4.5 「옹벽과 둑」): the side road east between 대강당 and 용재관 (the
# 1990 map) leaves 백양로 where the rubble wall and its bank turn into it (Kakao roadview 2008-08 2381323, 2010-12
# 1016786034: the camera at s 553 - 557 looks straight up it, the wall's kerb curving in on the right and the island's
# on the left; the planting strip and the verge open across its mouth).  ± 2 m (the panos' headings unsolved)
AUD_SIDE_MOUTH = (-1, 552.5, 561.0)
# ... and the yard before 학생회관 별관 (the drive's foot, AUD_RAMP below) opens to 백양로 in the same way: the 1990 ·
# 1994 · 1995 maps' road north of 학생회관 leaves its east side here; Kakao roadview April 2011: the verge's round north
# end south of the opening at s 420.8 (1017220190) and 421.8 (1017220191), the next piece's south end at s 430.0
# (1017220191; 1016786021 of December 2010 about 429), the poses as for the drive (reference/고증/4.5)
AUD_YARD_MOUTH = (-1, 421.3, 429.6)
AUD_BANK = dict(s0=433.1, s1=AUD_SIDE_MOUTH[1] - 0.5, wall=0.7, cap=0.35, top=7.0, ext=12.55, side=-1, walk_z=0.15)   # (walk_z: road.py WZ)
AUD_BANK['gap'] = [round(AUD_FLIGHT['s_range'][0] + 0.05, 2), round(AUD_FLIGHT['s_range'][1] - 0.05, 2)]  # (the flight)
AUD_T = AUD_HEAD                              # (the forecourt and the terrace at the flight's head)
# the drive (AUD_RAMP): Kakao roadview April 2011 1017220188 - 196 (the poses of the panos solved from 대강당's front
# and the wall's south end; reference/고증.md 4.5) and skyview 2008 · 2010 have an asphalt ramp from 백양로 just past
# the wall's south end north-east up to the terrace, the bank a wedge between it and the street, and 학생회관 별관's
# ground floor and the yard before it down at the street's level.  At its foot three bollards stand across the
# carriageway 1.3 m apart and one more on the walk; from them it climbs 22 m on a bearing of 38 deg to the head,
# 39.8 +- 0.45 m (four frames looking up it, the horizon of each set by the bollards' feet): 20 % here (17 - 22 %).
# The carriageway 4.7 m wide, a walk 1.8 m wide up its east side and beyond that a strip of clipped shrubs 4.5 m wide
# on the slope down to the yard, from 2.5 m below the bollards (its lower end and its outer edge from 190 - 193: 0.1 m
# apart in three; 학생회관 별관's ground floor stands 10 m beyond it, the yard between).  The foot: the middle bollard, from 190 and 192 (its distance from 188 - 191 agrees with the bollards'
# heights in those frames to 4 %; the skyview has it 3.5 m further east).  The terrace beyond the head is not level
# but falls with 백양로, from the flight's head (40.33 m) to the drive's head.
# (the bollards: the triangulated row, 1.22 · 1.16 · 1.75 m apart; their spacing in 2008 · 2010 frames agrees, 4.5)
AUD_RAMP = dict(foot_rng=(7.56, -9.22), bearing=38.0, run=22.0, w=4.7, walk=1.8, band=4.45, band_t0=-2.5, mouth=5.0, z1=39.8,
                bollards=(-1.22, 0.0, 1.16, 2.91))
# (the foot was solved against the wall's south end where the line as first laid put it: it goes with the wall to the
# same place along and across the moved line (#162), 2.2 m across the drive.  The 1997 vertical aerial photos have the
# strip of its asphalt and walk 2.6 +- 0.5 m that way from the first place in four frames, the skyview 2.7 m
# (reference/고증/4.5).  foot_rng: the first place, by which the planting was cleared, AUD_RAMP_MOVE: from it)
AUD_RAMP['foot'] = tuple(round(float(v_), 2) for v_ in along_raw(*s_off_rng(*AUD_RAMP['foot_rng']))[:2])
AUD_RAMP_MOVE = (round(AUD_RAMP['foot'][0] - AUD_RAMP['foot_rng'][0], 2), round(AUD_RAMP['foot'][1] - AUD_RAMP['foot_rng'][1], 2))
_ru = np.array([math.sin(math.radians(AUD_RAMP['bearing'])), math.cos(math.radians(AUD_RAMP['bearing']))])  # (up it)
_rn = np.array([_ru[1], -_ru[0]])                                      # (across it, east)
_rf = np.array(AUD_RAMP['foot'])
AUD_RAMP['pts'] = [[round(float(v_), 2) for v_ in _rf + _ru * t_] for t_ in (-AUD_RAMP['mouth'], 0.0, AUD_RAMP['run'])]
AUD_RAMP['z0'] = round(prof_h(s_off(*_rf)[0]) + AUD_BANK['walk_z'], 3)
AUD_RAMP['s_head'] = round(s_off(*AUD_RAMP['pts'][-1])[0], 2)


def ramp_xy(t, o):
    """t m up the drive from the middle bollard, o m across it (+ east)"""
    return tuple(float(v_) for v_ in _rf + _ru * t + _rn * o)


def ramp_strip(o0, o1, t0, t1):
    return Polygon([ramp_xy(t0, o0), ramp_xy(t1, o0), ramp_xy(t1, o1), ramp_xy(t0, o1)])


def aud_ramp_z(x, y):
    """the drive's surface (level across it) at (x, y): the street's level below the bollards, then up to the head"""
    t_ = min(AUD_RAMP['run'], max(0.0, float((np.array([x, y]) - _rf) @ _ru)))
    return AUD_RAMP['z0'] + (AUD_RAMP['z1'] - AUD_RAMP['z0']) * t_ / AUD_RAMP['run']


def aud_terrace_z(s_):
    """the terrace along 백양로: from the drive's head up to the flight's head, level north of it"""
    f_ = min(1.0, max(0.0, (s_ - AUD_RAMP['s_head']) / (AUD_FLIGHT['s'] - AUD_RAMP['s_head'])))
    return AUD_RAMP['z1'] + (AUD_T - AUD_RAMP['z1']) * f_


_rk = (_rf - _rn * AUD_RAMP['w'] / 2, _ru)                             # (the west kerb: a point and its direction)


def aud_bank_top(s_):
    """how deep the bank is behind the wall's face at s_: 7 m, less where the drive's west kerb runs closer (the wedge)"""
    x_, y_, _ = along_raw(s_, AUD_BANK['side'] * E_WALK)
    nb_ = np.array(along_raw(s_, AUD_BANK['side'] * (E_WALK + 1.0))[:2]) - (x_, y_)
    t_, l_ = np.linalg.solve(np.array([[nb_[0], -_rk[1][0]], [nb_[1], -_rk[1][1]]]), _rk[0] - (x_, y_))
    if l_ > AUD_RAMP['run'] + 1.0:
        return AUD_BANK['top']
    return min(AUD_BANK['top'], max(AUD_BANK['cap'] + 0.4, float(t_) - 0.3))


_ts0 = AUD_RAMP['s_head'] - 2.0
_tb = [along_raw(s_, AUD_BANK['side'] * (E_WALK + AUD_BANK['top'] - 0.5))[:2] for s_ in np.arange(_ts0, AUD_BANK['s1'] + 0.1, 4.0)]
_tb += [along_raw(s_, AUD_BANK['side'] * (E_WALK + 21.0))[:2] for s_ in np.arange(AUD_BANK['s1'], _ts0 - 0.1, -4.0)]
AUD_TERRACE = court_poly(5.0).union(Polygon(_tb)).union(Point(AUD_RAMP['pts'][-1]).buffer(5.0))
_bk = Polygon([along_raw(s_, AUD_BANK['side'] * (E_WALK - 2.0))[:2] for s_ in np.arange(AUD_BANK['s0'] - 2.0, AUD_BANK['s1'] + 0.1, 2.0)] +
              [along_raw(s_, AUD_BANK['side'] * (E_WALK + aud_bank_top(s_) - 0.5))[:2]
               for s_ in np.arange(AUD_BANK['s1'], AUD_BANK['s0'] - 2.1, -0.5)])           # (the bank: its own mesh)
AUD_RAMP_CW = ramp_strip(-AUD_RAMP['w'] / 2, AUD_RAMP['w'] / 2, -AUD_RAMP['mouth'], AUD_RAMP['run'])
AUD_RAMP_WALK = ramp_strip(AUD_RAMP['w'] / 2, AUD_RAMP['w'] / 2 + AUD_RAMP['walk'], -AUD_RAMP['mouth'], AUD_RAMP['run'])
AUD_RAMP_BAND = ramp_strip(AUD_RAMP['w'] / 2 + AUD_RAMP['walk'], AUD_RAMP['w'] / 2 + AUD_RAMP['walk'] + AUD_RAMP['band'],
                           AUD_RAMP['band_t0'], AUD_RAMP['run'] - 1.0)  # (the shrubs east of the walk)
AUD_RAMP_POLY = unary_union([ramp_strip(-AUD_RAMP['w'] / 2, AUD_RAMP['w'] / 2 + AUD_RAMP['walk'], 0.0, AUD_RAMP['run'])]) \
    .difference(_bk)
# 학생회관 별관 북쪽의 윗단 길 (AUD_UPPER, reference/고증/4.5): from the drive's head the paved terrace runs on east
# along the annex's north side between it and 대강당's south wing (the 1990 and 1994 maps' road between 학생회관 and
# 대강당 towards 루스채플; Kakao skyview 2008 (winter): cars parked in a row 8 - 12 m off the annex's north wall,
# on from the terrace; roadview 2010-12 · 2011-04: a lamp up on that level behind the annex's north-west corner).
# The game had the road there (OSM, 12 m off the wall) dip to 37.1 m between the terrace and the slope east of the
# annex.  The strip 4.5 - 14 m off the OSM north wall (6.8 - 16.3 m off the game's, ANNEX_1997), from the terrace's
# level at the drive's head (39.80 m) to the ground past the annex's north-east corner; the ground by the wall as it was
AUD_ANNEX_N = (np.array([31.91, -1.15]), np.array([63.48, -9.21]))   # (the annex's north wall, OSM 1444448646)
_uu = (AUD_ANNEX_N[1] - AUD_ANNEX_N[0]) / np.linalg.norm(AUD_ANNEX_N[1] - AUD_ANNEX_N[0])
_un = np.array([-_uu[1], _uu[0]])                                    # (north, away from the annex)
AUD_UPPER = dict(u0=-6.0, u1=35.0, v0=4.5, v1=14.0, z0=AUD_RAMP['z1'])
AUD_UPPER['z1'] = round(sample(Hn, NEAR_HALF, NEAR_STEP, *(AUD_ANNEX_N[0] + _uu * AUD_UPPER['u1'] + _un * 9.0)), 2)
AUD_UPPER_POLY = Polygon([tuple(AUD_ANNEX_N[0] + _uu * u_ + _un * v_) for u_, v_ in
                          ((AUD_UPPER['u0'], AUD_UPPER['v0']), (AUD_UPPER['u1'], AUD_UPPER['v0']),
                           (AUD_UPPER['u1'], AUD_UPPER['v1']), (AUD_UPPER['u0'], AUD_UPPER['v1']))])


def aud_upper_z(x, y):
    """the upper road north of 학생회관 별관: from the terrace's level at the drive's head to the ground past the annex"""
    u_ = float((np.array([x, y]) - AUD_ANNEX_N[0]) @ _uu)
    f_ = min(1.0, max(0.0, (u_ - AUD_UPPER['u0']) / (AUD_UPPER['u1'] - AUD_UPPER['u0'])))
    return AUD_UPPER['z0'] + (AUD_UPPER['z1'] - AUD_UPPER['z0']) * f_


COURT_Z = round(aud_terrace_z(s_at(*COURT['pos'])), 3)              # (the court level: the terrace at its middle)
_tw = shapely.contains_xy(AUD_TERRACE, X, Y)
_rw = shapely.contains_xy(AUD_RAMP_POLY.buffer(1.5), X, Y) & ~_tw
_cw = shapely.contains_xy(court_poly(5.0), X, Y)
_uw = shapely.contains_xy(AUD_UPPER_POLY, X, Y) & ~_tw & ~_rw
_zt = np.full(X.shape, AUD_T)
for _j, _i in zip(*np.nonzero(_tw)):
    _zt[_j, _i] = COURT_Z if _cw[_j, _i] else aud_terrace_z(s_at(X[_j, _i], Y[_j, _i]))
for _j, _i in zip(*np.nonzero(_rw)):
    _zt[_j, _i] = aud_ramp_z(X[_j, _i], Y[_j, _i])
for _j, _i in zip(*np.nonzero(_uw)):
    _zt[_j, _i] = aud_upper_z(X[_j, _i], Y[_j, _i])
_in = _tw | _rw | _uw
_ni = ndimage.distance_transform_edt(~_in, return_distances=False, return_indices=True)
_zt = _zt[_ni[0], _ni[1]]                                           # (beyond them: the nearest node's level)
_tw = np.maximum(_in.astype(float), ndimage.gaussian_filter(ndimage.binary_dilation(_in, iterations=1).astype(float), 1.0))
_tw *= np.clip((dist - ROAD_HALF - 1.0) / 3.0, 0, 1)
_tw[(near_buildings(11.0) & ~_rw & ~_cw & ~_uw) | near_buildings(3.0) | FIXED] = 0.0   # (the court's margin: level)
Hn[:] = Hn * (1 - _tw) + _zt * _tw
FIXED[_tw > 0.999] = True
print('대강당 앞 진입로: z %.2f -> %.2f over %.1f m (%.1f %%), head at s %.1f; terrace %.2f -> %.2f, court %.2f'
      % (AUD_RAMP['z0'], AUD_RAMP['z1'], AUD_RAMP['run'], 100 * (AUD_RAMP['z1'] - AUD_RAMP['z0']) / AUD_RAMP['run'],
         AUD_RAMP['s_head'], AUD_RAMP['z1'], AUD_T, COURT_Z))
print('별관 북쪽 윗단 길: %.2f -> %.2f m, grid nodes %d' % (AUD_UPPER['z0'], AUD_UPPER['z1'], int(_uw.sum())))


def aud_bank_z(top, tp, o, to=None):
    """the bank's surface o m behind the wall face: the wall's cap, then an S-curve up to its top edge to m behind"""
    if o <= AUD_BANK['cap']:
        return top
    t_ = min(1.0, (o - AUD_BANK['cap']) / ((to or AUD_BANK['top']) - AUD_BANK['cap']))
    return top + (tp - top) * t_ * t_ * (3 - 2 * t_)


_ab = []    # per metre of the wall: s, the sidewalk, the wall top, the top edge, the ground beyond, the bank's depth,
# how far out the ground beyond is drawn (the wedge by the drive: only out over its kerb)
_gA, _gB = AUD_BANK['gap']                                          # (and at the two ends of the gap for the flight)
for _s in sorted(set([round(float(v_), 3) for v_ in np.arange(AUD_BANK['s0'], AUD_BANK['s1'] + 1e-6, 1.0)] + [_gA, _gB])):
    _zb = prof_h(_s) + AUD_BANK['walk_z']
    _top = _zb + AUD_BANK['wall']
    _to = aud_bank_top(_s)
    _ext = AUD_BANK['ext'] if _to >= AUD_BANK['top'] else _to + 1.0
    _far = [sample(Hn, NEAR_HALF, NEAR_STEP, *along_raw(_s, AUD_BANK['side'] * (E_WALK + o_))[:2])
            for o_ in (_to, (_to + _ext) / 2, _ext)]
    # the top edge at the terrace's level (the 5 m grid rounds it off); south of the drive's head, at the drive's
    _far[0] = max(_far[0], aud_terrace_z(_s)) if _s >= AUD_RAMP['s_head'] else \
        aud_ramp_z(*along_raw(_s, AUD_BANK['side'] * (E_WALK + _to))[:2])
    _ab.append((float(_s), _zb, _top, max(_far[0], _top + 0.05), _far, _to, _ext))
_abs = np.array([a_[0] for a_ in _ab])
# the grid under the bank: below its surface, and so low that no terrain triangle reaching out under the sidewalk
# rises over the sidewalk in front of the wall
_win = (X > -40) & (X < 90) & (Y > -60) & (Y < 100)
_jj, _ii = np.nonzero(_win)
_SO = {}
for _j, _i in zip(_jj.tolist(), _ii.tolist()):
    _s, _o = s_off(X[_j, _i], Y[_j, _i])
    _SO[(_j, _i)] = (_s, AUD_BANK['side'] * _o - E_WALK)          # (o: metres behind the wall face, + into the bank)
_nb = 0
for (_j, _i), (_s, _o) in _SO.items():
    if not (AUD_BANK['s0'] <= _s <= AUD_BANK['s1'] and 0.0 <= _o < AUD_BANK['top']):
        continue
    _k = int(np.clip(np.searchsorted(_abs, _s), 1, len(_abs) - 1))
    _f = (_s - _abs[_k - 1]) / (_abs[_k] - _abs[_k - 1])
    _zb, _top, _tp, _to = [_ab[_k - 1][q_] * (1 - _f) + _ab[_k][q_] * _f for q_ in (1, 2, 3, 5)]
    if _o >= _to:
        continue                                                    # (the drive beyond the wedge)
    _h = min(float(Hn[_j, _i]), aud_bank_z(_top, _tp, _o, _to) - 0.03)
    if abs(_s - AUD_FLIGHT['s']) < AUD_FLIGHT['w'] / 2 + AUD_FLIGHT['cheek'] + 2.5:
        _h = min(_h, AUD_FLIGHT['foot_z'] - 0.3)                    # (under the flight: its treads hide nothing)
    for _dj in (-1, 0, 1):
        for _di in (-1, 0, 1):
            _q = _SO.get((_j + _dj, _i + _di))
            if _q is None or _q[1] >= 0.0 or not (AUD_BANK['s0'] - 6 <= _q[0] <= AUD_BANK['s1'] + 6):
                continue
            _ha = float(Hn[_j + _dj, _i + _di])
            _fr = -_q[1] / (_o - _q[1])                            # where the line between them meets the wall face
            _h = min(_h, _ha + (_zb - 0.03 - _ha) / max(_fr, 1e-3))
    Hn[_j, _i] = _h
    FIXED[_j, _i] = True
    _nb += 1
AUD_BANK['sections'] = []
for _s, _zb, _top, _tp, _far, _to, _ext in _ab:
    if _gA < _s < _gB:
        continue                                                    # (the flight stands there)
    _x, _y, _a = along_raw(_s, AUD_BANK['side'] * E_WALK)
    # s, the wall face's foot (x, y), the heading into the bank, sidewalk, wall top, top edge, the ground beyond at
    # the top edge, halfway and out (+4 cm), the bank's depth and how far out the ground beyond goes
    AUD_BANK['sections'].append([round(_s, 2), round(_x, 3), round(_y, 3),
                                 round(math.atan2(AUD_BANK['side'] * math.cos(_a), -AUD_BANK['side'] * math.sin(_a)), 5),
                                 round(_zb, 3), round(_top, 3), round(_tp, 3)] + [round(v_ + 0.04, 3) for v_ in _far] +
                                [round(_to, 3), round(_ext, 3)])
AUD_BANK['terrace'] = AUD_T
_fl = [a_ for a_ in _ab if abs(a_[0] - AUD_FLIGHT['s']) < 0.6]
AUD_FLIGHT['far'] = [round(v_ + 0.04, 3) for v_ in (_fl[0][4] if _fl else [AUD_HEAD] * 3)]   # (the terrace beyond its head)
print('대강당 앞 둑: terrace', AUD_T, 'wall s %.1f - %.1f' % (AUD_BANK['s0'], AUD_BANK['s1']), 'grid nodes under it', _nb,
      'bank over the wall top %.2f - %.2f m' % (min(a_[3] - a_[2] for a_ in _ab), max(a_[3] - a_[2] for a_ in _ab)))

# ---------------------------------------------------------------------------
# Ground splat map  (R asphalt, G pavers, B dirt/forest floor ; rest = grass)
# ---------------------------------------------------------------------------
SPLAT = dict(x0=-560.0, y0=-560.0, x1=640.0, y1=680.0, res=0.5)
SW = int((SPLAT['x1'] - SPLAT['x0']) / SPLAT['res'])
SH = int((SPLAT['y1'] - SPLAT['y0']) / SPLAT['res'])


def to_px(x, y):
    return ((x - SPLAT['x0']) / SPLAT['res'], (SPLAT['y1'] - y) / SPLAT['res'])

layers = {k: Image.new('L', (SW, SH), 0) for k in ('asphalt', 'pavers', 'dirt')}
dr = {k: ImageDraw.Draw(v) for k, v in layers.items()}
# ... and the ground as the random planting reads it (PAV_PRE, ASPH_PRE below): every stroke up to there goes on these
# too, but where a stroke follows 백양로 or what stands by it, these get it as first laid (BLINE_RNG; pre=False on the
# stroke, the first one by rng_line / rng_poly)
layers_rng = {k: Image.new('L', (SW, SH), 0) for k in ('asphalt', 'pavers')}
dr_rng = {k: ImageDraw.Draw(v) for k, v in layers_rng.items()}
# every stroke is also kept (in metres) to be drawn again finer for the map the game reads (splat_aa below): the
# random planting, the decals and the leaf mask go on reading these 0.5 m layers as before
SPLAT_OPS = []


def _line_on(d_, coords, width):
    pp = [to_px(x, y) for x, y in coords]
    wpx = max(1, int(width / SPLAT['res']))
    d_.line(pp, fill=255, width=wpx, joint='curve')
    r = wpx / 2
    for x, y in pp:
        d_.ellipse([x - r, y - r, x + r, y + r], fill=255)
    return wpx


def _poly_on(d_, poly, val):
    for g in (poly.geoms if hasattr(poly, 'geoms') else [poly]):
        if g.geom_type != 'Polygon':
            continue
        d_.polygon([to_px(x, y) for x, y in g.exterior.coords], fill=val)
        for hole in g.interiors:
            d_.polygon([to_px(x, y) for x, y in hole.coords], fill=0)


def rng_line(layer, coords, width):
    """a stroke on the ground the random planting reads only (as first laid)"""
    if dr_rng is not None and layer in dr_rng:
        _line_on(dr_rng[layer], coords, width)


def rng_poly(layer, poly, val=255):
    if dr_rng is not None and layer in dr_rng and not poly.is_empty:
        _poly_on(dr_rng[layer], poly, val)


def draw_line(layer, coords, width, pre=True):
    wpx = _line_on(dr[layer], coords, width)
    if pre:
        rng_line(layer, coords, width)
    SPLAT_OPS.append(('line', layer, [tuple(c[:2]) for c in coords], wpx, True))


def draw_poly(layer, poly, val=255, pre=True):
    if poly.is_empty:
        return
    _poly_on(dr[layer], poly, val)
    if pre:
        rng_poly(layer, poly, val)
    geoms = poly.geoms if hasattr(poly, 'geoms') else [poly]
    for g in geoms:
        if g.geom_type != 'Polygon':
            continue
        SPLAT_OPS.append(('poly', layer, list(g.exterior.coords), val))
        for hole in g.interiors:
            SPLAT_OPS.append(('poly', layer, list(hole.coords), 0))


def splat_aa(names, ss=8, strip=62):
    """The splat strokes (SPLAT_OPS) drawn again at ss times the resolution, a strip of rows at a time, and averaged
    back to the 0.5 m texels: each texel holds how much of it the paving covers, so the edge the terrain shader cuts
    where a channel crosses one half (web/src/terrain.js) runs straight and smooth instead of following the texels in
    0.5 m steps (at 8x it lies within about 5 cm of the drawn outline; the old map's, PIL filling whole texels, wandered
    from 0.5 m inside it to 0.9 m out, 0.16 m out on the average).  The priority of the layers (asphalt > pavers > dirt)
    is taken at the fine resolution.  Returns {name: float32 (SH, SW) 0..255}."""
    out_ = {n_: np.zeros((SH, SW), np.float32) for n_ in names}
    k_ = ss / SPLAT['res']
    boxes = []
    for op in SPLAT_OPS:
        ys_ = [c[1] for c in op[2]]
        pad_ = (op[3] if op[0] == 'line' else 0) * SPLAT['res'] + 1.0
        boxes.append(((SPLAT['y1'] - max(ys_) - pad_) / SPLAT['res'], (SPLAT['y1'] - min(ys_) + pad_) / SPLAT['res']))
    for r0 in range(0, SH, strip):
        r1 = min(SH, r0 + strip)
        hi = {n_: Image.new('L', (SW * ss, (r1 - r0) * ss), 0) for n_ in names}
        dd_ = {n_: ImageDraw.Draw(im_) for n_, im_ in hi.items()}
        P_ = lambda x, y: ((x - SPLAT['x0']) * k_, (SPLAT['y1'] - y) * k_ - r0 * ss)
        for op, (b0, b1) in zip(SPLAT_OPS, boxes):
            if op[1] not in hi or b1 < r0 or b0 > r1:
                continue
            if op[0] == 'poly':
                dd_[op[1]].polygon([P_(x, y) for x, y in op[2]], fill=op[3])
                continue
            pp = [P_(x, y) for x, y in op[2]]
            w_ = op[3] * ss
            dd_[op[1]].line(pp, fill=255, width=w_, joint='curve')
            if op[4]:
                for x, y in pp:
                    dd_[op[1]].ellipse([x - w_ / 2, y - w_ / 2, x + w_ / 2, y + w_ / 2], fill=255)
        arr = {n_: np.array(im_, np.int16) for n_, im_ in hi.items()}
        if 'asphalt' in arr:
            arr['pavers'] = np.minimum(arr['pavers'], 255 - arr['asphalt'])
            arr['dirt'] = np.clip(np.minimum(arr['dirt'], 255 - arr['asphalt'] - arr['pavers']), 0, 255)
        for n_, a_ in arr.items():
            out_[n_][r0:r1] = a_.reshape(r1 - r0, ss, SW, ss).mean((1, 3))
    return out_

# forest floor under woods (natural=wood / landuse=forest)
woods = []
for wv in ways.values():
    t = wv.get('tags', {})
    if t.get('natural') == 'wood' or t.get('landuse') == 'forest':
        if len(wv['geometry']) > 3:
            pg = Polygon([xy(p) for p in wv['geometry']]).buffer(0)
            if pg.area > 200:
                woods.append(pg)
woods_u = unary_union(woods) if woods else Polygon()
draw_poly('dirt', woods_u.buffer(-6), 170)

# city ground: everything around houses is concrete/asphalt-ish alleys
city = unary_union([bp.buffer(5) for bp, b in zip(bpolys, buildings) if b['style'] == 'city'])
draw_poly('asphalt', city, 210)

# OSM roads / paths (indoor corridors skipped; modern 백양로 garden paths skipped)
WID = {'primary': 24, 'primary_link': 9, 'secondary': 14, 'tertiary': 10, 'residential': 6.5,
       'living_street': 6, 'service': 6, 'unclassified': 6, 'road': 6, 'busway': 8,
       'footway': 2.6, 'path': 2.0, 'steps': 3.0, 'pedestrian': 4}
bcorr = bline.buffer(ROAD_HALF + 12)
bcorr_rng = BLINE_RNG.buffer(ROAD_HALF + 12)
# Photo A's camera (reference/고증.md 2.2; the 「1997 사진 시점」 of web/src/birdseye.js, compare/baekyangro in
# tools/snapshots.json): the ray through a pixel of the 2100 x 1338 photo, and the ground point under it on the terrain
# as built.  The gate's side road, island, booth and banners below are kept as the pixels read off the photo, so they
# follow the camera and 백양로's height section when either changes (first read through the camera and the flat road
# of before #8, they had come out 4 - 10 m too far in).  When the ground went over to Copernicus GLO-30 (gate
# 34.9 -> 25.7 m, the north end of 백양로 7 m down, 언더우드관's quarter 1 m) the camera came down with it: its height
# over the road where the photo's widths were read (s 60 - 140 m, 9.1 m lower, all of it; the road between the box
# hedges stays 8.9 m) and its pitch from the halls it was fitted to (중앙도서관, 제1공학관, 언더우드관: the new camera
# puts them where the old one did on the old ground within 11 px rms; it was 54.0 m, -2.70 deg).  Its depth was then
# fixed (issues #82, #83, reference/고증.md 2.2): 제1공학관's south-east corner before the 2014 - 2015 wings, solved from
# ten roadview panoramas at (-124.0, -280), and 백주년기념관's drum from the roadview (#101), with the vertical edges,
# lines and vanishing points of the unchanged halls, roll held at 0: 3.1 px rms (it was (-119.6, -424.0, 44.9), yaw
# 15.8, pitch -2.13, fov 27.9, fitted to a 52 m drum).
# (an optional 'roll' in degrees, + clockwise as tools/photofit/cam.py; the bird's-eye view and compare/baekyangro
# have none, so the camera is kept without)
# Moved with the road (#162, reference/고증/2.1-2.2 「2.2.2」): photo A was taken from over the carriageway, so when
# the 1997 vertical aerial photos put the carriageway 5.4 m east the camera goes with it.  The camera fitted to the
# halls and to the points on the ground at once (the carriageway's middle and the eagle where the aerial photos have
# them): those within 7 px rms, 중앙도서관 and the towers within 5 px, 제1공학관's south-east corner and 백주년기념관's
# north-west corner and drum 23 - 48 px off (the photo and the aerial ones cannot be fitted by one camera).  It was
# (-111.0, -395.7, 44.5), yaw 15.87, pitch -3.60, fov 32.13: PHOTO_A_RNG, through which the random planting still
# reads the photo's pixels.
PHOTO_A = dict(pos=(-106.87, -396.83, 45.22), yaw=15.59, pitch=-3.84, fov=33.06, size=(2100, 1338))
PHOTO_A_RNG = dict(pos=(-111.0, -395.7, 44.5), yaw=15.87, pitch=-3.60, fov=32.13, size=(2100, 1338))


def photo_ray(px, py, cam=None):
    cam = cam or PHOTO_A
    W_, H_ = cam['size']
    f_ = H_ / 2 / math.tan(math.radians(cam['fov'] / 2))
    yw, pt_ = math.radians(cam['yaw']), math.radians(cam['pitch'])
    fwd = np.array([math.sin(yw) * math.cos(pt_), math.cos(yw) * math.cos(pt_), math.sin(pt_)])
    rgt = np.array([math.cos(yw), -math.sin(yw), 0.0])
    up = np.cross(rgt, fwd)
    rl = math.radians(cam.get('roll', 0.0))
    rgt, up = rgt * math.cos(rl) + up * math.sin(rl), -rgt * math.sin(rl) + up * math.cos(rl)
    return np.array(cam['pos']), fwd + (px - W_ / 2) / f_ * rgt - (py - H_ / 2) / f_ * up


def photo_ground(px, py, dz=0.0, cam=None):
    """where the ray through a pixel of photo A meets the terrain (or the surface dz over it)"""
    o_, d_ = photo_ray(px, py, cam)
    z_ = 36.0
    for _ in range(12):
        x_, y_ = o_[:2] + d_[:2] * (z_ - o_[2]) / d_[2]
        z_ = sample(Hn, NEAR_HALF, NEAR_STEP, x_, y_) + dz
    return round(float(x_), 2), round(float(y_), 2)


def photo_top(x, y, py_top, px, cam=None):
    """the height over the ground at (x, y) of the point in pixel column px, row py_top straight over it (a crown's top)"""
    o_, d_ = photo_ray(px, py_top, cam)
    t_ = float(np.dot(np.array([x, y]) - o_[:2], d_[:2]) / np.dot(d_[:2], d_[:2]))
    return float(o_[2] + d_[2] * t_ - sample(Hn, NEAR_HALF, NEAR_STEP, x, y))


def photo_on_line(px, p0, dv, lo=-80.0, hi=80.0, cam=None):
    """the point of the 2D line p0 + t dv (lo <= t <= hi, in front of the camera) seen in pixel column px (for feet
    that stand on a known line, where the ground ray runs too flat or the foot is out of the frame)"""
    def col(t):
        q = photo_px(p0[0] + dv[0] * t, p0[1] + dv[1] * t, 30.0, cam)
        return q[0] - px if q[2] > 1.0 else None             # (None: behind or beside the camera)
    ts = np.linspace(lo, hi, 161)
    cs = [col(t) for t in ts]
    br = [(a, b) for a, b, ca, cb in zip(ts, ts[1:], cs, cs[1:]) if ca is not None and cb is not None and ca * cb <= 0]
    assert br, 'photo_on_line: column %.0f does not cross the line' % px
    a, b = br[0]
    for _ in range(40):
        m_ = (a + b) / 2
        a, b = (m_, b) if col(a) * col(m_) > 0 else (a, m_)
    return round(float(p0[0] + dv[0] * a), 2), round(float(p0[1] + dv[1] * a), 2)


def photo_px(x, y, z, cam=None):
    """photo A pixel of a point (the inverse of photo_ray) and its depth along the view"""
    cam = cam or PHOTO_A
    W_, H_ = cam['size']
    o_, _ = photo_ray(W_ / 2, H_ / 2, cam)
    f_ = H_ / 2 / math.tan(math.radians(cam['fov'] / 2))
    fwd = photo_ray(W_ / 2, H_ / 2, cam)[1]
    rgt = photo_ray(W_ / 2 + f_, H_ / 2, cam)[1] - fwd
    up = fwd - photo_ray(W_ / 2, H_ / 2 + f_, cam)[1]
    v = np.array([x, y, z]) - o_
    zf = float(v @ fwd)
    return W_ / 2 + f_ * float(v @ rgt) / zf, H_ / 2 - f_ * float(v @ up) / zf, zf


# 정문 안쪽 왼편 화단섬 (1997 photo): hedge-bordered flower bed with azaleas, a pine, a stone marker and a sign.
# The island lies between the side road and the front of 제1공학관's south end; the side road leaves 백양로 at the
# speed bump and runs west-north-west past it to the road along the south of the engineering halls.  South of the road,
# lawn and trees.  Its outline: the kerb of the south edge as it shows in photo A, from the east hedge round the
# south-east corner and west to the round west end at the photo's edge (pixels), the north side (hidden) as first read.
_ISL_PX = [(757, 1100), (740, 1115), (690, 1124), (600, 1123), (480, 1122), (400, 1117), (300, 1110), (200, 1103),
           (60, 1097), (38, 1080), (75, 1004), (309, 968), (757, 957)]
ISL = Polygon([photo_ground(*p) for p in _ISL_PX]).difference(bline.buffer(ROAD_HALF + 0.6))
if isinstance(ISL, MultiPolygon):
    ISL = max(ISL.geoms, key=lambda g: g.area)
ISL_SOUTH = LineString([photo_ground(*p) for p in _ISL_PX[1:10]])      # the kerb with the azaleas behind
# (the island and side road as first read, before the camera was fitted again: what the random planting reads, so
# that the rest of the campus keeps its layout)
ISL_OLD = Polygon([(-105.9, -337.3), (-112.5, -334.2), (-119.4, -328.8), (-128.2, -322.5), (-128.0, -310.0),
                   (-119.0, -303.5), (-100.0, -306.0)]).difference(BLINE_RNG.buffer(ROAD_HALF + 0.6))
ISL_SOUTH_OLD = LineString([(-105.9, -337.3), (-119.4, -328.8), (-128.2, -322.5)])
ISL_ROAD_OLD = [(-103.5, -345.5), (-113, -344.5), (-120, -341.5), (-126, -337), (-134, -331), (-148, -327)]
GATE_APRON_OLD = Polygon([along_rng(86.5, ROAD_HALF + 0.5)[:2], (-105.9, -337.3), (-112.5, -334.2), (-119.4, -328.8),
                          (-128.2, -322.5), (-146, -320), (-148, -334), (-127, -348), (-123.1, -350.9), (-117.0, -354.3),
                          along_rng(66.0, ROAD_HALF + 0.5)[:2]])
# The side road joins 백양로 without a kerb (photo A): the west sidewalk ends square across, from the island's
# south-east corner to the carriageway, 85 m in from the gate (its boxwood verge 3.4 m before, with a round end); from
# there to below the bottom of the photo the west side is one sheet of asphalt flush with the carriageway, opening into
# a ~20 m wide apron between the island's kerb and the lawn hedge to the south (백양로's yellow edge line painted
# straight on through).  MOUTH: side (+1 = west), s0, s1, corner radii at the south / north ends, how much further
# the verge stops short at the north end.  The south end is out of the photo (the lawn hedge meets the planting strip
# ~65 m in, the asphalt reaches the photo's bottom edge at 62.5 m).
_mouth_n = round(s_at(*photo_ground(930, 1118)), 1)                  # the sidewalk's square end at the carriageway
_verge_n = round(s_at(*photo_ground(905, 1095)), 1)                  # the round end of the verge
MOUTH = (1, 62.0, _mouth_n, 3.0, 0.6, round(_verge_n - _mouth_n, 1))
_ms, _m0, _m1 = MOUTH[0], MOUTH[1], MOUTH[2]
# 제1공학관 앞 진입로 (reference/고증/3.8): a paved forecourt from 백양로's sidewalk straight to the hall's door, the
# planting strip (hedge, ginkgo) open before it: the 1994 aerial photo has the band, 12 m wide, between two planted
# blocks; Kakao roadview August 2008 2381234, December 2010 1016785994 and April 2011 1017220165 the asphalt forecourt
# with the verge open at s 161.3 - 173.0 (2008) and 161.9 - 173.4 (2011), each pano's heading from the yellow edge
# lines' vanishing point, its place across the road from their slopes, along it from the hall's south-east corner
# (tools/roadview/eng/mouth.py).  Photo A (May 1997) has the boxwood verge whole over the north half of that, and the
# sidewalk too: the opening is the strip's only (blender/road.py strip_breaks), the verge and the sidewalk stay.
# (side, s0, s1)
ENG_MOUTH = (1, 161.6, 173.2)
# 경영학교실단(백양관) 앞 (reference/고증/3.15): the planting strip opens before the front flight and a walk runs from
# the sidewalk straight to its foot.  Kakao roadview August 2008 2381318, December 2010 1016786030 and April 2011
# 1017220201 have the hedges parted there, the walk between them as wide as the flight and no tree on it; the game had
# the ginkgo row and its hedge across, the flight standing on the lawn.  The opening is the flight's own width (its
# side walls 7 m outside, BK_FOOT below: the foot's s from the same outline), the verge and the sidewalk stay
_bkt0 = np.array([-4.6, 105.49]) - np.array([-20.74, 45.64])
_bkt0 /= np.linalg.norm(_bkt0)
_bk_s = round(s_at(*(np.array([-20.74, 45.64]) + _bkt0 * 45.66 + np.array([_bkt0[1], -_bkt0[0]]) * 5.1)), 1)
BK_WALK = (1, round(_bk_s - 3.4, 1), round(_bk_s + 3.4, 1))
# 백양관 북쪽 주차장 어귀: the drive from 백양로 into the car park before the hall's north wing.  The same three years'
# roadview (2008 2381322 · 2381323, 2010 1016786032 · 1016786034) have the verge ending round and the planting strip
# open there, yellow-and-black bollards across the sidewalk at its south side and the cars nose in along the wing
# (BK_LOT below); the game had the drive (OSM, its centre at s 548.7) end at the hedge.  From the verge's round end
# (Kakao skyview 2008 s 544.8, 2010 s 545.4; the 2010 pano 1016786032 with its heading from the yellow lines' vanishing
# point and its place from the north wing's two east corners 546.4) to the hedge island's south tip (skyview 552.8):
# the verge and the strip open there, the sidewalk stays (cars cross it).  (reference/고증/3.15-3.17 「북쪽 주차장」)
BK_MOUTH = (1, 545.5, 552.8)
# ... and north of it the clipped hedge island between the car park's aisle and 백양로 (BK_ISLAND below): it stands in
# the planting strip's place, so the strip (its hedge and ginkgos) gives way to it
BK_ISLAND_S = (552.8, 567.7)
STRIP_OPEN = [ENG_MOUTH, BK_WALK, BK_MOUTH, (1, *BK_ISLAND_S)]            # (blender/road.py strip_breaks)
# 중앙도서관 앞: the plaza before the terrace's flight runs out to 백양로 (LIB97, the 1997 aerial photos: no verge shrubs
# and no crowns along it; the 2010 roadview 1016786015 · 017 have the verge end there too)
LIB_MOUTH = (1, round(s_at(*LF(LIB97['plaza'][0], LIB_ROAD_O)), 1), round(s_at(*LF(LIB97['plaza'][1], LIB_ROAD_O)), 1))
STRIP_OPEN.append(LIB_MOUTH)
# 독수리상 서쪽 옆길이 백양로와 만나는 곳 (JUNC below): the drive along 제1공학관's north side runs on east between the
# eagle's garden and 활천대's to 백양로; its mouth in the verge and the strip (the sidewalk stays, the cars cross it)
JUNC_MOUTH = (1, 245.2, 253.0)
STRIP_OPEN.append(JUNC_MOUTH)
# (대강당 북쪽 곁길 어귀 · 별관 앞마당 어귀, AUD_BANK above; the planting strip stays open on north of the yard's mouth
# to the wall's south end: the drive's flat mouth before its bollards, paved from the sidewalk, reference/고증/4.5)
AUD_YARD_STRIP = (AUD_YARD_MOUTH[0], AUD_YARD_MOUTH[1], AUD_BANK['s0'])
STRIP_OPEN += [AUD_SIDE_MOUTH, AUD_YARD_STRIP]
BUMP_S =round(s_at(*photo_ground(1050, 1145)), 1)                   # the hatched speed bump, just short of the mouth's end


def photo_line(p, q):
    """the ground line through two pixels of photo A: a point on it and its direction (towards 백양로)"""
    a_, b_ = np.array(photo_ground(*p)), np.array(photo_ground(*q))
    return a_, (b_ - a_) / np.linalg.norm(b_ - a_)


# lane paint (photo A): a solid yellow line down the middle of the side road from the mouth west-north-west past the
# island, white planters along it and the parking booth beside it at the photo's edge; south of it a dashed and a solid
# yellow line, 4.9 and 9.7 m off, to the lawn hedge (lanes for the road south to the tennis courts)
_c0, _cd = photo_line((60, 1141), (470, 1170))
_d0, _dd = photo_line((210, 1192), (445, 1211))
_e0, _ed = photo_line((150, 1233), (420, 1253))
_hed = [photo_ground(165, 1280), photo_ground(300, 1288)]          # the lawn hedge south of the apron
_hd = (np.array(_hed[1]) - np.array(_hed[0])) / np.linalg.norm(np.array(_hed[1]) - np.array(_hed[0]))


def _to_strip(p0, d, off):
    """walk from p0 along d (towards 백양로) to `off` m west of the centre line"""
    k = 0.0
    while s_off(*(p0 + d * k))[1] > off and k < 60:
        k += 0.25
    return p0 + d * k


# the side road's centre: along the solid line from the mouth past the booth, then (out of the photo; the 2010 roadview
# and OSM have the road along the south of the engineering halls leaving here west-north-west) bending north-west into it
_post = np.array(photo_ground(75, 1140))                              # on the centre line at the booth's east end


def _chaikin(pts, n=3):
    P_ = [np.array(p, dtype=float) for p in pts]
    for _ in range(n):
        Q_ = [P_[0]]
        for a_, b_ in zip(P_[:-1], P_[1:]):
            Q_ += [a_ * 0.75 + b_ * 0.25, a_ * 0.25 + b_ * 0.75]
        P_ = Q_ + [P_[-1]]
    return [tuple(np.round(p, 2)) for p in P_]


ISL_ROAD = [tuple(np.round(_to_strip(_c0, _cd, E_CURB0 + 1.0), 2)), tuple(np.round(_post, 2))] + \
    _chaikin([_post - _cd * 5.0, _post - _cd * 8.0, (-140.0, -324.8), (-148.0, -316.4), (-156.0, -314.3)])
_hw_e = _to_strip(np.array(_hed[1]), _hd, ROAD_HALF + 0.5)
GATE_APRON = Polygon([along_raw(_m1, ROAD_HALF + 0.5)[:2]] + [photo_ground(*p) for p in _ISL_PX[3:10]] +
                     [(-131.0, -326.5), (-147.2, -313.5), (-145.5, -317.0), (-150.6, -339.8)] + _hed +
                     [tuple(_hw_e), along_raw(_m0, ROAD_HALF + 0.5)[:2]]).buffer(0)
assert GATE_APRON.is_valid and GATE_APRON.geom_type == 'Polygon'
APRON_LINES = []
_keep = GATE_APRON.buffer(-1.2).difference(bline.buffer(E_WALK + 0.5))
for _ln, _kind in ((LineString(ISL_ROAD), 'yellow'),
                   (LineString([tuple(_d0 - _dd * 45), tuple(_d0 + _dd * 20)]), 'yellow_dash'),
                   (LineString([tuple(_e0 - _ed * 45), tuple(_e0 + _ed * 20)]), 'yellow')):
    _ln = _ln.intersection(_keep)
    for _g in (_ln.geoms if hasattr(_ln, 'geoms') else [_ln]):
        if _g.geom_type == 'LineString' and _g.length > 2:
            APRON_LINES.append((_kind, list(_g.coords)))
print('gate apron: mouth s %.1f - %.1f (verge to %.1f), bump %.1f, line by the booth (%.1f, %.1f)' %
      (_m0, _m1, _verge_n, BUMP_S, _post[0], _post[1]))
# east of 백양로 between the gate and 백주년기념관: in 1997 a lawn with scattered trees and a shaded car park
# (the curving promenade paths in OSM belong to the 2015 백양로 garden)
EAST_LAWN = Polygon([(-86, -404), (-18, -404), (-18, -266), (-50, -258)]).difference(bline.buffer(ROAD_HALF + 1))
EAST_LAWN_RNG = Polygon([(-86, -404), (-18, -404), (-18, -266), (-50, -258)]).difference(BLINE_RNG.buffer(ROAD_HALF + 1))
paths_out = []
for wv in ways.values():
    t = wv.get('tags', {})
    hw = t.get('highway')
    if hw not in WID or t.get('area') == 'yes' or t.get('indoor') or t.get('level', '0') not in ('0', '0;1'):
        continue
    if t.get('tunnel') or t.get('layer', '0').startswith('-'):
        continue
    if t.get('name') == '백양로':
        continue
    g = [xy(p) for p in wv['geometry']]
    ls = LineString(g)
    if ls.intersects(ISL_OLD.buffer(-0.5)) and hw not in ('footway', 'path', 'steps', 'pedestrian'):
        continue
    if hw in ('footway', 'path', 'steps', 'pedestrian'):
        # (and none across 활천대's basin or the eagle's round: OSM's walks there are the 2015 백양누리 garden's;
        # the ground the random planting reads has them cut as first laid: BLINE_RNG)
        # (the moved road's corridor cuts them as the first one did too: OSM's walks along the 2015 road are its garden's)
        for lawn_, corr_, fp_, ep_, pre_ in ((EAST_LAWN, bcorr.union(bcorr_rng), FOUNTAIN['pos'], EAGLE_PLAZA, False),
                                             (EAST_LAWN_RNG, bcorr_rng, FOUNTAIN_RNG, EAGLE_PLAZA_RNG, True)):
            if lawn_.contains(ls.centroid):
                continue
            ls_ = ls.difference(corr_).difference(ISL_OLD.buffer(1.0)).difference(Point(*fp_).buffer(FOUNTAIN['pave'] + 0.3)) \
                .difference(ep_.buffer(1.0))
            for l in (ls_.geoms if hasattr(ls_, 'geoms') else [ls_]):
                if l.is_empty or l.length < 3:
                    continue
                if pre_:
                    rng_line('pavers', l.coords, WID[hw])
                    continue
                draw_line('pavers', l.coords, WID[hw], pre=False)
                paths_out.append(dict(kind=hw, w=WID[hw], pts=[[round(x, 1), round(y, 1)] for x, y in l.coords]))
    else:
        draw_line('asphalt', g, WID[hw])
        paths_out.append(dict(kind=hw, w=WID[hw], pts=[[round(x, 1), round(y, 1)] for x, y in g]))

# 1997 roads branching at the 삼거리 + 정문 forecourt
extra_roads = [
    [(38, 168), (20, 175), (-2, 178), (-43, 186), (-74, 194)],                 # west fork
    [(38, 168), (62, 160), (85, 150), (110, 140)],                            # east fork toward 노천극장
    [GATE, (-150, -432), (-250, -428)], [GATE, (0, -440), (120, -440)],
    ISL_ROAD_OLD,
]
_extra_rng = {2: [BYS_RNG[0], (-150, -432), (-250, -428)], 3: [BYS_RNG[0], (0, -440), (120, -440)]}   # (as first laid)
# west of the eagle (1997 photo, back-projected with its camera): a row of parked cars ~48 m west of 백양로 between
# s 250 and 300, a grey drive along their east side.  The drive runs parallel to 백양로 from the end of the road along
# 제1공학관's north side up to the square south of 중앙도서관; the cars park nose in along its west side.
# (Drawn after the random planting has read the ground: ASPH_PRE below.)
SIDE_W = [(-119.9, -181.8)] + [tuple(round(c_, 1) for c_ in along_raw(s, 43.5)[:2]) for s in (240, 270, 300, 330, 352)]
SIDE_W_W = 6.0
LOT_W = [along_raw(s, 48.5) for s in np.arange(255, 300, 3.0)]
draw_poly('asphalt', GATE_APRON_OLD.difference(BLINE_RNG.buffer(ROAD_HALF)))   # (as first read: ASPH_PRE below)
for k_, r in enumerate(extra_roads):
    draw_line('asphalt', r, 7 if r is ISL_ROAD_OLD else 8, pre=k_ not in _extra_rng)
    if k_ in _extra_rng:
        rng_line('asphalt', _extra_rng[k_], 8)
    paths_out.append(dict(kind='service', w=7 if r is ISL_ROAD_OLD else 8, pts=[list(p) for p in (ISL_ROAD if r is ISL_ROAD_OLD else r)]))


def mouth_poly(s0, s1, r0, r1, line=None):
    # the mouth itself is road geometry (blender/road.py), asphalt under it too
    return Polygon([along_raw(s, _ms * E_CURB0, line)[:2] for s in np.arange(s0 - r0, s1 + r1 + 0.1, 1.0)] +
                   [along_raw(s, _ms * (ROAD_HALF + 1.0), line)[:2] for s in np.arange(s1, s0 - 0.1, -1.0)])


draw_poly('asphalt', mouth_poly(66.0, 86.5, 3.0, 2.0), pre=False)
rng_poly('asphalt', mouth_poly(66.0, 86.5, 3.0, 2.0, BLINE_RNG))

# shaded car park on the lawn south-west of 백주년기념관 (red car under the trees in the 1997 photo)
LOT_E = [along_raw(s, -(ROAD_HALF + 8.5)) for s in np.arange(150, 196, 3.2)]
# 1997 photo: no car park beside the road here; the cars stand in a row on the dry lawn in front of 백주년기념관, side
# on to the camera: the front row's wheels from the red car (x 1650, y 931 px) to the dark cars on the right (2030, 921),
# kept as pixels and placed through PHOTO_A (issue #83; first read through the camera of before #8), a car every 4.6 m
# from the red one, along the row
_lc0, _lc1 = np.array(photo_ground(1650, 931)), np.array(photo_ground(2030, 921))
_lcd = (_lc1 - _lc0) / np.linalg.norm(_lc1 - _lc0)
LOT_C = [(round(float(q_[0]), 2), round(float(q_[1]), 2), round(math.atan2(_lcd[1], _lcd[0]), 3))
         for q_ in (_lc0 + _lcd * 4.6 * k for k in range(7))]
draw_line('dirt', [(x, y) for x, y, _ in LOT_C], 7.0)          # (on the trodden dry lawn, no paving)
# 백양로 itself is real geometry (Blender) – paint asphalt below so seams never show grass
draw_line('asphalt', bys, 2 * E_CURB0, pre=False)
draw_line('pavers', bys, 2 * ROAD_HALF, pre=False)
rng_line('asphalt', BYS_RNG, 2 * E_CURB0)
rng_line('pavers', BYS_RNG, 2 * ROAD_HALF)


# 대강당: its forecourt is paved from the porch out to the drive (the 2009 photos: cars park in front of the porch)
_af0, _af1 = np.array([51.13, 28.26]), np.array([59.82, 61.16])
_av = (_af1 - _af0) / np.linalg.norm(_af1 - _af0)
_aw = np.array([-_av[1], _av[0]])                                   # out of the front (west)
AUD_FORECOURT = Polygon([tuple(_af0 - _av * 14), tuple(_af1 + _av * 14), tuple(_af1 + _av * 14 + _aw * 12.5),
                         tuple(_af0 - _av * 14 + _aw * 12.5)])
draw_poly('asphalt', AUD_FORECOURT)
# building aprons (paved strips around campus buildings), library forecourt, 정문 plaza
aprons = unary_union([bp.buffer(3.5) for bp, b in zip(bpolys, buildings) if b['style'] != 'city'])
draw_poly('pavers', aprons, pre=False)
rng_poly('pavers', unary_union([bp.buffer(3.5) for bp, b in zip(bpolys_rng, buildings) if b['style'] != 'city']))
plazas = [
    Polygon([(-85, -72), (-66, 4), (-12, -8), (-30, -88)]),                     # 중앙도서관 앞 광장
    Polygon([(18, -60), (4, -112), (-14, -105), (2, -52)]),                     # 학생회관 앞
    Point(GATE[0], GATE[1] + 10).buffer(22),                                  # 정문
    Polygon([(40, 150), (100, 140), (110, 185), (55, 195)]).buffer(2),          # 노천극장 진입
]
# 백주년기념관's paved court towards 광혜원 (2010 roadview) and the foot of 과학관's flight (the 1996 album photos: paved)
_pa, _pb = np.array(CENT_NE[0]), np.array(CENT_NE[1])
_pn = np.array([(_pb - _pa)[1], -(_pb - _pa)[0]]) / np.linalg.norm(_pb - _pa)
plazas.append(Polygon([tuple(_pa + (_pb - _pa) * 0.25), tuple(_pa + (_pb - _pa) * 0.95), tuple(_pa + (_pb - _pa) * 0.95 + _pn * 17.0),
                       tuple(_pa + (_pb - _pa) * 0.25 + _pn * 17.0)]))
_PLAZA_RNG = {len(plazas) - 1: shapely.affinity.translate(plazas[-1], -BLD_MOVE[324328422][0], -BLD_MOVE[324328422][1])}
plazas.append(Polygon([tuple(SCI_DOOR - SCI_T * 9.0), tuple(SCI_DOOR + SCI_T * 9.0), tuple(SCI_DOOR + SCI_T * 11.0 + SCI_N * 17.0),
                       tuple(SCI_DOOR - SCI_T * 11.0 + SCI_N * 17.0)]))
# (the plaza before 언더우드관 정원: where the game had its steps and banks.  Kept as drawn then, for the random planting
# below; 백양로's end steps, their banks and the square at their head are painted after it: UW_STEPS, PAV_PRE)
UW_BANKS = Polygon([wu_xy(-31.0, -43.4), wu_xy(31.0, -43.4), wu_xy(31.0, -26.0), wu_xy(-31.0, -26.0)])
plazas[3] = plazas[3].difference(UW_BANKS)
for k_, pz in enumerate(plazas):
    draw_poly('pavers', pz, pre=k_ != 2 and k_ not in _PLAZA_RNG)
    if k_ in _PLAZA_RNG:
        rng_poly('pavers', _PLAZA_RNG[k_])
rng_poly('pavers', Point(BYS_RNG[0][0], BYS_RNG[0][1] + 10).buffer(22))       # (the 정문 plaza: by the gate as first laid)

# --- 중앙도서관 앞 (1997).  Not one paved square from the hall to 백양로: the 1990 and 1995 campus maps
# (reference/1990_캠퍼스_지도.png, 1995_캠퍼스_지도.jpg) draw a paved walk along the arcade and, between it and 백양로,
# hedged beds with a cross walk to the middle of the front and a walk running slant through the north bed; the
# 1997 aerial photo shows that ground full of trees (the eagle stood 80 m further south: EAGLE above; the 2011
# roadview has a flower bed where the 2015 rebuilding put it, before the hall's south end).  The 1997 photo
# (reference/1997_중앙도서관.jpg) was
# taken by the head of that slant walk, north-east of the hall (eleven arches along the long front on the left, the
# shaded north end on the right): the walk runs off 13 deg left of the view, its people 1.6 m under the eye at 15 to
# 46 m (their height against the height of their feet under the horizon).
# Frame: s along the front from the south-east corner, o out of it (east).  (The old forecourt square stays south of
# the hall's south end.)
LIB_OLD_SQUARE = plazas[0]
_lib_street = next(LineString(p_['pts']) for p_ in paths_out if p_['kind'] == 'living_street'
                   and p_['pts'][0] == [-60.4, 21.1])                  # the drive along the hall's north end
LIB_APRON = lf_rect(-4.0, 79.0, 0.0, 12.0)                            # the walk along the arcade
# the slant walk: from the drive's kerb, just right of the photo's camera (README view: the game's camera there, fitted
# to the hall's corners, roofline and arches), to the main door, where it meets the cross walk; 4.2 m wide (the
# people on it)
LIB_DIAG = [(-23.2, 9.0), LF(39.0, 12.0)]
LIB_DIAG_W = 4.2
LIB_SDIAG_W = 3.2


def _lib_layout(line):
    """the walks and beds before 중앙도서관 along 백양로's line (and as the random planting first read them: BLINE_RNG)"""
    road_ = line.buffer(E_WALK)                                       # 백양로 to the outer edge of its sidewalk
    cross_ = lf_rect(34.5, 42.5, 11.0, 60.0).difference(road_)        # to the main door, the middle bay
    # and one from the 학생회관 crossing to the south end of the arcade (from the crossing as first put)
    sdiag_ = [along_raw(CROSS_RNG[1], E_WALK - 0.3, line)[:2], LF(9.0, 11.0)]
    walks_ = unary_union([LIB_APRON, cross_, LineString(LIB_DIAG).buffer(LIB_DIAG_W / 2, cap_style=2),
                          LineString(sdiag_).buffer(LIB_SDIAG_W / 2, cap_style=2)])
    beds_ = (unary_union([lf_rect(5.0, 34.5, 12.0, 60.0), lf_rect(42.5, 100.0, 12.0, 60.0)])
             .difference(road_.buffer(ROAD['strip'])).difference(_lib_street.buffer(3.6)).difference(walks_))
    beds_ = unary_union([g_ for g_ in (beds_.geoms if hasattr(beds_, 'geoms') else [beds_])
                         if g_.area > 20 and g_.centroid.y < _lib_street.interpolate(_lib_street.project(g_.centroid)).y])
    return road_, cross_, sdiag_, walks_, beds_


_lib_road, LIB_CROSS, LIB_SDIAG, LIB_WALKS, LIB_BEDS = _lib_layout(bline)
_, _, _, LIB_WALKS_RNG, LIB_BEDS_RNG = _lib_layout(BLINE_RNG)

# ---------------------------------------------------------------------------
# Front gardens laid out from the photos (reference/학교연혁_언더우드관.jpg, 언더우드관_2024_*, 학교연혁_연희관.jpg,
# 연희관_2024_*, 학교연혁_대우관.jpg, 대우관_*): each in a frame (u across, v towards the building)
# ---------------------------------------------------------------------------
def frame(ox, oy, ux, uy):
    n_ = math.hypot(ux, uy)
    ux, uy = ux / n_, uy / n_
    return lambda u, v: (ox + u * ux - v * uy, oy + u * uy + v * ux)


def frame_from(bid):
    # the recessed front edge (footprint[3] -> [4]) of an H-plan hall; v points into the building
    fp_ = next(b for b in buildings if b['id'] == bid)['footprint']
    (ax, ay), (bx, by) = FRAME_AB.get(bid, (fp_[3], fp_[4]))
    return frame(ax, ay, bx - ax, by - ay)


def fpoly(W, pts):
    return Polygon([W(u, v) for u, v in pts])


# 언더우드관 앞 정원 as the game had it (four lawn beds either side of an axis 8.5 m east of the tower, the statue at
# its south end): still drawn here for the random planting below (PAV_PRE, GARDEN_ZONES), the real layout (UWG) is
# drawn over it after that.  WU stays the frame of the road before 언더우드관 (bollards, stall, notice board).
WU = frame(62.0, 213.0, 0.970, -0.243)
garden = Polygon([(30, 190), (80, 177), (95, 236), (44, 250)])
draw_poly('pavers', garden.buffer(1.5))
draw_poly('pavers', garden.buffer(-3), 0)
draw_line('pavers', [WU(0, -30), WU(0, 31)], 5.5)
draw_line('dirt', [WU(-25, 2), WU(25, 2)], 3.0)
# where the game had the steps up from the 삼거리 (now 백양로's end steps further south, UW_STEPS): the paving as drawn
# then, for the random planting (the square at the head of the real steps is painted after it, PAV_PRE)
for _ly in ('pavers', 'asphalt'):                                  # (the banks are lawn: not 백양로's paving round its end)
    draw_poly(_ly, fpoly(WU, [(-31.0, -43.0), (31.0, -43.0), (31.0, -34.4), (-31.0, -34.4)]), 0)
draw_line('pavers', [WU(0, -34.6), WU(0, -30)], 5.0)
draw_poly('pavers', fpoly(WU, [(-24.0, -34.4), (24.0, -34.4), (24.0, -31.4), (-24.0, -31.4)]))
draw_poly('asphalt', fpoly(WU, [(-10.5, -48.5), (10.5, -48.5), (10.5, -42.5), (-10.5, -42.5)]))
# 연희관 앞 정원 (YEONHUI above): the diamond of walks (OSM draws them), a broad axis walk from the south flight to the
# north one, a cross walk, a paved ring round the planter and a paved forecourt at the head of the south flight (the
# radiating joints and the drain of reference/연희관_정면_2023.jpg); the four beds between are lawn; the banks up to
# the road and the court between 연희관's wings stay lawn too
WY = frame_from(245623759)
YH_G = lambda e, n: tuple(GF_C + GF_E * e + GF_N * n)
_ybank = Polygon([YH_DIAMOND[1], YH_DIAMOND[2], YH_DIAMOND[3], (118.8 - 0.8, 335.6 - 2.9), (85.2 - 0.8, 345.0 - 2.9),
                  (51.7 - 0.8, 354.5 - 2.9)])
yeonhui_garden = unary_union([Polygon(YH_DIAMOND).buffer(3.0), _ybank, fpoly(WY, [(0.5, -10.0), (39.8, -10.0), (39.8, -0.5), (0.5, -0.5)])])
draw_line('pavers', [YEONHUI['flights'][1]['top'], YEONHUI['flights'][0]['foot']], 4.0)
draw_line('pavers', [YH_DIAMOND[1], YH_DIAMOND[3]], 3.0)
draw_poly('pavers', Point(*YH_C).buffer(5.6))
draw_poly('pavers', Point(*YH_DIAMOND[0]).buffer(4.6))
for _f in YEONHUI['flights']:
    draw_poly('pavers', Point(*_f['foot']).buffer(_f['width'] / 2 + 0.8))
# 대우관 상뜰 (reference/대우관_정면_전경.jpg, 대우관_블로그_본관_정면_상뜰.jpg, 학교연혁_대우관.jpg, from above the
# 연희관 side; 대우관_2024_정면과_상뜰.jpg on the ground): a round lawn about 6.5 m across inside a low curb with one
# small tree in it, ringed by a broad paved circle (the OSM footway ring, 9 m across, is its centre line); a broad walk
# from it north to the podium's arch and south to the steps down towards 연희관; from the walk's two ends paths run
# out to the drives west and east, so the walks make a diamond (OSM) with two lawn triangles inside it, low shrubs
# along their upper edges and benches along their lower ones, a pair facing each path from either side; the lawns
# outside the diamond, under the terrace, carry the big spreading pines.  (SG: e east along the hall, n north.)
WD = frame_from(242897922)
SANG_LAWN = 3.25                                         # (SANG, SG, SANG_DIAMOND: with the 상뜰's levels above)
# (here as it was first laid out on OSM's ring, what the random planting reads: PAV_PRE, GARDEN_ZONES; the 상뜰 of the
# photos is painted after that, DW_FRONT below)
daewoo_garden = Point(*SANG_RNG).buffer(17).union(Polygon(SANG_DIAMOND_RNG).buffer(3.0))
draw_poly('pavers', Point(*SANG_RNG).buffer(7.2))
draw_line('pavers', [WD(23.5, 0), SANG_RNG], 6.0)
draw_line('pavers', [SG_RNG(0.0, -6.5), SANG_DIAMOND_RNG[2], (101.2, 405.4)], 6.0)        # the broad walk to the south steps
draw_poly('pavers', Point(*SANG_RNG).buffer(SANG_LAWN + 0.1), 0)    # (the lawn inside the curb: after the walks, not under them)
# 대우관 뒤: the car park and the drive asphalt, paving round the planter in the recess (DAEWOO_BACK above)
# (the car park of five rows the game had there, as the random planting first read it: PAV_PRE, ASPH_PRE; the yard
# of 1997 is painted after that, DWB_ZONE below)
rng_poly('asphalt', fpoly(WD, [(25.0, 25.0), (66.0, 25.0), (64.0, 78.0), (25.0, 78.0)]))
rng_poly('pavers', fpoly(WD, [(-0.6, 14.8), (46.0, 14.8), (46.0, 24.6), (-0.6, 24.6)]))
draw_poly('pavers', court_poly(1.0, COURT_OLD))                # (as first read: PAV_PRE; the court's own below)
rng_poly('pavers', Point(*FOUNTAIN_RNG).buffer(3.7))             # (the first basin's paved ring, as first read: PAV_PRE)
GARDEN_ZONES = [garden, yeonhui_garden, daewoo_garden, court_poly(2.0, COURT_OLD), Point(*FOUNTAIN_SCATTER).buffer(FOUNTAIN_SCATTER_R)]

# amphitheater (worn earth), sports field (dirt), tree-root patches done in web shader
draw_poly('dirt', Point(AMPH['cx'], AMPH['cy']).buffer(1).simplify(0))
ell = [amph_xy((AMPH['arena_rx'] + 0.5) * math.cos(a), (AMPH['arena_ry'] + 0.5) * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 48)]
# the floor, the ground round the stage and between it and the seat ends, the path round the rim
amph_dirt = [Polygon(ell), Polygon([amph_xy(u, v) for u, v in ((_back, -15), (AMPH['stage_u'] + 1, -15), (AMPH['stage_u'] + 1, 15), (_back, 15))]),
             Polygon([amph_xy((AMPH['arena_rx'] + AMPH_DEPTH + dd) * math.cos(a), (AMPH['arena_ry'] + AMPH_DEPTH + dd) * math.sin(a))
                      for dd, aa in ((0.4, 1), (2.2, -1)) for a in np.radians(np.linspace(-AMPH['seat_end'], AMPH['seat_end'], 40))[::aa]])]
for pg in amph_dirt:
    draw_poly('dirt', pg)
for wv in ways.values():
    t = wv.get('tags', {})
    if t.get('leisure') in ('pitch', 'track') and len(wv['geometry']) > 3:
        pg = Polygon([xy(p) for p in wv['geometry']]).buffer(0)
        if pg.area > 1500:
            draw_poly('dirt', pg, 230)

# the old amphitheater: no paths across the bowl (the 1999 theatre's aisles and steps)
draw_poly('asphalt', AMPH_PATHS, 0)
draw_poly('pavers', AMPH_PATHS, 0)
draw_poly('dirt', AMPH_PATHS, 0)
for pg in amph_dirt:
    draw_poly('dirt', pg)
# 중앙도서관 앞: lawn in the beds (over the old square and OSM's later walks), the 1997 walks paved.  The random
# planting below still reads the paving as it was before (PAV_PRE), so that the rest of the campus keeps its draws.
PAV_PRE = np.array(layers_rng['pavers']) > 40
ASPH_PRE = np.array(layers_rng['asphalt']) > 40
dr_rng = layers_rng = None
# the gate's apron, side road and island as photo A has them (above: as first read)
_erase = GATE_APRON_OLD.union(LineString(ISL_ROAD_OLD).buffer(3.6)).union(mouth_poly(66.0, 86.5, 3.0, 2.0)) \
    .difference(bline.buffer(E_CURB0))
draw_poly('asphalt', _erase, 0)
draw_poly('asphalt', GATE_APRON.difference(bline.buffer(ROAD_HALF)))
draw_poly('asphalt', mouth_poly(_m0, _m1, MOUTH[3], MOUTH[4]))
for pth in paths_out:
    if pth['kind'] not in ('footway', 'path', 'steps', 'pedestrian') and LineString(pth['pts']).intersects(_erase.buffer(4)):
        draw_line('asphalt', [tuple(p) for p in pth['pts']], pth['w'])
draw_poly('asphalt', ISL, 0)
draw_poly('pavers', ISL, 0)
draw_poly('pavers', LIB_BEDS, 0)
# the same for the eagle's ring and walks and the side road west of it with its car stalls (EAGLE_PAVED, SIDE_W,
# LOT_W); no OSM walk across its beds
draw_poly('pavers', EAGLE_BEDS, 0)
draw_poly('pavers', Point(*FOUNTAIN['pos']).buffer(FOUNTAIN['pave']))   # 활천대: the pool and its flagstones (no grass)
draw_poly('pavers', EAGLE_PAVED.difference(bline.buffer(E_WALK)))
draw_line('asphalt', SIDE_W, SIDE_W_W)
draw_line('asphalt', [(x, y) for x, y, _ in LOT_W], 5.0)
draw_poly('pavers', LIB_WALKS.intersection(LIB_OLD_SQUARE.union(lf_rect(-4.0, 100.0, 0.0, 60.0))).difference(_lib_road))
# ... and for 백양로's end (UW_STEPS above): the road stops at the foot of the steps.  Past it, the paving of the old
# extension to the garden's south edge and the two drives forking from there (extra_roads: they doubled OSM's drives
# round the bank, 10 - 15 m off) give way to the banks (lawn) and the square at the head of the steps (paved); OSM's
# drives and walks there are drawn again, not across the banks
_ext = substring(bline, BY_END_S, L)
for _ly in ('asphalt', 'pavers'):
    draw_poly(_ly, _ext.buffer(ROAD_HALF + 0.5, cap_style='flat'), 0)
    draw_poly(_ly, UW_BANK, 0)
_forks = unary_union([LineString(r_).buffer(4.6) for r_ in extra_roads[:2]])
draw_poly('asphalt', _forks, 0)
draw_poly('pavers', UW_HEAD.difference(garden.buffer(1.5)))
_bank_core = Polygon([st_xy(-20.0, -0.4), st_xy(20.0, -0.4), st_xy(20.0, _US['v_head'] - 0.3), st_xy(-20.0, _US['v_head'] - 0.3)])
_redo = _ext.buffer(ROAD_HALF + 1.0).union(_forks).union(UW_BANK)
_fork_pts = [[list(q) for q in r_] for r_ in extra_roads[:2]]
for p_ in paths_out:
    _pl = LineString(p_['pts'])
    if len(p_['pts']) < 2 or not _pl.intersects(_redo) or p_['pts'] in _fork_pts:
        continue
    _pl = _pl.difference(_bank_core)
    for g_ in (_pl.geoms if hasattr(_pl, 'geoms') else [_pl]):
        if g_.length > 0.5:
            draw_line('pavers' if p_['kind'] in ('footway', 'path', 'steps', 'pedestrian') else 'asphalt', g_.coords, p_['w'])
# 대우관 뒤 (DAEWOO_BACK): OSM's aisles and walks there and the game's old car park give way to the yard of 1997: the
# low court's asphalt out to the road, the theatre's paving, the upper car park's asphalt round its lawns (the hedge
# belt, the terrace over the portal and the mound, the bed west of the short row, the island east of its mouth)
_uvp = lambda pts_: Polygon([dw_xy(*q_) for q_ in pts_])
DWB_COURT_ASPH = _uvp([(-11.5, 27.2), (0.2, 27.2), (0.2, 28.0)] + DWB_COURT_UV[2:-4] + [(14.5, 63.2), (11.2, 63.4), (9.0, 60.3), (-13.6, 28.3)])
DWB_LOT_ASPH = _uvp([(26.2, 61.7), (36.1, 61.7), (36.1, 57.2), (40.0, 57.2), (40.0, 69.7), (45.1, 69.7), DAEWOO_BACK['mound_tip'], (35.8, 79.2),
                     (31.9, 83.5), (38.8, 89.6), (46.3, 80.3), (54.8, 69.3), (61.0, 68.5), (61.0, 35.5)] +
                    dwb_arc(DAEWOO_BACK['r_belt'], 14.7, 84.4))
assert DWB_COURT_ASPH.is_valid and DWB_LOT_ASPH.is_valid
DWB_ZONE = unary_union([_uvp(q_) for q_ in (DWB_COURT_UV, DWB_AREA_UV, DWB_FLOOR_UV, DWB_HIGH_UV)] + [DWB_COURT_ASPH, DWB_LOT_ASPH]).buffer(0.6)
_dw_road = LineString([q_ for q_, _ in DWB_ROAD] + [(193.1, 568.4), (201.4, 571.3)]).buffer(3.0)
for _ly in ('asphalt', 'pavers'):
    draw_poly(_ly, DWB_ZONE.difference(_dw_road), 0)
draw_poly('asphalt', DWB_COURT_ASPH)
draw_poly('asphalt', DWB_LOT_ASPH)
# 대우관 앞 · 상뜰 (DAEWOO, SANG above; reference/고증/3.6): OSM's drives and walks before the hall and the 상뜰 as first
# laid out give way to the photos': the asphalt drive across the terrace from the west drive to the east one, paving
# before the tower's door, and the 상뜰 on the hall's axis -- the round lawn in its paved ring, the broad walk from the
# podium's forecourt through it to the head of the south flight, the diamond's four walks and the cross walk out to
# the two drives.  (OSM's drive along the east wing's side goes: the wing stands there, and the photos have lawn and
# trees between it and the road to 북문.)
_pd = DAEWOO['podium']
DW_FRONT_ZONE = _uvh([(_tu0, _tv0 - 1.0), (64.5, _tv0 - 1.0), (64.5, 28.5), (_tu0, 28.5)])
DW_FRONT_PAV = _uvh([(_tu0 - 1.3, -30.5), (56.0, -30.5), (56.0, _tv0 - 1.0), (_tu0 - 1.3, _tv0 - 1.0)])
_sgn = {k_: SG(*v_) for k_, v_ in SANG_NODES.items()}
_sfw = LineString([(66.6, 414.3), SANG_FOOT, (137.7, 396.5)])
SANG_ZONE = unary_union([Polygon(SANG_DIAMOND_RNG).buffer(4.5), Polygon(SANG_DIAMOND).buffer(4.5),
                         LineString([SG_RNG(0.0, -6.5), SANG_DIAMOND_RNG[2], SANG_FOOT]).buffer(3.6),
                         LineString([WD(23.5, 0), SANG_RNG]).buffer(3.6)]).difference(_sfw.buffer(2.2))
SANG_WALKS = dict(                       # (the walks' middle lines and widths)
    axis=([dh_xy(DW_UC, _pd['end']), SANG, _sgn['S']], 4.7),
    diamond=([_sgn['N'], _sgn['W'], _sgn['S'], _sgn['E'], _sgn['N']], 3.4),
    cross=([SG(SANG_NODES['W'][0] - 12.0, SANG_NODES['W'][1]), _sgn['W'], _sgn['E'], SG(SANG_NODES['E'][0] + 1.5, SANG_NODES['E'][1])], 3.8))
SANG_PAVE = unary_union([Point(*SANG).buffer(6.85), LineString([_sgn['S'], SANG_FOOT]).buffer(2.75, cap_style='flat'),
                         _uvh([(DW_UC - _pd['court'], _pd['end']), (DW_UC + _pd['court'], _pd['end']),
                               (DW_UC + _pd['court'], _pd['face']), (DW_UC - _pd['court'], _pd['face'])])] +
                        [LineString(l_).buffer(w_ / 2, cap_style='flat', join_style='mitre') for l_, w_ in SANG_WALKS.values()])
DW_TERR_DRIVE = _uvh([(DAEWOO['u0'] - 5.0, _tv0), (62.3, _tv0), (62.3, _tv1), (DAEWOO['u0'] - 5.0, _tv1)])
for _ly in ('asphalt', 'pavers'):
    draw_poly(_ly, DW_FRONT_ZONE, 0)
draw_poly('pavers', DW_FRONT_PAV.union(SANG_ZONE), 0)
draw_poly('asphalt', DW_TERR_DRIVE)
draw_line('asphalt', [dh_xy(59.3, _tv0 - 6.0), dh_xy(59.3, _tv0 + 0.5)], 4.0)        # (the east drive's head)
draw_poly('pavers', _uvh([(DW_UC - 5.5, _tv1), (DW_UC + 5.5, _tv1), (DW_UC + 5.5, 0.0), (DW_UC - 5.5, 0.0)]))
draw_poly('pavers', SANG_PAVE)
draw_poly('pavers', Point(*SANG).buffer(SANG_LAWN + 0.1), 0)    # (the lawn inside the curb)
# (the road north of the hall where the cars use it, from the bend to the mouth: OSM's line bows up to 1.2 m north
# of their way there, and the 1997 photos' road is 6.2 - 6.5 m wide)
draw_line('asphalt', [tuple(q_) for q_ in TR_E[TR_EKH + 4:]], 6.6)
draw_poly('pavers', _uvp(DWB_FLOOR_UV).difference(footprint(ways[242897922])))
spl = np.stack([np.array(layers['asphalt']), np.array(layers['pavers']), np.array(layers['dirt'])], -1).astype(np.float32)
# priority: asphalt > pavers > dirt
spl[..., 1] = np.minimum(spl[..., 1], 255 - spl[..., 0])
spl[..., 2] = np.minimum(spl[..., 2], 255 - spl[..., 0] - spl[..., 1])
for ch in range(3):
    spl[..., ch] = ndimage.gaussian_filter(spl[..., ch], 0.7)
os.makedirs(os.path.join(ROOT, 'web/public/assets/textures'), exist_ok=True)
Image.fromarray(np.clip(spl, 0, 255).astype(np.uint8), 'RGB').save(
    os.path.join(ROOT, 'web/public/assets/textures/ground_splat.png'), optimize=True)
# 언더우드관 정원 (UWG): the layout drawn again over the one the game had, for the game's map only (splat_aa below):
# spl above, which the random planting, the decals and the leaf map read, keeps the old one so their draws stay.
# Paved: the walks along the side halls (the drive along 스팀슨관, 아펜젤러관's walk to its front) and before
# 언더우드관.  Gravel (마사토, the 2010 roadview and the 2011 photo; pale in the 1994 aerial photo): the ring round the
# platform, the radial walks, the cross walk, the axis walk to the tower and a walk inside the south hedge.  Lawn in
# the beds and between them and the hedges
_uwz = UW_GARDEN.union(garden.buffer(1.6))
for _ly in ('asphalt', 'pavers', 'dirt'):
    draw_poly(_ly, _uwz, 0)
_UG = lambda pts: Polygon([uwg_xy(u, v) for u, v in pts])
for _pz in (_UG([(-28.0, -28.5), (-24.0, -28.5), (-24.0, 50.0), (-28.0, 50.0)]),
            _UG([(22.6, -28.5), (33.0, -28.5), (33.0, 50.0), (22.6, 50.0)]),
            _UG([(-28.0, 43.4), (33.0, 43.4), (33.0, 50.0), (-28.0, 50.0)])):
    draw_poly('pavers', _pz)
draw_poly('dirt', Point(*UW_STATUE).buffer(UW_RING))
for _e in ((0.0, 22.6), (21.6, 21.6), (23.2, 0.0), (23.2, -23.2), (0.0, -25.3), (-20.6, -20.6), (-21.6, 0.0), (-21.6, 21.6)):
    draw_line('dirt', [UW_STATUE, uwg_xy(*_e)], UW_WALK_W)
draw_line('dirt', [uwg_xy(-24.0, 22.6), uwg_xy(22.6, 22.6)], 2.8)
draw_line('dirt', [uwg_xy(0.0, 22.6), uwg_xy(0.0, 43.4)], 3.0)
draw_line('dirt', [uwg_xy(-20.6, -25.3), uwg_xy(22.6, -25.3)], 2.0)
draw_line('dirt', [uwg_xy(-20.6, -25.3), uwg_xy(-20.6, -20.6), uwg_xy(-23.6, -20.6)], 2.0)
# Dry lawn (issue #10): in the May 1997 photo the lawn east of 백양로 between the gate and 백주년기념관 is worn, yellowed
# grass with bare earth showing (the cars park on it in the shade), and so is the ground inside the 화단섬 hedge
# between the azaleas and the trees.  A grey mask over the splat's rectangle at 1 m (web/src/terrain.js mixes the
# lawn there to straw and patches of earth); the trodden car row darker still.
DRY_RES = 1.0
_dry = Image.new('L', (int(SW * SPLAT['res'] / DRY_RES), int(SH * SPLAT['res'] / DRY_RES)), 0)
_dd = ImageDraw.Draw(_dry)
_tp = lambda x, y: ((x - SPLAT['x0']) / DRY_RES, (SPLAT['y1'] - y) / DRY_RES)
# (the worn lawn reaches right up to 백양로's planting strip, wider than EAST_LAWN, whose west edge keeps the trees
# off the road)
_dl = Polygon([(-140, -404), (-18, -404), (-18, -266), (-44, -258), (-140, -258)]).difference(bline.buffer(ROAD_HALF + 0.8))
_dl = max(_dl.geoms, key=lambda g_: g_.centroid.x) if hasattr(_dl, 'geoms') else _dl
for _poly, _v in ((_dl, 235), (ISL.buffer(-1.0), 190)):
    _dd.polygon([_tp(x, y) for x, y in _poly.exterior.coords], fill=_v)
_dd.line([_tp(x, y) for x, y, _ in LOT_C], fill=255, width=9)
_dry = ndimage.gaussian_filter(np.array(_dry).astype(np.float32), 2.5)
# Paving kinds (issue #85), in the same map's G and B (R stays the dry lawn): where the splat has paving, the terrain
# shader lays blocks of another kind instead of the campus's red interlocking pavers (web/src/terrain.js).
#  - G only: 상뜰's dark grey rectangular blocks, about 20 x 10 cm in rows across the walks, the long side along the
#    hall (reference/대우관_2024_정면과_상뜰.jpg; the 2008 roadview 2381737 shows the same walks)
#  - B only: red clay bricks in rows across the walk, the long side along the statue's u axis: the eagle's north and
#    south walks (2011 roadview 1017220175 · 1017220172: the walks up to its round dais)
#  - G and B: the same bricks a quarter turned: its east and west walks
# Coverage at 1 m from the outlines drawn 8 times finer, so the shader's cut at one half runs within ~10 cm of them.
_KIND_SS = 8


def _kind_cover(geoms, W_, H_, res=DRY_RES):
    out_ = np.zeros((H_, W_), np.float32)
    for g_ in geoms:
        for p_ in (g_.geoms if hasattr(g_, 'geoms') else [g_]):
            if p_.is_empty or p_.geom_type != 'Polygon':
                continue
            x0_, y0_, x1_, y1_ = p_.bounds
            i0, i1 = max(0, int((x0_ - SPLAT['x0']) / res) - 1), min(W_, int((x1_ - SPLAT['x0']) / res) + 2)
            j0, j1 = max(0, int((SPLAT['y1'] - y1_) / res) - 1), min(H_, int((SPLAT['y1'] - y0_) / res) + 2)
            k_ = _KIND_SS / res
            im_ = Image.new('L', ((i1 - i0) * _KIND_SS, (j1 - j0) * _KIND_SS), 0)
            d_ = ImageDraw.Draw(im_)
            P_ = lambda x, y: ((x - SPLAT['x0']) * k_ - i0 * _KIND_SS, (SPLAT['y1'] - y) * k_ - j0 * _KIND_SS)
            d_.polygon([P_(x, y) for x, y in p_.exterior.coords], fill=255)
            for h_ in p_.interiors:
                d_.polygon([P_(x, y) for x, y in h_.coords], fill=0)
            a_ = np.array(im_, np.float32).reshape(j1 - j0, _KIND_SS, i1 - i0, _KIND_SS).mean((1, 3))
            out_[j0:j1, i0:i1] = np.maximum(out_[j0:j1, i0:i1], a_)
    return out_


_DW, _DH = _dry.shape[1], _dry.shape[0]
_sang_pave = SANG_PAVE.buffer(0.6)
_eu = EAGLE_WALK_W / 2 + 0.2
_eband = Polygon([eagle_xy(-40.0, -_eu), eagle_xy(40.0, -_eu), eagle_xy(40.0, _eu), eagle_xy(-40.0, _eu)])
_brick_ew = EAGLE_PAVED.intersection(_eband)
_kind_g = _kind_cover([_sang_pave, _brick_ew], _DW, _DH)
_kind_b = _kind_cover([EAGLE_PAVED], _DW, _DH)
PAVE = dict(ang=[round(math.atan2(SG_E[1], SG_E[0]), 4), round(EAGLE_ROT, 4)])     # the kinds' long sides (G, B)
Image.fromarray(np.clip(np.stack([_dry, _kind_g, _kind_b], -1), 0, 255).round().astype(np.uint8), 'RGB').save(
    os.path.join(ROOT, 'web/public/assets/textures/ground_dry.png'), optimize=True)

# ---------------------------------------------------------------------------
# Vegetation
# ---------------------------------------------------------------------------
trees = []        # [species, x, y, scale, rot]
DROP_TREES = []   # trees planted by the line as first laid that the moved road (#162) runs over: cleared at the end


def drop_tree(t_):
    DROP_TREES.append(t_)


def clear_trees(zone, zone_rng=None, old=None):
    """trees[:] less those in the way: in zone_rng (zone if None) at their first places (rxy; or old(x, y) True), as
    the list was first cleared, so that it keeps its order; those the moves of #162 brought into zone go at the end"""
    gone_ = old or (lambda x_, y_: (zone if zone_rng is None else zone_rng).contains(Point(x_, y_)))
    trees[:] = [t_ for t_ in trees if not gone_(*rxy(t_))]
    for t_ in trees:
        if zone.contains(Point(t_[1], t_[2])):
            drop_tree(t_)


def to_new(x, y):
    """a point at its place along and across the line as first laid (BLINE_RNG), put at that place by the moved one:
    what stands at (x, y) by the first line is in a zone laid out along the moved line if to_new(x, y) is"""
    s_ = float(BLINE_RNG.project(Point(x, y)))
    cx_, cy_, a_ = along_raw(s_, 0.0, BLINE_RNG)
    return along_raw(s_, (x - cx_) * -math.sin(a_) + (y - cy_) * math.cos(a_))[:2]


def rxy(t_):
    """where a tree stood as the planting first put it: the trees that follow 백양로, photo A or the halls moved by
    #162 carry it in a sixth place (dropped when written out); the clearing below asks it of them, so that the list
    keeps the order it had (the web picks each tree's model by its place in it)"""
    return tuple(t_[5]) if len(t_) > 5 else (t_[1], t_[2])


shrubs = []       # [kind, x, y, scale, rot]
asph = ASPH_PRE                        # (the ground before 중앙도서관's 1997 beds and the eagle's round: see above)
pav = PAV_PRE


def blocked(x, y, pad=4.0):
    px, py = to_px(x, y)
    if not (0 <= px < SW and 0 <= py < SH):
        return False
    r = int(pad / SPLAT['res'])
    x0, x1, y0, y1 = int(px) - r, int(px) + r, int(py) - r, int(py) + r
    x0, y0 = max(0, x0), max(0, y0)
    return bool(asph[y0:y1, x0:x1].any() or pav[y0:y1, x0:x1].any())

ball_buf = ball.buffer(5)
ball_buf_rng = ball_rng.buffer(5)
# Openings in the verge / outer strip where side roads and the 정문 화단섬 road meet 백양로
GAPS = []          # (s, side, half_width)
for pth in paths_out:
    if pth['kind'] in ('footway', 'path', 'steps', 'pedestrian'):
        continue
    ls_ = LineString(pth['pts'])
    hit = ls_.intersection(bline.buffer(ROAD_HALF + 0.5))
    if hit.is_empty or bline.distance(ls_) > ROAD_HALF:
        continue
    for side in (-1, 1):
        edge = bline.offset_curve(side * (E_CURB0 + 0.5))
        cut = ls_.intersection(edge)
        for g in (cut.geoms if hasattr(cut, 'geoms') else [cut]):
            if g.is_empty or g.geom_type != 'Point':
                continue
            s_ = float(bline.project(g))
            if 6 < s_ < L - 6:
                GAPS.append((round(s_, 1), side, round(pth['w'] / 2 + 1.5, 1)))


def in_gap(s, side, pad=0.0, outer=False, verge=False):
    if any(abs(s - c) < 3.0 + pad for c in CROSS):
        return True
    r0, r1 = (0.0, 0.0) if outer else MOUTH[3:5]       # (out on the planting strip the corners are not rounded)
    if side == MOUTH[0] and MOUTH[1] - r0 - pad < s < MOUTH[2] + r1 + pad + (MOUTH[5] if verge else 0.0):
        return True                 # the side-road mouth: no verge, sidewalk or planting strip (the verge stops short)
    return any(sd == side and abs(s - g) < hw + pad for g, sd, hw in GAPS)


# (the gaps as the ginkgo rows first read them, on the line as first laid: the crossings where they stand now, the
# side-road mouth through photo A's camera of before #162, the side roads' gaps (GAPS); the rows' draws follow these)
MOUTH_RNG = (1, 62.0, 98.8, 3.0, 0.6, 2.7)
GAPS_RNG = [(570.0, -1, 4.5), (570.2, 1, 4.5), (447.2, 1, 4.5), (604.8, -1, 4.5), (605.3, 1, 4.5)]


def in_gap_rng(s, side, pad=0.0):
    """in_gap(s, side, pad) as the ginkgo rows first read it"""
    if any(abs(s - c) < 3.0 + pad for c in [CROSS[0], CROSS[1]] + CROSS_RNG[2:]):
        return True
    if side == MOUTH_RNG[0] and MOUTH_RNG[1] - MOUTH_RNG[3] - pad < s < MOUTH_RNG[2] + MOUTH_RNG[4] + pad:
        return True
    return any(sd == side and abs(s - g) < hw + pad for g, sd, hw in GAPS_RNG)


# 화단 띠가 끊기는 곳 (reference/고증.md 2.3): besides the crossings and the side-road gaps, the openings in the verge
# that the 2008 and the 2010 roadview both show, [side, s0, s1]; blender/road.py gives every opening round kerbed ends
# and a ramp down to the carriageway (campus.json baekyangro breaks).  대강당 계단 발치: the flight's foot at s 498 -
# 500 m (4.5), the roadview's opening with its round south end just short of it.  Only the verge's shrubs make way
# (after their random draw, so the planting elsewhere keeps its layout)
VERGE_BREAKS = [[-1, 496.5, 503.5]]                 # (the foot of 대강당's flight: its posts' outer faces at s 497.4 - 502.9)
# 학생회관 앞: the verge cut into four short islands (A - D) with round ends, the openings at the carriageway's level
# with a row of bollards each (2008-08 2480542 - 2480547 and 2010-12 1016786015 - 018, nodes 186 - 189, solved together
# on the library's, 학생회관's and 백양관's corners: tips within 0.3 m in both years, the frame +-1.2 m).  The crossing
# takes the 6 m between A and B (CROSS); the last opening, 2.4 m, is the passage to the plaza north of the hall
VERGE_BREAKS += [[-1, 368.3, 371.9], [-1, 386.5, 393.6], [-1, 396.1, 398.4], [-1, 401.9, 404.3]]
VERGE_BREAKS.append([BK_MOUTH[0], BK_MOUTH[1], BK_MOUTH[2]])      # (백양관 북쪽 주차장 어귀)
VERGE_BREAKS += [list(AUD_SIDE_MOUTH), list(AUD_YARD_MOUTH)]      # (대강당 북쪽 곁길 어귀 · 별관 앞마당 어귀)
VERGE_BREAKS.append(list(LIB_MOUTH))                              # (중앙도서관 앞 광장)
VERGE_BREAKS.append(list(JUNC_MOUTH))                             # (독수리상 서쪽 옆길 어귀)


def in_break(s, side, pad=0.0):
    return any(sd == side and b0 - pad < s < b1 + pad for sd, b0, b1 in VERGE_BREAKS)


def in_eng_mouth(s, side, pad=0.0):
    # the planting strip's openings (STRIP_OPEN: 제1공학관 앞 진입로, 백양관 앞 계단 길과 북쪽 주차장 어귀): only the
    # hedge's appends ask, after its random draw, and the row's ginkgos there go at the end (ENG_COURT, BK_COURT), so
    # that the planting elsewhere keeps its layout
    return any(side == o_[0] and o_[1] - pad < s < o_[2] + pad for o_ in STRIP_OPEN)


def in_gap_old(s, side, pad=0.0):
    # the gaps before the side-road mouth (a 10 m opening in the verge only) and the crossings where they were first
    # put (CROSS_RNG); used to keep the random draws
    if any(abs(s - c) < 3.0 + pad for c in CROSS_RNG):
        return True
    return any(sd == side and abs(s - g) < hw + pad for g, sd, hw in GAPS_RNG + [(82.3, 1, 5.0)])


# 백양로 ginkgo rows (은행나무 가로수) in the outer planting strip with a clipped hedge, and the boxwood verges
strip_fill = random.Random(131)          # (the shrubs where a crossing first stood, CROSS_RNG)
for side in (-1, 1):
    s = 22.0
    while s < L_RNG - 30:
        x, y, _ = along_raw(s, side * (E_WALK + ROAD['strip'] * 0.5))
        # (1997 photo: on the west side the row only starts past the 화단섬; by the island, its hedge and young trees)
        if not in_gap_rng(s, side, 1.0) and not ball_rng.buffer(2).contains(Point(*along_rng(s, side * (E_WALK + ROAD['strip'] * 0.5))[:2])) \
                and not (side > 0 and s < 122):
            trees.append(['ginkgo', round(x, 2), round(y, 2), round(rng.uniform(0.85, 1.0), 2), round(rng.uniform(0, 6.28), 2),
                          tuple(round(v_, 2) for v_ in along_rng(s, side * (E_WALK + ROAD['strip'] * 0.5))[:2])])
            if in_gap(s, side, 1.0) or ball.buffer(2).contains(Point(x, y)):
                drop_tree(trees[-1])        # (where the moved road has a gap or a hall: cleared at the end)
        s += 8.5
    # (the random draws follow the gaps as they were before the mouth was opened, so the rest of the campus keeps
    # its random layout)
    s = 18.0
    while s < L_RNG - 24:
        if not in_gap_old(s, side, 0.6):
            x, y, a = along_raw(s, side * (E_WALK + ROAD['strip'] * 0.5))
            if not ball_rng.buffer(1).contains(Point(*along_rng(s, side * (E_WALK + ROAD['strip'] * 0.5))[:2])):
                sc_ = round(rng.uniform(0.95, 1.05), 2)
                if not in_gap(s, side, 0.6, outer=True) and not in_eng_mouth(s, side, 0.6) and not ball.buffer(1).contains(Point(x, y)):
                    shrubs.append(['hedge_low', round(x, 2), round(y, 2), sc_, round(a, 3)])
        elif not in_gap(s, side, 0.6, outer=True) and not in_eng_mouth(s, side, 0.6):
            # (where a crossing first stood: planted from strip_fill's numbers)
            x, y, a = along_raw(s, side * (E_WALK + ROAD['strip'] * 0.5))
            if not ball.buffer(1).contains(Point(x, y)):
                shrubs.append(['hedge_low', round(x, 2), round(y, 2), round(strip_fill.uniform(0.95, 1.05), 2), round(a, 3)])
        s += 1.5
    # (the verge: every other shrub a 향나무 clipped in two tiers on a bare trunk -- the April 2011 roadview has
    # them 5 - 6 m apart along every verge from the gate to the library, the May 1997 photo flat-topped pads twice as
    # close, some with a darker skirt -- round boxwood between them; the kinds take no random numbers)
    s, k_ = 14.0, 0
    while s < L_RNG - 20:
        if not in_gap_old(s, side, 0.8):
            x, y, _ = along_raw(s, side * (E_CURB + ROAD['verge'] * 0.5))
            sc_ = round(rng.uniform(0.95, 1.1), 2)
            if not in_gap(s, side, 0.8, verge=True) and not in_break(s, side, 0.8):
                if k_ % 2 == 0:
                    shrubs.append(['juniper_tiers', round(x, 2), round(y, 2), sc_, round((k_ * 2.39996) % 6.2832, 3)])
                else:
                    shrubs.append(['topiary_round', round(x, 2), round(y, 2), sc_, 0])
        elif not in_gap(s, side, 0.8, verge=True) and not in_break(s, side, 0.8):
            # (where a crossing first stood: planted from strip_fill's numbers)
            x, y, _ = along_raw(s, side * (E_CURB + ROAD['verge'] * 0.5))
            sc_ = round(strip_fill.uniform(0.95, 1.1), 2)
            if k_ % 2 == 0:
                shrubs.append(['juniper_tiers', round(x, 2), round(y, 2), sc_, round((k_ * 2.39996) % 6.2832, 3)])
            else:
                shrubs.append(['topiary_round', round(x, 2), round(y, 2), sc_, 0])
        s += 2.6
        k_ += 1
# 학생회관 앞의 짧은 섬(VERGE_BREAKS): the 2008 / 2010 roadview has a clipped two-tier 향나무 in the middle of the
# islands A, C and D (B has the lamp and a shrub of the row above); the row's 2.6 m steps miss them (strip_fill's
# numbers, no draw from rng)
for _s in (373.7, 394.85, 400.15):                   # (the islands' middles: A 371.9 - 375.5, C 393.6 - 396.1, D 398.4 - 401.9)
    x, y, _ = along_raw(_s, -(E_CURB + ROAD['verge'] * 0.5))
    shrubs.append(['juniper_tiers', round(x, 2), round(y, 2), round(strip_fill.uniform(0.9, 1.0), 2), round(strip_fill.uniform(0, 6.28), 3)])
N_ROWS = len(trees)

# 정문 화단섬: hedge border, red azaleas massed along the south and east edges, pine + maple + zelkova
ring = ISL.buffer(-0.8).exterior
for d_ in np.arange(0, ring.length, 1.5):
    p = ring.interpolate(d_)
    q = ring.interpolate(min(ring.length, d_ + 0.5))
    shrubs.append(['hedge_low', round(p.x, 2), round(p.y, 2), 1.0, round(math.atan2(q.y - p.y, q.x - p.x), 3)])
# azaleas massed in two rows just inside the hedge along the south and the 백양로 (east) edges (their own random
# numbers; as many are taken from rng as the island as first read took, so that the rest of the campus keeps its layout)


def _azalea_spots(isl, south, line=None):
    for off in (0.0, 1.15):
        rr = isl.buffer(-1.9 - off).exterior
        d_ = 0.0
        while d_ < rr.length:
            p = rr.interpolate(d_)
            if south.distance(p) < 3.5 or (line or bline).distance(p) < ROAD_HALF + 4.5:
                yield p
            d_ += 1.25


for _ in range(4 * sum(1 for _p in _azalea_spots(ISL_OLD, ISL_SOUTH_OLD, BLINE_RNG))):
    rng.random()
rng_i = random.Random(611)
for p in _azalea_spots(ISL, ISL_SOUTH):
    shrubs.append(['azalea_red', round(p.x + rng_i.uniform(-.15, .15), 2), round(p.y + rng_i.uniform(-.15, .15), 2),
                   round(rng_i.uniform(0.85, 1.05), 2), round(rng_i.uniform(0, 6.28), 2)])
# trees of the island, at their trunks' pixels in photo A.  Scales from the photo too: the crown top's pixel row above
# the trunk, through the photo's camera, gives the height (the island pine ~6 m, not 15)
for sp, px_, py_, sc in (('pine', 431, 1004, 0.55), ('zelkova', 652, 1012, 0.75), ('zelkova', 588, 988, 0.9),
                         ('maple', 195, 1043, 0.8), ('cherry', 257, 1048, 0.7)):
    trees.append([sp, *photo_ground(px_, py_), sc, round(rng.uniform(0, 6.28), 2), photo_ground(px_, py_, cam=PHOTO_A_RNG)])

# east lawn between the gate and 백주년기념관: a denser 1997 planting (zelkova, pine, cherry, maple)
lot_line = LineString([(x, y) for x, y, _ in LOT_E]).buffer(4.5)
lot_line_rng = LineString([along_rng(s, -(ROAD_HALF + 8.5))[:2] for s in np.arange(150, 196, 3.2)]).buffer(4.5)   # (as first laid)
east_pts = []
for k in range(6000):
    x, y = rng.uniform(-90, -18), rng.uniform(-404, -258)
    pt = Point(x, y)
    if not EAST_LAWN_RNG.buffer(-2).contains(pt) or ball_buf_rng.contains(pt) or lot_line_rng.contains(pt) or blocked(x, y, 2.5):
        continue
    if any((x - u) ** 2 + (y - v) ** 2 < 8.0 ** 2 for u, v in east_pts):
        continue
    east_pts.append((x, y))
    trees.append([rng.choice(['zelkova', 'zelkova', 'pine', 'pine', 'cherry', 'maple']), round(x, 2), round(y, 2),
                  round(rng.uniform(0.85, 1.2), 2), round(rng.uniform(0, 6.28), 2)])
    if not EAST_LAWN.buffer(-2).contains(pt) or lot_line.contains(pt) or ball_buf.contains(pt):
        drop_tree(trees[-1])

# 1997 photo: the east lawn is mostly open dry grass with a few big trees by 백주년기념관 and the car park; thin the planting
# (a separate RNG so the rest of the campus keeps its layout)
rng2 = random.Random(1997 + 7)
n0 = len(trees) - len(east_pts)
east_keep = []
for t_ in trees[n0:]:
    if -72 < t_[1] < -26 and -356 < t_[2] < -288:
        continue
    if t_[2] < -300 and rng2.random() < 0.55:
        continue
    if -310 < t_[2] < -290 and -64 < t_[1] < -20:
        continue        # keep the car row clear
    east_keep.append(t_)
trees[n0:] = east_keep
N_EAST = (n0, n0 + len(east_keep))
# trees read off the 1997 photo, kept as its pixels and placed through PHOTO_A at build time (photo_ground; issue #83:
# first read through the camera and the flat road of before #8): the red maple and the big zelkova between the island
# and 제1공학관's canopy; in front, south of the side road, a young ginkgo and a round cherry; on the east lawn the two
# big zelkovas shading the car row, the young cherry and the propped zelkova beyond it, the zelkova by the dark cars,
# the dark round pine by the sidewalk and the pines at the foot of 백주년기념관's low block.  Each: species, the trunk's
# foot (x, y px), the crown's top (row px) for its height (photo_top), or None and the height (m) kept.  The feet of the
# first big zelkova (behind the roadside ginkgo) and of the round pine (under its crown) are hidden: taken at the row
# of the next one's and at the crown's foot.  The pines by the block stand where the ground ray runs too flat (a pixel
# is metres there, and the ground through PHOTO_A lands them 10 - 14 m short of the block): on a line 2 m before the
# block's front, at their columns (photo_on_line).
SPECIES_H = {'ginkgo': 9.8, 'zelkova': 13.0, 'cherry': 7.5, 'maple': 6.5, 'oak': 12.5, 'pine': 11.0,
             'zelkova_young': 9.0, 'cherry_young': 5.4, 'metasequoia': 13.5, 'magnolia': 8.0, 'poplar': 17.0}   # blender/vegetation.py
_BLOCK_LINE = (np.array([round(float(v_), 2) for v_ in _c0_rv]) - np.array(CENT_BLOCK['t_side']) * 2.0,      # (the front's line
               np.array(CENT_BLOCK['t_front']))                                                            # as first read)
_BLOCK_LINE_RNG = (_BLOCK_LINE[0] - BLD_MOVE[324328422], _BLOCK_LINE[1])          # (the hall where first read)
PHOTO_TREES = [('maple', 274, 965, 838, None), ('zelkova', 410, 905, 762, None),
               ('ginkgo', 530, 1373, None, 8.33), ('cherry', 97, 1330, None, 4.5),
               ('zelkova', 1462, 930, 695, None), ('zelkova', 1610, 933, 702, None), ('cherry', 1747, 966, 850, None),
               ('zelkova', 1890, 977, None, 9.3), ('zelkova', 2082, 933, 715, None), ('pine', 1730, 1195, 1040, None),
               ('pine', 1855, 790, 677, 'block'), ('pine', 1762, 787, 736, 'block')]
for sp, px_, py_, pt_, h_ in PHOTO_TREES:
    if h_ == 'block':           # (height from foot to top in pixels at that depth: the ground there stands ~3 m over the
        x, y = photo_on_line(px_, *_BLOCK_LINE)                  # photo's through PHOTO_A, reference/고증.md 5장)
        h_ = (py_ - pt_) * photo_px(x, y, 30.0)[2] / (PHOTO_A['size'][1] / 2 / math.tan(math.radians(PHOTO_A['fov'] / 2)))
        xy_rng = photo_on_line(px_, *_BLOCK_LINE_RNG, cam=PHOTO_A_RNG)
    else:
        x, y = photo_ground(px_, py_)
        h_ = photo_top(x, y, pt_, px_) if pt_ is not None else h_
        xy_rng = photo_ground(px_, py_, cam=PHOTO_A_RNG)
    trees.append([sp, x, y, round(h_ / SPECIES_H[sp], 2), round(rng2.uniform(0, 6.28), 2), xy_rng])
    print('photo tree %s (%.1f, %.1f) %.1f m' % (sp, x, y, h_))
N_PHOTO_TREES = len(trees)          # trees up to here are placed and sized one by one (rows, island, photo trees)

# the lawn between the gate and the side road, west of 백양로: open grass in the 1997 photo but for the trees above
FRONT_LAWN = Polygon([(-160, -440), (-100, -440), (-100, -336), (-160, -322)])
# campus scatter (Poisson-ish)
species_campus = ['zelkova'] * 5 + ['pine'] * 3 + ['cherry'] * 1 + ['ginkgo'] * 1 + ['maple'] * 1
placed = [(t[1], t[2]) for t in trees]
from scipy.spatial import cKDTree


def far_enough(x, y, r):
    for px_, py_ in placed[-400:]:
        if (px_ - x) ** 2 + (py_ - y) ** 2 < r * r:
            return False
    return True

zone_campus = campus_zone_rng.buffer(30)
bbox = (-420, -430, 560, 600)
cand = 0
grid_cells = {}
CELL = 9.0
for k in range(60000):
    x = rng.uniform(bbox[0], bbox[2])
    y = rng.uniform(bbox[1], bbox[3])
    pt = Point(x, y)
    in_wood = woods_u.contains(pt)
    in_campus = zone_campus.contains(pt)
    if not (in_wood or in_campus):
        continue
    r = 6.5 if in_wood else 11.0
    key = (int(x // CELL), int(y // CELL))
    ok = True
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            for (qx, qy) in grid_cells.get((key[0] + dx, key[1] + dy), []):
                if (qx - x) ** 2 + (qy - y) ** 2 < r * r:
                    ok = False
    if not ok or ball_buf_rng.contains(pt) or blocked(x, y, 3.5 if in_wood else 4.5) or bcorr_rng.contains(pt):
        continue
    if amph_poly is not None and Point(*AMPH_CLEAR[:2]).distance(pt) < AMPH_CLEAR[2]:
        continue
    if any(z.contains(pt) for z in GARDEN_ZONES) or ISL_OLD.buffer(3).contains(pt) or EAST_LAWN_RNG.contains(pt) or lot_line_rng.contains(pt) \
            or FRONT_LAWN.contains(pt):
        continue
    sp = rng.choice(['pine', 'pine', 'oak', 'oak', 'zelkova']) if in_wood else rng.choice(species_campus)
    trees.append([sp, round(x, 2), round(y, 2), round(rng.uniform(0.8, 1.25), 2), round(rng.uniform(0, 6.28), 2)])
    if bline.distance(pt) < ROAD_HALF + 3.0 or lot_line.contains(pt) or ball_buf.contains(pt):    # (as on the east lawn)
        drop_tree(trees[-1])
    grid_cells.setdefault(key, []).append((x, y))
# the wood round the old amphitheater (reference/1997_구노천극장_마지막모습.jpg): two rows round the rim beyond its path,
# pines, oaks and zelkovas; behind the stage the tall narrow poplars of the photo (drawn with the narrow metasequoia,
# the nearest shape the game has) among oaks; pines on the banks beside the seat ends.  Its own RNG: as many draws are
# taken from rng as the ring of pines it replaced took, so that the rest of the campus keeps its layout
for _ in range(57):
    rng.random()
rng_a = random.Random(1933)
_near_halls = unary_union([Polygon(b['footprint']) for b in buildings
                           if Point(AMPH['cx'], AMPH['cy']).distance(Polygon(b['footprint'])) < 80]).buffer(3.0)


def _amph_tree(sp, x, y, sc):
    if not _near_halls.contains(Point(x, y)) and not blocked(x, y, 1.5):
        trees.append([sp, round(x, 2), round(y, 2), round(sc, 2), round(rng_a.uniform(0, 6.28), 2)])


trees = [t for t in trees if not (amph_d(t[1], t[2])[0] < AMPH_DEPTH + 2.6 and amph_d(t[1], t[2])[1] <= AMPH['seat_end'] + 6)]
for dd, step, ph in ((4.5, 7.0, 0.0), (10.5, 7.5, 0.5)):
    Ru, Rv, a_lim = AMPH['arena_rx'] + AMPH_DEPTH + dd, AMPH['arena_ry'] + AMPH_DEPTH + dd, AMPH['seat_end'] + 12
    n = int(math.radians(2 * a_lim) * (Ru + Rv) / 2 / step)
    for k in range(n + (ph == 0)):
        a = math.radians(-a_lim + 2 * a_lim * (k + ph + rng_a.uniform(-0.25, 0.25)) / n)
        x, y = amph_xy((Ru + rng_a.uniform(-1.5, 1.5)) * math.cos(a), (Rv + rng_a.uniform(-1.5, 1.5)) * math.sin(a))
        _amph_tree(rng_a.choice(['pine'] * 4 + ['oak'] * 3 + ['zelkova'] * 3), x, y, rng_a.uniform(0.9, 1.25))
for sp, u, v, sc in (('oak', -25.0, -13.0, 1.15), ('metasequoia', -25.5, -4.0, 1.4), ('metasequoia', -27.5, 3.5, 1.5),
                     ('metasequoia', -25.5, 9.5, 1.35), ('zelkova', -26.0, 16.5, 1.1), ('oak', -33.0, -9.0, 1.1),
                     ('oak', -32.0, 6.0, 1.15), ('oak', -34.0, 17.0, 1.0), ('zelkova', -33.5, -19.0, 1.1),
                     ('pine', -23.0, -17.0, 1.1), ('zelkova', -23.5, -10.0, 1.15), ('pine', -23.0, 15.0, 1.05),
                     ('oak', -30.5, 0.0, 1.2), ('oak', -31.0, -15.5, 1.1), ('pine', -30.0, 12.0, 1.1),
                     ('pine', -20.0, 18.0, 1.0), ('pine', -24.5, 23.0, 1.1), ('pine', -20.0, -18.0, 1.05), ('pine', -24.5, -23.0, 1.0),
                     ('oak', -21.0, -30.5, 1.15), ('zelkova', -29.0, -24.0, 1.1), ('oak', -21.0, 30.5, 1.1)):
    _amph_tree(sp, *amph_xy(u + rng_a.uniform(-0.8, 0.8), v + rng_a.uniform(-0.8, 0.8)), sc)

# 1997's lawn trees were young.  Measured in the 1997 aerial photo (crown tops above the trunks through its fitted
# camera) the scattered zelkovas, pines and cherries between the gate and 중앙도서관 stand at about 2/3 of the
# generic model heights (zelkova ~9 m, not 13-16); the ginkgo rows already match.  Scale the scattered trees there
# (not the rows or the hand-placed photo trees), easing back to full size past the library where the photo shows
# nothing, and keep the east lawn's below 8 m so 백주년기념관's dark porch shows over them as in the photo.
YOUNG = 0.65                        # (SPECIES_H: with the photo trees above)
n_young = 0
for i, t_ in enumerate(trees):
    if i < N_ROWS + 5 or N_EAST[1] <= i < N_PHOTO_TREES:
        continue                            # ginkgo rows, island trees, the photo's own trees
    pt = Point(*rxy(t_))                    # (the line and the places as first read, as the sizes were)
    if BLINE_RNG.distance(pt) > 120:
        continue
    f = float(np.interp(BLINE_RNG.project(pt), [0, 380, 480], [YOUNG, YOUNG, 1.0]))
    if f >= 0.999:
        continue
    sc_ = t_[3] * f
    cap = 8.0 if N_EAST[0] <= i < N_EAST[1] else 9.5
    sc_ = min(sc_, cap / SPECIES_H[t_[0]]) if f < 0.9 else sc_
    t_[3] = round(sc_, 2)
    n_young += 1
print('young 1997 trees scaled:', n_young)
# ... and they look young (issue #10): the photo's zelkovas and cherries up to here are thin, upright crowns in light
# new leaves, not the round full domes of the grown models.  Wherever a zelkova or cherry stands at under 0.9 of its
# grown size between the gate and the library (the scattered trees above, the island's and the photo's own), it
# becomes the young model, scaled to the same height.
n_vase = 0
for i, t_ in enumerate(trees):
    if i < N_ROWS or t_[0] not in ('zelkova', 'cherry') or t_[3] >= 0.9:
        continue
    if BLINE_RNG.distance(Point(*rxy(t_))) > 120 or BLINE_RNG.project(Point(*rxy(t_))) > 430:
        continue
    young_sp = t_[0] + '_young'
    t_[3] = round(t_[3] * SPECIES_H[t_[0]] / SPECIES_H[young_sp], 2)
    t_[0] = young_sp
    n_vase += 1
print('young crowns:', n_vase)
# 메타세쿼이아 (issue #10): tall narrow conifers in the photo's bottom right corner, east of 백양로 just inside the gate.
# Their trunks are below the frame: on the lawn behind the ginkgo row (clear of its trees, 14.7 and 19.9 m east of the
# centre line), where the columns of the two crowns (photo x 1930 and 2080) cross those lines through PHOTO_A, their
# heights from the crowns' tops (y 1000 and 1030; issue #83: first placed through the camera of before #8)
METASEQ = [(1930, 1000, 14.7), (2080, 1030, 19.9)]       # crown column, top row (px), offset east (m)
_mq, _mq_rng = [], []
for _px, _pt, _o in METASEQ:
    _a, _b = np.array(along_raw(20.0, -_o)[:2]), np.array(along_raw(70.0, -_o)[:2])
    _x, _y = photo_on_line(_px, _a, (_b - _a) / np.linalg.norm(_b - _a), 0.0, 100.0)
    _h = photo_top(_x, _y, _pt, _px)
    print('metasequoia s %.1f, %.1f m east: %.1f m' % (s_at(_x, _y), _o, _h))
    _mq.append((_x, _y))
    _a, _b = np.array(along_rng(20.0, -_o)[:2]), np.array(along_rng(70.0, -_o)[:2])
    _mq_rng.append(photo_on_line(_px, _a, (_b - _a) / np.linalg.norm(_b - _a), 0.0, 100.0, cam=PHOTO_A_RNG))
    trees.append(['metasequoia', round(_x, 2), round(_y, 2), round(_h / SPECIES_H['metasequoia'], 2), round(rng2.uniform(0, 6.28), 2),
                  _mq_rng[-1]])
trees[N_ROWS:] = [t_ for t_ in trees[N_ROWS:] if t_[0] == 'metasequoia' or min(math.hypot(rxy(t_)[0] - x_, rxy(t_)[1] - y_) for x_, y_ in _mq_rng) > 5.0]
for t_ in trees[N_ROWS:]:
    if t_[0] != 'metasequoia' and min(math.hypot(t_[1] - x_, t_[2] - y_) for x_, y_ in _mq) <= 5.0:
        drop_tree(t_)
def hedge_rect(W, u0, u1, v0, v1, gap=None, step=1.5):
    """low clipped boxwood round a bed; gap=(edge index, centre, half width) leaves an opening"""
    corners = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    for e in range(4):
        (ua, va), (ub, vb) = corners[e], corners[(e + 1) % 4]
        L_ = math.hypot(ub - ua, vb - va)
        (xa, ya), (xb, yb) = W(ua, va), W(ub, vb)
        a_ = math.atan2(yb - ya, xb - xa)
        for k in range(int(L_ / step) + 1):
            f_ = min(1.0, (k + 0.5) * step / L_)
            if gap and gap[0] == e and abs(f_ * L_ - gap[1]) < gap[2]:
                continue
            shrubs.append(['hedge_low', round(xa + (xb - xa) * f_, 2), round(ya + (yb - ya) * f_, 2), 1.0, round(a_, 3)])


def underwood_hedge_poly(poly, inset, step=1.5):
    """low clipped boxwood round a bed of any shape, inset m inside its edge, a piece every step m along it"""
    ring_ = poly.buffer(-inset, join_style=2).exterior
    for s_ in np.arange(step / 2, ring_.length, step):
        a_, b_ = ring_.interpolate(s_ - 0.05), ring_.interpolate(s_ + 0.05)
        p_ = ring_.interpolate(s_)
        shrubs.append(['hedge_low', round(p_.x, 2), round(p_.y, 2), 1.0, round(math.atan2(b_.y - a_.y, b_.x - a_.x), 3)])


def plant(kind, W, u, v, sc, rot=0.0):
    x, y = W(u, v)
    (trees if kind in ('pine', 'zelkova', 'ginkgo', 'cherry', 'maple', 'oak', 'magnolia', 'poplar') else shrubs).append(
        [kind, round(x, 2), round(y, 2), round(sc, 2), round(rot, 3)])


def axis_angle(W):
    (x0, y0), (x1, y1) = W(0, 0), W(0, 1)
    return math.atan2(y1 - y0, x1 - x0)


# 언더우드관 앞 정원 (UWG above; reference/고증.md 4.2): the statue's round platform at the hub, the beds between the
# radial walks edged with clipped boxwood (the 1990s photo behind the statue, reference/용재관.jpg; the 2010 roadview and
# reference/언더우드동상_2011_받침과_둘레단.jpg), round clipped boxwood in them; the two half-round beds beyond the cross
# walk with a clipped pine each side of the axis; clipped pines along the inner side of the side walks (2010 roadview,
# the skyview's rows of round crowns); a clipped boxwood hedge along the south edge, above the square (2008 roadview).
# (No crape myrtles: the 2010 / 2011 ones have no 1990s source, and no cone topiary.)  The random draws as before.
UW_BEDS = underwood_beds()
UWG = frame(*UW_STATUE, *_wuu)
_uwr = random.Random(1997 + 99)
_uw_own0 = (len(trees), len(shrubs))
for bed_ in UW_BEDS['radial']:
    underwood_hedge_poly(bed_, 0.45)
    c_ = bed_.representative_point()
    shrubs.append(['topiary_round', round(c_.x, 2), round(c_.y, 2), 1.15, 0.0])
for sg_ in (-1, 1):                      # the half-round beds: a clipped pine either side of the axis in each
    underwood_hedge_poly(UW_BEDS['half'][0 if sg_ < 0 else 1], 0.45)
    for du_ in (5.2, 11.0):
        plant('pine', UWG, sg_ * du_, 30.0, 0.42, rng.uniform(0, 6.28))
    for (du_, dv_) in ((3.6, 34.2), (12.6, 34.2), (8.1, 37.4)):
        plant('topiary_round', UWG, sg_ * du_, dv_, 1.0)
for sg_ in (-1, 1):                      # clipped pines along the side walks, the cross walk left open
    for v_ in (-15.0, -9.5, -4.0, 4.0, 9.5, 14.5, 18.5, 27.0, 32.5, 38.0):      # (clear of the walks' ends)
        plant('pine', UWG, sg_ * 21.6, v_, round(_uwr.uniform(0.32, 0.38), 2), _uwr.uniform(0, 6.28))
for k_ in range(24):                     # the hedge along the south edge, waist high
    (xa_, ya_), (xb_, yb_) = UWG(-22.0 + 44.0 * k_ / 24, -27.4), UWG(-22.0 + 44.0 * (k_ + 1) / 24, -27.4)
    shrubs.append(['hedge_blob', round((xa_ + xb_) / 2, 2), round((ya_ + yb_) / 2, 2), 1.0, round(math.atan2(yb_ - ya_, xb_ - xa_), 3)])
# tall trees on the square beyond the south hedge (clear of the view past the statue to 용재관 in reference/용재관.jpg),
# by the side walks south of the side halls and before 언더우드관;
# at the north-west corner, by the road before 언더우드관, a clipped pine instead
# (reference/2003_봄_언더우드관_앞길_벚나무.jpg: clipped pines and benches all along that side of the road)
for (u, v) in ((-17.0, -31.5), (-34.0, -12.0), (-18.8, 43.3), (31.0, -32.0), (35.0, -22.0), (17.0, 41.0)):
    if (u, v) == (-18.8, 43.3):
        plant('pine', UWG, u, v, 0.45, rng.uniform(0, 6.28))
        continue
    plant('zelkova', UWG, u, v, 1.15, rng.uniform(0, 6.28))
UW_OWN = {(t_[0], t_[1], t_[2]) for t_ in trees[_uw_own0[0]:] + shrubs[_uw_own0[1]:]}
# 연희관 앞 정원 (YEONHUI): a parterre of clipped boxwood as the photos and roadview before the 2013 works show it
# (reference/2003_가을_연희관앞정원과_교육관_북쪽계단.jpg from above to the north-west, 2003_봄_교육관에서_본_*; Kakao
# roadview 2008-08 and 2010-12 from 한경길 and the road before 연희관).  Each of the four beds: a low boxwood edging, a
# second band inside it with a strip of lawn between (the 2003 photo's parallel bands), tiered cones of clipped yew at
# its corners (in pairs either side of the axis from the south), a clipped pine and round boxwood in the middle.  The
# edgings of the two beds by the forecourt are a little higher (2010: brown winter boxwood up to the waist); the tall
# square-topped hedge blocks of reference/연희관_정면_2023.jpg are those edgings grown on after 2011.  The big clipped
# yew in the round planter; small round-headed shrubs and clipped pines along the top of the banks by the road and a
# low hedge along their foot; big zelkovas on the lawns down to 한경길 (2008: three in the south-east one), a magnolia
# at the south-west corner by the west drive (2011-04, in flower), ginkgos and round pines in the court before 연희관
rng7 = random.Random(1997 + 71)


def hedge_line(pts, kind='hedge_low', sc=1.0, step=1.5, closed=True):
    pts = list(pts) + ([pts[0]] if closed else [])
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        L_ = math.hypot(xb - xa, yb - ya)
        a_ = math.atan2(yb - ya, xb - xa)
        for k in range(max(1, int(L_ / step))):
            f_ = (k + 0.5) / max(1, int(L_ / step))
            shrubs.append([kind, round(xa + (xb - xa) * f_, 2), round(ya + (yb - ya) * f_, 2), sc, round(a_, 3)])


def _ring(g):
    """the exterior of a polygon (the largest part if it fell apart), [] if nothing is left"""
    if g.is_empty:
        return []
    if g.geom_type != 'Polygon':
        g = max(g.geoms, key=lambda q: q.area)
    return list(g.exterior.coords)[:-1]


_yd = Polygon(YH_DIAMOND).buffer(-1.4, join_style='mitre')
_ywalks = unary_union([LineString([YH_G(0, -20), YH_G(0, 20)]).buffer(2.2), LineString([YH_DIAMOND[1], YH_DIAMOND[3]]).buffer(1.7),
                       Point(*YH_C).buffer(5.8)])
_beds = _yd.difference(_ywalks)
# the forecourt at the head of the south flight (reference/연희관_정면_2023.jpg, Kakao roadview 2026: the same old slabs):
# concrete slabs whose joints radiate from a point between the tips of the two south beds, a drain of perforated
# concrete blocks across it at the head of the flight, the walk's centre joint on to the planter (blender/landmarks.py
# yeonhui_garden lays them on the garden plane)
_fcc = YH_G(0.0, -13.0)
_fc = Polygon(YH_DIAMOND).buffer(0.6, join_style='mitre').union(                          # (the walks, and the head of
    Polygon([YH_G(-2.4, -16.3), YH_G(2.4, -16.3), YH_G(2.4, -14.0), YH_G(-2.4, -14.0)])).intersection(   # the flight)
    Polygon([YH_G(-5.5, -16.3), YH_G(5.5, -16.3), YH_G(5.5, -9.5), YH_G(-5.5, -9.5)])).difference(_beds.buffer(0.1)).simplify(0.1)
_fc = max(_fc.geoms, key=lambda q: q.area) if _fc.geom_type != 'Polygon' else _fc
_dr = LineString([YH_G(-8.0, -15.95), YH_G(8.0, -15.95)]).intersection(_fc)
_fz = lambda x, y: round(yh_plane(*g_en(x, y)) + 0.02, 3)
_rays = []
for k in range(8):
    a_ = math.pi / 4 * k
    d_ = GF_E * math.cos(a_) + GF_N * math.sin(a_)
    seg_ = LineString([_fcc, tuple(np.array(_fcc) + d_ * 12.0)]).intersection(_fc)
    for g_ in ([seg_] if seg_.geom_type == 'LineString' else getattr(seg_, 'geoms', [])):
        if g_.geom_type == 'LineString' and g_.length > 0.5:
            _rays.append([[round(x, 2), round(y, 2), _fz(x, y)] for x, y in g_.coords])
_rays.append([[*map(lambda v: round(v, 2), YH_G(0.0, -13.0)), _fz(*YH_G(0.0, -13.0))],
              [*map(lambda v: round(v, 2), YH_G(0.0, -6.2)), _fz(*YH_G(0.0, -6.2))]])       # the walk's centre joint
YEONHUI['forecourt'] = dict(c=[*map(lambda v: round(v, 2), _fcc), _fz(*_fcc)],
                            poly=[[round(x, 2), round(y, 2), _fz(x, y)] for x, y in list(_fc.exterior.coords)[:-1]],
                            rays=_rays,
                            drain=[[round(x, 2), round(y, 2), _fz(x, y)] for x, y in (_dr.coords if _dr.geom_type == 'LineString'
                                                                                      else max(_dr.geoms, key=lambda q: q.length).coords)])
for bed in sorted(_beds.geoms if hasattr(_beds, 'geoms') else [_beds], key=lambda g: g.centroid.y):
    if bed.area < 20:
        continue
    bed = bed.simplify(0.3)
    south = g_en(bed.centroid.x, bed.centroid.y)[1] < 0
    hedge_line(_ring(bed), 'hedge_low', 1.15 if south else 1.0, step=1.5)                 # the edging
    band = bed.buffer(-1.6, join_style='mitre').simplify(0.3)
    if band.area > 6:
        hedge_line(_ring(band), 'hedge_low', 0.8, step=1.25)                           # the inner band
    # the tiered yews in the strip between the edging and the band, away from the axis (2010: in pairs either side of
    # it, the walk itself between round shrubs): at the bed's tip by the cross walk and halfway along its outer edge.
    # Five or six rounded pads stacked up a bare trunk (blender/shrubs.py yew_tiers; the December 2010 roadview from
    # 한경길, the August 2008 one from the drive along 교육관), not a smooth cone
    _in = _ring(bed.buffer(-0.8, join_style='mitre').simplify(0.5))
    _tip = max(_in, key=lambda q: abs(g_en(*q)[0]))
    _out = max(zip(_in, _in[1:] + _in[:1]), key=lambda ab: math.hypot(ab[1][0] - ab[0][0], ab[1][1] - ab[0][1]))
    for (px_, py_) in (_tip, ((_out[0][0] + _out[1][0]) / 2, (_out[0][1] + _out[1][1]) / 2)):
        shrubs.append(['yew_tiers', round(px_, 2), round(py_, 2), round(rng7.uniform(1.05, 1.2), 2), round(rng7.uniform(0, 6.28), 2)])
    core = bed.buffer(-2.7)
    cx_, cy_ = (core.centroid.x, core.centroid.y) if not core.is_empty else (bed.centroid.x, bed.centroid.y)
    trees.append(['pine', round(cx_, 2), round(cy_, 2), round(rng7.uniform(0.34, 0.4), 2), round(rng7.uniform(0, 6.28), 2)])
    _done = [(cx_, cy_)]
    for (px_, py_) in _ring(core.simplify(0.8)):
        if min(math.hypot(px_ - qx_, py_ - qy_) for qx_, qy_ in _done) > 2.6:
            _done.append((px_, py_))
            shrubs.append(['topiary_round', round(px_, 2), round(py_, 2), round(rng7.uniform(0.75, 0.9), 2), 0])
for k in range(6):                                                  # the clipped yew filling the round planter
    a_ = 2 * math.pi * k / 6
    shrubs.append(['topiary_round', round(YH_C[0] + 1.55 * math.cos(a_), 2), round(YH_C[1] + 1.55 * math.sin(a_), 2), 1.45, 0])
shrubs.append(['topiary_round', YH_C[0], YH_C[1], 1.9, 0])
for (a_, b_) in ((YH_DIAMOND[1], YH_DIAMOND[2]), (YH_DIAMOND[2], YH_DIAMOND[3])):
    a_, b_ = np.array(a_), np.array(b_)
    d_ = (b_ - a_) / np.linalg.norm(b_ - a_)
    o_ = np.array([-d_[1], d_[0]])                                   # (out of the diamond: north-west / north-east)
    _ax = 2.6 if a_[0] < YH_C[0] else 0.0                            # (clear of the north flight's walls)
    hedge_line([tuple(a_ + d_ * (1.0 + (0 if a_[0] < YH_C[0] else 3.6)) + o_ * 1.7),
                tuple(b_ - d_ * (1.0 + _ax) + o_ * 1.7)], closed=False)
for (p0, p1) in ((_FRONT_RD[0], _FRONT_RD[1]), (_FRONT_RD[1], _FRONT_RD[2])):
    p0, p1 = np.array(p0), np.array(p1)
    d_ = (p1 - p0) / np.linalg.norm(p1 - p0)
    s_ = np.array([d_[1], -d_[0]])                                   # (south, off the road)
    for k in range(int(np.linalg.norm(p1 - p0) / 3.4)):
        q_ = p0 + d_ * (1.7 + k * 3.4) + s_ * 4.6
        if np.linalg.norm(q_ - (_tn - _un * 1.0)) < 4.6 or not _ybank.buffer(-0.5).contains(Point(*q_)):
            continue
        if k % 2:                     # (every other one a low clipped pine: 2008 roadview along the road)
            trees.append(['pine', round(float(q_[0]), 2), round(float(q_[1]), 2), round(rng7.uniform(0.28, 0.32), 2),
                          round(rng7.uniform(0, 6.28), 2)])
        else:
            shrubs.append(['topiary_round', round(float(q_[0]), 2), round(float(q_[1]), 2), 1.15, 0])
_yh_face = unary_union([LineString([p_[:2] for p_ in r_]) for r_ in YEONHUI['wall']])
_yh_front = unary_union([LineString([p_[:2] for p_ in r_]).buffer(3.0, cap_style='flat').difference(
    _yh_offset(LineString([p_[:2] for p_ in r_]), 1.5).buffer(1.5, cap_style='flat')) for r_ in YEONHUI['wall']])   # (road side)


def _yh_behind(x_, y_, d_min=2.0):
    """a lawn tree set back behind the retaining wall's face, clear of the boxwood on its top"""
    p_ = Point(x_, y_)
    if _yh_face.distance(p_) >= d_min and not _yh_front.contains(p_):
        return x_, y_
    q_ = _yh_face.interpolate(_yh_face.project(p_))
    c_ = np.array(YH_C) - np.array([q_.x, q_.y])
    t_ = np.array([q_.x, q_.y]) - np.array(_yh_face.interpolate(max(0.0, _yh_face.project(p_) - 0.5)).coords[0])
    o_ = np.array([-t_[1], t_[0]]) / max(np.linalg.norm(t_), 1e-6)
    o_ = o_ if o_ @ c_ > 0 else -o_
    return float(q_.x + o_[0] * d_min), float(q_.y + o_[1] * d_min)


for (e_, n_, kind_, sc_) in ((-28, -13, 'zelkova', 1.1), (-19, -21, 'pine', 0.6), (-38, -2, 'zelkova', 0.95),
                             (23, -15, 'zelkova', 1.25), (13, -21, 'zelkova', 1.1), (33, -8, 'zelkova', 1.15)):
    x_, y_ = _yh_behind(*YH_G(e_, n_))     # (three stood on 한경길's verge or the drive, in front of the wall; the
    # west one stepped 2 m along it, off the wall and clear of the cherry over the drive)
    trees.append([kind_, round(x_, 2), round(y_, 2), sc_, round(rng7.uniform(0, 6.28), 2)])
for (u, v, kind_, sc_) in ((-6.0, -11.5, 'ginkgo', 1.25), (46.5, -10.5, 'ginkgo', 1.25), (6.0, -5.5, 'pine', 0.34),
                           (12.5, -5.5, 'pine', 0.3), (27.5, -5.5, 'pine', 0.3), (34.0, -5.5, 'pine', 0.34)):
    plant(kind_, WY, u, v, sc_, rng7.uniform(0, 6.28))
# the bank of clipped boxwood all along the top of the retaining wall (YEONHUI['wall']; the 2008 and 2010 roadview
# from 한경길: big rounded mounds close together, bronzed in December), clear of the lamp at the flight's head
rng_yw = random.Random(1997 + 80)
for r_ in YEONHUI['wall']:
    _bk = _yh_offset(LineString([p_[:2] for p_ in r_]), 0.85)
    for s_ in np.arange(0.8, _bk.length - 0.5, 1.55):
        q_, q2_ = _bk.interpolate(s_), _bk.interpolate(min(_bk.length, s_ + 0.5))
        a_ = math.atan2(q2_.y - q_.y, q2_.x - q_.x) + rng_yw.uniform(-0.2, 0.2)
        k_, sc_ = rng_yw.random(), rng_yw.uniform(0.9, 1.12)
        if math.hypot(q_.x - YEONHUI['lamp'][0], q_.y - YEONHUI['lamp'][1]) < 1.2:
            continue
        if k_ < 0.3:
            shrubs.append(['topiary_round', round(q_.x, 2), round(q_.y, 2), round(sc_ * 1.05, 2), 0])
        else:
            shrubs.append(['hedge_blob', round(q_.x, 2), round(q_.y, 2), round(sc_, 2), round(a_, 3)])
# 대우관 상뜰 (see SANG above): the small round-crowned pine in the round lawn, a broadleaf tree in the west lawn
# triangle by the ring and one in the north-east triangle under its upper walk (on the lawn, 1.6 m clear of the walk:
# it stood on the paving), low shrubs along the triangles' upper edges, and the big pines on the lawns outside the
# walks towards the terrace
ang_d = axis_angle(WD)
rng6 = random.Random(1997 + 61)
# (SGX: a place given on the diamond as OSM had it -- W -26.5, E 26.6, N 14.2, S -15.3 -- at the same place on the
# photos')
SGX = lambda e, n: SG(e * (SANG_NODES['W'][0] / -26.5 if e < 0 else SANG_NODES['E'][0] / 26.6),
                      n * (SANG_NODES['N'][1] / 14.2 if n > 0 else SANG_NODES['S'][1] / -15.3))
# (the clipped garden pines of the photos -- the one in the round lawn, those by the ring and before the podium -- are
# shrubs, DW_BEDS below.  The trees that stood in their places keep their places in the list and stand elsewhere: the
# round lawn's pine in the west triangle, the two zelkovas on the bank under the lower walks, the four tall pines before
# the podium's ends at the lawns' outer ends)
trees.append(['pine', *(round(float(c_), 2) for c_ in SG(-13.0, -3.0)), 0.5, 0.4])
for (e_, n_, kind_, sc_) in ((-19.0, -14.5, 'zelkova', 0.75), (18.5, -15.0, 'zelkova', 0.8), (13.0, -2.5, 'pine', 0.45)):
    x_, y_ = SGX(e_, n_)
    trees.append([kind_, round(x_, 2), round(y_, 2), sc_, round(rng6.uniform(0, 6.28), 2)])
# the planted bank under the diamond's lower walks, down to the footway, the south flight going down between its
# trees (issue #39; reference/대우관_정면_전경.jpg: spreading conifers east of the flight, broadleaves west of it)
for (e_, n_, kind_, sc_) in ((-7.5, -18.6, 'zelkova', 0.85), (-15.0, -15.5, 'maple', 0.75), (-23.0, -11.5, 'zelkova', 0.9),
                             (-30.5, -8.0, 'oak', 0.85), (-11.0, -20.5, 'cherry', 0.7), (7.5, -18.8, 'pine', 0.95),
                             (14.5, -16.0, 'pine', 0.8), (22.0, -12.0, 'zelkova', 0.85), (30.0, -8.5, 'pine', 0.85),
                             (11.5, -19.5, 'maple', 0.65)):          # (up the bank, off the footway's edge)
    x_, y_ = SGX(e_, n_)
    trees.append([kind_, round(x_, 2), round(y_, 2), sc_, round(rng6.uniform(0, 6.28), 2)])
for sg in (-1, 1):
    for (e_, n_, sc_) in ((-24.0, 17.2, 0.95), (-27.5, 13.5, 0.85), (-27.0, 7.2, 0.8)):   # (clear of the walks and the podium)
        x_, y_ = SG(sg * e_, n_)
        trees.append(['pine', round(x_, 2), round(y_, 2), sc_, round(rng6.uniform(0, 6.28), 2)])
    for t_ in (0.3, 0.5, 0.72):                              # shrubs along the inside of the upper (NW / NE) walk
        e_, n_ = -26.5 * t_, 14.2 * (1 - t_)
        x_, y_ = SGX(-sg * (e_ + 0.9), n_ - 1.9)
        shrubs.append(['bush', round(x_, 2), round(y_, 2), round(rng6.uniform(0.8, 1.05), 2), round(rng6.uniform(0, 6.28), 2)])
# 대우관 뒤 (Street View 2009): pointed conifers 4-5 m tall in a row along the two planters (none before the tower);
# on the lawn mound west of the car park young clipped pines and round shrubs; a few trees between the rows of cars
rng4 = random.Random(1997 + 23)
_pl = [(2.0, 17.6), (44.6, 17.6)]
_dwb_conifers = [(25.35, 48.8), (25.35, 51.2), (25.35, 53.6), (25.35, 56.0), (25.35, 58.4), (25.35, 60.6), (28.2, 64.4), (33.2, 64.6)]
for k in range(12):
    u_ = _pl[0][0] + 1.6 + k * (_pl[1][0] - _pl[0][0] - 3.2) / 11
    if abs(u_ - 23.55) < 6.5:
        continue                                                  # (the draws of the planter the game had there)
    # (the pointed conifers along the top of the wall over the portal and on the terrace behind it, DAEWOO_BACK)
    u_, v_ = _dwb_conifers.pop(0)
    x_, y_ = WD(u_ + rng4.uniform(-0.4, 0.4) * 0.5, v_)
    trees.append(['metasequoia', round(x_, 2), round(y_, 2), round(rng4.uniform(0.3, 0.36), 2), round(rng4.uniform(0, 6.28), 2)])
# (the young pines on the mound between the road and the upper car park, as the 1997 photos' crowns stand, and the two
# clipped ones in the planter round the theatre's west rim, behind the cars)
for (u_, v_, sc_) in ((30.5, 75.0, 0.42), (33.2, 73.4, 0.38), (35.6, 75.6, 0.45), (36.6, 72.4, 0.4), (10.5, 38.7, 0.36),
                      (33.4, 70.6, 0.44), (27.5, 71.8, 0.4), (41.0, 71.3, 0.46), (23.0, 66.0, 0.4), (8.9, 34.8, 0.3)):
    plant('pine', WD, u_, v_, sc_, rng4.uniform(0, 6.28))
_n_sh0 = len(shrubs)
_diag = LineString([(-13.0, 29.0), (10.0, 62.0), (31.0, 83.0)])     # the drive to 북문 (OSM), in (u, v)
_n_sh = 0
while _n_sh < 10:
    u_, v_ = rng4.uniform(-8, 23), rng4.uniform(29, 72)
    if _diag.distance(Point(u_, v_)) > 4.5 and Point(u_, v_).y < 29 + (u_ + 13) * 1.43 \
            and LineString([(4, 39), (16, 55)]).distance(Point(u_, v_)) > 4 and LineString([(10, 62), (25, 55)]).distance(Point(u_, v_)) > 4:
        plant(rng4.choice(['topiary_round', 'bush']), WD, u_, v_, rng4.uniform(0.8, 1.2))
        _n_sh += 1
del shrubs[_n_sh0:]                                               # (their draws stay; the yard's shrubs below, DWB_SHRUBS)
for (u_, v_) in ((68.5, 34.0), (66.5, 58.0)):                     # on the bank below the road to 북문
    plant('maple', WD, u_, v_, 0.7, rng4.uniform(0, 6.28))
# 활천대 (reference/활천대_2009_연세춘추.jpg, 활천대_공사전_연세대블로그.jpg): on the lawn round its flagstones, low
# clipped shrubs on bare stems and a few small clipped pines scattered a few metres out, and red azaleas towards the
# eagle (the radii and draws of the first, 5.2 m basin's planting, moved out to the 9.5 m pool's flagstones)
_fx, _fy = FOUNTAIN['pos']
_FOUNTAIN_LAWN = Point(_fx, _fy).buffer(FOUNTAIN_SCATTER_R)
trees = [t_ for t_ in trees if not Point(*FOUNTAIN_RNG).buffer(FOUNTAIN_SCATTER_R).contains(Point(*rxy(t_)))]   # (as first cleared)
for t_ in trees:
    if _FOUNTAIN_LAWN.contains(Point(t_[1], t_[2])):
        drop_tree(t_)
for k, a_ in enumerate(np.radians([40, 105, 170, 235])):       # (none on the 2009 photo's side, south-east)
    rr_ = FOUNTAIN['pave'] + 2.6 + (k % 2) * 1.2
    trees.append(['pine', round(_fx + rr_ * math.cos(a_), 2), round(_fy + rr_ * math.sin(a_), 2), round(rng2.uniform(0.2, 0.26), 2),
                  round(rng2.uniform(0, 6.28), 2),
                  (round(FOUNTAIN_RNG[0] + rr_ * math.cos(a_), 2), round(FOUNTAIN_RNG[1] + rr_ * math.sin(a_), 2))])
for k in range(14):
    a_ = 2 * math.pi * (k + 0.5) / 14 + rng2.uniform(-0.12, 0.12)
    rr_ = FOUNTAIN['pave'] + 0.6 + rng2.uniform(0, 2.6) * 0.6
    shrubs.append(['topiary_round', round(_fx + rr_ * math.cos(a_), 2), round(_fy + rr_ * math.sin(a_), 2),
                   round(rng2.uniform(0.6, 0.85), 2), 0])
for k in range(9):
    a_ = math.atan2(EAGLE['pos'][1] - _fy, EAGLE['pos'][0] - _fx) + (k - 4) * 0.09
    rr_ = 12.1 + (k % 3) * 0.8
    shrubs.append(['azalea_red', round(_fx + rr_ * math.cos(a_), 2), round(_fy + rr_ * math.sin(a_), 2),
                   round(rng2.uniform(0.9, 1.1), 2), round(rng2.uniform(0, 6.28), 2)])
# --- the trees of the 2003 spring and autumn photos (reference/2003_*.jpg, taken by the user; reference/고증.md
# 3.18).  Where they show the old cherries in flower and the October ginkgos, plant them one by one (the trees
# scattered on those spots step aside):
#  - 2003_봄_백양로끝_핀슨관길_벚나무.jpg: from the square at the head of the steps up from the end of 백양로
#    (UW_STEPS), looking west-south-west along the top of their banks: big cherries, benches facing the square with a
#    green recycling box among them, the pair of stone 해태 at the steps' head (with the props below)
#  - 2003_봄_언더우드관_앞길_벚나무.jpg: from the road before 언더우드관 looking east, a row of them behind a low
#    hedge where the road ends, on the slope up towards 논지당
#  - 2003_봄_언더우드관정원_남쪽계단_벚나무.jpg: big cherries on the lawn along the garden's south edge, either side
#    of the axis at the head of the steps from the end of 백양로
#  - 2003_봄_교육관에서_본_연희관앞정원과_성암관.jpg: a big one on the verge across the drive from 교육관's front,
#    another on the far side of the garden before 성암관
#  - 2003_가을_*: the ginkgos at the corners of 연희관's wings reach its third floor (above: 1.25), a young yellow one
#    before its porch, a ginkgo and a reddening maple before 성암관's north wing
rng8 = random.Random(1997 + 2003)
PHOTO03 = []                                                      # (species, x, y, scale)
PHOTO03_PROPS = []                                                # (name, x, y, rot), added with the props below
# the drive west from the 삼거리 towards 핀슨관: big cherries along its south side (2011-04 roadview from the 삼거리
# looking west: 백양관 and its parked cars behind a hedge on the left, the drive bending right and climbing, cherries
# along its left).  The 2003 photo that had put benches, a bin and the 해태 (with a stair between them) here looks
# along the top of the steps' banks instead: they stand at the head of UW_STEPS (props below)
_br = LineString([(28.2, 124.1), (24.2, 125.3), (19.6, 127.2), (14.2, 131.1), (8.7, 136.9), (4.4, 143.6), (1.6, 149.5),
                  (-2.0, 160.5)])                                 # the drive west from the 삼거리 (OSM, 6 m)
_brs = _br.offset_curve(6.0)                                      # (its left: the south side)
_rows = [(t_[1], t_[2]) for t_ in trees[:N_ROWS]]
for k in range(6):
    q_ = _brs.interpolate(9.0 + 6.8 * k)                           # (past 백양로's sidewalk at its end)
    if min(math.hypot(q_.x - a_, q_.y - b_) for a_, b_ in _rows) < 4.0:
        continue                                                  # (not into 백양로's ginkgo rows)
    PHOTO03.append(('cherry', q_.x, q_.y, rng8.uniform(1.2, 1.4)))
for (x_, y_) in ((99.5, 246.5), (101.5, 239.5), (103.0, 232.5), (104.0, 225.5), (104.5, 218.5)):
    PHOTO03.append(('cherry', x_, y_, rng8.uniform(1.1, 1.3)))
hedge_line([(95.0, 214.0), (93.6, 249.0)], closed=False)
for u_ in (-19.4, -13.6, -7.8, 7.8, 13.6, 19.4):                  # (along the top of the banks, UW_STEPS)
    x_, y_ = st_xy(u_, UW_STEPS['v_head'] - 1.4)
    PHOTO03.append(('cherry', x_, y_, rng8.uniform(1.15, 1.3)))
PHOTO03 += [('cherry', 49.5, 317.5, 1.3), ('cherry', 106.0, 321.0, 1.05),
            ('ginkgo', 119.5, 317.5, 1.0), ('maple', 120.5, 328.5, 0.9)]
x_, y_ = WY(16.5, -3.8)
PHOTO03.append(('ginkgo', x_, y_, 0.42))
#  - the white-stemmed 은백양 by the foot of the steps up to 언더우드관 정원, just east of them (bare in April; the
#    same tree in the 2010 and 2026 roadview, a thick trunk forking at 4 - 5 m; the white trunk at the left of the
#    photo from the steps' head is this one, not a second tree by the drive west of the 삼거리)
#  - 목련: in the north-west corner of 연희관 앞 정원 behind the double lamp (2003_봄_교육관에서_본_*), and before
#    언더우드관 east of its tower (2024_봄_언더우드관_목련.jpg).  That one was young in 1997: in the December 2010
#    roadview (1016786670, 1016786671, 1016786656) it is a slender tree with a narrow crown, its top level with the
#    tower's door head, about 5.5 - 6 m, where the 2024 photo has it full grown (8 m).  Run back thirteen years at a
#    young magnolia's 25 - 30 cm a year it stood about 2.5 - 3 m in 1997: a newly planted tree of the nurseries' size
MAGNOLIA_UW_1997 = 0.38                                           # (x 8 m: 3 m)
PHOTO03.append(('poplar', *st_xy(6.6, 0.2), 1.0))
PHOTO03 += [('magnolia', 58.0, 339.5, 1.0), ('magnolia', *WU(-3.0, 40.6), MAGNOLIA_UW_1997)]
#  - 목련 at the south-west corner of 연희관 앞 정원, where the west drive leaves 한경길 (Kakao roadview 2011-04, in
#    full flower; taken to have stood there in 1997)
PHOTO03.append(('magnolia', 48.5, 307.5, 1.1))
_n0 = len(trees)
trees[N_PHOTO_TREES:] = [t_ for t_ in trees[N_PHOTO_TREES:]
                         if min(math.hypot(t_[1] - p_[1], t_[2] - p_[2]) for p_ in PHOTO03) > 4.2]
for sp_, x_, y_, sc_ in PHOTO03:
    trees.append([sp_, round(float(x_), 2), round(float(y_), 2), round(sc_, 2), round(rng8.uniform(0, 6.28), 2)])
print('2003 photo trees:', len(PHOTO03), '- scattered trees moved off them', _n0 - len(trees) + len(PHOTO03))
# --- front doors of the procedural halls (blender/generic.py builds them).  Every hall had one, and the outlines alone
# gave the generic halls none: walls of windows all round.  The 1996 graduation-album photos (2022 재상봉 기념문집,
# 「25년 전 우리는」; reference/고증.md) show what they were like: 과학관's and 백주년기념관's broad granite
# flights with low side walls and steel handrails, 백주년기념관's and 음악관's aluminium-framed glass doors and screens
# (음악관's under a deep canopy), 빌링슬리관's Tudor-arched door in its rubble wall under a stone hood.  Where: on the
# face the walks lead to.  OSM marks no entrances here, but its footways end at the doors; so the door goes where a
# walk comes closest, kept off the uphill side (where the ground stands above the floor the door would be buried)
# and away from other buildings, and the trees and shrubs that had been scattered on its steps step aside.
ENTRY_STYLES = ('modern', 'white', 'stone', 'brick', 'tile', 'stone_pale', 'gym', 'house')
# where the photos say otherwise: 과학관's door is in the middle of its east wing's south front, over the courtyard
# (1995 aerial photo: a broad flight up from the car park there; OSM's two short flights below it), three bays of
# glass under a long canopy at the top of a wide granite flight with side walls (the 1996 album photos of 생물학과,
# 생화학과 and 지질학과 on it); its walls cream, as in the aerial photo.  (point near the door, door options)
# Its flight is as wide as the photos (16 m: fourteen risers down to the court, sci_grade), with the
# five-globe lamp at its head.  음악관 (기악과's photo): a deep canopy on two round white columns over four bays of
# aluminium-framed glass, white tile walls and tiled planters either side of the granite steps, blue window frames:
# 신관's door (MUSIC_B; its ENTRY_AT below).
# 빌링슬리관: in the middle of its long south front, under a window group (the 1996 album photo of 의류환경학과:
# the arched door between equal piers, a group of three lights over it).  The 1994 campus map draws the arched door
# there, in the middle between the gabled end bays with a walk running south from it; and OSM's footway from the south
# ends there too, 22.6 m along the 45.1 m front (the door had gone to the short east end, the slope having buried this
# front: FORECOURTS).
ENTRY_AT = {222843398: ((-242.7, 13.8), dict(span=3, canopy=3.0, stair_w=16.0, lamp5=True, floor=1)),
            245623193: ((35.93, 412.08), dict(floor=0))}
# 음악관 (MUSIC_B above): 신관's porch 33 m along its south front (the skyview's canopy; 34.6 m from the 2008
# roadview's bearing), five risers (2010 roadview); 구관's door 18 m along its south front (14.5 - 20.0 m from three 2008
# panoramas' bearings; its second door, 47 m along, is left out).  The planting's zones before the doors
# (ENTRY_ZONE_AT) stay where they were drawn when the porch was 구관's, so that the trees and the decals keep their draws.
ENTRY_AT[MUSIC_A] = ((147.65, -12.67), {})
ENTRY_AT[MUSIC_B] = ((239.30, -21.09), dict(span=2, music=True, risers=5))
ENTRY_ZONE_AT = {MUSIC_A: ((144.08, -11.73), 2), MUSIC_B: ((240.66, -21.45), 1)}
# (제2인문관, GONE_1997: its door where the ground before 외솔관2's road lowering put it, so that the paving drawn
# there before the site is laid bare, and with it the decals' random draws, stay as they were)
ENTRY_AT[246156119] = ((-4.35, 348.6), {})
# (논지당: its door where the slope before its terrace (NONJI_LEVEL) put it, at the low end of its front, for the
# same reason)
ENTRY_AT[413217834] = ((112.14, 251.72), {})
# 경영학교실단 (백양관)'s front door (reference/고증.md 3.15): at the north end of the low front between the wings, where
# the annex before the north wing begins, 44.9 m along its face to 백양로 (± 3 m; the door takes the two bays nearest,
# 45.7 m).  The 2008 and 2010 roadview count thirteen risers in one straight flight, about 7 m wide over its side
# walls, 2.0 - 2.1 m up (risers of 15 - 16 cm, and the perspective's 2.0 - 2.3 m), to glass doors in under a thick
# flat canopy; the 2003 photo has the same flight.  So the front's floor stands 2.1 m over the walk at the foot of the
# flight (its sill, generic.porch: 0.12 m over the floor), over a half-sunk storey: the hall's second level.
_bk_a, _bk_b = np.array([-20.74, 45.64]), np.array([-4.6, 105.49])
BK_T = (_bk_b - _bk_a) / np.linalg.norm(_bk_b - _bk_a)
BK_N = np.array([BK_T[1], -BK_T[0]])
BK_DOOR = _bk_a + BK_T * 46.4
BK_FOOT = _bk_a + BK_T * 45.66 + BK_N * 5.1                  # (landing 1.2 m, twelve treads of 0.3 m and the last)
BK_FRONT_BASE = round(max(ground_h(*(BK_FOOT + BK_T * u)) for u in (-3.2, 0.0, 3.2)) + 2.1 - 0.12
                      - FLOOR_H['white'], 2)
ENTRY_AT[990022] = ((round(float(BK_DOOR[0]), 2), round(float(BK_DOOR[1]), 2)),
                    dict(span=2, floor=1, stair_w=5.8, risers=13, tread=0.3, landing=1.2, side='plaster_white',
                         canopy=2.4, canopy_t=0.4))
_walks = [LineString(p_['pts']) for p_ in paths_out if len(p_['pts']) > 1] + [bline]
_walk_u = unary_union(_walks)
_bp_all = [Polygon(b_['footprint']) for b_ in buildings]
ENTRY_ZONES = []


def _entry(b, poly):
    cs = list(poly.exterior.coords)[:-1]
    if not Polygon(cs).exterior.is_ccw:
        cs = cs[::-1]
    best = None
    others = [q for q in _bp_all if q is not poly and q.distance(poly) < 30]
    for i in range(len(cs)):
        (ax, ay), (bx_, by_) = cs[i], cs[(i + 1) % len(cs)]
        Le = math.hypot(bx_ - ax, by_ - ay)
        if Le < 5.5:
            continue
        tx, ty = (bx_ - ax) / Le, (by_ - ay) / Le
        nx, ny = ty, -tx                                          # outward (CCW outline)
        for s_ in np.arange(2.4, Le - 2.4 + 1e-6, 0.8):
            px_, py_ = ax + tx * s_, ay + ty * s_
            q = Point(px_ + nx * 3.0, py_ + ny * 3.0)
            if poly.contains(q) or any(o.distance(q) < 3.0 for o in others):
                continue
            rise = max(ground_h(px_ + nx * k, py_ + ny * k) for k in (1.0, 3.0)) - b['base']
            if rise > 0.7 and b['id'] not in ENTRY_AT:
                continue
            fall = b['base'] - ground_h(px_ + nx * 6.0, py_ + ny * 6.0)
            # (a walk usually runs the length of a front, so the middle of the longest front it passes wins)
            sc_ = min(_walk_u.distance(q), 12.0) + 0.25 * abs(s_ - Le / 2) - 0.04 * Le + 2.0 * max(0.0, rise) \
                + 0.4 * max(0.0, fall - 1.8)
            if b['id'] in ENTRY_AT:
                sc_ = math.hypot(px_ - ENTRY_AT[b['id']][0][0], py_ - ENTRY_AT[b['id']][0][1])
            if best is None or sc_ < best[0]:
                best = (sc_, px_, py_, nx, ny)
    return best


n_entry = 0
# 광복관's broad front flight (blender/landmarks.py kwangbok: three bays of glass 19 m along the south front)
_kb = next(b_ for b_ in buildings if b_['id'] == 468614722)['footprint']
_ka, _kb2 = np.array(_kb[1]), np.array(_kb[2])
_kt = (_kb2 - _ka) / np.linalg.norm(_kb2 - _ka)
_kn = np.array([_kt[1], -_kt[0]])
_kc = _ka + _kt * 19.0
ENTRY_ZONES.append(Polygon([tuple(_kc - _kt * 10), tuple(_kc + _kt * 10), tuple(_kc + _kt * 10 + _kn * 16), tuple(_kc - _kt * 10 + _kn * 16)]))
for b, bp in zip(buildings, _bp_all):
    if b['style'] not in ENTRY_STYLES:
        continue
    e_ = _entry(b, bp)
    if not e_:
        continue
    _, px_, py_, nx, ny = e_
    b['entry'] = dict(p=[round(px_, 2), round(py_, 2)], n=[round(nx, 4), round(ny, 4)], **ENTRY_AT.get(b['id'], (0, {}))[1])
    (zx_, zy_), zs_ = ENTRY_ZONE_AT.get(b['id'], ((px_, py_), b['entry'].get('span', 1)))
    hw_ = (3.4 if b['style'] in ('modern', 'gym') else 2.6) * zs_
    tx, ty = -ny, nx                                              # along the wall
    ENTRY_ZONES.append(Polygon([(zx_ - tx * hw_, zy_ - ty * hw_), (zx_ + tx * hw_, zy_ + ty * hw_),
                                (zx_ + tx * hw_ + nx * 8.0, zy_ + ty * hw_ + ny * 8.0),
                                (zx_ - tx * hw_ + nx * 8.0, zy_ - ty * hw_ + ny * 8.0)]))
    n_entry += 1
# 백주년기념관's paved court towards 광혜원, 과학관's broad flight (wider than the door's own zone)
_ca, _cb = np.array(CENT_NE[0]), np.array(CENT_NE[1])
_cn = np.array([(_cb - _ca)[1], -(_cb - _ca)[0]]) / np.linalg.norm(_cb - _ca)
CENT_PLAZA = Polygon([tuple(_ca + (_cb - _ca) * 0.3), tuple(_ca + (_cb - _ca) * 0.9), tuple(_ca + (_cb - _ca) * 0.9 + _cn * 16.0),
                      tuple(_ca + (_cb - _ca) * 0.3 + _cn * 16.0)])
SCI_STAIR = Polygon([tuple(SCI_DOOR - SCI_T * 10.5), tuple(SCI_DOOR + SCI_T * 10.5), tuple(SCI_DOOR + SCI_T * 10.5 + SCI_N * 18.0),
                     tuple(SCI_DOOR - SCI_T * 10.5 + SCI_N * 18.0)])
ENTRY_ZONES += [CENT_PLAZA, SCI_STAIR]


def flight_zone(p, n, hw, depth, inside=0.5):
    """the ground before a door at p (on the wall, n out of it) that a flight takes, hw either side, depth out"""
    p, n = np.array(p, float), np.array(n, float) / np.linalg.norm(n)
    t = np.array([-n[1], n[0]])
    return Polygon([tuple(p - t * hw - n * inside), tuple(p + t * hw - n * inside), tuple(p + t * hw + n * depth),
                    tuple(p - t * hw + n * depth)])


# 교육관's and 성암관's flights (blender/landmarks.py builds them, not generic.porch): the front doors, east and west,
# and 교육관's outside flight from the bay on its north end straight out to the yard (gyoyuk_north_flight).  The zone
# along that end's wall is the one the flight had when it was drawn running east along it: the paving decals below
# are drawn against these zones, and dropping it shifts every crack and stain on the campus
ENTRY_ZONES += [flight_zone((39.65, 327.89), (0.97, -0.25), 2.8, 9.0), flight_zone((117.18, 307.08), (-0.97, 0.24), 3.0, 9.0),
                flight_zone((33.7, 347.9), (0.25, 0.97), 7.0, 5.5), flight_zone((30.29, 348.78), (0.25, 0.97), 2.4, 12.5)]
_ez = unary_union(ENTRY_ZONES + [tennis_poly(pd_, 2.5) for pd_ in TENNIS['pads']])     # (and off the tennis courts)
_ez_rng = unary_union([shapely.affinity.translate(z_, *(-v_ for v_ in BLD_MOVE[324328422])) if z_ is CENT_PLAZA else z_
                       for z_ in ENTRY_ZONES] + [tennis_poly(pd_, 2.5) for pd_ in TENNIS['pads']])   # (as first cleared)
_nt = len(trees)
trees[N_ROWS:] = [t_ for t_ in trees[N_ROWS:] if not _ez_rng.contains(Point(*rxy(t_)))]
for t_ in trees[N_ROWS:]:
    if _ez.contains(Point(t_[1], t_[2])):
        drop_tree(t_)
_ns = len(shrubs)
shrubs = [s_ for s_ in shrubs if not _ez.contains(Point(s_[1], s_[2]))]
print('hall doors', n_entry, '- trees moved off them', _nt - len(trees), 'shrubs', _ns - len(shrubs))
# the clipped junipers on the banks either side of 과학관's flight (the 1996 photos: big dark rounded bushes, one or two
# trained up into cones, close against the side walls)
rng5 = random.Random(1997 + 53)
for sg in (-1, 1):
    for k, (u_, v_) in enumerate(((8.9, 1.2), (9.6, 3.4), (8.8, 5.6), (11.6, 2.0), (11.2, 4.8), (13.6, 3.0))):
        x_, y_ = SCI_DOOR + SCI_T * (sg * u_) + SCI_N * v_
        kind_ = 'topiary_cone' if k == 3 else 'topiary_round'
        shrubs.append([kind_, round(float(x_), 2), round(float(y_), 2), round(rng5.uniform(1.5, 1.9) if kind_ == 'topiary_round' else 1.4, 2),
                       round(rng5.uniform(0, 6.28), 2)])

# shrubs around building aprons (round the halls where the random planting first read them, moved with them: BLD_MOVE)
for b, bp in zip(buildings, bpolys_rng):
    if b['style'] == 'city':
        continue
    ring = bp.buffer(5.5).exterior
    nshr = int(ring.length / 7)
    _mv = BLD_MOVE.get(b['id'], (0.0, 0.0))
    for k in range(nshr):
        p = ring.interpolate(rng.uniform(0, ring.length))
        if not blocked(p.x, p.y, 1.2) and not ball_rng.contains(p) and not any(z.contains(p) for z in GARDEN_ZONES) and rng.random() < 0.55:
            p = Point(p.x + _mv[0], p.y + _mv[1])
            sh_ = ['bush', round(p.x, 2), round(p.y, 2), round(rng.uniform(0.7, 1.3), 2), round(rng.uniform(0, 6.28), 2)]
            if not _ez.contains(p):              # (drawn all the same, so the rest of the campus keeps its random draws)
                shrubs.append(sh_)

# 중앙도서관 앞 beds (1997, LIB_BEDS above).  Clear what the random planting put there (not the ginkgo row on
# 백양로's strip), then plant the beds as the 1997 photo shows them along the slant walk.  That planting is placed in
# the walk's own frame (t from the drive's kerb along the walk, w to its right, the hall's side) from where it stands
# in the photo: its bearing off the view through the README camera, at the photo's distance (from the sizes of
# shrubs, lamp and people) times 0.68, the README camera's wider lens; heights from the crown tops' rows.
_lbz = LIB_BEDS.buffer(0.3)
_lsz = LIB_WALKS.intersection(_lib_road.buffer(ROAD['strip'] + 0.3)).buffer(0.4)   # the walks' gaps in the strip
_nt, _ns = len(trees), len(shrubs)
trees = [t_ for t_ in trees if t_[0] == 'ginkgo' or not LIB_BEDS_RNG.buffer(0.3).contains(Point(*rxy(t_)))]   # (as first cleared)
for t_ in trees:
    if t_[0] != 'ginkgo' and _lbz.contains(Point(t_[1], t_[2])):
        drop_tree(t_)
shrubs = [s_ for s_ in shrubs if not (_lbz.contains(Point(s_[1], s_[2])) or _lsz.contains(Point(s_[1], s_[2])))]
_lcleared = (_nt - len(trees), _ns - len(shrubs))
_la, _lb = np.array(LIB_DIAG[0]), np.array(LIB_DIAG[1])
_lda = (_lb - _la) / np.linalg.norm(_lb - _la)                         # down the walk (south-west)
_ldr = np.array([_lda[1], -_lda[0]])                                   # its right (north-west, the hall's side)


def LD(t, w):
    return tuple(float(c) for c in _la + _lda * t + _ldr * w)


LIB_GROUPS = [Point(-46.0, -26.0), Point(-40.0, -45.0)]                # (web/src/main.js: people stand about here)
_lok = LIB_BEDS.buffer(-0.4).difference(LIB_WALKS.buffer(0.8)).difference(unary_union([g_.buffer(4.5) for g_ in LIB_GROUPS]))
_lok_rng = LIB_BEDS_RNG.buffer(-0.4).difference(LIB_WALKS_RNG.buffer(0.8)).difference(unary_union([g_.buffer(4.5) for g_ in LIB_GROUPS]))
LIB_PLANT = [
    # right of the walk: clipped juniper mounds 1.2 m high (round the near lamp), two juniper cones and a big dark one,
    # mounds and round box on to the door, a round box by the hall's north end
    ('hedge_blob', LD(8.3, 4.9), 1.5), ('hedge_blob', LD(9.8, 3.7), 1.5), ('hedge_blob', LD(11.8, 3.6), 1.45),
    ('hedge_blob', LD(10.7, 5.9), 1.4), ('hedge_blob', LD(7.0, 6.6), 1.4), ('hedge_blob', LD(13.6, 3.9), 1.3),
    ('hedge_blob', LD(16.1, 5.1), 1.3), ('hedge_blob', LD(17.6, 4.2), 1.15), ('hedge_blob', LD(26.5, 3.6), 1.1),
    ('hedge_blob', LD(36.0, 3.4), 1.15),
    ('topiary_round', LD(40.0, 3.4), 1.25), ('topiary_round', LD(44.0, 3.4), 1.15),
    ('topiary_cone', LD(18.7, 7.6), 0.85), ('topiary_cone', LD(21.7, 7.7), 0.8), ('topiary_cone', LD(31.7, 3.5), 1.3),
    ('topiary_round', LF(82.0, 13.6), 1.6),
    # left of the walk: the big mound in the photo's left corner, round boxes further on
    ('hedge_blob', LD(16.1, -3.5), 1.5), ('hedge_blob', LD(17.6, -4.6), 1.4), ('hedge_blob', LD(14.6, -4.5), 1.4),
    ('hedge_blob', LD(19.0, -3.7), 1.25), ('topiary_round', LD(25.0, -3.4), 1.3), ('topiary_round', LD(42.0, -3.3), 1.2),
]
LIB_TREES = [
    ('zelkova', LD(24.8, 5.6), 0.53),           # the round broadleaf in the middle of the photo, ~7 m
    ('zelkova_young', LD(20.3, 11.3), 0.75),    # the young one with the forked stem behind the lamp
    ('pine', LD(19.9, 14.9), 0.87),             # the big dark pine on the right, ~10 m
    ('pine', LD(35.0, -4.9), 0.55),             # the low pine at the photo's left edge
    # the rest of the beds (1997 aerial photo: trees all over them)
    ('zelkova', LF(50.0, 34.0), 0.7), ('zelkova', LF(61.0, 40.0), 0.72), ('cherry', LF(73.0, 41.0), 0.9),
    ('zelkova', LF(28.0, 22.0), 0.7), ('pine', LF(23.0, 15.5), 0.45), ('cherry', LF(31.0, 30.0), 0.85),
    ('zelkova', LF(8.0, 30.0), 0.66), ('pine', LF(14.0, 40.0), 0.42), ('pine', LF(19.0, 44.0), 0.4),
]
rng10 = random.Random(1997 + 163)
_n_lib = 0
LIB_TREE_OBJS = []
for kind_, (x_, y_), sc_ in LIB_PLANT:
    if _lok.contains(Point(x_, y_)):
        shrubs.append([kind_, round(x_, 2), round(y_, 2), sc_, round(rng10.uniform(0, 6.28), 2)])
        _n_lib += 1
for k_, (kind_, (x_, y_), sc_) in enumerate(LIB_TREES):
    if _lok_rng.contains(Point(x_, y_)):              # (as first planted: the list keeps its order)
        trees.append([kind_, round(x_, 2), round(y_, 2), sc_, round(rng10.uniform(0, 6.28), 2)])
        _n_lib += 1
        LIB_TREE_OBJS.append((trees[-1], (x_, y_), k_))
        if not _lok.contains(Point(x_, y_)):
            drop_tree(trees[-1])
# green azalea clumps under the trees in the south bed and the east of the north bed, and the beds' low box hedges
# along the walk by the arcade and the cross walk (the maps' dotted edges), broken where the slant walks run through
for (s_, o_) in ((10.0, 26.0), (11.5, 27.2), (26.0, 24.0), (27.4, 23.0), (52.0, 36.0), (53.4, 37.0), (62.5, 42.0)):
    x_, y_ = LF(s_, o_)
    if _lok.contains(Point(x_, y_)):
        shrubs.append(['bush', round(x_, 2), round(y_, 2), round(rng10.uniform(0.9, 1.2), 2), round(rng10.uniform(0, 6.28), 2)])
_ledge = LIB_APRON.union(LIB_CROSS).buffer(1.6)
_lslant = unary_union([LineString(LIB_DIAG).buffer(LIB_DIAG_W / 2 + 0.9), LineString(LIB_SDIAG).buffer(LIB_SDIAG_W / 2 + 0.9)])
for g_ in (LIB_BEDS.geoms if hasattr(LIB_BEDS, 'geoms') else [LIB_BEDS]):
    ring_ = g_.buffer(-0.6, join_style=2).exterior
    for d_ in np.arange(0.75, ring_.length, 1.5):
        p_, q_ = ring_.interpolate(d_), ring_.interpolate(min(ring_.length, d_ + 0.5))
        if _ledge.contains(p_) and not _lslant.contains(p_):
            shrubs.append(['hedge_low', round(p_.x, 2), round(p_.y, 2), 1.0, round(math.atan2(q_.y - p_.y, q_.x - p_.x), 3)])
print('library beds: cleared (trees, shrubs)', _lcleared, 'planted', _n_lib)
# the eagle's round and walk (EAGLE_PLAZA) through 백양로's strip, the side road west of it and its parked cars (SIDE_W,
# LOT_W): clear them
# (the ginkgo row on 백양로's strip stands at the beds' edge, as in the roadview: keep it)
_ecz = unary_union([EAGLE_PLAZA.buffer(0.6), Point(*EAGLE['pos']).buffer(EAGLE_BEDS_R + 0.8),
                    LineString([(x, y) for x, y, _ in LOT_W]).buffer(3.2), LineString(SIDE_W).buffer(SIDE_W_W / 2 + 1.5)])
_strip = bline.buffer(ROAD_HALF + 0.3).difference(EAGLE_PAVED.buffer(0.8))
# (as first cleared: the eagle, its walk, the side road and the stalls where they first stood, BLINE_RNG)
_ecz_rng = unary_union([EAGLE_PLAZA_RNG.buffer(0.6), Point(*EAGLE_RNG).buffer(EAGLE_BEDS_R + 0.8),
                        LineString([along_rng(s, 48.5)[:2] for s in np.arange(255, 300, 3.0)]).buffer(3.2),
                        LineString([SIDE_W[0]] + [tuple(round(c_, 1) for c_ in along_rng(s, 43.5)[:2]) for s in (240, 270, 300, 330, 352)])
                        .buffer(SIDE_W_W / 2 + 1.5)])
_strip_rng = BLINE_RNG.buffer(ROAD_HALF + 0.3).difference(EAGLE_PAVED_RNG.buffer(0.8))
_nt, _ns = len(trees), len(shrubs)
trees = [t_ for t_ in trees if not _ecz_rng.contains(Point(*rxy(t_))) or _strip_rng.contains(Point(*rxy(t_)))]
for t_ in trees:
    if _ecz.contains(Point(t_[1], t_[2])) and not _strip.contains(Point(t_[1], t_[2])):
        drop_tree(t_)
shrubs = [s_ for s_ in shrubs if not _ecz.contains(Point(s_[1], s_[2]))]
print('eagle precinct, west cars: cleared (trees, shrubs)', (_nt - len(trees), _ns - len(shrubs)))
# its four beds: clipped azaleas massed on a 1.1 m staggered grid, the outer rows a little lower (their own random
# draws, so the rest of the campus keeps its own); clear of the strip's ginkgo trunks
rng55 = random.Random(55)
_inner = EAGLE_BEDS.buffer(-0.3)
_outer = EAGLE_BEDS.buffer(-1.2)
_trunks = [Point(t_[1], t_[2]) for t_ in trees if Point(*EAGLE['pos']).distance(Point(t_[1], t_[2])) < EAGLE_BEDS_R + 1]
_n_bed = 0
for j_, v_ in enumerate(np.arange(-EAGLE_BEDS_R, EAGLE_BEDS_R + 0.01, 0.95)):
    for u_ in np.arange(-EAGLE_BEDS_R + (j_ % 2) * 0.55, EAGLE_BEDS_R + 0.01, 1.1):
        x_, y_ = eagle_xy(u_ + rng55.uniform(-0.12, 0.12), v_ + rng55.uniform(-0.12, 0.12))
        sc_, rot_ = rng55.uniform(0.98, 1.14), rng55.uniform(0, 6.28)
        p_ = Point(x_, y_)
        if not _inner.contains(p_) or any(p_.distance(q_) < 0.9 for q_ in _trunks):
            continue
        shrubs.append(['azalea_red', round(x_, 2), round(y_, 2), round(sc_ * (1.0 if _outer.contains(p_) else 0.86), 2),
                       round(rot_, 2)])
        _n_bed += 1
print('eagle beds: azaleas', _n_bed)
print('trees', len(trees), 'shrubs', len(shrubs))

# ---------------------------------------------------------------------------
# Props & landmarks
# ---------------------------------------------------------------------------


def along(s, off):
    p = bline.interpolate(s)
    p2 = bline.interpolate(min(L, s + 1))
    tx, ty = p2.x - p.x, p2.y - p.y
    n_ = math.hypot(tx, ty)
    return p.x - ty / n_ * off, p.y + tx / n_ * off, math.atan2(ty, tx)

props = []
# 백양로 street lamps: two-armed lamps with box heads along the east side (1997 aerial photo: they stand along the
# east side all the way up; along the west side, from the gate past the library, there is not one pole).  In the
# verge's lawn just inside its kerb to the sidewalk (the August 2008 roadview; in photo A both near poles come down
# inside the verge, reference/고증.md 2.3), halfway between two of the verge's shrubs (14 m + 2.6 m steps, above);
# on the sidewalk 0.45 m out before
for s in np.arange(40, L - 20, 34):
    for side in (-1,):
        s_ = s
        while True:
            s_ = 14.0 + 2.6 * (math.floor((s_ - 14.0) / 2.6) + 0.5)
            if not (in_gap(s_, side, 1.0) or in_break(s_, side, 1.0)):
                break
            s_ += 4.0
        x, y, a = along_raw(s_, side * (E_VERGE - 0.45))
        props.append(['lamp_arm', round(x, 2), round(y, 2), round(a + (math.pi if side < 0 else 0), 3)])
# (no white flags or poles along the west sidewalk.)  The white cloth past the gate, by the island's hedge about
# 92-106 m in from the gate (issue #12, back-projected with the photo's camera), is no row of flags: it is one long
# placard stretched between two trees inside the island's hedge, seen end-on through the trees so that it shows as
# three white patches.  The north end is tied to the island's young zelkova, the south end to a young tree by the
# hedge; the cloth hangs low, about 2.3 m up, its lettering towards the road.  Its ends are kept as the pixels of the
# cloth's top (north end x 790, y 929; south end 742, 989), placed along the road through PHOTO_A where they stand 2.35 m
# over the ground (issue #83; first read through the camera of before #8), the trees a little beyond either end.  Across
# the road it stays just inside the strip's hedge, as in the photo: the pixels through PHOTO_A put it 9.9 - 10.5 m west,
# at the sidewalk's outer edge (8.1 - 8.7 m through the camera of before #162; reference/고증/2.7)
_pln, _pls = (s_off(*photo_ground(790, 929, 2.35)), s_off(*photo_ground(742, 989, 2.35)))
_pl_s, _pl_o = (round(_pls[0], 1), round(_pln[0], 1)), (round(ROAD_HALF + 0.9, 1),) * 2
print('bed placard: through the photo %.1f - %.1f m west' % (_pls[1], _pln[1]))
_pt0 = along_raw(_pl_s[0] - 1.8, _pl_o[0] - 0.2)[:2]  # the south tree, just inside the hedge
trees.append(['zelkova_young', round(_pt0[0], 2), round(_pt0[1], 2), 0.9, 1.3])
print('bed placard s %.1f - %.1f, %.1f - %.1f m west' % (*_pl_s, *_pl_o))
BED_PLACARD = dict(s=_pl_s, off=_pl_o, tie=((_pl_s[0] - 1.8, _pl_o[0] - 0.2), (_pl_s[1] + 1.7, _pl_o[1] + 0.8)), top=2.35, depth=0.82,
                   text='’97 공과대학 학술제  —  공학인의 밤', sub='연세대학교 공과대학 학생회', color='white')
# banners (현수막) across the road, tied with ropes to the trees on either side (no poles of their own).  The first
# five are read off photo A (reference/고증.md 2.5): the pixels of each cloth's corners (top west, top east, bottom
# west, bottom east) and the height of its bottom edge over the road (~5 m, a lorry's height): the banner stands where
# the middle of its bottom edge is that high, and its ends where the corner rays meet the vertical plane across the
# road there (banner_from_photo, through the photo's camera above): plain cloth strips about 0.8-0.9 m deep and 9-12 m
# long (a 10:1 to 14:1 strip; the 1997 표준 현수막 is 0.9 x 10 m), hung 5-6 m over the road, unevenly (one end often
# half a metre higher).  The rest per banner: s, spec, colour, and (west end offset, east end offset, west top, east
# top, depth) in m (offsets + west / - east, tops above the road).


def banner_from_photo(tw, te, bw, be, hb):
    o_, d_ = photo_ray((bw[0] + be[0]) / 2, (bw[1] + be[1]) / 2)
    lo, hi = 10.0, 700.0
    for _ in range(50):                     # along the bottom edge's middle ray to where it stands hb over the road
        mid = (lo + hi) / 2
        x_, y_, z_ = o_ + d_ * mid
        lo, hi = (mid, hi) if z_ - prof_h(s_at(x_, y_)) > hb else (lo, mid)
    x_, y_, _ = o_ + d_ * lo
    s = s_at(x_, y_)
    cx_, cy_, a_ = along_raw(s, 0.0)
    t_ = np.array([math.cos(a_), math.sin(a_), 0.0])

    def end(p):
        o2, d2 = photo_ray(*p)
        q = o2 + d2 * float(np.dot(np.array([cx_, cy_, 0.0]) - o2, t_) / np.dot(d2, t_))
        return (q[0] - cx_) * -math.sin(a_) + (q[1] - cy_) * math.cos(a_), q[2] - prof_h(s)
    (ow, tw_), (oe, te_), (_, bw_), (_, be_) = end(tw), end(te), end(bw), end(be)
    return round(s, 1), tuple(round(float(v), 2) for v in (ow, oe, tw_, te_, (tw_ - bw_ + te_ - be_) / 2))


BANNERS = [
    # the front one: a small line over the title, a dark band of small print along the bottom (일시 · 장소 · 주최; of it
    # 「4월 30일 … 오후 2:00 ~ 6:30」 can be made out), 경 and 축 in red circles at the ends
    (banner_from_photo((730, 1257), (1397, 1276), (731, 1303), (1397, 1321), 5.0),
     dict(text='창립 7주년 기념 세미나 및 학부모 초빙 행사', sub='연세대학교 사회환경건축공학부 도시공학전공', marks=['경', '축'],
          band='일시: 4월 30일 오후 2:00 ~ 6:30   ·   주최: 연세대학교 사회환경건축공학부 도시공학전공'), 'white'),
    (banner_from_photo((880, 957), (1191, 986), (880, 987), (1191, 1016), 5.0),
     dict(text='기술고등고시 설명회', sub='분야: 기계, 전기, 화공, 환경, 토목, 건축, 전산, 통신기술'), 'white_yellow'),
    # 「아식」: the ASIC설계공동연구소 of 공과대학 (연세대학교 ASIC 설계 공동 연구소, IT SoC Magazine)
    (banner_from_photo((921, 803), (1182, 813), (922, 822), (1181, 832), 4.85),
     dict(text='아식설계공동연구소 10주년 기념식 및 초청강연회'), 'white'),
    # 사진 속 먼 쪽 두 장(글자는 읽히지 않음)은 연고전 현수막이 걸리는 가을에는 겹치므로 뺀다. 맨 끝 장은 양끝에 붉은 원(경 · 축)
    (banner_from_photo((942, 701), (1114, 701), (942, 714), (1114, 714), 5.2),
     dict(text='’97 학술제 안내  —  학과별 발표회 및 초청강연', hide='autumn'), 'white'),
    (banner_from_photo((955, 610), (1063, 610), (955, 620), (1063, 620), 5.7),
     dict(text='신입생 환영 학과 설명회  —  연세대학교 총학생회', marks=['경', '축'], hide='autumn'), 'white'),
    # 연고전 응원 현수막: 신촌 상점들이 걸어 준 푸른 현수막이 줄지어 걸리는 건 가을(연고제)뿐이다.
    # 글귀는 reference/1997_제2백양로_파란물결_연고전현수막_연세춘추.jpg 에서 읽은 것.
    (160, dict(text='연고전이 그대를 기다린다  —  주색가무를 갖춘자여!', sub='다복주전 · 연세대학교 응원단', only='autumn'), 'blue'),
    (175, dict(text='그 이름 찬란히 빛나라, 연세여!', sub='YESSS · 연세대학교 응원단', only='autumn'), 'blue'),
    (190, dict(text='독수리여! 본질을 꿰뚫는 이성으로', sub='복성각 · 연세대학교 응원단', only='autumn'), 'blue'),
    (205, dict(text='ENJOY! THIS IS BEAUTIFUL!', sub='SLAMMERS 337-8169 · 연세대학교 응원단', only='autumn'), 'blue'),
    (220, dict(text='연고전, 연세의 승리를 위한 푸른 함성', sub='연세대학교 응원단', only='autumn'), 'blue'),
    (235, dict(text='연고전이 열리는 날, 신촌이 푸르다', sub='신촌 상점가 · 연세대학교 응원단', only='autumn'), 'blue'),
    (250, dict(text='거친파도 해치고 나가자. 연세!', sub='먹쇠식당 · 연세대학교 응원단', only='autumn'), 'blue'),
    (310, dict(text='’97 대동제  ·  5월, 백양로에서 만나요',
               seasons=dict(autumn=dict(text='’97 가을 학술제  ·  학과별 발표회와 초청강연', color='white'))), 'yellow'),
    (390, dict(text='신입생 여러분 환영합니다  —  총학생회',
               seasons=dict(autumn=dict(text='2학기 중간고사  ·  중앙도서관 열람실 24시간 개방  —  총학생회'))), 'white'),
    # 연고전 is in September: in spring the 4·19 marathon (reference/1997_마라톤대회.jpg), in May the 대동제 shows,
    # in late October the victory (reference/1997_연고전_승리.jpg: 3승 1무 1패)
    (460, dict(text='’97 4·19 마라톤대회  —  4월 19일 백양로 출발',
               seasons=dict(summer=dict(text='’97 대동제 축하공연  ·  노천극장', color='yellow'),
                            autumn=dict(text='’97 정기 연고전 3승 1무 1패 압승!  고마워요 연세인'))), 'blue'),
]
# what a banner rope can be tied to: the trees beside the road only (the ginkgo rows, and where the west row has not
# started yet, the island's and the lawn's trees).  In the 1997 photo every banner hangs from the trees: the lamp
# posts carry none.
ANCHORS = [(*s_off(t_[1], t_[2]), t_[1], t_[2]) for t_ in trees if bline.distance(Point(t_[1], t_[2])) < 30]
N_FLOATING_TIES = 0


def tie_for(s, off_end, top):
    """the trunk outside the banner's end on its side of the road with the shortest rope (within 24 m along the road:
    by the gate's side road, where the west side has no trees, a rope runs to the island's or the lawn's trees)"""
    global N_FLOATING_TIES
    side = 1 if off_end > 0 else -1
    best = None
    for sa, oa, xa, ya in ANCHORS:
        if not (side * off_end + 0.3 < side * oa < 30.0) or abs(sa - s) > 24.0:
            continue
        d_ = math.hypot(sa - s, oa - off_end)
        if best is None or d_ < best[0]:
            best = (d_, xa, ya)
    if best is None:
        N_FLOATING_TIES += 1
        xa, ya, _ = along_raw(s, side * (E_WALK + ROAD['strip'] * 0.5))
        best = (0.0, xa, ya)
    return [round(best[1], 2), round(best[2], 2), round(prof_h(s) + top + 0.35, 2)]


banners = []
for row in BANNERS:
    s, spec, col = row[:3]
    ow, oe, tw, te, dep = row[3] if len(row) > 3 else (5.0, -5.0, 5.9, 5.9, 0.9)
    if isinstance(s, tuple):                # read off photo A
        s, (ow, oe, tw, te, dep) = s
    (xw, yw, _), (xe, ye, _) = along_raw(s, ow), along_raw(s, oe)
    h0 = prof_h(s)
    banners.append(dict(color=col, a=[round(xe, 2), round(ye, 2), round(h0 + te, 2)],
                        b=[round(xw, 2), round(yw, 2), round(h0 + tw, 2)], depth=dep,
                        ties=[tie_for(s, oe, te), tie_for(s, ow, tw)], **spec))
print('banner ropes tied to nothing:', N_FLOATING_TIES)
# the placard in the island bed (above): along the road, its north end first so the lettering faces 백양로
_bp = BED_PLACARD
_bn, _bs = along_raw(_bp['s'][1], _bp['off'][1])[:2], along_raw(_bp['s'][0], _bp['off'][0])[:2]
_gn, _gs = sample(Hn, NEAR_HALF, NEAR_STEP, *_bn), sample(Hn, NEAR_HALF, NEAR_STEP, *_bs)
_tn, _ts_ = along_raw(*_bp['tie'][1])[:2], along_raw(*_bp['tie'][0])[:2]
_tq = min(trees, key=lambda t_: math.hypot(t_[1] - _tn[0], t_[2] - _tn[1]))
if math.hypot(_tq[1] - _tn[0], _tq[2] - _tn[1]) < 8.0:            # (the north rope to the nearest tree beyond the end)
    _tn = (_tq[1], _tq[2])
banners.append(dict(color=_bp['color'], text=_bp['text'], sub=_bp['sub'], depth=_bp['depth'],
                    a=[round(_bn[0], 2), round(_bn[1], 2), round(_gn + _bp['top'] + 0.05, 2)],
                    b=[round(_bs[0], 2), round(_bs[1], 2), round(_gs + _bp['top'], 2)],
                    ties=[[round(_tn[0], 2), round(_tn[1], 2), round(_gn + _bp['top'] + 0.3, 2)],
                          [round(_ts_[0], 2), round(_ts_[1], 2), round(_gs + _bp['top'] + 0.25, 2)]]))

def P(name, x, y, rot=0.0):
    props.append([name, round(x, 2), round(y, 2), round(rot, 3)])

# 공중전화 부스: a bank of three along the 백양로 side of 학생회관 (동문 기억: 학생회관 앞에 있었다), fronts towards the road
_ub = next(b for b in buildings if b['name'] == '학생회관')
_f = _ub['footprint']
_a, _b = np.array(_f[2]), np.array(_f[0])           # the long west face: (18.46, -89.86) -> (34.0, -30.25)
_u = (_b - _a) / np.linalg.norm(_b - _a)
_n = np.array([-_u[1], _u[0]])
if _n[0] > 0:
    _n = -_n                                         # outwards = towards 백양로 (west)
_c = (_a + _b) / 2 + _n * 3.0
for k in (-1, 0, 1):
    _p = _c + _u * 1.2 * k
    P('payphone', float(_p[0]), float(_p[1]), math.atan2(_n[1], _n[0]))
# benches along the beds' edge by the arcade of 중앙도서관, facing the hall
for s_ in (14.0, 25.0, 56.0, 62.0):
    P('bench', *LF(s_, 11.3), math.atan2(-_lfn[1], -_lfn[0]))
# 노천극장 진입 광장 (plazas): on the grass at the east edge of its paving, the long side along it, looking in (it
# stood across the edge)
_pz = Polygon([(40, 150), (100, 140), (110, 185), (55, 195)]).buffer(2).exterior
_q = _pz.interpolate(_pz.project(Point(110, 160)))
_o = np.array([110 - _q.x, 160 - _q.y]) / _q.distance(Point(110, 160))
P('bench', _q.x + _o[0] * 0.4, _q.y + _o[1] * 0.4, math.atan2(-_o[1], -_o[0]))
# the old amphitheater: a lamp at each end of the stage, by the foot of the flight up the seat end (the 1997 photo)
for _sv in (-1, 1):
    P('lamp_double', *amph_xy(AMPH['stage_u'] - 1.0, _sv * (AMPH['stage_w'] / 2 + 0.8)), AMPH['rot'])
# 경영학교실단: against its east wall by the south-east corner, looking out over the apron towards 백양로 (it stood across
# the apron)
_bk = Polygon(next(b for b in buildings if b['name'] == '경영학교실단')['footprint']).exterior
_q = _bk.interpolate(_bk.project(Point(-20, 35)))
_o = np.array([-20 - _q.x, 35 - _q.y]) / _q.distance(Point(-20, 35))
P('bench', _q.x + _o[0] * 0.6, _q.y + _o[1] * 0.6, math.atan2(_o[1], _o[0]))
# 백양로: on the sidewalk's outer edge against the planting strip, halfway between two ginkgos, the long side along the
# road and the seat towards it, as under the cherries by the road to 핀슨관 (2003_봄_백양로끝_핀슨관길_벚나무.jpg); out
# of the walkers' lines 0.4 and 0.68 of the way across the sidewalk (web/src/main.js).  (They stood across the
# sidewalk, one of them in its middle.)
BENCH_DEPTH = 0.62                                   # (blender/props.py bench: its footprint, seat front to back posts)
for (s0, side) in ((256.0, -1), (298.0, -1), (502.0, 1)):
    s_ = min((22.0 + 8.5 * (k + 0.5) for k in range(int(L / 8.5))),
             key=lambda t: abs(t - s0) + (99.0 if in_gap(t, side, 2.0) else 0.0))
    x, y, a = along_raw(s_, side * (E_WALK - BENCH_DEPTH / 2 - 0.05))
    P('bench', x, y, a - side * math.pi / 2)
# garden benches, long side along the walk, seat towards it (BENCH_FACE: which way the bench model looks)
BENCH_FACE = math.pi


def bench_along(W, u, v, face_u):
    (x, y) = W(u, v)
    a_ = axis_angle(W) - math.pi / 2 + (0 if face_u < 0 else math.pi) + BENCH_FACE
    P('bench', x, y, a_)


for v in (27.0, 34.0, 38.5):                       # 언더우드관: along the axis walk between the half-round beds
    bench_along(UWG, -2.0, v, 1)
    bench_along(UWG, 2.0, v, -1)
# 연희관 앞 정원: along the two upper walks of the diamond at the foot of the banks, looking into the garden
for (a_, b_) in ((YH_DIAMOND[1], YH_DIAMOND[2]), (YH_DIAMOND[2], YH_DIAMOND[3])):
    a_, b_ = np.array(a_), np.array(b_)
    d_ = (b_ - a_) / np.linalg.norm(b_ - a_)
    o_ = np.array([-d_[1], d_[0]])
    for t_ in (0.3, 0.55):
        q_ = a_ + (b_ - a_) * (t_ if a_[0] < YH_C[0] else 1 - t_) + o_ * 0.95
        P('bench', float(q_[0]), float(q_[1]), math.atan2(-o_[1], -o_[0]))
# ... and on the verge of the road before 연희관, between the shrubs and pines along the top of the banks, looking at
# the road (Kakao roadview 2008-08; reference/2003_가을_연희관_정면.jpg: a plank bench on the verge)
for (p0, p1), ks in (((_FRONT_RD[0], _FRONT_RD[1]), (4, 6)), ((_FRONT_RD[1], _FRONT_RD[2]), (3, 5))):
    p0, p1 = np.array(p0), np.array(p1)
    d_ = (p1 - p0) / np.linalg.norm(p1 - p0)
    s_ = np.array([d_[1], -d_[0]])                                   # (south, off the road)
    for k in ks:
        q_ = p0 + d_ * (3.4 * k) + s_ * 4.1
        P('bench', float(q_[0]), float(q_[1]), math.atan2(-s_[1], -s_[0]))
# 대우관 상뜰: along the two lower (SW / SE) walks of the diamond, two benches on the lawn triangle inside facing the
# walk and two on the far side facing back (the photos; a bench model faces its rot angle, see bench_along)
for sg in (-1, 1):
    _w0, _w1 = np.array(SANG_NODES['E' if sg > 0 else 'W']), np.array(SANG_NODES['S'])
    _d = (_w1 - _w0) / np.linalg.norm(_w1 - _w0)
    _in = np.array([-_d[1], _d[0]]) * (1 if sg < 0 else -1)          # into the triangle (towards the ring)
    for t_, side in ((0.5, 1), (0.78, 1), (0.25, -1), (0.65, -1)):
        e_, n_ = _w0 + (_w1 - _w0) * t_ + _in * 2.3 * side
        x_, y_ = SG(e_, n_)
        f_ = -_in * side                                                 # facing the walk
        fw_ = SG_E * f_[0] + SG_N * f_[1]
        P('bench', x_, y_, math.atan2(fw_[1], fw_[0]))
# the campus bin is the grey-and-green recycling box of the 2003 photo (props.recycle_bin), its doors to the walk
for (x, y), r_ in [((-48, -40), 0.0), ((-4, -64), math.pi), (uwg_xy(-2.4, 41.0), math.atan2(_wuu[1], _wuu[0])),
                   ((-94, -404), math.pi), ((-44, -175), math.pi)]:
    P('recycle_bin', x, y, r_)
# double-globe lamps at the north-west corner of 연희관 앞 정원 and by 교육관's north yard (the 2003 photos)
for (name_, x, y, r) in PHOTO03_PROPS:
    P(name_, x, y, r)
# 언더우드관 앞길 (2003_봄_언더우드관_앞길_벚나무.jpg, looking east from before the west wing): a row of yellow-and-black
# bollards across the road before the west wing and another at its east end, where it meets the slope towards
# 논지당 (no cars in front of the hall); before the west wing a green canvas tent (a stall) and, at the road's edge
# by the west side of the tower's flight, a notice board under a little green roof (the people walking past it
# stand ~17 m off in the photo, by their height: so the flight behind it is the tower's, not a side door's; in the
# Dec. 2010 roadview, panoramas 1016786672 - 673, no board is left)
_south = math.atan2(-_wuv[1], -_wuv[0])
for (u_, vs_) in ((-22.0, np.arange(29.9, 37.0, 1.4)), (15.2, np.arange(30.8, 36.4, 1.35))):
    for v_ in vs_:
        P('bollard', *WU(u_, float(v_)), 0.0)
P('tent_kiosk', *WU(-28.0, 40.4), _south)
P('notice_board', *WU(-14.8, 37.2), _south)
# 연희관 (2003_가을_연희관_정면.jpg, from the south-west; Kakao roadview 2008-08 from the west end of the road): the
# green tent stall west of the entrance flight, at its foot by the road, its counter to the road
_yd = min(np.arange(-10.0, 60.0, 0.25), key=lambda u_: abs(float((np.array(WY(u_, 0.0)) - GF_C) @ GF_E)))   # the axis
_ye = 1.0 if WY(_yd + 1.0, 0.0)[0] > WY(_yd, 0.0)[0] else -1.0
_yo = math.atan2(*(np.array(WY(_yd, -1.0)) - np.array(WY(_yd, 0.0)))[::-1])                              # out of the front
P('tent_kiosk', *WY(_yd - _ye * 5.4, -8.0), _yo)
# 백양로 끝 계단 (UW_STEPS), the top of the banks either side of the head (the 2003 spring photos: from the 삼거리, the
# backs of the benches and the bin's grey back in a row east of the head and a stone 해태 at its west corner; from the
# square looking west-south-west, the same row's seats and the bin's green doors, the pair of 해태 at the head's
# corners with their heads towards the steps): benches facing the square, east of the head bench - bench - bin -
# bench - bench and west of it three benches; the 해태 on their plinths either side of the head, looking down the steps
_st_south, _st_north = math.atan2(-_stv[1], -_stv[0]), math.atan2(_stv[1], _stv[0])
for u_ in UW_HEAD_BENCHES:
    P('bench', *st_xy(u_, UW_STEPS['v_head'] + 0.4), _st_north)
P('recycle_bin', *st_xy(UW_HEAD_BIN, UW_STEPS['v_head'] + 0.4), _st_north)
for u_ in UW_HAETAE:
    P('haetae', *st_xy(u_, UW_STEPS['v_head'] + 0.4), _st_south)
for (x, y) in [(52.6, 340.5), (46.0, 358.0)]:
    P('lamp_double', x, y, -0.25)
# a double-globe lamp at the tip of the 화단섬; before 중앙도서관 the four-globe lamps of the 1997 photo, in the clipped
# shrubs on the hall's side of the slant walk (a near one, a far one where it meets the walk along the arcade), and
# along the edge of the beds by the arcade
P('lamp_double', *photo_ground(632, 1092), -0.25)               # (its foot in photo A, by the island's south-east kerb)
for (x, y) in [LD(10.6, 4.4), LD(48.2, 3.5), LF(18.0, 13.8), LF(33.0, 13.8), LF(66.0, 13.8)]:
    P('lamp_quad', x, y, -0.25)
# 화단섬: natural stone marker, campus guide sign, white round planters along the side road (their feet in photo A)
P('stone_marker', *photo_ground(470, 1058), 0.4)
P('sign_board', *photo_ground(222, 1073), -0.9)
for (px_, py_) in ((95, 1140), (233, 1147), (360, 1157), (245, 1247)):
    P('planter', *photo_ground(px_, py_), 0)
# the side road's parking booth (photo A's left edge: what looked like the front of a blue bus is a booth with a
# rounded glazed front, blue frames and a white cap, a raised red-and-white barrier arm and yellow barrier boxes at its
# east end; the 2010 roadview has the side road's toll booth and barriers on an island between the lanes in the same
# way, a little further north-east).  The booth's island stands just south of the centre line (the line runs on
# behind the booth), its nose at the yellow barrier box, facing 백양로 (blender/props.py parking_booth).
_bn = np.array([-_cd[1], _cd[0]])                                   # left of the road towards 백양로 (north-east)
_box = np.array(photo_ground(85, 1155))                             # the barrier box's foot
_bo = _box - _cd * 1.6 - _bn * 1.0
P('parking_booth', round(float(_bo[0]), 2), round(float(_bo[1]), 2), round(math.atan2(_cd[1], _cd[0]), 3))

# parked & moving cars (1990s 승용차), engineering-side motorbikes
cars = []
# (LOT_W, west of the eagle along the side road SIDE_W: with the roads above)
# These three straight rows were placeholders from before the roads and lawns were drawn.  The first left no car
# (most of it falls in halls), and the other two stood on lawn slopes north of 광복관 and of 백주년기념관, tilted
# 0.3 - 0.6 m into the grass.  No 1997 source puts cars there, so they are still drawn (one stream of draws, see
# above) but not parked.
lots = [((60, 100), (100, 92), 9), ((-130, 110), (-80, 130), 8), ((20, -150), (40, -180), 6)]
for (a, b_, n) in lots:
    for k in range(n):
        t_ = k / max(1, n - 1)
        x = a[0] + (b_[0] - a[0]) * t_
        y = a[1] + (b_[1] - a[1]) * t_
        ang = math.atan2(b_[1] - a[1], b_[0] - a[0]) + math.pi / 2
        if rng.random() < 0.85 and not ball.buffer(1.5).contains(Point(x, y)):
            _ = (rng.choice(['sedan', 'sedan', 'hatch', 'taxi']), rng.uniform(-.05, .05), rng.randrange(8))   # (a car's draws)
for line in (LOT_W, LOT_E):
    for (x, y, a) in line:
        if rng.random() < 0.8 and not ball.buffer(1.5).contains(Point(x, y)):
            car = [rng.choice(['sedan', 'sedan', 'hatch', 'taxi']), round(x, 2), round(y, 2),
                   round(a + math.pi / 2 + rng.uniform(-.05, .05), 3), rng.randrange(8)]
            if line is not LOT_E:
                cars.append(car)
rng3 = random.Random(1997 + 11)
# (the seven stalls: the cars, 4.7 m long, stood nose to tail every 4.6 m, each one into the next.  Photo A has the
# red car side-on at the front edge of a pale paved car park (LOT_C_PAD below), more cars on it behind: the front row
# from the red car along the photo's row, a car's length and a gap apart, the stalls left over in a row behind.  The
# same seven draws, so the cars after these keep their places in the list, and with them their colours)
_lcn = np.array([-_lcd[1], _lcd[0]])                               # (into the car park, away from the camera)
_lc_span = float(np.linalg.norm(_lc1 - _lc0))
_lc_nf = max(2, min(len(LOT_C), int(_lc_span / 5.6) + 1))
_lc_sp = _lc_span / (_lc_nf - 1) if _lc_nf > 1 else 5.6
LOT_C_CARS = [(*(_lc0 + _lcd * (_lc_sp * k)), a_) if k < _lc_nf else (*(_lc0 + _lcd * (2.8 + 5.6 * (k - _lc_nf)) + _lcn * 8.0), a_)
              for k, (_, _, a_) in enumerate(LOT_C)]
# (2026-11-11, reference/고증/2.3 「주차」) re-read through PHOTO_A: the red car's wheels at x 1630 and 1677 px put it
# 0.3 m on along the row from the pixel it was placed by; behind it the cars that show between the trees, each
# placed by the foot of what shows of it (the near side of one side-on, the nose of one facing the camera, half a
# car's length or width short of its middle): a maroon one side-on 2.3 m along the row and 13.3 m back, a silver one
# facing the camera 6.9 m along and 11.3 m back, a red one side-on 14.8 m along and 9.1 m back (and a blue van facing
# the camera behind that one, 13.7 m back: LOT_C_VAN, at the list's end).  Before, the three behind were guessed 8 m
# back, side-on and 5.6 m apart
LOT_C_BACK = [(2.3, 13.25, 0.0), (6.9, 11.3, -math.pi / 2), (14.8, 9.05, 0.0)]
LOT_C_VAN = (14.7, 13.7, -math.pi / 2)
_lca = math.atan2(_lcd[1], _lcd[0])
LOT_C_CARS[0] = (*(_lc0 + _lcd * 0.3), LOT_C_CARS[0][2])
for k_, (u_, v_, h_) in zip(range(_lc_nf, len(LOT_C_CARS)), LOT_C_BACK):
    LOT_C_CARS[k_] = (*(_lc0 + _lcd * u_ + _lcn * v_), _lca + h_ if h_ == 0.0 else math.atan2(-_lcn[1], -_lcn[0]))
print('정문 동쪽 잔디 주차: photo row %.1f m, front %d cars %.1f m apart, %d behind' % (_lc_span, _lc_nf, _lc_sp, len(LOT_C) - _lc_nf))
for k_, (x, y, a) in enumerate(LOT_C_CARS):     # the first is the photo's red car (web/src/main.js PARKED_COLORS[6])
    if k_ == 0 or rng3.random() < 0.85:
        kind_ = rng3.choice(['sedan', 'sedan', 'hatch', 'taxi']) if k_ else 'hatch'
        cars.append([kind_, round(x, 2), round(y, 2), round(a + rng3.uniform(-.06, .06), 3),
                     rng3.randrange(8) if k_ else 'red'])          # (its colour index once the list is final, below)
# 대우관 뒤 (DAEWOO_BACK): the cars in the yard's stalls, nose in
rng5 = random.Random(1997 + 29)
(_x0, _y0), (_x1, _y1) = WD(0, 0), WD(1, 0)
_hu = math.atan2(_y1 - _y0, _x1 - _x0)                            # heading along +u
# (53 of them, as the five rows the game had there held: the web picks each car's model and colour by its place in
# the list.  The yard's stalls but four left free for the cars that drive in (TRAFFIC), the rest along the kerb)
DWB_FREE = {('col', 1), ('col', 3), ('east', 4), ('east', 9)}
_dw_spots = [(q_, h_) for n_, i_, q_, h_, _ in dwb_stalls() if (n_, i_) not in DWB_FREE] + DWB_KERB
assert len(_dw_spots) >= 53, len(_dw_spots)
for (x_, y_), h_ in _dw_spots[:53]:
    cars.append([rng5.choice(['sedan', 'sedan', 'sedan', 'hatch']), round(x_, 2), round(y_, 2), round(h_ + rng5.uniform(-.04, .04), 3),
                 rng5.randrange(8)])
# 교육관's north yard, full of cars in the 2003 autumn photo (2003_가을_연희관앞정원과_교육관_북쪽계단.jpg): a row nose in
# towards the hall, east of the outside flight that comes down from the bay near its west corner
_gt, _gn = np.array([-0.969, 0.248]), np.array([0.248, 0.969])     # along its north end (from the east corner), out of it
rng9 = random.Random(1997 + 2004)
for s_ in (1.8, 4.4, 7.0, 9.6):
    if rng9.random() < 0.9:
        q_ = np.array([44.15, 345.23]) + _gt * s_ + _gn * 8.2
        cars.append([rng9.choice(['sedan', 'sedan', 'sedan', 'hatch']), round(float(q_[0]), 2), round(float(q_[1]), 2),
                     round(math.atan2(-_gn[1], -_gn[0]) + rng9.uniform(-.04, .04), 3), rng9.randrange(8)])
# motorbikes in front of the south end of 제1공학관 (the 1997 photo: by its south-east corner, next to the island): from
# 5 m before its south face (LATE_FOOTPRINT_1997) south-south-east to 19 m, as photo A shows them through PHOTO_A with
# the ground there the 2.3 m lower that the corner's foot wants (reference/고증.md 3.8)
for k in range(16):
    t_ = k / 15
    x, y = -127.8 + 9.0 * t_ + rng.uniform(-.3, .3), -285.0 - 14.0 * t_
    P('motorbike', x, y, -1.385 + rng.uniform(-.2, .2))

# keep the carriageway clear: nothing static may stand on 백양로's driving lanes
def on_carriageway(x, y):
    return bline.distance(Point(x, y)) < E_CURB + 0.3 and bline.project(Point(x, y)) < L - 1
n0 = (len(props), len(cars), len(trees), len(shrubs))
# (bline runs on past the drawn end, over the steps: what stands along their head stays, as below)
_uw_kept = lambda p: p[0] in ('bench', 'recycle_bin', 'haetae') and UW_HEAD_ROW.contains(Point(p[1], p[2]))
props = [p for p in props if not on_carriageway(p[1], p[2]) or _uw_kept(p)]
# (nor on the halls' front steps: benches, bins and phone boxes stood beside the doors, not in them)
props = [p for p in props if p[0] in ('lamp_arm', 'guard_booth') or not _ez.contains(Point(p[1], p[2]))]
cars = [c for c in cars if not on_carriageway(c[1], c[2]) and not _ez.contains(Point(c[1], c[2]))]
trees = [t for t in trees if not (BLINE_RNG.distance(Point(*rxy(t))) < E_CURB + 0.3 and BLINE_RNG.project(Point(*rxy(t))) < L_RNG - 1)]
for t in trees:                                     # (as first cleared, on the line as first laid; the moved one's at the end)
    if on_carriageway(t[1], t[2]):
        drop_tree(t)
shrubs = [t for t in shrubs if not on_carriageway(t[1], t[2])]
print('removed from carriageway (props, cars, trees, shrubs):',
      n0[0] - len(props), n0[1] - len(cars), n0[2] - len(trees), n0[3] - len(shrubs))
# ... nor in the 1997 photo's view over the old amphitheater
trees = [t for t in trees if not _in_photo_view(*rxy(t))]
shrubs = [t for t in shrubs if not _in_photo_view(t[1], t[2], 1.0)]
# ... nor on 백양로's end steps (UW_STEPS) and their banks, nor on the old extension of the road past them (planted
# above along the full line, to keep the random draws) or the paved head of the steps (only the trees of the photos
# stay there); then the planting of the banks (the 2003 spring photo, the 2010 - 2026 roadview): rows of clipped round
# shrubs down both banks and a border of pansies along their top under the cherries
_uwz = Polygon([st_xy(-5.8, -0.5), st_xy(5.8, -0.5), st_xy(5.8, UW_STEPS['v_head'] + 0.3), st_xy(-5.8, UW_STEPS['v_head'] + 0.3)])
_ext_z = _ext.buffer(ROAD_HALF + 1.0, cap_style='flat')
_keep_sp = ('poplar', 'magnolia', 'fir')
_gone = lambda x_, y_: _uwz.contains(Point(x_, y_)) or _ext_z.contains(Point(x_, y_))
props = [p for p in props if not _gone(p[1], p[2]) or _uw_kept(p)]
cars = [c for c in cars if not _gone(c[1], c[2]) and not UW_BANK.contains(Point(c[1], c[2]))]
_photo_xy = {(round(float(x_), 2), round(float(y_), 2)) for _, x_, y_, _ in PHOTO03}
trees = [t for t in trees if (t[1], t[2]) in _photo_xy or t[0] in _keep_sp
         or not (_gone(*rxy(t)) or UW_HEAD.contains(Point(*rxy(t))))]
for t in trees:
    if not ((t[1], t[2]) in _photo_xy or t[0] in _keep_sp) and (_gone(t[1], t[2]) or UW_HEAD.contains(Point(t[1], t[2]))):
        drop_tree(t)
shrubs = [t for t in shrubs if not (_gone(t[1], t[2]) or UW_BANK.contains(Point(t[1], t[2])) or UW_HEAD.contains(Point(t[1], t[2])))]
rng10 = random.Random(1997 + 2005)
_along = math.atan2(_stu[1], _stu[0])
for sg in (-1, 1):
    for k, v_ in enumerate((2.2, 5.6, 9.0, 12.4, 15.4)):
        for u_ in np.arange(7.2 + (k % 2) * 1.8, 21.0, 3.6):
            x_, y_ = st_xy(sg * u_, v_)
            shrubs.append(['topiary_round', round(x_, 2), round(y_, 2), round(rng10.uniform(0.95, 1.2), 2), 0])
    for u_ in np.arange(6.4, 22.0, 1.6):
        x_, y_ = st_xy(sg * u_, UW_STEPS['v_head'] - 0.7)
        shrubs.append(['pansy_bed', round(x_, 2), round(y_, 2), 1.0, round(_along, 3)])

# ---------------------------------------------------------------------------
# Fallen leaves (issue #18): where October's ginkgo leaves and April's cherry petals lie.  An RGB mask over the
# splat's rectangle at 1 m like ground_dry.png: R ginkgo, G cherry (the young cherries blossom too: their leaf
# material is the cherry's), B the other broadleaves in October (zelkova, oak, maple, cherry).  Thick under the crown,
# thinning past its edge and dragged LEAF_DRIFT m east by the (assumed) west wind; on a carriageway thin in the middle,
# where the cars sweep it, and full in the gutters.  web/src/terrain.js lays the month's carpet from it, and
# web/src/litter.js the same on 백양로's own road mesh (its asphalt and pavers).
CROWN_RX = {'ginkgo': 2.05, 'zelkova': 6.0, 'cherry': 4.3, 'maple': 3.2, 'oak': 5.0,
            'zelkova_young': 2.9, 'cherry_young': 2.2, 'magnolia': 3.4, 'poplar': 4.4}   # crown radii, blender/vegetation.py SPECIES rx
LEAF_CH = {'ginkgo': (0,), 'cherry': (1, 2), 'cherry_young': (1, 2), 'zelkova': (2,), 'zelkova_young': (2,),
           'oak': (2,), 'maple': (2,), 'magnolia': (2,), 'poplar': (2,)}
LEAF_DRIFT = 2.5
LEAF_SPREAD = 3.2                     # m past the crown's edge the carpet thins out
LEAF_STREW = 5.0                      # ... and a few strewn leaves this much farther (out onto the road)
LW, LH = int((SPLAT['x1'] - SPLAT['x0']) / DRY_RES), int((SPLAT['y1'] - SPLAT['y0']) / DRY_RES)


def _ss(a, b, x):
    t_ = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t_ * t_ * (3 - 2 * t_)


_lv = np.zeros((LH, LW, 3), np.float32)
for _sp, _tx, _ty, _sc, *_ in trees:
    if _sp not in LEAF_CH:
        continue
    _R = CROWN_RX[_sp] * _sc
    _pad = _R + LEAF_DRIFT + LEAF_SPREAD + LEAF_STREW + 0.5
    _c0, _c1 = max(0, int((_tx - _pad - SPLAT['x0']) / DRY_RES)), min(LW, int((_tx + _pad - SPLAT['x0']) / DRY_RES) + 1)
    _r0, _r1 = max(0, int((SPLAT['y1'] - _ty - _pad) / DRY_RES)), min(LH, int((SPLAT['y1'] - _ty + _pad) / DRY_RES) + 1)
    if _c0 >= _c1 or _r0 >= _r1:
        continue
    _dx = (SPLAT['x0'] + (np.arange(_c0, _c1) + 0.5) * DRY_RES - _tx)[None, :]
    _dy = (SPLAT['y1'] - (np.arange(_r0, _r1) + 0.5) * DRY_RES - _ty)[:, None]
    _t = np.clip(_dx / LEAF_DRIFT, 0.0, 1.0)                  # along the drift, trunk -> downwind
    _d = np.hypot(_dx - _t * LEAF_DRIFT, _dy)
    _v = np.maximum(1 - _ss(0.6 * _R, _R + LEAF_SPREAD, _d), 0.4 * (1 - _ss(_R, _R + LEAF_SPREAD + LEAF_STREW, _d)))
    _v *= 1 - 0.35 * _t
    for _ch in LEAF_CH[_sp]:
        _blk = _lv[_r0:_r1, _c0:_c1, _ch]
        _lv[_r0:_r1, _c0:_c1, _ch] = 1 - (1 - _blk) * (1 - _v)   # overlapping crowns pile up
# the cars sweep the middle of a carriageway: the splat's asphalt (side roads, aprons) by the distance to its edge ...
_ad = ndimage.distance_transform_edt(spl[..., 0] > 127) * SPLAT['res']
_ad = _ad.reshape(LH, int(DRY_RES / SPLAT['res']), LW, int(DRY_RES / SPLAT['res'])).mean((1, 3))
_sweep = 1 - 0.7 * _ss(1.0, 2.6, _ad)
# ... and 백양로's own carriageway (drawn as pavers in the splat, under the road mesh) by the distance to its centre line
_gx, _gy = np.meshgrid(SPLAT['x0'] + (np.arange(LW) + 0.5) * DRY_RES, SPLAT['y1'] - (np.arange(LH) + 0.5) * DRY_RES)
_bb = bline.buffer(E_CURB + 1).bounds
_in = (_gx > _bb[0]) & (_gx < _bb[2]) & (_gy > _bb[1]) & (_gy < _bb[3])
_bd = np.full(_gx.shape, 1e9, np.float32)
_bd[_in] = shp_distance(bline, shp_points(_gx[_in], _gy[_in]))
_sweep *= np.where(_bd < E_CURB, 0.25 + 0.75 * _ss(E_CURB - 1.8, E_CURB - 0.4, _bd), 1.0)
_lv = ndimage.gaussian_filter(_lv, (0.8, 0.8, 0)) * _sweep[..., None]
Image.fromarray(np.clip(_lv * 255, 0, 255).astype(np.uint8), 'RGB').save(
    os.path.join(ROOT, 'web/public/assets/textures/ground_leaves.png'), optimize=True)
print('leaf mask: ginkgo %.0f, cherry %.0f, broadleaf %.0f m2' % tuple((_lv > 0.3).sum((0, 1)) * DRY_RES ** 2))

LANDMARKS = [
    dict(id='gate', name='정문', pos=[round(GATE_C[0] + 2.0, 1), round(GATE_C[1] + 2.0, 1)], r=22, photo=None,     # (just inside it)
         title='연세대학교 정문', year='1997',
         text='신촌 로터리에서 걸어 올라오면 만나는 정문. 1997년의 정문 앞에는 학교 버스와 오토바이, 그리고 오늘도 늦은 학생들이 뒤섞였다. 여기서 백양로가 북쪽 본관까지 곧게 뻗어 있다.'),
    dict(id='baekyangro', name='백양로', pos=[-82, -300], r=26, photo=['photos/baekyangro_1997_pano.jpg', 'photos/yongo_banner_news_1997.jpg'],
         title='그때의 백양로', year='1997',
         text='1997년의 백양로는 차와 사람이 함께 오가던 아스팔트 길이었다. 2차선 차도 양옆의 둥근 회양목, 넓은 보도와 은행나무 가로수, 그리고 길을 가로지른 현수막들. 연고제가 있는 가을이면 신촌 상점들이 건 푸른 응원 현수막이 줄지어 걸려 「제2백양로의 파란물결」이라 불렸다. 2015년 백양로 재창조 사업으로 차도는 지하로 들어가고 지금은 보행자 전용 숲길이 되었다.'),
    dict(id='engineering', name='제1공학관', pos=[-104, -262], r=20, photo=None,
         title='공과대학 (제1공학관)', year='1997',
         text='정문을 들어서면 왼편으로 길게 늘어선 공학관. 1997년 사진 속 공학관 앞에는 오토바이들이 줄지어 서 있다.'),
    dict(id='centennial', name='백주년기념관', pos=[-30, -215], r=26, photo=['photos/centennial_1997.jpg'],
         title='백주년기념관', year='1997',
         text='원통형 매스가 인상적인 백주년기념관. 공연과 강연, 졸업 행사가 열리던 곳으로, 1997년 백양로 오른편 풍경의 중심이었다.'),
    # the museum's own door in the hall's 백양로 porch (blender/landmarks.py museum_porch), at the foot of its flight
    dict(id='museum', name='연세대학교 박물관', pos=[round(CENT_MUSEUM['door'][0] + CENT_MUSEUM['n'][0] * 9.5, 1),
                                                  round(CENT_MUSEUM['door'][1] + CENT_MUSEUM['n'][1] * 9.5, 1)], r=12, photo=['photos/museum_1996.jpg', 'photos/museum_1996_side.jpg'],
         title='백주년기념관 박물관 입구', year='1996',
         credit='사진: 1997년 졸업 앨범의 학과 단체사진(1996년 5 ~ 6월, 2022 재상봉 25주년 기념문집 「25년 전 우리는」), 사람이 없는 윗부분',
         text='백주년기념관의 백양로 쪽 현관 북쪽, 흰 벽과 흰 원통 사이로 비스듬히 기운 유리벽과 흰 관 기둥이 서 있고 「YONSEI UNIVERSITY MUSEUM」 긴 현수막이 걸려 있었다. 짙은 차양 아래 유리문으로 들어가면 박물관. 1996년 봄엔 「세계한민족 화학학술대회」와 박물관 강좌 「민요의 현장을 찾아서」 현수막이 걸렸고, 공대 여러 학과가 이 계단에서 졸업 사진을 찍었다.'),
    dict(id='eagle', name='독수리상', pos=EAGLE['pos'], r=16, photo=['photos/eagle_2024.jpg'],
         title='독수리상', year='1997',
         text='연세의 상징 독수리. 높은 기둥 위에서 날개를 편 독수리가 정문 쪽으로 백양로를 내려다본다. 2015년 백양로를 다시 만들 때 북쪽 중앙도서관 앞으로 옮겨져 지금도 서 있다.'),
    dict(id='hwalcheon', name='활천대', pos=FOUNTAIN['pos'], r=12, photo=['photos/hwalcheon_old.jpg'],
         title='활천대 (活泉臺)', year='1974',
         credit='사진: 연세대학교 공식 블로그 「연세대학교의 조형물을 찾아서!! 제3탄」(2017)의 「예전의 활천대」(blog.naver.com/luckycmw)',
         text='독수리상 옆의 분수대. 전기공학과 동창회가 모금해 1974년 앞뜰에 만들었고, 연세의 영향력이 사회 전 분야에 퍼지길 바라는 마음을 담았다고 한다. 둥근 막돌 담 안에 물이 찰랑이고, 가운데 돌섬 위에 선 十자 기둥 꼭대기에서 물기둥이 솟았다. 공대 축제 「활천제」의 이름도 여기서 왔다. 백양로 재창조 뒤에는 제1공학관 앞으로 자리를 옮겼다.'),
    dict(id='library', name='중앙도서관', pos=[-58, -40], r=22, photo=['photos/library_1997.jpg', 'photos/library_reading_1997.jpg', 'photos/baekyangro_library_1995.jpg'],
         title='1997년 중앙도서관', year='1997',
         text='1979년 준공된 중앙도서관. 아치형 기둥이 늘어선 정면은 그 시절 연세인 모두의 배경이었다. 시험 기간이면 열람실 자리를 맡으려 새벽부터 줄을 섰다.'),
    dict(id='union', name='학생회관', pos=[0, -62], r=22, photo=['photos/union_1997.jpg', 'photos/marathon_news_1997.jpg'],
         title='1997년 학생회관', year='1997',
         credit='사진: 연세춘추 제1316호(1997.5.5) 「4·19 정신잇기」 김민정 기자 · 연세대학교 기록관',
         text='격자무늬 콘크리트 외벽의 학생회관. 동아리방과 식당, 총학생회가 있던 캠퍼스의 사랑방이었다. 벽면에는 늘 대자보와 현수막이 걸려 있었다. 1997년 4월 18일에는 이 앞에서 4·19 정신 계승 마라톤이 열렸다. 200여 명의 학생이 10km를 달리며 선전전을 벌였다.'),
    dict(id='chapel', name='루스채플', pos=[50, -70], r=18, photo=None,
         title='루스채플', year='1997',
         text='1974년 미국 헨리 루스 재단의 기부금과 학교 보조금으로 지어진 채플. 채플 수업 시간이면 학생들이 이 앞에 모여들었다.'),
    dict(id='auditorium', name='대강당', pos=[38, 30], r=22, photo=['photos/auditorium_2009.jpg', 'photos/auditorium_2009_side.jpg'],
         title='대강당', year='1958',
         text='1958년 12월 준공된 2,300여 석의 대강당. 평일마다 채플이 열렸고, 입학식과 졸업식, 각종 집회와 공연이 열린 큰 무대였다. 화강석 판의 큰 박공 아래 짝지은 긴 창 다섯 칸, 놋쇠 틀 유리문 세 칸, 그 앞 열 단 계단 위의 넓은 현관.',
         credit='사진: younghwan12.tistory.com (2009.4.12 촬영)'),
    dict(id='amphitheater', name='노천극장', pos=[150, 150], r=30, photo=['photos/amphitheater_1997.jpg', 'photos/amphitheater_1999.jpg'],
         title='구 노천극장의 마지막 모습', year='1997.04',
         text='잔디 계단이 언덕을 따라 둥글게 둘러선 옛 노천극장. 1997년 4월 사진은 철거 전 마지막 모습이다. 아카라카와 응원제의 함성이 울리던 이 자리에는 1999년 5월 지금의 새 노천극장이 들어섰다.'),
    dict(id='underwood', name='언더우드관', pos=[58, 215], r=30, photo=['photos/underwood_2023.jpg', 'photos/underwood_2024.jpg', 'photos/underwood_garden_2024.jpg'],
         title='언더우드관 · 스팀슨관 · 아펜젤러관', year='1920s',
         text='백양로 끝, 담쟁이로 덮인 석조 건물들. 언더우드관 앞 정원을 사이에 두고 스팀슨관과 아펜젤러관이 마주 선다. 연세의 역사가 시작된 곳.'),
    dict(id='events', name='게시판 · 그때 우리는', pos=[9, -36], r=9, photo=['photos/marathon_1997.jpg', 'photos/daedongje_1997.jpg', 'photos/yongo_1997.jpg', 'photos/cheer_1997.jpg', 'photos/yongo_banner_1997.jpg'],
         title='신촌 캠퍼스 1997 · 그때 우리는', year='1997',
         text='4월 마라톤대회, 5월 빗속의 대동제, 9월 정기 연고전 출정식과 응원제. 백양로는 늘 푸른 물결로 가득했다.'),
    dict(id='yongjae', name='용재관', pos=[64.2, 127.7], r=18, photo=['photos/yongjae_1990s.jpg'],
         title='용재관', year='1957 – 2013',
         credit='사진: 동문 제공 (reference/용재관.jpg)',
         text='연세대 초대 총장 용재(庸齋) 백낙준의 호를 딴 흰 건물. 1957년 도서관으로 지어졌고, 언더우드 동상 너머로 보이던 세로로 긴 계단탑이 상징이었다. 2013년 헐리고 그 자리에 경영관(2015)이 섰다. 경영관 한쪽의 「용재관 타워」가 옛 모습을 잇는다.'),
    dict(id='daewoo', name='대우관', pos=[113.5, 453.8], r=26,
         photo=['photos/daewoo_2017.jpg', 'photos/daewoo_2024.jpg', 'photos/daewoo_annex_2017.jpg'],
         title='대우관과 상뜰', year='1996',
         credit='사진: 연세대 상경대학 홈페이지 (blog.naver.com/maxx5335/221067910905 재인용) · 다음 카페 「훌리건 천국」 이호성 (2024)',
         text='1996년 6월 문을 연 상경대학 · 경영대학의 새 집. 대우그룹 김우중 회장과 상경대 동문들의 기부로 지어져 대우관(김우중 기념관)이라 불렸다. 흰 석조의 고딕풍 건물로, 앞뜰의 소나무 정원 「상뜰」은 공강 시간마다 붐볐다. 정문에서 900m, 캠퍼스에서 가장 높고 깊숙한 곳.'),
    dict(id='yeonhui', name='연희관', pos=[88.0, 343.0], r=20, photo=['photos/yeonhui_2024a.jpg', 'photos/yeonhui_2024b.jpg'],
         title='연희관 가는 길', year='1956',
         credit='사진: 다음 카페 「훌리건 천국」 이호성 (2024)',
         text='1956년 과학관으로 지어져 1984년부터 연희관으로 불린 석조 건물. 담쟁이 덮인 벽과 회양목 정원 사이로, 대우관까지 이어지는 오르막길이 시작된다.'),
]
STATUES = dict(
    eagle=dict(pos=EAGLE['pos'], rot=EAGLE_ROT,                  # looks down 백양로 to the gate (2011 roadview side view)
               r=round(EAGLE_DAIS[0] + 0.05, 2), dais=list(EAGLE_DAIS), ring=list(EAGLE_RING), beds=EAGLE_BEDS_R, walk=EAGLE_WALK_W,
               walk_edge=EAGLE_EDGE, groups=[list(g_) for g_ in EAGLE_GROUPS]),
    underwood_statue=dict(pos=list(UW_STATUE), rot=math.radians(-14)),
    court=dict(pos=COURT['pos'], rot=COURT['rot'], L=COURT['L'], W=COURT['W']),
    fountain=dict(FOUNTAIN, rot=0.0),                            # (the column's arms face the compass points)
    gate=dict(pos=[round(GATE_C[0], 2), round(GATE_C[1], 2)], rot=math.radians(-14)),      # (정문의 자리, above)
)
_tn = dict(TENNIS, rot=round(TENNIS['rot'], 5))
for v in STATUES.values():
    v['h'] = round(ground_h(*v['pos']), 2)
STATUES['court']['h'] = COURT_Z         # (on the terrace behind 백양로's bank, AUD_BANK: level, at its middle's)
# its stone skirt down to the lowest ground round it and half a metre under
_cr = court_poly(1.2).exterior
STATUES['court']['skirt'] = round(max(2.0, COURT_Z + 0.5 - min(ground_h(*_cr.interpolate(k_ / 80, normalized=True).coords[0])
                                                             for k_ in range(80))), 2)
# 공학원 (연세공학원) broke ground on 18 August 1995 on the 정구장's two blocks (TENNIS) and was finished on 8 April 1999
# (yonsei.ac.kr/sc/349: 지하 5층 · 지상 4층; namu.wiki): the 1990 · 1994 · 1995 maps and the 1994 aerial photo show the
# courts before it.  In the spring of 1997 the block between the service roads was a building site: bare earth behind
# a hoarding round the hall's outline and the courts' pads, its gate on the service road to the north
# (reference/고증.md 4.4).  The courts' levelled pads and the planting laid out round them stay as they were.
_gw = unary_union([footprint(ways[218430716])] + [tennis_poly(pd_, 1.0) for pd_ in TENNIS['pads']]).convex_hull
_gw = _gw.difference(unary_union([LineString(p_['pts']).buffer(p_['w'] / 2 + 1.0) for p_ in paths_out
                                  if p_['kind'] in ('service', 'residential', 'primary', 'secondary', 'tertiary', 'road')
                                  and len(p_['pts']) > 1 and LineString(p_['pts']).distance(_gw) < 5.0]))
GONGWON_SITE_RNG = shapely.geometry.polygon.orient(max(getattr(_gw, 'geoms', [_gw]), key=lambda g_: g_.area).simplify(0.6), 1.0)
# The vertical aerial photos of 28 July 1997 (자료 Q, tools/aerial97.py: frames 26/16 and 26/15, the east side in 27/17
# too; resampled into the courts' own frame, TENNIS, at the ground's height: reference/고증/4.4) have the site itself,
# a rectangle 134.5 x 84.5 m behind its hoarding (the frames within 1 m of each other), 14.5 m further west, 11.5 m
# further east and 11.5 m further south than the hull of the hall's outline and the pads above; its south side steps
# 7 m north for its east 43 m.  (u, v): TENNIS's frame, along the site and up its slope.
#  - Inside, no storey over the ground yet: a deck with a grid of beams 3 m under the ground round it (two frames'
#    stereo: 24.7 - 25.6 m at eight places where the roads round it are at 28.0 - 28.8 m) over all but the west 28 m,
#    which is a slab at the ground's own height (28.0 m).
#  - East of it the site's own ground between the hoarding and the lawn's trees: a car park of some twenty cars (the
#    booth and the lanes of photo A lead into it), a row of cars along the north hoarding, a two-storey prefab office
#    31 x 5.5 m north of the lane (its roof 4.9 m over the ground) with a smaller one west of it, and south of the
#    car park a yard behind three low prefab rows down to the gate's forecourt.
#  - No court is left: the whole block is the site.
_gc_, _gs_ = math.cos(TENNIS['rot']), math.sin(TENNIS['rot'])


def site_xy(u, v):
    return (TENNIS['o'][0] + u * _gc_ - v * _gs_, TENNIS['o'][1] + u * _gs_ + v * _gc_)


def site_poly(pts):
    return Polygon([site_xy(u_, v_) for u_, v_ in pts])


GONGWON_SITE = shapely.geometry.polygon.orient(site_poly([(-80.5, -4.5), (10.5, -4.5), (10.5, 2.5), (51.0, 2.5), (54.0, 6.0),
                                                          (54.0, 80.0), (-80.5, 80.0)]), 1.0)
GW_LOT = site_poly([(54.6, 56.5), (54.6, 91.8), (77.5, 91.8), (89.5, 83.5), (89.5, 56.5)])       # the car park (asphalt)
GW_ROW = site_poly([(-16.0, 80.6), (54.6, 80.6), (54.6, 88.5), (-16.0, 88.5)])                   # the row along the hoarding
GW_YARD = site_poly([(54.6, 8.0), (54.6, 56.5), (76.0, 56.5), (76.0, 30.0), (70.5, 30.0), (70.5, 22.0), (62.0, 8.0)])   # (bare)
GW_SHEDS = [(46.7, 77.4, 92.2, 97.7, 5.0), (37.0, 46.3, 93.2, 101.0, 2.7),           # the offices: u0, u1, v0, v1, height
            (76.0, 90.0, 49.0, 53.0, 2.8), (77.3, 80.0, 28.0, 49.0, 2.6), (71.0, 79.0, 23.5, 29.0, 2.8)]
GW_SHED_POLYS = [site_poly([(u0_, v0_), (u1_, v0_), (u1_, v1_), (u0_, v1_)]) for u0_, u1_, v0_, v1_, _ in GW_SHEDS]
assert not any(Polygon(b_['footprint']).intersects(p_) for b_ in buildings for p_ in GW_SHED_POLYS + [GONGWON_SITE])
GW_PIT, GW_SLAB = (-50.0, 47.0, 9.0, 74.0), (-74.5, -53.0, 2.0, 74.0)      # the deck in the pit, the slab at the ground's height
_gr, GONGWON_RING = GONGWON_SITE.exterior, []
for k_ in range(int(math.ceil(_gr.length / 2.5))):
    q_ = _gr.interpolate(k_ * _gr.length / math.ceil(_gr.length / 2.5))
    GONGWON_RING.append([round(q_.x, 2), round(q_.y, 2), round(ground_h(q_.x, q_.y), 2)])
_gq = site_xy(6.0, 80.0)                # (the gate: the gap in the row of cars along the north hoarding)
_gn = min(range(len(GONGWON_RING)), key=lambda k_: math.hypot(GONGWON_RING[k_][0] - _gq[0], GONGWON_RING[k_][1] - _gq[1]))
# the pit and the slab: level, the pit 3 m under the ground as it stood there (after the planting: nothing reads it)
_gzz = []
for (u0_, u1_, v0_, v1_), dz_ in ((GW_PIT, -3.0), (GW_SLAB, 0.0)):
    _in = shapely.contains_xy(site_poly([(u0_, v0_), (u1_, v0_), (u1_, v1_), (u0_, v1_)]), X, Y)
    _gzz.append(round(float(np.median(Hn[_in])) + dz_, 2))
    Hn[_in] = _gzz[-1]
_gz0 = _gzz[1]
STATUES['gongwon_site'] = dict(ring=GONGWON_RING, gate=[_gn - 1, _gn + 1],     # (the gate: ring points either side)
                               o=list(TENNIS['o']), rot=round(TENNIS['rot'], 5), pit=[*GW_PIT, _gzz[0]],
                               slab=[*GW_SLAB, _gzz[1]],
                               sheds=[[u0_, u1_, v0_, v1_, round(min(ground_h(*site_xy(u_, v_)) for u_ in (u0_, u1_) for v_ in (v0_, v1_)), 2), h_]
                                      for u0_, u1_, v0_, v1_, h_ in GW_SHEDS])
print('공학원 site', round(GONGWON_SITE.area), 'm2 (first', round(GONGWON_SITE_RNG.area), '), hoarding', round(_gr.length), 'm, ground',
      _gz0)
# the walks and service roads OSM has across it now go (the minimap, the crowd's walks: gw_cut, once the decals are
# laid along the walks as they were: decal_spots draws its random numbers walk by walk)
_gwz = unary_union([GONGWON_SITE.buffer(1.0), GW_YARD, GW_LOT.difference(GATE_APRON.buffer(1.0))] + [p_.buffer(0.8) for p_ in GW_SHED_POLYS])


def gw_cut(lst):
    po_ = []
    for p_ in lst:
        if len(p_['pts']) < 2 or not LineString(p_['pts']).intersects(_gwz) or p_['pts'] in _fork_pts:
            po_.append(p_)
            continue
        rest_ = LineString(p_['pts']).difference(_gwz)
        for l_ in (rest_.geoms if hasattr(rest_, 'geoms') else [rest_]):
            if l_.geom_type == 'LineString' and l_.length > 4.0:
                po_.append(dict(p_, pts=[[round(x_, 1), round(y_, 1)] for x_, y_ in l_.coords]))
    print('공학원 site: walks and roads cut', len(lst), '->', len(po_))
    lst[:] = po_

_sx, _sy, _ = along_raw(GATE_S + 6.0, E_VERGE + ROAD['walk'] * 0.5)        # on the west sidewalk just inside the gate (s 30 before)
SPAWN = dict(pos=[round(_sx, 1), round(_sy, 1)], yaw=math.radians(-14))

# ---------------------------------------------------------------------------
# 정문 밖 (tools/gate_town.py, reference/고증/4.8_정문_밖.md): 성산로's bed levelled and the rails' bed cut where the
# ground stands over it, after the planting and everything else that reads the ground inside the gate.  The gate's
# wall: blender/props.py gate, 31.5 m either way from the gate's middle (STATUES['gate']).
# ---------------------------------------------------------------------------
_gate_c, _gate_r = np.array(STATUES['gate']['pos']), STATUES['gate']['rot']
_gate_w = np.array([math.cos(_gate_r), math.sin(_gate_r)]) * 31.5
TOWN_PLAN = gate_town.plan(Hn, NEAR_HALF, NEAR_STEP, GATE_C, along_raw(GATE_S, 0.0)[2], (_gate_c - _gate_w, _gate_c + _gate_w), ground_h)
TOWN_SECS = gate_town.bank_fix(TOWN_PLAN, Hn, ground_h)
print('정문 밖: 성산로 %.0f m, 철둑 %.0f m, 레일 높이 %.2f m (정문 앞 길 %.2f m)' % (
    TOWN_PLAN['road'].cum[-1], TOWN_PLAN['rail'].cum[-1], TOWN_PLAN['rail_z'], TOWN_PLAN['rail_z'] - gate_town.RAIL_UP))
# 신촌 로터리 (tools/sinchon_rotary.py, reference/고증/4.10_신촌_로터리.md): the near terrain's patch south of the grid
# (y -1200 .. -800), and the bed of 연세로 south of the bridge and of the junction, levelled across
HS = sinchon_rotary.patch(raw_grid, Hn, NEAR_HALF, NEAR_STEP)
ROT_GEO = sinchon_rotary.streets(TOWN_PLAN)
ROT_LEVEL = sinchon_rotary.level(Hn, HS, NEAR_HALF, NEAR_STEP, ROT_GEO, ground_h)
print('신촌 로터리: 교차로 높이 %.2f m, 연세로 %s, 길 %s' % (ROT_LEVEL['z_junction'], ROT_LEVEL['z_yonsei'], ROT_LEVEL['arms']))


def ground_t(x, y):
    """the ground as saved, the patch south of the grid too"""
    return sinchon_rotary.sample_s(HS, x, y) if sinchon_rotary.in_patch(x, y) else ground_h(x, y)

jk_grade()             # (연구관 · 장기원 기념관's terrace: above, with the other grading)
# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
os.makedirs(os.path.join(ROOT, 'web/public/data'), exist_ok=True)
Hn.astype(np.float32).tofile(os.path.join(ROOT, 'web/public/data/terrain_near.bin'))
HS.astype(np.float32).tofile(os.path.join(ROOT, 'web/public/data/terrain_south.bin'))
Hf = np.array(tf['rows_south_to_north'], dtype=np.float32)
Hf = ndimage.gaussian_filter(Hf, 0.7).astype(np.float32)
Hf.tofile(os.path.join(ROOT, 'web/public/data/terrain_far.bin'))
# ---------------------------------------------------------------------------
# Building name markers (bird's-eye pins, walk-mode labels, big map).  One per name, over its largest footprint.
# MARKER_NAME: the name a 1997 student would use (or None: no marker, e.g. not built yet in 1997).
# ---------------------------------------------------------------------------
buildings[:] = [b for b in buildings if not any(b is q for q in YONGJAE_SCATTER)] + YONGJAE_BUILDINGS   # (above)
# GONE_1997 / LATE_FOOTPRINT_1997 (with the hall table above): the planting is done
GONE_SITES = [(GONE_1997[b['id']], Polygon(b['footprint'])) for b in buildings if b['id'] in GONE_1997
              and b['id'] not in FIELD_GONE]     # (대운동장 북쪽 끝의 둘: no site, cleared with the field below)
FIELD_GONE_SITES = [Polygon(b['footprint']) for b in buildings if b['id'] in FIELD_GONE]
# (blender/build.py draws each hall's colours and roof clutter from one stream in this list's order: it still draws
# for these at their old place, `at`, so that the halls after them keep their looks)
RND_GHOSTS = [{**{k_: v_ for k_, v_ in b.items() if k_ != 'entry'}, 'at': i_ - j_}
              for j_, (i_, b) in enumerate((i_, b) for i_, b in enumerate(buildings) if b['id'] in GONE_1997)]
buildings[:] = [b for b in buildings if b['id'] not in GONE_1997]
# (연합신학대학원, UTS above: a pitched stone hall draws nothing from that stream, with OSM's outline or with the one put in
# its place below, so it keeps its place in the list)
UTS_OSM = Polygon(next(b for b in buildings if b['id'] == UTS)['footprint'])
# the OLD_HALLS put back after the planting (OLD_HALLS_EARLY): at the end of the halls list, so that blender/build.py's
# colour and roof draws for the halls before them stay as they were (their doors once the outlines below are in)
LATE_HALLS = []
for pid, nm, style, lv, poly in OLD_HALLS:
    if pid in OLD_HALLS_EARLY:
        continue
    poly = shapely.geometry.polygon.orient(poly.simplify(0.05), 1.0)
    hs = [ground_h(x, y) for x, y in poly.exterior.coords]
    LATE_HALLS.append(dict(id=pid, name=nm, style=style, levels=lv,
                           height=round(lv * FLOOR_H_AT.get(pid, FLOOR_H[style]) + 1.2, 2),
                           base=BK_FRONT_BASE if pid == 990022 else BASE_1997.get(pid, round(min(hs), 2)),
                           top_ground=round(max(hs), 2),
                           footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]]))
buildings += LATE_HALLS
# (연합신학대학원: the 1997 hall's door in the middle of its east wall, where OSM's walk from the road east of it comes
# in; the photos do not show it.  Set here: the planting ran with the door of OSM's outline)
UTS_FP = Polygon(LATE_FOOTPRINT_1997[UTS])
UTS_DOOR = tuple((np.array(LATE_FOOTPRINT_1997[UTS][1]) + np.array(LATE_FOOTPRINT_1997[UTS][2])) / 2)
ENTRY_AT[UTS] = (UTS_DOOR, {})
LATE_SITES = []
LATE_SITES_RNG = []        # (as the trees were first cleared: MED_SITES_RNG)
for b in buildings:
    if b['id'] not in LATE_FOOTPRINT_1997:
        continue
    poly = Polygon(LATE_FOOTPRINT_1997[b['id']])
    poly = shapely.geometry.polygon.orient(poly if b['id'] in LATE_NO_SIMPLIFY else poly.simplify(0.35), 1.0)
    hs = [ground_h(x, y) for x, y in poly.exterior.coords]
    b.update(base=BASE_1997.get(b['id'], round(min(hs), 2)), top_ground=round(max(hs), 2),
             footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]])
    if b['id'] in LATE_LEVELS:
        b.update(levels=LATE_LEVELS[b['id']], height=round(LATE_LEVELS[b['id']] * FLOOR_H[b['style']] + 1.2, 2))
    if b['id'] == 222843398:           # (blender/generic.py: the part a storey higher, the roof's domes and penthouse)
        b['wing'] = [list(sci_xy(u_, v_)) for u_, v_ in SCI['wing']]
        b['roof'] = dict(o=[float(v_) for v_ in SCI['o']], t=[round(float(v_), 5) for v_ in SCI['t']],
                         dome=SCI['dome'], pent=SCI['pent'], dome2=SCI['dome2'], tank=SCI['tank'], clutter=SCI['clutter'])
    _bp_all = [Polygon(b_['footprint']) for b_ in buildings]
    poly = next(q for q, b_ in zip(_bp_all, buildings) if b_ is b)
    b.pop('entry', None)
    e_ = _entry(b, poly) if b['style'] in ENTRY_STYLES else None       # (the landmarks make their own doors)
    if e_:
        b['entry'] = dict(p=[round(e_[1], 2), round(e_[2], 2)], n=[round(e_[3], 4), round(e_[4], 4)],
                          **ENTRY_AT.get(b['id'], (0, {}))[1])
    LATE_SITES.append(poly)
    if b['id'] not in SITES_NEW_1997 and MED_SITES_RNG.get(b['id'], poly) is not None:
        LATE_SITES_RNG.append(MED_SITES_RNG.get(b['id'], poly))
_bp_all = [Polygon(b_['footprint']) for b_ in buildings]
for b in LATE_HALLS:
    poly = next(q for q, b_ in zip(_bp_all, buildings) if b_ is b)
    e_ = _entry(b, poly) if b['style'] in ENTRY_STYLES else None
    if e_:
        b['entry'] = dict(p=[round(e_[1], 2), round(e_[2], 2)], n=[round(e_[3], 4), round(e_[4], 4)],
                          **ENTRY_AT.get(b['id'], (0, {}))[1])
    if not ball.buffer(0.5).contains(poly):                  # (not the parts of an outline that stood at the planting)
        LATE_SITES.append(poly)
    q_ = None if b['id'] in SITES_NEW_1997 else MED_SITES_RNG.get(b['id'], poly)
    if q_ is not None and b['id'] in MED_SITES_RNG:           # (rounded as its footprint was)
        q_ = Polygon([(round(x, 2), round(y, 2)) for x, y in
                      list(shapely.geometry.polygon.orient(q_.simplify(0.05), 1.0).exterior.coords)[:-1]])
    if q_ is not None and not ball.buffer(0.5).contains(q_):
        LATE_SITES_RNG.append(q_)
print('1997: left out', [n for n, _ in GONE_SITES], '- outlines put back', len(LATE_SITES))
MARKER_NAME = {n: None for n in ('별동연구동', '영빈관', '영선실', '차량실', '행정동', '학생회관 별관', '광혜관')}
EXTRA_MARKERS = [('청송대', 238.0, 284.0), ('농구장', COURT['pos'][0], COURT['pos'][1])]          # the wooded park east of 연희관 (OSM leisure=park)
EXTRA_MARKERS += [(n, round(p.centroid.x, 1), round(p.centroid.y, 1)) for n, p in GONE_SITES if n]
EXTRA_MARKERS += [('공학원 (공사중)', round(GONGWON_SITE.centroid.x, 1), round(GONGWON_SITE.centroid.y, 1))]
EXTRA_MARKERS += [('대운동장', round(FIELD_POLY.centroid.x, 1), round(FIELD_POLY.centroid.y, 1))]
LANDMARK_NAMES = {l['name'] for l in LANDMARKS}
groups = {}
for b in buildings:
    if not b['name'] or b['style'] == 'city':
        continue
    nm = MARKER_NAME.get(b['name'], b['name'])
    if not nm or nm in LANDMARK_NAMES:
        continue
    poly = Polygon(b['footprint'])
    g = groups.get(nm)
    if g is None or poly.area > g[0]:
        groups[nm] = (poly.area, poly, b)
markers = []
for nm, (area, poly, b) in groups.items():
    c = poly.representative_point() if not poly.contains(poly.centroid) else poly.centroid
    markers.append(dict(name=nm, pos=[round(c.x, 1), round(c.y, 1)], top=round(b['base'] + b['height'] + 1.0, 1)))
for nm, x, y in EXTRA_MARKERS:
    markers.append(dict(name=nm, pos=[x, y], top=round(ground_h(x, y) + 12, 1)))
print('markers', len(markers))

# the apron's lane paint, resampled every metre and draped on the terrain (blender/road.py lays it on)
APRON_PAINT = []
for k_, c_ in APRON_LINES:
    ls_ = LineString(c_)
    pts_ = [ls_.interpolate(d_).coords[0] for d_ in np.arange(0, ls_.length + 0.01, 1.0)]
    APRON_PAINT.append(dict(kind=k_, pts=[[round(x, 2), round(y, 2), round(ground_h(x, y), 3)] for x, y in pts_]))

# 백양로 가운데 초소 (the guard booth on the centre line, 1997 aerial photo x 1020 - 1049, y 841 - 906): its foot
# (x 1034.5, y 906.5) kept as the pixel and placed on the road profile through PHOTO_A (issue #83: first read through
# the camera of before #8, 132.8 m in, 0.34 m east of the centre line), 1.4 m across; a red-and-white barrier arm runs
# west from beside it across the outgoing lane and another east across the incoming lane further on.
# blender/props.py guard_booth / barrier_arm build it in a frame with the origin at the booth's centre, -Y up the
# road, +X west; the arm pivots below are that file's BOOTH_ARMS (x, y, z, side).  The cars keep clear of its island
# (web/src/main.js) and the arms swing up for them (web/src/life.js BoothGates).
# Across the road it stands where the photo has it between its two yellow edge lines (their pixels on the foot's row,
# x 961.6 and 1105.6): the photo's carriageway lies some 1.15 m east of the game's centre line there (reference/
# 고증.md 2.2.1, the centre line kept), so the foot's own offset would put the island 1.2 m east, leaving the
# northbound lane 1.3 m of asphalt (as it was before)
def _photo_road_off(px, py):
    o_, d_ = photo_ray(px, py)
    z_ = 30.0
    for _ in range(12):
        q_ = o_ + d_ * (z_ - o_[2]) / d_[2]
        z_ = prof_h(s_at(q_[0], q_[1]))
    return s_off(q_[0], q_[1])


_bs_, _boff_ = _photo_road_off(1034.5, 906.5)
_bmid_ = (_photo_road_off(961.6, 906.0)[1] + _photo_road_off(1105.6, 906.0)[1]) / 2
BOOTH = dict(s=round(_bs_, 1), off=round(_boff_ - _bmid_, 2), island=[-0.85, 0.85, -6.0, 1.6])
print('guard booth s %.1f, %.2f m west (the photo\'s carriageway: its middle %.2f m west of the centre line)'
      % (BOOTH['s'], BOOTH['off'], _bmid_))
_bx, _by, _ba = along_raw(BOOTH['s'], BOOTH['off'])
props.append(['guard_booth', round(_bx, 2), round(_by, 2), round(_ba, 3)])
BOOTH['arms'] = []
for _ax, _ay, _az, _sd in ((0.82, -1.5, 1.0, 1), (-0.82, -5.5, 1.0, -1)):
    _px = _bx + _ax * math.cos(_ba + math.pi / 2) + _ay * math.cos(_ba + math.pi)
    _py = _by + _ax * math.sin(_ba + math.pi / 2) + _ay * math.sin(_ba + math.pi)
    BOOTH['arms'].append(dict(x=round(_px, 2), y=round(_py, 2), z=_az, dir=round(_ba + _sd * math.pi / 2, 3),
                              s=round(BOOTH['s'] - _ay, 2), side=_sd))

# 중앙도서관 앞: OSM's walks through the 1997 beds are the later layout (the beds are lawn now); the 1997 walks go
# first, so that the crowd (web/src/main.js) walks the slant one
def lib_osm_walk(p_):
    return p_['kind'] in ('footway', 'path', 'steps', 'pedestrian') and len(p_['pts']) > 1 \
        and LIB_BEDS.buffer(1.0).contains(LineString(p_['pts']).centroid)


LIB_PATHS = [dict(kind='footway', w=LIB_DIAG_W, pts=[[round(x, 1), round(y, 1)] for x, y in LIB_DIAG]),
             dict(kind='footway', w=LIB_SDIAG_W, pts=[[round(x, 1), round(y, 1)] for x, y in LIB_SDIAG]),
             dict(kind='footway', w=8.0, pts=[[round(x, 1), round(y, 1)] for x, y in (LF(38.5, 11.0), LF(38.5, 47.0))]),
             dict(kind='footway', w=6.0, pts=[[round(x, 1), round(y, 1)] for x, y in (LF(-3.0, 8.0), LF(78.0, 8.0))])]


def _ui_paths():
    """The walks the game reads (out['paths']: the minimap, the crowd's walks), from paths_out as it stands; made again
    once 용재관's ground has changed paths_out (below)."""
    return LIB_PATHS + [dict(kind='service', w=SIDE_W_W, pts=[list(p_) for p_ in SIDE_W])] + \
        [p_ for p_ in paths_out if not lib_osm_walk(p_) and p_['pts'] not in _fork_pts]


# 백양로 as drawn (the road mesh, its decals, the cars and walkers): to the foot of the steps at the 삼거리 (UW_STEPS);
# the full line kept its section (to 615 m) and the planting.  The last crossing on the 삼거리's near side (the
# skyview's zebra across the road's end), not 30 m before the old end on the bank
bys = [tuple(c_) for c_ in substring(bline, 0.0, BY_END_S).coords]
CROSS = [c_ for c_ in CROSS if c_ < BY_END_S - 20.0] + [round(BY_END_S - 14.0, 1)]
CROSS_RNG = [c_ for c_ in CROSS_RNG if c_ < BY_END_S - 20.0] + [round(BY_END_S - 14.0, 1)]
GAPS = [g_ for g_ in GAPS if g_[0] < BY_END_S - 3.0]
def dwb_deck(cells=None, poly=None, hfun=None):
    """DAEWOO_BACK's upper level over the cells whose nodes the walls pulled down (above): triangles on a 1.25 m
    lattice cut to the level's outline, on its surface (dwb_h, 2.5 cm over it against the ground's own triangles under
    it), but along the edges it shares with whole cells of the ground exactly as the ground runs; its rim, for a skirt.
    (cells, poly, hfun: another level's, the terrace before the hall.)"""
    DWB_DECK_CELLS, DWB_DECK_POLY, dwb_h = (globals()['DWB_DECK_CELLS'], globals()['DWB_DECK_POLY'], globals()['dwb_h']) \
        if cells is None else (cells, poly, hfun)
    sub_ = NEAR_STEP / 4
    V_, F_ = {}, []

    def vid(x_, y_):
        return V_.setdefault((round(x_, 3), round(y_, 3)), len(V_))

    for j_, i_ in sorted(DWB_DECK_CELLS):
        for a_ in range(4):
            for b_ in range(4):
                sq_ = shapely.geometry.box(gx[i_] + b_ * sub_, gx[j_] + a_ * sub_, gx[i_] + (b_ + 1) * sub_, gx[j_] + (a_ + 1) * sub_)
                pc_ = sq_.intersection(DWB_DECK_POLY)
                for g_ in (pc_.geoms if hasattr(pc_, 'geoms') else [pc_]):
                    if g_.geom_type != 'Polygon' or g_.area < 1e-3:
                        continue
                    tris_ = [g_] if len(g_.exterior.coords) == 4 else \
                        [t_ for t_ in shapely.ops.triangulate(g_) if g_.buffer(1e-6).contains(t_.representative_point())]
                    for t_ in tris_:
                        c_ = list(shapely.geometry.polygon.orient(t_, 1.0).exterior.coords)[:3]
                        if Polygon(c_).area > 1e-4:
                            F_.append([vid(*q_) for q_ in c_])

    def zf(x_, y_):
        fx_, fy_ = (x_ + NEAR_HALF) / NEAR_STEP, (y_ + NEAR_HALF) / NEAR_STEP
        ii_ = [int(round(fx_)) - 1, int(round(fx_))] if abs(fx_ - round(fx_)) < 1e-6 else [int(math.floor(fx_))]
        jj_ = [int(round(fy_)) - 1, int(round(fy_))] if abs(fy_ - round(fy_)) < 1e-6 else [int(math.floor(fy_))]
        if any((j_, i_) not in DWB_DECK_CELLS for j_ in jj_ for i_ in ii_):
            return sample(Hn, NEAR_HALF, NEAR_STEP, x_, y_)                 # (a shared edge: as the ground runs)
        return dwb_h(x_, y_) + 0.025

    rings_ = []
    for g_ in (DWB_DECK_POLY.geoms if hasattr(DWB_DECK_POLY, 'geoms') else [DWB_DECK_POLY]):
        for r_ in [g_.exterior] + list(g_.interiors):
            rings_.append([[round(x_, 2), round(y_, 2), round(zf(x_, y_), 3)] for x_, y_ in shapely.segmentize(r_, 1.25).coords])
    vs_ = sorted(V_, key=V_.get)
    return dict(v=[[round(x_, 3), round(y_, 3), round(zf(x_, y_), 3)] for x_, y_ in vs_], f=F_, rim=rings_)


DAEWOO_BACK['deck'] = dwb_deck()
DAEWOO['deck'] = dwb_deck(DW_FDECK_CELLS, DW_FDECK_POLY, lambda x_, y_: DAEWOO['terrace'])
DAEWOO_BACK['lot_z'] = [round(dwb_lot_z(v_), 3) for v_ in (36.0, 75.0, 86.0)]
print('daewoo back deck: %d vertices, %d triangles, rim %d' % (len(DAEWOO_BACK['deck']['v']), len(DAEWOO_BACK['deck']['f']),
                                                             sum(len(r_) for r_ in DAEWOO_BACK['deck']['rim'])))
# the hall's outline as the 1997 photos' roofs have it (DW_OUTLINE_UV, in the hall's own frame: the wings 11.5 m wide
# either side of the axis, the back tower and the two blocks).  The planting and the ground were first laid out round
# OSM's outline (what stands in the new one's way goes below, DW_FRONT); points 3 -> 4 are the recessed front
_dwb_b = next(b_ for b_ in buildings if b_['id'] == 242897922)
DW_FP_RNG = Polygon(_dwb_b['footprint'])
_dwb_b['footprint'] = [[round(c_, 2) for c_ in dh_xy(*q_)] for q_ in DW_OUTLINE_UV]
out = dict(
    origin=[LAT0, LON0],
    terrain=dict(near=dict(half=NEAR_HALF, step=NEAR_STEP, n=n_near, file='data/terrain_near.bin'),
                 south={**sinchon_rotary.SOUTH, 'file': 'data/terrain_south.bin'},
                 far=dict(half=tf['half'], step=tf['step'], n=tf['n'], file='data/terrain_far.bin')),
    splat=SPLAT,
    tsplat=sinchon_rotary.TSPLAT,
    baekyangro=dict(pts=[[round(x, 2), round(y, 2)] for x, y in bys], profile_s=[round(v, 1) for v in ss[::2]],
                    profile_h=[round(float(v), 3) for v in prof[::2]], crossings=CROSS, bump=BUMP_S,
                    gaps=[list(g) for g in GAPS], mouths=[list(MOUTH)], apron_paint=APRON_PAINT, **ROAD),
    amphitheater={k: (round(v, 3) if isinstance(v, float) else v) for k, v in AMPH.items()},
    buildings=buildings, trees=trees, shrubs=shrubs, props=props, cars=cars, banners=banners,
    paths=_ui_paths(), landmarks=LANDMARKS, statues=STATUES, spawn=SPAWN, markers=markers, daewoo_front=DAEWOO, daewoo_back=DAEWOO_BACK,
    centennial_block=CENT_BLOCK, sang=dict(c=list(SANG), r=SANG_LAWN), yeonhui=YEONHUI, underwood_steps=UW_STEPS,
    gyoyuk_floor=GYOYUK_FLOOR,
    seongam_floor=SEONGAM_FLOOR,
    colliders=[CENT_BLOCK['poly']] + [[[round(x_, 2), round(y_, 2)] for x_, y_ in list(g_.exterior.coords)[:-1]]
                                      for g_ in [GONGWON_SITE] + GW_SHED_POLYS]
    + YH_WALL_COLL,
)
out['rnd_ghosts'] = RND_GHOSTS                # (GONE_1997: blender/build.py)
out['baekyangro']['booth'] = BOOTH
# 정문 앞 어귀: short of the gate (s 0 .. GATE_S) no verge, sidewalk or planting strip on either side, the asphalt flush
# out to the gate's mouth (blender/road.py mouths; [side, s0, s1, r0, r1]); they start a metre past the wall's line,
# clear of the gate's pillars (blender/props.py gate: 1.9 m square on its line)
out['baekyangro']['mouths'] += [[1, -2.0, round(GATE_S + 1.0, 2), 0.0, 0.0], [-1, -2.0, round(GATE_S + 1.0, 2), 0.0, 0.0]]
# 대강당 앞 둑: blender/road.py leaves the planting strip out where the wall stands, blender/landmarks.py aud_bank builds it
out['baekyangro']['walls'] = [[AUD_BANK['side'], AUD_BANK['s0'], AUD_BANK['s1']]]
out['baekyangro']['strip_breaks'] = [list(o_) for o_ in STRIP_OPEN]     # (제1공학관 앞 진입로, 백양관 앞)
out['baekyangro']['breaks'] = VERGE_BREAKS          # (the verge's openings besides crossings and gaps, above)
# yellow-and-black bollards on the ramps of the openings, where the 2008 and the 2010 roadview both have them
# (side, s; 1997 unknown): 백주년기념관 앞 건널목 (the one south of the grate), 학생회관 앞 (two, two, three, two and
# two in the forecourt's five openings, VERGE_BREAKS)
_bsm = [np.array(p_, float) for p_ in bys]
for _ in range(3):                                   # (the road mesh's own frame, Chaikin x3 as blender/road.py)
    _q = [_bsm[0]]
    for a_, b_ in zip(_bsm[:-1], _bsm[1:]):
        _q += [a_ + (b_ - a_) * 0.25, a_ + (b_ - a_) * 0.75]
    _bsm = _q + [_bsm[-1]]
_bsm = LineString(_bsm)
for _sd, _s in ((-1, 226.9), (-1, 369.6), (-1, 370.7), (-1, 378.6), (-1, 380.0), (-1, 388.3), (-1, 390.2), (-1, 392.1),
                 (-1, 396.9), (-1, 397.75), (-1, 402.6), (-1, 403.5)):
    _p, _p0, _p1 = _bsm.interpolate(_s), _bsm.interpolate(_s - 2), _bsm.interpolate(_s + 2)
    _tx, _ty = _p1.x - _p0.x, _p1.y - _p0.y
    _n = math.hypot(_tx, _ty)
    _o = _sd * (ROAD['median'] + ROAD['lane'] + 0.4)
    P('bollard', _p.x - _ty / _n * _o, _p.y + _tx / _n * _o, 0.0)
# (and before 백주년기념관's flights: paving and tree pits instead of the strip, CENT_TERRACE)
out['baekyangro']['walls'].append([-1, round(s_at(*ct_xy(CT_PAVED_S[1], 33.0)), 2), round(s_at(*ct_xy(CT_PAVED_S[0], 33.0)), 2)])
out['aud_bank'] = {k: v for k, v in AUD_BANK.items()}
out['aud_flight'] = AUD_FLIGHT                # (blender/landmarks.py aud_flight)
out['pave'] = PAVE                            # paving kinds in ground_dry.png's G and B (web/src/terrain.js)


# ---------------------------------------------------------------------------
# Decals on the paving (web/src/decals.js): [kind, x, y, heading, scale], the heading along the decal's long side.
# 백양로's carriageway stays as clean as in the 1997 photos: a manhole now and then in a lane, gully grates along both
# kerbs and the zebra stripes scuffed where the wheels run (its own frame: blender/road.py smooth_line, 2 m frames).
# The side roads, aprons and car parks get the wear: manholes down the middle, grates along the edges, saw-cut asphalt
# patches, oil under where cars stand (every stall, taken or not); the paving cracks and stains, a utility lid here and
# there on 백양로's sidewalks. Nothing on stairs, courts, building floors or out in the city round the campus.
def decal_spots():
    rnd = random.Random(1997 + 45)
    found = []

    def add(kind, x, y, rot, sc=1.0):
        found.append([kind, round(float(x), 2), round(float(y), 2), round(float(rot) % (2 * math.pi), 3), round(float(sc), 2)])

    def splat(x, y, ch):
        px, py = int((x - SPLAT['x0']) / SPLAT['res']), int((SPLAT['y1'] - y) / SPLAT['res'])
        return float(spl[py, px, ch]) if 0 <= px < SW and 0 <= py < SH else 0.0

    steps = [LineString(p_['pts']) for p_ in paths_out if p_['kind'] == 'steps' and len(p_['pts']) > 1]
    city = [Polygon(b['footprint']).buffer(25) for b in buildings if b['style'] == 'city']
    city += [p_.buffer(25) for p_ in FIELD_GONE_SITES]      # (the two left out by 대운동장: the draws stay as they were)
    # (신촌로 and its bus lanes along the south are the city's road, not the campus's)
    trunk = [LineString(p_['pts']).buffer(p_['w'] / 2 + 3.0) for p_ in paths_out
             if p_['kind'] in ('primary', 'primary_link', 'secondary', 'busway') and len(p_['pts']) > 1]
    banned = unary_union([ball.buffer(0.4), _ez, court_poly(1.0, COURT_OLD), Point(*FOUNTAIN['pos']).buffer(FOUNTAIN['pave'] + 0.3),
                          AMPH_PATHS.buffer(2.0)] + [l_.buffer(2.0) for l_ in steps] + city + trunk)
    shapely.prepare(banned)
    road_c = bline.buffer(ROAD_HALF + 1.0)
    shapely.prepare(road_c)
    # the campus: within 40 m of its trees (10 m cells)
    camp = np.zeros((int((SPLAT['y1'] - SPLAT['y0']) / 10) + 1, int((SPLAT['x1'] - SPLAT['x0']) / 10) + 1), bool)
    for t_ in trees:
        i_, j_ = int((SPLAT['y1'] - t_[2]) / 10), int((t_[1] - SPLAT['x0']) / 10)
        if 0 <= i_ < camp.shape[0] and 0 <= j_ < camp.shape[1]:
            camp[i_, j_] = True
    camp = ndimage.binary_dilation(camp, iterations=4)

    def in_camp(x, y):
        i_, j_ = ((SPLAT['y1'] - y) / 10).astype(int), ((x - SPLAT['x0']) / 10).astype(int)
        inside = (i_ >= 0) & (i_ < camp.shape[0]) & (j_ >= 0) & (j_ < camp.shape[1])
        return inside & camp[np.clip(i_, 0, camp.shape[0] - 1), np.clip(j_, 0, camp.shape[1] - 1)]

    def ok(x, y, pad=0.0):
        if not (-420 < x < 600 and -430 < y < 600) or not in_camp(np.array(x), np.array(y)):
            return False
        return not (shapely.intersects_xy(banned, x, y) or (pad > 0 and shapely.dwithin(banned, Point(x, y), pad)))

    # 백양로 in the road mesh's own frame (Chaikin x3 like blender/road.py smooth_line)
    P_ = [np.array(p_, float) for p_ in bys]
    for _ in range(3):
        Q_ = [P_[0]]
        for a_, b_ in zip(P_[:-1], P_[1:]):
            Q_ += [a_ + (b_ - a_) * 0.25, a_ + (b_ - a_) * 0.75]
        P_ = Q_ + [P_[-1]]
    sm = LineString(P_)
    Ls = sm.length

    def fr(s, off):
        p_, p0, p1 = sm.interpolate(s), sm.interpolate(max(0.0, s - 2)), sm.interpolate(min(Ls, s + 2))
        tx, ty = p1.x - p0.x, p1.y - p0.y
        n_ = math.hypot(tx, ty)
        return p_.x - ty / n_ * off, p_.y + tx / n_ * off, math.atan2(ty, tx)

    e_lane = ROAD['median'] + ROAD['lane']

    def near_cross(s, pad, cr=None):
        return any(abs(s - c_) < pad for c_ in (cr or CROSS)) or abs(s - BUMP_S) < pad - 1.0

    # (the random draws below follow the crossings where they were first put, CROSS_RNG)
    # manholes every 50 m, in the middle of one lane or the other (clear of the booth's island)
    for k, s in enumerate(np.arange(30.0, Ls - 10, 50.0)):
        s += rnd.uniform(-6, 6)
        if near_cross(s, 6.0, CROSS_RNG) or BOOTH['s'] - 9 < s < BOOTH['s'] + 4:
            continue
        x, y, h = fr(s, (1 if k % 2 else -1) * (e_lane * 0.5 + rnd.uniform(-0.3, 0.3)))
        a_ = rnd.uniform(0, 2 * math.pi)
        if not near_cross(s, 6.0):
            add('manhole', x, y, a_)
    # gully grates against both kerbs every 30 m (none in a crossing, a side road's opening, an opening in the verge or
    # the mouth by the gate): in the concrete gutter, filling its 0.3 m against the kerb (2008 / 2010 roadview, the
    # grates 0.28 m across; the decal's 1.0 x 0.42 m scaled to 0.7 x 0.29 m)
    for side, s0 in ((1, 14.0), (-1, 29.0)):
        for s in np.arange(s0, Ls - 8, 30.0):
            if near_cross(s, 5.5) or (side == MOUTH[0] and MOUTH[1] - 6 < s < MOUTH[2] + 5) \
                    or any(sd == side and abs(s - g_) < hw + 1.5 for g_, sd, hw in GAPS) \
                    or in_break(s, side, 1.5):
                continue
            x, y, h = fr(s, side * (e_lane - ROAD['gutter'] / 2))
            add('drain', x, y, h, 0.7)
    # the big grates in the crossings' openings against the kerb line (2008 / 2010 / 2011 roadview: 백주년기념관 앞 on
    # both sides, the east one half under a loose steel plate; 학생회관 앞 east, between the bollards): the gully grate's
    # decal at full size (1.0 x 0.42 m; the grates 0.6 - 0.8 m, no square decal)
    for c_i, side, ds in ((0, -1, 0.1), (0, 1, 0.4), (1, -1, 0.8)):
        x, y, h = fr(CROSS[c_i] + ds, side * (e_lane - 0.2))
        add('drain', x, y, h, 1.0)
    # the zebra stripes (road.py: centred on the 2 m frame nearest the crossing, 0.5 m wide, 4 m long, 1 m apart):
    # worn where the wheels run, 0.75 m either side of each lane's middle. Each stripe is a flat quad 12 mm over its
    # frame's height, so on the slope its uphill end sinks under the asphalt: only the part that shows (the scale is
    # the share of the 4 m), as road.py draws it from the 4 m profile
    wheels = [side * (e_lane * 0.5 + d_) for side in (-1, 1) for d_ in (-0.75, 0.75)]
    hroad = lambda s_: float(np.interp(s_, ss[::2], np.round(prof[::2], 3)))
    for c_ in CROSS:
        sc_ = 2.0 * round(c_ / 2.0)
        vis = [t_ for t_ in np.arange(-2.0, 2.001, 0.05) if hroad(sc_ + t_) < hroad(sc_) + 0.012 - 0.003]
        if len(vis) < 10:
            continue
        t0, t1 = min(vis), max(vis)
        o = -e_lane + 0.5
        while o < e_lane - 0.4:
            x, y, h = fr(sc_ + (t0 + t1) / 2, o + 0.25)
            add('wear' if min(abs(o + 0.25 - w_) for w_ in wheels) < 0.4 else 'wear_lt', x, y, h, (t1 - t0) / 4.0)
            o += 1.0
    # the sidewalks: cracked and stained paving, and a utility lid by the verge every ~45 m
    E_VERGE_, WALK_ = E_CURB + ROAD['verge'], ROAD['walk']
    for side in (-1, 1):
        for s in np.arange(5.0, Ls - 5, 7.0):
            s += rnd.uniform(-2.5, 2.5)
            if near_cross(s, 4.0, CROSS_RNG) or (side == MOUTH[0] and MOUTH[1] - 4 < s < MOUTH[2] + 4) or rnd.random() > 0.75:
                continue
            x, y, h = fr(s, side * (E_VERGE_ + 0.8 + rnd.random() * (WALK_ - 1.6)))
            add('crack' if rnd.random() < 0.6 else 'stain', x, y, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.8, 1.3))
        for s in np.arange(20.0 + (side > 0) * 20, Ls - 10, 45.0):
            if near_cross(s, 5.0, CROSS_RNG) or (side == MOUTH[0] and MOUTH[1] - 4 < s < MOUTH[2] + 4) or rnd.random() > 0.7:
                continue
            x, y, h = fr(s, side * (E_VERGE_ + 0.45))
            add('lid', x, y, h)

    # side roads (asphalt in the splat, away from 백양로): manholes down the middle every ~32 m, grates at the edges
    taken = {}

    def spaced(kind, x, y, r):
        key = (kind, int(x // r), int(y // r))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for (qx, qy) in taken.get((kind, key[1] + dx, key[2] + dy), ()):
                    if (qx - x) ** 2 + (qy - y) ** 2 < r * r:
                        return False
        taken.setdefault(key, []).append((x, y))
        return True

    road_lines = []
    for p_ in paths_out:
        if p_['kind'] not in ('service', 'residential', 'living_street', 'unclassified', 'road', 'tertiary', 'busway') \
                or len(p_['pts']) < 2:
            continue
        ls_ = LineString(p_['pts'])
        road_lines.append(ls_)
        hw = p_['w'] / 2
        for kind, step, offs in (('manhole', 38.0, (0.0,)), ('drain', 26.0, (hw - 0.25, -(hw - 0.25)))):
            for off in offs:
                for s in np.arange(rnd.uniform(4, step), ls_.length - 3, step):
                    a_, b_ = ls_.interpolate(max(0.0, s - 1)), ls_.interpolate(min(ls_.length, s + 1))
                    h = math.atan2(b_.y - a_.y, b_.x - a_.x)
                    nx, ny = -math.sin(h), math.cos(h)
                    q_ = ls_.interpolate(s)
                    j = rnd.uniform(-0.5, 0.5) if kind == 'manhole' else 0.0
                    x, y = q_.x + nx * (off + j), q_.y + ny * (off + j)
                    if splat(x, y, 0) < 200 or shapely.intersects_xy(road_c, x, y) or not ok(x, y, 0.8):
                        continue
                    if kind == 'drain':
                        # only at a real edge of the asphalt (not out in an apron), and not every time
                        sg = 1 if off > 0 else -1
                        if splat(x + nx * sg * 1.2, y + ny * sg * 1.2, 0) > 120 or rnd.random() > 0.55:
                            continue
                    if spaced(kind, x, y, 14.0 if kind == 'manhole' else 10.0):
                        add(kind, x, y, h if kind == 'drain' else rnd.uniform(0, 2 * math.pi))
    shapely.prepare(road_lines)

    def road_heading(x, y, fallback):
        best, bh = 9.0, fallback
        for ls_ in road_lines:
            d_ = ls_.distance(Point(x, y))
            if d_ < best:
                s = ls_.project(Point(x, y))
                a_, b_ = ls_.interpolate(max(0.0, s - 1)), ls_.interpolate(min(ls_.length, s + 1))
                best, bh = d_, math.atan2(b_.y - a_.y, b_.x - a_.x)
        return bh

    # parking: an oil stain under the engine of every stall, taken or not (the cars' +x is forward), a few drips
    (_x0, _y0), (_x1, _y1) = WD(0, 0), WD(1, 0)
    hu = math.atan2(_y1 - _y0, _x1 - _x0)
    stalls = []
    # (대우관 뒤: the stalls of the car park the game had there still draw, so that the campus keeps its stains; nothing
    # is put down for them: `ghost`.  The yard's own stains have their own numbers, below)
    for (u_, face) in [(27.6, -1), (38.4, 1), (43.6, -1), (54.4, 1), (59.6, -1)]:
        v_ = 33.0
        while v_ <= 76.0 + 0.01:
            if not (50.4 < v_ < 56.6):
                stalls.append((*WD(u_, v_), hu + (0.0 if face > 0 else math.pi), True))
            v_ += 2.6
    for (a_, b_, n) in lots:
        for k in range(n):
            t_ = k / max(1, n - 1)
            stalls.append((a_[0] + (b_[0] - a_[0]) * t_, a_[1] + (b_[1] - a_[1]) * t_, math.atan2(b_[1] - a_[1], b_[0] - a_[0]) + math.pi / 2))
    stalls += [(x, y, a_ + math.pi / 2) for (x, y, a_) in LOT_W]
    _gt, _gn = np.array([-0.969, 0.248]), np.array([0.248, 0.969])
    stalls += [(*(np.array([44.15, 345.23]) + _gt * s_ + _gn * 8.2), math.atan2(-_gn[1], -_gn[0])) for s_ in (1.8, 4.4, 7.0, 9.6, 12.2, 14.8)]
    _add = add
    for (x, y, h, *ghost) in stalls:
        if (not ghost and max(splat(x, y, 0), splat(x, y, 1)) < 160) or not ok(x, y):
            continue
        add = (lambda *a_: None) if ghost else _add
        if rnd.random() < 0.8:
            f_ = rnd.uniform(0.9, 1.5)
            add('oil', x + math.cos(h) * f_, y + math.sin(h) * f_, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.6, 1.1))
        if rnd.random() < 0.35:
            f_ = rnd.uniform(-1.4, 0.4)
            add('oil', x + math.cos(h) * f_, y + math.sin(h) * f_, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.35, 0.6))
    add = lambda *a_: None                                        # (the old car park's aisles: drawn, not put down)
    # the car park's aisles behind 대우관: polished darker where the cars turn in, a patch or two, a manhole, grates at
    # its low (west) side
    for u_ in (33.0, 49.0):
        for v_ in np.arange(32.0, 78.0, 7.5):
            x, y = WD(u_ + rnd.uniform(-1, 1), v_ + rnd.uniform(-2, 2))
            add('grime', x, y, hu + math.pi / 2 + rnd.uniform(-0.2, 0.2), rnd.uniform(0.9, 1.3))
    for (u_, v_, kind, sc_) in ((49.0, 53.5, 'manhole', 1.0), (33.5, 61.0, 'patch', 1.1), (48.0, 36.0, 'patch', 0.8),
                                 (41.0, 72.0, 'patch', 1.4)):
        x, y = WD(u_, v_)
        add(kind, x, y, hu + rnd.choice((0.0, math.pi / 2)) + rnd.uniform(-0.03, 0.03), sc_)
    add = _add
    # the yard as it is (DAEWOO_BACK): its stalls' stains, the aisles' grime, a manhole, the grating across the low
    # court's mouth (Naver street view 2010)
    _rd = random.Random(1997 + 157)
    for _, _, (x, y), h, _ in dwb_stalls():
        if _rd.random() < 0.8:
            f_ = _rd.uniform(0.9, 1.5)
            add('oil', x + math.cos(h) * f_, y + math.sin(h) * f_, _rd.uniform(0, 2 * math.pi), _rd.uniform(0.6, 1.1))
    for u_ in DAEWOO_BACK['aisles']:
        for v_ in np.arange(48.0, 68.0, 7.0):
            x, y = WD(u_ + _rd.uniform(-0.6, 0.6), v_ + _rd.uniform(-2, 2))
            add('grime', x, y, hu + math.pi / 2 + _rd.uniform(-0.2, 0.2), _rd.uniform(0.9, 1.3))
    for (u_, v_, kind, sc_, r_) in ((50.8, 58.0, 'manhole', 1.0, 0.0), (12.0, 50.5, 'patch', 1.1, 0.5), (51.0, 73.5, 'patch', 0.9, 0.78),
                                    (7.6, 56.3, 'drain', 1.0, 0.96), (9.0, 58.2, 'drain', 1.0, 0.96), (39.3, 84.6, 'drain', 1.0, -0.76)):
        x, y = WD(u_, v_)
        add(kind, x, y, hu + r_, sc_)

    # the rest of the asphalt: saw-cut patches (lined up with the nearest road) and dark blotches, ~1 per 220 m²
    def scatter(ch, thresh, per_m2, r):
        yy, xx = np.nonzero(spl[..., ch] > thresh)
        xs, ys = SPLAT['x0'] + (xx + 0.5) * SPLAT['res'], SPLAT['y1'] - (yy + 0.5) * SPLAT['res']
        keep = (xs > -420) & (xs < 600) & (ys > -430) & (ys < 600)
        xs, ys = xs[keep], ys[keep]
        keep = in_camp(xs, ys)
        xs, ys = xs[keep], ys[keep]
        keep = ~shapely.intersects_xy(banned, xs, ys) & ~shapely.intersects_xy(road_c, xs, ys)
        xs, ys = xs[keep], ys[keep]
        n = int(len(xs) * SPLAT['res'] ** 2 / per_m2)
        idx = list(range(len(xs)))
        rnd.shuffle(idx)
        picked = []
        for i in idx:
            if len(picked) >= n:
                break
            if spaced(ch, xs[i], ys[i], r):
                picked.append((float(xs[i]), float(ys[i])))
        return picked
    for (x, y) in scatter(0, 230, 220.0, 6.0):
        if not ok(x, y, 1.2):
            continue
        if rnd.random() < 0.7:
            add('patch', x, y, road_heading(x, y, rnd.uniform(0, math.pi)) + rnd.choice((0.0, math.pi / 2)) + rnd.uniform(-0.04, 0.04),
                rnd.uniform(0.6, 1.5))
        else:
            add('grime', x, y, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.6, 1.1))
    # ... and the paving of walks and forecourts: cracks and stains, ~1 per 75 m²
    for (x, y) in scatter(1, 230, 75.0, 3.5):
        if ok(x, y, 0.6):
            add('crack' if rnd.random() < 0.55 else 'stain', x, y, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.7, 1.3))
    return found


out['decals'] = decal_spots()
gw_cut(paths_out)                          # (공학원 공사장: above)
gw_cut(out['paths'])
out['decals'] = [d_ for d_ in out['decals'] if not court_poly(1.0).contains(Point(d_[1], d_[2]))]   # (the court's slab)
out['decals'] = [d_ for d_ in out['decals'] if not _uwz.contains(Point(d_[1], d_[2]))]   # (the old garden's paving)
print('decals', len(out['decals']), {k_: sum(1 for d_ in out['decals'] if d_[0] == k_) for k_ in sorted({d_[0] for d_ in out['decals']})})
# 용재관's ground (YONGJAE above) now that the random draws are done.  The photo has the 진달래동산 right behind the
# statue: the bank between the 삼거리's east fork and the hall's 백양로 side and north end, one sheet of azaleas with
# the walk and its flight going up through it (YJ_GARDEN, with the bank round the level ground on those sides).  OSM's
# walks over the hall's ground go, and so do the parts of the 2010s walks and drive over the bank (they go round
# 경영관); the decals there go, and the splat there is painted again: the old outline's aprons and the bank's
# paving out, the new hall's aprons, the paving along the porch and the fin face, and its walk in.
_SE_FORK = Polygon([(-10, 181.5), (38, 163.5), (62, 155.5), (85, 145.5), (110, 135.5), (160, 115.5), (160, 40),
                    (-10, 40)])                                      # (this side of the 삼거리's east fork)
_YG_RNG = unary_union([yongjae_poly(-22.0, -7.0, 16.0, 52.0, YONGJAE_RNG), yongjae_poly(-7.0, 10.0, 43.0, 52.0, YONGJAE_RNG)])
# (the bank as it was laid round the hall as first put, and on east to the hall where the aerial photos have it)
YJ_GARDEN = unary_union([_YG_RNG, yongjae_poly(-30.0, -7.0, 12.0, 58.0).intersection(_SE_FORK),
                         yongjae_poly(-7.0, 0.0, 43.0, 56.0).intersection(_SE_FORK)]).difference(
    bline.buffer(ROAD_HALF + 3.0)).difference(YJ_DRIVE.buffer(3.6)).difference(YJ_PAD)   # (the east fork runs through it)
_YG_RNG = _YG_RNG.difference(bline.buffer(ROAD_HALF + 3.0)).difference(YJ_DRIVE.buffer(3.6))
# East of the east fork the game had a broad paved forecourt from 노천극장 to the fork (the plazas above: the 2015
# 경영관's).  The 1997 aerial photos have lawn and trees there, the car park before the north walls (YJ_LOT) and the
# drive to 노천극장 leaving the fork (YJ_BRANCH): lawn, then those two asphalt and a clump of trees (YJ_NEW_TREES)
_HG = LineString([(87.0, 165.7), (94.5, 174.7), (104.0, 186.3)])
YJ_EAST_LAWN = Polygon([(40, 150), (100, 140), (110, 185), (55, 195)]).buffer(2).intersection(
    Polygon(list(YJ_DRIVE.coords) + list(_HG.coords)[1:] + [(140, 186.3), (140, 110), (46.6, 110)])).difference(
    YJ_DRIVE.buffer(3.0)).difference(_HG.buffer(3.0))      # (up to the asphalt: no walk along it in the photos)
_xroads = [[list(q) for q in r_] for r_ in extra_roads]
_ypaths = []
for p_ in paths_out:
    if yj_gone(p_):
        continue
    ls_ = LineString(p_['pts']) if len(p_['pts']) > 1 else None
    _yw = YJ_GARDEN.union(YJ_EAST_LAWN) if p_['kind'] in ('footway', 'path', 'steps', 'pedestrian') else YJ_GARDEN
    if ls_ is None or p_['pts'] in _xroads or not ls_.intersects(_yw):
        _ypaths.append(p_)
        continue
    rest_ = ls_.difference(_yw)
    for g_ in (rest_.geoms if hasattr(rest_, 'geoms') else [rest_]):
        if g_.geom_type == 'LineString' and g_.length >= 3.0:
            _ypaths.append(dict(p_, pts=[[round(x, 1), round(y, 1)] for x, y in g_.coords]))
paths_out[:] = _ypaths + [dict(kind='footway', w=2.6, pts=[[round(x, 1), round(y, 1)] for x, y in YJ_WALK])]
out['paths'] = _ui_paths()                  # (out was made above, from the walks before this)
# 대우관 앞 · 상뜰 (DW_FRONT_ZONE, SANG_PAVE above): OSM's walks and drives there go the same way, and the photos' come
# in: the terrace's drive, the 상뜰's walks, its flight
_fz_walk = unary_union([DW_FRONT_ZONE, DW_FRONT_PAV, SANG_ZONE])
_fpaths = []
for p_ in paths_out:
    ls_ = LineString(p_['pts']) if len(p_['pts']) > 1 else None
    z_ = _fz_walk if p_['kind'] in ('footway', 'path', 'steps', 'pedestrian') else DW_FRONT_ZONE
    if ls_ is None or not ls_.intersects(z_):
        _fpaths.append(p_)
        continue
    rest_ = ls_.difference(z_)
    for g_ in (rest_.geoms if hasattr(rest_, 'geoms') else [rest_]):
        if g_.geom_type == 'LineString' and g_.length >= 3.0:
            _fpaths.append(dict(p_, pts=[[round(x, 1), round(y, 1)] for x, y in g_.coords]))
_rp = lambda l_: [[round(x, 1), round(y, 1)] for x, y in l_]
paths_out[:] = _fpaths + [dict(kind='service', w=7.9, pts=_rp(LineString(DW_TERR_DRIVE.exterior.coords[:2]).parallel_offset(
    (DAEWOO['drive'][1] - DAEWOO['drive'][0]) / 2, 'left').coords))] + \
    [dict(kind='footway', w=w_, pts=_rp(l_)) for l_, w_ in SANG_WALKS.values()] + \
    [dict(kind='steps', w=5.5, pts=_rp([SANG_DIAMOND[2], SANG_FOOT]))]
print('대우관 앞 · 상뜰: walks', len(paths_out), 'of them cut or gone', len(_ypaths) + 1 - len(_fpaths))
out['paths'] = _ui_paths()
_kept = unary_union([LineString(p_['pts']).buffer(p_['w'] / 2) for p_ in paths_out
                     if len(p_['pts']) > 1 and LineString(p_['pts']).distance(YJ_GARDEN) < 10.0])
_yclear = YJ_PAD.union(unary_union([Polygon(b_['footprint']).buffer(4.0) for b_ in YONGJAE_SCATTER])).difference(YJ_DRIVE.buffer(3.6))
_ydz = _yclear.union(YJ_GARDEN)
out['decals'] = [d_ for d_ in out['decals'] if not _ydz.contains(Point(d_[1], d_[2]))]
# (대우관 앞 · 상뜰: what the random planting and the first layout left on the hall as the photos have it, on the terrace
# and its podium and on the 상뜰's walks goes; a tree as those under the moved 백양로 do, the last one taking its place)
_fzt = unary_union([_dwp.buffer(1.2), DW_TERR, DW_TERR_DRIVE,
                    _uvh([(DW_UC - _pd['hw'] - 0.5, _pd['end']), (DW_UC + _pd['hw'] + 0.5, _pd['end']),
                          (DW_UC + _pd['hw'] + 0.5, _tv0), (DW_UC - _pd['hw'] - 0.5, _tv0)]),
                    SANG_PAVE.difference(Point(*SANG).buffer(SANG_LAWN)).buffer(0.5)])
_n0 = (len(DROP_TREES), len(shrubs), len(props), len(out['decals']))
for t_ in trees:
    if _fzt.contains(Point(t_[1], t_[2])):
        drop_tree(t_)
        print('   대우관 앞: tree in the way', t_[:3])
shrubs = [s_ for s_ in shrubs if not _fzt.contains(Point(s_[1], s_[2]))]
props = [p_ for p_ in props if not _fzt.contains(Point(p_[1], p_[2]))]
out['decals'] = [d_ for d_ in out['decals'] if not _fzt.union(DW_FRONT_ZONE).union(SANG_ZONE).contains(Point(d_[1], d_[2]))]
print('대우관 앞 · 상뜰: trees dropped, shrubs, props, decals gone', len(DROP_TREES) - _n0[0], _n0[1] - len(shrubs), _n0[2] - len(props),
      _n0[3] - len(out['decals']))
# the planting (reference/용재관.jpg, April): the bank one sheet of violet 진달래, in flower before their leaves, either
# side of the walk; a clipped hedge along the walk's west side, a few red 영산홍 at the foot of the bank, a double-
# globe lamp at the head of the flight by the canopy, a cherry in flower on the bank by the foot of the walk; a tall
# 전나무 beyond the statue by the garden's south hedge (the right of the photo, its trunk 3.9 deg right of the camera's
# axis, its foot ~97 m from the lens behind the hedge; on that line where it passes the tall conifer of the 2010
# roadview, 3.5 m off the two garden panoramas' crossing: reference/고증.md 4.2.1).  The scattered planting there goes
# first.
YJ_BANK = YJ_PAD.buffer(12.0).difference(YJ_PAD.buffer(0.5)).intersection(yongjae_poly(-30.0, 4.0, -16.0, 50.0))
YJ_BANK = YJ_BANK.difference(bline.buffer(ROAD_HALF + 3.0)).union(YJ_GARDEN.difference(YJ_PAD.buffer(0.5)))
YJ_BANK = YJ_BANK.intersection(_SE_FORK).difference(YJ_LOT.buffer(1.5))
_yjz = YJ_PAD.buffer(1.0).union(YJ_BANK)
# (the trees go as the list was first cleared, round the hall as first put: those the hall's place brings in, at the
# end)
YJ_BANK_RNG = YJ_PAD_RNG.buffer(12.0).difference(YJ_PAD_RNG.buffer(0.5)).intersection(
    unary_union([yongjae_poly(-30.0, 4.0, -16.0, 62.0, YONGJAE_RNG), yongjae_poly(-30.0, 22.0, 41.0, 62.0, YONGJAE_RNG)]))
YJ_BANK_RNG = YJ_BANK_RNG.difference(bline.buffer(ROAD_HALF + 3.0)).union(_YG_RNG.difference(YJ_PAD_RNG.buffer(0.5)))
YJ_BANK_RNG = YJ_BANK_RNG.intersection(_SE_FORK)
_n0 = (len(trees), len(shrubs), len(props), len(cars))
_yzr = YJ_PAD_RNG.buffer(1.0).union(YJ_BANK_RNG)
trees[:] = [t_ for t_ in trees if not _yzr.contains(Point(*rxy(t_)))]
# (those the hall's new place stands on are moved, in their places in the list, to the clump north of it: below)
_YJ_MOVED = [t_ for t_ in trees if _yjz.contains(Point(t_[1], t_[2]))]
shrubs = [s for s in shrubs if not _yjz.contains(Point(s[1], s[2]))]
props = [p for p in props if not _yjz.contains(Point(p[1], p[2])) or _uw_kept(p)]   # (the row at the steps' head)
cars = [c for c in cars if not _yjz.contains(Point(c[1], c[2]))]
_ybank = YJ_BANK.difference(_kept.buffer(0.7)).difference(LineString(YJ_WALK).buffer(2.0))
rng11 = random.Random(1997 + 4)
_yb0, _yb1 = _ybank.bounds[:2], _ybank.bounds[2:]
_yjp = []
for _k in range(24000):
    x_, y_ = rng11.uniform(_yb0[0], _yb1[0]), rng11.uniform(_yb0[1], _yb1[1])
    if not _ybank.contains(Point(x_, y_)) or any((x_ - a_) ** 2 + (y_ - b_) ** 2 < 1.3 ** 2 for a_, b_ in _yjp[-500:]):
        continue
    _yjp.append((x_, y_))
    foot_ = YJ_PAD.distance(Point(x_, y_)) > 9.5
    kind_ = 'azalea_red' if foot_ and rng11.random() < 0.3 else 'azalea_violet'
    shrubs.append([kind_, round(x_, 2), round(y_, 2), round(rng11.uniform(1.0, 1.45), 2), round(rng11.uniform(0, 6.28), 2)])
_wl = LineString(YJ_WALK[1:3])
for f_ in np.arange(0.06, 0.95, 1.6 / _wl.length):                 # the hedge along the walk's west side
    a_, b_ = _wl.interpolate(f_, normalized=True), _wl.interpolate(min(1.0, f_ + 0.01), normalized=True)
    ang_ = math.atan2(b_.y - a_.y, b_.x - a_.x)
    shrubs.append(['hedge_low', round(a_.x - math.sin(ang_) * 2.0, 2), round(a_.y + math.cos(ang_) * 2.0, 2), 1.0,
                   round(ang_, 3)])
# (the cherry: the round crown 7 m across of the 2010 skyview, north-west of the east fork, where the 1997 aerial
# photos have a crown too; the bank's spot of before, south-east of the fork, is open ground in them)
for sp_, (x_, y_), sc_ in (('fir', (50.0, 167.5), 1.15), ('cherry', (50.5, 131.5), 1.05)):
    trees.append([sp_, round(x_, 2), round(y_, 2), sc_, round(rng11.uniform(0, 6.28), 2)])
# (the 은백양 by the foot of the steps, tall in the 2003 photos, stands at the foot of 백양로's end steps (UW_STEPS),
# left of the tower in this view: the big bare tree on the photo's left edge, full grown)
_lx, _ly = yj_xy(-3.9, 20.4)
props.append(['lamp_double', round(_lx, 2), round(_ly, 2), round(YONGJAE['ang'], 3)])
# the car park before the north walls (YJ_LOT): a row nose in to the walls and two by the drive to 노천극장, about as
# many as the 1997 aerial photos show
_rc = random.Random(1997 + 160)
_hd = YONGJAE['ang'] - math.pi / 2                                 # facing the walls (-v)
for u_ in (4.0, 6.6, 11.8, 24.5, 27.1, 32.3, 34.9):
    if _rc.random() < 0.85:
        x_, y_ = yj_xy(u_, 46.5)
        cars.append([_rc.choice(['sedan', 'sedan', 'sedan', 'hatch']), round(x_, 2), round(y_, 2),
                     round(_hd + _rc.uniform(-.05, .05), 3), _rc.randrange(8)])
for x_, y_, h_ in ((91.6, 151.0, 0.82), (94.0, 153.4, 0.82)):
    cars.append([_rc.choice(['sedan', 'hatch']), x_, y_, round(h_ + _rc.uniform(-.05, .05), 3), _rc.randrange(8)])
# the clump of trees between the car park and the drive to 노천극장 and the wood north of that drive, as in the 1997
# aerial photos (on the forecourt's paving in the game before): at the list's end, so that no other tree changes its
# model
_tz = unary_union([Polygon([(99.5, 147.0), (106.5, 145.0), (118.5, 142.0), (119.0, 150.0), (114.0, 152.0), (100.5, 153.5)]),
                   Polygon([(91.0, 165.5), (99.0, 162.5), (110.0, 161.0), (116.0, 160.0), (112.0, 170.0), (106.0, 178.0),
                            (100.0, 176.5)]).difference(_HG.buffer(6.0))])
_tpts = [(t_[1], t_[2]) for t_ in trees if abs(t_[1] - 105) < 30 and abs(t_[2] - 160) < 30]
YJ_NEW_TREES = []
_rt = random.Random(1997 + 161)
for _k in range(400):
    x_, y_ = _rt.uniform(88, 122), _rt.uniform(140, 180)
    if not _tz.contains(Point(x_, y_)) or any((x_ - a_) ** 2 + (y_ - b_) ** 2 < 6.0 ** 2 for a_, b_ in _tpts):
        continue
    _tpts.append((x_, y_))
    YJ_NEW_TREES.append([_rt.choice(['zelkova', 'oak', 'oak', 'pine']), round(x_, 2), round(y_, 2),
                         round(_rt.uniform(0.9, 1.15), 2), round(_rt.uniform(0, 6.28), 2)])
for t_, q_ in zip(_YJ_MOVED, YJ_NEW_TREES):
    if len(t_) < 6:
        t_.append((t_[1], t_[2]))      # (later clearings ask where it first stood: rxy)
    t_[1], t_[2] = q_[1], q_[2]
YJ_NEW_TREES = YJ_NEW_TREES[len(_YJ_MOVED):]
print('yongjae: trees moved to the clump', len(_YJ_MOVED), 'new', len(YJ_NEW_TREES))
print('yongjae: cleared (trees, shrubs, props, cars)', _n0[0] - len(trees) + 2, _n0[1] - len(shrubs),
      _n0[2] - len(props) + 1, _n0[3] - len(cars), '- 진달래동산', len(_yjp))
# the 1997 sites (GONE_1997, LATE_FOOTPRINT_1997): off the bare site and its ring of shrubs, off the walls put back,
# off 공학원's building site and the pavement decals there
# (공학원's site as the 1997 photos have it, with its car park, yard and offices: GW_CLEAR; not the part of the car
# park that photo A's apron already was, where its booth and planters stand)
GW_CLEAR = unary_union([GW_LOT.difference(GATE_APRON.buffer(1.0)), GW_ROW, GW_YARD] + [p_.buffer(1.0) for p_ in GW_SHED_POLYS])
_gz = unary_union([p_.buffer(6.0) for _, p_ in GONE_SITES] + [p_.buffer(2.0) for p_ in LATE_SITES] +
                  [GONGWON_SITE.buffer(1.5), GW_CLEAR])
_gwd = GONGWON_SITE.buffer(1.0).union(GW_YARD)
out['decals'] = [d_ for d_ in out['decals'] if not _gwd.contains(Point(d_[1], d_[2]))]
# (the halls left out or put back since the planting was laid, GONE_NEW · SITES_NEW_1997: off the list as first
# cleared)
_gone_new = [Polygon(g_['footprint']) for g_ in RND_GHOSTS if g_['id'] in GONE_NEW]
_gone_lawn = [Polygon(g_['footprint']) for g_ in RND_GHOSTS if g_['id'] in GONE_LAWN]
_gz_rng = unary_union([p_.buffer(6.0) for _, p_ in GONE_SITES if not any(p_.equals(q_) for q_ in _gone_new)] +
                      [Polygon(ENG_FP_RNG).buffer(2.0)] +
                      [p_.buffer(2.0) for p_ in LATE_SITES_RNG if not p_.intersects(Polygon(ENG_FP_RNG).buffer(-1.0))] + [GONGWON_SITE_RNG.buffer(1.5)])
# the trees that stand in what the site has gained keep their places in the list (the web picks each tree's model by
# it) and go to the lawn between the car park and 백양로, a dense clump in the 1997 photos
# (north of the gate wall's paved strip)
_gw_spots = [site_xy(u_, v_) for u_, v_ in ((93.0, 40.0), (99.5, 43.5), (94.0, 48.0), (99.0, 52.5), (95.0, 57.0), (99.5, 61.5),
                                            (94.5, 66.0), (99.0, 70.5), (95.5, 75.0), (91.5, 53.0), (91.5, 62.0), (91.5, 71.0))]
_gw_moved = []
_gw_new = GONGWON_SITE.buffer(1.5).union(GW_CLEAR)
for t_ in trees:
    if not _gw_new.contains(Point(t_[1], t_[2])) or _gz_rng.contains(Point(*rxy(t_))):
        continue
    q_ = next((q_ for q_ in _gw_spots if min(math.hypot(o_[1] - q_[0], o_[2] - q_[1]) for o_ in trees) > 4.5), None)
    if q_ is None:
        continue                                  # (no room left: cleared below, the list's last tree in its place)
    _gw_moved.append((t_[0], t_[1], t_[2]))
    if len(t_) < 6:
        t_.append((t_[1], t_[2]))      # (later clearings ask where it first stood: rxy)
    t_[1], t_[2] = round(q_[0], 2), round(q_[1], 2)
print('공학원 site: trees moved to the lawn by the car park', _gw_moved)
_n0 = (len(trees), len(shrubs), len(props), len(cars))
# (의료원: the trees left standing where the halls of the 1997 aerial photos are move, each in its place in the list,
# to the nearest free spot on the lawns of the two gardens south and east of 제중관, by 외래진료소's front and between
# the two towers, so that the list keeps its length: no tree after them changes its model)
MED_TREE_SPOTS = [(130.0, -297.0), (117.0, -284.0), (102.0, -291.0), (160.0, -265.0), (146.0, -250.0), (166.0, -236.0),
                  (44.45, -334.76), (10.0, -320.0), (145.46, -157.15)]
_mz = unary_union([Polygon(b_['footprint']).buffer(2.0) for b_ in buildings if b_['id'] in MED_SITES_RNG])
_mzr = unary_union([p_.buffer(6.0) for _, p_ in GONE_SITES] + [p_.buffer(2.0) for p_ in LATE_SITES_RNG])
_msp = list(MED_TREE_SPOTS)
_mn = 0
for t_ in trees:
    if _msp and _mz.contains(Point(t_[1], t_[2])) and not _mzr.contains(Point(*rxy(t_))):
        q_ = min(_msp, key=lambda q_: math.hypot(q_[0] - t_[1], q_[1] - t_[2]))
        _msp.remove(q_)
        if len(t_) < 6:
            t_.append((t_[1], t_[2]))      # (later clearings ask where it first stood: rxy)
        t_[1], t_[2] = q_
        _mn += 1
print('의료원: trees moved off the 1997 halls', _mn, '- spots left', len(_msp))
# (the trees go as first cleared, with 제1공학관 as first put back: ENG_FP_RNG)
# (과학관 · 연구관 · 장기원 기념관 · 어린이생활지도연구원: the trees left standing where the outlines put back since
# are (SITES_NEW_1997) step aside, each in its place in the list, 3.5 m off the walls)
_gzn = unary_union([Polygon(b_['footprint']).buffer(2.0) for b_ in buildings
                    if b_['id'] in SITES_NEW_1997])
_gzo = unary_union([g_.buffer(1.5).exterior for g_ in (_gzn.geoms if hasattr(_gzn, 'geoms') else [_gzn])])
_n_aside = 0
for t_ in trees:
    if _gzn.contains(Point(t_[1], t_[2])) and not _gz_rng.contains(Point(*rxy(t_))):
        q_ = shapely.ops.nearest_points(_gzo, Point(t_[1], t_[2]))[0]
        if len(t_) < 6:
            t_.append((t_[1], t_[2]))
        t_[1], t_[2] = round(q_.x, 2), round(q_.y, 2)
        _n_aside += 1
# (the site of the hall left out since, GONE_NEW, keeps its trees: those on the halls of 1997 there have stepped aside)
clear_trees(_gz.difference(unary_union([q_.buffer(6.0) for q_ in _gone_new])), _gz_rng)
shrubs = [s for s in shrubs if not _gz.contains(Point(s[1], s[2]))]
props = [p for p in props if not _gz.contains(Point(p[1], p[2]))]
cars = [c for c in cars if not _gz.contains(Point(c[1], c[2]))]
print('1997 sites: cleared (trees, shrubs, props, cars)', _n0[0] - len(trees), _n0[1] - len(shrubs), _n0[2] - len(props),
      _n0[3] - len(cars), '- trees stepped aside', _n_aside)
# 과학관 (SCI; the 1997-07-28 aerial photos, reference/고증/3.10): the courtyard a paved court (a chequered paving in the
# photos), no tree on it; four clipped hedges in kerbed beds in its north half; cars nose to tail in two rows round
# its south-east corner and along its south side.  The yard north-west of the link asphalt, a few cars by the fan-
# shaped hall.  (The trees the planting put there go as those under the moved 백양로 do; the junipers by the flight
# and the lamp stay.)
SCI_COURT = sci_poly([(-53.6, -5.8), (-4.0, -5.8), (-4.0, -44.5), (-45.5, -44.5), (-45.5, -25.6), (-53.6, -25.6)])
SCI_YARD = sci_poly([(-118.7, -25.6), (-121.0, -12.0), (-86.0, 15.5), (-72.4, 18.4), (-72.4, 0.3), (-67.7, 0.3), (-67.7, -25.6)])
_scz = unary_union([SCI_COURT.buffer(1.0), SCI_YARD.buffer(1.0)])
_n0 = (len(DROP_TREES), len(shrubs), len(props))
# (its trees go to the clump the photos have between the court's east end and the road, in their places in the list)
_spots = [sci_xy(u_, v_) for u_, v_ in ((1.5, -24.0), (2.0, -31.0), (0.5, -38.0), (4.0, -43.0))]
for t_ in trees:
    if _scz.contains(Point(t_[1], t_[2])):
        if not _spots:
            drop_tree(t_)
            continue
        if len(t_) < 6:
            t_.append((t_[1], t_[2]))
        t_[1], t_[2] = _spots.pop(0)
shrubs = [s_ for s_ in shrubs if not _scz.contains(Point(s_[1], s_[2])) or s_[0].startswith('topiary')]
props = [p_ for p_ in props if not _scz.contains(Point(p_[1], p_[2])) or p_[0] == 'lamp5']
for u0_, u1_, v_ in ((-36.0, -31.0, -11.0), (-28.0, -23.0, -11.0), (-14.0, -6.0, -11.0), (-36.0, -22.0, -19.5)):
    hedge_line([sci_xy(u0_, v_), sci_xy(u1_, v_)], 'hedge_low', 1.1, step=1.4, closed=False)
hedge_line([sci_xy(-121.0, -10.6), sci_xy(-87.0, 16.2)], 'hedge_low', 1.2, step=1.4, closed=False)   # (the yard's north-west edge)
_rs = random.Random(1997 + 163)
SCI_CARS = []          # (at the end of the cars' list, so that no other car changes its model)
for row_ in ([(-8.5, -19.0), (-9.5, -25.0), (-12.5, -31.0), (-17.5, -36.5), (-24.0, -40.0), (-37.0, -41.0)],
             [(-13.5, -19.5), (-14.5, -25.0), (-17.0, -29.5), (-21.0, -33.0), (-26.0, -35.5), (-37.0, -36.5)]):
    _rl = LineString([sci_xy(u_, v_) for u_, v_ in row_])
    for d_ in np.arange(1.3, _rl.length - 1.0, 2.6):
        q_, q2_ = _rl.interpolate(d_), _rl.interpolate(d_ + 0.5)
        if _rs.random() < 0.85:
            SCI_CARS.append([_rs.choice(['sedan', 'sedan', 'sedan', 'hatch']), round(q_.x, 2), round(q_.y, 2),
                             round(math.atan2(q2_.y - q_.y, q2_.x - q_.x) + math.pi / 2 + _rs.uniform(-.05, .05), 3), _rs.randrange(8)])
for u_, v_ in ((-102.0, -9.5), (-102.0, -12.1), (-102.0, -14.7), (-102.0, -17.3), (-108.5, -16.0), (-111.0, -16.0)):
    if _rs.random() < 0.85:
        x_, y_ = sci_xy(u_, v_)
        SCI_CARS.append([_rs.choice(['sedan', 'sedan', 'hatch']), x_, y_,
                         round(_sa + (0.0 if u_ > -105 else math.pi / 2) + _rs.uniform(-.05, .05), 3), _rs.randrange(8)])
print('과학관: off the court and the yard (trees, shrubs, props)', len(DROP_TREES) - _n0[0], _n0[1] - len(shrubs), _n0[2] - len(props))
# 대운동장 (FIELD): the 1997 photos have the oval bare from edge to edge, and the random planting had put trees on its
# east end (they go to the woods round it, below); and what stood round the two outlines left out at its north end
# (FIELD_GONE)
_fdz = unary_union([FIELD_POLY.buffer(-0.5)] + [p_.buffer(5.5) for p_ in FIELD_GONE_SITES])
_n0 = (len(shrubs), len(props), len(out['decals']))
_f_moved = [t_ for t_ in trees if _fdz.contains(Point(t_[1], t_[2]))]
shrubs = [s for s in shrubs if not _fdz.contains(Point(s[1], s[2]))]
props = [p for p in props if not _fdz.contains(Point(p[1], p[2]))]
out['decals'] = [d_ for d_ in out['decals'] if not _fdz.contains(Point(d_[1], d_[2]))]
# The woods round it (the same photos: tree crowns edge to edge along the hillside north-west and north of the oval,
# a band between it and the 야구장 (here one row, between the walk and the road OSM has there now), a band between it
# and 성산로; the bank towards the road past its east end keeps what the planting gave it).  Not tree by tree: rows
# 6.5 m apart along the oval's edge, so many deep by the side.  Their own random numbers; the trees taken off the
# oval go to the first of these places (in place: the list keeps its length and order), the rest at the list's end.
_frnd = random.Random(1997 + 161)
_fex = shapely.geometry.polygon.orient(FIELD_POLY, 1.0).exterior
_f_keep = unary_union([LineString(p_['pts']).buffer(p_['w'] / 2 + 1.5) for p_ in paths_out
                       if len(p_['pts']) > 1 and LineString(p_['pts']).distance(FIELD_POLY) < 40.0]
                      + [FIELD_PAD, FIELD_POLY.buffer(2.5)])
_f_old = [(t_[1], t_[2]) for t_ in trees if FIELD_PATCH.buffer(6.0).contains(Point(t_[1], t_[2])) and not any(t_ is q_ for q_ in _f_moved)]
FIELD_NEW_TREES = []
for d_ in np.arange(0.0, _fex.length, 6.5):
    p_, q_ = _fex.interpolate(d_), _fex.interpolate(d_ + 1.0)
    tx_, ty_ = q_.x - p_.x, q_.y - p_.y
    nx_, ny_ = ty_, -tx_                               # (out of the oval)
    if nx_ < -0.2 and ny_ > 0.2:                       # the hillside north-west
        rows_, kinds_ = (4.0, 10.5, 17.0, 23.0), ('oak', 'oak', 'pine', 'zelkova')
    elif ny_ >= 0.2 and nx_ <= 0.5:                    # the north end (the way up out of it at x -365 left open)
        rows_, kinds_ = (() if -374.0 < p_.x < -356.0 else (4.0, 11.0, 18.0)), ('oak', 'pine', 'zelkova')
    elif nx_ > 0.2 and ny_ < -0.2:                     # towards the 야구장
        rows_, kinds_ = (8.6,), ('zelkova', 'oak', 'oak')
    elif ny_ <= -0.2:                                  # towards 성산로
        rows_, kinds_ = (3.5,), ('oak', 'pine')
    elif nx_ <= -0.8:                                  # the west end, beside 학군단
        rows_, kinds_ = (4.0, 10.0), ('oak', 'pine')
    else:
        rows_, kinds_ = (), ()
    for r_ in rows_:
        o_, a_ = r_ + _frnd.uniform(-1.5, 1.5) * (0.5 if len(rows_) == 1 else 1.0), _frnd.uniform(-2.0, 2.0)
        x_, y_ = p_.x + nx_ * o_ + tx_ * a_, p_.y + ny_ * o_ + ty_ * a_
        t_ = [_frnd.choice(kinds_), round(x_, 2), round(y_, 2), round(_frnd.uniform(0.85, 1.25), 2), round(_frnd.uniform(0, 6.28), 2)]
        if FIELD_PATCH.contains(Point(x_, y_)) and not _f_keep.contains(Point(x_, y_)) \
                and all(math.hypot(x_ - u_, y_ - v_) > 3.5 for u_, v_ in _f_old + [(q_[1], q_[2]) for q_ in FIELD_NEW_TREES]):
            FIELD_NEW_TREES.append(t_)
_n_new = len(FIELD_NEW_TREES)
for t_ in _f_moved:
    t_[:] = FIELD_NEW_TREES.pop(0)
print('대운동장: off the oval and the two sites (trees moved to the woods round it, shrubs, props, decals)', len(_f_moved),
      _n0[0] - len(shrubs), _n0[1] - len(props), _n0[2] - len(out['decals']), '- woods', _n_new)
# 연합신학대학원 (UTS): the ring of bushes round OSM's outline and the stains on its apron go; the walk from the road
# east of it runs on to the 1997 hall's door; the ground OSM's outline and its apron leave is lawn again (UTS_LAWN,
# painted below) with trees as on the hill round it (the aerial photos: crowns up to the hall's north and west walls,
# open ground south of it and along its east wall), at the list's end
_n0 = (len(shrubs), len(out['decals']))
shrubs = [s for s in shrubs if not (s[0] == 'bush' and abs(UTS_OSM.exterior.distance(Point(s[1], s[2])) - 5.5) < 0.2
                                    and not UTS_OSM.contains(Point(s[1], s[2])))]
out['decals'] = [d_ for d_ in out['decals'] if not UTS_OSM.buffer(4.0).contains(Point(d_[1], d_[2]))]
UTS_WALK = _uw0 = None
for p_ in paths_out:
    if len(p_['pts']) == 2 and p_['kind'] == 'footway' and UTS_OSM.buffer(1.0).contains(Point(p_['pts'][0])) \
            and not UTS_OSM.buffer(1.0).contains(Point(p_['pts'][1])) and Point(p_['pts'][0]).distance(Point(UTS_DOOR)) < 12.0:
        _uw0 = LineString(p_['pts']).buffer(p_['w'] / 2 + 0.4)       # (the walk as OSM has it, to the later hall's door)
        p_['pts'][0] = [round(float(UTS_DOOR[0] + _ut[0] * 1.2), 1), round(float(UTS_DOOR[1] + _ut[1] * 1.2), 1)]
        UTS_WALK = [tuple(q_) for q_ in p_['pts']]
out['paths'] = _ui_paths()
_uk = unary_union([LineString(p_['pts']).buffer(p_['w'] / 2 + 0.4) for p_ in paths_out
                   if len(p_['pts']) > 1 and LineString(p_['pts']).distance(UTS_OSM) < 10.0])
UTS_LAWN = unary_union([UTS_OSM.buffer(3.6, join_style=2)] + ([_uw0] if _uw0 is not None else [])).difference(_uk)
_uzt = UTS_OSM.buffer(1.5).difference(UTS_FP.buffer(5.0)).difference(_uk.buffer(2.5))
_tpts = [(t_[1], t_[2]) for t_ in trees if UTS_OSM.buffer(18.0).contains(Point(t_[1], t_[2]))]
UTS_NEW_TREES = []
_rt = random.Random(1997 + 1964)
_ub = _uzt.bounds
for _k in range(600):
    x_, y_ = _rt.uniform(_ub[0], _ub[2]), _rt.uniform(_ub[1], _ub[3])
    if not _uzt.contains(Point(x_, y_)) or any((x_ - a_) ** 2 + (y_ - b_) ** 2 < 5.5 ** 2 for a_, b_ in _tpts):
        continue
    _tpts.append((x_, y_))
    UTS_NEW_TREES.append([_rt.choice(['zelkova', 'oak', 'oak', 'pine']), round(x_, 2), round(y_, 2),
                          round(_rt.uniform(0.9, 1.15), 2), round(_rt.uniform(0, 6.28), 2)])
print('연합신학대학원: bushes %d, decals %d gone; walk to the door %s; new trees %d' % (
    _n0[0] - len(shrubs), _n0[1] - len(out['decals']), UTS_WALK, len(UTS_NEW_TREES)))
# 대우관 뒤 (DAEWOO_BACK): nothing the random planting put down stays on the yard's asphalt and paving or in its walls'
# way (a tree goes as those under the moved 백양로 do: the last one takes its place in the list); then the yard's own:
# the hedge belt round the theatre, the planter round its west rim, the strip along the wall over the portal, the
# mound, the bank under the road to 북문 (rockery and shrubs in the 2010 street view)
_dz = unary_union([DWB_COURT_ASPH, DWB_LOT_ASPH, _uvp(DWB_FLOOR_UV), _uvp(DWB_AREA_UV)]).buffer(0.3)
_n0 = (len(DROP_TREES), len(shrubs), len(props))
_dw_moved = [t_ for t_ in trees if _dz.contains(Point(t_[1], t_[2]))]
shrubs = [s for s in shrubs if not _dz.contains(Point(s[1], s[2]))]
props = [p for p in props if not _dz.contains(Point(p[1], p[2]))]
_rd = random.Random(1997 + 158)
_ds = lambda kind_, u_, v_, sc_: shrubs.append([kind_, *(round(c_, 2) for c_ in dw_xy(u_, v_)), round(sc_, 2), round(_rd.uniform(0, 6.28), 2)])
for r_, a0_, a1_, st_ in ((16.1, 16.0, 94.0, 1.7), (17.6, 18.0, 92.0, 1.9), (16.0, 129.0, 186.0, 2.0)):
    for u_, v_ in dwb_arc(r_, a0_, a1_, step_=math.degrees(st_ / r_)):
        _ds(_rd.choice(['bush', 'bush', 'topiary_round']), u_ + _rd.uniform(-0.3, 0.3), v_ + _rd.uniform(-0.3, 0.3), _rd.uniform(0.9, 1.25))
for u_, v_ in [(25.5, 50.0), (25.5, 52.4), (25.5, 54.8), (25.5, 57.2), (25.5, 59.5), (26.5, 63.0), (30.6, 63.2), (35.0, 63.0), (30.8, 66.0),
               (38.3, 59.8), (38.2, 64.5), (21.5, 64.2), (26.0, 69.5), (38.5, 76.8), (43.6, 72.6), (20.0, 63.4)]:
    _ds(_rd.choice(['bush', 'topiary_round']), u_, v_, _rd.uniform(0.8, 1.15))
for k_ in range(14):                                               # (the bank under the road to 북문)
    _ds('bush', _rd.uniform(62.3, 65.5), 37.0 + k_ * 2.3 + _rd.uniform(-0.6, 0.6), _rd.uniform(0.9, 1.4))
for u_, v_ in [(50.5, 76.5), (55.5, 73.0), (58.5, 71.0)]:           # (the island east of the mouth)
    _ds('topiary_round', u_, v_, _rd.uniform(0.9, 1.2))
# (new trees, at the list's end below: the young trees of the hedge belt, the one in the square planter at the head
# of the flight and the one in the corner behind the west wing, two small pines on the island east of the mouth)
DW_NEW_TREES = [[k_, *(round(c_, 2) for c_ in dw_xy(u_, v_)), sc_, round(_rd.uniform(0, 6.28), 2)] for k_, u_, v_, sc_ in (
    ('maple', 34.9, 44.3, 0.45), ('zelkova', 39.9, 37.0, 0.5), ('maple', 29.5, 46.8, 0.42), ('zelkova', 19.9, 40.8, 0.45),
    ('zelkova', 3.6, 24.4, 0.55), ('pine', 51.5, 78.6, 0.4), ('pine', 56.8, 72.2, 0.38))]
for t_ in _dw_moved:                                # (in place: the list keeps its length and order)
    if DW_NEW_TREES:
        t_[:5] = DW_NEW_TREES.pop(4 if len(DW_NEW_TREES) > 4 else 0)
    else:
        drop_tree(t_)
print('대우관 뒤: off the yard (trees moved to the yard\'s own places, dropped, shrubs, props)', len(_dw_moved), len(DROP_TREES) - _n0[0],
      _n0[1] - len(shrubs), _n0[2] - len(props))
# 대강당 앞 둑 (AUD_BANK): the strip's clipped hedge goes where the bank rises behind the wall (the ginkgo row stays, on
# the bank as in the roadview); the bank is thick with shrubs (bare and brown in April 2011, green with yellow flowers
# at its foot in August 2008) under a clipped hedge along its top.  Its own random numbers.
AUD_BANK_POLY = Polygon([along_raw(s_, AUD_BANK['side'] * (E_WALK - 0.1))[:2] for s_ in np.arange(AUD_BANK['s0'], AUD_BANK['s1'] + 0.1, 2.0)] +
                        [along_raw(s_, AUD_BANK['side'] * (E_WALK + aud_bank_top(s_) + 0.1))[:2]
                         for s_ in np.arange(AUD_BANK['s1'], AUD_BANK['s0'] - 0.1, -0.5)])
_n0 = len(shrubs)
_hp = Polygon([along_raw(s_, AUD_BANK['side'] * (E_WALK - 0.1))[:2] for s_ in np.arange(AUD_BANK['s0'] - 3.2, AUD_BANK['s1'] + 3.3, 2.0)] +
               [along_raw(s_, AUD_BANK['side'] * (E_WALK + AUD_BANK['top'] + 0.1))[:2]
                for s_ in np.arange(AUD_BANK['s1'] + 3.2, AUD_BANK['s0'] - 3.3, -2.0)])     # (and its ends' 3 m toes)
shrubs = [s for s in shrubs if not (s[0] == 'hedge_low' and _hp.contains(Point(s[1], s[2])))]
_n0 -= len(shrubs)
# the flight (AUD_FLIGHT) and a metre round it: no tree, shrub, prop or car (the ginkgo row stands either side of it)
_fo = np.array(along_raw(AUD_FLIGHT['s'], -E_WALK)[:2])
_fv, _fu = np.array(AUD_FLIGHT['axis']), _afv
_fh = AUD_FLIGHT['w'] / 2 + AUD_FLIGHT['cheek']
AUD_FLIGHT_POLY = Polygon([tuple(_fo + _fu * u_ + _fv * v_) for u_, v_ in ((-_fh, 0.0), (_fh, 0.0), (_fh, AUD_FLIGHT['run'] + 0.6),
                                                                          (-_fh, AUD_FLIGHT['run'] + 0.6))])
_fz = AUD_FLIGHT_POLY.buffer(1.0)
_nf = (len(trees), len(shrubs), len(props), len(cars))
clear_trees(_fz, old=lambda x_, y_: _fz.contains(Point(*to_new(x_, y_))))
shrubs = [s for s in shrubs if not _fz.contains(Point(s[1], s[2]))]
props = [p for p in props if not _fz.contains(Point(p[1], p[2]))]
cars = [c for c in cars if not _fz.contains(Point(c[1], c[2]))]
print('대강당 앞 돌계단: cleared (trees, shrubs, props, cars)', _nf[0] - len(trees), _nf[1] - len(shrubs), _nf[2] - len(props),
      _nf[3] - len(cars))
# the court on the terrace and the drive up to it, and its mouth before the bollards: no tree, shrub, prop or car
# (laid after the planting)
_cz = unary_union([court_poly(2.0), AUD_RAMP_CW.buffer(0.5), AUD_RAMP_WALK.buffer(0.5), AUD_RAMP_BAND,
                   ramp_strip(-AUD_RAMP['w'] / 2 - 1.0, AUD_RAMP['w'] / 2 + AUD_RAMP['walk'], -AUD_RAMP['mouth'] - 3.0, 0.0)])
# (the list is cleared by the drive where it first lay, AUD_RAMP_MOVE: what the moved one runs over goes at the end)
_cz_rng = unary_union([court_poly(2.0)] + [shapely.affinity.translate(g_, -AUD_RAMP_MOVE[0], -AUD_RAMP_MOVE[1]) for g_ in (
    AUD_RAMP_CW.buffer(0.5), AUD_RAMP_WALK.buffer(0.5), AUD_RAMP_BAND,
    ramp_strip(-AUD_RAMP['w'] / 2 - 1.0, AUD_RAMP['w'] / 2 + AUD_RAMP['walk'], -AUD_RAMP['mouth'] - 3.0, 0.0))])
_cz, _cz_rng = _cz.difference(bline.buffer(E_WALK + 0.3)), _cz_rng.difference(BLINE_RNG.buffer(E_WALK + 0.3))
_nf = (len(trees), len(shrubs), len(props), len(cars))
clear_trees(_cz, _cz_rng)
shrubs = [s for s in shrubs if not _cz.contains(Point(s[1], s[2]))]
props = [p for p in props if not _cz.contains(Point(p[1], p[2]))]
cars = [c for c in cars if not _cz.contains(Point(c[1], c[2]))]
print('대강당 앞 코트 · 진입로: cleared (trees, shrubs, props, cars)', _nf[0] - len(trees), _nf[1] - len(shrubs),
      _nf[2] - len(props), _nf[3] - len(cars))
# the trees round the drive (reference/고증.md 4.5): Kakao roadview April 2011 1017220190 - 195, each trunk from
# three to five panos (their poses solved from 대강당's front and the wall's south end).  The ginkgo row on the bank
# 1.2 m behind the wall every 6.2 m from the wedge's tip (the planting's row has 8.5 m); a pine on the wedge by the
# drive's west kerb, a pine and a zelkova in the strip of shrubs east of its walk, a pine and a zelkova in front of
# 학생회관 별관's west face (in round beds in the yard), another zelkova off its north-west corner.  (The weeping
# cherry the 2011 frames have on the terrace by the drive's head stands where the court was, and is left out.)
# 1997 sizes (4.5, #143): the ginkgos as the rest of 백양로's row (photo A, May 1997, matched the row at the model's
# height); the others 14 years younger than measured in April 2011 (tops over the panoramas' horizon at their solved
# distances): the zelkova north of the annex ~18.5 m then -> 15 m, the one at the drive's head ~11 m -> 7.5 m (young
# crown; the one by the annex's corner, hidden in theirs, as it), the pines 5.5 · 6 · 7.6 m -> three quarters
AUD_ROW_S = (438.4, 444.4, 450.5, 456.9, 463.2, 469.5, 475.7, 480.6)
AUD_TREES = [('pine', 12.4, 1.5, 0.38), ('pine', 18.2, -5.6, 0.41), ('zelkova_young', 21.1, -0.1, 0.83),
             ('pine', 27.3, -8.8, 0.52), ('zelkova_young', 28.7, -2.8, 0.83), ('zelkova', 35.1, 1.7, 1.15)]
# (the three by the drive, solved in the same panos as its foot, go with it: AUD_RAMP_MOVE; those before the annex's
# walls stay by the walls)
AUD_TREES[:3] = [(sp_, round(x_ + AUD_RAMP_MOVE[0], 2), round(y_ + AUD_RAMP_MOVE[1], 2), sc_) for sp_, x_, y_, sc_ in AUD_TREES[:3]]
AUD_TREE_BEDS = [Point(x_, y_).buffer(1.6) for _, x_, y_, _ in AUD_TREES[3:5]]
# (the planting's row trees there are moved in place, the rest added at the very end, after the town's: the game picks
# each tree's model in the list's order, web/src/world.js Forest, so the campus keeps its trees' looks)
_old = [i_ for i_, t_ in enumerate(trees) if t_[0] == 'ginkgo' and AUD_ROW_S[0] - 5.0 < s_off_rng(*rxy(t_))[0] < AUD_ROW_S[-1] + 4.0
        and abs(s_off_rng(*rxy(t_))[1] + E_WALK + 1.1) < 0.6]           # (as first found: their first places, BLINE_RNG)
_old.sort(key=lambda i_: s_off_rng(*rxy(trees[i_]))[0])
_rt = random.Random(139)
AUD_NEW_TREES = []
for _k, _s in enumerate(AUD_ROW_S):
    _x, _y, _ = along_raw(_s, AUD_BANK['side'] * (E_WALK + 1.2))
    _sc, _rot = round(_rt.uniform(0.86, 0.98), 2), round(_rt.uniform(0, 6.28), 2)
    if _k < len(_old):
        trees[_old[_k]][1:3] = [round(_x, 2), round(_y, 2)]
        trees[_old[_k]][5:] = [tuple(round(v_, 2) for v_ in along_rng(_s, AUD_BANK['side'] * (E_WALK + 1.2))[:2])]   # (rxy)
    else:
        AUD_NEW_TREES.append(['ginkgo', round(_x, 2), round(_y, 2), _sc, _rot])
for _sp, _x, _y, _sc in AUD_TREES:
    AUD_NEW_TREES.append([_sp, _x, _y, _sc, round(_rt.uniform(0, 6.28), 2)])
_nf = len(_old)
_tz = unary_union([Point(t_[1], t_[2]).buffer(1.2) for t_ in AUD_TREES])
shrubs = [s_ for s_ in shrubs if not _tz.contains(Point(s_[1], s_[2]))]
props = [p_ for p_ in props if not _tz.contains(Point(p_[1], p_[2]))]
cars = [c_ for c_ in cars if not _tz.contains(Point(c_[1], c_[2]))]
print('대강당 앞 진입로 나무: ginkgo row', _nf, '->', len(AUD_ROW_S), 'and', len(AUD_TREES), 'round the drive')
# the strip east of the walk: three staggered rows of clipped mounds grown into one mass (green in April 2011), down
# to the yard below the bollards; the bollards at the foot
_ob = AUD_RAMP['w'] / 2 + AUD_RAMP['walk']
for _t in np.arange(AUD_RAMP['band_t0'] + 0.6, AUD_RAMP['run'] - 1.4, 1.4):
    for _k, _o in enumerate((0.7, 1.95, 3.2)):
        _x, _y = ramp_xy(_t + 0.7 * (_k % 2) + _rt.uniform(-0.2, 0.2), _ob + _o + _rt.uniform(-0.15, 0.15))
        _sc, _rot = round(_rt.uniform(0.95, 1.3), 2), round(_rt.uniform(0, 6.28), 2)
        if _tz.buffer(0.3).contains(Point(_x, _y)):
            continue
        shrubs.append(['topiary_round', round(_x, 2), round(_y, 2), _sc, _rot])
for _o in AUD_RAMP['bollards']:
    P('bollard', *ramp_xy(0.0, _o), 0.0)
_rb = random.Random(84)
_gk = [Point(t[1], t[2]) for t in trees + AUD_NEW_TREES if AUD_BANK_POLY.buffer(1.0).contains(Point(t[1], t[2]))]
_nb0 = len(shrubs)
_in_flight = lambda s_, m_: AUD_BANK['gap'][0] - m_ < s_ < AUD_BANK['gap'][1] + m_
for _s in np.arange(AUD_BANK['s0'] + 1.0, AUD_BANK['s1'] - 0.5, 1.7):
    for _k, _o in enumerate((1.3, 2.9, 4.5)):
        _ss = _s + (0.85 if _k % 2 else 0.0) + _rb.uniform(-0.3, 0.3)
        _x, _y, _ = along_raw(_ss, AUD_BANK['side'] * (E_WALK + _o + _rb.uniform(-0.3, 0.3)))
        _sc, _rot = round(_rb.uniform(1.0, 1.45), 2), round(_rb.uniform(0, 6.28), 2)
        if any(g_.distance(Point(_x, _y)) < 1.1 for g_ in _gk) or _ss > AUD_BANK['s1'] - 0.6 or _in_flight(_ss, 0.9) \
                or aud_bank_top(_ss) < AUD_BANK['top']:
            continue                                                # (the wedge by the drive: below)
        shrubs.append(['bush', round(_x, 2), round(_y, 2), _sc, _rot])
# the wedge between the wall and the drive: as thick, down to its tip (the 2011 frames), in rows across its depth
for _s in np.arange(AUD_BANK['s0'] + 0.6, AUD_BANK['s1'], 1.3):
    _d = aud_bank_top(_s)
    if _d >= AUD_BANK['top']:
        break
    _n = int(np.clip(round(_d / 1.6), 1, 3))
    for _k in range(_n):
        _ss = _s + (0.65 if _k % 2 else 0.0) + _rt.uniform(-0.25, 0.25)
        _o = _d * (_k + 0.5) / _n + _rt.uniform(-0.2, 0.2)
        _x, _y, _ = along_raw(_ss, AUD_BANK['side'] * (E_WALK + _o))
        _sc, _rot = round(_rt.uniform(0.85, 1.3), 2), round(_rt.uniform(0, 6.28), 2)
        if _d < 0.9 or _o > aud_bank_top(_ss) - 0.35 or any(g_.distance(Point(_x, _y)) < 1.1 for g_ in _gk):
            continue
        shrubs.append(['bush', round(_x, 2), round(_y, 2), _sc, _rot])
for _s in np.arange(AUD_BANK['s0'] + 2.0, AUD_BANK['s1'] - 0.5, 1.5):
    if _in_flight(_s, 0.8) or aud_bank_top(_s) < AUD_BANK['top']:
        continue                                                    # (no hedge along the drive's kerb)
    _x, _y, _a = along_raw(_s, AUD_BANK['side'] * (E_WALK + AUD_BANK['top'] - 0.2))
    shrubs.append(['hedge_low', round(_x, 2), round(_y, 2), 1.0, round(_a, 3)])
print('대강당 앞 둑: strip hedge cleared', _n0, 'bank shrubs', len(shrubs) - _nb0)
# 학생회관 별관 앞마당 (ANNEX_YARD, reference/고증/4.5): Kakao skyview 2008 (winter) · 2010 and the 2008 · 2010 roadview
# (1017220187 - 193): asphalt from the foot of the drive's shrub strip to the hall's shop fronts and on south to the
# paved plaza before 학생회관's flight, cars parked in two rows before the shops (2008 skyview); a long lawn island with
# kerbs, its north tip 7 m short of the hall's south end, round clipped shrubs and pines on it (the 1997 photo: the
# drive in the foreground, the kerbed island with its pines before 학생회관); west of it an asphalt lane, then the lawn
# along 백양로.  The game had a lawn over all of it south of the hall's middle.  (After the planting: its own random
# numbers; the island's pines go at the very end of the tree list, below.)
ANNEX_ISLAND = LineString([(16.5, -22.9), (16.5, -46.4)]).buffer(2.7)
ANNEX_YARD = Polygon([(8.5, -21.0), (11.5, -21.0), (11.5, -56.7), (17.0, -59.5), (18.3, -56.0), (40.0, -56.0), (40.0, -1.0),
                      (8.5, -1.0)]).difference(unary_union([Polygon(b_['footprint']) for b_ in buildings])) \
    .difference(unary_union([Polygon(LATE_FOOTPRINT_1997[ANNEX_1997['id']]), ANNEX_ISLAND, AUD_RAMP_BAND, AUD_BANK_POLY,
                             bline.buffer(ROAD_HALF), ramp_strip(-AUD_RAMP['w'] / 2 - 1.0, AUD_RAMP['w'] / 2 + AUD_RAMP['walk'],
                                                                 -AUD_RAMP['mouth'] - 1.0, AUD_RAMP['run'])] + AUD_TREE_BEDS))
_n0 = (len(shrubs), len(props), len(cars))
_az = ANNEX_YARD.union(ANNEX_ISLAND)
shrubs = [s_ for s_ in shrubs if not _az.contains(Point(s_[1], s_[2]))]
props = [p_ for p_ in props if not _az.contains(Point(p_[1], p_[2]))]
cars = [c_ for c_ in cars if not _az.contains(Point(c_[1], c_[2]))]
print('학생회관 별관 앞마당: cleared (shrubs, props, cars)', _n0[0] - len(shrubs), _n0[1] - len(props), _n0[2] - len(cars),
      '- island %.0f m², yard %.0f m²' % (ANNEX_ISLAND.area, ANNEX_YARD.area))
# (painted in two halves split down the island: _ypaint fills a polygon's outer ring only, and the yard rings the island)
ANNEX_YARD_HALVES = [ANNEX_YARD.intersection(Polygon([(0.0, -70.0), (16.5, -70.0), (16.5, 0.0), (0.0, 0.0)])),
                     ANNEX_YARD.intersection(Polygon([(16.5, -70.0), (45.0, -70.0), (45.0, 0.0), (16.5, 0.0)]))]
_ra = random.Random(141)
ANNEX_TREES = [['pine', 16.4, -29.4, 0.62, round(_ra.uniform(0, 6.28), 2)],
               ['pine', 16.6, -40.8, 0.66, round(_ra.uniform(0, 6.28), 2)]]
for _x, _y in ((16.5, -21.6), (16.5, -24.2), (16.4, -35.2), (16.6, -45.6)):        # (the tip's and the planters' mounds)
    shrubs.append(['topiary_round', round(_x + _ra.uniform(-0.3, 0.3), 2), round(_y + _ra.uniform(-0.3, 0.3), 2),
                   round(_ra.uniform(1.15, 1.4), 2), round(_ra.uniform(0, 6.28), 2)])
for _y in np.arange(-26.0, -45.0, -2.4):                                             # (low ones down its sides)
    for _x in (14.6, 18.4):
        if min(abs(_y - t_[2]) for t_ in ANNEX_TREES) < 2.0:
            continue
        shrubs.append(['topiary_round', round(_x + _ra.uniform(-0.2, 0.2), 2), round(float(_y) + _ra.uniform(-0.4, 0.4), 2),
                       round(_ra.uniform(0.75, 0.95), 2), round(_ra.uniform(0, 6.28), 2)])
# the cars before the shops, end on to the hall, in the 2008 skyview's two rows (fewer; their stalls: park_lot below)
ANNEX_CARS = []
for _x, _y in ((22.0, -15.4), (16.8, -15.6), (23.2, -18.7), (18.0, -18.9)):
    ANNEX_CARS.append([_ra.choice(['sedan', 'sedan', 'hatch']), _x, _y,
                       round(math.radians(_ra.choice((0.0, 180.0)) - 13.0), 3), _ra.randrange(8)])
cars += ANNEX_CARS
# In front of 스팀슨관's south end (reference/고증.md 3.5.2; the Dec. 2010 walk past it, panoramas 1016786683 - 686,
# placed by the bearings of the end's corners and its bay): a bed of bare low shrubs in a boxwood band with round
# corners west of the walk, benches and a bin along its west side under the trees of a low bank, the walk and the
# forecourt before the end decomposed granite (마사토), and an asphalt path from the forecourt west over the bank to the
# drive.  (Laid after the planting: the rest of the campus keeps its draws.)
ST_BED = Polygon([(9.4, 186.4), (15.2, 186.1), (17.4, 201.6), (9.8, 201.8)]).buffer(-1.5).buffer(1.5)
ST_PATH = [(9.5, 208.0), (3.0, 207.6), (-4.0, 206.0), (-11.5, 204.8)]
_stw = LineString([(13.7, 173.2), (16.4, 184.4), (23.0, 210.8)])        # (OSM's walk: its middle)
ST_MASATO = unary_union([ST_BED.buffer(3.2), _stw.buffer(2.8, cap_style='flat'),
                         Polygon([(9.0, 201.0), (21.5, 201.0), (21.8, 210.6), (20.3, 210.8), (9.0, 213.8)])])
_stz = unary_union([ST_MASATO, LineString(ST_PATH).buffer(2.2)])
_n0 = (len(trees), len(shrubs), len(props))
clear_trees(_stz)
shrubs = [s for s in shrubs if not _stz.contains(Point(s[1], s[2]))]
props = [p for p in props if not _stz.contains(Point(p[1], p[2]))]
rng97 = random.Random(1997 + 97)
_be = ST_BED.exterior
for f_ in np.arange(0.0, _be.length, 1.5):                               # the boxwood band
    a_, b_ = _be.interpolate(f_), _be.interpolate(f_ + 0.3)
    shrubs.append(['hedge_low', round(a_.x, 2), round(a_.y, 2), 1.0, round(math.atan2(b_.y - a_.y, b_.x - a_.x), 3)])
_sb = ST_BED.buffer(-1.0)
_sbp = []
for _k in range(4000):                                                 # its low shrubs, bare in December
    x_, y_ = rng97.uniform(*_sb.bounds[0::2]), rng97.uniform(*_sb.bounds[1::2])
    if _sb.contains(Point(x_, y_)) and all((x_ - a_) ** 2 + (y_ - b_) ** 2 > 1.6 ** 2 for a_, b_ in _sbp):
        _sbp.append((x_, y_))
        shrubs.append(['azalea_red', round(x_, 2), round(y_, 2), round(rng97.uniform(0.55, 0.7), 2),
                       round(rng97.uniform(0, 6.28), 2)])
for y_ in (187.2, 190.6, 193.6, 197.2):                                  # benches facing the bed, and the bin
    props.append(['bench', round(6.9 + (y_ - 186.4) * 0.026, 2), y_, 0.0])
props.append(['recycle_bin', 6.8, 195.4, 0.0])
draw_poly('pavers', ST_MASATO, 0)
draw_poly('dirt', ST_MASATO)
draw_line('asphalt', ST_PATH, 3.0)
out['paths'].append(dict(kind='footway', w=3.0, pts=[list(p_) for p_ in ST_PATH]))
print('스팀슨관 south: cleared (trees, shrubs, props)', _n0[0] - len(trees), _n0[1] - len(shrubs), _n0[2] - len(props),
      '- bed shrubs', len(_sbp))
# the photo's red car on the east lawn (LOT_C): the web app paints car i in PARKED_COLORS[(c * 7 + i) % 13], 6 = red
cars = [c[:4] + [(2 * (6 - i)) % 13] if c[4] == 'red' else c for i, c in enumerate(cars)]
# 백주년기념관 앞 테라스 (CENT_TERRACE above; after every planting, so nothing else moves): before the flights the
# ginkgos stand in round pits in the paving 1.7 m behind the strip's line (2010 roadview: two of them triangulated at
# d 30.3 and 30.7), the strip's hedge goes; clipped shrubs fill the planters


def ct_sd(x, y):
    q = np.array([x, y]) - _ct0
    return float(q @ CT_T), float(q @ CT_N)


CT_PIT_D = 30.5
CENT_TERRACE['pits'] = []
for _t in trees:
    _s, _d = ct_sd(_t[1], _t[2])
    if _t[0] == 'ginkgo' and CT_PAVED_S[0] <= _s <= CT_PAVED_S[1] and 28.0 < _d < 36.0:
        _t[1], _t[2] = ct_xy(_s, CT_PIT_D)[0], ct_xy(_s, CT_PIT_D)[1]
        CENT_TERRACE['pits'].append(ct_xy(_s, CT_PIT_D)[:2])
shrubs = [_b for _b in shrubs if not (_b[0] == 'hedge_low' and CT_PAVED_S[0] - 0.5 <= ct_sd(_b[1], _b[2])[0] <= CT_PAVED_S[1] + 0.5
                                       and 28.0 < ct_sd(_b[1], _b[2])[1] < 36.0)]
_ang = round(math.atan2(CT_T[1], CT_T[0]), 3)
_angn = round(math.atan2(CT_N[1], CT_N[0]), 3)              # (hedge pieces along the flight: clear of the steps' zones)
for _p in CENT_TERRACE['planters']:
    _f = CENT_TERRACE['flights'][_p['f']]
    _d1 = _f['d0'] - (_f['n'] - 1) * _ctt
    for _dd in np.arange(_f['d0'] - 0.55, _d1 + 0.1, -0.9):
        for _ss in np.arange(_p['s'][0] + 0.5, _p['s'][1] - 0.5 + 1e-6, 0.65):
            shrubs.append(['hedge_low', *ct_xy(float(_ss), float(_dd))[:2], 0.85, _angn])
for _lo, _hi, _ds in ((CENT_TERRACE['box']['s'], CENT_TERRACE['box']['d'], 0.7),
                      (CENT_TERRACE['bed']['s'], CENT_TERRACE['bed']['d'], 0.9)):
    for _dd in np.arange(_hi[1] - 0.6, _hi[0] + 0.3, -_ds):           # (clear of the lower flight's zone)
        for _ss in np.arange(_lo[0] + 0.6, _lo[1] - 0.5, _ds):
            shrubs.append(['hedge_low', *ct_xy(float(_ss), float(_dd))[:2], 0.9, _ang])
out['centennial_terrace'] = CENT_TERRACE
out.update(trees=trees, shrubs=shrubs, props=props, cars=cars)
# 정문 밖: the town's own lists (its banks' trees, the road's lamps, the walker's barrier along the kerb), added after
# everything drawn from `rng`; what stood in its ground before (OSM's later walks there) goes
out['town'], TOWN = gate_town.layout(TOWN_PLAN, TOWN_SECS, ground_h, [Polygon(b_['footprint']) for b_ in buildings], E_CURB0)
_tz = TOWN['road_poly'].union(TOWN['bank']).buffer(1.0)
shapely.prepare(_tz)
for _lst in (trees, shrubs, props):
    _lst[:] = [t_ for t_ in _lst if not shapely.contains_xy(_tz, t_[1], t_[2])]
# ---------------------------------------------------------------------------
# 정문 앞 어귀 (정문의 자리, above; 고증 4.8).  South of the gate's wall, in its mouth and on 백양로's line short of the
# gate (s 0 .. GATE_S, whose verges, sidewalks and planting strips are flush asphalt now: blender/road.py mouths,
# below) nothing stands: the shrubs, props and decals the planting put there go, and its trees are moved, each in its
# own place in the list (web/src/world.js picks a tree's model by its index), onto the lawns inside the wall, past
# its paved strip (gate_town inside) and clear of 백양로.  Their own random stream, nothing drawn from `rng`.
# ---------------------------------------------------------------------------
_gw_t = np.array([math.cos(STATUES['gate']['rot']), math.sin(STATUES['gate']['rot'])])
_gw_n = np.array([-_gw_t[1], _gw_t[0]])
_gc = np.array(STATUES['gate']['pos'], float)
_south = Polygon([tuple(_gc + _gw_t * u_ + _gw_n * v_) for u_, v_ in ((-300, -0.6), (300, -0.6), (300, -300), (-300, -300))])
_gband = Polygon([along_raw(s_, ROAD_HALF + 0.6)[:2] for s_ in np.arange(0.0, GATE_S + 6.01, 2.0)]
                 + [along_raw(s_, -(ROAD_HALF + 0.6))[:2] for s_ in np.arange(GATE_S + 6.0, -0.01, -2.0)])
GATE_OUT = TOWN['mouth'].union(_gband).intersection(_south).buffer(0.3)
shapely.prepare(GATE_OUT)
_gate_rng = random.Random(1380)
_gate_moved = []
for _i, _t in enumerate(trees):
    if not shapely.contains_xy(GATE_OUT, _t[1], _t[2]):
        continue
    for _ in range(400):
        _u, _v = _gate_rng.uniform(15.0, 30.0), _gate_rng.uniform(15.5, 30.0)       # (the east lawn: the west one is open grass in photo A)
        _q = _gc + _gw_t * _u + _gw_n * _v
        if bline.distance(Point(*_q)) < ROAD_HALF + 1.5 or any(Polygon(b_['footprint']).buffer(3.0).contains(Point(*_q)) for b_ in buildings
                                                              if abs(b_['footprint'][0][0] - _q[0]) < 120):
            continue
        if min(math.hypot(o_[1] - _q[0], o_[2] - _q[1]) for o_ in trees) < 5.0:
            continue
        _gate_moved.append((_i, _t[0], (_t[1], _t[2]), (round(float(_q[0]), 2), round(float(_q[1]), 2))))
        trees[_i] = [_t[0], round(float(_q[0]), 2), round(float(_q[1]), 2)] + list(_t[3:5])
        break
shrubs[:] = [s_ for s_ in shrubs if not shapely.contains_xy(GATE_OUT, s_[1], s_[2])]
props[:] = [p_ for p_ in props if not shapely.contains_xy(GATE_OUT, p_[1], p_[2])]
out['decals'] = [d_ for d_ in out['decals'] if not shapely.contains_xy(GATE_OUT, d_[1], d_[2])]
# The gate's own stones (blender/props.py gate, GATE_MAIN / GATE_SIDE / GATE_LODGE / GATE_SLAB; 고증 4.8.1): the main
# pillars stand on the verges' south ends, the west walk's outer pillar and the lodge on the strip west of it, the
# tall slab on the strip east of the east walk.  The verges' clipped shrubs and the strips' hedge give way to them.
# (u0, u1 along the wall eastwards from the gate's middle, v0, v1 north of its line; 0.6 m clear)
GATE_PARTS = [(-5.65, -4.25, -0.3, 2.1), (4.25, 5.65, -0.3, 2.1), (-11.65, -10.3, -0.3, 1.7), (-18.65, -11.65, -0.3, 4.9),
              (10.25, 12.75, -0.2, 0.2)]
_gparts = unary_union([Polygon([tuple(_gc + _gw_t * u_ + _gw_n * v_) for u_, v_ in ((a_, c_), (b_, c_), (b_, d_), (a_, d_))])
                       for a_, b_, c_, d_ in GATE_PARTS]).buffer(0.6)
_ngs = len(shrubs)
shrubs[:] = [s_ for s_ in shrubs if not shapely.contains_xy(_gparts, s_[1], s_[2])]
print('정문 앞 어귀: gate at s %.1f (%.1f, %.1f); trees moved %s; shrubs under the gate\'s stones -%d'
      % (GATE_S, *GATE_C, _gate_moved, _ngs - len(shrubs)))
# The web picks each tree's model by its place in the list (web/src/world.js Forest: one draw a tree, in order), so
# the town's share of it is held at TOWN_TREE_SLOTS: the trees after it (대강당 진입로's, 신촌 로터리's) keep their
# looks whatever the town plants.  Short of it, more trees on the banks west of the bridge, beside the town's own;
# over it, the last go.  (Its own random stream.)
TOWN_TREE_SLOTS = 113
_tt, _trng = list(TOWN['trees'])[:TOWN_TREE_SLOTS], random.Random(1381)
_bank_src = [t_ for t_ in _tt if t_[0] in ('poplar', 'zelkova', 'oak', 'zelkova_young') and t_[1] < gate_town.BRIDGE[0] - 12]
for _ in range(2000):
    if len(_tt) >= TOWN_TREE_SLOTS or not _bank_src:
        break
    _src = _trng.choice(_bank_src)
    _q = (round(_src[1] + _trng.choice((-1, 1)) * _trng.uniform(3.5, 6.0), 2), _src[2])
    if min(math.hypot(o_[1] - _q[0], o_[2] - _q[1]) for o_ in _tt) < 3.0 or not TOWN['bank'].contains(Point(*_q)):
        continue
    _tt.append([_src[0], _q[0], _q[1], round(_trng.uniform(0.5, 0.8), 2), round(_trng.uniform(0, 6.28), 2)])
assert len(_tt) == TOWN_TREE_SLOTS, len(_tt)
TOWN['trees'] = _tt
trees += TOWN['trees']
trees += AUD_NEW_TREES                         # (대강당 진입로 둘레: last, so that no other tree changes its model)
shrubs += TOWN['shrubs']
props += TOWN['props']
out['colliders'] += TOWN['colliders']
shapely.prepare(TOWN['zone'])
out['paths'] = [p_ for p_ in out['paths'] if not all(shapely.contains_xy(TOWN['zone'], x_, y_) for x_, y_ in p_['pts'])] + TOWN['paths']
print('정문 밖: blocks', len(out['town']['blocks']), 'signs', len(out['town']['signs']), 'trees', len(TOWN['trees']),
      'shrubs', len(TOWN['shrubs']), 'lamps', len(TOWN['props']), 'barrier', len(TOWN['colliders']))
# 제1공학관 앞 진입로 (ENG_MOUTH): the forecourt, as wide as the opening, from the sidewalk to the hall's front
# (asphalt: painted with 의료원's car parks below, _ga); nothing planted or parked on it or in the strip's opening.  The
# row's ginkgo there gives its place in the list to the last tree (the game picks each tree's model in the list's
# order, web/src/world.js Forest, so no other tree changes its looks).  (2008 - 2011 have a row of bollards across it
# on the strip's line, left out with the verge's opening)
_eng_fp = Polygon(next(b_ for b_ in buildings if b_['id'] == 205583531)['footprint'])
ENG_COURT = Polygon([along_raw(s_, o_)[:2] for s_, o_ in ((ENG_MOUTH[1], E_WALK - 0.2), (ENG_MOUTH[2], E_WALK - 0.2),
                                                         (ENG_MOUTH[2], 48.0), (ENG_MOUTH[1], 48.0))]).difference(_eng_fp)
_ez = ENG_COURT.union(Polygon([along_raw(s_, o_)[:2] for s_, o_ in ((ENG_MOUTH[1] - 0.6, E_WALK), (ENG_MOUTH[2] + 0.6, E_WALK),
                                                                    (ENG_MOUTH[2] + 0.6, ROAD_HALF + 0.6),
                                                                    (ENG_MOUTH[1] - 0.6, ROAD_HALF + 0.6))]))
_nf = (len(trees), len(shrubs), len(props), len(cars))
for _i in sorted((i_ for i_, t_ in enumerate(trees) if _ez.contains(Point(*to_new(*rxy(t_))))), reverse=True):
    trees[_i] = trees[-1]           # (as first cleared, along the line as first laid: to_new; the moved line's at the end)
    trees.pop()
for t_ in trees:
    if _ez.contains(Point(t_[1], t_[2])):
        drop_tree(t_)
shrubs[:] = [s_ for s_ in shrubs if not _ez.buffer(0.5).contains(Point(s_[1], s_[2]))]
props[:] = [p_ for p_ in props if not _ez.contains(Point(p_[1], p_[2]))]
cars[:] = [c_ for c_ in cars if not _ez.buffer(1.0).contains(Point(c_[1], c_[2]))]
print('제1공학관 앞 진입로: cleared (trees, shrubs, props, cars)', _nf[0] - len(trees), _nf[1] - len(shrubs),
      _nf[2] - len(props), _nf[3] - len(cars))
out['paths'].append(dict(kind='service', w=round(ENG_MOUTH[2] - ENG_MOUTH[1], 1),
                         pts=[[round(v_, 1) for v_ in along_raw((ENG_MOUTH[1] + ENG_MOUTH[2]) / 2, o_)[:2]] for o_ in (ROAD_HALF, 38.0)]))
# ---------------------------------------------------------------------------------------------------------------------
# 중앙도서관 앞 (LIB97 above, reference/고증/3.2): the forecourt of the vertical aerial photos of 28 July 1997 over the
# one drawn from the 1990 · 1995 maps (LIB_BEDS, LIB_WALKS: the random planting read those, so this comes after every
# planting and nothing else moves).  From the hall out (o): the terrace 9.8 m (the hall's own mesh), a band of clipped
# shrubs at its wall's foot, the lane along it (SIDE_W run on north), the beds (each with a slant walk from the far corner to the plaza), a
# walk along their far side, a strip of trees, 백양로's own strip and sidewalk; in the middle the plaza from the flight's
# foot out to the sidewalk, a hedged island down it; north of the beds the drive and its row of cars (asphalt).
# Trees in the way move to the nearest bed in place (the web picks each tree's model by its place in the list).
_l9 = LIB97
_l9st = LIB_ROAD_O - ROAD_HALF                              # the inner edge of 백양로's planting strip (o)
_l9n = 93.0                                                # the asphalt north of the beds, out to OSM's drive (its kerb at s 92.4)
LIB97_TERRACE = unary_union([lf_rect(_l9['south'], _l9['north'], -0.3, _l9['depth']),
                             lf_rect(_l9['south'], 0.3, _l9['south_w'], _l9['depth']),
                             lf_rect(LIB_LEN - 0.3, _l9['north'], _l9['north_w'], _l9['depth'])])
LIB97_PLAZA = lf_rect(*_l9['plaza'], _l9['depth'], _l9st + 0.4)
LIB97_ISLAND = lf_rect(*_l9['island'])
LIB97_WALK = lf_rect(-17.4, _l9n, _l9['band'], _l9['walk'])
LIB97_OUTER = lf_rect(-17.4, _l9['beds'][1] + 0.5, *_l9['outer'])


def _l9_slant(a_, b_, ext=1.2):
    a_, b_ = np.array(LF(*a_)), np.array(LF(*b_))
    u_ = (b_ - a_) / np.linalg.norm(b_ - a_)
    return LineString([tuple(a_ - u_ * ext), tuple(b_ + u_ * ext)]).buffer(_l9['slant_w'] / 2, cap_style=2)


LIB97_SLANT = unary_union([_l9_slant(*q_) for q_ in _l9['slant']]).intersection(
    lf_rect(_l9['beds'][0], _l9['beds'][1], _l9['walk'] - 0.5, _l9['outer'][0] + 0.5))
LIB97_BEDS = lf_rect(*_l9['beds'], _l9['walk'], _l9['outer'][0]).difference(unary_union([LIB97_PLAZA, LIB97_SLANT]))
LIB97_STRIP = lf_rect(*_l9['beds'], _l9['outer'][1], _l9st).difference(LIB97_PLAZA)
# the shrub band: along the front either side of the flight, round the south end, by the north end
LIB97_BANDS = [(_l9['south'], _l9['plaza'][0] - 0.9, _l9['depth'], _l9['band']),
               (_l9['plaza'][1] + 0.4, _l9['north'], _l9['depth'], _l9['band']),
               (_l9['south'] - 2.6, _l9['south'], _l9['south_w'], _l9['band']),
               (_l9['north'], _l9['north'] + 2.2, _l9['north_w'], _l9['band'])]
LIB97_NORTH = lf_rect(_l9['beds'][1], _l9n, _l9['band'], _l9st)
LIB97_PAVED = unary_union([LIB97_WALK, LIB97_OUTER, LIB97_SLANT, LIB97_PLAZA.difference(LIB97_ISLAND), LIB97_NORTH])
LIB97_ZONE = unary_union([lf_rect(_l9['beds'][0], _l9n, _l9['band'], _l9st), lf_rect(_l9['beds'][0], _l9['north'] + 2.2, -0.5, _l9['band']),
                          LIB97_TERRACE.buffer(2.7, join_style=2)] + [lf_rect(*q_) for q_ in LIB97_BANDS]).difference(_lib.buffer(-0.5))
_l9mouth = lf_rect(_l9['plaza'][0] - 0.6, _l9['plaza'][1] + 0.6, _l9st - 0.3, LIB_ROAD_O - E_WALK + 0.3)   # (the strip's opening)
_l9ok = unary_union([LIB97_BEDS.buffer(-1.2), LIB97_STRIP.buffer(-0.9)])
shapely.prepare(LIB97_ZONE)
_n9 = [len(shrubs), len(props), 0, 0]
# the slant walk's frame as the photo's planting was first placed (LD above) and as the walk runs (t from its head at
# the far corner, w to its right, the hall's side); what stood along the old one goes as far along the new
_l9a, _l9b = np.array(LF(*_l9['slant'][1][0])), np.array(LF(*_l9['slant'][1][1]))
_l9len = float(np.linalg.norm(_l9b - _l9a))
_l9u = (_l9b - _l9a) / _l9len
_l9r = np.array([_l9u[1], -_l9u[0]])
_l9k = _l9len / float(np.linalg.norm(_lb - _la))


def LD9(x_, y_):
    """a place given in the old slant walk's frame, at the same place along the walk of 1997"""
    q_ = np.array([x_, y_]) - _la
    return tuple(float(c_) for c_ in _l9a + _l9u * float(q_ @ _lda) * _l9k + _l9r * float(q_ @ _ldr))


_l9kept = []
# (free places a tree in the way can go to: the beds and the trees' strip on a 2.5 m grid, clear of where people stand)
_l9clear = unary_union([Point(*LF(*q_)).buffer(4.5) for q_ in ((43.0, 33.0), (13.6, 29.3), (53.6, 24.4))])   # (main.js groups)
_l9spots = [Point(*LF(float(s_), float(o_))) for s_ in np.arange(_l9['beds'][0] + 1.5, _l9['beds'][1], 2.5)
            for o_ in np.arange(_l9['walk'] + 1.5, _l9st, 2.5)]
_l9spots = [q_ for q_ in _l9spots if _l9ok.contains(q_) and not _l9clear.contains(q_)]


def _l9_place(p_, gap=3.2):
    """the nearest free place in a bed (or the trees' strip) for a tree at p_: p_ itself if it stands in one"""
    if _l9ok.contains(p_) and all(p_.distance(q_) >= gap for q_ in _l9kept):
        return p_
    return min((q_ for q_ in _l9spots if all(q_.distance(k_) >= gap for k_ in _l9kept)), key=p_.distance)


for t_, (x0_, y0_), k_ in LIB_TREE_OBJS:                   # the photo's own trees first (LIB_TREES' first four): along the walk of 1997
    if k_ < 4:
        t_[1], t_[2] = (round(c_, 2) for c_ in LD9(x0_, y0_))
_l9hand = {id(t_) for t_, _, _ in LIB_TREE_OBJS}
for t_ in sorted((t_ for t_ in trees if LIB97_ZONE.contains(Point(t_[1], t_[2])) or _l9mouth.contains(Point(t_[1], t_[2]))),
                 key=lambda t_: id(t_) not in _l9hand):
    if any(t_ is d_ for d_ in DROP_TREES):
        continue
    p_ = Point(t_[1], t_[2])
    q_ = _l9_place(p_)
    if q_.distance(p_) > 0.01:                             # (백양로's row before the plaza too: into the trees' strip beside it)
        t_[1], t_[2] = round(q_.x, 2), round(q_.y, 2)
        _n9[3] += 1
    _l9kept.append(Point(t_[1], t_[2]))
shrubs[:] = [s_ for s_ in shrubs if not (LIB97_ZONE.contains(Point(s_[1], s_[2])) or _l9mouth.contains(Point(s_[1], s_[2])))]
props[:] = [p_ for p_ in props if not (p_[0] in ('lamp_quad', 'bench') and LIB97_ZONE.contains(Point(p_[1], p_[2])))]
rng97 = random.Random(1997 + 1631)
# the photos' beds and the strip along 백양로 are one canopy: more trees there, the strip's in a row (they go at the very
# end of the list, LIB97_NEW_TREES, so that no other tree changes its model)
LIB97_NEW_TREES = []
for s_ in np.arange(_l9['beds'][0] + 3.0, _l9['beds'][1] - 2.0, 7.5):
    q_ = Point(*LF(float(s_), (_l9['outer'][1] + _l9st) / 2 + rng97.uniform(-0.5, 0.5)))
    kind_, sc_ = rng97.choice(('zelkova', 'zelkova', 'cherry')), round(rng97.uniform(0.6, 0.85), 2)
    if _l9ok.contains(q_) and all(q_.distance(k_) >= 4.0 for k_ in _l9kept):
        LIB97_NEW_TREES.append([kind_, round(q_.x, 2), round(q_.y, 2), sc_, round(rng97.uniform(0, 6.28), 2)])
        _l9kept.append(q_)
for (s_, o_, kind_) in ((-5.0, 27.0, 'zelkova'), (2.0, 24.5, 'pine'), (17.0, 24.0, 'zelkova'), (21.0, 33.0, 'cherry'), (12.0, 37.0, 'zelkova'),
                        (-2.0, 38.5, 'maple'), (56.0, 31.0, 'zelkova'), (64.0, 24.5, 'pine'), (74.0, 26.0, 'zelkova'),
                        (79.0, 33.0, 'cherry'), (66.0, 38.0, 'maple'), (54.0, 38.5, 'zelkova')):
    q_ = Point(*LF(s_, o_))
    if _l9ok.contains(q_) and not _l9clear.contains(q_) and all(q_.distance(k_) >= 4.0 for k_ in _l9kept):
        LIB97_NEW_TREES.append([kind_, round(q_.x, 2), round(q_.y, 2), round(rng97.uniform(0.55, 0.8), 2), round(rng97.uniform(0, 6.28), 2)])
        _l9kept.append(q_)
_l9bed = LIB97_BEDS.buffer(-0.4).difference(_l9clear)
for kind_, (x_, y_), sc_ in LIB_PLANT:                     # the photo's clipped shrubs, along the walk of 1997
    x_, y_ = LD9(x_, y_)
    if _l9bed.contains(Point(x_, y_)):
        shrubs.append([kind_, round(x_, 2), round(y_, 2), sc_, round(rng97.uniform(0, 6.28), 2)])
for (s_, o_) in ((10.0, 24.5), (11.5, 25.7), (22.0, 36.0), (23.4, 37.0), (55.0, 37.0), (56.4, 38.0), (70.0, 25.0)):
    if _l9bed.contains(Point(*LF(s_, o_))):                # green azalea clumps under the trees
        shrubs.append(['bush', *(round(c_, 2) for c_ in LF(s_, o_)), round(rng97.uniform(0.9, 1.2), 2), round(rng97.uniform(0, 6.28), 2)])
# the band at the terrace wall's foot: clipped mounds in two rows (the photos: a dark scalloped band 3.6 m deep; the
# 2008 - 2010 roadview: round clipped shrubs along the wall)
_l9fa = math.atan2(_lfu[1], _lfu[0])
for s0_, s1_, o0_, o1_ in LIB97_BANDS:
    along_s = (s1_ - s0_) > (o1_ - o0_)
    a0_, a1_, b0_, b1_ = (s0_, s1_, o0_, o1_) if along_s else (o0_, o1_, s0_, s1_)
    rows_ = [b0_ + 1.1, b1_ - 1.0] if b1_ - b0_ > 3.0 else [(b0_ + b1_) / 2]
    for k_, b_ in enumerate(rows_):
        for a_ in np.arange(a0_ + 0.9 + 0.95 * (k_ % 2), a1_ - 0.6, 1.9):
            x_, y_ = LF(a_, b_) if along_s else LF(b_, a_)
            shrubs.append(['hedge_blob', round(x_, 2), round(y_, 2), round(rng97.uniform(1.35, 1.55), 2), round(rng97.uniform(0, 6.28), 2)])
# the beds' low box hedges along the walk by the band and along the plaza, the island's two rows
_l9edge = LIB97_WALK.union(LIB97_PLAZA).buffer(1.6)
_l9sl = LIB97_SLANT.buffer(0.9)
for g_ in (LIB97_BEDS.geoms if hasattr(LIB97_BEDS, 'geoms') else [LIB97_BEDS]):
    ring_ = g_.buffer(-0.6, join_style=2).exterior
    for d_ in np.arange(0.75, ring_.length, 1.5):
        p_, q_ = ring_.interpolate(d_), ring_.interpolate(min(ring_.length, d_ + 0.5))
        if _l9edge.contains(p_) and not _l9sl.contains(p_):
            shrubs.append(['hedge_low', round(p_.x, 2), round(p_.y, 2), 1.0, round(math.atan2(q_.y - p_.y, q_.x - p_.x), 3)])
_l9im = (_l9['island'][0] + _l9['island'][1]) / 2
for o_ in np.arange(_l9['island'][2] + 0.9, _l9['island'][3] - 0.5, 1.5):
    for s_ in (_l9im - 0.35, _l9im + 0.35):
        shrubs.append(['hedge_low', *(round(c_, 2) for c_ in LF(s_, float(o_))), 1.0, round(math.atan2(_lfn[1], _lfn[0]), 3)])
# benches at the beds' edge facing the hall; the four-globe lamps of the 1997 photo by the slant walk (a near one, a far
# one), on the island (the 2008 - 2010 roadview) and at the beds' edge
for s_ in (4.0, 16.0, 60.0, 72.0):
    P('bench', *LF(s_, _l9['walk'] + 0.7), math.atan2(-_lfn[1], -_lfn[0]))
for (x_, y_) in [LD9(*LD(10.6, 4.4)), LD9(*LD(48.2, 3.5)), LF(_l9im, 27.0), LF(_l9im, 39.5), LF(12.0, _l9['walk'] + 0.9),
                 LF(64.0, _l9['walk'] + 0.9)]:
    P('lamp_quad', x_, y_, -0.25)
# the walks the game reads (minimap, crowd) and the decals: what lay on the old paving goes with it
_l9z = lf_rect(_l9['beds'][0], _l9n, -1.0, _l9st)
out['paths'] = [p_ for p_ in out['paths'] if not (p_['kind'] in ('footway', 'path', 'pedestrian', 'steps') and len(p_['pts']) > 1
                                                  and _l9z.contains(LineString(p_['pts']).centroid))]
_lpt = lambda *q_: [[round(c_, 1) for c_ in LF(*v_)] for v_ in q_]
out['paths'][:0] = [dict(kind='footway', w=round(_l9['walk'] - _l9['band'], 1), pts=_lpt((-17.0, 17.2), (_l9n, 17.2))),   # (first, as LIB_PATHS were: the crowd walks the first long ones)
                 dict(kind='footway', w=round(_l9['outer'][1] - _l9['outer'][0], 1), pts=_lpt((-17.0, 43.4), (_l9['beds'][1], 43.4))),
                 dict(kind='footway', w=_l9['slant_w'], pts=_lpt(*_l9['slant'][0])),
                 dict(kind='footway', w=_l9['slant_w'], pts=_lpt(*_l9['slant'][1])),
                 dict(kind='footway', w=8.0, pts=_lpt((_l9['plaza'][0] + 4.2, _l9['depth'] + 2.0), (_l9['plaza'][0] + 4.2, _l9st + 1.0))),
                 dict(kind='footway', w=8.0, pts=_lpt((_l9['plaza'][1] - 4.6, _l9['depth'] + 2.0), (_l9['plaza'][1] - 4.6, _l9st + 1.0))),
                 dict(kind='footway', w=8.0, pts=_lpt((_l9['south'] + 2.0, 5.0), (_l9['north'] - 2.0, 5.0)))]
_nd9 = len(out['decals'])
out['decals'] = [d_ for d_ in out['decals'] if not (LIB97_ZONE.contains(Point(d_[1], d_[2])) and not LIB97_PAVED.contains(Point(d_[1], d_[2])))]
out['library_terrace'] = dict(
    o=[float(v_) for v_ in _lf0], t=[round(float(v_), 5) for v_ in _lfu], n=[round(float(v_), 5) for v_ in _lfn], len=round(LIB_LEN, 3),
    floor=LIB_FLOOR, foot=LIB_FOOT, depth=_l9['depth'], south=_l9['south'], north=round(_l9['north'], 3), south_w=_l9['south_w'],
    north_w=_l9['north_w'], stair_w=_l9['stair_w'], risers=_l9['risers'], tread=_l9['tread'])
print('중앙도서관 앞 1997: trees moved %d (hand-placed %d), new %d; shrubs %d -> %d, props %d -> %d, decals -%d'
      % (_n9[3], len(LIB_TREE_OBJS), len(LIB97_NEW_TREES), _n9[0], len(shrubs), _n9[1], len(props), _nd9 - len(out['decals'])))
# 독수리상 서쪽 옆길이 백양로와 만나는 길 (reference/고증/2.3): in the vertical aerial photos of July 1997 (three frames
# within 0.3 m) the drive along 제1공학관's north side does not end at the side road's corner west of the eagle
# (SIDE_W) but runs on east, 7 m wide, between the eagle's garden and 활천대's to 백양로 (its kerbs at y -183.3 and
# -190.6 by the road; the 2011 roadview has the same drive and a crossing there).  After every planting: what
# stands in its way steps aside in place.
JUNC = [tuple(SIDE_W[1]), (-88.0, -185.7), (-72.0, -186.3), (-65.0, -186.9),
        tuple(round(c_, 2) for c_ in along_raw((JUNC_MOUTH[1] + JUNC_MOUTH[2]) / 2, E_CURB - 0.3)[:2])]
JUNC_W = 7.0
_jz = LineString(JUNC).buffer(JUNC_W / 2 + 0.9, cap_style=2).difference(bline.buffer(E_VERGE + 0.2))
_jout = _jz.buffer(1.6).exterior
_nj = [0, len(shrubs), len(props)]
for t_ in trees:
    p_ = Point(t_[1], t_[2])
    if _jz.contains(p_) and not any(t_ is d_ for d_ in DROP_TREES):
        q_ = _jout.interpolate(_jout.project(p_))          # (aside, in place: the list keeps its order)
        t_[1], t_[2] = round(q_.x, 2), round(q_.y, 2)
        _nj[0] += 1
shrubs[:] = [s_ for s_ in shrubs if not _jz.buffer(0.3).contains(Point(s_[1], s_[2]))]
props[:] = [p_ for p_ in props if not _jz.contains(Point(p_[1], p_[2]))]
out['paths'].append(dict(kind='service', w=JUNC_W, pts=[[round(c_, 1) for c_ in q_] for q_ in JUNC]))
out['decals'] = [d_ for d_ in out['decals'] if not (d_[0] in ('crack', 'stain') and _jz.contains(Point(d_[1], d_[2])))]
print('독수리상 서쪽 옆길 ~ 백양로: trees aside %d, shrubs -%d, props -%d' % (_nj[0], _nj[1] - len(shrubs), _nj[2] - len(props)))
# ---------------------------------------------------------------------------------------------------------------------
# 주차 칸 (park_…): every car park's stalls, in rows, and their painted lines where a photo or the roadview shows them
# (campus.json `parking`; blender/landmarks.py parking_lines lays them on the ground, as 대우관 뒤 had them alone
# before).  A row: k stalls w wide side by side from its corner o along t, each d deep along n (from the aisle towards
# the cars' noses); skew (deg) turns the stalls off n towards t (angled bays, the stall w measured square to its sides).
# Its lines: the sides between the stalls and at both ends of the row, and the line across their heads if `head`.
# Nothing here draws from a shared random stream: the cars of these lots are placed with their own (above).
PARK_LOTS = []


def park_lot(name, paint=None, w=0.12):
    """a car park in campus.json `parking`: paint 'white' / 'yellow' (None: no lines in any source), line width w"""
    lot = dict(name=name, paint=paint, w=w, stalls=[], lines=[])
    PARK_LOTS.append(lot)
    return lot


def park_row(lot, o, t, n, k, w=2.6, d=5.0, skew=0.0, head=False):
    """k stalls in a row (above) into `lot`; returns their middles and the cars' headings (nose along the stall)"""
    o, t, n = np.asarray(o, float), np.asarray(t, float), np.asarray(n, float)
    sk = math.radians(skew)
    a_ = n * math.cos(sk) + t * math.sin(sk)                    # (along the stall's sides, towards the nose)
    pitch = w / max(0.2, math.cos(sk))                           # (along the row from one side line to the next)
    out_ = []
    for i in range(k + 1):
        p_ = o + t * pitch * i
        lot['lines'].append([round(float(v_), 2) for v_ in (*p_, *(p_ + a_ * d))])
    if head and k:
        lot['lines'].append([round(float(v_), 2) for v_ in (*(o + a_ * d), *(o + t * pitch * k + a_ * d))])
    for i in range(k):
        c_ = o + t * pitch * (i + 0.5) + a_ * (d / 2)
        out_.append((float(c_[0]), float(c_[1]), math.atan2(a_[1], a_[0])))
        lot['stalls'].append([round(float(c_[0]), 2), round(float(c_[1]), 2), round(math.atan2(a_[1], a_[0]), 3)])
    return out_


# 대우관 뒤 (DAEWOO_BACK, the cars above): white lines either side of every stall (the 1997 aerial photos show the
# rows' lines; Naver street view 2010)
_lot = park_lot('대우관 뒤', 'white')
_seen = set()
for _n, _i, (_x, _y), _h, _sides in dwb_stalls():
    _lot['stalls'].append([round(_x, 2), round(_y, 2), round(_h, 3)])
    for _a, _b in _sides:
        if (_a, _b) not in _seen:
            _seen.add((_a, _b))
            _lot['lines'].append([round(float(v_), 2) for v_ in (*_a, *_b)])
# 경영학교실단(백양관) 앞 (BK_WALK): the walk through the strip's opening from the sidewalk to the front flight's paved
# foot (paving, as the sidewalk: _gp below); the car park before the north wing (BK_LOT, asphalt: _ga below), its
# drive's mouth through the strip (BK_MOUTH) and the clipped hedge island north of it (BK_ISLAND); the game had the
# drive end in a loop on the lawn with no car.  (reference/고증/3.15-3.17 「북쪽 주차장」)
# BK_LOT: Kakao skyview 2008 (winter) and 2010 (summer), co-registered to 0.1 m and 0.125 m a pixel, with the 2008 ·
# 2010 roadview (2381322 · 2381323, 1016786032 · 1016786034): asphalt from the front block's north wall and the wing's
# east face out to the narrow planted island along its east side (x 2.5) and north past the wing's north-east corner,
# 4 m west round it, to a row along the north edge (y 132).  Its bays: a row nose in towards the wing, seven cars in
# 2008 between the front block's wall and 16 m north (3.5 m off the face: the walk and the ramp along the annex), and
# five nose north along the north edge (2008 and 2010 both); white lines either side of them and across their heads
# (2008 roadview).  Nothing planted or parked on the walk, the openings, the car park or the island but its cars
_bk_off = float(bline.distance(Point(*BK_FOOT)))
BK_COURT = Polygon([along_raw(s_, o_)[:2] for s_, o_ in ((BK_WALK[1], E_WALK - 0.2), (BK_WALK[2], E_WALK - 0.2),
                                                        (BK_WALK[2], _bk_off - 1.5), (BK_WALK[1], _bk_off - 1.5))])
_bkq = np.array([-14.58, 108.14])                       # (the front block's north wall meets the wing's east face)
_bkne = np.array([-13.1, 113.6])                        # (the wing's north-east corner, its north face going west)
_bknf = (np.array([-59.0, 125.8]) - _bkne) / np.linalg.norm(np.array([-59.0, 125.8]) - _bkne)
BK_LOT = Polygon([tuple(_bkq), tuple(_bkne), tuple(_bkne + _bknf * 4.0), (-17.0, 132.0), (2.5, 132.0), (2.5, 109.0),
                  (-4.6, 105.49)])
# (the drive from it to the mouth, over the lawn the OSM drive crossed)
BK_DRIVE = Polygon([(-4.6, 105.49), (2.5, 103.8), tuple(along_raw(BK_MOUTH[1], E_WALK - 0.2)[:2]),
                    tuple(along_raw(BK_MOUTH[2] - 0.5, E_WALK - 0.2)[:2]), (2.5, 112.0)]).buffer(0)
# BK_ISLAND: the skyview's island, 8.2 m wide, its round ends at s 552.8 and 567.7, 6.2 m in from the carriageway's kerb
# beside it (the cars park on the asphalt between); here in from the game's kerb as much: from just behind the
# sidewalk (E_WALK) back over the strip's place.  A clipped boxwood hedge round a lawn, two pines in it (the 2008 /
# 2010 roadview: the south one leaning on three props)
_bki0 = E_WALK + 0.2
BK_ISLAND = LineString([along_raw(s_, _bki0 + 4.1)[:2] for s_ in np.arange(BK_ISLAND_S[0] + 4.1, BK_ISLAND_S[1] - 4.1 + 0.01, 0.5)]
                       ).buffer(4.1, quad_segs=8)
_bz = unary_union([BK_COURT, BK_LOT, BK_DRIVE, BK_ISLAND]
                  + [Polygon([along_raw(s_, o_)[:2] for s_, o_ in ((o0_ - 0.6, E_WALK), (o1_ + 0.6, E_WALK),
                                                                  (o1_ + 0.6, ROAD_HALF + 0.6), (o0_ - 0.6, ROAD_HALF + 0.6))])
                     for _, o0_, o1_ in (BK_WALK, BK_MOUTH)])
_nf = (len(trees), len(shrubs), len(props), len(cars))
# (the trees go once 신촌 로터리's are in, below: each gives its place to the very last one, so that only that one
# tree, far off in the town, may change its model)
LATE_GONE_TREES = {i_ for i_, t_ in enumerate(trees) if _bz.buffer(0.8).contains(Point(*to_new(*rxy(t_))))}   # (as first cleared)
DROP_TREES += [t_ for i_, t_ in enumerate(trees) if i_ not in LATE_GONE_TREES and _bz.buffer(0.8).contains(Point(t_[1], t_[2]))]
shrubs[:] = [s_ for s_ in shrubs if not _bz.buffer(0.5).contains(Point(s_[1], s_[2]))]
props[:] = [p_ for p_ in props if not _bz.contains(Point(p_[1], p_[2]))]
cars[:] = [c_ for c_ in cars if not _bz.buffer(1.0).contains(Point(c_[1], c_[2]))]
_rbk = random.Random(1997 + 548)
_lot = park_lot('백양관 북쪽', 'white')
_bk_st = park_row(_lot, _bkq + BK_T * 1.0 + BK_N * 8.5, BK_T, -BK_N, 7, w=2.3, d=5.0, head=True)       # (nose in)
_bk_st += park_row(_lot, np.array([-13.0, 126.8]), np.array([1.0, 0.0]), np.array([0.0, 1.0]), 5, w=2.3, d=5.0, head=True)
for x_, y_, h_ in _bk_st:
    if _rbk.random() < 0.85:
        cars.append([_rbk.choice(['sedan', 'sedan', 'sedan', 'hatch']), round(x_, 2), round(y_, 2),
                     round(h_ + _rbk.uniform(-.04, .04), 3), _rbk.randrange(8)])
# the island's hedge, a pine at each end inside it (appended to the trees at the very end, below: BK_ISLAND_TREES),
# and the two bollards across the sidewalk at the mouth's south side (2010 1016786032 · 1016786034, 2008 2381322)
hedge_line(list(BK_ISLAND.buffer(-0.45).exterior.coords)[:-1], 'hedge_low', 1.0, step=1.5)
BK_ISLAND_TREES = [['pine', *[round(float(v_), 2) for v_ in along_raw(BK_ISLAND_S[0] + 4.5, _bki0 + 4.6)[:2]], 0.95, 0.6],
                   ['pine', *[round(float(v_), 2) for v_ in along_raw(BK_ISLAND_S[1] - 5.0, _bki0 + 3.6)[:2]], 0.8, 2.9]]
for o_ in (6.6, 8.6):
    P('bollard', *along_raw(BK_MOUTH[1] - 1.5, o_)[:2], 0.0)
print('경영학교실단 앞 길 · 북쪽 주차장: cleared (trees, shrubs, props, cars)', len(LATE_GONE_TREES), _nf[1] - len(shrubs),
      _nf[2] - len(props), _nf[3] - len(cars), '- walk s %.1f - %.1f to %.1f m' % (BK_WALK[1], BK_WALK[2], _bk_off),
      '- island %.0f m², bays %d' % (BK_ISLAND.area, len(_bk_st)))
# 대강당 북쪽 곁길 어귀 (AUD_SIDE_MOUTH) and 별관 앞마당 어귀 (AUD_YARD_MOUTH): asphalt (_ga below) through the strip's
# opening from the sidewalk (it stays: cars cross it) to the road or the yard behind it; nothing planted or parked in
# it.  The row's ginkgo in each moves in place along the row to 2 m past the opening's nearer end (so that no other
# tree changes its place in the list, and so its model)


def aud_mouth_poly(m_, o1_, pad_=0.0, o0_=E_WALK - 0.2):
    return Polygon([along_raw(s_, m_[0] * o_)[:2] for s_, o_ in ((m_[1] - pad_, o0_), (m_[2] + pad_, o0_), (m_[2] + pad_, o1_),
                                                                (m_[1] - pad_, o1_))])


AUD_SIDE_POLY = unary_union([aud_mouth_poly(AUD_SIDE_MOUTH, ROAD_HALF + 3.0), aud_mouth_poly(AUD_YARD_STRIP, 19.5)])
_sz = unary_union([AUD_SIDE_POLY] + [aud_mouth_poly(m_, ROAD_HALF + 0.6, 0.6, E_WALK) for m_ in (AUD_SIDE_MOUTH, AUD_YARD_STRIP)])
_nf = (0, len(shrubs), len(props), len(cars))
for t_ in trees:
    if not _sz.buffer(0.8).contains(Point(t_[1], t_[2])):
        continue
    _s, _o = s_off(t_[1], t_[2])
    _m = min((AUD_SIDE_MOUTH, AUD_YARD_STRIP), key=lambda m_: abs(_s - (m_[1] + m_[2]) / 2))
    _s = _m[1] - 2.0 if _s - _m[1] < _m[2] - _s else _m[2] + 2.0
    t_[1:3] = [round(v_, 2) for v_ in along_raw(_s, _o)[:2]]
    t_[5:] = [tuple(round(v_, 2) for v_ in along_rng(_s, _o)[:2])]          # (rxy: the same spot by the first line)
    _nf = (_nf[0] - 1, *_nf[1:])
shrubs[:] = [s_ for s_ in shrubs if not _sz.buffer(0.5).contains(Point(s_[1], s_[2]))]
props[:] = [p_ for p_ in props if not _sz.contains(Point(p_[1], p_[2]))]
cars[:] = [c_ for c_ in cars if not _sz.buffer(1.0).contains(Point(c_[1], c_[2]))]
print('대강당 북쪽 곁길 · 별관 앞마당 어귀: cleared (trees moved, shrubs, props, cars)', -_nf[0],
      _nf[1] - len(shrubs), _nf[2] - len(props), _nf[3] - len(cars), '- s %.1f - %.1f, %.1f - %.1f' % (*AUD_SIDE_MOUTH[1:], *AUD_YARD_MOUTH[1:]))
out['paths'].append(dict(kind='footway', w=round(BK_WALK[2] - BK_WALK[1], 1),
                         pts=[[round(v_, 1) for v_ in along_raw(_bk_s, o_)[:2]] for o_ in (E_WALK, _bk_off - 1.0)]))
# 정문 동쪽 잔디 주차 (LOT_C_CARS): photo A's pale car park under them, asphalt (_ga below), from just in front of the
# red car back 16 m (LOT_C_BACK: the cars on it behind the red one, the farthest 13.7 m back; it was 10.5 m), and the
# trees that stood in a car moved out of it, off the car park's edge (the photo's shade trees stand round it).  Not the
# zelkova whose trunk stands by the red car's nose: its foot (1610, 932.5 px) is 2.0 m west of the red car's wheels'
# middle on the line of its near wheels (+- 0.4 m for +- 2 px), beside the car, not in it (it had been moved 1.9 m
# out in front of the row as if it stood in the car)
LOT_C_TRUNK = photo_ground(1610, 932.5)
_lc_len = max(_lc_span, 2.8 + 5.6 * (len(LOT_C) - _lc_nf - 1), 4.6 * (len(LOT_C) - 1)) + 3.5    # (over the old row's trodden earth)
LOT_C_PAD = Polygon([tuple(_lc0 + _lcd * u_ + _lcn * v_) for u_, v_ in ((-3.5, -1.4), (_lc_len, -1.4), (_lc_len, 16.0), (-3.5, 16.0))])
_rlc = random.Random(1997 + 12)
_q = _lc0 + _lcd * LOT_C_VAN[0] + _lcn * LOT_C_VAN[1]
cars.append(['sedan', round(float(_q[0]), 2), round(float(_q[1]), 2), round(math.atan2(-_lcn[1], -_lcn[0]) + _rlc.uniform(-.06, .06), 3),
             _rlc.randrange(8)])
_lct = []
for c_ in cars:
    if not LOT_C_PAD.contains(Point(c_[1], c_[2])):
        continue
    _ct_ = np.array([math.cos(c_[3]), math.sin(c_[3])])
    _cn_ = np.array([-_ct_[1], _ct_[0]])
    for t_ in trees:
        if math.hypot(t_[1] - LOT_C_TRUNK[0], t_[2] - LOT_C_TRUNK[1]) < 0.6:
            continue
        d_ = np.array([t_[1] - c_[1], t_[2] - c_[2]])
        u_, v_ = float(d_ @ _ct_), float(d_ @ _cn_)
        if abs(u_) < 2.35 + 0.6 and abs(v_) < 0.88 + 0.6:
            q_ = np.array([t_[1], t_[2]])
            _back = float((np.array([c_[1], c_[2]]) - _lc0) @ _lcn) > 4.0
            v_to = 16.0 + 0.8 if _back else -1.4 - 0.8               # (beyond the car park's far edge, or before it)
            q_ = q_ + _lcn * (v_to - float((q_ - _lc0) @ _lcn))
            _lct.append((t_[0], round(t_[1], 1), round(t_[2], 1)))
            t_[1], t_[2] = round(float(q_[0]), 2), round(float(q_[1]), 2)
            del t_[5:]
park_lot('정문 동쪽 잔디', None)['stalls'] = [[c_[1], c_[2], c_[3]] for c_ in cars if LOT_C_PAD.contains(Point(c_[1], c_[2]))]
print('정문 동쪽 잔디 주차: trees moved out of the cars', _lct)
# 교육관 북쪽 마당 (the 2003 autumn photo: asphalt, yellow lines, the cars nose in towards the hall): the yard paved
# from the hall's apron out to the drive, between its east corner and the flight's paved foot; the game had a lawn
# island there under the cars (_ga below)
_gyt0, _gyn0 = np.array([-0.969, 0.248]), np.array([0.248, 0.969])
GY_YARD = Polygon([tuple(np.array([44.15, 345.23]) + _gyt0 * u_ + _gyn0 * v_) for u_, v_ in ((-3.0, 3.3), (11.4, 3.3), (11.4, 15.5), (-3.0, 15.5))])
_nf = (len(LATE_GONE_TREES), len(shrubs))
LATE_GONE_TREES |= {i_ for i_, t_ in enumerate(trees) if GY_YARD.buffer(0.5).contains(Point(*rxy(t_)))}
shrubs[:] = [s_ for s_ in shrubs if not GY_YARD.buffer(0.4).contains(Point(s_[1], s_[2]))]
print('교육관 북쪽 마당: cleared (trees, shrubs)', len(LATE_GONE_TREES) - _nf[0], _nf[1] - len(shrubs))


# the car parks with no painted line in their sources: 독수리상 서쪽 옆길 (photo A), 교육관 북쪽 마당 (the 2003 photo's
# yellow line runs along the lawn's kerb at the cars' noses, the bays' own lines do not show), 정문 동쪽 잔디 (above)
park_lot('독수리상 서쪽 옆길', None)['stalls'] = [[round(float(x_), 2), round(float(y_), 2), round(float(a_ + math.pi / 2), 3)]
                                              for x_, y_, a_ in LOT_W]
park_lot('교육관 북쪽 마당', None)['stalls'] = [[*[round(float(v_), 2) for v_ in np.array([44.15, 345.23]) + _gyt0 * s_ + _gyn0 * 8.2],
                                             round(math.atan2(-_gyn0[1], -_gyn0[0]), 3)] for s_ in (1.8, 4.4, 7.0, 9.6)]
park_lot('학생회관 별관 앞', None)['stalls'] = [[c_[1], c_[2], c_[3]] for c_ in ANNEX_CARS]   # (ANNEX_YARD, above)
# 핀슨관 옆 (PINSON above, reference/고증/2.9): a row of stalls nose in off the road's south side, where the 2008 skyview
# has a dozen cars; four of them taken, the rest for the cars that come up 백양로 (TRAFFIC)
_lot = park_lot('핀슨관 옆', 'white')
_pst = park_row(_lot, PINSON['o'] + PINSON['n'] * PINSON['off'], PINSON['t'], PINSON['n'], PINSON['k'], w=PINSON['w'], d=PINSON['d'])
_rpn = random.Random(1997 + 2901)
PINSON_FREE = []
for k_, (x_, y_, h_) in enumerate(_pst):
    if k_ in (1, 4, 5, 8):
        cars.append([_rpn.choice(['sedan', 'sedan', 'sedan', 'hatch']), round(x_, 2), round(y_, 2),
                     round(h_ + _rpn.uniform(-.04, .04), 3), _rpn.randrange(8)])
    else:
        PINSON_FREE.append((round(x_, 2), round(y_, 2)))
# 공학원 공사장 앞 (GW_LOT, GW_ROW above; the 1997 vertical photos): the car park's rows as the photos have them (no line
# shows at 0.54 m a pixel), noses north and south, and the row nose in along the north hoarding either side of its
# gate.  Their own random stream
_lot = park_lot('공학원 공사장 앞', None)
_rgw = random.Random(1997 + 4404)
_gw_h = math.atan2(_gc_, -_gs_)                         # (up the site's v)
for u_, v_, d_ in [(60.0, 75.5, 1), (62.8, 75.5, 1)] + [(u_, 79.5, 1) for u_ in (68.0, 70.8, 73.6, 78.2)] + \
        [(74.7 + 2.8 * k_, 69.0, -1) for k_ in range(6)] + [(72.5 + 2.9 * k_, 63.3, 1) for k_ in range(4)] + \
        [(75.0, 58.9, -1), (78.0, 58.9, -1)] + [(u_, 84.3, 1) for u_ in np.arange(12.5, 53.0, 2.9)] + \
        [(u_, 84.3, 1) for u_ in np.arange(-14.0, 1.0, 2.9)]:
    x_, y_ = site_xy(float(u_), v_)
    h_ = _gw_h + (0.0 if d_ > 0 else math.pi) + (0.45 if v_ > 84 else 0.0)
    _lot['stalls'].append([round(x_, 2), round(y_, 2), round(h_, 3)])
    if _rgw.random() < 0.85:
        cars.append([_rgw.choice(['sedan', 'sedan', 'sedan', 'hatch']), round(x_, 2), round(y_, 2),
                     round(h_ + _rgw.uniform(-.05, .05), 3), _rgw.randrange(8)])
cars += SCI_CARS                    # (과학관's court and yard: last, so that no other car changes its model)
# (the oil under the stalls of the car parks that decal_spots, above, does not know: 백양관 북쪽; their own random
# numbers, at the end of the decals' list, so that no other decal moves)
_rpo = random.Random(1997 + 4581)
for l_ in PARK_LOTS:
    if l_['name'] not in ('백양관 북쪽',):
        continue
    for x_, y_, h_ in l_['stalls']:
        if _rpo.random() < 0.8:
            f_ = _rpo.uniform(0.9, 1.5)
            out['decals'].append(['oil', round(x_ + math.cos(h_) * f_, 2), round(y_ + math.sin(h_) * f_, 2),
                                  round(_rpo.uniform(0, 2 * math.pi), 3), round(_rpo.uniform(0.6, 1.1), 2)])
print('주차 칸:', ', '.join('%s %d stalls %d lines' % (l_['name'], len(l_['stalls']), len(l_['lines'])) for l_ in PARK_LOTS))
out['parking'] = [dict(name=l_['name'], paint=l_['paint'], w=l_['w'], stalls=l_['stalls'], lines=l_['lines'])
                  for l_ in PARK_LOTS]
# 신촌 로터리: 연세로 on south of gate_town's rows to the junction, its corners and the town south of the grid; the
# walks there open to the walker (barrier round them), the lamps, the subway's entrances, the town's ground map
ROT = sinchon_rotary.layout(ROT_GEO, out['town'], TOWN, ground_t, None)
props += ROT['props']
shrubs += ROT['shrubs']
trees += ROT['trees']                       # (at the list's end: the web picks each tree's model by its place in it)
for _i in sorted(LATE_GONE_TREES, reverse=True):     # (백양관 앞 길 · 북쪽 주차장, 교육관 북쪽 마당, above)
    trees[_i] = trees[-1]
    trees.pop()
_n_drop = 0
for t_ in DROP_TREES:                               # (under the moved 백양로, #162: the same way)
    _i = next((i_ for i_, q_ in enumerate(trees) if q_ is t_), None)
    if _i is not None:
        trees[_i] = trees[-1]
        trees.pop()
        _n_drop += 1
print('trees under the moved 백양로 cleared:', _n_drop, 'of', len(DROP_TREES))
trees += BK_ISLAND_TREES                    # (백양관 북쪽 주차장 앞 섬: last, so that no other tree changes its model)
trees += ANNEX_TREES                        # (학생회관 별관 앞 섬의 소나무: after every other tree, none changes its model)
trees += YJ_NEW_TREES                       # (용재관 북쪽: the same)
trees += DW_NEW_TREES                       # (대우관 뒤: the same)
trees += FIELD_NEW_TREES                    # (대운동장 둘레 숲: the same)
trees += LIB97_NEW_TREES                    # (중앙도서관 앞: the same)
trees += UTS_NEW_TREES                      # (연합신학대학원: where OSM's later outline stood)
markers += ROT['markers']
out['colliders'] += ROT['colliders']
out['paths'] += ROT['paths']
sinchon_rotary.town_splat(ROT['paints'], os.path.join(ROOT, 'web/public/assets/textures/ground_splat_town.png'))


def _ypaint(geoms, img, width=None):
    dr_ = ImageDraw.Draw(img)
    for g_ in geoms:
        if width:
            dr_.line([to_px(x, y) for x, y in g_], fill=255, width=max(1, int(width / SPLAT['res'])), joint='curve')
            SPLAT_OPS.append(('line', _YN[id(img)], [tuple(c[:2]) for c in g_], max(1, int(width / SPLAT['res'])), False))
            continue
        for p_ in (g_.geoms if hasattr(g_, 'geoms') else [g_]):
            if p_.geom_type == 'Polygon':
                dr_.polygon([to_px(x, y) for x, y in p_.exterior.coords], fill=255)
                SPLAT_OPS.append(('poly', _YN[id(img)], list(p_.exterior.coords), 255))


_yz, _yg, _yp = (Image.new('L', (SW, SH), 0) for _ in range(3))
_YN = {id(_yz): '_yz', id(_yg): '_yg', id(_yp): '_yp'}
_ypaint([_yclear], _yz)
_ypaint([YJ_GARDEN.difference(_kept)], _yg)
_ypaint([YJ_EAST_LAWN], _yg)                   # (용재관 북동쪽: the 2015 forecourt's paving out; YJ_LOT, YJ_BRANCH below)
_ypaint([BK_ISLAND], _yg)                   # (백양관 북쪽 주차장 앞 섬: lawn over the strip's place)
_ypaint([ANNEX_ISLAND], _yg)                 # (학생회관 별관 앞 섬: lawn, the later walks across it cleared)
_ypaint([p_.buffer(5.5) for p_ in FIELD_GONE_SITES], _yg)    # (대운동장 북쪽 끝: the two later halls' aprons out)
_ypaint([GONGWON_SITE.buffer(0.5), GW_LOT, GW_ROW, GW_YARD], _yg)    # (공학원 공사장: OSM's later roads and walks across it out)
# (the aprons of the halls left out or moved since the planting was laid, GONE_LAWN · SITES_NEW_1997: lawn where no hall of
# 1997 stands; 과학관's court paved to the bank's foot and under its flight)
_old_aprons = unary_union([Polygon(g_['footprint']) for g_ in RND_GHOSTS if g_['id'] in GONE_LAWN] +
                          [q_ for pid_, _, _, _, q_ in OLD_HALLS if pid_ in (990010, 990011, 990012)]).buffer(4.2)
_ypaint([_old_aprons.difference(unary_union(LATE_SITES).buffer(3.5))], _yg)
_ypaint([SCI_COURT.union(flight_zone(SCI_DOOR, SCI_N, 8.8, 7.0))], _yp)
_ypaint([sci_poly([(-121.0, -12.0), (-86.0, 15.5), (-88.5, 18.6), (-123.5, -8.9)])], _yg)   # (the hedge's bed: SCI_YARD)
_ypaint([Polygon(b_['footprint']).buffer(3.5, join_style=2) for b_ in YONGJAE_BUILDINGS] +
        [yongjae_poly(-4.5, 2.8, -1.0, 21.0)], _yp)
_ypaint([YJ_WALK], _yp, width=2.6)
_ypaint([LIB97_ZONE.difference(LIB97_TERRACE.buffer(-0.2))], _yg)   # (중앙도서관 앞: lawn; its walks and plaza below, _gp · _ga)
_ypaint([UTS_LAWN], _yg)                     # (연합신학대학원: OSM's outline and its apron lawn again; the 1997 hall's: _gp)
if UTS_WALK:
    _ypaint([UTS_WALK], _yp, width=2.6)
_yz = ndimage.gaussian_filter(np.array(_yz, np.float32) / 255.0, 0.7)
_yg = ndimage.gaussian_filter(np.array(_yg, np.float32) / 255.0, 0.7)
spl[..., 0] *= 1.0 - _yg
spl[..., 1] *= (1.0 - _yz) * (1.0 - _yg)
spl[..., 2] *= (1.0 - _yz) * (1.0 - _yg)
spl[..., 1] = np.minimum(np.maximum(spl[..., 1], ndimage.gaussian_filter(np.array(_yp, np.float32), 0.7)), 255 - spl[..., 0])
# the 1997 sites: 제2인문관's bare earth (the rest of its apron and its walks left as they were), 미우학사's apron round
# its own walls
_gd, _gp = Image.new('L', (SW, SH), 0), Image.new('L', (SW, SH), 0)
_YN[id(_gd)], _YN[id(_gp)] = '_gd', '_gp'       # (redrawn sharp for the game's map: splat_aa below)
_ypaint([p_.buffer(2.0) for n_, p_ in GONE_SITES if n_] + [GONGWON_SITE.buffer(0.5), GW_YARD], _gd)
# (and 경영학교실단's front flight: paved to 2 m past its foot; 교육관's north flight, which comes down 9.5 m out of
# the gable onto the yard (blender/landmarks.py gyoyuk_north_flight): paved round its foot and the low wall past it)
_bkc = _bk_a + BK_T * 45.66
_gyc, _gyt, _gyn = np.array([30.29, 348.78]), np.array([-0.969, 0.248]), np.array([0.248, 0.969])
_ypaint([p_.buffer(3.5, join_style=2) for p_ in LATE_SITES]
        + [Polygon([tuple(_bkc + BK_T * u + BK_N * v) for u, v in ((-4.5, 0.0), (4.5, 0.0), (4.5, 7.1), (-4.5, 7.1))])]
        + [Polygon([tuple(_gyc + _gyt * u + _gyn * v) for u, v in ((-2.6, 8.4), (2.6, 8.4), (2.6, 12.6), (-2.6, 12.6))])], _gp)
# 백주년기념관 앞 테라스 (CENT_TERRACE): the apron paved out to the sidewalk, and under the flights, landings and the
# porch's level to just inside their side walls and the retaining wall (so no kerb runs along them)
_ypaint([Polygon([ct_xy(s_, sec_[0][0] + 0.3)[:2] for s_, sec_ in _ap] + [ct_xy(s_, sec_[2][0] - 0.25)[:2] for s_, sec_ in _ap[::-1]]),
         Polygon([ct_xy(s_, d_)[:2] for s_, d_ in ((8.6, CT_FOOT_D + 0.1), (35.35, CT_FOOT_D + 0.1), (35.35, 0.3), (8.6, 0.3))])], _gp)
# 중앙도서관 앞 (LIB97): the beds' walks paved, the ground under the terrace too (no grass under its slab); asphalt (_ga
# below) the plaza round its island (the 2008 - 2010 roadview), the drive north of the beds and the lane along the
# shrub band, which is the side road west of the eagle (SIDE_W, the grey drive of photo A) run on past the hall's front
# to the north drive: the photos have cars parked along it
_ypaint([LIB97_TERRACE, LIB97_OUTER] + list(LIB97_SLANT.geoms if hasattr(LIB97_SLANT, 'geoms') else [LIB97_SLANT]), _gp)
# 의료원: the two sites left out without a name are the car parks round the old halls (asphalt, their aprons paved)
_ga = Image.new('L', (SW, SH), 0)
_YN[id(_ga)] = '_ga'
_ypaint([p_ for n_, p_ in GONE_SITES if not n_ and not any(p_.equals(q_) for q_ in _gone_lawn)], _ga)
_li = LIB97['island']
_ypaint([lf_rect(LIB97['plaza'][0], _li[0], LIB97['depth'], _l9st + 0.4), lf_rect(_li[1], LIB97['plaza'][1], LIB97['depth'], _l9st + 0.4),
         lf_rect(_li[0] - 0.1, _li[1] + 0.1, LIB97['depth'], _li[2]), lf_rect(_li[0] - 0.1, _li[1] + 0.1, _li[3], _l9st + 0.4),
         LIB97_NORTH, LIB97_WALK], _ga)         # (중앙도서관 앞 광장 · 북쪽 찻길 · 관목 띠를 따르는 찻길)
_ypaint([JUNC], _ga, width=JUNC_W)            # (독수리상 서쪽 옆길이 백양로와 만나는 길)
_ypaint([SCI_YARD.difference(unary_union([Polygon(b_['footprint']) for b_ in LATE_HALLS if b_['id'] in (990060, 990061)]).buffer(0.5))], _ga)
# 용재관's car park and the drive to 노천극장 (YJ_LOT, YJ_BRANCH), a paved strip along the walls
_ypaint([YJ_LOT.difference(unary_union([Polygon(b_['footprint']).buffer(1.0) for b_ in YONGJAE_BUILDINGS])),
         YJ_BRANCH.buffer(3.0)], _ga)
# 대강당 앞 돌계단: the forecourt's paving runs on to the head of the flight (the 2009 photo: cars parked at its top)
_ypaint([Polygon([tuple(_fo + _fu * u_ + _fv * v_) for u_, v_ in ((-4.5, AUD_FLIGHT['run'] - 0.2), (4.5, AUD_FLIGHT['run'] - 0.2),
                                                                   (6.0, 26.0), (-6.0, 26.0))])], _ga)
# 대강당 앞: the terrace and the drive up to it asphalt, and the yard before 학생회관 별관 where the court first stood
# (the 1994 aerial photo: one paved yard from 별관's foot to the hall)
AUD_YARD = unary_union([AUD_RAMP_CW, AUD_RAMP_WALK, AUD_TERRACE.buffer(-1.0), court_poly(1.0, COURT_OLD),
                        AUD_UPPER_POLY]).difference(bline.buffer(ROAD_HALF)).difference(AUD_BANK_POLY) \
    .difference(AUD_RAMP_BAND).difference(unary_union(AUD_TREE_BEDS))
_ypaint([AUD_YARD], _ga)
_ypaint([AUD_SIDE_POLY], _ga)                 # (대강당 북쪽 곁길 어귀 · 별관 앞마당 어귀)
_ypaint([ENG_COURT], _ga)                     # (제1공학관 앞 진입로)
# 찻길 (TRAFFIC, its middle line TR_CENTRE above): the two lanes, the car park's round, the loop the game reads
# (that was the cars' loop till the alumnus's word on it: the drive itself stays, levelled and paved; the cars take
# the outer roads, TR_E and TR_W above)
def _tr_bez(p0, c, p1, n=9):
    p0, c, p1 = (np.asarray(q_, float)[:2] for q_ in (p0, c, p1))
    return [[round(float(v_), 2) for v_ in (1 - t_) ** 2 * p0 + 2 * t_ * (1 - t_) * c + t_ ** 2 * p1] for t_ in np.linspace(0, 1, n)]


def _tr_loop(loop):
    """a loop's line every 1.25 m: its points and the speed limit at each"""
    ll_ = LineString([q_[:2] for q_ in loop])
    lc_ = np.concatenate([[0.0], np.cumsum([math.dist(a_[:2], b_[:2]) for a_, b_ in zip(loop[:-1], loop[1:])])])
    n_ = int(round(ll_.length / 1.25))
    pts_, v_ = [], []
    for k_ in range(n_ + 1):
        s_ = ll_.length * k_ / n_
        q_ = ll_.interpolate(s_)
        pts_.append([round(q_.x, 2), round(q_.y, 2)])
        v_.append(float(loop[min(len(loop) - 1, int(np.searchsorted(lc_, s_)))][2]))
    return pts_, v_


# east: up the road's right-hand side, left off the road along 대우관's north side into the car park's west aisle, along
# the lane before the hall's back, up the east aisle and right onto the road again (no car crosses another's way),
# back on the other side.  A stall (campus.json traffic.loops[].stalls): the loop's point i where a car turns off it,
# its way in to the stall's middle (a), its way out backwards (b) to the loop's point j.  From an aisle a car turns
# in nose first and backs out the way it came, then drives on along the aisle.
_eu = [(*(q_ - n_ * o_), v_) for q_, n_, o_, v_ in zip(TR_E, TR_EN, TR_EO, TR_EV)]
_edn = [(*(q_ + n_ * o_), v_) for q_, n_, o_, v_ in zip(TR_E, TR_EN, TR_EO, TR_EV)]
# (대우관 뒤, DAEWOO_BACK: left off the road into the upper car park's mouth on its right-hand side, down the west
# aisle past the short row, round at the south end before the row along the wall, up the east aisle past the long row
# and right onto the road again)
_mq, _md = (np.array(q_) for q_ in DAEWOO_BACK['mouth'])
_mr = np.array([_md[1], -_md[0]])                                       # (to the right going in: south-west)
_me = lambda s_, o_: dw_xy(*(_mq + _md * s_ + _mr * o_))
_lv = DAEWOO_BACK['turn_v']
_kw = min(range(TR_EKH + 10, len(TR_E)), key=lambda k_: math.dist(_eu[k_][:2], dw_xy(38.4, 89.3)))      # 5 m short of the mouth
_ke = min(range(TR_EKH + 10, len(TR_E)), key=lambda k_: math.dist(_edn[k_][:2], dw_xy(39.9, 90.7)))    # and 7 m past it
_lot = _fillet([_eu[_kw - 9][:2], _eu[_kw][:2], _me(6.0, 1.5), _me(16.0, 0.6), dw_xy(TR_E_AISLES[0], 68.0), dw_xy(TR_E_AISLES[0], _lv),
                dw_xy(TR_E_AISLES[1], _lv), dw_xy(TR_E_AISLES[1], 66.0), _me(17.0, -1.4), _me(6.0, -1.5), _edn[_ke][:2], _edn[_ke - 9][:2]],
               [0, 4.0, 4.0, 5.0, 4.0, 2.6, 2.6, 4.0, 5.0, 4.0, 4.0, 0])
_eloop = _eu[:_kw - 9] + [(*q_, TR_V['lot']) for q_ in _lot] + _edn[:_ke - 9][::-1]
_epts, _ev = _tr_loop(_eloop)
_ep = np.array(_epts)
_euv = [dw_uv(q_) for q_ in _epts]
_occ = [(c_[1], c_[2]) for c_ in cars]
_dwl = next(l_ for l_ in PARK_LOTS if l_['name'] == '대우관 뒤')
_estalls = []
for s_ in _dwl['stalls']:
    if any(math.dist(s_[:2], q_) < 1.5 for q_ in _occ):
        continue
    u_, v_ = dw_uv(s_[:2])
    for au_, sg_ in ((TR_E_AISLES[0], -1.0), (TR_E_AISLES[1], 1.0)):       # (down the west aisle, up the east one)
        if 3.5 < (au_ - u_) * -sg_ < 6.8 and _lv + 6.0 < v_ < 69.0:        # (the short row west of the west aisle, the long one east of the east)
            cand_ = [k_ for k_ in range(len(_epts)) if abs(_euv[k_][0] - au_) < 0.3 and _lv + 1.0 < _euv[k_][1] < 70.0]
            i_ = min(cand_, key=lambda k_: abs(_euv[k_][1] - (v_ - sg_ * 5.8)))      # 5.8 m before the stall
            in_ = _tr_bez(_epts[i_], dw_xy(au_, v_), s_[:2])
            _estalls.append(dict(i=i_, j=i_, a=in_, b=in_[::-1]))
_estalls.sort(key=lambda d_: d_['i'])
# west: up the drive past 스팀슨관, round the island to the left and down the road before 한경관 to the stalls beside
# 핀슨관; a car turns left across the road into its stall, backs out round to the west and drives off east again
_wu = [(*(q_ - n_ * o_), v_) for q_, n_, o_, v_ in zip(TR_W, TR_WN, TR_WO, TR_WV)]
_wdn = [(*(q_ + n_ * o_), v_) for q_, n_, o_, v_ in zip(TR_W, TR_WN, TR_WO, TR_WV)]
_wpts, _wv = _tr_loop(_wu + _wdn[::-1])
_wp = np.array(_wpts)
_wku = int(np.argmin(np.hypot(*(_wp - np.array(_wu[-1][:2])).T)))             # (the far end, where the two sides meet)
_wstalls = []
for x_, y_ in PINSON_FREE:
    kc_ = int(round(_wls.project(Point(x_, y_))))
    i_ = int(np.argmin(np.hypot(*(_wp[:_wku] - np.array(_wu[kc_ - 8][:2])).T)))
    j_ = _wku + int(np.argmin(np.hypot(*(_wp[_wku:] - np.array(_wdn[min(len(_wdn) - 1, kc_ + 5)][:2])).T)))
    _wstalls.append(dict(i=i_, j=j_, a=_tr_bez(_wpts[i_], _wu[kc_], (x_, y_)), b=_tr_bez((x_, y_), _wdn[kc_], _wpts[j_])))
TRAFFIC = dict(s_out=TR_S0, v_lot=TR_V['lot'],
               loops=[dict(name='east', pts=_epts, v=_ev, stalls=_estalls), dict(name='west', pts=_wpts, v=_wv, stalls=_wstalls)])
out['traffic'] = TRAFFIC
print('traffic: east loop %.0f m, %d points, %d free stalls on its aisles; west loop %.0f m, %d points, %d stalls' % (
    LineString(_epts).length, len(_epts), len(_estalls), LineString(_wpts).length, len(_wpts), len(_wstalls)))
# the 삼거리: the drive's mouth in 백양로's west side.  It was a gap in the kerb and the verge only (GAPS: where OSM's
# drive crosses), the sidewalk's paving running on across it, so the cars would cross a paved walk; the 2008 roadview
# (2381332, looking west over the 삼거리) has asphalt from the carriageway into the drive, kerbed lawn corners either
# side.  A mouth as at the gate's side road (blender/road.py mouths: the verge, the sidewalk and the planting strip
# stop, the asphalt runs out flush), wide enough for the two lanes turning through it on the slant; the verge's and the
# strip's shrubs in it go (the planting keeps reading GAPS, so no other draw changes)
TR_MOUTH = [1, round(TR_SJ - 3.0, 1), round(TR_SJ + 8.4, 1), 3.0, 1.5]
out['baekyangro']['mouths'].append(TR_MOUTH)
out['baekyangro']['gaps'] = [g_ for g_ in out['baekyangro']['gaps'] if not (g_[1] == TR_MOUTH[0] and TR_MOUTH[1] - 4 < g_[0] < TR_MOUTH[2] + 4)]
_n0 = len(shrubs)
shrubs[:] = [s_ for s_ in shrubs if not (TR_MOUTH[1] + 0.5 < s_at(s_[1], s_[2]) < TR_MOUTH[2] + 0.3
                                         and E_CURB0 - 0.5 < s_off(s_[1], s_[2])[1] * TR_MOUTH[0] < ROAD_HALF + 0.8)]
print('traffic: the 삼거리 mouth', TR_MOUTH, 'shrubs taken out', _n0 - len(shrubs), 'trees in it',
      [t_[:3] for t_ in trees if TR_MOUTH[1] - 0.6 < s_at(t_[1], t_[2]) < TR_MOUTH[2] + 0.6
       and E_CURB0 < s_off(t_[1], t_[2])[1] * TR_MOUTH[0] < ROAD_HALF + 1.0])
_ypaint([TR_CENTRE[:int(TR_SJC) + 24]], _ga, width=7.4)       # (the drive's asphalt out to meet it, both lanes' width)
# (한경길 어귀: the corner the cars cut on the 교육관 side, a metre of asphalt inside OSM's angle)
_ypaint([[q_ for q_ in TR_CENTRE if math.dist(q_, (40.0, 301.4)) < 12.0]], _ga, width=5.6)
# the east fork's mouth the same way (2008 skyview: one sheet of asphalt from the carriageway into both forks)
TR_MOUTH_E = [-1, round(TR_SJ - 7.0, 1), round(TR_SJ + 4.5, 1), 3.0, 1.5]
out['baekyangro']['mouths'].append(TR_MOUTH_E)
out['baekyangro']['gaps'] = [g_ for g_ in out['baekyangro']['gaps'] if not (g_[1] == TR_MOUTH_E[0] and TR_MOUTH_E[1] - 4 < g_[0] < TR_MOUTH_E[2] + 4)]
_n0 = len(shrubs)
shrubs[:] = [s_ for s_ in shrubs if not (TR_MOUTH_E[1] + 0.5 < s_at(s_[1], s_[2]) < TR_MOUTH_E[2] + 0.3
                                         and E_CURB0 - 0.5 < s_off(s_[1], s_[2])[1] * TR_MOUTH_E[0] < ROAD_HALF + 0.8)]
print('traffic: the east mouth', TR_MOUTH_E, 'shrubs taken out', _n0 - len(shrubs))
# the asphalt under the two loops where the roads' own did not reach: the forks' first metres, the turn round the
# island, the bend north-east of 대우관 (the wedge between the two roads there), the car park's mouths, 핀슨관's stalls
_ypaint([[tuple(q_) for q_ in TR_E[:int(_esj) + 26]]], _ga, width=7.4)
_ypaint([[tuple(q_) for q_ in TR_E[TR_EKH - 42:TR_EKH + 24]]], _ga, width=8.6)
_ekc = int(round(_els.project(Point(212.6, 356.4))))               # (the corner where the road under 청송대 goes on east)
_ypaint([[tuple(q_) for q_ in TR_E[_ekc - 16:_ekc + 22]]], _ga, width=8.6)
_ypaint([_lot[:10], _lot[-10:]], _ga, width=5.6)
_wki = int(round(_wls.project(Point(-14.5, 204.6))))
_ypaint([[tuple(q_) for q_ in TR_W[_wki:int(round(_wls.project(Point(-36.1, 210.7))))]]], _ga, width=7.4)
_ypaint([[tuple(q_) for q_ in TR_W[int(round(_wls.project(Point(-62.2, 138.4)))):]]], _ga, width=6.4)
_ypaint([PINSON_LOT], _ga)
# what stands in the cars' way off 백양로: the shrubs and the props go, a tree moves aside in its place in the list
# (web/src/world.js picks the trees' models by their order)
_troad = unary_union([LineString([tuple(q_) for q_ in TR_E[TR_EK0:]]).buffer(3.6), LineString([tuple(q_) for q_ in TR_W[TR_K0:]]).buffer(3.6),
                      LineString(_lot).buffer(2.4), PINSON_LOT.buffer(0.5)])
_n0 = (len(shrubs), len(props))
shrubs[:] = [s_ for s_ in shrubs if not _troad.contains(Point(s_[1], s_[2]))]
props[:] = [p_ for p_ in props if not _troad.contains(Point(p_[1], p_[2]))]
_tmoved = []
for t_ in trees:
    q_ = Point(t_[1], t_[2])
    if _troad.buffer(0.9).contains(q_):
        n_ = shapely.ops.nearest_points(_troad.buffer(1.6).exterior if _troad.buffer(1.6).geom_type == 'Polygon' else _troad.buffer(1.6).boundary, q_)[0]
        _tmoved.append((t_[0], t_[1], t_[2], round(n_.x, 2), round(n_.y, 2)))
        t_[1], t_[2] = round(n_.x, 2), round(n_.y, 2)
print('traffic: on the roads, shrubs taken out %d, props %d, trees moved aside %d' % (_n0[0] - len(shrubs), _n0[1] - len(props), len(_tmoved)), _tmoved)
print('traffic: 삼거리 s %.1f, leaves 백양로 at %.1f' % (TR_SJ, TR_S0))
# 대우관's west side: the asphalt on the drive's new line and along the hall's back to the car park, paving in the
# place of the old line's along the wall (a walk of 2 m at the wall's foot); the shrubs of the old kerb line go to
# the new one's
_dwl = LineString(TR_CENTRE[TR_KDW - 22:])
_dws = _dwl.buffer(3.1, cap_style='flat')
_ypaint([_dws], _ga)
DW_WALL_WALK = Polygon([dh_xy(u_, v_) for u_, v_ in ((DAEWOO['u0'] - 3.0, DAEWOO['wing_v'][0]), (DAEWOO['u0'] + 2.0, DAEWOO['wing_v'][0]),
                                                     (DAEWOO['u0'] + 2.0, 27.4), (DAEWOO['u0'] - 3.0, 27.4))]).difference(_dws)
_dw_moved = []
for s_ in shrubs:
    q_ = Point(s_[1], s_[2])
    if _dwl.distance(q_) < 3.9 and not _dws.buffer(0.8).disjoint(q_):
        f_ = _dwl.project(q_)
        a_, b_ = np.array(_dwl.interpolate(max(0.0, f_ - 0.5)).coords[0]), np.array(_dwl.interpolate(min(_dwl.length, f_ + 0.5)).coords[0])
        n_ = np.array([-(b_ - a_)[1], (b_ - a_)[0]]) / np.linalg.norm(b_ - a_)
        side_ = 1.0 if (np.array([s_[1], s_[2]]) - a_) @ n_ >= 0 else -1.0
        s_[1], s_[2] = (round(float(v_), 2) for v_ in np.array(_dwl.interpolate(f_).coords[0]) + n_ * side_ * 4.1)
        _dw_moved.append(s_[0])
# (the small pine on the island by the car park's way in stood a car's width from the lane: 1.8 m back onto the island,
# in its place in the list)
for k_, t_ in enumerate(trees):
    if t_[0] == 'pine' and math.dist(t_[1:3], (128.96, 520.05)) < 0.05:
        trees[k_] = [t_[0], 128.49, 518.31] + list(t_[3:])
print('daewoo west drive: shrubs moved to its kerbs', len(_dw_moved), 'trees within 3.6 m',
      [t_[:3] for t_ in trees if _dwl.distance(Point(t_[1], t_[2])) < 3.6])
# 대우관 테라스 · 석축에 심은 것 (reference/고증/3.6 「테라스와 석축의 나무」): the hall's own mesh drew them as plain green
# cones, domes and boxes.  They are the campus' clipped shrubs now (blender/shrubs.py), in the hall's frame; the
# planters' soil is a walked face in blender/landmarks.py daewoo_front (`bed`), so they stand on it.  At the list's
# end, with draws of their own.
#  - the wall's planter either side of the podium: a clipped hedge, the row of pointed conifers standing out of it
#  - the tier's planters under it: clipped hedge blocks; the one on the podium: a low clipped block
#  - the stepped planters before the lower flights: a round shrub on each
#  - between the wings: clipped cones along the hall, round shrubs towards the drive
_bd_r = random.Random(1997 + 166)
_bd_ang = DAEWOO['frame']['ang']
DW_BEDS = []


def _dw_bed(kind_, u_, v_, sc_, along_=False):
    DW_BEDS.append([kind_, *dh_xy(u_, v_), round(sc_, 2), round(_bd_ang if along_ else _bd_r.uniform(0, 6.28), 3)])


for _bd_a, _bd_b in ((DAEWOO['tu'][0], DW_UC - DAEWOO['podium']['hw']), (DW_UC + DAEWOO['podium']['hw'], DAEWOO['tu'][1] - 8.0)):
    _bd_n = int(math.ceil((_bd_b - _bd_a - 0.5) / 1.8))
    for _bd_k in range(_bd_n):                                           # (pieces 1.9 m long)
        _dw_bed('hedge_blob', _bd_a + 1.2 + _bd_k * (_bd_b - _bd_a - 2.4) / (_bd_n - 1), DAEWOO['drive'][0] - 1.4, 0.95, True)
    _bd_n = max(2, int((_bd_b - _bd_a) / 3.6))
    for _bd_k in range(_bd_n):                                           # (3.0 - 3.4 m tall)
        _dw_bed('topiary_cone', _bd_a + (_bd_k + 0.5) * (_bd_b - _bd_a) / _bd_n + _bd_r.uniform(-0.15, 0.15), DAEWOO['drive'][0] - 1.05, _bd_r.uniform(1.22, 1.38))
for _bd_s in (-1, 1):
    _bd_a, _bd_b = sorted((DW_UC + _bd_s * 13.3, DW_UC + _bd_s * 23.4))
    for _bd_k in range(5):
        _dw_bed('hedge_blob', _bd_a + 1.35 + _bd_k * (_bd_b - _bd_a - 2.7) / 4, -22.2, 1.05, True)
    for _bd_k in range(4):                                            # (blender/landmarks.py daewoo_front: cw, d_lo)
        _bd_d0, _bd_d1 = DAEWOO['podium']['court'], DAEWOO['podium']['court'] + 19 * 0.30
        _dw_bed('topiary_round', DW_UC + _bd_s * (_bd_d0 + (_bd_d1 - _bd_d0) * (_bd_k + 0.5) / 4), (DAEWOO['podium']['front'] + 2.5 + DAEWOO['podium']['face']) / 2, 0.7)
    _bd_a, _bd_b = sorted((DW_UC + _bd_s * 7.0, DW_UC + _bd_s * (DW_WI - 1.5)))
    for _bd_k in range(5):
        _bd_u = _bd_a + (_bd_k + 0.5) * (_bd_b - _bd_a) / 5
        _dw_bed('topiary_cone', _bd_u + _bd_r.uniform(-0.12, 0.12), -2.4, _bd_r.uniform(1.1, 1.3))
        _dw_bed('topiary_round', _bd_u + _bd_r.uniform(-0.12, 0.12), -8.4, _bd_r.uniform(0.95, 1.12))
for _bd_du in (-1.22, 1.22):
    for _bd_dv in (-1.05, 0.0, 1.05):
        _dw_bed('hedge_low', DW_UC + _bd_du, -21.5 + _bd_dv, 1.35, True)
# (the garden pines: in the round lawn, by the ring where the upper walks leave it, before the podium's ends)
for _bd_e, _bd_n, _bd_sc in ((0.0, 0.0, 1.15), (-8.5, 5.0, 1.0), (8.5, 5.0, 1.05), (-14.5, 10.5, 1.05), (14.5, 10.5, 1.0),
                             (-20.5, 11.5, 1.3), (20.5, 11.5, 1.25)):
    DW_BEDS.append(['pine_cloud', *(round(float(c_), 2) for c_ in SG(_bd_e, _bd_n)), _bd_sc, round(_bd_r.uniform(0, 6.28), 3)])
shrubs += DW_BEDS
print('대우관 테라스 · 석축: clipped shrubs', len(DW_BEDS), {k_: sum(1 for b_ in DW_BEDS if b_[0] == k_) for k_ in sorted({b_[0] for b_ in DW_BEDS})})
_ypaint([BK_LOT, BK_DRIVE, LOT_C_PAD, GY_YARD], _ga)    # (백양관 북쪽 주차장, 정문 동쪽 잔디 주차, 교육관 북쪽 마당)
_ypaint(ANNEX_YARD_HALVES, _ga)               # (학생회관 별관 앞마당)
_ypaint([GW_LOT, GW_ROW], _ga)                # (공학원 공사장 앞 주차장, 북쪽 가림막 앞 줄)
_gw = Image.new('L', (SW, SH), 0)                # (백양관 앞 계단 길: paving over the asphalt laid under 백양로's mesh)
_YN[id(_gw)] = '_gw'
_ypaint([BK_COURT], _gw)
_ypaint([DW_WALL_WALK], _gw)               # (대우관 서쪽 벽 발치: the old line's asphalt along the wall)
_ypaint([AUD_RAMP_WALK.difference(bline.buffer(ROAD_HALF)).difference(AUD_BANK_POLY)], _gp)   # (its walk: paving)
_gd = ndimage.gaussian_filter(np.array(_gd, np.float32), 1.2)
spl[..., 1] *= 1.0 - _gd / 255.0
spl[..., 2] = np.where(_gd > 0, np.minimum(np.maximum(spl[..., 2], _gd), 255.0 - spl[..., 0] - spl[..., 1]), spl[..., 2])
spl[..., 1] = np.minimum(np.maximum(spl[..., 1], ndimage.gaussian_filter(np.array(_gp, np.float32), 0.7)), 255 - spl[..., 0])
_ga = ndimage.gaussian_filter(np.array(_ga, np.float32), 0.7) * (1.0 - ndimage.gaussian_filter(np.array(_gp, np.float32), 0.7) / 255.0)
spl[..., 0] = np.maximum(spl[..., 0], _ga)
spl[..., 1] = np.minimum(spl[..., 1], 255.0 - spl[..., 0])
spl[..., 2] = np.minimum(spl[..., 2], 255.0 - spl[..., 0] - spl[..., 1])
print('yongjae ground: walks', len(paths_out), 'decals', len(out['decals']))
# 대강당 앞 둑 (AUD_BANK_POLY): the bank's slope is the woods' floor under its shrubs (the bank mesh draws the ground's
# own shading: web/src/terrain.js drapeTerrain), no paving of the strip under it, no grass blades
_gb = Image.new('L', (SW, SH), 0)
_YN[id(_gb)] = '_gb'
_ypaint([AUD_BANK_POLY.difference(AUD_FLIGHT_POLY)], _gb)          # (not the flight: its head is paved)
_gbm = ndimage.gaussian_filter(np.array(_gb, np.float32), 0.7) / 255.0
spl[..., 0] *= 1.0 - _gbm
spl[..., 1] *= 1.0 - _gbm
spl[..., 2] = spl[..., 2] * (1.0 - _gbm) + 178.0 * _gbm

# 정문 밖 (tools/gate_town.py): its ground cleared of what OSM's roads and the town's houses had painted there, then
# 성산로, the gate's mouth, 연세로 and the town's alleys (asphalt), the sidewalks (paving) and the banks' slopes (the
# woods' floor, drawn by the bank's own mesh: blender/town.py)
_tl = {k_: Image.new('L', (SW, SH), 0) for k_ in ('clear', 'asphalt', 'pavers', 'dirt')}
for k_, im_ in _tl.items():
    _YN[id(im_)] = '_t' + k_[0]
    _ypaint(TOWN['paints'][k_], im_)


def town_splat(S, c, a, p, d):
    """the town's four layers (0..255) laid on a splat array in place"""
    S *= (1.0 - c / 255.0)[..., None]
    S[..., 0] = np.maximum(S[..., 0], a)
    S[..., 1] = np.minimum(np.maximum(S[..., 1], p), 255.0 - S[..., 0])
    S[..., 2] = np.clip(np.minimum(np.maximum(S[..., 2], d * (170.0 / 255.0)), 255.0 - S[..., 0] - S[..., 1]), 0, 255)


town_splat(spl, *(ndimage.gaussian_filter(np.array(_tl[k_], np.float32), 0.7) for k_ in ('clear', 'asphalt', 'pavers', 'dirt')))

# ---------------------------------------------------------------------------
# The ground map the game reads, and the curbs along its paving
# ---------------------------------------------------------------------------
# The same strokes as spl, anti-aliased (splat_aa): the asphalt and paving as sharp as drawn, the dirt (woods,
# pitches, the old amphitheater) as soft as before, 용재관's ground painted again the same way.  (spl above, binary
# 0.5 m texels blurred, stays as it was for the debug map.)
#
# 섬처럼 놓인 포장 (reference/고증/2.3): today's OSM walks leave bits of paving on the lawns that lead nowhere, a stub
# running a few metres out of another walk to stop in the grass, a lone patch with nothing round it.  The 1997 aerial
# photos and the 2008 - 2011 roadview have none such; their walks join something at both ends.  For the game's map
# only (spl above, which the planting and the decals read, keeps them, so the random draws stay): a walk's end that
# (or OSM's steps, painted as paving) stops in the lawn, clear of every hall (3 m), flight's foot (3 m), landmark (6 m),
# the woods' floor and 백양로, loses its stretch back to where it meets other paving if that is PRUNE_TAIL or less
# (its stroke in SPLAT_OPS cut short, so the edge is drawn again as smooth as the rest), and an end run a few metres
# past a road or walk it crosses goes back to the crossing; a patch under PRUNE_PATCH touching no asphalt, hall or
# flight goes (spl_aa).  The walks the game reads (out['paths']: minimap, crowd) and the decals lose the same
_pav0 = (spl[..., 0] + spl[..., 1] > 127.5) | (np.array(_ga) > 127) | (np.array(_gp) > 127) | (np.array(_yp) > 127) \
    | (np.array(_gw) > 127)
_dirt0 = spl[..., 2] > 127.5
try:
    _ents = json.load(open(os.path.join(ROOT, 'web/public/data/entrances.json')))['entrances']
except (OSError, ValueError, KeyError):
    _ents = []
_halls = [Polygon(b_['footprint']) for b_ in out['buildings'] if b_['style'] != 'city']
# (#151, looked at one by one from above; reference/고증/2.3 「섬처럼 놓인 포장」)
# PRUNE_SCRAP: OSM walks taken out whole, by their two ends: side strands and jogs a few metres off another walk
# PRUNE_TAILS: walk ends cut back whatever they stop near, up to the length given, to where they meet other paving
# (or, False, only to the walk they join: a strip lying along an apron or another walk)
PRUNE_SCRAP = [(((-115.7, -135.7), (-108.5, -138.0)), '도서관 남서쪽 꺾인 길: 3 m 곁의 나란한 가닥'),
               (((-115.7, -135.7), (-116.7, -139.0)), '  〃 가닥과 본 길 사이'),
               (((-116.7, -139.0), (-128.7, -140.8)), '  〃 가닥의 꺾인 끝'),
               (((-96.5, -138.5), (-98.7, -133.6)), '  〃 독수리상 서쪽 옆길 가의 턱진 이음'),
               (((-93.9, -143.0), (-99.9, -137.6)), '  〃'),
               (((-77.8, -158.9), (-81.0, -184.5)), '독수리상과 활천대 사이 반원 길 (2015년 백양누리 정원)'),
               (((-16.7, -413.0), (-28.6, -399.4)), '정문 동쪽 잔디밭으로 드는 계단 (2015년 산책로, EAST_LAWN)'),
               (((179.6, 184.5), (193.2, 198.8)), '옛 노천극장: 1999년 객석 통로 계단이 꼭대기 길을 건너 남은 토막'),
               (((193.2, 198.8), (195.4, 201.1)), '  〃'), (((195.4, 201.1), (190.4, 204.9)), '  〃'),
               (((184.8, 141.7), (200.5, 132.8)), '  〃'), (((178.3, 134.4), (191.0, 125.5)), '  〃')]
PRUNE_TAILS = [((-128.9, 24.1), 30.0, True),    # (도서관 북쪽 길이 서쪽 잔디에서 끝나는 26 m)
               ((146.2, -28.9), 25.0, False),   # (음악관 남쪽 잔디로 나온 두 꼬리: 곁의 포장에 닿아 남았던 것)
               ((162.5, -51.1), 20.0, False),
               ((198.9, 181.3), 12.0, False),   # (옛 노천극장: 동쪽 길로 이어지는 1999년 계단의 객석 쪽 끝)
               ((111.9, 66.2), 45.0, True)]     # (대강당 동쪽 41 m: 2008 · 2010년 스카이뷰에 포장 길 없음)
PRUNE_TAIL = 18.0                                # (12 -> 18 m: the 12 - 18 m tails were all stubs into the lawn)
PRUNE_PATCH = 200.0                              # (60 -> 200 m²: two lone walks of 120 and 155 m², west of 과학관
#                                                   and north of 어린이생활지도연구원, touching nothing)
PRUNE_KEEP = unary_union([p_.buffer(3.0) for p_ in _halls]
                         + [Point(e_['o'][0] + e_['v'][0] * e_['len'], e_['o'][1] + e_['v'][1] * e_['len']).buffer(3.0)
                            for e_ in _ents]
                         + [Point(*l_['pos']).buffer(6.0) for l_ in out['landmarks']]
                         + [bline.buffer(ROAD_HALF + 6.0), TOWN['zone'].buffer(5.0)])
shapely.prepare(PRUNE_KEEP)
_res = SPLAT['res']
_pav_ops = [k_ for k_, op_ in enumerate(SPLAT_OPS) if op_[0] == 'line' and op_[1] == 'pavers' and len(op_[2]) > 1]
_op_a = np.array([SPLAT_OPS[k_][2][0][:2] for k_ in _pav_ops])
_op_b = np.array([SPLAT_OPS[k_][2][-1][:2] for k_ in _pav_ops])
PRUNED = []                                           # (the stretches taken off: the decals left on them go too)
# (#151) A walk's end that lies on another walk or road (within its half width + 0.3 m of its centre line), and that
# one still painted there, is not a tail.  The raster test alone took a walk going straight on for one ending in
# the lawn, the other's first metres lying under this one's own stroke: OSM's steps between a drive's end and a walk
# (과학관 북쪽, 12 m and 8 m) were cut out whole, the walk and the drive left 2 - 3 m apart.  And the walks are taken
# as OSM's ways joined end to end where just two meet (linemerge), so that a tail is measured back to its junction,
# not to where OSM happens to split it
_WALK = ('footway', 'path', 'pedestrian', 'steps')
_wk = [(k_, LineString(p_['pts']), p_['w']) for k_, p_ in enumerate(out['paths']) if len(p_['pts']) > 1]
_wtree = shapely.STRtree([g_ for _, g_, _ in _wk])
_wmax = max(w_ for _, _, w_ in _wk)
_kept = {}                                            # path index -> the stretch still drawn (None: all of it gone)
WALK_SCRAP = []                                      # (paths taken out whole by hand below, PRUNE_SCRAP)


def _wpaved(x, y):
    i_, j_ = int((SPLAT['y1'] - y) / _res), int((x - SPLAT['x0']) / _res)
    return 0 <= i_ < SH and 0 <= j_ < SW and bool(_pav0[i_, j_])


def _wjoin(own, q_, w_):
    for j_ in _wtree.query(q_.buffer(w_ / 2 + _wmax / 2 + 0.3)):
        k2_, g2_, w2_ = _wk[j_]
        if k2_ in own:
            continue
        g2_ = _kept.get(k2_, g2_)
        if g2_ is None or g2_.distance(q_) > w2_ / 2 + 0.3:
            continue
        # (and still painted there, clear of this walk's own stroke: walks whose paving a later bed, garden or the
        # old amphitheater's bowl took away do not count)
        t_, d_ = g2_.project(q_), w_ / 2 + 1.0
        s_ = [g_ for g_ in (g2_.interpolate(max(0.0, t_ - d_)), g2_.interpolate(min(g2_.length, t_ + d_)))
              if g_.distance(q_) >= w_ / 2 + 0.8]
        if not s_ or any(_wpaved(g_.x, g_.y) for g_ in s_):
            return True
    return False


def _wcross(own, ls_, end_, w_):
    """how far back from a walk's end it crosses another walk or road still painted there, within 6 m (None if not):
    OSM's walks often run a few metres past a road and stop in the lawn on its far side"""
    L_ = ls_.length
    pc_ = substring(ls_, 0.0, min(6.0, L_)) if end_ == 0 else substring(ls_, max(0.0, L_ - 6.0), L_)
    best_ = None
    for j_ in _wtree.query(pc_.buffer(0.1)):
        k2_, g2_, w2_ = _wk[j_]
        g2_ = _kept.get(k2_, g2_)
        if k2_ in own or g2_ is None:
            continue
        x_ = pc_.intersection(g2_)
        for p_ in (x_.geoms if hasattr(x_, 'geoms') else [x_]):
            if p_.is_empty or p_.geom_type != 'Point':
                continue
            t_ = ls_.project(p_) if end_ == 0 else L_ - ls_.project(p_)
            u_ = g2_.project(p_)
            if 0.75 <= t_ <= 6.0 and (best_ is None or t_ < best_) and \
                    any(_wpaved(*g2_.interpolate(min(max(u_ + s_, 0.0), g2_.length)).coords[0])
                        for s_ in (-w_ / 2 - 1.0, w_ / 2 + 1.0)):
                best_ = t_
    return best_


def _wnear(pts, P, tol=0.3):
    a_, b_ = np.array(pts[0], float), np.array(pts[-1], float)
    p0_, p1_ = np.array(P[0], float), np.array(P[1], float)
    return bool(max(np.hypot(*(a_ - p0_)), np.hypot(*(b_ - p1_))) < tol
                or max(np.hypot(*(a_ - p1_)), np.hypot(*(b_ - p0_))) < tol)


for k_, p_ in enumerate(out['paths']):
    if len(p_['pts']) > 1 and p_['kind'] in _WALK and any(_wnear(p_['pts'], P_) for P_, _ in PRUNE_SCRAP):
        _kept[k_] = None
        WALK_SCRAP.append(k_)
        PRUNED.append(LineString(p_['pts']).buffer(p_['w'] / 2 + 0.3))
_force = [(Point(*q_), (L_, r_)) for q_, L_, r_ in PRUNE_TAILS]
_widx = [k_ for k_, p_ in enumerate(out['paths']) if p_['kind'] in _WALK and len(p_['pts']) > 1 and k_ not in _kept]
_mg = linemerge([LineString(out['paths'][k_]['pts']) for k_ in _widx])
_chains = list(_mg.geoms) if hasattr(_mg, 'geoms') else [_mg]
_cways = [[] for _ in _chains]
_ctree = shapely.STRtree(_chains)
for k_ in _widx:
    g_ = LineString(out['paths'][k_]['pts'])
    for c_ in _ctree.query(g_):
        if all(_chains[c_].distance(Point(q_)) < 0.01
               for q_ in (g_.coords[0], g_.coords[-1], g_.interpolate(0.5, normalized=True).coords[0])):
            _cways[c_].append(k_)
            break
for c_, ch_ in enumerate(_chains):                     # (one walk: OSM's ways end to end; steps painted as paving)
    own = set(_cways[c_])
    if not own or ch_.is_closed:
        continue
    Lc_ = ch_.length
    w_ = max(out['paths'][k_]['w'] for k_ in own)
    if Lc_ < 1.0:
        continue
    # (its ends as seen: where a later bed, garden or the old amphitheater's bowl took the paving away, from
    # where it is still painted; the 1999 theatre's aisles stop at the bowl's edge, their stretch to the top path
    # a tail like any other)
    _ta = next((t_ for t_ in np.arange(0.0, Lc_, 0.5) if _wpaved(*ch_.interpolate(t_).coords[0])), None)
    if _ta is None:
        continue
    _tb = next(t_ for t_ in np.arange(0.0, Lc_, 0.5) if _wpaved(*ch_.interpolate(Lc_ - t_).coords[0]))
    ls_ = ch_
    if _ta > 1.0 or _tb > 1.0:
        ls_ = substring(ch_, _ta, Lc_ - _tb)
        if ls_.geom_type != 'LineString' or ls_.length < 1.0:
            continue
    else:
        _ta = _tb = 0.0
    L_ = ls_.length
    x0_, y0_, x1_, y1_ = ls_.bounds
    pad_ = w_ + 3.0
    j0_, j1_ = max(0, int((x0_ - pad_ - SPLAT['x0']) / _res)), min(SW, int((x1_ + pad_ - SPLAT['x0']) / _res) + 1)
    i0_, i1_ = max(0, int((SPLAT['y1'] - y1_ - pad_) / _res)), min(SH, int((SPLAT['y1'] - y0_ + pad_) / _res) + 1)
    if j1_ - j0_ < 2 or i1_ - i0_ < 2:
        continue
    own_ = Image.new('L', (j1_ - j0_, i1_ - i0_), 0)
    do_ = ImageDraw.Draw(own_)
    pp_ = [((x - SPLAT['x0']) / _res - j0_, (SPLAT['y1'] - y) / _res - i0_) for x, y in ls_.coords]
    wpx_ = max(1, int(round((w_ + 0.6) / _res)))
    do_.line(pp_, fill=255, width=wpx_, joint='curve')
    for (u_, v_) in (pp_[0], pp_[-1]):
        do_.ellipse([u_ - wpx_ / 2, v_ - wpx_ / 2, u_ + wpx_ / 2, v_ + wpx_ / 2], fill=255)
    other_ = _pav0[i0_:i1_, j0_:j1_] & ~(np.array(own_) > 0)
    if not other_.any():
        continue                              # (a walk on its own: the patch pass below)
    D_ = ndimage.distance_transform_edt(~other_) * _res
    cut_ = [0.0, L_]
    for end_ in (0, 1):
        q_ = Point(ls_.coords[0] if end_ == 0 else ls_.coords[-1])
        lim_, ras_ = next((Lf_ for P_, Lf_ in _force if P_.distance(q_) < 3.0), (None, True))   # (PRUNE_TAILS)
        if lim_ is None:
            if PRUNE_KEEP.contains(q_):
                continue
            qi_, qj_ = int((SPLAT['y1'] - q_.y) / _res), int((q_.x - SPLAT['x0']) / _res)
            if _dirt0[max(0, qi_ - 3):qi_ + 4, max(0, qj_ - 3):qj_ + 4].any():
                continue                      # (a trail going on into the woods)
        if _wjoin(own, q_, w_):
            continue
        hit_ = None
        for t_ in np.arange(0.0, min(L_, (lim_ or PRUNE_TAIL) + 0.25), 0.25):
            g_ = ls_.interpolate(t_ if end_ == 0 else L_ - t_)
            if lim_ is None and PRUNE_KEEP.contains(g_):
                break
            ii_, jj_ = int((SPLAT['y1'] - g_.y) / _res) - i0_, int((g_.x - SPLAT['x0']) / _res) - j0_
            if (ras_ and 0 <= ii_ < D_.shape[0] and 0 <= jj_ < D_.shape[1] and D_[ii_, jj_] <= w_ / 2 + 0.6) or \
                    (t_ >= 0.75 and _wjoin(own, g_, w_)):          # (PRUNE_TAILS: back to the walk it joins)
                hit_ = t_
                break
        if hit_ is not None and hit_ < 0.75:
            # (touching: but if it only runs past a road or walk it crossed, into the lawn beyond, back to the
            # crossing, its round end inside what it crossed)
            e_ = np.array(q_.coords[0])
            f_ = np.array(ls_.interpolate(min(1.0, L_) if end_ == 0 else max(0.0, L_ - 1.0)).coords[0])
            d_ = (e_ - f_) / max(1e-6, np.linalg.norm(e_ - f_))
            hx_ = None if _wpaved(*(e_ + d_ * (w_ / 2 + 0.8))) else _wcross(own, ls_, end_, w_)
            if hx_ is None:
                continue
            hit_ = hx_ + 0.2
        if hit_ is None or hit_ < 0.75:
            continue
        keep_t = max(0.0, hit_ - 0.2)         # (up to the edge of what it meets)
        if end_ == 0:
            cut_[0] = keep_t
        else:
            cut_[1] = L_ - keep_t
    if cut_ == [0.0, L_]:
        continue
    for t0_, t1_ in ((0.0, cut_[0]), (cut_[1], L_)):
        if t1_ - t0_ > 0.05:
            PRUNED.append(substring(ls_, t0_, t1_).buffer(w_ / 2 + 0.3))
    # (back onto OSM's ways along the walk: the chain's own metres, its unpainted ends dropped where cut)
    c0_ = _ta + cut_[0] if cut_[0] > 0.0 else 0.0
    c1_ = _ta + cut_[1] if cut_[1] < L_ else Lc_
    if cut_[1] - cut_[0] <= w_ + 0.5:
        c1_ = c0_                                     # (what is left lies in what it met: no nub of round ends)
    for k_ in own:
        g_ = LineString(out['paths'][k_]['pts'])
        a_, b_ = sorted((ch_.project(Point(g_.coords[0])), ch_.project(Point(g_.coords[-1]))))
        s0_, s1_ = max(a_, c0_), min(b_, c1_)
        if s1_ - s0_ <= 0.3:
            _kept[k_] = None
        elif s0_ > a_ + 0.05 or s1_ < b_ - 0.05:
            _kept[k_] = substring(ch_, s0_, s1_)
for k_, keep_ls in _kept.items():
    p_ = out['paths'][k_]
    ls_ = LineString(p_['pts'])
    _pa, _pb = np.array(p_['pts'][0]), np.array(p_['pts'][-1])
    for m_ in np.flatnonzero((np.hypot(*(_op_a - _pa).T) < 0.2) & (np.hypot(*(_op_b - _pb).T) < 0.2)):
        k2_ = _pav_ops[m_]
        op_ = SPLAT_OPS[k2_]
        if len(op_[2]) != len(p_['pts']) or LineString(op_[2]).hausdorff_distance(ls_) > 0.2:
            continue
        SPLAT_OPS[k2_] = ('line', 'pavers', list(keep_ls.coords), op_[3], op_[4]) if keep_ls is not None else ('line', 'pavers', [], 0, False)
SPLAT_OPS[:] = [op_ for op_ in SPLAT_OPS if not (op_[0] == 'line' and len(op_[2]) < 2)]
# (the walks the game reads, out['paths']: the minimap draws them and the crowd walks them, so they lose the same)
for k_ in sorted(_kept, reverse=True):
    if _kept[k_] is None:
        out['paths'].pop(k_)
    else:
        out['paths'][k_]['pts'] = [[round(x, 1), round(y, 1)] for x, y in _kept[k_].coords]
print('섬처럼 놓인 포장: walk stubs cut', len(PRUNED) - len(WALK_SCRAP), 'walks taken out', len(WALK_SCRAP),
      '%.0f m²' % unary_union(PRUNED).area if PRUNED else '')
_aa = splat_aa(['asphalt', 'pavers', 'dirt', '_yz', '_yg', '_yp', '_gd', '_gp', '_ga', '_gw'])
spl_aa = np.stack([_aa['asphalt'], _aa['pavers'], ndimage.gaussian_filter(_aa['dirt'], 0.7)], -1)
_yzA, _ygA = _aa['_yz'] / 255.0, _aa['_yg'] / 255.0
spl_aa[..., 0] *= 1.0 - _ygA
spl_aa[..., 1] *= (1.0 - _yzA) * (1.0 - _ygA)
spl_aa[..., 2] *= (1.0 - _yzA) * (1.0 - _ygA)
spl_aa[..., 1] = np.minimum(np.maximum(spl_aa[..., 1], _aa['_yp']), 255 - spl_aa[..., 0])
# the 1997 sites (GONE_1997, LATE_FOOTPRINT_1997) as in spl above: 제2인문관's bare earth soft, 미우학사's apron sharp
_gdA = ndimage.gaussian_filter(_aa['_gd'], 1.2)
spl_aa[..., 1] *= 1.0 - _gdA / 255.0
spl_aa[..., 2] = np.where(_gdA > 0, np.minimum(np.maximum(spl_aa[..., 2], _gdA), 255.0 - spl_aa[..., 0] - spl_aa[..., 1]), spl_aa[..., 2])
spl_aa[..., 1] = np.minimum(np.maximum(spl_aa[..., 1], _aa['_gp']), 255 - spl_aa[..., 0])
spl_aa[..., 0] = np.maximum(spl_aa[..., 0], _aa['_ga'] * (1.0 - _aa['_gp'] / 255.0))      # (의료원's car parks)
spl_aa[..., 1] = np.minimum(spl_aa[..., 1], 255 - spl_aa[..., 0])
spl_aa[..., 0] *= 1.0 - _aa['_gw'] / 255.0                                                   # (백양관 앞 계단 길)
spl_aa[..., 1] = np.maximum(spl_aa[..., 1], _aa['_gw'])
spl_aa[..., 2] = np.clip(np.minimum(spl_aa[..., 2], 255 - spl_aa[..., 0] - spl_aa[..., 1]), 0, 255)
_gbA = splat_aa(['_gb'])['_gb'] / 255.0           # (대강당 앞 둑, as in spl above)
spl_aa[..., 0] *= 1.0 - _gbA
spl_aa[..., 1] *= 1.0 - _gbA
spl_aa[..., 2] = spl_aa[..., 2] * (1.0 - _gbA) + 178.0 * _gbA
_tA = splat_aa(['_tc', '_ta', '_tp', '_td'])       # (정문 밖, as in spl above)
town_splat(spl_aa, _tA['_tc'], _tA['_ta'], _tA['_tp'], ndimage.gaussian_filter(_tA['_td'], 0.7))
# (섬처럼 놓인 포장, above: the lone patches) paving touching no asphalt, under PRUNE_PATCH, nowhere near a hall, a
# flight's foot, a landmark or 백양로 (PRUNE_KEEP)
_pvA = (spl_aa[..., 0] + spl_aa[..., 1] > 127.5) & (spl_aa[..., 1] >= spl_aa[..., 0])
_asA = ndimage.binary_dilation(spl_aa[..., 0] > 127.5, iterations=2)
_lab, _nlab = ndimage.label(_pvA)
_gone = np.zeros_like(_pvA)
_np = 0
for _k, _sl in enumerate(ndimage.find_objects(_lab), 1):
    _m = _lab[_sl] == _k
    if _m.sum() * SPLAT['res'] ** 2 >= PRUNE_PATCH or (_asA[_sl] & _m).any():
        continue
    _ii, _jj = np.nonzero(_m)
    _xs = SPLAT['x0'] + (_jj + _sl[1].start + 0.5) * SPLAT['res']
    _ys = SPLAT['y1'] - (_ii + _sl[0].start + 0.5) * SPLAT['res']
    if shapely.contains_xy(PRUNE_KEEP, _xs, _ys).any():
        continue
    _gone[_sl] |= _m
    _np += 1
    PRUNED.append(Polygon([(_xs.min() - 1, _ys.min() - 1), (_xs.max() + 1, _ys.min() - 1), (_xs.max() + 1, _ys.max() + 1),
                           (_xs.min() - 1, _ys.max() + 1)]))
_gone = ndimage.binary_dilation(_gone, iterations=2) & (spl_aa[..., 0] < 127.5)
spl_aa[..., 1][_gone] = 0.0
print('섬처럼 놓인 포장: lone patches', _np)
# (and the walks drawn only there go from the walks the game reads; the decals placed on what is gone, cracks and
# stains read off spl above, go with it)
_pg = unary_union(PRUNED).buffer(0.3) if PRUNED else Polygon()
shapely.prepare(_pg)
out['paths'] = [p_ for p_ in out['paths'] if not (p_['kind'] in ('footway', 'path', 'pedestrian', 'steps') and len(p_['pts']) > 1
                                                  and _pg.contains(LineString(p_['pts'])))]
# 의료원: OSM's walks and drives there are today's.  Where one runs through a hall of the 1997 aerial photos
# (MED_SITES_RNG), the walk the game reads (the minimap, the crowd) keeps its longest stretch outside the hall, in its
# place in the list; a short one mostly inside goes
# (and through 연구관 · 장기원 기념관 · 과학관 · 어린이생활지도연구원 as put back since: SITES_NEW_1997)
_mh = [Polygon(b_['footprint']) for b_ in buildings if b_['id'] in MED_SITES_RNG or b_['id'] in SITES_NEW_1997]
_mh0, _mh1 = unary_union([q_.buffer(-0.5) for q_ in _mh]), unary_union([q_.buffer(1.0) for q_ in _mh])
_nm = [0, 0]
for p_ in list(out['paths']):
    if len(p_['pts']) < 2:
        continue
    ls_ = LineString(p_['pts'])
    in_ = ls_.intersection(_mh0).length
    if in_ <= 1.0:
        continue
    d_ = ls_.difference(_mh1)
    pcs_ = [g_ for g_ in getattr(d_, 'geoms', [d_]) if g_.geom_type == 'LineString' and g_.length >= 10.0]
    if pcs_:
        p_['pts'] = [[round(x, 1), round(y, 1)] for x, y in max(pcs_, key=lambda g_: g_.length).coords]
        _nm[0] += 1
    elif in_ > 0.5 * ls_.length:
        out['paths'] = [q_ for q_ in out['paths'] if q_ is not p_]
        _nm[1] += 1
print('의료원: walks cut back at the 1997 halls', _nm[0], '- taken out', _nm[1])
_nd = len(out['decals'])


def _still_paved(x, y):
    i_, j_ = int((SPLAT['y1'] - y) / SPLAT['res']), int((x - SPLAT['x0']) / SPLAT['res'])
    return 0 <= i_ < SH and 0 <= j_ < SW and spl_aa[i_, j_, 0] + spl_aa[i_, j_, 1] > 127.5


out['decals'] = [d_ for d_ in out['decals'] if not shapely.contains_xy(_pg, d_[1], d_[2]) or _still_paved(d_[1], d_[2])]
print('섬처럼 놓인 포장: decals taken off with the paving', _nd - len(out['decals']))
Image.fromarray(np.clip(np.round(spl_aa), 0, 255).astype(np.uint8), 'RGB').save(
    os.path.join(ROOT, 'web/public/assets/textures/ground_splat.png'), optimize=True)


def iso_chains(F, level):
    """Marching squares over the texel centres of F (rows from the north): the polylines where F crosses level, in
    campus metres, and whether each is closed."""
    H_, W_ = F.shape
    b_ = F > level
    c_ = (b_[:-1, :-1] * 1 + b_[:-1, 1:] * 2 + b_[1:, 1:] * 4 + b_[1:, :-1] * 8).astype(np.uint8)
    # the cell's edges: 0 top, 1 right, 2 bottom, 3 left; a saddle is split by the mean of its corners
    table = {1: [(3, 0)], 2: [(0, 1)], 3: [(3, 1)], 4: [(1, 2)], 6: [(0, 2)], 7: [(3, 2)], 8: [(2, 3)], 9: [(2, 0)],
             11: [(2, 1)], 12: [(1, 3)], 13: [(1, 0)], 14: [(0, 3)]}
    ii, jj = np.nonzero((c_ > 0) & (c_ < 15))
    adj = {}

    def eid(i, j, e):
        return (2 * (i * W_ + j), 2 * (i * W_ + j + 1) + 1, 2 * ((i + 1) * W_ + j), 2 * (i * W_ + j) + 1)[e]
    for i, j, k in zip(ii.tolist(), jj.tolist(), c_[ii, jj].tolist()):
        if k in (5, 10):
            hi_ = (F[i, j] + F[i, j + 1] + F[i + 1, j] + F[i + 1, j + 1]) / 4 > level
            pairs = ([(3, 2), (1, 0)] if hi_ else [(3, 0), (1, 2)]) if k == 5 else ([(0, 3), (2, 1)] if hi_ else [(0, 1), (2, 3)])
        else:
            pairs = table[k]
        for a_, b2 in pairs:
            ea, eb = eid(i, j, a_), eid(i, j, b2)
            adj.setdefault(ea, []).append(eb)
            adj.setdefault(eb, []).append(ea)

    def where(e):
        i, j = divmod(e >> 1, W_)
        if e & 1:
            f0, f1 = F[i, j], F[i + 1, j]
            r, c = i + (level - f0) / (f1 - f0), j
        else:
            f0, f1 = F[i, j], F[i, j + 1]
            r, c = i, j + (level - f0) / (f1 - f0)
        return SPLAT['x0'] + (c + 0.5) * SPLAT['res'], SPLAT['y1'] - (r + 0.5) * SPLAT['res']
    seen, chains = set(), []
    for e0 in adj:
        if e0 in seen:
            continue
        seen.add(e0)
        ch = [e0]
        for end in (0, 1):
            cur = e0
            while True:
                nxt = [n_ for n_ in adj[cur] if n_ not in seen]
                if not nxt:
                    break
                cur = nxt[0]
                seen.add(cur)
                if end:
                    ch.insert(0, cur)
                else:
                    ch.append(cur)
        closed = len(ch) > 2 and ch[0] in adj[ch[-1]]
        chains.append((np.array([where(e) for e in ch]), closed))
    return chains


def smooth_chain(P, closed, step=0.1, sigma=0.35, corner=40.0):
    """An edge traced off the ground map, laid out as a kerb is: resampled every step m and smoothed along its length
    (a Gaussian of sigma m), keeping its corners (where it turns more than `corner` degrees within 0.6 m either way).
    The trace wanders a few cm about the drawn outline with the 0.5 m texels, and simplified at 5 cm that came out as
    1 m stretches turning 10 degrees one way and the next (the median turn between stones was 9.8 degrees); smoothed,
    a straight edge stays straight and a curve bends evenly, within 1 - 2 cm of the trace."""
    Q = np.vstack([P, P[:1]]) if closed else P
    cum = np.r_[0.0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]
    if cum[-1] < 8 * sigma:
        return P
    n_ = max(int(round(cum[-1] / step)), 8)
    s_ = np.linspace(0.0, cum[-1], n_ + 1)[:-1] if closed else np.linspace(0.0, cum[-1], n_ + 1)
    R = np.column_stack([np.interp(s_, cum, Q[:, 0]), np.interp(s_, cum, Q[:, 1])])
    w_ = max(1, int(round(0.6 / step)))
    if closed:
        A, B = np.roll(R, w_, 0), np.roll(R, -w_, 0)
    else:
        A, B = R[np.maximum(np.arange(len(R)) - w_, 0)], R[np.minimum(np.arange(len(R)) + w_, len(R) - 1)]
    u_, v_ = R - A, B - R
    turn = np.degrees(np.abs(np.arctan2(u_[:, 0] * v_[:, 1] - u_[:, 1] * v_[:, 0], (u_ * v_).sum(1))))
    if not closed:
        turn[:w_] = turn[-w_:] = 0.0
    peak = (turn > corner) & (turn == ndimage.maximum_filter1d(turn, 2 * w_ + 1, mode='wrap' if closed else 'nearest'))
    cuts = np.flatnonzero(peak)
    sg_ = sigma / step
    if not len(cuts):
        return ndimage.gaussian_filter1d(R, sg_, axis=0, mode='wrap' if closed else 'nearest')
    if closed:                                     # start the loop at a corner, and close it there
        R = np.vstack([np.roll(R, -cuts[0], 0), np.roll(R, -cuts[0], 0)[:1]])
        cuts = np.r_[cuts - cuts[0], len(R) - 1]
    else:
        cuts = np.unique(np.r_[0, cuts, len(R) - 1])
    out_ = R.copy()
    for a_, b_ in zip(cuts[:-1], cuts[1:]):
        if b_ - a_ > 2:
            out_[a_ + 1:b_] = ndimage.gaussian_filter1d(R[a_:b_ + 1], sg_, axis=0, mode='nearest')[1:-1]
    return out_[:-1] if closed else out_


# Curbs (경계석): wherever the painted asphalt or paving meets the lawn, a low granite kerb stands along the edge on the
# lawn side (1997 photos and the 2008 / 2011 roadview: kerbs round the 상뜰's beds and the drives, the paths across the
# lawns, the forecourts), drawn by web/src/curbs.js.  Not along 백양로 (its own road mesh has its kerbs), the walls of
# the halls, the woods' floor, nor in the town round the campus.  [kind, x0, y0, dx1, dy1, ...]: the lawn on the left
# going along, kind 'a' by the asphalt (drives, car parks), 'p' by the paving; x0, y0 in cm, then each next point's
# step from the last in cm.
def curb_runs(F3):
    paved = F3[..., 0] + F3[..., 1]
    grass = np.clip(255.0 - paved - F3[..., 2], 0, 255)
    keep_out = unary_union([bline.buffer(ROAD_HALF + 0.4), city.buffer(2.0),
                            Point(*FOUNTAIN['pos']).buffer(FOUNTAIN['pave'] + 0.6)] +    # (활천대's flagstones run into the turf)
                           [Polygon(b_['footprint']).buffer(0.5) for b_ in out['buildings']] +
                           [LineString(xy(q) for q in w_['geometry']).buffer(WID[w_['tags']['highway']] / 2 + 1.5)
                            for w_ in ways.values() if w_.get('tags', {}).get('highway') in ('primary', 'secondary')])
    area = unary_union([Polygon(b_['footprint']).buffer(45.0) for b_ in out['buildings'] if b_['style'] != 'city'] +
                       [bline.buffer(60.0)])                       # (the campus: not the hills' and the town's roads)
    shapely.prepare(keep_out)
    shapely.prepare(area)

    def at(A, P):
        return ndimage.map_coordinates(A, [(SPLAT['y1'] - P[:, 1]) / SPLAT['res'] - 0.5,
                                           (P[:, 0] - SPLAT['x0']) / SPLAT['res'] - 0.5], order=1, mode='nearest')
    runs, lawns = [], []

    def emit(P, lab, closed, behind, kinds, probe=3.0):
        # the kerbs of one chain (lab per point: 0 none, else an index into kinds) and how far `behind` (> 128) reaches
        # on their left (the lawn, or the paving behind a drive's kerb; at most `probe` m), every CURB_LAWN_STEP m
        # along each in dm
        if closed and (lab == lab[0]).all():
            pieces = [(np.r_[np.arange(len(P)), 0], lab[0])] if lab[0] else []
        else:
            if closed:                                             # start the loop where a kerb breaks off or changes
                k0 = int(np.flatnonzero(lab != np.roll(lab, 1))[0])
                P, lab = np.roll(P, -k0, 0), np.roll(lab, -k0)
            cut = np.flatnonzero(np.diff(lab)) + 1
            pieces = []
            for s_, e_ in zip(np.r_[0, cut], np.r_[cut, len(P)]):
                if lab[s_]:                                        # (a kerb runs on to the next kind's first point)
                    nxt = e_ + 1 if e_ < len(P) and lab[e_] else e_
                    pieces.append((np.arange(s_, nxt), lab[s_]))
        T = np.gradient(P, axis=0)
        T /= np.maximum(np.hypot(T[:, 0], T[:, 1]), 1e-9)[:, None]
        N = np.stack([-T[:, 1], T[:, 0]], 1)
        for idx, k_ in pieces:
            if len(idx) < 3:
                continue
            ls_ = LineString(P[idx])
            # (a piece on its own under 2 m goes; one running on from or into another kind's stays from 0.5 m, so
            # that a drive's kerb meets the lowered stretch beside it with no gap)
            joined = (idx[0] > 0 and lab[idx[0] - 1] != 0) or lab[idx[-1] % len(lab)] != k_
            if ls_.length < (0.5 if joined else 2.0):
                continue
            q_ = np.round(np.array(ls_.simplify(0.015).coords) * 100).astype(int)
            q_[1:] -= q_[:-1].copy()
            runs.append([kinds[k_]] + q_.ravel().tolist())
            # how far the lawn reaches behind the kerb (to the next paving, the woods' floor, at most 3 m), every
            # CURB_LAWN_STEP m along the run in dm: the raised lawn's edge (issue #86, web/src/curbs.js) spans a narrow
            # strip from kerb to kerb and on a wide lawn eases back down; behind a drive's kerb the same for the paving
            Pi, Ni = P[idx], N[idx]
            dd_ = np.arange(0.3, probe + 0.01, 0.1)
            lawn_ = np.ones((len(Pi), len(dd_)), bool)
            for m_, d_ in enumerate(dd_):
                lawn_[:, m_] = at(behind, Pi + Ni * d_) > 128
            Dp = np.where(lawn_.all(1), probe, dd_[np.argmin(lawn_, 1)] - 0.05)
            Dp = ndimage.minimum_filter1d(Dp, 11, mode='nearest')          # (about 1 m: smooth_chain's 0.1 m points)
            cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(Pi, axis=0).T))])
            lawns.append(np.round(np.interp(np.arange(0.0, cum[-1] + CURB_LAWN_STEP, CURB_LAWN_STEP), cum, Dp) * 10).astype(int).tolist())

    def chain(F, P, closed):
        # smoothed, the left normals, turned so that F is lower on the left
        P = smooth_chain(P, closed)
        T = np.gradient(P, axis=0)
        if closed:
            T[0], T[-1] = P[1] - P[-1], P[0] - P[-2]
        T /= np.maximum(np.hypot(T[:, 0], T[:, 1]), 1e-9)[:, None]
        N = np.stack([-T[:, 1], T[:, 0]], 1)                       # the left of the way along
        if np.mean(at(F, P + N * 0.4) - at(F, P - N * 0.4)) > 0:
            P, N = P[::-1].copy(), -N[::-1]
        return P, N

    inside = lambda P: shapely.contains_xy(area, P[:, 0], P[:, 1]) & ~shapely.contains_xy(keep_out, P[:, 0], P[:, 1])
    for P, closed in iso_chains(paved, 127.5):
        if len(P) < 4:
            continue
        P, N = chain(paved, P, closed)                             # (the lawn on the left)
        ok = (at(grass, P + N * 0.45) > 150) & (at(paved, P - N * 0.45) > 160) & inside(P)
        asph = (at(F3[..., 0], P - N * 0.45) > at(F3[..., 1], P - N * 0.45)).astype(np.int8)
        asph = ndimage.median_filter(asph, 17, mode='wrap' if closed else 'nearest')    # (no flicker over a texel)
        emit(P, np.where(ok, 1 + asph, 0), closed, grass, (None, 'p', 'a'))
    # 연석 between a drive or a car park and the paving beside it (issue: 「아스팔트와 보도블록의 경계가 흐림」): the two
    # met level, one texture cut into the other.  The 2008 - 2011 roadview has a granite kerb along every one of them
    # (대우관 서쪽 차로, the eagle's side road and its brick walks, 백양관 앞 · 북쪽 주차장, 학생회관 앞), the paving's side
    # up to its top: kind 'k', the paving on the left, raised behind it as the lawn is behind the others (curbs.js).
    # (issue 「연석: 낮춘 곳 · 같은 높이였던 곳」, reference/고증/2.3)
    #  - 낮춘 곳 (kind 'd', 2 cm over the asphalt, nothing raised behind it): where the paving behind the kerb is a
    #    strip running away from it, not along it, the kerb crosses the strip's end: a walk meeting the drive (on both
    #    sides where it crosses), or a drive passing through a sidewalk (the kerb along the drive's side across the
    #    sidewalk), with paving again across the asphalt.  0.8 m behind the kerb the paving reaches CURB_LOW_SPAN m or
    #    less along the kerb and on away from it CURB_LOW_DEPTH m or more.  백양로's crossings have the walk ramped
    #    down to the road in the 2008 - 2010 roadview, and a drive's mouth can't keep a standing kerb; the kerbs beside
    #    them ramp down to it (curbs.js)
    #  - 같은 높이 (CURB_FLUSH): no kerb at all where the 2008 roadview has the paving run flush into the asphalt
    #  - the kerb runs on to the lawn's kerb ('a', the loop above) along the same edge and over a gap under
    #    CURB_BRIDGE m, so a corner where the two meet has no tooth missing
    pave, asp = F3[..., 1], F3[..., 0]
    flush = unary_union([p_ for _, p_ in CURB_FLUSH])
    shapely.prepare(flush)
    dd_low = np.arange(0.3, CURB_LOW_DEPTH + 0.01, 0.1)
    ss_low = np.arange(0.0, CURB_LOW_SPAN + 0.01, 0.1)
    for P, closed in iso_chains(asp, 127.5):
        if len(P) < 4:
            continue
        P, N = chain(asp, P, closed)                               # (the asphalt on the right)
        T = np.stack([N[:, 1], -N[:, 0]], 1)
        ins = inside(P)
        pv = (at(pave, P + N * 0.45) > 150) & (at(asp, P - N * 0.45) > 160) & ins
        lw = (at(grass, P + N * 0.45) > 150) & (at(paved, P - N * 0.45) > 160) & ins    # (the lawn's kerb, 'a')
        ok = curb_bridge(pv, lw, closed, int(round(CURB_BRIDGE / 0.1)))
        if ok.any():                                               # (no stones on a texel's corner)
            ok = ndimage.binary_opening(np.r_[ok[-4:], ok, ok[:4]] if closed else ok, np.ones(9, bool))
            ok = ok[4:-4] if closed else ok
        ok &= ~shapely.contains_xy(flush, P[:, 0], P[:, 1])
        # the paving behind: how far on away from the kerb, and how far along it 0.8 m in (or half way, if shallower)
        deep = np.ones(len(P), bool)
        depth = np.full(len(P), CURB_LOW_DEPTH)
        for d_ in dd_low:
            hit = deep & (at(pave, P + N * d_) <= 128)
            depth[hit] = d_
            deep &= ~hit
        Q = P + N * np.minimum(0.8, depth / 2)[:, None]
        span = np.zeros(len(P))
        for sg_ in (1, -1):
            go = np.ones(len(P), bool)
            for s_ in ss_low[1:]:
                go &= at(pave, Q + T * (sg_ * s_)) > 128
                span += go * 0.1
        # (and straight across the asphalt, within CURB_LOW_ACROSS m, paving again: the walk goes on over the road, or
        # the sidewalk on past the drive's mouth; a walk ending at a road with the lawn across keeps its kerb, as the
        # brick flight to the eagle's terrace does in the 2008 roadview, 2381990)
        across = np.zeros(len(P), bool)
        live = np.ones(len(P), bool)
        for d_ in np.arange(0.5, CURB_LOW_ACROSS + 0.01, 0.25):
            R_ = P - N * d_
            off = live & (at(asp, R_) <= 128)
            across |= off & (at(pave, R_) > 128)
            live &= ~off
        low = ok & (span < CURB_LOW_SPAN) & (depth >= CURB_LOW_DEPTH - 0.05) & across
        low = ndimage.median_filter(low.astype(np.int8), 9, mode='wrap' if closed else 'nearest').astype(bool) & ok
        if low.any():                                              # (a lowered stretch 1.5 m long at least)
            low = ndimage.binary_opening(np.r_[low[-8:], low, low[:8]] if closed else low, np.ones(15, bool))
            low = low[8:-8] if closed else low
        lab = np.where(ok, np.where(low, 2, 1), 0).astype(np.int8)
        emit(P, lab, closed, pave, (None, 'k', 'd'), probe=CURB_RAISE_PROBE)
    print('curbs: %d runs, %.0f m' % (len(runs), sum(np.hypot(*np.reshape(r_[3:], (-1, 2)).T).sum() / 100 for r_ in runs)),
          'lawn behind them < 2 m: %.0f %%' % (100 * np.mean([v_ < 20 for l_ in lawns for v_ in l_])),
          '- lowered %d runs, %.0f m' % (sum(r_[0] == 'd' for r_ in runs),
                                         sum(np.hypot(*np.reshape(r_[3:], (-1, 2)).T).sum() / 100 for r_ in runs if r_[0] == 'd')))
    return runs, lawns


def curb_bridge(k, other, closed, gap):
    # k with its gaps of up to `gap` points filled where k is on both sides of the gap, or k on one side and `other`
    # (another kerb along the same edge) on the other
    lab = np.where(k, 1, np.where(other, 2, 0)).astype(np.int8)
    n = len(lab)
    if not k.any() or (lab == 0).all():
        return k.copy()
    sh = int(np.flatnonzero(lab != 0)[0]) if closed else 0
    L = np.roll(lab, -sh)
    out = L == 1
    z = np.r_[0, (L == 0).astype(np.int8), 0]
    starts, ends = np.flatnonzero(np.diff(z) == 1), np.flatnonzero(np.diff(z) == -1)    # [s, e) runs of zeros
    for s, e in zip(starts, ends):
        if e - s > gap:
            continue
        a = L[s - 1] if s > 0 else (L[-1] if closed else 0)
        b = L[e] if e < n else (L[0] if closed else 0)
        if (a == 1 and b in (1, 2)) or (b == 1 and a == 2):
            out[s:e] = True
    return np.roll(out, sh)


CURB_LAWN_STEP = 2.0
CURB_LOW_SPAN, CURB_LOW_DEPTH, CURB_LOW_ACROSS = 7.0, 3.0, 14.0      # (curb_runs: 낮춘 곳)
CURB_BRIDGE = 1.5                                 # (curb_runs: the longest gap a drive's kerb runs on over)
CURB_RAISE_PROBE = 6.0                            # (how far the paving behind a drive's kerb is measured, m)
# 같은 높이였던 곳 (reference/고증/2.3): the paving meets the asphalt with no kerb, level
#  - 학생회관 뒤: the service yard and the walk along the hall's east wall north of the drive (2008-08 2381272 ·
#    2381274: level concrete, a row of yellow-and-black bollards on the line instead of a kerb; the hall's south wall
#    stands in the asphalt)
CURB_FLUSH = [('학생회관 뒤', Polygon([(28.0, -126.0), (72.0, -126.0), (72.0, -95.0), (28.0, -95.0)]))]
# (TRAFFIC: the cars' loop stays on the asphalt, a car's half width either side of it; 백양로 itself is its own mesh)
_toff = []
for lp_ in TRAFFIC['loops']:
  _tp = np.array(lp_['pts'])
  _tt = np.gradient(_tp, axis=0)
  _tn = np.stack([-_tt[:, 1], _tt[:, 0]], 1) / np.maximum(1e-9, np.linalg.norm(_tt, axis=1))[:, None]
  for k_, (q_, n_) in enumerate(zip(_tp, _tn)):
    if bline.distance(Point(*q_)) < ROAD_HALF + 1.0:        # (blender/road.py's own mesh, its gap at the 삼거리)
        continue
    for o_ in (-0.85, 0.85):
        x_, y_ = q_ + n_ * o_
        if spl_aa[int((SPLAT['y1'] - y_) / SPLAT['res']), int((x_ - SPLAT['x0']) / SPLAT['res']), 0] < 128:
            _toff.append((lp_['name'][0], k_, round(float(x_), 1), round(float(y_), 1)))
print('traffic: wheel tracks off the asphalt', len(_toff), _toff[:40])
out['curbs'], out['curb_lawn'] = curb_runs(spl_aa)
out['trees'][:] = [t_[:5] for t_ in out['trees']]      # (the places as first planted, rxy: not written out)
for p in (os.path.join(ROOT, 'data/campus.json'), os.path.join(ROOT, 'web/public/data/campus.json')):
    json.dump(out, open(p, 'w'), ensure_ascii=False, separators=(',', ':'))
np.save(os.path.join(ROOT, 'data/terrain_near.npy'), Hn.astype(np.float32))
np.save(os.path.join(ROOT, 'data/terrain_south.npy'), HS.astype(np.float32))
print('baekyangro length %.0f m, rise %.1f -> %.1f m' % (L, prof[0], prof[-1]))

# ---------------------------------------------------------------------------
# Debug map
# ---------------------------------------------------------------------------
dbg = Image.fromarray(np.clip(spl, 0, 255).astype(np.uint8), 'RGB').resize((SW // 2, SH // 2))
d = ImageDraw.Draw(dbg)
COL = {'modern': (150, 150, 200), 'white': (230, 230, 230), 'stone': (160, 120, 90), 'house': (200, 150, 120),
       'gym': (120, 200, 200), 'city': (90, 90, 90)}
def tp(x, y):
    a, b_ = to_px(x, y)
    return a / 2, b_ / 2
for b in buildings:
    col = (255, 80, 80) if b['style'].startswith('lm') else COL.get(b['style'], (255, 0, 255))
    d.polygon([tp(x, y) for x, y in b['footprint']], fill=col, outline=(0, 0, 0))
for t in trees:
    x, y = tp(t[1], t[2])
    c_ = {'ginkgo': (255, 230, 0), 'pine': (0, 90, 30), 'zelkova': (40, 160, 40), 'cherry': (255, 150, 200), 'maple': (200, 60, 20), 'oak': (60, 120, 30),
          'zelkova_young': (120, 220, 90), 'cherry_young': (255, 190, 220), 'metasequoia': (150, 200, 60),
          'magnolia': (250, 250, 235), 'poplar': (210, 220, 210), 'fir': (10, 70, 40)}[t[0]]
    d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=c_)
for l in LANDMARKS:
    x, y = tp(*l['pos'])
    d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=(255, 0, 255), width=2)
for bn in banners:
    d.line([tp(*bn['a'][:2]), tp(*bn['b'][:2])], fill=(0, 0, 255), width=2)
dbg.save(os.path.join(ROOT, 'data/debug_map.png'))
