// 미니 게임 전체 순위: 판마다 30위까지를 공개 DoltHub DB(benelog/yonsei-1997)의 표 scores 에 둔다. 읽기는 브라우저가
// DoltHub 에서 바로, 쓰기는 쪽지와 같은 Worker(notes-worker/src/rank.js)가 한다.
//
// 점수만 적은 요청으로는 올릴 수 없다. 한 판은 Run 하나:
//   - Run.open(board): Worker 에서 판 열쇠(서명한 판 번호 · 서버 시각 · 씨앗)를 받는다. 씨앗이 그 판의 문제를 정한다(rnd).
//   - 게임은 프레임마다 frame(dt, paused), 걷는 동안 sample(x, y), 일이 생기면 add(kind, x, y, ...)(rankrules.js).
//   - 8 s(판의 시계)마다, 멈출 때 · 다시 할 때 · 끝날 때 기록의 해시 사슬을 Worker 에 맡기고 영수증을 받는다(beat).
//   - submit(name): 기록 전체와 영수증을 서버의 공개 키와 일회용 키로 맞춘 AES-GCM 으로 봉해 보낸다.
//     서버는 영수증으로 기록이 판을 하는 동안 실시간으로 쌓였는지 보고, 점수는 기록에서 다시 셈한다.
// 열쇠를 못 받았거나 박동이 끊긴 판은 이 브라우저의 기록에만 남는다.
import { judge, parseBoard, boardTitle, showValue, showDetail, rng, TOP, NAME_MAX } from './rankrules.js';
import { safeGet, safeSet } from './util.js';
import './rank.css';

const API = (new URLSearchParams(location.search).get('notesapi') || 'https://y97-notes.habit-chain-worker.workers.dev').replace(/\/+$/, '');
const READ = 'https://www.dolthub.com/api/v1alpha1/benelog/yonsei-1997/main';
const NAME = 'y97-rank-name';
const BEAT = 8;          // s of the round's clock between beats (the server allows 12.5)
const EVERY = 0.25;      // s between points of the way
const enc = new TextEncoder();

const b64 = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const unb64 = (s) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/')), (c) => c.charCodeAt(0));
const hex = (buf) => [...new Uint8Array(buf)].map((x) => x.toString(16).padStart(2, '0')).join('');
const sha = async (s) => hex(await crypto.subtle.digest('SHA-256', enc.encode(s)));
const r2 = (v) => Math.round(v * 100) / 100;
const r3 = (v) => Math.round(v * 1000) / 1000;
const wait = (ms) => new Promise((ok) => setTimeout(ok, ms));

