"""노천극장 · 음악관 뒤 언덕과 동쪽 찻길 남쪽의 1997년 땅 (#189; reference/고증/3.14_옛_노천극장.md 「땅의 높이」,
3.11 · 2.9).  tools/build_campus.py 가 부른다.

    took, info = music97.grade(Hn, X, Y, FIXED, halls, keep, fill, amph, tr_line, tr_n)   # 심기가 끝난 뒤, 저장 바로 앞

Frame: campus metres, x east, y north.  Every absolute height written here is above sea level (해발), taken up to
the working datum the ground is laid on (해발 + tilt: tools/datum.py) where it is read.

- The game's ground round the old 노천극장 and on the wooded hill north of 음악관 was the surface model's, 8 - 13 m under
  the 1997-07-28 scans round the bowl and 20 m on the hilltop (3.14 「남은 한계」).  The 1:5000 survey (국토지리정보원
  수치지형도, surveyed 2006 and 2024: spot heights and 5 m contours) settles it.  The photos' heights stand over the
  survey's by one plane all over the campus (datum.tilt: 107 spot heights, rms 0.35 m, both surveys alike: the photos'
  block took the tilt of the game's roads it was tied to, so the working datum is that plane over the sea).  Here
  photo − (survey + plane) is +0.4 m (median of 445 ground points, rms 1.4), but game − (survey + plane) −6 to −23 m
  round the bowl and on the hill.  So the photos were right.
- GRID: the ground at the game's 5 m nodes (x 115 .. 285, y 30 .. 230, decimetres): the 2006 survey's surface (its contours with
  its spot heights, 2.5 m), nudged to the 1997 photos where they see the ground within 4 m of it (the
  survey is after the 1999 theatre: the photos have the 1997 bowl).  Applied inside REGION, the halls' feet kept,
  eased out round it (harmonic) to the game's ground.
- 노천극장 (AMPH in build_campus.py): its floor (56.3 m; the 1999 theatre's floor, 2006 · 2024 survey
  + plane: 55.8 · 56.4 m) instead of a stage under the walk behind it; the bowl cut into GRID as the first cut was
  into the old ground (the same terraces and easing past the rim; behind the stage 2 m level, then down to the walk
  west of it over 6 m, as the photos have that 4 m under the floor).
- 동쪽 찻길 (TR_E) from 아펜젤러관's yard to the fork east of 한경길 (EAST_Q97 from there): ROAD, the survey's spot
  heights and the contours crossing it.  The photos' across-road profiles here read 1.5 - 3.5 m higher
  (the canopy's edge, as 2.9 「남은 한계」 suspected).  Levelled across as tr_grade does.
- 용재관's drive (YJ_BRANCH, x < 126) is the 대강당 · 용재관 part's (51.2 m at its east end): TM_KEEP stays.
- 음악관 두 동 (halls; 3.11 「두 동의 절대 높이」): the two halls and the ground before them stood 1.5 · 2.25 m under the
  photos and the survey.  HALLS_FRONT: the road along 구관's front and 신관's forecourt at its door, read again on bare
  asphalt with small windows (the first reading, 1.4 m over the survey, had the parked cars' roofs and the hedge in
  it); the survey's spot on the road before 구관 and its 55 m contour along 신관's front agree to 0.45 m.  The whole
  platform is lifted by what it lacks (the shapes on it stay: build_campus.py music_grade), the lift eased to nothing
  at the hill behind (GRID), the car parks south and east (tools/med97.py) and 26 m off; the halls' floors go with it.
  신관's east yard (EAST_YARD) on the photos' own grade: a terrace over the car park east of it.
- 신관 앞마당의 남동쪽 (forecourt_se; 3.11 「신관 앞마당의 남동쪽과 앞 찻길 남쪽의 칸 줄」): south of the level forecourt the asphalt
  fell south-east to the exit road and the row of stalls along the kerb, on the scans' bare asphalt between the cars
  (FORECOURT_SE).  MUSIC_PAVE97: the asphalt there and along 구관's road out to the back of its stalls (painted by
  build_campus.py), so that the row of cars along the kerb stands on it (tools/cars97_new.json).
- Nothing here draws from build_campus.py's `rng`.
"""
# (every absolute height written in this file's code is above sea level, 해발: datum.up · up3 · up_at · up_plane take it
# up to the working datum the ground is laid on, 해발 + tilt, where it is read: tools/datum.py.  The heights quoted
# in the comments are 해발 too)
import math

import numpy as np
import datum
import shapely
from shapely.geometry import LineString, Point, Polygon
import shapely.ops
from shapely.ops import unary_union

