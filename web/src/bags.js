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
// A carried bag is in the right hand because the wave (emote-yes) lifts the left arm; such a person waves instead of
// using the right hand (life.js). The heroes' bags are fixed (HERO_BAGS), never carried in the hand: the basketball
// takes both hands (hoops.js).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

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
  'man-tee': { type: 'backpack', color: '#1b1b1e', size: 1 },
  'man-cheer': { type: 'sling', color: '#55585e', side: -1, size: 1 },
  'woman-tee': { type: 'mini', color: '#5a3a24', size: 1 },
  'woman-dress': { type: 'shoulder', color: '#4e3022', side: 1, size: 1 },
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
  const woman = id.startsWith('woman');
  const kind = id === 'man-professor' ? 'prof' : id.endsWith('-staff') ? 'staff' : 'student';
  if ((n * 0.6180339887 + 0.31) % 1 >= (kind === 'prof' ? 0.85 : kind === 'staff' ? 0.55 : 0.7)) return null;
  let type;
  if (kind !== 'student') type = woman ? choose(r(), [['shoulder', 0.6], ['brief', 0.4]]) : 'brief';
  else if (woman) {
    type = choose(r(), [['backpack', 0.18], ['mini', 0.14], ['sling', 0.1], ['shoulder', 0.28], ['cross', 0.12],
      ['hand', 0.18]]);
  } else type = choose(r(), [['backpack', 0.42], ['sling', 0.26], ['cross', 0.24], ['brief', id === 'man-blazer' ? 0.3 : 0.03]]);
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
  const f = {
    bi, shTop, zB: at(back), zF: at(front), xS: at(side),
    backMin: over(back, Math.min), frontMax: over(front, Math.max), sideMax: over(side, Math.max),
    chest: rest('Chest'), torso: rest('Torso'), abd: rest('Abdomen'), hips: rest('Hips'), wristR: rest('WristR'),
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
      const w = weigh(P.getX(i), P.getY(i), P.getZ(i)).filter(([, v]) => v > 0.001).slice(0, 4);
      const sum = w.reduce((s, [, v]) => s + v, 0) || 1;
      w.forEach(([b, v], k) => { si[i * 4 + k] = b; sw[i * 4 + k] = v / sum; });
    }
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
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

