// Third-person walker in the manner of sim-office (office/engine/movement.js + camera.js):
// ↑↓ / W S walk forward and back, ← → / A D turn, Shift runs; the camera follows behind and above.
// Mouse drag swings the camera round (it settles back behind you when you walk), the wheel zooms.
// Dragging up (or PageUp) looks up: the camera sinks behind the walker and tips up to the roofs, the statues and the
// sky; dragging down (PageDown) brings it level and then up over the walker. The look up settles back as you walk.
// The touch stick (touch.js) is camera-relative instead: push it the way you want to go on screen and the
// walker turns that way; the camera keeps its direction and only drifts back behind you while you head away from it.
// Collisions: building footprints and circles (trees, lamps, statues, people); ground follows the
// terrain, the 백양로 curbs and the amphitheater terraces through a BVH raycast.
// First person (V, the HUD button, the wheel or a pinch on past the closest view): the camera in the walker's eyes,
// at 0.93 of their height over the ground they walk on. A drag looks round and up and down; the keys turn the body
// and the view together, and the body comes round to where you look as you set off. The walker's own body is not
// drawn (its shadow still is); the head bobs a little with the steps of the walk clip.
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
const DIST_MIN = 2.4, DIST_MAX = 16;
// First person. The eye is on the walker's own axis (never nearer a wall than the walker's circle: the near plane's
// corners are 0.19 m out), EYE of their height up. cam.lift is the vertical axis here too: the view tips FP_UP rad
// up at lift -1 and FP_DOWN rad down per unit of lift (72 degrees down at LIFT_MAX).
const EYE = 0.93, FP_UP = 1.3, FP_DOWN = 1.14;
// walking, a steep look comes back slowly as far as FP_EASY_UP / FP_EASY_DOWN rad (you see where you go); less
// than that stays where you left it: looking up at the trees and the roofs as you walk is what the view is for
const FP_EASY_UP = 0.45, FP_EASY_DOWN = 0.3, FP_EASY_RATE = 0.8;
// seconds into the eyes (from behind the walker; from the tour's or a scene's camera) and back out
const FP_IN = 0.35, FP_SWOOP = 0.8, FP_OUT = 0.3;
const FP_BODY = 0.45;    // the body is not drawn while the camera is this close to the eyes (m)
// the head bob: the walk clip's own rise and fall of the head (6 cm from top to bottom walking, 7 cm running, lowest
// as a foot lands), this share of it: 1.3 cm walking, 2 cm running. BOB_MAX: never more than this off the middle
const BOB_WALK = 0.25, BOB_RUN = 0.42, BOB_MAX = 0.02;
const VIEW_LAYER = 0;    // (the hidden body leaves the layer the view draws; shadows.js draws its shadow from layer 1)
const eyeHeight = (a) => (a.id?.startsWith('woman') ? 1.61 : 1.73) * (a.tall || 1) * EYE;
const fpPitch = (lift) => (lift < 0 ? -lift * FP_UP : -lift * FP_DOWN);
const fpLift = (pitch) => (pitch > 0 ? -pitch / FP_UP : -pitch / FP_DOWN);
const smooth = (u) => u * u * (3 - 2 * u);

// numeric grid-cell key (no string building in the per-frame lookups); unique for |i|, |j| < 32768
const cellKey = (i, j) => (i + 32768) * 65536 + (j + 32768);

