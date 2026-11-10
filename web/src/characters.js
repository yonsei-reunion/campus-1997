// People: Quaternius CC0 modular characters (blender/characters.py) driven by the shared rig clips,
// in the manner of the sim-office engine (actors.js): a holder group, an AnimationMixer per person,
// cross-faded clips, and walk/run cycles whose playback speed follows the ground speed (no foot sliding).
import * as THREE from 'three';
import { clone as skeletonClone } from 'three/addons/utils/SkeletonUtils.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { loadGLB } from './world.js';
import { pcss } from './materials.js';
import { HERO_BAGS, baggedGeometry } from './bags.js';
import { mulberry, versioned } from './util.js';

export const PEOPLE = {
  'man-tee': '흰 티 · 청바지',
  'man-check': '버건디 셔츠',
  'man-cheer': '파란 점퍼',
  'man-hoodie': '남색 후드티',
  'man-grey': '갈색 염색 머리',
  'man-blazer': '콤비 재킷',
  'man-professor': '교수님',
  'man-staff': '교직원',
  'woman-tee': '흰 티 · 청바지',
  'woman-pink': '분홍 니트',
  'woman-dress': '베이지 롱원피스',
  'woman-dress-blue': '남색 롱원피스',
  'woman-cardigan': '올리브 카디건',
  'woman-staff': '교직원',
};
export const STUDENTS = ['man-tee', 'man-check', 'man-cheer', 'man-hoodie', 'man-grey', 'man-blazer',
  'woman-tee', 'woman-pink', 'woman-dress', 'woman-dress-blue', 'woman-cardigan'];
export const HEROES = ['man-tee', 'man-cheer', 'man-check', 'woman-tee', 'woman-dress', 'woman-cardigan'];

// Every part of a person (skin, clothes, hair ...) is a flat colour, so one vertex-coloured material serves
// everyone and each person is a single SkinnedMesh: one draw call (and one in the shadow pass) instead of 6-10.
// The per-part roughness (hair is glossier) rides along as a vertex attribute.
// The eyes, brows and mouths are a few lines drawn on one small atlas all the people share (blender/faces.py): the
// front of a face lies on its own cell, everything else on the blank cell, and the picture multiplies the vertex
// colour. So the lines keep to whatever skin a person of the crowd has, and fade into it with distance (mip maps).
// The picture's alpha is how much of that shows: the rest is the white of the eye.
const PERSON_MAT = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, metalness: 0, envMapIntensity: 0.8 });
PERSON_MAT.name = 'person';
const FACE_BIAS = '-0.75', EYE_WHITE = '0.84, 0.83, 0.80';     // (faces.py WHITE)
const BLANK_UV = 0.875;            // the middle of the atlas' blank cell (u and v): faces.py BLANK
function loadFaces() {
  return new Promise((res, rej) => new THREE.TextureLoader().load(versioned(PEOPLE_DIR + 'faces.png'), (t) => {
    t.colorSpace = THREE.SRGBColorSpace;
    t.flipY = false;               // (glTF texture coordinates: v from the top)
    t.anisotropy = 4;
    PERSON_MAT.map = t;
    PERSON_MAT.needsUpdate = true;
    res();
  }, undefined, rej));
}
PERSON_MAT.onBeforeCompile = (sh) => {
  sh.vertexShader = sh.vertexShader
    .replace('#include <common>', '#include <common>\nattribute float rough;\nvarying float vRough;')
    .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRough = rough;');
  sh.fragmentShader = sh.fragmentShader
    .replace('#include <common>', '#include <common>\nvarying float vRough;')
    .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = vRough;')
    // the drawn face, laid on after the vertex colour (the white of the eye is white on any skin), read most of a
    // mip level sharper than the screen asks for: thin strokes hold a little further away
    .replace('#include <map_fragment>', '')
    .replace('#include <color_fragment>', `#include <color_fragment>
      vec4 drawn = texture2D( map, vMapUv, ${FACE_BIAS} );
      diffuseColor.rgb = mix( vec3( ${EYE_WHITE} ), diffuseColor.rgb * drawn.rgb, drawn.a );`);
};
pcss(PERSON_MAT);

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
    g.setAttribute('rough', new THREE.Float32BufferAttribute(new Float32Array(n).fill(/Hair/.test(m.material.name) ? 0.55 : 0.85), 1));
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
// one in five, dark ones. The heroes, the drivers and the birthday pair keep the models as they are.
const JEANS = ['#46638f', '#2b3c5c', '#7f9cc0', '#8fa8c8'];
const SKIN = ['#f0c9a4', '#e6b991', '#d9a77d', '#c99168'];
const RIMS = ['#77736c', '#2a2420'];       // thin metal, dark horn
// material name -> the colours to draw from (the first is the model's own)
const LOOKS = {
  'man-tee': { LightBrown: ['#f1efe8', '#f1efe8', '#d8dde3', '#e9dfa8', '#a9c3de', '#2f3a55', '#9a9a96'], LightBlue: [...JEANS, '#a8946a'] },
  'man-check': { LightBrown: ['#8a3a33', '#2f5a45', '#27406e', '#b58a3a', '#5b6b7c', '#e4e0d4'], LightBlue: [...JEANS, '#3a3f47', '#a8946a'] },
  'man-hoodie': { Purple: ['#23345e', '#8d8f92', '#2f5a45', '#6e2430', '#c9c3b2', '#1f1f24'], LightBlue: ['#a8946a', ...JEANS, '#3a3f47'] },
  'man-cheer': { LightBlue: JEANS },                       // (the cheer jacket stays Yonsei blue)
  'man-grey': { Purple: ['#b3262e', '#8d8f92', '#d8b23a', '#2f6a4a', '#e9e6dc', '#274a8a'], LightBlue: JEANS },
  'man-blazer': { Suit: ['#5e4634', '#27304a', '#4a4d52', '#8a7a5c', '#3d4a3a'], LightBlue: [...JEANS, '#3a3f47', '#a8946a'] },
  'man-professor': { Suit: ['#55595f', '#2c3448', '#4a4038', '#3a3f47', '#6b6a5c'], Tie: ['#2f4a7a', '#6e2430', '#3d5a45', '#4a4a50'] },
  'man-staff': {},
  'woman-tee': { White: ['#f4f1e8', '#f4f1e8', '#f3d9de', '#cfe0ee', '#e9dfa8', '#2f3a55', '#b9c9a8'], Orange: [...JEANS, '#cdb994', '#2a2a2e'] },
  'woman-pink': { White: ['#e7a7b6', '#f0e6d2', '#a9c3de', '#c7b3dc', '#b5d6c3', '#e8c66a', '#c95a5a'], Orange: ['#cdb994', ...JEANS, '#2a2a2e', '#f0eee8'] },
  'woman-dress': { LimeGreen: ['#e3d7bd', '#d9b8b0', '#aeb89a', '#c9b48a', '#8f6f5a', '#b7c4d6'] },
  'woman-dress-blue': { LimeGreen: ['#4f6f9c', '#27304a', '#6e2430', '#2f5a45', '#3a3338', '#7a5a7a'] },
  'woman-cardigan': { Black: ['#6f7f5a', '#b58a3a', '#7a2f38', '#8d8f92', '#2f3a55', '#e6dcc6', '#c98a8a'], Orange: ['#2b2f3a', ...JEANS, '#5b5348', '#cdb994'] },
  'woman-staff': { Black: ['#2f3644', '#3a3f47', '#4a4038', '#5b6470'] },
};

