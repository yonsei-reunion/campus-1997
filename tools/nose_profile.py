"""옆에서 본 코의 선을 사람 GLB 에서 측정한다(고증 4.9.3).

  python3 tools/nose_profile.py                      # 17명 모두와 남녀 평균
  python3 tools/nose_profile.py --png out.png p01 p11   # 그 사람들의 옆선 그림도

얼굴 한가운데(x = 0)를 자른 선에서 기준점을 찾는다: 코끝(가장 앞), 코 밑(코의 밑면이 윗입술로 넘어가는 곳), 미간의
가장 들어간 곳(눈높이 둘레), 그 위 이마의 가장 나온 곳, 턱. 눈높이는 안경테의 가운데 높이로 삼는다.
  nasofrontal  비전두각: 이마 - 미간 - 코끝
  nasolabial   비순각: 코 밑면(코 밑에서 5 mm 나온 곳) - 코 밑 - 윗입술(7 mm 아래)
  nasofacial   비면각: 이마 - 턱의 선과 콧등(미간 - 코끝)의 선
  protrusion   비첨 돌출: 코 밑 - 코끝, mm
길이는 게임 안의 값(모델의 m)이다.
"""
import sys, json, struct, math
from glb_plain import read_bytes                # (the people are Draco-compressed: decoded first)
def load(path):
    d = read_bytes(path)
    n = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + n]); b = d[20 + n + 8:]
    def acc(i):
        a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]
        off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        fmt = {5126: 'f', 5123: 'H', 5121: 'B', 5125: 'I'}[a['componentType']]
        nc = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
        sz = struct.calcsize(fmt) * nc; st = v.get('byteStride') or sz
        return [struct.unpack_from('<' + fmt * nc, b, off + k * st) for k in range(a['count'])]
    segs, eye = [], None
    for m in j['meshes']:
        for p in m['primitives']:
            name = j['materials'][p['material']]['name']
            a = j['accessors'][p['attributes']['POSITION']]
            if name == 'Glasses':
                eye = (a['min'][1] + a['max'][1]) / 2
            if name not in ('Skin', 'Hair'):
                continue
            P = acc(p['attributes']['POSITION']); I = [i[0] for i in acc(p['indices'])]
            for t in range(0, len(I), 3):
                tri = [P[I[t + k]] for k in range(3)]
                if max(v[1] for v in tri) < 1.3 or min(v[2] for v in tri) < 0.0:
                    continue
                pts = []
                for k in range(3):
                    a_, c = tri[k], tri[(k + 1) % 3]
                    if (a_[0] > 0) != (c[0] > 0):
                        u = a_[0] / (a_[0] - c[0]); pts.append((a_[1] + (c[1] - a_[1]) * u, a_[2] + (c[2] - a_[2]) * u))
                if len(pts) == 2:
                    segs.append(pts)
    return segs, eye
def front(segs, step=0.0005):
    ys = [y for s in segs for y, _ in s]
    out, y = [], max(ys)
    while y > min(ys):
        best = None
        for (y0, z0), (y1, z1) in segs:
            if min(y0, y1) <= y <= max(y0, y1) and y0 != y1:
                z = z0 + (z1 - z0) * (y - y0) / (y1 - y0)
                best = z if best is None else max(best, z)
        if best is not None: out.append((y, best))
        y -= step
    return out
def ang(a, o, c):
    return math.degrees(math.acos(max(-1, min(1, ((a[0]-o[0])*(c[0]-o[0]) + (a[1]-o[1])*(c[1]-o[1])) / math.hypot(a[0]-o[0], a[1]-o[1]) / math.hypot(c[0]-o[0], c[1]-o[1])))))
