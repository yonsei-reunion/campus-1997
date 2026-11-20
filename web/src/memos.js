// 캠퍼스 쪽지: anyone leaves a sticky note where they stand (on the wall in front of them, or on a little stake in the
// ground when no wall is near), anyone reads it, anyone takes it off. The notes live in a public DoltHub database
// (benelog/yonsei-1997, table notes): read straight from DoltHub (no token: a public read), written through a small
// Cloudflare Worker (notes-worker/), which holds the token, since DoltHub's CORS lets no browser send one.
// Notes come and go with the wind: one taken off here, or gone from the list when it is read again, blows away.
// A note: { id, text, name, color, x, y (campus), z (its top edge, 해발 = the game's height), yaw (the way it faces,
// campus: (sin, cos), 0 = north), kind ('wall' | 'stake'), place (the place name where it was put), created_at (UTC) }.
import * as THREE from 'three';
import { $, safeGet, safeSet, MOBILE } from './util.js';
import './memos.css';

const READ = 'https://www.dolthub.com/api/v1alpha1/benelog/yonsei-1997/main';
export const WRITE = new URLSearchParams(location.search).get('notesapi') || 'https://y97-notes.habit-chain-worker.workers.dev';
const NAME_KEY = 'y97-memo-name';
const MAX_TEXT = 100, MAX_NAME = 12, SHOW = 300;
const SIZE = 0.4;                  // m: the paper's side (a real one is 7.6 cm: unseen past a few steps)
const STAKE = 1.3;                 // m: the paper's top edge over the ground on a stake
const REACH = 3;                   // m: how far ahead a wall takes the note
const NEAR = 2.6;                  // m: the prompt to read it
const SEEN = 160, TEXTURED = 45;   // m: drawn within, its writing drawn within
export const COLORS = { yellow: '#ffef7a', pink: '#ffbdd3', mint: '#bdf0d9', blue: '#bfdcff', orange: '#ffd08f' };
const COLOR_NAMES = { yellow: '노랑', pink: '분홍', mint: '민트', blue: '하늘', orange: '주황' };
const WIND = new THREE.Vector3(0.85, 0, 0.45).normalize();     // (three: blowing to the east and a little south)

