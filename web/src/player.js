// Third-person walker in the manner of sim-office (office/engine/movement.js + camera.js):
// ↑↓ / W S walk forward and back, ← → / A D turn, Shift runs; the camera follows behind and above.
// Mouse drag swings the camera round (it settles back behind you when you walk), the wheel zooms.
// Dragging up (or PageUp) looks up: the camera sinks behind the walker and tips up to the roofs, the statues and the
// sky; dragging down (PageDown) brings it level and then up over the walker. The look up settles back as you walk.
// The touch stick (touch.js) is camera-relative instead: push it the way you want to go on screen and the
// walker turns that way; the camera keeps its direction and only drifts back behind you while you head away from it.
// Collisions: building footprints and circles (trees, lamps, statues, people); ground follows the
// terrain, the 백양로 curbs and the amphitheater terraces through a BVH raycast.
import * as THREE from 'three';
import { computeBoundsTree, acceleratedRaycast } from 'three-mesh-bvh';
import { locomotion } from './characters.js';
import { clamp, closestOnSegment, wrapAngle } from './util.js';

THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;

const RADIUS = 0.32, STEP = 0.55;
// wall rays, above the feet: the low ones catch kerbs, plinths, planter and flower-bed edges down to ankle height
// (0.1 m: stone edgings and shallow bases lower than 20 cm no longer let the feet through), the low ends of the stair
// side walls; a face they hit is still a step when the walkable ground right behind it rises to the ray
const WALL_RAY_H = [0.1, 0.2, 0.42, 0.65, 1.3];
const LOW_RAY = 0.6;
export const WALK = 2.4, RUN = 6.2, TURN = 2.3;
// The camera's one vertical axis, cam.lift: 0 is the usual view from behind and a little above; up to LIFT_MAX the
// camera climbs to look down on the walker; below 0 the view looks up: by LOOK_UP the camera has sunk behind the
// walker to CAM_LOW over the ground and the view has tipped up PITCH_MAX past its level look, about 70° above the
// horizon in all (the 12 m 독수리상 from its plinth, a five-storey roof line from across the road, clouds, the sun).
// The walker sits low in the frame while the view climbs and drops out of it at the top of the range.
export const LIFT_MAX = 1.1, LOOK_UP = -1;
const PITCH_MAX = 1.05, CAM_LOW = 0.5, LOOK_KEY = 1.1, LOOK_BACK = 1.0;
// how far down the camera has sunk at a look up of u (0..1): all the way by u = 0.6, quickly at first
const sink = (u) => { const t = Math.min(1, u / 0.6); return 1 - (1 - t) * (1 - t); };

// numeric grid-cell key (no string building in the per-frame lookups); unique for |i|, |j| < 32768
const cellKey = (i, j) => (i + 32768) * 65536 + (j + 32768);

