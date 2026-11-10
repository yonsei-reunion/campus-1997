// Curbs (경계석) where the painted asphalt and paving meet the lawn. tools/build_campus.py traces the edges of the
// paving in the ground map (campus.json curbs: [kind, x0, y0, dx1, dy1, ...] in cm, the lawn on the left going along:
// kind 'p' by the paving, 'a' by the asphalt of the drives and car parks; 'k' between a drive or a car park and the
// paving beside it, the paving on the left; none along 백양로, whose own road mesh has its kerbs, nor along the walls
// of the halls or in the woods). Each run gets a low granite kerb standing on the lawn (or the paving) side over the
// edge, so the cut between the two ground textures (terrain.js) lies under its face to the lower side:
//  - by the paving 15 cm wide and 15 cm high, by the asphalt 18 cm wide (the 상뜰's kerbs in
//    reference/대우관_2024_정면과_상뜰.jpg, the drives' and the 백양로 islands' in the 2008 / 2011 roadview); between
//    asphalt and paving 15 cm wide, 14 cm over the asphalt, the paving behind it raised to 2 cm under its top
//  - the top arris on the paving side rounded, a joint every metre and each stone a shade lighter or darker
//    (the shared 'curb' material of 백양로's kerbs, with the joints and the tones as a shader edit)
// The kerbs are built in CELL m squares as the camera comes within reach, on the terrain as it is drawn (each 5 m
// cell's two triangles, terrain.js gridGeometry); where a flight, a terrace or the road stands over the ground the
// kerb is left out. Every built square within reach is drawn as one mesh (one draw call), merged again when that set
// changes; phones reach less far.
// The lawn behind the kerbs stands nearly level with their tops (issue #86: the 2008 - 2011 roadview, the 2024 photo
// of the 상뜰), not at the paving's level as the 5 m grid has it: along each kerb a strip of ground in the terrain's own
// material (terrain.js groundLipCut) rises LIP over the ground at the kerb's lawn face. On a lawn wider than about 2 m
// it eases back down to the ground 1.6 m out; a narrower strip (campus.json curb_lawn: how far the lawn reaches behind
// each kerb) is raised from kerb to kerb, the two edges meeting level. Behind a 'k' kerb the paving is raised the same
// way (aPave: terrain.js groundLipCut keeps the paving there, not the lawn). Built and drawn with the kerbs (one more
// draw call); lift() gives its height for the walker and the grass blades standing on it.
import * as THREE from 'three';
import { MOBILE } from './util.js';
import { derivedCopy, patchShader } from './materials.js';
import { groundLipCut } from './terrain.js';

const CELL = 64;
const FAR = MOBILE ? 80 : 140;       // reach from the camera, m
const STEP = 6;                      // look again after the camera has moved this far
const PIECE = 1.0;                   // stone length, m
const SUB = 2.5;                     // longest straight stretch between two sections (half a terrain cell)
const KINDS = [{ w: 0.15, h: 0.15 }, { w: 0.18, h: 0.15 }, { w: 0.15, h: 0.14 }];      // 'p', 'a', 'k'
const LAP = 0.04;                    // how far the stone reaches over the edge onto the paving
const ARRIS = 0.025;                 // radius of the rounded top edge on the paving side
const SINK = 0.1;                    // how far the faces go down into the ground
const FLOATS = 8;                    // position 3, normal 3, uv 2
const LIP = 0.12;                    // the lawn's edge over the ground at the kerb (3 cm under the kerb's top)
const LIP_O = [0.0, 0.5, 1.0, 1.6];  // a wide lawn's edge: out from the kerb's face (m) ...
const LIP_Z = [1.0, 0.95, 0.5, -0.25];      // ... and its height there, a share of LIP (sunk under the ground at the end)
const LIP_FLOATS = 7;                // position 3, normal 3, aPave 1 (the paving's edge behind a 'k' kerb)
const LAWN_STEP = 2.0;               // campus.json curb_lawn: a value every this many metres along the run (dm)
const BIN = 4;                       // lift(): the kerbs near a point, by squares of this size

