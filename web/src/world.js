// Loads the Blender-built GLBs, binds shared materials, merges static geometry into
// spatial chunks, and instances vegetation / props.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { mulberry, placeMatrix, countBy, versioned } from './util.js';
import { Impostor, renderImpostors, nearTreeMaterial, LOD, FADE } from './impostors.js';

const draco = new DRACOLoader().setDecoderPath('draco/').preload();     // (the decoder comes down with the first files)
export const gltfLoader = new GLTFLoader().setDRACOLoader(draco);

// GLBs asked for ahead (prefetch): the loading screen's files all come down at once, and the main thread parses each
// when its turn comes, instead of every stage asking for its files only once the stage before is done
const ahead = new Map();
export function prefetch(urls, priority = 'auto') {
  for (const u of urls) {
    if (!ahead.has(u)) ahead.set(u, fetch(versioned(u), { priority }).then((r) => (r.ok ? r.arrayBuffer() : null), () => null));
  }
}
// the material names in a prefetched GLB's JSON chunk: their textures can be asked for before it is parsed
export async function glbMaterials(url) {
  const buf = await ahead.get(url);
  if (!buf) return [];
  const v = new DataView(buf);
  if (v.getUint32(0, true) !== 0x46546c67) return [];        // ('glTF')
  const json = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 20, v.getUint32(12, true))));
  return (json.materials || []).map((m) => m.name);
}
export async function loadGLB(url) {
  const buf = await ahead.get(url);
  ahead.delete(url);
  if (buf) return gltfLoader.parseAsync(buf, THREE.LoaderUtils.extractUrlBase(url));
  return new Promise((res, rej) => gltfLoader.load(versioned(url), res, undefined, rej));
}

// A building that keeps its own shade of a shared material (the GLB names only the shared one): 연희관's rubble is
// the warm red-brown of reference/연희관_정면_2023.jpg, 언더우드관 · 스팀슨관 · 아펜젤러관's the warm brown of their 2016
// photos (stone_rubble_warm), the other stone halls' the greyer stone of 핀슨관 · 성암관
const OWN = [
  [/^lm_yeonhui/, { stone_rubble: 'stone_rubble_brown' }],
  [/^lm_(underwood|stimson|appenzeller)/, { stone_rubble: 'stone_rubble_warm' }],
];
const ownMats = (o) => OWN.find(([re]) => re.test(o.name) || re.test(o.parent?.name ?? ''))?.[1];

// Our own GLBs carry material *names*; replace them with the shared library materials.
// baked: the halls and landmarks, whose COLOR_0 is blender/bake.py's occlusion and weathering data, not a colour:
// their library materials become lib.baked() copies reading it as the attribute `bake`.
export function bindMaterials(root, lib, keepUnknown = false, baked = false) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const own = ownMats(o);                        // (the loaded materials are shared between meshes: rename nothing)
    let out = mats.map((m) => (own?.[m.name] ?? ((lib.defs[m.name] || !keepUnknown) ? m.name : null)))
      .map((n, i) => (n ? lib.get(n) : mats[i]));
    if (baked) {
      const age = o.userData.weather ?? o.parent?.userData.weather ?? 1;
      out = out.map((m) => lib.baked(m, age));
      const g = o.geometry;
      if (out.some((m) => m.userData.baked) && g.attributes.color && !g.attributes.bake) {
        g.setAttribute('bake', g.attributes.color);
        g.deleteAttribute('color');
      }
      if (g.attributes._edge) { g.setAttribute('edge', g.attributes._edge); g.deleteAttribute('_edge'); }   // (bake.py)
    }
    o.material = Array.isArray(o.material) ? out : out[0];
  });
}

// the baked attribute as Draco decodes it (16-bit normalized RGBA), so that every geometry of a bucket merges;
// white where a mesh has none
function bakeU16(a, count) {
  if (a && a.array instanceof Uint16Array && a.normalized && a.itemSize === 4) return a;
  const out = new Uint16Array(count * 4).fill(65535);
  if (a) for (let i = 0; i < count; i++) for (let c = 0; c < Math.min(4, a.itemSize); c++) out[i * 4 + c] = Math.round(a.getComponent(i, c) * 65535);
  return new THREE.BufferAttribute(out, 4, true);
}

