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

// Cars on 성산로's six inner lanes and city buses on its two kerb lanes (campus.json town.lanes), and on 연세로 and
// through 신촌 로터리 (tools/sinchon_rotary.py: lanes with `stops`, round the island). Each keeps its lane and its
// distance to whatever is ahead of it (a car of another lane merging or turning, the walker), waits at its stop
// lines while its signal is red, and comes round again at the lane's start.
const AHEAD = 16;          // metres a car looks ahead
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
      this.cars.push({ root, lane, s, speed, v: speed, len: bb.max.x - bb.min.x, kind, x: 0, y: 0, dx: 1, dy: 0 });
    };
    const path = (l) => { const p = new Path(l.pts, groundAt); p.stops = l.stops || []; return p; };
    const lanes = (kind, junction) => T.lanes.filter((l) => l.kind === kind && !!l.stops === junction).map(path);
    const carLanes = lanes('car', false), busLanes = lanes('bus', false), rotLanes = lanes('car', true);
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
    // (신촌 로터리: two or three a lane, a bus now and then; their own stream, so 성산로's stay as they were)
    const r2 = mulberry(57);
    const perLane = MOBILE ? 1 : 3;
    rotLanes.forEach((lane, li) => {
      for (let i = 0; i < perLane; i++) {
        const bus = P.bus && r2() < 0.18;
        const kind = bus ? 'bus' : KINDS[Math.floor(r2() * KINDS.length)];
        add(kind, lane, ((i + r2() * 0.5) / perLane) * lane.length, bus ? 9 + r2() * 2 : 10 + r2() * 4,
          bus ? BUS_COLORS[Math.floor(r2() * BUS_COLORS.length)] : kind === 'taxi' ? '#ecebe4' : CAR_COLORS[Math.floor(r2() * CAR_COLORS.length)]);
      }
    });
    for (const c of this.cars) shadows?.addDynamic(c.root, c.len / 2 + 1.5);
    this.p = new THREE.Vector2(); this.d = new THREE.Vector2();
    // the signals (campus.json town.signals): per group a cycle of its phases' greens, each followed by amber and
    // all red; t runs on from the page's start
    const G = T.signals?.groups ?? [];
    this.groups = G.map((g, k) => {
      const cyc = g.green.reduce((a, v) => a + v + T.signals.amber + T.signals.red, 0);
      return { green: g.green, cyc, t: k * 7.0 };
    });
    this.amber = T.signals?.amber ?? 3; this.red = T.signals?.red ?? 3;
    this.heads = T.heads ? new SignalHeads(scene, T.heads, groundAt) : null;
  }
  // the light a phase of a group shows now: 0 red, 1 amber, 2 green
  light(g, ph) {
    const G = this.groups[g];
    if (!G) return 2;
    let t = G.t % G.cyc;
    for (let k = 0; k < G.green.length; k++) {
      const span = G.green[k] + this.amber + this.red;
      if (t < span) return k !== ph ? 0 : t < G.green[k] ? 2 : t < G.green[k] + this.amber ? 1 : 0;
      t -= span;
    }
    return 0;
  }
  // camPos: the view (three coords); walker: {x, y} in the campus frame (cars stop short of them)
  update(dt, camPos, walker = null) {
    const p = this.p, d = this.d;
    for (const g of this.groups) g.t += dt;
    for (const c of this.cars) {
      c.lane.at(c.s, p); c.lane.dir(c.s, d);
      c.x = p.x; c.y = p.y; c.dx = d.x; c.dy = d.y;
    }
    const n = this.cars.length;
    for (let i = 0; i < n; i++) {
      const c = this.cars[i];
      let target = c.speed;
      for (let j = 0; j < n; j++) {
        if (j === i) continue;
        const o = this.cars[j];
        if (o.lane === c.lane) {
          const gap = o.s - c.s - (o.len + c.len) / 2;
          if (gap > -1 && gap < 14) target = Math.min(target, gap < 4 ? 0 : o.v * 0.92);
          continue;
        }
        if (!c.lane.stops.length && !o.lane.stops.length) continue;      // (성산로's lanes keep apart)
        const rx = o.x - c.x, ry = o.y - c.y;
        const along = rx * c.dx + ry * c.dy;
        if (along < 0.5 || along > AHEAD + o.len) continue;
        const lat = Math.abs(rx * c.dy - ry * c.dx);
        if (lat > 2.0) continue;
        if (o.dx * c.dx + o.dy * c.dy < -0.3) continue;                 // (coming the other way: its own side)
        // side by side into one lane: the one behind on its own lane, or the later in the list, gives way
        const back = (c.x - o.x) * o.dx + (c.y - o.y) * o.dy;
        if (back > 0.5 && back < AHEAD && j > i) continue;
        const gap = along - (o.len + c.len) / 2;
        target = Math.min(target, gap < 3 ? 0 : o.v * 0.9 * Math.min(1, gap / 10));
      }
      if (walker) {
        const rx = walker.x - c.x, ry = walker.y - c.y;
        const along = rx * c.dx + ry * c.dy;
        if (along > 0 && along < AHEAD && Math.abs(rx * c.dy - ry * c.dx) < 1.8) {
          const gap = along - c.len / 2 - 1.5;
          target = Math.min(target, gap < 1 ? 0 : c.speed * Math.min(1, gap / 10));
        }
      }
      for (const [s, g, ph] of c.lane.stops) {               // red ahead: stop at the line (amber: only if well short)
        const gap = s - c.s - c.len / 2;
        if (gap < -0.5 || gap > 30) continue;
        const l = this.light(g, ph);
        if (l === 2 || (l === 1 && gap < 6)) continue;
        target = Math.min(target, gap < 0.8 ? 0 : c.speed * Math.min(1, gap / 22));
      }
      c.v += (target - c.v) * Math.min(1, dt * (target < c.v ? 3 : 1));
      if (c.v < 0.05 && target === 0) c.v = 0;
      c.s += c.v * dt;
      if (c.s > c.lane.length) c.s = 0;
      c.lane.at(c.s, p);
      c.lane.dir(c.s, d);
      c.root.position.set(p.x, c.lane.h(c.s), -p.y);
      c.root.rotation.y = Math.atan2(d.y, d.x);             // (the models: +X forward)
      if (camPos) c.root.visible = (p.x - camPos.x) ** 2 + (p.y + camPos.z) ** 2 < SEEN * SEEN;
    }
    this.heads?.update(this, camPos);
  }
}

