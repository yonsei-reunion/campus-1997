// Far trees (world.js Forest): impostors drawn with the scene's own light.
// Each tree model is rendered once (again after a season change) from 8 directions round it and from above into two
// atlases: its albedo (the leaf and bark textures x tint x the vertex AO, no light) and its normals (the crown-spherical
// normals of the leaf cards, in the model's frame) with each texel's depth along the view. The impostor is one quad per
// tree facing the camera; its fragment blends the two views nearest the direction it is seen from with the view from
// above (by the height of the view over the tree) and is lit like any other material (MeshStandardMaterial: the sun
// with its cloud shadows and the shadow map, the environment, the hemisphere light, the fog), so a far crown is bright
// on the sun's side and dark on the other, as the near trees are, from wherever it is seen. The near trees' leaves shade
// each other in the shadow map; an impostor casts nothing, so its sunlight is dimmed by the way through its own crown
// (an ellipsoid round the leaves) from the point the texel's depth puts it at, towards the sun.
// The switch between the full model and the impostor is a dithered cross-fade over the FADE metres inside the switch
// distance (with TAA on the dither runs through its thresholds, as the foliage's near-camera fade: materials.js DITHER),
// so no more full models are drawn than without it.
import * as THREE from 'three';
import { FullScreenQuad } from 'three/addons/postprocessing/Pass.js';
import { ATMOS, DITHER, derivedCopy, patchShader, pcss } from './materials.js';
import { MOBILE } from './util.js';

const VIEWS = 8;                   // directions round the tree (the first from +z, turning towards +x)
const CELL = MOBILE ? 64 : 128;    // a side view's width in texels (twice that high); the view from above CELL x CELL
const W = 4 * CELL, H = 5 * CELL;  // 4 x 2 side views, the view from above in a third row
export const FADE = 30;            // metres of cross-fade between the model and its impostor
// the side views' share falls to the view from above between these heights of the view over the tree (radians)
const EL = [0.55, 1.25];
const DENSITY = 0.4;               // how fast the sunlight thins through a crown (1/m)

// where the trees switch: x, z (three) of the LOD centre, the switch distance, FADE. Forest.update sets it when it sorts
// the trees, so the fade always agrees with which trees have which form
export const LOD = { value: new THREE.Vector4(0, 0, 230, FADE) };

// the dither both sides of the cross-fade read (complementary: a pixel is the model's or the impostor's)
const FADE_GLSL = /* glsl */`
  float impFade( vec2 o ) {
    return smoothstep( uImpLod.z - uImpLod.w, uImpLod.z, distance( o, uImpLod.xy ) );
  }`;
const DITHER_GLSL = 'fract( dot( floor( gl_FragCoord.xy ), vec2( 0.0671, 0.00584 ) ) * 52.98 + uImpDither )';

// ---------------------------------------------------------------------------- the near trees
// The full models' materials: a copy of each library material (bark is shared with the shrubs, which never fade)
// that dithers out where the impostor takes over; the leaves' copies follow the season like the originals.
// The leaf cards are wound against their crown-spherical normals (blender/vegetation.py: a card's face normal points
// into the crown), so from outside a crown three saw their back faces and turned the normal inwards: the sunlit side
// of a crown took no sun and the side away from it did. The copies keep the crown normal on both faces (the bake too).
const NEAR = new WeakMap();
export function nearTreeMaterial(lib, m) {
  if (lib.mats.get(m.name) !== m) return lib.instanced(m);
  let v = NEAR.get(m);
  if (!v) {
    v = derivedCopy(m);
    const leaf = !!m.userData.species;
    patchShader(v, leaf ? 'forestLeaf' : 'forestNear', (sh) => {
      sh.uniforms.uImpLod = LOD;
      sh.uniforms.uImpDither = DITHER;
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', `#include <common>\nuniform vec4 uImpLod;\nvarying float vImpFade;\n${FADE_GLSL}`)
        .replace('#include <begin_vertex>', `#include <begin_vertex>
          #ifdef USE_INSTANCING
          vImpFade = impFade( instanceMatrix[ 3 ].xz );
          #else
          vImpFade = 0.0;
          #endif`);
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform float uImpDither;\nvarying float vImpFade;')
        .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>
          if ( vImpFade > 0.0 && ${DITHER_GLSL} < vImpFade ) discard;`);
      if (leaf) {
        sh.fragmentShader = sh.fragmentShader.replace('#include <normal_fragment_begin>', `#include <normal_fragment_begin>
          #ifdef DOUBLE_SIDED
          normal *= faceDirection;
          #endif`);
      }
    });
    if (lib.leafMats.includes(m)) lib.leafMats.push(v);
    NEAR.set(m, v);
  }
  return v;
}

