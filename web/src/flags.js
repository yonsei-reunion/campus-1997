// The white flag's cloth (prop flag_white, blender/props.py: material flag_cloth) in the wind, as the banners' over
// 백양로 (life.js bannerWind): the trees' clock and slow gust swell, a slow belly and quicker ripples running from the
// pole to the free edge and down, the normal tilted with the slope so the folds catch the light, and the shadow map
// looked up where the cloth rests (materials.js restShadow). The cloth's UVs say where it is held: u from the pole
// (0) to the free edge (1), v down from the bar it hangs on (three's flipped v: 0 at the bar); held along both, its far
// bottom corner swings most (about 15 cm). It moves along the flag's plane (local z), so its strips stay together.
// Only the instanced prop moves: the museum banners merged into 백주년기념관 (blender/landmarks.py) share the
// material but are single quads, and stay still.
import { patchShader, restShadow, windTime } from './materials.js';

const FLAG_GLSL = /* glsl */`
  #define FLAG_W 1.0
  #define FLAG_H 2.3
  // offset along the cloth's normal (m) at q (uv), P: the flag's phase, gust: the trees' slow swell
  float flagD(vec2 q, float P, float gust) {
    float T = uWindT, a = q.x * FLAG_W, b = q.y * FLAG_H;
    float w = pow(clamp(q.y, 0.0, 1.0), 0.8) * smoothstep(0.0, 0.9, q.x);
    float d = 0.09 * sin(T * 1.7 + P - b * 0.9) + 0.05 * sin(T * 4.2 - a * 3.0 - b * 1.2 + P)
      + 0.02 * sin(T * 7.1 - a * 6.0 - b * 2.0 + P * 1.3);
    return w * d * gust;
  }`;

export function flagWind(lib) {
  const m = lib.get('flag_cloth');
  patchShader(m, 'flagWind', (sh) => {
    sh.uniforms.uWindT = windTime;
    const vs = sh.vertexShader, decl = vs.includes('uniform float uWindT;') ? '' : '\nuniform float uWindT;';
    sh.vertexShader = restShadow(vs
      .replace('#include <common>', `#include <common>
        #ifdef USE_INSTANCING${decl}${FLAG_GLSL}
        #endif`)
      .replace('#include <beginnormal_vertex>', `#include <beginnormal_vertex>
        vec3 flagN = vec3(0.0, 0.0, 1.0);                         // the cloth's plane (its strips fold a little)
        float flagWd = 0.0;
        #ifdef USE_INSTANCING
        {
          vec3 o = (modelMatrix * vec4(instanceMatrix[3].xyz, 1.0)).xyz;
          float gust = 0.7 + 0.3 * sin(uWindT * 0.21 - dot(o.xz, vec2(0.92, -0.38)) * 0.01);
          float P = dot(o.xz, vec2(0.37, 0.53));
          flagWd = flagD(uv, P, gust);
          float sx = (flagD(uv + vec2(0.02, 0.0), P, gust) - flagWd) / (0.02 * FLAG_W);   // slope away from the pole
          float sy = (flagD(uv + vec2(0.0, 0.02), P, gust) - flagWd) / (0.02 * FLAG_H);   // and down
          // (u runs to local -x, v down)
          objectNormal = normalize(objectNormal - dot(objectNormal, flagN) * vec3(-sx, -sy, 0.0));
        }
        #endif`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        transformed += flagN * flagWd;
        vec3 windW = vec3(0.0);
        #ifdef USE_INSTANCING
          windW = mat3(modelMatrix) * mat3(instanceMatrix) * (flagN * flagWd);
        #endif`));
  });
}
