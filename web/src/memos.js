// 캠퍼스 쪽지: anyone leaves a sticky note where they stand (on the wall in front of them, or on a little stake in the
// ground when no wall is near), anyone reads it, anyone takes it off. The notes live in a public DoltHub database
// (benelog/yonsei-1997, table notes): read straight from DoltHub (no token: a public read), written through a small
// Cloudflare Worker (notes-worker/), which holds the token, since DoltHub's CORS lets no browser send one.
// Notes come and go with the wind: one taken off here, or gone from the list when it is read again, blows away.
// A note: { id, text, name, color, x, y (campus), z (its top edge, 해발 = the game's height), yaw (the way it faces,
// campus: (sin, cos), 0 = north), kind ('wall' | 'stake'), place (the place name where it was put), created_at (UTC) }.
// Each card has an address of its own, to copy and send: ./?memos the list, ./?memo=<id> one note. A card opens as a
// history entry (src/nav.js): the browser's back closes it, and a page opened at one opens its card at once
// (openFromUrl) over the plain game.
import * as THREE from 'three';
import { $, safeGet, safeSet, MOBILE, copyButton } from './util.js';
import * as nav from './nav.js';
import './memos.css';

const READ = 'https://www.dolthub.com/api/v1alpha1/benelog/yonsei-1997/main';
export const WRITE = new URLSearchParams(location.search).get('notesapi') || 'https://y97-notes.habit-chain-worker.workers.dev';
const NAME_KEY = 'y97-memo-name';
const MAX_TEXT = 100, MAX_NAME = 12, SHOW = 300;
const SIZE = 0.4;                  // m: the paper's side (a real one is 7.6 cm: unseen past a few steps)
const STAKE = 1.3;                 // m: the paper's top edge over the ground on a stake
const REACH = 3;                   // m: how far ahead a wall takes the note
const NEAR = 3.2;                  // m: the prompt to read it (main.js onGo sets the walker down 2.7 m off)
const SEEN = 160, TEXTURED = 45;   // m: drawn within, its writing drawn within
const BOARD_SIZE = 0.15;           // m: a note pinned on a notice board (the paper's side there)
const BOARD_IN = 0.035;            // m: the board's frame-side margin kept clear of the notes
const PINS = [0xd23030, 0x2f62c8, 0xf0c428, 0x2f9e52];

