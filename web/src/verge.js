// The lawn of 백양로's roadside (issue #130): the verge between the carriageway's kerb and the sidewalk's, where the
// two-tier junipers and the round boxwoods stand, and the outer planting strip past the sidewalk (the ginkgo row and
// the low hedge). The Kakao roadview of August 2008 shows both green from the gate to 대강당, that of December 2010
// winter-yellow, the bare earth only in patches by the kerbs and round the trunks; the near verge of the 1997 photo
// is green between its shrubs. The road mesh draws them with the material 'verge_lawn' (blender/road.py LAWN), here
// replaced by the near terrain's own material made all lawn, so the verge is the lawn round it (the season's colour,
// the fallen leaves, the baked sun shadow), with:
//  - bare earth where the map built here says (the terrain's raked dirt): round the shrubs, the trees and any lamp
//    standing on the lawn, under the hedge, worn patches here and there (one to every WORN m², a metre or so across)
//    and short ones along the kerbs, at random; its edge frayed by the lawn texture
//  - the grass blades of the lawns (grass.js) on it, at its own height (height(); fewer on the bare earth: bare())
// The map is a texture over a rectangle turned to 백양로's direction (RES m texels): a few hundred kB.
import * as THREE from 'three';
import { MOBILE, mulberry } from './util.js';
import { derivedCopy, patchShader, upload } from './materials.js';

const BIN = 2;                         // point lookups: the lawn's triangles by squares of this size, m
const RES = MOBILE ? 0.5 : 0.25;       // the bare-earth map's texel, m
const PAD = 1.5;                       // its margin round the lawn, m
const WORN = 18;                       // a worn patch to every this many m² of the lawn
// bare earth round what stands on the lawn: [full to r0, none past r1 (m), how bare at most]
const AROUND = {
  juniper_tiers: [0.12, 0.5, 0.75], topiary_round: [0.2, 0.55, 0.8], hedge_low: [0.3, 0.6, 0.9],
  tree: [0.3, 0.85, 0.85], lamp: [0.15, 0.5, 0.8], shrub: [0.15, 0.5, 0.7],
};

const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

// the terrain shader (terrain.js makeNearTerrain) all lawn: no asphalt, paving or dirt from the ground map, no dry lawn;
// the dirt's share from the bare-earth map, frayed by the ground's own noise
function vergeEdit(uniforms) {
  return (sh) => {
    Object.assign(sh.uniforms, uniforms);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform sampler2D uVergeBare; uniform vec4 uVergeF, uVergeR;')
      .replace('sp.g = pvS * (1.0 - raS);', 'sp.g = pvS * (1.0 - raS);\n        sp = vec3(0.0); pvS = 0.0;')
      .replace('vec3 dryK = texture2D(uDry, suv).rgb * inside;', 'vec3 dryK = vec3(0.0);')
      .replace('float wg = max(0.0, 1.0 - wa - wpv - wd);', `float wg;
        {
          vec2 vd = wp - uVergeF.zw;
          vec2 vq = vec2(dot(vd, vec2(-uVergeF.y, uVergeF.x)), dot(vd, uVergeF.xy));
          float vm = texture2D(uVergeBare, (vq - uVergeR.xy) * uVergeR.zw).r;
          // (the lawn texture's green: linear mean 0.24, spread 0.1)
          float vf = texture2D(gD, wp / 1.3).g * 0.6 + texture2D(gD, wp / 4.7 + 0.31).g * 0.4 - 0.24;
          wd = smoothstep(0.42, 0.6, vm + vf * 2.2);
          wg = 1.0 - wd;
        }`);
  };
}

