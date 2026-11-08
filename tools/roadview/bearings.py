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
EAGLE_GAME, FOUNTAIN_GAME = (-66.5, -161.0), (-80.7, -203.2)


def pan_of(xy, look):
    tx, ty = LOOK[look]
    return (math.degrees(math.atan2(tx - xy[0], ty - xy[1])) + 360) % 360


def bearing(pan, px):
    return math.floor(pan + 1e-9) + math.degrees(math.atan((px - 694) / F))


# 2011: pano, thing seen (SE/NE/C12 landmark, E eagle pillar, F 활천대 pillar), the shot's look target, pixel column
READ_2011 = [
    (169, 'C12', 'centNW', 755.9), (169, 'E', 'eagle', 697.2), (169, 'F', 'fountain', 727.0),
    (172, 'C12', 'centNW', 713.9), (172, 'E', 'libSE', 563.5), (172, 'F', 'fountain', 733.3),
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

if __name__ == '__main__':
    for i, k, look, px in READ_2011:
        p = pan_of(XY[i], look)
        print('2011 %d %-3s look %-8s pan %7.2f -> %3d  x %6.1f  bearing %7.2f' % (i, k, look, p, math.floor(p), px, OBS_2011[i][k]))
    for name, d in PAST.items():
        print(name, d['pano'], {k: round(v, 2) for k, v in d['obs'].items()}, 'dist', d.get('dist'), 'car', d.get('car'))
