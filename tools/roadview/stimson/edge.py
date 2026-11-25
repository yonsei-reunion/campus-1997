"""edge.py <spec.txt> [sheet.png]   spec lines: pano feature c r0 r1 [win=6] [sign=0] [lean]
A straight near-vertical edge as one line: over columns c +- win and leans +-0.25 px/row, the line whose mean
horizontal gradient (rows r0..r1, sign +1 = brighter to the right, -1 = darker to the right, 0 = either) is largest.
The error is the spread of the same search on the top and bottom halves and on alternate rows.  Writes the reading
into readings.json like batch.py ([[c, r0], [c, r1]]), and a sheet of the crops with the line drawn."""
import os
import sys, json, numpy as np
from PIL import Image, ImageDraw
D = os.environ.get('ST_WORK', '/tmp/stimson_rv')
IM = {}


def gray(p):
    if p not in IM:
        im = Image.open(f'{D}/st/tiles/eq/{p}.jpg'); big = Image.new('RGB', (8192, 2048)); big.paste(im, (0, 0)); big.paste(im, (4096, 0))
        g = np.asarray(big.convert('L'), float)
        gx = np.zeros_like(g); gx[:, 1:-1] = (g[:, 2:] - g[:, :-2]) / 2
        IM[p] = (big, gx)
    return IM[p]


def search(gx, c, rows, win, sign, lean0=None):
    cs = np.arange(c - win, c + win + 0.001, 0.25)
    leans = np.arange(-0.25, 0.2501, 0.01) if lean0 is None else np.arange(lean0 - 0.01, lean0 + 0.0101, 0.005)
    rm = rows.mean(); best = (-1e9, c, 0)
    for ln in leans:
        X = cs[:, None] + ln * (rows[None, :] - rm)             # columns at each row
        i0 = np.floor(X).astype(int); f = X - i0
        v = gx[rows[None, :], i0] * (1 - f) + gx[rows[None, :], i0 + 1] * f
        m = v.mean(1)
        s = m * sign if sign else np.abs(m)
        k = int(np.argmax(s))
        if s[k] > best[0]: best = (s[k], cs[k], ln)
    return best


R = json.load(open(f'{D}/readings.json')) if os.path.exists(f'{D}/readings.json') else {}
tiles = []
for ln in open(sys.argv[1]):
    t = ln.split('#')[0].split()
    if not t: continue
    pano, feat = t[0], t[1]; c, r0, r1 = float(t[2]), int(t[3]), int(t[4])
    win = float(t[5]) if len(t) > 5 else 6; sign = int(t[6]) if len(t) > 6 else 0
    lean0 = float(t[7]) if len(t) > 7 else None          # the lean the pano's tilt gives (lean.py), +- 0.01
    big, gx = gray(pano)
    off = 4096 if c < 300 else 0; c += off
    rows = np.arange(r0, r1 + 1)
    s, cm, lean = search(gx, c, rows, win, sign, lean0)
    rm = rows.mean()
    sub = []
    for rr in (rows[:len(rows) // 2], rows[len(rows) // 2:], rows[::2], rows[1::2]):
        s2, c2, l2 = search(gx, cm + lean * (rr.mean() - rm), rr, 2.5, sign, lean0)
        sub.append(c2 - lean * (rr.mean() - rm))                 # back to the centre row
    err = float(np.std(sub, ddof=1)) if len(sub) > 1 else 0
    top = cm + lean * (r0 - rm) - off; bot = cm + lean * (r1 - rm) - off
    R.setdefault(pano, {})[feat] = [[round(top % 4096, 2), r0], [round(bot % 4096, 2), r1]]
    print(f'{pano} {feat:8s} r{r0} {top % 4096:8.2f}  r{r1} {bot % 4096:8.2f}  lean {lean:+.3f}  grad {s:5.1f}  err {err:.2f}  halves {[round(x - cm, 2) for x in sub]}')
    S = 4; c0 = int(c - win - 14); c1 = int(c + win + 14)
    rr0 = r0 - 10; rr1 = r1 + 10
    hh = rr1 - rr0
    if hh * S > 900: S2 = max(1, 900 // hh)
    else: S2 = S
    cr = big.crop((c0, rr0, c1, rr1)).resize(((c1 - c0) * S, hh * S2), Image.LANCZOS)
    d = ImageDraw.Draw(cr)
    x0 = (top + off - c0 + 0.5) * S; x1 = (bot + off - c0 + 0.5) * S
    d.line([(x0 - 2 * S, 10 * S2), (x1 - 2 * S, (hh - 10) * S2)], fill='cyan'); d.line([(x0 + 2 * S, 10 * S2), (x1 + 2 * S, (hh - 10) * S2)], fill='cyan')
    W = Image.new('RGB', (max(cr.width, 90), cr.height + 14), 'white'); W.paste(cr, (0, 14)); ImageDraw.Draw(W).text((2, 1), f'{pano[-3:]} {feat}', fill='black')
    tiles.append(W)
json.dump(R, open(f'{D}/readings.json', 'w'), indent=0)
if tiles and len(sys.argv) > 2:
    H = max(t.height for t in tiles); Wd = sum(t.width + 8 for t in tiles)
    sheet = Image.new('RGB', (Wd, H), 'white'); x = 0
    for t in tiles: sheet.paste(t, (x, 0)); x += t.width + 8
    if sheet.width > 1900: sheet = sheet.resize((1900, int(sheet.height * 1900 / sheet.width)))
    sheet.save(sys.argv[2])
