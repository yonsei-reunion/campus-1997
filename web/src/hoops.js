// 대강당 앞 농구장: a loose basketball you can pick up (E) and shoot at the hoops (E or Space while holding it).
// The rims, backboards and nets are in the court model (blender/landmarks.py basketball_court); this file only knows
// where they are: court-local x = ±(L/2 - 1.575) is the rim, ±(L/2 - 1.2) the backboard, rim height 3.05 m.
import * as THREE from 'three';
import { ArmPose } from './armpose.js';

const R = 0.12, G = 9.8;
const RIM_R = 0.235, RIM_H = 3.05;
// the shot, in seconds: gather (ball dips to the waist, knees would bend), rise (ball goes up past the face with a hop),
// release over the head, follow through, arms come down
const T_GATHER = 0.3, T_RELEASE = 0.7, T_END = 1.25;
const HOLD = new THREE.Vector3(0, 1.2, 0.34);               // ball held at the chest, in the walker's own frame (+Z = forward)
const LOW = new THREE.Vector3(0, 0.98, 0.3);
const HIGH = new THREE.Vector3(0, 2.18, 0.26);
// First person (player.js): the walker's body is not drawn, so the ball is carried out in front, at the lower edge
// of a level view, and the shot dips and goes up half a metre before the face instead of past the chin. Each is
// [metres over the eyes, metres ahead].
const FP_HOLD = [-0.3, 0.56], FP_LOW = [-0.5, 0.48], FP_HIGH = [0.52, 0.42];
const ease = (u) => u * u * (3 - 2 * u);

