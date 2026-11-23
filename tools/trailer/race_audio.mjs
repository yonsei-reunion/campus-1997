// 달리기 홍보 영상에 깔 게임의 소리: 백양로 직선 주로를 실제로 뛰는 동안의 발소리 · 바람 · 새소리를 녹음한다.
//   node tools/trailer/race_audio.mjs <출력 폴더> [--port 5231] [--secs 40]
// <출력 폴더>/audio/run.wav 를 쓴다. 문 · 출발 · 결승의 신호음은 race_video.py 가 게임과 같은 소리로 합성해
// 영상의 그때(meta.json 의 표시)에 놓으므로, 여기서는 그 신호음을 끈다(Race.sound = null).
// - 소리는 실제 시간으로 흐르므로 프레임 녹화(intro.mjs)와 따로, 작은 창으로 돈다. 프레임 녹화와 함께 돌리지 않는다.
// - 달리는 사람은 페이지 안에서 코스의 선을 따라 돌린다(race_segments.js 의 driver 와 같은 셈).
import { createRequire } from 'module';
import { execFileSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '../..');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
const out = path.join(path.resolve(process.argv[2] && !process.argv[2].startsWith('--') ? process.argv[2] : path.join(os.tmpdir(), 'y97-race')), 'audio');
const port = arg('port', '5231');
const secs = +arg('secs', '40');

function findPlaywright() {
  const tries = [process.env.PLAYWRIGHT, path.join(root, 'web/'), here + '/'].filter(Boolean);
  const npx = path.join(os.homedir(), '.npm/_npx');
  if (fs.existsSync(npx)) for (const d of fs.readdirSync(npx)) tries.push(path.join(npx, d, 'node_modules/'));
  for (const t of tries) {
    try { return createRequire(t.endsWith('/') ? t : t + '/')('playwright'); } catch { /* next */ }
  }
  throw new Error('playwright not found');
}

fs.mkdirSync(out, { recursive: true });
const { chromium } = findPlaywright();
const browser = await chromium.launch({ args: ['--use-angle=vulkan', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'] });
const ctx = await browser.newContext({ viewport: { width: 480, height: 270 }, deviceScaleFactor: 1 });
await ctx.route(/dolthub\.com\/api\/|workers\.dev/, (r) => r.fulfill({ status: 200, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: '{"query_execution_status":"Success","rows":[]}' }));
const page = await ctx.newPage();
page.on('pageerror', (e) => console.log('PAGEERR', e.message));
await page.goto(`http://localhost:${port}/`);
await page.waitForFunction(() => window.__y97 && window.__y97.birthday && !document.querySelector('#start')?.disabled, null, { timeout: 300000 });
await page.evaluate(async () => {
  localStorage.setItem('y97-season', 'autumn');
  document.querySelector('#news .close')?.click();
  document.querySelector('#start').click();
});
await page.waitForFunction(() => document.querySelector('#intro').hidden, null, { timeout: 120000 });
await page.evaluate(async () => {
  const y = window.__y97, R = await y.loadRace();
  await R.start('baekyang');
  R.sound = null;                                  // (신호음은 race_video.py 가 영상의 그때에)
  const pl = y.player;
  window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyW', key: 'w' }));
  let s = 0;
  setInterval(() => {
    if (R.state !== 'play') return;
    const { pts, at } = R.line;
    let best = Infinity;
    for (let i = 1; i < pts.length && at[i - 1] < s + 40; i++) {
      if (at[i] < s - 10) continue;
      const [ax, ay] = pts[i - 1], [bx, by] = pts[i], dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy || 1;
      const u = Math.min(1, Math.max(0, ((pl.x - ax) * dx + (pl.y - ay) * dy) / l2)), qx = ax + dx * u - pl.x, qy = ay + dy * u - pl.y, e = qx * qx + qy * qy;
      if (e < best) { best = e; s = at[i - 1] + u * Math.sqrt(l2); }
    }
    const p = R.pointAt(s + 5);
    pl.heading = Math.atan2(p.x - pl.x, -(p.y - pl.y));
    pl.cam.orbit = 0;
  }, 50);
});
await page.waitForFunction(() => window.__y97.race.state === 'play', null, { timeout: 60000 });
const state = await page.evaluate(async () => {
  const s = window.__y97.sound;
  s.start?.();
  for (let i = 0; i < 100 && !(s.ctx && s.ctx.state === 'running'); i++) { await s.ctx?.resume?.(); await new Promise((r) => setTimeout(r, 100)); }
  const d = s.ctx.createMediaStreamDestination();
  s.tap.connect(d);
  const mr = new MediaRecorder(d.stream, { mimeType: 'audio/webm;codecs=opus', audioBitsPerSecond: 256000 });
  const parts = [];
  mr.ondataavailable = (e) => parts.push(e.data);
  mr.start(500);
  window.__rec = { mr, parts, d };
  return s.ctx.state + ' ' + s.ctx.sampleRate;
});
console.log('run:', state);
await page.waitForTimeout(secs * 1000);
const b64 = await page.evaluate(async () => {
  const { mr, parts, d } = window.__rec;
  await new Promise((r) => { mr.onstop = r; mr.stop(); });
  window.__y97.sound.tap.disconnect(d);
  const buf = new Uint8Array(await new Blob(parts).arrayBuffer());
  let s = '';
  for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode(...buf.subarray(i, i + 0x8000));
  return btoa(s);
});
console.log('ran to', await page.evaluate(() => { const R = window.__y97.race; return `${R.state} gate ${R.next}`; }));
const webm = path.join(out, 'run.webm');
fs.writeFileSync(webm, Buffer.from(b64, 'base64'));
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', webm, '-ar', '48000', '-ac', '2', path.join(out, 'run.wav')]);
fs.rmSync(webm);
console.log('run.wav', (fs.statSync(path.join(out, 'run.wav')).size / 1e6).toFixed(1), 'MB');
await browser.close();
