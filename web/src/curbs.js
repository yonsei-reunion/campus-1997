// Curbs (경계석) where the painted asphalt and paving meet the lawn. tools/build_campus.py traces the edges of the
// paving in the ground map (campus.json curbs: [kind, x0, y0, dx1, dy1, ...] in cm, the lawn on the left going along:
// kind 'p' by the paving, 'a' by the asphalt of the drives and car parks; none along 백양로, whose own road mesh has
// its kerbs, nor along the walls of the halls or in the woods). Each run gets a low granite kerb standing on the lawn
// side over the edge, so the cut between the two ground textures (terrain.js) lies under its paving-side face:
//  - by the paving 15 cm wide and 15 cm high, by the asphalt 18 cm wide (the 상뜰's kerbs in
//    reference/대우관_2024_정면과_상뜰.jpg, the drives' and the 백양로 islands' in the 2008 / 2011 roadview)
//  - the top arris on the paving side rounded, a joint every metre and each stone a shade lighter or darker
//    (the shared 'curb' material of 백양로's kerbs, with the joints and the tones as a shader edit)
// The kerbs are built in CELL m squares as the camera comes within reach, on the terrain as it is drawn (each 5 m
// cell's two triangles, terrain.js gridGeometry); where a flight, a terrace or the road stands over the ground the
// kerb is left out. Every built square within reach is drawn as one mesh (one draw call), merged again when that set
// changes; phones reach less far.
import * as THREE from 'three';
import { MOBILE } from './util.js';
import { derivedCopy, patchShader } from './materials.js';

const CELL = 64;
const FAR = MOBILE ? 80 : 140;       // reach from the camera, m
const STEP = 6;                      // look again after the camera has moved this far
const PIECE = 1.0;                   // stone length, m
const SUB = 2.5;                     // longest straight stretch between two sections (half a terrain cell)
const KINDS = [{ w: 0.15, h: 0.15 }, { w: 0.18, h: 0.15 }];      // 'p', 'a'
const LAP = 0.04;                    // how far the stone reaches over the edge onto the paving
const ARRIS = 0.025;                 // radius of the rounded top edge on the paving side
const SINK = 0.1;                    // how far the faces go down into the ground
const FLOATS = 8;                    // position 3, normal 3, uv 2

// the visible terrain's height: the 5 m grid's cells split along (i+1, j)-(i, j+1) as terrain.js draws them
function terrainHeight(hf, x, y) {
  const { half, step, n, data } = hf;
  const fx = Math.min(Math.max((x + half) / step, 0), n - 1.001), fy = Math.min(Math.max((y + half) / step, 0), n - 1.001);
  const i = fx | 0, j = fy | 0, ax = fx - i, ay = fy - j;
  const a = data[j * n + i], b = data[j * n + i + 1], c = data[(j + 1) * n + i], d = data[(j + 1) * n + i + 1];
  return ax + ay <= 1 ? a + (b - a) * ax + (c - a) * ay : d + (c - d) * (1 - ax) + (b - d) * (1 - ay);
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
  // road, the flights, the terraces: no kerb under them); lib: the material library
  constructor(scene, list, hf, over, lib) {
    this.hf = hf;
    this.over = over;
    this.ray = new THREE.Raycaster();
    this.ray.firstHitOnly = true;
    // every run's points, subdivided to SUB m, in flat arrays; segments by cell
    const X = [], Y = [], U = [], MX = [], MY = [], K = [];
    this.cells = new Map();                 // key -> {segs: start indices, data: Float32Array | null}
    const seg = (i) => {
      const key = this._key((X[i] + X[i + 1]) / 2, (Y[i] + Y[i + 1]) / 2);
      let c = this.cells.get(key);
      if (!c) this.cells.set(key, (c = { segs: [], data: null }));
      c.segs.push(i);
    };
    let seed = 1;
    for (const r of list) {
      const kind = r[0] === 'a' ? 1 : 0;
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
            MX.push(sn[0]); MY.push(sn[1]); U.push(u + L * f); K.push(kind);
          }
          u += L;
        }
        X.push(a[0]); Y.push(a[1]); MX.push(ma[0]); MY.push(ma[1]); U.push(u); K.push(kind);
      }
      for (let i = first; i < X.length - 1; i++) seg(i);       // (none from a run's last point to the next run)
    }
    const f32 = (a) => Float32Array.from(a);
    Object.assign(this, { X: f32(X), Y: f32(Y), U: f32(U), MX: f32(MX), MY: f32(MY), K: Uint8Array.from(K) });
    this.state = new Uint8Array(X.length);            // 0 not looked at, 1 on the ground, 2 under something
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

  // once a frame: build the cells coming within reach (a few a frame), and draw the ones within reach
  update(cam) {
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
      for (const [k, c] of this.cells) if (c.data && this._dist(k, cx, cy) > FAR * 2.5) c.data = null;
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
  }

  stats() {
    let built = 0, segs = 0;
    for (const c of this.cells.values()) { if (c.data) built++; segs += c.segs.length; }
    return { cells: this.cells.size, built, segs, shown: this.shown.split(';').filter(Boolean).length, verts: this.geo.drawRange.count / 3 * 2 };
  }
}

const _o = new THREE.Vector3(), _down = new THREE.Vector3(0, -1, 0);
