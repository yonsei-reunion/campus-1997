"""활천대 생일 영상: tools/trailer/birthday.mjs 가 찍은 게임 프레임에 사진 → 게임 전환, 자막, 소리를 붙여 MP4 로.

    python3 tools/trailer/birthday_video.py <프레임 폴더> trailer/birthday.mp4

- 처음 3초는 reference/활천대_공사전_연세대블로그.jpg (4:3, 좌우 검은 띠). 게임의 첫 화면은 이 사진을 푼 카메라에서
  물줄기를 끄고 찍었으므로 사진과 겹친다. 사진은 분수에서 바깥으로 번지는 얼룩 모양으로 게임 화면에 자리를 내주고,
  게임 화면의 색은 사진의 색에서 제 색으로 돌아온다. 그다음 검은 띠가 열려 16:9 화면이 된다.
- 소리는 여기서 합성한다: 새소리 · 바람, 분수 물소리(물줄기가 켜진 뒤), 던질 때 바람 소리, 물보라, 오르골
  「생일 축하합니다」(Happy Birthday to You: 힐 자매의 1893년 「Good Morning to All」 선율, 퍼블릭 도메인).
- events.json 의 영상 시각(장면이 바뀐 때)에 맞춰 소리와 자막을 놓는다.
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
SRC, OUT = sys.argv[1], sys.argv[2]
PHOTO = os.path.join(ROOT, 'reference', '활천대_공사전_연세대블로그.jpg')
W, H = 1920, 1080
PW = 1440                                   # the photo's 4:3 width at full height
BAR = (W - PW) // 2
FONT_B = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
# the recorder's timeline (tools/trailer/birthday.mjs T): photo until DISSOLVE, game fully in by DISSOLVE_END
DISSOLVE, DISSOLVE_END, GRADE_END, BARS, BARS_END = 3.2, 5.8, 6.6, 6.0, 7.4

meta = json.load(open(os.path.join(SRC, 'events.json')))
FPS, N = meta['fps'], meta['frames']
EV = {}
for e in meta['events']:
    EV.setdefault(e['e'], e['t'])
TOTAL = N / FPS
print(f'{N} frames, {TOTAL:.1f} s; events', {k: round(v, 2) for k, v in EV.items()})


def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def frame(i):
    return np.asarray(Image.open(os.path.join(SRC, 'frames', f'{i:05d}.jpg')).convert('RGB'), dtype=np.float32) / 255


# ---------------------------------------------------------------- the photo and the dissolve
photo = np.asarray(Image.open(PHOTO).convert('RGB').resize((PW, H), Image.LANCZOS), dtype=np.float32) / 255
rng = np.random.default_rng(1997)


def octave(cells_x, cells_y):
    a = (rng.random((cells_y, cells_x)) * 255).astype(np.uint8)
    return np.asarray(Image.fromarray(a).resize((PW, H), Image.BICUBIC), dtype=np.float32) / 255


noise = octave(16, 12) + 0.5 * octave(40, 30) + 0.25 * octave(110, 82)
noise = (noise - noise.min()) / (noise.max() - noise.min())
# outwards from the column (photo: x 520 / 1006, y 400 / 754)
yy, xx = np.mgrid[0:H, 0:PW].astype(np.float32)
cx, cy = 520 / 1006 * PW, 400 / 754 * H
rad = np.hypot(xx - cx, (yy - cy) * 1.15)
rad /= rad.max()
field = 0.5 * noise + 0.5 * rad
f0, f1 = field.min(), field.max()
EDGE = 0.07

# the game's first frame graded to the photo's colours (per-channel mean / spread), easing back to its own
g0 = frame(0)[:, BAR:BAR + PW]
PM, PS = photo.reshape(-1, 3).mean(0), photo.reshape(-1, 3).std(0)
GM, GS = g0.reshape(-1, 3).mean(0), g0.reshape(-1, 3).std(0)
print('photo mean', PM.round(3), 'game mean', GM.round(3))


def graded(img, k):
    if k <= 0:
        return img
    m = (img - GM) / GS * PS + PM
    return img + (np.clip(m, 0, 1) - img) * k


# ---------------------------------------------------------------- captions
def caption(lines, shadow=True):
    """lines: [(text, font path, size, colour)] -> RGBA image of the block, centred lines."""
    fonts = [ImageFont.truetype(f, s, index=1 if f.endswith('.ttc') else 0) for _, f, s, _ in lines]
    boxes = [fn.getbbox(t) for (t, *_), fn in zip(lines, fonts)]
    gap = 18
    w = max(b[2] - b[0] for b in boxes) + 80
    h = sum(b[3] - b[1] for b in boxes) + gap * (len(lines) - 1) + 80
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 40
    for (t, _, _, col), fn, b in zip(lines, fonts, boxes):
        x = (w - (b[2] - b[0])) // 2 - b[0]
        d.text((x, y - b[1]), t, font=fn, fill=col)
        y += b[3] - b[1] + gap
    if shadow:
        a = img.split()[3].filter(ImageFilter.GaussianBlur(7))
        sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: int(v * 0.75)))
        img = Image.alpha_composite(sh, img)
    return np.asarray(img, dtype=np.float32) / 255


WHITE, SOFT = (255, 255, 255, 255), (235, 235, 228, 255)
END0 = EV.get('rest', TOTAL - 6) + 1.4
CAPS = [
    # (from, to, image, centre y)
    (0.7, 3.0, caption([('활천대', FONT_B, 92, WHITE), ('독수리상 옆 분수대 · 백양로 재창조 전', FONT, 40, SOFT),
                        ('사진: blog.naver.com/luckycmw', FONT, 24, (210, 210, 205, 255))]), 0.80),
    (7.0, 10.0, caption([('그 시절, 생일이면 어김없이…', FONT, 54, WHITE)]), 0.86),
    (END0, TOTAL + 1, caption([('생일 축하해!', FONT_B, 108, WHITE),
                               ('신촌 캠퍼스 1997  ·  yonsei-1997.benelog.net', FONT, 40, SOFT)]), 0.74),
]


def datestamp():
    fn = ImageFont.truetype(MONO, 40)
    t = "'97 5 21"
    b = fn.getbbox(t)
    img = Image.new('RGBA', (b[2] + 60, b[3] + 50), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((30, 25 - b[1] // 2), t, font=fn, fill=(255, 154, 46, 255))
    glow = img.filter(ImageFilter.GaussianBlur(6))
    glow.putalpha(glow.split()[3].point(lambda v: int(min(255, v * 1.6))))
    tint = Image.new('RGBA', img.size, (255, 120, 20, 0))
    tint.putalpha(glow.split()[3])
    return np.asarray(Image.alpha_composite(tint, img), dtype=np.float32) / 255


STAMP = datestamp()


def over(dst, img, x, y, a=1.0):
    h, w = img.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    src = img[y0 - y:y1 - y, x0 - x:x1 - x]
    al = src[..., 3:4] * a
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - al) + src[..., :3] * al


def fade(t, a, b, d=0.5):
    return min(1.0, max(0.0, (t - a) / d), max(0.0, (b - t) / d))


# ---------------------------------------------------------------- picture
def picture(i):
    t = i / FPS
    out = np.zeros((H, W, 3), np.float32)
    if t < DISSOLVE:
        out[:, BAR:BAR + PW] = photo
    else:
        g = frame(i)
        g = graded(g, 1 - smooth((t - DISSOLVE) / (GRADE_END - DISSOLVE)))
        if t < DISSOLVE_END:
            u = smooth((t - DISSOLVE) / (DISSOLVE_END - DISSOLVE))
            thr = f0 - EDGE + (f1 - f0 + 2 * EDGE) * u
            al = np.clip((thr - field + EDGE) / (2 * EDGE), 0, 1)[..., None]
            core = g[:, BAR:BAR + PW]
            mix = photo * (1 - al) + core * al
            mix += 0.1 * (4 * al * (1 - al))          # a soft light along the edge, as a print developing
            out[:, BAR:BAR + PW] = np.clip(mix, 0, 1)
        else:
            out[:] = g
        # the black bars open out to the full frame
        bw = int(round(BAR * (1 - smooth((t - BARS) / (BARS_END - BARS)))))
        if bw > 0:
            out[:, :bw] = 0
            out[:, W - bw:] = 0
    for a, b, img, cy in CAPS:
        k = fade(t, a, b, 0.6)
        if k > 0:
            over(out, img, (W - img.shape[1]) // 2, int(cy * H - img.shape[0] / 2), k)
    if t > BARS_END - 0.2:
        over(out, STAMP, W - STAMP.shape[1] - 30, H - STAMP.shape[0] - 26, min(1, (t - BARS_END + 0.2) / 0.8))
    # in from black, out to black
    k = min(1.0, t / 0.8, max(0.0, (TOTAL - t) / 1.3))
    return (np.clip(out * k, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------- sound
SR = 48000
NS = int((TOTAL + 0.5) * SR)
arng = np.random.default_rng(5)


def band(x, lo, hi, tilt=0.0):
    """band-pass by FFT with soft skirts; tilt: dB per octave above lo"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = 1 / (1 + (lo / np.maximum(f, 1)) ** 4) / (1 + (f / hi) ** 4)
    if tilt:
        g *= (np.maximum(f, lo) / lo) ** (tilt / 6.02)
    return np.fft.irfft(X * g, len(x))


