// 연고전 응원 연습 (the title card's and the settings card's 「응원 연습」): a rhythm game on 대강당's forecourt in
// October. You stand in the front row of a block of students facing the porch, where a cheerleader leads; signs come
// down four lanes (박수, 만세, 어깨동무 and 뛰기) and are pressed on the beat. The block and the leader do every sign on
// the beat themselves, so the one standing still is you.
//  - the music is a drum pattern made here (audio.js's building blocks): the big drum, the snare, a tick on the
//    off-beats, and the crowd's claps, shouts and landings on the signs. No cheering song, words or recording
//  - the signs are timed by the game's clock (the loop's dt), not the wall's: a key's moment is placed between the
//    frame before it and the one after by its event time, so a slow frame takes nothing from the player
//  - the moves are built over 'idle' (no clip in the rig claps or jumps): the hands by two-bone IK (armpose.js
//    ArmPose), the knees' bounce and the sway by Stance, the fists by Hands.curl, a jump by lifting the holder
//  - every game is kept in this browser per beat (score, the longest combo, the hits)
// Loaded only when the picker opens (main.js).
import * as THREE from 'three';
import { play, STUDENTS, HERO, crowdLook } from './characters.js';
import { ArmPose, Stance, Hands } from './armpose.js';
import { lineTime } from './talk.js';
import { safeGet, safeSet, mulberry } from './util.js';
import { tallOf } from './who.js';
import './cheer.css';

// the four lanes, left to right: what the sign is, its keys and its colour
export const LANES = [
  { id: 'clap', name: '박수', keys: ['ArrowLeft', 'KeyA'], key: '←', color: '#ffcf3a' },
  { id: 'up', name: '만세', keys: ['ArrowUp', 'KeyW'], key: '↑', color: '#ff8a65' },
  { id: 'sway', name: '어깨동무', keys: ['ArrowRight', 'KeyD'], key: '→', color: '#62d0c6' },
  { id: 'jump', name: '뛰기', keys: ['Space', 'ArrowDown', 'KeyS'], key: 'Space', color: '#93b6ff' },
];
const MOVES = LANES.map((l) => l.id);
const CALL = { clap: '박수!', up: '만세!', sway: '어깨동무!', jump: '뛰어!' };     // the leader's call before a new sign

// the beats: a bar is eight eighth notes, c 박수 · u 만세 · s 어깨동무 (left and right by turns) · j 뛰기 · . nothing.
// 짝짝 짝짝짝 and 삼삼칠 박수 are the clapping everybody knew; the rest is made up for the game
export const CHARTS = [
  { id: 'easy', name: '천천히', bpm: 84, lead: 2.0, desc: '한 박에 하나씩. 박수와 만세부터',
    bars: ['c...c...', 'c...c...', 'c.c.c.c.', 'c.c.c.c.', 'u.......', 'u.......', 'c.c.u...', 'c.c.u...',
      's...s...', 's...s...', 's.s.s.s.', 'c.c.c.c.', 'j.......', 'j.......', 'c.c.u...', 'c.c.j...',
      's...s...', 's.s.s.s.', 'c.c.u...', 'u...j...'] },
  { id: 'normal', name: '보통', bpm: 100, lead: 1.6, desc: '짝짝 짝짝짝, 삼삼칠 박수가 섞여요',
    bars: ['c.c.c.c.', 'c.c.ccc.', 'c.c.c.c.', 'c.c.ccc.', 'u...u...', 'c.c.u...', 'u...u...', 'c.c.u.u.',
      's.s.s.s.', 's.s.s.s.', 'c.c.ccc.', 'u...j...', 'ccc.ccc.', 'ccccccc.', 's.s.s.s.', 'j...j...',
      'c.c.u...', 'c.c.u...', 's.s.c.c.', 's.s.c.c.', 'u.u.j...', 'ccc.ccc.', 'ccccccc.', 'u...j...'] },
  { id: 'hard', name: '빠르게', bpm: 124, lead: 1.25, desc: '엇박과 바뀌는 동작. 응원단 수준',
    bars: ['c.c.ccc.', 'c.c.ccc.', 'u.c.u.c.', 'u.c.u.c.', 's.s.s.s.', 's.s.cc.c', 'j...c.c.', 'j...u...',
      'ccc.ccc.', 'ccccccc.', 'u.cc.cu.', 's.s.u.u.', 'c.cc.cc.', 'u...j...', 's.s.s.cc', 's.s.s.u.',
      'j...c.c.', 'j...c.c.', 'uccucc..', 'u.u.j...', 's.s.c.cc', 's.s.u.cc', 'j...j...', 'c.c.ccc.',
      'ccc.ccc.', 'ccccccc.', 'u.s.u.s.', 'c.c.j...', 'cc.cc.u.', 'cc.cc.u.', 's.s.s.s.', 'u...j...'] },
];
export const chartOf = (id) => CHARTS.find((c) => c.id === id);
const lengthOf = (c) => c.bars.length * 8 * 30 / c.bpm;

// timing windows (s either side of the beat) and what each is worth
const JUDGE = [
  { w: 0.045, name: '최고!', cls: 'perfect', pts: 1000, acc: 1 },
  { w: 0.09, name: '좋아!', cls: 'great', pts: 700, acc: 0.7 },
  { w: 0.14, name: '괜찮아', cls: 'good', pts: 400, acc: 0.4 },
];
const LINE = 24;                     // the line: this far over the lanes' foot (px)
const LATE = JUDGE[JUDGE.length - 1].w;
const KEY = 'y97-cheer-records', MAX = 30;
const VERDICT = [[0.95, '응원단장감!'], [0.85, '응원단 합격'], [0.7, '목이 좀 풀렸어요'], [0.5, '연습이 더 필요해요'], [0, '내일 또 나와요']];

