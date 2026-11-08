# Issue #82 (road): s 300-385 carriageway from heading-free resection of 2010-12 / 2011-04 panos on unchanged OSM
# corners (lm.py: 중앙도서관, 학생회관, 백양관, 백주년기념관), and Kakao's stored positions vs the resected cameras.
#   cd tools/roadview/north && uv run --with numpy --with scipy --with shapely python final.py
# Readings: run2010.py, run2011.py (pans as rv.mjs printed them); car offsets: lanes2.py on the yellow edge lines.
# Kakao's stored positions come from rv.map.kakao.com roadview-search/v2/node/<2011 node> records saved as
# api/n10172201xx.json (not in the repo); without them that column is skipped.
# Result 2026-11-08 (reference/고증.md 2.2.1): road centre +2.0 .. +2.7 m east of the game line at s 353 - 383 (2010 and
# 2011 drives apart), +4.3 at s 304 (weak), 181 unresolved; the 2010-12 panos sit on the 2011 node line (moved there).
import json, glob, math, os
import numpy as np
from scipy.optimize import least_squares
from lm import L, bearing
from geo import s_off, OSMLINE
import run2010, run2011
P = {**run2010.P, **run2011.P}
EAST = np.array([0.9668, -0.2554]); ROADV = np.array([0.2554, 0.9668])
LAT0, LON0 = 37.5640, 126.9380
def g(lon, lat): return ((lon - LON0) * 111320 * math.cos(math.radians(LAT0)), (lat - LAT0) * 110574)
def az(p, q): return math.degrees(math.atan2(q[0] - p[0], q[1] - p[1]))
def wrap(d): return (d + 180) % 360 - 180
# road direction in each pano's own frame, from the yellow-line vanishing point (lanes2.py), and car offset east of the centre
RD = {'2010@178': 17.3, '2010@181': 15.8, '2010@184': 15.7, '2010@187': 16.35, '2010@175': 16.5, '2011@184': 15.9}
# Kakao stored position of each pano (API roadview-search/v2/node/<2011 node>: street or past[])
def kakao_pos(pano):
    for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api', 'n10172201*.json')):
        st = json.load(open(f))['street_view']['street']
        if not st: continue
        if st['id'] == pano: return g(st['wgsx'], st['wgsy'])
        for p in st.get('past') or []:
            if p['id'] == pano: return g(p['wgsx'], p['wgsy'])
def solve(d, drop=(), rd=None, rd_true=15.1, sd_h=0.7, lm_err=0.7):
    obs = {k: v for k, v in d['obs'].items() if k not in drop}
    def sig(k, p): return math.hypot(math.degrees(1.5 / 783), math.degrees(lm_err / math.dist(p, L[k])))
    def res(q):
        r = [wrap(obs[k] - q[2] - az(q[:2], L[k])) / sig(k, q[:2]) for k in obs]
        if rd is not None: r.append(wrap(q[2] - (rd - rd_true)) / sd_h)
        return np.array(r)
    h0 = np.mean([wrap(obs[k] - az(d['start'], L[k])) for k in obs])
    r = least_squares(res, np.array([*d['start'], h0]))
    C = np.linalg.pinv(r.jac.T @ r.jac)
    dof = len(r.fun) - 3
    return r.x, math.sqrt(EAST @ C[:2, :2] @ EAST), r.fun @ r.fun, dof, {k: r.fun[i] * sig(k, r.x[:2]) for i, k in enumerate(obs)}
print('road centre = resected camera - car offset; + east of the game line (bline); OSM = 백양로 pedestrian way now')
for name in ('2010@178', '2010@181', '2010@184', '2011@184', '2010@187', '2010@175'):
    d = P[name]
    for drop in ((), ('libNE',)):
        if name == '2010@175' and drop: continue
        x, sd, chi2, dof, resid = solve(d, drop, RD[name])
        s, e = s_off(*x[:2]); _, eo = s_off(*x[:2], OSMLINE)
        # leave-one-out over the remaining landmarks
        loo = []
        ks = [k for k in d['obs'] if k not in drop]
        if len(ks) >= 4:
            for k in ks:
                x2, *_ = solve(d, drop + (k,), RD[name]); loo.append(s_off(*x2[:2])[1] - d['car'])
        kp = kakao_pos(d['pano'])
        lat = (x[:2] - np.array(kp)) @ EAST if kp is not None else float('nan')
        print('%s %-9s s %3.0f  road %+5.2f ± %.2f (OSM %+5.2f)  chi2 %5.2f/%d  h %+5.2f  LOO %s  | camera %+.2f m east of its Kakao position, car %.2f -> link %+.2f from road centre  | resid %s' % (
            name, ('-' + ','.join(drop)) if drop else 'all', s, e - d['car'], sd, eo - d['car'], chi2, dof, x[2],
            ('%+.2f..%+.2f' % (min(loo), max(loo))) if loo else '-', lat, d['car'], -lat + d['car'],
            ' '.join('%s %+.2f' % kv for kv in resid.items())))
