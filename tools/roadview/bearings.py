# Readings for issue #82 (2026-11-08): pixel columns read off roadview screenshots (rv.mjs, ruler.py) and the
# bearings they give in each pano's own (unknown-offset) heading frame.  resect.py solves positions from them.
#   python bearings.py        print every reading and its bearing
# The viewer floors the pan to a whole degree, so the bearing is floor(pan) + atan((x - 694) / F).
import math

F = 785.0          # focal length at zoom 3 in the 1388 px view (783 ± 5 measured with whole-degree steps)
# Kakao positions (game frame, as rv.mjs printed them, 0.1 m) of the 2011-04-16 panos along 백양로
XY = {169: (-61.3, -220.8), 172: (-53.3, -192.5), 175: (-46.5, -165.4), 178: (-38.6, -135.5), 181: (-32.6, -112.7),
      184: (-25.8, -86.0), 187: (-18.6, -57.3)}          # pano ids 10172201xx
# landmarks (OSM corners; they match the Kakao skyview roofs within ~1 m) and the look targets used to aim the shots
L = {'SE': (-85.4, -71.1),      # 중앙도서관 south-east corner (way 163525865)
     'NE': (-65.9, 3.2),        # 중앙도서관 north-east corner
     'C12': (-11.0, -181.3)}    # 백주년기념관 north-west corner of the hall box (way 324328422, vertex 12)
LOOK = {'libSE': L['SE'], 'libNE': L['NE'], 'centNW': (-11.1, -181.3), 'eagle': (-66.5, -161.0), 'fountain': (-80.7, -203.2)}
# the statues' first spots (from Kakao's headings and positions); offsets are measured from these.  The game moved
# them on 2026-11-08 to (-70.6, -159.9) and (-82.8, -202.6) (statues.py, reference/고증.md 4.1.4, 4.3)
EAGLE_GAME, FOUNTAIN_GAME = (-66.5, -161.0), (-80.7, -203.2)


def pan_of(xy, look):
    tx, ty = LOOK[look]
    return (math.degrees(math.atan2(tx - xy[0], ty - xy[1])) + 360) % 360


def bearing(pan, px):
    return math.floor(pan + 1e-9) + math.degrees(math.atan((px - 694) / F))


# 2011: pano, thing seen (SE/NE/C12 landmark, E eagle pillar, F 활천대 pillar), the shot's look target, pixel column
READ_2011 = [
    (169, 'C12', 'centNW', 755.9), (169, 'E', 'eagle', 697.2), (169, 'F', 'fountain', 727.0),
    (172, 'C12', 'centNW', 713.9), (172, 'E', 'libSE', 558.1), (172, 'F', 'fountain', 733.3),
    (175, 'SE', 'libSE', 730.4), (175, 'E', 'eagle', 744.6), (175, 'C12', 'centNW', 700.0),
    (178, 'SE', 'libSE', 745.7), (178, 'NE', 'libNE', 730.2), (178, 'E', 'eagle', 816.3),
    (181, 'SE', 'libSE', 698.4), (181, 'NE', 'libNE', 721.6), (181, 'E', 'eagle', 748.1),
    (184, 'SE', 'libSE', 676.7), (184, 'NE', 'libNE', 697.4),
    (187, 'SE', 'libSE', 732.4), (187, 'NE', 'libNE', 728.6)]
OBS_2011 = {}
for i, k, look, px in READ_2011:
    OBS_2011.setdefault(i, {})[k] = round(bearing(pan_of(XY[i], look), px), 2)

# eagle pillar width (0.66 m) -> distance from the pano: 24 px from 175 (2011)
DIST_2011 = {175: (21.7, 1.5)}

# past panos through compare mode (rv.mjs past): pans as actually used (whole degrees), heading frame unknown
PAST = {
    '2010@175': dict(pano=1016786004, obs={'SE': bearing(337, 755.0), 'C12': bearing(114, 640.5), 'E': bearing(282, 833.4)},
                     dist=(19.2, 1.2), car=0.40),
    '2010@187': dict(pano=1016786016, obs={'SE': bearing(258, 730.8), 'NE': bearing(322, 664.3)}, car=None),
    '2008@175': dict(pano=2381283, obs={'C12': bearing(105, 545.5), 'E': bearing(290, 626.4)}, dist=(24.7, 1.6), car=2.14),
}
# car offset east of the carriageway centre, from the two yellow edge lines (ratio of their image slopes, 6.6 m apart)
CAR_2011 = 0.92