// the look of the n-th person of the crowd: { colors: {material: hex}, scale: [width, height], glasses }. Its own
// random stream (as bags.js crowdBag), so the crowd's paths and faces stay where they were. The drawn lines of the
// face need no colours here: they darken the skin they lie on (the brows stay the model's: dark, or a professor's grey).
export function crowdLook(id, n) {
  const r = mulberry(n * 2654435761 + 977);
  const colors = {};
  const set = LOOKS[id] || {};
  for (const k in set) colors[k] = set[k][Math.floor(r() * set[k].length)];
  colors.Skin = SKIN[Math.floor(r() * SKIN.length)];
  const h = r();
  if (id !== 'man-professor' && id !== 'man-grey') {       // (grey hair, and the dyed brown of 1997, stay)
    colors.Hair = h < 0.74 ? '#141110' : h < 0.93 ? '#2b1f18' : '#4a3020';
  }
  const tall = 1 + 0.032 * ((r() + r() + r() - 1.5) / 0.5);            // about normal, sd 3.2 %
  const build = 1 + 0.02 * (r() + r() - 1);
  const clamp = (v) => Math.min(1.065, Math.max(0.94, v));
  const glasses = r() < (id === 'man-professor' ? 0.7 : 0.3);
  colors.Glasses = RIMS[r() < 0.8 ? 0 : 1];
  return { colors, scale: [clamp(tall * build), clamp(tall)], glasses };
}

// the triangles of `geo` without the glasses: an index of its own, kept with the index it was taken from
const bareIndex = new WeakMap();
function withoutGlasses(geo, ranges) {
  const part = ranges?.find((p) => p.name === 'Glasses');
  if (!part) return geo.index;
  let idx = bareIndex.get(geo.index);
  if (!idx) {
    const a = geo.index.array, keep = [];
    for (let i = 0; i < a.length; i += 3) if (a[i] < part.start || a[i] >= part.start + part.count) keep.push(a[i], a[i + 1], a[i + 2]);
    idx = new THREE.BufferAttribute(new a.constructor(keep), 1);
    bareIndex.set(geo.index, idx);
  }
  return idx;
}

// `geo` (a person's merged geometry, or that with a bag: the person's vertices come first) as one person wears it:
// the parts named in `colors` in those colours, with the glasses or without. A geometry sharing every buffer but
// the colours (and the index, without glasses); people who wear the model as it is share one.
const worn = new WeakMap();        // geometry -> [without glasses, with]
function dressed(geo, ranges, colors, glasses) {
  if (!ranges || !geo.attributes.color) return geo;
  if (!colors) {
    const made = worn.get(geo) || worn.set(geo, []).get(geo);
    return made[+glasses] || (made[+glasses] = dressed(geo, ranges, {}, glasses));
  }
  const g = new THREE.BufferGeometry();
  for (const k in geo.attributes) if (k !== 'color') g.setAttribute(k, geo.attributes[k]);
  g.setIndex(glasses ? geo.index : withoutGlasses(geo, ranges));
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
      if (o.isSkinnedMesh) o.geometry = dressed(o.geometry, src.ranges, look?.colors, look ? look.glasses : src.glasses);
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
