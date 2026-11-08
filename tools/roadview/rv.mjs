// Kakao Map roadview, headless.  Game coords: x = east, y = north (m), as tools/build_campus.py xy().
//   node tools/roadview/rv.mjs near <x> <y> [radius=60]     nearest pano and its past panos
//   node tools/roadview/rv.mjs info <panoId> [...]            date, game xy, north angle, pasts, neighbours
//   node tools/roadview/rv.mjs shots <spec.json> <outDir>     screenshots; spec = [{pano, pan?|look:[x,y], tilt?, zoom?, name?}, ...]
//   node tools/roadview/rv.mjs past <node2011> <2008|2010> <outDir> <name:x:y[:zoom]|name:pan:P[:zoom]> ...
//       a past pano of a 2011 node, full screen in compare mode (2010-12 ids along 백양로 load neither by URL nor by
//       setPanoId).  Kakao reports the NODE's position for it, so solve its position from landmarks.
// pan = bearing (0 = north, 90 = east), floored to a whole degree (the viewer does that anyway); look = aim at a game
// point from the pano's Kakao position.  tilt: negative = up; use 0 for bearings (vertical edges stay vertical).
// zoom 0 (f ~458 px) .. 3 (f 783 px) in the 1388 x 900 view.  Bearing of pixel x: pan + atan((x - 694) / f).
// Kakao headings are off by up to ~5 deg and positions by metres: use angles between things in one pano (README.md).
// Screenshots are for looking only: write them outside the repo and never commit them (CLAUDE.md 「고증 자료」).
import fs from 'fs';
import path from 'path';
import { launch, toLL, LON0, LAT0, KX, KY, wholePan, hideOverlays } from './pw.mjs';

const [cmd, ...args] = process.argv.slice(2);
const { browser, page } = await launch();

