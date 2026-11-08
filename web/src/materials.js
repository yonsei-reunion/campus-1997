// Shared PBR material library, built from data/materials.json (same file Blender uses).
import * as THREE from 'three';
import { MOBILE, versioned, mulberry } from './util.js';
import { LITTER_MATS, litterUniforms, litterEdit, litterSeason } from './litter.js';
import { wallTone, edgeWear } from './walltone.js';
import { shrubTexture, hedgeMaps, hedgeEdit, HEDGE_KEY, SHRUB_LEAVES, cardEdit, CARD_KEY } from './hedges.js';

const texLoader = new THREE.TextureLoader();
const cache = new Map();
const pending = new Set();
export const texturesReady = () => Promise.all([...pending]);

// Phones: the whole 2K texture set is ~1 GB of GPU memory with mipmaps -> upload smaller copies.
const MOBILE_MAX_TEX = 1024;

// downscale an image so its longest side is at most `max` (returns the image itself if it already fits)
export function shrinkImage(img, max) {
  const w = img && img.width, h = img && img.height;
  if (!w || !h || Math.max(w, h) <= max) return img;
  const s = max / Math.max(w, h);
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(w * s));
  c.height = Math.max(1, Math.round(h * s));
  const x = c.getContext('2d');
  x.imageSmoothingQuality = 'high';
  x.drawImage(img, 0, 0, c.width, c.height);
  return c;
}

// NOTE: flipY=false everywhere -> matches glTF UV convention (v=0 at the top of the image)
export function loadTex(url, { srgb = true, repeat = true, flipY = false, mobileMax = MOBILE_MAX_TEX } = {}) {
  const key = url + srgb + flipY;
  if (!cache.has(key)) {
    let done;
    const pr = new Promise((r) => (done = r));
    pending.add(pr);
    const t = texLoader.load(versioned(url), (tx) => {
      if (MOBILE) { tx.image = shrinkImage(tx.image, mobileMax); tx.needsUpdate = true; }
      // clones share the image Source but keep their own version -> bump them once data exists
      for (const c of tx.userData.clones || []) c.needsUpdate = true;
      pending.delete(pr); done();
    }, undefined, () => { pending.delete(pr); done(); });
    t.userData.clones = [];
    t.flipY = flipY;
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = 8;
    cache.set(key, t);
  }
  return cache.get(key);
}

function tiled(url, tile, srgb) {
  const base = loadTex(url, { srgb });
  const t = base.clone();                         // shares the image Source
  t.repeat.set(1 / tile, 1 / tile);
  if (base.image && base.image.complete !== false && base.image.width) t.needsUpdate = true;
  else base.userData.clones.push(t);
  return t;
}

export const SEASONS = {
  spring: { short: '4월 · 벚꽃', grass: [0.17, 0.25, 0.075], date: "'97 4 15" },
  summer: { short: '5월 · 신록', grass: [0.13, 0.22, 0.06], date: "'97 5 21" },
  autumn: { short: '10월 · 단풍', grass: [0.21, 0.2, 0.08], date: "'97 10 28" },
};
for (const s of Object.values(SEASONS)) s.label = `1997년 ${s.short}`;

// species -> available seasonal atlas suffixes
const LEAF_VARIANTS = {
  ginkgo: ['spring', 'autumn'], zelkova: ['spring', 'autumn'], cherry: ['spring', 'autumn'],
  maple: ['spring', 'autumn'], oak: ['spring', 'autumn'], pine: [], ivy: ['spring', 'autumn'], boxwood: [],
  azalea: ['summer'], azalea_red: [], magnolia: ['spring', 'autumn'], poplar: ['spring', 'autumn'], pansy: [],
};

export function leafUrl(species, season, young = false) {
  const v = LEAF_VARIANTS[species] || [];
  // young trees (1997's lawn planting) still wear April's light, sparse leaves in May
  if (young && season === 'summer' && v.includes('spring')) return `assets/textures/leaf_${species}_spring.png`;
  // 영산홍 · 철쭉 · 진달래: their bloom and their leaves by the month (hedges.js)
  if (species.startsWith('azalea')) return `assets/textures/leaf_${shrubTexture(species, season)}.png`;
  if (v.includes(season)) return `assets/textures/leaf_${species}_${season}.png`;
  return `assets/textures/leaf_${species}.png`;
}

// ---------------------------------------------------------------------------- shader patches
// A material's shader edits stack (one no longer replaces another), and the program cache key names them all: by
// default three keys a program by onBeforeCompile's source text, which is the same for every material with one kind
// of patch whatever values it bakes in (the bark's foliage glow 0 and the leaves' 0.05 could share one program).
const PATCHES = new WeakMap();
export function patchShader(m, key, edit) {
  if (!PATCHES.has(m)) PATCHES.set(m, []);
  const list = PATCHES.get(m);
  // once per material: an instanced copy shares its original's list, a baked copy replays the original's edits (its
  // entry's key names them all)
  if (list.some((p) => p.key.split('|').includes(key))) return;
  list.push({ key, edit });
  m.onBeforeCompile = (sh) => { for (const p of list) p.edit(sh); };
  m.customProgramCacheKey = () => list.map((p) => p.key).join('|');
}

// the same, for a material that may carry a hand-written onBeforeCompile (terrain's, people's): that one becomes the
// first edit of the stack instead of being replaced
export function patchShaderOwn(m, key, edit) {
  if (!PATCHES.has(m) && Object.hasOwn(m, 'onBeforeCompile')) patchShader(m, m.customProgramCacheKey(), m.onBeforeCompile);
  patchShader(m, key, edit);
}