// the distances to the arrises (blender/bake.py _edge, metres) as 16-bit normalized / 128 m (2 mm); 1 (none) where a
// mesh has none
function edgeU16(a, count) {
  if (a && a.array instanceof Uint16Array && a.normalized && a.itemSize === 4) return a;
  const out = new Uint16Array(count * 4).fill(65535);
  if (a) for (let i = 0; i < count; i++) for (let c = 0; c < Math.min(4, a.itemSize); c++) out[i * 4 + c] = Math.round(Math.min(Math.max(a.getComponent(i, c) / 128, 0), 1) * 65535);
  return new THREE.BufferAttribute(out, 4, true);
}

// Merge every mesh under root into one mesh per (material, chunk).
export function mergeStatic(root, { chunk = 160, castShadow = true, receiveShadow = true, name = 'static' } = {}) {
  root.updateMatrixWorld(true);
  const buckets = new Map();
  const box = new THREE.Box3(), c = new THREE.Vector3();
  root.traverse((o) => {
    if (!o.isMesh) return;
    const g = o.geometry.clone();
    g.applyMatrix4(o.matrixWorld);
    for (const k of Object.keys(g.attributes)) {
      if (!['position', 'normal', 'uv', 'color', 'bake', 'edge'].includes(k)) g.deleteAttribute(k);
    }
    if (!g.attributes.uv) g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    if (o.material.userData.baked) g.setAttribute('bake', bakeU16(g.attributes.bake, g.attributes.position.count));
    else if (g.attributes.bake) g.deleteAttribute('bake');
    if (o.material.userData.baked) g.setAttribute('edge', edgeU16(g.attributes.edge, g.attributes.position.count));
    else if (g.attributes.edge) g.deleteAttribute('edge');
    if (o.material.vertexColors) {
      if (!g.attributes.color) g.setAttribute('color', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 3).fill(1), 3));
      else if (g.attributes.color.itemSize === 4) {
        const c4 = g.attributes.color, c3 = new Float32Array(c4.count * 3);
        for (let i = 0; i < c4.count; i++) { c3[i * 3] = c4.getX(i); c3[i * 3 + 1] = c4.getY(i); c3[i * 3 + 2] = c4.getZ(i); }
        g.setAttribute('color', new THREE.Float32BufferAttribute(c3, 3));
      }
    } else if (g.attributes.color) g.deleteAttribute('color');
    // keep the index (mergeGeometries needs all or none indexed): the Blender meshes share ~1/3 of their corners,
    // so de-indexing would cost 1.5x the vertices on the GPU and in every pass
    if (!g.index) g.setIndex(Array.from({ length: g.attributes.position.count }, (_, i) => i));
    box.setFromBufferAttribute(g.attributes.position);
    box.getCenter(c);
    // (by material object: a building's own weathering makes a second copy of a library material, same name)
    const key = o.material.name + '#' + o.material.id + '|' + Math.floor(c.x / chunk) + '|' + Math.floor(c.z / chunk);
    if (!buckets.has(key)) buckets.set(key, { mat: o.material, geos: [] });
    buckets.get(key).geos.push(g);
  });
  const group = new THREE.Group();
  group.name = name;
  for (const [key, { mat, geos }] of buckets) {
    const merged = mergeGeometries(geos, false);
    if (!merged) { console.warn('mergeStatic: could not merge', key); continue; }
    merged.computeBoundingSphere();
    const m = new THREE.Mesh(merged, mat);
    m.castShadow = castShadow && !mat.name.startsWith('glass');
    m.receiveShadow = receiveShadow;
    m.name = key;
    group.add(m);
  }
  return group;
}

// ---------------------------------------------------------------------------- instancing
function instanced(geo, mat, capacity, castShadow) {
  const im = new THREE.InstancedMesh(geo, mat, capacity);
  im.count = 0;
  im.castShadow = castShadow;
  im.receiveShadow = true;
  im.frustumCulled = false;
  return im;
}