# --- heights, 해발 (each taken up to the working datum at its place) -----------------------------------------------
AMPH_FLOOR = datum.up(154.0, 160.0, 56.35)                 # 노천극장's floor (the 1997 scans)
ROAD = datum.up3([(69.1, 146.2, 42.12),      # (x, y, height) on TR_E: 아펜젤러관's yard (the square's level, kept)
        (86.0, 164.6, 44.99),      # 2006 contour 45 m, 0.9 m off the road's middle
        (126.1, 211.5, 51.37),     # 2024 spot 51.34 m on the road
        (132.6, 222.4, 50.7),     # (between it and the 50 m contour 6.9 m off at (128.8, 231.1))
        (141.5, 251.0, 49.99),     # 2005/2006 contour 50 m, 3 m off
        (149.7, 262.8, 49.11)])     # EAST_Q97's first photo height (the fork), as it was
# 음악관: (x, y, height) of the ground before each hall: the road along 구관's front (the photos 해발 55.3 m: 60 points
# S -8 .. 60 m along it, 5 - 6 frame pairs each; the survey's spot (177.0, -31.1) 54.87 m), 신관's forecourt at its door
# (the photos 해발 54.95 m by the stalls east of the door; the survey's 55 m contour runs along the front there)
HALLS_FRONT = datum.up3([(170.0, -25.0, 55.3), (250.0, -31.0, 54.95)])
HALLS_EASE = 26.0                 # the lift fades out this far round the platform
# the paved yard along 신관's east wall (two columns of stalls in the photos), rising north on one grade: (x, y, height)
# at its south and north ends (the photos 해발 55.0 -> 56.3 m, 60 points with five or six frame pairs; it stands 2.4 m
# over the car park east of it at its south end, level with it at its north end), and its outline
EAST_YARD = datum.up3([(276.0, -26.0, 55.0), (276.0, 22.0, 56.34)])
EAST_YARD_POLY = Polygon([(262.5, -31.0), (283.5, -31.0), (283.5, 23.5), (271.5, 23.5), (270.5, 14.5), (263.5, -15.0)])
# 신관 앞마당의 남동쪽 (3.11 「신관 앞마당의 남동쪽과 앞 찻길 남쪽의 칸 줄」): south of 신관's level forecourt the asphalt fell
# south-east to the exit road and the row of stalls along the south kerb, on the 1997 scans' bare asphalt between the cars
# (126 points, 1.25 m windows, three or more frame pairs within 0.35 m; a smooth surface through them, cross-validated
# 0.15 m).  The game's grid had the forecourt level 5 m further south and then dropped 2.5 m in 10 m under the row's
# east end.  (x, y, height) of the game's 5 m nodes inside FORECOURT_SE_ZONE
FORECOURT_SE = datum.up3([
    (210.0, -40.0, 55.24), (215.0, -40.0, 55.17), (220.0, -40.0, 54.95), (225.0, -40.0, 54.57), (230.0, -40.0, 54.35),
    (235.0, -40.0, 54.23), (240.0, -40.0, 53.96), (245.0, -40.0, 54.14),
    (210.0, -45.0, 55.23), (215.0, -45.0, 55.00), (220.0, -45.0, 54.61), (225.0, -45.0, 53.97), (230.0, -45.0, 53.69),
    (235.0, -45.0, 53.38), (240.0, -45.0, 53.24), (245.0, -45.0, 53.33),
    (210.0, -50.0, 55.08), (215.0, -50.0, 54.84), (220.0, -50.0, 54.31), (225.0, -50.0, 53.65), (230.0, -50.0, 53.25),
    (235.0, -50.0, 52.86), (240.0, -50.0, 52.45), (245.0, -50.0, 52.32),
    (225.0, -55.0, 53.43), (230.0, -55.0, 52.99), (235.0, -55.0, 52.55), (240.0, -55.0, 51.94)])
FORECOURT_SE_ZONE = Polygon([(205, -37.5), (232, -36.5), (246, -37.5), (246, -49), (242, -57.5), (232, -57.5), (220, -54), (205, -49)])
FORECOURT_SE_RING = 8.0
# the asphalt in 1997 (the scans): the road along 구관's front out to the back of its row of stalls (white lines, nose to
# the kerb), and south of 신관's lawn bed the forecourt out to the kerb behind the row of cars along it
MUSIC_PAVE97 = Polygon([(226.5, -34.6), (231.0, -31.5), (233.0, -28.3), (243.0, -28.3), (243.0, -40.0), (236.0, -45.0),
                        (234.8, -46.2), (232.7, -55.7), (223.4, -53.1), (210.5, -47.6), (190.3, -41.2), (185.8, -39.4),
                        (150.4, -30.1), (145.6, -28.6), (148.0, -19.2), (152.8, -20.7), (188.2, -30.0), (192.8, -31.8),
                        (201.7, -34.6)])
