// Bags: about 70 % of the people on campus carry one, as students did in 1997 (the user's request; reference/
// 1997_중앙도서관.jpg: five of the six students walking past carry a backpack or a shoulder bag, the 2003 spring
// photos the same). In the manner of blender/characters.py's outfits, 1997 kinds and colours:
//  backpack  두 어깨 백팩: nylon in black, navy, forest green, burgundy, royal blue, grey, khaki (JanSport, Eastpak)
//  mini      작은 가죽 백팩: brown or black leather, the women's fashion of 1996-97
//  sling     한쪽 어깨에 걸친 백팩: the same backpack hanging lower off one shoulder by one strap
//  cross     크로스백 · 메신저백: across the chest, the bag behind the hip; black or navy nylon, khaki canvas, leather
//  shoulder  숄더백: a small leather bag under the arm on its own shoulder's strap (women)
//  hand      손가방: a small handbag carried by its handles (women)
//  brief     서류가방: professors and staff, now and then a student in a blazer
// A bag is built here in the people's bind pose (blender/characters.py: the T-pose, feet at y 0, facing +Z, +X the
// person's left, real height in metres), fitted to that person's torso and hips (the bands of their own vertices),
// skinned to the bones it hangs from (a backpack blended from the chest down to the spine, a hip bag to the pelvis, a
// carried bag rigidly to the right hand), and merged into the person's one vertex-coloured SkinnedMesh
// (characters.js Cast.make): no draw call more, in the shadow pass neither, and the walk cycle carries it along.
// A strap over a shoulder is laid on the body as it stands with the arms down (the idle's first frame: in the bind
// pose the arms stand out and the shoulders are high), on the body's own surface, and taken back to the bind pose
// (slung).
// A carried bag is in the right hand because the wave (emote-yes) lifts the left arm; such a person waves instead of
// using the right hand (life.js). The heroes' bags are fixed (HERO_BAGS), never carried in the hand: the basketball
// takes both hands (hoops.js).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { isWoman, kindOf } from './who.js';

const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
const ss = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

// sRGB colours, with a weight: how often each turns up
const PALETTE = {
  backpack: [['#1b1b1e', 4], ['#1f2a46', 3], ['#24402f', 1.5], ['#5c1f28', 1.5], ['#27458c', 1], ['#55585e', 1],
    ['#7c6b4b', 1], ['#3d2c55', 0.6], ['#8a2626', 0.5]],
  mini: [['#5a3a24', 3], ['#1b1b1e', 2], ['#8a6646', 1.5], ['#2f2f36', 1]],
  cross: [['#1b1b1e', 3], ['#232a3c', 2], ['#6e6650', 2], ['#4a3324', 1.5], ['#3b4430', 1]],
  shoulder: [['#1b1b1e', 3], ['#4e3022', 2], ['#9e7a54', 1.5], ['#5d2229', 1], ['#d6cbb6', 1]],
  hand: [['#1b1b1e', 3], ['#5a3a26', 2], ['#b4966f', 1.5], ['#6a1f2b', 1]],
  brief: [['#18181a', 3], ['#2e1f17', 2], ['#4a2a1e', 1]],
};
PALETTE.sling = PALETTE.backpack;

// the player's characters (characters.js HEROES): four of the thirteen
export const HERO_BAGS = {
  'p01': { type: 'backpack', color: '#1b1b1e', size: 1 },
  'p04': { type: 'sling', color: '#55585e', side: -1, size: 1 },
  'p09': { type: 'mini', color: '#5a3a24', size: 1 },
  'p11': { type: 'shoulder', color: '#4e3022', side: 1, size: 1 },
};