// The walker's walls (the halls' outlines, campus.json colliders, circles round trunks, lamps, shrubs, benches) on a
// grid of 8 m cells. A push-out reads only the cells under the circle and a margin round it, and passes by every
// collider whose box it does not touch. (The 3 x 3 cells of 24 m it read before held 1,181 colliders at 언더우드관's
// front: 40 µs a push-out, and 290 µs at the gate while the thin walls round 연세로's walks stood there.)
const MARGIN = 1.0;       // round the circle, for the three passes of a push-out (they move it centimetres)
// Colliders.walkOut: the grid it walks (m), how far away counts as out (the largest shut-in lawn, by 정문, is 16 x 17 m),
// how much ground round it does too (m²; the largest is 180), how far it looks for another spot
const OUT_STEP = 0.5, OUT_REACH = 30, OUT_AREA = 2500, OUT_SEARCH = 60;
export class Colliders {
  constructor(cell = 8) {
    this.cell = cell;
    this.grid = new Map();
    this._near = [];
    this._stamp = 0;
  }
  _put(o, minx, miny, maxx, maxy) {
    const c = this.cell;
    Object.assign(o, { minx, miny, maxx, maxy });
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
  // colliders in the cells that meet the square (x, y) ± m, each once (reused array: valid until the next call)
  near(x, y, m = this.cell) {
    const c = this.cell, i0 = Math.floor((x - m) / c), i1 = Math.floor((x + m) / c), j0 = Math.floor((y - m) / c), j1 = Math.floor((y + m) / c);
    const res = this._near, stamp = ++this._stamp;
    res.length = 0;
    for (let i = i0; i <= i1; i++)
      for (let j = j0; j <= j1; j++) {
        const a = this.grid.get(cellKey(i, j));
        if (!a) continue;
        for (const o of a) if (o.seen !== stamp) { o.seen = stamp; res.push(o); }
      }
    return res;
  }
  insideBuilding(x, y) {
    const a = this.grid.get(cellKey(Math.floor(x / this.cell), Math.floor(y / this.cell)));
    return !!a && a.some((o) => o.type === 'poly' && pointInPoly(x, y, o.pts));
  }
  // whether a circle (x, y, r) touches no collider
  clear(x, y, r = RADIUS) {
    for (const o of this.near(x, y, r + MARGIN)) {
      if (x + r < o.minx || x - r > o.maxx || y + r < o.miny || y - r > o.maxy) continue;
      if (o.type === 'circle') {
        if (Math.hypot(x - o.x, y - o.y) < o.r + r) return false;
      } else {
        const p = o.pts;
        if (pointInPoly(x, y, p)) return false;
        for (let i = 0; i < p.length; i++) {
          const [ax, ay] = p[i], [bx, by] = p[(i + 1) % p.length];
          if (closestOnSegment(x, y, ax, ay, bx, by)[2] < r) return false;
        }
      }
    }
    return true;
  }
  // A spot to put the walker down at (x, y) from which it can walk away. Where the walker is put down (a pin of the
  // bird's eye view, the map, the start list) can lie among plantings no walker gets into: the parterres of
  // 언더우드관's and 연희관's gardens, closed round by their boxwood edging; the 진달래동산 round 용재관, whose azaleas
  // stand closer than the walker is wide, with pockets of a couple of metres between them. Put down there, it could
  // not get out. So: a walk over a grid of OUT_STEP squares, from the spot through the gaps the walker fits through,
  // until it is OUT_REACH m away (or has OUT_AREA m² round it); if it never gets there, the nearest spot it does
  // from. shut(x, y): where the walker is not put down besides (main.js: under a hall's or a landmark's roof, inside
  // walls the outlines miss); asked of the spot only, not along the way out (a ray each: too slow for the walk).
  walkOut(x, y, r = RADIUS, shut = null) {
    [x, y] = this.resolve(x, y, r + 0.02);
    const open = (px, py) => this.clear(px, py, r) && !shut?.(px, py);
    const tried = new Set();                          // grid squares round (x, y) already found shut in
    const key = (i, j) => (i + 4096) * 8192 + (j + 4096);
    const escapes = (sx, sy) => {
      const seen = new Set(), qi = [0], qj = [0];
      seen.add(key(0, 0));
      const max = OUT_AREA / (OUT_STEP * OUT_STEP), far = (OUT_REACH / OUT_STEP) ** 2;
      for (let h = 0; h < qi.length; h++) {
        if (qi.length > max) return true;
        for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const i = qi[h] + di, j = qj[h] + dj, k = key(i, j);
          if (seen.has(k) || !this.clear(sx + i * OUT_STEP, sy + j * OUT_STEP, r)) continue;
          if (i * i + j * j >= far) return true;
          seen.add(k); qi.push(i); qj.push(j);
        }
      }
      // shut in: remember its squares (on the search grid round the first spot)
      for (let h = 0; h < qi.length; h++) tried.add(key(Math.round((sx - x) / OUT_STEP) + qi[h], Math.round((sy - y) / OUT_STEP) + qj[h]));
      return false;
    };
    if (open(x, y) && escapes(x, y)) return [x, y];
    // rings outwards from the spot, nearest first
    for (let d = OUT_STEP; d <= OUT_SEARCH; d += OUT_STEP) {
      const n = Math.max(8, Math.ceil(2 * Math.PI * d / OUT_STEP));
      for (let k = 0; k < n; k++) {
        const a = k * 2 * Math.PI / n, cx = x + d * Math.cos(a), cy = y + d * Math.sin(a);
        if (tried.has(key(Math.round((cx - x) / OUT_STEP), Math.round((cy - y) / OUT_STEP))) || !open(cx, cy)) continue;
        if (escapes(cx, cy)) return [cx, cy];
      }
    }
    return [x, y];
  }
  // push a circle (x,y,r) out of every collider (and the moving circles); returns corrected [x,y]
  resolve(x, y, r, movers = []) {
    // one neighbourhood serves the three passes, but where a push has moved the circle out of it (out of a hall's
    // inside, across its floor) the cells there are read again
    const m = r + MARGIN;
    let qx = x, qy = y, near = this.near(x, y, m);
    for (let it = 0; it < 3; it++) {
      if (Math.abs(x - qx) > MARGIN || Math.abs(y - qy) > MARGIN) { qx = x; qy = y; near = this.near(x, y, m); }
      for (const o of near) {
        if (x + r < o.minx || x - r > o.maxx || y + r < o.miny || y - r > o.maxy) continue;
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
    this.lift = null;                 // (x, y) -> metres the ground stands over the terrain there (curbs.js lift)
    this.setActor(actor);
    this.vy = 0;
    this.speed = 0;
    this.heading = 0;                 // facing: forward = (sin h, cos h) in three's XZ
    this.keys = new Set();
    this.enabled = false;
    // a short scene that moves the walker itself (birthday.js): while true, update() leaves the walker, its clip and
    // its mixer to the scene and only runs the camera
    this.scripted = false;
    // {pos, look, k?}: the camera eases to this view instead of following behind (k = 1 sets it at once)
    this.camOverride = null;
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
    this._eye = new THREE.Vector3(); this._eq = new THREE.Quaternion(); this._eul = new THREE.Euler(0, 0, 0, 'YXZ');
    this.fpv = false;                 // first person chosen (setFpv)
    this.onView = null;               // (fpv) => {}: the view was changed (V, the button, the wheel, a pinch)
    // camera rig
    // up: the look up actually shown (follows -lift, smoothed like the camera's position)
    // fp: how far the camera is into the walker's eyes (0 = behind the walker, 1 = first person), fpT: seconds the way
    // in takes, stale: the rig behind was not kept up (all the way in); eyeY: the eye's height, eased over kerbs;
    // bob, hop: the head bob and a shot's hop (hoops.js); aim: a point the first-person view turns to (a shot's
    // basket); set: where the camera was left last frame
    this.cam = { pos: new THREE.Vector3(), look: new THREE.Vector3(), ready: false, orbit: 0, lift: 0, up: 0, dist: 5.4, drag: null,
      fp: 0, fpT: FP_IN, stale: false, eyeY: null, bob: 0, headAvg: null, hop: 0, aim: null, set: new THREE.Vector3() };
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
      const dy = Math.abs(e.deltaY) * (e.deltaMode === 1 ? 33 : e.deltaMode === 2 ? 400 : 1);
      this.zoomBy(e.deltaY > 0 ? 1.1 : 0.9, clamp(dy / 200, 0.05, 0.5));     // (two notches on past the end)
    }, { passive: false });
  }

