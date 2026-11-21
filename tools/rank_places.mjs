// 전체 순위의 Worker(notes-worker/src/rank.js)가 기록을 검사할 때 쓰는 자리: 출발할 곳(places.js startPlaces),
// 활천대에서 생일인 친구가 선 자리, 공중전화(campus.json 의 payphone)마다 수화기를 드는 자리(pager.js 의 sx · sy).
// 앞의 둘은 게임이 열릴 때 충돌 · 현관 자료로 셈하는 값이라 헤드리스로 읽어 둔다.
//   cd web && npx vite --port 5197          (다른 터미널, 아무 포트)
//   node tools/rank_places.mjs [--port 5197]   → notes-worker/src/places.json
// 건물 · 현관 · 땅을 고쳐 출발할 곳이 옮겨지면 다시 돌리고 Worker 를 다시 배포한다(cd notes-worker && npx wrangler deploy).
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '..');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
const port = arg('port', '5197');
const out = path.join(root, 'notes-worker/src/places.json');

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
const browser = await chromium.launch({ args: ['--use-angle=vulkan', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 640, height: 400 } });
await page.goto(`http://localhost:${port}/`);
await page.waitForFunction(() => window.__y97 && window.__y97.places && window.__y97.birthday, null, { timeout: 300000, polling: 1000 });
const data = await page.evaluate(async () => {
  const { NORTH } = await import('/src/places.js');
  const r2 = (v) => Math.round(v * 100) / 100;
  const y = window.__y97, b = y.birthday.b.holder.position;
  return {
    places: y.places.map((p) => ({ name: p.name, x: r2(p.x), y: r2(p.y), ...(p.front ? { front: true } : {}), ...(NORTH.includes(p.name) ? { north: true } : {}) })),
    bday: { x: r2(b.x), y: r2(-b.z) },
  };
});
await browser.close();
// the booths' standing spots (pager.js: STAND m out of the open front)
const STAND = 0.85;
const campus = JSON.parse(fs.readFileSync(path.join(root, 'web/public/data/campus.json'), 'utf8'));
data.booths = campus.props.filter((p) => p[0] === 'payphone').map(([, x, y, rot]) => [x + Math.cos(rot) * STAND, y + Math.sin(rot) * STAND]);
fs.writeFileSync(out, JSON.stringify(data, null, 1) + '\n');
console.log(`${data.places.length} places, ${data.booths.length} booths, 생일인 친구 (${data.bday.x}, ${data.bday.y}) → ${path.relative(root, out)}`);
