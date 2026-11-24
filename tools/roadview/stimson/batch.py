"""batch.py <spec.txt> <sheet.png>   spec lines: pano feature ca cb r0 r1 [win] [sign] [manual]
  'manual' : take ca/cb as the reading (no edge search).  Updates readings.json {pano: {feature: [[c,r],[c,r]]}}."""
import os
import sys, json, numpy as np
from PIL import Image, ImageDraw
D = os.environ.get('ST_WORK', '/tmp/stimson_rv')
IM = {}
def gray(p):
    if p not in IM:
        im = Image.open(f'{D}/st/tiles/eq/{p}.jpg'); big = Image.new('RGB', (8192, 2048)); big.paste(im, (0, 0)); big.paste(im, (4096, 0))
        IM[p] = (big, np.asarray(big.convert('L'), float))
    return IM[p]
def fit(g, ca, cb, r0, r1, win, sign):
    pts = []
    for r in np.arange(int(r0), int(r1) + 1, 2):
        gg = ca + (cb - ca) * (r - r0) / (r1 - r0)
        lo, hi = int(gg - win - 2), int(gg + win + 3)
        band = np.convolve(g[r - 2:r + 3, lo:hi].mean(0), [0.25, 0.5, 0.25], 'same')
        d = np.diff(band)[1:-1]; k = d * sign if sign else np.abs(d); i = int(np.argmax(k))
        sub = 0.0
        if 0 < i < len(k) - 1:
            den = k[i - 1] - 2 * k[i] + k[i + 1]; sub = 0.5 * (k[i - 1] - k[i + 1]) / den if den else 0
        pts.append((r, lo + i + 2 + sub))
    P = np.array(pts); w = np.ones(len(P))
    for it in range(6):
        A = np.c_[np.ones(len(P)), P[:, 0] - r0]
        sol = np.linalg.lstsq(A * w[:, None], P[:, 1] * w, rcond=None)[0]
        res = P[:, 1] - A @ sol; s = max(np.sqrt(np.sum(w * res ** 2) / max(w.sum() - 2, 1)), 0.3)
        w = (np.abs(res) < 2.5 * s).astype(float)
    return sol, s, P, w
R = json.load(open(f'{D}/readings.json')) if len(sys.argv) > 3 or __import__('os').path.exists(f'{D}/readings.json') else {}
tiles = []
for ln in open(sys.argv[1]):
    t = ln.split('#')[0].split()
    if not t: continue
    pano, feat = t[0], t[1]; ca, cb, r0, r1 = map(float, t[2:6])
    win = float(t[6]) if len(t) > 6 else 5; sign = int(t[7]) if len(t) > 7 else 0; manual = 'manual' in t
    big, g = gray(pano)
    off = 4096 if min(ca, cb) < 0 else 0; ca += off; cb += off
    if manual:
        sol = np.array([ca, (cb - ca) / (r1 - r0)]); s = 0; P = np.zeros((0, 2)); w = np.zeros(0)
    else:
        sol, s, P, w = fit(g, ca, cb, r0, r1, win, sign)
    top = sol[0] - off; bot = sol[0] + sol[1] * (r1 - r0) - off
    R.setdefault(pano, {})[feat] = [[round(top % 4096, 2), r0]] if (manual and r1 - r0 < 3) else [[round(top % 4096, 2), r0], [round(bot % 4096, 2), r1]]
    print(f'{pano} {feat:6s} r{int(r0)} {top:8.2f}  r{int(r1)} {bot:8.2f}  lean {sol[1]:+.3f}  rms {s:.2f}  {int(w.sum())}/{len(w)}')
    c0 = int(min(ca, cb) - 30); c1 = int(max(ca, cb) + 30); S = 3
    cr = big.crop((c0, int(r0) - 15, c1, int(r1) + 15)).resize(((c1 - c0) * S, (int(r1) - int(r0) + 30) * S))
    d = ImageDraw.Draw(cr)
    for (r, c), ww in zip(P, w): d.point(((c - c0) * S, (r - r0 + 15) * S), fill='red' if ww else 'yellow')
    x0 = (sol[0] - c0) * S; x1 = (sol[0] + sol[1] * (r1 - r0) - c0) * S
    for dx in (-7, 7): d.line([(x0 + dx, 15 * S), (x1 + dx, (r1 - r0 + 15) * S)], fill='cyan')
    W = Image.new('RGB', (cr.width, cr.height + 14), 'white'); W.paste(cr, (0, 14)); ImageDraw.Draw(W).text((2, 1), f'{pano[-3:]} {feat}', fill='black')
    tiles.append(W)
json.dump(R, open(f'{D}/readings.json', 'w'), indent=0)
if tiles and sys.argv[2].endswith('.png'):
    H = max(t.height for t in tiles); Wd = sum(t.width + 8 for t in tiles)
    sheet = Image.new('RGB', (Wd, H), 'white'); x = 0
    for t in tiles: sheet.paste(t, (x, 0)); x += t.width + 8
    if sheet.width > 1900: sheet = sheet.resize((1900, int(sheet.height * 1900 / sheet.width)))
    sheet.save(sys.argv[2])
