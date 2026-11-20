"""동문과 그 둘레 (reference/고증/3.26_동문.md).  tools/build_campus.py 가 부른다.

    took, info = dongmun.grade(Hn, X, Y, FIXED, halls)    # 1997년 땅: 측량 면 + 사진 높이(심기가 끝난 뒤)
    woods, walk = dongmun.splat_paint()                   # 본 땅 지도(x < 640) 쪽: 언덕 숲 바닥, 청송길 남쪽 보도
    tsplat.update(dongmun.pack(png, dongmun.draw_map(), tsplat))   # 동쪽 조각의 땅 지도(동네 · 신촌 로터리 지도와 한 장)
    dongmun.houses(ground)            # 1997년의 법현학사 두 덩이 · 수위실 · 문 밖 동네 집(건물 목록 끝)
    dongmun.gate()                    # campus.json dongmun: 문 기둥 둘, 요금정산소, 길가 옹벽(blender/landmarks.py dongmun)
    dongmun.trees(trees, halls)       # 언덕 숲의 나무(나무 목록 끝), dongmun.props() 가로등, dongmun.paint() 노면 표시

Frame: campus metres, x east, y north.  55 동문 on the 1990 and 1995 maps, 78 on the 2000 map; OSM 2026's gate nodes
(696.3, 238.8) · (700.7, 237.7) on 청송길 where it leaves the campus for 연대동문길 and the town of 대신동 · 봉원동.

- The 1997-07-28 scans: only course 27 (27/15 · 27/16 · 27/17) sees it.  The gate's two white piers either side of the
  road at 56.3 m (their tops 2.7 - 2.9 m over it), the lodge's dark hipped roof east of the east pier, a white hump
  across the road just outside, a toll island with a booth 30 m inside, the woods on the knoll north of the road and
  법현학사's two flat roofs south of it, the town's houses beyond.
- Heights: the photo pairs (27/15 · 27/16 · 27/17, and the winter 1996 frames) give the open ground within 0.2 - 0.3 m of
  the 1:5000 survey's spot heights on the roads (55.65 · 52.7 · 57.54 m), the woods' floor none: under the woods GRID is
  the 2006 survey's contours and spots (the knoll's top 97.2 m, both surveys; the game had 80 m), nudged to the photos'
  open-ground points (Gaussian, sigma 5 m), the flyover's deck (봉원고가, +4.5 m) and the roofs left out.
- Nothing here draws from build_campus.py's `rng`; the trees are a stream of their own, at the trees' very end.
"""
# (every absolute height written in this file's code is above sea level, 해발: datum.up · up3 takes it up to the
# working datum the ground is laid on, 해발 + tilt, where it is read: tools/datum.py.  The heights quoted in the
# comments are 해발 too)
import math
import os
import random

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union, nearest_points

import datum

# the east patch's own ground map, packed beside the town's and the north patch's (web/src/terrain.js uERect); the
# main map (build_campus.py SPLAT, x < 640) keeps its rectangle and its pixels
ESPLAT = dict(x0=640.0, y0=140.0, x1=770.0, y1=350.0, res=0.5)
REGION = box(562.0, 137.0, 773.0, 363.0)        # (where grade() lays the 1997 ground)
TAPER = 25.0                                    # (eased into the game's ground over this much inside REGION's edge)
HALL_PAD, HALL_EASE = 3.0, 8.0                  # (the feet of the halls already there stay, eased round over HALL_EASE)

