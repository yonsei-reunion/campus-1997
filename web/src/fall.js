// Falling petals and leaves (issue #41): April's cherry petals and October's ginkgo and other broadleaf leaves coming
// down through the air round the camera, over the carpet litter.js lays on the ground. One InstancedMesh of small
// cards; the cards of the CELL-sized cells round the camera are copied in again whenever it has moved MOVE metres
// (as grass.js does). Where they come down follows the carpet itself: ground_leaves.png (R ginkgo, G cherry, B the
// other broadleaves, litter.js FALL weighs the month's layers), read once on the CPU and drawn from per cell; each card
// lets go upwind of that spot by about the distance the wind carries it while it falls, so the air above the carpet
// carries what lies on it. May has none.
// The vertex shader moves every card as a function of time (the wind clock, materials.js windTime): it falls, swings
// across the trees' wind (windSway's direction) or spirals, tilts or tumbles, and drifts downwind under the trees'
// gust swell, more of them letting go in a gust. It comes down on the walked surface (the terrain and the terraces on
// it: the baked heights of bakedshadow.js, uSunGround + uSunLift), lies there a moment and starts again from the top,
// a little off its last spot. The cards are lit as standard materials (the sun's shadow map on the desktop, the baked
// ground shadow under them on phones), take the clouds and fog, and cast no shadow. Phones: a quarter of the cards in a
// smaller ring.
// A card stays a few pixels across however far it is (turning to the view once it is drawn larger than life), and
// writes alpha 0 into the frame: the desktop's TAA (post.js) has no motion vectors and would otherwise fade a speck
// this small and quick into the history behind it; there it takes the new frame instead.
import * as THREE from 'three';
import { patchShader, pcss, globalPatch, windTime } from './materials.js';
import { FALL } from './litter.js';
import { MOBILE, mulberry, versioned } from './util.js';

const R = MOBILE ? 12 : 20;            // radius round the camera, m
const CELL = 4;                        // the refill grid, m
const CAP = MOBILE ? 300 : 1200;
const DENSITY = MOBILE ? 1.6 : 2.4;    // cards per m² of ground under a full carpet (a share of them in the air)
const MOVE = 2;                        // refill once the camera has moved this far
const BACK = 5;                        // farthest a card lets go upwind of where it lands, m
const REST = 1.0;                      // a fall lasts (H + REST) / speed: it lies on the ground for the last bit
const JITTER = 1.6;                    // each fall starts this far (square) round the card's spot
const MIN_PX = 5.0;                    // a far card stays this many pixels across
const DIR = [0.92, -0.38];             // downwind, three XZ (materials.js windSway)

// per kind (0 cherry petal, 1 ginkgo leaf, 2 the other broadleaves): metres above the ground it lets go at, fall
// speed m/s, drift with the wind m/s (times the gust swell), card size m, swing across the wind m and its rate rad/s,
// along / across share of the swing (1: a spiral), the atlas cell(s), colours (sRGB)
const KINDS = [
  { h: [2.4, 5.6], v: [0.7, 1.1], w: 0.55, size: [0.026, 0.034], amp: 0.22, om: 2.4, along: 0.9,
    pal: [[246, 206, 218], [248, 216, 226], [250, 226, 233], [244, 198, 212], [252, 236, 240], [240, 190, 205], [247, 222, 228]] },
  { h: [3.0, 9.5], v: [0.9, 1.4], w: 0.4, size: [0.055, 0.075], amp: 0.45, om: 1.7, along: 0.3,
    pal: [[240, 200, 40], [230, 185, 30], [250, 215, 70], [215, 170, 30], [200, 180, 50], [236, 196, 52], [190, 150, 40]] },
  { h: [4.0, 11.0], v: [1.0, 1.5], w: 0.45, size: [0.06, 0.09], amp: 0.4, om: 1.5, along: 0.35,
    // the zelkovas', oaks' and cherries' rust-brown, a maple's red now and then, a few yellow-brown
    pal: [[176, 98, 48], [160, 88, 46], [192, 118, 58], [142, 78, 42], [200, 124, 52], [176, 98, 48], [190, 62, 40],
      [168, 48, 36], [184, 142, 62]] },
];
const f3 = (v) => v.toFixed(3);
const K3 = (k) => `vec3(${f3(KINDS[0][k])}, ${f3(KINDS[1][k])}, ${f3(KINDS[2][k])})`;
const K3r = (k, i) => `vec3(${f3(KINDS[0][k][i])}, ${f3(KINDS[1][k][i])}, ${f3(KINDS[2][k][i])})`;