async function open(pano) {
  await page.goto(`https://map.kakao.com/?map_type=TYPE_MAP&map_attribute=ROADVIEW&panoid=${pano}&pan=0&tilt=0&zoom=0`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(() => { const c = window.Application?.roadviewController?.normalRoadview_; return c && c.getPanoData && c.getPanoData()?.panoId; }, null, { timeout: 40000 });
  await page.waitForTimeout(2500);
}
async function setPano(pano) {
  const cur = await page.evaluate(() => window.Application?.roadviewController?.normalRoadview_?.getPanoId?.());
  if (!cur) { await open(pano); return; }
  if (cur == pano) return;
  try {
    await page.evaluate(id => window.Application.roadviewController.normalRoadview_.setPanoId(Number(id)), pano);
    await page.waitForFunction(id => { const r = window.Application.roadviewController.normalRoadview_; return r.getPanoId() == id && r.getPanoData()?.panoId == id; }, pano, { timeout: 12000 });
    await page.waitForTimeout(2500);
  } catch (e) { await open(pano); }
}
async function describe() {
  return page.evaluate(([LON0, LAT0, KX, KY]) => {
    const r = window.Application.roadviewController.normalRoadview_;
    const d = r.getPanoData(); const p = r.getPosition();
    const c = new kakao.maps.Coords(p.x, p.y).toLatLng();
    const g = [(c.getLng() - LON0) * KX, (c.getLat() - LAT0) * KY];
    return { pano: d.panoId, date: d.date, xy: g.map(v => +v.toFixed(1)), northAngle: d.northAngle,
      pasts: (d.availablePasts || []).map(a => ({ pano: a.panoId, date: a.date })),
      spots: (d.spots || []).map(s => ({ pano: s.panoId, dir: s.dirnameKo })) };
  }, [LON0, LAT0, KX, KY]);
}
async function view(pan, tilt, zoom) {
  for (let k = 0; k < 2; k++) {   // zoom is sometimes ignored on the first call
    await page.evaluate(([pan, tilt, zoom]) => window.Application.roadviewController.normalRoadview_.setViewpoint({ pan, tilt, zoom }), [pan, tilt, zoom]);
    await page.waitForTimeout(k ? 3000 : 1200);
  }
  await hideOverlays(page);
}
const aim = (from, x, y) => wholePan(Math.atan2(x - from[0], y - from[1]) * 180 / Math.PI);

if (cmd === 'near') {
  const [x, y, rad = 60] = args.map(Number);
  await open(1017220175);
  const [lat, lng] = toLL(x, y);
  const id = await page.evaluate(([lat, lng, rad]) => new Promise(res => {
    try { new kakao.maps.RoadviewClient().getNearestPanoId(new kakao.maps.LatLng(lat, lng), rad, res); } catch (e) { res('ERR ' + e); }
    setTimeout(() => res(null), 15000);
  }), [lat, lng, rad]);
  if (!id || String(id).startsWith('ERR')) console.log('no pano within', rad, 'm', id || '');
  else { await setPano(id); console.log(JSON.stringify(await describe())); }
} else if (cmd === 'info') {
  for (const id of args) { await setPano(id); console.log(JSON.stringify(await describe())); }
} else if (cmd === 'shots') {
  const spec = JSON.parse(fs.readFileSync(args[0], 'utf8'));
  const outDir = args[1]; fs.mkdirSync(outDir, { recursive: true });
  for (const [i, s] of spec.entries()) {
    await setPano(s.pano);
    const d = await describe();
    const pan = s.look ? aim(d.xy, s.look[0], s.look[1]) : wholePan(s.pan ?? 0);
    const tilt = s.tilt ?? 0, zoom = s.zoom ?? 0;
    await view(pan, tilt, zoom);
    const name = s.name || `${String(i).padStart(2, '0')}_${s.pano}_p${pan}_t${Math.round(tilt)}_z${zoom}`;
    const file = path.join(outDir, name + '.png');
    await page.screenshot({ path: file });
    console.log(file, JSON.stringify({ pano: d.pano, date: d.date, xy: d.xy, pan, tilt, zoom }));
  }
} else if (cmd === 'past') {
  const [node, year, outDir, ...targets] = args; fs.mkdirSync(outDir, { recursive: true });
  await open(node);
  await page.locator('text=2011년 04월').first().click(); await page.waitForTimeout(2000);
  if (year === '2010') {   // the timeline knob: left end = 2008.08, ~140+ px right = 2010.12
    const bb = await page.locator('button.btn_drag:visible').first().boundingBox();
    await page.mouse.move(bb.x + 8, bb.y + 8); await page.mouse.down(); await page.mouse.move(bb.x + 208, bb.y + 8, { steps: 10 }); await page.mouse.up(); await page.waitForTimeout(2500);
  }
  await page.locator('.btn_compare:visible').first().click(); await page.waitForTimeout(5000);
  await page.evaluate(() => window.Application.roadviewController.normalRoadview_.pastCompare.setRatio(1)); await page.waitForTimeout(2500);
  const d = await describe();
  const past = await page.evaluate(() => { const pc = window.Application.roadviewController.normalRoadview_.pastCompare; return { pano: pc.getPanoId(), date: pc.getDate() }; });
  console.log(JSON.stringify({ node: d.pano, nodeDate: d.date, nodeXY: d.xy, past: past.pano, pastDate: past.date,
    note: 'aimed from the node position; the past pano stands metres away and its heading frame differs' }));
  for (const t of targets) {
    const [name, a, b, z = '3'] = t.split(':');
    const pan = a === 'pan' ? wholePan(+b) : aim(d.xy, +a, +b);
    await view(pan, 0, +z);
    const file = path.join(outDir, `${name}.png`);
    await page.screenshot({ path: file });
    console.log(file, JSON.stringify({ pan, zoom: +z }));
  }
} else {
  console.log('usage: near <x> <y> [r] | info <pano...> | shots <spec.json> <outDir> | past <node2011> <2008|2010> <outDir> <targets...>');
}
await browser.close();