// ---------------------------------------------------------------------------- the impostor material
const IMP_VERT = /* glsl */`
  uniform vec4 uImpBox;     // the views' half width, their bottom and top, the crown centre's height (model units)
  uniform vec2 uImpQuad;    // the quad's bottom and top from the crown centre
  uniform vec4 uImpLod;
  uniform vec2 uImpEl;
  varying vec2 vImpAB;      // the point on the quad from the crown centre (model units: right, up on screen)
  varying vec4 vImpV;       // the first of the two side views, the share of the second, the top's share, the fade
  varying vec4 vImpR;       // the model's x axis in world xz (the tree's turn), the screen's right in model xz
  ${FADE_GLSL}`;
// (an InstancedMesh at the origin: the instance matrix is the model -> world transform, a turn about y and a scale)
const IMP_BILLBOARD = /* glsl */`
  vec3 impO = instanceMatrix[ 3 ].xyz;
  float impS = length( instanceMatrix[ 0 ].xyz );
  vec2 impX = instanceMatrix[ 0 ].xz / impS;
  #define IMP_TO_MODEL( v ) vec3( impX.x * ( v ).x + impX.y * ( v ).z, ( v ).y, impX.x * ( v ).z - impX.y * ( v ).x )
  vec3 impC = impO + vec3( 0.0, uImpBox.w * impS, 0.0 );
  vec3 impToCam = cameraPosition - impC;
  vec3 impR = vec3( viewMatrix[ 0 ].x, viewMatrix[ 1 ].x, viewMatrix[ 2 ].x );   // the camera's right and up (world)
  vec3 impU = vec3( viewMatrix[ 0 ].y, viewMatrix[ 1 ].y, viewMatrix[ 2 ].y );
  // the views: which two round the tree, and how much of the one from above
  vec3 impM = IMP_TO_MODEL( impToCam );
  float impAz = atan( impM.x, impM.z ) * ${(VIEWS / (2 * Math.PI)).toFixed(6)};
  impAz += impAz < 0.0 ? ${VIEWS.toFixed(1)} : 0.0;
  float impK = min( floor( impAz ), ${(VIEWS - 1).toFixed(1)} );
  float impEl = asin( clamp( impToCam.y / max( length( impToCam ), 1e-3 ), -1.0, 1.0 ) );
  vImpV = vec4( impK, impAz - impK, smoothstep( uImpEl.x, uImpEl.y, impEl ), impFade( impO.xz ) );
  vec3 impRM = IMP_TO_MODEL( impR );
  vImpR = vec4( impX, normalize( impRM.xz + vec2( 1e-6, 0.0 ) ) );
  vImpAB = vec2( mix( - uImpBox.x, uImpBox.x, position.x ), mix( uImpQuad.x, uImpQuad.y, position.y ) );
  vec3 impPos = IMP_TO_MODEL( ( impC - impO ) / impS + impR * vImpAB.x + impU * vImpAB.y );
  vec3 objectNormal = IMP_TO_MODEL( cross( impR, impU ) );`;

