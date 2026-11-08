// People: Quaternius CC0 modular characters (blender/characters.py) driven by the shared rig clips,
// in the manner of the sim-office engine (actors.js): a holder group, an AnimationMixer per person,
// cross-faded clips, and walk/run cycles whose playback speed follows the ground speed (no foot sliding).
import * as THREE from 'three';
import { clone as skeletonClone } from 'three/addons/utils/SkeletonUtils.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { loadGLB } from './world.js';
import { pcss } from './materials.js';
import { HERO_BAGS, baggedGeometry } from './bags.js';

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

// Every part of a person (skin, clothes, hair, eyes ...) is a flat colour, so one vertex-coloured material serves
// everyone and each person is a single SkinnedMesh: one draw call (and one in the shadow pass) instead of 6-10.
// The per-part roughness (hair is glossier) rides along as a vertex attribute.
const PERSON_MAT = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, metalness: 0, envMapIntensity: 0.8 });
PERSON_MAT.name = 'person';
PERSON_MAT.onBeforeCompile = (sh) => {
  sh.vertexShader = sh.vertexShader
    .replace('#include <common>', '#include <common>\nattribute float rough;\nvarying float vRough;')
    .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRough = rough;');
  sh.fragmentShader = sh.fragmentShader
    .replace('#include <common>', '#include <common>\nvarying float vRough;')
    .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = vRough;');
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
  const geos = parts.map((m) => {
    const src = m.geometry, n = src.attributes.position.count;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', src.attributes.position);
    g.setAttribute('normal', src.attributes.normal);
    // the parts may store joints / weights in different array types: unify them so they merge
    const si = src.attributes.skinIndex, sw = src.attributes.skinWeight;
    const idx = new Uint16Array(n * 4), wt = new Float32Array(n * 4);
    for (let i = 0; i < n; i++) {
      for (let k = 0; k < 4; k++) { idx[i * 4 + k] = si.getComponent(i, k); wt[i * 4 + k] = sw.getComponent(i, k); }
    }
    g.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(idx, 4));
    g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(wt, 4));
    const c = m.material.color, col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.setAttribute('rough', new THREE.Float32BufferAttribute(new Float32Array(n).fill(/Hair/.test(m.material.name) ? 0.55 : 0.85), 1));
    g.setIndex(src.index ? Array.from(src.index.array) : Array.from({ length: n }, (_, i) => i));
    return g;
  });
  const merged = mergeGeometries(geos, false);
  if (!merged) { console.warn('could not merge person parts', root.name); return; }
  const mesh = new THREE.SkinnedMesh(merged, PERSON_MAT);
  mesh.name = first.name;
  mesh.position.copy(first.position); mesh.quaternion.copy(first.quaternion); mesh.scale.copy(first.scale);
  first.parent.add(mesh);
  mesh.bind(first.skeleton, first.bindMatrix);
  merged.computeBoundingSphere();
  mesh.boundingSphere = merged.boundingSphere.clone();
  mesh.boundingSphere.radius *= POSE_SLACK;
  for (const p of parts) { p.parent.remove(p); p.geometry.dispose(); }
}

const PEOPLE_DIR = 'assets/models/people/', RIGS = ['rig-umc', 'rig-women'];
// the files Cast.load(ids) reads (for world.js prefetch)
export const castFiles = (ids) => [...RIGS, ...ids].map((n) => PEOPLE_DIR + n + '.glb');

export class Cast {
  constructor() { this.models = {}; this.rigs = {}; }

  async load(ids, onEach) {
    const base = PEOPLE_DIR;
    await Promise.all(RIGS.map(async (r) => {
      const g = await loadGLB(base + r + '.glb');
      const u = g.scene.getObjectByName(r)?.userData || {};
      this.rigs[r] = { clips: g.animations, walkSpeed: +u.walk_speed || 1.2, runSpeed: +u.run_speed || 2.8 };
      onEach?.();
    }));
    await Promise.all(ids.map(async (id) => {
      const g = await loadGLB(base + id + '.glb');
      let rig = 'rig-umc';
      g.scene.traverse((o) => { if (o.userData && typeof o.userData.rig === 'string') rig = o.userData.rig; });
      mergeParts(g.scene);
      this.models[id] = { scene: g.scene, rig };
      onEach?.();
    }));
  }

  // bag: what the person carries (bags.js: merged into their one mesh), null for nothing; a hero has their own
  make(id, bag = HERO_BAGS[id] ?? null) {
    const src = this.models[id];
    const holder = new THREE.Group();
    const root = skeletonClone(src.scene);
    if (bag) root.traverse((o) => { if (o.isSkinnedMesh) o.geometry = baggedGeometry(o, id, bag); });
    // frustum culled by the posed bounds above (off-screen people cost nothing, in the shadow pass too)
    root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    holder.add(root);
    const rig = this.rigs[src.rig];
    const mixer = new THREE.AnimationMixer(root);
    const actions = {};
    for (const c of rig.clips) actions[c.name] = mixer.clipAction(c);
    const a = { id, bag, holder, root, mixer, actions, current: null, walkSpeed: rig.walkSpeed, runSpeed: rig.runSpeed, after: null };
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