const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
const at = (s) => new Date(String(s).replace(' ', 'T') + 'Z');
export function ago(s) {
  const d = at(s), sec = (Date.now() - d) / 1000;
  if (!(sec >= 0)) return '';
  if (sec < 60) return '방금';
  if (sec < 3600) return `${Math.floor(sec / 60)}분 전`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}시간 전`;
  if (sec < 7 * 86400) return `${Math.floor(sec / 86400)}일 전`;
  const y = d.getFullYear() !== new Date().getFullYear() ? `${d.getFullYear()}년 ` : '';
  return `${y}${d.getMonth() + 1}월 ${d.getDate()}일`;
}
const row = (r) => ({
  id: String(r.id), text: String(r.text ?? ''), name: String(r.name ?? ''), color: COLORS[r.color] ? r.color : 'yellow',
  x: +r.x, y: +r.y, z: +r.z, yaw: +r.yaw, kind: r.kind === 'stake' ? 'stake' : 'wall', place: String(r.place ?? ''), created_at: String(r.created_at ?? ''),
});

// the paper: a square hung from its top edge (the hinge at the origin), its lower half curling off the wall a little
function paperGeometry() {
  const g = new THREE.PlaneGeometry(SIZE, SIZE, 2, 6);
  g.translate(0, -SIZE / 2, 0);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const t = -p.getY(i) / SIZE, side = Math.abs(p.getX(i)) / (SIZE / 2);
    p.setZ(i, 0.004 + 0.035 * t * t * t + 0.008 * t * side * side);
  }
  g.computeVertexNormals();
  return g;
}

// the note's face: the colour, the sticky strip, the writing, the name
function drawPaper(cv, n, font) {
  const W = cv.width, x = cv.getContext('2d');
  x.fillStyle = COLORS[n.color]; x.fillRect(0, 0, W, W);
  const g = x.createLinearGradient(0, 0, 0, W);
  g.addColorStop(0, 'rgba(0,0,0,.10)'); g.addColorStop(0.16, 'rgba(0,0,0,.03)'); g.addColorStop(0.17, 'rgba(0,0,0,0)');
  g.addColorStop(0.85, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.08)');
  x.fillStyle = g; x.fillRect(0, 0, W, W);
  x.fillStyle = '#26324a'; x.textBaseline = 'top';
  const pad = W * 0.09, maxW = W - pad * 2, top = W * 0.16, bottom = W * (n.name ? 0.8 : 0.92);
  // the largest size the writing fits the paper at
  let size = W * 0.16, lines = [];
  for (; size > W * 0.055; size *= 0.9) {
    x.font = `${Math.round(size)}px ${font}`;
    lines = wrap(x, n.text, maxW);
    if (lines.length * size * 1.22 <= bottom - top) break;
  }
  lines.forEach((l, i) => { if (top + (i + 1) * size * 1.22 <= bottom + size) x.fillText(l, pad, top + i * size * 1.22); });
  if (n.name) {
    x.font = `${Math.round(W * 0.085)}px ${font}`;
    x.textAlign = 'right';
    x.fillText(`— ${n.name}`, W - pad, W * 0.84);
    x.textAlign = 'left';
  }
}
function wrap(x, text, maxW) {
  const out = [];
  for (const para of text.split('\n')) {
    let line = '';
    for (const ch of [...para]) {
      if (x.measureText(line + ch).width > maxW && line) { out.push(line); line = ch.trim() ? ch : ''; } else line += ch;
    }
    out.push(line);
  }
  return out;
}

export class Memos {
  // walls: the meshes a note sticks to (player.walls); placeAt(x, y): the place name; onGo(note): walk to it;
  // onOpen() / onClose(): a card of ours opened / closed (main.js stops / lets go of the walker); patch: the scene's
  // atmosphere for our materials; toast(text)
  constructor({ scene, camera, player, canvas, walls, placeAt, onGo, onOpen, onClose, patch = (m) => m, toast = () => {}, canPick = () => true }) {
    Object.assign(this, { scene, camera, player, walls, placeAt, onGo, onOpen, onClose, patch, toast, canPick });
    this.notes = new Map();          // id → { n, root, hinge, paper, tex, ph }
    this.flying = [];                // blowing away: { root, v, spin, t }
    this.group = new THREE.Group();
    this.group.name = 'memos';
    scene.add(this.group);
    this.geo = paperGeometry();
    this.stakeGeo = new THREE.CylinderGeometry(0.018, 0.022, STAKE + 0.08, 6).translate(0, -(STAKE + 0.08) / 2 + 0.06, -0.025);
    this.stakeMat = patch(new THREE.MeshStandardMaterial({ color: 0x8a6a46, roughness: 0.9 }));
    this.plain = {};                 // colour → the material of a far note (no writing)
    for (const [k, c] of Object.entries(COLORS)) this.plain[k] = patch(new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, side: THREE.DoubleSide }));
    this.font = '"Jua", "Noto Sans KR", sans-serif';
    this.fontReady = document.fonts?.load?.(`40px ${this.font}`).catch(() => {}) ?? Promise.resolve();
    this.ray = new THREE.Raycaster();
    this.ray.firstHitOnly = true;
    this.loaded = false;
    this.listeners = new Set();
    this._t = 0; this._near = 0;
    this._bindPick(canvas);
    this._buildCards();
  }

  // ---------------------------------------------------------------- data
  async load() {
    if (this._loading) return this._loading;
    this._loading = (async () => {
      const q = `SELECT id, text, name, color, x, y, z, yaw, kind, place, created_at FROM notes ORDER BY created_at DESC LIMIT ${SHOW}`;
      try {
        const r = await fetch(`${READ}?q=${encodeURIComponent(q)}`, { cache: 'no-store' });
        const j = await r.json();
        if (j.query_execution_status !== 'Success') throw new Error(j.query_execution_message || 'DoltHub');
        this._sync((j.rows || []).map(row).filter((n) => Number.isFinite(n.x + n.y + n.z + n.yaw)));
        this.loaded = true;
        this.error = null;
      } catch (e) {
        this.error = e;
      } finally {
        this._loading = null;
        this._changed();
      }
    })();
    return this._loading;
  }
  // what came back is what hangs now: new ones put up, the ones gone blow away (but not one of ours still going up)
  _sync(list) {
    const keep = new Set(list.map((n) => n.id));
    for (const [id, o] of this.notes) if (!keep.has(id) && !o.pending) this._blow(id);
    for (const n of list) if (!this.notes.has(n.id)) this._put(n);
  }
  get list() { return [...this.notes.values()].map((o) => o.n).sort((a, b) => (a.created_at < b.created_at ? 1 : -1)); }
  _changed() { for (const f of this.listeners) f(); }

  async _send(method, path, body) {
    const r = await fetch(WRITE + path, { method, headers: body ? { 'content-type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
    let j = {};
    try { j = await r.json(); } catch { /* not JSON */ }
    if (!r.ok) throw new Error(j.error || `${r.status}`);
    return j;
  }

  // ---------------------------------------------------------------- the notes in the scene
  _put(n, pending = false) {
    const root = new THREE.Group(), hinge = new THREE.Group();
    root.position.set(n.x, n.z, -n.y);
    root.rotation.y = Math.PI - n.yaw;                // (the paper's front, local +z, the way it faces)
    root.add(hinge);
    if (n.kind === 'stake') root.add(new THREE.Mesh(this.stakeGeo, this.stakeMat));
    const paper = new THREE.Mesh(this.geo, this.plain[n.color]);
    paper.userData.memo = n.id;
    hinge.add(paper);
    root.userData.memo = n.id;
    this.group.add(root);
    const o = { n, root, hinge, paper, tex: null, ph: Math.random() * 100, pending };
    this.notes.set(n.id, o);
    return o;
  }
  _texture(o, on) {
    if (on === !!o.tex) return;
    if (!on) {
      o.tex.map.dispose(); o.tex.dispose(); o.tex = null;
      o.paper.material = this.plain[o.n.color];
      return;
    }
    const cv = document.createElement('canvas');
    cv.width = cv.height = 256;
    drawPaper(cv, o.n, this.font);
    const map = new THREE.CanvasTexture(cv);
    map.colorSpace = THREE.SRGBColorSpace;
    map.anisotropy = 4;
    o.tex = this.patch(new THREE.MeshStandardMaterial({ map, roughness: 0.85, side: THREE.DoubleSide }));
    o.paper.material = o.tex;
    this.fontReady.then(() => { if (o.tex?.map === map) { drawPaper(cv, o.n, this.font); map.needsUpdate = true; } });
  }
  // taken off: it lets go of the wall and the wind carries it off, tumbling, up and away
  _blow(id) {
    const o = this.notes.get(id);
    if (!o) return;
    this.notes.delete(id);
    o.root.userData.memo = null;
    o.paper.userData.memo = null;
    const v = WIND.clone().multiplyScalar(2.2 + Math.random() * 1.5);
    v.y = 1.2 + Math.random() * 0.8;
    // (a stake stays where it was a moment, then goes with the paper)
    this.flying.push({ o, v, spin: new THREE.Vector3((Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6), t: 0 });
    this._changed();
  }
  _drop(f) {
    this.group.remove(f.o.root);
    if (f.o.tex) { f.o.tex.map.dispose(); f.o.tex.dispose(); }
  }

  update(dt, t) {
    this._t = t;
    // the flutter: a breeze lifting the paper's foot off the wall (more on a stake)
    const cam = this.camera.position;
    const check = t - this._near > 0.4;
    if (check) this._near = t;
    for (const o of this.notes.values()) {
      if (check) {
        const d = o.root.position.distanceTo(cam);
        o.root.visible = d < SEEN;
        this._texture(o, d < TEXTURED);
        o.close = d < 40;
      }
      if (!o.close) continue;
      const gust = 0.55 + 0.45 * Math.sin(t * 0.43 + o.ph * 1.7);
      const flap = (0.5 + 0.5 * Math.sin(t * 2.1 + o.ph)) * 0.7 + 0.3 * (0.5 + 0.5 * Math.sin(t * 5.3 + o.ph * 3.1));
      o.hinge.rotation.x = -(o.n.kind === 'stake' ? 0.06 + 0.22 * gust * flap : 0.02 + 0.11 * gust * flap);
      o.hinge.rotation.z = o.n.kind === 'stake' ? 0.05 * Math.sin(t * 1.3 + o.ph) * gust : 0;
    }
    for (let i = this.flying.length - 1; i >= 0; i--) {
      const f = this.flying[i], r = f.o.root;
      f.t += dt;
      f.v.addScaledVector(WIND, dt * 1.8);
      f.v.y += dt * (0.6 - f.t * 0.35);
      r.position.addScaledVector(f.v, dt);
      f.o.hinge.rotation.x += f.spin.x * dt; f.o.hinge.rotation.y += f.spin.y * dt; f.o.hinge.rotation.z += f.spin.z * dt;
      const k = Math.max(0, 1 - f.t / 3.5);
      f.o.hinge.scale.setScalar(0.3 + 0.7 * k);
      if (f.o.root.children.length > 1 && f.t > 0.25) f.o.root.children[1].visible = false;      // (the stake: gone)
      if (f.t > 3.5) { this._drop(f); this.flying.splice(i, 1); }
    }
  }

  // the nearest note within reach of the walker (and on its level), or null
  nearest(x, y, h) {
    let best = null, bd = NEAR;
    for (const o of this.notes.values()) {
      const n = o.n, d = Math.hypot(n.x - x, n.y - y);
      if (d < bd && Math.abs(n.z - 1.5 - h) < 2.5) { bd = d; best = n; }
    }
    return best;
  }

  // a tap or a click on a note (no drag between down and up) reads it
  _bindPick(dom) {
    if (!dom) return;
    let sx = 0, sy = 0;
    dom.addEventListener('pointerdown', (e) => { sx = e.clientX; sy = e.clientY; });
    dom.addEventListener('pointerup', (e) => {
      if (Math.hypot(e.clientX - sx, e.clientY - sy) > 6 || !this.canPick() || this.open) return;
      const r = dom.getBoundingClientRect();
      this.ray.setFromCamera(new THREE.Vector2((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1), this.camera);
      this.ray.far = 30;
      const papers = [...this.notes.values()].filter((o) => o.close).map((o) => o.paper);
      const hit = this.ray.intersectObjects(papers, false)[0];
      if (hit) this.read(this.notes.get(hit.object.userData.memo)?.n, false);
    });
  }

  // where a note would go now: the nearest wall ahead within reach at chest height (straight ahead, or up to 35° to
  // either side), else a stake a step ahead
  spot() {
    const p = this.player, cam = this.camera;
    const f = cam.getWorldDirection(new THREE.Vector3());
    f.y = 0;
    if (f.lengthSq() < 1e-6) f.set(-Math.sin(p.yaw), 0, -Math.cos(p.yaw));
    f.normalize();
    const from = new THREE.Vector3(p.pos.x, p.pos.y + 1.35, p.pos.z), dir = new THREE.Vector3();
    this.ray.far = REACH;
    let best = null;
    for (const a of [0, 0.3, -0.3, 0.6, -0.6]) {
      dir.set(f.x * Math.cos(a) - f.z * Math.sin(a), 0, f.x * Math.sin(a) + f.z * Math.cos(a));
      this.ray.set(from, dir);
      const hit = this.ray.intersectObjects(this.walls, false)[0];
      if (!hit?.face || (best && hit.distance >= best.distance)) continue;
      const nrm = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
      if (nrm.dot(dir) > 0) nrm.negate();                 // (a face seen from behind: the side the walker is on)
      if (Math.abs(nrm.y) > 0.45) continue;               // (a sill, a step: not a wall)
      nrm.y = 0; nrm.normalize();
      best = { distance: hit.distance, point: hit.point, nrm };
    }
    if (best) {
      const q = best.point.clone().addScaledVector(best.nrm, 0.012);
      return { x: q.x, y: -q.z, z: q.y + SIZE / 2, yaw: Math.atan2(best.nrm.x, -best.nrm.z), kind: 'wall' };
    }
    // no wall: a stake 1.2 m ahead, the paper facing the walker
    const sx = p.pos.x + f.x * 1.2, sz = p.pos.z + f.z * 1.2;
    const g = p.groundAt(sx, sz, p.pos.y + 1.5) ?? p.pos.y;
    return { x: sx, y: -sz, z: g + STAKE, yaw: Math.atan2(-f.x, f.z), kind: 'stake' };
  }

  // ---------------------------------------------------------------- cards
  get open() { return !this.writeEl.hidden || !this.readEl.hidden || !this.listEl.hidden; }

  _modal(id, cls) {
    const root = el('div', 'memo-modal');
    root.id = id;
    root.hidden = true;
    const card = el('article', `memo-card ${cls}`);
    root.appendChild(card);
    document.body.appendChild(root);
    root.addEventListener('click', (e) => { if (e.target === root) this._close(root); });
    return [root, card];
  }
  _close(root) {
    if (root.hidden) return;
    root.hidden = true;
    if (root === this.writeEl) this._preview(null);
    if (root === this.readEl && this._fromList) { this._fromList = false; this.listEl.hidden = false; return; }
    if (!this.open) this.onClose();
  }
  closeAll() { for (const r of [this.writeEl, this.readEl, this.listEl]) r.hidden = true; this._preview(null); this._fromList = false; }

  _buildCards() {
    this._buildWrite();
    this._buildRead();
    this._buildList();
    // Esc: our card first (before main.js: the capture phase)
    addEventListener('keydown', (e) => {
      if (!this.open || e.code !== 'Escape') return;
      e.stopImmediatePropagation();
      e.preventDefault();
      const top = !this.readEl.hidden ? this.readEl : !this.writeEl.hidden ? this.writeEl : this.listEl;
      this._close(top);
    }, true);
  }

  // 쪽지 남기기
  _buildWrite() {
    const [root, c] = this._modal('memo-write', 'memo-writecard');
    this.writeEl = root;
    c.innerHTML = `<h2>쪽지 남기기 <small class="where"></small></h2>
      <div class="memo-paper"><textarea maxlength="${MAX_TEXT}" rows="5" placeholder="하고 싶은 말을 적어 보세요"></textarea>
        <input class="memo-name" maxlength="${MAX_NAME}" placeholder="이름 (안 적어도 돼요)" autocomplete="nickname" />
        <span class="count"></span></div>
      <div class="memo-colors" role="radiogroup" aria-label="쪽지 색"></div>
      <p class="memo-wind">🍃 쪽지는 바람에 날려 언제든 없어질 수 있어요. 누구나 읽고, 누구나 뗄 수 있어요. 연락처 같은 개인 정보는 적지 마세요.</p>
      <div class="memo-row"><button type="button" class="ghost cancel">그만두기</button><button type="button" class="ok">붙이기</button></div>`;
    const colors = c.querySelector('.memo-colors');
    for (const [k, v] of Object.entries(COLORS)) {
      const b = el('button');
      b.type = 'button'; b.dataset.color = k; b.style.background = v; b.title = COLOR_NAMES[k]; b.setAttribute('aria-label', COLOR_NAMES[k]);
      b.addEventListener('click', () => this._pick(k));
      colors.appendChild(b);
    }
    const ta = c.querySelector('textarea'), count = c.querySelector('.count'), ok = c.querySelector('.ok');
    const counted = () => { const n = [...ta.value].length; count.textContent = `${n} / ${MAX_TEXT}`; ok.disabled = !ta.value.trim() || this._posting; };
    ta.addEventListener('input', counted);
    this._counted = counted;
    c.querySelector('.cancel').addEventListener('click', () => this._close(root));
    c.querySelector('.ok').addEventListener('click', () => this._post());
    ta.addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); this._post(); } });
  }

  // 쪽지 읽기
  _buildRead() {
    const [root, c] = this._modal('memo-read', 'memo-readcard');
    this.readEl = root;
    c.innerHTML = `<div class="memo-paper big"><p class="text"></p><p class="sign"></p></div>
      <p class="memo-meta"></p>
      <p class="memo-wind small">🍃 바람에 날려 언제든 없어질 수 있는 쪽지예요</p>
      <div class="memo-row"><button type="button" class="go">그곳으로 가기</button><button type="button" class="ghost del">떼어 내기</button><button type="button" class="close">닫기</button></div>`;
    c.querySelector('.close').addEventListener('click', () => this._close(root));
    c.querySelector('.go').addEventListener('click', () => { const n = this._reading; if (!n) return; this.closeAll(); this.onGo(n); });
    c.querySelector('.del').addEventListener('click', () => this._remove());
  }

  // 쪽지 목록
  _buildList() {
    const [root, c] = this._modal('memo-list', 'memo-listcard');
    this.listEl = root;
    c.innerHTML = `<h2>캠퍼스 쪽지 <small class="count"></small></h2>
      <p class="memo-wind">🍃 쪽지는 바람에 날려 언제든 없어질 수 있어요. 누르면 쪽지를 읽고, 「가기」를 누르면 쪽지가 붙은 곳으로 가요.</p>
      <ul class="memo-items"></ul>
      <button type="button" class="close">닫기</button>`;
    c.querySelector('.close').addEventListener('click', () => this._close(root));
    this.listeners.add(() => { if (!this.listEl.hidden) this._fillList(); });
  }

  _pick(color) {
    this._color = color;
    safeSet('y97-memo-color', color);
    const c = this.writeEl;
    c.querySelector('.memo-paper').style.background = COLORS[color];
    c.querySelectorAll('.memo-colors button').forEach((b) => b.classList.toggle('on', b.dataset.color === color));
    if (this._ghost) this._ghost.paper.material = this.plain[color];
  }
  // where the note will go while it is being written: a plain paper of the colour picked
  _preview(s) {
    if (this._ghost) { this.group.remove(this._ghost.root); this._ghost = null; }
    if (!s) return;
    const n = { ...s, id: '', color: this._color, text: '' };
    const o = this._put(n);
    this.notes.delete('');
    o.paper.userData.memo = null;
    o.root.userData.memo = null;
    this._ghost = o;
  }

  openWrite() {
    if (this.open) return;
    const s = this.spot();
    this._spot = s;
    this._spot.place = this.placeAt(s.x, s.y);
    const c = this.writeEl;
    c.querySelector('.where').textContent = `${s.kind === 'wall' ? '앞의 벽에 붙여요' : '작은 말뚝에 꽂아요'} · ${this._spot.place}`;
    const ta = c.querySelector('textarea');
    ta.value = '';
    c.querySelector('.memo-name').value = safeGet(NAME_KEY) || '';
    this._posting = false;
    c.querySelector('.ok').textContent = '붙이기';
    this._pick(COLORS[safeGet('y97-memo-color')] ? safeGet('y97-memo-color') : 'yellow');
    this._counted();
    this._preview(s);
    c.hidden = false;
    this.onOpen();
    if (!MOBILE) setTimeout(() => ta.focus({ preventScroll: true }), 30);
  }

  async _post() {
    const c = this.writeEl, ta = c.querySelector('textarea');
    const text = ta.value.trim(), name = c.querySelector('.memo-name').value.trim();
    if (!text || this._posting) return;
    if ([...text].length > MAX_TEXT) return;
    safeSet(NAME_KEY, name);
    this._posting = true;
    const ok = c.querySelector('.ok');
    ok.disabled = true; ok.textContent = '붙이는 중…';
    const s = this._spot;
    const body = { text, name, color: this._color, x: s.x, y: s.y, z: s.z, yaw: s.yaw, kind: s.kind, place: s.place };
    // up at once (the database takes a couple of seconds); the id comes back with the answer
    const tmp = `tmp-${Date.now()}`;
    const n = { ...body, id: tmp, created_at: new Date().toISOString().slice(0, 19).replace('T', ' ') };
    this._preview(null);
    const o = this._put(n, true);
    c.hidden = true;
    if (!this.open) this.onClose();
    this.toast('쪽지를 붙였어요 · 바람이 불면 날아갈 수도 있어요');
    this._changed();
    try {
      const r = await this._send('POST', '/', body);
      this.notes.delete(tmp);
      n.id = r.id; n.created_at = r.created_at || n.created_at;
      o.paper.userData.memo = o.root.userData.memo = r.id;
      o.pending = false;
      this.notes.set(r.id, o);
      this._changed();
    } catch (e) {
      o.pending = false;
      this._blow(tmp);
      this.toast(`쪽지가 바람에 날아갔어요 (붙이지 못함: ${e.message})`, 4500);
    } finally {
      this._posting = false;
    }
  }

  // read: the note on a big paper. fromList: opened from the list (its 「그곳으로 가기」 shown, closing goes back to it)
  read(n, fromList = false) {
    if (!n) return;
    this._reading = n;
    this._fromList = fromList || !this.listEl.hidden;
    const c = this.readEl;
    const paper = c.querySelector('.memo-paper');
    paper.style.background = COLORS[n.color];
    paper.style.setProperty('--tilt', `${((n.id.charCodeAt(1) || 0) % 7 - 3) * 0.6}deg`);
    c.querySelector('.text').textContent = n.text;
    c.querySelector('.sign').textContent = n.name ? `— ${n.name}` : '';
    c.querySelector('.memo-meta').textContent = [n.place, ago(n.created_at)].filter(Boolean).join(' · ');
    c.querySelector('.go').hidden = !fromList;
    const del = c.querySelector('.del');
    del.textContent = '떼어 내기'; del.classList.remove('armed'); del.disabled = n.id.startsWith('tmp-');
    clearTimeout(this._arm);
    this.listEl.hidden = true;
    c.hidden = false;
    this.onOpen();
  }

  // 떼어 내기: pressed twice (the first press asks), then it blows away at once and the database is told
  async _remove() {
    const c = this.readEl, del = c.querySelector('.del'), n = this._reading;
    if (!n || n.id.startsWith('tmp-')) return;
    if (!del.classList.contains('armed')) {
      del.classList.add('armed');
      del.textContent = '한 번 더 누르면 떼어져요';
      clearTimeout(this._arm);
      this._arm = setTimeout(() => { del.classList.remove('armed'); del.textContent = '떼어 내기'; }, 3500);
      return;
    }
    clearTimeout(this._arm);
    this._fromList = false;
    this._close(c);
    const had = this.notes.get(n.id);
    if (had) this._blow(n.id);
    this.toast('쪽지를 떼었어요 · 바람에 날려 보냈어요');
    try {
      await this._send('DELETE', `/${n.id}`);
    } catch (e) {
      if (had && !this.notes.has(n.id)) this._put(n);
      this._changed();
      this.toast(`쪽지를 떼지 못했어요: ${e.message}`, 4500);
    }
  }

  openList() {
    this._fillList();
    this.listEl.hidden = false;
    this.onOpen();
    this.load();
  }
  _fillList() {
    const c = this.listEl, ul = c.querySelector('.memo-items'), list = this.list;
    c.querySelector('.count').textContent = this.loaded || list.length ? `${list.length}장 붙어 있어요` : this.error ? '' : '불러오는 중…';
    ul.innerHTML = '';
    if (!list.length) {
      const li = el('li', 'empty', this.error && !this.loaded ? '쪽지를 불러오지 못했어요. 잠시 뒤에 다시 열어 보세요.'
        : this.loaded ? '아직 붙은 쪽지가 없어요. 캠퍼스를 걷다가 「쪽지」 버튼으로 남겨 보세요.' : '쪽지를 불러오는 중이에요…');
      ul.appendChild(li);
      return;
    }
    for (const n of list) {
      const li = el('li');
      const b = el('button', 'item');
      b.type = 'button';
      b.title = '쪽지 읽기';
      const chip = el('i'); chip.style.background = COLORS[n.color];
      const body = el('span', 'body');
      body.appendChild(el('span', 'text', n.text.replace(/\s*\n\s*/g, ' ')));
      body.appendChild(el('small', 'meta', [n.name && `${n.name}`, n.place, ago(n.created_at)].filter(Boolean).join(' · ')));
      b.append(chip, body);
      b.addEventListener('click', () => this.read(n, true));
      const go = el('button', 'go', '가기');
      go.type = 'button';
      go.title = '쪽지가 붙은 곳으로 가기';
      go.addEventListener('click', () => { this.closeAll(); this.onGo(n); });
      li.append(b, go);
      ul.appendChild(li);
    }
  }

  // the big map's dots (ui.js)
  dots() { return this.list.map((n) => ({ x: n.x, y: n.y, color: COLORS[n.color] })); }
}