// the visible terrain's height: the 5 m grid's cells split along (i+1, j)-(i, j+1) as terrain.js draws them
function terrainHeight(hf, x, y) {
  const { half, step, n, data } = hf;
  const fx = Math.min(Math.max((x + half) / step, 0), n - 1.001), fy = Math.min(Math.max((y + half) / step, 0), n - 1.001);
  const i = fx | 0, j = fy | 0, ax = fx - i, ay = fy - j;
  const a = data[j * n + i], b = data[j * n + i + 1], c = data[(j + 1) * n + i], d = data[(j + 1) * n + i + 1];
  return ax + ay <= 1 ? a + (b - a) * ax + (c - a) * ay : d + (c - d) * (1 - ax) + (b - d) * (1 - ay);
}

// the terrain's shading normal there (campus east, north, up; not unit): its vertices' normals (central differences,
// close to computeVertexNormals) blended across the cell, so the lawn's edge is lit as the lawn beside it
function terrainNormal(hf, x, y, out) {
  const { half, step, n, data } = hf;
  const fx = Math.min(Math.max((x + half) / step, 1), n - 2.001), fy = Math.min(Math.max((y + half) / step, 1), n - 2.001);
  const i = fx | 0, j = fy | 0, ax = fx - i, ay = fy - j;
  out[0] = out[1] = 0;
  for (const [di, dj, w] of [[0, 0, (1 - ax) * (1 - ay)], [1, 0, ax * (1 - ay)], [0, 1, (1 - ax) * ay], [1, 1, ax * ay]]) {
    const k = (j + dj) * n + i + di;
    out[0] -= w * (data[k + 1] - data[k - 1]) / (2 * step);
    out[1] -= w * (data[k + n] - data[k - n]) / (2 * step);
  }
  out[2] = 1;
  return out;
}

const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
// the lawn's edge across, from the kerb's lawn face: offsets o and heights z over the ground for `room` m of lawn to
// the next kerb's face (narrow: level all the way; wide: easing down as LIP_O / LIP_Z)
function lipProfile(room, o, z) {
  const k = smooth(1.2, 2.2, room);
  for (let i = 0; i < 4; i++) {
    const on = (room + 0.03) * i / 3;
    o[i] = on + (LIP_O[i] - on) * k;
    z[i] = LIP * (1 + (LIP_Z[i] - 1) * k);
  }
}
const _po = new Float32Array(4), _pz = new Float32Array(4);
function lipAt(room, d) {
  if (room < 0.1) return 0;
  lipProfile(room, _po, _pz);
  if (d < -0.02 || d > _po[3]) return 0;
  for (let i = 1; i < 4; i++) {
    if (d <= _po[i]) return Math.max(0, _pz[i - 1] + (_pz[i] - _pz[i - 1]) * Math.max(0, d - _po[i - 1]) / Math.max(1e-4, _po[i] - _po[i - 1]));
  }
  return 0;
}

// the joints and the stones' tones (aAlong: metres along the run, offset per run)
function curbEdit(sh) {
  sh.vertexShader = sh.vertexShader
    .replace('#include <common>', '#include <common>\nattribute float aAlong;\nvarying float vAlong;')
    .replace('#include <uv_vertex>', '#include <uv_vertex>\nvAlong = aAlong;');
  sh.fragmentShader = sh.fragmentShader
    .replace('#include <common>', '#include <common>\nvarying float vAlong;')
    .replace('#include <map_fragment>', `#include <map_fragment>
      {
        float pc = vAlong / ${PIECE.toFixed(2)};
        float dj = (0.5 - abs(fract(pc) - 0.5)) * ${PIECE.toFixed(2)};          // metres to the nearest joint
        float jw = fwidth(vAlong);
        float joint = (1.0 - smoothstep(0.003, 0.003 + jw * 1.2, dj)) * (1.0 - smoothstep(0.02, 0.08, jw));
        float id = floor(pc);
        float tone = 0.92 + 0.13 * fract(sin(id * 12.9898) * 43758.5453);
        diffuseColor.rgb *= tone * (1.0 - 0.5 * joint);
      }`);
}