// The cards' atlas: four 64 px cells, two petals (one curled, narrower), a ginkgo leaf, an ovate serrated leaf, drawn
// near white (the instance colour tints them) with the pink claw, the fold and the veins of tools/make_textures.py's
// litter tiles. Colour is spread into the transparent texels so the edges have no dark fringe.
function leafAtlas() {
  const C = 64, W = C * 4;
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = C;
  const g = cv.getContext('2d', { willReadFrequently: true });
  // shapes in leaf units, base at the origin, tip towards -y; fitted into their cell
  const fitter = (cell, pts) => {
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    for (const [x, y] of pts) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    const s = 0.88 * C / Math.max(x1 - x0, y1 - y0), cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    return ([x, y]) => [cell * C + C / 2 + (x - cx) * s, C / 2 + (y - cy) * s];
  };
  const poly = (map, pts, fill) => {
    g.beginPath();
    pts.forEach((p, i) => { const [x, y] = map(p); if (i) g.lineTo(x, y); else g.moveTo(x, y); });
    g.closePath();
    g.fillStyle = fill;
    g.fill();
  };
  const line = (map, a, b, col, w) => {
    g.beginPath();
    g.moveTo(...map(a)); g.lineTo(...map(b));
    g.strokeStyle = col; g.lineWidth = w; g.stroke();
  };
  // petals (make_textures.py shape_petal): widest two thirds out, the rounded tip notched
  const petal = (cell, wk) => {
    const w = 0.42 * wk, notch = 0.1, right = [];
    for (let i = 0; i <= 36; i++) {
      const t = i / 36;
      let x = t < 0.66 ? w * Math.pow(t / 0.66, 0.65) : w * Math.sqrt(Math.max(0, 1 - ((t - 0.66) / 0.34) ** 2));
      let y = -t;
      if (t > 0.8) y += notch * Math.max(0, 1 - x / (0.35 * w));
      right.push([x, y]);
    }
    const pts = [...right, ...right.slice(1).reverse().map(([x, y]) => [-x, y])];
    const map = fitter(cell, pts);
    poly(map, pts, '#fff');
    poly(map, [[0, 0], ...right.filter(([x]) => x > 0), [0, -1]], 'rgb(243,243,243)');     // one half curls
    poly(map, pts.map(([x, y]) => [x * 0.65, y * 0.5]), 'rgb(250,232,238)');             // the claw, pinker
    poly(map, pts.map(([x, y]) => [x * 0.36, y * 0.28]), 'rgb(245,211,222)');
    g.lineWidth = 1; g.strokeStyle = 'rgb(222,222,222)';
    g.beginPath(); pts.forEach((p, i) => { const [x, y] = map(p); if (i) g.lineTo(x, y); else g.moveTo(x, y); }); g.closePath(); g.stroke();
  };
  petal(0, 1.0);
  petal(1, 0.66);
  // ginkgo (shape_ginkgo): a fan notched in the middle on a short stem, fine veins fanning out
  {
    const spread = 65 * Math.PI / 180, arc = [];
    for (let i = 0; i <= 24; i++) {
      const a = -Math.PI / 2 - spread + 2 * spread * i / 24;
      const rr = (1 - 0.18 * Math.exp(-(((i - 12) / 1.6) ** 2))) * (1 + 0.03 * Math.sin(i * 2.3));
      arc.push([rr * Math.cos(a) * 0.95, rr * Math.sin(a) * 0.95 - 0.35]);
    }
    const pts = [[0, 0], ...arc];
    const map = fitter(2, [...pts, [0, 0.35]]);
    poly(map, pts, 'rgb(250,250,250)');
    poly(map, [[0, 0], ...arc.slice(12)], 'rgb(228,228,228)');                          // the far half a shade darker
    for (let i = 1; i < 24; i += 2) line(map, [0, -0.05], [arc[i][0] * 0.94, -0.35 + (arc[i][1] + 0.35) * 0.94], 'rgba(190,190,190,0.55)', 0.7);
    line(map, [0, 0], [0, 0.35], 'rgb(120,105,70)', 1.6);
  }
  // the other broadleaves (shape_ovate, serrated): a pointed oval with a midrib, the fold a shade darker
  {
    const right = [];
    for (let i = 0; i <= 34; i++) {
      const t = i / 34;
      let x = 0.42 * Math.sin(Math.PI * Math.pow(t, 0.85)) * (1 - 0.15 * t);
      if (i % 2) x *= 1.08;
      right.push([x, -t]);
    }
    const pts = [...right, ...right.slice(1).reverse().map(([x, y]) => [-x, y])];
    const map = fitter(3, [...pts, [0, 0.12]]);
    poly(map, pts, 'rgb(236,236,236)');
    poly(map, [...right, [0, -1]], 'rgb(204,204,204)');
    for (let k = 1; k <= 5; k++) {
      const t = k / 6.5;
      line(map, [0, -t], [0.3, -t - 0.16], 'rgba(170,170,170,0.6)', 0.7);
      line(map, [0, -t], [-0.3, -t - 0.16], 'rgba(255,255,255,0.6)', 0.7);
    }
    line(map, [0, 0.12], [0, -0.88], 'rgb(255,255,255)', 1.2);
    line(map, [0, 0.12], [0, 0], 'rgb(110,90,60)', 1.6);
  }
  // spread the colour into the clear texels (a few rings), then a texture with mipmaps
  const img = g.getImageData(0, 0, W, C), d = img.data;
  for (let pass = 0; pass < 4; pass++) {
    const src = d.slice();
    for (let y = 0; y < C; y++) {
      for (let x = 0; x < W; x++) {
        const o = (y * W + x) * 4;
        if (src[o + 3] > 8) continue;
        let r = 0, gg = 0, b = 0, n = 0;
        for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
          const xx = x + i, yy = y + j;
          if (xx < 0 || yy < 0 || xx >= W || yy >= C || ((xx / C) | 0) !== ((x / C) | 0)) continue;
          const q = (yy * W + xx) * 4;
          if (src[q + 3] > 8) { r += src[q]; gg += src[q + 1]; b += src[q + 2]; n++; }
        }
        if (n) { d[o] = r / n; d[o + 1] = gg / n; d[o + 2] = b / n; d[o + 3] = 1; }
      }
    }
  }
  for (let k = 3; k < d.length; k += 4) if (d[k] === 1) d[k] = 0;
  const t = new THREE.DataTexture(new Uint8Array(d.buffer.slice(0)), W, C, THREE.RGBAFormat, THREE.UnsignedByteType);
  t.colorSpace = THREE.SRGBColorSpace;
  t.magFilter = THREE.LinearFilter;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.generateMipmaps = true;
  t.needsUpdate = true;
  return t;
}

