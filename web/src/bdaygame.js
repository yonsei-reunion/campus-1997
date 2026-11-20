// 생일 축하 (the title card's and the settings card's 「생일 축하」): the birthday scene at 활천대 (birthday.js) as a
// game. The birthday student asks you to bring four friends; they stand in front of halls round the campus, each in
// a look of their own (the HUD's hints: 「중앙도서관 앞 · 노란 카디건에 자주색 숄더백」). Come up to one and press E
// (the button on a phone): they greet you and fall in behind you. With all of them, back to the birthday student
// within the time, and the throw (birthday.js, unchanged) happens with the friends standing round, counting along.
// The friends walk the walker's own trail (the points the walker stood on, so the stairs, narrow paths and walls
// the walker got past): they cannot get stuck on it, and one too far behind is set down on it further on.
// Every run that got there is kept in this browser (the time from the start to the throw).
// Loaded only when the game starts (main.js).
import * as THREE from 'three';
import { play, locomotion, HERO } from './characters.js';
import { lineTime } from './talk.js';
import { tallOf } from './who.js';
import { safeGet, safeSet, wrapAngle } from './util.js';
import './bdaygame.css';

const N = 4;                      // friends to bring
const LIMIT = 300;                // s
const NEAR = 4.0;                 // a friend within this (m) can be asked along
const CALL = 14;                  // a friend waves and calls out once you are this close
const BDAY_NEAR = 4.4;            // the birthday student (birthday.js OFFER_NEAR 4.6)
const GAP0 = 1.1, GAP = 0.95;     // along the trail: the first follower behind the walker, then each to the next
const SNAP = 14;                  // further behind than this along the trail: set down on it closer up
const SHOW = 170;                 // friends drawn within this of the camera
const KEY = 'y97-bday-records', MAX = 50;
const ease = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));

// the friends: a model of the cast, a name and a look (the bag added to the model: bags.js); hints name both
const POOL = [
  { id: 'p02', name: '민수', look: '체크 남방에 남색 백팩', bag: { type: 'backpack', color: '#1f2a46', size: 1 } },
  { id: 'p05', name: '태호', look: '줄무늬 티에 빨간 백팩', bag: { type: 'backpack', color: '#8a2626', size: 1 } },
  { id: 'p16', name: '상우', look: '초록 남방에 카키 크로스백', bag: { type: 'cross', color: '#6e6650', side: -1, size: 1 } },
  { id: 'p13', name: '경희', look: '노란 카디건에 자주색 숄더백', bag: { type: 'shoulder', color: '#5d2229', side: 1, size: 1 } },
  { id: 'p10', name: '혜원', look: '분홍 니트에 베이지 손가방', bag: { type: 'hand', color: '#b4966f', size: 1 } },
  { id: 'p12', name: '미영', look: '크림색 맨투맨에 갈색 미니 백팩', bag: { type: 'mini', color: '#5a3a24', size: 1 } },
  { id: 'p17', name: '은주', look: '청남방에 검은 숄더백', bag: { type: 'shoulder', color: '#1b1b1e', side: 1, size: 1 } },
  { id: 'p15', name: '지혜', look: '줄무늬 티에 파란 백팩', bag: { type: 'backpack', color: '#27458c', size: 1 } },
];
// where they wait: halls round 활천대 within about 250 m (places.js startPlaces: in front of the door)
const HALLS = ['제1공학관', '백주년기념관', '학생회관', '중앙도서관', '체육관', '광혜원', '루스채플', '제2공학관', '장기원 기념관'];
const HELLO = ['어, 누구 생일인데? 가자!', '생일? 당연히 가야지!', '분수에 빠뜨리러? 좋아!', '오늘이었어? 같이 가!'];
const shuffle = (a) => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
// 민수야 / 경희야, 태호야: the call's ending by the name's last syllable
const call = (name) => { const c = name.charCodeAt(name.length - 1) - 0xac00; return name + (c >= 0 && c % 28 ? '아' : '야'); };