// 신촌 로터리's signals (campus.json town.heads: [x, y, the way the lamps face, group, phase, the mast arm's reach]):
// a grey pole at the kerb, a mast arm over the lanes, a box of three lamps (red, amber, green, the Korean order left
// to right) lit as the cycle goes. One merged mesh for the poles and boxes, the lamps a mesh each colour whose
// instances turn on and off.
const LAMP_ON = { r: new THREE.Color(1.0, 0.08, 0.05), a: new THREE.Color(1.0, 0.55, 0.05), g: new THREE.Color(0.1, 0.95, 0.55) };
class SignalHeads {
  constructor(scene, heads, groundAt) {
    const geos = [];
    const grey = new THREE.MeshStandardMaterial({ color: 0x55595e, roughness: 0.6, metalness: 0.3 });
    pcss(grey);
    globalPatch(grey);
    this.heads = heads;
    this.lamps = { r: [], a: [], g: [] };
    const lampGeo = new THREE.CircleGeometry(0.13, 12);
    const m4 = new THREE.Matrix4();
    this.mats = {};
    this.meshes = {};
    for (const k of ['r', 'a', 'g']) {
      this.mats[k] = new THREE.MeshBasicMaterial({ color: 0xffffff });
      this.meshes[k] = new THREE.InstancedMesh(lampGeo, this.mats[k], heads.length);
      this.meshes[k].instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(heads.length * 3), 3);
      this.meshes[k].frustumCulled = false;
    }
    const q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(1, 1, 1), v = new THREE.Vector3();
    heads.forEach(([x, y, face, , , reach], i) => {
      const z = groundAt(x, y);
      const fx = Math.cos(face), fy = Math.sin(face);           // the way the lamps look (at the cars coming)
      const ax = fy, ay = -fx;                                  // the mast arm reaches out over the lanes: to the right
      const pole = new THREE.CylinderGeometry(0.11, 0.13, 6.2, 8).translate(x, z + 3.1, -y);
      const arm = new THREE.BoxGeometry(reach, 0.12, 0.12);
      arm.rotateY(Math.atan2(ay, ax)).translate(x + ax * reach / 2, z + 5.9, -(y + ay * reach / 2));
      const hx = x + ax * reach * 0.8, hy = y + ay * reach * 0.8;
      const box = new THREE.BoxGeometry(1.15, 0.42, 0.3);
      box.rotateY(Math.atan2(ay, ax)).translate(hx, z + 5.6, -hy);
      geos.push(pole, arm, box);
      ['r', 'a', 'g'].forEach((k, j) => {
        const o = (j - 1) * 0.36;                               // red at the left as the driver sees it
        v.set(hx - ax * o + fx * 0.16, z + 5.6, -(hy - ay * o + fy * 0.16));
        e.set(0, Math.atan2(fx, -fy), 0);
        q.setFromEuler(e);
        m4.compose(v, q, sc);
        this.meshes[k].setMatrixAt(i, m4);
      });
    });
    const g = mergeGeometries(geos.map((x) => { x.deleteAttribute('uv'); return x; }), false);
    const frame = new THREE.Mesh(g, grey);
    frame.castShadow = frame.receiveShadow = true;
    frame.name = 'town_signals';
    scene.add(frame);
    for (const k in this.meshes) { this.meshes[k].name = 'town_signal_' + k; scene.add(this.meshes[k]); }
    this.off = new THREE.Color(0.06, 0.06, 0.06);
  }
  update(street) {
    this.heads.forEach(([, , , g, ph], i) => {
      const l = street.light(g, ph);
      this.meshes.r.setColorAt(i, l === 0 ? LAMP_ON.r : this.off);
      this.meshes.a.setColorAt(i, l === 1 ? LAMP_ON.a : this.off);
      this.meshes.g.setColorAt(i, l === 2 ? LAMP_ON.g : this.off);
    });
    for (const k in this.meshes) this.meshes[k].instanceColor.needsUpdate = true;
  }
}
