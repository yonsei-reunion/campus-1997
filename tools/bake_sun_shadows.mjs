// Bake the campus's static sun shadow (web/src/bakedshadow.js) into web/public/assets/textures/sun_shadow.png, and
// the height of the walked surface over the terrain it lies on (terraces, plinths, flights) into sun_ground.png.
// sun_shadow.png holds the town south of the campus too (정문 밖, 연세로, 신촌 로터리), coarser, in slices east of the
// campus's block (bakedshadow.js TOWN_RECT, SUN_MAP_GLSL).
// Run it after anything that casts a shadow or is walked on has changed (buildings, trees, shrubs, props, parked
// cars, the amphitheater) or the sun:
//   cd web && npm run dev          (any port; the page is opened in desktop mode: the bake uses the shadow map)
//   node tools/bake_sun_shadows.mjs [port=5197]
// Needs Playwright's Chromium (`npx playwright install chromium`); PLAYWRIGHT=<dir with node_modules/playwright> if
// it is not installed where Node finds it. Writes 8-bit grey PNGs, row 0 = north.
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import os from 'os';
import zlib from 'zlib';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(here, '../web/public/assets/textures/sun_shadow.png');
const OUT_GROUND = path.join(here, '../web/public/assets/textures/sun_ground.png');
const port = process.argv[2] || '5197';

function findPlaywright() {
  const tries = [process.env.PLAYWRIGHT, path.join(here, '../web/'), here + '/'].filter(Boolean);
  const npx = path.join(os.homedir(), '.npm/_npx');           // a `npx playwright` cache
  if (fs.existsSync(npx)) for (const d of fs.readdirSync(npx)) tries.push(path.join(npx, d, 'node_modules/'));
  for (const t of tries) {
    try { return createRequire(t.endsWith('/') ? t : t + '/')('playwright'); } catch { /* next */ }
  }
  throw new Error('playwright not found: npx playwright install chromium, or set PLAYWRIGHT=<dir>');
}

// grey PNG: each row with the filter that packs it best
function png(w, h, data) {
  const crcT = new Int32Array(256).map((_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c; });
  const crc = (b) => { let c = -1; for (const v of b) c = crcT[(c ^ v) & 255] ^ (c >>> 8); return (c ^ -1) >>> 0; };
  const chunk = (type, body) => {
    const t = Buffer.from(type), len = Buffer.alloc(4), c = Buffer.alloc(4);
    len.writeUInt32BE(body.length);
    c.writeUInt32BE(crc(Buffer.concat([t, body])));
    return Buffer.concat([len, t, body, c]);
  };
  const raw = Buffer.alloc((w + 1) * h), cand = Array.from({ length: 5 }, () => Buffer.alloc(w));
  for (let y = 0; y < h; y++) {
    const row = data.subarray(y * w, (y + 1) * w), up = y ? data.subarray((y - 1) * w, y * w) : new Uint8Array(w);
    let best = 0, bestS = Infinity;
    for (let f = 0; f < 5; f++) {
      const o = cand[f];
      let s = 0;
      for (let x = 0; x < w; x++) {
        const a = x ? row[x - 1] : 0, b = up[x], c = x ? up[x - 1] : 0;
        let p = 0;
        if (f === 1) p = a; else if (f === 2) p = b; else if (f === 3) p = (a + b) >> 1;
        else if (f === 4) { const q = a + b - c, pa = Math.abs(q - a), pb = Math.abs(q - b), pc = Math.abs(q - c); p = pa <= pb && pa <= pc ? a : pb <= pc ? b : c; }
        const v = (row[x] - p) & 255;
        o[x] = v;
        s += v < 128 ? v : 256 - v;
      }
      if (s < bestS) { bestS = s; best = f; }
    }
    raw[y * (w + 1)] = best;
    cand[best].copy(raw, y * (w + 1) + 1);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8; ihdr[9] = 0;                                    // 8 bit, greyscale
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(raw, { level: 9 })), chunk('IEND', Buffer.alloc(0))]);
}

const { chromium } = findPlaywright();
const browser = await chromium.launch({ args: ['--use-angle=vulkan', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
page.on('pageerror', (e) => console.log('pageerror', e.message));
page.on('console', (m) => { if (m.type() === 'error') console.log('console', m.text().slice(0, 300)); });
await page.goto(`http://localhost:${port}/`, { waitUntil: 'load' });
await page.waitForFunction(() => window.__y97 && window.__y97.bird, null, { timeout: 300000 });
await page.evaluate(() => window.__y97.setSeason('summer'));     // the leaves of May (April and October differ little)
await page.waitForTimeout(8000);
const t0 = Date.now();
const res = await page.evaluate(async () => {
  const { width, height, data, lift } = await window.__y97.bakeSunMap();
  const b64 = (a) => {
    let s = '';
    for (let i = 0; i < a.length; i += 0x8000) s += String.fromCharCode.apply(null, a.subarray(i, i + 0x8000));
    return btoa(s);
  };
  return { w: width, h: height, b64: b64(data), lw: lift.width, lh: lift.height, lift: b64(lift.data) };
});
await browser.close();
const { w, h } = res, data = new Uint8Array(Buffer.from(res.b64, 'base64')), lift = new Uint8Array(Buffer.from(res.lift, 'base64'));
fs.writeFileSync(OUT, png(w, h, data));
fs.writeFileSync(OUT_GROUND, png(res.lw, res.lh, lift));
let lit = 0, raised = 0, top = 0, full = 0;
for (const v of data) lit += v;
// (the town's slices: the columns east of the campus's 3200, the rows they fill)
let tl = 0, tn = 0;
for (let r = 0; r < h; r++) for (let c = 3200; c < w; c++) { const v = data[r * w + c]; if (v < 255) { tl += v; tn++; } }
for (const v of lift) { if (v >= 10) raised++; if (v > top) top = v; if (v === 255) full++; }
const MB = (f) => (fs.statSync(f).size / 1e6).toFixed(2);
console.log(`baked ${w}x${h} in ${((Date.now() - t0) / 1000).toFixed(0)} s, mean ${(lit / data.length / 255).toFixed(3)} -> ${OUT} (${MB(OUT)} MB)`);
console.log(`town slices: ${(tn / 1e6).toFixed(2)} M texels in some shadow, mean of those ${(tl / Math.max(1, tn) / 255).toFixed(3)}`);
// (sun_ground: 0.05 m a level, src/bakedshadow.js LIFT_STEP; 255 = 12.75 m or more)
console.log(`walked surface: ${(raised / lift.length * 100).toFixed(1)} % of the texels 0.5 m or more over the terrain, highest ${(top * 0.05).toFixed(2)} m` +
  `${full ? ` (${full} texels clipped)` : ''} -> ${OUT_GROUND} (${MB(OUT_GROUND)} MB)`);