# 신관 앞마당의 섬과 동쪽 칸 줄 (3.11 「섬과 동쪽 칸 줄의 땅, 칸 선」; #152): the scans' white stall lines stand at their own
# height where the two courses see them alike (a line's place across itself moves 0.7 m per metre of height between
# course 26 and course 27; lines running north - south read it best).  The island's north row 54.55 m (its dividers
# 54.53 - 54.60, the bare asphalt of its two empty stalls 54.53 - 54.61 by window), the row east of it 54.6 m (its
# aisle line in four pieces 54.58 - 54.77), the row east of 신관's door 54.95 m (dividers 54.90 - 54.99: the forecourt's
# level, as it stands).  The game had the two rows on the lawn's slope, 0.6 - 1.9 m under them (the cars would lean
# 11 - 14 deg).  (x, y, height) of the game's 5 m nodes under the cars' wheels and the asphalt between the rows: level;
# the island's west end (its shrubs, the fan's band west of them on the forecourt's fall: kept) a little lower, as the
# row's cars' roofs there read; behind the north row the island's shrubs and east of the east row the tree strip take
# the fall to the exit road and to the car park east (2.4 m there, 3.11) in one cell: their ground does not show
ISLAND97 = datum.up3([
    (245.0, -45.0, 54.3),
    (250.0, -40.0, 54.6), (255.0, -40.0, 54.6), (260.0, -40.0, 54.6), (265.0, -40.0, 54.6),
    (250.0, -45.0, 54.5), (255.0, -45.0, 54.55), (260.0, -45.0, 54.55), (265.0, -45.0, 54.55),
    (250.0, -50.0, 54.3), (255.0, -50.0, 54.4), (260.0, -50.0, 54.4), (265.0, -50.0, 54.4),
    (270.0, -35.0, 54.6), (275.0, -35.0, 54.6), (270.0, -40.0, 54.6), (275.0, -40.0, 54.6),
    (270.0, -45.0, 54.6), (275.0, -45.0, 54.6), (270.0, -50.0, 54.45), (275.0, -50.0, 54.45)])
# the asphalt in 1997 (the scans) where the game had lawn: the island's north row, the gap east of it and the east row
# (one piece); the band round the island's west end (a white arc and short white ticks 1.1 m apart: not car stalls);
# the row east of 신관's door (its stalls empty on 28 July; the shrubs in them go: STALLS_DOOR_E)
PAVE97_ISLAND = [
    Polygon([(260.71, -42.8), (261.0, -40.0), (268.11, -35.32), (268.38, -34.3), (274.72, -35.95), (271.64, -47.61),
             (267.5, -46.54), (267.4, -47.6), (266.6, -50.2), (262.0, -50.8), (259.94, -49.62), (244.13, -45.58),
             (245.82, -38.99)]),
    Polygon([(242.9, -38.92), (243.26, -42.05), (241.88, -42.65), (241.44, -42.98), (241.2, -43.49), (241.08, -44.03),
             (240.9, -45.64), (241.02, -46.91), (241.38, -47.46), (242.51, -48.44), (241.56, -51.45), (240.38, -50.72),
             (239.26, -49.8), (238.49, -48.79), (238.08, -47.53), (237.84, -46.36), (237.82, -45.18), (238.15, -42.89),
             (238.54, -41.82), (239.15, -40.82), (240.01, -40.11), (241.42, -39.44)]),
    Polygon([(241.2, -33.3), (257.39, -37.58), (259.29, -29.83), (243.1, -25.56)])]
