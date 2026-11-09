// 활천대 앞 생일 축하: two students stand on the flagstones south of the basin. Come up to them and one says
// 「나 오늘 생일이야!」; press E (or tap the prompt) and you and the friend say 「축하해!」, take the birthday student
// under the arms and the knees, swing them 「하나, 둘, 셋!」 and drop them in the pool, as was done on campus fountains
// on birthdays. The birthday student goes along with it (arms up all the way in), sits up in the water, climbs out
// over the wall dripping and stands where they were, wet for a while.
//
// No clip in the rig holds a person up (characters.js: idle, walk, sprint, sit, emote-yes / no, interact-right), so
// the carry is built here: the birthday student in the 'sit' clip, tipped back into a V and moved by the hips; the two
// carriers in 'idle' with both hands put under the arms / the knees by two-bone IK (armpose.js), and the carried one's
// own arms up over their head the same way.
import * as THREE from 'three';
import { play, locomotion } from './characters.js';
import { ArmPose } from './armpose.js';
import { lineTime } from './talk.js';
import { wrapAngle } from './util.js';

const BDAY = 'man-hoodie', FRIEND = 'man-grey';   // not among the heroes, so you never meet yourself
const SPOT_A = -105 * Math.PI / 180;              // where they stand: bearing from the basin's centre (campus, from east)
const SPOT_R = 5.3;                               // on the flagstones (wall's outer face 4.75, flagstones to 5.85)
const LAND_R = 2.6;                               // where the birthday student comes down in the pool
const SAY_NEAR = 6.5, OFFER_NEAR = 4.6, RESET_FAR = 16;
const G = 9.8;
const PITCH = 0.95;                               // the carried V: tipped back this far (rad) from sitting upright
const CARRY_H = 0.8;                              // hips over the flagstones while carried
const SWING_T = 0.8, SWING_A = 0.32;              // one swing (s) and how far out / in it goes (m)
const ease = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));
const height = (id) => (id.startsWith('woman') ? 1.61 : 1.73);

const _v = new THREE.Vector3(), _w = new THREE.Vector3(), _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion();
const _e = new THREE.Euler(0, 0, 0, 'YXZ'), _X = new THREE.Vector3(1, 0, 0), _Y = new THREE.Vector3(0, 1, 0), _Z = new THREE.Vector3(0, 0, 1);

// the hips' place in the holder's frame for a clip (sampled once from the model)
function sampleHips(a, clip) {
  a.mixer.stopAllAction();
  const act = a.actions[clip];
  act.reset(); act.setLoop(THREE.LoopRepeat, Infinity); act.setEffectiveWeight(1); act.play();
  a.mixer.update(0.4);
  a.holder.updateMatrixWorld(true);
  const p = a.root.getObjectByName('Hips').getWorldPosition(new THREE.Vector3());
  a.holder.worldToLocal(p);
  a.mixer.stopAllAction();
  a.current = null;
  play(a, 'idle', { fade: 0 });
  return p;
}

// --------------------------------------------------------------- droplets
// The splash: a few hundred drops thrown up and out round where the body went in, falling back to the water.
class Splash {
  constructor(scene, n = 420) {
    this.n = n;
    this.pos = new Float32Array(n * 3);
    this.col = new Float32Array(n * 4);
    this.vel = new Float32Array(n * 3);
    this.life = new Float32Array(n);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('color', new THREE.BufferAttribute(this.col, 4).setUsage(THREE.DynamicDrawUsage));
    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const x = c.getContext('2d'), grd = x.createRadialGradient(32, 32, 2, 32, 32, 30);
    grd.addColorStop(0, 'rgba(255,255,255,1)'); grd.addColorStop(0.5, 'rgba(255,255,255,0.75)'); grd.addColorStop(1, 'rgba(255,255,255,0)');
    x.fillStyle = grd; x.fillRect(0, 0, 64, 64);
    const map = new THREE.CanvasTexture(c);
    this.mat = new THREE.PointsMaterial({ size: 0.1, map, vertexColors: true, transparent: true, depthWrite: false,
      color: new THREE.Color(0.86, 0.92, 0.96).multiplyScalar(2.2) });
    this.points = new THREE.Points(g, this.mat);
    this.points.frustumCulled = false;
    this.points.visible = false;
    this.points.name = 'birthday_splash';
    scene.add(this.points);
    this.water = 0;
    this.active = 0;
  }

