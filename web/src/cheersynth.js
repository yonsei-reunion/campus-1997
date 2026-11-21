// 응원 연습(cheer.js)의 밴드 악기. 녹음은 없다: 음마다 소리를 여기서 계산해 버퍼로 만들고(cheerband.js 가 Web Audio 로
// 튼다), 그래서 받을 파일도 지킬 라이선스도 없다.
//  - 기타: 줄 셋(근음 · 5도 · 옥타브)을 뜯는 줄 모형(Karplus–Strong)으로 울리고 앰프의 일그러짐과 스피커 통을 거친다.
//    두 번 쳐서 왼쪽 · 오른쪽에 하나씩(더블 트래킹). 손바닥으로 누른 짧은 소리와 열어 둔 긴 소리
//  - 베이스: 같은 줄 모형 하나, 낮게
//  - 키보드: 오른손은 신스 브라스(톱니파 다섯을 조금씩 어긋나게, 음마다 열리는 필터, 늦게 오는 비브라토),
//    왼손은 드로바 오르간
//  - 드럼: 큰북 · 작은북 · 하이햇(닫힌 · 반 열린 · 열린) · 크래시 · 탐 셋 · 스틱, 그리고 구호의 응원 북
//  - 앞마당의 울림: 대강당 벽에서 돌아오는 소리와 짧은 잔향(ConvolverNode 의 임펄스)
// three.js 도 Web Audio 도 읽지 않는 계산이라 node 에서도 돌린다.

