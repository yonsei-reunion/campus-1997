"""연세로's shop rows from the bridge to the junction as they stood in July 1997, house by house
(reference/고증/4.10.8_연세로_가게_줄.md).

- where each house stood and how wide: the roofs of the 1997-07-28 scans (26/16 · 27/17 · 27/18 · 27/19 at the ground,
  tools/aerial97.py), which OSM's outlines of today follow but for the lots rebuilt since
- storeys: the roofs' heights over the walk in those scans (pairs of frames, 2.5 m windows every 2.5 m along both rows,
  4 and 8 m behind the fronts), a storey to 3.2 - 3.6 m
- walls (WALLS97, 2026-11-21): the 1996 photos first.  The houses they show (the seven and the INDIS five on the west,
  YRO_FIXED's at the junction) have the photos' wall; the rest the mix of the 27 fronts the photos show (grey 8, white
  tile 10, brick 3, cream 4, pink and purple-grey 2) as quotas: the wall of the Kakao roadview of 2008-08 (west half)
  and 2009-03 (east half, no leaves) kept where the house of 1997 still stood, the cream ones over the quota whose
  colour the roadview's notes do not name and the fronts redone or rebuilt since drawn to the quotas left
  (random.Random(4807); reference/고증/4.10.8 「벽」, the table's 「벽」 against its 「로드뷰」)
- shops: the two anthologies' street maps (2019 문집 25쪽 「1990 그때 그 시절 다시 보는 신촌거리」, 2021 문집 22 ~ 23쪽
  「90년대 신촌 그 때 그 거리」), block by block between the side streets; where the two differ the 2019 map's order.
  Which house of a block a shop was in is not known but for the few the roadview still has (새마을금고, 사진관, the
  1 · 2 · 3 floors of 상아탑분식's house): the names are laid along the block in the maps' order

ROWS[side]: (y of the north wall, y of the south wall, storeys, wall (WALLS97), depth m, shops), north to south;
side +1 east, -1 west.  shops: (name, floor); the name is a cell of sign_yro97.png (SIGNS, tools/make_textures.py
yro97_signs).  The last house of each side (금강제화, 홍익문고) and the two south of the last side street stay
tools/sinchon_rotary.py's (YRO_FIXED: the 1996 photos, the corner's landmarks).
"""

# the rows' walls (town_yro.jpg's bands, tools/make_textures.py YRO_WALLS; blender/town.py takes a block's wall field
# 8 + this): grimy where the 1996 photos have them so, streaked from the sills and the parapet
WALLS97 = ['붉은 벽돌', '갈색 벽돌', '크림', '회색', '흰 타일', '분홍', '연보라']

