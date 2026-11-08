// Terrain (near: 5 m heightfield with PBR splat shader; far: 100 m ring with Seoul mountains)
// and the sky dome.  World frame: X = east, Y = up, Z = -north.
import * as THREE from 'three';
import { loadTex, shrinkImage, pcss } from './materials.js';
import { MOBILE, mulberry, placeMatrix, versioned } from './util.js';
import { ATMOS, ATMOS_GLSL, SKY_DRIFT } from './materials.js';
import { LITTER_GLSL, litterMagnolias } from './litter.js';

export class Heightfield {
  constructor(data, half, step, n) {
    Object.assign(this, { data, half, step, n });
  }
  // x = east, y = north (campus frame)
  height(x, y) {
    const { half, step, n, data } = this;
    let fx = (x + half) / step, fy = (y + half) / step;
    fx = Math.min(Math.max(fx, 0), n - 1.001);
    fy = Math.min(Math.max(fy, 0), n - 1.001);
    const i = fx | 0, j = fy | 0, ax = fx - i, ay = fy - j;
    const a = data[j * n + i], b = data[j * n + i + 1], c = data[(j + 1) * n + i], d = data[(j + 1) * n + i + 1];
    return a * (1 - ax) * (1 - ay) + b * ax * (1 - ay) + c * (1 - ax) * ay + d * ax * ay;
  }
}

