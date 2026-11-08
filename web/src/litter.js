// Fallen leaves and petals (issues #18, #35): October's ginkgo carpet and April's cherry petals under the trees.
// tools/build_campus.py bakes where they lie (ground_leaves.png over the splat's rectangle at 1 m: R ginkgo, G cherry,
// B the other broadleaves), tools/make_textures.py paints the tiles of leaves and of petals (litter_ginkgo.png,
// litter_petals.png, alpha = each leaf's rank). The near terrain's splat shader (terrain.js) and 백양로's own road mesh
// (its asphalt and pavers, materials.js) both lay the month's layer with litter().
import * as THREE from 'three';

// how much of each layer the month shows: x ginkgo leaves, y cherry petals, z the other broadleaves' leaves
export const FALL = { spring: [0, 1, 0], summer: [0, 0, 0], autumn: [1, 0, 0.75] };
// the month's tile in uLitter: the leaves and the petals never lie in the same month, so one sampler serves both
// (the terrain's shader has few to spare on a phone)
const TILE = { spring: 'assets/textures/litter_petals.png', summer: 'assets/textures/litter_ginkgo.png',
  autumn: 'assets/textures/litter_ginkgo.png' };
// library materials that get the layer too (백양로's carriageway and sidewalks)
export const LITTER_MATS = new Set(['asphalt', 'pavers']);

let tiles = null;

// shared by every material that lays the layer (MaterialLibrary.uniforms); the rectangle is the splat's (terrain.js)
export function litterUniforms(loadTex) {
  tiles = Object.fromEntries(Object.entries(TILE).map(([s, url]) => [s, loadTex(url)]));
  return {
    uLeaf: { value: loadTex('assets/textures/ground_leaves.png', { srgb: false, repeat: false }) },
    uLitter: { value: tiles.summer },
    uLeafRect: { value: new THREE.Vector4(0, 0, 1, 1) },
    uFall: { value: new THREE.Vector3() },
  };
}

// the month's layers and tile (MaterialLibrary.setSeason)
export function litterSeason(uniforms, season) {
  uniforms.uFall.value.fromArray(FALL[season]);
  uniforms.uLitter.value = tiles[season];
}

