"""캠퍼스 사람 하나를 메타모아 야영지 캐릭터 GLB 로 묶는다.

    .venv/bin/python tools/metamoa_character.py p11 <나갈 파일.glb>

게임은 사람(people/pNN.glb)을 그릴 때 얼굴 아틀라스(faces.png)를 곱하고, 안경을
쓰지 않은 사람의 안경을 빼고, 몸짓은 rig-*.glb 에서 뼈 이름으로 가져온다
(web/src/characters.js). 메타모아는 표준 glTF 하나만 받으니 그 일을 미리 한다.

- 얼굴: 그 사람의 칸과 빈 칸만 잘라 피부색을 곱해 굽는다. 흰자는 게임의
  EYE_WHITE. 피부 재질은 그 텍스처 하나를 쓴다.
- 안경: 쓰지 않은 사람은 안경 조각을 뺀다.
- 몸짓: rig 의 `idle` 하나만 뼈 이름으로 옮긴다.
- 게임 전용 속성(`_OCC` · `_LEG`)과 노드 extras 는 뺀다.

인쇄가 있는 옷(게스 · 연세 글자: 텍스처 좌표가 피부 밖에도 있음)은 메타모아가
제3자 로고로 거절하므로 만들지 않는다.

메타모아 한도: 4 MB, 삼각형 20,000, 관절 64, 텍스처 넷, 애니메이션 하나.
"""
import io, json, struct, sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PEOPLE = ROOT / 'web/public/assets/models/people'
GRID = 5                                  # (blender/faces.py GRID)
BLANK = (GRID - 1, GRID - 1)              # 빈 칸: 마지막 칸 (faces.py BLANK)
EYE_WHITE = np.array([0.84, 0.83, 0.80])  # 흰자, 선형 (characters.js EYE_WHITE)
LIMITS = dict(bytes=4 * 1024 * 1024, tris=20000, joints=64)

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16,
        5125: np.uint32, 5126: np.float32}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def read_glb(path):
    b = path.read_bytes()
    jlen = struct.unpack_from('<I', b, 12)[0]
    g = json.loads(b[20:20 + jlen])
    off = 20 + jlen
    blen = struct.unpack_from('<I', b, off)[0]
    return g, b[off + 8:off + 8 + blen]


def accessor(g, binary, i):
    a = g['accessors'][i]
    v = g['bufferViews'][a['bufferView']]
    dt, n = np.dtype(COMP[a['componentType']]), NCOMP[a['type']]
    start = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = v.get('byteStride', dt.itemsize * n)
    raw = np.frombuffer(binary, np.uint8, count=stride * (a['count'] - 1) + dt.itemsize * n, offset=start)
    rows = np.lib.stride_tricks.as_strided(raw, (a['count'], dt.itemsize * n), (stride, 1))
    arr = np.ascontiguousarray(rows).view(dt).reshape(a['count'], n)
    if a.get('normalized'):
        arr = arr.astype(np.float32) / np.iinfo(dt).max
    return arr