  // at (x, z) on the water at height y; dir: the way the body was going (xz, unit), throws the drops further that way
  burst(x, y, z, dir) {
    this.water = y;
    for (let i = 0; i < this.n; i++) {
      const a = Math.random() * Math.PI * 2, r = 0.15 + Math.random() * 0.45;
      const crown = i < this.n * 0.7;
      const out = crown ? 1.0 + Math.random() * 2.4 : 0.2 + Math.random() * 1.0;
      const up = crown ? 2.0 + Math.random() * 2.8 : 3.4 + Math.random() * 2.6;
      const vx = Math.cos(a) * out + dir.x * 0.9, vz = Math.sin(a) * out + dir.z * 0.9;
      this.pos.set([x + Math.cos(a) * r, y + 0.05, z + Math.sin(a) * r], i * 3);
      this.vel.set([vx, up, vz], i * 3);
      this.life[i] = 1;
      this.col.set([1, 1, 1, 0.9], i * 4);
    }
    this.active = this.n;
    this.points.visible = true;
  }

  update(dt) {
    if (!this.active) return;
    let live = 0;
    for (let i = 0; i < this.n; i++) {
      if (this.life[i] <= 0) continue;
      const k = i * 3;
      this.vel[k + 1] -= G * dt;
      this.vel[k] *= 1 - 0.6 * dt; this.vel[k + 2] *= 1 - 0.6 * dt;
      this.pos[k] += this.vel[k] * dt; this.pos[k + 1] += this.vel[k + 1] * dt; this.pos[k + 2] += this.vel[k + 2] * dt;
      if (this.pos[k + 1] < this.water && this.vel[k + 1] < 0) { this.life[i] = 0; this.col[i * 4 + 3] = 0; this.pos[k + 1] = -1e4; continue; }
      live++;
    }
    this.active = live;
    this.points.geometry.attributes.position.needsUpdate = true;
    this.points.geometry.attributes.color.needsUpdate = true;
    if (!live) this.points.visible = false;
  }
}

// --------------------------------------------------------------- the scene
export class Birthday {
  // F: campus.statues.fountain; water: FountainWater (or null); bubbles: talk.js Bubbles
  constructor({ scene, cast, player, F, water, bubbles, ui, shadows, blobs, mobile = false }) {
    Object.assign(this, { scene, player, F, water, bubbles, ui, mobile });
    const C = (this.C = new THREE.Vector3(F.pos[0], F.h, -F.pos[1]));
    // radial (out from the basin) and tangent (counter-clockwise round it) directions at the spot, three coordinates
    this.rad = new THREE.Vector3(Math.cos(SPOT_A), 0, -Math.sin(SPOT_A));
    this.tan = new THREE.Vector3(-Math.sin(SPOT_A), 0, -Math.cos(SPOT_A));
    this.spot = C.clone().addScaledVector(this.rad, SPOT_R);
    this.headEnd = this.spot.clone().addScaledVector(this.tan, -0.92);     // the friend, behind the birthday student
    this.feetEnd = this.spot.clone().addScaledVector(this.tan, 1.12);      // you, at their feet
    this.friendHome = this.spot.clone().addScaledVector(this.tan, -1.05).addScaledVector(this.rad, 0.15);
    this.land = C.clone().addScaledVector(this.rad, LAND_R).setY(F.h + F.water);
    this.floorY = F.h + F.floor;

    this.b = cast.make(BDAY, null);
    this.f = cast.make(FRIEND, null);
    this.hipSit = sampleHips(this.b, 'sit');
    this.hipIdle = sampleHips(this.b, 'idle');
    for (const a of [this.b, this.f]) {
      scene.add(a.holder);
      shadows?.addDynamic(a.holder);
      blobs?.addPerson(a);
      a.mixer.setTime(Math.random() * 2);
    }
    this.bTop = height(BDAY); this.fTop = height(FRIEND);
    this.anchor = new THREE.Object3D();     // over the carried student's head, for their speech bubbles
    scene.add(this.anchor);
    this.bPose = new ArmPose(this.b);
    this.fPose = new ArmPose(this.f);
    this.hPose = new ArmPose(player.actor);
    this.bones = {
      shoulders: ['UpperArmL', 'UpperArmR'].map((n) => this.b.root.getObjectByName(n)),
      knees: ['LowerLegL', 'LowerLegR'].map((n) => this.b.root.getObjectByName(n)),
      head: this.b.root.getObjectByName('Head'),
    };
    this.makeWettable();
    this.splash = new Splash(scene, mobile ? 260 : 600);
    this.state = 'idle';
    this.st = 0;                // seconds in the state
    this.said = false;          // 「나 오늘 생일이야!」 heard on this visit
    this.wet = 0;
    this.armW = 0;              // the carriers' hands on the body (0..1)
    this.armsUp = 0;
    this.reset();
  }

