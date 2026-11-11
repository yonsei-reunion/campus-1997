// 캠퍼스 둘러보기 (bird's-eye tour), in the manner of sim-office's "Look around town" (office/engine/camera.js tour):
// the camera circles a point you move over the campus, from high above down to street level.
//   ↑↓ / W S  forward and back       ← → / A D  turn            Q E  sideways
//   Z X / wheel  closer and farther   R F  higher and lower (tilt)  Shift  faster
//   Space  slow circling on/off       T  season                  Y  1997 film look        Esc / B  back
//   mouse: drag = look round (turn & tilt), right-drag / Ctrl-drag = slide over the ground, double-click = fly there
//   touch: one finger slides, two fingers pinch-zoom and twist; the bar's buttons do the rest
// Landmark pins float over the buildings; picking one flies there and offers "여기서 걷기" / "추억 보기".
// Campus frame: x = east, y = north; three.js: (x, h, -y).
import * as THREE from 'three';
import { clamp, wrapAngle } from './util.js';

const BOUNDS = { x0: -480, x1: 580, y0: -520, y1: 600 };
const DIST = [6, 1400], PITCH = [0.04, 1.5];

export class BirdsEye {
  constructor({ camera, dom, landmarks, markers = [], heightAt, surfaceAt, pickGround, onWalkHere, onMemory, onAction }) {
    Object.assign(this, { camera, dom, heightAt, surfaceAt, pickGround, onWalkHere, onMemory, onAction });
    this.active = false;
    this.cur = { x: 0, y: -60, dist: 600, yaw: 0, pitch: 0.9, lift: 0 };    // lift: aim above the ground (statues)
    this.goal = { ...this.cur };
    this.auto = true;
    this.baseFov = camera.fov;                 // the preset views below narrow it; everything else goes back to this
    this.fovGoal = camera.fov;
    this.keys = new Set();
    this.focus = new THREE.Vector3();          // ground point at the view centre (tree LOD / shadows / crowd)
    this.selected = null;
    this.player = null;                        // {x, y} of the walker, or null on the title screen
    this._v = new THREE.Vector3();

    // ---------------------------------------------------------------- DOM: pins, selected place, tour bar
    this.layer = document.getElementById('birdpins');
    this.bar = document.getElementById('birdbar');
    this.tourbar = document.getElementById('tourbar');
    const pin = (l, cls) => {
      const el = document.createElement('button');
      el.className = cls;
      el.innerHTML = `<span>${l.name}</span>`;
      el.addEventListener('click', (e) => { e.stopPropagation(); this.select(l); });
      this.layer.appendChild(el);
      return el;
    };
    this.pins = [
      ...landmarks.map((l, i) => ({ l, el: pin(l, 'pin'), h: null, prio: l.id === 'events' ? 99 : i })),
      // smaller name tags over the other buildings (campus.markers), placed after the landmarks so they give way
      ...markers.map((l, i) => ({ l, el: pin(l, 'pin bld'), h: l.top + 3, prio: 100 + i, bld: true })),
    ];
    this.me = document.createElement('div');
    this.me.className = 'pin me';
    this.me.innerHTML = '<span>나</span>';
    this.layer.appendChild(this.me);
    this.bar.querySelector('.walk').addEventListener('click', () => {
      if (this.selected) this.onWalkHere(this.selected.pos[0], this.selected.pos[1], this.selected);
    });
    this.bar.querySelector('.memory').addEventListener('click', () => { if (this.selected) this.onMemory(this.selected); });
    this.bar.querySelector('.close').addEventListener('click', () => this.select(null));
    // bar buttons: tap = one step; held (tilt / zoom on touch screens) = keep going
    this.held = null;
    this.tourbar.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-tour]');
      if (!b) return;
      this.do(b.dataset.tour);
      b.blur();
    });
    this.tourbar.addEventListener('pointerdown', (e) => {
      const b = e.target.closest('button[data-hold]');
      if (b) this.held = b.dataset.hold;
    });
    addEventListener('pointerup', () => { this.held = null; });
    addEventListener('pointercancel', () => { this.held = null; });

    // ---------------------------------------------------------------- pointer input
    this.pointers = new Map();
    dom.addEventListener('pointerdown', (e) => {
      if (!this.active || e.target !== dom) return;
      const slide = e.pointerType === 'touch' || e.button === 2 || e.ctrlKey;
      this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY, slide });
      dom.setPointerCapture(e.pointerId);
      dom.classList.add('grabbing');
    });
    dom.addEventListener('pointermove', (e) => {
      const p = this.pointers.get(e.pointerId);
      if (!this.active || !p) return;
      const dx = e.clientX - p.x, dy = e.clientY - p.y;
      if (this.pointers.size === 2) {
        // pinch zoom + twist with two fingers
        const [a, b] = [...this.pointers.values()];
        const before = Math.hypot(a.x - b.x, a.y - b.y), angB = Math.atan2(b.y - a.y, b.x - a.x);
        p.x = e.clientX; p.y = e.clientY;
        const after = Math.hypot(a.x - b.x, a.y - b.y), angA = Math.atan2(b.y - a.y, b.x - a.x);
        if (before > 10 && after > 10) {
          this.goal.dist = clamp(this.goal.dist * before / after, ...DIST);
          this.goal.yaw -= wrapAngle(angA - angB);
        }
      } else if (p.slide) {
        this.slide(-dx, dy);
        p.x = e.clientX; p.y = e.clientY;
      } else {
        // look round: turn and tilt (sim-office's drag)
        this.goal.yaw -= dx * 0.006;
        this.goal.pitch = clamp(this.goal.pitch + dy * 0.004, ...PITCH);
        p.x = e.clientX; p.y = e.clientY;
      }
      if (Math.abs(dx) + Math.abs(dy) > 0) this.stopAuto();
    });
    const up = (e) => { this.pointers.delete(e.pointerId); if (!this.pointers.size) dom.classList.remove('grabbing'); };
    dom.addEventListener('pointerup', up);
    dom.addEventListener('pointercancel', up);
    dom.addEventListener('contextmenu', (e) => { if (this.active) e.preventDefault(); });
    dom.addEventListener('wheel', (e) => {
      if (!this.active) return;
      e.preventDefault();
      this.goal.dist = clamp(this.goal.dist * (e.deltaY > 0 ? 1.12 : 0.89), ...DIST);
      this.stopAuto();
    }, { passive: false });
    dom.addEventListener('dblclick', (e) => {
      if (!this.active) return;
      const r = dom.getBoundingClientRect();
      const hit = this.pickGround(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      if (hit) { this.goal.x = hit[0]; this.goal.y = hit[1]; this.goal.dist = Math.min(this.goal.dist, 200); }
      this.stopAuto();
    });

    // ---------------------------------------------------------------- keys
    addEventListener('keydown', (e) => {
      if (!this.active || /INPUT|TEXTAREA/.test(e.target.tagName)) return;
      this.keys.add(e.code);
      if (/Arrow|Space|PageUp|PageDown/.test(e.code)) e.preventDefault();
      if (e.repeat) return;
      if (e.code === 'Space') this.do('auto');
      else if (e.code === 'KeyT') this.do('season');
      else if (e.code === 'KeyY') this.do('film');
      else if (/^(Arrow|Key[WASDQEZXRF]$)/.test(e.code)) this.stopAuto();
    });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());
  }

  // screen-space slide (pixels) -> campus offset, scaled by the zoom
  slide(px, py) {
    const k = this.goal.dist * 0.0018;
    const s = Math.sin(this.goal.yaw), c = Math.cos(this.goal.yaw);
    // screen right = (cos yaw, -sin yaw), screen up = forward (sin yaw, cos yaw)
    this.goal.x += (px * c + py * s) * k;
    this.goal.y += (-px * s + py * c) * k;
  }

  // leave the fixed photo view: carry on from the same spot as an ordinary orbit view
  release() {
    const k = this.fixed;
    if (!k) return;
    this.fixed = null;
    const dx = k.tx - k.x, dy = k.ty - k.y, hor = Math.hypot(dx, dy);
    const v = { x: k.tx, y: k.ty, dist: clamp(Math.hypot(hor, k.h - k.th), ...DIST), yaw: Math.atan2(dx, dy), pitch: clamp(Math.atan2(k.h - k.th, hor), ...PITCH), lift: 0 };
    Object.assign(this.cur, v);
    Object.assign(this.goal, v);
    this.fovGoal = this.baseFov;
  }

  stopAuto() {
    this.release();
    if (this.auto) { this.auto = false; this.labels(); }
  }

  // bar buttons and their keys
  do(what) {
    const g = this.goal;
    if (what !== 'photo' && what !== 'back') this.release();
    if (what === 'back') { this.onAction('back'); return; }
    if (what === 'auto') this.auto = !this.auto;
    else if (what === 'season' || what === 'film') this.onAction(what);
    else if (what === 'in') { g.dist = clamp(g.dist * 0.7, ...DIST); this.stopAuto(); }
    else if (what === 'out') { g.dist = clamp(g.dist * 1.4, ...DIST); this.stopAuto(); }
    else if (what === 'up') { g.pitch = clamp(g.pitch + 0.18, ...PITCH); this.stopAuto(); }
    else if (what === 'down') { g.pitch = clamp(g.pitch - 0.18, ...PITCH); this.stopAuto(); }
    else if (what === 'street') {        // drop to eye level over the view centre, looking ahead
      Object.assign(g, { dist: 14, pitch: 0.08, lift: 0 });
      this.fovGoal = this.baseFov;
      this.stopAuto();
    } else if (what === 'overview') {    // the whole campus from high above
      Object.assign(g, { x: -20, y: -40, dist: 900, pitch: 1.0, lift: 0 });
      this.fovGoal = this.baseFov;
    } else if (what === 'photo') {       // the 1997 aerial photo (reference/1997_백양로_항공사진.jpg): taken ~19 m over the gate with a
      this.stopAuto();                   // normal lens, up 백양로 to 언더우드관 and 대우관 (any other control returns to the orbit view).
      // Camera fitted by least squares to the vertical edges, lines and vanishing points of the unchanged halls,
      // 제1공학관's south-east corner before its 2014 - 2015 wings (solved from the roadview) and 백주년기념관's drum
      // (3.1 px rms on the 2100 px scan, roll 0; issues #82, #83: tools/build_campus.py PHOTO_A)
      this.fixed = { x: -111.0, y: -395.7, h: 44.5, tx: 53.1, ty: 181.4, th: 6.75 };
      this.fovGoal = 32.13;
      this.camera.fov = 32.13;
      this.camera.updateProjectionMatrix();
    }
    this.labels();
  }

  // texts on the bar that show the state (season & film come from the game)
  labels(extra = {}) {
    Object.assign(this, extra);
    const set = (k, t) => { const b = this.tourbar.querySelector(`[data-tour="${k}"]`); if (b) b.textContent = t; };
    set('auto', this.auto ? '자동 회전: 켬' : '자동 회전: 끔');
    if (this.seasonLabel) set('season', `계절: ${this.seasonLabel}`);
    if (this.filmOn !== undefined) set('film', this.filmOn ? '필름: 켬' : '필름: 끔');
    set('back', this.player ? '걷기로 돌아가기' : '처음 화면으로');
  }

  enter({ x, y, yaw, player }) {
    this.active = true;
    this.player = player;
    this.keys.clear();
    this.pointers.clear();
    this.auto = true;
    this.fixed = null;
    this.fovGoal = this.baseFov;
    if (player) {
      // start just above the walker and climb out
      Object.assign(this.cur, { x, y, dist: 20, yaw, pitch: 0.5, lift: 0 });
      Object.assign(this.goal, { x: x * 0.6 - 20 * 0.4, y: y * 0.6 - 60 * 0.4, dist: 520, yaw, pitch: 0.92, lift: 0 });
    } else {
      // from the title card: over the gate, looking up 백양로 like the 1997 aerial photo, then out
      Object.assign(this.cur, { x: -90, y: -330, dist: 140, yaw: 0.24, pitch: 0.32, lift: 0 });
      Object.assign(this.goal, { x: -45, y: -150, dist: 560, yaw: 0.24, pitch: 0.75, lift: 0 });
    }
    this.layer.hidden = false;
    this.tourbar.hidden = false;
    document.body.classList.add('birds');
    this.select(null);
    this.labels();
  }

  exit() {
    this.active = false;
    this.fixed = null;
    this.camera.fov = this.fovGoal = this.baseFov;
    this.camera.near = 0.1;
    this.camera.updateProjectionMatrix();
    this.layer.hidden = true;
    this.bar.hidden = true;
    this.tourbar.hidden = true;
    this.dom.classList.remove('grabbing');
    document.body.classList.remove('birds');
  }

  select(l) {
    this.selected = l;
    this._order = null;
    this.bar.hidden = !l;
    for (const p of this.pins) p.el.classList.toggle('on', p.l === l);
    if (!l) return;
    this.bar.querySelector('b').textContent = l.name;
    this.bar.querySelector('.memory').hidden = !l.photo;
    this.bar.querySelector('.walk').textContent = this.player ? '여기서 걷기' : '여기서 걷기 시작';
    this.goal.x = l.pos[0];
    this.goal.y = l.pos[1];
    this.goal.dist = clamp(this.goal.dist, 90, 210);
    this.goal.pitch = clamp(this.goal.pitch, 0.45, 1.0);
    this.goal.lift = 0;
    this.stopAuto();
  }

  update(dt, player) {
    if (this.fixed) {
      if (this.keys.size || this.held) this.release();
      else {
        const f = this.fixed, c = this.camera;
        c.position.set(f.x, f.h, -f.y);
        c.lookAt(f.tx, f.th, -f.ty);
        if (Math.abs(c.fov - this.fovGoal) > 0.01) { c.fov = this.fovGoal; }
        if (c.near !== 1) c.near = 1;
        c.updateProjectionMatrix();
        c.updateMatrixWorld();
        this.focus.set((f.x + f.tx) / 2, 40, -(f.y + f.ty) / 2);
        if (this.player) { this.player.x = player.x; this.player.y = player.y; }
        this._pins();
        return;
      }
    }
    const g = this.goal, k = this.keys, h = this.held;
    const on = (...codes) => codes.some((c) => k.has(c));
    const fwd = (on('KeyW', 'ArrowUp') ? 1 : 0) - (on('KeyS', 'ArrowDown') ? 1 : 0);
    const turn = (on('KeyA', 'ArrowLeft') ? 1 : 0) - (on('KeyD', 'ArrowRight') ? 1 : 0);
    const side = (on('KeyE') ? 1 : 0) - (on('KeyQ') ? 1 : 0);
    const zoom = (on('KeyX', 'Minus', 'NumpadSubtract', 'PageDown') || h === 'out' ? 1 : 0) - (on('KeyZ', 'Equal', 'NumpadAdd', 'PageUp') || h === 'in' ? 1 : 0);
    const tilt = (on('KeyR') || h === 'up' ? 1 : 0) - (on('KeyF') || h === 'down' ? 1 : 0);
    const fast = on('ShiftLeft', 'ShiftRight') ? 2.4 : 1;
    if (this.auto) g.yaw += dt * 0.06;
    g.yaw += turn * 1.3 * dt;
    // forward = away from the camera, over the ground
    const move = (6 + g.dist * 0.45) * fast * dt;
    const fx = Math.sin(g.yaw), fy = Math.cos(g.yaw);
    g.x += (fx * fwd + fy * side) * move;
    g.y += (fy * fwd - fx * side) * move;
    g.dist = clamp(g.dist * (1 + zoom * 1.2 * dt), ...DIST);
    g.pitch = clamp(g.pitch + tilt * 0.7 * dt, ...PITCH);
    g.x = clamp(g.x, BOUNDS.x0, BOUNDS.x1);
    g.y = clamp(g.y, BOUNDS.y0, BOUNDS.y1);

    // smooth follow
    const c = this.cur, f = 1 - Math.exp(-dt * 3.2), fa = 1 - Math.exp(-dt * 6);
    c.x += (g.x - c.x) * f;
    c.y += (g.y - c.y) * f;
    c.dist += (g.dist - c.dist) * f;
    c.pitch += (g.pitch - c.pitch) * fa;
    c.yaw += wrapAngle(g.yaw - c.yaw) * fa;
    c.lift += ((g.lift || 0) - (c.lift || 0)) * f;
    if (Math.abs(this.camera.fov - this.fovGoal) > 0.01) {
      this.camera.fov += (this.fovGoal - this.camera.fov) * f;
      this.camera.updateProjectionMatrix();
    }

    const gh = this.heightAt(c.x, c.y);
    const hor = Math.cos(c.pitch) * c.dist;
    const cx = c.x - Math.sin(c.yaw) * hor, cy = c.y - Math.cos(c.yaw) * hor;
    // never inside the ground, a roof or a tree-top: stay above whatever is below the camera
    const floor = Math.max(this.heightAt(cx, cy), this.surfaceAt(cx, cy)) + 1.7;
    const ch = Math.max(gh + Math.sin(c.pitch) * c.dist, floor);
    // look a little above the ground near street level so the view runs along the street, not into it
    const lookUp = clamp(14 - c.dist, 0, 8) * 0.18;
    this.camera.position.set(cx, ch, -cy);
    this.camera.lookAt(c.x, gh + 1.2 + lookUp + (c.lift || 0), -c.y);
    const near = c.dist < 60 ? 0.15 : 1.0;
    if (this.camera.near !== near) { this.camera.near = near; this.camera.updateProjectionMatrix(); }
    this.camera.updateMatrixWorld();
    this.focus.set(c.x, gh, -c.y);
    if (this.player) { this.player.x = player.x; this.player.y = player.y; }
    this._pins();
  }

  // heading-up minimap angle (ui.drawMinimap's convention)
  get mapYaw() { return -this.cur.yaw; }

  _pins() {
    const W = innerWidth, H = innerHeight, v = this._v;
    const place = (el, x, y, hgt) => {
      v.set(x, hgt, -y).project(this.camera);
      if (v.z > 1 || v.z < -1 || Math.abs(v.x) > 1.1 || Math.abs(v.y) > 1.1) { el.style.display = 'none'; return; }
      el.style.display = '';
      el.style.transform = `translate(${((v.x + 1) / 2) * W}px, ${((1 - v.y) / 2) * H}px)`;
    };
    const scale = clamp(380 / this.cur.dist, 0.75, 1.15);
    this.layer.style.setProperty('--pin-scale', String(scale));
    const cam = this.camera.position;
    // place pins in priority order (selected first, then the list order) and hide any that would overlap
    const order = (this._order ||= [...this.pins].sort((a, b) => (b.l === this.selected) - (a.l === this.selected) || a.prio - b.prio));
    const boxes = this._boxes ||= [];
    boxes.length = 0;
    for (const p of order) {
      if (p.h === null) p.h = this.heightAt(p.l.pos[0], p.l.pos[1]) + 24;
      // at street level only nearby places get a pin
      const far = Math.hypot(p.l.pos[0] - cam.x, p.l.pos[1] + cam.z) > (p.bld ? Math.max(170, this.cur.dist * 1.8) : Math.max(260, this.cur.dist * 3));
      if (far && p.l !== this.selected) { p.el.style.display = 'none'; continue; }
      place(p.el, p.l.pos[0], p.l.pos[1], p.h);
      if (p.el.style.display === 'none') continue;
      const sx = ((v.x + 1) / 2) * W, sy = ((1 - v.y) / 2) * H;
      const w = (p.l.name.length * (p.bld ? 12 : 15) + 22) * scale, h = (p.bld ? 24 : 30) * scale;
      const box = [sx - w / 2, sy - 10 - h, sx + w / 2, sy - 10];
      if (boxes.some((q) => box[0] < q[2] + 4 && box[2] > q[0] - 4 && box[1] < q[3] + 2 && box[3] > q[1] - 2)) {
        p.el.style.display = 'none';
        continue;
      }
      boxes.push(box);
    }
    if (this.player) place(this.me, this.player.x, this.player.y, this.heightAt(this.player.x, this.player.y) + 6);
    else this.me.style.display = 'none';
  }
}