export const LITTER_GLSL = `
  uniform sampler2D uLeaf, uLitter;
  uniform vec4 uLeafRect;
  uniform vec3 uFall;
  float litHash(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
  float litNoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(litHash(i), litHash(i + vec2(1.0, 0.0)), f.x), mix(litHash(i + vec2(0.0, 1.0)), litHash(i + vec2(1.0, 1.0)), f.x), f.y);
  }
  // the month's fallen leaves / petals at campus point wp (x east, y north): their coverage (0..1), and their colour
  // in col; grass: how much of the ground there is lawn (the petals show whiter on it). (Call it in uniform control
  // flow: the screen-space derivatives are taken before any branch.)
  float litter(vec2 wp, float grass, out vec3 col) {
    col = vec3(0.0);
    vec2 dwx = dFdx(wp), dwy = dFdy(wp);
    float px = sqrt(length(dwx) * length(dwy));                // metres per pixel on the ground
    vec2 luv = vec2((wp.x - uLeafRect.x) / (uLeafRect.z - uLeafRect.x), (uLeafRect.w - wp.y) / (uLeafRect.w - uLeafRect.y));
    vec3 m = texture2D(uLeaf, luv).rgb * uFall * step(0.0, luv.x) * step(luv.x, 1.0) * step(0.0, luv.y) * step(luv.y, 1.0);
    if (m.x + m.y + m.z < 0.004) return 0.0;
    // fray the soft 1 m mask: drifts and bare patches rather than smooth discs
    float nz = litNoise(wp * 0.43) * 0.6 + litNoise(wp * 1.7 + 5.3) * 0.4;
    float cov = 0.0;
    if (m.x + m.z > 0.004) {
      // a leaf of the tile shows where its rank clears the threshold that covers a share d of the ground (the
      // tile's coverage above rank t is about 1 - exp(-4.6 (1 - t))). Once the leaves shrink to a pixel or two
      // the mip levels average the ranks, and the share itself takes over.
      float near = 1.0 - smoothstep(0.005, 0.016, px);
      mat2 tr = mat2(0.8, -0.6, 0.6, 0.8) * 1.1;                    // turned, for the other leaves
      vec4 lg = textureGrad(uLitter, wp * 1.25, dwx * 1.25, dwy * 1.25);   // 0.8 m tiles
      vec4 lo = textureGrad(uLitter, tr * wp + 0.37, tr * dwx, tr * dwy);
      float dg = clamp(m.x * (0.6 + 1.0 * nz), 0.0, 1.0);
      float dO = clamp(m.z * (0.3 + 0.9 * nz), 0.0, 0.8);
      float tg = 1.0 + log(max(1.0 - 0.97 * dg, 0.001)) / 4.6;
      float to = 1.0 + log(max(1.0 - 0.97 * dO, 0.001)) / 4.6;
      float cg = mix(dg * 0.97, smoothstep(tg - 0.03, tg + 0.01, lg.a), near) * smoothstep(0.0, 0.04, dg);
      float co = mix(dO * 0.97, smoothstep(to - 0.03, to + 0.01, lo.a), near) * smoothstep(0.0, 0.04, dO);
      // the zelkovas', oaks' and cherries' leaves rust-brown, a maple's red here and there
      vec3 oc = lo.rgb * mix(vec3(0.78, 0.46, 0.26), vec3(0.85, 0.3, 0.16), step(0.8, litHash(floor(wp * 0.25))));
      cov = 1.0 - (1.0 - cg) * (1.0 - co);
      col = (lg.rgb * 0.82 * cg + oc * co * (1.0 - cg)) / max(cov, 1e-4);
    }
    if (m.y > 0.004) {
      // cherry petals 1.1-1.5 cm long (this month's uLitter is their tile, 0.4 m). April is full bloom, when the
      // crowns are white and the ground under them all but bare (the 2003 spring photos, the April 2011 roadview:
      // reference/고증.md 3.18): a strew of 1-9 % under the crown, thicker where the wind heaps it, thinning out a
      // metre or two past its edge (not as far as October's leaves: the mask's long tail is left out). The tile is a
      // strew too (its coverage above rank t is about 1 - exp(-0.2 (1 - t))). Two lookups turned against each
      // other, each laying half the share, hide the tile's repeat; once the petals shrink to a pixel or two their
      // share takes over, as with the leaves.
      float dp = 0.06 * smoothstep(0.3, 1.0, m.y) * (0.25 + 0.75 * smoothstep(0.25, 0.85, nz))
                 * (0.5 + litNoise(wp * 2.9 + 1.7));
      float near = 1.0 - smoothstep(0.0025, 0.008, px);
      float tp = 1.0 + log(max(sqrt(1.0 - dp), 0.8)) / 0.2;            // (each layer 1 - sqrt(1 - d): together d)
      // (a mip level sharper than the footprint: the coarser levels average a petal's rank with the bare ground
      // round it and would shave each petal down to its middle)
      mat2 tr = mat2(0.6, -0.8, 0.8, 0.6) * 2.9;
      vec4 la = textureGrad(uLitter, wp * 2.5, dwx * 1.25, dwy * 1.25);
      vec4 lb = textureGrad(uLitter, tr * wp + 0.61, tr * dwx * 0.5, tr * dwy * 0.5);
      float ca = smoothstep(tp - 0.004, tp + 0.004, la.a), cb = smoothstep(tp - 0.004, tp + 0.004, lb.a);
      float cp = mix(dp, 1.0 - (1.0 - ca) * (1.0 - cb), near) * smoothstep(0.0, 0.003, dp);
      vec3 pc = mix(la.rgb, lb.rgb, mix(0.5, cb, near));
      // on the lawn a little brighter and whiter, or the green swallows the pink
      pc = mix(pc * 1.1, min(pc * 1.2 + 0.04, vec3(1.0)), grass);
      col = mix(col, pc, cp);
      cov = 1.0 - (1.0 - cov) * (1.0 - cp);
    }
    return cov;
  }`;

// the layer on a library material (백양로's asphalt and pavers): on its upward faces, over the diffuse colour, with
// the leaves' own roughness and the texture's relief pressed flat under them
export function litterEdit(uniforms) {
  const { uLeaf, uLitter, uLeafRect, uFall } = uniforms;
  return (sh) => {
    Object.assign(sh.uniforms, { uLeaf, uLitter, uLeafRect, uFall });
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vLitW;')
      .replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
        {
          vec4 lw = vec4(transformed, 1.0);
          #ifdef USE_INSTANCING
            lw = instanceMatrix * lw;
          #endif
          vLitW = (modelMatrix * lw).xyz;
        }`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\nvarying vec3 vLitW;\nfloat litCov = 0.0;\n${LITTER_GLSL}`)
      .replace('#include <color_fragment>', `#include <color_fragment>
        {
          vec3 litCol;
          float up = smoothstep(0.55, 0.85, dot(viewMatrix[1].xyz, normalize(vNormal)));
          litCov = litter(vec2(vLitW.x, -vLitW.z), 0.0, litCol) * up;
          diffuseColor.rgb = mix(diffuseColor.rgb, litCol, litCov);
        }`)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
        roughnessFactor = mix(roughnessFactor, 0.8, litCov);`)
      .replace('#include <normal_fragment_maps>',
        THREE.ShaderChunk.normal_fragment_maps.replace('mapN.xy *= normalScale;', 'mapN.xy *= normalScale * (1.0 - 0.8 * litCov);'));
  };
}