// A "kit" is a loaded GLB whose meshes become InstancedMesh parts sharing one transform list.
// mat: the material the parts draw with, for each library material (the forest's near trees take their own copies)
export class InstancedKit {
  constructor(gltfScene, lib, capacity, { shadows = true, colors = false, mat = (m) => lib.instanced(m) } = {}) {
    this.parts = [];
    gltfScene.updateMatrixWorld(true);
    gltfScene.traverse((o) => {
      if (!o.isMesh) return;
      const g = o.geometry.clone();
      g.applyMatrix4(o.matrixWorld);
      this.parts.push(instanced(g, mat(o.material), capacity, shadows));
    });
    this.capacity = capacity;
    this.count = 0;
    this.colors = colors;
  }
  add(matrix, color) {
    if (this.count >= this.capacity) return -1;
    for (const p of this.parts) {
      p.setMatrixAt(this.count, matrix);
      if (color && ((this.colors && p.material.name === 'car_paint') || p.material.name === 'cloth')) p.setColorAt(this.count, color);
    }
    return this.count++;
  }
  set(i, matrix) {
    for (const p of this.parts) p.setMatrixAt(i, matrix);
  }
  // bounds: only for kits placed once (the forest re-commits as you walk; its parts are never frustum culled)
  commit(bounds = true) {
    for (const p of this.parts) {
      p.count = this.count;
      p.instanceMatrix.needsUpdate = true;
      if (p.instanceColor) p.instanceColor.needsUpdate = true;
      if (bounds) p.computeBoundingSphere();
    }
  }
  addTo(parent) {
    for (const p of this.parts) parent.add(p);
  }
}

// ---------------------------------------------------------------------------- view culling of the kits
// The kits placed once (shrubs, props, parked cars), the forest's near trees and impostors and the far hills' trees are
// an InstancedMesh per part over the whole campus (or the whole ring of hills), drawn whole whatever the view: never
// frustum culled, as their bounds are always in view. A KitCuller packs only the instances in view to the front of
// their buffers: those whose bounding sphere meets a frustum TURN wider than the camera's on every side and PAD metres
// out, worked out again once the camera has turned or moved past those margins (and the buffers sent again only when
// that changed what is in view). A part with none in view is hidden (three draws an InstancedMesh of count 0 too).
// A kit may have a lighter model for the instances farther than some distance (the parked cars).
// whole(): the full sets, for what draws from elsewhere (the static shadow cache, shadows.js; the sun-shadow bake).
const TURN = 6 * Math.PI / 180, PAD = 2.5;
const _q = new THREE.Quaternion(), _p = new THREE.Vector3(), _c = new THREE.Vector3(), _mm = new THREE.Matrix4();

// parts sharing one transform list: one buffer for all of them (one upload), a copy of the full list to pack from
function packed(parts) {
  const M = parts[0].instanceMatrix, cap = M.count;
  for (const p of parts) p.instanceMatrix = M;
  M.setUsage(THREE.DynamicDrawUsage);
  for (const p of parts) p.instanceColor?.setUsage(THREE.DynamicDrawUsage);
  const colors = parts.filter((p) => p.instanceColor).map((p) => [p.instanceColor, new Float32Array(cap * 3)]);
  return { parts, M, all: new Float32Array(cap * 16), colors, idx: new Uint32Array(cap), shown: 0 };
}

export class KitCuller {
  constructor() {
    this.sets = [];
    this.cam = new THREE.PerspectiveCamera();
    this.frustum = new THREE.Frustum();
    this.at = new THREE.Vector3(1e9, 0, 0);
    this.q = new THREE.Quaternion();
    this.lens = '';
    this.full = true;            // every set drawn whole (until the first update)
    this.enabled = true;
  }

  // parts: InstancedMeshes sharing one transform list (an InstancedKit's parts, or an impostor's mesh), the first
  // parts[0].count of it in place; bounds: their joint bounding sphere in the model frame (or the parts' boxes');
  // far: the parts of a lighter model placed alike, drawn for the instances farther than dist from the camera.
  // Returns the set, for refill() when the list changes (the forest's as you walk)
  add(parts, { bounds = null, far = null, dist = 0 } = {}) {
    let ks = bounds;
    if (!ks) {
      const box = new THREE.Box3();
      for (const p of parts) { if (!p.geometry.boundingBox) p.geometry.computeBoundingBox(); box.union(p.geometry.boundingBox); }
      ks = box.getBoundingSphere(new THREE.Sphere());
    }
    const cap = parts[0].instanceMatrix.count;
    const s = { near: packed(parts), far: far && packed(far), d2: dist * dist, n: 0, ks, sph: new Float32Array(cap * 4),
      valid: false, dirty: false };
    this.sets.push(s);
    this.refill(s);
    return s;
  }

