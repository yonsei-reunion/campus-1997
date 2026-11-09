// Procedural arm pose for the shared Quaternius rig: both hands go to given points (two-bone IK), blended over the clip's own arm
// motion. The bones run along their local +Y, so a bone is "aimed" by turning its +Y towards a world direction. Call update()
// each frame AFTER the animation mixer has run and before the frame is rendered.
import * as THREE from 'three';

const _p = new THREE.Quaternion(), _w = new THREE.Quaternion(), _r = new THREE.Quaternion();
const _a = new THREE.Vector3(), _b = new THREE.Vector3(), _c = new THREE.Vector3(), _d = new THREE.Vector3();
const UP = new THREE.Vector3(0, 1, 0);

// turn a bone so that its local `axis` (unit) points along the world direction dir, w of the way from its pose; its
// parents' world matrices must be current
export function aimAxis(bone, axis, dir, w = 1) {
  bone.parent.getWorldQuaternion(_p);
  _w.copy(_p).multiply(bone.quaternion);
  _a.copy(axis).applyQuaternion(_w);
  _r.setFromUnitVectors(_a, dir);
  _w.premultiply(_r);
  _p.invert().multiply(_w).normalize();
  if (w >= 0.999) bone.quaternion.copy(_p); else bone.quaternion.slerp(_p, w);
  bone.updateWorldMatrix(false, true);
}
const aim = (bone, dir) => aimAxis(bone, UP, dir);

// two-bone IK: joint J, lengths l1 and l2, end wanted at E, the middle joint bending towards pole. Returns the middle
// joint's place (in out)
export function twoBone(J, E, l1, l2, pole, out) {
  const v = _c.copy(E).sub(J);
  const d = Math.min(Math.max(v.length(), Math.abs(l1 - l2) + 0.02), l1 + l2 - 0.004);
  v.normalize();
  const a = (l1 * l1 - l2 * l2 + d * d) / (2 * d), h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
  _d.copy(pole).addScaledVector(v, -pole.dot(v)).normalize();
  return out.copy(J).addScaledVector(v, a).addScaledVector(_d, h);
}

export class ArmPose {
  constructor(actor) {
    this.setActor(actor);
  }

  setActor(actor) {
    this.actor = actor;
    const f = (n) => actor.root.getObjectByName(n);
    this.arms = ['L', 'R'].map((s) => ({ up: f('UpperArm' + s), low: f('LowerArm' + s), wrist: f('Wrist' + s), s }));
    this.body = f('Body');
    this.ok = this.arms.every((a) => a.up && a.low && a.wrist) && !!this.body;
  }

  // targets: [leftHandWorld, rightHandWorld]; hints: matching elbow direction hints (world vectors); w: 0..1 blend
  // bodyUp: metres to lift the hips (a hop)
  apply(targets, hints, w, bodyUp = 0) {
    if (!this.ok || (w <= 0.001 && !bodyUp)) return;
    this.actor.holder.updateMatrixWorld(true);
    if (bodyUp) this.body.position.y += bodyUp;
    if (w <= 0.001) return;
    this.arms.forEach((arm, i) => {
      const q0 = arm.up.quaternion.clone(), q1 = arm.low.quaternion.clone();
      arm.up.getWorldPosition(_b);                         // shoulder joint
      arm.low.getWorldPosition(_c);                        // elbow
      arm.wrist.getWorldPosition(_d);
      const l1 = _b.distanceTo(_c), l2 = _c.distanceTo(_d);
      const S = _b.clone(), H = targets[i].clone();
      const v = H.clone().sub(S);
      let d = v.length();
      d = Math.min(Math.max(d, Math.abs(l1 - l2) + 0.02), l1 + l2 - 0.01);
      v.normalize();
      const a = (l1 * l1 - l2 * l2 + d * d) / (2 * d);
      const h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
      const pole = hints[i].clone();
      pole.addScaledVector(v, -pole.dot(v)).normalize();
      const E = S.clone().addScaledVector(v, a).addScaledVector(pole, h);
      const Hn = S.clone().addScaledVector(v, d);
      aim(arm.up, E.clone().sub(S).normalize());
      aim(arm.low, Hn.sub(E).normalize());
      if (w < 0.999) {                                     // blend towards the pose from the clip's own arms
        const n0 = arm.up.quaternion.clone(), n1 = arm.low.quaternion.clone();
        arm.up.quaternion.copy(q0).slerp(n0, w);
        arm.low.quaternion.copy(q1).slerp(n1, w);
        arm.up.updateWorldMatrix(false, true);
      }
    });
  }
}

