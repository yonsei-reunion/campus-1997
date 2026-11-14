"""노천극장 · 음악관 뒤 언덕과 동쪽 찻길 남쪽의 1997년 땅 (#189; reference/고증/3.14_옛_노천극장.md 「땅의 높이」,
3.11 · 2.9).  tools/build_campus.py 가 부른다.

    took, info = music97.grade(Hn, X, Y, FIXED, halls, keep, fill, amph, tr_line, tr_n)   # 심기가 끝난 뒤, 저장 바로 앞

Frame: campus metres, x east, y north.  Every absolute height here is 게임 기준 (the game's datum, which near here is
the 1997 photos' datum: 한경길 · 언더우드관 · 의료원 둘레 photo − game +0.1 ~ +0.9 m), not the survey's above sea level.

- The game's ground round the old 노천극장 and on the wooded hill north of 음악관 was the surface model's, 8 - 13 m under
  the 1997-07-28 scans round the bowl and 20 m on the hilltop (3.14 「남은 한계」).  The 1:5000 survey (국토지리정보원
  수치지형도, surveyed 2006 and 2024: spot heights and 5 m contours) settles it.  The photos' heights stand over the
  survey's by one plane all over the campus (PHOTO_DZ: 107 spot heights, rms 0.35 m, both surveys alike: the photos'
  block took the tilt of the game's roads it was tied to, so the game's datum is that plane over the sea).  Here
  photo − (survey + plane) is +0.4 m (median of 445 ground points, rms 1.4), but game − (survey + plane) −6 to −23 m
  round the bowl and on the hill.  So the photos were right.
- GRID: the ground at the game's 5 m nodes (x 115 .. 285, y 30 .. 230, decimetres): the 2006 survey's surface (its contours with
  its spot heights, 2.5 m) + PHOTO_DZ, nudged to the 1997 photos where they see the ground within 4 m of it (the
  survey is after the 1999 theatre: the photos have the 1997 bowl).  Applied inside REGION, the halls' feet kept,
  eased out round it (harmonic) to the game's ground.
- 노천극장 (AMPH in build_campus.py): its floor on the photos (59.6 m; the 1999 theatre's floor, 2006 · 2024 survey
  + plane: 59.1 · 59.7 m) instead of a stage under the walk behind it; the bowl cut into GRID as the first cut was
  into the old ground (the same terraces and easing past the rim; behind the stage 2 m level, then down to the walk
  west of it over 6 m, as the photos have that 4 m under the floor).
- 동쪽 찻길 (TR_E) from 아펜젤러관's yard to the fork east of 한경길 (EAST_Q97 from there): ROAD, the survey's spot
  heights and the contours crossing it, + PHOTO_DZ.  The photos' across-road profiles here read 1.5 - 3.5 m higher
  (the canopy's edge, as 2.9 「남은 한계」 suspected).  Levelled across as tr_grade does.
- 용재관's drive (YJ_BRANCH, x < 126) is the 대강당 · 용재관 part's (54.3 m at its east end): TM_KEEP stays.
- 음악관 두 동 (halls; 3.11 「두 동의 절대 높이」): the two halls and the ground before them stood 1.5 · 2.25 m under the
  photos and the survey.  HALLS_FRONT: the road along 구관's front and 신관's forecourt at its door, read again on bare
  asphalt with small windows (the first reading, 1.4 m over the survey, had the parked cars' roofs and the hedge in
  it); the survey's spot on the road before 구관 and its 55 m contour along 신관's front agree to 0.45 m.  The whole
  platform is lifted by what it lacks (the shapes on it stay: build_campus.py music_grade), the lift eased to nothing
  at the hill behind (GRID), the car parks south and east (tools/med97.py) and 26 m off; the halls' floors go with it.
  신관's east yard (EAST_YARD) on the photos' own grade: a terrace over the car park east of it.
- Nothing here draws from build_campus.py's `rng`.
"""
# (2026-11-15: every absolute height in this file's code is on the sea-level datum, 2.0 m under the old game datum;
# heights quoted in comments written before then are 2.0 m higher: tools/build_campus.py SURFACE_DZ)
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
import shapely.ops
from shapely.ops import unary_union