  setActor(actor) {
    if (this.actor) {
      const old = this.actor.holder;
      actor.holder.position.copy(old.position);
      old.parent?.remove(old);
      this.showBody(true);
    }
    this.actor = actor;
    this.pos = actor.holder.position;
    this.eyeH = eyeHeight(actor);
    this.headBone = actor.root.getObjectByName('Head') || null;
    if (this.cam) this.cam.headAvg = null;
    // first person: one more ring of wall rays at the eyes (a sill, a pilaster or a rail the footprint leaves out)
    this.wallRaysFp = [...WALL_RAY_H, this.eyeH];
  }

  // first person on / off (the camera eases in and out: updateCamera)
  setFpv(on) {
    on = !!on;
    if (on === this.fpv) return;
    this.fpv = on;
    this._push = 0;
    this.onView?.(on);
  }

  // the wheel and the pinch: f < 1 comes closer, f > 1 goes farther. Pushing on past the closest view goes into the
  // walker's eyes, pulling back comes out behind them again. push: how much of that push this step is (1 = enough)
  zoomBy(f, push = 1) {
    const c = this.cam;
    if (this.fpv) {
      this._push = f > 1 ? (this._push || 0) + push : 0;
      if (this._push >= 1) { c.dist = DIST_MIN; this.setFpv(false); }
      return;
    }
    if (f < 1 && c.dist <= DIST_MIN + 1e-3) {
      this._push = (this._push || 0) + push;
      if (this._push >= 1) this.setFpv(true);
      return;
    }
    this._push = 0;
    c.dist = clamp(c.dist * f, DIST_MIN, DIST_MAX);
  }

