// The loading screen: the bar with its percentage (index.html #loadbar) and the cards that keep the wait company
// (#waitbox: 삐삐 number codes to guess, and things about the 1997 campus).
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

// ------------------------------------------------------------------ the cards
// 삐삐(무선호출기) 숫자 암호: the number first, its meaning after a moment or a tap. The others are things about the
// campus of this game (reference/고증.md, the 추억 카드 texts of tools/build_campus.py) and about 1997.
const CODES = [
  ['8282', '빨리빨리', '「빨리 와!」'],
  ['1004', '천사', '「넌 나의 천사」'],
  ['486', '사랑해', '글자의 획수가 4 · 8 · 6'],
  ['1010235', '열렬히 사모', '열(10) · 열(10) · 이(2) · 삼(3) · 오(5)'],
  ['7942', '친구 사이', '「우리는 친구 사이」'],
  ['0242', '연인 사이', '「우리는 연인 사이」'],
  ['0404', '영원히 사랑해', '영(0) · 사(4) · 영(0) · 사(4)'],
  ['1212', '홀짝홀짝', '「술 한잔하자」'],
  ['175', '일찍 와', '일(1) · 칠(7) · 오(5)'],
  ['045', '빵 사 와', '빵(0) · 사(4) · 오(5)'],
  ['100', '돌아와', 'back(백) = 100'],
  ['2848', '이판사판', '이(2) · 팔(8) · 사(4) · 팔(8)'],
];
const FACTS = [
  ['12', '백양로의 오르막', '정문에서 본관 앞 삼거리까지 백양로는 12 m를 오릅니다. 그래서 아침마다 숨이 찼습니다.'],
  ['1997', '옛 노천극장', '잔디 계단 객석의 옛 노천극장은 1997년이 마지막 해였습니다. 그 마지막 모습을 걸어 보세요.'],
  ['1974', '활천대', '독수리상 옆 분수 활천대 앞에서는, 생일을 맞은 친구에게 다가가 보세요.'],
  ['1996', '대우관', '대우관은 1996년 6월에 문을 열었습니다. 정문에서 900 m, 가장 높고 깊숙한 곳입니다.'],
  ['2015', '백양로', '1997년의 백양로는 차와 사람이 함께 다니던 2차선 길이었습니다. 차도는 2015년에 땅속으로 들어갔습니다.'],
  ['1957', '용재관', '언더우드 동상 너머의 흰 계단탑, 용재관은 1957년에 지어져 2013년에 헐렸습니다.'],
  ['200', '건물', '랜드마크 말고도 200여 동의 건물이 실제 외곽선 위에 서 있습니다. 창의 7 %쯤은 열려 있습니다.'],
  ['33', '번호판', '차들은 2004년 이전의 두 줄 번호판을 달았습니다. 녹색 바탕에 「서울 33 가 1997」.'],
  ['0', '시내버스', '1997년에는 시내버스가 교내로 들어오지 않았습니다. 그래서 백양로에는 버스가 없습니다.'],
  ['419', '4 · 19 마라톤', '1997년 4월 18일 학생회관 앞에서 200여 명이 10 km를 달렸습니다.'],
  ['2', '제2백양로', '굴다리 너머 신촌 거리를 「제2백양로」라고 불렀습니다. 가을이면 푸른 응원 현수막이 걸렸습니다.'],
  ['1971', '독수리다방', '굴다리 앞 독수리다방은 1971년에 문을 열었습니다. 삐삐가 없던 때에는 메모판에 쪽지를 남겼습니다.'],
  ['97.3', '시티폰', '1997년 3월, 걸 수만 있는 전화 시티폰이 나왔습니다. 공중전화 부스 근처에서만 터졌습니다.'],
  ['97.10', 'PCS', '1997년 10월에 016 · 018 · 019 PCS가 시작되었습니다. 삐삐의 시대가 저물던 가을입니다.'],
  ['01410', 'PC통신', '01410은 하이텔의 접속 번호였습니다. 모뎀 소리가 끝나야 파란 화면이 열렸습니다.'],
  ['E', '추억 카드', '랜드마크 앞에서 E 를 누르면(폰은 「추억 보기」) 그 시절 사진이 담긴 추억 카드가 열립니다.'],
  ['3', '계절', '4월 벚꽃, 5월 신록, 10월 단풍. 걷는 중에도 설정에서 계절을 바꿀 수 있습니다.'],
];
const SHOW_Q = 2800, SHOW_A = 4200, SHOW_FACT = 7500;

function shuffled(list, rnd = Math.random) {
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

function waitCards() {
  const box = $('#waitbox');
  if (!box) return;
  const lcd = box.querySelector('.lcd b'), kicker = box.querySelector('small'), line = box.querySelector('.line');
  // a code, then a fact, in turn: both lists in a new order every visit
  const codes = shuffled(CODES), facts = shuffled(FACTS);
  const deck = [];
  for (let i = 0; i < Math.max(codes.length, facts.length); i++) {
    deck.push({ code: codes[i % codes.length] }, { fact: facts[i % facts.length] });
  }
  let at = -1, open = true, timer = 0;
  const later = (ms, fn) => { clearTimeout(timer); timer = setTimeout(fn, ms); };
  const flip = (fn) => {
    // (the text changes while it is faded out: style.css .turn)
    box.classList.add('turn');
    setTimeout(() => { fn(); box.classList.remove('turn'); }, 160);
  };
  const reveal = () => {
    const [, meaning, how] = deck[at].code;
    open = true;
    box.classList.remove('ask');
    flip(() => { kicker.textContent = '삐삐 암호'; line.innerHTML = `<b>${meaning}</b> <span>${how}</span>`; });
    later(SHOW_A, next);
  };
  const next = () => {
    if (box.offsetParent === null) return;            // (the walk has begun: the title screen is hidden)
    at = (at + 1) % deck.length;
    const card = deck[at];
    flip(() => {
      if (card.code) {
        lcd.textContent = card.code[0];
        kicker.textContent = '삐삐가 울렸습니다';
        line.innerHTML = '무슨 뜻일까요? <span>눌러서 확인</span>';
      } else {
        const [n, title, text] = card.fact;
        lcd.textContent = n;
        kicker.textContent = title;
        line.textContent = text;
      }
    });
    box.classList.toggle('ask', !!card.code);
    box.classList.add('ring');
    setTimeout(() => box.classList.remove('ring'), 900);
    open = !card.code;
    later(card.code ? SHOW_Q : SHOW_FACT, card.code ? reveal : next);
  };
  box.addEventListener('click', () => (open ? next() : reveal()));
  // (a hidden tab's timers crawl: start again from the next card when it comes back)
  document.addEventListener('visibilitychange', () => { if (!document.hidden && box.offsetParent !== null) later(600, next); });
  next();
}

function setup() {
  els.bar = $('#loadbar'); els.fill = $('#loadfill'); els.pct = $('#loadpct'); els.text = $('#loadtext'); els.bytes = $('#loadbytes');
  if (!els.fill) return;
  update();
  waitCards();
}
setup();