const TAU = 2 * Math.PI;
const hz = (m) => 440 * 2 ** ((m - 69) / 12);
const smooth = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));
function rng(a) {
  return () => {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// a biquad over x in place (the Audio EQ Cookbook's): lp · hp · bp · pk (peak, dB) · hs · ls (shelves, dB)
function biquad(x, sr, type, f, q = 0.707, db = 0) {
  const w = TAU * Math.min(f, sr * 0.45) / sr, c = Math.cos(w), al = Math.sin(w) / (2 * q), A = 10 ** (db / 40), rA = 2 * Math.sqrt(A) * al;
  let b0, b1, b2, a0, a1, a2;
  if (type === 'lp') { b0 = (1 - c) / 2; b1 = 1 - c; b2 = b0; a0 = 1 + al; a1 = -2 * c; a2 = 1 - al; }
  else if (type === 'hp') { b0 = (1 + c) / 2; b1 = -(1 + c); b2 = b0; a0 = 1 + al; a1 = -2 * c; a2 = 1 - al; }
  else if (type === 'bp') { b0 = al; b1 = 0; b2 = -al; a0 = 1 + al; a1 = -2 * c; a2 = 1 - al; }
  else if (type === 'pk') { b0 = 1 + al * A; b1 = -2 * c; b2 = 1 - al * A; a0 = 1 + al / A; a1 = -2 * c; a2 = 1 - al / A; }
  else if (type === 'hs') {
    b0 = A * ((A + 1) + (A - 1) * c + rA); b1 = -2 * A * ((A - 1) + (A + 1) * c); b2 = A * ((A + 1) + (A - 1) * c - rA);
    a0 = (A + 1) - (A - 1) * c + rA; a1 = 2 * ((A - 1) - (A + 1) * c); a2 = (A + 1) - (A - 1) * c - rA;
  } else {
    b0 = A * ((A + 1) - (A - 1) * c + rA); b1 = 2 * A * ((A - 1) - (A + 1) * c); b2 = A * ((A + 1) - (A - 1) * c - rA);
    a0 = (A + 1) + (A - 1) * c + rA; a1 = -2 * ((A - 1) + (A + 1) * c); a2 = (A + 1) + (A - 1) * c - rA;
  }
  b0 /= a0; b1 /= a0; b2 /= a0; a1 /= a0; a2 /= a0;
  let z1 = 0, z2 = 0;
  for (let i = 0; i < x.length; i++) {
    const v = x[i], y = b0 * v + z1;
    z1 = b1 * v - a1 * y + z2; z2 = b2 * v - a2 * y;
    x[i] = y;
  }
  return x;
}

const peakOf = (...ch) => { let p = 0; for (const x of ch) for (let i = 0; i < x.length; i++) { const v = x[i] < 0 ? -x[i] : x[i]; if (v > p) p = v; } return p; };
const scale = (g, ...ch) => { for (const x of ch) for (let i = 0; i < x.length; i++) x[i] *= g; };
// the loudest stretch's level (rms over `win` s)
function rmsOf(x, sr, win = 0.2) {
  const w = Math.max(1, Math.min(x.length, Math.round(win * sr)));
  let best = 0;
  for (let i0 = 0; i0 + w <= x.length; i0 += w >> 1 || 1) {
    let s = 0;
    for (let i = i0; i < i0 + w; i++) s += x[i] * x[i];
    if (s > best) best = s;
  }
  return Math.sqrt(best / w);
}
// the end faded, so a buffer cut short does not click
function tail(x, sr, s = 0.03) {
  const n = Math.min(x.length, Math.round(s * sr));
  for (let i = 0; i < n; i++) x[x.length - 1 - i] *= i / n;
  return x;
}

// ---------------------------------------------------------------- a plucked string
// Karplus–Strong with Jaffe and Smith's tuning: a delay line a period long, a lowpass in the loop (the highs die
// first: `damp` is what a 1 kHz partial loses each period) and an allpass for the fraction of a sample.
// The pluck: the string let go from `pick` of its length (a two-level wave) and the pick's scrape (noise)
function string(out, at, sr, f, { amp = 1, t60 = 3, damp = 0.005, pick = 0.13, scrape = 0.35, soft = 0, seed = 1 }) {
  const q = 2 * damp / (TAU * 1000 / sr) ** 2, a = ((2 * q + 1) - Math.sqrt(4 * q + 1)) / (2 * q);
  const N = sr / f, lag = a / (1 - a), L = Math.floor(N - lag - 0.2), d = N - lag - L, C = (1 - d) / (1 + d);
  const rho = 10 ** (-3 / (f * t60)), line = new Float32Array(L), r = rng(seed);
  const p = Math.max(1, Math.round(pick * L));
  for (let i = 0; i < L; i++) line[i] = (i < p ? 1 - pick : -pick) * 0.9 + (r() * 2 - 1) * scrape;
  if (soft > 0) {            // a softer stroke: the corners rounded (round the loop, both ways)
    let v = line[L - 1];
    for (let k = 0; k < 2; k++) for (let i = 0; i < L; i++) { v += (1 - soft) * (line[i] - v); line[i] = v; }
    for (let k = 0; k < 2; k++) for (let i = L - 1; i >= 0; i--) { v += (1 - soft) * (line[i] - v); line[i] = v; }
  }
  let lp = 0, x1 = 0, y1 = 0, k = 0;
  for (let i = at; i < out.length; i++) {
    const x = line[k];
    out[i] += x * amp;
    lp += (1 - a) * (x - lp);
    const y = C * lp + x1 - C * y1;
    x1 = lp; y1 = y;
    line[k] = y * rho;
    if (++k === L) k = 0;
  }
}

// 기타: a power chord on m (root, fifth, octave), palm-muted or open, two takes left and right.
// Worked at twice the rate so the drive's overtones do not fold back; the speaker's roll-off is the decimator
function guitar(sr, m, dur, open) {
  const sr2 = sr * 2, n2 = Math.ceil(dur * sr2), n = n2 >> 1, takes = [];
  for (let t = 0; t < 2; t++) {
    const x = new Float32Array(n2), r = rng(m * 31 + t * 7 + (open ? 3 : 0));
    [0, 7, 12].forEach((semi, i) => {
      const cents = (t ? 4 : -3) + (r() - 0.5) * 3;
      string(x, Math.round((i * (open ? 0.009 : 0.004) + r() * 0.002) * sr2), sr2, hz(m + semi) * 2 ** (cents / 1200), {
        amp: [1, 0.9, 0.7][i], t60: open ? 5 : 0.55, damp: open ? 0.006 : 0.08, pick: (t ? 0.17 : 0.12) + i * 0.01, scrape: open ? 0.35 : 0.25, seed: m * 97 + i * 13 + t * 5 + 1 });
    });
    // the amplifier: tightened and pushed in the mids before the drive, then the cabinet
    biquad(x, sr2, 'hp', 120, 0.7);
    biquad(x, sr2, 'pk', 800, 0.7, 6);
    const g = open ? 12 : 8, bias = 0.12, tb = Math.tanh(bias);
    for (let i = 0; i < n2; i++) x[i] = Math.tanh(g * x[i] + bias) - tb;
    biquad(x, sr2, 'hp', 85, 0.8);
    biquad(x, sr2, 'pk', 140, 1, open ? 2 : 4);
    biquad(x, sr2, 'pk', 450, 1, -3.5);
    biquad(x, sr2, 'pk', 2700, 1.1, 4.5);
    biquad(x, sr2, 'lp', 4800, 0.8);
    biquad(x, sr2, 'lp', 5600, 0.6);
    const y = new Float32Array(n);
    for (let i = 0; i < n; i++) y[i] = x[i * 2];
    takes.push(tail(y, sr));
  }
  const [a, b] = takes, L = new Float32Array(n), R = new Float32Array(n);
  for (let i = 0; i < n; i++) { L[i] = a[i] + 0.2 * b[i]; R[i] = b[i] + 0.2 * a[i]; }
  scale(0.2 / Math.max(rmsOf(L, sr, 0.12), rmsOf(R, sr, 0.12)), L, R);
  return { sr, ch: [L, R] };
}

// 베이스: one string, plucked with the fingers near the neck pickup, a little grit and the cabinet's roll-off
function bass(sr, m, dur) {
  const x = new Float32Array(Math.ceil(dur * sr));
  string(x, 0, sr, hz(m), { t60: 7, damp: 0.035, pick: 0.22, scrape: 0.12, soft: 0.55, seed: m * 53 + 9 });
  biquad(x, sr, 'hp', 32, 0.7);
  for (let i = 0; i < x.length; i++) x[i] = Math.tanh(1.6 * x[i]);
  biquad(x, sr, 'ls', 70, 0.7, -4);
  biquad(x, sr, 'pk', 110, 0.9, 2);
  biquad(x, sr, 'pk', 850, 1, 4);         // (the growl: what a phone's speaker still plays of it)
  biquad(x, sr, 'lp', 2800, 0.7);
  scale(0.25 / rmsOf(x, sr, 0.12), x);
  return { sr, ch: [tail(x, sr)] };
}

// ---------------------------------------------------------------- the keyboard
// 신스 브라스(오른손): three saws a few cents apart and two an octave under, through a 24 dB lowpass that opens with
// each note and settles; the pitch scoops up into the note, and the vibrato comes late, each saw at its own pace
function brass(sr, m, dur) {
  const f0 = hz(m), n = Math.ceil(dur * sr), x = new Float32Array(n), r = rng(m * 131 + 5);
  const V = [[-7, 1, 1], [0, 1, 1], [6, 1, 1], [-4, 0.5, 0.5], [5, 0.5, 0.5]]
    .map(([c, o, g]) => ({ k: o * 2 ** (c / 1200), g, p: r(), vp: r() * TAU, vr: 5.2 + r() * 0.6 }));
  for (let i0 = 0; i0 < n; i0 += 32) {
    const t = i0 / sr, i1 = Math.min(n, i0 + 32), scoop = -32 * Math.exp(-t / 0.02), vd = 9 * smooth((t - 0.22) / 0.4);
    for (const v of V) {
      const dt = f0 * v.k * 2 ** ((scoop + vd * Math.sin(v.vp + TAU * v.vr * t)) / 1200) / sr, g = v.g;
      let p = v.p;
      for (let i = i0; i < i1; i++) {
        let s = 2 * p - 1;          // (a saw, its step rounded over two samples: polyBLEP)
        if (p < dt) { const u = p / dt; s -= u + u - u * u - 1; } else if (p > 1 - dt) { const u = (p - 1) / dt; s -= u * u + u + u + 1; }
        x[i] += s * g;
        p += dt; if (p >= 1) p -= 1;
      }
      v.p = p;
    }
  }
  // the filter (two state-variable lowpasses) and the loudness: both a touch over at the attack
  let a1 = 0, a2 = 0, a3 = 0, b1 = 0, b2 = 0, b3 = 0, s1 = 0, s2 = 0, s3 = 0, s4 = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    if (!(i & 15)) {
      const e = t < 0.03 ? t / 0.03 : 0.6 + 0.4 * Math.exp(-(t - 0.03) / 0.22);
      const g = Math.tan(Math.PI * Math.min(f0 * (2 + 9 * e), 8000, sr * 0.4) / sr);
      a1 = 1 / (1 + g * (g + 1.25)); a2 = g * a1; a3 = g * a2;
      b1 = 1 / (1 + g * (g + 0.85)); b2 = g * b1; b3 = g * b2;
    }
    let v3 = x[i] - s2, v1 = a1 * s1 + a2 * v3, v2 = s2 + a2 * s1 + a3 * v3;
    s1 = 2 * v1 - s1; s2 = 2 * v2 - s2;
    v3 = v2 - s4; v1 = b1 * s3 + b2 * v3; v2 = s4 + b2 * s3 + b3 * v3;
    s3 = 2 * v1 - s3; s4 = 2 * v2 - s4;
    x[i] = v2 * Math.min(1, t / 0.012) * (0.86 + 0.14 * Math.exp(-t / 0.25));
  }
  biquad(x, sr, 'hp', 170, 0.7);
  biquad(x, sr, 'pk', 1350, 0.8, 3);
  scale(0.2 / rmsOf(x, sr, 0.15), x);
  for (let i = 0; i < n; i++) x[i] = Math.tanh(2.4 * x[i]) / 2.4;      // (the saws' peaks rounded: room for the rest)
  scale(0.2 / rmsOf(x, sr, 0.15), x);
  return { sr, ch: [tail(x, sr)] };
}

// 드로바 오르간(왼손): the drawbars' sines, two sets a few cents apart, the rotary speaker's slow shimmer.
// Nothing in it is over 3 kHz: made at half the rate
function organ(sr0, m, dur) {
  const sr = sr0 / 2, f = hz(m), n = Math.ceil(dur * sr), x = new Float32Array(n), r = rng(m * 17 + 3);
  const bars = [[1, 1], [2, 0.7], [3, 0.5], [4, 0.32], [6, 0.14]], ph = bars.map(() => [r() * TAU, r() * TAU]), tp = r() * TAU;
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    let s = 0;
    for (let k = 0; k < bars.length; k++) {
      const w = TAU * f * bars[k][0] * t;
      s += bars[k][1] * (Math.sin(w * 0.9975 + ph[k][0]) + Math.sin(w * 1.0025 + ph[k][1]));
    }
    x[i] = s * Math.min(1, t / 0.008) * (1 + 0.1 * Math.sin(TAU * 6.3 * t + tp));
  }
  const cl = rng(m + 77);       // (the key's click)
  for (let i = 0; i < Math.min(n, sr * 0.004); i++) x[i] += (cl() * 2 - 1) * 1.2 * (1 - i / (sr * 0.004));
  biquad(x, sr, 'lp', 3200, 0.7);
  scale(0.15 / rmsOf(x, sr, 0.15), x);
  return { sr, ch: [tail(x, sr)] };
}

