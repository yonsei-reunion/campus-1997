"""Motion capture on the people's rigs: takes (.bvh, .glb) retargeted to actions of the 62-bone Quaternius armature.

blender/characters.py build_rig() calls build(): the clips of CLIPS replace the pack's hand-keyed ones (walk, idle,
sprint, sit) and add new ones. The takes come from tools/fetch_mocap.py (assets_src/mocap/, see its header for the
licences). No add-on: the .bvh and .glb files are read here, with numpy.

How a take becomes a clip
- Everything about the rig is read from its rest armature when the clip is built (joint positions, the bones' axes),
  so other proportions need no change here. The women's bones have no real tails: lengths are joint to joint.
- Rotations go over as world rotations. A source joint that has turned D from its reference pose (the rest pose of
  a .bvh or .glb, frame 0 of the CMU files: a T pose, as the rig's rest) turns the rig's bone D from its rest.
  ACCAD's men have no T pose in the file: a frame where the actor stands at ease is taken for the standing pose of
  another take (pose_reference).
  Arms and hands also take up the difference in direction between the two T poses (so the rig's bone points where
  the source's does, A pose or not). The spine's turn from pelvis to chest is shared out over Abdomen, Torso, Chest
  whatever the source's spine has; the collar bones do a part of theirs.
- Legs: the hips' height and the ankles' positions are scaled by the leg lengths. Foot.L/R (bones under the root,
  not under the leg) are keyed from the source's ankles, the pole targets PT.L/R in front of the knees, and
  UpperLeg/LowerLeg are solved (two bones) to end on the Foot bones. While a foot is down (low and slow in the
  take) it is flat, at the ground's height and still: in a walk cycle it moves back at the one speed of the cycle.
- A walk or a run is one stride cut from a long take, turned into a cycle in place: the frame of reference moves on
  at the stride's mean speed (and turn rate, the takes walk in curves), the difference left between the two ends is
  spread over the cycle. That speed is the clip's ground speed (rig extras 'speeds').
- Standing clips: the feet stay where they are for the whole loop, the two ends are cross-faded.
- Keys are resampled (15 a second standing, 24-30 in a cycle), then thinned per bone to what linear interpolation
  needs.
"""
import json
import math
import os
import struct

import numpy as np

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.join(ROOT, 'assets_src', 'mocap')
AXES = np.array([[1., 0, 0], [0, 0, -1], [0, 1, 0]])       # y up, facing +z (bvh, glTF)  ->  z up, facing -y (Blender)
FWD = np.array([0., -1, 0])
UP = np.array([0., 0, 1])

# source joints: the rig's parts in each source's names ({Side} Left/Right, {S} L/R, {s} l/r)
MAPS = {
    '100style': dict(pelvis='Hips', chest='Chest4', neck='Neck', head='Head', collar='{Side}Collar',
                     upper='{Side}Shoulder', lower='{Side}Elbow', hand='{Side}Wrist', tip='{Side}Wrist.end',
                     thigh='{Side}Hip', shin='{Side}Knee', foot='{Side}Ankle', toe='{Side}Toe'),
    'cmu': dict(pelvis='Hips', chest='Spine1', neck='Neck1', head='Head', collar='{Side}Shoulder', upper='{Side}Arm',
                lower='{Side}ForeArm', hand='{Side}Hand', tip='{Side}HandIndex1', thigh='{Side}UpLeg',
                shin='{Side}Leg', foot='{Side}Foot', toe='{Side}ToeBase'),
    'accad': dict(pelvis='Hips', chest='Spine1', neck='Neck', head='Head', collar='{Side}Shoulder', upper='{Side}Arm',
                  lower='{Side}ForeArm', hand='{Side}Hand', tip='{Side}Hand.end', thigh='{Side}UpLeg',
                  shin='{Side}Leg', foot='{Side}Foot', toe='{Side}ToeBase'),
    'ual1': dict(pelvis='DEF-hips', chest='DEF-spine.003', neck='DEF-neck', head='DEF-head',
                 collar='DEF-shoulder.{S}', upper='DEF-upper_arm.{S}', lower='DEF-forearm.{S}', hand='DEF-hand.{S}',
                 tip='DEF-f_middle.01.{S}', thigh='DEF-thigh.{S}', shin='DEF-shin.{S}', foot='DEF-foot.{S}',
                 toe='DEF-toe.{S}'),
    'ual2': dict(pelvis='pelvis', chest='spine_03', neck='neck_01', head='Head', collar='clavicle_{s}',
                 upper='upperarm_{s}', lower='lowerarm_{s}', hand='hand_{s}', tip='middle_01_{s}', thigh='thigh_{s}',
                 shin='calf_{s}', foot='foot_{s}', toe='ball_{s}'),
}
FILES = {'100style': '100style/{}.bvh', 'cmu': 'cmu/{}.bvh', 'accad': 'accad/{}.bvh',
         'ual1': 'quaternius/ual1.glb', 'ual2': 'quaternius/ual2.glb'}
REF = {'cmu': 0}                    # the reference pose: a frame of the take (default: the file's rest pose)
# degrees a part pitches forward in the source when its actor stands at ease, over the reference pose (100STYLE's
# skeleton holds neck and head 20 degrees forward of its T pose all the time): taken off, so the rig looks ahead
POSTURE = {'100style': {'neck': 23.0, 'head': 20.0}}
SIDES = {'L': dict(Side='Left', S='L', s='l'), 'R': dict(Side='Right', S='R', s='r')}
ANKLE = 0.15                        # the ankle joint: this far up from the Foot bone (the sole) to the knee
# corners of the shoe's sole: (along the foot, across it) from the Foot bone's head, in knee-to-sole lengths
SOLE = ((-0.07, -0.06), (-0.07, 0.06), (0.43, -0.07), (0.43, 0.07))
SPINE = (('Abdomen', 0.3), ('Torso', 0.7), ('Chest', 1.0))     # share of the pelvis -> chest turn reached at each
COLLAR = 0.6                        # share of the source's collar bone turn


# ---------- rotations (numpy; matrices (..., 3, 3), quaternions (..., 4) as w x y z) ----------

def _unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def q_from_m(M):
    M = np.asarray(M, dtype=float)
    m = lambda i, j: M[..., i, j]
    tr = m(0, 0) + m(1, 1) + m(2, 2)
    cand = np.stack([
        np.stack([1 + tr, m(2, 1) - m(1, 2), m(0, 2) - m(2, 0), m(1, 0) - m(0, 1)], -1),
        np.stack([m(2, 1) - m(1, 2), 1 + m(0, 0) - m(1, 1) - m(2, 2), m(0, 1) + m(1, 0), m(0, 2) + m(2, 0)], -1),
        np.stack([m(0, 2) - m(2, 0), m(0, 1) + m(1, 0), 1 - m(0, 0) + m(1, 1) - m(2, 2), m(1, 2) + m(2, 1)], -1),
        np.stack([m(1, 0) - m(0, 1), m(0, 2) + m(2, 0), m(1, 2) + m(2, 1), 1 - m(0, 0) - m(1, 1) + m(2, 2)], -1)], -2)
    best = np.argmax(np.stack([tr, m(0, 0), m(1, 1), m(2, 2)], -1), -1)
    q = np.take_along_axis(cand, best[..., None, None], -2)[..., 0, :]
    q = _unit(q)
    return np.where(q[..., :1] < 0, -q, q)


def m_from_q(q):
    w, x, y, z = (q[..., i] for i in range(4))
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
                     np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
                     np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], -2)


def q_slerp(a, b, t):
    """a to b (the short way) at t; t broadcasts over the leading axes."""
    t = np.asarray(t, dtype=float)[..., None]
    d = np.sum(a * b, -1, keepdims=True)
    b = np.where(d < 0, -b, b)
    d = np.clip(np.abs(d), 0, 1)
    th = np.arccos(d)
    s = np.sin(th)
    near = s < 1e-5
    s = np.where(near, 1, s)
    wa = np.where(near, 1 - t, np.sin((1 - t) * th) / s)
    wb = np.where(near, t, np.sin(t * th) / s)
    return _unit(wa * a + wb * b)


