// The far stand-in of a campus cell made lighter off the main thread (farlod.js): meshoptimizer's simplify within an
// error in metres, across the seams between the merged materials (Permissive), dropping the little pieces that
// vanish within it (Prune: the frames, the railings, the signs), the corners' colours weighed in so that a dark band
// on a pale wall holds. Then only the corners still used are kept.
import { MeshoptSimplifier as M } from 'meshoptimizer/simplifier';

const COLOR_W = 0.6;        // metres of error a full step of linear colour (0 → 1 in a channel) counts as

self.onmessage = async (e) => {
  const { id, pos, nrm, solid, bake, idx, err } = e.data;
  try {
    await M.ready;
    const n = pos.length / 3;
    const col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) for (let k = 0; k < 3; k++) col[i * 3 + k] = solid[i * 4 + k] / 65535;
    const [out, got] = M.simplifyWithAttributes(idx, pos, 3, col, 3, [COLOR_W, COLOR_W, COLOR_W], null, 0, err,
      ['ErrorAbsolute', 'Prune', 'Permissive']);
    const [remap, m] = M.compactMesh(out);
    const P = new Float32Array(m * 3), N = new Float32Array(m * 3), S = new Uint16Array(m * 4), B = bake ? new Uint16Array(m * 4) : null;
    for (let i = 0; i < n; i++) {
      const j = remap[i];
      if (j === 0xffffffff) continue;
      P[j * 3] = pos[i * 3]; P[j * 3 + 1] = pos[i * 3 + 1]; P[j * 3 + 2] = pos[i * 3 + 2];
      N[j * 3] = nrm[i * 3]; N[j * 3 + 1] = nrm[i * 3 + 1]; N[j * 3 + 2] = nrm[i * 3 + 2];
      for (let k = 0; k < 4; k++) S[j * 4 + k] = solid[i * 4 + k];
      if (B) for (let k = 0; k < 4; k++) B[j * 4 + k] = bake[i * 4 + k];
    }
    const transfer = [P.buffer, N.buffer, S.buffer, out.buffer];
    if (B) transfer.push(B.buffer);
    self.postMessage({ id, pos: P, nrm: N, solid: S, bake: B, idx: out, err: got }, transfer);
  } catch (x) {
    self.postMessage({ id, error: String(x?.message ?? x) });
  }
};
