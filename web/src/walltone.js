// Tone and repeat of the halls' walls (the tiled PBR materials with a `weather` in materials.json): a photo of a wall is
// never one tile printed over and over at one tone.
//  1. broad tone: brightness (±8 %) and a touch of warmth drift over metres, as a render, a pour or a quarry's stone
//     does. Read from the clouds' tileable fBm (materials.js ATMOS.uCloudTex) laid on the wall's plane in world
//     metres, two scales on desktop, one on phones
//  2. panels: the textures laid in panels or tiles (their joint lattice in GRID) take a tone per panel, the granite
//     a little warmer or cooler too; it fades out where a panel is under a couple of pixels (the facade tiles far off)
//  3. desktop only, against the repeat itself: in a jointed texture every panel shows another panel of the same
//     texture, shifted by whole panels (the joints stay where they are, panel by panel the stone or the pour differs);
//     in an unjointed one (render, rubble, brick) the tile's own large blotches are taken out, so only the broad tone
//     varies across the wall
//  4. arrises (the halls' and landmarks' baked copies, blender/bake.py `_edge`): within a few centimetres of the nearest
//     convex edge the stone and the concrete are worn: lighter, rougher, and on desktop the normal leans out over the
//     edge as on a slightly rounded arris, so it catches the light (never narrower than a pixel: no shimmer far off)
// Patched from MaterialLibrary.get (materials.js) after its own map edit (patchMap), as one edit of the stack; the
// arrises from MaterialLibrary.baked.
import { MOBILE } from './util.js';

// joint lattice in texture uv: [columns, rows, u, v of a joint]; columns 0: courses running the whole width
const GRID = {
  granite_tile: [5, 5, 0, 0],
  white_stone_panels: [4, 4, 0, 0],
  white_square_tiles: [8, 8, 0, 0],
  rectangular_facade_tiles: [40, 13, 0, 0],
  concrete_wall_008: [4, 2, 0.0156, 0.2881],      // the formwork's panels
  concrete_slab_wall: [0, 2, 0, 0.4443],          // horizontal slabs
};
// per panel: spread of brightness (full range) and of warm against cool
const TONE = {
  granite_tile: [0.16, 0.05], white_stone_panels: [0.08, 0.02], white_square_tiles: [0.05, 0],
  rectangular_facade_tiles: [0.18, 0.04], concrete_wall_008: [0.08, 0.02], concrete_slab_wall: [0.07, 0.02],
};
// unjointed textures whose blotches repeat across a broad wall
const FLAT = new Set(['white_plaster_02', 'grey_plaster', 'brushed_concrete', 'old_stone_wall', 'red_bricks_02']);

const f = (x) => (Number.isInteger(x) ? x.toFixed(1) : String(x));

const COMMON = /* glsl */`
uniform sampler2D uWallNoise;
uint wvMix(uint n) { n ^= n >> 16; n *= 0x7feb352du; n ^= n >> 15; n *= 0x846ca68bu; n ^= n >> 16; return n; }
float wvHash(vec2 c, uint k) {
  uvec2 q = uvec2(ivec2(c) + 32768);
  return float(wvMix(q.x * 1973u + q.y * 9277u + k * 26699u) >> 8) / 16777216.0;
}`;

// world position, and the wall's plane in world metres: (along the wall, height), or (x, z) on what faces up
const WORLD = /* glsl */`
  vec3 wvW = (-vViewPosition - viewMatrix[3].xyz) * mat3(viewMatrix);
  #ifdef FLAT_SHADED
    vec3 wvNw = normalize(cross(dFdx(vViewPosition), dFdy(vViewPosition)) * mat3(viewMatrix));
  #else
    vec3 wvNw = normalize(vNormal * mat3(viewMatrix));
  #endif
  vec2 wvP = abs(wvNw.y) > 0.7 ? wvW.xz : vec2(dot(wvW.xz, normalize(vec2(-wvNw.z, wvNw.x))), wvW.y);`;

