// People: Quaternius CC0 modular characters (blender/characters.py) driven by the shared rig clips,
// in the manner of the sim-office engine (actors.js): a holder group, an AnimationMixer per person,
// cross-faded clips, and walk/run cycles whose playback speed follows the ground speed (no foot sliding).
// The clips are motion capture fitted to the rigs (blender/mocap.py): three walks of different paces (each with its
// own speed over the ground, the rig's `speeds`), a run, standing (idle, and shifting the weight, looking about, arms
// folded, talking, on the phone), sitting and sitting talking; the wave, the reach and the shake of the head are
// the pack's.  locomotion() takes the walk nearest the speed; whoever stands plays `a.stand` (life.js sets it).
import * as THREE from 'three';
import { clone as skeletonClone } from 'three/addons/utils/SkeletonUtils.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { loadGLB } from './world.js';
import { pcss, windTime } from './materials.js';
import { HERO_BAGS, baggedGeometry } from './bags.js';
import { MOBILE, mulberry, versioned } from './util.js';

export const PEOPLE = {
  'man-tee': '게스 긴팔 티 · 연청바지',
  'man-check': '체크 남방 · 청바지',
  'man-cheer': '연세 점퍼 · 블랙진',
  'man-hoodie': '남색 후드티',
  'man-grey': '줄무늬 티 · 진청바지',
  'man-blazer': '콤비 재킷',
  'man-professor': '교수님',
  'man-staff': '교직원',
  'woman-tee': '연세 티 · 연청바지',
  'woman-pink': '분홍 니트',
  'woman-dress': '빨간 니트 · 청치마',
  'woman-dress-blue': '크림색 맨투맨 · 블랙진',
  'woman-cardigan': '노란 카디건',
  'woman-staff': '교직원',
  'woman-stripe': '줄무늬 티 · 청바지',
  'man-shirt': '초록 남방 · 면바지',
  'woman-denim': '청남방 · 면바지',
};
export const STUDENTS = ['man-tee', 'man-check', 'man-cheer', 'man-hoodie', 'man-grey', 'man-blazer',
  'woman-tee', 'woman-pink', 'woman-dress', 'woman-dress-blue', 'woman-cardigan'];
export const HEROES = ['man-tee', 'woman-dress', 'man-cheer', 'woman-tee', 'man-check', 'woman-cardigan', 'man-blazer', 'woman-pink',
  'woman-dress-blue', 'man-hoodie', 'woman-stripe', 'man-shirt', 'woman-denim'];