// ---------------------------------------------------------------- records (this browser only)
export function records() {
  let list;
  try { list = JSON.parse(safeGet(KEY) || '[]'); } catch { list = []; }
  return (Array.isArray(list) ? list : []).filter((r) => r && Number.isFinite(r.time)).sort((a, b) => a.time - b.time || a.at - b.at);
}
function addRecord(rec) {
  const list = records();
  list.push(rec);
  list.sort((a, b) => a.time - b.time || a.at - b.at);
  safeSet(KEY, JSON.stringify(list.slice(0, MAX)));
  return { rank: list.indexOf(rec) + 1, total: list.length };
}
const fmt = (s) => { s = Math.max(0, s); const m = Math.floor(s / 60), r = Math.floor(s - m * 60); return `${m}:${String(r).padStart(2, '0')}`; };
const day = (ms) => { const d = new Date(ms); return `${d.getMonth() + 1}/${d.getDate()}`; };

// ---------------------------------------------------------------- the walker's trail
// points (three coordinates) at least 0.2 m apart, with the distance along them
class Trail {
  constructor() { this.p = []; this.s = []; }
  reset(v) { this.p = [v.clone()]; this.s = [0]; }
  get head() { return this.s[this.s.length - 1] ?? 0; }
  get start() { return this.s[0] ?? 0; }
  push(v) {
    const last = this.p[this.p.length - 1];
    if (!last) { this.reset(v); return; }
    const d = Math.hypot(v.x - last.x, v.z - last.z);
    if (d < 0.2) { last.y = v.y; return; }
    this.p.push(v.clone());
    this.s.push(this.head + d);
  }
  // drop what lies behind s
  trim(s) {
    let k = 0;
    while (k < this.s.length - 2 && this.s[k + 1] < s) k++;
    if (k > 64) { this.p.splice(0, k); this.s.splice(0, k); }
  }
  at(s, out) {
    const S = this.s, n = S.length;
    if (!n) return out;
    if (s <= S[0]) return out.copy(this.p[0]);
    if (s >= S[n - 1]) return out.copy(this.p[n - 1]);
    let lo = 0, hi = n - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (S[m] <= s) lo = m; else hi = m; }
    return out.lerpVectors(this.p[lo], this.p[hi], (s - S[lo]) / (S[hi] - S[lo]));
  }
}

const _v = new THREE.Vector3(), _w = new THREE.Vector3();

export class BdayGame {
  // birthday: birthday.js Birthday; places: places.js startPlaces; bubbles: talk.js Bubbles; ensure(x, y):
  // chunks.ensure; onBegin(msg): main.js takes the walk on; onQuit: back to the walk
  constructor({ scene, camera, player, cast, birthday, places, groundAt, bubbles, shadows, blobs, sound, ui, mobile, ensure, onBegin, onQuit }) {
    Object.assign(this, { scene, camera, player, cast, birthday, places, groundAt, bubbles, shadows, blobs, sound, ui, mobile, ensure, onBegin, onQuit });
    this.state = 'off';           // off | play | scene | done
    this.actors = {};
    this.trail = new Trail();
    this.t = 0;
    this.paused = false;
    addEventListener('keydown', (e) => {
      if (!this.on) return;
      if (this.resultsOpen) {
        if (e.code === 'Escape') { e.stopImmediatePropagation(); this.stop(); }
        return;
      }
      if (e.code === 'KeyB' || e.code === 'KeyM') { e.stopImmediatePropagation(); return; }    // (no tour, no map meanwhile)
      if (e.code === 'KeyE' && !e.repeat && !this.paused && this.act) { e.stopImmediatePropagation(); this.action(); }
    }, true);
  }

  get on() { return this.state !== 'off'; }
  get busy() { return this.resultsOpen; }

