// Post-processing: N8AO ambient occlusion -> TAA -> eye adaptation -> small bloom -> "1997 film" grade -> tone
// mapping/sRGB output.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { Pass, FullScreenQuad } from 'three/addons/postprocessing/Pass.js';
import { N8AOPass } from 'n8ao';
import { MOBILE } from './util.js';
import { DITHER } from './materials.js';

const FilmShader = {
  uniforms: {
    tDiffuse: { value: null }, tBloom: { value: null }, uBloom: { value: 0 }, uSharp: { value: 0 },
    uTime: { value: 0 }, uFilm: { value: 0 }, uRes: { value: new THREE.Vector2(1, 1) },
    tEye: { value: null }, uEye: { value: 0 },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse, tBloom, tEye; uniform float uTime, uFilm, uBloom, uSharp, uEye; uniform vec2 uRes; varying vec2 vUv;
    float rnd(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233)) + uTime*7.0) * 43758.5453); }
    void main(){
      vec4 c = texture2D(tDiffuse, vUv);
      if (uSharp > 0.0) {
        // TAA leaves a softness of about a pixel: give it back, held within the cross round the pixel (no halos)
        vec2 e = 1.0 / uRes;
        vec3 a = texture2D(tDiffuse, vUv + vec2(e.x, 0.0)).rgb, b = texture2D(tDiffuse, vUv - vec2(e.x, 0.0)).rgb;
        vec3 u = texture2D(tDiffuse, vUv + vec2(0.0, e.y)).rgb, d = texture2D(tDiffuse, vUv - vec2(0.0, e.y)).rgb;
        vec3 s = c.rgb + uSharp * (c.rgb - (a + b + u + d) * 0.25);
        c.rgb = clamp(s, min(c.rgb, min(min(a, b), min(u, d))), max(c.rgb, max(max(a, b), max(u, d))));
      }
      // the bloom is added here (linear, before the grade and the tone mapping) instead of in a full-screen pass of its own
      vec3 bl = uBloom > 0.0 ? texture2D(tBloom, vUv).rgb * uBloom : vec3(0.0);
      // the eye's adaptation (EyeAdapt): a scale of the exposure, before the grade as a camera's would be
      float ex = uEye > 0.0 ? exp2(texture2D(tEye, vec2(0.5)).r) : 1.0;
      c.rgb = (c.rgb + bl) * ex;
      // gentle spring haze for everyone
      c.rgb = mix(c.rgb, c.rgb * vec3(1.02, 1.0, 0.97), 0.6);
      if (uFilm > 0.0) {
        vec2 d = (vUv - 0.5);
        // slight lens softness + warm 35mm print look
        vec3 blur = ((texture2D(tDiffuse, vUv + d * 0.004).rgb + texture2D(tDiffuse, vUv - d * 0.004).rgb) * 0.5 + bl) * ex;
        vec3 g = mix(c.rgb, blur, 0.5);
        float l = dot(g, vec3(0.299, 0.587, 0.114));
        g = mix(vec3(l), g, 0.82);                                 // desaturate
        // warm, lifted blacks (lifted less since the height fog hazes the distance itself: no milky double haze)
        g = g * vec3(1.08, 1.0, 0.86) + vec3(0.024, 0.014, 0.0);
        g = pow(g, vec3(0.95));
        float vig = smoothstep(0.85, 0.25, length(d * vec2(1.25, 1.0)));
        g *= mix(0.62, 1.0, vig);
        g += (rnd(vUv * uRes) - 0.5) * 0.06;                       // grain
        c.rgb = mix(c.rgb, g, uFilm);
      }
      gl_FragColor = c;
    }`,
};

// SMAA on the linear HDR colour that N8AO leaves: it has to come before the film grade (it would take the grain for
// edges), so before the tone mapping too. Edges are looked for on a display-like encoding of that colour (on raw
// linear values a dark frame on dark glass is no edge), and the two sides are mixed tone-mapped and back (Karis)
// instead of in the gamma-2.2 space the three.js port assumes for an already encoded input.
function hdrSMAA(w, h) {
  const p = new SMAAPass(w, h);
  // edges and blend weights fit in 8 bits as in the reference (the port keeps two half-float screens for them)
  for (const rt of [p.edgesRT, p.weightsRT]) rt.texture.type = THREE.UnsignedByteType;
  const e = p.materialEdges, b = p.materialBlend;
  e.fragmentShader = e.fragmentShader
    .replace(/texture2D\( colorTex, ([^)]+) \)\.rgb/g, 'smaaEnc( colorTex, $1 )')
    .replace('vec4 SMAAColorEdgeDetectionPS', `vec3 smaaEnc( sampler2D t, vec2 uv ) { vec3 c = max( texture2D( t, uv ).rgb, 0.0 ); return sqrt( c / ( 1.0 + c ) ); }
      vec4 SMAAColorEdgeDetectionPS`);
  b.fragmentShader = b.fragmentShader
    .replace('C.xyz = pow(C.xyz, vec3(2.2));', 'C.xyz /= 1.0 + max( C.x, max( C.y, C.z ) );')
    .replace('Cop.xyz = pow(Cop.xyz, vec3(2.2));', 'Cop.xyz /= 1.0 + max( Cop.x, max( Cop.y, Cop.z ) );')
    .replace('mixed.xyz = pow(mixed.xyz, vec3(1.0 / 2.2));', 'mixed.xyz /= max( 1.0 - max( mixed.x, max( mixed.y, mixed.z ) ), 1e-4 );');
  return p;
}

// A small bloom of only what is far brighter than the rest (sunlit white walls and concrete, the sky round the sun,
// bright clouds, the light on car roofs): AgX squeezes those to a flat pale grey, and a higher exposure would lift
// the shade too. Two levels only instead of UnrealBloomPass's five: a half-resolution bright pass (a tight glow) and
// a quarter-resolution Gaussian of it (a wider one, ~20 pixels), so it stays a photo's halation, not a haze. The result
// is a half-resolution texture that the film pass adds (Bloom.texture); nothing is drawn into the composer's buffers.
const quadVS = `varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;
const DownFS = `
  uniform sampler2D tSrc; uniform vec2 uTexel; uniform float uThreshold, uKnee; varying vec2 vUv;
  #ifdef PREFILTER
  // what is brighter than the threshold (luminance, so that red flowers and shirts in the sun stay out), faded in over
  // uKnee; each tap weighted down by its brightness (Karis) so that a single glint on a car does not flicker as a blob
  vec4 tap(vec2 uv) {
    vec3 c = texture2D(tSrc, uv).rgb;
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    c *= smoothstep(uThreshold, uThreshold + uKnee, l);
    float w = 1.0 / (1.0 + l);
    return vec4(c * w, w);
  }
  #else
  vec4 tap(vec2 uv) { return vec4(texture2D(tSrc, uv).rgb, 1.0); }
  #endif
  void main() {
    // four bilinear taps one source texel off the centre: a 4x4 box of the source
    vec4 s = tap(vUv + uTexel * vec2(-1.0, -1.0)) + tap(vUv + uTexel * vec2(1.0, -1.0))
           + tap(vUv + uTexel * vec2(-1.0, 1.0)) + tap(vUv + uTexel * vec2(1.0, 1.0));
    gl_FragColor = vec4(s.rgb / s.a, 1.0);
  }`;