function gridGeometry(hf, { skirt = 0, hole = 0, colorFn = null } = {}) {
  const { n, half, step, data } = hf;
  const pos = [], idx = [], col = [];
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const x = -half + i * step, y = -half + j * step;
      const h = data[j * n + i];
      pos.push(x, h, -y);
      if (colorFn) col.push(...colorFn(x, y, h, i, j));
    }
  }
  for (let j = 0; j < n - 1; j++) {
    for (let i = 0; i < n - 1; i++) {
      if (hole) {
        const x0 = -half + i * step, y0 = -half + j * step;
        if (x0 >= -hole && x0 + step <= hole && y0 >= -hole && y0 + step <= hole) continue;
      }
      const a = j * n + i, b = a + 1, c = a + n, d = c + 1;
      idx.push(a, b, c, b, d, c);
    }
  }
  if (skirt) {
    // vertical skirt around the border hides cracks against the far ring
    const base = pos.length / 3;
    const ring = [];
    for (let i = 0; i < n; i++) ring.push(i);                       // south edge
    for (let j = 1; j < n; j++) ring.push(j * n + n - 1);           // east
    for (let i = n - 2; i >= 0; i--) ring.push((n - 1) * n + i);    // north
    for (let j = n - 2; j > 0; j--) ring.push(j * n);               // west
    ring.forEach((v) => {
      pos.push(pos[v * 3], pos[v * 3 + 1] - skirt, pos[v * 3 + 2]);
      if (colorFn) col.push(col[v * 3], col[v * 3 + 1], col[v * 3 + 2]);
    });
    for (let k = 0; k < ring.length; k++) {
      const a = ring[k], b = ring[(k + 1) % ring.length];
      const a2 = base + k, b2 = base + (k + 1) % ring.length;
      idx.push(a, a2, b, b, a2, b2);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  if (colorFn) g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

export function makeNearTerrain(hf, campus, lib) {
  const g = gridGeometry(hf, { skirt: 40 });
  const S = campus.splat;
  const P = 'assets/textures/pbr/';
  const T = (n, srgb = true) => loadTex(P + n, { srgb });
  const uniforms = {
    uSplat: { value: loadTex('assets/textures/ground_splat.png', { srgb: false, repeat: false, mobileMax: 2048 }) },
    // worn, dry lawn (the east lawn and the 화단섬 of the May 1997 photo): same rectangle, 1 m texels
    uDry: { value: loadTex('assets/textures/ground_dry.png', { srgb: false, repeat: false }) },
    uRect: { value: new THREE.Vector4(S.x0, S.y0, S.x1, S.y1) },
    gD: { value: T('leafy_grass/diff.jpg') }, gN: { value: T('leafy_grass/nor.jpg', false) },
    aD: { value: T('asphalt_02/diff.jpg') }, aN: { value: T('asphalt_02/nor.jpg', false) },
    pD: { value: T('patterned_concrete_pavers/diff.jpg') }, pN: { value: T('patterned_concrete_pavers/nor.jpg', false) },
    dD: { value: T('raked_dirt/diff.jpg') }, dN: { value: T('raked_dirt/nor.jpg', false) },
    fD: { value: T('forest_ground_04/diff.jpg') },
    uGrass: lib.uniforms.uGrass,
    // the month's fallen leaves (litter.js): shared with 백양로's road materials, over the same rectangle
    uLeaf: lib.uniforms.uLeaf, uLitter: lib.uniforms.uLitter, uLeafRect: lib.uniforms.uLeafRect, uFall: lib.uniforms.uFall,
    uMag: lib.uniforms.uMag, uMagFall: lib.uniforms.uMagFall,           // (April's magnolia petals)
  };
  uniforms.uLeafRect.value.set(S.x0, S.y0, S.x1, S.y1);
  litterMagnolias(lib.uniforms, campus.trees);
  const m = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1 });
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uniforms);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWPos;\nvarying vec3 vWNrm;')
      .replace('#include <project_vertex>', `#include <project_vertex>
        vWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
        vWNrm = normalize(mat3(modelMatrix) * objectNormal);`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        varying vec3 vWPos; varying vec3 vWNrm;
        uniform sampler2D uSplat, uDry, gD, gN, aD, aN, pD, pN, dD, dN, fD;
        uniform vec4 uRect; uniform vec3 uGrass;
        vec3 gTN; float gRough;
        vec3 nrm(sampler2D t, vec2 uv) { return texture2D(t, uv).xyz * 2.0 - 1.0; }
        float hash12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
        ${LITTER_GLSL}`)
      .replace('#include <map_fragment>', `
        vec2 wp = vec2(vWPos.x, -vWPos.z);                 // campus x=east, y=north
        vec2 suv = vec2((wp.x - uRect.x) / (uRect.z - uRect.x), (uRect.w - wp.y) / (uRect.w - uRect.y));
        vec3 sp = texture2D(uSplat, suv).rgb;
        float inside = step(0.0, suv.x) * step(suv.x, 1.0) * step(0.0, suv.y) * step(suv.y, 1.0);
        sp *= inside;
        // the paving's edge: the map holds how much of each texel the asphalt and the paving cover (anti-aliased,
        // tools/build_campus.py splat_aa), so the edge is where that crosses one half: cut there as sharp as the
        // screen allows instead of blending grass into paving over a metre (the kerbs of curbs.js stand on it), and
        // the same between asphalt and paving
        float pv = sp.r + sp.g;
        float pvw = max(fwidth(pv) * 0.75, 0.002);
        float pvS = smoothstep(0.5 - pvw, 0.5 + pvw, pv);
        float ra = sp.r / max(pv, 1e-3);
        float raw = max(fwidth(ra) * 0.75, 0.002);
        float raS = smoothstep(0.5 - raw, 0.5 + raw, ra);
        sp.r = pvS * raS;
        sp.g = pvS * (1.0 - raS);
        // break up hard splat edges with a little texture-driven noise
        float macro = texture2D(dD, wp / 61.0).r;
        float n2 = texture2D(gD, wp / 23.0).g;
        sp.b = clamp(sp.b + (macro - 0.45) * 0.25 * step(0.05, sp.b), 0.0, 1.0 - pvS);
        float wa = sp.r, wpv = sp.g, wd = sp.b;
        float wg = max(0.0, 1.0 - wa - wpv - wd);
        vec2 ug = wp / 4.0, ua = wp / 7.0, up = wp / 2.4, ud = wp / 4.0;
        vec3 cg = texture2D(gD, ug).rgb;
        float lum = dot(cg, vec3(0.299, 0.587, 0.114));
        vec3 grass = uGrass * (0.45 + 1.6 * lum) * mix(0.82, 1.15, macro) * mix(0.92, 1.06, n2);
        grass = mix(grass, grass * vec3(1.15, 1.05, 0.7), smoothstep(0.55, 0.75, macro) * 0.5);
        // asphalt: the 1997 photo's roads are even, so the texture's cracks and patches are toned down (issue #11:
        // the side road's apron next to 백양로's own asphalt mesh showed more of them)
        vec3 aTex = texture2D(aD, ua).rgb;
        vec3 asph = mix(texture2D(aD, ua, 9.0).rgb, aTex, 0.55) * 0.85;
        vec3 pav = texture2D(pD, up).rgb * vec3(1.08, 0.94, 0.92);
        vec3 dirt = texture2D(dD, ud).rgb;
        vec3 forest = texture2D(fD, wp / 5.0).rgb * 0.8;
        float forestMask = smoothstep(0.55, 0.7, sp.b) * (1.0 - smoothstep(0.85, 0.95, sp.b));
        dirt = mix(dirt, forest, forestMask);
        // dry lawn: the grass goes to straw, with patches of bare trodden earth where the macro noise is high
        float dry = texture2D(uDry, suv).r * inside;
        if (dry > 0.003) {
          dry = clamp(dry * 1.5 - 0.25 + (macro - 0.5) * 0.9 + (n2 - 0.5) * 0.3, 0.0, 1.0);   // a ragged edge, green tufts
          vec3 straw = vec3(0.45, 0.37, 0.2) * (0.5 + 1.3 * lum) * mix(0.85, 1.12, n2);
          float patchy = macro + (n2 - 0.5) * 0.6 + (texture2D(dD, wp / 17.0).g - 0.45) * 0.5;
          float bare = smoothstep(0.38, 0.58, patchy) * smoothstep(0.3, 0.9, dry);
          vec3 earth = texture2D(dD, ud).rgb * vec3(1.05, 0.9, 0.74);
          vec3 worn = mix(mix(grass, straw, 0.65 + 0.3 * smoothstep(0.35, 0.6, n2)), earth, bare * 0.85);
          grass = mix(grass, worn, smoothstep(0.0, 0.6, dry));
        }
        vec3 albedo = grass * wg + asph * wa + pav * wpv + dirt * wd;
        // fallen leaves / petals of the month on top, flat: the ground's relief pressed down under them
        vec3 litCol;
        float litCov = litter(wp, wg, litCol);
        albedo = mix(albedo, litCol, litCov);
        diffuseColor.rgb *= albedo;
        gTN = nrm(gN, ug) * wg + nrm(aN, ua) * wa * 0.45 + nrm(pN, up) * wpv + nrm(dN, ud) * wd;
        gTN *= 1.0 - 0.75 * litCov;
        gRough = mix(0.98 * wg + 0.92 * wa + 0.85 * wpv + 1.0 * wd, 0.8, litCov);
      `)
      .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = gRough;')
      .replace('#include <normal_fragment_maps>', `
        vec3 nW = normalize(vWNrm + vec3(gTN.x, 0.0, -gTN.y) * 0.9);
        normal = normalize((viewMatrix * vec4(nW, 0.0)).xyz);
      `);
  };
  pcss(m);
  const mesh = new THREE.Mesh(g, m);
  mesh.receiveShadow = true;
  mesh.name = 'terrain_near';
  return mesh;
}

// low-frequency 0..1 noise over the far ring: where the woods start on the hills (terrain colour and canopy clumps)
const hillNoise = (x, y) => Math.sin(x * 0.013) * Math.cos(y * 0.011) * 0.5 + 0.5;

export function makeFarTerrain(hf, nearHalf) {
  const wc = new THREE.Color();
  const col = (x, y, h) => {
    // forest on the hills (안산, 인왕산, 북한산 ...), dense grey city in the valleys
    const r = Math.hypot(x, y);
    const n = hillNoise(x, y);
    const forest = THREE.MathUtils.smoothstep(h, 55 + n * 25, 95 + n * 30);
    // (linear albedo of roofs and streets seen from afar: brighter came out a white plain under the haze)
    const city = [0.25 + n * 0.05, 0.245 + n * 0.045, 0.24 + n * 0.04];
    // sRGB forest greens converted to linear (vertex colours are linear): dark, as in the 1997 photos
    wc.setRGB(0.2 + n * 0.06, 0.3 + n * 0.06, 0.15, THREE.SRGBColorSpace);
    const wood = [wc.r, wc.g, wc.b];
    const river = h < 6 && r > 3000 ? 1 : 0;      // (Copernicus GLO-30: the Han 2.5 - 3 m, 여의도 and the banks 8 m and up)
    const c = city.map((v, k) => v * (1 - forest) + wood[k] * forest);
    return river ? [0.32, 0.4, 0.45] : c;
  };
  const g = gridGeometry(hf, { hole: nearHalf, colorFn: col });
  const m = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1 });
  const mesh = new THREE.Mesh(g, m);
  mesh.name = 'terrain_far';
  mesh.receiveShadow = false;
  return mesh;
}

// Forest canopy on the far hills (안산, 인왕산 …): clumps of low-poly crowns so the slopes read as woodland
// rather than a smooth green dome.
export function makeFarForest(hf, nearHalf, maxR = 3800) {
  const rnd = mulberry(77);
  const pts = [];
  const { n, half, step, data } = hf;
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const x = -half + i * step, y = -half + j * step;
      if (Math.abs(x) < nearHalf - 50 && Math.abs(y) < nearHalf - 50) continue;
      const r = Math.hypot(x, y);
      if (r > maxR) continue;
      const h = data[j * n + i];
      if (h < 70 + hillNoise(x, y) * 30) continue;
      const k = r < 2400 ? 14 : 6;
      for (let m = 0; m < k; m++) pts.push([x + (rnd() - 0.5) * step, y + (rnd() - 0.5) * step]);
    }
  }
  const geo = new THREE.IcosahedronGeometry(1, 1);
  const mat = new THREE.MeshStandardMaterial({ roughness: 1, flatShading: true });
  const im = new THREE.InstancedMesh(geo, mat, pts.length);
  const m4 = new THREE.Matrix4(), sc = new THREE.Vector3(), c = new THREE.Color();
  pts.forEach(([x, y], i) => {
    const rr = 9 + rnd() * 8;
    sc.set(rr, rr * (0.55 + rnd() * 0.25), rr * (0.9 + rnd() * 0.2));
    im.setMatrixAt(i, placeMatrix(m4, x, hf.height(x, y) + rr * 0.25, y, rnd() * 6.28, sc));
    c.setRGB(0.16 + rnd() * 0.08, 0.26 + rnd() * 0.08, 0.11 + rnd() * 0.05, THREE.SRGBColorSpace);
    im.setColorAt(i, c);
  });
  im.instanceMatrix.needsUpdate = true;
  im.computeBoundingSphere();
  im.name = 'far_forest';
  return im;
}

// The masts on the 안산 summit, visible above 백양로 in the 1997 aerial photo.
export function makeSummitTower(hf, near = [710, 1400]) {
  let best = [-1e9, 0, 0];
  for (let dy = -300; dy <= 300; dy += 20) {
    for (let dx = -300; dx <= 300; dx += 20) {
      const h = hf.height(near[0] + dx, near[1] + dy);
      if (h > best[0]) best = [h, near[0] + dx, near[1] + dy];
    }
  }
  const [h, x, y] = best;
  const g = new THREE.Group();
  const white = new THREE.MeshStandardMaterial({ color: 0xd9dcdf, roughness: 0.6, metalness: 0.3 });
  const grey = new THREE.MeshStandardMaterial({ color: 0x9a9fa5, roughness: 0.7 });
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 2.6, 34, 4), white);
  mast.position.set(0, 17, 0);
  const deck = new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.2, 1.6, 8), white);
  deck.position.set(0, 24, 0);
  const top = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.4, 10, 6), white);
  top.position.set(0, 39, 0);
  const mast2 = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 1.4, 22, 4), white);
  mast2.position.set(14, 11, 6);
  const hut = new THREE.Mesh(new THREE.BoxGeometry(12, 5, 8), grey);
  hut.position.set(6, 2.5, -8);
  g.add(mast, deck, top, mast2, hut);
  g.position.set(x, h - 3, -y);
  g.name = 'ansan_tower';
  return g;
}

// Distant 1990s Seoul: instanced apartment blocks scattered on the low ground of the far ring.
export function makeCity(hf, nearHalf, count = 1600) {
  const c = document.createElement('canvas');
  c.width = 64; c.height = 128;
  const x = c.getContext('2d');
  x.fillStyle = '#d9d6cf'; x.fillRect(0, 0, 64, 128);
  for (let r = 0; r < 16; r++) {
    for (let k = 0; k < 4; k++) {
      x.fillStyle = Math.random() < 0.2 ? '#8a8d92' : '#4f5a66';
      x.fillRect(4 + k * 15, 4 + r * 8, 10, 4);
    }
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  const geo = new THREE.BoxGeometry(1, 1, 1);
  geo.translate(0, 0.5, 0);
  const mat = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.9 });
  const im = new THREE.InstancedMesh(geo, mat, count);
  const m4 = new THREE.Matrix4(), s = new THREE.Vector3();
  let k = 0, tries = 0;
  const rnd = mulberry(7);
  while (k < count && tries < count * 20) {
    tries++;
    const X = (rnd() * 2 - 1) * 6500, Y = (rnd() * 2 - 1) * 6500;
    if (Math.abs(X) < nearHalf + 150 && Math.abs(Y) < nearHalf + 150) continue;
    const h = hf.height(X, Y);
    if (h > 60 || h < 8) continue;
    const apt = rnd() < 0.45;
    s.set(apt ? 14 : 10 + rnd() * 20, apt ? 25 + rnd() * 20 : 6 + rnd() * 12, apt ? 60 + rnd() * 40 : 10 + rnd() * 20);
    im.setMatrixAt(k++, placeMatrix(m4, X, h - 1, Y, rnd() < 0.7 ? 0.25 : rnd() * 3, s));
  }
  im.count = k;
  im.name = 'far_city';
  return im;
}

// the horizon fades into the scene's fog colour for that direction (materials.js ATMOS): seamless with far terrain.
// The photo's clouds drift with the wind (materials.js SKY_DRIFT) as a flat layer: what is seen along d is the point of
// the photo's layer uDrift upwind of there, so they cross fastest overhead and hardly move at the horizon. The sun's
// disc and glow are in the photo: the drift fades out from 60 deg off the sun to 2 deg, one bent lookup. (Over a 5 to
// 30 deg band the cloud beside the sun was torn; two lookups mixed instead of one bent showed every cloud twice.)
const SKY_FIX = [Math.cos(60 * Math.PI / 180), Math.cos(2 * Math.PI / 180)];
export function makeSky(skyMeta) {
  const tex = new THREE.TextureLoader().load(versioned('assets/hdri/sky_8k.jpg'), (t) => {
    if (MOBILE) { t.image = shrinkImage(t.image, 4096); t.needsUpdate = true; }   // 8K sky: 90 MB on the GPU
  });
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = THREE.RepeatWrapping;
  tex.anisotropy = 4;
  const mat = new THREE.ShaderMaterial({
    uniforms: { uSky: { value: tex }, uV0: { value: skyMeta.sky_v0 }, uExposure: { value: 1.0 }, uDrift: SKY_DRIFT,
      ...ATMOS },
    vertexShader: `varying vec3 vDir; void main(){ vDir = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); gl_Position.z = gl_Position.w; }`,
    fragmentShader: `
      uniform sampler2D uSky; uniform float uV0; uniform float uExposure; uniform vec2 uDrift; varying vec3 vDir;
      ${ATMOS_GLSL}
      void main(){
        vec3 d = normalize(vDir), s = d;
        if (d.y > 1e-3) {
          float k = 1.0 - smoothstep(${SKY_FIX[0].toFixed(6)}, ${SKY_FIX[1].toFixed(6)}, dot(d, uSunW));
          vec2 p = d.xz / d.y - uDrift * k;
          s = vec3(p.x, 1.0, p.y) * inversesqrt(1.0 + dot(p, p));
        }
        float u = atan(s.z, s.x) * 0.15915494 + 0.5;
        float el = asin(clamp(s.y, -1.0, 1.0));
        float v = (el * 0.31830989 + 0.5 - uV0) / (1.0 - uV0);
        // the mip level from u's change across the pixel without its jump from 1 to 0 in the west: it drew a line up
        // the sky there, which the drift would now carry along
        vec2 gx = vec2(dFdx(u), dFdx(v)), gy = vec2(dFdy(u), dFdy(v));
        gx.x -= floor(gx.x + 0.5); gy.x -= floor(gy.x + 0.5);
        vec3 c = textureGrad(uSky, vec2(u, clamp(v, 0.002, 0.998)), gx, gy).rgb * uExposure;
        float hz = smoothstep(-0.02, 0.10, d.y);
        c = mix(y97FogColor(d), c, hz * 0.85 + 0.15 * smoothstep(0.1, 0.4, d.y));
        gl_FragColor = vec4(c, 1.0);
        #include <colorspace_fragment>
      }`,
    side: THREE.BackSide, depthWrite: false, depthTest: true, fog: false,
  });
  // the texture is sRGB; the shader works in the texture's decoded linear space
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 32), mat);
  mesh.scale.setScalar(8000);
  // after every other opaque object: it sits on the far plane, so the depth test drops the sky pixels behind
  // buildings, trees and terrain instead of shading the whole screen first and painting over it
  mesh.renderOrder = 10;
  mesh.frustumCulled = false;
  mesh.name = 'sky';
  return mesh;
}
