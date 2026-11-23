"""캠퍼스 달리기 홍보 영상(1분): intro.mjs --segments race_segments.js 가 찍은 장면을 잇고 소리를 붙여 MP4 로.

  .venv/bin/python tools/trailer/race_video.py <녹화 폴더> trailer/race.mp4 [--no-audio] [--crf 18]

- 순서와 자르는 곳은 아래 CLIPS. 장면 사이는 0.4 초 겹쳐 번지게(XF) 잇는다. 자막은 프레임에 이미 들어 있다.
- 소리:
  - 배경 음악은 여기서 합성한다(이 영상만의 가락. 가장조 132 BPM). 「출발!」에 첫 박이 오게 맞추고, 그 앞(제목 ·
    카운트다운)은 깔리는 화음만, 결승(「도착!」) 뒤는 북 없이 끝 화음까지
  - 카운트다운 · 출발 · 문 · 결승의 신호음은 게임(web/src/audio.js cue)과 같은 소리로 합성해 meta.json 의 표시(n3 n2 n1
    gobig gate fin)에 놓는다
  - 뛰는 동안 발소리 · 바람 · 새소리: tools/trailer/race_audio.mjs 가 녹음한 <녹화 폴더>/audio/run.wav
- <녹화 폴더>/seq/ 에 이은 프레임(심볼릭 링크, 번지는 곳만 새 그림)을, <녹화 폴더>/race.wav 에 소리를 둔다.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import wave

import numpy as np
from PIL import Image

SRC = os.path.abspath(sys.argv[1])
OUT = os.path.abspath(sys.argv[2])
NO_AUDIO = '--no-audio' in sys.argv
CRF = sys.argv[sys.argv.index('--crf') + 1] if '--crf' in sys.argv else '18'
FPS = 30
XF = 12
SR = 48000

# (장면, 시작, 끝): None 은 처음 · 끝, ('t', 초), ('mark', 이름, 더할 초)
CLIPS = [
    ('baek', None, ('mark', 'jump', 0)),             # 제목 → 3 · 2 · 1 · 출발! → 백양로
    ('forest', None, None),                          # 청송대 숲길
    ('town', None, None),                            # 신촌 로터리 → 연세로
    ('baek', ('mark', 'jump', 1.6), None),           # 결승 · 결과 창
    ('end', None, None),                             # 코스 다섯 가지 → 제목 · 주소
]
FADE_IN, FADE_OUT = 0.4, 1.2


def meta(seg):
    return json.load(open(os.path.join(SRC, seg, 'meta.json')))


def frame_of(seg, spec, default):
    if spec is None:
        return default
    if spec[0] == 't':
        return round(spec[1] * FPS)
    for m in meta(seg)['marks']:
        if spec[1] in m['mark'].split(','):
            return m['frame'] + round(spec[2] * FPS)
    raise SystemExit(f'{seg}: no mark {spec[1]}')


# ---------------------------------------------------------------- 프레임을 잇기
clips = []
for seg, a, b in CLIPS:
    n = meta(seg)['frames']
    clips.append((seg, max(0, frame_of(seg, a, 0)), min(n, frame_of(seg, b, n))))
seq = os.path.join(SRC, 'seq')
shutil.rmtree(seq, ignore_errors=True)
os.makedirs(seq)
path = lambda seg, i: os.path.join(SRC, seg, f'{i:05d}.jpg')
out_i = 0
starts = []
for k, (seg, fa, fb) in enumerate(clips):
    first = fa + (XF if k else 0)
    starts.append((out_i - (XF if k else 0)) / FPS)
    last = fb - (XF if k + 1 < len(clips) else 0)
    for i in range(first, last):
        os.symlink(path(seg, i), os.path.join(seq, f'{out_i:06d}.jpg'))
        out_i += 1
    if k + 1 < len(clips):
        nseg, na, _ = clips[k + 1]
        for j in range(XF):
            u = (j + 1) / (XF + 1)
            u = u * u * (3 - 2 * u)
            im = Image.blend(Image.open(path(seg, last + j)).convert('RGB'), Image.open(path(nseg, na + j)).convert('RGB'), u)
            im.save(os.path.join(seq, f'{out_i:06d}.jpg'), quality=95)
            out_i += 1
TOTAL = out_i / FPS
ends = starts[1:] + [TOTAL]
print(f'{out_i} frames, {TOTAL:.1f} s')
for (seg, fa, fb), s, e in zip(clips, starts, ends):
    print(f'  {s:6.1f} - {e:6.1f}  {seg} [{fa}:{fb}]')


def marks_at(name):
    """표시 name 이 영상에 들어간 때들 (s)."""
    out = []
    for k, (seg, fa, fb) in enumerate(clips):
        for m in meta(seg)['marks']:
            if name in m['mark'].split(',') and fa <= m['frame'] < fb:
                out.append(starts[k] + (m['frame'] - fa) / FPS)
    return sorted(set(round(t, 4) for t in out))


def span(name):
    ks = [k for k, c in enumerate(clips) if c[0] == name]
    return starts[ks[0]], ends[ks[-1]]


def env(n, spans, fade=0.8):
    t = np.arange(n) / SR
    g = np.zeros(n)
    for a, b in spans:
        g = np.maximum(g, np.clip((t - a + fade / 2) / fade, 0, 1) * np.clip((b - t + fade / 2) / fade, 0, 1))
    return g


def load(name):
    p = os.path.join(SRC, 'audio', name + '.wav')
    if not os.path.exists(p):
        print('no', p)
        return None
    w = wave.open(p)
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, w.getnchannels()).astype(np.float64) / 32768
    assert w.getframerate() == SR
    return x if x.shape[1] == 2 else np.repeat(x, 2, axis=1)


def looped(x, n, skip=2.0, xf=1.5):
    x = x[int(skip * SR):]
    k = int(xf * SR)
    body = x[:-k].copy()
    ramp = np.linspace(0, 1, k)[:, None]
    body[:k] = body[:k] * ramp + x[-k:] * (1 - ramp)
    return np.tile(body, (n // len(body) + 1, 1))[:n]


# ---------------------------------------------------------------- 소리 만들기
rng = np.random.default_rng(97)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)


def adsr(n, a, d, s, r, hold):
    t = np.arange(n) / SR
    g = np.where(t < a, t / max(a, 1e-4), np.where(t < a + d, 1 - (1 - s) * (t - a) / d, s))
    return g * np.clip((hold + r - t) / r, 0, 1)


def saw(f, t, k=12):
    return sum(np.sin(2 * math.pi * f * j * t) / j for j in range(1, k + 1)) * 0.55


def sq(f, t, k=7):
    return sum(np.sin(2 * math.pi * f * j * t) / j for j in range(1, 2 * k, 2)) * 0.8


def inst(kind, m=0, dur=0.2):
    if kind == 'kick':
        n = int(0.42 * SR); t = np.arange(n) / SR
        ph = 2 * math.pi * np.cumsum(45 + 110 * np.exp(-t * 28)) / SR
        return np.sin(ph) * np.exp(-t * 7.5) + 0.25 * rng.standard_normal(n) * np.exp(-t * 180)
    if kind == 'snare':
        n = int(0.3 * SR); t = np.arange(n) / SR
        x = 0.7 * rng.standard_normal(n) * np.exp(-t * 16)
        x = x - np.concatenate([[0], x[:-1]]) * 0.6                     # (위쪽으로)
        return x + 0.5 * np.sin(2 * math.pi * 185 * t) * np.exp(-t * 22)
    if kind == 'hat':
        n = int(0.09 * SR); t = np.arange(n) / SR
        x = rng.standard_normal(n)
        x = x - np.concatenate([[0], x[:-1]])
        return 0.32 * x * np.exp(-t * 55)
    if kind == 'crash':
        n = int(2.2 * SR); t = np.arange(n) / SR
        x = rng.standard_normal(n)
        x = x - np.concatenate([[0], x[:-1]])
        return 0.35 * x * np.exp(-t * 2.2)
    f = hz(m)
    if kind == 'bass':
        n = int((dur + 0.05) * SR); t = np.arange(n) / SR
        return (np.sin(2 * math.pi * f * t) + 0.5 * saw(f, t, 5) * np.exp(-t * 9)) * adsr(n, 0.004, 0.08, 0.7, 0.04, dur)
    if kind == 'stab':
        n = int((dur + 0.15) * SR); t = np.arange(n) / SR
        return sum(saw(f * d, t, 9) for d in (0.997, 1.0, 1.004)) / 3 * adsr(n, 0.005, 0.12, 0.35, 0.12, dur)
    if kind == 'lead':
        n = int((dur + 0.25) * SR); t = np.arange(n) / SR
        vib = 1 + 0.004 * np.sin(2 * math.pi * 5.5 * t) * np.clip(t / 0.3, 0, 1)
        ph = 2 * math.pi * np.cumsum(f * vib) / SR
        return (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)) * adsr(n, 0.01, 0.1, 0.75, 0.2, dur)
    if kind == 'pluck':
        n = int((dur + 0.4) * SR); t = np.arange(n) / SR
        return (np.sin(2 * math.pi * f * t) + 0.4 * np.sin(4 * math.pi * f * t) * np.exp(-t * 8)) * np.exp(-t * 6) * np.clip(t / 0.003, 0, 1)
    if kind == 'pad':
        n = int((dur + 1.2) * SR); t = np.arange(n) / SR
        return sum(saw(f * d, t, 6) for d in (0.995, 1.0, 1.005)) / 3 * adsr(n, 0.6, 0.5, 0.8, 1.2, dur)
    raise ValueError(kind)


# 게임의 신호음(web/src/audio.js cue): 카운트 · 문 880 Hz 사각파 0.12 s, 출발 1320 Hz 0.32 s, 결승 톱니 196 + 198.5 Hz 0.85 s
def cue(what):
    if what == 'buzzer':
        n = int(1.0 * SR); t = np.arange(n) / SR
        return sum(saw(f, t, 14) for f in (196, 198.5)) * 0.07 * 2.2 * adsr(n, 0.01, 0.01, 1, 0.12, 0.85)
    f, hold = (1320, 0.32) if what == 'go' else (880, 0.12)
    n = int((hold + 0.06) * SR); t = np.arange(n) / SR
    return sq(f, t) * 0.05 * 2.6 * adsr(n, 0.004, 0.01, 1, 0.05, hold)


BPM = 132
BEAT = 60 / BPM
BAR = 4 * BEAT
# 가장조: A · F#m · D · E 를 되풀이, 마지막 벌은 D · E · A
PROG = [(45, (69, 73, 76)), (42, (69, 73, 78)), (38, (69, 74, 78)), (40, (68, 71, 76))]
TUNE = [  # (MIDI, 박): 마디마다 4 박
    [(81, 1), (83, .5), (85, 1.5), (83, 1)], [(81, 1), (78, 1), (81, 2)],
    [(78, 1), (81, .5), (83, 1.5), (81, 1)], [(80, 2), (76, 2)],
    [(81, 1), (83, .5), (85, 1.5), (88, 1)], [(86, 1), (85, 1), (81, 2)],
    [(78, .5), (81, .5), (83, 1), (85, 1), (86, 1)], [(85, 3), (0, 1)],
]


def music(n, t_go, t_fin, t_end):
    L, R = np.zeros(n + SR * 4), np.zeros(n + SR * 4)

    def put(x, at, gain, pan=0.0):
        i = int(round(at * SR))
        if i >= n or i + len(x) <= 0:
            return
        if i < 0:
            x, i = x[-i:], 0
        x = x[:len(L) - i]
        L[i:i + len(x)] += x * gain * (1 - pan) / 2 * 2 ** 0.5
        R[i:i + len(x)] += x * gain * (1 + pan) / 2 * 2 ** 0.5

    # 제목 · 카운트다운: 출발 앞 마디들에 깔리는 화음과 오르는 뜯는 소리(카운트 동안은 낮게)
    b0 = -math.ceil(t_go / BAR)
    for b in range(b0, 0):
        t0 = t_go + b * BAR
        bass, ch = PROG[b % 4]
        for m, pan in zip(ch, (-0.3, 0, 0.3)):
            put(inst('pad', m - 12, BAR), t0, 0.06)
        put(inst('bass', bass, BAR * 0.9), t0, 0.12)
        for j in range(8):
            m = ch[j % 3] + (12 if j >= 4 else 0)
            put(inst('pluck', m, BEAT / 2), t0 + j * BEAT / 2, 0.08 + 0.05 * (b - b0) / max(1, -b0), (-0.4, 0.1, 0.4)[j % 3])
    # 출발에서 결승까지: 북 · 베이스 · 화음 · 가락
    nb = int((t_fin - t_go) / BAR) + 1
    for b in range(nb):
        t0 = t_go + b * BAR
        if t0 >= t_fin:
            break
        bass, ch = PROG[b % 4]
        for j in range(4):
            put(inst('kick'), t0 + j * BEAT, 0.55)
            if j % 2:
                put(inst('snare'), t0 + j * BEAT, 0.3)
        for j in range(8):
            put(inst('hat'), t0 + j * BEAT / 2 + BEAT / 2 * 0, 0.18 if j % 2 else 0.1, 0.3)
            put(inst('bass', bass + (12 if j % 2 else 0), BEAT / 2 * 0.8), t0 + j * BEAT / 2, 0.3)
        for j in (0.5, 1.5, 2.5, 3.5):
            for m, pan in zip(ch, (-0.35, 0, 0.35)):
                put(inst('stab', m, BEAT * 0.35), t0 + j * BEAT, 0.07, pan)
        if b == 0:
            put(inst('crash'), t0, 0.5, 0)
        if b >= 2:
            u = 0
            for m, d in TUNE[(b - 2) % 8]:
                if m:
                    put(inst('lead', m, d * BEAT * 0.9), t0 + u * BEAT, 0.13, 0.12)
                u += d
    # 결승: 한 번 크게 치고, 끝까지 북 없이 화음 · 가락을 느슨하게, 끝에서 으뜸화음
    put(inst('crash'), t_fin, 0.55)
    put(inst('kick'), t_fin, 0.6)
    k = 0
    t0 = t_fin
    while t0 < t_end - 2 * BAR:
        bass, ch = PROG[(k + 2) % 4]
        for m, pan in zip(ch, (-0.3, 0, 0.3)):
            put(inst('pad', m, BAR), t0, 0.07, pan)
        put(inst('bass', bass, BAR * 0.9), t0, 0.18)
        for j in range(8):
            put(inst('pluck', ch[j % 3] + 12, BEAT / 2), t0 + j * BEAT / 2, 0.1, (-0.4, 0.1, 0.4)[j % 3])
        if k >= 1:
            for j in range(4):
                put(inst('kick'), t0 + j * BEAT, 0.28)
                put(inst('hat'), t0 + j * BEAT + BEAT / 2, 0.12, 0.3)
        k += 1
        t0 += BAR
    put(inst('bass', 45, 3.0), t0, 0.3)
    for j, m in enumerate((69, 73, 76, 81, 85)):
        put(inst('pad', m, 3.0), t0 + j * 0.03, 0.08, (j - 2) * 0.2)
        put(inst('pluck', m + 12, 1.0), t0 + j * 0.09, 0.12, (j - 2) * 0.2)
    put(inst('crash'), t0, 0.3)
    return np.stack([L[:n], R[:n]], axis=1)


if not NO_AUDIO:
    n = int(TOTAL * SR)
    t_go = marks_at('gobig')[0]
    t_fin = marks_at('fin')[0]
    print(f'go {t_go:.2f} s, finish {t_fin:.2f} s')
    mix = music(n, t_go, t_fin, TOTAL) * 0.8
    for name, what, g in (('n3', 'beep', 1), ('n2', 'beep', 1), ('n1', 'beep', 1), ('gobig', 'go', 1), ('gate', 'beep', 0.8), ('fin', 'buzzer', 1)):
        for t in marks_at(name):
            x = cue(what) * g
            i = int(t * SR)
            x = x[:n - i]
            mix[i:i + len(x)] += x[:, None]
    run = load('run')
    if run is not None:
        # (결승을 지나면 발소리도 멈춤)
        on =[(t_go, ends[0]), span('forest'), span('town'), (starts[3], t_fin + 0.3)]
        mix += looped(run, n) * (0.7 * env(n, on, 0.5))[:, None]
    t = np.arange(n) / SR
    mix *= (np.clip(t / FADE_IN, 0, 1) * np.clip((TOTAL - t) / FADE_OUT, 0, 1))[:, None]
    peak = np.abs(mix).max()
    mix *= min(1.0, 0.89 / peak)
    wav = os.path.join(SRC, 'race.wav')
    with wave.open(wav, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    print('sound ->', wav, f'peak {peak:.2f}')

vf = f'fade=t=in:st=0:d={FADE_IN},fade=t=out:st={TOTAL - FADE_OUT:.3f}:d={FADE_OUT},format=yuv420p'
cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-stats', '-framerate', str(FPS), '-i', os.path.join(seq, '%06d.jpg')]
if not NO_AUDIO:
    cmd += ['-i', os.path.join(SRC, 'race.wav')]
cmd += ['-vf', vf, '-c:v', 'libx264', '-preset', 'slow', '-crf', CRF, '-profile:v', 'high', '-r', str(FPS), '-g', '60']
if not NO_AUDIO:
    cmd += ['-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest']
cmd += ['-movflags', '+faststart', OUT]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
subprocess.run(cmd, check=True)
print('->', OUT, f'{os.path.getsize(OUT) / 1e6:.1f} MB')