export class Verge {
  // root: the road's scene (baekyangro.glb, its materials bound); campus: campus.json (the road's line, the shrubs,
  // trees and lamps)
  constructor(root, campus) {
    this.meshes = [];
    root.updateMatrixWorld(true);
    root.traverse((o) => { if (o.isMesh && o.material?.name === 'verge_lawn') this.meshes.push(o); });
    // the triangles in campus coordinates (x east, y north, h up), nine numbers each
    const T = [];
    const v = new THREE.Vector3();
    for (const m of this.meshes) {
      const pos = m.geometry.attributes.position, idx = m.geometry.index;
      const n = idx ? idx.count : pos.count;
      for (let k = 0; k < n; k++) {
        v.fromBufferAttribute(pos, idx ? idx.getX(k) : k).applyMatrix4(m.matrixWorld);
        T.push(v.x, -v.z, v.y);
      }
    }
    this.T = Float32Array.from(T);
    const nt = this.T.length / 9;
    this.bins = new Map();
    for (let t = 0; t < nt; t++) {
      const o = t * 9, xs = [this.T[o], this.T[o + 3], this.T[o + 6]], ys = [this.T[o + 1], this.T[o + 4], this.T[o + 7]];
      for (let i = Math.floor(Math.min(...xs) / BIN); i <= Math.floor(Math.max(...xs) / BIN); i++) {
        for (let j = Math.floor(Math.min(...ys) / BIN); j <= Math.floor(Math.max(...ys) / BIN); j++) {
          const key = this._key(i, j);
          if (!this.bins.has(key)) this.bins.set(key, []);
          this.bins.get(key).push(t);
        }
      }
    }
    this._map(campus);
    this.material = null;
  }

  _key(i, j) { return (i + 32768) * 65536 + (j + 32768); }

  // the lawn's height at campus (x, y), NaN off it
  height(x, y) {
    const list = this.bins.get(this._key(Math.floor(x / BIN), Math.floor(y / BIN)));
    if (!list) return NaN;
    const T = this.T;
    for (const t of list) {
      const o = t * 9;
      const ax = T[o], ay = T[o + 1], bx = T[o + 3] - ax, by = T[o + 4] - ay, cx = T[o + 6] - ax, cy = T[o + 7] - ay;
      const d = bx * cy - by * cx;
      if (Math.abs(d) < 1e-9) continue;
      const px = x - ax, py = y - ay;
      const u = (px * cy - py * cx) / d, w = (bx * py - by * px) / d;
      if (u < -1e-4 || w < -1e-4 || u + w > 1 + 1e-4) continue;
      return T[o + 2] + (T[o + 5] - T[o + 2]) * u + (T[o + 8] - T[o + 2]) * w;
    }
    return NaN;
  }

