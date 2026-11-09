// 활천대 fountain water, rendered with Ultra Water (https://github.com/Humpalumps/Ultra-Water, MIT; ./ultra-water/).
//
// Ultra Water is an ocean renderer; the fountain's pool is 8.9 m across and 30 cm deep, so only the parts that scale
// down are used:
//  - OceanSim: the Tessendorf FFT with capillary-gravity dispersion, at 64² and with cascades of 4.5 m to 19 cm,
//    driven by a light breeze over a few metres of fetch, so the basin carries fine wind ripples.
//  - WaveCaustics: area-ratio splatting of the three longer cascades onto the basin floor depth.
//  - From OceanSurface's water shader: slope + slope-variance (LEAN) roughness from the cascades' mips, Kaplanyan
//    geometric specular AA, Lagarde's roughness-aware Fresnel, the GGX sun with its alpha floor, the facet-count
//    glints, Beer-Lambert absorption, and the Cauchy-Poisson impact rings (here: the jet falling back).
// The basin under the water (concrete floor, the field-stone wall's inner face, the stone island) is ray-traced in the
// same shader through the refracted view ray, so it bends with the ripples and takes the caustics and the shadows of
// the wall and the island; the scene's sun shadow map (when shadows are on) darkens the surface and the floor.
// The pool's sizes come with campus.statues.fountain (tools/build_campus.py FOUNTAIN): heights there are over the
// flagstones round it, here over the pool's floor.
// Cost: the sim and caustics run only while the fountain is on screen and within SIM_DIST of the camera (every
// second frame on phones); otherwise the surface keeps its last state and only the shader runs, on the few pixels the
// basin covers.
import * as THREE from 'three';
import { OceanSim, defaultOceanParams } from './ultra-water/OceanSim.js';
import { WaveCaustics } from './ultra-water/Caustics.js';
import { patchShader } from '../materials.js';

const N = 64;
const CASCADES = [4.5, 1.5, 0.5, 0.19];    // 4.5 = 3 x 1.5 = 9 x 0.5 exactly, so the caustic tile (all three summed) tiles
const COL_R = 0.45, COL_TOP = 3.04;        // the carved cross column (its shadow: a cylinder that wide), its top over
                                           // the flagstones (blender/landmarks.py FOUNTAIN_COL)
const CURTAIN_R = 1.05;                    // where the jet's fall meets the water (FOUNTAIN_CURTAIN)
const SIM_DIST = 70;                       // metres: beyond this the ripples freeze (too small to see move)
const IMPACTS = 16;

const fountainParams = () => ({
  ...defaultOceanParams(),
  windSpeed: 2.6, windDirection: 35, fetchKm: 0.04, spreadBlend: 0.6, windSwell: 0,
  gamma: 1.5,
  shortWavesFade: 0.002,     // metres: keep the centimetre ripples the ocean preset cuts away
  capillaryFade: 0.003,
  waveScale: 1.0,
  swellScale: 0,
  choppiness: 0.6,
  timeScale: 1,
});

const VERT = /* glsl */`
#include <common>
#include <fog_pars_vertex>
#include <shadowmap_pars_vertex>
varying vec3 vWorld;
void main() {
  vec3 transformedNormal = normalMatrix * vec3(0.0, 1.0, 0.0);
  vec4 worldPosition = modelMatrix * vec4(position, 1.0);
  vWorld = worldPosition.xyz;
  vec4 mvPosition = viewMatrix * worldPosition;
  gl_Position = projectionMatrix * mvPosition;
  #include <shadowmap_vertex>
  #include <fog_vertex>
}`;