const FALL_GLSL = /* glsl */`
  attribute vec4 aSpot;        // where it lets go (three x, z), how high above the ground there, rank
  attribute vec4 aFall;        // phase (0..1), fall speed m/s, kind, seed
  uniform float uWindT, uPx;
  uniform sampler2D uSunGround, uSunLift;
  uniform vec4 uSunRect;
  uniform vec3 uSunGroundF;
  const vec2 FALL_DIR = vec2(${f3(DIR[0])}, ${f3(DIR[1])});
  vec4 fallHash(vec2 p) {
    vec4 p4 = fract(p.xyxy * vec4(0.1031, 0.1030, 0.0973, 0.1099));
    p4 += dot(p4, p4.wzxy + 33.33);
    return fract((p4.xxyz + p4.yzzw) * p4.zywx);
  }
  // the walked surface at q (three x, z): the terrain and the terraces, plinths and flights on it (bakedshadow.js)
  float fallGround(vec2 q) {
    vec2 p = vec2(q.x, -q.y);
    vec2 r = vec2((p.x - uSunRect.x) / (uSunRect.z - uSunRect.x), (uSunRect.w - p.y) / (uSunRect.w - uSunRect.y));
    return textureLod(uSunGround, ((p + uSunGroundF.x) / uSunGroundF.y + 0.5) / uSunGroundF.z, 0.0).r
         + textureLod(uSunLift, r, 0.0).r * 12.75;
  }
  // where a fall from a is after tau seconds: drifting downwind, swinging across the wind (sw: across, along, rate,
  // phase; along = across makes a spiral)
  vec2 fallXZ(vec2 a, vec2 drift, vec4 sw, float tau) {
    float s = sw.z * tau + sw.w;
    return a + drift * tau + vec2(-FALL_DIR.y, FALL_DIR.x) * (sw.x * sin(s)) + FALL_DIR * (sw.y * cos(s));
  }
  mat3 fallRx(float a) { float c = cos(a), s = sin(a); return mat3(1.0, 0.0, 0.0, 0.0, c, s, 0.0, -s, c); }
  mat3 fallRy(float a) { float c = cos(a), s = sin(a); return mat3(c, 0.0, -s, 0.0, 1.0, 0.0, s, 0.0, c); }
  mat3 fallRz(float a) { float c = cos(a), s = sin(a); return mat3(c, s, 0.0, -s, c, 0.0, 0.0, 0.0, 1.0); }`;

