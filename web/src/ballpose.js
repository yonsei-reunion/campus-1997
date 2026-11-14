// Basketball motions on the shared rig, for the court (hoops.js), the 1-minute shooting game (shootout.js) and the
// 캠퍼스 사람들 page (people.js): holding and catching the ball, the shot (the men one-handed: the right hand under
// the ball, the left at its side; the women the two-handed set shot of the day) and a feeder's pick-up off the
// ground and chest pass. No clip in the rig does any of it, so it is built here over the clip that plays.
//
// The ball's path is given in the person's own frame from where their shoulders are, so it suits every model's reach
// (the rig's arms are short: 0.41 m shoulder to wrist). Each hand gets a place on the ball (a palm on its side, or the
// shooting palm under it) that gives where its wrist goes and how the hand lies; the arms go there by two-bone IK
// (armpose.js ArmPose) and the hands are turned to lie on the ball (Hands). The ball then goes where the hands really
// are: it never floats off a hand that cannot quite reach.
//
// Call pose() each frame after the person's mixer has run, and before the frame is drawn.
import * as THREE from 'three';
import { ArmPose, Stance, Hands } from './armpose.js';

export const R = 0.12, G = 9.8;
const PALM = 0.075;                  // wrist to the middle of the palm
const ON = R + 0.012;                // the middle of a palm on the ball from its centre
const CURL = 0.22;                   // the fingers spread round the ball, a little bent
// men shoot one-handed, women the two-handed set shot
export const oneHanded = (id) => !String(id).startsWith('woman');
// the shot, in seconds from the press: the dip (ball to the waist, knees bend), the ball up to the set point as the
// jump starts, the top of the jump (the moment to let go), held on past it until LATE at the most; from letting go the
// flick (the arm straightens and the ball rolls off the fingers) and the follow-through
export const SHOT = { DIP: 0.22, SET: 0.5, TOP: 0.62, LATE: 1.0, FLICK: 0.09, FOLLOW: 0.42 };
// the chest pass: the ball back to the chest, pushed out and let go at PUSH, the hands held out after it till FOLLOW
export const PASS = { PULL: 0.12, PUSH: 0.28, FOLLOW: 0.6 };
// picking a ball up off the ground: bent down to it by DOWN, up with it at the chest by UP
export const PICK = { DOWN: 0.4, UP: 0.9 };
// how high the jump of the shot has the person at time t (m): up from 0.34 s, highest at the top (men jump, the
// women's set shot is a little hop). Lift the person by it before pose()
export const hopAt = (one, t) => (one ? 0.16 : 0.07) * bell((t - 0.34) / (2 * (SHOT.TOP - 0.34)));

const ease = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));
const bell = (u) => (u <= 0 || u >= 1 ? 0 : Math.sin(Math.PI * u));
const lerp = (a, b, u) => a + (b - a) * u;
const DEG = Math.PI / 180;
const _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _m = new THREE.Matrix4();
const _a = new THREE.Vector3(), _b = new THREE.Vector3(), _c = new THREE.Vector3();
const X = new THREE.Vector3(1, 0, 0), Y = new THREE.Vector3(0, 1, 0);

// ---------------------------------------------------------------- the ball
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
let BALL = null;
// a ball mesh (all balls share one geometry and material); patch: something to do to the material once (main.js: the
// atmosphere's cloud shadows and fog)
export function makeBall(patch = null) {
  if (!BALL) {
    BALL = { geo: new THREE.SphereGeometry(R, 24, 16), mat: new THREE.MeshStandardMaterial({ map: ballTexture(), roughness: 0.75 }) };
    patch?.(BALL.mat);
  }
  const m = new THREE.Mesh(BALL.geo, BALL.mat);
  m.name = 'basketball';
  m.castShadow = true;
  return m;
}

// each foot from its knee in the knee's frame, as the person stands now (armpose.js Stance)
export function shinOf(actor) {
  actor.holder.updateMatrixWorld(true);
  const s = actor.holder.scale.y || 1;
  return ['L', 'R'].map((side) => {
    const knee = actor.root.getObjectByName('LowerLeg' + side), foot = actor.root.getObjectByName('Foot' + side);
    if (!knee || !foot) return new THREE.Vector3(0, 0.4, 0);
    const kq = knee.getWorldQuaternion(new THREE.Quaternion()).invert();
    return foot.getWorldPosition(new THREE.Vector3()).sub(knee.getWorldPosition(new THREE.Vector3())).applyQuaternion(kq).divideScalar(s);
  });
}

