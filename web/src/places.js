// 출발할 곳 (title card): the memory spots and every named building (in AREAS below), each with where the walker stands and which way
// it faces.  A building's walker stands a few metres past the foot of its widest entrance flight, looking at the door
// (data/entrances.json: o at the door, v out along the flight, len its run); one without a flight steps out of its
// footprint to face the nearest wall.  A memory spot keeps its own ground (the card opens there), looking at its
// building's door, unless the door is close enough to still be inside the spot.
import { pointInPoly } from './player.js';

const segDist = ([x, y], [ax, ay], [bx, by]) => {
  const dx = bx - ax, dy = by - ay, l = dx * dx + dy * dy || 1;
  const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / l));
  return Math.hypot(x - ax - t * dx, y - ay - t * dy);
};
const polyDist = (p, poly) => (pointInPoly(p[0], p[1], poly) ? 0 : Math.min(...poly.map((a, i) => segDist(p, poly[i ? i - 1 : poly.length - 1], a))));
const yawTo = (dx, dy) => Math.atan2(-dx, dy);          // Player.teleport's yaw: the walker then faces (-sin yaw, cos yaw)
// a building whose flights give on a court too narrow to stand back in (의과대학: between its two halls, a wall 6 m
// before the door): where to stand instead, and the point of its wall to face (the long hall's open north-west side)
// 북문 is no hall but two frames the loop road runs between (고증 3.21: the gap's middle (15, 915), the road in from
// the east): on that road 10 m inside them, facing the gap. 무악학사's name stands in the middle of its first hall,
// between wings the walker could not get out from: on the bend of the road before the two halls (its 1997 line,
// 고증 3.21 「1학사 남쪽 굽은 길」), facing the court
// between them
const STAND = { 의과대학: { at: [128.9, -321.9], face: [134.5, -327.5] },
  북문: { at: [25.5, 918.0], face: [15.0, 915.0] }, 무악학사: { at: [141.0, 1156.6], face: [133.5, 1176.0] } };
// the places 350 - 600 m north of the campus map's sheet (campus.json markers): the map shows them in an inset
// (ui.js) and the tour pins them as it does the memory spots (main.js)
export const NORTH = ['북문', '무악학사'];

// the title card's list in areas, in the order a walk up from the gate meets them (main.js: one optgroup each, names in
// 가나다 order, the memory spots starred). A name in none of them goes under 그 밖, last
export const AREAS = [
  ['정문 · 백양로', ['정문', '백양로', '독수리상', '활천대', '백주년기념관', '연세대학교 박물관']],
  ['가운데: 도서관 · 학생회관 · 대강당', ['중앙도서관', '학생회관', '루스채플', '대강당', '음대 계단', '음악대학',
    '게시판 · 그때 우리는', '농구장', '족구장']],
  ['북쪽: 언더우드관 둘레', ['언더우드관', '스팀슨관', '아펜젤러관', '용재관', '노천극장', '청송대', '논지당', '핀슨관',
    '한경관', '경영학교실단', '광복관', '연합신학대학원', '언더우드가 사택', '인문관', '종합관', '청경관', '교육관',
    '제2인문관 (공사중)', '연희관', '성암관', '상대신관', '상대별관', '가정관']],
  ['서쪽: 공대 · 이과대 · 운동장', ['제1공학관', '제2공학관', '제3공학관 (공사중)', '공학원 (공사중)', '과학관', '연구관',
    '장기원 기념관', '체육관', '체육교육관', '대운동장', '학군단', '서문']],
  ['남동쪽: 세브란스 · 의료원', ['광혜원', '수경원 정자각', '제중관', '의과대학', '의료원 종합관', '의학도서관', '외래진료소',
    '임상의학연구센터', '안·이비인후과병원', '심장혈관병원', '특별병동', '재활병원', '간호학관', '간호대학', '치과대학',
    '치과대학병원', '동문회관', '행란사', '선우학사']],
  ['동쪽: 기숙사 · 한국어학당', ['한국어학당', '알렌관', '어린이생활지도연구원', '국제학사', '미우학사', '제중학사',
    '법현학사', '대학사택', '총장공관', '동문']],
  ['북문 · 무악학사', ['북문', '무악학사', '무악학사 3 · 4학사 (공사중)', '농업개발원', '우유처리장']],
  ['캠퍼스 밖: 신촌', ['신촌 로터리', '신촌역 (2호선)', '그랜드백화점', '그레이스백화점', '금강제화', '외환은행', '홍익문고']],
];
export const OTHER_AREA = '그 밖';
const areaOf = new Map(AREAS.flatMap(([a, names]) => names.map((n) => [n, a])));

