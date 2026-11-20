// 캠퍼스 달리기 (the title card's second game, the settings card's 「캠퍼스 달리기」): a time trial over one of three
// courses. Each course is a row of gates on the ground (campus x, y); the first is the start line, the last the
// finish. The walker runs without Shift meanwhile (Shift walks: Player.autoRun) and finds their own way from gate to
// gate: the HUD's arrow points at the next one. Every run is kept in this browser per course, with the times at each
// gate, so the next run shows how far ahead of (or behind) the best one it is.
// Loaded only when the course picker opens (main.js).
import * as THREE from 'three';
import { HERO } from './characters.js';
import { safeGet, safeSet, wrapAngle } from './util.js';
import './race.css';

// the gates: [x, y] about 55 m apart along a way the walker can run (found over the walker's colliders and run
// through with Player.update: TECH_NOTE 「달리기」); the first is where the run starts, facing the second
export const COURSES = [
  { id: 'baekyang', name: '백양로 직선 주로', desc: '정문에서 백양로를 따라 언더우드관 앞까지',
    gates: [[-110, -383], [-98, -333.7], [-85, -284.9], [-72.7, -235.7], [-57, -188], [-41, -140.4], [-28, -91.5], [-14.1, -43.1], [-4, 7], [10, 55.5], [21, 105.2], [34, 154], [34, 202.5], [59, 244]] },
  { id: 'loop', name: '중앙 광장 한 바퀴', desc: '학생회관 앞에서 대강당 · 용재관 · 광복관 · 중앙도서관을 돌아 다시 학생회관 앞으로',
    gates: [[-2, -58], [26, -18.3], [34, 30.7], [46, 78.2], [53.9, 124.9], [28.5, 124], [-21.3, 132], [-70.6, 141], [-86.4, 94.6], [-118.8, 66], [-103.8, 37.8], [-74, 9], [-55, -42], [-6, -48]] },
  { id: 'cheongsong', name: '청송대 숲길', desc: '언더우드관 앞에서 노천극장 · 청송대 · 연희관을 돌아 언더우드관 앞으로',
    gates: [[59, 244], [78, 196.9], [118.1, 164.9], [154.5, 144.5], [190.6, 184.6], [226, 225], [235, 276.2], [200.3, 288], [149, 285.8], [124, 324], [80.4, 325.4], [59.4, 286], [40, 250], [57, 243]] },
];
export const courseOf = (id) => COURSES.find((c) => c.id === id);
export const lengthOf = (c) => c.gates.reduce((s, p, i) => (i ? s + Math.hypot(p[0] - c.gates[i - 1][0], p[1] - c.gates[i - 1][1]) : 0), 0);

const COUNT = 3;
const GATE_R = 4.5, GATE_H = 2.6;      // a gate is passed within GATE_R of its middle (and 5 m in height)
const KEY = 'y97-run-records', MAX = 50;

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

export class Race {
  // groundAt(x, y): the walk's height there; ensure(x, y): chunks.ensure (a promise while the halls there come in);
  // onBegin(msg): main.js takes the walk on (title card off, settings card shut); onQuit: back to the walk
  constructor({ scene, camera, player, sound, groundAt, ensure, onBegin, onQuit }) {
    Object.assign(this, { scene, camera, player, sound, groundAt, ensure, onBegin, onQuit });
    this.state = 'off';                 // off | count | play | done
    this.group = new THREE.Group();
    this.group.name = 'race_gates';
    this.ringTex = ringTexture();
    this.flagTex = flagTexture();
    this._dir = new THREE.Vector3();
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
      ? '달리는 동안은 화면 왼쪽을 밀기만 해도 뛰어요. 위의 화살표가 다음 문을 가리켜요.'
      : '달리는 동안은 ↑(W)만 눌러도 뛰어요(Shift를 누르면 걸어요). 위의 화살표가 다음 문을 가리켜요.';
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
    try {
      const [sx, sy] = c.gates[0];
      const wait = this.ensure?.(sx, sy);
      if (wait) await wait;
    } finally { this.starting = false; }
    this.results(false);
    this.course = c;
    this.best = records(c.id)[0] || null;
    this.buildGates(c);
    const pl = this.player, [sx, sy] = c.gates[0], [nx, ny] = c.gates[1];
    this.onBegin?.(`${c.name} · ${matchMedia('(pointer: coarse)').matches ? '화면 왼쪽을 밀어 달려요' : '↑(W)로 달리고 ←→(A·D)로 방향을 바꿔요'} · 화살표가 다음 문을 가리켜요`);
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
    this.hudEl().hidden = false;
    this.flash('');
    this.showGates();
  }

  // back to the walk (onQuit: main.js resumes it)
  stop() {
    if (!this.on) return;
    this.state = 'off';
    this.player.autoRun = false;
    this.player.enabled = true;
    if (this.group.parent) this.scene.remove(this.group);
    if (this.hud) this.hud.el.hidden = true;
    this.big('');
    this.results(false);
    this.onQuit?.();
  }

  buildGates(c) {
    for (const o of [...this.group.children]) {
      this.group.remove(o);
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
    if (!this.group.parent) this.scene.add(this.group);
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
  }

  // t: the loop's clock; paused: the settings card, a memory card or the map is open (the clock stops)
  update(dt, t, paused) {
    if (!this.on) return;
    for (const g of this.gates) if (g.visible) g.userData.ring.rotation.y = t * 0.6;
    if (!paused) this.tick(dt);
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
      }
    } else if (this.state === 'play') {
      this.time += dt;
      const g = this.gates[this.next].userData;
      const dz = pl.pos.y - g.h;
      if (Math.hypot(pl.x - g.x, pl.y - g.y) < GATE_R && dz > -2 && dz < 5) this.pass();
    }
    if (this.bigT !== undefined) { this.bigT -= dt; if (this.bigT <= 0) { this.big(''); this.bigT = undefined; } }
  }

  pass() {
    this.splits.push(this.time);
    const i = this.next, last = this.gates.length - 1;
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
    this.sound?.cue('buzzer');
    this.big('도착!');
    const pl = this.player;
    pl.enabled = false;
    pl.speed = 0;
    this.gates.forEach((g) => { g.visible = false; });
    const rec = { id: Date.now(), at: Date.now(), time: Math.round(this.time * 100) / 100, splits: this.splits.map((s) => Math.round(s * 100) / 100),
      hero: pl.actor.id, view: pl.fpv ? 'first' : 'third' };
    const prev = this.best;
    const { rank, total } = addRecord(this.course.id, rec);
    setTimeout(() => { if (this.state === 'done') this.results(true, { rec, rank, total, prev }); }, 1200);
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
        + '<button type="button" class="quit">그만하고 산책하기</button></div>';
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
    el.hidden = false;
    el.querySelector('.again').focus({ preventScroll: true });
  }
  get resultsOpen() { return !!this.resEl && !this.resEl.hidden; }
}
