// 응원 연습(cheer.js)의 밴드를 트는 곳: cheersynth.js 가 계산한 악기 소리를 Web Audio 버퍼로 두고, cheersong.js 의
// 음표마다 하나씩 튼다(버퍼 하나와 게인 하나라, 음마다 오실레이터를 여럿 세우던 때보다 가볍다).
//  - 악기마다 제 크기로 모아 버스 컴프레서 하나를 거친다(큰북이 칠 때 다른 악기가 함께 눌려 한 덩어리로 들림)
//  - 악기마다 정한 만큼을 앞마당의 울림(ConvolverNode)으로 보낸다
import { MIX, partsOf, make, needsOf, roomIR } from './cheersynth.js';

export class Band {
  constructor(sound) {
    this.sound = sound;
    this.kit = new Map();            // id → { buf: AudioBuffer, len (s asked for) }
    this.lanes = new Map();
  }

  // the buffer of an id at least len long (made now if it is not there: a few ms)
  buffer(id, len = 0) {
    const ctx = this.sound.ctx, have = this.kit.get(id);
    if (have && have.len >= len) return have.buf;
    const raw = make(id, len, ctx.sampleRate);
    if (!raw) return null;
    const buf = ctx.createBuffer(raw.ch.length, raw.ch[0].length, raw.sr);
    raw.ch.forEach((x, c) => buf.copyToChannel(x, c));
    this.kit.set(id, { buf, len });
    return buf;
  }

  // make what a chart's events need before its count, a buffer at a time so the frames go on
  // (about a quarter of a second in all at a desk, a second or two on a phone)
  async prepare(events) {
    if (!this.sound?.ctx) return;
    let t = performance.now();
    for (const [id, len] of needsOf(events)) {
      this.buffer(id, len);
      if (performance.now() - t > 5) { await new Promise((r) => setTimeout(r)); t = performance.now(); }
    }
    this.ensure();
  }

  // the instruments' gains into the compressor, their sends into the room; all of it out of this.out
  ensure() {
    const S = this.sound, ctx = S.ctx;
    if (this.out && this.out.context === ctx) return this.out;
    const out = this.out = ctx.createGain();
    const comp = ctx.createDynamicsCompressor();
    Object.assign(comp.threshold, { value: -18 }); Object.assign(comp.knee, { value: 10 }); Object.assign(comp.ratio, { value: 2.5 });
    Object.assign(comp.attack, { value: 0.02 }); Object.assign(comp.release, { value: 0.15 });
    const sum = S._gain(1);
    S._chain(sum, comp, S._gain(0.9), out);
    const ir = roomIR(ctx.sampleRate), room = this.room = ctx.createConvolver();
    room.normalize = false;
    const buf = ctx.createBuffer(2, ir.ch[0].length, ir.sr);
    ir.ch.forEach((x, c) => buf.copyToChannel(x, c));
    room.buffer = buf;
    room.connect(out);
    this.inst = {};
    this.lanes.clear();
    for (const [name, m] of Object.entries(MIX)) {
      const g = this.inst[name] = S._gain(m.g);
      g.connect(sum);
      this.send(g, m.room);
    }
    return out;
  }

  // some of a node's sound into the room
  send(node, amount) {
    const g = this.sound._gain(amount);
    node.connect(g); g.connect(this.room);
  }

  // where an instrument's mono notes sit between the speakers
  lane(inst, pan) {
    const ctx = this.sound.ctx;
    if (!pan || !ctx.createStereoPanner) return this.inst[inst];
    const key = inst + pan;
    let p = this.lanes.get(key);
    if (!p) { p = ctx.createStereoPanner(); p.pan.value = pan; p.connect(this.inst[inst]); this.lanes.set(key, p); }
    return p;
  }

  // one event of cheersong.js's bandOf at the audio clock's `at`
  play(e, at) {
    const ctx = this.sound.ctx;
    this.ensure();
    for (const p of partsOf(e)) {
      const buf = this.buffer(p.id, p.len);
      if (!buf) continue;
      const src = ctx.createBufferSource(), g = ctx.createGain();
      src.buffer = buf;
      g.gain.value = p.g;
      src.connect(g);
      g.connect(buf.numberOfChannels === 1 ? this.lane(p.inst, p.pan) : this.inst[p.inst]);
      src.start(at);
      if (p.off != null) {           // a held note let go
        g.gain.setValueAtTime(p.g, at + p.off);
        g.gain.setTargetAtTime(0, at + p.off, p.rel / 3);
        src.stop(at + p.off + p.rel * 2.5);
      }
    }
  }
}
