// Small helpers shared by the game modules.
import * as THREE from 'three';

export const $ = (s) => document.querySelector(s);

// every asset URL carries its file's content hash (vite.config.js assetHashes), so a new deploy never mixes with cached
// old files and a file that did not change keeps its URL (and its place in the browser's cache and public/sw.js's). A
// file the build did not hash carries the build number. A PNG with a WebP copy (tools/webp_textures.py) comes as that.
export const BUILD = __BUILD__;
const ASSETS = __ASSETS__;
export function versioned(url) {
  if (BUILD === 'dev') return url;
  const q = url.indexOf('?');
  let path = q < 0 ? url : url.slice(0, q);
  const h = ASSETS[path.replace(/^\.\//, '')];
  if (h?.endsWith(':webp')) path = path.slice(0, -4) + '.webp';
  const rest = q < 0 ? '' : url.slice(q + 1) + '&';
  return `${path}?${rest}v=${h ? h.split(':')[0] : BUILD}`;
}

// The service worker (public/sw.js) keeps the versioned files, so a return visit takes from the disk what this deploy
// did not change. Not under vite's dev server, whose files carry no version.
if (BUILD !== 'dev' && 'serviceWorker' in navigator && location.protocol !== 'file:') {
  navigator.serviceWorker.register('./sw.js').catch(() => { /* (private windows, blocked storage) */ });
}

// GitHub Pages caches index.html for 10 minutes, and index.html is what names this deploy's script. So a visit just
// after a deploy (or a cached page) can run the old game. On load, ask the server (no-store) which script the page names;
// if it is not the one running, reload once for it (the sessionStorage mark keeps a stale CDN edge from looping).
if (BUILD !== 'dev' && /^https?:$/.test(location.protocol)) {
  const mine = document.querySelector('script[type="module"][src*="main-"]')?.getAttribute('src');
  if (mine) {
    fetch(`./index.html?fresh=${Date.now()}`, { cache: 'no-store' }).then((r) => (r.ok ? r.text() : '')).then((html) => {
      const now = html.match(/src="([^"]*main-[^"]+\.js)"/)?.[1];
      if (!now || now === mine) return;
      try { if (sessionStorage.getItem('y97-reload') === now) return; sessionStorage.setItem('y97-reload', now); } catch { return; }
      location.reload();
    }).catch(() => { /* offline: the page as it is */ });
  }
}

// Phones / tablets: no shadow maps, smaller textures, fewer people, touch controls and touch help texts.
// ?touch in the URL forces it (testing the phone layout on a desktop browser).
export const MOBILE = matchMedia('(pointer: coarse)').matches || /[?&]touch\b/.test(location.search);

// A phone's copy of a big texture (tools/mobile_textures.py), when there is one no larger than `max`, the size the phone
// shrinks that texture to anyway: the phone then downloads only what it uploads.
const PHONE = __PHONE__;
export function phoneCopy(url, max) {
  const c = MOBILE && PHONE[url.replace(/^\.\//, '')];
  return c && c[1] <= max ? c[0] : url;
}
// the same copy on any device (null when there is none): what a desktop shows first while the full image still comes
export function smallCopy(url) {
  return PHONE[url.replace(/^\.\//, '')]?.[0] ?? null;
}
document.documentElement.classList.toggle('touch', MOBILE);

export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const wrapAngle = (a) => Math.atan2(Math.sin(a), Math.cos(a));

// localStorage can throw (private mode, blocked site data)
export function safeGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
export function safeSet(k, v) { try { localStorage.setItem(k, v); } catch { /* ignore */ } }

// the mini games' own addresses (./?game=<key>, main.js), for sharing: ?game=shoot makes the title card the game's,
// the others make their button stand out on it. While one is under way the address bar says it (src/nav.js)
export const GAMES = { shoot: '농구 1분 슛 게임', run: '캠퍼스 달리기', photo: '이곳은 어디?', pager: '삐삐 호출', cheer: '연고전 응원 연습',
  class: '강의실 찾기', bday: '생일 축하' };
export const gameUrl = (key = 'shoot') => `${location.origin}${location.pathname}?game=${key}`;
// put text on the clipboard: the Clipboard API, or (plain http, an old browser) a hidden field's selection. True when
// it worked
export async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { /* not allowed here */ }
  const t = document.createElement('textarea');
  t.value = text; t.setAttribute('readonly', '');
  t.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0';
  document.body.appendChild(t);
  t.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch { ok = false; }
  t.remove();
  return ok;
}
// a copy button: copies what text() gives and says so on the button for a moment (or that it could not)
export function copyButton(btn, text, fail = '복사하지 못했어요 · 주소를 길게 눌러 복사하세요') {
  const label = btn.textContent;
  btn.addEventListener('click', async (e) => {
    e.stopPropagation();
    const ok = await copyText(text());
    btn.textContent = ok ? '복사했어요!' : fail;
    btn.classList.toggle('done', ok);
    clearTimeout(btn._t);
    btn._t = setTimeout(() => { btn.textContent = label; btn.classList.remove('done'); }, ok ? 1600 : 4000);
  });
}

// seeded PRNG: the same campus every visit
export function mulberry(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// {key: number of items} for a list, keyed by keyFn
export function countBy(list, keyFn) {
  const out = {};
  list.forEach((v, i) => { const k = keyFn(v, i); out[k] = (out[k] || 0) + 1; });
  return out;
}

export function polylineLength(pts) {
  let L = 0;
  for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  return L;
}

// closest point to (x, y) on the segment a-b: [qx, qy, distance]
export function closestOnSegment(x, y, ax, ay, bx, by) {
  const ex = bx - ax, ey = by - ay;
  const t = clamp(((x - ax) * ex + (y - ay) * ey) / (ex * ex + ey * ey || 1), 0, 1);
  const qx = ax + ex * t, qy = ay + ey * t;
  return [qx, qy, Math.hypot(x - qx, y - qy)];
}

// instance matrix for an object standing at campus (x, y) on height h, turned by rot about the vertical
const _p = new THREE.Vector3(), _q = new THREE.Quaternion(), _s = new THREE.Vector3();
const UP = new THREE.Vector3(0, 1, 0);
export function placeMatrix(out, x, h, y, rot = 0, scale = 1) {
  _p.set(x, h, -y);
  _q.setFromAxisAngle(UP, rot);
  if (typeof scale === 'number') _s.setScalar(scale); else _s.copy(scale);
  return out.compose(_p, _q, _s);
}