  // ---------------------------------------------------------------- a round
  async start() {
    const bd = this.birthday;
    if (!bd || this.starting) return;
    this.starting = true;
    try {
      const wait = this.ensure?.(bd.spot.x, -bd.spot.z);
      if (wait) await wait;
    } finally { this.starting = false; }
    this.results(false);
    this.clear();
    const pl = this.player;
    if (pl.scripted) bd.abort(); else bd.reset();
    // who, and where: four of the friends (not the one you walk as) in front of four halls
    const who = shuffle(POOL.filter((f) => f.id !== pl.actor.id)).slice(0, N);
    const halls = shuffle(HALLS.map((n) => this.places.find((p) => p.name === n && p.front) || this.places.find((p) => p.name === n)).filter(Boolean)).slice(0, N);
    this.friends = who.slice(0, halls.length).map((f, i) => {
      const a = this.actorOf(f), h = halls[i];
      // facing out of the door (the place faces the door: Player.teleport's yaw)
      const fx = Math.sin(h.yaw), fy = -Math.cos(h.yaw);
      const home = new THREE.Vector3(h.x, this.groundAt(h.x, h.y), -h.y);
      const heading = Math.atan2(fx, -fy);
      a.stand = a.actions['idle-look'] ? 'idle-look' : 'idle';
      a.holder.position.copy(home);
      a.heading = heading; a.holder.rotation.set(0, heading, 0);
      play(a, a.stand, { fade: 0 });
      a.mixer.setTime(Math.random() * 3);
      return { ...f, a, hall: h.name, home, heading, got: false, called: false, s: 0, w: 1, from: new THREE.Vector3(), v: 0, top: tallOf(f.id) };
    });
    this.onBegin?.(`생일인 친구가 기다려요 · 친구 ${this.friends.length}명을 ${LIMIT / 60}분 안에 데려와요 · 친구에게 다가가 ${this.mobile ? '버튼을 눌러요' : 'E를 눌러요'}`);
    // you: on the lawn a few metres out from the birthday student, facing them
    const p = bd.spot.clone().addScaledVector(bd.rad, 3.4);
    pl.teleport(p.x, -p.z, Math.atan2(-(bd.spot.x - p.x), -(bd.spot.z - p.z)));
    pl.enabled = true;
    pl.keys.clear();
    pl.stick.set(0, 0);
    pl.speed = 0;
    this.trail.reset(pl.pos);
    this.clock = LIMIT;
    this.state = 'play';
    this.counted = 0; this.wasState = bd.state; this.nagged = false; this.doneAt = null;
    const t = this.t;
    this.say(bd.f.holder, bd.fTop, `친구들 ${this.friends.length}명만 불러 와 줘!`, t + 2.3);
    this.say(bd.b.holder, bd.bTop, `${LIMIT / 60}분 안에! 여기서 기다릴게`, t + 4.6);
    this.sound?.cue('go');
    this.hudEl().hidden = false;
    this.drawHud(true);
  }

  // back to the walk (onQuit: main.js resumes it)
  stop() {
    if (!this.on) return;
    const bd = this.birthday;
    if (this.state === 'scene' && this.player.scripted) bd.abort();
    this.state = 'off';
    this.clear();
    if (this.hud) this.hud.el.hidden = true;
    this.setAct(null);
    this.results(false);
    this.player.enabled = true;
    this.onQuit?.();
  }

  // the friends out of the scene
  clear() {
    for (const f of this.friends || []) if (f.a.holder.parent) this.scene.remove(f.a.holder);
    this.friends = [];
  }

  actorOf(f) {
    let a = this.actors[f.id];
    if (!a) {
      a = this.actors[f.id] = this.cast.make(f.id, f.bag);
      this.shadows?.addDynamic(a.holder);
      this.blobs?.addPerson(a);
    }
    return a;
  }

  say(holder, top, text, from, dur = lineTime(text)) { this.bubbles?.add(holder, top, text, from, from + dur); }

