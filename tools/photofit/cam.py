# pinhole camera in the game frame (x east, y north, z up); params p = [x, y, z, yaw°, pitch°, roll°, f_px]
import math
import numpy as np


def basis(p):
    yaw, pit, rol = np.radians(p[3]), np.radians(p[4]), np.radians(p[5])
    d = np.array([math.sin(yaw) * math.cos(pit), math.cos(yaw) * math.cos(pit), math.sin(pit)])
    r0 = np.array([math.cos(yaw), -math.sin(yaw), 0.0])
    u0 = np.cross(r0, d)
    r = r0 * math.cos(rol) + u0 * math.sin(rol)
    u = -r0 * math.sin(rol) + u0 * math.cos(rol)
    return np.array(p[:3], float), d, r, u, p[6]


def project(p, X, W, H, off=(0.0, 0.0)):
    C, d, r, u, f = basis(p)
    v = np.atleast_2d(np.asarray(X, float)) - C
    z = v @ d
    return np.stack([W / 2 + off[0] + f * (v @ r) / z, H / 2 + off[1] - f * (v @ u) / z], -1)


def ray(p, px, py, W, H, off=(0.0, 0.0)):
    C, d, r, u, f = basis(p)
    v = d + (px - W / 2 - off[0]) / f * r - (py - H / 2 - off[1]) / f * u
    return C, v / np.linalg.norm(v)


def ground(p, px, py, W, H, hfun, z0=40.0, off=(0.0, 0.0), it=30):
    """where the ray through a pixel meets the surface z = hfun(x, y)"""
    C, v = ray(p, px, py, W, H, off)
    z = z0
    for _ in range(it):
        t = (z - C[2]) / v[2]
        x, y = C[0] + v[0] * t, C[1] + v[1] * t
        z2 = float(hfun(x, y))
        if abs(z2 - z) < 1e-4:
            break
        z = z + 0.7 * (z2 - z)
    return np.array([x, y, z])


def depress(p, px, py, W, H, off=(0.0, 0.0)):
    C, v = ray(p, px, py, W, H, off)
    return math.degrees(-math.asin(v[2]))
