"""광복관 · 핀슨관 · 한경관 둘레와 서쪽 찻길의 1997년 땅 (#189; reference/고증/3.9_광복관.md 「둘레 땅의 높이」 · 「1997년의 평면과
지붕」, 2.9_찻길.md 「서쪽 길의 높이」, 3.15-3.17_일반_건물.md 「핀슨관 · 한경관의 바닥」).  tools/build_campus.py 가 부른다.

    took, info = kwangbok97.grade(Hn, X, Y, FIXED, keep, fill, tr_pts, tr_n)   # 심기가 끝난 뒤, 저장 바로 앞
    kwangbok97.outline()                      # 광복관의 1997년 외곽 (LATE_FOOTPRINT_1997)
    kwangbok97.paint()                        # (걷어 낼 것, 아스팔트, 보도블록) 다각형
    kwangbok97.walks(paths)                   # 길 목록: 1997년 땅에 놓일 수 없는 것을 빼고 1997년의 길을 더함
    kwangbok97.move_off(trees, shrubs, props) # 마당 · 길 위의 나무는 가장자리로(목록 제자리), 관목 · 소품은 뺌

Frame: campus metres, x east, y north.  Nothing here draws from build_campus.py's `rng`: the lists keep their order.

Heights: every absolute height in this file is 해발 (above sea level: the 1:5000 survey's datum).  The build lays the
ground on its working datum, that + T(x, y) at the place itself (tools/datum.py tilt, 고증 2.8 「측량 표고」), and takes
the tilt out again where it writes the ground: T() below is that lift.

What was measured (고증 3.9): the 1997-07-28 scans, frame pairs one by one (1.25 - 1.5 m windows, pairs over 0.7), and
the survey's spot heights and contours (2006 · 2024).  The two agree to 0.5 m wherever the photos see the ground:
- 광복관 stood on a bench at 49.85 m: its yard (a car park of lined rows), the road west of it, the road north of it
  and the paved place south of 핀슨관 on one level (the photos 49.6 - 50.2 on 60 points; the survey's spots 49.64 ·
  50.50).  The game had a lawn slope from 56 m (west) to 44.7 m (the road north of it).
- 핀슨관 on a knoll over it: the road up its west side 49.9 -> 54.8 m (20 % over 20 m, then nearly level; cars along
  its east edge), a small car park north of the hall at 52.0 m, the road past its east side about 50.2 m (under
  trees: the survey), 한경관's east front 52.1 m.  The game stood 3 - 6 m lower there.
- the west road of the cars (TR_W: 삼거리 -> 스팀슨관 서쪽 -> the island -> 한경관 앞 -> 핀슨관 동쪽 -> the place south of
  핀슨관): 37.8 m at the 삼거리, the survey's 40 · 45 · 50 m contours across it at s 30 · 80 · 112 m and its spot
  47.86 m at the island (s 101), 50.9 m before 한경관, then level at 50.2 m.  The game's road rose to 47.7 m and fell
  to 43.8 m.
GRID: the ground at the game's 5 m nodes inside REGION: the level places and the roads as measured, the 2006 survey's
surface elsewhere (핀슨관's knoll, 한경관, the wood between the two roads), eased between them.  Its row y 230 is the
boundary with the ground north of it (인문관 · 교육관 쪽: tools/jonghap97.py), on the heights agreed there.
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, unary_union

import datum

# --- the datum: the build's working height = 해발 + T(x, y) (tools/datum.py) -------------------------------------------
def T(x, y):
    return datum.tilt(x, y)


KB, PINSON, HANGYEONG = 468614722, 246156113, 246156110
# --- 광복관 (1997): its own frame, o OSM's south-west corner, u along OSM's south face (east-south-east), v north-north-east.
# The scans' roofs resampled in this frame on the eaves' plane (four frames, each edge where the frames agree to 0.2 m):
# the eaves at 60.4 - 61.5 m (the two wings alike), the flat-roofed block in the corner 65.8 m, a low flat-roofed
# annex in the yard against the south wing 52.3 - 53.0 m.  The walls 0.5 m inside the eaves.  (u0, u1, v0, v1):
KB_O, KB_ANG = (-146.88, 71.59), -14.85
KB_WALLS = dict(head_w=(-1.2, 7.8, 11.75, 31.6),      # the west head: a hipped block deeper than the wing
                south=(7.8, 47.8, 11.75, 22.55),      # the south wing (the front with the door)
                north=(36.5, 46.9, 22.55, 63.9),      # the north wing along the yard's east side
                head_n=(26.8, 36.5, 55.1, 63.9),      # the north head, out into the yard's north end
                tower=(39.85, 50.0, 16.8, 25.55))     # the flat-roofed block where the wings meet, a storey higher
KB_ANNEX = (10.7, 27.0, 22.55, 32.6)                  # the low annex in the yard (one storey)
KB_OUTLINE_UV = [(-1.2, 11.75), (47.8, 11.75), (47.8, 16.8), (50.0, 16.8), (50.0, 25.55), (46.9, 25.55), (46.9, 63.9),
                 (26.8, 63.9), (26.8, 55.1), (36.5, 55.1), (36.5, 22.55), (7.8, 22.55), (7.8, 31.6), (-1.2, 31.6)]
KB_DOOR_U = 19.0                  # the door's middle along the south front (where OSM's walk up from the library comes)
BENCH_Z = 49.85                   # 해발 @ (-120, 110): the yard, the two roads and the place south of 핀슨관
KB_FLOOR = 49.75                  # 해발 @ (-125.5, 78.1): the main floor (the eaves 11.1 m over it: 60.85)
KB_FORE_Z = 48.0                  # 해발 @ (-126.5, 72.0): the forecourt at the foot of the front flight (ten or eleven risers)
KB_EAVES, KB_TOWER, KB_ANNEX_TOP = 60.85, 65.85, 52.75      # 해발 @ (-120, 85)
KB_FORE_UV = (2.0, 36.0, 1.0, 11.75)
# south of the forecourt the ground falls gently to the walk up from the library (the survey: 47.5 m at the front,
# 46.3 - 47 m 12 m south of it, 45 m 22 m south): one slope over the apron the game first levelled before OSM's front
# (44.9 m, 12 m farther south than the 1997 front), from the forecourt's edge down to that apron's own south edge
KB_SLOPE_UV = (-5.0, 34.0, -14.0, 1.0)
KB_SLOPE_Z = (48.0, 44.9)         # 해발 @ (-127, 68) and (-131, 53): at v 1 and at v -14

_ka = math.radians(KB_ANG)
_kt = np.array([math.cos(_ka), math.sin(_ka)])
_kn = np.array([-_kt[1], _kt[0]])


def kb_xy(u, v):
    q = np.array(KB_O) + _kt * u + _kn * v
    return round(float(q[0]), 2), round(float(q[1]), 2)


def kb_uv(x, y):
    dx, dy = np.asarray(x, float) - KB_O[0], np.asarray(y, float) - KB_O[1]
    return dx * _kt[0] + dy * _kt[1], dx * _kn[0] + dy * _kn[1]


def kb_rect(u0, u1, v0, v1):
    return Polygon([kb_xy(u0, v0), kb_xy(u1, v0), kb_xy(u1, v1), kb_xy(u0, v1)])


def outline():
    """광복관's 1997 outline (CCW), for LATE_FOOTPRINT_1997"""
    return [kb_xy(u, v) for u, v in KB_OUTLINE_UV]


