# Readings for issue #132 (2026-11-11): 백주년기념관's north-west corner C12 seen from the 2010-12 north road, plus
# the 백양로 readings of tools/roadview/north (readings.py, readings2011.py) and bearings.py (eagle E, 활천대 F).
# Everything as (pano, target, bearing in the pano's own frame (deg), sd (deg)).
# North road: zoom 3 (f 783), whole-degree pans as rv.mjs printed, x read at 2 - 8x crops.
#   C12  the tall box's north-west vertical edge, read high on the wall (the attic corner the 백양로 panos read);
#        lower down the edge leans by up to 40 px (the overhanging upper floor or the camera's tilt): sd 3 - 8 px
#   C13b the corner block's east edge seen through the passage under it (958 - 961); a free tie point
#   E    the eagle pillar's middle; libSE the middle of the SE-facing strip (lit step - 3 px); libSW the left end of the
#        stone face; engT the left end of 제1공학관's east face (sd 6 px: a lower block at its south end, 25 px apart)
# 960 and 961 see only C12 and C13b (the mound's trees hide 학생회관 and the library) and add nothing on their own.
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', 'north'))
import readings as r10, readings2011 as r11, bearings as fb

NORTH = {
    'n956': dict(pano=1016786956, start=(-21.0, -171.3), obs=[
        ('C12', 135, 715.0, 3), ('E', 315, 282.0, 1.5), ('libSE', 0, 333.7, 3), ('libSE', 315, 981.7, 3),
        ('libNE', 0, 596.0, 3), ('engT', 225, 750.0, 6)]),
    'n957': dict(pano=1016786957, start=(-12.0, -172.0), obs=[
        ('C12', 165, 618.0, 4), ('E', 270, 826.5, 1.5), ('libSE', 315, 849.5, 3), ('libSW', 315, 712.0, 3),
        ('engT', 225, 736.0, 6)]),
    'n958': dict(pano=1016786958, start=(-4.0, -172.0), obs=[('C12', 195, 650.0, 8), ('C13b', 195, 306.0, 8), ('E', 270, 659.2, 1.5)]),
    'n959': dict(pano=1016786959, start=(4.0, -166.0), obs=[('C12', 195, 902.0, 3), ('C13b', 195, 709.0, 3), ('E', 270, 628.0, 3)]),
    'n960': dict(pano=1016786960, start=(12.0, -158.0), obs=[('C12', 215, 714.0, 2), ('C13b', 215, 598.0, 3)]),
    'n961': dict(pano=1016786961, start=(18.0, -150.0), obs=[('C12', 212, 763.0, 2), ('C13b', 212, 673.5, 3)]),
}


def _b(pan, x, f=783.0):
    return math.floor(pan + 1e-9) + math.degrees(math.atan((x - 694) / f))


R, START = [], {}
for p, d in NORTH.items():
    START[p] = d['start']
    for k, pan, x, sd in d['obs']:
        R.append((p, k, _b(pan, x), math.degrees(math.atan(sd / 783.0))))
# 백양로, s 267 - 335 m (tools/roadview/north): first the north/ readings, then what bearings.py adds (E, F, C12)
CAR = {}
have = set()
for P in (r10.P, r11.P):
    for name, d in P.items():
        START[name] = d['start']; CAR[name] = d['car']
        for k, v in d['obs'].items():
            sd = v[2] if len(v) > 2 else 1.5
            R.append((name, k.split('#')[0], _b(v[0], v[1]), math.degrees(math.atan(sd / 783.0)))); have.add((name, k.split('#')[0]))
KMAP = {'SE': 'libSE', 'NE': 'libNE'}
for i, k, pan, px, sg in fb.READ_SOUTH + fb.READ_NORTH:
    nm, kk = '2011@%d' % i, KMAP.get(k, k)
    if (nm, kk) in have: continue
    START.setdefault(nm, fb.XY[i]); R.append((nm, kk, fb.bearing(pan, px), sg))
for nm, d in fb.PAST2.items():
    START.setdefault(nm, d['start'])
    for k, pan, px, sg in d['obs']:
        if (nm, KMAP.get(k, k)) not in have: R.append((nm, KMAP.get(k, k), fb.bearing(pan, px), sg))
TIE0 = {'E': (-70.9, -159.8), 'F': (-83.1, -202.6), 'C13b': (-3.0, -183.0)}
