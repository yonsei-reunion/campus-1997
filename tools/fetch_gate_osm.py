"""정문 밖(성산로 남쪽)의 OSM 자료를 받아 data/raw/osm_gate_south.json 에 둔다.

data/raw/osm_campus.json 은 y = -498 m(캠퍼스 좌표)에서 끝나 경의선과 창천동이 없다. 여기서는 그 남쪽의 철도 선형,
길, 건물 외곽선만 받는다(tools/build_campus.py 의 「정문 밖」이 읽음. reference/고증/4.8_정문_밖.md).
OSM API 의 map 호출 한 번(상자 하나)이고, osm_campus.json 과 같은 모양(way 마다 tags · geometry)으로 줄여 적는다.

    python3 tools/fetch_gate_osm.py
"""
import json, os, re, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'data/raw/osm_gate_south.json')
BBOX = (126.9305, 37.5548, 126.9455, 37.5612)        # west, south, east, north
URL = 'https://api.openstreetmap.org/api/0.6/map.json?bbox=%s' % ','.join('%.4f' % v for v in BBOX)
ROADS = re.compile(r'^(primary|secondary|tertiary|residential|living_street|unclassified|pedestrian|service)')
RAILS = ('rail', 'light_rail', 'disused', 'abandoned')
KEEP = ('highway', 'railway', 'building', 'building:levels', 'name', 'bridge', 'tunnel', 'layer', 'lanes', 'oneway',
        'embankment', 'cutting', 'service', 'electrified', 'gauge', 'usage', 'amenity', 'religion')


def main():
    req = urllib.request.Request(URL, headers={'User-Agent': 'osm-fetch-script/1.0'})
    data = json.loads(urllib.request.urlopen(req, timeout=120).read())
    nodes = {e['id']: (round(e['lat'], 6), round(e['lon'], 6)) for e in data['elements'] if e['type'] == 'node'}
    els = []
    for e in data['elements']:
        t = e.get('tags', {})
        if e['type'] != 'way' or not (t.get('railway') in RAILS or ROADS.match(t.get('highway', '')) or 'building' in t):
            continue
        g = [nodes[n] for n in e['nodes'] if n in nodes]
        if len(g) < 2:
            continue
        els.append(dict(type='way', id=e['id'], tags={k: v for k, v in t.items() if k in KEEP},
                        geometry=[dict(lat=a, lon=b) for a, b in g]))
    els.sort(key=lambda e: e['id'])
    json.dump(dict(bbox=BBOX, elements=els), open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
    kinds = {k: sum(1 for e in els if k in e['tags']) for k in ('railway', 'highway', 'building')}
    print(len(els), 'ways', kinds, '->', OUT, os.path.getsize(OUT) // 1024, 'KB')


if __name__ == '__main__':
    main()