class Writer:
    """accessor · bufferView 를 새로 쌓는다(빽빽하게, 4바이트 맞춤)."""

    def __init__(self):
        self.blob, self.views, self.accessors = bytearray(), [], []

    def view(self, data, target=None):
        while len(self.blob) % 4:
            self.blob.append(0)
        v = {'buffer': 0, 'byteOffset': len(self.blob), 'byteLength': len(data)}
        if target:
            v['target'] = target
        self.blob += data
        self.views.append(v)
        return len(self.views) - 1

    def add(self, arr, kind, target=None, minmax=False):
        arr = np.ascontiguousarray(arr)
        ctype = {v: k for k, v in COMP.items()}[arr.dtype.type]
        a = {'bufferView': self.view(arr.tobytes(), target), 'componentType': ctype,
             'count': len(arr), 'type': kind}
        if minmax:
            a['min'] = arr.min(axis=0).tolist()
            a['max'] = arr.max(axis=0).tolist()
        self.accessors.append(a)
        return len(self.accessors) - 1


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def face_texture(skin, cell):
    """그 사람 칸(위)과 빈 칸(아래)을 피부색으로 구운 PNG. 게임 셰이더와 같은 식:
    mix(EYE_WHITE, skin * drawn.rgb, drawn.a)."""
    atlas = np.asarray(Image.open(PEOPLE / 'faces.png').convert('RGBA'), np.float64) / 255
    s = atlas.shape[0] // GRID
    crop = lambda c: atlas[c[1] * s:(c[1] + 1) * s, c[0] * s:(c[0] + 1) * s]
    px = np.concatenate([crop(cell), crop(BLANK)], axis=0)
    rgb, a = srgb_to_linear(px[..., :3]), px[..., 3:]
    out = EYE_WHITE * (1 - a) + np.asarray(skin) * rgb * a
    img = Image.fromarray(np.round(linear_to_srgb(out) * 255).astype(np.uint8), 'RGB')
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def build(pid, out):
    g, binary = read_glb(PEOPLE / f'{pid}.glb')
    look = next((n['extras'] for n in g['nodes'] if 'rig' in n.get('extras', {})), {})
    rig_g, rig_bin = read_glb(PEOPLE / f"{look.get('rig', 'rig-umc')}.glb")
    mats = g['materials']
    w = Writer()

    # 조각: 안경을 쓰지 않으면 안경을 빼고, 게임 전용 속성을 뺀다
    mesh = g['meshes'][0]
    prims, skin_cell = [], None
    for p in mesh['primitives']:
        name = mats[p['material']]['name']
        if name == 'Glasses' and not look.get('glasses'):
            continue
        attrs = {}
        for k, i in p['attributes'].items():
            if k.startswith('_'):
                continue
            arr = accessor(g, binary, i)
            if k == 'TEXCOORD_0':
                if name != 'Skin':
                    sys.exit(f'{pid}: {name} 에 인쇄가 있어 만들지 않음(제3자 로고)')
                uv = arr.astype(np.float32)
                blank = (uv[:, 0] >= BLANK[0] / GRID) & (uv[:, 1] >= BLANK[1] / GRID)
                cells = {tuple(c) for c in np.floor(uv[~blank] * GRID).astype(int)}
                if len(cells) != 1:
                    sys.exit(f'{pid}: 얼굴이 칸 하나에 있지 않음 {cells}')
                skin_cell = cells.pop()
                # 칸 안의 자리로: 얼굴 칸은 위 절반, 빈 칸은 아래 절반
                c = np.where(blank[:, None], np.array(BLANK, np.float32), np.array(skin_cell, np.float32))
                uv = (uv * GRID - c) * [1, 0.5] + np.where(blank[:, None], [0, 0.5], [0, 0])
                attrs[k] = w.add(uv.astype(np.float32), 'VEC2', 34962)
            elif k == 'POSITION':
                attrs[k] = w.add(arr.astype(np.float32), 'VEC3', 34962, minmax=True)
            elif k == 'JOINTS_0':
                # 무게 0 인 자리의 관절 번호는 0 으로 (glTF Validator 경고)
                wt = accessor(g, binary, p['attributes']['WEIGHTS_0'])
                attrs[k] = w.add(np.where(wt > 0, arr, 0).astype(np.uint16), 'VEC4', 34962)
            elif k == 'WEIGHTS_0':
                arr = arr.astype(np.float32)
                arr /= np.maximum(arr.sum(axis=1, keepdims=True), 1e-8)
                attrs[k] = w.add(arr, 'VEC4', 34962)
            else:
                attrs[k] = w.add(arr.astype(np.float32), g['accessors'][i]['type'], 34962)
        idx = accessor(g, binary, p['indices']).ravel()
        idx = idx.astype(np.uint16 if idx.max() < 65535 else np.uint32)
        prims.append({'attributes': attrs, 'indices': w.add(idx, 'SCALAR', 34963), 'material': p['material']})
    if skin_cell is None:
        sys.exit(f'{pid}: 피부에 텍스처 좌표가 없음')

    # 재질: 쓰는 것만, 피부는 구운 얼굴 텍스처
    used = sorted({p['material'] for p in prims})
    remap = {old: new for new, old in enumerate(used)}
    materials = []
    for old in used:
        m = json.loads(json.dumps(mats[old]))
        m.pop('extras', None)
        if m['name'] == 'Skin':
            pbr = m['pbrMetallicRoughness']
            skin = pbr['baseColorFactor'][:3]
            pbr['baseColorFactor'] = [1, 1, 1, 1]
            pbr['baseColorTexture'] = {'index': 0}
        materials.append(m)
    for p in prims:
        p['material'] = remap[p['material']]
    png = face_texture(skin, skin_cell)
    image_view = w.view(png)

    # 뼈 · 노드: 그대로, extras 만 뺀다. 스킨 메시 노드는 장면 맨 위로(부모 변환이
    # 스킨 메시에 듣지 않으니 부모 밑에 두지 않는다: glTF Validator 경고)
    nodes = [{k: v for k, v in n.items() if k != 'extras'} for n in g['nodes']]
    roots = list(g['scenes'][0]['nodes'])
    for i, n in enumerate(nodes):
        if 'skin' in n:
            for parent in nodes:
                if i in parent.get('children', []):
                    parent['children'] = [c for c in parent['children'] if c != i] or None
                    if parent['children'] is None:
                        del parent['children']
            roots.append(i)
    skins = []
    for s in g['skins']:
        s = dict(s)
        s['inverseBindMatrices'] = w.add(accessor(g, binary, s['inverseBindMatrices']).astype(np.float32), 'MAT4')
        skins.append(s)
    if len(skins[0]['joints']) > LIMITS['joints']:
        sys.exit(f"관절 {len(skins[0]['joints'])} 개: {LIMITS['joints']} 넘음")

    # 몸짓: rig 의 idle 을 뼈 이름으로
    by_name = {n.get('name'): i for i, n in enumerate(nodes)}
    idle = next(a for a in rig_g['animations'] if a['name'] == 'idle')
    samplers, channels, cache = [], [], {}
    for s in idle['samplers']:
        for k in ('input', 'output'):
            if s[k] not in cache:
                ra = rig_g['accessors'][s[k]]
                cache[s[k]] = w.add(accessor(rig_g, rig_bin, s[k]).astype(np.float32), ra['type'], minmax=k == 'input')
        samplers.append({'input': cache[s['input']], 'output': cache[s['output']],
                         'interpolation': s.get('interpolation', 'LINEAR')})
    for c in idle['channels']:
        bone = rig_g['nodes'][c['target']['node']]['name']
        channels.append({'sampler': c['sampler'], 'target': {'node': by_name[bone], 'path': c['target']['path']}})

    out_g = {
        'asset': {'version': '2.0', 'generator': 'yonsei-1997 tools/metamoa_character.py'},
        'scene': 0,
        'scenes': [{'name': pid, 'nodes': roots}],
        'nodes': nodes,
        'meshes': [{'name': mesh.get('name', pid), 'primitives': prims}],
        'skins': skins,
        'materials': materials,
        'textures': [{'source': 0, 'sampler': 0}],
        'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 33071, 'wrapT': 33071}],
        'images': [{'bufferView': image_view, 'mimeType': 'image/png'}],
        'animations': [{'name': 'idle', 'samplers': samplers, 'channels': channels}],
        'accessors': w.accessors,
        'bufferViews': w.views,
        'buffers': [{'byteLength': 0}],
    }
    while len(w.blob) % 4:
        w.blob.append(0)
    out_g['buffers'][0]['byteLength'] = len(w.blob)
    js = json.dumps(out_g, ensure_ascii=False, separators=(',', ':')).encode()
    js += b' ' * (-len(js) % 4)
    glb = (struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(w.blob))
           + struct.pack('<II', len(js), 0x4E4F534A) + js
           + struct.pack('<II', len(w.blob), 0x004E4942) + bytes(w.blob))
    out.write_bytes(glb)

    tris = sum(out_g['accessors'][p['indices']]['count'] // 3 for p in prims)
    print(f'{out}: {len(glb):,} B, 삼각형 {tris:,}, 관절 {len(skins[0]["joints"])}, '
          f'텍스처 1, 애니메이션 idle ({len(channels)} 채널), 얼굴 칸 {tuple(map(int, skin_cell))}')
    if len(glb) > LIMITS['bytes'] or tris > LIMITS['tris']:
        sys.exit('메타모아 한도를 넘음')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], Path(sys.argv[2]))
