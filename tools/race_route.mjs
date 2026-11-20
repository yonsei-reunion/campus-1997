// 캠퍼스 달리기(web/src/race.js)의 코스: 경유점 사이를 걷는 사람이 달릴 수 있는 길로 잇고, 그 길을 따라 문을 놓는다.
//   cd web && npx vite --port 5197          (다른 터미널, 아무 포트)
//   node tools/race_route.mjs [--port 5197] [--only baekyang,loop] [--check]
// - 길: 걷는 사람의 충돌(Colliders: 건물 외곽 · 나무 · 관목 · 소품) 위 0.5 m 격자에서 A*. 벽에서 0.45 m 안은 막고 1.6 m 안은 비싸게.
// - 그 길을 Player.update 로 실제로 달려 본다(계단 · 테라스 벽 · 화단 턱은 충돌 목록에 없고 걷기의 광선에만 있음).
//   2 s 동안 2 m 를 못 가면 그 자리를 막고 다시 찾는다(8번까지).
// - 문: 길을 따라 약 55 m 마다. 출력의 gates 를 race.js COURSES 에 붙인다.
// - legs: 문과 문 사이 길의 꺾이는 점(양끝 문은 뺌). 바닥 화살표가 이 선을 따른다. race.js COURSES 의 legs 에 붙인다.
// - --check: race.js 의 지금 문을 경유점 삼아 A* 로 이은 길로 게임을 처음부터 결승까지 돌려(Race.start · update)
//   끝나는지만 본다. legs 가 있는 코스는 바닥 화살표의 선(문과 legs)을 그대로 달리고, 없는 코스는 1 m 격자로
//   이은 길의 legs 도 낸다.
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '..');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
const port = arg('port', '5197');
const only = arg('only', '');
const check = process.argv.includes('--check');

// 경유점: [x, y] 또는 출발할 곳(places.js)의 이름. 현관 앞(계단 · 테라스)은 피해 보도 위에 둔다
const VIA = {
  baekyang: [[-110.2, -383.0], [-46, -166], [-15, -50], [28, 124], '언더우드관'],
  loop: [[-2, -58], [30, -10], [42.0, 48.3], [64.7, 131.3], [-70.9, 140.7], [-130.1, 67.9], [-58, -40], [-6, -48]],
  cheongsong: ['언더우드관', [147.5, 138.4], [235.8, 293.4], [150, 284], [84.9, 334.6], [40, 250]],
  // (상대신관: 상뜰 남쪽 계단으로 올라 상뜰 위가 결승)
  gate_sang: [[-110.2, -383.0], [-46, -166], [-15, -50], [28, 124], '언더우드관', [102.1, 403.2], [104.6, 413.0], [106, 421]],
  rotary_sang: [[-104, -930], [-99, -700], [-99, -470], [-68, -456.5], [-68, -421], [-110.2, -383.0], [-46, -166], [-15, -50],
    [28, 124], '언더우드관', [102.1, 403.2], [104.6, 413.0], [106, 421]],
};
const SPACING = 55;

function findPlaywright() {
  const tries = [process.env.PLAYWRIGHT, path.join(root, 'web/'), here + '/'].filter(Boolean);
  const npx = path.join(os.homedir(), '.npm/_npx');
  if (fs.existsSync(npx)) for (const d of fs.readdirSync(npx)) tries.push(path.join(npx, d, 'node_modules/'));
  for (const t of tries) {
    try { return createRequire(t.endsWith('/') ? t : t + '/')('playwright'); } catch { /* next */ }
  }
  throw new Error('playwright not found: npx playwright install chromium, or set PLAYWRIGHT=<dir>');
}

