// Small talk on campus: passers-by who meet stop to greet each other and trade a line or two, standing groups chat,
// people say hello when you come up to them or ask to get by when you block the way. What they say follows the month
// picked (materials.js SEASONS: spring = 4월 벚꽃, summer = 5월 신록, autumn = 10월 단풍). The lines float over the
// speakers' heads as speech bubbles, in the DOM like the building tags (labels.js).
import * as THREE from 'three';

export const kindOf = (id) => (id === 'man-professor' ? 'prof' : id.endsWith('-staff') ? 'staff' : 'student');

// Every table: `common` lines fit any month, the season's own lines are picked more often.
// A dialogue alternates speakers: the one who speaks first, the other, (the first again).

// two students meeting on a path
const FRIENDS = {
  common: [
    ['어, 안녕!', '안녕! 어디 가?', '수업 가. 이따 봐!'],
    ['야, 오랜만이다!', '그러게. 연락 좀 해.'],
    ['밥 먹었어?', '아직. 학관 갈래?'],
    ['어제 삐삐 쳤는데 못 봤어?', '미안, 음성 이제 들었어.'],
    ['수업 끝났어?', '응, 중도 가려고.'],
    ['이따 독다방에서 볼래?', '좋아. 삐삐 쳐!'],
    ['과방 가?', '응, 같이 가자.'],
  ],
  spring: [
    ['벚꽃 진짜 예쁘다!', '사진 찍자. 필름 남았어?'],
    ['중간고사 언제부터야?', '다음 주야. 큰일 났다…'],
    ['이번 주말 MT 가?', '응, 대성리로 간대.'],
    ['동아리 정했어?', '아직 고민 중이야.'],
    ['어제 「별은 내 가슴에」 봤어?', '응, 안재욱 너무 멋있더라.'],
    ['날씨 좋다. 수업 째고 싶다.', '그러다 F 맞는다.'],
  ],
  summer: [
    ['축제 때 뭐 해?', '과 주점 한대. 놀러 와!'],
    ['잔디밭에서 짜장면 시켜 먹을래?', '좋지! 누가 쏘는 건데?'],
    ['스승의 날 꽃 샀어?', '과에서 같이 드리기로 했어.'],
    ['벌써 덥다. 여름 같아.', '아이스크림 하나 먹자.'],
    ['체육대회 나가?', '응, 축구 선수래.'],
    ['노천극장에서 공연한대.', '진짜? 같이 가자!'],
  ],
  autumn: [
    ['중간고사 끝났어?', '아직 하나 남았어…'],
    ['한일전 봤어?', '이민성 중거리 슛, 최고였지!'],
    ['「접속」 봤어?', '응, 음악이 참 좋더라.'],
    ['벌써 쌀쌀하다.', '은행잎 다 노래졌네.'],
    ['토익 학원 다녀?', '응, 이제 취업 준비해야지.'],
  ],
};

// a student passing a professor or a staff member: the student greets first, the elder answers
const TO_PROF = { common: ['교수님, 안녕하세요!', '안녕하세요, 교수님!'] };
const PROF = {
  common: ['그래, 반갑다.', '그래, 수업 때 보자.', '그래, 밥은 먹었니?'],
  spring: ['그래, 중간고사 준비 잘 하고.', '그래, 리포트 잊지 말고.'],
  summer: ['그래, 축제라고 너무 놀지만 말고.', '그래, 날씨 참 좋다.'],
  autumn: ['그래, 시험은 잘 봤니?', '그래, 연고전 꼭 이기자!'],
};
const TO_STAFF = { common: ['안녕하세요!', '수고하세요!'] };
const STAFF = {
  common: ['네, 안녕하세요.', '네, 조심히 다녀요.'],
  spring: ['네, 꽃구경 많이 해요.'],
  summer: ['네, 축제 잘 즐겨요.'],
  autumn: ['네, 감기 조심해요.'],
};

// two professors / staff members
const ADULTS = {
  common: [['안녕하세요. 식사하셨어요?', '네, 방금 먹고 오는 길이에요.'], ['수고 많으십니다.', '네, 수고하세요.']],
  spring: [['벚꽃이 한창이네요.', '그러게요. 꽃이 참 좋습니다.']],
  summer: [['축제라 학교가 시끌벅적하네요.', '젊음이 좋지요.']],
  autumn: [['시험 기간이라 도서관이 꽉 찼더군요.', '네, 밤늦게까지 불이 켜져 있어요.'], ['은행잎이 다 물들었네요.', '가을이 깊었습니다.']],
};

