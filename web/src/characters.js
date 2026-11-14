// People: Quaternius CC0 modular characters (blender/characters.py) driven by the shared rig clips,
// in the manner of the sim-office engine (actors.js): a holder group, an AnimationMixer per person,
// cross-faded clips, and walk/run cycles whose playback speed follows the ground speed (no foot sliding).
import * as THREE from 'three';
import { clone as skeletonClone } from 'three/addons/utils/SkeletonUtils.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { loadGLB } from './world.js';
import { pcss, windTime } from './materials.js';
import { HERO_BAGS, baggedGeometry } from './bags.js';
import { MOBILE, mulberry, versioned } from './util.js';

export const PEOPLE = {
  'man-tee': '흰 티 · 청바지',
  'man-check': '줄무늬 티',
  'man-cheer': '파란 점퍼',
  'man-hoodie': '남색 후드티',
  'man-grey': '아이보리 점퍼',
  'man-blazer': '콤비 재킷',
  'man-professor': '교수님',
  'man-staff': '교직원',
  'woman-tee': '흰 티 · 청바지',
  'woman-pink': '분홍 니트',
  'woman-dress': '흰 니트 · 치마',
  'woman-dress-blue': '배꼽티 · 청바지',
  'woman-cardigan': '노란 카디건',
  'woman-staff': '교직원',
};
export const STUDENTS = ['man-tee', 'man-check', 'man-cheer', 'man-hoodie', 'man-grey', 'man-blazer',
  'woman-tee', 'woman-pink', 'woman-dress', 'woman-dress-blue', 'woman-cardigan'];
export const HEROES = ['man-tee', 'man-cheer', 'man-check', 'woman-tee', 'woman-dress', 'woman-cardigan'];

