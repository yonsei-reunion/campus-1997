// The look of the paving decals (decals.js), painted procedurally into two atlases; no DOM and no three.js, so the
// same file runs as a module worker (decals.js starts it: a second of painting off the main thread while the rest
// loads) and, where workers fail, on the main thread.
//  - lit (RGBA colour, normals from a painted relief, roughness / metalness): manholes, gully grates, a utility lid
//  - mul (a factor per channel, 1 = the ground as it is, white round every shape so the mip levels fade them cleanly):
//    oil, asphalt patches, cracks, stains, the zebra stripes' worn paint, grime

// size: along x across (m) at scale 1; cells: [x, y, w, h] of the atlas (0..1), one per variant; thin: halved on phones;
// stretch: the scale is the length only (a zebra stripe's showing part)
const q = (i, j) => [i / 4, j / 4, 1 / 4, 1 / 4];
export const KINDS = {
  manhole: { lit: true, size: [0.76, 0.76], cells: [[0, 0, 0.5, 0.5], [0.5, 0, 0.5, 0.5]] },
  drain: { lit: true, size: [1.0, 0.42], cells: [[0, 0.5, 0.5, 0.25], [0, 0.75, 0.5, 0.25]] },
  lid: { lit: true, size: [0.62, 0.62], cells: [[0.5, 0.5, 0.5, 0.5]] },
  oil: { size: [1.5, 1.5], cells: [q(0, 0), q(1, 0), q(2, 0), q(3, 0)] },
  patch: { size: [2.6, 2.6], cells: [q(0, 1), q(1, 1), q(2, 1), q(3, 1)] },
  crack: { size: [1.2, 1.2], cells: [q(0, 2), q(1, 2)], thin: true },
  stain: { size: [1.2, 1.2], cells: [q(2, 2), q(3, 2)], thin: true },
  wear: { size: [4.0, 0.5], cells: [0, 1, 2, 3].map((k) => [0, 0.75 + k / 32, 0.25, 1 / 32]), stretch: true },
  wear_lt: { size: [4.0, 0.5], cells: [4, 5, 6, 7].map((k) => [0, 0.75 + k / 32, 0.25, 1 / 32]), stretch: true },
  grime: { size: [3.0, 3.0], cells: [q(1, 3), q(2, 3)], thin: true },
};

