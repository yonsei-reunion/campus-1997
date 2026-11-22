// 강의실 찾기의 시간표와 건물 사이 길이(timetable.js). three.js 를 읽지 않는 자료라 전체 순위의 Worker
// (notes-worker/src/rank.js)도 같은 것을 읽어 기록을 검사한다.
import { RUN } from './pace.js';

// the halls with lecture rooms in 1997 (their 1997 names: 고증 3.1; halls built later are not in the game) and the
// way between their doors in metres: the walker's colliders, A* over a 1 m grid from door to door (places.js: where
// the walker stands 4 m past the foot of the widest flight), measured headless on the campus of 2026-11-21
// (장기원 기념관's row on 2026-11-22, the same A*; toward 과학관 it finds no way, so 과학관 → 장기원 기념관).
// HALLS[i]'s ways to HALLS[0 .. i - 1] are WAY[i]
export const HALLS = ['인문관', '종합관', '연희관', '성암관', '교육관', '가정관', '광복관', '용재관', '상대신관', '상대별관', '경영학교실단', '과학관', '제1공학관',
  '아펜젤러관', '음악대학', '체육교육관', '대강당', '연합신학대학원', '장기원 기념관'];
export const WAY = [[], [127], [178, 164], [190, 205, 46], [135, 143, 44, 76], [200, 132, 93, 137, 89],
  [253, 329, 396, 383, 353, 430], [188, 289, 243, 197, 225, 313, 243],
  [285, 238, 159, 165, 162, 109, 515, 361], [286, 245, 119, 125, 162, 117, 508, 321, 51],
  [193, 296, 302, 274, 259, 340, 188, 86, 421, 397],
  [355, 431, 514, 513, 471, 548, 145, 396, 633, 631, 312],
  [564, 659, 689, 655, 646, 727, 342, 462, 808, 779, 387, 320],
  [152, 202, 154, 108, 139, 226, 299, 90, 272, 232, 166, 453, 548],
  [471, 565, 483, 437, 482, 572, 433, 309, 584, 534, 302, 545, 443, 363],
  [455, 525, 598, 585, 555, 632, 222, 440, 717, 710, 356, 155, 227, 501, 544],
  [249, 353, 339, 293, 299, 387, 221, 99, 457, 416, 70, 345, 364, 185, 243, 377],
  [85, 186, 265, 263, 222, 285, 168, 199, 371, 371, 178, 270, 488, 189, 462, 365, 239],
  [305, 389, 448, 442, 405, 482, 72, 278, 567, 560, 194, 119, 275, 351, 428, 161, 225, 230]];
export const wayOf = (a, b) => {
  const i = HALLS.indexOf(a), j = HALLS.indexOf(b);
  return i < 0 || j < 0 || i === j ? 0 : i > j ? WAY[i][j] : WAY[j][i];
};
// the break: the way at running pace, two fifths more for the turns and the doubt, and 20 s to get going (checked
// headless: a walker running the A* way, held up where steps and low walls are, makes every break of every timetable).
// (제2공학관 is not in: its door is on the court between it and 제3공학관, up flights a walker coming at it from
// below finds only by going round)
export const breakOf = (m) => Math.ceil((m / RUN * 1.4 + 20) / 5) * 5;

// the timetables: [class, hall] for 1 – 4교시 (a class every hour on the hour). The subjects are a game's, under
// their 1997 names where known (고증 4.15). The ids changed with the halls (liberal · commerce · eng had 대학영어
// in 종합관, science 교양체육 in 체육교육관 and 기독교의 이해 in 종합관), so the boards of the old ways are not mixed in
export const SETS = [
  { id: 'arts', name: '문과대학', classes: [['국어학개론', '인문관'], ['교양영어', '경영학교실단'], ['사회학개론', '연희관'], ['채플', '대강당']] },
  { id: 'sci', name: '이과대학', classes: [['일반물리학', '과학관'], ['체력 단련', '용재관'], ['채플', '대강당'], ['기독교와 타종교와의 대화', '장기원 기념관']] },
  { id: 'econ', name: '상경대학', classes: [['경제원론', '상대신관'], ['교양영어', '경영학교실단'], ['채플', '대강당'], ['회계원리', '상대별관']] },
  { id: 'engr', name: '공과대학', classes: [['공업수학', '제1공학관'], ['미적분학', '과학관'], ['채플', '대강당'], ['교양영어', '경영학교실단']] },
];
// the halls whose class is always the same (오늘의 시간표 too); the rest draw from SUBJECTS
export const FIXED = { 대강당: '채플', 경영학교실단: '교양영어', '장기원 기념관': '기독교와 타종교와의 대화', 용재관: '체력 단련' };
export const SUBJECTS = ['철학개론', '글과 삶', '말과 삶', '통계학(1)', '심리학개론', '일반생물학', '경제원론', '일의 세계와 심리학', '청년기 갈등과 자기 이해', '연극의 이해'];

// 오늘의 시간표: four halls drawn from the day's date (the same for everyone that day), each break 120 – 480 m
// (상대신관's door is up the horseshoe flights over 상뜰, which a walker coming from 백양로 finds late: a first class
// only)
export const START_ONLY = ['상대신관'];
export const dayKey = (d = new Date()) => `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
export function todaySet(key = dayKey()) {
  let s = +key >>> 0;
  const rnd = () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const pick = (a) => a[Math.floor(rnd() * a.length)];
  for (let tries = 0; tries < 200; tries++) {
    const halls = [pick(HALLS)];
    while (halls.length < 4) {
      const last = halls[halls.length - 1];
      const ok = HALLS.filter((h) => !halls.includes(h) && !START_ONLY.includes(h) && wayOf(last, h) >= 120 && wayOf(last, h) <= 480);
      if (!ok.length) break;
      halls.push(pick(ok));
    }
    if (halls.length < 4) continue;
    const subj = [...SUBJECTS];
    const classes = halls.map((h) => [FIXED[h] || subj.splice(Math.floor(rnd() * subj.length), 1)[0], h]);
    return { id: `today-${key}`, name: '오늘의 시간표', today: true, classes };
  }
  return { ...SETS[0], id: `today-${key}`, name: '오늘의 시간표', today: true };
}
export const setOf = (id) => (id?.startsWith('today') ? todaySet() : SETS.find((s) => s.id === id));
export const legsOf = (set) => set.classes.slice(1).map(([, h], k) => breakOf(wayOf(set.classes[k][1], h)));
