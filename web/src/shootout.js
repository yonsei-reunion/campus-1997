// 농구 1분 슛 게임 (the title card's game, or ./?game=shoot): on the 대강당 court, as many baskets as you can in a
// minute. You start on the free-throw line of the north basket; a friend stands off to your right towards the basket
// by a heap of balls and keeps you supplied: they bend for a ball, come up with it and chest-pass it to wherever you
// stand as soon as your shot is away (ballpose.js). Walk where you like: the farther out, the narrower the timing
// (hoops.js). A shot counts if it left the hands before the buzzer. Balls that have come down fade and turn up in
// the heap again. Every game is kept in this browser with its place in the ranking (shootrecords.js).
// Loaded only when the game starts (main.js).
import * as THREE from 'three';
import { play } from './characters.js';
import { BallForm, PICK, PASS, R } from './ballpose.js';
import { FREE_THROW, verdict } from './hoops.js';
import { lineTime } from './talk.js';
import { wrapAngle, copyButton, gameUrl } from './util.js';
import * as Records from './shootrecords.js';

const FRIEND = 'man-grey';              // 아이보리 점퍼: a student you never walk as
const TIME = 60, COUNT = 3;
const POOL = 6, HEAP = 3;               // balls in all, and in the heap at the friend's feet
// court-local, from the shooting spot on the free-throw line: the friend (towards the basket, to your right) and the
// heap before their feet (towards you)
const FRIEND_AT = [3.0, -2.1], HEAP_AT = 0.5;
const FRIEND_TOP = 1.73;

export class Shootout {
  // ball: hoops.js Basketball; bubbles: talk.js Bubbles; sound: audio.js Sound; onQuit: back to the walk (main.js)
  constructor({ scene, cast, player, ball, ui, bubbles, shadows, blobs, sound, mobile = false, onQuit = null }) {
    Object.assign(this, { scene, player, ball, ui, bubbles, sound, mobile, onQuit });
    this.f = cast.make(FRIEND, null);
    shadows?.addDynamic(this.f.holder);
    blobs?.addPerson(this.f);
    this.form = null;
    this.state = 'off';                 // off | count | play | over | done
    this.body = () => {
      const p = this.f.holder.position;
      return [{ x: p.x, z: p.z, y: p.y, top: p.y + 1.7, r: 0.22 }];
    };
    // the shooting spot, the friend's and the heap's (three coordinates, on the slab)
    const hoop = ball.hoops.find((h) => h.sg > 0);
    this.hoop = hoop;
    const sx = ball.court.L / 2 - 1.575 - FREE_THROW;
    const at = (lx, ly) => { const [x, y] = ball.toWorld(lx, ly); return new THREE.Vector3(x, ball.floorAt(x, -y, ball.court.h + 50), -y); };
    this.spot = at(sx, 0);
    this.fspot = at(sx + FRIEND_AT[0], FRIEND_AT[1]);
    const toSpot = this.spot.clone().sub(this.fspot).setY(0).normalize(), lat = new THREE.Vector3(-toSpot.z, 0, toSpot.x);
    this.slots = [[-0.27, 0], [0, 0.12], [0.27, 0]].map(([s, f]) => {
      const p = this.fspot.clone().addScaledVector(toSpot, HEAP_AT + f).addScaledVector(lat, s);
      p.y = ball.floorAt(p.x, p.z, p.y + 2) + R;
      return p;
    });
  }

  get on() { return this.state !== 'off'; }

