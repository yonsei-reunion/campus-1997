// 캐릭터 크게 보기 (the title card's 「크게 보기」): the hero picked, large and turning slowly, in a window over the
// card. Thirteen portraits in one row are 60 pixels wide each; here one person has the window. Drag turns them, the
// arrows (and ← →) go to the next hero, who is picked on the card as well; 「얼굴 가까이」 shows the head and the
// shoulders, 「걷는 모습」 the walk. A renderer of its own, made when the window opens and let go when it shuts
// (loaded with this file, on the first press).
import * as THREE from 'three';
import { PEOPLE, HERO, heroScale, play } from './characters.js';
import './herozoom.css';

let shut = null;

export function openHeroZoom({ cast, ids, id, onPick }) {
  shut?.();
  const el = document.createElement('div');
  el.id = 'herozoom';
  el.setAttribute('role', 'dialog');
  el.setAttribute('aria-modal', 'true');
  el.setAttribute('aria-label', '캐릭터 크게 보기');
  el.innerHTML = `<article>
    <div class="stage"><canvas></canvas>
      <button type="button" class="prev" aria-label="앞 사람">‹</button>
      <button type="button" class="next" aria-label="다음 사람">›</button>
      <span class="count"></span>
    </div>
    <div class="cap">
      <div><b></b><small></small></div>
      <div class="btns">
        <button type="button" class="face">얼굴 가까이</button>
        <button type="button" class="walk">걷는 모습</button>
        <button type="button" class="close">닫기</button>
      </div>
    </div>
  </article>`;
  document.body.appendChild(el);
  const $ = (s) => el.querySelector(s);
  const stage = $('.stage'), canvas = $('canvas');

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.setClearColor(0x000000, 0);
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8a7a66, 2.2));
  const sun = new THREE.DirectionalLight(0xffffff, 2.4);
  sun.position.set(2, 4, 3);
  scene.add(sun);
  // (the soft shade under the feet)
  const c2 = document.createElement('canvas');
  c2.width = c2.height = 128;
  const g2 = c2.getContext('2d'), grad = g2.createRadialGradient(64, 64, 4, 64, 64, 62);
  grad.addColorStop(0, 'rgba(40,36,30,.42)'); grad.addColorStop(1, 'rgba(40,36,30,0)');
  g2.fillStyle = grad; g2.fillRect(0, 0, 128, 128);
  const shadeMap = new THREE.CanvasTexture(c2);
  const shade = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 0.8).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({ map: shadeMap, transparent: true, depthWrite: false, toneMapped: false }));
  const pivot = new THREE.Group();
  pivot.add(shade);
  scene.add(pivot);
  const camera = new THREE.PerspectiveCamera(24, 1, 0.1, 60);

  let a = null, head = null, face = false, walk = false, yaw = 0.4, dragUntil = 0, raf = 0;
  const _v = new THREE.Vector3();
  const show = (to) => {
    id = to;
    if (a) { pivot.remove(a.holder); a.mixer.stopAllAction(); }
    a = cast.make(id, undefined, null, heroScale(id));
    pivot.add(a.holder);
    head = a.root.getObjectByName('Head');
    play(a, walk ? 'walk' : 'idle', { fade: 0 });
    const h = HERO[id];
    $('b').textContent = `${h.name} · ${h.college}`;
    $('small').textContent = `${PEOPLE[id]}${h.height ? ` · ${Math.round(h.height * 100)} cm` : ''} · ${h.place} 앞에서 출발`;
    $('.count').textContent = `${ids.indexOf(id) + 1} / ${ids.length}`;
  };
  const step = (d) => { const to = ids[(ids.indexOf(id) + d + ids.length) % ids.length]; show(to); onPick?.(to); };
  $('.prev').addEventListener('click', () => step(-1));
  $('.next').addEventListener('click', () => step(1));
  $('.face').addEventListener('click', (e) => { face = !face; e.currentTarget.textContent = face ? '온몸 보기' : '얼굴 가까이'; });
  $('.walk').addEventListener('click', (e) => {
    walk = !walk;
    e.currentTarget.textContent = walk ? '서 있는 모습' : '걷는 모습';
    play(a, walk ? 'walk' : 'idle', { fade: 0.3 });
  });

  // drag: turn (the slow turning waits a while after it)
  let x0 = null;
  stage.addEventListener('pointerdown', (e) => { if (e.target.closest('button')) return; x0 = e.clientX; stage.setPointerCapture?.(e.pointerId); });
  stage.addEventListener('pointermove', (e) => {
    if (x0 === null) return;
    yaw += (e.clientX - x0) * 0.012;
    x0 = e.clientX;
    dragUntil = performance.now() + 2500;
  });
  const up = () => { x0 = null; };
  stage.addEventListener('pointerup', up);
  stage.addEventListener('pointercancel', up);

  const clock = new THREE.Clock();
  const frame = () => {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(clock.getDelta(), 0.1);
    const w = stage.clientWidth, h = stage.clientHeight;
    if (w < 2 || h < 2) return;
    const pr = renderer.getPixelRatio();
    if (canvas.width !== Math.round(w * pr) || canvas.height !== Math.round(h * pr)) renderer.setSize(w, h, false);
    if (performance.now() > dragUntil && x0 === null) yaw += dt * 0.35;
    pivot.rotation.y = yaw;
    a.mixer.update(dt);
    // the whole person: 2.1 m of height, or less of it across a narrow window; from near the head and the shoulders
    camera.aspect = w / h;
    const top = (id.startsWith('woman') ? 1.61 : 1.73) * a.tall;
    const tall = face ? 0.62 : 2.1, wide = face ? 0.5 : walk ? 1.25 : 0.92;
    const d = Math.max(tall, wide / camera.aspect) / 2 / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const y = face ? top - 0.2 : 0.9;
    // (from near: the head in the middle, wherever the pose holds it)
    pivot.updateMatrixWorld(true);
    const x = face && head ? head.getWorldPosition(_v).x : 0;
    camera.position.set(x, y + (face ? 0.02 : 0.12), d);
    camera.lookAt(x, y, 0);
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
  };

  // (the keys stay in the window: the title card behind it would take Enter for 「산책하기」)
  const onKey = (e) => {
    e.stopPropagation();
    if (e.code === 'Escape') close();
    else if (e.code === 'ArrowLeft') step(-1);
    else if (e.code === 'ArrowRight') step(1);
    else return;
    e.preventDefault();
  };
  const close = () => {
    if (shut !== close) return;
    shut = null;
    cancelAnimationFrame(raf);
    removeEventListener('keydown', onKey, true);
    a?.mixer.stopAllAction();
    shade.geometry.dispose(); shade.material.dispose(); shadeMap.dispose();
    renderer.dispose();
    renderer.forceContextLoss();          // (free the extra WebGL context now, not when it is garbage collected)
    el.remove();
  };
  shut = close;
  addEventListener('keydown', onKey, true);
  $('.close').addEventListener('click', close);
  el.addEventListener('click', (e) => { if (e.target === el) close(); });
  show(id);
  frame();
  $('.close').focus({ preventScroll: true });
  return close;
}