// a hand on the ball, in the person's own frame: W where the wrist goes, h the way the hand points, n the way the palm
// faces (unit, at right angles)
const frame = (W, h, n) => ({ W, h, n });
function blend(a, b, u) {
  if (u <= 0) return a;
  if (u >= 1) return b;
  const qa = basis(a, new THREE.Quaternion()), qb = basis(b, _q2);
  qa.slerp(qb, u);
  return frame(a.W.clone().lerp(b.W, u), X.clone().applyQuaternion(qa), Y.clone().applyQuaternion(qa));
}
function basis(f, out) {
  _c.crossVectors(f.h, f.n);
  _m.makeBasis(f.h, f.n, _c);
  return out.setFromRotationMatrix(_m);
}

// ---------------------------------------------------------------- the person with the ball
export class BallForm {
  constructor(actor) { this.setActor(actor); }

  // measured as the person stands now (any standing or walking clip will do: the shoulders hardly move)
  setActor(actor) {
    this.actor = actor;
    this.arms = new ArmPose(actor);
    this.hands = new Hands(actor);
    this.stance = new Stance(actor, shinOf(actor));
    this.one = oneHanded(actor.id);
    this.ok = this.arms.ok;
    if (!this.ok) return;
    const h = actor.holder;
    h.updateMatrixWorld(true);
    const loc = (b) => h.worldToLocal(b.getWorldPosition(new THREE.Vector3()));
    const [L, Rt] = this.arms.arms;
    const sl = loc(L.up), sr = loc(Rt.up);
    this.sh = [sl, sr];
    const len = (a) => loc(a.up).distanceTo(loc(a.low)) + loc(a.low).distanceTo(loc(a.wrist));
    this.A = (len(L) + len(Rt)) / 2;
    this.sx = Math.sign(sl.x - sr.x) || 1;            // the left hand's side of the body (+X or -X of the holder)
    const Sy = (sl.y + sr.y) / 2, Sz = (sl.z + sr.z) / 2, rs = -this.sx;
    const v = (x, y, z) => new THREE.Vector3(x, y, z);
    this.K = {
      hold: v(0, Sy - 0.21, Sz + 0.25),
      dip: v(this.one ? rs * 0.04 : 0, Sy - 0.36, Sz + 0.22),
      set: this.one ? v(rs * 0.07, Sy + 0.3, Sz + 0.2) : v(0, Sy + 0.01, Sz + 0.3),
      top: v(0, Sy + 0.33, Sz + 0.42),               // two hands: where the ball leaves them
      pull: v(0, Sy - 0.25, Sz + 0.17),
      push: v(0, Sy - 0.12, Sz + 0.5),
      ground: v(0, R, Sz + 0.4),                     // a ball to pick up: before the feet
    };
    // one hand: the arm straight up and forward (a little in) at the release, the palm still under the back of the
    // ball as it rolls off the fingers; THETA: the palm's angle up from forward at the set point and there
    const dir = v(-rs * 0.1, 0.88, 0.46).normalize();
    this.wTop = sr.clone().addScaledVector(dir, this.A * 0.96);
    this.fTop = Math.atan2(dir.y, dir.z);           // the forearm's angle up from forward
    this.nSet = 78 * DEG; this.nTop = this.fTop - 45 * DEG;
    this.K.top1 = this.under(null, this.nTop, this.wTop).ball;
    this.eye = null;
    this.last = null;                                // the last frame's hands, for the arms coming down
    this.ball = null; this.from = new THREE.Vector3();
  }

  // the shooting palm under the ball (one hand), palm at angle t up from forward; from the ball's centre B, or from
  // the wrist W
  under(B, t, W = null) {
    const n = new THREE.Vector3(0, Math.sin(t), Math.cos(t)), h = new THREE.Vector3(0, Math.cos(t), -Math.sin(t));
    if (W) return { ball: W.clone().addScaledVector(h, PALM).addScaledVector(n, ON), f: frame(W.clone(), h, n) };
    return { ball: B, f: frame(B.clone().addScaledVector(n, -ON).addScaledVector(h, -PALM), h, n) };
  }

