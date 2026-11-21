// 미니 게임 전체 순위의 판정 규칙. 브라우저(rank.js)와 Worker(notes-worker/src/rank.js)가 같은 코드를 읽는다:
// 게임이 보낸 점수는 쓰지 않고, 판의 기록(log: 궤적과 사건)에서 점수를 다시 셈하고 그 기록이 게임에서 나올 수
// 있는 것인지 본다. three.js 를 읽지 않는다.
//
// 기록 한 줄: [t, kind, x, y, ...더] — t 는 판의 시계(s, 판 열쇠를 받은 뒤 멈추지 않은 프레임의 dt 합), x · y 는
// 걷는 사람의 캠퍼스 자리(m). 줄마다 자리가 있어 모든 줄이 궤적의 점이다. kind:
//   p    궤적(0.25 s 마다)
//   go   출발(카운트가 끝남 · 판의 첫 자리). 사진 찾기는 q 가 문제마다의 출발
//   sh   슛이 손을 떠남 [.., three]            mk   그 슛이 들어감 [.., 슛 번호]       end  버저
//   g    문을 지남 [.., 문 번호]
//   q    사진 문제의 출발 [.., 문제 번호]       a    찍음 [.., 문제 번호, 보는 방위(°)]
//   ar   현관에 닿음 [.., 교시 번호]
//   pk   친구 합류 [.., 친구 번호]              fin  생일인 친구에게 E
//   pg   삐삐가 옴 [.., 몇 번째]               lf   수화기를 듦(부스의 자리로 옮겨짐)    cn   연결됨
//   ans  숫자 암호 [.., 맞음 1 · 틀림 0]       ag   만날 곳을 들음                       mt   만남
//   st   응원 시작(노래 시계 [.., 그때의 노래 시각])      ht   동작 [.., 표시 번호, 박에서 벗어난 s]
import { COURSES, courseOf, lineOf } from './courses.js';
import { CHARTS, chartOf, notesOf, lengthOf, JUDGE as CHEER_JUDGE, LATE as CHEER_LATE } from './cheercharts.js';
import { setOf, todaySet, legsOf, wayOf, dayKey, SETS } from './timetables.js';
import { RUN } from './pace.js';

export const TOP = 30;                 // 판마다 남기는 순위
export const NAME_MAX = 12;

// ---------------------------------------------------------------- the games' own constants (the games read them here)
export const SHOOT = { TIME: 60 };
export const PHOTO = { ROUND: 5, LIMIT: 100, SEP: 15, NEAR: [60, 170], POS: 700, DIR: 300, D_FULL: 2, D_ZERO: 42, A_FULL: 10, A_ZERO: 70 };
export const RACE = { GATE_R: 4.5 };
export const CLASS = { DOOR_R: 5.5 };
export const PAGER = { PAGES: 3, NEAR: 1.4, MEET_R: 4.0 };
export const BDAY = { N: 4, LIMIT: 300, NEAR: 4.0, BDAY_NEAR: 4.4,
  HALLS: ['제1공학관', '백주년기념관', '학생회관', '중앙도서관', '체육관', '광혜원', '루스채플', '제2공학관', '장기원 기념관'] };

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const wrap = (a) => { a = (a + Math.PI) % (2 * Math.PI); return a < 0 ? a + Math.PI : a - Math.PI; };
const DEG = Math.PI / 180;

export function photoScore(d, a) {
  const P = PHOTO;
  const p = clamp((P.D_ZERO - Math.max(d, P.D_FULL)) / (P.D_ZERO - P.D_FULL), 0, 1);
  const w = d < P.D_ZERO ? clamp((P.A_ZERO - Math.max(a, P.A_FULL)) / (P.A_ZERO - P.A_FULL), 0, 1) : 0;
  return { pos: Math.round(P.POS * p), dir: Math.round(P.DIR * w), total: Math.round(P.POS * p) + Math.round(P.DIR * w) };
}