const FALL_MAIN = /* glsl */`
  vec3 fallP = vec3(0.0);
  mat3 fallM = mat3(1.0);
  float fallS = 0.0;
  {
    int kind = int(aFall.z + 0.5);
    float H = aSpot.z, v = aFall.y;
    vec4 k = fallHash(vec2(aFall.w * 311.0, 17.0));           // the card's own draw
    vec4 k2 = fallHash(vec2(aFall.w * 97.0, 3.0));
    float P = (H + ${f3(REST)}) / v;                           // one fall and a moment on the ground
    float cyc = uWindT / P + aFall.x;
    float c = floor(cyc), tau = fract(cyc) * P;
    vec4 h = fallHash(vec2(aFall.w * 173.0, c));              // this fall's draw
    vec2 a = aSpot.xy + (h.xy - 0.5) * ${f3(JITTER)};
    // the trees' gust swell (materials.js windSway) when it let go: more of them let go in a gust
    float gust = 0.7 + 0.3 * sin((c - aFall.x) * P * 0.21 - dot(a, FALL_DIR) * 0.01);
    if (h.z < 0.55 + 0.45 * smoothstep(0.5, 0.95, gust)) {
      vec3 sel = vec3(equal(ivec3(kind), ivec3(0, 1, 2)));
      float om = dot(sel, ${K3('om')}) * (0.8 + 0.45 * k.y);
      float amp = dot(sel, ${K3('amp')}) * (0.6 + 0.8 * k.z);
      vec4 sw = vec4(amp * (k.w < 0.5 ? 1.0 : -1.0), amp * dot(sel, ${K3('along')}), om, h.w * 6.2832);
      vec2 drift = FALL_DIR * (dot(sel, ${K3('w')}) * gust * (0.8 + 0.4 * k.x));
      float gA = fallGround(a);
      vec2 xz = fallXZ(a, drift, sw, tau);
      float y = gA + H - v * tau + 0.12 * amp * cos(2.0 * (om * tau + sw.w));   // a swing lifts it at either end
      float gN = fallGround(xz), above = y - gN;
      float tl = tau;
      if (above < 0.0) {
        // down: where it met the ground (two steps along the fall), lying flat
        tl = (H + gA - gN) / v;
        xz = fallXZ(a, drift, sw, tl);
        tl = (H + gA - fallGround(xz)) / v;
        xz = fallXZ(a, drift, sw, tl);
        y = fallGround(xz) + 0.012;
        above = 0.0;
      }
      // a petal tumbles; a leaf rocks with its swing, a few of them tumbling too; all turn slowly about the vertical
      float s = om * tl + sw.w;
      float tumble = kind == 0 ? 1.0 : step(k2.z, 0.3);
      float tilt = mix(0.8 * cos(s) * sign(sw.x), (3.0 + 4.0 * k2.w) * (k2.x < 0.5 ? 1.0 : -1.0) * tl, tumble);
      float roll = mix(0.3 * sin(2.0 * s), (2.0 + 2.0 * k2.y) * tl, tumble * (kind == 0 ? 1.0 : 0.35));
      // settling: the nearest flat pose over the last few decimetres
      float fl = smoothstep(0.0, 0.35, above);
      tilt = mix(floor(tilt / 3.14159 + 0.5) * 3.14159, tilt, fl);
      roll = mix(floor(roll / 3.14159 + 0.5) * 3.14159, roll, fl);
      fallM = fallRy(k2.x * 6.2832 + (k2.y - 0.5) * 2.5 * tl) * fallRx(tilt) * fallRz(roll) * fallRx(-1.5708);
      fallP = vec3(xz.x, y, xz.y);
      float camD = distance(fallP, cameraPosition);
      float size = mix(dot(sel, ${K3r('size', 0)}), dot(sel, ${K3r('size', 1)}), k2.w);
      // never thinner than a few pixels; drawn larger than life, a card in the air turns mostly to the view (seen
      // edge-on, a speck that small would vanish), still spinning in its own plane
      float minS = ${f3(MIN_PX)} * uPx * camD;
      float bill = smoothstep(1.0, 2.5, minS / size) * 0.8 * fl;
      if (bill > 0.0) {
        vec3 n = normalize(cameraPosition - fallP), rt = cross(vec3(0.0, 1.0, 0.0), n);
        rt = dot(rt, rt) > 1e-6 ? normalize(rt) : vec3(1.0, 0.0, 0.0);
        vec3 up = cross(n, rt);
        float cr = cos(roll + tilt), sr = sin(roll + tilt);
        fallM = mat3(mix(fallM[0], rt * cr + up * sr, bill), mix(fallM[1], up * cr - rt * sr, bill), mix(fallM[2], n, bill));
      }
      fallS = max(size, minS)
            * smoothstep(0.0, 0.6, tau) * (1.0 - smoothstep(P - 0.5, P, tau))   // grows in the crown, goes on the ground
            * smoothstep(0.35, 0.9, camD)                                    // none in the camera's lens
            * step(aSpot.w, 1.0 - smoothstep(${f3(0.7 * R)}, ${f3(R)}, camD));   // thinning out by rank at the edge
      #ifdef USE_MAP
        vMapUv = (vMapUv + vec2(kind == 0 ? step(0.6, k.x) : float(kind + 1), 0.0)) * vec2(0.25, 1.0);
      #endif
    }
  }`;

