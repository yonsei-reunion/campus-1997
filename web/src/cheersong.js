// 응원 연습(cheer.js)의 음악: 아카라카 구호로 열고, 연세대학교 「응원가」(용맹있게 앞에 나가라 굳센 연세 용사들아)를
// 기타 · 베이스 · 키보드 · 드럼으로.
//  - 가락은 학교 홈페이지 「노래」에 실린 응원가 악보(yonsei.ac.kr/sites/sc/down/img_rooterssong.jpg)를 옮긴 것:
//    내림가장조, 4/4, 열세 마디. 학교 음원(song_03.mp3)의 빠르기는 약 100 BPM 으로 「보통」과 같다. 가사는 싣지 않는다
//  - 구호의 글은 학교 홈페이지 「구호」(yonsei.ac.kr/sc/240/subview.do)의 첫 구호, 장단은 이 게임이 붙인 것
//  - 화음, 악기의 짜임, 판마다 마디 수를 채우는 순서(구호 여섯 마디, 되풀이, 끝 화음)는 이 게임이 붙인 것
//  - 박자표(cheercharts.js)는 그대로라 순위 서버의 검사와 지난 기록은 바뀌지 않는다
// three.js 를 읽지 않는 자료라 node 에서도 돌린다.

// note names → MIDI (내림가장조라 B · E · A · D 는 늘 내림)
const PC = { C: 0, Db: 1, D: 2, Eb: 3, E: 4, F: 5, G: 7, Ab: 8, A: 9, Bb: 10, B: 11 };
const midi = (n) => { const [, p, o] = n.match(/^([A-G]b?)(\d)$/); return PC[p] + 12 * (+o + 1); };
const len = (s) => (s.includes('/') ? s.split('/')[0] / s.split('/')[1] : +s);

// the song, bar by bar: the tune (note length in beats; 1/3 is a triplet's eighth) and a chord on each beat
const SONG = [
  ['Ab4 1, Ab4 1, C5 1.5, Bb4 .5', 'Ab Ab Ab Ab'],                         // 용맹있게
  ['Ab4 .75, Bb4 .25, Ab4 .75, F4 .25, Eb4 1, Eb4 1', 'Ab Ab Ab Ab'],      // 앞에 나-가라
  ['Db5 1, Db5 1, C5 1, C5 1', 'Db Db Ab Ab'],                             // 굳센 연세
  ['Bb4 1, Bb4 .75, C5 .25, Bb4 2', 'Eb Eb Eb Eb7'],                       // 용사들아
  ['Ab4 1, Ab4 1, C5 1.5, Bb4 .5', 'Ab Ab Ab Ab'],                         // 너의 정성
  ['Ab4 .75, Bb4 .25, Ab4 .75, F4 .25, Eb4 1, Eb4 1', 'Ab Ab Ab Ab'],      // 힘을 합하여라
  ['Db5 1, Db5 1, C5 1, C5 1', 'Db Db Ab Ab'],                             // 너의 대적
  ['Bb4 .75, Bb4 .25, C5 .75, Db5 .25, Eb5 1.5, Db5 .5', 'Bbm Bbm Eb Eb7'], // 물러나가서 흩
  ['C5 1, Bb4 1, Ab4 2', 'Ab Eb Ab Ab'],                                   // 어지네
  ['Ab4 1, G4 1, F4 1, Eb4 1', 'Ab Eb Db Eb'],                             // 라라라라
  ['Ab4 1, G4 1, F4 1, Eb4 1', 'Ab Eb Db Eb'],                             // 연세연세
  ['Ab4 .75, Ab4 .25, Bb4 1/3, Ab4 1/3, Bb4 1/3, C5 .75, Bb4 .25, Db5 .75, Db5 .25', 'Ab Bbm Ab Eb7'],  // 산기운-을 합하여서
  ['C5 .75, C5 .25, Bb4 .75, Bb4 .25, Ab4 2', 'Ab Eb7 Ab Ab'],             // 앞에나가라
].map(([mel, ch]) => ({
  mel: mel.split(',').map((x) => { const [n, d] = x.trim().split(/\s+/); return [midi(n), len(d)]; }),
  ch: ch.split(' '),
}));
export const SONG_BARS = SONG.length;
const PHRASE = new Set([0, 4, 7, 10]);     // where the song's lines begin

