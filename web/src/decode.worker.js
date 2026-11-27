// Textures fetched and decoded off the page's main thread (materials.js imageTexture). Decoding a blob there waits for
// the main thread to read it in: while the loading's long steps held it (~2 s on a desktop, 2026-11-27), the images
// that had come down stood still, and the start waited for their decoding after. Here the reading and decoding go on
// meanwhile; the main thread only takes up each finished ImageBitmap (transferred).
// in: { id, url (absolute), opts (createImageBitmap's), max (longest side) }; out: { id, img } or { id, error }
self.onmessage = async ({ data: { id, url, opts, max } }) => {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    let img = await createImageBitmap(await r.blob(), opts);
    if (Math.max(img.width, img.height) > max) {
      const s = max / Math.max(img.width, img.height);
      const small = await createImageBitmap(img, { resizeWidth: Math.max(1, Math.round(img.width * s)),
        resizeHeight: Math.max(1, Math.round(img.height * s)), resizeQuality: 'high' });
      img.close();
      img = small;
    }
    self.postMessage({ id, img }, [img]);
  } catch (e) {
    self.postMessage({ id, error: String(e?.message ?? e) });
  }
};
