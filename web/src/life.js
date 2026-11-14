// Campus life: 1997 banners (현수막) across 백양로, students walking, cars on the road.
import * as THREE from 'three';
import { mulberry, wrapAngle } from './util.js';
import { patchShader, restShadow } from './materials.js';
import { play, locomotion, gesturing, crowdLook } from './characters.js';
import { crowdBag, carriesInHand } from './bags.js';
import { kindOf, meeting, chatter, hello, excuse, lineTime } from './talk.js';

// ---------------------------------------------------------------- polyline helpers (campus frame)
const _a = new THREE.Vector2(), _b = new THREE.Vector2();

export class Path {
  constructor(pts, heightFn) {
    this.pts = pts.map(([x, y]) => new THREE.Vector2(x, y));
    this.cum = [0];
    for (let i = 1; i < this.pts.length; i++) this.cum.push(this.cum[i - 1] + this.pts[i].distanceTo(this.pts[i - 1]));
    this.length = this.cum[this.cum.length - 1];
    this.heightFn = heightFn;
    // cached heights every 2 m
    this.hs = [];
    for (let s = 0; s <= this.length + 2; s += 2) {
      const p = this.at(s);
      this.hs.push(heightFn(p.x, p.y));
    }
  }
  at(s, out = new THREE.Vector2()) {
    s = Math.max(0, Math.min(this.length, s));
    // binary search for the first vertex at or past s (called several times per walker and car every frame)
    const cum = this.cum;
    let lo = 1, hi = cum.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (cum[mid] < s) lo = mid + 1; else hi = mid;
    }
    const i = lo;
    const t = (s - this.cum[i - 1]) / (this.cum[i] - this.cum[i - 1] || 1);
    return out.copy(this.pts[i - 1]).lerp(this.pts[i], t);
  }
  dir(s, out = new THREE.Vector2()) {
    this.at(Math.max(0, s - 1), _a);
    return out.copy(this.at(Math.min(this.length, s + 1), _b)).sub(_a).normalize();
  }
  h(s) {
    const f = Math.max(0, s) / 2, i = Math.min(this.hs.length - 2, f | 0);
    return this.hs[i] + (this.hs[i + 1] - this.hs[i]) * (f - i);
  }
  // A lane's speed limit by the metre: the limit given at each vertex (m/s, Infinity = the car's own pace), no faster
  // than a bend allows (latAcc sideways), and falling ahead of a slower stretch as a car brakes for it (dec).
  // vmax(s) reads it.
  setLimits(lim, latAcc = 1.7, dec = 1.6) {
    const n = Math.ceil(this.length) + 1, v = new Float32Array(n);
    const a = new THREE.Vector2(), b = new THREE.Vector2(), c = new THREE.Vector2();
    let k = 1;
    for (let i = 0; i < n; i++) {
      while (k < this.cum.length - 1 && this.cum[k] < i) k++;
      v[i] = Math.min(lim[k - 1], lim[k]);
      // the bend over 3 m either side: the heading's turn per metre
      this.at(i - 3, a); this.at(i, b); this.at(i + 3, c);
      const t1 = Math.atan2(b.y - a.y, b.x - a.x), t2 = Math.atan2(c.y - b.y, c.x - b.x);
      const turn = Math.abs(Math.atan2(Math.sin(t2 - t1), Math.cos(t2 - t1))) / 3;
      if (i > 3 && i < n - 4 && turn > 1e-3) v[i] = Math.min(v[i], Math.sqrt(latAcc / turn));
    }
    for (let i = n - 2; i >= 0; i--) v[i] = Math.min(v[i], Math.sqrt(v[i + 1] * v[i + 1] + 2 * dec));
    this.lim = v;
    return this;
  }
  vmax(s) { return this.lim ? this.lim[Math.max(0, Math.min(this.lim.length - 1, Math.round(s)))] : Infinity; }
  // The ground under a car's two wheel tracks (half m either side of the line), by the metre: [left, right]
  setTracks(half = 0.72) {
    const n = Math.ceil(this.length) + 2, l = new Float32Array(n), r = new Float32Array(n);
    const p = new THREE.Vector2(), d = new THREE.Vector2();
    for (let i = 0; i < n; i++) {
      this.at(i, p); this.dir(i, d);
      l[i] = this.heightFn(p.x - d.y * half, p.y + d.x * half);
      r[i] = this.heightFn(p.x + d.y * half, p.y - d.x * half);
    }
    this.tracks = [l, r];
    return this;
  }
  track(side, s) {
    const t = this.tracks[side], f = Math.max(0, Math.min(t.length - 1.001, s)), i = f | 0;
    return t[i] + (t[i + 1] - t[i]) * (f - i);
  }
  // a parallel line `off` m to the left; off may also be a function of the arc length (a lane bending round an island)
  offset(off) {
    const out = [];
    const step = 3, p = new THREE.Vector2(), d = new THREE.Vector2();
    for (let s = 0; s <= this.length; s += step) {
      this.at(s, p); this.dir(s, d);
      const o = typeof off === 'function' ? off(s) : off;
      out.push([p.x - d.y * o, p.y + d.x * o]);
    }
    return out;
  }
}

// ---------------------------------------------------------------- banners
// 1997 aerial photo (reference/1997_백양로_항공사진.jpg): plain cloth strips about 0.8-0.9 m deep and 9-12 m long,
// tied with ropes to the ginkgos and lamp posts on either side of the road (no poles of their own).
const BANNER_STYLE = {
  blue: { bg: '#1d3f9a', fg: '#ffffff', edge: '#0d2463' },
  // white cloth, blue lettering, a dark blue strip along the bottom with small white print (photo)
  white: { bg: '#f7f5ee', fg: '#1d2a6b', edge: '#c9c3b2', band: '#22348a', bandFg: '#e8ecf7' },
  // white cloth, blue lettering, a yellow strip along the bottom with small red print (photo)
  white_yellow: { bg: '#f7f5ee', fg: '#1d2a6b', edge: '#c9c3b2', band: '#f1cf2c', bandFg: '#b8261e' },
  yellow: { bg: '#ffd83a', fg: '#1d3f9a', edge: '#c9a400' },
};
const FONT = '"Do Hyeon", "Jua", sans-serif';

function fitFont(x, text, size, maxW, min = 18) {
  size = Math.round(size);
  x.font = `${size}px ${FONT}`;
  while (x.measureText(text).width > maxW && size > min) { size -= 2; x.font = `${size}px ${FONT}`; }
  return size;
}

// the title as big as the cloth allows, its letters spread to fill the width (as the 1997 banners are lettered)
function title(x, text, cx, cy, size, maxW, fill = 0.9) {
  fitFont(x, text, size, maxW);
  const w = x.measureText(text).width;
  const chars = [...text];
  if (w > maxW * fill || chars.length < 2) { x.fillText(text, cx, cy); return; }
  const ws = chars.map((ch) => x.measureText(ch).width);
  const gap = (maxW * fill - w) / (chars.length - 1);
  let px = cx - (maxW * fill) / 2;
  x.textAlign = 'left';
  chars.forEach((ch, i) => { x.fillText(ch, px, cy); px += ws[i] + gap; });
  x.textAlign = 'center';
}