// ---------------------------------------------------------------- the seeded draw (the ticket's seed)
// the server's seed decides what a round deals (the photos, the friends' halls), so a client cannot pick easy ones
export function rng(seed) {
  let s = (typeof seed === 'string' ? parseInt(seed.slice(0, 8), 16) : seed) >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
export function shuffle(a, rnd = Math.random) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}
// the photos of a round: shuffled, no two answers closer than SEP
export function pickPhotos(items, rnd) {
  const pick = [];
  for (const q of shuffle([...items], rnd)) {
    if (pick.length < PHOTO.ROUND && pick.every((p) => Math.hypot(p.x - q.x, p.y - q.y) >= PHOTO.SEP)) pick.push(q);
  }
  return pick;
}
// the friends' halls: names of BDAY.HALLS that have a place, shuffled, the first N
export const pickHalls = (has, rnd) => shuffle(BDAY.HALLS.filter(has), rnd).slice(0, BDAY.N);
// 삐삐 호출's times: to a booth from where the page came (the straight way to the nearest, a third more, some to dial),
// and to the meeting place from the booth
const round5 = (s) => Math.ceil(s / 5) * 5;
export const callLimit = (d) => round5(20 + (d * 1.35) / RUN);
export const meetLimit = (d) => round5(12 + (d * 1.35) / RUN);
// the meeting place: somewhere 80 - 230 m off, not within 40 m of where the game has been (used: pushed to)
export function pickMeet(places, x, y, used, rnd) {
  const ok = (p, lo, hi) => {
    const d = Math.hypot(p.x - x, p.y - y);
    return d > lo && d < hi && p.y > -420 && p.y < 460 && !used.some((u) => Math.hypot(u.x - p.x, u.y - p.y) < 40);
  };
  let list = places.filter((p) => ok(p, 80, 230));
  if (!list.length) list = places.filter((p) => ok(p, 40, 400));
  if (!list.length) list = places;
  const p = list[Math.floor(rnd() * list.length)];
  const m = { x: p.x, y: p.y, name: p.name };
  used.push(m);
  return m;
}
// 응원 연습's points for a sign hit `off` s from its beat, the combo so far counted in
export function cheerPoints(off, combo) {
  const j = CHEER_JUDGE.findIndex((x) => Math.abs(off) <= x.w);
  return j < 0 ? null : { j, pts: Math.round(CHEER_JUDGE[j].pts * (1 + Math.min(combo, 40) * 0.025)) };
}

// ---------------------------------------------------------------- boards
// shoot · photo · bday · pager: one board each; race:<course>; cheer:<chart>; class:<timetable>[:easy]
// (오늘의 시간표: class:today-YYYYMMDD)
export function parseBoard(board) {
  if (typeof board !== 'string' || board.length > 48) return null;
  if (['shoot', 'photo', 'bday', 'pager'].includes(board)) return { game: board };
  let c = board.match(/^cheer:([a-z]+)$/);
  if (c) return chartOf(c[1]) ? { game: 'cheer', chart: c[1] } : null;
  let m = board.match(/^race:([a-z_]+)$/);
  if (m) return courseOf(m[1]) ? { game: 'race', course: m[1] } : null;
  m = board.match(/^class:([a-z]+|today-\d{8})(:easy)?$/);
  if (m) {
    const today = m[1].startsWith('today-');
    if (!today && !SETS.some((s) => s.id === m[1])) return null;
    return { game: 'class', set: m[1], easy: !!m[2], today: today ? m[1].slice(6) : null };
  }
  return null;
}
export const raceBoard = (id) => `race:${id}`;
export const cheerBoard = (id) => `cheer:${id}`;
export const classBoard = (id, easy) => `class:${id}${easy ? ':easy' : ''}`;

export function boardTitle(board) {
  const b = parseBoard(board);
  if (!b) return board;
  if (b.game === 'shoot') return '1분 슛 게임';
  if (b.game === 'photo') return '이곳은 어디?';
  if (b.game === 'bday') return '생일 축하';
  if (b.game === 'pager') return '삐삐 호출';
  if (b.game === 'cheer') return `응원 연습 · ${chartOf(b.chart).name}`;
  if (b.game === 'race') return `캠퍼스 달리기 · ${courseOf(b.course).name}`;
  const set = b.today ? { name: `오늘의 시간표 (${+b.today.slice(4, 6)}월 ${+b.today.slice(6)}일)` } : SETS.find((s) => s.id === b.set);
  return `강의실 찾기 · ${set.name}${b.easy ? ' · 쉬운 판' : ''}`;
}

