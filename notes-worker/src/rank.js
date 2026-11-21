// 미니 게임 전체 순위(web/src/rank.js)의 쓰기 다리. 점수를 그대로 받지 않는다:
//
//   POST /rank/start  { board }                        → { ticket, seed, pub }
//     판 열쇠(ticket): 판 번호(sid) · 순위표 · 서버 시각 · 씨앗(seed)을 HMAC 으로 서명한 것. 씨앗이 그 판이 내는 문제
//     (사진 · 친구가 선 건물)를 정해, 쉬운 판을 골라 올 수 없다. pub 은 기록을 봉할 서버의 ECDH 공개 키.
//   POST /rank/beat   { ticket, k, n, g, h, f }        → { ts, r }
//     심장 박동: 판의 시계 g 에서 기록의 앞 n 줄의 해시 사슬 h 를 맡기고, 서버 시각 ts 를 적은 영수증 r(HMAC)을 받는다.
//     f: 0 그냥 · 1 멈춤 · 2 다시 · 3 끝. 서버는 아무것도 저장하지 않는다(영수증이 곧 기록).
//   POST /rank/submit { e, iv, c }                     → { rank, top } | { rank: null, cut }
//     봉한 기록: 브라우저의 일회용 ECDH 키(e)와 서버 키로 맞춘 AES-GCM 키로 암호화한 { ticket, name, hero, beats, log }.
//
// 검사(제출 때):
//   1. 판 열쇠의 서명 · 나이(3시간) · 순위표, 판 번호는 한 번만(scores.sid 가 기본 키)
//   2. 영수증마다 서명, 박동 번호가 1부터 빠짐없이, 해시 사슬이 보낸 기록의 앞부분과 같음
//      → 기록은 판을 하는 동안 조금씩 맡겨진 것이라, 다 끝난 뒤 지어낸 기록을 한 번에 낼 수 없다
//   3. 판의 시계가 서버 시계보다 빨리 가지 않음(g ≤ 열쇠를 받은 뒤 흐른 시간 + 1 s), 멈추지 않은 동안 반보다
//      느리지도 않음(느린 화면으로 시간을 버는 것), 박동 사이가 12.5 s 를 넘지 않음
//   4. web/src/rankrules.js 의 judge: 궤적이 뛰는 것보다 빠르지 않고, 사건이 그 자리 · 순서에서 일어났고, 점수는
//      기록에서 서버가 다시 셈
// 그다음 그 순위표의 30위와 견주어 들면 넣고, 31위부터는 지운다.
import { judge, parseBoard, TOP, NAME_MAX } from '../../web/src/rankrules.js';
import photoquiz from '../../web/public/data/photoquiz.json';
import places from './places.json';

const API = 'https://www.dolthub.com/api/v1alpha1';
const TICKET_AGE = 3 * 3600_000;
const AAD = new TextEncoder().encode('y97-rank-v1');
const enc = new TextEncoder(), dec = new TextDecoder();

const b64 = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const unb64 = (s) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/')), (c) => c.charCodeAt(0));
const hex = (buf) => [...new Uint8Array(buf)].map((x) => x.toString(16).padStart(2, '0')).join('');
const sha = async (s) => hex(await crypto.subtle.digest('SHA-256', enc.encode(s)));