  // ---------------------------------------------------------------- E / the button
  action() {
    const act = this.act;
    if (!act || this.state !== 'play') return;
    const pl = this.player, t = this.t;
    if (act.f) {
      const f = act.f;
      f.got = true;
      const k = this.friends.filter((x) => x.got && x !== f).length;
      f.order = k;
      f.s = Math.max(this.trail.start, this.trail.head - GAP0 - k * GAP);
      f.from.copy(f.a.holder.position);
      f.w = 0;
      f.a.stand = 'idle';
      this.say(pl.actor.holder, tallOf(pl.actor.id), `${call(f.name)}! 생일 축하하러 가자!`, t);
      this.say(f.a.holder, f.top, HELLO[Math.floor(Math.random() * HELLO.length)], t + 1.2);
      play(f.a, 'emote-yes', { once: true, fade: 0.25 });
      this.sound?.cue('beep');
      const left = this.friends.filter((x) => !x.got).length;
      this.ui?.toast(left ? `${f.name} 합류! · ${left}명 남았어요` : '모두 모였어요! 활천대로 가요', 2600);
    } else if (act.bday) {
      const bd = this.birthday;
      bd.said = true;
      if (!bd.action()) return;
      this.time = LIMIT - this.clock;
      this.state = 'scene';
      this.counted = 0;
      this.sound?.cue('go');
      this.slots();
    }
    this.setAct(null);
  }

  // where the friends stand round the throw: two either side of the carry, the near ones on the flagstones and the
  // far ones on the lawn behind, clear of the scene's camera (birthday.js action: out on the lawn, side on)
  slots() {
    const bd = this.birthday;
    const at = [[-2.4, 0.5], [2.5, 0.5], [-2.9, 1.6], [3.0, 1.6], [-1.6, 2.2], [1.8, 2.3]];
    this.friends.forEach((f, i) => {
      const [u, r] = at[i % at.length];
      f.slot = bd.mid.clone().addScaledVector(bd.tan, u).addScaledVector(bd.rad, r);
      f.slot.y = this.groundAt(f.slot.x, -f.slot.z);
      // round the basin, not over it
      const c = bd.C, p = f.a.holder.position;
      const ap = Math.atan2(p.z - c.z, p.x - c.x), as = Math.atan2(f.slot.z - c.z, f.slot.x - c.x);
      const d = wrapAngle(as - ap);
      f.via = Math.abs(d) > 0.6 ? c.clone().add(_v.set(Math.cos(ap + d / 2), 0, Math.sin(ap + d / 2)).multiplyScalar(6.6)) : null;
      if (f.via) f.via.y = this.groundAt(f.via.x, -f.via.z);
      f.walkT = 0;
    });
  }

  setAct(a) {
    this.act = a;
    const el = this.hud?.act;
    if (!el) return;
    const text = a ? a.text : '';
    if (!a) { el.hidden = true; return; }
    el.hidden = false;
    if (el.lastChild.textContent !== text) el.lastChild.textContent = text;
  }