// ---------------------------------------------------------------- the drums
const exp = Math.exp;
function noise(n, r, g = 1) { const x = new Float32Array(n); for (let i = 0; i < n; i++) x[i] = (r() * 2 - 1) * g; return x; }
// equal-power place of a mono sound: pan -1 (left) .. 1
function place(x, pan) {
  const a = (pan + 1) * Math.PI / 4, L = new Float32Array(x.length), R = new Float32Array(x.length), l = Math.cos(a) * Math.SQRT2, rr = Math.sin(a) * Math.SQRT2;
  for (let i = 0; i < x.length; i++) { L[i] = x[i] * l; R[i] = x[i] * rr; }
  return [L, R];
}
const norm = (p, ...ch) => { scale(p / peakOf(...ch), ...ch); return ch; };

// 큰북(드럼 세트): the head's thump falling in pitch, the beater's click
function kick(sr) {
  const n = Math.round(0.5 * sr), x = new Float32Array(n), c = noise(Math.round(0.03 * sr), rng(11));
  let ph = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    ph += TAU * (56 + 95 * exp(-t / 0.016) + 22 * exp(-t / 0.07)) / sr;
    x[i] = Math.sin(ph) * exp(-t / 0.085) * Math.min(1, t / 0.0015);
  }
  biquad(c, sr, 'bp', 3200, 0.9);
  for (let i = 0; i < c.length; i++) x[i] += c[i] * 1.6 * exp(-i / sr / 0.004);
  for (let i = 0; i < n; i++) x[i] = Math.tanh(1.8 * x[i]);
  biquad(x, sr, 'pk', 300, 1, -3);
  return { sr, ch: norm(0.9, tail(x, sr, 0.05)) };
}