def m_slerp(A, B, t):
    return m_from_q(q_slerp(q_from_m(A), q_from_m(B), t))


def m_pow(M, t):
    """The rotation M done to the share t (about the same axis)."""
    q = q_from_m(M)
    one = np.zeros_like(q)
    one[..., 0] = 1
    return m_from_q(q_slerp(one, q, t))


def rot_axis(axis, a):
    """Rotation about a unit axis (..., 3) by a (radians)."""
    axis = _unit(np.asarray(axis, dtype=float))
    a = np.asarray(a, dtype=float)
    shape = np.broadcast_shapes(axis.shape[:-1], a.shape)
    axis = np.broadcast_to(axis, shape + (3,))
    a = np.broadcast_to(a, shape)
    K = np.zeros(shape + (3, 3))
    K[..., 0, 1], K[..., 0, 2] = -axis[..., 2], axis[..., 1]
    K[..., 1, 0], K[..., 1, 2] = axis[..., 2], -axis[..., 0]
    K[..., 2, 0], K[..., 2, 1] = -axis[..., 1], axis[..., 0]
    s, c = np.sin(a)[..., None, None], np.cos(a)[..., None, None]
    return np.eye(3) + s * K + (1 - c) * (K @ K)


def rot_z(a):
    return rot_axis(UP, a)


def swing(a, b):
    """The smallest rotation that turns direction a to direction b."""
    a, b = _unit(np.asarray(a, dtype=float)), _unit(np.asarray(b, dtype=float))
    axis = np.cross(a, b)
    n = np.linalg.norm(axis)
    if n < 1e-9:
        return np.eye(3)
    return rot_axis(axis / n, math.atan2(n, float(a @ b)))


def heading(D):
    """Yaw of a turn from the reference pose: where its forward (-Y) points, about +Z."""
    f = D @ FWD
    return np.arctan2(f[..., 0], -f[..., 1])


def frame_of(s, y):
    """Rotation matrices with columns s, y, s x y."""
    return np.stack([s, y, np.cross(s, y)], -1)


def smooth(x, n=1):
    for _ in range(n):
        x = np.concatenate([x[:1], (x[:-2] + 2 * x[1:-1] + x[2:]) / 4, x[-1:]])
    return x


# ---------- takes ----------

class Take:
    """World rotations R (frames, joints, 3, 3) and positions P (frames, joints, 3) of a take's joints, in Blender's
    axes and the source's units, and the same of its reference pose (ref_R, ref_P)."""

    def __init__(self, names, parent, fps, R, P, ref_R, ref_P):
        self.names, self.parent, self.fps = names, parent, fps
        self.R, self.P, self.ref_R, self.ref_P = R, P, ref_R, ref_P
        self.ix = {n: i for i, n in enumerate(names)}

    def joints(self, m):
        """{part or (part, side): joint index} of a MAPS entry."""
        out = {}
        for part, name in m.items():
            if '{' in name:
                for side, f in SIDES.items():
                    out[part, side] = self.ix[name.format(**f)]
            else:
                out[part] = self.ix[name]
        return out


def _euler(axis, a):
    c, s = np.cos(a), np.sin(a)
    R = np.zeros(a.shape + (3, 3))
    i = 'XYZ'.index(axis)
    j, k = (i + 1) % 3, (i + 2) % 3
    R[..., i, i] = 1
    R[..., j, j] = R[..., k, k] = c
    R[..., j, k], R[..., k, j] = -s, s
    return R


def load_bvh(path, ref=None):
    with open(path) as fh:
        head, motion = fh.read().split('MOTION')
    names, parent, offs, chans, stack, cur = [], [], [], [], [], None
    for line in head.split('\n'):
        w = line.split()
        if not w:
            continue
        if w[0] in ('ROOT', 'JOINT', 'End'):
            names.append(w[1] if w[0] != 'End' else names[cur] + '.end')
            parent.append(cur if cur is not None else -1)
            offs.append([0, 0, 0])
            chans.append([])
            new = len(names) - 1
        elif w[0] == 'OFFSET':
            offs[new] = [float(x) for x in w[1:4]]
        elif w[0] == 'CHANNELS':
            chans[new] = w[2:]
        elif w[0] == '{':
            stack.append(new)
            cur = new
        elif w[0] == '}':
            stack.pop()
            cur = stack[-1] if stack else None
    lines = motion.strip().split('\n', 2)
    count, dt = int(lines[0].split()[-1]), float(lines[1].split()[-1])
    data = np.array(lines[2].split(), dtype=float).reshape(count, -1)
    offs = np.array(offs, dtype=float)

    def fk(data):
        n, col, R, P = len(data), 0, [], []
        for i in range(len(names)):
            r, t = np.tile(np.eye(3), (n, 1, 1)), np.tile(offs[i], (n, 1))
            for c in chans[i]:
                if c.endswith('position'):         # (the root's: its channel is the position, not added to the offset)
                    t[:, 'XYZ'.index(c[0])] = data[:, col]
                else:
                    r = r @ _euler(c[0], np.radians(data[:, col]))
                col += 1
            if parent[i] < 0:
                R.append(r)
                P.append(t)
            else:
                R.append(R[parent[i]] @ r)
                P.append(P[parent[i]] + np.einsum('nij,nj->ni', R[parent[i]], t))
        R, P = np.stack(R, 1), np.stack(P, 1)
        return AXES @ R @ AXES.T, P @ AXES.T

    R, P = fk(data)
    if ref is None:
        ref_R, ref_P = (a[0] for a in fk(np.zeros((1, data.shape[1]))))
    else:
        ref_R, ref_P = R[ref], P[ref]
    return Take(names, parent, 1 / dt, R, P, ref_R, ref_P)


_GLB = {}


def _glb(path):
    if path not in _GLB:
        with open(path, 'rb') as fh:
            d = fh.read()
        n = struct.unpack('<I', d[12:16])[0]
        _GLB[path] = json.loads(d[20:20 + n]), d[28 + n:]
    return _GLB[path]


def load_glb(path, clip, fps=30):
    """A clip of a .glb (node animation, linear keys) sampled at fps; the reference pose is the nodes' rest."""
    j, blob = _glb(path)

    def acc(i):
        a = j['accessors'][i]
        v = j['bufferViews'][a['bufferView']]
        k = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[a['type']]
        if a['componentType'] != 5126 or v.get('byteStride', 4 * k) != 4 * k:
            raise SystemExit(f'{path}: accessor {i} is not packed floats')
        return np.frombuffer(blob, '<f4', a['count'] * k, v.get('byteOffset', 0) + a.get('byteOffset', 0)).reshape(-1, k).astype(float)

    nodes = j['nodes']
    anim = next((a for a in j['animations'] if a['name'] == clip), None)
    if anim is None:
        raise SystemExit(f'{path}: no clip {clip}')
    parent = [-1] * len(nodes)
    for i, nd in enumerate(nodes):
        for c in nd.get('children', []):
            parent[c] = i
    dur = max(j['accessors'][s['input']]['max'][0] for s in anim['samplers'])
    n = int(round(dur * fps)) + 1
    times = np.arange(n) / fps
    T = np.array([nd.get('translation', (0, 0, 0)) for nd in nodes], dtype=float)
    Q = np.array([nd.get('rotation', (0, 0, 0, 1)) for nd in nodes], dtype=float)[:, [3, 0, 1, 2]]
    S = np.array([nd.get('scale', (1, 1, 1)) for nd in nodes], dtype=float)
    t, q, s = (np.tile(a, (n, 1, 1)) for a in (T, Q, S))
    for ch in anim['channels']:
        sm = anim['samplers'][ch['sampler']]
        kt, kv = acc(sm['input'])[:, 0], acc(sm['output'])
        node, what = ch['target']['node'], ch['target']['path']
        hi = np.clip(np.searchsorted(kt, times), 1, len(kt) - 1) if len(kt) > 1 else np.zeros(n, int)
        lo = np.maximum(hi - 1, 0)
        f = np.clip((times - kt[lo]) / np.maximum(kt[hi] - kt[lo], 1e-9), 0, 1) if len(kt) > 1 else np.zeros(n)
        if what == 'rotation':
            kv = kv[:, [3, 0, 1, 2]]
            q[:, node] = q_slerp(kv[lo], kv[hi], f)
        elif what == 'translation':
            t[:, node] = kv[lo] + (kv[hi] - kv[lo]) * f[:, None]
        elif what == 'scale':
            s[:, node] = kv[lo] + (kv[hi] - kv[lo]) * f[:, None]

    def fk(t, q, s):
        order, R, P, Sc = [], {}, {}, {}
        todo = [i for i in range(len(nodes)) if parent[i] < 0]
        while todo:
            i = todo.pop()
            order.append(i)
            todo += nodes[i].get('children', [])
        for i in order:
            r = m_from_q(q[:, i])
            if parent[i] < 0:
                R[i], P[i], Sc[i] = r, t[:, i], s[:, i]
            else:
                p = parent[i]
                R[i] = R[p] @ r
                P[i] = P[p] + np.einsum('nij,nj->ni', R[p], Sc[p] * t[:, i])
                Sc[i] = Sc[p] * s[:, i]
        k = range(len(nodes))
        return AXES @ np.stack([R[i] for i in k], 1) @ AXES.T, np.stack([P[i] for i in k], 1) @ AXES.T

    R, P = fk(t, q, s)
    ref_R, ref_P = (a[0] for a in fk(T[None], Q[None], S[None]))
    names = [nd.get('name', str(i)) for i, nd in enumerate(nodes)]
    return Take(names, parent, fps, R, P, ref_R, ref_P)


