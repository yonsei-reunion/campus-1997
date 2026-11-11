// Baked sun shadows: the whole campus's static sun shadow, cast on the ground, in one texture (and the town south of
// the gate, 정문 밖 to 신촌 로터리, coarser, in the same texture: TOWN_RECT).
// The sun never moves, so the shadows of the buildings, the trees (their alpha-tested crowns: dappled, not solid), the
// shrubs, the props and the parked cars on the ground are drawn once, from above (bakeSunMap below, run by
// tools/bake_sun_shadows.mjs), into assets/textures/sun_shadow.png: 1 = sunlit, 0 = in shadow.
// Phones draw no shadow maps (main.js: the shadow pass crashes some GPU drivers), so there this is the only sun
// shadow; on the desktop it shades what the real-time map (shadows.js) leaves out: the ground beyond its reach and
// the shadows of the far trees, which are impostors that cast nothing.
// "The ground" is the walked surface: the terrain and on it the terraces of 노천극장, 대우관's terrace over the 상뜰,
// the arcade on 중앙도서관's plinth, the flights (main.js walkables). Its height over the terrain is baked with the map
// (assets/textures/sun_ground.png), so what stands on a terrace takes the terrace's shadow as on the lawn.
// Higher up, the walls and roofs of the halls and landmarks carry their own sun shadow per corner (the alpha of the
// attribute blender/bake.py writes): on phones that is their shadow there (SUN_WALL); the desktop has its map.
import * as THREE from 'three';
import { versioned } from './util.js';
import { patchShaderOwn, upload } from './materials.js';

// the baked rectangle (campus x = east, y = north, metres; every building and tree, and their shadows to the
// north-west) and its size in texels: 31 cm texels
export const SUN_RECT = { x0: -440, y0: -505, x1: 560, y1: 745 };
export const SUN_SIZE = [3200, 4000];
const URL = 'assets/textures/sun_shadow.png';
// 정문 밖 south of it (창천동, 연세로, 신촌 로터리: seen from the gate and from above, not walked) in 70 cm texels, in
// the same texture, so that no material reads one more: east of the campus's block, three slices of the town from
// west to east one above the other, each with GUTTER texels of the town round it (the filtering reaches across a
// slice's edge into the right ground). The texture: 3968 x 4000 (under 4096 a side), 21 MB on the GPU with its
// mipmaps, 4 MB more than the campus alone.
const TOWN_TEXEL = 0.7, SLICE = [736, 986], SLICES = 3, GUTTER = 16;
export const TOWN_RECT = { x0: -845, y1: SUN_RECT.y0, x1: -845 + SLICES * SLICE[0] * TOWN_TEXEL, y0: SUN_RECT.y0 - SLICE[1] * TOWN_TEXEL };
export const MAP_SIZE = [SUN_SIZE[0] + SLICE[0] + 2 * GUTTER, SUN_SIZE[1]];
const f1 = (v) => v.toFixed(1);
// The map at p (campus metres), filtered over the screen footprint dpx, dpy of a pixel (dFdx, dFdy of p: taken by
// the caller before any branch; the map's areas meet where the coordinates jump); 1 (sunlit) outside both areas.
// (uSunMap and uSunRect declared before it)
export const SUN_MAP_GLSL = `
  float sunMapAt( vec2 p, vec2 dpx, vec2 dpy ) {
    vec2 uv = vec2( ( p.x - uSunRect.x ) / ( uSunRect.z - uSunRect.x ), ( uSunRect.w - p.y ) / ( uSunRect.w - uSunRect.y ) );
    vec2 t, k;                // texel coordinates in the map, texels a metre
    if ( uv.x >= 0.0 && uv.x <= 1.0 && uv.y >= 0.0 && uv.y <= 1.0 ) {
      t = uv * vec2( ${f1(SUN_SIZE[0])}, ${f1(SUN_SIZE[1])} );
      t.x = min( t.x, ${f1(SUN_SIZE[0] - 0.5)} );
      k = vec2( ${f1(SUN_SIZE[0])}, ${f1(SUN_SIZE[1])} ) / ( uSunRect.zw - uSunRect.xy );
    } else {
      t = vec2( p.x - ${f1(TOWN_RECT.x0)}, ${f1(TOWN_RECT.y1)} - p.y ) / ${TOWN_TEXEL.toFixed(3)};
      if ( t.x < 0.0 || t.y < 0.0 || t.x > ${f1(SLICES * SLICE[0])} || t.y > ${f1(SLICE[1])} ) return 1.0;
      float s = min( floor( t.x / ${f1(SLICE[0])} ), ${f1(SLICES - 1)} );
      t = vec2( ${f1(SUN_SIZE[0] + GUTTER)} + t.x - s * ${f1(SLICE[0])}, s * ${f1(SLICE[1] + 2 * GUTTER)} + ${f1(GUTTER)} + t.y );
      k = vec2( ${(1 / TOWN_TEXEL).toFixed(5)} );
    }
    vec2 inv = 1.0 / vec2( ${f1(MAP_SIZE[0])}, ${f1(MAP_SIZE[1])} );
    return textureGrad( uSunMap, t * inv, dpx * k * inv, dpy * k * inv ).r;
  }`;