const mmss = (s, d = 1) => { const m = Math.floor(s / 60), r = s - m * 60; return `${m}:${r.toFixed(d).padStart(d ? 3 + d : 2, '0')}`; };
// the ranking's main column: what `value` is in that game
export function showValue(game, value, detail = {}) {
  if (game === 'shoot') return `${value}골`;
  if (game === 'photo' || game === 'pager' || game === 'cheer') return `${value.toLocaleString('ko-KR')}점`;
  if (game === 'race') return mmss(value, 2);
  if (game === 'class') return detail.late ? `${mmss(value)} · 지각 ${detail.late}` : mmss(value);
  return mmss(value, 1);
}
// and its small print
export function showDetail(game, d = {}) {
  if (game === 'shoot') return d.shots ? `${Math.round(100 * d.makes / d.shots)}% · 슛 ${d.shots}${d.threes ? ` · 3점 ${d.threes}` : ''}` : '';
  if (game === 'pager') return d.calls !== undefined ? `${d.calls}통 · 암호 ${d.right}개` : '';
  if (game === 'cheer') return d.acc !== undefined ? `정확도 ${Math.round(d.acc * 100)}% · 콤보 ${d.combo}` : '';
  return '';
}

// ---------------------------------------------------------------- judging a round
const KINDS = {
  shoot: new Set(['p', 'go', 'sh', 'mk', 'end']),
  race: new Set(['p', 'go', 'g']),
  photo: new Set(['p', 'q', 'a']),
  class: new Set(['p', 'go', 'ar']),
  bday: new Set(['p', 'go', 'pk', 'fin']),
  pager: new Set(['p', 'go', 'pg', 'lf', 'cn', 'ans', 'ag', 'mt', 'end']),
  cheer: new Set(['st', 'ht', 'end']),
};
// the walker set down somewhere (Player.teleport) at these: anywhere (a segment starts again), or this close to the
// point before (the booth's spot, from within reach of its receiver)
const JUMP = { go: Infinity, q: Infinity, lf: PAGER.NEAR + 0.8 };
const MAX_LINES = 30000;
const SPEED = RUN * 1.2, SLACK = 0.45;   // m/s between two points, and m on top (sliding off walls, the frame)
const PACE = RUN * 1.06, PACE_SLACK = 1.2, PACE_T = [2, 5, 10, 20];   // and the way walked over windows this long
const GAP = 0.8;                          // s: the most between two points of a moving segment

class Bad extends Error {}
const bad = (msg) => { throw new Bad(msg); };
const near = (e, p, r) => Math.hypot(e[2] - p.x, e[3] - p.y) <= r;
const r2 = (v) => Math.round(v * 100) / 100;

// the log's shape and the walker's way: no faster than running, no gaps, set down only at a segment's start
function checkWay(log, kinds, moving) {
  if (!Array.isArray(log) || !log.length) bad('기록이 비었어요');
  if (log.length > MAX_LINES) bad('기록이 너무 길어요');
  let prev = null, open = false;
  // the way walked so far in this segment at each line, for the PACE_T windows
  let seg = [], walked = 0;
  const pace = () => {
    for (const w of PACE_T) {
      for (let i = 0, j = 0; i < seg.length; i++) {
        while (j < seg.length && seg[j][0] - seg[i][0] < w) j++;
        if (j >= seg.length) break;
        if (seg[j][1] - seg[i][1] > PACE * (seg[j][0] - seg[i][0]) + PACE_SLACK) bad('뛰는 것보다 빨라요');
      }
    }
  };
  for (const e of log) {
    if (!Array.isArray(e) || e.length < 4 || e.length > 8) bad('기록 형식');
    const [t, k, x, y] = e;
    if (!kinds.has(k)) bad(`모르는 사건 ${k}`);
    if (![t, x, y].every(Number.isFinite) || Math.abs(x) > 3000 || Math.abs(y) > 3000 || t < 0 || t > 7200) bad('기록 값');
    for (let i = 4; i < e.length; i++) if (!Number.isFinite(e[i])) bad('기록 값');
    if (prev && t < prev[0]) bad('시간이 거꾸로');
    if (JUMP[k] === Infinity || (prev && open && moving && JUMP[k] && Math.hypot(x - prev[2], y - prev[3]) <= JUMP[k])) {
      // set down somewhere: a new segment (or close by, a booth's spot: the same one on from there)
      if (moving) { pace(); seg = []; walked = 0; }
      open = true;
    } else if (prev && open && moving) {
      const dt = t - prev[0], d = Math.hypot(x - prev[2], y - prev[3]);
      if (dt > GAP) bad('궤적이 끊겼어요');
      if (d > SPEED * dt + SLACK) bad('뛰는 것보다 빨라요');
      walked += d;
    }
    if (moving && open) seg.push([t, walked]);
    prev = e;
  }
  if (moving) pace();
}
const only = (log, k) => log.filter((e) => e[1] === k);
function one(log, k) {
  const l = only(log, k);
  if (l.length !== 1) bad(`${k} 가 ${l.length}번`);
  return l[0];
}
// the distance from (x, y) to a polyline
function offLine(x, y, pts) {
  let best = Infinity;
  for (let i = 1; i < pts.length; i++) {
    const [ax, ay] = pts[i - 1], [bx, by] = pts[i], dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy;
    const u = L ? clamp(((x - ax) * dx + (y - ay) * dy) / L, 0, 1) : 0;
    best = Math.min(best, Math.hypot(x - ax - u * dx, y - ay - u * dy));
  }
  return best;
}