// ---------------------------------------------------------------- in the page
function pageLib() {
  window.__route = (via, blocked, asLegs = false, G = 0.5, R = 0.45) => {
    const Y = window.__y97, C = Y.player.col;
    const P = (n) => { const p = Y.places.find((q) => q.name === n); if (!p) throw new Error('no place ' + n); return [p.x, p.y]; };
    const pts = via.map((v) => (typeof v === 'string' ? P(v) : v)).map(([x, y]) => C.resolve(x, y, 0.7));
    const isBlocked = (x, y) => blocked.some(([bx, by, r]) => Math.hypot(x - bx, y - by) < r);
    const K = (i, j) => i * 100000 + j;     // (G: 0.5 m, so the 2 m walk by 성산로's crossing is open)
    function astar(a, b) {
      const si = Math.round(a[0] / G), sj = Math.round(a[1] / G), ti = Math.round(b[0] / G), tj = Math.round(b[1] / G);
      const open = [[0, si, sj]], g = new Map([[K(si, sj), 0]]), from = new Map(), memo = new Map();
      const cost = (i, j) => {
        let c = memo.get(K(i, j));
        if (c === undefined) { const x = i * G, y = j * G;
          c = !C.clear(x, y, R) || isBlocked(x, y) ? Infinity : !C.clear(x, y, 1.6) ? 2.2 : 1; memo.set(K(i, j), c); }
        return c;
      };
      const push = (n) => { open.push(n); let c = open.length - 1; while (c) { const p = (c - 1) >> 1; if (open[p][0] <= open[c][0]) break; [open[p], open[c]] = [open[c], open[p]]; c = p; } };
      const pop = () => {
        const t = open[0], l = open.pop();
        if (open.length) {
          open[0] = l;
          for (let c = 0; ;) {
            const a = 2 * c + 1, b = a + 1; let m = c;
            if (a < open.length && open[a][0] < open[m][0]) m = a;
            if (b < open.length && open[b][0] < open[m][0]) m = b;
            if (m === c) break;
            [open[m], open[c]] = [open[c], open[m]]; c = m;
          }
        }
        return t;
      };
      for (let n = 0; open.length; n++) {
        const [, i, j] = pop();
        if ((i === ti && j === tj) || n > 1.2e7) break;
        const gc = g.get(K(i, j));
        for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]) {
          const ni = i + di, nj = j + dj, c = cost(ni, nj);
          if (c === Infinity) continue;
          const ng = gc + c * Math.hypot(di, dj);
          if (ng < (g.get(K(ni, nj)) ?? Infinity)) { g.set(K(ni, nj), ng); from.set(K(ni, nj), [i, j]); push([ng + Math.hypot(ni - ti, nj - tj), ni, nj]); }
        }
      }
      const out = [[ti, tj]];
      for (let cur = [ti, tj]; cur[0] !== si || cur[1] !== sj;) { cur = from.get(K(cur[0], cur[1])); if (!cur) return null; out.push(cur); }
      return out.reverse().map(([i, j]) => [i * G, j * G]);
    }
    let full = [];
    const legs = [];
    for (let i = 1; i < pts.length; i++) {
      const p = astar(pts[i - 1], pts[i]);
      if (!p) return { fail: i, from: pts[i - 1], to: pts[i] };
      legs.push(p);
      full = full.concat(i > 1 ? p.slice(1) : p);
    }
    return asLegs ? legs : full;
  };
  // run along path (the walker steered at the point 2.5 m ahead); where it stays put 2 s, note it and hop on
  window.__sim = async (path) => {
    const pl = window.__y97.player;
    pl.autoRun = true; pl.enabled = true; pl.keys.clear(); pl.keys.add('KeyW');
    pl.teleport(path[0][0], path[0][1], 0);
    let k = 0, t = 0, last = [pl.x, pl.y], lastT = 0;
    const stuck = [];
    while (k < path.length - 1 && t < 900) {
      while (k < path.length - 1 && Math.hypot(path[k][0] - pl.x, path[k][1] - pl.y) < 2.5) k++;
      const [tx, ty] = path[k];
      pl.heading = Math.atan2(tx - pl.x, -(ty - pl.y));
      pl.cam.orbit = 0;
      pl.update(1 / 30); t += 1 / 30;
      if (t - lastT > 2) {
        if (Math.hypot(pl.x - last[0], pl.y - last[1]) < 2) {
          const d = Math.hypot(tx - pl.x, ty - pl.y) || 1;
          stuck.push([pl.x, pl.y], [pl.x + (tx - pl.x) / d * 1.2, pl.y + (ty - pl.y) / d * 1.2]);
          k = Math.min(path.length - 1, k + 6);
          pl.teleport(path[k][0], path[k][1], 0);
        }
        last = [pl.x, pl.y]; lastT = t;
      }
      if ((t * 30 | 0) % 20 === 0) await new Promise((r) => setTimeout(r, 0));
    }
    pl.keys.clear();
    return { t, stuck };
  };
  // the game itself over a course, steered at its gates through the points of path (or straight at them)
  window.__race = async (id, path) => {
    const Y = window.__y97, pl = Y.player, R = await Y.loadRace();
    R.stop();
    await R.start(id);
    const gates = R.course.gates;
    path = (path || gates).concat([gates[gates.length - 1]]);
    let t = 0, k = 0;
    while (R.state === 'count') { R.update(1 / 30, t, false); pl.update(1 / 30); t += 1 / 30; }
    pl.keys.add('KeyW');
    while (R.state === 'play' && t < 400) {
      // a gate passed (within its 4.5 m): on along the next leg, as the arrows lead
      const at = path.indexOf(gates[R.next - 1]);
      if (at >= k) k = at + 1;
      while (k < path.length - 1 && Math.hypot(path[k][0] - pl.x, path[k][1] - pl.y) < 2.5) k++;
      pl.heading = Math.atan2(path[k][0] - pl.x, -(path[k][1] - pl.y)); pl.cam.orbit = 0;
      pl.update(1 / 30); R.update(1 / 30, t, false); t += 1 / 30;
      if ((t * 30 | 0) % 30 === 0) await new Promise((r) => setTimeout(r, 0));
    }
    pl.keys.clear();
    const res = { state: R.state, time: +R.time.toFixed(1), gate: R.next, of: gates.length - 1 };
    R.stop();
    return res;
  };
}

