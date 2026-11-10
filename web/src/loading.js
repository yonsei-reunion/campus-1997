// The loading screen: the bar with its percentage (index.html #loadbar) and the cards that keep the wait company
// (#waitbox: a 삐삐 quiz, the meaning shown and the number keyed in).
import { $, MOBILE, versioned } from './util.js';

// ------------------------------------------------------------------ the bar
// Two measures, each 0..1, make the percentage:
//   down   what has come down: the models' and data's bytes, counted as their streams arrive (fetchCounted), and the
//          textures in out of those asked for (materials.js texCount; an <img> each, so by their mean size)
//   work   main.js's steps done, each by the time it takes (parsing, merging, planting, compiling the shaders)
// How much of the wait is the download depends on the line: a cached visit is all work, a slow line nearly all
// download. So the download's share is its expected time over the whole expected time, from the speed of the first
// two seconds (or of the whole download, when it is over sooner). Until then the bar shows the smaller of the two
// extremes, so fixing the share never takes it back.
const WORK_S = MOBILE ? 22 : 9;   // seconds of work once everything is down (measured: TECH_NOTE.md 「로딩 화면」)
const SHARE = [0.08, 0.88];       // the download's share: no less, no more
const TEX_EXPECT = 100;           // textures a load asks for (fewer are known at first: the share is of this many)
const TEX_BYTES = 280e3;          // their mean size (29 MB over 105 on a desktop)
const GUESS = 150e3;              // a file whose size is not known yet counts as this many bytes
const MEASURE_MS = 2000;

const files = new Set();          // { got, size, packed, done }
let work = 0, workTotal = 1, texAsked = 0, texDone = 0;
let share = 0, firstByte = 0;     // share 0: not fixed yet
let target = 0, shown = 0, raf = 0, finished = false;
const marks = [];                 // [ms, label, weight] of every step: where a load's time went (loading.state)
const els = {};

// The body of `url` as an ArrayBuffer, its bytes counted into the bar as they arrive. Throws as fetch does, and on a
// status that is not ok.
export async function fetchCounted(url, init) {
  const f = { got: 0, size: 0, packed: false, done: false };
  files.add(f);
  try {
    const r = await fetch(versioned(url), init);
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    f.size = +r.headers.get('content-length') || 0;
    // (a compressed answer's length is the compressed one, while the stream hands over the unpacked bytes)
    f.packed = !['', 'identity'].includes(r.headers.get('content-encoding') || '');
    if (!r.body) {
      const b = await r.arrayBuffer();
      f.got = b.byteLength;
      return b;
    }
    const reader = r.body.getReader();
    const parts = [];
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      parts.push(value);
      f.got += value.byteLength;
      firstByte ||= performance.now();
      update();
    }
    const out = new Uint8Array(f.got);
    let at = 0;
    for (const p of parts) { out.set(p, at); at += p.byteLength; }
    return out.buffer;
  } finally {
    f.done = true;
    update();
  }
}

// { got, all: bytes in and expected over the files and the textures, counted: the files' bytes alone, coming: a file
// still on its way }
function downCount() {
  let got = 0, all = 0, coming = false;
  for (const f of files) {
    got += f.got;
    if (f.done) { all += f.got; continue; }
    coming = true;
    if (!f.size) all += Math.max(GUESS, f.got * 1.2);
    else all += f.packed ? Math.max(f.size * 3, f.got * 1.15) : Math.max(f.size, f.got);
  }
  const counted = got;
  got += texDone * TEX_BYTES;
  all += Math.max(texAsked, TEX_EXPECT) * TEX_BYTES;
  return { got, all, counted, coming: coming || texDone < texAsked };
}

// the download's share of the wait, once the line's speed is known
function fixShare(d) {
  if (share || !firstByte) return;
  const ms = performance.now() - firstByte;
  const filesIn = files.size > 2 && ![...files].some((f) => !f.done);
  if (ms < MEASURE_MS && !filesIn) return;
  const seconds = d.all / (d.counted / Math.max(ms, 50) * 1000);
  share = Math.min(SHARE[1], Math.max(SHARE[0], seconds / (seconds + WORK_S)));
}

const mb = (n) => (n / 1048576).toFixed(n < 10485760 ? 1 : 0);

