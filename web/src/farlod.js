// The campus cells from far off (#248). From the gate some 70 % of the halls' and landmarks' draw calls and 1.1 M of
// their 1.7 M triangles were cells more than 400 m away, where a window is a few pixels and a frame or a railing less
// than one (TECH_NOTE 「성능: 로딩 · 게임 중 측정 (2026-11-27)」). Each cell's file gets a stand-in for that distance:
// its opaque meshes (some forty, one a material) as one or two of the plain-colour material (materials.js solid),
// each corner coloured by its material's colour and the mean of its colour texture (roughness and metalness alike),
// made lighter by meshoptimizer within ERR metres (farlod.worker.js). The baked shade, the atmosphere and the baked
// sun shadow come with that material. The transparent and the cut-out ones (ivy, glass doors) stay as they are.
// The walker's walls, the notes' rays and the shadow cache's first pass keep reading the cell's own meshes (hidden
// ones are hit alike); the stand-in casts the static shadow in their place while it is shown.
import * as THREE from 'three';

export const FAR_IN = 420, FAR_OUT = 380;     // m from the camera to the cell's box: the stand-in in past FAR_IN, out again inside FAR_OUT
const ERR = 0.4;                              // m: 400 m off at a phone's or a desktop's view, under a pixel
// window glass (materials.js rooms: a room behind each pane, tinted, the sky over it by Fresnel) as a smooth surface
// of the rooms' mean colour times the tint; glass without rooms as a plain pale grey
const GLASS = { color: [0.24, 0.26, 0.28], rough: 0.15, metal: 0.0 };

let worker = null, seq = 0;
const asked = new Map();
function simplify(msg) {
  if (!worker) {
    worker = new Worker(new URL('./farlod.worker.js', import.meta.url), { type: 'module' });
    worker.onmessage = (e) => {
      const w = asked.get(e.data.id);
      asked.delete(e.data.id);
      if (e.data.error) w.no(new Error(e.data.error)); else w.ok(e.data);
    };
  }
  const id = ++seq;
  return new Promise((ok, no) => {
    asked.set(id, { ok, no });
    const t = [msg.pos.buffer, msg.nrm.buffer, msg.solid.buffer, msg.idx.buffer];
    if (msg.bake) t.push(msg.bake.buffer);
    worker.postMessage({ id, ...msg }, t);
  });
}

// the mean linear colour of a texture's image (8 x 8 drawn down), once a Source; null while its image is not in
const means = new WeakMap();
let cv = null;
const lin = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
function texMean(t) {
  const img = t?.image;
  if (!img || !img.width) return null;
  if (means.has(t.source)) return means.get(t.source);
  cv ||= Object.assign(document.createElement('canvas'), { width: 8, height: 8 });
  const x = cv.getContext('2d', { willReadFrequently: true });
  x.imageSmoothingQuality = 'high';
  x.clearRect(0, 0, 8, 8);
  x.drawImage(img, 0, 0, 8, 8);
  const d = x.getImageData(0, 0, 8, 8).data, srgb = t.colorSpace === THREE.SRGBColorSpace, out = [0, 0, 0];
  for (let i = 0; i < 64; i++) for (let k = 0; k < 3; k++) { const v = d[i * 4 + k] / 255; out[k] += (srgb ? lin(v) : v) / 64; }
  means.set(t.source, out);
  return out;
}

// colour (linear), roughness and metalness of a material as one plain value; null: not one for the stand-in;
// false: a texture it needs is not in yet
function plainOf(m, lib) {
  if (!m.isMeshStandardMaterial || m.userData.wallLeaf || m.alphaTest > 0 || m.alphaMap) return null;
  const d = lib.defs[m.name] || {};
  if (m.name.startsWith('glass')) {
    if (m.transparent && m.opacity < 0.5) return null;
    if (!d.rooms || !m.map) return GLASS;
    const t = texMean(m.map);
    if (!t) return false;
    const tint = d.tint || [1, 1, 1];
    return { color: t.map((v, k) => v * tint[k]), rough: GLASS.rough, metal: 0 };
  }
  if (m.transparent) return null;
  let c = [m.color.r, m.color.g, m.color.b];
  if (m.map) {
    const t = texMean(m.map);
    if (!t) return false;
    let s = [...t];
    const lum = 0.299 * s[0] + 0.587 * s[1] + 0.114 * s[2];
    if (d.recolor) { const g = lib.uniforms.uGrass.value; s = [g.r, g.g, g.b].map((v) => v * (0.45 + 1.6 * lum)); c = [1, 1, 1]; }
    else if (d.sat !== undefined) s = s.map((v) => lum + (v - lum) * d.sat);
    c = c.map((v, k) => v * s[k]);
  }
  let rough = m.roughness, metal = m.metalness;
  if (m.roughnessMap) { const t = texMean(m.roughnessMap); if (!t) return false; rough *= t[1]; }
  if (m.metalnessMap) { const t = texMean(m.metalnessMap); if (!t) return false; metal *= t[2]; }
  return { color: c, rough, metal };
}

