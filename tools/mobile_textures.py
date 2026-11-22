"""Smaller copies of the big textures for phones, so a phone downloads what it uploads.

Phones upload textures at most 1024 px (web/src/materials.js loadTex, mobileMax) and the sky at 4096 (terrain.js), but
used to download the 2K / 8K files and shrink them in the page. This writes beside each source a copy at that size
(<stem>_<n>k.jpg, LANCZOS, JPEG q90) and records the source's sha1 in tools/mobile_sources.json. web/vite.config.js
offers the copy (src/util.js phoneCopy) only while that sha1 still matches: a source rewritten without its copy goes to
phones whole, as before.

  python tools/mobile_textures.py           every copy that is missing or stale
  python tools/mobile_textures.py --all     all of them again

Only colour / normal / roughness maps: a data map (ground_*, sun_*) is also read at full size by the page.
A PBR map's copy gets its WebP too (tools/webp_textures.py pbr_webp), which the build serves in its place.
"""
import glob, hashlib, json, os, sys
from PIL import Image
from webp_textures import pbr_webp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'web/public')
RECORD = os.path.join(ROOT, 'tools/mobile_sources.json')
SETS = [('assets/textures/pbr/*/*.jpg', 1024), ('assets/hdri/sky_8k.jpg', 4096)]


def _sha1(path):
    with open(path, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def copy_name(key, size):
    return f'{key[:-4]}_{size // 1024}k.jpg'


def main(args):
    try:
        with open(RECORD) as f:
            rec = json.load(f)
    except FileNotFoundError:
        rec = {}
    made = before = after = 0
    for pat, size in SETS:
        for p in sorted(glob.glob(os.path.join(PUB, pat))):
            key = os.path.relpath(p, PUB).replace(os.sep, '/')
            stem, _, tail = key[:-4].rpartition('_')
            if tail[:-1].isdigit() and tail.endswith('k') and os.path.exists(os.path.join(PUB, stem + '.jpg')):
                continue                                    # (a copy)
            out = copy_name(key, size)
            sha = _sha1(p)
            if '--all' not in args and os.path.exists(os.path.join(PUB, out)) and rec.get(key) == [out, size, sha]:
                continue
            im = Image.open(p)
            im.load()
            if max(im.size) <= size:
                continue
            s = size / max(im.size)
            im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS).save(os.path.join(PUB, out),
                                                                                       quality=90, optimize=True)
            rec[key] = [out, size, sha]
            if '/pbr/' in key:
                pbr_webp(os.path.join(PUB, out))            # (its WebP, made from the source: webp_textures.py)
            made += 1
            before += os.path.getsize(p)
            after += os.path.getsize(os.path.join(PUB, out))
            print('copy', out)
    with open(RECORD, 'w') as f:
        json.dump(dict(sorted(rec.items())), f, indent=1)
        f.write('\n')
    if made:
        print(f'{made} files: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB')


if __name__ == '__main__':
    main(sys.argv[1:])
