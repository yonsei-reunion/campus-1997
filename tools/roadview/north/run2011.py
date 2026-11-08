from solve import report
from lm import bearing
P = {}
P['2011@184'] = dict(pano=1017220184, start=(-25.8, -86.0), car=0.92, obs={
    'libSE': bearing(284, 675.2), 'libNE': bearing(335, 696.0), 'uSW': bearing(129, 767.6), 'uNW': bearing(47, 724.5), 'bySE': bearing(0, 712.5)})
if __name__ == "__main__":
    import sys
    for k, d in P.items():
        if len(sys.argv) > 1 and k not in sys.argv[1:]: continue
        report(k, d['obs'], d['start'], d.get('car'))
