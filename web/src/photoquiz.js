// 이곳은 어디? (the title card's mini game, the settings card's 「이곳은 어디?」, ./?game=photo): a photo of the campus
// (README 「사진과 비교」's photos whose game camera stands on the ground: data/photoquiz.json, tools/photoquiz.py) is
// shown in a corner, and the walker, set down somewhere 60 - 170 m away, walks to where it was taken and looks the
// same way. E / Space (or the 「여기서 찍기」 button) takes the answer: the score is by the level distance to the
// camera and the difference in the way the view looks (the camera's, so the first person view, which the game
// turns on, is the photo's). Five photos a round; every round is kept in this browser.
// Loaded only when the game starts (main.js).
import * as THREE from 'three';
import { HERO } from './characters.js';
import { safeGet, safeSet, wrapAngle, versioned, copyButton } from './util.js';
import './photoquiz.css';
import { Run, mountRankBox } from './rank.js';
import { PHOTO, photoScore, pickPhotos } from './rankrules.js';

// (rankrules.js, which the ranking's server judges by) ROUND photos a round, LIMIT s for one (then the answer is taken
// where the walker stands), starts NEAR m from the answer, no two answers closer than SEP m; the score: POS for the
// place (full within D_FULL m, none past D_ZERO), DIR for the way (full within A_FULL°, none past A_ZERO; only
// within D_ZERO m)
const { ROUND, LIMIT, NEAR, POS, DIR, D_ZERO } = PHOTO;
const HINT_AT = 40;                // s: the nearest named place shows from then on
const KEY = 'y97-photo-records', MAX = 50;
const DEG = Math.PI / 180;

export const photoUrl = () => `${location.origin}${location.pathname}?game=photo`;
export const scoreOf = photoScore;

// ---------------------------------------------------------------- records (this browser only)
export function records() {
  let list;
  try { list = JSON.parse(safeGet(KEY) || '[]'); } catch { list = []; }
  return (Array.isArray(list) ? list : []).filter((r) => r && Number.isFinite(r.score)).sort((a, b) => b.score - a.score || a.at - b.at);
}
function addRecord(rec) {
  const list = records();
  list.push(rec);
  list.sort((a, b) => b.score - a.score || a.at - b.at);
  safeSet(KEY, JSON.stringify(list.slice(0, MAX)));
  return { rank: list.indexOf(rec) + 1, total: list.length };
}
const day = (ms) => { const d = new Date(ms); return `${d.getMonth() + 1}/${d.getDate()}`; };
const mmss = (s) => { s = Math.max(0, Math.ceil(s)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };

// the answer's mark: a column of light and an arrow on the ground the way the photo looks
function beacon() {
  const g = new THREE.Group();
  g.name = 'photoquiz_answer';
  const col = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 40, 24, 1, true),
    new THREE.MeshBasicMaterial({ color: 0xffd23a, transparent: true, opacity: 0.35, depthWrite: false, side: THREE.DoubleSide, fog: false, toneMapped: false }));
  col.position.y = 20;
  const s = new THREE.Shape();
  s.moveTo(0, 3.2); s.lineTo(1.3, 0.6); s.lineTo(0.45, 0.6); s.lineTo(0.45, -0.8); s.lineTo(-0.45, -0.8); s.lineTo(-0.45, 0.6); s.lineTo(-1.3, 0.6); s.closePath();
  const arrow = new THREE.Mesh(new THREE.ShapeGeometry(s),
    new THREE.MeshBasicMaterial({ color: 0xffd23a, transparent: true, opacity: 0.9, depthWrite: false, side: THREE.DoubleSide, fog: false, toneMapped: false }));
  arrow.rotation.x = -Math.PI / 2;           // (shape +y → north, -z)
  const turn = new THREE.Group();
  turn.position.y = 0.08;
  turn.add(arrow);
  g.add(col, turn);
  col.renderOrder = arrow.renderOrder = 5;
  g.userData.turn = turn;
  return g;
}

