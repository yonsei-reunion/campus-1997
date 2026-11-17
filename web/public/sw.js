// Keeps the game's versioned files (src/util.js versioned(): data, models, textures, photos with ?v=<content hash>) on
// the disk. A URL's file never changes, so a kept one is answered without asking GitHub Pages (whose cache lasts
// 10 minutes, and every deploy used to change every URL). Taking in a new version of a file drops its older ones.
// Everything else (the pages, vite's own hashed scripts) goes to the network as before.
const CACHE = 'y97-files-1';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
  await self.clients.claim();
})()));

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || req.headers.has('range')) return;
  const u = new URL(req.url);
  if (u.origin !== self.location.origin || !u.searchParams.has('v')) return;
  e.respondWith(answer(e, req, u));
});

async function answer(e, req, u) {
  let cache;
  try {
    cache = await caches.open(CACHE);
    const hit = await cache.match(u.href, { ignoreVary: true });
    if (hit) return hit;
  } catch { /* storage blocked: the network alone */ }
  const res = await fetch(req);
  if (cache && res.ok && res.type === 'basic') e.waitUntil(keep(cache, u, res.clone()));
  return res;
}

async function keep(cache, u, res) {
  try {
    const path = u.origin + u.pathname;
    for (const old of await cache.keys(path, { ignoreSearch: true, ignoreVary: true })) {
      if (old.url !== u.href) await cache.delete(old, { ignoreVary: true });
    }
    await cache.put(u.href, res);
  } catch { /* full (quota): the network next time */ }
}
