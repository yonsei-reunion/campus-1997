import '@fontsource/noto-sans-kr/400.css';
import '@fontsource/noto-sans-kr/700.css';
import '@fontsource/jua/400.css';
import '@fontsource/do-hyeon/400.css';
import * as THREE from 'three';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { MaterialLibrary, SEASONS, texturesReady, texCount, updatePcss, uploadEarly, upgradeTextures, texturesFull } from './materials.js';
import { loading, fetchCounted } from './loading.js';
import { ATMOS, globalPatch, setupAtmosphere, updateAtmosphere } from './materials.js';
import { Heightfield, makeNearTerrain, makeSouthTerrain, makeFarTerrain, makeFarForest, makeSummitTower, makeCity, makeSky, drapeHeight } from './terrain.js';
import { loadGLB, prefetch, glbMaterials, bindMaterials, InstancedKit, KitCuller, Forest } from './world.js';
import { chunkIndex, nearUrls, CampusChunks } from './chunks.js';
import { Grass } from './grass.js';
import { Fall } from './fall.js';
import { Player, Colliders, pointInPoly } from './player.js';
import { UI } from './ui.js';
import { Post } from './post.js';
import { Path, makeBanners, Crowd, Traffic, BoothGates, CAR_COLORS } from './life.js';
import { makeGatePosters } from './posters.js';
import { Cast, PEOPLE, STUDENTS, HEROES, HERO, heroScale, portraits, castFiles, play } from './characters.js';
import { BirdsEye } from './birdseye.js';
import { SunShadows } from './shadows.js';
import { TouchControls } from './touch.js';
import { setupNews } from './news.js';
import { WalkLabels } from './labels.js';
import { Bubbles } from './talk.js';
import { FountainWater } from './water/fountain.js';
import { Birthday } from './birthday.js';
import { startPlaces, NORTH } from './places.js';
import { SunMap, bakeSunMap } from './bakedshadow.js';
import { Blobs } from './blobs.js';
import { Birds } from './birds.js';
import { flagWind } from './flags.js';
import { Decals } from './decals.js';
import { Curbs } from './curbs.js';
import { Verge } from './verge.js';
import { Sound } from './audio.js';
import { addTown, Street } from './town.js';
import { $, MOBILE, versioned, safeGet, safeSet, copyButton, gameUrl, mulberry, countBy, polylineLength, closestOnSegment, placeMatrix } from './util.js';

const canvas = $('#view');
// ./?game=shoot: the title card is the 1-minute basketball game's (style.css body.game-shoot)
if (new URLSearchParams(location.search).get('game') === 'shoot') document.body.classList.add('game-shoot');
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
const PROPS = ['lamp_double', 'lamp_quad', 'lamp_arm', 'flag_white', 'planter', 'stone_marker', 'sign_board', 'scooter',
  ...CARS.flatMap((k) => [`car_${k}`, `car_${k}_far`]), 'payphone', 'bench', 'recycle_bin', 'guard_booth', 'barrier_arm', 'bollard', 'bollard_stone',
  'tent_kiosk', 'notice_board', 'haetae', 'parking_booth', 'bus'];