// a backpack on the back: sling = hanging off one shoulder (side: +1 the left, -1 the right) by that strap only
function backpack(kit, f, col, trim, s, woman, { mini = false, sling = false, side = -1 } = {}) {
  const { bi } = f;
  const [w, h, d] = (mini ? [0.22, 0.26, 0.09] : woman ? [0.27, 0.35, 0.12] : [0.3, 0.4, 0.13]).map((v) => v * s);
  const drop = sling ? 0.09 : 0;
  const tilt = sling ? side * 0.22 : 0;                      // (a sling leans out from the shoulder it hangs from)
  const yT = f.shTop - 0.055 - drop, yB = yT - h;
  const xc = sling ? side * 0.05 : 0;
  const zIn = f.backMin(yB - 0.03, yT) - 0.014;              // its face against the back
  const zc = zIn - d / 2;
  // from the chest at the top to half spine at the bottom: the bag follows the back as it bends
  const weigh = (x, y) => { const t = ss(yB, yT, y); return [[bi.Chest, 0.45 + 0.55 * t], [bi.Torso, 0.55 - 0.55 * t]]; };
  const rough = mini ? 0.55 : 0.8;
  const body = placed(pillow(w, h, d, { r: mini ? 0.05 : 0.07, bevel: 0.02, bulge: d * 0.25, taper: 0.14 }), xc, (yT + yB) / 2, zc, 0, tilt);
  kit.add(body, col, rough, weigh);
  const pocket = placed(pillow(w * 0.68, h * 0.4, 0.05, { r: 0.035, bevel: 0.012, bulge: 0.01 }), 0, 0, 0);
  // (the parts below the bag's middle move out with its lean: a point a below the middle turns to x = a sin(tilt))
  kit.add(placed(pocket, xc + Math.sin(tilt) * h * 0.2, yB + h * 0.3, zc - d / 2 - 0.022, 0, tilt), trim, rough, weigh);
  if (!mini) kit.add(placed(pillow(w * 0.96, 0.05, d * 0.9, { r: 0.02, bevel: 0.01 }), xc + Math.sin(tilt) * (h / 2 - 0.02), yB + 0.02, zc, 0, tilt), trim, rough, weigh);
  // shoulder straps: from the bag's top over the shoulder, down the chest, under the arm to the bag's lower corner
  const sides = sling ? [side] : [-1, 1];
  const yS = f.shTop, yA = f.shTop - 0.2;
  for (const sx of sides) {
    const mid = (y) => (f.zB(y) + f.zF(y)) / 2;
    const pts = [V(xc + sx * 0.07, yT - 0.02, zIn - 0.02),
      V(sx * 0.085, yS - 0.04, f.zB(yS - 0.04) - 0.006), V(sx * 0.092, yS + 0.006, mid(yS)),
      V(sx * 0.1, yS - 0.05, f.zF(yS - 0.05) + 0.006), V(sx * 0.11, yS - 0.12, f.zF(yS - 0.12) + 0.006),
      V(sx * 0.125, yA + 0.02, f.zF(yA + 0.02) * 0.7 + mid(yA) * 0.3 + 0.006),
      V(sx * (f.xS(yA - 0.03) + 0.006), yA - 0.03, mid(yA - 0.03)),
      V(xc + sx * (w / 2 - 0.035), yB + 0.07, zIn - 0.02)];
    const outs = [V(0, 0, -1), V(0, 0.3, -1), V(0, 1, 0), V(0, 0.3, 1), V(0, 0, 1), V(sx * 0.4, 0, 1), V(sx, 0, 0), V(sx * 0.5, 0, -1)];
    if (sling) { pts.splice(7); outs.splice(7); }              // (the free end of a sling's strap is under the arm)
    const sb = sx > 0 ? bi.ShoulderL : bi.ShoulderR;
    const sw = (x, y, z) => (y > yS - 0.07 && z > f.zB(yS) ? [[bi.Chest, 0.6], [sb, 0.4]] : weigh(x, y));
    kit.add(strap(pts, outs, mini ? 0.028 : 0.042, 0.007), trim, rough, sw);
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

// a bag behind the hip on the side sx: across the chest from the other shoulder (cross) or from its own (shoulder)
function hipBag(kit, f, col, trim, s, woman, { cross = true, side = 1 } = {}) {
  const { bi } = f;
  const sx = side;
  const [w, h, d] = (cross ? (woman ? [0.27, 0.2, 0.07] : [0.32, 0.25, 0.08]) : [0.26, 0.19, 0.085]).map((v) => v * s);
  const yT = cross ? f.abd.y + 0.03 : f.torso.y - 0.02, yB = yT - h;
  const a = cross ? 0.95 : 1.25;                             // how far round from the back it sits
  const span = [yB - 0.04, yT + 0.02];
  const at = round(f, (yT + yB) / 2, a, sx, d / 2 + 0.02, span);
  const ry = Math.atan2(-at.n.x, -at.n.z);
  const rough = cross ? 0.75 : 0.55;                         // nylon or canvas, leather
  const bagBone = cross ? bi.Body : bi.Torso;              // a cross bag rides on the pelvis, a shoulder bag on the spine
  const bag = placed(pillow(w, h, d, { r: cross ? 0.03 : 0.05, bevel: 0.014, bulge: 0.008 }), at.p.x, (yT + yB) / 2, at.p.z, ry);
  kit.add(bag, col, rough, () => [[bagBone, 1]]);
  // a flap over the outer face
  const flap = placed(pillow(w * 1.02, h * 0.62, 0.012, { r: 0.03, bevel: 0.004 }), 0, 0, 0);
  kit.add(placed(flap, at.p.x + at.n.x * (d / 2 + 0.004), yT - h * 0.31 + 0.004, at.p.z + at.n.z * (d / 2 + 0.004), ry), trim, rough, () => [[bagBone, 1]]);
  // the strap: from the bag's front end round the side, up across the chest (or the side) over a shoulder, and down
  // the back to the bag's back end
  const tl = V(Math.cos(ry), 0, -Math.sin(ry));            // the bag's length axis in the person's frame
  const end = (u) => at.p.clone().addScaledVector(tl, u * (w / 2 - 0.03)).setY(yT - 0.01);
  const fwd = tl.z > 0 ? 1 : -1;                            // which end of the bag is towards the front
  const yS = f.shTop, wb = (y) => [[bi.Chest, ss(f.abd.y, f.chest.y, y)], [bagBone, 1 - ss(f.abd.y, f.chest.y, y)]];
  let pts, outs;
  if (cross) {
    const os = -sx;                                         // the other shoulder
    const fr = [round(f, yT + 0.05, 1.75, sx, 0.008), round(f, f.abd.y + 0.12, 2.6, sx, 0.008),
      round(f, f.chest.y - 0.02, Math.PI, sx, 0.008), round(f, yS - 0.07, 2.75, os, 0.008)];
    const bk = [round(f, yS - 0.07, 0.35, os, 0.008), round(f, f.chest.y - 0.04, 0.1, sx, 0.008),
      round(f, f.abd.y + 0.1, 0.55, sx, 0.008)];
    pts = [end(fwd), ...fr.map((q) => q.p), V(os * 0.095, yS + 0.007, (f.zB(yS) + f.zF(yS)) / 2), ...bk.map((q) => q.p), end(-fwd)];
    outs = [at.n, ...fr.map((q) => q.n), V(0, 1, 0), ...bk.map((q) => q.n), at.n];
  } else {
    const fr = [round(f, yT + 0.06, 1.6, sx, 0.008), round(f, f.chest.y, 1.85, sx, 0.008), round(f, yS - 0.06, 2.2, sx, 0.008)];
    const bk = [round(f, yS - 0.06, 0.95, sx, 0.008), round(f, f.chest.y, 1.1, sx, 0.008), round(f, yT + 0.06, 1.15, sx, 0.008)];
    pts = [end(fwd), ...fr.map((q) => q.p), V(sx * 0.11, yS + 0.007, (f.zB(yS) + f.zF(yS)) / 2), ...bk.map((q) => q.p), end(-fwd)];
    outs = [at.n, ...fr.map((q) => q.n), V(0, 1, 0), ...bk.map((q) => q.n), at.n];
  }
  kit.add(strap(pts, outs, cross ? 0.035 : 0.022, 0.006), trim, rough, (x, y) => wb(y));
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

// the geometry of person `id` (its template SkinnedMesh) carrying `bag`: the body's own merged with the bag's,
// shared by everyone of that look
export function baggedGeometry(mesh, id, bag) {
  const key = `${id}|${bag.type}|${bag.color}|${bag.side ?? 0}|${bag.size ?? 1}`;
  if (cache.has(key)) return cache.get(key);
  const f = fitOf(id, mesh);
  const woman = id.startsWith('woman');
  const col = new THREE.Color(bag.color);
  const hsl = col.getHSL({});
  // straps and trim: a shade darker; on a light leather bag the same leather a little darker
  const trim = col.clone().offsetHSL(0, 0, -Math.min(0.06, hsl.l * 0.35));
  const s = bag.size ?? 1, side = bag.side ?? -1;
  const kit = new Kit();
  switch (bag.type) {
    case 'backpack': backpack(kit, f, col, trim, s, woman); break;
    case 'mini': backpack(kit, f, col, trim, s, woman, { mini: true }); break;
    case 'sling': backpack(kit, f, col, trim, s, woman, { sling: true, side }); break;
    case 'cross': hipBag(kit, f, col, trim, s, woman, { cross: true, side }); break;
    case 'shoulder': hipBag(kit, f, col, trim, s, woman, { cross: false, side }); break;
    case 'brief': carried(kit, f, col, trim, s, true, woman); break;
    case 'hand': carried(kit, f, col, trim, s, false, woman); break;
    default: return mesh.geometry;
  }
  const merged = mergeGeometries([mesh.geometry, ...kit.geos], false);
  for (const g of kit.geos) g.dispose();
  const out = merged || mesh.geometry;
  cache.set(key, out);
  return out;
}

// whether the bag is carried in the (right) hand
export const carriesInHand = (bag) => !!bag && (bag.type === 'brief' || bag.type === 'hand');
