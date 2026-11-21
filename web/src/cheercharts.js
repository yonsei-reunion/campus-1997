// 응원 연습의 박자표와 판정 창(cheer.js). three.js 를 읽지 않는 자료라 전체 순위의 Worker(notes-worker/src/rank.js)도
// 같은 것을 읽어 기록을 검사한다.

// the beats: a bar is eight eighth notes, c 박수 · u 만세 · s 어깨동무 (left and right by turns) · j 뛰기 · . nothing.
// 짝짝 짝짝짝 and 삼삼칠 박수 are the clapping everybody knew; the rest is made up for the game
export const CHARTS = [
  { id: 'easy', name: '천천히', bpm: 84, lead: 2.0, desc: '한 박에 하나씩. 박수와 만세부터',
    bars: ['c...c...', 'c...c...', 'c.c.c.c.', 'c.c.c.c.', 'u.......', 'u.......', 'c.c.u...', 'c.c.u...',
      's...s...', 's...s...', 's.s.s.s.', 'c.c.c.c.', 'j.......', 'j.......', 'c.c.u...', 'c.c.j...',
      's...s...', 's.s.s.s.', 'c.c.u...', 'u...j...'] },
  { id: 'normal', name: '보통', bpm: 100, lead: 1.6, desc: '짝짝 짝짝짝, 삼삼칠 박수가 섞여요',
    bars: ['c.c.c.c.', 'c.c.ccc.', 'c.c.c.c.', 'c.c.ccc.', 'u...u...', 'c.c.u...', 'u...u...', 'c.c.u.u.',
      's.s.s.s.', 's.s.s.s.', 'c.c.ccc.', 'u...j...', 'ccc.ccc.', 'ccccccc.', 's.s.s.s.', 'j...j...',
      'c.c.u...', 'c.c.u...', 's.s.c.c.', 's.s.c.c.', 'u.u.j...', 'ccc.ccc.', 'ccccccc.', 'u...j...'] },
  { id: 'hard', name: '빠르게', bpm: 124, lead: 1.25, desc: '엇박과 바뀌는 동작. 응원단 수준',
    bars: ['c.c.ccc.', 'c.c.ccc.', 'u.c.u.c.', 'u.c.u.c.', 's.s.s.s.', 's.s.cc.c', 'j...c.c.', 'j...u...',
      'ccc.ccc.', 'ccccccc.', 'u.cc.cu.', 's.s.u.u.', 'c.cc.cc.', 'u...j...', 's.s.s.cc', 's.s.s.u.',
      'j...c.c.', 'j...c.c.', 'uccucc..', 'u.u.j...', 's.s.c.cc', 's.s.u.cc', 'j...j...', 'c.c.ccc.',
      'ccc.ccc.', 'ccccccc.', 'u.s.u.s.', 'c.c.j...', 'cc.cc.u.', 'cc.cc.u.', 's.s.s.s.', 'u...j...'] },
];
export const chartOf = (id) => CHARTS.find((c) => c.id === id);
export const lengthOf = (c) => c.bars.length * 8 * 30 / c.bpm;

// timing windows (s either side of the beat) and what each is worth
export const JUDGE = [
  { w: 0.045, name: '최고!', cls: 'perfect', pts: 1000, acc: 1 },
  { w: 0.09, name: '좋아!', cls: 'great', pts: 700, acc: 0.7 },
  { w: 0.14, name: '괜찮아', cls: 'good', pts: 400, acc: 0.4 },
];
export const LATE = JUDGE[JUDGE.length - 1].w;

export function notesOf(c) {
  const e = 30 / c.bpm, out = [];
  let sway = 0;
  c.bars.forEach((b, m) => {
    for (let i = 0; i < 8; i++) {
      const lane = 'cusj'.indexOf(b[i]);
      if (lane < 0) continue;
      out.push({ t: (m * 8 + i) * e, lane, dir: lane === 2 ? (sway++ % 2 ? 1 : -1) : 0, hit: null, el: null });
    }
  });
  return out;
}
