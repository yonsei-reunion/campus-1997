// HUD, minimap, campus map with teleport, memory cards and the stamp collection.
import { pointInPoly } from './player.js';
import { $, safeGet, safeSet, versioned } from './util.js';

const FOOT = new Set(['footway', 'path', 'steps', 'pedestrian']);

// trace a campus-frame polyline through the map projection P
function trace(x, pts, P) {
  x.beginPath();
  pts.forEach(([a, b], i) => { const [u, v] = P(a, b); i ? x.lineTo(u, v) : x.moveTo(u, v); });
}

// round marker: filled, and outlined when a stroke colour is given
function dot(x, u, v, r, fill, stroke = null, lineWidth = 0) {
  x.fillStyle = fill;
  x.beginPath(); x.arc(u, v, r, 0, 7); x.fill();
  if (stroke) { x.strokeStyle = stroke; x.lineWidth = lineWidth; x.stroke(); }
}

export class UI {
  constructor(campus, opts) {
    this.c = campus;
    this.opts = opts;           // {onTeleport(x,y), onClose()}
    this.collected = new Set(JSON.parse(safeGet('y97-stamps') || '[]'));
    this.cards = campus.landmarks;
    this.current = null;
    this.spots = campus.landmarks.filter((l) => l.r);          // landmarks with a memory spot on the ground
    // building centres for the place names (named buildings only)
    this.named = campus.buildings.filter((b) => b.name).map((b) => {
      const n = b.footprint.length;
      const [cx, cy] = b.footprint.reduce((a, p) => [a[0] + p[0] / n, a[1] + p[1] / n], [0, 0]);
      return { name: b.name, cx, cy };
    });
    this.minimap = $('#minimap');
    this.minimapCtx = this.minimap.getContext('2d');
    this.mapCanvas = this._renderMap();
    this._bindMap();
    $('#memory .close').onclick = () => this.closeMemory();
    $('#mapview .close').onclick = () => this.toggleMap(false);
    this.updateStamps();
  }

