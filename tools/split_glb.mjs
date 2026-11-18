// Splits campus_buildings.glb and campus_landmarks.glb into files of one CELL x CELL m cell each (the cell of each
// node's centre: a hall stays whole in one file), so that the game takes in first the cells round where the walk
// starts and the rest by distance (web/src/chunks.js). The Draco-compressed bytes are copied as they are: nothing is
// decoded or encoded again, a cell's file changes only when something in it does, and it takes well under a second.
//   node tools/split_glb.mjs            (blender/common.py export_glb runs it after the two files; so does vite's
//                                        config when the cells are older than them, as on GitHub Actions)
// Out: web/public/assets/models/campus/<kind>_<i>_<j>.glb, <kind>_base.glb and chunks.json (gitignored: made from the
// two GLBs, which stay as they are for the tools that read them whole; not deployed: web/vite.config.js).
// base: what the loading screen always takes, wherever the walk starts: the walked surfaces of the flights and the
// amphitheater (main.js walkables: the trees, shrubs, props and cars are set down on them), the raised ground's meshes
// (terrain_drape: the lawn's blades and the kerbs stand on them), and anything wider than BIG m (the road paint, the
// parking lines, ...), whose centre's cell says little of where it is seen.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const MODELS = path.join(here, '../web/public/assets/models');
const OUT = path.join(MODELS, 'campus');
const CELL = 160, BIG = 200;
const KINDS = { buildings: 'campus_buildings.glb', landmarks: 'campus_landmarks.glb' };
const BASE = /walk_stairs|amphitheater/;
const CAMPUS = path.join(here, '../web/public/data/campus.json');

function readGLB(file) {
  const b = fs.readFileSync(file);
  if (b.readUInt32LE(0) !== 0x46546c67) throw new Error(`${file}: not a GLB`);
  const jl = b.readUInt32LE(12);
  const json = JSON.parse(b.subarray(20, 20 + jl).toString('utf8'));
  const bo = 20 + jl;
  const bin = b.subarray(bo + 8, bo + 8 + b.readUInt32LE(bo));
  return { json, bin };
}

function writeGLB(json, bin) {
  const pad = (buf, n, fill) => (buf.length % n ? Buffer.concat([buf, Buffer.alloc(n - (buf.length % n), fill)]) : buf);
  const j = pad(Buffer.from(JSON.stringify(json), 'utf8'), 4, 0x20), d = pad(bin, 4, 0);
  const head = Buffer.alloc(12), jh = Buffer.alloc(8), dh = Buffer.alloc(8);
  head.writeUInt32LE(0x46546c67, 0); head.writeUInt32LE(2, 4); head.writeUInt32LE(12 + 8 + j.length + 8 + d.length, 8);
  jh.writeUInt32LE(j.length, 0); jh.writeUInt32LE(0x4e4f534a, 4);
  dh.writeUInt32LE(d.length, 0); dh.writeUInt32LE(0x004e4942, 4);
  return Buffer.concat([head, jh, j, dh, d]);
}

// a node's local matrix (column-major), from its matrix or its TRS
function localMatrix(n) {
  if (n.matrix) return n.matrix;
  const [tx, ty, tz] = n.translation || [0, 0, 0], [x, y, z, w] = n.rotation || [0, 0, 0, 1], [sx, sy, sz] = n.scale || [1, 1, 1];
  const xx = x * x, yy = y * y, zz = z * z, xy = x * y, xz = x * z, yz = y * z, wx = w * x, wy = w * y, wz = w * z;
  return [(1 - 2 * (yy + zz)) * sx, 2 * (xy + wz) * sx, 2 * (xz - wy) * sx, 0,
    2 * (xy - wz) * sy, (1 - 2 * (xx + zz)) * sy, 2 * (yz + wx) * sy, 0,
    2 * (xz + wy) * sz, 2 * (yz - wx) * sz, (1 - 2 * (xx + yy)) * sz, 0, tx, ty, tz, 1];
}
const mul = (a, b) => {
  const o = new Array(16);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
    o[c * 4 + r] = a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3];
  }
  return o;
};

