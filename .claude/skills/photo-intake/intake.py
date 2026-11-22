"""받은 참고 사진을 훑어보고(list), 가릴 곳을 가려 줄인 사본을 만든다(make). 원본은 고치지 않는다.

  python3 .claude/skills/photo-intake/intake.py list <받은 폴더> <보기 폴더>
      하위 폴더까지 돌며 사진마다 번호 · 크기 · EXIF 의 찍은 때 · 카메라를 적고, 보기용 사본(긴 변 1400 px,
      <번호>_<하위 폴더>__<이름>.jpg)을 보기 폴더에 쓴다. 보기 사본을 한 장씩 열어 장소와 가릴 곳을 정한다.

  python3 .claude/skills/photo-intake/intake.py make <jobs.json> <받은 폴더> <out 폴더>
      jobs.json: [{ "src": "하위/원래 이름.jpg", "name": "2004-09_용재관_현관_차양.jpg",
                    "faces": [[cx, cy, r], ...],         얼굴: 가운데와 반지름 → 조금 넉넉한 네모를 모자이크
                    "boxes": [[x0, y0, x1, y1], ...],    그 밖에 가릴 네모(번호판 · 이름표 · 화면)
                    "crop": [x0, y0, x1, y1],            가린 뒤 잘라 낼 네모(없으면 전체)
                    "unit": 1400 }, ...]                 좌표를 읽은 그림의 긴 변 px(보기 사본에서 읽었으면 1400. 없으면 원본 화소)
      좌표는 EXIF 방향대로 돌린 뒤의 화소. 긴 변 1600 px 로 줄여 JPEG(q86)로 새로 쓴다: EXIF(위치 · 기기)는 남지 않는다.
      "name" 이 없는 항목은 건너뛴다(저장소에 넣지 않을 사진).
"""
import json
import os
import sys

from PIL import Image, ImageOps

EXT = ('.jpg', '.jpeg', '.png', '.heic', '.tif', '.tiff', '.webp')
VIEW, LONG = 1400, 1600


def photos(src):
    out = []
    for d, _, fs in os.walk(src):
        out += [os.path.relpath(os.path.join(d, f), src) for f in fs if f.lower().endswith(EXT)]
    return sorted(out)


def exif(im):
    e = im.getexif()
    sub = e.get_ifd(0x8769) if hasattr(e, 'get_ifd') else {}
    when = sub.get(36867) or sub.get(36868) or e.get(306)            # DateTimeOriginal · Digitized · DateTime
    cam = ' '.join(str(v).strip() for v in (e.get(271), e.get(272)) if v)
    gps = bool(e.get_ifd(0x8825)) if hasattr(e, 'get_ifd') else False
    return when, cam, gps


def cmd_list(src, view):
    os.makedirs(view, exist_ok=True)
    for i, rel in enumerate(photos(src), 1):
        try:
            im = Image.open(os.path.join(src, rel))
        except OSError as ex:
            print('%02d %s: 열지 못함 (%s)' % (i, rel, ex))
            continue
        when, cam, gps = exif(im)
        im = ImageOps.exif_transpose(im).convert('RGB')
        w, h = im.size
        im.thumbnail((VIEW, VIEW), Image.LANCZOS)
        name = '%02d_%s.jpg' % (i, os.path.splitext(rel)[0].replace(os.sep, '__'))
        im.save(os.path.join(view, name), quality=85)
        print('%02d %s: %d x %d, 찍은 때 %s, 카메라 %s%s -> %s' % (i, rel, w, h, when or '없음', cam or '없음', ', 위치 있음' if gps else '', name))


def mosaic(im, box):
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(im.width, x1), min(im.height, y1)
    if x1 <= x0 or y1 <= y0:
        return
    r = im.crop((x0, y0, x1, y1))
    n = max(6, max(r.width, r.height) // 5)                           # (칸이 대상의 5분의 1: 눈 · 코 · 글자가 한 칸에 뭉개짐)
    small = r.resize((max(1, r.width // n), max(1, r.height // n)), Image.BILINEAR)
    im.paste(small.resize(r.size, Image.NEAREST), (x0, y0))


def cmd_make(jobs, src, out):
    os.makedirs(out, exist_ok=True)
    for j in json.load(open(jobs, encoding='utf-8')):
        if not j.get('name'):
            continue
        im = ImageOps.exif_transpose(Image.open(os.path.join(src, j['src']))).convert('RGB')
        k = max(im.size) / j['unit'] if j.get('unit') else 1.0
        for cx, cy, r in j.get('faces', []):
            mosaic(im, ((cx - 1.25 * r) * k, (cy - 1.45 * r) * k, (cx + 1.25 * r) * k, (cy + 1.45 * r) * k))
        for b in j.get('boxes', []):
            mosaic(im, [v * k for v in b])
        if j.get('crop'):
            im = im.crop(tuple(int(round(v * k)) for v in j['crop']))
        if max(im.size) > LONG:
            im.thumbnail((LONG, LONG), Image.LANCZOS)
        p = os.path.join(out, j['name'])
        im.save(p, quality=86, optimize=True)
        print('%s: %d x %d, %d KB, 가린 곳 %d' % (j['name'], im.width, im.height, os.path.getsize(p) // 1024,
                                              len(j.get('faces', [])) + len(j.get('boxes', []))))


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == 'list':
        cmd_list(a[1], a[2])
    elif len(a) == 4 and a[0] == 'make':
        cmd_make(a[1], a[2], a[3])
    else:
        sys.exit(__doc__)
