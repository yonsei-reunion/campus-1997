// Campus life: 1997 banners (현수막) across 백양로, students walking, cars on the road.
import * as THREE from 'three';
import { mulberry, wrapAngle } from './util.js';
import { patchShader, restShadow } from './materials.js';
import { play, locomotion, gesturing } from './characters.js';
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

// b: { text, sub?, marks?: ['경', '축'], color }; H: canvas height for a 2048 px wide strip (the cloth's aspect)
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
    fitFont(x, '일시 · 장소 · 주최  연세대학교', bandH * 0.62, W * 0.5, 8);
    x.fillStyle = st.bandFg;
    x.fillText('일시 · 장소 · 주최  연세대학교', W / 2, band0 + bandH / 2 + 1);
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
// Walkers follow paths at their own pace and stop when you are in the way; groups stand and chat, nodding now and
// then. Far away people (and the drivers of far cars) leave the scene and their animation is not updated.
// Small talk (talk.js): two walkers coming towards each other near the view now and then stop, face each other, wave
// and trade a line or two; groups talk among themselves and greet you; a walker you block asks to get by.
const FAR2 = 190 * 190;
const TALK_NEAR2 = 45 * 45;        // talk only where it can be seen
const MAX_TALKS = 4;               // conversations at once round the view
const height = (id) => (id.startsWith('woman') ? 1.61 : 1.73);

