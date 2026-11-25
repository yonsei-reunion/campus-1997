import os
import json, math
D = os.environ.get('ST_WORK', '/tmp/stimson_rv')
U = (0.2516, 0.9678); N = (-0.9678, 0.2516)       # Stimson: along the front (north), toward the back (west)
SE = (20.39, 210.38); LEN = 35.09
def st(u, v): return (SE[0] + u * U[0] + v * N[0], SE[1] + u * U[1] + v * N[1])
F = dict(ST_SE=st(0, 0), ST_NE=st(LEN, 0), ST_SW=st(0, 13.0), ST_NW=st(LEN, 13.0),
         AP_SW=(79.83, 194.74), AP_NW=(88.8, 229.19), AP_SE=(92.32, 191.49), AP_NE=(101.28, 225.94),
         UW_SW=(39.39, 266.12), UW_NW=(43.01, 278.89), UW_SE=(88.06, 252.5), STATUE=(49.8, 198.2))
P = {}
for l in open(f'{D}/st/paths.jsonl'):
    j = json.loads(l)
    for i in j['items']:
        if i['date'] < '2012':
            p = i['position']; P[i['pano']] = dict(date=i['date'][:7], na=i['northAngle'], node=j['node'],
                                                   xy=(p[0] - 194522.4, p[1] - 451609.9))
def col(pano, xy, b=None):
    pp = P[pano]
    if b is None: b = math.degrees(math.atan2(xy[0] - pp['xy'][0], xy[1] - pp['xy'][1]))
    return ((b + pp['na']) % 360) * 4096 / 360 - 0.5
