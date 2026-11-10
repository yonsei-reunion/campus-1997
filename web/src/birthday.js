// 활천대 앞 생일 축하: two students stand on the flagstones south of the basin. Come up to them and one says
// 「나 오늘 생일이야!」; press E (or tap the prompt) and you and the friend say 「축하해!」, take the birthday student
// by the raised wrists and by the ankles, swing them 「하나, 둘, 셋!」 and drop them in the pool, as was done on
// campus fountains on birthdays. The birthday student goes along with it (arms up all the way in), sits up in the
// water, climbs out over the wall dripping and stands where they were, wet for a while.
//
// No clip in the rig holds a person up or bends down (characters.js: idle, walk, sprint, sit, emote-yes / no,
// interact-right), so the carry is built here over 'idle':
// - the birthday student: the body placed by the hips and tipped back, the legs bent by two-bone IK to where the soles
//   should be (on the flagstones until you have the ankles, then up with your hands), the arms up to the friend's hands
// - the two carriers: hands by two-bone IK (armpose.js ArmPose) on the wrists / the ankles, and the body brought to
//   where the hands reach on planted feet (armpose.js Stance: squat, lean, sway). The rig's arms are short (0.39 m
//   shoulder to wrist), so you squat right down for the ankles and stand up with them, while the friend, holding the
//   wrists, steps back as the body is laid over; in the swing both sway from the hips, the feet where they are.
// - the throw: the last swing is a heave that ends at the speed the body flies off with, so nothing jumps at letting go
import * as THREE from 'three';
import { play, locomotion } from './characters.js';
import { ArmPose, Stance, Hands, aimAxis, twoBone } from './armpose.js';
import { lineTime } from './talk.js';
import { wrapAngle } from './util.js';

const BDAY = 'man-hoodie', FRIEND = 'man-grey';   // not among the heroes, so you never meet yourself
const SPOT_A = -105 * Math.PI / 180;              // where they stand: bearing from the basin's centre (campus, from east)
const SPOT_R = 5.3;                               // on the flagstones (wall's outer face 4.75, flagstones to 5.85)
const LAND_R = 2.6;                               // where the birthday student comes down in the pool
const SAY_NEAR = 6.5, OFFER_NEAR = 4.6, RESET_FAR = 16;
const G = 9.8;
const PITCH = 1.13;                               // carried: tipped back this far (rad) from upright
const CARRY_H = 0.55;                             // hips over the flagstones while carried (they sag between the hands)
const LEG_OUT = 0.73, LEG_UP = 0.28;              // carried: the soles from the hips, towards the feet's end and up
const HERO_AT = 0.8, FRIEND_AT = -0.48;          // where you squat for the ankles / the friend takes the wrists (m along
                                                  // the line of the carry from where the birthday student stands)
const CARRY_AT = HERO_AT - 0.97;                  // the hips there once carried: your hands just reach the ankles
const PALM = 0.08;                                // wrist to the middle of the palm
const TAKE_T = 1.0, LIFT_T = 1.5;                 // taking hold (s), laying over and lifting (s)
const SWING_T = 0.8, SWING_A = 0.32;              // one swing (s) and how far out / in it goes (m)
const HEAVE_T = 0.42, HEAVE_X = 0.38, HEAVE_Y = 0.42;   // the last swing in: how long, and where they let go (in, up)
const FLY_T = 0.8;                                // in the air (s)
const REST = { drop: 0, lean: 0, side: 0, sway: 0, fwd: 0 };
const ease = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));
const height = (id) => (id.startsWith('woman') ? 1.61 : 1.73);

const _v = new THREE.Vector3(), _w = new THREE.Vector3(), _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion();
const _X = new THREE.Vector3(1, 0, 0), _Y = new THREE.Vector3(0, 1, 0), _Z = new THREE.Vector3(0, 0, 1);

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

