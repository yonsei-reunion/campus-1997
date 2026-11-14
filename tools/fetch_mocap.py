"""Download the motion capture takes blender/mocap.py retargets onto the people's rigs -> assets_src/mocap/<source>/

usage: fetch_mocap.py            every source
       fetch_mocap.py 100style   only these (100style, accad, cmu, quaternius)
       fetch_mocap.py --list     what would be fetched

Only data that may be redistributed (the retargeted clips ship in the game's rig files):
- 100style    100STYLE dataset, Ian Mason, Sebastian Starke, Taku Komura (2022), CC BY 4.0
              https://www.ianxmason.com/100style/  https://zenodo.org/records/8127870
              (the 1.5 GB zip is read over HTTP range requests: only the listed .bvh files come down)
- accad       Open Motion Project by ACCAD / The Ohio State University, CC BY 3.0
              https://accad.osu.edu/research/motion-lab/mocap-system-and-data  (Female 1 and Male 2, BVH)
- cmu         CMU Graphics Lab Motion Capture Database, mocap.cs.cmu.edu ("free for use in research and commercial
              projects"), in B. Hahne's BVH conversion (cgspeed.com, 2010; frame 0 is a T pose), from a mirror on GitHub
- quaternius  Universal Animation Library 1 and 2, Standard (quaternius.com, CC0), the Godot .glb of each
Mixamo, Rokoko, ActorCore, Bandai Namco, LAFAN1 and the AMASS family may not be redistributed: not used.
"""
import io
import os
import struct
import sys
import urllib.request
import zipfile
import zlib

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets_src', 'mocap')
UA = {'User-Agent': 'mocap-fetch/1.0'}

STYLE_ZIP = 'https://zenodo.org/api/records/8127870/files/100STYLE.zip/content'
STYLE = ['Neutral_FW', 'Neutral_ID', 'ArmsFolded_ID', 'OnPhoneRight_ID']
STYLE_EXTRA = ['Dataset_List.csv', 'Frame_Cuts.csv']

ACCAD_URL = 'https://accad.osu.edu/sites/accad.osu.edu/files/'
ACCAD = {'Female1_bvh.zip': ['Female1_B03_Walk1', 'Female1_A01_Stand', 'Female1_A02_Sway', 'Female1_A04_Look',
                             'Female1_D3_ConversationGestures'],
         'Male2_bvh.zip': ['Male2_A2_Sway', 'Male2_A4_LookAround']}

CMU_RAW = 'https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/'
CMU = ['07_01', '08_01', '35_17']                 # walk, walk (fast), run/jog
CMU_EXTRA = ['READMEFIRST.txt']

UAL = {'ual1': ('https://opengameart.org/sites/default/files/universal_animation_librarystandard.zip',
                'Godot/AnimationLibrary_Godot_Standard.glb'),
       'ual2': ('https://opengameart.org/sites/default/files/universal_animation_library_2standard.zip',
                'Unreal-Godot/UAL2_Standard.glb')}


def have(dst):
    return os.path.exists(dst) and os.path.getsize(dst) > 0


def save(dst, data):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst + '.part', 'wb') as f:
        f.write(data)
    os.replace(dst + '.part', dst)
    print(f'ok   {os.path.relpath(dst, ROOT)}  {len(data) // 1024} KB')


def get(url, first=None, last=None):
    head = dict(UA)
    if first is not None:
        head['Range'] = f'bytes={first}-{last}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=head), timeout=300) as r:
        if first is not None and r.status != 206:
            raise RuntimeError(f'{url}: no range requests (status {r.status})')
        return r.read()


# ---------- a zip on a server, read member by member ----------

def remote_dir(url):
    """{member name: (offset of its local header, compressed size, method)} from the zip's central directory."""
    with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, 'Range': 'bytes=0-0'}), timeout=60) as r:
        total = int(r.headers['Content-Range'].split('/')[1])
    tail = get(url, max(0, total - 70000), total - 1)
    i = tail.rfind(b'PK\x05\x06')
    if i < 0:
        raise RuntimeError('no zip directory')
    count, size, off = struct.unpack('<HII', tail[i + 10:i + 20])
    if off == 0xFFFFFFFF or count == 0xFFFF:             # zip64
        k = tail.rfind(b'PK\x06\x06')
        count, size, off = struct.unpack('<QQQ', tail[k + 32:k + 56])
    cd, out, p = get(url, off, off + size - 1), {}, 0
    while cd[p:p + 4] == b'PK\x01\x02':
        method, = struct.unpack('<H', cd[p + 10:p + 12])
        csize, usize = struct.unpack('<II', cd[p + 20:p + 28])
        nl, el, cl = struct.unpack('<HHH', cd[p + 28:p + 34])
        at, = struct.unpack('<I', cd[p + 42:p + 46])
        name = cd[p + 46:p + 46 + nl].decode('utf8', 'replace')
        extra, q = cd[p + 46 + nl:p + 46 + nl + el], 0
        while q + 4 <= len(extra):                       # zip64 sizes and offset
            tag, ln = struct.unpack('<HH', extra[q:q + 4])
            if tag == 1:
                vals, r = extra[q + 4:q + 4 + ln], 0
                if usize == 0xFFFFFFFF:
                    r += 8
                if csize == 0xFFFFFFFF:
                    csize, = struct.unpack('<Q', vals[r:r + 8])
                    r += 8
                if at == 0xFFFFFFFF:
                    at, = struct.unpack('<Q', vals[r:r + 8])
            q += 4 + ln
        out[name] = (at, csize, method)
        p += 46 + nl + el + cl
    return out


