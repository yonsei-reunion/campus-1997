// Sun shadows with a static cache.
// The sun never moves, so buildings, trees, props and the ground only need drawing into the shadow map when the
// shadow frustum itself moves (it follows the view in coarse, texel-snapped steps), the span or map size changes,
// or the season swaps the leaf textures. That static map is kept in a second render target. Every frame only the
// moving casters (people, cars; registered with addDynamic) are redrawn: the cached texels under where they were
// and where they are now are copied back, and the moving casters near the view are drawn on top of them.
import * as THREE from 'three';

export const DYNAMIC_LAYER = 1;           // the moving casters' meshes are on this layer as well as layer 0
const DYN_R = 55;                         // moving things farther than this from the view cast no shadow
const MOVE = 0.16;                        // re-render the static map once the view is this share of the span off centre
const _v = new THREE.Vector3();

export class SunShadows {
  constructor(renderer, scene, sun, sunDir, dist = 420) {
    this.renderer = renderer;
    this.scene = scene;
    this.sun = sun;
    this.sunDir = sunDir;
    this.dist = dist;
    this.cache = null;
    this.dirty = true;
    this.span = 0;
    this.center = new THREE.Vector3(1e9, 0, 0);
    this.dyn = [];                        // {root, meshes, r}
    this.toPx = new THREE.Matrix4();
    this.prev = null;                     // pixel rect where moving casters were drawn last frame
    this.rect = [0, 0, 0, 0];
    this.staticCam = new THREE.Camera();  // layer 0: everything (moving casters are switched off for that pass)
    this.dynCam = new THREE.Camera();
    this.dynCam.layers.set(DYNAMIC_LAYER);
    this.noClear = () => {};
    this.refreshes = 0;
    this.wholeSets = null;                // (on) => the view-culled kits drawn whole or culled again (world.js KitCuller)
    this.pending = null;                  // what update() asked for this frame: {focus, y, span}
    this.req = { focus: new THREE.Vector3(), y: 0, span: 0 };
    // The depth passes need the renderer's per-render state, so they run where three draws shadows: inside
    // render(), after the scene matrices and the on-screen skeletons are updated and before the lights are set up.
    const sm = renderer.shadowMap;
    this.drawShadows = sm.render;
    sm.render = (lights, sc, camera) => {
      if (sc !== scene || !this.pending) return;
      this.pending = null;
      this._frame();
    };
  }

  // a moving object (a person's holder, a car with its driver); r: the radius its shadow caster fits in, metres
  addDynamic(root, r = 1.6) {
    const meshes = [];
    root.traverse((o) => {
      if (!o.isMesh) return;
      o.layers.enable(DYNAMIC_LAYER);
      meshes.push(o);
    });
    this.dyn.push({ root, meshes, r });
  }

  invalidate() { this.dirty = true; }

  // focus: the point the view centres on; y: the height the light aims at; span: half width of the shadow frustum
  // (call before rendering the frame; the work happens in the frame's first render of the scene)
  update(focus, y, span) {
    if (!this.renderer.shadowMap.enabled) return;
    this.req.focus.copy(focus);
    this.req.y = y;
    this.req.span = span;
    this.pending = this.req;
    const sh = this.sun.shadow;
    const far = Math.hypot(focus.x - this.center.x, focus.z - this.center.z) > span * MOVE || Math.abs(y - this.center.y) > 30;
    if (this.dirty || far || span !== this.span || !sh.map || !this.cache || this.cache.width !== sh.mapSize.x) this._place(focus, y, span);
  }

  // move the shadow frustum (the scene's matrices, the light's too, are updated by the render that follows)
  _place(focus, y, span) {
    const { sun } = this;
    const sh = sun.shadow, cam = sh.camera;
    if (span !== this.span) {
      this.span = span;
      Object.assign(cam, { left: -span, right: span, top: span, bottom: -span });
      cam.updateProjectionMatrix();
    }
    // snap to whole shadow texels so the static shadows do not swim when the frustum steps
    const texel = (span * 2) / sh.mapSize.x;
    this.center.set(Math.round(focus.x / texel) * texel, y, Math.round(focus.z / texel) * texel);
    sun.target.position.copy(this.center);
    sun.position.copy(this.center).addScaledVector(this.sunDir, this.dist);
    this.dirty = true;
  }

