"""tools/snapshots.mjs 가 찍은 PNG 를 tools/snapshots.json 의 out 대로 줄이고 붙여 JPEG 로 쓴다.

    python tools/snapshots_compose.py <raw 폴더> [이름,이름] [snapshots.json 경로]
    python tools/snapshots_compose.py --sheet <검토용.jpg> [이름 일부,…]   # README 사진 | 게임 짝을 한 장에

out 항목: {"path": 저장소 루트 기준 경로, "width": 줄일 폭(없으면 그대로), "quality": JPEG 품질(기본 86)}.
grid 항목: {"name", "grid": [shot 이름 …], "cell": [폭, 높이], "gap": 6, "out": [...]} 은 칸마다 가운데를 잘라 맞춘 뒤
위에서 아래로 쌓는다(README 「사진과 비교」에서 사진 두 장을 위아래로 둔 칸).
"""
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def raw_path(raw, name):
    return os.path.join(raw, name.replace('/', '__') + '.png')


def fit(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x0, y0 = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x0, y0, x0 + w, y0 + h))


def save(im, outs):
    for o in outs:
        p = os.path.normpath(os.path.join(ROOT, o['path']))
        if not os.path.isdir(os.path.dirname(p)):
            print('skip (no folder)', o['path'])
            continue
        w = o.get('width')
        out = im if not w or w == im.width else im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        out.save(p, quality=o.get('quality', 86), optimize=True, progressive=True)
        print('wrote', o['path'], out.size)


def sheet(out, only):
    """README 「사진과 비교」의 사진 | 게임 짝을 한 줄씩 쌓은 검토용 그림(저장소 밖에 쓴다)."""
    import re
    from PIL import ImageDraw, ImageFont
    names = re.findall(r'docs/compare/(\w+)_photo\.jpg', open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read())
    names = [n for n in names if not only or any(p in n for p in only)]
    try:
        font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 20)
    except OSError:
        font = ImageFont.load_default()
    H, rows = 300, []
    for n in names:
        p, g = (Image.open(os.path.join(ROOT, f'docs/compare/{n}_{k}.jpg')).convert('RGB') for k in ('photo', 'game'))
        h = min(H, (1600 - 10) / (p.width / p.height + g.width / g.height))    # a row is at most 1600 px wide
        p, g = (im.resize((round(im.width * h / im.height), round(h))) for im in (p, g))
        r = Image.new('RGB', (p.width + g.width + 10, round(h) + 26), 'white')
        r.paste(p, (0, 26))
        r.paste(g, (p.width + 10, 26))
        ImageDraw.Draw(r).text((4, 0), n, fill='black', font=font)
        rows.append(r)
    im = Image.new('RGB', (max(r.width for r in rows), sum(r.height for r in rows)), 'white')
    y = 0
    for r in rows:
        im.paste(r, (0, y))
        y += r.height
    if im.width > 1600:
        im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
    im.save(out, quality=80)
    print('sheet', out, im.size)


def main():
    if sys.argv[1] == '--sheet':     # python tools/snapshots_compose.py --sheet <out.jpg> [이름 일부,…]
        return sheet(sys.argv[2], [p for p in (sys.argv[3] if len(sys.argv) > 3 else '').split(',') if p])
    raw = sys.argv[1]
    only = [p for p in (sys.argv[2] if len(sys.argv) > 2 else '').split(',') if p]
    picked = lambda n: not only or any(n == p or n.startswith(p) for p in only)
    spec_path = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else os.path.join(HERE, 'snapshots.json')
    spec = json.load(open(spec_path, encoding='utf-8'))
    for s in spec['shots']:
        if 'grid' in s:
            if not any(picked(n) for n in s['grid'] + [s['name']]):
                continue
            w, h = s['cell']
            g = s.get('gap', 6)
            cells = [fit(Image.open(raw_path(raw, n)).convert('RGB'), w, h) for n in s['grid']]
            im = Image.new('RGB', (w, len(cells) * h + (len(cells) - 1) * g), 'white')
            for k, c in enumerate(cells):
                im.paste(c, (0, k * (h + g)))
            save(im, s['out'])
        elif picked(s['name']) and s.get('out'):
            p = raw_path(raw, s['name'])
            if os.path.exists(p):
                save(Image.open(p).convert('RGB'), s['out'])


if __name__ == '__main__':
    main()
