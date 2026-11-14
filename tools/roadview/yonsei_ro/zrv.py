"""zebra bars in a roadview section strip: profile across s within v0..v1, bar centres and period (s units).
   python zrv.py <strip name> <v0> <v1> [s0 s1] [--png]"""
import sys, json
import numpy as np
from PIL import Image
import eq

name, v0, v1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
s0, s1 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 and not sys.argv[4].startswith('--') else (-5, 5)
st = np.load(f'{eq.D}/td/{name}_strip.npy'); m = json.load(open(f'{eq.D}/td/{name}_strip.json'))
vs = m['vmin'] + np.arange(st.shape[0]) * m['dv']
S = m['s0'] + np.arange(st.shape[1]) * m['ds']
rk = (vs >= v0) & (vs <= v1); ck = (S >= s0) & (S <= s1)
sb = st[rk][:, ck]; S = S[ck]
sub = sb.min(2) - 0.6 * (sb.max(2) - sb.min(2))   # whiteness: bright and grey (not the yellow lines)
p = np.percentile(sub, 50, 0)
q = p - np.convolve(p, np.ones(101) / 101, 'same')
thr = 0.35 * q.max()
# bar = contiguous run above thr; centre = mean of the run's half-max edges
runs = []; i = 0
while i < len(q):
    if q[i] > thr:
        j = i
        while j < len(q) and q[j] > thr:
            j += 1
        if 0.06 < S[j - 1] - S[i] < 0.24:
            runs.append((S[i], S[j - 1]))
        i = j
    else:
        i += 1
cen = np.array([(a + b) / 2 for a, b in runs]); wid = np.array([b - a for a, b in runs])
print(name, f'v {v0}-{v1}', 'bars', len(cen))
print(' centres', ' '.join(f'{c:.3f}' for c in cen))
print(' widths ', ' '.join(f'{w:.3f}' for w in wid))
if len(cen) > 2:
    d = np.diff(cen)
    print(' gaps   ', ' '.join(f'{x:.3f}' for x in d))
    good = np.abs(d - np.median(d)) < 0.25 * np.median(d)
    n = np.round((cen - cen[0]) / np.median(d))
    A = np.c_[n, np.ones(len(n))]
    sol = np.linalg.lstsq(A, cen, rcond=None)[0]
    print(f' period (fit) {sol[0]:.4f}  resid sd {np.std(cen - A @ sol):.4f}  span {cen[-1] - cen[0]:.3f} over {int(n[-1])} periods')
if '--png' in sys.argv:
    Image.fromarray(np.clip(st[rk][:, ck][::-1], 0, 255).astype(np.uint8)).save(f'{eq.D}/td/{name}_z.png')
