# landmarks (OSM corners, checked against the Kakao skyview roofs within ~1 m) and readings
import math
F3 = 783.0
L = {
    'libSE': (-85.44, -71.08),   # 중앙도서관 SE (way 163525865 v3)
    'libNE': (-65.91, 3.16),     # 중앙도서관 NE (v6)
    'uSW': (4.45, -110.95),      # 학생회관 south glass block SW (way 240334198 v10)
    'uNW': (34.00, -30.25),      # 학생회관 main block NW, over the lower north annex (way 1444448640 v0/v11)
    'bySE': (-24.10, 33.19),     # 백양관 SE (way 256933753 v5)
    'C12': (-11.05, -181.26),    # 백주년기념관 hall box NW (way 324328422 v12)
}
def bearing(pan, px, f=F3):
    return math.floor(pan + 1e-9) + math.degrees(math.atan((px - 694) / f))
