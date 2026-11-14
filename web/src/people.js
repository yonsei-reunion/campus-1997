// 캠퍼스 사람들 (people.html): every model of the cast on one page, without the campus. One renderer draws each
// person into the rectangle of their card (a scissored viewport over the page), so fourteen people cost one WebGL
// context. Drag turns them all (or the chips: front, right, back, left), other chips pick the clip everybody plays,
// a click opens one person large from the four sides at once; there the looks the crowd gives that model
// (characters.js crowdLook) can be tried on. people.html#<id> opens that person.
import * as THREE from 'three';
import { Cast, PEOPLE, STUDENTS, HEROES, HERO, crowdLook, play } from './characters.js';
import { HERO_BAGS, crowdBag } from './bags.js';
import { windTime } from './materials.js';

// the six you can walk as first (by their names and colleges), then the others
const IDS = [...HEROES, ...Object.keys(PEOPLE).filter((id) => !HEROES.includes(id))];
const title = (id) => (HERO[id] ? `${HERO[id].name} · ${HERO[id].college}` : PEOPLE[id]);
const sub = (id) => (HERO[id] ? PEOPLE[id] : kind(id));
const $ = (s) => document.querySelector(s);
const kind = (id) => (STUDENTS.includes(id) ? (id.startsWith('woman') ? '여학생' : '남학생') : id.endsWith('professor') ? '교수님' : '교직원');
// the clips to show: [label, clip, once]
const MOVES = [['서 있기', 'idle'], ['둘러보기', 'idle-look'], ['팔짱', 'idle-fold'], ['이야기', 'talk'], ['전화', 'phone'],
  ['인사', 'emote-yes', true], ['걷기', 'walk'], ['뛰기', 'sprint'], ['앉기', 'sit']];
// the sides to look from: the person turned by this much (0: facing the view; their left is +x)
const SIDES = [['앞', 0], ['오른쪽', Math.PI / 2], ['뒤', Math.PI], ['왼쪽', -Math.PI / 2]];
const SEAT = 0.43, THIGH = 0.085;       // a bench's seat and the hips over it (life.js)
const GAP = 12;                          // metres between two people in the one scene: each alone in their view

const canvas = $('#gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.AgXToneMapping;
renderer.setClearColor(0x000000, 0);
const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a7a66, 2.2));
const sun = new THREE.DirectionalLight(0xffffff, 2.4);
sun.position.set(2, 4, 3);
scene.add(sun);
const camera = new THREE.PerspectiveCamera(24, 1, 0.1, 60);

// the soft shade under a person, and the box they sit on
const blob = (() => {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d'), r = g.createRadialGradient(64, 64, 4, 64, 64, 62);
  r.addColorStop(0, 'rgba(40,36,30,.42)'); r.addColorStop(1, 'rgba(40,36,30,0)');
  g.fillStyle = r; g.fillRect(0, 0, 128, 128);
  const m = new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, toneMapped: false });
  const geo = new THREE.PlaneGeometry(1.1, 0.8).rotateX(-Math.PI / 2);
  return () => new THREE.Mesh(geo, m);
})();
const benchMat = new THREE.MeshStandardMaterial({ color: 0x8a7458, roughness: 0.9 });
const benchGeo = new THREE.BoxGeometry(0.62, SEAT, 0.42).translate(0, SEAT / 2, 0);

const cast = new Cast();
const slots = [];              // { id, el, x, a, pivot, bench, look }
let move = MOVES[0], yaw = 0.4, yawTo = null, spin = true, bags = false, dragUntil = 0, zoom = null, four = true, face = false;
const _v = new THREE.Vector3();

function dress(slot) {
  const { id } = slot;
  if (slot.a) { slot.pivot.remove(slot.a.holder); slot.a.mixer.stopAllAction(); }
  const n = slot.look;
  const bag = !bags || move[1] === 'sit' ? null : n == null ? HERO_BAGS[id] ?? crowdBag(id, 7) : crowdBag(id, n);
  slot.a = cast.make(id, bag, n == null ? null : crowdLook(id, n));
  slot.pivot.add(slot.a.holder);
  pose(slot);
}
function pose(slot) {
  const a = slot.a, [, clip, once] = move;
  a.holder.position.y = 0;
  slot.bench.visible = clip === 'sit';
  if (once) play(a, clip, { once: true, then: 'idle', fade: 0.2 });
  else play(a, a.actions[clip] ? clip : 'idle', { fade: 0.3 });
  if (clip === 'sit') {
    // the hips THIGH over the seat, as the game seats people (life.js)
    a.mixer.update(1);
    a.holder.updateMatrixWorld(true);
    const legs = ['UpperLegL', 'UpperLegR'].map((b) => a.root.getObjectByName(b)).filter(Boolean);
    const hip = legs.length ? legs.reduce((s, b) => s + b.getWorldPosition(_v).y, 0) / legs.length : 0.29 * a.tall;
    a.holder.position.y = SEAT + THIGH - hip;
  }
}
function addSlot(id, el, look = null) {
  const pivot = new THREE.Group();
  const slot = { id, el, x: slots.length * GAP, a: null, pivot, bench: new THREE.Mesh(benchGeo, benchMat), look };
  pivot.position.x = slot.x;
  slot.bench.position.z = -0.06;
  pivot.add(blob(), slot.bench);
  scene.add(pivot);
  slots.push(slot);
  dress(slot);
  return slot;
}