// ---------------------------------------------------------------------------- noise, shapes
export function hash2(x, y, s) {
  let h = Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(s, 1442695041);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
function vnoise(x, y, s) {
  const xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi;
  const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
  const a = hash2(xi, yi, s), b = hash2(xi + 1, yi, s), c = hash2(xi, yi + 1, s), d = hash2(xi + 1, yi + 1, s);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function fbm(x, y, s, oct = 3) {
  let sum = 0, amp = 0.5, norm = 0;
  for (let i = 0; i < oct; i++) { sum += amp * vnoise(x, y, s + i * 31); norm += amp; x *= 2.03; y *= 2.03; amp *= 0.5; }
  return sum / norm;
}
function rng(a) {            // (util.js mulberry, here so the worker imports nothing)
  return () => {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
const sstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const mix = (a, b, t) => a + (b - a) * t;
const sdBox = (u, v, hx, hy) => {
  const qx = Math.abs(u) - hx, qy = Math.abs(v) - hy;
  return Math.hypot(Math.max(qx, 0), Math.max(qy, 0)) + Math.min(Math.max(qx, qy), 0);
};
const segDist = (u, v, ax, ay, bx, by) => {
  const dx = bx - ax, dy = by - ay, t = Math.min(1, Math.max(0, ((u - ax) * dx + (v - ay) * dy) / (dx * dx + dy * dy || 1)));
  return Math.hypot(u - ax - dx * t, v - ay - dy * t);
};

// the texel rectangle of a cell, and the metres <-> texels of a kind's size over it
function cellBox(N, cell, size) {
  const x0 = Math.round(cell[0] * N), y0 = Math.round(cell[1] * N), w = Math.round(cell[2] * N), h = Math.round(cell[3] * N);
  return { x0, y0, w, h, sx: size[0] / w, sy: size[1] / h };
}
// walk the texels of one cell (or of the part of it round [u0, u1] x [v0, v1]): fn(u, v, px, index) with u along and
// v across in metres from the cell's centre, px the texel size
function eachTexel(N, cell, size, fn, box = null) {
  const { x0, y0, w, h, sx, sy } = cellBox(N, cell, size);
  let i0 = 0, i1 = w, j0 = 0, j1 = h;
  if (box) {
    i0 = Math.max(0, Math.floor((box[0] + size[0] / 2) / sx)); i1 = Math.min(w, Math.ceil((box[1] + size[0] / 2) / sx));
    j0 = Math.max(0, Math.floor((box[2] + size[1] / 2) / sy)); j1 = Math.min(h, Math.ceil((box[3] + size[1] / 2) / sy));
  }
  for (let j = j0; j < j1; j++) {
    const v = (j + 0.5) * sy - size[1] / 2;
    for (let i = i0; i < i1; i++) fn((i + 0.5) * sx - size[0] / 2, v, sx, (y0 + j) * N + x0 + i);
  }
}

// ---------------------------------------------------------------------------- the lit atlas
// sRGB colour, roughness, metalness
const IRON = [0.19, 0.185, 0.18, 0.62, 0.55];
const STEEL = [0.42, 0.41, 0.4, 0.42, 0.7];          // the cast pattern's tops, worn bright by tyres and shoes
const RUST = [0.21, 0.15, 0.11, 0.9, 0.15];
const DIRT = [0.12, 0.11, 0.1, 0.95, 0];
const TAR = [0.07, 0.07, 0.068, 0.75, 0];
const HOLE = [0.015, 0.014, 0.013, 1, 0];
const CONCRETE = [0.5, 0.49, 0.46, 0.93, 0];
const MORTAR = [0.42, 0.41, 0.38, 0.95, 0];

export function paintLit(N) {
  const col = new Uint8Array(N * N * 4), orm = new Uint8Array(N * N * 4), nrm = new Uint8Array(N * N * 4);
  const hgt = new Float32Array(N * N);
  const o = { c: TAR, a: 0, h: 0, t: null, k: 0 };
  // colour c (blended towards t by k), coverage a, height h (m)
  const put = (idx) => {
    const c = o.c, t = o.t || c, k = o.t ? o.k : 0;
    for (let n = 0; n < 3; n++) col[idx * 4 + n] = Math.round(mix(c[n], t[n], k) * 255);
    col[idx * 4 + 3] = Math.round(o.a * 255);
    orm[idx * 4] = 255;
    orm[idx * 4 + 1] = Math.round(mix(c[3], t[3], k) * 255);
    orm[idx * 4 + 2] = Math.round(mix(c[4], t[4], k) * 255);
    orm[idx * 4 + 3] = 255;
    hgt[idx] = o.h;
  };
  // the cast tops worn bright, the recesses rusty and dirty
  const iron = (u, v, s, raised) => {
    if (raised > 0.5) { o.c = IRON; o.t = STEEL; o.k = sstep(0.35, 0.75, fbm(u * 9, v * 9, s, 3)) * 0.85; }
    else { o.c = RUST; o.t = DIRT; o.k = 0.3 + 0.7 * sstep(0.3, 0.7, fbm(u * 14, v * 14, s + 7, 3)); }
  };

  // 1, 2: round cast-iron sewer covers (0.6 m) in their frames, sealed into the asphalt with tar
  const manhole = (cell, variant) => eachTexel(N, cell, KINDS.manhole.size, (u, v, px, idx) => {
    const r = Math.hypot(u, v), a = Math.atan2(v, u);
    const e = (d) => sstep(px, -px, d);                    // inside a band whose signed distance is d (antialiased)
    o.a = 1; o.h = 0; o.t = null;
    if (r > 0.335) {                                       // the tar seal round the frame, a little ragged
      o.c = TAR;
      o.a = e(r - 0.35 - 0.006 * (vnoise(a * 7 + 9, 0.5, 3) - 0.5)) * 0.7;
    } else if (r > 0.303) {                                // the frame: flat, worn
      iron(u, v, 11, 1);
      o.k *= 0.6;
      o.h = 0.001;
    } else if (r > 0.298) {
      o.c = HOLE; o.h = -0.004;                            // the gap round the cover
    } else {
      let raised;
      if (variant === 0) {
        // concentric rings, 24 radial ribs, a boss in the middle
        const arc = Math.abs(((a / (2 * Math.PI)) * 24 % 1 + 1) % 1 - 0.5) * (2 * Math.PI * r / 24);
        raised = Math.max(e(0.272 - r), e(Math.abs(r - 0.215) - 0.006), e(Math.abs(r - 0.15) - 0.006),
          r > 0.085 && r < 0.27 ? e(arc - 0.0055) : 0);
        // the boss: a raised cross on a lower disc
        if (r < 0.064) raised = e(r - 0.058) * (0.6 + 0.4 * Math.max(e(Math.abs(u) - 0.008), e(Math.abs(v) - 0.008)));
      } else {
        // anti-skid checker of little raised squares, a plain band and a boss with a ring of ticks
        const g = 0.032, cu = u / g - Math.round(u / g), cv = v / g - Math.round(v / g);
        const sq = e(Math.max(Math.abs(cu), Math.abs(cv)) * g - 0.0095);
        raised = Math.max(e(0.27 - r), r > 0.13 && r < 0.262 ? sq : 0, e(Math.abs(r - 0.112) - 0.012),
          e(r - 0.04), r < 0.088 && r > 0.05 ? e(Math.abs(((a / (2 * Math.PI)) * 16 % 1 + 1) % 1 - 0.5) * 2 * Math.PI * r / 16 - 0.004) : 0);
      }
      iron(u, v, 17 + variant, raised);
      o.h = raised * 0.004;
      // two pick slots
      const sl = sdBox(Math.abs(u) - 0.235, v, 0.012, 0.006);
      if (sl < 0.002) { o.c = HOLE; o.t = null; o.h = -0.006 * e(sl); }
    }
    put(idx);
  });
  manhole(KINDS.manhole.cells[0], 0);
  manhole(KINDS.manhole.cells[1], 1);

  // 3, 4: gully grates against the kerb (0.92 x 0.37 m): a frame and cross bars over the dark drain, a mortar joint
  const drain = (cell, variant) => eachTexel(N, cell, KINDS.drain.size, (u, v, px, idx) => {
    const d = sdBox(u, v, 0.46, 0.185), e = (x) => sstep(px, -px, x);
    o.t = null; o.h = 0; o.a = 1;
    if (d > 0) {
      o.c = MORTAR; o.a = e(d - 0.012) * 0.85;
    } else if (sdBox(u, v, 0.43, 0.155) > 0) {
      iron(u, v, 23 + variant, 1); o.k *= 0.7; o.h = 0.002;
    } else {
      const bar = Math.max(e(Math.abs(((u + 0.43) / 0.046) % 1 - 0.5) * 0.046 - 0.0105), e(Math.abs(v) - 0.011));
      if (bar > 0.5) { iron(u, v, 29 + variant, 1); o.h = 0.002; }
      else {
        o.c = HOLE; o.h = -0.02;
        if (variant === 1) {                                   // silted up: earth and dead leaves in the slots
          const m = sstep(0.45, 0.7, fbm(u * 6, v * 12, 41, 3));
          o.t = [0.24, 0.19, 0.13, 0.95, 0]; o.k = m; o.h = -0.02 + 0.012 * m;
        }
      }
    }
    put(idx);
  });
  drain(KINDS.drain.cells[0], 0);
  drain(KINDS.drain.cells[1], 1);

  // 5: a square utility lid in the sidewalk (0.54 m): concrete in an iron angle frame, two lifting holes
  eachTexel(N, KINDS.lid.cells[0], KINDS.lid.size, (u, v, px, idx) => {
    const d = sdBox(u, v, 0.27, 0.27), e = (x) => sstep(px, -px, x);
    o.t = null; o.h = 0; o.a = 1;
    if (d > 0) { o.c = MORTAR; o.a = e(d - 0.016) * 0.9; }
    else if (d > -0.022) { iron(u, v, 51, 1); o.k *= 0.5; o.h = 0.002; }
    else if (d > -0.026) { o.c = HOLE; o.h = -0.003; }
    else {
      o.c = CONCRETE; o.t = [0.38, 0.37, 0.34, 0.95, 0]; o.k = sstep(0.4, 0.8, fbm(u * 8, v * 8, 57, 4)) * 0.6;
      const rim = sdBox(u, v, 0.215, 0.215);
      o.h = rim > -0.008 && rim < 0 ? 0.0015 : 0;
      if (sdBox(Math.abs(u) - 0.16, v, 0.018, 0.008) < 0) { o.c = HOLE; o.t = null; o.h = -0.01; }
    }
    put(idx);
  });

  // relief -> tangent-space normals (texel rows run with +v: the textures are not flipped)
  for (const k of Object.values(KINDS)) {
    if (!k.lit) continue;
    for (const cell of k.cells) {
      const { x0, y0, w, h, sx, sy } = cellBox(N, cell, k.size);
      const at = (i, j) => hgt[(y0 + Math.min(h - 1, Math.max(0, j))) * N + x0 + Math.min(w - 1, Math.max(0, i))];
      for (let j = 0; j < h; j++) {
        for (let i = 0; i < w; i++) {
          const dx = (at(i + 1, j) - at(i - 1, j)) / (2 * sx), dy = (at(i, j + 1) - at(i, j - 1)) / (2 * sy);
          const l = Math.hypot(dx, dy, 1), idx = ((y0 + j) * N + x0 + i) * 4;
          nrm[idx] = Math.round((-dx / l * 0.5 + 0.5) * 255);
          nrm[idx + 1] = Math.round((-dy / l * 0.5 + 0.5) * 255);
          nrm[idx + 2] = Math.round((1 / l * 0.5 + 0.5) * 255);
          nrm[idx + 3] = 255;
        }
      }
    }
  }
  return { col, nrm, orm };
}

// ---------------------------------------------------------------------------- the multiplied atlas
export function paintMul(N) {
  const f = new Float32Array(N * N * 3).fill(1);
  const dark = (idx, k, t) => { f[idx * 3] *= 1 - k * (1 - t[0]); f[idx * 3 + 1] *= 1 - k * (1 - t[1]); f[idx * 3 + 2] *= 1 - k * (1 - t[2]); };
  const OIL = [0.2, 0.19, 0.18], TARC = [0.34, 0.34, 0.35], NEW = [0.64, 0.64, 0.66], OLD = [0.84, 0.84, 0.84];
  const GRIT = [0.42, 0.38, 0.33];

  // oil: a dark core soaked into the surface, a darker tide line where it spread, a few drips round it
  KINDS.oil.cells.forEach((cell, n) => {
    const r = rng(450 + n);
    const drops = Array.from({ length: 3 + Math.floor(r() * 5) }, () => {
      const a = r() * 6.28, d = 0.35 + r() * 0.3;
      return [Math.cos(a) * d, Math.sin(a) * d, 0.015 + r() * 0.035];
    });
    const R0 = n === 3 ? 0.36 : 0.42 + r() * 0.12, el = n === 3 ? 1.8 : 1 + r() * 0.3;
    eachTexel(N, cell, KINDS.oil.size, (u, v, px, idx) => {
      let k = 0;
      const d0 = Math.hypot(u / el, v) / R0;
      if (d0 < 1.5) {
        const wx = (fbm(u * 2.4 + n, v * 2.4, 60 + n, 2) - 0.5) * 0.45, wy = (fbm(u * 2.4, v * 2.4 + n, 70 + n, 2) - 0.5) * 0.45;
        const d = Math.hypot((u + wx) / el, v + wy) / R0;
        if (d < 1.15) k = sstep(1.05, 0.3, d) * (0.55 + 0.45 * fbm(u * 10, v * 10, 80 + n)) + Math.exp(-(((d - 0.97) / 0.06) ** 2)) * 0.22;
      }
      for (const [x, y, rr] of drops) k = Math.max(k, sstep(rr, rr * 0.4, Math.hypot(u - x, v - y)) * 0.75);
      if (k > 0.002) dark(idx, Math.min(1, k) * 0.95, OIL);
    });
  });

  // asphalt patches: saw-cut, filled darker and smoother, the joint sealed with tar
  const patchCell = (cell, n, shapes) => eachTexel(N, cell, KINDS.patch.size, (u, v, px, idx) => {
    for (const [sd, tint] of shapes) {
      const d = sd(u, v);
      if (d > 0.08) continue;
      const dj = d + (vnoise(u * 18, v * 18, 90 + n) - 0.5) * 0.012;
      const inside = sstep(px, -px, dj);
      if (inside > 0) dark(idx, inside * (0.75 + 0.5 * fbm(u * 5, v * 5, 95 + n, 2)), tint);
      const seam = Math.exp(-((dj / 0.016) ** 2));
      if (seam > 0.01) dark(idx, seam * 0.85, TARC);
    }
  });
  patchCell(KINDS.patch.cells[0], 0, [[(u, v) => sdBox(u, v, 1.05, 0.7), NEW]]);
  patchCell(KINDS.patch.cells[1], 1, [[(u, v) => sdBox(u, v, 1.15, 0.3), [0.7, 0.7, 0.72]]]);
  patchCell(KINDS.patch.cells[2], 2, [[(u, v) => sdBox(u + 0.2, v + 0.15, 0.85, 0.75), OLD], [(u, v) => sdBox(u - 0.45, v - 0.3, 0.55, 0.42), NEW]]);
  patchCell(KINDS.patch.cells[3], 3, [[(u, v) => Math.hypot(u + (fbm(u * 2, v * 2, 99, 2) - 0.5) * 0.5, (v + (fbm(u * 2 + 5, v * 2, 98, 2) - 0.5) * 0.5) * 1.25) - 0.62,
    [0.68, 0.68, 0.7]]]);

  // cracked paving: a crack wandering across the slabs with branches, grit trodden in along it, chips broken off
  KINDS.crack.cells.forEach((cell, n) => {
    const { w, h } = cellBox(N, cell, KINDS.crack.size);
    const acc = new Float32Array(w * h);                 // darkness, the most of any stroke (no double darkening)
    const { x0, y0 } = cellBox(N, cell, KINDS.crack.size);
    const at = (idx) => (Math.floor(idx / N) - y0) * w + (idx % N) - x0;
    const r = rng(470 + n);
    const segs = [], chips = [];
    const crack = (x, y, a, len, width, depth) => {
      for (let s = 0; s < len; s += 0.03) {
        a += (r() - 0.5) * 0.7;
        const nx = x + Math.cos(a) * 0.03, ny = y + Math.sin(a) * 0.03;
        if (Math.hypot(nx, ny) > 0.52) break;
        segs.push([x, y, nx, ny, width]);
        x = nx; y = ny;
        if (depth < 2 && r() < 0.05) crack(x, y, a + (r() < 0.5 ? 1 : -1) * (0.6 + r() * 0.8), len * 0.4, width * 0.7, depth + 1);
        if (depth === 0 && r() < 0.05) chips.push([x + (r() - 0.5) * 0.04, y + (r() - 0.5) * 0.04, 0.04 + r() * 0.05, r() * 100]);
      }
    };
    crack(-0.5, (r() - 0.5) * 0.4, (r() - 0.5) * 0.6, 1.4, 0.016, 0);
    crack((r() - 0.5) * 0.3, -0.5, 1.57 + (r() - 0.5) * 0.6, 0.6 + r() * 0.5, 0.012, 1);
    for (const [ax, ay, bx, by, wd] of segs) {
      const halo = wd * 4;
      eachTexel(N, cell, KINDS.crack.size, (u, v, px, idx) => {
        const d = segDist(u, v, ax, ay, bx, by);
        const k = Math.max(sstep(wd / 2 + px / 2, wd / 2 - px / 2, d) * 0.75, Math.exp(-((d / halo) ** 2)) * 0.22);
        const t = at(idx);
        if (k > acc[t]) acc[t] = k;
      }, [Math.min(ax, bx) - halo * 2, Math.max(ax, bx) + halo * 2, Math.min(ay, by) - halo * 2, Math.max(ay, by) + halo * 2]);
    }
    for (const [cx, cy, rr, s] of chips) {
      eachTexel(N, cell, KINDS.crack.size, (u, v, px, idx) => {
        const a = Math.atan2(v - cy, u - cx), d = Math.hypot(u - cx, v - cy);
        const edge = rr * (0.65 + 0.5 * vnoise(a * 1.6 + s, s, 7));
        const t = at(idx);
        acc[t] = Math.max(acc[t], sstep(edge + px, edge - px, d) * 0.5);
      }, [cx - rr * 1.3, cx + rr * 1.3, cy - rr * 1.3, cy + rr * 1.3]);
    }
    if (n === 1) {
      // a spot trodden to pieces where the crack crosses: shards (a Voronoi of 14 points), each sunk and soiled its
      // own amount, dark gaps between them, a ring of grit round it
      const pts = Array.from({ length: 14 }, () => { const a = r() * 6.28, d = Math.sqrt(r()) * 0.3; return [Math.cos(a) * d, Math.sin(a) * d, 0.12 + 0.3 * r()]; });
      eachTexel(N, cell, KINDS.crack.size, (u, v, px, idx) => {
        const rr = Math.hypot(u, v), er = 0.27 + 0.1 * (vnoise(Math.atan2(v, u) * 2 + 3, 1.5, 9) - 0.5);
        let d1 = 9, d2 = 9, sh = 0;
        for (const [x, y, s] of pts) { const d = Math.hypot(u - x, v - y); if (d < d1) { d2 = d1; d1 = d; sh = s; } else if (d < d2) d2 = d; }
        const gap = sstep(0.007 + px / 2, 0.007 - px / 2, (d2 - d1) / 2) * 0.75;
        const k = Math.max(sstep(er + px, er - px, rr) * Math.max(gap, sh), sstep(0.009 + px / 2, 0.009 - px / 2, Math.abs(rr - er)) * 0.7,
          sstep(er + 0.1, er, rr) * 0.2);
        const t = at(idx);
        if (k > acc[t]) acc[t] = k;
      }, [-0.4, 0.4, -0.4, 0.4]);
    }
    eachTexel(N, cell, KINDS.crack.size, (u, v, px, idx) => { const k = acc[at(idx)]; if (k > 0.002) dark(idx, k, GRIT); });
  });

  // stains on the paving: chewing gum trodden flat and black, a dried spill with its tide line
  {
    const r = rng(481);
    const gum = Array.from({ length: 30 }, () => [(r() - 0.5) * 0.95, (r() - 0.5) * 0.95, 0.014 + r() * 0.022, 0.55 + r() * 0.25]);
    for (const [x, y, rr, k] of gum) {
      eachTexel(N, KINDS.stain.cells[0], KINDS.stain.size, (u, v, px, idx) => {
        const d = Math.hypot(u - x, (v - y) * 1.2) + (vnoise(u * 300, v * 300, 5) - 0.5) * 0.004;
        if (d < rr + px) dark(idx, sstep(rr + px, rr - px, d) * k, [0.32, 0.31, 0.3]);
      }, [x - rr - 0.01, x + rr + 0.01, y - rr - 0.01, y + rr + 0.01]);
    }
  }
  eachTexel(N, KINDS.stain.cells[1], KINDS.stain.size, (u, v, px, idx) => {
    if (Math.hypot(u, v) > 0.56) return;
    const d = Math.hypot(u + (fbm(u * 3, v * 3, 483, 2) - 0.5) * 0.35, v + (fbm(u * 3, v * 3, 484, 2) - 0.5) * 0.35) / 0.36;
    const k = sstep(1.0, 0.2, d) * 0.42 * (0.6 + 0.8 * fbm(u * 12, v * 12, 485)) + Math.exp(-(((d - 0.97) / 0.05) ** 2)) * 0.3;
    if (k > 0.002) dark(idx, k, [0.5, 0.45, 0.37]);
  });

  // the zebra stripes' paint worn through to the asphalt in patches and scuffed grey by the tyres; kept 2-3 cm inside
  // the stripe (the decal is the stripe itself)
  [...KINDS.wear.cells, ...KINDS.wear_lt.cells].forEach((cell, n) => {
    const heavy = n < 4;
    eachTexel(N, cell, KINDS.wear.size, (u, v, px, idx) => {
      const inside = sstep(0.018, 0.035, 0.25 - Math.abs(v)) * sstep(0.02, 0.06, 2 - Math.abs(u));
      if (inside <= 0) return;
      const nz = fbm(u * 2.6, v * 7, 500 + n, 4) + 0.08 * Math.exp(-((v / 0.14) ** 2));
      const th = heavy ? 0.66 : 0.74;
      const loss = sstep(th - 0.03, th + 0.03, nz) * inside;
      const speck = 0.3 + 0.15 * vnoise(u * 160, v * 160, 520 + n);
      const scuff = 1 - inside * (heavy ? 0.14 : 0.07) * (0.6 + 0.8 * fbm(u * 6, v * 20, 530 + n, 2));
      const k = mix(scuff, speck, loss);
      f[idx * 3] *= k; f[idx * 3 + 1] *= k; f[idx * 3 + 2] *= Math.min(1, k * 1.01);
    });
  });

  // grime: a car park's aisle darkened where the cars turn, soft blotches on the asphalt; tyre-polished tracks
  eachTexel(N, KINDS.grime.cells[0], KINDS.grime.size, (u, v, px, idx) => {
    if (Math.hypot(u, v) > 1.5) return;
    const d = Math.hypot(u + (fbm(u, v, 540, 2) - 0.5) * 0.8, v + (fbm(u, v, 541, 2) - 0.5) * 0.8) / 1.25;
    const k = sstep(1.0, 0.1, d) * 0.4 * (0.4 + 1.2 * fbm(u * 3, v * 3, 542, 4));
    if (k > 0.002) dark(idx, Math.min(k, 0.5), [0.5, 0.48, 0.45]);
  });
  eachTexel(N, KINDS.grime.cells[1], KINDS.grime.size, (u, v, px, idx) => {
    const band = Math.max(Math.exp(-(((v - 0.75) / 0.17) ** 2)), Math.exp(-(((v + 0.75) / 0.17) ** 2)));
    if (band < 0.01) return;
    const k = band * sstep(1.45, 0.9, Math.abs(u)) * 0.3 * (0.5 + fbm(u * 2, v * 8, 550, 3));
    if (k > 0.002) dark(idx, k, [0.5, 0.5, 0.5]);
  });

  const data = new Uint8Array(N * N * 4);
  for (let i = 0; i < N * N; i++) {
    data[i * 4] = Math.round(Math.max(0, f[i * 3]) * 255);
    data[i * 4 + 1] = Math.round(Math.max(0, f[i * 3 + 1]) * 255);
    data[i * 4 + 2] = Math.round(Math.max(0, f[i * 3 + 2]) * 255);
    data[i * 4 + 3] = 255;
  }
  return data;
}

// as a worker: {lit: N, mul: N} -> the atlases' pixels
if (typeof WorkerGlobalScope !== 'undefined' && self instanceof WorkerGlobalScope) {
  self.onmessage = ({ data }) => {
    const lit = paintLit(data.lit), mul = paintMul(data.mul);
    self.postMessage({ lit, mul }, [lit.col.buffer, lit.nrm.buffer, lit.orm.buffer, mul.buffer]);
  };
}
