"""Download Copernicus DEM GLO-30 tiles around Yonsei Sinchon campus and write a local heightmap grid (meters) in
campus-local coordinates.  Local frame: origin lat0/lon0, x = east (m), y = north (m).

  .venv/bin/python tools/fetch_terrain.py near    # data/terrain.json      10 m grid, +-1400 m
  .venv/bin/python tools/fetch_terrain.py far     # data/terrain_far.json  100 m grid, +-8000 m

Copernicus GLO-30 (1 arc-second, TanDEM-X 2011-2015, heights over EGM2008) is a surface model: roofs are in it.
The halls and town blocks are opened out of it on its own grid (a grey opening ~80 m across: whatever cannot hold
that footprint goes, the slopes stay; under OSM's halls a wider one for the big blocks), then smoothed a little.
reference/고증.md 2.8 has the check against the 1:25000 maps' spot heights and contours (the old source, AWS
Terrarium, ran ~10 m high in the valley).
The tiles (30 MB each) are cached in data/raw/copernicus/ (not in git).
© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union
and ESA; all rights reserved."""
import math, json, os, sys, urllib.request
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon
from scipy import ndimage

LAT0, LON0 = 37.5640, 126.9380
KX = 111320.0 * math.cos(math.radians(LAT0))       # (tools/build_campus.py xy())
KY = 110574.0
MODE = sys.argv[1] if len(sys.argv) > 1 else 'near'
HALF, STEP, NAME = {'near': (1400, 10, 'terrain.json'), 'far': (8000, 100, 'terrain_far.json')}[MODE]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'data')
RAW = os.path.join(OUT, 'raw', 'copernicus')
URL = 'https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif'


def tile(lat, lon):
    """one 1 x 1 degree tile, 3600 x 3600, pixel-is-point: pixel (r, c) at (lat + 1 - r / 3600, lon + c / 3600)"""
    n = 'Copernicus_DSM_COG_10_N%02d_00_E%03d_00_DEM' % (lat, lon)
    p = os.path.join(RAW, n + '.tif')
    if not os.path.exists(p):
        os.makedirs(RAW, exist_ok=True)
        print('downloading', n)
        urllib.request.urlretrieve(URL.format(n=n), p + '.part')
        os.replace(p + '.part', p)
    a = np.array(Image.open(p), dtype=np.float64)
    assert a.shape == (3600, 3600), a.shape
    return a


lat_lo, lat_hi = LAT0 - (HALF + 600) / KY, LAT0 + (HALF + 600) / KY
lon_lo, lon_hi = LON0 - (HALF + 600) / KX, LON0 + (HALF + 600) / KX
lats = range(int(math.floor(lat_lo)), int(math.floor(lat_hi)) + 1)
lons = range(int(math.floor(lon_lo)), int(math.floor(lon_hi)) + 1)
# a mosaic on the tiles' common grid (rows from the north edge of the top tile row, columns from the west edge)
top, west = max(lats) + 1, min(lons)
M = np.zeros((3600 * len(lats), 3600 * len(lons)))
for i, la in enumerate(sorted(lats, reverse=True)):
    for j, lo in enumerate(lons):
        M[i * 3600:(i + 1) * 3600, j * 3600:(j + 1) * 3600] = tile(la, lo)
r0 = max(0, int((top - lat_hi) * 3600) - 10); r1 = min(M.shape[0], int((top - lat_lo) * 3600) + 10)
c0 = max(0, int((lon_lo - west) * 3600) - 10); c1 = min(M.shape[1], int((lon_hi - west) * 3600) + 10)
W = M[r0:r1, c0:c1]

# 1" is 30.9 m north-south and 24.5 m east-west here: a 3 x 3 cross reaches ~25 m east-west and ~31 m north-south.
fp = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
O = ndimage.grey_opening(W, footprint=fp)
# Blocks too big for that (the hospital, 공학원, 경영관, 백주년기념관's drum): under the halls OSM has
# (data/raw/osm_campus.json, the campus and the hospital), 15 m round them, a wider opening (5 x 5, ~130 m) where it
# is lower, eased in over a pixel.  (7 x 7 cut the hillside halls' slopes; the map check in reference/고증.md 2.8.)
osm = json.load(open(os.path.join(OUT, 'raw', 'osm_campus.json')))['elements']
mask_im = Image.new('L', (W.shape[1], W.shape[0]), 0)
draw = ImageDraw.Draw(mask_im)
for e in osm:
    if not e.get('tags', {}).get('building') or len(e.get('geometry') or []) < 4:
        continue
    pg = Polygon([((p['lon'] - LON0) * KX, (p['lat'] - LAT0) * KY) for p in e['geometry']]).buffer(15.0)
    for part in getattr(pg, 'geoms', [pg]):
        draw.polygon([((LON0 + x / KX - west) * 3600.0 - c0, (top - (LAT0 + y / KY)) * 3600.0 - r0)
                      for x, y in part.exterior.coords], fill=255)
wb = np.clip(ndimage.gaussian_filter((np.array(mask_im) > 0).astype(float), 0.7) * 1.5, 0, 1)
O5 = ndimage.grey_opening(W, size=(5, 5))
G = ndimage.gaussian_filter(O - wb * np.maximum(O - O5, 0.0), 0.8)


def elev(x, y):
    lat = LAT0 + np.asarray(y) / KY
    lon = LON0 + np.asarray(x) / KX
    r = (top - lat) * 3600.0 - r0
    c = (lon - west) * 3600.0 - c0
    return ndimage.map_coordinates(G, [r, c], order=3, mode='nearest')


n = 2 * HALF // STEP + 1
g = -HALF + np.arange(n) * STEP
X, Y = np.meshgrid(g, g)                          # rows south -> north
H = elev(X, Y)
rows = [[round(float(v), 2) for v in r] for r in H]
json.dump({'origin': [LAT0, LON0], 'half': HALF, 'step': STEP, 'n': n, 'source': 'Copernicus GLO-30, grey opening',
           'rows_south_to_north': rows}, open(os.path.join(OUT, NAME), 'w'))
print('grid', n, 'min %.1f max %.1f' % (H.min(), H.max()))