def annex():
    return kb_rect(*KB_ANNEX)


# --- the level places and the roads (x, y[, 해발]) ---------------------------------------------------------------------
# the bench: the paved yard, the road west of the hall and the one north of it, the place south of 핀슨관, the hall's
# own ground north of its south face, out to the top of the bank east of the north wing (under trees in the scans; the
# survey's 50 m contour)
BENCH = Polygon([(-176.0, 54.0), (-172.5, 64.0), (-168.5, 71.0), (-166.0, 76.5), (-163.0, 81.0), (-159.0, 88.0), (-155.0, 95.0),
                 (-150.5, 101.5), (-147.0, 106.5), (-143.8, 110.5), (-140.0, 114.5), (-137.0, 119.0), (-133.5, 126.0),
                 (-128.0, 130.0), (-121.0, 133.0), (-113.0, 135.5), (-106.0, 137.5), (-100.5, 139.5), (-92.0, 141.0),
                 (-86.5, 139.5), (-82.5, 137.5), (-78.0, 138.5), (-76.3, 148.3), (-65.6, 145.5), (-61.5, 142.5), (-58.0, 137.0),
                 (-60.0, 133.5), (-64.5, 130.0), (-68.0, 124.0), (-70.0, 118.0), (-71.5, 110.0), (-76.0, 100.0), (-79.5, 90.0),
                 (-83.0, 80.0), kb_xy(52.0, 11.75), kb_xy(-1.2, 11.75), (-147.5, 79.0), (-152.0, 73.5), (-157.5, 69.5), (-163.0, 66.0),
                 (-168.0, 58.0), (-170.0, 54.0)])