  // the set's list as its buffers hold it now (parts[0].count of them, just written and sent whole): drawn whole
  // until the next update() culls it
  refill(s) {
    const n = s.n = s.near.parts[0].count, { sph, ks } = s;
    for (const d of [s.near, s.far]) {
      if (!d) continue;
      d.all.set(d.M.array.subarray(0, n * 16));
      for (const [attr, src] of d.colors) src.set(attr.array.subarray(0, n * 3));
    }
    const all = s.near.all;
    for (let i = 0; i < n; i++) {
      _mm.fromArray(all, i * 16);
      _c.copy(ks.center).applyMatrix4(_mm);
      sph[i * 4] = _c.x; sph[i * 4 + 1] = _c.y; sph[i * 4 + 2] = _c.z;
      sph[i * 4 + 3] = ks.radius * _mm.getMaxScaleOnAxis();
    }
    const d = s.near;
    for (const p of d.parts) p.visible = true;
    this._send(d.M, n * 16);                           // (all of it: a hidden part's last range may be pending)
    for (const [attr] of d.colors) this._send(attr, n * 3);
    d.shown = n;
    this._hide(s.far);
    s.valid = false;
    s.dirty = true;
  }

  // camera: the view about to be drawn
  update(camera, force = false) {
    if (!this.enabled) return;
    camera.updateMatrixWorld();
    camera.matrixWorld.decompose(_p, _q, _c);
    const lens = `${camera.fov},${camera.aspect},${camera.zoom},${camera.near},${camera.far}`;
    if (!force && !this.full && lens === this.lens && _p.distanceTo(this.at) < PAD && _q.angleTo(this.q) < TURN * 0.8) {
      for (const s of this.sets) if (s.dirty) this._cull(s);     // (a list refilled since)
      return;
    }
    this.at.copy(_p);
    this.q.copy(_q);
    this.lens = lens;
    // the camera's frustum, TURN wider each way
    const c = this.cam;
    const tv = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) / camera.zoom, th = tv * camera.aspect;
    const v = Math.min(Math.atan(tv) + TURN, 1.5), h = Math.min(Math.atan(th) + TURN, 1.5);
    c.fov = THREE.MathUtils.radToDeg(v * 2);
    c.aspect = Math.tan(h) / Math.tan(v);
    c.near = camera.near;
    c.far = camera.far;
    c.updateProjectionMatrix();
    _mm.multiplyMatrices(c.projectionMatrix, camera.matrixWorldInverse);
    this.frustum.setFromProjectionMatrix(_mm);
    for (const s of this.sets) this._cull(s);
    this.full = false;
  }

  // every instance drawn, in the full model (update() culls again)
  whole() {
    for (const s of this.sets) {
      const d = s.near, n = s.n;
      for (const p of d.parts) p.visible = true;
      this._hide(s.far);
      if (d.shown === n && !s.valid) continue;
      d.M.array.set(d.all.subarray(0, n * 16));
      for (const [attr, src] of d.colors) { attr.array.set(src.subarray(0, n * 3)); this._send(attr, n * 3); }
      this._send(d.M, n * 16);
      for (const p of d.parts) p.count = n;
      d.shown = n;
      s.valid = false;
    }
    this.full = true;
  }

  _cull(s) {
    const planes = this.frustum.planes, { sph, n, near, far, d2 } = s;
    const ni = near.idx, fi = far?.idx, { x: cx, y: cy, z: cz } = this.at;
    s.dirty = false;
    let k = 0, f = 0, same = s.valid;
    for (let i = 0; i < n; i++) {
      const x = sph[i * 4], y = sph[i * 4 + 1], z = sph[i * 4 + 2], r = -(sph[i * 4 + 3] + PAD);
      let inside = true;
      for (let j = 0; j < 6; j++) {
        const { normal: nn, constant } = planes[j];
        if (nn.x * x + nn.y * y + nn.z * z + constant < r) { inside = false; break; }
      }
      if (!inside) continue;
      if (far && (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 > d2) {
        if (fi[f] !== i) { fi[f] = i; same = false; }
        f++;
      } else {
        if (ni[k] !== i) { ni[k] = i; same = false; }
        k++;
      }
    }
    if (same && k === near.shown && (!far || f === far.shown)) return;
    this._pack(near, k);
    if (far) this._pack(far, f);
    s.valid = true;
  }

  // instances idx[0 .. k) of the full list to the front of the buffers
  _pack(d, k) {
    const dst = d.M.array, all = d.all, idx = d.idx;
    for (let j = 0; j < k; j++) { const i = idx[j]; dst.set(all.subarray(i * 16, i * 16 + 16), j * 16); }
    for (const [attr, src] of d.colors) {
      for (let j = 0; j < k; j++) { const i = idx[j]; attr.array.set(src.subarray(i * 3, i * 3 + 3), j * 3); }
      this._send(attr, k * 3);
    }
    this._send(d.M, k * 16);
    for (const p of d.parts) { p.count = k; p.visible = k > 0; }
    d.shown = k;
  }

  _hide(d) {
    if (!d) return;
    for (const p of d.parts) { p.count = 0; p.visible = false; }
    d.shown = 0;
  }

  _send(attr, len) {
    if (!len) return;                                  // (nothing drawn)
    attr.clearUpdateRanges();
    attr.addUpdateRange(0, len);
    attr.needsUpdate = true;
  }
}

