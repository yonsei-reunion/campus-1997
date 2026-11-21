// 주소가 있는 창: the cards and modes with an address of their own over the game (the notes ?memos, a note ?memo=<id>,
// the credits ?credits, a mini game under way ?game=<key>). Each is opened with history.pushState, so the browser's
// back button closes it and leaves the game as it was before; closed by its own buttons, the entry is let go of with
// history.back(), so the history keeps no dead entries. A page opened at such an address puts the plain game under it
// first (base), so back goes to the game there too.
//   open(id, url, close)   push the entry; close() runs when back (or a lower card closing) takes it away
//   close(ids, run = true) take the lowest of ids and every entry over it away (their close() too, unless run false);
//                          false when none of them is open
//   urlWith(key, value)    this page's address with that card's parameter (the other cards' ones dropped)
const KEYS = ['memos', 'memo', 'credits'];
const stack = [];           // { id, close }, the lowest first; entry i has history.state.y97 = i + 1
let pending = 0;            // steps back asked for, not gone yet (several closes in one task: one history.go)
let ignore = 0;             // popstates of our own going back
let queue = [];             // pushes waiting for that going back to land

export function urlWith(key = null, value = '') {
  const q = new URLSearchParams(location.search);
  for (const k of KEYS) q.delete(k);
  if (key) q.set(key, value);
  const s = [...q].map(([k, v]) => (v === '' ? encodeURIComponent(k) : `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)).join('&');
  return location.pathname + (s ? `?${s}` : '') + location.hash;
}
export const fullUrl = (rel) => location.origin + rel;

const later = (f) => { if (pending || ignore) queue.push(f); else f(); };

export function has(id) { return stack.some((e) => e.id === id); }

export function open(id, url, close) {
  const top = stack[stack.length - 1];
  if (top?.id === id) {                       // (the same card again: its address now)
    top.close = close;
    const n = stack.length;
    later(() => history.replaceState({ y97: n }, '', url));
    return;
  }
  stack.push({ id, close });
  const n = stack.length;
  later(() => history.pushState({ y97: n }, '', url));
}

export function close(ids, run = true) {
  const i = stack.findIndex((e) => ids.includes(e.id));
  if (i < 0) return false;
  const gone = stack.splice(i).reverse();
  if (!pending) setTimeout(flush, 0);
  pending += gone.length;
  if (run) for (const e of gone) e.close();
  return true;
}
function flush() {
  if (!pending) return;
  ignore++;
  history.go(-pending);
  pending = 0;
}

// the page opened at a card's address: the plain game under it (then open() the card)
export function base() { history.replaceState(null, '', urlWith()); }

addEventListener('popstate', (e) => {
  if (ignore) {
    ignore--;
    const q = queue;
    queue = [];
    for (const f of q) f();
    return;
  }
  const n = e.state?.y97 ?? 0;
  if (n < stack.length) for (const g of stack.splice(n).reverse()) g.close();
  else if (n > stack.length) { ignore++; history.go(stack.length - n); }     // (forward: a card closed stays closed)
});
