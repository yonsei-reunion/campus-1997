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
from shapely.ops import unary_union
import shapely
from PIL import Image, ImageDraw

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
B = {
    163525865: ('lm:library', 5, '중앙도서관'),
    1444448640: ('lm:union', 4, '학생회관'),
    1444448646: ('white', 3, '학생회관 별관'),
    324328422: ('lm:centennial', 4, '백주년기념관'),
    246156115: ('lm:underwood', 3, '언더우드관'),
    246156116: ('lm:appenzeller', 2, '아펜젤러관'),
    246156118: ('lm:stimson', 2, '스팀슨관'),
    371403811: ('lm:auditorium', 4, '대강당'),
    429249499: ('lm:chapel', 2, '루스채플'),
    205583531: ('lm:engineering', 5, '제1공학관'),
    246156113: ('stone', 3, '핀슨관'),
    429249496: ('lm:hanok', 1, '광혜원'),
    # engineering / science quarter
    # (제1공학관's 공AS block, 1451926794, is the 2015 north wing: a car park in the 1997 photo; see FOOTPRINT_1997)
    1451926793: ('modern', 5, '제1공학관'), 1451926787: ('modern', 5, '제1공학관'),
    256932940: ('modern', 6, '제2공학관'),
    224955691: ('modern', 5, '제3공학관 (공사중)'), 324328471: ('white', 2, '별동연구동'),
    222843398: ('white', 6, '과학관'), 468614722: ('lm:kwangbok', 4, '광복관'),   # (blender/landmarks.py kwangbok)
    256933753: ('white', 5, '백양관'),          # (OSM: 경영학교실단) the old 상경대학 hall, 백양관 since 1996
    421415366: ('gym', 2, '체육관'), 421415365: ('white', 4, '체육교육관'),
    # humanities / north campus
    246156112: ('modern', 6, '인문관'), 246156114: ('modern', 5, '인문관'),
    246156119: ('white', 4, '제2인문관 (공사중)'), 245623759: ('lm:yeonhui', 4, '연희관'),
    246156121: ('stone', 2, '연합신학대학원'), 246156123: ('modern', 6, '종합관'),
    246156117: ('lm:seongam', 2, '성암관'), 246156111: ('lm:gyoyuk', 3, '교육관'),   # (blender/landmarks.py seongam, gyoyuk)
    245623193: ('stone_pale', 4, '생활과학관'), 413217834: ('house', 1, '논지당'),
    242897922: ('lm:daewoo', 6, '대우관'), 242897923: ('lm:daewoo_annex', 5, '대우관 별관'),
    429077789: ('white', 4, '음악대학'), 429077790: ('white', 4, '음악대학'),
    429079066: ('stone', 2, '언더우드가 사택'), 472512289: ('brick', 2, '알렌관'),
    472512292: ('white', 2, '어린이생활지도연구원'), 472965030: ('house', 2, '대학사택'),
    472987415: ('house', 2, '대학사택'), 472987419: ('house', 2, '대학사택'),
    472534641: ('house', 2, '영빈관'), 472534642: ('house', 2, '총장공관'),
    472516998: ('tile', 5, '국제학사'), 371403603: ('brick', 5, '한국어학당'),
    429077785: ('white', 1, '영선실'), 472516999: ('white', 1, '차량실'),
    722550503: ('white', 2, '행정동'),
    # medical quarter (old Severance)
    472648570: ('modern', 10, '세브란스병원'), 429249489: ('modern', 6, '의료원 종합관'),
    429249493: ('white', 5, '치과대학'), 429249490: ('modern', 6, '치과대학병원'),
    429249494: ('white', 5, '간호대학'),
    473006250: ('white', 4, '광혜관'), 473006251: ('white', 5, '제중관'),
    324328456: ('white', 4, '의학도서관'), 473014379: ('modern', 5, '임상의학연구센터'),
    1178739301: ('white', 5, '의과대학'), 1178739302: ('white', 5, '의과대학'),
    473014385: ('white', 4, '동문회관'), 429079067: ('white', 4, '재활병원'),
    324328481: ('modern', 7, '심장혈관병원'), 324328472: ('white', 5, '안·이비인후과병원'),
    # in 1997 too, missing before
    246156110: ('stone', 2, '한경관'), 429249497: ('house', 1, '수경원 정자각'), 1178743320: ('white', 3, '미우학사'),
}
# Outlines that have grown since 1997.  제1공학관: the College of Engineering added south and north wings in 2014-15
# (연세대 공과대학 연혁: 2014.6 착공, 2015.7 봉헌; yonsei.ac.kr/sc/243: 1,452평, 지상 6층) and the sixth floor in 2007.
# In the 1997 aerial photo (reference/1997_백양로_항공사진.jpg, camera fitted to the buildings) the 백양로 front ends
# about 65 m from its south end, with a car park and lawn where OSM now has another 13.5 m of hall and the 공AS block;
# the OSM outline's slanted south end, 9 m past the west wall, is the south wing.  So: the OSM hall's rectangle from
# 9 m to 74.5 m along its length (about 800 m2 a floor taken off, as much as the wings added).
FOOTPRINT_1997 = {205583531: [(-127.6, -296.97), (-110.42, -233.76), (-124.96, -229.8), (-142.14, -293.01)]}
FLOOR_H = {'modern': 3.8, 'white': 3.6, 'stone': 4.2, 'house': 3.4, 'gym': 6.5, 'city': 3.0, 'brick': 3.6, 'tile': 3.4, 'stone_pale': 4.0}

# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------
tn = json.load(open(os.path.join(ROOT, 'data/terrain.json')))
tf = json.load(open(os.path.join(ROOT, 'data/terrain_far.json')))
H10 = np.array(tn['rows_south_to_north'], dtype=np.float64)       # 10 m grid, +-1400
H10 = ndimage.gaussian_filter(H10, 1.6)                             # remove DSM building bumps
NEAR_HALF, NEAR_STEP = 800, 5.0
n_near = int(2 * NEAR_HALF / NEAR_STEP) + 1
gx = np.linspace(-NEAR_HALF, NEAR_HALF, n_near)
ii = (gx + tn['half']) / tn['step']
JJ, II = np.meshgrid(ii, ii, indexing='ij')                          # rows = y, cols = x
Hn = ndimage.map_coordinates(H10, [JJ, II], order=3)
Hn = ndimage.gaussian_filter(Hn, 1.5)
Hn_orig = Hn.copy()


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
# The road was rebuilt in 2015 (백양로 재창조) and OSM follows the new walk.  Measured in the 1997 aerial photo
# (reference/1997_백양로_항공사진.jpg, its camera fitted to 제1공학관, 중앙도서관, 백주년기념관 and the towers of
# 언더우드관 and 대우관; the ground points back-projected onto the terrain): the 1997 carriageway ran ~4 m further
# west, all the way from the gate to past 백주년기념관 (4.1 m at 100 m, 4.0 at 185 m, 3.5 at 320 m).  Shift the line,
# easing back onto OSM towards the 삼거리 where the photo shows nothing.
_bl0 = LineString(bys)


def _west(s):
    return 4.0 if s <= 300 else 4.0 * max(0.0, (520 - s) / 220)


_shifted = []
for _x, _y in bys:
    _s = _bl0.project(Point(_x, _y))
    _p0, _p1 = _bl0.interpolate(max(0, _s - 2)), _bl0.interpolate(min(_bl0.length, _s + 2))
    _tx, _ty = _p1.x - _p0.x, _p1.y - _p0.y
    _n = math.hypot(_tx, _ty)
    _shifted.append((round(_x - _ty / _n * _west(_s), 2), round(_y + _tx / _n * _west(_s), 2)))
bys = _shifted
GATE = bys[0]
bline = LineString(bys)
# Road cross-section, half widths from the centre line.  As in the 1997 aerial photo (reference/1997_백양로_항공사진.jpg):
# a two-lane carriageway (white dashed centre line, yellow edge lines) with no median, a raised verge of
# clipped round boxwood on each side, a paver sidewalk, and an outer planting strip carrying the ginkgo row and a low
# clipped hedge.  Widths measured in the photo at 100 m and 185 m from the gate: 6.6 m between the yellow edge lines
# (OSM's modern road is wider), the verges' outer edge 5 m out, the sidewalk to ~9.5 m.
ROAD = dict(median=0.0, lane=3.3, curb=0.25, verge=1.8, walk=4.6, strip=2.2)
E_CURB = ROAD['median'] + ROAD['lane'] + ROAD['curb']       # carriageway edge (curb top)
E_VERGE = E_CURB + ROAD['verge']                             # inner edge of the sidewalk
E_WALK = E_VERGE + ROAD['walk']                              # outer edge of the sidewalk
ROAD_HALF = E_WALK + ROAD['strip']


def s_at(x, y):
    return float(bline.project(Point(x, y)))


def along_raw(s, off):
    """point `off` m to the west (left) of the 백양로 centre line at arc length s, and the road heading there"""
    p = bline.interpolate(s)
    p2 = bline.interpolate(min(bline.length, s + 1))
    p0 = bline.interpolate(max(0, s - 1))
    tx, ty = p2.x - p0.x, p2.y - p0.y
    n_ = math.hypot(tx, ty)
    return p.x - ty / n_ * off, p.y + tx / n_ * off, math.atan2(ty, tx)

# Height profile along 백양로 (issue #8).  The elevation tiles are a surface model (roofs and tree crowns in it) and
# the 5 m grid smears the hall blocks and the wooded hill behind 언더우드관 down onto the road: sampled along it, the
# road stayed flat for 100 m in from the gate, then climbed 20.6 m to the 삼거리, 11.6 of them in the last 110 m.
# The designers of the 2015 rebuilding (Annual Technical Report(지하융복합)_2023, 2.1: 「정문에서 본관 앞 삼거리까지
# 약 12m의 레벨 차가 있는 완만한 경사」, about 8 m of it over the 360 m of the building) drew the road before the works
# in their long section (그림 2.5 (a), reference/고증.md): its ground line, read off column by column, rises
# about 1.1 m in the first 50 m, runs nearly level to ~150 m and then climbs evenly (about 2.5 %) to the 삼거리.
# So: the road gets that section, 12 m from the gate's height, and the ground around it moves with it (by the
# difference between the section and the ground's trend across a 120 m band), fading out 50-230 m from the road;
# beyond the 삼거리 that lowers 언더우드관's quarter, which carries its aprons, garden, statue and steps along.
L = bline.length
ss = np.arange(0, L + 0.1, 2.0)
_dem = np.array([sample(Hn, NEAR_HALF, NEAR_STEP, *bline.interpolate(s).coords[0]) for s in ss])
H_GATE = float(ndimage.gaussian_filter1d(_dem, 12)[0])
# 그림 2.5 (a): (fraction of the way to the 삼거리, rise in m) at the ground line's turning points
SECTION = [(0.0, 0.0), (0.019, 0.0), (0.083, 1.14), (0.252, 1.71), (0.359, 3.43), (0.487, 5.14), (0.592, 6.86),
           (0.656, 7.43), (0.805, 9.71), (0.910, 10.86), (1.0, 12.0)]
prof = H_GATE + np.interp(ss / L, [f for f, _ in SECTION], [d for _, d in SECTION])
prof = ndimage.gaussian_filter1d(prof, 6, mode='nearest')
prof += (H_GATE + 12.0 - prof[-1]) * (ss / L) ** 2            # (keep the ends where they belong after smoothing)
_band = np.array([np.mean([sample(Hn, NEAR_HALF, NEAR_STEP, *along_raw(s, o)[:2]) for o in np.arange(-60, 61, 10)])
                  for s in ss])
_shift = ndimage.gaussian_filter1d(prof - ndimage.gaussian_filter1d(_band, 15, mode='nearest'), 10, mode='nearest')
_shift *= np.clip(ss / 80.0, 0, 1) ** 2 * (3 - 2 * np.clip(ss / 80.0, 0, 1))     # (the town outside the gate stays)


def prof_h(s):
    return float(np.interp(s, ss, prof))


# zebra crossings (arc length): 백주년기념관, 학생회관-중앙도서관, 대강당, 삼거리.  Near the gate the 1997 photo
# shows a yellow/white hatched speed bump (raised, striped) instead.  The carriageway itself stays clear of objects.
CROSS = [round(s_at(-55, -200), 1), round(s_at(-20, -62), 1), round(s_at(5, 40), 1), round(L - 30, 1)]
BUMP_S = 85.0                   # read off the 1997 photo

X, Y = grid_pts()
pts = np.stack([X.ravel(), Y.ravel()], 1)
from shapely import points as shp_points, distance as shp_distance, line_locate_point
P = shp_points(pts)
dist = shp_distance(P, bline).reshape(X.shape)
spos = line_locate_point(bline, P).reshape(X.shape)
_fade = np.clip((dist - 50.0) / 180.0, 0, 1)
Hn = Hn + np.interp(spos, ss, _shift) * (1 - _fade * _fade * (3 - 2 * _fade))
print('백양로 section: gate %.2f, 삼거리 %.2f m; ground shifted by %.1f .. %.1f m' % (prof[0], prof[-1], _shift.min(), _shift.max()))
hline = np.interp(spos, ss, prof)
w = np.clip((dist - (ROAD_HALF + 4)) / 30.0, 0, 1)
w = w * w * (3 - 2 * w)
Hn = hline * (1 - w) + Hn * w

# --- the hill north of 한경길 (연희관, 대우관, 생활과학관), 6 m down.  The elevation tiles are a radar surface model at
# 30 m: over the wooded hill and its big halls they stand over the ground, and the 5 m grid had 연희관's door 19.5 m
# over 한경길 behind 언더우드관, with 13 m of it one 30 % slope across the garden between them.  The photos have
# something else: a level parterre a short flight (OSM: 5 m) over 한경길, then a bank with a broad flight up to the
# road before 연희관 and its entrance flight, some 7 - 9 m in all (reference/연희관_정면_2023.jpg, 학교연혁_연희관.jpg,
# 대우관_블로그_연희관과_대우관_원경.jpg).  In the 1997 aerial photo, through its fitted camera, 대우관's tower top stood
# 18 px (6 m) and 연희관's 17 px (5.5 m) under where the game had them, while 언더우드관's roof sat right.  With the hill
# 6 m down their eaves, gables and towers land within 2 - 4 px (about a metre), the roads either side of the garden ease from 27 % and 18 % to 14 % and 8 %, and
# 연희관 keeps its back yard a storey over its front as before.  Full over the hill (G frame: e across, n up the
# garden's axis from its round planter), easing in from 한경길 to the road before 연희관 (the garden takes the step,
# YEONHUI below) and out into the woods west, east and north.
GF_C, GF_E, GF_N = np.array([78.4, 318.3]), np.array([0.968, -0.250]), np.array([0.250, 0.968])
GE = (X - GF_C[0]) * GF_E[0] + (Y - GF_C[1]) * GF_E[1]
GN = (X - GF_C[0]) * GF_N[0] + (Y - GF_C[1]) * GF_N[1]
NORTH_DROP = 6.0


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def north_drop(e, n):
    return NORTH_DROP * (_smooth((n + 22.0) / 48.0) * (1 - _smooth((n - 235.0) / 95.0))
                         * (1 - _smooth((-95.0 - e) / 50.0)) * (1 - _smooth((e - 105.0) / 45.0)))


def drop_at(x, y):
    d_ = np.array([x, y]) - GF_C
    return float(north_drop(d_ @ GF_E, d_ @ GF_N))


Hn = Hn - north_drop(GE, GN)
print('north hill down %.1f m (%d grid nodes moved)' % (NORTH_DROP, int((north_drop(GE, GN) > 0.05).sum())))

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

# --- 대강당 앞 농구장 (1997): an outdoor court between 백양로 and the 대강당 driveway, where 금호아트홀 (under
# 백양누리) was later built (namu.wiki 연세대학교/신촌캠퍼스).  No photo found: a standard 28 x 15 m court, long side
# along 백양로.  Flatten the ground under it.
COURT = dict(pos=[21.9, 2.5], rot=1.313, L=28.0, W=15.0)
# --- 활천대 (活泉臺): the fountain the electrical engineering alumni raised money for in 1974 (연세대학교 공식 블로그
# 「연세대학교의 조형물을 찾아서!! 제3탄」, 2017).  Before 백양로 was rebuilt it stood beside the eagle (연세춘추
# 「연세인도 모르는 연세대학교」, 2009.9: 「활천대는 독수리상 옆에 있는 분수대다」; since 2015 it is in front of
# 제1공학관, where its old spot became the stairs down to 백양누리).  Its 2009 photo (reference/활천대_2009_연세춘추.jpg)
# was taken from 백양로's west sidewalk looking north-west past it: the arched east front of 중앙도서관 behind, the dome
# of 과학관 far left, the eagle on the right.  Solving for that camera (the eagle's top and foot and its place in the
# frame, the library's arches and roofline, the dome; a wide lens, residuals under 6 px) puts the basin 11 m in front
# of it, 36 m south-south-west of the eagle and 20 m off 백양로's centre line; it is ~6.4 m across (the bell of jets
# 180 px wide) and its column ~3.3 m over the water.  (The camera: (-51.0, -125.8), 1.6 m up, heading 29.2 deg west
# of north, tilted 5.1 deg up, vertical field 51.5 deg.)
FOUNTAIN = dict(pos=[-58.0, -117.0], r=3.2)


def court_poly(pad=0.0):
    c_, s_ = math.cos(COURT['rot']), math.sin(COURT['rot'])
    hl, hw = COURT['L'] / 2 + pad, COURT['W'] / 2 + pad
    return Polygon([(COURT['pos'][0] + u * c_ - v * s_, COURT['pos'][1] + u * s_ + v * c_)
                    for u, v in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))])


