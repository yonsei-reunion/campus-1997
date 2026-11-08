// README · 문집에 쓰는 게임 화면을 다시 찍는다. 카메라와 저장할 곳은 tools/snapshots.json 한 곳에 있다.
//   cd web && npx vite --port 5197          (다른 터미널, 아무 포트)
//   node tools/snapshots.mjs [--port 5197] [--only 이름,이름] [--raw <폴더>] [--no-compose] [--query ?touch] [--spec <json>]
// 찍은 PNG 는 --raw 폴더(기본: 임시 폴더/y97-snapshots)에 두고, 끝에 tools/snapshots_compose.py 가 줄이고 붙여서
// json 의 out 경로(README 의 docs/…, 이웃 저장소 ../yonsei-anthology/… 등)에 JPEG 로 쓴다.
// --only 는 shot 이름이나 이름의 앞부분(compare/ 처럼)을 쉼표로. grid 는 고른 shot 이 들어 있으면 다시 붙인다.
// --spec: 후보 카메라를 시험할 임시 json(같은 형식, out 을 빼면 PNG 만 남음). 기본은 tools/snapshots.json.
// Playwright 의 Chromium 이 필요하다(tools/bake_sun_shadows.mjs 와 같은 방법으로 찾음).
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '..');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
const port = arg('port', '5197');
const only = arg('only', '');
const raw = path.resolve(arg('raw', path.join(os.tmpdir(), 'y97-snapshots')));
const query = arg('query', '');
const compose = !process.argv.includes('--no-compose');
const specPath = path.resolve(arg('spec', path.join(here, 'snapshots.json')));

function findPlaywright() {
  const tries = [process.env.PLAYWRIGHT, path.join(root, 'web/'), here + '/'].filter(Boolean);
  const npx = path.join(os.homedir(), '.npm/_npx');
  if (fs.existsSync(npx)) for (const d of fs.readdirSync(npx)) tries.push(path.join(npx, d, 'node_modules/'));
  for (const t of tries) {
    try { return createRequire(t.endsWith('/') ? t : t + '/')('playwright'); } catch { /* next */ }
  }
  throw new Error('playwright not found: npx playwright install chromium, or set PLAYWRIGHT=<dir>');
}

const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
const picked = (n) => !only || only.split(',').some((p) => n === p || n.startsWith(p));
const shots = spec.shots.filter((s) => !s.grid && picked(s.name));
fs.mkdirSync(raw, { recursive: true });

const { chromium } = findPlaywright();
const browser = await chromium.launch({ args: ['--use-angle=vulkan', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
const errs = [];

// one page per mode: bird shots hide the UI and fly a fixed camera; walk shots keep the UI and place the walker
async function openPage(mode) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().replace(/\0/g, '').slice(0, 300)); });
  page.on('pageerror', (e) => errs.push('PAGEERR ' + e.message));
  await page.goto(`http://localhost:${port}/${query}`);
  await page.waitForFunction(() => window.__y97 && window.__y97.bird && !document.querySelector('#start')?.disabled, null, { timeout: 300000 });
  await page.waitForTimeout(5000);
  await page.evaluate((mode) => {
    const y = window.__y97;
    if (mode === 'walk') y.startWalk();
    else { y.enterBird(); y.bird.auto = false; }
  }, mode);
  await page.waitForTimeout(2000);
  return page;
}

const pages = {};
const state = {};
for (const s of shots) {
  const mode = s.walk ? 'walk' : 'bird';
  const page = pages[mode] ??= await openPage(mode);
  const st = state[mode] ??= { season: null, film: false, ui: true };
  await page.setViewportSize({ width: s.size[0], height: s.size[1] });
  const season = s.season || 'summer';
  if (season !== st.season) { await page.evaluate((v) => window.__y97.setSeason(v), season); st.season = season; await page.waitForTimeout(2500); }
  const film = !!s.film;
  if (film !== st.film) {
    await page.evaluate((v) => { const e = document.querySelector('#opt-film'); e.checked = v; e.dispatchEvent(new Event('change')); }, film);
    st.film = film;
  }
  const ui = s.ui ?? (mode === 'walk');
  if (ui !== st.ui) {
    await page.evaluate((show) => {
      const keep = new Set();
      for (let n = window.__y97.renderer.domElement; n; n = n.parentElement) keep.add(n);
      document.querySelectorAll('body *').forEach((e) => { if (!keep.has(e)) e.style.visibility = show ? '' : 'hidden'; });
    }, ui);
    st.ui = ui;
  }
  if (mode === 'bird') {
    await page.evaluate((c) => {
      const Y = window.__y97, B = Y.bird, hf = Y.player.hf;
      const h = c.h ?? hf.height(c.x, c.y) + (c.dh ?? 1.7);
      const th = c.th ?? hf.height(c.tx, c.ty) + (c.tdh ?? 5);
      B.fixed = { x: c.x, y: c.y, h, tx: c.tx, ty: c.ty, th };
      const fov = c.fov || 50; B.fovGoal = fov; Y.camera.fov = fov; Y.camera.updateProjectionMatrix();
    }, s.cam);
  } else {
    await page.evaluate((w) => {
      const p = window.__y97.player;
      p.teleport(w.x, w.y, w.yaw);
      p.cam.dist = w.dist ?? 5.4; p.cam.lift = w.lift ?? 0; p.cam.orbit = w.orbit ?? 0; p.cam.ready = false;
    }, s.walk);
  }
  if (s.eval) await page.evaluate(s.eval);
  await page.waitForTimeout(s.wait ?? 4000);
  for (const k of s.keys || []) { await page.keyboard.press(k); await page.waitForTimeout(s.keyWait ?? 1500); }
  if (s.post) { await page.evaluate(s.post); await page.waitForTimeout(s.postWait ?? 3000); }
  const file = path.join(raw, s.name.replace(/\//g, '__') + '.png');
  await page.screenshot({ path: file });
  for (const k of s.keysAfter || []) { await page.keyboard.press(k); await page.waitForTimeout(500); }
  console.log('shot', s.name);
}
for (const page of Object.values(pages)) {
  const bad = await page.evaluate(() => window.__y97.renderer.info.programs.filter((p) => p.diagnostics).length);
  if (bad) console.log('failed shader programs:', bad);
}
const shown = errs.filter((e) => !/403|font/i.test(e));
if (shown.length) console.log('console errors:\n' + shown.slice(0, 10).join('\n'));
await browser.close();

if (compose) {
  const py = fs.existsSync(path.join(root, '.venv/bin/python')) ? path.join(root, '.venv/bin/python') : 'python3';
  execFileSync(py, [path.join(here, 'snapshots_compose.py'), raw, only, specPath], { stdio: 'inherit', cwd: root });
}
