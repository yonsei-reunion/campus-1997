// 삐삐 호출 (the title card's and the settings card's 「삐삐 호출」): the pager on the belt goes off, its screen shows a
// number to call back and a number code (8282, 1004, 486 …). Run to a public phone booth before the time is up, lift
// the receiver (E, or the button on a phone) and dial the number; the line comes through, the code's meaning is asked
// (four choices) and the friend on the line names where to meet. Run there; the next page comes. Three pages a game.
// Every leg's time left is the score (and the right meanings); each game is kept in this browser.
// The booths are campus.json's 'payphone' props. The crowd's callers (main.js: in all but one booth of a bank) stay on
// the line; the free booths may have a caller of this game's own, who hangs up soon once you wait beside them.
// Loaded only when the game starts (main.js).
import * as THREE from 'three';
import { HERO, play } from './characters.js';
import { safeGet, safeSet, wrapAngle } from './util.js';
import './pager.css';

const PAGES = 3;
const KEY = 'y97-pager-records', MAX = 50;
const NEAR = 1.4;                 // m from a booth's standing spot: the receiver within reach
const MEET_R = 4.0;               // m from the meeting place: arrived
const RUN = 6.2;                  // the walker's running speed (player.js RUN)
const STAND = 0.85;               // m out of a booth's open front: where its caller stands (main.js, the crowd's)

// the codes of the 1990s pagers (the loading card's quiz has most of them: loading.js); how: shown after the answer;
// say: the friend's line naming the place to meet, bye: the last call's
export const CODES = [
  { code: '8282', mean: '빨리빨리', how: '팔(8) · 이(2) · 팔(8) · 이(2)', say: (p) => `빨리빨리! 나 ${p} 앞이야. 얼른 와!`, bye: '빨리 와 줘서 고마워! 내일 수업 때 보자' },
  { code: '1004', mean: '천사', how: '천(1000) · 사(4)', say: (p) => `천사가 기다린다~ ${p} 앞에서 봐`, bye: '전화해 줘서 고마워. 역시 천사야' },
  { code: '486', mean: '사랑해', how: '「사 · 랑 · 해」 세 글자의 획 수 4 · 8 · 6', say: (p) => `목소리 듣고 싶어서 쳤지. ${p} 앞에서 만나`, bye: '목소리 들으니 좋다. 내일 봐' },
  { code: '38317', mean: '사랑해', how: '거꾸로 보면 LIEBE, 독일어로 「사랑」', say: (p) => `거꾸로 읽어 봤어? ${p} 앞에서 기다릴게`, bye: '알아봐 줘서 고마워. 내일 봐' },
  { code: '7942', mean: '친구 사이', how: '칠(7) · 구(9) · 사(4) · 이(2)', say: (p) => `친구야, ${p} 앞에서 같이 밥 먹자`, bye: '역시 친구야. 내일 학관에서 보자' },
  { code: '9090', mean: '가자', how: '9는 g, 0은 o를 닮아 「GO GO」', say: (p) => `가자 가자! ${p} 앞에 다 모였어`, bye: '다 모였다, 이제 가자! 끊는다' },
  { code: '505', mean: '도와줘', how: '5는 S, 0은 O를 닮아 「SOS」', say: (p) => `살려 줘, 짐이 너무 많아! ${p} 앞이야`, bye: '살았다, 고마워! 내일 밥 살게' },
  { code: '1472', mean: '일사천리', how: '일(1) · 사(4) · 칠(7) · 이(2)', say: (p) => `일이 술술 풀렸어! ${p} 앞에서 얘기해 줄게`, bye: '오늘은 일사천리다. 내일 봐' },
];
// the exchanges round 신촌 (the callers' numbers: made up, 7 digits as in 1997)
const EXCH = ['312', '313', '392', '393', '362', '363', '364', '365', '332', '336', '337', '338', '324', '325'];

