import { defineConfig } from 'vite';
import { execSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

// Build number appended to every data / model / texture / photo URL (src/util.js versioned()): GitHub Pages serves
// them with a 10-minute cache, so a new deploy would otherwise mix fresh code with stale assets for a while.
function buildId() {
  if (process.env.GITHUB_SHA) return process.env.GITHUB_SHA.slice(0, 8);
  try { return execSync('git rev-parse --short=8 HEAD', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); } catch { /* not a git checkout */ }
  return Date.now().toString(36);
}

// A content hash per file of public/data and public/assets (but the news pages' pictures), so a deploy changes the URL
// (src/util.js versioned()) only of the files that changed, and the browser and the service worker (public/sw.js) keep
// the rest. A .png with a .webp beside it made from that very PNG (tools/webp_textures.py records its sha1) is served
// as the .webp; a PNG rewritten since falls back to itself.
function assetHashes() {
  const pub = new URL('./public/', import.meta.url).pathname;
  let made = {};
  try { made = JSON.parse(readFileSync(new URL('../tools/webp_sources.json', import.meta.url), 'utf8')); } catch { /* none yet */ }
  const sha1 = (b) => createHash('sha1').update(b).digest('hex');
  const out = {};
  const walk = (dir) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, e.name);
      const key = relative(pub, p).split(sep).join('/');
      if (e.isDirectory()) { if (key !== 'assets/news') walk(p); continue; }
      if (key.endsWith('.webp') && existsSync(p.slice(0, -5) + '.png')) continue;      // (under its PNG's name)
      let file = p, body = readFileSync(p);
      if (key.endsWith('.png') && made[key] && existsSync(p.slice(0, -4) + '.webp') && made[key] === sha1(body)) {
        file = p.slice(0, -4) + '.webp';
        body = readFileSync(file);
      }
      const h = sha1(body).slice(0, 10);
      out[key] = file === p ? h : `${h}:webp`;
    }
  };
  for (const d of ['data', 'assets']) walk(join(pub, d));
  return out;
}

// Phones' copies of the big textures (tools/mobile_textures.py): source -> [copy, its longest side], for the sources
// the copy was made from as they are now (src/util.js phoneCopy)
function phoneCopies() {
  const pub = new URL('./public/', import.meta.url).pathname;
  let rec = {};
  try { rec = JSON.parse(readFileSync(new URL('../tools/mobile_sources.json', import.meta.url), 'utf8')); } catch { /* none yet */ }
  const out = {};
  for (const [key, [copy, size, sha]] of Object.entries(rec)) {
    if (!existsSync(join(pub, key)) || !existsSync(join(pub, copy))) continue;
    if (createHash('sha1').update(readFileSync(join(pub, key))).digest('hex') === sha) out[key] = [copy, size];
  }
  return out;
}

export default defineConfig(({ command }) => ({
  base: './',
  server: { port: 5197 },
  build: {
    chunkSizeWarningLimit: 2000,
    assetsInlineLimit: 0,
    // the game, the 새 소식 page (it shares src/notes.js with the game's news panel) and the 캠퍼스 사람들 page (the
    // cast alone, src/people.js)
    rollupOptions: { input: { main: 'index.html', news: 'news.html', people: 'people.html' } },
  },
  define: {
    __BUILD__: JSON.stringify(command === 'serve' ? 'dev' : buildId()),
    __ASSETS__: JSON.stringify(command === 'serve' ? {} : assetHashes()),
    __PHONE__: JSON.stringify(phoneCopies()),
  },
}));