# GRID: the 1997 ground (해발, decimetres) on the game's 5 m nodes, x 560 .. 775, y 135 .. 365, rows south to north:
# the 2006 survey's contours (layers 7111 · 7114) and spot heights (7217) of 서울078, with the 2024 survey's spots
# (layer F0027217; the two on the flyover's deck left out), as one triangulated surface, shifted (+0.62, -0.86) m onto
# the photos' block (reference/고증/1.1.1 「평면의 틀」), then nudged to the 1997-07 and 1996-12 photo pairs' ground
# points (2,746 points 4 m under to 2.5 m over the survey: roofs, crowns and the flyover out; Gaussian sigma 5 m,
# prior 0.3)
GRID_X0, GRID_Y0, GRID_D = 560.0, 135.0, 5.0
GRID = np.array([[int(v) for v in r.split()] for r in """
478 475 473 473 479 481 479 470 460 457 451 449 448 450 453 454 451 449 449 450 452 454 455 458 460 468 474 477 479 478 473 471 476 486 492 493 499 508 516 522 528 533 536 541
484 482 480 481 483 484 483 474 462 460 454 451 452 454 456 455 452 451 451 452 454 454 454 452 454 467 476 481 482 482 480 475 477 485 488 492 495 504 510 515 528 540 546 550
488 487 486 486 485 485 484 478 473 465 459 453 454 457 458 459 458 453 452 453 455 457 458 456 455 464 476 483 485 485 485 482 482 482 486 491 494 497 503 509 529 551 559 560
491 490 488 487 486 486 488 490 486 475 465 463 464 464 459 460 460 458 455 454 456 458 460 461 463 462 473 483 488 490 489 490 490 483 485 491 493 491 500 511 538 563 563 563
493 492 490 489 489 490 494 493 495 485 473 471 473 470 465 459 458 457 457 459 458 459 461 465 469 466 474 484 490 494 495 497 494 488 486 491 493 492 489 515 556 565 564 564
496 495 494 494 494 493 493 493 493 494 482 479 473 473 469 464 461 459 459 459 460 460 462 466 470 470 476 486 492 496 500 498 498 497 494 492 494 494 492 509 563 566 564 564
501 499 496 495 496 500 500 499 497 496 493 484 475 472 471 467 466 465 466 463 461 464 464 463 465 469 475 482 488 493 500 500 501 502 502 496 495 496 497 502 553 566 564 565
506 504 502 501 503 508 510 506 505 503 498 489 480 474 472 470 469 469 468 467 466 469 467 464 464 468 473 477 482 489 498 502 504 505 506 501 496 498 499 503 515 565 564 564
510 508 507 507 511 517 517 511 509 508 504 496 485 480 475 472 471 469 469 470 471 474 472 470 467 466 471 473 477 486 498 506 507 508 509 508 501 498 500 504 507 539 564 565
514 513 513 516 522 525 524 518 514 513 511 506 498 489 480 476 475 474 473 473 476 480 478 475 471 469 470 474 476 486 497 506 510 511 512 513 510 501 500 500 498 504 555 563
524 521 523 529 533 534 531 527 522 522 525 526 521 514 501 484 481 480 479 479 480 485 483 479 476 474 473 475 479 486 495 504 512 514 515 516 516 512 500 494 493 494 520 556
537 537 540 542 543 543 542 540 538 541 544 544 543 543 540 532 513 488 486 483 479 482 484 483 482 481 480 479 482 487 492 501 512 517 517 518 518 517 503 493 494 495 497 532
547 549 551 551 552 553 553 553 554 556 556 556 554 552 550 548 545 542 526 493 482 481 483 482 481 485 490 488 484 487 488 499 512 518 520 520 520 519 508 497 498 498 497 520
556 558 559 561 562 564 565 566 565 566 565 563 561 558 556 555 553 550 545 538 519 490 485 478 475 483 494 495 491 486 488 497 515 521 521 522 521 519 509 500 500 501 500 516
565 564 565 568 572 573 575 575 574 573 572 571 570 566 563 562 560 557 552 547 541 537 518 491 478 482 492 495 494 491 491 497 516 521 522 522 521 516 505 501 501 501 500 509
572 571 571 574 578 581 582 582 580 582 586 588 588 584 579 579 575 568 561 555 550 545 541 535 513 494 493 496 496 496 496 496 508 518 521 521 518 509 501 500 500 500 499 503
577 578 578 582 585 586 588 591 594 600 611 619 623 621 619 620 614 596 572 564 558 554 552 546 542 539 521 505 500 500 497 495 497 506 512 513 508 502 500 500 500 500 502 504
581 586 589 593 594 592 595 601 614 626 636 643 650 654 655 655 651 642 618 588 569 564 562 553 548 549 548 541 524 499 494 492 490 497 501 502 501 500 500 500 500 501 504 505
590 596 601 602 600 600 606 623 636 645 659 679 699 698 694 690 686 675 658 640 616 576 568 558 551 554 555 550 546 534 511 503 500 498 499 500 500 500 500 500 500 501 503 516
603 606 608 606 605 607 626 642 655 680 701 720 736 737 730 726 720 706 685 667 651 634 599 576 563 563 560 557 552 543 529 515 505 499 501 500 505 505 505 505 505 507 512 526
610 613 615 616 616 628 644 670 696 727 746 756 760 761 759 754 748 739 718 695 678 664 649 620 581 572 566 562 558 552 537 523 512 504 505 507 512 512 513 513 514 516 519 525
612 618 625 627 633 649 684 719 736 748 764 769 772 772 771 770 766 757 748 738 717 696 683 663 634 592 573 566 562 558 547 533 519 512 515 517 521 521 525 528 529 527 528 531
618 623 630 640 651 686 727 748 754 769 778 781 783 783 783 785 783 765 755 753 756 742 710 692 663 633 595 573 567 563 554 539 529 525 530 531 532 530 532 536 538 538 538 541
628 632 636 647 679 717 750 756 770 791 799 800 798 796 798 802 798 774 765 762 763 761 744 714 686 659 628 581 571 566 557 546 540 540 541 542 541 529 527 531 534 537 544 550
641 645 648 664 697 735 751 762 779 806 816 821 822 816 817 821 812 786 780 778 778 771 758 740 707 680 650 588 577 570 560 549 550 552 550 551 549 527 520 524 527 529 539 549
657 661 659 684 712 743 757 771 790 820 833 840 842 837 832 828 815 800 794 791 788 785 771 757 725 694 661 602 581 572 563 552 552 556 558 560 557 532 520 520 520 521 529 544
677 683 687 701 719 742 766 785 809 837 849 856 859 853 831 820 816 812 808 803 798 793 789 769 732 696 664 613 581 572 565 558 554 557 557 560 558 533 520 518 518 518 523 537
696 704 708 712 722 742 774 802 830 853 866 875 883 878 851 843 837 828 819 814 809 805 801 779 732 691 661 614 584 578 572 569 558 560 560 559 556 533 523 520 519 520 522 532
709 711 715 720 727 744 778 810 836 861 882 894 903 896 880 874 867 852 839 827 825 821 810 785 734 692 659 614 592 586 582 579 564 565 564 563 556 537 526 523 521 521 522 530
714 715 718 724 733 748 775 807 836 857 883 903 904 902 902 899 888 875 860 847 839 828 812 788 743 699 667 629 602 593 591 587 568 568 568 563 557 541 530 525 523 522 525 530
720 721 724 729 737 750 772 809 840 858 880 906 914 918 919 914 903 888 868 851 837 825 809 783 741 701 669 647 623 599 593 592 573 568 564 560 556 538 531 525 523 524 527 531
728 729 733 738 746 756 773 816 845 860 880 912 926 928 926 920 904 886 865 847 832 819 805 775 732 693 663 652 632 609 593 587 574 567 563 561 553 538 532 527 523 526 529 532
738 740 744 749 759 768 778 828 850 860 879 912 935 941 938 927 911 888 866 848 831 814 799 766 720 675 653 643 628 613 599 587 576 567 563 559 546 538 533 529 527 526 530 533
750 753 759 763 767 778 791 844 860 866 881 914 940 951 953 939 917 890 867 848 829 809 789 753 713 649 641 632 623 612 600 593 581 570 565 558 544 539 534 531 529 527 530 533
773 772 770 770 775 788 796 848 865 876 886 909 934 951 962 955 928 894 868 847 825 800 774 740 704 647 640 631 622 615 606 603 590 580 572 563 550 541 537 534 531 532 532 533
798 789 780 780 788 800 824 844 857 875 888 897 920 947 959 954 930 892 865 844 818 788 759 725 683 644 642 634 626 620 612 607 598 586 575 567 556 547 541 536 534 535 534 536
824 819 808 806 814 831 836 843 858 874 886 893 896 921 942 945 929 893 864 842 814 777 745 710 674 650 645 639 631 624 615 606 597 586 578 575 571 557 544 538 537 537 537 539
847 846 834 827 833 840 843 851 865 876 883 885 887 893 915 930 921 896 871 849 811 770 735 701 678 661 649 640 632 623 613 604 597 587 582 585 582 572 549 540 540 540 540 541
858 857 849 839 843 852 857 862 870 877 882 881 884 886 892 906 907 888 868 850 810 766 730 697 679 662 648 641 633 620 607 603 596 587 586 589 585 577 556 542 541 541 541 544
870 869 865 858 859 863 866 866 869 877 881 883 884 883 885 887 887 877 860 837 801 755 721 700 680 657 646 644 636 622 606 601 595 589 589 593 589 579 559 545 543 543 547 552
882 881 876 873 870 869 870 870 869 875 881 883 884 881 878 875 872 864 850 821 785 745 724 703 687 656 645 645 636 624 612 607 601 593 590 594 591 578 559 548 546 548 555 563
894 891 888 884 878 874 873 873 872 872 873 878 879 873 867 863 861 853 829 799 764 737 722 707 683 655 643 641 634 624 616 614 607 597 592 592 589 576 560 553 551 554 567 581
915 911 909 901 885 879 877 876 875 873 870 870 868 860 855 852 850 824 794 772 745 730 717 704 677 659 649 643 635 627 625 618 612 603 594 592 587 574 564 558 556 563 584 592
936 935 936 931 910 886 880 878 878 875 870 868 865 855 847 838 813 787 763 747 735 723 713 698 671 659 654 646 640 636 630 622 612 603 602 598 592 579 570 565 563 577 594 599
959 959 962 959 944 918 887 882 882 877 873 867 863 848 825 813 787 767 750 743 730 718 708 693 672 662 653 653 648 639 631 622 607 601 602 603 600 587 578 573 571 587 601 604
984 985 987 982 968 948 920 888 886 880 874 868 857 838 818 799 778 758 750 740 728 716 706 696 682 666 652 652 646 637 627 617 606 600 601 601 601 597 590 584 583 593 601 603
1000 1000 1000 999 983 967 951 922 897 887 874 860 845 828 811 794 777 761 748 735 722 710 700 700 686 672 659 649 639 630 621 612 603 600 600 600 600 600 599 599 595 596 600 601
""".strip().split('\n')], float) / 10.0