const BlurFS = `
  uniform sampler2D tSrc; uniform vec2 uDir; varying vec2 vUv;
  void main() {
    // 9-tap Gaussian from five bilinear fetches
    gl_FragColor = vec4(texture2D(tSrc, vUv).rgb * 0.2270270270
      + (texture2D(tSrc, vUv + uDir * 1.3846153846).rgb + texture2D(tSrc, vUv - uDir * 1.3846153846).rgb) * 0.3162162162
      + (texture2D(tSrc, vUv + uDir * 3.2307692308).rgb + texture2D(tSrc, vUv - uDir * 3.2307692308).rgb) * 0.0702702703, 1.0);
  }`;
const UpFS = `
  uniform sampler2D tHalf, tQuarter; varying vec2 vUv;
  void main() { gl_FragColor = vec4((texture2D(tHalf, vUv).rgb + texture2D(tQuarter, vUv).rgb) * 0.5, 1.0); }`;

class Bloom extends Pass {
  constructor() {
    super();
    this.needsSwap = false;
    const opt = { type: THREE.HalfFloatType, depthBuffer: false };
    this.half = new THREE.WebGLRenderTarget(1, 1, opt);
    this.quarter = new THREE.WebGLRenderTarget(1, 1, opt);
    this.quarter2 = new THREE.WebGLRenderTarget(1, 1, opt);
    this.out = new THREE.WebGLRenderTarget(1, 1, opt);
    // luminance before tone mapping: sunlit white walls 1.0-1.2, the sky round the sun 1.25, sunlit paving and the
    // blue sky below 0.85, sunlit lawns and leaves below 0.5
    this.threshold = { value: 0.85 };
    this.knee = { value: 0.35 };
    const down = (prefilter) => new THREE.ShaderMaterial({
      defines: prefilter ? { PREFILTER: '' } : {},
      uniforms: { tSrc: { value: null }, uTexel: { value: new THREE.Vector2() }, uThreshold: this.threshold, uKnee: this.knee },
      vertexShader: quadVS, fragmentShader: DownFS, depthTest: false, depthWrite: false,
    });
    this.prefilter = down(true);
    this.down = down(false);
    const blur = (src) => new THREE.ShaderMaterial({
      uniforms: { tSrc: { value: src.texture }, uDir: { value: new THREE.Vector2() } },
      vertexShader: quadVS, fragmentShader: BlurFS, depthTest: false, depthWrite: false,
    });
    this.blurH = blur(this.quarter);
    this.blurV = blur(this.quarter2);
    this.up = new THREE.ShaderMaterial({
      uniforms: { tHalf: { value: this.half.texture }, tQuarter: { value: this.quarter.texture } },
      vertexShader: quadVS, fragmentShader: UpFS, depthTest: false, depthWrite: false,
    });
    this.down.uniforms.tSrc.value = this.half.texture;
    this.quad = new FullScreenQuad(null);
  }
  get texture() { return this.out.texture; }
  setSize(w, h) {
    const hw = Math.max(1, Math.ceil(w / 2)), hh = Math.max(1, Math.ceil(h / 2));
    const qw = Math.max(1, Math.ceil(w / 4)), qh = Math.max(1, Math.ceil(h / 4));
    this.half.setSize(hw, hh);
    this.out.setSize(hw, hh);
    this.quarter.setSize(qw, qh);
    this.quarter2.setSize(qw, qh);
    this.prefilter.uniforms.uTexel.value.set(1 / w, 1 / h);
    this.down.uniforms.uTexel.value.set(1 / hw, 1 / hh);
    this.blurH.uniforms.uDir.value.set(1 / qw, 0);
    this.blurV.uniforms.uDir.value.set(0, 1 / qh);
  }
  _draw(renderer, material, target) {
    this.quad.material = material;
    renderer.setRenderTarget(target);
    this.quad.render(renderer);
  }
  render(renderer, writeBuffer, readBuffer) {
    this.prefilter.uniforms.tSrc.value = this.src ?? readBuffer.texture;
    this._draw(renderer, this.prefilter, this.half);
    this._draw(renderer, this.down, this.quarter);
    this._draw(renderer, this.blurH, this.quarter2);
    this._draw(renderer, this.blurV, this.quarter);
    this._draw(renderer, this.up, this.out);
  }
}
const BLOOM = 0.2;
const SHARP = 0.6;

