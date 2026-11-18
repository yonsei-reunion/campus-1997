// The halls and landmarks in cells (tools/split_glb.mjs: campus_buildings.glb and campus_landmarks.glb cut into a file
// for each 160 m cell, a hall whole in the cell of its centre, plus a base file of each with what has to be there
// wherever the walk starts). The loading screen waits for the base files and the cells within NEAR_R of the gate; the
// rest come down while the title card is up and as the walk goes on, the nearest to the view first, each set in once
// its textures are in and its shaders compiled.
// Without the cells (a tree whose GLBs were never split: vite.config.js splits them when it starts), the two whole
// files are the base.
import * as THREE from 'three';
import { loadGLB, prefetch, glbMaterials, bindMaterials, mergeStatic } from './world.js';
import { drapeTerrain } from './terrain.js';
import { texturesReady } from './materials.js';

export const NEAR_R = 250;                // m from the gate (and from wherever the walk is set down) to the cell's box
const AHEAD = 3;                          // files coming down at once behind the loading screen

export async function chunkIndex(models, json) {
  try {
    const ix = await json(models + 'campus/chunks.json');
    return { ...ix, dir: models + 'campus/' };
  } catch {
    return { cell: 0, dir: models, files: ['buildings', 'landmarks'].map((kind) => ({ file: `campus_${kind}.glb`, kind, cell: null, bytes: 1 })) };
  }
}

// m on the ground from campus (x, y) to a file's box (three x, z: z = -y); a base file is everywhere
const away = (f, x, y) => (f.cell ? Math.hypot(Math.max(f.box[0] - x, 0, x - f.box[2]), Math.max(f.box[1] + y, 0, -y - f.box[3])) : 0);

// the URLs of the files within r of (x, y): before the material library is up, to ask for their bytes (the list names
// the gate, campus.json's spawn, so that this need not wait for campus.json)
export const nearUrls = (ix, [x, y], r = NEAR_R) => ix.files.filter((f) => away(f, x, y) <= r).map((f) => ix.dir + f.file);

export class CampusChunks {
  // terrainMat: the raised ground's meshes draw with it (terrain.js drapeTerrain)
  constructor(index, { lib, scene, terrainMat }) {
    this.lib = lib;
    this.scene = scene;
    this.terrainMat = terrainMat;
    this.files = index.files.map((f) => ({ ...f, url: index.dir + f.file, asked: false, p: null, in: false }));
    this.groups = {};
    for (const kind of ['buildings', 'landmarks']) {
      const g = this.groups[kind] = new THREE.Group();
      g.name = kind;
      scene.add(g);
    }
    // from the base files: the walked surfaces of the flights and the amphitheater, the raised ground's meshes
    this.stairWalk = [];
    this.amph = [];
    this.drapes = [];
    this.late = false;            // set in from now on: compiled and textured first, then onAdd
    this.onPrepare = null;        // (group) for each file set in late, before its shaders are compiled: their patches
    this.onAdd = null;            // (meshes) once it is in: the walker's walls, the shadows
    this.focus = () => [0, 0];
    this.inflight = 0;
    this.chain = Promise.resolve();
    this.renderer = null;
    this.camera = null;
    this.left = this.files.length;
    this.allIn = new Promise((r) => { this._allIn = r; });
  }

  get loaded() { return this.left === 0; }

  // the files within r of any of the points (campus x, y), the base ones with them
  near(points, r = NEAR_R) {
    return this.files.filter((f) => !f.cell || points.some(([x, y]) => away(f, x, y) <= r));
  }

  // their bytes asked for, and their materials' textures as soon as each file's JSON is in
  ask(files, priority = 'auto') {
    const fresh = files.filter((f) => !f.asked);
    if (!fresh.length) return;
    prefetch(fresh.map((f) => f.url), priority);
    for (const f of fresh) {
      f.asked = true;
      glbMaterials(f.url).then((names) => { for (const n of names) if (this.lib.defs[n]) this.lib.get(n); });
    }
  }

  // the file parsed and set in (once): the parsing in turn with the other files' (the main thread's part of it)
  load(f) {
    if (f.p) return f.p;
    this.ask([f]);
    f.p = (async () => {
      const g = await loadGLB(f.url);
      const run = this.chain.then(() => this._place(f, g));
      this.chain = run.catch(() => {});
      await run;
    })().catch((e) => console.warn('campus cell', f.file, e));
    return f.p;
  }

  // every file within r of (x, y) set in; null if they all are already, else a promise of it (the nearest first)
  ensure(x, y, r = NEAR_R) {
    const want = this.near([[x, y]], r).filter((f) => !f.in).sort((a, b) => away(a, x, y) - away(b, x, y));
    return want.length ? Promise.all(want.map((f) => this.load(f))) : null;
  }

  // the rest, the nearest to focus() (campus x, y) first, AHEAD at a time
  stream(focus) {
    this.focus = focus;
    const pump = () => {
      while (this.inflight < AHEAD) {
        const [x, y] = this.focus();
        let best = null, bd = Infinity;
        for (const f of this.files) {
          if (f.p) continue;
          const d = away(f, x, y);
          if (d < bd) { bd = d; best = f; }
        }
        if (!best) return;
        this.inflight++;
        this.load(best).finally(() => { this.inflight--; pump(); });
      }
    };
    pump();
  }

  async _place(f, gltf) {
    const root = gltf.scene, lib = this.lib;
    bindMaterials(root, lib, false, true);
    for (const m of drapeTerrain(root, this.terrainMat)) this.drapes.push(m);
    root.updateMatrixWorld(true);
    const amph = [], stairs = [];
    root.traverse((o) => {
      if (!o.isMesh) return;
      const names = o.name + ((o.parent && o.parent.name) || '');
      if (/walk_stairs/.test(names)) stairs.push(o);
      else if (/amphitheater/.test(names)) amph.push(o);
    });
    if (this.late && (amph.length || stairs.length)) console.warn('campus cell', f.file, 'has walked surfaces: they belong in the base file');
    for (const o of stairs) { o.material = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }); o.removeFromParent(); this.stairWalk.push(o); }
    for (const m of amph) {                  // (drawn as they are, not merged: walked on)
      const w = m.matrixWorld.clone();
      m.removeFromParent();
      m.matrix.copy(w);
      m.matrix.decompose(m.position, m.quaternion, m.scale);
      m.castShadow = m.receiveShadow = true;
      this.amph.push(m);
    }
    // a cell's file: one mesh of each material (its own cell); a base file: in 160 m cells as before
    const merged = mergeStatic(root, { chunk: f.cell ? 0 : 160, name: f.file });
    const meshes = [...merged.children];
    if (this.late) {
      this.onPrepare?.(merged);
      await texturesReady([merged]);
      const r = this.renderer;
      if (r) {
        const prev = r.getRenderTarget();
        r.setRenderTarget(this.warm ||= new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType }));
        // (the scene's lights and fog: the programs the frame will ask for)
        const c = r.extensions.has('KHR_parallel_shader_compile') ? r.compileAsync(merged, this.camera, this.scene) : r.compile(merged, this.camera, this.scene);
        r.setRenderTarget(prev);
        await c;
      }
    }
    for (const m of meshes) this.groups[f.kind].add(m);
    f.in = true;
    if (this.late) this.onAdd?.(meshes);
    if (--this.left === 0) this._allIn();
  }
}
