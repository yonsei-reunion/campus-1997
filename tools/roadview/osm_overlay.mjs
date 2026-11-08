// Draw OSM building outlines (red) over Kakao's base map or skyview, to check how well the outlines the game and the
// photo fits rely on sit on the buildings (the skyview roofs show no lean on campus).
//   node tools/roadview/osm_overlay.mjs <out.png> <x> <y> [level=1] [sky] [wayId,wayId,...]
// x, y: game coordinates of the view centre.  Level 1 = 0.25 m/px.  The left search panel covers x < ~400 px.
// Result 2026-11-08: 중앙도서관, 제1공학관, 백주년기념관 match the skyview roofs within ~1 m.
import fs from 'fs';
import path from 'path';
import { launch, root, toLL } from './pw.mjs';

const [out, x, y, level = '1', sky = '', ids = ''] = process.argv.slice(2);
const WANT = ids ? ids.split(',').map(Number) :
  [163525865, 324328422, 1444448640, 240334198, 205583531, 256933753, 468614722, 371403811, 222843398, 324328472, 429249499, 473006250];
const osm = JSON.parse(fs.readFileSync(path.join(root, 'data/raw/osm_campus.json'), 'utf8')).elements;
const B = osm.filter(e => WANT.includes(e.id) && e.geometry).map(e => e.geometry.map(p => [p.lat, p.lon]));
const [lat, lng] = toLL(+x, +y);

const { browser, page } = await launch();
await page.goto(`https://map.kakao.com/?map_type=${sky === 'sky' ? 'TYPE_SKYVIEW' : 'TYPE_MAP'}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForFunction(() => window.Application?.map?.getProjection, null, { timeout: 40000 });
await page.waitForTimeout(3000);
const mpp = await page.evaluate(([lat, lng, level, B]) => {
  const map = window.Application.map;
  const C = ll => { const q = new kakao.maps.LatLng(ll[0], ll[1]); return q.toCoords ? q.toCoords() : q; };
  map.setLevel(+level); map.setCenter(C([lat, lng]));
  for (const path of B) new kakao.maps.Polygon({ path: path.map(C), strokeColor: '#ff0000', strokeWeight: 2, strokeOpacity: 0.9, fillOpacity: 0 }).setMap(map);
  const pr = map.getProjection();
  const a = pr.containerPointFromCoords(C([lat, lng])), b = pr.containerPointFromCoords(C([lat, lng + 100 / (111320 * Math.cos(lat * Math.PI / 180))]));
  return 100 / Math.hypot(b.x - a.x, b.y - a.y);
}, [lat, lng, level, B]);
await page.waitForTimeout(4000);
await page.screenshot({ path: out });
console.log(out, JSON.stringify({ x: +x, y: +y, level: +level, sky: sky === 'sky', mPerPx: +mpp.toFixed(3), outlines: B.length }));
await browser.close();
