import '@fontsource/noto-sans-kr/400.css';
import '@fontsource/noto-sans-kr/700.css';
import '@fontsource/jua/400.css';
import '@fontsource/do-hyeon/400.css';
import * as THREE from 'three';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { MaterialLibrary, SEASONS, texturesReady, texCount, updatePcss, uploadEarly } from './materials.js';
import { loading, fetchCounted } from './loading.js';
import { ATMOS, globalPatch, setupAtmosphere, updateAtmosphere } from './materials.js';
import { Heightfield, makeNearTerrain, makeSouthTerrain, makeFarTerrain, makeFarForest, makeSummitTower, makeCity, makeSky, drapeTerrain } from './terrain.js';
import { loadGLB, prefetch, glbMaterials, bindMaterials, mergeStatic, InstancedKit, KitCuller, Forest } from './world.js';
import { Grass } from './grass.js';
import { Fall } from './fall.js';
import { Player, Colliders } from './player.js';
import { UI } from './ui.js';
import { Post } from './post.js';
import { Path, makeBanners, Crowd, Traffic, BoothGates, CAR_COLORS } from './life.js';
import { Cast, PEOPLE, STUDENTS, HEROES, portraits, castFiles } from './characters.js';
import { BirdsEye } from './birdseye.js';
import { SunShadows } from './shadows.js';
import { TouchControls } from './touch.js';
import { setupNews } from './news.js';
import { WalkLabels } from './labels.js';
import { Bubbles } from './talk.js';
import { FountainWater } from './water/fountain.js';
import { Birthday } from './birthday.js';
import { Basketball } from './hoops.js';
import { startPlaces } from './places.js';
import { SunMap, bakeSunMap } from './bakedshadow.js';
import { Blobs } from './blobs.js';
import { Birds } from './birds.js';
import { flagWind } from './flags.js';
import { Decals } from './decals.js';
import { Curbs } from './curbs.js';
import { Verge } from './verge.js';
import { Sound } from './audio.js';
import { addTown, Street } from './town.js';
import { $, MOBILE, versioned, safeGet, safeSet, mulberry, countBy, polylineLength, closestOnSegment, placeMatrix } from './util.js';

const canvas = $('#view');
let season = safeGet('y97-season');
if (!SEASONS[season]) season = 'summer';
const NOBODY = { x: 1e9, y: 1e9 };       // the player before the walk starts: nobody in the way
// The weights of main()'s steps together: a weight is the hundredths of a second the step before the call takes on a
// desktop (window.__y97.loading.state.marks after a load says; the 90 or so models of trees, shrubs, props and people
// are 1 each, the town outside the gate 20, and the first frames after the last call 190).
const STEPS = 960;

// ------------------------------------------------------------------ progress
// the bar, its percentage and the cards beside it: loading.js. The data files' bytes are counted as they come down.
const progress = (label, weight) => loading.step(label, weight);
const json = (u) => fetchCounted(u).then((b) => JSON.parse(new TextDecoder().decode(b)));
const MODELS = 'assets/models/';
const CARS = ['sedan', 'sedan2', 'hatch', 'tico', 'taxi', 'van'];
const PROPS = ['lamp_double', 'lamp_quad', 'lamp_arm', 'flag_white', 'planter', 'stone_marker', 'sign_board', 'motorbike',
  ...CARS.flatMap((k) => [`car_${k}`, `car_${k}_far`]), 'payphone', 'bench', 'recycle_bin', 'guard_booth', 'barrier_arm', 'bollard',
  'tent_kiosk', 'notice_board', 'haetae', 'parking_booth', 'bus'];
const CAR_FAR = 20;     // parked cars farther than this from the camera: their lighter models (a fifth of the triangles)
const SHRUB_FAR = 25;   // shrubs, hedges and flower beds farther than this: theirs (blender/shrubs.py far_version)
// the vegetation campus.json plants: two models of each tree species, one of each shrub (and its lighter one, _far)
const treeFile = (sp, v) => `veg/${sp}_${v}.glb`, shrubFile = (k) => `veg/${k}.glb`;
const vegFiles = (campus) => [...new Set(campus.trees.map((t) => t[0]))].flatMap((sp) => [treeFile(sp, 0), treeFile(sp, 1)])
  .concat([...new Set(campus.shrubs.map((s) => s[0]))].flatMap((k) => [shrubFile(k), shrubFile(k + '_far')]));
const bin = (u) => fetchCounted(u).then((b) => new Float32Array(b));

function seasonButtons(v) {
  document.querySelectorAll('[data-season]').forEach((b) => b.classList.toggle('on', b.dataset.season === v));
}
seasonButtons(season);
setupNews();