_TAKES = {}


def take(source, name):
    """The take `name` of a source ('100style', 'cmu', 'accad': a .bvh file; 'ual1', 'ual2': a clip of the .glb)."""
    if (source, name) not in _TAKES:
        path = os.path.join(SRC, FILES[source].format(name))
        if not os.path.exists(path):
            raise SystemExit(f'missing motion capture take {os.path.relpath(path, ROOT)}: run  python3 tools/fetch_mocap.py  first')
        _TAKES[source, name] = load_glb(path, name) if path.endswith('.glb') else load_bvh(path, REF.get(source))
    return _TAKES[source, name]


# ---------- the rig ----------

class Rig:
    """What the retarget needs of the armature's rest pose (armature space, the rig's units)."""

    def __init__(self, arm):
        bones = arm.data.bones
        self.names = [b.name for b in bones]                      # parents first
        self.parent = {b.name: b.parent.name if b.parent else None for b in bones}
        self.rest = {b.name: np.array(b.matrix_local) for b in bones}
        self.local = {n: (np.linalg.inv(self.rest[p]) @ self.rest[n] if p else self.rest[n]) for n, p in self.parent.items()}
        need = ['Root', 'Body', 'Abdomen', 'Torso', 'Chest', 'Neck', 'Head'] + [
            f'{b}.{s}' for s in SIDES for b in ('Shoulder', 'UpperArm', 'LowerArm', 'Wrist', 'Middle2', 'UpperLeg', 'LowerLeg', 'Foot', 'PT')]
        missing = [n for n in need if n not in self.rest]
        if missing:
            raise SystemExit('mocap: the rig has no bone ' + ', '.join(missing))
        head = lambda n: self.rest[n][:3, 3].copy()
        self.head = head
        self.leg = {}
        for s in SIDES:
            H, K, F = head('UpperLeg.' + s), head('LowerLeg.' + s), head('Foot.' + s)
            A = F + ANKLE * (K - F)
            u = _unit(A - H)
            bend = (K - H) - ((K - H) @ u) * u             # the knee off the hip-ankle line: forward
            pole = _unit(bend) if np.linalg.norm(bend) > 1e-4 * np.linalg.norm(A - H) else FWD
            hinge = _unit(np.cross(u, pole))
            yaxis = _unit(self.rest['Foot.' + s][:3, 1] * [1, 1, 0])       # the foot points along its bone
            xaxis, kf = np.cross(yaxis, UP), np.linalg.norm(K - F)
            self.leg[s] = dict(H=H, K=K, F=F, A=A, L1=np.linalg.norm(K - H), L2=np.linalg.norm(A - K), hinge=hinge,
                               F1=frame_of(hinge, _unit(K - H)), F2=frame_of(hinge, _unit(A - K)),
                               sole=[F + (yaxis * a + xaxis * b) * kf - UP * F[2] for a, b in SOLE], pt=head('PT.' + s))
        self.legs = np.mean([d['L1'] + d['L2'] for d in self.leg.values()])
        self.hip = np.mean([d['H'] for d in self.leg.values()], 0)
        self.ankle = np.mean([d['A'] for d in self.leg.values()], 0)
        self.posed = {}                                           # (pose_reference)
        self.dir = {}
        for s in SIDES:
            self.dir['upper', s] = _unit(head('LowerArm.' + s) - head('UpperArm.' + s))
            self.dir['lower', s] = _unit(head('Wrist.' + s) - head('LowerArm.' + s))
            self.dir['hand', s] = _unit(head('Middle2.' + s) - head('Wrist.' + s))


# ---------- a motion: the frames of a clip, still on the source's skeleton ----------

class Motion:
    def __init__(self, tk, j, R, P, fps, down, flat, loop=False, speed=0.0):
        self.take, self.j, self.R, self.P, self.fps = tk, j, R, P, fps
        self.down, self.flat = down, flat         # down: (frames, 2) the feet on the ground; flat: ankle heights then
        self.loop, self.speed = loop, speed       # speed: source units a second (a cycle in place)

    def __len__(self):
        return len(self.R)


def source_legs(tk, j):
    return np.mean([np.linalg.norm(tk.ref_P[j['shin', s]] - tk.ref_P[j['thigh', s]]) +
                    np.linalg.norm(tk.ref_P[j['foot', s]] - tk.ref_P[j['shin', s]]) for s in SIDES])


def contacts(tk, j, f0=0, f1=None, slow=0.22, low=0.045):
    """(frames, 2) bool: the ankle of the left, right foot low and slow (leg lengths a second, leg lengths over the
    height it has when it stands); and that standing height of each."""
    L = source_legs(tk, j)
    out, flat = [], []
    for s in SIDES:
        p = tk.P[f0:f1, j['foot', s]]
        k = max(1, int(round(tk.fps / 30)))
        v = np.zeros(len(p))
        v[k:-k] = np.linalg.norm(p[2 * k:] - p[:-2 * k], axis=1) * tk.fps / (2 * k)
        v[:k], v[-k:] = v[k], v[-k - 1]
        still = v < slow * L
        h = np.median(p[still, 2]) if still.sum() > 5 else np.percentile(p[:, 2], 10)
        d = still & (p[:, 2] < h + low * L)
        # close gaps and drop blips shorter than 1/15 s
        g = max(1, int(round(tk.fps / 15)))
        d = _runs(d, g)
        out.append(d)
        flat.append(h)
    return np.stack(out, 1), np.array(flat)


def _runs(d, g):
    d = d.copy()
    for val in (False, True):                 # fill short gaps, then drop short runs
        i = 0
        while i < len(d):
            if d[i] == val:
                k = i
                while k < len(d) and d[k] == val:
                    k += 1
                if k - i < g and i > 0 and k < len(d):
                    d[i:k] = not val
                i = k
            else:
                i += 1
    return d


def sample(tk, j, times, down=None, flat=None, **kw):
    """The take at the times (seconds): positions linear, rotations slerped between its frames."""
    f = np.clip(np.asarray(times) * tk.fps, 0, len(tk.R) - 1)
    lo = np.minimum(np.floor(f).astype(int), len(tk.R) - 2)
    a = (f - lo)[:, None]
    P = tk.P[lo] + (tk.P[lo + 1] - tk.P[lo]) * a[..., None]
    R = m_slerp(tk.R[lo], tk.R[lo + 1], a)
    if down is None:
        down, flat = contacts(tk, j)
    return Motion(tk, j, R, P, 1 / (times[1] - times[0]), down[np.round(f).astype(int)], flat, **kw)


