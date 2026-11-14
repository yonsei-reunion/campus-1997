"""download the 32 tiles (8 x 4 of 512) of each past pano and assemble the 4096 x 2048 equirect.
   YRO_WORK=<dir> python -I fetch.py <years comma list, e.g. 2008,2009> [maxper]"""
import sys, json, os, io, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

D = os.environ.get('YRO_WORK', '/tmp/yonsei_ro')     # paths.jsonl (from paths.mjs) is read from here
years = sys.argv[1].split(',')
OUT = f'{D}/tiles/eq'
os.makedirs(OUT, exist_ok=True)
items = {}
for ln in open(f'{D}/paths.jsonl'):
    j = json.loads(ln)
    for it in j['items']:
        if it['date'][:4] in years and it.get('imagePath'):
            items.setdefault(it['pano'], dict(it, nodes=[]))['nodes'].append(j['node'])
json.dump(items, open(f'{D}/panos.json', 'w'), indent=0)


def get(url):
    rq = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://map.kakao.com/'})
    for _ in range(3):
        try:
            return urllib.request.urlopen(rq, timeout=30).read()
        except Exception as e:
            err = e
    raise err


def one(pano):
    it = items[pano]
    f = f'{OUT}/{pano}.jpg'
    if os.path.exists(f):
        return pano, 'have'
    p = it['imagePath']; key = p.split('/')[-1]
    W = Image.new('RGB', (4096, 2048))
    for i in range(1, 33):
        b = get(f'https://map.kakaocdn.net/map_roadview/{p}/{key}_{i:02d}.jpg')
        im = Image.open(io.BytesIO(b)).convert('RGB')
        r, c = (i - 1) // 8, (i - 1) % 8
        W.paste(im, (c * 512, r * 512))
    W.save(f, quality=95)
    return pano, 'ok'


with ThreadPoolExecutor(6) as ex:
    for pano, st in ex.map(one, sorted(items)):
        print(pano, items[pano]['date'], st, flush=True)