# --- 게임 기준 heights (the one place to shift them all) ------------------------------------------------------------
PHOTO_DZ = (0.052, 0.522, 0.248)  # survey height + c + a x / 100 + b y / 100 = the game's datum (s134's plane, since the 2 m datum shift)
AMPH_FLOOR = 57.6                 # 노천극장's floor (the 1997 scans)
ROAD = [(69.1, 146.2, 42.9),      # (x, y, height) on TR_E: 아펜젤러관's yard (the square's level, kept)
        (86.0, 164.6, 45.9),      # 2006 contour 45 m, 0.9 m off the road's middle
        (126.1, 211.5, 52.6),     # 2024 spot 51.34 m on the road
        (132.6, 222.4, 52.0),     # (between it and the 50 m contour 6.9 m off at (128.8, 231.1): 53.3)
        (141.5, 251.0, 51.4),     # 2005/2006 contour 50 m, 3 m off
        (149.7, 262.8, 50.6)]     # EAST_Q97's first photo height (the fork), as it was
# 음악관: (x, y, height) of the ground before each hall: the road along 구관's front (the photos 해발 55.3 m: 60 points
# S -8 .. 60 m along it, 5 - 6 frame pairs each; the survey's spot (177.0, -31.1) 54.87 m), 신관's forecourt at its door
# (the photos 해발 54.95 m by the stalls east of the door; the survey's 55 m contour runs along the front there)
HALLS_FRONT = [(170.0, -25.0, 56.18), (250.0, -31.0, 56.23)]
HALLS_EASE = 26.0                 # the lift fades out this far round the platform
# the paved yard along 신관's east wall (two columns of stalls in the photos), rising north on one grade: (x, y, height)
# at its south and north ends (the photos 해발 55.0 -> 56.3 m, 60 points with five or six frame pairs; it stands 2.4 m
# over the car park east of it at its south end, level with it at its north end), and its outline
EAST_YARD = [(276.0, -26.0, 56.43), (276.0, 22.0, 57.89)]
EAST_YARD_POLY = Polygon([(262.5, -31.0), (283.5, -31.0), (283.5, 23.5), (271.5, 23.5), (270.5, 14.5), (263.5, -15.0)])
GRID_X0, GRID_Y0, GRID_D = 115.0, 30.0, 5.0       # (the grid's south-west node, spacing: the game's 5 m nodes)
GRID = np.array([[int(v) for v in r.split()] for r in """
512 521 555 567 565 619 636 652 634 710 701 686 671 661 707 711 762 762 763 762 713 713 663 662 606 590 580 581 588 599 602 607 609 611 607
490 512 536 554 560 620 644 634 709 695 679 660 761 761 711 744 759 767 766 764 763 713 684 664 628 598 585 587 601 615 622 623 623 619 618
477 509 526 548 559 622 643 659 699 680 660 760 732 711 733 756 773 785 786 777 764 714 706 680 665 645 638 639 648 675 678 678 664 641 622
458 508 521 547 559 627 659 709 691 669 760 732 711 734 754 767 793 811 813 801 780 765 718 706 685 665 663 671 678 687 688 680 679 664 625
458 508 521 548 592 615 656 684 687 727 742 711 731 752 770 787 808 829 824 817 814 780 767 719 717 702 699 700 703 706 705 693 680 679 624
458 494 520 543 559 619 609 688 698 760 710 725 750 768 786 804 816 818 817 815 814 814 765 752 736 729 722 715 716 717 713 699 684 675 670
459 494 518 539 559 622 610 708 713 710 711 739 761 782 802 812 819 824 827 828 825 817 816 765 765 755 743 724 715 716 717 703 685 669 668
480 498 509 536 559 622 610 711 710 702 723 751 772 800 812 820 828 836 843 850 851 839 822 818 766 765 765 745 715 716 716 710 693 675 667
501 505 510 535 559 622 610 711 710 709 727 761 791 812 817 828 839 850 860 871 874 858 843 825 819 766 765 765 738 716 716 716 703 689 679
513 511 511 534 559 622 610 712 727 712 728 761 812 812 822 836 852 867 867 870 875 877 860 843 825 819 766 766 751 726 716 716 712 699 689
515 513 511 534 560 622 610 710 694 711 728 761 812 812 824 843 870 873 869 868 876 878 878 860 838 824 801 766 759 741 716 717 717 707 697
516 511 511 535 560 622 610 711 711 718 728 762 792 812 820 846 873 875 869 865 870 877 878 879 856 835 820 795 766 757 738 717 717 714 704
511 507 510 535 560 622 610 706 661 740 731 757 778 801 813 815 871 865 860 861 867 875 878 878 869 847 822 809 787 766 767 733 717 717 711
502 506 510 534 560 621 611 711 661 762 763 765 777 795 816 814 816 831 846 863 875 878 878 878 876 857 836 817 806 782 767 767 742 717 718
499 506 509 533 558 610 647 680 689 714 738 766 790 798 807 817 815 815 834 872 876 878 878 877 875 865 846 827 817 805 780 767 767 743 732
499 506 508 531 557 606 623 673 670 695 729 738 740 790 788 805 817 815 819 880 879 879 879 878 874 871 855 841 829 820 806 780 766 759 743
500 506 508 531 560 600 626 626 653 674 679 735 742 736 783 781 801 817 817 839 880 880 880 876 871 868 865 856 847 831 820 806 782 767 768
501 506 509 534 567 576 613 623 627 676 677 681 732 736 748 763 776 786 815 817 845 872 871 868 867 867 872 865 856 846 830 819 818 784 768
501 507 509 536 569 584 598 624 628 662 674 675 676 727 732 732 726 771 781 802 816 854 866 866 866 867 870 871 861 853 840 826 819 807 779
502 507 509 536 567 580 581 630 628 643 656 671 671 673 701 727 726 738 770 768 816 841 866 866 866 866 868 872 871 860 849 835 823 819 798
503 509 511 537 565 574 577 626 624 623 635 648 661 671 672 691 724 723 743 769 789 832 871 869 867 867 867 869 874 867 854 840 827 820 810
506 514 519 539 563 567 568 605 617 618 619 620 636 671 671 672 694 722 732 769 770 826 855 875 869 867 867 868 870 865 851 838 827 821 819
510 514 524 543 560 561 570 585 595 602 611 615 619 621 672 673 674 708 721 755 771 800 829 875 867 866 867 867 868 857 841 831 825 821 819
514 513 530 550 559 564 570 577 583 588 595 605 614 619 648 675 676 696 722 750 771 773 822 836 860 864 866 867 853 835 827 823 821 820 819
512 517 533 555 560 566 570 574 576 579 584 594 608 616 622 675 676 692 722 745 771 774 821 821 828 839 841 836 818 818 818 818 819 819 819
511 518 533 555 561 567 571 573 573 573 578 587 601 613 620 673 674 690 720 743 772 775 805 821 822 824 823 817 818 818 818 818 819 819 819
512 516 533 555 561 567 571 573 571 555 574 585 599 613 619 671 672 689 720 737 771 775 791 814 823 822 819 818 818 807 798 787 786 786 785
515 512 532 556 560 567 572 574 574 573 578 588 601 613 619 670 671 687 719 734 770 773 781 795 805 809 802 793 784 768 768 769 769 769 769
519 516 531 557 555 567 574 578 579 581 585 595 608 614 637 669 670 686 710 730 753 773 775 780 784 782 770 768 756 752 746 744 745 746 752
527 524 545 559 555 572 583 588 589 593 600 608 614 615 653 669 669 690 717 727 744 758 764 764 762 759 748 736 730 718 719 719 719 719 728
532 530 573 568 573 586 601 609 608 612 617 619 618 667 669 670 678 698 715 724 736 743 745 743 737 731 722 719 718 719 719 714 714 715 720
537 562 577 580 589 604 616 621 624 624 624 622 669 668 670 670 691 713 714 721 728 730 725 724 722 715 712 710 706 703 702 702 703 706 710
539 551 578 587 600 615 620 628 632 635 642 657 669 669 670 686 704 712 715 720 723 723 718 713 705 699 694 691 688 686 686 687 690 695 700
536 559 572 589 614 616 624 634 641 647 655 668 669 670 684 699 713 714 717 721 723 717 707 698 690 683 676 670 669 668 668 669 676 683 690
525 525 570 584 613 615 626 637 648 658 667 669 674 683 695 719 717 719 721 719 713 704 694 685 677 669 670 670 668 667 666 667 670 671 681
516 532 559 564 598 615 626 638 654 666 668 672 679 687 697 710 713 715 715 708 701 693 681 670 669 669 669 668 666 663 662 666 671 673 673
509 520 543 562 574 614 622 634 653 666 668 671 678 685 692 697 701 703 702 698 689 676 669 668 666 664 662 662 661 661 661 665 671 672 673
479 512 529 546 558 579 614 624 640 655 662 670 674 679 683 684 690 693 688 684 673 669 664 659 656 655 655 656 657 658 660 663 668 670 671
462 500 518 532 541 547 578 615 621 636 644 652 663 678 683 685 683 681 678 673 662 655 650 647 645 646 647 649 652 654 656 659 664 668 669
462 493 511 519 522 536 545 560 621 625 629 633 643 655 662 661 670 669 653 646 640 637 634 633 633 634 639 643 647 650 652 655 661 667 667
471 497 511 507 514 528 547 559 591 610 615 619 618 627 632 632 627 617 617 617 617 618 618 618 618 619 631 637 642 647 651 654 658 664 668
""".strip().splitlines()], float) / 10.0
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
