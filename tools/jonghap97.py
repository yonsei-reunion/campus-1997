"""종합관 · 외솔관2 · 인문관 둘레의 1997년 땅과 건물 (#189; reference/고증/3.1 「종합관 · 외솔관2 · 인문관: 1997년의 땅과
건물」).  tools/build_campus.py 가 부른다.

    took, info = jonghap97.grade(Hn, X, Y, FIXED, halls, keep, fill)     # 심기가 끝난 뒤, 저장 바로 앞
    jonghap97.OUTLINE · FLOORS · DOORS                                    # 세 건물의 1997년 외곽선 · 바닥 · 층 · 문
    jonghap97.trees_aside(trees, halls)                                   # 포장된 마당 위의 나무를 목록 제자리에서

Frames: campus metres, x east, y north.  (u, v): 종합관's own frame, o OSM's south-west corner of its west wing, u east
along the slab's south face, v north (uv · xy below); 외솔관2 and 인문관 stand square to it in the scans (OSM's 인문관
is 0.85 degrees off).  Every absolute height is 게임 기준 (해발 + T, T = 0.05 + 0.522 x/100 + 0.248 y/100 m: tools/aerial97.py survey_dz); each constant
has its place beside it (`# @ (x, y)`), GRID its nodes' (GRID_X0, GRID_Y0, GRID_D).

What the game had: the surface model's ground, 8 - 10 m too high round 외솔관2's west end, brought down in #110 to
6 - 9 m too low (it took 외솔관2's lowest corner + 4.5 m for the car park); the three halls on OSM's outlines, their
floors at the lowest corner of that ground.  What the 1997-07-28 scans (six frames, heights frame pair by frame pair,
edges read on each roof's own plane from opposite flight lines) and the 1:5000 survey (2006 · 2024) have:

- 종합관: a slab 63.4 x 22.6 m, its roof's surface at 89.6 m (the parapet 0.9 m over it), four storeys over the yard
  north of it (72.6 m) on an open storey at 69.3 m; across its east end a low block of two storeys (1994's 400평: 19.4
  x 58.3 m with the slab's end, its roof 69.1 m, its floor the road east of it, 61.25 m).  OSM's outline has the low
  block 7.6 m too far east and 3 - 5 m short on the south.
- 외솔관2: two storeys (연혁: 지하 1층 · 지상 1층, 333.65평 = 2 x 551 m2) on the two of the corridor under them, 42.9 x
  12.95 m (556 m2), a low white gabled roof (eaves 77.3 m, ridge 78.4 m); its west end stands 7.5 m over the ground there
  (the 2026 roadview), its south wall 18.7 m over the lane behind 인문관.
- 인문관: 67.7 x 16.3 m with two shallow blocks standing 2.4 m out of its north face (1,186 m2; 연혁 2,171.60평 = 6 x
  1,196 m2; OSM's east 3.8 m are its porch), its roof 82.5 m: six storeys of 4.0 m on the road along its south face
  (58.4 m), not on the ground 2.5 m under it at OSM's south-east corner.
- the 2006 survey's own outlines of the three (수치지형도 layer 4111) lie on these within 1 m once moved (+0.6, -0.8) m
  in (u, v), the T of 종합관 and 인문관's two blocks included.
- the ground: the road east of 종합관 level at 61.25 m (photos; survey spots 60.24 · 60.54 m 해발), falling south to
  54.3 m before 인문관's east end; the paved yard north of the slab 72.6 m to u 30, a terrace at the low block's roof
  (69.1 m) between them and the slab; the road from the yard down to the east road falls 8 m in its first 14 m (the
  photos and the 2006 contours alike), then runs level; the lane behind 인문관 and round its west end under 60 m
  해발 (both surveys' 60 · 65 m contours run along 외솔관2's south wall and wrap 인문관's west end); the wooded hill
  north-west of the halls up to 102 m 해발 (the game had 87 m).

GRID: the 2006 survey's surface (its contours with its spot heights, 2.5 m) + T at the game's 5 m nodes, for the
woods (HILL) and the slope south-east of the halls (SE), where no photo sees the ground or the photos agree with it
(the roads east of 인문관 within 0.5 m).  ZONES · STRIPS: the levels and profiles read from the photos.
Nothing here draws from build_campus.py's `rng`.
"""
import numpy as np
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
PODIUM = 990070                                                 # 종합관's low east block (1994)
SLAB_UV = (-1.6, 61.8, 0.0, 22.6)
PODIUM_UV = (45.2, 64.6, -17.5, 40.8)
OESOL2_UV = (-4.5, 38.4, -18.25, -5.3)
INMUN_UV = [(-29.3, -42.8), (38.4, -42.8), (38.4, -24.1), (16.8, -24.1), (16.8, -26.5), (-16.4, -26.5), (-16.4, -24.1),
            (-29.3, -24.1)]                                     # (the two blocks out of its north face; no porch)
