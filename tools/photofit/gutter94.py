# 1994 aerial photo: the book-spread gutter prints a ~136 px strip twice; check that the two copies are identical
# (shift and scale per row band), so the strip cannot bias anything measured across it.  python gutter94.py
import numpy as np
from PIL import Image
import os
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
im = np.asarray(Image.open(os.path.join(ROOT, 'reference/1994_캠퍼스_항공사진_전경.jpg')).convert('L')).astype(float)
H, W = im.shape
# find the page edge: column where the left page stops (look for discontinuity)
cols = np.abs(np.diff(im[200:1700], axis=1)).mean(axis=0)
print('biggest column jumps', np.argsort(cols)[-8:][::-1])
# for row bands, best shift and scale of left strip [x0,x1) into right page
def best(y0, y1, x0=1380, x1=1495):
    L = im[y0:y1, x0:x1]
    L = (L - L.mean()) / (L.std() + 1e-6)
    res = []
    for sc in np.linspace(0.95, 1.05, 21):
        for sh in np.arange(120, 152, 0.5):
            xs = (np.arange(x0, x1) - 1505) * sc + 1505 + sh
            xi = np.floor(xs).astype(int); fr = xs - xi
            R = im[y0:y1, xi] * (1 - fr) + im[y0:y1, xi + 1] * fr
            R = (R - R.mean()) / (R.std() + 1e-6)
            res.append(((L * R).mean(), sc, sh))
    return max(res)
for y0 in range(700, 1560, 60):
    c, sc, sh = best(y0, y0 + 60)
    print(y0 + 30, 'corr %.3f scale %.3f shift %.1f' % (c, sc, sh))