  // ---------------------------------------------------------------- every frame
  // paused: the settings card, a memory card or the map is open (the clock stops)
  update(dt, t, paused) {
    this.t = t;
    this.paused = paused;
    if (!this.on) return;
    const pl = this.player, bd = this.birthday;
    if (this.state === 'play') {
      if (!paused) this.clock -= dt;
      // the trail: a jump (somewhere else at once) starts it again where the walker is
      const last = this.trail.p[this.trail.p.length - 1];
      if (last && Math.hypot(pl.pos.x - last.x, pl.pos.z - last.z) > 6) {
        this.trail.reset(pl.pos);
        for (const f of this.friends) if (f.got) { f.s = 0; f.from.copy(pl.pos); f.w = 0; }
      } else this.trail.push(pl.pos);
      let near = null, nd = NEAR;
      for (const f of this.friends) {
        if (f.got) continue;
        const d = Math.hypot(pl.pos.x - f.a.holder.position.x, pl.pos.z - f.a.holder.position.z);
        if (d < nd) { nd = d; near = f; }
        if (d < CALL && !f.called) {
          f.called = true;
          this.say(f.a.holder, f.top, `어? ${HERO[pl.actor.id]?.name ? call(HERO[pl.actor.id].name) : '야'}! 여기야!`, t);
          play(f.a, 'emote-yes', { once: true, fade: 0.25 });
        } else if (d > CALL * 2) f.called = false;
      }
      const all = this.friends.every((f) => f.got);
      const dB = Math.hypot(pl.pos.x - bd.b.holder.position.x, pl.pos.z - bd.b.holder.position.z);
      const tap = this.mobile ? '눌러서 ' : '';
      if (near) this.setAct({ f: near, text: `${tap}${near.name}${this.josa(near.name)} 같이 가기` });
      else if (all && dB < BDAY_NEAR && bd.state === 'idle') this.setAct({ bday: true, text: `${tap}생일 축하해 주기` });
      else this.setAct(null);
      if (!all && dB < 6.5 && !this.nagged && LIMIT - this.clock > 8) {
        this.nagged = true;
        const left = this.friends.filter((f) => !f.got).length;
        this.say(bd.b.holder, bd.bTop, `아직 ${left}명 더!`, t);
      } else if (dB > 12) this.nagged = false;
      if (this.clock <= 0) this.timeUp();
    } else if (this.state === 'scene') {
      this.setAct(null);
      // the birthday scene let go of (birthday.js abort): the round is over
      if (bd.state === 'idle') { this.stop(); return; }
      if (bd.state === 'swing' && bd.counted > this.counted) {
        this.counted = bd.counted;
        const word = ['하나!', '둘!', '셋!'][this.counted - 1];
        for (const f of this.friends) this.say(f.a.holder, f.top, word, t, 0.75);
      }
      if (bd.state === 'water' && this.wasState !== 'water') {
        this.friends.forEach((f, i) => {
          this.say(f.a.holder, f.top, i % 2 ? '축하해~!' : '생일 축하해!', t + 1.9 + i * 0.35);
          f.cheerAt = t + 0.4 + i * 0.25;
        });
      }
      if (bd.state === 'rest' && this.doneAt === null) this.doneAt = t + 1.2;
      if (this.doneAt !== null && t >= this.doneAt) this.finish();
    }
    this.wasState = bd.state;
    this.moveFriends(dt, t);
    if (this.state === 'play') this.drawHud();
  }

  josa(name) { const c = name.charCodeAt(name.length - 1) - 0xac00; return c >= 0 && c % 28 ? '과' : '와'; }

  moveFriends(dt, t) {
    const pl = this.player, cam = this.camera.position, tr = this.trail;
    let minS = tr.head;
    for (const f of this.friends) {
      const a = f.a, h = a.holder;
      const seen = Math.hypot(h.position.x - cam.x, h.position.z - cam.z) < SHOW;
      if (seen && !h.parent) this.scene.add(h);
      else if (!seen && h.parent) this.scene.remove(h);
      if (this.state === 'play' && f.got) {
        // along the trail to its place behind the walker, as fast as it needs (a run when the walker runs)
        const want = Math.max(tr.start, tr.head - GAP0 - f.order * GAP);
        if (want - f.s > SNAP) f.s = want - SNAP * 0.5;
        const vmax = Math.max(2.2, Math.abs(pl.speed) * 1.25 + 0.6);
        const v = Math.min(vmax, Math.max(0, want - f.s) * 2.2);
        f.s = Math.min(want, f.s + v * dt);
        minS = Math.min(minS, f.s);
        const old = _w.copy(h.position);
        tr.at(f.s, _v);
        if (f.w < 1) { f.w = Math.min(1, f.w + dt / 0.9); _v.lerpVectors(f.from, _v, ease(f.w)); }
        h.position.copy(_v);
        const dx = h.position.x - old.x, dz = h.position.z - old.z, moved = Math.hypot(dx, dz);
        const sp = moved / Math.max(dt, 1e-4);
        f.v += (sp - f.v) * Math.min(1, dt * 8);
        // facing the way they go, or the walker once there
        const wantH = moved > 0.004 ? Math.atan2(dx, dz) : Math.atan2(pl.pos.x - h.position.x, pl.pos.z - h.position.z);
        this.turn(a, wantH, dt, moved > 0.004 ? 10 : 3);
        locomotion(a, f.v > 0.25 ? f.v : 0, 2.9);
      } else if (this.state === 'scene' || (this.state === 'done' && f.slot)) {
        if (f.slot) this.toSlot(f, dt);
        if (f.cheerAt && t >= f.cheerAt) { f.cheerAt = null; play(a, 'emote-yes', { once: true, fade: 0.25 }); }
      } else if (!f.got && this.state === 'play') {
        // waiting: turn to you as you come up (standing on the ground as it is once the halls there are in)
        if (seen && (f.hT = (f.hT ?? 0) - dt) < 0) { f.hT = 1; h.position.y = this.groundAt(h.position.x, -h.position.z); }
        const d = Math.hypot(pl.pos.x - h.position.x, pl.pos.z - h.position.z);
        this.turn(a, d < CALL ? Math.atan2(pl.pos.x - h.position.x, pl.pos.z - h.position.z) : f.heading, dt, 3);
      }
      if (seen) a.mixer.update(dt);
    }
    if (this.state === 'play') tr.trim(minS - 2);
  }