ROWS = {
    1: [
        # 연세로 (the lane east along the bank's foot, y -516) to 연세로12길: one house in two parts, five storeys with
        # the top floor set back and a low shop on its south (2009: 연대포토랜드 still in it); south of it 창천교회's
        # paved yard, open to the street (cars parked on it in the scans)
        (-520.0, -531.0, 5, 3, 12.0, [('연세식품', 1)]),
        (-531.0, -540.0, 2, 4, 10.0, [('사진관', 1)]),
        # 연세로12길 to 명물1길: the lot of 독수리다방 · 초원각 · 독수리약국 is DOK97's (its houses of December 1996, not
        # the pit of July 1997); the three-storey house south of it stood on
        (-587.6, -600.0, 3, 4, 10.0, [('알서림', 1), ('식품점', 1)]),
        # 명물1길 to the street at y -700
        (-604.0, -610.6, 2, 2, 9.0, [('새마을금고', 1)]),
        (-610.8, -620.6, 5, 3, 11.0, [('오락실', 1)]),
        (-620.8, -624.6, 2, 2, 9.0, []),
        (-624.8, -639.1, 4, 5, 12.0, []),
        (-639.2, -647.4, 4, 3, 12.0, []),
        (-647.5, -656.0, 4, 4, 12.0, []),
        (-656.6, -669.6, 3, 4, 11.0, [('아마데우스', 1)]),
        (-669.9, -681.0, 4, 1, 12.0, [('초원분식', 1)]),
        (-681.2, -695.0, 4, 3, 12.0, [('웬디스버거', 1)]),
        # the street at y -700 to 명물길
        (-703.5, -715.0, 4, 1, 12.0, [('레벤호프', 1)]),
        (-715.1, -729.0, 3, 2, 10.0, [('아트박스', 1)]),
        # 명물길 to 연세로4길
        (-755.5, -761.0, 4, 4, 11.0, [('비잔틴', 1)]),
        (-761.1, -770.6, 5, 4, 12.0, [('태림레코드', 1)]),       # (52006 · 52106: its south face of white tile)
        # 연세로4길 to 연세로2길: three low houses, then three- and four-storey ones (the towers of today came later);
        # the four at its south end are YRO_FIXED's
        (-779.5, -788.3, 2, 4, 10.0, [('프리타임', 1), ('영당구장', 2)]),
        (-788.4, -798.4, 2, 4, 10.0, [('베를린호프', 1)]),
        (-798.5, -808.6, 2, 3, 10.0, [('복지다방', 2)]),
        (-809.0, -822.0, 3, 3, 12.0, [('동화은행', 1)]),   # (51979: its wall signs 안과 · 동화은행 here)
        (-823.0, -834.5, 3, 4, 12.0, []),
        (-835.0, -848.4, 4, 4, 13.0, []),
    ],
    -1: [
        # 연세로13길 (along the bank's foot) to 연세로11길
        (-521.5, -530.0, 5, 3, 12.0, [('독수리문구', 1)]),
        (-530.1, -540.3, 5, 0, 12.0, [('시골분식', 1), ('이태리분식', 1)]),
        (-540.5, -552.0, 1, 2, 9.0, [('연세문화사', 1)]),
        # 연세로11길 to 연세로9길
        (-563.0, -574.5, 3, 6, 12.0, [('연희식당', 1), ('장미당구장', 2)]),
        (-574.7, -590.5, 4, 4, 13.0, [('쟈뎅', 1), ('Y오락실', 1)]),
        (-590.7, -602.0, 5, 2, 12.0, [('상아탑분식', 1), ('상아탑다방', 2), ('상아탑당구장', 3)]),
        # 연세로9길 to 연세로7길
        (-610.5, -619.5, 4, 4, 11.0, [('오늘의 책', 1), ('기원', 2)]),
        (-620.0, -631.0, 4, 0, 11.0, [('레코드', 1)]),
        (-634.5, -645.5, 8, 3, 13.0, [('신촌반점', 1), ('가든당구장', 2)]),
        (-646.0, -659.6, 7, 3, 14.0, [('진미락', 1)]),
        (-659.9, -668.8, 5, 3, 12.0, [('천지문', 1)]),
        (-669.0, -680.6, 5, 2, 13.0, [('오비넬라', 1), ('뚱보분식', 1)]),
        (-680.9, -694.0, 3, 4, 12.0, [('빌보드', 1), ('파블로', 1)]),
        # 연세로7길 to 연세로5길
        (-705.0, -716.5, 7, 4, 13.0, [('약국', 1), ('연세만화랑', 3)]),
        (-721.5, -736.0, 4, 4, 12.0, [('오락실', 1)]),
        # 연세로5길 to the street at y -888: a small open corner with trees first (the scans: no roof before y -783),
        # then the seven storeys of white tile and dark window bands (52006 · 52106: 현대예식장's sign up its corner,
        # 신영증권 on its roof; the scans: 32 m along the street, its roof 22 - 25 m over the walk), a paved court
        # with parked cars south of it
        (-787.5, -816.5, 7, 4, 16.0, [('하이클라스', 1), ('국민은행', 1)]),
        (-823.0, -833.8, 3, 1, 12.0, []),
        (-834.0, -842.5, 4, 3, 12.0, []),
        (-846.0, -861.0, 3, 4, 13.0, [('쌍쌍호프', 1)]),
        (-862.0, -876.2, 4, 5, 14.0, []),
        (-876.4, -883.5, 5, 4, 13.0, []),          # (52006: the white five of INDIS · 기원 · 바둑 · 만화)
    ],
}
# the shop on the house YRO_FIXED keeps north of each corner's landmark (west: the cream three north of 금강제화)
FIXED_SHOPS = {(-1, 3, 1): [('스페인하우스', 1)]}

