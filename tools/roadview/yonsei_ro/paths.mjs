// imagePath of each past pano (pre-2014) of the given 2026 nodes: node paths.mjs <node> ... > $YRO_WORK/paths.jsonl
import { launch } from '../pw.mjs';
const nodes = process.argv.slice(2);
const { browser, page } = await launch();
await page.goto(`https://map.kakao.com/?map_type=TYPE_MAP&map_attribute=ROADVIEW&panoid=${nodes[0]}&pan=0&tilt=0&zoom=0`, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForFunction(() => { const c = window.Application?.roadviewController?.normalRoadview_; return c && c.getPanoData && c.getPanoData()?.panoId; }, null, { timeout: 40000 });
await page.waitForTimeout(2500);
for (const n of nodes) {
  const cur = await page.evaluate(() => window.Application.roadviewController.normalRoadview_.getPanoId());
  if (cur != n) {
    await page.evaluate(id => window.Application.roadviewController.normalRoadview_.setPanoId(Number(id)), n);
    try { await page.waitForFunction(id => window.Application.roadviewController.normalRoadview_.getPanoData()?.panoId == id, n, { timeout: 12000 }); } catch (e) { console.error('timeout', n); continue; }
    await page.waitForTimeout(1500);
  }
  const r = await page.evaluate(() => {
    const d = window.Application.roadviewController.normalRoadview_.getPanoData();
    const out = [{ pano: d.panoId, date: d.date, imagePath: d.imagePath, northAngle: d.northAngle, position: d.position }];
    for (const a of (d.availablePasts || [])) {
      if (a.date >= '2014') continue;
      let st = null; try { st = d.getPastStreet(a.panoId); } catch (e) { }
      out.push({ pano: a.panoId, date: a.date, imagePath: st?.imagePath, northAngle: st?.northAngle, position: st?.position, shotTool: st?.shotTool });
    }
    return out;
  });
  console.log(JSON.stringify({ node: +n, items: r }));
}
await browser.close();