  // both back where they stand, dry, chatting
  reset() {
    this.state = 'idle'; this.st = 0; this.said = false;
    this.setWet(0);
    this.place(this.b, this.spot, this.headingTo(this.spot, this.friendHome));
    this.place(this.f, this.friendHome, this.headingTo(this.friendHome, this.spot));
    this.b.holder.quaternion.setFromAxisAngle(_Y, this.b.holder.rotation.y);
    play(this.b, 'idle', { fade: 0 });
    play(this.f, 'idle', { fade: 0 });
    this.armW = 0; this.armsUp = 0;
  }

  place(a, p, heading) {
    a.holder.position.copy(p);
    a.heading = heading;
    a.holder.rotation.set(0, heading, 0);
  }

  headingTo(from, to) { return Math.atan2(to.x - from.x, to.z - from.z); }

  // turn a standing person towards a heading, smoothly
  turn(a, want, dt, rate = 6) {
    a.heading = (a.heading ?? a.holder.rotation.y) + wrapAngle(want - (a.heading ?? a.holder.rotation.y)) * (1 - Math.exp(-dt * rate));
    a.holder.rotation.set(0, a.heading, 0);
  }

  // walk towards p (flat), turning to face the way; true when there (within 4 cm)
  walk(a, p, dt, speed = 1.25) {
    const h = a.holder.position, dx = p.x - h.x, dz = p.z - h.z, d = Math.hypot(dx, dz);
    if (d < 0.04) { locomotion(a, 0); return true; }
    const want = Math.atan2(dx, dz);
    this.turn(a, want, dt, 9);
    const s = Math.min(speed, d / dt);
    const go = Math.max(0, Math.cos(wrapAngle(want - a.heading)));      // turn first, then step
    h.x += Math.sin(a.heading) * s * go * dt;
    h.z += Math.cos(a.heading) * s * go * dt;
    locomotion(a, s * go > 0.05 ? Math.max(0.6, s * go) : 0);
    return false;
  }

  // the carried student's clothes go dark and a little glossy when wet: their own copy of the merged mesh's colours
  makeWettable() {
    this.b.root.traverse((o) => {
      if (!o.isSkinnedMesh || this.mesh) return;
      o.geometry = o.geometry.clone();
      this.mesh = o;
    });
    if (!this.mesh) return;
    const g = this.mesh.geometry, c = g.attributes.color.array, r = g.attributes.rough?.array;
    this.col0 = Float32Array.from(c);
    this.rough0 = r ? Float32Array.from(r) : null;
    // skin stays (warm, light); the rest (clothes, shoes, hair) darkens
    this.wetK = new Float32Array(c.length / 3);
    for (let i = 0; i < this.wetK.length; i++) {
      const R = c[i * 3], Gg = c[i * 3 + 1], B = c[i * 3 + 2];
      const skin = R > 0.25 && R > Gg * 1.2 && Gg > B * 1.15 && R - B > 0.12;
      this.wetK[i] = skin ? 0.08 : 1;
    }
  }

