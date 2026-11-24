"""over.py <pano> [x y]  overview crop with predicted feature columns"""
import os
import sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feat import *
from PIL import Image, ImageDraw
pano = int(sys.argv[1])
if len(sys.argv) > 3: P[pano]['xy'] = (float(sys.argv[2]), float(sys.argv[3]))
cs = {k: col(pano, v) for k, v in F.items()}
# span: stimson + appenzeller
c_ref = cs['ST_SE']
rel = {k: ((c - c_ref + 2048) % 4096) - 2048 for k, c in cs.items()}
lo = min(v for k, v in rel.items() if k.startswith(('ST', 'AP'))) - 120; hi = max(v for k, v in rel.items() if k.startswith(('ST', 'AP'))) + 120
c0 = int(c_ref + lo); c1 = int(c_ref + hi)
im = Image.open(f'{D}/st/tiles/eq/{pano}.jpg'); big = Image.new('RGB', (8192, 2048)); big.paste(im, (0, 0)); big.paste(im, (4096, 0))
if c0 < 0: c0 += 4096; c1 += 4096
c0 %= 4096; c1 = c0 + int(hi - lo)
cr = big.crop((c0, 800, c1, 1150))
s = min(1.0, 1500 / cr.width)
cr = cr.resize((int(cr.width * s), int(cr.height * s)))
W = Image.new('RGB', (cr.width, cr.height + 40), 'white'); W.paste(cr, (0, 40)); d = ImageDraw.Draw(W)
for k, c in cs.items():
    x = ((c - c0) % 4096) * s
    if 0 <= x < cr.width:
        d.line([(x, 25), (x, 40)], fill='red'); d.text((x - 10, 12 if k.startswith('ST') else 0), k[0:2] + k[3:], fill='black')
for c in range(c0 - c0 % 50 + 50, c1, 50):
    x = (c - c0) * s; d.line([(x, 36), (x, 40)], fill='blue')
    if c % 100 == 0: d.text((x + 1, 26), str(c % 4096), fill='blue')
W.save(f'{D}/o_{pano}.png'); print(pano, P[pano]['date'], 'c0', c0, 'scale', round(s, 3), {k: round(v) for k, v in cs.items()})