const IMP_FRAG = /* glsl */`
  uniform sampler2D uImpAlb, uImpNrm;
  uniform vec4 uImpBox;
  uniform vec4 uImpCrown;   // the leaves' ellipsoid: radius across, half height; the depths' scale; its density (1/m)
  uniform vec3 uImpSun;     // towards the sun (world)
  uniform float uImpDither;
  varying vec2 vImpAB;
  varying vec4 vImpV;
  varying vec4 vImpR;
  // the atlas: side views in 4 columns x 2 rows (each 1/4 x 2/5 of it), the view from above over them (1/4 x 1/5)
  vec2 impSide( float k, vec2 uv ) { return ( vec2( mod( k, 4.0 ), floor( k / 4.0 ) ) + uv ) * vec2( 0.25, 0.4 ); }
  vec2 impTop( vec2 uv ) { return vec2( uv.x * 0.25, 0.8 + uv.y * 0.2 ); }
  float impIn( vec2 uv ) { return step( 0.0, uv.x ) * step( uv.x, 1.0 ) * step( 0.0, uv.y ) * step( uv.y, 1.0 ); }
  vec3 impNormal;
  float impSun;`;

// The atlases hold colour x coverage (cleared to 0, so their mip levels average the colour of the covered texels only):
// the blend of the views is a blend of premultiplied samples, divided by the coverage at the end.
const IMP_SAMPLE = /* glsl */`
  if ( ${DITHER_GLSL} >= vImpV.w ) discard;
  {
    float k = floor( vImpV.x + 0.5 ), t = vImpV.y, top = vImpV.z;
    vec2 ab = vImpAB;
    vec2 su = vec2( ( ab.x + uImpBox.x ) / ( 2.0 * uImpBox.x ), ( ab.y + uImpBox.w - uImpBox.y ) / ( uImpBox.z - uImpBox.y ) );
    // from above: the screen's right and (on the ground) its up, in the model's frame; the view's +x right, -z up
    vec2 rt = vImpR.zw, X = ab.x * rt + ab.y * vec2( rt.y, - rt.x );
    vec2 tu = vec2( X.x, - X.y ) / ( 2.0 * uImpBox.x ) + 0.5;
    float ws = ( 1.0 - top ) * impIn( su ), wt = top * impIn( tu );
    vec2 uv0 = impSide( k, su ), uv1 = impSide( mod( k + 1.0, ${VIEWS.toFixed(1)} ), su ), uv2 = impTop( tu );
    vec4 alb = ( texture2D( uImpAlb, uv0 ) * ( 1.0 - t ) + texture2D( uImpAlb, uv1 ) * t ) * ws + texture2D( uImpAlb, uv2 ) * wt;
    vec4 nrm = ( texture2D( uImpNrm, uv0 ) * ( 1.0 - t ) + texture2D( uImpNrm, uv1 ) * t ) * ws + texture2D( uImpNrm, uv2 ) * wt;
    float cov = max( alb.a, 1e-4 );
    diffuseColor.rgb *= alb.rgb / cov;
    // the coarser the mip level, the thinner its averaged coverage: a lower cut keeps a far crown as full as a near one
    // (the material's alpha test is at 0.5)
    float lod = log2( max( length( dFdx( ab ) ), length( dFdy( ab ) ) ) * ${CELL.toFixed(1)} / ( 2.0 * uImpBox.x ) );
    diffuseColor.a *= alb.a * 0.5 / mix( 0.5, 0.22, smoothstep( 0.5, 4.0, lod ) );
    vec3 n = normalize( nrm.rgb / cov * 2.0 - 1.0 + vec3( 0.0, 1e-4, 0.0 ) );
    vec2 x = vImpR.xy;                                  // model -> world: the tree's turn about y
    impNormal = normalize( ( viewMatrix * vec4( x.x * n.x - x.y * n.z, n.y, x.y * n.x + x.x * n.z, 0.0 ) ).xyz );
    // where the texel is in the crown (from its centre, model frame): across the screen, and its depth towards the
    // camera (side views) or its height (from above); then the way from there through the crown towards the sun
    float d = ( nrm.a / cov - 0.5 ) * 2.0 * uImpCrown.z;
    vec2 tc = vec2( - rt.y, rt.x );
    vec3 p = mix( vec3( ab.x * rt.x + d * tc.x, ab.y, ab.x * rt.y + d * tc.y ), vec3( X.x, d, X.y ), wt / max( ws + wt, 1e-4 ) );
    vec3 sm = vec3( x.x * uImpSun.x + x.y * uImpSun.z, uImpSun.y, x.x * uImpSun.z - x.y * uImpSun.x );
    vec3 q = p / uImpCrown.xyx, l = sm / uImpCrown.xyx;
    float qa = dot( l, l ), qb = dot( q, l ), qc = dot( q, q ) - 1.0, disc = qb * qb - qa * qc;
    impSun = exp( - uImpCrown.w * max( disc > 0.0 ? ( sqrt( disc ) - qb ) / qa : 0.0, 0.0 ) );
  }`;

