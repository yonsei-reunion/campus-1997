"""아래 얼굴의 길이와 코 밑 아래 옆선의 앞뒤 자리를 사람 GLB 에서 측정한다(고증 4.9.6).

  python3 tools/lower_face.py                        # 17명 모두와 남녀 평균
  python3 tools/lower_face.py <폴더> p01 p09         # 다른 폴더의 GLB(전 · 후 비교)
  PNG=out.png python3 tools/lower_face.py            # 옆선 그림도

얼굴 한가운데의 옆선(tools/nose_profile.py)에서: 코 밑(sn), 입술 사이(sto: 그림의 입 높이에서 가장 들어간 곳),
윗입술 · 아랫입술의 가장 나온 곳(ls · li), 입술 아래 오목한 곳(si), 턱 끝의 가장 나온 곳(pg), 턱 밑(me: 옆선이 2 mm에
4 mm 넘게 뒤로 꺾이는 곳).
  eye_sn  눈높이 - 코 밑, sn_sto 코 밑 - 입술 사이, sto_me 입술 사이 - 턱 밑, sn_me 코 밑 - 턱 밑 (mm)
  ratio   sto_me / sn_sto
  ls li si pg  그 점이 코 밑보다 앞(+) · 뒤(-)인 거리, li_si 아랫입술 - 오목한 곳의 높이차 (mm)
  nla nfa 비순각 · 비면각(nose_profile)
길이는 게임 안의 값이다.
"""
import sys, os, statistics as st
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nose_profile import measure
MEN = ['p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p16']
WOMEN = ['p09', 'p10', 'p11', 'p12', 'p13', 'p14', 'p15', 'p17']
S = {'m': 1.73 / 1.856, 'w': 1.61 / 1.797}
MOUTH = {'m': -.0747, 'w': -.0793}
def low(path, rig):
    m = measure(path)
    pr, eye, sn = m['pr'], m['eye'], m['sn']
    sto_y = eye + MOUTH[rig] * S[rig]
    at = lambda y: min(pr, key=lambda p: abs(p[0] - y))
    win = lambda lo, hi: [p for p in pr if lo <= p[0] <= hi]
    sto = min(win(sto_y - 0.0015, sto_y + 0.0015), key=lambda p: p[1])
    ls = max(win(sto[0], sn[0] - 0.003), key=lambda p: p[1])
    li = max(win(sto[0] - 0.012, sto[0] - 0.001), key=lambda p: p[1])
    # menton: going down, where the profile falls back more than 4 mm in 2 mm
    me = None
    below = [p for p in pr if p[0] < sto[0] - 0.008]
    for i in range(len(below) - 4):
        if below[i][1] - below[i + 4][1] > 0.004:
            me = below[i]; break
    me = me or below[-1]
    pg = max(win(me[0], li[0] - 0.006), key=lambda p: p[1])
    si = min(win(pg[0], li[0]), key=lambda p: p[1])
    mm = lambda v: v * 1000
    return dict(eye_sn=mm(eye - sn[0]), sn_sto=mm(sn[0] - sto[0]), sto_me=mm(sto[0] - me[0]), sn_me=mm(sn[0] - me[0]),
                ratio=(sto[0] - me[0]) / (sn[0] - sto[0]), ls=mm(ls[1] - sn[1]), li=mm(li[1] - sn[1]), si=mm(si[1] - sn[1]),
                pg=mm(pg[1] - sn[1]), li_si=mm(li[0] - si[0]), nla=m['nasolabial'], nfa=m['nasofacial'], pts=dict(sn=sn, sto=sto, ls=ls, li=li, si=si, pg=pg, me=me), m=m)
if __name__ == '__main__':
    args = sys.argv[1:]
    d = args.pop(0) if args and os.path.isdir(args[0]) else os.path.join(R, 'web', 'public', 'assets', 'models', 'people')
    ids = args or MEN + WOMEN
    K = ('eye_sn', 'sn_sto', 'sto_me', 'sn_me', 'ratio', 'ls', 'li', 'si', 'pg', 'li_si', 'nla', 'nfa')
    print('     ' + ' '.join(f'{k:>6}' for k in K))
    res = {}
    for i in ids:
        res[i] = low(os.path.join(d, i + '.glb'), 'm' if i in MEN else 'w')
        print(i, ' ' + ' '.join(f'{res[i][k]:6.1f}' if k != 'ratio' else f'{res[i][k]:6.2f}' for k in K))
    for name, g in (('men', MEN), ('wom', WOMEN)):
        r = [res[i] for i in g if i in res]
        if len(r) > 1:
            print(name, ' ' + ' '.join(f'{st.mean(x[k] for x in r):6.1f}' if k != 'ratio' else f'{st.mean(x[k] for x in r):6.2f}' for k in K))
    if os.environ.get('PNG'):
        from PIL import Image, ImageDraw
        k, W, H = 6000, 300, 640
        im = Image.new('RGB', (W * len(res), H), 'white'); dr = ImageDraw.Draw(im)
        for n, (i, r) in enumerate(res.items()):
            m = r['m']; ox = n * W
            to = lambda p: (ox + W - 60 - (m['tip'][1] - p[1]) * k, 150 - (p[0] - m['tip'][0]) * k)
            dr.line([to(p) for p in m['pr'] if -0.085 < p[0] - m['tip'][0] < 0.03], fill=(0, 0, 0), width=2)
            for key, c in (('sn', 'orange'), ('sto', 'red'), ('ls', 'purple'), ('li', 'purple'), ('si', 'blue'), ('pg', 'green'), ('me', 'brown')):
                x0, y0 = to(r['pts'][key]); dr.ellipse((x0 - 4, y0 - 4, x0 + 4, y0 + 4), outline=c, width=2)
            dr.text((ox + 8, 8), f"{i} nla {r['nla']:.0f} sto-me {r['sto_me']:.0f} ({r['ratio']:.2f})", fill=(200, 0, 0))
        im.save(os.environ['PNG'])