async function post(path, body, ms = 15000) {
  const ac = new AbortController(), timer = setTimeout(() => ac.abort(), ms);
  try {
    const res = await fetch(`${API}/rank/${path}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body), signal: ac.signal });
    const out = await res.json().catch(() => ({}));
    if (!res.ok) { const e = new Error(out.error || `HTTP ${res.status}`); e.status = res.status; throw e; }
    return out;
  } finally { clearTimeout(timer); }
}

// the sealed envelope: an ECDH key of this moment with the server's, through HKDF, to AES-GCM
async function seal(obj, pub) {
  const info = enc.encode('y97-rank-v1');
  const theirs = await crypto.subtle.importKey('raw', unb64(pub), { name: 'ECDH', namedCurve: 'P-256' }, false, []);
  const mine = await crypto.subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({ name: 'ECDH', public: theirs }, mine.privateKey, 256);
  const epub = new Uint8Array(await crypto.subtle.exportKey('raw', mine.publicKey));
  const hk = await crypto.subtle.importKey('raw', bits, 'HKDF', false, ['deriveKey']);
  const key = await crypto.subtle.deriveKey({ name: 'HKDF', hash: 'SHA-256', salt: epub, info }, hk, { name: 'AES-GCM', length: 256 }, false, ['encrypt']);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const c = await crypto.subtle.encrypt({ name: 'AES-GCM', iv, additionalData: info }, key, enc.encode(JSON.stringify(obj)));
  return { e: b64(epub), iv: b64(iv), c: b64(c) };
}

// ---------------------------------------------------------------- one round
export class Run {
  // the round's ticket, at most `ms` waited for (else the round is played for this browser alone)
  static async open(board, ms = 3000) {
    const run = new Run(board);
    await Promise.race([run.opening, wait(ms)]);
    if (run.state === 'opening') run.fail('순위 서버가 늦게 답해요');
    return run;
  }

  constructor(board) {
    this.board = board;
    this.game = parseBoard(board)?.game;
    this.log = [];
    this.beats = [];
    this.g = 0;                 // the round's clock
    this.k = 0;                 // beats sent
    this.sent = { n: 0, h: null };
    this.lastBeat = 0;
    this.lastP = -Infinity;
    this.paused = false;
    this.state = 'opening';     // opening | on | ended | off
    this.why = null;            // why not ranked
    this.rnd = Math.random;
    this.ctx = null;            // what the game knows that the judging may use (rankrules.js judge's ctx)
    this.queue = Promise.resolve();
    this.opening = (async () => {
      try {
        const r = await post('start', { board }, 8000);
        if (this.state !== 'opening') return;
        this.ticket = r.ticket; this.pub = r.pub; this.seed = r.seed;
        this.rnd = rng(r.seed);
        const sid = JSON.parse(new TextDecoder().decode(unb64(r.ticket.split('.')[0]))).sid;
        this.sent.h = await sha(sid);
        this.state = 'on';
        this.onHide = () => { if (document.hidden && this.state === 'on' && !this.paused) { this.paused = true; this.beat(1); } };
        document.addEventListener('visibilitychange', this.onHide);
      } catch (e) {
        this.fail(e.status && e.status !== 404 ? e.message : '순위 서버에 닿지 못했어요');
      }
    })();
  }

  get ranked() { return this.state === 'on' || this.state === 'ended'; }

  // (a round already over keeps its log: it can still go up from its results card)
  fail(why) {
    if (this.state === 'off' || this.state === 'ended') return;
    this.state = 'off';
    this.why = why;
    if (this.onHide) document.removeEventListener('visibilitychange', this.onHide);
  }

  // every frame while the game is on (paused: its menu or a card is up, the clock stopped)
  frame(dt, paused) {
    if (this.state !== 'on') return;
    if (paused !== this.paused) { this.paused = paused; this.beat(paused ? 1 : 2); }
    if (paused) return;
    this.g += dt;
    if (this.g - this.lastBeat >= BEAT) this.beat(0);
  }

  add(kind, x, y, ...more) {
    if (this.state !== 'on') return;
    this.log.push([r3(this.g), kind, r2(x), r2(y), ...more.map((v) => r3(+v))]);
    if (kind !== 'p') this.lastP = this.g;
  }
  // a point of the way, every EVERY s
  sample(x, y) {
    if (this.state !== 'on' || this.g - this.lastP < EVERY) return;
    this.lastP = this.g;
    this.add('p', x, y);
  }

  // hand the log's hash chain so far to the server for a receipt (f: 0 · 1 pause · 2 resume · 3 the end)
  beat(f) {
    if (this.state !== 'on') return this.queue;
    const k = ++this.k, n = this.log.length, g = r3(this.g), from = this.sent.n;
    this.sent.n = n;
    this.lastBeat = this.g;
    const chunk = JSON.stringify(this.log.slice(from, n));
    this.queue = this.queue.then(async () => {
      if (this.state === 'off') return;
      const h = this.sent.h = await sha(`${this.sent.h}|${chunk}`);
      for (let tries = 0; ; tries++) {
        try {
          const r = await post('beat', { ticket: this.ticket, k, n, g, h, f }, 8000);
          this.beats.push({ k, n, g, h, f, ts: r.ts, r: r.r });
          return;
        } catch (e) {
          if (e.status === 400 || tries >= 3) { this.fail('순위 서버와 연결이 끊겼어요'); return; }
          await wait(800 * (tries + 1));
        }
      }
    });
    return this.queue;
  }

  // the round is over: the last beat (the log stops here)
  end() {
    if (this.state !== 'on') return this.queue;
    const q = this.beat(3);
    this.state = 'ended';
    if (this.onHide) document.removeEventListener('visibilitychange', this.onHide);
    return q;
  }

  // this browser's own judging of the log (the server does the same): { value, sort, detail } or { error }
  result() {
    if (!this._res) this._res = judge(this.board, this.log, { seed: this.seed, ...this.ctx });
    return this._res;
  }

  async submit(name, hero) {
    await this.queue;
    if (this.state !== 'ended') throw new Error(this.why || '아직 끝나지 않은 판이에요');
    const env = await seal({ ticket: this.ticket, name, hero, beats: this.beats, log: this.log }, this.pub);
    const out = await post('submit', env, 30000);
    this.done = out;
    return out;
  }
}

// ---------------------------------------------------------------- the board, read straight from DoltHub
const lit = (s) => `'${String(s).replace(/\\/g, '\\\\').replace(/'/g, "''")}'`;
export async function fetchTop(board) {
  const q = `SELECT sid, name, sort, value, detail, hero, created_at FROM scores WHERE board = ${lit(board)} ORDER BY sort, created_at LIMIT ${TOP}`;
  const res = await fetch(`${READ}?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error(`DoltHub ${res.status}`);
  const j = await res.json();
  if (j.query_execution_status !== 'Success' && j.query_execution_status !== 'RowLimit') throw new Error(j.query_execution_message || 'DoltHub');
  return j.rows || [];
}

export const lastName = () => safeGet(NAME) || safeGet('y97-shoot-name') || '';

// created_at is the server's UTC: shown as this browser's date (a Korean morning is the day after UTC's evening)
const day = (s) => {
  const d = new Date(`${String(s || '').replace(' ', 'T')}Z`);
  return Number.isNaN(d.getTime()) ? '' : `${d.getMonth() + 1}/${d.getDate()}`;
};
const parse = (s) => { try { return JSON.parse(s || '{}'); } catch { return {}; } };

// ---------------------------------------------------------------- the box on a results card
// new RankBox() once per card (append box.el where it goes, or mountRankBox), then box.set(run, { hero, heroName })
// for each round; box.view(board) shows a board alone (no round, no form)
export class RankBox {
  constructor() {
    const el = this.el = document.createElement('section');
    el.className = 'rankbox';
    el.innerHTML = '<h3>전체 순위 <small></small></h3><p class="rk-msg"></p>'
      + `<form class="rk-form" hidden><input type="text" maxlength="${NAME_MAX}" enterkeyhint="send" autocomplete="nickname" spellcheck="false" placeholder="이름" aria-label="순위에 적을 이름" />`
      + '<button type="submit">순위에 올리기</button></form>'
      + '<ol class="rk-list"></ol><button type="button" class="rk-more" hidden>30위까지 모두 보기</button>';
    this.msg = el.querySelector('.rk-msg');
    this.form = el.querySelector('.rk-form');
    this.input = this.form.querySelector('input');
    this.btn = this.form.querySelector('button');
    this.list = el.querySelector('.rk-list');
    this.more = el.querySelector('.rk-more');
    this.input.addEventListener('keydown', (e) => { if (e.code !== 'Escape') e.stopPropagation(); });
    this.form.addEventListener('submit', (e) => { e.preventDefault(); this.send(); });
    this.more.addEventListener('click', () => { this.all = !this.all; this.draw(); });
  }

  // the board without a round of this browser (the ranking window of the title card and the pause card)
  async view(board) {
    const run = this.run = { board, game: parseBoard(board)?.game, ranked: false };
    this.all = true; this.mark = null; this.rows = null; this.onName = null;
    this.el.querySelector('h3 small').textContent = `${boardTitle(board)} · ${TOP}위까지`;
    this.form.hidden = true;
    this.say('순위를 읽는 중…');
    this.draw();
    try {
      this.rows = await fetchTop(board);
      if (this.run === run) this.say('');
    } catch {
      this.rows = [];
      if (this.run === run) this.say('순위를 읽지 못했어요', 'off');
    }
    if (this.run === run) this.draw();
  }

  // onName(name): called with the name a round went up under (a game keeps it on its own record too)
  async set(run, { hero = '', heroName = '', onName = null } = {}) {
    this.run = run; this.hero = hero; this.all = false; this.mark = null; this.rows = null; this.onName = onName;
    const board = run?.board;
    this.el.querySelector('h3 small').textContent = board ? `${boardTitle(board)} · ${TOP}위까지` : '';
    this.form.hidden = true;
    this.input.value = lastName();
    this.input.placeholder = heroName ? `이름 (비우면 ${heroName})` : '이름';
    this.heroName = heroName;
    this.say(run?.ranked ? '순위를 읽는 중…' : '');
    this.draw();
    if (!run) return;
    const my = run.ranked ? run.result() : null;
    try {
      this.rows = await fetchTop(board);
    } catch {
      this.rows = [];
      if (this.run === run) this.say('순위를 읽지 못했어요');
    }
    if (this.run !== run) return;
    this.draw();
    if (!run.ranked) { this.say(`이번 판은 이 브라우저에만 적었어요 (${run.why || '순위 서버에 닿지 못했어요'})`, 'off'); return; }
    if (my.error) { this.say(`이번 판은 순위에 올릴 수 없어요 (${my.error})`, 'off'); return; }
    const rank = 1 + this.rows.filter((r) => +r.sort <= my.sort).length;
    if (rank > TOP) {
      this.say(`${TOP}위 안에 들지 못했어요 · ${TOP}위 ${showValue(run.game, +this.rows[TOP - 1].value, parse(this.rows[TOP - 1].detail))}`, 'off');
      return;
    }
    this.say(`전체 ${rank}위에 드는 기록이에요! 이름을 적어 올려 보세요`, 'good');
    this.form.hidden = false;
    this.btn.disabled = false;
  }

  async send() {
    const run = this.run;
    if (!run || this.btn.disabled) return;
    const name = (this.input.value.trim() || this.heroName).slice(0, NAME_MAX);
    if (!name) { this.input.focus(); return; }
    safeSet(NAME, this.input.value.trim());
    this.btn.disabled = true;
    this.say('올리는 중…');
    try {
      const out = await run.submit(name, this.hero);
      if (this.run !== run) return;
      this.onName?.(name);
      this.form.hidden = true;
      if (out.rank) {
        this.rows = out.top; this.mark = out.sid;
        this.say(`전체 ${out.rank}위로 올렸어요!`, 'good');
      } else this.say(`그사이 다른 기록이 올라와 ${TOP}위 밖이 됐어요`, 'off');
      this.draw();
    } catch (e) {
      if (this.run !== run) return;
      this.say(e.message || '올리지 못했어요', 'off');
      this.btn.disabled = !!e.status && e.status !== 429;
    }
  }

  say(text, cls = '') {
    this.msg.textContent = text;
    this.msg.className = `rk-msg ${cls}`;
  }

  draw() {
    const rows = this.rows || [], game = this.run?.game, at = rows.findIndex((r) => r.sid === this.mark);
    const show = this.all ? rows : rows.slice(0, 5);
    const li = (r, i) => {
      const e = document.createElement('li');
      e.classList.toggle('me', r.sid === this.mark);
      const d = parse(r.detail);
      e.innerHTML = '<span class="n"></span><span class="w"></span><span class="v"></span><span class="d"></span>';
      e.querySelector('.n').textContent = `${i + 1}`;
      e.querySelector('.w').textContent = r.name;
      e.querySelector('.v').textContent = showValue(game, +r.value, d);
      e.querySelector('.d').textContent = [showDetail(game, d), day(r.created_at)].filter(Boolean).join(' · ');
      return e;
    };
    const items = show.map(li);
    if (at >= show.length) {
      const gap = document.createElement('li'); gap.className = 'gap'; gap.textContent = '⋯';
      items.push(gap, li(rows[at], at));
    }
    if (this.rows && !rows.length) { const e = document.createElement('li'); e.className = 'none'; e.textContent = '아직 올린 기록이 없어요. 첫 기록을 올려 보세요'; items.push(e); }
    this.list.replaceChildren(...items);
    this.more.hidden = rows.length <= 5;
    this.more.textContent = this.all ? '다섯 위까지만 보기' : `${TOP}위까지 모두 보기 (${rows.length}명)`;
  }
}

// the box on a results card, above the card's own list of this browser's rounds (`mine`), which gets the heading
// 「내 기록」 (a heading already there just before it is reused)
export function mountRankBox(mine) {
  const box = new RankBox();
  let head = mine.previousElementSibling;
  if (head?.tagName !== 'H3') { head = document.createElement('h3'); mine.before(head); }
  head.className = 'rk-mine';
  head.textContent = '내 기록 (이 브라우저)';
  head.before(box.el);
  return box;
}