// the world box (x, z) of a node's own mesh
function nodeBox(json, n, W) {
  const box = [Infinity, Infinity, -Infinity, -Infinity];
  for (const p of json.meshes[n.mesh].primitives) {
    const a = json.accessors[p.attributes.POSITION];
    for (const x of [a.min[0], a.max[0]]) for (const y of [a.min[1], a.max[1]]) for (const z of [a.min[2], a.max[2]]) {
      const wx = W[0] * x + W[4] * y + W[8] * z + W[12], wz = W[2] * x + W[6] * y + W[10] * z + W[14];
      box[0] = Math.min(box[0], wx); box[1] = Math.min(box[1], wz); box[2] = Math.max(box[2], wx); box[3] = Math.max(box[3], wz);
    }
  }
  return box;
}

function split(kind, file) {
  const { json, bin } = readGLB(file);
  const scene = json.scenes[json.scene ?? 0];
  // every mesh node with its world matrix and its chain of parents (kept, so names and extras read as before)
  const items = [];
  const walk = (i, M, chain) => {
    const n = json.nodes[i], W = mul(M, localMatrix(n)), ch = [...chain, i];
    if (n.mesh !== undefined) items.push({ i, chain: ch, box: nodeBox(json, n, W) });
    for (const c of n.children || []) walk(c, W, ch);
  };
  for (const r of scene.nodes) walk(r, [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], []);
  const groups = new Map();
  for (const it of items) {
    const n = json.nodes[it.i], names = it.chain.map((k) => json.nodes[k].name || '').join('/') + '/' + (json.meshes[n.mesh].name || '');
    const drape = json.meshes[n.mesh].primitives.some((p) => json.materials?.[p.material]?.name === 'terrain_drape');
    const [x0, z0, x1, z1] = it.box;
    const key = BASE.test(names) || drape || x1 - x0 > BIG || z1 - z0 > BIG ? 'base'
      : `${Math.floor((x0 + x1) / 2 / CELL)}_${Math.floor((z0 + z1) / 2 / CELL)}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(it);
  }
  const out = [];
  for (const [key, list] of groups) {
    // the nodes (the chains, each once, in the file's order) and what they use, renumbered
    const nodeSet = new Set(list.flatMap((it) => it.chain)), nodeIdx = new Map();
    [...nodeSet].sort((a, b) => a - b).forEach((k, j) => nodeIdx.set(k, j));
    const meshIdx = new Map(), accIdx = new Map(), bvIdx = new Map(), matIdx = new Map();
    const take = (map, k) => { if (!map.has(k)) map.set(k, map.size); return map.get(k); };
    const nodes = [], meshes = [], accessors = [], bufferViews = [], materials = [];
    const parts = [];
    let off = 0;
    for (const k of nodeIdx.keys()) {
      const n = { ...json.nodes[k] };
      if (n.children) { n.children = n.children.filter((c) => nodeSet.has(c)).map((c) => nodeIdx.get(c)); if (!n.children.length) delete n.children; }
      if (n.mesh !== undefined && list.some((it) => it.i === k)) {
        const had = meshIdx.has(n.mesh), mi = take(meshIdx, n.mesh);
        if (!had) {
          const m = json.meshes[n.mesh];
          meshes[mi] = { ...m, primitives: m.primitives.map((p) => {
            const q = { ...p, attributes: {} };
            for (const [a, ai] of Object.entries(p.attributes)) q.attributes[a] = take(accIdx, ai);
            if (p.indices !== undefined) q.indices = take(accIdx, p.indices);
            if (p.material !== undefined) q.material = take(matIdx, p.material);
            const dr = p.extensions?.KHR_draco_mesh_compression;
            if (dr) {
              const bi = bvIdx.has(dr.bufferView) ? bvIdx.get(dr.bufferView) : (() => {
                const v = json.bufferViews[dr.bufferView], j = take(bvIdx, dr.bufferView);
                const al = (4 - (off % 4)) % 4;
                if (al) { parts.push(Buffer.alloc(al)); off += al; }
                parts.push(bin.subarray(v.byteOffset || 0, (v.byteOffset || 0) + v.byteLength));
                bufferViews[j] = { buffer: 0, byteOffset: off, byteLength: v.byteLength };
                off += v.byteLength;
                return j;
              })();
              q.extensions = { ...p.extensions, KHR_draco_mesh_compression: { ...dr, bufferView: bi } };
            }
            return q;
          }) };
        }
        n.mesh = mi;
      } else delete n.mesh;
      nodes.push(n);
    }
    for (const [ai, j] of accIdx) {
      const a = json.accessors[ai];
      if (a.bufferView !== undefined) throw new Error(`${file}: accessor ${ai} has a bufferView (only Draco primitives are split)`);
      accessors[j] = a;
    }
    for (const [mi, j] of matIdx) materials[j] = json.materials[mi];
    const roots = scene.nodes.filter((r) => nodeSet.has(r)).map((r) => nodeIdx.get(r));
    const data = Buffer.concat(parts);
    const doc = { asset: json.asset, extensionsUsed: json.extensionsUsed, extensionsRequired: json.extensionsRequired,
      scene: 0, scenes: [{ ...scene, nodes: roots }], nodes, meshes, accessors, bufferViews, buffers: [{ byteLength: data.length }], materials };
    for (const k of Object.keys(doc)) if (doc[k] === undefined) delete doc[k];
    const glb = writeGLB(doc, data);
    const name = `${kind}_${key}.glb`;
    const dst = path.join(OUT, name);
    if (!fs.existsSync(dst) || !fs.readFileSync(dst).equals(glb)) fs.writeFileSync(dst, glb);
    const box = list.reduce((b, it) => [Math.min(b[0], it.box[0]), Math.min(b[1], it.box[1]), Math.max(b[2], it.box[2]), Math.max(b[3], it.box[3])],
      [Infinity, Infinity, -Infinity, -Infinity]).map((v) => Math.round(v * 10) / 10);
    out.push({ file: name, kind, cell: key === 'base' ? null : key.split('_').map(Number), box, bytes: glb.length,
      materials: [...new Set(materials.map((m) => m.name))].sort() });
  }
  return out;
}

export function splitAll() {
  fs.mkdirSync(OUT, { recursive: true });
  const files = [];
  for (const [kind, f] of Object.entries(KINDS)) files.push(...split(kind, path.join(MODELS, f)));
  files.sort((a, b) => (a.cell ? 1 : 0) - (b.cell ? 1 : 0) || a.file.localeCompare(b.file));
  const keep = new Set(files.map((f) => f.file));
  for (const f of fs.readdirSync(OUT)) if (f.endsWith('.glb') && !keep.has(f)) fs.unlinkSync(path.join(OUT, f));
  // (the gate, campus.json spawn: the game asks for the cells round it before campus.json is in)
  let spawn = null;
  try { spawn = JSON.parse(fs.readFileSync(CAMPUS, 'utf8')).spawn.pos; } catch { /* none */ }
  fs.writeFileSync(path.join(OUT, 'chunks.json'), JSON.stringify({ cell: CELL, spawn, files }) + '\n');
  return files;
}

// the cells are older than either GLB or campus.json (or missing)
export function stale() {
  const idx = path.join(OUT, 'chunks.json');
  if (!fs.existsSync(idx)) return true;
  const t = fs.statSync(idx).mtimeMs;
  return [...Object.values(KINDS).map((f) => path.join(MODELS, f)), CAMPUS].some((f) => fs.existsSync(f) && fs.statSync(f).mtimeMs > t);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const t = Date.now(), files = splitAll();
  const sum = (k) => files.filter((f) => f.kind === k).reduce((s, f) => s + f.bytes, 0);
  console.log(`split: ${files.length} files (buildings ${(sum('buildings') / 1e6).toFixed(1)} MB, landmarks ${(sum('landmarks') / 1e6).toFixed(1)} MB) in ${Date.now() - t} ms`);
}