  // (re)start: the walker on the free-throw line facing the basket, the friend by the heap, three seconds to go
  start() {
    const pl = this.player, b = this.ball;
    if (!this.f.holder.parent) this.scene.add(this.f.holder);
    // what the walker had in hand, or in the air, goes back to the heap with the rest
    if (b.shot) { b.shot = null; pl.cam.aim = null; }
    b.mine = null;
    while (b.balls.length < POOL) b.add();
    b.balls.forEach((x, i) => {
      x.shot = null; x.pass = null; x.vel.set(0, 0, 0); x.fade = 0; x.mesh.scale.setScalar(1);
      if (i < HEAP) { x.state = 'pile'; x.slot = i; x.pos.copy(this.slots[i]); } else { x.state = 'away'; x.slot = -1; }
    });
    b.game = this;
    if (!b.bodies.includes(this.body)) b.bodies.push(this.body);
    const yaw = Math.atan2(this.hoop.rim.x - this.spot.x, this.hoop.rim.z - this.spot.z);
    pl.teleport(this.spot.x, -this.spot.z, yaw - Math.PI);
    if (!pl.fpv) { pl.cam.dist = 4.6; pl.cam.lift = 0.12; }
    const fh = Math.atan2(this.spot.x - this.fspot.x, this.spot.z - this.fspot.z);
    const a = this.f;
    a.holder.position.copy(this.fspot);
    a.heading = fh; a.holder.rotation.set(0, fh, 0);
    play(a, 'idle', { fade: 0 });
    a.mixer.update(0.3);
    if (!this.form) this.form = new BallForm(a);
    this.form.rest();
    this.fst = 'wait'; this.ft = 0; this.fb = null; this.fW = 0;
    this.state = 'count'; this.clock = COUNT; this.shown = 0;
    Object.assign(this, { makes: 0, shots: 0, threes: 0, perfect: 0, streak: 0, said10: false });
    this.hudEl().hidden = false;
    this.results(false);
    pl.enabled = true;
    this.say('내가 공 줄게! 1분 동안 몇 개 넣나 보자', 0.2);
  }

  // back to the walk: the friend goes, the ball in hand (or one) stays
  stop() {
    if (!this.on) return;
    this.state = 'off';
    const b = this.ball, pl = this.player;
    if (this.f.holder.parent) this.scene.remove(this.f.holder);
    this.form?.rest();
    b.bodies = b.bodies.filter((x) => x !== this.body);
    b.game = null;
    let keep = b.mine;
    if (!keep) {
      keep = b.balls.find((x) => x.state === 'ground') || b.balls[0];
      const p = pl.pos, h = pl.heading;
      keep.pos.set(p.x + Math.sin(h) * 0.9, 0, p.z + Math.cos(h) * 0.9);
      keep.pos.y = b.floorAt(keep.pos.x, keep.pos.z, p.y + 1) + R;
      keep.state = 'ground'; keep.vel.set(0, 0, 0); keep.shot = null; keep.pass = null;
    }
    for (const x of b.balls) { x.fade = 0; x.mesh.scale.setScalar(1); if (x !== keep) { x.state = 'away'; x.shot = null; x.pass = null; } }
    b.free = keep;
    this.hud.el.hidden = true;
    this.big('');
    this.results(false);
    this.onQuit?.();
  }

  // hoops.js asks
  canShoot() { return this.state === 'play'; }
  meter() { return true; }
  onRelease(s) { if (this.state === 'play' && verdict(s.q)[1] === 'perfect') this.perfect++; }
  onShot(b) {
    b.shot.counts = this.state === 'play';
    if (b.shot.counts) this.shots++;
  }
  onScore(b) {
    if (!b.shot.counts) return;
    this.makes++;
    this.streak++;
    if (b.shot.three) this.threes++;
    this.hud.el.classList.remove('bump'); void this.hud.el.offsetWidth; this.hud.el.classList.add('bump');
    if (b.shot.three && Math.random() < 0.6) this.say('3점!');
    else if (this.streak === 3) this.say('오, 감 좋은데?');
    else if (this.streak === 6) this.say('불붙었다!');
    else if (Math.random() < 0.15) this.say(['나이스!', '좋아!', '굿!'][Math.floor(Math.random() * 3)]);
  }
  onCatch() {}

  say(text, delay = 0) {
    const t = (this.t ?? 0) + delay;
    this.bubbles?.add(this.f.holder, FRIEND_TOP, text, t, t + Math.min(lineTime(text), 2.4));
  }

  // circles the walker collides with (the friend), appended to out
  movers(px, py, out) {
    if (!this.on) return out;
    const p = this.f.holder.position;
    const c = (this.circle ||= { x: 0, y: 0, r: 0.3 });
    c.x = p.x; c.y = -p.z;
    out.push(c);
    return out;
  }