function rng(seed) {
  let a = (Math.imul(seed | 0, 2654435761) + 0x9e3779b9) >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function choose(u, list) {
  let sum = 0;
  for (const [, w] of list) sum += w;
  let x = u * sum;
  for (const [v, w] of list) { if ((x -= w) < 0) return v; }
  return list[list.length - 1][0];
}

// the bag of the n-th person of the crowd (or none): its own random stream, so the crowd's paths and faces stay
// where they were. Students 70 %, professors 85 % (a briefcase), staff 55 %; whether one carries a bag at all is
// read off the golden-ratio sequence, so that any dozen people in a row come near the share, the phone's smaller
// crowd too
export function crowdBag(id, n) {
  const r = rng(n * 7919 + 101);
  const woman = isWoman(id);
  const kind = kindOf(id);
  if ((n * 0.6180339887 + 0.31) % 1 >= (kind === 'prof' ? 0.85 : kind === 'staff' ? 0.55 : 0.7)) return null;
  let type;
  if (kind !== 'student') type = woman ? choose(r(), [['shoulder', 0.6], ['brief', 0.4]]) : 'brief';
  else if (woman) {
    type = choose(r(), [['backpack', 0.18], ['mini', 0.14], ['sling', 0.1], ['shoulder', 0.28], ['cross', 0.12],
      ['hand', 0.18]]);
  } else type = choose(r(), [['backpack', 0.42], ['sling', 0.26], ['cross', 0.24], ['brief', id === 'p06' ? 0.3 : 0.03]]);
  return { type, color: choose(r(), PALETTE[type]), side: r() < 0.6 ? -1 : 1, size: [0.93, 1, 1.07][Math.floor(r() * 3)] };
}

// ---------------------------------------------------------------------------------------------------------------
// the person's build, read off their bind-pose vertices: torso front / back and half width in 2 cm bands (arms,
// hands, neck and head left out, the legs and a dress kept), the top of the shoulders, the bones' rest positions
const ARM = /^(UpperArm|LowerArm|Wrist|Index|Middle|Ring|Pinky|Thumb|Neck|Head)/;
const Y0 = 0.3, DY = 0.02, NB = 70;
const fits = new Map();

function fitOf(id, mesh) {
  if (fits.has(id)) return fits.get(id);
  const g = mesh.geometry, P = g.attributes.position, SI = g.attributes.skinIndex, SW = g.attributes.skinWeight;
  const bones = mesh.skeleton.bones;
  const bi = {};
  bones.forEach((b, i) => { bi[b.name] = i; });
  const m4 = new THREE.Matrix4();
  const rest = (n) => V().setFromMatrixPosition(m4.copy(mesh.skeleton.boneInverses[bi[n]]).invert()
    .premultiply(mesh.bindMatrixInverse));
  const skipBone = bones.map((b) => ARM.test(b.name));
  const skip = new Uint8Array(P.count);
  let shTop = 0;
  for (let i = 0; i < P.count; i++) {
    let k = 0, w = -1;
    for (let j = 0; j < 4; j++) { const ww = SW.getComponent(i, j); if (ww > w) { w = ww; k = SI.getComponent(i, j); } }
    skip[i] = skipBone[k] ? 1 : 0;
    const x = Math.abs(P.getX(i));
    if (!skip[i] && x > 0.05 && x < 0.15) shTop = Math.max(shTop, P.getY(i));
  }
  // the surface's cross-section at each band's middle (the mesh is low-poly: its vertices lie in loops several bands
  // apart, so the triangles are cut, not the vertices read)
  const back = new Float32Array(NB).fill(9), front = new Float32Array(NB).fill(-9), side = new Float32Array(NB).fill(-9);
  const I = g.index, E = [[0, 1], [1, 2], [2, 0]], v = [0, 0, 0];
  for (let t = 0; t < I.count; t += 3) {
    v[0] = I.getX(t); v[1] = I.getX(t + 1); v[2] = I.getX(t + 2);
    if (skip[v[0]] || skip[v[1]] || skip[v[2]]) continue;
    const ys = v.map((i) => P.getY(i));
    const k0 = Math.max(0, Math.ceil((Math.min(...ys) - Y0) / DY - 0.5)), k1 = Math.min(NB - 1, Math.floor((Math.max(...ys) - Y0) / DY - 0.5));
    for (let k = k0; k <= k1; k++) {
      const yk = Y0 + (k + 0.5) * DY;
      for (const [p, q] of E) {
        const yp = ys[p], yq = ys[q];
        if (yp === yq || (yp - yk) * (yq - yk) > 0) continue;
        const s = (yk - yp) / (yq - yp);
        const x = P.getX(v[p]) + s * (P.getX(v[q]) - P.getX(v[p])), z = P.getZ(v[p]) + s * (P.getZ(v[q]) - P.getZ(v[p]));
        if (Math.abs(x) < 0.13) { back[k] = Math.min(back[k], z); front[k] = Math.max(front[k], z); }
        side[k] = Math.max(side[k], Math.abs(x));
      }
    }
  }
  for (const a of [back, front, side]) {             // empty bands take their nearest neighbour's
    for (let b = 1; b < NB; b++) if (Math.abs(a[b]) === 9) a[b] = a[b - 1];
    for (let b = NB - 2; b >= 0; b--) if (Math.abs(a[b]) === 9) a[b] = a[b + 1];
  }
  const at = (a) => (y) => {
    const f = Math.min(NB - 1.001, Math.max(0, (y - Y0) / DY - 0.5)), i = Math.floor(f);
    return a[i] + (a[i + 1] - a[i]) * (f - i);
  };
  // the extreme over a span of heights: what a rigid bag must clear
  const over = (a, fn) => (y0, y1) => {
    let v = fn === Math.min ? 9 : -9;
    for (let b = Math.max(0, Math.floor((y0 - Y0) / DY)); b <= Math.min(NB - 1, Math.floor((y1 - Y0) / DY)); b++) v = fn(v, a[b]);
    return v;
  };
  // the surface itself, for what must lie on it (a shoulder bag and its strap): the triangles of the trunk and the
  // legs, and those with the upper arms
  const upper = bones.map((b) => /^UpperArm/.test(b.name));
  const major = new Uint16Array(P.count);
  for (let i = 0; i < P.count; i++) {
    let k = 0, w = -1;
    for (let j = 0; j < 4; j++) { const ww = SW.getComponent(i, j); if (ww > w) { w = ww; k = SI.getComponent(i, j); } }
    major[i] = k;
  }
  const trunk = [], armed = [];
  for (let t = 0; t < I.count; t += 3) {
    const a = I.getX(t), b = I.getX(t + 1), c = I.getX(t + 2);
    const sk = skip[a] + skip[b] + skip[c];
    if (!sk) trunk.push(a, b, c);
    if (!sk || [a, b, c].every((i) => !skip[i] || upper[major[i]])) armed.push(a, b, c);
  }
  // the body as it stands now: Cast.make (characters.js) has put the bones in the idle's first frame, the arms
  // hanging, which is how a strap must be laid (in the bind pose the arms stand out sideways and the shoulders
  // are high). Each bone's matrix from the bind pose to this one, and the vertices there
  const pose = bones.map((b, i) => new THREE.Matrix4().copy(mesh.bindMatrixInverse).multiply(b.matrixWorld)
    .multiply(mesh.skeleton.boneInverses[i]).multiply(mesh.bindMatrix));
  const blend = (ws) => {                                   // the matrix of a point with these bone weights
    const e = new Array(16).fill(0);
    let sum = 0;
    for (const [b, w] of ws) { sum += w; for (let k = 0; k < 16; k++) e[k] += pose[b].elements[k] * w; }
    return new THREE.Matrix4().fromArray(e.map((x) => x / sum));
  };
  const bind = new Float32Array(P.count * 3), stood = new Float32Array(P.count * 3), _p = V();
  for (let i = 0; i < P.count; i++) {
    bind.set([P.getX(i), P.getY(i), P.getZ(i)], i * 3);
    const ws = [];
    for (let j = 0; j < 4; j++) if (SW.getComponent(i, j) > 0) ws.push([SI.getComponent(i, j), SW.getComponent(i, j)]);
    _p.fromArray(bind, i * 3).applyMatrix4(blend(ws)).toArray(stood, i * 3);
  }
  // where the ray from o (inside the body) along d leaves it within `far`: the last surface it crosses, and the bone
  // weights of the skin there. arms: with the upper arms; standing: the body as it stands, not the bind pose
  // (each triangle's box, for each list and pose: one far from the ray's segment is passed over, in the same order)
  const boxes = new Map();
  const boxOf = (tris, X) => {
    const key = (tris === armed ? 1 : 0) + (X === stood ? 2 : 0);
    if (boxes.has(key)) return boxes.get(key);
    const B = new Float32Array(tris.length * 2);            // per triangle: min x y z, max x y z
    for (let k = 0; k < tris.length; k += 3) {
      for (let c = 0; c < 3; c++) {
        const a = X[tris[k] * 3 + c], b = X[tris[k + 1] * 3 + c], e = X[tris[k + 2] * 3 + c];
        B[k * 2 + c] = Math.min(a, b, e);
        B[k * 2 + 3 + c] = Math.max(a, b, e);
      }
    }
    boxes.set(key, B);
    return B;
  };
  const ray = (o, d, { arms = false, standing = false, far = 0.3 } = {}) => {
    const tris = arms ? armed : trunk, X = standing ? stood : bind, B = boxOf(tris, X);
    const E = 1e-5;
    const x0 = Math.min(o.x, o.x + d.x * far) - E, x1 = Math.max(o.x, o.x + d.x * far) + E;
    const y0 = Math.min(o.y, o.y + d.y * far) - E, y1 = Math.max(o.y, o.y + d.y * far) + E;
    const z0 = Math.min(o.z, o.z + d.z * far) - E, z1 = Math.max(o.z, o.z + d.z * far) + E;
    let bt = 0, bk = -1, bu = 0, bv = 0;
    for (let k = 0; k < tris.length; k += 3) {
      const q = k * 2;
      if (B[q + 4] < y0 || B[q + 1] > y1 || B[q + 3] < x0 || B[q] > x1 || B[q + 5] < z0 || B[q + 2] > z1) continue;
      const a = tris[k] * 3, b = tris[k + 1] * 3, c = tris[k + 2] * 3;
      const ax = X[a], ay = X[a + 1], az = X[a + 2];
      const e1x = X[b] - ax, e1y = X[b + 1] - ay, e1z = X[b + 2] - az;
      const e2x = X[c] - ax, e2y = X[c + 1] - ay, e2z = X[c + 2] - az;
      const px = d.y * e2z - d.z * e2y, py = d.z * e2x - d.x * e2z, pz = d.x * e2y - d.y * e2x;
      const det = e1x * px + e1y * py + e1z * pz;
      if (Math.abs(det) < 1e-12) continue;
      const tx = o.x - ax, ty = o.y - ay, tz = o.z - az;
      const u = (tx * px + ty * py + tz * pz) / det;
      if (u < 0 || u > 1) continue;
      const qx = ty * e1z - tz * e1y, qy = tz * e1x - tx * e1z, qz = tx * e1y - ty * e1x;
      const v = (d.x * qx + d.y * qy + d.z * qz) / det;
      if (v < 0 || u + v > 1) continue;
      const tt = (e2x * qx + e2y * qy + e2z * qz) / det;
      if (tt > bt && tt < far) { bt = tt; bk = k; bu = u; bv = v; }
    }
    if (bk < 0) return null;
    const ws = new Map();
    [[tris[bk], 1 - bu - bv], [tris[bk + 1], bu], [tris[bk + 2], bv]].forEach(([i, m]) => {
      for (let j = 0; j < 4; j++) {
        const w = SW.getComponent(i, j) * m;
        if (w > 0) ws.set(SI.getComponent(i, j), (ws.get(SI.getComponent(i, j)) || 0) + w);
      }
    });
    return { p: o.clone().addScaledVector(d, bt), w: [...ws] };
  };
  const f = {
    bi, shTop, zB: at(back), zF: at(front), xS: at(side), ray, blend, ofArm: skipBone,
    backMin: over(back, Math.min), frontMax: over(front, Math.max), sideMax: over(side, Math.max),
    chest: rest('Chest'), torso: rest('Torso'), abd: rest('Abdomen'), hips: rest('Hips'), wristR: rest('WristR'),
    // (the shoulder joints as the body stands)
    armL: V().setFromMatrixPosition(pose[bi.UpperArmL].clone().multiply(new THREE.Matrix4().setPosition(rest('UpperArmL')))),
    armR: V().setFromMatrixPosition(pose[bi.UpperArmR].clone().multiply(new THREE.Matrix4().setPosition(rest('UpperArmR')))),
  };
  fits.set(id, f);
  return f;
}

// ---------------------------------------------------------------------------------------------------------------
// geometry: a soft rounded box and a strap, each an indexed BufferGeometry with positions and normals

// a box w x h x d (outline in x y, depth along z) with rounded corners r and edges rounded by `bevel`; the -z face
// bulges out by `bulge` (a filled backpack), the top is narrower by `taper`
function pillow(w, h, d, { r = 0.04, bevel = 0.015, seg = 2, bulge = 0, taper = 0 } = {}) {
  const ring = (inset) => {
    const pts = [], hw = w / 2 - inset, hh = h / 2 - inset, rr = Math.max(0.003, Math.min(r - inset * 0.5, hw, hh));
    const cs = [[hw - rr, hh - rr], [-(hw - rr), hh - rr], [-(hw - rr), -(hh - rr)], [hw - rr, -(hh - rr)]];
    cs.forEach(([cx, cy], q) => {
      for (let k = 0; k <= seg; k++) {
        const a = (q + k / seg) * Math.PI / 2;
        pts.push([cx + rr * Math.cos(a), cy + rr * Math.sin(a)]);
      }
    });
    return pts;
  };
  const rings = [[ring(bevel), -d / 2], [ring(0), -d / 2 + bevel], [ring(0), d / 2 - bevel], [ring(bevel), d / 2]];
  const M = rings[0][0].length, pos = [], idx = [];
  for (const [pts, z] of rings) for (const [x, y] of pts) pos.push(x * (1 - taper * (y / h + 0.5)), y, z);
  for (let k = 0; k < 3; k++) {
    for (let i = 0; i < M; i++) {
      const a = k * M + i, b = k * M + (i + 1) % M;
      idx.push(a, b, b + M, a, b + M, a + M);
    }
  }
  const c0 = pos.length / 3;
  pos.push(0, 0, -d / 2 - bulge, 0, 0, d / 2);
  for (let i = 0; i < M; i++) {
    const b = (i + 1) % M;
    idx.push(c0, b, i, c0 + 1, 3 * M + i, 3 * M + b);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

// a strap of width x thickness along points lying on what it rests on (outs: the outward normal at each); its ends
// are left open (they are inside the bag or the hand)
function strap(pts, outs, width, thick) {
  const pos = [], idx = [], n = pts.length, T = V(), N = V(), B = V(), ctr = [];
  for (let i = 0; i < n; i++) {
    T.subVectors(pts[Math.min(n - 1, i + 1)], pts[Math.max(0, i - 1)]).normalize();
    N.copy(outs[i]).addScaledVector(T, -outs[i].dot(T)).normalize();
    B.crossVectors(T, N).normalize();
    for (const [u, v] of [[-1, 0], [1, 0], [1, 1], [-1, 1]]) {
      const p = pts[i].clone().addScaledVector(B, u * width / 2).addScaledVector(N, v * thick);
      pos.push(p.x, p.y, p.z);
    }
    ctr.push(pts[i].clone().addScaledVector(N, thick / 2));
  }
  const p = (k) => V(pos[k * 3], pos[k * 3 + 1], pos[k * 3 + 2]);
  for (let i = 0; i < n - 1; i++) {
    for (const [s, t] of [[0, 1], [1, 2], [2, 3], [3, 0]]) {
      const a = i * 4 + s, b = i * 4 + t, c = (i + 1) * 4 + t, e = (i + 1) * 4 + s;
      const nrm = V().subVectors(p(b), p(a)).cross(V().subVectors(p(c), p(a)));
      const mid = p(a).add(p(b)).add(p(c)).add(p(e)).multiplyScalar(0.25).sub(ctr[i].clone().add(ctr[i + 1]).multiplyScalar(0.5));
      if (nrm.dot(mid) >= 0) idx.push(a, b, c, a, c, e); else idx.push(a, c, b, a, e, c);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

// the parts of one bag with their colour, roughness and bone weights (weigh(x, y, z) -> [[bone, w], ...])
class Kit {
  constructor() { this.geos = []; }
  add(g, color, rough, weigh) {
    const P = g.attributes.position, n = P.count;
    const col = new Float32Array(n * 3), part = new Float32Array(n * 3);
    const si = new Uint16Array(n * 4), sw = new Float32Array(n * 4);
    for (let i = 0; i < n; i++) {
      col.set([color.r, color.g, color.b], i * 3);
      part.set([rough, 3, 0], i * 3);            // (characters.js `part`: roughness, a hard thing, nothing shades it)
      const w = weigh(P.getX(i), P.getY(i), P.getZ(i), i).filter(([, v]) => v > 0.001).slice(0, 4);
      const sum = w.reduce((s, [, v]) => s + v, 0) || 1;
      w.forEach(([b, v], k) => { si[i * 4 + k] = b; sw[i * 4 + k] = v / sum; });
    }
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.userData.tone = color === TONE.col ? 'col' : color === TONE.trim ? 'trim' : null;     // (baggedGeometry)
    g.setAttribute('part', new THREE.Float32BufferAttribute(part, 3));
    g.setAttribute('leg', new THREE.Uint8BufferAttribute(new Uint8Array(n * 4), 4, true));     // (not trousers)
    // (the people's material draws the faces from an atlas: a bag lies on its blank cell, characters.js BLANK_UV)
    g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(n * 2).fill(0.9), 2));
    g.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(si, 4));
    g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(sw, 4));
    this.geos.push(g);
  }
}

const placed = (g, x, y, z, ry = 0, rz = 0) => g.applyMatrix4(new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(0, ry, rz, 'YXZ')))
  .translate(x, y, z);

// ---------------------------------------------------------------------------------------------------------------
// the bags, each fitted to the person (f), its colour col / trim, size s

// a strap over the shoulder of the side sh (+1 the left), laid on the body as it stands with the arms down (fitOf)
// and then taken back to the bind pose: an arc over the shoulder (arcDeg: from the front to the back, 90 straight
// up; inset: how far in from the joint, of the joint's distance from the middle), and from the arc's two ends the
// way down to where the strap is fixed.  front / back: { to (that point, in the bind pose), w (the bone weights it
// moves with), face(t) (which way the strap faces on its way down, t 0 at the arc .. 1 at the point: added to the
// arc's own way as that fades), direct (no way down: straight from the arc to the point) }.
// The way down is the straight line to the point, each sample of it pushed out of the body the way it faces, and
// the whole is drawn tight: no sample further in than half way between its neighbours, so the strap spans the
// hollows and leaves the body where the straight way to its end does.
// Over the shoulder each sample moves with the skin under it (half of the arm's share: a strap does not go with the
// arm as a sleeve does); further down the strap is a band between the shoulder and its end, the weights going
// evenly from the one's to the other's, so it stays one even line whatever the skin round the armpit does
function slung(kit, f, sh, inset, arcDeg, front, back, width, thick, color, rough) {
  const J = sh > 0 ? f.armL : f.armR;                       // the shoulder joint
  const Cs = V(J.x * (1 - inset), J.y - 0.04, J.z);         // inside the shoulder, under the strap
  const arc = (deg) => V(0, Math.sin(deg * Math.PI / 180), Math.cos(deg * Math.PI / 180));
  const opt = { arms: true, standing: true };
  const hF = f.ray(Cs, arc(arcDeg[0]), opt), hB = f.ray(Cs, arc(arcDeg[arcDeg.length - 1]), opt);
  if (!hF || !hB) return;
  const stood = (e) => e.to.clone().applyMatrix4(f.blend(e.w));
  const eF = stood(front), eB = stood(back);
  const down = (from, d0, e, to, n = 24) => {
    const out = [];
    for (let i = 1; i < n && !e.direct; i++) {
      const t = i / n, q = from.clone().lerp(to, t);
      const dn = d0.clone().multiplyScalar(1 - ss(0, 0.4, t)).add(e.face(t)).normalize();
      out.push({ c: q.addScaledVector(dn, -0.12), d: dn, arms: t < 0.3, far: 0.3, t, e });
    }
    return out;
  };
  const rays = [...down(hF.p, arc(arcDeg[0]), front, eF).reverse(), ...arcDeg.map((deg) => ({ c: Cs, d: arc(deg), arms: true, far: 0.3, t: 0 })),
    ...down(hB.p, arc(arcDeg[arcDeg.length - 1]), back, eB)];
  const on = [];
  for (const g of rays) {
    const hit = f.ray(g.c, g.d, { arms: g.arms, standing: true, far: g.far });
    if (hit) on.push({ c: g.c, n: g.d, r: hit.p.distanceTo(g.c) + 0.0015, w: hit.w, t: g.t, e: g.e, p: V() });
  }
  const put = (q) => q.p.copy(q.c).addScaledVector(q.n, q.r);
  on.forEach(put);
  const mid = V();
  for (let it = 0; it < 60; it++) {
    for (let i = 0; i < on.length; i++) {
      const q = on[i];
      mid.addVectors(i ? on[i - 1].p : eF, i < on.length - 1 ? on[i + 1].p : eB).multiplyScalar(0.5).sub(q.c);
      if (mid.dot(q.n) > q.r) { q.r = mid.dot(q.n); put(q); }
    }
  }
  const mixed = (wa, wb, k) => {
    const ws = new Map(wa.map(([b, v]) => [b, v * (1 - k)]));
    for (const [b, v] of wb) ws.set(b, (ws.get(b) || 0) + v * k);
    return [...ws].sort((p, q) => q[1] - p[1]).slice(0, 4);
  };
  const T0 = 0.3;
  for (const q of on) q.w = mixed(q.w.map(([b, v]) => [b, f.ofArm[b] ? v * 0.5 : v]), [], 0);
  for (const [from, step] of [[on.findIndex((q) => q.t === 0), -1], [on.map((q) => q.t).lastIndexOf(0), 1]]) {
    let last = on[from].w;
    for (let i = from; i >= 0 && i < on.length; i += step) {
      const q = on[i];
      if (q.t <= T0) last = q.w; else q.w = mixed(last, q.e.w, (q.t - T0) / (1 - T0));
    }
  }
  // back to the bind pose
  const pts = [front.to.clone()], outs = [null];
  for (const q of on) {
    const inv = f.blend(q.w).invert();
    pts.push(q.p.clone().applyMatrix4(inv));
    outs.push(q.n.clone().transformDirection(inv));
  }
  pts.push(back.to.clone());
  outs[0] = front.out || outs[1];
  outs.push(back.out || outs[outs.length - 1]);
  const ws = [front.w, ...on.map((q) => q.w), back.w];
  kit.add(strap(pts, outs, width, thick), color, rough, (x, y, z, i) => ws[i >> 2]);
}

// The plane a bag's face lies in against the back between the heights y0 and y1, at the places xs across: of the
// lines z(y) that keep `gap` behind the back at every height, the one that lies closest to it on the whole (both
// its ends as far forward as they may be), leaning no more than BAG_LEAN.  The back is the body as it stands (the
// shoulder blades come back as the arms hang), seen from the bag: a point of the bag's face moves with the bones
// `weigh` gives it, so the back is found along the bag's own way out in the standing pose and taken back to the
// bind pose by the same matrix.  Cloth gives under a loaded bag: a top hanging loose over the hips (its hem 2 cm
// off the trousers), a hood lying on the shoulders.  So the bag's lower half may press into it by up to BAG_PRESS
// (most at the foot), its top edge by BAG_PRESS_TOP.  Returns the face's z at the middle height and the lean
// (radians about x: positive, the foot further back than the top)
const BAG_GAP = 0.006, BAG_LEAN = 0.32, BAG_PRESS = 0.02, BAG_PRESS_TOP = 0.008;
function backFace(f, y0, y1, gap, xs, weigh) {
  const ys = [];
  for (let y = y0; y <= y1 + 1e-6; y += 0.01) ys.push(y);
  const out = V(0, 0, -1);
  const zs = ys.map((y) => {
    let z = f.zB(y);
    for (const x of xs) {
      const M = f.blend(weigh(x, y)), inv = M.clone().invert();
      const o = V(x, y, (f.zB(y) + f.zF(y)) / 2).applyMatrix4(M);
      const hit = f.ray(o, out.clone().transformDirection(M), { standing: true });
      if (hit) z = Math.min(z, hit.p.applyMatrix4(inv).z);
    }
    return z - gap + BAG_PRESS * ss((y0 + y1) / 2, y0 + 0.08, y) + BAG_PRESS_TOP * ss(y1 - 0.04, y1, y);
  });
  const ym = (y0 + y1) / 2, H = y1 - y0;
  // candidates: the line through each pair of heights, and level lines; keep those nowhere in front of the back
  let best = null;
  const tryLine = (k, c) => {                              // z = c + k (y - ym)
    if (Math.abs(Math.atan(k)) > BAG_LEAN) return;
    for (let i = 0; i < ys.length; i++) if (c + k * (ys[i] - ym) > zs[i] + 1e-6) return;
    if (!best || c > best.c) best = { k, c };
  };
  tryLine(0, Math.min(...zs));
  for (let i = 0; i < ys.length; i++) {
    for (let j = i + 1; j < ys.length; j++) {
      const k = (zs[j] - zs[i]) / (ys[j] - ys[i]);
      tryLine(k, zs[i] + k * (ym - ys[i]));
    }
  }
  return { zIn: best.c, lean: Math.atan(best.k), H };
}

// a backpack on the back: sling = hanging off one shoulder (side: +1 the left, -1 the right) by that strap only
function backpack(kit, f, col, trim, s, woman, { mini = false, sling = false, side = -1 } = {}) {
  const { bi } = f;
  const [w, h, d] = (mini ? [0.22, 0.26, 0.09] : woman ? [0.27, 0.35, 0.11] : [0.3, 0.4, 0.12]).map((v) => v * s);
  const drop = sling ? 0.09 : 0;
  const tilt = sling ? side * 0.22 : 0;                      // (a sling leans out from the shoulder it hangs from)
  // (its top a hand under the shoulders' top, on the shoulder blades: higher, it stood off the back where that turns
  // forward to the neck)
  const yT = f.shTop - 0.085 - drop, yB = yT - h;
  const xc = sling ? side * 0.05 : 0;
  // its face against the back: a plane that the back (and a top's hem hanging loose over the hips) nowhere comes
  // through, leaning as it must to touch the back twice: hanging from the straps the bag lies on the shoulder blades
  // and its foot on the small of the back or the hem.  (A plane upright behind the furthest point stood off the
  // shoulder blades by the hem's or the hood's depth: 4 to 5 cm.)
  // from the chest at the top to half spine at the bottom: the bag follows the back as it bends
  const weigh = (x, y) => { const t = ss(yB, yT, y); return [[bi.Chest, 0.45 + 0.55 * t], [bi.Torso, 0.55 - 0.55 * t]]; };
  const { zIn, lean } = backFace(f, yB - 0.03, yT, BAG_GAP, [xc - w * 0.38, xc, xc + w * 0.38], weigh);
  const zc = zIn - d / 2;
  const ym = (yT + yB) / 2;
  const tilt3 = new THREE.Matrix4().makeTranslation(0, ym, zIn).multiply(new THREE.Matrix4().makeRotationX(lean))
    .multiply(new THREE.Matrix4().makeTranslation(0, -ym, -zIn));
  const rough = mini ? 0.55 : 0.8;
  const body = placed(pillow(w, h, d, { r: mini ? 0.05 : 0.07, bevel: 0.02, bulge: d * 0.2, taper: 0.14 }), xc, (yT + yB) / 2, zc, 0, tilt);
  kit.add(body.applyMatrix4(tilt3), col, rough, weigh);
  const pocket = placed(pillow(w * 0.68, h * 0.4, 0.05, { r: 0.035, bevel: 0.012, bulge: 0.01 }), 0, 0, 0);
  // (the parts below the bag's middle move out with its lean: a point a below the middle turns to x = a sin(tilt))
  kit.add(placed(pocket, xc + Math.sin(tilt) * h * 0.2, yB + h * 0.3, zc - d / 2 - 0.022, 0, tilt).applyMatrix4(tilt3), trim, rough, weigh);
  if (!mini) kit.add(placed(pillow(w * 0.96, 0.05, d * 0.9, { r: 0.02, bevel: 0.01 }), xc + Math.sin(tilt) * (h / 2 - 0.02), yB + 0.02, zc, 0, tilt).applyMatrix4(tilt3), trim, rough, weigh);
  // shoulder straps: from the bag's top over the shoulder, down the chest, under the arm and back to the bag's lower
  // corner (a sling's one strap the same)
  for (const sx of sling ? [side] : [-1, 1]) {
    const top = V(xc + sx * 0.07, yT - 0.02, zIn - 0.02).applyMatrix4(tilt3);
    const low = V(xc + sx * (w / 2 - 0.035) + Math.sin(tilt) * (h / 2 - 0.07), yB + 0.07, zIn - 0.02).applyMatrix4(tilt3);
    slung(kit, f, sx, 0.3, [40, 55, 70, 85, 100, 115, 130, 145],
      { to: low, w: weigh(low.x, low.y), out: V(sx * 0.5, 0, -1),
        face: (t) => V(sx * ss(0.2, 0.65, t), 0, ss(0, 0.3, t) * (1 - ss(0.3, 0.7, t)) - 0.7 * ss(0.7, 1, t)) },
      { to: top, w: weigh(top.x, top.y), out: V(0, 0.3, -1), direct: true }, mini ? 0.028 : 0.042, 0.007, trim, rough);
  }
}

// a point on the torso's surface at height y, angle a round it from the back (0) towards the side sx (pi / 2) and
// on to the front (pi), and its outward normal (an ellipse through the band's back, front and half width)
function round(f, y, a, sx, off, span = null) {
  const zb = span ? f.backMin(...span) : f.zB(y), zf = span ? f.frontMax(...span) : f.zF(y);
  const ax = Math.max(0.08, span ? f.sideMax(...span) : f.xS(y)), bz = Math.max(0.06, (zf - zb) / 2), zc = (zf + zb) / 2;
  const n = V(sx * Math.sin(a) / ax, 0, -Math.cos(a) / bz).normalize();
  return { p: V(sx * ax * Math.sin(a), y, zc - bz * Math.cos(a)).addScaledVector(n, off), n };
}

// a cross bag behind the hip on the side sx, its strap across the chest and the back from the other shoulder
function crossBag(kit, f, col, trim, s, woman, side) {
  const { bi } = f;
  const sx = side;
  const [w, h, d] = (woman ? [0.27, 0.2, 0.07] : [0.32, 0.25, 0.08]).map((v) => v * s);
  const yT = f.abd.y + 0.03, yB = yT - h;
  const a = 0.95;                                           // how far round from the back it sits
  const at = round(f, (yT + yB) / 2, a, sx, d / 2 + 0.02, [yB - 0.04, yT + 0.02]);
  const ry = Math.atan2(-at.n.x, -at.n.z);
  const rough = 0.75;                                       // nylon or canvas
  const hang = [[bi.Body, 1]];                              // it rides on the pelvis
  const bag = placed(pillow(w, h, d, { r: 0.03, bevel: 0.014, bulge: 0.008 }), at.p.x, (yT + yB) / 2, at.p.z, ry);
  kit.add(bag, col, rough, () => hang);
  // a flap over the outer face
  const flap = placed(pillow(w * 1.02, h * 0.62, 0.012, { r: 0.03, bevel: 0.004 }), 0, 0, 0);
  kit.add(placed(flap, at.p.x + at.n.x * (d / 2 + 0.004), yT - h * 0.31 + 0.004, at.p.z + at.n.z * (d / 2 + 0.004), ry), trim, rough, () => hang);
  // the strap: from the bag's front end up across the chest, over the other shoulder, and down the back to the
  // bag's back end
  const tl = V(Math.cos(ry), 0, -Math.sin(ry));            // the bag's length axis in the person's frame
  const end = (u) => at.p.clone().addScaledVector(tl, u * (w / 2 - 0.03)).addScaledVector(at.n, -d / 2 + 0.014).setY(yT - 0.01);
  const fwd = tl.z > 0 ? 1 : -1;                            // which end of the bag is towards the front
  const face = (fb) => (t) => V(sx * (fb > 0 ? 1 : 0.8) * ss(0.55, 0.95, t), 0, fb * ss(0, 0.25, t) * (1 - 0.7 * ss(0.6, 0.95, t)));
  slung(kit, f, -sx, 0.34, [50, 63, 77, 90, 103, 117, 130],
    { to: end(fwd), w: hang, out: at.n, face: face(1) }, { to: end(-fwd), w: hang, out: at.n, face: face(-1) }, 0.035, 0.006, trim, rough);
}

// a shoulder bag: at the waist on the side sx, under the arm (which hangs outside it), its long strap over that
// side's shoulder. The bag rests against the body: its inner face clear of the waist at its top and of the hip at its
// bottom (by rays at the body's own surface, not the bands' ellipse), so it leans as the hip is wider.
function shoulderBag(kit, f, col, trim, s, side) {
  const { bi } = f;
  const sx = side;
  const [w, h, d] = [0.23, 0.185, 0.065].map((v) => v * s);
  const yT = f.torso.y + 0.02, yB = yT - h, ym = (yT + yB) / 2;
  const a = 1.0;                                            // how far round from the back it sits
  const zc = (y) => (f.zB(y) + f.zF(y)) / 2;
  const dir = (ang) => V(sx * Math.sin(ang), 0, -Math.cos(ang));
  const at = round(f, ym, a, sx, 0, [yB - 0.04, yT + 0.02]);
  const tl = V(-at.n.z, 0, at.n.x);                         // the bag's length, level
  // how far the body stands out under the bag: near its top, near its bottom
  const stand = (y0, y1) => {
    let m = -1;
    for (let y = y0; y <= y1 + 1e-6; y += 0.015) {
      for (let da = -0.6; da <= 0.6; da += 0.1) {
        const hit = f.ray(V(0, y, zc(y)), dir(a + da));
        if (!hit) continue;
        const q = hit.p.sub(at.p);
        if (Math.abs(q.dot(tl)) < w / 2 - 0.01) m = Math.max(m, q.dot(at.n));
      }
    }
    return m > -1 ? m : 0.02;
  };
  const mT = stand(yT - 0.05, yT - 0.005), mB = stand(yB + 0.005, yB + 0.05);
  const lean = Math.max(-0.1, Math.min(0.2, Math.atan2(mB - mT, h - 0.055)));
  const ctr = at.p.clone().addScaledVector(at.n, Math.max((mT + mB) / 2, stand(yB + 0.05, yT - 0.05) - 0.01) + d / 2 + 0.003).setY(ym);
  const M = new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(lean, Math.atan2(-at.n.x, -at.n.z), 0, 'YXZ')).setPosition(ctr);
  const hang = [[bi.Torso, 0.5], [bi.Hips, 0.5]];           // it hangs from the trunk and rests on the hip
  const rough = 0.55;
  kit.add(pillow(w, h, d, { r: 0.05, bevel: 0.014, bulge: 0.008 }).applyMatrix4(M), col, rough, () => hang);
  // a flap over the outer face
  const flap = pillow(w * 1.02, h * 0.62, 0.012, { r: 0.03, bevel: 0.004 }).translate(0, h * 0.19 + 0.004, -(d / 2 + 0.004));
  kit.add(flap.applyMatrix4(M), trim, rough, () => hang);

  // the strap: from the bag's top (its inner edge) up before the armpit, over the shoulder and down behind it
  const end = (u) => V(u * (w / 2 - 0.025), h / 2 - 0.012, d / 2 - 0.014).applyMatrix4(M);
  let eF = end(1), eB = end(-1);
  if (eF.z < eB.z) [eF, eB] = [eB, eF];
  const face = (fb) => (t) => V(sx * (fb > 0 ? 1 : 0.35) * ss(0.25, 0.9, t), 0, fb * ss(0, 0.3, t) * (1 - 0.8 * ss(0.45, 0.9, t)));
  slung(kit, f, sx, 0.26, [55, 67, 79, 90, 101, 113, 125],
    { to: eF, w: hang, out: at.n, face: face(1) }, { to: eB, w: hang, out: at.n, face: face(-1) }, 0.022, 0.005, trim, rough);
}