# 독수리빌딩's lot, east side between 연세로12길 and the house at y -587.6.  In the scans of 1996-12-23 (26/16 · 26/17)
# and 1996-11-28 (27/17 · 27/18) the old houses stand; on 1997-07-28 (26/16 · 27/17 · 27/18) it is a pit shored with steel
# struts (the same lattice at the same place in all three, 0 - 2 m over the walk); a tall block finished in 1998-10
# (연세춘추 1998-05-11: 8 storeys, to open that summer).  When the old houses came down between the two is not known; the
# game's season is May and the user chose the old houses (2026-11-21).  LOT: the pit's outline in the three frames of
# 1997, which is the lot that was cleared (whatever of gate_town's stands in it goes)
LOT = [(-83.6, -563.6), (-69.0, -562.0), (-55.5, -561.5), (-53.0, -574.0), (-58.0, -584.5), (-63.5, -592.5), (-76.0, -591.5),
       (-83.2, -587.2)]

# The lot in December 1996 (heights over the walk: the four frames' roofs matched pair by pair, 1.2 m windows every 1.5 m;
# outlines: the roofs' edges where two frames laid at the roof's height agree):
# - 독수리다방's own house at the back, 16 m in from 연세로 behind a paved yard at the lane's corner: a three-storey block
#   11.0 m high, its north face 17.6 m along the lane, the west one 3.9 m and then turning south-east; a stair tower a
#   storey higher (13.6 m) on that turned side; a round bay 8 - 10 m high bulging west where the two meet.  The 2019
#   anthology's photo of the house (26쪽, an older print: dark brick, a slate mansard along the north face with the white
#   letters 독 수 리 on it, three wide windows of coloured glass under it and a narrower one over the door at the corner,
#   two storeys of glazing at the east half, the round bay and the taller tower round the corner on the right) is this
#   one seen from the north-west: the same three masses at the same heights, and the three wide windows show in 26/16
# - a four-storey house on the street south of the yard, 14.3 m high, its front 2.5 m behind the row's (a higher stair
#   head on its north-east); its wall pale where the sun is on it (the south face in 26/17)
# - the yard: the banded paving of 창천교회's front along the street's walk, cars on it
DOK97 = dict(
    # 독수리다방: the three-storey block's outline, counter-clockwise from its north-west corner
    main=[(-66.0, -566.6), (-66.0, -570.5), (-63.6, -579.3), (-60.0, -579.8), (-58.8, -577.6), (-48.0, -570.0), (-48.5, -564.9)],
    h=11.0,
    tower=[(-66.0, -570.5), (-64.4, -576.5), (-61.0, -576.5), (-61.0, -570.5)], tower_h=13.6,
    bay=(-66.0, -569.9, 2.4, 3.6, 9.4),          # (the round bay: its middle on the west wall, radius, from - to over the floor)
    # the street house: (y north, y south, storeys, wall (WALLS97), depth, how far its front is behind the row's, shops)
    house=(-575.8, -587.3, 4, 4, 14.0, 2.5, [('초원각', 1), ('독수리약국', 1), ('독수리만화방', 2)]),
    # the yard open to the walker: from the row's front line to 독수리다방's walls, the lane to the street house, and the
    # strip before the street house's front
    yard=[(-82.6, -561.0), (-82.6, -587.6), (-79.9, -587.6), (-79.9, -575.5), (-65.4, -575.5), (-65.4, -561.0)],
    fore=[(-66.5, -561.0), (-66.5, -565.9), (-49.0, -564.2), (-49.0, -561.0)],     # (and the strip before its north face)
)
# 창천교회's front yard, open to the walker (2026-11-21, user's request): north of 독수리다방's yard across the lane
# (연세로12길), from 연세로's walk to the church's west front and along it north to the houses' end.  The scans of
# 1997-07-28: a paved yard with cars parked on it south of 사진관's house, a bus standing before the church's front, the
# lane's kerb along its south and south-west.  The game has no carriageway or kerb for the lane, so the whole of it to
# 독수리다방's yard is one open ground; whatever house or the church stands in these boxes is cut out of them
CHURCH_YARD = [
    [(-82.6, -540.4), (-82.6, -561.2), (-49.0, -561.2), (-49.0, -540.4)],
    [(-72.2, -520.5), (-72.2, -540.6), (-49.0, -540.6), (-49.0, -520.5)],
]
# The church's porch stands in that yard before the west front (blender/church.py PORCH: 1.25 m out of the towers'
# faces, 14.7 m long with its middle 0.45 m south of the hall's, walls 0.5 m thick, three arches 3.3 m wide between four
# piers 4.627 m apart): the walker goes in under the arches to the doors, round the piers.  The piers' feet in the
# church's frame (gate_town.CHURCH: u east along the hall from its middle, v north): (u0, u1, v0, v1)