OUTLINE = {JONGHAP: rect(*SLAB_UV), PODIUM: rect(*PODIUM_UV), OESOL2: rect(*OESOL2_UV), INMUN: poly(INMUN_UV)}
# floors: base (게임 기준), storeys, storey height.  종합관: the open storey (69.35) and four over it, the roof's surface
# 89.6; the low block's two from the east road (61.25) and one under them at its south end, where the ground before
# 인문관 is a storey lower (its roof 69.2; the photos 69.1: 0.1 over, clear of the terrace beside it); 외솔관2: the
# corridor's two and its own two, eaves 77.3; 인문관: six from the south road, the roof 82.4
FLOORS = {JONGHAP: dict(base=69.35, levels=5, fh=4.05),         # @ (-58, 301)
          PODIUM: dict(base=57.275, levels=3, fh=3.975),        # @ (-30, 293)
          OESOL2: dict(base=61.3, levels=4, fh=4.0),            # @ (-74, 282)
          INMUN: dict(base=58.4, levels=6, fh=4.0)}             # @ (-92, 262)
OESOL2_ROOF = dict(mat='plaster_white', pitch=0.165, over=0.5, gable=True)      # (the ridge 1.15 m over the eaves)
# doors (the place on the wall, generic.porch's options): 종합관 from the yard, on the first storey over the open one;
# the low block from the east road; 외솔관2 at its west end (the storey the ground there reaches); 인문관 in its east
# wall under the porch
DOORS = {JONGHAP: (xy(16.0, 22.6), dict(floor=1)), PODIUM: (xy(64.6, 31.5), {}),
         OESOL2: (xy(-4.5, -11.8), {}), INMUN: (xy(38.4, -34.5), {})}

# --- 게임 기준 heights of the ground ------------------------------------------------------------------------------------
Z_EAST = 61.25                    # the road east of 종합관, level                    @ (-4, 310)
Z_YARD = 72.6                     # the paved yard north of the slab                  @ (-66, 325)
Z_TERR = 69.1                     # the terrace west of the low block's north wing    @ (-46, 318)
Z_ROOF = 68.9                     # under the low block's roof, by the terrace        @ (-40, 310)
Z_COURT = 69.3                    # the passage between the slab and 외솔관2, its east  @ (-52, 287)
Z_PASS_W = 72.0                   # ... its west mouth                                @ (-92, 296)
Z_OESOL_W = 69.8                  # the ground at 외솔관2's west end                    @ (-97, 287)
Z_LANE = 58.6                     # the lane behind 인문관 and round its west end        @ (-80, 272)
Z_INMUN = 58.4                    # 인문관's floor: the road along its south face       @ (-92, 250)
Z_APRON = ((38.0, 58.4), (46.0, 58.2), (82.0, 54.3))      # (u, z) before 인문관's east end   @ (-50 .. -17, 252 .. 243)
# (v, z) east of the low block's south wing, the east road's heights abreast     @ (-22, 269) .. (-12, 292)
Z_SWING_E = ((-17.5, 56.6), (-14.4, 57.0), (-10.4, 57.6), (-6.5, 58.6), (-2.4, 59.2), (1.6, 59.7), (9.5, 60.7), (12.0, 61.25))
# profiles (x, y, z) along OSM's ways, the photos' heights (the survey's within 0.5 m)
RAMP = [(27.0, 38.1, 72.3), (31.0, 39.8, 70.0), (35.0, 41.4, 67.0), (38.1, 42.7, 65.2), (43.8, 43.8, 63.6),
        (48.0, 43.9, 62.4), (51.0, 43.9, 61.4), (56.0, 44.0, 61.3), (66.0, 44.2, 61.25)]        # (u, v, z): 61's east part
