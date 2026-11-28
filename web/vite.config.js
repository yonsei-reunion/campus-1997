import { defineConfig } from 'vite';
import { execSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, existsSync, rmSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

// Build number appended to every data / model / texture / photo URL (src/util.js versioned()): GitHub Pages serves
// them with a 10-minute cache, so a new deploy would otherwise mix fresh code with stale assets for a while.
function buildId() {
  if (process.env.GITHUB_SHA) return process.env.GITHUB_SHA.slice(0, 8);
  try { return execSync('git rev-parse --short=8 HEAD', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); } catch { /* not a git checkout */ }
  return Date.now().toString(36);
}

// The halls and landmarks in 160 m cells (tools/split_glb.mjs; gitignored): made again here when they are older than
// the two whole GLBs (a fresh checkout, GitHub Actions, a rebuild while no Blender export ran the split). The whole
// files stay in public/ for the tools that read them, but are not deployed (no page asks for them).
const { splitAll, stale } = await import('../tools/split_glb.mjs');
if (stale()) splitAll();
const WHOLE = ['assets/models/campus_buildings.glb', 'assets/models/campus_landmarks.glb'];
let outDir = '';

// A content hash per file of public/data and public/assets (but the news pages' pictures), so a deploy changes the URL
// (src/util.js versioned()) only of the files that changed, and the browser and the service worker (public/sw.js) keep
// the rest. A .png or .jpg with a .webp beside it made for that very file (tools/webp_textures.py records its sha1:
// the leaf atlases, the baked sun maps, the PBR maps) is served as the .webp; one rewritten since falls back to itself.
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
      if (WHOLE.includes(key)) continue;
      if (key.endsWith('.webp') && (existsSync(p.slice(0, -5) + '.png') || existsSync(p.slice(0, -5) + '.jpg'))) continue;   // (under its source's name)
      let file = p, body = readFileSync(p);
      if (/\.(png|jpg)$/.test(key) && made[key] && existsSync(p.slice(0, -4) + '.webp') && made[key] === sha1(body)) {
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

// The first files main.js asks for (src/main.js main()), named in index.html so that they come down beside the scripts
// rather than after them: main.js fetches the same URLs (src/util.js versioned()) and takes these answers.
const FIRST = ['data/campus.json', 'data/materials.json', 'data/sky.json', 'data/entrances.json', 'data/terrain_near.bin',
  'data/terrain_far.bin', 'data/terrain_south.bin', 'data/terrain_north.bin', 'assets/models/campus/chunks.json',
  'assets/models/campus/landmarks_base.glb', 'assets/models/campus/buildings_base.glb', 'assets/models/baekyangro.glb',
  'assets/models/campus_town_ground.glb', 'assets/hdri/env_1k_nosun.hdr'];

export default defineConfig(({ command }) => {
  const hashes = command === 'serve' ? {} : assetHashes();
  return {
    base: './',
    plugins: [{
      name: 'drop-whole-halls',
      apply: 'build',
      writeBundle(out) { outDir = out.dir; },
      closeBundle() { for (const f of WHOLE) rmSync(join(outDir, f), { force: true }); },
    }, {
      // @fontsource's faces name a .woff after each .woff2: every browser that runs the game (WebGL 2) reads woff2, so
      // the second source only doubles the style sheet the page waits for (and the build's font files)
      name: 'woff2-only',
      enforce: 'pre',
      transform(code, id) {
        if (!/@fontsource[\\/].*\.css(\?|$)/.test(id)) return null;
        return { code: code.replace(/,\s*url\([^)]*\.woff\)\s*format\(['"]woff['"]\)/g, ''), map: null };
      },
    }, {
      name: 'preload-first',
      apply: 'build',
      transformIndexHtml: {
        order: 'post',
        handler(html, ctx) {
          if (!/(^|\/)index\.html$/.test(ctx.filename)) return html;
          return FIRST.filter((f) => hashes[f] && !hashes[f].includes(':')).map((f) => ({
            tag: 'link', injectTo: 'head',
            attrs: { rel: 'preload', as: 'fetch', crossorigin: 'anonymous', href: `${f}?v=${hashes[f]}` },
          }));
        },
      },
    }],
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
      __ASSETS__: JSON.stringify(hashes),
      __PHONE__: JSON.stringify(phoneCopies()),
    },
  };
});