// standing groups: two students, a student and a professor, a student and a staff member
const GROUP = {
  common: [
    ['그래서 걔가 뭐래?', '몰라, 삐삐에 음성만 남겼대.'],
    ['오늘 저녁 뭐 먹지?', '신촌 가서 닭갈비 어때?'],
    ['이번 학기 몇 학점 들어?', '21학점. 죽겠어.'],
    ['PC통신에서 번개 한대.', '하이텔? 나우누리?'],
    ['리포트 다 썼어?', '아직. 오늘 밤새야 돼.'],
  ],
  spring: [
    ['MT 장기자랑 뭐 하지?', 'H.O.T. 「캔디」 춤 어때?'],
    ['중간고사 범위 어디까지야?', '몰라, 노트 좀 빌려줘.'],
    ['미팅 나갈 사람?', '나! 나!'],
    ['꽃 다 지기 전에 사진 찍자.', '이따 수업 끝나고!'],
  ],
  summer: [
    ['주점 메뉴 정했어?', '파전이랑 동동주!'],
    ['잔디밭에서 기타 치고 노래할까?', '좋다, 기타 가져올게.'],
    ['축제 때 연예인 온대.', '누구? 진짜?'],
    ['날씨 좋다, 수업 듣기 아깝다.', '그러게, 그냥 여기 앉아 있자.'],
  ],
  autumn: [
    ['응원 연습 가?', '응, 이번엔 꼭 이기자!'],
    ['은행잎 주워서 책갈피 만들까?', '아직도 그런 거 하냐?'],
    ['다들 취업 준비해?', '나 벌써 원서 쓰고 있어.'],
    ['가을 타나 봐. 시 쓰고 싶다.', '윤동주 시비 앞에 가서 써.'],
  ],
};
const PROF_TALK = {
  common: [['교수님, 리포트 마감 좀 미뤄 주시면 안 돼요?', '안 된다. 금요일까지야.'], ['교수님, 질문 있는데요.', '그래, 이따 연구실로 와.']],
  spring: [['교수님, 중간고사 범위가 어디까지예요?', '배운 데까지 다.']],
  summer: [['교수님, 축제 때 저희 주점 오세요!', '허허, 그래 들르마.']],
  autumn: [['교수님도 연고전 같이 가요!', '허허, 그날은 좀 바빠서…']],
};
const STAFF_TALK = {
  common: [['수고 많으세요.', '네, 학생도 공부 열심히 해요.']],
  spring: [['벚꽃 구경 온 사람이 많네요.', '이맘때면 늘 그래요.']],
  summer: [['요즘 학교가 축제로 시끌시끌하죠?', '네, 그래도 보기 좋아요.']],
  autumn: [['은행잎이 참 예쁘게 물들었어요.', '네, 지금이 제일 좋을 때예요.']],
};

// to you, coming up to a standing group; and from a walker you are standing in front of
const HELLO = {
  student: {
    common: ['어, 안녕!', '왔어? 이리 와.', '오랜만이다!', '어디 가는 길이야?'],
    spring: ['벚꽃 보러 가?', '중간고사 공부는 했어?'],
    summer: ['축제 때 우리 주점 와!', '날씨 좋지?'],
    autumn: ['연고전 같이 가자!', '시험 끝났어?'],
  },
  prof: { common: ['그래, 반갑다.', '어, 왔니?'] },
  staff: { common: ['안녕하세요.', '어서 와요.'] },
};
const EXCUSE = {
  student: { common: ['저기, 좀 지나갈게요.', '앗, 죄송해요.', '잠깐만 지나갈게요~'] },
  prof: { common: ['학생, 좀 지나가자.'] },
  staff: { common: ['학생, 좀 지나갈게요.'] },
};

// a random entry of table.common + table[season], the month's own more often, and not one heard just now
const recent = [];
function pick(table, season) {
  const own = table[season] || [], common = table.common || [];
  let it = null;
  for (let k = 0; k < 4; k++) {
    const list = own.length && (!common.length || Math.random() < 0.6) ? own : common;
    it = list[Math.floor(Math.random() * list.length)];
    if (!recent.includes(it)) break;
  }
  recent.push(it);
  if (recent.length > 12) recent.shift();
  return it;
}