  // ---------------------------------------------------------------- base map (1 px = 0.6 m)
  _renderMap() {
    // (the splat's rectangle, down to 신촌 로터리 where the town's own map reaches it: tools/sinchon_rotary.py)
    const S = this.c.tsplat ? { ...this.c.splat, y0: Math.min(this.c.splat.y0, -1060) } : this.c.splat;
    const k = 1 / 0.6;
    const W = Math.round((S.x1 - S.x0) * k), H = Math.round((S.y1 - S.y0) * k);
    const cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    const x = cv.getContext('2d');
    const P = (px, py) => [(px - S.x0) * k, (S.y1 - py) * k];
    this.toMap = P;
    this.mapScale = k;
    x.fillStyle = '#b5cf9a'; x.fillRect(0, 0, W, H);
    // the town south of the rails (정문 밖), its houses
    const T = this.c.town;
    if (T) {
      x.fillStyle = '#cfc9bd';
      x.fillRect(0, P(0, -470)[1], W, H);
      x.fillStyle = '#b9b2a6'; x.strokeStyle = '#968e82'; x.lineWidth = 1;
      for (const b of T.blocks) {
        if (b[6] <= 0) continue;
        const [cx, cy, L, Wd, a] = b, c = Math.cos(a), sn = Math.sin(a);
        trace(x, [[-L / 2, -Wd / 2], [L / 2, -Wd / 2], [L / 2, Wd / 2], [-L / 2, Wd / 2]].map(([u, v]) => [cx + u * c - v * sn, cy + u * sn + v * c]), P);
        x.closePath(); x.fill(); x.stroke();
      }
    }
    // paths & roads
    x.lineCap = 'round'; x.lineJoin = 'round';
    for (const p of this.c.paths) {
      x.strokeStyle = FOOT.has(p.kind) ? '#efe6d4' : '#8d9096';
      x.lineWidth = Math.max(1.2, p.w * k);
      trace(x, p.pts, P);
      x.stroke();
    }
    const R = this.c.baekyangro;
    const eCurb = R.median + R.lane + R.curb, eVerge = eCurb + (R.verge || 0);
    trace(x, R.pts, P);
    x.strokeStyle = '#8fb576'; x.lineWidth = 2 * (eVerge + R.walk + (R.strip || 0)) * k; x.stroke();   // ginkgo strip
    x.strokeStyle = '#e8dccb'; x.lineWidth = 2 * (eVerge + R.walk) * k; x.stroke();                     // sidewalks
    x.strokeStyle = '#7fa868'; x.lineWidth = 2 * eVerge * k; x.stroke();                                // boxwood verges
    x.strokeStyle = '#6f737b'; x.lineWidth = 2 * (R.median + R.lane) * k; x.stroke();                    // carriageway
    // buildings
    for (const b of this.c.buildings) {
      const lm = b.style.startsWith('lm:');
      x.fillStyle = lm ? '#f4a259' : b.style === 'city' ? '#b9b2a6' : '#e9e4da';
      x.strokeStyle = lm ? '#9c4f17' : '#857d70';
      x.lineWidth = 1;
      trace(x, b.footprint, P);
      x.closePath(); x.fill(); x.stroke();
    }
    // amphitheater
    const A = this.c.amphitheater;
    const [ax, ay] = P(A.cx, A.cy);
    x.fillStyle = '#c7a97c';
    x.beginPath(); x.ellipse(ax, ay, (A.arena_rx + A.rows * A.row_d) * k, (A.arena_ry + A.rows * A.row_d) * k, -A.rot, 0, Math.PI * 2); x.fill();
    x.fillStyle = '#d9c39b';
    x.beginPath(); x.ellipse(ax, ay, A.arena_rx * k, A.arena_ry * k, -A.rot, 0, Math.PI * 2); x.fill();
    // trees
    for (const t of this.c.trees) dot(x, ...P(t[1], t[2]), 2.2 * k * t[3], 'rgba(60,110,50,.45)');
    if (T?.island) dot(x, ...P(T.island.c[0], T.island.c[1]), T.island.r * k, '#7fa868');     // 신촌 로터리's island
    // labels (minimap only; the big map draws its own)
    x.font = `bold ${Math.round(13 * k / 1.6)}px "Noto Sans KR", sans-serif`;
    x.textAlign = 'center';
    for (const l of this.spots) {
      const [u, v] = P(l.pos[0], l.pos[1]);
      x.fillStyle = 'rgba(255,255,255,.85)';
      const w = x.measureText(l.name).width + 10;
      x.fillRect(u - w / 2, v - 26, w, 20);
      x.fillStyle = '#143c8c';
      x.fillText(l.name, u, v - 11);
      dot(x, u, v, 5, '#143c8c');
    }
    return cv;
  }

  drawMinimap(px, py, yaw) {
    const cv = this.minimap, x = this.minimapCtx, map = this.mapCanvas;
    const W = cv.width, H = cv.height;
    x.save();
    x.clearRect(0, 0, W, H);
    x.beginPath(); x.arc(W / 2, H / 2, W / 2, 0, 7); x.clip();
    const [u, v] = this.toMap(px, py);
    x.translate(W / 2, H / 2);
    x.rotate(yaw);                         // heading-up
    // only the part of the ~2000 px base map that falls inside the round window (any rotation)
    const R = W / 2 + 2;
    const sx = Math.max(0, Math.floor(u - R)), sy = Math.max(0, Math.floor(v - R));
    const sw = Math.min(map.width, Math.ceil(u + R)) - sx, sh = Math.min(map.height, Math.ceil(v + R)) - sy;
    if (sw > 0 && sh > 0) x.drawImage(map, sx, sy, sw, sh, sx - u, sy - v, sw, sh);
    // landmark markers
    for (const l of this.spots) {
      const [a, b] = this.toMap(l.pos[0], l.pos[1]);
      dot(x, a - u, b - v, 6, this.collected.has(l.id) ? '#f2c230' : '#ffffff', '#143c8c', 2);
    }
    x.restore();
    // player arrow (always up)
    x.fillStyle = '#e63946'; x.strokeStyle = '#fff'; x.lineWidth = 2;
    x.beginPath(); x.moveTo(W / 2, H / 2 - 10); x.lineTo(W / 2 + 7, H / 2 + 8); x.lineTo(W / 2, H / 2 + 4); x.lineTo(W / 2 - 7, H / 2 + 8); x.closePath();
    x.fill(); x.stroke();
    // north marker
    x.fillStyle = '#fff'; x.font = 'bold 13px sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
    x.fillText('N', W / 2 + Math.sin(yaw) * (W / 2 - 12), H / 2 - Math.cos(yaw) * (H / 2 - 12));
  }