STALLS_DOOR_E = Polygon([(242.21, -30.67), (257.72, -34.77), (258.92, -29.89), (243.41, -25.79)])
GRID_X0, GRID_Y0, GRID_D = 115.0, 30.0, 5.0       # (the grid's south-west node, spacing: the game's 5 m nodes)
GRID = np.array([[int(v) for v in r.split()] for r in """
5047 5135 5472 5590 5567 6104 6272 6429 6246 7004 6911 6759 6606 6503 6961 6998 7506 7503 7510 7498 7005 7003 6500 6487 5925 5762 5659 5667 5734 5842 5869 5916 5934 5951 5909
4826 5043 5281 5458 5516 6113 6350 6248 6995 6853 6690 6497 7505 7502 7000 7327 7474 7552 7539 7517 7504 7001 6709 6506 6143 5841 5708 5726 5863 6000 6068 6075 6073 6030 6017
4695 5012 5180 5397 5504 6132 6339 6497 6894 6701 6499 7496 7214 7001 7218 7446 7613 7730 7738 7645 7513 7010 6927 6665 6512 6310 6237 6244 6332 6599 6627 6624 6481 6249 6056
4504 5001 5128 5386 5503 6181 6498 6995 6813 6590 7498 7215 7002 7230 7427 7554 7812 7989 8007 7884 7671 7519 7046 6924 6711 6508 6486 6563 6631 6718 6725 6643 6630 6477 6085
4502 5000 5127 5395 5832 6059 6467 6744 6771 7169 7316 7004 7201 7408 7586 7753 7961 8168 8115 8043 8010 7668 7535 7052 7030 6877 6845 6852 6879 6907 6894 6771 6639 6626 6074
4501 4859 5116 5343 5501 6098 5995 6783 6880 7498 6995 7142 7390 7567 7745 7922 8039 8057 8044 8022 8009 8006 7514 7381 7218 7146 7073 7001 7008 7015 6973 6830 6678 6585 6532
4510 4857 5095 5302 5499 6127 6004 6982 7029 6996 7004 7281 7499 7706 7903 8001 8068 8116 8143 8150 8118 8035 8022 7510 7507 7405 7282 7089 6997 7004 7012 6869 6686 6524 6511
4719 4896 5003 5271 5498 6126 6003 7010 6998 6915 7123 7400 7607 7885 8002 8080 8157 8234 8302 8369 8376 8254 8081 8039 7516 7503 7501 7298 6996 7003 7000 6938 6765 6583 6500
4927 4965 5012 5260 5497 6124 6002 7009 6997 6984 7161 7499 7796 8003 8051 8158 8266 8373 8470 8578 8605 8443 8290 8107 8045 7512 7500 7497 7224 7002 6999 6996 6864 6721 6619
5046 5024 5021 5248 5496 6123 6001 7018 7165 7013 7170 7497 8005 8002 8100 8237 8394 8542 8539 8567 8614 8631 8459 8286 8104 8041 7508 7506 7353 7100 6998 6995 6953 6820 6717
5065 5042 5020 5247 5504 6122 5999 6997 6834 7001 7169 7496 8004 8001 8118 8306 8573 8601 8558 8545 8623 8640 8638 8455 8232 8090 7857 7504 7432 7249 6997 7004 7001 6899 6796
5074 5021 5018 5256 5503 6121 5998 7005 7003 7070 7168 7505 7802 8000 8077 8335 8602 8619 8557 8514 8561 8629 8636 8644 8411 8198 8046 7793 7501 7408 7215 7003 7000 6968 6865
5022 4980 5007 5255 5502 6119 5997 6954 6502 7289 7196 7454 7661 7889 8006 8023 8581 8518 8465 8473 8530 8608 8635 8632 8540 8317 8065 7932 7709 7497 7504 7162 6999 6996 6934
4931 4969 5006 5243 5501 6108 6006 7003 6500 7508 7515 7532 7650 7827 8035 8012 8029 8177 8324 8492 8609 8636 8634 8631 8609 8416 8203 8011 7898 7656 7503 7500 7248 6995 7002
4900 4967 4995 5232 5480 5997 6364 6692 6779 7026 7264 7541 7779 7856 7943 8041 8018 8016 8203 8580 8618 8635 8633 8620 8597 8495 8302 8110 8007 7884 7632 7499 7496 7254 7141
4899 4966 4984 5211 5468 5956 6123 6620 6588 6835 7173 7260 7277 7775 7752 7920 8037 8014 8052 8659 8647 8644 8641 8629 8586 8553 8391 8248 8126 8033 7890 7628 7485 7413 7250
4907 4965 4982 5210 5497 5894 6152 6149 6417 6624 6671 7229 7296 7234 7701 7678 7876 8033 8031 8248 8655 8653 8650 8607 8555 8522 8490 8397 8304 8142 8029 7887 7644 7491 7499
4916 4964 4991 5238 5566 5653 6021 6118 6155 6643 6650 6688 7195 7232 7350 7497 7624 7722 8009 8027 8304 8571 8559 8526 8514 8511 8558 8486 8393 8291 8128 8015 8003 7660 7498
4915 4972 4990 5257 5585 5732 5869 6127 6164 6502 6619 6626 6634 7141 7188 7186 7123 7571 7668 7875 8013 8390 8508 8505 8502 8510 8537 8545 8442 8359 8227 8084 8011 7889 7606
4924 4971 4989 5256 5563 5691 5698 6186 6163 6310 6438 6585 6582 6600 6877 7135 7122 7239 7557 7534 8012 8259 8506 8504 8501 8499 8516 8553 8541 8428 8315 8173 8050 8008 7795
4933 4990 5007 5265 5542 5629 5657 6144 6122 6109 6226 6354 6481 6579 6586 6773 7101 7088 7286 7543 7740 8168 8555 8532 8510 8507 8505 8522 8569 8497 8364 8222 8089 8016 7914
4961 5039 5086 5283 5521 5558 5566 5933 6050 6058 6065 6073 6230 6577 6575 6582 6800 7077 7174 7542 7549 8106 8394 8591 8529 8506 8503 8511 8528 8476 8333 8200 8088 8025 8003
5000 5037 5135 5322 5490 5497 5584 5732 5829 5897 5984 6021 6059 6076 6584 6591 6598 6936 7063 7400 7558 7845 8133 8590 8507 8495 8502 8500 8507 8394 8232 8129 8067 8024 8001
5039 5026 5194 5391 5478 5526 5583 5651 5708 5755 5823 5920 6007 6055 6342 6610 6617 6814 7072 7349 7557 7574 8061 8199 8436 8474 8491 8498 8356 8173 8091 8048 8025 8013 8000
5018 5065 5222 5440 5487 5545 5582 5619 5637 5664 5711 5809 5946 6024 6081 6608 6616 6773 7071 7298 7555 7583 8050 8048 8115 8222 8240 8187 8004 8002 7999 7997 8004 8001 7999
5006 5074 5221 5438 5496 5553 5591 5608 5605 5603 5650 5738 5875 5992 6060 6587 6595 6752 7049 7277 7564 7592 7889 8046 8054 8071 8058 7996 8003 8001 7998 7995 8003 8000 7998
5015 5052 5220 5437 5495 5552 5589 5607 5584 5422 5609 5716 5854 5991 6049 6566 6573 6741 7048 7216 7553 7590 7748 7975 8062 8050 8017 8005 8002 7889 7797 7684 7672 7669 7656
5044 5011 5209 5446 5483 5551 5598 5616 5613 5600 5648 5745 5873 5990 6047 6555 6562 6719 7037 7184 7542 7569 7646 7784 7881 7919 7846 7753 7661 7498 7496 7503 7500 7498 7495
5083 5050 5197 5455 5432 5550 5617 5654 5662 5679 5717 5814 5941 5999 6226 6543 6551 6708 6946 7143 7370 7568 7585 7633 7670 7647 7525 7502 7380 7337 7274 7252 7259 7266 7324
5161 5129 5336 5474 5431 5598 5706 5753 5760 5798 5865 5943 6000 6007 6385 6542 6540 6747 7014 7112 7279 7417 7474 7471 7449 7416 7304 7181 7118 6996 7003 7000 6998 6995 7083
5210 5188 5615 5562 5610 5737 5884 5962 5949 5987 6034 6051 6039 6526 6544 6551 6628 6826 6993 7081 7198 7265 7283 7260 7197 7135 7042 7010 6997 7004 7002 6949 6947 6954 7001
5259 5506 5654 5681 5768 5916 6033 6081 6108 6105 6103 6080 6548 6535 6552 6550 6757 6975 6982 7049 7117 7134 7081 7069 7046 6974 6941 6918 6876 6843 6831 6828 6835 6863 6900
5278 5395 5662 5750 5877 6025 6072 6149 6187 6214 6282 6429 6546 6544 6551 6708 6886 6963 6991 7038 7065 7063 7010 6958 6875 6812 6760 6727 6695 6672 6669 6677 6704 6752 6799
5246 5474 5601 5769 6016 6033 6111 6208 6276 6333 6410 6538 6545 6552 6690 6837 6975 6982 7009 7047 7064 7002 6899 6806 6724 6651 6579 6516 6503 6491 6488 6496 6563 6630 6698
5135 5133 5580 5717 6005 6022 6130 6237 6344 6442 6529 6546 6594 6681 6799 7036 7013 7031 7048 7026 6963 6870 6768 6675 6593 6510 6517 6515 6492 6479 6467 6474 6502 6509 6606
5044 5201 5469 5516 5853 6021 6128 6246 6403 6520 6538 6575 6643 6720 6817 6945 6972 6990 6987 6914 6842 6759 6637 6524 6511 6509 6506 6493 6471 6438 6426 6463 6510 6528 6525
4973 5080 5307 5495 5612 6010 6087 6204 6392 6519 6537 6564 6631 6699 6766 6814 6851 6868 6856 6813 6720 6588 6515 6503 6480 6457 6435 6432 6420 6417 6414 6452 6509 6517 6524
4671 4999 5166 5334 5451 5658 6006 6103 6261 6408 6475 6553 6590 6638 6675 6682 6740 6767 6714 6672 6559 6517 6464 6411 6379 6366 6364 6371 6378 6386 6403 6431 6478 6495 6503
4500 4878 5055 5192 5280 5337 5645 6012 6069 6217 6294 6372 6479 6626 6674 6691 6668 6646 6613 6561 6448 6375 6323 6290 6268 6275 6282 6300 6327 6345 6362 6389 6437 6474 6481
4499 4806 4984 5061 5089 5226 5313 5461 6068 6105 6143 6180 6278 6395 6462 6450 6537 6525 6362 6289 6227 6194 6162 6149 6146 6154 6201 6238 6276 6303 6321 6348 6405 6463 6460
4588 4845 4983 4940 5007 5145 5332 5449 5767 5954 6002 6039 6026 6114 6161 6159 6106 6003 6001 5998 5996 6003 6000 5998 5995 6002 6120 6177 6225 6272 6309 6337 6374 6432 6469
""".strip().splitlines()], float) / 100.0
# (centimetres above sea level; up to the working datum, to the decimetre it was first written in: tools/datum.py)
GRID = np.round(GRID + datum.tilt(*np.meshgrid(GRID_X0 + GRID_D * np.arange(GRID.shape[1]),
                                               GRID_Y0 + GRID_D * np.arange(GRID.shape[0]))), 1)