// the walked surface's height over the terrain, in texels twice as large (62 cm: 3.2 MB on the GPU, and the halls'
// own bake has the shadows at a terrace's edge), 8-bit, LIFT_STEP m a level (0 .. 12.75 m)
const GROUND_URL = 'assets/textures/sun_ground.png';
const LIFT_SIZE = [SUN_SIZE[0] / 2, SUN_SIZE[1] / 2];
const LIFT_STEP = 0.05;
const LIFT_MAX = (255 * LIFT_STEP).toFixed(2);
// The map is the shadow on the top-most surface no higher than this above the walked surface: the ground, and on it
// plinths, steps, shrubs, benches and parked car roofs (porch roofs and the like are higher: the ground under them is
// baked)
const LIFT = 1.6;

// The shader edit. SUN_MODE 0: ground (the terrain) takes the map as it is. 1: everything else static or moving,
// read where it stands; walls read the ground just in front of them (the texel under a wall is in the building's
// own shadow), and nothing higher than the baked surfaces takes it. 2: people, the whole body the light of the
// spot it stands on (no moving thing is in the map, so nobody darkens in their own shadow).
// SUN_WALL (phones; the halls' and landmarks' materials): their own baked shadow as well, at every height.
// The result is the global `bakedSun` (1 sunlit, 0 in shadow), set at the top of main(): the sun's direct light is
// scaled by it, and a later edit of the lighting can read it too.
const VERT = `
  {
    vec4 sunW = vec4( transformed, 1.0 );
    #ifdef USE_BATCHING
    sunW = batchingMatrix * sunW;
    #endif
    #ifdef USE_INSTANCING
    sunW = instanceMatrix * sunW;
    #endif
    vSunW = ( modelMatrix * sunW ).xyz;
    vSunN = ( vec4( transformedNormal, 0.0 ) * viewMatrix ).xyz;
  }`;