  // t: the loop's clock (speech bubbles); paused: the game's menu or a card is open (the clock stops)
  update(dt, t, paused) {
    if (!this.on) return;
    this.t = t;
    if (!paused) {
      this.tick(dt);
      this.friend(dt);
      this.recycle(dt);
    }
    this.drawHud();
  }

  tick(dt) {
    if (this.state === 'count') {
      this.clock -= dt;
      const n = Math.ceil(this.clock);
      if (n !== this.shown && n > 0) { this.shown = n; this.big(String(n)); this.sound?.cue('beep'); }
      if (this.clock <= 0) { this.state = 'play'; this.clock = TIME; this.big('시작!'); this.sound?.cue('go'); }
    } else if (this.state === 'play') {
      this.clock -= dt;
      if (this.clock <= 10 && !this.said10) { this.said10 = true; this.say('10초 남았어!'); }
      if (this.clock <= 0) { this.clock = 0; this.state = 'over'; this.overT = 0; this.big('끝!'); this.sound?.cue('buzzer'); }
    } else if (this.state === 'over') {
      // the shots let go before the buzzer come down first
      this.overT += dt;
      const flying = this.ball.balls.some((x) => x.shot?.counts && !x.shot.scored && x.state === 'flying' && x.age < 3.5);
      if ((this.overT > 1.4 && !flying) || this.overT > 4) this.finish();
    }
    if (this.bigT !== undefined) { this.bigT -= dt; if (this.bigT <= 0) { this.big(''); this.bigT = undefined; } }
  }

  // ---------------------------------------------------------------- the friend
  goF(name) { this.fst = name; this.ft = 0; }

  heapBall() {
    let best = null;
    for (const x of this.ball.balls) if (x.state === 'pile' && !x.fade && (!best || x.slot === 1)) best = x;
    return best;
  }

  friend(dt) {
    const a = this.f, form = this.form, pl = this.player, b = this.ball;
    a.mixer.update(dt);
    this.ft += dt;
    const live = this.state === 'count' || this.state === 'play';
    const fh = a.holder.position;
    const toward = (p) => Math.atan2(p.x - fh.x, p.z - fh.z);
    let face = pl.pos;
    switch (this.fst) {
      case 'wait': {
        const hb = live && this.heapBall();
        if (hb) { this.fb = hb; this.fat = hb.pos.clone(); this.goF('turn'); }
        break;
      }
      case 'turn':
        face = this.fat;
        if (Math.abs(wrapAngle(toward(this.fat) - a.heading)) < 0.2 || this.ft > 0.6) this.goF('pick');
        break;
      case 'pick':
        face = this.ft < PICK.DOWN + 0.15 ? this.fat : pl.pos;
        if (this.ft >= PICK.DOWN && this.fb.state === 'pile') { this.fb.state = 'held'; this.fb.slot = -1; }
        if (this.ft >= PICK.UP) this.goF('ready');
        break;
      case 'ready':
        if (this.state === 'play' && b.ready && this.ft > 0.12 && pl.pos.distanceTo(fh) < 18 && Math.abs(wrapAngle(toward(pl.pos) - a.heading)) < 0.3) this.goF('pass');
        if (!live) this.goF('keep');
        break;
      case 'pass':
        if (this.ft >= PASS.FOLLOW) this.goF('down');
        break;
      case 'down':
        if (this.ft > 0.2) this.goF('wait');
        break;
      case 'keep':      // the buzzer went with a ball in hand: hold on to it
        break;
    }
    a.heading += wrapAngle(toward(face) - a.heading) * (1 - Math.exp(-dt * 9));
    a.holder.rotation.set(0, a.heading, 0);
    const busy = this.fst === 'pick' || this.fst === 'ready' || this.fst === 'pass' || this.fst === 'keep';
    this.fW += ((busy ? 1 : 0) - this.fW) * Math.min(1, dt * (busy ? 10 : 6));
    if (this.fst === 'pick') form.pose('pick', { t: this.ft, at: this.fat, w: 1 });
    else if (this.fst === 'ready' || this.fst === 'keep') form.pose('hold', { w: this.fW });
    else if (this.fst === 'pass') form.pose('pass', { t: this.ft, w: this.fW });
    else if (this.fW > 0.01) form.pose('free', { w: this.fW });
    else if (form.last) form.rest();
    const fb = this.fb;
    if (fb?.state === 'held') {
      if (form.ball) fb.pos.copy(form.ball);
      else if (this.fst === 'pass') {
        // let go: to the walker's hands, a little faster the farther (a flat chest pass)
        const to = b.form.holdPoint(pl.cam.fp, pl.eyeH), d = form.from.distanceTo(to);
        b.passTo(fb, form.from, Math.min(1.0, Math.max(0.35, d / 7.5)), 0.12 + 0.025 * d);
        this.fb = null;
        // more balls into the heap while the friend looks the other way
        this.refill = true;
      }
    }
  }

