"""신촌 로터리 둘레의 OSM 자료를 받아 data/raw/osm_rotary.json 에 둔다.

data/raw/osm_gate_south.json(tools/fetch_gate_osm.py)은 y = -1017 m(캠퍼스 좌표)에서 끝나고 건물 관계(multipolygon)를
버린다. 여기서는 로터리(y 약 -975 m)와 그 남쪽 서강로 · 백범로 어귀까지의 길과 건물 외곽선을 받는다(tools/sinchon_rotary.py
가 읽음. reference/고증/4.10_신촌_로터리.md). 건물 관계는 바깥 고리(outer)마다 한 외곽선으로 풀어, 관계의 태그와
id(10**12 + 관계 id)를 단다. osm_gate_south.json 과 같은 모양(way 마다 tags · geometry)이다.

    python3 tools/fetch_rotary_osm.py
"""
import json, os, re, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'data/raw/osm_rotary.json')
BBOX = (126.9300, 37.5525, 126.9430, 37.5575)        # west, south, east, north
URL = 'https://api.openstreetmap.org/api/0.6/map.json?bbox=%s' % ','.join('%.4f' % v for v in BBOX)
ROADS = re.compile(r'^(primary|secondary|tertiary|residential|living_street|unclassified|pedestrian|service)')
KEEP = ('highway', 'railway', 'building', 'building:levels', 'name', 'bridge', 'tunnel', 'layer', 'lanes', 'oneway',
        'amenity', 'shop', 'ref')
REL = 10 ** 12


def rings(ways):
    """join open member ways into closed rings (node id lists)"""
    out, open_ = [], [list(w) for w in ways if len(w) > 1]
    while open_:
        r = open_.pop(0)
        changed = True
        while r[0] != r[-1] and changed:
            changed = False
            for i, w in enumerate(open_):
                if w[0] == r[-1]:
                    r += w[1:]
                elif w[-1] == r[-1]:
                    r += w[::-1][1:]
                elif w[-1] == r[0]:
                    r = w[:-1] + r
                elif w[0] == r[0]:
                    r = w[::-1][:-1] + r
                else:
                    continue
                open_.pop(i)
                changed = True
                break
        if r[0] == r[-1] and len(r) > 3:
            out.append(r)
    return out


def main():
    req = urllib.request.Request(URL, headers={'User-Agent': 'osm-fetch-script/1.0'})
    data = json.loads(urllib.request.urlopen(req, timeout=180).read())
    nodes = {e['id']: (round(e['lat'], 6), round(e['lon'], 6)) for e in data['elements'] if e['type'] == 'node'}
    ways = {e['id']: e for e in data['elements'] if e['type'] == 'way'}
    geo = lambda ids: [dict(lat=nodes[n][0], lon=nodes[n][1]) for n in ids if n in nodes]
    els = []
    for e in ways.values():
        t = e.get('tags', {})
        if not (ROADS.match(t.get('highway', '')) or 'building' in t):
            continue
        g = geo(e['nodes'])
        if len(g) < 2:
            continue
        els.append(dict(type='way', id=e['id'], tags={k: v for k, v in t.items() if k in KEEP}, geometry=g))
    for e in data['elements']:
        t = e.get('tags', {})
        if e['type'] != 'relation' or t.get('type') != 'multipolygon' or 'building' not in t:
            continue
        outer = [ways[m['ref']]['nodes'] for m in e['members'] if m['type'] == 'way' and m['role'] == 'outer' and m['ref'] in ways]
        for k, r in enumerate(rings(outer)):
            g = geo(r)
            if len(g) >= 4:
                els.append(dict(type='way', id=REL + e['id'] * 10 + k, tags={k_: v for k_, v in t.items() if k_ in KEEP},
                                geometry=g))
    els.sort(key=lambda e: e['id'])
    json.dump(dict(bbox=BBOX, elements=els), open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
    kinds = {k: sum(1 for e in els if k in e['tags']) for k in ('highway', 'building')}
    print(len(els), 'ways', kinds, '->', OUT, os.path.getsize(OUT) // 1024, 'KB')


if __name__ == '__main__':
    main()