export class PhotoQuiz {
  // places: main.js's start places ({ name, x, y, yaw }), where a photo starts and its hint;
  // go(x, y, yaw, still): set the walker down there (the halls round it in first, then only if still() holds);
  // groundAt(x, y): the walk's height;
  // onBegin(msg): main.js takes the walk on; onQuit: back to the walk
  constructor({ scene, camera, player, sound, places, groundAt, go, onBegin, onQuit, mobile }) {
    Object.assign(this, { scene, camera, player, sound, places, groundAt, go, onBegin, onQuit, mobile });
    this.state = 'off';                // off | load | play | reveal | done
    this.paused = false;
    this._dir = new THREE.Vector3();
    this.mark = beacon();
    addEventListener('keydown', (e) => this.onKey(e), true);
  }

  get on() { return this.state !== 'off'; }
  // a card of its own (or the big photo) is up: main.js leaves the keys to it
  get busy() { return this.state === 'reveal' || this.state === 'done' || this.zoomed; }
  get zoomed() { return !!this.zoomEl && !this.zoomEl.hidden; }

  onKey(e) {
    if (!this.on || /INPUT|TEXTAREA|SELECT/.test(e.target?.tagName)) return;
    const stop = () => { e.stopImmediatePropagation(); e.preventDefault(); };
    if (this.zoomed) { if (e.code === 'Escape' || e.code === 'Enter' || e.code === 'Space') { stop(); this.zoom(false); } return; }
    if (this.state === 'reveal' && !this.peeking) {
      if (e.code === 'Escape') { stop(); this.next(); }
      return;
    }
    if (this.state === 'reveal' && this.peeking && (e.code === 'KeyE' || e.code === 'Space' || e.code === 'Enter') && !e.repeat) { stop(); this.next(); return; }
    if (this.state === 'done') { if (e.code === 'Escape') { stop(); this.stop(); } return; }
    if (this.state === 'play' && !this.paused && (e.code === 'KeyE' || e.code === 'Space') && !e.repeat) { stop(); this.submit(); }
  }

  async load() {
    if (this.items) return this.items;
    const r = await fetch(versioned('data/photoquiz.json'));
    this.items = (await r.json()).items;
    return this.items;
  }

  // ---------------------------------------------------------------- a round
  async start() {
    if (this.state === 'load' || this.opening) return;
    this.run?.fail('다시 시작');
    let items, run;
    this.opening = true;
    try { [items, run] = await Promise.all([this.load(), Run.open('photo')]); } finally { this.opening = false; }
    this.run = run;
    this.results(false);
    // five answers, no two close together, drawn by the ranking's seed (the server deals the same five)
    this.round = pickPhotos(items, run.rnd);
    this.answers = [];
    this.score = 0;
    this.i = -1;
    if (this.fpv0 === undefined) this.fpv0 = this.player.fpv;
    this.player.setFpv(true);
    this.onBegin?.(`이곳은 어디? 사진을 찍은 자리를 찾아가 같은 쪽을 보고 ${this.mobile ? '「여기서 찍기」를 누르세요' : 'E나 스페이스를 누르세요'} · ${ROUND}문제`);
    this.hudEl().hidden = false;
    this.nextQuestion();
  }

  async nextQuestion() {
    this.i++;
    const q = this.q = this.round[this.i];
    this.peeking = false;
    this.reveal(false);
    if (this.mark.parent) this.scene.remove(this.mark);
    this.state = 'load';
    this.time = LIMIT;
    this.hint = null;
    this.showPhoto(q);
    // where to start: a named place 60 - 170 m off (else the nearest past 40 m)
    const far = (p) => Math.hypot(p.x - q.x, p.y - q.y);
    let from = this.places.filter((p) => far(p) >= NEAR[0] && far(p) <= NEAR[1]);
    if (!from.length) from = this.places.filter((p) => far(p) >= 40).sort((a, b) => far(a) - far(b)).slice(0, 3);
    const s = from[Math.floor(Math.random() * from.length)] || { x: q.x + 80, y: q.y, yaw: 0 };
    const pl = this.player;
    pl.enabled = false;
    await this.go(s.x, s.y, s.yaw, () => this.state === 'load' && this.q === q);
    if (this.state !== 'load' || this.q !== q) return;          // (stopped meanwhile)
    pl.autoRun = true;
    pl.enabled = true;
    this.state = 'play';
    this.run?.add('q', pl.x, pl.y, this.i);
    const near = this.places.filter((p) => far(p) < 60).sort((a, b) => far(a) - far(b))[0];
    this.hintText = near ? `힌트: ${near.name} 근처` : '힌트: 사진 속 건물을 찾아보세요';
    this.sound?.cue('beep');
  }