  // turn the body to heading h at once (a shot at the basket); in first person the view keeps its direction
  face(h) {
    const d = wrapAngle(h - this.heading);
    this.heading = h;
    if (this.cam.fp > 0) this.cam.orbit = wrapAngle(this.cam.orbit - d);
  }

  // the walker's own body drawn or not (first person). Its meshes only leave the layer the view draws: the holder
  // stays visible, so the shadow map (shadows.js draws the moving casters from their own layer) and the phones' blob
  // (blobs.js) still have it
  showBody(on) {
    if (this._body === this.actor && this._bodyOn === on) return;
    this._body = this.actor; this._bodyOn = on;
    this.actor.holder.traverse((o) => { if (o.isMesh) { if (on) o.layers.enable(VIEW_LAYER); else o.layers.disable(VIEW_LAYER); } });
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
    this.cam.lift = this.fpv ? 0 : Math.max(0, this.cam.lift);      // arrive looking level
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
    for (const h of (this.fpv ? this.wallRaysFp : this.wallRays)) {
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
    if (!hits.length) return null;
    // on the terrain: and on the lawn's raised edge along the kerbs
    return hits[0].point.y + (this.lift && hits[0].object === this.walk[0] ? this.lift(x, -z) : 0);
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
    if (this.scripted) { this.speed = 0; this.vy = 0; this.updateCamera(dt); return; }
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
    } else if (this.fpv && !this.camOverride && (inp.fwd || inp.turn)) {
      // first person, keys: the body comes round to where you look as you set off (the view itself stays), so you
      // walk where you look, and a drag steers while you walk
      const c = this.cam, o = wrapAngle(c.orbit), d = o * Math.min(1, dt * 12);
      this.heading += d;
      c.orbit = o - d;
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
    const c = this.cam, cam = this.camera;
    // first person, but for a scene that stages its own view (birthday.js: camOverride, scripted)
    const first = this.fpv && !this.scripted && !this.camOverride;
    // somebody else has had the camera since the last frame (the tour: birdseye.js)
    const taken = c.set.x !== cam.position.x || c.set.y !== cam.position.y || c.set.z !== cam.position.z;
    if (first) {
      if (!c.ready) { c.fp = 1; c.fpT = FP_IN; c.eyeY = null; c.ready = true; }      // set down somewhere: there at once
      // back from the tour (main.js leaveBird has put the rig at its camera): down into the eyes from there
      else if (taken) { c.fp = 0; c.fpT = FP_SWOOP; }
      else if (c.fp < 1) { c.fp = Math.min(1, c.fp + dt / c.fpT); if (c.fp === 1) c.fpT = FP_IN; }
    } else if (c.fp > 0) {
      if (this.fpv || taken) {
        // a scene takes the view from the eyes: its camera sets off from where they are
        c.pos.copy(cam.position);
        c.look.copy(cam.position).add(this._q.set(0, 0, -3).applyQuaternion(cam.quaternion));
        c.up = 0; c.fp = 0; c.stale = false; c.ready = true; c.eyeY = null;
        c.fpT = FP_SWOOP;                             // (and the way back in afterwards takes as long)
      } else c.fp = Math.max(0, c.fp - dt / FP_OUT);
    }
    if (this.camOverride) {
      const o = this.camOverride, k = o.k ?? 1 - Math.exp(-dt * 2.2);
      c.pos.lerp(o.pos, k);
      c.look.lerp(o.look, k);
      c.up *= 1 - k;
      c.ready = true;
      cam.position.copy(c.pos);
      cam.lookAt(c.look);
      this.cameraSet();
      return;
    }
    if (c.fp < 1) this.behindCamera(dt, inp, first);
    else c.stale = true;                              // (the rig behind the walker is not kept up meanwhile)
    if (c.fp > 0) {
      const eye = this.eyeCamera(dt, inp, first);
      if (c.fp < 1) { const s = smooth(c.fp); cam.position.lerp(eye, s); cam.quaternion.slerp(this._eq, s); }
      else { cam.position.copy(eye); cam.quaternion.copy(this._eq); }
    } else c.eyeY = null;
    this.cameraSet();
  }

  // the camera is placed for this frame: the body is not drawn while the view is in its head or on its way through
  // it (into first person and out, a scene's camera leaving the eyes)
  cameraSet() {
    const c = this.cam, p = this.pos, at = this.camera.position;
    const inHead = (this.fpv || c.fp > 0) && at.distanceToSquared(this._eye.set(p.x, c.eyeY ?? p.y + this.eyeH, p.z)) < FP_BODY * FP_BODY;
    this.showBody(!inHead);
    c.set.copy(at);
  }

  // the camera behind and above the walker
  behindCamera(dt, inp, first) {
    const c = this.cam, p = this.pos;
    if (c.stale) { c.stale = false; c.ready = false; }      // out of first person: the rig straight to its place
    // walking: the camera swings back behind you and a look up comes back to level (a camera raised to look down stays)
    if (!first && !c.drag && (inp.fwd || inp.turn)) {
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

  // the camera in the walker's eyes: where it is (returned) and how it is turned (this._eq)
  eyeCamera(dt, inp, first) {
    const c = this.cam, p = this.pos;
    if (first) {
      if (c.aim) {
        // a shot: the view turns to the basket
        const dx = c.aim.x - p.x, dz = c.aim.z - p.z, k = 1 - Math.exp(-dt * 6);
        const pitch = Math.min(0.9, Math.atan2(c.aim.y - (p.y + this.eyeH), Math.hypot(dx, dz)));
        c.orbit += wrapAngle(Math.atan2(dx, dz) - this.heading - c.orbit) * k;
        c.lift += (fpLift(pitch) - c.lift) * k;
      } else if (inp.stick && !c.drag) {
        // the stick: the view comes round to the way you walk, as the camera behind does (the walker heads
        // stick.rel off the view, so it is the view that turns by a share of that)
        c.orbit += inp.stick.rel * (1 - Math.exp(-dt * inp.recenter));
      }
      if (inp.fwd && !c.drag && !inp.tilt && !c.aim) {
        const easy = clamp(c.lift, fpLift(FP_EASY_UP), fpLift(-FP_EASY_DOWN));
        c.lift = easy + (c.lift - easy) * Math.exp(-dt * FP_EASY_RATE);
      }
    }
    // the eye's height follows the walked surface; a kerb's 15 cm in one frame is taken in a few
    const ey = p.y + this.eyeH;
    if (c.eyeY === null || Math.abs(ey - c.eyeY) > 1.5) c.eyeY = ey;
    else c.eyeY += (ey - c.eyeY) * (1 - Math.exp(-dt * 16));
    // head bob: the clip's own head height about its running mean (the mixer has run: in step with the footfalls)
    let bob = 0;
    const sp = Math.abs(this.speed);
    if (this.headBone && sp > 0) {
      const hy = this.headBone.getWorldPosition(this._q).y - p.y;
      if (c.headAvg === null) c.headAvg = hy;
      c.headAvg += (hy - c.headAvg) * (1 - Math.exp(-dt * 2.5));
      const run = clamp((sp - WALK) / (RUN - WALK), 0, 1);
      bob = clamp((hy - c.headAvg) * (BOB_WALK + (BOB_RUN - BOB_WALK) * run) * Math.min(1, sp / 1.2), -BOB_MAX, BOB_MAX);
    } else c.headAvg = null;
    c.bob += (bob - c.bob) * (1 - Math.exp(-dt * 25));
    this._eq.setFromEuler(this._eul.set(fpPitch(c.lift), this.heading + c.orbit + Math.PI, 0));
    return this._eye.set(p.x, c.eyeY + c.bob + c.hop * 0.5, p.z);
  }

  // the walker's body on screen, head to knees, in CSS px [left, top, right, bottom] (for the HUD to keep clear of it)
  screenBox(camera, out = this._sbox || (this._sbox = [0, 0, 0, 0])) {
    const v = this._sb || (this._sb = new THREE.Vector3());
    if (this._bodyOn === false) { out[0] = out[1] = out[2] = out[3] = -1e4; return out; }      // first person: no body there
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