const frag = ({ WATER_Z, PED_R, RIM_H, PLINTH_H, COL_H }) => /* glsl */`
#include <common>
#include <packing>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <shadowmap_pars_fragment>
#include <cube_uv_reflection_fragment>

uniform sampler2D uEnvMap;
uniform float uEnvI;
uniform sampler2D uSlope0, uSlope1, uSlope2, uSlope3;
uniform vec4 uLength;
uniform sampler2D uCaustics;
uniform float uCausticL, uCausticOn;
uniform vec3 uCenter;          // basin centre at the floor (world)
uniform float uR, uTime;
uniform vec3 uSunDir, uSunColor, uSkyColor;
uniform sampler2D uFloorMap, uWallMap;
uniform vec3 uFloorTint, uWallTint;
uniform vec3 uAbsorb, uScatter;
uniform vec4 uImpact[${IMPACTS}];      // x, z (world), age (s), amplitude (m)
uniform float uImpactSize[${IMPACTS}];
uniform vec4 uJets;            // -, landing radius of the jet's falling curtain, -, -
varying vec3 vWorld;

#define WATER_Z ${WATER_Z.toFixed(3)}
#define PED_R ${PED_R.toFixed(3)}
#define RIM_H ${RIM_H.toFixed(3)}

// --- Ultra Water (OceanSurface.js): hash, Poisson draw, impact rings ---------------------------------------------
float hash12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float poisson(float lam, float u) {
  if (lam > 12.0) return max(0.0, floor(lam + sqrt(lam) * (u - 0.5) * 3.4 + 0.5));
  float k = 0.0, p = exp(-lam), s = p;
  for (int i = 0; i < 24; i++) { if (u <= s) break; k += 1.0; p *= lam / k; s += p; }
  return k;
}
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash12(i), hash12(i + vec2(1, 0)), f.x), mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), f.x), f.y);
}
// Ripple rings from objects hitting the water (Cauchy-Poisson): by stationary phase a
// point impulse gives local wavenumber k = g t^2 / (4 r^2) at radius r and phase k r, so
// long waves race ahead and short ones trail inside. A splash of radius L excites
// ~ (kL)^2 exp(-(kL)^2); kMax band-limits to what the pixel can show.
// Returns (height, dh/dx, dh/dz).
vec3 impactWaves(vec2 xz, float kMax) {
  vec3 o = vec3(0.0);
  for (int i = 0; i < ${IMPACTS}; i++) {
    vec4 e = uImpact[i];
    if (e.w <= 0.0) continue;
    vec2 dv = xz - e.xy;
    float r = length(dv) + 1e-3, L = uImpactSize[i];
    float k = 9.81 * e.z * e.z / (4.0 * r * r);
    float kl2 = k * k * L * L;
    float amp = e.w * 2.72 * kl2 * exp(-kl2 - k * k / (kMax * kMax) - 0.9 * e.z) * L / (L + r);
    float ph = k * r;
    o.x += amp * cos(ph);
    o.yz += dv / r * (amp * k * sin(ph));
  }
  return o;
}

// --- basin geometry (local: centre of the floor at the origin, y up) ---------------------------------------------
// distance along the ray from p (inside radius R) to where it leaves radius R
float exitCircle(vec2 p, vec2 d, float R) {
  float a = dot(d, d), b = dot(p, d), c = dot(p, p) - R * R;
  return a < 1e-8 ? 1e9 : (-b + sqrt(max(b * b - a * c, 0.0))) / a;
}
// distance along the ray from p (outside radius R) to where it enters radius R (1e9: misses)
float enterCircle(vec2 p, vec2 d, float R) {
  float a = dot(d, d), b = dot(p, d), c = dot(p, p) - R * R;
  float disc = b * b - a * c;
  if (a < 1e-8 || disc < 0.0) return 1e9;
  float t = (-b - sqrt(disc)) / a;
  return t > 0.0 ? t : 1e9;
}
// shadow of the granite rim and the pedestal on a point q under water, for the refracted sun ray rs (pointing down)
float basinShadow(vec3 q, vec3 rs, vec3 sun) {
  vec3 up = -rs;
  float tS = (WATER_Z - q.y) / up.y;                  // to the surface
  // under water: the inner wall and the pedestal foot
  if (exitCircle(q.xz, up.xz, uR) < tS) return 0.0;
  if (length(q.xz) > PED_R && enterCircle(q.xz, up.xz, PED_R) < tS) return 0.0;
  // above: the wall (up to RIM_H at radius uR), the island and the column on it
  vec3 e = q + up * tS;
  float tR = exitCircle(e.xz, sun.xz, uR);
  if (WATER_Z + sun.y * tR < RIM_H) return 0.0;
  float tP = enterCircle(e.xz, sun.xz, PED_R);
  if (tP < 1e8 && WATER_Z + sun.y * tP < ${PLINTH_H.toFixed(3)}) return 0.0;
  float tP2 = enterCircle(e.xz, sun.xz, ${COL_R.toFixed(3)});
  if (tP2 < 1e8 && WATER_Z + sun.y * tP2 < ${COL_H.toFixed(3)}) return 0.0;
  return 1.0;
}

void main() {
  vec3 toCam = cameraPosition - vWorld;
  float dist = length(toCam);
  vec3 V = toCam / dist;
  vec2 xz = vWorld.xz;
  vec2 lp = xz - uCenter.xz;                // local horizontal position
  float rr = length(lp);
  vec2 fwXZ = fwidth(xz);
  float fw = max(max(fwXZ.x, fwXZ.y), 1e-4);

  // --- surface: slopes + slope variance from the four cascades ---------------------------------------------------
  // the water is stirred most around the ring where the jet falls back, calmest at the outer wall
  float stir = 0.45 + 0.9 * exp(-pow((rr - uJets.y) / 0.6, 2.0));
  vec4 s0 = texture(uSlope0, xz / uLength.x), s1 = texture(uSlope1, xz / uLength.y);
  vec4 s2 = texture(uSlope2, xz / uLength.z), s3 = texture(uSlope3, xz / uLength.w);
  vec2 slope = (s0.xy + s1.xy + s2.xy + s3.xy) * stir;
  vec2 variance = (max(s0.zw - s0.xy * s0.xy, 0.0) + max(s1.zw - s1.xy * s1.xy, 0.0)
                 + max(s2.zw - s2.xy * s2.xy, 0.0) + max(s3.zw - s3.xy * s3.xy, 0.0)) * stir * stir;
  vec3 imp = impactWaves(xz, 2.0 / fw);
  slope += imp.yz;
  vec3 Nrm = normalize(vec3(-slope.x, 1.0, -slope.y));
  // geometric specular AA (Kaplanyan): normal change across the pixel adds variance
  vec3 dndx = dFdx(Nrm), dndy = dFdy(Nrm);
  float geoVar = min(0.25 * (dot(dndx, dndx) + dot(dndy, dndy)), 0.18);
  float alpha2 = 0.0004 + variance.x + variance.y + geoVar;
  float alpha = sqrt(alpha2);
  float NoV = max(dot(Nrm, V), 1e-4);

  float shadow = 1.0;
  #if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
    DirectionalLightShadow dls = directionalLightShadows[0];
    shadow = getShadow(directionalShadowMap[0], dls.shadowMapSize, dls.shadowIntensity, dls.shadowBias, dls.shadowRadius, vDirectionalShadowCoord[0]);
  #endif
  vec3 sun = uSunColor * shadow;
  #if defined( Y97_ATMOS ) && defined( USE_FOG )
    sun *= y97Cloud(vWorld);     // the drifting cloud shadows (materials.js globalPatch)
  #endif
  // irradiance from the sky (pre-filtered environment, as three's getIBLIrradiance) and the hemisphere light
  vec3 ambient = PI * textureCubeUV(uEnvMap, vec3(0.0, 1.0, 0.0), 1.0).rgb * uEnvI + uSkyColor;

  // --- under the surface: ray-trace the basin through the refracted view ray --------------------------------------
  vec3 P = vec3(lp.x, WATER_Z, lp.y);
  vec3 T = refract(-V, Nrm, 1.0 / 1.33);
  if (T.y > -0.02) T = normalize(vec3(T.x, -0.02, T.z));
  float tF = P.y / -T.y;                              // floor
  float tW = exitCircle(P.xz, T.xz, uR);              // inner wall
  float tP = rr > PED_R ? enterCircle(P.xz, T.xz, PED_R) : 1e9;   // pedestal foot
  float t = min(tF, min(tW, tP));
  vec3 Q = P + T * t;
  vec3 rs = refract(-uSunDir, vec3(0.0, 1.0, 0.0), 1.0 / 1.33);   // the sun under flat water
  vec3 albedo, nQ;
  if (t == tF) {
    albedo = texture(uFloorMap, Q.xz / 3.0).rgb * uFloorTint;
    nQ = vec3(0.0, 1.0, 0.0);
  } else {
    vec2 radial = normalize(Q.xz);
    nQ = t == tW ? vec3(-radial.x, 0.0, -radial.y) : vec3(radial.x, 0.0, radial.y);
    float u = atan(Q.z, Q.x) * (t == tW ? uR : PED_R);
    albedo = texture(uWallMap, vec2(u, Q.y) / 3.2).rgb * uWallTint;      // (stone_rubble_brown's tile)
  }
  float depthQ = WATER_Z - Q.y;
  // caustics registered at the surface entry point of the sun ray through Q
  vec2 entry = Q.xz + uCenter.xz + rs.xz / rs.y * depthQ;
  float lodC = log2(max(fw * 256.0 / uCausticL, 1.0));
  float caustic = mix(1.0, textureLod(uCaustics, entry / uCausticL, lodC).r, uCausticOn * clamp(depthQ / 0.2, 0.0, 1.0));
  float sunIn = max(dot(nQ, -rs), 0.0) * basinShadow(Q, rs, uSunDir) * 0.97;    // 0.97: Fresnel loss going in
  vec3 floorCol = albedo * (sun * sunIn * caustic + ambient * 0.75) / PI;
  // Beer-Lambert along the path down and (roughly) back up, towards an in-scatter colour lit like the water
  float path = t + depthQ;
  vec3 Tr = exp(-uAbsorb * path);
  vec3 inscatter = uScatter * (ambient * 0.6 + sun * max(uSunDir.y, 0.0) * 0.4) / PI;
  vec3 body = floorCol * Tr + inscatter * (1.0 - Tr);

  // aerated water where the jet comes down: churned, whitish, flickering patches
  float churn = exp(-pow((rr - uJets.y) / 0.28, 2.0)) * 0.55;
  churn *= smoothstep(0.35, 0.75, vnoise(lp * 7.0 + vec2(uTime * 1.7, -uTime * 1.3)) * 0.6 + vnoise(lp * 19.0 - uTime * 2.3) * 0.5);
  body = mix(body, vec3(0.85, 0.9, 0.92) * (sun * max(uSunDir.y, 0.0) + ambient) / PI, churn * 0.7);

  // Fresnel with roughness-aware F90 (Lagarde) so the rough parts don't go white
  const float F0 = 0.02;
  float F90 = max(1.0 - 0.7 * sqrt(alpha), F0);
  float F = F0 + (F90 - F0) * pow(1.0 - NoV, 5.0);

  // reflection: the sky (the pre-filtered environment) by roughness; the rim hides the low sky near the wall
  vec3 R = reflect(-V, Nrm);
  R.y = abs(R.y);
  vec3 refl = textureCubeUV(uEnvMap, R, sqrt(alpha)).rgb * uEnvI;
  float tRim = exitCircle(P.xz, R.xz, uR);
  float hRim = WATER_Z + R.y * tRim;
  refl = mix(refl, uWallTint * 0.35 * (ambient + sun * 0.3) / PI, step(hRim, RIM_H) * 0.8);

  // sun specular: GGX, alpha floored so the sun acts as a small area light
  vec3 L = uSunDir;
  float NoL = max(dot(Nrm, L), 0.0);
  float aS = max(alpha, 0.015);
  float aS2 = aS * aS;
  vec3 H = normalize(L + V);
  float NoH = max(dot(Nrm, H), 0.0);
  float dd = NoH * NoH * (aS2 - 1.0) + 1.0;
  float D = aS2 / (PI * dd * dd);
  float vis = 0.5 / (NoL * sqrt(NoV * NoV * (1.0 - aS2) + aS2) + NoV * sqrt(NoL * NoL * (1.0 - aS2) + aS2) + 1e-5);
  float Fs = F0 + (1.0 - F0) * pow(1.0 - max(dot(V, H), 0.0), 5.0);
  vec3 spec = sun * (PI * D * vis * Fs * NoL);
  // glitter (Ultra Water): the lobe as a finite number of facets per pixel-sized cell, twinkling
  if (dot(spec, vec3(1.0)) > 0.02) {
    const float FACETS = 6e4;   // per m^2 (calibration knob)
    float lf = log2(fw) + 1.0;
    float l0 = floor(lf);
    float per = FACETS * D * NoH * 6.8e-5 / (4.0 * max(dot(V, H), 0.05));
    float m = 0.0;
    for (int j = 0; j < 2; j++) {
      float l = l0 + float(j), sz = exp2(l);
      vec2 cell = floor(xz / sz);
      float lam = per * sz * sz;
      float tt = uTime * 3.0 + hash12(cell + l * 17.17) * 64.0, it = floor(tt);
      float n0 = poisson(lam, clamp(hash12(cell * 1.31 + it * 3.7), 1e-4, 0.9999));
      float n1 = poisson(lam, clamp(hash12(cell * 1.31 + (it + 1.0) * 3.7), 1e-4, 0.9999));
      m += (j == 0 ? 1.0 - (lf - l0) : lf - l0) * min(mix(n0, n1, smoothstep(0.0, 1.0, tt - it)) / max(lam, 1e-4), 30.0);
    }
    spec *= mix(1.0, m, 0.8);
  }

  vec3 col = body * (1.0 - F) + refl * F * (1.0 - churn * 0.6) + spec;
  gl_FragColor = vec4(col, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
  #include <fog_fragment>
}`;