# --- second pass (2026-11-08): 활천대 and the eagle's 「연세인」 groups from every 2011 pano 169-177 (statues.py,
# groups.py).  Pans are the whole degrees rv.mjs printed; a sigma (deg) per reading.  The first pass's 172 E was
# misread (563.5; the same shot reads 558.1, fixed above).
XY.update({170: (-58.5, -211.2), 171: (-55.7, -201.6), 173: (-50.9, -182.9), 174: (-48.5, -174.1),
           176: (-43.3, -154.6), 177: (-40.6, -144.2)})          # Kakao positions of 10172201xx (rv.mjs info)
READ_SOUTH = [
    (169, 'F', 310, 753.6, .1), (169, 'C12', 51, 755.6, .1), (169, 'E', 351, 750.0, .1),
    (170, 'F', 290, 741.0, .1), (170, 'C12', 57, 755.6, .1), (170, 'E', 347, 750.0, .1),
    (171, 'F', 269, 717.3, .3), (171, 'C12', 65, 750.2, .1),
    (172, 'F', 252, 679.0, .1), (172, 'C12', 75, 712.7, .1), (172, 'E', 332, 736.4, .1),
    (173, 'F', 239, 695.7, .1), (173, 'C12', 87, 725.7, .1), (173, 'E', 320, 755.2, .1),
    (174, 'F', 231, 693.2, .1), (174, 'C12', 100, 721.7, .1), (174, 'E', 303, 756.5, .1),
    (175, 'F', 225, 686.4, .1), (175, 'C12', 114, 700.5, .1), (175, 'E', 284, 716.6, .1), (175, 'SE', 337, 730.4, .1),
    (176, 'F', 220, 703.1, .15), (176, 'C12', 129, 668.8, .1), (176, 'E', 259, 772.1, .1),
    (177, 'E', 242, 763.0, .1),
]
# north group 178-187 kept from READ_2011 (their pans recomputed from the look targets there)
READ_NORTH = []
for i, k, look, px in READ_2011:
    if i >= 178:
        READ_NORTH.append((i, k, math.floor(pan_of(XY[i], look)), px, 1.0 if (k == 'NE' and i in (178, 181)) else .3))
READ_SOUTH_FIRST = [(i, k, math.floor(pan_of(XY[i], look)), px, .3) for i, k, look, px in READ_2011 if i < 178]

# past panos (rv.mjs past): name -> pano id, readings (kind, pan, x, sigma), optional pillar distance (m, sd), car offset
PAST2 = {
    # 1016786004, 2010-12-06, node 175 (SE kept from bearings.py; E, C12, F read here)
    '2010@175': dict(pano=1016786004, obs=[('SE', 337, 755.0, .1), ('C12', 114, 640.3, .1), ('E', 284, 803.3, .1), ('F', 225, 708.3, .15)],
                     dist=(19.2, 1.2), start=(-52.6, -166.4)),
    # 1016786002, 2010-12-06, node 172: F, E, C12 only (no redundancy alone)
    '2010@172': dict(pano=1016786002, obs=[('F', 252, 564.3, .15), ('E', 332, 656.7, .1), ('C12', 75, 816.8, .1)], start=(-55.0, -192.0)),
    # 1016785998, 2010-12-06, node 169
    '2010@169': dict(pano=1016785998, obs=[('F', 310, 851.9, .1), ('E', 351, 791.0, .1), ('C12', 51, 727.0, .1)], start=(-62.0, -220.0)),
}

# the four 「연세인」 groups: group centre (middle of its white mass / base, +-5 px on 2.5 - 5x crops) and the pillar
# centre in the same shot, so the heading cancels (groups.py)
# (view, pan, pillar x, {group: x})  -- 2011-04 panos 10172201xx, zoom 3, the E shots
G2011 = [
    (169, 351, 750.0, dict(A=697, B=730, C=773, D=799)),
    (170, 347, 750.0, dict(A=678, B=730, C=770, D=812)),
    (172, 332, 736.4, dict(A=640, D=831)),
    (174, 303, 756.5, dict(A=634, C=697, B=807, D=900)),
    (175, 284, 716.6, dict(A=636, C=593, B=808, D=843)),
    (176, 259, 772.1, dict(C=652, A=733, D=852, B=899)),
    (177, 242, 763.0, dict(C=654, D=779, B=874)),
]
GPAST = [('2010@172', 332, 656.7, dict(A=529, D=768))]


if __name__ == '__main__':
    for i, k, look, px in READ_2011:
        p = pan_of(XY[i], look)
        print('2011 %d %-3s look %-8s pan %7.2f -> %3d  x %6.1f  bearing %7.2f' % (i, k, look, p, math.floor(p), px, OBS_2011[i][k]))
    for name, d in PAST.items():
        print(name, d['pano'], {k: round(v, 2) for k, v in d['obs'].items()}, 'dist', d.get('dist'), 'car', d.get('car'))