def grid_z(x, y):
    """GRID, bilinear, on the working datum (해발 + datum.tilt)"""
    from scipy.ndimage import map_coordinates
    x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    z = map_coordinates(GRID, [(y.ravel() - GRID_Y0) / GRID_D, (x.ravel() - GRID_X0) / GRID_D], order=1, mode='nearest')
    z = z + datum.tilt(x.ravel(), y.ravel())
    return z.reshape(x.shape) if x.ndim else float(z[0])


# 청송길 from the game's road end by 제중학사 to where it meets 연대동문길 outside the gate (OSM 2026 way 338082883: on
# the 1997 scans' road within 0.3 - 0.6 m, the middle line 0.25 m left of it).  Its surface by s from the start: the
# three 1997 frames' heights along it (median within 4 m) -- 57.5 m by 제중학사, down to 55.2 m at s 50 - 60, up
# through the toll island (s 85 - 98) to the gate (56.4 m at s 120) and on to 57.2 m at the junction (survey 57.54 m at
# (720.5, 285.5), 2024)
ROAD_PTS = [(595.1, 207.9), (605.3, 202.6), (614.6, 199.7), (625.5, 197.7), (633.2, 198.0), (637.5, 199.7), (650.1, 205.5),
            (663.8, 212.9), (683.6, 226.5), (686.9, 229.4), (696.3, 238.8), (697.5, 240.5), (699.1, 245.4), (700.3, 249.1),
            (702.1, 257.4), (703.6, 262.5), (705.5, 266.6), (708.7, 271.3), (711.2, 273.8), (713.7, 276.1), (719.6, 280.4)]
ROAD_PROF = [(0.0, 57.46), (10.0, 56.75), (20.0, 56.0), (30.0, 55.59), (40.0, 55.3), (50.0, 55.23), (60.0, 55.24), (70.0, 55.34),
             (80.0, 55.52), (90.0, 55.79), (100.0, 55.88), (110.0, 56.09), (120.0, 56.36), (125.0, 56.46), (135.0, 57.0),
             (165.2, 57.2)]
ROAD_HALF = 4.0                 # (the dark asphalt 8 m kerb to kerb on the scans, -4.6 .. +3.4 m about OSM's line)
WALK = (4.0, 6.0, 0.0, 117.0)   # (the walk south of it, offsets right of travel, s from .. to: lamps' shadows on it)
LAMPS_S = (8.0, 30.0, 52.0, 74.0, 102.0)
# 연대동문길 outside the gate (OSM 472659166): from 성산로's side south-west of the gate up past it to 봉원동; the 1997
# pairs' heights along it (44.4 m by 성산로, 48.5 m at y 200 = the survey's 48.45, 57.2 m at the junction, 62.4 m at
# y 333); 6 m of asphalt, the parking along its west side 4.5 m more (cars in a row on the 1997 scans, y 205 - 275)
LANE = [(645.8, 126.4, 44.4), (667.2, 157.4, 45.5), (699.1, 201.6, 48.5), (707.8, 213.7, 50.0), (721.2, 243.9, 52.3),
        (722.4, 269.1, 55.2), (719.6, 280.4, 57.2), (717.2, 291.6, 57.6), (705.0, 333.0, 62.4)]
