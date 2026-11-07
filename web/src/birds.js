// Magpies (까치) on the lawns and pigeons (비둘기) on the paved squares, two to four at a spot. On the ground they walk,
// peck and look round; a person (you or a student) coming within FLEE_R sends them up, the rest of the spot's birds
// following a moment later, in an arc to another lawn, a roof or into a tree 15-70 m away. They settle there, and
// after a while go back home. Blender-free low-poly models made here: a lofted body, head, tail, legs and two wings
// of a few triangles each, coloured per face; the wings fold along the back on the ground and flap in the vertex
// shader (per instance: how open, the flap angle, the head's bob). One InstancedMesh per species and one of soft
// dark patches under them (no shadow map: a 30 cm bird's shadow would need a dynamic caster each).
import * as THREE from 'three';
import { patchShader, pcss, globalPatch } from './materials.js';
import { mulberry, wrapAngle } from './util.js';

// [x, y, radius, species, birds] in campus metres (open lawn or paving, clear of trees and shrubs)
const SPOTS = [
  [-62, -372, 7, 'magpie', 3],     // 정문 안 동쪽 잔디, 백양로 가까이
  [-42, -332, 9, 'magpie', 2],     //   그 북쪽
  [-60, -60, 5, 'pigeon', 4],      // 중앙도서관 앞 광장
  [-63, -18, 5, 'pigeon', 3],
  [7, -71, 3.5, 'pigeon', 3],      // 학생회관 앞
  [-20, -140, 6, 'magpie', 2],     // 백양로 동쪽, 백주년기념관 북쪽 잔디
  [2, -150, 6, 'pigeon', 3],
  [-116, -104, 7, 'magpie', 2],    // 백양로 서쪽 잔디
  [159, -68, 8, 'magpie', 3],      // 루스채플 동쪽 잔디
  [49, 205, 3.5, 'magpie', 2],     // 언더우드관 정원
  [73, 202, 3.5, 'pigeon', 3],
  [145, 185, 6, 'magpie', 3],      // 노천극장 잔디
  [-31, 162, 5, 'pigeon', 3],      // 백양관 앞 잔디
];
const FLEE_R = 4;                  // m: a person this close sends a bird up
const CALM_R = 5;                  // a bird picks no spot on the ground this close to anybody
const SIM_R = 150;                 // farther from the view: the birds wait where they are
const DRAW_R = 160;
const BLOB_R = 70;

const KINDS = {
  pigeon: { walk: 0.42, fly: 9.5, hz: 7.5, size: [0.92, 1.06], peck: 0.62, perch: { roof: 0.5, tree: 0.15 } },
  magpie: { walk: 0.55, fly: 7.5, hz: 5.0, size: [0.95, 1.06], peck: 0.5, perch: { roof: 0.2, tree: 0.45 } },
};
// pigeons are not all the blue-grey rock dove: darker, paler, a chequered brown, a rare white one
const PIGEON_TINTS = [[1, 1, 1], [1, 1, 1], [0.78, 0.78, 0.84], [1.18, 1.14, 1.1], [1.1, 0.88, 0.74], [0.6, 0.6, 0.66], [1.75, 1.72, 1.68]];

// ---------------------------------------------------------------------------- models
const C = (hex) => new THREE.Color(hex);
const BODY = [0, 0, 0];
const HEAD = [0, 0, 1];