export class Curbs {
  // list: campus.json curbs; hf: the near terrain heightfield; over: the walked meshes other than the terrain (the
  // road, the flights, the terraces: no kerb under them); lib: the material library; lawn: campus.json curb_lawn;
  // ground: the near terrain's material (the lawn's raised edge; none without it)
  constructor(scene, list, hf, over, lib, { lawn = [], ground = null } = {}) {
    this.hf = hf;
    this.over = over;
    this.ray = new THREE.Raycaster();
    this.ray.firstHitOnly = true;
    // every run's points, subdivided to SUB m, in flat arrays; segments by cell; D: the lawn behind the kerb there, m
    const X = [], Y = [], U = [], MX = [], MY = [], K = [], D = [];
    let ri = -1;
    this.cells = new Map();                 // key -> {segs: start indices, data: Float32Array | null}
    const seg = (i) => {
      const key = this._key((X[i] + X[i + 1]) / 2, (Y[i] + Y[i + 1]) / 2);
      let c = this.cells.get(key);
      if (!c) this.cells.set(key, (c = { segs: [], data: null }));
      c.segs.push(i);
    };
    let seed = 1;
    for (const r of list) {
      const lw = lawn[++ri];
      const kind = r[0] === 'a' ? 1 : r[0] === 'k' ? 2 : 0;
      const P = [];
      let x = 0, y = 0;
      for (let k = 1; k < r.length; k += 2) { x += r[k]; y += r[k + 1]; P.push([x / 100, y / 100]); }
      const closed = P.length > 3 && Math.hypot(P[0][0] - P.at(-1)[0], P[0][1] - P.at(-1)[1]) < 0.01;
      if (closed) P.pop();
      const m = P.length;
      if (m < 2) continue;
      // the left normal of each segment, and the mitred one at each point (its length: the offset there per metre)
      const nrm = [];
      for (let k = 0; k < (closed ? m : m - 1); k++) {
        const a = P[k], b = P[(k + 1) % m], L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
        nrm.push([-(b[1] - a[1]) / L, (b[0] - a[0]) / L]);
      }
      const miter = (k) => {
        const n0 = nrm[closed ? (k - 1 + m) % m : Math.max(0, k - 1)], n1 = nrm[closed ? k % m : Math.min(nrm.length - 1, k)];
        let mx = n0[0] + n1[0], my = n0[1] + n1[1];
        const l = Math.hypot(mx, my);
        if (l < 1e-6) return n1;
        mx /= l; my /= l;
        const s = 1 / Math.max(0.5, mx * n1[0] + my * n1[1]);       // (at most twice as long in a sharp corner)
        return [mx * s, my * s];
      };
      let u = (seed = (seed * 16807) % 2147483647) % 1000 / 1000 * PIECE;
      const u0 = u;
      const depth = (uu) => {
        if (!lw?.length) return 3;
        const f = Math.min(Math.max((uu - u0) / LAWN_STEP, 0), lw.length - 1), k0 = Math.min(f | 0, lw.length - 2);
        return lw.length < 2 ? lw[0] / 10 : (lw[k0] + (lw[k0 + 1] - lw[k0]) * (f - k0)) / 10;
      };
      const first = X.length;
      for (let k = 0; k < (closed ? m + 1 : m); k++) {
        const a = P[k % m], ma = miter(k % m);
        if (k > 0) {
          const b = P[k - 1];
          const L = Math.hypot(a[0] - b[0], a[1] - b[1]), nsub = Math.max(1, Math.ceil(L / SUB));
          const sn = nrm[(k - 1) % nrm.length];                  // (straight between the points: its own normal)
          for (let t = 1; t < nsub; t++) {
            const f = t / nsub;
            X.push(b[0] + (a[0] - b[0]) * f); Y.push(b[1] + (a[1] - b[1]) * f);
            MX.push(sn[0]); MY.push(sn[1]); U.push(u + L * f); K.push(kind); D.push(depth(u + L * f));
          }
          u += L;
        }
        X.push(a[0]); Y.push(a[1]); MX.push(ma[0]); MY.push(ma[1]); U.push(u); K.push(kind); D.push(depth(u));
      }
      for (let i = first; i < X.length - 1; i++) seg(i);       // (none from a run's last point to the next run)
    }
    const f32 = (a) => Float32Array.from(a);
    Object.assign(this, { X: f32(X), Y: f32(Y), U: f32(U), MX: f32(MX), MY: f32(MY), K: Uint8Array.from(K), D: f32(D) });
    this.state = new Uint8Array(X.length);            // 0 not looked at, 1 on the ground, 2 under something
    this.lipOk = new Uint8Array(X.length);            // the lawn behind it may be raised (once looked at)
    this.g0 = new Float32Array(X.length);             // ground under the paving side, the lawn side
    this.g1 = new Float32Array(X.length);
    for (const c of this.cells.values()) c.segs = Int32Array.from(c.segs);

    const mat = derivedCopy(lib.get('curb'));
    mat.side = THREE.FrontSide;
    mat.color.setRGB(1.7, 1.7, 1.68);           // pale granite, lighter than the paving (the 상뜰's kerbs in the photo)
    mat.name = 'curb_stone';
    patchShader(mat, 'curbJoint', curbEdit);
    this.cap = 0;
    this.geo = new THREE.BufferGeometry();
    this.mesh = new THREE.Mesh(this.geo, mat);
    this.mesh.name = 'curbs';
    this.mesh.frustumCulled = false;
    this.mesh.receiveShadow = true;
    this.mesh.castShadow = false;
    this.mesh.visible = false;
    scene.add(this.mesh);
    // the lawn's raised edge: drawn before the terrain (whose pixels under it are then skipped), no shadow of its own
    this.lipMesh = null;
    if (ground) {
      const gm = derivedCopy(ground);
      gm.name = 'curb_lawn';
      patchShader(gm, 'groundLipCut', groundLipCut);
      this.lipCap = 0;
      this.lipGeo = new THREE.BufferGeometry();
      this.lipMesh = new THREE.Mesh(this.lipGeo, gm);
      Object.assign(this.lipMesh, { name: 'curb_lawn', frustumCulled: false, receiveShadow: true, castShadow: false, visible: false, renderOrder: -1 });
      // (into the scene at the first update: its material replays the terrain's edits, the baked sun shadow's
      // among them, so the pass that gives every material in the scene that shadow must not find it)
      this.scene = scene;
    }
    this.bins = new Map();
    this.last = new THREE.Vector3(1e9, 0, 0);
    this.shown = '';
    this.queue = [];
  }

