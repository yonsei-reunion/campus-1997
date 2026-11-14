// 대강당 앞 농구장: basketballs to pick up (E) and shoot at the hoops. A shot is timed: hold E or Space (on a phone the
// button) and let go at the top of the jump, when the meter's bar is in the green. The farther from the rim, the
// narrower the green; let go early and the ball falls short, late and it goes long. The motions (the men's one-handed
// shot, the women's two-handed set shot, catching) are in ballpose.js; the 1-minute game (shootout.js) adds balls,
// a friend passing them and the score.
// The rims, backboards and nets are in the court model (blender/landmarks.py basketball_court); this file only knows
// where they are: court-local x = ±(L/2 - 1.575) is the rim, ±(L/2 - 1.2) the backboard, rim height 3.05 m.
// Loaded when the walk or the view comes near the court, or for the game (main.js), not with the page.
import * as THREE from 'three';
import { R, G, SHOT, BallForm, makeBall, hopAt } from './ballpose.js';
import './basket.css';

const RIM_R = 0.235, RIM_H = 3.05;
export const THREE_PT = 6.25;           // the 3-point line of 1997 (FIBA: 6.75 m since 2010)
export const FREE_THROW = 4.225;        // the free-throw line from the rim's centre (5.8 m from the baseline)
const REACH = 16;                       // farther than this from both rims a shot is a throw
// the timing window: half its width (s) round the top of the jump, narrower the farther (m) from the rim
export const windowAt = (d) => Math.max(0.022, Math.min(0.08, 0.08 - 0.007 * (d - 2)));
const PERFECT = 0.4;                    // of the window: 완벽
// where the shot comes down off the rim's centre (m, along the line of the shot and across it) for a release q
// windows late (- early). Coming down at 60 degrees from the free-throw line, 52 from 9 m (flight), the ball clears the
// front of the rim (and the 2 cm the rim pushes from) 4 - 7 cm short of the centre; long, the back of the rim and the board knock it down into the
// net more often than not (src/hoops.js step: 9 in 10 still go in 15 cm long). So early shots fall short less far
// than late ones go long: inside the window it goes in, a little out of it it hits the rim (and may drop), farther
// out it misses, and wider
function miss(q, d) {
  const a = Math.abs(q), r = () => Math.random() - 0.5;
  const k = q < 0 ? [-0.028, -0.2] : [0.05, 0.34];
  if (a <= 1) return [k[0] * a + 0.008 * r(), 0.02 * r()];
  return [k[0] + k[1] * Math.min(4, a - 1) + 0.03 * r(), 2 * (0.015 + 0.06 * Math.min(3, a - 1) + 0.0015 * d) * r()];
}
// a shot's time in the air (s) from d m out: a high arc, so it comes down steeply into the rim
const flight = (d) => Math.min(2.0, 0.95 + 0.07 * d);
// what the meter says of a release q windows late
export function verdict(q) {
  const a = Math.abs(q);
  if (a <= PERFECT) return ['완벽!', 'perfect'];
  if (a <= 1) return ['좋아요', 'good'];
  if (q < 0) return [a > 2.2 ? '너무 빨라요' : '조금 빨라요', 'early'];
  return [a > 2.2 ? '너무 늦어요' : '조금 늦어요', 'late'];
}
const _to = new THREE.Vector3(), _n = new THREE.Vector3();

// one ball: ground (resting or rolling) | flying | held | pass (on its way to the walker's hands) | pile (the game's,
// at the friend's feet) | away (not in the scene)
class Ball {
  constructor(mesh) {
    this.mesh = mesh;
    this.pos = mesh.position;
    this.vel = new THREE.Vector3();
    this.state = 'ground';
    this.shot = null;           // { hoop, d, three, q, scored } while a shot is in the air
    this.pass = null;           // { from, t, T, arc }
    this.idle = 0;              // s at rest
    this.age = 0;               // s since it left the hands
  }
}