// a bag carried by its handles in the right hand (brief: a briefcase, else a handbag). In the T-pose the arm runs
// along -x, so the bag lies along it out from the hand: the walk and the idle lower the arm and it hangs
function carried(kit, f, col, trim, s, brief, woman) {
  const { bi } = f;
  const g = f.wristR.clone().add(V(-0.074, -0.031, 0.012));    // the grip, in the curled fingers
  const [len, hgt, thk] = (brief ? (woman ? [0.36, 0.27, 0.07] : [0.4, 0.3, 0.08]) : [0.27, 0.2, 0.1]).map((v) => v * s);
  const gap = brief ? 0.045 : 0.07;                             // handle height above the bag
  // local x (length) -> z (forward), local y (height) -> -x (out along the arm: down, once it hangs), local z
  // (thickness) -> -y (once it hangs: across, to the side); the bag a little out from the grip, clear of the thigh
  const box = pillow(len, hgt, thk, { r: brief ? 0.02 : 0.045, bevel: brief ? 0.008 : 0.02, taper: brief ? 0 : -0.25 });
  box.applyMatrix4(new THREE.Matrix4().makeBasis(V(0, 0, 1), V(-1, 0, 0), V(0, -1, 0)));
  box.translate(g.x - gap - hgt / 2, g.y + 0.012, g.z);
  const rigid = () => [[bi.WristR, 1]];
  kit.add(box, col, brief ? 0.45 : 0.55, rigid);
  const hz = brief ? 0.05 : 0.07;
  for (const k of brief ? [0] : [-1, 1]) {
    const y = g.y + 0.012 + k * thk * 0.3;
    const pts = [V(g.x - gap - 0.01, y, g.z - hz), V(g.x - gap * 0.45, y, g.z - hz * 0.8), V(g.x + 0.004, y, g.z - hz * 0.3),
      V(g.x + 0.004, y, g.z + hz * 0.3), V(g.x - gap * 0.45, y, g.z + hz * 0.8), V(g.x - gap - 0.01, y, g.z + hz)];
    const outs = pts.map((p) => V(p.x - (g.x - gap), 0, p.z - g.z).normalize());
    kit.add(strap(pts, outs, 0.016, 0.01), trim, 0.5, rigid);
  }
}