# what of it was paved (asphalt): not the hall, not the planted bank east of the north wing
BENCH_PAVED_EAST = [(-85.0, 121.0), (-75.0, 118.5), (-70.5, 122.0), (-67.0, 127.0), (-63.0, 131.5), (-60.5, 134.5)]     # (the place's south-east edge)
# the road west of 광복관 (OSM's line, which the scans' road follows to 1 m): its height along it, from where it leaves
# the game's ground (x, y, 해발)
ROAD_KB_W = [(-173.8, 55.1, 48.3), (-170.2, 60.0, 49.2), (-167.1, 65.0, 49.8), (-163.9, 70.1, 50.05), (-157.7, 80.4, 50.2),
             (-148.3, 95.8, 50.2), (-142.1, 106.1, 50.0), (-134.3, 115.1, 49.85)]
# the road up 핀슨관's west side to the car park north of the hall: its middle line and the scans' heights on it
ROAD_PIN_W = [(-93.2, 137.5, 49.9), (-92.1, 144.2, 51.4), (-91.05, 150.0, 52.4), (-90.3, 154.0, 53.2), (-89.75, 157.0, 53.85),
              (-89.2, 160.0, 54.05), (-87.6, 164.9, 54.2), (-85.6, 170.7, 54.6), (-83.8, 176.8, 54.8), (-81.0, 181.5, 54.6),
              (-76.5, 184.5, 53.6), (-71.0, 185.0, 52.5)]
PIN_W_HALF = (3.2, 5.6)           # (west of the line, east of it: the lane and the cars along its east edge)
PIN_LOT = Polygon([(-71.5, 175.3), (-57.6, 171.7), (-53.0, 190.0), (-71.0, 190.5)])       # the car park north of 핀슨관
PIN_LOT_Z = 52.0                  # 해발 @ (-63, 181)
HK_APRON = Polygon([(-41.9, 209.8), (-39.2, 209.1), (-36.0, 222.6), (-38.4, 223.2)])       # before 한경관's east front
HK_APRON_Z = 52.1                 # 해발 @ (-40, 216)
HK_FLOOR = 52.1                   # 해발 @ (-40.2, 216.4): 한경관's floor at its east door (the scans: 51.9 - 52.3 m at the wall's foot)
# the cars' west road (TR_W): (x, y, 해발) on its middle line.  The 삼거리 and the first 30 m as the game has them
# (the survey's 40 m contour crosses it at s 27 - 33 m, where the game stands at 39.7 - 40.4)
ROAD_W = [(6.2, 140.7, 40.05), (1.6, 149.6, 41.25), (-1.5, 159.1, 42.55), (-4.6, 168.6, 43.7), (-7.7, 178.1, 44.6),
          (-10.4, 186.6, 45.4), (-13.3, 197.3, 46.6), (-14.8, 205.3, 47.8), (-17.5, 211.6, 48.8), (-21.0, 217.2, 49.8),
          (-24.2, 218.4, 50.15), (-28.8, 218.3, 50.55), (-33.7, 217.2, 50.9), (-36.0, 211.0, 50.7), (-38.3, 203.0, 50.45),
          (-41.1, 193.4, 50.3), (-45.3, 179.0, 50.25), (-50.9, 159.8, 50.2), (-56.4, 145.9, 50.1), (-62.7, 138.1, 49.95),
          (-71.6, 133.9, 49.85), (-108.0, 130.4, 49.85)]
