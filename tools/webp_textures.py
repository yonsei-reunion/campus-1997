"""WebP copies of the colour atlases the game downloads (leaf_*.png, litter_*.png) and of the people's faces from
near (assets/models/people/faces/*.png: blender/characters.py -- faces writes the PNGs, this their copies; a face's
relief <id>_n.png goes lossless: lossy colour halves the resolution of two of its three channels, which are a normal's
x and y and the gloss, and leaves errors of up to a half at the lids' edges).

The PNGs stay the source (Blender reads leaf_<name>.png, the texture tools write them). Beside each one this writes
<name>.webp, lossy colour (q90) with lossless alpha, and records the PNG's sha1 in tools/webp_sources.json.
web/vite.config.js serves the .webp in place of the .png only while that sha1 still matches: a PNG rewritten without
its WebP falls back to the PNG by itself.

  python tools/webp_textures.py              every leaf_* / litter_* / face PNG whose WebP is missing or stale
  python tools/webp_textures.py --all        all of them again
  python tools/webp_textures.py a.png b.png  these files

The texture tools (make_textures.py, make_shrub_textures.py) call to_webp() after each save.
A data map (ground_*) must stay exact: lossy colour would change it. The baked sun maps (sun_shadow.png,
sun_ground.png: LOSSLESS) go as lossless WebP, the same values in 10 % fewer bytes (tools/bake_sun_shadows.mjs runs
this after a bake).

The PBR maps (assets/textures/pbr/<set>/{diff,nor,rough}[_1k].jpg) get theirs the same way, served by the same
record, but made from the Poly Haven source the JPG was made from (assets_src/textures/<set>/<map>.jpg, resized
alike: tools/prepare_web_textures.py, mobile_textures.py), at the lowest quality whose PSNR to that source is no
lower than the JPG's: as good as the JPG, about 30 % fewer bytes (2026-11-23: 2K maps -29 %, 1K copies -36 %; AVIF
at the same quality -35 % / -41 %, not worth a second format and its fallback). Made from the JPG itself a WebP
as close is no smaller. A map with no source, or one whose JPG is a byte copy of its source (no quality reaches an
infinite PSNR; the painted barks were so until 2026-11-24), keeps its JPG (recorded as jpg:<sha1>, so it is not tried
again until the JPG changes).

  python tools/webp_textures.py --pbr        the PBR maps only (missing or stale)

The clipped shrubs' surfaces (hedge_<name>.jpg and its normal map) get theirs by the same rule from the painted
image itself: tools/make_shrub_textures.py calls src_webp() as it saves each JPG.
The bronzes' maps (statues/<name>_{col,nor,orm}.jpg) likewise, from the pictures blender/sculpt.py keeps beside the
other sources as it saves the JPGs (assets_src/statues/<name>_<map>.png): run this after `blender/build.py -- statues`.
A JPG with no such source here keeps its WebP while its sha1 still matches the record, and goes out as the JPG once it
has been re-baked without this being run.
"""
import glob, hashlib, io, json, os, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, 'web/public/assets/textures')
RECORD = os.path.join(ROOT, 'tools/webp_sources.json')
PATTERNS = ('leaf_*.png', 'litter_*.png')
FACES = os.path.join(ROOT, 'web/public/assets/models/people/faces/*.png')     # (a face's colour under its alpha 0 is the eye: exact)
LOSSLESS = ('sun_shadow.png', 'sun_ground.png')
PBR = os.path.join(TEX, 'pbr/*/*.jpg')
SRC = os.path.join(ROOT, 'assets_src/textures')
STATUES = os.path.join(TEX, 'statues/*.jpg')
STATUE_SRC = os.path.join(ROOT, 'assets_src/statues')        # blender/sculpt.py _save: each map before the JPEG's loss


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
    relief = os.path.basename(os.path.dirname(png)) == 'faces' and png.endswith('_n.png')
    if os.path.basename(png) in LOSSLESS or relief:
        im.save(png[:-4] + '.webp', 'WEBP', lossless=True, quality=100, method=4, exact=True)
    else:
        # exact: keep the colour under transparent pixels (the atlases bleed their edge colour there for the mip maps)
        im.save(png[:-4] + '.webp', 'WEBP', quality=90, alpha_quality=100, method=6, exact=True)
    rec[_key(png)] = _sha1(png)
    if own:
        _save(rec)


