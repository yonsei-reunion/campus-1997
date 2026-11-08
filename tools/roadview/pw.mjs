// Shared helpers for the Kakao roadview tools: find playwright (as tools/snapshots.mjs does), launch headless
// chromium with the GPU flags the roadview needs, and the game <-> lat/lng conversion of tools/build_campus.py xy().
import { createRequire } from 'module';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { fileURLToPath } from 'url';

export const here = path.dirname(fileURLToPath(import.meta.url));
export const root = path.resolve(here, '../..');

export const LON0 = 126.938, LAT0 = 37.564, KX = 111320 * Math.cos(LAT0 * Math.PI / 180), KY = 110574;
export const toGame = (lat, lng) => [(lng - LON0) * KX, (lat - LAT0) * KY];
export const toLL = (x, y) => [LAT0 + y / KY, LON0 + x / KX];

function findPlaywright() {
  const tries = [process.env.PLAYWRIGHT, path.join(root, 'web/'), here + '/'].filter(Boolean);
  const npx = path.join(os.homedir(), '.npm/_npx');
  if (fs.existsSync(npx)) for (const d of fs.readdirSync(npx)) tries.push(path.join(npx, d, 'node_modules/'));
  for (const t of tries) {
    try { return createRequire(t.endsWith('/') ? t : t + '/')('playwright'); } catch { /* next */ }
  }
  throw new Error('playwright not found: npx playwright install chromium, or set PLAYWRIGHT=<dir>');
}

export async function launch() {
  const { chromium } = findPlaywright();
  const browser = await chromium.launch({ args: ['--use-angle=vulkan', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1388, height: 900 }, locale: 'ko-KR' });
  return { browser, page };
}

// The viewer floors the pan to a whole degree (258.3, 258.6 and 258.9 all render as 258), so aim with whole degrees
// and report those: bearing of a pixel = pan + atan((x - 694) / f), f = 783 px at zoom 3, ~458 px at zoom 0.
export const wholePan = p => Math.floor(((p % 360) + 360) % 360 + 1e-9);

export async function hideOverlays(page) {
  await page.evaluate(() => { document.querySelectorAll('.box_minimap, .minimap, .roadview_minimap, .area_util, .zoom_control').forEach(e => e.style.visibility = 'hidden'); });
}