LANE_HALF = 3.0
LANE_BAY = Polygon([(708.6, 206.0), (712.0, 205.0), (719.0, 221.0), (718.4, 244.0), (719.2, 270.0), (716.0, 276.0), (712.4, 272.5),
                    (713.5, 246.0), (712.8, 228.0)])
# the road east from the junction down to 봉원동 사거리 under the flyover (OSM 338082883's east end): 1997 heights
TOWN_RD = [(719.6, 280.4, 57.2), (726.5, 286.6, 56.1), (748.2, 290.9, 53.2), (757.0, 292.5, 52.7), (772.0, 295.4, 52.6)]
TOWN_HALF = 4.0
JUNCTION = Polygon([(711.0, 272.0), (716.5, 271.0), (724.5, 277.5), (726.0, 289.5), (715.5, 292.5), (709.0, 283.5)])
# the planted island between 청송길 and the parking (topiary and small trees on the 1997 scans and in 2010)
ISLAND = Polygon([(705.0, 246.0), (708.6, 238.0), (712.0, 241.0), (712.4, 262.0), (711.5, 271.0), (708.4, 268.0), (705.6, 259.0)])
# 성산로 east of all this, at its ground (the 1997 scans: eight lanes; OSM 2026's carriageways and links), half widths
SSR = [((616.1, 6.3), (638.4, 39.9), (674.1, 89.5), (700.1, 131.1), (764.5, 244.2), (814.4, 333.2), 6.5),
       ((808.7, 336.4), (758.6, 247.6), (695.2, 136.0), (672.9, 100.5), (632.5, 43.9), (595.9, -2.6), 6.5),
       ((699.8, 118.0), (710.9, 135.9), (770.9, 243.0), (781.5, 261.3), (787.3, 269.7), 3.5),
       ((699.8, 118.0), (706.0, 123.5), (735.1, 159.0), (748.7, 180.7), (758.3, 199.6), (768.3, 226.0), (770.9, 243.0), 3.0),
       ((756.7, 286.9), (755.0, 266.5), (752.8, 258.4), (716.7, 190.2), (668.9, 109.4), 3.5),
       ((756.7, 286.9), (760.9, 277.6), (768.5, 269.8), (774.5, 267.0), (782.0, 266.7), (787.3, 269.7), 3.5)]
# the campus side of the boundary (the gate, the lodge, the knoll's east foot, 법현학사 and the slope south of the road):
# west of it the woods and the campus road, east and south the town
CAMPUS_SIDE = Polygon([(600.0, 166.0), (640.0, 166.0), (652.0, 176.0), (672.0, 180.0), (690.0, 186.0), (697.0, 205.0), (699.5, 226.0),
                       (702.5, 238.5), (697.0, 246.5), (691.0, 258.0), (686.5, 276.0), (679.5, 300.0), (673.5, 330.0), (668.0, 352.0),
                       (600.0, 352.0)])
# the bright band along the road's north edge between the asphalt and the woods (the 1997 scans: bare slope; 2010:
# rock, dry grass and a granite-block wall at the foot): s and offsets left of travel
BARE = (40.0, 117.0, ROAD_HALF, ROAD_HALF + 6.0)
WALL_S = (44.0, 116.5)          # (the granite-block wall at the foot of the slope, along the road's north edge)
WALL_OFF = ROAD_HALF + 0.3
# 법현학사 (1975, raised to three storeys in 1979, gone in 2015): the 2006 survey's outline (the same building as the
# 1997 roofs, within 0.8 m), split where the two roofs meet; roofs 54.8 m (west) and 56.3 m (east) on the 1997 scans,
# the stair tower between them and the bright box on the east roof 59.35 m; the ground by the road on the north 55.2 -
# 55.6 m, the floors coming out of the slope to the south (reference/고증/3.1.2.1)
BEOPHYEON = [
    (994000, ((654.7, 180.7), (674.2, 184.1), (672.9, 192.6), (665.4, 193.2), (652.9, 191.1)), 54.8),
    (994001, ((672.9, 192.6), (673.9, 186.2), (685.9, 188.3), (685.2, 192.0), (688.7, 192.1), (687.9, 197.2), (690.0, 197.5),
              (689.0, 203.7), (666.1, 199.8), (666.7, 196.4), (664.9, 196.1), (665.4, 193.2)), 56.3),
]
BEOPHYEON_TOPS = [(994002, ((665.2, 187.5), (670.2, 188.3), (669.1, 195.2), (664.1, 194.4)), 59.35),     # (the stair tower)
                  (994003, ((676.6, 190.5), (684.5, 191.8), (683.7, 196.7), (675.8, 195.4)), 59.35)]     # (the box on the roof)
