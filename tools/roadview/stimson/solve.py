"""solve.py [--us sigma_m] [--fixvf] [--drop pano:feat,...] [--only pano,...] [--sig px] [--up [--tsig deg]]
Joint resection of the panoramas round 스팀슨관: per pano x, y, yaw, two tilts; Stimson's rear offsets WS, WN (and front
offsets vfS, vfN unless --fixvf); the chimney CH and Underwood's shift free.  Readings: readings.json.
--up: each pano's two tilts pulled (sigma --tsig, default 0.5 deg) to its 'up' in up.json (tilt.py) instead of 0 +- 14 deg."""
import os
import sys, json, math, numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feat import *
A = sys.argv[1:]
fixvf = '--fixvf' in A
sig = float(A[A.index('--sig') + 1]) if '--sig' in A else 1.5
drop = set(A[A.index('--drop') + 1].split(',')) if '--drop' in A else set()
only = set(A[A.index('--only') + 1].split(',')) if '--only' in A else None
vfp = float(A[A.index('--vfp') + 1]) if '--vfp' in A else 0.25
tsig = math.radians(float(A[A.index('--tsig') + 1])) if '--tsig' in A else math.radians(0.5)
UP = json.load(open(f'{D}/up.json')) if '--up' in A else {}
R = json.load(open(f'{D}/readings.json'))
obs = []
for p, fs in R.items():
    if only and p not in only and p[-3:] not in only: continue
    for f, pts in fs.items():
        if f'{p}:{f}' in drop or f'{p[-3:]}:{f}' in drop or f.startswith('_'): continue
        for c, r in pts: obs.append((p, f, c, r))
panos = sorted({o[0] for o in obs})
G = ['WS', 'WN', 'vfS', 'vfN', 'CHx', 'CHy', 'UWx', 'UWy', 'pk', 'us']
feats = {o[1] for o in obs}
if 'CH' not in feats: G = [g for g in G if not g.startswith('CH')]
if not any(f.startswith('UW') for f in feats): G = [g for g in G if not g.startswith('UW')]
if fixvf: G = [g for g in G if not g.startswith('vf')]
if not any(f.endswith('K') for f in feats): G.remove('pk')
if '--oneW' in A: G.remove('WN')
usp = float(A[A.index('--us') + 1]) if '--us' in A else None     # Stimson slid along its length: prior sigma (m)
if usp is None: G.remove('us')
gi = {g: i for i, g in enumerate(G)}; NG = len(G)
def gv(par, g, d=0.0): return par[gi[g]] if g in gi else d
ALIAS = dict(H_FS='ST_SE', H_BS='ST_SW', H_FN='ST_NE', H_BN='ST_NW', H_SMID='ST_SAPEX', H_NMID='ST_NAPEX')
def where(f, par):
    f = ALIAS.get(f, f)
    if f.startswith('ST_'):
        X, Y = where0(f, par); d = gv(par, 'us'); return (X + d * U[0], Y + d * U[1])
    return where0(f, par)
def where0(f, par):
    if f == 'ST_SE': return st(0, gv(par, 'vfS'))
    if f == 'ST_NE': return st(LEN, gv(par, 'vfN', gv(par, 'vfS')))
    if f == 'ST_SW': return st(0, gv(par, 'WS'))
    if f == 'ST_NW': return st(LEN, gv(par, 'WN', gv(par, 'WS')))
    if f == 'CH': return (par[gi['CHx']], par[gi['CHy']])
    if f == 'ST_SAPEX': return st(0, (gv(par, 'vfS') + gv(par, 'WS')) / 2)
    if f == 'ST_NAPEX': return st(LEN, (gv(par, 'vfN') + gv(par, 'WN')) / 2)
    if f == 'ST_SWK': return st(0, gv(par, 'WS') + gv(par, 'pk', 0.15))
    if f == 'ST_NWK': return st(LEN, gv(par, 'WN') + gv(par, 'pk', 0.15))
    if f == 'ST_SEK': return st(0, gv(par, 'vfS') - gv(par, 'pk', 0.15))
    if f == 'ST_NEK': return st(LEN, gv(par, 'vfN') - gv(par, 'pk', 0.15))
    if f == 'AP_SAPEX': return tuple((np.array(F['AP_SW']) + F['AP_SE']) / 2)
    if f == 'AP_NAPEX': return tuple((np.array(F['AP_NW']) + F['AP_NE']) / 2)
    if f.startswith('UW'): b = F[f]; return (b[0] + gv(par, 'UWx'), b[1] + gv(par, 'UWy'))
    return F[f]
def ray(c, r):
    az = 2 * math.pi * (c + 0.5) / 4096; el = math.pi / 2 - math.pi * (r + 0.5) / 2048
    return np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)])