const SUN_LINE = 'getDirectionalLightInfo( directionalLight, directLight );';
function impostorMaterial(key, box, quad, crown, alb, nrm) {
  const m = new THREE.MeshStandardMaterial({ roughness: 0.85, metalness: 0, alphaTest: 0.5 });
  m.name = 'impostor_' + key;          // (bakedshadow.js: no baked ground shadow on it)
  patchShader(m, 'impostor', (sh) => {
    Object.assign(sh.uniforms, {
      uImpAlb: { value: alb }, uImpNrm: { value: nrm }, uImpBox: { value: box }, uImpQuad: { value: quad },
      uImpCrown: { value: crown }, uImpSun: ATMOS.uSunW, uImpLod: LOD, uImpEl: { value: new THREE.Vector2(...EL) },
      uImpDither: DITHER,
    });
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>\n${IMP_VERT}`)
      .replace('#include <beginnormal_vertex>', IMP_BILLBOARD)
      .replace('#include <begin_vertex>', 'vec3 transformed = impPos;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>\n${IMP_FRAG}`)
      .replace('#include <map_fragment>', IMP_SAMPLE)
      .replace('#include <normal_fragment_maps>', 'normal = impNormal;')
      // the foliage's glow (materials.js foliage)
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += diffuseColor.rgb * 0.09;')
      // (the lights chunk expanded to reach the sun's line; impostors take no baked sun shadow, bakedshadow.js, which
      // expands it too)
      .replace('#include <lights_fragment_begin>', THREE.ShaderChunk.lights_fragment_begin
        .replace(SUN_LINE, `${SUN_LINE}\ndirectLight.color *= impSun;`));
  });
  return pcss(m);
}

// one quad, (0, 0) - (1, 1): the vertex shader spreads it over the tree, facing the camera
let quadGeo = null;
function quad() {
  if (!quadGeo) {
    quadGeo = new THREE.BufferGeometry();
    quadGeo.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0], 3));
    quadGeo.setAttribute('normal', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1], 3));
    quadGeo.setIndex([0, 1, 2, 0, 2, 3]);
  }
  return quadGeo;
}