// ctx: { seed, items (photoquiz.json items), places (places.json, Worker only), today (YYYYMMDD of the server) }.
// The browser has no places: the checks by place are the Worker's.
// returns { value, sort (smaller is better), detail } or throws Bad
const JUDGE = {
  shoot(log) {
    checkWay(log, KINDS.shoot, false);
    const go = one(log, 'go'), end = one(log, 'end');
    const len = end[0] - go[0];
    if (len < SHOOT.TIME - 0.1 || len > SHOOT.TIME + 0.3) bad('경기 시간');
    const shots = only(log, 'sh'), makes = only(log, 'mk');
    let last = -Infinity;
    for (const s of shots) {
      if (s[0] < go[0] || s[0] > end[0]) bad('시간 밖의 슛');
      if (s[0] - last < 0.9) bad('슛 사이가 너무 짧아요');
      last = s[0];
    }
    const used = new Set();
    for (const m of makes) {
      const i = m[4], s = shots[i];
      if (!s || used.has(i)) bad('들어간 슛');
      used.add(i);
      if (m[0] - s[0] < 0.3 || m[0] - s[0] > 4.6) bad('공이 날아간 시간');
    }
    for (const e of log) if (Math.hypot(e[2] - go[2], e[3] - go[3]) > 25) bad('코트 밖');
    const threes = makes.filter((m) => shots[m[4]][4] === 1).length;
    const n = makes.length, pct = shots.length ? n / shots.length : 0;
    return { value: n, sort: -(n * 100000 + Math.round(pct * 10000)), detail: { makes: n, shots: shots.length, threes } };
  },

  race(log, ctx, b) {
    checkWay(log, KINDS.race, true);
    const c = courseOf(b.course), go = one(log, 'go');
    if (log[0] !== go) bad('출발 전의 기록');
    if (!near(go, { x: c.gates[0][0], y: c.gates[0][1] }, 3)) bad('출발선');
    const gates = only(log, 'g');
    if (gates.length !== c.gates.length - 1) bad('문 수');
    gates.forEach((e, i) => {
      const [gx, gy] = c.gates[i + 1];
      if (e[4] !== i + 1 || !near(e, { x: gx, y: gy }, RACE.GATE_R + 0.3)) bad(`${i + 1}번 문`);
    });
    const fin = gates[gates.length - 1];
    if (log[log.length - 1] !== fin) bad('결승 뒤의 기록');
    const line = lineOf(c);
    for (const e of log) if (offLine(e[2], e[3], line) > 28) bad('코스를 벗어났어요');
    const time = fin[0] - go[0];
    return { value: r2(time), sort: Math.round(time * 100), detail: { splits: gates.map((e) => r2(e[0] - go[0])) } };
  },

  photo(log, ctx) {
    checkWay(log, KINDS.photo, true);
    if (!ctx.items) bad('문제 자료가 없어요');
    const round = pickPhotos(ctx.items, rng(ctx.seed));
    const qs = only(log, 'q'), as = only(log, 'a');
    if (qs.length !== round.length || as.length !== round.length) bad('문제 수');
    const starts = ctx.places?.places.filter((p) => !p.north);
    let total = 0, at = 0;
    const items = round.map((q, i) => {
      const s = qs[i], a = as[i];
      if (s[4] !== i || a[4] !== i) bad('문제 순서');
      const si = log.indexOf(s), ai = log.indexOf(a);
      if (si < at || ai < si) bad('문제 순서');
      // between a question's start and its answer, its own way only; nothing else between two questions
      for (let k = si + 1; k < ai; k++) if (log[k][1] !== 'p') bad('문제 사이의 기록');
      if (i + 1 < round.length && log.indexOf(qs[i + 1]) !== ai + 1) bad('문제 사이의 기록');
      at = ai;
      const from = Math.hypot(s[2] - q.x, s[3] - q.y);
      if (from < 39 || from > 175) bad('출발한 곳');
      if (starts && !starts.some((p) => near(s, p, 3))) bad('출발한 곳');
      if (a[0] - s[0] > PHOTO.LIMIT + 0.2) bad('시간 초과 뒤에 찍음');
      const d = Math.hypot(a[2] - q.x, a[3] - q.y), ang = Math.abs(wrap((a[5] - q.bearing) * DEG)) / DEG;
      const sc = photoScore(d, ang);
      total += sc.total;
      return { id: q.id, d: Math.round(d * 10) / 10, a: Math.round(ang), s: sc.total };
    });
    if (log[log.length - 1] !== as[as.length - 1]) bad('마지막 뒤의 기록');
    return { value: total, sort: -total, detail: { items } };
  },

  class(log, ctx, b) {
    checkWay(log, KINDS.class, true);
    if (b.today && ctx.today && Math.abs(dayNum(b.today) - dayNum(ctx.today)) > 1) bad('지난 날의 시간표');
    const set = b.today ? todaySet(b.today) : setOf(b.set);
    const go = one(log, 'go');
    if (log[0] !== go) bad('출발 전의 기록');
    const place = (name) => ctx.places?.places.find((p) => p.name === name);
    const p0 = place(set.classes[0][1]);
    if (ctx.places && (!p0 || !near(go, p0, 9))) bad('첫 건물');
    const ars = only(log, 'ar'), limits = legsOf(set);
    if (ars.length !== set.classes.length - 1) bad('도착 수');
    let t0 = go[0], late = 0;
    const splits = ars.map((e, i) => {
      const hall = set.classes[i + 1][1], p = place(hall);
      if (e[4] !== i + 1) bad('도착 순서');
      if (ctx.places && (!p || !near(e, p, CLASS.DOOR_R + 0.4))) bad(`${hall} 현관`);
      const leg = e[0] - t0, way = wayOf(set.classes[i][1], hall);
      if (leg < (0.85 * way - 15) / RUN) bad(`${hall}까지 너무 빨라요`);
      if (leg > limits[i]) late++;
      t0 = e[0];
      return Math.round(leg * 10) / 10;
    });
    const end = ars[ars.length - 1];
    if (log[log.length - 1] !== end) bad('끝난 뒤의 기록');
    const time = end[0] - go[0];
    return { value: Math.round(time * 10) / 10, sort: late * 1e7 + Math.round(time * 10), detail: { late, splits } };
  },

  bday(log, ctx) {
    checkWay(log, KINDS.bday, true);
    const go = one(log, 'go'), fin = one(log, 'fin');
    if (log[0] !== go) bad('출발 전의 기록');
    if (log[log.length - 1] !== fin) bad('끝난 뒤의 기록');
    const pks = only(log, 'pk');
    if (pks.length !== BDAY.N) bad('친구 수');
    const P = ctx.places;
    if (P) {
      const placeOf = (n) => P.places.find((p) => p.name === n && p.front) || P.places.find((p) => p.name === n);
      const halls = pickHalls((n) => !!placeOf(n), rng(ctx.seed));
      const seen = new Set();
      for (const e of pks) {
        const i = e[4], p = halls[i] && placeOf(halls[i]);
        if (!p || seen.has(i) || !near(e, p, BDAY.NEAR + 0.5)) bad('친구를 만난 곳');
        seen.add(i);
      }
      if (!near(go, P.bday, 6) || !near(fin, P.bday, BDAY.BDAY_NEAR + 0.5)) bad('생일인 친구');
    }
    const time = fin[0] - go[0];
    if (time > BDAY.LIMIT + 0.2) bad('시간 초과');
    return { value: Math.round(time * 10) / 10, sort: Math.round(time * 10), detail: {} };
  },
};
JUDGE.pager = function pager(log, ctx) {
  checkWay(log, KINDS.pager, true);
  const go = one(log, 'go'), end = one(log, 'end');
  if (log[0] !== go || log[log.length - 1] !== end) bad('시작 · 끝');
  const P = ctx.places, booths = P?.booths, starts = P?.places.filter((p) => !p.north);
  const meetRnd = rng(ctx.seed), used = [];
  let score = 0, right = 0, calls = 0, page = null, booth = null, meet = null, n = 0, answered = true;
  for (const e of log) {
    const [t, k, x, y] = e;
    if (k === 'pg') {
      if (page || meet || e[4] !== ++n || n > PAGER.PAGES) bad('삐삐 순서');
      const d = booths ? Math.min(...booths.map(([bx, by]) => Math.hypot(bx - x, by - y))) : 0;
      page = { t, limit: booths ? callLimit(d) : Infinity };
    } else if (k === 'lf') {
      if (!page) bad('삐삐 없이 수화기');
      booth = booths ? booths.find(([bx, by]) => Math.hypot(bx - x, by - y) < 0.3) : [x, y];
      if (!booth) bad('부스가 아닌 곳');
    } else if (k === 'cn') {
      if (!page || !booth || Math.hypot(booth[0] - x, booth[1] - y) > 0.3) bad('연결');
      const left = page.limit - (t - page.t);
      if (left <= 0) bad('시간 초과 뒤에 연결');
      if (booths) score += Math.ceil(left) * 10;
      calls++; page = null; answered = false;
    } else if (k === 'ans') {
      if (answered || !booth) bad('암호 답');
      answered = true;
      if (e[4] === 1) { right++; score += 100; }
    } else if (k === 'ag') {
      if (!booth || page || calls !== n || n >= PAGER.PAGES) bad('만날 곳');
      if (starts) {
        const m = pickMeet(starts, booth[0], booth[1], used, meetRnd);
        meet = { t, m, limit: meetLimit(Math.hypot(m.x - booth[0], m.y - booth[1])) };
      } else meet = { t, m: null, limit: Infinity };
      booth = null;
    } else if (k === 'mt') {
      if (!meet) bad('만남');
      if (meet.m && Math.hypot(meet.m.x - x, meet.m.y - y) > PAGER.MEET_R + 0.3) bad('만날 곳이 아니에요');
      const left = meet.limit - (t - meet.t);
      if (left <= 0) bad('시간 초과 뒤에 만남');
      if (starts) score += Math.ceil(left) * 10;
      meet = null;
    } else if (k === 'end') {
      if (e[4] === 1 && (calls !== PAGER.PAGES || page || meet)) bad('끝');
    }
  }
  if (!booths) score = -1;              // (the browser: the times by place are the Worker's)
  return { value: score, sort: -score, detail: { calls, right } };
};