  // the bare-earth map: its frame turned along 백양로 (chord from the gate to the far end), then what makes it bare
  _map(campus) {
    const P = campus.baekyangro.pts, [ox, oy] = P[0], [ex, ey] = P[P.length - 1];
    const L = Math.hypot(ex - ox, ey - oy), ax = (ex - ox) / L, ay = (ey - oy) / L;     // along; across = (-ay, ax)
    this.frame = [ax, ay, ox, oy];
    const toQ = (x, y) => [(x - ox) * -ay + (y - oy) * ax, (x - ox) * ax + (y - oy) * ay];
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (let k = 0; k < this.T.length; k += 3) {
      const [qx, qy] = toQ(this.T[k], this.T[k + 1]);
      x0 = Math.min(x0, qx); x1 = Math.max(x1, qx); y0 = Math.min(y0, qy); y1 = Math.max(y1, qy);
    }
    if (!(x1 > x0)) { x0 = y0 = 0; x1 = y1 = 1; }
    x0 -= PAD; y0 -= PAD;
    const W = Math.ceil((x1 + PAD - x0) / RES / 4) * 4, H = Math.ceil((y1 + PAD - y0) / RES);
    const M = new Float32Array(W * H);
    Object.assign(this, { W, H, q0: [x0, y0] });
    // stamp f(distance) at the texels within r of a point or a segment (a, b), the bareness kept where it is higher
    const stamp = (pax, pay, pbx, pby, r0, r1, peak) => {
      const [qax, qay] = toQ(pax, pay), [qbx, qby] = toQ(pbx, pby);
      const i0 = Math.max(0, Math.floor((Math.min(qax, qbx) - r1 - x0) / RES)), i1 = Math.min(W - 1, Math.ceil((Math.max(qax, qbx) + r1 - x0) / RES));
      const j0 = Math.max(0, Math.floor((Math.min(qay, qby) - r1 - y0) / RES)), j1 = Math.min(H - 1, Math.ceil((Math.max(qay, qby) + r1 - y0) / RES));
      const dx = qbx - qax, dy = qby - qay, l2 = dx * dx + dy * dy;
      for (let j = j0; j <= j1; j++) {
        for (let i = i0; i <= i1; i++) {
          const qx = x0 + (i + 0.5) * RES - qax, qy = y0 + (j + 0.5) * RES - qay;
          const t = l2 > 0 ? Math.min(1, Math.max(0, (qx * dx + qy * dy) / l2)) : 0;
          const d = Math.hypot(qx - dx * t, qy - dy * t);
          const val = peak * (1 - smooth(r0, r1, d));
          const k = j * W + i;
          if (val > M[k]) M[k] = val;
        }
      }
    };
    const onLawn = (x, y, r) => [[0, 0], [r, 0], [-r, 0], [0, r], [0, -r]].some(([u, w]) => this.height(x + u, y + w) === this.height(x + u, y + w));
    // round what stands on it
    for (const s of campus.shrubs) {
      if (!onLawn(s[1], s[2], 0)) continue;
      const [r0, r1, pk] = AROUND[s[0]] || AROUND.shrub, sc = s[3] || 1;
      stamp(s[1], s[2], s[1], s[2], r0 * sc, r1 * sc, pk);
    }
    for (const t of campus.trees) {
      if (onLawn(t[1], t[2], 0)) stamp(t[1], t[2], t[1], t[2], ...AROUND.tree);
    }
    for (const p of campus.props) {
      if (/^lamp/.test(p[0]) && onLawn(p[1], p[2], 0.2)) stamp(p[1], p[2], p[1], p[2], ...AROUND.lamp);
    }
    // worn patches here and there on the lawn, one to every WORN m² (the 2008 roadview: a metre or two across, between
    // the shrubs and by the kerbs, most of the verge whole)
    const rnd = mulberry(130);
    const nt = this.T.length / 9, area = new Float64Array(nt);
    let tot = 0;
    for (let t = 0; t < nt; t++) {
      const o = t * 9, T = this.T;
      tot += Math.abs((T[o + 3] - T[o]) * (T[o + 7] - T[o + 1]) - (T[o + 4] - T[o + 1]) * (T[o + 6] - T[o])) / 2;
      area[t] = tot;
    }
    for (let k = Math.round(tot / WORN); k > 0; k--) {
      const r = rnd() * tot;
      let lo = 0, hi = nt - 1;
      while (lo < hi) { const mid = (lo + hi) >> 1; if (area[mid] < r) lo = mid + 1; else hi = mid; }
      let u = rnd(), w = rnd();
      if (u + w > 1) { u = 1 - u; w = 1 - w; }
      const o = lo * 9, T = this.T;
      const px = T[o] + (T[o + 3] - T[o]) * u + (T[o + 6] - T[o]) * w, py = T[o + 1] + (T[o + 4] - T[o + 1]) * u + (T[o + 7] - T[o + 1]) * w;
      const a = rnd() * Math.PI, len = 0.3 + rnd() * 1.2, hx = Math.cos(a) * len / 2, hy = Math.sin(a) * len / 2;
      stamp(px - hx, py - hy, px + hx, py + hy, 0.2 + rnd() * 0.2, 0.6 + rnd() * 0.4, 0.6 + rnd() * 0.25);
    }
    // and short ones along the kerbs: the lawn's open edges (welded by position, an edge of one triangle only), each
    // patch on the lawn's side of it, a few metres apart
    const ids = new Map(), V = [];
    const vid = (x, y) => {
      const key = `${Math.round(x * 200)},${Math.round(y * 200)}`;
      let id = ids.get(key);
      if (id === undefined) { ids.set(key, (id = V.length / 2)); V.push(x, y); }
      return id;
    };
    const edges = new Map();
    for (let t = 0; t < nt; t++) {
      const o = t * 9, a = vid(this.T[o], this.T[o + 1]), b = vid(this.T[o + 3], this.T[o + 4]), c = vid(this.T[o + 6], this.T[o + 7]);
      for (const [p, q] of [[a, b], [b, c], [c, a]]) {
        if (p === q) continue;
        const key = p < q ? p * 1048576 + q : q * 1048576 + p;
        const e = edges.get(key);
        if (e) e[2]++; else edges.set(key, [p, q, 1, t]);
      }
    }
    let next = rnd() * 6;
    for (const [p, q, n, t] of edges.values()) {
      if (n !== 1) continue;
      const pxa = V[p * 2], pya = V[p * 2 + 1], dx = V[q * 2] - pxa, dy = V[q * 2 + 1] - pya, l = Math.hypot(dx, dy);
      if (l < 1e-3) continue;
      // the inward side: towards the triangle's middle
      const o = t * 9, cx = (this.T[o] + this.T[o + 3] + this.T[o + 6]) / 3, cy = (this.T[o + 1] + this.T[o + 4] + this.T[o + 7]) / 3;
      let nx = -dy / l, ny = dx / l;
      if ((cx - pxa) * nx + (cy - pya) * ny < 0) { nx = -nx; ny = -ny; }
      while (next < l) {
        const len = 0.4 + rnd() * 1.4, r1 = 0.35 + rnd() * 0.15, pk = 0.6 + rnd() * 0.2, f = next / l;
        const mx = pxa + dx * f + nx * 0.1, my = pya + dy * f + ny * 0.1, hx = dx / l * len / 2, hy = dy / l * len / 2;
        stamp(mx - hx, my - hy, mx + hx, my + hy, 0.15, r1, pk);
        next += 5 + rnd() * 14;
      }
      next -= l;
    }
    const data = this.data = new Uint8Array(W * H);
    for (let k = 0; k < data.length; k++) data[k] = Math.round(Math.min(1, M[k]) * 255);
    const tex = new THREE.DataTexture(data, W, H, THREE.RedFormat, THREE.UnsignedByteType);
    tex.unpackAlignment = 1;
    tex.magFilter = THREE.LinearFilter;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    tex.generateMipmaps = true;
    tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
    tex.needsUpdate = true;
    this.uniforms = {
      uVergeBare: { value: tex },
      uVergeF: { value: new THREE.Vector4(ax, ay, ox, oy) },
      uVergeR: { value: new THREE.Vector4(x0, y0, 1 / (W * RES), 1 / (H * RES)) },
    };
  }