function ballTexture() {
  const c = document.createElement('canvas');
  c.width = 256; c.height = 128;
  const x = c.getContext('2d');
  x.fillStyle = '#c8581c'; x.fillRect(0, 0, 256, 128);
  for (let i = 0; i < 1500; i++) {                              // pebbled leather
    x.fillStyle = `rgba(${i % 2 ? '255,170,100' : '80,30,5'},0.08)`;
    x.fillRect(Math.random() * 256, Math.random() * 128, 2, 2);
  }
  x.strokeStyle = '#1a0d05'; x.lineWidth = 3;
  x.beginPath(); x.moveTo(0, 64); x.lineTo(256, 64); x.stroke();                       // equator seam
  for (const cx of [0, 128, 256]) { x.beginPath(); x.moveTo(cx, 0); x.lineTo(cx, 128); x.stroke(); }
  for (const cx of [64, 192]) {                                                        // curved side seams
    x.beginPath(); x.ellipse(cx, 64, 46, 80, 0, -Math.PI / 2, Math.PI / 2); x.stroke();
    x.beginPath(); x.ellipse(cx, 64, 46, 80, 0, Math.PI / 2, 3 * Math.PI / 2); x.stroke();
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

export class Basketball {
  constructor({ scene, player, ui, court, hf, mobile = false }) {
    Object.assign(this, { player, ui, court, hf, mobile });
    this.mesh = new THREE.Mesh(new THREE.SphereGeometry(R, 24, 16),
      new THREE.MeshStandardMaterial({ map: ballTexture(), roughness: 0.75 }));
    this.mesh.castShadow = true;
    scene.add(this.mesh);
    this.cos = Math.cos(court.rot); this.sin = Math.sin(court.rot);
    // rim centres in three coordinates (campus (x, y) -> three (x, h, -y)), and the backboards behind them
    this.hoops = [-1, 1].map((sg) => {
      const rim = this.toWorld(sg * (court.L / 2 - 1.575), 0);
      const board = this.toWorld(sg * (court.L / 2 - 1.2), 0);
      return { sg, rim: new THREE.Vector3(rim[0], court.h + RIM_H, -rim[1]), board: new THREE.Vector3(board[0], court.h, -board[1]) };
    });
    // the ball lies on the court a few metres from the centre circle towards the north basket, in view of a walker
    // sent to the court (who stands in the circle, or comes up from the south).  Not off the sideline: the slab's
    // margin there is the low hedge along the bank's top, which hid it
    const home = this.toWorld(3.0, 2.0);
    this.home = new THREE.Vector3(home[0], this.floorAt(home[0], -home[1], 1000) + R, -home[1]);
    this.pos = this.home.clone();
    this.vel = new THREE.Vector3();
    this.state = 'ground';            // ground (resting or rolling) | held | flying
    this.shots = 0; this.makes = 0;
    this.scored = false;
    this.idle = 0;
    this.mesh.position.copy(this.pos);
    this.pose = new ArmPose(player.actor);
    this.armW = 0;                    // how much the arms follow the pose instead of the walk/idle clip
    this.t = 0;                       // time into a shot
    this.shot = null;                 // {hoop} while the shot is being taken
    this.carry = new THREE.Vector3();
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

  get held() { return this.state === 'held' && !this.shot; }

  near() {
    const p = this.player.pos;
    return this.state === 'ground' && Math.hypot(p.x - this.pos.x, p.z - this.pos.z) < 2.3;
  }

  // text for the E prompt (null = nothing to offer)
  prompt() {
    const k = this.mobile ? '눌러서 ' : '';
    if (this.shot) return null;
    if (this.state === 'held') return this.nearestHoop(16) ? `${k}슛!` : `${k}공 던지기 · 골대에 가까이 가 보세요`;
    if (this.near()) return `${k}농구공 줍기`;
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

  // E / tap on the prompt: pick up, or shoot. Returns true when it did something.
  action() {
    if (this.shot) return true;
    if (this.state === 'held') { this.shoot(); return true; }
    if (this.near()) {
      this.state = 'held';
      this.ui.toast(this.mobile ? '농구공을 주웠어요 · 골대 가까이에서 버튼을 눌러 슛!' : '농구공을 주웠어요 · 골대 가까이에서 E 또는 스페이스로 슛!', 3500);
      return true;
    }
    return false;
  }

  // E: turn to the basket and start the shot (the ball leaves the hands at T_RELEASE, see release())
  shoot() {
    const pl = this.player, p = pl.pos;
    const hoop = this.nearestHoop(16);
    if (hoop) pl.face(Math.atan2(hoop.rim.x - p.x, hoop.rim.z - p.z));         // turn to face the basket
    pl.cam.aim = hoop ? hoop.rim : null;                                       // (first person: the view turns to it)
    this.shot = { hoop };
    this.t = 0;
    this.idle = 0;
    pl.enabled = false;                                                        // stand still while shooting
  }

  release() {
    const { hoop } = this.shot;
    const pl = this.player, p = pl.pos;
    const fwd = new THREE.Vector3(Math.sin(pl.heading), 0, Math.cos(pl.heading));
    const from = this.pos.clone();
    let v;
    if (hoop) {
      const d = Math.hypot(hoop.rim.x - from.x, hoop.rim.z - from.z);
      const err = 0.025 + 0.008 * d;                                    // longer shots miss more
      const to = hoop.rim.clone();
      to.x += (Math.random() - 0.5) * 2 * err; to.z += (Math.random() - 0.5) * 2 * err;
      const t = Math.min(1.7, 0.8 + 0.06 * d);
      v = new THREE.Vector3((to.x - from.x) / t, (to.y - from.y + 0.5 * G * t * t) / t, (to.z - from.z) / t);
      this.shots++;
      this.scored = false;
      this.shotFrom = d;
    } else {
      v = fwd.clone().multiplyScalar(5).setY(5.5);
      this.shotFrom = 0;
    }
    this.vel.copy(v);
    this.state = 'flying';
    this.hoopShot = !!hoop;
    this.lastRelease = from;
  }

  // ball and arms while it is held / being shot; returns the hop height in metres
  carryAndPose(dt) {
    const pl = this.player, holder = pl.actor.holder;
    holder.updateMatrixWorld(true);
    // where the ball is held: at the chest, or before the eyes as far as the view is in them (player.js cam.fp)
    const fp = pl.cam.fp;
    const at = (P, F) => (fp > 0 ? new THREE.Vector3(0, pl.eyeH + F[0], F[1]).lerp(P, 1 - fp) : P);
    let local = at(HOLD, FP_HOLD), hop = 0, spread = 0.115, follow = 0;
    if (this.shot) {
      if (!this.freeze) this.t += dt;      // (freeze: for stepping through the shot while testing)
      const t = this.t, low = at(LOW, FP_LOW), high = at(HIGH, FP_HIGH);
      if (t < T_GATHER) local = local.clone().lerp(low, ease(t / T_GATHER));
      else if (t < T_RELEASE) local = low.clone().lerp(high, ease((t - T_GATHER) / (T_RELEASE - T_GATHER)));
      else local = high;
      hop = t > 0.35 && t < 0.95 ? 0.13 * Math.sin(Math.PI * (t - 0.35) / 0.6) : 0;
      if (t >= T_RELEASE && this.state === 'held') this.release();
      if (t >= T_RELEASE) follow = Math.min(1, (t - T_RELEASE) / 0.3);
      if (t > T_RELEASE) spread = 0.115 - 0.05 * follow;
    }
    pl.cam.hop = hop;                      // (the first-person eye hops with the shot)
    if (this.state === 'held') {
      this.carry.copy(local);
      holder.localToWorld(this.pos.copy(this.carry));
      this.pos.y += hop;
      this.mesh.position.copy(this.pos);
      this.mesh.rotation.y = pl.heading;
    }
    // arms: hands on the ball's two sides; after release they follow through forward and a little down
    const side = new THREE.Vector3(1, 0, 0).applyQuaternion(holder.quaternion);
    const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(holder.quaternion);
    const c = this.state === 'held' ? this.pos : (this.lastRelease || this.pos).clone();
    if (follow) { c.addScaledVector(fwd, 0.22 * ease(follow)); c.y += 0.04 - 0.1 * ease(follow); }
    // which bone is the left arm: the side it sits on, in the walker's frame
    const pr = this.pose;
    if (!this.shot && this.state !== 'held' && this._tg) { pr.apply(this._tg, this._hn, this.armW, 0); return; }   // arms coming down
    const posL = new THREE.Vector3(); pr.arms[0].up.getWorldPosition(posL);
    const sL = Math.sign(holder.worldToLocal(posL.clone()).x) || 1;
    const targets = [c.clone().addScaledVector(side, sL * spread), c.clone().addScaledVector(side, -sL * spread)];
    const hints = [new THREE.Vector3(0, -1, -0.15).addScaledVector(side, sL * 0.9), new THREE.Vector3(0, -1, -0.15).addScaledVector(side, -sL * 0.9)];
    // the hands are anchored to the ball, not the other way round: shift targets when the ball is out of reach
    this._tg = targets; this._hn = hints;
    pr.apply(targets, hints, this.armW, hop);
  }

  update(dt, tAcc, active) {
    this.mesh.visible = true;
    const pl = this.player;
    if (this.pose.actor !== pl.actor) this.pose.setActor(pl.actor);
    // the arms ease in when the ball is picked up and out again after the shot
    const wantArms = this.state === 'held' || (this.shot && this.t < T_END) ? 1 : 0;
    this.armW += (wantArms - this.armW) * Math.min(1, dt * (wantArms ? 9 : 5));
    if (this.armW < 0.01 && !wantArms) this.armW = 0;
    if (this.state === 'held' || this.shot || this.armW > 0) this.carryAndPose(dt);
    if (this.shot && this.t >= T_END) {                // shot finished: the walker may move again
      this.shot = null;
      pl.cam.aim = null;
      const open = this.ui.memoryOpen || this.ui.mapOpen || !document.getElementById('pause').hidden;
      if (!open) pl.enabled = true;
    }
    if (this.state === 'held') return;
    if (!active) { this.mesh.position.copy(this.pos); return; }
    const sub = Math.ceil(dt / 0.01);
    for (let i = 0; i < sub; i++) this.step(dt / sub);
    this.mesh.position.copy(this.pos);
    // a ball left far from the court goes back to its spot once nobody is near it
    const pd = Math.hypot(pl.pos.x - this.pos.x, pl.pos.z - this.pos.z);
    if (this.state === 'ground' && this.vel.lengthSq() < 0.01) {
      this.idle += dt;
      const [lx, ly] = this.toLocal(this.pos);
      if (this.idle > 20 && pd > 15 && (Math.abs(lx) > this.court.L / 2 + 14 || Math.abs(ly) > this.court.W / 2 + 14)) {
        this.pos.copy(this.home); this.vel.set(0, 0, 0); this.idle = 0;
      }
    }
  }

  step(dt) {
    if (this.state === 'ground' && this.vel.lengthSq() < 0.0004) { this.vel.set(0, 0, 0); return; }
    const pos = this.pos, vel = this.vel;
    const prevY = pos.y;
    vel.y -= G * dt;
    pos.addScaledVector(vel, dt);
    this.mesh.rotation.x += vel.z * dt * 6; this.mesh.rotation.z -= vel.x * dt * 6;
    // ground
    const gy = this.floorAt(pos.x, pos.z, prevY + 0.3) + R;      // (from where it was: a fall through the slab's top bounces)
    if (pos.y < gy) {
      pos.y = gy;
      if (vel.y < -0.8) {
        this.onSound?.('bounce', pos, -vel.y);
        vel.y = -vel.y * 0.72; vel.x *= 0.92; vel.z *= 0.92;
        this.state = 'flying';
      } else {
        vel.y = 0; this.state = 'ground';
        const f = Math.max(0, 1 - 1.6 * dt);
        vel.x *= f; vel.z *= f;
      }
    } else if (this.state === 'ground') this.state = 'flying';
    for (const h of this.hoops) {
      // backboard: a 1.8 x 1.05 m plate in the plane x_local = const, facing the court
      const [lx, ly] = this.toLocal(pos);
      const bx = h.sg * (this.court.L / 2 - 1.2);
      const board = (lx - bx) * h.sg;                      // >0 means behind the board
      const [plx] = this.toLocal(new THREE.Vector3(pos.x - vel.x * dt, pos.y, pos.z - vel.z * dt));
      const was = (plx - bx) * h.sg;
      if (was < R && board >= R * 0 && Math.abs(ly) < 0.95 && pos.y > h.rim.y - 0.2 && pos.y < h.rim.y + 0.85 && was <= 0.06 && board > -0.0) {
        // reflect the velocity component along the court's long axis
        const vl = vel.x * this.cos + -vel.z * this.sin;
        if (vl * h.sg > 0) {
          this.onSound?.('board', pos, Math.abs(vl));
          const k = (1 + 0.55) * vl;
          vel.x -= k * this.cos; vel.z -= -k * this.sin;
          const [nx, ny] = [bx - h.sg * R * 1.2, ly];
          const w = this.toWorld(nx, ny);
          pos.x = w[0]; pos.z = -w[1];
        }
      }
      // rim: the nearest point of the ring pushes the ball away
      const dx = pos.x - h.rim.x, dz = pos.z - h.rim.z, dh = Math.hypot(dx, dz) || 1e-6;
      const rp = new THREE.Vector3(h.rim.x + dx / dh * RIM_R, h.rim.y, h.rim.z + dz / dh * RIM_R);
      const nrm = pos.clone().sub(rp);
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
      if (prevY >= h.rim.y && pos.y < h.rim.y && vel.y < 0 && dh < RIM_R - R * 0.6 && !this.scored && this.hoopShot) {
        this.scored = true;
        this.makes++;
        this.onSound?.('swish', pos, 3);
        this.ui.toast(`골인! ${this.shotFrom >= 6.25 ? '3점슛 · ' : ''}${this.makes}골 / ${this.shots}번 시도`, 3200);
      }
      if (pos.y < h.rim.y && pos.y > h.rim.y - 0.5 && dh < RIM_R) { vel.x *= 0.92; vel.z *= 0.92; vel.y *= 0.985; }   // the net slows it
    }
  }
}
