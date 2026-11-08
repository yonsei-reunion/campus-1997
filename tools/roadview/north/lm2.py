# landmarks for s 260 - 335 m (OSM corners; see ov/ for the skyview checks) and the bearing of a pixel
import math
F3 = 783.0
L = {
    'libSW': (-127.33, -60.21),  # 중앙도서관 SW (way 163525865 v2)
    'libSE': (-85.44, -71.08),   # 중앙도서관 SE (v3)
    'libNE': (-65.91, 3.16),     # 중앙도서관 NE (v6)
    'bySE': (-24.10, 33.19),     # 백양관 SE (way 256933753 v5)
    'uNW': (34.00, -30.25),      # 학생회관 main block NW (way 1444448640 v0)
    'uGN': (10.46, -87.86),      # 학생회관 south block NW (1444448640 v6)
    'uSW': (4.45, -110.95),      # 학생회관 south block SW (240334198 v10)
    'uSE': (34.70, -118.73),     # 학생회관 south block SE (240334198 v11)
    'C14': (16.84, -168.65),     # 백주년기념관 north box N tip (324328422 v14)
    'C13': (-2.81, -183.30),     # 백주년기념관 north box W end, inner corner (v13)
    'C12': (-11.05, -181.26),    # 백주년기념관 hall box NW (v12)
}
def bearing(pan, px, f=F3):
    return math.floor(pan + 1e-9) + math.degrees(math.atan((px - 694) / f))
# test: LMSHIFT="C12:2.9:-1.6,C14:2.1:-4.0" moves landmarks (e.g. to the Kakao base-map footprint of 백주년기념관)
import os as _os
for _t in filter(None, _os.environ.get('LMSHIFT', '').split(',')):
    _k, _dx, _dy = _t.split(':'); L[_k] = (L[_k][0] + float(_dx), L[_k][1] + float(_dy))