// Temporal anti-aliasing (the HQ path's, instead of SMAA, which kept the still frame's edges smooth but not a moving
// one's: alpha-tested leaf edges switched pixels on and off from frame to frame and whole crowns crawled as you walked).
// The projection is shifted by a sub-pixel Halton offset every frame (begin), so an edge covers a different share of
// each pixel each frame, and the resolve blends the frame into a history reprojected through the depth (the camera's
// motion; both views unjittered, so a still view reads the history in place): edges settle to their coverage.
//  - the pixel's own value is the 3x3 neighbourhood weighted by each sample's distance from the pixel centre (each
//    was drawn the jitter off it): the image does not swim with the jitter
//  - without motion vectors, what moves by itself (people, cars, swaying leaves) is held to the frame's 3x3
//    neighbourhood: variance clipping in YCoCg, on tone-mapped values so the bright sky does not outweigh the leaves
//  - history read with a 5-tap Catmull-Rom; a moving view (which resamples it every frame) takes more of the new
//    frame; the film pass gives back the remaining softness (SHARP)
//  - the foliage's near-camera dither runs through its thresholds frame by frame (materials.js DITHER): a smooth fade
const HALTON = Array.from({ length: 8 }, (_, i) => {
  const h = (b, n) => { let f = 1, r = 0; for (n += 1; n > 0; n = Math.floor(n / b)) { f /= b; r += f * (n % b); } return r; };
  return [h(2, i) - 0.5, h(3, i) - 0.5];
});
const TaaFS = /* glsl */`
  uniform sampler2D tCur, tHist, tDepth;
  uniform mat4 uReproj;               // this frame's clip -> the previous frame's (both unjittered)
  uniform vec2 uTexel, uJitter;
  uniform float uReset;
  uniform vec2 uBlend;                // the current frame's share: still, and moving 8 px a frame or more
  varying vec2 vUv;
  vec3 tm(vec3 c) { return c / (1.0 + max(c.r, max(c.g, c.b))); }
  vec3 itm(vec3 c) { return c / max(1.0 - max(c.r, max(c.g, c.b)), 1e-4); }
  vec3 ycocg(vec3 c) { return vec3(dot(c, vec3(0.25, 0.5, 0.25)), dot(c, vec3(0.5, 0.0, -0.5)), dot(c, vec3(-0.25, 0.5, -0.25))); }
  vec3 rgb(vec3 y) { return vec3(y.x + y.y - y.z, y.x + y.z, y.x - y.y - y.z); }
  vec3 cur(vec2 o) { return ycocg(tm(max(texture2D(tCur, vUv + o * uTexel).rgb, 0.0))); }
  // the history at uv, Catmull-Rom from 5 bilinear taps (the corners of the 4x4 kernel left out)
  vec3 hist(vec2 uv) {
    vec2 res = 1.0 / uTexel, p = uv * res, c = floor(p - 0.5) + 0.5, f = p - c;
    vec2 w0 = f * (-0.5 + f * (1.0 - 0.5 * f)), w1 = 1.0 + f * f * (-2.5 + 1.5 * f);
    vec2 w2 = f * (0.5 + f * (2.0 - 1.5 * f)), w3 = f * f * (-0.5 + 0.5 * f);
    vec2 w12 = w1 + w2, t0 = (c - 1.0) * uTexel, t3 = (c + 2.0) * uTexel, t12 = (c + w2 / w12) * uTexel;
    vec3 s = texture2D(tHist, vec2(t12.x, t0.y)).rgb * w12.x * w0.y
           + texture2D(tHist, vec2(t0.x, t12.y)).rgb * w0.x * w12.y
           + texture2D(tHist, t12).rgb * w12.x * w12.y
           + texture2D(tHist, vec2(t3.x, t12.y)).rgb * w3.x * w12.y
           + texture2D(tHist, vec2(t12.x, t3.y)).rgb * w12.x * w3.y;
    float w = w12.x * w0.y + w0.x * w12.y + w12.x * w12.y + w3.x * w12.y + w12.x * w3.y;
    return max(s / w, 0.0);
  }
  void main() {
    // the 3x3 neighbourhood: its mean and spread, and the pixel's own value from it, weighted by each sample's
    // distance from the pixel centre (each was drawn uJitter off it: Blackman-Harris as a Gaussian) so the image
    // does not swim with the jitter; the nearest depth of the cross: an edge moves with the thing in front
    vec3 m1 = vec3(0.0), m2 = vec3(0.0), c = vec3(0.0);
    float d = 1.0, cw = 0.0;
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
      vec2 o = vec2(float(i), float(j));
      vec3 s = cur(o);
      m1 += s; m2 += s * s;
      vec2 q = o + uJitter;
      float w = exp(-2.29 * dot(q, q));
      c += s * w; cw += w;
      if (i == 0 || j == 0) d = min(d, texture2D(tDepth, vUv + o * uTexel).r);
    }
    c /= cw;
    m1 /= 9.0;
    vec3 sd = sqrt(max(m2 / 9.0 - m1 * m1, 0.0)) * 1.25;
    vec4 p = uReproj * vec4(vUv * 2.0 - 1.0, d * 2.0 - 1.0, 1.0);
    vec2 puv = p.xy / p.w * 0.5 + 0.5;
    if (uReset > 0.5 || any(lessThan(puv, vec2(0.0))) || any(greaterThan(puv, vec2(1.0)))) {
      gl_FragColor = vec4(itm(rgb(c)), 1.0);         // (nothing to reproject: a new view, or just come into it)
      return;
    }
    vec3 h = ycocg(tm(hist(puv)));
    // clip the history towards the neighbourhood's mean, into its box
    vec3 e = h - m1, r = abs(e) / max(sd, vec3(1e-5));
    float k = max(r.x, max(r.y, r.z));
    if (k > 1.0) h = m1 + e / k;
    // a moving view resamples the history every frame (each time a little softer): a larger share of the new frame
    float a = mix(uBlend.x, uBlend.y, smoothstep(0.5, 8.0, length((puv - vUv) / uTexel)));
    gl_FragColor = vec4(itm(rgb(mix(h, c, a))), 1.0);
  }`;