_inside = np.array([court_poly(1.5).contains(Point(x, y)) for x, y in pts]).reshape(X.shape)
if _inside.any():
    _soft = ndimage.gaussian_filter(ndimage.binary_dilation(_inside, iterations=1).astype(float), 1.0)
    Hn = Hn * (1 - _soft) + float(Hn[_inside].mean()) * _soft

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

# --- old 노천극장 (1997): bowl carved into the hillside east of the stage
AMPH = dict(cx=160.0, cy=163.0, arena_rx=18.0, arena_ry=14.0, rows=15, row_d=1.6, row_h=0.45,
            rot=math.radians(45))      # local -x (stage / open side) faces SW, downhill; seats climb toward 안산
amph_poly = None
for wv in ways.values():
    if wv['id'] == 180788744:
        amph_poly = Polygon([xy(p) for p in wv['geometry']]).buffer(0)
AMPH['arena_h'] = round(sample(Hn, NEAR_HALF, NEAR_STEP, AMPH['cx'], AMPH['cy']) - 0.6, 2)


def amph_height(x, y):
    """Terraced bowl height (continuous); used both for terrain carving and Blender."""
    dx, dy = x - AMPH['cx'], y - AMPH['cy']
    c, s = math.cos(-AMPH['rot']), math.sin(-AMPH['rot'])
    u, v = dx * c - dy * s, dx * s + dy * c
    r = math.hypot(u / AMPH['arena_rx'], v / AMPH['arena_ry'])
    if r <= 1:
        return AMPH['arena_h']
    d = (r - 1) * min(AMPH['arena_rx'], AMPH['arena_ry'])
    return AMPH['arena_h'] + d / AMPH['row_d'] * AMPH['row_h']

R_OUT = AMPH['rows'] * AMPH['row_d'] + max(AMPH['arena_rx'], AMPH['arena_ry'])
# the bowl replaces the hillside (cut and fill), blending back over 30 m
for j in range(n_near):
    for i in range(n_near):
        x, y = gx[i], gx[j]
        dx, dy = x - AMPH['cx'], y - AMPH['cy']
        c_, s_ = math.cos(-AMPH['rot']), math.sin(-AMPH['rot'])
        u, v = dx * c_ - dy * s_, dx * s_ + dy * c_
        ang = math.atan2(v / AMPH['arena_ry'], u / AMPH['arena_rx'])
        r_el = math.hypot(u / (AMPH['arena_rx'] + AMPH['rows'] * AMPH['row_d']), v / (AMPH['arena_ry'] + AMPH['rows'] * AMPH['row_d']))
        if r_el > 2.2:
            continue
        open_side = abs(ang) > math.radians(128)          # stage side (west): flat apron
        hb = AMPH['arena_h'] + 0.1 if open_side else min(amph_height(x, y), AMPH['arena_h'] + AMPH['rows'] * AMPH['row_h']) - 0.25
        t = float(np.clip((r_el - 1.0) / (0.35 if open_side else 0.9), 0, 1))
        t = t * t * (3 - 2 * t)
        Hn[j, i] = hb * (1 - t) + Hn[j, i] * t

# ---------------------------------------------------------------------------
# Buildings
# ---------------------------------------------------------------------------


def ground_h(x, y):
    return sample(Hn, NEAR_HALF, NEAR_STEP, x, y)


def footprint(wv):
    pts_ = [xy(p) for p in wv['geometry']]
    if pts_[0] == pts_[-1]:
        pts_ = pts_[:-1]
    poly = Polygon(pts_).buffer(0)
    if isinstance(poly, MultiPolygon):
        poly = max(poly.geoms, key=lambda g: g.area)
    poly = poly.simplify(0.35)
    if not poly.exterior.is_ccw:
        poly = Polygon(list(poly.exterior.coords)[::-1])
    return poly


