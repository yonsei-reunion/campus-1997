from solve import report
from lm import bearing
P = {}
# 2010-12 panos through compare mode; pans as used (whole degrees, aimed from the 2011 node), x read at 3x
P['2010@184'] = dict(pano=1016786013, start=(-25.8, -86.4), car=1.24, obs={
    'libSE': bearing(284, 693.5), 'libNE': bearing(335, 678.3), 'uSW': bearing(129, 715.7), 'uNW': bearing(34, 867.5), 'bySE': bearing(0, 703.0)})
P['2010@187'] = dict(pano=1016786016, start=(-18.6, -58.1), car=1.19, obs={
    'libSE': bearing(258, 728.4), 'libNE': bearing(321, 677.6), 'uSW': bearing(156, 748.8), 'uNW': bearing(62, 716.4), 'bySE': bearing(356, 702.5)})
P['2010@181'] = dict(pano=1016786010, start=(-33.0, -114.7), car=1.11, obs={
    'libSE': bearing(308, 685.5), 'libNE': bearing(343, 732.0), 'uSW': bearing(87, 680.0), 'uNW': bearing(38, 697.6), 'bySE': bearing(3, 716.0)})
P['2010@178'] = dict(pano=1016786008, start=(-37.8, -133.1), car=1.16, obs={
    'libSE': bearing(323, 698.0), 'libNE': bearing(348, 727.6), 'uSW': bearing(60, 725.0), 'C12': bearing(148, 765.0), 'bySE': bearing(4, 727.0)})
P['2010@175'] = dict(pano=1016786004, start=(-46.9, -168.2), car=0.87, obs={
    'libSE': bearing(337, 756.0), 'libNE': bearing(353, 740.8), 'C12': bearing(114, 633.0)})
if __name__ == "__main__":
    import sys
    for k, d in P.items():
        if len(sys.argv) > 1 and k not in sys.argv[1:]: continue
        report(k, d['obs'], d['start'], d.get('car'))