// A dialogue as lines { who, text, wave }: who 0 is a, 1 is b; wave: the speaker raises a hand as they speak.
export function meeting(ka, kb, season) {
  if (ka === 'student' && kb === 'student') return pick(FRIENDS, season).map((text, i) => ({ who: i & 1, text, wave: i < 2 }));
  if (ka !== 'student' && kb !== 'student') return pick(ADULTS, season).map((text, i) => ({ who: i & 1, text, wave: i === 0 }));
  const st = ka === 'student' ? 0 : 1, elder = st ? ka : kb;
  return [
    { who: st, text: pick(elder === 'prof' ? TO_PROF : TO_STAFF, season), wave: false },
    { who: 1 - st, text: pick(elder === 'prof' ? PROF : STAFF, season), wave: true },
  ];
}

// a standing group: the two speakers' kinds; the student speaks first when only one is a student
export function chatter(ka, kb, season) {
  let t;
  if (ka === 'student' && kb === 'student') t = GROUP;
  else if (ka !== 'student' && kb !== 'student') t = ADULTS;
  else t = (ka === 'student' ? kb : ka) === 'prof' ? PROF_TALK : STAFF_TALK;
  const st = ka === 'student' || kb !== 'student' ? 0 : 1;
  return pick(t, season).map((text, i) => ({ who: i & 1 ? 1 - st : st, text, wave: false }));
}

export const hello = (kind, season) => pick(HELLO[kind], season);
export const excuse = (kind, season) => pick(EXCUSE[kind], season);

// seconds a line stays up: long enough to read
export const lineTime = (text) => Math.min(3.6, Math.max(2, 1.3 + text.length * 0.09));

// ---------------------------------------------------------------- speech bubbles
const SHOW = 26, POOL = 8;

export class Bubbles {
  constructor(layer, camera) {
    this.camera = camera;
    this.free = [];
    for (let i = 0; i < POOL; i++) {
      const el = document.createElement('div');
      el.className = 'bubble';
      el.style.display = 'none';
      layer.appendChild(el);
      this.free.push(el);
    }
    this.lines = [];
    this.v = new THREE.Vector3();
  }

  // text over a person's head (holder: the person's group in the scene; top: their height) from `from` to `to` s
  add(holder, top, text, from, to) { this.lines.push({ holder, top, text, from, to, el: null }); }

  release(l) {
    if (!l.el) return;
    l.el.style.display = 'none';
    this.free.push(l.el);
    l.el = null;
  }

  // visible: walking (not the title card or the bird's-eye view); far, off-screen and pending lines hold no bubble
  update(t, visible) {
    const W = innerWidth, H = innerHeight, v = this.v, cam = this.camera.position;
    if (this.lines.length) this.camera.updateMatrixWorld();      // the walker's camera has moved since the last render
    for (let i = this.lines.length - 1; i >= 0; i--) {
      const l = this.lines[i];
      if (t >= l.to) { this.release(l); this.lines.splice(i, 1); continue; }
      if (!visible || t < l.from || !l.holder.parent) { this.release(l); continue; }
      v.copy(l.holder.position);
      v.y += l.top + 0.3;
      const d = v.distanceTo(cam);
      if (d > SHOW) { this.release(l); continue; }
      v.project(this.camera);
      if (v.z > 1 || Math.abs(v.x) > 1.1 || v.y > 1.1 || v.y < -1) { this.release(l); continue; }
      if (!l.el) {
        l.el = this.free.pop();
        if (!l.el) continue;
        l.el.textContent = l.text;
        l.el.style.display = '';
      }
      const sx = ((v.x + 1) / 2) * W, sy = ((1 - v.y) / 2) * H - 8;
      const s = Math.min(1.1, Math.max(0.72, 1.22 - d * 0.022));
      const fade = Math.min(1, (t - l.from) / 0.15, (l.to - t) / 0.25, (SHOW - d) / 6);
      l.el.style.opacity = fade.toFixed(2);
      l.el.style.zIndex = String(Math.round(100 - d));
      l.el.style.transform = `translate(${sx.toFixed(1)}px, ${sy.toFixed(1)}px) translate(-50%, -100%) scale(${s.toFixed(3)})`;
    }
  }
}
