"""Copy/resize the CC0 Poly Haven PBR textures used by blender/materials.json into the web app."""
import json, os
from PIL import Image
from webp_textures import pbr_webp
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
M = json.load(open(os.path.join(ROOT, 'blender/materials.json')))
HI = {'old_stone_wall', 'concrete_wall_008', 'asphalt_02', 'patterned_concrete_pavers', 'leafy_grass', 'white_plaster_02'}
EXTRA = ['raked_dirt', 'forest_ground_04']           # used by the terrain splat shader
names = sorted({v['tex'] for v in M.values() if isinstance(v, dict) and 'tex' in v} | set(EXTRA))
for n in names:
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
json.dump(M, open(os.path.join(ROOT, 'web/public/data/materials.json'), 'w'), ensure_ascii=False, indent=1)
