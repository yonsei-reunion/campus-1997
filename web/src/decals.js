// Decals on the paving: manhole covers, gully grates and utility lids, saw-cut asphalt patches, oil under the parking
// stalls, scuffed zebra stripes, cracked and stained paving. tools/build_campus.py picks where they lie (campus.json
// decals: [kind, x, y, heading, scale]: on 백양로's carriageway only a manhole now and then and the grates along its
// kerbs, the wear on the side roads, car parks and walks); decals_paint.js paints what they look like into two
// atlases, in a worker while the rest loads.
//  - lit: the iron and concrete things lying on the ground (manholes, grates, lids): their own colour, relief (a normal
//    map), roughness and metal, lit as the ground is (PCSS, the baked sun shadow, the clouds and the fog: the shared
//    patches of materials.js and bakedshadow.js)
//  - mul: what only darkens the ground (oil, patches, grime, cracks, stains, worn paint): multiplied onto the frame
//    after the opaque scene, so the ground's own texture, light and shade show through
// One InstancedMesh each (two draw calls), holding the decals within FAR m of the camera, refilled when the camera has
// moved STEP m; each is laid on the walked surface (a plane through 3 x 3 raycast points, lifted over the highest)
// when it first comes near, and fades out towards FAR. Phones: a shorter reach, smaller atlas, half the cracks, stains
// and grime.
import * as THREE from 'three';
import { MOBILE, mulberry } from './util.js';
import { pcss, patchShader, globalPatch } from './materials.js';
import { KINDS, hash2, paintLit, paintMul } from './decals_paint.js';

const FAR = MOBILE ? 55 : 80;
const STEP = 4;
const LIFT = 0.015;
const SPREAD = 0.06;           // a decal whose 3 x 3 points are farther than this off one plane lies on steps, a kerb: dropped
const LIT_N = 512, MUL_N = MOBILE ? 512 : 1024;

const MUL_VS = `
  attribute vec4 aRect;
  attribute float aK;
  uniform float uFar;
  varying vec2 vUv; varying float vK;
  void main() {
    vUv = aRect.xy + uv * aRect.zw;
    vec4 w = modelMatrix * instanceMatrix * vec4( position, 1.0 );
    vK = aK * ( 1.0 - smoothstep( uFar - 15.0, uFar, distance( ( modelMatrix * instanceMatrix[ 3 ] ).xyz, cameraPosition ) ) );
    gl_Position = projectionMatrix * viewMatrix * w;
  }`;
const MUL_FS = `
  uniform sampler2D uAtlas;
  varying vec2 vUv; varying float vK;
  void main() {
    gl_FragColor = vec4( mix( vec3( 1.0 ), texture2D( uAtlas, vUv ).rgb, vK ), 1.0 );
  }`;