class TAA extends Pass {
  constructor() {
    super();
    this.needsSwap = false;            // the next passes read this.texture (Post wires them)
    const opt = { type: THREE.HalfFloatType, depthBuffer: false, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter };
    this.rt = [new THREE.WebGLRenderTarget(1, 1, opt), new THREE.WebGLRenderTarget(1, 1, opt)];
    this.cur = 0;
    this.frame = 0;
    this.reset = true;
    this.material = new THREE.ShaderMaterial({
      uniforms: { tCur: { value: null }, tHist: { value: null }, tDepth: { value: null }, uReproj: { value: new THREE.Matrix4() },
        uTexel: { value: new THREE.Vector2() }, uJitter: { value: new THREE.Vector2() }, uReset: { value: 1 }, uBlend: { value: new THREE.Vector2(0.1, 0.2) } },
      vertexShader: quadVS, fragmentShader: TaaFS, depthTest: false, depthWrite: false,
    });
    this.quad = new FullScreenQuad(this.material);
    this.prevVP = new THREE.Matrix4();
    this.vp = new THREE.Matrix4();
    this.saved = new THREE.Matrix4();
    this.size = new THREE.Vector2(1, 1);
    this.prevPos = new THREE.Vector3(1e9, 0, 0);
    this.onOutput = null;
  }
  get texture() { return this.rt[this.cur].texture; }
  setSize(w, h) {
    for (const rt of this.rt) rt.setSize(w, h);
    this.size.set(w, h);
    this.material.uniforms.uTexel.value.set(1 / w, 1 / h);
    this.reset = true;
  }
  // before the scene is drawn: shift the projection by this frame's sub-pixel offset (undone by end())
  begin(camera) {
    const [jx, jy] = HALTON[this.frame % HALTON.length];
    DITHER.value = (this.frame++ * 0.6180339887) % 1;
    this.saved.copy(camera.projectionMatrix);
    camera.updateMatrixWorld();
    // (a jump - teleport, bird's-eye view - starts the history over)
    if (camera.position.distanceTo(this.prevPos) > 6) this.reset = true;
    this.prevPos.copy(camera.position);
    const P = camera.projectionMatrix;
    P.elements[8] += (2 * jx) / this.size.x;
    P.elements[9] += (2 * jy) / this.size.y;
    this.material.uniforms.uJitter.value.set(jx, jy);     // (the pixel then shows what lies jx, jy px off its centre)
    camera.projectionMatrixInverse.copy(P).invert();
    // the history is an unjittered image: reproject from this frame's unjittered view (a still view reads it in place)
    this.vp.multiplyMatrices(this.saved, camera.matrixWorldInverse);
    this.material.uniforms.uReproj.value.multiplyMatrices(this.prevVP, this.vp.invert());
  }
  end(camera) {
    camera.projectionMatrix.copy(this.saved);
    camera.projectionMatrixInverse.copy(this.saved).invert();
    this.prevVP.multiplyMatrices(this.saved, camera.matrixWorldInverse);
  }
  render(renderer, writeBuffer, readBuffer) {
    const u = this.material.uniforms;
    const prev = this.cur;
    this.cur = 1 - this.cur;
    u.tCur.value = readBuffer.texture;
    u.tHist.value = this.rt[prev].texture;
    u.tDepth.value = this.depth();
    u.uReset.value = this.reset ? 1 : 0;
    this.reset = false;
    renderer.setRenderTarget(this.rt[this.cur]);
    this.quad.render(renderer);
    this.onOutput?.(this.texture);
  }
}