def church_porch_piers(ch, out_=1.25, w=14.7, c0=-0.45, th=0.5, arch=3.3, pitch=4.627, end=0.41):
    import math
    uw, hw = -ch['L'] / 2 - out_, w / 2
    out = []
    for k in range(4):                                     # (the front's four, from the north end)
        m = c0 + hw - end - pitch * k
        v1 = c0 + hw if k == 0 else m + (pitch - arch) / 2
        v0 = c0 - hw if k == 3 else m - (pitch - arch) / 2
        out.append((uw, uw + th, v0, v1))
    for sg in (-1, 1):                                     # (each end's short wall back to the tower's face)
        e = c0 + sg * hw
        out.append((uw, -ch['L'] / 2, min(e, e - sg * th), max(e, e - sg * th)))
    c, s_ = math.cos(ch['ang']), math.sin(ch['ang'])
    P = lambda u, v: (ch['c'][0] + u * c - v * s_, ch['c'][1] + u * s_ + v * c)
    return [[P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1)] for u0, u1, v0, v1 in out]


# East of the church in July 1997 (reference/고증/4.8.5 「교회 동쪽」; the scans' roofs in thirteen pairs of 1996 - 1999):
# a paved yard from the church's east wall to x 17.5, in it a small flat-roofed house two storeys high (its roof
# 28.0 m over the sea, 5.9 m over the yard); east of the yard a tiled house of one storey where the town had two
# (eaves 24.5, ridge 26.7 m), south-east of it houses of three and four storeys where the town had one and two (roofs
# 30.3 · 32.1 and 34.4 m).  (x, y, length, width, the long side's way rad, storeys, hipped, the town's house it
# stands for (x, y) or None, wall, roof[, its roof's top over the sea: storeys that high, no stair head drawn]): the
# house it stands for goes with its draws kept, these come at the end.  Roofs by the scans' brightness (#258): the
# small house and the two four-storey ones a light grey slab (3, as bright as the yard's paving), the tiled house
# darker than the church's slate (1, blue-grey tiles: the colour aerial's dark grey)
# The four-storey house north-east of the yard (#258, 1996 - 1999 scans; the town's two-storey box stood 4 m west and
# 4 m north of it): two blocks under one coping 35.7 m over the sea (13.3 m over the lane, three rows of windows over a
# band at 25.5 m), the east one 1 m further south, and the stair's band between them 37.6 m high (its south end not read)
CHURCH_EAST97 = [
    (10.1, -539.7, 8.5, 7.5, 0.12, 2, 0, None, 1, 3),
    (24.6, -525.0, 15.0, 4.8, -1.5932, 1, 1, (23.67, -524.05), None, None),
    (15.51, -548.99, 12.18, 6.14, -0.3926, 3, 0, (15.51, -548.99), None, 3),
    (28.77, -546.01, 17.52, 7.7, 3.1416, 4, 0, (28.77, -546.01), None, 3),
    (36.2, -525.65, 7.7, 9.58, -0.009, 4, 0, (34.99, -522.05), None, 3, 35.7),
    (42.85, -526.2, 5.6, 10.51, -0.009, 4, 0, None, 2, 3, 35.7),
    (40.6, -524.85, 2.8, 7.3, -0.009, 5, 0, None, 2, 3, 37.6),
    # (#259) the six storeys 4.1 m east of it (1996 - 1999 scans, the same outline in every year): 6.5 x 6.4 m under a
    # coping 41.1 m over the sea (window rows 2.9 m apart over a shop's floor, the east wall blind), a light flat roof,
    # the stair's head in its north-west corner 42.5 m; it stands for the town's two-storey box 3 m west of it.  Its
    # neighbours east (a hipped house of one storey, its ridge 25.5 - 26.0 m) and south (24.7 m) where the town had two
    (53.15, -521.49, 6.5, 6.4, -0.004, 6, 0, (49.72, -521.74), 2, 3, 41.1),
    (51.3, -519.65, 2.8, 3.1, -0.004, 7, 0, None, 2, 3, 42.5),
    (66.09, -525.47, 10.63, 8.42, -1.5787, 1, 1, (66.09, -525.47), None, None),
    (48.84, -528.35, 7.07, 5.98, 3.096, 1, 1, (48.84, -528.35), None, None),
]