  // balls that have come down fade out, and come back in the heap
  recycle(dt) {
    const b = this.ball, lim = b.court.L / 2 + 4, wide = b.court.W / 2 + 4;
    for (const x of b.balls) {
      if (x.fade) {
        x.fadeT += dt;
        const u = Math.min(1, x.fadeT / 0.3);
        x.mesh.scale.setScalar(x.fade < 0 ? 1 - u : u);
        if (u >= 1) {
          if (x.fade < 0) { x.state = 'away'; x.shot = null; }
          x.fade = 0; x.mesh.scale.setScalar(1);
        }
        continue;
      }
      if (x.state !== 'ground' && x.state !== 'flying') continue;
      const [lx, ly] = b.toLocal(x.pos);
      const slow = x.state === 'ground' && x.vel.lengthSq() < 0.36;
      if (x.age > 1 && (slow || x.age > 7 || Math.abs(lx) > lim || Math.abs(ly) > wide)) {
        x.fade = -1; x.fadeT = 0;
        if (x.shot?.counts && !x.shot.scored) this.streak = 0;
      }
    }
    if (!this.refill && this.fst !== 'pass' && this.fst !== 'down') return;
    const used = new Set(b.balls.filter((x) => x.state === 'pile').map((x) => x.slot));
    for (let i = 0; i < HEAP; i++) {
      if (used.has(i)) continue;
      const x = b.balls.find((y) => y.state === 'away' && !y.fade);
      if (!x) break;
      x.state = 'pile'; x.slot = i; x.pos.copy(this.slots[i]); x.vel.set(0, 0, 0); x.shot = null;
      x.fade = 1; x.fadeT = 0; x.mesh.scale.setScalar(0);
    }
    this.refill = false;
  }

  // ---------------------------------------------------------------- the score, the clock, the results
  hudEl() {
    if (this.hud) return this.hud.el;
    const el = document.createElement('div');
    el.id = 'shoothud';
    el.innerHTML = '<div class="clock"><small>남은 시간</small><b>1:00</b></div><div class="score"><small>골</small><b>0</b><span>슛 0</span></div>';
    document.body.appendChild(el);
    const big = document.createElement('div');
    big.id = 'shootbig';
    document.body.appendChild(big);
    this.hud = { el, clock: el.querySelector('.clock b'), score: el.querySelector('.score b'), shots: el.querySelector('.score span'), big };
    return el;
  }

  drawHud() {
    const h = this.hud;
    if (!h) return;
    const s = this.state === 'count' ? TIME : Math.max(0, this.clock);
    const txt = s < 10 && this.state === 'play' ? s.toFixed(1) : `${Math.floor(Math.ceil(s) / 60)}:${String(Math.ceil(s) % 60).padStart(2, '0')}`;
    if (h.clock.textContent !== txt) h.clock.textContent = txt;
    const m = String(this.makes);
    if (h.score.textContent !== m) h.score.textContent = m;
    const sh = `슛 ${this.shots}${this.threes ? ` · 3점 ${this.threes}` : ''}`;
    if (h.shots.textContent !== sh) h.shots.textContent = sh;
    h.el.classList.toggle('hurry', this.state === 'play' && s < 10);
  }

  // the big word in the middle: the count, 시작!, 끝!
  big(text) {
    const el = this.hud?.big;
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('small', text.length > 2);
    el.classList.remove('pop'); void el.offsetWidth;
    if (text) { el.classList.add('pop'); this.bigT = text.length > 1 ? 1.1 : 0.9; }
  }