  setWet(w) {
    this.wet = w;
    if (!this.mesh) return;
    const g = this.mesh.geometry, c = g.attributes.color.array, r = g.attributes.rough?.array;
    for (let i = 0; i < this.wetK.length; i++) {
      const k = 1 - 0.45 * w * this.wetK[i];
      c[i * 3] = this.col0[i * 3] * k; c[i * 3 + 1] = this.col0[i * 3 + 1] * k; c[i * 3 + 2] = this.col0[i * 3 + 2] * k;
      if (r) r[i] = this.rough0[i] - (this.rough0[i] - 0.4) * w * this.wetK[i];
    }
    g.attributes.color.needsUpdate = true;
    if (r) g.attributes.rough.needsUpdate = true;
  }

  // circles the walker collides with (appended to out)
  movers(px, py, out) {
    if (Math.abs(this.spot.x - px) > 10 || Math.abs(-this.spot.z - py) > 10) return out;
    for (const a of [this.b, this.f]) {
      if (this.state !== 'idle' && this.state !== 'rest') continue;
      const c = (a.circle ||= { x: 0, y: 0, r: 0.3 });
      c.x = a.holder.position.x; c.y = -a.holder.position.z;
      out.push(c);
    }
    return out;
  }

  distTo(p) { const q = this.player.pos; return Math.hypot(q.x - p.x, q.z - p.z); }

  // text for the E prompt
  prompt() {
    if (this.state !== 'idle' || !this.said || this.distTo(this.b.holder.position) > OFFER_NEAR) return null;
    return `${this.mobile ? '눌러서 ' : ''}생일 축하해 주기`;
  }

  // E / tap: start the celebration (true when it did)
  action() {
    if (!this.prompt()) return false;
    this.go('gather');
    const pl = this.player;
    pl.scripted = true;
    pl.enabled = false;
    pl.keys.clear();
    this.hero = pl.actor;
    this.hTop = height(this.hero.id);
    if (this.hPose.actor !== this.hero) this.hPose.setActor(this.hero);
    this.hero.heading = pl.heading;
    // the camera stands back on the lawn, side on to the carry: you and the friend left and right, the pool beyond
    if (!this.noCamera) {
      this.camPos = this.spot.clone().addScaledVector(this.rad, 4.2).addScaledVector(this.tan, 0.6).setY(this.F.h + 1.7);
      this.camLook = this.spot.clone().addScaledVector(this.rad, -1.1).setY(this.F.h + 0.75);
      pl.camOverride = { pos: this.camPos, look: this.camLook };
    }
    const t = this.t;
    this.say(this.hero.holder, this.hTop, '축하해!', t + 0.1);
    this.say(this.f.holder, this.fTop, '축하해!', t + 0.1);
    return true;
  }

  go(state) { this.state = state; this.st = 0; }

  say(holder, top, text, from, dur = lineTime(text)) { this.bubbles?.add(holder, top, text, from, from + dur); }

  // the carried student's hips are at `hips` (world), tipped back `pitch` from upright, facing `yaw`, rolled `roll`
  // (about their own forward axis); `hip` is where the hips sit in the holder's frame for the clip playing
  carry(hips, yaw, pitch, roll, hip) {
    const h = this.b.holder;
    _q.setFromAxisAngle(_Y, yaw);
    _q2.setFromAxisAngle(_Z, roll); _q.multiply(_q2);
    _q2.setFromAxisAngle(_X, -pitch); _q.multiply(_q2);
    h.quaternion.copy(_q);
    h.position.copy(hip).applyQuaternion(_q).negate().add(hips);
  }