def church_porch_floor(ch, tow=5.7, front_in=1.15):
    """the floor under the porch between the two towers, in to the gable wall and its doors (the church's box, which is
    cut out of the yard, runs from the towers' faces): open to the walker"""
    import math
    u0, u1, hv = -ch['L'] / 2 - 0.7, -ch['L'] / 2 + front_in - 0.35, ch['W'] / 2 - tow - 0.35
    c, s_ = math.cos(ch['ang']), math.sin(ch['ang'])
    P = lambda u, v: (ch['c'][0] + u * c - v * s_, ch['c'][1] + u * s_ + v * c)
    return [P(u0, -hv), P(u1, -hv), P(u1, hv), P(u0, hv)]

# 챔프2 오락실 (reference/고증/4.10.8 「챔프2 오락실」): not on 연세로 but one block in along 연세로11길, on the south-west
# corner where 연세로9길's north - south leg meets it (the three anthology maps: 2019 문집 25쪽 an 오락실 with a joystick
# on that corner house, 2021 문집 22쪽 「챔투 오락실」, 2022 문집 30 ~ 31쪽 「챔프 II 오락실」; the 2021 문집's text: 「챔프2라는
# 오락실 출입구 옆에 붙어있던 메모지 부착 보드」 for leaving where friends would meet).  The scans of 1997-07-28 (26/16 · 27/17
# · 27/18 in pairs, 0.75 m points): a three-storey roof 9.3 - 10.6 m over the lane (median 9.7) on the corner, x -155.0 .. -149.2,
# y -571.9 .. -564.2; a low ledge 1.5 - 2.6 m high along its north face and round the north-east corner (out 1.7 m
# on the north, 1.2 m on the east); west of it a roof 10.7 - 12.5 m high (median 12.0) to x -162.  The Kakao roadview of 2008-11-12 (2104013 · 2104010 ·
# 2103941): the same corner house in red brick, three storeys, shops on the ground floor; west of it a dark brick house
# of four.  Boxes: (x west, x east, y south, y north, storeys, metres a storey, wall (WALLS97), shop on the ground floor)
CHAMP97 = dict(
    house=(-155.0, -149.2, -571.9, -564.2, 3, 3.2, 0, 1),
    west=(-162.0, -155.1, -572.0, -565.0, 4, 3.0, 1, 0),      # (its ground floor in 1997 not known: no shop front)
    shops=[('챔프2 오락실', 1)],
    # the ledge over the shop fronts: its top over the lane, how far out from the north and the east face, how far it
    # runs down the east face from the corner (the scans read it there for 1.3 m; further south they do not settle it)
    ledge=(2.3, 1.7, 1.2, 1.3),
    # the board for notes by the door on the north face (along it from the north-east corner, m): door, board
    door=(2.2, 3.8), board=(0.5, 1.7, 0.95, 1.85),         # board: from - to along the face, bottom - top over the lane
)
# 연세로11길 open to the walker (2026-11-28, user's request: to walk to 챔프2 오락실): from 연세로's west walk in along
# the lane to the shop's north face and door, and 9길's leg down its east face.  Like 연세로12길 the game draws no
# carriageway or kerb for the lane, so it is one open ground; the houses standing in these boxes are cut out of them
CHAMP_LANE = [
    [(-156.0, -552.4), (-156.0, -562.6), (-104.5, -562.6), (-104.5, -552.4)],
    [(-149.0, -562.6), (-149.0, -574.0), (-143.3, -574.0), (-143.3, -562.6)],
]
# sign_yro97's cells of the house itself (not shop boards): the roof's letters, the coloured glass of the wide windows;
# 챔프2 오락실's board for notes: three cells one over the other (54, 58, 62: 512 x 384)
DOK_CELLS = dict(roof=52, glass=53)
MEMO_CELLS = (54, 58, 62)

