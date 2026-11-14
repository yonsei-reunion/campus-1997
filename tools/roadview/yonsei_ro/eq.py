"""equirect panorama helpers (Kakao 4096 x 2048 tiles assembled by fetch.py).
pano frame: a = azimuth from image column (clockwise, 0 at the left edge), e = elevation from the row.
d = (cos e sin a, cos e cos a, sin e).  level frame = R d, R = Rx(pitch) @ Ry(roll) (small angles, degrees)."""
import os
import numpy as np
from PIL import Image

# work folder outside the repo (panoramas, strips, level.json): YRO_WORK, default /tmp/yonsei_ro
D = os.environ.get('YRO_WORK', '/tmp/yonsei_ro')
os.makedirs(f'{D}/td', exist_ok=True)
W, H = 4096, 2048


def load(pano, gray=False):
    im = Image.open(f'{D}/tiles/eq/{pano}.jpg')
    a = np.asarray(im.convert('L') if gray else im.convert('RGB'), np.float32)
    return a


def rot(pitch, roll):
    t, f = np.radians(pitch), np.radians(roll)
    Rx = np.array([[1, 0, 0], [0, np.cos(t), -np.sin(t)], [0, np.sin(t), np.cos(t)]])
    Ry = np.array([[np.cos(f), 0, np.sin(f)], [0, 1, 0], [-np.sin(f), 0, np.cos(f)]])
    return Rx @ Ry


def dir_of(a, e):
    return np.stack([np.cos(e) * np.sin(a), np.cos(e) * np.cos(a), np.sin(e)], -1)


def ae_of(d):
    return np.arctan2(d[..., 0], d[..., 1]) % (2 * np.pi), np.arcsin(np.clip(d[..., 2], -1, 1))


def cr_of(a, e):
    return a / (2 * np.pi) * W - 0.5, (np.pi / 2 - e) / np.pi * H - 0.5


def ae_of_cr(c, r):
    return 2 * np.pi * (c + 0.5) / W, np.pi / 2 - np.pi * (r + 0.5) / H


def sample(img, c, r):
    c = np.asarray(c) % W; r = np.clip(np.asarray(r), 0, H - 1.001)
    c0 = np.floor(c).astype(int); r0 = np.floor(r).astype(int)
    fc0 = c - c0; c0 = c0 % W
    fc = fc0; fr = r - r0
    c1 = (c0 + 1) % W; r1 = r0 + 1
    if img.ndim == 3:
        fc = fc[..., None]; fr = fr[..., None]
    return (img[r0, c0] * (1 - fc) * (1 - fr) + img[r0, c1] * fc * (1 - fr) + img[r1, c0] * (1 - fc) * fr + img[r1, c1] * fc * fr)


def level_sample(img, R, a, e):
    """sample the pano at level-frame directions (a, e)"""
    d = dir_of(a, e) @ R          # R^T d (rows)
    ap, ep = ae_of(d)
    return sample(img, *cr_of(ap, ep))


def topdown(img, R, psi, h, u0, u1, v0, v1, res):
    """ground image: u lateral (right +), v along psi (forward +), camera at (0, 0) height h (nominal m).
    psi: the road direction as a level-frame azimuth (rad).  rows: v1 (top) .. v0, cols: u0 .. u1"""
    us = np.arange(u0, u1, res); vs = np.arange(v1, v0, -res)
    U, V = np.meshgrid(us, vs)
    X = U * np.cos(psi) + V * np.sin(psi)
    Y = -U * np.sin(psi) + V * np.cos(psi)
    d = np.stack([X, Y, -np.full_like(X, h)], -1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    dp = d @ R
    ap, ep = ae_of(dp)
    return sample(img, *cr_of(ap, ep)), us, vs


def ground_of(R, c, r, psi, h=1.0):
    """pixel(s) -> ground (u, v) in the road frame; nan above the horizon"""
    a, e = ae_of_cr(np.asarray(c, float), np.asarray(r, float))
    d = dir_of(a, e) @ R.T
    t = -h / np.where(d[..., 2] < -1e-6, d[..., 2], np.nan)
    X, Y = d[..., 0] * t, d[..., 1] * t
    return X * np.cos(psi) - Y * np.sin(psi), X * np.sin(psi) + Y * np.cos(psi)