function setMove(m) {
  move = m;
  document.querySelectorAll('#moves button').forEach((b) => { b.classList.toggle('on', b.textContent === m[0]); b.setAttribute('aria-checked', b.textContent === m[0]); });
  // (a seated person carries no bag: dress() sees to it either way)
  for (const s of slots) if (bags) dress(s); else pose(s);
}

// ---------------------------------------------------------------- the page
for (const m of MOVES) {
  const b = document.createElement('button');
  b.type = 'button'; b.textContent = m[0]; b.setAttribute('role', 'radio');
  b.addEventListener('click', () => setMove(m));
  $('#moves').appendChild(b);
}
const setSpin = (on) => { spin = on; $('#spin').checked = on; };
for (const [label, to] of SIDES) {
  const b = document.createElement('button');
  b.type = 'button'; b.textContent = label;
  b.addEventListener('click', () => { setSpin(false); yawTo = to; });
  $('#sides').appendChild(b);
}
$('#spin').addEventListener('change', (e) => { spin = e.target.checked; yawTo = null; });
$('#bags').addEventListener('change', (e) => { bags = e.target.checked; for (const s of slots) dress(s); });

// drag on a person: everybody turns; a press without a drag opens that person
function turnable(el, onTap) {
  let x0 = null, moved = 0;
  el.addEventListener('pointerdown', (e) => { x0 = e.clientX; moved = 0; el.setPointerCapture?.(e.pointerId); });
  el.addEventListener('pointermove', (e) => {
    if (x0 === null) return;
    const dx = e.clientX - x0;
    x0 = e.clientX; moved += Math.abs(dx);
    yaw += dx * 0.012; yawTo = null;
    dragUntil = performance.now() + 2500;
  });
  const up = (e) => { if (x0 !== null && moved < 5 && e.type === 'pointerup') onTap?.(); x0 = null; };
  el.addEventListener('pointerup', up);
  el.addEventListener('pointercancel', up);
}

const zoomEl = $('#zoom'), zoomStage = zoomEl.querySelector('.stage.one'), quarters = [...zoomEl.querySelectorAll('.stage.q')];
function setFour(on) {
  four = on;
  zoomStage.hidden = on;
  for (const q of quarters) q.hidden = !on;
  zoomEl.querySelector('.mode').textContent = on ? '한 방향으로 크게' : '네 방향 한 번에';
}
zoomEl.querySelector('.mode').addEventListener('click', () => setFour(!four));
function setFace(on) { face = on; zoomEl.querySelector('.face').textContent = on ? '온몸 보기' : '얼굴 가까이'; }
zoomEl.querySelector('.face').addEventListener('click', () => setFace(!face));
function openZoom(id, push = true) {
  if (!PEOPLE[id] || !cast.models[id]) return;
  if (!zoom) zoom = addSlot(id, zoomStage);
  zoom.id = id; zoom.look = null;
  dress(zoom);
  zoomEl.querySelector('b').textContent = title(id);
  zoomEl.querySelector('small').textContent = sub(id) + (HERO[id] ? ` · ${HERO[id].place}에서 산책을 시작하는 주인공` : '');
  zoomEl.querySelector('.own').hidden = true;
  zoomEl.hidden = false;
  if (push && location.hash !== '#' + id) history.replaceState(null, '', '#' + id);
}
function closeZoom() {
  zoomEl.hidden = true;
  history.replaceState(null, '', location.pathname + location.search);
}
zoomEl.querySelector('.close').addEventListener('click', closeZoom);
zoomEl.addEventListener('click', (e) => { if (e.target === zoomEl) closeZoom(); });
addEventListener('keydown', (e) => { if (e.code === 'Escape' && !zoomEl.hidden) closeZoom(); });
zoomEl.querySelector('.other').addEventListener('click', () => {
  zoom.look = zoom.look == null ? 1 + Math.floor(Math.random() * 40) : zoom.look + 1;
  dress(zoom);
  zoomEl.querySelector('.own').hidden = false;
});
zoomEl.querySelector('.own').addEventListener('click', (e) => { zoom.look = null; dress(zoom); e.target.hidden = true; });
turnable(zoomStage);
for (const q of quarters) q.addEventListener('click', () => { yaw = +q.dataset.yaw * Math.PI; yawTo = null; setSpin(false); setFour(false); });
addEventListener('hashchange', () => { const id = location.hash.slice(1); if (PEOPLE[id]) openZoom(id, false); else if (!zoomEl.hidden) closeZoom(); });