const CAR_FAR = 20;     // parked cars farther than this from the camera: their lighter models (a fifth of the triangles)
// phones: no parked car drawn farther than this (the 1997 aerial scans put 506 on the campus; from the gate some 460
// were in view, 1.6 M triangles of the lighter models, most of them behind 백양로's trees)
const CAR_MAX_MOBILE = 250;
const SHRUB_R = { topiary_cone: 0.6, azalea_red: 0.62, pine_cloud: 0.3, topiary_dome: 1.0, topiary_egg: 1.15 };   // (walls, m at scale 1; the pine: its trunk)
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
  // the halls first (the cells of them round the gate, src/chunks.js), the rest at low priority. The environment map
  // comes down with the data.
  const halls = ['baekyangro.glb', 'campus_town_ground.glb'].map((f) => MODELS + f);
  prefetch(halls);
  prefetch([...PROPS.map((n) => `${MODELS}props/${n}.glb`), ...castFiles(Object.keys(PEOPLE))], 'low');
  const envHdr = new RGBELoader().loadAsync(versioned('assets/hdri/env_1k_nosun.hdr'));
  const [campus, matDefs, skyMeta, nearData, farData, entrances, southData, northData, cells] = await Promise.all([
    json('data/campus.json').then((c) => { prefetch(vegFiles(c).map((f) => MODELS + f), 'low'); return c; }),
    json('data/materials.json'), json('data/sky.json'),
    bin('data/terrain_near.bin'), bin('data/terrain_far.bin'),
    json('data/entrances.json').catch(() => ({ entrances: [] })),
    bin('data/terrain_south.bin').catch(() => null),        // 신촌 로터리: the patch south of the grid
    bin('data/terrain_north.bin').catch(() => null),        // 무악학사 · 북문: the patch north of it
    // (the cells round the gate asked for as soon as the list is in: it names the gate too)
    chunkIndex(MODELS, json).then((ix) => { if (ix.spawn) prefetch(nearUrls(ix, ix.spawn)); return ix; }),
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
  const chunks = new CampusChunks(cells, { lib, scene });
  const nearCells = chunks.near([campus.spawn.pos]);
  chunks.ask(nearCells);

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
  const northPatch = T.north && northData ? hfNear.setPatch(northData, T.north, true) : null;
  lib.setTerrain(hfNear);
  const hfFar = new Heightfield(farData, T.far.half, T.far.step, T.far.n);
  // the far ring as it was where the town's ground went onto the survey (tools/town97.py far_ring): the far forest and
  // city decide on these heights, so that their draws stay as they were
  let hfFarRng = hfFar;
  if (T.far.rng) {
    const { i0, j0, nx, ny, h } = T.far.rng, d = farData.slice();
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) d[(j0 + j) * T.far.n + i0 + i] = h[j * nx + i];
    hfFarRng = new Heightfield(d, T.far.half, T.far.step, T.far.n);
  }
  // the campus's static sun shadow baked into one texture (src/bakedshadow.js): the phones' only sun shadow, the
  // desktop's beyond the shadow map; on the terrain here, on every other lit material once the scene is built.
  // Phones also take the halls' and landmarks' own baked shadow on their walls and roofs (blender/bake.py).
  const sunMap = new SunMap(hfNear, { walls: !renderer.shadowMap.enabled }).load();
  const terrain = makeNearTerrain(hfNear, campus, lib);
  sunMap.patch(terrain.material, 0);
  scene.add(terrain);
  const terrainSouth = hfNear.ext ? makeSouthTerrain(hfNear, terrain.material) : null;   // (신촌 로터리)
  if (terrainSouth) scene.add(terrainSouth);
  const terrainNorth = northPatch ? makeSouthTerrain(hfNear, terrain.material, northPatch) : null;   // (무악학사 · 북문)
  if (terrainNorth) scene.add(terrainNorth);
  const grass = new Grass(renderer, scene, lib, hfNear, campus, sun);     // blades on the lawn round the camera
  const fall = new Fall(renderer, scene, lib, hfNear, campus, sunMap);   // petals / leaves coming down round it
  const patches = [hfNear.ext && T.south, northPatch && T.north].filter(Boolean);
  scene.add(makeFarTerrain(hfFar, T.near.half, patches));
  scene.add(makeCity(hfFar, T.near.half, 1600, patches, hfFarRng));
  // the kits placed for good, the forest and the far hills' trees, drawn only where in view (world.js); whole into
  // the shadow cache
  const kitCull = new KitCuller();
  shadows.wholeSets = (on) => kitCull.shadowPass(on);
  const farForest = makeFarForest(hfFar, T.near.half, 3800, patches, northPatch &&
    { hf: hfNear, rect: [northPatch.x0, northPatch.y0, northPatch.x1, northPatch.y1], clear: T.north.clear || [], woods: T.north.woods || [] },
    hfFarRng);
  kitCull.add([farForest]);
  scene.add(farForest);
  scene.add(makeSummitTower(hfFar));
  progress('백양로를 까는 중…', 20);

  // ---------------------------------------------------------------- GLB assets
  const load = async (u, label, weight) => { const g = await loadGLB(MODELS + u); progress(label, weight); return g; };
  // the halls and landmarks round the gate (src/chunks.js; the rest come after the loading screen)
  chunks.terrainMat = terrain.material;
  const cellW = 230 / nearCells.reduce((a, f) => a + f.bytes, 0);
  const cellsIn = Promise.all(nearCells.map((f) => chunks.load(f).then(() => progress(f.kind === 'buildings' ? '건물을 세우는 중…' : '언더우드관에 담쟁이를 심는 중…', f.bytes * cellW))));
  const [road, townG] = await Promise.all([
    load('baekyangro.glb', '백양로에 차선을 긋는 중…', 115),
    // 정문 밖 (src/town.js): here only the banks the walker and the trees stand on; the town's houses, landmarks and
    // signs (campus_town.glb) come after the loading screen (the end of main)
    load('campus_town_ground.glb', '굴다리 너머 신촌에 불을 켜는 중…', 20).catch(() => null),
  ]);
  await cellsIn;
  const drapes = chunks.drapes;          // 대강당 앞 둑: the ground's own material (src/terrain.js drapeTerrain)
  bindMaterials(road.scene, lib);
  const verge = new Verge(road.scene, campus);        // 백양로's verge and planting strip: lawn (src/verge.js)
  // 정문 밖: 성산로, the railway's bank and the town beyond; the banks' trees stand on the banks' own meshes
  const townBanks = townG && campus.town ? addTown(scene, townG, lib, terrain.material) : [];
  grass.verge = verge;

  // walkable surfaces: terrain + road + amphitheater terraces
  const walkables = [terrain];
  const amph = chunks.amph;
  // the smoothed surface of every entrance flight (blender/landmarks.py walk_mesh; the procedural halls' front steps
  // are in the buildings' base file): invisible, only walked on
  const stairWalk = chunks.stairWalk;
  const roadMeshes = [];
  road.scene.traverse((o) => { if (o.isMesh) { o.receiveShadow = true; roadMeshes.push(o); } });
  scene.add(road.scene);
  road.scene.updateMatrixWorld(true);
  for (const m of [...roadMeshes, ...amph, ...stairWalk, ...townBanks]) walkables.push(m);
  if (terrainSouth) walkables.push(terrainSouth);
  if (terrainNorth) walkables.push(terrainNorth);
  for (const m of walkables) m.geometry.computeBoundsTree();

  const amphGroup = new THREE.Group();
  for (const m of amph) amphGroup.add(m);
  scene.add(amphGroup);
  // 활천 water: Ultra Water FFT ripples, caustics and the jet's rings (src/water/fountain.js)
  const fountainWater = campus.statues.fountain ? new FountainWater(renderer, scene, campus.statues.fountain, lib, sun, sunDir, { mobile: MOBILE }) : null;
  progress('건물을 정리하는 중…', 70);

  const ray = new THREE.Raycaster();
  ray.firstHitOnly = true;
  const DOWN = new THREE.Vector3(0, -1, 0), from = new THREE.Vector3();
  // (only the surfaces whose box is over the point: the trees, shrubs, props, cars and every walker's and car's path
  // ask this tens of thousands of times while the page loads)
  const walkBox = new Map(), under = [];
  const groundAt = (x, y) => {
    ray.set(from.set(x, 600, -y), DOWN);
    under.length = 0;
    for (const m of walkables) {
      let b = walkBox.get(m);
      if (!b) walkBox.set(m, b = new THREE.Box3().setFromObject(m));
      if (x >= b.min.x && x <= b.max.x && -y >= b.min.z && -y <= b.max.z) under.push(m);
    }
    const h = ray.intersectObjects(under, false);
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
  for (const b of campus.buildings) colliders.addPolygon(b.style === 'lm:hanok' ? hanokWalls(b.footprint) : RECT_HALLS.has(b.style) ? minAreaRect(b.footprint) : b.footprint);
  for (const poly of campus.colliders || []) colliders.addPolygon(poly);     // parts outside the OSM outlines (백주년기념관's front block)
  const carSets = [];                // the parked cars' culling sets (KitCuller.add): their reach on phones
  {
    const byKind = {};
    for (const pr of campus.props) (byKind[pr[0]] ||= []).push(pr);
    const rnd = mulberry(5);
    const COLLIDE = { lamp_double: 0.25, lamp_quad: 0.25, lamp_arm: 0.25, flag_white: 0.12, planter: 0.5, stone_marker: 1.0, sign_board: 0.9, payphone: 0.62, guard_booth: 1.05,
      bollard: 0.12, bollard_stone: 0.14, tent_kiosk: 1.5, notice_board: 0.7, haetae: 0.95, parking_booth: 1.3, recycle_bin: 0.7 };
    // (the 오토바이 parked before 제1공학관: the scooter the students ride, blender/bikes.py, on its stand)
    const BIKE_PAINT = ['#b3262b', '#e6e4dc', '#1f3f8f', '#d2a81c', '#1b1b1e', '#1f6f66', '#8e9399', '#7a1f2c'];
    for (const [kind, list] of Object.entries(byKind)) {
      const src = P[kind === 'motorbike' ? 'scooter' : kind];
      if (!src) continue;
      const kit = new InstancedKit(src.scene, lib, list.length, { colors: true });
      for (const [, x, y, rot] of list) {
        // Blender models face -Y; campus rotation is the heading in the campus frame
        const col = kind === 'motorbike' ? new THREE.Color(BIKE_PAINT[Math.floor(rnd() * BIKE_PAINT.length)]) : null;
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
    // (campus.json names each car's model and its colour in PARKED_COLORS: tools/build_campus.py, the cars' last pass)
    const carCount = countBy(campus.cars, (c) => c[0]);
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
    campus.cars.forEach(([k, x, y, ang, ci]) => {
      const col = new THREE.Color(PARKED_COLORS[ci % PARKED_COLORS.length]);
      parkedMatrix(k, x, y, ang);
      carKits[k].add(m4, col);
      farKits[k].add(m4, col);
      colliders.addCircle(x + Math.cos(ang) * 1.2, y + Math.sin(ang) * 1.2, 1.0);
      colliders.addCircle(x - Math.cos(ang) * 1.2, y - Math.sin(ang) * 1.2, 1.0);
    });
    for (const k in carKits) {
      for (const kit of [carKits[k], farKits[k]]) { kit.commit(); kit.addTo(scene); }
      carSets.push(kitCull.add(carKits[k].parts, { far: farKits[k].parts, dist: CAR_FAR, max: MOBILE ? CAR_MAX_MOBILE : 0 }));
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
    } else colliders.addCircle(x, y, (SHRUB_R[k] ?? 0.72) * sc);
  }
  const S = campus.statues;
  colliders.addCircle(S.eagle.pos[0], S.eagle.pos[1], S.eagle.r ?? 4.2);       // the eagle's round dais (its brick ring is walked on)
  for (const [b, r] of S.eagle.groups ?? []) {   // the four groups on the dais' edge, their wedges out on the ring
    const a = b * Math.PI / 180;
    colliders.addCircle(S.eagle.pos[0] + r * Math.sin(a), S.eagle.pos[1] + r * Math.cos(a), 0.6);
  }
  colliders.addCircle(S.underwood_statue.pos[0], S.underwood_statue.pos[1], 1.64);   // the rock-faced octagon (the lawn and curb round it are walked on; blender/statues.py UW_K)
  if (S.fountain) colliders.addCircle(S.fountain.pos[0], S.fountain.pos[1], S.fountain.rim);   // 활천 basin's stone wall
  if (S.court) {                                                                     // the two hoops of the 대강당 court
    const c = Math.cos(S.court.rot), s = Math.sin(S.court.rot);
    for (const sg of [-1, 1]) {
      // portable stands (1997 aerial scans): their frames on the paving behind the boards; else posts behind the baselines
      const ds = S.court.goals === 'portable' ? [[S.court.base[0] + 0.6, 0.75], [S.court.base[1] - 0.6, 0.75]] : [[1.0, 0.3]];
      for (const [o, r] of ds) {
        const d = sg * (S.court.L / 2 + o);
        colliders.addCircle(S.court.pos[0] + c * d, S.court.pos[1] + s * d, r);
      }
    }
  }
  if (S.jokgu) {                                                                     // the net court's two posts
    const J = S.jokgu, y = J.W / 2 + J.post;
    for (const sg of [-1, 1]) colliders.addCircle(J.pos[0] - Math.sin(J.rot) * sg * y, J.pos[1] + Math.cos(J.rot) * sg * y, 0.15);
  }
  for (const [x, y, a] of S.pitch?.goals ?? []) {                                    // 대운동장's goalposts
    for (const sg of [-1, 1]) colliders.addCircle(x - Math.sin(a) * sg * 3.72, y + Math.cos(a) * sg * 3.72, 0.15);
  }
  const banners = makeBanners(campus.banners, lib);
  flagWind(lib);                    // the white flag's cloth stirs in the wind too (src/flags.js)
  scene.add(banners);
  const posters = makeGatePosters(campus.statues.gate, groundAt);     // 정문 흰 담의 대자보 (src/posters.js)
  posters.userData.setSeason(season);
  scene.add(posters);
  scene.add(makeBoard(campus.landmarks.find((l) => l.id === 'events'), groundAt));
  const decals = new Decals(scene, campus.decals || [], walkables, hfNear, sunMap);   // manholes, oil, patches (src/decals.js)
  const drapeAt = drapeHeight(drapes);                 // the raised ground's meshes (the terraces' decks, the banks)
  const curbs = new Curbs(scene, campus.curbs || [], hfNear, walkables.slice(1), lib,     // kerbs along the paving (src/curbs.js)
    { lawn: campus.curb_lawn, ground: terrain.material, drape: drapeAt });
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
  const groups = [[-42.6, -37.9], [-53.6, -65.4], [3, -58], [-2, -92], [-96, -400], [58, 200], [-48.2, -25.5], [12, -30], [-20, 30], [110, 150], [-87.5, -178.6]]
    .map(([x, y]) => [x, y, groundAt(x, y)]);
  // people on the benches (about half of them taken, one to three to a bench; a third of that on phones) and the
  // queue at 학생회관's phone booths: one on the phone in two of the three, two more waiting behind the middle one
  const seats = [], lines = [];
  // the bench before 백주년기념관 seats 승민 and 서연 (the hero's own place goes to someone else, so no one sits twice)
  const savedHero = safeGet('y97-hero');
  const duo = ['p01', 'p11'].filter((id) => id !== savedHero);
  for (const id of ['p09', 'p10', 'p12']) if (duo.length < 2) duo.push(id);
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
        heading: Math.atan2(fx, -fy) + (((jit * 7 + k * 0.37) % 1) - 0.5) * 0.22,
        ...(Math.hypot(x + 39.94, y + 182.8) < 1 && slots.length === 2 ? { id: duo[k] } : {}) })));
    }
    // (the bank by 학생회관: the first booths in the list; a booth elsewhere is left free, so nobody here changes)
    const phones = campus.props.filter((pr) => pr[0] === 'payphone');
    const booths = phones.filter((pr) => Math.hypot(pr[1] - phones[0][1], pr[2] - phones[0][2]) < 4);
    booths.forEach(([, x, y, rot], i) => {
      if (booths.length > 1 && i === booths.length - 1) return;        // (one booth free)
      const fx = Math.cos(rot), fy = Math.sin(rot), heading = Math.atan2(-fx, fy);
      const at = (d, side = 0) => { const px = x + fx * d - fy * side, py = y + fy * d + fx * side; return { x: px, y: py, h: groundAt(px, py), heading }; };
      const on = { ...at(0.85), phone: true };                        // (the one in the booth)
      lines.push(i === Math.floor((booths.length - 1) / 2) && !MOBILE ? [on, at(1.95, 0.1), at(2.8, -0.12)] : [on]);
    });
  }
  const crowd = new Crowd(scene, cast, [...STUDENTS, ...STUDENTS, 'p07', 'p08', 'p14'], paths, groups, MOBILE ? 40 : 110, 3, { seats, lines });
  for (const p of crowd.people) shadows.addDynamic(p.a.holder);
  // small talk over their heads; what they say follows the month (crowd.season)
  crowd.season = season;
  crowd.bubbles = new Bubbles($('#bubbles'), camera);
  // 연세로's two sidewalks to 신촌 로터리 (campus.json town.walks): a crowd of their own, its own random stream. Seen
  // from the gate and from above only (nobody walks there): six walking on a phone. Updated only while the view is
  // within reach of them (life.js Crowd: 190 m), and once more after, to take them out of the scene.
  // 신촌 로터리 (tools/sinchon_rotary.py town.waiting): standing about in front of 홍익문고 and 그레이스백화점 and at
  // the two bus stops, alone (looking out for someone) or in twos and threes; fewer on the phone
  const rotWait = campus.town?.waiting;
  const rotGroups = rotWait ? rotWait.groups.filter((g, i) => !MOBILE || i % 3 === 0).map(([x, y]) => [x, y, groundAt(x, y)]) : [];
  const rotLines = rotWait ? rotWait.singles.filter((s, i) => !MOBILE || i % 4 === 0)
    .map(([x, y, fx, fy]) => [{ x, y, h: groundAt(x, y), heading: Math.atan2(fx, -fy) }]) : [];
  const townCrowd = campus.town?.walks ? new Crowd(scene, cast, [...STUDENTS, ...STUDENTS, 'p08', 'p14'],
    campus.town.walks.map((w) => new Path(w, groundAt)), rotGroups, MOBILE ? 6 : 30, 11, { lines: rotLines }) : null;
  let townCrowdNear = () => false;
  if (townCrowd) {
    for (const p of townCrowd.people) shadows.addDynamic(p.a.holder);
    townCrowd.season = season;
    townCrowd.bubbles = crowd.bubbles;
    townCrowd.shown = true;
    const pts = [...campus.town.walks.flat(), ...rotGroups, ...(rotWait?.singles ?? [])], reach = 200;
    const x0 = Math.min(...pts.map((q) => q[0])) - reach, x1 = Math.max(...pts.map((q) => q[0])) + reach;
    const y0 = Math.min(...pts.map((q) => q[1])) - reach, y1 = Math.max(...pts.map((q) => q[1])) + reach;
    townCrowdNear = (f) => f.x > x0 && f.x < x1 && -f.z > y0 && -f.z < y1;
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
  // The cars' ways are three loops (campus.json traffic, tools/build_campus.py TRAFFIC): up 백양로's northbound lane and,
  // at the 삼거리 before 언더우드관, right up the east fork past 용재관 and round 성암관 and 대우관 별관 to the car park
  // behind 대우관, or off that road at the fork east of 한경길 and round its two lanes, or left up the drive past 스팀슨관 and round the island there down to the stalls beside 핀슨관; into
  // a stall, out again after a while, and back down the roads' other side into the southbound lane.  (An alumnus
  // remembers no cars on the drives right beside 언더우드관 and 연희관, where the 2008 roadview's car went.)  One lane
  // for every free stall: the loop with the way into that stall and the way out backwards spliced in (life.js Traffic).
  let westLanes = 0;
  const bikeLanes = [];                // the loops whole, no stall: the scooters' (life.js Traffic.addBikes)
  {
    const off = R.median + R.lane * 0.5, TR = campus.traffic;
    const north = center.offset((s) => -(off + 0.5 * roundBooth(s)));            // (a point every 3 m)
    const south = center.offset((s) => off + 0.5 * roundBooth(s));
    if (TR) {
      const n = Math.ceil((TR.s_out - 0.5) / 3), vLot = TR.v_lot ?? 2.8;
      const head = north.slice(0, n), tail = south.slice(0, n).reverse(), free = Array(n).fill(Infinity);
      for (const L of TR.loops.slice().reverse()) {                              // (west first: one car to each of its stalls)
        if (L.name === 'west') westLanes = L.stalls.length;
        {
          const lane = new Path([...head, ...L.pts, ...tail], groundAt).setLimits([...free, ...L.v, ...free]).setTracks();
          lane.loop = true;
          bikeLanes.push(lane);
        }
        for (const st of L.stalls) {
          const k = st.a.length + st.b.length - 2;
          const pts = [...head, ...L.pts.slice(0, st.i + 1), ...st.a.slice(1), ...st.b.slice(1), ...L.pts.slice(st.j + 1), ...tail];
          const lim = [...free, ...L.v.slice(0, st.i + 1), ...Array(k).fill(vLot), ...L.v.slice(st.j + 1), ...free];
          const lane = new Path(pts, groundAt).setLimits(lim).setTracks();
          lane.loop = true;                // (its two ends side by side at the gate)
          const k0 = n + st.i, k1 = k0 + st.a.length - 1, k2 = k1 + st.b.length - 1;
          // the stall's turn-off, the stall (stop there for a while) and where the way out backwards ends (stop, then on)
          lane.det = [lane.cum[k0], lane.cum[k2]];
          lane.rev = [lane.cum[k1], lane.cum[k2]];
          lane.stops = [{ s: lane.cum[k1], park: true }, { s: lane.cum[k2] }];
          lane.shared = st.i === st.j;     // (the way out ends where the way in began: a car may pass the stall by)
          lanes.push(lane);
        }
      }
    } else {
      lanes.push(new Path(north, groundAt));
      lanes.push(new Path(south.reverse(), groundAt));
    }
  }
  // (more of them: the loop is nearly twice the two lanes' length and slow off 백양로, which still carries a few
  // fewer than it did)
  const traffic = new Traffic(scene, { sedan: P.car_sedan, sedan2: P.car_sedan2, hatch: P.car_hatch, tico: P.car_tico, taxi: P.car_taxi, van: P.car_van }, lanes,
    campus.traffic ? (MOBILE ? 18 : 26) : 14, cast, STUDENTS.concat(['p07', 'p08', 'p14']), 9, westLanes);
  if (P.scooter) traffic.addBikes(scene, P.scooter, bikeLanes, MOBILE ? 3 : 5, cast, ['p01', 'p02', 'p04', 'p03', 'p01', 'p09', 'p13']);
  for (const c of traffic.cars) shadows.addDynamic(c.root, c.len / 2 + 1.5);
  const walkers = crowd.people.filter((p) => p.path);        // (the cars wait for them: life.js Traffic)
  const gates = new BoothGates(scene, P.barrier_arm, R.booth, groundAt, shadows);
  // 성산로's cars and city buses (src/town.js); the sound hears them with 백양로's
  const street = campus.town && townG ? new Street(scene, campus.town, P, groundAt, { shadows }) : null;
  const heard = { cars: street ? traffic.cars.concat(street.cars) : traffic.cars };

  // ---------------------------------------------------------------- player / UI / post
  progress('가방을 메는 중…', 36);
  let heroId = safeGet('y97-hero');
  if (!HEROES.includes(heroId)) heroId = HEROES[0];
  const hero = cast.make(heroId, undefined, null, heroScale(heroId));
  scene.add(hero.holder);
  shadows.addDynamic(hero.holder);
  const player = new Player(camera, canvas, colliders, walkables, hfNear, hero);
  grass.lift = player.lift = (x, y, deck) => curbs.lift(x, y, deck);     // the lawn raised along the kerbs
  player.deckWalk = new Set(stairWalk);                // (the decks' walked faces are with the flights': on them, deck)
  grass.drape = drapeAt;                               // and the blades on the raised ground's meshes
  for (const name of ['buildings', 'landmarks']) {      // walls for the walker: BVHs built once, shared with the bird's-eye roof picking
    scene.getObjectByName(name)?.traverse((o) => { if (o.isMesh) { if (!o.geometry.boundsTree) o.geometry.computeBoundsTree(); player.walls.push(o); } });
  }
  player.teleport(campus.spawn.pos[0], campus.spawn.pos[1], campus.spawn.yaw);
  // 정문 밖: past the line of 성산로's north kerb (tools/gate_town.py town.limit, the walker's barrier's north edge) the
  // walk goes on only where campus.json walk_open has it: over 성산로's crossing, 연세로's two sidewalks and 신촌 로터리's
  // corners and crossings (tools/sinchon_rotary.py, walled round by colliders). The map, the bird's eye view and the
  // start list set no walker down past the line but there (a list of polygons: other gates may add theirs; walk_holes:
  // the rings cut out of them, 연세로's carriageway between two crossings)
  const LIMIT = campus.town?.limit ?? [];
  const OPEN = campus.walk_open ?? [], HOLES = campus.walk_holes ?? [];
  const inOpen = (x, y) => OPEN.some((p) => pointInPoly(x, y, p)) && !HOLES.some((p) => pointInPoly(x, y, p));
  const beyondGate = (x, y) => {
    if (inOpen(x, y)) return false;
    for (let k = 1; k < LIMIT.length; k++) {
      const [ax, ay] = LIMIT[k - 1], [bx, by] = LIMIT[k];
      if (x >= Math.min(ax, bx) && x <= Math.max(ax, bx)) return y < ay + (by - ay) * (x - ax) / ((bx - ax) || 1e-6);
    }
    return false;
  };
  // (and never in a pocket no walker gets out of: a garden's parterre, the gaps of a planting, inside a hall's walls;
  // Colliders.walkOut). Nor under a roof: the first face of the halls and landmarks straight down from above, more than
  // a storey over the walked surface there (inside walls the outlines miss; a porch or an arcade too, which only moves
  // the walker out from under it)
  const roofRay = new THREE.Raycaster();
  roofRay.firstHitOnly = true;
  const underRoof = (x, y) => {
    roofRay.set(from.set(x, 900, -y), DOWN);
    const h = roofRay.intersectObjects(player.walls, false)[0];
    return !!h && h.point.y > (player.groundAt(x, -y, 400) ?? hfNear.height(x, y)) + 2.2;
  };
  const walkOut = (x, y) => colliders.walkOut(x, y, undefined, underRoof);
  // the nearest point of walk_open within r m (1 m in from its edge), or null
  const nearestOpen = (x, y, r = 60) => {
    let best = null, bd = r;
    for (const p of OPEN.concat(HOLES)) {
      for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
        const [ax, ay] = p[j], [bx, by] = p[i], dx = bx - ax, dy = by - ay, l = dx * dx + dy * dy || 1;
        const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / l)), qx = ax + t * dx, qy = ay + t * dy;
        const d = Math.hypot(x - qx, y - qy);
        if (d >= bd) continue;
        const L = Math.sqrt(l), nx = -dy / L, ny = dx / L;
        for (const s of [1, -1]) if (inOpen(qx + nx * s, qy + ny * s)) { best = [qx + nx * s, qy + ny * s]; bd = d; break; }
      }
    }
    return best;
  };
  const landAt = (x, y) => {
    if (!beyondGate(x, y)) return [...walkOut(x, y), null];
    const q = nearestOpen(x, y);                       // (on 연세로 or the junction: the nearest walk open to the walker)
    if (q) return [...walkOut(q[0], q[1]), null];
    setTimeout(() => ui.toast('그쪽으로는 걸어갈 수 없어요 · 정문에서 걸어요', 3500), 0);   // (after the start's own)
    return [campus.spawn.pos[0], campus.spawn.pos[1], campus.spawn.yaw];
  };
  const post = new Post(renderer, scene, camera);
  const ui = new UI(campus, {
    onTeleport: async (x, y, facing = null) => {         // (facing: a place of the map's inset, its walker's yaw)
      if (bird.active) leaveBird();
      const wait = chunks.ensure(x, y);          // (the halls there in first: the walls, the roofs over the walk)
      if (wait) { ui.toast('그쪽 건물을 세우는 중이에요…', 60000); await wait; ui.toast('', 1); }
      const [lx, ly, yaw] = landAt(x, y);
      player.teleport(lx, ly, yaw ?? facing);
      forest.update(camera.position, true);
      resume();
    },
    onClose: () => resume(),
  });
  // 대강당 앞 농구장 (src/hoops.js): loaded when the walk or the view comes near the court, or for the 1-minute game
  // (src/shootout.js, loaded when it starts); neither comes with the page (loadBall, startShoot below)
  let ball = null, ballLoad = null, shootout = null;
  // 미니 게임 등록부: every mini game other than the 1-minute shootout and the race (which predate it) pushes one entry
  //   { on: () => bool,            under way (the walk's map, bird view, memory cards and prompts are its own then)
  //     busy?: () => bool,         a card of its own open (results, picker): main.js leaves the keys to it
  //     stop: () => void,          let it go (toTitle, another game starting)
  //     update?: (dt, t, paused) => void, pauseButtons?: (inGame) => void }
  // and the checks below ask inGame() / gameBusy() instead of naming each game
  const games = [];
  const inGame = () => !!(shootout?.on || race?.on || games.some((g) => g.on()));
  const gameBusy = () => games.some((g) => g.busy?.());
  const stopGames = (except = null) => { for (const g of games) if (g !== except) g.stop(); };
  // hero picker on the title card (portraits rendered from the real models)
  const pics = portraits(cast, HEROES);
  const pickEl = $('#hero-pick');
  const pickHero = (id) => {
    heroId = id;
    safeSet('y97-hero', id);
    pickEl.querySelectorAll('button').forEach((b) => b.classList.toggle('on', b.dataset.id === id));
    if (player.actor.id !== id) { const a = cast.make(id, undefined, null, heroScale(id)); scene.add(a.holder); shadows.addDynamic(a.holder); player.setActor(a); }
    heroPlace(id);
    $('#hero-who').textContent = `${HERO[id].name} · ${HERO[id].college}`;
  };
  let heroPlace = () => {};          // (the places come further down: the walk starts at the hero's own college)
  for (const id of HEROES) {
    const b = document.createElement('button');
    b.dataset.id = id;
    b.title = HERO[id].college;
    b.innerHTML = `<img src="${pics[id]}" alt=""><span><b>${HERO[id].name}</b>${HERO[id].short}</span>`;
    b.addEventListener('click', () => pickHero(id));
    pickEl.appendChild(b);
  }
  pickHero(heroId);
  // 「크게 보기」: the hero picked, large (src/herozoom.js, loaded on the first press); its arrows pick the next one
  $('#hero-zoom').disabled = false;
  $('#hero-zoom').addEventListener('click', (e) => {
    e.currentTarget.blur();
    import('./herozoom.js').then(({ openHeroZoom }) => openHeroZoom({ cast, ids: HEROES, id: heroId, onPick: pickHero }));
  });
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
  }
  // 활천대 앞 생일 축하: two students on the flagstones; you and the friend throw the birthday one in (src/birthday.js)
  const birthday = S.fountain ? new Birthday({ scene, cast, player, F: S.fountain, water: fountainWater, bubbles: crowd.bubbles, ui, shadows, blobs, mobile: MOBILE }) : null;
  // where to start walking (title card): 정문, the memory spots, then every named building at its front door
  // (신촌's buildings: on the nearest walk open to the walker, facing them; none further than that)
  const places = startPlaces(campus, entrances.entrances || [], (x, y, r) => colliders.resolve(x, y, r))
    .map((p) => {
      if (!beyondGate(p.x, p.y)) return p;
      const q = nearestOpen(p.x, p.y, 45);
      return q && { ...p, x: q[0], y: q[1], yaw: Math.atan2(-(p.x - q[0]), p.y - q[1]), front: false };
    })
    .filter(Boolean);
  const placeEl = $('#place-pick');
  for (const group of ['추억 장소', '건물']) {
    const og = Object.assign(document.createElement('optgroup'), { label: group });
    places.forEach((p, i) => { if (p.group === group) og.appendChild(new Option(p.name, i)); });
    placeEl.appendChild(og);
  }
  heroPlace = (id) => { const i = places.findIndex((p) => p.name === HERO[id]?.place); placeEl.value = i < 0 ? '' : i; };
  heroPlace(heroId);
  // 북문 · 무악학사 (places.js NORTH): past the map's sheet, so the map has them in an inset, and the tour pins them as
  // it does the memory spots (seen from over the campus, not only from close by)
  const north = NORTH.map((name) => {
    const m = (campus.markers || []).find((q) => q.name === name), p = places.find((q) => q.name === name);
    return m && p && { id: `north-${name}`, name, pos: m.pos, x: p.x, y: p.y, yaw: p.yaw };
  }).filter(Boolean);
  ui.north = north;

  const setSeason = (v) => {
    season = v;
    crowd.season = v;
    if (townCrowd) townCrowd.season = v;
    safeSet('y97-season', v);
    lib.setSeason(v);
    fall.setSeason(v);
    banners.userData.setSeason(v);
    posters.userData.setSeason(v);
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
    // (in the game: the way out of it; else the way into it)
    $('#shoot-quit').hidden = !shootout?.on;
    $('#shoot-go').hidden = inGame() || !S.court;
    $('#run-quit').hidden = !race?.on;
    $('#run-go').hidden = inGame();
    for (const g of games) g.pauseButtons?.(inGame());
    shootBest();
    $('#pause').hidden = false;
    $('#resume').focus({ preventScroll: true });        // (keys: Enter goes on, Shift+Tab to the buttons above it)
  };
  const startWalk = (where = null, msg = null) => {
    if (started) return;
    started = true;
    $('#intro').hidden = true;
    $('#hud').hidden = false;
    if (MOBILE) $('#touch').hidden = false;
    resume();
    const how = MOBILE ? '화면 왼쪽을 누른 채 밀어서 걸어요' : '↑↓(W·S)로 걷고 ←→(A·D)로 방향을 바꿔요';
    ui.toast(msg || `${how} · ${where ? `${where}에서 출발해요` : '정문에서 백양로를 따라 걸어 보세요'}`, 5000);
  };
  let arriving = false;
  $('#start').addEventListener('click', async () => {
    if (arriving) return;
    const p = places[placeEl.value];         // '' → 정문 (the walker stands at the spawn: at first, and after toTitle)
    // (the halls round a place far from the gate may not be in yet: src/chunks.js)
    const wait = chunks.ensure(...(p ? [p.x, p.y] : campus.spawn.pos));
    if (wait) {
      arriving = true;
      $('#start').disabled = true;
      ui.toast('그쪽 건물을 세우는 중이에요…', 60000);
      await wait;
      $('#start').disabled = false;
      arriving = false;
    }
    if (p) { player.teleport(...walkOut(p.x, p.y), p.yaw); forest.update(camera.position, true); }
    startWalk(p ? (p.front ? `${p.name} 앞` : p.name) : null);
  });
  // 「처음 화면으로」 (the settings card, the tour bar): the title card again without loading the page anew, to pick who,
  // when and where and start over. Whatever is under way is let go of (the game, the tour, a card, a shot, the
  // birthday scene, the keys and fingers held) and the walker stands idle at the gate as when the page came up
  const toTitle = () => {
    if (!started && !bird.active) return;
    shootout?.stop();                        // (its onQuit goes on with the walk: stopped below)
    race?.stop();
    race?.closePicker();
    stopGames();
    started = false;
    paused = false;
    if (ui.memoryOpen) ui.closeMemory();
    if (ui.mapOpen) ui.toggleMap(false);
    if (bird.active) leaveBird();            // (not started: it leaves for the title card)
    if (player.scripted) birthday?.abort();
    ball?.drop();
    shotBy = null;
    touch.reset();
    player.keys.clear();
    player.stick.set(0, 0);
    player.enabled = false;
    player.speed = 0;
    player.teleport(campus.spawn.pos[0], campus.spawn.pos[1], campus.spawn.yaw);
    player.showBody(true);
    play(player.actor, 'idle', { fade: 0 });
    player.actor.mixer.update(0.3);
    ui.setPrompt(null);
    for (const id of ['#pause', '#hud', '#touch', '#toast']) $(id).hidden = true;
    $('#intro').hidden = false;
    shootBest();
    forest.update(camera.position, true);
  };
  $('#to-title').addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); toTitle(); });
  // the games' results cards: 「처음 화면으로」 next to 「그만하고 산책하기」 (data-to-title, made by each game)
  document.addEventListener('click', (e) => { if (e.target.closest?.('[data-to-title]')) { e.stopPropagation(); e.target.blur(); toTitle(); } });
  $('#resume').addEventListener('click', resume);
  const setFilm = (v) => { $('#opt-film').checked = v; post.setFilm(v); document.body.classList.toggle('film', v); bird.labels({ filmOn: v }); };
  const toggleFilm = () => setFilm(!$('#opt-film').checked);
  $('#opt-film').addEventListener('change', (e) => setFilm(e.target.checked));
  $('#opt-hq').addEventListener('change', (e) => { post.setHQ(e.target.checked); sun.shadow.mapSize.set(e.target.checked ? 4096 : 2048, e.target.checked ? 4096 : 2048); sun.shadow.map?.dispose(); sun.shadow.map = null; shadows.invalidate(); });
  // first person (src/player.js): V, the HUD button, the wheel or a pinch on past the closest view; remembered
  player.onView = (first) => {
    safeSet('y97-view', first ? 'first' : 'third');
    $('#viewbtn span').textContent = first ? '3인칭' : '1인칭';
    document.querySelectorAll('[data-view]').forEach((b) => b.classList.toggle('on', (b.dataset.view === 'first') === first));
    if (started) ui.toast(first ? '1인칭 시점' : '3인칭 시점');
  };
  // (the game's address may say which: ./?game=shoot&view=first)
  const viewParam = new URLSearchParams(location.search).get('view');
  player.setFpv(viewParam ? viewParam === 'first' : safeGet('y97-view') === 'first');
  document.querySelectorAll('[data-view]').forEach((b) => {
    b.classList.toggle('on', (b.dataset.view === 'first') === player.fpv);
    b.addEventListener('click', (e) => { e.stopPropagation(); player.setFpv(b.dataset.view === 'first'); });
  });
  const openNearby = () => {
    if (ui.memoryOpen) { ui.closeMemory(); return; }
    if (inGame()) return;     // (the game: the key is the shot, shotDown)
    if (ball && !bird.active && ball.action()) { ui.setPrompt(ball.prompt()); return; }
    if (birthday && !bird.active && birthday.action()) { ui.setPrompt(null); return; }
    const l = ui.nearestLandmark(player.x, player.y);
    if (l) { player.enabled = false; ui.openMemory(l); }
  };
  const toggleMap = () => {
    if (!started || inGame()) return;
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
  const loadBall = () => (ballLoad ||= !S.court ? Promise.resolve(null) : import('./hoops.js').then(({ Basketball }) => {
    ball = new Basketball({ scene, player, ui, court: S.court, hf: hfNear, shadows, mobile: MOBILE, patch: globalPatch });
    ball.onSound = (what, p, k) => sound.ball(what, p, k);
    if (blobs) blobs.ball = ball;
    return ball;
  }));
  // the shot: held down with the ball in hand and let go (hoops.js), by E, Space or the prompt button; `by` says which,
  // so only that one coming up shoots
  let shotBy = null;
  const shotDown = (by) => {
    if (!ball?.mine || ball.shot || bird.active || !player.enabled || !ball.press()) return false;
    shotBy = by;
    ui.setPrompt(ball.prompt());
    return true;
  };
  const shotUp = (by) => { if (by && by === shotBy) { shotBy = null; ball?.letGo(); ui.setPrompt(ball?.prompt()); } };
  // 농구 1분 슛 게임 (src/shootout.js): from the title card (straight to it from ./?game=shoot), the settings card of
  // the walk and the tour bar
  let shootLoading = false;
  const startShoot = async () => {
    if (shootout?.on || shootLoading) return;
    const btn = $('#shoot-start'), go = $('#shoot-go');
    shootLoading = btn.disabled = go.disabled = true;
    try {
      const [{ Shootout }] = await Promise.all([import('./shootout.js'), loadBall()]);
      if (!ball) return;
      shootout ||= new Shootout({ scene, cast, player, ball, ui, bubbles: crowd.bubbles, shadows, blobs, sound, mobile: MOBILE,
        onQuit: () => { document.body.classList.remove('shootout'); resume(); ui.toast('농구장에서 산책을 이어 가요'); } });
    } finally { shootLoading = btn.disabled = go.disabled = false; }
    if (bird.active) leaveBird();
    race?.stop();
    stopGames();
    const how = MOBILE ? '공을 받으면 「슛」을 꾹 눌렀다가' : '공을 받으면 E나 스페이스를 꾹 눌렀다가';
    const msg = `1분 동안 몇 골? ${how} 막대가 초록 칸에 올 때 떼세요`;
    document.body.classList.add('shootout');
    if (!started) startWalk(null, msg); else { paused = false; $('#pause').hidden = true; resume(); ui.toast(msg, 5000); }
    shootout.start();
    forest.update(camera.position, true);
  };
  $('#shoot-start').addEventListener('click', startShoot);
  $('#shoot-go').addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); startShoot(); });
  $('#shoot-quit').addEventListener('click', (e) => { e.stopPropagation(); shootout?.stop(); });
  // this browser's ranking of the game, from the title card and the pause card (src/shootrecords.js, loaded when opened)
  const shootBest = () => {
    let list;
    try { list = JSON.parse(safeGet('y97-shoot-records') || '[]'); } catch { list = []; }
    if (!Array.isArray(list)) list = [];
    const best = Math.max(0, +(safeGet('y97-shoot-best') || 0), ...list.map((r) => +r?.makes || 0));
    $('#shoot-best').textContent = best ? `최고 기록 ${best}골` : '';
    $('#shoot-rank').hidden = $('#rank-pause').hidden = !(best || list.length);
  };
  shootBest();
  const openRanking = (e) => { e.stopPropagation(); e.currentTarget.blur(); import('./shootrecords.js').then((R) => R.openRanking({ onChange: shootBest })); };
  $('#shoot-rank').addEventListener('click', openRanking);
  // the game's own address, to copy and send
  $('#shoot-url').textContent = gameUrl();
  copyButton($('#shoot-copy'), gameUrl);
  $('#rank-pause').addEventListener('click', openRanking);
  // 캠퍼스 달리기 (src/race.js): a course picked from the title card or the settings card, a run through its gates
  let race = null, raceLoad = null;
  const loadRace = () => (raceLoad ||= import('./race.js').then(({ Race }) => (race = new Race({
    scene, camera, player, sound, groundAt, ensure: (x, y) => chunks.ensure(x, y), cast, shadows, blobs,
    onBegin: (msg) => {
      // nobody walking about and no car on the roads while racing: only the runners of race.js
      for (const o of [crowd, townCrowd, traffic, street]) if (o) o.hidden = true;
      if (bird.active) leaveBird();
      shootout?.stop();
      stopGames();
      if (ui.memoryOpen) ui.closeMemory();
      if (ui.mapOpen) ui.toggleMap(false);
      ball?.drop();
      document.body.classList.add('racing');
      if (!started) startWalk(null, msg); else { paused = false; $('#pause').hidden = true; ui.toast(msg, 5000); }
      ui.setPrompt(null);
      forest.update(camera.position, true);
    },
    onQuit: () => {
      for (const o of [crowd, townCrowd, traffic, street]) if (o) o.hidden = false;
      document.body.classList.remove('racing'); resume(); ui.toast('달리기를 마치고 산책을 이어 가요'); },
  }))));
  const openRace = async (e) => {
    e?.stopPropagation(); e?.currentTarget?.blur();
    (await loadRace()).openPicker();
  };
  $('#run-start').addEventListener('click', openRace);
  $('#run-go').addEventListener('click', openRace);
  $('#run-quit').addEventListener('click', (e) => { e.stopPropagation(); race?.stop(); });
  // 이곳은 어디? (src/photoquiz.js): a photo's spot to walk to and look from, five a round (./?game=photo)
  let quiz = null, quizLoad = null;
  const quizEntry = { on: () => !!quiz?.on, busy: () => !!quiz?.busy, stop: () => quiz?.stop(),
    update: (dt, t, p) => quiz?.update(dt, t, p),
    pauseButtons: (game) => { $('#photo-go').hidden = game; $('#photo-quit').hidden = !quiz?.on; } };
  games.push(quizEntry);
  // (./?game=photo makes the title card's button stand out)
  if (new URLSearchParams(location.search).get('game') === 'photo') document.body.classList.add('game-photo');
  const loadQuiz = () => (quizLoad ||= import('./photoquiz.js').then(({ PhotoQuiz }) => (quiz = new PhotoQuiz({
    scene, camera, player, sound, places, groundAt, mobile: MOBILE,
    go: async (x, y, yaw, still) => {      // (still(): not let go of while the halls came in)
      const wait = chunks.ensure(x, y);
      if (wait) { ui.toast('그쪽 건물을 세우는 중이에요…', 60000); await wait; ui.toast('', 1); }
      if (still && !still()) return;
      const [lx, ly] = landAt(x, y);
      player.teleport(lx, ly, yaw);
      forest.update(camera.position, true);
    },
    onBegin: (msg) => {
      if (bird.active) leaveBird();
      shootout?.stop(); race?.stop(); race?.closePicker(); stopGames(quizEntry);
      if (ui.memoryOpen) ui.closeMemory();
      if (ui.mapOpen) ui.toggleMap(false);
      ball?.drop();
      document.body.classList.add('photoquiz');
      if (!started) startWalk(null, msg); else { paused = false; $('#pause').hidden = true; ui.toast(msg, 5000); }
      ui.setPrompt(null);
    },
    onQuit: () => { document.body.classList.remove('photoquiz'); resume(); ui.toast('사진 찾기를 마치고 산책을 이어 가요'); },
  })))).then((q) => { if (window.__y97) window.__y97.quiz = q; return q; });
  const startQuiz = async (e) => { e?.stopPropagation(); e?.currentTarget?.blur(); (await loadQuiz()).start(); };
  $('#photo-start').addEventListener('click', (e) => { sound.start(); startQuiz(e); });
  $('#photo-go').addEventListener('click', startQuiz);
  $('#photo-quit').addEventListener('click', (e) => { e.stopPropagation(); quiz?.stop(); });
  // 삐삐 호출 (src/pager.js): from the title card or the settings card; the pager goes off, a run to a phone booth
  // (campus.json's payphones), the number dialled, a run to where the friend on the line said
  let pager = null, pagerLoad = null;
  const pagerGame = { on: () => !!pager?.on, busy: () => !!pager?.busy, stop: () => pager?.stop(), update: (dt, t, p) => pager?.update(dt, t, p),
    pauseButtons: (game) => { $('#pager-go').hidden = game; $('#pager-quit').hidden = !pager?.on; } };
  games.push(pagerGame);
  const loadPager = () => (pagerLoad ||= import('./pager.js').then(({ Pager }) => (pager = new Pager({
    scene, camera, player, cast, crowd, sound, groundAt, ensure: (x, y) => chunks.ensure(x, y), shadows, blobs, mobile: MOBILE,
    booths: campus.props.filter((pr) => pr[0] === 'payphone'), buildings: campus.buildings, places: places.filter((p) => !NORTH.includes(p.name)),
    onBegin: (msg) => {
      if (bird.active) leaveBird();
      shootout?.stop();
      race?.stop();
      race?.closePicker();
      stopGames(pagerGame);
      if (ui.memoryOpen) ui.closeMemory();
      if (ui.mapOpen) ui.toggleMap(false);
      ball?.drop();
      document.body.classList.add('paging');
      if (!started) startWalk(null, msg); else { paused = false; $('#pause').hidden = true; ui.toast(msg, 5000); }
      ui.setPrompt(null);
    },
    onQuit: () => { document.body.classList.remove('paging'); resume(); ui.toast('삐삐를 끄고 산책을 이어 가요'); },
  }))));
  const startPager = async (e) => {
    e?.stopPropagation(); e?.currentTarget?.blur();
    sound.start();
    await loadPager();
    if (window.__y97) window.__y97.pager = pager;       // (headless checks)
    pager.start();
  };
  $('#pager-start').addEventListener('click', startPager);
  $('#pager-go').addEventListener('click', startPager);
  $('#pager-quit').addEventListener('click', (e) => { e.stopPropagation(); pager?.stop(); });
  // 연고전 응원 연습 (src/cheer.js): a beat picked from the title card or the settings card, the moves on the beat
  // with a block of students on 대강당's forecourt
  let cheer = null, cheerLoad = null;
  const cheerGame = { on: () => !!cheer?.on, busy: () => !!(cheer?.pickOpen || cheer?.resultsOpen),
    stop: () => { cheer?.stop(); cheer?.closePicker(); }, update: (dt, t, p) => cheer?.update(dt, t, p),
    pauseButtons: (game) => { $('#cheer-go').hidden = game; $('#cheer-quit').hidden = !cheer?.on; } };
  games.push(cheerGame);
  const loadCheer = () => (cheerLoad ||= import('./cheer.js').then(({ Cheer }) => (cheer = new Cheer({
    scene, cast, player, sound, groundAt, crowd, shadows, blobs, bubbles: crowd.bubbles, mobile: MOBILE,
    ensure: (x, y) => chunks.ensure(x, y), season: () => season, setSeason,
    onBegin: (msg) => {
      if (bird.active) leaveBird();
      shootout?.stop();
      race?.stop();
      race?.closePicker();
      stopGames(cheerGame);
      if (ui.memoryOpen) ui.closeMemory();
      if (ui.mapOpen) ui.toggleMap(false);
      ball?.drop();
      document.body.classList.add('cheering');
      if (!started) startWalk(null, msg); else { paused = false; $('#pause').hidden = true; ui.toast(msg, 5000); }
      ui.setPrompt(null);
      forest.update(camera.position, true);
    },
    onQuit: () => { document.body.classList.remove('cheering'); resume(); ui.toast('응원 연습을 마치고 산책을 이어 가요'); },
  }))));
  const openCheer = async (e) => {
    e?.stopPropagation(); e?.currentTarget?.blur();
    (await loadCheer()).openPicker();
  };
  $('#cheer-start').addEventListener('click', (e) => { sound.start(); openCheer(e); });
  $('#cheer-go').addEventListener('click', openCheer);
  $('#cheer-quit').addEventListener('click', (e) => { e.stopPropagation(); cheer?.stop(); });
  // 강의실 찾기 (src/timetable.js): a timetable picked from the title card or the settings card, its halls' doors in turn
  let lecture = null, lectureLoad = null;
  const lectureGame = {
    on: () => !!lecture?.on,
    busy: () => !!(lecture?.pickOpen || lecture?.resultsOpen),
    stop: () => { lecture?.stop(); lecture?.closePicker(); },
    update: (dt, t, p) => lecture?.update(dt, t, p),
    pauseButtons: (game) => { $('#class-go').hidden = game; $('#class-quit').hidden = !lecture?.on; },
  };
  games.push(lectureGame);
  const loadLecture = () => (lectureLoad ||= import('./timetable.js').then(({ Timetable }) => (lecture = new Timetable({
    scene, camera, player, sound, groundAt, places, mobile: MOBILE, ensure: (x, y) => chunks.ensure(x, y),
    onBegin: (msg) => {
      if (bird.active) leaveBird();
      shootout?.stop();
      race?.stop();
      race?.closePicker();
      stopGames(lectureGame);
      if (ui.memoryOpen) ui.closeMemory();
      if (ui.mapOpen) ui.toggleMap(false);
      ball?.drop();
      document.body.classList.add('classing');
      if (!started) startWalk(null, msg); else { paused = false; $('#pause').hidden = true; ui.toast(msg, 5000); }
      ui.setPrompt(null);
      forest.update(camera.position, true);
    },
    onQuit: () => { document.body.classList.remove('classing'); resume(); ui.toast('강의실 찾기를 마치고 산책을 이어 가요'); },
  }))));
  const openLecture = async (e) => {
    e?.stopPropagation(); e?.currentTarget?.blur();
    sound.start();
    (await loadLecture()).openPicker();
  };
  $('#class-start').addEventListener('click', openLecture);
  $('#class-go').addEventListener('click', openLecture);
  $('#class-quit').addEventListener('click', (e) => { e.stopPropagation(); lecture?.stop(); });
  // 생일 축하 (src/bdaygame.js): friends brought from in front of the halls within the time, then the throw at 활천대
  let bday = null, bdayLoad = null;
  const loadBday = () => (bdayLoad ||= import('./bdaygame.js').then(({ BdayGame }) => (bday = new BdayGame({
    scene, camera, player, cast, birthday, places, groundAt, bubbles: crowd.bubbles, shadows, blobs, sound, ui, mobile: MOBILE,
    ensure: (x, y) => chunks.ensure(x, y),
    onBegin: (msg) => {
      if (bird.active) leaveBird();
      shootout?.stop();
      race?.stop();
      race?.closePicker();
      stopGames(bdayGame);
      for (const o of [crowd, townCrowd, traffic, street]) if (o?.hidden) o.hidden = false;   // (the friends are among the crowd)
      if (ui.memoryOpen) ui.closeMemory();
      if (ui.mapOpen) ui.toggleMap(false);
      ball?.drop();
      document.body.classList.add('bdaygame');
      if (!started) startWalk(null, msg); else { paused = false; $('#pause').hidden = true; ui.toast(msg, 6000); }
      ui.setPrompt(null);
      forest.update(camera.position, true);
    },
    onQuit: () => { document.body.classList.remove('bdaygame'); resume(); ui.toast('생일 축하를 마치고 산책을 이어 가요'); },
  }))));
  const bdayGame = { on: () => !!bday?.on, busy: () => !!bday?.busy, stop: () => bday?.stop(), update: (dt, t, p) => bday?.update(dt, t, p),
    pauseButtons: (g) => { $('#bday-go').hidden = g || !birthday; $('#bday-quit').hidden = !bday?.on; } };
  games.push(bdayGame);
  const startBday = async (e) => {
    e?.stopPropagation(); e?.currentTarget?.blur();
    sound.start();
    (await loadBday()).start();
  };
  $('#bday-start').hidden = !birthday;
  $('#bday-start').addEventListener('click', startBday);
  $('#bday-go').addEventListener('click', startBday);
  $('#bday-quit').addEventListener('click', (e) => { e.stopPropagation(); bday?.stop(); });
  if (birthday) birthday.onSplash = (p) => sound.splash(p);
  $('#opt-sound').checked = sound.on;
  $('#opt-sound').addEventListener('change', (e) => sound.setOn(e.target.checked));
  for (const id of ['#start', '#tour-start', '#shoot-start', '#run-start']) $(id).addEventListener('click', () => sound.start());
  const SEASON_ORDER = ['spring', 'summer', 'autumn'];
  const SEASON_KEYS = { Digit1: 'spring', Digit2: 'summer', Digit3: 'autumn' };
  // the tour may go over all the detailed ground: the near grid and the patches beside it (terrain.south: 신촌 로터리)
  const tourBounds = (() => {
    const h = T.near.half, b = { x0: -h, x1: h, y0: -h, y1: h };
    for (const P of Object.values(T)) {
      if (!P || P === T.near || !(P.nx && P.ny && P.step && P.x0 !== undefined)) continue;
      b.x0 = Math.min(b.x0, P.x0); b.y0 = Math.min(b.y0, P.y0);
      b.x1 = Math.max(b.x1, P.x0 + (P.nx - 1) * P.step); b.y1 = Math.max(b.y1, P.y0 + (P.ny - 1) * P.step);
    }
    return b;
  })();
  const bird = new BirdsEye({
    camera, dom: canvas, landmarks: [...campus.landmarks, ...north], markers: (campus.markers || []).filter((m) => !NORTH.includes(m.name)),
    heightAt: (x, y) => hfNear.height(x, y),
    groundAt,
    surfaceAt,
    bounds: tourBounds,
    pickGround: (nx, ny) => {
      pickRay.setFromCamera(new THREE.Vector2(nx, ny), camera);
      const h = pickRay.intersectObjects(walkables, false)[0];
      return h ? [h.point.x, -h.point.z] : null;
    },
    onWalkHere: (x, y, l) => {
      // a pin's walker stands where the start list puts it: before the door, facing it (a building's tag sits inside
      // its footprint, a memory spot's pin in the middle of its ground: the parterres before 언더우드관, the azaleas
      // round 용재관, the eagle's dais); 정문: the walk's own start
      const p = l && (l.id === 'gate' ? { x: campus.spawn.pos[0], y: campus.spawn.pos[1], yaw: campus.spawn.yaw } : places.find((q) => q.name === l.name));
      if (!p) [x, y] = colliders.resolve(x, y, 0.6);
      const fromTitle = !started;
      leaveBird();
      const [lx, ly, yaw] = landAt(p ? p.x : x, p ? p.y : y);            // (신촌: on the nearest open walk)
      if (fromTitle) startWalk(ui.placeName(lx, ly, false));
      player.teleport(lx, ly, yaw ?? p?.yaw ?? null);
      player.cam.ready = false;
      forest.update(camera.position, true);
    },
    onMemory: (l) => { player.enabled = false; ui.openMemory(l); },
    onAction: (what) => {
      if (what === 'back') leaveBird();
      else if (what === 'shoot') startShoot();
      else if (what === 'title') toTitle();
      else if (what === 'film') toggleFilm();
      else if (what === 'season') setSeason(SEASON_ORDER[(SEASON_ORDER.indexOf(season) + 1) % 3]);
    },
  });
  const enterBird = () => {
    if (bird.active || inGame()) return;
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
    if (shootout?.resultsOpen) { if (e.code === 'Escape') shootout.stop(); return; }
    if (race?.resultsOpen || race?.pickOpen || gameBusy()) return;           // (their Escape: race.js and the games' own)
    // (the settings card is open: Enter is its focused button's, and no card opens behind it)
    if (paused && (e.code === 'Enter' || e.code === 'KeyE' || e.code === 'KeyM')) return;
    if (e.code === 'KeyB' && !ui.memoryOpen) { enterBird(); return; }
    if ((e.code === 'KeyE' || e.code === 'Space') && !e.repeat && shotDown(e.code)) return;
    if (e.code === 'KeyE' || e.code === 'Enter') openNearby();
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
  addEventListener('keyup', (e) => shotUp(e.code));
  addEventListener('blur', () => shotUp(shotBy));
  const walkLabels = new WalkLabels(campus.markers || [], camera, $('#blabels'));
  // HUD buttons (the only way in on a phone: no keys there)
  const touch = new TouchControls(player, canvas, $('#stick'));
  const tap = (sel, fn) => $(sel).addEventListener('click', (e) => { e.stopPropagation(); e.currentTarget.blur(); fn(); });
  // the prompt: a tap does what E does; with the ball in hand it is the shot, held down and let go (shotDown)
  let swallow = false;
  $('#prompt').addEventListener('pointerdown', (e) => { if (shotDown('p' + e.pointerId)) { swallow = true; e.preventDefault(); } });
  addEventListener('pointerup', (e) => shotUp('p' + e.pointerId));
  addEventListener('pointercancel', (e) => shotUp('p' + e.pointerId));
  tap('#prompt', () => { if (swallow) swallow = false; else openNearby(); });
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
      shootout?.movers(player.x, player.y, player.movers);
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
    if (townCrowd && (townCrowd.shown || townCrowdNear(focus))) {
      townCrowd.update(dt, tAcc, started ? player : NOBODY, focus);
      townCrowd.shown = townCrowd.people.some((p) => p.a.holder.parent);
    }
    birthday?.update(dt, tAcc, started && !bird.active, focus);
    crowd.bubbles.update(tAcc, started && !bird.active);
    birds.update(dt, tAcc, started ? player : NOBODY, crowd.people, focus);
    traffic.update(dt, started ? player : NOBODY, focus, walkers);
    street?.update(dt, focus, started ? player : null);
    gates.update(dt, traffic);
    fountainWater?.update(dt, camera);
    lib.uniforms.uWindT.value = tAcc;     // the wind in the leaves, branches and banners (materials.js sway)
    if (!ballLoad && S.court && (focus.x - S.court.pos[0]) ** 2 + (focus.z + S.court.pos[1]) ** 2 < 150 * 150) loadBall();
    ball?.update(dt, tAcc, started && !bird.active);
    shootout?.update(dt, tAcc, paused || ui.memoryOpen || ui.mapOpen);
    race?.update(dt, tAcc, paused || ui.memoryOpen || ui.mapOpen);
    for (const g of games) g.update?.(dt, tAcc, paused || ui.memoryOpen || ui.mapOpen);
    blobs?.update(camera.position);
    sound.update(dt, tAcc, { player, walking: started && !bird.active, crowd, traffic: heard, birds, season });
    decals.update(camera.position);
    curbs.update(camera.position);
    // the shadow frustum follows the view in texel-snapped steps; people and cars are redrawn into it every frame
    shadows.update(focus, bird.active ? focus.y : camera.position.y - 10, span);
    if (MOBILE) for (const s of carSets) s.m2 = bird.active ? 0 : CAR_MAX_MOBILE ** 2;   // (the tour shows them all)
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
        const game = inGame(), busy = game || !!ball?.pick;      // (picking up the ball: no other prompt meanwhile)
        const bp = game && !shootout?.on ? null : busy ? ball.prompt() : ball?.prompt() || birthday?.prompt();
        ui.setPrompt(bp ? bp : l && !busy && !ui.memoryOpen ? `${l.name} · ${MOBILE ? '눌러서 ' : ''}그때의 추억 보기` : null);
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
    startWalk, enterBird, leaveBird, toTitle, record, birthday, get bday() { return bday; }, loadBday, post, grass, sunMap, blobs, curbs, verge, sound, birds, landAt, places,
    get ball() { return ball; }, loadBall, startShoot, get shootout() { return shootout; }, loadRace, get race() { return race; }, loadLecture, get lecture() { return lecture; },
    // tools/bake_sun_shadows.mjs (desktop path: it draws with the shadow map; the page needs reloading afterwards)
    // (the kits whole for it: it draws them from above, tile by tile)
    bakeSunMap: async () => {
      kitCull.whole();
      kitCull.enabled = false;
      try {
        return await bakeSunMap({ renderer, scene, sun, sunDir, shadows, forest, hf: hfNear, walk: walkables, hide: [banners, ...(ball?.balls.map((b) => b.mesh) ?? [])], skip: farScenery });
      } finally {
        kitCull.enabled = true;
      }
    },
    kitCull, chunks,
    // every cell of the halls and landmarks in (src/chunks.js), and the textures at full size (materials.js
    // laterFull): the tools that shoot or bake wait for it
    get campusLoaded() { return chunks.loaded && texturesFull(); } };
  window.__y97.atmos = ATMOS;
  window.__y97.loading = loading;

  // ready once the first frames are drawn (the shadow map's and the post passes' shaders are compiled there)
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  placeEl.disabled = false;
  loading.done('1997년, 백양로에 도착했습니다.');
  $('#start').disabled = false;
  $('#tour-start').disabled = false;
  $('#shoot-start').disabled = false;
  $('#run-start').disabled = false;
  $('#photo-start').disabled = false;
  $('#pager-start').disabled = false;
  $('#cheer-start').disabled = false;
  $('#class-start').disabled = false;
  $('#bday-start').disabled = false;
  // the rest of the halls and landmarks, the nearest to the view first (src/chunks.js); each set in once its
  // textures are in and its shaders compiled: then the walker's walls, the sun's shadows and the atmosphere take it
  chunks.renderer = renderer;
  chunks.camera = camera;
  chunks.late = true;
  chunks.onPrepare = (g) => {
    g.traverse((o) => { for (const m of [].concat(o.material || [])) globalPatch(m); });
    sunMap.patchScene(g, farScenery);
  };
  chunks.onAdd = (meshes) => {
    for (const o of meshes) {
      o.geometry.computeBoundsTree();
      player.walls.push(o);
    }
    shadows.invalidate();
  };
  chunks.stream(() => { const f = bird.active ? bird.focus : camera.position; return [f.x, -f.z]; });
  // then the big textures at full size, where the loading screen had their smaller copies (materials.js laterFull)
  chunks.allIn.then(() => upgradeTextures());
  // the town beyond the gate: its houses, 신촌 로터리's landmarks and signs, the bridge (campus_town.glb, 1.3 MB), down
  // while the title card is up rather than on the loading screen (2026-11-16). __y97.townLoaded: for the tools that
  // shoot or bake (tools/snapshots.mjs, tools/bake_sun_shadows.mjs)
  window.__y97.townLoaded = !campus.town;
  if (campus.town) {
    window.__y97.townReady = loadGLB(MODELS + 'campus_town.glb').then((g) => {
      const had = new Set(scene.children);
      addTown(scene, g, lib, terrain.material);
      for (const o of scene.children) if (!had.has(o)) sunMap.patchScene(o, farScenery);
    }).catch((e) => console.warn('no campus_town.glb:', e)).finally(() => { window.__y97.townLoaded = true; });
  }
}