  submit() {
    if (this.state !== 'play') return;
    const q = this.q, pl = this.player;
    const d = Math.hypot(pl.x - q.x, pl.y - q.y);
    const v = this.camera.getWorldDirection(this._dir);
    const look = Math.atan2(v.x, -v.z);
    const a = Math.abs(wrapAngle(look - q.bearing * DEG)) / DEG;
    const sc = scoreOf(d, a);
    this.run?.add('a', pl.x, pl.y, this.i, Math.round(look / DEG * 100) / 100);
    this.score += sc.total;
    this.answers.push({ id: q.id, d: Math.round(d * 10) / 10, a: Math.round(a), s: sc.total, time: Math.round(LIMIT - this.time) });
    this.state = 'reveal';
    pl.enabled = false;
    pl.speed = 0;
    pl.autoRun = false;
    this.sound?.cue(sc.total >= 700 ? 'go' : 'buzzer');
    // the mark at the answer, the arrow the way the photo looks
    this.mark.position.set(q.x, this.groundAt(q.x, q.y), -q.y);
    this.mark.userData.turn.rotation.y = -q.bearing * DEG;
    this.scene.add(this.mark);
    this.reveal(true, { q, d, a, sc });
  }

  // stand at the answer looking the photo's way (the reveal card folds to a bar meanwhile)
  async peek() {
    const q = this.q;
    this.peeking = true;
    this.revEl.classList.add('peek');
    if (this.mark.parent) this.scene.remove(this.mark);
    await this.go(q.x, q.y, -q.bearing * DEG, () => this.peeking && this.q === q);
    if (!this.peeking) return;
    this.player.setFpv(true);
    this.revEl.querySelector('.bar .next').focus({ preventScroll: true });
  }

  next() {
    if (this.state !== 'reveal') return;
    if (this.i + 1 < this.round.length) { this.nextQuestion(); return; }
    this.finish();
  }

  finish() {
    this.state = 'done';
    this.run?.end();
    this.reveal(false);
    this.showPhoto(null);
    if (this.mark.parent) this.scene.remove(this.mark);
    this.hud.el.hidden = this.hud.go.hidden = true;
    const pl = this.player;
    const rec = { id: Date.now(), at: Date.now(), score: this.score, items: this.answers, hero: pl.actor.id };
    const prev = records()[0] || null;
    const { rank, total } = addRecord(rec);
    this.results(true, { rec, rank, total, prev });
  }

  // back to the walk (onQuit: main.js resumes it)
  stop() {
    if (!this.on) return;
    this.state = 'off';
    this.run?.fail('그만둠');
    this.peeking = false;
    const pl = this.player;
    pl.autoRun = false;
    pl.enabled = true;
    if (this.fpv0 !== undefined) { pl.setFpv(this.fpv0); this.fpv0 = undefined; }
    if (this.mark.parent) this.scene.remove(this.mark);
    if (this.hud) this.hud.el.hidden = this.hud.go.hidden = true;
    this.showPhoto(null);
    this.zoom(false);
    this.reveal(false);
    this.results(false);
    this.onQuit?.();
  }

  // t: the loop's clock; paused: the settings card, a memory card or the map is open (the clock stops)
  update(dt, t, paused) {
    if (!this.on) return;
    this.paused = paused;
    this.run?.frame(dt, paused || this.zoomed);      // (the big photo stops the photo's clock too)
    if (this.mark.parent) this.mark.children[0].material.opacity = 0.28 + 0.12 * Math.sin(t * 3);
    if (this.state === 'play' && !paused && !this.zoomed) {
      this.time -= dt;
      this.run?.sample(this.player.x, this.player.y);
      if (LIMIT - this.time >= HINT_AT) this.hint = this.hintText;
      if (this.time <= 0) { this.time = 0; this.submit(); }
    }
    this.drawHud();
  }

