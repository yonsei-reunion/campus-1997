// 응원 연습(cheer.js)의 음악: 아카라카 구호로 열고, 연세대학교 「응원가」(용맹있게 앞에 나가라 굳센 연세 용사들아)를
// 기타 · 베이스 · 키보드 · 드럼으로.
//  - 가락은 학교 홈페이지 「노래」에 실린 응원가 악보(yonsei.ac.kr/sites/sc/down/img_rooterssong.jpg)를 옮긴 것:
//    내림가장조, 4/4, 열세 마디. 학교 음원(song_03.mp3)의 빠르기는 약 100 BPM 으로 「보통」과 같다. 가사는 싣지 않는다
//  - 구호의 글은 학교 홈페이지 「구호」(yonsei.ac.kr/sc/240/subview.do)의 첫 구호, 장단은 이 게임이 붙인 것
//  - 화음, 가락 아래의 화성 성부, 악기의 짜임, 판마다 마디 수를 채우는 순서(구호 여섯 마디, 되풀이, 끝 화음)는
//    이 게임이 붙인 것. 악기 소리는 cheersynth.js 가 만든다
//  - 박자표(cheercharts.js)는 그대로라 순위 서버의 검사와 지난 기록은 바뀌지 않는다
// three.js 를 읽지 않는 자료라 node 에서도 돌린다.

// note names → MIDI (내림가장조라 B · E · A · D 는 늘 내림)
const PC = { C: 0, Db: 1, D: 2, Eb: 3, E: 4, F: 5, G: 7, Ab: 8, A: 9, Bb: 10, B: 11 };
const midi = (n) => { const [, p, o] = n.match(/^([A-G]b?)(\d)$/); return PC[p] + 12 * (+o + 1); };
const len = (s) => (s.includes('/') ? s.split('/')[0] / s.split('/')[1] : +s);

// the song, bar by bar: the tune (note length in beats; 1/3 is a triplet's eighth), a chord on each beat, and the
// second voice under the tune (thirds and sixths, on the chord where the tune rests on it)
const SONG = [
  ['Ab4 1, Ab4 1, C5 1.5, Bb4 .5', 'Ab Ab Ab Ab', 'Eb4 1, Eb4 1, Ab4 1.5, G4 .5'],                              // 용맹있게
  ['Ab4 .75, Bb4 .25, Ab4 .75, F4 .25, Eb4 1, Eb4 1', 'Ab Ab Ab Ab', 'Eb4 .75, G4 .25, Eb4 .75, Db4 .25, C4 1, C4 1'],   // 앞에 나-가라
  ['Db5 1, Db5 1, C5 1, C5 1', 'Db Db Ab Ab', 'F4 1, F4 1, Eb4 1, Eb4 1'],                                      // 굳센 연세
  ['Bb4 1, Bb4 .75, C5 .25, Bb4 2', 'Eb Eb Eb Eb7', 'G4 1, G4 .75, Ab4 .25, G4 2'],                             // 용사들아
  ['Ab4 1, Ab4 1, C5 1.5, Bb4 .5', 'Ab Ab Ab Ab', 'Eb4 1, Eb4 1, Ab4 1.5, G4 .5'],                              // 너의 정성
  ['Ab4 .75, Bb4 .25, Ab4 .75, F4 .25, Eb4 1, Eb4 1', 'Ab Ab Ab Ab', 'Eb4 .75, G4 .25, Eb4 .75, Db4 .25, C4 1, C4 1'],   // 힘을 합하여라
  ['Db5 1, Db5 1, C5 1, C5 1', 'Db Db Ab Ab', 'F4 1, F4 1, Eb4 1, Eb4 1'],                                      // 너의 대적
  ['Bb4 .75, Bb4 .25, C5 .75, Db5 .25, Eb5 1.5, Db5 .5', 'Bbm Bbm Eb Eb7', 'F4 .75, F4 .25, Ab4 .75, Bb4 .25, Bb4 1.5, G4 .5'],   // 물러나가서 흩
  ['C5 1, Bb4 1, Ab4 2', 'Ab Eb Ab Ab', 'Ab4 1, G4 1, Eb4 2'],                                                  // 어지네
  ['Ab4 1, G4 1, F4 1, Eb4 1', 'Ab Eb Db Eb', 'C4 1, Bb3 1, Ab3 1, G3 1'],                                      // 라라라라
  ['Ab4 1, G4 1, F4 1, Eb4 1', 'Ab Eb Db Eb', 'C4 1, Bb3 1, Ab3 1, G3 1'],                                      // 연세연세
  ['Ab4 .75, Ab4 .25, Bb4 1/3, Ab4 1/3, Bb4 1/3, C5 .75, Bb4 .25, Db5 .75, Db5 .25', 'Ab Bbm Ab Eb7',
    'Eb4 .75, Eb4 .25, F4 1/3, F4 1/3, F4 1/3, Ab4 .75, G4 .25, G4 .75, G4 .25'],                               // 산기운-을 합하여서
  ['C5 .75, C5 .25, Bb4 .75, Bb4 .25, Ab4 2', 'Ab Eb7 Ab Ab', 'Ab4 .75, Ab4 .25, G4 .75, G4 .25, Eb4 2'],       // 앞에나가라
].map(([mel, ch, harm]) => {
  const line = (s) => s.split(',').map((x) => { const [n, d] = x.trim().split(/\s+/); return [midi(n), len(d)]; });
  return { mel: line(mel), ch: ch.split(' '), harm: line(harm) };
});
export const SONG_BARS = SONG.length;
// where the arrangement turns: 용맹있게 · 너의 정성 · 라라라라 · 산기운을 (a crash there, a fill before it)
const TURN = new Set([0, 4, 9, 11]);
// how hard the band plays each bar, the first time through and after: 1 the guitars muted, the hats closed, the tune
// alone; 2 the second voice, the guitars opening on the chords; 3 everything open; 'hits': a chord on every beat
const LEVEL = [[1, 1, 1, 1, 2, 2, 2, 2, 2, 'hits', 'hits', 3, 3], [2, 2, 2, 2, 3, 3, 3, 3, 3, 'hits', 'hits', 3, 3]];