// → [{ name, group, memory, x, y, yaw, front }] (group: its AREAS name; memory: a memory spot; front: standing at the
// door); resolve(x, y, r) pushes a circle out of the colliders
export function startPlaces(campus, zones, resolve) {
  const named = campus.buildings.filter((b) => b.name);
  // each flight belongs to the named footprint it sits on (within 6 m: the big landmark flights stand off the shell)
  const door = new Map();
  for (const z of zones) {
    let best = null, bd = 6;
    for (const b of named) {
      const d = polyDist(z.o, b.footprint);
      if (d < bd) { bd = d; best = b.name; }
    }
    if (best && !(door.get(best)?.hw >= z.hw)) door.set(best, z);
  }
  const centre = new Map();
  for (const b of named) {
    const n = b.footprint.length;
    if (!centre.has(b.name)) centre.set(b.name, b.footprint.reduce((a, p) => [a[0] + p[0] / n, a[1] + p[1] / n], [0, 0]));
  }
  const atDoor = (z) => {
    const d = z.len + 4;
    const [x, y] = resolve(z.o[0] + z.v[0] * d, z.o[1] + z.v[1] * d, 0.6);
    return { x, y, yaw: yawTo(-z.v[0], -z.v[1]), front: true };
  };
  // out of whatever stands at pos (a footprint) and 3 m back from it, facing it; on open ground, facing faceTo or,
  // with nothing to face (a statue, a fountain), 8 m back down the campus axis (the way up from the gate), facing pos
  const ahead = [-Math.sin(campus.spawn.yaw), Math.cos(campus.spawn.yaw)];
  const near = (pos, faceTo) => {
    let [x, y] = resolve(pos[0], pos[1], 0.6);
    let dx = pos[0] - x, dy = pos[1] - y, d = Math.hypot(dx, dy);
    if (d > 0.5) [x, y] = resolve(x - dx / d * 3, y - dy / d * 3, 0.6);
    else if (faceTo) { dx = faceTo[0] - x; dy = faceTo[1] - y; d = Math.hypot(dx, dy); }
    else {
      [x, y] = resolve(pos[0] - ahead[0] * 8, pos[1] - ahead[1] * 8, 0.6);
      dx = pos[0] - x; dy = pos[1] - y; d = Math.hypot(dx, dy);
    }
    return { x, y, yaw: d > 0.5 ? yawTo(dx, dy) : campus.spawn.yaw, front: false };
  };
  const out = [];
  for (const l of campus.landmarks) {
    if (!l.r || l.id === 'gate') continue;         // 정문: the walker's own spawn, the picker's default
    const z = door.get(l.name), at = z && atDoor(z);
    const p = at && Math.hypot(at.x - l.pos[0], at.y - l.pos[1]) < l.r ? at : near(l.pos, z ? z.o : centre.get(l.name));
    out.push({ name: l.name, group: areaOf.get(l.name) ?? OTHER_AREA, memory: true, ...p });
  }
  const taken = new Set(campus.landmarks.map((l) => l.name));
  const bld = (campus.markers || []).filter((m) => !taken.has(m.name)).sort((a, b) => a.name.localeCompare(b.name, 'ko'));
  for (const m of bld) {
    const z = door.get(m.name), s = STAND[m.name];
    const p = s ? { x: s.at[0], y: s.at[1], yaw: yawTo(s.face[0] - s.at[0], s.face[1] - s.at[1]), front: false } : z ? atDoor(z) : near(m.pos, null);
    out.push({ name: m.name, group: areaOf.get(m.name) ?? OTHER_AREA, memory: false, ...p });
  }
  return out;
}