export class Colliders {
  constructor(cell = 24) {
    this.cell = cell;
    this.grid = new Map();
    this._near = [];
    this._stamp = 0;
  }
  _put(o, minx, miny, maxx, maxy) {
    const c = this.cell;
    for (let i = Math.floor(minx / c); i <= Math.floor(maxx / c); i++)
      for (let j = Math.floor(miny / c); j <= Math.floor(maxy / c); j++) {
        const k = cellKey(i, j);
        if (!this.grid.has(k)) this.grid.set(k, []);
        this.grid.get(k).push(o);
      }
  }
  addPolygon(pts) {   // campus frame [[x,y],...]
    let minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9;
    for (const [x, y] of pts) { minx = Math.min(minx, x); maxx = Math.max(maxx, x); miny = Math.min(miny, y); maxy = Math.max(maxy, y); }
    this._put({ type: 'poly', pts }, minx, miny, maxx, maxy);
  }
  addCircle(x, y, r) {
    this._put({ type: 'circle', x, y, r }, x - r, y - r, x + r, y + r);
  }
  // colliders in the 3x3 cells round (x, y), each once (reused array: valid until the next call)
  near(x, y) {
    const c = this.cell, ci = Math.floor(x / c), cj = Math.floor(y / c);
    const res = this._near, stamp = ++this._stamp;
    res.length = 0;
    for (let i = -1; i <= 1; i++)
      for (let j = -1; j <= 1; j++) {
        const a = this.grid.get(cellKey(ci + i, cj + j));
        if (!a) continue;
        for (const o of a) if (o.seen !== stamp) { o.seen = stamp; res.push(o); }
      }
    return res;
  }
  insideBuilding(x, y) {
    const a = this.grid.get(cellKey(Math.floor(x / this.cell), Math.floor(y / this.cell)));
    return !!a && a.some((o) => o.type === 'poly' && pointInPoly(x, y, o.pts));
  }
  // push a circle (x,y,r) out of every collider (and the moving circles); returns corrected [x,y]
  resolve(x, y, r, movers = []) {
    // the push-outs move the circle by centimetres: one neighbourhood (±1 cell = 24 m) serves all three passes
    const near = this.near(x, y);
    for (let it = 0; it < 3; it++) {
      for (const o of near) {
        if (o.type === 'circle') {
          const dx = x - o.x, dy = y - o.y, d = Math.hypot(dx, dy), m = o.r + r;
          if (d < m && d > 1e-6) { x = o.x + dx / d * m; y = o.y + dy / d * m; }
        } else {
          const p = o.pts;
          const inside = pointInPoly(x, y, p);
          let best = 1e9, bx = 0, by = 0;
          for (let i = 0; i < p.length; i++) {
            const [ax, ay] = p[i], [cx, cy] = p[(i + 1) % p.length];
            const [qx, qy, d] = closestOnSegment(x, y, ax, ay, cx, cy);
            if (d < best) { best = d; bx = qx; by = qy; }
          }
          if (inside) {
            const dx = bx - x, dy = by - y, d = Math.hypot(dx, dy) || 1;
            x = bx + dx / d * r; y = by + dy / d * r;
          } else if (best < r) {
            const dx = x - bx, dy = y - by, d = best || 1;
            x = bx + dx / d * r; y = by + dy / d * r;
          }
        }
      }
      for (const m of movers) {
        const dx = x - m.x, dy = y - m.y, d = Math.hypot(dx, dy), mm = m.r + r;
        if (d < mm && d > 1e-6) { x = m.x + dx / d * mm; y = m.y + dy / d * mm; }
      }
    }
    return [x, y];
  }
}

export function pointInPoly(x, y, p) {
  let c = false;
  for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
    const [xi, yi] = p[i], [xj, yj] = p[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c;
  }
  return c;
}

