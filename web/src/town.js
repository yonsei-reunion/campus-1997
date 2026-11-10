// 정문 밖 (campus.json `town`, tools/gate_town.py, blender/town.py): 성산로, the 경의선's bank and bridge, the town south of
// it. The town's models, and the cars and city buses that pass on 성산로.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { bindMaterials, mergeStatic } from './world.js';
import { drapeTerrain } from './terrain.js';
import { Path, CAR_COLORS } from './life.js';
import { pcss, globalPatch } from './materials.js';
import { MOBILE, mulberry } from './util.js';

const SEEN = 380;          // cars farther than this from the view are not drawn

// The town's GLB into the scene. The banks (meshes named town_bank_*) stay meshes of their own, drawn with the ground's
// material where they are slope: returned, for main.js to stand the banks' trees on them. The rest is merged, a mesh a
// material and 320 m square.
export function addTown(scene, gltf, lib, terrainMat) {
  const root = gltf.scene;
  bindMaterials(root, lib);
  drapeTerrain(root, terrainMat);
  root.updateMatrixWorld(true);
  const banks = [];
  root.traverse((o) => { if (o.isMesh && (o.name.startsWith('town_bank') || o.parent?.name.startsWith('town_bank'))) banks.push(o); });
  const group = new THREE.Group();
  group.name = 'town_banks';
  for (const m of banks) {
    const w = m.matrixWorld.clone();
    m.removeFromParent();
    m.matrix.copy(w); m.matrix.decompose(m.position, m.quaternion, m.scale);
    m.castShadow = m.receiveShadow = true;
    group.add(m);
  }
  scene.add(group);
  group.updateMatrixWorld(true);
  scene.add(mergeStatic(root, { name: 'town', chunk: 320 }));
  return banks;
}