def remote_member(url, entry):
    at, csize, method = entry
    head = get(url, at, at + 29)
    nl, el = struct.unpack('<HH', head[26:30])
    data = get(url, at + 30 + nl + el, at + 30 + nl + el + csize - 1) if csize else b''
    if method == 0:
        return data
    if method != 8:
        raise RuntimeError(f'zip method {method}')
    return zlib.decompress(data, -15)


# ---------- the sources ----------

def style(dry):
    d = os.path.join(ROOT, '100style')
    want = {f'100STYLE/{n.rsplit("_", 1)[0]}/{n}.bvh': n + '.bvh' for n in STYLE}
    want.update({f'100STYLE/{n}': n for n in STYLE_EXTRA})
    todo = {k: v for k, v in want.items() if not have(os.path.join(d, v))}
    if dry:
        return print('100style:', ', '.join(want.values()))
    if not todo:
        return
    listing = remote_dir(STYLE_ZIP)
    for member, name in todo.items():
        if member not in listing:
            print(f'FAIL 100style/{name}: not in the zip')
            continue
        save(os.path.join(d, name), remote_member(STYLE_ZIP, listing[member]))


def accad(dry):
    d = os.path.join(ROOT, 'accad')
    if dry:
        return print('accad:', ', '.join(n + '.bvh' for names in ACCAD.values() for n in names))
    for archive, names in ACCAD.items():
        names = [n + '.bvh' for n in names]
        if all(have(os.path.join(d, n)) for n in names):
            continue
        z = zipfile.ZipFile(io.BytesIO(get(ACCAD_URL + archive)))
        inside = {os.path.basename(i.filename): i for i in z.infolist()}
        for n in names:
            if n not in inside:
                print(f'FAIL accad/{n}: not in {archive}')
            elif not have(os.path.join(d, n)):
                save(os.path.join(d, n), z.read(inside[n]))


def cmu(dry):
    d = os.path.join(ROOT, 'cmu')
    if dry:
        return print('cmu:', ', '.join(n + '.bvh' for n in CMU))
    for n in CMU:
        dst = os.path.join(d, n + '.bvh')
        if not have(dst):
            save(dst, get(f'{CMU_RAW}data/{int(n.split("_")[0]):03d}/{n}.bvh'))
    for n in CMU_EXTRA:
        if not have(os.path.join(d, n)):
            save(os.path.join(d, n), get(CMU_RAW + n))


def quaternius(dry):
    d = os.path.join(ROOT, 'quaternius')
    if dry:
        return print('quaternius:', ', '.join(k + '.glb' for k in UAL))
    for name, (url, member) in UAL.items():
        dst = os.path.join(d, name + '.glb')
        if have(dst):
            continue
        z = zipfile.ZipFile(io.BytesIO(get(url)))
        hit = [i for i in z.infolist() if i.filename.endswith(member)]
        if not hit:
            print(f'FAIL quaternius/{name}: no {member} in the zip')
            continue
        save(dst, z.read(hit[0]))
        lic = [i for i in z.infolist() if os.path.basename(i.filename) == 'License.txt']
        if lic:
            save(os.path.join(d, name + '_License.txt'), z.read(lic[0]))


SOURCES = {'100style': style, 'accad': accad, 'cmu': cmu, 'quaternius': quaternius}

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    unknown = [a for a in args if a not in SOURCES]
    if unknown:
        raise SystemExit(f'unknown source(s): {", ".join(unknown)}  (known: {", ".join(SOURCES)})')
    failed = []
    for name in args or SOURCES:
        try:
            SOURCES[name]('--list' in sys.argv)
        except Exception as e:
            print('FAIL', name, e)
            failed.append(name)
    if failed:
        raise SystemExit('failed: ' + ', '.join(failed))