def env_curve(points):
    """piecewise-linear gain over the whole track: [(t, gain)]"""
    ts = np.arange(NS) / SR
    p = np.array(points, dtype=np.float64)
    return np.interp(ts, p[:, 0], p[:, 1])


def norm(x):
    return x / (np.abs(x).max() + 1e-9)


mix = np.zeros(NS)
# birds and a breath of wind under everything
wind = norm(band(arng.standard_normal(NS), 120, 900)) * (0.6 + 0.4 * np.sin(np.arange(NS) / SR * 0.37))
mix += 0.05 * wind
for k in range(int(TOTAL * 0.9)):
    t0 = arng.uniform(0.5, TOTAL - 1)
    n = int(SR * arng.uniform(0.06, 0.13))
    tt = np.arange(n) / SR
    f = arng.uniform(2600, 4200) + 900 * np.sin(2 * np.pi * arng.uniform(18, 30) * tt)
    chirp = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / tt[-1]) ** 2
    for r in range(arng.integers(1, 4)):
        s = int((t0 + r * 0.16) * SR)
        if s + n < NS:
            mix[s:s + n] += 0.05 * chirp * arng.uniform(0.5, 1)
# the fountain: falling water once the jet is on, softer as the view rises away at the end
water = norm(band(arng.standard_normal(NS), 350, 7000, tilt=-2.0))
water *= 1 + 0.25 * norm(band(arng.standard_normal(NS), 0.3, 3))
mix += 0.16 * water * env_curve([(0, 0), (6.0, 0), (7.6, 1), (END0 - 2, 1), (END0 + 2, 0.45), (TOTAL + 1, 0.45)])
# the throw: a whoosh over the flight (slow motion), into the splash
if 'fly' in EV and 'water' in EV:
    a, b = EV['fly'] - 0.3, EV['water']
    n = int((b - a + 0.05) * SR)
    tt = np.arange(n) / SR
    w = band(arng.standard_normal(n), 180, 1600) * np.sin(np.pi * np.clip(tt / (b - a), 0, 1)) ** 1.5
    s = int(a * SR)
    mix[s:s + n] += 0.22 * norm(w)