def rot(yaw, ax, ay):
    cy, sy = math.cos(yaw), math.sin(yaw)
    Rz = np.array([[cy, sy, 0], [-sy, cy, 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    Ry = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    return Rz @ Rx @ Ry
RAYS = [ray(c, r) for _, _, c, r in obs]
def tilt0(p):
    """(ax, ay) that bring the pano's measured up to the zenith (rot's Rx Ry), or None."""
    if p not in UP: return None
    u = np.array(UP[p]); f = lambda t: (rot(0, t[0], t[1]) @ u)[:2]
    return least_squares(f, [0.0, 0.0]).x
T0 = {p: tilt0(p) for p in panos}
def wrap(a): return (a + math.pi) % (2 * math.pi) - math.pi
def resid(par):
    out = []
    for k, (p, f, c, r) in enumerate(obs):
        i = NG + 5 * panos.index(p); x, y, yaw, ax, ay = par[i:i + 5]
        d = rot(yaw, ax, ay) @ RAYS[k]
        X, Y = where(f, par)
        sg = sig * (2.5 if f == 'CH' else 1.5 if f.startswith(('AP', 'UW', 'SF')) else 1.0)
        out.append(wrap(math.atan2(d[0], d[1]) - math.atan2(X - x, Y - y)) / math.radians(sg * 360 / 4096))
    # priors
    for g in G:
        if g.startswith('vf'): out.append(par[gi[g]] / vfp)
        if g.startswith('UW'): out.append(par[gi[g]] / 0.5)
        if g == 'pk': out.append((par[gi[g]] - 0.15) / 0.15)
        if g == 'us': out.append(par[gi[g]] / usp)
    for j in range(len(panos)):
        i = NG + 5 * j; t0 = T0[panos[j]]
        out += [par[i + 3] / 0.25, par[i + 4] / 0.25] if t0 is None else [(par[i + 3] - t0[0]) / tsig, (par[i + 4] - t0[1]) / tsig]
    return np.array(out)
p0 = []
for g in G: p0.append({'WS': 13.0, 'WN': 13.0, 'CHx': 12.0, 'CHy': 230.0}.get(g, 0.0))
for p in panos:
    pp = P[int(p)]; t0 = T0[p] if T0[p] is not None else (0.0, 0.0)
    p0 += [pp['xy'][0], pp['xy'][1], math.radians(-pp['na']), t0[0], t0[1]]
p0 = np.array(p0)
best = None
for trial in range(6):   # yaw restarts
    q = p0.copy()
    if trial:
        rng = np.random.default_rng(trial); q[NG:] += np.tile([0, 0, 0, 0, 0], len(panos)); 
        for j in range(len(panos)): q[NG + 5 * j + 2] += math.radians(rng.normal(0, 6)); q[NG + 5 * j:NG + 5 * j + 2] += rng.normal(0, 2, 2)
    s = least_squares(resid, q, method='lm', max_nfev=20000)
    if best is None or s.cost < best.cost: best = s
s = best
J = s.jac; dof = max(len(s.fun) - len(s.x), 1)
C = np.linalg.pinv(J.T @ J)
chi = 2 * s.cost / dof
print(f'obs {len(obs)} panos {len(panos)} unknowns {len(s.x)}  chi2/dof {chi:.2f}  (sig {sig} px)')
for g in G: print(f'  {g:4s} {s.x[gi[g]]:8.3f} +- {math.sqrt(C[gi[g], gi[g]]):.3f}')
if 'WS' in gi and 'vfS' in gi:
    for e in 'SN':
        if 'W' + e not in gi or 'vf' + e not in gi: continue
        a, b = gi['W' + e], gi['vf' + e]; v = C[a, a] + C[b, b] - 2 * C[a, b]
        print(f'  width {e}: {s.x[a] - s.x[b]:.3f} +- {math.sqrt(v):.3f}')
for j, p in enumerate(panos):
    i = NG + 5 * j; x, y, yaw, ax, ay = s.x[i:i + 5]
    pp = P[int(p)]
    print(f'  {p} {pp["date"]}  xy ({x:7.2f}, {y:7.2f})  kakao ({pp["xy"][0]:.1f}, {pp["xy"][1]:.1f})  yaw {math.degrees(yaw) % 360:7.2f} (kakao {-pp["na"] % 360:.1f})  tilt {math.degrees(ax):+.2f} {math.degrees(ay):+.2f}')
    for k, o in enumerate(obs):
        if o[0] == p: print(f'      {o[1]:6s} c {o[2]:8.2f} r {o[3]:6.0f}  res {s.fun[k] * sig:+.2f} px')