def hip_mid(mo):
    return (mo.P[:, mo.j['thigh', 'L']] + mo.P[:, mo.j['thigh', 'R']]) / 2


def facing(P, j):
    """Yaw of the pelvis from where the hip joints are: radians, 0 facing -Y."""
    f = np.cross(P[..., j['thigh', 'L'], :] - P[..., j['thigh', 'R'], :], UP)
    return np.arctan2(f[..., 0], -f[..., 1])


def turn(mo, rz, origin):
    """Every frame into its own frame of reference: P <- rz (P - origin), R <- rz R."""
    mo.P = np.einsum('nij,nkj->nki', rz, mo.P - origin[:, None])
    mo.R = rz[:, None] @ mo.R


def cycle(tk, j, f0, f1, fps, down=None, flat=None, run=False):
    """Frames f0..f1 of the take (one stride: both ends at the same point of the gait) as a cycle in place of
    n = round(T fps) frames. The frame of reference moves along an arc at the stride's mean speed and turn rate."""
    T = (f1 - f0) / tk.fps
    n = int(round(T * fps))
    if down is None and run:                                # (a running foot is never slow for long)
        down, flat = contacts(tk, j, slow=0.9, low=0.10)
    mo = sample(tk, j, f0 / tk.fps + np.arange(n + 1) * T / n, down, flat, loop=True)
    mo.fps = n / T
    hip, yaw = hip_mid(mo)[:, :2], np.unwrap(facing(mo.P, j))
    w = (yaw[-1] - yaw[0]) / T                              # turn rate
    chord = hip[-1] - hip[0]
    half = w * T / 2
    v = np.linalg.norm(chord) / T / (np.sin(half) / half if abs(half) > 1e-6 else 1)
    th0 = math.atan2(chord[0], -chord[1]) - half            # heading of travel at the start (0: -Y)
    tau = np.arange(n + 1) * T / n
    th = th0 + w * tau
    step = v * (T / n) * np.stack([np.sin(th), -np.cos(th)], 1)
    mid = v * (T / n) * np.stack([np.sin(th + w * T / n / 2), -np.cos(th + w * T / n / 2)], 1)   # (midpoint rule)
    c = hip[0] + np.concatenate([[[0, 0]], np.cumsum(mid[:-1], 0)])
    c += (hip[-1] - c[-1]) * (tau / T)[:, None]             # (what the arc misses of the chord: a millimetre)
    turn(mo, rot_z(-th), np.concatenate([c, np.zeros((n + 1, 1))], 1))
    # spread what is left between the two ends over the cycle, so that frame n is frame 0
    u = (tau / T - 0.5)
    mo.P = mo.P + (-u)[:, None, None] * (mo.P[-1] - mo.P[0])
    E = mo.R[0] @ np.swapaxes(mo.R[-1], -1, -2)             # end -> start
    mo.R = m_pow(np.broadcast_to(E, mo.R.shape), np.broadcast_to(u[:, None], mo.R.shape[:2])) @ mo.R
    mo.R, mo.P, mo.down = mo.R[:-1], mo.P[:-1], mo.down[:-1]
    mo.P[:, :, :2] -= hip_mid(mo)[:, :2].mean(0)            # the hips over the origin, on average
    mo.speed = v
    mo.turn = math.degrees(w * T)
    return mo


def standing(tk, j, f0, f1, fps, fade=0.5, down=None, flat=None, loop=True):
    """Frames f0..f1 as a clip on the spot: facing -Y on average, the ankles' midpoint at the origin. A loop's first
    `fade` seconds blend from what follows f1 into what follows f0 (the take must go on that long after f1; 0 for
    a take that is a loop already, f1 its repeat of f0)."""
    n = int(round((f1 - f0) / tk.fps * fps))
    b = int(round(fade * fps)) if loop else 0
    mo = sample(tk, j, f0 / tk.fps + np.arange(n + b + (0 if loop else 1)) / fps, down, flat, loop=loop)
    if loop and b:
        w = np.arange(b) / b
        w = (w * w * (3 - 2 * w))
        mo.P[:b] = mo.P[n:] + (mo.P[:b] - mo.P[n:]) * w[:, None, None]
        mo.R[:b] = m_slerp(mo.R[n:], mo.R[:b], np.broadcast_to(w[:, None], mo.R[:b].shape[:2]))
        mo.down[:b] |= mo.down[n:]
    if loop:
        mo.R, mo.P, mo.down = mo.R[:n], mo.P[:n], mo.down[:n]
    yaw = np.unwrap(facing(mo.P, j))
    feet = (mo.P[:, j['foot', 'L']] + mo.P[:, j['foot', 'R']]) / 2
    c = np.append(feet[:, :2].mean(0), 0)
    turn(mo, np.broadcast_to(rot_z(-yaw.mean()), (len(mo), 3, 3)), np.broadcast_to(c, (len(mo), 3)))
    return mo


# ---------- the retarget ----------

def _intervals(d):
    out, i = [], 0
    while i < len(d):
        if d[i]:
            k = i
            while k < len(d) and d[k]:
                k += 1
            out.append((i, k))
            i = k
        else:
            i += 1
    return out


def part_turn(rig, tk, j, R, part, posture=None):
    """How far a part of the source has turned from the rig's rest pose: (n, 3, 3) world rotations."""
    i = j[part]
    name = part if isinstance(part, str) else part[0]
    posed = rig.posed.get(id(tk))
    if posed is not None:                                    # a take without a T pose: from its standing frame
        return R[:, i] @ posed[part]
    d = R[:, i] @ tk.ref_R[i].T
    if posture and posture.get(name):
        d = d @ rot_axis(np.array([1., 0, 0]), -math.radians(posture[name]))
    if name in ARM:                                          # the rig's bone points where the source's does
        d = d @ swing(tk.ref_P[j[ARM[name], part[1]]] - tk.ref_P[i], rig.dir[part]).T
    return d


ARM = {'upper': 'lower', 'lower': 'hand', 'hand': 'tip'}     # part -> the part its bone points to
STAND = ('100style', 'Neutral_ID', 800)                      # a man standing at ease (pose_reference)


def pose_reference(rig, tk, j, frame):
    """For a take whose file has no T pose (ACCAD's men): `frame` is one where its actor stands at ease. Assume that
    is the pose of STAND, and keep per part the rotation that takes the source's joint to the rig's turn from rest."""
    if id(tk) in rig.posed:
        return
    if 'stand' not in rig.posed:
        st = take(*STAND[:2])
        js = st.joints(MAPS[STAND[0]])
        R = st.R[STAND[2]:STAND[2] + 1]
        back = rot_z(-facing(st.P[STAND[2]], js))
        rig.posed['stand'] = {p: back @ part_turn(rig, st, js, R, p, POSTURE.get(STAND[0]))[0] for p in js if p[0] != 'tip'}
    yaw = rot_z(facing(tk.P[frame], j))
    rig.posed[id(tk)] = {p: tk.R[frame, j[p]].T @ yaw @ d for p, d in rig.posed['stand'].items()}


def plant(p, D, down, leg, back, loop, ease, hold=False):
    """A foot's keys with the ground under it. p: (n, 3) the Foot bone's head, D: (n, 3, 3) its turn from rest, down:
    (n,) on the ground, back: how far a planted foot moves back (+Y) each frame (a cycle in place). While it is down
    the foot is flat, at its rest height, on a line at that speed; `ease` frames blend in and out.
    hold: down for the whole clip, in one place."""
    n = len(p)
    reps = 3 if loop else 1
    pp, DD, dd = np.tile(p, (reps, 1)), np.tile(D, (reps, 1, 1)), np.tile(down, reps)
    yaw = np.unwrap(heading(DD))
    tgt, tyaw, w = pp.copy(), yaw.copy(), np.zeros(len(pp))
    for a, b in ([(0, len(pp))] if hold else _intervals(dd)):
        k = np.arange(a, b)
        mid = k.mean()
        x, y, ya = pp[a:b, 0].mean(), (pp[a:b, 1] - back * (k - mid)).mean(), yaw[a:b].mean()
        lo, hi = max(0, a - ease), min(len(pp), b + ease)
        kk = np.arange(lo, hi)
        ww = np.clip(np.minimum(kk - (a - ease - 1), (b + ease) - kk) / (ease + 1), 0, 1)
        ww = ww * ww * (3 - 2 * ww)
        better = ww > w[lo:hi]
        line = np.stack([np.full(len(kk), x), y + back * (kk - mid), np.full(len(kk), leg['F'][2])], 1)
        tgt[lo:hi][better] = line[better]
        tyaw[lo:hi][better] = ya
        w[lo:hi][better] = ww[better]
    DD = m_slerp(DD, rot_z(tyaw), w)
    pp = pp + (tgt - pp) * w[:, None]
    low = np.zeros(len(pp))                                  # nowhere under the ground: heel and toe of the sole
    for pt in leg['sole']:
        low = np.minimum(low, pp[:, 2] + np.einsum('nij,j->ni', DD, pt - leg['F'])[:, 2])
    pp[:, 2] -= low
    sl = slice(n, 2 * n) if loop else slice(0, n)
    return pp[sl], DD[sl], w[sl]


