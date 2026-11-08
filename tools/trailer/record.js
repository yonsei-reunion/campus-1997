// 신촌 캠퍼스 1997 trailer: paste into the browser console on the running game (npm run dev), with
// `python3 tools/trailer/frame_server.py <frames dir>` running.  Renders 46 s at 30 fps, 1920x1080, frame by frame
// (window.__y97.record steps the game loop at a fixed time, so a slow or background tab still gives smooth video):
// a bird's-eye flight over the campus, down onto 백양로 as in the 1997 aerial photo, a swoop down behind the walker who
// walks up 백양로, then back up into the sky and jumps to 독수리상 and 언더우드 동상.  Then: python3 tools/trailer/make_video.py <dir with frames/> out.mp4
(async () => {
  const y = window.__y97, B = y.bird, FPS = 30, T = 65;
  // bird's-eye keyframes: t, x, y, dist, pitch, yaw, lift (campus frame; lift = aim height above the ground)
  const K1 = [[0, -30, -60, 640, 0.62, -0.45, 0], [7, -20, -50, 600, 0.66, 0.12, 0], [13, -85, -310, 230, 0.42, 0.24, 0],
    [19, -60, -205, 110, 0.26, 0.24, 0], [23, -48, -140, 40, 0.16, 0.24, 0]];
  // after the walk: back up into the sky, jump to 독수리상 (an arc in front of the eagle, the library behind),
  // jump on to 언더우드 동상 (from the front, Underwood Hall behind), then pull back over the courtyard
  const K2 = [null, [36, -55, -110, 160, 0.8, 0.24, 0], [40, -52, -82, 17, 0.68, -0.85, 10], [46.5, -52, -82, 17, 0.7, -1.85, 10],
    [50, 0, 60, 330, 0.95, -0.4, 0], [54, 49.8, 198.2, 11, 0.22, 0.24, 4.5], [59, 49.8, 198.2, 13, 0.14, -0.15, 4.2],
    [64, 52, 215, 110, 0.42, -0.1, 0], [65, 52, 217, 118, 0.43, -0.12, 0]];
  const ease = (u) => u * u * (3 - 2 * u);
  const at = (K, t) => {
    let i = 0;
    while (i < K.length - 2 && t > K[i + 1][0]) i++;
    const a = K[i], b = K[i + 1];
    const u = ease(Math.min(1, Math.max(0, (t - a[0]) / (b[0] - a[0]))));
    const v = a.map((x, k) => x + (b[k] - x) * u);
    return { x: v[1], y: v[2], dist: v[3], pitch: v[4], yaw: v[5], lift: v[6] };
  };
  y.setSeason('summer');
  await new Promise((r) => setTimeout(r, 2500));
  y.startWalk();
  y.player.keys.clear();
  y.player.teleport(-47, -128, -0.24);          // west sidewalk below the library, facing up 백양로
  y.enterBird();
  B.auto = false;
  y.record.start(1920, 1080);
  let walked = false, left = false, back = false;
  for (let i = 0; i < T * FPS; i++) {
    const t = i / FPS;
    if (t < 23) { const k = at(K1, t); Object.assign(B.goal, k); Object.assign(B.cur, k); }
    else if (!left) { y.leaveBird(); left = true; }
    if (t >= 24.2 && !walked) { y.player.keys.add('KeyW'); walked = true; }
    if (t >= 33 && !back) {
      // up again from exactly where the walking camera is
      y.player.keys.clear();
      const cam = y.camera.position, look = y.player.cam.look;
      const dx = look.x - cam.x, dy = -look.z + cam.z, dz = look.y - cam.y;
      const hor = Math.hypot(dx, dy), dist = Math.hypot(hor, dz);
      K2[0] = [33, look.x, -look.z, dist, Math.max(0.05, Math.asin(-dz / dist)), Math.atan2(dx, dy), 0];
      y.enterBird();
      B.auto = false;
      back = true;
    }
    if (back) { const k = at(K2, t); Object.assign(B.goal, k); Object.assign(B.cur, k); }
    y.record.step(1 / FPS);
    const blob = await new Promise((res) => y.renderer.domElement.toBlob(res, 'image/jpeg', 0.92));
    await fetch('http://127.0.0.1:8765/f/' + String(i).padStart(5, '0'), { method: 'POST', body: blob });
    window.__rec = { n: i, done: false };
  }
  y.player.keys.clear();
  y.record.stop();
  window.__rec = { n: T * FPS - 1, done: true };
  console.log('trailer frames done');
})();