def measure(path):
    segs, eye = load(path)
    pr = front(segs)
    win = lambda lo, hi: [p for p in pr if lo <= p[0] <= hi]
    tip = max(win(eye - 0.062, eye - 0.022), key=lambda p: p[1])
    # subnasale: going down from the tip, where the underside has run back to the lip (the profile stands upright again)
    below = [p for p in pr if p[0] < tip[0] - 0.002]
    sn = below[-1]
    for i in range(len(below) - 6):
        if abs(below[i + 6][1] - below[i][1]) < 0.35 * (below[i][0] - below[i + 6][0]):
            sn = below[i]; break
    ls = min(win(sn[0] - 0.0075, sn[0] - 0.0065), key=lambda p: p[0])               # (the lip, 7 mm under it)
    se = min(win(eye - 0.008, eye + 0.02), key=lambda p: p[1])
    gl = max(win(se[0] + 0.006, se[0] + 0.03), key=lambda p: p[1])
    pg = max(win(sn[0] - 0.060, sn[0] - 0.030), key=lambda p: p[1])
    under = [p for p in pr if sn[0] < p[0] < tip[0]]
    col = min(under, key=lambda p: abs(p[1] - sn[1] - 0.005))                       # (the underside, 5 mm out from the lip)
    # the dorsum's line against the face's plane
    facial = math.degrees(math.atan2(gl[1] - pg[1], gl[0] - pg[0]))          # (forward lean of glabella over the chin)
    dorsum = math.degrees(math.atan2(tip[1] - se[1], se[0] - tip[0]))
    return dict(pr=pr, eye=eye, tip=tip, sn=sn, ls=ls, se=se, gl=gl, pg=pg,
                nasofrontal=ang(gl, se, tip), nasolabial=ang(col, sn, ls), nasofacial=dorsum + facial,
                protrusion=math.hypot(tip[0] - sn[0], tip[1] - sn[1]) * 1000, dorsum=dorsum,
                length=math.hypot(tip[0] - se[0], tip[1] - se[1]) * 1000, height=(se[0] - sn[0]) * 1000,
                sellion_over_eye=(se[0] - eye) * 1000, sn_behind_se=(se[1] - sn[1]) * 1000)
if __name__ == '__main__':
    import os
    import statistics as st
    DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web', 'public', 'assets', 'models', 'people')
    MEN = ['p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p16']
    WOMEN = ['p09', 'p10', 'p11', 'p12', 'p13', 'p14', 'p15', 'p17']
    args = sys.argv[1:]
    png = None
    if args and args[0] == '--png':
        png, args = args[1], args[2:]
    ids = args or MEN + WOMEN
    res = {i: measure(i if i.endswith('.glb') else os.path.join(DIR, i + '.glb')) for i in ids}
    KEYS = ('nasofrontal', 'nasolabial', 'nasofacial', 'protrusion')
    for i, m in res.items():
        print(os.path.basename(i)[:3], ' '.join(f'{k} {m[k]:5.1f}' for k in KEYS), f"dorsum {m['dorsum']:4.1f}  sellion {m['sellion_over_eye']:+.1f} mm over the eyes")
    for name, group in (('men', MEN), ('women', WOMEN)):
        ms = [res[i] for i in group if i in res]
        if len(ms) > 1:
            print(name, ' '.join(f"{k} {st.mean(m[k] for m in ms):.1f} ({min(m[k] for m in ms):.1f} - {max(m[k] for m in ms):.1f})" for k in KEYS))
    if png:
        from PIL import Image, ImageDraw
        k, W, H = 5000, 330, 620
        im = Image.new('RGB', (W * len(res), H), 'white')
        dr = ImageDraw.Draw(im)
        for n, (name, m) in enumerate(res.items()):
            ox = n * W
            to = lambda p: (ox + W - 50 - (m['tip'][1] - p[1]) * k, 330 - (p[0] - m['tip'][0]) * k)      # noqa: E731
            dr.line([to(p) for p in m['pr'] if -0.055 < p[0] - m['tip'][0] < 0.065], fill=(0, 0, 0), width=2)
            for key, c in (('tip', 'red'), ('se', 'blue'), ('gl', 'green'), ('sn', 'orange'), ('ls', 'purple')):
                x0, y0 = to(m[key])
                dr.ellipse((x0 - 4, y0 - 4, x0 + 4, y0 + 4), outline=c, width=2)
            dr.text((ox + 8, 8), f"{os.path.basename(name)[:3]}  {m['nasofrontal']:.0f}  {m['nasolabial']:.0f}  {m['nasofacial']:.0f}  {m['protrusion']:.1f} mm", fill=(200, 0, 0))
        im.save(png)