# the two roads north of the island (OSM's, to 인문관 and to 교육관), south of y 230: the heights agreed with the ground
# north of it (the scans and the two surveys within 0.5 m there)
ROAD_N1 = [(-14.8, 205.3, 47.8), (-20.1, 220.2, 50.35), (-20.7, 224.2, 50.85), (-21.3, 228.2, 51.45), (-21.4, 232.1, 52.05)]
ROAD_N2 = [(-11.3, 216.6, 49.45), (-10.0, 221.4, 49.75), (-8.7, 226.2, 50.35), (-6.2, 235.9, 51.1)]
ROW_230 = [(-60.0, 55.0), (-50.0, 54.4), (-40.0, 53.8), (-30.0, 52.85), (-20.0, 51.8), (-10.0, 50.45), (0.0, 50.0)]   # (x, 해발) on y 230

# --- GRID: the ground at the game's 5 m nodes (x GRID_X0 + 5 i, y GRID_Y0 + 5 j; rows south -> north), 해발 in decimetres;
# made by the composer in this file's history (the level places and roads above, the 2006 survey's surface elsewhere,
# harmonic between them); 0 where REGION does not reach
GRID_X0, GRID_Y0, GRID_D = -180.0, 50.0, 5.0
GRID = np.array([[int(v) for v in r.split()] for r in """
0 0 0 0 0 0 0 0 0 0 0 0 449 425 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 483 486 0 0 0 0 0 450 451 454 456 459 447 437 428 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 498 492 484 0 450 453 456 458 461 464 466 469 472 457 450 450 450 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 496 498 485 0 463 466 468 471 474 476 479 480 470 465 466 467 455 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 509 500 501 487 473 476 478 480 480 480 480 480 476 475 480 498 477 458 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 501 501 502 490 485 480 480 480 480 480 480 480 480 480 498 498 477 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 514 502 502 502 492 480 480 480 480 480 480 498 498 498 498 498 498 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 502 502 502 502 480 480 498 498 498 498 498 498 498 498 498 498 480 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 519 502 502 502 501 498 498 498 498 498 498 498 498 498 498 498 498 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 516 502 502 501 499 498 498 498 498 498 498 498 498 498 498 498 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 502 501 501 500 499 498 498 498 498 498 498 498 498 498 498 483 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 520 500 500 500 499 499 498 498 498 498 498 498 498 498 498 498 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 518 499 499 499 498 498 498 498 498 498 498 498 498 498 498 478 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 514 499 498 498 498 498 498 498 498 498 498 498 498 498 486 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 498 498 498 498 498 498 498 498 498 498 498 498 498 498 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 519 498 498 498 498 498 498 498 498 498 498 498 498 498 487 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 518 498 498 498 498 498 498 498 498 498 498 498 498 498 485 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 515 509 498 498 498 498 498 498 498 498 498 498 498 481 466 450 450 450 450 436 419 408 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 510 506 498 498 504 503 498 498 498 498 490 478 468 459 453 450 450 434 421 412 408 404 400
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 517 514 516 517 509 498 498 498 501 501 490 478 467 458 450 450 443 431 421 414 408 406
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 527 523 524 526 518 511 507 505 503 501 501 485 473 461 450 450 450 438 428 419 414 411
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 534 534 536 527 519 515 510 506 502 502 489 477 464 450 450 450 443 432 422 420 418
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 541 540 541 532 525 518 514 508 502 502 494 481 467 450 450 450 446 436 428 426 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 546 542 543 538 529 522 517 512 506 502 502 486 471 457 450 450 445 439 433 431 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 550 545 546 546 534 523 519 515 509 502 502 489 476 462 450 450 446 442 438 436 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 550 547 548 535 520 520 520 513 502 502 491 480 467 454 450 448 444 443 440 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 553 547 546 538 520 520 520 520 509 503 495 484 472 458 455 452 448 447 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 556 548 541 533 520 520 520 520 511 503 503 489 478 462 459 456 453 450 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 550 542 533 520 520 520 520 512 503 503 493 482 468 464 459 457 453 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 550 545 538 531 527 524 520 513 503 503 497 487 478 471 464 463 457 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 550 549 544 539 533 528 523 516 509 504 504 494 485 477 470 469 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 550 546 541 536 531 525 520 514 505 505 498 490 483 478 472 464 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 550 547 542 538 533 528 523 520 521 507 502 496 488 485 478 468 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 550 547 544 540 536 532 527 524 521 508 507 502 496 493 485 474 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 548 545 542 539 536 532 528 521 509 506 502 503 500 497 485 465 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 549 547 545 542 540 537 533 529 522 517 513 510 506 502 503 481 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 550 549 548 550 547 544 541 538 533 528 523 518 511 504 502 500 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
""".strip().splitlines()], float) / 10.0
REGION = Polygon([(-178.0, 52.0), (-176.0, 62.0), (-171.0, 71.0), (-166.0, 80.0), (-162.0, 88.0), (-158.0, 95.0), (-153.5, 102.0),
                  (-150.0, 107.0), (-146.5, 111.5), (-142.5, 116.0), (-139.5, 120.0), (-136.0, 127.0), (-130.0, 132.0),
                  (-122.0, 135.5), (-113.0, 138.0), (-104.0, 141.0), (-101.0, 146.0), (-99.0, 155.0), (-96.5, 165.0),
                  (-94.0, 175.0), (-91.0, 185.0), (-88.0, 196.0), (-84.0, 206.0), (-80.0, 216.0), (-79.0, 226.0), (-78.0, 230.5),
                  (2.0, 230.5), (2.0, 222.0), (-3.0, 212.0), (-6.0, 200.0), (-3.0, 188.0), (0.0, 176.0), (3.0, 166.0), (6.0, 156.0),
                  (9.0, 148.0), (11.0, 141.0), (4.0, 138.0), (-8.0, 136.0), (-20.0, 134.0), (-35.0, 133.0), (-48.0, 131.0),
                  (-57.0, 131.0), (-62.5, 127.5), (-66.0, 123.0), (-68.0, 117.0), (-69.5, 110.0), (-74.0, 100.0), (-77.5, 90.0),
                  (-81.0, 80.0), (-84.0, 71.0), (-86.0, 62.0), kb_xy(52.0, -1.0), kb_xy(34.5, -14.5), kb_xy(-5.5, -14.5),
                  kb_xy(-5.5, -1.0), (-156.0, 66.0), (-163.0, 60.0), (-168.0, 52.0)])