// A standing figure's stance on planted feet: squat, lean forward or sideways, shift the hips. In this rig the legs
// hang from Body and the feet are separate bones under Root, so lowering Body leaves the feet where they are and the
// legs are bent to them here. Call apply() each frame after the mixer (and before ArmPose); apply() with nothing
// gives the clip's own pose back.
const _hq = new THREE.Quaternion(), _lq = new THREE.Quaternion(), _bq = new THREE.Quaternion();
const _j = new THREE.Vector3(), _k = new THREE.Vector3(), _e = new THREE.Vector3(), _pl = new THREE.Vector3(), _ax = new THREE.Vector3();
const X = new THREE.Vector3(1, 0, 0), Z = new THREE.Vector3(0, 0, 1);

export class Stance {
  // shin: where each foot bone sits from its knee, in the knee's frame, at rest ([L, R])
  constructor(actor, shin) {
    this.shin = shin;
    this.setActor(actor);
  }

  setActor(actor) {
    this.actor = actor;
    const f = (n) => actor.root.getObjectByName(n);
    this.body = f('Body');
    this.hips = f('Hips');
    this.head = f('Head');
    this.legs = ['L', 'R'].map((s) => ({ up: f('UpperLeg' + s), low: f('LowerLeg' + s), foot: f('Foot' + s) }));
    this.ok = !!this.body && !!this.hips && this.legs.every((l) => l.up && l.low && l.foot);
    if (this.ok) this.hipsRest = this.hips.quaternion.clone();     // no clip turns Hips: ours to turn and put back
  }

  // drop: metres the hips come down; lean: rad forward from the hips; side: rad towards the figure's +X;
  // sway, fwd: metres the hips move towards +X / the way the figure faces
  apply({ drop = 0, lean = 0, side = 0, sway = 0, fwd = 0 } = {}) {
    if (!this.ok) return;
    const h = this.actor.holder;
    this.hips.quaternion.copy(this.hipsRest);
    const mag = Math.abs(drop) + Math.abs(sway) + Math.abs(fwd);
    if (mag < 1e-4 && Math.abs(lean) + Math.abs(side) < 1e-4) return;
    h.updateMatrixWorld(true);
    h.getWorldQuaternion(_hq);
    if (mag >= 1e-4) {
      this.body.getWorldPosition(_j);
      _j.add(_e.set(sway, -drop, fwd).applyQuaternion(_hq));
      this.body.position.copy(this.body.parent.worldToLocal(_j));
      this.body.updateWorldMatrix(false, true);
    }
    // the spine from the hips, in the figure's own frame
    _lq.setFromAxisAngle(X, lean).multiply(_bq.setFromAxisAngle(Z, -side));
    _lq.premultiply(_hq).multiply(_bq.copy(_hq).invert());
    this.body.getWorldQuaternion(_bq);
    this.hips.quaternion.copy(_bq).invert().multiply(_lq).multiply(_bq).multiply(this.hipsRest).normalize();
    this.hips.updateWorldMatrix(false, true);
    // the head stays up as the back goes over (the clips drive Head, so this lasts the frame)
    if (this.head && lean > 0.2) { this.head.quaternion.multiply(_lq.setFromAxisAngle(X, -0.55 * (lean - 0.2))); this.head.updateWorldMatrix(false, true); }
    if (mag < 1e-4) return;
    // the legs to the feet: knees forward, and apart as the squat deepens
    const w = Math.min(1, mag / 0.04), wide = Math.min(1, Math.max(0, drop) / 0.45);
    this.legs.forEach((leg, i) => {
      leg.up.getWorldPosition(_j); leg.low.getWorldPosition(_k); leg.foot.getWorldPosition(_e);
      const l1 = _j.distanceTo(_k), l2 = this.shin[i].length() * l1 / leg.low.position.length();
      const sg = Math.sign(h.worldToLocal(_pl.copy(_j)).x) || 1;
      _pl.set(sg * (0.15 + 1.1 * wide), 0, 1).applyQuaternion(_hq);
      twoBone(_j, _e, l1, l2, _pl, _k);
      aimAxis(leg.up, _ax.copy(leg.low.position).normalize(), _k.sub(_j).normalize(), w);
      leg.low.getWorldPosition(_k);
      aimAxis(leg.low, _ax.copy(this.shin[i]).normalize(), _e.sub(_k).normalize(), w);
    });
  }
}

