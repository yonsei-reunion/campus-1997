"""연세로's shop rows from the bridge to the junction as they stood in July 1997, house by house
(reference/고증/4.10.8_연세로_가게_줄.md).

- where each house stood and how wide: the roofs of the 1997-07-28 scans (26/16 · 27/17 · 27/18 · 27/19 at the ground,
  tools/aerial97.py), which OSM's outlines of today follow but for the lots rebuilt since
- storeys: the roofs' heights over the walk in those scans (pairs of frames, 2.5 m windows every 2.5 m along both rows,
  4 and 8 m behind the fronts), a storey to 3.2 - 3.6 m
- walls: the Kakao roadview of 2008-08 (west half) and 2009-03 (east half, no leaves) where the house of 1997 still
  stood (the same frontage and height); a later front's colour is not 1997's, so those are the nearest of the four
  bands (blender/town.py: 0 red brick, 1 cream, 2 grey, 3 white tile)
- shops: the two anthologies' street maps (2019 문집 25쪽 「1990 그때 그 시절 다시 보는 신촌거리」, 2021 문집 22 ~ 23쪽
  「90년대 신촌 그 때 그 거리」), block by block between the side streets; where the two differ the 2019 map's order.
  Which house of a block a shop was in is not known but for the few the roadview still has (새마을금고, 사진관, the
  1 · 2 · 3 floors of 상아탑분식's house): the names are laid along the block in the maps' order

ROWS[side]: (y of the north wall, y of the south wall, storeys, wall band, depth m, shops), north to south;
side +1 east, -1 west.  shops: (name, floor); the name is a cell of sign_yro97.png (SIGNS, tools/make_textures.py
yro97_signs).  The last house of each side (금강제화, 홍익문고) and the two south of the last side street stay
tools/sinchon_rotary.py's (YRO_FIXED: the 1996 photos, the corner's landmarks).
"""

ROWS = {
    1: [
        # 연세로 (the lane east along the bank's foot, y -516) to 연세로12길: one house in two parts, five storeys with
        # the top floor set back and a low shop on its south (2009: 연대포토랜드 still in it); south of it 창천교회's
        # paved yard, open to the street (cars parked on it in the scans)
        (-520.0, -531.0, 5, 2, 12.0, [('연세식품', 1)]),
        (-531.0, -540.0, 2, 1, 10.0, [('사진관', 1)]),
        # 연세로12길 to 명물1길: the lot of 독수리다방 · 초원각 · 독수리약국 was a pit in July 1997 (PIT: 독수리빌딩 going
        # up); the three-storey house south of it stood on
        (-587.6, -600.0, 3, 1, 10.0, [('알서림', 1), ('식품점', 1)]),
        # 명물1길 to the street at y -700
        (-604.0, -610.6, 2, 1, 9.0, [('새마을금고', 1)]),
        (-610.8, -620.6, 5, 2, 11.0, [('오락실', 1)]),
        (-620.8, -624.6, 2, 1, 9.0, []),
        (-624.8, -639.1, 4, 3, 12.0, []),
        (-639.2, -647.4, 4, 2, 12.0, []),
        (-647.5, -656.0, 4, 1, 12.0, []),
        (-656.6, -669.6, 3, 3, 11.0, [('아마데우스', 1)]),
        (-669.9, -681.0, 4, 0, 12.0, [('초원분식', 1)]),
        (-681.2, -695.0, 4, 2, 12.0, [('웬디스버거', 1)]),
        # the street at y -700 to 명물길
        (-703.5, -715.0, 4, 3, 12.0, [('레벤호프', 1)]),
        (-715.1, -729.0, 3, 1, 10.0, [('아트박스', 1)]),
        # 명물길 to 연세로4길
        (-755.5, -761.0, 4, 3, 11.0, [('비잔틴', 1)]),
        (-761.1, -770.6, 5, 2, 12.0, [('태림레코드', 1)]),
        # 연세로4길 to 연세로2길: three low houses, then three- and four-storey ones (the towers of today came later);
        # the four at its south end are YRO_FIXED's
        (-779.5, -788.3, 2, 1, 10.0, [('프리타임', 1), ('영당구장', 2)]),
        (-788.4, -798.4, 2, 3, 10.0, [('베를린호프', 1)]),
        (-798.5, -808.6, 2, 2, 10.0, [('복지다방', 2)]),
        (-809.0, -822.0, 3, 1, 12.0, [('사우나', 1)]),
        (-823.0, -834.5, 3, 3, 12.0, []),
        (-835.0, -848.4, 4, 2, 13.0, []),
    ],
    -1: [
        # 연세로13길 (along the bank's foot) to 연세로11길
        (-521.5, -530.0, 5, 2, 12.0, [('독수리문구', 1)]),
        (-530.1, -540.3, 5, 3, 12.0, [('시골분식', 1), ('이태리분식', 1)]),
        (-540.5, -552.0, 1, 1, 9.0, [('연세문화사', 1)]),
        # 연세로11길 to 연세로9길
        (-563.0, -574.5, 3, 1, 12.0, [('연희식당', 1), ('장미당구장', 2)]),
        (-574.7, -590.5, 4, 3, 13.0, [('쟈뎅', 1), ('Y오락실', 1)]),
        (-590.7, -602.0, 5, 1, 12.0, [('상아탑분식', 1), ('상아탑다방', 2), ('상아탑당구장', 3)]),
        # 연세로9길 to 연세로7길
        (-610.5, -619.5, 4, 3, 11.0, [('오늘의 책', 1), ('기원', 2)]),
        (-620.0, -631.0, 4, 0, 11.0, [('레코드', 1)]),
        (-634.5, -645.5, 8, 2, 13.0, [('신촌반점', 1), ('가든당구장', 2)]),
        (-646.0, -659.6, 7, 2, 14.0, [('진미락', 1)]),
        (-659.9, -668.8, 5, 2, 12.0, [('천지문', 1)]),
        (-669.0, -680.6, 5, 1, 13.0, [('오비넬라', 1), ('뚱보분식', 1)]),
        (-680.9, -694.0, 3, 3, 12.0, [('빌보드', 1), ('파블로', 1)]),
        # 연세로7길 to 연세로5길
        (-705.0, -716.5, 7, 3, 13.0, [('약국', 1), ('연세만화랑', 3)]),
        (-721.5, -736.0, 4, 3, 12.0, [('오락실', 1)]),
        # 연세로5길 to the street at y -888: a small open corner with trees first (the scans: no roof before y -783),
        # then the seven storeys of white tile and dark window bands (52006 · 52106: 현대예식장's sign up its corner,
        # 신영증권 on its roof; the scans: 32 m along the street, its roof 22 - 25 m over the walk), a paved court
        # with parked cars south of it
        (-787.5, -816.5, 7, 3, 16.0, [('하이클라스', 1), ('국민은행', 1)]),
        (-823.0, -833.8, 3, 1, 12.0, []),
        (-834.0, -842.5, 4, 2, 12.0, []),
        (-846.0, -861.0, 3, 3, 13.0, [('쌍쌍호프', 1)]),
        (-862.0, -876.2, 4, 3, 14.0, []),
        (-876.4, -883.5, 5, 3, 13.0, []),          # (52006: the white five of INDIS · 바둑 · 학원)
    ],
}
# the shop on the house YRO_FIXED keeps north of each corner's landmark (west: the cream three north of 금강제화)
FIXED_SHOPS = {(-1, 3, 1): [('스페인하우스', 1)]}

