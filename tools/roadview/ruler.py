# Read pixel columns off roadview screenshots: crops with a ruler in the ORIGINAL pixel units.
#   python ruler.py crop  <in.png> <out.png> x0 y0 x1 y1 [scale=2]     ticks every 10 px, labels every 50 (x) and 50 (y)
#   python ruler.py stack <out.png> file:x0:y0:x1:y1 ...                 several crops scaled to width 1380, one above another
#   python ruler.py sheet <out.png> file ...                             2-up contact sheet at half size, red line at x 694
# Read an edge where it is sharpest (mid-height of a wall); a corner pier's outer edge is the corner.  The image a
# viewer shows you may be scaled again: always read positions off the printed labels, not off displayed pixels.
import sys
from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def ruled(f, x0, y0, x1, y1, width=None, scale=None):
    im = Image.open(f).convert('RGB').crop((x0, y0, x1, y1))
    sc = width / im.width if width else scale
    im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    fn = font(16)
    for x in range((x0 // 10 + 1) * 10, x1, 10):
        X = (x - x0) * sc
        L = 16 if x % 50 == 0 else 6
        d.line([(X, 0), (X, L)], fill=(255, 0, 0), width=1)
        d.line([(X, im.height - L), (X, im.height)], fill=(255, 0, 0), width=1)
        if x % 50 == 0:
            d.text((X + 2, 14), str(x), fill=(255, 255, 0), font=fn, stroke_width=2, stroke_fill=(0, 0, 0))
    for y in range((y0 // 50 + 1) * 50, y1, 50):
        Y = (y - y0) * sc
        d.line([(0, Y), (12, Y)], fill=(0, 255, 255), width=2)
        d.text((14, Y - 8), str(y), fill=(0, 255, 255), font=fn, stroke_width=2, stroke_fill=(0, 0, 0))
    return im, fn


def main(a):
    cmd = a[0]
    if cmd == 'crop':
        f, out, x0, y0, x1, y1 = a[1], a[2], *map(int, a[3:7])
        im, _ = ruled(f, x0, y0, x1, y1, scale=float(a[7]) if len(a) > 7 else 2.0)
        im.save(out)
    elif cmd == 'stack':
        out, tiles = a[1], []
        for sp in a[2:]:
            f, x0, y0, x1, y1 = sp.rsplit(':', 4)
            im, fn = ruled(f, int(x0), int(y0), int(x1), int(y1), width=1380)
            ImageDraw.Draw(im).text((6, im.height - 24), f.split('/')[-1], fill=(0, 255, 255), font=fn, stroke_width=2, stroke_fill=(0, 0, 0))
            tiles.append(im)
        S = Image.new('RGB', (1380, sum(t.height + 4 for t in tiles)), (40, 40, 40))
        y = 0
        for t in tiles:
            S.paste(t, (0, y))
            y += t.height + 4
        S.save(out)
    elif cmd == 'sheet':
        out, files = a[1], a[2:]
        fn = font(22)
        S = Image.new('RGB', (1388, 450 * ((len(files) + 1) // 2)))
        for i, f in enumerate(files):
            im = Image.open(f).convert('RGB')
            d = ImageDraw.Draw(im)
            d.line([(694, 0), (694, 900)], fill=(255, 0, 0), width=1)
            for x in range(0, 1388, 50):
                d.line([(x, 880), (x, 900)], fill=(255, 255, 0), width=2)
            d.text((10, 860), f.split('/')[-1], fill=(255, 255, 0), font=fn)
            S.paste(im.resize((694, 450)), ((i % 2) * 694, (i // 2) * 450))
        S.save(out)
    else:
        print(__doc__ or open(__file__).read().split('\nimport')[0])


if __name__ == '__main__':
    main(sys.argv[1:])
