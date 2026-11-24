"""xm.py out.png pano:c0:c1:r0:r1 ...  crops from several panos side by side (4x)"""
import os
import sys, subprocess
from PIL import Image, ImageDraw
D = os.environ.get('ST_WORK', '/tmp/stimson_rv')
ims = []
for i, s in enumerate(sys.argv[2:]):
    p, c0, c1, r0, r1 = s.split(':')
    f = f'{D}/_x{i}.png'
    subprocess.run(['python3', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crop.py'), f'{D}/st/tiles/eq/{p}.jpg', c0, c1, r0, r1, '4', f], check=True)
    im = Image.open(f); W = Image.new('RGB', (im.width, im.height + 14), 'white'); W.paste(im, (0, 14)); ImageDraw.Draw(W).text((40, 0), p[-4:], fill='blue'); ims.append(W)
W = Image.new('RGB', (sum(i.width + 10 for i in ims), max(i.height for i in ims)), 'white'); x = 0
for i in ims: W.paste(i, (x, 0)); x += i.width + 10
W.save(sys.argv[1])