  _frame() {
    if (this.dirty || !this.sun.shadow.map || !this.cache || this.cache.width !== this.sun.shadow.mapSize.x) this._static();
    this._dynamic(this.req.focus);
  }

  _draw(camera) {
    this.renderer.shadowMap.needsUpdate = true;
    this.drawShadows([this.sun], this.scene, camera);
  }

  _static() {
    const { renderer, sun } = this;
    const sh = sun.shadow, cam = sh.camera;
    for (const d of this.dyn) for (const m of d.meshes) m.castShadow = false;
    this.wholeSets?.(true);               // the cache serves every view: shrubs, props and cars out of sight cast too
    try {
      this._draw(this.staticCam);
    } finally {
      this.wholeSets?.(false);
    }
    // light space -> shadow map pixels, for the rectangles of the moving casters
    this.toPx.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse);
    const w = sh.map.width, h = sh.map.height;
    if (!this.cache || this.cache.width !== w || this.cache.height !== h) {
      this.cache?.dispose();
      this.cache = new THREE.WebGLRenderTarget(w, h, { minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false });
      const prevRT = renderer.getRenderTarget();
      renderer.setRenderTarget(this.cache);          // creates its framebuffer
      renderer.setRenderTarget(prevRT);
    }
    this._blit(sh.map, this.cache, 0, 0, w, h);
    this.prev = null;
    this.dirty = false;
    this.refreshes++;
  }

  _dynamic(focus) {
    const { renderer, sun } = this;
    const sh = sun.shadow, w = sh.map.width, h = sh.map.height;
    const pxPerM = w / (this.span * 2);
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const r2 = DYN_R * DYN_R;
    for (const d of this.dyn) {
      const p = d.root.position;
      const on = !!d.root.parent && d.root.visible && (p.x - focus.x) ** 2 + (p.z - focus.z) ** 2 < r2;
      for (const m of d.meshes) m.castShadow = on;
      if (!on) continue;
      // (skeletons: three's shadow pass updates every caster it draws, the ones behind the camera too)
      _v.set(p.x, p.y + 1, p.z).applyMatrix4(this.toPx);
      const cx = (_v.x * 0.5 + 0.5) * w, cy = (_v.y * 0.5 + 0.5) * h, rr = d.r * pxPerM + 2;
      x0 = Math.min(x0, cx - rr); x1 = Math.max(x1, cx + rr);
      y0 = Math.min(y0, cy - rr); y1 = Math.max(y1, cy + rr);
    }
    const cur = x1 > x0 ? this.rect : null;
    if (cur) {
      cur[0] = Math.max(0, Math.floor(x0)); cur[1] = Math.max(0, Math.floor(y0));
      cur[2] = Math.min(w, Math.ceil(x1)); cur[3] = Math.min(h, Math.ceil(y1));
    }
    // put back the static texels under last frame's moving casters and under this frame's
    const p = this.prev;
    if (p || cur) {
      const a = p || cur, b = cur || p;
      this._blit(this.cache, sh.map, Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3]));
    }
    if (!cur) { this.prev = null; return; }
    this.prev = (this._prevBuf ||= [0, 0, 0, 0]);
    this.prev.splice(0, 4, ...cur);
    // the moving casters on top, without clearing the restored map
    const clear = renderer.clear;
    renderer.clear = this.noClear;
    try {
      this._draw(this.dynCam);
    } finally {
      renderer.clear = clear;
    }
  }

  // copy colour (packed depth) and depth between two render targets of the same size and format
  _blit(src, dst, x0, y0, x1, y1) {
    if (x1 <= x0 || y1 <= y0) return;
    const renderer = this.renderer, gl = renderer.getContext(), state = renderer.state;
    const props = renderer.properties;
    const sf = props.get(src).__webglFramebuffer, df = props.get(dst).__webglFramebuffer;
    if (!sf || !df) return;
    const prevRT = renderer.getRenderTarget();
    state.setScissorTest(false);
    state.bindFramebuffer(gl.READ_FRAMEBUFFER, sf);
    state.bindFramebuffer(gl.DRAW_FRAMEBUFFER, df);
    gl.blitFramebuffer(x0, y0, x1, y1, x0, y0, x1, y1, gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT, gl.NEAREST);
    state.bindFramebuffer(gl.READ_FRAMEBUFFER, null);
    state.bindFramebuffer(gl.DRAW_FRAMEBUFFER, null);
    renderer.setRenderTarget(prevRT);
  }
}