// 응원 북(구호): a big drum beaten with a mallet: lower, longer, the skin's first overtones and its slap
function boom(sr) {
  const n = Math.round(0.9 * sr), x = new Float32Array(n), c = noise(Math.round(0.08 * sr), rng(12));
  let p1 = 0, p2 = 0, p3 = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sr, f = 64 + 34 * exp(-t / 0.03);
    p1 += TAU * f / sr; p2 += TAU * f * 1.59 / sr; p3 += TAU * f * 2.14 / sr;
    x[i] = (Math.sin(p1) * exp(-t / 0.17) + 0.45 * Math.sin(p2) * exp(-t / 0.09) + 0.3 * Math.sin(p3) * exp(-t / 0.06)) * Math.min(1, t / 0.002);
  }
  biquad(c, sr, 'lp', 1100, 0.7);
  for (let i = 0; i < c.length; i++) x[i] += c[i] * 1.3 * exp(-i / sr / 0.018);
  for (let i = 0; i < n; i++) x[i] = Math.tanh(1.4 * x[i]);
  return { sr, ch: norm(0.9, tail(x, sr, 0.05)) };
}

// 작은북: the two heads' tones and the wires' rattle (bright noise, a quick part and a longer one)
function snare(sr) {
  const n = Math.round(0.42 * sr), x = new Float32Array(n), w = noise(n, rng(21));
  biquad(w, sr, 'hp', 1300, 0.7);
  biquad(w, sr, 'pk', 4600, 0.9, 5);
  biquad(w, sr, 'lp', 11000, 0.7);
  let p1 = 0, p2 = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sr, bend = 1 + 0.35 * exp(-t / 0.008);
    p1 += TAU * 188 * bend / sr; p2 += TAU * 331 * bend / sr;
    x[i] = 0.75 * Math.sin(p1) * exp(-t / 0.05) + 0.4 * Math.sin(p2) * exp(-t / 0.03)
      + w[i] * (0.55 * exp(-t / 0.028) + 0.38 * exp(-t / 0.085)) * Math.min(1, t / 0.0008);
  }
  for (let i = 0; i < n; i++) x[i] = Math.tanh(1.5 * x[i]);
  return { sr, ch: norm(0.9, tail(x, sr, 0.04)) };
}