function update() {
  const d = downCount();
  fixShare(d);
  const down = d.all ? d.got / d.all : 0, done = Math.min(1, work / workTotal);
  const mix = (k) => k * down + (1 - k) * done;
  const p = finished ? 100 : Math.min(99, 100 * (share ? mix(share) : Math.min(mix(SHARE[0]), mix(SHARE[1]))));
  if (p > target) target = p;            // (files asked for later would take the bar back: it only waits)
  if (!els.fill) return;
  els.fill.style.transform = `scaleX(${target / 100})`;
  els.bar.setAttribute('aria-valuenow', Math.round(target));
  // the megabytes while they are still coming down (nothing to say once everything is in)
  els.bytes.textContent = !finished && d.coming ? `${mb(d.got)} / ${mb(d.all)} MB` : '';
  if (!raf) raf = requestAnimationFrame(count);
}

// the number counts up to where the bar is going
function count() {
  raf = 0;
  shown += Math.max(0.4, (target - shown) * 0.2);
  if (shown > target) shown = target;
  els.pct.textContent = `${Math.floor(shown)}%`;
  if (shown < target) raf = requestAnimationFrame(count);
}

export const loading = {
  // main.js: the weights of all its steps together (a weight: hundredths of a second on a desktop)
  expect(total) { workTotal = total; },
  // a step is done; `label` says what comes next
  step(label, weight = 1) {
    work += weight;
    marks.push([Math.round(performance.now()), label || '', weight]);
    if (label && els.text) els.text.textContent = label;
    update();
  },
  // The last stretch holds the page (the first frames: every shader and shadow at once), so nothing can be counted
  // there. The bar glides on by itself instead, a transition the browser runs without the page's help.
  coast(seconds) {
    if (!els.fill || finished) return;
    target = Math.max(target, 99);
    els.fill.style.transitionDuration = `${seconds}s`;
    els.fill.style.transform = 'scaleX(0.99)';
  },
  // materials.js texCount: asked for, in
  textures(asked, done) { texAsked = asked; texDone = done; update(); },
  done(label) {
    finished = true;
    if (label && els.text) els.text.textContent = label;
    if (els.fill) els.fill.style.transitionDuration = '';
    update();
    shown = 100;
    if (els.pct) els.pct.textContent = '100%';
    els.bar?.classList.add('done');
    $('#loadblock')?.classList.add('done');          // (the wait is over: the cards fold away, style.css)
  },
  fail(message) {
    if (els.text) els.text.textContent = message;
    els.bar?.classList.add('failed');
  },
  // what the bar was made of (the weights and WORK_S above were set from runs of this)
  get state() { return { work, workTotal, texAsked, texDone, down: downCount(), share, target, marks }; },
};

// ------------------------------------------------------------------ the quiz
// 삐삐(무선호출기) 숫자 암호 맞히기: the meaning is shown, the number is keyed in on the pager's screen. It is checked
// once it has as many digits as the answer (a phone's number pad has no Enter), and only a right answer brings the
// next one. Every second miss shows one more digit of the answer, faintly, on the screen.
const CODES = [
  // [number, meaning, the kind of code (shown with the question), how it reads (shown once it is right)]
  ['38317', '사랑해', '뒤집어 읽는 숫자', '거꾸로 보면 LIEBE, 독일어로 「사랑」'],
  ['8282', '빨리빨리', '소리 내어 읽는 숫자', '팔(8) · 이(2) · 팔(8) · 이(2)'],
  ['7942', '친구 사이', '소리 내어 읽는 숫자', '칠(7) · 구(9) · 사(4) · 이(2)'],
  ['1004', '천사', '소리 내어 읽는 숫자', '천(1000) · 사(4)'],
  ['9090', '가자', '모양이 닮은 숫자', '9는 g, 0은 o를 닮아 「GO GO」'],
  ['505', '도와줘', '모양이 닮은 숫자', '5는 S, 0은 O를 닮아 「SOS」'],
  ['1472', '일사천리', '소리 내어 읽는 숫자', '일(1) · 사(4) · 칠(7) · 이(2)'],
];
const NEXT_MS = 2600, AGAIN_MS = 4000, MISS_MS = 650;