async function main() {
  loading.expect(STEPS);
  texCount.onChange = () => loading.textures(texCount.asked, texCount.done);
  // every model of the loading screen asked for at once (world.js prefetch), the vegetation once campus.json names it;
  // the halls first, the rest at low priority. The environment map comes down with the data.
  const halls = ['campus_buildings.glb', 'campus_landmarks.glb', 'baekyangro.glb', 'campus_town.glb'].map((f) => MODELS + f);
  prefetch(halls);
  prefetch([...PROPS.map((n) => `${MODELS}props/${n}.glb`), ...castFiles(Object.keys(PEOPLE))], 'low');
  const envHdr = new RGBELoader().loadAsync(versioned('assets/hdri/env_1k_nosun.hdr'));
  const [campus, matDefs, skyMeta, nearData, farData, entrances, southData] = await Promise.all([
    json('data/campus.json').then((c) => { prefetch(vegFiles(c).map((f) => MODELS + f), 'low'); return c; }),
    json('data/materials.json'), json('data/sky.json'),
    bin('data/terrain_near.bin'), bin('data/terrain_far.bin'),
    json('data/entrances.json').catch(() => ({ entrances: [] })),
    bin('data/terrain_south.bin').catch(() => null),        // 신촌 로터리: the patch south of the grid
  ]);
  progress('지형 데이터를 펼치는 중…', 60);

  // ---------------------------------------------------------------- renderer / scene
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.setSize(innerWidth, innerHeight);
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.toneMappingExposure = 1.05;
  // Phones: no shadow maps. On a Pixel 10 (PowerVR DXT) the shadow pass crashes Chrome's GPU process
  // (SIGSEGV in the driver's LoadTextureState -> WebGL context lost -> white screen) at any map size.
  renderer.shadowMap.enabled = !MOBILE;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  uploadEarly(renderer);          // (each texture to the GPU as it comes)

  const scene = new THREE.Scene();
  // switches fog on (USE_FOG) for every material; what they draw is the height fog of materials.js ATMOS (globalPatch)
  const fogColor = new THREE.Color(0xc4cfd8);
  scene.fog = new THREE.FogExp2(fogColor, 0.0003);
  const camera = new THREE.PerspectiveCamera(66, innerWidth / innerHeight, 0.1, 12000);

  const lib = new MaterialLibrary(matDefs);
  lib.setSeason(season);
  // the halls' textures asked for as soon as their files are in, not once they are parsed and merged
  for (const u of halls) glbMaterials(u).then((names) => { for (const n of names) if (lib.defs[n]) lib.get(n); });

  // Environment lighting from the CC0 Poly Haven HDRI (same sky as the backdrop) with its sun's disc taken out
  // (blender/sky_bake.py): left in, the disc was ~70 % of the light an upward face got from the environment, and as
  // no shadow map stops the environment, the shade under trees and buildings was lit by the sun all the same.
  const pmrem = new THREE.PMREMGenerator(renderer);
  const hdr = await envHdr;
  hdr.mapping = THREE.EquirectangularReflectionMapping;
  scene.environment = pmrem.fromEquirectangular(hdr).texture;
  scene.environmentIntensity = 0.75;
  progress('하늘을 칠하는 중…', 5);

  // sun direction from the HDRI's brightest texel (three equirect convention)
  const phi = (skyMeta.sun_u - 0.5) * Math.PI * 2, el = (skyMeta.sun_v - 0.5) * Math.PI;
  const sunDir = new THREE.Vector3(Math.cos(el) * Math.cos(phi), Math.sin(el), Math.cos(el) * Math.sin(phi)).normalize();
  // The disc's light shines from the DirectionalLight instead, so the shadow maps (on phones the baked sun shadow)
  // and the clouds take all of the sun. sky.json sun_E is what the disc threw on a face turned to it (linear); three's
  // PMREM had spread it over a lobe narrower than the cosine law, so that an upward face got only ~70 % of it: 0.7
  // keeps the sunlit ground as bright as it was. 3.1 -> 3.9: what the hemisphere light below no longer gives a floor.
  const sunRGB = new THREE.Color(0xfff1dc).multiplyScalar(3.9)
    .add(new THREE.Color().fromArray(skyMeta.sun_E).multiplyScalar(scene.environmentIntensity * 0.7));
  const sunI = Math.max(sunRGB.r, sunRGB.g, sunRGB.b);
  const sun = new THREE.DirectionalLight(sunRGB.clone().multiplyScalar(1 / sunI), sunI);
  sun.castShadow = true;
  sun.shadow.mapSize.set(4096, 4096);
  const SH = 125;
  Object.assign(sun.shadow.camera, { left: -SH, right: SH, top: SH, bottom: -SH, near: 10, far: 900 });
  sun.shadow.bias = -0.0002;
  sun.shadow.normalBias = 0.05;
  // where the sun stands (shadows.js moves it along with the shadow frustum; phones, which draw no shadow maps, had
  // three's default overhead light: the ground got all of the sun and no wall any)
  sun.position.copy(sunDir).multiplyScalar(420);
  scene.add(sun, sun.target);
  // static casters cached, only people and cars redrawn each frame (src/shadows.js)
  const shadows = new SunShadows(renderer, scene, sun, sunDir);
  // The hemisphere light is the light the sunlit paving and lawns throw back: walls facing away from the sun (the
  // fronts of 학생회관, 대강당 and 백주년기념관 on 백양로 face west, the sun is in the south-east) stay a light grey as
  // in the photos instead of a dark blue-grey, and soffits and porch ceilings see the ground. Its sky side is back to
  // a faint fill (the sky itself is the environment's): shade on the ground keeps only the sky's light, as dark as in
  // the photos. A wall (half sky side, half ground side) gets what it got before.
  const hemiSky = new THREE.Color(0xcfe0ff).multiplyScalar(0.35);
  const hemiGround = new THREE.Color(0xcfe0ff).add(new THREE.Color(0xc4b090)).multiplyScalar(1.25).sub(hemiSky);
  scene.add(new THREE.HemisphereLight(hemiSky, hemiGround, 1));

  setupAtmosphere(sunDir);        // cloud shadows and the fog's sun side
  const sky = makeSky(skyMeta);
  sky.material.uniforms.uExposure.value = 1.25;
  scene.add(sky);

  // ---------------------------------------------------------------- terrain
  const T = campus.terrain;
  const hfNear = new Heightfield(nearData, T.near.half, T.near.step, T.near.n);
  if (T.south && southData) hfNear.setPatch(southData, T.south);
  lib.setTerrain(hfNear);
  const hfFar = new Heightfield(farData, T.far.half, T.far.step, T.far.n);
  // the campus's static sun shadow baked into one texture (src/bakedshadow.js): the phones' only sun shadow, the
  // desktop's beyond the shadow map; on the terrain here, on every other lit material once the scene is built.
  // Phones also take the halls' and landmarks' own baked shadow on their walls and roofs (blender/bake.py).
  const sunMap = new SunMap(hfNear, { walls: !renderer.shadowMap.enabled }).load();
  const terrain = makeNearTerrain(hfNear, campus, lib);
  sunMap.patch(terrain.material, 0);
  scene.add(terrain);
  const terrainSouth = hfNear.ext ? makeSouthTerrain(hfNear, terrain.material) : null;   // (신촌 로터리)
  if (terrainSouth) scene.add(terrainSouth);
  const grass = new Grass(renderer, scene, lib, hfNear, campus, sun);     // blades on the lawn round the camera
  const fall = new Fall(renderer, scene, lib, hfNear, campus, sunMap);   // petals / leaves coming down round it
  scene.add(makeFarTerrain(hfFar, T.near.half, hfNear.ext && T.south));
  scene.add(makeCity(hfFar, T.near.half, 1600, hfNear.ext && T.south));
  // the kits placed for good, the forest and the far hills' trees, drawn only where in view (world.js); whole into
  // the shadow cache
  const kitCull = new KitCuller();
  shadows.wholeSets = (on) => kitCull.shadowPass(on);
  const farForest = makeFarForest(hfFar, T.near.half, 3800, hfNear.ext && T.south);
  kitCull.add([farForest]);
  scene.add(farForest);
  scene.add(makeSummitTower(hfFar));
  progress('백양로를 까는 중…', 20);

  // ---------------------------------------------------------------- GLB assets
  const load = async (u, label, weight) => { const g = await loadGLB(MODELS + u); progress(label, weight); return g; };
  const [bld, lms, road, townG] = await Promise.all([
    load('campus_buildings.glb', '건물을 세우는 중…', 115),
    load('campus_landmarks.glb', '언더우드관에 담쟁이를 심는 중…', 115),
    load('baekyangro.glb', '백양로에 차선을 긋는 중…', 115),
    load('campus_town.glb', '굴다리 너머 신촌에 불을 켜는 중…', 20).catch(() => null),      // 정문 밖 (src/town.js)
  ]);
  bindMaterials(bld.scene, lib, false, true);
  bindMaterials(lms.scene, lib, false, true);
  drapeTerrain(lms.scene, terrain.material);          // 대강당 앞 둑: the ground's own material (src/terrain.js)
  bindMaterials(road.scene, lib);
  const verge = new Verge(road.scene, campus);        // 백양로's verge and planting strip: lawn (src/verge.js)
  // 정문 밖: 성산로, the railway's bank and the town beyond; the banks' trees stand on the banks' own meshes
  const townBanks = townG && campus.town ? addTown(scene, townG, lib, terrain.material) : [];
  grass.verge = verge;

  // walkable surfaces: terrain + road + amphitheater terraces
  const walkables = [terrain];
  const amph = [];
  lms.scene.traverse((o) => { if (o.isMesh && /amphitheater/.test((o.parent && o.parent.name) + o.name)) amph.push(o); });
  // the smoothed surface of every entrance flight (blender/landmarks.py walk_mesh): invisible, only walked on
  const stairWalk = [];
  lms.scene.updateMatrixWorld(true);
  bld.scene.updateMatrixWorld(true);
  for (const sc of [lms.scene, bld.scene]) {     // (the procedural halls' front steps are in the buildings file)
    sc.traverse((o) => { if (o.isMesh && /walk_stairs/.test(o.name + ((o.parent && o.parent.name) || ''))) stairWalk.push(o); });
  }
  for (const o of stairWalk) { o.material = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }); o.removeFromParent(); }
  const roadMeshes = [];
  road.scene.traverse((o) => { if (o.isMesh) { o.receiveShadow = true; roadMeshes.push(o); } });
  scene.add(road.scene);
  road.scene.updateMatrixWorld(true);
  for (const m of [...roadMeshes, ...amph, ...stairWalk, ...townBanks]) walkables.push(m);
  if (terrainSouth) walkables.push(terrainSouth);
  for (const m of walkables) m.geometry.computeBoundsTree();

  const amphGroup = new THREE.Group();
  for (const m of amph) {
    const w = m.matrixWorld.clone();
    m.parent.remove(m);
    m.matrix.copy(w); m.matrix.decompose(m.position, m.quaternion, m.scale);
    m.castShadow = m.receiveShadow = true;
    amphGroup.add(m);
  }
  scene.add(amphGroup);
  scene.add(mergeStatic(bld.scene, { name: 'buildings' }));
  scene.add(mergeStatic(lms.scene, { name: 'landmarks' }));
  // 활천 water: Ultra Water FFT ripples, caustics and the jet's rings (src/water/fountain.js)
  const fountainWater = campus.statues.fountain ? new FountainWater(renderer, scene, campus.statues.fountain, lib, sun, sunDir, { mobile: MOBILE }) : null;
  progress('건물을 정리하는 중…', 70);

  const ray = new THREE.Raycaster();
  ray.firstHitOnly = true;
  const DOWN = new THREE.Vector3(0, -1, 0), from = new THREE.Vector3();
  const groundAt = (x, y) => {
    ray.set(from.set(x, 600, -y), DOWN);
    const h = ray.intersectObjects(walkables, false);
    return h.length ? h[0].point.y : hfNear.height(x, y);
  };

  // ---------------------------------------------------------------- vegetation
  // trees, shrubs and props parsed (and their textures asked for) together, the cast alongside (placed further down)
  const cast = new Cast();                  // Quaternius CC0 people (blender/characters.py)
  const castLoaded = cast.load(Object.keys(PEOPLE), () => progress('사람들이 모여드는 중…'));
  const kits = {};
  const species = [...new Set(campus.trees.map((t) => t[0]))];      // ginkgo, zelkova, …, zelkova_young, metasequoia
  clearEntrances(campus.shrubs, entrances.entrances || []);
  const shrubScenes = {};
  const shrubCounts = countBy(campus.shrubs, (s) => s[0]);
  const P = {};
  await Promise.all([
    ...species.flatMap((sp) => [0, 1].map(async (v) => {
      const g = await load(treeFile(sp, v), '나무를 심는 중…');
      bindMaterials(g.scene, lib);
      kits[`${sp}_${v}`] = g.scene;
    })),
    ...Object.keys(shrubCounts).flatMap((k) => [k, k + '_far']).map(async (k) => {
      const g = await load(shrubFile(k), '회양목을 다듬는 중…');
      bindMaterials(g.scene, lib);
      shrubScenes[k] = g.scene;
    }),
    ...PROPS.map(async (n) => {
      const g = await load(`props/${n}.glb`, '공중전화를 놓는 중…');
      bindMaterials(g.scene, lib, true);
      P[n] = g;
    }),
  ]);
  await texturesReady(Object.values(kits));     // the impostors are drawn from the tree models: their leaves and bark
  const forest = new Forest(scene, renderer, lib, kits, campus.trees, groundAt, kitCull);
  // (and their lighter models farther than SHRUB_FAR from the camera)
  const shrubKits = {};
  for (const k in shrubCounts) for (const f of [k, k + '_far']) shrubKits[f] = new InstancedKit(shrubScenes[f], lib, shrubCounts[k]);
  const m4 = new THREE.Matrix4();
  for (const [k, x, y, sc, rot] of campus.shrubs) {
    placeMatrix(m4, x, groundAt(x, y) - 0.05, y, rot, sc);
    shrubKits[k].add(m4);
    shrubKits[k + '_far'].add(m4);
  }
  for (const k in shrubKits) { shrubKits[k].commit(); shrubKits[k].addTo(scene); }
  for (const k in shrubCounts) kitCull.add(shrubKits[k].parts, { far: shrubKits[k + '_far'].parts, dist: SHRUB_FAR });

  // ---------------------------------------------------------------- props
  progress('가로등과 벤치를 놓는 중…', 16);
  const colliders = new Colliders();
  for (const b of campus.buildings) colliders.addPolygon(b.style === 'lm:hanok' ? hanokWalls(b.footprint) : b.footprint);
  for (const poly of campus.colliders || []) colliders.addPolygon(poly);     // parts outside the OSM outlines (백주년기념관's front block)
  {
    const byKind = {};
    for (const pr of campus.props) (byKind[pr[0]] ||= []).push(pr);
    const rnd = mulberry(5);
    const COLLIDE = { lamp_double: 0.25, lamp_quad: 0.25, lamp_arm: 0.25, flag_white: 0.12, planter: 0.5, stone_marker: 1.0, sign_board: 0.9, payphone: 0.62, guard_booth: 1.05,
      bollard: 0.12, tent_kiosk: 1.5, notice_board: 0.7, haetae: 0.95, parking_booth: 1.3, recycle_bin: 0.7 };
    for (const [kind, list] of Object.entries(byKind)) {
      const src = P[kind];
      if (!src) continue;
      const kit = new InstancedKit(src.scene, lib, list.length, { colors: true });
      for (const [, x, y, rot] of list) {
        // Blender models face -Y; campus rotation is the heading in the campus frame
        const col = kind === 'motorbike' ? new THREE.Color().setHSL(rnd(), 0.5, 0.45) : null;
        kit.add(placeMatrix(m4, x, groundAt(x, y), y, rot + (kind === 'motorbike' ? 0 : Math.PI / 2)), col);
        // a bench (1.8 m by 0.62, facing rot): three circles along its length
        if (kind === 'bench') for (const t of [-0.55, 0, 0.55]) colliders.addCircle(x - Math.sin(rot) * t, y + Math.cos(rot) * t, 0.38);
        else if (kind !== 'motorbike') colliders.addCircle(x, y, COLLIDE[kind] ?? 0.55);
      }
      kit.commit();
      kit.addTo(scene);
      kitCull.add(kit.parts);
    }
    // parked cars
    const carKits = {};
    const PARKED_COLORS = [...CAR_COLORS, '#8c8f94'];
    const MODEL = (k, i) => (k === 'sedan' ? ['sedan', 'sedan2', 'sedan', 'van'][i % 4] : k === 'hatch' ? ['hatch', 'tico'][i % 2] : k);
    const carCount = countBy(campus.cars, (c, i) => MODEL(c[0], i));
    // (and their lighter models, blender/build.py car_*_far: farther than CAR_FAR from the camera)
    const farKits = {};
    for (const [k, n] of Object.entries(carCount)) {
      carKits[k] = new InstancedKit(P['car_' + k].scene, lib, n, { colors: true });
      farKits[k] = new InstancedKit(P[`car_${k}_far`].scene, lib, n, { colors: true });
    }
    // each car stands on its four tyres: where they meet the ground (model frame, +X forward, three -Z left) ...
    const tyres = {};
    const tyresOf = (k) => tyres[k] ||= (() => {
      const sc = P['car_' + k].scene, v = new THREE.Vector3(), xs = [], zs = [];
      sc.updateMatrixWorld(true);
      sc.traverse((o) => { if (/^wheel_/.test(o.name)) { o.getWorldPosition(v); xs.push(v.x); zs.push(v.z); } });
      return xs.length ? { f: Math.max(...xs), r: Math.min(...xs), l: Math.min(...zs), rt: Math.max(...zs) } : { f: 1.4, r: -1.4, l: -0.75, rt: 0.75 };
    })();
    // ... and leans with the slope under them (pitch about its own Z, roll about its own X), so that on a drive's
    // slope or a kerb no tyre sinks into the ground and none hangs over it
    const carEuler = new THREE.Euler(0, 0, 0, 'YZX'), carQ = new THREE.Quaternion(), carP = new THREE.Vector3(), ONE = new THREE.Vector3(1, 1, 1);
    const parkedMatrix = (k, x, y, ang) => {
      const t = tyresOf(k), c = Math.cos(ang), s = Math.sin(ang);
      const g = (lx, lz) => groundAt(x + lx * c + lz * s, y + lx * s - lz * c);      // model (x, z) -> campus
      const fl = g(t.f, t.l), fr = g(t.f, t.rt), rl = g(t.r, t.l), rr = g(t.r, t.rt);
      const pitch = Math.max(-0.3, Math.min(0.3, Math.atan2((fl + fr - rl - rr) / 2, t.f - t.r)));
      const roll = Math.max(-0.3, Math.min(0.3, Math.atan2((fl + rl - fr - rr) / 2, t.rt - t.l)));     // + : the left side up
      const mx = (t.f + t.r) / 2, mz = (t.l + t.rt) / 2;
      const h = (fl + fr + rl + rr) / 4 - mx * Math.tan(pitch) + mz * Math.tan(roll);     // the plane under the tyres at the origin
      carQ.setFromEuler(carEuler.set(roll, ang, pitch));
      return m4.compose(carP.set(x, h, -y), carQ, ONE);
    };
    campus.cars.forEach(([k0, x, y, ang, ci], i) => {
      const k = MODEL(k0, i);
      const col = new THREE.Color(k === 'taxi' ? '#ecebe4' : PARKED_COLORS[(ci * 7 + i) % PARKED_COLORS.length]);
      parkedMatrix(k, x, y, ang);
      carKits[k].add(m4, col);
      farKits[k].add(m4, col);
      colliders.addCircle(x + Math.cos(ang) * 1.2, y + Math.sin(ang) * 1.2, 1.0);
      colliders.addCircle(x - Math.cos(ang) * 1.2, y - Math.sin(ang) * 1.2, 1.0);
    });
    for (const k in carKits) {
      for (const kit of [carKits[k], farKits[k]]) { kit.commit(); kit.addTo(scene); }
      kitCull.add(carKits[k].parts, { far: farKits[k].parts, dist: CAR_FAR });
    }
  }
  for (const t of campus.trees) colliders.addCircle(t[1], t[2], 0.35 * t[3]);
  // clipped shrubs: round boxwood, cones, bushes and azaleas are as wide as a person; low hedges are three overlapping circles
  for (const [k, x, y, sc, rot] of campus.shrubs) {
    if (k === 'hedge_low') {
      const c = Math.cos(rot), s = Math.sin(rot);
      colliders.addCircle(x, y, 0.42 * sc);
      colliders.addCircle(x + c * 0.55 * sc, y + s * 0.55 * sc, 0.42 * sc);
      colliders.addCircle(x - c * 0.55 * sc, y - s * 0.55 * sc, 0.42 * sc);
    } else colliders.addCircle(x, y, (k === 'topiary_cone' ? 0.6 : k === 'azalea_red' ? 0.62 : 0.72) * sc);
  }
  const S = campus.statues;
  colliders.addCircle(S.eagle.pos[0], S.eagle.pos[1], S.eagle.r ?? 4.2);       // the eagle's round dais (its brick ring is walked on)
  for (const [b, r] of S.eagle.groups ?? []) {   // the four groups on the dais' edge, their wedges out on the ring
    const a = b * Math.PI / 180;
    colliders.addCircle(S.eagle.pos[0] + r * Math.sin(a), S.eagle.pos[1] + r * Math.cos(a), 0.6);
  }
  colliders.addCircle(S.underwood_statue.pos[0], S.underwood_statue.pos[1], 2.1);   // the rock-faced octagon (the round slab is walked on)
  if (S.fountain) colliders.addCircle(S.fountain.pos[0], S.fountain.pos[1], S.fountain.rim);   // 활천 basin's stone wall
  if (S.court) {                                                                     // the two hoop posts of the 대강당 court
    for (const sg of [-1, 1]) {
      const d = sg * (S.court.L / 2 + 1.0);
      colliders.addCircle(S.court.pos[0] + Math.cos(S.court.rot) * d, S.court.pos[1] + Math.sin(S.court.rot) * d, 0.3);
    }
  }
  const banners = makeBanners(campus.banners, lib);
  flagWind(lib);                    // the white flag's cloth stirs in the wind too (src/flags.js)
  scene.add(banners);
  scene.add(makeBoard(campus.landmarks.find((l) => l.id === 'events'), groundAt));
  const decals = new Decals(scene, campus.decals || [], walkables, hfNear, sunMap);   // manholes, oil, patches (src/decals.js)
  const curbs = new Curbs(scene, campus.curbs || [], hfNear, walkables.slice(1), lib,     // kerbs along the paving (src/curbs.js)
    { lawn: campus.curb_lawn, ground: terrain.material });
  await castLoaded;

  // ---------------------------------------------------------------- life
  progress('학생들이 등교하는 중…', 40);
  const R = campus.baekyangro;
  const center = new Path(R.pts, groundAt);
  const eWalk = R.median + R.lane + R.curb + (R.verge || 0);      // inner edge of the sidewalk
  const paths = [];
  for (const off of [eWalk + R.walk * 0.4, eWalk + R.walk * 0.68, -(eWalk + R.walk * 0.4), -(eWalk + R.walk * 0.68)]) paths.push(new Path(center.offset(off), groundAt));
  for (const p of campus.paths) {
    if (p.kind !== 'footway' || p.pts.length < 2) continue;
    if (polylineLength(p.pts) > 45 && Math.abs(p.pts[0][0]) < 260 && p.pts[0][1] > -380 && p.pts[0][1] < 420 && paths.length < 26) paths.push(new Path(p.pts, groundAt));
  }
  const groups = [[-40, -45], [-36, -70], [3, -58], [-2, -92], [-96, -400], [58, 200], [-46, -26], [12, -30], [-20, 30], [110, 150], [-88, -186]]
    .map(([x, y]) => [x, y, groundAt(x, y)]);
  // people on the benches (about half of them taken, one to three to a bench; a third of that on phones) and the
  // queue at 학생회관's phone booths: one on the phone in two of the three, two more waiting behind the middle one
  const seats = [], lines = [];
  {
    const rnd = mulberry(41);
    const SLOTS = [[], [[0], [-0.45], [0.45]], [[-0.42, 0.42], [-0.55, 0.02], [-0.02, 0.55]], [[-0.6, 0, 0.6]]];
    for (const [kind, x, y, rot] of campus.props) {
      if (kind !== 'bench') continue;
      const r = rnd(), pick = rnd(), jit = rnd();
      const n = MOBILE ? (r < 0.82 ? 0 : r < 0.94 ? 1 : 2) : r < 0.48 ? 0 : r < 0.72 ? 1 : r < 0.92 ? 2 : 3;
      if (!n) continue;
      // the bench faces (cos rot, sin rot), its length runs along (-sin rot, cos rot); the seat's top is 0.43 m up
      const slots = SLOTS[n][Math.floor(pick * SLOTS[n].length)], h = groundAt(x, y) + 0.43;
      const fx = Math.cos(rot), fy = Math.sin(rot);
      seats.push(slots.map((t, k) => ({ x: x - fy * t + fx * 0.03, y: y + fx * t + fy * 0.03, h,
        heading: Math.atan2(fx, -fy) + (((jit * 7 + k * 0.37) % 1) - 0.5) * 0.22 })));
    }
    const booths = campus.props.filter((pr) => pr[0] === 'payphone');
    booths.forEach(([, x, y, rot], i) => {
      if (booths.length > 1 && i === booths.length - 1) return;        // (one booth free)
      const fx = Math.cos(rot), fy = Math.sin(rot), heading = Math.atan2(-fx, fy);
      const at = (d, side = 0) => { const px = x + fx * d - fy * side, py = y + fy * d + fx * side; return { x: px, y: py, h: groundAt(px, py), heading }; };
      lines.push(i === Math.floor((booths.length - 1) / 2) && !MOBILE ? [at(0.85), at(1.95, 0.1), at(2.8, -0.12)] : [at(0.85)]);
    });
  }
  const crowd = new Crowd(scene, cast, [...STUDENTS, ...STUDENTS, 'man-professor', 'man-staff', 'woman-staff'], paths, groups, MOBILE ? 40 : 110, 3, { seats, lines });
  for (const p of crowd.people) shadows.addDynamic(p.a.holder);
  // small talk over their heads; what they say follows the month (crowd.season)
  crowd.season = season;
  crowd.bubbles = new Bubbles($('#bubbles'), camera);
  // 연세로's two sidewalks to 신촌 로터리 (campus.json town.walks): a crowd of their own, its own random stream
  const townCrowd = campus.town?.walks ? new Crowd(scene, cast, [...STUDENTS, ...STUDENTS, 'man-staff', 'woman-staff'],
    campus.town.walks.map((w) => new Path(w, groundAt)), [], MOBILE ? 10 : 30, 11) : null;
  if (townCrowd) {
    for (const p of townCrowd.people) shadows.addDynamic(p.a.holder);
    townCrowd.season = season;
    townCrowd.bubbles = crowd.bubbles;
  }
  const lanes = [];
  // one lane each way on the 1997 two-lane road (right-hand traffic); both bend out 0.5 m round the guard booth's
  // island on the centre line (tools/build_campus.py BOOTH: 1.7 m across), the mirrors 0.3 - 0.4 m clear of its kerb
  // and inside the carriageway's
  const bo = R.booth;
  const roundBooth = (s) => {
    if (!bo) return 0;
    const a = bo.s - bo.island[3] - 1.2, b = bo.s - bo.island[2] + 1.0;         // the island, nose to tail (+ margin)
    const t = s < a ? 1 - (a - s) / 12 : s > b ? 1 - (s - b) / 12 : 1;
    const u = Math.min(1, Math.max(0, t));
    return u * u * (3 - 2 * u);
  };
  for (const off of [R.median + R.lane * 0.5]) {
    lanes.push(new Path(center.offset((s) => -(off + 0.5 * roundBooth(s))), groundAt));            // northbound
    lanes.push(new Path(center.offset((s) => off + 0.5 * roundBooth(s)).reverse(), groundAt));    // southbound
  }
  const traffic = new Traffic(scene, { sedan: P.car_sedan, sedan2: P.car_sedan2, hatch: P.car_hatch, tico: P.car_tico, taxi: P.car_taxi, van: P.car_van }, lanes, 14, cast, STUDENTS.concat(['man-professor', 'man-staff', 'woman-staff']));
  for (const c of traffic.cars) shadows.addDynamic(c.root, c.len / 2 + 1.5);
  const gates = new BoothGates(scene, P.barrier_arm, R.booth, lanes, groundAt, shadows);
  // 성산로's cars and city buses (src/town.js); the sound hears them with 백양로's
  const street = campus.town && townG ? new Street(scene, campus.town, P, groundAt, { shadows }) : null;
  const heard = { cars: street ? traffic.cars.concat(street.cars) : traffic.cars };

  // ---------------------------------------------------------------- player / UI / post
  progress('가방을 메는 중…', 36);
  let heroId = safeGet('y97-hero');
  if (!HEROES.includes(heroId)) heroId = HEROES[0];
  const hero = cast.make(heroId);
  scene.add(hero.holder);
  shadows.addDynamic(hero.holder);
  const player = new Player(camera, canvas, colliders, walkables, hfNear, hero);
  grass.lift = player.lift = (x, y) => curbs.lift(x, y);     // the lawn raised along the kerbs
  for (const name of ['buildings', 'landmarks']) {      // walls for the walker: BVHs built once, shared with the bird's-eye roof picking
    scene.getObjectByName(name)?.traverse((o) => { if (o.isMesh) { if (!o.geometry.boundsTree) o.geometry.computeBoundsTree(); player.walls.push(o); } });
  }
  player.teleport(campus.spawn.pos[0], campus.spawn.pos[1], campus.spawn.yaw);
  const post = new Post(renderer, scene, camera);
  const ui = new UI(campus, {
    onTeleport: (x, y) => { if (bird.active) leaveBird(); player.teleport(x, y); forest.update(camera.position, true); resume(); },
    onClose: () => resume(),
  });
  const ball = S.court ? new Basketball({ scene, player, ui, court: S.court, hf: hfNear, mobile: MOBILE }) : null;   // 대강당 앞 농구장
  // hero picker on the title card (portraits rendered from the real models)
  const pics = portraits(cast, HEROES);
  const pickEl = $('#hero-pick');
  const pickHero = (id) => {
    heroId = id;
    safeSet('y97-hero', id);
    pickEl.querySelectorAll('button').forEach((b) => b.classList.toggle('on', b.dataset.id === id));
    if (player.actor.id !== id) { const a = cast.make(id); scene.add(a.holder); shadows.addDynamic(a.holder); player.setActor(a); }
  };
  for (const id of HEROES) {
    const b = document.createElement('button');
    b.dataset.id = id;
    b.innerHTML = `<img src="${pics[id]}" alt=""><span>${PEOPLE[id]}</span>`;
    b.addEventListener('click', () => pickHero(id));
    pickEl.appendChild(b);
  }
  pickHero(heroId);
  // ---------------------------------------------------------------- baked sun shadows, blob shadows
  progress('그림자를 드리우는 중…', 42);
  const FAR_SCENERY = /^(sky|terrain_far|far_city|far_forest|ansan_tower)$/;
  const farScenery = (o) => { for (let p = o; p; p = p.parent) if (FAR_SCENERY.test(p.name)) return true; return false; };
  sunMap.patchScene(scene, farScenery);
  // phones: a soft dark patch under each person, moving car and the ball (src/blobs.js); the shadow map has them here
  const blobs = renderer.shadowMap.enabled ? null : new Blobs(scene, hfNear, sunMap);
  if (blobs) {
    for (const p of crowd.people) blobs.addPerson(p.a);
    for (const p of townCrowd?.people ?? []) blobs.addPerson(p.a);
    for (const c of heard.cars) blobs.addCar(c);
    blobs.hero = () => player.actor;
    blobs.ball = ball;
  }
  // 활천대 앞 생일 축하: two students on the flagstones; you and the friend throw the birthday one in (src/birthday.js)
  const birthday = S.fountain ? new Birthday({ scene, cast, player, F: S.fountain, water: fountainWater, bubbles: crowd.bubbles, ui, shadows, blobs, mobile: MOBILE }) : null;
  // where to start walking (title card): 정문, the memory spots, then every named building at its front door
  const places = startPlaces(campus, entrances.entrances || [], (x, y, r) => colliders.resolve(x, y, r));
  const placeEl = $('#place-pick');
  for (const group of ['추억 장소', '건물']) {
    const og = Object.assign(document.createElement('optgroup'), { label: group });
    places.forEach((p, i) => { if (p.group === group) og.appendChild(new Option(p.name, i)); });
    placeEl.appendChild(og);
  }

  const setSeason = (v) => {
    season = v;
    crowd.season = v;
    if (townCrowd) townCrowd.season = v;
    safeSet('y97-season', v);
    lib.setSeason(v);
    fall.setSeason(v);
    banners.userData.setSeason(v);
    seasonButtons(v);
    $('#datestamp').textContent = SEASONS[v].date;
    bird.labels({ seasonLabel: SEASONS[v].short });
    // impostor textures and the cached tree shadows come from the leaf textures -> refresh after they load
    shadows.invalidate();
    texturesReady().then(() => { forest.renderImpostors(renderer); shadows.invalidate(); });
    ui.toast(SEASONS[v].label);
  };
  $('#datestamp').textContent = SEASONS[season].date;
  document.querySelectorAll('[data-season]').forEach((b) => b.addEventListener('click', (e) => { e.stopPropagation(); setSeason(b.dataset.season); }));

  // ---------------------------------------------------------------- input / states
  let started = false, paused = false;
  const resume = () => {
    if (!started || ui.memoryOpen || ui.mapOpen) return;
    if (bird.active) { paused = false; $('#pause').hidden = true; return; }   // keep the walker parked
    paused = false;
    $('#pause').hidden = true;
    player.enabled = true;
  };
  const pause = () => {
    if (!started || ui.memoryOpen || ui.mapOpen) return;
    paused = true;
    player.enabled = false;
    $('#pause').hidden = false;
  };
  const startWalk = (where = null) => {
    if (started) return;
    started = true;
    $('#intro').hidden = true;
    $('#hud').hidden = false;
    if (MOBILE) $('#touch').hidden = false;
    resume();
    const how = MOBILE ? '화면 왼쪽을 누른 채 밀어서 걸어요' : '↑↓(W·S)로 걷고 ←→(A·D)로 방향을 바꿔요';
    ui.toast(`${how} · ${where ? `${where}에서 출발해요` : '정문에서 백양로를 따라 걸어 보세요'}`, 5000);
  };
  $('#start').addEventListener('click', () => {
    const p = places[placeEl.value];         // '' → 정문 (the walker already stands at the spawn)
    if (p) { player.teleport(p.x, p.y, p.yaw); forest.update(camera.position, true); }
    startWalk(p ? (p.front ? `${p.name} 앞` : p.name) : null);
  });
  $('#resume').addEventListener('click', resume);
  const setFilm = (v) => { $('#opt-film').checked = v; post.setFilm(v); document.body.classList.toggle('film', v); bird.labels({ filmOn: v }); };
  const toggleFilm = () => setFilm(!$('#opt-film').checked);
  $('#opt-film').addEventListener('change', (e) => setFilm(e.target.checked));
  $('#opt-hq').addEventListener('change', (e) => { post.setHQ(e.target.checked); sun.shadow.mapSize.set(e.target.checked ? 4096 : 2048, e.target.checked ? 4096 : 2048); sun.shadow.map?.dispose(); sun.shadow.map = null; shadows.invalidate(); });
  // first person (src/player.js): V, the HUD button, the wheel or a pinch on past the closest view; remembered
  player.onView = (first) => {
    safeSet('y97-view', first ? 'first' : 'third');
    $('#viewbtn span').textContent = first ? '3인칭' : '1인칭';
    if (started) ui.toast(first ? '1인칭 시점' : '3인칭 시점');
  };
  player.setFpv(safeGet('y97-view') === 'first');
  const openNearby = () => {
    if (ui.memoryOpen) { ui.closeMemory(); return; }
    if (ball && !bird.active && ball.action()) { ui.setPrompt(ball.prompt()); return; }
    if (birthday && !bird.active && birthday.action()) { ui.setPrompt(null); return; }
    const l = ui.nearestLandmark(player.x, player.y);
    if (l) { player.enabled = false; ui.openMemory(l); }
  };
  const toggleMap = () => {
    if (!started) return;
    if (ui.mapOpen) { ui.toggleMap(false); return; }
    player.enabled = false;
    ui.toggleMap(true, player.x, player.y);
  };

  // ---------------------------------------------------------------- 캠퍼스 둘러보기 (bird's-eye tour, blender-free: src/birdseye.js)
  const pickRay = new THREE.Raycaster();
  pickRay.firstHitOnly = true;
  const downRay = new THREE.Raycaster();
  downRay.firstHitOnly = true;
  const roofs = [...walkables, ...player.walls];     // ground and the building / landmark meshes (BVHs built above)
  const surfaceAt = (x, y) => {
    downRay.set(from.set(x, 900, -y), DOWN);
    const h = downRay.intersectObjects(roofs, false)[0];
    return h ? h.point.y : -1e9;
  };
  const birds = new Birds(scene, { groundAt, surfaceAt, colliders, forest, sunMap, mobile: MOBILE });   // 까치 · 비둘기 (src/birds.js)
  // sound (src/audio.js): synthesized, started by the first click of the title card
  const sound = new Sound({ camera, campus, hf: hfNear });
  birds.onTakeOff = (b) => sound.flap(b.x, b.h + 0.3, -b.y);
  if (ball) ball.onSound = (what, p, k) => sound.ball(what, p, k);
  if (birthday) birthday.onSplash = (p) => sound.splash(p);
  $('#opt-sound').checked = sound.on;
  $('#opt-sound').addEventListener('change', (e) => sound.setOn(e.target.checked));
  for (const id of ['#start', '#tour-start']) $(id).addEventListener('click', () => sound.start());
  const SEASON_ORDER = ['spring', 'summer', 'autumn'];
  const SEASON_KEYS = { Digit1: 'spring', Digit2: 'summer', Digit3: 'autumn' };
  const bird = new BirdsEye({
    camera, dom: canvas, landmarks: campus.landmarks, markers: campus.markers || [],
    heightAt: (x, y) => hfNear.height(x, y),
    surfaceAt,
    pickGround: (nx, ny) => {
      pickRay.setFromCamera(new THREE.Vector2(nx, ny), camera);
      const h = pickRay.intersectObjects(walkables, false)[0];
      return h ? [h.point.x, -h.point.z] : null;
    },
    onWalkHere: (x, y) => {
      [x, y] = colliders.resolve(x, y, 0.6);        // a building's tag sits inside its footprint: step out to the wall
      const fromTitle = !started;
      leaveBird();
      if (fromTitle) startWalk(ui.placeName(x, y, false));
      player.teleport(x, y);
      player.cam.ready = false;
      forest.update(camera.position, true);
    },
    onMemory: (l) => { player.enabled = false; ui.openMemory(l); },
    onAction: (what) => {
      if (what === 'back') leaveBird();
      else if (what === 'film') toggleFilm();
      else if (what === 'season') setSeason(SEASON_ORDER[(SEASON_ORDER.indexOf(season) + 1) % 3]);
    },
  });
  const enterBird = () => {
    if (bird.active) return;
    if (ui.memoryOpen) ui.closeMemory();
    if (ui.mapOpen) ui.toggleMap(false);
    paused = false;
    $('#pause').hidden = true;
    player.enabled = false;
    touch.reset();
    bird.labels({ seasonLabel: SEASONS[season].short, filmOn: $('#opt-film').checked });
    if (started) {
      const d = camera.getWorldDirection(new THREE.Vector3());
      bird.enter({ x: player.x, y: player.y, yaw: Math.atan2(d.x, -d.z), player: { x: player.x, y: player.y } });
    } else {
      $('#intro').hidden = true;
      $('#hud').hidden = false;
      bird.enter({ player: null });
    }
    ui.setPrompt(null);
    ui.toast(MOBILE ? '캠퍼스 위로 날아가기 · 한 손가락으로 밀고 두 손가락으로 확대·회전, 이름표를 누르면 그곳으로 가요'
      : '캠퍼스 위로 날아가기 · 방향키(WASD)로 날고 이름표를 누르면 그곳으로 가요', 4000);
  };
  const leaveBird = () => {
    if (!bird.active) return;
    if (ui.memoryOpen) ui.closeMemory();
    bird.exit();
    forest.nearDist = 230;
    if (started) {
      // swoop back down behind the walker from where the tour camera is now
      player.cam.pos.copy(camera.position);
      player.cam.look.copy(bird.focus);
      player.cam.ready = true;
      player.enabled = true;
      lastPlace = -1;
    } else {
      $('#hud').hidden = true;
      $('#intro').hidden = false;
    }
    forest.update(camera.position, true);
  };
  const toggleBird = () => (bird.active ? leaveBird() : enterBird());
  $('#birdbtn').addEventListener('click', (e) => { e.stopPropagation(); toggleBird(); e.currentTarget.blur(); });
  $('#tour-start').addEventListener('click', enterBird);

  addEventListener('keydown', (e) => {
    if (bird.active) {
      // the tour's own keys live in birdseye.js; here only leaving it and the game-wide season keys
      if (ui.memoryOpen) { if (e.code === 'Escape' || e.code === 'Enter') ui.closeMemory(); return; }
      if (e.code === 'KeyB' || e.code === 'Escape') leaveBird();
      else if (SEASON_KEYS[e.code]) setSeason(SEASON_KEYS[e.code]);
      return;
    }
    if (!started) return;
    if (e.code === 'KeyB' && !ui.memoryOpen) { enterBird(); return; }
    if (e.code === 'KeyE' || e.code === 'Enter') openNearby();
    else if (e.code === 'Space' && ball?.held && !bird.active && player.enabled) ball.action();
    else if (e.code === 'KeyM') toggleMap();
    else if (e.code === 'KeyF') toggleFilm();
    else if (e.code === 'KeyV' && !e.repeat) player.setFpv(!player.fpv);
    else if (SEASON_KEYS[e.code]) setSeason(SEASON_KEYS[e.code]);
    else if (e.code === 'Escape') {
      if (ui.memoryOpen) ui.closeMemory();
      else if (ui.mapOpen) ui.toggleMap(false);
      else if (paused) resume(); else pause();
    }
  });
  const walkLabels = new WalkLabels(campus.markers || [], camera, $('#blabels'));
  // HUD buttons (the only way in on a phone: no keys there)
  const touch = new TouchControls(player, canvas, $('#stick'));
  const tap = (sel, fn) => $(sel).addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); fn(); });
  tap('#prompt', openNearby);
  tap('#minimap', toggleMap);
  tap('#mapbtn', toggleMap);
  tap('#menubtn', pause);
  tap('#viewbtn', () => player.setFpv(!player.fpv));

  addEventListener('resize', () => {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
    post.setSize(innerWidth, innerHeight);          // CSS pixels: EffectComposer applies the pixel ratio itself
  });

  // ---------------------------------------------------------------- atmosphere (materials.js ATMOS)
  // every material in the scene gets the drifting cloud shadows and the height fog: the library's (patched as they
  // are made) and the rest, made here and there (terrain, far hills, city, impostors, people, banners, the fountain)
  scene.traverse((o) => { for (const m of [].concat(o.material || [])) globalPatch(m); });
  verge.attach(terrain.material);          // (after these passes: its material replays the terrain's edits)
  const cloudK = ATMOS.uCloud.value.z;
  addEventListener('keydown', (e) => {        // C: cloud shadows off / on (no option for it in the settings card)
    if (e.code !== 'KeyC' || e.repeat || (!started && !bird.active) || ui.memoryOpen || /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
    const on = ATMOS.uCloud.value.z === 0;
    ATMOS.uCloud.value.z = on ? cloudK : 0;
    ui.toast(on ? '구름 그림자 켬' : '구름 그림자 끔');
  });

  // ---------------------------------------------------------------- loop
  const clock = new THREE.Clock();
  let tAcc = 0, lastPlace = 0;
  const onRoad = (x, y) => {
    // distance to 백양로 centre line
    let best = 1e9;
    for (let i = 1; i < R.pts.length; i++) {
      const [ax, ay] = R.pts[i - 1], [bx, by] = R.pts[i];
      best = Math.min(best, closestOnSegment(x, y, ax, ay, bx, by)[2]);
    }
    return best < eWalk + R.walk + 1;
  };
  let viewW = 0, viewH = 0;        // 0: size once on the first frame too
  let fixedDt = 0, recording = false;  // trailer recording: the loop is stepped by hand at a fixed frame time
  const frame = () => {
    // a window resized while the tab was in the background may never send 'resize': check every frame
    if (!recording && (innerWidth !== viewW || innerHeight !== viewH)) { viewW = innerWidth; viewH = innerHeight; dispatchEvent(new Event('resize')); }
    const dt = fixedDt || Math.min(0.05, clock.getDelta());
    tAcc += dt;
    if (started) {
      crowd.movers(player.x, player.y, player.movers);
      traffic.movers(player.x, player.y, player.movers);
      birthday?.movers(player.x, player.y, player.movers);
      player.update(dt);
    }
    let span = SH;
    if (bird.active) {
      bird.update(dt, player);
      // wider shadows and more full-detail trees the higher up the view is
      span = bird.cur.dist > 260 ? 340 : bird.cur.dist > 90 ? 220 : SH;
      forest.nearDist = bird.cur.dist > 150 ? 330 : 230;
    }
    // what the shadows, tree LOD and crowd culling centre on: the camera, or the ground point below a bird's-eye view
    const focus = bird.active ? bird.focus : camera.position;
    if (!started && !bird.active) {
      // slow cinematic drift along 백양로 behind the title card
      const s = (tAcc * 3.2) % (center.length - 60) + 20;
      const p = center.at(s), d = center.dir(s);
      camera.position.set(p.x - d.y * 4, center.h(s) + 9 + Math.sin(tAcc * 0.2) * 2, -(p.y + d.x * 4));
      camera.lookAt(p.x + d.x * 40, center.h(s + 40) + 6, -(p.y + d.y * 40));
    }
    sky.position.copy(camera.position);
    updateAtmosphere(dt);
    forest.update(focus);
    grass.update(camera.position, tAcc);
    fall.update(camera);
    crowd.update(dt, tAcc, started ? player : NOBODY, focus);
    townCrowd?.update(dt, tAcc, started ? player : NOBODY, focus);
    birthday?.update(dt, tAcc, started && !bird.active, focus);
    crowd.bubbles.update(tAcc, started && !bird.active);
    birds.update(dt, tAcc, started ? player : NOBODY, crowd.people, focus);
    traffic.update(dt, started ? player : NOBODY, focus);
    street?.update(dt, focus, started ? player : null);
    gates.update(dt, traffic);
    fountainWater?.update(dt, camera);
    lib.uniforms.uWindT.value = tAcc;     // the wind in the leaves, branches and banners (materials.js sway)
    ball?.update(dt, tAcc, started && !bird.active);
    blobs?.update(camera.position);
    sound.update(dt, tAcc, { player, walking: started && !bird.active, crowd, traffic: heard, birds, season });
    decals.update(camera.position);
    curbs.update(camera.position);
    // the shadow frustum follows the view in texel-snapped steps; people and cars are redrawn into it every frame
    shadows.update(focus, bird.active ? focus.y : camera.position.y - 10, span);
    kitCull.update(camera);
    updatePcss(sun, post.hq);    // contact-hardening shadows on the desktop HQ path only
    if (bird.active) {
      ui.drawMinimap(bird.cur.x, bird.cur.y, bird.mapYaw);
      if (tAcc - lastPlace > 0.25) {
        lastPlace = tAcc;
        ui.setPlace(`하늘에서 · ${ui.placeName(bird.cur.x, bird.cur.y, onRoad(bird.cur.x, bird.cur.y))}`);
      }
    } else if (started) {
      ui.drawMinimap(player.x, player.y, player.yaw);
      walkLabels.update(dt, player.x, player.y);
      if (!bird.active && tAcc - lastPlace > 0.25) {
        lastPlace = tAcc;
        const l = ui.nearestLandmark(player.x, player.y);
        ui.setPlace(ui.placeName(player.x, player.y, onRoad(player.x, player.y)));
        const bp = ball?.prompt() || birthday?.prompt();
        ui.setPrompt(bp ? bp : l && !ui.memoryOpen ? `${l.name} · ${MOBILE ? '눌러서 ' : ''}그때의 추억 보기` : null);
      }
      if (MOBILE) ui.clearWalker(player.screenBox(camera));     // the prompt button off the walker (phones)
    }
    post.draw(tAcc);
  };
  // The first frame's work done ahead while the page still answers: every texture in (each went up to the GPU as it
  // came, materials.js upload), the scene's shaders compiled for the target post.js draws the scene into (no tone
  // mapping there), in the background where the browser can (KHR_parallel_shader_compile). Held a desktop's first
  // frame for 3 s, after the start button had come on.
  progress('햇살을 고르는 중…', 8);
  await texturesReady();
  progress('필름을 끼우는 중…');
  const warm = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType });
  renderer.setRenderTarget(warm);
  const compiled = renderer.extensions.has('KHR_parallel_shader_compile') ? renderer.compileAsync(scene, camera) : renderer.compile(scene, camera);
  renderer.setRenderTarget(null);
  await compiled;
  progress('첫 장면을 그리는 중…', 20);
  loading.coast(MOBILE ? 6 : 2.5);
  warm.dispose();
  renderer.setAnimationLoop(frame);
  post.setSize(innerWidth, innerHeight);          // CSS pixels: EffectComposer applies the pixel ratio itself
  // offline trailer recording (used from the browser console / automation): fixed-size frames, stepped by hand
  const record = {
    start(w = 1920, h = 1080) {
      recording = true;
      renderer.setAnimationLoop(null);
      renderer.setPixelRatio(1);
      post.composer.setPixelRatio(1);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      post.setSize(w, h);
    },
    step(dt = 1 / 30) { fixedDt = dt; frame(); fixedDt = 0; },
    stop() {
      recording = false;
      renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
      post.composer.setPixelRatio(renderer.getPixelRatio());
      viewW = viewH = 0;
      clock.getDelta();
      renderer.setAnimationLoop(frame);
    },
  };
  window.__y97 = { scene, camera, player, renderer, forest, ui, lib, setSeason, crowd, townCrowd, cast, traffic, street, bird, toggleBird, shadows, fountainWater,
    startWalk, enterBird, leaveBird, record, ball, birthday, post, grass, sunMap, blobs, curbs, verge, sound, birds,
    // tools/bake_sun_shadows.mjs (desktop path: it draws with the shadow map; the page needs reloading afterwards)
    // (the kits whole for it: it draws them from above, tile by tile)
    bakeSunMap: async () => {
      kitCull.whole();
      kitCull.enabled = false;
      try {
        return await bakeSunMap({ renderer, scene, sun, sunDir, shadows, forest, hf: hfNear, walk: walkables, hide: [banners, ball?.mesh], skip: farScenery });
      } finally {
        kitCull.enabled = true;
      }
    },
    kitCull };
  window.__y97.atmos = ATMOS;
  window.__y97.loading = loading;

  // ready once the first frames are drawn (the shadow map's and the post passes' shaders are compiled there)
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  placeEl.disabled = false;
  loading.done('1997년, 백양로에 도착했습니다.');
  $('#start').disabled = false;
  $('#tour-start').disabled = false;
}