// ---------------------------------------------------------------------------------------------------------------
const cache = new Map();
// the bag laid on the person once for each shape (who, which bag, which side, how big), whatever its colour: the
// fit was ~0.7 s of the loading screen's crowd, nearly every bag of it a colour of its own. Its parts drawn in the
// stand-in colours TONE, painted afresh for each colour
const layouts = new Map();
const TONE = { col: new THREE.Color(), trim: new THREE.Color() };

// the geometry of person `id` (its template SkinnedMesh) carrying `bag`: the body's own merged with the bag's,
// shared by everyone of that look
export function baggedGeometry(mesh, id, bag, stand) {
  const key = `${id}|${bag.type}|${bag.color}|${bag.side ?? 0}|${bag.size ?? 1}`;
  if (cache.has(key)) return cache.get(key);
  const lkey = `${id}|${bag.type}|${bag.side ?? 0}|${bag.size ?? 1}`;
  let lay = layouts.get(lkey);
  if (!lay) {
    // (stand: puts the bones as the person stands, and gives back what undoes it; the fit reads the pose once)
    const undo = fits.has(id) ? null : stand?.();
    const f = fitOf(id, mesh);
    undo?.();
    const woman = isWoman(id);
    const { col, trim } = TONE;
    const s = bag.size ?? 1, side = bag.side ?? -1;
    const kit = new Kit();
    switch (bag.type) {
      case 'backpack': backpack(kit, f, col, trim, s, woman); break;
      case 'mini': backpack(kit, f, col, trim, s, woman, { mini: true }); break;
      case 'sling': backpack(kit, f, col, trim, s, woman, { sling: true, side }); break;
      case 'cross': crossBag(kit, f, col, trim, s, woman, side); break;
      case 'shoulder': shoulderBag(kit, f, col, trim, s, side); break;
      case 'brief': carried(kit, f, col, trim, s, true, woman); break;
      case 'hand': carried(kit, f, col, trim, s, false, woman); break;
      default: return mesh.geometry;
    }
    layouts.set(lkey, lay = kit.geos);
  }
  const col = new THREE.Color(bag.color);
  const hsl = col.getHSL({});
  // straps and trim: a shade darker; on a light leather bag the same leather a little darker
  const trim = col.clone().offsetHSL(0, 0, -Math.min(0.06, hsl.l * 0.35));
  const geos = lay.map((g) => {
    const c = g.clone(), tone = g.userData.tone === 'col' ? col : g.userData.tone === 'trim' ? trim : null;
    if (tone) {
      const a = c.attributes.color;
      for (let i = 0; i < a.count; i++) a.setXYZ(i, tone.r, tone.g, tone.b);
    }
    return c;
  });
  const merged = mergeGeometries([mesh.geometry, ...geos], false);
  for (const g of geos) g.dispose();
  const out = merged || mesh.geometry;
  cache.set(key, out);
  return out;
}

// whether the bag is carried in the (right) hand
export const carriesInHand = (bag) => !!bag && (bag.type === 'brief' || bag.type === 'hand');
