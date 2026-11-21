// 캠퍼스 달리기 (the title card's second game, the settings card's 「캠퍼스 달리기」): a time trial over one of three
// courses. Each course is a row of gates on the ground (campus x, y); the first is the start line, the last the
// finish. The walker always runs meanwhile (Player.autoRun: Shift changes nothing) and goes from gate to gate along
// the arrows on the ground (the course's legs) and the HUD's arrow, which points at the next one. Every run is kept in this browser per course, with the times at each
// gate, so the next run shows how far ahead of (or behind) the best one it is.
// Loaded only when the course picker opens (main.js).
import * as THREE from 'three';
import { HERO, STUDENTS, crowdLook, locomotion } from './characters.js';
import { safeGet, safeSet, wrapAngle } from './util.js';
import './race.css';
import { Run, RankBox } from './rank.js';
import { raceBoard, RACE } from './rankrules.js';

import { COURSES, courseOf, lineOf, lengthOf } from './courses.js';
export { COURSES, courseOf, lengthOf };

const COUNT = 3;
const ARROW_GAP = 4.5, ARROW_CLEAR = 4.5;   // the ground's arrows: one every ARROW_GAP m, none within ARROW_CLEAR of a gate
const GATE_R = RACE.GATE_R, GATE_H = 2.6;      // a gate is passed within GATE_R of its middle (and 5 m in height)
const KEY = 'y97-run-records', MAX = 50;
// the other runners (nobody else is about meanwhile: main.js hides the crowd and the cars): jogging along the course,
// some the other way; one farther than RUN_FAR from the walker comes back RUN_AHEAD m ahead of them along the course
const RUNNERS = matchMedia('(pointer: coarse)').matches ? 4 : 6, RUN_FAR = 90, RUN_AHEAD = [45, 85];

// ---------------------------------------------------------------- records (this browser only)
export function loadAll() {
  let all;
  try { all = JSON.parse(safeGet(KEY) || '{}'); } catch { all = {}; }
  return all && typeof all === 'object' && !Array.isArray(all) ? all : {};
}
export function records(id) {
  const list = loadAll()[id];
  return (Array.isArray(list) ? list : []).filter((r) => r && Number.isFinite(r.time)).sort((a, b) => a.time - b.time || a.at - b.at);
}
function addRecord(id, rec) {
  const all = loadAll(), list = records(id);
  list.push(rec);
  list.sort((a, b) => a.time - b.time || a.at - b.at);
  all[id] = list.slice(0, MAX);
  safeSet(KEY, JSON.stringify(all));
  return { rank: list.indexOf(rec) + 1, total: list.length };
}
export const fmt = (s) => {
  const m = Math.floor(s / 60), r = s - m * 60;
  return `${m}:${r.toFixed(2).padStart(5, '0')}`;
};
const fmtGap = (d) => `${d < 0 ? '−' : '+'}${Math.abs(d).toFixed(2)}`;
const day = (ms) => { const d = new Date(ms); return `${d.getMonth() + 1}/${d.getDate()}`; };

