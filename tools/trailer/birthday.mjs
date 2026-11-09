// 활천대 생일 영상의 게임 프레임을 찍는다 (web/src/birthday.js 의 장면).
//   cd web && npx vite --port 5197          (다른 터미널)
//   node tools/trailer/birthday.mjs <출력 폴더> [--port 5197] [--only 0,300,600]
// <출력 폴더>/frames/%05d.jpg (1920 × 1080, 30 fps) 와 events.json(장면이 바뀐 영상 시각)을 쓴다. 이어서
//   python3 tools/trailer/birthday_video.py <출력 폴더> trailer/birthday.mp4
// 가 사진 → 게임 전환, 자막, 소리를 붙인다.
// 처음 몇 초는 reference/활천대_공사전_연세대블로그.jpg 를 푼 카메라(tools/snapshots.json compare/hwalcheon_old)에서
// 물줄기를 끈 채로 찍어, 사진이 그대로 게임 화면으로 바뀌게 한다. 프레임마다 게임을 고정 시간만큼 진행하므로
// (main.js record) 느린 컴퓨터에서도 고르게 찍히고, 던지는 순간은 게임 시간을 늦춰 슬로 모션으로 찍는다.
// --only: 그 프레임 번호만 저장(카메라 · 연출 시험용).
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '../..');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
const out = path.resolve(process.argv[2] && !process.argv[2].startsWith('--') ? process.argv[2] : path.join(os.tmpdir(), 'y97-birthday'));
const port = arg('port', '5197');
const only = arg('only', '') ? new Set(arg('only', '').split(',').map(Number)) : null;
const W = 1920, H = 1080, FPS = 30;

function findPlaywright() {
  const tries = [process.env.PLAYWRIGHT, path.join(root, 'web/'), here + '/'].filter(Boolean);
  const npx = path.join(os.homedir(), '.npm/_npx');
  if (fs.existsSync(npx)) for (const d of fs.readdirSync(npx)) tries.push(path.join(npx, d, 'node_modules/'));
  for (const t of tries) {
    try { return createRequire(t.endsWith('/') ? t : t + '/')('playwright'); } catch { /* next */ }
  }
  throw new Error('playwright not found: npx playwright install chromium, or set PLAYWRIGHT=<dir>');
}

fs.mkdirSync(path.join(out, 'frames'), { recursive: true });
const { chromium } = findPlaywright();
const browser = await chromium.launch({ args: ['--use-angle=vulkan', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const errs = [];
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().replace(/\0/g, '').slice(0, 300)); });
page.on('pageerror', (e) => errs.push('PAGEERR ' + e.message));
await page.goto(`http://localhost:${port}/`);
await page.waitForFunction(() => window.__y97 && window.__y97.birthday && !document.querySelector('#start')?.disabled, null, { timeout: 300000 });
await page.evaluate(() => window.__y97.setSeason('summer'));
await page.waitForTimeout(4000);
// only the speech bubbles over the picture, drawn bigger for a 1080p frame
await page.addStyleTag({ content: `
  #hud > *:not(#bubbles), #toast, #birdpins, #tourbar { display: none !important; }
  #bubbles .bubble { font-size: 30px; max-width: 460px; padding: 9px 22px 11px; border-width: 2.5px; border-radius: 26px;
    box-shadow: 0 5px 16px rgba(0,0,0,.28); }
  #bubbles .bubble::after { width: 18px; height: 18px; bottom: -11px; margin-left: -10px; border-width: 0 2.5px 2.5px 0; }` });