export class Basketball {
  // court: campus.json statues.court; shadows: the moving casters' shadow map (main.js); patch: for the ball's material
  constructor({ scene, player, ui, court, hf, shadows = null, mobile = false, patch = null }) {
    Object.assign(this, { scene, player, ui, court, hf, shadows, mobile, patch });
    this.cos = Math.cos(court.rot); this.sin = Math.sin(court.rot);
    // rim centres in three coordinates (campus (x, y) -> three (x, h, -y)), and the backboards behind them
    this.hoops = [-1, 1].map((sg) => {
      const rim = this.toWorld(sg * (court.L / 2 - 1.575), 0);
      const board = this.toWorld(sg * (court.L / 2 - 1.2), 0);
      return { sg, rim: new THREE.Vector3(rim[0], court.h + RIM_H, -rim[1]), board: new THREE.Vector3(board[0], court.h, -board[1]) };
    });
    this.balls = [];
    // the ball lies on the court a few metres from the centre circle towards the north basket, in view of a walker
    // sent to the court (who stands in the circle, or comes up from the south).  Not off the sideline: the slab's
    // margin there is the low hedge along the bank's top, which hid it
    const home = this.toWorld(3.0, 2.0);
    this.home = new THREE.Vector3(home[0], this.floorAt(home[0], -home[1], 1000) + R, -home[1]);
    this.free = this.add();
    this.free.pos.copy(this.home);
    this.shots = 0; this.makes = 0;
    this.form = new BallForm(player.actor);
    this.mine = null;           // the ball in the walker's hands
    this.shot = null;           // { t, tr, hoop, d, win, q, ball, gone } from the press to the end of the follow-through
    this.armW = 0;              // how far the arms follow the ball instead of the walk / idle clip
    this.bodies = [];           // () => [{ x, z, y, top, r }]: people the balls bounce off (the game's friend)
    this.game = null;           // shootout.js while the game is on: onShot, onScore, onCatch
    this.frameAt = 0;
    this.meter = null;
  }

  add() {
    const b = new Ball(makeBall(this.patch));
    this.scene.add(b.mesh);
    this.shadows?.addDynamic(b.mesh, 1.2);
    this.balls.push(b);
    return b;
  }

  // the ground under three (x, z): the surfaces the walker walks on, looked for from height `top` down (the court's
  // slab stands up to 5 m over the terrain on 학생회관 별관's side); the terrain where there is none
  floorAt(x, z, top) {
    return this.player.groundAt(x, z, top) ?? this.hf.height(x, -z);
  }

  toWorld(lx, ly) {
    const c = this.court;
    return [c.pos[0] + lx * this.cos - ly * this.sin, c.pos[1] + lx * this.sin + ly * this.cos];
  }

  toLocal(p) {                                     // three position -> court-local (x along the long side, y across)
    const dx = p.x - this.court.pos[0], dy = -p.z - this.court.pos[1];
    return [dx * this.cos + dy * this.sin, -dx * this.sin + dy * this.cos];
  }

  // (main.js, tools/snapshots.json: where the ball is)
  get pos() { return (this.mine || this.free).pos; }
  get held() { return !!this.mine && !this.shot; }

  // a ball on the ground within reach of the walker
  near() {
    const p = this.player.pos;
    let best = null, bd = 2.3;
    for (const b of this.balls) {
      if (b.state !== 'ground') continue;
      const d = Math.hypot(p.x - b.pos.x, p.z - b.pos.z);
      if (d < bd) { bd = d; best = b; }
    }
    return best;
  }

  // text for the E prompt (null = nothing to offer)
  prompt() {
    const k = this.mobile ? '눌러서 ' : '';
    if (this.shot) return this.shot.tr === null && this.shot.hoop ? '떼면 슛!' : null;
    if (this.mine && this.game && !this.game.canShoot()) return null;
    if (this.mine) return this.nearestHoop(REACH) ? `꾹 눌렀다 떼서 슛${this.mobile ? '' : ' (스페이스도)'}` : `${k}공 던지기 · 골대에 가까이 가 보세요`;
    if (!this.game && this.near()) return `${k}농구공 줍기`;
    return null;
  }

  nearestHoop(maxD) {
    const p = this.player.pos;
    let best = null, bd = maxD;
    for (const h of this.hoops) {
      const d = Math.hypot(h.rim.x - p.x, h.rim.z - p.z);
      if (d < bd) { bd = d; best = h; }
    }
    return best;
  }