export class Crowd {
  constructor(scene, cast, ids, paths, groups, count, rndSeed = 3) {
    this.scene = scene;
    this.people = [];
    const rnd = mulberry(rndSeed);
    const pick = () => ids[Math.floor(rnd() * ids.length)];
    // about 70 % carry a bag (bags.js: its own random stream, so the walkers' paths stay where they were)
    for (let i = 0; i < count; i++) {
      const id = pick();
      const a = cast.make(id, crowdBag(id, i));
      const path = paths[Math.floor(rnd() * paths.length)];
      const p = { a, path, s: rnd() * path.length, dir: rnd() < 0.5 ? 1 : -1, speed: 1.15 + rnd() * 0.4, side: (rnd() - 0.5) * 0.8,
        heading: 0, walking: true, gestureAt: 5 + rnd() * 30, tick: i & 1,
        kind: kindOf(a.id), top: height(a.id), x: 1e9, y: 1e9, fx: 0, fy: 0,
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
        const a = cast.make(id, crowdBag(id, 1000 + this.people.length));
        a.mixer.setTime(rnd() * 2);
        a.holder.position.set(x, h, -y);
        const heading = Math.atan2(gx - x, -(gy - y));
        a.holder.rotation.y = heading;
        scene.add(a.holder);
        const p = { a, walking: false, heading, home: heading, gestureAt: 3 + rnd() * 20, tick: k & 1, x, y,
          kind: kindOf(a.id), top: height(a.id), group: g };
        g.people.push(p);
        this.people.push(p);
      }
    }
    this.v = new THREE.Vector2();
    this.d = new THREE.Vector2();
    this.frame = 0;
    this.season = 'summer';        // main.js keeps it on the month picked
    this.bubbles = null;           // talk.js Bubbles (main.js); without it people still stop and wave, silently
    this.talks = [];               // end times of the conversations going on
    this.cues = [];                // gestures timed to the lines: { at, p }
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
        // stop for the player standing in front, and look at them
        const tx = player.x - v.x, ty = player.y - v.y, td = Math.hypot(tx, ty);
        const ahead = (tx * d.x + ty * d.y) / (td || 1);
        const blocked = td < 1.3 && ahead > 0.2;
        const halt = t < p.chatUntil || gesturing(a);       // talking: stand still facing the other
        if (halt) {
          const o = p.face?.a.holder.position;
          if (o) want = Math.atan2(o.x - hp.x, o.z - hp.z);
        } else if (!blocked) {
          speed = p.speed;
          p.s += p.dir * speed * dt;
          if (p.s > p.path.length) { p.s = p.path.length; p.dir = -1; }
          if (p.s < 0) { p.s = 0; p.dir = 1; }
          p.path.at(p.s, v);
          want = Math.atan2(d.x, -d.y);
        } else want = Math.atan2(tx, -ty);
        hp.set(v.x - d.y * p.side, p.path.h(p.s), -(v.y + d.x * p.side));
        p.x = hp.x; p.y = -hp.z; p.fx = d.x; p.fy = d.y;
        // blocked for a moment: ask to get by (not everyone, and not all at once on a busy sidewalk)
        if (blocked && !halt) {
          p.blockedT += dt;
          if (p.blockedT > 1.1 && t > p.excuseAfter) {
            p.excuseAfter = t + 60;
            if (t > this.excuseAt && Math.random() < 0.6) { this.excuseAt = t + 10; this.say(p, excuse(p.kind, this.season), t); }
          }
        } else p.blockedT = 0;
      } else {
        const tx = player.x - p.x, ty = player.y - p.y;
        want = Math.hypot(tx, ty) < 2.6 ? Math.atan2(tx, -ty) : p.home;      // turn to greet you
      }
      if (want !== null) {
        p.heading += wrapAngle(want - p.heading) * (1 - Math.exp(-dt * 7));
        a.holder.rotation.y = p.heading;
      }
      // far away: out of the scene graph altogether (hiding it would still update its ~60 bones every frame)
      if (far > FAR2) { if (a.holder.parent) this.scene.remove(a.holder); continue; }
      if (!a.holder.parent) this.scene.add(a.holder);
      if (!p.walking && t > p.gestureAt) {
        p.gestureAt = t + 12 + Math.random() * 20;
        // (a bag carried in the right hand: wave with the left)
        playGesture(a, Math.random() < 0.7 || carriesInHand(a.bag) ? 'emote-yes' : 'interact-right');
      }
      locomotion(a, speed);
      // distant people animate at half rate
      if (far < 70 * 70) a.mixer.update(dt);
      else if ((this.frame & 1) === p.tick) a.mixer.update(dt * 2);
    }
    for (let i = this.cues.length - 1; i >= 0; i--) {
      const c = this.cues[i];
      if (t < c.at) continue;
      if (c.p.a.holder.parent) playGesture(c.p.a, 'emote-yes');
      this.cues.splice(i, 1);
    }
    this.scanT -= dt;
    if (this.scanT <= 0) { this.scanT = 0.2; this.socialize(t, player, camPos); }
  }

  // one line over p's head, now
  say(p, text, t) { this.bubbles?.add(p.a.holder, p.top, text, t, t + lineTime(text)); }

  // lines one after another from t0 (speakers[who] speaks each); returns when the last one is done
  converse(speakers, lines, t0) {
    let at = t0;
    for (const l of lines) {
      const p = speakers[l.who], dur = lineTime(l.text);
      this.bubbles?.add(p.a.holder, p.top, l.text, at, at + dur);
      if (l.wave) this.cues.push({ at, p });
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
  constructor(scene, armGltf, booth, lanes, groundAt, shadows = null) {
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
      // the road heading there, and the way the lane's cars run along it (+1 northbound, the arm pointing east)
      const head = a.dir - a.side * Math.PI / 2;
      this.arms.push({ root, a, lane: lanes[a.side > 0 ? 1 : 0], fx: Math.cos(head) * -a.side, fy: Math.sin(head) * -a.side, lift: 0 });
    }
  }
  update(dt, traffic) {
    for (const g of this.arms) {
      let open = false;
      for (const c of traffic.cars) {
        if (c.lane !== g.lane) continue;
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
// 1997 paint: lots of white, silver and dark navy, the mid-90s dark green (진녹색), a few wine / gunmetal / gold
export const CAR_COLORS = ['#eeeeea', '#f2f1ec', '#b9bdc3', '#a9aeb5', '#1b2333', '#2a2d33', '#6e1b1f', '#244a3a', '#1d3b30', '#3a3f45', '#b59a6a', '#2c4a78'];
// sedan 쏘나타Ⅱ type, sedan2 프린스 type, hatch 프라이드 type, tico 티코 type, van 그레이스 type (blender/cars.py)
const WEIGHTS = { sedan: 4, sedan2: 3, hatch: 3, tico: 2, taxi: 3, van: 2 };
// driver's hips in the car frame (blender/cars.py driver_seat, times CAR_SCALE 1.07)
const DRIVER = { sedan: [-0.05, 0.40], sedan2: [-0.03, 0.40], hatch: [-0.27, 0.39], tico: [-0.32, 0.33], taxi: [-0.05, 0.40], van: [0.98, 0.40] };

export class Traffic {
  constructor(scene, carGltfs, lanes, n = 12, cast = null, driverIds = [], rndSeed = 9) {
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
      let driver = null;
      if (cast && driverIds.length) {
        driver = cast.make(driverIds[Math.floor(rnd() * driverIds.length)], null);     // (no bag at the wheel)
        play(driver, 'sit', { fade: 0 });
        const [dx, dy] = DRIVER[kind];
        // car frame: +X forward, Blender +Y (left, the driver's side) is three -Z; the 'sit' clip puts the hips 0.22 above
        // the holder, so 0.30 seats them low (~0.52 m) as in a real car and keeps the head under the roof
        driver.holder.position.set(dx, 0.30, -dy);
        driver.holder.rotation.y = Math.PI / 2;
        root.add(driver.holder);
      }
      scene.add(root);
      const lane = lanes[i % lanes.length];
      // wheel radius from the model, so the tyres roll without slipping
      const radius = wheels.length ? new THREE.Box3().setFromObject(wheels[0]).getSize(new THREE.Vector3()).y / 2 : 0.3;
      this.cars.push({ root, lane, s: (i / n) * lane.length * 2 % lane.length + rnd() * 20, speed: 8 + rnd() * 4,
        v: 8, len, wheels, brake, radius, driver, kind });
    }
  }
  // camPos: the view's centre (three coords); drivers of cars farther than the crowd's reach leave the car
  update(dt, player, camPos = null) {
    const p = this.p ||= new THREE.Vector2(), d = this.d ||= new THREE.Vector2();
    for (const c of this.cars) {
      c.lane.at(c.s, p);
      c.lane.dir(c.s, d);
      // brake for the player standing in the lane ahead, and keep a gap to the car in front
      const rx = player.x - p.x, ry = player.y - p.y;
      const ahead = rx * d.x + ry * d.y, lateral = Math.abs(-rx * d.y + ry * d.x);
      const reach = c.len / 2 + 4;
      let target = c.speed;
      if (ahead > 0 && ahead < reach + 10 && lateral < 2.0) target = ahead < reach ? 0 : c.speed * (ahead - reach) / 10;
      for (const o of this.cars) {
        if (o === c || o.lane !== c.lane) continue;
        const gap = o.s - c.s - (o.len + c.len) / 2;
        if (gap > -1 && gap < 9) target = Math.min(target, gap < 3 ? 0 : o.v * 0.9);
      }
      const prev = c.v;
      c.v += (target - c.v) * Math.min(1, dt * (target < c.v ? 3.5 : 1.2));
      const braking = c.v < prev - 0.02 || c.v < 0.3;
      for (const m of c.brake) m.emissiveIntensity = braking ? 3.0 : 0.35;
      c.s += c.v * dt;
      if (c.s > c.lane.length) c.s = 0;
      c.lane.at(c.s, p);
      c.lane.dir(c.s, d);
      c.root.position.set(p.x, c.lane.h(c.s), -p.y);
      // car model: +X forward
      c.root.rotation.y = Math.atan2(d.y, d.x);
      for (const w of c.wheels) w.rotation.z -= (c.v * dt) / c.radius;
      if (c.driver) {
        const near = !camPos || (p.x - camPos.x) ** 2 + (p.y + camPos.z) ** 2 < FAR2;
        const h = c.driver.holder;
        if (near && !h.parent) c.root.add(h);
        else if (!near && h.parent) c.root.remove(h);
        if (near) c.driver.mixer.update(dt);
      }
    }
  }
  // circles along each car near the player, appended to out (reused circles per car: this runs every frame)
  movers(px, py, out) {
    for (const c of this.cars) {
      const x = c.root.position.x, y = -c.root.position.z;
      if (Math.abs(x - px) > 12 || Math.abs(y - py) > 12) continue;
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