RING = 15.0                       # eased out (harmonic) this far round REGION
NORTH_Y = 230.0                   # (no easing north of it: the ground there is jonghap97's)
HALL_PAD = 2.6                    # the feet of the halls that stay (백양관 북쪽 날개, 연합신학대학원)
ROAD_HALF = 3.0


def grid_z(x, y):
    """GRID at (x, y), bilinear: 해발"""
    from scipy.ndimage import map_coordinates
    x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    z = map_coordinates(GRID, [(y.ravel() - GRID_Y0) / GRID_D, (x.ravel() - GRID_X0) / GRID_D], order=1, mode='nearest')
    return z.reshape(x.shape) if x.ndim else float(z[0])


def _prof(line, x, y):
    """the height on a (x, y, z) line abreast of the points, and their distance from it and along it"""
    ls = LineString([q[:2] for q in line])
    ss = np.array([ls.project(Point(*q[:2])) for q in line])
    zs = np.array([q[2] for q in line])
    P = shapely.points(np.asarray(x, float), np.asarray(y, float))
    s = shapely.line_locate_point(ls, P)
    return np.interp(s, ss, zs), shapely.distance(ls, P), s, ls


def bench_z(x, y):
    """the bench's height at (x, y): BENCH_Z, the road west of the hall on ROAD_KB_W south of the yard"""
    z, d, s, ls = _prof(ROAD_KB_W, x, y)
    w = np.clip((14.0 - d) / 6.0, 0.0, 1.0)             # (the road's own height within 8 m of its line, eased by 14 m)
    return BENCH_Z + (z - BENCH_Z) * w