  // E / a tap on the prompt with empty hands: pick up the ball (true when it did)
  action() {
    if (this.shot || this.mine || this.game) return false;
    const b = this.near();
    if (!b) return false;
    this.take(b);
    this.ui.toast(this.mobile ? '농구공을 주웠어요 · 골대 가까이에서 「슛」을 꾹 눌렀다가 막대가 초록 칸에 올 때 떼세요'
      : '농구공을 주웠어요 · 골대 가까이에서 E나 스페이스를 꾹 눌렀다가 막대가 초록 칸에 올 때 떼세요', 4500);
    return true;
  }

  take(b) {
    this.mine = b;
    b.state = 'held'; b.pass = null; b.shot = null;
    b.vel.set(0, 0, 0);
  }

  // E / Space / the button pressed with the ball in hand: turn to the basket and start the shot (true when it did)
  press() {
    if (!this.mine || this.shot || (this.game && !this.game.canShoot())) return false;
    const pl = this.player, p = pl.pos;
    const hoop = this.nearestHoop(REACH);
    const d = hoop ? Math.hypot(hoop.rim.x - p.x, hoop.rim.z - p.z) : 0;
    if (hoop) pl.face(Math.atan2(hoop.rim.x - p.x, hoop.rim.z - p.z));        // turn to face the basket
    pl.cam.aim = hoop ? hoop.rim : null;                                       // (first person: the view turns to it)
    this.shot = { t: 0, tr: null, hoop, d, win: hoop ? windowAt(d) : 1, q: 0, ball: this.mine, gone: false };
    pl.enabled = false;                                                        // stand still while shooting
    return true;
  }

  // ... and let go: when, against the top of the jump, decides the shot (the ball leaves the fingers SHOT.FLICK later)
  letGo() {
    const s = this.shot;
    if (!s || s.tr !== null) return false;
    // (the key comes up between two frames: the time since the last one counts)
    s.tr = s.t + Math.min(0.05, Math.max(0, (performance.now() - this.frameAt) / 1000));
    s.q = (s.tr - SHOT.TOP) / s.win;
    if (s.hoop) this.game?.onRelease?.(s);
    return true;
  }

  // the walker's hands are free for a pass: no ball, and any shot on its way
  get ready() { return !this.mine && (!this.shot || this.shot.gone) && !this.incoming(); }
  incoming() { return this.balls.find((b) => b.state === 'pass') || null; }

  // ball b flies from `from` (world) to the walker's hands in T s, `arc` m over the straight line at its middle
  passTo(b, from, T, arc = 0.25) {
    b.state = 'pass'; b.shot = null;
    b.pass = { from: from.clone(), t: 0, T, arc };
    b.pos.copy(from);
  }

  launch(s, from) {
    const b = s.ball, pl = this.player;
    this.mine = null;
    b.state = 'flying'; b.pos.copy(from); b.age = 0; b.idle = 0;
    if (s.hoop) {
      const rim = s.hoop.rim, dx = rim.x - from.x, dz = rim.z - from.z, d = Math.hypot(dx, dz) || 1;
      const [along, across] = miss(s.q, d);
      const to = _to.copy(rim);
      to.x += (dx * along - dz * across) / d; to.z += (dz * along + dx * across) / d;
      const T = flight(d);
      b.vel.set((to.x - from.x) / T, (to.y - from.y + 0.5 * G * T * T) / T, (to.z - from.z) / T);
      b.shot = { hoop: s.hoop, d: s.d, three: s.d >= THREE_PT, q: s.q, scored: false };
      this.shots++;
      this.game?.onShot?.(b);
    } else {
      b.vel.set(Math.sin(pl.heading) * 5, 5.5, Math.cos(pl.heading) * 5);
      b.shot = null;
    }
  }

  endShot() {
    this.shot = null;
    const pl = this.player;
    pl.cam.aim = null;
    const open = this.ui.memoryOpen || this.ui.mapOpen || !document.getElementById('pause').hidden || this.game?.resultsOpen;
    if (!open) pl.enabled = true;
  }