# --------------------------------------------------------------------------------------------------------------------
# where GRID is laid: the hill round the bowl, the walk west of 음악관 구관 north of its corner, short of 용재관 (its
# drive, YJ_BRANCH, is the 대강당 · 용재관 part's), of the fork east of 한경길 and of 어린이생활지도연구원
REGION = Polygon([(117.0, 35.0), (205.0, 35.0), (205.0, 40.0), (272.0, 40.0), (285.0, 55.0), (285.0, 150.0), (270.0, 212.0),
                  (225.0, 226.0), (160.0, 226.0), (138.0, 224.0), (126.0, 205.0), (126.0, 172.0), (130.0, 140.0), (117.0, 100.0)])
TM_KEEP = Polygon([(60.0, 100.0), (126.0, 100.0), (126.0, 180.0), (60.0, 180.0)])   # (용재관 and its drive: tm)
RING = 18.0                       # eased out (harmonic) this far round REGION
ROAD_RING = 13.0                  # ... and round the road, as tr_grade
HALL_PAD = 7.1                    # the halls' feet (the late halls' floors read the nodes round their corners)
ROAD_PAD = 1.5                    # (the road takes its nodes this close to a wall, as tr_grade)
ROAD_HALF = 3.3


def grid_z(x, y):
    """GRID, bilinear (game datum)"""
    from scipy.ndimage import map_coordinates
    x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    z = map_coordinates(GRID, [(y.ravel() - GRID_Y0) / GRID_D, (x.ravel() - GRID_X0) / GRID_D], order=1, mode='nearest')
    return z.reshape(x.shape) if x.ndim else float(z[0])


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def bowl(A, x, y, ground):
    """The old 노천극장 cut into `ground` (heights at x, y) as build_campus.py first cut it (the same terraces, the
    easing past the rim and behind the stage), its floor A['arena_h'].  Returns the heights and the weight left to the
    ground (1: untouched)."""
    c, s = math.cos(A['rot']), math.sin(A['rot'])
    dx, dy = x - A['cx'], y - A['cy']
    u, v = dx * c + dy * s, -dx * s + dy * c
    rx, ry = A['arena_rx'], A['arena_ry']
    lo, hi = np.full(u.shape, 0.05 - min(rx, ry)), np.full(u.shape, 400.0)
    for _ in range(40):
        d = (lo + hi) / 2
        out = (u / (rx + d)) ** 2 + (v / (ry + d)) ** 2 > 1
        lo, hi = np.where(out, d, lo), np.where(out, hi, d)
    d = (lo + hi) / 2
    ang = np.degrees(np.abs(np.arctan2(v / (ry + d), u / (rx + d))))
    depth = A['rows'] * A['row_d']
    floor, top, stage = A['arena_h'], A['arena_h'] + A['rows'] * A['row_h'], A['arena_h'] + A['stage_h']
    back = A['stage_u'] - A['stage_d'] - 2.0
    mr = min(rx, ry)
    hgt = floor + np.clip(d, 0.0, depth) / A['row_d'] * A['row_h']
    dip = 0.9 * _smooth(1 - np.abs(d) / 6.0)
    seat = np.where(d <= 0, floor - 0.3 - dip, np.where(d <= depth, hgt - 0.3 - dip, top - 0.05))
    opn = np.where(u > A['stage_u'] - 2.5, floor - np.where(d <= 0, 0.3 + dip, 0.1), stage - 0.12)
    off = np.radians(ang - A['seat_end']) * (mr + np.maximum(d, 0.0))
    opn = np.where(d > 0, np.maximum(opn, hgt - 0.3 - dip - 0.6 * np.maximum(off - 1.8, 0.0)), opn)
    h = np.where(ang <= A['seat_end'], seat, opn)
    t = _smooth((d - depth - 3.0) / 14.0)
    t = np.where(ang > A['seat_end'], np.maximum(t, _smooth((back - u) / 6.0)), t)
    t = np.where(np.hypot(u, v) > 95, 1.0, t)
    return h * (1 - t) + ground * t, t