// 광혜원's OSM outline takes in its whole stone platform (기단) and more; the walker collides with the hall's walls
// (15 x 8.4 m, blender/landmarks.py hanok) instead, so the steps up onto the platform can be climbed
function hanokWalls(fp) {
  const [a, b, c] = fp;
  const e1 = [b[0] - a[0], b[1] - a[1]], e2 = [c[0] - b[0], c[1] - b[1]];
  const l1 = Math.hypot(...e1), l2 = Math.hypot(...e2);
  const [u, lu, v, lv] = l1 >= l2 ? [e1, l1, e2, l2] : [e2, l2, e1, l1];
  const cx = (a[0] + c[0]) / 2, cy = (a[1] + c[1]) / 2;
  return [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([i, j]) => [cx + u[0] / lu * i * 7.6 + v[0] / lv * j * 4.3, cy + u[1] / lu * i * 7.6 + v[1] / lv * j * 4.3]);
}

// The clipped shrubs round the building aprons are scattered on a ring (tools/build_campus.py), and some landed on the
// entrance steps (a round bush in the middle of the top of the 언더우드관 flight, right before the door).  Every flight's
// zone comes from blender/build.py (data/entrances.json: origin at the door, u along the facade, v out along the
// flight); a shrub on one steps aside along the facade, clear of the flight and its side walls, a hedge piece goes.
function clearEntrances(shrubs, zones) {
  const inZone = (z, x, y, r) => {
    const dx = x - z.o[0], dy = y - z.o[1];
    const u = dx * z.u[0] + dy * z.u[1], v = dx * z.v[0] + dy * z.v[1];
    return v >= -r && v <= z.len + r && Math.abs(u) <= z.hw + r ? u : null;
  };
  for (let i = shrubs.length - 1; i >= 0; i--) {
    const s = shrubs[i];
    const r = 0.72 * s[3];
    for (const z of zones) {
      if (s[0] === 'hedge_low') {           // the three circles of its collider (main.js below)
        const c = Math.cos(s[4]) * 0.55 * s[3], sn = Math.sin(s[4]) * 0.55 * s[3];
        if ([0, 1, -1].some((k) => inZone(z, s[1] + k * c, s[2] + k * sn, 0.42 * s[3]) !== null)) { shrubs.splice(i, 1); break; }
        continue;
      }
      const u = inZone(z, s[1], s[2], r);
      if (u === null) continue;
      const to = (u < 0 ? -1 : 1) * (z.hw + r + 0.25);
      s[1] = +(s[1] + (to - u) * z.u[0]).toFixed(2);
      s[2] = +(s[2] + (to - u) * z.u[1]).toFixed(2);
      break;
    }
  }
}