  // how bare the earth is at campus (x, y), 0..1 (the map, without the shader's fraying)
  bare(x, y) {
    const [ax, ay, ox, oy] = this.frame;
    const qx = (x - ox) * -ay + (y - oy) * ax, qy = (x - ox) * ax + (y - oy) * ay;
    const fx = (qx - this.q0[0]) / RES - 0.5, fy = (qy - this.q0[1]) / RES - 0.5;
    const i = Math.floor(fx), j = Math.floor(fy);
    if (i < 0 || j < 0 || i >= this.W - 1 || j >= this.H - 1) return 0;
    const u = fx - i, w = fy - j, M = this.data, k = j * this.W + i;
    return ((M[k] * (1 - u) + M[k + 1] * u) * (1 - w) + (M[k + this.W] * (1 - u) + M[k + this.W + 1] * u) * w) / 255;
  }

  // the near terrain's material, all lawn, onto the road's lawn meshes. After every pass that patches the scene's
  // materials (the baked sun shadow's, the atmosphere's): the copy replays the terrain's own edits, those among them
  attach(terrainMat) {
    if (this.material || !this.meshes.length) return;
    const m = this.material = derivedCopy(terrainMat);
    m.name = 'verge_lawn';
    patchShader(m, 'vergeLawn', vergeEdit(this.uniforms));
    upload(this.uniforms.uVergeBare.value);
    for (const o of this.meshes) o.material = m;
  }
}