# the splash (slowed down): a deep body thump, a burst of water, then drops falling back
if 'water' in EV:
    s = int(EV['water'] * SR)
    n = int(2.6 * SR)
    tt = np.arange(n) / SR
    burst = band(arng.standard_normal(n), 150, 3500) * np.exp(-tt / 0.45) * (1 - np.exp(-tt / 0.012))
    thump = np.sin(2 * np.pi * (70 + 40 * np.exp(-tt * 8)) * tt) * np.exp(-tt / 0.18)
    drops = np.zeros(n)
    for _ in range(140):
        d0 = int(arng.uniform(0.25, 2.4) ** 1.3 / 2.4 ** 0.3 * SR)
        m = int(0.02 * SR)
        if d0 + m < n:
            ft = arng.uniform(900, 2400)
            drops[d0:d0 + m] += np.sin(2 * np.pi * ft * np.arange(m) / SR * (1 + np.arange(m) / m)) * np.exp(-np.arange(m) / (0.004 * SR)) * arng.uniform(0.2, 1)
    sp = 0.55 * norm(burst) + 0.35 * thump + 0.12 * norm(drops) * np.exp(-tt / 1.4)
    e = min(NS, s + n)
    mix[s:e] += 0.9 * sp[:e - s]
# 「생일 축하합니다」 on a music box, from the two of you cheering to the end
MUSIC0 = EV.get('water', TOTAL - 16) + 1.9
BPM = 100
beat = 60 / BPM
# (note, beats): the old tune, in C
mel = [('G4', .75), ('G4', .25), ('A4', 1), ('G4', 1), ('C5', 1), ('B4', 2),
       ('G4', .75), ('G4', .25), ('A4', 1), ('G4', 1), ('D5', 1), ('C5', 2),
       ('G4', .75), ('G4', .25), ('G5', 1), ('E5', 1), ('C5', 1), ('B4', 1), ('A4', 2),
       ('F5', .75), ('F5', .25), ('E5', 1), ('C5', 1), ('D5', 1), ('C5', 3)]