// ---------------------------------------------------------------------------- vegetation with impostor LOD
// Trees within nearDist of the LOD centre (the camera, or the ground point below a bird's-eye view) are the full
// models, the rest impostors lit by the scene (impostors.js), with a dithered cross-fade over the last FADE metres.
// culler: the KitCuller that draws only the ones in view of each (refilled as the lists change)
export class Forest {
  constructor(scene, renderer, lib, kits, trees, groundAt, culler = null) {
    this.scene = scene;
    this.kits = kits;            // {species_variant: gltf.scene}
    this.lib = lib;
    this.items = [];             // {key, m4, x, z}: instance matrix and ground position (three XZ)
    const rnd = mulberry(42);
    for (const [sp, x, y, sc, rot] of trees) {
      const v = rnd() < 0.5 ? 0 : 1;
      const key = `${sp}_${v}`;
      if (!kits[key]) continue;
      const m4 = placeMatrix(new THREE.Matrix4(), x, groundAt(x, y) - 0.05, y, rot, sc);
      this.items.push({ key, m4, x, z: -y });
    }
    // near meshes
    this.near = {};
    this.impostors = {};         // {key: Impostor} (its InstancedMesh: .im)
    this.culler = culler;
    this.culled = [];            // their sets in the culler
    const counts = countBy(this.items, (it) => it.key);
    for (const key of Object.keys(kits)) {
      if (!counts[key]) continue;
      const kit = new InstancedKit(kits[key], lib, counts[key], { mat: (m) => nearTreeMaterial(lib, m) });
      kit.addTo(scene);
      this.near[key] = kit;
      const imp = new Impostor(key, kits[key], counts[key]);
      scene.add(imp.im);
      this.impostors[key] = imp;
      if (!culler) continue;
      // (the impostor's quad turns to the camera round the crown centre: R across, quad.x .. quad.y up)
      const { box, quad } = imp, up = Math.max(-quad.x, quad.y);
      this.culled.push(culler.add(kit.parts), culler.add([imp.im], { bounds: new THREE.Sphere(new THREE.Vector3(0, box.w, 0), Math.hypot(box.x, up)) }));
    }
    this.renderImpostors(renderer);
    this.lastUpdate = new THREE.Vector3(1e9, 0, 0);
    this.lastNear = 0;
    this.nearDist = 230;
  }

  // (re)draw the impostor atlases from the tree models, e.g. after a season change swapped the leaf textures
  renderImpostors(renderer) {
    renderImpostors(renderer, Object.values(this.impostors));
  }

  update(camPos, force = false) {
    if (!force && this.nearDist === this.lastNear && camPos.distanceToSquared(this.lastUpdate) < 64) return;
    this.lastUpdate.copy(camPos);
    this.lastNear = this.nearDist;
    // (the cross-fade's centre moves with the sorting: both forms in the FADE metres inside nearDist)
    LOD.value.set(camPos.x, camPos.z, this.nearDist, FADE);
    const nearIn = this.nearDist ** 2, impOut = Math.max(0, this.nearDist - FADE) ** 2;
    for (const k in this.near) this.near[k].count = 0;
    const ic = {};
    for (const k in this.impostors) ic[k] = 0;
    for (const it of this.items) {
      const d2 = (it.x - camPos.x) ** 2 + (it.z - camPos.z) ** 2;
      if (d2 < nearIn) {
        const kit = this.near[it.key];
        kit.set(kit.count++, it.m4);
      }
      if (d2 > impOut) this.impostors[it.key].im.setMatrixAt(ic[it.key]++, it.m4);
    }
    for (const k in this.near) this.near[k].commit(false);
    for (const k in this.impostors) {
      const { im } = this.impostors[k];
      im.count = ic[k];
      im.instanceMatrix.needsUpdate = true;
    }
    for (const s of this.culled) this.culler.refill(s);
  }
}