// The notice boards a note may be pinned on: the board for notes by 챔프2 오락실's door (campus.json town.sites kind
// champ97, drawn by blender/town.py _champ97: the cork on the north face, d.board = from - to west of the north-east
// corner, bottom - top over the floor, the cork 0.07 m off the wall).  A board: its face's middle (x, y campus, z
// 해발), width, height, yaw (the way it faces), name.  A note is on a board when it lies on the cork (onBoard): the
// database keeps it as a wall's note (kind 'wall'), the game draws it small with a pin
export function siteBoards(sites = []) {
  const out = [];
  for (const d of sites) {
    if (d.kind !== 'champ97' || !d.board || !d.outline) continue;
    const x1 = Math.max(...d.outline.map((p) => p[0])), y1 = Math.max(...d.outline.map((p) => p[1]));
    const [b0, b1, z0, z1] = d.board;
    out.push({ x: x1 - (b0 + b1) / 2, y: y1 + 0.07, z: d.base + (z0 + z1) / 2, w: b1 - b0, h: z1 - z0, yaw: 0, name: `${d.name} 게시판` });
  }
  return out;
}
// a board's frame: f the way it faces, t along it (to the right of one looking at it), campus
const frameOf = (b) => ({ f: [Math.sin(b.yaw), Math.cos(b.yaw)], t: [-Math.cos(b.yaw), Math.sin(b.yaw)] });
const hash = (s) => { let h = 7; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h; };
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
const ID = /^[0-9a-z]{4,40}$/i;          // (notes-worker: 12 hex digits)
const COPY_FAIL = '복사하지 못했어요 · 주소창의 주소를 복사하세요';
const base = () => location.origin + location.pathname;
export const listUrl = () => `${base()}?memos`;
export const noteUrl = (id) => `${base()}?memo=${encodeURIComponent(id)}`;
const LIST = 'memos', NOTE = 'memo';      // (their entries in src/nav.js)
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
  // Two stages: the cards and the list come with the page (the title card's list works while the campus loads), the
  // notes in the scene once the walker is in (attach). toast(text, ms)
  constructor({ toast = () => {} } = {}) {
    this.toast = toast;
    this.notes = new Map();          // id → { n, pending } and, once attached, { root, hinge, paper, tex, ph }
    this.flying = [];                // blowing away: { o, v, spin, t }
    this.onOpen = this.onClose = () => {};
    this.font = '"Jua", "Noto Sans KR", sans-serif';
    this.fontReady = document.fonts?.load?.(`40px ${this.font}`).catch(() => {}) ?? Promise.resolve();
    this.loaded = false;
    this.listeners = new Set();
    this._t = 0; this._near = 0;
    this._buildCards();
  }

  // the scene's part: walls, the meshes a note sticks to (player.walls); placeAt(x, y): the place name; onGo(note):
  // walk to it; onOpen() / onClose(): a card of ours opened / closed (main.js stops / lets go of the walker); patch:
  // the scene's atmosphere for our materials; canPick(): a tap on a note may read it now
  attach({ scene, camera, player, canvas, walls, placeAt, onGo, onOpen, onClose, patch = (m) => m, canPick = () => true, toast, boards = [] }) {
    Object.assign(this, { scene, camera, player, walls, placeAt, onGo, onOpen, onClose, patch, canPick, boards });
    if (toast) this.toast = toast;
    this.group = new THREE.Group();
    this.group.name = 'memos';
    scene.add(this.group);
    this.geo = paperGeometry();
    this.stakeGeo = new THREE.CylinderGeometry(0.018, 0.022, STAKE + 0.08, 6).translate(0, -(STAKE + 0.08) / 2 + 0.06, -0.025);
    this.stakeMat = patch(new THREE.MeshStandardMaterial({ color: 0x8a6a46, roughness: 0.9 }));
    this.pinGeo = new THREE.SphereGeometry(0.009, 8, 6).scale(1, 1, 0.8).translate(0, -0.014, 0.012);
    this.pinMats = PINS.map((c) => patch(new THREE.MeshStandardMaterial({ color: c, roughness: 0.4 })));
    this.plain = {};                 // colour → the material of a far note (no writing)
    for (const [k, c] of Object.entries(COLORS)) this.plain[k] = patch(new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, side: THREE.DoubleSide }));
    this.ray = new THREE.Raycaster();
    this.ray.firstHitOnly = true;
    this._bindPick(canvas);
    for (const o of this.notes.values()) this._mesh(o);
    this._changed();                 // (the list's 「가기」 come on, and the card's)
    this._goState();
  }
  get attached() { return !!this.scene; }

  // ---------------------------------------------------------------- data
  async load() {
    if (this._loading) return this._loading;
    this._loading = (async () => {
      try {
        this._sync(await this._query(`ORDER BY created_at DESC LIMIT ${SHOW}`));
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
  async _query(tail) {
    const q = `SELECT id, text, name, color, x, y, z, yaw, kind, place, created_at FROM notes ${tail}`;
    const r = await fetch(`${READ}?q=${encodeURIComponent(q)}`, { cache: 'no-store' });
    const j = await r.json();
    if (j.query_execution_status !== 'Success') throw new Error(j.query_execution_message || 'DoltHub');
    return (j.rows || []).map(row).filter((n) => Number.isFinite(n.x + n.y + n.z + n.yaw));
  }
  // one note by its id (an address's, older than the list reaches): put up with the rest, or null when it is gone
  async _fetchOne(id) {
    if (this.notes.has(id)) return this.notes.get(id).n;
    if (!ID.test(id)) return null;
    try {
      const n = (await this._query(`WHERE id = '${id}'`))[0];
      if (!n) return null;
      if (!this.notes.has(n.id)) { this._put(n).extra = true; this._changed(); }
      return this.notes.get(n.id).n;
    } catch { return null; }
  }
  // what came back is what hangs now: new ones put up, the ones gone blow away (but not one of ours still going up,
  // nor one an address asked for past the list's end)
  _sync(list) {
    const keep = new Set(list.map((n) => n.id));
    for (const [id, o] of this.notes) if (!keep.has(id) && !o.pending && !o.extra) this._blow(id);
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
    const o = { n, pending };
    this.notes.set(n.id, o);
    if (this.attached) this._mesh(o);
    return o;
  }
  _mesh(o) {
    const n = o.n, root = new THREE.Group(), hinge = new THREE.Group();
    root.position.set(n.x, n.z, -n.y);
    root.rotation.y = Math.PI - n.yaw;                // (the paper's front, local +z, the way it faces)
    root.add(hinge);
    if (n.kind === 'stake') root.add(new THREE.Mesh(this.stakeGeo, this.stakeMat));
    // on a notice board: small, pinned at its top edge's middle, a little askew
    const board = n.kind === 'wall' && this.onBoard(n);
    let tilt = 0;
    if (board) {
      const k = hash(n.id || `${n.x},${n.z}`);
      hinge.scale.setScalar(BOARD_SIZE / SIZE);
      tilt = ((k % 17) / 16 - 0.5) * 0.3;
      root.add(new THREE.Mesh(this.pinGeo, this.pinMats[(k >> 5) % PINS.length]));
    }
    const paper = new THREE.Mesh(this.geo, this.plain[n.color]);
    paper.userData.memo = n.id;
    hinge.add(paper);
    root.userData.memo = n.id;
    this.group.add(root);
    Object.assign(o, { root, hinge, paper, tex: null, ph: Math.random() * 100, board: !!board, tilt });
    hinge.rotation.z = tilt;
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
    this._changed();
    if (!o.root) return;
    o.root.userData.memo = null;
    o.paper.userData.memo = null;
    const v = WIND.clone().multiplyScalar(2.2 + Math.random() * 1.5);
    v.y = 1.2 + Math.random() * 0.8;
    // (a stake stays where it was a moment, then goes with the paper)
    this.flying.push({ o, v, spin: new THREE.Vector3((Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6), t: 0 });
  }
  _drop(f) {
    this.group.remove(f.o.root);
    if (f.o.tex) { f.o.tex.map.dispose(); f.o.tex.dispose(); }
  }

  update(dt, t) {
    if (!this.attached) return;
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
      o.hinge.rotation.x = -(o.n.kind === 'stake' ? 0.06 + 0.22 * gust * flap : o.board ? 0.01 + 0.05 * gust * flap : 0.02 + 0.11 * gust * flap);
      o.hinge.rotation.z = o.n.kind === 'stake' ? 0.05 * Math.sin(t * 1.3 + o.ph) * gust : o.tilt;
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
    const pinned = this._boardSpot(p.pos.x, -p.pos.z, p.pos.y, f.x, -f.z);
    if (pinned) return pinned;
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

  // the board a note lies on (its paper on the cork), or null
  onBoard(n) {
    for (const b of this.boards || []) {
      const { f, t } = frameOf(b), dx = n.x - b.x, dy = n.y - b.y;
      if (Math.abs(n.yaw - b.yaw) > 0.2 || Math.abs(dx * f[0] + dy * f[1]) > 0.08) continue;
      if (Math.abs(dx * t[0] + dy * t[1]) > b.w / 2 + 0.03) continue;
      if (n.z > b.z + b.h / 2 + 0.05 || n.z < b.z - b.h / 2 + BOARD_SIZE - 0.05) continue;
      return b;
    }
    return null;
  }
  // a board in front of the walker (x, y campus, feet h, looking along (fx, fy)): the note goes on it, at the free place
  // nearest where the walker looks (one paper's width from the others; all taken: the nearest, over another), or null
  _boardSpot(x, y, h, fx, fy) {
    for (const b of this.boards || []) {
      const { f, t } = frameOf(b), d = (x - b.x) * f[0] + (y - b.y) * f[1], c = -(fx * f[0] + fy * f[1]);
      if (d < 0.2 || d > REACH + 0.5 || c < 0.5) continue;              // (in front of it, looking at it within 60°)
      const s = d / c, a = (x + fx * s - b.x) * t[0] + (y + fy * s - b.y) * t[1];
      if (Math.abs(a) > b.w / 2 + 0.8) continue;
      // the places: a grid of tops over the cork, the walker's eye line first
      const S = BOARD_SIZE, aw = b.w / 2 - BOARD_IN - S / 2, top = b.z + b.h / 2 - BOARD_IN, low = b.z - b.h / 2 + BOARD_IN + S;
      const aim = [Math.max(-aw, Math.min(aw, a)), Math.max(low, Math.min(top, h + 1.5 + S / 2))];
      const taken = [...this.notes.values()].filter((o) => o.n.id && o.board && this.onBoard(o.n) === b)
        .map((o) => [(o.n.x - b.x) * t[0] + (o.n.y - b.y) * t[1], o.n.z]);
      const nx = Math.max(1, Math.floor((2 * aw) / (S * 1.05)) + 1), nz = Math.max(1, Math.floor((top - low) / (S * 1.05)) + 1);
      let best = null, bd = Infinity, any = null, ad = Infinity;
      for (let i = 0; i < nx; i++) {
        for (let j = 0; j < nz; j++) {
          const q = [nx > 1 ? -aw + (2 * aw * i) / (nx - 1) : 0, nz > 1 ? low + ((top - low) * j) / (nz - 1) : top];
          const dd = Math.hypot(q[0] - aim[0], q[1] - aim[1]);
          if (dd < ad) { ad = dd; any = q; }
          if (dd < bd && taken.every((r) => Math.hypot(r[0] - q[0], r[1] - q[1]) > S * 0.9)) { bd = dd; best = q; }
        }
      }
      const [u, z] = best || any, j = (Math.random() - 0.5) * 0.02;
      return { x: b.x + t[0] * (u + j) + f[0] * 0.012, y: b.y + t[1] * (u + j) + f[1] * 0.012, z: z + j, yaw: b.yaw, kind: 'wall', board: b.name };
    }
    return null;
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
  // closed by its button, Esc or a click beside it: the write card at once, the list and a note through their history
  // entries (_drop when it is taken away)
  _close(root) {
    if (root.hidden) return;
    if (root === this.writeEl) { root.hidden = true; this._preview(null); if (!this.open) this.onClose(); return; }
    if (!nav.close([root === this.readEl ? NOTE : LIST])) this._drop(root);
  }
  // a card's entry taken away (its button, the browser's back): a note read from the list goes back to the list
  _drop(root) {
    if (root.hidden) return;
    root.hidden = true;
    if (root === this.readEl && this._fromList && nav.has(LIST)) { this._fromList = false; this.listEl.hidden = false; this._fillList(); return; }
    if (!this.open) this.onClose();
  }
  closeAll() {
    for (const r of [this.writeEl, this.readEl, this.listEl]) r.hidden = true;
    this._preview(null);
    this._fromList = false;
    nav.close([LIST, NOTE], false);
  }

  // ---------------------------------------------------------------- addresses
  // a page opened at a card's address: that card, over the title card (the note's: the list under it, and a word
  // when it has blown away meanwhile); back goes to the title card
  async openFromUrl() {
    const q = new URLSearchParams(location.search), id = q.get('memo');
    if (id === null && !q.has('memos')) return;
    nav.base();
    this.openList();
    if (id === null) return;
    await this.load();
    const n = await this._fetchOne(id);
    if (this.listEl.hidden) return;              // (closed meanwhile)
    if (n) this.read(n, true);
    else this._say('찾는 쪽지는 바람에 날아갔어요 · 다른 쪽지를 읽어 보세요');
  }
  _say(text) {
    const p = this.listEl.querySelector('.memo-notice');
    p.textContent = text;
    p.hidden = !text;
  }

  _buildCards() {
    this._buildWrite();
    this._buildRead();
    this._buildList();
    // Esc: our card first (before main.js: the capture phase)
    addEventListener('keydown', (e) => {
      // ← →: the note before / after at the same spot (while one is being read)
      if (!this.readEl.hidden && (e.code === 'ArrowLeft' || e.code === 'ArrowRight')) {
        e.stopImmediatePropagation();
        e.preventDefault();
        this.step(e.code === 'ArrowLeft' ? -1 : 1);
        return;
      }
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
      <div class="memo-step" hidden><button type="button" class="prev" aria-label="이전 쪽지">‹ 이전</button><span class="pos"></span><button type="button" class="next" aria-label="다음 쪽지">다음 ›</button></div>
      <p class="memo-meta"></p>
      <p class="memo-share"><button type="button" class="memo-copy" title="이 쪽지가 바로 열리는 주소를 복사해요">쪽지 주소 복사</button></p>
      <p class="memo-wind small">🍃 바람에 날려 언제든 없어질 수 있는 쪽지예요</p>
      <div class="memo-row"><button type="button" class="go">그곳으로 가기</button><button type="button" class="ghost del">떼어 내기</button><button type="button" class="close">닫기</button></div>`;
    c.querySelector('.close').addEventListener('click', () => this._close(root));
    c.querySelector('.go').addEventListener('click', () => { const n = this._reading; if (!n) return; this.closeAll(); this.onGo(n); });
    c.querySelector('.del').addEventListener('click', () => this._remove());
    copyButton(c.querySelector('.memo-copy'), () => noteUrl(this._reading?.id ?? ''), COPY_FAIL);
    c.querySelector('.prev').addEventListener('click', () => this.step(-1));
    c.querySelector('.next').addEventListener('click', () => this.step(1));
    // a sideways swipe on the paper: the next note (to the left) or the one before
    const paper = c.querySelector('.memo-paper');
    let tx = null, ty = 0;
    paper.addEventListener('touchstart', (e) => { const t = e.touches[0]; tx = e.touches.length === 1 ? t.clientX : null; ty = t.clientY; }, { passive: true });
    paper.addEventListener('touchend', (e) => {
      const t = e.changedTouches[0];
      if (tx === null || !t) return;
      const dx = t.clientX - tx, dy = t.clientY - ty;
      tx = null;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) this.step(dx < 0 ? 1 : -1);
    });
  }

  // 쪽지 목록
  _buildList() {
    const [root, c] = this._modal('memo-list', 'memo-listcard');
    this.listEl = root;
    c.innerHTML = `<h2>캠퍼스 쪽지 <small class="count"></small></h2>
      <p class="memo-wind">🍃 쪽지는 바람에 날려 언제든 없어질 수 있어요. 누르면 쪽지를 읽고, 「가기」를 누르면 쪽지가 붙은 곳으로 가요.</p>
      <p class="memo-share"><button type="button" class="memo-copy" title="이 목록이 바로 열리는 주소를 복사해요">목록 주소 복사</button></p>
      <p class="memo-notice" hidden></p>
      <ul class="memo-items"></ul>
      <button type="button" class="close">닫기</button>`;
    c.querySelector('.close').addEventListener('click', () => this._close(root));
    copyButton(c.querySelector('.memo-copy'), listUrl, COPY_FAIL);
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
    c.querySelector('.where').textContent = `${s.board ? `${s.board}에 꽂아요` : s.kind === 'wall' ? '앞의 벽에 붙여요' : '작은 말뚝에 꽂아요'} · ${this._spot.place}`;
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

  // read: the note on a big paper. fromList: opened from the list (its 「그곳으로 가기」 shown, closing goes back to it).
  // Read in the scene, the other notes readable from where the walker stands come with it: 「이전」 · 「다음」 (← →, a
  // swipe) go through them, left to right as the walker sees them
  read(n, fromList = false) {
    if (!n) return;
    this._fromList = fromList || !this.listEl.hidden;
    this._group = this._fromList ? [n] : this._around(n);
    this._show(n);
  }
  // the notes read from one spot: the ones within reach of the walker (nearest's reach), or, for a note tapped from
  // further off, the ones within that reach of it; left to right from the walker's view, the newest first on a tie
  _around(n) {
    if (!this.attached) return [n];
    const p = this.player, x = p.pos.x, y = -p.pos.z, h = p.pos.y;
    const all = [...this.notes.values()].map((o) => o.n);
    let g = all.filter((m) => Math.hypot(m.x - x, m.y - y) < NEAR && Math.abs(m.z - 1.5 - h) < 2.5);
    if (!g.includes(n)) g = all.filter((m) => Math.hypot(m.x - n.x, m.y - n.y) < NEAR && Math.abs(m.z - n.z) < 1.5);
    if (!g.includes(n)) g.push(n);
    const f = this.camera.getWorldDirection(new THREE.Vector3()), fx = f.x, fy = -f.z;
    const side = (m) => { const dx = m.x - x, dy = m.y - y; return Math.atan2(dx * fy - dy * fx, dx * fx + dy * fy); };
    return g.map((m) => [side(m), m]).sort((a, b) => a[0] - b[0] || (a[1].created_at < b[1].created_at ? -1 : 1)).map((e) => e[1]);
  }
  // the note before (-1) or after (1) among the ones read from this spot (those blown away meanwhile skipped)
  step(d) {
    if (this.readEl.hidden || !this._reading) return;
    const g = (this._group || []).filter((m) => m === this._reading || this.notes.get(m.id)?.n === m);
    this._group = g;
    const n = g[g.indexOf(this._reading) + d];
    if (n) this._show(n);
  }
  _show(n) {
    this._reading = n;
    const c = this.readEl;
    const paper = c.querySelector('.memo-paper');
    paper.style.background = COLORS[n.color];
    paper.style.setProperty('--tilt', `${((n.id.charCodeAt(1) || 0) % 7 - 3) * 0.6}deg`);
    c.querySelector('.text').textContent = n.text;
    c.querySelector('.sign').textContent = n.name ? `— ${n.name}` : '';
    c.querySelector('.memo-meta').textContent = [n.place, ago(n.created_at)].filter(Boolean).join(' · ');
    const g = this._group || [n], i = g.indexOf(n), step = c.querySelector('.memo-step');
    step.hidden = g.length < 2;
    step.querySelector('.pos').textContent = `${i + 1} / ${g.length}`;
    step.querySelector('.prev').disabled = i <= 0;
    step.querySelector('.next').disabled = i >= g.length - 1;
    c.querySelector('.go').hidden = !this._fromList;
    this._goState();
    c.querySelector('.memo-copy').disabled = n.id.startsWith('tmp-');
    const del = c.querySelector('.del');
    del.textContent = '떼어 내기'; del.classList.remove('armed'); del.disabled = n.id.startsWith('tmp-');
    clearTimeout(this._arm);
    this.listEl.hidden = true;
    c.hidden = false;
    if (!n.id.startsWith('tmp-')) nav.open(NOTE, nav.urlWith('memo', n.id), () => this._drop(c));
    this.onOpen();
  }
  // 「그곳으로 가기」: once the campus is in (the title card's list opens before)
  _goState() {
    const go = this.readEl.querySelector('.go');
    go.disabled = !this.attached;
    go.textContent = this.attached ? '그곳으로 가기' : '캠퍼스를 불러오는 중…';
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
    if (!nav.close([LIST, NOTE])) this._drop(c);
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
    this._say('');
    this._fillList();
    this.listEl.hidden = false;
    nav.open(LIST, nav.urlWith('memos'), () => this._drop(this.listEl));
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
      go.title = this.attached ? '쪽지가 붙은 곳으로 가기' : '캠퍼스를 다 불러오면 갈 수 있어요';
      go.disabled = !this.attached;
      go.addEventListener('click', () => { this.closeAll(); this.onGo(n); });
      li.append(b, go);
      ul.appendChild(li);
    }
  }

  // the big map's dots (ui.js)
  dots() { return this.list.map((n) => ({ x: n.x, y: n.y, color: COLORS[n.color] })); }
}
