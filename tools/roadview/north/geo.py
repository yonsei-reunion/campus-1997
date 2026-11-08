# game line (bline) as in tools/build_campus.py, plus OSM buildings
import json, math, os
from shapely.geometry import LineString, Point, Polygon
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
LAT0, LON0 = 37.5640, 126.9380
def xy(p):
    return ((p['lon'] - LON0) * 111320 * math.cos(math.radians(LAT0)), (p['lat'] - LAT0) * 110574)
osm = json.load(open(os.path.join(ROOT, 'data/raw/osm_campus.json')))['elements']
ways = {e['id']: e for e in osm if e.get('geometry')}
bys = None
for w in ways.values():
    if w.get('tags', {}).get('name') == '백양로' and w['tags'].get('highway') == 'pedestrian':
        bys = [xy(p) for p in w['geometry']]
bys = list(reversed(bys))
bys = [(-108.0, -428.0)] + bys[1:] + [(33.0, 145.0), (38.0, 168.0)]
OSMLINE = LineString(bys)
_bl0 = LineString(bys)
def _west(s):
    return 4.0 if s <= 300 else 4.0 * max(0.0, (520 - s) / 220)
_sh = []
for _x, _y in bys:
    _s = _bl0.project(Point(_x, _y))
    _p0, _p1 = _bl0.interpolate(max(0, _s - 2)), _bl0.interpolate(min(_bl0.length, _s + 2))
    _tx, _ty = _p1.x - _p0.x, _p1.y - _p0.y
    _n = math.hypot(_tx, _ty)
    _sh.append((round(_x - _ty / _n * _west(_s), 2), round(_y + _tx / _n * _west(_s), 2)))
bline = LineString(_sh)
def s_off(x, y, line=bline):
    """s along line, offset EAST (+) of it"""
    s = line.project(Point(x, y))
    p = line.interpolate(s); p2 = line.interpolate(min(line.length, s + 1)); p0 = line.interpolate(max(0, s - 1))
    tx, ty = p2.x - p0.x, p2.y - p0.y; n = math.hypot(tx, ty)
    # east of a north-going line = right side: (ty, -tx)
    return s, ((x - p.x) * ty - (y - p.y) * tx) / n
if __name__ == '__main__':
    import sys
    print('bline length', bline.length)
    XY = {169: (-61.3, -220.8), 172: (-53.3, -192.5), 175: (-46.5, -165.4), 178: (-38.6, -135.5), 181: (-32.6, -112.7),
          184: (-25.8, -86.0), 187: (-18.6, -57.3)}
    for i, p in XY.items():
        s, e = s_off(*p); s2, e2 = s_off(*p, OSMLINE)
        print(i, p, 's %.1f east of game %.2f, east of OSM %.2f' % (s, e, e2))
    for w in ways.values():
        t = w.get('tags', {})
        if 'building' in t:
            pts = [xy(p) for p in w['geometry']]
            c = Polygon(pts).centroid
            if -200 < c.x < 150 and -300 < c.y < 200:
                print(w['id'], t.get('name'), '(%.0f, %.0f)' % (c.x, c.y), len(pts))
