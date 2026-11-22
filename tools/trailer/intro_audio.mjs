// 소개 영상에 깔 게임의 소리를 받는다: 게임이 브라우저에서 합성하는 소리(web/src/audio.js)를 그대로 녹음한다.
//   node tools/trailer/intro_audio.mjs <출력 폴더> [--port 5231] [--only cheer,walk,fountain]
// <출력 폴더>/audio/cheer.wav (연고전 응원 연습: 아카라카 구호와 응원가, 자동 연주), walk.wav (백양로의 바람 · 새소리),
// fountain.wav (활천대 분수 곁)를 쓴다. intro_video.py 가 영상의 구간에 맞춰 섞는다.
// - 소리는 실제 시간으로 흐르므로 프레임 녹화(intro.mjs)와 따로, 작은 창(그리는 일이 가벼워 박자가 밀리지 않게)으로 돈다.
// - Sound 의 끝(리미터 뒤의 tap)을 MediaStream 으로 받아 MediaRecorder 로 녹음하고, ffmpeg 로 WAV(48 kHz)로 바꾼다.
import { createRequire } from 'module';
import { execFileSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '../..');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
const out = path.join(path.resolve(process.argv[2] && !process.argv[2].startsWith('--') ? process.argv[2] : path.join(os.tmpdir(), 'y97-intro')), 'audio');
const port = arg('port', '5231');
const only = arg('only', 'cheer,walk,fountain').split(',');

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
// (순위 · 쪽지 서버에는 닿지 않게)
await ctx.route(/dolthub\.com\/api\/|workers\.dev/, (r) => r.fulfill({ status: 200, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: '{"query_execution_status":"Success","rows":[]}' }));
const page = await ctx.newPage();
page.on('pageerror', (e) => console.log('PAGEERR', e.message));

const load = async () => {
  await page.goto(`http://localhost:${port}/`);
  await page.waitForFunction(() => window.__y97 && window.__y97.birthday && !document.querySelector('#start')?.disabled, null, { timeout: 300000 });
  await page.evaluate(() => { localStorage.setItem('y97-season', 'summer'); document.querySelector('#news .close')?.click(); });
};
// 녹음을 시작 · 끝(끝에서 webm 을 base64 로 돌려줌)
const recStart = () => page.evaluate(async () => {
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
const recStop = async (name) => {
  const b64 = await page.evaluate(async () => {
    const { mr, parts, d } = window.__rec;
    await new Promise((r) => { mr.onstop = r; mr.stop(); });
    window.__y97.sound.tap.disconnect(d);
    const buf = new Uint8Array(await new Blob(parts).arrayBuffer());
    let s = '';
    for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode(...buf.subarray(i, i + 0x8000));
    return btoa(s);
  });
  const webm = path.join(out, name + '.webm');
  fs.writeFileSync(webm, Buffer.from(b64, 'base64'));
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', webm, '-ar', '48000', '-ac', '2', path.join(out, name + '.wav')]);
  fs.rmSync(webm);
  console.log(name + '.wav', (fs.statSync(path.join(out, name + '.wav')).size / 1e6).toFixed(1), 'MB');
};

if (only.includes('cheer')) {
  await load();
  // 응원 연습 「보통」(100 BPM: 학교 음원의 빠르기)을 자동 연주로
  await page.evaluate(() => document.querySelector('#cheer-start').click());
  await page.waitForFunction(() => { const e = document.querySelector('#cheerpick'); return e && !e.hidden; }, null, { timeout: 60000 });
  console.log('cheer:', await recStart());
  await page.evaluate(() => { document.querySelectorAll('#cheerpick button')[1].click(); });
  await page.waitForFunction(() => window.__y97.cheer?.state === 'count' || window.__y97.cheer?.state === 'play', null, { timeout: 60000 });
  await page.evaluate(() => { window.__y97.cheer.auto = true; });
  await page.waitForFunction(() => window.__y97.cheer.state === 'done' || window.__y97.cheer.state === 'off', null, { timeout: 180000, polling: 500 });
  await page.waitForTimeout(1500);
  await recStop('cheer');
}
for (const [name, place, secs] of [['walk', '백양로', 45], ['fountain', '활천대', 25]]) {
  if (!only.includes(name)) continue;
  await load();
  await page.evaluate((p) => {
    document.querySelector('#place-pick').value = String(window.__y97.places.findIndex((q) => q.name === p));
    document.querySelector('#start').click();
  }, place);
  await page.waitForFunction(() => document.querySelector('#intro').hidden, null, { timeout: 120000 });
  await page.waitForTimeout(3000);
  console.log(name + ':', await recStart());
  await page.waitForTimeout(secs * 1000);
  await recStop(name);
}
await browser.close();