async function pixels(url, w, h, draw) {
  const img = await createImageBitmap(await (await fetch(versioned(url))).blob());
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const x = c.getContext('2d', { willReadFrequently: true });
  x.drawImage(img, 0, 0, w, h);
  draw?.(x);
  img.close?.();
  return x.getImageData(0, 0, w, h).data;
}

export class Fall {
  constructor(renderer, scene, lib, hf, campus, sunMap) {
    this.renderer = renderer;
    this.hf = hf;
    this.season = lib.season;
    this.enabled = true;
    const S = this.rect = campus.splat;
    this.w = Math.round(S.x1 - S.x0);                // ground_leaves.png: the splat's rectangle at 1 m
    this.h = Math.round(S.y1 - S.y0);
    this.mask = null;
    this.cells = new Map();
    this.last = new THREE.Vector3(1e9, 0, 0);
    this.order = [];                                 // cell offsets round the camera's cell, nearest first
    const span = Math.ceil((R + MOVE + BACK) / CELL) + 1;
    for (let j = -span; j <= span; j++) for (let i = -span; i <= span; i++) this.order.push([i, j, Math.hypot(i, j)]);
    this.order.sort((a, b) => a[2] - b[2]);

    const su = sunMap.uniforms;
    this.uniforms = { uWindT: windTime, uPx: { value: 0.001 },
      uSunGround: su.uSunGround, uSunLift: su.uSunLift, uSunRect: su.uSunRect, uSunGroundF: su.uSunGroundF };
    const mat = this.material = new THREE.MeshStandardMaterial({
      map: leafAtlas(), alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.75, metalness: 0,
    });
    mat.name = 'fall';
    pcss(mat);
    patchShader(mat, 'fall', (sh) => {
      Object.assign(sh.uniforms, this.uniforms);
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', `#include <common>\n${FALL_GLSL}`)
        .replace('#include <beginnormal_vertex>', `${FALL_MAIN}\n#include <beginnormal_vertex>\nobjectNormal = fallM * objectNormal;`)
        .replace('#include <begin_vertex>', '#include <begin_vertex>\ntransformed = fallP + fallM * (transformed * fallS);');
      sh.fragmentShader = sh.fragmentShader
        // the atlas read no coarser than a few texels a pixel: a far card keeps its leaf instead of fading under the
        // alpha test in the small mip levels
        .replace('#include <map_fragment>', `#ifdef USE_MAP
          vec2 fallDx = dFdx(vMapUv), fallDy = dFdy(vMapUv);
          float fallK = min(1.0, 3.0 / max(max(length(fallDx * vec2(256.0, 64.0)), length(fallDy * vec2(256.0, 64.0))), 1e-6));
          diffuseColor *= textureGrad(map, vMapUv, fallDx * fallK, fallDy * fallK);
          #endif`)
        // thin, and in the open air on every side: the light through it and the sky round it keep it brighter than
        // the shaded ground it falls past (in the shade under a crown, a lit petal against the petals lying there)
        .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += diffuseColor.rgb * 0.3;')
        // marked for the TAA (post.js): a speck this small and quick would fade into the history behind it
        .replace('#include <dithering_fragment>', '#include <dithering_fragment>\ngl_FragColor.a = 0.0;');
    });
    sunMap.patch(mat, 0);          // the baked sun shadow on the ground under the card (phones' only one)
    globalPatch(mat);

    const geo = new THREE.PlaneGeometry(1, 1);
    this.spot = new THREE.InstancedBufferAttribute(new Float32Array(CAP * 4), 4);
    this.fall = new THREE.InstancedBufferAttribute(new Float32Array(CAP * 4), 4);
    for (const a of [this.spot, this.fall]) a.setUsage(THREE.DynamicDrawUsage);
    geo.setAttribute('aSpot', this.spot);
    geo.setAttribute('aFall', this.fall);
    const im = this.mesh = new THREE.InstancedMesh(geo, mat, CAP);   // (the instance matrices stay identity)
    im.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(CAP * 3), 3);
    im.instanceColor.setUsage(THREE.DynamicDrawUsage);
    im.count = 0;
    im.frustumCulled = false;
    im.castShadow = false;
    im.receiveShadow = true;
    im.visible = false;
    im.name = 'fall';
    im.userData.fall = this;
    scene.add(im);
    this.ready = this._load(campus).catch((e) => console.warn('fall:', e));
  }

  async _load(campus) {
    const S = this.rect;
    // nothing comes down inside the buildings: their footprints painted out
    this.mask = await pixels('assets/textures/ground_leaves.png', this.w, this.h, (x) => {
      x.fillStyle = '#000';
      for (const b of campus.buildings) {
        x.beginPath();
        b.footprint.forEach(([px, py], k) => { if (k) x.lineTo(px - S.x0, S.y1 - py); else x.moveTo(px - S.x0, S.y1 - py); });
        x.fill();
      }
    });
    this.last.set(1e9, 0, 0);
  }

  // the month's layers (main.js setSeason)
  setSeason(season) {
    this.season = season;
    this.cells.clear();
    this.last.set(1e9, 0, 0);
  }

  // the cards of one cell (campus cell i, j; by where they land), made once a month
  _cell(i, j) {
    const key = (i + 4096) * 8192 + (j + 4096);
    let c = this.cells.get(key);
    if (c) return c;
    if (this.cells.size > 2000) this.cells.clear();
    const rnd = mulberry((i * 73856093) ^ (j * 19349663) ^ 41);
    const f = FALL[this.season], S = this.rect, m = this.mask;
    const tries = Math.round(DENSITY * CELL * CELL);
    const spot = new Float32Array(tries * 4), fall = new Float32Array(tries * 4), col = new Float32Array(tries * 3);
    const land = new Float32Array(tries * 2);
    const tmp = this._c ||= new THREE.Color();
    let n = 0;
    for (let k = 0; k < tries; k++) {
      const x = (i + rnd()) * CELL, y = (j + rnd()) * CELL, pick = rnd(), u = rnd();
      const px = Math.floor(x - S.x0), py = Math.floor(S.y1 - y);
      if (px < 0 || py < 0 || px >= this.w || py >= this.h) continue;
      const o = (py * this.w + px) * 4;
      const wg = m[o] / 255 * f[0], wc = m[o + 1] / 255 * f[1], wb = m[o + 2] / 255 * f[2];
      const sum = wg + wc + wb;
      if (pick >= Math.min(1, sum)) continue;
      const kind = u * sum < wc ? 0 : u * sum < wc + wg ? 1 : 2, K = KINDS[kind];
      // from high up only where the carpet is thick (under the crown); where it thins out they come from lower down
      const thick = m[o + [1, 0, 2][kind]] / 255;               // (G cherry, R ginkgo, B the others)
      const H = K.h[0] + rnd() * (K.h[1] - K.h[0]) * (0.35 + 0.65 * thick), v = K.v[0] + rnd() * (K.v[1] - K.v[0]);
      // it lets go upwind of where it lands, by about how far the wind takes it while it falls (gust swell ~0.85)
      const back = Math.min(BACK, K.w * 0.85 * H / v);
      spot.set([x - DIR[0] * back, -y - DIR[1] * back, H, rnd()], n * 4);
      fall.set([rnd(), v, kind, rnd()], n * 4);
      const p = K.pal[Math.floor(rnd() * K.pal.length)], jt = 0.94 + rnd() * 0.1;
      tmp.setRGB(p[0] / 255 * jt, p[1] / 255 * jt, p[2] / 255 * jt, THREE.SRGBColorSpace);
      col.set([tmp.r, tmp.g, tmp.b], n * 3);
      land[n * 2] = x; land[n * 2 + 1] = -y;
      n++;
    }
    c = { n, spot, fall, col, land };
    this.cells.set(key, c);
    return c;
  }

  _refill(cx, cz) {
    const ds = this.spot.array, df = this.fall.array, dc = this.mesh.instanceColor.array;
    const ci = Math.floor(cx / CELL), cj = Math.floor(-cz / CELL);
    const reach = R + MOVE + BACK;
    let count = 0;
    for (const [oi, oj, d] of this.order) {
      if ((d - 1) * CELL > reach) break;
      const c = this._cell(ci + oi, cj + oj);
      for (let k = 0; k < c.n && count < CAP; k++) {
        const dx = c.land[k * 2] - cx, dz = c.land[k * 2 + 1] - cz;
        if (dx * dx + dz * dz > reach * reach) continue;
        for (let e = 0; e < 4; e++) { ds[count * 4 + e] = c.spot[k * 4 + e]; df[count * 4 + e] = c.fall[k * 4 + e]; }
        for (let e = 0; e < 3; e++) dc[count * 3 + e] = c.col[k * 3 + e];
        count++;
      }
      if (count >= CAP) break;
    }
    this.mesh.count = count;
    for (const [a, w] of [[this.spot, 4], [this.fall, 4], [this.mesh.instanceColor, 3]]) {
      a.clearUpdateRanges();
      a.addUpdateRange(0, count * w);
      a.needsUpdate = true;
    }
  }

  // once a frame: camera, the view's pixel size, the refill
  update(cam) {
    const p = cam.position;
    // high above the ground (the bird's-eye view) the cards would be specks; none in May
    const on = this.enabled && !!this.mask && FALL[this.season].some((v) => v > 0) && p.y - this.hf.height(p.x, -p.z) < 30;
    if (!on) { this.mesh.visible = false; return; }
    this.uniforms.uPx.value = 2 * Math.tan(cam.fov * Math.PI / 360) / Math.max(1, this.renderer.domElement.height);
    const dx = p.x - this.last.x, dz = p.z - this.last.z;
    if (dx * dx + dz * dz >= MOVE * MOVE) {
      this.last.copy(p);
      this._refill(p.x, p.z);
    }
    this.mesh.visible = this.mesh.count > 0;
  }
}