function shuffled(list, rnd = Math.random) {
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

function pagerQuiz() {
  const box = $('#waitbox');
  if (!box) return;
  const pad = box.querySelector('input'), kicker = box.querySelector('small'), line = box.querySelector('.line');
  let round = [], at = 0, misses = 0, lock = null, timer = 0;   // lock: the screen's text while it shows a verdict
  const later = (ms, fn) => { clearTimeout(timer); timer = setTimeout(fn, ms); };
  const flip = (fn) => {
    // (the text changes while it is faded out: style.css .turn)
    box.classList.add('turn');
    setTimeout(() => { fn(); box.classList.remove('turn'); }, 160);
  };
  const buzz = (cls, ms) => {
    box.classList.remove(cls);
    void box.offsetWidth;                              // (so the animation starts over)
    box.classList.add(cls);
    setTimeout(() => box.classList.remove(cls), ms);
  };
  const show = (text, faint) => { lock = faint ? null : text; pad.value = faint ? '' : text; pad.placeholder = faint ? text : ''; };
  const ask = () => {
    const [num, meaning, kind] = round[at];
    misses = 0;
    show('_'.repeat(num.length), true);
    pad.maxLength = num.length;
    box.classList.remove('right');
    flip(() => {
      kicker.textContent = `삐삐 퀴즈 ${at + 1} / ${round.length} · 이 뜻의 번호는?`;
      line.innerHTML = `<b>${meaning}</b> <span>${kind}</span>`;
    });
    buzz('ring', 900);
  };
  const deal = () => {
    const last = round[round.length - 1];
    round = shuffled(CODES);
    if (round[0] === last) round.push(round.shift());  // (a new round never opens with the code that ended the last)
    at = 0;
    ask();
  };
  const next = () => {
    if (++at < round.length) return ask();
    box.classList.remove('right');
    show(`${round.length}-${round.length}`);
    flip(() => { kicker.textContent = '삐삐 퀴즈 완주'; line.innerHTML = `<b>모두 맞혔습니다</b> <span>곧 새 판이 시작됩니다</span>`; });
    buzz('ring', 900);
    later(AGAIN_MS, deal);
  };
  const check = () => {
    const [num, meaning, , how] = round[at];
    if (pad.value === num) {
      show(num);
      box.classList.add('right');
      flip(() => { kicker.textContent = '정답!'; line.innerHTML = `<b>${meaning}</b> <span>${how}</span>`; });
      buzz('ring', 900);
      later(NEXT_MS, next);
      return;
    }
    misses++;
    const hint = Math.min(num.length, misses >> 1);
    show(pad.value);
    buzz('wrong', 400);
    kicker.textContent = hint ? '다시 한 번 · 화면에 힌트' : '다시 한 번';
    later(MISS_MS, () => show(num.slice(0, hint) + '_'.repeat(num.length - hint), true));
  };
  const typed = () => {
    if (lock !== null) { pad.value = lock; return; }  // (a verdict is on the screen: keys wait for the next question)
    const v = pad.value.replace(/\D/g, '');
    if (v !== pad.value) pad.value = v;
    if (!v) return;
    box.classList.add('played');                      // (a game in play is not folded away when the load is over)
    if (v.length >= round[at][0].length) check();
  };
  pad.addEventListener('input', typed);
  box.addEventListener('submit', (e) => { e.preventDefault(); if (lock === null && pad.value) check(); });
  box.addEventListener('click', (e) => { if (e.target !== pad) pad.focus(); });
  // on a desktop the digits can be typed straight away, wherever the focus is on the title card
  addEventListener('keydown', (e) => {
    if (!/^[0-9]$/.test(e.key) || e.ctrlKey || e.metaKey || e.altKey || e.target === pad) return;
    if (/INPUT|TEXTAREA|SELECT/.test(e.target.tagName) || box.offsetParent === null || $('#news')?.hidden === false) return;
    if ($('#loadblock')?.classList.contains('done') && !box.classList.contains('played')) return;   // (folded)
    e.preventDefault();
    pad.focus();
    if (lock === null && pad.value.length < pad.maxLength) pad.value += e.key;
    typed();
  });
  deal();
}

function setup() {
  els.bar = $('#loadbar'); els.fill = $('#loadfill'); els.pct = $('#loadpct'); els.text = $('#loadtext'); els.bytes = $('#loadbytes');
  if (!els.fill) return;
  update();
  pagerQuiz();
}
setup();