// Eye adaptation (the HQ path with TAA; not on phones): the exposure follows the view's brightness a little, so that
// under the arcade of 중앙도서관, in the pilotis of 학생회관 or the porch of 백주년기념관 the shade opens up and the
// sunlit world outside is held back a little, and stepping out into the sun the view settles over a second or so.
//  - the TAA output's log luminance, 8x8 taps per texel into 32x16, then one mean weighted towards the middle of the
//    view, all on the GPU: nothing is read back, the film pass reads the exposure from a 1x1 target
//  - the goal is KEY minus that mean, less a dead zone, eased into +-0.3 EV (+-0.5 in the film mode, a camera's
//    automatic exposure). KEY is the mean of walking views along 백양로 (-2.1 to -2.9 by the season and the way one
//    looks, -3.1 under its trees), which so stay as they were, as do most views from above (-2.1 to -2.5).
//    The pilotis of 학생회관 read -3.1 to -4.6 (up to +0.3 EV), the porch of 백주년기념관 -3.4 (+0.24 EV), the sunlit
//    arcade of 중앙도서관 looking out over its forecourt -1.7 to -1.9 (about -0.2 EV)
//  - followed at 0.5 EV/s into the shade and 0.7 EV/s into the light, easing in over the last tenth of an EV
//  - a jump of the view (a teleport, the bird's-eye view) starts it at its goal
//  - __y97.post.adapt = false turns it off (the frame is then as without it)
const EYE_W = 32, EYE_H = 16;
const EYE_KEY = -2.55, EYE_DEAD = 0.4, EYE_GAIN = 0.75;
const EyeLumFS = `
  uniform sampler2D tSrc; varying vec2 vUv;
  float ll(vec2 uv) { return log2(max(dot(texture2D(tSrc, uv).rgb, vec3(0.2126, 0.7152, 0.0722)), 1e-4)); }
  void main() {
    // 8x8 bilinear taps spread evenly over this texel's share of the view
    float s = 0.0;
    for (int j = 0; j < 8; j++) for (int i = 0; i < 8; i++)
      s += ll(vUv + (vec2(float(i), float(j)) - 3.5) / vec2(${EYE_W * 8}.0, ${EYE_H * 8}.0));
    gl_FragColor = vec4(s / 64.0, 0.0, 0.0, 1.0);
  }`;