// 게시판 with the 1997 photos pinned up (the "그때 우리는" memory spot)
function makeBoard(l, groundAt) {
  const g = new THREE.Group();
  if (!l) return g;
  const W = 1600, H = 900;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const x = c.getContext('2d');
  x.fillStyle = '#6b5236'; x.fillRect(0, 0, W, H);
  x.fillStyle = '#c9a877'; x.fillRect(30, 30, W - 60, H - 60);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const photos = (l.photo || []).map((p) => 'assets/' + p);
  const posters = [['대동제', '#c0392b'], ['총학생회', '#1d3f9a'], ['동아리 신입회원 모집', '#2e7d32'], ['아카라카 응원 연습', '#1d3f9a']];
  let i = 0;
  const rnd = mulberry(11);
  posters.forEach(([t, col], k) => {
    x.save();
    x.translate(120 + k * 360, 120 + (k % 2) * 380);
    x.rotate((rnd() - 0.5) * 0.08);
    x.fillStyle = '#f7f3e6'; x.fillRect(0, 0, 300, 220);
    x.fillStyle = col; x.font = 'bold 44px "Do Hyeon", sans-serif'; x.fillText(t, 20, 70);
    x.fillStyle = '#333'; x.font = '24px "Noto Sans KR", sans-serif';
    x.fillText('1997. 5. 대강당 앞', 20, 120); x.fillText('많은 참여 바랍니다', 20, 160);
    x.restore();
  });
  photos.forEach((src) => {
    const img = new Image();
    img.onload = () => {
      const k = i++;
      x.save();
      x.translate(160 + (k % 3) * 470, 300 + Math.floor(k / 3) * 300 - (k % 2) * 160);
      x.rotate((rnd() - 0.5) * 0.12);
      x.fillStyle = '#fff'; x.fillRect(-10, -10, 400, 290);
      x.drawImage(img, 0, 0, 380, 250);
      x.fillStyle = '#d33'; x.beginPath(); x.arc(190, -2, 9, 0, 7); x.fill();
      x.restore();
      tex.needsUpdate = true;
    };
    img.src = versioned(src);
  });
  const mat = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.85 });
  const board = new THREE.Mesh(new THREE.BoxGeometry(4.0, 2.25, 0.12), [mat, mat, mat, mat, mat, new THREE.MeshStandardMaterial({ color: '#5a4a3a' })]);
  const h = groundAt(l.pos[0], l.pos[1]);
  board.position.set(l.pos[0], h + 1.85, -l.pos[1]);
  board.rotation.y = -Math.PI / 2 + 0.25;
  board.castShadow = true;
  g.add(board);
  const legGeo = new THREE.BoxGeometry(0.12, 3.0, 0.12), legMat = new THREE.MeshStandardMaterial({ color: '#4a3a2a' });
  for (const s of [-1.7, 1.7]) {
    const leg = new THREE.Mesh(legGeo, legMat);
    leg.position.set(s, -0.35, 0);
    board.add(leg);
  }
  const roof = new THREE.Mesh(new THREE.BoxGeometry(4.4, 0.12, 0.6), new THREE.MeshStandardMaterial({ color: '#2f4f3f' }));
  roof.position.set(0, 1.25, 0.15);
  board.add(roof);
  return g;
}

main().catch((e) => {
  console.error(e);
  loading.fail('불러오기 실패: ' + e.message);
});