  // ---------------------------------------------------------------- the photo in the corner (tap: big)
  showPhoto(q) {
    if (!this.photoEl) {
      const p = this.photoEl = el('figure');
      p.id = 'pqphoto';
      p.innerHTML = '<button type="button" title="크게 보기"><img alt=""></button><figcaption></figcaption>';
      p.querySelector('button').addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); this.zoom(true); });
      document.body.appendChild(p);
      const z = this.zoomEl = el('div');
      z.id = 'pqzoom';
      z.hidden = true;
      z.innerHTML = '<figure><img alt=""><figcaption></figcaption></figure><p>눌러서 닫기</p>';
      z.addEventListener('click', () => this.zoom(false));
      document.body.appendChild(z);
    }
    this.photoEl.hidden = !q;
    if (!q) return;
    for (const img of [this.photoEl.querySelector('img'), this.zoomEl.querySelector('img')]) {
      img.src = versioned(q.photo);
      img.width = q.w; img.height = q.h;
      img.alt = `${this.i + 1}번 사진`;
    }
    this.photoEl.querySelector('figcaption').textContent = `${q.when} · ${q.credit}`;
    this.zoomEl.querySelector('figcaption').textContent = `${q.when} · 사진 ${q.credit}`;
    this.photoEl.classList.toggle('tall', q.h > q.w);
    this.photoEl.classList.toggle('wide', q.w > 3 * q.h);       // (the strips cut from group photos)
    this.zoomEl.querySelector('img').classList.toggle('small', Math.max(q.w, q.h) < 500);
  }
  zoom(on) { if (this.zoomEl) this.zoomEl.hidden = !on; }

  // ---------------------------------------------------------------- HUD
  hudEl() {
    if (this.hud) return this.hud.el;
    const h = el('div');
    h.id = 'pqhud';
    h.innerHTML = '<div class="n"><small>문제</small><b></b></div><div class="t"><small>남은 시간</small><b></b></div>'
      + '<div class="s"><small>점수</small><b></b></div><p class="hint"></p>';
    document.body.appendChild(h);
    const go = el('button', '', '');
    go.id = 'pqgo';
    go.type = 'button';
    go.innerHTML = this.mobile ? '여기서 찍기' : '<kbd>E</kbd>여기서 찍기';
    go.addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); this.submit(); });
    document.body.appendChild(go);          // (not in the HUD: its transform would hold the fixed button)
    this.hud = { el: h, n: h.querySelector('.n b'), t: h.querySelector('.t b'), s: h.querySelector('.s b'), hint: h.querySelector('.hint'), go };
    return h;
  }

  drawHud() {
    const h = this.hud;
    if (!h || !this.round) return;
    const set = (e, v) => { if (e.textContent !== v) e.textContent = v; };
    set(h.n, `${Math.min(this.i + 1, this.round.length)} / ${this.round.length}`);
    set(h.t, mmss(this.time));
    h.t.parentElement.classList.toggle('low', this.state === 'play' && this.time < 15);
    set(h.s, this.score.toLocaleString('ko-KR'));
    h.go.hidden = this.state !== 'play';
    // warm / hot once within 40 m (and the hint after a while)
    let msg = this.state === 'load' ? '사진을 찍은 곳 근처로 가는 중…' : '';
    if (this.state === 'play') {
      const d = Math.hypot(this.player.x - this.q.x, this.player.y - this.q.y);
      const warm = d < 12 ? '뜨거워요! 사진과 같은 쪽을 보세요' : d < 40 ? '따뜻해요' : '';
      msg = [warm, this.hint].filter(Boolean).join(' · ');
      h.hint.classList.toggle('hot', d < 12);
    }
    set(h.hint, msg);
    h.hint.hidden = !msg;
  }

  // ---------------------------------------------------------------- one answer's card
  reveal(show, info = {}) {
    let r = this.revEl;
    if (!show) { if (r) r.hidden = true; return; }
    if (!r) {
      r = this.revEl = el('div');
      r.id = 'pqreveal';
      r.innerHTML = '<div class="card"><p class="no"></p><h2></h2><div class="pair"><img alt=""><dl><div><dt>거리</dt><dd class="d"></dd></div>'
        + '<div><dt>방향 차이</dt><dd class="a"></dd></div></dl></div><p class="pts"></p>'
        + '<div class="btns"><button type="button" class="see">정답 자리에서 보기</button><button type="button" class="next"></button></div></div>'
        + '<div class="bar"><span></span><button type="button" class="next"></button></div>';
      document.body.appendChild(r);
      r.querySelector('.see').addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); this.peek(); });
      for (const b of r.querySelectorAll('.next')) b.addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); this.next(); });
    }
    const { q, d, a, sc } = info;
    r.classList.remove('peek');
    r.querySelector('.no').textContent = `${this.i + 1}번 사진 · ${q.when}`;
    r.querySelector('h2').textContent = q.title;
    const img = r.querySelector('img');
    img.src = versioned(q.photo); img.width = q.w; img.height = q.h;
    r.querySelector('.d').textContent = d < 1 ? '1 m 안' : `${Math.round(d)} m`;
    r.querySelector('.a').textContent = d < D_ZERO ? `${Math.round(a)}°` : '—';
    const pts = r.querySelector('.pts');
    pts.textContent = `+${sc.total}점` + (sc.total ? ` (자리 ${sc.pos} · 방향 ${sc.dir})` : (this.time <= 0 ? ' · 시간이 다 됐어요' : ''));
    pts.classList.toggle('good', sc.total >= 700);
    const last = this.i + 1 >= this.round.length;
    for (const b of r.querySelectorAll('.next')) b.textContent = last ? '결과 보기' : '다음 사진';
    r.querySelector('.bar span').textContent = `정답 자리 · ${q.title}`;
    r.hidden = false;
    r.querySelector('.card .next').focus({ preventScroll: true });
  }

  // ---------------------------------------------------------------- the round's card
  results(show, info = {}) {
    let r = this.resEl;
    if (!show) { if (r) r.hidden = true; return; }
    if (!r) {
      r = this.resEl = el('div');
      r.id = 'pqresult';
      r.innerHTML = '<div><h2>이곳은 어디?</h2><p class="big"></p><p class="best"></p><ol class="each"></ol><h3>이 브라우저의 기록</h3><ol class="ranks"></ol>'
        + '<p class="url">게임 주소 <code></code> <button type="button" class="copy">주소 복사</button></p>'
        + '<div class="btns"><button type="button" class="again">다시 하기</button><button type="button" class="quit">그만하고 산책하기</button><button type="button" class="quit totitle" data-to-title>처음 화면으로</button></div></div>';
      document.body.appendChild(r);
      r.querySelector('.again').addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); this.start(); });
      r.querySelector('.quit').addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); this.stop(); });
      r.querySelector('.url code').textContent = photoUrl();
      copyButton(r.querySelector('.copy'), photoUrl);
    }
    const { rec, rank, total, prev } = info;
    r.querySelector('.big').textContent = `${rec.score.toLocaleString('ko-KR')}점`;
    const be = r.querySelector('.best'), top = rank === 1;
    be.textContent = top
      ? (prev ? `내 새 기록! ${(rec.score - prev.score).toLocaleString('ko-KR')}점 올림` : `첫 기록! (${ROUND * (POS + DIR)}점 만점)`)
      : `내 기록 ${rank}번째 (${total}번 가운데) · 내 최고 ${prev.score.toLocaleString('ko-KR')}점`;
    be.classList.toggle('new', top);
    const byId = new Map(this.items.map((q) => [q.id, q]));
    r.querySelector('.each').replaceChildren(...rec.items.map((x) => {
      const li = el('li');
      li.append(el('span', 'w', byId.get(x.id)?.title ?? x.id), el('span', 'm', `${Math.round(x.d)} m · ${x.d < D_ZERO ? `${x.a}°` : '—'}`), el('span', 'p', `${x.s}`));
      return li;
    }));
    r.querySelector('.ranks').replaceChildren(...records().slice(0, 5).map((x, i) => {
      const li = el('li');
      li.classList.toggle('me', x.id === rec.id);
      li.append(el('span', 'n', `${i + 1}`), el('span', 'w', `${HERO[x.hero]?.name ?? ''} · ${day(x.at)}`), el('span', 'p', x.score.toLocaleString('ko-KR')));
      return li;
    }));
    if (!this.rankBox) { this.rankBox = mountRankBox(r.querySelector('.ranks')); }
    this.rankBox.set(this.run, { hero: rec.hero, heroName: HERO[rec.hero]?.name ?? '' });
    r.hidden = false;
    r.querySelector('.again').focus({ preventScroll: true });
  }
  get resultsOpen() { return !!this.resEl && !this.resEl.hidden; }
}