// ---------------------------------------------------------------- the place: 대강당's forecourt
// d: metres out from the hall's front (its OSM outline, 대강당 앞 돌계단 in build_campus.py), s: along it to the north.
// The porch (the top of the ten steps) is level 1.6 m over the forecourt from d 0 to 5.5, s -16 to 16; the forecourt
// is level from d 9 to 28. The court (hoops.js) takes s 4 to 19, so the block stands south of it
const F0 = [55.47, 44.71], AU = [0.255, 0.967], AN = [-0.967, 0.255];
const at = (d, s) => [F0[0] + AN[0] * d + AU[0] * s, F0[1] + AN[1] * d + AU[1] * s];
const S0 = -7;                       // the block's middle and the leader's (s)
const ROW_D = [12.2, 13.6, 15.0], COL = 0.78;       // rows (d) and the spacing in a row: shoulder to shoulder
const LEADER_D = 4.6;                 // (the porch's railing runs at 5.5)
const FACE_HALL = Math.atan2(-AN[0], AN[1]), FACE_OUT = Math.atan2(AN[0], -AN[1]);   // three's heading (forward = sin h, cos h)
const CLEAR_R = 15;                  // the walk's crowd is kept out of sight this close to the block's middle

// ---------------------------------------------------------------- records (this browser only)
function loadAll() {
  let all;
  try { all = JSON.parse(safeGet(KEY) || '{}'); } catch { all = {}; }
  return all && typeof all === 'object' && !Array.isArray(all) ? all : {};
}
export function records(id) {
  const list = loadAll()[id];
  return (Array.isArray(list) ? list : []).filter((r) => r && Number.isFinite(r.score)).sort((a, b) => b.score - a.score || a.at - b.at);
}
function addRecord(id, rec) {
  const all = loadAll(), list = records(id);
  list.push(rec);
  list.sort((a, b) => b.score - a.score || a.at - b.at);
  all[id] = list.slice(0, MAX);
  safeSet(KEY, JSON.stringify(all));
  return { rank: list.indexOf(rec) + 1, total: list.length };
}
const day = (ms) => { const d = new Date(ms); return `${d.getMonth() + 1}/${d.getDate()}`; };
const num = (n) => n.toLocaleString('ko-KR');

// the signs of a chart: { t: s from the first bar, lane, dir (어깨동무: -1 / 1 by turns) }
function notesOf(c) {
  const e = 30 / c.bpm, out = [];
  let sway = 0;
  c.bars.forEach((b, m) => {
    for (let i = 0; i < 8; i++) {
      const lane = 'cusj'.indexOf(b[i]);
      if (lane < 0) continue;
      out.push({ t: (m * 8 + i) * e, lane, dir: lane === 2 ? (sway++ % 2 ? 1 : -1) : 0, hit: null, el: null });
    }
  });
  return out;
}

// the drums under it, and the crowd's sounds on the signs: { t, kind }
function drumsOf(c, notes) {
  const b = 60 / c.bpm, ev = [], n = c.bars.length;
  for (let k = 0; k < 4; k++) ev.push({ t: (k - 4) * b, kind: k === 3 ? 'rim2' : 'rim' });
  for (let m = 0; m < n; m++) {
    const t0 = m * 4 * b;
    for (let k = 0; k < 4; k++) {
      ev.push({ t: t0 + k * b, kind: k % 2 ? 'snare' : 'kick' });
      ev.push({ t: t0 + (k + 0.5) * b, kind: 'tick' });
    }
    if (m % 4 === 0) ev.push({ t: t0, kind: 'cymbal' });
    if (m % 4 === 3) for (let k = 1; k < 4; k++) ev.push({ t: t0 + (3 + k / 4) * b, kind: 'snare2' });     // a fill into the next four
  }
  ev.push({ t: n * 4 * b, kind: 'kick' }, { t: n * 4 * b, kind: 'cymbal' }, { t: n * 4 * b + 0.05, kind: 'roar' });
  for (const x of notes) {
    const id = MOVES[x.lane];
    if (id === 'clap') ev.push({ t: x.t, kind: 'clap' });
    else if (id === 'up') ev.push({ t: x.t, kind: 'hey' });
    else if (id === 'jump') ev.push({ t: x.t + 0.52, kind: 'stomp' });
  }
  return ev.sort((p, q) => p.t - q.t);
}

const smooth = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));
// up in a, held h, down in r (s since the move began)
const env = (s, a, h, r) => (s < 0 ? 0 : s < a ? smooth(s / a) : s < a + h ? 1 : s < a + h + r ? 1 - smooth((s - a - h) / r) : 0);

const _v = new THREE.Vector3(), _w = new THREE.Vector3(), _q = new THREE.Quaternion();

// the shins of a figure as it stands (Stance needs them): each foot from its knee, in the knee's frame
function shinOf(a) {
  a.holder.updateMatrixWorld(true);
  return ['L', 'R'].map((s) => {
    const knee = a.root.getObjectByName('LowerLeg' + s), foot = a.root.getObjectByName('Foot' + s);
    const kq = knee.getWorldQuaternion(new THREE.Quaternion()).invert();
    return foot.getWorldPosition(new THREE.Vector3()).sub(knee.getWorldPosition(new THREE.Vector3())).applyQuaternion(kq);
  });
}

// one of those doing the moves: the leader, a student of the block, or you
class Performer {
  constructor(a, { lag = 0, amp = 1 } = {}) {
    this.a = a;
    this.lag = lag;
    this.amp = amp;
    this.last = { clap: -9, up: -9, sway: -9, jump: -9 };
    this.swayDir = 1;
    this.baseY = 0;
    play(a, 'idle', { fade: 0 });
    a.mixer.update(0.01);
    this.pose = new ArmPose(a);
    this.stance = new Stance(a, shinOf(a));
    this.hands = new Hands(a);
    this.arms = ['L', 'R'].map((s) => ({ up: a.root.getObjectByName('UpperArm' + s), wrist: a.root.getObjectByName('Wrist' + s) }));
    this.T = [new THREE.Vector3(), new THREE.Vector3()];
    this.H = [new THREE.Vector3(), new THREE.Vector3()];
  }