// ---------------------------------------------------------------- the gates' look
// a ring of light standing on the ground (fading upwards), and a number over it
function ringTexture() {
  const c = document.createElement('canvas');
  c.width = 4; c.height = 64;
  const g = c.getContext('2d'), gr = g.createLinearGradient(0, 64, 0, 0);
  gr.addColorStop(0, 'rgba(255,255,255,0.95)');
  gr.addColorStop(0.15, 'rgba(255,255,255,0.55)');
  gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 4, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
function flagTexture() {           // the finish: a chequered ring
  const c = document.createElement('canvas');
  c.width = 128; c.height = 64;
  const g = c.getContext('2d');
  for (let i = 0; i < 16; i++) for (let j = 0; j < 8; j++) { g.fillStyle = (i + j) % 2 ? '#111' : '#fff'; g.fillRect(i * 8, j * 8, 8, 8); }
  const fade = g.createLinearGradient(0, 0, 0, 64);
  fade.addColorStop(0, 'rgba(0,0,0,1)'); fade.addColorStop(0.55, 'rgba(0,0,0,0)');
  g.globalCompositeOperation = 'destination-out';
  g.fillStyle = fade; g.fillRect(0, 0, 128, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = THREE.RepeatWrapping; t.repeat.set(4, 1);
  return t;
}
function labelTexture(text, bg) {
  const c = document.createElement('canvas');
  c.width = 128; c.height = 128;
  const g = c.getContext('2d');
  g.fillStyle = bg; g.beginPath(); g.arc(64, 64, 56, 0, Math.PI * 2); g.fill();
  g.lineWidth = 8; g.strokeStyle = '#fff'; g.stroke();
  g.fillStyle = '#fff'; g.font = `700 ${text.length > 2 ? 34 : 60}px "Noto Sans KR", sans-serif`;
  g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, 64, 68);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// a chevron lying on the ground, pointing to -z (campus +y) before it is turned
function arrowGeometry() {
  const s = new THREE.Shape();
  s.moveTo(0, 0.8); s.lineTo(1.1, -0.3); s.lineTo(1.1, -0.95); s.lineTo(0, 0.15); s.lineTo(-1.1, -0.95); s.lineTo(-1.1, -0.3); s.closePath();
  const g = new THREE.ShapeGeometry(s);
  g.rotateX(-Math.PI / 2);
  return g;
}
const GOLD = new THREE.Color(0xffc83a), PALE = new THREE.Color(1, 1, 0.9);

export class Race {
  // groundAt(x, y): the walk's height there; ensure(x, y): chunks.ensure (a promise while the halls there come in);
  // onBegin(msg): main.js takes the walk on (title card off, settings card shut); onQuit: back to the walk
  constructor({ scene, camera, player, sound, groundAt, ensure, onBegin, onQuit, cast, shadows, blobs }) {
    Object.assign(this, { scene, camera, player, sound, groundAt, ensure, onBegin, onQuit, cast, shadows, blobs });
    this.runners = [];
    this.state = 'off';                 // off | count | play | done
    this.group = new THREE.Group();
    this.group.name = 'race_gates';
    this.ringTex = ringTexture();
    this.flagTex = flagTexture();
    this.arrowGeo = arrowGeometry();
    const mat = (opacity) => new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity, depthWrite: false, side: THREE.DoubleSide,
      polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2, toneMapped: false });
    this.arrowOn = mat(1);
    this.arrowDim = mat(0.5);
    this._dir = new THREE.Vector3();
    this._o = new THREE.Object3D();
    this._c = new THREE.Color();
    addEventListener('keydown', (e) => {
      if (e.code !== 'Escape') return;
      if (this.pickOpen) { e.stopImmediatePropagation(); this.closePicker(); }
      else if (this.resultsOpen) { e.stopImmediatePropagation(); this.stop(); }
    }, true);
  }

  get on() { return this.state !== 'off'; }

  // ---------------------------------------------------------------- the course picker
  openPicker() {
    let el = this.pickEl;
    if (!el) {
      el = this.pickEl = document.createElement('div');
      el.id = 'racepick';
      el.innerHTML = '<div><h2>캠퍼스 달리기</h2><p class="lead">코스를 고르세요. 문(링)을 차례로 지나 결승선까지 달려요.</p>'
        + '<ul class="courses"></ul><p class="how"></p><button type="button" class="close">닫기</button></div>';
      document.body.appendChild(el);
      el.querySelector('.close').addEventListener('click', () => this.closePicker());
      el.addEventListener('click', (e) => { if (e.target === el) this.closePicker(); });
    }
    const ul = el.querySelector('.courses');
    ul.replaceChildren(...COURSES.map((c) => {
      const li = document.createElement('li'), best = records(c.id)[0];
      li.innerHTML = `<button type="button"><b></b><span class="desc"></span><span class="meta"></span></button>`;
      li.querySelector('b').textContent = c.name;
      li.querySelector('.desc').textContent = c.desc;
      li.querySelector('.meta').textContent = `약 ${Math.round(lengthOf(c) / 10) * 10} m · 문 ${c.gates.length - 2}개와 결승${best ? ` · 최고 ${fmt(best.time)}` : ''}`;
      li.querySelector('button').addEventListener('click', (e) => { e.currentTarget.blur(); this.closePicker(); this.start(c.id); });
      return li;
    }));
    el.querySelector('.how').textContent = matchMedia('(pointer: coarse)').matches
      ? '달리는 동안은 화면 왼쪽을 밀기만 해도 늘 뛰어요. 바닥의 화살표를 따라가면 다음 문이 나와요.'
      : '달리는 동안은 ↑(W)만 눌러도 늘 뛰어요. Shift는 누르지 않아도 돼요. ←→(A·D)로 방향을 바꾸고, 바닥의 화살표를 따라가면 다음 문이 나와요.';
    el.hidden = false;
    el.querySelector('.courses button')?.focus({ preventScroll: true });
  }
  closePicker() { if (this.pickEl) this.pickEl.hidden = true; }
  get pickOpen() { return !!this.pickEl && !this.pickEl.hidden; }

  // ---------------------------------------------------------------- a run
  async start(id = this.course?.id) {
    const c = courseOf(id);
    if (!c || this.starting) return;
    this.starting = true;
    this.run?.fail('다시 시작');
    let run;
    try {
      const [sx, sy] = c.gates[0];
      [run] = await Promise.all([Run.open(raceBoard(c.id)), this.ensure?.(sx, sy)]);
    } finally { this.starting = false; }
    this.run = run;
    this.results(false);
    this.course = c;
    this.best = records(c.id)[0] || null;
    this.buildGates(c);
    const pl = this.player, [sx, sy] = c.gates[0], [nx, ny] = c.gates[1];
    this.onBegin?.(c.name);          // (how to run: the hint under the HUD)
    pl.teleport(sx, sy, Math.atan2(-(nx - sx), ny - sy));
    pl.cam.ready = false;
    pl.autoRun = true;
    pl.enabled = false;
    pl.keys.clear();
    pl.stick.set(0, 0);
    pl.speed = 0;
    this.next = 1;
    this.splits = [];
    this.time = 0;
    this.state = 'count';
    this.clock = COUNT;
    this.shown = 0;
    this.placeRunners(c);
    this.hudEl().hidden = false;
    this.hint(true);
    this.flash('');
    this.showGates();
  }

  // back to the walk (onQuit: main.js resumes it)
  stop() {
    if (!this.on) return;
    this.state = 'off';
    this.run?.fail('그만둠');
    this.player.autoRun = false;
    this.player.enabled = true;
    if (this.group.parent) this.scene.remove(this.group);
    for (const r of this.runners) if (r.a.holder.parent) this.scene.remove(r.a.holder);
    if (this.hud) this.hud.el.hidden = true;
    this.hint(false);
    this.big('');
    this.results(false);
    this.onQuit?.();
  }

  buildGates(c) {
    for (const o of [...this.group.children]) {
      this.group.remove(o);
      if (o.isInstancedMesh) { o.dispose(); continue; }       // (the arrows: their geometry and materials are shared)
      o.traverse((m) => { m.geometry?.dispose(); if (m.material?.map && m.material.map !== this.ringTex && m.material.map !== this.flagTex) m.material.map.dispose(); m.material?.dispose(); });
    }
    const last = c.gates.length - 1;
    this.gates = c.gates.map(([x, y], i) => {
      const fin = i === last, g = new THREE.Group();
      const h = this.groundAt(x, y);
      g.position.set(x, h, -y);
      const ring = new THREE.Mesh(new THREE.CylinderGeometry(GATE_R * 0.8, GATE_R * 0.8, GATE_H, 40, 1, true),
        new THREE.MeshBasicMaterial({ map: fin ? this.flagTex : this.ringTex, color: fin ? 0xffffff : 0xffc83a, transparent: true,
          depthWrite: false, side: THREE.DoubleSide, fog: false, toneMapped: false }));
      ring.position.y = GATE_H / 2 - 0.05;
      ring.renderOrder = 5;
      const disc = new THREE.Mesh(new THREE.RingGeometry(GATE_R * 0.8 - 0.25, GATE_R * 0.8, 40),
        new THREE.MeshBasicMaterial({ color: fin ? 0xffffff : 0xffc83a, transparent: true, opacity: 0.9, depthWrite: false, side: THREE.DoubleSide, fog: false, toneMapped: false }));
      disc.rotation.x = -Math.PI / 2;
      disc.position.y = 0.06;
      const tag = new THREE.Sprite(new THREE.SpriteMaterial({ map: labelTexture(fin ? '결승' : i === 0 ? '출발' : String(i), fin ? '#c0392b' : '#143c8c'),
        depthWrite: false, fog: false, toneMapped: false }));
      tag.scale.setScalar(1.3);
      tag.position.y = GATE_H + 1.0;
      tag.renderOrder = 6;
      g.add(ring, disc, tag);
      g.userData = { ring, disc, tag, x, y, h };
      this.group.add(g);
      return g;
    });
    this.arrows = c.gates.slice(0, -1).map((a, k) => this.buildLeg([a, ...(c.legs?.[k] || []), c.gates[k + 1]]));
    if (!this.group.parent) this.scene.add(this.group);
  }

  // one leg's arrows: spots every ARROW_GAP m along its line (s: how far along, for the flowing light), laid on the
  // ground when the leg is shown (placeLeg: the halls there may have come in since)
  buildLeg(pts) {
    let total = 0;
    for (let i = 1; i < pts.length; i++) total += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    const spots = [];
    let acc = 0;
    for (let i = 1; i < pts.length; i++) {
      const [ax, ay] = pts[i - 1], [bx, by] = pts[i], d = Math.hypot(bx - ax, by - ay);
      if (d < 1e-6) continue;
      for (let s = Math.ceil((acc - ARROW_CLEAR) / ARROW_GAP) * ARROW_GAP + ARROW_CLEAR; s < acc + d; s += ARROW_GAP) {
        if (s < ARROW_CLEAR || s > total - ARROW_CLEAR) continue;
        const u = (s - acc) / d;
        spots.push({ x: ax + (bx - ax) * u, y: ay + (by - ay) * u, dx: (bx - ax) / d, dy: (by - ay) / d, s });
      }
      acc += d;
    }
    const m = new THREE.InstancedMesh(this.arrowGeo, this.arrowDim, Math.max(1, spots.length));
    m.count = spots.length;
    m.frustumCulled = false;
    m.renderOrder = 4;
    m.visible = false;
    for (let i = 0; i < spots.length; i++) m.setColorAt(i, GOLD);
    m.userData = { spots, placed: false };
    this.group.add(m);
    return m;
  }

  placeLeg(m) {
    const o = this._o;
    m.userData.spots.forEach((p, i) => {
      const h = this.groundAt(p.x, p.y), hf = this.groundAt(p.x + p.dx * 0.6, p.y + p.dy * 0.6), hb = this.groundAt(p.x - p.dx * 0.6, p.y - p.dy * 0.6);
      o.position.set(p.x, h + 0.08, -p.y);
      o.rotation.set(Math.atan2(hf - hb, 1.2), Math.atan2(-p.dx, p.dy), 0, 'YXZ');
      o.updateMatrix();
      m.setMatrixAt(i, o.matrix);
    });
    m.instanceMatrix.needsUpdate = true;
    m.userData.placed = true;
  }

  // the next gate bright, the one after it faint, the rest (and those passed) away
  showGates() {
    this.gates.forEach((g, i) => {
      const k = i - this.next;
      g.visible = k === 0 || k === 1 || (i === 0 && this.state === 'count');
      const a = k === 0 ? 1 : 0.35;
      g.userData.ring.material.opacity = a;
      g.userData.disc.material.opacity = 0.9 * a;
      g.userData.tag.material.opacity = k === 0 ? 1 : 0.6;
      g.userData.tag.scale.setScalar(k === 0 ? 1.5 : 1.0);
    });
    // the arrows: the leg to the next gate bright, the one after it faint
    this.arrows.forEach((m, k) => {
      const d = k - (this.next - 1);
      m.visible = this.state !== 'done' && (d === 0 || d === 1);
      if (!m.visible) return;
      if (!m.userData.placed || d === 0) this.placeLeg(m);
      m.material = d === 0 ? this.arrowOn : this.arrowDim;
      if (d === 1) { for (let i = 0; i < m.count; i++) m.setColorAt(i, GOLD); if (m.instanceColor) m.instanceColor.needsUpdate = true; }
    });
  }

  // the bright leg's arrows: a light running along them toward the gate
  flowArrows(t) {
    const m = this.arrows?.[this.next - 1];
    if (!m?.visible || !m.count) return;
    const c = this._c;
    m.userData.spots.forEach((p, i) => {
      const f = 0.5 + 0.5 * Math.cos((p.s / ARROW_GAP) * 0.9 - t * 5);
      m.setColorAt(i, c.copy(GOLD).lerp(PALE, f * 0.75).multiplyScalar(0.75 + 0.35 * f));
    });
    m.instanceColor.needsUpdate = true;
  }

  // t: the loop's clock; paused: the settings card, a memory card or the map is open (the clock stops)
  update(dt, t, paused) {
    if (!this.on) return;
    for (const g of this.gates) if (g.visible) g.userData.ring.rotation.y = t * 0.6;
    this.flowArrows(t);
    this.run?.frame(dt, paused);
    if (!paused) { this.tick(dt); this.moveRunners(dt); }
    this.drawHud();
  }

  tick(dt) {
    const pl = this.player;
    if (this.state === 'count') {
      pl.enabled = false;
      this.clock -= dt;
      const n = Math.ceil(this.clock);
      if (n !== this.shown && n > 0) { this.shown = n; this.big(String(n)); this.sound?.cue('beep'); }
      if (this.clock <= 0) {
        this.state = 'play';
        this.big('출발!');
        this.sound?.cue('go');
        pl.enabled = true;
        this.showGates();
        this.run?.add('go', pl.x, pl.y);
      }
    } else if (this.state === 'play') {
      this.time += dt;
      this.run?.sample(pl.x, pl.y);
      if (this.time > 6 && this.hintOn) this.hint(false);
      const g = this.gates[this.next].userData;
      const dz = pl.pos.y - g.h;
      if (Math.hypot(pl.x - g.x, pl.y - g.y) < GATE_R && dz > -2 && dz < 5) this.pass();
    }
    if (this.bigT !== undefined) { this.bigT -= dt; if (this.bigT <= 0) { this.big(''); this.bigT = undefined; } }
  }

  pass() {
    this.splits.push(this.time);
    const i = this.next, last = this.gates.length - 1;
    this.run?.add('g', this.player.x, this.player.y, i);
    const ref = this.best?.splits?.[i - 1];
    if (Number.isFinite(ref)) this.flash(fmtGap(this.time - ref), this.time <= ref ? 'ahead' : 'behind');
    else this.flash(fmt(this.time), '');
    if (i === last) { this.finish(); return; }
    this.sound?.cue('beep');
    this.next++;
    this.showGates();
  }

  finish() {
    this.state = 'done';
    this.run?.end();
    this.sound?.cue('buzzer');
    this.big('도착!');
    const pl = this.player;
    pl.enabled = false;
    pl.speed = 0;
    this.gates.forEach((g) => { g.visible = false; });
    this.arrows.forEach((m) => { m.visible = false; });
    this.hint(false);
    const rec = { id: Date.now(), at: Date.now(), time: Math.round(this.time * 100) / 100, splits: this.splits.map((s) => Math.round(s * 100) / 100),
      hero: pl.actor.id, view: pl.fpv ? 'first' : 'third' };
    const prev = this.best;
    const { rank, total } = addRecord(this.course.id, rec);
    setTimeout(() => { if (this.state === 'done') this.results(true, { rec, rank, total, prev }); }, 1200);
  }

  // ---------------------------------------------------------------- the other runners
  // the course as one line (gates and the turns between) with the distance along it at each point
  lineAlong(c) {
    const pts = lineOf(c), at = [0];
    for (let i = 1; i < pts.length; i++) at.push(at[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const [fx, fy] = pts[0], [lx, ly] = pts[pts.length - 1];
    return { pts, at, len: at[at.length - 1], loop: Math.hypot(lx - fx, ly - fy) < 12 };
  }
  // the point s m along the line, and the way it goes there
  pointAt(s) {
    const { pts, at } = this.line;
    let i = 1;
    while (i < at.length - 1 && at[i] < s) i++;
    const [ax, ay] = pts[i - 1], [bx, by] = pts[i], d = at[i] - at[i - 1] || 1, u = Math.min(1, Math.max(0, (s - at[i - 1]) / d));
    return { x: ax + (bx - ax) * u, y: ay + (by - ay) * u, dx: (bx - ax) / d, dy: (by - ay) / d };
  }
  // how far along the line the walker is (the nearest point of it)
  progress(x, y) {
    const { pts, at } = this.line;
    let best = Infinity, s = 0;
    for (let i = 1; i < pts.length; i++) {
      const [ax, ay] = pts[i - 1], [bx, by] = pts[i], dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy || 1;
      const u = Math.min(1, Math.max(0, ((x - ax) * dx + (y - ay) * dy) / l2)), qx = ax + dx * u - x, qy = ay + dy * u - y, d = qx * qx + qy * qy;
      if (d < best) { best = d; s = at[i - 1] + u * Math.sqrt(l2); }
    }
    return s;
  }

  placeRunners(c) {
    this.line = this.lineAlong(c);
    if (!this.cast) return;
    const mine = this.player.actor?.id, ids = STUDENTS.filter((id) => id !== mine);
    while (this.runners.length < RUNNERS) {
      const n = this.runners.length, id = ids[(n * 5 + 3) % ids.length];
      const a = this.cast.make(id, null, crowdLook(id, 5200 + n * 11));
      this.shadows?.addDynamic(a.holder);
      this.blobs?.addPerson(a);
      this.runners.push({ a, n });
    }
    // spread from just ahead of the start: the first few the way the course goes, every third one coming back
    this.runners.forEach((r, i) => {
      r.dir = i % 3 === 2 ? -1 : 1;
      r.speed = 3.4 + ((i * 7) % 6) * 0.25;
      r.side = ((i * 5) % 7) / 7 * 1.6 - 0.8;
      this.respawn(r, 12 + i * (Math.min(this.line.len, 2 * RUN_FAR) - 12) / RUNNERS);
      if (!r.a.holder.parent) this.scene.add(r.a.holder);
    });
  }
  respawn(r, s) {
    const L = this.line.len;
    r.s = this.line.loop ? ((s % L) + L) % L : Math.min(L - 1, Math.max(1, s));
    r.x = r.y = null;
  }

  moveRunners(dt) {
    if (!this.runners.length || !this.line) return;
    const pl = this.player, L = this.line.len, col = pl.col;
    this.progT = (this.progT ?? 0) - dt;
    if (this.progT <= 0) { this.progT = 0.5; this.prog = this.progress(pl.x, pl.y); }
    for (const r of this.runners) {
      r.s += r.dir * r.speed * dt;
      if (this.line.loop) r.s = ((r.s % L) + L) % L;
      else if (r.s > L - 1 || r.s < 1) { r.dir = -r.dir; r.s = Math.min(L - 1, Math.max(1, r.s)); }
      let p = this.pointAt(r.s);
      let x = p.x - p.dy * r.side, y = p.y + p.dx * r.side;
      // far from the walker: back on the course ahead of them (out of sight behind them now)
      if (Math.hypot(x - pl.x, y - pl.y) > RUN_FAR) {
        this.respawn(r, (this.prog ?? 0) + RUN_AHEAD[0] + Math.random() * (RUN_AHEAD[1] - RUN_AHEAD[0]));
        p = this.pointAt(r.s);
        x = p.x - p.dy * r.side; y = p.y + p.dx * r.side;
      }
      // out of the walls and round the walker (nobody runs through anybody)
      [x, y] = col.resolve(x, y, 0.3);
      const ox = x - pl.x, oy = y - pl.y, od = Math.hypot(ox, oy);
      if (od < 0.9 && od > 1e-3) { x = pl.x + ox / od * 0.9; y = pl.y + oy / od * 0.9; }
      const h = r.a.holder;
      h.position.set(x, this.groundAt(x, y), -y);
      h.rotation.y = Math.atan2(p.dx * r.dir, -p.dy * r.dir);
      r.x = x; r.y = y;
      locomotion(r.a, r.speed, 3.0);
      r.a.mixer.update(dt);
    }
  }

  // ---------------------------------------------------------------- HUD
  hudEl() {
    if (this.hud) return this.hud.el;
    const el = document.createElement('div');
    el.id = 'racehud';
    el.innerHTML = '<div class="time"><small>기록</small><b>0:00.00</b></div>'
      + '<div class="gate"><small>문</small><b>1 / 10</b><span></span></div>'
      + '<div class="way"><i></i><span></span></div>';
    document.body.appendChild(el);
    const big = document.createElement('div');
    big.id = 'racebig';
    document.body.appendChild(big);
    const split = document.createElement('div');
    split.id = 'racesplit';
    document.body.appendChild(split);
    this.hud = { el, time: el.querySelector('.time b'), gate: el.querySelector('.gate b'), best: el.querySelector('.gate span'),
      arrow: el.querySelector('.way i'), dist: el.querySelector('.way span'), big, split };
    return el;
  }

  drawHud() {
    const h = this.hud;
    if (!h || !this.course) return;
    const txt = fmt(this.time);
    if (h.time.textContent !== txt) h.time.textContent = txt;
    const n = this.gates.length - 1, gi = Math.min(this.next, n);
    const gt = gi === n ? '결승' : `${gi} / ${n - 1}`;
    if (h.gate.textContent !== gt) h.gate.textContent = gt;
    const bt = this.best ? `최고 ${fmt(this.best.time)}` : '첫 기록 도전';
    if (h.best.textContent !== bt) h.best.textContent = bt;
    // the arrow: the next gate's direction from where the camera looks (up = straight ahead)
    const g = this.gates[gi]?.userData;
    h.arrow.parentElement.style.visibility = this.state === 'done' ? 'hidden' : '';
    if (g && this.state !== 'done') {
      const pl = this.player, d = this.camera.getWorldDirection(this._dir);
      const look = Math.atan2(d.x, -d.z), to = Math.atan2(g.x - pl.x, g.y - pl.y);
      const a = wrapAngle(to - look);
      h.arrow.style.transform = `rotate(${a.toFixed(3)}rad)`;
      const m = `${Math.round(Math.hypot(g.x - pl.x, g.y - pl.y))} m`;
      if (h.dist.textContent !== m) h.dist.textContent = m;
    }
  }

  // how to run, under the HUD: through the count and the first seconds
  hint(on) {
    this.hintOn = on;
    let el = this.hintEl;
    if (!el) {
      if (!on) return;
      el = this.hintEl = document.createElement('div');
      el.id = 'racehint';
      document.body.appendChild(el);
    }
    if (on) el.textContent = matchMedia('(pointer: coarse)').matches
      ? '화면 왼쪽을 밀면 늘 뛰어요 · 바닥의 화살표를 따라가요'
      : '↑(W)만 눌러도 늘 뛰어요 · Shift는 필요 없어요 · 바닥의 화살표를 따라가요';
    el.hidden = !on;
  }

  // the big word in the middle: the count, 출발!, 도착!
  big(text) {
    const el = this.hud?.big;
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('small', text.length > 1);
    el.classList.remove('pop'); void el.offsetWidth;
    if (text) { el.classList.add('pop'); this.bigT = text.length > 1 ? 1.1 : 0.9; }
  }

  // a gate's time against the best run's at the same gate (ahead: green, behind: red)
  flash(text, cls = '') {
    const el = this.hud?.split;
    if (!el) return;
    el.textContent = text;
    el.className = cls;
    el.classList.remove('pop'); void el.offsetWidth;
    if (text) el.classList.add('pop');
  }

  // ---------------------------------------------------------------- the results card
  results(show, info = {}) {
    let el = this.resEl;
    if (!show) { if (el) el.hidden = true; return; }
    if (!el) {
      el = this.resEl = document.createElement('div');
      el.id = 'raceresult';
      el.innerHTML = '<div><h2></h2><p class="big"></p><p class="best"></p><ol class="ranks"></ol>'
        + '<div class="btns"><button type="button" class="again">다시 달리기</button><button type="button" class="other">다른 코스</button></div>'
        + '<button type="button" class="quit">그만하고 산책하기</button><button type="button" class="quit totitle" data-to-title>처음 화면으로</button></div>';
      document.body.appendChild(el);
      el.querySelector('.again').addEventListener('click', (e) => { e.currentTarget.blur(); this.start(); });
      el.querySelector('.other').addEventListener('click', (e) => { e.currentTarget.blur(); this.results(false); this.openPicker(); });
      el.querySelector('.quit').addEventListener('click', (e) => { e.currentTarget.blur(); this.stop(); });
    }
    const { rec, rank, total, prev } = info;
    el.querySelector('h2').textContent = this.course.name;
    el.querySelector('.big').textContent = fmt(rec.time);
    const be = el.querySelector('.best'), top = rank === 1;
    be.textContent = top
      ? (prev ? `새 기록! ${(prev.time - rec.time).toFixed(2)}초 앞당김` : '첫 기록! 다음엔 이 기록과 겨뤄요')
      : `이 브라우저 ${rank}위 (${total}번 가운데) · 최고 ${fmt(prev.time)}`;
    be.classList.toggle('new', top);
    const list = records(this.course.id).slice(0, 5);
    el.querySelector('.ranks').replaceChildren(...list.map((r, i) => {
      const li = document.createElement('li');
      li.classList.toggle('me', r.id === rec.id);
      li.innerHTML = '<span class="n"></span><span class="who"></span><span class="t"></span>';
      li.querySelector('.n').textContent = `${i + 1}`;
      li.querySelector('.who').textContent = `${HERO[r.hero]?.name ?? ''} · ${day(r.at)}`;
      li.querySelector('.t').textContent = fmt(r.time);
      return li;
    }));
    if (!this.rankBox) { this.rankBox = new RankBox(); el.querySelector('.ranks').after(this.rankBox.el); }
    this.rankBox.set(this.run, { hero: rec.hero, heroName: HERO[rec.hero]?.name ?? '' });
    el.hidden = false;
    el.querySelector('.again').focus({ preventScroll: true });
  }
  get resultsOpen() { return !!this.resEl && !this.resEl.hidden; }
}
