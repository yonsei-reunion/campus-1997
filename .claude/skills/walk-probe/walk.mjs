// 걷기 탐침: 떠 있는 vite 의 게임에서, 게임 자신의 충돌 계산으로 가상의 걷는 사람을 길마다 4 cm 씩 걸려 본다.
//   node .claude/skills/walk-probe/walk.mjs <포트> <routes.json> [--back] [--query ?touch] [--events 8]
//   routes.json: [{ "name": "앞 계단 오르기", "pts": [[x, y], [x, y], ...] }, ...]   캠퍼스 좌표 m (x = 동, y = 북)
//   --back   길마다 거꾸로도 걷는다(계단은 오르기와 내려가기가 다르게 막힌다)
// 한 걸음: Colliders.resolve(반지름 0.32) → pushFromWalls → groundAt(발 위 0.55 m 에서 아래로). web/src/player.js 의 update 와 같은 순서.
// 길마다 내는 것
//   reached   마지막 점에 0.3 m 안으로 닿았는지
//   events    fall(한 걸음에 1 m 넘게 떨어짐: x, y, 전 높이, 뒤 높이) · wall(0.45 m 넘는 턱: x, y, 높이차) · blocked(나아가지 못함: x, y, 높이)
//   maxDrop · maxClimb   한 걸음의 가장 큰 내려감 · 올라감(m), start · end 는 [x, y, 높이(해발)]
// 끝에 벽 메시 수(0 이면 벽 밀기를 못 본 것), 실패한 셰이더 수, 콘솔 에러.
// Playwright 의 Chromium 이 필요하다(tools/snapshots.mjs 와 같은 방법으로 찾음. PLAYWRIGHT=<node_modules/playwright 가 든 폴더>).
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '../../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); if (i < 0) return d; const v = args[i + 1]; args.splice(i, 2); return v; };
const query = opt('query', '');
const nEvents = +opt('events', 8);
const back = args.includes('--back');
const [port, routesPath] = args.filter((a) => !a.startsWith('--'));
if (!port || !routesPath) { console.error('usage: node walk.mjs <port> <routes.json> [--back] [--query ?touch] [--events 8]'); process.exit(2); }

function findPlaywright() {
  const tries = [process.env.PLAYWRIGHT, path.join(root, 'web/'), path.join(root, 'tools/')].filter(Boolean);
  const npx = path.join(os.homedir(), '.npm/_npx');
  if (fs.existsSync(npx)) for (const d of fs.readdirSync(npx)) tries.push(path.join(npx, d, 'node_modules/'));
  for (const t of tries) {
    try { return createRequire(t.endsWith('/') ? t : t + '/')('playwright'); } catch { /* next */ }
  }
  throw new Error('playwright not found: npx playwright install chromium, or set PLAYWRIGHT=<dir>');
}

let routes = JSON.parse(fs.readFileSync(routesPath, 'utf8'));
if (back) routes = routes.flatMap((r) => [r, { name: r.name + ' (거꾸로)', pts: [...r.pts].reverse() }]);

const { chromium } = findPlaywright();
const browser = await chromium.launch({ args: ['--use-angle=vulkan', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
const errs = [];
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().replace(/\0/g, '').slice(0, 300)); });
page.on('pageerror', (e) => errs.push('PAGEERR ' + e.message));
await page.goto(`http://localhost:${port}/${query}`, { timeout: 120000 });
await page.waitForFunction(() => window.__y97 && window.__y97.player && window.__y97.player.walk && window.__y97.player.walk.length > 1
  && window.__y97.campusLoaded !== false && !document.querySelector('#start')?.disabled, null, { timeout: 300000 });
await page.waitForTimeout(4000);
const res = await page.evaluate(({ routes, nEvents }) => {
  const P = window.__y97.player, out = [];
  const r2 = (v) => +v.toFixed(2);
  for (const r of routes) {
    let [x, y] = r.pts[0];
    let h = P.groundAt(x, -y, 400) ?? P.hf.height(x, y);
    const log = { name: r.name, reached: false, start: [x, y, r2(h)], end: null, maxDrop: 0, maxClimb: 0, events: [] };
    let gaveUp = false;
    for (let k = 1; k < r.pts.length && !gaveUp; k++) {
      const [tx, ty] = r.pts[k];
      let stuck = 0;
      for (let it = 0; it < 6000; it++) {
        const dx = tx - x, dy = ty - y, d = Math.hypot(dx, dy);
        if (d < 0.08) break;
        let nx = x + dx / d * 0.04, ny = y + dy / d * 0.04;
        [nx, ny] = P.col.resolve(nx, ny, 0.32, []);
        if (P.walls.length) { const [wx, wz] = P.pushFromWalls(nx, h, -ny); nx = wx; ny = -wz; }
        let g = P.groundAt(nx, -ny, h + 0.55);
        if (g === null) g = P.hf.height(nx, ny);
        const dz = g - h;
        if (dz < -1.0) log.events.push(['fall', r2(nx), r2(ny), r2(h), r2(g)]);
        if (dz > 0.45) {
          log.events.push(['wall', r2(nx), r2(ny), r2(dz)]);
          if (++stuck > 30) { gaveUp = true; break; }
          continue;
        }
        log.maxDrop = Math.max(log.maxDrop, -dz); log.maxClimb = Math.max(log.maxClimb, dz);
        const prog = Math.hypot(tx - nx, ty - ny) < d - 0.005;
        if (!prog) {
          if (++stuck > 60) { log.events.push(['blocked', r2(x), r2(y), r2(h)]); gaveUp = true; break; }
        } else stuck = 0;
        x = nx; y = ny; h = g;
      }
    }
    const [lx, ly] = r.pts[r.pts.length - 1];
    log.reached = Math.hypot(lx - x, ly - y) < 0.3;
    log.end = [r2(x), r2(y), r2(h)];
    log.nEvents = log.events.length;
    log.events = log.events.slice(0, nEvents);
    log.maxDrop = r2(log.maxDrop); log.maxClimb = r2(log.maxClimb);
    out.push(log);
  }
  return { out, walls: P.walls.length, badPrograms: window.__y97.renderer.info.programs.filter((p) => p.diagnostics).length };
}, { routes, nEvents });
for (const r of res.out) {
  const flag = !r.reached || r.events.some((e) => e[0] !== 'wall') ? '!!' : 'ok';
  console.log(`${flag} ${r.name}: reached ${r.reached}, drop ${r.maxDrop}, climb ${r.maxClimb}, start ${JSON.stringify(r.start)}, end ${JSON.stringify(r.end)}`);
  for (const e of r.events) console.log('     ' + JSON.stringify(e));
  if (r.nEvents > r.events.length) console.log(`     … 사건 ${r.nEvents - r.events.length}개 더`);
}
console.log(`wall meshes ${res.walls}, failed shader programs ${res.badPrograms}`);
const shown = errs.filter((e) => !/font|403|Failed to load resource/i.test(e));
if (shown.length) console.log('console errors:\n' + shown.slice(0, 5).join('\n'));
await browser.close();
process.exit(res.out.some((r) => !r.reached || r.events.some((e) => e[0] === 'fall')) ? 1 : 0);