const GROUND_DECL = `
  uniform sampler2D uSunGround, uSunLift, uSunPatch;
  uniform vec4 uSunRect;      // x0, y0 (south-west corner), x1, y1 (north-east) of the map's campus block
  uniform vec3 uSunGroundF;   // the terrain heightfield: half size, step, vertices per side
  uniform vec4 uSunPatchF;    // its patch south of the grid (terrain.js Heightfield.setPatch): x0, y0, x1, y1
  uniform vec2 uSunPatchN;    // the patch's vertices along x, y
  vec2 sunUV( vec2 p ) {
    return vec2( ( p.x - uSunRect.x ) / ( uSunRect.z - uSunRect.x ), ( uSunRect.w - p.y ) / ( uSunRect.w - uSunRect.y ) );
  }
  float sunTerrainH( vec2 p ) {
    if ( p.y < uSunPatchF.w && p.x >= uSunPatchF.x && p.x <= uSunPatchF.z )
      return texture2D( uSunPatch, ( ( p - uSunPatchF.xy ) / ( uSunPatchF.zw - uSunPatchF.xy ) * ( uSunPatchN - 1.0 ) + 0.5 ) / uSunPatchN ).r;
    return texture2D( uSunGround, ( ( p + uSunGroundF.x ) / uSunGroundF.y + 0.5 ) / uSunGroundF.z ).r;
  }
  // the walked surface at p: the terrain and the terraces, plinths and flights on it (baked in the campus's block only)
  float sunGroundH( vec2 p ) {
    vec2 uv = sunUV( p );
    bool lifted = uv.x >= 0.0 && uv.x <= 1.0 && uv.y >= 0.0 && uv.y <= 1.0;
    return sunTerrainH( p ) + ( lifted ? texture2D( uSunLift, uv ).r * ${LIFT_MAX} : 0.0 );
  }`;
const FRAG_DECL = `
  uniform sampler2D uSunMap;
  ${GROUND_DECL}
  ${SUN_MAP_GLSL}
  varying vec3 vSunW; varying vec3 vSunN;
  float bakedSun;
  float sunBaked() {
    vec2 p = vec2( vSunW.x, -vSunW.z );
    float own = 1.0, w = 1.0;
    #ifdef SUN_WALL
    own = vBake.a;            // the hall's own bake: its shadows and its neighbours' and the trees' on it
    #endif
    #if SUN_MODE == 1
    vec3 n = normalize( vSunN );
    p += vec2( n.x, -n.z ) * 0.35;
    w = 1.0 - smoothstep( 1.0, ${LIFT.toFixed(2)}, vSunW.y - sunGroundH( p ) );
    #elif SUN_MODE == 2
    w = 1.0 - smoothstep( 2.2, 2.8, vSunW.y - sunGroundH( p ) );
    #endif
    vec2 dpx = dFdx( p ), dpy = dFdy( p );
    #if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
    // in the real-time shadow map and near the view that map alone (sharper, and it has the people and cars);
    // farther out, where its trees are impostors, both (where both see a caster they agree); outside it this alone
    vec3 sc = vDirectionalShadowCoord[ 0 ].xyz / vDirectionalShadowCoord[ 0 ].w;
    vec2 e = min( sc.xy, 1.0 - sc.xy );
    float inMap = smoothstep( 0.0, 0.04, min( e.x, e.y ) ) * step( sc.z, 1.0 );
    w *= 1.0 - inMap * ( 1.0 - smoothstep( 110.0, 150.0, distance( vSunW, cameraPosition ) ) );
    #endif
    if ( w <= 0.0 ) return own;
    return min( own, mix( 1.0, sunMapAt( p, dpx, dpy ), w ) );
  }`;
const SUN_LINE = 'getDirectionalLightInfo( directionalLight, directLight );';

function editShader(sh, uniforms, mode) {
  Object.assign(sh.uniforms, uniforms);
  sh.vertexShader = sh.vertexShader
    .replace('#include <common>', '#include <common>\nvarying vec3 vSunW; varying vec3 vSunN;')
    .replace('#include <project_vertex>', `#include <project_vertex>${VERT}`);
  // (the lights chunk is expanded here so the sun's line in it can be reached; another edit may have done it already.
  // The function goes right before main(), after every declaration: the real-time map's coordinates among them,
  // whether shadowmap_pars_fragment is still an include or the PCSS edit has already replaced it.)
  sh.fragmentShader = sh.fragmentShader
    .replace('#include <lights_fragment_begin>', THREE.ShaderChunk.lights_fragment_begin)
    .replace('void main() {', `#define SUN_MODE ${mode}${FRAG_DECL}\nvoid main() {\n\tbakedSun = sunBaked();`)
    .replace(SUN_LINE, `${SUN_LINE}\n\t\tdirectLight.color *= bakedSun;`);
}