def grade(Hn, X, Y, FIXED, halls, keep, fill, A, tr_pts, tr_n, step=5.0, half=800.0):
    """GRID inside REGION (FIXED there yields, but the halls' feet and `keep` stay), the bowl cut into it on the
    photos' floor (A: AMPH, its arena_h set here), TR_E on ROAD level across; then eased out round them (fill:
    harmonic_fill) over nodes no other rule set.  Returns the nodes set (to be FIXED) and a summary."""
    H0 = Hn.copy()
    near_hall = shapely.contains_xy(unary_union([h.buffer(HALL_PAD) for h in halls]), X, Y)
    near_wall = shapely.contains_xy(unary_union([h.buffer(ROAD_PAD) for h in halls]), X, Y)
    stay = near_hall | keep | shapely.contains_xy(TM_KEEP, X, Y)
    took = np.zeros(X.shape, bool)
    info = dict(floor=(A['arena_h'], AMPH_FLOOR))
    # the road: its nodes (the cells its wheels cross) on ROAD, level across
    ls = LineString([tuple(q) for q in tr_pts])
    qs = np.array([ls.project(Point(x, y)) for x, y, _ in ROAD])
    zs = np.array([z for _, _, z in ROAD])
    k0 = int(np.argmin([np.hypot(*(np.array(q) - ROAD[0][:2])) for q in tr_pts]))
    k1 = int(np.argmin([np.hypot(*(np.array(q) - ROAD[-1][:2])) for q in tr_pts]))
    cells = set()
    for k in range(k0, k1 + 1):
        for o in np.arange(-4.0, 4.01, 0.8):        # (both lanes and their wheels, TR_EO + 0.72)
            x, y = np.array(tr_pts[k]) + np.array(tr_n[k]) * o
            cells.add((int(math.floor((y + half) / step)), int(math.floor((x + half) / step))))
    road = np.zeros(X.shape, bool)
    for j, i in {(j + a, i + b) for j, i in cells for a in (0, 1) for b in (0, 1)}:
        s = ls.project(Point(X[j, i], Y[j, i]))
        if near_wall[j, i] or s <= qs[0] + 0.5 or s >= qs[-1] - 0.5:
            continue
        Hn[j, i] = float(np.interp(s, qs, zs))
        road[j, i] = True
    took |= road
    info['road'] = (int(road.sum()), round(float((Hn - H0)[road].min()), 1), round(float((Hn - H0)[road].max()), 1))
    # the hill
    inr = shapely.contains_xy(REGION, X, Y) & ~stay & ~road
    G = grid_z(X, Y)
    Hn[inr] = G[inr]
    took |= inr
    # the bowl, cut into it
    A['arena_h'] = AMPH_FLOOR
    bz = (np.hypot(X - A['cx'], Y - A['cy']) < 95) & ~stay & ~road & (shapely.contains_xy(REGION.buffer(RING), X, Y))
    hb, tb = bowl(A, X[bz], Y[bz], Hn[bz])
    cut = tb < 0.999
    jj, ii = np.nonzero(bz)
    Hn[jj[cut], ii[cut]] = hb[cut]
    took[jj[cut], ii[cut]] = True
    info['bowl'] = int(cut.sum())
    d = (Hn - H0)[inr]
    info['hill'] = (int(inr.sum()), round(float(d.min()), 1), round(float(d.max()), 1))
    # round them
    seg = shapely.ops.substring(ls, qs[0], qs[-1])
    ring = (shapely.contains_xy(REGION.buffer(RING), X, Y) | shapely.contains_xy(seg.buffer(ROAD_RING), X, Y)) \
        & ~took & ~stay & ~FIXED
    ring |= shapely.contains_xy(seg.buffer(6.0), X, Y) & ~took & ~near_hall & ~keep & ~FIXED   # (its verge: not tm's)
    if ring.any():
        fill(ring)
    info['ring'] = int(ring.sum())
    moved = np.abs(Hn - H0)
    info['moved'] = (int((moved > 0.05).sum()), round(float(moved.max()), 1))
    return took | ring, info


