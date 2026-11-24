"""multi.py <pano> <out> c0:c1:r0:r1 ...  side-by-side 3x crops with rulers"""
import os
import sys, subprocess
from PIL import Image
D = os.environ.get('ST_WORK', '/tmp/stimson_rv')
pano, out, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
ims = []
for i, s in enumerate(specs):
    c0, c1, r0, r1 = s.split(':')
    sc = s.split(':')
    f = f'{D}/_m{i}.png'
    subprocess.run(['python3', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crop.py'), f'{D}/st/tiles/eq/{pano}.jpg', c0, c1, r0, r1, '4', f], check=True)
    ims.append(Image.open(f))
W = Image.new('RGB', (sum(i.width + 10 for i in ims), max(i.height for i in ims)), 'white')
x = 0
for i in ims: W.paste(i, (x, 0)); x += i.width + 10
W.save(out)