// the chords: the root (MIDI, bass octave) and the keyboard's voicing round middle C
const CHORD = {
  Ab: { root: 32, keys: [56, 60, 63] },
  Db: { root: 37, keys: [56, 61, 65] },
  Eb: { root: 39, keys: [55, 58, 63] },
  Eb7: { root: 39, keys: [55, 61, 63] },
  Bbm: { root: 34, keys: [53, 58, 61] },
};
const UNDER = { 32: 31, 34: 32, 37: 36, 39: 37 };      // the bass's step up into a root: the scale's note under it
function rng(a) {       // (util.js's mulberry: the players' small unevenness, the same every time)
  return () => {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// 아카라카 구호(학교 홈페이지 「구호」의 첫 구호): the words as the page gives them, the beat is the game's (no source
// writes it down): six bars on sixteenths, the leader's call alone, then the block. Bar by bar:
// [the bubble's line, [[sixteenth, syllable], …], the sixteenths where the drums and the band hit with it]
const CHANT = [
  ['아카라카!', [[0, '아'], [2, '카'], [4, '라'], [6, '카']], []],
  ['아카라카칭 아카라카쵸', [[0, '아'], [1, '카'], [2, '라'], [3, '카'], [4, '칭'], [8, '아'], [9, '카'], [10, '라'], [11, '카'], [12, '쵸']], [4, 12]],
  ['아카라카 칭칭 쵸쵸쵸', [[0, '아'], [1, '카'], [2, '라'], [3, '카'], [4, '칭'], [6, '칭'], [8, '쵸'], [10, '쵸'], [12, '쵸']], [4, 6, 8, 10, 12]],
  ['랄랄라 시스붐바', [[0, '랄'], [2, '랄'], [4, '라'], [8, '시'], [9, '스'], [10, '붐'], [12, '바']], [12]],
  ['연세 선수 라플라', [[0, '연'], [2, '세'], [4, '선'], [6, '수'], [8, '라'], [10, '플'], [12, '라']], [12]],
  ['헤이 연세 야!', [[0, '헤'], [2, '이'], [4, '연'], [6, '세'], [8, '야']], [8]],
];
export const CHANT_BARS = CHANT.length;
// each syllable's sounds for the voice (cheer.js): the consonant before it and the vowel
export const SYL = {
  아: ['', 'a'], 카: ['k', 'a'], 라: ['r', 'a'], 칭: ['ch', 'i'], 쵸: ['ch', 'o'], 랄: ['r', 'a'], 시: ['s', 'i'], 스: ['s', 'eu'],
  붐: ['b', 'u'], 바: ['b', 'a'], 연: ['y', 'eo'], 세: ['s', 'e'], 선: ['s', 'eo'], 수: ['s', 'u'], 플: ['p', 'eu'], 헤: ['h', 'e'],
  이: ['', 'i'], 야: ['y', 'a'],
};

// the bars of a chart of n bars: the chant, the song as many times as fit, then its last two lines or its last
// line, and what is left held on the home chord. Each bar of the song: pass (which time through), turn (the
// arrangement turns here: a crash), level
export function arrange(n) {
  const out = [];
  let pass = 0;
  const song = (i, turn = TURN.has(i)) => out.push({ ...SONG[i], i, turn, level: LEVEL[Math.min(pass, 1)][i] });
  for (let i = 0; i < CHANT.length && out.length < n; i++) out.push({ chant: CHANT[i], i, turn: i === 0 });
  for (; n - out.length >= SONG.length; pass++) for (let i = 0; i < SONG.length; i++) song(i);
  let rest = n - out.length;
  const from = rest >= 6 ? 7 : rest >= 3 ? 10 : 13;
  for (let i = from; i < 13; i++) song(i, i === from || TURN.has(i));
  rest = n - out.length;
  for (let k = 0; k < rest; k++) out.push({ hold: true, ch: ['Ab', 'Ab', 'Ab', 'Ab'], turn: k === 0, last: k === rest - 1 });
  return out;
}

// the band's notes: { t (s from the first bar), kind, m (MIDI), d (s), k (loudness) }
//  drums: kick · snare · snare2 (a fill's stroke) · ghost · tick (the hat closed) · hath (half open) · hato (open) ·
//    cymbal · tom1 · tom2 · tom3 · rim · rim2 (the sticks) · boom (the chant's big drum)
//  gtr (a power chord on m; open: let ring), bass, lead (the tune), harm (the voice under it), keys (a chord)
export function bandOf(bpm, n) {
  const b = 60 / bpm, ev = [], bars = arrange(n), r = rng(1997);
  // (nobody plays like a clock: each note a few ms off and a little louder or softer)
  const push = (t, kind, o = {}, ms = 0) => ev.push({ t: t + (r() - 0.5) * ms / 500, kind, ...o, k: (o.k ?? 1) * (ms ? 0.94 + r() * 0.12 : 1) });
  for (let k = 0; k < 4; k++) push((k - 4) * b, k === 3 ? 'rim2' : 'rim');       // the sticks counting in
  bars.forEach((bar, m) => {
    const t0 = m * 4 * b, next = bars[m + 1], fill = !next || next.turn;
    const at = (beat) => t0 + beat * b;
    if (bar.chant) {
      // the chant: the leader's call bare, then the big drum on every beat under the block and the band on its hits
      const [text, syl, hits] = bar.chant, lead = bar.i === 0;
      push(t0, 'line', { text, lead, d: 4 * b });
      syl.forEach(([q, s], j) => {
        const nq = j + 1 < syl.length ? syl[j + 1][0] : 16;
        push(at(q / 4), 'chant', { syl: s, d: s === '야' ? 1.2 * b : Math.min(0.9, (nq - q) / 4) * b, k: hits.includes(q) ? 1 : 0.8, lead });
      });
      if (lead) return;
      for (let k = 0; k < 4; k++) if (!(fill && k === 3)) push(at(k), 'boom', { k: k ? 0.85 : 1 }, 2);
      for (const q of hits) {
        push(at(q / 4), 'snare', { k: 0.9 }, 2);
        push(at(q / 4), 'gtr', { m: 44, d: b * 0.5, k: 1, open: true }, 3);
        push(at(q / 4), 'bass', { m: 32, d: b * 0.4 }, 3);
      }
      if (fill) {       // into the song: the cymbal on 야, the toms down
        push(at(2), 'cymbal');
        ['tom1', 'tom2', 'tom3'].forEach((tom, i) => push(at(3.25 + i / 4), tom, { k: 0.8 + i * 0.1 }, 2));
      }
      return;
    }
    if (bar.hold) {
      // the home chord let ring under the tune's last note in three parts, a roll on the snare into the end
      if (bar.turn) { push(t0, 'kick'); push(t0, 'cymbal'); push(t0, 'bass', { m: 32, d: 4 * b * 0.95 }); }
      push(t0, 'gtr', { m: 44, d: 4 * b, k: bar.turn ? 1 : 0.8, open: true }, 3);
      push(t0, 'keys', { m: CHORD.Ab.keys, d: 4 * b });
      push(t0, 'lead', { m: 68, d: 4 * b * 0.95 }, 4);
      push(t0, 'harm', { m: 72, d: 4 * b * 0.95 }, 4);
      push(t0, 'harm', { m: 63, d: 4 * b * 0.95 }, 4);
      if (bar.last) {
        for (let i = 4; i < 16; i++) push(at(i / 4), 'snare2', { k: 0.3 + 0.7 * (i / 16) ** 1.5 }, 2);
        push(at(3), 'kick'); push(at(3.5), 'kick', { k: 0.9 });
      }
      return;
    }
    const L = bar.level, hits = L === 'hits', big = fill && (!next || next.hold || next.level === 'hits');
    const fillAt = fill ? (big ? 2 : 3) : 9;       // the beat the fill begins on (the hats stop there)
    // drums: a rock beat that opens up with the level, a crash where the arrangement turns, a fill before the next
    const kicks = hits ? [0, 2, 3.5] : m % 2 ? [0, 1.5, 2] : [0, 2, 2.5];
    for (const beat of kicks) if (beat < fillAt || beat === Math.floor(beat)) push(at(beat), 'kick', { k: beat === Math.floor(beat) ? 1 : 0.8 }, 2);
    for (const beat of [1, 3]) if (beat < fillAt) push(at(beat), 'snare', {}, 2);
    if (L !== 1 && fillAt > 3) push(at(2.75), 'ghost', {}, 3);
    for (let k = 0; k < 8; k++) {
      const beat = k / 2;
      if (beat >= fillAt) break;
      if (hits) { if (k % 2 === 0) push(at(beat), 'hato', {}, 3); }
      else if (L === 3) push(at(beat), k % 2 ? 'tick' : 'hath', { k: k % 2 ? 0.8 : 1 }, 3);
      else if (L === 2 && k === 7 && m % 2) push(at(beat), 'hato', { k: 0.8 }, 3);
      else push(at(beat), 'tick', { k: k % 2 ? 0.6 : 1 }, 3);
    }
    if (bar.turn) push(t0, 'cymbal');
    if (fill && big) {       // two beats: the snare, then down the toms, louder as it goes
      ['snare2', 'snare2', 'tom1', 'tom1', 'tom2', 'tom2', 'tom3', 'tom3'].forEach((kind, i) => push(at(2 + i / 4), kind, { k: 0.6 + 0.4 * i / 7 }, 2));
      push(at(3), 'kick', { k: 0.8 });
    } else if (fill) ['snare2', 'snare2', 'tom1', 'tom2'].forEach((kind, i) => push(at(3 + i / 4), kind, { k: 0.65 + 0.35 * i / 3 }, 2));
    // guitar: muted eighths (1), open on the chords (2), open eighths (3), a chord on each beat (hits)
    for (let k = 0; k < 8; k++) {
      const c = CHORD[bar.ch[k >> 1]], m0 = c.root + 12, change = k % 2 === 0 && (k === 0 ? bar.turn || L === 2 : c.root !== CHORD[bar.ch[(k >> 1) - 1]].root);
      if (hits) { if (k % 2 === 0) push(at(k / 2), 'gtr', { m: m0, d: b * 0.85, k: 0.9, open: true }, 4); continue; }
      if (L === 3) { push(at(k / 2), 'gtr', { m: m0, d: b * 0.5, k: k % 2 ? 0.68 : 0.85, open: true }, 4); continue; }
      if (change) { push(at(k / 2), 'gtr', { m: m0, d: b * 0.95, open: true }, 4); k++; continue; }
      push(at(k / 2), 'gtr', { m: m0, d: b * 0.3, k: k % 2 ? 0.75 : 0.95 }, 4);
    }
    // bass: eighths on the root, up an octave on the last of each half, or a step up into the chord that comes
    for (let k = 0; k < 8; k++) {
      const root = CHORD[bar.ch[k >> 1]].root, to = k === 7 ? (next?.ch ? CHORD[next.ch[0]].root : root) : k % 2 ? CHORD[bar.ch[(k >> 1) + 1]].root : root;
      const mm = hits ? root + (k % 2 ? 12 : 0) : k % 2 && to !== root ? UNDER[to] : root + (k % 4 === 3 ? 12 : 0);
      push(at(k / 2), 'bass', { m: mm, d: b * (hits && k % 2 === 0 ? 0.48 : 0.45), k: k % 2 ? 0.85 : 1 }, 3);
    }
    // keyboard: the tune in the right hand (the second voice with it from level 2), the chord held in the left
    for (const [kind, line] of [['lead', bar.mel], ...(L === 1 ? [] : [['harm', bar.harm]])]) {
      let beat = 0;
      for (const [mm, d] of line) {
        const on = Math.abs(beat - Math.round(beat)) < 0.01;
        push(at(beat), kind, { m: mm, d: d * b * (d >= 1.5 ? 0.96 : d === 1 ? 0.86 : 0.93), k: on ? 1 : 0.88 }, 4);
        beat += d;
      }
    }
    for (let k = 0; k < 4;) {
      let j = k + 1;
      while (j < 4 && bar.ch[j] === bar.ch[k]) j++;
      push(at(k), 'keys', { m: CHORD[bar.ch[k]].keys, d: (j - k) * b * 0.95 });
      k = j;
    }
  });
  // the end: the band on the home chord
  const tEnd = n * 4 * b;
  push(tEnd, 'kick'); push(tEnd, 'cymbal');
  push(tEnd, 'gtr', { m: 44, d: 1.6, k: 1, open: true });
  push(tEnd, 'bass', { m: 32, d: 1.4 });
  push(tEnd, 'keys', { m: [56, 60, 63, 68], d: 1.6 });
  push(tEnd, 'lead', { m: 68, d: 1.4 });
  push(tEnd, 'harm', { m: 72, d: 1.4 });
  push(tEnd, 'harm', { m: 63, d: 1.4 });
  return ev;
}
