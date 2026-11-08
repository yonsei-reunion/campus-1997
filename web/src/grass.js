// Grass blades (issue #25): within R of the camera, clumps of blades stand on the lawns so the ground round the
// walker has some depth instead of looking like a flat photo. One InstancedMesh; the clumps of the CELL-sized cells
// round the camera are copied in again whenever it has moved MOVE metres (as the Forest re-commits its trees).
// Where they stand comes from the maps the terrain shader paints with: ground_splat.png's grass share (building
// footprints taken out) and ground_dry.png, where the worn lawn grows thin. Each clump takes its colour from the
// ground under it, computed as terrain.js does (season uGrass, dry lawn's straw, bare earth), so the blades melt into
// the painted lawn. They are lit as the lawn is: every blade faces up like the ground, so its light is the scene's
// sky / environment light for an upward face plus the sun times its shadow, measured once from the scene's own lights
// (calibrate) and applied per vertex. The sun's shadow map is read at each vertex; the blades cast no shadow and
// are not in the shadow pass, and the fragment shader only fogs a colour: blades cost vertices, hardly any shading.
// Farther clumps thin out one by one (a per-clump dither by rank).
import * as THREE from 'three';
import { loadTex } from './materials.js';
import { MOBILE, mulberry, versioned } from './util.js';

const R = MOBILE ? 18 : 25;          // radius round the camera, m
const CELL = 4;                      // the refill grid, m
const DENSITY = MOBILE ? 3.5 : 15;   // clumps per m² near the camera on a full lawn (CAP: about 1300 m² of it)
const CAP = MOBILE ? 3000 : 20000;
const NEAR = 6;                      // full density within this, thinning to FAR_KEEP at R
const FAR_KEEP = 0.3;
const MOVE = 2;                      // refill once the camera has moved this far
const BLADES = 12;                   // per clump

// share of the clumps kept at distance d (by rank): the same in the vertex shader (KEEP_GLSL)
function keep(d) {
  const t = Math.min(1, Math.max(0, (d - NEAR) / (R - NEAR)));
  const e = Math.min(1, Math.max(0, (d - 0.8 * R) / (0.2 * R)));
  return (1 - (1 - FAR_KEEP) * t) * (1 - e * e * (3 - 2 * e));
}
const KEEP_GLSL = `
  float grassKeep(float d) {
    float t = clamp((d - ${NEAR.toFixed(1)}) / ${(R - NEAR).toFixed(1)}, 0.0, 1.0);
    return (1.0 - ${(1 - FAR_KEEP).toFixed(2)} * t) * (1.0 - smoothstep(${(0.8 * R).toFixed(1)}, ${R.toFixed(1)}, d));
  }`;

// one clump: thin triangles round its foot leaning outward, 7-13 cm tall. aBlade: x the blade's tone, y 0 at the
// foot, 1 at the tip.
function clumpGeometry() {
  const rnd = mulberry(25);
  const pos = [], bl = [];
  for (let b = 0; b < BLADES; b++) {
    const a = rnd() * Math.PI * 2, r = Math.sqrt(rnd()) * 0.11;
    const cx = Math.cos(a) * r, cz = Math.sin(a) * r;
    const face = rnd() * Math.PI, w = 0.006 + rnd() * 0.005;
    const h = 0.07 + rnd() * 0.06, lean = (0.15 + rnd() * 0.45) * h, la = a + (rnd() - 0.5) * 1.4;
    const fx = Math.cos(face) * w, fz = Math.sin(face) * w;
    pos.push(cx - fx, 0, cz - fz, cx + fx, 0, cz + fz, cx + Math.cos(la) * lean, h, cz + Math.sin(la) * lean);
    const tone = 0.85 + rnd() * 0.3;
    bl.push(tone, 0, tone, 0, tone, 1);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('aBlade', new THREE.Float32BufferAttribute(bl, 2));
  return g;
}

// The light an upward-facing patch of lawn gets, per unit albedo, in the scene's lighting: amb (sky, environment)
// and sun (the directional light, unshadowed). A white MeshStandardMaterial ground, seen at a third-person angle,
// drawn without and with the directional lights into a float target (linear, not tone mapped) and read back.
function calibrate(renderer, scene, roughness) {
  if (!renderer.extensions.has('EXT_color_buffer_float')) return null;   // (no float target: keep the defaults)
  const cal = new THREE.Scene();
  cal.environment = scene.environment;
  cal.environmentIntensity = scene.environmentIntensity;
  cal.environmentRotation.copy(scene.environmentRotation);
  const dirs = [];
  for (const o of scene.children) {
    if (o.isHemisphereLight || o.isAmbientLight) cal.add(o.clone());
    else if (o.isDirectionalLight) {
      const d = new THREE.DirectionalLight(o.color, o.intensity);
      d.position.copy(o.position).sub(o.target.position).normalize();
      cal.add(d);
      dirs.push([d, o.intensity]);
    }
  }
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(20, 20).rotateX(-Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0xffffff, roughness }));
  cal.add(quad);
  const cam = new THREE.PerspectiveCamera(30, 1, 0.1, 50);
  cam.position.set(0, 2.2, 4.0);
  cam.lookAt(0, 0, 0);
  const rt = new THREE.WebGLRenderTarget(4, 4, { type: THREE.FloatType });
  const px = new Float32Array(4 * 4 * 4);
  const read = () => {
    renderer.setRenderTarget(rt);
    renderer.render(cal, cam);
    renderer.readRenderTargetPixels(rt, 0, 0, 4, 4, px);
    const c = new THREE.Vector3();
    for (let k = 0; k < 16; k++) c.x += px[k * 4] / 16, c.y += px[k * 4 + 1] / 16, c.z += px[k * 4 + 2] / 16;
    return c;
  };
  const prev = renderer.getRenderTarget();
  for (const [d] of dirs) d.intensity = 0;
  const amb = read();
  for (const [d, i] of dirs) d.intensity = i;
  const sun = read().sub(amb);
  renderer.setRenderTarget(prev);
  rt.dispose();
  quad.geometry.dispose();
  quad.material.dispose();
  return { amb, sun };
}