  // hand i (0 = L, 1 = R) on the ball's side, the palm `back` rad round behind it; the hand pointing `up` rad up from
  // forward
  side(B, i, back, up) {
    const s = i === 0 ? this.sx : -this.sx;
    const d = new THREE.Vector3(s * Math.cos(back), 0, -Math.sin(back));
    const n = d.clone().negate();
    const h = new THREE.Vector3(0, Math.sin(up), Math.cos(up));
    h.addScaledVector(n, -h.dot(n)).normalize();
    return frame(B.clone().addScaledVector(d, ON).addScaledVector(h, -PALM), h, n);
  }

  // the elbows: down and out, or (the shooting arm) forward and down under the ball
  pole(i, out, down, fwd) { return new THREE.Vector3((i === 0 ? this.sx : -this.sx) * out, -down, fwd); }

  // where the ball is held at the chest, world; fp, eyeH: as for pose()
  holdPoint(fp = 0, eyeH = 1.6, out = new THREE.Vector3()) {
    const h = this.actor.holder;
    h.updateMatrixWorld(true);
    out.copy(this.K.hold);
    if (fp > 0) out.lerp(_a.set(0, eyeH / (h.scale.y || 1) - 0.3, 0.56), fp);
    return h.localToWorld(out);
  }

  // mode: 'hold' (at the chest), 'catch' (hands out to `at`, world: the ball coming in), 'shot' (t: s since the
  // press, tr: when it was let go, null while held on), 'pick' (t: s into picking up the ball at `at`, world),
  // 'pass' (t: s into the chest pass), 'free' (the arms coming down: w going to 0)
  // w: how far the arms follow this (0..1) instead of the clip; fp: how far the view is in the person's eyes (player.js
  // cam.fp: the body is not drawn, and the ball is held before the eyes instead), eyeH: their eyes' height
  // Sets this.ball (world: the ball in the hands, null when it is not) and this.from (where it was last in them: where
  // a shot or a pass leaves the hands). A shot's jump is the caller's to make (hopAt), before this
  pose(mode, { t = 0, tr = null, w = 1, at = null, fp = 0, eyeH = 1.6 } = {}) {
    this.ball = null;
    if (!this.ok) return;
    const a = this.actor, h = a.holder;
    h.updateMatrixWorld(true);
    let st = null, B = null, f = null, poles = null, fpB = null, carry = true, corr = 1;
    const K = this.K;
    if (mode === 'free') {
      if (!this.last || w <= 0.001) { this.rest(); return; }
      ({ f, poles } = this.last);
      carry = false;
    } else if (mode === 'hold' || mode === 'catch') {
      B = mode === 'catch' ? h.worldToLocal(at.clone()) : K.hold.clone();
      f = [this.side(B, 0, 0.15, 1.1), this.side(B, 1, 0.15, 1.1)];
      poles = [this.pole(0, 0.9, 1, -0.15), this.pole(1, 0.9, 1, -0.15)];
      fpB = mode === 'hold' ? new THREE.Vector3(0, -0.3, 0.56) : null;
      carry = mode === 'hold';
    } else if (mode === 'shot') {
      ({ B, f, poles, fpB, st, carry } = this.shot(t, tr));
    } else if (mode === 'pick') {
      const G0 = h.worldToLocal(at.clone()), dn = ease(t / PICK.DOWN), up = ease((t - PICK.DOWN) / (PICK.UP - PICK.DOWN));
      const k = dn * (1 - up);
      st = { drop: 0.3 * k, lean: 1.25 * k, fwd: 0.03 * k };
      B = G0.clone().lerp(K.hold, up);
      const hu = lerp(-0.6, 1.1, up);
      f = [this.side(B, 0, 0.1, hu), this.side(B, 1, 0.1, hu)];
      poles = [this.pole(0, 0.8, 1, -0.3), this.pole(1, 0.8, 1, -0.3)];
      carry = t > PICK.DOWN;
      corr = ease(up / 0.4);
      w *= ease(t / 0.25);
    } else if (mode === 'pass') {
      ({ B, f, poles, st, carry } = this.passAt(t));
      fpB = null;
    }
    this.stance.apply(st || undefined);
    // the hands there, and the ball where they are
    const hq = h.getWorldQuaternion(_q);
    const W = f.map((x) => h.localToWorld(x.W.clone()));
    for (let i = 0; i < 2; i++) this.arms.applyArm(i, W[i], poles[i].clone().applyQuaternion(hq).normalize(), w);
    const G2 = f.map((x) => ({ h: x.h.clone().applyQuaternion(hq), n: x.n.clone().applyQuaternion(hq) }));
    this.hands.grip(G2, w, CURL * w);
    this.last = { f, poles };
    if (!B || !carry) return;
    const Bw = h.localToWorld(B.clone());
    // the ball goes with the hands that hold it (the shooting hand alone, once the guide hand is only at its side)
    const real = this.arms.arms.map((x) => x.wrist.getWorldPosition(new THREE.Vector3()));
    const use = mode === 'shot' && this.one ? [1] : [0, 1];
    const e = new THREE.Vector3();
    for (const i of use) e.add(real[i].sub(W[i]));
    e.multiplyScalar((corr * w ** 4) / use.length);
    Bw.add(e);
    if (fp > 0 && fpB) {
      const eye = _c.set(0, eyeH / (h.scale.y || 1), 0).add(fpB);
      Bw.lerp(h.localToWorld(eye), Math.min(1, fp));
    }
    this.ball = Bw;
    this.from.copy(Bw);
  }

