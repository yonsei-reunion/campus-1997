// Blob shadows for phones: a soft dark patch on the ground under every person, moving car and the basketball.
// Phones draw no shadow maps (main.js), and the baked map (bakedshadow.js) has only what stands still, so without
// these people and cars float over the ground. One InstancedMesh of ground-hugging quads, drawn after the opaque
// scene and multiplied onto it (no depth writes), each a gaussian-edged round rectangle: a 0.35 m disc between a
// person's feet, the body's outline under a car. In the baked shadow of a building or a tree they are fainter (no
// sun to block there, only the sky).
import * as THREE from 'three';
import { SUN_MAP_GLSL } from './bakedshadow.js';

const MAX = 320;
const FAR = 70;                                   // farther from the view than this: no blob
const LIFT = 0.02;
const _m = new THREE.Matrix4(), _x = new THREE.Vector3(), _y = new THREE.Vector3(), _z = new THREE.Vector3();
const _a = new THREE.Vector3(), _b = new THREE.Vector3();

const VERT = `
  attribute vec4 aShape;      // half length (local x), half width (local z), corner radius, core inset
  attribute vec2 aSoft;       // gaussian width of the edge, darkness at the core
  varying vec2 vP; varying vec4 vShape; varying vec2 vSoft; varying vec3 vW;
  void main() {
    vec2 ext = aShape.xy + 2.5 * aSoft.x;
    vP = position.xz * ext;
    vShape = aShape; vSoft = aSoft;
    vec4 w = modelMatrix * instanceMatrix * vec4( vP.x, 0.0, vP.y, 1.0 );
    vW = w.xyz;
    gl_Position = projectionMatrix * viewMatrix * w;
  }`;
const FRAG = `
  uniform sampler2D uSunMap;
  uniform vec4 uSunRect;
  ${SUN_MAP_GLSL}
  uniform vec3 uView;
  varying vec2 vP; varying vec4 vShape; varying vec2 vSoft; varying vec3 vW;
  void main() {
    // signed distance to the round rectangle, then a gaussian falloff outside its core
    vec2 q = abs( vP ) - ( vShape.xy - vShape.z );
    float d = length( max( q, 0.0 ) ) + min( max( q.x, q.y ), 0.0 ) - vShape.z;
    float t = max( d + vShape.w, 0.0 ) / vSoft.x;
    float a = vSoft.y * exp( -t * t );
    // in the shade (baked sun shadow) only the sky is blocked: fainter
    vec2 p = vec2( vW.x, -vW.z );
    float sun = sunMapAt( p, dFdx( p ), dFdy( p ) );
    a *= mix( 0.45, 1.0, sun );
    a *= 1.0 - smoothstep( ${(FAR - 20).toFixed(1)}, ${FAR.toFixed(1)}, distance( vW, uView ) );
    gl_FragColor = vec4( vec3( 1.0 - a ), 1.0 );
  }`;

export class Blobs {
  // hf: the terrain heightfield (slopes); sunMap: bakedshadow.js SunMap
  constructor(scene, hf, sunMap) {
    this.hf = hf;
    this.people = [];             // {a: actor, feet: [bone, bone]}
    this.cars = [];               // {c: traffic car, hl, hw}
    this.hero = null;             // () => actor
    this.ball = null;             // hoops.js Basketball
    const geo = new THREE.PlaneGeometry(2, 2);
    geo.rotateX(-Math.PI / 2);    // in the ground plane, facing up
    this.shape = new THREE.InstancedBufferAttribute(new Float32Array(MAX * 4), 4);
    this.soft = new THREE.InstancedBufferAttribute(new Float32Array(MAX * 2), 2);
    this.shape.setUsage(THREE.DynamicDrawUsage);
    this.soft.setUsage(THREE.DynamicDrawUsage);
    geo.setAttribute('aShape', this.shape);
    geo.setAttribute('aSoft', this.soft);
    this.uView = { value: new THREE.Vector3() };
    const mat = new THREE.ShaderMaterial({
      uniforms: { uSunMap: sunMap.uniforms.uSunMap, uSunRect: sunMap.uniforms.uSunRect, uView: this.uView },
      vertexShader: VERT, fragmentShader: FRAG,
      transparent: true, depthWrite: false, blending: THREE.MultiplyBlending,
      // (pulled a little towards the view: no fighting with the ground's depth farther out)
      polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4,
    });
    this.mesh = new THREE.InstancedMesh(geo, mat, MAX);
    this.mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.mesh.count = 0;
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = -1;   // before the see-through things (glass, spray), which would otherwise be darkened
    this.mesh.name = 'blob_shadows';
    scene.add(this.mesh);
  }

