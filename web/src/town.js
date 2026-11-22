// 정문 밖 (campus.json `town`, tools/gate_town.py, blender/town.py): 성산로, the 경의선's bank and bridge, the town south of
// it. The town's models, and the cars and city buses that pass on 성산로.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { bindMaterials, mergeStatic } from './world.js';
import { drapeTerrain } from './terrain.js';
import { Path, CAR_COLORS } from './life.js';
import { pcss, globalPatch } from './materials.js';
import { oneMesh, painted, carMaterial } from './carmesh.js';
import { MOBILE, mulberry } from './util.js';

const SEEN = 380;          // cars farther than this from the view are not drawn
const WAKE = SEEN + 20;    // nor moved: they stand where they were till the view comes back (update below)

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
  scene.add(mergeStatic(root, { name: 'town', chunk: 320, split: true }));
  return banks;
}

// the band round a city bus (blender/town.py bus): green, blue, the seat buses' red
const BUS_COLORS = ['#1e7a4c', '#1e7a4c', '#2458a8', '#b02a2e'];
const KINDS = ['sedan', 'sedan', 'sedan2', 'hatch', 'tico', 'taxi', 'taxi', 'van'];

// Cars on 성산로's eight inner lanes and city buses on its two kerb lanes (campus.json town.lanes), and on 연세로 and
// through 신촌 로터리 (tools/sinchon_rotary.py: lanes with `stops`, round the island). Each keeps its lane and its
// distance to whatever is ahead of it (a car of another lane merging or turning, the walker), waits at its stop
// lines while its signal is red, and comes round again at the lane's start.
const AHEAD = 16;          // metres a car looks ahead
export class Street {
  constructor(scene, T, P, groundAt, { shadows = null } = {}) {
    this.scene = scene;
    const rnd = mulberry(31);
    const mat = carMaterial();
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
    const path = (l) => { const p = new Path(l.pts, groundAt); p.stops = l.stops || []; p.rot = !!l.stops && !l.ss; return p; };
    // (the junction's lanes keep an eye on one another; 성산로's (ss) only wait at their signal since 2026-11-16)
    const lanes = (kind, junction) => T.lanes.filter((l) => l.kind === kind && (!!l.stops && !l.ss) === junction).map(path);
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
    for (const c of this.cars) {                               // (where each stands before its first move)
      c.lane.at(c.s, this.p); c.lane.dir(c.s, this.d);
      c.x = this.p.x; c.y = this.p.y; c.dx = this.d.x; c.dy = this.d.y;
      c.awake = true;
    }
    // the signals (campus.json town.signals): per group a cycle of its phases' greens, each followed by amber and
    // all red; t runs on from the page's start
    const G = T.signals?.groups ?? [];
    this.groups = G.map((g, k) => {
      const cyc = g.green.reduce((a, v) => a + v + T.signals.amber + T.signals.red, 0);
      return { green: g.green, cyc, t: k * 7.0 };
    });
    this.amber = T.signals?.amber ?? 3; this.red = T.signals?.red ?? 3;
    this.heads = T.heads ? new SignalHeads(scene, T.heads, groundAt) : null;
    this.peds = T.peds?.length ? new PedHeads(scene, T.peds, groundAt) : null;
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
  // the walkers' light a crossing shows now (its group, the phases whose green lets them go, bits): 0 red, 2 green,
  // 3 green blinking (its last 6 s). A run of such phases is one green, through the amber and all red between them
  walk(g, mask) {
    const G = this.groups[g];
    if (!G) return 0;
    const n = G.green.length, span = (k) => G.green[k] + this.amber + this.red;
    let t = G.t % G.cyc, k = 0;
    while (k < n - 1 && t >= span(k)) { t -= span(k); k++; }
    if (!(mask >> k & 1)) return 0;
    // (t: seconds into phase k; what is left: to the end of the last walking phase's green in the run from k on)
    let left = G.green[k] - t, j = k;
    for (let c = 1; c < n && (mask >> ((j + 1) % n) & 1); c++) { j = (j + 1) % n; left += this.amber + this.red + G.green[j]; }
    if (left <= 0) return 0;
    return left < 6 ? 3 : 2;
  }
  // camPos: the view (three coords); walker: {x, y} in the campus frame (cars stop short of them)
  // hidden: no car about (the running game, race.js): all out of the scene, standing still where they were
  set hidden(on) {
    this._hidden = on;
    for (const c of this.cars) {
      if (on && c.root.parent) this.scene.remove(c.root);
      else if (!on && !c.root.parent) this.scene.add(c.root);
    }
  }
  get hidden() { return !!this._hidden; }

  update(dt, camPos, walker = null) {
    if (this._hidden) return;
    const p = this.p, d = this.d;
    for (const g of this.groups) g.t += dt;
    // Only the cars within WAKE of the view move, and only they look out for one another: on the campus, north of the
    // gate, that is a few of 성산로's or none, where all 67 once looked at all 67 every frame. A sleeping car stands
    // unseen where it was; one coming awake on another (both stood or ran on past WAKE) waits behind it.
    for (const c of this.cars) {
      c.awake = !camPos || (c.x - camPos.x) ** 2 + (c.y + camPos.z) ** 2 < WAKE * WAKE;
      if (!c.awake) { c.root.visible = false; continue; }
      c.lane.at(c.s, p); c.lane.dir(c.s, d);
      c.x = p.x; c.y = p.y; c.dx = d.x; c.dy = d.y;
    }
    const n = this.cars.length;
    for (let i = 0; i < n; i++) {
      const c = this.cars[i];
      if (!c.awake) continue;
      let target = c.speed;
      for (let j = 0; j < n; j++) {
        if (j === i) continue;
        const o = this.cars[j];
        if (!o.awake) continue;
        if (o.lane === c.lane) {
          // (s on round: one just come round to the lane's start is still ahead of one about to, not 800 m behind it)
          let ds = o.s - c.s;
          if (ds < -c.lane.length / 2) ds += c.lane.length;
          const gap = ds - (o.len + c.len) / 2;
          if (gap > -1 && gap < 14) target = Math.min(target, gap < 4 ? 0 : o.v * 0.92);
          continue;
        }
        if (!c.lane.rot && !o.lane.rot) continue;                         // (성산로's lanes keep apart)
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
      if (c.s > c.lane.length) {
        // round to the lane's start, but not onto a car standing or running there (one of a lane that starts at the same
        // place: 연세로's under the bridge): it waits at the far end till the start is clear
        const q = c.lane.pts[0];
        const busy = this.cars.some((o) => o !== c && o.awake && o.s < (o.len + c.len) / 2 + 2 &&
          (o.lane === c.lane || o.lane.pts[0].distanceToSquared(q) < 2.0));
        if (busy) { c.s = c.lane.length; c.v = 0; } else c.s = 0;
      }
      c.lane.at(c.s, p);
      c.lane.dir(c.s, d);
      c.root.position.set(p.x, c.lane.h(c.s), -p.y);
      c.root.rotation.y = Math.atan2(d.y, d.x);             // (the models: +X forward)
      if (camPos) c.root.visible = (p.x - camPos.x) ** 2 + (p.y + camPos.z) ** 2 < SEEN * SEEN;
    }
    this.heads?.update(this, camPos);
    this.peds?.update(this, camPos);
  }
}

// The walkers' signals at the crossings (campus.json town.peds: [x, y, the way the lamps face, group, phases]): a grey
// pole with a pointed cap at each end of a zebra, on its side at 2.4 - 3.1 m a black box of two lamps under hoods, the
// red standing figure over the green walking one (서울연구원 50377, 1995.10; 30197, 1996.10). The figures: drawn once on
// a canvas, lit by each instance's colour
const PED_ON = { r: new THREE.Color(1.0, 0.12, 0.06), g: new THREE.Color(0.2, 1.0, 0.62) };
function figureTex(walking) {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const x = c.getContext('2d');
  x.fillStyle = '#080808';
  x.fillRect(0, 0, 64, 64);
  x.fillStyle = '#fff'; x.strokeStyle = '#fff'; x.lineCap = 'round'; x.lineWidth = 6;
  x.beginPath(); x.arc(32, 13, 6, 0, Math.PI * 2); x.fill();          // (the head)
  const L = (pts) => { x.beginPath(); x.moveTo(...pts[0]); for (const p of pts.slice(1)) x.lineTo(...p); x.stroke(); };
  if (walking) {
    L([[32, 22], [29, 40]]); L([[29, 40], [21, 56]]); L([[29, 40], [38, 49], [41, 57]]);
    L([[31, 26], [22, 36]]); L([[31, 26], [40, 33]]);
  } else {
    x.lineWidth = 8; L([[32, 22], [32, 40]]); x.lineWidth = 6;
    L([[29, 40], [28, 57]]); L([[35, 40], [36, 57]]); L([[28, 25], [24, 41]]); L([[36, 25], [40, 41]]);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
// the lamps stand still: one sphere round the red ones (every head has one; the unused arrow lamps are scaled to
// nothing at the origin) culls each set with the view, so that they are not drawn behind it
function cullAsOne(meshes) {
  meshes.r.computeBoundingSphere();
  const s = meshes.r.boundingSphere;
  s.radius += 1;
  for (const k in meshes) meshes[k].boundingSphere = s.clone();
}
class PedHeads {
  constructor(scene, peds, groundAt) {
    const grey = new THREE.MeshStandardMaterial({ color: 0x8a8e92, roughness: 0.55, metalness: 0.35 });
    const black = new THREE.MeshStandardMaterial({ color: 0x0c0c0d, roughness: 0.6 });
    for (const m of [grey, black]) { pcss(m); globalPatch(m); }
    this.peds = peds;
    const poles = [], boxes = [];
    this.meshes = {};
    const lampGeo = new THREE.PlaneGeometry(0.25, 0.25);
    for (const k of ['r', 'g']) {
      const mat = new THREE.MeshBasicMaterial({ map: figureTex(k === 'g') });
      this.meshes[k] = new THREE.InstancedMesh(lampGeo, mat, peds.length);
      this.meshes[k].instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(peds.length * 3), 3);
    }
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), one = new THREE.Vector3(1, 1, 1), v = new THREE.Vector3();
    peds.forEach(([x, y, face], i) => {
      const z = groundAt(x, y), fx = Math.cos(face), fy = Math.sin(face), rot = Math.atan2(fy, fx);   // (box x: out the face)
      poles.push(new THREE.CylinderGeometry(0.06, 0.07, 3.3, 8).translate(x, z + 1.65, -y));
      poles.push(new THREE.ConeGeometry(0.075, 0.22, 8).translate(x, z + 3.41, -y));
      const hx = x + fx * 0.2, hy = y + fy * 0.2, hz = z + 2.75;       // (the box on the pole's side, towards the street)
      const add = (g, a, up, b) => { g.rotateY(rot); g.translate(hx + fx * a, hz + up, -(hy + fy * a)); boxes.push(g); };
      add(new THREE.BoxGeometry(0.2, 0.66, 0.34), 0, 0, 0);
      for (const up of [0.16, -0.16]) add(new THREE.BoxGeometry(0.16, 0.02, 0.32), 0.17, up + 0.14, 0);   // (the hoods)
      for (const up of [0.16, -0.16]) for (const s of [-1, 1]) {
        const g = new THREE.BoxGeometry(0.16, 0.26, 0.015);
        g.translate(0, 0, s * 0.155);
        add(g, 0.17, up + 0.01, 0);
      }
      add(new THREE.BoxGeometry(0.12, 0.06, 0.06), -0.14, 0.2, 0);        // (its brackets)
      add(new THREE.BoxGeometry(0.12, 0.06, 0.06), -0.14, -0.2, 0);
      ['r', 'g'].forEach((k, j) => {
        v.set(hx + fx * 0.102, hz + (j === 0 ? 0.16 : -0.16), -(hy + fy * 0.102));
        e.set(0, Math.atan2(fx, -fy), 0);
        q.setFromEuler(e);
        m4.compose(v, q, one);
        this.meshes[k].setMatrixAt(i, m4);
      });
    });
    cullAsOne(this.meshes);
    const strip = (g) => { g.deleteAttribute('uv'); return g; };
    const pm = new THREE.Mesh(mergeGeometries(poles.map(strip), false), grey);
    const bm = new THREE.Mesh(mergeGeometries(boxes.map(strip), false), black);
    pm.castShadow = pm.receiveShadow = bm.castShadow = bm.receiveShadow = true;
    pm.name = 'town_ped_poles'; bm.name = 'town_ped_boxes';
    scene.add(pm, bm);
    for (const k in this.meshes) { this.meshes[k].name = 'town_ped_' + k; scene.add(this.meshes[k]); }
    this.frame = [pm, bm];
    this.off = new THREE.Color(0.07, 0.07, 0.07);
    this.cx = peds.reduce((a, h) => a + h[0], 0) / peds.length;
    this.cy = peds.reduce((a, h) => a + h[1], 0) / peds.length;
    this.reach = Math.max(...peds.map(([x, y]) => Math.hypot(x - this.cx, y - this.cy))) + SEEN;
    this.last = peds.map(() => -1);
    this.t = 0;
  }
  update(street, camPos) {
    const near = !camPos || (this.cx - camPos.x) ** 2 + (this.cy + camPos.z) ** 2 < this.reach * this.reach;
    for (const m of this.frame) m.visible = near;
    for (const k in this.meshes) this.meshes[k].visible = near;
    if (!near) return;
    const blink = (performance.now() % 1000) < 500;
    let changed = false;
    this.peds.forEach(([, , , g, mask], i) => {
      let l = street.walk(g, mask);
      if (l === 3) l = blink ? 2 : 1;                   // (blinking: on, then dark)
      if (l === this.last[i]) return;
      this.last[i] = l;
      changed = true;
      this.meshes.r.setColorAt(i, l === 0 ? PED_ON.r : this.off);
      this.meshes.g.setColorAt(i, l === 2 ? PED_ON.g : this.off);
    });
    if (changed) for (const k in this.meshes) this.meshes[k].instanceColor.needsUpdate = true;
  }
}

// 신촌 로터리's signals (campus.json town.heads: [x, y, the way the lamps face, group, phase, the mast arm's reach,
// lamps, the head's m along the arm (else 0.8 of the reach)]): a grey pole at the kerb, a mast arm over the lanes, a box of three lamps (red, amber, green, the Korean
// order left to right) lit as the cycle goes; the junction's (lamps 4: 서울연구원 52007 · 52111 · 52139, 1996) a box
// of four, the left arrow between amber and green, always dark (the game's cycle has no turn of its own). One merged
// mesh for the poles and boxes, the lamps a mesh each colour whose instances turn on and off.
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
    for (const k of ['r', 'a', 'g', 'l']) {
      this.mats[k] = new THREE.MeshBasicMaterial({ color: 0xffffff });
      this.meshes[k] = new THREE.InstancedMesh(lampGeo, this.mats[k], heads.length);
      this.meshes[k].instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(heads.length * 3), 3);
    }
    const q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(1, 1, 1), v = new THREE.Vector3();
    const none = new THREE.Matrix4().makeScale(0, 0, 0);
    const dark = new THREE.Color(0.06, 0.06, 0.06);
    heads.forEach(([x, y, face, , , reach, nl, at], i) => {
      const z = groundAt(x, y);
      const fx = Math.cos(face), fy = Math.sin(face);           // the way the lamps look (at the cars coming)
      const ax = fy, ay = -fx;                                  // the mast arm reaches out over the lanes: to the right
      const pole = new THREE.CylinderGeometry(0.11, 0.13, 6.2, 8).translate(x, z + 3.1, -y);
      const arm = new THREE.BoxGeometry(Math.abs(reach), 0.12, 0.12);   // (a negative reach: out to the left)
      arm.rotateY(Math.atan2(ay, ax)).translate(x + ax * reach / 2, z + 5.9, -(y + ay * reach / 2));
      const hd = at === undefined ? reach * 0.8 : Math.sign(reach) * at;
      const hx = x + ax * hd, hy = y + ay * hd;
      const four = nl === 4;
      const box = new THREE.BoxGeometry(four ? 1.51 : 1.15, 0.42, 0.3);
      box.rotateY(Math.atan2(ay, ax)).translate(hx, z + 5.6, -hy);
      geos.push(pole, arm, box);
      (four ? ['r', 'a', 'l', 'g'] : ['r', 'a', 'g']).forEach((k, j, ks) => {
        const o = (j - (ks.length - 1) / 2) * 0.36;             // red at the left as the driver sees it
        v.set(hx - ax * o + fx * 0.16, z + 5.6, -(hy - ay * o + fy * 0.16));
        e.set(0, Math.atan2(fx, -fy), 0);
        q.setFromEuler(e);
        m4.compose(v, q, sc);
        this.meshes[k].setMatrixAt(i, m4);
      });
      if (!four) this.meshes.l.setMatrixAt(i, none);
      this.meshes.l.setColorAt(i, dark);
    });
    cullAsOne(this.meshes);
    const g = mergeGeometries(geos.map((x) => { x.deleteAttribute('uv'); return x; }), false);
    const frame = new THREE.Mesh(g, grey);
    frame.castShadow = frame.receiveShadow = true;
    frame.name = 'town_signals';
    scene.add(frame);
    for (const k in this.meshes) { this.meshes[k].name = 'town_signal_' + k; scene.add(this.meshes[k]); }
    this.off = new THREE.Color(0.06, 0.06, 0.06);
    // (where the heads stand, for the update's distance test)
    this.frame = frame;
    this.cx = heads.reduce((a, h) => a + h[0], 0) / heads.length;
    this.cy = heads.reduce((a, h) => a + h[1], 0) / heads.length;
    this.reach = Math.max(...heads.map(([x, y]) => Math.hypot(x - this.cx, y - this.cy))) + SEEN;
    this.last = heads.map(() => -1);
  }
  // Out of sight (the view farther than SEEN from every head: they are thumb-wide there) the poles and lamps are not
  // drawn and the lamps keep their colours; in sight a lamp's colour goes up only when its light has changed.
  update(street, camPos) {
    const near = !camPos || (this.cx - camPos.x) ** 2 + (this.cy + camPos.z) ** 2 < this.reach * this.reach;
    this.frame.visible = near;
    for (const k in this.meshes) this.meshes[k].visible = near;
    if (!near) return;
    let changed = false;
    this.heads.forEach(([, , , g, ph], i) => {
      const l = street.light(g, ph);
      if (l === this.last[i]) return;
      this.last[i] = l;
      changed = true;
      this.meshes.r.setColorAt(i, l === 0 ? LAMP_ON.r : this.off);
      this.meshes.a.setColorAt(i, l === 1 ? LAMP_ON.a : this.off);
      this.meshes.g.setColorAt(i, l === 2 ? LAMP_ON.g : this.off);
    });
    if (changed) for (const k in this.meshes) this.meshes[k].instanceColor.needsUpdate = true;
  }
}
