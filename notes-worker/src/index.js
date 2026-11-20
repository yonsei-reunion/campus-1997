// 캠퍼스 쪽지 (web/src/memos.js)의 쓰기 다리. DoltHub 는 브라우저가 토큰을 붙인 요청을 CORS 로 막아서
// (preflight 가 GET 만 허용하고 authorization 헤더를 받지 않음), 쓰기만 이 Worker 가 대신 한다. 읽기는 브라우저가
// DoltHub 에서 바로 한다(공개 DB, 토큰 없이).
//
// 받는 것은 둘뿐이다. SQL 은 여기서 만든다(아무 SQL 이나 넘기지 않음).
//   POST   /         { text, name, color, x, y, z, yaw, kind, place } → { id, created_at }
//   DELETE /<id>                                                     → { ok: true }
// 토큰은 secret DOLT_TOKEN(wrangler secret put DOLT_TOKEN), DB 는 vars DOLT_DB(owner/name).

const API = 'https://www.dolthub.com/api/v1alpha1';
const ORIGINS = [
  /^https:\/\/yonsei-1997\.benelog\.net$/,
  /^https:\/\/yonsei-reunion\.github\.io$/,
  /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/,
];
const COLORS = new Set(['yellow', 'pink', 'mint', 'blue', 'orange']);
const KINDS = new Set(['wall', 'stake']);
const MAX_TEXT = 100, MAX_NAME = 12, MAX_PLACE = 40;
// 한 isolate 안에서만 세는 느슨한 제한: 한 IP 가 1분에 쓰기 8번
const RATE = 8, WINDOW = 60_000;
const hits = new Map();

function cors(origin) {
  const ok = origin && ORIGINS.some((r) => r.test(origin));
  return ok ? {
    'access-control-allow-origin': origin,
    'access-control-allow-methods': 'POST, DELETE, OPTIONS',
    'access-control-allow-headers': 'content-type',
    'access-control-max-age': '86400',
    vary: 'origin',
  } : { vary: 'origin' };
}

const json = (body, status, head) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json; charset=utf-8', ...head } });

// 글: 앞뒤 공백을 떼고, 줄바꿈 말고 제어 문자는 빼고, 빈 줄은 하나까지. 길이는 글자(코드 포인트)로
function clean(s, max, lines = false) {
  if (typeof s !== 'string') return '';
  s = s.normalize('NFC').replace(lines ? /[\u0000-\u0009\u000b-\u001f\u007f]/g : /[\u0000-\u001f\u007f]/g, '');
  if (lines) s = s.replace(/\r/g, '').replace(/\n{3,}/g, '\n\n');
  s = s.trim();
  const cps = [...s];
  return cps.length > max ? null : s;
}

const lit = (s) => `'${s.replace(/\\/g, '\\\\').replace(/'/g, "''")}'`;
const num = (v, lo, hi) => (typeof v === 'number' && Number.isFinite(v) && v >= lo && v <= hi ? v : null);

async function doltJSON(url, init) {
  const res = await fetch(url, init);
  const text = await res.text();
  if (!res.ok) throw new Error(`DoltHub ${res.status}: ${text.slice(0, 160)}`);
  try { return JSON.parse(text); } catch { throw new Error(`DoltHub: ${text.slice(0, 160)}`); }
}

// 한 문장 쓰기: 작업을 걸고, 끝날 때까지 묻는다(보통 1.5 ~ 2초)
async function write(env, stmt) {
  const base = `${API}/${env.DOLT_DB}`, auth = { authorization: `token ${env.DOLT_TOKEN}` };
  const start = await doltJSON(`${base}/write/main/main?q=${encodeURIComponent(stmt)}`, { method: 'POST', headers: auth });
  if (!start.operation_name) throw new Error(start.query_execution_message || 'no operation');
  const until = Date.now() + 20_000;
  for (let wait = 400; Date.now() < until; wait = Math.min(wait * 1.4, 1500)) {
    await new Promise((ok) => setTimeout(ok, wait));
    const r = await doltJSON(`${base}/write?operationName=${encodeURIComponent(start.operation_name)}`, { headers: auth });
    if (r.done) {
      const d = r.res_details || {};
      if (d.query_execution_status && d.query_execution_status !== 'Success') throw new Error(d.query_execution_message || d.query_execution_status);
      return;
    }
  }
  throw new Error('DoltHub 작업이 20초 안에 끝나지 않았어요');
}

function limited(ip) {
  const now = Date.now(), list = (hits.get(ip) || []).filter((t) => now - t < WINDOW);
  if (list.length >= RATE) { hits.set(ip, list); return true; }
  list.push(now);
  hits.set(ip, list);
  if (hits.size > 5000) hits.clear();
  return false;
}

async function add(env, body) {
  const text = clean(body.text, MAX_TEXT, true), name = clean(body.name ?? '', MAX_NAME), place = clean(body.place ?? '', MAX_PLACE);
  if (!text) return [400, { error: text === null ? `쪽지는 ${MAX_TEXT}자까지 쓸 수 있어요` : '빈 쪽지예요' }];
  if (name === null) return [400, { error: `이름은 ${MAX_NAME}자까지예요` }];
  const color = COLORS.has(body.color) ? body.color : 'yellow';
  const kind = KINDS.has(body.kind) ? body.kind : 'wall';
  const x = num(body.x, -3000, 3000), y = num(body.y, -3000, 3000), z = num(body.z, -100, 400), yaw = num(body.yaw, -10, 10);
  if (x === null || y === null || z === null || yaw === null) return [400, { error: '붙일 자리가 이상해요' }];
  const id = crypto.randomUUID().replace(/-/g, '').slice(0, 12);
  const at = new Date().toISOString().slice(0, 19).replace('T', ' ');
  await write(env, 'INSERT INTO notes (id, text, name, color, x, y, z, yaw, kind, place, created_at) VALUES ('
    + [lit(id), lit(text), lit(name), lit(color), x.toFixed(3), y.toFixed(3), z.toFixed(3), yaw.toFixed(4), lit(kind), lit(place || ''), lit(at)].join(', ') + ')');
  return [200, { id, created_at: at }];
}

export default {
  async fetch(req, env) {
    const head = cors(req.headers.get('origin'));
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: head });
    const path = new URL(req.url).pathname.replace(/\/+$/, '');
    try {
      if (req.method === 'POST' && path === '') {
        if (limited(req.headers.get('cf-connecting-ip') || '?')) return json({ error: '잠시 뒤에 다시 붙여 주세요' }, 429, head);
        let body;
        try { body = await req.json(); } catch { return json({ error: '읽을 수 없는 쪽지예요' }, 400, head); }
        const [status, out] = await add(env, body || {});
        return json(out, status, head);
      }
      const m = path.match(/^\/([0-9a-f]{12})$/);
      if (req.method === 'DELETE' && m) {
        if (limited(req.headers.get('cf-connecting-ip') || '?')) return json({ error: '잠시 뒤에 다시 해 주세요' }, 429, head);
        await write(env, `DELETE FROM notes WHERE id = ${lit(m[1])}`);
        return json({ ok: true }, 200, head);
      }
      if (req.method === 'GET' && path === '') return json({ ok: true, db: env.DOLT_DB }, 200, head);
      return json({ error: 'not found' }, 404, head);
    } catch (e) {
      return json({ error: String(e.message || e).slice(0, 200) }, 502, head);
    }
  },
};
