"""종합관 · 외솔관2 · 인문관 둘레의 1997년 땅과 건물 (#189; reference/고증/3.1 「종합관 · 외솔관2 · 인문관: 1997년의 땅과
건물」).  tools/build_campus.py 가 부른다.

    took, info = jonghap97.grade(Hn, X, Y, FIXED, halls, keep, fill)     # 심기가 끝난 뒤, 저장 바로 앞
    jonghap97.OUTLINE · FLOORS · DOORS                                    # 세 건물의 1997년 외곽선 · 바닥 · 층 · 문
    jonghap97.trees_aside(trees, halls)                                   # 포장된 마당 위의 나무를 목록 제자리에서

Frames: campus metres, x east, y north.  (u, v): 종합관's own frame, o OSM's south-west corner of its west wing, u east
along the slab's south face, v north (uv · xy below); 외솔관2 and 인문관 stand square to it in the scans (OSM's 인문관
is 0.85 degrees off).  Every absolute height is above sea level (해발), taken up to the working datum the
ground is laid on (해발 + tilt: tools/datum.py) where it is read, each at its own place (datum.up(x, y, z); the profiles
in (u, v) through xy; a hall's floor at the middle of its frame, as campus.json's `tilt` has it), GRID at its nodes
(GRID_X0, GRID_Y0, GRID_D).

What the game had: the surface model's ground, 8 - 10 m too high round 외솔관2's west end, brought down in #110 to
6 - 9 m too low (it took 외솔관2's lowest corner + 4.5 m for the car park); the three halls on OSM's outlines, their
floors at the lowest corner of that ground.  What the 1997-07-28 scans (six frames, heights frame pair by frame pair,
edges read on each roof's own plane from opposite flight lines) and the 1:5000 survey (2006 · 2024) have:

- 종합관: a slab 63.4 x 22.6 m, its roof's surface at 89.1 m (the parapet 0.9 m over it), four storeys over the yard
  north of it (72.1 m) on an open storey at 68.8 m; across its east end a low block of two storeys (1994's 400평: 19.4
  x 58.3 m with the slab's end, its roof 68.6 m, its floor the road east of it, 60.45 m; a third storey under them
  shows at its south end, where the ground is that much lower).  OSM's outline has the low block 7.6 m too far east
  and 5 m short on the south.
- 외솔관2: two storeys (연혁: 지하 1층 · 지상 1층, 333.65평 = 2 x 551 m2) on the two of the corridor under them, 42.9 x
  12.95 m (556 m2), a low white gabled roof (eaves 76.9 m, ridge 78.0 m); its west end stands 7.5 m over the ground there
  (the 2026 roadview), its south wall 18.7 m over the lane behind 인문관.
- 인문관: 67.7 x 16.3 m with two shallow blocks standing 2.4 m out of its north face (1,186 m2; 연혁 2,171.60평 = 6 x
  1,196 m2; OSM's east 3.8 m are its porch), its roof 82.3 m: six storeys of 4.0 m on the road along its south face
  (58.2 m), not on the ground 2.5 m under it at OSM's south-east corner.
- the 2006 survey's own outlines of the three (수치지형도 layer 4111) lie on these within 1 m once moved (+0.6, -0.8) m
  in (u, v), the T of 종합관 and 인문관's two blocks included.
- the ground: the road east of 종합관 level at 60.45 m (photos; survey spots 60.24 · 60.54 m 해발), falling south to
  53.7 m before 인문관's east end; the paved yard north of the slab 72.1 m to u 30, a terrace at the low block's roof
  (68.6 m) between them and the slab; the road from the yard down to the east road falls 8 m in its first 14 m (the
  photos and the 2006 contours alike), then runs level; the lane behind 인문관 and round its west end under 60 m
  해발 (both surveys' 60 · 65 m contours run along 외솔관2's south wall and wrap 인문관's west end); the wooded hill
  north-west of the halls up to 102 m 해발 (the game had 87 m).

GRID: the 2006 survey's surface (its contours with its spot heights, 2.5 m) + T at the game's 5 m nodes, for the
woods (HILL) and the slope south-east of the halls (SE), where no photo sees the ground or the photos agree with it
(the roads east of 인문관 within 0.5 m).  ZONES · STRIPS: the levels and profiles read from the photos.
Nothing here draws from build_campus.py's `rng`.
"""
import numpy as np
import datum
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

O = np.array([-88.69, 298.1])            # 종합관's frame: OSM 246156123's south-west corner (the west wing's)
TU = np.array([0.9662, -0.2580])         # ... u, along the slab's south face (east)
TV = np.array([0.2580, 0.9662])          # ... v (north)


def xy(u, v):
    return tuple(float(c) for c in O + TU * u + TV * v)


def uv(x, y):
    """(u, v) of campus points; arrays too"""
    x, y = np.asarray(x, float) - O[0], np.asarray(y, float) - O[1]
    return x * TU[0] + y * TU[1], x * TV[0] + y * TV[1]


def rect(u0, u1, v0, v1, f=xy):
    return Polygon([f(u0, v0), f(u1, v0), f(u1, v1), f(u0, v1)])