  // stand at campus (x, y) on h, facing heading; the sway's sign: which way of the figure's is the hall's north
  place(x, y, h, heading) {
    const hd = this.a.holder;
    hd.position.set(x, h, -y);
    hd.rotation.set(0, heading, 0);
    this.a.heading = heading;
    this.baseY = h;
    hd.updateMatrixWorld(true);
    const ax = _v.set(1, 0, 0).applyQuaternion(hd.quaternion);
    this.north = Math.sign(ax.x * AU[0] - ax.z * AU[1]) || 1;
    this.sL = Math.sign(hd.worldToLocal(this.arms[0].up.getWorldPosition(_w)).x) || 1;
  }

  reset() {
    for (const m of MOVES) this.last[m] = -9;
    this.a.holder.position.y = this.baseY;
    this.stance.apply();
    this.hands.curl(0, 0); this.hands.curl(1, 0);
    play(this.a, 'idle', { fade: 0.3 });
  }

  // the move begins at song time s (its peak a moment later); dir: 어깨동무's way (1: the hall's north)
  start(move, s, dir = 0) {
    this.last[move] = s;
    if (dir) this.swayDir = dir;
  }

  // after the mixer: the body, then the arms and the hands, for song time s; beat: 0..1 through the beat
  apply(s, beat, playing) {
    const L = this.last, a = this.a, hd = a.holder, amp = this.amp;
    const wc = env(s - L.clap, 0.07, 0.06, 0.3), wu = env(s - L.up, 0.1, 0.2, 0.35);
    const ws = env(s - L.sway, 0.15, 0.85, 0.5), wj = env(s - L.jump, 0.1, 0.3, 0.3);
    const lean = env(s - L.sway, 0.18, 0.14, 0.4) * this.swayDir * this.north * amp;
    // the knees give on every beat; a jump crouches, goes up 0.3 m and lands in a crouch
    let drop = playing ? 0.022 * (0.5 + 0.5 * Math.cos(2 * Math.PI * beat)) : 0, hop = 0;
    const sj = s - L.jump;
    if (sj >= 0 && sj < 0.08) drop += 0.08 * (sj / 0.08);
    else if (sj >= 0.08 && sj < 0.52) { const u = (sj - 0.08) / 0.44; hop = 0.3 * amp * 4 * u * (1 - u); drop = 0; }
    else if (sj >= 0.52 && sj < 0.74) drop += 0.08 * (1 - smooth((sj - 0.52) / 0.22));
    hd.position.y = this.baseY + hop;
    this.stance.apply({ drop, side: 0.22 * lean, sway: 0.06 * lean });
    const W = Math.min(1, wc + wu + ws + wj);
    if (W > 0.01 && this.pose.ok) {
      hd.updateMatrixWorld(true);
      for (let i = 0; i < 2; i++) {
        const sg = i === 0 ? this.sL : -this.sL;
        const sh = hd.worldToLocal(this.arms[i].up.getWorldPosition(_v));
        const rest = hd.worldToLocal(this.arms[i].wrist.getWorldPosition(_w));
        const T = this.T[i].set(0, 0, 0), H = this.H[i].set(0, 0, 0);
        const add = (w, x, y, z, hx, hy, hz) => { if (w > 0) { T.x += w * x; T.y += w * y; T.z += w * z; H.x += w * hx; H.y += w * hy; H.z += w * hz; } };
        add(wu, sh.x + sg * 0.07, sh.y + 0.46, sh.z + 0.05, sg, 0, -0.2);
        add(wc, sg * 0.035, sh.y + 0.02, sh.z + 0.28, sg, -0.5, 0);
        add(ws, sh.x + sg * 0.42, sh.y + 0.03, sh.z - 0.05, 0, -1, -0.3);
        add(wj, sh.x + sg * 0.12, sh.y + 0.4, sh.z + 0.1, sg, 0, 0);
        const sum = wu + wc + ws + wj;
        T.multiplyScalar(1 / sum);
        // from where the clip has the hand, by a way bowed forward (the bones' own blend takes the short way: up
        // behind the back)
        T.lerpVectors(rest, T, W);
        T.z += 0.22 * Math.sin(Math.PI * W) * (1 - wc / sum);
        hd.localToWorld(T);
        H.normalize().applyQuaternion(hd.getWorldQuaternion(_q));
      }
      this.pose.apply(this.T, this.H, Math.min(1, W / 0.15));
    }
    const fist = Math.min(1, wu + wj) * 0.9;
    this.hands.curl(0, fist); this.hands.curl(1, fist);
  }
}

export class Cheer {
  // groundAt(x, y): the walk's height there; ensure(x, y): chunks.ensure; crowd: the walk's (kept out of the way);
  // season() / setSeason(v): main.js's; onBegin(msg): main.js takes the walk on; onQuit: back to the walk
  constructor({ scene, cast, player, sound, groundAt, ensure, crowd, shadows, blobs, bubbles, mobile, season, setSeason, onBegin, onQuit }) {
    Object.assign(this, { scene, cast, player, sound, groundAt, ensure, crowd, shadows, blobs, bubbles, mobile, season, setSeason, onBegin, onQuit });
    this.state = 'off';                 // off | count | play | done
    this.view = 'front';
    this.block = null;                  // the leader and the students (made the first time)
    this.heroes = {};                   // actor id -> Performer: you
    this.hidden = new Set();
    this.presses = [];
    this.t = 0;
    addEventListener('keydown', (e) => this.key(e), true);
    if (window.__y97) window.__y97.cheer = this;
  }