  // ---------------------------------------------------------------- big map
  _bindMap() {
    const cv = $('#bigmap');
    cv.addEventListener('click', (e) => {
      const r = cv.getBoundingClientRect();
      const mx = (e.clientX - r.left) / r.width * cv.width, my = (e.clientY - r.top) / r.height * cv.height;
      const { ox, oy, s } = this._bigView;
      const u = (mx - ox) / s, v = (my - oy) / s;
      const S = this.c.splat, k = this.mapScale;
      let px = u / k + S.x0, py = S.y1 - v / k;
      // snap to a landmark if close
      for (const l of this.spots) if (Math.hypot(l.pos[0] - px, l.pos[1] - py) < 18) [px, py] = l.pos;
      for (const b of this.c.buildings) if (pointInPoly(px, py, b.footprint)) return;
      this.toggleMap(false);
      this.opts.onTeleport(px, py);
    });
  }
  toggleMap(show, px, py) {
    const el = $('#mapview');
    if (show === undefined) show = el.hidden;
    el.hidden = !show;
    if (show) this._drawBig(px, py);
    else this.opts.onClose();
    return show;
  }
  _drawBig(px, py) {
    const cv = $('#bigmap'), x = cv.getContext('2d');
    const W = cv.width;
    // view: the core campus
    const S = this.c.splat, k = this.mapScale;
    const [u0, v0] = this.toMap(-360, 560), [u1, v1] = this.toMap(420, -480);
    const s = Math.min(W / (u1 - u0), W / (v1 - v0));
    const ox = -u0 * s + (W - (u1 - u0) * s) / 2, oy = -v0 * s + (W - (v1 - v0) * s) / 2;
    this._bigView = { ox, oy, s };
    x.fillStyle = '#b5cf9a'; x.fillRect(0, 0, W, W);
    x.drawImage(this.mapCanvas, ox, oy, this.mapCanvas.width * s, this.mapCanvas.height * s);
    x.textAlign = 'center';
    // other buildings: small grey names under the memory spots
    x.font = 'bold 11px "Noto Sans KR", sans-serif';
    x.lineWidth = 3; x.strokeStyle = 'rgba(255,253,246,.9)'; x.fillStyle = '#4a5260';
    for (const m of this.c.markers || []) {
      const [a, b] = this.toMap(m.pos[0], m.pos[1]);
      const X = ox + a * s, Y = oy + b * s;
      if (X < 0 || Y < 0 || X > W || Y > W) continue;
      x.strokeText(m.name, X, Y + 4); x.fillText(m.name, X, Y + 4);
    }
    x.font = 'bold 15px "Noto Sans KR", sans-serif';
    for (const l of this.spots) {
      const [a, b] = this.toMap(l.pos[0], l.pos[1]);
      const X = ox + a * s, Y = oy + b * s;
      dot(x, X, Y, 9, this.collected.has(l.id) ? '#f2c230' : '#fff', '#143c8c', 3);
      const w = x.measureText(l.name).width + 12;
      x.fillStyle = 'rgba(255,253,246,.92)'; x.fillRect(X - w / 2, Y - 34, w, 22);
      x.fillStyle = '#143c8c'; x.fillText(l.name, X, Y - 18);
    }
    if (px !== undefined) {
      const [a, b] = this.toMap(px, py);
      dot(x, ox + a * s, oy + b * s, 8, '#e63946', '#fff', 3);
    }
  }