// The hands of the shared rig closing round something: the wrist turned so the hand lies across it with the palm on
// it, and the fingers curled. No clip moves the finger bones, so they are ours to curl and must be put back (grip
// with w = 0). Make it while the fingers are at rest.
const _m1 = new THREE.Matrix4(), _m2 = new THREE.Matrix4(), _t = new THREE.Vector3(), _u = new THREE.Vector3();
const CURL = { 1: 0.15, 2: 1.15, 3: 1.05, 4: 0.6 }, THUMB = { 1: 0.75, 2: 0.5, 3: 0.4 };

export class Hands {
  constructor(actor) { this.setActor(actor); }

  setActor(actor) {
    this.actor = actor;
    actor.holder.updateMatrixWorld(true);
    const f = (n) => actor.root.getObjectByName(n);
    const yOf = (b) => new THREE.Vector3(0, 1, 0).applyQuaternion(b.getWorldQuaternion(new THREE.Quaternion()));
    this.sides = ['L', 'R'].map((s) => {
      const wrist = f('Wrist' + s), i2 = f('Index2' + s), i4 = f('Index4' + s), m2 = f('Middle2' + s);
      if (!wrist || !i2 || !i4 || !m2) return null;
      const wq = wrist.getWorldQuaternion(new THREE.Quaternion()).invert();
      // along the hand, and the palm's side (the way the fingers already bend)
      const along = m2.getWorldPosition(new THREE.Vector3()).sub(wrist.getWorldPosition(new THREE.Vector3())).normalize();
      const palm = yOf(i4).sub(yOf(i2));
      palm.addScaledVector(along, -palm.dot(along)).normalize();
      const fingers = [];
      for (const name of ['Index', 'Middle', 'Ring', 'Pinky', 'Thumb']) for (let k = 1; k <= 4; k++) {
        const b = f(name + k + s), a = (name === 'Thumb' ? THUMB : CURL)[k];
        if (!b || !a) continue;
        // the axis the bone turns about to bend towards the palm, in its own frame
        const axis = yOf(b).cross(palm).normalize().applyQuaternion(b.getWorldQuaternion(new THREE.Quaternion()).invert());
        fingers.push({ b, rest: b.quaternion.clone(), axis, a });
      }
      return { wrist, along: along.applyQuaternion(wq), palm: palm.applyQuaternion(wq), fingers };
    });
    this.ok = this.sides.every(Boolean);
  }

  // curl the fingers of hand i (0 = L, 1 = R) c of the way shut
  curl(i, c) {
    if (!this.ok) return;
    for (const g of this.sides[i].fingers) g.b.quaternion.copy(g.rest).multiply(_bq.setFromAxisAngle(g.axis, g.a * c));
  }

  // G: per hand { h: the way the hand points, n: the way the palm faces } (world, unit, at right angles); w: 0..1.
  // After ArmPose.apply
  grip(G, w) {
    if (!this.ok) return;
    this.sides.forEach((sd, i) => {
      this.curl(i, w);
      if (w <= 0.001 || !G) return;
      const { h, n } = G[i];
      _m1.makeBasis(sd.along, sd.palm, _t.crossVectors(sd.along, sd.palm));
      _m2.makeBasis(h, n, _u.crossVectors(h, n));
      _lq.setFromRotationMatrix(_m2.multiply(_m1.transpose()));
      sd.wrist.parent.getWorldQuaternion(_bq);
      _lq.premultiply(_bq.invert()).normalize();
      if (w >= 0.999) sd.wrist.quaternion.copy(_lq); else sd.wrist.quaternion.slerp(_lq, w);
      sd.wrist.updateWorldMatrix(false, true);
    });
  }
}