// The stand-in of a cell's meshes: { group, shown: the meshes it stands for } or null (nothing to stand for);
// throws 'later' while a texture is still coming
export async function cellStandIn(meshes, lib, name) {
  const sets = { plain: [], baked: [] };
  const shown = [];
  for (const o of meshes) {
    const g = o.geometry, m = o.material;
    let plain = null;
    if (m.name === 'solid' && g.attributes.solid) plain = 'attr';
    else {
      plain = plainOf(m, lib);
      if (plain === false) throw new Error('later');
    }
    if (!plain) continue;
    sets[m.userData.baked ? 'baked' : 'plain'].push({ g, plain });
    shown.push(o);
  }
  if (!shown.length) return null;
  const group = new THREE.Group();
  group.name = 'far:' + name;
  group.visible = false;
  for (const [kind, list] of Object.entries(sets)) {
    if (!list.length) continue;
    let nv = 0, ni = 0;
    for (const { g } of list) { nv += g.attributes.position.count; ni += g.index ? g.index.count : g.attributes.position.count; }
    const pos = new Float32Array(nv * 3), nrm = new Float32Array(nv * 3), solid = new Uint16Array(nv * 4);
    const bake = kind === 'baked' ? new Uint16Array(nv * 4).fill(65535) : null, idx = new Uint32Array(ni);
    let v0 = 0, i0 = 0;
    for (const { g, plain } of list) {
      const n = g.attributes.position.count, P = g.attributes.position, N = g.attributes.normal;
      for (let i = 0; i < n; i++) {
        pos[(v0 + i) * 3] = P.getX(i); pos[(v0 + i) * 3 + 1] = P.getY(i); pos[(v0 + i) * 3 + 2] = P.getZ(i);
        if (N) { nrm[(v0 + i) * 3] = N.getX(i); nrm[(v0 + i) * 3 + 1] = N.getY(i); nrm[(v0 + i) * 3 + 2] = N.getZ(i); }
      }
      if (plain === 'attr') solid.set(g.attributes.solid.array.subarray(0, n * 4), v0 * 4);
      else {
        const r = Math.round(Math.min(plain.color[0], 1) * 65535), gg = Math.round(Math.min(plain.color[1], 1) * 65535);
        const b = Math.round(Math.min(plain.color[2], 1) * 65535);
        const rm = Math.round(Math.min(plain.rough, 1) * 255) * 256 + Math.round(Math.min(plain.metal, 1) * 255);
        for (let i = 0; i < n; i++) { const k = (v0 + i) * 4; solid[k] = r; solid[k + 1] = gg; solid[k + 2] = b; solid[k + 3] = rm; }
      }
      const B = g.attributes.bake;
      if (bake && B) {
        if (B.array instanceof Uint16Array && B.itemSize === 4) bake.set(B.array.subarray(0, n * 4), v0 * 4);
        else for (let i = 0; i < n; i++) for (let c = 0; c < Math.min(4, B.itemSize); c++) bake[(v0 + i) * 4 + c] = Math.round(B.getComponent(i, c) * 65535);
      }
      if (g.index) { const I = g.index.array; for (let i = 0; i < I.length; i++) idx[i0 + i] = I[i] + v0; i0 += I.length; }
      else { for (let i = 0; i < n; i++) idx[i0 + i] = v0 + i; i0 += n; }
      v0 += n;
    }
    const r = await simplify({ pos, nrm, solid, bake, idx, err: ERR });
    if (!r.idx.length) continue;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(r.pos, 3));
    geo.setAttribute('normal', new THREE.BufferAttribute(r.nrm, 3));
    geo.setAttribute('solid', new THREE.BufferAttribute(r.solid, 4, true));
    if (r.bake) geo.setAttribute('bake', new THREE.BufferAttribute(r.bake, 4, true));
    geo.setIndex(new THREE.BufferAttribute(r.idx, 1));
    geo.computeBoundingSphere();
    const mesh = new THREE.Mesh(geo, lib.solid(kind === 'baked'));
    mesh.name = `far|${kind}|${name}`;
    mesh.castShadow = mesh.receiveShadow = true;
    group.add(mesh);
  }
  return group.children.length ? { group, shown } : null;
}