  // over to the slot round the throw (by way of a point round the basin), then facing the carry
  toSlot(f, dt) {
    const a = f.a, h = a.holder, bd = this.birthday;
    f.walkT += dt;
    const goal = f.via || f.slot;
    const dx = goal.x - h.position.x, dz = goal.z - h.position.z, d = Math.hypot(dx, dz);
    if (f.walkT > 7) { h.position.copy(f.slot); f.via = null; }       // (anything in the way: there)
    if (d < 0.08 || f.walkT > 7) {
      if (f.via) { f.via = null; return; }
      locomotion(a, 0);
      this.turn(a, Math.atan2(bd.mid.x - h.position.x, bd.mid.z - h.position.z), dt, 5);
      return;
    }
    const want = Math.atan2(dx, dz);
    this.turn(a, want, dt, 9);
    const s = Math.min(1.7, d / dt) * Math.max(0, Math.cos(wrapAngle(want - a.heading)));
    h.position.x += Math.sin(a.heading) * s * dt;
    h.position.z += Math.cos(a.heading) * s * dt;
    h.position.y = this.groundAt(h.position.x, -h.position.z);
    locomotion(a, s > 0.05 ? Math.max(0.6, s) : 0, 2.9);
  }

  turn(a, want, dt, rate) {
    a.heading = (a.heading ?? a.holder.rotation.y) + wrapAngle(want - (a.heading ?? a.holder.rotation.y)) * (1 - Math.exp(-dt * rate));
    a.holder.rotation.set(0, a.heading, 0);
  }

  timeUp() {
    this.state = 'done';
    this.clock = 0;
    this.setAct(null);
    this.sound?.cue('buzzer');
    const got = this.friends.filter((f) => f.got).length;
    this.drawHud(true);
    this.player.enabled = false;
    this.player.speed = 0;
    this.say(this.player.actor.holder, tallOf(this.player.actor.id), '아… 시간이 다 됐다', this.t);
    setTimeout(() => { if (this.state === 'done') this.results(true, { ok: false, got }); }, 1500);
  }

  finish() {
    this.state = 'done';
    this.doneAt = null;
    const pl = this.player;
    pl.enabled = false;
    pl.speed = 0;
    const rec = { id: Date.now(), at: Date.now(), time: Math.round(this.time * 10) / 10, n: this.friends.length, hero: pl.actor.id };
    const prev = records()[0] || null;
    const { rank, total } = addRecord(rec);
    this.results(true, { ok: true, rec, rank, total, prev });
  }

