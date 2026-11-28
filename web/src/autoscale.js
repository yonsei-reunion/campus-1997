// The render scale (the renderer's pixel ratio), stepped down where the frames come slowly and the pixels are why.
// A laptop's built-in GPU on a high-density screen drew the walk at 13 frames a second at the usual 1.5 and at 26 at
// 1.0 (2560 x 1440, TECH_NOTE.md 「성능: 받는 양 · 게임 중 측정 (2026-11-28)」); where the CPU is the limit, a smaller
// picture is no faster.
//   - frame(on) is called once per drawn frame; on: the walk or the tour is going (not the title card, not paused,
//     not a hidden tab, not the trailer's hand-stepped frames)
//   - the frame times of WINDOW ms at a time give a median; two slow medians in a row (slower than `slow` ms a frame)
//     step the scale down once. slow: 40 ms on a computer (under 25 frames a second: the picture's sharpness is worth
//     more than a few frames there). Phones are left alone for now (main.js gives them no lower step): a warm
//     Pixel 10 Pro XL drew 백양로 at 28 - 41 frames a second at 1.5 and at 49 at 1.0, but one step of 1.25 gained
//     less than the test asks and was undone; they need one step straight to 1.0 and a threshold of their own
//   - the next full window is the test: unless its median is BETTER (x GAIN) than before, the step is undone and the
//     scale left alone from then on (the pixels were not the limit); else it stays, and the watch goes on
//   - never back up by itself: a view that had to come down would only swing between the two
const WINDOW = 2500, GAIN = 0.9, WAIT = 5000;
const STEPS = [1.25, 1, 0.8];

export class AutoScale {
  // start: the scale the page begins with; floor: the lowest it may go to; slow: ms a frame (above);
  // apply(scale): sets it; told(scale): after a step that stayed
  constructor(start, floor, slow, apply, told = () => {}) {
    this.slowMs = slow;
    this.levels = [start, ...STEPS.filter((v) => v < start - 0.05 && v >= floor - 1e-6)];
    this.i = 0;
    this.apply = apply;
    this.told = told;
    this.dts = [];
    this.span = 0;          // ms in the window so far
    this.slow = 0;          // slow windows in a row
    this.test = null;       // the median before a step being tried
    this.skip = 0;          // windows left out (the first after the walk begins or a step: the resize, the history)
    this.done = this.levels.length < 2;
    this.last = 0;
    this.since = 0;         // ms watched since the walk went on
    this.log = [];          // [seconds watched, median ms, scale]: for the tools (window.__y97.autoScale)
  }
  get scale() { return this.levels[this.i]; }
  frame(on, now = performance.now()) {
    if (this.done) return;
    const dt = now - this.last;
    this.last = now;
    if (!on || dt > 500) { this.dts.length = 0; this.span = 0; if (!on) { this.slow = 0; this.since = 0; } return; }
    this.since += dt;
    if (this.since < WAIT) return;                    // (the walk just begun: its cells and shaders still coming)
    this.dts.push(dt);
    this.span += dt;
    if (this.span < WINDOW) return;
    const med = this.dts.sort((a, b) => a - b)[this.dts.length >> 1];
    this.dts.length = 0;
    this.span = 0;
    this.log.push([Math.round(this.since / 1000), +med.toFixed(1), this.scale]);
    if (this.skip > 0) { this.skip--; return; }
    if (this.test !== null) {
      if (med > this.test * GAIN) {                   // no faster: back, and no more
        this.i--;
        this.apply(this.scale);
        this.done = true;
      } else {
        this.told(this.scale);
        if (this.i === this.levels.length - 1) this.done = true;
      }
      this.test = null;
      this.slow = 0;
      return;
    }
    if (med <= this.slowMs) { this.slow = 0; return; }
    if (++this.slow < 2) return;
    this.test = med;
    this.i++;
    this.apply(this.scale);
    this.skip = 1;
  }
}