# --- level aprons in front of the old halls.  The 5 m terrain grid smooths the hillsides behind 스팀슨관, 아펜젤러관
# and 연희관 down across their fronts, so the ground fell 2-4 m within a few metres of the doors and the entrance flights
# grew to 16-20 risers.  The photos (reference/스팀슨관_정면_2016.jpg, 아펜젤러관_정면_2016.jpg) show 8-9 risers up
# from a level walk: each front gets a level apron at the height of the ground along its wall,
# blending back into the slope beyond.
FORECOURTS = [  # OSM way, outward front direction (None: the recess edge footprint[3] -> [4] of an H plan), depth, options
    # 언더우드관 (first, from the untouched ground): the garden walk level up to the foot of its 16 steps
    # (reference/언더우드관_정면_2016.jpg); the garden beyond is filled smoothly from here (below), so only a short blend
    (246156115, (0.27, -1.0), 12.0, dict(blend=8.0)),
    (246156118, (1.0, -0.27), 11.0, {}),      # 스팀슨관
    (246156116, (-1.0, 0.27), 11.0, {}),      # 아펜젤러관
    # (연희관's front: YEONHUI below, with the garden before it)
    # 대강당: the 45 m wide flight under the canopy ran across a 2 m cross slope, its north end under the grass
    (371403811, (-1.0, 0.25), 13.0, dict(max_half=27.0, blend=12.0)),
    # 대우관 별관: likewise the lower of its two flights (10 m wide) on the slope of the road past its front
    (242897923, (-0.97, 0.24), 9.0, dict(max_half=10.0, blend=10.0)),
    # 백주년기념관's 백양로 front: the smoothed DEM drapes the hall's own bulk over its west lawn, a 3-5 m mound
    # against its dark porch; the 1997 aerial photo shows level lawn (and parked cars) from the sidewalk to the porch.
    # Level it at the hall's floor (its lowest corner, a little over 백양로 alongside)
    (324328422, None, 30.0, dict(face=((-11.05, -181.26), (-28.82, -256.68)), max_half=40.0, blend=8.0, level='corner',
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
# 백주년기념관's low front block (issue #9).  In the 1997 aerial photo the hall's south-west corner is not the podium's
# corner but a lower block standing out in front of it, its long face towards the camera (the south face) with a wide
# dark entrance, its short west side with a dark door, and above that side a light wall stepping up towards the
# porch.  Back-projected with the photo's camera: the top edge of the west side (x 1523 -> 1587, y 630 -> 642) is a
# level line ~5.2 m up in a plane ~6 m west of the podium's 백양로 face, so the block's corner (x 1587) stands about
# 3.5 m south of the outline's south face; its front runs on east past the drum (to x ~2000), and the entrance spans
# 0.7 - 9.7 m from the corner (x 1597 - 1730; its foot is behind the trees).  blender/landmarks.py builds it from this.
_cnw, _csw, _cse = np.array([-11.05, -181.26]), np.array([-28.82, -256.68]), np.array([-12.33, -261.24])
_tw = (_cnw - _csw) / np.linalg.norm(_cnw - _csw)                 # the 백양로 face, south -> north
_ts = (_cse - _csw) / np.linalg.norm(_cse - _csw)                 # the south face, west -> east
_nw = np.array([-_tw[1], _tw[0]])                                 # out of the 백양로 face (west)
_c0 = _csw + _nw * 6.0 - _tw * 3.3
CENT_BLOCK = dict(corner=[round(float(v), 2) for v in _c0], t_front=[round(float(v), 4) for v in _ts],
                  t_side=[round(float(v), 4) for v in _tw], front=33.0, side=19.6, h=5.2,
                  entrance=[0.7, 9.7, 2.7], door=[13.2, 15.8, 2.5], parapet=[(19.6, 25.0, 6.0), (25.0, 30.0, 6.8)])
CENT_BLOCK['poly'] = [[round(float(v), 2) for v in q] for q in
                      (_c0, _c0 + _ts * 33.0, _c0 + _ts * 33.0 + _tw * 19.6, _c0 + _tw * 19.6)]
# (its forecourt: level at the hall's floor like the 백양로 side, so the entrance is not half buried)
FORECOURTS.append((324328422, None, 14.0, dict(face=(tuple(_c0), tuple(_c0 + _ts * 33.0)), max_half=16.5, blend=8.0,
                                                level='corner', inside=1.0)))
# 백주년기념관's museum entrance (blender/landmarks.py museum_entrance): the 1996 album photos of 화학공학 · 전기 · 전자 ·
# 건축공학 · 기계설계 · 컴퓨터과학과 stand on a level paved forecourt at the foot of a broad granite flight, a storey and a
# half of glass leaning out between a white cylinder and a white wall behind them.  It is the north-east face, towards
# 광혜원 and 수경원 (연세 역사의 뜰, laid out in 1987 with the hall, "spatially one with the museum inside the hall"):
# the right of the photos runs on into the drum's curved foot, the 백양로 side is the concert hall's dark porch, and
# the south and east faces stand a few metres from the hospital.  The ground there stood 3 m over the hall's floor
# (the hall's lowest corner, by 백양로); the forecourt is levelled at 광혜원's height, nine risers below the doors.
CENT_NE = ((41.28, -200.97), (16.84, -168.65))       # the face, its outside to the right
CENT_PLAZA_H = 42.7
FORECOURTS.append((324328422, None, 18.0, dict(face=CENT_NE, max_half=20.3, blend=10.0, level=CENT_PLAZA_H, inside=1.0)))
# 과학관's courtyard flight (blender/generic.py porch, ENTRY_AT): in the 1996 photos of 생물학과, 생화학과 and 지질학과
# fifteen-odd granite risers climb the whole width of the picture to the cream wall, between sloped granite side walls
# with clipped junipers on banks either side, a five-globe lamp at the top.  The 5 m grid ran the courtyard's slope
# up to the doors (five risers); the car park below is levelled 2.8 m under them and banks back up beside the flight.
SCI_DOOR, SCI_N = np.array([-242.6, 13.81]), np.array([-0.2629, -0.9648])
SCI_T = np.array([-SCI_N[1], SCI_N[0]])
_sf = SCI_DOOR + SCI_N * 1.6                         # the head of the flight (the plaza runs in under it)
FORECOURTS.append((222843398, None, 20.0, dict(face=(tuple(_sf - SCI_T * 8.8), tuple(_sf + SCI_T * 8.8)), max_half=8.8,
                                                blend=8.0, side_blend=3.0, level=58.9, inside=0.0)))
# 빌링슬리관's south front (its door: ENTRY_AT).  The 5 m grid ran the slope from the north-west across it, 3.7 m
# along the 45 m front, so the door in its middle stood 1.6 m under the ground and the west half of the ground floor
# was buried.  reference/학교연혁_빌링슬리관_옛생활과학관.jpg, from the lawn at the west end, shows the ground floor
# standing on a level lawn all along the front: level it at the floor (its south-east corner), a riser or two under
# the threshold, banking back up into the hill at the west end.
BILL_FRONT = ((14.11, 417.87), (57.73, 406.29))      # the south front, west -> east (the outside to the right)
FORECOURTS.append((245623193, None, 12.0, dict(face=BILL_FRONT, max_half=23.0, blend=10.0, side_blend=9.0,
                                                level=round(68.85 - drop_at(36.0, 412.0), 2), inside=2.0)))  # (68.85 before)
# 교육관 (blender/landmarks.py gyoyuk): its west side stands three full storeys over the drive below 제2인문관
# (reference/2003_가을_교육관_서쪽면.jpg, taken from there) and its north end's outside flight starts from a yard of
# parked cars at the ground floor (2003_가을_연희관앞정원과_교육관_북쪽계단.jpg).  The 5 m grid ran the hill from 종합관
# and 제2인문관 down over both: the ground stood 3-4 m over the floor at the north-west corner.  Level the drive and
# the yard at the floor, banking back up to the hill beyond.
GYOYUK_FLOOR = 53.0                                  # (blender/landmarks.py GYOYUK_FLOOR)
FORECOURTS.append((246156111, None, 6.0, dict(face=((26.82, 349.67), (17.82, 314.97)), max_half=18.0, blend=7.0,
                                               side_blend=6.0, level=GYOYUK_FLOOR, inside=1.0)))      # the west drive
FORECOURTS.append((246156111, None, 11.0, dict(face=((44.15, 345.23), (26.82, 349.67)), max_half=9.0, blend=6.0,
                                                side_blend=5.0, level=GYOYUK_FLOOR, inside=1.0)))     # the north yard


def level_forecourt(wid, front, depth, blend=18.0, side_blend=7.0, max_half=20.0, level=None, face=None, inside=2.0):
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
        level = min(sample(Hn, NEAR_HALF, NEAR_STEP, x_, y_) for x_, y_ in poly.exterior.coords)
    if level is None:
        level = float(np.mean([sample(Hn, NEAR_HALF, NEAR_STEP, mx + tx * s + fx, my + ty * s + fy) for s in np.linspace(-hw, hw, 7)]))
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


def near_buildings(pad):
    """Grid nodes within pad m of a campus building's footprint (whose own ground the fills must not move)."""
    m = np.zeros(X.shape, bool)
    for wid in B:
        if wid in ways:
            m |= shapely.contains_xy(footprint(ways[wid]).buffer(pad), X, Y)
    return m


# --- 중앙도서관: level all round.  The 5 m grid drapes the slope behind it (and the bulk of the 학술정보원 built
# against its back in the 2000s) over the hall: the ground stood 6 m over the front plaza at its north-west corner, so
# the back and the north end were buried past the ground floor.  The 1997 photos show the piers coming down to a
# level walk; give the hall a level apron 6 m wide at the height of its 백양로 forecourt on every side, and fill the
# ground from there out to 30 m with one smooth surface (so the rise to the slope behind is spread over the lawn).
_lib = footprint(ways[163525865])
_lf0, _lf1 = np.array([-85.44, -71.08]), np.array([-65.91, 3.16])           # the 백양로 front, south -> north
_lfn = np.array([(_lf1 - _lf0)[1], -(_lf1 - _lf0)[0]]) / np.linalg.norm(_lf1 - _lf0)   # out of it (east)
LIBRARY_LEVEL = float(np.mean([sample(Hn, NEAR_HALF, NEAR_STEP, *(_lf0 + (_lf1 - _lf0) * f + _lfn * 3.0))
                               for f in np.linspace(0.05, 0.95, 9)]))
_lap = shapely.contains_xy(_lib.buffer(6.0, join_style=2), X, Y) & (dist > ROAD_HALF + 4)
Hn[_lap] = LIBRARY_LEVEL
FIXED[_lap] = True
_lring = shapely.contains_xy(_lib.buffer(30.0), X, Y) & ~_lap & ~FIXED & (dist > ROAD_HALF + 4) & ~near_buildings(1.0)
harmonic_fill(_lring)
print('library apron', round(LIBRARY_LEVEL, 2))


# --- 언더우드관 정원 남쪽 계단 (reference/2003_봄_언더우드관정원_남쪽계단_벚나무.jpg, from the head of 백양로 looking
# north; reference/고증.md 3.18).  The garden's south edge stood some 2 m over the 삼거리: two flights of granite steps
# rose from the road either side of a planted bed with a stone tablet to a landing, and one broad flight went on up the
# axis to the terrace with the statue, between grass banks set with clipped round shrubs and topped by a border of
# yellow pansies, the big cherries along the top and a white-stemmed poplar by the foot.  The game had a level paved
# plaza there.  Now: the terrace along the garden's south edge at the road's level plus fourteen risers of 0.15, the
# banks a straight grade down to the road, the ground under the steps kept below their treads; the garden falls from
# the terrace to 언더우드관's front (GARDEN_FILL below).  blender/landmarks.py underwood_steps builds them (UW_STEPS).
_wuo = np.array([62.0, 213.0])
_wuu = np.array([0.970, -0.243]) / math.hypot(0.970, -0.243)
_wuv = np.array([-_wuu[1], _wuu[0]])                         # (WU below: u across the garden, v up its axis)


def wu_xy(u, v):
    return tuple(float(c) for c in _wuo + _wuu * u + _wuv * v)


UWU = (X - _wuo[0]) * _wuu[0] + (Y - _wuo[1]) * _wuu[1]
UWV = (X - _wuo[0]) * _wuv[0] + (Y - _wuo[1]) * _wuv[1]
_H0 = sample(Hn, NEAR_HALF, NEAR_STEP, *wu_xy(0.0, -45.0))     # the road at the foot
# (widths from the people on them in the photo, about 88 px/m at the foot: the whole about 9 m across)
UW_STEPS = dict(rise=0.15, n=7, tread=0.32, v_top=-34.5, land=(-40.4, -37.14), land_hw=3.65, cheek=0.35,
                low=dict(u=2.3, w=2.7), up=dict(w=3.6), bed=(-42.9, -40.4), v_bank=-43.0)
UW_STEPS.update(h0=round(_H0, 2), hl=round(_H0 + 7 * 0.15, 2), ht=round(_H0 + 14 * 0.15, 2))
_US = UW_STEPS


def _uw_flight(name, u, v, width, z_top, z_foot, landing):
    foot = wu_xy(u, v - landing - _US['n'] * _US['tread'])
    return dict(name=name, top=[round(c, 2) for c in wu_xy(u, v)], down=[round(-float(_wuv[0]), 4), round(-float(_wuv[1]), 4)],
                foot=[round(c, 2) for c in foot], z_top=z_top, z_foot=z_foot, n=_US['n'], width=width, landing=landing,
                tread=_US['tread'], cheek=_US['cheek'])


_US['flights'] = [_uw_flight('uw_up', 0.0, _US['v_top'], _US['up']['w'], _US['ht'], _US['hl'], 0.4)] + \
    [_uw_flight('uw_low_%s' % ('w' if sg < 0 else 'e'), sg * _US['low']['u'], _US['land'][0] + 0.3, _US['low']['w'], _US['hl'],
                _US['h0'], 0.3) for sg in (-1, 1)]
_US['frame'] = dict(o=[float(c) for c in _wuo], u=[round(float(c), 5) for c in _wuu], v=[round(float(c), 5) for c in _wuv])
# the terrace (up to the statue's line) and the banks, fading into the ground beyond the garden's corners
_H_pre = Hn.copy()
_reg = (np.abs(UWU) < 32.0) & (UWV > _US['v_bank'] - 0.01) & (UWV < -26.0) & ~near_buildings(1.5)
_zf = np.array([sample(_H_pre, NEAR_HALF, NEAR_STEP, *wu_xy(u_, _US['v_bank'])) for u_ in UWU[_reg]])
_tb = np.clip((UWV[_reg] - _US['v_bank']) / (_US['v_top'] - _US['v_bank']), 0.0, 1.0)
_wl = 1 - _smooth((np.abs(UWU[_reg]) - 20.0) / 10.0)
Hn[_reg] += _wl * (_zf + (_US['ht'] - _zf) * _tb - Hn[_reg])
FIXED[_reg] = True
_stp = np.hypot(X - 55.5, Y - 187.5) < 6.0                   # the statue on the terrace, its round steps level
Hn[_stp] = _US['ht']
FIXED[_stp] = True
# under the steps, the landing, the bed and the raised beds behind the landing: below their tops
_zc = np.where(UWV < -42.64, _US['h0'], np.where(UWV < -40.4, _US['h0'] + (_US['hl'] - _US['h0']) * (UWV + 42.64) / 2.24,
               np.where(UWV < -37.14, _US['hl'], _US['hl'] + (_US['ht'] - _US['hl']) * np.clip((UWV + 37.14) / 2.24, 0, 1))))
_sz = (np.abs(UWU) < 6.5) & (UWV > -45.5) & (UWV < -33.5)
Hn[_sz] = np.minimum(Hn[_sz], _zc[_sz] - 0.7)                 # (low enough for the 5 m chords to clear)
FIXED[_sz] = True
print('언더우드관 정원 남쪽 계단: road %.2f, landing %.2f, terrace %.2f m' % (_US['h0'], _US['hl'], _US['ht']))


# --- 언더우드관 앞 정원 (issue #3).  The level aprons of 스팀슨관 (51.6 m) and 아펜젤러관 (54.3 m) face each other across
# the garden, but the 5 m grid keeps a hollow down its middle (49.4 m): each apron ended in a grass bank, 5 m over 18 m
# in front of 아펜젤러관, where the photos (reference/아펜젤러관_정면_2016.jpg, 언더우드관_2024_여름_계단에서_본_정원.jpg) show
# the garden walks running nearly level to the foot of the steps.  Fill the garden between the aprons, the foot of
# 언더우드관's flight and the statue with one smooth surface: the 2.7 m between the aprons becomes an even fall across
# the garden, the hollow goes.  Kept as they are: the aprons, 언더우드관's front (its flight is measured from it) and
# the ground under the Underwood statue (statues.underwood_statue.h).
GARDEN_FILL = Polygon([(27, 190), (84, 176), (84, 243), (44, 249)])
_free = shapely.contains_xy(GARDEN_FILL, X, Y) & ~FIXED & ~near_buildings(1.5)
_free &= np.hypot(X - 55.5, Y - 187.5) > 6.0                 # the statue on its round steps (on the terrace: UW_STEPS)
harmonic_fill(_free)


def fix_strip(line_pts, h0, h1, half, top=False):
    """Grid nodes within half m of a polyline (not past its ends) get a straight grade from h0 to h1 along it.
    top: only lower them to it (the ground under a flight must stay below its treads)."""
    ls = LineString(line_pts)
    m = shapely.contains_xy(ls.buffer(half, cap_style='flat'), X, Y)
    z = h0 + (h1 - h0) * shapely.line_locate_point(ls, shapely.points(X[m], Y[m])) / ls.length
    Hn[m] = np.minimum(Hn[m], z) if top else z
    FIXED[m] = True
    return m


# --- 연희관 앞 정원: between 언더우드관's back and 연희관 (OSM; reference/연희관_정면_2023.jpg, 학교연혁_연희관.jpg from
# its south walk, 대우관_블로그_연희관과_대우관_원경.jpg from above to the west, the 1995 map's star-shaped garden).
# A diamond of walks round a round planter, a cross of walks through it, four beds edged with clipped boxwood.  It is
# a level terrace (a 4 % rise northwards) a short flight over 한경길 (OSM 5 m: 16 risers); to the north a planted bank
# with a broad flight between low walls (OSM 10 m: 32 risers) climbs to the road before 연희관, whose entrance flight
# (nineteen risers, a landing) rises from the road between the wings.  West and east, walled flights come down into
# the garden's side corners from the drives along 교육관 and 성암관.  The 5 m grid had one 30 % slope from 한경길 to
# the door; now: 한경길 45.6 -> garden 48.0 (the S node) .. 49.4 (the N node) -> road 54.3 -> door 57.3.
YH_DIAMOND = [(74.4, 302.5), (52.7, 325.4), (82.5, 335.4), (103.4, 312.1)]      # S, W, N, E nodes of the walks
YH_C = (78.4, 318.3)                                                            # the round planter (GF_C)
_zh = sample(Hn, NEAR_HALF, NEAR_STEP, 73.1, 297.5)                             # 한경길 at the foot of the S flight
YEONHUI = dict(garden=round(_zh + 2.4, 2), slope=0.04, planter=dict(c=list(YH_C), r=3.2, h=0.5))


def yh_plane(e, n):
    return YEONHUI['garden'] + YEONHUI['slope'] * (n + 16.3)          # (n = -16.3 at the S node)


def g_en(x, y):
    d_ = np.array([x, y]) - GF_C
    return float(d_ @ GF_E), float(d_ @ GF_N)


def flight_at(name, top, down, z_top, z_foot, width, landing=0.6, tread=0.30, maxrise=0.165, **kw):
    d_ = np.array(down, float) / np.linalg.norm(down)
    n_ = int(math.ceil((z_top - z_foot) / maxrise - 1e-6))
    foot = np.array(top) + d_ * (landing + n_ * tread)
    return dict(name=name, top=[round(float(top[0]), 2), round(float(top[1]), 2)], down=[round(float(d_[0]), 4), round(float(d_[1]), 4)],
                foot=[round(float(foot[0]), 2), round(float(foot[1]), 2)], z_top=round(float(z_top), 2), z_foot=round(float(z_foot), 2),
                n=n_, width=width, landing=landing, tread=tread, **kw)


# the north flight: from the road's south edge on the OSM line down onto the garden's axis walk, 32 risers of 0.16
_un = np.array([85.2 - 82.5, 345.0 - 335.4]) / math.hypot(85.2 - 82.5, 345.0 - 335.4)
_tn = np.array([85.2, 345.0]) - _un * 3.0
_fn = _tn - _un * (0.6 + 32 * 0.31)
_zfn = yh_plane(*g_en(*_fn))
YEONHUI['road'] = round(_zfn + 32 * 0.16, 2)                  # the road before 연희관, on the garden's axis
YEONHUI['floor'] = round(YEONHUI['road'] + 3.0, 2)            # 연희관's door (blender: gothic z_floor)
_rw, _rc, _re = YEONHUI['road'] + 1.3, YEONHUI['road'], YEONHUI['road'] - 1.5       # the road's west end, axis, east end
_hw0 = sample(Hn, NEAR_HALF, NEAR_STEP, 40.3, 301.6)          # 한경길 where the west drive leaves it
_he0 = sample(Hn, NEAR_HALF, NEAR_STEP, 106.6, 289.8)         # and the east one
for _ln in ([(154.1, 270.8), (149.3, 272.5), (105.3, 286.1), (72.5, 295.2), (52.5, 300.2), (40.3, 301.6)],
            [(40.3, 301.6), (52.2, 296.6), (71.4, 290.9), (104.1, 281.3), (147.7, 268.6)]):
    _m = shapely.contains_xy(LineString(_ln).buffer(3.5, cap_style='flat'), X, Y)
    FIXED[_m] = True                                          # 한경길 itself stays as it was
_FRONT_RD = [(51.7, 354.5), (85.2, 345.0), (118.8, 335.6)]
_W_RD = [(40.3, 301.6), (40.7, 306.0), (41.7, 310.2), (45.5, 327.4), (51.7, 354.5)]
_E_RD = [(106.6, 289.8), (111.9, 310.1), (118.8, 335.6)]
fix_strip(_FRONT_RD[:2], _rw, _rc, 3.5)
fix_strip(_FRONT_RD[1:], _rc, _re, 3.5)
fix_strip(_W_RD, _hw0, _rw, 3.5)
fix_strip(_E_RD, _he0, _re, 3.5)
_wrd, _erd = LineString(_W_RD), LineString(_E_RD)
# the garden terrace, its walks and a metre beyond
_gd = shapely.contains_xy(Polygon(YH_DIAMOND).buffer(2.0), X, Y)
Hn[_gd] = yh_plane(GE[_gd], GN[_gd])
FIXED[_gd] = True
# the court between 연희관's wings: from the foot of its walls (the floor less the 1.2 m plinth) down to the road
_yfp = list(footprint(ways[245623759]).exterior.coords)
_ya, _yb = np.array(_yfp[3]), np.array(_yfp[4])
_yt = (_yb - _ya) / np.linalg.norm(_yb - _ya)
_yn = np.array([-_yt[1], _yt[0]])
YH_U = (X - _ya[0]) * _yt[0] + (Y - _ya[1]) * _yt[1]
YH_V = (X - _ya[0]) * _yn[0] + (Y - _ya[1]) * _yn[1]
_ct = (YH_U > -14.5) & (YH_U < 52.5) & (YH_V > -10.6) & (YH_V < -0.8) & ~near_buildings(0.3)
_rd_u = np.interp(YH_U[_ct], [float((np.array(p_) - _ya) @ _yt) for p_ in _FRONT_RD], [_rw, _rc, _re])   # (its grade)
Hn[_ct] = (YEONHUI['floor'] - 1.2) + (_rd_u - (YEONHUI['floor'] - 1.2)) * np.clip(-YH_V[_ct] / 10.5, 0, 1)
FIXED[_ct] = True
# the flights (blender/landmarks.py yeonhui_garden builds them from these)
_dw = np.array([52.7 - 45.5, 325.4 - 327.4]); _dw /= np.linalg.norm(_dw)
_tw = np.array([45.5, 327.4]) + _dw * 3.0
_de = np.array([103.4 - 111.9, 312.1 - 310.1]); _de /= np.linalg.norm(_de)
_te = np.array([111.9, 310.1]) + _de * 3.0
_ds = np.array([73.1 - 74.4, 297.5 - 302.5]); _ds /= np.linalg.norm(_ds)
_zw = float(_hw0 + (_rw - _hw0) * _wrd.project(Point(*_tw)) / _wrd.length)
_zeo = float(_he0 + (_re - _he0) * _erd.project(Point(*_te)) / _erd.length)
YEONHUI['flights'] = [
    flight_at('north', _tn, -_un, YEONHUI['road'], _zfn, 5.0, landing=0.6, tread=0.31, maxrise=0.16, cheek=0.4),
    flight_at('south', YH_DIAMOND[0], _ds, yh_plane(*g_en(*YH_DIAMOND[0])), _zh, 4.0, landing=0.5, maxrise=0.15, cheek=0.35),
]
_fw = flight_at('west', _tw, _dw, _zw, 0.0, 3.2, landing=0.5, cheek=0.35, maxrise=0.16)
_fw = flight_at('west', _tw, _dw, _zw, yh_plane(*g_en(*_fw['foot'])), 3.2, landing=0.5, cheek=0.35, maxrise=0.16)
_fe = flight_at('east', _te, _de, _zeo, 0.0, 3.2, landing=0.5, cheek=0.35, maxrise=0.16)
_fe = flight_at('east', _te, _de, _zeo, yh_plane(*g_en(*_fe['foot'])), 3.2, landing=0.5, cheek=0.35, maxrise=0.16)
YEONHUI['flights'] += [_fw, _fe]
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
# the rest of the block (the banks, the lawns between the garden and 한경길, the verges along 교육관 and 성암관) one
# smooth surface between all that
_blk = Polygon(_W_RD + _FRONT_RD[1:] + _E_RD[::-1][1:] + [(105.3, 286.1), (72.5, 295.2), (52.5, 300.2)]).buffer(8.0)
_free = shapely.contains_xy(_blk, X, Y) & (GN > -24.0) & ~FIXED & ~near_buildings(1.0)
harmonic_fill(_free)
print('연희관 앞', {k: v for k, v in YEONHUI.items() if k != 'flights'},
      [(f_['name'], f_['n'], f_['z_top'], f_['z_foot']) for f_ in YEONHUI['flights']])

# --- 대우관 (reference/대우관_정면_전경.jpg, 대우관_2024_정면과_상뜰.jpg, 대우관_측면_2012.jpg): the hall stands on a
# terrace about 6 m over the 상뜰.  A white stone podium projects from the tower with the main door at the plaza level
# (no steps: a wide low arch, a glazed lobby behind) and flights climb to the terrace beside it; the tower's own
# pointed door opens onto the terrace.  The 5 m grid smooths all this into one 20% slope down to the 상뜰, so: the
# courtyard between the wings goes down to the plaza level (under the terrace, out of sight), the plaza in front of the
# podium is level, falling 4% away from it, and the ground around meets it with one smooth surface.
# The hall itself stays where it stood (its floor from the ground just in front of the tower, as blender's gothic()
# measured it), and blender reads the levels back from campus.json (daewoo_front).
_fp = list(footprint(ways[242897922]).exterior.coords)
_a, _b = np.array(_fp[3]), np.array(_fp[4])
_t = (_b - _a) / np.linalg.norm(_b - _a)
_nl = np.array([-_t[1], _t[0]])                                  # into the hall
DW_U = (X - _a[0]) * _t[0] + (Y - _a[1]) * _t[1]                 # along the recessed front, from its west end
DW_V = (X - _a[0]) * _nl[0] + (Y - _a[1]) * _nl[1]              # towards the hall (its front wall at v = 0)
_door = _a + _t * 23.55 + _nl * -3.3
_floor = sample(Hn, NEAR_HALF, NEAR_STEP, *_door) + 1.3          # the door threshold (blender: z0 + plinth - 0.1)
DAEWOO = dict(floor=round(_floor, 2), terrace=round(_floor - 0.45, 2), plaza=round(_floor - 0.45 - 6.0, 2),
              podium=-17.0, fall=0.04, u0=-12.1, u1=55.5)
_P = DAEWOO['plaza']
_court = (((DW_U > -1.0) & (DW_U < 48.2) & (DW_V > -17.5) & (DW_V < 1.0))         # under the podium and the terrace
          | ((DW_U > -12.0) & (DW_U < 55.4) & (DW_V > -17.5) & (DW_V < -10.5)))    # and its planted steps before the wings
_strip = (DW_U > -12.0) & (DW_U < 59.0) & (DW_V <= -17.0) & (DW_V > -31.0)        # the plaza in front of it
Hn[_court] = _P
Hn[_strip] = _P - DAEWOO['fall'] * (-17.0 - DW_V[_strip])
# 상뜰 (issue #39; reference/대우관_정면_전경.jpg, 대우관_2024_정면과_상뜰.jpg): a level terrace, not the 11 - 16 % slope the
# smooth fill made south of the plaza.  From the plaza's level at the diamond's north node it falls 2.5 % southwards
# and 1.5 % west / 1 % east of its axis, so its side nodes meet the drives (east within 0.2 m, west by a short ramp).
# At its south node a broad granite flight with steel handrails on both sides goes down through the trees to the
# footway (OSM 1451337739, 7 m: 22 risers of 15.5 cm), which runs straight between its ends but for the foot of the
# flight; the bank round it and under the diamond's lower walks is filled smoothly (and planted, below).
# (SG: e east along the hall, n north, from the round lawn's centre.)
SANG = (106.8, 427.1)
SG_E = np.array([0.964, -0.263])
SG_N = np.array([0.263, 0.964])
SG = lambda e, n: tuple(np.array(SANG) + SG_E * e + SG_N * n)
SANG_DIAMOND = [SG(-0.8, 14.2), SG(-26.5, 0.0), SG(0.0, -15.3), SG(26.6, 0.4)]       # N, W, S, E nodes of the walks
_vN = float((np.array(SANG_DIAMOND[0]) - _a) @ _nl)
SANG_LV = dict(top=round(_P - DAEWOO['fall'] * (-17.0 - _vN), 2), fall=0.025, west=0.015, east=0.01)


def sang_h(e, n):
    return SANG_LV['top'] + SANG_LV['fall'] * (n - 14.2) - np.where(e < 0, SANG_LV['west'], SANG_LV['east']) * np.abs(e)


_SE = (X - SANG[0]) * SG_E[0] + (Y - SANG[1]) * SG_E[1]
_SN = (X - SANG[0]) * SG_N[0] + (Y - SANG[1]) * SG_N[1]
_sg = shapely.contains_xy(Polygon(SANG_DIAMOND).buffer(3.0), X, Y) & ~_court
Hn[_sg] = sang_h(_SE[_sg], _SN[_sg])
FIXED[_sg] = True
_zS = float(sang_h(0.0, -15.3))
_ds_ = np.array([101.2, 405.4]) - np.array(SANG_DIAMOND[2])
DAEWOO['sang'] = SANG_LV
DAEWOO['stair'] = flight_at('sang_south', SANG_DIAMOND[2], _ds_, _zS, _zS - 22 * 0.155, 5.5, landing=0.5, tread=0.30,
                            maxrise=0.155, rails=True, cheek=0.25)
_fwW, _fwE = sample(Hn, NEAR_HALF, NEAR_STEP, 66.6, 414.3), sample(Hn, NEAR_HALF, NEAR_STEP, 137.7, 396.5)
fix_strip([(66.6, 414.3), (101.2, 405.4)], _fwW, DAEWOO['stair']['z_foot'], 1.8)
fix_strip([(101.2, 405.4), (137.7, 396.5)], DAEWOO['stair']['z_foot'], _fwE, 1.8)
_st = DAEWOO['stair']
fix_strip([_st['top'], _st['foot']], _st['z_top'] - 0.35, _st['z_foot'] - 0.25, _st['width'] / 2 + 1.6, top=True)
print('상뜰', SANG_LV, 'S node %.2f, footway %.2f .. %.2f .. %.2f' % (_zS, _fwW, _st['z_foot'], _fwE))
_free = (DW_U > -32) & (DW_U < 80) & (DW_V > -74) & (DW_V < 4) & ~_court & ~_strip & ~FIXED & ~near_buildings(1.0)
harmonic_fill(_free)
print('daewoo', DAEWOO)
# --- 대우관 뒤 (Google Street View, 2009-11, from the drive behind the hall and from the road to 북문 east of it; the
# hall itself opened in June 1996, so its back and yard looked the same in 1997).  The hall's back faces a large
# car park on a terrace at about its ground floor: three rows of cars east of the middle, a lawn mound with clipped
# pines west of it (the drive from the west road to the car park runs between that and the hall), and along the back
# of the hall, in the recess between the wings, a long planter with low concrete walls and pointed conifers.  The
# road to 북문 runs above the car park's east side behind an iron fence, on a planted bank.  The 5 m grid had only a
# slope rising 9 m from west to east across all this: the yard becomes one plane falling gently westwards (as a car
# park drains), the ground round it one smooth surface.  (u, v) as above: u along the hall from the west end of its
# front, v from the front wall to the back (the back wall at v = 14.8, the wings' back ends at v = 24.4).
DAEWOO_BACK = dict(h0=round(DAEWOO['floor'] - 0.1, 2), su=0.01, sv=0.03, u0=45.0, v0=26.0,
                   yard=[(-4.0, 14.9), (46.5, 14.9), (46.5, 24.4), (66.0, 24.4), (64.5, 79.0), (24.5, 79.0), (24.5, 27.0),
                         (-12.5, 27.0), (-12.5, 24.4), (-4.0, 24.4)],
                   lot=[(25.0, 25.0), (66.0, 25.0), (64.0, 78.0), (25.0, 78.0)],
                   planter=[(2.0, 17.6), (44.6, 17.6), (44.6, 23.2), (2.0, 23.2)],
                   # rows of stalls either side of the aisles OSM has (u = 33 and 49, a cross aisle at v ~ 53),
                   # cars nose in: (row centre u, which way they face along u)
                   rows=[(27.6, -1), (38.4, 1), (43.6, -1), (54.4, 1), (59.6, -1)], stall=2.6, row_v=(33.0, 76.0),
                   gap=(50.4, 56.6), fence=[(74.5, 25.0), (71.5, 38.0), (67.8, 68.0), (67.2, 79.0)])
_db = DAEWOO_BACK
_yard = shapely.contains_xy(Polygon(_db['yard']), DW_U, DW_V)
# (at the floor's height all along the back wall, as Street View shows the hall's back doors level with the yard; it
# rose 3 % eastwards too, which stood it up to 0.9 m against the east wing's back: now 1 % falling west, and the 3 %
# rise only northwards past the wings)
Hn[_yard] = _db['h0'] + _db['su'] * (DW_U[_yard] - _db['u0']) + _db['sv'] * np.maximum(0.0, DW_V[_yard] - _db['v0'])
FIXED[_yard] = True
_free = (DW_U > -40) & (DW_U < 90) & (DW_V > 10) & (DW_V < 115) & ~_yard & ~FIXED & ~near_buildings(1.0)
harmonic_fill(_free)
print('daewoo back yard', _db['h0'])
# 대우관's sides and back ends.  The grid nodes within a metre of a hall are left out of the smooth fills above, so
# the old surface (the elevation data still holding a little of the hall's own bulk) stayed against its walls: a
# mound up to 1 m over the ground floor along the east wing's back and side, half burying the lowest windows, and on
# the west the bare slope 2-3 m under the floor, baring the dark granite foundation all along the wing.  The 2012
# photo (reference/대우관_측면_2012.jpg) and Street View show the hall standing on its ground floor all round, the
# lawns falling away from a walk along its walls: a 3 m apron at the floor's height round the wings' sides and the
# back, blending into the ground over the next 7 m (not across the front court, the yard or the other aprons).
_dwp = footprint(ways[242897922])
_bb = (DW_U > -40) & (DW_U < 95) & (DW_V > -14) & (DW_V < 60) & ~FIXED & ~_court & ~_strip
_jj, _ii = np.nonzero(_bb)
_dd = shapely.distance(_dwp, shapely.points(X[_jj, _ii], Y[_jj, _ii]))
_uu, _vv = DW_U[_jj, _ii], DW_V[_jj, _ii]
_w = np.clip(1 - (_dd - 3.0) / 7.0, 0, 1) * (((_uu < 0.5) | (_uu > 46.5)) * np.clip((_vv + 12.0) / 4.0, 0, 1) + (_vv > 14.0))     # (beside and under the wings)
_w = np.clip(_w, 0, 1)                         # (the nodes under the wings too, or the walls' foot dips between nodes)
DW_APRON = round(DAEWOO['floor'] - 0.15, 2)
Hn[_jj, _ii] = Hn[_jj, _ii] * (1 - _w) + DW_APRON * _w
print('daewoo sides apron', DW_APRON, 'nodes', int((_w > 0).sum()))

buildings = []
campus_polys = []
for wid, (style, lv, label) in B.items():
    wv = ways.get(wid)
    if not wv:
        print('missing', wid, label)
        continue
    poly = Polygon(FOOTPRINT_1997[wid]) if wid in FOOTPRINT_1997 else footprint(wv)
    campus_polys.append(poly)
    hs = [ground_h(x, y) for x, y in poly.exterior.coords]
    fh = FLOOR_H.get(style, 4.0)
    buildings.append(dict(id=wid, name=label, style=style, levels=lv,
                          height=round(lv * fh + (1.2 if not style.startswith('lm') else 0), 2),
                          base=round(min(hs), 2), top_ground=round(max(hs), 2),
                          footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]]))

# 용재관 (demolished; 경영관 has stood on its site since 2015, so it is not in OSM).  Placed from the 경영관 indoor
# corridors in OSM (x 72..120, y 88..136) and reference/용재관.jpg, taken from behind the Underwood statue looking
# south-east: a white modernist hall whose slender stair tower faces the end of 백양로, a three-storey wing with a
# dark hipped roof and the entrance canopy beside it, and a five-storey block behind.
YONGJAE = dict(o=(74.0, 124.0), ang=math.radians(20), parts=[
    (990001, 'lm:yongjae', 7, (-3.2, 3.2, -4, 3.5)),        # tower: u0, u1, v0, v1 (v = towards 백양로 / the statue)
    (990002, 'lm:none', 3, (3.2, 34, -11, 1)),          # wing
    (990003, 'lm:none', 5, (-2, 36, -27, -11)),       # block
])


def yongjae_poly(u0, u1, v0, v1):
    (ox, oy), a = YONGJAE['o'], YONGJAE['ang']
    c, s_ = math.cos(a), math.sin(a)
    return Polygon([(ox + u * c - v * s_, oy + u * s_ + v * c) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))])


