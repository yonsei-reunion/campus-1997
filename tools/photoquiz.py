"""미니 게임 「이곳은 어디?」(web/src/photoquiz.js)의 문제 목록과 사진을 만든다.

    python tools/photoquiz.py

- 문제: README 「사진과 비교」의 사진 가운데, 그 짝의 카메라(tools/snapshots.json 의 compare/*)가
  땅 위 사람 눈높이 언저리(땅 위 5 m 안, 걸어서 설 수 있는 자리)이고 라이선스가 분명하거나 기념문집
  사진인 것. 기념문집 사진은 얼굴을 알아볼 수 있는 사람이 보이면 뺌(뒷모습 · 멀리 작은 사람은 씀).
  카메라의 자리(x, y)와 바라보는 방향(겨냥점 쪽)이 정답이다.
- 뺀 것
  - 하늘 · 옥상 · 언덕 위 카메라: 백양로 · 캠퍼스 서쪽 · 캠퍼스 전경 · 초소 항공 사진, 대우관 · 상뜰,
    연세로 · 신촌 로터리 옥상, 정문(철둑 비탈, 걸어서 못 감), 교육관 둘(땅 위 5.6 ~ 6.8 m)
  - 라이선스가 분명하지 않은 것: 개인 블로그(학생회관 · 대강당 · 대우관), 사용자 제공 용재관
  - 중앙도서관(걷는 사람들의 뒷모습) · 옛 노천극장(멀리 작은 사람)은 그대로 씀
  - 과학관 앞 계단(단체사진에서 자른 것, 사람은 없으나 카메라가 걷는 면 위 5.1 m)
  - 같은 사진의 옛 카메라: compare/cherry_1(핀슨관길 사진은 고증 3.18 의 풀이 compare/haetae_1 로),
    compare/cherry_2(앞길 사진은 compare/uw_steps_2 로), compare/uw_steps_1(정원 남쪽 계단 사진의 풀이
    (12.5, 109.7)는 게임에서 생울타리 · 차에 가려 사진과 닮지 않음)
- 사진은 긴 변 960 px JPEG 로 줄여 web/public/assets/photoquiz/ 에, 목록은 web/public/data/photoquiz.json 에.
"""
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SNAP = json.loads((ROOT / 'tools/snapshots.json').read_text())
OUT_IMG = ROOT / 'web/public/assets/photoquiz'
OUT_JSON = ROOT / 'web/public/data/photoquiz.json'
LONG = 960

TUNG = 'Tungdangthanh · Wikimedia Commons, CC BY-SA 4.0'
OWN = '제작자 사진'
# (id, compare shot, reference photo, title shown after the answer, when, credit)
ANTH97 = '2026 재상봉 25주년 기념문집 「응답하라 1997!」'
ANTH96 = '2022 재상봉 25주년 기념문집 단체사진(건물 부분)'
# CROP: 위에서부터 남길 높이의 비. 아펜젤러관 정면은 아래 1/6 쯤이 빈 회색 띠
CROP = {'appenzeller': 1050 / 1280}
QUIZ = [
    ('underwood', 'compare/underwood', '언더우드관_정면_2016.jpg', '언더우드관 앞 정원', '2016년', TUNG),
    ('stimson', 'compare/stimson', '스팀슨관_정면_2016.jpg', '스팀슨관 정면', '2016년', TUNG),
    ('appenzeller', 'compare/appenzeller', '아펜젤러관_정면_2016.jpg', '아펜젤러관 정면', '2016년', TUNG),
    ('yeonhui', 'compare/yeonhui', '연희관_정면_2023.jpg', '연희관 남쪽 계단 위', '2023년 가을',
     'Huntsmanleader · Wikimedia Commons, CC BY 4.0'),
    ('statue', 'compare/underwood_statue', '언더우드동상_2009.jpg', '언더우드 동상 왼쪽 앞', '2009년',
     'Thinkinglex · Wikimedia Commons, 퍼블릭 도메인'),
    ('hwalcheon', 'compare/hwalcheon', '활천대_2009_연세춘추.jpg', '활천대 분수 앞', '2009년', '연세춘추'),
    ('haetae', 'compare/haetae_1', '2003_봄_백양로끝_핀슨관길_벚나무.jpg', '백양로 끝 계단 윗머리 북동쪽 길',
     '2003년 봄', OWN),
    ('frontroad', 'compare/uw_steps_2', '2003_봄_언더우드관_앞길_벚나무.jpg', '언더우드관 서쪽 날개 앞길',
     '2003년 봄', OWN),
    ('kiosk', 'compare/haetae_2', '2003_가을_연희관_정면.jpg', '연희관 앞 남서쪽', '2003년 가을', OWN),
    ('library', 'compare/library', '1997_중앙도서관.jpg', '중앙도서관 북동쪽 비스듬한 길 머리', '1997년', ANTH97),
    ('museum', 'compare/museum', '백주년기념관_박물관입구_1996_정면.jpg', '백주년기념관 박물관 입구 앞마당',
     '1996년', ANTH96),
    ('kwangbok', 'compare/kwangbok', '광복관_현관_1996_1.jpg', '광복관 현관 앞', '1996년', ANTH96),
    ('music', 'compare/music', '음악관_현관_1996.jpg', '음악관 신관 정문 앞', '1996년', ANTH96),
    ('amphitheater', 'compare/amphitheater', '1997_구노천극장_마지막모습.jpg', '옛 노천극장 객석 동쪽 끝 너머 비탈',
     '1997년', ANTH97),
    ('billingsley', 'compare/billingsley', '빌링슬리관_현관_1996.jpg', '빌링슬리관 가운데 현관 앞', '1996년', ANTH96),
]


def shot(name):
    return next(s for s in SNAP['shots'] if s['name'] == name)


def main():
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    items = []
    for qid, name, photo, title, when, credit in QUIZ:
        c = shot(name)['cam']
        # bearing: clockwise from north (the game's yaw is its negative)
        bearing = math.degrees(math.atan2(c['tx'] - c['x'], c['ty'] - c['y'])) % 360
        im = Image.open(ROOT / 'reference' / photo).convert('RGB')
        if qid in CROP:
            im = im.crop((0, 0, im.width, round(im.height * CROP[qid])))
        k = LONG / max(im.size)
        if k < 1:
            im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        im.save(OUT_IMG / f'{qid}.jpg', quality=80, optimize=True, progressive=True)
        items.append({'id': qid, 'x': c['x'], 'y': c['y'], 'bearing': round(bearing, 1),
                      'photo': f'assets/photoquiz/{qid}.jpg', 'w': im.width, 'h': im.height,
                      'title': title, 'when': when, 'credit': credit, 'from': f'reference/{photo}', 'shot': name})
    doc = {'_doc': 'tools/photoquiz.py 가 만든다(손으로 고치지 않음). x, y: 정답 자리(캠퍼스 m), '
                   'bearing: 바라보는 방위(북에서 시계 방향, 도)', 'items': items}
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print(f'{len(items)} items → {OUT_JSON.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