def cars_1997():
    """the cars read off the scans in this part (tools/cars97_new.json, labels kb-* · pin-*): (x, y, heading rad, label)"""
    import json
    import os
    d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cars97_new.json'), encoding='utf-8'))
    out = []
    for z in d.values():
        for c in z.get('cars', []):
            if len(c) > 5 and isinstance(c[5], str) and (c[5].startswith('kb-') or c[5].startswith('pin-')):
                out.append((c[0], c[1], math.radians(c[2]), c[5]))
    return out


def grade(Hn, X, Y, FIXED, keep, fill, tr_pts, tr_n, step=5.0, half=800.0):
    """GRID + T inside REGION (FIXED there yields; `keep`, the feet of the halls that stay, does not), the cars' west
    road on ROAD_W level across (the cells its wheels cross), then eased out round REGION (fill: harmonic_fill) over
    the nodes no other rule set.  Returns the nodes set (to be FIXED) and a summary."""
    H0 = Hn.copy()
    Tn = T(X, Y)
    inr = shapely.contains_xy(REGION, X, Y) & ~keep
    Hn[inr] = (grid_z(X, Y) + Tn)[inr]
    info = dict(region=(int(inr.sum()), round(float((Hn - H0)[inr].min()), 1), round(float((Hn - H0)[inr].max()), 1)))
    # the road: its nodes (the cells its wheels cross), level across
    ls = LineString([tuple(q) for q in tr_pts])
    qs = np.array([ls.project(Point(x, y)) for x, y, _ in ROAD_W])
    zs = np.array([z for _, _, z in ROAD_W])
    k0 = int(round(qs[0]))
    cells = set()
    for k in range(k0, len(tr_pts)):
        for o in np.arange(-2.7, 2.71, 0.9):
            x, y = np.array(tr_pts[k]) + np.array(tr_n[k]) * o
            cells.add((int(math.floor((y + half) / step)), int(math.floor((x + half) / step))))
    road = np.zeros(X.shape, bool)
    for j, i in {(j + a, i + b) for j, i in cells for a in (0, 1) for b in (0, 1)}:
        s = ls.project(Point(X[j, i], Y[j, i]))
        if keep[j, i] or s <= qs[0] + 0.5:
            continue
        Hn[j, i] = float(np.interp(s, qs, zs)) + Tn[j, i]
        road[j, i] = True
    info['road'] = (int(road.sum()), round(float((Hn - H0)[road].min()), 1), round(float((Hn - H0)[road].max()), 1))
    # the cars the scans have parked here (tools/cars97_new.json: the rows of the yard, the two roads and the car park
    # north of 핀슨관): the grid cells under each car on its place's own level, so that a row along a kerb does not lean
    # with the bank beside it
    lot = np.zeros(X.shape, bool)
    for x, y, h, lab in cars_1997():
        t, n = (math.cos(h), math.sin(h)), (-math.sin(h), math.cos(h))
        cells = {(int(math.floor((y + t[1] * a + n[1] * b + half) / step)), int(math.floor((x + t[0] * a + n[0] * b + half) / step)))
                 for a in (-1.7, -0.6, 0.6, 1.7) for b in (-0.85, 0.85)}
        for j, i in {(j + a, i + b) for j, i in cells for a in (0, 1) for b in (0, 1)}:
            if keep[j, i] or road[j, i]:
                continue
            if lab.startswith('pin-R'):
                z = float(_prof(ROAD_PIN_W, X[j, i], Y[j, i])[0])
            elif lab.startswith('pin-P'):
                z = PIN_LOT_Z
            else:
                z = float(bench_z(X[j, i], Y[j, i]))
            Hn[j, i] = z + Tn[j, i]
            lot[j, i] = True
    info['cars'] = int(lot.sum())
    took = inr | road | lot
    # round them
    north = Y > NORTH_Y + 1.0                           # (jonghap97's ground)
    east = ((X > 4.0) & (Y > 147.0)) | (X > 14.0)       # (스팀슨관's south yard and back, the 삼거리: as they are)
    ring = shapely.contains_xy(REGION.buffer(RING), X, Y) & ~took & ~keep & ~FIXED & ~north & ~east
    if ring.any():
        fill(ring)
    info['ring'] = int(ring.sum())
    moved = np.abs(Hn - H0)
    info['moved'] = (int((moved > 0.05).sum()), round(float(moved.max()), 1))
    return took | ring, info