  // the shot at time t (tr: let go then, or null)
  shot(t, tr) {
    const K = this.K, one = this.one, rs = -this.sx;
    const before = (u) => {
      // the ball's path while held on: down to the waist, up to the set point, a little higher by the top of the jump
      if (u < SHOT.DIP) return K.hold.clone().lerp(K.dip, ease(u / SHOT.DIP));
      if (u < SHOT.SET) return K.dip.clone().lerp(K.set, ease((u - SHOT.DIP) / (SHOT.SET - SHOT.DIP)));
      return K.set.clone().setY(K.set.y + 0.03 * ease((u - SHOT.SET) / (SHOT.TOP - SHOT.SET)));
    };
    const turn = (u) => ease((u - 0.04) / (SHOT.SET - 0.04));          // the shooting hand from the side to under the ball
    // the knees: down before the jump (hopAt) and again on landing
    const land = 0.34 + 2 * (SHOT.TOP - 0.34);
    const st = { drop: (one ? 0.1 : 0.08) * bell(t / 0.36) + 0.06 * bell((t - land) / 0.25), lean: 0.06 * bell(t / 0.36) };
    let B, f, poles, fpB, carry = true;
    const k = tr === null ? -1 : (t - tr) / SHOT.FLICK;
    // first person, from the eyes: down out of the view, then (one hand) up over the brow, only its underside in view as
    // you look up at the rim, or (two hands) up before the chin
    const fpAt = (u) => (u < SHOT.DIP ? _b.set(0, -0.3, 0.56).lerp(_c.set(0, -0.5, 0.48), ease(u / SHOT.DIP))
      : _b.set(0, -0.5, 0.48).lerp(_c.set(one ? rs * 0.1 : 0, one ? 0.38 : -0.12, one ? 0.46 : 0.5), ease((u - SHOT.DIP) / (SHOT.SET - SHOT.DIP))));
    if (one) {
      const pR = this.pole(1, 0.25, 0.55, 0.8), pL = this.pole(0, 0.9, 0.4, -0.1);
      if (k < 0) {
        B = before(t);
        const u = turn(t);
        f = [this.side(B, 0, 0.25, 1.25), blend(this.side(B, 1, 0.15, 1.1), this.under(B, this.nSet).f, u)];
        poles = [pL, this.pole(1, 0.9, 1, -0.15).lerp(pR, u)];
        fpB = fpAt(t).clone();
      } else if (k < 1) {
        // the flick: the arm straightens, the palm turns forward under the ball and it rolls up off the fingers
        const B0 = before(tr), u0 = turn(tr), e = ease(k);
        B = B0.clone().lerp(K.top1, e);
        const sh = this.under(B, lerp(this.nSet, this.nTop, e)).f;
        f = [this.side(B, 0, 0.25, 1.25), blend(this.side(B, 1, 0.15, 1.1), sh, lerp(u0, 1, ease(k * 2)))];
        poles = [pL, pR];
        fpB = fpAt(tr).clone().lerp(_c.set(rs * 0.06, 0.5, 0.6), e);
        this._guide = f[0];
      } else {
        // gone: the arm stays up, the wrist folds over (the "gooseneck"), the guide hand stays where it was
        const u = ease((t - tr - SHOT.FLICK) / 0.2);
        f = [this._guide || this.side(K.top1, 0, 0.25, 1.25), this.under(null, lerp(this.nTop, this.nTop - 70 * DEG, u), this.wTop).f];
        poles = [pL, pR];
        carry = false;
      }
    } else {
      const P = [this.pole(0, 0.75, 0.65, 0.1), this.pole(1, 0.75, 0.65, 0.1)];
      const hands = (B, back, up) => [this.side(B, 0, back, up), this.side(B, 1, back, up)];
      if (k < 0) {
        B = before(t);
        const u = ease((t - SHOT.DIP) / (SHOT.SET - SHOT.DIP));
        f = hands(B, lerp(0.15, 0.45, u), lerp(1.1, 1.3, u));
        poles = [this.pole(0, 0.9, 1, -0.15).lerp(P[0], u), this.pole(1, 0.9, 1, -0.15).lerp(P[1], u)];
        fpB = fpAt(t).clone();
      } else if (k < 1) {
        const e = ease(k);
        B = before(tr).lerp(K.top, e);
        f = hands(B, lerp(0.45, 0.6, e), lerp(1.3, 0.85, e));
        poles = P;
        fpB = fpAt(tr).clone().lerp(_c.set(0, 0.36, 0.55), e);
        this._two = f;
      } else {
        // the thumbs go down and the palms turn out after it
        const u = ease((t - tr - SHOT.FLICK) / 0.2);
        const f0 = this._two || hands(K.top, 0.6, 0.85);
        f = f0.map((x, i) => {
          const s = i === 0 ? this.sx : -this.sx;
          return blend(x, frame(x.W.clone().add(_a.set(s * 0.03, -0.02, 0.04)), new THREE.Vector3(0, -0.35, 0.94).normalize(), new THREE.Vector3(s, -0.3, 0).normalize()), u);
        });
        poles = P;
        carry = false;
      }
    }
    return { B, f, poles, fpB, st, carry };
  }