for pid, style, lv, uv in YONGJAE['parts']:
    poly = yongjae_poly(*uv)
    campus_polys.append(poly)
    hs = [ground_h(x, y) for x, y in poly.exterior.coords]
    buildings.append(dict(id=pid, name='용재관', style=style, levels=lv, height=round(lv * 3.6, 2),
                          base=round(min(hs), 2), top_ground=round(max(hs), 2),
                          footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]],
                          frame=dict(o=YONGJAE['o'], ang=round(YONGJAE['ang'], 5), uv=uv)))

# Halls on the 1990 · 1994 · 1995 campus maps that OSM no longer has (reference/1990_캠퍼스_지도.png,
# 1994_캠퍼스_지도.jpg, 1995_캠퍼스_지도.jpg; reference/고증.md).  Behind (west of) 중앙도서관, where
# 삼성학술정보관 stands now: 23 어학당, a long three-storey hall curved like a bow, its convex side to the west and
# south-west, and 24 장기원 기념관, a four-storey block across the library's axis with a rounded west end and a low
# round hall at its south-west foot (the 1994 map draws both; 서울신문 1996.9.3: classes moved to the temporary rooms
# of the 기념관 "도서관 뒤쪽" that September).  The 한국어학당 left the bow-shaped hall for its own building in April
# 1991 (yonsei.ac.kr/sc/349), so a student of 1997 knew it as the old one.  12 청경관, a student cafeteria, low at the
# foot of a crescent of planting south-west of 유억겸 기념관 and west of 언더우드관: the triangle between the three
# drives there.  (16 요업관, the other cafeteria, stood behind 연희관 where 대우관's 상뜰 was laid out in 1996.)
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


_lib_u = np.array([0.2544, 0.9671])                   # 중앙도서관's long axis
_jk = np.array([-150.0, -25.0])
OLD_HALLS = [
    (990010, '옛 어학당', 'white', 3, arc_poly((-147.0, 18.0), 30.0, 40.0, 165.0, 230.0)),
    (990011, '장기원 기념관', 'white', 4, block_poly(_jk, (_lib_u[1], -_lib_u[0]), 10.0, 7.0, round_end=True)),
    (990012, '', 'white', 2, Point(*(_jk + np.array([_lib_u[1], -_lib_u[0]]) * -14.0 - _lib_u * 12.0)).buffer(7.0, 3)),
    (990013, '청경관', 'white', 2, block_poly((20.0, 266.0), (0.557, 0.830), 8.0, 4.5)),
]
for pid, nm, style, lv, poly in OLD_HALLS:
    poly = shapely.geometry.polygon.orient(poly.simplify(0.05), 1.0)
    campus_polys.append(poly)
    hs = [ground_h(x, y) for x, y in poly.exterior.coords]
    buildings.append(dict(id=pid, name=nm, style=style, levels=lv, height=round(lv * FLOOR_H[style], 2),
                          base=round(min(hs), 2), top_ground=round(max(hs), 2),
                          footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]]))

campus_zone = unary_union([p.buffer(60) for p in campus_polys]).buffer(-20)

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


def draw_line(layer, coords, width):
    pp = [to_px(x, y) for x, y in coords]
    wpx = max(1, int(width / SPLAT['res']))
    dr[layer].line(pp, fill=255, width=wpx, joint='curve')
    r = wpx / 2
    for x, y in pp:
        dr[layer].ellipse([x - r, y - r, x + r, y + r], fill=255)


def draw_poly(layer, poly, val=255):
    if poly.is_empty:
        return
    geoms = poly.geoms if hasattr(poly, 'geoms') else [poly]
    for g in geoms:
        if g.geom_type != 'Polygon':
            continue
        dr[layer].polygon([to_px(x, y) for x, y in g.exterior.coords], fill=val)
        for hole in g.interiors:
            dr[layer].polygon([to_px(x, y) for x, y in hole.coords], fill=0)

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
# 정문 안쪽 왼편 화단섬 (1997 photo): hedge-bordered flower bed with azaleas, a pine, a stone marker and a sign.
# Back-projected from the photo with its fitted camera: the island lies between the side road and the front of
# 제1공학관's south end, its southern hedge ~85 m in from the gate; the side road leaves 백양로 at the speed bump and runs
# west-north-west past the island to the road along the south of the engineering halls.  South of it, lawn and trees.
ISL = Polygon([(-105.9, -337.3), (-112.5, -334.2), (-119.4, -328.8), (-128.2, -322.5), (-128.0, -310.0),
               (-119.0, -303.5), (-100.0, -306.0)]).difference(bline.buffer(ROAD_HALF + 0.6))
if isinstance(ISL, MultiPolygon):
    ISL = max(ISL.geoms, key=lambda g: g.area)
ISL_ROAD = [(-103.5, -345.5), (-113, -344.5), (-120, -341.5), (-126, -337), (-134, -331), (-148, -327)]
ISL_SOUTH = LineString([(-105.9, -337.3), (-119.4, -328.8), (-128.2, -322.5)])      # the hedge with the azaleas
# The side road joins 백양로 without a kerb (1997 photo, ground points back-projected with its camera): the west
# sidewalk, boxwood verge and planting strip stop about 86 m in from the gate at the island's south-east corner, and
# from there to the bottom of the photo (s ~ 65 m) the west side is one sheet of asphalt flush with the carriageway,
# opening into a ~20 m wide apron between the island's hedge and the lawn hedge to the south (yellow edge line of
# 백양로 painted straight on through).  MOUTH: side (+1 = west), s0, s1, corner radii at the south / north ends.
MOUTH = (1, 66.0, 86.5, 3.0, 2.0)
_ms, _m0, _m1 = MOUTH[0], MOUTH[1], MOUTH[2]
GATE_APRON = Polygon([along_raw(_m1, ROAD_HALF + 0.5)[:2], (-105.9, -337.3), (-112.5, -334.2), (-119.4, -328.8),
                      (-128.2, -322.5), (-146, -320), (-148, -334), (-127, -348), (-123.1, -350.9), (-117.0, -354.3),
                      along_raw(_m0, ROAD_HALF + 0.5)[:2]])
assert GATE_APRON.is_valid
# lane paint on the apron (photo): a solid yellow line from the mouth north-west past the island, and two dashed
# yellow lines 4.3 m and 7.6 m south of it (back-projected dashes); clipped to the apron, kept off 백양로 itself
_ad = np.array([0.758, -0.652])                       # along the apron lines, towards 백양로
_an = np.array([0.652, 0.758])                        # their normal (north-east)
_a0 = np.array([-114.6, -342.5])                      # a point of the solid line
APRON_LINES = []
for _off, _kind in ((0.0, 'yellow'), (-4.3, 'yellow_dash'), (-7.6, 'yellow_dash')):
    _ln = LineString([tuple(_a0 + _an * _off - _ad * 40), tuple(_a0 + _an * _off + _ad * 12)])
    _ln = _ln.intersection(GATE_APRON.buffer(-1.2)).difference(bline.buffer(ROAD_HALF + 0.6))
    for _g in (_ln.geoms if hasattr(_ln, 'geoms') else [_ln]):
        if _g.geom_type == 'LineString' and _g.length > 2:
            APRON_LINES.append((_kind, list(_g.coords)))
# east of 백양로 between the gate and 백주년기념관: in 1997 a lawn with scattered trees and a shaded car park
# (the curving promenade paths in OSM belong to the 2015 백양로 garden)
EAST_LAWN = Polygon([(-86, -404), (-18, -404), (-18, -266), (-50, -258)]).difference(bline.buffer(ROAD_HALF + 1))
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
    if ls.intersects(ISL.buffer(-0.5)) and hw not in ('footway', 'path', 'steps', 'pedestrian'):
        continue
    if hw in ('footway', 'path', 'steps', 'pedestrian'):
        if EAST_LAWN.contains(ls.centroid):
            continue
        # (and none across 활천대's basin: OSM's walks there lead down to the 2015 백양누리 entrance)
        ls = ls.difference(bcorr).difference(ISL.buffer(1.0)).difference(Point(*FOUNTAIN['pos']).buffer(FOUNTAIN['r'] + 1.5))
        if ls.is_empty:
            continue
        lsl = ls.geoms if hasattr(ls, 'geoms') else [ls]
        for l in lsl:
            if l.length < 3:
                continue
            draw_line('pavers', l.coords, WID[hw])
            paths_out.append(dict(kind=hw, w=WID[hw], pts=[[round(x, 1), round(y, 1)] for x, y in l.coords]))
    else:
        draw_line('asphalt', g, WID[hw])
        paths_out.append(dict(kind=hw, w=WID[hw], pts=[[round(x, 1), round(y, 1)] for x, y in g]))

# 1997 roads branching at the 삼거리 + 정문 forecourt
extra_roads = [
    [(38, 168), (20, 175), (-2, 178), (-43, 186), (-74, 194)],                 # west fork
    [(38, 168), (62, 160), (85, 150), (110, 140)],                            # east fork toward 노천극장
    [GATE, (-150, -432), (-250, -428)], [GATE, (0, -440), (120, -440)],
    ISL_ROAD,
]
draw_poly('asphalt', GATE_APRON.difference(bline.buffer(ROAD_HALF)))
for r in extra_roads:
    draw_line('asphalt', r, 7 if r is ISL_ROAD else 8)
    paths_out.append(dict(kind='service', w=7 if r is ISL_ROAD else 8, pts=[list(p) for p in r]))