// ---------------------------------------------------------------- the scene, in the page
await page.evaluate(({ W, H, FPS }) => {
  const y = window.__y97, bd = y.birthday, pl = y.player, V = y.camera.position.constructor;
  y.startWalk();
  bd.reset();
  bd.noCamera = true;
  const F = bd.F, C = bd.C, h0 = F.h;
  // campus (x, y) + height over the flagstones -> three
  const P = (x, yy, dh) => new V(x, h0 + dh, -yy);
  // round the basin: bearing a (deg, campus, from east), r metres, dh over the flagstones
  const R = (a, r, dh) => { const t = a * Math.PI / 180; return new V(C.x + Math.cos(t) * r, h0 + dh, C.z - Math.sin(t) * r); };
  const at = (base, rad, tan, dh) => base.clone().addScaledVector(bd.rad, rad).addScaledVector(bd.tan, tan).setY(h0 + dh);
  const S = bd.spot, M = bd.mid;                   // where they stand; the middle of the carry
  // the shots: camera position, the point looked at, vertical field of view
  const SHOT = {
    // the photo's camera (tools/snapshots.json compare/hwalcheon_old)
    photo: { pos: P(-72.63, -209.14, 1.84), look: P(-83.1, -202.6, 1.4), fov: 34.3 },
    // round to the south: the two by the wall, you coming up from the right
    approach: { pos: R(-70, 12.5, 1.9), look: at(S, -0.6, 1.4, 1.05), fov: 40 },
    // side on to the carry
    side: { pos: at(M, 3.7, 0.35, 1.45), look: at(M, -0.9, 0.1, 0.8), fov: 44 },
    // the throw, a little wider and looking into the pool
    throw: { pos: at(M, 4.3, 0.9, 1.75), look: at(M, -1.9, 0.1, 0.9), fov: 46 },
    // over your shoulders, down at them in the water
    water: { pos: at(S, 2.9, 0.15, 2.25), look: at(bd.land, 0, 0, 0.75), fov: 46 },
    back: { pos: at(S, 4.0, 0.2, 1.6), look: at(S, -0.6, 0.1, 1.05), fov: 44 },
    // up and away: 활천대 with the eagle and the library beyond
    sky: { pos: P(-83.5, -233, 15), look: P(-83.1, -199, 0), fov: 46 },
  };
  const sprays = [];
  y.scene.traverse((o) => { for (const m of [].concat(o.material || [])) if (m.name === 'water_spray' && !sprays.includes(m)) sprays.push(m); });
  const spray0 = sprays.map((m) => m.opacity);
  const setSpray = (k) => sprays.forEach((m, i) => { m.opacity = spray0[i] * k; m.visible = k > 0.002; });
  // you, coming from 백양로's side (out of the picture until the frame has widened), round the basin to them
  const hero = pl.actor;
  const route = [P(-74.0, -202.5, 0), R(-40, 5.6, 0), at(S, 0.55, 2.7, 0)];
  const start = route[0], stop = route[2];
  pl.teleport(start.x, -start.z, 0);
  hero.heading = Math.atan2(route[1].x - start.x, route[1].z - start.z);
  pl.heading = hero.heading;
  hero.holder.rotation.y = hero.heading;
  pl.scripted = true;
  const smooth = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));
  const cam = { pos: SHOT.photo.pos.clone(), look: SHOT.photo.look.clone(), fov: SHOT.photo.fov, vp: new V(), vl: new V(), vf: 0 };
  const T = { dissolve: 3.2, jet: 6.0, dolly: 6.6, walk: 6.6 };
  // a critically damped spring towards the shot (w: how quick, 1/s): moves start and stop softly
  const spring = (goal, w, h) => {
    const a = new V();
    a.copy(goal.pos).sub(cam.pos).multiplyScalar(w * w).addScaledVector(cam.vp, -2 * w);
    cam.vp.addScaledVector(a, h); cam.pos.addScaledVector(cam.vp, h);
    a.copy(goal.look).sub(cam.look).multiplyScalar(w * w).addScaledVector(cam.vl, -2 * w);
    cam.vl.addScaledVector(a, h); cam.look.addScaledVector(cam.vl, h);
    cam.vf += ((goal.fov - cam.fov) * w * w - 2 * w * cam.vf) * h; cam.fov += cam.vf * h;
  };
  const st = (window.__bd = { i: 0, T: 0, events: [], last: '', said: null, acted: null, slow: 1, shot: 'photo', blend: null });
  const lerpShot = (a, b, u) => ({ pos: a.pos.clone().lerp(b.pos, u), look: a.look.clone().lerp(b.look, u), fov: a.fov + (b.fov - a.fov) * u });

  window.__bdStep = () => {
    const t = st.T;
    // game time runs slow from just before they let go until the splash has settled
    let want = 1;
    if ((bd.state === 'swing' && bd.st > 1.86) || bd.state === 'fly' || (bd.state === 'water' && bd.st < 0.55)) want = 0.32;
    st.slow += (want - st.slow) * (want < st.slow ? 0.35 : 0.12);
    const dt = st.slow / FPS;
    // the jet comes on after the photo has gone
    setSpray(smooth((t - T.jet) / 1.6));
    // you walk up to them
    if (!st.acted && t >= T.walk) {
      const wp = route[Math.min(st.leg ??= 1, 2)];
      if (bd.walk(hero, wp, dt, 1.55) || (st.leg < 2 && hero.holder.position.distanceTo(wp) < 0.5)) st.leg++;
      if (st.leg > 2) bd.turn(hero, Math.atan2(bd.b.holder.position.x - hero.holder.position.x, bd.b.holder.position.z - hero.holder.position.z), dt, 5);
      hero.holder.position.y = pl.groundAt(hero.holder.position.x, hero.holder.position.z) ?? hero.holder.position.y;
      pl.heading = hero.heading;
    }
    if (!st.acted) hero.mixer.update(dt);
    if (bd.said && st.said === null) { st.said = t; st.events.push({ t, e: 'said' }); }
    if (st.said !== null && !st.acted && t >= st.said + 2.6) { st.acted = bd.action() ? t : null; if (st.acted) st.events.push({ t, e: 'action' }); }
    if (bd.state !== st.last) { st.events.push({ t, e: bd.state }); st.last = bd.state; }
    // the camera: the photo's, then a dolly round to the two of them, then a shot per part of the scene, eased
    let goal;
    if (t < T.dolly) goal = SHOT.photo;
    else if (!st.acted) goal = lerpShot(SHOT.photo, SHOT.approach, smooth((t - T.dolly) / 4.2));
    else {
      const s = bd.state;
      goal = s === 'gather' || s === 'take' || s === 'lift' ? SHOT.side
        : s === 'swing' ? (bd.st > 1.7 ? SHOT.throw : SHOT.side)
        : s === 'fly' ? SHOT.throw
        : s === 'water' ? (bd.st > 0.9 ? SHOT.water : SHOT.throw)
        : s === 'stand' || s === 'wade' ? SHOT.water
        : s === 'climb' || (s === 'back' && bd.st < 2.0) ? SHOT.back
        : SHOT.sky;
    }
    if (!st.acted) { cam.pos.copy(goal.pos); cam.look.copy(goal.look); cam.fov = goal.fov; }
    else spring(goal, goal === SHOT.sky ? 1.1 : 3.2, 1 / FPS);
    pl.camOverride = { pos: cam.pos, look: cam.look, k: 1 };
    if (Math.abs(y.camera.fov - cam.fov) > 1e-4) { y.camera.fov = cam.fov; y.camera.updateProjectionMatrix(); }
    y.record.step(dt);
    st.i++;
    st.T = st.i / FPS;
    return { T: st.T, state: bd.state, st: bd.st, done: bd.state === 'rest' && bd.st > 7.5 };
  };
  y.record.start(W, H);
  // settle the exposure, the water and the anti-aliasing history on the first shot before the first frame
  for (let i = 0; i < 45; i++) { pl.camOverride = { pos: cam.pos, look: cam.look, k: 1 }; y.camera.fov = cam.fov; y.camera.updateProjectionMatrix(); setSpray(0); y.record.step(1 / FPS); }
}, { W, H, FPS });

let i = 0;
for (;;) {
  const r = await page.evaluate(() => window.__bdStep());
  if (!only || only.has(i)) await page.screenshot({ path: path.join(out, 'frames', String(i).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 93 });
  if (i % 60 === 0) console.log(`frame ${i}  ${r.T.toFixed(2)} s  ${r.state} ${r.st.toFixed(2)}`);
  i++;
  if (r.done || i > 60 * FPS || (only && i > Math.max(...only))) break;
}
const events = await page.evaluate(() => window.__bd.events);
fs.writeFileSync(path.join(out, 'events.json'), JSON.stringify({ fps: FPS, frames: i, events }, null, 1));
console.log(`${i} frames -> ${out}`);
console.log(events.map((e) => `${e.t.toFixed(2)} ${e.e}`).join('\n'));
if (errs.length) console.log('errors:\n' + errs.slice(0, 10).join('\n'));
await browser.close();
