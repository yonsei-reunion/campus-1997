"""WebP copies of the colour atlases the game downloads (leaf_*.png, litter_*.png).

The PNGs stay the source (Blender reads leaf_<name>.png, the texture tools write them). Beside each one this writes
<name>.webp, lossy colour (q90) with lossless alpha, and records the PNG's sha1 in tools/webp_sources.json.
web/vite.config.js serves the .webp in place of the .png only while that sha1 still matches: a PNG rewritten without
its WebP falls back to the PNG by itself.

  python tools/webp_textures.py              every leaf_* / litter_* PNG whose WebP is missing or stale
  python tools/webp_textures.py --all        all of them again
  python tools/webp_textures.py a.png b.png  these files

The texture tools (make_textures.py, make_shrub_textures.py) call to_webp() after each save.
Only colour atlases go here: a data map (ground_*, sun_*) must stay exact, and lossy colour would change it.
"""
import glob, hashlib, json, os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, 'web/public/assets/textures')
RECORD = os.path.join(ROOT, 'tools/webp_sources.json')
PATTERNS = ('leaf_*.png', 'litter_*.png')


def _sha1(path):
    with open(path, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def _load():
    try:
        with open(RECORD) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save(rec):
    with open(RECORD, 'w') as f:
        json.dump(dict(sorted(rec.items())), f, indent=1)
        f.write('\n')


def _key(png):
    return os.path.relpath(png, os.path.join(ROOT, 'web/public')).replace(os.sep, '/')


def to_webp(png, rec=None):
    """Write png's WebP beside it and record its source sha1 (rec: a record being batched, saved by the caller)."""
    own = rec is None
    if own:
        rec = _load()
    im = Image.open(png)
    im.load()
    # exact: keep the colour under transparent pixels (the atlases bleed their edge colour there for the mip maps)
    im.save(png[:-4] + '.webp', 'WEBP', quality=90, alpha_quality=100, method=6, exact=True)
    rec[_key(png)] = _sha1(png)
    if own:
        _save(rec)


def main(args):
    rec = _load()
    if args and args[0] != '--all':
        pngs = [os.path.abspath(a) for a in args]
    else:
        pngs = sorted(p for pat in PATTERNS for p in glob.glob(os.path.join(TEX, pat)))
        if not args:
            pngs = [p for p in pngs if not os.path.exists(p[:-4] + '.webp') or rec.get(_key(p)) != _sha1(p)]
    before = after = 0
    for p in pngs:
        to_webp(p, rec)
        before += os.path.getsize(p)
        after += os.path.getsize(p[:-4] + '.webp')
        print('webp', os.path.basename(p))
    _save(rec)
    if pngs:
        print(f'{len(pngs)} files: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB')


if __name__ == '__main__':
    main(sys.argv[1:])