  // ---------------------------------------------------------------- HUD
  hudEl() {
    if (this.hud) return this.hud.el;
    const el = document.createElement('div');
    el.id = 'bdayhud';
    el.innerHTML = '<div class="top"><div class="time"><small>남은 시간</small><b>5:00</b></div><div class="got"><small>친구</small><b>0 / 4</b></div></div>'
      + '<ul class="hints"></ul>';
    document.body.appendChild(el);
    const act = document.createElement('button');
    act.id = 'bdayact';
    act.type = 'button';
    act.hidden = true;
    act.innerHTML = '<kbd>E</kbd> <span></span>';
    act.addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); this.action(); });
    act.addEventListener('pointerdown', (e) => e.stopPropagation());
    document.body.appendChild(act);
    this.hud = { el, time: el.querySelector('.time b'), timeBox: el.querySelector('.time'), got: el.querySelector('.got b'), hints: el.querySelector('.hints'), act };
    return el;
  }

  drawHud(full = false) {
    const h = this.hud;
    if (!h) return;
    const txt = fmt(Math.ceil(this.clock));
    if (h.time.textContent !== txt) h.time.textContent = txt;
    h.timeBox.classList.toggle('low', this.clock < 30);
    const got = this.friends.filter((f) => f.got).length, all = got === this.friends.length;
    const gt = `${got} / ${this.friends.length}`;
    if (h.got.textContent !== gt) h.got.textContent = gt;
    const key = this.friends.map((f) => +f.got).join('') + all;
    if (!full && key === this.hintKey) return;
    this.hintKey = key;
    h.hints.replaceChildren(...this.friends.map((f) => {
      const li = document.createElement('li');
      li.classList.toggle('got', f.got);
      li.innerHTML = '<b></b><span></span>';
      li.querySelector('b').textContent = f.got ? `✓ ${f.name}` : `${f.hall} 앞`;
      li.querySelector('span').textContent = f.look;
      return li;
    }), ...(all ? [Object.assign(document.createElement('li'), { className: 'go', textContent: '모두 모였어요! 활천대로 돌아가요' })] : []));
  }

  // ---------------------------------------------------------------- the results card
  results(show, info = {}) {
    let el = this.resEl;
    if (!show) { if (el) el.hidden = true; return; }
    if (!el) {
      el = this.resEl = document.createElement('div');
      el.id = 'bdayresult';
      el.innerHTML = '<div><h2>생일 축하</h2><p class="big"></p><p class="best"></p><ol class="ranks"></ol>'
        + '<button type="button" class="again">다시 하기</button>'
        + '<button type="button" class="quit">그만하고 산책하기</button></div>';
      document.body.appendChild(el);
      el.querySelector('.again').addEventListener('click', (e) => { e.currentTarget.blur(); this.start(); });
      el.querySelector('.quit').addEventListener('click', (e) => { e.currentTarget.blur(); this.stop(); });
    }
    const big = el.querySelector('.big'), be = el.querySelector('.best');
    if (info.ok) {
      const { rec, rank, total, prev } = info;
      big.textContent = fmt(rec.time);
      const top = rank === 1;
      be.textContent = top
        ? (prev ? `새 기록! ${Math.round(prev.time - rec.time)}초 앞당김 · 친구 ${rec.n}명과 함께` : `첫 기록! 친구 ${rec.n}명과 함께 축하했어요`)
        : `이 브라우저 ${rank}위 (${total}번 가운데) · 최고 ${fmt(prev.time)}`;
      be.classList.toggle('new', top);
    } else {
      big.textContent = '시간 초과';
      be.textContent = `친구 ${info.got}명을 데려왔어요 · ${this.friends.length}명 모두 데려와야 해요`;
      be.classList.remove('new');
    }
    big.classList.toggle('fail', !info.ok);
    const list = records().slice(0, 5);
    el.querySelector('.ranks').replaceChildren(...list.map((r, i) => {
      const li = document.createElement('li');
      li.classList.toggle('me', r.id === info.rec?.id);
      li.innerHTML = '<span class="n"></span><span class="who"></span><span class="t"></span>';
      li.querySelector('.n').textContent = `${i + 1}`;
      li.querySelector('.who').textContent = `${HERO[r.hero]?.name ?? ''} · ${day(r.at)}`;
      li.querySelector('.t').textContent = fmt(r.time);
      return li;
    }));
    if (this.hud) this.hud.el.hidden = true;
    el.hidden = false;
    el.querySelector('.again').focus({ preventScroll: true });
  }
  get resultsOpen() { return !!this.resEl && !this.resEl.hidden; }
}