// b: { text, sub?, marks?: ['경', '축'], band?: small print of the bottom band, color }; H: canvas height for a 2048 px wide strip (the cloth's aspect)
function bannerTexture(b, H = 160) {
  const st = BANNER_STYLE[b.color] || BANNER_STYLE.white;
  const c = document.createElement('canvas');
  c.width = 2048; c.height = H;
  const x = c.getContext('2d');
  const W = c.width;
  const e = Math.max(4, Math.round(H * 0.035));
  x.fillStyle = st.bg; x.fillRect(0, 0, W, H);
  x.fillStyle = st.edge; x.fillRect(0, 0, W, e); x.fillRect(0, H - e, W, e);
  const marks = b.marks || null;
  const R = H * 0.34;
  const padX = marks ? H * 0.62 + R + H * 0.3 : H * 0.4;
  const yellow = b.color === 'white_yellow';
  const bandH = st.band ? Math.round(H * (yellow ? 0.24 : 0.16)) : 0;
  const band0 = H - e - bandH;
  if (bandH) { x.fillStyle = st.band; x.fillRect(padX - H * 0.2, band0, W - 2 * (padX - H * 0.2), bandH); }
  x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillStyle = st.fg;
  if (b.sub && !yellow) {
    // a small line over the main text (who holds the event), as on the photo's front banner
    fitFont(x, b.sub, H * 0.17, W * 0.5);
    x.fillText(b.sub, W / 2, e + H * 0.11);
    const top = e + H * 0.21;
    title(x, b.text, W / 2, (top + band0) / 2 + H * 0.03, (band0 - top) * 1.05, W - 2 * padX, 0.97);
  } else if (b.sub && yellow) {
    // big title, the fields below it in smaller print, then the yellow strip
    title(x, b.text, W / 2, e + H * 0.27, H * 0.5, W - 2 * padX);
    fitFont(x, b.sub, H * 0.15, W * 0.6);
    x.fillText(b.sub, W / 2, e + H * 0.6);
  } else {
    title(x, b.text, W / 2, (e + band0) / 2 + H * 0.03, (band0 - e) * 0.8, W - 2 * padX);
  }
  if (bandH && st.bandFg) {
    // the small print of the bottom band: what can be made out on the photo (b.band), else the usual fields
    const band = b.band || '일시 · 장소 · 주최  연세대학교';
    fitFont(x, band, bandH * 0.62, W * (b.band ? 0.8 : 0.5), 8);
    x.fillStyle = st.bandFg;
    x.fillText(band, W / 2, band0 + bandH / 2 + 1);
  }
  if (marks) {
    // red circles with a white character at both ends (경 … 축)
    marks.forEach((m, i) => {
      const cx = i ? W - H * 0.62 : H * 0.62, cy = H / 2;
      x.fillStyle = '#d0232a'; x.beginPath(); x.arc(cx, cy, R, 0, Math.PI * 2); x.fill();
      x.fillStyle = '#ffffff'; x.font = `${Math.round(R * 1.35)}px ${FONT}`; x.fillText(m, cx, cy + R * 0.08);
    });
  }
  // cloth wrinkles
  const g = x.createLinearGradient(0, 0, W, 0);
  for (let i = 0; i <= 12; i++) g.addColorStop(i / 12, `rgba(0,0,0,${i % 2 ? 0.0 : 0.06})`);
  x.fillStyle = g; x.fillRect(0, 0, W, H);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

// a thin rope between two points (three coords)
const ROPE_GEO = new THREE.CylinderGeometry(0.012, 0.012, 1, 4, 1, true).translate(0, 0.5, 0);
const _up = new THREE.Vector3(0, 1, 0);
function rope(P, Q, mat) {
  const d = Q.clone().sub(P);
  const m = new THREE.Mesh(ROPE_GEO, mat);
  m.position.copy(P);
  m.scale.set(1, d.length(), 1);
  m.quaternion.setFromUnitVectors(_up, d.normalize());
  return m;
}

// banners can carry per-season texts ({seasons: {autumn: {text, color}}}): group.userData.setSeason swaps them.
// b.a / b.b: top corners of the east / west end [x, y, z] (campus frame), b.depth: cloth depth, b.ties: where the
// ropes of the east / west end are tied (a ginkgo trunk or a lamp post)
export function makeBanners(banners, lib) {
  const group = new THREE.Group();
  group.name = 'banners';
  const cloths = [];
  const ropeMat = new THREE.MeshStandardMaterial({ color: 0xd9d5c9, roughness: 0.9 });
  const windT = lib.uniforms.uWindT;   // the trees' wind clock (materials.js)
  const V = (p) => new THREE.Vector3(p[0], p[2], -p[1]);
  for (const b of banners) {
    const g = new THREE.Group();      // one banner (cloth + ropes): hidden outside its season when it has `only`
    group.add(g);
    const A = V(b.a), B = V(b.b);     // east, west (top corners)
    const dep = b.depth || 0.9;
    const span = new THREE.Vector3().subVectors(A, B);
    const len = Math.hypot(span.x, span.z);
    // towards the gate (south): the side the text reads from
    const nrm = new THREE.Vector3(-span.z, 0, span.x).normalize();
    // the cloth (issue #12): a grid so it can hang like cloth -- the top sags a little between the ties and the
    // free bottom edge a little more, a couple of long soft bellies along it, and fan-shaped tension folds running in
    // from the four tied corners; the wind stirs it (vertex shader below)
    const N = 40, M = 4;
    const ph = (b.a[0] * 0.37 + b.b[1] * 0.11) % 6.283;
    const pos = [], uv = [], idx = [];
    for (let i = 0; i <= N; i++) {
      const t = i / N;
      const top = B.clone().lerp(A, t);
      const dEnd = Math.min(t, 1 - t) * len;                       // metres from the nearer tied end
      for (let j = 0; j <= M; j++) {
        const v = j / M;                                          // 0 top .. 1 bottom
        const p = top.clone();
        p.y -= v * dep + Math.sin(t * Math.PI) * (0.07 + 0.07 * v);
        let off = Math.sin(t * Math.PI * 3 + ph) * 0.035 * (0.6 + 0.4 * v) + Math.sin(t * Math.PI * 7 + ph * 2) * 0.012;
        const corner = v < 0.5 ? v : 1 - v;                       // folds fan in from the top and bottom corners
        off += Math.sin((dEnd * 2.6 + corner * 2.2) * Math.PI) * 0.028 * Math.exp(-dEnd / 1.3);
        p.addScaledVector(nrm, off);
        pos.push(p.x, p.y, p.z);
        uv.push(t, 1 - v);
      }
      if (i < N) for (let j = 0; j < M; j++) {
        const k = i * (M + 1) + j, k2 = k + M + 1;
        idx.push(k, k + 1, k2, k2, k + 1, k2 + 1);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    geo.setIndex(idx);
    geo.computeVertexNormals();
    const mat = new THREE.MeshStandardMaterial({ side: THREE.DoubleSide, roughness: 0.9 });
    // the wind: slow bellies along the cloth under the trees' gust swell, and small ripples running across it
    // from the west end, most at the free bottom edge; the normal tilts with the slope so they catch the light
    const W = { uWindN: { value: nrm.clone() }, uWindS: { value: new THREE.Vector3(span.x, 0, span.z).normalize() },
      uWindPh: { value: ph }, uWindL: { value: len }, uWindDep: { value: dep } };
    patchShader(mat, 'bannerWind', (sh) => {
      Object.assign(sh.uniforms, W, { uWindT: windT });
      sh.vertexShader = restShadow(sh.vertexShader
        .replace('#include <common>', `#include <common>
          uniform float uWindT, uWindPh, uWindL, uWindDep; uniform vec3 uWindN, uWindS;
          // offset along the cloth's normal (metres) at t (0 west .. 1 east end), v (0 top .. 1 bottom)
          float bannerWind(float t, float v) {
            float x = t * uWindL, T = uWindT, P = uWindPh, e = sin(t * 3.14159);
            float gust = 0.75 + 0.25 * sin(T * 0.21 + P);
            float d = (0.3 + 0.7 * v) * (0.05 * sin(T * 1.3 + t * 6.0 + P) + 0.02 * sin(T * 2.1 + t * 13.0 + P * 1.7));
            d += (0.006 + 0.022 * v * v) * (sin(T * 4.6 - x * 2.3 + P) + 0.5 * sin(T * 7.3 - x * 4.1 + P * 2.0));
            return d * e * gust;
          }`)
        .replace('#include <beginnormal_vertex>', `#include <beginnormal_vertex>
          float windD = bannerWind(uv.x, 1.0 - uv.y);
          {
            float sx = (bannerWind(uv.x + 0.01, 1.0 - uv.y) - windD) / (0.01 * uWindL);    // slope along the cloth
            float sy = (bannerWind(uv.x, 1.0 - uv.y + 0.05) - windD) / (0.05 * uWindDep);  // and down it
            objectNormal = normalize(objectNormal - dot(objectNormal, uWindN) * (uWindS * sx - vec3(0.0, sy, 0.0)));
          }`)
        .replace('#include <begin_vertex>', `#include <begin_vertex>
          vec3 windW = uWindN * windD;
          transformed += windW;`));
    });
    const texH = Math.max(96, Math.min(256, Math.round(2048 * dep / len)));
    cloths.push({ b, mat, g, key: null, texH });
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = true;
    g.add(m);
    // two ropes from each end (top and bottom corner) to its tie
    const ties = b.ties || [];
    [[A, ties[0]], [B, ties[1]]].forEach(([P, tie]) => {
      if (!tie) return;
      const T = V(tie);
      g.add(rope(P, T, ropeMat));
      g.add(rope(P.clone().setY(P.y - dep), T, ropeMat));
    });
  }
  group.userData.setSeason = (season) => {
    for (const c of cloths) {
      c.g.visible = (!c.b.only || c.b.only === season) && c.b.hide !== season;
      const spec = { ...c.b, ...(c.b.seasons?.[season] || {}) };
      const key = spec.text + spec.color;
      if (key === c.key) continue;
      c.key = key;
      c.mat.map?.dispose();
      c.mat.map = bannerTexture(spec, c.texH);
      c.mat.needsUpdate = true;
    }
  };
  group.userData.setSeason(lib.season);
  return group;
}

// ---------------------------------------------------------------- students (Quaternius people, sim-office style)
// Walkers follow paths at their own pace and stop when you are in the way; groups stand and chat. Far away people
// (and the drivers of far cars) leave the scene and their animation is not updated.
// Whoever stands does not stand like a post: every few seconds they take another of the standing clips (POSES:
// shifting the weight, looking about, arms folded), talk with their hands while a line of theirs is up, and the one
// in a phone booth holds the receiver to the ear. Seated people gesture while they speak.
// Nobody walks through anybody (steer): a walker who sees somebody in their way within a couple of metres - another
// walker, people standing in a group or a queue, you - steps aside as they go (to their own right when it is head-on,
// so two coming towards each other part), comes back to their side of the path once past, and shortens the stride
// rather than tread on the heels of a slower one; you they wait for a moment first, and ask to get by.
// Small talk (talk.js): two walkers coming towards each other near the view now and then stop, face each other, wave
// and trade a line or two; groups talk among themselves and greet you; a walker you block asks to get by.
const FAR2 = 190 * 190;
const TALK_NEAR2 = 45 * 45;        // talk only where it can be seen
const MAX_TALKS = 4;               // conversations at once round the view
const height = (id) => (id.startsWith('woman') ? 1.61 : 1.73);
// Sitting (the benches: 2003_봄_언더우드관정원_남쪽계단_벚나무.jpg, three people to a bench): the 'sit' clip, the hips
// THIGH over the seat. A seated person keeps still but for the head, which turns a little (LOOK_MAX, the neck with
// it) to whoever is speaking or to you.
const THIGH = 0.085;
// the standing clips and how often each is taken; waiting in a line one looks about more
const POSES = [['idle', 5], ['idle-shift', 3], ['idle-look', 2], ['idle-fold', 1.2]];
const POSES_LINE = [['idle', 3], ['idle-shift', 3], ['idle-look', 4], ['idle-fold', 1]];
function nextPose(p, t) {
  const set = (p.queue ? POSES_LINE : POSES).filter(([n]) => p.a.actions[n] && !(n === 'idle-fold' && carriesInHand(p.a.bag)));
  let r = Math.random() * set.reduce((s, [, w]) => s + w, 0);
  p.pose = set.find(([, w]) => (r -= w) < 0)?.[0] || 'idle';
  p.poseUntil = t + 6 + Math.random() * 10;
}
const _hip = new THREE.Vector3(), _head = new THREE.Vector3();
// stepping round each other: who is looked at (m ahead, m either side of the way), how far a walker leaves their own
// line and how fast (m/s sideways at a full stride), from how far off the camera it is done at all, and how long a
// walker waits for you standing in the way before going round
const SEE = 2.4, WIDE = 0.78, OFF_MAX = 1.0, SIDESTEP = 0.75, STEER2 = 60 * 60, PATIENCE = 2.6;
const _YOU = { walking: false };
// the head of somebody sitting turns no further than this (rad), the neck doing its share
const LOOK_MAX = 0.6, NECK_SHARE = 0.4;

export class Crowd {
  // extras: { seats: [[{x, y, h, heading}, ...], ...] people sitting together (h: the seat's top),
  //           lines: [[{x, y, heading}, ...], ...] people standing in a row (the queue at the phone booths) }
  constructor(scene, cast, ids, paths, groups, count, rndSeed = 3, extras = {}) {
    this.scene = scene;
    this.people = [];
    const rnd = mulberry(rndSeed);
    const pick = () => ids[Math.floor(rnd() * ids.length)];
    // about 70 % carry a bag (bags.js: its own random stream, so the walkers' paths stay where they were)
    for (let i = 0; i < count; i++) {
      const id = pick();
      const a = cast.make(id, crowdBag(id, i), crowdLook(id, i));
      const path = paths[Math.floor(rnd() * paths.length)];
      const p = { a, path, s: rnd() * path.length, dir: rnd() < 0.5 ? 1 : -1, speed: 1.15 + rnd() * 0.4, side: (rnd() - 0.5) * 0.8,
        heading: 0, walking: true, gestureAt: 5 + rnd() * 30, tick: i & 1, off: 0, offTo: 0, slow: 1, pace: 1, v: 0,
        kind: kindOf(a.id), top: height(a.id) * a.tall, x: 1e9, y: 1e9, fx: 0, fy: 0,
        chatUntil: 0, chatAfter: 2 + rnd() * 10, face: null, blockedT: 0, excuseAfter: 0 };
      a.mixer.setTime(rnd() * 2);
      scene.add(a.holder);
      this.people.push(p);
    }
    // standing groups (친구들과 수다): 2-4 people round a point, facing the middle
    this.groups = [];
    for (const [gx, gy, h] of groups) {
      const n = 2 + Math.floor(rnd() * 3);
      const g = { people: [], next: 4 + rnd() * 14, busyUntil: 0, greetAfter: 0, near: false };
      this.groups.push(g);
      for (let k = 0; k < n; k++) {
        const ang = (k / n) * Math.PI * 2 + rnd() * 0.4;
        const x = gx + Math.cos(ang) * 0.85, y = gy + Math.sin(ang) * 0.85;
        const id = pick();
        const nth = 1000 + this.people.length;
        const a = cast.make(id, crowdBag(id, nth), crowdLook(id, nth));
        a.mixer.setTime(rnd() * 2);
        a.holder.position.set(x, h, -y);
        const heading = Math.atan2(gx - x, -(gy - y));
        a.holder.rotation.y = heading;
        scene.add(a.holder);
        const p = { a, walking: false, heading, home: heading, gestureAt: 3 + rnd() * 20, tick: k & 1, x, y,
          kind: kindOf(a.id), top: height(a.id) * a.tall, group: g };
        g.people.push(p);
        this.people.push(p);
      }
    }
    // people of the extras: their own random stream (the walkers and the groups above stay who and where they were)
    const rx = mulberry(rndSeed * 31 + 7);
    const pickX = () => ids[Math.floor(rx() * ids.length)];
    const join = (g, a, x, y, heading, more) => {
      a.holder.rotation.y = heading;
      scene.add(a.holder);
      const p = { a, walking: false, heading, home: heading, gestureAt: 3 + rx() * 20, tick: this.people.length & 1, x, y,
        kind: kindOf(a.id), top: height(a.id) * a.tall, group: g, ...more };
      g.people.push(p);
      this.people.push(p);
      return p;
    };
    for (const row of extras.lines || []) {
      // (they wait, each looking at the back of the one ahead: no chatting round a circle, but they greet you)
      const g = { people: [], next: Infinity, busyUntil: 0, greetAfter: 0, near: false };
      this.groups.push(g);
      for (const m of row) {
        const id = pickX(), n = 3000 + this.people.length;
        // (the one on the phone holds the receiver in the right hand: nothing else in it)
        const bag = crowdBag(id, n);
        const a = cast.make(id, m.phone && carriesInHand(bag) ? null : bag, crowdLook(id, n));
        a.mixer.setTime(rx() * 2);
        a.holder.position.set(m.x, m.h, -m.y);
        join(g, a, m.x, m.y, m.heading, { queue: true, phone: !!m.phone });
      }
    }
    for (const bench of extras.seats || []) {
      const g = { people: [], next: 3 + rx() * 20, busyUntil: 0, greetAfter: 0, near: false };
      this.groups.push(g);
      for (const m of bench) {
        const id = pickX(), n = 2000 + this.people.length;
        // (nothing on the back against the bench's; a bag in the hand would hang through the seat)
        const a = cast.make(id, null, crowdLook(id, n));
        play(a, 'sit', { fade: 0 });
        a.mixer.update(0);
        // the hips THIGH over the seat: where the clip holds them over the holder, at this person's size
        a.holder.position.set(m.x, 0, -m.y);
        a.holder.rotation.y = m.heading;
        a.holder.updateMatrixWorld(true);
        const legs = ['UpperLegL', 'UpperLegR'].map((b) => a.root.getObjectByName(b)).filter(Boolean);
        let hip = 0.29 * a.tall;
        if (legs.length) hip = legs.reduce((sum, b) => sum + b.getWorldPosition(_hip).y, 0) / legs.length;
        a.holder.position.y = m.h + THIGH - hip;
        const head = a.root.getObjectByName('Head');
        const top = head ? head.getWorldPosition(_head).y + 0.24 * a.tall : hip + 0.75;
        // (headRest: the head as the clip holds it. The turn is set from it, never added to the frame before)
        const neck = a.root.getObjectByName('Neck');
        const p = join(g, a, m.x, m.y, m.heading, { seated: true, head, headRest: head?.quaternion.clone(), neck, neckRest: neck?.quaternion.clone(),
          look: 0, lookTo: 0, lookAt: rx() * 6 });
        p.top = top;
      }
    }
    this.v = new THREE.Vector2();
    this.d = new THREE.Vector2();
    this.frame = 0;
    this.season = 'summer';        // main.js keeps it on the month picked
    this.bubbles = null;           // talk.js Bubbles (main.js); without it people still stop and wave, silently
    this.talks = [];               // end times of the conversations going on
    this.cues = [];                // gestures timed to the lines: { at, p }
    this.says = [];                // who speaks when: { at, until, p } (they talk with their hands meanwhile)
    this.scanT = 0;
    this.excuseAt = 0;             // the next time a blocked walker may speak up
    this._near = [];
  }
  // circles the player collides with (one reused circle per person: this runs every frame)
  movers(px, py, out = []) {
    out.length = 0;
    for (const p of this.people) {
      const x = p.a.holder.position.x, y = -p.a.holder.position.z;
      if (Math.abs(x - px) < 6 && Math.abs(y - py) < 6) {
        const c = (p.circle ||= { x: 0, y: 0, r: 0.3 });
        c.x = x; c.y = y;
        out.push(c);
      }
    }
    return out;
  }
  // where a walker steps aside to, and how much of their pace is left: p at (x, y) going d, their left n = (-d.y, d.x)
  steer(p, d, x, y, player) {
    let push = 0, slow = 1;
    const see = (q, qx, qy) => {
      const rx = qx - x, ry = qy - y;
      if (Math.abs(rx) > SEE || Math.abs(ry) > SEE) return;
      const ahead = rx * d.x + ry * d.y, lat = -rx * d.y + ry * d.x, wide = Math.abs(lat);
      if (ahead < -0.1 || ahead > SEE || wide > WIDE) return;
      // somebody going the same way no slower: nothing to pass, only not to tread on their heels
      if (q.walking && q.v > 0 && q.fx * d.x + q.fy * d.y > 0.5 && q.v >= p.speed * 0.92) {
        if (ahead < 0.9 && wide < 0.5) slow = Math.min(slow, q.v / p.speed * (ahead < 0.6 ? 0.8 : 1));
        return;
      }
      // (to the side they are not on; head-on, or right behind somebody slower: to the right)
      push += (lat > 0.04 ? -1 : lat < -0.04 ? 1 : -1) * (WIDE - wide) * (1.25 - 0.5 * ahead / SEE);
      if (ahead < 0.75 && wide < 0.5) slow = Math.min(slow, ahead < 0.45 ? 0.15 : 0.4);
    };
    for (const q of this.people) if (q !== p && q.a.holder.parent) see(q, q.x, q.y);
    see(_YOU, player.x, player.y);
    // (what is seen is seen from where they are now, `off` and all: so much further, or back to their own line)
    p.offTo = push ? Math.max(-OFF_MAX, Math.min(OFF_MAX, p.off + push)) : 0;
    p.slow = slow;
  }
  update(dt, t, player, camPos) {
    this.frame++;
    const v = this.v, d = this.d;
    for (const p of this.people) {
      const a = p.a, hp = a.holder.position;
      const far = (hp.x - camPos.x) ** 2 + (hp.z - camPos.z) ** 2;
      let speed = 0, want = null;
      if (p.walking) {
        p.path.at(p.s, v);
        p.path.dir(p.s, d).multiplyScalar(p.dir);
        // (where they are: `side`, and `off` for whoever they are stepping round, to the left of the way they go)
        let lat = p.side + p.off;
        const wx = v.x - d.y * lat, wy = v.y + d.x * lat;
        // stop for the player standing in the way, and look at them; after a while go round
        const tx = player.x - wx, ty = player.y - wy, td = Math.hypot(tx, ty);
        const ahead = tx * d.x + ty * d.y;
        const blocked = td < 1.3 && ahead > 0.2 * td && Math.abs(-tx * d.y + ty * d.x) < 0.6 && p.blockedT < PATIENCE;
        const halt = t < p.chatUntil || gesturing(a);       // talking: stand still facing the other
        if (far > STEER2) { p.offTo = 0; p.slow = 1; }
        else if ((this.frame & 1) === p.tick) this.steer(p, d, wx, wy, player);
        if (halt) {
          const o = p.face?.a.holder.position;
          if (o) want = Math.atan2(o.x - hp.x, o.z - hp.z);
        } else if (!blocked) {
          p.pace += (p.slow - p.pace) * (1 - Math.exp(-dt * 6));
          speed = p.speed * p.pace;
          p.s += p.dir * speed * dt;
          if (p.s > p.path.length) { p.s = p.path.length; p.dir = -1; p.off = -p.off - 2 * p.side; }      // (turning round on the spot)
          if (p.s < 0) { p.s = 0; p.dir = 1; p.off = -p.off - 2 * p.side; }
          p.path.at(p.s, v);
          // sideways no faster than the stride allows (nobody slides standing), and facing where that takes them
          const step = Math.max(-1, Math.min(1, (p.offTo - p.off) / (SIDESTEP * dt || 1))) * SIDESTEP * Math.min(1, speed / p.speed + 0.25);
          p.off += step * dt;
          lat = p.side + p.off;
          want = Math.atan2(d.x * speed - d.y * step, -(d.y * speed + d.x * step));
        } else want = Math.atan2(tx, -ty);
        p.v = speed;
        hp.set(v.x - d.y * lat, p.path.h(p.s), -(v.y + d.x * lat));
        p.x = hp.x; p.y = -hp.z; p.fx = d.x; p.fy = d.y;
        // blocked for a moment: ask to get by (not everyone, and not all at once on a busy sidewalk)
        if (halt) p.blockedT = 0;
        else if (blocked || (p.blockedT >= PATIENCE && td < 1.6)) {
          p.blockedT += dt;
          if (p.blockedT > 1.1 && t > p.excuseAfter) {
            p.excuseAfter = t + 60;
            if (t > this.excuseAt && Math.random() < 0.6) { this.excuseAt = t + 10; this.say(p, excuse(p.kind, this.season), t); }
          }
        } else p.blockedT = 0;
      } else if (p.seated) {
        // only the head turns: to you close by, else now and then to a bench mate or along the path
        if (t > p.lookAt) {
          p.lookAt = t + 4 + Math.random() * 9;
          const tx = player.x - p.x, ty = player.y - p.y, mates = p.group.people;
          const o = mates.length > 1 && Math.random() < 0.6 ? mates[Math.floor(Math.random() * mates.length)] : null;
          let to = null;
          if (Math.hypot(tx, ty) < 3.5) to = Math.atan2(tx, -ty);
          else if (o && o !== p) to = Math.atan2(o.x - p.x, -(o.y - p.y));
          p.lookTo = to === null ? (Math.random() - 0.5) * 0.6 : Math.max(-LOOK_MAX, Math.min(LOOK_MAX, wrapAngle(to - p.heading)));
        }
        p.look += (p.lookTo - p.look) * (1 - Math.exp(-dt * 2));
      } else {
        const tx = player.x - p.x, ty = player.y - p.y;
        want = Math.hypot(tx, ty) < 2.6 ? Math.atan2(tx, -ty) : p.home;      // turn to greet you
        if (t > (p.poseUntil || 0)) nextPose(p, t);
      }
      if (want !== null) {
        p.heading += wrapAngle(want - p.heading) * (1 - Math.exp(-dt * 7));
        a.holder.rotation.y = p.heading;
      }
      // far away: out of the scene graph altogether (hiding it would still update its ~60 bones every frame)
      if (far > FAR2) { if (a.holder.parent) this.scene.remove(a.holder); continue; }
      if (!a.holder.parent) this.scene.add(a.holder);
      if (p.seated) {
        // (the head's turn starts from the pose it had on sitting down each time, not from the frame before: the
        // mixer writes a bone only when its value has changed, and a turn added to the last one would spin the head)
        if (far < 45 * 45 || !p.posed) {
          p.posed = true;
          const clip = t < (p.talkUntil || 0) && a.actions['sit-talk'] ? 'sit-talk' : 'sit';
          if (a.current !== a.actions[clip]) play(a, clip, { fade: 0.5 });
          a.mixer.update(dt);
          if (p.head) { p.head.quaternion.copy(p.headRest); p.head.rotateY(p.look * (p.neck ? 1 - NECK_SHARE : 1)); }
          if (p.neck) { p.neck.quaternion.copy(p.neckRest); p.neck.rotateY(p.look * NECK_SHARE); }
        }
        continue;
      }
      // standing: on the phone, talking with the hands (not with a bag in one), or the pose of the moment
      a.stand = p.phone ? 'phone' : t < (p.talkUntil || 0) && !carriesInHand(a.bag) ? 'talk' : p.pose || 'idle';
      locomotion(a, speed);
      // distant people animate at half rate
      if (far < 70 * 70) a.mixer.update(dt);
      else if ((this.frame & 1) === p.tick) a.mixer.update(dt * 2);
    }
    for (let i = this.says.length - 1; i >= 0; i--) {
      const c = this.says[i];
      if (t < c.at) continue;
      c.p.talkUntil = c.until;
      this.says.splice(i, 1);
    }
    for (let i = this.cues.length - 1; i >= 0; i--) {
      const c = this.cues[i];
      if (t < c.at) continue;
      if (c.p.a.holder.parent && !c.p.seated) playGesture(c.p.a, 'emote-yes');     // (a wave would stand them up)
      this.cues.splice(i, 1);
    }
    this.scanT -= dt;
    if (this.scanT <= 0) { this.scanT = 0.2; this.socialize(t, player, camPos); }
  }

  // one line over p's head, now
  say(p, text, t) { this.bubbles?.add(p.a.holder, p.top, text, t, t + lineTime(text)); p.talkUntil = t + lineTime(text); }

  // lines one after another from t0 (speakers[who] speaks each); returns when the last one is done
  converse(speakers, lines, t0) {
    let at = t0;
    for (const l of lines) {
      const p = speakers[l.who], dur = lineTime(l.text);
      this.bubbles?.add(p.a.holder, p.top, l.text, at, at + dur);
      if (l.wave) this.cues.push({ at, p });
      else this.says.push({ at, until: at + dur, p });
      at += dur + 0.15;
    }
    this.talks.push(at);
    return at;
  }

  // a few times a second: who meets whom near the view
  socialize(t, player, cam) {
    this.talks = this.talks.filter((e) => e > t);
    const room = () => this.talks.length < MAX_TALKS;
    const season = this.season, cx = cam.x, cy = -cam.z;
    // two walkers coming towards each other within a couple of metres: sometimes they stop and talk
    const near = this._near;
    near.length = 0;
    for (const p of this.people) {
      if (p.walking && t > p.chatUntil && t > p.chatAfter && (p.x - cx) ** 2 + (p.y - cy) ** 2 < TALK_NEAR2) near.push(p);
    }
    for (let i = 0; i < near.length && room(); i++) {
      const A = near[i];
      if (t < A.chatUntil) continue;
      for (let j = i + 1; j < near.length; j++) {
        const B = near[j];
        if (t < B.chatUntil) continue;
        const dx = B.x - A.x, dy = B.y - A.y, dd = dx * dx + dy * dy;
        if (dd > 2.4 * 2.4 || dd < 0.6 * 0.6) continue;
        if (A.fx * B.fx + A.fy * B.fy > -0.3 || A.fx * dx + A.fy * dy <= 0) continue;   // facing, not yet past
        if (Math.random() > 0.5) { A.chatAfter = B.chatAfter = t + 6; continue; }      // just walk on by
        const end = this.converse([A, B], meeting(A.kind, B.kind, season), t + 0.35) + 0.4;
        A.chatUntil = B.chatUntil = end;
        A.face = B; B.face = A;
        A.chatAfter = end + 40 + Math.random() * 40;
        B.chatAfter = end + 40 + Math.random() * 40;
        break;
      }
    }
    // standing groups: greet you as you come up; otherwise talk among themselves now and then
    for (const g of this.groups) {
      const m = g.people[0];
      if ((m.x - cx) ** 2 + (m.y - cy) ** 2 > TALK_NEAR2) continue;
      let best = null, bd = 1e9;
      for (const p of g.people) {
        const d = Math.hypot(player.x - p.x, player.y - p.y);
        if (d < bd) { bd = d; best = p; }
      }
      if (bd > 4.5) g.near = false;
      else if (bd < 2.6 && !g.near) {
        g.near = true;
        if (t > g.greetAfter && t > g.busyUntil) {
          g.greetAfter = t + 40;
          g.busyUntil = this.converse([best], [{ who: 0, text: hello(best.kind, season), wave: true }], t + 0.3);
          continue;
        }
      }
      if (t < g.next || t < g.busyUntil || !room() || g.people.length < 2) continue;
      // two speakers, students before the elders
      const order = g.people.slice();
      for (let k = order.length - 1; k > 0; k--) { const r = Math.floor(Math.random() * (k + 1)); [order[k], order[r]] = [order[r], order[k]]; }
      order.sort((a, b) => (a.kind === 'student' ? 0 : 1) - (b.kind === 'student' ? 0 : 1));
      const [A, B] = order;
      g.busyUntil = this.converse([A, B], chatter(A.kind, B.kind, season), t);
      g.next = g.busyUntil + 6 + Math.random() * 16;
    }
  }
}

function playGesture(a, name) {
  if (!a.actions[name]) return;
  play(a, name, { once: true, fade: 0.3 });
}

// ---------------------------------------------------------------- 초소 barrier gates
// The guard booth on 백양로's centre line (1997 aerial photo; tools/build_campus.py BOOTH): a red-and-white arm across
// each lane, down as in the photo, swung up while a car on that lane comes within ~22 m of it and until it is past.
export class BoothGates {
  constructor(scene, armGltf, booth, groundAt, shadows = null) {
    this.arms = [];
    if (!booth || !armGltf) return;
    for (const a of booth.arms) {
      const root = armGltf.scene.clone(true);
      root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
      root.rotation.order = 'YXZ';
      root.rotation.y = a.dir;
      root.position.set(a.x, groundAt(a.x, a.y) + a.z, -a.y);
      scene.add(root);
      shadows?.addDynamic(root, 3);
      // the road heading there, and the way its side's cars run along it (+1 northbound, the arm pointing east)
      const head = a.dir - a.side * Math.PI / 2;
      this.arms.push({ root, a, fx: Math.cos(head) * -a.side, fy: Math.sin(head) * -a.side, lift: 0 });
    }
  }
  update(dt, traffic) {
    for (const g of this.arms) {
      let open = false;
      for (const c of traffic.cars) {
        // (the cars heading its way: both ways are one loop now, main.js)
        if (Math.cos(c.root.rotation.y) * g.fx + Math.sin(c.root.rotation.y) * g.fy < 0.5) continue;
        const dx = c.root.position.x - g.a.x, dy = -c.root.position.z - g.a.y;
        const along = dx * g.fx + dy * g.fy;          // < 0 still coming
        if (along > -22 && along < 4 + c.len / 2 && Math.abs(dx * g.fy - dy * g.fx) < 6) { open = true; break; }
      }
      const target = open ? 1.45 : 0;
      g.lift += Math.sign(target - g.lift) * Math.min(Math.abs(target - g.lift), dt * (open ? 1.4 : 0.9));
      g.root.rotation.z = g.lift;
    }
  }
}

// ---------------------------------------------------------------- traffic
// Cars from blender/cars.py: wheels spin with the distance travelled, brake lights come on when slowing,
// a seated driver (Quaternius 'sit' clip) behind the wheel; they keep their distance and stop for you.
// A lane may carry a stall (main.js: det, rev, stops): the car turns off into it, stands there a while with its driver
// gone, backs out and drives on.
// A lane may carry speed limits (Path.setLimits: the drives off 백양로, their bends, the car park) and the ground
// under its wheel tracks (Path.setTracks): the car then stands on its four tyres, nose up on a climb and leaning
// with a cross fall, as the parked ones do (main.js parkedMatrix).
// 1997 paint: lots of white, silver and dark navy, the mid-90s dark green (진녹색), a few wine / gunmetal / gold
export const CAR_COLORS = ['#eeeeea', '#f2f1ec', '#b9bdc3', '#a9aeb5', '#1b2333', '#2a2d33', '#6e1b1f', '#244a3a', '#1d3b30', '#3a3f45', '#b59a6a', '#2c4a78'];
// sedan 쏘나타Ⅱ type, sedan2 프린스 type, hatch 프라이드 type, tico 티코 type, van 그레이스 type (blender/cars.py)
const WEIGHTS = { sedan: 4, sedan2: 3, hatch: 3, tico: 2, taxi: 3, van: 2 };
// The driver's seat in the car frame (blender/cars.py driver_seat: x forward, y left), the seat's height and how far
// the driver leans back (radians).  The cars are their real sizes, so the driver sits low and leaning back, as in a
// car, the head under a 1.4 m roof (a van's driver sits upright over the front axle).
const DRIVER = { sedan: [-0.05, 0.36, 0.20, 0.33], sedan2: [-0.05, 0.36, 0.20, 0.33], hatch: [-0.27, 0.36, 0.23, 0.30], tico: [-0.30, 0.31, 0.20, 0.33],
  taxi: [-0.05, 0.36, 0.20, 0.33], van: [1.00, 0.38, 0.60, 0.10] };

// 스쿠터 (blender/bikes.py SEAT, GRIP: x forward, z up, the left grip's y): where the rider sits and holds on; the
// rider leans a little forward to the bars.  1990s scooter paint
const BIKE = { seat: [-0.42, 0.742], grip: [0.17, 0.29, 0.985], lean: 0.2 };
const BIKE_COLORS = ['#b3262b', '#e6e4dc', '#1f3f8f', '#d2a81c', '#1b1b1e', '#1f6f66', '#8e9399', '#7a1f2c'];
const _s3 = new THREE.Vector3(), _e3 = new THREE.Vector3(), _w3 = new THREE.Vector3(), _d3 = new THREE.Vector3(), _p3 = new THREE.Vector3(),
  _n3 = new THREE.Vector3(), _t3 = new THREE.Vector3(), _tg = new THREE.Vector3(), _pl = new THREE.Vector3(), _q1 = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _q3 = new THREE.Quaternion();
// turn a bone about its head so that the direction `from` (world) comes to `to`
function swing(bone, from, to) {
  _q1.setFromUnitVectors(from.normalize(), to.normalize());
  bone.parent.getWorldQuaternion(_q2).invert();
  bone.getWorldQuaternion(_q3);
  bone.quaternion.copy(_q2).multiply(_q1).multiply(_q3);
  bone.updateMatrixWorld(true);
}
// an arm (upper, lower, wrist bones) reaching for `target` (world), the elbow off towards `pole`
function reachFor([upper, lower, wrist], target, pole) {
  upper.getWorldPosition(_s3); lower.getWorldPosition(_e3); wrist.getWorldPosition(_w3);
  const l1 = _s3.distanceTo(_e3), l2 = _e3.distanceTo(_w3);
  _d3.copy(target).sub(_s3);
  const dist = Math.min(_d3.length(), (l1 + l2) * 0.985);
  _d3.normalize();
  const a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist), h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
  _p3.copy(pole).addScaledVector(_d3, -pole.dot(_d3)).normalize();
  _n3.copy(_s3).addScaledVector(_d3, a).addScaledVector(_p3, h);            // the elbow
  _t3.copy(_s3).addScaledVector(_d3, dist);                                 // the wrist (the target, within reach)
  swing(upper, _e3.sub(_s3), _p3.copy(_n3).sub(_s3));
  lower.getWorldPosition(_e3); wrist.getWorldPosition(_w3);
  swing(lower, _w3.sub(_e3), _t3.sub(_e3));
}

export class Traffic {
  // single: the first `single` lanes take one car each (a stall a car cannot pass by: main.js)
  constructor(scene, carGltfs, lanes, n = 12, cast = null, driverIds = [], rndSeed = 9, single = 0) {
    this.cars = [];
    const rnd = mulberry(rndSeed);
    const bag = Object.entries(WEIGHTS).filter(([k]) => carGltfs[k]).flatMap(([k, w]) => Array(w).fill(k));
    for (let i = 0; i < n; i++) {
      const kind = bag[Math.floor(rnd() * bag.length)];
      const root = carGltfs[kind].scene.clone(true);
      const col = new THREE.Color(kind === 'taxi' ? '#ecebe4' : CAR_COLORS[Math.floor(rnd() * CAR_COLORS.length)]);
      const brake = [];
      const wheels = [];
      root.traverse((o) => {
        if (/^wheel_/.test(o.name)) wheels.push(o);
        if (!o.isMesh) return;
        o.castShadow = true;
        o.receiveShadow = true;
        if (o.material.name === 'car_paint') { o.material = o.material.clone(); o.material.color = col; }
        if (o.material.name === 'light_red') { o.material = o.material.clone(); brake.push(o.material); }
      });
      const box = new THREE.Box3().setFromObject(root);
      const len = box.max.x - box.min.x;
      // where the tyres meet the ground (model frame: +X forward, -Z left): front and rear axles, left and right tracks
      const wx = [], wz = [], wv = new THREE.Vector3();
      root.updateMatrixWorld(true);
      for (const w of wheels) { w.getWorldPosition(wv); wx.push(wv.x); wz.push(wv.z); }
      const tyres = wx.length ? { f: Math.max(...wx), r: Math.min(...wx), l: Math.min(...wz), rt: Math.max(...wz) } : { f: 1.4, r: -1.4, l: -0.75, rt: 0.75 };
      root.rotation.order = 'YZX';             // yaw, then pitch about its own Z, then roll about its own X
      let driver = null;
      if (cast && driverIds.length) {
        driver = cast.make(driverIds[Math.floor(rnd() * driverIds.length)], null);     // (no bag at the wheel)
        play(driver, 'sit', { fade: 0 });
        const [dx, dy, dz, lean] = DRIVER[kind];
        // car frame: +X forward, Blender +Y (left, the driver's side) is three -Z; the 'sit' clip puts the hips 0.22 above
        // the holder (leaning back about the holder takes the hips back with it: the seat a little forward for that)
        driver.holder.rotation.order = 'YXZ';
        driver.holder.position.set(dx + 0.22 * Math.sin(lean), dz, -dy);
        driver.holder.rotation.set(-lean, Math.PI / 2, 0);
        root.add(driver.holder);
      }
      scene.add(root);
      const lane = i < single || lanes.length === single ? lanes[i % lanes.length] : lanes[single + (i - single) % (lanes.length - single)];
      const k = 0.88 + rnd() * 0.2;            // how briskly this driver takes a lane's limits
      // wheel radius from the model, so the tyres roll without slipping
      const radius = wheels.length ? new THREE.Box3().setFromObject(wheels[0]).getSize(new THREE.Vector3()).y / 2 : 0.3;
      let s0 = ((i / n) * lane.length * lanes.length + rnd() * 20) % lane.length;
      if (lane.det && s0 > lane.det[0] - 12 && s0 < lane.det[1] + 6) s0 = lane.det[1] + 6 + rnd() * 20;   // (not inside a stall)
      this.cars.push({ root, lane, s: s0, speed: 8 + rnd() * 4, v: 8, len, wheels, brake, radius, driver, kind, k, tyres, pitch: 0, roll: 0,
        x: lane.at(s0).x, y: lane.at(s0).y, hx: 1, hy: 0, stopK: lane.stops ? lane.stops.filter((q) => q.s < s0).length : 0 });
    }
  }
  // 스쿠터를 탄 학생들 (blender/bikes.py): they ride the cars' loops round and out again, taking no stall.  The rider
  // sits on the 'sit' clip, the arms brought to the grips (reachFor, above); the scooter leans into the bends
  addBikes(scene, gltf, lanes, n, cast, riderIds, rndSeed = 31) {
    const rnd = mulberry(rndSeed);
    for (let i = 0; i < n && lanes.length; i++) {
      const root = gltf.scene.clone(true);
      const col = new THREE.Color(BIKE_COLORS[Math.floor(rnd() * BIKE_COLORS.length)]);
      const brake = [], wheels = [];
      root.traverse((o) => {
        if (/^wheel_/.test(o.name)) wheels.push(o);
        if (o.name === 'stand') o.visible = false;                  // (down on the parked ones: main.js)
        if (!o.isMesh) return;
        o.castShadow = true;
        o.receiveShadow = true;
        if (o.material.name === 'car_paint') { o.material = o.material.clone(); o.material.color = col; }
        if (o.material.name === 'light_red') { o.material = o.material.clone(); brake.push(o.material); }
      });
      root.updateMatrixWorld(true);
      const box = new THREE.Box3().setFromObject(root);
      const wx = wheels.map((w) => w.getWorldPosition(_s3).x);
      const tyres = { f: Math.max(...wx), r: Math.min(...wx), l: 0, rt: 0 };
      const radius = wheels.length ? new THREE.Box3().setFromObject(wheels[0]).getSize(_s3).y / 2 : 0.2;
      root.rotation.order = 'YZX';
      let driver = null, arms = null;
      if (cast && riderIds.length) {
        const id = riderIds[Math.floor(rnd() * riderIds.length)];
        driver = cast.make(id, null, crowdLook(id, 4100 + i * 7));
        play(driver, 'sit', { fade: 0 });
        driver.mixer.update(0);
        const h = driver.holder;
        h.rotation.order = 'YXZ';
        h.rotation.set(BIKE.lean, Math.PI / 2, 0);
        h.position.set(0, 0, 0);
        root.add(h);
        root.updateMatrixWorld(true);
        // the hips THIGH over the seat (as on the benches), on the scooter's middle line
        const legs = ['UpperLegL', 'UpperLegR'].map((b) => driver.root.getObjectByName(b)).filter(Boolean);
        _e3.set(0, 0.29 * driver.tall, 0);
        if (legs.length) { _e3.set(0, 0, 0); for (const b of legs) _e3.add(b.getWorldPosition(_w3)); _e3.multiplyScalar(1 / legs.length); }
        h.position.set(BIKE.seat[0] - _e3.x, BIKE.seat[1] + THIGH - _e3.y, -_e3.z);
        arms = ['L', 'R'].map((sd) => ['UpperArm', 'LowerArm', 'Wrist'].map((b) => driver.root.getObjectByName(b + sd)));
        if (arms.some((a) => a.some((b) => !b))) arms = null;
      }
      scene.add(root);
      const lane = lanes[i % lanes.length];
      const s0 = ((i + 0.37) / n * lane.length + rnd() * 30) % lane.length;
      this.cars.push({ root, lane, s: s0, speed: 6.5 + rnd() * 2.5, v: 6, len: box.max.x - box.min.x, wheels, brake, radius, driver, kind: 'scooter',
        k: 0.9 + rnd() * 0.15, tyres, pitch: 0, roll: 0, x: lane.at(s0).x, y: lane.at(s0).y, hx: 1, hy: 0, stopK: 0, bike: true, arms, hd0: null });
    }
  }
  // camPos: the view's centre (three coords); drivers of cars farther than the crowd's reach leave the car.
  // walkers: the crowd's people who walk (life.js Crowd, {x, y}): a car waits for one crossing just ahead of it
  // (the west sidewalk crosses the drive's mouth at the 삼거리, walks cross the drives), a few seconds at most
  update(dt, player, camPos = null, walkers = null) {
    const p = this.p ||= new THREE.Vector2(), d = this.d ||= new THREE.Vector2(), q = this.q ||= new THREE.Vector2();
    for (const c of this.cars) {
      const L = c.lane;
      // out of the gate and away for a while (a loop's two ends are one spot, side by side: the car that left would
      // be the one coming in), then in again once the lane's first metres are clear (every lane starts up 백양로)
      if (c.away > 0) {
        c.away -= dt;
        if (c.away > 0) continue;
        if (this.cars.some((o) => o !== c && !(o.away > 0) && o.s < 16)) { c.away = 0.6; continue; }
        c.s = 0; c.v = c.speed * 0.7; c.root.visible = true; c.stopK = 0;
      }
      // in its stall for a while (the driver gone meanwhile), or stopped a moment at the end of backing out
      if (c.parkT > 0) {
        c.parkT -= dt;
        const away = c.parked && c.parkT > 2 && c.parkT < c.parkT0 - 2.5;
        if (c.driver) {
          const h = c.driver.holder;
          if (away && h.parent) c.root.remove(h);
          else if (!away && !h.parent && (!camPos || (c.x - camPos.x) ** 2 + (c.y + camPos.z) ** 2 < FAR2)) c.root.add(h);
        }
        for (const m of c.brake) m.emissiveIntensity = c.parked && c.parkT < c.parkT0 - 1 && c.parkT > 1.2 ? 0.35 : 3.0;
        if (c.parkT > 0) continue;
        c.parked = false;
      }
      // a stall another car of this lane is in: past it, along the aisle (the way out ends where the way in began)
      if (L.det) {
        if (!c.inDet && c.s >= L.det[0] && c.s < L.det[1]) {
          if (L.user && L.user !== c && L.shared) { c.s = L.det[1] + (c.s - L.det[0]); c.stopK = L.stops.length; }
          else { L.user = c; c.inDet = true; }
        } else if (c.inDet && c.s >= L.det[1] + c.len) { c.inDet = false; if (L.user === c) L.user = null; }
      }
      L.at(c.s, p);
      L.dir(c.s, d);
      // brake for the player standing in the lane ahead, and keep a gap to the car in front
      const rx = player.x - p.x, ry = player.y - p.y;
      const ahead = rx * d.x + ry * d.y, lateral = Math.abs(-rx * d.y + ry * d.x);
      const reach = c.len / 2 + 4;
      let target = Math.min(c.speed, L.vmax(c.s) * c.k);
      if (ahead > 0 && ahead < reach + 10 && lateral < 2.0) target = ahead < reach ? 0 : c.speed * (ahead - reach) / 10;
      if (walkers && !(c.pushOn > 0)) {
        const near = c.len / 2 + 2.2;
        for (const w of walkers) {
          const wx = w.x - p.x, wy = w.y - p.y;
          if (wx > 12 || wx < -12 || wy > 12 || wy < -12) continue;
          const a = wx * d.x + wy * d.y;
          if (a > 0 && a < near + 5 && Math.abs(-wx * d.y + wy * d.x) < 1.5) target = Math.min(target, a < near ? 0 : c.speed * (a - near) / 5);
        }
        // (somebody standing in the way for long: on round them, slowly)
        c.waited = target === 0 && c.v < 0.2 ? (c.waited || 0) + dt : 0;
        if (c.waited > 5) { c.pushOn = 4; c.waited = 0; }
      } else if (c.pushOn > 0) { c.pushOn -= dt; target = Math.min(target, 2.5); }
      // The car in the way, whatever lane it is on (the lanes share the roads; they cross at the 삼거리 and in the
      // car parks): another car standing on this car's own line within the next metres.  One coming the other way on
      // its own side is not in the way (a tight bend's inner lane passes close to it); of two in each other's way
      // the one that has already given way waits; a car stuck behind another for long edges on.
      c.yieldTo = null;
      if (!(c.edge > 0)) {
        for (const o of this.cars) {
          if (o === c || o.away > 0 || o.yieldTo === c) continue;
          const ox = o.x - p.x, oy = o.y - p.y;
          if (ox > 18 || ox < -18 || oy > 18 || oy < -18) continue;
          let at = -1;
          for (let a = 1.5; a < c.len / 2 + 10.5; a += 1.5) {
            L.at(c.s + a, q);
            if ((q.x - o.x) ** 2 + (q.y - o.y) ** 2 < 2.4) { at = a; break; }
          }
          if (at < 0) continue;
          L.dir(c.s + at, q);
          if (o.v > 0.3 && o.hx * q.x + o.hy * q.y < -0.5) continue;
          const gap = at - (o.len + c.len) / 2;
          if (gap < 9) { target = Math.min(target, gap < 3 ? 0 : Math.max(0, o.v * (o.hx * q.x + o.hy * q.y)) * 0.9); c.yieldTo = o; }
        }
        c.stuck = c.yieldTo && c.v < 0.2 ? (c.stuck || 0) + dt : 0;
        if (c.stuck > 14) { c.edge = 3; c.stuck = 0; }
      } else { c.edge -= dt; target = Math.min(target, 1.5); }
      // the next stop on its lane: its stall, and the end of the way out backwards
      const stop = L.stops && c.stopK < L.stops.length ? L.stops[c.stopK] : null;
      if (stop) target = Math.min(target, Math.sqrt(2.4 * Math.max(0, stop.s - c.s - 0.04)) + 0.15);
      const prev = c.v;
      c.v += (target - c.v) * Math.min(1, dt * (target < c.v ? 3.5 : 1.2));
      const braking = c.v < prev - 0.02 || c.v < 0.3;
      for (const m of c.brake) m.emissiveIntensity = braking ? 3.0 : 0.35;
      c.s += c.v * dt;
      if (stop && c.s >= stop.s - 0.08) {
        c.s = stop.s; c.v = 0; c.stopK++;
        c.parked = !!stop.park;
        c.parkT = c.parkT0 = stop.park ? 18 + Math.random() * 45 : 0.9;
      }
      if (c.s > L.length) {
        if (L.loop) { c.away = 2 + Math.random() * 9; c.root.visible = false; continue; }
        c.s = 0;
      }
      L.at(c.s, p);
      // the way it points: along the lane, or against it while it backs out of its stall; one-sided at the stall and
      // at the end of the way out, where the line turns back on itself
      const back = !!L.rev && c.s > L.rev[0] - 1e-3 && c.s < L.rev[1] - 1e-3 && !(c.s <= L.rev[0] + 1e-3 && c.parkT > 0 && !c.parked);
      if (L.rev && Math.abs(c.s - L.rev[0]) < 1.6) {
        if (c.s <= L.rev[0] + 1e-3) d.copy(p).sub(L.at(c.s - 1.5, q)); else d.copy(L.at(c.s + 1.5, q)).sub(p);
        d.normalize();
      } else if (L.rev && Math.abs(c.s - L.rev[1]) < 1.6) {
        if (c.s < L.rev[1] - 1e-3) d.copy(p).sub(L.at(c.s - 1.5, q)); else d.copy(L.at(c.s + 1.5, q)).sub(p);
        d.normalize();
      } else L.dir(c.s, d);
      const g = back ? -1 : 1;
      c.x = p.x; c.y = p.y; c.hx = d.x * g; c.hy = d.y * g;
      // car model: +X forward
      c.root.rotation.y = Math.atan2(c.hy, c.hx);
      if (L.tracks) {
        const t = c.tyres, li = back ? 1 : 0;
        const fl = L.track(li, c.s + g * t.f), fr = L.track(1 - li, c.s + g * t.f), rl = L.track(li, c.s + g * t.r), rr = L.track(1 - li, c.s + g * t.r);
        const pitch = Math.max(-0.3, Math.min(0.3, Math.atan2((fl + fr - rl - rr) / 2, t.f - t.r)));
        // (the lean held to 7 deg: where a yard or a road at another height stands right beside the drive, the 5 m
        // grid tips the drive's edge towards it, tools/build_campus.py tr_grade)
        let roll = 0;
        if (c.bike) {
          // a scooter leans into the bend: by its speed and how fast its heading turns (left turn: the left side down)
          const hd = c.root.rotation.y;
          const w = c.hd0 === null || dt <= 0 ? 0 : wrapAngle(hd - c.hd0) / dt;
          c.hd0 = hd;
          c.turn = (c.turn || 0) + (w - (c.turn || 0)) * Math.min(1, dt * 2.5);
          roll = Math.max(-0.42, Math.min(0.42, -Math.atan(c.v * c.turn / 9.8)));
        } else roll = Math.max(-0.12, Math.min(0.12, Math.atan2((fl + rl - fr - rr) / 2, t.rt - t.l)));    // + : the left side up
        // (eased: the terrain's facets and the tracks' metre steps would nod it otherwise)
        const e = Math.min(1, dt * 9);
        c.pitch += (pitch - c.pitch) * e; c.roll += (roll - c.roll) * e;
        const mx = (t.f + t.r) / 2, mz = (t.l + t.rt) / 2;
        c.root.position.set(p.x, (fl + fr + rl + rr) / 4 - mx * Math.tan(c.pitch) + mz * Math.tan(c.roll), -p.y);
        c.root.rotation.z = c.pitch;
        c.root.rotation.x = c.roll;
      } else c.root.position.set(p.x, L.h(c.s), -p.y);
      for (const w of c.wheels) w.rotation.z -= g * (c.v * dt) / c.radius;
      if (c.driver) {
        const near = !camPos || (p.x - camPos.x) ** 2 + (p.y + camPos.z) ** 2 < FAR2;
        const h = c.driver.holder;
        if (near && !h.parent) c.root.add(h);
        else if (!near && h.parent) c.root.remove(h);
        if (near) c.driver.mixer.update(dt);
        if (near && c.arms) {                 // the rider's hands to the grips
          c.root.updateMatrixWorld(true);
          for (let k = 0; k < 2; k++) {
            const sd = k ? 1 : -1;            // (three z: the left grip at -z)
            _tg.set(BIKE.grip[0] - 0.07, BIKE.grip[2] + 0.015, sd * BIKE.grip[1]).applyMatrix4(c.root.matrixWorld);
            _pl.set(-0.2, -1, sd * 0.55).transformDirection(c.root.matrixWorld);
            reachFor(c.arms[k], _tg, _pl);
          }
        }
      }
    }
  }
  // circles along each car near the player, appended to out (reused circles per car: this runs every frame)
  movers(px, py, out) {
    for (const c of this.cars) {
      const x = c.root.position.x, y = -c.root.position.z;
      if (Math.abs(x - px) > 12 || Math.abs(y - py) > 12 || c.away > 0) continue;
      const fx = Math.cos(c.root.rotation.y), fy = Math.sin(c.root.rotation.y);
      const n = Math.max(1, Math.round(c.len / 1.6));
      const circles = (c.circles ||= Array.from({ length: n }, () => ({ x: 0, y: 0, r: 0.9 })));
      for (let k = 0; k < n; k++) {
        const t = (k / Math.max(1, n - 1) - 0.5) * (c.len - 1.6);
        circles[k].x = x + fx * t; circles[k].y = y + fy * t;
        out.push(circles[k]);
      }
    }
    return out;
  }
}