// ---------------------------------------------------------------------------- one tree model's impostor
export class Impostor {
  // src: the model (its library materials), capacity: how many trees of it
  constructor(key, src, capacity) {
    src.updateMatrixWorld(true);
    // its extent round the trunk (the y axis) and the crown's centre (the leaves' middle height)
    let r = 0, rl = 0, y0 = Infinity, y1 = -Infinity, l0 = Infinity, l1 = -Infinity;
    const v = new THREE.Vector3();
    src.traverse((o) => {
      if (!o.isMesh) return;
      const p = o.geometry.attributes.position, leaf = !!o.material.userData.species;
      for (let i = 0; i < p.count; i++) {
        v.fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld);
        r = Math.max(r, Math.hypot(v.x, v.z));
        y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y);
        if (leaf) { l0 = Math.min(l0, v.y); l1 = Math.max(l1, v.y); rl = Math.max(rl, Math.hypot(v.x, v.z)); }
      }
    });
    if (l0 > l1) { l0 = y0; l1 = y1; rl = r; }
    const R = r * 1.04, pad = (y1 - y0) * 0.02, Y0 = y0 - pad, Y1 = y1 + pad, yc = (l0 + l1) / 2;
    this.box = new THREE.Vector4(R, Y0, Y1, yc);
    this.crown = new THREE.Vector4(rl, (l1 - l0) / 2, Math.max(R, Y1 - yc, yc - Y0), DENSITY);
    this.quad = new THREE.Vector2(Math.min(Y0 - yc, -R), Math.max(Y1 - yc, R));
    // the cameras of the views: round the tree from +z towards +x, and from above (+x right, -z up)
    const D = R + 50;
    this.cams = Array.from({ length: VIEWS }, (_, k) => {
      const a = (k / VIEWS) * Math.PI * 2;
      const c = new THREE.OrthographicCamera(-R, R, Y1, Y0, 1, 2 * D);
      c.position.set(Math.sin(a) * D, 0, Math.cos(a) * D);
      c.lookAt(0, 0, 0);
      c.updateMatrixWorld();
      return c;
    });
    const top = new THREE.OrthographicCamera(-R, R, R, -R, 1, Y1 - Y0 + 100);
    top.up.set(0, 0, -1);
    top.position.set(0, Y1 + 50, 0);
    top.lookAt(0, Y0, 0);
    top.updateMatrixWorld();
    this.cams.push(top);
    // the atlases: no depth (the views are drawn into a shared target first), mipmapped
    const opt = { depthBuffer: false, generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter, magFilter: THREE.LinearFilter };
    this.alb = new THREE.WebGLRenderTarget(W, H, opt);
    this.alb.texture.colorSpace = THREE.SRGBColorSpace;
    this.nrm = new THREE.WebGLRenderTarget(W, H, opt);
    for (const t of [this.alb.texture, this.nrm.texture]) t.anisotropy = 4;
    this.model = src.clone(true);
    this.material = impostorMaterial(key, this.box, this.quad, this.crown, this.alb.texture, this.nrm.texture);
    this.im = new THREE.InstancedMesh(quad(), this.material, capacity);
    this.im.count = 0;
    this.im.castShadow = false;
    this.im.receiveShadow = true;
    this.im.frustumCulled = false;
    this.im.name = 'impostor_' + key;
  }
}

// ---------------------------------------------------------------------------- drawing the atlases
// The views' materials: the source material's albedo (colour x map x vertex colour = the AO) or its normal (the
// model's frame; the bark's flipped on a back face as three lights it, the leaves' not: see nearTreeMaterial),
// alpha-tested like it.
const BAKE_VERT = /* glsl */`
  #include <common>
  #include <color_pars_vertex>
  uniform mat3 uvTransform;
  varying vec2 vUv;
  varying vec3 vN, vP;
  void main() {
    #include <color_vertex>
    vUv = ( uvTransform * vec3( uv, 1.0 ) ).xy;
    vN = mat3( modelMatrix ) * normal;
    vP = ( modelMatrix * vec4( position, 1.0 ) ).xyz;
    gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
  }`;
const BAKE_FRAG = /* glsl */`
  #include <common>
  #include <color_pars_fragment>
  uniform vec3 diffuse;
  uniform sampler2D map;
  uniform float alphaTest;
  uniform vec4 uView;       // towards the view's camera; the crown centre's height
  uniform float uDepth;     // the depths' scale
  varying vec2 vUv;
  varying vec3 vN, vP;
  void main() {
    vec4 diffuseColor = vec4( diffuse, 1.0 );
    #ifdef USE_MAP
    diffuseColor *= texture2D( map, vUv );
    #endif
    #include <color_fragment>
    if ( diffuseColor.a < alphaTest ) discard;
    #ifdef BAKE_NORMAL
    vec3 n = normalize( vN );
    #ifdef BAKE_FLIP
    n *= gl_FrontFacing ? 1.0 : - 1.0;
    #endif
    // the depth: towards the camera from the crown centre (from above: the height over it)
    gl_FragColor = vec4( n * 0.5 + 0.5, 0.5 + 0.5 * dot( vP - vec3( 0.0, uView.w, 0.0 ), uView.xyz ) / uDepth );
    #else
    gl_FragColor = vec4( diffuseColor.rgb, 1.0 );
    #endif
  }`;