// A car model as one mesh for the street: every part merged, its material's colour written on its corners, so that a
// passing car is one draw call (백양로's are thirty meshes each, with a driver: they pass an arm's length away; these
// pass 10 m and more off, their wheels not seen to turn). paint: 1 where the corner is body paint.
const GLASS = new THREE.Color(0.035, 0.045, 0.055);
const LAMP = { light_red: new THREE.Color(0.45, 0.02, 0.02), light_white: new THREE.Color(0.85, 0.85, 0.8), light_amber: new THREE.Color(0.85, 0.4, 0.04) };
function oneMesh(src) {
  src.updateMatrixWorld(true);
  const geos = [];
  src.traverse((o) => {
    if (!o.isMesh) return;
    const g = o.geometry.clone().applyMatrix4(o.matrixWorld);
    for (const k of Object.keys(g.attributes)) if (k !== 'position' && k !== 'normal') g.deleteAttribute(k);
    if (!g.attributes.normal) g.computeVertexNormals();
    const n = g.attributes.position.count, m = o.material, name = m.name || '';
    const c = name.startsWith('glass') ? GLASS : LAMP[name] ?? (m.map ? new THREE.Color(0.75, 0.75, 0.72) : m.color);
    const col = new Float32Array(n * 3), paint = new Float32Array(n).fill(name === 'car_paint' ? 1 : 0);
    for (let i = 0; i < n; i++) { col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    g.setAttribute('paint', new THREE.BufferAttribute(paint, 1));
    if (!g.index) g.setIndex(Array.from({ length: n }, (_, i) => i));
    geos.push(g);
  });
  const g = mergeGeometries(geos, false);
  g.computeBoundingBox();
  g.computeBoundingSphere();
  return g;
}
// that mesh in a colour of its own: the shared corners, its own colours
function painted(base, color) {
  const g = new THREE.BufferGeometry();
  g.setIndex(base.index);
  g.setAttribute('position', base.attributes.position);
  g.setAttribute('normal', base.attributes.normal);
  const col = base.attributes.color.array.slice(), p = base.attributes.paint.array;
  for (let i = 0; i < p.length; i++) if (p[i]) { col[i * 3] = color.r; col[i * 3 + 1] = color.g; col[i * 3 + 2] = color.b; }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.boundingBox = base.boundingBox; g.boundingSphere = base.boundingSphere;
  return g;
}

// the band round a city bus (blender/town.py bus): green, blue, the seat buses' red
const BUS_COLORS = ['#1e7a4c', '#1e7a4c', '#2458a8', '#b02a2e'];
const KINDS = ['sedan', 'sedan', 'sedan2', 'hatch', 'tico', 'taxi', 'taxi', 'van'];

// Cars on 성산로's six inner lanes and city buses on its two kerb lanes (campus.json town.lanes): each keeps its lane
// and its distance to the one ahead, and comes round again at the lane's start.
export class Street {
  constructor(scene, T, P, groundAt, { shadows = null } = {}) {
    const rnd = mulberry(31);
    // (dressed as the library's materials are: the soft shadows and the air, materials.js)
    const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.42, metalness: 0.15 });
    pcss(mat);
    mat.name = 'street_car';
    globalPatch(mat);
    const base = {};
    const mesh = (kind) => (base[kind] ||= oneMesh((P[`car_${kind}_far`] ?? P[kind]).scene));
    this.cars = [];
    const add = (kind, lane, s, speed, color) => {
      const root = new THREE.Mesh(painted(mesh(kind), new THREE.Color(color)), mat);
      root.castShadow = root.receiveShadow = true;
      root.name = 'street_' + kind;
      scene.add(root);
      const bb = root.geometry.boundingBox;
      this.cars.push({ root, lane, s, speed, v: speed, len: bb.max.x - bb.min.x, kind });
    };
    const lanes = (kind) => T.lanes.filter((l) => l.kind === kind).map((l) => new Path(l.pts, groundAt));
    const carLanes = lanes('car'), busLanes = lanes('bus');
    const nCars = MOBILE ? 12 : 26, nBus = P.bus ? (MOBILE ? 3 : 5) : 0;
    for (let i = 0; i < nCars; i++) {
      const kind = KINDS[Math.floor(rnd() * KINDS.length)], lane = carLanes[i % carLanes.length];
      add(kind, lane, ((i / nCars) * 2 + rnd() * 0.08) % 1 * lane.length, 11 + rnd() * 5,
        kind === 'taxi' ? '#ecebe4' : CAR_COLORS[Math.floor(rnd() * CAR_COLORS.length)]);
    }
    for (let i = 0; i < nBus; i++) {
      const lane = busLanes[i % busLanes.length];
      add('bus', lane, ((i / nBus) * 1.5 + 0.2 + rnd() * 0.1) % 1 * lane.length, 9 + rnd() * 3, BUS_COLORS[Math.floor(rnd() * BUS_COLORS.length)]);
    }
    for (const c of this.cars) shadows?.addDynamic(c.root, c.len / 2 + 1.5);
    this.p = new THREE.Vector2(); this.d = new THREE.Vector2();
  }
  // camPos: the view (three coords)
  update(dt, camPos) {
    const p = this.p, d = this.d;
    for (const c of this.cars) {
      let target = c.speed;
      for (const o of this.cars) {
        if (o === c || o.lane !== c.lane) continue;
        const gap = o.s - c.s - (o.len + c.len) / 2;
        if (gap > -1 && gap < 14) target = Math.min(target, gap < 4 ? 0 : o.v * 0.92);
      }
      c.v += (target - c.v) * Math.min(1, dt * (target < c.v ? 3 : 1));
      c.s += c.v * dt;
      if (c.s > c.lane.length) c.s = 0;
      c.lane.at(c.s, p);
      c.lane.dir(c.s, d);
      c.root.position.set(p.x, c.lane.h(c.s), -p.y);
      c.root.rotation.y = Math.atan2(d.y, d.x);             // (the models: +X forward)
      if (camPos) c.root.visible = (p.x - camPos.x) ** 2 + (p.y + camPos.z) ** 2 < SEEN * SEEN;
    }
  }
}