def _calm(R, seconds, fps, loop):
    """Rotations (n, 3, 3) eased over time: each the mean of those `seconds` about it (a loop's wrap round)."""
    k = int(round(seconds * fps / 2))
    if k < 1:
        return R
    q = q_from_m(R)
    for i in range(1, len(q)):
        if q[i] @ q[i - 1] < 0:
            q[i] = -q[i]
    for _ in range(2):
        pad = np.concatenate([q[-k:], q, q[:k]]) if loop else np.concatenate([q[:1]] * k + [q] + [q[-1:]] * k)
        if loop and pad[0] @ pad[k] < 0:                     # (the wrapped ends on the same side of the sphere)
            pad[:k] = -pad[:k]
        if loop and pad[-1] @ pad[-k - 1] < 0:
            pad[-k:] = -pad[-k:]
        q = _unit(np.stack([pad[i:i + len(q)] for i in range(2 * k + 1)]).mean(0))
    return m_from_q(q)


def solve(rig, mo, pose=None, arm_out=0.0, hold_feet=False, ease=2, stance=1.0, posture=None, tall=True, seat=None,
          twist=0.0, elbow=0.0, stride=1.0, sway=1.0, s=1.0, look=1.0, turn=1.0, calm=0.0, level=0.0, upright=0.0,
          lap=None, knees=1.0, arm_down=0.0):
    """The motion on the rig: {bone: (n, 4, 4) armature-space matrices} for the bones that get keys, and a report.
    arm_out: degrees the hanging arms are held further from the body; twist: degrees the forearms and hands are
    turned out (thumbs forward); hold_feet: the feet stay in one place; stance: the feet's distance from the middle
    line, scaled; posture: {part: degrees} of forward pitch taken off (see POSTURE); tall: stand the legs straight
    if the source's skeleton stands with bent knees; seat: (hip height, ground under the feet) of a seated clip,
    metres at the game's scale (see SIT); pose: see pose_reference(); stride: a cycle's steps (and its speed)
    scaled; sway: the chest's turn against the pelvis scaled (a man's walk on the women's rig); elbow: degrees the
    elbows bend more (hands resting on the lap, off thicker thighs); look: the neck's and the head's turn against the
    chest scaled, calm: and eased over this many seconds (an actor asked to look about turns the head to the
    shoulder and whips it back: in a crowd of people doing it every little while that reads as a tic); turn: the
    hips' turn about where they face on average scaled (the chest, the arms and the head go with them); level: the
    share taken off the turn the collar bones are held at on average against the chest (an actor whose shoulders hang
    lower than the skeleton's T pose has them: on the rig the shoulder joints then sit centimetres under where the
    body was modelled, a slump); upright: degrees the chest is stood back up from a forward lean, the arms, the
    neck and the head with it (the Universal Animation Library's standing loops lean 16 degrees forward on this rig,
    one foot 30 cm before the other: `stride` brings a stand's feet together fore and aft as it shortens a cycle's
    steps); lap: the hands of a seated clip laid on the thighs (see LAP: the take's arms hold them where its own
    actor's thighs were; its `sides`: 'L', 'R' or both); knees: a seated clip's knees (and feet) this much of their
    distance from the middle line; arm_down: degrees the arms are let down about the shoulders (a seated actor talking
    with both hands held out at the chest's height)."""
    tk, j, n = mo.take, mo.j, len(mo)
    k = rig.legs / source_legs(tk, j)
    if pose is not None:
        pose_reference(rig, tk, j, pose)
    D = lambda part: part_turn(rig, tk, j, mo.R, part, posture)
    ground = mo.flat.mean()
    out, info = {}, {'scale': k}

    # pelvis
    Dp0 = Dp = D('pelvis')
    if turn != 1.0:
        yaw = np.unwrap(heading(Dp0))
        Dp = rot_z(-(1 - turn) * (yaw - yaw.mean())) @ Dp0
    hip = hip_mid(mo) * k
    hip[:, 2] = rig.ankle[2] + (hip_mid(mo)[:, 2] - ground) * k
    # (a cycle is centred on the hips, a stand on the feet, a seated clip on the hips)
    origin = (rig.hip if mo.speed else rig.hip - np.append(hip[:, :2].mean(0), 0) if seat else rig.ankle)[:2]
    hip[:, :2] += origin
    mo.speed *= stride

    # feet
    feet = {}
    for i, sd in enumerate(SIDES):
        lg = rig.leg[sd]
        Df = D(('foot', sd))
        still = mo.down[:, i]
        if still.any():                                     # level the foot as it stands in the take
            Df = swing(_unit((Df[still] @ UP).mean(0)), UP) @ Df
        A = mo.P[:, j['foot', sd]] * k
        A[:, 2] = lg['A'][2] + (mo.P[:, j['foot', sd], 2] - mo.flat[i]) * k
        A[:, :2] += origin
        mid = 0.0 if mo.speed else hip[:, 0].mean()
        A[:, 0] = mid + (A[:, 0] - mid) * stance * (knees if seat else 1.0)
        A[:, 1] = rig.hip[1] + (A[:, 1] - rig.hip[1]) * stride
        feet[sd] = [A - np.einsum('nij,j->ni', Df, lg['A'] - lg['F']), Df]
    if seat:                                                # seated: the hips at the seat's height, the feet on its ground
        dz = seat[0] / s - hip[:, 2].mean()
        hip[:, 2] += dz
        for sd in SIDES:
            p, Df = feet[sd]
            p[:, 2] += seat[1] / s + rig.leg[sd]['F'][2] - p[:, 2].min()
    for i, sd in enumerate(SIDES):
        p, Df = feet[sd]
        if seat:
            feet[sd] = (p, Df)
            continue
        p, Df, _ = plant(p, Df, mo.down[:, i], rig.leg[sd], mo.speed * k / mo.fps, mo.loop, ease, hold_feet)
        feet[sd] = (p, Df)

    def ankles(sd):
        p, Df = feet[sd]
        A = p + np.einsum('nij,j->ni', Df, rig.leg[sd]['A'] - rig.leg[sd]['F'])
        return A, hip + np.einsum('nij,j->ni', Dp, rig.leg[sd]['H'] - rig.hip)

    # a source skeleton that stands on bent knees (its legs too long for its actor): the hips up, legs near straight
    if tall and not seat:
        ext = np.concatenate([np.linalg.norm(A - H, axis=1) / (rig.leg[sd]['L1'] + rig.leg[sd]['L2'])
                              for sd in SIDES for A, H in [ankles(sd)]])
        top = np.percentile(ext, 90)
        if top < 0.985:
            rise = (0.985 / top - 1) * (hip[:, 2] - rig.ankle[2]).mean()
            hip[:, 2] += rise
            info['rise'] = float(rise)
    # the hips never further from an ankle than the leg is long
    drop = np.zeros(n)
    for sd in SIDES:
        A, H = ankles(sd)
        reach = 0.997 * (rig.leg[sd]['L1'] + rig.leg[sd]['L2'])
        d = A - H
        drop = np.maximum(drop, -d[:, 2] - np.sqrt(np.maximum(reach ** 2 - d[:, 0] ** 2 - d[:, 1] ** 2, 0)))
    if drop.max() > 0:
        e = drop.copy()
        for _ in range(2):
            pad = np.concatenate([e[-3:], e, e[:3]]) if mo.loop else np.concatenate([e[:1]] * 3 + [e] + [e[-1:]] * 3)
            e = np.maximum(e, smooth(pad, 2)[3:-3])
        hip[:, 2] -= e
    info['hip_drop'] = float(drop.max())

    body = np.tile(np.eye(4), (n, 1, 1))
    body[:, :3, :3] = Dp @ rig.rest['Body'][:3, :3]
    body[:, :3, 3] = hip - np.einsum('nij,j->ni', Dp, rig.hip - rig.head('Body'))
    out['Body'] = body

    # spine: the turn from pelvis to chest, shared out; neck and head as in the take
    turns = {}
    Dc0 = Dc = D('chest')
    rel = np.swapaxes(Dp0, -1, -2) @ Dc
    if sway != 1.0 or turn != 1.0:
        rel = m_pow(rel, np.full(n, sway))
        Dc = Dp @ rel
    if upright:                                             # (the chest back up, about the hips' own side to side)
        Dc = rot_axis(np.einsum('nij,j->ni', Dp, np.array([1., 0, 0])), -np.radians(upright)) @ Dc
        rel = np.swapaxes(Dp, -1, -2) @ Dc
    # (with the hips turned less or the chest stood up, what hangs on the chest goes with the chest: K takes it from
    # where the take has it)
    K = Dc @ np.swapaxes(Dc0, -1, -2) if turn != 1.0 or upright else None
    with_chest = (lambda M: K @ M) if K is not None else (lambda M: M)
    for bone, share in SPINE:
        turns[bone] = Dp @ m_pow(rel, np.full(n, share))
    for bone, part in (('Neck', 'neck'), ('Head', 'head')):
        Dh = with_chest(D(part))
        if look != 1.0 or calm:
            r = np.swapaxes(Dc, -1, -2) @ Dh
            if calm:
                r = _calm(r, calm, mo.fps, mo.loop)
            Dh = Dc @ m_pow(r, np.full(n, look))
        turns[bone] = Dh
    fwd = np.einsum('nij,j->ni', Dc, FWD)
    for sd, sign in (('L', 1), ('R', -1)):
        collar = np.swapaxes(Dc, -1, -2) @ with_chest(D(('collar', sd)))
        if level:                                           # (the turn the take holds them at all the while, taken off)
            q = q_from_m(collar)
            q = np.where((q @ q[0])[:, None] < 0, -q, q)
            collar = m_pow(m_from_q(_unit(q.mean(0))).T, level) @ collar
        turns['Shoulder.' + sd] = Dc @ m_pow(collar, np.full(n, COLLAR))
        extra = None
        for part, bone in (('upper', 'UpperArm.'), ('lower', 'LowerArm.'), ('hand', 'Wrist.')):
            Db = with_chest(D((part, sd)))
            if arm_out and part == 'upper':                 # hanging arms a little away from the body
                hang = np.clip(-(Db @ rig.dir[part, sd])[:, 2], 0, 1)
                extra = rot_axis(fwd, sign * np.radians(arm_out) * hang)
            if extra is not None:
                Db = extra @ Db
            if arm_down:
                Db = rot_axis(np.einsum('nij,j->ni', Dc, np.array([1., 0, 0])), np.radians(arm_down)) @ Db
            if elbow and part != 'upper':
                Db = rot_axis(np.einsum('nij,j->ni', Dc, np.array([1., 0, 0])), -np.radians(elbow)) @ Db
            if twist and part != 'upper':                   # about the forearm, as it lies
                Db = rot_axis(np.einsum('nij,j->ni', turns['LowerArm.' + sd] if part == 'hand' else Db, rig.dir['lower', sd]),
                              -sign * np.radians(twist) * (1.0 if part == 'hand' else 0.5)) @ Db
            turns[bone + sd] = Db

    # legs: two bones from the hip joint to the ankle the Foot bone holds
    thighs = {}
    for sd in SIDES:
        lg = rig.leg[sd]
        p, Df = feet[sd]
        A, H = ankles(sd)
        v = A - H
        d = np.linalg.norm(v, axis=1)
        u = v / d[:, None]
        d = np.clip(d, abs(lg['L1'] - lg['L2']) * 1.01, (lg['L1'] + lg['L2']) * 0.9995)
        a = (lg['L1'] ** 2 - lg['L2'] ** 2 + d ** 2) / (2 * d)
        h = np.sqrt(np.maximum(lg['L1'] ** 2 - a ** 2, 0))
        # the knee's side of the hip-ankle line as in the take; a straight leg bends where foot and pelvis face
        Hs, Ks, As = (mo.P[:, j[part, sd]] for part in ('thigh', 'shin', 'foot'))
        us = _unit(As - Hs)
        ps = (Ks - Hs) - np.sum((Ks - Hs) * us, 1, keepdims=True) * us
        pole = ps / source_legs(tk, j) + 0.03 * (np.einsum('nij,j->ni', Df, FWD) + np.einsum('nij,j->ni', Dp, FWD))
        pole = _unit(pole - np.sum(pole * u, 1, keepdims=True) * u)
        K = H + a[:, None] * u + h[:, None] * pole
        if seat and knees != 1.0:                           # the knee as near the middle line as its circle comes
            want = K.copy()
            want[:, 0] = hip[:, 0] + (K[:, 0] - hip[:, 0]) * knees
            pole = want - (H + a[:, None] * u)
            pole = _unit(pole - np.sum(pole * u, 1, keepdims=True) * u)
            K = H + a[:, None] * u + h[:, None] * pole
        thighs[sd] = (H, K)
        hinge = _unit(np.cross(u, pole))
        turns['UpperLeg.' + sd] = frame_of(hinge, _unit(K - H)) @ lg['F1'].T
        turns['LowerLeg.' + sd] = frame_of(hinge, _unit(A - K)) @ lg['F2'].T
        foot = np.tile(np.eye(4), (n, 1, 1))
        foot[:, :3, :3] = Df @ rig.rest['Foot.' + sd][:3, :3]
        foot[:, :3, 3] = p
        out['Foot.' + sd] = foot
        pt = np.tile(rig.rest['PT.' + sd], (n, 1, 1))
        pt[:, :3, 3] = K + pole * np.linalg.norm(lg['pt'] - lg['K'])
        out['PT.' + sd] = pt
        info['knee_' + sd] = float(np.degrees(np.arccos(np.clip(np.sum(_unit(K - H) * _unit(A - K), 1), -1, 1))).max())

    # forward kinematics: every keyed bone's armature-space matrix
    def place(name):
        M, q = rig.local[name], rig.parent[name]
        while q is not None and q not in out:               # an unkeyed parent keeps its rest pose on its parent
            M, q = rig.local[q] @ M, rig.parent[q]
        follow = out[q] @ M if q is not None else np.tile(M, (n, 1, 1))
        m = np.tile(np.eye(4), (n, 1, 1))
        m[:, :3, :3] = turns[name] @ rig.rest[name][:3, :3]
        m[:, :3, 3] = follow[:, :3, 3]
        out[name] = m

    for name in rig.names:
        if name not in out and name in turns:
            place(name)
    if lap is not None:
        for sd in lap.get('sides', 'LR'):
            info['lap_' + sd] = hands_on_lap(rig, sd, out, turns, thighs[sd], dict(LAP, **lap), s)
            for bone in ('UpperArm.', 'LowerArm.', 'Wrist.'):
                place(bone + sd)
    return out, info


