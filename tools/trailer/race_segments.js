// 캠퍼스 달리기 홍보 영상(1분)의 장면들. tools/trailer/intro_page.js 뒤에 넣는다(intro.mjs --segments race_segments.js).
// 순서와 자르는 곳은 race_video.py 가 정한다. 여기서는 장면마다 카메라 · 자막 · 게임 조작만.
// 달리는 사람은 자동으로 코스의 선(문과 바닥 화살표의 꺾이는 점)을 따라 뛴다(drive). 게임은 그대로 돌고(문 · 기록 ·
// 함께 뛰는 사람들), 카메라만 장면마다 놓는다.
(() => {
  const I = window.__iv, y = window.__y97, pl = y.player;
  const { seg, show, line, key, hud, toWalk, toBird, birdCam, walkCam, season, ensure, step, settle, ground, G, V, sleep, smooth, lerp, clamp, FPS, DT, $ } = I;
  const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
  const untilDo = async (ok, max = 600, dt = DT) => { for (let k = 0; k < max && !ok(); k++) { step(dt); if (k % 6 === 5) await sleep(0); } return ok(); };
  const waitFor = async (ok, ms = 8000) => { for (let k = 0; k < ms / 50 && !ok(); k++) await sleep(50); return ok(); };
  const shown = (sel) => { const e = $(sel); return !!e && !e.hidden && getComputedStyle(e).display !== 'none'; };
  // 게임의 화면 요소: 걷기 화면의 것은 숨기고 달리기의 HUD(기록 · 문 · 화살표, 가운데 큰 글씨, 문마다의 차이)만
  // (결과 창의 전체 순위 칸: 녹화는 순위 서버에 닿지 않으므로 「닿지 못했어요」가 나와 감춤)
  const RACE_HUD = '#hud > *:not(#bubbles), #toast, #birdpins, #tourbar, #birdbar, #raceresult .rankbox { display: none !important; }';
  const NO_RACE_HUD = RACE_HUD + ' #racehud, #racebig, #racesplit, #racehint, #raceresult { display: none !important; }';

  // 코스를 골라 출발선에 섬(카운트가 시작된 때). hero: 주인공 id
  const begin = async (id, hero) => {
    await toWalk(hero);
    const R = await y.loadRace();
    $('#news .close')?.click();
    await R.start(id);
    await waitFor(() => R.state === 'count', 10000);
    // 함께 뛰는 사람: 모두 같은 쪽으로, 코스 선에서 1.3 m 비켜(게임에서는 셋에 하나가 마주 와서 좁은 보도에서
    // 주인공과 부딪혀 밀려남. 같은 쪽으로 더 느리게 뛰니 주인공이 옆으로 앞질러 감)
    for (const r of R.runners) { r.dir = 1; r.side = r.n % 2 ? 1.3 : -1.3; }
    return R;
  };
  // 이 브라우저의 기록: 그 코스를 조금 늦게 뛴 판 셋(문마다의 시간과 함께). 문을 지날 때 「최고 기록」과의 차이(초록)가,
  // 결승에서 「내 새 기록!」이 나오게. 시간은 코스의 선의 길이를 뛰는 빠르기(6.2 m/s)로 나눈 것에 slow 를 곱함
  const seed = (c, heroes) => {
    const pts = c.gates.flatMap((g, k) => [g, ...(c.legs?.[k] || [])]), at = [0];
    for (let i = 1; i < pts.length; i++) at.push(at[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const gi = [];
    let k = 0;
    c.gates.forEach((g, j) => { gi.push(k); k += 1 + (c.legs?.[j]?.length || 0); });
    const now = Date.now(), DAY = 864e5;
    const runs = [[1.045, 2], [1.09, 6], [1.16, 9]].map(([slow, ago], n) => {
      const splits = gi.slice(1).map((i) => Math.round((0.7 + at[i] / 6.2 * slow) * 100) / 100);
      return { id: now - ago * DAY, at: now - ago * DAY, time: splits[splits.length - 1], splits, hero: heroes[n % heroes.length], view: 'third' };
    });
    localStorage.setItem('y97-run-records', JSON.stringify({ [c.id]: runs }));
    return runs;
  };
  // 자동으로 뛰기: 코스의 선(문과 꺾이는 점)을 차례로 겨냥한다(tools/race_route.mjs --check 와 같은 몰기: 2.5 m 안에 들면
  // 다음 점으로). 카메라는 등 뒤(orbit 0). d.s: 선을 따라 온 길이, d.dir: 달리는 쪽(부드럽게)
  const driver = (R) => {
    const { pts, at } = R.line;
    const d = { s: 0, k: 1, dir: null, t: 0, best: 0, bestT: 0 };
    d.update = (dt = DT) => {
      // 1.5 s 동안 1 m 도 못 나아가면(턱 · 벽에 걸림) 선을 따라 4 m 앞으로(건너뛰는 동안에만: 찍는 장면은 막히지 않는 곳)
      d.t += dt;
      if (d.s > d.best + 1) { d.best = d.s; d.bestT = d.t; }
      else if (d.unstick && d.t - d.bestT > 1.5) {
        const q = R.pointAt(d.s + 4);
        pl.teleport(q.x, q.y, null);
        while (d.k < pts.length - 1 && at[d.k] < d.s + 4.5) d.k++;
        d.bestT = d.t;
      }
      while (d.k < pts.length - 1 && Math.hypot(pts[d.k][0] - pl.x, pts[d.k][1] - pl.y) < 2.5) d.k++;
      const [tx, ty] = pts[d.k], left = Math.hypot(tx - pl.x, ty - pl.y);
      d.s = Math.max(d.s, at[d.k] - left);
      const want = Math.atan2(tx - pl.x, -(ty - pl.y));
      pl.heading += wrap(want - pl.heading) * Math.min(1, dt * 14);
      pl.cam.orbit = 0;
      const q = R.pointAt(d.s + 3), w = Math.min(1, dt * 2.5);
      d.dir = d.dir ? [lerp(d.dir[0], q.dx, w), lerp(d.dir[1], q.dy, w)] : [q.dx, q.dy];
      const n = Math.hypot(...d.dir) || 1; d.dir = [d.dir[0] / n, d.dir[1] / n];
    };
    return d;
  };
  // 카운트를 그 자리에 붙잡아 둠(제목 장면 동안), 놓으면 3 · 2 · 1 · 출발!
  const hold = (R) => { R.clock = 3; R.shown = 3; R.hud.big.textContent = ''; };
  const release = (R) => { R.clock = 3; R.shown = 0; };
  // 달리는 사람에 붙은 카메라: f 앞(+) · s 옆(+ 오른쪽) · h 위, 사람의 가슴 위 lookH 를 봄. dir: 달리는 쪽(캠퍼스 [x, y])
  const rig = (dir, f, s, h, look = [0, 0, 1.3]) => {
    const p = pl.pos, fx = dir[0], fz = -dir[1], rx = dir[1], rz = dir[0];     // three 의 앞 · 오른쪽
    return { pos: new V(p.x + fx * f + rx * s, p.y + h, p.z + fz * f + rz * s), look: new V(p.x + fx * look[0] + rx * look[1], p.y + look[2], p.z + fz * look[0] + rz * look[1]) };
  };
  // 게임의 카메라가 놓는 자리(player.js behindCamera)
  const behind = () => {
    const p = pl.pos, h = pl.heading, el = 0.36, dist = pl.cam.dist, back = dist * Math.cos(el), high = 1.25 + dist * Math.sin(el);
    return { pos: new V(p.x - Math.sin(h) * back, p.y + high, p.z - Math.cos(h) * back), look: new V(p.x + Math.sin(h) * 1.2, p.y + 1.45, p.z + Math.cos(h) * 1.2) };
  };
  const mixCam = (a, b, u, fa, fb) => walkCam(a.pos.clone().lerp(b.pos, u), a.look.clone().lerp(b.look, u), lerp(fa, fb, u));

  // ---------------------------------------------------------------- 백양로 직선 주로: 제목 → 카운트다운 → 달리기 … 결승
  // 0 ~ 5 s 제목(카운트를 붙잡고, 하늘에서 출발선의 성구 뒤로 내려옴), 그 뒤 3 · 2 · 1 · 출발!, 13 s 를 뜀.
  // 그다음 프레임(표시 jump)에서 결승 40 m 앞까지 한 번에 건너뛰고(프레임 저장 없이 게임만 진행), 결승 · 결과 창까지.
  const T = { title: 5, run: 13.2, after: 5.2 };
  seg.baek = {
    n: 200 * FPS,
    season: 'autumn',
    async init() {
      hud(NO_RACE_HUD);
      this.R = await begin('baekyang', 'p04');
      this.R.best = seed(this.R.course, ['p04', 'p09', 'p01'])[0];     // (기록은 시작할 때 읽으니 그 자리에 넣음)
      this.d = driver(this.R);
      for (let k = 0; k < 40; k++) { hold(this.R); step(); }
      hold(this.R);
      this.from = { pos: G(-100, -343, 30), look: G(-108, -383, 1.2) };
      this.go = null;
    },
    async step(i, t) {
      const R = this.R;
      let mark;
      if (t < T.title) {
        hold(R);
        // 북쪽 40 m · 30 m 위에서 출발선을 내려다보다 길 위로(가로수 위) 넘어가 등 뒤 게임의 카메라 자리로
        const u = smooth(t / T.title), b = behind();
        const k = smooth(clamp((t - 1.2) / (T.title - 1.2), 0, 1));
        const mid = { pos: G(-107, -404, 12), look: G(-109, -381, 1.4) };
        const a = { pos: this.from.pos.clone().lerp(mid.pos, smooth(Math.min(1, u * 1.6))), look: this.from.look.clone().lerp(mid.look, smooth(Math.min(1, u * 1.6))) };
        mixCam(a, b, k * k, 48, 66);
      } else if (!this.released) {
        this.released = true;
        pl.camOverride = null;
        I.fov(66);
        hud(RACE_HUD);
        release(R);
        key('KeyW', true);
        mark = 'count';
      }
      if (R.state === 'play') {
        if (!this.go) { this.go = t; mark = 'go'; }
        this.d.update();
      }
      // 결승 40 m 앞까지 건너뜀(이 프레임부터 영상의 결승 장면)
      if (this.go && !this.jumped && t > this.go + T.run) {
        this.jumped = true;
        const L = R.line.len;
        hud(NO_RACE_HUD);
        this.d.unstick = true;
        await untilDo(() => { this.d.update(); return this.d.s > L - 40 || R.state !== 'play'; }, 9000);
        this.d.unstick = false;
        hud(RACE_HUD);
        mark = 'jump';
      }
      const g0 = R.next;
      step();
      if (R.next !== g0 && R.state === 'play') mark = (mark ? mark + ',' : '') + 'gate';
      if (R.state === 'done' && !this.fin) { this.fin = t; mark = (mark ? mark + ',' : '') + 'fin'; key('KeyW', false); }
      if (R.state !== 'done') {
        const b = R.hud?.big?.textContent;
        if (b && b !== this.lastBig) mark = (mark ? mark + ',' : '') + (b === '출발!' ? 'gobig' : 'n' + b);
        this.lastBig = b;
      }
      // 자막
      show('scrim', 'scrim', '', t, 0, 999, { slide: 0 });
      show('title', 'title', '<b>캠퍼스 달리기</b><span>1997년 신촌 캠퍼스를 달린다</span><small>신촌 캠퍼스 1997 · 미니 게임</small>', t, 0.3, T.title - 0.2, { fade: 0.5 });
      const g = this.go ?? 1e9;
      show('c1', 'cap', '<b>백양로 직선 주로</b><span>정문에서 언더우드관 앞까지</span>', t, T.title + 0.2, g + 3.6);
      line('l1', '빛의 <i>문</i>을 차례로 지나 결승까지', t, g + 4.2, g + 8.2);
      line('l2', '바닥의 <i>화살표</i>를 따라 · 문마다 내 최고 기록과 겨루기', t, g + 8.6, g + T.run - 0.3);
      if (this.fin) {
        show('c2', 'cap', '<b>새 기록!</b><span>내 최고 기록을<br>몇 초 앞당겼을까</span>', t, this.fin + 1.6, this.fin + T.after);
        if (t > this.fin + T.after) return { done: true, mark };
      }
      return { mark, note: `${R.state} gate ${R.next} s ${this.d.s.toFixed(0)}` };
    },
  };

  // ---------------------------------------------------------------- 청송대 숲길: 숲속 길을 따라 (자동으로 4번 문 앞까지 간 뒤)
  seg.forest = {
    n: Math.round(10.5 * FPS),
    season: 'summer',
    async init(arg) {
      hud(NO_RACE_HUD);
      const R = this.R = await begin('cheongsong', 'p09');
      settle(10);
      await untilDo(() => R.state === 'play', 400);
      key('KeyW', true);
      this.d = driver(R);
      // 4번 문(숲의 길 어귀)을 지나 조금 더(카메라가 문의 빛 기둥 안에 들지 않게)
      const gate = arg?.gate ?? 4;
      this.d.unstick = true;
      await untilDo(() => { this.d.update(); return R.next > gate || R.state !== 'play'; }, 6000);
      this.d.unstick = false;
      for (let k = 0; k < 30; k++) { this.d.update(); step(); }
    },
    step(i, t) {
      this.d.update();
      // 앞에서 뒷걸음질하며(낮게, 달려오는 얼굴) | 컷 | 뒤 옆 위에서 숲길을 내려다봄
      if (t < 5) { const a = rig(this.d.dir, 5.5, -1.6, 1.2, [0, 0, 1.25]); walkCam(a.pos, a.look, 46); }
      else { const b = rig(this.d.dir, -6, 3.5, 6.5, [5, 0, 0.8]); walkCam(b.pos, b.look, 54); }
      step();
      show('scrim', 'scrim', '', t, 0, 999, { slide: 0 });
      show('c', 'cap', '<b>청송대 숲길</b><span>아펜젤러관 옆 찻길을 올라 숲의 길을 한 바퀴</span>', t, 0.4, 10.2);
      return { note: `gate ${this.R.next}` };
    },
  };

  // ---------------------------------------------------------------- 신촌 로터리에서 상대신관: 연세로를 달려 올라감
  seg.town = {
    n: Math.round(9.5 * FPS),
    season: 'spring',
    async init(arg) {
      hud(NO_RACE_HUD);
      await y.townReady;
      const R = this.R = await begin('rotary_sang', 'p01');
      settle(10);
      await untilDo(() => R.state === 'play', 400);
      key('KeyW', true);
      this.d = driver(R);
      const s0 = arg?.s ?? 40;
      await untilDo(() => { this.d.update(); return this.d.s > s0; }, 2000);
    },
    step(i, t) {
      this.d.update();
      // 찻길 위 높이에서 돌아보며(길과 가게들, 가로수 너머) | 컷 | 보도 위 앞에서 낮게
      if (t < 4.5) { const a = rig(this.d.dir, lerp(16, 12, t / 4.5), 7, 15, [-2, 0, 1.0]); walkCam(a.pos, a.look, 50); }
      else { const b = rig(this.d.dir, 6, 0.6, 1.7, [-1, 0, 1.3]); walkCam(b.pos, b.look, 50); }
      step();
      show('scrim', 'scrim', '', t, 0, 999, { slide: 0 });
      show('c', 'cap', '<b>신촌 로터리에서 상대신관</b><span>연세로를 올라 정문 · 백양로를 지나 1.5 km</span>', t, 0.4, 9.2);
      return { note: `s ${this.d.s.toFixed(0)}` };
    },
  };

  // ---------------------------------------------------------------- 끝: 코스 다섯 가지 → 제목과 주소
  const COURSES = [
    ['백양로 직선 주로', '정문 → 언더우드관 앞', '680 m'],
    ['중앙 광장 한 바퀴', '학생회관 앞에서 한 바퀴', '630 m'],
    ['청송대 숲길', '언더우드관 앞에서 숲길 한 바퀴', '700 m'],
    ['정문에서 상대신관', '백양로를 지나 상뜰까지', '920 m'],
    ['신촌 로터리에서 상대신관', '연세로 · 정문 · 백양로', '1.5 km'],
  ];
  seg.end = {
    n: Math.round(12 * FPS),
    season: 'autumn',
    async init() {
      toBird();
      hud('none');
      await ensure(-60, -200);
      this.at(0);
      settle(90);
    },
    at(t) {
      // 정문 위에서 백양로를 따라 천천히 올라감
      const u = t / 12;
      birdCam(lerp(-128, -112, u), lerp(-470, -420, u), lerp(70, 64, u), lerp(-40, -25, u), lerp(-120, -60, u), 30, 44);
    },
    step(i, t) {
      this.at(t);
      step();
      show('shade', 'shade', '', t, 0.2, 999, { slide: 0, fade: 0.6 });
      const list = COURSES.map(([n, s, l]) => `<li><b>${n}</b>${s} <small style="display:inline;margin-left:14px">${l}</small></li>`).join('');
      show('p1', 'pg', `<h2>코스 다섯 가지</h2><ul>${list}</ul>`, t, 0.4, 6.2);
      show('p2', 'title', '<b>캠퍼스 달리기</b><span>신촌 캠퍼스 1997 · 미니 게임</span><small>yonsei-1997.benelog.net</small>', t, 6.6, 99, { fade: 0.6 });
    },
  };
})();