# the lodge east of the east pier (the 2006 survey's outline; on the 1997 scans the dark hipped roof there; 2010
# roadview: one storey, light grey render, a door and a window towards the road, a dark shingle hipped roof)
LODGE_ID = 994010
LODGE = ((705.2, 228.6), (701.1, 230.9), (703.6, 236.0), (704.3, 238.5), (706.3, 239.1), (708.4, 238.2), (709.4, 236.3), (709.0, 234.8))
# the gate's two piers (the 1997 scans: white tops 2.7 - 2.9 m over the road where three frames agree on a 59 m plane;
# 2010 roadview: white concrete piers, each a ㄇ open to the road with the dark iron leaf folded in it, a globe lamp
# on top): centres, along the road (t), the road's side (n into the road)
PIERS = [dict(c=(694.5, 242.5), t=(0.39, 0.921), n=(0.921, -0.39)), dict(c=(700.6, 239.0), t=(0.39, 0.921), n=(-0.921, 0.39))]
PIER_L, PIER_W, PIER_H = 3.2, 1.5, 2.85
# the toll island 30 m inside (the 1997 scans: an island on the road's middle with hatched ends, a white booth's roof
# on it 3.2 x 2 m, lanes either side; 1994-11 paid parking and a toll on cars through 북문 ~ 동문: reference/고증/3.21)
TOLL = dict(pos=[673.3, 218.0], rot=round(math.atan2(13.6, 19.8), 4), size=[3.2, 1.5], height=2.4, island=[14.0, 1.8], bar=3.0)
# the white hump just outside the gate (the 1997 scans: a band across the road, 2.5 - 3 m deep, 8.5 m across)
HUMP = dict(xy=[700.0, 245.6], t=[0.31, 0.951], half=4.2, len=2.6)
# 문 밖 동네의 집 (OSM 2026 outlines, simplified 0.25 m): (OSM id, name, the roof's height on the 1997 scans or None)
# -- kept where a 1997 roof stands in the outline (three frames, 1.5 m windows) or, where the scans could not tell
# (the houses down by 성산로), the 2006 survey has the same house
HOUSES = [
    (1178743289, '', None, ((688.2, 153.9), (678.7, 139.5), (667.9, 145.9), (675.4, 154.4), (673.5, 155.6), (675.0, 157.0), (677.4, 155.4), (679.4, 159.1))),
    (1178743290, '', None, ((702.8, 177.1), (690.9, 158.1), (679.7, 166.0), (692.4, 182.2), (693.5, 181.8), (694.4, 183.1))),
    (1178743291, '', 54.2, ((700.2, 195.4), (707.7, 190.0), (703.4, 184.4), (706.0, 182.9), (703.1, 179.7), (694.0, 185.8))),
    (1178743292, '', 59.0, ((713.6, 213.6), (719.4, 210.9), (711.6, 199.2), (708.7, 204.3))),
    (1178743293, '', 70.6, ((739.1, 242.7), (722.9, 215.5), (719.0, 214.7), (715.9, 215.5), (713.4, 218.6), (725.6, 247.1), (735.5, 246.4))),
    (1178743294, '565', 56.9, ((739.9, 281.0), (741.7, 270.5), (741.8, 262.6), (739.8, 252.0), (730.6, 252.1), (729.1, 260.8), (728.5, 270.8), (729.8, 280.6))),
    (1178743312, '', None, ((649.3, 163.8), (654.8, 160.3), (646.0, 148.2), (639.5, 153.4))),
    (1178743313, '', None, ((657.8, 158.7), (663.0, 155.2), (653.5, 142.9), (647.8, 146.9))),
    (1359781926, '', 73.6, ((710.8, 294.4), (713.3, 282.4), (703.4, 280.5), (701.6, 292.8))),
    (1359781927, '', 75.2, ((690.2, 289.6), (698.0, 290.1), (699.9, 278.6), (692.0, 277.6))),
    (1359781928, '', 75.8, ((695.3, 312.6), (707.8, 314.4), (710.9, 300.6), (698.9, 299.7))),
    (1359781929, '', 76.4, ((686.2, 310.0), (692.8, 311.4), (696.4, 298.9), (689.4, 297.1))),
    (1359781930, '', 74.2, ((680.8, 327.7), (700.8, 331.1), (703.1, 317.5), (683.8, 314.3))),
    (1359781931, '', 74.2, ((685.9, 350.0), (696.9, 352.1), (700.0, 340.1), (687.9, 337.0))),
    (1359790834, '567-8', 64.6, ((720.7, 303.0), (732.3, 305.2), (733.1, 301.1), (735.6, 300.8), (736.8, 309.9), (743.4, 306.8), (741.9, 303.7),
                                 (741.5, 296.8), (725.7, 293.7), (722.2, 295.2))),
    (1359790835, '567', 67.4, ((750.4, 319.3), (740.8, 309.1), (737.1, 312.6), (735.7, 319.9), (749.7, 322.6))),
    (1359790836, '', 71.3, ((715.7, 316.6), (731.6, 319.9), (733.7, 307.3), (718.4, 303.9))),
    (1359790837, '', None, ((711.1, 329.6), (726.4, 332.2), (727.9, 323.6), (712.5, 321.0))),
    (1359790838, '', 62.1, ((729.5, 333.6), (738.9, 334.9), (740.0, 327.3), (730.6, 325.9))),
    (1359790839, '', 59.8, ((740.4, 334.1), (749.6, 335.5), (751.1, 326.1), (741.9, 324.7))),
    (1359790840, '', 67.0, ((726.8, 343.4), (736.3, 344.7), (737.7, 335.2), (728.7, 334.1))),
    (1359790841, '', 61.7, ((738.4, 346.3), (747.8, 347.7), (749.3, 338.2), (740.3, 337.1))),
    (1359790848, '', 63.3, ((705.2, 353.9), (719.9, 357.1), (722.3, 343.9), (707.6, 340.7))),
    (1359790849, '', None, ((709.8, 339.3), (724.0, 341.8), (725.2, 335.0), (711.0, 332.6))),
    (1359790854, '8', 61.9, ((759.3, 347.2), (774.3, 351.9), (777.2, 342.6), (762.2, 337.9))),
]
HOUSE_ID0 = 994100
MARKER = (697.6, 240.8)