# A seated person's hands lie on their thighs.  The take's arms hold the hands where its own actor's thighs were:
# on these bodies (other arms, thicker or thinner thighs, the knees brought together) that left them in the air
# before the knees, the elbows out and the fingers spread over the edge.  So the arms of a seated clip are solved
# anew each frame, two bones from the shoulder joint as the take's trunk carries it to a wrist on the thigh:
#   at: the wrist's place along the thigh (0 the hip joint, 1 the knee); up: the wrist joint over the thigh's axis,
#   metres at the game's scale (the thigh, its cloth and half the wrist); inn: and in toward the other thigh;
#   toe: degrees the fingers point in from along the thigh; dip: and down toward the knee, as the thigh thins;
#   roll: degrees the palm leans in (the thumb's side lower: the hand lies over the round of the thigh);
#   out: the elbow's place round the shoulder-wrist line, degrees out from straight behind it;
#   twist: the share of the palm's turn the forearm does (the wrist the rest)
LAP = dict(at=0.46, up=0.105, inn=-0.012, toe=12.0, dip=6.0, roll=6.0, out=24.0, twist=0.55)


def hands_on_lap(rig, sd, out, turns, thigh, o, s):
    """turns of UpperArm, LowerArm and Wrist of one side for a hand resting on its thigh (LAP); the elbow's
    greatest bend, degrees."""
    head = rig.head
    H, K = thigh
    sign = 1.0 if rig.leg[sd]['H'][0] > rig.hip[0] else -1.0                # (+x: this side's outward)
    S = out['UpperArm.' + sd][:, :3, 3]
    L1 = np.linalg.norm(head('LowerArm.' + sd) - head('UpperArm.' + sd))
    L2 = np.linalg.norm(head('Wrist.' + sd) - head('LowerArm.' + sd))
    t = _unit(K - H)
    up = _unit(UP - np.sum(UP * t, 1, keepdims=True) * t)
    inward = -sign * np.cross(up, t)
    inward = np.where(np.sum(inward * [sign, 0, 0], 1, keepdims=True) > 0, -inward, inward)
    W = H + t * o['at'] * np.linalg.norm(K - H, axis=1, keepdims=True) + up * o['up'] / s + inward * o['inn'] / s
    v = W - S
    d = np.linalg.norm(v, axis=1)
    u = v / d[:, None]
    d = np.clip(d, abs(L1 - L2) * 1.05, (L1 + L2) * 0.985)
    W = S + u * d[:, None]
    a = (L1 ** 2 - L2 ** 2 + d ** 2) / (2 * d)
    h = np.sqrt(np.maximum(L1 ** 2 - a ** 2, 0))
    back, outw = -FWD, np.array([sign, 0., 0])
    pole = back * math.cos(math.radians(o['out'])) + outw * math.sin(math.radians(o['out']))
    pole = _unit(pole - np.sum(pole * u, 1, keepdims=True) * u)
    E = S + a[:, None] * u + h[:, None] * pole
    hinge = _unit(np.cross(u, pole))
    # (the rest pose: a T, the elbow bending forward, so its point is behind)
    d1, d2 = rig.dir['upper', sd], rig.dir['lower', sd]
    F1 = frame_of(_unit(np.cross(d1, -FWD)), d1)
    F2 = frame_of(_unit(np.cross(d2, -FWD)), d2)
    turns['UpperArm.' + sd] = frame_of(hinge, _unit(E - S)) @ F1.T
    lower = frame_of(hinge, _unit(W - E)) @ F2.T
    # the hand: its fingers along the thigh, turned in and down, the palm on the cloth
    f = _unit(t + inward * math.tan(math.radians(o['toe'])) - up * math.tan(math.radians(o['dip'])))
    nrm = up * math.cos(math.radians(o['roll'])) + inward * math.sin(math.radians(o['roll']))
    nrm = _unit(nrm - np.sum(nrm * f, 1, keepdims=True) * f)
    f0 = rig.dir['hand', sd]
    idx, pinky = (head(b + '2.' + sd) - head('Wrist.' + sd) for b in ('Index', 'Pinky'))
    n0 = _unit(sign * np.cross(idx, pinky))                 # the back of the hand: up in the T pose
    n0 = _unit(n0 - (n0 @ f0) * f0)
    hand = frame_of(f, nrm) @ frame_of(f0, n0).T
    # the forearm does its share of the turn about its own length
    q = q_from_m(np.swapaxes(lower, -1, -2) @ hand)
    ang = 2 * np.arctan2(q[:, 1:] @ d2, q[:, 0])
    ang = (ang + np.pi) % (2 * np.pi) - np.pi
    turns['LowerArm.' + sd] = lower @ rot_axis(d2, o['twist'] * ang)
    turns['Wrist.' + sd] = hand
    return float(np.degrees(np.arccos(np.clip(np.sum(_unit(E - S) * _unit(W - E), 1), -1, 1))).max())


