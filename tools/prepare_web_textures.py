"""Resize the PBR texture sets used by blender/materials.json into the web app.

The source of every set is assets_src/textures/<set>/{diff,nor,rough}.jpg: the CC0 Poly Haven downloads
(tools/fetch_polyhaven.py) and the painted ones (tools/make_tile_texture.py, make_textures.py's barks). Each map goes
to web/public/assets/textures/pbr/<set>/ as JPEG (diff q84, nor / rough q80), with its WebP (tools/webp_textures.py).

  python tools/prepare_web_textures.py         every set, and the web copy of blender/materials.json
  python tools/prepare_web_textures.py a b     these sets only

The texture tools call prepare_set(<set>) after writing a set's source.
"""
import json, os, sys
from PIL import Image
from webp_textures import pbr_webp

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
HI = {'old_stone_wall', 'concrete_wall_008', 'asphalt_02', 'patterned_concrete_pavers', 'leafy_grass', 'white_plaster_02'}
EXTRA = ['raked_dirt', 'forest_ground_04']           # used by the terrain splat shader


def prepare_set(n):
    src = os.path.join(ROOT, 'assets_src/textures', n)
    dst = os.path.join(ROOT, 'web/public/assets/textures/pbr', n)
    os.makedirs(dst, exist_ok=True)
    size = 2048 if n in HI else 1024
    for m in ('diff', 'nor', 'rough'):
        p = os.path.join(src, m + '.jpg')
        if not os.path.exists(p):
            continue
        im = Image.open(p)
        im = im.convert('RGB') if m != 'rough' else im.convert('L')
        if im.width > size:
            im = im.resize((size, size), Image.LANCZOS)
        im.save(os.path.join(dst, m + '.jpg'), quality=84 if m == 'diff' else 80, optimize=True)
        pbr_webp(os.path.join(dst, m + '.jpg'))        # the copy the game downloads (tools/webp_textures.py)
    print(n, size)


def main(args):
    M = json.load(open(os.path.join(ROOT, 'blender/materials.json')))
    if args:
        for n in args:
            prepare_set(n)
        return
    for n in sorted({v['tex'] for v in M.values() if isinstance(v, dict) and 'tex' in v} | set(EXTRA)):
        prepare_set(n)
    json.dump(M, open(os.path.join(ROOT, 'web/public/data/materials.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1:])