# the mouth itself is road geometry (blender/road.py), asphalt under it too
MOUTH_POLY = Polygon([along_raw(s, _ms * E_CURB)[:2] for s in np.arange(_m0 - MOUTH[3], _m1 + MOUTH[4] + 0.1, 1.0)] +
                     [along_raw(s, _ms * (ROAD_HALF + 1.0))[:2] for s in np.arange(_m1, _m0 - 0.1, -1.0)])
draw_poly('asphalt', MOUTH_POLY)

# shaded car park on the lawn south-west of 백주년기념관 (red car under the trees in the 1997 photo)
LOT_E = [along_raw(s, -(ROAD_HALF + 8.5)) for s in np.arange(150, 196, 3.2)]
# 1997 photo: no car park beside the road here; the cars stand in a row on the dry lawn in front of 백주년기념관
LOT_C = [(x, -301.0 + (x + 58) * 0.06, 0.0) for x in np.arange(-58, -24, 4.6)]     # its cars back-projected
draw_line('dirt', [(x, y) for x, y, _ in LOT_C], 7.0)          # (on the trodden dry lawn, no paving)
# 백양로 itself is real geometry (Blender) – paint asphalt below so seams never show grass
draw_line('asphalt', bys, 2 * E_CURB)
draw_line('pavers', bys, 2 * ROAD_HALF)


# 대강당: its forecourt is paved from the porch out to the drive (the 2009 photos: cars park in front of the porch)
_af0, _af1 = np.array([51.13, 28.26]), np.array([59.82, 61.16])
_av = (_af1 - _af0) / np.linalg.norm(_af1 - _af0)
_aw = np.array([-_av[1], _av[0]])                                   # out of the front (west)
AUD_FORECOURT = Polygon([tuple(_af0 - _av * 14), tuple(_af1 + _av * 14), tuple(_af1 + _av * 14 + _aw * 12.5),
                         tuple(_af0 - _av * 14 + _aw * 12.5)])
draw_poly('asphalt', AUD_FORECOURT)
# building aprons (paved strips around campus buildings), library forecourt, 정문 plaza
aprons = unary_union([bp.buffer(3.5) for bp, b in zip(bpolys, buildings) if b['style'] != 'city'])
draw_poly('pavers', aprons)
plazas = [
    Polygon([(-85, -72), (-66, 4), (-12, -8), (-30, -88)]),                     # 중앙도서관 앞 광장
    Polygon([(18, -60), (4, -112), (-14, -105), (2, -52)]),                     # 학생회관 앞
    Point(GATE[0], GATE[1] + 10).buffer(22),                                  # 정문
    Polygon([(40, 150), (100, 140), (110, 185), (55, 195)]).buffer(2),          # 노천극장 진입
]
# 백주년기념관's museum forecourt and the foot of 과학관's flight (the 1996 album photos: paved)
_pa, _pb = np.array(CENT_NE[0]), np.array(CENT_NE[1])
_pn = np.array([(_pb - _pa)[1], -(_pb - _pa)[0]]) / np.linalg.norm(_pb - _pa)
plazas.append(Polygon([tuple(_pa + (_pb - _pa) * 0.25), tuple(_pa + (_pb - _pa) * 0.95), tuple(_pa + (_pb - _pa) * 0.95 + _pn * 17.0),
                       tuple(_pa + (_pb - _pa) * 0.25 + _pn * 17.0)]))
plazas.append(Polygon([tuple(SCI_DOOR - SCI_T * 9.0), tuple(SCI_DOOR + SCI_T * 9.0), tuple(SCI_DOOR + SCI_T * 11.0 + SCI_N * 17.0),
                       tuple(SCI_DOOR - SCI_T * 11.0 + SCI_N * 17.0)]))
# (the plaza before 언더우드관 정원: the steps and the banks now, UW_STEPS)
UW_BANKS = Polygon([wu_xy(-31.0, -43.4), wu_xy(31.0, -43.4), wu_xy(31.0, -26.0), wu_xy(-31.0, -26.0)])
plazas[3] = plazas[3].difference(UW_BANKS)
for pz in plazas:
    draw_poly('pavers', pz)

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
    (ax, ay), (bx, by) = fp_[3], fp_[4]
    return frame(ax, ay, bx - ax, by - ay)


def fpoly(W, pts):
    return Polygon([W(u, v) for u, v in pts])


# 언더우드관 앞 정원: a formal parterre.  The axis runs from the Underwood statue to the hall's door; four lawn beds
# edged with clipped boxwood carry clipped pines and topiary; a cross walk halfway.
WU = frame(62.0, 213.0, 0.970, -0.243)
garden = Polygon([(30, 190), (80, 177), (95, 236), (44, 250)])
draw_poly('pavers', garden.buffer(1.5))
draw_poly('pavers', garden.buffer(-3), 0)
draw_line('pavers', [WU(0, -30), WU(0, 31)], 5.5)
draw_line('dirt', [WU(-25, 2), WU(25, 2)], 3.0)
# the steps up from the 삼거리 (UW_STEPS): the axis walk on to the head of the upper flight, a walk along the top of the
# banks, the road's asphalt up to the foot of the lower flights
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
daewoo_garden = Point(*SANG).buffer(17).union(Polygon(SANG_DIAMOND).buffer(3.0))
draw_poly('pavers', Point(*SANG).buffer(7.2))
draw_line('pavers', [WD(23.5, 0), SANG], 6.0)
draw_line('pavers', [SG(0.0, -6.5), SANG_DIAMOND[2], (101.2, 405.4)], 6.0)        # the broad walk to the south steps
draw_poly('pavers', Point(*SANG).buffer(SANG_LAWN + 0.1), 0)    # (the lawn inside the curb: after the walks, not under them)
# 대우관 뒤: the car park and the drive asphalt, paving round the planter in the recess (DAEWOO_BACK above)
for _k in ('lot',):
    draw_poly('asphalt', fpoly(WD, DAEWOO_BACK[_k]))
draw_poly('pavers', fpoly(WD, [(-0.6, 14.8), (46.0, 14.8), (46.0, 24.6), (-0.6, 24.6)]))
draw_poly('pavers', court_poly(1.0))
draw_poly('pavers', Point(*FOUNTAIN['pos']).buffer(FOUNTAIN['r'] + 1.1))         # a narrow paved ring, lawn beyond
GARDEN_ZONES = [garden, yeonhui_garden, daewoo_garden, court_poly(2.0), Point(*FOUNTAIN['pos']).buffer(FOUNTAIN['r'] + 7)]

# amphitheater arena (dirt), sports field (dirt), tree-root patches done in web shader
draw_poly('dirt', Point(AMPH['cx'], AMPH['cy']).buffer(1).simplify(0))
c, s = math.cos(AMPH['rot']), math.sin(AMPH['rot'])
ell = [(AMPH['cx'] + (AMPH['arena_rx'] + 1) * math.cos(a) * c - (AMPH['arena_ry'] + 1) * math.sin(a) * s,
        AMPH['cy'] + (AMPH['arena_rx'] + 1) * math.cos(a) * s + (AMPH['arena_ry'] + 1) * math.sin(a) * c)
       for a in np.linspace(0, 2 * math.pi, 48)]
draw_poly('dirt', Polygon(ell))
for wv in ways.values():
    t = wv.get('tags', {})
    if t.get('leisure') in ('pitch', 'track') and len(wv['geometry']) > 3:
        pg = Polygon([xy(p) for p in wv['geometry']]).buffer(0)
        if pg.area > 1500:
            draw_poly('dirt', pg, 230)

# the old amphitheater: no paths across the bowl
bowl = Polygon([(AMPH['cx'] + (AMPH['arena_rx'] + AMPH['rows'] * AMPH['row_d'] + 1) * math.cos(a) * math.cos(AMPH['rot']) - (AMPH['arena_ry'] + AMPH['rows'] * AMPH['row_d'] + 1) * math.sin(a) * math.sin(AMPH['rot']),
                  AMPH['cy'] + (AMPH['arena_rx'] + AMPH['rows'] * AMPH['row_d'] + 1) * math.cos(a) * math.sin(AMPH['rot']) + (AMPH['arena_ry'] + AMPH['rows'] * AMPH['row_d'] + 1) * math.sin(a) * math.cos(AMPH['rot'])) for a in np.linspace(0, 2 * math.pi, 64)])
draw_poly('asphalt', bowl, 0)
draw_poly('pavers', bowl, 0)
draw_poly('dirt', bowl, 0)
draw_poly('dirt', Polygon(ell))
spl = np.stack([np.array(layers['asphalt']), np.array(layers['pavers']), np.array(layers['dirt'])], -1).astype(np.float32)
# priority: asphalt > pavers > dirt
spl[..., 1] = np.minimum(spl[..., 1], 255 - spl[..., 0])
spl[..., 2] = np.minimum(spl[..., 2], 255 - spl[..., 0] - spl[..., 1])
for ch in range(3):
    spl[..., ch] = ndimage.gaussian_filter(spl[..., ch], 0.7)
os.makedirs(os.path.join(ROOT, 'web/public/assets/textures'), exist_ok=True)
Image.fromarray(np.clip(spl, 0, 255).astype(np.uint8), 'RGB').save(
    os.path.join(ROOT, 'web/public/assets/textures/ground_splat.png'), optimize=True)
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
Image.fromarray(np.clip(_dry, 0, 255).astype(np.uint8), 'L').save(
    os.path.join(ROOT, 'web/public/assets/textures/ground_dry.png'), optimize=True)

# ---------------------------------------------------------------------------
# Vegetation
# ---------------------------------------------------------------------------
trees = []        # [species, x, y, scale, rot]
shrubs = []       # [kind, x, y, scale, rot]
asph = np.array(layers['asphalt']) > 40
pav = np.array(layers['pavers']) > 40


def blocked(x, y, pad=4.0):
    px, py = to_px(x, y)
    if not (0 <= px < SW and 0 <= py < SH):
        return False
    r = int(pad / SPLAT['res'])
    x0, x1, y0, y1 = int(px) - r, int(px) + r, int(py) - r, int(py) + r
    x0, y0 = max(0, x0), max(0, y0)
    return bool(asph[y0:y1, x0:x1].any() or pav[y0:y1, x0:x1].any())

ball_buf = ball.buffer(5)
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
        edge = bline.offset_curve(side * (E_CURB + 0.5))
        cut = ls_.intersection(edge)
        for g in (cut.geoms if hasattr(cut, 'geoms') else [cut]):
            if g.is_empty or g.geom_type != 'Point':
                continue
            s_ = float(bline.project(g))
            if 6 < s_ < L - 6:
                GAPS.append((round(s_, 1), side, round(pth['w'] / 2 + 1.5, 1)))


def in_gap(s, side, pad=0.0, outer=False):
    if any(abs(s - c) < 3.0 + pad for c in CROSS):
        return True
    r0, r1 = (0.0, 0.0) if outer else MOUTH[3:5]       # (out on the planting strip the corners are not rounded)
    if side == MOUTH[0] and MOUTH[1] - r0 - pad < s < MOUTH[2] + r1 + pad:
        return True                 # the side-road mouth: no verge, sidewalk or planting strip
    return any(sd == side and abs(s - g) < hw + pad for g, sd, hw in GAPS)


def in_gap_old(s, side, pad=0.0):
    # the gaps before the side-road mouth (a 10 m opening in the verge only); used to keep the random draws
    if any(abs(s - c) < 3.0 + pad for c in CROSS):
        return True
    return any(sd == side and abs(s - g) < hw + pad for g, sd, hw in GAPS + [(82.3, 1, 5.0)])


# 백양로 ginkgo rows (은행나무 가로수) in the outer planting strip with a clipped hedge, and the boxwood verges
for side in (-1, 1):
    s = 22.0
    while s < L - 30:
        x, y, _ = along_raw(s, side * (E_WALK + ROAD['strip'] * 0.5))
        # (1997 photo: on the west side the row only starts past the 화단섬; by the island, its hedge and young trees)
        if not in_gap(s, side, 1.0) and not ball.buffer(2).contains(Point(x, y)) and not (side > 0 and s < 122):
            trees.append(['ginkgo', round(x, 2), round(y, 2), round(rng.uniform(0.85, 1.0), 2), round(rng.uniform(0, 6.28), 2)])
        s += 8.5
    # (the random draws follow the gaps as they were before the mouth was opened, so the rest of the campus keeps
    # its random layout)
    s = 18.0
    while s < L - 24:
        if not in_gap_old(s, side, 0.6):
            x, y, a = along_raw(s, side * (E_WALK + ROAD['strip'] * 0.5))
            if not ball.buffer(1).contains(Point(x, y)):
                sc_ = round(rng.uniform(0.95, 1.05), 2)
                if not in_gap(s, side, 0.6, outer=True):
                    shrubs.append(['hedge_low', round(x, 2), round(y, 2), sc_, round(a, 3)])
        s += 1.5
    s = 14.0
    while s < L - 20:
        if not in_gap_old(s, side, 0.8):
            x, y, _ = along_raw(s, side * (E_CURB + ROAD['verge'] * 0.5))
            sc_ = round(rng.uniform(0.95, 1.1), 2)
            if not in_gap(s, side, 0.8):
                shrubs.append(['topiary_round', round(x, 2), round(y, 2), sc_, 0])
        s += 2.6
N_ROWS = len(trees)

# 정문 화단섬: hedge border, red azaleas massed along the south and east edges, pine + maple + zelkova
ring = ISL.buffer(-0.8).exterior
for d_ in np.arange(0, ring.length, 1.5):
    p = ring.interpolate(d_)
    q = ring.interpolate(min(ring.length, d_ + 0.5))
    shrubs.append(['hedge_low', round(p.x, 2), round(p.y, 2), 1.0, round(math.atan2(q.y - p.y, q.x - p.x), 3)])
# azaleas massed in two rows just inside the hedge along the south and the 백양로 (east) edges
for off in (0.0, 1.15):
    rr = ISL.buffer(-1.9 - off).exterior
    d_ = 0.0
    while d_ < rr.length:
        p = rr.interpolate(d_)
        if ISL_SOUTH.distance(p) < 3.5 or bline.distance(p) < ROAD_HALF + 4.5:
            shrubs.append(['azalea_red', round(p.x + rng.uniform(-.15, .15), 2), round(p.y + rng.uniform(-.15, .15), 2),
                           round(rng.uniform(0.85, 1.05), 2), round(rng.uniform(0, 6.28), 2)])
        d_ += 1.25
# trees of the island and around it, at their trunks as back-projected from the 1997 photo.  Scales from the photo
# too: the crown top's pixel row above the trunk, through the photo's camera, gives the height (the island pine
# ~6 m, not 15)
for sp, x, y, sc in (('pine', -114.4, -314.0, 0.55), ('zelkova', -106.2, -318.2, 0.75), ('zelkova', -108.0, -312.0, 0.9),
                     ('maple', -123.1, -319.9, 0.8), ('cherry', -120.9, -321.4, 0.7)):
    trees.append([sp, x, y, sc, round(rng.uniform(0, 6.28), 2)])

# east lawn between the gate and 백주년기념관: a denser 1997 planting (zelkova, pine, cherry, maple)
lot_line = LineString([(x, y) for x, y, _ in LOT_E]).buffer(4.5)
east_pts = []
for k in range(6000):
    x, y = rng.uniform(-90, -18), rng.uniform(-404, -258)
    pt = Point(x, y)
    if not EAST_LAWN.buffer(-2).contains(pt) or ball_buf.contains(pt) or lot_line.contains(pt) or blocked(x, y, 2.5):
        continue
    if any((x - u) ** 2 + (y - v) ** 2 < 8.0 ** 2 for u, v in east_pts):
        continue
    east_pts.append((x, y))
    trees.append([rng.choice(['zelkova', 'zelkova', 'pine', 'pine', 'cherry', 'maple']), round(x, 2), round(y, 2),
                  round(rng.uniform(0.85, 1.2), 2), round(rng.uniform(0, 6.28), 2)])

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
# trees read off the 1997 photo (trunks back-projected onto the ground with its fitted camera): the red maple and the
# big zelkova between the island and 제1공학관's canopy; in front, south of the side road, a young ginkgo and a round
# cherry; on the east lawn the two big zelkovas shading the car row, the young trees and the propped zelkova beyond it,
# the dark round pine by the sidewalk and the small pines at the foot of 백주년기념관.  Heights measured in the photo
# (crown top above the trunk through its camera): the two big zelkovas are ~9 m (not 16-17), the round pine ~5 m,
# the conifer at the foot of the hall ~3.5 m -- young trees in 1997, so the hall's dark porch shows above them
for sp, x, y, sc in (('maple', -118.5, -301.0, 0.85), ('zelkova', -110.5, -291.0, 0.66),
                     ('ginkgo', -114.5, -362.0, 0.85), ('cherry', -124.0, -356.0, 0.6),
                     ('zelkova', -59.5, -292.5, 0.72), ('zelkova', -50.5, -293.0, 0.71), ('cherry', -54.3, -311.3, 0.65),
                     ('zelkova', -47.1, -311.8, 0.71), ('zelkova', -39.0, -310.1, 0.85), ('pine', -78.5, -351.9, 0.45),
                     ('pine', -27.6, -278.1, 0.68), ('pine', -33.1, -277.1, 0.32)):
    trees.append([sp, x, y, sc, round(rng2.uniform(0, 6.28), 2)])
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