def basis(rig, pose):
    """{bone: (n, 4, 4) matrix_basis} of the armature-space matrices of solve()."""
    n = len(next(iter(pose.values())))
    full, out = {}, {}
    for name in rig.names:
        p = rig.parent[name]
        follow = (full[p] @ rig.local[name]) if p else np.tile(rig.local[name], (n, 1, 1))
        if name in pose:
            full[name] = pose[name]
            out[name] = np.linalg.inv(follow) @ pose[name]
        else:
            full[name] = follow
    return out


# ---------- actions ----------

# what thinning the keys may cost, degrees and metres (legs, hips and feet closer: the leg has to end on the foot)
TOL = {'rot': 0.45, 'loc': 0.001, 'foot': 0.0007, 'leg': 0.12, 'pole': 0.03}


def _thin(err, n, tol):
    """Indices of the keys to keep: split at the worst frame until linear interpolation is within tol everywhere."""
    keep = [0, n - 1]
    todo = [(0, n - 1)]
    while todo:
        a, b = todo.pop()
        if b - a < 2:
            continue
        e = err(a, b)
        i = int(np.argmax(e))
        if e[i] > tol:
            keep.append(a + 1 + i)
            todo += [(a, a + 1 + i), (a + 1 + i, b)]
    return sorted(keep)


def write_action(arm, name, mats, fps, scene_fps, loop, s=1.0, thin=True):
    """An action of the armature from {bone: (n, 4, 4) matrix_basis} at fps. A loop gets frame n = frame 0."""
    act = bpy.data.actions.new(name)
    slot = act.slots.new(id_type='OBJECT', name=arm.name)
    bag = act.layers.new('Layer').strips.new(type='KEYFRAME').channelbag(slot, ensure=True)
    keys = 0
    for bone, M in mats.items():
        if loop:
            M = np.concatenate([M, M[:1]])
        n = len(M)
        frames = np.arange(n) * scene_fps / fps
        loc = M[:, :3, 3]
        q = q_from_m(M[:, :3, :3])
        for i in range(1, n):                                       # no sign flips from key to key
            if q[i] @ q[i - 1] < 0:
                q[i] = -q[i]
        if loop:
            q[-1] = q[0]
        group = bag.groups.new(bone)
        arm.pose.bones[bone].rotation_mode = 'QUATERNION'
        leg = bone.startswith(('UpperLeg', 'LowerLeg', 'Body'))
        for prop, vals in (('location', loc), ('rotation_quaternion', q)):
            still = np.abs(vals - vals[0]).max() < 1e-6
            rest = np.abs(vals - ([0, 0, 0] if prop == 'location' else [1, 0, 0, 0])).max() < 1e-5
            if still and rest:
                continue
            if bone.startswith('PT') and prop != 'location':
                continue
            if still:
                keep = [0, n - 1]
            elif not thin:
                keep = list(range(n))
            elif prop == 'location':
                def err(a, b, v=vals):
                    t = (np.arange(a + 1, b) - a)[:, None] / (b - a)
                    return np.linalg.norm(v[a] + (v[b] - v[a]) * t - v[a + 1:b], axis=1)
                keep = _thin(err, n, TOL['pole' if bone.startswith('PT') else 'foot' if bone.startswith('Foot') else 'loc'] / s)
            else:
                def err(a, b, v=vals):
                    t = (np.arange(a + 1, b) - a) / (b - a)
                    w = q_slerp(np.broadcast_to(v[a], (b - a - 1, 4)), np.broadcast_to(v[b], (b - a - 1, 4)), t)
                    return np.degrees(2 * np.arccos(np.clip(np.abs(np.sum(w * v[a + 1:b], 1)), 0, 1)))
                keep = _thin(err, n, TOL['leg'] if leg else TOL['rot'])
            for c in range(vals.shape[1]):
                fc = bag.fcurves.new(f'pose.bones["{bone}"].{prop}', index=c)
                fc.group = group
                fc.keyframe_points.add(len(keep))
                co = np.stack([frames[keep], vals[keep, c]], 1).ravel()
                fc.keyframe_points.foreach_set('co', co)
                fc.keyframe_points.foreach_set('interpolation', [1] * len(keep))       # LINEAR
                fc.update()
                keys += len(keep)
    act.use_fake_user = True
    return act, keys


