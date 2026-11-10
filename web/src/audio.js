// Sound. Nothing is recorded: every sound is made here with the Web Audio API from noise and a few oscillators (as
// tools/trailer/birthday_video.py makes the birthday film's), so there is no file to load and no licence to keep.
//  - the air: a breath of wind, the leaves' rustle where trees stand round the listener (campus.json trees), rising
//    and falling with the gusts that sway them, a far city rumble
//  - birds: small birds' chirps from the trees round you, the magpies' chatter and the pigeons' coo from where
//    birds.js has them, their wings when they go up
//  - 활천대's fountain, heard from where it stands
//  - cars: engine and tyres of the nearest few, by their speed
//  - footsteps: yours when a foot of the walk or run cycle comes down, on what you walk on (ground_splat.png: paving
//    and asphalt, earth, lawn; steps and terraces are stone); those of the people walking close by
//  - the basketball (bounce, rim, backboard, net) and the birthday splash
// The listener is the camera. The context starts on the first click (browsers allow no sound before one) and
// sleeps while the tab is hidden. 「소리」 in the pause card turns it off (remembered).
import * as THREE from 'three';
import { MOBILE, safeGet, safeSet, versioned } from './util.js';

const AC = window.AudioContext || window.webkitAudioContext;
const VOLUME = 0.9;
const CAR_VOICES = MOBILE ? 2 : 4, CAR_R = 75;
const STEP_R = 9;                    // other people's footsteps are heard this close to the walker
const SEASON_LEAF = { spring: 0.6, summer: 1, autumn: 0.85 };       // how much there is to rustle
const SEASON_BIRD = { spring: 1.2, summer: 1, autumn: 0.6 };
const _v = new THREE.Vector3(), _f = new THREE.Vector3();
const rand = (a, b) => a + Math.random() * (b - a);

function noiseBuffer(ctx, seconds, channels, pink = false) {
  const n = Math.floor(ctx.sampleRate * seconds), buf = ctx.createBuffer(channels, n, ctx.sampleRate);
  for (let c = 0; c < channels; c++) {
    const d = buf.getChannelData(c);
    let b0 = 0, b1 = 0, b2 = 0;
    for (let i = 0; i < n; i++) {
      const w = Math.random() * 2 - 1;
      if (!pink) { d[i] = w; continue; }
      // (Paul Kellet's economy pink filter)
      b0 = 0.99765 * b0 + w * 0.0990460; b1 = 0.96300 * b1 + w * 0.2965164; b2 = 0.57000 * b2 + w * 1.0526913;
      d[i] = (b0 + b1 + b2 + w * 0.1848) * 0.22;
    }
  }
  return buf;
}

export class Sound {
  constructor({ camera, campus, hf }) {
    Object.assign(this, { camera, campus, hf });
    this.on = safeGet('y97-sound') !== '0';
    this.ctx = null;
    this.stats = { steps: 0, chirps: 0, calls: 0, flaps: 0, balls: 0 };      // (for the tests)
    // trees per 16 m cell: how leafy it is round a point
    this.cell = 16;
    this.trees = new Map();
    for (const t of campus.trees || []) {
      const k = this._key(t[1], t[2]);
      this.trees.set(k, (this.trees.get(k) || 0) + 1);
    }
    this.ground = null;              // ground_splat.png at 1 m: R asphalt, G paving, B earth, the rest lawn
    const S = this.rect = campus.splat;
    this.gw = Math.round(S.x1 - S.x0); this.gh = Math.round(S.y1 - S.y0);
    this.feet = null; this.stepActor = null;
    this.nextChirp = 2; this.nextCall = 6;
    this.cars = [];
    addEventListener('visibilitychange', () => { if (this.ctx) (document.hidden ? this.ctx.suspend() : this.ctx.resume()); });
  }

  _key(x, y) { return Math.floor(x / this.cell) * 4096 + Math.floor(y / this.cell); }