zone_campus = campus_zone.buffer(30)
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
    if not ok or ball_buf.contains(pt) or blocked(x, y, 3.5 if in_wood else 4.5) or bcorr.contains(pt):
        continue
    if amph_poly is not None and Point(AMPH['cx'], AMPH['cy']).distance(pt) < R_OUT + 1:
        continue
    if any(z.contains(pt) for z in GARDEN_ZONES) or ISL.buffer(3).contains(pt) or EAST_LAWN.contains(pt) or lot_line.contains(pt) \
            or FRONT_LAWN.contains(pt):
        continue
    sp = rng.choice(['pine', 'pine', 'oak', 'oak', 'zelkova']) if in_wood else rng.choice(species_campus)
    trees.append([sp, round(x, 2), round(y, 2), round(rng.uniform(0.8, 1.25), 2), round(rng.uniform(0, 6.28), 2)])
    grid_cells.setdefault(key, []).append((x, y))
# ring of pines around the old amphitheater (as in the April 1997 photo)
for a in np.linspace(0, 2 * math.pi, 26, endpoint=False):
    if abs(((a - math.pi - AMPH["rot"]) + math.pi) % (2 * math.pi) - math.pi) < 0.8:
        continue        # keep the stage side open
    rr = R_OUT + rng.uniform(3, 8)
    x, y = AMPH['cx'] + rr * math.cos(a), AMPH['cy'] + rr * math.sin(a)
    if not ball_buf.contains(Point(x, y)):
        trees.append(['pine', round(x, 2), round(y, 2), round(rng.uniform(1.0, 1.3), 2), round(rng.uniform(0, 6.28), 2)])

# 1997's lawn trees were young.  Measured in the 1997 aerial photo (crown tops above the trunks through its fitted
# camera) the scattered zelkovas, pines and cherries between the gate and 중앙도서관 stand at about 2/3 of the
# generic model heights (zelkova ~9 m, not 13-16); the ginkgo rows already match.  Scale the scattered trees there
# (not the rows or the hand-placed photo trees), easing back to full size past the library where the photo shows
# nothing, and keep the east lawn's below 8 m so 백주년기념관's dark porch shows over them as in the photo.
SPECIES_H = {'ginkgo': 9.8, 'zelkova': 13.0, 'cherry': 7.5, 'maple': 6.5, 'oak': 12.5, 'pine': 11.0,
             'zelkova_young': 9.0, 'cherry_young': 5.4, 'metasequoia': 13.5, 'magnolia': 8.0, 'poplar': 17.0}   # blender/vegetation.py
YOUNG = 0.65
n_young = 0
for i, t_ in enumerate(trees):
    if i < N_ROWS + 5 or N_EAST[1] <= i < N_PHOTO_TREES:
        continue                            # ginkgo rows, island trees, the photo's own trees
    pt = Point(t_[1], t_[2])
    if bline.distance(pt) > 120:
        continue
    f = float(np.interp(bline.project(pt), [0, 380, 480], [YOUNG, YOUNG, 1.0]))
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
    if bline.distance(Point(t_[1], t_[2])) > 120 or bline.project(Point(t_[1], t_[2])) > 430:
        continue
    young_sp = t_[0] + '_young'
    t_[3] = round(t_[3] * SPECIES_H[t_[0]] / SPECIES_H[young_sp], 2)
    t_[0] = young_sp
    n_vase += 1
print('young crowns:', n_vase)
# 메타세쿼이아 (issue #10): tall narrow conifers in the photo's bottom right corner, east of 백양로 just inside the gate.
# Their trunks are below the frame; the columns of the two crowns (photo x 1930 and 2080, tops at y 1000 and 1030)
# through the fitted camera, on the lawn behind the ginkgo row (clear of its trees), give these spots and heights
METASEQ = [(52.0, 14.7, 9.4), (57.0, 19.9, 8.0)]       # s, offset east, height
_mq = []
for _s, _o, _h in METASEQ:
    _x, _y, _ = along_raw(_s, -_o)
    _mq.append((_x, _y))
    trees.append(['metasequoia', round(_x, 2), round(_y, 2), round(_h / SPECIES_H['metasequoia'], 2), round(rng2.uniform(0, 6.28), 2)])
trees[N_ROWS:] = [t_ for t_ in trees[N_ROWS:] if t_[0] == 'metasequoia' or min(math.hypot(t_[1] - x_, t_[2] - y_) for x_, y_ in _mq) > 5.0]
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


def plant(kind, W, u, v, sc, rot=0.0):
    x, y = W(u, v)
    (trees if kind in ('pine', 'zelkova', 'ginkgo', 'cherry', 'maple', 'oak', 'magnolia', 'poplar') else shrubs).append(
        [kind, round(x, 2), round(y, 2), round(sc, 2), round(rot, 3)])


def axis_angle(W):
    (x0, y0), (x1, y1) = W(0, 0), W(0, 1)
    return math.atan2(y1 - y0, x1 - x0)


# 언더우드관 앞 정원
for su in (-1, 1):
    for (v0, v1) in ((-23.0, -0.5), (4.5, 25.0)):
        u0, u1 = sorted((su * 4.5, su * 22.5))
        hedge_rect(WU, u0, u1, v0, v1)
        uc, vc = (u0 + u1) / 2, (v0 + v1) / 2
        plant('pine', WU, uc, vc, 0.55, rng.uniform(0, 6.28))                      # the clipped pine in each bed
        for du in (-5.5, 5.5):
            for dv in (-6.5, 6.5):
                plant('topiary_round', WU, uc + du, vc + dv, 1.25)
        for (cu, cv) in ((u0 + 1.4, v0 + 1.4), (u1 - 1.4, v0 + 1.4), (u0 + 1.4, v1 - 1.4), (u1 - 1.4, v1 - 1.4)):
            plant('topiary_cone', WU, cu, cv, 1.1)
# tall trees standing round the parterre's edge; at its north-west corner, by the road before 언더우드관, a clipped pine
# instead (reference/2003_봄_언더우드관_앞길_벚나무.jpg: clipped pines and benches all along that side of the road)
for (u, v) in ((-27, -20), (-28, 8), (-27, 26), (27, -22), (28, 6), (27, 27)):
    if (u, v) == (-27, 26):
        plant('pine', WU, u, v, 0.45, rng.uniform(0, 6.28))
        continue
    plant('zelkova', WU, u, v, 1.15, rng.uniform(0, 6.28))
# 연희관 앞 정원 (YEONHUI): each of the four beds edged with clipped boxwood, a clipped pine in its middle and round
# boxwood towards its corners; the two by the south walk behind tall clipped hedges that end square at the forecourt
# (reference/연희관_정면_2023.jpg), the two under the bank low ones (대우관_블로그_연희관과_대우관_원경.jpg); the big
# clipped yew in the round planter; small round-headed shrubs along the top of the banks by the road and a low hedge
# along their foot; zelkovas on the lawns down to 한경길, ginkgos and round pines in the court before 연희관
rng7 = random.Random(1997 + 71)


def hedge_line(pts, kind='hedge_low', sc=1.0, step=1.5, closed=True):
    pts = list(pts) + ([pts[0]] if closed else [])
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        L_ = math.hypot(xb - xa, yb - ya)
        a_ = math.atan2(yb - ya, xb - xa)
        for k in range(max(1, int(L_ / step))):
            f_ = (k + 0.5) / max(1, int(L_ / step))
            shrubs.append([kind, round(xa + (xb - xa) * f_, 2), round(ya + (yb - ya) * f_, 2), sc, round(a_, 3)])


_yd = Polygon(YH_DIAMOND).buffer(-1.4, join_style='mitre')
_ywalks = unary_union([LineString([YH_G(0, -20), YH_G(0, 20)]).buffer(2.2), LineString([YH_DIAMOND[1], YH_DIAMOND[3]]).buffer(1.7),
                       Point(*YH_C).buffer(5.8)])
_beds = _yd.difference(_ywalks)
for bed in sorted(_beds.geoms if hasattr(_beds, 'geoms') else [_beds], key=lambda g: g.centroid.y):
    if bed.area < 20:
        continue
    bed = bed.simplify(0.3)
    south = g_en(bed.centroid.x, bed.centroid.y)[1] < 0
    hedge_line(list(bed.exterior.coords)[:-1], 'hedge_blob' if south else 'hedge_low', 1.3 if south else 1.0,
               step=1.6 if south else 1.5)
    inner = bed.buffer(-2.2).simplify(1.0)
    cx_, cy_ = bed.centroid.x, bed.centroid.y
    trees.append(['pine', round(cx_, 2), round(cy_, 2), round(rng7.uniform(0.36, 0.44), 2), round(rng7.uniform(0, 6.28), 2)])
    _done = [(cx_, cy_)]
    for (px_, py_) in ([] if inner.is_empty or inner.geom_type != 'Polygon' else list(inner.exterior.coords)[:-1]):
        if min(math.hypot(px_ - qx_, py_ - qy_) for qx_, qy_ in _done) > 3.2:
            _done.append((px_, py_))
            shrubs.append(['topiary_round', round(px_, 2), round(py_, 2), round(rng7.uniform(0.95, 1.2), 2), 0])
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
        shrubs.append(['topiary_round', round(float(q_[0]), 2), round(float(q_[1]), 2), 1.15, 0])
for (e_, n_, kind_, sc_) in ((-30, -12, 'zelkova', 1.0), (-19, -21, 'pine', 0.6), (-38, -2, 'zelkova', 0.9),
                             (24, -16, 'zelkova', 1.05), (14, -22, 'pine', 0.55), (33, -8, 'zelkova', 0.9)):
    x_, y_ = YH_G(e_, n_)
    trees.append([kind_, round(x_, 2), round(y_, 2), sc_, round(rng7.uniform(0, 6.28), 2)])
for (u, v, kind_, sc_) in ((-6.0, -11.5, 'ginkgo', 1.25), (46.5, -10.5, 'ginkgo', 1.25), (6.0, -5.5, 'pine', 0.34),
                           (12.5, -5.5, 'pine', 0.3), (27.5, -5.5, 'pine', 0.3), (34.0, -5.5, 'pine', 0.34)):
    plant(kind_, WY, u, v, sc_, rng7.uniform(0, 6.28))
# 대우관 상뜰 (see SANG above): the small round-crowned pine in the round lawn, a broadleaf tree in the west lawn
# triangle by the ring and one by the north-east path, low shrubs along the triangles' upper edges, and the big pines
# on the lawns outside the walks towards the terrace
ang_d = axis_angle(WD)
rng6 = random.Random(1997 + 61)
trees.append(['pine', SANG[0], SANG[1], 0.55, 0.4])
for (e_, n_, kind_, sc_) in ((-8.5, 4.5, 'zelkova', 0.75), (10.0, 8.6, 'zelkova', 0.8), (13.0, -2.5, 'pine', 0.45)):
    x_, y_ = SG(e_, n_)
    trees.append([kind_, round(x_, 2), round(y_, 2), sc_, round(rng6.uniform(0, 6.28), 2)])
# the planted bank under the diamond's lower walks, down to the footway, the south flight going down between its
# trees (issue #39; reference/대우관_정면_전경.jpg: spreading conifers east of the flight, broadleaves west of it)
for (e_, n_, kind_, sc_) in ((-7.5, -18.6, 'zelkova', 0.85), (-15.0, -15.5, 'maple', 0.75), (-23.0, -11.5, 'zelkova', 0.9),
                             (-30.5, -8.0, 'oak', 0.85), (-11.0, -20.5, 'cherry', 0.7), (7.5, -18.8, 'pine', 0.95),
                             (14.5, -16.0, 'pine', 0.8), (22.0, -12.0, 'zelkova', 0.85), (30.0, -8.5, 'pine', 0.85),
                             (11.5, -21.0, 'maple', 0.65)):
    x_, y_ = SG(e_, n_)
    trees.append([kind_, round(x_, 2), round(y_, 2), sc_, round(rng6.uniform(0, 6.28), 2)])
for sg in (-1, 1):
    for (e_, n_, sc_) in ((-19.5, 7.0, 0.95), (-12.0, 10.2, 0.85), (-25.5, 5.5, 0.8)):
        x_, y_ = SG(sg * e_, n_)
        trees.append(['pine', round(x_, 2), round(y_, 2), sc_, round(rng6.uniform(0, 6.28), 2)])
    for t_ in (0.3, 0.5, 0.72):                              # shrubs along the inside of the upper (NW / NE) walk
        e_, n_ = -0.8 + (-26.5 + 0.8) * t_, 14.2 * (1 - t_)
        x_, y_ = SG(-sg * (e_ + 0.9), n_ - 1.9)
        shrubs.append(['bush', round(x_, 2), round(y_, 2), round(rng6.uniform(0.8, 1.05), 2), round(rng6.uniform(0, 6.28), 2)])
# 대우관 뒤 (Street View 2009): pointed conifers 4-5 m tall in a row along the two planters (none before the tower);
# on the lawn mound west of the car park young clipped pines and round shrubs; a few trees between the rows of cars
rng4 = random.Random(1997 + 23)
_pl = DAEWOO_BACK['planter']
for k in range(12):
    u_ = _pl[0][0] + 1.6 + k * (_pl[1][0] - _pl[0][0] - 3.2) / 11
    if abs(u_ - 23.55) < 6.5:
        continue                                                  # the back tower stands out into the planter there
    x_, y_ = WD(u_, 20.4 + rng4.uniform(-0.4, 0.4))
    trees.append(['metasequoia', round(x_, 2), round(y_, 2), round(rng4.uniform(0.3, 0.36), 2), round(rng4.uniform(0, 6.28), 2)])
for (u_, v_, sc_) in ((-4.0, 31.0, 0.42), (3.0, 34.0, 0.38), (10.0, 32.0, 0.45), (17.0, 34.0, 0.4), (16.0, 44.0, 0.36),
                      (22.0, 40.0, 0.44), (21.0, 52.0, 0.4), (20.0, 62.0, 0.46), (23.0, 68.0, 0.4), (2.0, 30.5, 0.3)):
    plant('pine', WD, u_, v_, sc_, rng4.uniform(0, 6.28))
_diag = LineString([(-13.0, 29.0), (10.0, 62.0), (31.0, 83.0)])     # the drive to 북문 (OSM), in (u, v)
_n_sh = 0
while _n_sh < 10:
    u_, v_ = rng4.uniform(-8, 23), rng4.uniform(29, 72)
    if _diag.distance(Point(u_, v_)) > 4.5 and Point(u_, v_).y < 29 + (u_ + 13) * 1.43 \
            and LineString([(4, 39), (16, 55)]).distance(Point(u_, v_)) > 4 and LineString([(10, 62), (25, 55)]).distance(Point(u_, v_)) > 4:
        plant(rng4.choice(['topiary_round', 'bush']), WD, u_, v_, rng4.uniform(0.8, 1.2))
        _n_sh += 1
for (u_, v_) in ((68.5, 34.0), (66.5, 58.0)):                     # on the bank below the road to 북문
    plant('maple', WD, u_, v_, 0.7, rng4.uniform(0, 6.28))
# 활천대 (reference/활천대_2009_연세춘추.jpg): on the lawn round its narrow paved ring, low clipped shrubs and a few
# small clipped pines scattered a few metres out, and red azaleas towards the eagle
_fx, _fy = FOUNTAIN['pos']
for k, a_ in enumerate(np.radians([40, 105, 170, 235])):       # (none on the 2009 photo's side, south-east)
    rr_ = FOUNTAIN['r'] + 5.0 + (k % 2) * 1.6
    trees.append(['pine', round(_fx + rr_ * math.cos(a_), 2), round(_fy + rr_ * math.sin(a_), 2), round(rng2.uniform(0.2, 0.26), 2),
                  round(rng2.uniform(0, 6.28), 2)])
for k in range(14):
    a_ = 2 * math.pi * (k + 0.5) / 14 + rng2.uniform(-0.12, 0.12)
    rr_ = FOUNTAIN['r'] + 2.4 + rng2.uniform(0, 2.6)
    shrubs.append(['topiary_round', round(_fx + rr_ * math.cos(a_), 2), round(_fy + rr_ * math.sin(a_), 2),
                   round(rng2.uniform(0.6, 0.85), 2), 0])
for k in range(9):
    a_ = math.atan2(-82 - _fy, -52 - _fx) + (k - 4) * 0.09
    rr_ = FOUNTAIN['r'] + 9.5 + (k % 3) * 0.8
    shrubs.append(['azalea_red', round(_fx + rr_ * math.cos(a_), 2), round(_fy + rr_ * math.sin(a_), 2),
                   round(rng2.uniform(0.9, 1.1), 2), round(rng2.uniform(0, 6.28), 2)])
# --- the trees of the 2003 spring and autumn photos (reference/2003_*.jpg, taken by the user; reference/고증.md
# 3.18).  Where they show the old cherries in flower and the October ginkgos, plant them one by one (the trees
# scattered on those spots step aside):
#  - 2003_봄_백양로끝_핀슨관길_벚나무.jpg: a row of big old cherries along the south side of the road from the 삼거리
#    at the head of 백양로 towards 핀슨관, which bends north-west and climbs; benches under them facing the road, a
#    green bin, a pair of stone 해태
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
# (the camera stood at the 삼거리 at the head of 백양로, by the steps up to 언더우드관 정원, looking west along the road
# towards 핀슨관 as it bends north-west and climbs; the user placed it there)
_br = LineString([(38, 168), (20, 175), (-2, 178), (-43, 186)])  # the west fork from the 삼거리 (extra_roads, 8 m)
_brs, _brb = _br.offset_curve(6.0), _br.offset_curve(4.7)         # (its left: the south side)
_rows = [(t_[1], t_[2]) for t_ in trees[:N_ROWS]]
for k in range(8):
    q_ = _brs.interpolate(11.0 + 6.8 * k)                          # (past 백양로's sidewalk at its end)
    if min(math.hypot(q_.x - a_, q_.y - b_) for a_, b_ in _rows) < 4.0:
        continue                                                  # (not into 백양로's ginkgo rows)
    PHOTO03.append(('cherry', q_.x, q_.y, rng8.uniform(1.2, 1.4)))
    if k < 7:                                                     # a bench between this one and the next
        b_ = _brb.interpolate(14.4 + 6.8 * k)
        r_ = _br.interpolate(_br.project(b_))
        if k in (3, 4):
            # the pair of stone 해태 on low plinths at the road's edge, facing each other across the opening of a path
            # (in the photo between the green bin and the benches beyond)
            h_ = _br.offset_curve(5.0).interpolate(14.4 + 6.8 * k)
            t0_, t1_ = _br.interpolate(_br.project(h_) - 1.0), _br.interpolate(_br.project(h_) + 1.0)
            fwd_ = math.atan2(t1_.y - t0_.y, t1_.x - t0_.x)
            PHOTO03_PROPS.append(('haetae', h_.x, h_.y, fwd_ if k == 3 else fwd_ + math.pi))
            continue
        PHOTO03_PROPS.append(('trashcan' if k == 2 else 'bench', b_.x, b_.y, math.atan2(r_.y - b_.y, r_.x - b_.x)))