  addPerson(a) {
    const f = (n) => a.root.getObjectByName(n);
    this.people.push({ a, feet: [f('FootL'), f('FootR')] });
  }

  addCar(c) {
    // body outline from the model at rest (+X forward, three -Z left), a little inside the bumpers and mirrors
    const box = new THREE.Box3().setFromObject(c.root, true);
    this.cars.push({ c, hl: c.len / 2 - 0.1, hw: (box.max.z - box.min.z) / 2 - 0.12 });
  }

  // one blob: centre (three x, ground height, z), heading (rotation about up), shape and softness
  _put(x, h, z, rot, hl, hw, corner, inset, sigma, dark) {
    const i = this.mesh.count;
    if (i >= MAX) return;
    // tilted to the terrain's slope (central differences over a metre and a half); level on what stands over the
    // terrain (the court's slab, a terrace, a landing)
    const hf = this.hf, cy = -z, e = 0.75;
    if (h - hf.height(x, cy) > 0.25) _y.set(0, 1, 0);
    else _y.set(hf.height(x - e, cy) - hf.height(x + e, cy), 2 * e, -(hf.height(x, cy - e) - hf.height(x, cy + e))).normalize();
    _a.set(Math.cos(rot), 0, -Math.sin(rot));                 // heading: local +X
    _z.crossVectors(_a, _y).normalize();
    _x.crossVectors(_y, _z);
    _m.makeBasis(_x, _y, _z).setPosition(x, h + LIFT, z);
    this.mesh.setMatrixAt(i, _m);
    this.shape.setXYZW(i, hl, hw, corner, inset);
    this.soft.setXY(i, sigma, dark);
    this.mesh.count = i + 1;
  }

  update(view) {
    this.mesh.count = 0;
    this.uView.value.copy(view);
    const far2 = FAR * FAR;
    const near = (p) => (p.x - view.x) ** 2 + (p.z - view.z) ** 2 < far2;
    const person = (a, feet) => {
      const hp = a.holder.position;
      if (!a.holder.parent || !a.holder.visible || !near(hp)) return;
      let x = hp.x, z = hp.z, up = 0;
      const [l, r] = feet;
      if (l && r) {
        // between the two feet (bones' world matrices from the last frame); off the ground in a jump: fainter, wider
        const L = l.matrixWorld.elements, R = r.matrixWorld.elements;
        x = (L[12] + R[12]) / 2; z = (L[14] + R[14]) / 2;
        if (Math.abs(x - hp.x) > 0.8 || Math.abs(z - hp.z) > 0.8) { x = hp.x; z = hp.z; }   // (not posed yet)
        else up = Math.max(0, Math.min(L[13], R[13]) - hp.y - 0.1);
      }
      // a dark core of 0.2 m (mostly under the feet), soft out to the 0.35 m radius and a little past it
      const k = 1 + up * 3;
      this._put(x, hp.y, z, a.holder.rotation.y, 0.35 * k, 0.35 * k, 0.35 * k, 0.15 * k, 0.24 * k, 0.6 / (k * k));
    };
    for (const p of this.people) person(p.a, p.feet);
    if (this.hero) {
      const a = this.hero();
      if (a !== this._heroA) { this._heroA = a; this._heroFeet = [a.root.getObjectByName('FootL'), a.root.getObjectByName('FootR')]; }
      person(a, this._heroFeet);
    }
    for (const { c, hl, hw } of this.cars) {
      const p = c.root.position;
      if (!c.root.parent || !near(p)) continue;
      this._put(p.x, p.y, p.z, c.root.rotation.y, hl, hw, 0.55, 0.1, 0.35, 0.65);
    }
    const b = this.ball;
    if (b && b.state !== 'held' && near(b.pos)) {
      const g = b.floorAt(b.pos.x, b.pos.z, b.pos.y), up = Math.max(0, b.pos.y - 0.12 - g);
      const k = 1 + up * 1.5;
      this._put(b.pos.x, g, b.pos.z, 0, 0.12 * k, 0.12 * k, 0.12 * k, 0.06 * k, 0.08 * k, 0.5 / (k * k));
    }
    this.mesh.instanceMatrix.needsUpdate = true;
    this.shape.needsUpdate = true;
    this.soft.needsUpdate = true;
  }
}