// the cymbals' metal: six square waves at the ratios drum machines have used since the TR-808, high-passed
function metal(n, sr, k, r) {
  const x = new Float32Array(n), F = [205.3, 304.4, 369.6, 522.7, 540, 800].map((f) => f * k * (0.99 + r() * 0.02) / sr), P = F.map(() => r());
  for (let i = 0; i < n; i++) {
    let s = 0;
    for (let j = 0; j < 6; j++) { P[j] += F[j]; if (P[j] >= 1) P[j] -= 1; s += P[j] < 0.5 ? 1 : -1; }
    x[i] = s / 6;
  }
  return x;
}
// 하이햇: closed (tau 12 ms), half open, open
function hat(sr, tau, len, pan) {
  const n = Math.round(len * sr), r = rng(31 + Math.round(tau * 1000)), x = metal(n, sr, 1.42, r), w = noise(n, r);
  biquad(x, sr, 'hp', 7200, 0.8); biquad(x, sr, 'hp', 6000, 0.7);
  biquad(w, sr, 'hp', 8000, 0.8);
  for (let i = 0; i < n; i++) { const t = i / sr; x[i] = (x[i] * 1.6 + w[i] * 0.55) * (0.7 * exp(-t / tau) + 0.3 * exp(-t / (tau * 0.3))) * Math.min(1, t / 0.0005); }
  biquad(x, sr, 'pk', 9500, 1, 3);
  return { sr, ch: norm(0.8, ...place(tail(x, sr, 0.02), pan)) };
}
// 크래시: the metal's clang under a wash of noise that darkens as it fades, each side its own
function crash(sr) {
  const n = Math.round(2.3 * sr), ch = [];
  for (let c = 0; c < 2; c++) {
    const r = rng(41 + c * 9), x = noise(n, r), m1 = metal(n, sr, 2.9, r), d = new Float32Array(n);
    biquad(x, sr, 'hp', 2600, 0.7); biquad(x, sr, 'pk', 5400, 0.8, 4);
    d.set(x); biquad(d, sr, 'lp', 4200, 0.7);
    biquad(m1, sr, 'hp', 3200, 0.7);
    for (let i = 0; i < n; i++) {
      const t = i / sr, u = Math.min(1, t / 1.2);
      x[i] = ((x[i] * (1 - u) + d[i] * u * 1.5) * (0.55 * exp(-t / 0.12) + 0.45 * exp(-t / 0.55)) + m1[i] * 1.1 * exp(-t / 0.3)) * Math.min(1, t / 0.002);
    }
    ch.push(tail(x, sr, 0.2));
  }
  return { sr, ch: norm(0.8, ...ch) };
}
// 탐: a head's tone falling as it rings, the stick on the skin
function tom(sr, f0, tau, pan) {
  const n = Math.round(tau * 5 * sr), x = new Float32Array(n), c = noise(Math.round(0.03 * sr), rng(51 + f0));
  let p1 = 0, p2 = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sr, f = f0 * (1 + 0.4 * exp(-t / 0.022) - 0.06 * Math.min(1, t / 0.4));
    p1 += TAU * f / sr; p2 += TAU * f * 1.52 / sr;
    x[i] = (Math.sin(p1) * exp(-t / tau) + 0.3 * Math.sin(p2) * exp(-t / (tau * 0.45))) * Math.min(1, t / 0.001);
  }
  biquad(c, sr, 'lp', 5000, 0.7); biquad(c, sr, 'hp', 600, 0.7);
  for (let i = 0; i < c.length; i++) x[i] += c[i] * 0.9 * exp(-i / sr / 0.007);
  for (let i = 0; i < n; i++) x[i] = Math.tanh(1.5 * x[i]);
  return { sr, ch: norm(0.85, ...place(tail(x, sr, 0.04), pan)) };
}
// 스틱: two sticks struck together (the count-in)
function stick(sr, k) {
  const n = Math.round(0.09 * sr), x = new Float32Array(n), c = noise(Math.round(0.004 * sr), rng(61));
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    x[i] = Math.sin(TAU * 1720 * k * t) * exp(-t / 0.012) + 0.6 * Math.sin(TAU * 2890 * k * t) * exp(-t / 0.008) + 0.35 * Math.sin(TAU * 4350 * k * t) * exp(-t / 0.005);
  }
  for (let i = 0; i < c.length; i++) x[i] += c[i] * 0.8 * (1 - i / c.length);
  return { sr, ch: norm(0.7, tail(x, sr, 0.01)) };
}

