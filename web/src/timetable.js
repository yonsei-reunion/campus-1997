// 강의실 찾기 (the title card's and the settings card's 「강의실 찾기」): a timetable of four classes in four halls. The
// walker comes out of the first hall as its class ends and has the break (10 minutes on the campus clock, a minute or
// two of play) to reach the front door of the next one, then the next. The halls are named and nothing more: no arrow,
// no map, no hall names over the roofs; the way is the one remembered from 1997. The easy round has the HUD's arrow,
// the door's ring from afar and three short looks from above (조감도). Every round is kept in this browser per timetable.
// Loaded only when the timetable picker opens (main.js).
import * as THREE from 'three';
import { HERO } from './characters.js';
import { RUN } from './player.js';
import { safeGet, safeSet, wrapAngle } from './util.js';
import './timetable.css';

// the halls with lecture rooms in 1997 (their 1997 names: 고증 3.1; halls built later are not in the game) and the
// way between their doors in metres: the walker's colliders, A* over a 1 m grid from door to door (places.js: where
// the walker stands 4 m past the foot of the widest flight), measured headless on the campus of 2026-11-21.
// HALLS[i]'s ways to HALLS[0 .. i - 1] are WAY[i]
const HALLS = ['인문관', '종합관', '연희관', '성암관', '교육관', '가정관', '광복관', '용재관', '상대신관', '상대별관', '경영학교실단',
  '과학관', '제1공학관', '제2공학관', '아펜젤러관', '음악대학', '체육교육관', '대강당', '연합신학대학원'];
const WAY = [[], [127], [178, 164], [190, 205, 46], [135, 143, 44, 76], [200, 132, 93, 137, 89], [253, 329, 396, 383, 353, 430],
  [188, 289, 243, 197, 225, 313, 243], [285, 238, 159, 165, 162, 109, 515, 361], [286, 245, 119, 125, 162, 117, 508, 321, 51],
  [193, 296, 302, 274, 259, 340, 188, 86, 421, 397], [355, 431, 514, 513, 471, 548, 145, 396, 633, 631, 312],
  [564, 659, 689, 655, 646, 727, 342, 462, 808, 779, 387, 320], [531, 610, 673, 660, 631, 707, 298, 477, 792, 786, 395, 246, 188],
  [152, 202, 154, 108, 139, 226, 299, 90, 272, 232, 166, 453, 548, 563], [471, 565, 483, 437, 482, 572, 433, 309, 584, 534, 302, 545, 443, 529, 363],
  [455, 525, 598, 585, 555, 632, 222, 440, 717, 710, 356, 155, 227, 109, 501, 544],
  [249, 353, 339, 293, 299, 387, 221, 99, 457, 416, 70, 345, 364, 382, 185, 243, 377],
  [85, 186, 265, 263, 222, 285, 168, 199, 371, 371, 178, 270, 488, 449, 189, 462, 365, 239]];
export const wayOf = (a, b) => {
  const i = HALLS.indexOf(a), j = HALLS.indexOf(b);
  return i < 0 || j < 0 || i === j ? 0 : i > j ? WAY[i][j] : WAY[j][i];
};
// the break: the way at running pace, a third more for the turns and the doubt, and 15 s to get going (checked
// headless: a walker running the A* way makes every break of every timetable with 25 s or more to spare)
export const breakOf = (m) => Math.ceil((m / RUN * 1.35 + 15) / 5) * 5;

// the timetables: [class, hall] for 1 – 4교시 (a class every hour on the hour). The subjects are a game's: names
// any college had, not a record of 1997's courses; 채플 was in 대강당
export const SETS = [
  { id: 'liberal', name: '문과대학', classes: [['국어학개론', '인문관'], ['대학영어', '종합관'], ['사회학개론', '연희관'], ['채플', '대강당']] },
  { id: 'science', name: '이과대학', classes: [['일반물리학', '과학관'], ['교양체육', '체육교육관'], ['채플', '대강당'], ['기독교의 이해', '종합관']] },
  { id: 'commerce', name: '상경대학', classes: [['경제원론', '상대신관'], ['대학영어', '종합관'], ['채플', '대강당'], ['회계원리', '상대별관']] },
  { id: 'eng', name: '공과대학', classes: [['공업수학', '제1공학관'], ['일반화학실험', '제2공학관'], ['미적분학', '과학관'], ['채플', '대강당']] },
];
const SUBJECTS = ['대학영어', '기독교의 이해', '철학개론', '글쓰기', '통계학', '한국사', '심리학개론', '일반생물학', '경제학입문', '교양체육', '서양사', '컴퓨터 입문'];