export class Player {
  constructor(camera, dom, colliders, walkables, hf, actor) {
    this.camera = camera;
    this.dom = dom;
    this.col = colliders;
    this.walk = walkables;
    this.hf = hf;
    this.setActor(actor);
    this.vy = 0;
    this.speed = 0;
    this.heading = 0;                 // facing: forward = (sin h, cos h) in three's XZ
    this.keys = new Set();
    this.enabled = false;
    this.stick = new THREE.Vector2();
    this.movers = [];
    this.ray = new THREE.Raycaster();
    this.ray.firstHitOnly = true;
    this.walls = [];                  // static building / landmark meshes (with BVHs): columns, porches, stair walls the footprints miss
    this.wallRays = WALL_RAY_H;
    this.wray = new THREE.Raycaster();
    this.wray.firstHitOnly = true;
    this._wo = new THREE.Vector3(); this._wd = new THREE.Vector3(); this._wn = new THREE.Vector3();
    this.down = new THREE.Vector3(0, -1, 0);
    this._from = new THREE.Vector3();
    this._want = new THREE.Vector3(); this._head = new THREE.Vector3(); this._q = new THREE.Vector3(); this._look = new THREE.Vector3();
    // camera rig
    // up: the look up actually shown (follows -lift, smoothed like the camera's position)
    this.cam = { pos: new THREE.Vector3(), look: new THREE.Vector3(), ready: false, orbit: 0, lift: 0, up: 0, dist: 5.4, drag: null };
    addEventListener('keydown', (e) => { if (!/INPUT|TEXTAREA/.test(e.target.tagName)) this.keys.add(e.code); if (/Arrow|Space|Page(Up|Down)/.test(e.code) && this.enabled) e.preventDefault(); });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());
    dom.addEventListener('pointerdown', (e) => {
      if (!this.enabled || e.target !== dom || e.pointerType === 'touch') return;   // touch: touch.js
      this.cam.drag = { id: e.pointerId, x: e.clientX, y: e.clientY };
      dom.setPointerCapture(e.pointerId);
    });
    dom.addEventListener('pointermove', (e) => {
      const d = this.cam.drag;
      if (!d || d.id !== e.pointerId) return;
      this.cam.orbit -= (e.clientX - d.x) * 0.006;
      this.cam.lift = clamp(this.cam.lift + (e.clientY - d.y) * 0.004, LOOK_UP, LIFT_MAX);
      d.x = e.clientX; d.y = e.clientY;
    });
    const up = () => { this.cam.drag = null; };
    dom.addEventListener('pointerup', up);
    dom.addEventListener('pointercancel', up);
    dom.addEventListener('wheel', (e) => {
      if (!this.enabled) return;
      e.preventDefault();
      this.cam.dist = clamp(this.cam.dist * (e.deltaY > 0 ? 1.1 : 0.9), 2.4, 16);
    }, { passive: false });
  }

  setActor(actor) {
    if (this.actor) {
      const old = this.actor.holder;
      actor.holder.position.copy(old.position);
      old.parent?.remove(old);
    }
    this.actor = actor;
    this.pos = actor.holder.position;
  }

  // campus (x east, y north) placement; yaw: view direction with forward = (-sin yaw, -cos yaw) in three (0 = north)
  teleport(x, y, yaw = null) {
    const h = this.groundAt(x, -y, 400);
    this.pos.set(x, h ?? this.hf.height(x, y), -y);
    this.vy = 0;
    if (yaw !== null) this.heading = yaw + Math.PI;
    this.actor.holder.rotation.y = this.heading;
    this.cam.ready = false;
    this.cam.orbit = 0;
    this.cam.lift = Math.max(0, this.cam.lift);      // arrive looking level
  }

  // push the walker out of the walls of the real meshes: rays round a circle from ankle to chest height, so columns,
  // porches, the side walls of stairs and low ledges block like the footprints do; stair risers are let through
  pushFromWalls(x, y, z) {
    const R = RADIUS + 0.05, o = this._wo, d = this._wd, n = this._wn, ray = this.wray;
    ray.far = R;
    // only the meshes within reach (their world bounding spheres are cached on first use)
    if (!this._wsph) {
      this._wsph = this.walls.map((m) => { m.updateWorldMatrix(true, false); if (!m.geometry.boundingSphere) m.geometry.computeBoundingSphere(); return m.geometry.boundingSphere.clone().applyMatrix4(m.matrixWorld); });
    }
    const near = this._wnear || (this._wnear = []);
    near.length = 0;
    for (let i = 0; i < this.walls.length; i++) {
      const sp = this._wsph[i], dx = sp.center.x - x, dz = sp.center.z - z, dy = sp.center.y - y;
      if (dx * dx + dy * dy + dz * dz < (sp.radius + 1) * (sp.radius + 1)) near.push(this.walls[i]);
    }
    if (!near.length) return [x, z];
    for (const h of this.wallRays) {
      for (let k = 0; k < 8; k++) {
        const a = k * Math.PI / 4;
        d.set(Math.cos(a), 0, Math.sin(a));
        ray.set(o.set(x, y + h, z), d);
        const hit = ray.intersectObjects(near, false)[0];
        if (!hit || hit.distance >= R) continue;
        n.copy(hit.face.normal).transformDirection(hit.object.matrixWorld);
        if (Math.abs(n.y) > 0.6) continue;         // floors and slopes are the ground's business
        if (h < LOW_RAY && this.stepBehind(hit.point.x, hit.point.z, d.x, d.z, y + h, y)) continue;
        x -= d.x * (R - hit.distance); z -= d.z * (R - hit.distance);
      }
    }
    return [x, z];
  }

  // a low face is a step (a stair riser, a kerb onto a walked surface) when the walkable ground just behind it comes
  // up to the ray that hit it, within a step of the feet; a planter or a flower-bed edge has only the lawn behind it
  stepBehind(px, pz, dx, dz, ry, feet) {
    this.ray.set(this._from.set(px + dx * 0.08, ry + 0.6, pz + dz * 0.08), this.down);
    this.ray.far = 0.75;
    const hits = this.ray.intersectObjects(this.walk, false);
    return hits.length > 0 && hits[0].point.y > ry - 0.06 && hits[0].point.y < feet + STEP;
  }

  groundAt(x, z, from = null) {
    const top = from ?? this.pos.y + STEP;
    this.ray.set(this._from.set(x, top, z), this.down);
    this.ray.far = from ? 1000 : STEP + 60;
    const hits = this.ray.intersectObjects(this.walk, false);
    return hits.length ? hits[0].point.y : null;
  }

  input() {
    const k = this.keys;
    let fwd = 0, turn = 0;
    if (k.has('ArrowUp') || k.has('KeyW')) fwd += 1;
    if (k.has('ArrowDown') || k.has('KeyS')) fwd -= 1;
    if (k.has('ArrowLeft') || k.has('KeyA')) turn += 1;
    if (k.has('ArrowRight') || k.has('KeyD')) turn -= 1;
    const run = k.has('ShiftLeft') || k.has('ShiftRight');
    const tilt = (k.has('PageDown') ? 1 : 0) - (k.has('PageUp') ? 1 : 0);     // + = down, as a downward drag
    const m = this.stick.length();
    if (!fwd && !turn && m > 0.15) {
      // stick: the screen direction pushed (0 = straight ahead, + = left), relative to where the camera looks
      return { fwd: 0, turn: 0, run: m > 0.9, tilt, stick: { rel: Math.atan2(-this.stick.x, -this.stick.y), m: Math.min(1, (m - 0.15) / 0.75) } };
    }
    return { fwd: clamp(fwd, -1, 1), turn: clamp(turn, -1, 1), run, tilt };
  }

  update(dt) {
    const inp = this.enabled ? this.input() : { fwd: 0, turn: 0, run: false };
    if (inp.tilt) {
      const c = this.cam;
      if (!this._tilt) this._tiltSide = Math.sign(Math.round(c.lift * 100));
      const l = clamp(c.lift + inp.tilt * LOOK_KEY * dt, LOOK_UP, LIFT_MAX);
      c.lift = this._tiltSide * l < 0 ? 0 : l;      // a held key stops at level on its way across (press again to go on)
    }
    this._tilt = inp.tilt;
    if (inp.stick) {
      // turn quickly towards the pushed direction; the camera keeps its own direction meanwhile
      const c = this.cam, want = this.heading + c.orbit + inp.stick.rel;
      const d = wrapAngle(want - this.heading) * Math.min(1, dt * 9);
      this.heading += d;
      c.orbit = wrapAngle(c.orbit - d);
      inp.fwd = inp.stick.m;
      // drift back behind the walker only while walking away from the camera (never while coming towards it)
      inp.recenter = 1.3 * Math.max(0, Math.cos(inp.stick.rel));
    }
    this.heading += inp.turn * TURN * dt;
    const target = inp.fwd * (inp.run && inp.fwd > 0 ? RUN : WALK * (inp.fwd < 0 ? 0.6 : 1));
    this.speed += (target - this.speed) * Math.min(1, dt * 10);
    if (Math.abs(this.speed) < 0.05 && !target) this.speed = 0;
    let nx = this.pos.x + Math.sin(this.heading) * this.speed * dt;
    let nz = this.pos.z + Math.cos(this.heading) * this.speed * dt;
    if (this.speed) {
      const [cx, cy] = this.col.resolve(nx, -nz, RADIUS, this.movers);
      nx = cx; nz = -cy;
      if (this.walls.length) { const [wx, wz] = this.pushFromWalls(nx, this.pos.y, nz); nx = wx; nz = wz; }
    }
    // ground: step up curbs and terraces, fall down slopes
    this.vy -= 14 * dt;
    let ny = this.pos.y + this.vy * dt;
    const g = this.groundAt(nx, nz) ?? this.hf.height(nx, -nz);
    if (ny <= g + 0.02 || (this.vy <= 0 && ny < g + 0.35)) { ny = g; this.vy = 0; }
    this.pos.set(nx, ny, nz);
    this.actor.holder.rotation.y = this.heading;
    locomotion(this.actor, this.speed, WALK + 0.5);
    this.actor.mixer.update(dt);
    this.updateCamera(dt, inp);
  }

  updateCamera(dt, inp = { fwd: 0, turn: 0 }) {
    const c = this.cam, p = this.pos;
    // walking: the camera swings back behind you and a look up comes back to level (a camera raised to look down stays)
    if (!c.drag && (inp.fwd || inp.turn)) {
      c.orbit = wrapAngle(c.orbit);
      c.orbit *= Math.exp(-dt * (inp.recenter ?? 1.6));
      if (c.lift < 0 && !inp.tilt) c.lift *= Math.exp(-dt * LOOK_BACK);
    }
    const a = this.heading + c.orbit;
    const el = 0.36 + Math.max(0, c.lift) * 0.5, up = Math.max(0, -c.lift), s = sink(up);
    const back = c.dist * Math.cos(el), high = 1.25 + c.dist * Math.sin(el);
    const want = this._want.set(p.x - Math.sin(a) * back, p.y + high + (CAM_LOW - high) * s, p.z - Math.cos(a) * back);
    // keep the camera out of buildings: walk the line from the head and stop before a wall
    const head = this._head.set(p.x, p.y + 1.5, p.z), q = this._q;
    const steps = 12;
    for (let i = 1; i <= steps; i++) {
      q.lerpVectors(head, want, i / steps);
      if (this.col.insideBuilding(q.x, -q.z)) { want.lerpVectors(head, want, Math.max(0, (i - 1.5) / steps)); want.y += 0.6; break; }
    }
    // over the terrain; sunk low for a look up, also over the steps, kerbs and terraces walked on behind you
    let gy = this.hf.height(want.x, -want.z), floor = 0.6 - 0.3 * s;
    if (s > 0) {
      const w = this.groundAt(want.x, want.z, Math.max(want.y, p.y) + 2.5);
      if (w !== null && w > gy) gy = w;
      // and over the roof of a car coming up to it or stopped behind you, not inside it (people's circles are 0.3)
      for (const m of this.movers) if (m.r > 0.6 && Math.hypot(want.x - m.x, want.z + m.y) < m.r + 1) { floor = Math.max(floor, 1.9); break; }
    }
    if (want.y < gy + floor) want.y = gy + floor;
    const look = this._look.set(p.x + Math.sin(this.heading) * 1.2, p.y + 1.45, p.z + Math.cos(this.heading) * 1.2);
    const k = c.ready ? 1 - Math.exp(-dt * 4.5) : 1;
    c.ready = true;
    c.pos.lerp(want, k);
    c.look.lerp(look, k);
    c.up += (up - c.up) * k;
    this.camera.position.copy(c.pos);
    this.camera.lookAt(c.look);
    // the look up: tip the view about its own level side axis, past where it looks at the walker
    if (c.up > 1e-4) this.camera.rotateX(c.up * PITCH_MAX);
  }

  // the walker's body on screen, head to knees, in CSS px [left, top, right, bottom] (for the HUD to keep clear of it)
  screenBox(camera, out = this._sbox || (this._sbox = [0, 0, 0, 0])) {
    const v = this._sb || (this._sb = new THREE.Vector3());
    v.set(this.pos.x, this.pos.y + 1.75, this.pos.z).project(camera);
    const x = (v.x + 1) / 2 * innerWidth, top = (1 - v.y) / 2 * innerHeight;
    v.set(this.pos.x, this.pos.y + 0.45, this.pos.z).project(camera);
    const bottom = (1 - v.y) / 2 * innerHeight, half = (bottom - top) / 1.3 * 0.3;     // 0.6 m wide
    out[0] = x - half; out[1] = top; out[2] = x + half; out[3] = bottom;
    return out;
  }

  // campus frame helpers
  get x() { return this.pos.x; }
  get y() { return -this.pos.z; }
  // view direction for the heading-up minimap (old first-person convention: forward = (-sin yaw, -cos yaw))
  get yaw() { return this.heading + this.cam.orbit + Math.PI; }
}
