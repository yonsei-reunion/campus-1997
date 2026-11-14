// 정문 동쪽 흰 담의 대자보 (reference/고증/4.8.1_정문의_생김새.md 「대자보」).
// The October 1995 and May 1996 photos (reference/1995_정문_성산로_건너에서.jpg, 1996_정문_동쪽_담_철둑에서.jpg) both
// have the white wall's two bays papered over: big sheets of two or three 전지 (0.79 x 1.09 m) hung from near the
// wall's top, brush-written in black with a word or a line in red, one of them on brown paper, small notices under
// them.  What they say follows the season (mid-April, late May, late October 1997): the events are the ones the
// papers of those weeks report (서울신문 1997.4.4, 5.9, 6.5, 10.11 ...), the wording is made up.
import * as THREE from 'three';

// the white wall in the gate's frame (blender/props.py GATE_WALL): along the gate's line from its middle, m
const WALL = { u0: 11.3, h: 2.7, t: 0.35 };
const FONT = '"Do Hyeon", "Jua", "Noto Sans KR", sans-serif';
const INK = { k: '#17171a', r: '#b3201f', b: '#1c2f86', g: '#1f6a3a' };
const PAPER = { white: '#f4f1e8', kraft: '#b8946a', yellow: '#f0dc7a', pink: '#efc4cc', blue: '#c9dcee' };
const PPM = 280;                       // canvas pixels a metre

// A sheet: u = its left edge from the wall's west end, top = its top over the wall's foot, w x h (m: so many 전지),
// paper; lines: [text, letter height (m), ink]; body: the small writing; sign: who put it up (bottom right)
const SM = { u: 2.72, top: 0.9, w: 0.45, h: 0.62 }, SM2 = { u: 6.1, top: 0.93, w: 0.5, h: 0.62 };
const SHEETS = {
  spring: [
    { u: 0.08, top: 2.6, w: 2.37, h: 2.18, lines: [['신촌을 「제2의 대학로」로!', 0.27, 'r'], ['대학문화의 거리 지정 촉구 서명운동', 0.16, 'k']],
      body: ['연극 무대 하나 들어설 수 없는 신촌,', '서점의 책보다 맥주 한 잔이 더 마음을 끄는 신촌은', '진정한 대학가의 모습이 아닙니다.', '신촌을 대학문화의 메카로 — 서명에 함께해 주십시오.',
        '', '· 매주 목요일 민주광장 문화공연 (재즈 · 풍물 · 클래식)', '· 서명하는 곳: 학생회관 앞, 정문 앞'], sign: '연세대학교 총학생회' },
    { u: 2.43, top: 2.55, w: 1.09, h: 1.58, lines: [['4·19', 0.34, 'r'], ['서른일곱 돌', 0.13, 'k'], ['기념 마라톤', 0.17, 'k']],
      body: ['4월 19일', '학생회관 앞에서 출발', '함께 달립시다!'], sign: '총학생회' },
    { u: 4.08, top: 2.6, w: 1.09, h: 2.18, paper: 'kraft', lines: [['한보 비리', 0.2, 'k'], ['청문회', 0.2, 'k'], ['몸통을', 0.26, 'r'], ['밝혀라!', 0.26, 'r']],
      body: ['깃털이 아니라', '몸통을 —', '성역 없는 수사를', '촉구한다'], sign: '문과대 학생회' },
    { u: 5.25, top: 2.58, w: 2.37, h: 1.58, lines: [['한총련 탈퇴, 그 다음은?', 0.25, 'b'], ['새 학생운동을 말한다', 0.2, 'k']],
      body: ['정치 구호만 외치는 학생운동을 넘어', '학생 복지와 대학문화, 우리 생활의 문제까지', '공개 토론회 · 학생회관 — 누구나 와서 말합시다'], sign: '총학생회' },
    { ...SM, paper: 'yellow', lines: [['신입회원', 0.1, 'k'], ['모집', 0.14, 'r']], body: ['동아리 연합회', '학생회관 3층'] },
    { ...SM2, paper: 'pink', lines: [['수습기자', 0.1, 'k'], ['모집', 0.14, 'b']], body: ['연세춘추', '4월 말까지'] },
  ],
  summer: [
    { u: 0.08, top: 2.6, w: 2.37, h: 2.18, lines: [['음식쓰레기를 줄입시다', 0.27, 'g'], ['남기지 않으면 요구르트 하나!', 0.17, 'k']],
      body: ['지난 4월 한 달, 우리 식당 세 곳에서 버려진 음식물이 15,900 kg.', '하루 636 kg입니다.', '대동제 사흘 동안의 캠페인을 계속 이어 갑니다.',
        '', '· 맛나샘 · 고를샘 · 학생식당, 오전 11시 ~ 오후 2시', '· 줄인 처리 비용은 학생 복지에 씁니다'], sign: '연세대학교 총학생회' },
    { u: 2.43, top: 2.55, w: 1.09, h: 1.58, lines: [['5·18', 0.34, 'r'], ['열일곱 돌', 0.13, 'k'], ['오월 광주를', 0.15, 'k'], ['기억하자', 0.17, 'k']],
      body: ['사진전 · 영화 상영', '학생회관'], sign: '총학생회' },
    { u: 4.08, top: 2.6, w: 1.09, h: 2.18, paper: 'kraft', lines: [['김현철', 0.22, 'k'], ['구속,', 0.22, 'k'], ['다음은', 0.17, 'k'], ['대선자금', 0.24, 'r'], ['공개다!', 0.24, 'r']],
      body: ['92년 대선자금,', '한 점 남김없이', '밝혀라'], sign: '사회과학대 학생회' },
    { u: 5.25, top: 2.58, w: 2.37, h: 1.58, lines: [['이한열 열사 10주기', 0.25, 'k'], ['87년 6월을 기억하며', 0.19, 'b']],
      body: ['1987년 6월 9일, 이 문 앞에서 한열이가 쓰러졌습니다.', '열 해가 지난 오늘, 그날의 함성을 다시 생각합니다.', '추모제 · 6월 9일'], sign: '추모제 준비위원회' },
    { ...SM, paper: 'blue', lines: [['여름 농활', 0.1, 'k'], ['함께 가요', 0.1, 'g']], body: ['참가 신청', '각 단과대 학생회'] },
    { ...SM2, paper: 'yellow', lines: [['한총련 출범식', 0.075, 'k'], ['불참합니다', 0.1, 'r']], body: ['폭력 시위에 반대합니다', '총학생회'] },
  ],
  autumn: [
    { u: 0.08, top: 2.6, w: 2.37, h: 2.18, paper: 'blue', lines: [['’97 정기 연고전', 0.24, 'b'], ['필승! 전승! 압승!', 0.34, 'b']],
      body: ['푸른 옷을 입고 모입시다 — 응원 오리엔테이션', '독수리의 함성으로 가을 하늘을 덮자', '', '아카라카!'], sign: '연세대학교 응원단' },
    { u: 2.43, top: 2.55, w: 1.09, h: 1.58, lines: [['12·18', 0.3, 'r'], ['대통령 선거', 0.15, 'k'], ['대학생 유권자', 0.12, 'k'], ['한 표를 지키자', 0.13, 'k']],
      body: ['부재자 신고를', '잊지 맙시다'], sign: '총학생회' },
    { u: 4.08, top: 2.6, w: 1.09, h: 2.18, paper: 'kraft', lines: [['전두환', 0.24, 'k'], ['노태우', 0.24, 'k'], ['사면', 0.3, 'r'], ['반대!', 0.3, 'r']],
      body: ['학살자에게', '면죄부는 없다'], sign: '법과대 학생회' },
    { u: 5.25, top: 2.58, w: 2.37, h: 1.58, lines: [['취업 한파, 길을 묻다', 0.25, 'k'], ['4학년 취업 · 대학원 진학 설명회', 0.15, 'b']],
      body: ['잇따른 대기업 부도, 사상 최악의 취업난.', '올해 우리 대학원 지원자만 2천여 명입니다.', '먼저 길을 찾은 선배들이 답합니다 · 학생회관'], sign: '총학생회' },
    { ...SM, paper: 'white', lines: [['총학생회 선거', 0.07, 'k'], ['후보 등록 공고', 0.07, 'r']], body: ['중앙선거관리위원회', '11월'] },
    { ...SM2, paper: 'yellow', lines: [['가을 학술제', 0.09, 'k'], ['발표자 모집', 0.09, 'b']], body: ['각 과 학생회'] },
  ],
};