  _key(x, y) { return `${Math.floor(x / CELL)},${Math.floor(y / CELL)}`; }

  // ground at point i (both sides of the stone), or under a flight / terrace / the road
  _look(i) {
    if (this.state[i]) return this.state[i] === 1;
    const x = this.X[i], y = this.Y[i], mx = this.MX[i], my = this.MY[i], { w } = KINDS[this.K[i]];
    const s0 = -LAP, s1 = w - LAP;
    this.g0[i] = terrainHeight(this.hf, x + mx * s0, y + my * s0);
    this.g1[i] = terrainHeight(this.hf, x + mx * s1, y + my * s1);
    let ok = true;
    if (this.over.length) {
      this.ray.set(_o.set(x + mx * (s0 + s1) / 2, 600, -(y + my * (s0 + s1) / 2)), _down);
      const h = this.ray.intersectObjects(this.over, false);
      if (h.length && h[0].point.y > Math.min(this.g0[i], this.g1[i]) - 0.3) ok = false;
    }
    // the lawn's raised edge only where nothing walked on lies on the lawn just behind the stone (상뜰's round lawn is
    // a dome of its own, blender/landmarks.py)
    if (ok && this.lipMesh && this.over.length) {
      const lx = x + mx * (s1 + 0.4), ly = y + my * (s1 + 0.4);
      this.ray.set(_o.set(lx, 600, -ly), _down);
      const h = this.ray.intersectObjects(this.over, false);
      this.lipOk[i] = h.length && h[0].point.y > terrainHeight(this.hf, lx, ly) - 0.3 ? 0 : 1;
    } else this.lipOk[i] = ok ? 1 : 0;
    this.state[i] = ok ? 1 : 2;
    return ok;
  }

