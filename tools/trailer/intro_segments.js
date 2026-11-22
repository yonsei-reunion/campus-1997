// 소개 영상의 장면들 (tools/trailer/intro_page.js 뒤에 넣는다). 장면 이름 = 출력 폴더 이름.
// 순서와 자르는 곳은 intro_video.py 가 정한다. 여기서는 장면마다 카메라 · 자막 · 게임 조작만.
(() => {
  const I = window.__iv, y = window.__y97, pl = y.player, cam = y.camera;
  const { seg, show, line, key, tag, hud, toWalk, toBird, birdCam, walkCam, season, ensure, spline, step, settle, ground, P, G, V, sleep, smooth, lerp, clamp, FPS, DT, $ } = I;
  const mix = (a, b, u) => a.map((v, k) => lerp(v, b[k], u));

  // ---------------------------------------------------------------- 신촌 로터리 → 연세로 → 정문 → 백양로 → 독수리상 (날아가기)
  // 독수리상을 가까이서 한 바퀴 돈 뒤 땅으로 내려와 성구(상경대학)의 뒤, 걷는 화면의 카메라 자리로. 내려오기 시작할 때
  // 걷기 화면으로 바꾼다(성구가 그 자리에 서 있게). 카메라는 내려온 끝에서 게임의 카메라(player.js behindCamera)와 같은
  // 자리 · 시야각이라, 놓아주면 그대로 이어진다
  const EAGLE = [-67.95, -161.78];
  const ROAD = [0.242, 0.970];                                       // 백양로의 방향(북쪽으로)
  const FLY = { A: 14, B: 8.5, C: 3.6, D: 4.2 };                    // 날아가기 · 한 바퀴 · 내려오기 · 걷기 (s)
  seg.fly = {
    n: Math.round((FLY.A + FLY.B + FLY.C + FLY.D) * FPS),
    async init() {
      await y.townReady;
      toBird();
      hud('none');
      const E = EAGLE, n = ROAD;
      this.gE = ground(...E);
      this.R = 14;                                                   // 도는 반지름 m
      this.eh = this.gE + 10;                                        // 도는 높이(단 0.4 + 탑신 8.5 m 위의 독수리)
      this.eye = [E[0], E[1], this.gE + 10.4];                        // 독수리의 몸
      const O = [E[0] - n[0] * this.R, E[1] - n[1] * this.R];       // 남쪽(정면)에서 돌기 시작
      // 정문을 넘어 백양로 위로는 땅 위 높이로 적음
      const rel = (x, yy, dh) => [x, yy, ground(x, yy) + dh];
      const pts = [[-52, -1068, 60], [-84, -1004, 49], [-98, -915, 40], [-97, -785, 36], [-96, -665, 36], [-97, -565, 38], [-99, -487, 38],
        rel(-103, -432, 10), rel(-101, -384, 10.5), rel(-93, -318, 12), rel(-84, -262, 14), rel(-77, -214, 13.5), [O[0], O[1], this.eh]];
      // 곡선의 길이로 고르게(점 사이의 거리가 달라도 빠르기가 튀지 않게)
      const K = 600, P3 = [], S = [0];
      for (let k = 0; k <= K; k++) { P3.push(spline(pts, k / K)); if (k) S.push(S[k - 1] + Math.hypot(...P3[k].map((v, j) => v - P3[k - 1][j]))); }
      this.L = S[K];
      this.along = (d) => { d = clamp(d, 0, this.L); let a = 0, b = K; while (b - a > 1) { const m = (a + b) >> 1; if (S[m] <= d) a = m; else b = m; } const f = (d - S[a]) / Math.max(1e-6, S[b] - S[a]); return mix(P3[a], P3[b], f); };
      // 빠르기: 1.5 초에 걸쳐 오르고, 끝 4.5 초에 걸쳐 0 으로 내려앉음
      const NA = Math.round(FLY.A * FPS), D = [0];
      const v = (t) => Math.min(smooth(t / 1.5), smooth((FLY.A - t) / 4.5));
      for (let k = 1; k <= NA; k++) D.push(D[k - 1] + v((k - 0.5) / FPS));
      this.dist = (t) => { const f = clamp(t * FPS, 0, NA), k = Math.min(NA - 1, Math.floor(f)); return this.L * lerp(D[k], D[k + 1], f - k) / D[NA]; };
      // 성구: 독수리상 남쪽 15 m 에서 북쪽(독수리상)을 봄
      this.S = [E[0] - n[0] * 15, E[1] - n[1] * 15];
      this.at(0);
      settle(60);
    },
    // 게임의 카메라가 성구 뒤에 놓는 자리(player.js behindCamera: dist 5.4, 올려 본 각 0.36)
    behind() {
      const p = pl.pos, h = pl.heading, el = 0.36, dist = pl.cam.dist;
      const back = dist * Math.cos(el), high = 1.25 + dist * Math.sin(el);
      return { pos: new V(p.x - Math.sin(h) * back, p.y + high, p.z - Math.cos(h) * back), look: new V(p.x + Math.sin(h) * 1.2, p.y + 1.45, p.z + Math.cos(h) * 1.2) };
    },
    orbit(u) {
      const n = ROAD, a0 = Math.atan2(-n[1], -n[0]), a = a0 + 2 * Math.PI * smooth(u);
      return [EAGLE[0] + Math.cos(a) * this.R, EAGLE[1] + Math.sin(a) * this.R, this.eh + 0.6 * Math.sin(Math.PI * u)];
    },
    at(t) {
      if (t < FLY.A) {
        const d = this.dist(t), s = d / this.L;
        const p = this.along(d), a = this.along(d + 130);
        let look = [a[0], a[1], ground(a[0], a[1]) + 2];
        // 처음에는 로터리 건너 그랜드백화점을 봄
        look = mix(look, [-150, -975, 40], 0.85 * smooth(1 - d / 85));
        // 창천교회 쪽으로 잠깐 고개를 돌림
        const k = 0.42 * smooth(1 - Math.abs(p[1] + 640) / 110);
        look = mix(look, [-34, -533, 36], k);
        // 백양로 위에서는 독수리상을 봄
        look = mix(look, this.eye, smooth((p[1] + 330) / 120));
        birdCam(p[0], p[1], p[2], look[0], look[1], look[2], lerp(52, 46, smooth(s)));
        return;
      }
      const q = this.orbit(clamp((t - FLY.A) / FLY.B, 0, 1));
      birdCam(q[0], q[1], q[2], ...this.eye, 46);
    },
    async step(i, t) {
      if (t < FLY.A + FLY.B) { this.at(t); step(); }
      else {
        if (!this.walking) {
          // 걷기 화면으로: 성구를 독수리상 남쪽에 세움(카메라는 돌던 자리 그대로 이어 받음)
          this.walking = true;
          const q = this.orbit(1);
          this.from = { pos: P(q[0], q[1], q[2]), look: P(this.eye[0], this.eye[1], this.eye[2]) };
          await toWalk('p04', '독수리상');
          hud('none');
          await ensure(...this.S);
          pl.teleport(...this.S, null);
          pl.heading = Math.atan2(ROAD[0], -ROAD[1]);
          pl.actor.holder.rotation.y = pl.heading;
          walkCam(this.from.pos.clone(), this.from.look.clone(), 46);
          settle(20);
          this.to = this.behind();
        }
        const u = (t - FLY.A - FLY.B) / FLY.C;
        if (u < 1) {
          const k = smooth(u);
          // 내려오며 뒤로: 높이는 처음에 천천히, 끝에서 빨리 내려앉지 않게 같은 곡선으로
          walkCam(this.from.pos.clone().lerp(this.to.pos, k), this.from.look.clone().lerp(this.to.look, k), lerp(46, 66, k));
        } else if (pl.camOverride) {
          pl.camOverride = null;                                     // 게임의 카메라로(같은 자리에서 이어짐)
          I.fov(66);
        }
        if (u > 1.08 && !this.go) { this.go = true; key('KeyW', true); }
        step();
      }
      show('scrim', 'scrim', '', t, 0, 999, { slide: 0 });
      show('title', 'cap', '<b>신촌 캠퍼스 1997</b><span>1997년의 연세대학교 신촌 캠퍼스를 걷는 웹 3D 게임</span>', t, 0.5, 5.2);
      tag('grand', P(-168, -992, 60), '그랜드백화점', t, 0.3, 3.4);
      tag('grace', P(-186, -885, 79), '그레이스백화점', t, 0.9, 3.6);
      tag('hongik', P(-83.1, -909.3, 41), '홍익문고', t, 1.6, 4.8);
      tag('church', P(-30.3, -533.1, 52), '창천교회', t, 5.0, 8.0);
      tag('gate', P(-105.05, -395.96, 34), '정문', t, 8.0, 10.4);
      line('road', '신촌 로터리에서 연세로를 따라 <i>정문</i>으로, 백양로를 따라 <i>독수리상</i>까지', t, 5.8, FLY.A - 0.6);
      show('eagle', 'cap', '<b>독수리상</b><span>높은 기둥 위에서 정문 쪽 백양로를 내려다보는</span>', t, FLY.A + 0.4, FLY.A + FLY.B - 0.5);
      const t3 = FLY.A + FLY.B + FLY.C;
      show('hero', 'cap', '<b>성구 <i style="font-size:.62em">상경대학</i></b><span>주인공이 되어 1997년의 캠퍼스를 걷습니다</span>', t, t3 - 0.6, t3 + FLY.D);
      if (i === this.n - 1) key('KeyW', false);
    },
  };

  // ---------------------------------------------------------------- 썸네일: 5월의 언더우드관 (영상에는 넣지 않음, --seg thumb)
  // tools/snapshots.json anthology/underwood(언더우드 동상 뒤에서 정원 축을 따라)를 조금 높고 넓게
  seg.thumb = {
    n: 1,
    extra: true,
    season: 'summer',                                                // 5월 · 신록
    async init() {
      toBird();
      hud('none');
      const g = ground(48.4, 192.7), q = { x: 47.6, y: 186.5, h: g + 11, tx: 60.25, ty: 239.9, th: ground(60.25, 239.9) + 3, fov: 56 };
      await ensure(q.tx, q.ty);
      await ensure(q.x, q.y);
      birdCam(q.x, q.y, q.h, q.tx, q.ty, q.th, q.fov);
      settle(90);
    },
    step(i, t) {
      step();
      show('scrim', 'scrim', '', 1, 0, 9, { slide: 0, fade: 0.01 });
      show('title', 'cap', '<b>신촌 캠퍼스 1997</b><span>1997년의 연세대학교를 다시 걷는 웹 3D 게임</span>', 1, 0, 9, { slide: 0, fade: 0.01 });
    },
  };

  // ---------------------------------------------------------------- 정문 동쪽 담의 대자보
  // 담은 정문의 틀(u: 정문 줄을 따라 동쪽, v: 북쪽)에서 u 12.2 ~ 20.1, v -0.4 ~ -3.3 (web/src/posters.js WALL)
  const GATE = { pos: [-105.05, -395.96], rot: -0.24434609527920614 };
  const gate = (u, v) => [GATE.pos[0] + u * Math.cos(GATE.rot) - v * Math.sin(GATE.rot), GATE.pos[1] + u * Math.sin(GATE.rot) + v * Math.cos(GATE.rot)];
  seg.posters = {
    n: 6 * FPS,
    async init() {
      await toWalk();
      hud('none');
      await ensure(...GATE.pos);
      pl.teleport(...gate(4, -16), null);
      pl.actor.holder.visible = false;
      this.at(0);
      settle(60);
    },
    at(t) {
      const u = smooth(t / (this.n / FPS));
      const a = gate(lerp(13.5, 17.2, u), lerp(-10.5, -8.2, u)), b = gate(lerp(15.2, 18.6, u), -3.3);
      walkCam(G(a[0], a[1], 1.55), G(b[0], b[1], 1.5), 44);
    },
    step(i, t) {
      this.at(t);
      step();
      show('scrim', 'scrim', '', t, 0, 99, { slide: 0 });
      show('c', 'cap', '<b>정문 담의 대자보</b><span>1997년 그 계절의 이야기를 붓글씨로</span>', t, 0.4, 5.7);
    },
  };

  // ---------------------------------------------------------------- 4월: 벚꽃잎이 흩날림
  seg.spring = {
    n: 6.4 * FPS,
    season: 'spring',
    cut: 2.6, tele: 21,
    async init(arg) {
      if (arg?.tele) this.tele = arg.tele;
      await toWalk();
      hud('none');
      await ensure(-14, 150);
      pl.teleport(-14, 150, null);
      pl.actor.holder.visible = false;
      this.at(0);
      settle(90);
    },
    at(t) {
      const u = t / (this.n / FPS);
      // 벚꽃잎 카펫이 가장 짙은 벚나무 줄(스팀슨관 서쪽 길가) 아래의 보도를 따라
      if (t < this.cut) walkCam(G(lerp(-15, -12, u * 2), lerp(150.4, 149.4, u * 2), 1.35), G(10, 142, lerp(2.0, 2.3, u * 2)), 42);
      // 그리고 망원으로 낮게: 꽃잎(3 cm)이 화면에서 크게 보이는 거리
      else { const v = (t - this.cut) / (this.n / FPS - this.cut); walkCam(G(lerp(-11.5, -10.6, v), lerp(149.2, 148.9, v), 0.85), G(8.5, 141.6, 1.25), this.tele); }
    },
    step(i, t) {
      this.at(t);
      step();
      show('scrim', 'scrim', '', t, 0, 99, { slide: 0 });
      show('c', 'cap', '<b>4월, 벚꽃</b><span>꽃잎이 바람에 흩날리는 봄의 캠퍼스</span>', t, 0.4, 6.1);
    },
  };

  // ---------------------------------------------------------------- 10월: 백양로의 은행잎
  seg.autumn = {
    n: 6 * FPS,
    season: 'autumn',
    async init() {
      await toWalk();
      hud('none');
      await ensure(-84, -308);
      pl.teleport(-84, -308, null);
      pl.actor.holder.visible = false;
      this.at(0);
      settle(90);
    },
    at(t) {
      const u = t / (this.n / FPS);
      // 백양로 동쪽 보도를 따라 북쪽으로 (길의 방향: (0.242, 0.970))
      const s = lerp(0, 9, u), x0 = -76.3, y0 = -318;
      walkCam(G(x0 + 0.242 * s, y0 + 0.97 * s, 1.5), G(x0 + 0.242 * 60 - 3, y0 + 0.97 * 60, 4.5), 48);
    },
    step(i, t) {
      this.at(t);
      step();
      show('scrim', 'scrim', '', t, 0, 99, { slide: 0 });
      show('c', 'cap', '<b>10월, 단풍</b><span>은행잎이 내려앉는 백양로와 연고전 현수막</span>', t, 0.4, 5.7);
    },
  };

  // ---------------------------------------------------------------- 주인공 열세 명, 저마다의 단과대 앞에서
  // back: 출발지(현관 앞)에서 건물 반대쪽으로 물러선 거리 m. at · to: 따로 정한 자리와 등 뒤에 둘 건물 쪽의 점
  const HEROES = [
    { id: 'p01', name: '승민', college: '공과대학', place: '제1공학관', back: 12 },
    { id: 'p11', name: '서연', college: '음악대학', place: '음악대학', back: 12 },
    { id: 'p04', name: '성구', college: '상경대학', place: '상대신관', back: 22, lh: 3.5 },
    { id: 'p09', name: '지은', college: '문과대학', place: '인문관', back: 7 },
    { id: 'p02', name: '성훈', college: '이과대학', place: '과학관', back: 12 },
    { id: 'p13', name: '은정', college: '사회과학대학', place: '연희관', back: 12 },
    { id: 'p06', name: '준호', college: '법과대학', place: '광복관', back: 2, dist: 6, fov: 50, lh: 4 },
    { id: 'p10', name: '지영', college: '교육과학대학', place: '용재관', at: [62, 131], to: [98, 116], fov: 50, lh: 4.5 },
    { id: 'p12', name: '수진', college: '생활과학대학', place: '가정관', back: 12 },
    { id: 'p03', name: '동현', college: '의과대학', place: '의과대학', back: 30, dist: 6, fov: 50, lh: 4 },
    { id: 'p15', name: '혜진', college: '간호대학', place: '간호대학', at: [396, -18], to: [360, -32], dist: 6, fov: 50, lh: 4.5 },
    { id: 'p16', name: '정우', college: '신과대학', place: '아펜젤러관', back: 12 },
    { id: 'p17', name: '현정', college: '치과대학', place: '치과대학', back: 12 },
  ];
  const HERO_T = 2.3, PICK_T = 3.2;
  seg.heroes = {
    n: Math.round((PICK_T + HEROES.length * HERO_T) * FPS),
    async init(arg) {
      // (제목 화면의 카드는 CSS 화면 720 보다 길다: 줄여서 다 보이게)
      hud(`#hud > *, #toast, #birdpins, #tourbar, #birdbar { display: none !important; } #intro .intro-card { zoom: .76; margin-bottom: 60px; }`);
      this.k = -1;
      this.list = arg?.only ? HEROES.filter((h) => arg.only.includes(h.id)).map((h) => ({ ...h, ...(arg.set || {}) })) : HEROES;
      this.n = Math.round((PICK_T + this.list.length * HERO_T) * FPS);
    },
    // k 번째 주인공을 제 단과대 앞에 세움
    async stage(k) {
      const h = this.list[k];
      await toWalk(h.id);
      if (h.at) { pl.teleport(h.at[0], h.at[1], null); pl.heading = Math.atan2(h.to[0] - h.at[0], -(h.to[1] - h.at[1])); }
      const h0 = pl.heading, fx = Math.sin(h0), fz = Math.cos(h0);       // 건물 쪽
      if (h.back) pl.teleport(pl.pos.x - fx * h.back, -(pl.pos.z - fz * h.back), null);
      pl.heading = h0 + Math.PI;                                         // 건물을 등짐
      pl.actor.holder.rotation.y = pl.heading;
      await ensure(pl.x, pl.y);
      const p = pl.pos.clone(), dist = h.dist ?? 5, side = 0.9;
      this.shot = (u) => {
        const d = dist - 0.45 * u;
        // (주인공은 화면 오른쪽에, 자막은 왼쪽 아래에)
        walkCam(new V(p.x - fx * d + fz * side, p.y + 1.3, p.z - fz * d - fx * side), new V(p.x + fx * 6 + fz * 1.5, p.y + (h.lh ?? 3.2), p.z + fz * 6 - fx * 1.5), h.fov ?? 46);
      };
      this.shot(0);
      settle(40);
    },
    async step(i, t) {
      if (t < PICK_T) {
        // 제목 화면의 주인공 고르기
        if (i === 0) { if ($('#intro').hidden) y.toTitle(); $('#hero-pick button[data-id=p01]').click(); settle(20); }
        const pick = HEROES[Math.min(HEROES.length - 1, Math.floor((t - 0.5) / ((PICK_T - 0.8) / HEROES.length)))];
        if (t > 0.5 && pick && this.picked !== pick.id) { this.picked = pick.id; $(`#hero-pick button[data-id=${pick.id}]`).click(); }
        step();
        line('pick', '주인공은 <i>단과대마다 한 명</i>, 모두 열세 명', t, 0.3, PICK_T - 0.2);
        return;
      }
      line('pick', '', t, 0, 0);
      const k = Math.min(this.list.length - 1, Math.floor((t - PICK_T) / HERO_T)), u = (t - PICK_T - k * HERO_T) / HERO_T;
      if (k !== this.k) { this.k = k; await this.stage(k); }
      this.shot(u);
      step();
      const h = this.list[k], t0 = PICK_T + k * HERO_T;
      show('scrim', 'scrim', '', t, PICK_T, 999, { slide: 0, fade: 0.01 });
      show('h' + k, 'cap', `<b>${h.name} <i style="font-size:.62em">${h.college}</i></b><span>${h.place} 앞에서 출발</span>`, t, t0 + 0.04, t0 + HERO_T - 0.16, { fade: 0.16, slide: 10 });
      show('chip', 'chip', '주인공 열세 명', t, PICK_T, 999, { slide: 0, fade: 0.2 });
      return { mark: u < DT / HERO_T ? h.id : undefined };
    },
  };

  // ---------------------------------------------------------------- 활천대: 생일인 친구를 분수에 (web/src/birthday.js)
  // tools/trailer/birthday.mjs 의 장면에서 사진 전환을 뺀 것. 상태가 바뀔 때마다 mark 를 남겨 intro_video.py 가 자른다
  seg.birthday = {
    n: 0,
    async init() {
      await toWalk('p01', '활천대');
      hud('bubbles');
      const bd = (this.bd = y.birthday);
      bd.reset();
      bd.noCamera = true;
      const F = bd.F, C = bd.C, h0 = F.h;
      const R = (a, r, dh) => { const t = a * Math.PI / 180; return new V(C.x + Math.cos(t) * r, h0 + dh, C.z - Math.sin(t) * r); };
      const at = (base, rad, tan, dh) => base.clone().addScaledVector(bd.rad, rad).addScaledVector(bd.tan, tan).setY(h0 + dh);
      const S = bd.spot, M = bd.mid;
      this.SHOT = {
        approach: { pos: at(S, 4.4, 0.0, 1.6), look: at(S, -0.6, 0.7, 1.05), fov: 50 },
        side: { pos: at(M, 3.7, 0.35, 1.45), look: at(M, -0.9, 0.1, 0.8), fov: 44 },
        throw: { pos: at(M, 4.3, 0.9, 1.75), look: at(M, -1.9, 0.1, 0.9), fov: 46 },
        water: { pos: at(S, 2.9, 0.15, 2.25), look: at(bd.land, 0, 0, 0.75), fov: 46 },
        back: { pos: at(S, 4.0, 0.2, 1.6), look: at(S, -0.6, 0.1, 1.05), fov: 44 },
        sky: { pos: new V(-79.85, h0 + 15, 235.43), look: new V(-79.45, h0, 201.43), fov: 46 },
      };
      const hero = (this.hero = pl.actor);
      this.route = [R(-40, 5.6, 0), at(S, 0.55, 2.7, 0)];
      const start = R(-25, 8.5, 0);
      pl.teleport(start.x, -start.z, 0);
      hero.heading = Math.atan2(this.route[0].x - start.x, this.route[0].z - start.z);
      pl.heading = hero.heading;
      hero.holder.rotation.y = hero.heading;
      pl.scripted = true;
      const g = this.SHOT.approach;
      this.cam = { pos: g.pos.clone(), look: g.look.clone(), fov: g.fov, vp: new V(), vl: new V(), vf: 0 };
      this.st = { leg: 0, said: null, acted: null, slow: 1, last: '', T: 0 };
      walkCam(this.cam.pos, this.cam.look, this.cam.fov);
      settle(45);
    },
    spring(goal, w, h) {
      const c = this.cam, a = new V();
      a.copy(goal.pos).sub(c.pos).multiplyScalar(w * w).addScaledVector(c.vp, -2 * w);
      c.vp.addScaledVector(a, h); c.pos.addScaledVector(c.vp, h);
      a.copy(goal.look).sub(c.look).multiplyScalar(w * w).addScaledVector(c.vl, -2 * w);
      c.vl.addScaledVector(a, h); c.look.addScaledVector(c.vl, h);
      c.vf += ((goal.fov - c.fov) * w * w - 2 * w * c.vf) * h; c.fov += c.vf * h;
    },
    step(i, t) {
      const bd = this.bd, st = this.st, hero = this.hero, SHOT = this.SHOT;
      // 놓기 직전부터 물보라가 가라앉을 때까지는 게임의 시간을 늦춤
      let want = 1;
      if ((bd.state === 'swing' && bd.st > 1.86) || bd.state === 'fly' || (bd.state === 'water' && bd.st < 0.55)) want = 0.45;
      st.slow += (want - st.slow) * (want < st.slow ? 0.35 : 0.12);
      const dt = st.slow / FPS;
      if (!st.acted) {
        const wp = this.route[Math.min(st.leg, 1)];
        if (bd.walk(hero, wp, dt, 1.55) || (st.leg < 1 && hero.holder.position.distanceTo(wp) < 0.5)) st.leg++;
        if (st.leg > 1) bd.turn(hero, Math.atan2(bd.b.holder.position.x - hero.holder.position.x, bd.b.holder.position.z - hero.holder.position.z), dt, 5);
        hero.holder.position.y = pl.groundAt(hero.holder.position.x, hero.holder.position.z) ?? hero.holder.position.y;
        pl.heading = hero.heading;
        hero.mixer.update(dt);
      }
      const marks = [];
      if (bd.said && st.said === null) { st.said = t; marks.push('said'); }
      if (st.said !== null && !st.acted && t >= st.said + 2.0) { st.acted = bd.action() ? t : null; if (st.acted) marks.push('action'); }
      if (bd.state !== st.last) { marks.push(bd.state); st.last = bd.state; }
      let goal;
      if (!st.acted) goal = SHOT.approach;
      else {
        const s = bd.state;
        goal = s === 'gather' || s === 'take' || s === 'lift' ? SHOT.side
          : s === 'swing' ? (bd.st > 1.7 ? SHOT.throw : SHOT.side)
          : s === 'fly' ? SHOT.throw
          : s === 'water' ? (bd.st > 0.9 ? SHOT.water : SHOT.throw)
          : s === 'stand' || s === 'wade' ? SHOT.water
          : s === 'climb' || (s === 'back' && bd.st < 3.0) ? SHOT.back
          : SHOT.sky;
      }
      this.spring(goal, goal === SHOT.sky ? 1.1 : 3.2, DT);
      walkCam(this.cam.pos, this.cam.look, this.cam.fov);
      step(dt);
      show('scrim', 'scrim', '', t, 0, 999, { slide: 0 });
      show('chip', 'chip', '활천대', t, 0, 999, { slide: 0 });
      show('c', 'cap', '<b>생일인 친구는 분수에</b><span>독수리상 옆 활천대에 다가가면 생일 축하가 시작됩니다</span>', t, 0.3, 999);
      const done = (bd.state === 'back' && bd.st > 2.6) || bd.state === 'rest' || t > 60;
      return { mark: marks.join(',') || undefined, done, note: `${bd.state} ${bd.st.toFixed(2)}` };
    },
  };

  // ---------------------------------------------------------------- 대강당 앞 농구장: 공을 주워 슛 (web/src/hoops.js)
  seg.court = {
    n: 0,
    async init() {
      await toWalk('p01', '농구장');
      hud('play');
      await y.loadBall();
      const B = (this.B = y.ball);
      const b = B.balls.find((q) => q.state === 'ground') || B.balls[0];
      const c = new V(42.03, 0, -60.45);                              // 코트 가운데
      const hoop = B.hoops.slice().sort((p, q) => p.rim.distanceTo(pl.pos) - q.rim.distanceTo(pl.pos))[0];
      const d = new V(c.x - hoop.rim.x, 0, c.z - hoop.rim.z).normalize();
      const put = (o, r, side = 0) => { const x = hoop.rim.x + d.x * r - d.z * side, z = hoop.rim.z + d.z * r + d.x * side; return [x, z, pl.groundAt(x, z, 400) ?? pl.pos.y]; };
      const [bx, bz, bg] = put(0, 4.4);
      b.pos.set(bx, bg + (b.pos.y - (pl.groundAt(b.pos.x, b.pos.z, 400) ?? b.pos.y)), bz);
      b.vel?.set(0, 0, 0);
      const [px, pz] = put(0, 6.3);
      pl.teleport(px, -pz, Math.atan2(hoop.rim.x - px, hoop.rim.z - pz) - Math.PI);
      this.hoop = hoop;
      // 주인공의 오른쪽 뒤에서 골대까지
      const [cx, cz, cg] = put(0, 8.9, 2.5);
      this.camA = { pos: new V(cx, cg + 1.75, cz), look: new V(hoop.rim.x + d.x * 3.0, hoop.rim.y - 1.0, hoop.rim.z + d.z * 3.0) };
      walkCam(this.camA.pos, this.camA.look, 46);
      this.st = { phase: 'near', t0: 0 };
      settle(60);
    },
    step(i, t) {
      const B = this.B, st = this.st, marks = [];
      const go = (ph) => { st.phase = ph; st.t0 = t; marks.push(ph); };
      if (st.phase === 'near' && t > 1.3) { B.action(); go('pick'); }
      else if (st.phase === 'pick' && B.mine && !B.pick && t > st.t0 + 0.4) go('hold');
      else if (st.phase === 'hold' && t > st.t0 + 0.9) { B.press(); go('press'); }
      else if (st.phase === 'press' && B.shot && B.shot.tr === null && B.shot.t >= 0.62 - DT * 0.5) { B.letGo(); go('shot'); }
      else if (st.phase === 'shot' && t > st.t0 + 3.4) go('end');
      walkCam(this.camA.pos, this.camA.look, 46);
      step();
      show('scrim', 'scrim', '', t, 0, 999, { slide: 0 });
      show('chip', 'chip', '대강당 앞 농구장', t, 0, 999, { slide: 0 });
      show('c', 'cap', '<b>공을 주워 슛</b><span>꾹 눌렀다가 막대가<br>초록 칸에 올 때 떼기</span>', t, 0.3, 999);
      return { mark: marks.join(',') || undefined, done: st.phase === 'end' || t > 30, note: st.phase };
    },
  };

  // ---------------------------------------------------------------- 캠퍼스 쪽지 (web/src/memos.js)
  // 녹화용 쪽지: 실제 서버에 닿지 않는다(intro.mjs 가 가로챔). 글은 지어낸 것
  const MEMO_TEXT = '재상봉 때 여기서 다시 만나요!', MEMO_NAME = '문과97';
  const MEMO_LIST = [
    { text: '잔디밭에서 짜장면 시켜 먹던 날, 기억나?', name: '상경97', color: 'mint', at: [-60, -150], place: '독수리상' },
    { text: '도서관 4층 창가 자리는 아직 그대로일까', name: '이과97', color: 'blue', at: [-30, -80], place: '중앙도서관' },
    { text: '농구 한 판 하고 갑니다', name: '공대97', color: 'orange', at: [45, 52], place: '농구장' },
    { text: '아카라카 때 노천극장에서 목이 다 쉬었지', name: '사과97', color: 'pink', at: [170, 80], place: '노천극장' },
    { text: '정문 앞에서 기다린다던 그 친구, 잘 지내니?', name: '', color: 'yellow', at: [-108, -380], place: '정문' },
  ];
  seg.memo = {
    n: 0,
    async init() {
      await toWalk('p09', '중앙도서관');
      hud('cards');
      // 도서관 쪽으로 걸어 들어가 기둥 앞 3 m 안에(쪽지가 벽 · 기둥에 붙는 거리)
      const h = pl.heading;
      pl.teleport(pl.pos.x + Math.sin(h) * 9.5, -(pl.pos.z + Math.cos(h) * 9.5), null);
      const M = (this.M = y.memos);
      const now = Date.now();
      const stamp = (ms) => new Date(now - ms).toISOString().slice(0, 19).replace('T', ' ');
      window.__ivMemos = MEMO_LIST.map((m, k) => ({ id: `feed${k}c0ffee`, text: m.text, name: m.name, color: m.color, x: m.at[0], y: m.at[1], z: ground(m.at[0], m.at[1]) + 1.3,
        yaw: 0.4 * k, kind: 'stake', place: m.place, created_at: stamp((k + 1) * 5.3 * 3600e3) }));
      M._sync(window.__ivMemos.map((r) => ({ ...r })));
      M._changed();
      this.st = { phase: 'stand', t0: 0, typed: 0 };
      settle(60);
    },
    step(i, t) {
      const M = this.M, st = this.st, marks = [];
      const go = (ph) => { st.phase = ph; st.t0 = t; marks.push(ph); };
      const u = t - st.t0;
      const w = $('#memo-write'), ta = w.querySelector('textarea');
      if (st.phase === 'stand' && u > 1.4) { M.openWrite(); go('write'); }
      else if (st.phase === 'write') {
        // 한 글자씩
        const n = clamp(Math.floor((u - 0.7) / 0.13), 0, MEMO_TEXT.length);
        if (n !== st.typed) { st.typed = n; ta.value = MEMO_TEXT.slice(0, n); ta.dispatchEvent(new Event('input', { bubbles: true })); }
        if (u > 0.7 + MEMO_TEXT.length * 0.13 + 0.3) w.querySelector('.memo-name').value = MEMO_NAME;
        if (u > 0.7 + MEMO_TEXT.length * 0.13 + 1.1) { w.querySelector('.ok').click(); go('posted'); }
      } else if (st.phase === 'posted' && u > 0.5 && u <= 2.6) {
        // 붙은 쪽지로 다가감
        const n = M.list.find((q) => q.text === MEMO_TEXT);
        if (n) {
          const fx = Math.sin(n.yaw), fy = Math.cos(n.yaw), k = smooth((u - 0.5) / 1.3);
          const from = this.from ?? (this.from = { pos: cam.position.clone(), look: new V(n.x, n.z - 0.2, -n.y) });
          const to = new V(n.x + fx * 1.5 - fy * 0.45, n.z + 0.05, -(n.y + fy * 1.5 + fx * 0.45));
          walkCam(from.pos.clone().lerp(to, k), new V(n.x, n.z - 0.2, -n.y), 46);
        }
      } else if (st.phase === 'posted' && u > 2.6) {
        const n = M.list.find((q) => q.text === MEMO_TEXT);
        if (n) M.read(n);
        go('read');
      } else if (st.phase === 'read' && u > 2.8) { M.closeAll(); M.openList(); go('list'); }
      else if (st.phase === 'list' && u > 3.6) go('end');
      step();
      show('chip', 'chip', '캠퍼스 쪽지', t, 0, 999, { slide: 0 });
      const say = { stand: '<span class="key">N</span> 을 누르면 <i>그 자리에 쪽지</i>를 남깁니다', write: '<span class="key">N</span> 을 누르면 <i>그 자리에 쪽지</i>를 남깁니다',
        posted: '앞의 벽이나 기둥에 <i>포스트잇처럼</i> 붙습니다', read: '누구나 쓰고, <i>누구나 읽습니다</i>', list: '쪽지 목록에서 읽고, <i>붙은 곳으로</i> 갑니다' };
      for (const k of ['stand', 'posted', 'read', 'list']) {
        const on = st.phase === k || (k === 'stand' && st.phase === 'write');
        if (on && this.on !== k) { this.on = k; this.onT = t; }
        line('m-' + k, say[k], this.on === k ? t : -1, (this.onT ?? 0) + 0.1, 999);
      }
      return { mark: marks.join(',') || undefined, done: st.phase === 'end' || t > 40, note: st.phase };
    },
  };

  // ---------------------------------------------------------------- 미니 게임 일곱 가지
  // 게임마다 제목 화면에서 그 버튼을 눌러 시작한다(실제 들어가는 길 그대로). begin: 찍기 전의 준비(코스 창이 뜰 때까지,
  // 카운트다운을 넘길 때까지 프레임을 저장하지 않고 진행), tick(u): 그 게임의 u 초째에 할 조작
  const untilDo = async (ok, max = 600) => { for (let k = 0; k < max && !ok(); k++) { step(); if (k % 6 === 5) await sleep(0); } return ok(); };
  const shown = (sel) => { const e = $(sel); return !!e && !e.hidden && getComputedStyle(e).display !== 'none'; };
  const waitFor = async (ok, ms = 8000) => { for (let k = 0; k < ms / 50 && !ok(); k++) await sleep(50); return ok(); };
  const GAME_T = 3.5;
  const GAMES = [
    { key: 'shoot', name: '농구 1분 슛 게임', sub: '1분 동안 몇 골을<br>넣는지 겨루기',
      async begin() { $('#shoot-start').click(); await waitFor(() => !!y.shootout); await untilDo(() => y.shootout?.state === 'play' && !!y.ball?.mine && !y.ball?.pick); },
      tick(u) {
        const B = y.ball;
        if (!B) return;
        if (B.mine && !B.shot && u > (this.next ?? 0.25)) { B.press(); this.next = u + 1.3; }
        else if (B.shot && B.shot.tr === null && B.shot.t >= 0.62 - DT * 0.5) B.letGo();
      } },
    { key: 'run', name: '캠퍼스 달리기', sub: '코스를 골라<br>달리며 기록 겨루기',
      async begin() { $('#run-start').click(); await waitFor(() => shown('#racepick')); settle(8); },
      async tick(u) {
        if (u > 1.2 && !this.go) { this.go = true; $('#racepick button').click(); await waitFor(() => $('#intro').hidden && y.race?.on, 8000); await untilDo(() => y.race.state === 'play'); key('KeyW', true); }
      },
      end() { key('KeyW', false); } },
    { key: 'photo', name: '이곳은 어디?', sub: '옛 사진을 찍은<br>자리를 찾아가기',
      async begin() { $('#photo-start').click(); await waitFor(() => shown('#pqhud') || !!y.quiz?.on); settle(20); },
      tick(u) { if (u > 0.3 && !this.go) { this.go = true; key('KeyD', true); } if (u > 1.9 && this.go === true) { this.go = 2; key('KeyD', false); key('KeyW', true); } },
      end() { key('KeyD', false); key('KeyW', false); } },
    { key: 'pager', name: '삐삐 호출', sub: '삐삐가 울리면<br>공중전화로 달려가기',
      async begin() { $('#pager-start').click(); await waitFor(() => shown('#pagerhud')); settle(20); },
      tick(u) { if (u > 1.3 && !this.go) { this.go = true; key('ShiftLeft', true); key('KeyW', true); } },
      end() { key('KeyW', false); key('ShiftLeft', false); } },
    { key: 'cheer', name: '연고전 응원 연습', sub: '아카라카 구호와<br>응원가에 맞춰',
      async begin() { $('#cheer-start').click(); await waitFor(() => shown('#cheerpick')); settle(8); },
      async tick(u) {
        if (u > 1.0 && !this.go) {
          this.go = true;
          $('#cheerpick button').click();
          await waitFor(() => $('#intro').hidden && y.cheer?.state === 'count', 10000);
          y.cheer.auto = true;
          await untilDo(() => y.cheer.state === 'play' && (y.cheer.presses?.length ?? 0) >= 2, 900);      // 첫 박자를 칠 때까지
        }
      },
      async end() { I.season.now = null; } },
    { key: 'class', name: '강의실 찾기', sub: '쉬는 시간 안에<br>다음 수업 건물로',
      async begin() { $('#class-start').click(); await waitFor(() => shown('#classpick')); settle(8); },
      async tick(u) {
        if (u > 1.3 && !this.go) { this.go = true; document.querySelectorAll('#classpick button')[2].click(); await waitFor(() => $('#intro').hidden && y.lecture?.state === 'count', 8000); await untilDo(() => y.lecture.state === 'play'); key('KeyW', true); }
      },
      end() { key('KeyW', false); } },
    { key: 'bday', name: '생일 축하', sub: '친구 넷을 찾아<br>활천대로 데려오기',
      // (활천대 앞은 생일 장면이 이미 보여 줌) 친구 넷을 다 데려온 때로: 백양로 동쪽 보도를 북쪽으로 뛰는 주인공과
      // 그 발자취를 따라 뛰는 친구 넷을 동쪽 생울타리 위 앞에서 비스듬히 따라가며(줄이 겹치지 않게. 서쪽 화단은 관목이 가림)
      async begin() {
        $('#bday-start').click();
        await waitFor(() => shown('#bdayhud') && y.bday?.state === 'play');
        settle(10);
        const B = y.bday, n = ROAD, s0 = 32, at = (s) => [-76.3 + n[0] * s, -318 + n[1] * s];
        await ensure(...at(s0 + 25));
        pl.teleport(...at(s0), null);
        pl.heading = Math.atan2(n[0], -n[1]);
        pl.actor.holder.rotation.y = pl.heading;
        // 발자취: 주인공 뒤로 곧게 7 m, 친구는 그 위에 줄지어(bdaygame.js GAP0 1.1 · GAP 0.95)
        B.trail.reset(G(...at(s0 - 7)));
        for (let d = -6.75; d < 0; d += 0.25) B.trail.push(G(...at(s0 + d)));
        B.trail.push(pl.pos);
        B.friends.forEach((f, k) => {
          f.got = true; f.order = k; f.w = 1; f.a.stand = 'idle';
          f.s = B.trail.head - 1.1 - k * 0.95;
          B.trail.at(f.s, f.a.holder.position);
        });
        B.drawHud(true);
        key('ShiftLeft', true); key('KeyW', true);
        await untilDo(() => false, 36);                              // 뛰는 빠르기에 오를 때까지
      },
      tick(u) {
        const B = y.bday, n = ROAD, p = pl.pos, f = new V(n[0], 0, -n[1]), w = new V(-n[1], 0, -n[0]);     // 앞 · 서쪽(-w: 동쪽)
        walkCam(p.clone().addScaledVector(f, 4.0).addScaledVector(w, -3.3).setY(p.y + 2.2), p.clone().addScaledVector(f, -2.4).setY(p.y + 0.9), 44);
        if (u > 0.5 && !this.said) { this.said = true; const q = B.friends[1]; B.say(q.a.holder, q.top, '분수에 빠뜨리러 가자!', B.t); }
      },
      end() { key('ShiftLeft', false); key('KeyW', false); pl.camOverride = null; } },
  ];
  seg.games = {
    n: Math.round(GAMES.length * GAME_T * FPS),
    async init(arg) {
      hud('#hud > #place, #toast, #birdpins, #tourbar, #birdbar { display: none !important; }');
      this.list = arg?.only ? GAMES.filter((g) => arg.only.includes(g.key)) : GAMES;
      this.n = Math.round(this.list.length * GAME_T * FPS);
      this.k = -1;
      $('#news .close')?.click();
    },
    async step(i, t) {
      const k = Math.min(this.list.length - 1, Math.floor(t / GAME_T)), u = t - k * GAME_T;
      if (k !== this.k) {
        if (this.k >= 0) await this.list[this.k].end?.();
        this.k = k;
        if ($('#intro').hidden) { y.toTitle(); await sleep(150); }
        if (I.season.now === null) await season('summer');
        await this.list[k].begin();
      }
      const g = this.list[k];
      await g.tick(u);
      step();
      const t0 = k * GAME_T;
      show('scrim', 'scrim', '', t, 0, 999, { slide: 0 });
      show('chip', 'chip', '미니 게임 일곱 가지', t, 0, 999, { slide: 0 });
      show('g' + k, 'cap', `<b>${g.name}</b><span>${g.sub}</span>`, t, t0 + 0.04, t0 + GAME_T - 0.14, { fade: 0.16, slide: 10 });
      return { mark: u < DT ? g.key : undefined, note: g.key };
    },
  };

  // ---------------------------------------------------------------- 사진과 게임: 같은 시점에서 나란히
  // 왼쪽에 사진, 오른쪽에 같은 크기의 창으로 게임. 게임의 카메라는 사진에 맞춘 것(tools/snapshots.json 의 compare/*,
  // 독수리상 · 용재 동상은 여기서 맞춤)이고, 창이 사진과 같은 비율이라 창 안에 사진의 화면이 그대로 들어간다
  const EAGLE_C = [-67.95, -161.78], YJ = [-38.26, -27.34];
  const CMP = [
    { key: 'eagle', name: '독수리상', note: '1970년, 학생들의 모금으로 세운 연세의 상징', photo: '1971년 · 공유마당', file: 'reference/1971_독수리상_공유마당.jpg', size: [1254, 1600], t: 5.5,
      // 동쪽 조금 남쪽 42 m 에서, 기둥을 화면 왼쪽에 두고
      cam: () => { const a = -12 * Math.PI / 180, D = 42, g = ground(...EAGLE_C), d = [-Math.cos(a), -Math.sin(a)], r = [d[1], -d[0]];
        return { x: EAGLE_C[0] - d[0] * D, y: EAGLE_C[1] - d[1] * D, h: ground(EAGLE_C[0] - d[0] * D, EAGLE_C[1] - d[1] * D) + 1.6, tx: EAGLE_C[0] + r[0] * 5.0, ty: EAGLE_C[1] + r[1] * 5.0, th: g + 5.2, fov: 27 }; } },
    { key: 'uw', name: '언더우드 동상', note: '언더우드관 앞 정원에서 두 팔 벌려 맞이하는', photo: '2009년 · Wikimedia Commons', file: 'docs/compare/underwood_statue_photo.jpg', size: [717, 1365], t: 5.5, season: 'spring',
      cam: () => ({ x: 52.83, y: 184.65, h: 44.73, tx: 50.75, ty: 193.75, th: 45.41, fov: 18.53 }) },
    { key: 'yj', name: '용재 동상', note: '중앙도서관 앞, 초대 총장 용재 백낙준', photo: '2007년 · 연세춘추', file: 'reference/연세춘추/2007-03-24_10503_874_2738_5018.jpg', size: [290, 436], t: 5.5, season: 'spring',
      // 동상은 남쪽(방위 195°)을 봄: 정면 조금 서쪽 15 m 에서 망원으로 올려다봄
      cam: () => { const f = [-0.259, -0.966], w = [-0.966, 0.259], g = ground(...YJ), x = YJ[0] + f[0] * 15 + w[0] * 3.2, yy = YJ[1] + f[1] * 15 + w[1] * 3.2;
        return { x, y: yy, h: ground(x, yy) + 1.5, tx: YJ[0], ty: YJ[1], th: g + 2.35, fov: 19.2 }; } },
    { key: 'oesol', name: '외솔 흉상', note: '노천극장 가는 길목, 1994년에 세운 한글학자 외솔 최현배의 얼굴상', photo: '2007년 · 연세춘추 (외솔관 앞으로 옮긴 뒤)', file: 'docs/compare/oesol_bust_photo.jpg', size: [508, 374], t: 5.5, season: 'spring',
      // tools/snapshots.json compare/oesol_bust: 흉상 정면 4 m 에서 망원으로
      cam: () => ({ x: 100.14, y: 168.96, h: 47.85, tx: 104.0, ty: 170.0, th: 47.85, fov: 11.1 }) },
    { key: 'gate', name: '정문', photo: '1996년 8월 · 서울연구원', file: 'docs/compare/gate_photo.jpg', size: [1350, 903], t: 3.4, near: 38,
      cam: () => ({ x: -128.06, y: -468.52, h: 31.76, tx: -112.42, ty: -394.14, th: 29.92, fov: 18.54 }) },
    { key: 'road', name: '백양로', photo: '1999년 봄 항공 사진', file: 'docs/compare/baekyangro_photo.jpg', size: [1413, 900], t: 3.4,
      cam: () => ({ x: -106.87, y: -396.83, h: 44.69, tx: 54.38, ty: 181.1, th: 2.17, fov: 33.06 }) },
    { key: 'lib', name: '중앙도서관', photo: '1997년', file: 'docs/compare/library_photo.jpg', size: [1340, 904], t: 3.4,
      cam: () => ({ x: -16.84, y: 4.96, h: ground(-16.84, 4.96) + 1.6, tx: -60.0, ty: -13.66, th: 44.51, fov: 39.2 }) },
    { key: 'hwal', name: '활천대', photo: '2009년 · 연세춘추', file: 'docs/compare/hwalcheon_photo.jpg', size: [1050, 700], t: 3.4,
      cam: () => ({ x: -74.5, y: -218.83, h: ground(-74.5, -218.83) + 1.6, tx: -81.02, ty: -189.55, th: ground(-81.02, -189.55) + 3.93, fov: 36.1 }) },
  ];
  seg.compare = {
    files: Object.fromEntries(CMP.map((c) => [c.key, c.file])),
    async init(arg) {
      this.list = arg?.only ? CMP.filter((c) => arg.only.includes(c.key)) : CMP;
      let t = 0;
      for (const c of this.list) { c.t0 = t; t += c.t; }
      this.n = Math.round(t * FPS);
      this.k = -1;
      toBird();
      hud('none');
    },
    // 사진 · 창의 자리(1920 × 1080 의 화소): 사진의 비율로, 두 칸에 같은 크기
    rects(c) {
      const a = c.size[0] / c.size[1], bw = 860, bh = 670;
      const w = Math.round(Math.min(bw, bh * a)), h = Math.round(w / a), cy = 478;
      return { photo: { x: 500 - w / 2, y: cy - h / 2, w, h }, win: { x: 1420 - w / 2, y: cy - h / 2, w, h } };
    },
    async stage(k) {
      const c = this.list[k];
      I.clear();
      await season(c.season ?? 'summer');
      const q = c.cam();
      await ensure(q.tx, q.ty);
      await ensure(q.x, q.y);
      const r = (this.r = this.rects(c));
      // 창 안에 사진의 화면이 들어가게: 창을 온 화면으로 삼고 캔버스가 그 둘레까지 그린다
      cam.aspect = r.win.w / r.win.h;
      cam.setViewOffset(r.win.w, r.win.h, -r.win.x, -r.win.y, 1920, 1080);
      delete cam.near;
      if (c.near) Object.defineProperty(cam, 'near', { get: () => c.near, set: () => {}, configurable: true });
      else cam.near = 1;
      birdCam(q.x, q.y, q.h, q.tx, q.ty, q.th, q.fov);
      settle(45);
    },
    async step(i, t) {
      let k = this.list.findIndex((c) => t < c.t0 + c.t);
      if (k < 0) k = this.list.length - 1;
      if (k !== this.k) { this.k = k; await this.stage(k); }
      const c = this.list[k], r = this.r, u = t - c.t0;
      step();
      const o = { slide: 0, fade: 0.01 };
      const put = (e, q, b = 8) => { e.style.left = `${q.x - b}px`; e.style.top = `${q.y - b}px`; e.style.width = `${q.w}px`; e.style.height = `${q.h}px`; };
      put(show('win', 'cmp-win', '', t, 0, 1e9, o), r.win);
      const ph = show('ph' + k, 'cmp-photo', '', t, c.t0, c.t0 + c.t, o);
      if (!ph.style.backgroundImage) ph.style.backgroundImage = `url(${this.data[c.key]})`;
      put(ph, r.photo);
      const lab = (id, html, x) => { const e = show(id + k, 'cmp-lab', html, t, c.t0, c.t0 + c.t, o); e.style.left = `${x}px`; e.style.top = `${r.win.y + r.win.h + 26}px`; };
      lab('lp', `<b>사진</b>${c.photo}`, 500);
      lab('lg', '<b>게임</b>같은 시점', 1420);
      show('nm' + k, 'cmp-name', `${c.name}${c.note ? `<small>${c.note}</small>` : ''}`, t, c.t0, c.t0 + c.t, o);
      show('chip', 'chip', '사진과 게임', t, 0, 1e9, o);
      // 바뀌는 순간은 어둡게 덮음
      const e = show('cover', 'cover', '', 0, 0, 1, o);
      e.style.opacity = Math.max(0, 1 - Math.min(u, c.t - u) / 0.22).toFixed(3);
      return { mark: u < DT ? c.key : undefined, note: c.key };
    },
  };

  // ---------------------------------------------------------------- 참고한 자료의 양 · 출처 · 제보 · Thanks to
  // 캠퍼스 위를 천천히 도는 화면 위에 글. 숫자는 README 「고증」의 통계와 같게 둔다(고치면 함께 고침)
  const STATS = { total: 333, gb: 4.6, repo: [278, 66], aerial: [34, 4.3], maps: [9, 21, 190] };
  const PAGES = [
    { t: 12.5, chip: '고증에 참고한 자료', html: (n, g) => `<h1>사진과 지도 <i>${n}점</i>, 약 <i>${g} GB</i></h1>
      <ul>
        <li><b>저장소의 사진 ${STATS.repo[0]}장 · ${STATS.repo[1]} MB</b><small>재상봉 기념문집 · 옛 학교 홈페이지 · 연세춘추 · 공개 라이선스 사진</small></li>
        <li><b>항공사진 ${STATS.aerial[0]}장 · 약 ${STATS.aerial[1]} GB</b><small>국토지리정보원 1996 ~ 1999년 촬영분 (보며 측정만 함)</small></li>
        <li><b>1:5,000 수치지형도 ${STATS.maps[0]}도엽 ${STATS.maps[1]}판 · 약 ${STATS.maps[2]} MB</b><small>보며 측정만 함</small></li>
        <li><b>로드뷰 · 스카이뷰 · 거리뷰</b><small>카카오맵 2008 ~ 2011년, 네이버 2010년 촬영분을 화면으로 보며 측정</small></li>
      </ul>` },
    { t: 10.5, chip: '자료 출처', html: () => `<div class="cols">
        <div><h2>사진 · 기록</h2>연세대학교 재상봉 25주년 기념문집 (2019 ~ 2026년)<br>2026년 문집 「응답하라 1997!」<br>연세대학교 기록관 · 연세동문회보 · 연세춘추<br>교육97 김연희 · 상경97 김태봉 동문<br>1996 ~ 2000년의 연세대학교 홈페이지 (웨이백 머신)<br>서울연구원 「사진으로 본 서울」 · Wikimedia Commons<br>동문들이 보내 준 사진과 기억</div>
        <div><h2>측정 · 지도</h2>국토지리정보원 국토정보플랫폼<br>카카오맵 로드뷰 · 스카이뷰, 네이버 거리뷰<br>OpenStreetMap · Copernicus DEM
          <h2 style="margin-top:26px">3D 모형 · 움직임</h2>Poly Haven · Quaternius<br>Blender Human Base Meshes<br>100STYLE · ACCAD · CMU 모션 캡처<br>three.js · Ultra Water</div>
      </div><p class="foot">파일마다의 출처는 게임의 「자료 출처 · 고마운 분들」 창과 GitHub 저장소의 README · reference 폴더에 있습니다</p>` },
    { t: 9, chip: '자료 제보', html: () => `<h1>1997년과 <i>다른 곳</i>을 알려 주세요</h1><p>기억나는 모습이나 사진과 함께 보내 주시면 하나씩 확인해서 고칩니다</p>
      <ul>
        <li><b>게임 안 쪽지</b><small>다른 곳 앞에서 <span class="key">N</span> 키나 「쪽지」 버튼으로 그 자리에 붙이기</small></li>
        <li><b>메일</b><small>benelog@gmail.com</small></li>
        <li><b>GitHub 이슈</b><small>github.com/yonsei-reunion/campus-1997/issues</small></li>
      </ul>` },
    { t: 6, mid: true, html: () => `<h2 style="margin-top:0">Thanks to</h2><p>사진과 기억을 나눠 주신<br>아카라카북클럽(ABC) 회원 여러분</p><h2>Special Thanks to</h2><p>이중윤</p>` },
    { t: 5.5, end: true, html: () => '' },
  ];
  seg.info = {
    async init(arg) {
      this.list = arg?.only ? PAGES.filter((_, k) => arg.only.includes(k)) : PAGES;
      let t = 0;
      for (const p of this.list) { p.t0 = t; t += p.t; }
      this.n = Math.round(t * FPS);
      toBird();
      hud('none');
      this.at(0);
      settle(60);
    },
    at(t) {
      // 백양로 위를 남쪽에서 북쪽으로 천천히, 조금씩 돌며
      const u = t / (this.n / FPS), a = lerp(-1.95, -1.25, u), R = lerp(430, 360, u), cx = -20, cy = 0;
      birdCam(cx + Math.cos(a) * R, cy + Math.sin(a) * R, lerp(250, 200, u), cx, cy + 40, 40, 40);
    },
    step(i, t) {
      this.at(t);
      step();
      const T = this.n / FPS;
      const last = this.list[this.list.length - 1];
      // 끝 화면에서는 어둠을 걷음
      const sh = show('shade', 'shade', '', t, 0, 1e9, { slide: 0, fade: 0.01 });
      sh.style.opacity = last.end ? lerp(1, 0.35, smooth((t - last.t0 + 0.4) / 1.2)).toFixed(3) : '1';
      this.list.forEach((p, k) => {
        if (p.end) {
          show('end', 'title', '<b>신촌 캠퍼스 1997</b><span>1997년의 연세대학교를 다시 걷습니다</span><small>yonsei-1997.benelog.net</small>', t, p.t0 + 0.3, T + 9, { fade: 0.6 });
          return;
        }
        if (p.chip) show('chip' + k, 'chip', p.chip, t, p.t0 + 0.15, p.t0 + p.t - 0.15, { slide: 0 });
        let html = p.html(STATS.total, STATS.gb.toFixed(1));
        const e = show('pg' + k, p.mid ? 'pg mid' : 'pg', html, t, p.t0 + 0.2, p.t0 + p.t - 0.2, { fade: 0.45 });
        if (k === 0 && p.chip === '고증에 참고한 자료') {
          // 숫자가 올라감
          const q = smooth((t - p.t0 - 0.4) / 1.8), is = e.querySelectorAll('h1 i');
          if (is.length === 2) { is[0].textContent = `${Math.round(STATS.total * q)}점`; is[1].textContent = `${(STATS.gb * q).toFixed(1)} GB`; }
        }
        // 목록은 한 줄씩
        e.querySelectorAll('li').forEach((li, j) => {
          const q = smooth((t - p.t0 - 1.0 - j * 0.7) / 0.45);
          li.style.opacity = q.toFixed(3);
          li.style.transform = `translateY(${((1 - q) * 14).toFixed(1)}px)`;
        });
      });
    },
  };
})();