def poly(pts, f=xy):
    return Polygon([f(u, v) for u, v in pts])


# --- the halls as the 1997 scans have them ---------------------------------------------------------------------------
JONGHAP, OESOL2, INMUN = 246156123, 246156114, 246156112        # (OSM ways)
PODIUM = 990080                                                 # 종합관's low east block (1994)
SLAB_UV = (-1.6, 61.8, 0.0, 22.6)
PODIUM_UV = (45.2, 64.6, -17.5, 40.8)
OESOL2_UV = (-4.5, 38.4, -18.25, -5.3)
INMUN_UV = [(-29.3, -42.8), (38.4, -42.8), (38.4, -24.1), (16.8, -24.1), (16.8, -26.5), (-16.4, -26.5), (-16.4, -24.1),
            (-29.3, -24.1)]                                     # (the two blocks out of its north face; no porch)
OUTLINE = {JONGHAP: rect(*SLAB_UV), PODIUM: rect(*PODIUM_UV), OESOL2: rect(*OESOL2_UV), INMUN: poly(INMUN_UV)}
# floors: base (해발, at the middle of the hall's frame), storeys, storey height.  종합관: the open storey (68.81) and four
# over it, the roof's surface 89.1; the low block's two from the east road and one under them at its south end, where
# the ground before 인문관 is a storey lower (its roof 68.7; the photos 0.1 under: clear of the terrace beside it);
# 외솔관2: the corridor's two and its own two, eaves 76.9; 인문관: six from the south road, the roof 82.2
FLOORS = {JONGHAP: dict(base=datum.up(-48.14, 299.15, 68.81), levels=5, fh=4.05),
          PODIUM: dict(base=datum.up(-48.14, 299.15, 56.732, 3), levels=3, fh=3.975),
          OESOL2: dict(base=datum.up(-75.35, 282.35, 60.94), levels=4, fh=4.0),
          INMUN: dict(base=datum.up(-92.78, 264.0, 58.18), levels=6, fh=4.0)}
OESOL2_ROOF = dict(mat='plaster_white', pitch=0.165, over=0.5, gable=True)      # (the ridge 1.15 m over the eaves)
# doors (the place on the wall, generic.porch's options): 종합관 from the yard, on the first storey over the open one;
# the low block from the east road; 외솔관2 at its west end (the storey the ground there reaches); 인문관 in its east
# wall under the porch
DOORS = {JONGHAP: (xy(16.0, 22.6), dict(floor=1)), PODIUM: (xy(64.6, 31.5), {}),
         OESOL2: (xy(-4.5, -11.8), {}), INMUN: (xy(38.4, -34.5), {})}

# --- heights of the ground (해발, each at its own place) -------------------------------------------------------------
Z_EAST = datum.up(-4.0, 310.0, 60.45)         # the road east of 종합관, level
Z_YARD = datum.up(-66.0, 325.0, 72.09)        # the paved yard north of the slab
Z_TERR = datum.up(-46.0, 318.0, 68.5)         # the terrace west of the low block's north wing
Z_ROOF = datum.up(-40.0, 310.0, 68.29)        # under the low block's roof, by the terrace
Z_COURT = datum.up(-52.0, 287.0, 68.81)       # the passage between the slab and 외솔관2, its east
Z_PASS_W = datum.up(-92.0, 294.0, 70.1)       # ... its west mouth, by 외솔관2's north-west corner
Z_OESOL_W = datum.up(-97.0, 287.0, 69.54)     # the ground at 외솔관2's west end
Z_LANE = datum.up(-80.0, 272.0, 58.29)        # the lane behind 인문관 and round its west end
Z_INMUN = datum.up(-92.78, 264.0, 58.18)      # 인문관's floor (its frame's middle): the road along its south face
Z_APRON = datum.up_at(((38.0, 58.02), (46.0, 57.78), (82.0, 53.72)),
                      [(-59.7, 259.3), (-52.0, 257.2), (-17.2, 248.0)])      # (u, z) before 인문관's east end, at v -30
# (v, z) east of the low block's south wing, the east road's heights abreast (at u 67.25, the strip's middle)
Z_SWING_E = datum.up_at(((-17.5, 56.04), (-14.4, 56.43), (-10.4, 57.01), (-6.5, 58.0), (-2.4, 58.58), (1.6, 59.07),
                         (9.5, 60.04), (12.0, 60.58)),
                        [(-28.2, 263.8), (-27.4, 266.8), (-26.4, 270.7), (-25.4, 274.5), (-24.3, 278.4), (-23.3, 282.3),
                         (-21.3, 289.9), (-20.6, 292.3)])
# profiles (x, y, z) along OSM's ways, the photos' heights (the survey's within 0.5 m)
RAMP = datum.up3([(27.0, 38.1, 71.71), (31.0, 39.8, 69.39), (35.0, 41.4, 66.36), (38.1, 42.7, 64.54), (43.8, 43.8, 62.91),
                  (48.0, 43.9, 61.7), (51.0, 43.9, 60.68), (56.0, 44.0, 60.56), (66.0, 44.2, 60.47)], f=xy)     # (u, v, z)