function groundTexture(hf) {
  const { n, data } = hf;
  const h = new Uint16Array(n * n);
  for (let i = 0; i < n * n; i++) h[i] = THREE.DataUtils.toHalfFloat(data[i]);
  const t = new THREE.DataTexture(h, n, n, THREE.RedFormat, THREE.HalfFloatType);
  t.minFilter = t.magFilter = THREE.LinearFilter;
  t.needsUpdate = true;
  return t;
}

// the terrain's patch south of the grid (Heightfield.setPatch: 신촌 로터리), or nothing: (uniforms of sunTerrainH)
function patchUniforms(hf) {
  const e = hf.ext;
  if (!e) return { uSunPatch: { value: grey1(0) }, uSunPatchF: { value: new THREE.Vector4(0, 0, -1, -1) }, uSunPatchN: { value: new THREE.Vector2(1, 1) } };
  const h = new Uint16Array(e.nx * e.ny);
  for (let i = 0; i < h.length; i++) h[i] = THREE.DataUtils.toHalfFloat(e.data[i]);
  const t = new THREE.DataTexture(h, e.nx, e.ny, THREE.RedFormat, THREE.HalfFloatType);
  t.minFilter = t.magFilter = THREE.LinearFilter;
  t.needsUpdate = true;
  return { uSunPatch: { value: t }, uSunPatchF: { value: new THREE.Vector4(e.x0, e.y0, e.x1, e.y1) }, uSunPatchN: { value: new THREE.Vector2(e.nx, e.ny) } };
}

function grey1(v) {
  const t = new THREE.DataTexture(new Uint8Array([v]), 1, 1, THREE.RedFormat);
  t.needsUpdate = true;
  return t;
}

// an 8-bit grey map, row 0 = north
function rectTexture(t) {
  t.format = THREE.RedFormat;
  t.colorSpace = THREE.NoColorSpace;
  t.flipY = false;
  t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  t.needsUpdate = true;
  return t;
}

export class SunMap {
  // walls: the halls' and landmarks' own baked shadow on their walls and roofs too (the phones: no shadow map)
  constructor(hf, { walls = false } = {}) {
    this.white = grey1(255);
    const { x0, y0, x1, y1 } = SUN_RECT;
    this.uniforms = {
      uSunMap: { value: this.white },          // sunlit everywhere until the map has loaded
      uSunRect: { value: new THREE.Vector4(x0, y0, x1, y1) },
      uSunGround: { value: groundTexture(hf) },
      uSunGroundF: { value: new THREE.Vector3(hf.half, hf.step, hf.n) },
      uSunLift: { value: grey1(0) },           // the bare terrain until the walked surface has loaded
      ...patchUniforms(hf),
    };
    this.texture = null;
    this.walls = walls;
    this._on = true;
    this.patched = new WeakSet();
  }

  load() {
    const loader = new THREE.TextureLoader();
    loader.load(versioned(URL), (t) => {
      if (t.image.width !== MAP_SIZE[0] || t.image.height !== MAP_SIZE[1]) {     // (an old map: its shadows would be misplaced)
        console.warn(`no baked sun shadows: ${URL} is ${t.image.width} x ${t.image.height}, not ${MAP_SIZE.join(' x ')} (tools/bake_sun_shadows.mjs)`);
        return;
      }
      rectTexture(t).anisotropy = 8;
      upload(t);
      this.texture = t;
      if (this._on) this.uniforms.uSunMap.value = t;
    }, undefined, () => console.warn('no baked sun shadows:', URL));
    loader.load(versioned(GROUND_URL), (t) => {
      rectTexture(t).generateMipmaps = false;  // heights: never averaged across a terrace's edge in the distance
      t.minFilter = THREE.LinearFilter;
      upload(t);
      this.uniforms.uSunLift.value = t;
    }, undefined, () => console.warn('no baked walked surface (the shadows on the bare terrain):', GROUND_URL));
    return this;
  }