EAST_ROAD = [(-8.6, 290.7, 61.0), (-9.6, 286.8, 60.7), (-11.2, 279.0, 59.7), (-12.0, 275.1, 59.2), (-12.8, 271.1, 58.6),
             (-13.5, 267.2, 57.6), (-14.3, 263.3, 57.0), (-15.1, 259.4, 55.8), (-15.9, 255.4, 54.7), (-16.7, 251.5, 54.3),
             (-17.6, 247.6, 54.2), (-18.7, 243.8, 53.8), (-19.7, 239.9, 53.5), (-20.5, 236.0, 53.0), (-21.4, 232.1, 52.6)]
SW_ROAD = [(-88.0, 318.1, 72.6), (-103.6, 307.7, 73.0), (-116.9, 298.8, 73.0), (-123.5, 294.4, 72.4), (-129.8, 289.6, 71.6),
           (-131.0, 285.8, 70.4), (-132.1, 282.0, 69.6), (-133.3, 278.1, 68.9), (-134.4, 274.3, 68.4), (-135.6, 270.5, 68.0),
           (-136.7, 266.6, 67.8), (-137.9, 262.8, 67.6)]
GRID_X0, GRID_Y0, GRID_D = -225.0, 230.0, 5.0     # (the grid's south-west node, spacing: the game's 5 m nodes)
GRID = np.array([[int(v) for v in r.split()] for r in """
644 695 695 695 754 779 796 798 797 746 697 747 738 719 698 684 666 649 649 599 600 597 592 588 584 579 575 570 565 559 552 552 550 549 548 545 543 540 536 530 524 518 513 509 506 506 456 457 456
695 695 695 745 768 796 796 807 797 764 725 697 748 729 706 689 672 655 649 618 600 598 594 590 586 582 578 574 569 564 558 555 553 552 553 551 550 549 547 539 532 525 519 514 509 506 457 457 457
695 695 745 761 783 796 785 786 793 778 743 710 728 739 714 693 677 661 649 627 600 598 595 592 588 585 582 578 574 570 566 563 560 557 554 554 554 556 555 546 538 532 525 519 512 506 487 457 457
695 725 751 772 796 773 762 764 782 786 760 727 698 748 723 699 682 665 650 650 600 599 596 594 591 588 585 583 580 577 574 571 569 567 565 564 563 561 555 551 544 538 532 524 516 508 507 457 457
715 745 753 774 746 746 769 766 747 797 783 748 698 728 732 699 686 669 654 650 600 599 597 595 593 591 589 587 585 583 581 579 577 576 575 575 573 569 561 555 550 545 539 530 518 507 506 482 458
733 746 747 779 783 796 824 847 797 747 798 778 730 698 740 712 691 672 654 650 600 600 599 597 596 595 593 592 590 589 587 586 586 586 586 586 585 583 571 555 556 552 549 541 521 506 503 497 458
745 746 746 796 808 829 848 849 849 848 781 798 772 699 749 720 699 675 650 650 600 601 600 599 599 598 597 596 595 595 594 594 594 595 596 598 599 605 605 605 584 556 556 556 531 506 505 505 508
745 746 796 809 826 847 852 855 854 844 798 781 798 765 699 730 700 682 658 625 601 601 601 601 601 601 601 601 601 600 600 600 601 605 604 613 605 630 630 656 606 582 567 557 542 507 507 507 508
745 746 802 818 837 851 860 865 865 856 833 798 765 799 749 749 708 691 666 650 601 602 602 603 604 605 605 606 606 607 604 610 604 629 621 630 647 651 649 654 606 595 576 557 557 522 507 507 508
746 796 807 827 847 858 872 881 885 882 869 856 799 770 799 725 701 700 676 651 601 603 603 605 607 610 608 613 603 628 653 644 649 638 631 639 647 651 653 655 631 606 586 566 557 539 508 508 508
746 796 816 836 847 868 886 898 888 891 898 878 859 799 799 775 700 700 688 663 601 606 601 612 602 636 653 648 657 658 660 659 656 651 647 649 652 654 655 656 656 606 600 582 557 557 531 517 508
746 803 826 847 857 879 897 872 861 864 882 899 880 861 849 800 750 700 701 701 639 626 652 652 677 702 680 674 676 679 678 672 666 662 659 658 658 658 658 657 656 607 607 607 557 558 547 531 520
746 807 832 848 861 897 858 828 821 822 831 860 899 887 862 850 783 750 729 715 701 701 702 702 702 702 698 693 695 704 704 684 676 671 668 665 664 662 661 659 657 625 607 607 577 558 558 541 528
746 809 834 844 844 847 815 821 824 826 818 799 831 899 888 864 813 784 751 739 728 721 715 710 708 705 703 703 703 702 697 690 684 679 675 672 669 667 664 661 658 638 607 607 608 558 558 549 536
776 809 834 834 797 876 866 868 878 887 893 865 832 800 866 900 850 819 776 751 751 739 732 726 720 714 706 703 702 701 698 693 689 686 682 679 675 671 667 663 659 657 607 608 608 558 558 554 542
771 807 834 828 797 895 898 910 930 949 947 949 949 878 800 800 901 876 851 801 752 752 747 740 733 724 712 703 702 701 699 697 694 692 690 687 681 675 669 664 660 657 607 608 608 579 558 559 547
771 806 833 824 844 904 921 948 946 942 938 935 936 941 950 890 801 851 901 851 827 802 768 752 747 738 724 704 703 702 701 700 699 699 698 697 688 679 671 665 661 658 607 608 610 608 558 559 552
747 806 831 847 844 904 931 947 941 934 926 919 913 911 912 927 951 907 850 852 802 852 802 787 766 753 741 719 704 703 703 703 704 705 705 705 695 681 671 664 660 658 633 608 609 608 573 559 554
747 796 824 847 823 898 930 946 937 926 913 900 888 877 865 851 851 951 951 878 902 852 836 819 803 778 753 754 704 704 705 708 707 705 706 706 697 678 667 661 656 658 658 608 608 608 571 559 555
748 797 817 839 798 898 918 949 936 920 901 881 862 850 902 906 896 886 917 952 852 852 903 865 853 803 791 770 754 741 732 724 713 705 706 706 706 666 658 657 632 608 608 608 604 589 559 559 557
747 777 807 823 823 868 899 949 939 916 888 861 850 998 1001 979 954 932 927 938 952 913 895 878 853 853 837 804 784 766 755 745 723 706 706 685 656 657 645 607 607 608 608 608 600 585 565 559 559
747 747 798 809 819 850 899 924 949 917 876 850 930 994 967 966 1001 957 918 920 931 953 929 913 903 854 850 854 804 794 774 755 755 725 706 656 656 652 636 614 608 608 608 608 602 586 569 559 560
738 747 784 801 804 824 876 899 949 927 877 871 927 1001 901 901 928 970 1002 902 902 903 953 933 917 904 854 854 855 819 805 785 756 756 706 668 657 647 634 617 608 608 608 608 604 591 574 559 560
730 748 765 798 799 799 861 899 928 950 884 871 905 901 947 941 949 967 989 1002 956 924 903 946 929 914 904 854 855 840 817 805 785 756 706 672 657 648 635 621 608 608 608 609 609 598 582 560 560
722 740 748 778 798 799 824 870 899 931 850 879 898 935 1001 966 956 957 952 977 1003 954 916 953 936 920 904 855 857 855 830 811 806 756 706 682 657 652 639 624 608 608 608 609 609 609 598 569 560
715 733 748 763 790 799 799 833 868 892 900 926 904 938 1001 970 952 957 959 955 1003 977 930 929 943 925 909 880 862 855 838 816 806 767 756 707 657 657 644 627 608 608 609 609 609 609 610 577 560
707 725 742 748 777 799 799 800 846 881 850 951 901 944 1001 952 959 978 979 962 953 1003 948 904 948 929 908 880 861 857 844 818 806 772 757 707 678 657 649 632 614 608 609 609 609 609 610 582 560
704 718 734 749 764 790 799 800 829 882 875 914 901 939 970 952 967 984 985 967 953 1003 961 904 954 932 914 905 856 856 856 816 806 773 757 707 707 669 658 637 618 609 609 609 609 610 600 582 560
698 710 725 742 749 777 800 800 815 859 901 900 926 941 954 959 969 977 977 968 957 985 974 920 954 932 916 905 855 856 856 806 806 773 757 707 707 681 658 643 624 609 609 609 609 610 601 585 568
698 698 712 733 749 764 790 800 800 838 863 893 918 949 951 959 970 977 977 972 961 977 980 934 938 925 914 905 855 856 856 806 806 773 757 718 707 685 658 649 630 609 609 609 610 610 603 588 571
687 695 705 724 743 750 774 800 800 830 849 901 919 951 951 961 978 983 984 981 974 954 982 956 929 915 910 905 856 856 856 806 807 773 757 723 708 708 658 654 639 609 609 609 610 610 604 593 578
675 688 699 715 734 750 750 800 800 825 851 881 914 937 947 964 1002 995 993 993 997 987 967 954 922 907 907 905 856 856 845 806 807 774 757 723 708 708 686 659 659 659 609 610 610 610 607 600 589
668 684 696 706 724 743 750 775 801 818 851 851 902 920 940 959 981 1003 1000 1001 1004 965 955 954 921 905 906 890 856 856 841 807 807 774 747 721 708 708 697 659 659 659 609 610 610 610 610 611 611
659 682 699 699 714 736 748 750 801 814 839 851 902 902 928 952 962 979 989 989 978 962 954 939 919 905 905 884 856 856 842 817 807 774 747 722 708 708 708 671 659 659 660 626 614 610 611 611 611
649 669 689 699 713 737 749 751 777 808 832 852 882 902 913 940 953 960 967 968 962 954 945 931 917 905 897 879 861 856 840 819 807 774 758 724 708 708 709 684 659 659 660 641 623 610 611 611 611
649 658 686 700 713 736 750 751 751 801 825 852 864 902 902 916 953 953 954 956 954 946 934 922 911 905 891 877 863 856 838 821 807 776 758 725 708 708 709 697 659 660 660 654 640 620 611 611 611
649 658 685 700 710 727 744 751 751 801 815 842 852 875 903 903 915 931 938 939 934 928 921 913 905 901 887 874 862 852 836 819 807 782 758 728 708 709 709 709 679 660 660 660 660 638 611 611 611
649 666 685 700 700 720 734 751 748 751 802 825 852 852 867 890 903 904 911 915 914 912 909 905 905 895 881 869 859 849 833 816 807 786 758 733 708 709 709 709 692 660 660 660 661 661 628 611 612
649 670 690 700 704 714 725 735 741 746 752 802 827 853 853 863 875 887 892 895 904 905 905 905 894 883 872 863 856 848 832 815 808 791 758 740 709 709 709 709 699 678 665 660 661 661 643 611 612
649 676 700 700 700 708 717 725 733 740 748 752 802 823 837 848 853 861 868 875 881 883 884 882 876 869 862 856 857 848 830 814 808 791 758 758 709 709 709 709 710 690 674 661 661 661 661 624 612
649 688 700 700 700 701 709 717 726 734 742 749 753 803 822 835 846 853 854 854 862 864 864 864 861 856 856 856 857 847 827 808 808 791 758 759 728 709 709 710 710 697 684 670 661 661 661 642 612
700 700 700 700 701 701 701 710 718 727 736 744 750 753 810 824 841 854 854 854 855 855 855 856 856 856 856 857 857 845 823 808 808 791 758 759 745 725 709 710 710 705 696 683 661 661 662 662 612
700 700 700 700 701 701 701 702 711 721 730 739 747 752 803 811 827 844 854 855 855 855 855 856 856 856 856 857 857 839 815 808 808 791 759 759 751 736 722 710 710 710 711 703 688 677 662 662 662
""".strip().splitlines()], float) / 10.0
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
    """GRID, bilinear (게임 기준)"""
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