  // active: walking (not the title card or the bird's-eye view); focus: what the view centres on (main.js)
  update(dt, t, active, focus = this.player.pos) {
    this.t = t;
    const pl = this.player, b = this.b, f = this.f, F = this.F;
    const far = this.distTo(this.spot);
    this.splash.update(dt);
    if (this.wet > 0 && (this.state === 'rest' || this.state === 'idle')) this.setWet(Math.max(0, this.wet - dt / 90));
    // far from the view: out of the scene, nothing to do (the mixers rest too)
    const visible = Math.hypot(focus.x - this.spot.x, focus.z - this.spot.z) < 190;
    for (const a of [b, f]) {
      if (visible && !a.holder.parent) this.scene.add(a.holder);
      else if (!visible && a.holder.parent) this.scene.remove(a.holder);
    }
    if (!visible && this.state === 'idle') return;
    if (pl.scripted && this.state !== 'idle' && this.state !== 'rest' && (far > 12 || pl.actor !== this.hero)) { this.abort(); return; }
    this.st += dt;
    const s = this.st;
    const tanYaw = Math.atan2(this.tan.x, this.tan.z);

    switch (this.state) {
      case 'idle': {
        // chatting; turn to you as you come up, and tell you
        const near = active && far < SAY_NEAR;
        this.turn(b, near ? this.headingTo(b.holder.position, pl.pos) : this.headingTo(b.holder.position, f.holder.position), dt);
        this.turn(f, near ? this.headingTo(f.holder.position, pl.pos) : this.headingTo(f.holder.position, b.holder.position), dt);
        if (near && !this.said) {
          this.said = true;
          this.say(b.holder, this.bTop, '나 오늘 생일이야!', t + 0.3);
          this.cue = { at: t + 0.3, a: b };
        }
        if (!active || far > RESET_FAR) this.said = false;
        break;
      }
      case 'gather': {
        // you and the friend take your places at their feet and behind them; they turn round, puzzled
        const hDone = this.walk(this.hero, this.feetEnd, dt, 1.4);
        if (hDone) this.turn(this.hero, tanYaw + Math.PI, dt, 8);
        const fDone = this.walk(f, this.headEnd, dt, 1.0);
        if (fDone) this.turn(f, tanYaw, dt, 8);
        this.turn(b, tanYaw, dt, 4);
        const ready = hDone && fDone && Math.abs(wrapAngle(this.hero.heading - tanYaw - Math.PI)) < 0.1 && Math.abs(wrapAngle(f.heading - tanYaw)) < 0.1;
        if (ready && s > 2.2) {
          this.go('lift');
          play(b, 'sit', { fade: 0.45 });
          this.say(this.anchor, this.bTop, '살살 던져~!', t + 0.4, 1.4);
          this.yaw0 = b.heading;
        }
        break;
      }
      case 'lift': {
        // hands under the arms and the knees, then up: the student folds into the V and tips back
        const u = ease((s - 0.25) / 0.85);
        const hips = _v.copy(this.spot).setY(F.h + this.hipIdle.y + (CARRY_H - this.hipIdle.y) * u);
        const hip = _w.copy(this.hipIdle).lerp(this.hipSit, ease(s / 0.45));
        this.carry(hips, this.yaw0 + wrapAngle(tanYaw - this.yaw0) * ease(s / 0.3), PITCH * u, 0, hip);
        this.armsUp = Math.min(1, s / 0.6);
        if (s > 1.6) { this.go('swing'); this.counted = 0; this.sway = 0; }
        break;
      }
      case 'swing': {
        // 하나, 둘, 셋: out and in over the wall, higher each time; let go on the third swing in
        const w = 2 * Math.PI / SWING_T, amp = SWING_A * (0.7 + 0.3 * Math.min(1, s / (2 * SWING_T)));
        const x = -amp * Math.sin(w * s);                         // + towards the pool: back first
        const hips = _v.copy(this.spot).addScaledVector(this.rad, -x).setY(F.h + CARRY_H + 0.9 * x * x + 0.04 * s);
        this.carry(hips, tanYaw, PITCH, -0.25 * x, this.hipSit);
        const peaks = [0.75, 1.75, 2.5];                         // 「하나」「둘」 at the swings in, 「셋」 as they let go
        if (this.counted < 3 && s >= peaks[this.counted] * SWING_T - 0.12) {
          const word = ['하나!', '둘!', '셋!'][this.counted];
          this.say(f.holder, this.fTop, word, t, 0.75);
          this.say(this.hero.holder, this.hTop, word, t, 0.75);
          this.counted++;
        }
        this.sway = x;
        if (s >= 2.5 * SWING_T) {
          // the throw: from here to the landing spot in TF seconds
          const TF = 0.85;
          this.p0 = hips.clone();
          this.v0 = new THREE.Vector3((this.land.x - hips.x) / TF, (this.land.y + 0.12 - hips.y + 0.5 * G * TF * TF) / TF, (this.land.z - hips.z) / TF);
          this.go('fly');
          this.releaseHands();
        }
        break;
      }
      case 'fly': {
        const hips = _v.copy(this.p0).addScaledVector(this.v0, s);
        hips.y -= 0.5 * G * s * s;
        const u = ease(s / 0.7);
        this.carry(hips, tanYaw + 0.35 * u, PITCH + 0.55 * u, -0.25 * SWING_A + 0.5 * u, this.hipSit);
        this.armsUp = 1;
        if (hips.y <= this.land.y + 0.12) {
          this.go('water');
          this.hit = hips.clone();
          const dir = this.v0.clone().setY(0).normalize();
          this.splash.burst(hips.x, this.land.y, hips.z, dir);
          this.water?.splash(hips.x, hips.z, 0.06, 0.5);
          this.setWet(1);
          this.say(this.anchor, this.bTop, '아~ 시원하다!', t + 0.55);
          this.say(f.holder, this.fTop, '생일 축하해~!', t + 1.5);
          this.say(this.hero.holder, this.hTop, '생일 축하해~!', t + 1.5);
          this.cue = { at: t + 1.5, a: f };
          this.cue2 = { at: t + 1.6, a: this.hero };
        }
        break;
      }
      case 'water': {
        // down onto the pool's floor, then sitting up facing the two of you
        const sink = ease(s / 0.3), up = ease((s - 0.25) / 0.8);
        const hips = _v.copy(this.hit).setY(this.land.y + 0.12 + (this.floorY + this.hipSit.y * 0.4 - this.land.y - 0.12) * sink);
        const out = Math.atan2(this.rad.x, this.rad.z);
        const yaw = tanYaw + 0.35 + wrapAngle(out - tanYaw - 0.35) * up;
        this.carry(hips, yaw, (PITCH + 0.55) * (1 - up) + 0.12 * up, 0.25 * (1 - up), this.hipSit);
        this.armsUp = Math.max(0, 1 - s / 0.9);
        if (s > 3.4) {
          this.go('stand');
          play(b, 'idle', { fade: 0.6 });
          this.from = { hips: hips.clone(), yaw };
        }
        break;
      }
      case 'stand': {
        const u = ease(s / 0.7);
        const hips = _v.copy(this.from.hips).setY(this.from.hips.y + (this.floorY + this.hipIdle.y - this.from.hips.y) * u);
        const hip = _w.copy(this.hipSit).lerp(this.hipIdle, ease(s / 0.6));
        this.carry(hips, this.from.yaw, 0.12 * (1 - u), 0, hip);
        if (s > 0.75) {
          this.go('wade');
          b.heading = this.from.yaw;
          b.holder.quaternion.setFromAxisAngle(_Y, b.heading);
          b.holder.position.set(hips.x - this.hipIdle.x, this.floorY, hips.z - this.hipIdle.z);
          const r = this.C.clone().setY(0), p = b.holder.position.clone().setY(0);
          this.wadeTo = this.C.clone().addScaledVector(p.sub(r).normalize(), F.r - 0.3).setY(this.floorY);
        }
        break;
      }
      case 'wade': {
        b.holder.position.y = this.floorY;
        if (this.walk(b, this.wadeTo, dt, 0.9)) {
          this.go('climb');
          this.climbFrom = b.holder.position.clone();
          const d = this.climbFrom.clone().sub(this.C).setY(0).normalize();
          this.climbTo = this.C.clone().addScaledVector(d, this.F.rim + 0.45).setY(F.h);
        }
        break;
      }
      case 'climb': {
        // a step up onto the wall and down onto the flagstones
        const u = ease(s / 0.9);
        b.holder.position.lerpVectors(this.climbFrom, this.climbTo, u);
        b.holder.position.y += Math.sin(Math.PI * Math.min(1, s / 0.9)) * 0.42;
        locomotion(b, 0.7);
        if (s > 0.9) {
          this.go('back');
          this.say(b.holder, this.bTop, '고마워!', t + 0.6);
        }
        break;
      }
      case 'back': {
        const there = this.walk(b, this.spot, dt, 1.1);
        b.holder.position.y = F.h;
        if (there) this.turn(b, this.headingTo(b.holder.position, this.hero.holder.position), dt, 6);
        if (there && s > 2.4) this.finish();
        break;
      }
      case 'rest': {
        // back to chatting once you have gone (and come back another time)
        this.turn(b, this.headingTo(b.holder.position, f.holder.position), dt, 3);
        this.turn(f, this.headingTo(f.holder.position, b.holder.position), dt, 3);
        if (!active || far > RESET_FAR) { this.state = 'idle'; this.said = false; }
        break;
      }
    }

    // the carriers: in place, swaying with the swing, hands on the body while it is held
    const holding = this.state === 'lift' || this.state === 'swing';
    if (this.state === 'lift' || this.state === 'swing' || this.state === 'fly') {
      const x = this.state === 'swing' ? this.sway : this.state === 'lift' ? 0 : -SWING_A * 0.3;
      this.place(f, _w.copy(this.headEnd).addScaledVector(this.rad, x * 0.3), tanYaw);
      this.place(this.hero, _w.copy(this.feetEnd).addScaledVector(this.rad, x * 0.3), tanYaw + Math.PI);
      locomotion(f, 0); locomotion(this.hero, 0);
    }
    if (this.state === 'water' && s > 0.4) {
      // turn to watch the pool
      this.turn(f, this.headingTo(f.holder.position, b.holder.position), dt, 3);
      this.turn(this.hero, this.headingTo(this.hero.holder.position, b.holder.position), dt, 3);
    }
    const wantArms = holding ? (this.state === 'lift' ? ease(s / 0.3) : 1) : 0;
    this.armW += (wantArms - this.armW) * Math.min(1, dt * (wantArms > this.armW ? 14 : 4));

    // animate (the walker's own mixer too while the scene has it), then the arms on top
    if (visible) { b.mixer.update(dt); f.mixer.update(dt); }
    if (pl.scripted && this.hero) {
      pl.heading = this.hero.heading ?? pl.heading;
      this.hero.mixer.update(dt);
    }
    for (const c of ['cue', 'cue2']) {
      const q = this[c];
      if (q && t >= q.at) { play(q.a, 'emote-yes', { once: true, fade: 0.25 }); this[c] = null; }
    }
    b.holder.updateMatrixWorld(true);
    if (this.armsUp > 0.01) this.cheerArms(t);
    if (this.armW > 0.01 || this.state === 'fly') {
      if (holding) this.grip();
      this.fPose.apply(this.fT, this.fH, this.armW);
      if (this.hero) this.hPose.apply(this.hT, this.hH, this.armW);
    }
    // the bubble anchor: over the head
    const head = this.bones.head.getWorldPosition(_v);
    this.anchor.position.set(head.x, head.y + 0.2 - this.bTop, head.z);
  }