  // 0..1: how many trees stand within about 25 m
  leafy(x, y) {
    let n = 0;
    for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) n += this.trees.get(this._key(x + i * this.cell, y + j * this.cell)) || 0;
    return Math.min(1, n / 14);
  }

  // what is walked on at campus (x, y), the walker's feet at height gy
  surface(x, y, gy) {
    if (gy - this.hf.height(x, y) > 0.3) return 'hard';              // steps, terraces, the court's slab
    const d = this.ground, S = this.rect;
    const u = Math.floor(x - S.x0), v = Math.floor(S.y1 - y);
    if (!d || u < 0 || v < 0 || u >= this.gw || v >= this.gh) return 'grass';
    const k = (v * this.gw + u) * 4;
    return d[k] + d[k + 1] > 127 ? 'hard' : d[k + 2] > 127 ? 'dirt' : 'grass';
  }

  // (call from a click: browsers start no audio before one)
  start() {
    if (this.ctx || !AC) return;
    let ctx;
    try { ctx = this.ctx = new AC({ latencyHint: 'interactive' }); } catch { return; }
    this.master = ctx.createGain();
    this.master.gain.value = this.on ? VOLUME : 0;
    const lim = ctx.createDynamicsCompressor();
    Object.assign(lim.threshold, { value: -9 }); Object.assign(lim.ratio, { value: 10 });
    Object.assign(lim.attack, { value: 0.003 }); Object.assign(lim.release, { value: 0.2 });
    this.tap = ctx.createAnalyser();              // (levels, for the tests)
    this.tap.fftSize = 2048;
    // (nothing below 35 Hz: the pink noise's sub-bass only eats headroom)
    this._chain(this.master, this._filter('highpass', 35, 0.7), lim);
    lim.connect(this.tap); lim.connect(ctx.destination);
    this.white = noiseBuffer(ctx, 3, 2);
    this.pink = noiseBuffer(ctx, 4, 2, true);
    this._beds();
    this._loadGround();
  }

  setOn(v) {
    this.on = v;
    safeSet('y97-sound', v ? '1' : '0');
    if (this.ctx) this.master.gain.setTargetAtTime(v ? VOLUME : 0, this.ctx.currentTime, 0.08);
  }

  async _loadGround() {
    try {
      const img = await createImageBitmap(await (await fetch(versioned('assets/textures/ground_splat.png'))).blob());
      const c = document.createElement('canvas');
      c.width = this.gw; c.height = this.gh;
      const x = c.getContext('2d', { willReadFrequently: true });
      x.drawImage(img, 0, 0, this.gw, this.gh);
      img.close?.();
      this.ground = x.getImageData(0, 0, this.gw, this.gh).data;
    } catch { /* every step sounds of lawn */ }
  }

  // ---------------------------------------------------------------- building blocks
  _loop(buffer, rate = 1) {
    const s = this.ctx.createBufferSource();
    s.buffer = buffer; s.loop = true; s.playbackRate.value = rate;
    s.start(0, Math.random() * buffer.duration);
    return s;
  }

  _filter(type, f, q = 0.7) {
    const b = this.ctx.createBiquadFilter();
    b.type = type; b.frequency.value = f; b.Q.value = q;
    return b;
  }

  _gain(v = 0) { const g = this.ctx.createGain(); g.gain.value = v; return g; }

  // a point in the world (three coordinates): what goes into it is heard from there
  _panner(x, y, z, ref = 4, rolloff = 1.3) {
    const p = this.ctx.createPanner();
    p.panningModel = 'equalpower'; p.distanceModel = 'inverse';
    p.refDistance = ref; p.rolloffFactor = rolloff; p.maxDistance = 400;
    this._place(p, x, y, z);
    p.connect(this.master);
    return p;
  }

  _place(p, x, y, z) {
    if (p.positionX) { p.positionX.value = x; p.positionY.value = y; p.positionZ.value = z; } else p.setPosition(x, y, z);
  }

  // chain the nodes, return the last
  _chain(...nodes) { for (let i = 1; i < nodes.length; i++) nodes[i - 1].connect(nodes[i]); return nodes[nodes.length - 1]; }

  // a burst of noise through a filter with an attack / decay envelope, into `out` (decay: the time to fall 40 dB)
  _burst(out, { at = this.ctx.currentTime, type = 'bandpass', f = 1000, q = 0.8, f1 = null, gain = 0.2, attack = 0.004, decay = 0.08, pink = false }) {
    const ctx = this.ctx, src = ctx.createBufferSource();
    src.buffer = pink ? this.pink : this.white;
    const fl = this._filter(type, f, q), g = this._gain(0);
    if (f1) fl.frequency.exponentialRampToValueAtTime(f1, at + attack + decay);
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(gain, at + attack);
    g.gain.exponentialRampToValueAtTime(Math.max(1e-5, gain * 0.01), at + attack + decay);
    g.gain.linearRampToValueAtTime(0, at + attack + decay + 0.012);
    this._chain(src, fl, g, out);
    src.start(at, Math.random() * 2);
    src.stop(at + attack + decay + 0.03);
  }

  // a tone with a frequency glide and an attack / decay envelope
  _tone(out, { at = this.ctx.currentTime, type = 'sine', f = 440, f1 = null, gain = 0.2, attack = 0.005, decay = 0.1, hold = 0 }) {
    const ctx = this.ctx, o = ctx.createOscillator(), g = this._gain(0);
    o.type = type;
    o.frequency.setValueAtTime(f, at);
    if (f1) o.frequency.exponentialRampToValueAtTime(f1, at + attack + hold + decay);
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(gain, at + attack);
    if (hold) g.gain.setValueAtTime(gain, at + attack + hold);
    g.gain.exponentialRampToValueAtTime(Math.max(1e-5, gain * 0.01), at + attack + hold + decay);
    g.gain.linearRampToValueAtTime(0, at + attack + hold + decay + 0.012);
    this._chain(o, g, out);
    o.start(at);
    o.stop(at + attack + hold + decay + 0.03);
    return o;
  }

  // ---------------------------------------------------------------- the beds that play all the time
  _beds() {
    const ctx = this.ctx;
    // wind: a low breath; the leaves: a bright hiss; the city: a far rumble under everything
    this.windG = this._gain(0);
    this._chain(this._loop(this.pink), this._filter('highpass', 110, 0.5), this._filter('lowpass', 650, 0.5), this.windG, this.master);
    this.leafG = this._gain(0);
    this.leafF = this._filter('lowpass', 7000, 0.5);
    this._chain(this._loop(this.white, 0.9), this._filter('highpass', 2600, 0.5), this.leafF, this.leafG, this.master);
    this._chain(this._loop(this.pink, 0.5), this._filter('highpass', 50, 0.5), this._filter('lowpass', 180, 0.5), this._gain(0.03), this.master);
    // the fountain: falling water, with a slow swell of its own
    const F = this.campus.statues?.fountain;
    if (F) {
      this.fountain = this._panner(F.pos[0], (F.h ?? this.hf.height(F.pos[0], F.pos[1])) + 1.2, -F.pos[1], 5, 1.6);
      this.fountainG = this._gain(0.34);
      this._chain(this._loop(this.white, 1.1), this._filter('highpass', 380, 0.5), this._filter('lowpass', 6200, 0.5), this.fountainG, this.fountain);
      this._chain(this._loop(this.pink, 0.7), this._filter('bandpass', 260, 0.8), this._gain(0.2), this.fountain);     // the basin's low gurgle
    }
    // the cars' voices: a low sawtooth for the engine, a band of noise for the tyres
    for (let i = 0; i < CAR_VOICES; i++) {
      const pan = this._panner(0, 0, 0, 5, 1.5), out = this._gain(0);
      const osc = ctx.createOscillator();
      osc.type = 'sawtooth'; osc.frequency.value = 50;
      const eg = this._gain(0.16), tg = this._gain(0);
      this._chain(osc, this._filter('lowpass', 420, 0.7), eg, out);
      const tf = this._filter('bandpass', 800, 0.5);
      this._chain(this._loop(this.pink), tf, tg, out);
      out.connect(pan);
      osc.start();
      this.cars.push({ pan, out, osc, tg, tf, car: null });
    }
  }

  // ---------------------------------------------------------------- every frame
  // s: { player, walking (the walk is on, not the bird's-eye view), crowd, traffic, birds, season }
  update(dt, t, s) {
    const ctx = this.ctx;
    if (!ctx || ctx.state !== 'running') return;
    const now = ctx.currentTime, cam = this.camera, cp = cam.position;
    // the listener: the camera
    cam.getWorldDirection(_f);
    const L = ctx.listener;
    if (L.positionX) {
      L.positionX.value = cp.x; L.positionY.value = cp.y; L.positionZ.value = cp.z;
      L.forwardX.value = _f.x; L.forwardY.value = _f.y; L.forwardZ.value = _f.z;
      L.upX.value = 0; L.upY.value = 1; L.upZ.value = 0;
    } else { L.setPosition(cp.x, cp.y, cp.z); L.setOrientation(_f.x, _f.y, _f.z, 0, 1, 0); }
    const x = cp.x, y = -cp.z, alt = Math.max(0, cp.y - this.hf.height(x, y));
    const low = Math.exp(-alt / 60);                                   // what is heard of the ground from up there
    // the gusts (the same slow swell the trees and banners take, materials.js sway)
    const gust = 0.5 + 0.32 * Math.sin(t * 0.21) + 0.18 * Math.sin(t * 0.53 + 1.3);
    const leafy = this.leafy(x, y) * (SEASON_LEAF[s.season] ?? 1);
    this.windG.gain.setTargetAtTime(0.03 + 0.06 * gust + 0.12 * (1 - low), now, 0.4);
    this.leafG.gain.setTargetAtTime(leafy * low * (0.012 + 0.07 * gust * gust), now, 0.4);
    this.leafF.frequency.setTargetAtTime(5200 + 3000 * gust, now, 0.5);
    if (this.fountainG) this.fountainG.gain.setTargetAtTime(0.3 + 0.06 * Math.sin(t * 1.7) + 0.04 * Math.sin(t * 4.1), now, 0.2);
    this._birds(t, s, x, y, cp.y, alt, leafy);
    this._cars(now, s.traffic, x, y);
    if (s.walking) this._steps(dt, s);
  }

  // ---------------------------------------------------------------- birds
  _birds(t, s, x, y, h, alt, leafy) {
    if (alt > 90) return;
    if (t > this.nextChirp) {
      const k = (0.35 + leafy) * (SEASON_BIRD[s.season] ?? 1);
      this.nextChirp = t + rand(1.4, 6) / k;
      const a = rand(0, 6.283), d = rand(9, 38);
      this.chirp(x + Math.cos(a) * d, h - alt + rand(3, 9), -(y + Math.sin(a) * d));
    }
    if (t > this.nextCall) {
      this.nextCall = t + rand(7, 22);
      // a magpie's chatter or a pigeon's coo from one of the spots near by with birds on it
      const near = (s.birds?.spots || []).filter((sp) => sp.birds.length && (sp.x - x) ** 2 + (sp.y - y) ** 2 < (sp.kind === 'magpie' ? 80 : 30) ** 2);
      if (near.length) {
        const sp = near[Math.floor(Math.random() * near.length)], b = sp.birds[Math.floor(Math.random() * sp.birds.length)];
        const bh = (b.h ?? this.hf.height(b.x, b.y)) + 0.2;
        if (sp.kind === 'magpie') this.magpie(b.x, bh, -b.y); else this.coo(b.x, bh, -b.y);
      }
    }
  }

  // a small bird in a tree: a few quick chirps, two alternating notes, or a short warble
  chirp(x, y, z) {
    const ctx = this.ctx, out = this._panner(x, y, z, 12, 0.8), t0 = ctx.currentTime + 0.02;
    const kind = Math.random(), g = rand(0.1, 0.2);
    this.stats.chirps++;
    if (kind < 0.45) {              // 짹 짹 짹
      const n = 2 + Math.floor(Math.random() * 4), f = rand(3600, 5200), gap = rand(0.11, 0.17);
      for (let i = 0; i < n; i++) this._tone(out, { at: t0 + i * gap, f: f * rand(0.97, 1.05), f1: f * 0.62, gain: g, attack: 0.008, decay: 0.06 });
    } else if (kind < 0.8) {        // 쯔-삐 쯔-삐
      const hi = rand(5200, 6400), lo = hi * rand(0.66, 0.75), n = 2 + Math.floor(Math.random() * 3);
      for (let i = 0; i < n; i++) {
        this._tone(out, { at: t0 + i * 0.3, f: hi, f1: hi * 0.97, gain: g * 0.8, attack: 0.01, hold: 0.05, decay: 0.05 });
        this._tone(out, { at: t0 + i * 0.3 + 0.14, f: lo, f1: lo * 0.96, gain: g, attack: 0.01, hold: 0.06, decay: 0.06 });
      }
    } else {                        // a warble: a tone with a fast vibrato
      const o = this._tone(out, { at: t0, f: rand(2800, 3900), gain: g, attack: 0.03, hold: rand(0.12, 0.3), decay: 0.08 });
      const lfo = ctx.createOscillator(), depth = this._gain(rand(500, 900));
      lfo.frequency.value = rand(18, 30);
      lfo.connect(depth); depth.connect(o.frequency);
      lfo.start(t0); lfo.stop(t0 + 0.6);
    }
  }

  // 까치: 깍 깍 깍 깍, harsh and dry
  magpie(x, y, z) {
    const ctx = this.ctx, out = this._panner(x, y, z, 7, 1.0), t0 = ctx.currentTime + 0.02;
    const n = 3 + Math.floor(Math.random() * 5), gap = rand(0.15, 0.19);
    this.stats.calls++;
    const band = this._filter('bandpass', rand(2300, 2900), 0.9);
    band.connect(out);
    for (let i = 0; i < n; i++) {
      const at = t0 + i * gap * rand(0.95, 1.08);
      this._tone(band, { at, type: 'sawtooth', f: rand(430, 520), f1: 380, gain: 0.26, attack: 0.006, hold: 0.04, decay: 0.05 });
      this._burst(band, { at, type: 'highpass', f: 1500, gain: 0.3, attack: 0.005, decay: 0.085 });
    }
  }

  // 비둘기: 구구 구-
  coo(x, y, z) {
    const out = this._panner(x, y, z, 4, 1.2), t0 = this.ctx.currentTime + 0.02;
    this.stats.calls++;
    const f = rand(330, 400);
    let at = t0;
    for (const [dur, a, b] of [[0.16, 1, 1.04], [0.14, 1.03, 1], [0.42, 1.12, 0.9]]) {
      this._tone(out, { at, f: f * a, f1: f * b, gain: 0.3, attack: 0.04, hold: dur, decay: 0.09 });
      at += dur + 0.17;
    }
  }

  // wings going up (birds.js take-off): a few soft beats
  flap(x, y, z) {
    if (!this.ctx || this.ctx.state !== 'running') return;
    const out = this._panner(x, y, z, 3, 1.4), t0 = this.ctx.currentTime;
    this.stats.flaps++;
    const n = 6 + Math.floor(Math.random() * 4), beat = rand(0.085, 0.105);
    for (let i = 0; i < n; i++) {
      this._burst(out, { at: t0 + i * beat, type: 'lowpass', f: 2200 - i * 90, gain: 0.7 * (1 - i / (n + 3)), attack: 0.012, decay: 0.07 });
    }
  }

  // ---------------------------------------------------------------- cars
  _cars(now, traffic, x, y) {
    if (!traffic) return;
    // the nearest moving cars take the voices; a voice whose car has left fades out before it takes another
    const near = [];
    for (const c of traffic.cars) {
      const d = (c.root.position.x - x) ** 2 + (c.root.position.z + y) ** 2;
      if (d < CAR_R * CAR_R) near.push([d, c]);
    }
    near.sort((a, b) => a[0] - b[0]);
    const want = near.slice(0, this.cars.length).map((e) => e[1]);
    for (const v of this.cars) {
      if (v.car && !want.includes(v.car)) { v.car = null; v.free = now + 0.25; v.out.gain.setTargetAtTime(0, now, 0.06); }
    }
    for (const c of want) {
      if (this.cars.some((v) => v.car === c)) continue;
      const v = this.cars.find((o) => !o.car && !(o.free > now));
      if (v) v.car = c;
    }
    for (const v of this.cars) {
      const c = v.car;
      if (!c) continue;
      const p = c.root.position, sp = Math.abs(c.v);
      this._place(v.pan, p.x, p.y + 0.6, p.z);
      const small = c.kind === 'tico' ? 1.25 : c.kind === 'van' ? 0.85 : 1;
      v.osc.frequency.setTargetAtTime((34 + sp * 5.5) * small, now, 0.12);       // idling to third gear
      v.tg.gain.setTargetAtTime(Math.min(1, sp / 12) ** 1.5 * 0.9, now, 0.1);
      v.tf.frequency.setTargetAtTime(600 + sp * 70, now, 0.2);
      v.out.gain.setTargetAtTime(0.75, now, 0.15);
    }
  }

  // ---------------------------------------------------------------- footsteps
  _steps(dt, s) {
    const pl = s.player, a = pl.actor;
    if (a !== this.stepActor) {
      this.stepActor = a;
      this.feet = ['FootL', 'FootR'].map((n) => ({ bone: a.root.getObjectByName(n), min: 1e9, down: true }));
    }
    const sp = Math.abs(pl.speed);
    if (sp > 0.4 && !pl.scripted) {
      // a foot comes down: its bone back near the lowest it goes in the cycle after having been lifted
      for (const f of this.feet) {
        if (!f.bone) continue;
        const fy = f.bone.getWorldPosition(_v).y - pl.pos.y;
        f.min = Math.min(f.min + dt * 0.01, fy);
        if (f.down) { if (fy > f.min + 0.06) f.down = false; }
        else if (fy < f.min + 0.025) {
          f.down = true;
          this.step(this.surface(pl.x, pl.y, pl.pos.y), sp > 3.4 ? 1 : 0.62, null);
        }
      }
    } else if (this.feet) for (const f of this.feet) f.down = true;
    // the people walking by: a step every stride
    for (const p of s.crowd?.people || []) {
      if (!p.walking) continue;
      const dx = p.x - pl.x, dy = p.y - pl.y;
      if (dx * dx + dy * dy > STEP_R * STEP_R) { p._ax = undefined; continue; }
      if (p._ax !== undefined) {
        p._ad = (p._ad || 0) + Math.hypot(p.x - p._ax, p.y - p._ay);
        if (p._ad > 0.7 * (p.a.tall || 1)) {
          p._ad = 0;
          const hp = p.a.holder.position;
          this.step(this.surface(p.x, p.y, hp.y), 0.4, hp);
        }
      }
      p._ax = p.x; p._ay = p.y;
    }
  }

  // one footstep on `kind` (hard, dirt, grass), `w` its weight (a run lands harder); at: three position (null: yours)
  step(kind, w, at) {
    const ctx = this.ctx;
    if (!ctx || ctx.state !== 'running') return;
    this.stats.steps++;
    const out = at ? this._panner(at.x, at.y + 0.1, at.z, 2.5, 1.6) : this.master;
    const t0 = ctx.currentTime, v = rand(0.85, 1.15);
    if (kind === 'hard') {
      // the heel's knock and the sole's scuff on paving
      this._tone(out, { at: t0, f: 150 * v, f1: 70, gain: 0.24 * w, attack: 0.003, decay: 0.07 });
      this._burst(out, { at: t0, f: 1700 * v, q: 0.9, gain: 0.5 * w, attack: 0.002, decay: 0.05 });
      this._burst(out, { at: t0 + 0.035, f: 3200 * v, q: 0.7, gain: 0.14 * w, attack: 0.01, decay: 0.09 });
    } else if (kind === 'dirt') {
      this._tone(out, { at: t0, f: 110 * v, f1: 60, gain: 0.18 * w, attack: 0.004, decay: 0.07 });
      this._burst(out, { at: t0, f: 900 * v, q: 0.6, gain: 0.5 * w, attack: 0.004, decay: 0.1 });
      this._burst(out, { at: t0 + 0.02, f: 4200 * v, q: 0.8, gain: 0.2 * w, attack: 0.008, decay: 0.08 });       // grit
    } else {
      // lawn: a soft thud and the blades' swish
      this._tone(out, { at: t0, f: 90 * v, f1: 55, gain: 0.14 * w, attack: 0.006, decay: 0.08 });
      this._burst(out, { at: t0, f: 2600 * v, q: 0.5, gain: 0.4 * w, attack: 0.02, decay: 0.18 });
    }
  }

  // ---------------------------------------------------------------- the ball, the splash
  // hoops.js: what = bounce | rim | board | swish, p: three position, k: how hard (m/s)
  ball(what, p, k = 3) {
    const ctx = this.ctx;
    if (!ctx || ctx.state !== 'running') return;
    this.stats.balls++;
    const out = this._panner(p.x, p.y, p.z, 4, 1.2), t0 = ctx.currentTime, w = Math.min(1, k / 7);
    if (what === 'bounce') {
      // the rubber's ringing thump on the court
      this._tone(out, { at: t0, f: 210, f1: 95, gain: 0.5 * w, attack: 0.002, decay: 0.11 });
      this._tone(out, { at: t0, type: 'triangle', f: 640, f1: 420, gain: 0.2 * w, attack: 0.002, decay: 0.06 });
      this._burst(out, { at: t0, f: 1400, q: 0.7, gain: 0.3 * w, attack: 0.001, decay: 0.025 });
    } else if (what === 'rim') {
      for (const [f, g, d] of [[412, 0.3, 0.22], [1096, 0.2, 0.3], [2314, 0.1, 0.16]]) this._tone(out, { at: t0, f, gain: g * (0.4 + w), attack: 0.001, decay: d });
      this._burst(out, { at: t0, f: 2600, q: 1.5, gain: 0.16, attack: 0.001, decay: 0.03 });
    } else if (what === 'board') {
      this._tone(out, { at: t0, f: 170, f1: 110, gain: 0.5 * (0.4 + w), attack: 0.002, decay: 0.14 });
      this._burst(out, { at: t0, f: 700, q: 0.8, gain: 0.3, attack: 0.001, decay: 0.05 });
    } else {
      // through the net
      this._burst(out, { at: t0, f: 5200, f1: 2600, q: 0.8, gain: 0.3, attack: 0.02, decay: 0.2 });
    }
  }

  // somebody thrown into the fountain (birthday.js): the body's thump, the burst of water, the drops coming back
  splash(p) {
    const ctx = this.ctx;
    if (!ctx || ctx.state !== 'running') return;
    const out = this._panner(p.x, p.y, p.z, 6, 1.0), t0 = ctx.currentTime;
    this._tone(out, { at: t0, f: 110, f1: 62, gain: 0.45, attack: 0.004, decay: 0.5 });
    this._burst(out, { at: t0, type: 'lowpass', f: 3800, f1: 1100, gain: 0.7, attack: 0.012, decay: 1.6 });
    for (let i = 0; i < 40; i++) {
      const at = t0 + 0.25 + 1.6 * Math.random() ** 1.5, f = rand(900, 2400);
      this._tone(out, { at, f, f1: f * 1.8, gain: rand(0.08, 0.25) * (1 - (at - t0) / 2.4), attack: 0.002, decay: 0.04 });
    }
  }
}