# sign_yro97.png's cells, 4 across: (name as painted, background, letters)
SIGNS = [
    ('연세식품', (250, 248, 236), (190, 30, 30)), ('사 진 관', (20, 60, 150), (255, 255, 255)),
    ('알 서 림', (40, 80, 60), (245, 240, 220)), ('식 품 점', (252, 250, 240), (30, 100, 60)),
    ('새마을금고', (30, 110, 60), (255, 255, 255)), ('오 락 실', (20, 20, 24), (255, 90, 70)),
    ('아마데우스', (60, 30, 80), (250, 226, 150)), ('초원분식', (240, 120, 40), (255, 255, 255)),
    ('웬디스버거', (200, 30, 36), (255, 240, 200)), ('레벤호프', (110, 50, 20), (255, 222, 130)),
    ('아트박스', (250, 250, 246), (220, 40, 60)), ('비 잔 틴', (70, 40, 26), (240, 214, 160)),
    ('태림레코드', (24, 24, 30), (250, 220, 90)), ('프리타임', (252, 240, 210), (30, 70, 150)),
    ('영 당구장', (20, 70, 40), (255, 255, 255)), ('베를린호프', (130, 30, 24), (255, 226, 120)),
    ('복지다방', (120, 70, 36), (255, 240, 200)), ('동화은행', (30, 60, 150), (255, 255, 255)),
    ('독수리문구', (250, 210, 40), (30, 40, 120)), ('시골분식', (230, 96, 34), (255, 255, 255)),
    ('이태리분식', (252, 250, 240), (200, 40, 30)), ('연세문화사', (30, 60, 140), (255, 255, 255)),
    ('연희식당', (252, 252, 248), (30, 30, 30)), ('장미당구장', (150, 24, 60), (255, 236, 200)),
    ('쟈 뎅', (60, 36, 24), (240, 210, 150)), ('Y 오락실', (20, 20, 24), (120, 230, 255)),
    ('상아탑분식', (250, 246, 230), (200, 40, 30)), ('다 방', (110, 60, 30), (255, 236, 190)),
    ('당 구 장', (20, 70, 40), (255, 255, 255)), ('오늘의 책', (246, 240, 220), (40, 60, 50)),
    ('기 원', (250, 250, 244), (20, 20, 20)), ('레 코 드', (60, 20, 100), (255, 230, 120)),
    ('신촌반점', (180, 24, 24), (255, 220, 90)), ('가든당구장', (30, 100, 60), (255, 255, 230)),
    ('진 미 락', (190, 30, 30), (255, 226, 120)), ('천 지 문', (30, 30, 36), (240, 200, 90)),
    ('오비넬라', (252, 240, 200), (150, 60, 20)), ('뚱보분식', (250, 220, 60), (200, 40, 30)),
    ('빌 보 드', (24, 30, 80), (255, 255, 255)), ('파 블 로', (250, 246, 236), (90, 40, 110)),
    ('약 국', (252, 252, 250), (30, 130, 70)), ('연세만화랑', (255, 236, 120), (30, 60, 150)),
    ('하이클라스', (30, 40, 100), (255, 240, 180)), ('국 민 은 행', (250, 250, 246), (90, 70, 50)),
    ('쌍쌍호프', (120, 30, 20), (255, 220, 120)), ('스페인하우스', (160, 30, 30), (255, 236, 170)),
    ('초 원 각', (190, 30, 30), (255, 226, 120)), ('독수리약국', (252, 252, 250), (30, 130, 70)),
    ('독수리만화방', (250, 226, 90), (40, 40, 110)), ('챔프2 오락실', (24, 24, 30), (255, 214, 40)),
]
# the name in a shop's entry -> its cell
CELL = {'연세식품': 0, '사진관': 1, '알서림': 2, '식품점': 3, '새마을금고': 4, '오락실': 5, '아마데우스': 6, '초원분식': 7,
        '웬디스버거': 8, '레벤호프': 9, '아트박스': 10, '비잔틴': 11, '태림레코드': 12, '프리타임': 13, '영당구장': 14,
        '베를린호프': 15, '복지다방': 16, '동화은행': 17, '독수리문구': 18, '시골분식': 19, '이태리분식': 20, '연세문화사': 21,
        '연희식당': 22, '장미당구장': 23, '쟈뎅': 24, 'Y오락실': 25, '상아탑분식': 26, '상아탑다방': 27, '상아탑당구장': 28,
        '오늘의 책': 29, '기원': 30, '레코드': 31, '신촌반점': 32, '가든당구장': 33, '진미락': 34, '천지문': 35,
        '오비넬라': 36, '뚱보분식': 37, '빌보드': 38, '파블로': 39, '약국': 40, '연세만화랑': 41, '하이클라스': 42,
        '국민은행': 43, '쌍쌍호프': 44, '스페인하우스': 45, '초원각': 46, '독수리약국': 47, '독수리만화방': 48,
        '챔프2 오락실': 49}
COLS, CELLS = 4, 64          # the atlas: 4 x 16 cells of 512 x 128 (2048 x 2048); SIGNS from cell 0, DOK_CELLS apart