  // hand targets on the carried body: under the arms for the friend, under the knees for you
  grip() {
    const b = this.b;
    const down = _w.set(0, -1, 0).applyQuaternion(b.holder.quaternion);
    const pts = (bones, drop) => bones.map((bn) => bn.getWorldPosition(new THREE.Vector3()).addScaledVector(down, drop));
    this.fT = this.match(this.f, this.fPose, pts(this.bones.shoulders, 0.1));
    this.hT = this.match(this.hero, this.hPose, pts(this.bones.knees, 0.07));
    this.fH = this.hints(this.f, this.fPose);
    this.hH = this.hints(this.hero, this.hPose);
  }

  // the two targets in the order of the carrier's arms (L, R), by the side of the body each is on
  match(a, pose, two) {
    a.holder.updateMatrixWorld(true);
    const side = (p) => Math.sign(a.holder.worldToLocal(p.clone()).x) || 1;
    const sL = side(pose.arms[0].up.getWorldPosition(new THREE.Vector3()));
    const [p, q] = two;
    // hands, not wrists, on the body: the wrist stops 7 cm short, towards the carrier
    const pull = (v) => v.addScaledVector(_v.copy(a.holder.position).setY(v.y).sub(v).normalize(), 0.07);
    return side(p) === sL ? [pull(p), pull(q)] : [pull(q), pull(p)];
  }