export class FountainWater {
  // F: campus.statues.fountain ({pos, r, island, wall, water, floor, isle, rot, h}); lib: MaterialLibrary; sun: the
  // DirectionalLight; sunDir: towards it
  constructor(renderer, scene, F, lib, sun, sunDir, { mobile = false } = {}) {
    this.renderer = renderer;
    this.F = F;
    this.mobile = mobile;
    this.sunDir = sunDir;
    const fl = F.floor;                    // the pool's floor under the flagstones; the shader's heights are over it
    this.B = { WATER_Z: F.water - fl, PED_R: F.island, RIM_H: F.wall - fl, PLINTH_H: F.isle - fl, COL_H: COL_TOP - fl };
    this.center = new THREE.Vector3(F.pos[0], F.h + fl, -F.pos[1]);
    this.sphere = new THREE.Sphere(this.center.clone().setY(F.h + F.water), F.r + 0.5);
    this.frustum = new THREE.Frustum();
    this.m4 = new THREE.Matrix4();
    this.frame = 0;
    this.time = 0;

    this.sim = new OceanSim(renderer, fountainParams(), { n: N, cascades: CASCADES });
    this.caustics = new WaveCaustics(renderer, this.sim, { cascades: [0, 1, 2], depth: this.B.WATER_Z, cells: mobile ? 128 : 192, res: mobile ? 256 : 512, samples: mobile ? 0 : 4 });

    const env = scene.environment;
    const h = env.image.height, maxMip = Math.log2(h) - 2;
    const floorM = lib.get('concrete_dark'), wallM = lib.get('stone_rubble_brown');
    // the jet out of the column's top falls back round it into the pool (blender/landmarks.py); no jets on the rim
    this.curtainR = CURTAIN_R;
    this.impacts = Array.from({ length: IMPACTS }, () => new THREE.Vector4());
    this.sizes = new Array(IMPACTS).fill(0.06);
    this._flowSpray(lib.get('water_spray'));
    this.life = new Array(IMPACTS).fill(0);
    const sl = this.sim.slope;
    this.material = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: frag(this.B),
      lights: true,
      fog: true,
      defines: {
        ENVMAP_TYPE_CUBE_UV: '',
        CUBEUV_TEXEL_WIDTH: 1 / (3 * Math.max(Math.pow(2, maxMip), 7 * 16)),
        CUBEUV_TEXEL_HEIGHT: 1 / h,
        CUBEUV_MAX_MIP: maxMip.toFixed(1),
      },
      uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.lights, THREE.UniformsLib.fog, {
        uEnvI: { value: scene.environmentIntensity ?? 1 },
        uLength: { value: new THREE.Vector4(...CASCADES) },
        uCausticL: { value: this.caustics.length },
        uCausticOn: { value: 1 },
        uCenter: { value: this.center },
        uR: { value: F.r },
        uTime: { value: 0 },
        uSunDir: { value: sunDir.clone() },
        uSunColor: { value: sun.color.clone().multiplyScalar(sun.intensity) },
        uSkyColor: { value: new THREE.Color(0xcfe0ff).multiplyScalar(0.35) },
        uFloorTint: { value: floorM.color.clone() },
        uWallTint: { value: wallM.color.clone() },
        uAbsorb: { value: new THREE.Vector3(1.3, 0.5, 0.42) },     // a little green-blue, city fountain water
        uScatter: { value: new THREE.Color(0.05, 0.12, 0.13) },
        uImpactSize: { value: this.sizes },
        uJets: { value: new THREE.Vector4(0, this.curtainR, 0, 0) },
      }]),
    });
    // textures go in after the merge (UniformsUtils.merge would clone them)
    const u = this.material.uniforms;
    u.uEnvMap = { value: env };
    u.uSlope0 = { value: sl[0] }; u.uSlope1 = { value: sl[1] }; u.uSlope2 = { value: sl[2] }; u.uSlope3 = { value: sl[3] };
    u.uCaustics = { value: this.caustics.texture };
    u.uFloorMap = { value: floorM.map };
    u.uWallMap = { value: wallM.map };
    u.uImpact = { value: this.impacts };

    // a flat ring between the island and the wall, at the water level
    const geo = new THREE.RingGeometry(this.B.PED_R - 0.01, F.r + 0.01, 120, 1);
    geo.rotateX(-Math.PI / 2);
    this.mesh = new THREE.Mesh(geo, this.material);
    this.mesh.name = 'fountain_water';
    this.mesh.position.set(this.center.x, F.h + F.water, this.center.z);
    this.mesh.receiveShadow = true;
    this.mesh.castShadow = false;
    scene.add(this.mesh);

    // start with a full set of rings at staggered ages, and one sim step so the slopes aren't empty
    for (let i = 0; i < IMPACTS; i++) this._spawn(i, Math.random() * 1.6);
    this._step(1 / 30);
  }

  _spawn(i, age = 0) {
    // the jet's falling curtain: anywhere round its ring
    const a = Math.random() * Math.PI * 2, r = this.curtainR + (Math.random() - 0.5) * 0.3, amp = 0.005, size = 0.09;
    // blender's local frame (x, y) -> three (x, -z)
    this.impacts[i].set(this.center.x + Math.cos(a) * r, this.center.z - Math.sin(a) * r, age, amp * (0.7 + 0.6 * Math.random()));
    this.sizes[i] = size;
    this.life[i] = 1.2 + Math.random() * 0.8;
  }

  _step(dt) {
    const r = this.renderer, prev = r.getRenderTarget();
    this.sim.update(dt);
    this.caustics.update(this.sunDir);
    r.setRenderTarget(prev);
    const u = this.material.uniforms, sl = this.sim.slope;
    u.uSlope0.value = sl[0]; u.uSlope1.value = sl[1]; u.uSlope2.value = sl[2]; u.uSlope3.value = sl[3];
  }

  // The jets and the falling curtain are static meshes sharing the 'water_spray' material; instead of a fixed white
  // sheet, break it into streaks that run down (and up the central jet) at their own speeds, with gaps and
  // bright lumps of water, so it reads as flowing water.  Pattern is in world space: angle round the basin + height.
  _flowSpray(m) {
    if (!m) return;
    this.sprayT = { value: 0 };
    const cx = this.center.x, cz = this.center.z, cy = this.center.y, t = this.sprayT;
    patchShader(m, 'spray', (sh) => {       // stacked on the library's own patches (the atmosphere)
      sh.uniforms.uSprayT = t;
      sh.uniforms.uSprayC = { value: new THREE.Vector3(cx, cy, cz) };
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vSprayW;')
        .replace('#include <project_vertex>', '#include <project_vertex>\nvSprayW = (modelMatrix * vec4(transformed, 1.0)).xyz;');
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', `#include <common>
varying vec3 vSprayW; uniform float uSprayT; uniform vec3 uSprayC;
float sprH(float n) { return fract(sin(n * 127.1) * 43758.5453); }`)
        .replace('#include <color_fragment>', `#include <color_fragment>
{
  vec2 rel = vSprayW.xz - uSprayC.xz;
  float hy = vSprayW.y - uSprayC.y;       // height over the basin floor
  float ang = atan(rel.y, rel.x), rad = length(rel);
  float cell = floor(ang * 26.0 + rad * 9.0);
  float h = sprH(cell), h2 = sprH(cell + 31.7);
  float spd = 2.6 + 2.2 * h2;
  // the central jet runs up out of the column's top; everything else (the curtain, the arching jets) runs down
  float ph = hy * (1.1 + 0.8 * h) + (hy > ${this.B.COL_H.toFixed(2)} && rad < 0.3 ? 1.0 : -1.0) * uSprayT * spd * 0.5 + h * 9.0;
  float lump = smoothstep(0.35, 0.9, fract(ph));
  float fr = fract(ang * 26.0 + rad * 9.0);
  float thread = smoothstep(0.12, 0.5, fr) * smoothstep(0.95, 0.55, fr);
  float gap = step(0.25, h);
  diffuseColor.a *= clamp((0.12 + 0.95 * lump) * (0.35 + 0.65 * thread) * gap + 0.04, 0.0, 1.0);
}`);
    });
    m.needsUpdate = true;
  }

  // once per frame, before the scene is drawn
  update(dt, camera) {
    this.time += dt;
    if (this.sprayT) this.sprayT.value = this.time;
    this.material.uniforms.uTime.value = this.time;
    const d = camera.position.distanceTo(this.sphere.center);
    if (d > SIM_DIST) return;
    this.m4.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    this.frustum.setFromProjectionMatrix(this.m4);
    if (!this.frustum.intersectsSphere(this.sphere)) return;
    for (let i = 0; i < IMPACTS; i++) {
      this.impacts[i].z += dt;
      if (this.impacts[i].z > this.life[i]) this._spawn(i);
    }
    this.frame++;
    this.simDt = (this.simDt || 0) + dt;
    if (this.mobile && this.frame % 2) return;
    this._step(this.simDt);
    this.simDt = 0;
  }
}