# --- the ground map ---------------------------------------------------------------------------------------------------
def _strip(line, west, east):
    ls = LineString([q[:2] for q in line])
    return unary_union([ls.buffer(west, cap_style='flat', single_sided=True), ls.buffer(-east, cap_style='flat', single_sided=True)]).buffer(0)


def hall():
    return Polygon(outline()).buffer(0)


def paved():
    """the bench's asphalt (the yard, the two roads, the place south of 핀슨관), the road up 핀슨관's west side and the
    car park north of it"""
    east = Polygon([kb_xy(46.9, 63.9), kb_xy(26.8, 63.9)] + [(-106.0, 137.5), (-100.5, 139.5), (-92.0, 141.0), (-86.5, 139.5),
                    (-82.5, 137.5), (-78.0, 138.5), (-76.3, 148.3), (-65.6, 145.5), (-61.5, 142.5), (-58.5, 137.5)] +
                   BENCH_PAVED_EAST[::-1])
    west = BENCH.intersection(Polygon([(-200.0, 40.0), kb_xy(-1.2, 0.0), kb_xy(-1.2, 31.6), kb_xy(36.5, 31.6), kb_xy(36.5, 55.1),
                                       kb_xy(26.8, 55.1), kb_xy(26.8, 63.9), (-106.0, 137.5), (-140.0, 150.0), (-200.0, 150.0)]))
    yard = unary_union([west, east]).difference(hall().buffer(0.3)).difference(annex().buffer(0.3))
    pin = _strip(ROAD_PIN_W, *PIN_W_HALF)
    mouth = Polygon([(-65.6, 145.5), (-58.5, 147.0), (-55.0, 140.0), (-58.5, 137.5), (-61.5, 142.5)])   # (where the cars' road comes in)
    return unary_union([yard, pin, mouth, PIN_LOT.difference(Polygon(PINSON_FP).buffer(0.6))]).buffer(0)


PINSON_FP = [(-65.09, 146.74), (-58.57, 171.72), (-69.09, 174.43), (-75.61, 149.45)]      # (OSM 246156113)
KB_OSM = [(-142.58, 85.79), (-146.88, 71.59), (-93.32, 57.39), (-77.07, 117.88), (-94.07, 122.39), (-106.52, 76.06)]


def forecourt():
    return kb_rect(*KB_FORE_UV)


def paint():
    """(taken up: lawn again, asphalt, paving).  Taken up: OSM's 광복관 and its apron where no hall of 1997 stood, the
    walks the game had across the yard and on the bank east of the hall, the walk beside 핀슨관 that the road replaces"""
    asph = paved()
    fore = forecourt()
    gone = [LineString([a, b]).buffer(1.9) for a, b in WALKS_GONE]
    gone.append(LineString([(-70.8, 117.6), (-83.4, 74.0)]).buffer(1.9))      # (the walk down the east side: on the bank)
    front = kb_rect(-12.0, 62.0, -20.0, 0.8)        # (the walks before OSM's front stay, on the slope up to the forecourt)
    up = unary_union([Polygon(KB_OSM).buffer(4.2, join_style=2).difference(front), BENCH.buffer(1.0),
                      _strip(ROAD_PIN_W, 5.0, 8.5)] + gone).difference(hall())
    return up, asph, fore