// ---------------------------------------------------------------- the forecourt
// the room's impulse (left, right): the first echoes off 대강당's front and the porch, then a short tail that darkens
export function roomIR(sr) {
  const n = Math.round(1.2 * sr), r = rng(71), ch = [];
  for (let c = 0; c < 2; c++) {
    const x = noise(n, r), d = new Float32Array(n);
    biquad(x, sr, 'hp', 260, 0.7); biquad(x, sr, 'lp', 7500, 0.7);
    d.set(x); biquad(d, sr, 'lp', 2400, 0.7);
    for (let i = 0; i < n; i++) {
      const t = i / sr, u = Math.min(1, t / 0.7);
      x[i] = (x[i] * (1 - u) + d[i] * u * 1.4) * exp(-6.91 * t / 1.0) * smooth((t - 0.018) / 0.03);
    }
    let e = 0;
    for (let i = 0; i < n; i++) e += x[i] * x[i];
    scale(0.8 / Math.sqrt(e), x);
    for (const [t, g, side] of [[0.011, 0.34, 0], [0.017, 0.3, 1], [0.026, 0.26, 0], [0.037, 0.2, 1], [0.052, 0.17, 0], [0.071, 0.14, 1], [0.093, 0.1, 0]]) {
      x[Math.round(t * sr)] += g * (side === c ? 1 : 0.35) * (r() < 0.5 ? -1 : 1);
    }
    ch.push(tail(x, sr, 0.1));
  }
  return { sr, ch };
}