const EyeFS = `
  uniform sampler2D tLum, tPrev; uniform float uDt, uKey, uRange, uReset; uniform vec2 uRate; varying vec2 vUv;
  const float DEAD = ${EYE_DEAD.toFixed(3)}, GAIN = ${EYE_GAIN.toFixed(3)};
  void main() {
    // the mean log luminance, weighted towards the middle (the corners count a twentieth, the edges a fifth;
    // bilinear taps on the corners shared by four texels)
    float s = 0.0, ws = 0.0;
    for (int j = 0; j < ${EYE_H / 2}; j++) for (int i = 0; i < ${EYE_W / 2}; i++) {
      vec2 uv = (vec2(float(i), float(j)) * 2.0 + 1.0) / vec2(${EYE_W}.0, ${EYE_H}.0), d = uv - 0.5;
      float w = exp(-6.0 * dot(d, d));
      s += texture2D(tLum, uv).r * w; ws += w;
    }
    float L = s / ws;
    if (isnan(L) || isinf(L)) L = uKey;                    // (never let a stray value stick in the feedback)
    float e = uKey - L;
    float goal = sign(e) * uRange * tanh(GAIN * max(abs(e) - DEAD, 0.0) / uRange);
    float ev = texture2D(tPrev, vec2(0.5)).r;
    if (uReset > 0.5 || isnan(ev)) ev = goal;
    else {
      float de = goal - ev;
      ev += sign(de) * min(de > 0.0 ? uRate.x : uRate.y, abs(de) * 5.0) * uDt;
    }
    gl_FragColor = vec4(clamp(ev, -0.5, 0.5), L, goal, 1.0);
  }`;