for (x_, y_) in ((99.5, 246.5), (101.5, 239.5), (103.0, 232.5), (104.0, 225.5), (104.5, 218.5)):
    PHOTO03.append(('cherry', x_, y_, rng8.uniform(1.1, 1.3)))
hedge_line([(95.0, 214.0), (93.6, 249.0)], closed=False)
for (u_, v_) in ((-22.0, -27.0), (-15.0, -28.5), (-8.0, -29.5), (8.0, -29.5), (15.0, -28.5), (22.0, -27.0)):
    x_, y_ = WU(u_, v_)
    PHOTO03.append(('cherry', x_, y_, rng8.uniform(1.15, 1.3)))
PHOTO03 += [('cherry', 49.5, 317.5, 1.3), ('cherry', 106.0, 321.0, 1.05),
            ('ginkgo', 119.5, 317.5, 1.0), ('maple', 120.5, 328.5, 0.9)]
x_, y_ = WY(16.5, -3.8)
PHOTO03.append(('ginkgo', x_, y_, 0.42))
#  - the white-stemmed 은백양 by the foot of the steps up to 언더우드관 정원, just east of them (bare in April), and
#    another behind the first cherries along the road west from the 삼거리, beyond the side road south of them
#    (the 2003 spring photos)
#  - 목련: in the north-west corner of 연희관 앞 정원 behind the double lamp (2003_봄_교육관에서_본_*), and before
#    언더우드관 east of its tower (2024_봄_언더우드관_목련.jpg: the old tree is taken to have stood there in 1997 too)
PHOTO03.append(('poplar', *WU(5.4, -43.4), 1.0))
PHOTO03.append(('poplar', 24.0, 155.5, 0.92))
PHOTO03 += [('magnolia', 58.0, 339.5, 1.0), ('magnolia', *WU(-3.0, 40.6), 1.05)]
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
# Its flight is as wide as the photos (16 m: fifteen risers down to the levelled car park, FORECOURTS), with the
# five-globe lamp at its head.  음악관 (기악과's photo): a deep canopy on two round white columns over four bays of
# aluminium-framed glass, white tile walls and tiled planters either side of three granite steps, blue window frames.
# 빌링슬리관: in the middle of its long south front, under a window group (the 1996 album photo of 의류환경학과:
# the arched door between equal piers, a group of three lights over it).  The 1994 campus map draws the arched door
# there, in the middle between the gabled end bays with a walk running south from it; and OSM's footway from the south
# ends there too, 22.6 m along the 45.1 m front (the door had gone to the short east end, the slope having buried this
# front: FORECOURTS).
ENTRY_AT = {222843398: ((-242.7, 13.8), dict(span=3, canopy=3.0, stair_w=16.0, lamp5=True, floor=2)),
            429077789: ((144.08, -11.73), dict(span=2, music=True)),
            245623193: ((35.93, 412.08), dict(floor=0))}
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
    hw_ = (3.4 if b['style'] in ('modern', 'gym') else 2.6) * b['entry'].get('span', 1)
    tx, ty = -ny, nx                                              # along the wall
    ENTRY_ZONES.append(Polygon([(px_ - tx * hw_, py_ - ty * hw_), (px_ + tx * hw_, py_ + ty * hw_),
                                (px_ + tx * hw_ + nx * 8.0, py_ + ty * hw_ + ny * 8.0),
                                (px_ - tx * hw_ + nx * 8.0, py_ - ty * hw_ + ny * 8.0)]))
    n_entry += 1
# 백주년기념관's museum flight and forecourt, 과학관's broad flight (wider than the door's own zone)
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
# and 교육관's outside flight along its north end
ENTRY_ZONES += [flight_zone((39.65, 327.89), (0.97, -0.25), 2.8, 9.0), flight_zone((117.18, 307.08), (-0.97, 0.24), 3.0, 9.0),
                flight_zone((33.7, 347.9), (0.25, 0.97), 7.0, 5.5)]
_ez = unary_union(ENTRY_ZONES + [tennis_poly(pd_, 2.5) for pd_ in TENNIS['pads']])     # (and off the tennis courts)
_nt = len(trees)
trees[N_ROWS:] = [t_ for t_ in trees[N_ROWS:] if not _ez.contains(Point(t_[1], t_[2]))]
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

# shrubs around building aprons
for b, bp in zip(buildings, bpolys):
    if b['style'] == 'city':
        continue
    ring = bp.buffer(5.5).exterior
    nshr = int(ring.length / 7)
    for k in range(nshr):
        p = ring.interpolate(rng.uniform(0, ring.length))
        if not blocked(p.x, p.y, 1.2) and not ball.contains(p) and not any(z.contains(p) for z in GARDEN_ZONES) and rng.random() < 0.55:
            sh_ = ['bush', round(p.x, 2), round(p.y, 2), round(rng.uniform(0.7, 1.3), 2), round(rng.uniform(0, 6.28), 2)]
            if not _ez.contains(p):              # (drawn all the same, so the rest of the campus keeps its random draws)
                shrubs.append(sh_)
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
# 백양로 street lamps: two-armed lamps with box heads at the inner edge of the east sidewalk (1997 aerial photo: they
# stand along the east sidewalk all the way up; along the west sidewalk, from the gate past the library, there is
# not one pole)
for s in np.arange(40, L - 20, 34):
    for side in (-1,):
        s_ = s
        while in_gap(s_, side, 1.0):
            s_ += 4.0
        x, y, a = along_raw(s_, side * (E_VERGE + 0.45))
        props.append(['lamp_arm', round(x, 2), round(y, 2), round(a + (math.pi if side < 0 else 0), 3)])
# (no white flags or poles along the west sidewalk.)  The white cloth past the gate, by the island's hedge about
# 92-106 m in from the gate (issue #12, back-projected with the photo's camera), is no row of flags: it is one long
# placard stretched between two trees inside the island's hedge, seen end-on through the trees so that it shows as
# three white patches.  The north end is tied to the island's young zelkova, the south end to a young tree by the
# hedge; the cloth hangs low, about 2.3 m up, its lettering towards the road.
_pt0 = along_raw(93.5, 12.8)[:2]                      # the south tree, just inside the hedge
trees.append(['zelkova_young', round(_pt0[0], 2), round(_pt0[1], 2), 0.9, 1.3])
BED_PLACARD = dict(s=(95.3, 106.4), off=(13.0, 14.5), tie=((93.5, 12.8), (108.1, 15.3)), top=2.35, depth=0.82,
                   text='’97 공과대학 학술제  —  공학인의 밤', sub='연세대학교 공과대학 학생회', color='white')