# 연세로's wall signs, the boards standing out from the shops' walls up the floors (tools/sinchon_rotary.py
# yro_wall_signs, blender/town.py yro_signs; reference/고증/4.10.2 「세로 간판」).  sign_yonseiro.png: VS_COLS x 2 cells
# of 2048 / VS_COLS x 468 px over the banner's strip (tools/make_textures.py yro_signs), (words stacked down, background,
# letters, small words over them).  Which sign hangs where:
# - VS_UP: a shop the maps put upstairs (ROWS, floor 2 or 3; DOK97's street house) has the first signs of its own house
# - VS_OWN: the seven storeys of white tile on the west, its signs where the 1600 px copies of 52106 · 52006 show them
#   (their own boards in place of the drawn ones; reference/고증/4.10.2 「세로 간판」)
# - VS_PIN: a house's names on its own free signs (none left since VS_OWN)
# - VS_RUN: the rest of what the 1996 photos read (51979 · 52106: the two rows from the junction north), on the free
#   signs of that side south of y_from, north to south in the photos' order (the houses themselves are not read)
# - VS_ANY: everywhere else the kinds of business the photos and the maps show, by the sign's own draw
VSIGNS = [
    # west, 51979 · 52106
    ('비디오방', (196, 30, 36), (255, 255, 255), '독수리'), ('포켓당구장', (244, 240, 236), (200, 30, 36), 'TJ'),
    ('당구장', (248, 248, 246), (206, 30, 30), 'Y'), ('비디오방', (248, 196, 40), (196, 30, 30), '연세'),
    ('비디오감상', (204, 184, 112), (150, 40, 30), '연세'), ('VIVA', (196, 30, 44), (255, 255, 255), None),
    ('PISA', (248, 248, 250), (30, 60, 150), 'coffee'), ('오원당구클럽', (30, 50, 130), (255, 255, 255), '포켓전용'),
    ('게임프라자', (28, 118, 70), (255, 255, 255), None), ('제니스', (28, 58, 140), (255, 255, 255), None),
    ('하이크라스', (24, 60, 150), (250, 236, 190), '디스코'), ('현대해상화재', (26, 36, 60), (255, 255, 255), None),
    ('신영증권', (30, 58, 44), (255, 255, 255), None),
    # east, 51979 · 52106
    ('여인숙', (250, 250, 250), (30, 60, 150), None), ('비디오감상실', (250, 250, 248), (30, 40, 90), None),
    ('M비디오', (196, 28, 36), (255, 255, 255), None), ('허리우드', (28, 118, 70), (255, 255, 255), '비디오'),
    ('서영외과', (186, 30, 30), (255, 255, 255), '안재훈'), ('이발관', (240, 236, 220), (30, 40, 90), None),
    ('탁구', (250, 250, 248), (206, 30, 30), '복지'),
    # upstairs in the maps (their boards' colours in SIGNS)
    ('영당구장', (20, 20, 24), (255, 200, 60), None), ('복지다방', (240, 228, 196), (110, 50, 20), None),
    ('장미당구장', (196, 30, 60), (255, 255, 255), None), ('다방', (240, 228, 196), (110, 50, 20), '상아탑'),
    ('당구장', (30, 100, 60), (255, 255, 230), '상아탑'), ('가든당구장', (30, 100, 60), (255, 255, 230), None),
    ('연세만화랑', (255, 236, 120), (30, 60, 150), None), ('독수리만화방', (250, 226, 90), (40, 40, 110), None),
    # any
    ('당구장', (250, 250, 246), (206, 30, 30), None), ('다방', (240, 228, 196), (110, 50, 20), None),
    ('기원', (250, 250, 244), (20, 20, 20), None), ('노래방', (30, 60, 160), (255, 230, 80), None),
    # the seven storeys (52106, 1600 px)
    ('동양생명', (206, 34, 40), (255, 255, 255), None), ('개런티', (246, 246, 240), (30, 40, 110), 'NIGHT CLUB'),
    # east, 51979 (1600 px): between M 비디오 and 허리우드 비디오 (the eye clinic's name: 김성 and a third syllable not read)
    ('안과', (24, 34, 70), (214, 40, 36), None), ('동화은행', (30, 60, 150), (255, 255, 255), None),
]
VS_COLS = 18
VS_UP = {'영당구장': 20, '복지다방': 21, '장미당구장': 22, '상아탑다방': 23, '상아탑당구장': 24, '가든당구장': 25,
         '연세만화랑': 26, '독수리만화방': 27, '기원': 30}
