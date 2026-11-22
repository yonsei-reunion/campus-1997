// The clipped shrubs' bodies (materials.json hedge_*: the opaque leaf materials; blender/shrubs.py). Their surface
// is a seamless tile of clipped foliage with its normal map (tools/make_shrub_textures.py hedge_<name>.jpg,
// hedge_<name>_nor.jpg), laid from three sides in world space and blended by the face's normal: no UVs to stretch
// over a dome or a cone, the leaves the same size on every shrub whatever its scale, and the pieces of a hedge row
// (each its own instance, overlapping the next) carry one continuous leaf pattern, so the row reads as one hedge.
// A slow tone over the surface keeps a long hedge from repeating its tile. Phones: the colour only (three taps), the
// normal map is left off.
// The sprig cards that stand out of the bodies keep the usual leaf atlases (leaf_<name>.png), the same season's.
import * as THREE from 'three';
import { MeshoptSimplifier } from 'meshoptimizer/simplifier';
import { MOBILE } from './util.js';

// metres per repeat of each surface tile (tools/make_shrub_textures.py TILE: the leaves at their real size)
const TILE = { boxwood: 0.5, azalea: 0.7, azalea_red: 0.7, azalea_violet: 0.7, pansy: 0.6, summerbed: 0.6 };
const tiles = {};

// The textures a shrub wears in a season (spring = mid-April, summer = late May, autumn = late October):
// 철쭉 and 영산홍 (the bushes round the halls) flower from late April into May in Seoul: in mid-April they are still
// in last winter's red-brown leaves with the new shoots coming, a bud here and there (the 2011-04-16 roadview round
// the eagle, 2003 April photos), in late May in bloom, red and magenta (the May 1997 photo of the gate island).
// 진달래 flowers before its leaves, from about the end of March (Seoul's mean, KMA 1971-2000: 3-31) into the cherries'
// bloom (1997: 4-8): still out in mid-April, the first leaves coming (reference/용재관.jpg, 2003 April photos); leaves
// in May. In late October the azaleas' leaves bronze and red. Boxwood and the pansy border all year, and so the
// rotary island's summer bed (summerbed: 신촌 로터리, 52127 of August 1996, the bed as July 1997's scans have it).
export function shrubTexture(species, season) {
  if (species === 'azalea') return season === 'spring' ? 'azalea_spring' : season === 'autumn' ? 'azalea_autumn' : 'azalea';
  if (species === 'azalea_red') return season === 'spring' ? 'azalea_spring' : season === 'autumn' ? 'azalea_autumn' : 'azalea_red';
  if (species === 'azalea_violet') return season === 'spring' ? 'azalea_violet' : season === 'autumn' ? 'azalea_autumn' : 'azalea_summer';
  return species;
}

// a body's colour and normal maps in a season, and whether it takes the normal map at all
export function hedgeMaps(species, season) {
  const n = shrubTexture(species, season);
  return { map: `assets/textures/hedge_${n}.jpg`, normal: MOBILE ? null : `assets/textures/hedge_${n}_nor.jpg` };
}

// The sprig cards (leaf_<name>, not opaque): blender/shrubs.py gives each card the body's normal at its foot, so it
// shades like the clipped face it grows from, from either side. three turns a double-sided face's normal round when
// its back is seen, which would light half of the cards as if they faced into the shrub: they keep it.
export const SHRUB_LEAVES = new Set(['boxwood', 'azalea', 'azalea_red', 'azalea_violet', 'pansy', 'summerbed']);
export const CARD_KEY = 'shrubCard';
export const cardEdit = (sh) => {
  sh.fragmentShader = sh.fragmentShader.replace('#include <normal_fragment_begin>', `#include <normal_fragment_begin>
    #ifdef DOUBLE_SIDED
    normal *= faceDirection;
    #endif`);
};