// the chords: the root (MIDI, bass octave) and the keyboard's voicing round middle C
const CHORD = {
  Ab: { root: 32, keys: [56, 60, 63] },
  Db: { root: 37, keys: [56, 61, 65] },
  Eb: { root: 39, keys: [55, 58, 63] },
  Eb7: { root: 39, keys: [55, 61, 63] },
  Bbm: { root: 34, keys: [53, 58, 61] },
};

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
// line, and what is left held on the home chord
export function arrange(n) {
  const out = [], song = (i, phrase = PHRASE.has(i)) => out.push({ ...SONG[i], i, phrase });
  for (let i = 0; i < CHANT.length && out.length < n; i++) out.push({ chant: CHANT[i], i, phrase: i === 0 });
  while (n - out.length >= SONG.length) for (let i = 0; i < SONG.length; i++) song(i);
  let rest = n - out.length;
  const from = rest >= 6 ? 7 : rest >= 3 ? 10 : 13;
  for (let i = from; i < 13; i++) song(i, i === from || PHRASE.has(i));
  rest = n - out.length;
  for (let k = 0; k < rest; k++) out.push({ hold: true, ch: ['Ab', 'Ab', 'Ab', 'Ab'], phrase: k === 0, last: k === rest - 1 });
  return out;
}

// the band's notes: { t (s from the first bar), kind, m (MIDI), d (s), k (loudness) }
//  kick · snare · snare2 · tick · cymbal · rim · rim2 (drums), gtr (power chord on m), bass, lead (the tune), keys (a chord)
export function bandOf(bpm, n) {
  const b = 60 / bpm, ev = [], bars = arrange(n);
  const push = (t, kind, o = {}) => ev.push({ t, kind, ...o });
  for (let k = 0; k < 4; k++) push((k - 4) * b, k === 3 ? 'rim2' : 'rim');       // the sticks counting in
  bars.forEach((bar, m) => {
    const t0 = m * 4 * b, next = bars[m + 1], fill = !next || next.phrase;
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
      for (let k = 0; k < 4; k++) if (!(fill && k === 3)) push(at(k), 'kick', { k: 0.9 });
      for (const q of hits) {
        push(at(q / 4), 'snare', { k: 0.8 });
        push(at(q / 4), 'gtr', { m: 44, d: b * 0.5, k: 1 });
        push(at(q / 4), 'bass', { m: 32, d: b * 0.4 });
      }
      if (fill) { push(at(2), 'cymbal'); for (let i = 1; i < 4; i++) push(at(3 + i / 4), 'snare2'); }
      return;
    }
    if (bar.hold) {
      // the home chord let ring, a roll on the snare into the end
      if (bar.phrase) {
        push(t0, 'kick'); push(t0, 'cymbal');
        push(t0, 'gtr', { m: 44, d: 4 * b, k: 1, open: true });
        push(t0, 'bass', { m: 32, d: 4 * b * 0.95 });
        push(t0, 'keys', { m: CHORD.Ab.keys, d: 4 * b });
        push(t0, 'lead', { m: 68, d: 4 * b * 0.9 });
      } else {
        push(t0, 'gtr', { m: 44, d: 4 * b, k: 0.8, open: true });
        push(t0, 'keys', { m: CHORD.Ab.keys, d: 4 * b });
      }
      if (bar.last) for (let i = 4; i < 16; i++) push(at(i / 4), 'snare2', { k: 0.4 + 0.6 * i / 16 });
      return;
    }
    // drums: a rock beat, a crash where a line begins and a fill before the next
    for (let k = 0; k < 8; k++) {
      const beat = k / 2;
      if (k === 0 || k === 4 || k === 5) push(at(beat), 'kick', { k: k === 5 ? 0.7 : 1 });
      if (k === 2 || k === 6) push(at(beat), 'snare');
      if (!(fill && k >= 6)) push(at(beat), 'tick', { k: k % 2 ? 0.7 : 1 });
    }
    if (bar.phrase) push(t0, 'cymbal');
    if (fill) for (let i = 1; i < 4; i++) push(at(3 + i / 4), 'snare2');
    // guitar: eighths on the chord, muted, open on a line's first beat
    for (let k = 0; k < 8; k++) {
      const c = CHORD[bar.ch[k >> 1]];
      if (bar.phrase && k === 1) continue;
      const open = bar.phrase && k === 0;
      push(at(k / 2), 'gtr', { m: c.root + 12, d: open ? b : b * 0.3, k: open ? 1 : k % 2 ? 0.7 : 0.9, open });
    }
    // bass: eighths on the root, up an octave on the last of each half
    for (let k = 0; k < 8; k++) {
      const c = CHORD[bar.ch[k >> 1]];
      push(at(k / 2), 'bass', { m: c.root + (k % 4 === 3 ? 12 : 0), d: b * 0.45 });
    }
    // keyboard: the tune in the right hand, the chord held in the left while it lasts
    let beat = 0;
    for (const [mm, d] of bar.mel) { push(at(beat), 'lead', { m: mm, d: d * b * 0.9 }); beat += d; }
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
  return ev;
}
