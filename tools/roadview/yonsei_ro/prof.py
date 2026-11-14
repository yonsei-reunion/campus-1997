"""lateral profile of a section strip: median over rows (depth range) of gray and yellowness; plot under the strip.
   python prof.py <pano>_<tag> [v0 v1] [s0 s1]
   writes td/<name>_prof.png: the strip (cropped to v0..v1) with the profile curves and a tick ruler (0.1 s)."""
import sys, json
import numpy as np
from PIL import Image, ImageDraw
import eq

name = sys.argv[1]
st = np.load(f'{eq.D}/td/{name}_strip.npy'); m = json.load(open(f'{eq.D}/td/{name}_strip.json'))
v0, v1 = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (m['vmin'], m['vmax'])
s0, s1 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (-5, 5)
vs = m['vmin'] + np.arange(st.shape[0]) * m['dv']
S = m['s0'] + np.arange(st.shape[1]) * m['ds']
rk = (vs >= v0) & (vs <= v1); ck = (S >= s0) & (S <= s1)
sub = st[rk][:, ck]; S = S[ck]
g = sub.mean(2)
valid = sub.sum(2) > 0
gm = np.array([np.median(g[valid[:, j], j]) if valid[:, j].sum() > 5 else np.nan for j in range(len(S))])
yl = (sub[..., 0] + sub[..., 1]) / 2 - sub[..., 2]
ym = np.array([np.median(yl[valid[:, j], j]) if valid[:, j].sum() > 5 else np.nan for j in range(len(S))])
np.save(f'{eq.D}/td/{name}_prof.npy', np.c_[S, gm, ym])
sc = 1 if len(S) > 1200 else 2
Wd = len(S) * sc
top = Image.fromarray(np.clip(sub[::-1], 0, 255).astype(np.uint8)).resize((Wd, min(300, sub.shape[0] * sc)))
P = Image.new('RGB', (Wd, top.size[1] + 260), (255, 255, 255)); P.paste(top, (0, 0))
d = ImageDraw.Draw(P); y0 = top.size[1]
for j in range(len(S) - 1):
    if np.isfinite(gm[j]) and np.isfinite(gm[j + 1]):
        d.line([(j * sc, y0 + 250 - gm[j] * 0.9), ((j + 1) * sc, y0 + 250 - gm[j + 1] * 0.9)], fill=(0, 0, 0))
    if np.isfinite(ym[j]) and np.isfinite(ym[j + 1]):
        d.line([(j * sc, y0 + 250 - ym[j] * 1.2), ((j + 1) * sc, y0 + 250 - ym[j + 1] * 1.2)], fill=(220, 160, 0))
for s in np.arange(np.ceil(s0 * 10) / 10, s1 + 1e-6, 0.1):
    x = (s - S[0]) / m['ds'] * sc
    big = abs(s - round(s)) < 1e-6; half = abs(s * 2 - round(s * 2)) < 1e-6
    d.line([(x, y0), (x, y0 + (30 if big else 18 if half else 8))], fill=(255, 0, 0))
    if big or half:
        d.text((x + 2, y0 + 30), f'{s:.1f}', fill=(255, 0, 0))
P.save(f'{eq.D}/td/{name}_prof_{s0:+.1f}.png')
print(f'{eq.D}/td/{name}_prof_{s0:+.1f}.png', P.size)