// ---------------------------------------------------------------- keys (secret RANK_KEY: the P-256 private JWK)
let keys = null;
async function keysOf(env) {
  if (keys?.src === env.RANK_KEY) return keys;
  if (!env.RANK_KEY) throw new Error('RANK_KEY 가 없어요');
  const jwk = JSON.parse(env.RANK_KEY);
  const priv = await crypto.subtle.importKey('jwk', jwk, { name: 'ECDH', namedCurve: 'P-256' }, false, ['deriveBits']);
  const pubKey = await crypto.subtle.importKey('jwk', { kty: jwk.kty, crv: jwk.crv, x: jwk.x, y: jwk.y }, { name: 'ECDH', namedCurve: 'P-256' }, true, []);
  const pub = b64(await crypto.subtle.exportKey('raw', pubKey));
  const mac = await crypto.subtle.importKey('raw', enc.encode(`ticket|${jwk.d}`), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign', 'verify']);
  keys = { src: env.RANK_KEY, priv, pub, mac };
  return keys;
}
const sign = async (k, s) => b64(await crypto.subtle.sign('HMAC', k.mac, enc.encode(s)));
const verify = async (k, s, sig) => {
  try { return await crypto.subtle.verify('HMAC', k.mac, unb64(sig), enc.encode(s)); } catch { return false; }
};

async function readTicket(k, ticket) {
  if (typeof ticket !== 'string' || ticket.length > 400) return null;
  const [body, sig] = ticket.split('.');
  if (!body || !sig || !(await verify(k, body, sig))) return null;
  let t;
  try { t = JSON.parse(dec.decode(unb64(body))); } catch { return null; }
  if (t.v !== 1 || Date.now() - t.t0 > TICKET_AGE) return null;
  return t;
}

// ---------------------------------------------------------------- DoltHub
const lit = (s) => `'${String(s).replace(/\\/g, '\\\\').replace(/'/g, "''")}'`;
async function doltJSON(url, init) {
  const res = await fetch(url, init);
  const text = await res.text();
  if (!res.ok) throw new Error(`DoltHub ${res.status}: ${text.slice(0, 160)}`);
  try { return JSON.parse(text); } catch { throw new Error(`DoltHub: ${text.slice(0, 160)}`); }
}
async function read(env, q) {
  const r = await doltJSON(`${API}/${env.DOLT_DB}/main?q=${encodeURIComponent(q)}`);
  if (r.query_execution_status !== 'Success' && r.query_execution_status !== 'RowLimit') throw new Error(r.query_execution_message || 'DoltHub 읽기');
  return r.rows || [];
}
const topQuery = (board) => `SELECT sid, name, sort, value, detail, hero, created_at FROM scores WHERE board = ${lit(board)} ORDER BY sort, created_at LIMIT ${TOP}`;

// ---------------------------------------------------------------- the clean name (as the notes' clean)
function cleanName(s) {
  if (typeof s !== 'string') return null;
  s = s.normalize('NFC').replace(/[\u0000-\u001f\u007f\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff]/g, '').replace(/\s+/g, ' ').trim();
  const n = [...s].length;
  return n >= 1 && n <= NAME_MAX ? s : null;
}

// ---------------------------------------------------------------- the routes
export async function start(env, body) {
  const b = parseBoard(body?.board);
  if (!b) return [400, { error: '모르는 순위표예요' }];
  const k = await keysOf(env);
  const rnd = crypto.getRandomValues(new Uint8Array(16));
  const t = { v: 1, sid: hex(rnd.slice(0, 12)), b: body.board, t0: Date.now(), seed: hex(rnd.slice(12)) };
  const bodyS = b64(enc.encode(JSON.stringify(t)));
  return [200, { ticket: `${bodyS}.${await sign(k, bodyS)}`, seed: t.seed, pub: k.pub }];
}

const beatText = (sid, x) => `beat|${sid}|${x.k}|${x.n}|${x.g}|${x.h}|${x.f}|${x.ts}`;

export async function beat(env, body) {
  const k = await keysOf(env);
  const t = await readTicket(k, body?.ticket);
  if (!t) return [400, { error: '판 열쇠가 맞지 않아요' }];
  const { k: kk, n, g, h, f } = body;
  if (!Number.isInteger(kk) || kk < 1 || kk > 2000 || !Number.isInteger(n) || n < 0 || !Number.isFinite(g) || g < 0
    || typeof h !== 'string' || !/^[0-9a-f]{64}$/.test(h) || ![0, 1, 2, 3].includes(f)) return [400, { error: '박동 형식' }];
  const x = { k: kk, n, g, h, f, ts: Date.now() };
  return [200, { ts: x.ts, r: await sign(k, beatText(t.sid, x)) }];
}

async function unseal(k, body) {
  const { e, iv, c } = body || {};
  if (typeof e !== 'string' || typeof iv !== 'string' || typeof c !== 'string' || c.length > 1_500_000) throw new Error('봉투 형식');
  const epub = unb64(e);
  const their = await crypto.subtle.importKey('raw', epub, { name: 'ECDH', namedCurve: 'P-256' }, false, []);
  const bits = await crypto.subtle.deriveBits({ name: 'ECDH', public: their }, k.priv, 256);
  const hk = await crypto.subtle.importKey('raw', bits, 'HKDF', false, ['deriveKey']);
  const aes = await crypto.subtle.deriveKey({ name: 'HKDF', hash: 'SHA-256', salt: epub, info: AAD }, hk, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
  const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(iv), additionalData: AAD }, aes, unb64(c));
  return JSON.parse(dec.decode(plain));
}

