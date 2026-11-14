"""다른 해의 항공사진(assets_src/aerial_other/, 카메라를 맞추지 않음)을 1997년 7월 사진(자료 Q)의 백양로 띠 조각에 대어 보는 도구.

  PYTHONPATH=<opencv 를 둔 곳> FR=26/15 .venv/bin/python tools/aerial_years.py <사진> <s0> <s1> <반폭 m> <out.png>

옮긴 게임 중심선을 따라 편 조각(0.15 m 간격, s 는 세로, 가로는 중심선에서 동 · 서)을 1997년 사진 FR 에서 만들고,
같은 자리를 다른 해 사진에서 SIFT 호모그래피(전체 사진 → 띠 둘레 창)로 찾아 나란히 그린다(out.png, 다른 해의 조각은 out.png.npy).
땅을 평면으로 보므로 띠 둘레 몇 m 안에서만 맞고, 등록 오차는 s 방향으로 1 ~ 4 m(1996년 겨울 사진은 맞는 점이 적어 더 큼).
opencv 는 venv 에 없음: pip install --target <스크래치>/pylib opencv-python-headless
"""
import sys, os, numpy as np, cv2
sys.path.insert(0, 'tools')
import aerial97 as A
from aerial97_check import centre_line
from PIL import Image
img, s0, s1, HW, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
L, along = centre_line()
res = 0.15
ss = np.arange(s1, s0, -res); oo = np.arange(-HW, HW, res)
XY = np.array([[along(s, -o)[:2] for o in oo] for s in ss]); X, Y = XY[..., 0], XY[..., 1]
fr = tuple(int(v) for v in os.environ.get('FR', '26/15').split('/'))
p = A.to_px(fr, X, Y, A.ground(X, Y))
ref = A.sample(fr, p[..., 0], p[..., 1]).astype(np.float32)
def norm(a):
    lo, hi = np.percentile(a, [1, 99.5]); return np.clip((a - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
ref8 = norm(ref)
new = cv2.imread(img, cv2.IMREAD_GRAYSCALE)
old = norm(np.asarray(Image.open(A.FRAMES[fr]['file'] if 'file' in A.FRAMES[fr] else 'assets_src/aerial_1997/ngii_1997_199705A0301_c%d_n%d.jpg' % fr).convert('L')).astype(np.float32))
sift = cv2.SIFT_create(20000)
# global: old full frame -> new full frame
k1, d1 = sift.detectAndCompute(cv2.resize(old, None, fx=0.5, fy=0.5), None)
k2, d2 = sift.detectAndCompute(cv2.resize(new, None, fx=0.5, fy=0.5), None)
m = cv2.BFMatcher().knnMatch(d1, d2, k=2); g = [a for a, b in m if a.distance < 0.75 * b.distance]
P1 = np.float32([k1[a.queryIdx].pt for a in g]) * 2; P2 = np.float32([k2[a.trainIdx].pt for a in g]) * 2
H, inl = cv2.findHomography(P1, P2, cv2.RANSAC, 8.0)
print('global matches', len(g), 'inliers', int(inl.sum()))
# local: full-res window round the strip, old -> new
x0, y0 = int(p[..., 0].min()) - 250, int(p[..., 1].min()) - 250
x1, y1 = int(p[..., 0].max()) + 250, int(p[..., 1].max()) + 250
wo = old[y0:y1, x0:x1]
c = cv2.perspectiveTransform(np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]).reshape(-1, 1, 2), H).reshape(-1, 2)
nx0, ny0 = np.maximum(c.min(0).astype(int) - 150, 0); nx1, ny1 = c.max(0).astype(int) + 150
wn = new[ny0:ny1, nx0:nx1]
cl = cv2.createCLAHE(3.0, (8, 8))
k1, d1 = sift.detectAndCompute(cl.apply(wo), None); k2, d2 = sift.detectAndCompute(cl.apply(wn), None)
m = cv2.BFMatcher().knnMatch(d1, d2, k=2); g = [a for a, b in m if a.distance < 0.8 * b.distance]
P1 = np.float32([k1[a.queryIdx].pt for a in g]) + [x0, y0]; P2 = np.float32([k2[a.trainIdx].pt for a in g]) + [nx0, ny0]
pre = cv2.perspectiveTransform(P1.reshape(-1, 1, 2), H).reshape(-1, 2)
ok = np.hypot(*(pre - P2).T) < 40
H2, inl = cv2.findHomography(P1[ok], P2[ok], cv2.RANSAC, 3.0)
e = cv2.perspectiveTransform(P1[ok][inl.ravel() > 0].reshape(-1, 1, 2), H2).reshape(-1, 2) - P2[ok][inl.ravel() > 0]
print('local matches', len(g), 'near', int(ok.sum()), 'inliers', int(inl.sum()), 'rms px %.2f' % np.sqrt((e ** 2).sum(1).mean()))
q = cv2.perspectiveTransform(p.reshape(-1, 1, 2).astype(np.float32), H2).reshape(p.shape)
nstrip2 = cv2.remap(new, q[..., 0].astype(np.float32), q[..., 1].astype(np.float32), cv2.INTER_LINEAR)
np.save(out + '.npy', nstrip2)
both = np.concatenate([ref8, np.full((ref8.shape[0], 6), 255, np.uint8), norm(nstrip2.astype(np.float32))], 1)
im = Image.fromarray(both).convert('RGB'); im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
from PIL import ImageDraw
d = ImageDraw.Draw(im)
for s in np.arange(np.ceil(s0 / 5) * 5, s1, 5):
    yy = (s1 - s) / res * 2; d.line([0, yy, 14 if s % 10 else 28, yy], fill=(0, 255, 255))
    if s % 10 == 0: d.text((30, yy - 6), '%d' % s, fill=(0, 255, 255))
im.save(out); print(out, im.size)