EAST_ROAD = datum.up3([
    (-8.6, 290.7, 60.27), (-9.6, 286.8, 59.99), (-11.2, 279.0, 59.01), (-12.0, 275.1, 58.53), (-12.8, 271.1, 57.94),
    (-13.5, 267.2, 56.96), (-14.3, 263.3, 56.37), (-15.1, 259.4, 55.18), (-15.9, 255.4, 54.1), (-16.7, 251.5, 53.71),
    (-17.6, 247.6, 53.63), (-18.7, 243.8, 53.24), (-19.7, 239.9, 52.96), (-20.5, 236.0, 52.47), (-21.4, 232.1, 52.08)])
SW_ROAD = datum.up3([
    (-88.0, 318.1, 72.22), (-103.6, 307.7, 72.73), (-116.9, 298.8, 72.82), (-123.5, 294.4, 72.26), (-129.8, 289.6, 71.51),
    (-131.0, 285.8, 70.32), (-132.1, 282.0, 69.54), (-133.3, 278.1, 68.85), (-134.4, 274.3, 68.37), (-135.6, 270.5, 67.98),
    (-136.7, 266.6, 67.8), (-137.9, 262.8, 67.62)])
GRID_X0, GRID_Y0, GRID_D = -225.0, 230.0, 5.0     # (the grid's south-west node, spacing: the game's 5 m nodes)
GRID = np.array([[int(v) for v in r.split()] for r in """
6495 7003 7000 6997 7585 7832 8000 8017 8004 7492 6999 7496 7404 7211 6999 6856 6673 6501 6498 5996 6003 5970 5918 5875 5833 5780 5737 5685 5632 5570 5497 5494 5472 5459 5446 5414 5391 5359 5316 5253 5191 5128 5076 5033 5000 4998 4495 4503 4490
7004 7001 6999 7496 7724 8001 7998 8106 8003 7670 7278 6995 7503 7310 7077 6905 6732 6560 6497 6184 6002 5979 5937 5894 5851 5809 5766 5724 5671 5618 5556 5523 5500 5488 5495 5473 5460 5447 5425 5342 5270 5197 5134 5082 5029 4997 4504 4501 4499
7003 7000 7498 7655 7872 8000 7887 7894 7962 7809 7457 7124 7301 7409 7156 6944 6781 6618 6496 6273 6001 5978 5945 5913 5870 5837 5805 5762 5720 5677 5634 5602 5569 5537 5504 5501 5499 5516 5504 5411 5328 5266 5193 5130 5058 4995 4803 4500 4497
7001 7299 7556 7764 8001 7768 7656 7673 7851 7888 7625 7293 7000 7498 7245 7002 6830 6657 6505 6502 5999 5987 5954 5931 5899 5866 5834 5811 5778 5746 5713 5681 5658 5635 5613 5600 5588 5565 5502 5460 5387 5324 5262 5179 5097 5014 5001 4499 4496
7200 7498 7575 7782 7500 7497 7725 7692 7499 7997 7854 7502 6999 7296 7334 7001 6868 6696 6543 6501 5998 5985 5963 5940 5918 5895 5872 5850 5827 5805 5782 5759 5737 5724 5712 5709 5686 5644 5561 5498 5446 5393 5331 5238 5115 5003 4990 4748 4505
7379 7506 7514 7831 7869 7996 8273 8501 7998 7496 8003 7800 7318 6995 7412 7130 6917 6725 6542 6499 5997 5994 5982 5959 5946 5934 5911 5899 5876 5863 5841 5828 5825 5823 5820 5818 5805 5782 5660 5497 5505 5462 5429 5347 5144 4992 4959 4896 4504
7498 7505 7503 8000 8117 8325 8512 8520 8517 8504 7832 7999 7736 7004 7501 7209 6996 6753 6501 6498 5996 6003 5990 5978 5975 5963 5950 5937 5925 5922 5909 5907 5904 5912 5919 5936 5944 6001 5999 5996 5783 5501 5498 5496 5243 4990 4978 4975 5002
7497 7504 8001 8129 8296 8503 8551 8578 8566 8463 8000 7828 7995 7663 7000 7307 7005 6822 6580 6247 6004 6002 5999 5996 5994 5991 5989 5986 5983 5971 5968 5966 5973 6010 5998 6085 6003 6250 6247 6505 6002 5760 5607 5504 5352 4999 4996 4994 5001
7495 7503 8060 8217 8405 8542 8630 8677 8674 8582 8349 7997 7664 8001 7499 7496 7084 6911 6658 6496 6003 6010 6008 6015 6023 6030 6027 6035 6032 6040 6007 6064 6002 6249 6167 6254 6421 6459 6436 6484 6001 5888 5696 5503 5500 5148 4995 4993 5000
7504 8001 8109 8306 8504 8611 8748 8836 8873 8841 8708 8575 8003 7710 7998 7255 7012 7000 6757 6504 6002 6019 6017 6034 6051 6079 6056 6104 6001 6248 6496 6403 6451 6338 6265 6343 6420 6457 6475 6492 6250 5997 5794 5592 5499 5317 5004 5001 4999
7503 8000 8198 8395 8502 8710 8887 9005 8902 8929 8997 8794 8601 7999 7996 7754 7001 6998 6876 6623 6001 6048 5995 6103 6000 6338 6505 6452 6540 6547 6565 6552 6519 6467 6424 6441 6469 6486 6494 6501 6498 5996 5933 5751 5498 5495 5233 5090 4998
7502 8069 8296 8504 8601 8819 8996 8743 8631 8658 8835 9003 8810 8618 8495 8002 7500 6997 7005 7002 6379 6247 6504 6502 6749 6996 6774 6711 6728 6756 6743 6681 6618 6575 6543 6530 6528 6525 6522 6510 6497 6005 6002 5999 5497 5504 5392 5229 5116
7500 8108 8355 8512 8640 8997 8605 8302 8229 8237 8324 8612 8999 8876 8624 8501 7829 7496 7283 7141 6998 6996 7003 7000 6998 6995 6952 6900 6917 7005 7002 6799 6717 6664 6632 6599 6586 6564 6551 6529 6506 6183 6001 5998 5695 5503 5500 5328 5195
7499 8126 8374 8471 8469 8496 8173 8231 8258 8276 8193 8000 8318 8995 8883 8640 8127 7835 7502 7380 7267 7194 7132 7079 7056 7024 7001 6999 6996 6983 6931 6858 6796 6743 6700 6668 6635 6613 6580 6547 6515 6312 5999 5997 6004 5502 5499 5406 5274
7798 8125 8373 8370 7997 8785 8682 8700 8797 8884 8942 8659 8327 8004 8661 8999 8496 8183 7751 7498 7496 7373 7300 7238 7175 7113 7030 6997 6985 6972 6940 6887 6844 6812 6769 6737 6694 6651 6609 6566 6523 6501 5998 6006 6003 5500 5498 5455 5333
7747 8104 8371 8309 7996 8974 9001 9118 9316 9503 9481 9498 9495 8783 8000 7997 9005 8752 8500 7997 7504 7502 7449 7377 7304 7211 7089 6996 6984 6971 6948 6926 6893 6870 6848 6815 6753 6690 6627 6575 6532 6500 5997 6004 6002 5709 5497 5504 5381
7745 8093 8360 8268 8465 9062 9230 9497 9474 9432 9389 9357 9364 9411 9499 8896 8004 8501 8998 8496 8253 8001 7658 7495 7443 7350 7208 7005 6992 6980 6967 6954 6942 6939 6927 6914 6821 6729 6646 6584 6541 6508 5996 6003 6021 5998 5495 5503 5430
7504 8092 8339 8496 8464 9061 9328 9486 9423 9351 9268 9195 9133 9110 9118 9265 9502 9060 8487 8505 8002 8499 7997 7844 7631 7499 7376 7154 7001 6988 6986 6983 6991 6998 6995 6993 6890 6748 6645 6572 6530 6507 6255 6002 6009 5997 5644 5501 5449
7503 7990 8268 8495 8252 9000 9317 9475 9382 9269 9137 9004 8882 8769 8646 8504 8501 9499 9496 8763 9001 8498 8335 8163 8000 7748 7495 7502 7000 6997 7005 7032 7019 6997 7004 7002 6909 6716 6604 6541 6488 6506 6503 6001 5998 5995 5623 5500 5458
7512 7999 8196 8414 8001 8999 9196 9503 9371 9208 9016 8813 8620 8498 9015 9052 8950 8847 9155 9502 8499 8497 9004 8622 8499 7996 7874 7661 7499 7366 7273 7191 7078 6996 7003 7000 6998 6595 6512 6500 6247 6005 6002 5999 5957 5804 5502 5499 5476
7500 7798 8095 8253 8250 8697 9005 9502 9400 9167 8884 8612 8499 9976 10004 9781 9529 9306 9253 9361 9498 9106 8923 8750 8498 8495 8333 8000 7797 7615 7502 7400 7177 7004 7002 6789 6496 6504 6381 5999 5996 6003 6001 5998 5916 5763 5560 5498 5495
7499 7497 8004 8111 8209 8516 9004 9251 9498 9176 8763 8500 9298 9935 9663 9650 9997 9555 9162 9180 9287 9504 9262 9099 8997 8504 8461 8499 7996 7893 7691 7498 7496 7193 7000 6498 6495 6453 6290 6067 6005 6002 6000 5997 5934 5772 5599 5496 5504
7408 7495 7863 8030 8057 8255 8772 9000 9497 9274 8772 8709 9267 10004 9001 8999 9266 9684 10001 8998 8996 9003 9501 9298 9135 9003 8500 8497 8505 8142 8000 7797 7504 7502 6999 6617 6504 6401 6269 6096 6004 6001 5998 5996 5953 5820 5648 5495 5503
7327 7504 7671 7999 8006 8004 8621 8998 9286 9503 8841 8708 9045 9003 9460 9398 9475 9652 9870 9997 9534 9212 8999 9427 9254 9101 8999 8496 8504 8351 8118 7996 7793 7501 6998 6655 6503 6410 6278 6135 6002 6000 5997 6004 6002 5889 5727 5504 5501
7245 7423 7500 7798 7995 8002 8250 8707 8995 9312 8499 8787 8974 9342 9999 9646 9544 9551 9498 9746 10003 9511 9128 9495 9323 9160 8998 8505 8522 8500 8247 8055 8002 7499 6997 6754 6501 6449 6316 6164 6001 5998 5996 6003 6001 5998 5885 5593 5500
7174 7352 7499 7646 7914 8001 7999 8336 8683 8921 8998 9256 9033 9370 9998 9685 9502 9550 9567 9525 10002 9739 9267 9254 9392 9209 9046 8754 8571 8499 8326 8103 8001 7608 7495 7003 6500 6498 6365 6192 6000 5997 6005 6002 5999 5997 6004 5672 5499
7093 7270 7438 7495 7783 8000 7997 8005 8462 8809 8497 9504 9002 9429 9996 9504 9571 9759 9766 9593 9501 9998 9446 9003 9440 9248 9035 8752 8560 8517 8385 8122 7999 7657 7504 7002 6709 6496 6414 6241 6059 5996 6003 6001 5998 5996 6003 5720 5498
7062 7199 7357 7504 7651 7909 7996 8003 8291 8818 8746 9133 9000 9378 9685 9503 9650 9817 9825 9642 9500 9997 9574 9002 9499 9276 9094 9001 8509 8506 8503 8101 7998 7666 7503 7000 6998 6615 6503 6290 6097 6005 6002 6000 5997 6004 5902 5719 5496
7000 7118 7265 7433 7500 7777 8005 8002 8150 8587 9004 8992 9249 9397 9524 9571 9669 9746 9744 9651 9538 9816 9703 9160 9498 9275 9113 9000 8497 8505 8502 8000 7997 7664 7502 6999 6997 6734 6501 6349 6156 6003 6001 5998 5996 6003 5910 5748 5575
6999 6997 7134 7341 7499 7646 7904 8001 7998 8376 8623 8921 9168 9475 9493 9570 9677 9745 9742 9690 9577 9734 9762 9299 9337 9204 9091 8999 8496 8504 8501 7998 7996 7663 7501 7108 6995 6773 6500 6407 6215 6002 6000 5997 6004 6002 5929 5777 5604
6888 6965 7063 7250 7438 7505 7742 8000 7997 8295 8482 8999 9177 9494 9491 9589 9756 9804 9811 9778 9706 9503 9781 9518 9245 9103 9050 8998 8505 8502 8500 7997 8004 7662 7499 7157 7004 7001 6499 6456 6304 6001 5998 5996 6003 6001 5938 5825 5673
6767 6894 7002 7159 7346 7504 7501 7998 7996 8243 8501 8798 9125 9353 9450 9618 9995 9922 9900 9897 9935 9832 9629 9497 9174 9022 9019 8996 8504 8501 8388 7996 8003 7671 7498 7155 7003 7000 6778 6505 6502 6500 5997 6005 6002 5999 5967 5894 5781
6696 6853 6970 7068 7245 7432 7500 7747 8005 8172 8499 8497 9004 9182 9379 9566 9784 10001 9969 9976 10003 9611 9508 9496 9163 9000 9008 8845 8502 8500 8347 8005 8002 7669 7397 7134 7002 6999 6886 6504 6501 6499 5996 6003 6001 5998 5995 6003 6000
6604 6832 6999 6996 7144 7361 7479 7496 8003 8131 8378 8496 9003 9000 9258 9495 9593 9760 9857 9855 9742 9579 9497 9344 9142 8999 8996 8784 8501 8499 8356 8103 8001 7668 7396 7143 7000 6998 6995 6622 6500 6497 6505 6162 6039 5997 6004 6002 5999
6503 6700 6898 6995 7133 7370 7487 7505 7762 8070 8307 8504 8802 8999 9107 9374 9501 9569 9636 9643 9581 9498 9406 9263 9120 8998 8915 8733 8550 8497 8335 8122 8000 7667 7504 7162 6999 6996 7004 6751 6499 6496 6503 6311 6128 5996 6003 6000 5998
6502 6589 6867 7004 7131 7359 7496 7504 7501 7998 8236 8503 8620 8998 8995 9133 9500 9497 9505 9522 9500 9417 9294 9172 9059 8997 8854 8711 8569 8496 8314 8141 7998 7686 7503 7170 6998 6995 7003 6880 6497 6505 6502 6440 6297 6094 6002 5999 5997
6501 6588 6855 7003 7100 7268 7435 7502 7500 7997 8134 8402 8499 8727 9004 9001 9119 9276 9344 9351 9298 9236 9163 9081 8998 8955 8813 8680 8557 8455 8292 8120 7997 7744 7502 7199 6997 7004 7001 6999 6696 6504 6501 6498 6496 6273 6001 5998 5995
6499 6667 6854 7002 6999 7196 7334 7501 7468 7496 8003 8231 8498 8495 8643 8870 8998 9005 9072 9110 9097 9075 9042 8999 8997 8894 8751 8629 8526 8424 8261 8088 7996 7783 7501 7248 6995 7003 7000 6998 6825 6502 6500 6497 6504 6502 6169 5997 6004
6498 6705 6903 7000 7038 7135 7242 7340 7397 7445 7502 7999 8247 8504 8502 8599 8716 8834 8881 8908 8996 9003 9001 8998 8885 8773 8660 8568 8495 8412 8250 8077 8005 7832 7499 7317 7004 7002 6999 6996 6894 6681 6548 6496 6503 6501 6318 5995 6003
6497 6764 7002 6999 6996 7074 7161 7239 7316 7383 7461 7498 7996 8203 8340 8448 8495 8572 8640 8707 8765 8782 8789 8767 8704 8632 8559 8496 8504 8411 8229 8066 8003 7831 7498 7496 7003 7000 6998 6995 7002 6800 6637 6505 6502 6499 6497 6124 6002
6496 6883 7000 6998 6995 7003 7080 7157 7245 7322 7400 7467 7504 8002 8189 8316 8424 8491 8499 8496 8573 8591 8588 8586 8553 8500 8498 8495 8503 8400 8197 8005 8002 7829 7497 7504 7192 6999 6996 7004 7001 6869 6736 6593 6501 6498 6496 6303 6000
7004 7002 6999 6997 7004 7001 6999 7086 7163 7251 7338 7416 7473 7500 8068 8205 8373 8500 8497 8495 8502 8500 8497 8504 8502 8499 8497 8504 8501 8379 8156 8003 8001 7828 7496 7503 7360 7158 6995 7003 7000 6947 6855 6722 6500 6497 6504 6502 5999
7003 7001 6998 6995 7003 7000 6997 7005 7092 7190 7277 7364 7442 7489 7997 8074 8231 8399 8496 8504 8501 8498 8496 8503 8500 8498 8495 8503 8500 8317 8075 8002 8000 7827 7504 7502 7419 7267 7124 7001 6999 6996 7004 6921 6768 6656 6503 6500 6498
""".strip().splitlines()], float) / 100.0
# (centimetres above sea level; up to the working datum, to the decimetre it was first written in: tools/datum.py)
GRID = np.round(GRID + datum.tilt(*np.meshgrid(GRID_X0 + GRID_D * np.arange(GRID.shape[1]),
                                               GRID_Y0 + GRID_D * np.arange(GRID.shape[0]))), 1)