def _psnr(a, b):
    m = ((a.astype(np.float64) - b.astype(np.float64)) ** 2).mean()
    return 99.0 if m == 0 else 10 * np.log10(255 ** 2 / m)


def src_webp(jpg, source, rec=None):
    """A JPG's WebP made from the image the JPG was saved from (a PIL image of the same size), at the lowest quality
    whose PSNR to that source is no lower than the JPG's: as good as the JPG, in fewer bytes. Returns the WebP's path,
    or None where the JPG stays (no source, or no WebP as good is smaller: then any old WebP goes, and the JPG is
    recorded as jpg:<sha1> so that it is not tried again until it changes)."""
    own = rec is None
    if own:
        rec = _load()
    key, out = _key(jpg), jpg[:-4] + '.webp'
    best = None
    if source is not None:
        mode = source.mode if source.mode in ('L', 'RGB') else 'RGB'
        S = source.convert(mode)
        ref = np.asarray(S)
        aim = _psnr(ref, np.asarray(Image.open(jpg).convert(mode)))
        qs = list(range(50, 101, 2))
        lo, hi = 0, len(qs) - 1
        while lo <= hi:                                 # (PSNR rises with the quality)
            mid = (lo + hi) // 2
            b = io.BytesIO()
            S.save(b, 'WEBP', quality=qs[mid], method=6)
            if _psnr(ref, np.asarray(Image.open(io.BytesIO(b.getvalue())).convert(mode))) >= aim:
                best, hi = b.getvalue(), mid - 1
            else:
                lo = mid + 1
    if best is None or len(best) >= os.path.getsize(jpg):
        if os.path.exists(out):
            os.remove(out)
        rec[key] = 'jpg:' + _sha1(jpg)                  # (kept: not tried again until the JPG changes)
        out = None
    else:
        with open(out, 'wb') as f:
            f.write(best)
        rec[key] = _sha1(jpg)
    if own:
        _save(rec)
    return out


def pbr_webp(jpg, rec=None):
    """A PBR map's WebP from its Poly Haven source (see above). Returns the WebP's path, or None where the JPG stays."""
    setn, name = os.path.basename(os.path.dirname(jpg)), os.path.basename(jpg)[:-4]
    src = os.path.join(SRC, setn, name.split('_')[0] + '.jpg')
    S = None
    if os.path.exists(src):
        S = Image.open(src).convert('L' if name.startswith('rough') else 'RGB')
        size = Image.open(jpg).size
        if S.size != size:
            S = S.resize(size, Image.LANCZOS)
    return src_webp(jpg, S, rec)


def statue_webp(jpg, rec=None):
    """A bronze's map's WebP from the picture blender/sculpt.py saved it from. Returns its path, or None where the JPG
    stays (no source here: `blender/build.py -- statues` writes them)."""
    src = os.path.join(STATUE_SRC, os.path.basename(jpg)[:-4] + '.png')
    return src_webp(jpg, Image.open(src).convert('RGB') if os.path.exists(src) else None, rec)


def main(args):
    rec = _load()
    if args and not args[0].startswith('--'):
        files = [os.path.abspath(a) for a in args]
    else:
        files = sorted(glob.glob(PBR))
        if '--pbr' not in args:
            files = (sorted(p for pat in PATTERNS + LOSSLESS for p in glob.glob(os.path.join(TEX, pat))) + sorted(glob.glob(FACES))
                     + sorted(glob.glob(STATUES)) + files)
        if '--all' not in args:
            stale = lambda p: rec.get(_key(p)) != 'jpg:' + _sha1(p) and (
                not os.path.exists(p[:-4] + '.webp') or rec.get(_key(p)) != _sha1(p))
            files = [p for p in files if stale(p)]
    before = after = 0
    for p in files:
        jpg = statue_webp if os.path.basename(os.path.dirname(p)) == 'statues' else pbr_webp
        out = jpg(p, rec) if p.endswith('.jpg') else (to_webp(p, rec) or p[:-4] + '.webp')
        if out:
            before += os.path.getsize(p)
            after += os.path.getsize(out)
        print('webp' if out else 'keep', _key(p))
    _save(rec)
    if before:
        print(f'{len(files)} files: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB')


if __name__ == '__main__':
    main(sys.argv[1:])