# low notes on the bars' first beats (beat counted from the start, after the one-beat pickup)
bass = [(1, 'C3'), (4, 'G2'), (7, 'G2'), (10, 'C3'), (13, 'C3'), (16, 'F2'), (19, 'C3'), (21, 'G2'), (22, 'C3')]
NOTE = {'C': -9, 'D': -7, 'E': -5, 'F': -4, 'G': -2, 'A': 0, 'B': 2}


def hz(n):
    return 440 * 2 ** ((NOTE[n[0]] + 12 * (int(n[1]) - 4)) / 12)


def tine(f, amp, s):
    n = int(2.2 * SR)
    tt = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt * 3)
         + 0.12 * np.sin(2 * np.pi * 3 * f * tt) * np.exp(-tt * 6) + 0.1 * np.sin(2 * np.pi * 5.4 * f * tt) * np.exp(-tt * 12))
    x *= np.exp(-tt * 1.9) * (1 - np.exp(-tt / 0.002))
    e = min(NS, s + n)
    if e > s:
        music[s:e] += amp * x[:e - s]


music = np.zeros(NS)
b = 0.0
for n, d in mel:
    tine(hz(n), 1.0, int((MUSIC0 + b * beat) * SR))
    b += d
for bb, n in bass:
    tine(hz(n), 0.45, int((MUSIC0 + bb * beat) * SR))
# a little room round it
ir_n = int(1.1 * SR)
ir = arng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.32)
ir[0] = 0
wet = np.fft.irfft(np.fft.rfft(music, NS + ir_n) * np.fft.rfft(ir, NS + ir_n))[:NS]
music = music + 0.35 * norm(wet) * np.abs(music).max()
mix += 0.3 * norm(music)
# out with the picture
mix *= env_curve([(0, 0), (0.6, 1), (TOTAL - 1.4, 1), (TOTAL, 0), (TOTAL + 1, 0)])
mix = mix / np.abs(mix).max() * 0.89
wav = os.path.join(SRC, 'birthday.wav')
with wave.open(wav, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes((mix * 32767).astype(np.int16).tobytes())
print('sound ->', wav)

# ---------------------------------------------------------------- encode
cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
       '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
       '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '48000', '-c:a', 'aac', '-b:a', '160k', '-ac', '2', '-shortest', '-movflags', '+faststart', OUT]
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for i in range(N):
    p.stdin.write(picture(i).tobytes())
    if i % 150 == 0:
        print(f'  {i}/{N}')
p.stdin.close()
p.wait()
print('video ->', OUT)