class EyeAdapt extends Pass {
  constructor() {
    super();
    this.needsSwap = false;
    this.lum = new THREE.WebGLRenderTarget(EYE_W, EYE_H, { type: THREE.HalfFloatType, format: THREE.RedFormat, depthBuffer: false });
    const one = { type: THREE.FloatType, depthBuffer: false, minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter };
    this.rt = [new THREE.WebGLRenderTarget(1, 1, one), new THREE.WebGLRenderTarget(1, 1, one)];
    this.cur = 0;
    this.reset = true;
    this.src = null;
    this.onOutput = null;
    this.matLum = new THREE.ShaderMaterial({
      uniforms: { tSrc: { value: null } }, vertexShader: quadVS, fragmentShader: EyeLumFS, depthTest: false, depthWrite: false,
    });
    this.material = new THREE.ShaderMaterial({
      uniforms: { tLum: { value: this.lum.texture }, tPrev: { value: null }, uDt: { value: 0 }, uKey: { value: EYE_KEY },
        uRange: { value: 0.3 }, uReset: { value: 1 }, uRate: { value: new THREE.Vector2(0.5, 0.7) } },
      vertexShader: quadVS, fragmentShader: EyeFS, depthTest: false, depthWrite: false,
    });
    this.quad = new FullScreenQuad(null);
  }
  get texture() { return this.rt[this.cur].texture; }
  render(renderer, writeBuffer, readBuffer) {
    const u = this.material.uniforms;
    this.matLum.uniforms.tSrc.value = this.src ?? readBuffer.texture;
    this.quad.material = this.matLum;
    renderer.setRenderTarget(this.lum);
    this.quad.render(renderer);
    u.tPrev.value = this.rt[this.cur].texture;
    this.cur = 1 - this.cur;
    u.uReset.value = this.reset ? 1 : 0;
    this.reset = false;
    this.quad.material = this.material;
    renderer.setRenderTarget(this.rt[this.cur]);
    this.quad.render(renderer);
    this.onOutput?.(this.texture);
  }
  // [exposure offset EV, the weighted mean log2 luminance, the goal EV] (debugging: a synchronous read)
  read(renderer) {
    const b = new Float32Array(4);
    renderer.readRenderTargetPixels(this.rt[this.cur], 0, 0, 1, 1, b);
    return [...b.slice(0, 3)];
  }
}