def halls(Hn, X, Y, fp_a, fp_b, front_a, front_b, anchors, sample):
    """음악관 두 동과 그 앞 땅을 HALLS_FRONT 의 높이로: the platform (the road, walk and ground build_campus.py's music_grade
    levelled along 구관's front and between the halls, 신관's forecourt, both halls and their feet) lifted by what it
    lacks at HALLS_FRONT (구관's part by the first, 신관's by the second, between the halls from one to the other), the
    lift (not the ground: its shapes stay) eased to nothing, one harmonic surface, at the nodes GRID set, on `anchors`
    (the car parks south and east: polygons) and HALLS_EASE off.  fp_a, fp_b: 구관's and 신관's outlines; front_a,
    front_b: (corner, unit vector west -> east) of their south fronts (build_campus.py MU_O · MU_T, MB_O · MB_T).
    Returns the lifts (구관, 신관: the floors go up by them), the nodes on the platform and a summary."""
    da = HALLS_FRONT[0][2] - sample(*HALLS_FRONT[0][:2])
    db = HALLS_FRONT[1][2] - sample(*HALLS_FRONT[1][:2])
    o, t = np.array(front_a[0], float), np.array(front_a[1], float)
    n = np.array([t[1], -t[0]])                                    # out of the front (south)
    pa, pb = Polygon(fp_a).buffer(0), Polygon(fp_b).buffer(0)
    S = (X - o[0]) * t[0] + (Y - o[1]) * t[1]
    D = (X - o[0]) * n[0] + (Y - o[1]) * n[1]
    s_end, s_yard = 61.4, 100.0                                    # (music_grade: 구관's east end, 신관's forecourt)
    inside = np.where(S < s_end + 12.0, 21.5 + 6.5 * np.clip((S - s_end + 3.0) / 4.0, 0, 1), 6.0)
    b0, bt = np.array(front_b[0], float), np.array(front_b[1], float)
    bn = np.array([bt[1], -bt[0]])
    court = Polygon([tuple(b0 + bt * u + bn * v) for u, v in ((12.0, -1.0), (64.5, -1.0), (64.5, 22.0), (12.0, 22.0))])
    plat = ((S >= -11.0) & (S <= s_yard) & (D <= 19.0) & (D >= -inside)) | \
        shapely.contains_xy(unary_union([pa.buffer(HALL_PAD), pb.buffer(HALL_PAD), court]), X, Y)
    lift = da + (db - da) * np.clip((S - s_end) / (s_yard - s_end), 0.0, 1.0)
    # (신관's east yard on its own grade: what it lacks, node by node)
    ey = shapely.contains_xy(EAST_YARD_POLY, X, Y) & ~shapely.contains_xy(pb.buffer(0.3), X, Y)
    (_, y0, z0), (_, y1, z1) = EAST_YARD
    lift = np.where(ey, z0 + (z1 - z0) * (Y - y0) / (y1 - y0) - Hn, lift)
    plat = plat | ey
    near = shapely.contains_xy(shapely.MultiPoint(list(zip(X[plat].tolist(), Y[plat].tolist()))).buffer(HALLS_EASE), X, Y)
    hold = shapely.contains_xy(unary_union([REGION] + list(anchors)), X, Y) & ~plat
    free = near & ~plat & ~hold
    d = np.where(plat, lift, 0.0)
    jj, ii = np.nonzero(free)
    j0, j1, i0, i1 = jj.min() - 1, jj.max() + 2, ii.min() - 1, ii.max() + 2
    W, F = d[j0:j1, i0:i1].copy(), free[j0:j1, i0:i1]
    for _ in range(4000):
        avg = 0.25 * (W[:-2, 1:-1] + W[2:, 1:-1] + W[1:-1, :-2] + W[1:-1, 2:])
        inner = W[1:-1, 1:-1]
        inner[F[1:-1, 1:-1]] = avg[F[1:-1, 1:-1]]
    d[j0:j1, i0:i1][F] = W[F]
    Hn += d
    info = dict(lift=(round(float(da), 2), round(float(db), 2)), platform=int(plat.sum()), east_yard=int(ey.sum()),
                east_yard_lift=(round(float(d[ey].min()), 2), round(float(d[ey].max()), 2)), eased=int(free.sum()),
                eased_max=round(float(d[free].max()), 2) if free.any() else 0.0)
    return float(da), float(db), plat, info