// 오늘의 시간표: four halls drawn from the day's date (the same for everyone that day), each break 120 – 480 m
const dayKey = (d = new Date()) => `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
function todaySet(key = dayKey()) {
  let s = +key >>> 0;
  const rnd = () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const pick = (a) => a[Math.floor(rnd() * a.length)];
  for (let tries = 0; tries < 200; tries++) {
    const halls = [pick(HALLS)];
    while (halls.length < 4) {
      const last = halls[halls.length - 1];
      const ok = HALLS.filter((h) => !halls.includes(h) && wayOf(last, h) >= 120 && wayOf(last, h) <= 480);
      if (!ok.length) break;
      halls.push(pick(ok));
    }
    if (halls.length < 4) continue;
    const subj = [...SUBJECTS];
    const classes = halls.map((h) => [h === '대강당' ? '채플' : subj.splice(Math.floor(rnd() * subj.length), 1)[0], h]);
    return { id: `today-${key}`, name: '오늘의 시간표', today: true, classes };
  }
  return { ...SETS[0], id: `today-${key}`, name: '오늘의 시간표', today: true };
}
const setOf = (id) => (id?.startsWith('today') ? todaySet() : SETS.find((s) => s.id === id));
const legsOf = (set) => set.classes.slice(1).map(([, h], k) => breakOf(wayOf(set.classes[k][1], h)));

const COUNT = 3;
const DOOR_R = 5.5;                 // at the door: within this of the place where the walker would stand (4 m past the flight's foot)
const NEAR = 35;                    // the plain round shows the door's ring only this close
const PEEKS = 3, PEEK_T = 4;        // the easy round's looks from above: how many, how long (the clock runs meanwhile)
const KEY = 'y97-class-records', MAX = 30;

// ---------------------------------------------------------------- records (this browser only)
const recKey = (id, easy) => `${id}${easy ? '-easy' : ''}`;
const better = (a, b) => a.late - b.late || a.time - b.time || a.at - b.at;
function loadAll() {
  let all;
  try { all = JSON.parse(safeGet(KEY) || '{}'); } catch { all = {}; }
  return all && typeof all === 'object' && !Array.isArray(all) ? all : {};
}
export function records(id, easy) {
  const list = loadAll()[recKey(id, easy)];
  return (Array.isArray(list) ? list : []).filter((r) => r && Number.isFinite(r.time) && Number.isFinite(r.late)).sort(better);
}
function addRecord(id, easy, rec) {
  const all = loadAll(), list = records(id, easy);
  list.push(rec);
  list.sort(better);
  all[recKey(id, easy)] = list.slice(0, MAX);
  // (yesterday's timetables go: only today's is ever played again)
  const today = `today-${dayKey()}`;
  for (const k of Object.keys(all)) if (k.startsWith('today-') && !k.startsWith(today)) delete all[k];
  safeSet(KEY, JSON.stringify(all));
  return { rank: list.indexOf(rec) + 1, total: list.length };
}
export const fmt = (s) => {
  const m = Math.floor(s / 60), r = s - m * 60;
  return `${m}:${r.toFixed(1).padStart(4, '0')}`;
};
const fmtS = (s) => { s = Math.max(0, Math.ceil(s)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
const day = (ms) => { const d = new Date(ms); return `${d.getMonth() + 1}/${d.getDate()}`; };
// the campus clock: class k (0-based) is at (9 + k):00; the break before it runs from (8 + k):50
const clockAt = (k, u) => {
  const min = 50 + 10 * u, h = 8 + k + Math.floor(min / 60), m = Math.floor(min % 60);
  return `${h}:${String(m).padStart(2, '0')}`;
};
const hourOf = (k) => `${9 + k}:00`;

// ---------------------------------------------------------------- the door's look
function ringTexture() {
  const c = document.createElement('canvas');
  c.width = 4; c.height = 64;
  const g = c.getContext('2d'), gr = g.createLinearGradient(0, 64, 0, 0);
  gr.addColorStop(0, 'rgba(255,255,255,0.95)');
  gr.addColorStop(0.15, 'rgba(255,255,255,0.5)');
  gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 4, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
function nameTexture(text) {
  const c = document.createElement('canvas');
  c.width = 512; c.height = 128;
  const g = c.getContext('2d');
  g.font = '700 64px "Noto Sans KR", sans-serif';
  const w = Math.min(500, g.measureText(text).width + 56);
  g.fillStyle = '#c0392b';
  g.beginPath(); g.roundRect((512 - w) / 2, 14, w, 100, 22); g.fill();
  g.lineWidth = 6; g.strokeStyle = '#fff'; g.stroke();
  g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(text, 256, 68, 460);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
const glow = (color, opacity = 1) => new THREE.MeshBasicMaterial({ color, map: null, transparent: true, opacity, depthWrite: false,
  side: THREE.DoubleSide, fog: false, toneMapped: false });

export class Timetable {
  // places: main.js's start places (places.js: name, x, y, yaw); groundAt(x, y): the walk's height; ensure(x, y):
  // chunks.ensure; onBegin(msg): main.js takes the walk on; onQuit: back to the walk
  constructor({ scene, camera, player, sound, groundAt, places, ensure, mobile, onBegin, onQuit }) {
    Object.assign(this, { scene, camera, player, sound, groundAt, places, ensure, mobile, onBegin, onQuit });
    this.state = 'off';                 // off | count | play | done
    this.easy = safeGet('y97-class-easy') === '1';
    this.group = new THREE.Group();
    this.group.name = 'timetable_door';
    this.ringTex = ringTexture();
    this._dir = new THREE.Vector3();
    this.buildDoor();
    addEventListener('keydown', (e) => {
      if (e.code === 'Escape') {
        if (this.pickOpen) { e.stopImmediatePropagation(); this.closePicker(); }
        else if (this.resultsOpen) { e.stopImmediatePropagation(); this.stop(); }
      } else if (e.code === 'KeyM' && this.state === 'play' && this.easy && !e.repeat) {
        e.stopImmediatePropagation();
        this.peek();
      }
    }, true);
  }

  get on() { return this.state !== 'off'; }
  get coarse() { return this.mobile || matchMedia('(pointer: coarse)').matches; }

  // ---------------------------------------------------------------- the picker
  openPicker() {
    let el = this.pickEl;
    if (!el) {
      el = this.pickEl = document.createElement('div');
      el.id = 'classpick';
      el.innerHTML = '<div><h2>강의실 찾기</h2><p class="lead">시간표를 고르세요. 수업이 끝나면 쉬는 시간 안에 다음 수업 건물의 현관(계단 앞)까지 가요. 길은 1997년의 기억으로!</p>'
        + '<div class="mode" role="radiogroup" aria-label="난이도"><button type="button" data-easy="0">이름만</button><button type="button" data-easy="1">쉬운 판</button></div>'
        + '<p class="modehow"></p><ul class="sets"></ul><p class="how"></p><button type="button" class="close">닫기</button></div>';
      document.body.appendChild(el);
      el.querySelector('.close').addEventListener('click', () => this.closePicker());
      el.addEventListener('click', (e) => { if (e.target === el) this.closePicker(); });
      el.querySelectorAll('.mode button').forEach((b) => b.addEventListener('click', () => {
        this.easy = b.dataset.easy === '1';
        safeSet('y97-class-easy', this.easy ? '1' : '0');
        this.fillPicker();
      }));
    }
    this.fillPicker();
    el.hidden = false;
    el.querySelector('.sets button')?.focus({ preventScroll: true });
  }
  fillPicker() {
    const el = this.pickEl;
    el.querySelectorAll('.mode button').forEach((b) => b.classList.toggle('on', (b.dataset.easy === '1') === this.easy));
    el.querySelector('.modehow').textContent = this.easy
      ? '화살표가 다음 건물을 가리키고, 조감도를 세 번 잠깐 볼 수 있어요.'
      : '건물 이름만 보여요. 화살표 · 지도 · 이름표 없이 찾아가요.';
    const sets = [...SETS, todaySet()];
    el.querySelector('.sets').replaceChildren(...sets.map((s) => {
      const li = document.createElement('li'), best = records(s.id, this.easy)[0];
      li.innerHTML = '<button type="button"><b></b><span class="desc"></span><span class="meta"></span></button>';
      li.querySelector('b').textContent = s.name;
      li.querySelector('.desc').textContent = s.classes.map(([, h]) => h).join(' → ');
      const m = s.classes.slice(1).reduce((a, [, h], k) => a + wayOf(s.classes[k][1], h), 0);
      li.querySelector('.meta').textContent = `약 ${Math.round(m / 10) * 10} m · 쉬는 시간 셋${best ? ` · 최고 ${fmt(best.time)}${best.late ? ` (지각 ${best.late})` : ''}` : ''}`;
      li.querySelector('button').addEventListener('click', (e) => { e.currentTarget.blur(); this.closePicker(); this.start(s.id); });
      return li;
    }));
    el.querySelector('.how').textContent = this.coarse
      ? '화면 왼쪽을 밀면 달려요.' : '↑(W)로 달리고 ←→(A·D)로 방향을 바꿔요.';
  }
  closePicker() { if (this.pickEl) this.pickEl.hidden = true; }
  get pickOpen() { return !!this.pickEl && !this.pickEl.hidden; }

  // ---------------------------------------------------------------- a round
  placeOf(name) { return this.places.find((p) => p.name === name); }

  async start(id = this.set?.id) {
    const set = setOf(id);
    if (!set || this.starting) return;
    const stops = set.classes.map(([, h]) => this.placeOf(h));
    if (stops.some((p) => !p)) return;
    this.starting = true;
    try {
      const wait = this.ensure?.(stops[0].x, stops[0].y);
      if (wait) await wait;
    } finally { this.starting = false; }
    this.results(false);
    this.set = set;
    this.stops = stops.map((p) => ({ name: p.name, x: p.x, y: p.y, h: this.groundAt(p.x, p.y) }));
    this.limits = legsOf(set);
    this.best = records(set.id, this.easy)[0] || null;
    document.body.classList.toggle('class-easy', this.easy);
    const s0 = stops[0], s1 = stops[1];
    this.onBegin?.(`${set.name} · 1교시 ${set.classes[0][0]} 끝! 2교시는 ${s1.name}에서 · ${this.coarse ? '화면 왼쪽을 밀어 달려요' : '↑(W)로 달려요'}`);
    // out of the first hall's door, turned round to the campus
    const pl = this.player;
    pl.teleport(s0.x, s0.y, s0.yaw + Math.PI);
    pl.cam.ready = false;
    pl.autoRun = true;
    pl.enabled = false;
    pl.keys.clear();
    pl.stick.set(0, 0);
    pl.speed = 0;
    this.next = 1;
    this.leg = 0;              // the time in this break
    this.time = 0;             // the time over all of them
    this.splits = [];
    this.lates = [];
    this.lateShown = false;
    this.peeks = PEEKS;
    this.peekT = 0;
    this.state = 'count';
    this.clock = COUNT;
    this.shown = 0;
    this.hudEl().hidden = false;
    this.fillTable();
    this.placeDoor();
    if (!this.group.parent) this.scene.add(this.group);
  }

  stop() {
    if (!this.on) return;
    this.endPeek();
    this.state = 'off';
    this.player.autoRun = false;
    this.player.enabled = true;
    if (this.group.parent) this.scene.remove(this.group);
    if (this.hud) this.hud.el.hidden = this.hud.table.hidden = true;
    this.big('');
    this.results(false);
    document.body.classList.remove('class-easy');
    this.onQuit?.();
  }

  // the next door: a ring on the ground, and (only in a look from above) a pillar of light with the hall's name, and
  // one over the walker
  buildDoor() {
    const ring = new THREE.Mesh(new THREE.CylinderGeometry(DOOR_R * 0.75, DOOR_R * 0.75, 2.4, 40, 1, true),
      new THREE.MeshBasicMaterial({ map: this.ringTex, color: 0xff6b5a, transparent: true, depthWrite: false, side: THREE.DoubleSide, fog: false, toneMapped: false }));
    ring.position.y = 1.15;
    ring.renderOrder = 5;
    const disc = new THREE.Mesh(new THREE.RingGeometry(DOOR_R * 0.75 - 0.25, DOOR_R * 0.75, 40), glow(0xff6b5a, 0.9));
    disc.rotation.x = -Math.PI / 2;
    disc.position.y = 0.06;
    const pillar = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.2, 90, 16, 1, true), new THREE.MeshBasicMaterial({
      map: this.ringTex, color: 0xff6b5a, transparent: true, depthWrite: false, side: THREE.DoubleSide, fog: false, toneMapped: false, blending: THREE.AdditiveBlending }));
    pillar.position.y = 45;
    const tag = new THREE.Sprite(new THREE.SpriteMaterial({ depthTest: false, depthWrite: false, fog: false, toneMapped: false }));
    tag.renderOrder = 7;
    this.door = new THREE.Group();
    this.door.add(ring, disc, pillar, tag);
    this.doorParts = { ring, disc, pillar, tag };
    const me = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.4, 60, 12, 1, true), new THREE.MeshBasicMaterial({
      map: this.ringTex, color: 0x6fb7ff, transparent: true, depthWrite: false, side: THREE.DoubleSide, fog: false, toneMapped: false, blending: THREE.AdditiveBlending }));
    me.position.y = 30;
    this.me = new THREE.Group();
    this.me.add(me);
    this.group.add(this.door, this.me);
  }
  placeDoor() {
    const s = this.stops[this.next];
    if (!s) return;
    this.door.position.set(s.x, s.h, -s.y);
    const { tag } = this.doorParts;
    tag.material.map?.dispose();
    tag.material.map = nameTexture(s.name);
    tag.material.needsUpdate = true;
    this.showDoor();
  }
  showDoor() {
    const pl = this.player, s = this.stops[this.next], peeking = this.peekT > 0;
    const d = s ? Math.hypot(pl.x - s.x, pl.y - s.y) : Infinity;
    this.door.visible = this.state === 'play' && !!s && (this.easy || peeking || d < NEAR);
    const { pillar, tag } = this.doorParts;
    pillar.visible = tag.visible = peeking;
    this.me.visible = peeking;
    if (peeking) this.me.position.set(pl.x, pl.pos.y, -pl.y);
  }

  update(dt, t, paused) {
    if (!this.on) return;
    this.doorParts.ring.rotation.y = t * 0.6;
    if (!paused) this.tick(dt);
    this.showDoor();
    if (this.peekT > 0) this.peekCam();
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
        this.big('쉬는 시간!');
        this.sound?.cue('go');
        pl.enabled = true;
      }
    } else if (this.state === 'play') {
      this.time += dt;
      this.leg += dt;
      if (this.peekT > 0) { this.peekT -= dt; if (this.peekT <= 0) this.endPeek(); }
      const lim = this.limits[this.next - 1];
      if (!this.lateShown && this.leg > lim) { this.lateShown = true; this.big('지각!'); this.sound?.cue('buzzer'); }
      const s = this.stops[this.next], dz = pl.pos.y - s.h;
      if (Math.hypot(pl.x - s.x, pl.y - s.y) < DOOR_R && dz > -3 && dz < 6) this.arrive();
    }
    if (this.bigT !== undefined) { this.bigT -= dt; if (this.bigT <= 0) { this.big(''); this.bigT = undefined; } }
  }

  arrive() {
    const i = this.next, lim = this.limits[i - 1], late = this.leg > lim;
    this.endPeek();
    this.splits.push(Math.round(this.leg * 10) / 10);
    this.lates.push(late);
    this.flash(late ? `${this.stops[i].name} · ${fmtS(this.leg - lim)} 늦음` : `${this.stops[i].name} · ${fmtS(lim - this.leg)} 남기고 도착`, late ? 'behind' : 'ahead');
    if (i === this.stops.length - 1) { this.finish(); return; }
    this.sound?.cue('beep');
    this.next++;
    this.leg = 0;
    this.lateShown = false;
    this.big(`${this.next + 1}교시 ${this.stops[this.next].name}`);
    this.fillTable();
    this.placeDoor();
  }

  finish() {
    this.state = 'done';
    this.sound?.cue('buzzer');
    this.big('수업 끝!');
    this.fillTable();
    const pl = this.player;
    pl.enabled = false;
    pl.speed = 0;
    this.door.visible = false;
    const late = this.lates.filter(Boolean).length;
    const rec = { id: Date.now(), at: Date.now(), time: Math.round(this.time * 10) / 10, late, splits: this.splits,
      hero: pl.actor.id, peeks: this.easy ? PEEKS - this.peeks : undefined };
    const prev = this.best;
    const { rank, total } = addRecord(this.set.id, this.easy, rec);
    setTimeout(() => { if (this.state === 'done') this.results(true, { rec, rank, total, prev }); }, 1300);
  }

  // ---------------------------------------------------------------- the look from above (easy round)
  peek() {
    if (!this.easy || this.state !== 'play' || this.peekT > 0 || this.peeks <= 0) return;
    this.peeks--;
    this.peekT = PEEK_T;
    this.player.enabled = false;
    this.player.speed = 0;
    this.big('');
  }
  endPeek() {
    if (!(this.peekT > 0) && !this.peeking) return;
    this.peekT = 0;
    this.peeking = false;
    if (this.state === 'play') this.player.enabled = true;
    this.player.cam.ready = false;          // (the walk's camera snaps back behind the walker)
  }
  // high over the way from the walker to the door, the walker at the near edge and the door further up the picture
  peekCam() {
    this.peeking = true;
    const pl = this.player, s = this.stops[this.next], cam = this.camera;
    const dx = s.x - pl.x, dy = s.y - pl.y, d = Math.hypot(dx, dy) || 1, ux = dx / d, uy = dy / d;
    const mx = (pl.x + s.x) / 2, my = (pl.y + s.y) / 2, gh = (pl.pos.y + s.h) / 2;
    const h = Math.max(90, d * 0.85 + 50);
    cam.position.set(mx - ux * h * 0.45, gh + h, -(my - uy * h * 0.45));
    cam.lookAt(mx, gh, -my);
    const { tag } = this.doorParts;
    tag.position.y = 12 + h * 0.06;
    tag.scale.set(h * 0.22, h * 0.055, 1);
  }

  // ---------------------------------------------------------------- HUD
  hudEl() {
    if (this.hud) return this.hud.el;
    const el = document.createElement('div');
    el.id = 'classhud';
    el.innerHTML = '<div class="clock"><small>지금</small><b>9:50</b><span></span></div>'
      + '<div class="goal"><small></small><b></b><span></span></div>'
      + '<div class="way"><i></i><span></span></div>'
      + '<button type="button" class="peek">조감도<kbd>M</kbd><span></span></button>';
    if (this.coarse) el.querySelector('.peek kbd').remove();
    document.body.appendChild(el);
    const table = document.createElement('ol');
    table.id = 'classtable';
    document.body.appendChild(table);
    const big = document.createElement('div');
    big.id = 'classbig';
    document.body.appendChild(big);
    const split = document.createElement('div');
    split.id = 'classsplit';
    document.body.appendChild(split);
    el.querySelector('.peek').addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); this.peek(); });
    this.hud = { el, table, big, split, clock: el.querySelector('.clock b'), left: el.querySelector('.clock span'),
      goalK: el.querySelector('.goal small'), goal: el.querySelector('.goal b'), sub: el.querySelector('.goal span'),
      arrow: el.querySelector('.way i'), dist: el.querySelector('.way span'), peek: el.querySelector('.peek'), peeks: el.querySelector('.peek span') };
    return el;
  }

  // the timetable at the side: the classes done struck through, the next one marked
  fillTable() {
    const h = this.hud;
    h.table.hidden = false;
    h.table.replaceChildren(...this.set.classes.map(([subj, hall], k) => {
      const li = document.createElement('li');
      li.innerHTML = '<span class="k"></span><span class="t"></span><b></b><span class="s"></span>';
      li.querySelector('.k').textContent = `${k + 1}교시`;
      li.querySelector('.t').textContent = hourOf(k);
      li.querySelector('b').textContent = hall;
      li.querySelector('.s').textContent = subj;
      const done = k < this.next || this.state === 'done';
      li.classList.toggle('done', done);
      li.classList.toggle('now', !done && k === this.next);
      if (k > 0 && k <= this.lates.length) li.classList.toggle('late', this.lates[k - 1]);
      return li;
    }));
  }

  drawHud() {
    const h = this.hud;
    if (!h || !this.set) return;
    const k = Math.min(this.next, this.stops.length - 1), lim = this.limits[k - 1];
    const u = this.state === 'count' ? 0 : this.state === 'done' ? 1 : this.leg / lim;
    const set = (el, t) => { if (el.textContent !== t) el.textContent = t; };
    set(h.clock, this.state === 'done' ? hourOf(k) : clockAt(k - 1, u));
    const left = lim - (this.state === 'count' ? 0 : this.leg);
    set(h.left, this.state === 'done' ? '수업 끝' : left >= 0 ? `남은 ${fmtS(left)}` : `${fmtS(-left)} 늦음`);
    h.el.classList.toggle('late', this.state === 'play' && left < 0);
    h.el.classList.toggle('hurry', this.state === 'play' && left >= 0 && left < 15);
    set(h.goalK, `${k + 1}교시 ${hourOf(k)}`);
    set(h.goal, this.stops[k].name);
    set(h.sub, this.set.classes[k][0]);
    const g = this.stops[k], show = this.easy && this.state !== 'done';
    h.arrow.parentElement.hidden = !show;
    h.peek.hidden = !this.easy;
    h.peek.disabled = this.peeks <= 0 || this.state !== 'play';
    set(h.peeks, `${this.peeks}`);
    if (show) {
      const pl = this.player, d = this.camera.getWorldDirection(this._dir);
      const look = Math.atan2(d.x, -d.z), to = Math.atan2(g.x - pl.x, g.y - pl.y);
      h.arrow.style.transform = `rotate(${wrapAngle(to - look).toFixed(3)}rad)`;
      set(h.dist, `${Math.round(Math.hypot(g.x - pl.x, g.y - pl.y))} m`);
    }
  }

  big(text) {
    const el = this.hud?.big;
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('small', text.length > 1);
    el.classList.remove('pop'); void el.offsetWidth;
    if (text) { el.classList.add('pop'); this.bigT = text.length > 1 ? 1.4 : 0.9; }
  }
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
      el.id = 'classresult';
      el.innerHTML = '<div><h2></h2><p class="big"></p><p class="best"></p><table class="legs"></table><ol class="ranks"></ol>'
        + '<div class="btns"><button type="button" class="again">다시 하기</button><button type="button" class="other">다른 시간표</button></div>'
        + '<button type="button" class="quit">그만하고 산책하기</button></div>';
      document.body.appendChild(el);
      el.querySelector('.again').addEventListener('click', (e) => { e.currentTarget.blur(); this.start(); });
      el.querySelector('.other').addEventListener('click', (e) => { e.currentTarget.blur(); this.results(false); this.openPicker(); });
      el.querySelector('.quit').addEventListener('click', (e) => { e.currentTarget.blur(); this.stop(); });
    }
    const { rec, rank, total, prev } = info;
    el.querySelector('h2').textContent = `${this.set.name}${this.easy ? ' · 쉬운 판' : ''}`;
    el.querySelector('.big').textContent = rec.late ? `지각 ${rec.late}번` : '지각 없이 다 들었어요!';
    el.querySelector('.big').classList.toggle('late', rec.late > 0);
    const be = el.querySelector('.best'), top = rank === 1;
    be.textContent = `${fmt(rec.time)} · ${top
      ? (prev ? '새 기록!' : '첫 기록!')
      : `이 브라우저 ${rank}위 (${total}번 가운데)`}${this.easy ? ` · 조감도 ${rec.peeks}번` : ''}`;
    be.classList.toggle('new', top);
    el.querySelector('.legs').replaceChildren(...this.splits.map((t, i) => {
      const tr = document.createElement('tr'), lim = this.limits[i];
      tr.innerHTML = '<td class="k"></td><td class="n"></td><td class="t"></td><td class="r"></td>';
      tr.querySelector('.k').textContent = `${i + 2}교시`;
      tr.querySelector('.n').textContent = `${this.stops[i].name} → ${this.stops[i + 1].name}`;
      tr.querySelector('.t').textContent = `${fmtS(t)} / ${fmtS(lim)}`;
      tr.querySelector('.r').textContent = this.lates[i] ? '지각' : '출석';
      tr.classList.toggle('late', this.lates[i]);
      return tr;
    }));
    const list = records(this.set.id, this.easy).slice(0, 5);
    el.querySelector('.ranks').replaceChildren(...list.map((r, i) => {
      const li = document.createElement('li');
      li.classList.toggle('me', r.id === rec.id);
      li.innerHTML = '<span class="n"></span><span class="who"></span><span class="t"></span>';
      li.querySelector('.n').textContent = `${i + 1}`;
      li.querySelector('.who').textContent = `${HERO[r.hero]?.name ?? ''} · ${day(r.at)}`;
      li.querySelector('.t').textContent = `${fmt(r.time)}${r.late ? ` · 지각 ${r.late}` : ''}`;
      return li;
    }));
    el.hidden = false;
    el.querySelector('.again').focus({ preventScroll: true });
  }
  get resultsOpen() { return !!this.resEl && !this.resEl.hidden; }
}