function rng(seed) {                    // (mulberry32)
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// one line, letter by letter, as a hand with a brush writes it: each a little off the line, turned and sized
function handLine(x, rnd, text, cx, cy, size, maxW, ink) {
  x.font = `bold ${Math.round(size)}px ${FONT}`;
  let w = x.measureText(text).width;
  if (w > maxW) { size *= maxW / w; x.font = `bold ${Math.round(size)}px ${FONT}`; w = x.measureText(text).width; }
  x.fillStyle = ink; x.textAlign = 'center'; x.textBaseline = 'middle';
  let px = cx - w / 2;
  for (const ch of text) {
    const cw = x.measureText(ch).width;
    x.save();
    x.translate(px + cw / 2, cy + (rnd() - 0.5) * size * 0.09);
    x.rotate((rnd() - 0.5) * 0.07);
    const s = 1 + (rnd() - 0.5) * 0.1;
    x.scale(s, s);
    x.globalAlpha = 0.86 + rnd() * 0.14;
    x.fillText(ch, 0, 0);
    x.restore();
    px += cw;
  }
  x.globalAlpha = 1;
  return size;
}

function sheetTexture(s, seed) {
  const rnd = rng(seed);
  const W = Math.round(s.w * PPM), H = Math.round(s.h * PPM);
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const x = c.getContext('2d');
  const paper = PAPER[s.paper || 'white'];
  x.fillStyle = paper; x.fillRect(0, 0, W, H);
  // the paper: uneven, the seams of the 전지 pasted side by side (or one over the other), a few creases
  for (let k = 0; k < 40; k++) {
    x.fillStyle = `rgba(${rnd() < 0.5 ? '0,0,0' : '255,255,255'},${0.015 + rnd() * 0.03})`;
    x.fillRect(rnd() * W, rnd() * H, 30 + rnd() * W * 0.4, 10 + rnd() * H * 0.3);
  }
  x.strokeStyle = 'rgba(0,0,0,0.16)'; x.lineWidth = 1.5;
  const wide = s.w > s.h;
  const n = Math.max(1, Math.round((wide ? s.w : s.h) / 0.79));
  for (let k = 1; k < n; k++) {
    x.beginPath();
    if (wide) { x.moveTo(W * k / n + (rnd() - 0.5) * 4, 0); x.lineTo(W * k / n + (rnd() - 0.5) * 4, H); }
    else { x.moveTo(0, H * k / n + (rnd() - 0.5) * 4); x.lineTo(W, H * k / n + (rnd() - 0.5) * 4); }
    x.stroke();
  }
  x.strokeStyle = 'rgba(0,0,0,0.05)';
  for (let k = 0; k < 5; k++) { x.beginPath(); x.moveTo(rnd() * W, 0); x.lineTo(rnd() * W, H); x.stroke(); }
  // the big lines, the small writing under them, the name at the bottom right
  const pad = Math.min(W, H) * 0.08, maxW = W - 2 * pad;
  const small = (s.w < 0.8 ? 0.045 : 0.085) * PPM;
  const bodyH = (s.body ? s.body.length : 0) * small * 1.5 + (s.sign ? small * 1.8 : 0);
  const bigH = s.lines.reduce((a, l) => a + l[1] * PPM * 1.22, 0);
  let y = pad + Math.max(0, (H - 2 * pad - bodyH - bigH) * 0.3);
  for (const [text, size, ink] of s.lines) {
    const px = size * PPM;
    handLine(x, rnd, text, W / 2 + (rnd() - 0.5) * W * 0.02, y + px * 0.55, px, maxW, INK[ink] || INK.k);
    y += px * 1.22;
  }
  y += small * 0.8;
  for (const t of s.body || []) { if (t) handLine(x, rnd, t, W / 2, y + small * 0.5, small, maxW, INK.k); y += small * 1.5; }
  if (s.sign) handLine(x, rnd, s.sign, W - pad - maxW * 0.26, H - pad - small * 0.5, small * 1.15, maxW * 0.52, INK.k);
  // tape at the corners, the weather's grey along the bottom
  x.fillStyle = 'rgba(214,204,170,0.85)';
  const tw = Math.max(16, W * 0.05), th = Math.max(8, tw * 0.42);
  for (const [tx, ty] of [[0, 0], [W - tw, 0], [0, H - th], [W - tw, H - th]]) x.fillRect(tx + (tx ? -3 : 3), ty + (ty ? -3 : 3), tw, th);
  const g = x.createLinearGradient(0, H * 0.7, 0, H);
  g.addColorStop(0, 'rgba(60,50,40,0)'); g.addColorStop(1, 'rgba(60,50,40,0.1)');
  x.fillStyle = g; x.fillRect(0, 0, W, H);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

// gate: campus.statues.gate ({pos, rot, h}); groundAt(x, y): the ground's height (campus frame)
export function makeGatePosters(gate, groundAt) {
  const group = new THREE.Group();
  group.name = 'gate_posters';
  const cs = Math.cos(gate.rot), sn = Math.sin(gate.rot);
  const at = (u, v) => [gate.pos[0] + u * cs - v * sn, gate.pos[1] + u * sn + v * cs];
  const foot = Math.min(groundAt(...at(WALL.u0, 0)), groundAt(...at(WALL.u0 + 7.7, 0)));     // (the wall's own foot: props.py gate)
  const clear = () => {
    for (const m of [...group.children]) { m.geometry.dispose(); m.material.map.dispose(); m.material.dispose(); group.remove(m); }
  };
  group.userData.setSeason = (season) => {
    clear();
    (SHEETS[season] || []).forEach((s, i) => {
      const rnd = rng(1997 + i * 31 + season.length * 7);
      const mat = new THREE.MeshStandardMaterial({ map: sheetTexture(s, 97 + i * 13 + season.charCodeAt(1)), roughness: 0.95, metalness: 0,
        polygonOffset: true, polygonOffsetFactor: -2 - i, polygonOffsetUnits: -2 - i });
      const m = new THREE.Mesh(new THREE.PlaneGeometry(s.w, s.h), mat);
      const [px, py] = at(WALL.u0 + s.u + s.w / 2, -WALL.t / 2 - 0.012 - i * 0.003);
      m.position.set(px, foot + s.top - s.h / 2, -py);
      m.rotation.order = 'YXZ';
      m.rotation.set((rnd() - 0.5) * 0.012, gate.rot, (rnd() - 0.5) * 0.035);
      m.receiveShadow = true;
      group.add(m);
    });
  };
  return group;
}