  // ---------------------------------------------------------------- place / prompts
  nearestLandmark(px, py) {
    let best = null, bd = 1e9;
    for (const l of this.spots) {
      const d = Math.hypot(l.pos[0] - px, l.pos[1] - py);
      if (d < l.r && d < bd) { bd = d; best = l; }
    }
    return best;
  }
  placeName(px, py, onRoad) {
    const l = this.nearestLandmark(px, py);
    if (l) return l.name;
    if (onRoad) return '백양로';
    let best = null, bd = 45;
    for (const b of this.named) {
      const d = Math.hypot(b.cx - px, b.cy - py);
      if (d < bd) { bd = d; best = b; }
    }
    return best ? `${best.name} 앞` : '신촌 캠퍼스';
  }
  setPlace(name) {
    const el = $('#place b');
    if (el.textContent !== name) el.textContent = name;
  }
  setPrompt(text) {
    const el = $('#prompt');
    if (!text) { el.hidden = true; return; }
    el.hidden = false;
    el.querySelector('span').textContent = text;
  }
  // On a phone the look up (player.js) drops the walker to the foot of the screen, where the prompt button sits. While
  // the button would cover the walker's body it slides off to the walker's side, or fades where there is no room beside
  // it (a phone held upright). box: the walker's body on screen (Player.screenBox)
  clearWalker(box) {
    const b = this.promptEl || (this.promptEl = $('#prompt'));
    let dx = 0, fade = false;
    if (!b.hidden) {
      const text = b.textContent;
      if (text !== this._cwText || innerWidth !== this._cwW || innerHeight !== this._cwH) {
        // where the button sits when it stays (centred by the CSS), and the HUD's side edges
        this._cwText = text; this._cwW = innerWidth; this._cwH = innerHeight;
        const w = b.offsetWidth;
        this._cwHome = [innerWidth / 2 - w / 2, b.offsetTop, innerWidth / 2 + w / 2, b.offsetTop + b.offsetHeight];
        this._cwEdge = [$('#place').getBoundingClientRect().left, $('#minimap').getBoundingClientRect().right];
      }
      const [l, t, r, bt] = this._cwHome, [e0, e1] = this._cwEdge, m = this._cwDx || this._cwFade ? 14 : 4, gap = 12;
      if (box[0] < r + m && box[2] > l - m && box[1] < bt + m && box[3] > t - m) {
        if (box[2] + gap + r - l <= e1) dx = box[2] + gap - l;            // to the walker's right (the stick is left)
        else if (box[0] - gap - (r - l) >= e0) dx = box[0] - gap - r;
        else fade = true;
      }
    }
    if (Math.abs(dx - (this._cwDx || 0)) > (dx && this._cwDx ? 8 : 0)) {
      this._cwDx = dx;
      b.style.setProperty('--dx', `${Math.round(dx)}px`);
    }
    if (fade !== !!this._cwFade) { this._cwFade = fade; b.classList.toggle('faded', fade); }
  }
  toast(text, ms = 2600) {
    const el = $('#toast');
    el.textContent = text; el.hidden = false;
    clearTimeout(this._tt);
    this._tt = setTimeout(() => (el.hidden = true), ms);
  }

  // ---------------------------------------------------------------- memory cards
  openMemory(l) {
    this.current = l;
    const root = $('#memory');
    const ph = root.querySelector('.photos');
    ph.innerHTML = '';
    for (const src of l.photo || []) {
      const f = document.createElement('figure');
      if (/_pano\./.test(src)) f.classList.add('wide');      // two-page spread joined into one panorama
      const img = document.createElement('img');
      img.src = versioned('assets/' + src);
      img.alt = l.title;
      f.appendChild(img);
      ph.appendChild(f);
    }
    root.querySelector('.year').textContent = l.year;
    root.querySelector('h2').textContent = l.title;
    root.querySelector('p').textContent = l.text;
    const credit = root.querySelector('.credit');
    credit.textContent = l.credit || '사진출처: 연세대학교 기록관 · 연세동문회보 · 연세춘추 · 동문 제공';
    credit.hidden = !(l.photo && l.photo.length);
    root.hidden = false;
    if (!this.collected.has(l.id)) {
      this.collected.add(l.id);
      safeSet('y97-stamps', JSON.stringify([...this.collected]));
      this.updateStamps();
      setTimeout(() => this.toast(`추억 스탬프 획득! · ${l.name}`), 300);
    }
  }
  closeMemory() {
    $('#memory').hidden = true;
    this.current = null;
    this.opts.onClose();
  }
  get memoryOpen() { return !$('#memory').hidden; }
  get mapOpen() { return !$('#mapview').hidden; }
  updateStamps() {
    const total = this.cards.length;
    $('#stamps b').textContent = `${this.collected.size} / ${total}`;
    if (this.collected.size === total && total) this.toast('1997년의 추억을 모두 모았습니다! 🎓', 5000);
  }
}
