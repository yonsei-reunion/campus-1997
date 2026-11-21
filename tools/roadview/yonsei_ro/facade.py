"""연세로 양쪽 가게 줄의 앞면 띠: 로드뷰 파노라마(fetch.py 가 이은 4096 x 2048 정거원통)를 길과 나란한 세로 면에 펴서
파노라마마다 한 칸씩 늘어놓는다(reference/고증/4.10.8_연세로_가게_줄.md 「잰 법」).

    YRO_WORK=<폴더> .venv/bin/python tools/roadview/yonsei_ro/facade.py <2008|2009> <E|W> <이름>
        -> $YRO_WORK/fac/<이름>_NN.jpg (다섯 칸씩)

- $YRO_WORK 에 있어야 하는 것: walk.mjs 의 출력 walk_n.jsonl · walk_s.jsonl(지금 노드의 게임 좌표), paths.jsonl,
  fetch.py 가 쓴 panos.json · tiles/eq/<id>.jpg
- 방위: 정거원통의 왼쪽 끝이 차가 가는 쪽이고 열은 시계 방향으로 돈다. 열 c 의 방위 = 360 · (c + 0.5) / 4096 − northAngle
  (2008년 8월 남쪽으로 달린 차 −178°, 2009년 3월 북쪽으로 달린 차 0° 안팎). 가운데 열이 앞이라고 두면 길 반대쪽이 거울상으로
  나온다
- 면: 차에서 d m 떨어진 세로 면. 가까운 쪽은 앞벽 − 3.2 m, 먼 쪽은 앞벽 + 3.2 m(차가 제 차로 가운데를 달린다고 둠). 면의
  한 화소가 1 / ppm m 라 폭은 어림이고(카카오의 자리를 쓰므로 길 방향 ± 3 m), 층수 · 벽 · 간판을 보는 데 씀
- 칸 머리의 y 는 그 파노라마가 붙은 지금 노드의 게임 y. 붉은 눈금은 길 위 3 m 마다
- 동쪽 줄은 북쪽이 왼쪽(동쪽을 보고 선 눈), 서쪽 줄은 남쪽이 왼쪽. 화면은 저장소에 넣지 않는다(CLAUDE.md 「고증 자료」)
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

D = os.environ.get('YRO_WORK', '/tmp/yonsei_ro')
W, H = 4096, 2048


def node_xy():
    out = {}
    for f in ('walk_n', 'walk_s'):
        for ln in open(f'{D}/{f}.jsonl'):
            if ln.startswith('{'):
                j = json.loads(ln)
                out[j['pano']] = j['xy']
    return out


def front(y, side):
    """the fronts from the street's middle (고증 4.10.1): 12 m north of y -640, 9.5 m east and 10.5 m west south of it"""
    return 12.0 if y > -640 else (9.5 if side == 'E' else 10.5)


def tile(P, p, side, d, half=6.5, up=26.0, down=2.5, ppm=30):
    it = P[str(p)]
    img = np.asarray(Image.open(f'{D}/tiles/eq/{p}.jpg').convert('RGB'))
    us = np.arange(-half, half, 1 / ppm)                 # along the street, north +
    vs = np.arange(up, -down, -1 / ppm)
    U, V = np.meshgrid(us, vs)
    sgn = 1 if side == 'E' else -1
    bear = np.degrees(np.arctan2(sgn * d, U))            # (east = sgn d, north = U)
    el = np.arctan2(V, np.hypot(d, U))
    a = np.radians(bear + it['northAngle'])
    c = (a % (2 * np.pi)) / (2 * np.pi) * W - 0.5
    r = (np.pi / 2 - el) / np.pi * H - 0.5
    out = img[np.clip(np.round(r).astype(int), 0, H - 1), np.round(c).astype(int) % W]
    return out[:, ::-1] if side == 'E' else out          # (facing east, north is on the left)


def main(year, side, name, n=5, ppm=30, up=26.0):
    P = json.load(open(f'{D}/panos.json'))
    xy = node_xy()
    panos = sorted([(xy[it['nodes'][0]][1], int(p)) for p, it in P.items()
                    if it['date'][:4] == year and it['date'][5:7] in ('08', '03') and it['nodes'][0] in xy], reverse=True)
    near = (year == '2009') == (side == 'E')             # (2009: northbound, the east half; 2008: southbound, the west)
    tiles = []
    for y, p in panos:
        im = Image.fromarray(tile(P, p, side, front(y, side) + (-3.2 if near else 3.2), ppm=ppm, up=up))
        dr = ImageDraw.Draw(im)
        dr.rectangle([0, 0, 150, 16], fill=(0, 0, 0))
        dr.text((3, 2), 'y%.0f p%d' % (y, p), fill=(255, 255, 0))
        for k in range(1, 9):                            # (every 3 m over the road: the cameras rode 2.7 - 3.0 m up)
            zz = int((up - (3.0 * k - 2.8)) * ppm)
            dr.line([(0, zz), (10, zz)], fill=(255, 0, 0), width=2)
        tiles.append(im)
    if side == 'W':
        tiles = tiles[::-1]
    os.makedirs(f'{D}/fac', exist_ok=True)
    for i in range(0, len(tiles), n):
        part = tiles[i:i + n]
        s = Image.new('RGB', (sum(t.width for t in part) + 4 * (len(part) - 1), part[0].height), 'white')
        x = 0
        for t in part:
            s.paste(t, (x, 0))
            x += t.width + 4
        s.save(f'{D}/fac/{name}_{i // n:02d}.jpg', quality=85)
    print(name, len(tiles), 'tiles')


if __name__ == '__main__':
    main(*sys.argv[1:4])