JUDGE.cheer = function cheer(log, ctx, b) {
  checkWay(log, KINDS.cheer, false);
  const c = chartOf(b.chart), notes = notesOf(c), st = one(log, 'st'), end = one(log, 'end');
  if (log[0] !== st || log[log.length - 1] !== end) bad('시작 · 끝');
  const song = (e) => st[4] + (e[0] - st[0]);         // the song's clock at a line
  if (song(end) < lengthOf(c) + 0.5) bad('노래가 끝나기 전');
  // the hits and, for every sign nobody hit, its miss as the window closes: in the song's order
  const ev = [], hit = new Set();
  for (const e of only(log, 'ht')) {
    const i = e[4], n = notes[i], off = e[5];
    if (!n || hit.has(i) || Math.abs(off) > CHEER_LATE + 1e-6) bad('동작');
    const s = n.t + off;
    if (Math.abs(song(e) - s) > 0.12) bad('동작의 때');
    hit.add(i);
    ev.push({ s, off });
  }
  notes.forEach((n, i) => { if (!hit.has(i)) ev.push({ s: n.t + CHEER_LATE, miss: true }); });
  ev.sort((a, b2) => a.s - b2.s);
  let score = 0, combo = 0, maxCombo = 0;
  const counts = [0, 0, 0, 0];
  for (const x of ev) {
    if (x.miss) { counts[3]++; combo = 0; continue; }
    combo++;
    maxCombo = Math.max(maxCombo, combo);
    const p = cheerPoints(x.off, combo);
    counts[p.j]++;
    score += p.pts;
  }
  const acc = notes.length ? (counts[0] + counts[1] * 0.7 + counts[2] * 0.4) / notes.length : 0;
  return { value: score, sort: -score, detail: { combo: maxCombo, acc: Math.round(acc * 1000) / 1000, counts } };
};

const dayNum = (k) => Date.UTC(+k.slice(0, 4), +k.slice(4, 6) - 1, +k.slice(6, 8)) / 864e5;

export function judge(board, log, ctx = {}) {
  const b = parseBoard(board);
  if (!b) return { error: '모르는 순위표' };
  try {
    return { game: b.game, ...JUDGE[b.game](log, ctx, b) };
  } catch (e) {
    if (e instanceof Bad) return { error: e.message };
    throw e;
  }
}

export { dayKey, COURSES, CHARTS };