VS_PIN = []                                                   # (side, y north, y south, cells)
# (side, y north, y south of the house; then its boards: y along the front, foot and top as shares of the front's height
# over the walk, cell).  The seven storeys in 52106 (1600 px; its front from the north end leftwards, 7 px a metre along
# it at the top, 661 - 690 px from the walk to the roof): 디스코 하이크라스 from the roof down and the night club 개런티
# under it at the north corner, 현대해상화재 · 동양생명 · 신영증권 one over the other some 8 m south of it (± 3 m); 52006
# has the same three edge-on at that corner
VS_OWN = [(-1, -787.5, -816.5, [(-788.4, 0.64, 0.99, 10), (-788.4, 0.31, 0.58, 33),
                                (-795.5, 0.68, 0.86, 11), (-795.5, 0.49, 0.66, 32), (-795.5, 0.31, 0.46, 12)])]
VS_RUN = {-1: (-700.0, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]), 1: (-740.0, [13, 14, 15, 34, 35, 16, 17, 18, 19])}
VS_ANY = [28, 29, 30, 31]


def vsign_cells(signs, blocks=None):
    """sets the cell (the last field) of each of yro_wall_signs' signs [x, y, z, outward way, out, height, cell] by
    VS_UP · VS_PIN · VS_RUN, the rest VS_ANY by the cell yro_wall_signs drew (its draws stay as they were).  The houses of
    VS_OWN (found in blocks, the rows' boxes) lose their drawn signs for their own, added at the end"""
    import math
    own = []
    for s, yn, ys, boards in (VS_OWN if blocks else []):
        b = next(b for b in blocks if b[6] > 0 and (b[0] > -95) == (s > 0) and ys < b[1] < yn and b[7] >= 8)
        cx, cy, L, W, ang, base, lv = b[:7]
        hh = 3.0 * lv                                            # (the front over the walk, as blender/town.py draws it)
        u = (math.cos(ang), math.sin(ang))                       # (L: away from the street)
        signs = [q for q in signs if not ((q[0] > -95) == (s > 0) and ys <= q[1] <= yn)]
        for y, z0, z1, c in boards:
            w = 0.85
            k = (y - cy) / u[0] if abs(u[0]) > 0.5 else 0.0      # (along the front: the row runs north - south)
            t = (-u[1], u[0])
            x = cx - u[0] * (L / 2 + 0.12 + w / 2) + t[0] * k
            yy = cy - u[1] * (L / 2 + 0.12 + w / 2) + t[1] * k
            own.append([round(x, 2), round(yy, 2), round(base + 0.3 + hh * (z0 + z1) / 2, 2), round(math.atan2(-u[1], -u[0]), 4),
                        w, round(hh * (z1 - z0), 2), c])
    side = [1 if math.cos(q[3]) < 0 else -1 for q in signs]       # (the wall faces west: an east house)
    order = sorted(range(len(signs)), key=lambda i: -signs[i][1])  # (north first)
    cell = [None] * len(signs)

    def free(s, yn, ys):
        return [i for i in order if side[i] == s and ys <= signs[i][1] <= yn and cell[i] is None]

    def give(idx, cells):
        for i, c in zip(idx, cells):
            cell[i] = c
        return list(cells[len(idx):])

    houses = [(s, r[0], r[1], r[5]) for s in ROWS for r in ROWS[s]]
    houses.append((1, DOK97['house'][0], DOK97['house'][1], DOK97['house'][6]))
    for s, yn, ys, shops in houses:
        give(free(s, yn, ys), [VS_UP[n] for n, fl in shops if fl >= 2 and n in VS_UP])
    for s, yn, ys, cells in VS_PIN:                              # (what its house has no room for: the free signs
        for c in give(free(s, yn, ys), cells):                   # nearest to it)
            near = sorted(free(s, 1e9, -1e9), key=lambda i: abs(signs[i][1] - (yn + ys) / 2))
            if near:
                cell[near[0]] = c
    for s, (y_from, cells) in VS_RUN.items():
        rest = give(free(s, y_from, -1e9), cells)
        if rest:
            print('연세로 wall signs: no room for', [VSIGNS[c][0] for c in rest])
    for i, q in enumerate(signs):
        q[6] = cell[i] if cell[i] is not None else VS_ANY[q[6] % len(VS_ANY)]
    return signs + own
