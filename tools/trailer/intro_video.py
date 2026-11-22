"""소개 영상: tools/trailer/intro.mjs 가 찍은 장면 프레임을 순서대로 잇고 소리를 붙여 MP4 로.

  .venv/bin/python tools/trailer/intro_video.py <녹화 폴더> trailer/intro.mp4 [--no-audio] [--crf 18]

- 순서와 자르는 곳은 아래 CLIPS. 장면 사이는 0.4 초 겹쳐 번지게(XF) 잇는다. 자막은 프레임에 이미 들어 있다.
- 소리:
  - 배경 음악은 여기서 합성한다(이 영상에만 쓰는 가락. 라장조 92 BPM, 전기 피아노 · 베이스 · 오르골)
  - 게임의 소리는 tools/trailer/intro_audio.mjs 가 녹음한 <녹화 폴더>/audio/*.wav: 걷는 장면에 바람 · 새소리(walk),
    활천대 장면에 분수(fountain), 미니 게임 구간에 응원 연습의 아카라카 구호와 응원가(cheer, 그동안 배경 음악은 쉼)
- <녹화 폴더>/seq/ 에 이은 프레임(심볼릭 링크, 번지는 곳만 새 그림)을, <녹화 폴더>/intro.wav 에 소리를 둔다.
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
XF = 12                     # 장면 사이에 겹치는 프레임
SR = 48000

# (장면, 시작, 끝): None 은 처음 · 끝, ('t', 초), ('mark', 이름, 더할 초: meta.json 의 그 표시가 처음 나온 때부터)
CLIPS = [
    ('fly', None, None),
    ('posters', None, None),
    ('spring', None, None),
    ('autumn', None, None),
    ('heroes', None, None),
    ('compare', None, None),
    ('birthday', ('t', 0.3), ('mark', 'action', 1.0)),          # 다가가서 「나 오늘 생일이야!」
    ('birthday', ('mark', 'swing', -0.3), ('mark', 'water', 2.4)),   # 흔들어 던짐, 물보라
    ('birthday', ('mark', 'stand', -0.2), ('mark', 'stand', 1.9)),   # 분수 안에서 일어섬
    ('court', ('t', 0.4), None),
    ('memo', None, None),
    ('games', None, None),
    ('info', None, None),
]
FADE_IN, FADE_OUT = 0.6, 1.2    # 영상의 처음 · 끝 (s)


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
    fa, fb = max(0, frame_of(seg, a, 0)), min(n, frame_of(seg, b, n))
    clips.append((seg, fa, fb))
seq = os.path.join(SRC, 'seq')
shutil.rmtree(seq, ignore_errors=True)
os.makedirs(seq)
path = lambda seg, i: os.path.join(SRC, seg, f'{i:05d}.jpg')
out_i = 0
starts = []                 # 장면마다 영상에서 시작하는 때 (s)
for k, (seg, fa, fb) in enumerate(clips):
    first = fa + (XF if k else 0)                    # (앞의 XF 프레임은 앞 장면의 끝과 섞여 이미 나감)
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
print(f'{out_i} frames, {TOTAL:.1f} s ({int(TOTAL // 60)}:{TOTAL % 60:04.1f})')
for (seg, fa, fb), s, e in zip(clips, starts, ends):
    print(f'  {s:6.1f} - {e:6.1f}  {seg} [{fa}:{fb}]')


# ---------------------------------------------------------------- 소리
def span(name):
    """그 장면(들)이 영상에서 차지하는 구간 (처음 시작, 마지막 끝)."""
    ks = [k for k, c in enumerate(clips) if c[0] == name]
    return starts[ks[0]], ends[ks[-1]]


def env(n, spans, fade=0.8):
    """구간들 안에서 1, 밖에서 0 (fade 초 동안 번짐)."""
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


def looped(x, n, skip=3.0, xf=2.0):
    """x 의 skip 초 뒤부터를 n 표본 길이로 되풀이(이음매는 xf 초 겹침)."""
    x = x[int(skip * SR):]
    k = int(xf * SR)
    body = x[:-k].copy()
    ramp = np.linspace(0, 1, k)[:, None]
    body[:k] = body[:k] * ramp + x[-k:] * (1 - ramp)
    reps = n // len(body) + 1
    return np.tile(body, (reps, 1))[:n]


# 배경 음악: 라장조, 여덟 마디가 되풀이. 화음(근음 · 구성음의 MIDI)과 가락 두 벌
BPM = 92
BEAT = 60 / BPM
CHORDS = [   # (베이스, 화음의 세 음)
    (38, (62, 66, 69)), (37, (61, 64, 69)), (35, (59, 62, 66)), (30, (61, 66, 69)),
    (31, (59, 62, 67)), (30, (62, 66, 69)), (28, (59, 62, 67)), (33, (61, 64, 69)),
]
TUNE_A = [[(78, 2), (81, 1), (78, 1)], [(76, 2), (73, 1), (76, 1)], [(74, 2), (78, 1), (74, 1)], [(73, 3), (69, 1)],
          [(71, 2), (74, 1), (71, 1)], [(69, 2), (74, 1), (78, 1)], [(79, 1.5), (78, .5), (76, 1), (74, 1)], [(76, 3), (0, 1)]]
TUNE_B = [[(81, 1), (78, 1), (86, 2)], [(85, 1.5), (83, .5), (81, 2)], [(83, 1), (81, 1), (78, 2)], [(81, 3), (78, 1)],
          [(79, 1), (83, 1), (86, 2)], [(86, 1), (81, 1), (78, 2)], [(76, 1), (79, 1), (83, 1), (81, 1)], [(81, 2), (85, 2)]]
hz = lambda m: 440 * 2 ** ((m - 69) / 12)


def tone(kind, m, dur):
    """한 음(모노). keys: 전기 피아노, bass: 베이스, bell: 오르골, pad: 깔리는 화음."""
    f = hz(m)
    if kind == 'keys':
        n = int((dur + 1.4) * SR); t = np.arange(n) / SR
        x = np.sin(2 * math.pi * f * t + 1.6 * np.exp(-t * 5) * np.sin(2 * math.pi * f * 2 * t)) * np.exp(-t * 2.4)
        x += 0.3 * np.sin(2 * math.pi * f * 2 * t) * np.exp(-t * 5) + 0.12 * np.sin(2 * math.pi * f * 4 * t) * np.exp(-t * 9)
        x *= np.clip(t / 0.006, 0, 1)
    elif kind == 'bass':
        n = int((dur + 0.3) * SR); t = np.arange(n) / SR
        x = (np.sin(2 * math.pi * f * t) + 0.35 * np.sin(2 * math.pi * 2 * f * t) * np.exp(-t * 4)) * np.exp(-t * 1.1)
        x *= np.clip(t / 0.012, 0, 1) * np.clip((dur + 0.3 - t) / 0.25, 0, 1)
    elif kind == 'bell':
        n = int((dur + 2.2) * SR); t = np.arange(n) / SR
        x = np.sin(2 * math.pi * f * t) * np.exp(-t * 1.9) + 0.32 * np.sin(2 * math.pi * f * 3.0 * t) * np.exp(-t * 4.5)
        x += 0.12 * np.sin(2 * math.pi * f * 5.4 * t) * np.exp(-t * 9)
        x *= np.clip(t / 0.003, 0, 1)
    else:
        n = int((dur + 1.0) * SR); t = np.arange(n) / SR
        x = sum(np.sin(2 * math.pi * f * d * t + p) for d, p in ((1, 0), (1.004, 1.3), (0.996, 2.1))) / 3
        x *= np.clip(t / 0.9, 0, 1) * np.clip((dur + 1.0 - t) / 1.0, 0, 1)
    return x


def music(n, rests):
    """n 표본의 배경 음악(스테레오). rests: 쉬는 구간(미니 게임의 응원가)."""
    L, R = np.zeros(n + SR * 4), np.zeros(n + SR * 4)

    def put(x, at, gain, pan=0.0):
        i = int(at * SR)
        if i >= n:
            return
        x = x[:len(L) - i]
        L[i:i + len(x)] += x * gain * (1 - pan) / 2 * 2 ** 0.5
        R[i:i + len(x)] += x * gain * (1 + pan) / 2 * 2 ** 0.5

    bars = int(n / SR / (4 * BEAT)) + 1
    last = int((n / SR - 3.8) / (4 * BEAT))            # 끝 화음을 놓을 마디(영상의 끝 3.8 초 앞)
    for b in range(bars):
        t0 = b * 4 * BEAT
        if b > last:
            break
        if b == last:                                  # 으뜸화음을 길게 두고 끝냄
            put(tone('bass', 38, 6), t0, 0.34)
            for j, m in enumerate((62, 66, 69, 74, 78)):
                put(tone('keys', m, 6), t0 + j * 0.07, 0.26, (j - 2) * 0.2)
            put(tone('bell', 86, 4), t0 + 0.4, 0.2, 0.2)
            for m, pan in ((50, -0.3), (57, 0.0), (66, 0.3)):   # (길게 남는 울림)
                put(tone('pad', m, 4.5), t0, 0.16, pan)
            break
        bass, ch = CHORDS[b % 8]
        phrase = b // 8                                # 여덟 마디 한 벌
        put(tone('bass', bass, 2 * BEAT), t0, 0.32)
        put(tone('bass', bass + (12 if b % 2 else 7), 1.5 * BEAT), t0 + 2 * BEAT, 0.22)
        put(tone('pad', ch[0] - 12, 4 * BEAT), t0, 0.1, -0.3)
        put(tone('pad', ch[1], 4 * BEAT), t0, 0.07, 0.3)
        # 화음을 여덟 번에 풀어 침
        order = (0, 1, 2, 1, 0 + 3, 2, 1, 2) if phrase % 2 == 0 else (0, 2, 1, 2, 0 + 3, 2, 1, 2)
        for j, o in enumerate(order):
            m = ch[o % 3] + (12 if o >= 3 else 0)
            put(tone('keys', m, BEAT / 2), t0 + j * BEAT / 2, 0.2 if j % 2 else 0.25, (-0.35, 0.1, 0.4)[o % 3])
        # 가락: 첫 벌은 쉬고, 그 뒤 A · B 를 번갈아(넷째 벌마다 쉼)
        if phrase >= 1 and phrase % 4 != 0:
            tune = (TUNE_A if phrase % 2 else TUNE_B)[b % 8]
            u = 0
            for m, d in tune:
                if m:
                    put(tone('bell', m, d * BEAT), t0 + u * BEAT, 0.27, 0.15)
                u += d
    x = np.stack([L[:n], R[:n]], axis=1)
    g = 1 - env(n, rests, 1.6)
    return x * g[:, None]


if not NO_AUDIO:
    n = int(TOTAL * SR)
    mix = np.zeros((n, 2))
    games = span('games')
    bgm = music(n, [games])
    mix += bgm * 0.5
    walk = load('walk')
    if walk is not None:
        on = [span(s) for s in ('posters', 'spring', 'autumn', 'heroes', 'court', 'memo')]
        mix += looped(walk, n) * (0.55 * env(n, on, 1.0) + 0.3 * env(n, [span('fly'), span('birthday')], 1.0))[:, None]
    fountain = load('fountain')
    if fountain is not None:
        mix += looped(fountain, n) * (1.3 * env(n, [span('birthday')], 1.2))[:, None]
    cheer = load('cheer')
    if cheer is not None:
        # 구호의 끝 두 마디부터 응원가로(녹음의 14.5 초에 구호가 시작하고 28.9 초부터 응원가)
        a, b = games
        seg = cheer[int(24.1 * SR):int((24.1 + b - a + 1.5) * SR)]
        i = int((a - 0.2) * SR)
        seg = seg[:n - i]
        t = np.arange(len(seg)) / SR
        g = np.clip(t / 0.5, 0, 1) * np.clip((len(seg) / SR - t) / 1.6, 0, 1)
        mix[i:i + len(seg)] += seg * (0.8 * g)[:, None]
    t = np.arange(n) / SR
    mix *= (np.clip(t / FADE_IN, 0, 1) * np.clip((TOTAL - t) / FADE_OUT, 0, 1))[:, None]
    peak = np.abs(mix).max()
    mix *= min(1.0, 0.89 / peak)
    wav = os.path.join(SRC, 'intro.wav')
    with wave.open(wav, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    print('sound ->', wav, f'peak {peak:.2f}')

# ---------------------------------------------------------------- MP4
vf = f'fade=t=in:st=0:d={FADE_IN},fade=t=out:st={TOTAL - FADE_OUT:.3f}:d={FADE_OUT},format=yuv420p'
cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-stats', '-framerate', str(FPS), '-i', os.path.join(seq, '%06d.jpg')]
if not NO_AUDIO:
    cmd += ['-i', os.path.join(SRC, 'intro.wav')]
cmd += ['-vf', vf, '-c:v', 'libx264', '-preset', 'slow', '-crf', CRF, '-profile:v', 'high', '-r', str(FPS), '-g', '60']
if not NO_AUDIO:
    cmd += ['-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest']
cmd += ['-movflags', '+faststart', OUT]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
subprocess.run(cmd, check=True)
print('->', OUT, f'{os.path.getsize(OUT) / 1e6:.1f} MB')
