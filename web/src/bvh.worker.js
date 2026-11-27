// The ground meshes' BVHs built off the main thread (player.js bvhInWorker): three-mesh-bvh's own build on copies of
// the arrays, sent back serialized with the index in the order the build left it (as computeBoundsTree leaves it)
import { BufferGeometry, BufferAttribute } from 'three';
import { MeshBVH } from 'three-mesh-bvh';

self.onmessage = (e) => {
  const { id, pos, idx } = e.data;
  try {
    const g = new BufferGeometry();
    g.setAttribute('position', new BufferAttribute(pos, 3));
    g.setIndex(new BufferAttribute(idx, 1));
    const s = MeshBVH.serialize(new MeshBVH(g), { copyIndexBuffer: false });
    self.postMessage({ id, roots: s.roots, index: s.index }, [...s.roots, s.index.buffer]);
  } catch (err) {
    self.postMessage({ id, error: String(err?.message ?? err) });
  }
};
