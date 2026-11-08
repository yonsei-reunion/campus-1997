// Building name tags while walking: the few named buildings (campus.markers) nearest the walker float a small
// tag over their roof, fading with distance; tags that would overlap give way to the nearer building.
import * as THREE from 'three';

const NEAR = 90, SHOW = 5;

export class WalkLabels {
  constructor(markers, camera, layer) {
    this.camera = camera;
    this.layer = layer;
    this.items = markers.map((m) => {
      const el = document.createElement('div');
      el.className = 'blabel';
      el.textContent = m.name;
      el.style.display = 'none';
      layer.appendChild(el);
      return { m, el, d: 1e9, on: false };
    });
    this.active = [];
    this._t = 0;
    this._v = new THREE.Vector3();
  }

  hide() {
    for (const it of this.active) it.el.style.display = 'none';
    this.active.length = 0;
  }

  update(dt, px, py) {
    this._t -= dt;
    if (this._t <= 0) {
      // pick the candidates a few times a second: the nearest buildings round the walker
      this._t = 0.3;
      for (const it of this.items) it.d = Math.hypot(it.m.pos[0] - px, it.m.pos[1] - py);
      const next = this.items.filter((it) => it.d < NEAR).sort((a, b) => a.d - b.d).slice(0, SHOW);
      for (const it of this.active) if (!next.includes(it)) it.el.style.display = 'none';
      this.active = next;
    }
    const W = innerWidth, H = innerHeight, v = this._v, boxes = [];
    // how far the view looks up (the camera looks down its -Z): the roofs come into it, and the tags go back up to them
    const up = Math.max(0, -this.camera.matrixWorld.elements[9]);
    for (const it of this.active) {
      // over the roof, but never far above the eye: close to a tall hall the tag comes down its front
      v.set(it.m.pos[0], Math.min(it.m.top, this.camera.position.y + 7 + up * 60), -it.m.pos[1]).project(this.camera);
      // a tall hall close by puts its roof above the view: the tag then sits along the top edge
      if (v.z > 1 || Math.abs(v.x) > 1.05 || v.y < -0.6) { it.el.style.display = 'none'; continue; }
      const sx = ((v.x + 1) / 2) * W, sy = Math.max(70, ((1 - v.y) / 2) * H);
      const w = it.m.name.length * 13 + 20;
      const box = [sx - w / 2, sy - 26, sx + w / 2, sy];
      if (boxes.some((q) => box[0] < q[2] && box[2] > q[0] && box[1] < q[3] && box[3] > q[1])) { it.el.style.display = 'none'; continue; }
      boxes.push(box);
      it.el.style.display = '';
      it.el.style.opacity = String(Math.min(1, 1.6 - it.d / NEAR));
      it.el.style.transform = `translate(${sx}px, ${sy}px) translate(-50%, -100%)`;
    }
  }
}
