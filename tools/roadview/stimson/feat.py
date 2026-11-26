import os
import json, math
D = os.environ.get('ST_WORK', '/tmp/stimson_rv')
U = (0.2516, 0.9678); N = (-0.9678, 0.2516)       # Stimson: along the front (north), toward the back (west)
SE = (20.39, 210.38); LEN = 35.09
HALL = os.environ.get('HALL', 'st')
if HALL == 'ap':      # HALL=ap: 아펜젤러관 under test instead (front west, back east; its game outline, 12.9 m across)
    _sw, _nw, _se = (79.83, 194.74), (88.8, 229.19), (92.32, 191.49)
    LEN = math.dist(_sw, _nw); U = ((_nw[0] - _sw[0]) / LEN, (_nw[1] - _sw[1]) / LEN)
    _w = math.dist(_sw, _se); N = ((_se[0] - _sw[0]) / _w, (_se[1] - _sw[1]) / _w); SE = _sw
def st(u, v): return (SE[0] + u * U[0] + v * N[0], SE[1] + u * U[1] + v * N[1])
# ST_* (or H_FS front-south, H_BS back-south, H_FN, H_BN, H_SMID gable middle) are the hall under test
F = dict(ST_SE=st(0, 0), ST_NE=st(LEN, 0), ST_SW=st(0, 13.0), ST_NW=st(LEN, 13.0),
         AP_SW=(79.83, 194.74), AP_NW=(88.8, 229.19), AP_SE=(92.32, 191.49), AP_NE=(101.28, 225.94),
         UW_SW=(39.39, 266.12), UW_NW=(43.01, 278.89), UW_SE=(88.06, 252.5), UW_NE=(91.68, 265.28), STATUE=(49.8, 198.2),
         SF_SE=(20.39, 210.38), SF_NE=(29.22, 244.35))      # 스팀슨관's front corners, as anchors for HALL=ap
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