# ---------------------------------------------------------------------------------------------------------------------
# where GRID is laid.  HILL: the woods north-west and west of the halls (the game 5 - 16 m under the survey), short of
# 연희동's houses west of x -205 and north of y 400 there, of 제2인문관's building site east of x -62 and of the ground
# south of y 262; SE: the slope east of 인문관 down to y 235 (tools/kwangbok97.py has y <= 230), short of 스팀슨관's back.
# The drive behind 스팀슨관 (the first traffic line's levelled nodes, FIXED; no car takes it since the outer roads)
# stood 2 - 3.5 m under the survey and the photos south of y 255: it goes up with SE
HILL = Polygon([(-205.0, 275.0), (-160.0, 262.0), (-128.0, 262.0), (-128.0, 283.0), (-100.0, 290.0), (-100.0, 318.0),
                (-85.0, 330.0), (-62.0, 338.0), (-62.0, 425.0), (-150.0, 425.0), (-150.0, 400.0), (-205.0, 400.0)])
SE = Polygon([(-62.0, 233.0), (2.0, 233.0), (2.0, 243.0), (6.0, 247.0), (6.0, 262.0), (-2.0, 292.0), (-62.0, 292.0)])
Y_SOUTH = 232.0                   # no node at or south of this (광복관 · 핀슨관 · 한경관 쪽: tools/kwangbok97.py)
RING = 15.0                       # eased out (harmonic) this far round it all
HALL_PAD = 7.1                    # the other halls' feet (their floors read the nodes round their corners)
STRIP_HALF = 3.4


