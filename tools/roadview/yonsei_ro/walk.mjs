// walk the 2026 nodes along 연세로 via spots (북/남), print each node's xy and pasts up to 2013
import { launch, LON0, LAT0, KX, KY } from '../pw.mjs';
const { browser, page } = await launch();
const start = process.argv[2], dir = process.argv[3], n = +process.argv[4];
await page.goto(`https://map.kakao.com/?map_type=TYPE_MAP&map_attribute=ROADVIEW&panoid=${start}&pan=0&tilt=0&zoom=0`, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForFunction(() => { const c = window.Application?.roadviewController?.normalRoadview_; return c && c.getPanoData && c.getPanoData()?.panoId; }, null, { timeout: 40000 });
await page.waitForTimeout(2500);
const desc = () => page.evaluate(([LON0, LAT0, KX, KY]) => {
  const r = window.Application.roadviewController.normalRoadview_;
  const d = r.getPanoData(); const p = r.getPosition();
  const c = new kakao.maps.Coords(p.x, p.y).toLatLng();
  const g = [(c.getLng() - LON0) * KX, (c.getLat() - LAT0) * KY];
  return { pano: d.panoId, date: d.date, xy: g.map(v => +v.toFixed(1)), pasts: (d.availablePasts || []).filter(a => a.date < '2014').map(a => a.panoId + '@' + a.date.slice(0, 10)), spots: (d.spots || []).map(s => [s.panoId, s.dirnameKo]) };
}, [LON0, LAT0, KX, KY]);
let seen = new Set();
for (let i = 0; i < n; i++) {
  const d = await desc();
  console.log(JSON.stringify(d));
  seen.add(d.pano);
  const nx = d.spots.find(s => s[1] === dir && !seen.has(s[0]));
  if (!nx) break;
  await page.evaluate(id => window.Application.roadviewController.normalRoadview_.setPanoId(Number(id)), nx[0]);
  try { await page.waitForFunction(id => window.Application.roadviewController.normalRoadview_.getPanoData()?.panoId == id, nx[0], { timeout: 12000 }); } catch (e) { console.log('timeout', nx[0]); }
  await page.waitForTimeout(1500);
}
await browser.close();