def _line(V, step=1.0):
    """dict(s, p, cum, zv, ls) every `step` m along the vertices (zv: the vertices' heights, 해발, or None)"""
    P = np.array([(v[0], v[1]) for v in V], float)
    seg = np.hypot(*np.diff(P, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    ss = np.arange(0.0, cum[-1] + 1e-6, step)
    p = np.stack([np.interp(ss, cum, P[:, 0]), np.interp(ss, cum, P[:, 1])], 1)
    zv = np.array([v[2] if len(v) > 2 else np.nan for v in V], float)
    return dict(s=ss, p=p, cum=cum, zv=zv, ls=LineString([tuple(q) for q in P]))


def road():
    L = _line(ROAD_PTS)
    s, z = np.array(ROAD_PROF).T
    L['zv'] = np.interp(L['cum'], s, z)
    return L


def at(L, s, o):
    """the point o m left of the line at s"""
    a, b = L['ls'].interpolate(max(s - 0.5, 0.0)), L['ls'].interpolate(min(s + 0.5, L['ls'].length))
    t = np.array([b.x - a.x, b.y - a.y]); t /= np.linalg.norm(t)
    q = L['ls'].interpolate(s)
    return (float(q.x - t[1] * o), float(q.y + t[0] * o)), float(math.atan2(t[1], t[0]))


def strip(L, s0, s1, o0, o1, step=1.0):
    """the polygon between offsets o0 .. o1 (left +) from s0 to s1"""
    ss = list(np.arange(s0, s1, step)) + [s1]
    return Polygon([at(L, s, o0)[0] for s in ss] + [at(L, s, o1)[0] for s in ss[::-1]]).buffer(0)


def corridors():
    """[(name, line, half width)]: 청송길, 연대동문길, the road east from the junction"""
    return [('road', road(), ROAD_HALF), ('lane', _line(LANE), LANE_HALF), ('town', _line(TOWN_RD), TOWN_HALF)]


def _z_along(L, s):
    """the line's surface (해발) at s"""
    return np.interp(s, L['cum'], L['zv'])


def grade(Hn, X, Y, FIXED, halls, step=5.0, half=800.0):
    """The ground round the gate on GRID, late (the planting has read the ground as it was): every node in REGION goes
    to GRID, eased into the game's ground over TAPER m inside REGION's edge and over HALL_EASE m round the feet of the
    halls already there (their outlines + HALL_PAD stay, as do nodes another rule set: FIXED); the roads' nodes (half
    width + 1.25 m) level across on their own profiles.  halls: outlines of the halls of the list near REGION.
    Returns the nodes set (to be FIXED) and a summary."""
    H0 = Hn.copy()
    zone = shapely.contains_xy(REGION, X, Y) & ~FIXED
    xs, ys = X[zone], Y[zone]
    pts = shapely.points(np.stack([xs, ys], 1))
    t = np.clip(shapely.distance(REGION.exterior, pts) / TAPER, 0.0, 1.0)
    w = t * t * (3.0 - 2.0 * t)
    near = [h for h in halls if h.intersects(REGION.buffer(HALL_PAD + HALL_EASE))]
    if near:
        hold = unary_union([h.buffer(HALL_PAD) for h in near])
        u = np.clip(shapely.distance(hold, pts) / HALL_EASE, 0.0, 1.0)
        w *= u * u * (3.0 - 2.0 * u)
    G = grid_z(xs, ys)
    Hn[zone] = H0[zone] + w * (G - H0[zone])
    took = np.zeros(X.shape, bool)
    for nm, L, hw in corridors():
        sel = zone.copy()
        jj, ii = np.nonzero(sel)
        P = shapely.points(np.stack([X[sel], Y[sel]], 1))
        dist = shapely.distance(L['ls'], P)
        s = shapely.line_locate_point(L['ls'], P)
        on = (dist <= hw + 1.25) & (s > 0.01) & (s < L['cum'][-1] - 0.01)
        z = np.array([datum.up(X[j, i], Y[j, i], float(_z_along(L, ss)), None) for j, i, ss in zip(jj[on], ii[on], s[on])])
        # (eased into the ground as it was over the first and last 25 m where the line runs into the taper)
        wt = w[np.searchsorted(np.flatnonzero(zone.ravel()), (jj[on] * X.shape[1] + ii[on]))]
        Hn[jj[on], ii[on]] = H0[jj[on], ii[on]] + wt * (z - H0[jj[on], ii[on]])
        took[jj[on], ii[on]] = True
    moved = np.abs(Hn - H0)
    return took, dict(nodes=int((moved > 0.05).sum()), most=round(float(moved.max()), 1), raised=round(float((Hn - H0).max()), 1),
                      lowered=round(float((Hn - H0).min()), 1), road=int(took.sum()))


def woods():
    """the woods' floor on the campus side: the knoll north of the road, the slope south of it round 법현학사 (the
    1997 scans: closed crowns), off the roads, the bare band, the lodge's yard and the halls"""
    L = road()
    off = unary_union([L['ls'].buffer(ROAD_HALF + 0.5), strip(L, *BARE[:2], BARE[2], BARE[3]), strip(L, *WALK[2:], -WALK[1], -WALK[0]),
                       Polygon(LODGE).buffer(4.0), unary_union([Polygon(g).buffer(2.5) for _, g, _ in BEOPHYEON]),
                       _line(LANE)['ls'].buffer(LANE_HALF + 1.0), JUNCTION.buffer(1.0)])
    return CAMPUS_SIDE.difference(off)


def splat_paint():
    """(woods' floor, paving) for the main map west of x 641: the knoll's woods and the walk south of the road"""
    clip = box(595.0, 140.0, 641.0, 360.0)
    L = road()
    return woods().intersection(clip), strip(L, *WALK[2:], -WALK[1], -WALK[0]).intersection(clip)


def ground_map():
    """the east patch's ground map: {asphalt, pavers, dirt, woods} polygons"""
    C = corridors()
    L = C[0][1]
    asph = [C[0][1]['ls'].buffer(ROAD_HALF, cap_style='flat'), C[1][1]['ls'].buffer(LANE_HALF, cap_style='flat'), LANE_BAY,
            C[2][1]['ls'].buffer(TOWN_HALF, cap_style='flat'), JUNCTION]
    for r in SSR:
        asph.append(LineString(r[:-1]).buffer(r[-1], cap_style='flat'))
    # (the lodge's yard between it and the road: asphalt in 2010)
    asph.append(Polygon([(701.0, 228.0), (705.0, 226.0), (710.5, 233.5), (709.0, 239.5), (702.5, 239.0), (699.0, 233.0)]))
    asph_u = unary_union(asph).difference(Polygon(LODGE).buffer(0.1))
    toll = _toll_poly()
    asph_u = asph_u.difference(toll)
    halls = unary_union([Polygon(g).buffer(0) for _, g, _ in BEOPHYEON] + [Polygon(h[3]).buffer(0) for h in HOUSES] + [Polygon(LODGE)])
    walk = strip(L, *WALK[2:], -WALK[1], -WALK[0])
    yard = unary_union([Polygon(g).buffer(2.5) for _, g, _ in BEOPHYEON]).difference(
        unary_union([Polygon(g).buffer(0) for _, g, _ in BEOPHYEON])).intersection(Polygon([(650, 190), (692, 196), (692, 212), (650, 212)]))
    town = box(ESPLAT['x0'], ESPLAT['y0'], ESPLAT['x1'], ESPLAT['y1']).difference(CAMPUS_SIDE).difference(ISLAND)
    # (the town's alleys and yards between the houses: grey concrete and asphalt, as the town round the campus is drawn)
    asph_u = asph_u.union(town.difference(unary_union([walk, toll]))).difference(Polygon(LODGE).buffer(0.1))
    pav = unary_union([walk, yard, toll]).difference(asph_u)
    dirt = strip(L, *BARE[:2], BARE[2], BARE[3]).difference(asph_u)
    wd = woods().difference(unary_union([asph_u, pav, dirt]))
    return dict(asphalt=asph_u, pavers=pav, dirt=dirt, woods=wd)


def draw_map(k=4):
    """the patch's ground map as an RGB array (rows north first): R asphalt, G paving, B dirt 255 / the woods' floor 170
    (as build_campus.py's splat), each drawn at k times and averaged"""
    from PIL import Image, ImageDraw
    gm = ground_map()
    S = ESPLAT
    W, H = int(round((S['x1'] - S['x0']) / S['res'])), int(round((S['y1'] - S['y0']) / S['res']))
    P = lambda x, y: ((x - S['x0']) / S['res'] * k, (S['y1'] - y) / S['res'] * k)
    out = {}
    for layer in ('asphalt', 'pavers', 'dirt', 'woods'):
        im = Image.new('L', (W * k, H * k), 0)
        d = ImageDraw.Draw(im)
        g = gm[layer]
        for pg in (g.geoms if hasattr(g, 'geoms') else [g]):
            if pg.geom_type != 'Polygon' or pg.is_empty:
                continue
            d.polygon([P(x, y) for x, y in pg.exterior.coords], fill=255)
            for h in pg.interiors:
                d.polygon([P(x, y) for x, y in h.coords], fill=0)
        out[layer] = np.array(im, np.float32).reshape(H, k, W, k).mean(axis=(1, 3))
    a = out['asphalt']
    p = np.minimum(out['pavers'], 255.0 - a)
    b = np.minimum(np.maximum(out['dirt'], out['woods'] * (170.0 / 255.0)), 255.0 - a - p)
    return np.stack([a, p, np.clip(b, 0, 255)], -1)


def pack(town_png, rgb, tsplat, gutter=8):
    """the east map packed beside the town's and the north patch's in the one texture (tools/muak.py pack wrote those
    two; the terrain's shader samples one map for all three: no new texture unit).  Returns campus.json's tsplat with
    every fraction of the atlas rewritten for the wider texture, and `east` (its rectangle) with its own three"""
    from PIL import Image
    T = np.array(Image.open(town_png).convert('RGB'), np.uint8)
    h0, w0 = T.shape[:2]
    a = tsplat['atlas']
    h = max(h0, rgb.shape[0])
    W = w0 + gutter + rgb.shape[1]
    A = np.zeros((h, W, 3), np.uint8)
    A[:h0, :w0] = T
    A[:h0, w0:w0 + gutter // 2] = T[:, -1:]
    n = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
    x0 = w0 + gutter
    A[:n.shape[0], x0:] = n
    A[:n.shape[0], x0 - gutter // 2:x0] = n[:, :1]
    A[n.shape[0]:, x0:] = n[-1:]
    Image.fromarray(A, 'RGB').save(town_png, optimize=True)
    k = w0 / W
    out = dict(tsplat)
    out['atlas'] = [round(a[0] * k, 6), round(a[1] * h0 / h, 6), round(a[2] * k, 6), round(a[3] * k, 6), round(a[4] * h0 / h, 6),
                    round(x0 / W, 6), round(n.shape[1] / W, 6), round(n.shape[0] / h, 6)]
    out['east'] = [ESPLAT['x0'], ESPLAT['y0'], ESPLAT['x1'], ESPLAT['y1']]
    return out


def _toll_poly():
    c, s = math.cos(TOLL['rot']), math.sin(TOLL['rot'])
    L, W = TOLL['island']
    x, y = TOLL['pos']
    return Polygon([(x + u * c - v * s, y + u * s + v * c) for u, v in ((-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2))])


def _rect_to_hall(bid, name, style, g, base, roof, ground, par=0.9, fh0=3.0, **kw):
    poly = shapely.geometry.polygon.orient(Polygon(g).buffer(0), 1.0)
    hs = [ground(x, y) for x, y in poly.exterior.coords]
    z0 = min(hs) if base is None else base
    zt = max(roof - par - z0, 2.6)
    lv = max(1, int(round(zt / fh0)))
    b = dict(id=bid, name=name, style=style, levels=lv, height=round(zt, 2), fh=round(zt / lv, 3), base=round(z0, 2),
             top_ground=round(max(hs), 2), footprint=[[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]])
    b.update(kw)
    return b


def houses(ground):
    """campus.json buildings, at the list's end: 법현학사's two blocks and the boxes on its roof, the lodge, the town's
    houses (city blocks; a roof read off the scans gives the storeys over the lowest corner, else two)"""
    out = []
    for bid, g, roof in BEOPHYEON:
        out.append(_rect_to_hall(bid, '법현학사', 'brick', g, None, datum.up(*Polygon(g).centroid.coords[0], roof), ground, fh0=3.0))
    for bid, g, roof in BEOPHYEON_TOPS:
        under = next(b for b in out if Polygon(b['footprint']).buffer(0.5).contains(Polygon(g).centroid))
        rt = under['base'] + under['height'] + 0.9 * 0.0
        out.append(_rect_to_hall(bid, '법현학사', 'white', g, round(rt, 2), datum.up(*Polygon(g).centroid.coords[0], roof), ground, par=0.5))
        out[-1]['top_ground'] = out[-1]['base']          # (on the roof: no ground under it)
    out.append(_rect_to_hall(LODGE_ID, '', 'white', LODGE, None, 0.0, ground, par=0.0, levels=1,
                             hip=dict(mat='roof_slate', pitch=0.5, over=0.45)))
    lodge = out[-1]
    lodge.update(levels=1, height=2.6, fh=2.6)
    for k, (oid, nm, roof, g) in enumerate(HOUSES):
        poly = Polygon(g).buffer(0)
        hs = [ground(x, y) for x, y in poly.exterior.coords]
        if roof is None:
            top = min(hs) + 6.0 + 0.9
        else:
            top = max(datum.up(*poly.centroid.coords[0], roof), min(hs) + 3.5)
        b = _rect_to_hall(HOUSE_ID0 + k, '', 'city', g, None, top, ground)
        out.append(b)
    return out


def gate():
    """campus.json 「dongmun」 (blender/landmarks.py dongmun draws it, on the ground as saved): the piers, the toll
    island and its booth, the granite-block wall along the road's north edge (every metre)"""
    L = road()
    wall = [[round(c, 2) for c in at(L, s, WALL_OFF)[0]] for s in np.arange(WALL_S[0], WALL_S[1] + 1e-6, 1.0)]
    return dict(piers=[dict(c=list(p['c']), t=list(p['t']), n=list(p['n'])) for p in PIERS], L=PIER_L, W=PIER_W, H=PIER_H,
                toll=TOLL, wall=wall)


def paint():
    """road_paint additions: the middle line of 청송길 (yellow in 2010; one bright line on the 1997 scans) off the
    toll island, the hump outside the gate"""
    L = road()
    lines = []
    for s0, s1 in ((2.0, 82.0), (100.0, 116.0)):
        lines.append(dict(kind='yellow', w=0.15, pts=[[round(c, 2) for c in at(L, s, 0.25)[0]] for s in np.arange(s0, s1 + 1e-6, 2.0)]))
    return lines, [HUMP]


def props():
    """the street lamps on the walk south of the road (the 1997 scans: their poles' shadows on it)"""
    L = road()
    out = []
    for s in LAMPS_S:
        (x, y), a = at(L, s, -(WALK[0] + 0.45))
        out.append(['lamp_arm', round(x, 2), round(y, 2), round(a + math.pi, 3)])
    return out


def move_off(trees, shrubs, props_, taken):
    """what the planting left where the new roads and houses are (west of x 640 only: there were none east of it):
    trees step aside to the edge in their places in the list, shrubs and props go"""
    sh = taken.buffer(0.6)
    shapely.prepare(sh)
    n0 = (len(shrubs), len(props_))
    shrubs[:] = [s for s in shrubs if not sh.contains(Point(s[1], s[2]))]
    props_[:] = [p for p in props_ if not sh.contains(Point(p[1], p[2]))]
    e = sh.buffer(1.0).boundary
    moved = 0
    for t in trees:
        if sh.buffer(0.3).contains(Point(t[1], t[2])):
            q = nearest_points(e, Point(t[1], t[2]))[0]
            t[1], t[2] = round(q.x, 2), round(q.y, 2)
            moved += 1
    return n0[0] - len(shrubs), n0[1] - len(props_), moved


def taken():
    """what the roads, the walk and the halls here take (for move_off)"""
    C = corridors()
    L = C[0][1]
    return unary_union([L['ls'].buffer(ROAD_HALF), strip(L, *WALK[2:], -WALK[1], -WALK[0])] +
                       [Polygon(g).buffer(0.8) for _, g, _ in BEOPHYEON] + [Polygon(LODGE).buffer(0.8)])


def trees(trees_, halls, fill):
    """the woods' trees on the knoll and the slope (the 1997 scans: closed crowns), clear of the roads, the bare band and
    the halls, on a jittered lattice (fill: tools/muak.py woods_fill, its own stream), and the island's few"""
    wd = woods().buffer(-3.0).difference(Point(*MARKER).buffer(9.0))     # (crowns clear of the road and the gate)
    wd = wd.difference(unary_union([Polygon(h).buffer(3.0) for h in halls]))
    wd = wd.intersection(box(598.0, 140.0, 772.0, 352.0))
    out = fill(wd, trees_, seed=19970, spacing=7.5)
    rd = random.Random(19971)
    for x, y in ((707.6, 246.0), (709.4, 252.5), (709.8, 259.5), (709.6, 266.0)):
        out.append(['pine', round(x + rd.uniform(-0.4, 0.4), 2), round(y + rd.uniform(-0.4, 0.4), 2), round(rd.uniform(0.45, 0.6), 2),
                    round(rd.uniform(0, 6.28), 2)])
    return out


def shrubs():
    """clipped shrubs on the island (topiary in 2010; dark round crowns on the 1997 scans)"""
    out = []
    for x, y in ((706.4, 249.5), (708.0, 256.0), (708.4, 262.5), (709.8, 269.0), (707.2, 243.0)):
        out.append(['topiary_round', x, y, 0.9, 0.0])
    return out


def colliders():
    """the walker's walls: the two piers and the toll island's booth (the bars are lowered, walked under)"""
    out = []
    for p in PIERS:
        (cx, cy), (tx, ty), (nx, ny) = p['c'], p['t'], p['n']
        out.append([[round(cx + tx * u + nx * v, 2), round(cy + ty * u + ny * v, 2)]
                    for u, v in ((-PIER_L / 2, -PIER_W / 2), (PIER_L / 2, -PIER_W / 2), (PIER_L / 2, PIER_W / 2), (-PIER_L / 2, PIER_W / 2))])
    c, s = math.cos(TOLL['rot']), math.sin(TOLL['rot'])
    x, y = TOLL['pos']
    hl, hw = TOLL['size'][0] / 2 + 0.3, TOLL['size'][1] / 2 + 0.3
    out.append([[round(x + u * c - v * s, 2), round(y + u * s + v * c, 2)] for u, v in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))])
    return out