_pass = _lin(((-4.5, Z_PASS_W), (12.0, Z_COURT + 0.1), (45.2, Z_COURT), (52.0, Z_ROOF)))
_apron = _lin(Z_APRON)
# the ground's zones, each (name, outline in (u, v), height(u, v)); a later one over an earlier where they overlap.
# The zones run on under the halls' walls so that the ground is level up to them: the steps between the levels (the
# yard and the open storey, the passage and the lane 11 m under it, the terrace and the east road) fall inside the
# halls' outlines, where the 5 m grid's slopes are not seen.
ZONES = [
    ('west of the slab', poly([(-16.0, -3.0), (-1.6, -3.0), (-1.6, 17.5), (-5.0, 17.5), (-5.0, 24.0), (-16.0, 12.0)]), _const(Z_YARD)),
    ('외솔관2 west end', rect(-16.0, -4.5, -18.25, -3.0),
     lambda u, v: np.interp(v, [-12.0, -3.0], [Z_OESOL_W, Z_YARD])),
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
    ('lane', rect(-33.5, 46.0, -46.0, -19.6), _const(Z_LANE)),              # (behind 인문관 and round its west end)
    ('외솔관2 south', rect(2.0, 34.0, -18.25, -11.0), _const(Z_LANE)),
    ('인문관', rect(-29.3, 42.2, -45.5, -24.1), _const(Z_INMUN)),             # (its porch and the low strip along its south too)
    ('인문관 south-west', rect(-33.5, -17.7, -51.0, -42.8), _const(Z_INMUN)),  # (west and east of 인문관 남쪽 길, INM97)
    ('인문관 south-east', rect(31.3, 42.2, -53.0, -42.8), _const(Z_INMUN)),
]
# the yard's paving and the terrace on the game's map (paint); the trees the planting put on them step aside
PAVED = [poly([(-16.0, -3.0), (-1.6, -3.0), (-1.6, 22.6), (30.0, 22.6), (30.0, 40.5), (21.0, 43.5), (10.0, 40.0), (2.5, 31.0),
               (-5.0, 24.0), (-16.0, 12.0)]), rect(35.0, 45.2, 22.6, 40.5)]


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


def grade(Hn, X, Y, FIXED, halls, keep, fill):
    """GRID in HILL and SE, the zones and the roads' profiles round the three halls, the rest between and RING m round
    them one smooth surface (fill: harmonic_fill).  halls: the other halls' outlines (their feet stay), keep: nodes
    that stay as they are (인문관 남쪽 길).  #110's levels round 외솔관2 (FIXED there) give way.  Returns the nodes set
    (to be FIXED) and a summary."""
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
    # the survey's surface
    base = (shapely.contains_xy(HILL, X, Y) | shapely.contains_xy(SE, X, Y)) & ~stay & ~fixed
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