// the lit decals' own edit: each instance's atlas cell, the fade towards FAR
function litEdit(far) {
  return (sh) => {
    sh.uniforms.uDecalFar = far;
    const cellUv = [['MAP', 'vMapUv'], ['NORMALMAP', 'vNormalMapUv'], ['ROUGHNESSMAP', 'vRoughnessMapUv'], ['METALNESSMAP', 'vMetalnessMapUv']]
      .map(([m, v]) => `#ifdef USE_${m}\n${v} = aRect.xy + uv * aRect.zw;\n#endif`).join('\n');
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec4 aRect;\nuniform float uDecalFar;\nvarying float vDecalK;')
      .replace('#include <uv_vertex>', `#include <uv_vertex>\n${cellUv}`)
      .replace('#include <project_vertex>', `#include <project_vertex>
        vDecalK = 1.0;
        #ifdef USE_INSTANCING
        vDecalK = 1.0 - smoothstep( uDecalFar - 15.0, uDecalFar, distance( ( modelMatrix * instanceMatrix[ 3 ] ).xyz, cameraPosition ) );
        #endif`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying float vDecalK;')
      .replace('#include <map_fragment>', '#include <map_fragment>\ndiffuseColor.a *= vDecalK;');
  };
}

// an atlas texture, its pixels filled in when the painting is done
function atlas(N, srgb) {
  const t = new THREE.DataTexture(new Uint8Array(N * N * 4), N, N, THREE.RGBAFormat);
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.anisotropy = 8;
  return t;
}

export class Decals {
  // list: campus.json decals; walk: the walked surfaces (main.js walkables: the invisible flight ramps are skipped);
  // hf: the terrain heightfield (where no surface is hit); sunMap: bakedshadow.js SunMap
  constructor(scene, list, walk, hf, sunMap) {
    this.walk = walk.filter((m) => m.parent && m.visible);
    this.hf = hf;
    this.ray = new THREE.Raycaster();
    this.ray.firstHitOnly = true;
    const rnd = mulberry(4545);
    this.list = list.filter(([k]) => KINDS[k] && !(MOBILE && KINDS[k].thin && rnd() < 0.5));
    const n = this.list.length;
    this.state = new Int8Array(n);                // 0 not laid yet, 1 laid, -1 dropped
    this.mats = new Float32Array(n * 16);
    this.rects = new Float32Array(n * 4);
    this.ks = new Float32Array(n);
    this.list.forEach(([kind, x, y], i) => {
      const K = KINDS[kind], cx = Math.round(x * 10), cy = Math.round(y * 10);
      this.rects.set(K.cells[Math.floor(hash2(cx, cy, 45) * K.cells.length)], i * 4);
      this.ks[i] = 0.75 + 0.25 * hash2(cx, cy, 46);
    });
    this.last = new THREE.Vector3(1e9, 0, 0);
    this.far = { value: FAR };
    this.ready = false;

    const make = (lit, mat, name) => {
      const max = Math.max(1, this.list.filter(([k]) => !!KINDS[k].lit === lit).length);
      const geo = new THREE.PlaneGeometry(1, 1);
      geo.rotateX(-Math.PI / 2);
      geo.setAttribute('aRect', new THREE.InstancedBufferAttribute(new Float32Array(max * 4), 4).setUsage(THREE.DynamicDrawUsage));
      geo.setAttribute('aK', new THREE.InstancedBufferAttribute(new Float32Array(max), 1).setUsage(THREE.DynamicDrawUsage));
      const mesh = new THREE.InstancedMesh(geo, mat, max);
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      mesh.count = 0;
      mesh.frustumCulled = false;
      mesh.renderOrder = -2;       // with the blob shadows, before the see-through things (glass, spray)
      mesh.name = name;
      mesh.userData.owner = this;
      scene.add(mesh);
      return mesh;
    };
    this.tex = { col: atlas(LIT_N, true), nrm: atlas(LIT_N, false), orm: atlas(LIT_N, false), mul: atlas(MUL_N, false) };
    const lm = new THREE.MeshStandardMaterial({
      map: this.tex.col, normalMap: this.tex.nrm, roughnessMap: this.tex.orm, metalnessMap: this.tex.orm, roughness: 1, metalness: 1,
      transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4,
    });
    lm.name = 'decal_lit';
    pcss(lm);
    sunMap.patch(lm, 0);                            // (transparent: SunMap.patchScene would pass it by)
    patchShader(lm, 'decal', litEdit(this.far));
    globalPatch(lm);
    this.lit = make(true, lm, 'decals_lit');
    this.lit.receiveShadow = true;
    const mm = new THREE.ShaderMaterial({
      uniforms: { uAtlas: { value: this.tex.mul }, uFar: this.far },
      vertexShader: MUL_VS, fragmentShader: MUL_FS,
      transparent: true, depthWrite: false, blending: THREE.MultiplyBlending,
      polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4,
    });
    mm.name = 'decal_mul';
    this.mul = make(false, mm, 'decals_mul');
    this._paint();
  }

  // the atlases: painted in a worker (or, where that fails, here a moment later); nothing is drawn until they are in
  _paint() {
    const t0 = performance.now();
    const done = (lit, mul) => {
      const { col, nrm, orm, mul: m } = this.tex;
      col.image.data = lit.col; nrm.image.data = lit.nrm; orm.image.data = lit.orm; m.image.data = mul;
      for (const t of [col, nrm, orm, m]) t.needsUpdate = true;
      this.paintMs = performance.now() - t0;
      this.ready = true;
      this.last.set(1e9, 0, 0);
    };
    const here = () => setTimeout(() => done(paintLit(LIT_N), paintMul(MUL_N)), 0);
    let w = null;
    try { w = new Worker(new URL('./decals_paint.js', import.meta.url), { type: 'module' }); } catch { w = null; }
    if (!w) { here(); return; }
    w.onmessage = ({ data }) => { w.terminate(); done(data.lit, data.mul); };
    w.onerror = (e) => { e.preventDefault?.(); w.terminate(); here(); };
    w.postMessage({ lit: LIT_N, mul: MUL_N });
  }

  // the walked surface's height at campus (x, y)
  groundAt(x, y) {
    this.ray.set(_o.set(x, 600, -y), _down);
    const h = this.ray.intersectObjects(this.walk, false);
    return h.length ? h[0].point.y : this.hf.height(x, y);
  }

  // lay decal i on the ground: a plane through 3 x 3 points over its footprint, lifted over the highest of them
  _lay(i) {
    const [kind, x, y, rot, sc] = this.list[i];
    const K = KINDS[kind];
    const L = K.size[0] * sc, W = K.size[1] * (K.stretch ? 1 : sc), c = Math.cos(rot), s = Math.sin(rot);
    let h0 = 0, gu = 0, gv = 0;
    const hs = [];
    for (let a = -1; a <= 1; a++) {
      for (let b = -1; b <= 1; b++) {
        const du = a * 0.45 * L, dv = b * 0.45 * W;
        const h = this.groundAt(x + c * du - s * dv, y + s * du + c * dv);
        hs.push([du, dv, h]);
        h0 += h / 9;
        gu += h * du; gv += h * dv;
      }
    }
    gu /= 6 * (0.45 * L) ** 2; gv /= 6 * (0.45 * W) ** 2;
    let lo = 1e9, hi = -1e9;
    for (const [du, dv, h] of hs) { const r = h - (h0 + gu * du + gv * dv); lo = Math.min(lo, r); hi = Math.max(hi, r); }
    if (hi - lo > SPREAD) { this.state[i] = -1; return; }
    // three: campus (x, y, up) -> (x, up, -y); +x along the heading, +z to its right, +y the plane's normal
    _x.set(c, gu, -s).normalize();
    _z.set(s, -gv, c);
    _y.crossVectors(_z, _x).normalize();
    _z.crossVectors(_x, _y);
    _m.makeBasis(_x.multiplyScalar(L), _y, _z.multiplyScalar(W)).setPosition(x, h0 + hi + LIFT, -y);
    _m.toArray(this.mats, i * 16);
    this.state[i] = 1;
  }

  // once a frame: refill the meshes with the decals round the camera after it has moved STEP m
  update(cam) {
    if (!this.ready || cam.distanceToSquared(this.last) < STEP * STEP) return;
    this.last.copy(cam);
    const R2 = (FAR + STEP) ** 2;
    let nl = 0, nm = 0;
    for (let i = 0; i < this.list.length; i++) {
      const e = this.list[i], dx = e[1] - cam.x, dz = -e[2] - cam.z;
      if (dx * dx + dz * dz > R2 || this.state[i] < 0) continue;
      if (this.state[i] === 0) { this._lay(i); if (this.state[i] < 0) continue; }
      const lit = !!KINDS[e[0]].lit, mesh = lit ? this.lit : this.mul, k = lit ? nl++ : nm++;
      mesh.instanceMatrix.array.set(this.mats.subarray(i * 16, i * 16 + 16), k * 16);
      mesh.geometry.attributes.aRect.array.set(this.rects.subarray(i * 4, i * 4 + 4), k * 4);
      mesh.geometry.attributes.aK.array[k] = this.ks[i];
    }
    for (const [mesh, n] of [[this.lit, nl], [this.mul, nm]]) {
      mesh.count = n;
      mesh.instanceMatrix.needsUpdate = true;
      mesh.geometry.attributes.aRect.needsUpdate = true;
      mesh.geometry.attributes.aK.needsUpdate = true;
    }
  }

  stats() {
    return { total: this.list.length, lit: this.lit.count, mul: this.mul.count, dropped: this.state.reduce((a, v) => a + (v < 0), 0),
      laid: this.state.reduce((a, v) => a + (v > 0), 0), paintMs: Math.round(this.paintMs || -1), ready: this.ready };
  }
}

const _o = new THREE.Vector3(), _down = new THREE.Vector3(0, -1, 0);
const _x = new THREE.Vector3(), _y = new THREE.Vector3(), _z = new THREE.Vector3(), _m = new THREE.Matrix4();