  // the stones of one cell: 5 faces (paving face, two facets of the rounded arris, top, lawn face) per segment
  _build(c) {
    const out = new Float32Array(c.segs.length * 20 * FLOATS);
    let n = 0;
    const put = (x, z, y, nx, ny, nz, u, v) => {
      out[n++] = x; out[n++] = z; out[n++] = -y; out[n++] = nx; out[n++] = nz; out[n++] = -ny; out[n++] = u; out[n++] = v;
    };
    const R2 = Math.SQRT1_2;
    for (const i of c.segs) {
      if (!this._look(i) || !this._look(i + 1)) continue;
      for (const j of [i, i + 1]) {
        const x = this.X[j], y = this.Y[j], mx = this.MX[j], my = this.MY[j], u = this.U[j];
        const { w, h } = KINDS[this.K[j]];
        const ml = Math.hypot(mx, my), nx = mx / ml, ny = my / ml;    // the lawn side, unit
        const s0 = -LAP, s1 = w - LAP, g0 = this.g0[j], g1 = this.g1[j];
        const top = (g0 + g1) / 2 + h;
        const P = (s) => [x + mx * s, y + my * s];
        const [ax, ay] = P(s0), [bx, by] = P(s0 + ARRIS * 0.3), [cx, cy] = P(s0 + ARRIS), [dx, dy] = P(s1);
        put(ax, g0 - SINK, ay, -nx, -ny, 0, u, 0);                              // paving face
        put(ax, top - ARRIS, ay, -nx, -ny, 0, u, h + SINK - ARRIS);
        put(ax, top - ARRIS, ay, -nx, -ny, 0, u, 0);                            // arris, lower facet
        put(bx, top - ARRIS * 0.3, by, -nx * R2, -ny * R2, R2, u, ARRIS);
        put(bx, top - ARRIS * 0.3, by, -nx * R2, -ny * R2, R2, u, 0);           // arris, upper facet
        put(cx, top, cy, 0, 0, 1, u, ARRIS);
        put(cx, top, cy, 0, 0, 1, u, 0);                                        // top
        put(dx, top, dy, 0, 0, 1, u, w - ARRIS);
        put(dx, top, dy, nx, ny, 0, u, 0);                                      // lawn face
        put(dx, g1 - SINK, dy, nx, ny, 0, u, h + SINK);
      }
    }
    return out.subarray(0, n);
  }

  // the lawn's raised edge along the stones of one cell: 4 points across at each section, 3 quads a segment
  _buildLip(c) {
    const out = new Float32Array(c.segs.length * 8 * LIP_FLOATS);
    let n = 0;
    const o = new Float32Array(4), z = new Float32Array(4), tn = [0, 0, 1];
    for (const i of c.segs) {
      if (!this._look(i) || !this._look(i + 1) || !this.lipOk[i] || !this.lipOk[i + 1]) continue;
      const room = (j) => this.D[j] - 2 * (KINDS[this.K[j]].w - LAP);      // to the next paving's kerb, m
      if (room(i) < 0.1 && room(i + 1) < 0.1) continue;
      for (const j of [i, i + 1]) {
        const x = this.X[j], y = this.Y[j], mx = this.MX[j], my = this.MY[j], s1 = KINDS[this.K[j]].w - LAP;
        const ml = Math.hypot(mx, my), ux = mx / ml, uy = my / ml;
        lipProfile(Math.max(0.1, room(j)), o, z);
        for (let k = 0; k < 4; k++) {
          const px = x + mx * (s1 + o[k]), py = y + my * (s1 + o[k]);
          const k0 = Math.max(0, k - 1), k1 = Math.min(3, k + 1);
          const slope = (z[k1] - z[k0]) / Math.max(1e-3, (o[k1] - o[k0]) * ml);
          terrainNormal(this.hf, px, py, tn);
          let nx = tn[0] - slope * ux, ny = tn[1] - slope * uy;
          const nl = Math.hypot(nx, ny, 1);
          nx /= nl; ny /= nl;
          out[n++] = px; out[n++] = terrainHeight(this.hf, px, py) + z[k]; out[n++] = -py;
          out[n++] = nx; out[n++] = 1 / nl; out[n++] = -ny;
          out[n++] = this.K[j] === 2 ? 1 : 0;
        }
      }
    }
    return out.subarray(0, n);
  }

  // the raised lawn's height over the ground at campus (x, y) (0 off it): for the walker and the grass blades
  lift(x, y) {
    if (!this.lipMesh) return 0;
    const bi = Math.floor(x / BIN), bj = Math.floor(y / BIN), key = bi * 65536 + bj;
    let segs = this.bins.get(key);
    if (!segs) {
      if (this.bins.size > 30000) this.bins.clear();
      this.bins.set(key, (segs = this._binSegs(bi, bj)));
    }
    let best = 0;
    for (const i of segs) {
      const ax = this.X[i], ay = this.Y[i], dx = this.X[i + 1] - ax, dy = this.Y[i + 1] - ay, L2 = dx * dx + dy * dy;
      if (L2 < 1e-6) continue;
      const t = ((x - ax) * dx + (y - ay) * dy) / L2;
      if (t < -0.05 || t > 1.05) continue;
      const L = Math.sqrt(L2), d = ((x - ax) * -dy + (y - ay) * dx) / L;    // out on the lawn side (the left)
      const tc = Math.min(1, Math.max(0, t)), s1 = KINDS[this.K[i]].w - LAP;
      const z = lipAt(this.D[i] + (this.D[i + 1] - this.D[i]) * tc - 2 * s1, d - s1);
      if (z > best && this._look(i) && this._look(i + 1) && this.lipOk[i] && this.lipOk[i + 1]) best = z;
    }
    return best;
  }