  update(dt, tAcc, active) {
    this.frameAt = performance.now();
    const pl = this.player, s = this.shot;
    if (this.form.actor !== pl.actor) { this.form.rest(); this.form.setActor(pl.actor); }
    for (const b of this.balls) b.mesh.visible = b.state !== 'away';
    if (s) {
      s.t += dt;
      if (s.tr === null && s.t >= SHOT.LATE) this.letGo();               // held on too long: it goes, late
    }
    // the arms ease in when the ball is in hand (or about to be) and out again after the shot
    const inc = this.incoming(), catching = !!inc && inc.pass.T - inc.pass.t < 0.4;
    const want = this.mine || (s && !(s.gone && s.t > s.tr + SHOT.FLICK + SHOT.FOLLOW - 0.15)) || catching ? 1 : 0;
    this.armW += (want - this.armW) * Math.min(1, dt * (want ? 9 : 5));
    if (this.armW < 0.01 && !want) this.armW = 0;
    const fp = pl.cam.fp, eyeH = pl.eyeH, f = this.form;
    pl.cam.hop = 0;
    if (s) {
      const hop = hopAt(f.one, s.t);
      pl.pos.y += hop;                    // (player.js puts the walker back on the ground before the next frame)
      pl.cam.hop = hop;                   // (the first-person eye jumps with it)
      f.pose('shot', { t: s.t, tr: s.tr, w: this.armW, fp, eyeH });
      if (f.ball) s.ball.pos.copy(f.ball);
      else if (!s.gone) { s.gone = true; this.launch(s, f.from); }
      if (s.tr !== null && s.t >= s.tr + SHOT.FLICK + SHOT.FOLLOW) this.endShot();
    } else if (this.mine) {
      f.pose('hold', { w: this.armW, fp, eyeH });
      if (f.ball) this.mine.pos.copy(f.ball);
      this.mine.mesh.rotation.y = pl.heading;
    } else if (catching) {
      f.pose('catch', { at: inc.pos, w: this.armW });
    } else if (this.armW > 0) f.pose('free', { w: this.armW });
    else if (f.last) f.rest();
    this.drawMeter();
    if (!active) return;
    const sub = Math.ceil(dt / 0.01);
    const moving = this.balls.filter((b) => b.state === 'ground' || b.state === 'flying');
    for (const b of this.balls) if (b.state === 'pass') this.flyPass(b, dt);
    for (let i = 0; i < sub; i++) {
      for (const b of moving) this.step(b, dt / sub);
      this.collide(moving);
    }
    for (const b of moving) b.age += dt;
    // the ball left far from the court goes back to its spot once nobody is near it (not in the game: it has its own)
    const b = this.free;
    if (this.game || b.state !== 'ground' || b.vel.lengthSq() >= 0.01) { b.idle = 0; return; }
    b.idle += dt;
    const pd = Math.hypot(pl.pos.x - b.pos.x, pl.pos.z - b.pos.z), [lx, ly] = this.toLocal(b.pos);
    if (b.idle > 20 && pd > 15 && (Math.abs(lx) > this.court.L / 2 + 14 || Math.abs(ly) > this.court.W / 2 + 14)) {
      b.pos.copy(this.home); b.vel.set(0, 0, 0); b.idle = 0;
    }
  }

  // a pass on its way: to where the walker holds the ball (wherever they have moved to)
  flyPass(b, dt) {
    const p = b.pass;
    p.t += dt;
    const u = Math.min(1, p.t / p.T);
    const to = this.form.holdPoint(this.player.cam.fp, this.player.eyeH, _to);
    b.pos.lerpVectors(p.from, to, u);
    b.pos.y += p.arc * 4 * u * (1 - u);
    b.mesh.rotation.x -= dt * 9;
    if (u >= 1) {
      this.take(b);
      this.onSound?.('catch', b.pos, 2);
      this.game?.onCatch?.(b);
    }
  }