// Every part of a person (skin, clothes, hair ...) is a flat colour, so one vertex-coloured material serves
// everyone and each person is a single SkinnedMesh: one draw call (and one in the shadow pass) instead of 6-10.
// What a vertex is rides along as the attribute `part`: its roughness, its kind (KIND: cloth, skin, hair, or a
// hard thing: shoes, glasses, a bag) and how shut in it is by the rest of the person (blender/characters.py
// occlude(): the hair over the brow, the chin over the throat, sleeves, hems, the legs beside each other).
// The shader makes of the flat colours what they are (PERSON_MAT.onBeforeCompile):
//  - the shut-in places are shaded (the sky's light and its mirror image all the way, the sun's less), skin warmly
//  - cloth is unevenly dyed and worn, takes a soft light at grazing angles (its fuzz), and folds: trousers stack up
//    at the ankle and crease at the knee and the crotch, tops drape. The folds are a height over the rest pose
//    (bumped), so they stay on the cloth as it moves; they fade where a fold is smaller than a pixel
//  - skin has a little sheen, hair has strands (running down from the crown) in its colour and its gloss
// Phones go without the folds and the strands (no noise in the fragment shader there).
// The eyes, brows and mouths are a few lines drawn on one small atlas all the people share (blender/faces.py): the
// front of a face lies on its own cell, everything else on the blank cell, and the picture multiplies the vertex
// colour. So the lines keep to whatever skin a person of the crowd has, and fade into it with distance (mip maps).
// The picture's alpha is how much of that shows: the rest is the white of the eye.
// Glasses: everybody's model has a pair, a few millimetres thin. Thinner than a pixel, they glitter on and off from
// frame to frame where nothing smooths the edges (phones have no anti-aliasing, nor TAA): so a person who wears glasses
// has the rims' geometry drawn only while the rims are RIM_PX pixels or more across (rimLod: the index puts the glasses'
// triangles last, and the draw stops short of them), and from somewhat nearer than that on the same glasses drawn on
// the face from a second atlas (faces_rims.png), which the mip maps fade evenly with distance. Who wears them, and
// which rims, rides along as the attribute `glass` (0 none, 1 thin metal, 2 dark horn; plus 4 x the person's blink).
// Blinking: every few seconds (each of the BLINKS kinds of the crowd in its own time) the eyes of a face are drawn
// shut for an eighth of a second: skin over the eye's place on the cell and the lashes' line, sagging in the middle.
// By the clock of the wind; the line only from near.
const KIND = { cloth: 0, skin: 1, hair: 2, hard: 3 };
const kindOfPart = (name) => (name === 'Skin' ? KIND.skin : /^(Hair|Bridge)/.test(name) ? KIND.hair : /Glasses|feet/.test(name) ? KIND.hard : KIND.cloth);
const SKIN_ROUGH = 0.5;
const PERSON_MAT = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, metalness: 0, envMapIntensity: 0.8 });
PERSON_MAT.name = 'person';
const FACE_BIAS = '-0.75', EYE_WHITE = '0.84, 0.83, 0.80';     // (faces.py WHITE)
const BLANK_UV = 0.875;            // the middle of the atlas' blank cell (u and v): faces.py BLANK
const RIM_W = 0.0022;              // the rims' thickness in the game, m (faces.py RIM_T, scaled as the people)
const RIM_UV = 0.004;              // the same on the atlas: RIM_T / (2 HALF) / GRID
const RIM_PX = MOBILE ? 1.2 : 0.35;   // the rims' geometry from this many pixels across (desktop: TAA resolves less)
const RIMS = ['#77736c', '#2a2420'];  // thin metal, dark horn (crowdLook picks one; the shader's drawn ones alike)
const glsl = (hex) => { const c = new THREE.Color(hex); return `vec3(${c.r.toFixed(4)}, ${c.g.toFixed(4)}, ${c.b.toFixed(4)})`; };
const RIMS_TEX = { value: null };
const BLINKS = 16;
// the eye on a cell of the atlas (blender/faces.py: a cell is 2 HALF = 15 cm of the face, the eye line TOP under its
// top): the middle of an eye from the nose, its half width and height, as fractions of the cell
const EYE_U = 0.036 / 0.15, EYE_V = 0.042 / 0.15, EYE_A = 0.021 / 0.15, EYE_B = 0.013 / 0.15;
function loadTexture(file, srgb) {
  return new Promise((res, rej) => new THREE.TextureLoader().load(versioned(PEOPLE_DIR + file), (t) => {
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    t.flipY = false;               // (glTF texture coordinates: v from the top)
    t.anisotropy = 4;
    res(t);
  }, undefined, rej));
}
async function loadFaces() {
  // (without the drawn glasses the far ones are only left out: no reason to hold the people up)
  const [face, rims] = await Promise.all([loadTexture('faces.png', true), loadTexture('faces_rims.png', false).catch(() => null)]);
  PERSON_MAT.map = face;
  RIMS_TEX.value = rims;
  PERSON_MAT.needsUpdate = true;
}
const GRID_F = '4.0';                  // (faces.py GRID)
const FINE = !MOBILE;               // the folds of cloth and the strands of hair
PERSON_MAT.onBeforeCompile = (sh) => {
  sh.uniforms.uRims = RIMS_TEX;
  sh.uniforms.uBlinkT = windTime;
  sh.vertexShader = sh.vertexShader
    .replace('#include <common>', '#include <common>\nattribute vec3 part;\nattribute float glass;\nvarying vec3 vPart, vRest;\nvarying float vGlass;')
    .replace('#include <begin_vertex>', '#include <begin_vertex>\nvPart = part;\nvGlass = glass;\nvRest = position;');
  sh.fragmentShader = sh.fragmentShader
    .replace('#include <common>', `#include <common>
      varying vec3 vPart, vRest;
      varying float vGlass;
      uniform sampler2D uRims;
      uniform float uBlinkT;
      ${FINE ? `
      float pHash( vec3 p ) { p = fract( p * 0.3183099 + 0.1 ); p *= 17.0; return fract( p.x * p.y * p.z * ( p.x + p.y + p.z ) ); }
      float pNoise( vec3 x ) { vec3 i = floor( x ), f = fract( x ); f = f * f * ( 3.0 - 2.0 * f );
        return mix( mix( mix( pHash( i ), pHash( i + vec3( 1, 0, 0 ) ), f.x ), mix( pHash( i + vec3( 0, 1, 0 ) ), pHash( i + vec3( 1, 1, 0 ) ), f.x ), f.y ),
                    mix( mix( pHash( i + vec3( 0, 0, 1 ) ), pHash( i + vec3( 1, 0, 1 ) ), f.x ), mix( pHash( i + vec3( 0, 1, 1 ) ), pHash( i + vec3( 1, 1, 1 ) ), f.x ), f.y ), f.z ); }
      // the height of the folds of cloth (m) over the rest pose (y up, m): trousers stack up at the ankle and crease
      // behind the knee and at the crotch, tops drape and gather at the hem
      float pFolds( vec3 p ) {
        float n1 = pNoise( p * vec3( 13.0, 4.0, 13.0 ) ), n2 = pNoise( p * vec3( 5.0, 9.0, 5.0 ) + 7.0 );
        float legs = step( p.y, 0.93 );
        float stack = sin( p.y * 96.0 + 8.0 * n1 ) * smoothstep( 0.30, 0.08, p.y ) * ( 0.35 + 0.9 * n2 );
        float knee = sin( p.y * 74.0 + 6.0 * n1 + p.x * 20.0 ) * exp( - pow( ( p.y - 0.50 ) / 0.09, 2.0 ) ) * 0.45;
        float crotch = sin( ( p.y + abs( p.x ) * 0.8 ) * 86.0 + 4.0 * n2 ) * exp( - pow( ( p.y - 0.84 ) / 0.07, 2.0 ) ) * 0.6;
        float top = ( pNoise( p * vec3( 11.0, 17.0, 11.0 ) ) - 0.5 ) * 1.4 + sin( p.y * 64.0 + 5.0 * n1 ) * exp( - pow( ( p.y - 1.02 ) / 0.07, 2.0 ) ) * 0.6;
        return 0.0032 * mix( top, stack + knee + crotch + ( n2 - 0.5 ) * 1.4, legs );
      }` : ''}`)
    .replace('#include <roughnessmap_fragment>', `float roughnessFactor = vPart.x;
      float pCloth = 1.0 - step( 0.5, vPart.y ), pSkin = step( 0.5, vPart.y ) * ( 1.0 - step( 1.5, vPart.y ) );
      float pHair = step( 1.5, vPart.y ) * ( 1.0 - step( 2.5, vPart.y ) );
      roughnessFactor = mix( roughnessFactor, ${SKIN_ROUGH.toFixed(2)}, pSkin );
      ${FINE ? `
      float pNear = 1.0 - smoothstep( 0.006, 0.02, length( fwidth( vRest ) ) );          // (m to a pixel)
      float pDye = pNoise( vRest * vec3( 9.0, 5.0, 9.0 ) ) * 0.6 + pNoise( vRest * vec3( 37.0, 23.0, 37.0 ) ) * 0.4;
      diffuseColor.rgb *= mix( 1.0, 0.88 + 0.22 * pDye, pCloth );
      float pAz = atan( vRest.x, vRest.z + 0.04 );
      float pStrand = pNoise( vec3( pAz * 46.0, vRest.y * 7.0, 3.0 ) ) * 0.65 + pNoise( vec3( pAz * 150.0, vRest.y * 11.0, 9.0 ) ) * 0.35;
      diffuseColor.rgb *= mix( 1.0, 0.82 + 0.40 * pStrand, pHair * pNear );
      roughnessFactor = mix( roughnessFactor, 0.34 + 0.22 * pStrand, pHair );` : ''}`)
    // the drawn face, laid on after the vertex colour (the white of the eye is white on any skin), read most of a
    // mip level sharper than the screen asks for: thin strokes hold a little further away
    .replace('#include <map_fragment>', '')
    .replace('#include <color_fragment>', `#include <color_fragment>
      vec4 drawn = texture2D( map, vMapUv, ${FACE_BIAS} );
      float pBlink = floor( vGlass / 4.0 + 0.01 ), pGlass = vGlass - 4.0 * pBlink;
      {
        // a blink: now and then (every 3 to 6 s, by the person's own count) the eyes shut for an eighth of a second
        vec2 c = fract( vMapUv * ${GRID_F} );
        vec2 e = vec2( ( abs( c.x - 0.5 ) - ${EYE_U.toFixed(4)} ) / ${EYE_A.toFixed(4)}, ( c.y - ${(EYE_V - 0.02).toFixed(4)} ) / ${EYE_B.toFixed(4)} );
        float shut = step( fract( ( uBlinkT + pBlink * 1.37 ) / ( 3.0 + 0.19 * pBlink ) ) * ( 3.0 + 0.19 * pBlink ), 0.13 );
        shut *= step( 0.5, vPart.y ) * step( vPart.y, 1.5 ) * ( 1.0 - step( 0.75, vMapUv.x ) * step( 0.75, vMapUv.y ) );      // (skin, not the blank cell)
        float lid = shut * ( 1.0 - smoothstep( 0.8, 1.0, length( e ) ) );
        float lash = ( 1.0 - smoothstep( 0.09, 0.17, abs( e.y - 0.38 + 0.30 * e.x * e.x ) ) ) * ( 1.0 - smoothstep( 0.015, 0.04, length( fwidth( c ) ) ) );     // (the line from near only)
        drawn = mix( drawn, vec4( mix( vec3( 1.0 ), vec3( 0.07, 0.05, 0.05 ), lash * step( abs( e.x ), 0.92 ) ), 1.0 ), lid );
      }
      diffuseColor.rgb = mix( vec3( ${EYE_WHITE} ), diffuseColor.rgb * drawn.rgb, drawn.a );
      // the drawn glasses: in as the rims' geometry goes (how many pixels a rim is across, from the atlas' scale here)
      vec2 rimD = vec2( length( dFdx( vMapUv ) ), length( dFdy( vMapUv ) ) );
      float rimPx = ${RIM_UV} / max( max( rimD.x, rimD.y ), 1e-7 );
      float rim = texture2D( uRims, vMapUv ).r * step( 0.5, pGlass ) * smoothstep( ${(2 * RIM_PX).toFixed(2)}, ${RIM_PX.toFixed(2)}, rimPx );
      diffuseColor.rgb = mix( diffuseColor.rgb, pGlass > 1.5 ? ${glsl(RIMS[1])} : ${glsl(RIMS[0])}, rim );`)
    .replace('#include <aomap_fragment>', `#include <aomap_fragment>
      {
        // the shut-in places: skin shades warm (the light that gets there has been through skin), the rest grey
        vec3 pShade = mix( vec3( 1.0 ), mix( vec3( 0.0 ), vec3( 0.62, 0.40, 0.33 ), pSkin ), vPart.z * mix( 1.0, 0.75, pSkin ) );
        reflectedLight.indirectDiffuse *= pShade;
        reflectedLight.indirectSpecular *= 1.0 - vPart.z;
        reflectedLight.directDiffuse *= mix( vec3( 1.0 ), pShade, 0.4 );
        reflectedLight.directSpecular *= 1.0 - 0.6 * vPart.z;
        // the fuzz of cloth, the down of skin: a soft light where the surface turns away
        float pEdge = pow( 1.0 - saturate( dot( normal, normalize( vViewPosition ) ) ), 3.0 );
        vec3 pLit = ( reflectedLight.directDiffuse + reflectedLight.indirectDiffuse ) / max( material.diffuseColor, vec3( 0.05 ) );
        reflectedLight.indirectDiffuse += pLit * pEdge * ( pCloth * 0.085 * mix( vec3( 1.0 ), material.diffuseColor, 0.6 ) + pSkin * 0.035 * vec3( 1.0, 0.78, 0.68 ) );
      }`);
  if (FINE) sh.fragmentShader = sh.fragmentShader.replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
      {
        float pH = pFolds( vRest ) * pCloth * pNear + ( pStrand - 0.5 ) * 0.0018 * pHair * pNear;
        vec3 pDx = dFdx( - vViewPosition ), pDy = dFdy( - vViewPosition );
        vec3 pR1 = cross( pDy, normal ), pR2 = cross( normal, pDx );
        float pDet = dot( pDx, pR1 );
        normal = normalize( abs( pDet ) * normal - sign( pDet ) * ( dFdx( pH ) * pR1 + dFdy( pH ) * pR2 ) );
      }`);
};
pcss(PERSON_MAT);

// (onBeforeRender of a person who wears glasses) the rims' geometry only while it is RIM_PX pixels or more across: the
// glasses' triangles are the index's last (dressed), the draw stops short of them otherwise
const _vp = new THREE.Vector4(), _head = new THREE.Vector3(), _eye = new THREE.Vector3();
function rimLod(renderer, scene, camera, geometry) {
  if (!camera.isPerspectiveCamera) return;           // (the shadow pass: as the view left it)
  renderer.getCurrentViewport(_vp);
  _head.setFromMatrixPosition(this.matrixWorld).y += 1.5;
  const d = Math.max(0.1, _head.distanceTo(_eye.setFromMatrixPosition(camera.matrixWorld)));
  geometry.drawRange.count = RIM_W * camera.projectionMatrix.elements[5] * _vp.w / (2 * d) >= RIM_PX ? Infinity : geometry.userData.rims;
}

// The bounds the frustum (and shadow frustum) test uses: the rest pose sphere, grown to hold swinging arms,
// strides, gestures and the seated pose.
const POSE_SLACK = 1.35;

function mergeParts(root) {
  const parts = [];
  root.traverse((o) => { if (o.isSkinnedMesh) parts.push(o); });
  if (!parts.length) return;
  const first = parts[0];
  const ranges = [];                 // the vertices of each flat-coloured part, by its material's name (crowdLook)
  let at = 0;
  const geos = parts.map((m) => {
    const src = m.geometry, n = src.attributes.position.count;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', src.attributes.position);
    g.setAttribute('normal', src.attributes.normal);
    // (only the skin has texture coordinates, as normalized shorts: the other parts lie on the atlas' blank cell)
    const uv = new Float32Array(n * 2).fill(BLANK_UV), su = src.attributes.uv;
    if (su) for (let i = 0; i < n; i++) { uv[i * 2] = su.getX(i); uv[i * 2 + 1] = su.getY(i); }
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    // the parts may store joints / weights in different array types: unify them so they merge
    const si = src.attributes.skinIndex, sw = src.attributes.skinWeight;
    const idx = new Uint16Array(n * 4), wt = new Float32Array(n * 4);
    for (let i = 0; i < n; i++) {
      for (let k = 0; k < 4; k++) { idx[i * 4 + k] = si.getComponent(i, k); wt[i * 4 + k] = sw.getComponent(i, k); }
    }
    g.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(idx, 4));
    g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(wt, 4));
    ranges.push({ name: m.material.name, start: at, count: n });
    at += n;
    const c = m.material.color, col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    // roughness, kind, occlusion (the model's _OCC, a byte; an older file has none)
    const part = new Float32Array(n * 3), so = src.attributes._occ, kind = kindOfPart(m.material.name);
    for (let i = 0; i < n; i++) { part[i * 3] = /Hair/.test(m.material.name) ? 0.55 : 0.85; part[i * 3 + 1] = kind; part[i * 3 + 2] = so ? so.getX(i) / 255 : 0; }
    g.setAttribute('part', new THREE.Float32BufferAttribute(part, 3));
    g.setIndex(src.index ? Array.from(src.index.array) : Array.from({ length: n }, (_, i) => i));
    return g;
  });
  const merged = mergeGeometries(geos, false);
  if (!merged) { console.warn('could not merge person parts', root.name); return null; }
  const mesh = new THREE.SkinnedMesh(merged, PERSON_MAT);
  mesh.name = first.name;
  mesh.position.copy(first.position); mesh.quaternion.copy(first.quaternion); mesh.scale.copy(first.scale);
  first.parent.add(mesh);
  mesh.bind(first.skeleton, first.bindMatrix);
  merged.computeBoundingSphere();
  mesh.boundingSphere = merged.boundingSphere.clone();
  mesh.boundingSphere.radius *= POSE_SLACK;
  for (const p of parts) { p.parent.remove(p); p.geometry.dispose(); }
  return ranges;
}

// ---------------------------------------------------------------- one crowd, many looks
// The crowd is drawn from 14 models, so the same burgundy shirt came by every half minute. Each person of the crowd
// takes the model's cut in colours of their own (the 1997 wardrobe of blender/characters.py: stone-washed and dark
// denim, khaki and grey slacks, white, navy, forest green, burgundy, mustard tops), a skin tone, now and then dark
// brown hair, and a height and build of their own: heights spread about the model's (men 1.73 m, women 1.61 m) by
// 3.2 %, about 5.5 cm (6 % at most), builds by a couple of per cent. Every model has a pair of thin-rimmed glasses
// (blender/characters.py): about three in ten of the crowd wear theirs, whatever they wear else (four of the eleven
// students in the anthology's photographs of 1997-2002 do: reference/고증 4.9), most professors, in metal rims or,
// one in five, dark ones. Skin: the four tones evenly, and about one in fourteen each fair or tanned. The heroes, the
// drivers and the birthday pair keep the models as they are.
const JEANS = ['#46638f', '#2b3c5c', '#7f9cc0', '#8fa8c8'];
const SKIN = ['#f0c9a4', '#e6b991', '#d9a77d', '#c99168'];
const SKIN_FAIR = '#f7ddc8', SKIN_TAN = '#b9825a';      // now and then somebody fair, or tanned (가무잡잡)
// material name -> the colours to draw from (the first is the model's own)
const LOOKS = {
  'man-tee': { LightBrown: ['#f1efe8', '#f1efe8', '#d8dde3', '#e9dfa8', '#a9c3de', '#2f3a55', '#9a9a96'], LightBlue: [...JEANS, '#a8946a'] },
  'man-check': { LightBrown: ['#1f2f55', '#2f5a45', '#6e2430', '#1f2f55', '#2a2a2e', '#e4e0d4'], LightBlue: [...JEANS, '#3a3f47', '#a8946a'] },
  'man-hoodie': { Purple: ['#23345e', '#8d8f92', '#2f5a45', '#6e2430', '#c9c3b2', '#1f1f24'], LightBlue: ['#a8946a', ...JEANS, '#3a3f47'] },
  'man-cheer': { LightBlue: JEANS },                       // (the cheer jacket stays Yonsei blue)
  'man-grey': { Purple: ['#e8e0b0', '#8d8f92', '#2f6a4a', '#27406e', '#b3262e', '#1f1f24'], LightBlue: JEANS },
  'man-blazer': { Suit: ['#27304a', '#5e4634', '#4a4d52', '#8a7a5c', '#3d4a3a'], LightBlue: ['#b9a67e', ...JEANS, '#2c3550'] },
  'man-professor': { Suit: ['#55595f', '#2c3448', '#4a4038', '#3a3f47', '#6b6a5c'], Tie: ['#2f4a7a', '#6e2430', '#3d5a45', '#4a4a50'] },
  'man-staff': {},
  'woman-tee': { White: ['#f4f1e8', '#f4f1e8', '#f3d9de', '#cfe0ee', '#e9dfa8', '#2f3a55', '#b9c9a8'], Orange: [...JEANS, '#cdb994', '#2a2a2e'] },
  'woman-pink': { White: ['#e7a7b6', '#f0e6d2', '#a9c3de', '#c7b3dc', '#b5d6c3', '#e8c66a', '#c95a5a'], Orange: ['#cdb994', ...JEANS, '#2a2a2e', '#f0eee8'] },
  'woman-dress': { LimeGreen: ['#f1ede1', '#f3d9de', '#cfe0ee', '#ecdf9e', '#2a2a2e', '#b9c9a8'] },
  'woman-dress-blue': { Pink: ['#a9c6e6', '#f4f1e8', '#f3d9de', '#e9dfa8', '#2a2a2e', '#c95a5a'] },
  'woman-cardigan': { Black: ['#ecdf9e', '#f3d9de', '#6f7f5a', '#8d8f92', '#2f3a55', '#e6dcc6', '#c98a8a'], Orange: ['#46638f', ...JEANS, '#2b2f3a', '#cdb994'] },
  'woman-staff': { Black: ['#2f3644', '#3a3f47', '#4a4038', '#5b6470'] },
};
// the parts painted on an outfit (blender/characters.py `paint`): the stripes and the collar of a tee, a jumper's
// collar, a skirt, the jeans under a cropped tee. Drawn from a stream of their own, after everything else
const LOOKS_MORE = {
  'man-check': { Stripe: ['#1f8580', '#e9e4d6', '#d8b23a', '#7f9cc0', '#b3262e'], Stripe2: ['#d8742c', '#e9e4d6', '#8d8f92', '#c95a5a'],
    Collar: ['#ece8dc', '#ece8dc', '#1f2f55'] },
  'man-grey': { Collar: ['#3b3a3c', '#1f2a46', '#e9e6dc', '#5a1f28'] },
  'woman-dress': { Skirt: ['#1f1f24', '#1f1f24', '#27304a', '#6e2430', '#8a7a5c', '#4a4d52'] },
  'woman-dress-blue': { Orange: [JEANS[1], ...JEANS, '#f0eee8', '#e3cf7a', '#2a2a2e'] },
};
// about one striped tee in three is plain: its stripes and collar in the tee's own colour
const PLAIN = { 'man-check': ['LightBrown', ['Stripe', 'Stripe2', 'Collar'], 0.35] };

// the look of the n-th person of the crowd: { colors: {material: hex}, scale: [width, height], glasses }. Its own
// random stream (as bags.js crowdBag), so the crowd's paths and faces stay where they were. The drawn lines of the
// face need no colours here: they darken the skin they lie on (the brows stay the model's: dark, or a professor's grey).
export function crowdLook(id, n) {
  const r = mulberry(n * 2654435761 + 977);
  const colors = {};
  const set = LOOKS[id] || {};
  for (const k in set) colors[k] = set[k][Math.floor(r() * set[k].length)];
  const s = r();
  colors.Skin = s < 0.07 ? SKIN_FAIR : s >= 0.93 ? SKIN_TAN : SKIN[Math.floor((s - 0.07) / 0.86 * SKIN.length)];
  const h = r();
  if (id !== 'man-professor' && id !== 'man-grey' && id !== 'woman-dress-blue') {       // (grey hair, and the dyed brown of 1997, stay)
    colors.Hair = h < 0.74 ? '#141110' : h < 0.93 ? '#2b1f18' : '#4a3020';
  }
  const tall = 1 + 0.032 * ((r() + r() + r() - 1.5) / 0.5);            // about normal, sd 3.2 %
  const build = 1 + 0.02 * (r() + r() - 1);
  const clamp = (v) => Math.min(1.065, Math.max(0.94, v));
  const glasses = r() < (id === 'man-professor' ? 0.7 : 0.3);
  const blink = (n * 7 + 3) % BLINKS;                 // (no draw: the streams stay as they were)
  colors.Glasses = RIMS[r() < 0.8 ? 0 : 1];
  const r2 = mulberry(n * 40503 + 331), more = LOOKS_MORE[id] || {};
  for (const k in more) colors[k] = more[k][Math.floor(r2() * more[k].length)];
  const plain = PLAIN[id];
  if (plain && r2() < plain[2]) for (const k of plain[1]) colors[k] = colors[plain[0]];
  return { colors, scale: [clamp(tall * build), clamp(tall)], glasses, blink };
}

// the triangles of `geo` with the glasses' last: { index, bare: how many of its entries come before the glasses' },
// kept with the index it was made from. Everybody draws the one index, those without glasses short of the end.
const glassesOrder = new WeakMap();
function glassesLast(geo, ranges) {
  const part = ranges?.find((p) => p.name === 'Glasses');
  if (!part || !geo.index) return null;
  let o = glassesOrder.get(geo.index);
  if (!o) {
    const a = geo.index.array, rest = [], glass = [];
    for (let i = 0; i < a.length; i += 3) (a[i] >= part.start && a[i] < part.start + part.count ? glass : rest).push(a[i], a[i + 1], a[i + 2]);
    o = { index: new THREE.BufferAttribute(new a.constructor([...rest, ...glass]), 1), bare: rest.length };
    glassesOrder.set(geo.index, o);
  }
  return o;
}
// the attribute `glass` of a geometry of n vertices, all v: one shared buffer for each
const glassBuffers = new Map();
function glassAttribute(n, v) {
  const k = n * 64 + v;
  if (!glassBuffers.has(k)) glassBuffers.set(k, new THREE.Uint8BufferAttribute(new Uint8Array(n).fill(v), 1));
  return glassBuffers.get(k);
}

// `geo` (a person's merged geometry, or that with a bag: the person's vertices come first) as one person wears it:
// the parts named in `colors` in those colours, with the glasses or without. A geometry sharing every buffer but
// the colours; people who wear the model as it is share one.
const worn = new WeakMap();        // geometry -> [without glasses, with]
function dressed(geo, ranges, colors, glasses, blink = 0) {
  if (!ranges || !geo.attributes.color) return geo;
  if (!colors) {
    const made = worn.get(geo) || worn.set(geo, []).get(geo);
    return made[+glasses] || (made[+glasses] = dressed(geo, ranges, {}, glasses));        // (blink 0)
  }
  const g = new THREE.BufferGeometry();
  for (const k in geo.attributes) if (k !== 'color') g.setAttribute(k, geo.attributes[k]);
  const order = glassesLast(geo, ranges);
  g.setIndex(order ? order.index : geo.index);
  if (order && !glasses) g.setDrawRange(0, order.bare);
  if (order && glasses) g.userData.rims = order.bare;           // (rimLod)
  g.setAttribute('glass', glassAttribute(geo.attributes.position.count, (!order || !glasses ? 0 : colors.Glasses === RIMS[1] ? 2 : 1) + 4 * blink));
  if (!Object.keys(colors).length) {
    g.setAttribute('color', geo.attributes.color);
    g.boundingSphere = geo.boundingSphere;
    g.boundingBox = geo.boundingBox;
    return g;
  }
  const col = geo.attributes.color.clone(), c = new THREE.Color();
  for (const p of ranges) {
    if (!colors[p.name]) continue;
    c.set(colors[p.name]);
    for (let i = p.start; i < p.start + p.count; i++) col.setXYZ(i, c.r, c.g, c.b);
  }
  g.setAttribute('color', col);
  g.boundingSphere = geo.boundingSphere;
  g.boundingBox = geo.boundingBox;
  return g;
}

const PEOPLE_DIR = 'assets/models/people/', RIGS = ['rig-umc', 'rig-women'];
// the files Cast.load(ids) reads (for world.js prefetch)
export const castFiles = (ids) => [...RIGS, ...ids].map((n) => PEOPLE_DIR + n + '.glb');

export class Cast {
  constructor() { this.models = {}; this.rigs = {}; }

  async load(ids, onEach) {
    const base = PEOPLE_DIR;
    const drawn = loadFaces();
    await Promise.all(RIGS.map(async (r) => {
      const g = await loadGLB(base + r + '.glb');
      const u = g.scene.getObjectByName(r)?.userData || {};
      this.rigs[r] = { clips: g.animations, walkSpeed: +u.walk_speed || 1.2, runSpeed: +u.run_speed || 2.8 };
      onEach?.();
    }));
    await Promise.all(ids.map(async (id) => {
      const g = await loadGLB(base + id + '.glb');
      let rig = 'rig-umc', glasses = false;
      g.scene.traverse((o) => {
        if (o.userData && typeof o.userData.rig === 'string') { rig = o.userData.rig; glasses = !!o.userData.glasses; }
      });
      const ranges = mergeParts(g.scene);
      this.models[id] = { scene: g.scene, rig, ranges, glasses };
      onEach?.();
    }));
    await drawn;
  }

  // bag: what the person carries (bags.js: merged into their one mesh), null for nothing; a hero has their own
  // look: colours, size and glasses of their own (crowdLook), null for the model as it is
  make(id, bag = HERO_BAGS[id] ?? null, look = null) {
    const src = this.models[id];
    const holder = new THREE.Group();
    const root = skeletonClone(src.scene);
    if (bag) root.traverse((o) => { if (o.isSkinnedMesh) o.geometry = baggedGeometry(o, id, bag); });
    root.traverse((o) => {
      if (!o.isSkinnedMesh) return;
      o.geometry = dressed(o.geometry, src.ranges, look?.colors, look ? look.glasses : src.glasses, look?.blink);
      if (o.geometry.userData.rims) o.onBeforeRender = rimLod;
    });
    const [wide, tall] = look?.scale || [1, 1];
    holder.scale.set(wide, tall, wide);
    // frustum culled by the posed bounds above (off-screen people cost nothing, in the shadow pass too)
    root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    holder.add(root);
    const rig = this.rigs[src.rig];
    const mixer = new THREE.AnimationMixer(root);
    const actions = {};
    for (const c of rig.clips) actions[c.name] = mixer.clipAction(c);
    // (longer legs: longer strides at the same cadence)
    const a = { id, bag, holder, root, mixer, actions, current: null, walkSpeed: rig.walkSpeed * tall, runSpeed: rig.runSpeed * tall, after: null, tall };
    mixer.addEventListener('finished', () => { const next = a.after || 'idle'; a.after = null; play(a, next, { fade: 0.3 }); });
    play(a, 'idle', { fade: 0 });
    return a;
  }
}

export function play(a, name, opts = {}) {
  const act = a.actions[name] || a.actions.idle;
  if (!act) return null;
  if (a.current === act && !opts.once) return act;
  act.reset();
  act.setLoop(opts.once ? THREE.LoopOnce : THREE.LoopRepeat, Infinity);
  act.clampWhenFinished = !!opts.once;
  act.timeScale = opts.speed || 1;
  act.enabled = true;
  act.setEffectiveWeight(1);
  if (a.current && a.current !== act) act.crossFadeFrom(a.current, opts.fade ?? 0.25, false);
  act.play();
  a.current = act;
  a.after = opts.once ? opts.then || null : null;
  return act;
}

export const gesturing = (a) => a.current && a.current.loop === THREE.LoopOnce && a.current.isRunning();

// the clip follows the ground speed: by the rig's measured foot speed, so feet do not slide
export function locomotion(a, speed, runThreshold = 3.6) {
  if (gesturing(a)) return;
  if (!speed) { play(a, 'idle'); return; }
  if (Math.abs(speed) > runThreshold && a.actions.sprint) {
    play(a, 'sprint');
    a.current.timeScale = Math.abs(speed) / a.runSpeed;
  } else {
    play(a, 'walk');
    a.current.timeScale = Math.sign(speed) * Math.abs(speed) / a.walkSpeed;
  }
}

// Render a small portrait of each hero for the title screen (idle pose, three-quarter view).
export function portraits(cast, ids, w = 150, h = 190) {
  const r = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  r.setSize(w, h);
  r.outputColorSpace = THREE.SRGBColorSpace;
  r.toneMapping = THREE.AgXToneMapping;
  const out = {};
  for (const id of ids) {
    const sc = new THREE.Scene();
    sc.add(new THREE.HemisphereLight(0xffffff, 0x8a7a66, 2.2));
    const d = new THREE.DirectionalLight(0xffffff, 2.4);
    d.position.set(2, 4, 3);
    sc.add(d);
    const a = cast.make(id);
    a.mixer.update(0.5);
    a.holder.rotation.y = 0.45;
    sc.add(a.holder);
    const top = id.startsWith('woman') ? 1.61 : 1.73;
    const cam = new THREE.PerspectiveCamera(24, w / h, 0.1, 50);
    cam.position.set(0, top * 0.62, 5.2);
    cam.lookAt(0, top * 0.5, 0);
    r.render(sc, cam);
    out[id] = r.domElement.toDataURL('image/png');
  }
  r.dispose();
  r.forceContextLoss();          // free the extra WebGL context now, not when it is garbage collected
  return out;
}