  // the segments whose raised lawn may reach into the square (bi, bj)
  _binSegs(bi, bj) {
    const x0 = bi * BIN - 2.5, x1 = (bi + 1) * BIN + 2.5, y0 = bj * BIN - 2.5, y1 = (bj + 1) * BIN + 2.5;
    const out = [];
    for (let ci = Math.floor((x0 - SUB) / CELL); ci <= Math.floor((x1 + SUB) / CELL); ci++) {
      for (let cj = Math.floor((y0 - SUB) / CELL); cj <= Math.floor((y1 + SUB) / CELL); cj++) {
        const c = this.cells.get(`${ci},${cj}`);
        if (!c) continue;
        for (const i of c.segs) {
          const ax = this.X[i], ay = this.Y[i], bx = this.X[i + 1], by = this.Y[i + 1];
          if (Math.max(ax, bx) < x0 || Math.min(ax, bx) > x1 || Math.max(ay, by) < y0 || Math.min(ay, by) > y1) continue;
          out.push(i);
        }
      }
    }
    return Int32Array.from(out);
  }

  // once a frame: build the cells coming within reach (a few a frame), and draw the ones within reach
  update(cam) {
    if (this.lipMesh && !this.lipMesh.parent) this.scene.add(this.lipMesh);
    if (cam.distanceToSquared(this.last) > STEP * STEP) {
      this.last.copy(cam);
      const cx = cam.x, cy = -cam.z, hy = Math.max(0, cam.y - terrainHeight(this.hf, cx, cy));
      const reach = Math.sqrt(Math.max(0, FAR * FAR - hy * hy));
      const want = [];
      if (reach > 0) {
        const i0 = Math.floor((cx - reach) / CELL), i1 = Math.floor((cx + reach) / CELL);
        const j0 = Math.floor((cy - reach) / CELL), j1 = Math.floor((cy + reach) / CELL);
        for (let i = i0; i <= i1; i++) {
          for (let j = j0; j <= j1; j++) {
            const dx = Math.max(i * CELL - cx, 0, cx - (i + 1) * CELL), dy = Math.max(j * CELL - cy, 0, cy - (j + 1) * CELL);
            if (dx * dx + dy * dy > reach * reach) continue;
            const key = `${i},${j}`;
            if (this.cells.has(key)) want.push(key);
          }
        }
      }
      this.want = want.sort();
      this.queue = want.filter((k) => !this.cells.get(k).data)
        .sort((a, b) => this._dist(a, cx, cy) - this._dist(b, cx, cy));
      // the stones of cells far behind go (the ground under them stays looked at: built again quickly)
      for (const [k, c] of this.cells) if (c.data && this._dist(k, cx, cy) > FAR * 2.5) c.data = c.lip = null;
      if (!this.queue.length) this._show();
    }
    if (this.queue.length) {
      // the ground under each point first (a ray each, cached), some at a time, then the cell's stones in one go
      const t0 = performance.now();
      while (this.queue.length && performance.now() - t0 < 4) {
        const c = this.cells.get(this.queue[0]);
        c.at ??= 0;
        while (c.at < c.segs.length && performance.now() - t0 < 4) {
          for (const end = Math.min(c.segs.length, c.at + 32); c.at < end; c.at++) { this._look(c.segs[c.at]); this._look(c.segs[c.at] + 1); }
        }
        if (c.at < c.segs.length) break;
        c.data = this._build(c);
        c.lip = this.lipMesh ? this._buildLip(c) : null;
        this.queue.shift();
      }
      if (!this.queue.length) this._show();
    }
  }

  _dist(key, x, y) {
    const [i, j] = key.split(',').map(Number);
    return Math.hypot((i + 0.5) * CELL - x, (j + 0.5) * CELL - y);
  }