// The panel shuffle picks one panel per 2x2 pixel quad (the corner pixel's), so the uv the samplers get moves by one
// constant within a quad and the screen derivatives (mip level, the normal map's tangent frame) see no jump; the
// staircase lies in the joint. Which pixel of its quad a fragment is, is read off the derivative of the pixel parity,
// whichever way the quads lie on gl_FragCoord. The three maps' uvs are renamed to the shifted ones (macros), so their
// chunks, and any edit of them, stay as they are.
function shuffle([nx, ny, ox, oy]) {
  return /* glsl */`
#ifdef USE_MAP
  vec2 wvG = vMapUv * vec2(${f(nx)}, ${f(ny)}) - vec2(${f(ox)}, ${f(oy)});
  vec2 wvDx = dFdx(wvG), wvDy = dFdy(wvG);
  vec2 wvPar = mod(floor(gl_FragCoord.xy), 2.0);
  vec2 wvCell = floor(wvG - wvDx * (dFdx(wvPar.x) > 0.0 ? wvPar.x : 1.0 - wvPar.x)
                          - wvDy * (dFdy(wvPar.y) > 0.0 ? wvPar.y : 1.0 - wvPar.y));
  vec2 wvOff = vec2(${nx ? `floor(wvHash(wvCell, 1u) * ${f(nx)}) / ${f(nx)}` : 'wvHash(wvCell, 1u)'},
                    floor(wvHash(wvCell, 2u) * ${f(ny)}) / ${f(ny)});
  vec2 wvUv = vMapUv + wvOff;
  #define vMapUv wvUv
  #ifdef USE_NORMALMAP
    vec2 wvUvN = vNormalMapUv + wvOff;
    #define vNormalMapUv wvUvN
  #endif
  #ifdef USE_ROUGHNESSMAP
    vec2 wvUvR = vRoughnessMapUv + wvOff;
    #define vRoughnessMapUv wvUvR
  #endif
#endif`;
}

// broad tone: two reads of the fBm (std ~0.18 each about 0.5), at 37 m and, turned, at 13 m
const BROAD = /* glsl */`
{
  vec2 wvA = texture2D(uWallNoise, wvP * 0.027).rg;
  ${MOBILE ? 'float wvM = wvA.r - 0.5;' : `vec2 wvB = texture2D(uWallNoise, mat2(0.8, 0.6, -0.6, 0.8) * wvP * 0.077 + 0.5).rg;
  float wvM = wvA.r * 0.6 + wvB.r * 0.4 - 0.5;`}
  diffuseColor.rgb *= clamp(1.0 + 0.4 * wvM, 0.92, 1.08) * (1.0 + 0.12 * (wvA.g - 0.5) * vec3(1.0, 0.1, -0.9));
}`;

function panelTone([nx, ny, ox, oy], [tone, warm], shuffled) {
  return /* glsl */`
#ifdef USE_MAP
{
  ${shuffled ? '' : `vec2 wvG = vMapUv * vec2(${f(nx)}, ${f(ny)}) - vec2(${f(ox)}, ${f(oy)});
  vec2 wvDx = dFdx(wvG), wvDy = dFdy(wvG), wvCell = floor(wvG);`}
  float wvF = 1.0 - smoothstep(0.3, 0.7, max(length(wvDx), length(wvDy)));
  float wvB = wvHash(wvCell, 3u) - 0.5, wvC = wvHash(wvCell, 4u) - 0.5;
  diffuseColor.rgb *= 1.0 + wvF * (${f(tone)} * wvB + ${f(warm)} * wvC * vec3(1.0, 0.1, -0.9));
}
#endif`;
}

// The tile's own blotches (what repeats, seen across a broad wall) taken out: the texel over the map's mean colour, at
// the mip that has 8 texels across the tile (features over ~1/4 of the tile; never finer than the pixel's own mip, or
// it would shimmer far off), in luminance so a patchMap's colour edit (sat) is kept. The broad tone above puts
// blotches back that do not repeat.
const FLATTEN = /* glsl */`
#ifdef USE_MAP
{
  vec2 wvSz = vec2(textureSize(map, 0));
  vec2 wvTx = vMapUv * wvSz;
  float wvLod = max(log2(wvSz.x) - 3.0, log2(max(length(dFdx(wvTx)), length(dFdy(wvTx)))));
  float wvLo = dot(textureLod(map, vMapUv, wvLod).rgb, vec3(0.2126, 0.7152, 0.0722));
  float wvMu = dot(textureLod(map, vec2(0.5), 16.0).rgb, vec3(0.2126, 0.7152, 0.0722));
  diffuseColor.rgb *= mix(1.0, clamp(wvMu / max(wvLo, 1e-4), 0.5, 2.0), 0.85);
}
#endif`;