  // the balls off each other (equal masses, a little bounce lost)
  collide(list) {
    for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) {
      const a = list[i], b = list[j];
      _n.subVectors(b.pos, a.pos);
      const d = _n.length();
      if (d >= 2 * R || d < 1e-6) continue;
      _n.divideScalar(d);
      const push = (2 * R - d) / 2;
      a.pos.addScaledVector(_n, -push); b.pos.addScaledVector(_n, push);
      const vn = b.vel.dot(_n) - a.vel.dot(_n);
      if (vn < 0) { const k = -0.8 * vn; a.vel.addScaledVector(_n, -k); b.vel.addScaledVector(_n, k); a.state = b.state = 'flying'; }
    }
  }

  step(b, dt) {
    if (b.state === 'ground' && b.vel.lengthSq() < 0.0004) { b.vel.set(0, 0, 0); return; }
    const pos = b.pos, vel = b.vel;
    const prevY = pos.y;
    vel.y -= G * dt;
    pos.addScaledVector(vel, dt);
    b.mesh.rotation.x += vel.z * dt * 6; b.mesh.rotation.z -= vel.x * dt * 6;
    // ground
    const gy = this.floorAt(pos.x, pos.z, prevY + 0.3) + R;      // (from where it was: a fall through the slab's top bounces)
    if (pos.y < gy) {
      pos.y = gy;
      if (vel.y < -0.8) {
        this.onSound?.('bounce', pos, -vel.y);
        vel.y = -vel.y * 0.72; vel.x *= 0.92; vel.z *= 0.92;
        b.state = 'flying';
      } else {
        vel.y = 0; b.state = 'ground';
        const f = Math.max(0, 1 - 1.6 * dt);
        vel.x *= f; vel.z *= f;
      }
    } else if (b.state === 'ground') b.state = 'flying';
    // people: an upright cylinder each (the walker, and the game's friend); not the shooter as the ball leaves the hands
    const pl = this.player.pos;
    const people = b.age > 0.35 ? [{ x: pl.x, z: pl.z, y: pl.y, top: pl.y + 1.7, r: 0.22 }] : [];
    for (const q of this.bodies) people.push(...q());
    for (const q of people) {
      const dx = pos.x - q.x, dz = pos.z - q.z, d = Math.hypot(dx, dz), m = q.r + R;
      if (d >= m || d < 1e-6 || pos.y < q.y || pos.y > q.top + R) continue;
      _n.set(dx / d, 0, dz / d);
      pos.x = q.x + _n.x * m; pos.z = q.z + _n.z * m;
      const vn = vel.dot(_n);
      if (vn < 0) vel.addScaledVector(_n, -1.4 * vn);
    }
    for (const h of this.hoops) {
      // backboard: a 1.8 x 1.05 m plate in the plane x_local = const, facing the court
      const [lx, ly] = this.toLocal(pos);
      const bx = h.sg * (this.court.L / 2 - 1.2);
      const board = (lx - bx) * h.sg;                      // >0 means behind the board
      const [plx] = this.toLocal(_to.set(pos.x - vel.x * dt, pos.y, pos.z - vel.z * dt));
      const was = (plx - bx) * h.sg;
      if (was < R && board >= 0 && Math.abs(ly) < 0.95 && pos.y > h.rim.y - 0.2 && pos.y < h.rim.y + 0.85 && was <= 0.06) {
        // reflect the velocity component along the court's long axis
        const vl = vel.x * this.cos + -vel.z * this.sin;
        if (vl * h.sg > 0) {
          this.onSound?.('board', pos, Math.abs(vl));
          const k = (1 + 0.55) * vl;
          vel.x -= k * this.cos; vel.z -= -k * this.sin;
          const w = this.toWorld(bx - h.sg * R * 1.2, ly);
          pos.x = w[0]; pos.z = -w[1];
        }
      }
      // rim: the nearest point of the ring pushes the ball away
      const dx = pos.x - h.rim.x, dz = pos.z - h.rim.z, dh = Math.hypot(dx, dz) || 1e-6;
      const rp = _to.set(h.rim.x + dx / dh * RIM_R, h.rim.y, h.rim.z + dz / dh * RIM_R);
      const nrm = _n.copy(pos).sub(rp);
      const dist = nrm.length();
      if (dist < R + 0.02 && dist > 1e-6) {
        nrm.divideScalar(dist);
        const vn = vel.dot(nrm);
        if (vn < 0) {
          if (vn < -0.5) this.onSound?.('rim', pos, -vn);
          vel.addScaledVector(nrm, -(1 + 0.5) * vn);
        }
        pos.copy(rp).addScaledVector(nrm, R + 0.025);
      }
      // through the hoop, downwards
      if (prevY >= h.rim.y && pos.y < h.rim.y && vel.y < 0 && dh < RIM_R - R * 0.6 && b.shot && !b.shot.scored) {
        b.shot.scored = true;
        this.onSound?.('swish', pos, 3);
        if (this.game) this.game.onScore(b);
        else {
          this.makes++;
          this.ui.toast(`골인! ${b.shot.three ? '3점슛 · ' : ''}${this.makes}골 / ${this.shots}번 시도`, 3200);
        }
      }
      if (pos.y < h.rim.y && pos.y > h.rim.y - 0.5 && dh < RIM_R) { vel.x *= 0.92; vel.z *= 0.92; vel.y *= 0.985; }   // the net slows it
    }
  }

  // ---------------------------------------------------------------- the meter
  // A bar beside the walker (before the eyes in first person) while the ball is in hand near a basket: it fills
  // from the press, and the green is the window round the top of the jump for this distance (the bright middle:
  // 완벽). After the release it holds where it was let go and says how it was.
  drawMeter() {
    const s = this.shot, pl = this.player;
    const hoop = s ? s.hoop : this.mine && this.nearestHoop(REACH);
    const fresh = s?.tr !== null && s?.tr !== undefined ? s.t - s.tr : 0;
    const show = !!hoop && (!s || fresh < 1.1) && (!this.game || this.game.meter());
    if (!show) { if (this.meter) this.meter.el.hidden = true; return; }
    const m = this.meter || this.makeMeter();
    m.el.hidden = false;
    const d = s ? s.d : Math.hypot(hoop.rim.x - pl.pos.x, hoop.rim.z - pl.pos.z), win = windowAt(d);
    const pc = (t) => `${(100 * Math.min(1, Math.max(0, t / SHOT.LATE))).toFixed(1)}%`;
    m.zone.style.bottom = pc(SHOT.TOP - win); m.zone.style.top = `calc(100% - ${pc(SHOT.TOP + win)})`;
    m.sweet.style.bottom = pc(SHOT.TOP - win * PERFECT); m.sweet.style.top = `calc(100% - ${pc(SHOT.TOP + win * PERFECT)})`;
    m.fill.style.height = pc(s ? (s.tr ?? s.t) : 0);
    const dist = `${d.toFixed(1)} m${d >= THREE_PT ? ' · 3점' : ''}`;
    if (m.dist.textContent !== dist) m.dist.textContent = dist;
    const v = s?.tr !== null && s?.tr !== undefined ? verdict(s.q) : null;
    const cls = v ? `on ${v[1]}` : s ? 'on' : '';
    if (m.el.className !== cls) { m.el.className = cls; m.say.textContent = v ? v[0] : ''; }
    // beside the walker on screen (their right, the foot of it at their knees), or before the eyes; above the prompt
    const box = pl.screenBox(pl.camera), mh = m.el.offsetHeight || 210;
    const pr = document.getElementById('prompt'), top = pr && !pr.hidden ? pr.getBoundingClientRect().top - 10 : innerHeight - 16;
    let x, y;
    if (box[0] < -1e3) { x = innerWidth * 0.62; y = innerHeight * 0.3; }
    else { x = Math.min(innerWidth - 70, box[2] + 26); y = box[3] - mh; }
    y = Math.max(60, Math.min(top - mh, y));
    m.el.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
  }

  makeMeter() {
    const el = document.createElement('div');
    el.id = 'shotmeter';
    el.innerHTML = '<div class="bar"><i class="zone"></i><i class="sweet"></i><i class="fill"></i></div><b class="say"></b><small class="dist"></small>';
    (document.getElementById('hud') || document.body).appendChild(el);
    const q = (s) => el.querySelector(s);
    this.meter = { el, zone: q('.zone'), sweet: q('.sweet'), fill: q('.fill'), say: q('.say'), dist: q('.dist') };
    return this.meter;
  }
}
