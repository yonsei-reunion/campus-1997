"""count zebra periods between features: bars (index, s) fitted with s(n) = a + b n + c n^2, features located by
   inverting it.  python zcount.py "<n:s,n:s,...>" "<name:s,name:s,...>" [P=1.0]"""
import sys
import numpy as np

bars = [tuple(map(float, t.split(':'))) for t in sys.argv[1].split(',')]
feats = [(t.split(':')[0], float(t.split(':')[1])) for t in sys.argv[2].split(',')]
P = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
n = np.array([b[0] for b in bars]); s = np.array([b[1] for b in bars])
for deg in (1, 2):
    c = np.polyfit(n, s, deg)
    r = s - np.polyval(c, n)
    out = []
    for nm, sv in feats:
        roots = np.roots(np.r_[c[:-1], c[-1] - sv]) if deg == 2 else np.array([(sv - c[1]) / c[0]])
        roots = roots[np.isreal(roots)].real
        nn = roots[np.argmin(np.abs(roots - (sv - c[-1]) / c[-2]))]
        out.append((nm, nn))
    print(f'deg {deg}: coef {np.round(c, 5)} resid sd {r.std():.4f}  ' + '  '.join(f'{nm} n={nn:.3f}' for nm, nn in out))
    if len(out) >= 2:
        for i in range(len(out) - 1):
            print(f'    {out[i][0]} -> {out[i + 1][0]}: {(out[i + 1][1] - out[i][1]) * P:.3f} m')
        print(f'    {out[0][0]} -> {out[-1][0]}: {(out[-1][1] - out[0][1]) * P:.3f} m')
