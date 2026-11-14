"""sheet of kerb profiles: for each (name, side yellow s, direction) a panel over yellow-0.15 .. yellow+0.6 outward.
   python kerbsheet.py out.png name:ys:dir[:v0:v1] ...   dir = -1 (kerb at smaller s) or +1"""
import sys, json
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter1d
import eq

out = sys.argv[1]
panels = []
for spec in sys.argv[2:]:
    t = spec.split(':'); name, ys, dr = t[0], float(t[1]), int(t[2])
    v0, v1 = (float(t[3]), float(t[4])) if len(t) > 4 else (6, 18)
    st = np.load(f'{eq.D}/td/{name}_strip.npy'); m = json.load(open(f'{eq.D}/td/{name}_strip.json'))
    vs = m['vmin'] + np.arange(st.shape[0]) * m['dv']; S = m['s0'] + np.arange(st.shape[1]) * m['ds']
    lo, hi = sorted([ys - dr * 0.15, ys + dr * 0.6])
    ck = (S >= lo) & (S <= hi); rk = (vs >= v0) & (vs <= v1)
    sub = st[rk][:, ck]; Sc = S[ck]
    if dr < 0:
        sub = sub[:, ::-1]; Sc = Sc[::-1]
    g = np.median(sub.mean(2), 0); g = gaussian_filter1d(g, 1.5)
    W, Hh = 600, 300
    im = Image.new('RGB', (W, Hh + 120), (255, 255, 255))
    top = Image.fromarray(np.clip(sub[::-1], 0, 255).astype(np.uint8)).resize((W, Hh))
    im.paste(top, (0, 0)); d = ImageDraw.Draw(im)
    xs = np.linspace(0, W - 1, len(g))
    gn = (g - g.min()) / max(1e-6, g.max() - g.min())
    for i in range(len(g) - 1):
        d.line([(xs[i], Hh + 110 - gn[i] * 90), (xs[i + 1], Hh + 110 - gn[i + 1] * 90)], fill=(0, 0, 0), width=2)
    for k in range(-15, 61, 5):
        sv = ys + dr * k / 100.0
        x = (abs(sv - Sc[0])) / abs(Sc[-1] - Sc[0]) * (W - 1)
        d.line([(x, Hh), (x, Hh + (20 if k % 10 == 0 else 10))], fill=(255, 0, 0))
        if k % 10 == 0:
            d.text((x + 2, Hh + 20), f'{sv:+.2f}', fill=(255, 0, 0))
    d.text((5, 5), f'{name} yellow {ys:+.3f} dir {dr:+d} v{v0:g}-{v1:g}', fill=(255, 255, 0))
    panels.append(im)
cols = 2
rows = (len(panels) + 1) // cols
S_ = Image.new('RGB', (600 * cols, 420 * rows), (200, 200, 200))
for i, p in enumerate(panels):
    S_.paste(p, ((i % cols) * 600, (i // cols) * 420))
S_.save(out)
print(out, S_.size)
