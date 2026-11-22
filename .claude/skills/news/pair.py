"""새 소식의 전 · 후 그림 한 장: 같은 카메라로 찍은 두 캡처를 나란히(또는 위아래로) 붙이고 「전」 「후」를 적는다.

  python3 .claude/skills/news/pair.py <전.png> <후.png> <out.jpg> [v] [--width 1200] [--labels 사진,게임] [--crop x0,y0,x1,y1]

  v         위아래로(세로로 긴 화면). 없으면 좌우
  --width   붙인 그림의 폭(px, 기본 1200. 좌우일 때 한 칸은 그 절반)
  --labels  「전,후」 대신 쓸 말(사진과 게임을 견줄 때 「사진,게임」). 빈 값이면 적지 않음
  --crop    붙이기 전에 두 그림에서 같은 네모만 잘라 냄(0 ~ 1 비율: 0.1,0.2,0.9,0.8)

out 은 web/public/assets/news/<번호>_<이름>.jpg (번호는 그 폴더에서 가장 큰 번호 + 1: check_news.py 가 알려 줌).
"""
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'      # (fonts-noto-cjk. 없으면 글자 없이 붙임)
GAP = 6


def pair(a, b, out, width=1200, vertical=False, labels=('전', '후'), crop=None):
    A, B = Image.open(a).convert('RGB'), Image.open(b).convert('RGB')
    if crop:
        A, B = (im.crop((int(crop[0] * im.width), int(crop[1] * im.height), int(crop[2] * im.width), int(crop[3] * im.height))) for im in (A, B))
    if vertical:
        A, B = (im.resize((width, round(im.height * width / im.width)), Image.LANCZOS) for im in (A, B))
        C = Image.new('RGB', (width, A.height + B.height + GAP), 'white')
        C.paste(A, (0, 0))
        C.paste(B, (0, A.height + GAP))
        pos = [(12, 8), (12, A.height + GAP + 8)]
    else:
        w = (width - GAP) // 2
        A, B = (im.resize((w, round(im.height * w / im.width)), Image.LANCZOS) for im in (A, B))
        C = Image.new('RGB', (width, max(A.height, B.height)), 'white')
        C.paste(A, (0, 0))
        C.paste(B, (w + GAP, 0))
        pos = [(12, 8), (w + GAP + 12, 8)]
    if labels and any(labels):
        try:
            f = ImageFont.truetype(FONT, max(22, width // 40))
            d = ImageDraw.Draw(C)
            for p, t in zip(pos, labels):
                d.text(p, t, font=f, fill='white', stroke_width=3, stroke_fill='black')
        except OSError:
            print('글꼴이 없어 글자 없이 붙임:', FONT)
    C.save(out, quality=86)
    print(out, C.size)


if __name__ == '__main__':
    arg = sys.argv[1:]

    def opt(k, d=None):
        if k in arg:
            i = arg.index(k)
            v = arg[i + 1]
            del arg[i:i + 2]
            return v
        return d
    width = int(opt('--width', 1200))
    labels = opt('--labels', '전,후').split(',')
    crop = opt('--crop')
    if len(arg) < 3:
        sys.exit(__doc__)
    pair(arg[0], arg[1], arg[2], width, 'v' in arg[3:], labels, [float(v) for v in crop.split(',')] if crop else None)