const bakeMats = new WeakMap();
const VIEW = { uView: { value: new THREE.Vector4() }, uDepth: { value: 1 } };   // set for each view
function bakeMaterials(m) {
  let b = bakeMats.get(m);
  if (!b) {
    const uniforms = { diffuse: { value: new THREE.Color() }, map: { value: null }, uvTransform: { value: new THREE.Matrix3() },
      alphaTest: { value: 0 }, ...VIEW };
    const make = (normal) => new THREE.ShaderMaterial({
      uniforms, vertexShader: BAKE_VERT, fragmentShader: BAKE_FRAG, side: m.side, vertexColors: m.vertexColors,
      defines: { ...(normal ? { BAKE_NORMAL: '' } : {}), ...(m.side === THREE.DoubleSide && !m.userData.species ? { BAKE_FLIP: '' } : {}) },
    });
    b = { uniforms, albedo: make(false), normal: make(true), map: undefined };
    bakeMats.set(m, b);
  }
  // the source's current colour and leaf texture (setSeason swaps both)
  const u = b.uniforms;
  u.diffuse.value.copy(m.color);
  u.alphaTest.value = m.alphaTest;
  u.map.value = m.map;
  if (m.map) {
    if (m.map.matrixAutoUpdate) m.map.updateMatrix();
    u.uvTransform.value.copy(m.map.matrix);
  }
  if (b.map !== !!m.map) {
    b.map = !!m.map;
    for (const x of [b.albedo, b.normal]) {
      x.defines.USE_MAP = b.map ? '' : undefined;
      if (!b.map) delete x.defines.USE_MAP;
      x.needsUpdate = true;
    }
  }
  return b;
}

let copy = null;
// (re)draw the atlases of these impostors from their models, e.g. after a season change swapped the leaf textures
export function renderImpostors(renderer, impostors) {
  const target = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, depthBuffer: true, generateMipmaps: false,
    minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter });
  copy ??= new FullScreenQuad(new THREE.ShaderMaterial({
    uniforms: { tSrc: { value: null } },
    vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4( position.xy, 0.0, 1.0 ); }',
    fragmentShader: 'uniform sampler2D tSrc; varying vec2 vUv; void main() { gl_FragColor = texture2D( tSrc, vUv ); }',
    blending: THREE.NoBlending, depthTest: false, depthWrite: false,
  }));
  const scene = new THREE.Scene();
  const prevTarget = renderer.getRenderTarget(), prevAuto = renderer.autoClear;
  const prevClear = renderer.getClearColor(new THREE.Color()), prevAlpha = renderer.getClearAlpha();
  renderer.autoClear = false;
  renderer.setClearColor(0x000000, 0);
  for (const imp of impostors) {
    scene.add(imp.model);
    const meshes = [];
    imp.model.traverse((o) => { if (o.isMesh) meshes.push([o, bakeMaterials(o.userData.src ??= o.material)]); });
    for (const [pass, dest] of [['albedo', imp.alb], ['normal', imp.nrm]]) {
      for (const [o, b] of meshes) o.material = b[pass];
      target.viewport.set(0, 0, W, H);
      renderer.setRenderTarget(target);
      renderer.clear();
      imp.cams.forEach((cam, k) => {
        VIEW.uView.value.set(...cam.position.clone().normalize().toArray(), imp.box.w);
        VIEW.uDepth.value = imp.crown.z;
        if (k < VIEWS) target.viewport.set((k % 4) * CELL, Math.floor(k / 4) * 2 * CELL, CELL, 2 * CELL);
        else target.viewport.set(0, 4 * CELL, CELL, CELL);
        renderer.setRenderTarget(target);
        renderer.render(scene, cam);
      });
      target.viewport.set(0, 0, W, H);
      copy.material.uniforms.tSrc.value = target.texture;
      renderer.setRenderTarget(dest);
      copy.render(renderer);                // (and its mip levels)
    }
    scene.remove(imp.model);
  }
  renderer.setRenderTarget(prevTarget);
  renderer.setClearColor(prevClear, prevAlpha);
  renderer.autoClear = prevAuto;
  target.dispose();
}