export class Post {
  constructor(renderer, scene, camera) {
    const size = renderer.getDrawingBufferSize(new THREE.Vector2());
    const rt = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType });
    this.composer = new EffectComposer(renderer, rt);
    this.ao = new N8AOPass(scene, camera, size.x, size.y);
    this.ao.configuration.aoRadius = 2.2;
    this.ao.configuration.distanceFalloff = 1.0;
    this.ao.configuration.intensity = 2.2;
    this.ao.configuration.halfRes = true;
    this.ao.configuration.gammaCorrection = false;
    this.ao.setQualityMode('Medium');
    // N8AO turns on its transparency mode when the scene holds any transparent material (glass doors, car glass, the
    // tennis fence, the fountain spray): every frame it then walks the whole scene five times and draws it twice
    // more (a third of a phone's frame time) only to lift the AO off those few see-through pixels
    this.ao.autoDetectTransparency = false;
    this.ao.configuration.transparencyAware = false;
    this.render = new RenderPass(scene, camera);
    // The N8AO path has no MSAA (below), so it gets TAA (SMAA when set so: setAA('smaa'), made when first asked for),
    // and the small bloom; not on phones, where every full-screen pass counts (the RenderPass path keeps its 4x MSAA
    // and goes without bloom)
    this.smaa = null;
    this.taa = MOBILE ? null : new TAA();
    this.bloom = MOBILE ? null : new Bloom();
    this.eye = this.taa ? new EyeAdapt() : null;      // (with TAA only: it measures the TAA output)
    this.film = new ShaderPass(FilmShader);
    this.film.uniforms.tBloom.value = this.bloom?.texture ?? null;
    if (this.taa) this.taa.depth = () => this.ao.beautyRenderTarget.depthTexture;   // (N8AO draws the scene)
    if (this.taa) this.taa.onOutput = (t) => { this.film.uniforms.tDiffuse.value = t; if (this.bloom) this.bloom.src = t; this.eye.src = t; };
    if (this.eye) this.eye.onOutput = (t) => { this.film.uniforms.tEye.value = t; };
    this.output = new OutputPass();
    this.camera = camera;
    this.hq = true;
    this.aa = 'taa';
    this._build();
  }
  _build() {
    const c = this.composer;
    // MSAA only where the scene itself is drawn into the composer's targets (RenderPass). N8AO draws the scene into
    // its own single-sample target and then fills these with full-screen passes only: 4 samples there would just be
    // 4x the memory (two half-float screens) and a resolve after every pass.
    const samples = this.hq ? 0 : 4;
    for (const rt of [c.renderTarget1, c.renderTarget2]) {
      if (rt.samples !== samples) { rt.samples = samples; rt.dispose(); }
    }
    c.passes.length = 0;
    c.addPass(this.hq ? this.ao : this.render);
    const taa = this.hq && this.taa && this.aa === 'taa';
    const { width: w, height: h } = c.renderTarget1;      // (a pass left out of the list missed the resizes meanwhile)
    if (this.hq && !MOBILE && this.aa === 'smaa') {
      this.smaa ??= hdrSMAA(w, h);
      this.smaa.setSize(w, h);
      c.addPass(this.smaa);
    }
    if (taa) { this.taa.setSize(w, h); c.addPass(this.taa); c.addPass(this.eye); this.eye.reset = true; }
    if (this.hq && this.bloom) { this.bloom.setSize(w, h); c.addPass(this.bloom); }
    if (this.bloom) this.bloom.src = null;            // (set by the TAA pass each frame)
    c.addPass(this.film);
    c.addPass(this.output);
    // with TAA the bloom and the film read its history target (no copy into the composer's buffers)
    this.film.textureID = taa ? 'tTaa' : 'tDiffuse';
    this.film.uniforms.uBloom.value = this.hq && this.bloom ? BLOOM : 0;
    this.film.uniforms.uSharp.value = taa ? SHARP : 0;
    this.taaOn = taa;
    DITHER.value = 0;
  }
  setHQ(v) { this.hq = v; this._build(); }
  setAA(v) { this.aa = v; this._build(); }
  setFilm(v) {
    this.film.uniforms.uFilm.value = v ? 1 : 0;
    if (this.eye) this.eye.material.uniforms.uRange.value = v ? 0.5 : 0.3;
  }
  // the eye adaptation, on by default where there is TAA: __y97.post.adapt = false turns it off
  get adapt() { return this.eye?.enabled ?? false; }
  set adapt(v) {
    if (!this.eye || this.eye.enabled === !!v) return;
    this.eye.enabled = !!v;
    this.eye.reset = true;
  }
  setSize(w, h) {
    this.composer.setSize(w, h);
    this.film.uniforms.uRes.value.set(w * this.composer._pixelRatio, h * this.composer._pixelRatio);
  }
  draw(t) {
    const f = this.film.uniforms;
    f.uTime.value = t;
    const eye = this.taaOn && this.eye.enabled;
    f.uEye.value = eye ? 1 : 0;
    if (this.taaOn) {
      this.taa.begin(this.camera);
      if (eye) {
        // (a jump of the view starts the history over, and the adaptation at its goal)
        if (this.taa.reset) this.eye.reset = true;
        this.eye.material.uniforms.uDt.value = Math.min(0.1, Math.max(0, t - (this._t ?? t)));
      }
      this.composer.render();
      this.taa.end(this.camera);
    } else this.composer.render();
    this._t = t;
  }
}