  // the chest pass at time t
  passAt(t) {
    const K = this.K;
    let B, carry = true;
    const P = [this.pole(0, 0.85, 0.5, 0), this.pole(1, 0.85, 0.5, 0)];
    const st = { lean: 0.14 * ease((t - PASS.PULL) / (PASS.PUSH - PASS.PULL)) * (1 - ease((t - PASS.PUSH) / 0.4)),
      fwd: 0.07 * ease((t - PASS.PULL) / (PASS.PUSH - PASS.PULL)) * (1 - ease((t - PASS.PUSH) / 0.5)) };
    let f;
    if (t < PASS.PULL) {
      B = K.hold.clone().lerp(K.pull, ease(t / PASS.PULL));
      const u = ease(t / PASS.PULL);
      f = [this.side(B, 0, lerp(0.15, 0.55, u), lerp(1.1, 0.75, u)), this.side(B, 1, lerp(0.15, 0.55, u), lerp(1.1, 0.75, u))];
    } else if (t < PASS.PUSH) {
      B = K.pull.clone().lerp(K.push, ease((t - PASS.PULL) / (PASS.PUSH - PASS.PULL)));
      f = [this.side(B, 0, 0.55, 0.75), this.side(B, 1, 0.55, 0.75)];
    } else {
      // let go: the arms out after it, the thumbs down
      const u = ease((t - PASS.PUSH) / 0.15);
      f = [0, 1].map((i) => {
        const s = i === 0 ? this.sx : -this.sx, x = this.side(K.push, i, 0.55, 0.75);
        return blend(x, frame(x.W.clone().add(_a.set(s * 0.04, -0.03, 0.05)), new THREE.Vector3(0, -0.2, 0.98).normalize(), new THREE.Vector3(s, -0.5, 0).normalize()), u);
      });
      carry = false;
    }
    return { B, f, poles: P, st, carry };
  }

  // the arms, the hands and the stance back to the clip's
  rest() {
    if (!this.ok) return;
    if (this.last) this.hands.grip(null, 0);
    this.stance.apply();
    this.last = null;
  }
}
