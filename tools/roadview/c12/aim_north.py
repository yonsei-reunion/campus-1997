# 백양로 s 380 - 615 m (issue #132, not measured yet): aimed zoom-3 shots of the OSM corners around the road from the
# 2011-04 nodes (rv.mjs shots, opens by id) and the 2010-12 past panos (rv.mjs past: compare mode, whole-degree pans).
#   python aim_north.py 2011 189,191,...  > spec.json ; node ../rv.mjs shots spec.json <outDir>
#   python aim_north.py 2010 190,194,...  -> one `node ../rv.mjs past <node> 2010 <outDir> name:pan:P:3 ...` line per node
# Kakao node positions only aim the views.  What a first try (2026-11-11) found before reading:
# - 백양관's tall south wing ends about 5 deg (2011 191) to 4 deg (197) off OSM v5's bearing while 중앙도서관's NE corner
#   fits within 1.3 deg: the low front block (2005) may stand east of the wings, so which edge OSM v5 / v2 is must be
#   settled first (north/final.py used "bySE" from s 325 - 385 with residuals within 0.5 deg)
# - 대강당's front corners have a stepped parapet; read the same edge in every view (4.5 used the pediment middle too)
# - in 2011-04 the cherry trees and willows hide 핀슨관 · 스팀슨관 · 아펜젤러관; the 2010-12 compare views are leafless
#   but their heading frame differs from the node's by tens of degrees, so aimed pans can miss: take 8 directions
import json, math, sys
LN = {'libNE': (-65.91, 3.16), 'libNW': (-107.80, 14.03), 'bySE': (-24.10, 33.19), 'byNE': (-4.60, 105.49),
      'uNW': (34.00, -30.25), 'audSW': (51.13, 28.26), 'audNW': (59.82, 61.16), 'pinSE': (-65.1, 146.7),
      'pinNE': (-58.6, 171.7), 'stSW': (6.1, 214.6), 'stSE': (20.3, 210.8), 'appSW': (78.9, 192.1)}
NODES = {188: (-16.7, -47.8), 189: (-14.3, -38.6), 190: (-11.9, -29), 191: (-9.5, -19.5), 192: (-7.1, -9.9),
         193: (-4.7, -0.3), 194: (-1.9, 9.6), 195: (0.9, 19.6), 196: (3.7, 29.6), 197: (6.9, 39.5), 198: (9.7, 49.9),
         199: (12.4, 59.8), 200: (15.2, 69.8), 201: (18, 79.8), 202: (21.2, 89.7), 203: (24, 99.7), 204: (26.8, 110.1),
         205: (29.2, 117.2)}   # 10172201xx, Kakao positions (rv.mjs info)


def views(n):
    p = NODES[n]
    for k, q in LN.items():
        d, b = math.dist(p, q), math.degrees(math.atan2(q[0] - p[0], q[1] - p[1])) % 360
        if 8 < d < 230 and not (120 < b < 240 and d > 60):
            yield k, b


if __name__ == '__main__':
    year, nodes = sys.argv[1], [int(v) for v in sys.argv[2].split(',')]
    if year == '2011':
        spec = [dict(pano=1017220000 + n, look=list(LN[k]), tilt=0, zoom=3, name='a%d_%s' % (n, k)) for n in nodes for k, b in views(n)]
        json.dump(spec, sys.stdout, indent=1)
    else:
        for n in nodes:
            print('node ../rv.mjs past %d %s OUT ' % (1017220000 + n, year) + ' '.join('p%d_%s:pan:%d:3' % (n, k, math.floor(b)) for k, b in views(n)))
