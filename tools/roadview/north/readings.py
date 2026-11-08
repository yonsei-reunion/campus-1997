# 2010-12 readings (this session, 2026-11-08): pans as rvp.mjs printed them (whole degrees), x read at 3-9x.
# car = lanes2.py (m east of the road centre), rd = road direction in the pano frame from the yellow-line VP.
# A value (pan, x) or (pan, x, sd_px); sd_px defaults to 1.5.
# libSE: the corner has a SE-facing strip ~12 px wide (lit in both the Dec noon and the Apr morning views): the noon
#   lit/dim step (its right end) - 6 px, sd 3.  175/177: roofline top.
# libSW: left end of the stone face; a 2000s glass building stands at the SW corner (occlusion possible): sd 3, test without.
P = {}
P['2010@175'] = dict(pano=1016786004, start=(-46.9, -168.1), car=0.95, rd=16.5, obs={
    'libSE': (337, 755.0, 3), 'libNE': (353, 741.25), 'C14': (92, 725.0, 2.5), 'C12': (114, 640.0)})
P['2010@176'] = dict(pano=1016786006, start=(-42.6, -151.4), car=1.25, rd=16.1, obs={
    'libSE': (333, 698.0, 3), 'libNE': (351, 724.0, 2.5)})
P['2010@177'] = dict(pano=1016786007, start=(-40.2, -142.2), car=1.22, rd=16.1, obs={
    'libSE': (328, 712.0, 6), 'libNE': (350, 722.2, 2), 'C12': (141, 752.0)})
P['2010@178'] = dict(pano=1016786008, start=(-37.8, -133.1), car=1.15, rd=17.3, obs={
    'libSW': (310, 689.0, 3), 'libSE': (323, 694.0, 3), 'libNE': (348, 727.1), 'bySE': (4, 723.0, 4),
    'uSW': (60, 728.5), 'C12': (148, 764.5)})
P['2010@179'] = dict(pano=1016786009, start=(-35.4, -123.9), car=1.16, rd=16.2, obs={
    'libSW': (306, 679.0, 3), 'libSE': (319, 665.5, 3), 'libNE': (347, 711.3, 2), 'uGN': (49, 757.6, 2.5),
    'uSW': (67, 771.0), 'C12': (154, 781.6, 3)})
P['2010@181'] = dict(pano=1016786010, start=(-33.0, -114.7), car=1.12, rd=15.8, obs={
    'libSW': (298, 712.0, 3), 'libSE': (308, 711.5, 3), 'libNE': (343, 729.0, 3), 'bySE': (3, 716.0, 3),
    'uNW': (38, 697.1), 'uSW': (87, 678.3), 'uSE': (87, 805.0, 2.5), 'C12': (162, 725.0, 3)})
P['2010@182'] = dict(pano=1016786011, start=(-30.6, -105.2), car=1.10, rd=15.7, obs={
    'libSW': (301, 592.0, 3), 'libSE': (301, 689.5, 3), 'libNE': (341, 706.0, 2), 'uSW': (99, 710.0), 'uSE': (99, 740.0, 2)})
