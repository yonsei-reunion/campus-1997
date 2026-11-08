// Joints between kerb stones (issue #85): materials.json "joints": the stone's length in m. The mesh's uv u runs in
// metres along the kerb (blender/road.py: 백양로's granite kerbs, u = arc length along the road; the 2010 / 2011
// roadview shows stones about 1 m long), so a thin dark joint every `piece` of u, and each stone a shade lighter or
// darker, as curbs.js does for the lawn's kerbs. The joints fade out where they get thinner than a pixel.
export function kerbJointEdit(piece) {
  const P = Number(piece).toFixed(2);
  return (sh) => {
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying float vKerbU;')
      .replace('#include <uv_vertex>', '#include <uv_vertex>\nvKerbU = uv.x;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying float vKerbU;')
      .replace('#include <map_fragment>', `#include <map_fragment>
        {
          float pc = vKerbU / ${P};
          float dj = (0.5 - abs(fract(pc) - 0.5)) * ${P};          // metres to the nearest joint
          float jw = fwidth(vKerbU);
          float joint = (1.0 - smoothstep(0.003, 0.003 + jw * 1.2, dj)) * (1.0 - smoothstep(0.02, 0.08, jw));
          float tone = 0.93 + 0.12 * fract(sin(floor(pc) * 12.9898) * 43758.5453);
          diffuseColor.rgb *= tone * (1.0 - 0.5 * joint);
        }`);
  };
}