def grid_z(x, y):
    """GRID, bilinear (on the working datum)"""
    from scipy.ndimage import map_coordinates
    x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    z = map_coordinates(GRID, [(y.ravel() - GRID_Y0) / GRID_D, (x.ravel() - GRID_X0) / GRID_D], order=1, mode='nearest')
    return z.reshape(x.shape) if x.ndim else float(z[0])


def _lin(pts):
    """u -> z through (u, z) points"""
    us, zs = zip(*pts)
    return lambda u, v: np.interp(u, us, zs)


def _const(z):
    return lambda u, v: np.full(np.shape(u), z)




def _pass(u, v):
    """the passage between the slab and 외솔관2, and on under the slab's open storey: from its west mouth (the yard's
    level along the slab's end wall, Z_PASS_W along 외솔관2's north wall) down to the court's level 16 m in"""
    a = np.interp(v, [-5.3, 0.0], [Z_PASS_W, Z_YARD])
    return np.where(u < 12.0, a + (Z_COURT + 0.1 - a) * np.clip((u + 4.5) / 16.5, 0, 1),
                    np.interp(u, [12.0, 45.2, 52.0], [Z_COURT + 0.1, Z_COURT, Z_ROOF]))


_apron = _lin(Z_APRON)
# the ground's zones, each (name, outline in (u, v), height(u, v)); a later one over an earlier where they overlap.
# The zones run on under the halls' walls so that the ground is level up to them: the steps between the levels (the
# yard and the open storey, the passage and the lane 11 m under it, the terrace and the east road) fall inside the
# halls' outlines, where the 5 m grid's slopes are not seen.
ZONES = [
    ('west of the slab', poly([(-16.0, -3.0), (-1.6, -3.0), (-1.6, 17.5), (-5.0, 17.5), (-5.0, 24.0), (-16.0, 12.0)]), _const(Z_YARD)),
    ('외솔관2 west end', rect(-16.0, -4.5, -20.5, -3.0),                     # (level along its end wall, up to the yard north of it)
     lambda u, v: np.interp(v, [-5.3, -3.0], [Z_OESOL_W, Z_YARD])),
    ('passage', rect(-4.5, 52.0, -11.0, 17.5), _pass),                      # (under the slab's open storey too)
    ('court', rect(38.4, 52.0, -18.25, 0.0), _const(Z_COURT)),                # (the trees between 외솔관2 and the low block)
    ('yard', poly([(-5.0, 17.5), (30.0, 17.5), (30.0, 40.5), (21.0, 43.5), (10.0, 40.0), (2.5, 31.0), (-5.0, 24.0)]), _const(Z_YARD)),
    ('terrace', rect(35.0, 45.2, 17.5, 40.5), _const(Z_TERR)),
    ('low block, west', rect(45.2, 52.0, -11.0, 40.8), _const(Z_ROOF)),
    ('east road', poly([(58.0, 0.0), (58.0, 40.8), (51.0, 40.8), (51.0, 47.5), (84.0, 47.5), (84.0, 12.0), (64.6, 12.0), (64.6, 0.0)]),
     _const(Z_EAST)),
    ('south wing, east', rect(58.0, 76.5, -17.5, 12.0), lambda u, v: np.interp(v, *zip(*Z_SWING_E))),
    ('apron', rect(44.0, 84.0, -40.0, -19.6), _apron),                      # (before 인문관's east end, falling east)
    ('low block, south', rect(45.2, 64.6, -17.5, -11.0), _apron),
    # (behind 인문관 and round its west end; west of 외솔관2 its north edge 3 m further south, the bank up to the ground
    # at 외솔관2's west end clear of that hall's door)
    ('lane', poly([(-33.5, -46.0), (46.0, -46.0), (46.0, -19.6), (-2.0, -19.6), (-2.0, -23.5), (-33.5, -23.5)]), _const(Z_LANE)),
    ('외솔관2 south', rect(5.0, 34.0, -18.25, -11.0), _const(Z_LANE)),
    ('외솔관2 west end, inside', rect(-4.5, 5.0, -18.25, -11.0), _const(Z_OESOL_W)),   # (its end wall's foot level)
    ('인문관', rect(-29.3, 42.2, -45.5, -24.1), _const(Z_INMUN)),             # (its porch and the low strip along its south too)
    ('인문관 south-west', rect(-33.5, -17.7, -51.0, -42.8), _const(Z_INMUN)),  # (west and east of 인문관 남쪽 길, INM97)
    ('인문관 south-east', rect(31.3, 42.2, -53.0, -42.8), _const(Z_INMUN)),
]
# the yard's paving and the terrace on the game's map (paint); the trees the planting put on them step aside
PAVED = [poly([(-16.0, -3.0), (-1.6, -3.0), (-1.6, 22.6), (30.0, 22.6), (30.0, 40.5), (21.0, 43.5), (10.0, 40.0), (2.5, 31.0),
               (-5.0, 24.0), (-16.0, 12.0)]), rect(35.0, 45.2, 22.6, 40.5)]