# banners (현수막) across the road, tied with ropes to the trees and lamp posts on either side (no poles of their
# own).  The first five are read off the 1997 photo: their distances along the road back-projected with its fitted
# camera, and their ends found where the rays of the cloth's corners meet the vertical plane across the road there:
# plain cloth strips about 0.8-0.9 m deep and 9-12 m long (a 10:1 to 14:1 strip; the 1997 표준 현수막 is 0.9 x 10 m),
# hung 5-6 m over the road, unevenly (one end often half a metre higher).  Per banner: s, spec, colour, and
# (west end offset, east end offset, west top, east top, depth) in m (offsets + west / - east, tops above the road).
BANNERS = [
    (51, dict(text='창립 7주년 기념 세미나 및 학부모 초빙 행사', sub='연세대학교 사회환경건축공학부 도시공학전공', marks=['경', '축']), 'white',
     (6.8, -4.9, 6.0, 5.6, 0.81)),
    (82, dict(text='기술고등고시 설명회', sub='분야: 기계, 전기, 화공, 환경, 토목, 건축, 전산, 통신기술'), 'white_yellow',
     (5.4, -3.7, 6.3, 5.4, 0.88)),
    (128, dict(text='설계공동연구소 10주년 기념식 및 초청강연회'), 'white', (5.3, -6.8, 6.0, 5.5, 0.9)),
    # 사진 속 먼 쪽 두 장(글자는 읽히지 않음)은 연고전 현수막이 걸리는 가을에는 겹치므로 뺀다
    (170, dict(text='’97 학술제 안내  —  학과별 발표회 및 초청강연', hide='autumn'), 'white', (4.8, -5.9, 6.0, 6.0, 0.81)),
    (241, dict(text='신입생 환영 학과 설명회  —  연세대학교 총학생회', hide='autumn'), 'white', (4.9, -4.7, 6.6, 6.6, 0.9)),
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
def s_off(x, y):
    """arc length along 백양로 and signed offset (+ west) of a point"""
    s_ = s_at(x, y)
    cx_, cy_, a_ = along_raw(s_, 0.0)
    return s_, (x - cx_) * -math.sin(a_) + (y - cy_) * math.cos(a_)


# what a banner rope can be tied to: the trees beside the road only (the ginkgo rows, and where the west row has not
# started yet, the island's and the lawn's trees).  In the 1997 photo every banner hangs from the trees: the lamp
# posts carry none.
ANCHORS = [(*s_off(t_[1], t_[2]), t_[1], t_[2]) for t_ in trees if bline.distance(Point(t_[1], t_[2])) < 30]
N_FLOATING_TIES = 0


def tie_for(s, off_end, top):
    """the nearest trunk outside the banner's end on its side of the road (further along the road if none is close)"""
    global N_FLOATING_TIES
    side = 1 if off_end > 0 else -1
    best = None
    for reach in (14.0, 24.0):
        for sa, oa, xa, ya in ANCHORS:
            if not (side * off_end + 0.3 < side * oa < 30.0) or abs(sa - s) > reach:
                continue
            d_ = math.hypot(sa - s, oa - off_end)
            if best is None or d_ < best[0]:
                best = (d_, xa, ya)
        if best is not None:
            break
    if best is None:
        N_FLOATING_TIES += 1
        xa, ya, _ = along_raw(s, side * (E_WALK + ROAD['strip'] * 0.5))
        best = (0.0, xa, ya)
    return [round(best[1], 2), round(best[2], 2), round(prof_h(s) + top + 0.35, 2)]


banners = []
for row in BANNERS:
    s, spec, col = row[:3]
    ow, oe, tw, te, dep = row[3] if len(row) > 3 else (5.0, -5.0, 5.9, 5.9, 0.9)
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
for (x, y, r) in [(-50, -25, -1.82), (-47, -14, -1.82), (-58, -60, -1.82),
                  (-20, 35, 1.3), (6, 60, -1.82), (110, 160, 1.3), (-36, -140, -1.82), (-46, -180, -1.82)]:
    P('bench', x, y, r)
# garden benches, long side along the walk, seat towards it (BENCH_FACE: which way the bench model looks)
BENCH_FACE = math.pi


def bench_along(W, u, v, face_u):
    (x, y) = W(u, v)
    a_ = axis_angle(W) - math.pi / 2 + (0 if face_u < 0 else math.pi) + BENCH_FACE
    P('bench', x, y, a_)


for v in (-17.0, -6.0, 10.0, 20.0):                 # 언더우드관: along the axis, both sides
    bench_along(WU, -3.6, v, 1)
    bench_along(WU, 3.6, v, -1)
# 연희관 앞 정원: along the two upper walks of the diamond at the foot of the banks, looking into the garden
for (a_, b_) in ((YH_DIAMOND[1], YH_DIAMOND[2]), (YH_DIAMOND[2], YH_DIAMOND[3])):
    a_, b_ = np.array(a_), np.array(b_)
    d_ = (b_ - a_) / np.linalg.norm(b_ - a_)
    o_ = np.array([-d_[1], d_[0]])
    for t_ in (0.3, 0.55):
        q_ = a_ + (b_ - a_) * (t_ if a_[0] < YH_C[0] else 1 - t_) + o_ * 0.95
        P('bench', float(q_[0]), float(q_[1]), math.atan2(-o_[1], -o_[0]))
# 대우관 상뜰: along the two lower (SW / SE) walks of the diamond, two benches on the lawn triangle inside facing the
# walk and two on the far side facing back (the photos; a bench model faces its rot angle, see bench_along)
for sg in (-1, 1):
    _w0, _w1 = np.array([sg * 26.5, 0.0]), np.array([0.0, -15.3])
    _d = (_w1 - _w0) / np.linalg.norm(_w1 - _w0)
    _in = np.array([-_d[1], _d[0]]) * (1 if sg < 0 else -1)          # into the triangle (towards the ring)
    for t_, side in ((0.5, 1), (0.78, 1), (0.25, -1), (0.65, -1)):
        e_, n_ = _w0 + (_w1 - _w0) * t_ + _in * 2.3 * side
        x_, y_ = SG(e_, n_)
        f_ = -_in * side                                                 # facing the walk
        fw_ = SG_E * f_[0] + SG_N * f_[1]
        P('bench', x_, y_, math.atan2(fw_[1], fw_[0]))
for (x, y) in [(-48, -40), (-4, -64), (45, 200), (-94, -404), (-44, -175)]:
    P('trashcan', x, y, 0)
# under the cherries by the drive up to 핀슨관 (2003 spring photo): benches facing the drive, a green bin among them;
# double-globe lamps at the north-west corner of 연희관 앞 정원 and by 교육관's north yard (the 2003 photos)
for (name_, x, y, r) in PHOTO03_PROPS:
    P(name_, x, y, r)
# 언더우드관 앞길 (2003_봄_언더우드관_앞길_벚나무.jpg, looking east from before the west wing): a row of yellow-and-black
# bollards across the road before the west wing and another at its east end, where it meets the slope towards
# 논지당 (no cars in front of the hall); before the west wing a green canvas tent (a stall) and, by the wing's side
# door, a notice board under a little green roof
_south = math.atan2(-_wuv[1], -_wuv[0])
for (u_, vs_) in ((-22.0, np.arange(29.9, 37.0, 1.4)), (15.2, np.arange(30.8, 36.4, 1.35))):
    for v_ in vs_:
        P('bollard', *WU(u_, float(v_)), 0.0)
P('tent_kiosk', *WU(-28.0, 40.4), _south)
P('notice_board', *WU(-17.5, 38.2), _south)
# 연희관 (2003_가을_연희관_정면.jpg, from the south-west): the green tent stall against the tower just west of its porch
_yd = min(np.arange(-10.0, 60.0, 0.25), key=lambda u_: abs(float((np.array(WY(u_, 0.0)) - GF_C) @ GF_E)))   # the axis
_ye = 1.0 if WY(_yd + 1.0, 0.0)[0] > WY(_yd, 0.0)[0] else -1.0
_yo = math.atan2(*(np.array(WY(_yd, -1.0)) - np.array(WY(_yd, 0.0)))[::-1])                              # out of the front
P('tent_kiosk', *WY(_yd - _ye * 5.4, -3.2), _yo)
# 언더우드관 정원 남쪽 계단: benches along the walk at the top of the banks, looking out over the steps
for sg in (-1, 1):
    for u_ in (6.5, 13.5):
        P('bench', *WU(sg * u_, -32.7), _south)
for (x, y) in [(52.6, 340.5), (46.0, 358.0)]:
    P('lamp_double', x, y, -0.25)
# double-globe lamps around the library forecourt (1997 library photo: in the clipped shrubs some way out from the
# piers, not on the steps) and at the tip of the 화단섬
for (x, y) in [(-64, -58), (-58, -22), (-68.5, -41.5), (-106.7, -315.3)]:
    P('lamp_double', x, y, -0.25)
# 화단섬: natural stone marker, campus guide sign, white round planters along the side road (all from the 1997 photo)
P('stone_marker', -112.9, -321.5, 0.4)
P('sign_board', -122.1, -320.4, -0.9)
for k in range(4):
    x, y = -129.5 + k * 4.1, -326.4 - k * 2.9
    P('planter', x, y, 0)
for (x, y) in ((-121.0, -347.5), (-120.8, -356.6)):
    P('planter', x, y, 0)

# parked & moving cars (1990s 승용차), engineering-side motorbikes
cars = []
# west of 백양로 between 제1공학관 and 중앙도서관 (cars along the side road in the 1997 photo)
LOT_W = [along_raw(s, ROAD_HALF + 9.0) for s in np.arange(255, 300, 3.0)]
lots = [((60, 100), (100, 92), 9), ((-130, 110), (-80, 130), 8), ((20, -150), (40, -180), 6)]
for (a, b_, n) in lots:
    for k in range(n):
        t_ = k / max(1, n - 1)
        x = a[0] + (b_[0] - a[0]) * t_
        y = a[1] + (b_[1] - a[1]) * t_
        ang = math.atan2(b_[1] - a[1], b_[0] - a[0]) + math.pi / 2
        if rng.random() < 0.85 and not ball.buffer(1.5).contains(Point(x, y)):
            cars.append([rng.choice(['sedan', 'sedan', 'hatch', 'taxi']), round(x, 2), round(y, 2), round(ang + rng.uniform(-.05, .05), 3), rng.randrange(8)])
for line in (LOT_W, LOT_E):
    for (x, y, a) in line:
        if rng.random() < 0.8 and not ball.buffer(1.5).contains(Point(x, y)):
            car = [rng.choice(['sedan', 'sedan', 'hatch', 'taxi']), round(x, 2), round(y, 2),
                   round(a + math.pi / 2 + rng.uniform(-.05, .05), 3), rng.randrange(8)]
            if line is not LOT_E:
                cars.append(car)
rng3 = random.Random(1997 + 11)
for (x, y, a) in LOT_C:          # a red sedan among them, as in the photo
    if rng3.random() < 0.85:
        cars.append([rng3.choice(['sedan', 'sedan', 'hatch', 'taxi']), round(x, 2), round(y, 2),
                     round(math.pi / 2 + rng3.uniform(-.06, .06), 3), rng3.randrange(8)])
# 대우관 뒤: the car park behind the hall (Street View 2009: three rows of cars, nearly full), nose in, along v
rng5 = random.Random(1997 + 29)
(_x0, _y0), (_x1, _y1) = WD(0, 0), WD(1, 0)
_hu = math.atan2(_y1 - _y0, _x1 - _x0)                            # heading along +u
for (u_, face) in DAEWOO_BACK['rows']:
    v_ = DAEWOO_BACK['row_v'][0]
    while v_ <= DAEWOO_BACK['row_v'][1] + 0.01:
        if not (DAEWOO_BACK['gap'][0] < v_ < DAEWOO_BACK['gap'][1]) and rng5.random() < 0.8:
            x_, y_ = WD(u_, v_)
            cars.append([rng5.choice(['sedan', 'sedan', 'sedan', 'hatch']), round(x_, 2), round(y_, 2),
                         round(_hu + (0.0 if face > 0 else math.pi) + rng5.uniform(-.04, .04), 3), rng5.randrange(8)])
        v_ += DAEWOO_BACK['stall']
# 교육관's north yard, full of cars in the 2003 autumn photo (2003_가을_연희관앞정원과_교육관_북쪽계단.jpg): a row nose in
# towards the hall, clear of the outside flight along its wall
_gt, _gn = np.array([-0.969, 0.248]), np.array([0.248, 0.969])     # along its north end (from the east corner), out of it
rng9 = random.Random(1997 + 2004)
for s_ in (1.8, 4.4, 7.0, 9.6, 12.2, 14.8):
    if rng9.random() < 0.9:
        q_ = np.array([44.15, 345.23]) + _gt * s_ + _gn * 8.2
        cars.append([rng9.choice(['sedan', 'sedan', 'sedan', 'hatch']), round(float(q_[0]), 2), round(float(q_[1]), 2),
                     round(math.atan2(-_gn[1], -_gn[0]) + rng9.uniform(-.04, .04), 3), rng9.randrange(8)])
# motorbikes in front of the south end of 제1공학관 (the 1997 photo: by its south-east corner, next to the island)
for k in range(16):
    t_ = k / 15
    x, y = -141 + 13 * t_ + rng.uniform(-.3, .3), -299.5 - 6.5 * t_
    P('motorbike', x, y, -0.85 + rng.uniform(-.2, .2))

# keep the carriageway clear: nothing static may stand on 백양로's driving lanes
def on_carriageway(x, y):
    return bline.distance(Point(x, y)) < E_CURB + 0.3 and bline.project(Point(x, y)) < L - 1
n0 = (len(props), len(cars), len(trees), len(shrubs))
props = [p for p in props if not on_carriageway(p[1], p[2])]
# (nor on the halls' front steps: benches, bins and phone boxes stood beside the doors, not in them)
props = [p for p in props if p[0] in ('lamp_arm', 'guard_booth') or not _ez.contains(Point(p[1], p[2]))]
cars = [c for c in cars if not on_carriageway(c[1], c[2]) and not _ez.contains(Point(c[1], c[2]))]
trees = [t for t in trees if not on_carriageway(t[1], t[2])]
shrubs = [t for t in shrubs if not on_carriageway(t[1], t[2])]
print('removed from carriageway (props, cars, trees, shrubs):',
      n0[0] - len(props), n0[1] - len(cars), n0[2] - len(trees), n0[3] - len(shrubs))
# ... nor on 언더우드관 정원's south steps (UW_STEPS); then the planting of their banks and beds (the 2003 spring photo):
# clipped round shrubs on the banks in two staggered rows, a border of pansies along their top, and in the raised beds
# either side of the upper flight a clipped shrub and pansies along the front
_uwz = Polygon([wu_xy(-4.6, -43.4), wu_xy(4.6, -43.4), wu_xy(4.6, -34.2), wu_xy(-4.6, -34.2)])
props = [p for p in props if not _uwz.contains(Point(p[1], p[2]))]
cars = [c for c in cars if not _uwz.contains(Point(c[1], c[2]))]
trees = [t for t in trees if not _uwz.contains(Point(t[1], t[2]))]
_uwb = Polygon([wu_xy(-31.0, -43.4), wu_xy(31.0, -43.4), wu_xy(31.0, -31.2), wu_xy(-31.0, -31.2)])     # (not the garden's own)
shrubs = [t for t in shrubs if not _uwz.contains(Point(t[1], t[2])) and not _uwb.contains(Point(t[1], t[2]))]
rng10 = random.Random(1997 + 2005)
_along = math.atan2(_wuu[1], _wuu[0])
for sg in (-1, 1):
    for k, u_ in enumerate(np.arange(6.6, 27.0, 4.0)):
        for v_, du_ in ((-40.6, 0.0), (-37.4, 2.0)):
            x_, y_ = wu_xy(sg * (u_ + du_), v_)
            shrubs.append(['topiary_round', round(x_, 2), round(y_, 2), round(rng10.uniform(0.95, 1.2), 2), 0])
    for u_ in np.arange(5.0, 27.0, 1.6):
        x_, y_ = wu_xy(sg * u_, -34.95)
        shrubs.append(['pansy_bed', round(x_, 2), round(y_, 2), 1.0, round(_along, 3)])
    x_, y_ = wu_xy(sg * 2.9, -35.4)
    shrubs.append(['topiary_round', round(x_, 2), round(y_, 2), 0.6, 0])
    x_, y_ = wu_xy(sg * 2.9, -36.6)
    shrubs.append(['pansy_bed', round(x_, 2), round(y_, 2), 0.7, round(_along, 3)])

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
for _sp, _tx, _ty, _sc, _ in trees:
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
    dict(id='gate', name='정문', pos=[-106, -410], r=22, photo=None,
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
    # the museum's own door on the hall's north-east face (blender/landmarks.py museum_entrance), towards 광혜원
    dict(id='museum', name='연세대학교 박물관', pos=[37.0, -175.4], r=14, photo=['photos/museum_1996.jpg', 'photos/museum_1996_side.jpg'],
         title='백주년기념관 박물관 입구', year='1996',
         credit='사진: 1997년 졸업 앨범의 학과 단체사진(1996년 5 ~ 6월, 2022 재상봉 25주년 기념문집 「25년 전 우리는」), 사람이 없는 윗부분',
         text='백주년기념관의 광혜원 쪽 면, 흰 원통과 흰 벽 사이로 비스듬히 기운 유리벽과 흰 관 기둥이 서 있고 「YONSEI UNIVERSITY MUSEUM」 긴 현수막이 걸려 있었다. 짙은 차양 아래 유리문으로 들어가면 박물관. 1996년 봄엔 「세계한민족 화학학술대회」와 박물관 강좌 「민요의 현장을 찾아서」 현수막이 걸렸고, 공대 여러 학과가 이 계단에서 졸업 사진을 찍었다.'),
    dict(id='eagle', name='독수리상', pos=[-52, -82], r=16, photo=['photos/eagle_2024.jpg'],
         title='독수리상', year='1997',
         text='연세의 상징 독수리. 높은 기둥 위에서 날개를 편 독수리는 지금도 같은 자리에서 백양로를 내려다본다.'),
    dict(id='hwalcheon', name='활천대', pos=FOUNTAIN['pos'], r=12, photo=['photos/hwalcheon_2009.jpg', 'photos/hwalcheon_2017.jpg'],
         title='활천대 (活泉臺)', year='1974',
         credit='사진: 연세춘추 「연세인도 모르는 연세대학교」(2009.9.5, 우리대학교 홈페이지 자료) · 연세대학교 공식 블로그 「연세대학교의 조형물을 찾아서!! 제3탄」(2017)',
         text='독수리상 옆의 분수대. 전기공학과 동창회가 모금해 1974년 앞뜰에 만들었고, 연세의 영향력이 사회 전 분야에 퍼지길 바라는 마음을 담았다고 한다. 흰 돌을 깎은 十자 기둥 꼭대기에서 물기둥이 솟고, 둘레에서는 물줄기가 종처럼 휘어 들었다. 공대 축제 「활천제」의 이름도 여기서 왔다. 백양로 재창조 뒤에는 제1공학관 앞으로 자리를 옮겼다.'),
    dict(id='library', name='중앙도서관', pos=[-58, -40], r=22, photo=['photos/library_1997.jpg', 'photos/library_reading_1997.jpg', 'photos/baekyangro_library_1995.jpg'],
         title='1997년 중앙도서관', year='1997',
         text='1984년 준공된 중앙도서관. 아치형 기둥이 늘어선 정면은 그 시절 연세인 모두의 배경이었다. 시험 기간이면 열람실 자리를 맡으려 새벽부터 줄을 섰다.'),
    dict(id='union', name='학생회관', pos=[0, -62], r=22, photo=['photos/union_1997.jpg', 'photos/marathon_news_1997.jpg'],
         title='1997년 학생회관', year='1997',
         credit='사진: 연세춘추 제1316호(1997.5.5) 「4·19 정신잇기」 김민정 기자 · 연세대학교 기록관',
         text='격자무늬 콘크리트 외벽의 학생회관. 동아리방과 식당, 총학생회가 있던 캠퍼스의 사랑방이었다. 벽면에는 늘 대자보와 현수막이 걸려 있었다. 1997년 4월 18일에는 이 앞에서 4·19 정신 계승 마라톤이 열렸다. 200여 명의 학생이 10km를 달리며 선전전을 벌였다.'),
    dict(id='chapel', name='루스채플', pos=[50, -70], r=18, photo=None,
         title='루스채플', year='1997',
         text='1974년 미국 헨리 루스 재단의 기부금과 학교 보조금으로 지어진 채플. 채플 수업 시간이면 학생들이 이 앞에 모여들었다.'),
    dict(id='auditorium', name='대강당', pos=[38, 30], r=22, photo=['photos/auditorium_2009.jpg', 'photos/auditorium_2009_side.jpg'],
         title='대강당', year='1980',
         text='1980년 완공된 대강당(선교70주년기념관). 입학식과 졸업식, 각종 집회와 공연이 열린 큰 무대였다. 화강석 판의 큰 박공 아래 놋쇠 틀 유리문 세 칸, 그 앞 열 단 계단 위의 넓은 현관.',
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
    dict(id='yongjae', name='용재관', pos=[71.8, 136.0], r=18, photo=['photos/yongjae_1990s.jpg'],
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
    eagle=dict(pos=[-52, -82], rot=math.radians(-14 + 90)),
    underwood_statue=dict(pos=[55.5, 187.5], rot=math.radians(-14)),
    court=dict(pos=COURT['pos'], rot=COURT['rot'], L=COURT['L'], W=COURT['W']),
    fountain=dict(pos=FOUNTAIN['pos'], r=FOUNTAIN['r'], rot=0.0),     # (the column's arms face the compass points)
    gate=dict(pos=[round(GATE[0], 2), round(GATE[1] + 4, 2)], rot=math.radians(-14)),
)
_tn = dict(TENNIS, rot=round(TENNIS['rot'], 5))
for v in STATUES.values():
    v['h'] = round(ground_h(*v['pos']), 2)
STATUES['tennis'] = _tn                 # (its pads carry their own levels)

_sx, _sy, _ = along_raw(30, E_VERGE + ROAD['walk'] * 0.5)        # on the west sidewalk just inside the gate
SPAWN = dict(pos=[round(_sx, 1), round(_sy, 1)], yaw=math.radians(-14))

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
os.makedirs(os.path.join(ROOT, 'web/public/data'), exist_ok=True)
Hn.astype(np.float32).tofile(os.path.join(ROOT, 'web/public/data/terrain_near.bin'))
Hf = np.array(tf['rows_south_to_north'], dtype=np.float32)
Hf = ndimage.gaussian_filter(Hf, 0.7).astype(np.float32)
Hf.tofile(os.path.join(ROOT, 'web/public/data/terrain_far.bin'))
# ---------------------------------------------------------------------------
# Building name markers (bird's-eye pins, walk-mode labels, big map).  One per name, over its largest footprint.
# MARKER_NAME: the name a 1997 student would use (or None: no marker, e.g. not built yet in 1997).
# ---------------------------------------------------------------------------
MARKER_NAME = {n: None for n in ('별동연구동', '영빈관', '영선실', '차량실', '행정동', '학생회관 별관', '광혜관')}
EXTRA_MARKERS = [('청송대', 238.0, 284.0), ('농구장', 21.9, 2.5)]          # the wooded park east of 연희관 (OSM leisure=park)
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
# back-projected onto the road profile with the photo's camera lands 132 m in from the gate, 0.34 m east of the
# centre line, 1.4 m across; a red-and-white barrier arm runs west from beside it across the outgoing lane (s ~134)
# and another east across the incoming lane further on (s ~138).  blender/props.py guard_booth / barrier_arm build
# it in a frame with the origin at the booth's centre, -Y up the road, +X west; the arm pivots below are that
# file's BOOTH_ARMS (x, y, z, side).  The cars keep clear of its island (web/src/main.js) and the arms swing up
# for them (web/src/life.js BoothGates).
BOOTH = dict(s=132.8, off=-0.34, island=[-0.85, 0.85, -6.0, 1.6])
_bx, _by, _ba = along_raw(BOOTH['s'], BOOTH['off'])
props.append(['guard_booth', round(_bx, 2), round(_by, 2), round(_ba, 3)])
BOOTH['arms'] = []
for _ax, _ay, _az, _sd in ((0.82, -1.5, 1.0, 1), (-0.82, -5.5, 1.0, -1)):
    _px = _bx + _ax * math.cos(_ba + math.pi / 2) + _ay * math.cos(_ba + math.pi)
    _py = _by + _ax * math.sin(_ba + math.pi / 2) + _ay * math.sin(_ba + math.pi)
    BOOTH['arms'].append(dict(x=round(_px, 2), y=round(_py, 2), z=_az, dir=round(_ba + _sd * math.pi / 2, 3),
                              s=round(BOOTH['s'] - _ay, 2), side=_sd))

out = dict(
    origin=[LAT0, LON0],
    terrain=dict(near=dict(half=NEAR_HALF, step=NEAR_STEP, n=n_near, file='data/terrain_near.bin'),
                 far=dict(half=tf['half'], step=tf['step'], n=tf['n'], file='data/terrain_far.bin')),
    splat=SPLAT,
    baekyangro=dict(pts=[[round(x, 2), round(y, 2)] for x, y in bys], profile_s=[round(v, 1) for v in ss[::2]],
                    profile_h=[round(float(v), 3) for v in prof[::2]], crossings=CROSS, bump=BUMP_S,
                    gaps=[list(g) for g in GAPS], mouths=[list(MOUTH)], apron_paint=APRON_PAINT, **ROAD),
    amphitheater={k: (round(v, 3) if isinstance(v, float) else v) for k, v in AMPH.items()},
    buildings=buildings, trees=trees, shrubs=shrubs, props=props, cars=cars, banners=banners,
    paths=paths_out, landmarks=LANDMARKS, statues=STATUES, spawn=SPAWN, markers=markers, daewoo_front=DAEWOO, daewoo_back=DAEWOO_BACK,
    centennial_block=CENT_BLOCK, sang=dict(c=list(SANG), r=SANG_LAWN), yeonhui=YEONHUI, underwood_steps=UW_STEPS,
    colliders=[CENT_BLOCK['poly']] +
    [[[round(x_, 2), round(y_, 2)] for x_, y_ in list(tennis_poly(pd_, 0.1).exterior.coords)[:-1]] for pd_ in TENNIS['pads']],
)
out['baekyangro']['booth'] = BOOTH
for p in (os.path.join(ROOT, 'data/campus.json'), os.path.join(ROOT, 'web/public/data/campus.json')):
    json.dump(out, open(p, 'w'), ensure_ascii=False, separators=(',', ':'))
np.save(os.path.join(ROOT, 'data/terrain_near.npy'), Hn.astype(np.float32))
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
          'magnolia': (250, 250, 235), 'poplar': (210, 220, 210)}[t[0]]
    d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=c_)
for l in LANDMARKS:
    x, y = tp(*l['pos'])
    d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=(255, 0, 255), width=2)
for bn in banners:
    d.line([tp(*bn['a'][:2]), tp(*bn['b'][:2])], fill=(0, 0, 255), width=2)
dbg.save(os.path.join(ROOT, 'data/debug_map.png'))