// a leg's 1 m grid steps down to the turns (Douglas-Peucker, 0.3 m: no corner of a garden cut), for the arrows on the ground (race.js legs)
function simplify(p, tol = 0.3) {
  if (p.length < 3) return p;
  const [ax, ay] = p[0], [bx, by] = p[p.length - 1], L = Math.hypot(bx - ax, by - ay) || 1;
  let worst = 0, at = 0;
  for (let i = 1; i < p.length - 1; i++) {
    const d = Math.abs((bx - ax) * (ay - p[i][1]) - (ax - p[i][0]) * (by - ay)) / L;
    if (d > worst) { worst = d; at = i; }
  }
  return worst < tol ? [p[0], p[p.length - 1]] : simplify(p.slice(0, at + 1), tol).slice(0, -1).concat(simplify(p.slice(at), tol));
}
const legsOf = (legs) => legs.map((l) => simplify(l).slice(1, -1).map(([x, y]) => [+x.toFixed(1), +y.toFixed(1)]));

function spaceGates(p) {
  const L = p.reduce((s, q, i) => (i ? s + Math.hypot(q[0] - p[i - 1][0], q[1] - p[i - 1][1]) : 0), 0);
  const n = Math.max(6, Math.round(L / SPACING)), step = L / n, out = [p[0]];
  // legs: the path itself cut at the gates (not found again between them: the way the walker was run through)
  const legs = [[p[0]]];
  let acc = 0, next = step;
  for (let i = 1; i < p.length; i++) {
    const [ax, ay] = p[i - 1], [bx, by] = p[i], d = Math.hypot(bx - ax, by - ay);
    while (acc + d >= next - 1e-9 && out.length < n) {
      const u = (next - acc) / d, q = [+(ax + (bx - ax) * u).toFixed(1), +(ay + (by - ay) * u).toFixed(1)];
      out.push(q);
      legs[legs.length - 1].push(q);
      legs.push([q]);
      next += step;
    }
    legs[legs.length - 1].push(p[i]);
    acc += d;
  }
  out.push(p[p.length - 1].map((v) => +v.toFixed(1)));
  return { gates: out, legs, length: Math.round(L) };
}

// ---------------------------------------------------------------- run
const { chromium } = findPlaywright();
const browser = await chromium.launch({ args: ['--use-angle=vulkan', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 640, height: 400 } });
page.on('pageerror', (e) => console.error('page error:', e.message));
await page.goto(`http://localhost:${port}/`);
await page.waitForFunction(() => window.__y97 && !document.querySelector('#start').disabled, null, { timeout: 300000 });
await page.evaluate(() => { document.querySelector('#news .close')?.click(); window.__y97.startWalk(); });
console.error('every hall in…');
await page.waitForFunction(() => window.__y97.campusLoaded, null, { timeout: 600000, polling: 2000 });
await page.evaluate(() => window.__y97.renderer.setAnimationLoop(null));       // (the walker is stepped by hand)
await page.evaluate(`(${pageLib})()`);

const ids = Object.keys(VIA).filter((id) => !only || only.split(',').includes(id));
for (const id of ids) {
  if (check) {
    const r = await page.evaluate(async (id) => {
      // with legs: run along the ground's arrows (gates and the turns between); without (a course before legs):
      // gate to gate over the 1 m grid the gates were found on, and give the legs of that way
      const { courseOf } = await import('/src/race.js');
      const c = courseOf(id);
      if (c.legs) return window.__race(id, c.gates.flatMap((g, k) => [g, ...(c.legs[k] || [])]));
      const path = window.__route(c.gates, [], false, 1, 0.55);
      return Array.isArray(path) ? { ...(await window.__race(id, path)), legs: window.__route(c.gates, [], true, 1, 0.55) } : { noWay: path };
    }, id);
    const legs = r.legs;
    delete r.legs;
    console.log(id, JSON.stringify(r));
    if (legs) console.log(`  legs: ${JSON.stringify(legsOf(legs))}`);
    continue;
  }
  const blocked = [];
  let path = null;
  for (let it = 0; it < 8; it++) {
    path = await page.evaluate(([v, b]) => window.__route(v, b), [VIA[id], blocked]);
    if (!Array.isArray(path)) { console.error(id, 'no way between', JSON.stringify(path)); path = null; break; }
    const r = await page.evaluate((p) => window.__sim(p), path);
    console.error(`${id}: try ${it + 1}, ${r.t.toFixed(1)} s, stuck ${r.stuck.length / 2}${r.stuck.length ? " at " + JSON.stringify(r.stuck.filter((_, i) => !(i % 2)).map((p) => p.map((v) => Math.round(v)))) : ""}`);
    if (!r.stuck.length) break;
    for (const [x, y] of r.stuck) blocked.push([x, y, 2.2]);
    if (it === 7) path = null;
  }
  if (!path) continue;
  const g = spaceGates(path);
  console.log(`${id}: ${g.length} m, ${g.gates.length - 1} legs\n  gates: ${JSON.stringify(g.gates)}`);
  console.log(`  legs: ${JSON.stringify(legsOf(g.legs))}`);
}
await browser.close();