// the shader edit for a tiled library material (name, definition d), or null for one that is not a wall; noise: the
// uniform holding the clouds' fBm texture
export function wallTone(name, d, noise) {
  if (!d || !d.tex || d.weather === undefined) return null;
  const grid = GRID[d.tex];
  const tone = grid && TONE[d.tex];
  const shuffled = !!grid && !MOBILE;
  const flat = !grid && !MOBILE && FLAT.has(d.tex);
  const key = `wall${grid ? `G${d.tex}` : ''}${flat ? 'F' : ''}`;
  const edit = (sh) => {
    sh.uniforms.uWallNoise = noise;
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>${COMMON}`)
      .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>
        ${WORLD}
        ${shuffled ? shuffle(grid) : ''}`)
      .replace('#include <color_fragment>', `#include <color_fragment>
        ${BROAD}
        ${grid ? panelTone(grid, tone, shuffled) : ''}
        ${flat ? FLATTEN : ''}`);
  };
  return { key, edit };
}

// ---------------------------------------------------------------------------- 4. arrises
// The attribute `edge` (world.js: the GLB's _EDGE as 16-bit normalized, / EDGE_RANGE): metres along the face to up to
// four arrises; a mesh without it reads 1 (EDGE_RANGE: none).
const EDGE_RANGE = 128;
const EDGE_VERT = /* glsl */`
attribute vec4 edge;
varying vec4 vEdge;`;
// how far the wear reaches at an arris (chipped unevenly along it: 2-6 cm), widened to a pixel's footprint at least
// with its strength scaled down to match (the same share of the pixel worn); wvEd: m to the nearest arris
const EDGE_COLOR = /* glsl */`
float wvEd = min(min(vEdge.x, vEdge.y), min(vEdge.z, vEdge.w)) * ${f(EDGE_RANGE)};
float wvPx = max(length(dFdx(vViewPosition)), length(dFdy(vViewPosition)));
float wvR = 0.04 * (0.55 + 0.9 * texture2D(uWallNoise, wvP * 1.3 + 0.7).g);
float wvWear = (1.0 - smoothstep(0.0, wvR + wvPx, wvEd)) * wvR / (wvR + wvPx);
diffuseColor.rgb *= 1.0 + 0.18 * wvWear;`;
const EDGE_ROUGH = /* glsl */`
roughnessFactor = min(1.0, roughnessFactor + 0.25 * wvWear);`;
// the lean: up to 0.7 rad at the arris, away from the face towards the edge (minus the in-plane gradient of the
// distance, from screen derivatives), faded out where the rounding is under two pixels
const EDGE_NORMAL = /* glsl */`
{
  vec3 wvDpx = dFdx(-vViewPosition), wvDpy = dFdy(-vViewPosition);
  vec3 wvC1 = cross(wvDpy, nonPerturbedNormal), wvC2 = cross(nonPerturbedNormal, wvDpx);
  float wvDet = dot(wvDpx, wvC1);
  vec3 wvGr = (dFdx(wvEd) * wvC1 + dFdy(wvEd) * wvC2) / (abs(wvDet) > 1e-14 ? wvDet : 1e-14);
  float wvLean = 0.7 * (1.0 - smoothstep(0.0, wvR, wvEd)) * smoothstep(1.0, 2.0, wvR / max(wvPx, 1e-5));
  if (dot(wvGr, wvGr) > 1e-6) normal = normalize(normal * cos(wvLean) - normalize(wvGr) * sin(wvLean));
}`;

// the arrises' edit for the baked copy of a wall material (its definition d), or null; none: the attribute's value
// for a mesh without it (defaultAttributeValues)
export function edgeWear(d) {
  if (!d || !d.tex || !(d.weather > 0)) return null;
  const edit = (sh) => {
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>${EDGE_VERT}`)
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvEdge = edge;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec4 vEdge;')
      .replace('#include <color_fragment>', `#include <color_fragment>${EDGE_COLOR}`)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>${EDGE_ROUGH}`)
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>${MOBILE ? '' : EDGE_NORMAL}`);
  };
  return { key: 'edgeWear', edit, none: [1, 1, 1, 1] };
}