PINSON_EAVES = 56.9               # 해발 @ (-67.1, 160.6): 핀슨관's eaves (the scans' roof; the game's, as it was)


def plan():
    """광복관 for blender/landmarks.py kwangbok (campus.json buildings[].plan): its frame, the 1997 walls and the low
    annex (u0, u1, v0, v1), the door, and the heights on the working datum"""
    t = float(T(*kb_xy(KB_DOOR_U, 11.75)))
    return dict(o=list(KB_O), ang=KB_ANG, walls={k: list(v) for k, v in KB_WALLS.items()}, annex=list(KB_ANNEX), door_u=KB_DOOR_U,
                floor=round(KB_FLOOR + t, 2), eaves=round(KB_EAVES + t, 2), tower=round(KB_TOWER + t, 2),
                annex_top=round(KB_ANNEX_TOP + t, 2), yard=round(BENCH_Z + t, 2), fore=round(KB_FORE_Z + t, 2))


# OSM's walks that the 1997 ground leaves no room for (the bank east of the north wing is a 9 m drop in 6 m; the yard
# is a car park; 핀슨관's west walk is the road): (first point, last point), either way round
WALKS_GONE = [((-94.4, 132.5), (-107.8, 82.3)), ((-107.8, 82.3), (-117.9, 79.1)), ((-73.8, 194.2), (-87.7, 133.0)),
              ((-61.1, 118.1), (-64.8, 127.0)), ((-64.8, 127.0), (-64.4, 130.5)), ((-67.1, 130.0), (-68.2, 126.4)),
              ((-68.2, 126.4), (-70.8, 117.6)), ((-66.7, 110.5), (-69.0, 101.9)), ((-70.3, 97.5), (-72.1, 91.0)),
              ((-69.0, 101.9), (-70.3, 97.5)), ((-69.6, 99.8), (-72.8, 100.8)), ((-71.2, 116.1), (-65.7, 114.6)),
              ((-66.7, 110.5), (-65.7, 114.6))]


def _on(p, a, b, tol=1.2):
    """every point of the path within tol of the segment a - b"""
    seg = LineString([a, b])
    return all(seg.distance(Point(q[0], q[1])) < tol for q in p['pts'])


def walks(paths):
    """the list of walks and roads (campus.json paths) on the 1997 ground, in place: what is left of WALKS_GONE out
    (the walks among them are cut back already where their paving was taken up: paint), the road up 핀슨관's west side
    in.  Returns how many went."""
    n0 = len(paths)
    paths[:] = [p for p in paths if not (len(p['pts']) > 1 and any(_on(p, a, b) for a, b in WALKS_GONE))]
    paths.append(dict(kind='service', w=6, pts=[[round(q[0], 1), round(q[1], 1)] for q in ROAD_PIN_W]))
    return n0 + 1 - len(paths)


def move_off(trees, shrubs, props):
    """what the planting put on the 1997 asphalt and in the hall's 1997 outline: trees step aside to the nearest edge
    (in their places in the list), shrubs and props go.  Returns (shrubs out, props out, trees moved)"""
    zone = unary_union([paved(), forecourt(), annex()]).buffer(0.8)
    n0 = (len(shrubs), len(props))
    shrubs[:] = [s for s in shrubs if not zone.contains(Point(s[1], s[2]))]
    props[:] = [p for p in props if not zone.contains(Point(p[1], p[2]))]
    block = unary_union([zone, hall().buffer(3.0)]).buffer(1.5)
    edge = unary_union([g.exterior for g in (block.geoms if hasattr(block, 'geoms') else [block])])
    moved = []
    for t in trees:
        if zone.contains(Point(t[1], t[2])):
            q = nearest_points(edge, Point(t[1], t[2]))[0]
            moved.append((t[0], t[1], t[2], round(q.x, 2), round(q.y, 2)))
            t[1], t[2] = round(q.x, 2), round(q.y, 2)
    return n0[0] - len(shrubs), n0[1] - len(props), moved