  hints(a, pose) {
    const sideW = new THREE.Vector3(1, 0, 0).applyQuaternion(a.holder.quaternion);
    const sL = Math.sign(a.holder.worldToLocal(pose.arms[0].up.getWorldPosition(new THREE.Vector3())).x) || 1;
    return [new THREE.Vector3(0, -1, -0.2).addScaledVector(sideW, sL * 0.9), new THREE.Vector3(0, -1, -0.2).addScaledVector(sideW, -sL * 0.9)];
  }

  // let go: the hands follow through towards the pool as the arms come down
  releaseHands() {
    const push = this.rad.clone().multiplyScalar(-0.25).setY(0.12);
    this.fT = this.fT.map((p) => p.clone().add(push));
    this.hT = this.hT.map((p) => p.clone().add(push));
  }

  // the carried student's arms up over their head, as on a ride, swaying a little (in their own frame)
  cheerArms(t) {
    const pose = this.bPose, h = this.b.holder;
    if (!pose.ok) return;
    const sL = Math.sign(h.worldToLocal(pose.arms[0].up.getWorldPosition(new THREE.Vector3())).x) || 1;
    const T = [], H = [];
    for (let i = 0; i < 2; i++) {
      const sg = i ? -sL : sL, ph = i * 1.9;
      const sh = h.worldToLocal(pose.arms[i].up.getWorldPosition(new THREE.Vector3()));
      const loc = sh.add(new THREE.Vector3(sg * (0.2 + 0.05 * Math.sin(t * 5 + ph)), 0.5 + 0.04 * Math.sin(t * 6.3 + ph), 0.12 + 0.06 * Math.cos(t * 4.1 + ph)));
      T.push(h.localToWorld(loc));
      H.push(new THREE.Vector3(sg, 0, -0.5).applyQuaternion(h.quaternion));
    }
    pose.apply(T, H, this.armsUp);
  }

  finish() {
    this.go('rest');
    const pl = this.player;
    pl.scripted = false;
    pl.camOverride = null;
    pl.speed = 0;
    pl.heading = this.hero.heading;
    pl.pos.y = this.F.h;
    const open = this.ui?.memoryOpen || this.ui?.mapOpen || !document.getElementById('pause')?.hidden;
    if (!open) pl.enabled = true;
    play(this.hero, 'idle', { fade: 0.3 });
  }

  // the walker taken elsewhere mid-scene (the map, a memory spot): let go of them and start over
  abort() {
    const pl = this.player;
    pl.scripted = false;
    pl.camOverride = null;
    play(pl.actor, 'idle', { fade: 0 });
    this.reset();
  }
}