# 독수리빌딩's lot, east side between 연세로12길 and the house at y -587.6: old low houses in the scans of 1996-12
# (독수리다방's among them), a pit shored with steel struts in 1997-07-28 (26/16 · 27/17 · 27/18: the same lattice at
# the same place in all three, 0 - 2 m over the walk, so beams at the ground's level over a hole, not a frame going
# up), a tall block finished in 1998-10.  Its outline in the three frames
PIT = [(-83.6, -563.6), (-69.0, -562.0), (-55.5, -561.5), (-53.0, -574.0), (-58.0, -584.5), (-63.5, -592.5), (-76.0, -591.5),
       (-83.2, -587.2)]

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
    ('복지다방', (120, 70, 36), (255, 240, 200)), ('사 우 나', (30, 90, 150), (255, 255, 255)),
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
]
# the name in a shop's entry -> its cell
CELL = {'연세식품': 0, '사진관': 1, '알서림': 2, '식품점': 3, '새마을금고': 4, '오락실': 5, '아마데우스': 6, '초원분식': 7,
        '웬디스버거': 8, '레벤호프': 9, '아트박스': 10, '비잔틴': 11, '태림레코드': 12, '프리타임': 13, '영당구장': 14,
        '베를린호프': 15, '복지다방': 16, '사우나': 17, '독수리문구': 18, '시골분식': 19, '이태리분식': 20, '연세문화사': 21,
        '연희식당': 22, '장미당구장': 23, '쟈뎅': 24, 'Y오락실': 25, '상아탑분식': 26, '상아탑다방': 27, '상아탑당구장': 28,
        '오늘의 책': 29, '기원': 30, '레코드': 31, '신촌반점': 32, '가든당구장': 33, '진미락': 34, '천지문': 35,
        '오비넬라': 36, '뚱보분식': 37, '빌보드': 38, '파블로': 39, '약국': 40, '연세만화랑': 41, '하이클라스': 42,
        '국민은행': 43, '쌍쌍호프': 44, '스페인하우스': 45}
COLS, CELLS = 4, 48          # the atlas: 4 x 12 cells of 512 x 128 (2048 x 1536 padded to 2048 x 2048)
