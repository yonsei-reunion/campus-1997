// 소개 영상의 게임 장면을 프레임으로 찍는다 (장면의 내용: tools/trailer/intro_segments.js, 순서 · 길이: intro_video.py).
//   cd web && npx vite build --outDir <작업 폴더>/dist --emptyOutDir && npx vite preview --outDir <작업 폴더>/dist --port 5231
//   node tools/trailer/intro.mjs <출력 폴더> [--seg fly,heroes] [--port 5231] [--every 15] [--cdp 9333]
// <출력 폴더>/<장면>/%05d.jpg (1920 × 1080, 30 fps) 와 <장면>/meta.json 을 쓴다. 이어서
//   python3 tools/trailer/intro_video.py <출력 폴더> trailer/intro.mp4
// - 빌드한 사본을 vite preview 로 띄워 찍는다. 개발 서버(vite)는 다른 세션이 web/ 을 고치면 페이지를 다시 불러
//   찍던 장면이 끊긴다.
// - 장면마다 페이지를 새로 불러온다(앞 장면의 주인공 · 계절 · 미니 게임이 남지 않게).
// - --every N: N 프레임마다 한 장만 저장(구도 확인용, 게임은 모든 프레임을 진행).
// - --cdp <포트>: 이미 떠 있는 Chromium(--remote-debugging-port)에 붙는다. 장면을 고치며 볼 때 빠르다.
// - 쪽지는 실제 서버(DoltHub · Worker)에 닿지 않게 가로채서 녹화용 쪽지만 보인다(intro_segments.js MEMOS).
// 게임 페이지 하나가 메모리 3 GB쯤을 쓰니 한 번에 하나만 돌린다.
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '../..');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
const out = path.resolve(process.argv[2] && !process.argv[2].startsWith('--') ? process.argv[2] : path.join(os.tmpdir(), 'y97-intro'));
const port = arg('port', '5231');
const every = +arg('every', '1');
const cdp = arg('cdp', '');
const segArg = JSON.parse(arg('arg', 'null'));          // 장면의 init 에 넘기는 값(시험용: 예 --arg '{"only":["p10"]}')
const W = 1920, H = 1080, FPS = 30;
// 게임의 창 · 안내 버튼 · 말풍선(DOM)이 영상에서 읽히게 CSS 화면은 1280 × 720, 기기 화소 비 1.5 로 찍는다
const DPR = 1.5;

function findPlaywright() {
  const tries = [process.env.PLAYWRIGHT, path.join(root, 'web/'), here + '/'].filter(Boolean);
  const npx = path.join(os.homedir(), '.npm/_npx');
  if (fs.existsSync(npx)) for (const d of fs.readdirSync(npx)) tries.push(path.join(npx, d, 'node_modules/'));
  for (const t of tries) {
    try { return createRequire(t.endsWith('/') ? t : t + '/')('playwright'); } catch { /* next */ }
  }
  throw new Error('playwright not found: npx playwright install chromium, or set PLAYWRIGHT=<dir>');
}

const { chromium } = findPlaywright();
const errs = [];
let browser, ctx, page;
// 브라우저 · 페이지를 띄움. 찍다가 페이지가 죽으면(GPU 프로세스가 가끔 죽는다) 닫고 다시 띄워 그 장면을 처음부터 찍는다
let memos = [];
const open = async () => {
  browser = cdp ? await chromium.connectOverCDP(`http://127.0.0.1:${cdp}`)
    : await chromium.launch({ args: ['--use-angle=vulkan', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  ctx = await browser.newContext({ viewport: { width: W / DPR, height: H / DPR }, deviceScaleFactor: DPR });
  page = await ctx.newPage();
  page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().replace(/\0/g, '').slice(0, 300)); });
  page.on('pageerror', (e) => errs.push('PAGEERR ' + e.message));
  page.on('crash', () => console.log('page crashed'));
  // 쪽지: 읽기(DoltHub SQL API)와 쓰기(Worker)를 가로챈다. 녹화용 쪽지는 페이지의 window.__ivMemos 에서 읽는다
  await ctx.route(/dolthub\.com\/api\/.*yonsei-1997/, async (route) => {
    const q = decodeURIComponent(new URL(route.request().url()).searchParams.get('q') || '');
    const rows = /from\s+notes/i.test(q) ? memos : [];
    await route.fulfill({ status: 200, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' },
      body: JSON.stringify({ query_execution_status: 'Success', query_execution_message: '', rows }) });
  });
  await ctx.route(/y97-notes\.[a-z0-9-]+\.workers\.dev/, async (route) => {
    const req = route.request();
    const cors = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*' };
    if (req.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: cors });
    let body = {};
    try { body = JSON.parse(req.postData() || '{}'); } catch { /* none */ }
    if (req.method() === 'POST' && new URL(req.url()).pathname === '/') {
      const note = { ...body, id: 'a1b2c3d4e5f6', created_at: new Date().toISOString().slice(0, 19).replace('T', ' ') };
      memos = [note, ...memos];
      return route.fulfill({ status: 200, contentType: 'application/json', headers: cors, body: JSON.stringify({ id: note.id, created_at: note.created_at }) });
    }
    return route.fulfill({ status: 200, contentType: 'application/json', headers: cors, body: JSON.stringify({ ok: true, rows: [], scores: [] }) });
  });
};
const close = async () => {
  try { await ctx.close(); } catch { /* gone */ }
  if (!cdp) { try { await browser.close(); } catch { /* gone */ } }
};