// the shader edit (materials.js patchShader, key HEDGE_KEY)
export const HEDGE_KEY = 'hedge';
export function hedgeEdit(species) {
  const uTile = (tiles[species] ||= { value: 1 / (TILE[species] ?? 0.6) });
  return (sh) => {
    sh.uniforms.uHedgeTile = uTile;
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vHedgeW;\nvarying vec3 vHedgeN;')
      .replace('#include <project_vertex>', `#include <project_vertex>
        {
          vec4 hdW = vec4( transformed, 1.0 );
          #ifdef USE_INSTANCING
          hdW = instanceMatrix * hdW;
          #endif
          vHedgeW = ( modelMatrix * hdW ).xyz;
          vHedgeN = ( vec4( transformedNormal, 0.0 ) * viewMatrix ).xyz;      // (world: the view's turn undone)
        }`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float uHedgeTile;\nvarying vec3 vHedgeW;\nvarying vec3 vHedgeN;')
      .replace('#include <map_fragment>', `
        vec3 hdN = normalize( vHedgeN );
        vec3 hdB = pow( abs( hdN ), vec3( 4.0 ) );
        hdB /= hdB.x + hdB.y + hdB.z;
        vec3 hdP = (vHedgeW + vec3(0.0, 2.0, 0.0)) * uHedgeTile;     // (the tiles as laid on the old datum, 2.0 m higher)
        // the three projections: v runs down the world's up axis on the two side ones (the tile's top is up)
        vec2 hdUx = vec2( hdP.z, - hdP.y ), hdUy = hdP.xz, hdUz = vec2( hdP.x, - hdP.y );
        #ifdef USE_MAP
        {
          vec4 sampledDiffuseColor = texture2D( map, hdUx ) * hdB.x + texture2D( map, hdUy ) * hdB.y
            + texture2D( map, hdUz ) * hdB.z;
          float hdM = sin( dot( vHedgeW, vec3( 1.9, 1.3, 2.3 ) ) ) * sin( dot( vHedgeW, vec3( - 1.1, 2.9, 1.7 ) ) );
          sampledDiffuseColor.rgb *= 1.0 + 0.12 * hdM;
          diffuseColor *= sampledDiffuseColor;
        }
        #endif`)
      // the normal map's slopes (x along the tile's u, y along its v) added to the face's normal in world space
      .replace('#include <normal_fragment_maps>', `
        #ifdef USE_NORMALMAP
        {
          vec2 hdX = texture2D( normalMap, hdUx ).xy * 2.0 - 1.0;
          vec2 hdY = texture2D( normalMap, hdUy ).xy * 2.0 - 1.0;
          vec2 hdZ = texture2D( normalMap, hdUz ).xy * 2.0 - 1.0;
          vec3 hdT = vec3( 0.0, - hdX.y, hdX.x ) * hdB.x + vec3( hdY.x, 0.0, hdY.y ) * hdB.y + vec3( hdZ.x, - hdZ.y, 0.0 ) * hdB.z;
          vec3 hdF = hdN;
          #ifdef DOUBLE_SIDED
          hdF *= faceDirection;
          #endif
          normal = normalize( ( viewMatrix * vec4( normalize( hdF + hdT * normalScale.x ), 0.0 ) ).xyz );
        }
        #endif`);
  };
}

// A shrub from farther still (main.js SHRUB_FAR2): its lighter model (blender/shrubs.py far_version) without the sprig
// cards and with a body of fewer faces. From the gate a phone drew some 1,500 hedge pieces and 2,000 other shrubs at
// their _far models (400 k triangles), nearly all of them more than 50 m off, where a 0.6 m hedge is a few pixels
// high and the cards' fringe less than one. The body's corners are welded by place first (the model splits them
// along its seams). Those bodies are already about as light as simplify can make them (a hedge piece 76 triangles,
// 68 at best), so the sloppy simplifier (which merges by place, whatever the surface's shape) takes the fewest of
// FAR2_SHARES whose error stays within FAR2_ERR; each corner keeps the first one's normal and shade.
export const far2Ready = MeshoptSimplifier.ready.then(() => true, (e) => { console.warn('shrubs: no far2 models', e); return false; });
const FAR2_SHARES = [0.25, 0.35, 0.5, 0.7], FAR2_ERR = 0.08;     // (error: of the model's size; 50 m off on a phone 0.08 of a 1 m shrub is under a pixel)
function fewerFaces(idx, P) {
  for (const share of FAR2_SHARES) {
    // (unbounded, then judged by the error it reports: given FAR2_ERR as its bound it stops well short of the share)
    const [index, err] = MeshoptSimplifier.simplifySloppy(idx, P, 3, null, Math.floor(idx.length * share / 3) * 3, 1);
    if (index.length && err <= FAR2_ERR) return index;
  }
  return MeshoptSimplifier.simplify(idx, P, 3, 0, FAR2_ERR)[0];
}
export function shrubFar2(scene) {
  const g = new THREE.Group();
  scene.updateMatrixWorld(true);
  scene.traverse((o) => {
    if (!o.isMesh || o.material.name.startsWith('leaf_')) return;
    const geo = o.geometry.clone();
    geo.applyMatrix4(o.matrixWorld);
    if (geo.index && !o.material.name.startsWith('bark')) {
      const pos = geo.attributes.position, n = pos.count, P = new Float32Array(n * 3), first = new Map(), remap = new Uint32Array(n);
      for (let i = 0; i < n; i++) {
        P[i * 3] = pos.getX(i); P[i * 3 + 1] = pos.getY(i); P[i * 3 + 2] = pos.getZ(i);
        const k = `${Math.round(P[i * 3] * 1e4)},${Math.round(P[i * 3 + 1] * 1e4)},${Math.round(P[i * 3 + 2] * 1e4)}`;
        remap[i] = first.has(k) ? first.get(k) : (first.set(k, i), i);
      }
      const src = geo.index.array, idx = new Uint32Array(src.length);
      for (let i = 0; i < src.length; i++) idx[i] = remap[src[i]];
      const index = fewerFaces(idx, P);
      geo.setIndex(new THREE.BufferAttribute(n > 65535 ? index : Uint16Array.from(index), 1));
    }
    const m = new THREE.Mesh(geo, o.material);
    m.name = o.name;
    g.add(m);
  });
  return g;
}