  get on() { return this._on; }
  set on(v) { this._on = v; this.uniforms.uSunMap.value = v && this.texture ? this.texture : this.white; }

  // add the baked shadow to a lit material's sunlight
  patch(m, mode = 1) {
    if (!m || !m.isMeshStandardMaterial || this.patched.has(m)) return;
    this.patched.add(m);
    // (a define, not an edit of its own: a baked copy replays its original's edits, this one among them)
    if (this.walls && mode === 1 && m.userData.baked && !m.userData.wallLeaf) m.defines = { ...m.defines, SUN_WALL: '' };
    // on the shared patch stack (materials.js), so a patch added later (the atmosphere's, from main.js) stacks on it
    // instead of replacing it
    patchShaderOwn(m, `sun${mode}`, (sh) => editShader(sh, this.uniforms, mode));
    m.needsUpdate = true;
  }

  // every lit material in the scene but the far scenery and the see-through ones (glass, water)
  patchScene(root, skip = () => false) {
    root.traverse((o) => {
      if (!o.isMesh || skip(o)) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        if (m.transparent || /^impostor_/.test(m.name)) continue;
        this.patch(m, m.name === 'person' ? 2 : 1);
      }
    });
  }
}

// ---------------------------------------------------------------------------- baking (tools/bake_sun_shadows.mjs)
// Draws the maps in tiles from straight above. First the walked surface (walk: main.js walkables, the terrain among
// them): the height of the highest one over the terrain at every texel. Then the shadow, with the game's own sun
// shadow map (shadows.js, the desktop path): for each tile the shadow frustum is put over it, every tree near it is
// switched to its full model, and the ground is drawn with a material that writes the shadow only. Moving things
// (people, cars, the ball) and the banners (they change with the month) are hidden.
// The campus's block and then the town's area (the walked surface there: the bare terrain), packed into one map
// (MAP_SIZE, SUN_MAP_GLSL).
// Returns {width, height, data, lift: {width, height, data}}: row 0 = north, 0..255 (lift: LIFT_STEP m a level).
export async function bakeSunMap({ renderer, scene, sun, sunDir, shadows, forest, hf, walk = [], hide = [], skip = () => false }) {
  const BAKE = 7;                                       // layer of the surfaces the top view sees
  const [W, H] = SUN_SIZE;
  const TILE = 400, SS = 2, N = TILE * SS;              // texels per tile side, supersampling
  // the areas: north-west corner, texel, size in texels
  const CAMPUS = { x0: SUN_RECT.x0, y1: SUN_RECT.y1, texel: (SUN_RECT.x1 - SUN_RECT.x0) / W, w: W, h: H };
  const TOWN = { x0: TOWN_RECT.x0 - GUTTER * TOWN_TEXEL, y1: TOWN_RECT.y1 + GUTTER * TOWN_TEXEL, texel: TOWN_TEXEL,
    w: SLICES * SLICE[0] + 2 * GUTTER, h: SLICE[1] + 2 * GUTTER };
  renderer.setAnimationLoop(null);
  const rt = new THREE.WebGLRenderTarget(N, N, { minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false });
  const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 2000);
  cam.up.set(0, 0, -1);                                 // screen up = north
  cam.layers.set(BAKE);
  const buf = new Uint8Array(N * N * 4);
  // every tile of an area from straight above, 2x2 box filtered into out (GL rows run from the bottom: south);
  // draw(cx, cy, h, half): half the tile's side in metres
  const tiles = async (A, draw, out) => {
    const half = (TILE * A.texel) / 2;
    Object.assign(cam, { left: -half, right: half, top: half, bottom: -half });
    cam.updateProjectionMatrix();
    for (let ty = 0; ty < Math.ceil(A.h / TILE); ty++) {
      for (let tx = 0; tx < Math.ceil(A.w / TILE); tx++) {
        const cx = A.x0 + (tx + 0.5) * TILE * A.texel, cy = A.y1 - (ty + 0.5) * TILE * A.texel;
        const h = hf.height(cx, cy);
        cam.position.set(cx, h + 900, -cy);
        cam.lookAt(cx, h, -cy);
        draw(cx, cy, h, half);
        renderer.readRenderTargetPixels(rt, 0, 0, N, N, buf);
        for (let r = 0; r < Math.min(TILE, A.h - ty * TILE); r++) {
          const row = (ty * TILE + r) * A.w + tx * TILE, gr0 = (N - 1 - r * SS) * N, gr1 = gr0 - N;
          for (let c = 0; c < Math.min(TILE, A.w - tx * TILE); c++) {
            const a = (gr0 + c * SS) * 4, b = (gr1 + c * SS) * 4;
            out[row + c] = (buf[a] + buf[a + 4] + buf[b] + buf[b + 4] + 2) >> 2;
          }
        }
        await new Promise((res) => setTimeout(res, 0));
      }
    }
  };
  const uniforms = {
    uSunGround: { value: groundTexture(hf) }, uSunGroundF: { value: new THREE.Vector3(hf.half, hf.step, hf.n) },
    uSunRect: { value: new THREE.Vector4(SUN_RECT.x0, SUN_RECT.y0, SUN_RECT.x1, SUN_RECT.y1) },
    uSunLift: { value: grey1(0) },
    ...patchUniforms(hf),
  };
  renderer.setClearColor(0x000000, 1);

  // 1. the walked surface: copies of the walkables (some are not in the scene: the flights' walk surfaces)
  const walkScene = new THREE.Scene();
  const liftMat = new THREE.ShaderMaterial({
    uniforms, side: THREE.DoubleSide,
    vertexShader: `varying vec3 vW;
      void main() { vec4 w = modelMatrix * vec4( position, 1.0 ); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `${GROUND_DECL}
      varying vec3 vW;
      void main() {
        vec2 p = vec2( vW.x, -vW.z );
        float g = texture2D( uSunGround, ( ( p + uSunGroundF.x ) / uSunGroundF.y + 0.5 ) / uSunGroundF.z ).r;
        gl_FragColor = vec4( vec3( clamp( ( vW.y - g ) / ${LIFT_MAX}, 0.0, 1.0 ) ), 1.0 );
      }`,
  });
  for (const o of walk) {
    const m = new THREE.Mesh(o.geometry, liftMat);
    m.matrixAutoUpdate = false;
    m.matrix.copy(o.matrixWorld);
    m.layers.set(BAKE);
    walkScene.add(m);
  }
  const fine = new Uint8Array(W * H);
  await tiles(CAMPUS, () => { renderer.setRenderTarget(rt); renderer.render(walkScene, cam); }, fine);
  liftMat.dispose();
  const [LW, LH] = LIFT_SIZE, lift = new Uint8Array(LW * LH);
  for (let r = 0; r < LH; r++) {
    for (let c = 0; c < LW; c++) {
      const a = 2 * r * W + 2 * c;
      lift[r * LW + c] = (fine[a] + fine[a + 1] + fine[a + W] + fine[a + W + 1] + 2) >> 2;
    }
  }
  const liftTex = new THREE.DataTexture(lift, LW, LH, THREE.RedFormat);
  liftTex.minFilter = liftTex.magFilter = THREE.LinearFilter;
  liftTex.needsUpdate = true;
  uniforms.uSunLift.value = liftTex;

  // 2. the shadow on the top-most surface within LIFT of it
  const hidden = [];
  for (const o of [...shadows.dyn.map((d) => d.root), ...hide]) if (o && o.visible) { o.visible = false; hidden.push(o); }
  // the receivers: everything solid but the trees and the far scenery
  const trees = new Set();
  for (const k of Object.values(forest.near)) for (const p of k.parts) trees.add(p);
  for (const { im, top } of Object.values(forest.impostors)) { trees.add(im); trees.add(top); }
  const recv = [];
  scene.traverse((o) => {
    if (!o.isMesh || trees.has(o) || skip(o)) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    if (mats.every((m) => m.transparent)) return;
    let v = true;
    for (let p = o; p; p = p.parent) if (!p.visible) v = false;
    if (!v) return;
    recv.push([o, o.receiveShadow]);
    o.layers.enable(BAKE);
    o.receiveShadow = true;
  });
  sun.layers.enable(BAKE);
  const mat = new THREE.ShadowMaterial({ side: THREE.DoubleSide, fog: false });
  mat.transparent = false;
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uniforms);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vSunW; varying vec3 vSunN;')
      .replace('#include <project_vertex>', `#include <project_vertex>${VERT}`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        ${GROUND_DECL}
        varying vec3 vSunW;`)
      .replace('gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );', `
        if ( vSunW.y - sunGroundH( vec2( vSunW.x, -vSunW.z ) ) > ${LIFT.toFixed(2)} ) discard;
        gl_FragColor = vec4( vec3( getShadowMask() ), 1.0 );`);
  };
  const prevOverride = scene.overrideMaterial;
  scene.overrideMaterial = mat;
  const sh = sun.shadow;
  const prevNear = forest.nearDist, centre = new THREE.Vector3();
  renderer.setClearColor(0xffffff, 1);
  const shade = (cx, cy, h, half) => {
    const span = half * 1.45 + 20;
    Object.assign(sh.camera, { left: -span, right: span, top: span, bottom: -span });
    sh.camera.updateProjectionMatrix();
    shadows.span = span;
    centre.set(cx, h, -cy);
    // full trees within reach of the tile: its corners, the longest tree shadows and a crown
    forest.nearDist = half * 1.42 + 50;
    forest.update(centre, true);
    sun.target.position.copy(centre);
    sun.position.copy(centre).addScaledVector(sunDir, shadows.dist);
    shadows.req.focus.copy(centre);
    shadows.dirty = true;
    shadows.pending = shadows.req;                      // the static casters are drawn in the render below
    renderer.setRenderTarget(rt);
    renderer.render(scene, cam);
  };
  const out = new Uint8Array(W * H), town = new Uint8Array(TOWN.w * TOWN.h);
  await tiles(CAMPUS, shade, out);
  await tiles(TOWN, shade, town);
  renderer.setRenderTarget(null);
  scene.overrideMaterial = prevOverride;
  for (const [o, rs] of recv) { o.layers.disable(BAKE); o.receiveShadow = rs; }
  for (const o of hidden) o.visible = true;
  forest.nearDist = prevNear;
  shadows.invalidate();
  rt.dispose();
  liftTex.dispose();
  // the map: the campus's block at the west, the town's slices east of it (each with its gutters), sunlit between
  const [MW, MH] = MAP_SIZE, map = new Uint8Array(MW * MH).fill(255);
  for (let r = 0; r < H; r++) map.set(out.subarray(r * W, (r + 1) * W), r * MW);
  const SW = SLICE[0] + 2 * GUTTER, SH = SLICE[1] + 2 * GUTTER;
  for (let k = 0; k < SLICES; k++) {
    for (let r = 0; r < SH; r++) map.set(town.subarray(r * TOWN.w + k * SLICE[0], r * TOWN.w + k * SLICE[0] + SW), (k * SH + r) * MW + W);
  }
  return { width: MW, height: MH, data: map, lift: { width: LW, height: LH, data: lift } };
}
