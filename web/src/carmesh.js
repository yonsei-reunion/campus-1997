// A car model as one mesh: every part merged, its material's colour written on its corners, so that a car seen from
// some way off is one draw call. 성산로's cars are drawn so (town.js Street: they pass 10 m and more off), and
// 백양로's past an arm's length (life.js Traffic: the full model, thirty meshes and a driver, only near the view).
// The glass is opaque dark grey, the lamps their unlit colours, the wheels do not turn.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { pcss, globalPatch } from './materials.js';

const GLASS = new THREE.Color(0.035, 0.045, 0.055);
const LAMP = { light_red: new THREE.Color(0.45, 0.02, 0.02), light_white: new THREE.Color(0.85, 0.85, 0.8), light_amber: new THREE.Color(0.85, 0.4, 0.04) };

// paint: 1 where the corner is body paint. keep(o): false for a mesh to leave out (the scooter's stand)
export function oneMesh(src, keep = null) {
  src.updateMatrixWorld(true);
  const geos = [];
  src.traverse((o) => {
    if (!o.isMesh || (keep && !keep(o))) return;
    const g = o.geometry.clone().applyMatrix4(o.matrixWorld);
    for (const k of Object.keys(g.attributes)) if (k !== 'position' && k !== 'normal') g.deleteAttribute(k);
    if (!g.attributes.normal) g.computeVertexNormals();
    const n = g.attributes.position.count, m = o.material, name = m.name || '';
    const c = name.startsWith('glass') ? GLASS : LAMP[name] ?? (m.map ? new THREE.Color(0.75, 0.75, 0.72) : m.color);
    const col = new Float32Array(n * 3), paint = new Float32Array(n).fill(name === 'car_paint' ? 1 : 0);
    for (let i = 0; i < n; i++) { col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    g.setAttribute('paint', new THREE.BufferAttribute(paint, 1));
    if (!g.index) g.setIndex(Array.from({ length: n }, (_, i) => i));
    geos.push(g);
  });
  const g = mergeGeometries(geos, false);
  g.computeBoundingBox();
  g.computeBoundingSphere();
  return g;
}

// that mesh in a colour of its own: the shared corners, its own colours
export function painted(base, color) {
  const g = new THREE.BufferGeometry();
  g.setIndex(base.index);
  g.setAttribute('position', base.attributes.position);
  g.setAttribute('normal', base.attributes.normal);
  const col = base.attributes.color.array.slice(), p = base.attributes.paint.array;
  for (let i = 0; i < p.length; i++) if (p[i]) { col[i * 3] = color.r; col[i * 3 + 1] = color.g; col[i * 3 + 2] = color.b; }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.boundingBox = base.boundingBox; g.boundingSphere = base.boundingSphere;
  return g;
}

// the one material all such cars share (dressed as the library's materials are: the soft shadows and the air)
let shared = null;
export function carMaterial() {
  if (shared) return shared;
  shared = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.42, metalness: 0.15 });
  pcss(shared);
  shared.name = 'street_car';
  globalPatch(shared);
  return shared;
}
