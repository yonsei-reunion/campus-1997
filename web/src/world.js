// Loads the Blender-built GLBs, binds shared materials, merges static geometry into
// spatial chunks, and instances vegetation / props.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { mulberry, placeMatrix, countBy, versioned } from './util.js';
import { Impostor, renderImpostors, nearTreeMaterial, LOD, FADE } from './impostors.js';

const draco = new DRACOLoader().setDecoderPath('draco/');
export const gltfLoader = new GLTFLoader().setDRACOLoader(draco);
export const loadGLB = (url) => new Promise((res, rej) => gltfLoader.load(versioned(url), res, undefined, rej));

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

// ---------------------------------------------------------------------------- vegetation with impostor LOD
// Trees within nearDist of the LOD centre (the camera, or the ground point below a bird's-eye view) are the full
// models, the rest impostors lit by the scene (impostors.js), with a dithered cross-fade over the last FADE metres.
export class Forest {
  constructor(scene, renderer, lib, kits, trees, groundAt) {
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
    const counts = countBy(this.items, (it) => it.key);
    for (const key of Object.keys(kits)) {
      if (!counts[key]) continue;
      const kit = new InstancedKit(kits[key], lib, counts[key], { mat: (m) => nearTreeMaterial(lib, m) });
      kit.addTo(scene);
      this.near[key] = kit;
      const imp = new Impostor(key, kits[key], counts[key]);
      scene.add(imp.im);
      this.impostors[key] = imp;
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
  }
}
