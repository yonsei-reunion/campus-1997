# minimal GLB reader: world-space vertices per node (game frame: x east, y north, z up)
import json, struct, sys
import numpy as np
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def load(path):
    b = open(path, 'rb').read()
    l0, t0 = struct.unpack('<II', b[12:20])
    J = json.loads(b[20:20 + l0])
    o = 20 + l0
    l1, t1 = struct.unpack('<II', b[o:o + 8])
    BIN = b[o + 8:o + 8 + l1]

    def acc(i):
        a = J['accessors'][i]
        bv = J['bufferViews'][a['bufferView']]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        dt = CT[a['componentType']]
        nc = NC[a['type']]
        isz = np.dtype(dt).itemsize
        stride = bv.get('byteStride', 0)
        if stride and stride != nc * isz:
            raw = np.frombuffer(BIN, dtype=np.uint8, count=stride * a['count'], offset=off).reshape(a['count'], stride)
            return raw[:, :nc * isz].copy().view(dt).reshape(a['count'], nc)
        return np.frombuffer(BIN, dtype=dt, count=a['count'] * nc, offset=off).reshape(a['count'], nc)

    def mat(nd):
        if 'matrix' in nd:
            return np.array(nd['matrix']).reshape(4, 4).T
        T = np.eye(4)
        t = nd.get('translation', [0, 0, 0])
        x, y, z, w = nd.get('rotation', [0, 0, 0, 1])
        s = nd.get('scale', [1, 1, 1])
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        T[:3, :3] = R * np.array(s)
        T[:3, 3] = t
        return T

    out = {}

    def walk(i, M):
        nd = J['nodes'][i]
        M2 = M @ mat(nd)
        if 'mesh' in nd:
            for pr in J['meshes'][nd['mesh']]['primitives']:
                ext = pr.get('extensions', {}).get('KHR_draco_mesh_compression')
                if ext:
                    import DracoPy
                    bv = J['bufferViews'][ext['bufferView']]
                    off = bv.get('byteOffset', 0)
                    m = DracoPy.decode(BIN[off:off + bv['byteLength']])
                    P = np.asarray(m.points, dtype=np.float64).reshape(-1, 3)
                else:
                    P = acc(pr['attributes']['POSITION']).astype(np.float64)
                P = (M2[:3, :3] @ P.T).T + M2[:3, 3]
                out.setdefault(nd.get('name', str(i)), []).append(P)
        for c in nd.get('children', []):
            walk(c, M2)

    for sc in J['scenes']:
        for i in sc['nodes']:
            walk(i, np.eye(4))
    # glTF y-up -> game: game (x, y, z) = (gx, -gz, gy)
    conv = lambda P: np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1)
    return {k: conv(np.concatenate(v)) for k, v in out.items()}


if __name__ == '__main__':
    d = load(sys.argv[1])
    for k, v in sorted(d.items()):
        print(k, len(v), np.round(v.min(0), 1), np.round(v.max(0), 1))