// the near terrain's own surface: its 5 m grid split into the same two triangles per square as terrain.js draws
function surface(hf, x, y) {
  const { half, step, n, data } = hf;
  let fx = (x + half) / step, fy = (y + half) / step;
  fx = Math.min(Math.max(fx, 0), n - 1.001);
  fy = Math.min(Math.max(fy, 0), n - 1.001);
  const i = fx | 0, j = fy | 0, ax = fx - i, ay = fy - j;
  const a = data[j * n + i], b = data[j * n + i + 1], c = data[(j + 1) * n + i], d = data[(j + 1) * n + i + 1];
  return ax + ay <= 1 ? a + (b - a) * ax + (c - a) * ay : d + (c - d) * (1 - ax) + (b - d) * (1 - ay);
}

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

export class Grass {
  constructor(renderer, scene, lib, hf, campus, sun) {
    this.renderer = renderer;
    this.scene = scene;
    this.hf = hf;
    this.sun = sun;
    this.lit = false;                                  // calibrated against the scene's lights (first update)
    const S = this.rect = campus.splat;
    this.res = MOBILE ? 1 : 0.5;                       // metres per texel of the grass share map
    this.w = Math.round((S.x1 - S.x0) / this.res);
    this.h = Math.round((S.y1 - S.y0) / this.res);
    this.share = null;                                 // Uint8Array: grass share 0..255
    this.dry = null;                                   // Uint8Array at 1 m: dry lawn 0..255
    this.cells = new Map();
    this.enabled = true;
    this.last = new THREE.Vector3(1e9, 0, 0);
    this.order = [];                                   // cell offsets round the camera's cell, nearest first
    const span = Math.ceil((R + MOVE) / CELL) + 1;
    for (let j = -span; j <= span; j++) for (let i = -span; i <= span; i++) this.order.push([i, j, Math.hypot(i, j)]);
    this.order.sort((a, b) => a[2] - b[2]);

    const P = 'assets/textures/pbr/';
    this.uniforms = {
      uTime: { value: 0 },
      uAmb: { value: new THREE.Vector3(0.5, 0.5, 0.5) }, uSun: { value: new THREE.Vector3(1, 1, 1) },
      uShadow: { value: null }, uShadowOn: { value: 0 }, uShadowSize: { value: new THREE.Vector2(1, 1) },
      uSunMatrix: { value: sun.shadow.matrix },
      uRect: { value: new THREE.Vector4(S.x0, S.y0, S.x1, S.y1) },
      // the terrain's own textures (loadTex hands back the same objects): the clump's colour is the ground's
      gD: { value: loadTex(P + 'leafy_grass/diff.jpg') }, dD: { value: loadTex(P + 'raked_dirt/diff.jpg') },
      uDry: { value: loadTex('assets/textures/ground_dry.png', { srgb: false, repeat: false }) },
      uGrass: lib.uniforms.uGrass,
      uLeaf: lib.uniforms.uLeaf, uLeafRect: lib.uniforms.uLeafRect, uFall: lib.uniforms.uFall,
    };
    const mat = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide });
    mat.onBeforeCompile = (sh) => this._patch(sh);
    mat.customProgramCacheKey = () => 'grass';
    const geo = clumpGeometry();
    this.inst = new THREE.InstancedBufferAttribute(new Float32Array(CAP * 2), 2);      // rank, tone
    this.inst.setUsage(THREE.DynamicDrawUsage);
    geo.setAttribute('aInst', this.inst);
    const im = this.mesh = new THREE.InstancedMesh(geo, mat, CAP);
    im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    im.count = 0;
    im.frustumCulled = false;
    im.castShadow = im.receiveShadow = false;
    im.visible = false;
    im.name = 'grass';
    scene.add(im);
    this.ready = this._load(campus).catch((e) => console.warn('grass:', e));
  }

  async _load(campus) {
    const S = this.rect, res = this.res;
    const toPx = (x, y) => [(x - S.x0) / res, (S.y1 - y) / res];
    const [sp, dr] = await Promise.all([
      // no blades inside the buildings: their footprints painted over as asphalt
      pixels('assets/textures/ground_splat.png', this.w, this.h, (x) => {
        x.fillStyle = '#ff0000';
        for (const b of campus.buildings) {
          x.beginPath();
          b.footprint.forEach(([px, py], k) => { const [u, v] = toPx(px, py); if (k) x.lineTo(u, v); else x.moveTo(u, v); });
          x.fill();
        }
      }),
      pixels('assets/textures/ground_dry.png', Math.round(S.x1 - S.x0), Math.round(S.y1 - S.y0)),
    ]);
    const share = new Uint8Array(this.w * this.h);
    for (let k = 0; k < share.length; k++) share[k] = Math.max(0, 255 - sp[k * 4] - sp[k * 4 + 1] - sp[k * 4 + 2]);
    const dry = new Uint8Array(dr.length / 4);
    for (let k = 0; k < dry.length; k++) dry[k] = dr[k * 4];
    this.share = share;
    this.dry = dry;
    this.last.set(1e9, 0, 0);
  }

  // bilinear grass share (0..1) at campus (x, y)
  _share(x, y) {
    const S = this.rect, w = this.w, h = this.h;
    const fx = (x - S.x0) / this.res - 0.5, fy = (S.y1 - y) / this.res - 0.5;
    const i = Math.floor(fx), j = Math.floor(fy);
    if (i < 0 || j < 0 || i >= w - 1 || j >= h - 1) return 0;
    const ax = fx - i, ay = fy - j, s = this.share, k = j * w + i;
    return ((s[k] * (1 - ax) + s[k + 1] * ax) * (1 - ay) + (s[k + w] * (1 - ax) + s[k + w + 1] * ax) * ay) / 255;
  }

  _dry(x, y) {
    const S = this.rect, w = Math.round(S.x1 - S.x0);
    const i = Math.floor(x - S.x0), j = Math.floor(S.y1 - y);
    if (i < 0 || j < 0 || i >= w || j >= Math.round(S.y1 - S.y0)) return 0;
    return this.dry[j * w + i] / 255;
  }

  // the clumps of one cell (campus cell i, j), made once: matrices, rank and tone, and their three-frame XZ
  _cell(i, j) {
    const key = (i + 4096) * 8192 + (j + 4096);
    let c = this.cells.get(key);
    if (c) return c;
    if (this.cells.size > 3000) this.cells.clear();
    const rnd = mulberry((i * 73856093) ^ (j * 19349663));
    const tries = Math.round(DENSITY * CELL * CELL);
    const m = new Float32Array(tries * 16), a = new Float32Array(tries * 2), p = new Float32Array(tries * 2);
    const m4 = this._m4 ||= new THREE.Matrix4(), q = this._q ||= new THREE.Quaternion(), v = this._v ||= new THREE.Vector3();
    const s = this._s ||= new THREE.Vector3(), UP = this._up ||= new THREE.Vector3(0, 1, 0);
    let n = 0;
    for (let k = 0; k < tries; k++) {
      const x = (i + rnd()) * CELL, y = (j + rnd()) * CELL, pick = rnd(), rank = rnd(), tone = rnd(), sc = rnd(), hs = rnd(), rot = rnd();
      const sh = this._share(x, y);
      if (sh < 0.5) continue;                 // (the paving's edge is where the share crosses one half: terrain.js)
      // full lawn: all of them; its edges and the worn dry lawn: fewer
      const dry = Math.min(1, Math.max(0, this._dry(x, y) * 1.5 - 0.25));
      const t = Math.min(1, (sh - 0.5) / 0.35);
      if (pick > t * t * (3 - 2 * t) * (1 - 0.6 * dry)) continue;
      const scale = 0.8 + sc * 0.45;
      m4.compose(v.set(x, surface(this.hf, x, y), -y), q.setFromAxisAngle(UP, rot * Math.PI * 2), s.set(scale, scale * (0.8 + hs * 0.4), scale));
      m4.toArray(m, n * 16);
      a[n * 2] = rank;
      a[n * 2 + 1] = 0.85 + tone * 0.3;
      p[n * 2] = x;
      p[n * 2 + 1] = -y;
      n++;
    }
    c = { n, m, a, p };
    this.cells.set(key, c);
    return c;
  }

  _refill(cx, cz) {
    const dst = this.mesh.instanceMatrix.array, da = this.inst.array;
    const ci = Math.floor(cx / CELL), cj = Math.floor(-cz / CELL);
    const reach = R + MOVE + CELL * 0.75;
    let count = 0;
    for (const [oi, oj, d] of this.order) {
      if ((d - 1) * CELL > reach) break;
      const c = this._cell(ci + oi, cj + oj);
      for (let k = 0; k < c.n; k++) {
        const dx = c.p[k * 2] - cx, dz = c.p[k * 2 + 1] - cz;
        const dist = Math.sqrt(dx * dx + dz * dz);
        if (c.a[k * 2] >= keep(Math.max(0, dist - MOVE))) continue;
        for (let e = 0, s = k * 16, o = count * 16; e < 16; e++) dst[o + e] = c.m[s + e];
        da[count * 2] = c.a[k * 2];
        da[count * 2 + 1] = c.a[k * 2 + 1];
        if (++count >= CAP) break;
      }
      if (count >= CAP) break;
    }
    const im = this.mesh;
    im.count = count;
    im.instanceMatrix.clearUpdateRanges();
    im.instanceMatrix.addUpdateRange(0, count * 16);
    im.instanceMatrix.needsUpdate = true;
    this.inst.clearUpdateRanges();
    this.inst.addUpdateRange(0, count * 2);
    this.inst.needsUpdate = true;
  }

  // camPos: the camera (three frame); t: seconds, for the sway
  update(camPos, t) {
    const u = this.uniforms;
    u.uTime.value = t;
    const sm = this.sun.shadow.map;
    u.uShadowOn.value = sm ? 1 : 0;
    if (sm) { u.uShadow.value = sm.texture; u.uShadowSize.value.set(sm.width, sm.height); }
    // high above the ground (the bird's-eye view) there is nothing within reach
    const up = camPos.y - surface(this.hf, camPos.x, -camPos.z);
    this.mesh.visible = this.enabled && !!this.share && up < R * 0.8;
    if (!this.mesh.visible) return;
    if (!this.lit) {
      const c = calibrate(this.renderer, this.scene, 0.98);     // (the lawn's roughness, terrain.js)
      if (c) { u.uAmb.value.copy(c.amb); u.uSun.value.copy(c.sun); }
      this.lit = true;
    }
    const dx = camPos.x - this.last.x, dz = camPos.z - this.last.z;
    if (dx * dx + dz * dz < MOVE * MOVE) return;
    this.last.copy(camPos);
    this._refill(camPos.x, camPos.z);
  }

  _patch(sh) {
    Object.assign(sh.uniforms, this.uniforms);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
        #include <packing>
        attribute vec2 aBlade;
        attribute vec2 aInst;
        uniform float uTime, uShadowOn;
        uniform sampler2D uShadow, gD, dD, uDry, uLeaf;
        uniform vec2 uShadowSize;
        uniform mat4 uSunMatrix;
        uniform vec4 uRect, uLeafRect;
        uniform vec3 uGrass, uFall, uAmb, uSun;
        varying vec3 vGCol;
        ${KEEP_GLSL}`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        {
          vec3 root = (modelMatrix * instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
          float camD = distance(root, cameraPosition);
          float k = grassKeep(camD);
          vGCol = vec3(0.0);
          if (aInst.x >= k) {
            transformed = vec3(0.0);                   // thinned out: a point, nothing drawn
          } else {
            // the ground's colour at the foot, as terrain.js paints it (clump-sized averages of its textures)
            vec2 wp = vec2(root.x, -root.z);
            vec2 suv = vec2((wp.x - uRect.x) / (uRect.z - uRect.x), (uRect.w - wp.y) / (uRect.w - uRect.y));
            float macro = textureLod(dD, wp / 61.0, 4.0).r;
            float n2 = textureLod(gD, wp / 23.0, 4.0).g;
            float lum = dot(textureLod(gD, wp / 4.0, 4.0).rgb, vec3(0.299, 0.587, 0.114));
            vec3 g = uGrass * (0.45 + 1.6 * lum) * mix(0.82, 1.15, macro) * mix(0.92, 1.06, n2);
            g = mix(g, g * vec3(1.15, 1.05, 0.7), smoothstep(0.55, 0.75, macro) * 0.5);
            float dry = textureLod(uDry, suv, 0.0).r;
            float tall = 1.0;
            if (dry > 0.003) {
              dry = clamp(dry * 1.5 - 0.25 + (macro - 0.5) * 0.9 + (n2 - 0.5) * 0.3, 0.0, 1.0);
              vec3 straw = vec3(0.45, 0.37, 0.2) * (0.5 + 1.3 * lum) * mix(0.85, 1.12, n2);
              float patchy = macro + (n2 - 0.5) * 0.6 + (textureLod(dD, wp / 17.0, 4.0).g - 0.45) * 0.5;
              tall = 1.0 - smoothstep(0.38, 0.58, patchy) * smoothstep(0.3, 0.9, dry);      // none on bare earth
              g = mix(g, mix(g, straw, 0.65 + 0.3 * smoothstep(0.35, 0.6, n2)), smoothstep(0.0, 0.6, dry));
              tall *= 1.0 - 0.3 * dry;                                                       // trodden short
            }
            // under the month's carpet of leaves or petals the blades barely show
            vec2 luv = vec2((wp.x - uLeafRect.x) / (uLeafRect.z - uLeafRect.x), (uLeafRect.w - wp.y) / (uLeafRect.w - uLeafRect.y));
            tall *= 1.0 - 0.7 * clamp(dot(textureLod(uLeaf, luv, 0.0).rgb, uFall) * 1.3, 0.0, 1.0);
            // a gust from the west now and then: the tips bow east (a world offset, taken into the clump's frame)
            float ph = dot(wp, vec2(0.21, 0.13)) - uTime * 1.7;
            vec3 wind = vec3(0.012 + 0.012 * sin(ph) + 0.004 * sin(uTime * 4.3 + wp.y), 0.0, 0.006 * sin(ph * 1.7 + 1.3)) * aBlade.y;
            vec3 ax = instanceMatrix[0].xyz, az = instanceMatrix[2].xyz;
            transformed.y *= tall * mix(0.5, 1.0, smoothstep(0.0, 0.25, k - aInst.x));
            // farther away a blade would shrink below a pixel and shimmer: wider clumps instead
            transformed.xz *= 1.0 + camD / 14.0;
            transformed.x += dot(wind, ax) / dot(ax, ax);
            transformed.z += dot(wind, az) / dot(az, az);
            // the sun's shadow where the vertex is (the blades are not in the shadow pass): a clump on a shadow's
            // edge, or under the walker's own small shadow, is dark only in part
            float vis = 1.0;
            if (uShadowOn > 0.5) {
              vec4 sc = uSunMatrix * (modelMatrix * instanceMatrix * vec4(transformed + vec3(0.0, 0.08, 0.0), 1.0));
              sc.xyz /= sc.w;
              if (sc.x > 0.0 && sc.x < 1.0 && sc.y > 0.0 && sc.y < 1.0 && sc.z < 1.0) {
                vec2 tx = 0.7 / uShadowSize;
                float z = sc.z - 0.0002;
                vis = 0.25 * (
                  step(z, unpackRGBAToDepth(textureLod(uShadow, sc.xy + vec2(-tx.x, -tx.y), 0.0))) +
                  step(z, unpackRGBAToDepth(textureLod(uShadow, sc.xy + vec2(tx.x, -tx.y), 0.0))) +
                  step(z, unpackRGBAToDepth(textureLod(uShadow, sc.xy + vec2(-tx.x, tx.y), 0.0))) +
                  step(z, unpackRGBAToDepth(textureLod(uShadow, sc.xy + vec2(tx.x, tx.y), 0.0))));
              }
            }
            // lit as the lawn beside it; dark at the foot, light at the tip
            vGCol = g * aInst.y * aBlade.x * mix(0.7, 1.2, aBlade.y) * (uAmb + uSun * vis);
          }
        }`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vGCol;')
      .replace('#include <color_fragment>', 'diffuseColor.rgb = vGCol;');
  }
}