// the thirteen you can walk as: a name of the class of 1997 (the first two from the film 건축학개론, 2012, whose first half
// is a campus of 1996), the college they are of, and the hall their walk starts at (a name of campus.json's markers
// or landmarks: places.js startPlaces); height: taller or shorter than the model (men 1.73 m, women 1.61 m)
// short: the college as students called it (the title card's thirteen buttons have room for no more)
export const HERO = {
  'man-tee': { name: '승민', college: '공과대학', short: '공대', place: '제1공학관' },
  'woman-dress': { name: '서연', college: '음악대학', short: '음대', place: '음악대학' },
  'man-cheer': { name: '성구', college: '상경대학', short: '상경대', place: '상대신관', height: 1.79 },
  'woman-tee': { name: '지은', college: '문과대학', short: '문과대', place: '인문관' },
  'man-check': { name: '성훈', college: '이과대학', short: '이과대', place: '과학관' },
  'woman-cardigan': { name: '은정', college: '사회과학대학', short: '사과대', place: '연희관' },
  'man-blazer': { name: '준호', college: '법과대학', short: '법대', place: '광복관' },
  'woman-pink': { name: '지영', college: '교육과학대학', short: '교과대', place: '용재관' },
  'woman-dress-blue': { name: '수진', college: '생활과학대학', short: '생과대', place: '가정관' },
  'man-hoodie': { name: '동현', college: '의과대학', short: '의대', place: '의과대학' },
  // (the three models from here on are nobody of the crowd: STUDENTS, the crowd's pool, stays as it was)
  'woman-stripe': { name: '혜진', college: '간호대학', short: '간호대', place: '간호대학' },
  'man-shirt': { name: '정우', college: '신과대학', short: '신과대', place: '아펜젤러관' },
  'woman-denim': { name: '현정', college: '치과대학', short: '치대', place: '치과대학' },
};

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
//  - trousers are drawn by a leg's own coordinates (the attribute `leg`, blender/characters.py cut_trousers: which
//    way a point faces round the leg, and its height from the hem to the waistband): the seams down the outside and
//    the inside, the hem, the waistband, the back pockets and the front pockets' openings; and denim its wash, worn
//    pale on the front of the thigh, the knee and the seat and left dark inside the leg, behind the knee and at the
//    hem, the more the paler the jeans (WASH: dark, mid, stone-washed; khaki and slacks have the seams alone)
//  - a checked shirt (체크 남방) is the cloth of the material `Check`, drawn by where a point lies on the model at
//    rest: round the trunk and up it, or round a sleeve and along it (the sleeves begin at the shoulder joints: the
//    attribute `leg` of such a vertex is CHECK_W and where those are, mergeParts); over the shoulders, where the
//    cloth lies flat, across and back. Broad darker bands both ways, darkest where two cross, and a thin line
//    between them: a deep red on pale cloth, cream on dark
// Phones go without the folds and the strands (no noise in the fragment shader there).
// The eyes, brows and mouths are a few lines drawn on one small atlas all the people share (blender/faces.py): the
// front of a face lies on its own cell, everything else on the blank cell, and the picture multiplies the vertex
// colour. So the lines keep to whatever skin a person of the crowd has, and fade into it with distance (mip maps).
// The picture's alpha is how much of that shows: the rest is the white of the eye.
// What is printed on a chest (YONSEI on a jumper and a tee, the film 건축학개론's GEUSS triangle) is drawn the same
// way, from the atlas' print cell: ink is the picture's colour times the cloth's, white lettering its alpha.
// Glasses: everybody's model has a pair, a few millimetres thin. Thinner than a pixel, they glitter on and off from
// frame to frame where nothing smooths the edges (phones have no anti-aliasing, nor TAA): so a person who wears glasses
// has the rims' geometry drawn only while the rims are RIM_PX pixels or more across (rimLod: the index puts the glasses'
// triangles last, and the draw stops short of them), and from somewhat nearer than that on the same glasses drawn on
// the face from a second atlas (faces_rims.png), which the mip maps fade evenly with distance. Who wears them, and
// which rims, rides along as the attribute `glass` (0 none, 1 thin metal, 2 dark horn; plus 4 x the person's blink
// and 64 x the wash of their jeans).
// Blinking: every few seconds (each of the BLINKS kinds of the crowd in its own time) the eyes of a face are drawn
// shut for an eighth of a second: skin over the eye's place on the cell and the lashes' line, sagging in the middle.
// By the clock of the wind; the line only from near.
const KIND = { cloth: 0, skin: 1, hair: 2, hard: 3 };
const kindOfPart = (name) => (name === 'Skin' ? KIND.skin : /^(Hair|Bridge)/.test(name) ? KIND.hair : /Glasses|feet/.test(name) ? KIND.hard : KIND.cloth);
const SKIN_ROUGH = 0.5;
const PERSON_MAT = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, metalness: 0, envMapIntensity: 0.8 });
PERSON_MAT.name = 'person';
const FACE_BIAS = '-0.75', EYE_WHITE = '0.84, 0.83, 0.80';     // (faces.py WHITE)
const BLANK_UV = 0.9;              // the middle of the atlas' blank cell (u and v): faces.py BLANK (the last of 5 x 5)
const RIM_W = 0.0022;              // the rims' thickness in the game, m (faces.py RIM_T, scaled as the people)
const RIM_UV = 0.0032;             // the same on the atlas: RIM_T / (2 HALF) / GRID
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
const GRID_F = '5.0';                  // (faces.py GRID)
// a checked shirt (the material `Check`): the checks' size up the trunk (m), how many go round the trunk and round a
// sleeve, how deep the trunk's oval is for its width (the reciprocal), a band's and a thin line's share of a check
const CHECK = { pitch: 0.054, round: 16, sleeve: 6, deep: '0.66', band: 0.40, line: 0.07 };
const CHECK_W = 77;                    // the attribute `leg`'s fourth byte on such cloth (trousers: 255, anything else: 0)
const LEG_TOP = '1.25';                // (characters.py LEG_TOP)
const FINE = !MOBILE;               // the folds of cloth and the strands of hair
PERSON_MAT.onBeforeCompile = (sh) => {
  sh.uniforms.uRims = RIMS_TEX;
  sh.uniforms.uBlinkT = windTime;
  sh.vertexShader = sh.vertexShader
    .replace('#include <common>', '#include <common>\nattribute vec3 part;\nattribute float glass;\nattribute vec4 leg;\nvarying vec3 vPart, vRest, vRestN;\nvarying float vGlass;\nvarying vec4 vLeg;')
    .replace('#include <begin_vertex>', '#include <begin_vertex>\nvPart = part;\nvGlass = glass;\nvLeg = leg;\nvRest = position;\nvRestN = normal;');
  sh.fragmentShader = sh.fragmentShader
    .replace('#include <common>', `#include <common>
      varying vec3 vPart, vRest, vRestN;
      varying float vGlass;
      varying vec4 vLeg;
      uniform sampler2D uRims;
      // a line of half width w about x = 0, as much of the pixel as it covers (d: x over a pixel)
      float pLine( float x, float w, float d ) { return clamp( ( w - abs( x ) ) / max( d, 1e-5 ) + 0.5, 0.0, 1.0 ) * min( 1.0, 2.0 * w / max( d, 1e-5 ) ); }
      uniform float uBlinkT;
      // checked cloth of the colour base at q (in checks; d: checks to a pixel): broad darker bands both ways, darkest
      // where two cross, a thin line between them (deep red on pale cloth, cream on dark); far off, their mean
      vec3 pPlaid( vec2 q, float d, vec3 base ) {
        vec2 c = abs( fract( q ) - 0.5 );
        vec2 band = clamp( ( ${(CHECK.band / 2).toFixed(3)} - c ) / max( d, 1e-4 ) + 0.5, 0.0, 1.0 );
        vec2 thin = clamp( ( c - ${(0.5 - CHECK.line / 2).toFixed(3)} ) / max( d, 1e-4 ) + 0.5, 0.0, 1.0 ) * min( 1.0, ${CHECK.line.toFixed(3)} / max( d, 1e-4 ) );
        float far = smoothstep( 0.35, 0.9, d );
        band = mix( band, vec2( ${CHECK.band.toFixed(3)} ), far );
        thin = mix( thin, vec2( ${CHECK.line.toFixed(3)} ), far );
        float pale = step( 0.22, dot( base, vec3( 0.3, 0.59, 0.11 ) ) );
        vec3 ink = mix( mix( base, vec3( 0.80, 0.77, 0.66 ), 0.85 ), vec3( 0.26, 0.035, 0.04 ), pale );
        vec3 col = mix( base, base * mix( vec3( 0.50, 0.52, 0.60 ), vec3( 0.46, 0.36, 0.30 ), pale ), 0.5 * ( band.x + band.y ) );
        return mix( col, ink, 0.8 * max( thin.x, thin.y ) );
      }
      ${FINE ? `
      float pHash( vec3 p ) { p = fract( p * 0.3183099 + 0.1 ); p *= 17.0; return fract( p.x * p.y * p.z * ( p.x + p.y + p.z ) ); }
      float pNoise( vec3 x ) { vec3 i = floor( x ), f = fract( x ); f = f * f * ( 3.0 - 2.0 * f );
        return mix( mix( mix( pHash( i ), pHash( i + vec3( 1, 0, 0 ) ), f.x ), mix( pHash( i + vec3( 0, 1, 0 ) ), pHash( i + vec3( 1, 1, 0 ) ), f.x ), f.y ),
                    mix( mix( pHash( i + vec3( 0, 0, 1 ) ), pHash( i + vec3( 1, 0, 1 ) ), f.x ), mix( pHash( i + vec3( 0, 1, 1 ) ), pHash( i + vec3( 1, 1, 1 ) ), f.x ), f.y ), f.z ); }
      // the height of the folds of cloth (m) over the rest pose (y up, m): trousers stack up at the ankle and crease
      // behind the knee and at the crotch, tops drape and gather at the hem
      float pFolds( vec3 p, float trousers ) {
        float n1 = pNoise( p * vec3( 13.0, 4.0, 13.0 ) ), n2 = pNoise( p * vec3( 5.0, 9.0, 5.0 ) + 7.0 );
        float legs = max( trousers, step( p.y, 0.93 ) );
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
      diffuseColor.rgb *= mix( 1.0, mix( 0.88 + 0.22 * pDye, 0.82 + 0.34 * pDye, pJean * pWash / 3.0 ), pCloth );
      float pAz = atan( vRest.x, vRest.z + 0.04 );
      float pStrand = pNoise( vec3( pAz * 46.0, vRest.y * 7.0, 3.0 ) ) * 0.65 + pNoise( vec3( pAz * 150.0, vRest.y * 11.0, 9.0 ) ) * 0.35;
      diffuseColor.rgb *= mix( 1.0, 0.82 + 0.40 * pStrand, pHair * pNear );
      roughnessFactor = mix( roughnessFactor, 0.34 + 0.22 * pStrand, pHair );` : ''}`)
    // the drawn face, laid on after the vertex colour (the white of the eye is white on any skin), read most of a
    // mip level sharper than the screen asks for: thin strokes hold a little further away
    .replace('#include <map_fragment>', '')
    .replace('#include <color_fragment>', `#include <color_fragment>
      vec4 drawn = texture2D( map, vMapUv, ${FACE_BIAS} );
      float pWash = floor( vGlass / 64.0 + 0.01 ), pBlink = floor( ( vGlass - 64.0 * pWash ) / 4.0 + 0.01 );
      float pGlass = vGlass - 64.0 * pWash - 4.0 * pBlink;
      {
        // a blink: now and then (every 3 to 6 s, by the person's own count) the eyes shut for an eighth of a second
        vec2 c = fract( vMapUv * ${GRID_F} );
        vec2 e = vec2( ( abs( c.x - 0.5 ) - ${EYE_U.toFixed(4)} ) / ${EYE_A.toFixed(4)}, ( c.y - ${(EYE_V - 0.02).toFixed(4)} ) / ${EYE_B.toFixed(4)} );
        float shut = step( fract( ( uBlinkT + pBlink * 1.37 ) / ( 3.0 + 0.19 * pBlink ) ) * ( 3.0 + 0.19 * pBlink ), 0.13 );
        shut *= step( 0.5, vPart.y ) * step( vPart.y, 1.5 ) * ( 1.0 - step( 0.8, vMapUv.x ) * step( 0.8, vMapUv.y ) );      // (skin, not the blank cell)
        float lid = shut * ( 1.0 - smoothstep( 0.8, 1.0, length( e ) ) );
        float lash = ( 1.0 - smoothstep( 0.09, 0.17, abs( e.y - 0.38 + 0.30 * e.x * e.x ) ) ) * ( 1.0 - smoothstep( 0.015, 0.04, length( fwidth( c ) ) ) );     // (the line from near only)
        drawn = mix( drawn, vec4( mix( vec3( 1.0 ), vec3( 0.07, 0.05, 0.05 ), lash * step( abs( e.x ), 0.92 ) ), 1.0 ), lid );
      }
      diffuseColor.rgb = mix( vec3( ${EYE_WHITE} ), diffuseColor.rgb * drawn.rgb, drawn.a );
      // the drawn glasses: in as the rims' geometry goes (how many pixels a rim is across, from the atlas' scale here)
      vec2 rimD = vec2( length( dFdx( vMapUv ) ), length( dFdy( vMapUv ) ) );
      float rimPx = ${RIM_UV} / max( max( rimD.x, rimD.y ), 1e-7 );
      float rim = texture2D( uRims, vMapUv ).r * step( 0.5, pGlass ) * smoothstep( ${(2 * RIM_PX).toFixed(2)}, ${RIM_PX.toFixed(2)}, rimPx );
      diffuseColor.rgb = mix( diffuseColor.rgb, pGlass > 1.5 ? ${glsl(RIMS[1])} : ${glsl(RIMS[0])}, rim );
      float pLegs = step( 0.5, vLeg.w ) * step( 0.01, vLeg.x + vLeg.y );      // (a geometry without the attribute reads 0 0 0 1)
      if ( vLeg.w > 0.2 && vLeg.w < 0.4 ) {
        // a checked shirt, in checks: round the trunk (evenly round an oval about its middle) and up it; over the
        // shoulders, where the cloth lies flat, across and back (a yoke); round a sleeve (about the arm's axis) and
        // along it
        float ax = abs( vRest.x ), k = ${(1 / CHECK.pitch).toFixed(3)};
        float dq = length( fwidth( vRest ) ) * k;          // (checks to a pixel)
        vec2 t = vec2( vRest.x, vRest.z - ( vLeg.z - 0.5 ) );
        vec3 base = diffuseColor.rgb;
        if ( ax > vLeg.x ) diffuseColor.rgb = pPlaid( vec2( atan( vRest.y - ( 1.0 + vLeg.y ), t.y ) * ${(CHECK.sleeve / (2 * Math.PI)).toFixed(4)}, ax * k ), dq, base );
        else diffuseColor.rgb = mix( pPlaid( vec2( 0.5 * ( atan( t.x, t.y ) + atan( t.x * ${CHECK.deep}, t.y ) ) * ${(CHECK.round / (2 * Math.PI)).toFixed(4)}, vRest.y * k ), dq, base ),
          pPlaid( vRest.xz * k, dq, base ), smoothstep( 0.55, 0.8, abs( normalize( vRestN ).y ) ) );
      }
      float pJean = pLegs * step( 0.5, pWash );
      if ( pLegs > 0.5 ) {
        // trousers, by a leg's own coordinates: a (x 1 the front, -1 the back; y 1 the outside, -1 the inside) and
        // the height h (0 the hem, 0.5 the knee, 1 the hip joint, 1.2 the waistband)
        vec2 a = normalize( vLeg.xy * 2.0 - 1.0 + 1e-4 );
        float h = vLeg.z * ${LEG_TOP};
        vec2 da = fwidth( a );
        float dh = fwidth( h );
        float below = 1.0 - smoothstep( 0.80, 0.86, h );                 // (under the crotch)
        // denim worn pale where it rubs (the front of the thigh, the knee, the seat), dark where it does not (the
        // inside of the leg, behind the knee, the hem): more of it the paler the wash
        float thigh = smoothstep( 0.0, 0.8, a.x ) * smoothstep( 0.36, 0.62, h ) * ( 1.0 - smoothstep( 0.84, 1.02, h ) ) * 0.8;
        float knee = smoothstep( 0.1, 0.9, a.x ) * exp( - pow( ( h - 0.50 ) / 0.10, 2.0 ) );
        float shin = smoothstep( 0.3, 0.95, a.x ) * smoothstep( 0.05, 0.2, h ) * ( 1.0 - smoothstep( 0.3, 0.46, h ) );
        float seat = smoothstep( 0.1, 0.8, - a.x ) * exp( - pow( ( h - 0.97 ) / 0.085, 2.0 ) ) * ( 1.0 - smoothstep( 0.45, 0.9, abs( a.y ) ) );
        float worn = max( max( thigh, knee ), max( seat * 0.8, shin * 0.3 ) );
        float dark = max( smoothstep( 0.3, 0.95, - a.y ) * below * 0.7, smoothstep( 0.3, 0.9, - a.x ) * exp( - pow( ( h - 0.50 ) / 0.07, 2.0 ) ) * 0.55 );
        dark = max( dark, ( 1.0 - smoothstep( 0.03, 0.09, h ) ) * 0.35 );
        float fade = pWash < 0.5 ? 0.0 : pWash < 1.5 ? 0.07 : pWash < 2.5 ? 0.25 : 0.55;
        // (what worn denim pales to: blue to a milky blue, black to charcoal)
        vec3 pPale = mix( vec3( 0.36, 0.37, 0.40 ), vec3( 0.60, 0.68, 0.78 ), smoothstep( 0.01, 0.04, vColor.b - vColor.r ) );
        diffuseColor.rgb = mix( diffuseColor.rgb, pPale, fade * worn );
        diffuseColor.rgb *= 1.0 - dark * ( pWash < 0.5 ? 0.0 : 0.30 );
        // the seams down the outside and the inside, the hem, the waistband, the pockets: a dark line, on denim with
        // the paler ridge the wash leaves beside it
        float side = max( pLine( a.x, 0.035, da.x ) * step( 0.0, a.y ), pLine( a.x, 0.035, da.x ) * step( a.y, 0.0 ) * below );
        float ridge = max( pLine( a.x, 0.10, da.x ) * step( 0.0, a.y ) * 0.6, ( 1.0 - smoothstep( 0.0, 0.022, h ) ) );
        float hem = pLine( h - 0.030, 0.0035, dh ) + pLine( h - 1.105, 0.004, dh );
        vec2 pk = vec2( ( a.y - 0.06 ) / 0.50, h );                      // a back pocket: a patch with a pointed foot
        float foot = 0.865 - 0.03 * ( 1.0 - min( 1.0, abs( pk.x ) ) );
        float inPk = step( a.x, -0.2 ) * step( abs( pk.x ), 1.0 ) * step( foot, h ) * step( h, 1.015 );
        float pocket = step( a.x, -0.2 ) * max( max( pLine( abs( pk.x ) - 1.0, 0.045, da.y / 0.50 ) * step( foot, h ) * step( h, 1.015 ),
          pLine( h - 1.015, 0.004, dh ) * step( abs( pk.x ), 1.0 ) ), pLine( h - foot, 0.004, dh ) * step( abs( pk.x ), 1.0 ) );
        float scoop = pLine( h - ( 1.105 - 0.17 * smoothstep( 0.30, 0.98, a.y ) ), 0.004, dh ) * step( 0.0, a.x ) * step( 0.30, a.y );
        float line = max( max( side, min( 1.0, hem ) ), max( pocket, scoop ) );
        diffuseColor.rgb = mix( diffuseColor.rgb, pPale, fade * 0.6 * max( ridge, inPk * 0.25 ) * ( 1.0 - line ) );
        diffuseColor.rgb *= 1.0 - line * ( pWash < 0.5 ? 0.16 : 0.34 );
      }`)
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
        float pH = pFolds( vRest, pLegs ) * pCloth * pNear + ( pStrand - 0.5 ) * 0.0018 * pHair * pNear;
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
  // (the shoulder joint at rest, for a checked shirt)
  root.updateMatrixWorld(true);
  const joint = root.getObjectByName('UpperArmL')?.getWorldPosition(new THREE.Vector3());
  const byte = (v) => Math.max(0, Math.min(255, Math.round(v * 255)));
  const check = joint && [byte(Math.abs(joint.x) + 0.02), byte(joint.y - 1), byte(joint.z + 0.5), CHECK_W];
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
    // the trousers' own coordinates (the model's _LEG, four bytes; only the parts with trousers have it)
    const leg = new Uint8Array(n * 4), sl = src.attributes._leg;
    if (sl) for (let i = 0; i < n * 4; i++) leg[i] = sl.array[i];
    // (a checked shirt: where its sleeves begin, and the arms' axis: its height over 1 m, its depth + 0.5 m)
    else if (m.material.name === 'Check' && check) for (let i = 0; i < n; i++) leg.set(check, i * 4);
    g.setAttribute('leg', new THREE.Uint8BufferAttribute(leg, 4, true));
    ranges.push({ name: m.material.name, start: at, count: n, hex: '#' + m.material.color.getHexString(), legs: !!sl });
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
// (blender/characters.py JEANS: mid, dark 진청, light 연청, black 블랙진)
const JEANS = ['#44628f', '#1e2b4a', '#8fabcc', '#26272b'];
// how washed out a pair of trousers of this colour is: 0 not denim, 1 dark (rinsed), 2 mid, 3 pale (stone-washed);
// black denim is washed as the mid blue is, to charcoal (the shader tells by the colour what it fades to)
const WASH = { [JEANS[0]]: 2, [JEANS[1]]: 1, [JEANS[2]]: 3, [JEANS[3]]: 2 };
function washOf(hex) {
  const c = new THREE.Color(hex), d = new THREE.Color();
  for (const k in WASH) { d.set(k); if (Math.abs(c.r - d.r) + Math.abs(c.g - d.g) + Math.abs(c.b - d.b) < 0.02) return WASH[k]; }
  return 0;
}
const SKIN = ['#f0c9a4', '#e6b991', '#d9a77d', '#c99168'];
const SKIN_FAIR = '#f7ddc8', SKIN_TAN = '#b9825a';      // now and then somebody fair, or tanned (가무잡잡)
// material name -> the colours to draw from (the first is the model's own)
const LOOKS = {
  'man-tee': { LightBrown: ['#f1efe8', '#f1efe8', '#d8dde3', '#e9dfa8', '#a9c3de', '#2f3a55', '#9a9a96'], LightBlue: [...JEANS, '#a8946a'] },
  'man-check': { Check: ['#d6c49c', '#d6c49c', '#9db4d0', '#8f2a30', '#2f5a45', '#27345a', '#e4e0d4'], LightBlue: [...JEANS, '#a8946a', '#3a3f47'] },
  'man-hoodie': { Purple: ['#23345e', '#8d8f92', '#2f5a45', '#6e2430', '#c9c3b2', '#1f1f24'], LightBlue: ['#a8946a', ...JEANS, '#3a3f47'] },
  'man-cheer': { LightBlue: JEANS },                       // (the cheer jacket stays Yonsei blue)
  'man-grey': { LightBrown: ['#1f2f55', '#2f5a45', '#6e2430', '#1f2f55', '#2a2a2e', '#e4e0d4'], LightBlue: [JEANS[1], ...JEANS, '#3a3f47', '#a8946a'] },
  'man-blazer': { Suit: ['#27304a', '#5e4634', '#4a4d52', '#8a7a5c', '#3d4a3a'], LightBlue: ['#b9a67e', ...JEANS, '#2c3550'] },
  'man-professor': { Suit: ['#55595f', '#2c3448', '#4a4038', '#3a3f47', '#6b6a5c'], Tie: ['#2f4a7a', '#6e2430', '#3d5a45', '#4a4a50'] },
  'man-staff': {},
  'woman-tee': { White: ['#f4f1e8', '#f4f1e8', '#f3d9de', '#cfe0ee', '#e9dfa8', '#2f3a55', '#b9c9a8'], Orange: [...JEANS, '#cdb994', '#2a2a2e'] },
  'woman-pink': { White: ['#e7a7b6', '#f0e6d2', '#a9c3de', '#c7b3dc', '#b5d6c3', '#e8c66a', '#c95a5a'], Orange: ['#cdb994', ...JEANS, '#2a2a2e', '#f0eee8'] },
  'woman-dress': { LimeGreen: ['#a3202c', '#f1ede1', '#f3d9de', '#cfe0ee', '#ecdf9e', '#2a2a2e', '#b9c9a8'] },
  'woman-dress-blue': { LimeGreen: ['#ece4cc', '#ece4cc', '#8d8f92', '#27345a', '#6e2430', '#2f5a45', '#f3d9de', '#a9c6e6'] },
  'woman-cardigan': { Black: ['#ecdf9e', '#f3d9de', '#6f7f5a', '#8d8f92', '#2f3a55', '#e6dcc6', '#c98a8a'], Orange: [JEANS[1], ...JEANS, '#2b2f3a', '#cdb994'] },
  'woman-staff': { Black: ['#2f3644', '#3a3f47', '#4a4038', '#5b6470'] },
};
// the parts painted on an outfit (blender/characters.py `paint`): the stripes and the collar of a tee, a skirt, a
// sweatshirt's ribbing; and the tee under an open shirt. Drawn from a stream of their own, after everything else
const LOOKS_MORE = {
  'man-check': { LightGreen: ['#f1efe8', '#f1efe8', '#f1efe8', '#1f1f24', '#8d8f92'] },         // (the tee under the shirt)
  'man-grey': { Stripe: ['#1f8580', '#e9e4d6', '#d8b23a', '#7f9cc0', '#b3262e'], Stripe2: ['#d8742c', '#e9e4d6', '#8d8f92', '#c95a5a'],
    Collar: ['#ece8dc', '#ece8dc', '#1f2f55'] },
  // (the skirt is cut as denim: half of them are; the hairband shows on one in three, else it is the hair's black)
  'woman-dress': { Skirt: [JEANS[0], JEANS[0], JEANS[2], JEANS[1], '#1f1f24', '#8a7a5c', '#6e2430', '#4a4d52'],
    Band: ['#e3c443', '#141110', '#141110', '#b3262e', '#141110', '#f1ede1'] },
  'woman-dress-blue': { Orange: [JEANS[3], ...JEANS, '#f0eee8', '#e3cf7a', '#2a2a2e'] },
};
// the bars and the heel tab of a pair of trainers (blender/characters.py trainers()), from a stream of their own
const TRAINERS = { 'man-tee': 1, 'man-cheer': 1, 'woman-tee': 1, 'woman-pink': 1, 'woman-cardigan': 1 };
const BARS = ['#27345a', '#b3262e', '#2f5a45', '#1f1f24', '#8d8f92', '#1d3fa0'];
// the sides and the back clipped so short that the skin shows (blender/characters.py `fade`, FADE): how much of it in
// the upper and the lower band
const FADED = { 'man-hoodie': [0.40, 0.62] };
// stubble over skin: the hair's colour with t of the skin's, half way to grey (blender/characters.py hex_fade)
function fadeHex(hair, skin, t) {
  const h = parseInt(hair.slice(1), 16), s = parseInt(skin.slice(1), 16);
  const ch = [16, 8, 0].map((k) => ((h >> k) & 255) * (1 - t) + ((s >> k) & 255) * t);
  const grey = 0.3 * ch[0] + 0.59 * ch[1] + 0.11 * ch[2];
  return '#' + ch.map((v) => Math.round((v + grey) / 2).toString(16).padStart(2, '0')).join('');
}
// about one striped tee in three is plain: its stripes and collar in the tee's own colour
// (and a sweatshirt's ribbing is always the sweatshirt's colour: the model's own is a shade darker)
const PLAIN = { 'man-grey': ['LightBrown', ['Stripe', 'Stripe2', 'Collar'], 0.35], 'woman-dress-blue': ['LimeGreen', ['Rib'], 1] };
// what is printed on a chest (blender/faces.py PRINTS, characters.py print_map): the material it lies on, how many of
// the crowd in that model wear it, and the cloth it shows on (ink on light cloth; the jumper is always Yonsei blue).
// The heroes wear theirs.
const PRINTED = { 'man-tee': ['LightBrown', 0.2, true], 'man-cheer': ['Purple', 0.6, false], 'woman-tee': ['White', 0.4, true] };
const light = (hex) => { const c = new THREE.Color(hex); return c.r + c.g + c.b > 1.2; };       // (linear light)

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
  if (TRAINERS[id]) colors['Bar-feet'] = BARS[Math.floor(mulberry(n * 9973 + 59)() * BARS.length)];
  if (FADED[id]) {                                    // (clipped hair: this person's hair over this person's skin)
    colors.HairFade = fadeHex(colors.Hair, colors.Skin, FADED[id][0]);
    colors.HairFade2 = fadeHex(colors.Hair, colors.Skin, FADED[id][1]);
  }
  const pr = PRINTED[id];
  const print = !!pr && mulberry(n * 7919 + 101)() < pr[1] && (!pr[2] || light(colors[pr[0]]));
  return { colors, scale: [clamp(tall * build), clamp(tall)], glasses, blink, print };
}

// a hero's own size, [width, height] of the model's (the drivers and the crowd in the same model keep theirs):
// broader by half as much as taller
export function heroScale(id) {
  const h = HERO[id]?.height;
  if (!h) return null;
  const tall = h / (id.startsWith('woman') ? 1.61 : 1.73);
  return [1 + (tall - 1) / 2, tall];
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
  const k = n * 256 + v;
  if (!glassBuffers.has(k)) glassBuffers.set(k, new THREE.Uint8BufferAttribute(new Uint8Array(n).fill(v), 1));
  return glassBuffers.get(k);
}

// `geo` (a person's merged geometry, or that with a bag: the person's vertices come first) as one person wears it:
// the parts named in `colors` in those colours, with the glasses or without. A geometry sharing every buffer but
// the colours; people who wear the model as it is share one.
// the texture coordinates `uv` without what is printed on the clothes: the atlas' print cell (blender/faces.py PRINT:
// the cell before the blank one) pointed at the blank cell. One buffer for each model
const unprinted = new WeakMap();
function plainUv(uv) {
  let u = unprinted.get(uv);
  if (!u) {
    u = uv.clone();
    for (let i = 0; i < u.count; i++) if (u.getX(i) >= 0.6 && u.getX(i) < 0.8 && u.getY(i) >= 0.8) u.setXY(i, BLANK_UV, BLANK_UV);
    unprinted.set(uv, u);
  }
  return u;
}
const worn = new WeakMap();        // geometry -> [without glasses, with]
function dressed(geo, ranges, colors, glasses, blink = 0, print = true) {
  if (!ranges || !geo.attributes.color) return geo;
  if (!colors) {
    const made = worn.get(geo) || worn.set(geo, []).get(geo);
    return made[+glasses] || (made[+glasses] = dressed(geo, ranges, {}, glasses));        // (blink 0)
  }
  const g = new THREE.BufferGeometry();
  for (const k in geo.attributes) if (k !== 'color') g.setAttribute(k, geo.attributes[k]);
  if (!print) g.setAttribute('uv', plainUv(geo.attributes.uv));
  const order = glassesLast(geo, ranges);
  g.setIndex(order ? order.index : geo.index);
  if (order && !glasses) g.setDrawRange(0, order.bare);
  if (order && glasses) g.userData.rims = order.bare;           // (rimLod)
  const legs = ranges.find((p) => p.legs);
  g.setAttribute('glass', glassAttribute(geo.attributes.position.count,
    (!order || !glasses ? 0 : colors.Glasses === RIMS[1] ? 2 : 1) + 4 * blink + 64 * (legs ? washOf(colors[legs.name] || legs.hex) : 0)));
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
      let speeds = {};
      try { speeds = JSON.parse(u.speeds || '{}'); } catch { /* an older rig: the one walk */ }
      this.rigs[r] = { clips: g.animations, walkSpeed: +u.walk_speed || 1.2, runSpeed: +u.run_speed || 2.8, speeds };
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
  // scale: [width, height] of the model as it is (heroScale: the one you walk as)
  make(id, bag = HERO_BAGS[id] ?? null, look = null, scale = null) {
    const src = this.models[id];
    const holder = new THREE.Group();
    const root = skeletonClone(src.scene);
    if (bag) root.traverse((o) => { if (o.isSkinnedMesh) o.geometry = baggedGeometry(o, id, bag); });
    root.traverse((o) => {
      if (!o.isSkinnedMesh) return;
      o.geometry = dressed(o.geometry, src.ranges, look?.colors, look ? look.glasses : src.glasses, look?.blink, look ? look.print !== false : true);
      if (o.geometry.userData.rims) o.onBeforeRender = rimLod;
    });
    const [wide, tall] = scale || look?.scale || [1, 1];
    holder.scale.set(wide, tall, wide);
    // frustum culled by the posed bounds above (off-screen people cost nothing, in the shadow pass too)
    root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    holder.add(root);
    const rig = this.rigs[src.rig];
    const mixer = new THREE.AnimationMixer(root);
    const actions = {};
    for (const c of rig.clips) actions[c.name] = mixer.clipAction(c);
    // (longer legs: longer strides at the same cadence)
    const a = { id, bag, holder, root, mixer, actions, current: null, walkSpeed: rig.walkSpeed * tall, runSpeed: rig.runSpeed * tall, after: null, tall,
      stand: 'idle', gait: null, walks: {} };
    // the walks, slowest first: clip -> its speed over the ground at this person's size
    for (const n of WALKS) if (actions[n] && rig.speeds[n]) a.walks[n] = rig.speeds[n] * tall;
    if (!Object.keys(a.walks).length) a.walks.walk = a.walkSpeed;
    mixer.addEventListener('finished', () => { const next = a.after || a.stand; a.after = null; play(a, next, { fade: 0.3 }); });
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

const WALKS = ['walk-slow', 'walk', 'walk-fast'];
const STANDS = /^(idle|talk|phone)/;
// the clip follows the ground speed: by the clip's measured foot speed, so feet do not slide.  Of the walks the one
// whose own pace is nearest is played (kept until the speed is a quarter off it, so that it does not flicker between
// two), and a walk or the run comes in at the stride the one before had reached (the cycles start on the same foot).
// Standing: the clip `a.stand`; from one standing clip to another slowly (the feet stand differently in each).
export function locomotion(a, speed, runThreshold = 3.6) {
  if (gesturing(a)) return;
  if (!speed) {
    a.gait = null;
    play(a, a.stand, { fade: a.current && STANDS.test(a.current.getClip().name) ? 0.9 : 0.3 });
    return;
  }
  const v = Math.abs(speed);
  const from = a.current;
  if (v > runThreshold && a.actions.sprint) {
    a.gait = null;
    inStep(from, play(a, 'sprint')).timeScale = v / a.runSpeed;
    return;
  }
  let name = a.gait;
  if (!name || v > a.walks[name] * 1.28 || v < a.walks[name] * 0.78) {
    name = null;
    for (const n in a.walks) if (!name || Math.abs(Math.log(v / a.walks[n])) < Math.abs(Math.log(v / a.walks[name]))) name = n;
    a.gait = name;
  }
  inStep(from, play(a, name)).timeScale = Math.sign(speed) * v / a.walks[name];
}
// a walk or the run coming in after another: at the same point of the stride
function inStep(from, act) {
  if (from && from !== act && /^(walk|sprint)/.test(from.getClip().name)) act.time = (from.time / from.getClip().duration) * act.getClip().duration;
  return act;
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
    const a = cast.make(id, undefined, null, heroScale(id));
    a.mixer.update(0.5);
    a.holder.rotation.y = 0.45;
    sc.add(a.holder);
    const top = (id.startsWith('woman') ? 1.61 : 1.73) * a.tall;
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