  get on() { return this.state !== 'off'; }

  key(e) {
    if (e.code === 'Escape') {
      if (this.pickOpen) { e.stopImmediatePropagation(); this.closePicker(); }
      else if (this.resultsOpen) { e.stopImmediatePropagation(); this.stop(); }
      return;
    }
    if ((this.state !== 'count' && this.state !== 'play') || this.paused) return;
    if (/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
    const lane = LANES.findIndex((l) => l.keys.includes(e.code));
    if (lane >= 0) {
      e.preventDefault();
      e.stopImmediatePropagation();
      if (!e.repeat) this.press(lane, e.timeStamp);
    } else if (e.code === 'KeyV') { e.stopImmediatePropagation(); if (!e.repeat) this.toggleView(); }
    else if (/^Key[BEMR]$|^Enter$/.test(e.code)) e.stopImmediatePropagation();   // (no map, tour or memory card meanwhile)
  }

  // ---------------------------------------------------------------- the picker
  openPicker() {
    let el = this.pickEl;
    if (!el) {
      el = this.pickEl = document.createElement('div');
      el.id = 'cheerpick';
      el.innerHTML = '<div><h2>연고전 응원 연습</h2><p class="lead">10월, 대강당 앞마당. 응원단장을 따라 박자에 맞춰 응원 동작을 해요.</p>'
        + '<ul class="charts"></ul><p class="how"></p><button type="button" class="close">닫기</button></div>';
      document.body.appendChild(el);
      el.querySelector('.close').addEventListener('click', () => this.closePicker());
      el.addEventListener('click', (e) => { if (e.target === el) this.closePicker(); });
    }
    el.querySelector('.charts').replaceChildren(...CHARTS.map((c) => {
      const li = document.createElement('li'), best = records(c.id)[0];
      li.innerHTML = '<button type="button"><b></b><span class="desc"></span><span class="meta"></span></button>';
      li.querySelector('b').textContent = c.name;
      li.querySelector('.desc').textContent = c.desc;
      li.querySelector('.meta').textContent = `${c.bpm} BPM · ${Math.round(lengthOf(c))}초 · 동작 ${notesOf(c).length}개${best ? ` · 최고 ${num(best.score)}점` : ''}`;
      li.querySelector('button').addEventListener('click', (e) => { e.currentTarget.blur(); this.closePicker(); this.start(c.id); });
      return li;
    }));
    el.querySelector('.how').textContent = this.touchy()
      ? '내려오는 동작이 아래 줄에 닿을 때 그 버튼을 눌러요.'
      : '내려오는 동작이 아래 줄에 닿을 때 ← 박수 · ↑ 만세 · → 어깨동무 · 스페이스 뛰기. V로 보는 쪽을 바꿔요.';
    el.hidden = false;
    el.querySelector('.charts button')?.focus({ preventScroll: true });
  }
  closePicker() { if (this.pickEl) this.pickEl.hidden = true; }
  get pickOpen() { return !!this.pickEl && !this.pickEl.hidden; }
  touchy() { return this.mobile || matchMedia('(pointer: coarse)').matches; }

  // ---------------------------------------------------------------- the block
  async makeBlock() {
    if (this.block) return this.block;
    const rows = this.mobile ? 2 : 3, cols = this.mobile ? 7 : 9;
    const r = mulberry(1997);
    const pool = STUDENTS.filter((id) => id !== 'p04' && id !== 'p09');
    const people = [];
    let n = 0;
    for (let i = 0; i < rows; i++) for (let k = 0; k < cols; k++) {
      const front = i === 0 && k === (cols - 1) >> 1;            // (your place)
      const id = pool[(i * cols + k * 5 + 3) % pool.length];
      const a = front ? null : this.cast.make(id, null, crowdLook(id, 700 + n++));
      people.push({ a, row: i, col: k - (cols - 1) / 2, front, lag: 0.005 + r() * 0.04, amp: 0.85 + r() * 0.25 });
      if (a) await new Promise((res) => requestAnimationFrame(res));     // (spread over frames: a model is a few ms)
    }
    const leaders = { p04: this.cast.make('p04', null), p09: this.cast.make('p09', null) };
    for (const p of people) if (p.a) { p.perf = new Performer(p.a, p); this.shadows?.addDynamic(p.a.holder); this.blobs?.addPerson(p.a); }
    for (const a of Object.values(leaders)) { this.shadows?.addDynamic(a.holder); this.blobs?.addPerson(a); }
    this.block = { people, leaders, lead: {}, rows, cols };
    return this.block;
  }

  heroPerf() {
    const a = this.player.actor;
    let p = this.heroes[a.id];
    if (!p || p.a !== a) p = this.heroes[a.id] = new Performer(a, { lag: 0, amp: 1 });
    return p;
  }

  // ---------------------------------------------------------------- a game
  async start(id = this.chart?.id) {
    const c = chartOf(id);
    if (!c || this.starting) return;
    this.starting = true;
    try {
      const [cx, cy] = at(LEADER_D, S0);
      const wait = this.ensure?.(cx, cy);
      if (wait) await wait;
      await this.makeBlock();
    } finally { this.starting = false; }
    this.results(false);
    this.halt();
    this.chart = c;
    this.best = records(c.id)[0] || null;
    if (this.season?.() !== 'autumn') this.setSeason?.('autumn');     // (연고전 is in October: the leaves turn)
    this.onBegin?.(`${c.name} · ${this.touchy() ? '동작이 줄에 닿을 때 아래 버튼을' : '동작이 줄에 닿을 때 ← ↑ → 스페이스를'} 눌러요`);
    if (this.crowd?.hidden) this.crowd.hidden = false;      // (the running game hides it: back to the walk's)
    const pl = this.player, B = this.block;
    // you, in the middle of the front row
    const [hx, hy] = at(ROW_D[0], S0);
    pl.teleport(hx, hy);
    pl.heading = FACE_HALL;
    pl.actor.holder.rotation.y = FACE_HALL;
    pl.enabled = false; pl.scripted = true;
    pl.keys.clear(); pl.stick.set(0, 0); pl.speed = 0;
    this.me = this.heroPerf();
    this.me.place(hx, hy, pl.pos.y, FACE_HALL);
    // the block round you, and the leader on the porch (in the Yonsei jumper; in the Yonsei tee if that is you)
    this.perfs = [];
    for (const p of B.people) {
      if (p.front) continue;
      const [x, y] = at(ROW_D[p.row], S0 + p.col * COL);
      const h = this.groundAt(x, y);
      if (!p.a.holder.parent) this.scene.add(p.a.holder);
      p.perf.place(x, y, h, FACE_HALL);
      p.perf.reset();
      p.a.mixer.setTime(p.lag * 40);
      this.perfs.push(p.perf);
    }
    const lid = pl.actor.id === 'p04' ? 'p09' : 'p04';
    for (const [k, a] of Object.entries(B.leaders)) if (k !== lid && a.holder.parent) this.scene.remove(a.holder);
    const la = B.leaders[lid];
    this.leader = B.lead[lid] ||= new Performer(la, { lag: 0, amp: 1.15 });
    this.leaderTop = tallOf(lid);
    const [lx, ly] = at(LEADER_D, S0);
    if (!la.holder.parent) this.scene.add(la.holder);
    this.leader.place(lx, ly, this.groundAt(lx, ly), FACE_OUT);
    this.leader.reset();
    this.perfs.push(this.leader);
    this.me.reset();
    // the game
    this.notes = notesOf(c);
    this.drums = drumsOf(c, this.notes);
    this.beat = 60 / c.bpm;
    this.song = -4 * this.beat - 0.6;      // (a breath before the count)
    this.end = lengthOf(c);
    this.di = 0; this.ci = 0;
    for (const p of this.perfs) p.nextI = 0;
    this.presses.length = 0;
    this.wall = performance.now();
    Object.assign(this, { score: 0, combo: 0, maxCombo: 0, counts: [0, 0, 0, 0] });
    this.cues = this.callsOf(this.notes);
    this.state = 'count';
    this.paused = false;
    this.shown = null;
    this.camera(true);
    this.hudEl().hidden = false;
    this.layout();
    this.drawHud();
    this.say(this.leader, '자, 응원 연습 시작합니다!', 0);
  }

  // the leader's calls: a beat before a sign that differs from the one before it (not closer than two seconds)
  callsOf(notes) {
    const out = [];
    let prev = -1, lastT = -9;
    for (const n of notes) {
      if (n.lane !== prev && n.t - lastT > 2) { out.push({ t: n.t - this.beat * 1.5, text: CALL[MOVES[n.lane]] }); lastT = n.t; }
      prev = n.lane;
    }
    return out;
  }

  // the camera: before the block looking at you (front) or behind you looking at the leader (back)
  camera(snap = false) {
    const g = this.groundAt(...at(ROW_D[0], S0));
    const P = (d, s, h) => new THREE.Vector3(at(d, s)[0], g + h, -at(d, s)[1]);
    const low = this.touchy() ? 1.0 : 0;        // (the pads below take the lower half of a phone: you higher up)
    const o = this.view === 'front'
      ? { pos: P(7.4, S0 + 1.4, 2.5), look: P(ROW_D[1], S0 + (low ? -0.3 : 1.0), 0.95 - low) }
      : { pos: P(ROW_D[2] + 2.8, S0 + 1.2, 2.9), look: P(LEADER_D + 2, S0 - 0.3, 1.5 - low) };
    this.player.camOverride = snap ? { ...o, k: 1 } : o;
  }
  toggleView() { this.view = this.view === 'front' ? 'back' : 'front'; this.camera(); }

  // the walk's crowd: those who wander in are not seen till the game is over
  clearCrowd() {
    const [cx, cy] = at(ROW_D[1], S0);
    for (const p of this.crowd?.people ?? []) {
      const hd = p.a.holder, near = (hd.position.x - cx) ** 2 + (-hd.position.z - cy) ** 2 < CLEAR_R * CLEAR_R;
      if (near && hd.visible) { hd.visible = false; this.hidden.add(hd); }
      else if (!near && this.hidden.has(hd)) { hd.visible = true; this.hidden.delete(hd); }
    }
  }

  // everybody back as they were (the block goes, you walk)
  halt() {
    for (const hd of this.hidden) hd.visible = true;
    this.hidden.clear();
    if (this.block) {
      for (const p of this.block.people) if (p.a?.holder.parent) this.scene.remove(p.a.holder);
      for (const a of Object.values(this.block.leaders)) if (a.holder.parent) this.scene.remove(a.holder);
    }
    if (this.me) {
      this.me.reset();
      this.player.pos.y = this.me.baseY;
    }
    for (const n of this.notes ?? []) n.el?.remove();
  }

  stop() {
    if (!this.on) return;
    this.state = 'off';
    this.halt();
    const pl = this.player;
    pl.scripted = false;
    pl.camOverride = null;
    pl.cam.ready = false;
    pl.enabled = true;
    if (this.hud) this.hud.el.hidden = true;
    this.judge('');
    this.results(false);
    this.onQuit?.();
  }

  // a lane pressed at the event time ts (performance.now's clock): placed on the game's clock at the next frame
  press(lane, ts = performance.now()) {
    if (this.state !== 'count' && this.state !== 'play') return;
    this.presses.push({ lane, ts });
    const b = this.hud?.pads[lane];
    if (b) { b.classList.remove('down'); void b.offsetWidth; b.classList.add('down'); }
  }

  // t: the loop's clock; paused: the settings card, a memory card or the map is open (the song waits)
  update(dt, t, paused) {
    if (!this.on) return;
    this.t = t;
    const now = performance.now(), wall0 = this.wall;
    this.wall = now;
    this.paused = paused;
    if (paused) { this.presses.length = 0; return; }
    const s0 = this.song, s1 = s0 + dt;
    this.song = s1;
    this.clearCrowd();
    // the presses since the last frame, on the game's clock (between this frame and the one before by their time)
    const span = Math.max(1e-3, now - wall0);
    for (const p of this.presses) {
      const u = Math.min(1, Math.max(0, (p.ts - wall0) / span));
      this.hit(p.lane, s0 + u * dt);
    }
    this.presses.length = 0;
    if (this.auto) for (const n of this.notes) if (!n.hit && n.t <= s1 + (this.autoOff ?? 0) && n.t > s1 - 0.5) this.hit(n.lane, n.t + (this.autoOff ?? 0) + (Math.random() - 0.5) * (this.autoJitter ?? 0));
    // signs gone past unpressed
    for (const n of this.notes) {
      if (n.t > s1 - LATE) break;
      if (!n.hit) { n.hit = 'miss'; this.counts[3]++; this.combo = 0; this.judge('놓침', 'miss'); n.el?.classList.add('gone'); }
    }
    // the count, then the song
    if (this.state === 'count') {
      const k = Math.floor(s1 / this.beat) + 4;
      if (k >= 0 && k !== this.shown && k < 4) { this.shown = k; this.big(['하나', '둘', '셋', '넷'][k]); }
      if (s1 >= 0) this.state = 'play';
    }
    // the block and the leader on the signs (their peak on the beat), the leader's calls
    for (const p of this.perfs) {
      for (let i = p.nextI ?? 0; i < this.notes.length; i++) {
        const n = this.notes[i], go = n.t - 0.07 + p.lag;
        if (go > s1) { p.nextI = i; break; }
        if (go > s0 - 0.25) p.start(MOVES[n.lane], go, n.dir);
        p.nextI = i + 1;
      }
    }
    while (this.ci < this.cues.length && this.cues[this.ci].t <= s1) { this.say(this.leader, this.cues[this.ci].text, 0); this.ci++; }
    this.schedule(s1);
    // the end: the last sign and a bar after it
    if (this.state === 'play' && s1 > this.end + this.beat * 2) this.finish();
    this.animate(dt, s1);
    this.drawHud();
    if (this.bigT !== undefined) { this.bigT -= dt; if (this.bigT <= 0) { this.big(''); this.bigT = undefined; } }
  }

  animate(dt, s) {
    const beat = ((s % this.beat) + this.beat) % this.beat / this.beat;
    const playing = this.state === 'play' && s < this.end + this.beat;
    for (const p of this.perfs) {
      if (p !== this.leader && p.a.holder.parent === null) continue;
      p.a.mixer.update(dt);
      p.apply(s, beat, playing);
    }
    this.me.a.mixer.update(dt);
    this.me.apply(s, beat, playing);
    this.player.pos.y = this.me.a.holder.position.y;
  }

  // a press on the game's clock: the nearest open sign of that lane in the window, and your move at once
  hit(lane, s) {
    // (the move's peak comes a moment after it begins: begun that much before the press, you are on the beat too)
    this.me.start(MOVES[lane], s - 0.05, lane === 2 ? this.nextDir(s) : 0);
    let best = null;
    for (const n of this.notes) {
      if (n.t > s + LATE) break;
      if (n.hit || n.lane !== lane || Math.abs(n.t - s) > LATE) continue;
      if (!best || Math.abs(n.t - s) < Math.abs(best.t - s)) best = n;
    }
    if (!best) return;
    const off = s - best.t, j = JUDGE.findIndex((x) => Math.abs(off) <= x.w);
    const J = JUDGE[j];
    best.hit = J.cls;
    best.off = off;
    this.counts[j]++;
    this.combo++;
    this.maxCombo = Math.max(this.maxCombo, this.combo);
    this.score += Math.round(J.pts * (1 + Math.min(this.combo, 40) * 0.025));
    this.judge(J.name, J.cls, off);
    if (best.el) best.el.classList.add('hit');
    this.voice('tok', 0, j === 0 ? 1 : 0.7);
    if (this.combo && this.combo % 25 === 0) { this.voice('roar', 0, 0.5); this.say(this.leader, `${this.combo} 콤보! 좋아요!`, 0); }
  }
  // 어깨동무 pressed: the way of the sign nearest the press
  nextDir(s) {
    let best = null;
    for (const n of this.notes) if (n.lane === 2 && (!best || Math.abs(n.t - s) < Math.abs(best.t - s))) best = n;
    return best?.dir || 1;
  }

  finish() {
    this.state = 'done';
    const n = this.notes.length, [p, g, o, m] = this.counts;
    const acc = n ? (p + g * 0.7 + o * 0.4) / n : 0;
    const rec = { id: Date.now(), at: Date.now(), score: this.score, combo: this.maxCombo, acc: Math.round(acc * 1000) / 1000,
      counts: [p, g, o, m], hero: this.player.actor.id };
    const prev = this.best;
    const { rank, total } = addRecord(this.chart.id, rec);
    this.say(this.leader, acc >= 0.85 ? '수고했어요! 연고전 때 이대로!' : '수고했어요! 또 연습해요', 0);
    setTimeout(() => { if (this.state === 'done') this.results(true, { rec, rank, total, prev, acc }); }, 1500);
  }

  say(perf, text, delay = 0) {
    if (!perf || !this.bubbles) return;
    const t = this.t + delay;
    this.bubbles.add(perf.a.holder, perf === this.leader ? this.leaderTop : 1.7, text, t, t + Math.min(lineTime(text), 2.2));
  }

  // ---------------------------------------------------------------- sound (audio.js's blocks: nothing recorded)
  // the drums and the crowd's sounds a little ahead, on the audio clock by how far off they are on the game's
  schedule(s) {
    const LOOK = 0.12;
    while (this.di < this.drums.length && this.drums[this.di].t < s + LOOK) {
      const e = this.drums[this.di++];
      if (e.t > s - 0.05) this.voice(e.kind, Math.max(0, e.t - s));
    }
  }

  voice(kind, dt = 0, k = 1) {
    const S = this.sound, ctx = S?.ctx;
    if (!ctx || ctx.state !== 'running') return;
    if (!this.bus || this.bus.context !== ctx) { this.bus = ctx.createGain(); this.bus.gain.value = 0.85; this.bus.connect(S.master); }
    const out = this.bus, at = ctx.currentTime + dt + 0.01;
    const tone = (o) => S._tone(out, { at, ...o }), burst = (o) => S._burst(out, { at, ...o });
    switch (kind) {
      case 'kick':       // 큰북: a low thump falling in pitch, and the skin's slap
        tone({ type: 'sine', f: 118, f1: 46, gain: 0.6, attack: 0.003, decay: 0.42 });
        burst({ type: 'lowpass', f: 380, q: 0.7, gain: 0.18, decay: 0.06 });
        break;
      case 'snare': case 'snare2':
        burst({ type: 'bandpass', f: 1900, q: 0.7, gain: kind === 'snare' ? 0.2 : 0.11, decay: 0.15 });
        tone({ type: 'triangle', f: 230, f1: 180, gain: kind === 'snare' ? 0.12 : 0.06, decay: 0.08 });
        break;
      case 'tick':
        burst({ type: 'highpass', f: 6500, q: 0.7, gain: 0.045, decay: 0.035 });
        break;
      case 'rim': case 'rim2':     // the sticks counting in
        tone({ type: 'square', f: kind === 'rim2' ? 1250 : 940, f1: 700, gain: 0.05, decay: 0.05 });
        burst({ type: 'bandpass', f: 3000, q: 2, gain: 0.08, decay: 0.03 });
        break;
      case 'cymbal':
        burst({ type: 'highpass', f: 5200, q: 0.5, gain: 0.07, attack: 0.002, decay: 0.9 });
        break;
      case 'clap':       // the block's claps: a few hands not quite together
        for (let i = 0; i < 4; i++) S._burst(out, { at: at + i * 0.007, type: 'bandpass', f: 1050 + i * 120, q: 1.1, gain: 0.13, decay: 0.07 });
        burst({ type: 'bandpass', f: 1400, q: 0.6, gain: 0.05, attack: 0.02, decay: 0.2 });
        break;
      case 'hey':        // a short shout of many voices
        burst({ type: 'bandpass', f: 720, f1: 520, q: 2.2, gain: 0.3, attack: 0.025, decay: 0.24, pink: true });
        burst({ type: 'bandpass', f: 1500, f1: 1150, q: 3, gain: 0.12, attack: 0.025, decay: 0.2, pink: true });
        break;
      case 'stomp':
        tone({ type: 'sine', f: 85, f1: 40, gain: 0.32, attack: 0.004, decay: 0.2 });
        burst({ type: 'lowpass', f: 320, q: 0.7, gain: 0.14, decay: 0.1, pink: true });
        break;
      case 'roar':       // the crowd's cheer
        burst({ type: 'bandpass', f: 900, q: 0.6, gain: 0.32 * k, attack: 0.25, decay: 2.2, pink: true });
        burst({ type: 'bandpass', f: 2100, q: 0.9, gain: 0.1 * k, attack: 0.3, decay: 1.8, pink: true });
        break;
      case 'tok':        // your own hit
        tone({ type: 'sine', f: 1180, f1: 900, gain: 0.12 * k, attack: 0.002, decay: 0.06 });
        break;
    }
  }

  // ---------------------------------------------------------------- HUD: the score, the lanes, the word
  hudEl() {
    if (this.hud) return this.hud.el;
    const el = document.createElement('div');
    el.id = 'cheerhud';
    el.innerHTML = '<div class="top"><div class="score"><small>점수</small><b>0</b><span></span></div>'
      + '<div class="combo"><small>콤보</small><b>0</b></div><button type="button" class="view" title="보는 쪽 바꾸기 (V)">시점</button></div>'
      + '<div class="bar"><i></i></div>'
      + '<div class="track"><div class="lanes"></div><div class="pads"></div></div>'
      + '<div class="word"><b></b><span></span></div><div class="big"></div>';
    document.body.appendChild(el);
    const lanes = el.querySelector('.lanes'), pads = el.querySelector('.pads');
    for (const [i, l] of LANES.entries()) {
      const ln = document.createElement('div');
      ln.className = 'lane';
      ln.style.setProperty('--c', l.color);
      lanes.appendChild(ln);
      const b = document.createElement('button');
      b.type = 'button';
      b.style.setProperty('--c', l.color);
      b.innerHTML = `<b>${l.name}</b><kbd>${l.key}</kbd>`;
      b.addEventListener('pointerdown', (e) => { e.preventDefault(); e.stopPropagation(); this.press(i, e.timeStamp); });
      b.addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); });
      pads.appendChild(b);
    }
    const laneEls = [...lanes.children], line = document.createElement('div');
    line.className = 'line';
    lanes.appendChild(line);
    el.querySelector('.view').addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); this.toggleView(); });
    this.hud = { el, lanes: laneEls, pads: [...pads.children], score: el.querySelector('.score b'), best: el.querySelector('.score span'),
      combo: el.querySelector('.combo b'), bar: el.querySelector('.bar i'), word: el.querySelector('.word b'), off: el.querySelector('.word span'),
      wordBox: el.querySelector('.word'), big: el.querySelector('.big'), laneBox: lanes };
    addEventListener('resize', () => this.layout());
    return el;
  }

  layout() {
    if (!this.hud) return;
    this.laneH = (this.hud.laneBox.getBoundingClientRect().height || 300) - LINE;
  }

  drawHud() {
    const h = this.hud;
    if (!h || !this.chart) return;
    const sc = num(this.score);
    if (h.score.textContent !== sc) h.score.textContent = sc;
    const bt = this.best ? `최고 ${num(this.best.score)}` : '첫 기록 도전';
    if (h.best.textContent !== bt) h.best.textContent = bt;
    const cb = String(this.combo);
    if (h.combo.textContent !== cb) h.combo.textContent = cb;
    h.bar.style.transform = `scaleX(${Math.min(1, Math.max(0, this.song / this.end)).toFixed(4)})`;
    // the signs coming down: the line is where they are at their beat
    const lead = this.chart.lead, H = this.laneH, s = this.song;
    for (const n of this.notes) {
      if (n.t - lead > s) break;
      const gone = n.hit && n.hit !== 'miss' ? s - (n.hitAt ??= s) > 0.15 : s - n.t > 0.4;
      if (gone) { if (n.el) { n.el.remove(); n.el = null; n.done = true; } continue; }
      if (n.done) continue;
      if (!n.el) {
        const e = n.el = document.createElement('div');
        e.className = 'note';
        e.textContent = n.lane === 2 ? (n.dir > 0 ? '어깨 ▶' : '◀ 어깨') : LANES[n.lane].name;
        h.lanes[n.lane].appendChild(e);
      }
      const y = (1 - (n.t - s) / lead) * H;
      n.el.style.transform = `translate3d(0, ${y.toFixed(1)}px, 0)`;
    }
  }

  // the word for a press: 최고! · 좋아! · 괜찮아 · 놓침, and early / late under it
  judge(text, cls = '', off = 0) {
    const h = this.hud;
    if (!h) return;
    h.word.textContent = text;
    h.off.textContent = !text || cls === 'perfect' || cls === 'miss' ? '' : off < 0 ? '빨라요' : '늦어요';
    h.wordBox.className = `word ${cls}`;
    void h.wordBox.offsetWidth;
    if (text) h.wordBox.classList.add('pop');
  }

  big(text) {
    const el = this.hud?.big;
    if (!el) return;
    el.textContent = text;
    el.classList.remove('pop'); void el.offsetWidth;
    if (text) { el.classList.add('pop'); this.bigT = this.beat * 0.9; }
  }

  // ---------------------------------------------------------------- the results card
  results(show, info = {}) {
    let el = this.resEl;
    if (!show) { if (el) el.hidden = true; return; }
    if (!el) {
      el = this.resEl = document.createElement('div');
      el.id = 'cheerresult';
      el.innerHTML = '<div><h2></h2><p class="verdict"></p><p class="big"></p><p class="best"></p><ul class="counts"></ul><ol class="ranks"></ol>'
        + '<div class="btns"><button type="button" class="again">다시 하기</button><button type="button" class="other">다른 박자</button></div>'
        + '<button type="button" class="quit">그만하고 산책하기</button></div>';
      document.body.appendChild(el);
      el.querySelector('.again').addEventListener('click', (e) => { e.currentTarget.blur(); this.start(); });
      el.querySelector('.other').addEventListener('click', (e) => { e.currentTarget.blur(); this.results(false); this.openPicker(); });
      el.querySelector('.quit').addEventListener('click', (e) => { e.currentTarget.blur(); this.stop(); });
    }
    const { rec, rank, total, prev, acc } = info;
    el.querySelector('h2').textContent = `응원 연습 · ${this.chart.name}`;
    el.querySelector('.verdict').textContent = `${VERDICT.find(([v]) => acc >= v)[1]} · 정확도 ${Math.round(acc * 100)}%`;
    el.querySelector('.big').textContent = num(rec.score);
    const be = el.querySelector('.best'), top = rank === 1;
    be.textContent = top
      ? (prev ? `새 기록! ${num(rec.score - prev.score)}점 더` : '첫 기록! 다음엔 이 점수와 겨뤄요')
      : `이 브라우저 ${rank}위 (${total}번 가운데) · 최고 ${num(prev.score)}점`;
    be.classList.toggle('new', top);
    const [p, g, o, m] = rec.counts;
    el.querySelector('.counts').replaceChildren(...[['최고', p, 'perfect'], ['좋아', g, 'great'], ['괜찮아', o, 'good'], ['놓침', m, 'miss'], ['최대 콤보', rec.combo, 'combo']].map(([k, v, c]) => {
      const li = document.createElement('li');
      li.className = c;
      li.innerHTML = '<small></small><b></b>';
      li.querySelector('small').textContent = k;
      li.querySelector('b').textContent = v;
      return li;
    }));
    el.querySelector('.ranks').replaceChildren(...records(this.chart.id).slice(0, 5).map((r, i) => {
      const li = document.createElement('li');
      li.classList.toggle('me', r.id === rec.id);
      li.innerHTML = '<span class="n"></span><span class="who"></span><span class="t"></span>';
      li.querySelector('.n').textContent = `${i + 1}`;
      li.querySelector('.who').textContent = `${HERO[r.hero]?.name ?? ''} · ${day(r.at)} · 콤보 ${r.combo}`;
      li.querySelector('.t').textContent = num(r.score);
      return li;
    }));
    el.hidden = false;
    el.querySelector('.again').focus({ preventScroll: true });
  }
  get resultsOpen() { return !!this.resEl && !this.resEl.hidden; }
}
