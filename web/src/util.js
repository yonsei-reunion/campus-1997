// Small helpers shared by the game modules.
import * as THREE from 'three';

export const $ = (s) => document.querySelector(s);

// every asset URL carries the build number (vite.config.js), so a new deploy never mixes with cached old files
export const BUILD = __BUILD__;
export const versioned = (url) => (BUILD === 'dev' ? url : `${url}${url.includes('?') ? '&' : '?'}v=${BUILD}`);

// Phones / tablets: no shadow maps, smaller textures, fewer people, touch controls and touch help texts.
// ?touch in the URL forces it (testing the phone layout on a desktop browser).
export const MOBILE = matchMedia('(pointer: coarse)').matches || /[?&]touch\b/.test(location.search);
document.documentElement.classList.toggle('touch', MOBILE);

export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export const wrapAngle = (a) => Math.atan2(Math.sin(a), Math.cos(a));

// localStorage can throw (private mode, blocked site data)
export function safeGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
export function safeSet(k, v) { try { localStorage.setItem(k, v); } catch { /* ignore */ } }

// the 1-minute basketball game's own address (main.js ?game=shoot), for sharing
export const gameUrl = () => `${location.origin}${location.pathname}?game=shoot`;
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
export function copyButton(btn, text) {
  const label = btn.textContent;
  btn.addEventListener('click', async (e) => {
    e.stopPropagation();
    const ok = await copyText(text());
    btn.textContent = ok ? '복사했어요!' : '복사하지 못했어요 · 주소를 길게 눌러 복사하세요';
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