// the receipts against the log (see the top)
async function checkBeats(k, t, beats, log) {
  if (!Array.isArray(beats) || !beats.length || beats.length > 2000) return '심장 박동이 없어요';
  let h = await sha(t.sid), prev = { n: 0, g: 0, ts: t.t0, f: 0 }, run = 0, real = 0;
  for (let i = 0; i < beats.length; i++) {
    const x = beats[i];
    if (!x || x.k !== i + 1) return '박동 번호';
    if (!(await verify(k, beatText(t.sid, x), x.r))) return '영수증이 맞지 않아요';
    if (x.n < prev.n || x.n > log.length || x.g < prev.g || x.ts < prev.ts) return '박동 순서';
    h = await sha(`${h}|${JSON.stringify(log.slice(prev.n, x.n))}`);
    if (h !== x.h) return '기록이 맡긴 것과 달라요';
    if (x.n && log[x.n - 1][0] > x.g + 0.001) return '맡기기 전의 기록이 아니에요';
    if (x.g > (x.ts - t.t0) / 1000 + 1) return '판의 시계가 빨라요';
    const dg = x.g - prev.g, ds = (x.ts - prev.ts) / 1000;
    if (dg > 12.5) return '박동 사이가 길어요';
    if (prev.f === 1) { if (dg > 0.3) return '멈춘 동안 시계가 갔어요'; } else { run += dg; real += ds; }
    prev = x;
  }
  if (prev.f !== 3 || prev.n !== log.length) return '끝 박동이 없어요';
  if (run < 0.5 * real - 5) return '판의 시계가 너무 느려요';
  return null;
}

export async function submit(env, body, ctx) {
  const k = await keysOf(env);
  let p;
  try { p = await unseal(k, body); } catch { return [400, { error: '기록을 열 수 없어요' }]; }
  const t = await readTicket(k, p.ticket);
  if (!t) return [400, { error: '판 열쇠가 맞지 않거나 너무 오래됐어요' }];
  const name = cleanName(p.name);
  if (!name) return [400, { error: `이름은 1 ~ ${NAME_MAX}자로 적어 주세요` }];
  const log = p.log;
  if (!Array.isArray(log)) return [400, { error: '기록이 없어요' }];
  const why = await checkBeats(k, t, p.beats, log);
  if (why) return [422, { error: `순위에 올릴 수 없는 판이에요 (${why})` }];
  const now = new Date();
  const today = now.toISOString().slice(0, 10).replace(/-/g, '');
  const res = judge(t.b, log, { seed: t.seed, items: photoquiz.items, places, today });
  if (res.error) return [422, { error: `순위에 올릴 수 없는 판이에요 (${res.error})` }];
  // where it comes among the board's 30 (ties: the earlier first)
  const top = await read(env, topQuery(t.b));
  if (top.some((r) => r.sid === t.sid)) return [409, { error: '이미 올린 판이에요' }];
  const at = now.toISOString().slice(0, 19).replace('T', ' ');
  const rank = 1 + top.filter((r) => +r.sort <= res.sort).length;
  if (rank > TOP) return [200, { rank: null, cut: top[TOP - 1] ? +top[TOP - 1].value : null, value: res.value }];
  const hero = typeof p.hero === 'string' && /^p\d{2}$/.test(p.hero) ? p.hero : '';
  const detail = JSON.stringify(res.detail).slice(0, 2000);
  await env.write(`INSERT INTO scores (sid, game, board, name, sort, value, detail, hero, created_at) VALUES (${[
    lit(t.sid), lit(res.game), lit(t.b), lit(name), String(res.sort), String(res.value), lit(detail), lit(hero), lit(at)].join(', ')})`);
  // the 31st and on go (after the answer)
  if (top.length >= TOP) {
    ctx.waitUntil(env.write(`DELETE FROM scores WHERE board = ${lit(t.b)} AND sid NOT IN (SELECT sid FROM (SELECT sid FROM scores WHERE board = ${lit(t.b)} ORDER BY sort, created_at LIMIT ${TOP}) AS keep)`).catch(() => {}));
  }
  const mine = { sid: t.sid, name, sort: res.sort, value: res.value, detail, hero, created_at: at };
  const list = [...top.slice(0, rank - 1), mine, ...top.slice(rank - 1)].slice(0, TOP);
  return [200, { rank, sid: t.sid, value: res.value, top: list }];
}