# the court between 외솔관2's east end and the low block (trees in the scans) and the bank under its south edge: lawn
# over the paving OSM's outlines had left there
GRASS = [poly([(38.4, 0.0), (45.2, 0.0), (45.2, -17.5), (46.5, -21.5), (36.0, -21.5), (38.4, -18.25)])]


def _strip(Hn, X, Y, pts, half, mask, f=None):
    """the nodes within half m of the polyline pts ((x, y, z), or (u, v, z) with f) and in mask: the profile's height
    abreast of them.  Returns the nodes set."""
    q = [(f(a, b) if f else (a, b)) for a, b, _ in pts]
    ls = LineString(q)
    ss = np.array([ls.project(Point(p)) for p in q])
    zs = np.array([z for _, _, z in pts])
    P = shapely.points(X, Y)
    m = (shapely.distance(ls, P) <= half) & mask
    s = shapely.line_locate_point(ls, P)
    m &= (s > 0.01) & (s < ls.length - 0.01)
    Hn[m] = np.interp(s[m], ss, zs)
    return m


def grade(Hn, X, Y, FIXED, halls, keep, fill, eased=None):
    """GRID in HILL and SE, the zones and the roads' profiles round the three halls, the rest between and RING m round
    them one smooth surface (fill: harmonic_fill).  halls: the other halls' outlines (their feet stay), keep: nodes
    that stay as they are (인문관 남쪽 길).  #110's levels round 외솔관2 (FIXED there) give way.  Returns the nodes set
    (to be FIXED) and a summary; `eased`, a dict, gets the nodes only eased between (tools/ridge97.py lays the survey
    over those of them on the ridge south of HILL)."""
    H0 = Hn.copy()
    north = Y > Y_SOUTH
    stay = keep | shapely.contains_xy(unary_union([h.buffer(HALL_PAD) for h in halls]), X, Y) | ~north
    block = unary_union([p for _, p, _ in ZONES] + list(OUTLINE.values())).buffer(6.0)
    region = unary_union([block, HILL, SE])
    in_block = shapely.contains_xy(block, X, Y)
    # (FIXED nodes that give way: #110's levels round 외솔관2, the old drive's in SE)
    mine = (shapely.contains_xy(region.buffer(RING), X, Y) & (Y >= 262.0) & (X <= 3.0)) | (shapely.contains_xy(SE, X, Y) & north)
    _uf = FIXED & mine & ~stay
    info = dict(unfixed=(int(_uf.sum()), float(X[_uf].min()), float(X[_uf].max()), float(Y[_uf].min()), float(Y[_uf].max())))
    fixed = FIXED & ~mine
    took = np.zeros(X.shape, bool)
    # the survey's surface (not between the zones round the halls, where its contours run through the halls: those
    # nodes are eased between the zones below)
    base = (shapely.contains_xy(HILL, X, Y) | shapely.contains_xy(SE, X, Y)) & ~in_block & ~stay & ~fixed
    Hn[base] = grid_z(X, Y)[base]
    took |= base
    info['survey'] = (int(base.sum()), round(float((Hn - H0)[base].min()), 1), round(float((Hn - H0)[base].max()), 1))
    # the road down from the yard (the terrace and the low block's foot beside it: the levels below, over it)
    can = ~stay & ~fixed
    road = _strip(Hn, X, Y, RAMP, STRIP_HALF, can, f=xy)
    # the levels
    U, V = uv(X, Y)
    zoned = np.zeros(X.shape, bool)
    for name, p, zf in ZONES:
        m = shapely.contains_xy(p, X, Y) & can
        Hn[m] = zf(U[m], V[m])
        zoned |= m
    # the roads east of the low block and up the hill south-west of the halls, over the levels beside them
    road |= _strip(Hn, X, Y, EAST_ROAD, STRIP_HALF, can)
    road |= _strip(Hn, X, Y, SW_ROAD, STRIP_HALF, can & (Y >= 262.0))
    took |= zoned | road
    info['zones'] = (int(zoned.sum()), int(road.sum()))
    # between them and round it all
    free = (in_block | shapely.contains_xy(region.buffer(RING), X, Y)) & ~took & ~stay & ~fixed
    if free.any():
        fill(free)
    info['eased'] = int(free.sum())
    if eased is not None:
        eased['nodes'] = free
    d = Hn - H0
    info['moved'] = (int((np.abs(d) > 0.05).sum()), round(float(d.min()), 1), round(float(d.max()), 1))
    return took | free, info