  // merge the built cells within reach into the one mesh
  _show() {
    const keys = (this.want || []).filter((k) => this.cells.get(k).data);
    const sig = keys.join(';');
    if (sig === this.shown) return;
    this.shown = sig;
    let total = 0;
    for (const k of keys) total += this.cells.get(k).data.length;
    const verts = total / FLOATS;
    if (verts > this.cap) {
      this.cap = Math.ceil(verts * 1.3 / 20) * 20;
      this.buf = new Float32Array(this.cap * FLOATS);
      const ib = new THREE.InterleavedBuffer(this.buf, FLOATS).setUsage(THREE.DynamicDrawUsage);
      this.geo.dispose();
      this.geo = new THREE.BufferGeometry();
      this.geo.setAttribute('position', new THREE.InterleavedBufferAttribute(ib, 3, 0));
      this.geo.setAttribute('normal', new THREE.InterleavedBufferAttribute(ib, 3, 3));
      this.geo.setAttribute('uv', new THREE.InterleavedBufferAttribute(ib, 2, 6));
      // aAlong is the uv's u (metres along the run): the joints and tones read it
      this.geo.setAttribute('aAlong', new THREE.InterleavedBufferAttribute(ib, 1, 6));
      const quads = (this.cap / 20) * 5;
      const idx = new Uint32Array(quads * 6);
      for (let q = 0, k = 0; q < quads; q++) {
        // two sections of 10 vertices make five quads; vertex 2f, 2f+1 at section A, +10 at section B
        const seg = Math.floor(q / 5), f = q % 5, a = seg * 20 + f * 2, b = a + 10;
        idx[k++] = a; idx[k++] = b; idx[k++] = a + 1; idx[k++] = a + 1; idx[k++] = b; idx[k++] = b + 1;
      }
      this.geo.setIndex(new THREE.BufferAttribute(idx, 1));
      this.mesh.geometry = this.geo;
    }
    let o = 0;
    for (const k of keys) { const d = this.cells.get(k).data; this.buf.set(d, o); o += d.length; }
    this.geo.attributes.position.data.needsUpdate = true;
    this.geo.setDrawRange(0, (verts / 20) * 30);
    this.mesh.visible = verts > 0;
    if (this.lipMesh) this._showLip(keys);
  }

  // the same for the lawn's raised edge: 8 points a segment (4 across at either end), 3 quads
  _showLip(keys) {
    let total = 0;
    for (const k of keys) total += this.cells.get(k).lip.length;
    const verts = total / LIP_FLOATS;
    if (verts > this.lipCap) {
      this.lipCap = Math.ceil(verts * 1.3 / 8) * 8;
      this.lipBuf = new Float32Array(this.lipCap * LIP_FLOATS);
      const ib = new THREE.InterleavedBuffer(this.lipBuf, LIP_FLOATS).setUsage(THREE.DynamicDrawUsage);
      this.lipGeo.dispose();
      this.lipGeo = new THREE.BufferGeometry();
      this.lipGeo.setAttribute('position', new THREE.InterleavedBufferAttribute(ib, 3, 0));
      this.lipGeo.setAttribute('normal', new THREE.InterleavedBufferAttribute(ib, 3, 3));
      this.lipGeo.setAttribute('aPave', new THREE.InterleavedBufferAttribute(ib, 1, 6));
      const quads = (this.lipCap / 8) * 3;
      const idx = new Uint32Array(quads * 6);
      for (let q = 0, k = 0; q < quads; q++) {
        const seg = Math.floor(q / 3), f = q % 3, a = seg * 8 + f, b = a + 4;
        idx[k++] = a; idx[k++] = b; idx[k++] = b + 1; idx[k++] = a; idx[k++] = b + 1; idx[k++] = a + 1;
      }
      this.lipGeo.setIndex(new THREE.BufferAttribute(idx, 1));
      this.lipMesh.geometry = this.lipGeo;
    }
    let o = 0;
    for (const k of keys) { const d = this.cells.get(k).lip; this.lipBuf.set(d, o); o += d.length; }
    this.lipGeo.attributes.position.data.needsUpdate = true;
    this.lipGeo.setDrawRange(0, (verts / 8) * 18);
    this.lipMesh.visible = verts > 0;
  }

  stats() {
    let built = 0, segs = 0;
    for (const c of this.cells.values()) { if (c.data) built++; segs += c.segs.length; }
    return { cells: this.cells.size, built, segs, shown: this.shown.split(';').filter(Boolean).length, verts: this.geo.drawRange.count / 3 * 2 };
  }
}

const _o = new THREE.Vector3(), _down = new THREE.Vector3(0, -1, 0);
