// 1분 슛 게임의 기록: every game played in this browser, kept in localStorage (best first, up to MAX), and the ranking
// table the results card (shootout.js), the title card and the pause card (main.js) show. Nothing leaves the browser.
// A record: { id, makes, shots, threes, perfect, hero (characters.js id), view ('first' | 'third'), name, at (ms) }.
// Loaded with the game, or when a ranking is opened (main.js), not with the page.
import { HERO } from './characters.js';
import { safeGet, safeSet } from './util.js';
import './records.css';

export const KEY = 'y97-shoot-records';
const OLD = 'y97-shoot-best';           // (before the records: the best score alone)
const NAME = 'y97-shoot-name';          // the name last typed on the results card
const MAX = 100, SHOW = 10;

const pct = (r) => (r.shots ? r.makes / r.shots : 0);
// more baskets first; the same: the better share of shots; still the same: the earlier game
export const order = (a, b) => b.makes - a.makes || pct(b) - pct(a) || (a.at ?? 0) - (b.at ?? 0);

export function load() {
  let list;
  try { list = JSON.parse(safeGet(KEY) || '[]'); } catch { list = []; }
  if (!Array.isArray(list)) list = [];
  list = list.filter((r) => r && typeof r === 'object' && Number.isFinite(r.makes));
  if (!list.length) {
    const old = +(safeGet(OLD) || 0);
    if (old > 0) list.push({ id: 1, makes: old, shots: null, at: null });
  }
  return list.sort(order);
}

function save(list) { safeSet(KEY, JSON.stringify(list.slice(0, MAX))); }

// keep a game; returns its place among all kept (1 = best), how many there are and the list
export function add(rec) {
  const list = load();
  list.push(rec);
  list.sort(order);
  save(list);
  return { rank: list.indexOf(rec) + 1, total: list.length, list };
}

export function rename(id, name) {
  const list = load(), r = list.find((x) => x.id === id);
  name = name.trim().slice(0, 12);
  if (r) { r.name = name; save(list); }
  safeSet(NAME, name);
}

export function clear() {
  safeSet(KEY, '[]');
  try { localStorage.removeItem(OLD); } catch { /* storage blocked */ }
}

export const lastName = () => safeGet(NAME) || '';
export const who = (r) => r.name || HERO[r.hero]?.name || (r.at ? '이름 없음' : '이전 기록');

function when(at) {
  if (!at) return '—';
  const d = new Date(at), p = (n) => String(n).padStart(2, '0');
  return `${d.getMonth() + 1}.${d.getDate()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

// the ranking as a table: the first `limit` games, and the game `mark` (id) highlighted (added below at its place
// when it is further down)
export function table(list, { mark = null, limit = SHOW } = {}) {
  const t = document.createElement('table');
  t.className = 'shootranks';
  t.innerHTML = '<thead><tr><th>순위</th><th>이름</th><th>골</th><th>성공률</th><th class="v">시점</th><th class="d">날짜</th></tr></thead><tbody></tbody>';
  const body = t.tBodies[0];
  const row = (r, i) => {
    const tr = document.createElement('tr');
    if (r.id === mark) tr.className = 'me';
    const cells = [`${i + 1}`, who(r), `${r.makes}`, r.shots ? `${Math.round(100 * pct(r))}% <small>${r.makes}/${r.shots}</small>` : '—',
      r.view ? (r.view === 'first' ? '1인칭' : '3인칭') : '—', when(r.at)];
    cells.forEach((c, k) => {
      const td = document.createElement('td');
      if (k === 1) td.textContent = c; else td.innerHTML = c;
      if (k === 4) td.className = 'v';
      if (k === 5) td.className = 'd';
      tr.appendChild(td);
    });
    body.appendChild(tr);
  };
  list.slice(0, limit).forEach(row);
  const at = mark === null ? -1 : list.findIndex((r) => r.id === mark);
  if (at >= limit) {
    if (at > limit) { const gap = body.insertRow(); gap.className = 'gap'; gap.insertCell().colSpan = 6; gap.cells[0].textContent = '⋯'; }
    row(list[at], at);
  }
  if (!list.length) { const tr = body.insertRow(); tr.className = 'none'; const td = tr.insertCell(); td.colSpan = 6; td.textContent = '아직 기록이 없어요'; }
  return t;
}

// the whole ranking over everything (the title card, the pause card, the results card's 「순위 전체」)
let panel = null;
export function openRanking({ mark = null, onChange = null } = {}) {
  if (!panel) {
    panel = document.createElement('div');
    panel.id = 'shootrank';
    panel.innerHTML = '<div role="dialog" aria-label="1분 슛 게임 순위"><h2>1분 슛 게임 순위</h2><p class="sub">이 브라우저에 저장된 기록이에요</p>'
      + '<div class="tbl"></div><div class="btns"><button type="button" class="clear">기록 지우기</button><button type="button" class="close">닫기</button></div></div>';
    document.body.appendChild(panel);
    const close = () => { panel.hidden = true; };
    panel.addEventListener('click', (e) => { if (e.target === panel) close(); });
    panel.querySelector('.close').addEventListener('click', close);
    addEventListener('keydown', (e) => {
      if (panel.hidden || e.code !== 'Escape') return;
      e.stopImmediatePropagation(); e.preventDefault();
      close();
    }, true);
    // two presses to wipe them: the first only asks
    const wipe = panel.querySelector('.clear');
    wipe.addEventListener('click', () => {
      if (!wipe.classList.contains('ask')) {
        wipe.classList.add('ask'); wipe.textContent = '한 번 더 누르면 모두 지워요';
        clearTimeout(wipe._t); wipe._t = setTimeout(() => { wipe.classList.remove('ask'); wipe.textContent = '기록 지우기'; }, 3000);
        return;
      }
      clear();
      wipe.classList.remove('ask'); wipe.textContent = '기록 지우기';
      fill();
      panel._onChange?.();
    });
  }
  const fill = () => {
    const list = load(), box = panel.querySelector('.tbl');
    box.replaceChildren(table(list, { mark: panel._mark, limit: 20 }));
    panel.querySelector('.clear').hidden = !list.length;
    panel.querySelector('.sub').textContent = list.length ? `이 브라우저에 저장된 기록 ${list.length}판` : '이 브라우저에 저장된 기록이에요';
  };
  panel._mark = mark; panel._onChange = onChange;
  fill();
  panel.hidden = false;
  panel.querySelector('.close').focus({ preventScroll: true });
}