def trees_aside(trees, halls, pad=1.5):
    """trees the random planting put on the paved yard and the terrace (the photos have none there) and where the low
    block stands: each moved in its place in the list to the nearest free point pad m outside, clear of the halls by
    2.5 m and of the trees standing there by 3 m.  Returns the moves."""
    moved = []
    hb = unary_union([h.buffer(2.5) for h in halls] + [p.buffer(2.5) for p in OUTLINE.values()])
    clear = unary_union(PAVED + [OUTLINE[PODIUM].buffer(2.0)])
    rings = [g.exterior for g in getattr(clear.buffer(pad), 'geoms', [clear.buffer(pad)])]
    spots = [r.interpolate(d) for r in rings for d in np.arange(0.0, r.length, 0.5)]
    spots = [q for q in spots if not hb.contains(q)]
    inside = [t for t in trees if clear.buffer(0.3).contains(Point(t[1], t[2]))]
    near = [Point(t[1], t[2]) for t in trees if not any(t is i for i in inside) and abs(t[1] + 50.0) < 90 and abs(t[2] - 305.0) < 90]
    spots = [q for q in spots if all(q.distance(o) > 3.0 for o in near)]
    for t in inside:
        if not spots:
            break
        q = min(spots, key=lambda q_: q_.distance(Point(t[1], t[2])))
        moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
        t[1], t[2] = round(q.x, 2), round(q.y, 2)
        spots = [s for s in spots if s.distance(q) > 3.5]
    return moved
