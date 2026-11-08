// The clipped shrubs' bodies (materials.json hedge_*: the opaque leaf materials; blender/shrubs.py). Their surface
// is a seamless tile of clipped foliage with its normal map (tools/make_shrub_textures.py hedge_<name>.jpg,
// hedge_<name>_nor.jpg), laid from three sides in world space and blended by the face's normal: no UVs to stretch
// over a dome or a cone, the leaves the same size on every shrub whatever its scale, and the pieces of a hedge row
// (each its own instance, overlapping the next) carry one continuous leaf pattern, so the row reads as one hedge.
// A slow tone over the surface keeps a long hedge from repeating its tile. Phones: the colour only (three taps), the
// normal map is left off.
// The sprig cards that stand out of the bodies keep the usual leaf atlases (leaf_<name>.png), the same season's.
import { MOBILE } from './util.js';

// metres per repeat of each surface tile (tools/make_shrub_textures.py TILE: the leaves at their real size)
const TILE = { boxwood: 0.5, azalea: 0.7, azalea_red: 0.7, azalea_violet: 0.7, pansy: 0.6 };
const tiles = {};

// The textures a shrub wears in a season (spring = mid-April, summer = late May, autumn = late October):
// 영산홍 (the bushes round the halls) magenta in April; 철쭉 red from late April through May; 진달래 violet in April
// before its leaves; in late October the azaleas' leaves bronze and red. Boxwood and the pansy border all year.
export function shrubTexture(species, season) {
  if (species === 'azalea') return season === 'spring' ? 'azalea' : season === 'autumn' ? 'azalea_autumn' : 'azalea_summer';
  if (species === 'azalea_red') return season === 'autumn' ? 'azalea_autumn' : 'azalea_red';
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
export const SHRUB_LEAVES = new Set(['boxwood', 'azalea', 'azalea_red', 'azalea_violet', 'pansy']);
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
        vec3 hdP = vHedgeW * uHedgeTile;
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