// ---------------------------------------------------------------- records (this browser only)
export function records() {
  let list;
  try { list = JSON.parse(safeGet(KEY) || '[]'); } catch { list = []; }
  return (Array.isArray(list) ? list : []).filter((r) => r && Number.isFinite(r.score)).sort((a, b) => b.score - a.score || a.at - b.at);
}
function addRecord(rec) {
  const list = records();
  list.push(rec);
  list.sort((a, b) => b.score - a.score || a.at - b.at);
  safeSet(KEY, JSON.stringify(list.slice(0, MAX)));
  return { rank: list.indexOf(rec) + 1, total: list.length };
}
const fmt = (s) => { s = Math.max(0, Math.ceil(s)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
const day = (ms) => { const d = new Date(ms); return `${d.getMonth() + 1}/${d.getDate()}`; };
const pick = (a) => a[Math.floor(Math.random() * a.length)];
const shuffle = (a) => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const round5 = (s) => Math.ceil(s / 5) * 5;
const dash = (n) => `${n.slice(0, 3)}-${n.slice(3)}`;
// 로 or 으로 after a word (a final consonant other than ㄹ takes 으로; digits by their reading)
const ro = (w) => {
  const c = w.trim().slice(-1), d = '0123456789'.indexOf(c);
  if (d >= 0) return w + ([0, 3, 6].includes(d) ? '으로' : '로');
  const k = c.charCodeAt(0) - 0xac00;
  return w + (k >= 0 && k < 11172 && k % 28 && k % 28 !== 8 ? '으로' : '로');
};
// what the pager's screen shows: the number, a dash, the code
const screenText = (pg) => `${dash(pg.num)}-${pg.code.code}`;

// the ring at the meeting place: a light standing on the ground, fading upwards (race.js has the same)
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

export class Pager {
  // booths: campus.json's payphone props [[kind, x, y, rot]]; buildings: campus.json's (each booth is named after the
  // nearest); places: places.js startPlaces (the meeting places); crowd: life.js Crowd (its callers, its bubbles);
  // onBegin(msg): main.js takes the walk on; onQuit: back to the walk
  constructor({ scene, camera, player, cast, crowd, sound, groundAt, ensure, booths, buildings, places, shadows, blobs, mobile, onBegin, onQuit }) {
    Object.assign(this, { scene, camera, player, cast, crowd, sound, groundAt, ensure, places, shadows, blobs, mobile, onBegin, onQuit });
    this.state = 'off';               // off | run (to a booth) | dial (the phone card) | meet (to the place) | gap | done
    this.booths = booths.map(([, x, y, rot]) => {
      const fx = Math.cos(rot), fy = Math.sin(rot);
      return { x, y, rot, fx, fy, sx: x + fx * STAND, sy: y + fy * STAND, heading: Math.atan2(-fx, fy), name: nearestName(buildings, x, y),
        crowd: null, guest: null };
    });
    this.guests = [];                 // this game's own callers (made the first time a free booth needs one)
    this._dir = new THREE.Vector3();
    this.group = new THREE.Group();
    this.group.name = 'pager_meet';
    const ring = new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.2, 2.6, 40, 1, true),
      new THREE.MeshBasicMaterial({ map: ringTexture(), color: 0x6fd6ff, transparent: true, depthWrite: false, side: THREE.DoubleSide, fog: false, toneMapped: false }));
    ring.position.y = 1.25;
    ring.renderOrder = 5;
    const disc = new THREE.Mesh(new THREE.RingGeometry(2.95, 3.2, 40),
      new THREE.MeshBasicMaterial({ color: 0x6fd6ff, transparent: true, opacity: 0.9, depthWrite: false, side: THREE.DoubleSide, fog: false, toneMapped: false }));
    disc.rotation.x = -Math.PI / 2;
    disc.position.y = 0.06;
    this.group.add(ring, disc);
    this.ring = ring;
    addEventListener('keydown', (e) => this.onKey(e), true);
  }

  get on() { return this.state !== 'off'; }
  // a card of its own open: main.js leaves the keys to it
  get busy() { return this.state === 'dial' || this.resultsOpen; }

  // ---------------------------------------------------------------- a game
  start() {
    if (!this.booths.length) return;
    this.results(false);
    this.dial(false);
    if (this.crowd?.hidden) this.crowd.hidden = false;      // (the race takes the crowd away while it runs)
    // the crowd's callers: whoever stands on the phone at a booth's spot
    for (const b of this.booths) b.crowd = this.crowd?.people.find((p) => p.phone && Math.hypot(p.x - b.sx, p.y - b.sy) < 0.6) || null;
    for (const b of this.booths) this.freeGuest(b, true);
    const pl = this.player;
    this.onBegin?.(this.mobile ? '삐삐가 울리면 가까운 공중전화로 달려가요' : '삐삐가 울리면 가까운 공중전화로 달려가요 · ↑(W)만 눌러도 늘 뛰어요');
    pl.autoRun = true;
    pl.enabled = true;
    pl.keys.clear();
    pl.stick.set(0, 0);
    Object.assign(this, { n: 0, score: 0, right: 0, legs: [], page: null, used: [] });
    this.hudEl().hidden = false;
    this.pagerEl().hidden = false;
    this.lcd('', '');
    this.state = 'gap';
    this.gapT = 1.2;                  // (a breath before the first page)
    this.target = null;
  }

  stop() {
    if (!this.on) return;
    this.state = 'off';
    const pl = this.player;
    pl.autoRun = false;
    pl.enabled = true;
    if (pl.actor.stand === 'phone') pl.actor.stand = 'idle';
    for (const b of this.booths) this.freeGuest(b, true);
    if (this.group.parent) this.scene.remove(this.group);
    if (this.hud) this.hud.el.hidden = true;
    if (this.pgEl) this.pgEl.hidden = true;
    this.button(null);
    this.dial(false);
    this.results(false);
    this.onQuit?.();
  }

  // a page: a number, a code, the time to a booth (from the straight way to the nearest, a third more for the turns,
  // and some to dial)
  newPage() {
    this.n++;
    const code = pick(CODES.filter((c) => c.code !== this.page?.code.code));
    const num = pick(EXCH) + String(Math.floor(Math.random() * 10000)).padStart(4, '0');
    const pl = this.player, d = Math.min(...this.booths.map((b) => Math.hypot(b.sx - pl.x, b.sy - pl.y)));
    const limit = round5(20 + (d * 1.35) / RUN);
    this.page = { num, code, limit };
    this.left = limit;
    this.state = 'run';
    this.lcd(screenText(this.page), `호출 ${this.n}/${PAGES}`);
    this.buzz();
    // the free booths: now and then somebody on the phone there (for a while; sooner off once you wait)
    for (const b of this.booths) {
      if (b.crowd) continue;
      this.freeGuest(b);
      if (Math.random() < 0.55) this.takeGuest(b, 10 + Math.random() * 25);
    }
  }

  buzz() {
    const el = this.pgEl;
    el.classList.remove('buzz'); void el.offsetWidth; el.classList.add('buzz');
    for (const k of [0, 1, 2, 4, 5, 6]) setTimeout(() => this.on && this.sound?.cue('beep'), k * 140);
    this.flash(`삐삐삐! 호출 ${this.n}/${PAGES}`);
  }

  // ---------------------------------------------------------------- the booths' callers of this game's own
  takeGuest(b, secs) {
    let g = this.guests.find((q) => !q.booth);
    if (!g) {
      const pool = [...new Set((this.crowd?.people || []).map((p) => p.a.id))].filter((id) => id !== this.player.actor.id);
      const id = pool.length ? pick(pool) : 'p01';
      const a = this.cast.make(id, null);
      this.shadows?.addDynamic(a.holder);
      this.blobs?.addPerson(a);
      g = { a, top: (a.tall || 1) * 1.7 };
      this.guests.push(g);
    }
    g.booth = b; g.until = secs; g.leave = 0; g.said = false;
    b.guest = g;
    const a = g.a;
    a.holder.position.set(b.sx, this.groundAt(b.sx, b.sy), -b.sy);
    a.holder.rotation.y = b.heading;
    a.stand = 'phone';
    play(a, 'phone', { fade: 0 });
    a.mixer.update(Math.random() * 2);
    if (!a.holder.parent) this.scene.add(a.holder);
  }

  // the guest of booth b off the phone: walks away (now: gone at once)
  freeGuest(b, now = false) {
    const g = b.guest;
    if (!g) return;
    b.guest = null;
    if (now) { g.booth = null; if (g.a.holder.parent) this.scene.remove(g.a.holder); return; }
    g.leave = 3.2;
    g.a.stand = 'idle';
    // out of the front and to the side, away from you
    const pl = this.player, sx = -b.fy, sy = b.fx, side = (pl.x - b.sx) * sx + (pl.y - b.sy) * sy > 0 ? -1 : 1;
    g.vx = (b.fx * 0.5 + sx * side) * 1.25; g.vy = (b.fy * 0.5 + sy * side) * 1.25;
  }

  updateGuests(dt, t) {
    const pl = this.player;
    for (const g of this.guests) {
      if (!g.booth) continue;
      const a = g.a, b = g.booth;
      if (b.guest === g) {
        // waiting beside them: they finish up
        if (this.state === 'run' && Math.hypot(pl.x - b.sx, pl.y - b.sy) < 3.2) {
          if (!g.said) { g.said = true; g.until = Math.min(g.until, 3.5); this.crowd?.bubbles?.add(a.holder, g.top, pick(['금방 끊을게요!', '잠깐만요, 거의 다 했어요', '어, 끊을게. 뒤에 사람 기다려']), t, t + 2.6); }
        }
        g.until -= dt;
        if (g.until <= 0) {
          if (g.said) this.crowd?.bubbles?.add(a.holder, g.top, pick(['쓰세요~', '오래 기다리셨죠, 쓰세요', '다 썼어요']), t, t + 2.2);
          this.freeGuest(b);
        }
      } else {
        // walking off
        g.leave -= dt;
        const p = a.holder.position;
        p.x += g.vx * dt; p.z -= g.vy * dt;
        p.y = this.groundAt(p.x, -p.z);
        a.holder.rotation.y = Math.atan2(g.vx, -g.vy) + Math.PI;
        a.stand = 'idle';
        play(a, 'walk', { fade: 0.3 });
        if (g.leave <= 0) { g.booth = null; if (a.holder.parent) this.scene.remove(a.holder); continue; }
      }
      a.mixer.update(dt);
    }
  }

  // the nearest booth's spot to the walker, and whether it is free
  nearest() {
    const pl = this.player;
    let best = null, bd = Infinity;
    for (const b of this.booths) {
      const d = Math.hypot(b.sx - pl.x, b.sy - pl.y);
      if (d < bd) { bd = d; best = b; }
    }
    return { b: best, d: bd };
  }
  // where the HUD's arrow points: the nearest booth with nobody of the crowd in it (one of this game's callers may
  // still be finishing there), the meeting place
  aim() {
    if (this.state === 'meet') return this.meet;
    const pl = this.player;
    let best = null, bd = Infinity;
    for (const b of this.booths) {
      if (b.crowd) continue;
      const d = Math.hypot(b.sx - pl.x, b.sy - pl.y) + (b.guest ? 20 : 0);
      if (d < bd) { bd = d; best = b; }
    }
    return best ? { x: best.sx, y: best.sy, name: `${best.name} 공중전화` } : null;
  }

  // E, Space or the button by a booth
  act(t) {
    if (this.state !== 'run') return false;
    const { b, d } = this.nearest();
    if (!b || d > NEAR) return false;
    if (b.crowd) {
      this.crowd?.say?.(b.crowd, pick(['통화 중이에요…', '아직 통화 중이에요', '옆 전화 쓰세요~']), t);
      return true;
    }
    if (b.guest) { this.crowd?.bubbles?.add(b.guest.a.holder, b.guest.top, '잠깐만요, 금방 끝나요!', t, t + 2); return true; }
    this.lift(b);
    return true;
  }

  // the receiver up: the walker in the booth's spot, on the phone, and the phone's card
  lift(b) {
    const pl = this.player;
    this.booth = b;
    pl.teleport(b.sx, b.sy, Math.atan2(b.fx, -b.fy));
    pl.enabled = false;
    pl.speed = 0;
    pl.actor.stand = 'phone';
    this.state = 'dial';
    this.button(null);
    this.dial(true);
  }

  hangUp(done) {
    const pl = this.player;
    pl.actor.stand = 'idle';
    pl.enabled = true;
    this.dial(false);
    if (!done) { this.state = 'run'; return; }
  }

  // ---------------------------------------------------------------- the legs
  connected() {
    // the run to the booth scored by its time left
    const pts = Math.ceil(this.left) * 10;
    this.score += pts;
    this.legs.push({ what: 'call', left: Math.ceil(this.left) });
    this.lcd('', `호출 ${this.n}/${PAGES}`);
  }

  // after the quiz and the friend's line: the meeting place, or the end
  afterCall() {
    this.hangUp(true);
    if (this.n >= PAGES) { this.finish(true); return; }
    const m = this.meet = this.nextMeet;
    const pl = this.player, d = Math.hypot(m.x - pl.x, m.y - pl.y);
    this.left = round5(12 + (d * 1.35) / RUN);
    this.meetLimit = this.left;
    this.state = 'meet';
    const h = this.groundAt(m.x, m.y);
    this.group.position.set(m.x, h, -m.y);
    if (!this.group.parent) this.scene.add(this.group);
    this.group.visible = true;
    this.flash(`${ro(m.name)}!`);
    this.ensure?.(m.x, m.y);
  }

  // somewhere 80 - 230 m off, not where the game has been
  meetPlace() {
    const pl = this.player;
    const ok = (p, lo, hi) => {
      const d = Math.hypot(p.x - pl.x, p.y - pl.y);
      return d > lo && d < hi && p.y > -420 && p.y < 460 && !this.used.some((u) => Math.hypot(u.x - p.x, u.y - p.y) < 40);
    };
    let list = this.places.filter((p) => ok(p, 80, 230));
    if (!list.length) list = this.places.filter((p) => ok(p, 40, 400));
    if (!list.length) list = this.places;
    const p = pick(list);
    const m = { x: p.x, y: p.y, name: p.name };
    this.used.push(m);
    return m;
  }

  arrived() {
    const pts = Math.ceil(this.left) * 10;
    this.score += pts;
    this.legs.push({ what: 'meet', left: Math.ceil(this.left) });
    this.group.visible = false;
    this.sound?.cue('go');
    this.flash(`만났다! +${pts}`);
    this.state = 'gap';
    this.gapT = 2.2;
  }

  finish(all) {
    this.state = 'done';
    this.target = null;
    this.button(null);
    this.group.visible = false;
    const pl = this.player;
    pl.enabled = false;
    pl.speed = 0;
    this.sound?.cue(all ? 'go' : 'buzzer');
    if (!all) { this.flash('시간 초과!'); this.lcd('--------', '시간 초과'); }
    const calls = this.legs.filter((l) => l.what === 'call').length;
    const rec = { id: Date.now(), at: Date.now(), score: this.score, calls, right: this.right, hero: pl.actor.id };
    const prev = records()[0] || null;
    const { rank, total } = this.score ? addRecord(rec) : { rank: 0, total: records().length };     // (nothing to keep of an empty game)
    setTimeout(() => { if (this.state === 'done') this.results(true, { rec, rank, total, prev, all }); }, all ? 600 : 1400);
  }

  // t: the loop's clock; paused: the settings card, a memory card or the map is open (the clock stops)
  update(dt, t, paused) {
    if (!this.on) return;
    this.t = t;
    this.ring.rotation.y = t * 0.6;
    if (!paused) this.tick(dt, t);
    this.updateGuests(paused ? 0 : dt, t);
    this.drawHud();
  }

  tick(dt, t) {
    const pl = this.player;
    if (this.state === 'gap') {
      this.gapT -= dt;
      if (this.gapT <= 0) this.newPage();
    } else if (this.state === 'run' || this.state === 'dial') {
      this.left -= dt;
      if (this.state === 'run') {
        const { b, d } = this.nearest();
        this.button(b && d < NEAR ? (b.crowd ? '통화 중 · 다른 부스로' : b.guest ? '통화 중 · 기다리는 중…' : '수화기 들기') : null, !!(b && !b.crowd && !b.guest));
      }
      if (this.left <= 0) { if (this.state === 'dial') this.hangUp(true); this.finish(false); }
    } else if (this.state === 'meet') {
      this.left -= dt;
      if (Math.hypot(pl.x - this.meet.x, pl.y - this.meet.y) < MEET_R) this.arrived();
      else if (this.left <= 0) this.finish(false);
    }
    if (this.flashT !== undefined) { this.flashT -= dt; if (this.flashT <= 0) { this.flash(''); this.flashT = undefined; } }
  }

  onKey(e) {
    if (!this.on) return;
    if (this.resultsOpen) { if (e.code === 'Escape') { e.stopImmediatePropagation(); this.stop(); } return; }
    if (this.state === 'dial') {
      const k = e.key;
      if (/^[0-9]$/.test(k) && this.dl.stage === 'dial') { e.preventDefault(); this.press(k); return; }
      if (e.code === 'Backspace' && this.dl.stage === 'dial') { e.preventDefault(); this.press('back'); return; }
      if (e.code === 'Escape') { e.stopImmediatePropagation(); if (this.dl.stage === 'dial') this.hangUp(false); return; }
      if (this.dl.stage === 'quiz' && /^[1-4]$/.test(k)) { e.preventDefault(); this.answer(+k - 1); return; }
      if (this.dl.stage === 'talk' && (e.code === 'Enter' || e.code === 'Space' || e.code === 'KeyE')) { e.preventDefault(); this.afterCall(); }
      return;
    }
    if ((e.code === 'KeyE' || e.code === 'Space') && !e.repeat && this.state === 'run' && this.player.enabled) {
      if (this.act(this.t || 0)) { e.preventDefault(); e.stopImmediatePropagation(); }
    }
  }

  // ---------------------------------------------------------------- the phone's card
  dial(show) {
    let el = this.dialEl;
    if (!show) { if (el) el.hidden = true; return; }
    if (!el) {
      el = this.dialEl = document.createElement('div');
      el.id = 'pagerdial';
      el.innerHTML = '<div class="phone"><div class="top"><span class="mini"></span><b>공중전화</b></div>'
        + '<p class="lead"></p><div class="disp"><span></span></div>'
        + '<div class="keys"></div><div class="quiz" hidden><p class="q"></p><div class="opts"></div><p class="res"></p></div>'
        + '<div class="talk" hidden><p class="line"></p><button type="button" class="go"></button></div>'
        + '<button type="button" class="hang">수화기 내려놓기</button></div>';
      document.body.appendChild(el);
      const keys = el.querySelector('.keys');
      for (const k of ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'back', '0', 'clear']) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = k === 'back' ? '←' : k === 'clear' ? '다시' : k;
        btn.dataset.k = k;
        btn.addEventListener('click', (e) => { e.currentTarget.blur(); this.press(k); });
        keys.appendChild(btn);
      }
      el.querySelector('.hang').addEventListener('click', (e) => { e.currentTarget.blur(); this.hangUp(false); });
      el.querySelector('.go').addEventListener('click', (e) => { e.currentTarget.blur(); this.afterCall(); });
    }
    this.dl = { stage: 'dial', typed: '', el };
    el.querySelector('.mini').textContent = screenText(this.page);
    el.querySelector('.lead').textContent = `삐삐에 찍힌 번호 ${ro(dash(this.page.num))} 걸어요`;
    el.querySelector('.keys').hidden = false;
    el.querySelector('.quiz').hidden = true;
    el.querySelector('.talk').hidden = true;
    el.querySelector('.hang').hidden = false;
    this.showTyped();
    el.hidden = false;
  }

  showTyped(msg) {
    const s = this.dl.el.querySelector('.disp span');
    s.textContent = msg || (this.dl.typed ? (this.dl.typed.length > 3 ? dash(this.dl.typed) : this.dl.typed) : '번호를 누르세요');
    s.parentElement.classList.toggle('empty', !msg && !this.dl.typed);
    s.parentElement.classList.toggle('msg', !!msg);
  }

  press(k) {
    const dl = this.dl;
    if (!dl || dl.stage !== 'dial' || dl.wait) return;
    if (k === 'back') dl.typed = dl.typed.slice(0, -1);
    else if (k === 'clear') dl.typed = '';
    else if (dl.typed.length < 7) { dl.typed += k; this.sound?.cue('beep'); }
    this.showTyped();
    if (dl.typed.length < 7) return;
    dl.wait = true;
    if (dl.typed === this.page.num) {
      this.showTyped('따르릉… 따르릉…');
      setTimeout(() => { if (this.state === 'dial' && this.dl === dl) { dl.wait = false; this.connected(); this.quiz(); } }, 1100);
    } else {
      this.showTyped('없는 번호입니다');
      this.sound?.cue('buzzer');
      setTimeout(() => { if (this.dl === dl) { dl.wait = false; dl.typed = ''; this.showTyped(); } }, 1100);
    }
  }

  // what the code means: four choices
  quiz() {
    const dl = this.dl, el = dl.el, c = this.page.code;
    dl.stage = 'quiz';
    el.querySelector('.keys').hidden = true;
    el.querySelector('.hang').hidden = true;
    el.querySelector('.lead').textContent = '연결됐어요! 그런데 삐삐 끝의 숫자는…';
    this.showTyped(`${c.code} ?`);
    const q = el.querySelector('.quiz');
    q.hidden = false;
    q.querySelector('.q').textContent = `「${c.code}」는 무슨 뜻일까요?`;
    q.querySelector('.res').textContent = '';
    dl.opts = shuffle([c, ...shuffle(CODES.filter((x) => x.mean !== c.mean)).filter((x, i, a) => a.findIndex((y) => y.mean === x.mean) === i).slice(0, 3)]);
    q.querySelector('.opts').replaceChildren(...dl.opts.map((o, i) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.innerHTML = '<i></i><span></span>';
      b.querySelector('i').textContent = String(i + 1);
      b.querySelector('span').textContent = o.mean;
      b.addEventListener('click', (e) => { e.currentTarget.blur(); this.answer(i); });
      return b;
    }));
    q.querySelector('.opts button')?.focus({ preventScroll: true });
  }

  answer(i) {
    const dl = this.dl;
    if (!dl || dl.stage !== 'quiz' || dl.answered) return;
    dl.answered = true;
    const c = this.page.code, ok = dl.opts[i] === c, q = dl.el.querySelector('.quiz');
    q.querySelectorAll('.opts button').forEach((b, k) => { b.disabled = true; b.classList.toggle('right', dl.opts[k] === c); b.classList.toggle('wrong', k === i && !ok); });
    if (ok) { this.right++; this.score += 100; }
    q.querySelector('.res').textContent = ok ? `맞아요! +100점 · ${c.how}` : `「${c.mean}」였어요 · ${c.how}`;
    this.sound?.cue(ok ? 'go' : 'beep');
    setTimeout(() => { if (this.dl === dl && this.state === 'dial') this.talk(); }, 2200);
  }

  // the friend's line: where to meet (or goodbye, on the last call)
  talk() {
    const dl = this.dl, el = dl.el, c = this.page.code, last = this.n >= PAGES;
    dl.stage = 'talk';
    el.querySelector('.quiz').hidden = true;
    if (!last) this.nextMeet = this.meetPlace();
    const line = last ? c.bye : c.say(this.nextMeet.name);
    el.querySelector('.lead').textContent = '수화기 너머로…';
    this.showTyped('통화 중');
    el.querySelector('.line').textContent = `「${line}」`;
    const go = el.querySelector('.go');
    go.textContent = last ? '끊고 결과 보기' : '끊고 만나러 가기';
    el.querySelector('.talk').hidden = false;
    go.focus({ preventScroll: true });
  }

  // ---------------------------------------------------------------- HUD: the time left, the page, the score, the way
  hudEl() {
    if (this.hud) return this.hud.el;
    const el = document.createElement('div');
    el.id = 'pagerhud';
    el.innerHTML = '<div class="time"><small>남은 시간</small><b>0:00</b></div>'
      + '<div class="score"><small>점수</small><b>0</b><span></span></div>'
      + '<div class="way"><i></i><span></span></div>';
    document.body.appendChild(el);
    const big = document.createElement('div');
    big.id = 'pagerflash';
    document.body.appendChild(big);
    const btn = document.createElement('button');
    btn.id = 'pagerbtn';
    btn.type = 'button';
    btn.hidden = true;
    btn.innerHTML = '<span></span><kbd>E</kbd>';
    btn.addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); this.act(this.t || 0); });
    document.body.appendChild(btn);
    this.hud = { el, time: el.querySelector('.time b'), score: el.querySelector('.score b'), page: el.querySelector('.score span'),
      arrow: el.querySelector('.way i'), dist: el.querySelector('.way span'), big, btn };
    return el;
  }

  drawHud() {
    const h = this.hud;
    if (!h) return;
    const timed = this.state === 'run' || this.state === 'dial' || this.state === 'meet';
    const txt = timed ? fmt(this.left) : this.state === 'gap' && this.n ? '…' : '-:--';
    if (h.time.textContent !== txt) h.time.textContent = txt;
    h.time.classList.toggle('low', timed && this.left < 10);
    const sc = String(this.score);
    if (h.score.textContent !== sc) h.score.textContent = sc;
    const pg = `호출 ${Math.max(1, this.n)} / ${PAGES}`;
    if (h.page.textContent !== pg) h.page.textContent = pg;
    const g = this.state === 'run' || this.state === 'meet' ? this.aim() : null;
    h.arrow.parentElement.style.visibility = g ? '' : 'hidden';
    if (g) {
      const pl = this.player, d = this.camera.getWorldDirection(this._dir);
      const look = Math.atan2(d.x, -d.z), to = Math.atan2(g.x - pl.x, g.y - pl.y);
      h.arrow.style.transform = `rotate(${wrapAngle(to - look).toFixed(3)}rad)`;
      const m = `${g.name} ${Math.round(Math.hypot(g.x - pl.x, g.y - pl.y))} m`;
      if (h.dist.textContent !== m) h.dist.textContent = m;
    }
  }

  // the action button by a booth (on a phone the only way; on a desktop E or Space as well)
  button(text, live = true) {
    const b = this.hud?.btn;
    if (!b) return;
    if (!text) { if (!b.hidden) b.hidden = true; return; }
    b.hidden = false;
    const s = b.querySelector('span');
    if (s.textContent !== text) s.textContent = text;
    b.classList.toggle('dim', !live);
    b.querySelector('kbd').hidden = this.mobile;
  }

  flash(text) {
    const el = this.hud?.big;
    if (!el) return;
    el.textContent = text;
    el.classList.remove('pop'); void el.offsetWidth;
    if (text) { el.classList.add('pop'); this.flashT = 1.8; }
  }

  // ---------------------------------------------------------------- the pager on the belt (a numeric pager of the
  // 1990s, drawn in CSS: a black case, a green screen of seven-segment digits, a red light; no maker's name)
  pagerEl() {
    if (this.pgEl) return this.pgEl;
    const el = this.pgEl = document.createElement('div');
    el.id = 'pagerdev';
    el.innerHTML = '<div class="case"><i class="led"></i><div class="lcd"><span class="ghost">888-8888-8888</span><span class="txt"></span><small></small></div>'
      + '<div class="btns"><b></b><b></b></div></div>';
    document.body.appendChild(el);
    return el;
  }
  lcd(text, small) {
    const el = this.pgEl;
    if (!el) return;
    el.querySelector('.txt').textContent = text;
    el.querySelector('.ghost').textContent = text ? text.replace(/[0-9]/g, '8') : '888-8888-888';
    el.querySelector('small').textContent = small;
    el.classList.toggle('lit', !!text);
    el.querySelector('.txt').classList.toggle('long', text.length > 13);
  }

  // ---------------------------------------------------------------- the results card
  results(show, info = {}) {
    let el = this.resEl;
    if (!show) { if (el) el.hidden = true; return; }
    if (!el) {
      el = this.resEl = document.createElement('div');
      el.id = 'pagerresult';
      el.innerHTML = '<div><h2>삐삐 호출</h2><p class="big"></p><p class="sub"></p><p class="best"></p><ol class="ranks"></ol>'
        + '<button type="button" class="again">다시 하기</button><button type="button" class="quit">그만하고 산책하기</button></div>';
      document.body.appendChild(el);
      el.querySelector('.again').addEventListener('click', (e) => { e.currentTarget.blur(); this.start(); });
      el.querySelector('.quit').addEventListener('click', (e) => { e.currentTarget.blur(); this.stop(); });
    }
    const { rec, rank, total, prev, all } = info;
    el.querySelector('.big').textContent = `${rec.score}점`;
    el.querySelector('.sub').textContent = `${all ? `${PAGES}통 모두 걸었어요` : `${rec.calls}통 걸고 시간이 다 됐어요`} · 숫자 암호 ${rec.right}개 맞힘`;
    const be = el.querySelector('.best'), top = rank === 1;
    be.textContent = !rank ? '다음엔 한 통이라도 걸어 봐요' : top ? (prev ? `새 기록! 전 최고 ${prev.score}점` : '첫 기록!')
      : `이 브라우저 ${rank}위 (${total}판 가운데) · 최고 ${prev.score}점`;
    be.classList.toggle('new', top);
    el.querySelector('.ranks').replaceChildren(...records().slice(0, 5).map((r, i) => {
      const li = document.createElement('li');
      li.classList.toggle('me', r.id === rec.id);
      li.innerHTML = '<span class="n"></span><span class="who"></span><span class="t"></span>';
      li.querySelector('.n').textContent = `${i + 1}`;
      li.querySelector('.who').textContent = `${HERO[r.hero]?.name ?? ''} · ${r.calls}통 · ${day(r.at)}`;
      li.querySelector('.t').textContent = `${r.score}점`;
      return li;
    }));
    el.hidden = false;
    el.querySelector('.again').focus({ preventScroll: true });
  }
  get resultsOpen() { return !!this.resEl && !this.resEl.hidden; }
}

// the booth's name: the nearest named building (by its outline's nearest corner or edge)
function nearestName(buildings, x, y) {
  let best = '', bd = Infinity;
  for (const b of buildings) {
    if (!b.name || !b.footprint) continue;
    const f = b.footprint;
    for (let i = 0; i < f.length; i++) {
      const [ax, ay] = f[i], [bx, by] = f[(i + 1) % f.length];
      const dx = bx - ax, dy = by - ay, l = dx * dx + dy * dy || 1;
      const u = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / l));
      const d = Math.hypot(x - ax - u * dx, y - ay - u * dy);
      if (d < bd) { bd = d; best = b.name; }
    }
  }
  return best;
}
