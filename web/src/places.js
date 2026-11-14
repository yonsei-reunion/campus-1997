// 출발할 곳 (title card): the memory spots and every named building, each with where the walker stands and which way
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
const STAND = { 의과대학: { at: [128.9, -321.9], face: [134.5, -327.5] } };

// → [{ name, group, x, y, yaw, front }] (front: standing at the door); resolve(x, y, r) pushes a circle out of the colliders
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
    out.push({ name: l.name, group: '추억 장소', ...p });
  }
  const taken = new Set(campus.landmarks.map((l) => l.name));
  const bld = (campus.markers || []).filter((m) => !taken.has(m.name)).sort((a, b) => a.name.localeCompare(b.name, 'ko'));
  for (const m of bld) {
    const z = door.get(m.name), s = STAND[m.name];
    const p = s ? { x: s.at[0], y: s.at[1], yaw: yawTo(s.face[0] - s.at[0], s.face[1] - s.at[1]), front: false } : z ? atDoor(z) : near(m.pos, null);
    out.push({ name: m.name, group: '건물', ...p });
  }
  return out;
}