# ---------- the clips ----------

# clip -> take: (source, name); cycle: (first, last frame) one stride of a walk or run, in place;
#         stand: (first, last frame) a loop on the spot; fps: keys a second before thinning (24; between keys the
#         leg's rotations and the foot's position do not go quite together: a fast clip needs more);
#         the rest: solve() options.  The takes of somebody looking about turn the head to the shoulder (the man's
#         123 degrees one way and 105 the other with the hips and the chest, the woman's 67) at up to 220 degrees a
#         second: look / turn / sway / calm bring that down to about 30 degrees either way, eased
SIT = (0.29, -0.225)        # seated clips: the hip joints this high over the model's origin (as the 'sit' pose before:
#                             the game lifts a seated person by the hips), the ground a 0.43 m bench leaves the feet
_SIT = dict(take=('ual1', 'Sitting_Idle_Loop'), stand=(0, 50), fade=0, fps=15, seat=SIT, lap={})
# (talking: one hand stays on the lap, the other talks, let down from the chest's height to over the lap)
_SIT_TALK = dict(take=('ual1', 'Sitting_Talking_Loop'), stand=(0, 88), fade=0, fps=15, seat=SIT, lap=dict(sides='L'), arm_down=38)
# ACCAD's Female 1 holds her shoulders 2.6 cm lower on the rig than its rest pose has them (the men's takes 0.7 cm)
# and her neck 3 - 6 degrees forward: with the women's narrow shoulders that reads as a stoop.  Both taken off
_F1 = dict(level=1.0, posture={'neck': 4.0})
CLIPS = {
    'umc': {
        'walk': dict(take=('cmu', '07_01'), cycle=(71, 202)),
        'walk-slow': dict(take=('100style', 'Neutral_FW'), cycle=(1170, 1252)),
        'walk-fast': dict(take=('cmu', '08_01'), cycle=(94, 215)),
        'sprint': dict(take=('cmu', '35_17'), cycle=(35, 126), run=True, fps=30, arm_out=8),
        'idle': dict(take=('100style', 'Neutral_ID'), stand=(600, 960), fps=15, hold_feet=True),
        'idle-shift': dict(take=('accad', 'Male2_A2_Sway'), stand=(100, 1000), fps=15, hold_feet=True, pose=-5, stance=0.85),
        'idle-look': dict(take=('accad', 'Male2_A4_LookAround'), stand=(1020, 1800), fps=15, hold_feet=True, pose=-5,
                          turn=0.3, sway=0.5, look=0.26, calm=0.3),
        'idle-fold': dict(take=('100style', 'ArmsFolded_ID'), stand=(600, 900), fps=15, hold_feet=True),
        'talk': dict(take=('ual1', 'Idle_Talking_Loop'), stand=(0, 88), fade=0, fps=15, hold_feet=True, stance=0.7, upright=12, stride=0.35),
        'phone': dict(take=('100style', 'OnPhoneRight_ID'), stand=(600, 900), fps=15, hold_feet=True),
        'sit': _SIT,
        'sit-talk': _SIT_TALK,
    },
    'women': {
        'walk': dict(take=('accad', 'Female1_B03_Walk1'), cycle=(96, 134), **_F1),
        'walk-slow': dict(take=('100style', 'Neutral_FW'), cycle=(1170, 1252), stride=0.92, sway=0.7, arm_out=9),
        'walk-fast': dict(take=('cmu', '08_01'), cycle=(94, 215), stride=0.92, sway=0.7, arm_out=10),
        'sprint': dict(take=('cmu', '35_17'), cycle=(35, 126), run=True, fps=30, stride=0.92, sway=0.7, arm_out=10),
        'idle': dict(take=('accad', 'Female1_A01_Stand'), stand=(5, 70), fps=15, hold_feet=True, **_F1),
        'idle-shift': dict(take=('accad', 'Female1_A02_Sway'), stand=(15, 200), fps=15, hold_feet=True, arm_out=4, **_F1),
        'idle-look': dict(take=('accad', 'Female1_A04_Look'), stand=(10, 200), fps=15, hold_feet=True, look=0.42, calm=0.3,
                          **_F1),
        'idle-fold': dict(take=('ual2', 'Idle_FoldArms_Loop'), stand=(0, 75), fade=0, fps=15, hold_feet=True, stance=0.7,
                          upright=12, stride=0.35),
        'talk': dict(take=('accad', 'Female1_D3_ConversationGestures'), stand=(30, 240), fps=15, hold_feet=True, arm_out=5,
                     look=0.5, calm=0.4, **_F1),
        'phone': dict(take=('ual2', 'Idle_TalkingPhone_Loop'), stand=(0, 88), fade=0, fps=15, hold_feet=True, stance=0.7,
                      upright=12, stride=0.35),
        'sit': dict(_SIT, knees=0.55),
        'sit-talk': dict(_SIT_TALK, knees=0.55, arm_down=30),
    },
}


def build_clip(arm, rig, name, spec, scene_fps, s=1.0, thin=True):
    """One clip of CLIPS as an action: (action, {speed (m/s), seconds, keys, ...})."""
    spec = dict(spec)
    source, tname = spec.pop('take')
    fps = spec.pop('fps', 24)
    tk = take(source, tname)
    j = tk.joints(MAPS[source])
    if 'cycle' in spec:
        mo = cycle(tk, j, *spec.pop('cycle'), fps, run=spec.pop('run', False))
    else:
        mo = standing(tk, j, *spec.pop('stand'), fps, fade=spec.pop('fade', 0.5), loop=spec.pop('loop', True))
    spec.setdefault('posture', POSTURE.get(source))
    made, info = solve(rig, mo, s=s, **spec)
    act, keys = write_action(arm, name, basis(rig, made), mo.fps, scene_fps, mo.loop, s, thin)
    info.update(speed=mo.speed * info['scale'] * s, seconds=len(mo) / mo.fps, keys=keys, frames=len(mo), loop=mo.loop,
                turn=getattr(mo, 'turn', 0.0))
    return act, info


def build(rig_name, arm, acts, s, scene_fps, only=None):
    """The clips of CLIPS[rig_name] into acts ({clip: action}; the ones of the same name are replaced). The armature
    is at the pack's scale: s is metres to one of its units. Returns the rig's extras: walk_speed, run_speed and
    'speeds', a JSON object {clip: metres a second on the ground} of the cycles in place."""
    rig = Rig(arm)
    speeds, report = {}, {}
    for name, spec in CLIPS[rig_name].items():
        if only and name not in only:
            continue
        old = bpy.data.actions.get(name)
        if old is not None:                                 # (the pack's or characters.py's clip of that name)
            old.name = name + '~'
        act, info = build_clip(arm, rig, name, spec, scene_fps, s)
        acts[name] = act
        report[name] = info
        if info['speed']:
            speeds[name] = round(info['speed'], 3)
        print(f'mocap {rig_name} {name}: {spec["take"][0]} {spec["take"][1]}  {info["seconds"]:.2f} s  {info["frames"]} frames  '
              f'{info["keys"]} keys  speed {info["speed"]:.2f} m/s  turn {info["turn"]:.1f}  hip drop {info["hip_drop"] * s * 1000:.0f} mm  '
              f'knee {info["knee_L"]:.0f}/{info["knee_R"]:.0f}')
    meta = {'speeds': json.dumps(speeds, separators=(',', ':'))}
    if 'walk' in speeds:
        meta['walk_speed'] = speeds['walk']
    if 'sprint' in speeds:
        meta['run_speed'] = speeds['sprint']
    build.report = report
    return meta