// a carrier's reach in 'idle' (world metres): shoulder to palm, half the shoulders' width, the shoulders' height over
// the feet and how far forward of them, and the spine (hips to shoulders)
function reachOf(a) {
  a.holder.updateMatrixWorld(true);
  const p = (n) => a.root.getObjectByName(n).getWorldPosition(new THREE.Vector3());
  const s = p('UpperArmL'), e = p('LowerArmL'), w = p('WristL'), s2 = p('UpperArmR');
  const mid = s.clone().add(s2).multiplyScalar(0.5).sub(a.holder.position);
  const fwd = mid.x * Math.sin(a.holder.rotation.y) + mid.z * Math.cos(a.holder.rotation.y);
  return { arm: s.distanceTo(e) + e.distanceTo(w) + PALM, half: s.distanceTo(s2) / 2, h: mid.y, fwd,
    spine: mid.y + a.holder.position.y - p('Hips').y };
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
    // where the friend (behind the birthday student) and you (at their feet) take hold, and where the hips are once
    // they are carried; they come down in the pool straight in from there
    this.headEnd = this.spot.clone().addScaledVector(this.tan, FRIEND_AT);
    this.feetEnd = this.spot.clone().addScaledVector(this.tan, HERO_AT);
    this.mid = this.spot.clone().addScaledVector(this.tan, CARRY_AT);
    this.friendHome = this.spot.clone().addScaledVector(this.tan, -1.05).addScaledVector(this.rad, 0.15);
    this.land = C.clone().addScaledVector(this.rad, LAND_R).addScaledVector(this.tan, CARRY_AT).setY(F.h + F.water);
    this.floorY = F.h + F.floor;

    this.b = cast.make(BDAY, null);
    this.f = cast.make(FRIEND, null);
    this.hipSit = sampleHips(this.b, 'sit');
    this.hipIdle = sampleHips(this.b, 'idle');
    this.bones = {
      knees: ['LowerLegL', 'LowerLegR'].map((n) => this.b.root.getObjectByName(n)),
      feet: ['FootL', 'FootR'].map((n) => this.b.root.getObjectByName(n)),
      wrists: ['WristL', 'WristR'].map((n) => this.b.root.getObjectByName(n)),
      thighs: ['UpperLegL', 'UpperLegR'].map((n) => this.b.root.getObjectByName(n)),
      head: this.b.root.getObjectByName('Head'),
    };
    // the feet's rest pose (sampleHips has left the model in it): no clip drives their rotation while sitting or
    // standing, so what legsTo gives them would stay (and be saved by the mixer as their rest when a walk starts);
    // they go back to it every frame. And where each foot sits on its shin at rest (offset and turn in the shin's
    // frame), for legsTo to carry it along
    this.footRest = this.bones.feet.map((x) => ({ p: x.position.clone(), q: x.quaternion.clone() }));
    this.b.holder.updateMatrixWorld(true);
    this.footOnShin = [0, 1].map((i) => {
      const knee = this.bones.knees[i], foot = this.bones.feet[i];
      const kq = knee.getWorldQuaternion(new THREE.Quaternion()).invert();
      const off = foot.getWorldPosition(new THREE.Vector3()).sub(knee.getWorldPosition(new THREE.Vector3()));
      return { off: off.applyQuaternion(kq), rel: kq.clone().multiply(foot.getWorldQuaternion(new THREE.Quaternion())) };
    });
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
    this.fR = reachOf(this.f);
    this.hPose = new ArmPose(player.actor);
    const shin = this.footOnShin.map((x) => x.off);
    this.kneeAxis = this.bones.knees.map((k) => k.position.clone().normalize());
    this.legSide = this.bones.thighs.map((x) => Math.sign(this.b.holder.worldToLocal(x.getWorldPosition(new THREE.Vector3())).x) || 1);
    this.fStance = new Stance(this.f, shin);
    this.hStance = new Stance(player.actor, shin);
    this.fSt = { ...REST }; this.hSt = { ...REST };
    this.bHands = new Hands(this.b);
    this.fHands = new Hands(this.f);
    this.hHands = new Hands(player.actor);
    this.elbows = ['LowerArmL', 'LowerArmR'].map((n) => this.b.root.getObjectByName(n));
    this.makeWettable();
    this.splash = new Splash(scene, mobile ? 260 : 600);
    this.state = 'idle';
    this.st = 0;                // seconds in the state
    this.said = false;          // 「나 오늘 생일이야!」 heard on this visit
    this.wet = 0;
    this.fW = this.hW = 0;      // the friend's / your hands on the body (0..1)
    this.armsUp = 0;
    this.legW = 0;              // the birthday student's legs: ours (1) or the clip's (0)
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
    this.fW = this.hW = 0; this.armsUp = 0; this.legW = 0;
    this.fT = this.hT = null;
    this.p0 = null;
    Object.assign(this.fSt, REST); Object.assign(this.hSt, REST);
    this.fStance.apply(); this.hStance.apply();
    this.bHands.grip(null, 0); this.fHands.grip(null, 0); this.hHands.grip(null, 0);
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
    if (this.hPose.actor !== this.hero) { this.hHands.grip(null, 0); this.hPose.setActor(this.hero); this.hStance.setActor(this.hero); this.hHands.setActor(this.hero); }
    this.hR = reachOf(this.hero);
    this.hero.heading = pl.heading;
    // the camera stands back on the lawn, side on to the carry: you and the friend left and right, the pool beyond
    if (!this.noCamera) {
      this.camPos = this.mid.clone().addScaledVector(this.rad, 4.2).addScaledVector(this.tan, 0.6).setY(this.F.h + 1.7);
      this.camLook = this.mid.clone().addScaledVector(this.rad, -1.1).setY(this.F.h + 0.75);
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
    this.bones.feet.forEach((x, i) => { x.position.copy(this.footRest[i].p); x.quaternion.copy(this.footRest[i].q); });
    if (pl.scripted && this.state !== 'idle' && this.state !== 'rest' && (far > 12 || pl.actor !== this.hero)) { this.abort(); return; }
    this.st += dt;
    let s = this.st;
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
          this.go('take');
          this.say(this.anchor, this.bTop, '살살 던져~!', t + 0.4, 1.4);
          this.yaw0 = b.heading;
          b.holder.updateMatrixWorld(true);
          this.stand = this.bones.feet.map((x) => x.getWorldPosition(new THREE.Vector3()));
          this.hips0 = this.hipIdle.clone().applyAxisAngle(_Y, tanYaw).add(this.spot);
          this.hips1 = this.mid.clone().setY(F.h + CARRY_H);
          this.hR = reachOf(this.hero);
        }
        break;
      }
      case 'take': {
        // their arms go up and back to the friend's hands; you squat down to their ankles
        this.pose(this.hips0, this.yaw0 + wrapAngle(tanYaw - this.yaw0) * ease(s / 0.3), 0, 0, 0);
        this.armsUp = ease(s / 0.5);
        this.legW = ease(s / 0.3);
        this.fW = ease((s - 0.25) / 0.45);
        this.hW = ease((s - 0.4) / 0.5);
        if (s > TAKE_T) this.go('lift');
        break;
      }
      case 'lift': {
        // laid over backwards as you stand up with the ankles: the hips sink between the two pairs of hands, and the
        // friend steps back with the wrists
        const u = ease(s / LIFT_T);
        this.pose(_v.copy(this.hips0).lerp(this.hips1, u), tanYaw, PITCH * u, 0, ease(s / (LIFT_T - 0.15)));
        if (s > LIFT_T + 0.25) { this.go('swing'); this.counted = 0; }
        break;
      }
      case 'swing': {
        // 하나, 둘, 셋: out and in over the wall; from the third swing out, a heave in and up that ends at the
        // speed they fly off with
        const w = 2 * Math.PI / SWING_T, tH = 2.25 * SWING_T;
        const at = (x, up) => new THREE.Vector3().copy(this.mid).addScaledVector(this.rad, -x).setY(F.h + CARRY_H + up);
        let hips, roll;
        if (s < tH) {
          const amp = SWING_A * (0.7 + 0.3 * Math.min(1, s / (2 * SWING_T)));
          const x = -amp * Math.sin(w * s);                       // + towards the pool: back first
          hips = at(x, 0.9 * x * x + 0.04 * s);
          roll = -0.25 * x;
          this.dip = 0.05 * (1 - (x / SWING_A) ** 2);           // knees give as the weight comes through the bottom
        } else {
          if (!this.p0) {
            this.pB = at(-SWING_A, 0.9 * SWING_A * SWING_A + 0.04 * tH);
            this.p0 = at(HEAVE_X, HEAVE_Y);
            this.v0 = new THREE.Vector3((this.land.x - this.p0.x) / FLY_T,
              (this.land.y + 0.12 - this.p0.y + 0.5 * G * FLY_T * FLY_T) / FLY_T, (this.land.z - this.p0.z) / FLY_T);
          }
          const k = Math.min(1, (s - tH) / HEAVE_T), k2 = k * k, k3 = k2 * k;
          hips = this.pB.clone().multiplyScalar(2 * k3 - 3 * k2 + 1).addScaledVector(this.p0, 3 * k2 - 2 * k3)
            .addScaledVector(this.v0, (k3 - k2) * HEAVE_T);
          roll = 0.25 * SWING_A + (-0.25 * HEAVE_X - 0.25 * SWING_A) * ease(k);
          this.dip = 0.1 * Math.sin(Math.PI * Math.min(1, k * 1.6)) * (1 - k);   // down into the heave, up with it
        }
        this.pose(hips, tanYaw, PITCH, roll, 1);
        const peaks = [0.75 * SWING_T, 1.75 * SWING_T, tH + HEAVE_T];   // 「하나」「둘」 at the swings in, 「셋」 as they let go
        if (this.counted < 3 && s >= peaks[this.counted] - 0.12) {
          const word = ['하나!', '둘!', '셋!'][this.counted];
          this.say(f.holder, this.fTop, word, t, 0.75);
          this.say(this.hero.holder, this.hTop, word, t, 0.75);
          this.counted++;
        }
        if (s >= tH + HEAVE_T) {
          this.go('fly');
          this.releaseHands();
        }
        break;
      }
      case 'fly': {
        const hips = _v.copy(this.p0).addScaledVector(this.v0, s);
        hips.y -= 0.5 * G * s * s;
        const u = ease(s / 0.7);
        this.pose(hips, tanYaw + 0.35 * u, PITCH + 0.55 * u, -0.25 * HEAVE_X + 0.5 * u, 1);
        this.armsUp = 1;
        if (hips.y <= this.land.y + 0.12) {
          this.go('water');
          this.p0 = null;
          play(b, 'sit', { fade: 0.25 });
          this.hit = hips.clone();
          const dir = this.v0.clone().setY(0).normalize();
          this.splash.burst(hips.x, this.land.y, hips.z, dir);
          this.onSplash?.(hips);        // (audio.js)
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
        // (the legs go from ours to the 'sit' clip's under the splash)
        this.pose(hips, yaw, (PITCH + 0.55) * (1 - up) + 0.12 * up, 0.25 * (1 - up), 1, _w.copy(this.hipIdle).lerp(this.hipSit, Math.min(1, s / 0.25)));
        this.legW = 1 - ease(s / 0.25);
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

    const st = this.state, holding = st === 'take' || st === 'lift' || st === 'swing';
    s = this.st;                // (the state may have just changed)
    if (st === 'water' && s > 0.4) {
      // turn to watch the pool
      this.turn(f, this.headingTo(f.holder.position, b.holder.position), dt, 3);
      this.turn(this.hero, this.headingTo(this.hero.holder.position, b.holder.position), dt, 3);
    }
    if (!holding) {
      // let go: the arms come down
      const k = Math.min(1, dt * 4);
      this.fW -= this.fW * k; this.hW -= this.hW * k;
    }
    // the friend backs away with the wrists as the body is laid over (before the mixers: it sets the walk)
    if (st === 'lift') this.backWith(f, dt);
    else if (holding) locomotion(f, 0);
    if (holding) locomotion(this.hero, 0);

    // animate (the walker's own mixer too while the scene has it), then our poses on top
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
    if (this.legW > 0.001) this.legsTo();
    if (this.armsUp > 0.01) this.cheerArms(t, holding);
    // the carriers: bodies to where the hands reach on planted feet, then the hands round the wrists / the ankles
    const raw = holding ? this.grips() : null;
    const a = 1 - Math.exp(-dt * (holding ? 30 : 5));
    const settle = (cur, want) => { for (const k in cur) cur[k] += (want[k] - cur[k]) * a; };
    settle(this.fSt, !holding ? REST : st === 'lift' ? { ...REST, lean: this.leanFor(raw.f[0].p.y - f.holder.position.y) } : this.crouchTo(f, this.fR, raw.f.map((g) => g.p), st === 'take' ? this.fW : 1));
    this.fStance.apply(this.fSt);
    if (this.hero) {
      settle(this.hSt, holding ? this.crouchTo(this.hero, this.hR, raw.h.map((g) => g.p), st === 'take' ? ease(s / 0.7) : 1) : REST);
      this.hStance.apply(this.hSt);
    }
    if (holding) {
      this.fG = this.match(f, this.fPose, raw.f);
      this.hG = this.match(this.hero, this.hPose, raw.h);
      this.fT = this.fG.map((g) => g.w);
      this.hT = this.hG.map((g) => g.w);
      this.fH = this.hints(f, this.fPose);
      this.hH = this.hints(this.hero, this.hPose);
    }
    if (this.fT && (this.fW > 0.01 || this.hW > 0.01)) {
      this.fPose.apply(this.fT, this.fH, this.fW);
      this.fHands.grip(this.fG, this.fW);
      if (this.hero) { this.hPose.apply(this.hT, this.hH, this.hW); this.hHands.grip(this.hG, this.hW); }
    } else if (this.fT) {
      this.fHands.grip(null, 0);
      if (this.hero) this.hHands.grip(null, 0);
    }
    // held by the wrists, their own hands close loosely; open again in the air
    for (let i = 0; i < 2; i++) this.bHands.curl(i, 0.6 * this.fW);
    // the bubble anchor: over the head
    const head = this.bones.head.getWorldPosition(_v);
    this.anchor.position.set(head.x, head.y + 0.2 - this.bTop, head.z);
  }

  // the birthday student's body: hips at `hips` (world), facing `yaw`, tipped back `pitch`, rolled `roll`; u: the
  // soles from where they stood (0) to where they are carried (1)
  pose(hips, yaw, pitch, roll, u, hip = this.hipIdle) {
    this.carry(hips, yaw, pitch, roll, hip);
    (this.bp ||= { hips: new THREE.Vector3() }).hips.copy(hips);
    Object.assign(this.bp, { yaw, roll, u });
    if (this.state !== 'water') this.legW = Math.max(this.legW, 0.001);
  }

  // the legs by two-bone IK to the soles' places, knees the way the body faces (up, once it is tipped back). The
  // rig's feet are IK controls under Root, not children of the shins: each foot is put on the end of its shin as at
  // rest, or the skin would stretch from the knee to where the clip left the foot
  legsTo() {
    const bn = this.bones, { hips, yaw, roll, u } = this.bp, w = this.legW;
    const fr = new THREE.Quaternion().setFromAxisAngle(_Y, yaw).multiply(_q2.setFromAxisAngle(_Z, roll));
    const pole = new THREE.Vector3(0, 0, 1).applyQuaternion(this.b.holder.quaternion);
    const J = new THREE.Vector3(), K = new THREE.Vector3(), E = new THREE.Vector3(), kq = new THREE.Quaternion(), fq = new THREE.Quaternion();
    for (let i = 0; i < 2; i++) {
      const thigh = bn.thighs[i], knee = bn.knees[i], foot = bn.feet[i], { off, rel } = this.footOnShin[i];
      E.set(this.legSide[i] * 0.1, LEG_UP, LEG_OUT).applyQuaternion(fr).add(hips);
      E.lerpVectors(this.stand[i], E, u);
      thigh.getWorldPosition(J); knee.getWorldPosition(K);
      const l1 = J.distanceTo(K), l2 = off.length() * l1 / knee.position.length();
      twoBone(J, E, l1, l2, pole, K);
      aimAxis(thigh, this.kneeAxis[i], K.sub(J).normalize(), w);
      knee.getWorldPosition(K);
      aimAxis(knee, _w.copy(off).normalize(), E.sub(K).normalize(), w);
      knee.getWorldQuaternion(kq);
      foot.position.copy(foot.parent.worldToLocal(_w.copy(off).applyQuaternion(kq).add(K)));
      foot.parent.getWorldQuaternion(fq);
      foot.quaternion.copy(fq.invert().multiply(kq.multiply(rel)));   // (kq is spent here)
      foot.updateWorldMatrix(false, true);
    }
  }

  // what the hands close round on the carried body: the friend's the raised wrists (just below the hands), yours the
  // ankles (low on the shins). Each: a point on the limb's axis, the axis and the limb's radius
  grips() {
    const bn = this.bones, P = (o) => o.getWorldPosition(new THREE.Vector3());
    return {
      f: [0, 1].map((i) => {
        const p = P(bn.wrists[i]), axis = p.clone().sub(P(this.elbows[i])).normalize();
        return { p: p.addScaledVector(axis, -0.03), axis, r: 0.035 };
      }),
      h: [0, 1].map((i) => {
        const k = P(bn.knees[i]), e = P(bn.feet[i]);
        return { p: k.clone().lerp(e, 0.75), axis: e.sub(k).normalize(), r: 0.05 };
      }),
    };
  }

  // how far a carrier leans forward for hands at height y over their feet: a little for a carry at the waist, right
  // over for the ankles of someone standing
  leanFor(y) { return 0.15 * ease((1.35 - y) / 0.4) + 0.95 * ease((0.9 - y) / 0.75); }

  // the stance (armpose.js Stance) that brings carrier a's hands to the two points T on planted feet, k of the way:
  // lean by the height, hips towards the points (forward and across), and as deep a squat as the arms still need
  crouchTo(a, R, T, k) {
    const p = a.holder.position, yaw = a.heading, fx = Math.sin(yaw), fz = Math.cos(yaw), sx = fz, sz = -fx;
    const mx = (T[0].x + T[1].x) / 2 - p.x, my = (T[0].y + T[1].y) / 2 - p.y, mz = (T[0].z + T[1].z) / 2 - p.z;
    const along = mx * fx + mz * fz, lat = mx * sx + mz * sz;
    const lean = this.leanFor(my), out = R.fwd + R.spine * Math.sin(lean);
    const sway = THREE.MathUtils.clamp(0.6 * lat, -0.18, 0.18);
    const side = THREE.MathUtils.clamp(0.8 * (lat - sway) / R.spine, -0.35, 0.35);
    const l = Math.abs(lat - sway - R.spine * Math.sin(side)) + Math.max(0, T[0].distanceTo(T[1]) / 2 - R.half);
    const gap = 0.2 + 0.1 * ease((0.6 - my) / 0.4);              // arms further out for hands near the ground: the head clear
    const fwd = THREE.MathUtils.clamp(along - gap - out, -0.12, 0.12);
    const hz = along - out - fwd, reach = 0.93 * R.arm;
    const top = R.h - R.spine * (1 - Math.cos(lean));
    const dip = this.state === 'swing' ? this.dip || 0 : 0;
    const drop = THREE.MathUtils.clamp(top - my - Math.sqrt(Math.max(0.01, reach * reach - hz * hz - l * l)), 0, 0.62) + dip;
    return { drop: drop * k, lean: lean * k, side: side * k, sway: sway * k, fwd: fwd * k };
  }

  // the friend, holding the wrists, steps back to where the hands reach them with easy arms (facing the same way)
  backWith(a, dt) {
    const T = this.bones.wrists.map((x) => x.getWorldPosition(new THREE.Vector3())), R = this.fR, p = a.holder.position;
    const mx = (T[0].x + T[1].x) / 2, my = (T[0].y + T[1].y) / 2 - p.y, mz = (T[0].z + T[1].z) / 2;
    const lean = this.leanFor(my), dy = R.h - R.spine * (1 - Math.cos(lean)) - my, reach = 0.93 * R.arm;
    const hz = Math.min(0.2, Math.sqrt(Math.max(0.01, reach * reach - dy * dy)));
    const want = (mx - this.spot.x) * this.tan.x + (mz - this.spot.z) * this.tan.z - hz - R.fwd - R.spine * Math.sin(lean);
    const now = (p.x - this.spot.x) * this.tan.x + (p.z - this.spot.z) * this.tan.z;
    const go = THREE.MathUtils.clamp(want - now, -1.6 * dt, 0);
    p.addScaledVector(this.tan, go);
    const v = go / Math.max(dt, 1e-4);
    locomotion(a, Math.abs(v) > 0.08 ? Math.sign(v) * Math.max(0.5, Math.abs(v)) : 0);
  }

  // the carrier's two hands (L, R) on the two grips, uncrossed. Each hand lies across its limb, outside it with the
  // palm in (towards the other hand; palm down when the two are one above the other), so the curled fingers hook
  // under: w where the wrist goes, h the way the hand points, n the way the palm faces
  match(a, pose, two) {
    a.holder.updateMatrixWorld(true);
    const x = (p) => a.holder.worldToLocal(p.clone()).x;
    const sh = pose.arms.map((arm) => arm.up.getWorldPosition(new THREE.Vector3()));
    const [p, q] = (x(two[0].p) > x(two[1].p)) === (x(sh[0]) > x(sh[1])) ? two : [two[1], two[0]];
    const one = (g, o, s) => {
      const h = g.p.clone().sub(s).normalize();
      h.addScaledVector(g.axis, -h.dot(g.axis)).normalize();
      const n = new THREE.Vector3().crossVectors(g.axis, h);
      if (n.dot(_v.copy(o.p).sub(g.p).normalize()) - 0.5 * n.y < 0) n.negate();
      return { w: g.p.clone().addScaledVector(n, -g.r).addScaledVector(h, -PALM), h, n };
    };
    return [one(p, q, sh[0]), one(q, p, sh[1])];
  }

  // elbows down, out and a little back
  hints(a, pose) {
    const sideW = new THREE.Vector3(1, 0, 0).applyQuaternion(a.holder.quaternion), back = new THREE.Vector3(0, 0, -1).applyQuaternion(a.holder.quaternion);
    const sL = Math.sign(a.holder.worldToLocal(pose.arms[0].up.getWorldPosition(new THREE.Vector3())).x) || 1;
    return [1, -1].map((g) => new THREE.Vector3(0, -1, 0).addScaledVector(sideW, g * sL * 0.7).addScaledVector(back, 0.35));
  }

  // let go: the hands follow through towards the pool as the arms come down
  releaseHands() {
    const push = this.v0.clone().multiplyScalar(0.07);
    this.fT = this.fT.map((p) => p.clone().add(push));
    this.hT = this.hT.map((p) => p.clone().add(push));
  }

  // the carried student's arms up over their head (in their own frame): straight out to the friend's hands while
  // held, swaying a little as on a ride once let go
  cheerArms(t, held) {
    const pose = this.bPose, h = this.b.holder;
    if (!pose.ok) return;
    const sL = Math.sign(h.worldToLocal(pose.arms[0].up.getWorldPosition(new THREE.Vector3())).x) || 1;
    const T = [], H = [];
    for (let i = 0; i < 2; i++) {
      const sg = i ? -sL : sL, ph = i * 1.9;
      const sh = h.worldToLocal(pose.arms[i].up.getWorldPosition(new THREE.Vector3()));
      const up = this.state === 'take' ? 0 : this.state === 'lift' ? ease(this.st / LIFT_T) : 1;   // up and back, then straight out
      const loc = sh.add(held ? new THREE.Vector3(sg * (0.09 + 0.12 * up), 0.47 + 0.09 * up, -0.34 + 0.37 * up)
        : new THREE.Vector3(sg * (0.2 + 0.05 * Math.sin(t * 5 + ph)), 0.5 + 0.04 * Math.sin(t * 6.3 + ph), 0.12 + 0.06 * Math.cos(t * 4.1 + ph)));
      T.push(h.localToWorld(loc));
      H.push(new THREE.Vector3(sg, 0, -0.5).applyQuaternion(h.quaternion));
    }
    pose.apply(T, H, this.armsUp);
  }

  finish() {
    this.go('rest');
    const pl = this.player;
    Object.assign(this.hSt, REST); Object.assign(this.fSt, REST);
    this.hStance.apply(); this.fStance.apply();
    this.hHands.grip(null, 0); this.fHands.grip(null, 0); this.bHands.grip(null, 0);
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