def forecourt_se(Hn, X, Y, FIXED, fill):
    """신관 앞마당의 남동쪽 on the 1997 scans' bare asphalt (FORECOURT_SE: those nodes to their heights, the platform's
    level giving way there), eased (harmonic) over FORECOURT_SE_RING round the zone at the nodes no other rule holds.
    Returns the nodes set (to be FIXED) and a summary."""
    H0 = Hn.copy()
    took = np.zeros(X.shape, bool)
    for x, y, z in FORECOURT_SE:
        jj, ii = np.nonzero((np.abs(X - x) < 0.01) & (np.abs(Y - y) < 0.01))
        Hn[jj, ii] = z
        took[jj, ii] = True
    ring = shapely.contains_xy(FORECOURT_SE_ZONE.buffer(FORECOURT_SE_RING), X, Y) & ~took & ~FIXED
    if ring.any():
        fill(ring)
    d = Hn - H0
    return took | ring, dict(nodes=int(took.sum()), moved=(round(float(d[took].min()), 2), round(float(d[took].max()), 2)),
                             ring=int(ring.sum()), ring_moved=(round(float(d[ring].min()), 2), round(float(d[ring].max()), 2))
                             if ring.any() else (0.0, 0.0))


def island(Hn, X, Y):
    """신관 앞마당의 섬과 동쪽 칸 줄 on their painted lines' height (ISLAND97: those nodes to their heights; no ring: the
    cells round them hold the exit road and the car park east, which stay).  Returns the nodes set (to be FIXED) and a
    summary."""
    took = np.zeros(X.shape, bool)
    moved = []
    for x, y, z in ISLAND97:
        jj, ii = np.nonzero((np.abs(X - x) < 0.01) & (np.abs(Y - y) < 0.01))
        moved += [float(z - Hn[j, i]) for j, i in zip(jj, ii)]
        Hn[jj, ii] = z
        took[jj, ii] = True
    return took, dict(nodes=int(took.sum()), moved=(round(min(moved), 2), round(max(moved), 2)))
