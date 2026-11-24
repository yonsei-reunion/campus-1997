"""crop.py <eq.jpg> <c0> <c1> <r0> <r1> <scale> <out>  -- crop equirect columns c0..c1 (may wrap), rows r0..r1,
upscale, draw a ruler (ticks every 10 px of equirect, labels every 50) on top and left."""
import sys
from PIL import Image, ImageDraw
f, c0, c1, r0, r1, s, out = sys.argv[1], *map(int, sys.argv[2:7]), sys.argv[7]
im = Image.open(f)
big = Image.new('RGB', (8192, 2048)); big.paste(im, (0, 0)); big.paste(im, (4096, 0))
if c0 < 0: c0 += 4096; c1 += 4096
cr = big.crop((c0, r0, c1, r1)).resize(((c1 - c0) * s, (r1 - r0) * s), Image.LANCZOS)
W = Image.new('RGB', (cr.width + 40, cr.height + 20), 'white'); W.paste(cr, (40, 20)); d = ImageDraw.Draw(W)
for c in range(c0 - c0 % 5 + 5, c1, 5):
    x = 40 + (c - c0) * s; d.line([(x, 4 if c % 50 == 0 else (10 if c % 10 == 0 else 15)), (x, 20)], fill="red")
    if c % 50 == 0: d.text((x + 2, 0), str(c % 4096), fill='black')
for r in range(r0 - r0 % 10 + 10, r1, 10):
    y = 20 + (r - r0) * s; d.line([(32 if r % 50 else 24, y), (40, y)], fill='red')
    if r % 50 == 0: d.text((0, y - 10), str(r), fill='black')
W.save(out)