// ---------------------------------------------------------------- what an event plays
// each instrument's loudness in the mix (cheerband.js), and how much of it goes to the room
export const MIX = {
  drums: { g: 0.42, room: 0.16 }, gtr: { g: 0.6, room: 0.1 }, bass: { g: 0.36, room: 0.02 },
  lead: { g: 0.6, room: 0.22 }, keys: { g: 0.18, room: 0.15 },
};
const DRUM = {
  kick: ['kick', 0.85], boom: ['boom', 0.55], snare: ['snare', 0.8], snare2: ['snare', 0.5], ghost: ['snare', 0.16],
  tick: ['hat', 0.3], hath: ['hath', 0.34], hato: ['hato', 0.36], cymbal: ['crash', 0.55],
  tom1: ['tom1', 0.75], tom2: ['tom2', 0.8], tom3: ['tom3', 0.85], rim: ['stick', 0.5], rim2: ['stick2', 0.55],
};
export const BAND = new Set([...Object.keys(DRUM), 'gtr', 'bass', 'lead', 'harm', 'keys']);

// an event of cheersong.js's bandOf → the buffers it plays: { inst, id, g, pan, len (s: how long a buffer it needs),
// off (s after the start: let go there, over rel s; none: it rings out) }
export function partsOf(e) {
  const k = e.k ?? 1;
  if (DRUM[e.kind]) { const [id, g] = DRUM[e.kind]; return [{ inst: 'drums', id, g: g * k }]; }
  switch (e.kind) {
    case 'gtr': return e.open
      ? [{ inst: 'gtr', id: `go${e.m}`, g: k, len: e.d + 0.35, off: e.d, rel: 0.3 }]
      : [{ inst: 'gtr', id: `gm${e.m}`, g: k * 1.05, len: 0.45, off: Math.max(0.12, e.d), rel: 0.06 }];
    case 'bass': return [{ inst: 'bass', id: `b${e.m}`, g: k, len: e.d + 0.1, off: e.d, rel: 0.06 }];
    case 'lead': return [{ inst: 'lead', id: `l${e.m}`, g: k, pan: 0.08, len: e.d + 0.1, off: e.d, rel: 0.07 }];
    case 'harm': return [{ inst: 'lead', id: `l${e.m}`, g: k * 0.6, pan: -0.3, len: e.d + 0.1, off: e.d, rel: 0.07 }];
    case 'keys': return e.m.map((m) => ({ inst: 'keys', id: `o${m}`, g: k, pan: -0.2, len: e.d + 0.15, off: e.d, rel: 0.12 }));
  }
  return [];
}

// the buffer of an id: { sr, ch: [Float32Array (, Float32Array)] }; len: s (the notes that are held)
export function make(id, len, sr) {
  const m = +id.slice(id[0] === 'g' ? 2 : 1);
  switch (id) {
    case 'kick': return kick(sr);
    case 'boom': return boom(sr);
    case 'snare': return snare(sr);
    case 'hat': return hat(sr, 0.012, 0.09, 0.3);
    case 'hath': return hat(sr, 0.045, 0.3, 0.3);
    case 'hato': return hat(sr, 0.11, 0.6, 0.3);
    case 'crash': return crash(sr);
    case 'tom1': return tom(sr, 168, 0.11, -0.35);
    case 'tom2': return tom(sr, 124, 0.14, 0.05);
    case 'tom3': return tom(sr, 90, 0.18, 0.4);
    case 'stick': return stick(sr, 1);
    case 'stick2': return stick(sr, 1.16);
  }
  if (id.startsWith('go')) return guitar(sr, m, len, true);
  if (id.startsWith('gm')) return guitar(sr, m, len, false);
  if (id[0] === 'b') return bass(sr, m, len);
  if (id[0] === 'l') return brass(sr, m, len);
  if (id[0] === 'o') return organ(sr, m, len);
  return null;
}

// the buffers a list of events needs: id → the longest len asked (s, rounded up to a quarter second)
export function needsOf(events) {
  const need = new Map();
  for (const e of events) for (const p of partsOf(e)) need.set(p.id, Math.max(need.get(p.id) ?? 0, Math.ceil((p.len ?? 0) * 4) / 4));
  return need;
}