  finish() {
    this.state = 'done';
    this.big('');
    const pl = this.player;
    pl.enabled = false;                    // (behind the results card)
    const prev = Records.load()[0]?.makes ?? 0;
    const rec = { id: Date.now(), at: Date.now(), makes: this.makes, shots: this.shots, threes: this.threes, perfect: this.perfect,
      hero: pl.actor.id, view: pl.fpv ? 'first' : 'third', name: Records.lastName() };
    const { rank, total } = Records.add(rec);
    const top = this.makes > prev && this.makes > 0;
    this.say(top ? `${this.makes}골! 신기록이다!` : rank <= 3 && total > 3 ? `${this.makes}골, ${rank}등이야!` : this.makes >= 10 ? `${this.makes}골! 잘하는데?` : '수고했어! 한 번 더?', 0.1);
    this.results(true, { rec, rank, total, top });
  }

  // the results card: the score, its place in this browser's ranking (a name may be typed for it) and the ranking
  results(show, info = {}) {
    let el = this.resEl;
    if (!show) { if (el) el.hidden = true; return; }
    if (!el) {
      el = this.resEl = document.createElement('div');
      el.id = 'shootresult';
      el.innerHTML = '<div><h2>1분 슛 게임</h2><p class="big"></p><p class="detail"></p><p class="best"></p>'
        + '<label class="name">이름 <input type="text" maxlength="12" enterkeyhint="done" autocomplete="off" spellcheck="false" /></label>'
        + '<div class="ranks"></div>'
        + '<div class="btns"><button type="button" class="again">다시 하기</button><button type="button" class="quit">그만하고 산책하기</button></div>'
        + '<p class="link"><button type="button" class="all">순위 전체 보기</button><button type="button" class="copy">게임 주소 복사</button>'
        + '<br>이 주소로 친구와 겨뤄 보세요 <code></code></p></div>';
      document.body.appendChild(el);
      el.querySelector('.again').addEventListener('click', (e) => { e.currentTarget.blur(); this.start(); });
      el.querySelector('.quit').addEventListener('click', (e) => { e.currentTarget.blur(); this.stop(); });
      el.querySelector('.all').addEventListener('click', () => Records.openRanking({ mark: this.rec?.id, onChange: () => this.drawRanks() }));
      copyButton(el.querySelector('.copy'), gameUrl);
      const name = el.querySelector('.name input');
      name.addEventListener('input', () => { if (this.rec) { Records.rename(this.rec.id, name.value); this.drawRanks(); } });
      name.addEventListener('keydown', (e) => { if (e.key === 'Enter') name.blur(); });
    }
    this.rec = info.rec;
    const pct = this.shots ? Math.round((100 * this.makes) / this.shots) : 0;
    el.querySelector('.big').innerHTML = `${this.makes}<small>골</small>`;
    el.querySelector('.detail').textContent = `슛 ${this.shots}번 · 성공률 ${pct}%${this.threes ? ` · 3점슛 ${this.threes}개` : ''}${this.perfect ? ` · 완벽한 타이밍 ${this.perfect}번` : ''}`;
    const be = el.querySelector('.best');
    be.textContent = info.top ? '새 기록! 이 브라우저 1위' : `이 브라우저 ${info.rank}위 (${info.total}판 가운데)`;
    be.classList.toggle('new', !!info.top);
    const name = el.querySelector('.name input');
    name.value = info.rec.name || '';
    name.placeholder = Records.who({ hero: info.rec.hero });
    this.drawRanks();
    el.querySelector('.link code').textContent = gameUrl();
    el.hidden = false;
    el.querySelector('.again').focus({ preventScroll: true });
  }

  // the first five of the ranking, this game marked (below them at its place when it is further down)
  drawRanks() {
    if (!this.resEl) return;
    this.resEl.querySelector('.ranks').replaceChildren(Records.table(Records.load(), { mark: this.rec?.id, limit: 5 }));
  }

  get resultsOpen() { return !!this.resEl && !this.resEl.hidden; }
}