// replace the diffuse map read: `body` gets the texel in sampledDiffuseColor and applies it to diffuseColor
function patchMap(m, key, uniforms, decl, body) {
  patchShader(m, key, (sh) => {
    Object.assign(sh.uniforms, uniforms);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\n${decl}`)
      .replace('#include <map_fragment>', `vec4 sampledDiffuseColor = texture2D( map, vMapUv );${body}`);
  });
}

// ---------------------------------------------------------------------------- wind
// One clock for everything the wind stirs (leaves, branches, the banners' cloth, life.js): main.js sets it every frame.
export const windTime = { value: 0 };

// The static shadow map (shadows.js) is drawn once with nothing displaced (three's shadow pass does not run
// onBeforeCompile either), so a vertex the wind moved looks its shadow up where it rests: a leaf keeps its own light
// and shade instead of swaying in and out of its own shadow. `windW`: the world-space offset the vertex shader added.
export const restShadow = (vs) => vs.replace('#include <shadowmap_vertex>', `
  #ifdef USE_SHADOWMAP
    worldPosition.xyz -= windW;
  #endif
  #include <shadowmap_vertex>
  #ifdef USE_SHADOWMAP
    worldPosition.xyz += windW;
  #endif`);

// Wind in the instanced plants (trees, shrubs; their impostors are rendered from the plain meshes and stay still; the
// ivy merged into the halls has its own, wallWind below): the whole plant leans downwind by the square of the height
// above its foot (h^2/(h^2+60): trunks barely move, crown tips 10-20 cm), two slow sines whose phase runs downwind
// with the plant's position (a gust travels along the 백양로 ginkgo row, neighbours out of step), under a slow gust swell.
// Leaves (flutter: metres) also flutter on their own, shrubs hardly (smoothstep on the height).
function sway(m, flutter) {
  patchShader(m, `sway${flutter}`, (sh) => {
    sh.uniforms.uWindT = windTime;
    sh.vertexShader = restShadow(sh.vertexShader
      .replace('#include <common>', `#include <common>
        uniform float uWindT;
        vec3 windSway(vec3 o, vec3 r) {
          const vec2 dir = vec2(0.92, -0.38);                     // towards the east-north-east (three xz)
          float h = max(r.y, 0.0), t = uWindT;
          float along = dot(o.xz, dir);
          float ph = along * 0.2 + sin(o.x * 0.37 + o.z * 0.53) * 1.6;
          float gust = 0.7 + 0.3 * sin(t * 0.21 - along * 0.01);
          float bend = 0.22 * h * h / (h * h + 60.0) * gust;
          float s = 0.7 * sin(t * 1.1 - ph) + 0.3 * sin(t * 2.3 - ph * 1.7 + 1.3);   // downwind
          float c = 0.3 * sin(t * 1.7 - ph * 0.8 + 2.1);                            // across
          vec3 w = vec3(dir.x * s - dir.y * c, 0.0, dir.y * s + dir.x * c) * bend;
          ${flutter > 0 ? `float f = dot(r, vec3(1.7, 1.1, 2.3)) + ph;
          w += vec3(sin(t * 4.3 + f), 0.5 * sin(t * 3.7 + f * 1.3), sin(t * 5.1 + f * 0.8 + 1.0))
            * (${flutter.toFixed(3)} * smoothstep(0.3, 5.0, h) * gust);` : ''}
          return w;
        }`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vec3 windW = vec3(0.0);
        #ifdef USE_INSTANCING
        {
          mat3 im = mat3(instanceMatrix);                         // a turn about the vertical and a uniform scale
          windW = windSway(instanceMatrix[3].xyz, im * position);
          transformed += transpose(im) * windW / dot(im[0], im[0]);
        }
        #endif`));
  });
}

// Wind in the ivy merged into the stone halls, which has no instance to take a height and a phase from: each corner
// of a leaf card carries them (blender/landmarks.py ivy_patch, in the baked attribute): bake.r the card's phase,
// 1 - bake.g how far the corner hangs below the card's stalk (m) times how loose the card is. The lower corners lift
// off the wall and swing along it, 3-5 cm at the tips of the cards, under the trees' slow gust swell, a gust running
// downwind across the wall in a wave; nothing moves where the attribute is white (a mesh without it).
const WALL_WIND = /* glsl */`
{
  float ivW = 1.0 - bake.g;
  if (ivW > 0.0) {
    const vec2 dir = vec2(0.92, -0.38);
    float t = uWindT, ph = bake.r * 6.2832;
    vec3 n = normalize(objectNormal);
    vec3 side = cross(vec3(0.0, 1.0, 0.0), n);
    side = dot(side, side) > 1e-4 ? normalize(side) : vec3(1.0, 0.0, 0.0);
    vec3 wp = (modelMatrix * vec4(transformed, 1.0)).xyz;
    float along = dot(wp.xz, dir);
    float gust = (0.7 + 0.3 * sin(t * 0.21 - along * 0.01)) * (0.75 + 0.25 * sin(t * 1.3 - along * 0.35));
    float sp = 1.0 + 0.25 * fract(bake.r * 7.13);                 // cards out of step in speed too
    float lift = 0.6 * sin(t * 3.9 * sp + ph) + 0.4 * sin(t * 6.3 * sp + ph * 2.0 + 1.0);
    float swing = sin(t * 2.7 * sp + ph * 1.7);
    vec3 ivD = (n * lift * 0.8 + side * swing * 0.5) * (ivW * 0.06 * gust);
    transformed += ivD;
    windW += mat3(modelMatrix) * ivD;
  }
}`;

function wallWind(m) {
  patchShader(m, 'wallWind', (sh) => {
    sh.uniforms.uWindT = windTime;
    let vs = sh.vertexShader;
    if (!vs.includes('attribute vec4 bake;')) vs = vs.replace('#include <common>', '#include <common>\nattribute vec4 bake;');
    if (!vs.includes('uniform float uWindT;')) vs = vs.replace('#include <common>', '#include <common>\nuniform float uWindT;');
    if (!vs.includes('vec3 windW')) vs = restShadow(vs.replace('#include <begin_vertex>', '#include <begin_vertex>\nvec3 windW = vec3(0.0);'));
    sh.vertexShader = vs.replace('#include <project_vertex>', `${WALL_WIND}\n#include <project_vertex>`);
  });
}

// Foliage: a touch of glow so canopies don't go black (the sky's light through the leaves; the sun's is backlight
// below), and a dithered fade close to the camera so the third-person camera never looks through a wall of leaves or
// a trunk; the wind (sway).
// With TAA on (post.js) the dither runs through its thresholds frame by frame, so the history blends it into a smooth
// fade instead of a fixed screen-door pattern; 0 otherwise (a still pattern does not crawl).
export const DITHER = { value: 0 };
function foliage(m, glow = 0.09, flutter = 0.03) {
  sway(m, flutter);
  patchShader(m, `foliage${glow}`, (sh) => {
    sh.uniforms.uDither = DITHER;
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float uDither;')
      .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>
        {
          float camD = length(vViewPosition);
          float keep = smoothstep(1.2, 3.4, camD);
          vec2 q = floor(gl_FragCoord.xy);
          float dither = fract(dot(q, vec2(0.0671, 0.00584)) * 52.98 + uDither);
          if (keep < 0.999 && dither > keep) discard;
        }`)
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
       totalEmissiveRadiance += diffuseColor.rgb * ${glow.toFixed(3)};`);
  });
}

// Leaves: the sunlight through a leaf, seen from its shaded side. A leaf card lit from behind (the sun on the other
// side of the face that is seen) passes on a share of it, more saturated, mostly forward: strongest looking towards
// the sun through the canopy. The face is the card's own, from screen derivatives (the leaf normals are bent to the
// crown's sphere, and one side of a card reads them flipped).
// The light is the sun as three's light loop left it (directLight after the loop: the shadow map or the baked sun
// shadow, and the cloud over the pixel already in its colour), so a leaf in the shade of a hall stays dark. Inside a
// crown the leaves in front pass some of it on, scattered: in the shadow map, the depth of the crown between the leaf
// and the sun (to the first caster along the ray, one tap) fades it out over a few metres, so the underside of a
// canopy glows faintly and a leaf a hall shades from metres away does not. Without the map (phones, and beyond its
// edge) the crown's normal stands in: the farther the leaf is round the crown from the sun, the less reaches it.
// The leaves' even glow (foliage) is what is left for the sky's light: LEAF_GLOW. The impostor renders (world.js: no
// fog, a light of their own, cards seen from every side later) keep the glow the leaves had before, LEAF_GLOW_FLAT,
// so the far trees stay as bright as the near ones on average.
// uBacklight: x diffuse share, y forward share, z exponent of the forward lobe, w falloff round the crown (no map);
// uBacklightIn: x share scattered on through the crown, y its falloff (m).
const LEAF_GLOW = 0.05, LEAF_GLOW_FLAT = 0.09;
export const BACKLIGHT = { lobe: { value: new THREE.Vector4(0.3, 1.2, 4, 3) }, through: { value: new THREE.Vector2(0.8, 3) } };
function backlight(m) {
  patchShader(m, 'backlight', (sh) => {
    sh.uniforms.uBacklight = BACKLIGHT.lobe;
    sh.uniforms.uBacklightIn = BACKLIGHT.through;
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform vec4 uBacklight;
        uniform vec2 uBacklightIn;
        #if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
        uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];   // (the vertex shader's: map depth per metre)
        #endif`)
      .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
        #if NUM_DIR_LIGHTS > 0
        {
          vec3 blL = directLight.direction;
          vec3 blF = normalize( cross( dFdx( vViewPosition ), dFdy( vViewPosition ) ) );
          blF = dot( blF, geometryViewDir ) < 0.0 ? - blF : blF;
          float blW = saturate( - dot( blF, blL ) )
            * ( uBacklight.x + uBacklight.y * pow( saturate( - dot( geometryViewDir, blL ) ), uBacklight.z ) );
          vec3 blSun = directLight.color * exp( - uBacklight.w * saturate( - dot( normalize( vNormal ), blL ) ) );
          #if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
          vec3 blSc = vDirectionalShadowCoord[ 0 ].xyz / vDirectionalShadowCoord[ 0 ].w;
          vec2 blE = min( blSc.xy, 1.0 - blSc.xy );
          float blIn = smoothstep( 0.0, 0.04, min( blE.x, blE.y ) ) * step( blSc.z, 1.0 );
          if ( blIn > 0.0 ) {
            mat4 blM = directionalShadowMatrix[ 0 ];
            float blGap = max( 0.0, blSc.z - unpackRGBAToDepth( texture2D( directionalShadowMap[ 0 ], blSc.xy ) ) )
              / length( vec3( blM[ 0 ][ 2 ], blM[ 1 ][ 2 ], blM[ 2 ][ 2 ] ) );
            vec3 blOpen = directionalLights[ 0 ].color;          // the sun before the shadow map
            #if defined( USE_FOG ) && defined( Y97_ATMOS )
            blOpen *= y97CloudHere();
            #endif
            #ifdef SUN_MODE
            blOpen *= bakedSun;
            #endif
            blSun = mix( blSun, max( directLight.color, blOpen * uBacklightIn.x * exp( - blGap / uBacklightIn.y ) ), blIn );
          }
          #endif
          vec3 blC = diffuseColor.rgb;
          blC *= mix( vec3( 1.0 ), blC / max( max( blC.r, blC.g ), max( blC.b, 1e-4 ) ), 0.5 );
          reflectedLight.directDiffuse += blSun * BRDF_Lambert( blC ) * blW;
        }
        #endif
        #ifndef USE_FOG
        totalEmissiveRadiance += diffuseColor.rgb * ${(LEAF_GLOW_FLAT - LEAF_GLOW).toFixed(3)};
        #endif`);
  });
}

// Window glass (materials.json `rooms`): a room behind every pane, the sky over it by Fresnel. Blender gives window
// glass pane UVs (blender/common.py pane_uv): the whole part names a pane (a random number per window), the fraction
// runs across it, and v from 32 marks a hall behind tall glazing. Each pane takes a cell of the room atlas
// (tools/make_window_atlas.py: rows 0-2 rooms, row 3 halls), lit like a surface just behind the glass, or by its own
// light where the lights are on. The glass reflects the environment by Fresnel (ior 1.5, both faces of a pane: F0 ~
// 0.08), every pane tilted a hair so that neighbours mirror a different patch of sky. three ignores envMapIntensity
// with scene.environment, so the glass scales its own IBL radiance.
// A sash window (u from 64: the generic halls' ordinary windows; its room is picked from u - 64 mod 24) has, in one of
// OPEN_P, a sash slid open: on the half the pane's hash names, under the transom (v fraction < TRANSOM), there is no
// glass -- no reflection, the room dim and untinted behind the opening, which blender/windows.py sets back into the
// room. Blender picks the same windows with the same hash (blender/common.py SASH, OPEN_P, TRANSOM, pane_open).
// v < 0: a dark opening with neither glass nor room (an air conditioner's fan behind its grille).
// a room pane's cell: dark rooms, blinds and pale green curtains (학생회관) more often; 8, 13, 15 have the lights on
const ROOM_CELLS = '0, 0, 1, 1, 2, 3, 4, 5, 6, 6, 7, 8, 9, 10, 11, 11';
function windowGlass(d) {
  const m = new THREE.MeshPhysicalMaterial({
    map: loadTex('assets/textures/' + d.rooms, { repeat: false }),
    roughness: d.rough ?? 0.05,
    metalness: 0,
    ior: 1.5,
  });
  // both faces of the pane reflect (F0 0.04 each); the back face's light crosses the tinted glass (학생회관's green).
  // A coated (heat-reflecting) glass mirrors more, `f0` square on, in its own tint (대강당's pale green panes)
  const t = new THREE.Color(...(d.tint || [0.66, 0.69, 0.69]));
  const tm = Math.max(t.r, t.g, t.b);
  const f0 = d.f0 ?? 0.08;
  if (d.f0) m.specularColor.setRGB(t.r / tm, t.g / tm, t.b / tm).multiplyScalar(f0 / 0.04);
  else m.specularColor.setRGB(1 + t.r / tm, 1 + t.g / tm, 1 + t.b / tm);
  const u = {
    uRoomTint: { value: t },                       // what the (dusty) glass lets through
    uRoomLit: { value: d.lit ?? 0.45 },            // a room with the lights on
    uGlassEnv: { value: d.env ?? 2.0 },            // the reflection, x scene.environmentIntensity
    uRoomOpen: { value: 0.3 },                     // the room through an open sash (no glass, in the shade inside)
    uGlassF0: { value: f0 },                       // reflectance square on
  };
  m.userData.rooms = u;                            // (to tune from the console)
  patchShader(m, d.f0 ? 'roomsC' : 'rooms', (sh) => {
    Object.assign(sh.uniforms, u);
    if (d.f0) sh.defines = { ...sh.defines, GLASS_COATED: '' };
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform vec3 uRoomTint;
        uniform float uRoomLit, uGlassEnv, uRoomOpen, uGlassF0;
        const int ROOM_CELLS[16] = int[16](${ROOM_CELLS});
        const float SASH_U = 64.0, OPEN_P = 0.07, TRANSOM = 0.715;
        uint paneMix(uint n) { n ^= n >> 16; n *= 0x7feb352du; n ^= n >> 15; n *= 0x846ca68bu; n ^= n >> 16; return n; }
        float paneHash(vec2 p, uint k) {
          uvec2 q = uvec2(ivec2(p) + 4096);
          return float(paneMix(q.x * 1973u + q.y * 9277u + k * 26699u) >> 8) / 16777216.0;
        }`)
      .replace('#include <map_fragment>', `
        vec2 paneUv = vec2(vMapUv.x, 1.0 - vMapUv.y);              // (glTF flips v)
        vec2 pane = floor(paneUv), fp = fract(paneUv);
        bool paneDark = paneUv.y < 0.0;
        float paneOpen = paneDark || (pane.x > SASH_U - 0.5 && pane.y < 31.5 && paneHash(pane, 7u) < OPEN_P
          && (paneHash(pane, 8u) < 0.5 ? fp.x < 0.5 : fp.x > 0.5) && fp.y < TRANSOM) ? 1.0 : 0.0;
        vec2 roomPane = pane.x > SASH_U - 0.5 ? vec2(mod(pane.x - SASH_U, 24.0), pane.y) : pane;
        int cell = pane.y > 31.5 ? 12 + int(paneHash(roomPane, 1u) * 4.0) : ROOM_CELLS[int(paneHash(roomPane, 1u) * 16.0)];
        if (paneHash(roomPane, 2u) < 0.5) fp.x = 1.0 - fp.x;            // mirrored rooms: twice the variety
        vec2 cuv = (vec2(float(cell % 4), float(cell / 4)) + 0.02 + vec2(fp.x, 1.0 - fp.y) * 0.96) * 0.25;
        // gradients of the continuous uv: no mip seam where the fraction wraps between two panes of one face
        vec3 room = textureGrad(map, cuv, dFdx(paneUv) * 0.24, dFdy(paneUv) * 0.24).rgb;
        room *= mix(uRoomTint, vec3(uRoomOpen), paneOpen) * (0.75 + 0.5 * paneHash(roomPane, 3u));
        if (paneDark) room = vec3(0.012);
        float glassF = (1.0 - paneOpen) * (uGlassF0 + (1.0 - uGlassF0) * pow(1.0 - saturate(abs(dot(normalize(vNormal), normalize(vViewPosition)))), 5.0));
        float roomOn = !paneDark && (cell == 8 || cell == 13 || cell == 15) ? 1.0 : 0.0;
        diffuseColor.rgb = room * (1.0 - roomOn) * (1.0 - glassF);
        vec3 roomGlow = room * roomOn * uRoomLit * (1.0 - glassF);
        vec3 paneTilt = (vec3(paneHash(roomPane, 4u), paneHash(roomPane, 5u), paneHash(roomPane, 6u)) - 0.5) * 0.05;`)
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
        normal = normalize(normal + mat3(viewMatrix) * paneTilt);`)
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
        totalEmissiveRadiance += roomGlow;`)
      .replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
        material.specularColor *= 1.0 - paneOpen;                  // (no glass: neither the sun's nor the sky's gleam)
        material.specularF90 *= 1.0 - paneOpen;`)
      .replace('#include <lights_fragment_maps>', `#include <lights_fragment_maps>
        // the HDRI's horizon is open haze; the campus's is trees and buildings: dim what the glass mirrors low
        vec3 glassR = (vec4(reflect(-geometryViewDir, geometryNormal), 0.0) * viewMatrix).xyz;
        radiance *= uGlassEnv * mix(0.35, 1.0, smoothstep(-0.05, 0.4, glassR.y));`);
  });
  return m;
}

// Halls and landmarks: the per-corner data blender/bake.py writes (attribute `bake`, RGBA; a mesh without it reads
// white, i.e. open and under no ledge):
//   R  ambient occlusion by the buildings within 10 m -> only the light from the sky and the ground (hemisphere,
//      environment) is taken away, never the sun: the arcade of 중앙도서관, the pilotis of 학생회관 and the deep porch
//      of 백주년기념관 go dim in their own shade, and stay lit where the sun reaches into them
//   G  depth under the ledge above in fade lengths / 16, B position along that ledge (u + 8) / 16
// -> weathering: soil splashed up the foot of the walls (their height over the terrain the walker sees: setTerrain),
// rain streaks down from sills, copings and bands, grime on the faces that look up, scaled by the material's
// `weather` (materials.json) and the building's age (GLB extras `weather`: 대우관 was new in 1996)
const BAKE_VERT = /* glsl */`
attribute vec4 bake;
uniform sampler2D uTerrain;
uniform vec3 uTerrainGrid;
varying vec4 vBake;
varying vec3 vBakeW;
varying float vBakeH;
float bkGround(vec2 p) {
  vec2 f = clamp((p + uTerrainGrid.x) / uTerrainGrid.y, vec2(0.0), vec2(uTerrainGrid.z - 1.001));
  ivec2 i = ivec2(f);
  vec2 a = f - vec2(i);
  float h00 = texelFetch(uTerrain, i, 0).r, h10 = texelFetch(uTerrain, i + ivec2(1, 0), 0).r;
  float h01 = texelFetch(uTerrain, i + ivec2(0, 1), 0).r, h11 = texelFetch(uTerrain, i + ivec2(1, 1), 0).r;
  // (the two triangles of each cell, as terrain.js draws them)
  return a.x + a.y <= 1.0 ? h00 + (h10 - h00) * a.x + (h01 - h00) * a.y
                          : h11 + (h01 - h11) * (1.0 - a.x) + (h10 - h11) * (1.0 - a.y);
}`;
const BAKE_FRAG = /* glsl */`
varying vec4 vBake;
varying vec3 vBakeW;
varying float vBakeH;
uniform float uBakeAO;
uniform float uWeather;
float bkHash(vec3 p) { p = fract(p * 0.1031); p += dot(p, p.zyx + 31.32); return fract((p.x + p.y) * p.z); }
float bkNoise(vec3 x) {
  vec3 i = floor(x), f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(bkHash(i), bkHash(i + vec3(1, 0, 0)), f.x), mix(bkHash(i + vec3(0, 1, 0)), bkHash(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(bkHash(i + vec3(0, 0, 1)), bkHash(i + vec3(1, 0, 1)), f.x), mix(bkHash(i + vec3(0, 1, 1)), bkHash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}`;
// (world y is up: three's frame of the campus)
const BAKE_WEATHER = /* glsl */`
#ifdef BAKE_WEATHER
#ifdef BAKE_LITE
  #define bkDetail(p) 0.5
#else
  #define bkDetail(p) bkNoise(p)
#endif
{
  vec3 wN = inverseTransformDirection(nonPerturbedNormal, viewMatrix);
  vec3 P = vBakeW;
  float wall = 1.0 - smoothstep(0.35, 0.7, abs(wN.y));
  // soil splashed up the foot of the walls: darker and yellower, its top ragged
  float h = vBakeH, base = 0.0;
  if (h < 1.4) {
    float nb = bkNoise(P * vec3(1.1, 0.4, 1.1)) * 0.65 + bkDetail(P * 4.0) * 0.35;
    base = pow(1.0 - smoothstep(0.0, 0.35 + 0.9 * nb, h), 1.3) * wall;
  }
  // rain streaks down from the ledge above: a film under its whole width and darker columns, each running its own
  // length
  float dl = vBake.g * 16.0, ul = vBake.b * 16.0 - 8.0, streak = 0.0;
  if (dl < 1.0 && abs(ul) < 1.05) {
    float c1 = bkNoise(vec3(P.x * 5.0, P.y * 0.18, P.z * 5.0));
    float c2 = bkDetail(vec3(P.x * 14.0, P.y * 0.4, P.z * 14.0));
    float run = 1.0 - smoothstep(0.0, 0.45 + 0.55 * c1, dl);
    streak = (1.0 - smoothstep(0.7, 1.05, abs(ul))) * sqrt(run)
           * (0.55 + 0.45 * smoothstep(0.25, 0.65, c1 * 0.6 + c2 * 0.4)) * wall;
  }
  // grime where water stands and dust settles: sill tops, copings, ledges
  float up = 0.0;
  if (wN.y > 0.6) up = smoothstep(0.6, 0.9, wN.y) * smoothstep(0.35, 0.75, bkNoise(P * 1.9) * 0.6 + bkDetail(P * 7.0) * 0.4);
  // and broad uneven weathering, more of it in the corners the rain and the sun do not reach
  float broad = bkNoise(P * vec3(0.3, 0.8, 0.3)) - 0.5;
  float grime = clamp(up * 0.6 + broad * 0.18 + (1.0 - vBake.r) * 0.2, 0.0, 1.0);
  diffuseColor.rgb *= mix(vec3(1.0), vec3(0.58, 0.53, 0.46), base * uWeather);
  diffuseColor.rgb *= mix(vec3(1.0), vec3(0.44, 0.43, 0.42), streak * uWeather);
  diffuseColor.rgb *= mix(vec3(1.0), vec3(0.7, 0.69, 0.66), grime * uWeather);
}
#endif`;
// what aomap_fragment does with an AO map, with the baked value: the indirect light only
const BAKE_AO = /* glsl */`
{
  float bkAO = 1.0 - uBakeAO * (1.0 - vBake.r);
  reflectedLight.indirectDiffuse *= bkAO;
  // (a coated glass mirrors the sky over the walker, which neither the porch below nor the shallow reveals hide)
  #if defined( USE_ENVMAP ) && defined( STANDARD ) && !defined( GLASS_COATED )
    float bkNV = saturate( dot( geometryNormal, geometryViewDir ) );
    reflectedLight.indirectSpecular *= computeSpecularOcclusion( bkNV, bkAO, material.roughness );
  #endif
}`;

// a copy of a library material for meshes with the baked attribute (white where one has none), with the original's
// shader edits looked up at compile time first: also those made later (the season's, the baked sun shadow's)
function bakedCopy(m) {
  const v = m.clone();
  v.userData = { ...m.userData, baked: true };
  v.defaultAttributeValues = { bake: [1, 1, 1, 1] };
  // (one the copy was given itself as well, by whichever came first - the baked sun shadow's, from main.js - is not
  // replayed from the original)
  const mine = () => PATCHES.get(v).slice(1).map((p) => p.key);
  PATCHES.set(v, [{ get key() { return (PATCHES.get(m) || []).map((p) => p.key).join('|'); },
    edit: (sh) => { const own = mine(); for (const p of PATCHES.get(m) || []) if (!own.includes(p.key)) p.edit(sh); } }]);
  if (!PATCHES.has(m)) PATCHES.set(m, []);
  return v;
}

// a copy of a material that takes shader edits of its own (patchShader on it) after the original's, looked up at
// compile time as bakedCopy's are (impostors.js: the forest's near trees)
export function derivedCopy(m) {
  const v = m.clone();
  const mine = () => PATCHES.get(v).slice(1).map((p) => p.key);
  PATCHES.set(v, [{ get key() { return (PATCHES.get(m) || []).map((p) => p.key).join('|'); },
    edit: (sh) => { const own = mine(); for (const p of PATCHES.get(m) || []) if (!own.includes(p.key)) p.edit(sh); } }]);
  if (!PATCHES.has(m)) PATCHES.set(m, []);
  return v;
}

function bakeShade(m, uniforms, weather) {
  patchShader(m, weather ? 'bakeW' : 'bake', (sh) => {
    Object.assign(sh.uniforms, uniforms);
    if (weather) sh.defines = { ...sh.defines, BAKE_WEATHER: '', ...(MOBILE ? { BAKE_LITE: '' } : {}) };
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>${BAKE_VERT}`)
      .replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
        vBake = bake;
        vBakeW = (modelMatrix * vec4(transformed, 1.0)).xyz;
        vBakeH = vBakeW.y - bkGround(vec2(vBakeW.x, -vBakeW.z));`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>${BAKE_FRAG}`)
      .replace('#include <lights_physical_fragment>', `${BAKE_WEATHER}\n#include <lights_physical_fragment>`)
      .replace('#include <aomap_fragment>', `#include <aomap_fragment>${BAKE_AO}`);
  });
}

export class MaterialLibrary {
  constructor(defs) {
    this.defs = defs;
    this.mats = new Map();
    this.instancedMats = new Map();
    this.bakedMats = new Map();
    this.leafMats = [];
    this.season = 'summer';
    this.uniforms = { uGrass: { value: new THREE.Color(...SEASONS.summer.grass) }, uWindT: windTime, uBakeAO: { value: 1.0 },
      uTerrain: { value: null }, uTerrainGrid: { value: new THREE.Vector3(0, 1, 1) } };
    Object.assign(this.uniforms, litterUniforms(loadTex));     // the month's fallen leaves (litter.js)
    this.setTerrain({ data: new Float32Array(4).fill(-1e4), half: 0, step: 1, n: 2 });
  }

  // the near terrain's heights (web/src/terrain.js Heightfield) for the baked materials: how high each wall is
  setTerrain(hf) {
    const t = new THREE.DataTexture(hf.data, hf.n, hf.n, THREE.RedFormat, THREE.FloatType);
    t.needsUpdate = true;
    this.uniforms.uTerrain.value = t;
    this.uniforms.uTerrainGrid.value.set(hf.half, hf.step, hf.n);
  }

  // The halls' and landmarks' copy of a library material, reading their baked attribute (see BAKE_VERT above);
  // age scales the material's weathering (a building's GLB extras). It keeps the original's name and its shader
  // edits, also those made later. The leaves (ivy) take no shade from it but their wind (wallLeaf).
  baked(m, age = 1) {
    if (this.mats.get(m.name) !== m || !m.isMeshStandardMaterial) return m;
    if (m.vertexColors) return this.leafMats.includes(m) ? this.wallLeaf(m) : m;
    const key = `${m.name}|${age}`;
    let v = this.bakedMats.get(key);
    if (!v) {
      v = bakedCopy(m);
      const weather = (this.defs[m.name]?.weather ?? 0) * age;
      const { uBakeAO, uTerrain, uTerrainGrid } = this.uniforms;
      v.userData.uWeather = { value: weather };
      bakeShade(v, { uBakeAO, uTerrain, uTerrainGrid, uWeather: v.userData.uWeather }, weather > 0);
      const edge = edgeWear(this.defs[m.name]);               // worn arrises (walltone.js)
      if (edge) { patchShader(v, edge.key, edge.edit); v.defaultAttributeValues.edge = edge.none; }
      this.bakedMats.set(key, v);
    }
    return v;
  }

  // The leaves merged into the halls (the ivy): their baked attribute is the wind of each corner (WALL_WIND), not a
  // colour, so the copy drops the vertex colours; it follows the season's leaf textures like the original
  wallLeaf(m) {
    const key = `${m.name}|wall`;
    let v = this.bakedMats.get(key);
    if (!v) {
      v = bakedCopy(m);
      v.vertexColors = false;
      v.userData.wallLeaf = true;      // (its bake is wind, not shade: no SUN_WALL, bakedshadow.js)
      wallWind(v);
      this.leafMats.push(v);
      this.bakedMats.set(key, v);
    }
    return v;
  }

  // three keeps one compiled-program slot per material. One drawn both by plain meshes and by InstancedMeshes (the
  // metal of a building's railings and of the instanced lamps, the parked and the moving cars' parts) has its program
  // looked up again at every switch between the two, many times a frame. Instanced kits (world.js) draw with their
  // own copy, kept in step with the original (the season's leaf textures).
  instanced(m) {
    if (this.mats.get(m.name) !== m) return pcss(m);    // not a library material (a prop's own)
    let v = this.instancedMats.get(m);
    if (!v) {
      v = m.clone();
      v.onBeforeCompile = m.onBeforeCompile;            // (clone() keeps neither)
      v.customProgramCacheKey = m.customProgramCacheKey;
      // the copy shares the original's patch list: a patch added to either later (the baked sun shadow's, from
      // main.js) lands once in the shared list instead of once there and once more on the copy
      if (PATCHES.has(m)) PATCHES.set(v, PATCHES.get(m));
      this.instancedMats.set(m, v);
      if (this.leafMats.includes(m)) this.leafMats.push(v);
    }
    return v;
  }

  get(name) {
    if (this.mats.has(name)) return this.mats.get(name);
    const d = this.defs[name];
    let m;
    if (!d) {
      m = new THREE.MeshStandardMaterial({ color: 0xff00ff });
      console.warn('unknown material', name);
    } else if (d.tex) {
      const base = `assets/textures/pbr/${d.tex}/`;
      m = new THREE.MeshStandardMaterial({
        map: tiled(base + 'diff.jpg', d.tile, true),
        normalMap: tiled(base + 'nor.jpg', d.tile, false),
        roughnessMap: tiled(base + 'rough.jpg', d.tile, false),
        roughness: 1.0,
        color: new THREE.Color(...(d.tint || [1, 1, 1])),
        side: THREE.DoubleSide,
      });
      m.normalScale.set(d.nor ?? 0.9, d.nor ?? 0.9);
      if (d.recolor) {
        // grass: keep the texture's detail, but drive the hue from the seasonal colour
        patchMap(m, 'recolor', { uGrass: this.uniforms.uGrass }, 'uniform vec3 uGrass;', `
          float lum = dot(sampledDiffuseColor.rgb, vec3(0.299, 0.587, 0.114));
          diffuseColor.rgb = uGrass * (0.45 + 1.6 * lum);`);
      } else if (d.sat !== undefined) {
        // grey down a warm photo texture (e.g. the 1997 granite / concrete of 공학관, 중앙도서관, 백주년기념관)
        patchMap(m, 'sat', { uSat: { value: d.sat } }, 'uniform float uSat;', `
          float lumS = dot(sampledDiffuseColor.rgb, vec3(0.299, 0.587, 0.114));
          sampledDiffuseColor.rgb = mix(vec3(lumS), sampledDiffuseColor.rgb, uSat);
          diffuseColor *= sampledDiffuseColor;`);
      } else if (d.contrast !== undefined) {
        // tone a texture's detail down towards its own average colour (the 1997 roads' even asphalt)
        patchMap(m, 'contrast', { uContrast: { value: d.contrast } }, 'uniform float uContrast;', `
          sampledDiffuseColor.rgb = mix(texture2D( map, vMapUv, 9.0 ).rgb, sampledDiffuseColor.rgb, uContrast);
          diffuseColor *= sampledDiffuseColor;`);
      }
      if (name.startsWith('bark')) foliage(m, 0.0, 0);         // trunks and branches bend with the leaves, no flutter
      if (LITTER_MATS.has(name)) patchShader(m, 'litter', litterEdit(this.uniforms));
      const wall = wallTone(name, d, ATMOS.uCloudTex);         // walls: broad and per-panel tone, no repeat
      if (wall) patchShader(m, wall.key, wall.edit);
    } else if (d.leaf) {
      const species = d.leaf;
      const hedge = d.opaque && hedgeMaps(species, this.season);   // a clipped shrub's body (hedges.js)
      m = new THREE.MeshStandardMaterial({
        map: loadTex(hedge ? hedge.map : leafUrl(species, this.season, !!d.young), { repeat: !!d.opaque }),
        alphaTest: d.opaque ? 0 : 0.42,
        transparent: false,
        side: THREE.DoubleSide,
        roughness: 0.82,
        vertexColors: true,
        color: new THREE.Color(...(d.tint || [1, 1, 1])),
      });
      m.userData.species = species;
      m.userData.opaque = !!d.opaque;
      m.userData.young = !!d.young;
      m.userData.tint = d.tint || [1, 1, 1];
      m.userData.tintAutumn = d.tintAutumn || m.userData.tint;
      // (a clipped hedge's solid body does not flutter, nor does the sun shine through it)
      foliage(m, d.opaque ? LEAF_GLOW_FLAT : LEAF_GLOW, d.opaque ? 0 : 0.03);
      if (!d.opaque) {
        backlight(m);
        if (SHRUB_LEAVES.has(species)) patchShader(m, CARD_KEY, cardEdit);    // (a shrub's sprigs: hedges.js)
      } else {
        m.userData.hedge = true;
        if (hedge.normal) m.normalMap = loadTex(hedge.normal, { srgb: false });
        patchShader(m, HEDGE_KEY, hedgeEdit(species));
      }
      this.leafMats.push(m);
    } else if (d.rooms) {
      m = windowGlass(d);
    } else if (d.image) {
      m = new THREE.MeshStandardMaterial({ map: loadTex('assets/textures/' + d.image, { repeat: false }), roughness: d.rough ?? 0.6 });
      if (d.emissiveMap) {
        m.emissiveMap = m.map;
        m.emissive = new THREE.Color(0.35, 0.35, 0.35);
      }
    } else {
      const P = d.clearcoat ? THREE.MeshPhysicalMaterial : THREE.MeshStandardMaterial;
      m = new P({
        color: new THREE.Color(...(d.color || [0.8, 0.8, 0.8])),
        roughness: d.rough ?? 0.8,
        metalness: d.metal ?? 0,
        side: d.side === 'double' ? THREE.DoubleSide : THREE.FrontSide,
      });
      if (d.clearcoat) { m.clearcoat = d.clearcoat; m.clearcoatRoughness = d.clearcoatRough ?? 0.08; }
      if (d.opacity !== undefined) { m.transparent = true; m.opacity = d.opacity; m.depthWrite = false; }
      if (d.emissive) {
        m.emissive = new THREE.Color(...d.emissive);
        m.emissiveIntensity = d.emissiveIntensity ?? 1;
      }
      if (name.startsWith('glass')) {
        m.metalness = 0.35;
        m.envMapIntensity = d.env ?? 1.5;
      }
    }
    pcss(m);
    m.name = name;
    globalPatch(m);
    this.mats.set(name, m);
    return m;
  }

  setSeason(season) {
    this.season = season;
    this.uniforms.uGrass.value.setRGB(...SEASONS[season].grass);
    litterSeason(this.uniforms, season);                      // the month's fallen leaves or petals
    for (const m of this.leafMats) {
      if (m.userData.hedge) {
        const h = hedgeMaps(m.userData.species, season);
        m.map = loadTex(h.map);
        if (m.normalMap) m.normalMap = loadTex(h.normal, { srgb: false });
      } else m.map = loadTex(leafUrl(m.userData.species, season, m.userData.young), { repeat: m.userData.opaque });
      m.color.setRGB(...(season === 'autumn' ? m.userData.tintAutumn : m.userData.tint));
      m.needsUpdate = true;
    }
  }
}

// ---------------------------------------------------------------------------- contact-hardening sun shadows (PCSS)
// The sun is a disc 0.53° across, so a shadow's penumbra widens with the gap between what casts it and what it falls
// on: sharp at a walker's feet and the foot of a trunk, softer under a high canopy or off a roof edge. three's
// webgl_shadowmap_pcss example (blocker search -> penumbra estimate -> filter of that radius), for the sun's
// orthographic shadow camera: map depth is linear, so the penumbra radius is just the blocker-receiver gap along the
// light times tan(0.265°). Taps compare against the receiver's own plane (slope from screen derivatives), so the
// search disc, wider than the old PCF kernel, does not find the ground itself on sloped and grazing-lit faces; the
// filter's taps are bilinear so the penumbra stays smooth without noise. Desktop HQ only (updatePcss, from main.js);
// the static shadow cache (shadows.js) keeps the same depth map, so it works unchanged.
export const PCSS = {
  sunDeg: 0.53,       // the sun's angular diameter
  reach: 45,          // farthest blocker considered, metres along the light (the tallest halls and trees, sun at ~48°)
  minTexels: 0.5,     // smallest filter radius: below this the map's texels would show as steps
  uniform: { value: new THREE.Vector4() },  // x: radius (uv) per unit of map depth (0: off), y: search radius (uv),
};                                          // z: smallest radius (uv), w: largest |d depth / d uv| of a receiver plane

const vogel = (n) => Array.from({ length: n }, (_, i) => {
  const r = Math.sqrt((i + 0.5) / n), a = i * 2.39996323;
  return `vec2(${(r * Math.cos(a)).toFixed(4)}, ${(r * Math.sin(a)).toFixed(4)})`;
}).join(', ');

// Fetches per pixel: 4 + PCSS_RING to find the blockers (the old PCFSoft kernel read 16), and only in a penumbra
// 4 * PCSS_TAPS more for the filter (its centre tap reuses the search's four texels).
const PCSS_RING = 8, PCSS_TAPS = 6;
const PCSS_CHUNK = THREE.ShaderChunk.shadowmap_pars_fragment.replace('float getShadow(', 'float getShadowPCF(') + /* glsl */`
#ifdef USE_SHADOWMAP
  uniform vec4 uPcss;
  const vec2 PCSS_RING[ ${PCSS_RING} ] = vec2[]( ${vogel(PCSS_RING)} );
  const vec2 PCSS_TAPS[ ${PCSS_TAPS} ] = vec2[]( ${vogel(PCSS_TAPS)} );
  // depth test of one point, bilinear over the four texels round it
  float pcssTap( sampler2D map, vec2 size, vec2 uv, float z ) {
    vec2 t = uv * size - 0.5, f = fract( t ), e = 1.0 / size, b = ( floor( t ) + 0.5 ) * e;
    vec4 s = step( vec4( z ), vec4(
      unpackRGBAToDepth( texture2D( map, b ) ), unpackRGBAToDepth( texture2D( map, b + vec2( e.x, 0.0 ) ) ),
      unpackRGBAToDepth( texture2D( map, b + vec2( 0.0, e.y ) ) ), unpackRGBAToDepth( texture2D( map, b + e ) ) ) );
    return mix( mix( s.x, s.y, f.x ), mix( s.z, s.w, f.x ), f.y );
  }
  float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius,
    vec4 shadowCoord ) {
    if ( uPcss.x <= 0.0 ) {
      return getShadowPCF( shadowMap, shadowMapSize, shadowIntensity, shadowBias, shadowRadius, shadowCoord );
    }
    vec3 c = shadowCoord.xyz / shadowCoord.w;
    c.z += shadowBias;
    // the receiver's plane in the map: depth change per uv (clamped for grazing faces and leaf cards seen edge-on)
    vec3 cx = dFdx( c ), cy = dFdy( c );
    float det = cx.x * cy.y - cx.y * cy.x;
    vec2 dz = abs( det ) > 1e-14 ? vec2( cy.y * cx.z - cx.y * cy.z, cx.x * cy.z - cy.x * cx.z ) / det : vec2( 0.0 );
    dz = clamp( dz, - uPcss.w, uPcss.w );
    if ( c.x < 0.0 || c.x > 1.0 || c.y < 0.0 || c.y > 1.0 || c.z > 1.0 ) return 1.0;
    // 1. blockers: the mean depth of what is nearer the sun, in the four texels round the point (so thin casters, a
    // pole or a leg, are never stepped over) and on a ring out to the widest penumbra
    vec2 t = c.xy * shadowMapSize - 0.5, f = fract( t ), e = 1.0 / shadowMapSize, b = ( floor( t ) + 0.5 ) * e;
    vec4 d4 = vec4(
      unpackRGBAToDepth( texture2D( shadowMap, b ) ), unpackRGBAToDepth( texture2D( shadowMap, b + vec2( e.x, 0.0 ) ) ),
      unpackRGBAToDepth( texture2D( shadowMap, b + vec2( 0.0, e.y ) ) ), unpackRGBAToDepth( texture2D( shadowMap, b + e ) ) );
    vec4 blk = vec4( lessThan( d4, vec4( c.z ) ) );
    float sum = dot( blk, d4 ), n = dot( blk, vec4( 1.0 ) );
    for ( int i = 0; i < ${PCSS_RING}; i ++ ) {
      vec2 o = PCSS_RING[ i ] * uPcss.y;
      float d = unpackRGBAToDepth( texture2D( shadowMap, c.xy + o ) );
      if ( d < c.z + dot( dz, o ) ) { sum += d; n += 1.0; }
    }
    if ( n == 0.0 ) return 1.0;
    if ( n == ${4 + PCSS_RING}.0 ) return 1.0 - shadowIntensity;
    // 2. penumbra radius from the gap (similar triangles with the sun's disc), 3. filter over it: the four texels
    // above as the centre tap, and a disc of taps round it
    float r = clamp( ( c.z - sum / n ) * uPcss.x, uPcss.z, uPcss.y );
    vec4 s = 1.0 - blk;
    float lit = mix( mix( s.x, s.y, f.x ), mix( s.z, s.w, f.x ), f.y );
    for ( int i = 0; i < ${PCSS_TAPS}; i ++ ) {
      vec2 o = PCSS_TAPS[ i ] * r;
      lit += pcssTap( shadowMap, shadowMapSize, c.xy + o, c.z + dot( dz, o ) );
    }
    return mix( 1.0, lit / ${PCSS_TAPS + 1}.0, shadowIntensity );
  }
#endif
`;

// give a material the PCSS shadow lookup (once; a hand-written onBeforeCompile, as terrain's and people's, is kept
// as the first edit). Returns the material.
export function pcss(m) {
  if (PATCHES.get(m)?.some((p) => p.key === 'pcss')) return m;
  patchShaderOwn(m, 'pcss', (sh) => {
    sh.uniforms.uPcss = PCSS.uniform;
    sh.fragmentShader = sh.fragmentShader.replace('#include <shadowmap_pars_fragment>', PCSS_CHUNK);
  });
  return m;
}

// per frame: the light's current frustum (it widens in the bird's-eye view) and map size; on: desktop HQ
export function updatePcss(light, on) {
  const u = PCSS.uniform.value, sh = light.shadow, cam = sh.camera;
  if (!on) { u.x = 0; return; }
  const w = cam.right - cam.left, depth = cam.far - cam.near, k = Math.tan(PCSS.sunDeg * Math.PI / 360) / w;
  u.set(k * depth, k * PCSS.reach, PCSS.minTexels / sh.mapSize.x, 4 * w / depth);
}

// ---------------------------------------------------------------------------- atmosphere: cloud shadows, height fog
// One set of uniforms shared by every material in the scene (globalPatch), updated once a frame from main.js:
//  - cloud shadows (#16): only the sunlight is dimmed under clouds drifting over the campus. A tileable
//    two-channel fBm texture is read twice where the sun ray through the pixel meets the cloud layer (so walls and
//    hillsides get the shadow of the cloud above them): a rotated 1.7 km tile that gathers the clouds into clusters
//    and clear gaps and bends the second read, a 480 m tile of cloud shapes; no 480 m repeat shows from the air.
//    A light factor, not a caster: independent of the (cached) shadow maps, and on phones too.
//  - height fog (#17): replaces three's uniform FogExp2. The haze thins with height (its extinction integrated along
//    the view ray from the camera's height to the pixel's), so the city in the valleys is hazy and the summits clearer,
//    and a high view looks down through thinner air. Its colour is the sky photo's horizon (makeSky blends to the same
//    y97FogColor): bright and warm towards the sun, a darker blue-grey away from it.
const CLOUD_TILE = 480, CLOUD_TILE_B = 1730;             // metres
const CLOUD_WIND = new THREE.Vector2(4.4, -2.6);         // m/s in three's XZ (z = -north): from the west-south-west
const CLOUD_WIND_B = new THREE.Vector2(3.1, -2.2);       // the large tile lags behind: the cloud shapes slowly change
export const ATMOS = {
  uCloudTex: { value: null },
  // 1/tiles, strength (share of the sunlight a cloud takes: thin fair-weather clouds), threshold (~1/3 of sky cloudy)
  uCloud: { value: new THREE.Vector4(1 / CLOUD_TILE, 1 / CLOUD_TILE_B, 0.4, 0.62) },
  uCloudOff: { value: new THREE.Vector4() },             // drift of the two tiles, in texture units
  uSunW: { value: new THREE.Vector3(0, 1, 0) },          // towards the sun, world
  // extinction at height 0 (1/m: from the campus ~28 % haze over 안산 1.7 km off, ~65 % on the hills 7 km off, as
  // in the May 1997 photo of 백양로; ~7 % over the campus seen from 200 m up), its falloff with height (1/m)
  uFogH: { value: new THREE.Vector2(2.5e-4, 1 / 550) },
  uFogAway: { value: new THREE.Color().setRGB(0.27, 0.3, 0.39) },   // linear: the horizon away from the sun
  uFogSun: { value: new THREE.Color().setRGB(0.69, 0.68, 0.66) },   // and round the sun's azimuth (warmer)
  uFogGlow: { value: new THREE.Color().setRGB(0.22, 0.17, 0.1) },   // forward scattering close to the sun
};

// GLSL shared by the patched materials and the sky dome
export const ATMOS_GLSL = /* glsl */`
#define Y97_ATMOS
#define Y97_CLOUD_H 1500.0
uniform sampler2D uCloudTex;
uniform vec4 uCloud, uCloudOff;
uniform vec3 uSunW;
uniform vec2 uFogH;
uniform vec3 uFogAway, uFogSun, uFogGlow;
// factor on the sun's direct light at world point p
float y97Cloud(vec3 p) {
  vec2 q = p.xz + uSunW.xz * ((Y97_CLOUD_H - p.y) / uSunW.y);
  vec2 b = texture2D(uCloudTex, mat2(0.8, 0.6, -0.6, 0.8) * q * uCloud.y + uCloudOff.zw).rg - 0.5;
  float a = texture2D(uCloudTex, q * uCloud.x + uCloudOff.xy + b * 0.15).r;
  return 1.0 - uCloud.z * smoothstep(uCloud.w - 0.1, uCloud.w + 0.1, a + b.y);
}
// in-scattered colour seen along unit direction dir (world): the horizon of the sky photo
vec3 y97FogColor(vec3 dir) {
  float s = dot(dir, uSunW);
  float w = clamp((1.0 + s) * 0.6, 0.0, 1.0);
  return mix(uFogAway, uFogSun, w * w * w) + uFogGlow * pow(max(s, 0.0), 12.0);
}
// share of the fog colour over rel = pixel - camera (world): extinction uFogH.x * exp(-uFogH.y * height), integrated
float y97FogAmount(vec3 rel) {
  float x = uFogH.y * rel.y;
  float f = abs(x) > 1e-4 ? (1.0 - exp(-x)) / x : 1.0 - 0.5 * x;
  return 1.0 - exp(-uFogH.x * exp(-uFogH.y * cameraPosition.y) * length(rel) * f);
}
`;

const ATMOS_DONE = new WeakSet();
const DEFAULT_OBC = THREE.Material.prototype.onBeforeCompile;
function atmosEdit(sh) {
  if (sh.fragmentShader.includes('Y97_ATMOS')) return;     // (once, whatever wraps whom)
  Object.assign(sh.uniforms, ATMOS);
  // world position from the view-space one every material has here (instancing, skinning, morphs included)
  sh.vertexShader = sh.vertexShader
    .replace('#include <common>', '#include <common>\nvarying vec3 vY97World;')
    .replace('#include <fog_vertex>', '#include <fog_vertex>\nvY97World = (mvPosition.xyz - viewMatrix[3].xyz) * mat3(viewMatrix);');
  sh.fragmentShader = sh.fragmentShader
    .replace('#include <common>', `#include <common>\nvarying vec3 vY97World;\n${ATMOS_GLSL}`)
    // The cloud factor rides on the sun's colour wherever three's light loop (or a patched copy of it) fetches it: all
    // of the sun, since the environment map has no sun in it (main.js). A wrapper + macro, so the chunks stay
    // untouched. Only in the fogged main scene: the impostor and portrait renders (no fog) must not bake a cloud in.
    .replace('#include <lights_pars_begin>', `#include <lights_pars_begin>
#ifdef USE_FOG
float y97CloudPx = -1.0;
float y97CloudHere() { if (y97CloudPx < 0.0) y97CloudPx = y97Cloud(vY97World); return y97CloudPx; }
#if NUM_DIR_LIGHTS > 0
void y97DirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
  getDirectionalLightInfo( directionalLight, light );
  light.color *= y97CloudHere();
}
#define getDirectionalLightInfo y97DirectionalLightInfo
#endif
#endif`)
    .replace('#include <fog_fragment>', `#ifdef USE_FOG
{
  vec3 fogRel = vY97World - cameraPosition;
  gl_FragColor.rgb = mix(gl_FragColor.rgb, y97FogColor(normalize(fogRel)), y97FogAmount(fogRel));
}
#endif`);
}

// Give a material the shared atmosphere (cloud shadows + height fog). Safe to call more than once and on any material;
// an onBeforeCompile set by hand before (terrain, people, banners) stays, as the first edit of the stack.
export function globalPatch(m) {
  if (!m || ATMOS_DONE.has(m) || m.fog === false || m.isRawShaderMaterial) return m;
  if (m.isShaderMaterial ? !m.vertexShader.includes('#include <fog_vertex>') || !m.fragmentShader.includes('#include <fog_fragment>')
    : !(m.isMeshStandardMaterial || m.isMeshLambertMaterial || m.isMeshPhongMaterial || m.isMeshBasicMaterial || m.isMeshToonMaterial)) return m;
  ATMOS_DONE.add(m);
  if (/(^|\|)atmos(\||$)/.test(m.customProgramCacheKey())) return m;   // a library material's instanced copy
  if (!PATCHES.has(m) && m.onBeforeCompile !== DEFAULT_OBC) {
    const own = m.onBeforeCompile;
    PATCHES.set(m, [{ key: `own${hashString(own.toString())}`, edit: own }]);
  }
  patchShader(m, 'atmos', atmosEdit);
  m.needsUpdate = true;
  return m;
}

function hashString(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return (h >>> 0).toString(36);
}

// sunDir: unit vector towards the sun (world)
export function setupAtmosphere(sunDir) {
  ATMOS.uSunW.value.copy(sunDir);
  ATMOS.uCloudTex.value = cloudTexture();
}

// The clouds of the sky photo (terrain.js makeSky) drift with the same wind. The photo cannot scroll on for ever (its
// sun and the glow round it stay put, a cloud carried far from the sun would keep the bright rim the sun gave it, one
// from the horizon would come overhead stretched), so its cloud layer swings to and fro along the wind: SKY_SWING
// either way (layer height 1: ~14 deg overhead), at an even ~4.7 deg a minute overhead but for a minute at each turn
// (the shadows' clouds at 1.5 km cross 12 deg a minute there): 5 minutes downwind from the start, then back for 7,
// downwind again for 7, and so on. The cloud shadows on the ground keep step with it (their tiles can run back): the
// same way at its rate, ~1.17 times CLOUD_WIND for most of a sweep, so that on average they go as fast as the wind.
export const SKY_DRIFT = { value: new THREE.Vector2() };   // how far the photo's clouds moved: three's XZ, height 1
const SKY_SWING = 0.25, SKY_PERIOD = 840;                  // s
let skyT = SKY_PERIOD * 7 / 8;                             // upwind of the photo, moving downwind at full speed

// once a frame: the clouds drift (offsets wrapped to [0, 1) texture units: no precision loss over a long session)
export function updateAtmosphere(dt) {
  skyT = (skyT + dt) % SKY_PERIOD;
  // a triangle wave with rounded turns
  const ph = skyT * 2 * Math.PI / SKY_PERIOD, sn = Math.sin(ph), A96 = Math.asin(0.96);
  const swing = Math.asin(0.96 * sn) / A96;
  SKY_DRIFT.value.copy(CLOUD_WIND).normalize().multiplyScalar(SKY_SWING * swing);
  // the shadows' time: dt times the swing's rate over its mean rate (4 / SKY_PERIOD: there and back, 2 each way)
  const sdt = dt * (0.96 * Math.cos(ph) / Math.sqrt(1 - 0.9216 * sn * sn) / A96) * Math.PI / 2;
  const o = ATMOS.uCloudOff.value;
  // the large tile is read rotated (the mat2 in y97Cloud): its drift in its own axes
  const bx = 0.8 * CLOUD_WIND_B.x - 0.6 * CLOUD_WIND_B.y, by = 0.6 * CLOUD_WIND_B.x + 0.8 * CLOUD_WIND_B.y;
  o.x -= CLOUD_WIND.x * sdt / CLOUD_TILE; o.y -= CLOUD_WIND.y * sdt / CLOUD_TILE;
  o.z -= bx * sdt / CLOUD_TILE_B; o.w -= by * sdt / CLOUD_TILE_B;
  o.set(o.x - Math.floor(o.x), o.y - Math.floor(o.y), o.z - Math.floor(o.z), o.w - Math.floor(o.w));
}

// 256² tileable fBm of periodic gradient noise (4 octaves, 3 to 24 cells across), two independent channels, each
// scaled to mean 0.5 and spread 0.18 (so the threshold in uCloud sets the share of sky that is cloud)
function cloudTexture(N = 256) {
  const rnd = mulberry(1997);
  const octaves = [3, 6, 12, 24];
  const fade = (t) => t * t * t * (t * (t * 6 - 15) + 10);
  const data = new Uint8Array(N * N * 2);
  const v = new Float32Array(N * N);
  for (let ch = 0; ch < 2; ch++) {
    const grads = octaves.map((p) => Float32Array.from({ length: p * p }, () => rnd() * Math.PI * 2));
    let s1 = 0, s2 = 0;
    for (let j = 0; j < N; j++) {
      for (let i = 0; i < N; i++) {
        let sum = 0, amp = 1;
        octaves.forEach((p, o) => {
          const x = (i / N) * p, y = (j / N) * p;
          const x0 = Math.floor(x), y0 = Math.floor(y), fx = x - x0, fy = y - y0;
          const g = (cx, cy, dx, dy) => { const a = grads[o][(cy % p) * p + (cx % p)]; return Math.cos(a) * dx + Math.sin(a) * dy; };
          const u = fade(fx), w = fade(fy);
          const n0 = g(x0, y0, fx, fy) * (1 - u) + g(x0 + 1, y0, fx - 1, fy) * u;
          const n1 = g(x0, y0 + 1, fx, fy - 1) * (1 - u) + g(x0 + 1, y0 + 1, fx - 1, fy - 1) * u;
          sum += amp * (n0 * (1 - w) + n1 * w);
          amp *= 0.5;
        });
        v[j * N + i] = sum;
        s1 += sum; s2 += sum * sum;
      }
    }
    const mean = s1 / (N * N), sd = Math.sqrt(s2 / (N * N) - mean * mean);
    for (let k = 0; k < N * N; k++) data[k * 2 + ch] = Math.round(THREE.MathUtils.clamp(0.5 + ((v[k] - mean) / sd) * 0.18, 0, 1) * 255);
  }
  const t = new THREE.DataTexture(data, N, N, THREE.RGFormat, THREE.UnsignedByteType);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.generateMipmaps = true;
  t.needsUpdate = true;
  return t;
}
