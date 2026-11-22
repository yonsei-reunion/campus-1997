// 소개 영상(tools/trailer/intro.mjs)이 게임 페이지에 넣는 코드: 자막 층과 장면(segment)들.
// 장면마다 { n: 프레임 수, init(): 준비(비동기), step(i): i 번째 프레임을 그림 } 이고, step 은 카메라 · 자막을 놓은 뒤
// __y97.record.step(dt) 로 게임을 한 프레임 진행한다(30 fps 고정). 화면은 intro.mjs 가 page.screenshot 으로 받는다
// (자막 · 말풍선 · 게임의 창이 DOM 이라 캔버스만 받으면 빠진다).
// 좌표: 캠퍼스 (x 동, y 북), three 는 (x, 높이, -y). 높이는 해발.
(() => {
  const y = window.__y97, pl = y.player, cam = y.camera, V = cam.position.constructor, FPS = 30, DT = 1 / FPS;
  const $ = (s) => document.querySelector(s);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const smooth = (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u));
  const lerp = (a, b, u) => a + (b - a) * u;
  const ground = (x, yy) => pl.groundAt(x, -yy, 400) ?? pl.hf.height(x, yy);
  const P = (x, yy, h) => new V(x, h, -yy);                     // 해발 높이
  const G = (x, yy, dh = 0) => new V(x, ground(x, yy) + dh, -yy);   // 땅 위 dh

  // ---------------------------------------------------------------- 자막 층
  const css = document.createElement('style');
  css.textContent = `
  #iv { position: fixed; left: 0; top: 0; width: 1920px; height: 1080px; transform: scale(calc(1 / var(--iv-dpr))); transform-origin: 0 0;
    z-index: 2147483647; pointer-events: none; color: #fff; overflow: hidden; font-family: "Noto Sans KR", sans-serif; word-break: keep-all; }
  #iv > * { position: absolute; opacity: 0; will-change: opacity, transform; }
  #iv .scrim { inset: 0; background: radial-gradient(ellipse 62% 74% at 0% 100%, rgba(8,14,30,.8), rgba(8,14,30,.42) 45%, rgba(8,14,30,0) 72%); }
  #iv .shade { inset: 0; background: rgba(8,14,30,.62); }
  #iv .cap { left: 110px; bottom: 96px; max-width: 1500px; text-shadow: 0 3px 14px rgba(0,0,0,.55); }
  #iv .cap b { display: block; font: 400 92px/1.1 "Do Hyeon", sans-serif; letter-spacing: .5px; }
  #iv .cap span { display: block; margin-top: 14px; font: 500 42px/1.35 "Noto Sans KR", sans-serif; }
  #iv .cap small { display: block; margin-top: 10px; font: 400 30px/1.3 "Noto Sans KR", sans-serif; opacity: .85; }
  #iv .cap i { font-style: normal; color: #ffe45c; }
  #iv .line { left: 110px; right: 110px; bottom: 84px; text-align: center; font: 500 46px/1.35 "Noto Sans KR", sans-serif;
    text-shadow: 0 3px 14px rgba(0,0,0,.6); }
  #iv .line > u { display: inline-block; padding: 10px 36px 13px; border-radius: 20px; background: rgba(8,14,30,.62); text-decoration: none; text-shadow: none; }
  #iv .line i { font-style: normal; color: #ffe45c; }
  #iv .chip { left: 110px; top: 64px; padding: 10px 28px 8px; border-radius: 999px; background: #ffe45c; color: #1b2236;
    font: 400 38px/1.2 "Do Hyeon", sans-serif; box-shadow: 0 4px 14px rgba(0,0,0,.25); }
  #iv .title { left: 0; right: 0; top: 30%; text-align: center; text-shadow: 0 4px 24px rgba(0,0,0,.6); }
  #iv .title b { display: block; font: 400 150px/1.1 "Do Hyeon", sans-serif; }
  #iv .title span { display: block; margin-top: 18px; font: 500 46px/1.3 "Noto Sans KR", sans-serif; }
  #iv .title small { display: inline-block; margin-top: 30px; padding: 8px 30px; border-radius: 999px; background: #ffe45c; color: #1b2236;
    font: 700 38px/1.3 "Noto Sans KR", sans-serif; text-shadow: none; }
  #iv .tag { padding: 7px 22px 6px; border-radius: 14px; background: rgba(255,255,255,.96); color: #1b2236; transform: translate(-50%, -100%);
    font: 400 36px/1.2 "Do Hyeon", sans-serif; box-shadow: 0 4px 14px rgba(0,0,0,.3); white-space: nowrap; }
  #iv .tag::after { content: ""; position: absolute; left: 50%; bottom: -22px; width: 3px; height: 22px; margin-left: -1px; background: rgba(255,255,255,.96); }
  #iv .cmp-win { border: 8px solid #fff; box-shadow: 0 0 0 4000px rgba(8,14,30,.93); box-sizing: content-box; }
  #iv .cmp-photo { border: 8px solid #fff; box-shadow: 0 10px 30px rgba(0,0,0,.5); background: #222 center / cover no-repeat; box-sizing: content-box; }
  #iv .cmp-lab { transform: translateX(-50%); font: 500 34px/1.3 "Noto Sans KR", sans-serif; white-space: nowrap; text-align: center; }
  #iv .cmp-lab b { display: inline-block; margin-right: 14px; padding: 3px 18px 4px; border-radius: 999px; background: #ffe45c; color: #1b2236; font: 400 32px/1.3 "Do Hyeon", sans-serif; }
  #iv .cmp-name { left: 0; right: 0; bottom: 54px; text-align: center; font: 400 84px/1.1 "Do Hyeon", sans-serif; text-shadow: 0 3px 14px rgba(0,0,0,.6); }
  #iv .cmp-name small { display: block; margin-top: 8px; font: 500 34px/1.3 "Noto Sans KR", sans-serif; opacity: .9; }
  #iv .cover { inset: 0; background: #080e1e; }
  #iv .pg { left: 150px; right: 150px; top: 176px; }
  #iv .pg h1 { margin: 0; color: #fff; font: 400 112px/1.15 "Do Hyeon", sans-serif; text-shadow: 0 3px 16px rgba(0,0,0,.5); }
  #iv .pg h1 i { font-style: normal; color: #ffe45c; }
  #iv .pg h2 { margin: 0 0 8px; font: 400 50px/1.2 "Do Hyeon", sans-serif; color: #ffe45c; }
  #iv .pg p { margin: 16px 0 0; font: 500 44px/1.45 "Noto Sans KR", sans-serif; }
  #iv .pg li small { display: block; margin-top: 4px; font-size: .8em; font-weight: 400; opacity: .86; }
  #iv .pg ul { margin: 40px 0 0; padding: 0; list-style: none; }
  #iv .pg li { margin: 0 0 24px; padding: 20px 36px 22px; border-radius: 18px; background: rgba(255,255,255,.1); border-left: 8px solid #ffe45c;
    font: 500 42px/1.4 "Noto Sans KR", sans-serif; }
  #iv .pg li b { color: #ffe45c; font-weight: 700; margin-right: 12px; }
  #iv .pg .cols { display: grid; grid-template-columns: 1.5fr 1fr; gap: 26px 50px; margin-top: 30px; white-space: nowrap; }
  #iv .pg .cols div { font: 500 35px/1.66 "Noto Sans KR", sans-serif; }
  #iv .pg .foot { margin-top: 44px; font: 400 32px/1.4 "Noto Sans KR", sans-serif; opacity: .85; }
  #iv .pg.mid { top: 230px; text-align: center; }
  #iv .pg.mid h2 { font-size: 64px; margin-top: 56px; }
  #iv .pg.mid p { font-size: 58px; }
  #iv .key { display: inline-block; min-width: 54px; padding: 2px 14px; margin: 0 6px; border-radius: 10px; background: #1b2236; color: #fff;
    font: 700 36px/1.4 "Noto Sans KR", sans-serif; text-align: center; text-shadow: none; vertical-align: 4px; }
  `;
  document.head.appendChild(css);
  const iv = document.createElement('div');
  iv.id = 'iv';
  iv.style.setProperty('--iv-dpr', String(devicePixelRatio));   // 자막은 1920 × 1080 의 화소로 적고, CSS 화면(1280 × 720)에 맞춰 줄임
  document.body.appendChild(iv);
  const hide = document.createElement('style');
  document.head.appendChild(hide);
  // 게임의 화면 요소: 'none' 다 숨김, 'bubbles' 말풍선만, 'game' 그대로, 그 밖에는 CSS 그대로
  const HUD = {
    none: '#hud > *, #toast, #birdpins, #tourbar, #birdbar { display: none !important; }',
    bubbles: '#hud > *:not(#bubbles), #toast, #birdpins, #tourbar, #birdbar { display: none !important; }',
    // 걷는 화면에서 안내 버튼 · 말풍선 · 게임의 창만(지금 여기 · 미니맵 · 버튼은 숨김)
    play: '#hud > #place, #hud > #minimap, #hud > #stamps, #hud > #hudbtns, #hud > #blabels, #hud > #datestamp, #toast, #birdpins, #tourbar, #birdbar { display: none !important; }',
    // 게임의 창(쪽지 · 미니 게임)만
    cards: '#hud > #place, #hud > #minimap, #hud > #stamps, #hud > #hudbtns, #hud > #blabels, #hud > #datestamp, #hud > #prompt, #toast, #birdpins, #tourbar, #birdbar { display: none !important; }',
    game: '',
  };
  const hud = (k) => { hide.textContent = HUD[k] ?? k; };

  const els = new Map();
  // 자막 하나: t 가 [a, b] 안일 때 보임(0.4 초 번짐, 아래에서 살짝 올라옴). html 은 처음 한 번만 넣음
  const show = (id, cls, html, t, a, b, { fade = 0.4, slide = 18, x = null, yy = null } = {}) => {
    let e = els.get(id);
    if (!e) { e = document.createElement('div'); e.className = cls; e.innerHTML = html; iv.appendChild(e); els.set(id, e); }
    const o = t < a || t > b ? 0 : Math.min(1, (t - a) / fade, (b - t) / fade);
    e.style.opacity = smooth(o).toFixed(3);
    if (x !== null) { e.style.left = x.toFixed(1) + 'px'; e.style.top = yy.toFixed(1) + 'px'; }
    else if (slide) e.style.transform = `translateY(${((1 - smooth(Math.min(1, (t - a) / fade))) * slide).toFixed(1)}px)`;
    return e;
  };
  const line = (id, html, t, a, b, o) => show(id, 'line', `<u>${html}</u>`, t, a, b, o);
  // 키를 누르고 뗌(게임은 window 의 keydown · keyup 의 code 를 읽는다)
  const key = (code, down = true, k = '') => window.dispatchEvent(new KeyboardEvent(down ? 'keydown' : 'keyup', { code, key: k || code, bubbles: true, cancelable: true }));
  const clear = () => { for (const e of els.values()) e.remove(); els.clear(); };
  // 세계의 한 점에 붙는 이름표
  const tag = (id, p, text, t, a, b) => {
    const q = p.clone().project(cam);
    const on = q.z < 1 && Math.abs(q.x) < 1.05 && Math.abs(q.y) < 1.05;
    show(id, 'tag', text, on ? t : -1, a, b, { x: (q.x * 0.5 + 0.5) * 1920, yy: (-q.y * 0.5 + 0.5) * 1080 - 22 });
  };

  // ---------------------------------------------------------------- 게임의 상태
  const inTitle = () => !$('#intro').hidden;
  const fov = (f) => { if (Math.abs(cam.fov - f) > 1e-4) { cam.fov = f; cam.updateProjectionMatrix(); } };
  const step = (dt = DT) => y.record.step(dt);
  const settle = (n = 30, dt = DT) => { for (let i = 0; i < n; i++) step(dt); };
  // 걷기 화면으로(주인공 id 를 주면 그 사람으로, 그 단과대 앞에서)
  const toWalk = async (hero = null, place = undefined) => {
    if (y.bird.active) y.leaveBird();
    if (hero || !inTitle()) { if (!inTitle()) y.toTitle(); }
    if (inTitle()) {
      if (hero) $(`#hero-pick button[data-id=${hero}]`).click();
      if (place !== undefined) $('#place-pick').value = place === null ? '' : String(y.places.findIndex((p) => p.name === place));
      $('#start').click();
      for (let i = 0; i < 600 && inTitle(); i++) await sleep(100);
    }
    pl.scripted = false;
    pl.camOverride = null;
    pl.actor.holder.visible = true;
  };
  const toBird = () => { if (!y.bird.active) y.enterBird(); y.bird.auto = false; };
  const birdCam = (x, yy, h, tx, ty, th, f) => { y.bird.fixed = { x, y: yy, h, tx, ty, th }; y.bird.fovGoal = f; cam.fov = f; };
  const walkCam = (pos, look, f) => { pl.camOverride = { pos, look, k: 1 }; fov(f); };
  const season = async (s) => {
    if (localStorage.getItem('y97-season') === s && season.now === s) return;
    season.now = s;
    y.setSeason(s);
    for (let i = 0; i < 40; i++) { await sleep(120); step(); }       // 잎 텍스처 · 임포스터가 바뀔 때까지
  };
  const ensure = async (x, yy) => { const w = y.chunks.ensure(x, yy); if (w) await w; };
  // Catmull-Rom 으로 점들을 지남: pts [[...], ...], u 0 ~ 1
  const spline = (pts, u) => {
    const n = pts.length - 1, s = clamp(u, 0, 1) * n, i = Math.min(n - 1, Math.floor(s)), f = s - i;
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(n, i + 2)];
    return p1.map((_, k) => 0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * f + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * f * f + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * f * f * f));
  };

  // 고정 프레임 녹화: 캔버스는 CSS 화면 크기에 기기 화소 비를 곱한 1920 × 1080 으로 그림
  const rec = () => {
    y.record.start(innerWidth, innerHeight);
    y.renderer.setPixelRatio(devicePixelRatio);
    y.post.composer.setPixelRatio(devicePixelRatio);
    y.renderer.setSize(innerWidth, innerHeight, false);
    y.post.setSize(innerWidth, innerHeight);
  };
  const seg = {};
  const iv97 = (window.__iv = { seg, show, line, key, clear, rec, tag, hud, toWalk, toBird, birdCam, walkCam, season, ensure, spline, step, settle, fov, ground, P, G, V, sleep, smooth, lerp, clamp, FPS, DT, $,
    async init(name, arg) { clear(); rec(); await season(seg[name].season ?? 'summer'); await seg[name].init?.(arg); return seg[name].n; },
    async frame(name, i) { return (await seg[name].step(i, i / FPS)) || null; },
  });
  void iv97;
})();
