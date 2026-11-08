// Touch controls for the walk (phones / tablets):
//   left part of the screen: a floating stick that appears under the thumb wherever it lands.
//     Push it the way you want to go on screen (up = ahead, right = to the right, down = towards the camera);
//     push it all the way to run.
//   rest of the screen: one finger drags the camera round (up to look up at the roofs and the sky, down to look over
//     the walker), two fingers pinch to come closer or go farther.
// The bird's-eye tour has its own touch handling (birdseye.js): everything here sleeps while the walker is parked.
import { clamp } from './util.js';
import { LIFT_MAX, LOOK_UP } from './player.js';

const STICK_R = 50;            // px the knob can travel from the stick centre
const LEFT = 0.45;             // fraction of the screen width where a new touch starts the stick

export class TouchControls {
  constructor(player, dom, stickEl) {
    this.player = player;
    this.stickEl = stickEl;
    this.knob = stickEl.querySelector('div');
    this.stickId = null;
    this.cx = 0; this.cy = 0;
    this.looks = new Map();       // camera fingers: id -> {x, y}
    this.pinch = 0;

    dom.addEventListener('pointerdown', (e) => {
      if (e.pointerType !== 'touch' || !player.enabled || e.target !== dom) return;
      e.preventDefault();
      if (this.stickId === null && e.clientX < innerWidth * LEFT && !this.looks.size) this.startStick(e);
      else {
        this.looks.set(e.pointerId, { x: e.clientX, y: e.clientY });
        this.pinch = this.looks.size === 2 ? this.spread() : 0;
        player.cam.drag = { touch: true };         // the camera stops swinging back while a finger holds it
      }
      try { dom.setPointerCapture(e.pointerId); } catch { /* pointer already gone */ }
    });
    dom.addEventListener('pointermove', (e) => {
      if (e.pointerType !== 'touch') return;
      if (e.pointerId === this.stickId) { this.moveStick(e.clientX, e.clientY); return; }
      const f = this.looks.get(e.pointerId);
      if (!f) return;
      const c = player.cam;
      if (this.looks.size === 2) {
        f.x = e.clientX; f.y = e.clientY;
        const s = this.spread();
        if (this.pinch > 10 && s > 10) c.dist = clamp(c.dist * this.pinch / s, 2.4, 16);
        this.pinch = s;
        return;
      }
      c.orbit -= (e.clientX - f.x) * 0.008;
      c.lift = clamp(c.lift + (e.clientY - f.y) * 0.005, LOOK_UP, LIFT_MAX);
      f.x = e.clientX; f.y = e.clientY;
    });
    const up = (e) => {
      if (e.pointerType !== 'touch') return;
      if (e.pointerId === this.stickId) { this.endStick(); return; }
      if (!this.looks.delete(e.pointerId)) return;
      this.pinch = 0;
      if (!this.looks.size) player.cam.drag = null;
    };
    dom.addEventListener('pointerup', up);
    dom.addEventListener('pointercancel', up);
  }

  spread() {
    const [a, b] = [...this.looks.values()];
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  startStick(e) {
    this.stickId = e.pointerId;
    this.cx = e.clientX; this.cy = e.clientY;
    const el = this.stickEl;
    el.classList.add('live', 'used');
    el.style.left = `${this.cx - el.offsetWidth / 2}px`;
    el.style.top = `${this.cy - el.offsetHeight / 2}px`;
    el.style.bottom = 'auto';
    this.moveStick(e.clientX, e.clientY);
  }

  moveStick(x, y) {
    let dx = x - this.cx, dy = y - this.cy;
    const d = Math.hypot(dx, dy);
    if (d > STICK_R) { dx *= STICK_R / d; dy *= STICK_R / d; }
    this.knob.style.transform = `translate(${dx}px, ${dy}px)`;
    this.player.stick.set(dx / STICK_R, dy / STICK_R);
  }

  endStick() {
    this.stickId = null;
    this.player.stick.set(0, 0);
    this.knob.style.transform = '';
    const el = this.stickEl;
    el.classList.remove('live');
    el.style.left = el.style.top = el.style.bottom = '';    // back to the resting spot (CSS)
  }

  // the walk was paused (memory card, map, tour...): let go of everything
  reset() {
    if (this.stickId !== null) this.endStick();
    this.looks.clear();
    this.pinch = 0;
    this.player.cam.drag = null;
  }
}