function birdGeometry(kind) {
  const P = [], COL = [], F = [], A = [];
  const tri = (a, b, c, col, part = BODY, fold = null) => {
    [a, b, c].forEach((v, i) => {
      P.push(v[0], v[1], v[2]);
      COL.push(col.r, col.g, col.b);
      const f = fold ? fold[i] : v;
      F.push(f[0], f[1], f[2]);
      A.push(part[0], part[1], part[2]);
    });
  };
  const quad = (a, b, c, d, col, part) => { tri(a, b, c, col, part); tri(a, c, d, col, part); };
  const mx = (v) => [-v[0], v[1], v[2]];
  const lerp = (a, b, t) => a.map((x, i) => x + (b[i] - x) * t);
  const M = kind === 'magpie';
  // body: rings of six round the long axis (+Z forward, +Y up, feet at the origin); [z, centre y, half width, half height]
  const rings = M
    ? [[-0.095, 0.155, 0.028, 0.026], [-0.035, 0.152, 0.052, 0.05], [0.035, 0.16, 0.05, 0.05], [0.08, 0.182, 0.034, 0.037], [0.1, 0.21, 0.024, 0.025]]
    : [[-0.085, 0.128, 0.03, 0.025], [-0.03, 0.126, 0.05, 0.046], [0.03, 0.132, 0.052, 0.05], [0.07, 0.152, 0.035, 0.04], [0.086, 0.186, 0.022, 0.025]];
  const ANG = [90, 150, 210, 270, 330, 30].map((d) => (d * Math.PI) / 180);
  const ring = ([z, yc, rx, ry]) => ANG.map((a) => [rx * Math.cos(a), yc + ry * Math.sin(a), z]);
  const R = rings.map(ring);
  // faces between ring vertices k and k+1: 0, 5 the back, 1, 4 the sides, 2, 3 the belly
  const black = C('#0a0b0e'), white = C('#e9ebe8'), blue = C('#0d1220');
  const grey = C('#8a8f9b'), greyD = C('#5f6470'), greyL = C('#a3a7b0'), neckG = C('#4f7066'), neckP = C('#6c5874');
  const bodyCol = (i, k) => {
    if (M) return (i === 1 && k >= 1 && k <= 4) || (i === 0 && (k === 2 || k === 3)) ? white : black;   // white belly, flanks
    if (i >= 3) return k % 2 ? neckG : neckP;                      // the iridescent neck
    return k === 2 || k === 3 ? greyL : grey;
  };
  for (let i = 0; i + 1 < R.length; i++) {
    for (let k = 0; k < 6; k++) {
      const k2 = (k + 1) % 6;
      quad(R[i][k], R[i][k2], R[i + 1][k2], R[i + 1][k], bodyCol(i, k));
    }
  }
  const tailRoot = [0, rings[0][1], rings[0][0] - 0.012];
  for (let k = 0; k < 6; k++) tri(R[0][(k + 1) % 6], R[0][k], tailRoot, M ? black : grey);
  // head: a ring between a pointed back and front, and the beak (they bob and peck: HEAD)
  const [hz, hy, hr] = M ? [0.118, 0.232, 0.027] : [0.092, 0.206, 0.021];
  const H = ANG.map((a) => [hr * 0.85 * Math.cos(a), hy + hr * Math.sin(a), hz]);
  const hf = [0, hy - 0.004, hz + hr * 1.05], hb = [0, hy + 0.004, hz - hr * 1.15];
  const headCol = M ? black : greyD;
  for (let k = 0; k < 6; k++) {
    const k2 = (k + 1) % 6;
    tri(H[k], H[k2], hf, headCol, HEAD);
    tri(H[k2], H[k], hb, headCol, HEAD);
  }
  // (the top of the neck ring tucks into the head)
  const bl = M ? 0.05 : 0.02, bw = M ? 0.009 : 0.005;
  const tip = [0, hy - 0.006 - (M ? 0.004 : 0), hz + hr + bl];
  const b1 = [bw, hy - 0.002, hz + hr * 0.7], b2 = [-bw, hy - 0.002, hz + hr * 0.7], b3 = [0, hy - (M ? 0.014 : 0.009), hz + hr * 0.7];
  const beak = M ? black : C('#3e3a37');
  tri(b1, b2, tip, beak, HEAD); tri(b2, b3, tip, beak, HEAD); tri(b3, b1, tip, beak, HEAD);
  // tail: a flat fan (the magpie's long, a little cocked; the pigeon's with a dark band at the end)
  if (M) {
    const t0 = [0.022, 0.152, -0.08], t1 = [0.04, 0.178, -0.33];
    quad(t0, mx(t0), mx(t1), t1, blue);
  } else {
    const t0 = [0.024, 0.124, -0.075], t1 = [0.04, 0.108, -0.15], t2 = [0.042, 0.104, -0.172];
    quad(t0, mx(t0), mx(t1), t1, grey);
    quad(t1, mx(t1), mx(t2), t2, C('#383a40'));
  }
  // legs: two crossed thin quads each, and the toes
  const legCol = M ? C('#16171a') : C('#b5524c');
  const hip = M ? 0.115 : 0.09, lw = 0.005;
  for (const s of [-1, 1]) {
    const x = s * 0.018, top = [x, hip, 0.005], foot = [x, 0.0, 0.012];
    quad([top[0] - lw, top[1], top[2]], [top[0] + lw, top[1], top[2]], [foot[0] + lw, 0, foot[2]], [foot[0] - lw, 0, foot[2]], legCol);
    quad([top[0], top[1], top[2] - lw], [top[0], top[1], top[2] + lw], [foot[0], 0, foot[2] + lw], [foot[0], 0, foot[2] - lw], legCol);
    tri([x - 0.012, 0.002, 0.04], [x + 0.012, 0.002, 0.04], [x, 0.002, 0.0], legCol);
  }
  // wings: [open, folded] for the shoulder's leading and trailing edge, the wrist, the trailing middle and the tip;
  // part = [1, shoulder x, 0] (the vertex shader swings them about the shoulder)
  const wy = M ? 0.175 : 0.152, root = M ? 0.04 : 0.034;
  const W = M
    ? { L: [[root, wy, 0.05]], T: [[root, wy - 0.004, -0.045]], Wr: [[0.19, wy, 0.045], [0.058, wy + 0.002, 0.012]],
      Mi: [[0.165, wy - 0.004, -0.095], [0.06, wy - 0.014, -0.065]], Ti: [[0.335, wy, -0.04], [0.04, wy - 0.008, -0.175]] }
    : { L: [[root, wy, 0.045]], T: [[root, wy - 0.004, -0.04]], Wr: [[0.17, wy, 0.04], [0.054, wy + 0.002, 0.01]],
      Mi: [[0.15, wy - 0.004, -0.078], [0.056, wy - 0.012, -0.06]], Ti: [[0.31, wy, -0.03], [0.036, wy - 0.01, -0.152]] };
  for (const s of [1, -1]) {
    const o = (v) => [s * v[0], v[1], v[2]];
    const pt = (k) => [o(W[k][0]), o(W[k][1] || W[k][0])];      // [open, folded]
    const L = pt('L'), T = pt('T'), Wr = pt('Wr'), Mi = pt('Mi'), Ti = pt('Ti');
    const part = [1, root, 0];
    const wtri = (a, b, c, col) => tri(a[0], b[0], c[0], col, part, [a[1], b[1], c[1]]);
    if (M) {
      // black arm, white scapulars by the back, the hand white with a black tip
      const Pw = [lerp(Wr[0], Ti[0], 0.68), lerp(Wr[1], Ti[1], 0.68)], Pm = [lerp(Mi[0], Ti[0], 0.68), lerp(Mi[1], Ti[1], 0.68)];
      wtri(L, Wr, Mi, blue);
      wtri(L, Mi, T, white);
      wtri(Wr, Pw, Pm, white);
      wtri(Wr, Pm, Mi, white);
      wtri(Pw, Ti, Pm, black);
    } else {
      wtri(L, Wr, Mi, greyL);
      wtri(L, Mi, T, grey);
      wtri(Wr, Ti, Mi, greyD);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(COL, 3));
  g.setAttribute('aFold', new THREE.Float32BufferAttribute(F, 3));
  g.setAttribute('aPart', new THREE.Float32BufferAttribute(A, 3));
  g.computeVertexNormals();
  return g;
}

// the wings and the head, from the per-instance pose: x how open the wings are (0 folded along the back), y the flap
// angle (radians, up +), z the head's forward bob, w how far the head dips (pecking)
function birdMaterial() {
  // (a weak specular: the sky's sheen on the grazing facets would turn the magpie's black grey)
  const m = new THREE.MeshPhysicalMaterial({ vertexColors: true, flatShading: true, side: THREE.DoubleSide, roughness: 0.6, specularIntensity: 0.3 });
  m.name = 'bird';
  patchShader(m, 'birdPose', (sh) => {
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
        attribute vec3 aFold; attribute vec3 aPart; attribute vec4 aPose;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        if (aPart.x > 0.5) {
          vec3 p = mix(aFold, position, aPose.x);
          float s = position.x < 0.0 ? -1.0 : 1.0;
          float d = max(abs(p.x) - aPart.y, 0.0);                 // out from the shoulder
          float a = aPose.y * (0.75 + 1.5 * d);                   // the hand swings further than the arm
          transformed = vec3(s * (aPart.y + d * cos(a)), p.y + d * sin(a), p.z);
        }
        transformed += vec3(0.0, -aPose.w, aPose.z) * aPart.z;`);
  });
  return pcss(m);
}

// soft dark patches on the ground under the birds (multiplied onto the scene, as blobs.js does for the phones' people)
function blobMesh(n) {
  const geo = new THREE.PlaneGeometry(2, 2);
  geo.rotateX(-Math.PI / 2);
  const dark = new THREE.InstancedBufferAttribute(new Float32Array(n), 1);
  dark.setUsage(THREE.DynamicDrawUsage);
  geo.setAttribute('aDark', dark);
  const mat = new THREE.ShaderMaterial({
    vertexShader: `attribute float aDark; varying vec2 vP; varying float vDark;
      void main() { vP = position.xz; vDark = aDark; gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0); }`,
    fragmentShader: `varying vec2 vP; varying float vDark;
      void main() { float r2 = dot(vP, vP); float a = vDark * exp(-r2 * 3.0) * (1.0 - smoothstep(0.7, 1.0, r2)); gl_FragColor = vec4(vec3(1.0 - a), 1.0); }`,
    transparent: true, depthWrite: false, blending: THREE.MultiplyBlending,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4,
  });
  const mesh = new THREE.InstancedMesh(geo, mat, n);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.frustumCulled = false;
  mesh.renderOrder = -1;
  mesh.name = 'bird_blobs';
  mesh.count = 0;
  return { mesh, dark };
}

// ---------------------------------------------------------------------------- the flock
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _e = new THREE.Euler(0, 0, 0, 'YXZ');
const _p = new THREE.Vector3(), _s = new THREE.Vector3(), _c = new THREE.Color();
const ease = (u) => u * u * (3 - 2 * u);
const glide = (u) => 0.5 * u + 0.5 * ease(u);      // along a flight: off at half speed, landing at half speed

export class Birds {
  // groundAt / surfaceAt (x, y): the walked ground / the top of anything (roofs) there; colliders: player.js
  // Colliders (benches, trunks, shrubs: no bird walks into them); forest: world.js Forest (the trees they fly into);
  // sunMap: bakedshadow.js SunMap (the campus's baked shade on them)
  constructor(scene, { groundAt, surfaceAt, colliders = null, forest = null, sunMap = null, mobile = false }) {
    this.groundAt = groundAt;
    this.surfaceAt = surfaceAt;
    this.colliders = colliders;
    const rnd = (this.rnd = mulberry(1997));
    this.spots = SPOTS.map(([x, y, r, kind, n]) => ({ x, y, r, kind, n: mobile ? Math.max(1, Math.round(n / 2)) : n, birds: [], threats: [], near: false }));
    this.birds = [];
    for (const sp of this.spots) {
      for (let i = 0; i < sp.n; i++) {
        const K = KINDS[sp.kind];
        const [x, y] = this._spotPoint(sp, []);
        const b = { kind: sp.kind, K, home: sp, spot: sp, x, y, h: groundAt(x, y), gh: 0, yaw: rnd() * 6.283, pitch: 0, roll: 0,
          state: 'idle', until: rnd() * 3, leg: null, peck: 0, lookTo: 0, open: 0, flap: 0, phase: rnd() * 6.283, headF: 0, headD: 0,
          step: rnd(), calmAt: 0, backAt: Infinity, fleeAt: 0, follow: null, f: null,
          scale: K.size[0] + rnd() * (K.size[1] - K.size[0]), tint: PIGEON_TINTS[Math.floor(rnd() * PIGEON_TINTS.length)] };
        b.gh = b.h;
        b.lookTo = b.yaw;
        sp.birds.push(b);
        this.birds.push(b);
      }
    }
    // trees to fly into: where their crowns are (instance matrix: ground, turn, scale; the kit's size)
    this.trees = [];
    if (forest) {
      const size = {};
      for (const it of forest.items) {
        const kit = forest.kits[it.key];
        if (!kit) continue;
        const box = (size[it.key] ||= new THREE.Box3().setFromObject(kit));
        const s = new THREE.Vector3().setFromMatrixScale(it.m4).y;
        const top = (box.max.y - box.min.y) * s;
        if (top < 4) continue;
        this.trees.push({ x: it.x, y: -it.z, g: it.m4.elements[13], top, cr: Math.min(3, ((box.max.x - box.min.x) / 2) * s) });
      }
    }
    // meshes
    this.mat = birdMaterial();
    sunMap?.patch(this.mat, 1);
    globalPatch(this.mat);
    this.mesh = {};
    for (const kind of Object.keys(KINDS)) {
      const n = this.birds.filter((b) => b.kind === kind).length;
      if (!n) continue;
      const geo = birdGeometry(kind);
      const pose = new THREE.InstancedBufferAttribute(new Float32Array(n * 4), 4);
      pose.setUsage(THREE.DynamicDrawUsage);
      geo.setAttribute('aPose', pose);
      const im = new THREE.InstancedMesh(geo, this.mat, n);
      im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      if (kind === 'pigeon') im.setColorAt(0, _c.setRGB(1, 1, 1));
      im.frustumCulled = false;
      im.receiveShadow = true;
      im.name = `birds_${kind}`;
      im.count = 0;
      im.userData.pose = pose;
      scene.add(im);
      this.mesh[kind] = im;
    }
    this.blobs = blobMesh(this.birds.length);
    scene.add(this.blobs.mesh);
    this.enabled = true;
  }

  // nothing there to walk into (a bench, a trunk, a shrub)
  _free(x, y) {
    if (!this.colliders) return true;
    const [rx, ry] = this.colliders.resolve(x, y, 0.15);
    return Math.abs(rx - x) + Math.abs(ry - y) < 0.01;
  }

  // a free point on the spot's ground, CALM_R from everybody in `threats` ([x, y] pairs) if it can be
  _spotPoint(sp, threats) {
    let best = [sp.x, sp.y], bestD = -1;
    for (let k = 0; k < 10; k++) {
      const a = this.rnd() * 6.283, r = sp.r * Math.sqrt(this.rnd());
      const x = sp.x + Math.cos(a) * r, y = sp.y + Math.sin(a) * r;
      if (!this._free(x, y)) continue;
      let d = 1e9;
      for (const t of threats) d = Math.min(d, Math.hypot(t[0] - x, t[1] - y));
      if (d >= CALM_R) return [x, y];
      if (d > bestD) { bestD = d; best = [x, y]; }
    }
    return best;
  }

  _threatsNear(x, y, r, player, people, out) {
    out.length = 0;
    const r2 = r * r;
    if ((player.x - x) ** 2 + (player.y - y) ** 2 < r2) out.push([player.x, player.y]);
    for (const p of people) if ((p.x - x) ** 2 + (p.y - y) ** 2 < r2) out.push([p.x, p.y]);
    return out;
  }

  // where a bird scared from (b.x, b.y) away along (ax, ay) goes: another lawn, a roof, a tree, or the far side of
  // its own spot. {x, y, h, spot, perch}
  _destination(b, ax, ay) {
    const rnd = this.rnd, K = b.K;
    const pick = rnd();
    if (pick < K.perch.roof) {
      for (let k = 0; k < 7; k++) {
        const a = Math.atan2(ay, ax) + (rnd() - 0.5) * 2.4, d = 16 + rnd() * 24;
        const x = b.x + Math.cos(a) * d, y = b.y + Math.sin(a) * d;
        const s = this.surfaceAt(x, y), g = this.groundAt(x, y);
        if (s - g > 3.5 && s - g < 26) return { x, y, h: s, spot: null, perch: 'roof' };
      }
    } else if (pick < K.perch.roof + K.perch.tree && this.trees.length) {
      const c = [];
      for (const t of this.trees) {
        const dx = t.x - b.x, dy = t.y - b.y, d = Math.hypot(dx, dy);
        if (d > 12 && d < 45 && dx * ax + dy * ay > -0.2 * d) c.push(t);
      }
      if (c.length) {
        const t = c[Math.floor(rnd() * c.length)], a = rnd() * 6.283;
        const x = t.x + Math.cos(a) * t.cr * 0.35, y = t.y + Math.sin(a) * t.cr * 0.35;
        return { x, y, h: t.g + t.top * (0.55 + rnd() * 0.15), spot: null, perch: 'tree' };
      }
    }
    // another lawn or square away from the trouble, else the far side of this one
    const c = [];
    for (const sp of this.spots) {
      if (sp === b.spot || sp.kind !== b.kind && rnd() < 0.5) continue;
      const dx = sp.x - b.x, dy = sp.y - b.y, d = Math.hypot(dx, dy);
      if (d > 14 && d < 70 && dx * ax + dy * ay > -0.3 * d) c.push(sp);
    }
    const sp = c.length ? c[Math.floor(rnd() * c.length)] : b.spot;
    const [x, y] = this._spotPoint(sp, sp.threats);
    return { x, y, h: this.groundAt(x, y), spot: sp, perch: null };
  }

  _takeOff(b, dest, t) {
    const dx = dest.x - b.x, dy = dest.y - b.y, d = Math.hypot(dx, dy);
    const T = 0.8 + d / b.K.fly + Math.max(0, dest.h - b.h) / 4;
    // high enough over what lies on the way (roofs, walls; trees aside) and a little over the straight line
    const h0 = b.h, h1 = dest.h;
    const base = (u) => h0 + (h1 - h0) * (h1 > h0 ? 1 - (1 - u) * (1 - u) : u * u);
    let A = 1.0 + 0.07 * d;
    for (let k = 1; k < 7; k++) {
      const u = k / 7, s = glide(u);
      const top = this.surfaceAt(b.x + dx * s, b.y + dy * s);
      if (top > -1e8) A = Math.max(A, (top + 1.5 - base(u)) / (4 * u * (1 - u)));
    }
    // (the ground patch stays under it near either end; none in a tree's crown)
    b.f = { x0: b.x, y0: b.y, g0: b.gh, x1: dest.x, y1: dest.y, g1: dest.perch === 'tree' ? -1e9 : h1, T, A: Math.min(A, 30), t0: t, base, dest };
    b.state = 'fly';
    b.leg = null;
    b.fleeAt = 0;
    b.follow = null;
    b.phase = 0;
    b.spot?.birds.splice(b.spot.birds.indexOf(b), 1);
    b.spot = null;
  }

  _land(b, t) {
    const { dest } = b.f;
    b.x = dest.x; b.y = dest.y; b.h = dest.h;
    b.gh = b.f.g1;
    b.f = null;
    b.lookTo = b.yaw;
    b.calmAt = t + 0.8;
    if (dest.perch) {
      b.state = 'perch';
      b.until = t + 1 + this.rnd() * 3;
      b.backAt = t + 14 + this.rnd() * 26;
    } else {
      b.spot = dest.spot;
      dest.spot.birds.push(b);
      b.state = 'idle';
      b.until = t + 0.6 + this.rnd() * 1.5;
      b.backAt = dest.spot === b.home ? Infinity : t + 25 + this.rnd() * 35;
    }
  }

  // scared by (tx, ty): up and away, the spot's other birds close by after it
  _flee(b, tx, ty, t, dest = null) {
    let ax = b.x - tx, ay = b.y - ty;
    const l = Math.hypot(ax, ay) || 1;
    ax /= l; ay /= l;
    const sp = b.spot;
    dest ||= this._destination(b, ax, ay);
    this._takeOff(b, dest, t);
    if (!sp) return;
    for (const o of sp.birds) {
      if (o.fleeAt || o.state === 'fly' || Math.hypot(o.x - b.x, o.y - b.y) > 9) continue;
      o.fleeAt = t + 0.1 + this.rnd() * 0.55;
      o.follow = { tx, ty, dest };
    }
  }

  // follow the leader to its destination, a metre or two to the side
  _near(dest) {
    const a = this.rnd() * 6.283, r = 0.6 + this.rnd() * 1.4;
    const x = dest.x + Math.cos(a) * r, y = dest.y + Math.sin(a) * r;
    if (dest.perch === 'roof') {
      const s = this.surfaceAt(x, y);
      return Math.abs(s - dest.h) < 1.5 ? { ...dest, x, y, h: s } : dest;
    }
    if (dest.perch === 'tree') return { ...dest, x, y, h: dest.h + (this.rnd() - 0.5) * 1.5 };
    return { ...dest, x, y, h: this.groundAt(x, y) };
  }

  // a new thing to do on the ground: walk a little, peck, look round
  _next(b, t) {
    const r = this.rnd();
    b.headF = 0;
    if (b.state === 'perch') { b.until = t + 1.5 + r * 4; b.lookTo = b.yaw + (this.rnd() - 0.5) * 1.6; return; }
    if (r < 0.45) {
      const sp = b.spot;
      let [x, y] = this._spotPoint(sp, sp.threats);
      const dx = x - b.x, dy = y - b.y, d = Math.hypot(dx, dy);
      let go = Math.min(d, 0.8 + this.rnd() * 2);
      if (d > 0.01) { x = b.x + (dx / d) * go; y = b.y + (dy / d) * go; }
      if (!this._free(x, y) || !this._free((x + b.x) / 2, (y + b.y) / 2)) { x = b.x; y = b.y; go = 0; }
      const hop = b.kind === 'magpie' && this.rnd() < 0.3;
      b.leg = { x0: b.x, y0: b.y, h0: b.h, x1: x, y1: y, h1: this.groundAt(x, y), s: 0, d: go, hop };
      b.state = 'walk';
    } else if (r < 0.8) {
      b.state = 'peck';
      b.peck = 0;
      b.until = t + (2 + Math.floor(this.rnd() * 4)) * 0.42;
    } else {
      b.state = 'idle';
      b.lookTo = b.yaw + (this.rnd() - 0.5) * 1.4;
      b.until = t + 0.8 + this.rnd() * 2.2;
    }
  }

  update(dt, t, player, people, focus) {
    if (!this.enabled) return;
    const fx = focus.x, fy = -focus.z;
    for (const sp of this.spots) {
      sp.near = (sp.x - fx) ** 2 + (sp.y - fy) ** 2 < SIM_R * SIM_R;
      if (sp.near) this._threatsNear(sp.x, sp.y, sp.r + FLEE_R + 3, player, people, sp.threats);
      else sp.threats.length = 0;
    }
    for (const b of this.birds) {
      const near = b.state === 'fly' || (b.x - fx) ** 2 + (b.y - fy) ** 2 < SIM_R * SIM_R;
      if (near) this._step(b, dt, t, player, people);
    }
    this._draw(focus);
  }

  _step(b, dt, t, player, people) {
    const K = b.K;
    let pitch = 0, roll = 0, open = 0, flap = 0, headF = 0, headD = 0;
    // on the ground: anybody too close?
    if (b.spot && t > b.calmAt) {
      if (b.fleeAt && t >= b.fleeAt) {
        const { tx, ty, dest } = b.follow;
        this._flee(b, tx, ty, t, this._near(dest));
      } else if (!b.fleeAt) {
        for (const th of b.spot.threats) {
          if ((th[0] - b.x) ** 2 + (th[1] - b.y) ** 2 < FLEE_R * FLEE_R) { this._flee(b, th[0], th[1], t); break; }
        }
      }
    }
    // away from home long enough: back, when nobody is about there
    if ((b.state === 'perch' || (b.spot && b.spot !== b.home && b.state !== 'fly')) && t > b.backAt) {
      const sp = b.home;
      this._threatsNear(sp.x, sp.y, sp.r + CALM_R + 2, player, people, sp.threats);
      if (sp.threats.length) b.backAt = t + 5;
      else {
        const [x, y] = this._spotPoint(sp, sp.threats);
        b.spot?.birds.splice(b.spot.birds.indexOf(b), 1);
        b.spot = null;
        this._takeOff(b, { x, y, h: this.groundAt(x, y), spot: sp, perch: null }, t);
      }
    }
    if (b.state === 'fly') {
      const f = b.f, u = Math.min(1, (t - f.t0) / f.T), s = glide(u);
      const x = f.x0 + (f.x1 - f.x0) * s, y = f.y0 + (f.y1 - f.y0) * s;
      const h = f.base(u) + f.A * 4 * u * (1 - u);
      const vx = x - b.x, vy = y - b.y, vh = h - b.h, vxy = Math.hypot(vx, vy);
      if (vxy > 1e-4) {
        const want = Math.atan2(vx, -vy), turn = wrapAngle(want - b.yaw);
        b.yaw += turn * Math.min(1, dt * 10);
        roll = Math.max(-0.6, Math.min(0.6, -turn * 2));
      }
      b.x = x; b.y = y; b.h = h;
      b.gh = Math.hypot(x - f.x0, y - f.y0) < 1.5 ? f.g0 : Math.hypot(x - f.x1, y - f.y1) < 1.5 ? f.g1 : -1e9;
      // wings: hard strokes going up, steadier on the way (the magpie flaps and glides), spread and braking at the end
      b.phase += dt * K.hz * (u > 0.8 ? 0.8 : 1) * 6.283;
      let amp = u < 0.3 ? 1.0 : 0.7;
      if (b.kind === 'magpie' && u > 0.3 && u < 0.78 && Math.sin(t * 2.2 + b.scale * 40) > 0.35) amp = 0;   // glide
      open = b.open = Math.min(1, (t - f.t0) / 0.12);
      flap = amp ? amp * Math.sin(b.phase) + 0.15 : 0.18;
      pitch = Math.max(-0.7, Math.min(0.5, -Math.atan2(vh, vxy + 1e-3) * 0.6));
      if (u > 0.82) pitch -= (u - 0.82) / 0.18 * 0.55;                 // flare to land
      if (u >= 1) this._land(b, t);
    } else {
      b.open = Math.max(0, b.open - dt / 0.3);
      open = b.open;
      flap = open * 0.9;
      if (t > b.until && b.state !== 'walk') this._next(b, t);
      if (b.state === 'walk') {
        const L = b.leg;
        const want = Math.atan2(L.x1 - L.x0, -(L.y1 - L.y0)), turn = L.d > 0 ? wrapAngle(want - b.yaw) : 0;
        b.yaw += turn * Math.min(1, dt * 8);
        if (Math.abs(turn) < 0.6 && L.d > 0) {
          const v = L.hop ? K.walk * 1.8 : K.walk;
          L.s = Math.min(1, L.s + (v * dt) / L.d);
          b.step += dt * (L.hop ? 2.4 : b.kind === 'pigeon' ? 2.8 : 2.2);
        }
        b.x = L.x0 + (L.x1 - L.x0) * L.s;
        b.y = L.y0 + (L.y1 - L.y0) * L.s;
        b.h = b.gh = L.h0 + (L.h1 - L.h0) * L.s;
        const ph = b.step % 1;
        if (b.kind === 'pigeon') headF = 0.022 * (ph < 0.3 ? ph / 0.3 : 1 - (ph - 0.3) / 0.7) - 0.008;   // the head bob
        else b.h += L.hop ? 0.05 * Math.abs(Math.sin(ph * Math.PI)) : 0.006 * Math.abs(Math.sin(ph * 2 * Math.PI));
        if (L.s >= 1 || L.d <= 0) { b.state = 'idle'; b.until = t + 0.2 + this.rnd() * 0.8; b.lookTo = b.yaw; }
      } else if (b.state === 'peck') {
        b.peck += dt / 0.42;
        const p = b.peck % 1;
        const k = p < 0.3 ? ease(p / 0.3) : p < 0.45 ? 1 : 1 - ease((p - 0.45) / 0.55);
        pitch = K.peck * k;
        headD = 0.025 * k;
      } else {
        b.yaw += wrapAngle(b.lookTo - b.yaw) * Math.min(1, dt * 7);    // looking round
      }
    }
    b.pitch += (pitch - b.pitch) * Math.min(1, dt * 14);
    b.roll += (roll - b.roll) * Math.min(1, dt * 6);
    b.flap = flap;
    b.headF = headF;
    b.headD = headD;
  }

  _draw(focus) {
    const fx = focus.x, fz = focus.z;
    const count = { pigeon: 0, magpie: 0 };
    let nb = 0;
    const blob = this.blobs;
    for (const b of this.birds) {
      const d2 = (b.x - fx) ** 2 + (b.y + fz) ** 2;
      if (d2 > DRAW_R * DRAW_R) continue;
      const im = this.mesh[b.kind], i = count[b.kind]++;
      _e.set(b.pitch, b.yaw, b.roll);
      _q.setFromEuler(_e);
      _m.compose(_p.set(b.x, b.h, -b.y), _q, _s.setScalar(b.scale));
      im.setMatrixAt(i, _m);
      im.userData.pose.setXYZW(i, b.open, b.flap, b.headF, b.headD);
      if (im.instanceColor) im.setColorAt(i, _c.setRGB(b.tint[0], b.tint[1], b.tint[2]));
      // its patch on the ground, fading as it rises
      const up = b.h - b.gh;
      if (d2 < BLOB_R * BLOB_R && up < 2.5) {
        const r = (b.kind === 'magpie' ? 0.15 : 0.13) * b.scale * (1 + up * 0.6);
        _m.makeScale(r, 1, r).setPosition(b.x, b.gh + 0.02, -b.y);
        blob.mesh.setMatrixAt(nb, _m);
        blob.dark.setX(nb, 0.4 * Math.exp(-up * 1.6));
        nb++;
      }
    }
    for (const kind in this.mesh) {
      const im = this.mesh[kind];
      im.count = count[kind];
      im.instanceMatrix.needsUpdate = true;
      im.userData.pose.needsUpdate = true;
      if (im.instanceColor) im.instanceColor.needsUpdate = true;
    }
    blob.mesh.count = nb;
    blob.mesh.instanceMatrix.needsUpdate = true;
    blob.dark.needsUpdate = true;
  }
}