// The halls with a pitched roof and the gym stand on the smallest rectangle round their OSM outline (blender/generic.py
// build_generic, common.py min_area_rect): their walls are that rectangle's, so is the walker's. (On the outline, the
// corner an L or a T leaves out was open ground inside the walls: 연합신학대학원's 626 m², 한경관's 400 m², 논지당's
// 80 m²; put down there, the walker could not get out.)
const RECT_HALLS = new Set(['stone', 'house', 'stone_pale', 'gym']);
function minAreaRect(fp) {
  let best = null;
  for (let i = 0; i < fp.length; i++) {
    const [ax, ay] = fp[i], [bx, by] = fp[(i + 1) % fp.length];
    if (Math.hypot(bx - ax, by - ay) < 1e-3) continue;
    const ang = Math.atan2(by - ay, bx - ax), c = Math.cos(ang), s = Math.sin(ang);
    const us = fp.map(([x, y]) => x * c + y * s), vs = fp.map(([x, y]) => -x * s + y * c);
    const u0 = Math.min(...us), u1 = Math.max(...us), v0 = Math.min(...vs), v1 = Math.max(...vs);
    if (!best || (u1 - u0) * (v1 - v0) < best.area) best = { area: (u1 - u0) * (v1 - v0), c, s, u0, u1, v0, v1 };
  }
  const { c, s, u0, u1, v0, v1 } = best;
  return [[u0, v0], [u1, v0], [u1, v1], [u0, v1]].map(([u, v]) => [u * c - v * s, u * s + v * c]);
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
    if (s[5]) continue;                     // planted in a planter beside the flight (build_campus.py DW_ANNEX_BEDS)
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