// ---------------------------------------------------------------- drawing
function fit() {
  const w = innerWidth, h = innerHeight;
  if (canvas.width !== Math.round(w * renderer.getPixelRatio()) || canvas.height !== Math.round(h * renderer.getPixelRatio())) renderer.setSize(w, h, false);
  canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
  // (the canvas scrolls with the page between two frames, so the people do not lag behind their cards)
  canvas.style.transform = `translate(${scrollX}px, ${scrollY}px)`;
}
function draw(slot, el = slot.el) {
  const r = el.getBoundingClientRect(), H = innerHeight;
  if (r.bottom < 0 || r.top > H || r.right < 0 || r.left > innerWidth || r.width < 2) return;
  renderer.setViewport(r.left, H - r.bottom, r.width, r.height);
  renderer.setScissor(r.left, H - r.bottom, r.width, r.height);
  camera.aspect = r.width / r.height;
  // the whole person in view: 2.1 m of height at the person's place, or less of it across a narrow card; from near
  // (the opened person only) the head and the shoulders
  const near = face && slot === zoom;
  const top = (slot.id.startsWith('woman') ? 1.61 : 1.73) * slot.a.tall + slot.a.holder.position.y - (move[1] === 'sit' ? 0.42 * slot.a.tall : 0);
  const tall = near ? 0.62 : 2.1, wide = near ? 0.5 : /^(walk|sprint|sit|emote)/.test(move[1]) ? 1.25 : 0.92;
  const d = Math.max(tall, wide / camera.aspect) / 2 / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  const y = near ? top - 0.2 : 0.9;
  camera.position.set(slot.x, y + (near ? 0.02 : 0.12), d);
  camera.lookAt(slot.x, y, 0);
  camera.updateProjectionMatrix();
  renderer.render(scene, camera);
}
const clock = new THREE.Clock();
function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(clock.getDelta(), 0.1);
  windTime.value += dt;                       // (the blink's clock)
  if (yawTo !== null) {
    const d = Math.atan2(Math.sin(yawTo - yaw), Math.cos(yawTo - yaw));       // (the short way round)
    yaw += d * (1 - Math.exp(-dt * 9));
    if (Math.abs(d) < 1e-3) { yaw = yawTo; yawTo = null; }
  } else if (spin && performance.now() > dragUntil) yaw += dt * 0.35;
  fit();
  renderer.setScissorTest(false);
  renderer.clear();
  renderer.setScissorTest(true);
  const open = !zoomEl.hidden;
  for (const s of slots) {
    if ((s === zoom) !== open) continue;
    s.a.mixer.update(dt);
    if (s === zoom && four) {
      for (const q of quarters) { s.pivot.rotation.y = +q.dataset.yaw * Math.PI; draw(s, q); }
      continue;
    }
    s.pivot.rotation.y = yaw;
    draw(s);
  }
}

(async () => {
  const status = $('#status');
  let done = 0;
  try { await cast.load(IDS, () => { status.textContent = `사람들을 불러오는 중… ${Math.round(100 * ++done / (IDS.length + 2))}%`; }); }
  catch (e) { status.textContent = '사람들을 불러오지 못했습니다.'; console.error(e); return; }
  status.remove();
  const grid = $('#grid');
  for (const id of IDS) {
    const card = document.createElement('figure');
    card.className = 'card'; card.id = 'card-' + id;
    card.innerHTML = '<div class="stage"></div><figcaption><b></b><small></small></figcaption>';
    card.querySelector('b').textContent = title(id);
    card.querySelector('small').textContent = sub(id);
    if (HERO[id]) card.querySelector('b').insertAdjacentHTML('beforeend', '<em>주인공</em>');
    grid.appendChild(card);
    turnable(card.querySelector('.stage'), () => openZoom(id));
    addSlot(id, card.querySelector('.stage'));
  }
  setMove(MOVES[0]);
  if (PEOPLE[location.hash.slice(1)]) openZoom(location.hash.slice(1), false);
  window.__people = { slots, cast, scene, renderer, setMove, MOVES, openZoom, setFour, setFace, set yaw(v) { yaw = v; yawTo = null; }, set spin(v) { setSpin(v); } };
  frame();
})();