const load = async (query = '') => {
  await page.goto(`http://localhost:${port}/${query}`);
  await page.waitForFunction(() => window.__y97 && window.__y97.birthday && !document.querySelector('#start')?.disabled, null, { timeout: 300000 });
  await page.evaluate(() => Promise.all([document.fonts.load('40px "Do Hyeon"'), document.fonts.load('700 40px "Noto Sans KR"'), document.fonts.load('500 40px "Noto Sans KR"')]));
  await page.addScriptTag({ path: path.join(here, 'intro_page.js') });
  await page.addScriptTag({ path: path.join(here, 'intro_segments.js') });
};

await open();
await load();
const all = await page.evaluate(() => Object.keys(window.__iv.seg));
const names = arg('seg', '') ? arg('seg', '').split(',') : all;
const shoot = async (name) => {
  const t0 = Date.now();
  const query = await page.evaluate((n) => window.__iv.seg[n].query || '', name);
  await load(query);
  const dir = path.join(out, name);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  // 장면이 쓰는 저장소의 사진(사진과 게임의 대비): data URL 로 넘긴다
  const files = await page.evaluate((nm) => window.__iv.seg[nm].files || null, name);
  if (files) {
    const data = {};
    for (const [k, f] of Object.entries(files)) data[k] = `data:image/${/\.png$/i.test(f) ? 'png' : 'jpeg'};base64,` + fs.readFileSync(path.join(root, f)).toString('base64');
    await page.evaluate(([nm, d]) => { window.__iv.seg[nm].data = d; }, [name, data]);
  }
  const n = await page.evaluate(([nm, a]) => window.__iv.init(nm, a), [name, segArg]);
  memos = await page.evaluate(() => window.__ivMemos || []);
  let i = 0, saved = 0;
  const marks = [];
  for (;; i++) {
    const r = await page.evaluate(([nm, k]) => window.__iv.frame(nm, k), [name, i]);
    if (r?.mark) marks.push({ frame: i, t: i / FPS, mark: r.mark });
    if (i % every === 0) { await page.screenshot({ path: path.join(dir, String(every === 1 ? i : saved).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 93 }); saved++; }
    if (i % 90 === 0) console.log(`${name} frame ${i}${n ? ' / ' + n : ''}${r?.note ? '  ' + r.note : ''}`);
    if (r?.done || (n && i >= n - 1) || i > 120 * FPS) break;
  }
  fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify({ fps: FPS, frames: i + 1, every, marks }, null, 1));
  console.log(`${name}: ${i + 1} frames (${saved} saved) in ${((Date.now() - t0) / 1000).toFixed(0)} s -> ${dir}`);
  if (marks.length) console.log(marks.map((m) => `  ${m.t.toFixed(2)} ${m.mark}`).join('\n'));
};
const failed = [];
for (const name of names) {
  if (!all.includes(name)) { console.log(`no segment ${name} (have: ${all.join(' ')})`); continue; }
  let ok = false;
  for (let attempt = 1; attempt <= 4 && !ok; attempt++) {
    try { await shoot(name); ok = true; } catch (e) {
      console.log(`${name}: attempt ${attempt} failed (${String(e.message).split('\n')[0]}), reopening`);
      await close();
      await new Promise((r) => setTimeout(r, 3000));
      await open();
      await load();
    }
  }
  if (!ok) failed.push(name);
}
if (errs.length) console.log('errors:\n' + [...new Set(errs)].slice(0, 12).join('\n'));
if (failed.length) console.log('FAILED: ' + failed.join(' '));
await close();
process.exit(failed.length ? 1 : 0);
