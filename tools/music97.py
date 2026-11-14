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
- Nothing here draws from build_campus.py's `rng`.
"""
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
import shapely.ops
from shapely.ops import unary_union

# --- 게임 기준 heights (the one place to shift them all) ------------------------------------------------------------
PHOTO_DZ = (2.052, 0.522, 0.248)  # survey height + c + a x / 100 + b y / 100 = the game's datum (s134's plane)
AMPH_FLOOR = 59.6                 # 노천극장's floor (the 1997 scans)
ROAD = [(69.1, 146.2, 44.9),      # (x, y, height) on TR_E: 아펜젤러관's yard (the square's level, kept)
        (86.0, 164.6, 47.9),      # 2006 contour 45 m, 0.9 m off the road's middle
        (126.1, 211.5, 54.6),     # 2024 spot 51.34 m on the road
        (132.6, 222.4, 54.0),     # (between it and the 50 m contour 6.9 m off at (128.8, 231.1): 53.3)
        (141.5, 251.0, 53.4),     # 2005/2006 contour 50 m, 3 m off
        (149.7, 262.8, 52.6)]     # EAST_Q97's first photo height (the fork), as it was
GRID_X0, GRID_Y0, GRID_D = 115.0, 30.0, 5.0       # (the grid's south-west node, spacing: the game's 5 m nodes)
GRID = np.array([[int(v) for v in r.split()] for r in """
532 541 575 587 585 639 656 672 654 730 721 706 691 681 727 731 782 782 783 782 733 733 683 682 626 610 600 601 608 619 622 627 629 631 627
510 532 556 574 580 640 664 654 729 715 699 680 781 781 731 764 779 787 786 784 783 733 704 684 648 618 605 607 621 635 642 643 643 639 638
497 529 546 568 579 642 663 679 719 700 680 780 752 731 753 776 793 805 806 797 784 734 726 700 685 665 658 659 668 695 698 698 684 661 642
478 528 541 567 579 647 679 729 711 689 780 752 731 754 774 787 813 831 833 821 800 785 738 726 705 685 683 691 698 707 708 700 699 684 645
478 528 541 568 612 635 676 704 707 747 762 731 751 772 790 807 828 849 844 837 834 800 787 739 737 722 719 720 723 726 725 713 700 699 644
478 514 540 563 579 639 629 708 718 780 730 745 770 788 806 824 836 838 837 835 834 834 785 772 756 749 742 735 736 737 733 719 704 695 690
479 514 538 559 579 642 630 728 733 730 731 759 781 802 822 832 839 844 847 848 845 837 836 785 785 775 763 744 735 736 737 723 705 689 688
500 518 529 556 579 642 630 731 730 722 743 771 792 820 832 840 848 856 863 870 871 859 842 838 786 785 785 765 735 736 736 730 713 695 687
521 525 530 555 579 642 630 731 730 729 747 781 811 832 837 848 859 870 880 891 894 878 863 845 839 786 785 785 758 736 736 736 723 709 699
533 531 531 554 579 642 630 732 747 732 748 781 832 832 842 856 872 887 887 890 895 897 880 863 845 839 786 786 771 746 736 736 732 719 709
535 533 531 554 580 642 630 730 714 731 748 781 832 832 844 863 890 893 889 888 896 898 898 880 858 844 821 786 779 761 736 737 737 727 717
536 531 531 555 580 642 630 731 731 738 748 782 812 832 840 866 893 895 889 885 890 897 898 899 876 855 840 815 786 777 758 737 737 734 724
531 527 530 555 580 642 630 726 681 760 751 777 798 821 833 835 891 885 880 881 887 895 898 898 889 867 842 829 807 786 787 753 737 737 731
522 526 530 554 580 641 631 731 681 782 783 785 797 815 836 834 836 851 866 883 895 898 898 898 896 877 856 837 826 802 787 787 762 737 738
519 526 529 553 578 630 667 700 709 734 758 786 810 818 827 837 835 835 854 892 896 898 898 897 895 885 866 847 837 825 800 787 787 763 752
519 526 528 551 577 626 643 693 690 715 749 758 760 810 808 825 837 835 839 900 899 899 899 898 894 891 875 861 849 840 826 800 786 779 763
520 526 528 551 580 620 646 646 673 694 699 755 762 756 803 801 821 837 837 859 900 900 900 896 891 888 885 876 867 851 840 826 802 787 788
521 526 529 554 587 596 633 643 647 696 697 701 752 756 768 783 796 806 835 837 865 892 891 888 887 887 892 885 876 866 850 839 838 804 788
521 527 529 556 589 604 618 644 648 682 694 695 696 747 752 752 746 791 801 822 836 874 886 886 886 887 890 891 881 873 860 846 839 827 799
522 527 529 556 587 600 601 650 648 663 676 691 691 693 721 747 746 758 790 788 836 861 886 886 886 886 888 892 891 880 869 855 843 839 818
523 529 531 557 585 594 597 646 644 643 655 668 681 691 692 711 744 743 763 789 809 852 891 889 887 887 887 889 894 887 874 860 847 840 830
526 534 539 559 583 587 588 625 637 638 639 640 656 691 691 692 714 742 752 789 790 846 875 895 889 887 887 888 890 885 871 858 847 841 839
530 534 544 563 580 581 590 605 615 622 631 635 639 641 692 693 694 728 741 775 791 820 849 895 887 886 887 887 888 877 861 851 845 841 839
534 533 550 570 579 584 590 597 603 608 615 625 634 639 668 695 696 716 742 770 791 793 842 856 880 884 886 887 873 855 847 843 841 840 839
532 537 553 575 580 586 590 594 596 599 604 614 628 636 642 695 696 712 742 765 791 794 841 841 848 859 861 856 838 838 838 838 839 839 839
531 538 553 575 581 587 591 593 593 593 598 607 621 633 640 693 694 710 740 763 792 795 825 841 842 844 843 837 838 838 838 838 839 839 839
532 536 553 575 581 587 591 593 591 575 594 605 619 633 639 691 692 709 740 757 791 795 811 834 843 842 839 838 838 827 818 807 806 806 805
535 532 552 576 580 587 592 594 594 593 598 608 621 633 639 690 691 707 739 754 790 793 801 815 825 829 822 813 804 788 788 789 789 789 789
539 536 551 577 575 587 594 598 599 601 605 615 628 634 657 689 690 706 730 750 773 793 795 800 804 802 790 788 776 772 766 764 765 766 772
547 544 565 579 575 592 603 608 609 613 620 628 634 635 673 689 689 710 737 747 764 778 784 784 782 779 768 756 750 738 739 739 739 739 748
552 550 593 588 593 606 621 629 628 632 637 639 638 687 689 690 698 718 735 744 756 763 765 763 757 751 742 739 738 739 739 734 734 735 740
557 582 597 600 609 624 636 641 644 644 644 642 689 688 690 690 711 733 734 741 748 750 745 744 742 735 732 730 726 723 722 722 723 726 730
559 571 598 607 620 635 640 648 652 655 662 677 689 689 690 706 724 732 735 740 743 743 738 733 725 719 714 711 708 706 706 707 710 715 720
556 579 592 609 634 636 644 654 661 667 675 688 689 690 704 719 733 734 737 741 743 737 727 718 710 703 696 690 689 688 688 689 696 703 710
545 545 590 604 633 635 646 657 668 678 687 689 694 703 715 739 737 739 741 739 733 724 714 705 697 689 690 690 688 687 686 687 690 691 701
536 552 579 584 618 635 646 658 674 686 688 692 699 707 717 730 733 735 735 728 721 713 701 690 689 689 689 688 686 683 682 686 691 693 693
529 540 563 582 594 634 642 654 673 686 688 691 698 705 712 717 721 723 722 718 709 696 689 688 686 684 682 682 681 681 681 685 691 692 693
499 532 549 566 578 599 634 644 660 675 682 690 694 699 703 704 710 713 708 704 693 689 684 679 676 675 675 676 677 678 680 683 688 690 691
482 520 538 552 561 567 598 635 641 656 664 672 683 698 703 705 703 701 698 693 682 675 670 667 665 666 667 669 672 674 676 679 684 688 689
482 513 531 539 542 556 565 580 641 645 649 653 663 675 682 681 690 689 673 666 660 657 654 653 653 654 659 663 667 670 672 675 681 687 687
491 517 531 527 534 548 567 579 611 630 635 639 638 647 652 652 647 637 637 637 637 638 638 638 638 639 651 657 662 667 671 674 678 684 688
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
