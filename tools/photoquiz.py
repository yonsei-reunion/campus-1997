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
  - 2022 재상봉 단체사진에서 자른 건물 띠(박물관 입구 · 광복관 · 음악관 · 빌링슬리관 현관, 과학관 앞 계단):
    건물 일부만 보여 너무 어려움(사용자, 2026-11-21)
  - 같은 사진의 옛 카메라: compare/cherry_1(핀슨관길 사진은 고증 3.18 의 풀이 compare/haetae_1 로),
    compare/cherry_2(앞길 사진은 compare/uw_steps_2 로), compare/uw_steps_1(정원 남쪽 계단 사진의 풀이
    (12.5, 109.7)는 게임에서 생울타리 · 차에 가려 사진과 닮지 않음)
- 학교 홈페이지 사진(reference/학교홈페이지/, 고증 1.1.2 자료 R): 카메라를 tools/photofit/r96fit.py 로 풀어
  tools/photofit/r96/<이름>.json 의 result 에 둔 것 가운데 위치 불확실성이 대략 5 m 안이고 걸어서 설 수 있는
  자리인 것(R96). 사진이 작아(대개 400 × 290 px) 키우지 않고 그대로 씀
  - 뺀 것(photo2b 몫)
    - 불확실성이 큼(정면 한 벽만 보여 깊이가 안 풀림): grad(아펜젤러관 북서쪽, ±12 m), grad6(스팀슨관 남동쪽, ±12 m),
      socio(연희관 남서쪽, 탑 모양이 게임과 달라 기준점이 어긋남), dogsang(독수리상, ±30 m), p25underwood(2001년)
    - 게임 건물이 일반 상자 모델이라 창 · 모서리를 맞출 수 없음: homeco(가정관), music(음악관), liter1(인문관 · 종합관),
      dong1(동문회관), dent · med · nurse · sevr · ysev(의료원 쪽), b-bld04 · b-bld05 · b-bld07 · bld-old(경영학교실단),
      Info_Sub_1 · Info_Sub_2(무악학사 · 국제학사), p70allen(알렌관)
    - 건물 일부만 좁게 보이거나 가까이 찍은 것: yun(윤동주 시비), Eng_lndscape_3 · Eng_lndscape_5(석조관 벽 한 면),
      eagle · eagle.gif · junginbo(조형물 근접), hyungwan(과학관 현관)
    - 높은 데서 내려다봤거나 군중 사진: liter(눈 덮인 주차장), Eng_lndscape_1(밤), Eng_lndscape_4(정원),
      Eng_schlife_16 · place1(졸업식 군중)
    - 게임 모델과 모양이 달라 기준점이 모자람: edu(용재관, 사진은 붉은 기와 박공 지붕), bld-new(공사 중 대우관, 앞 맨흙 · 자재)
    - 1997년 모습과 다른 것: b-bld01 · b-bld02 · b-bld03 · b-bld06(공사 중 · 모형), engcenter · scicenter(계획 그림),
      71상남경영관(1997년 뒤), History_*(1920 ~ 1985년), biology_way · biology_alumni_way(어느 길인지 확실하지 않음 · 흐림),
      chung(청송대 숲), stone(어느 계단인지 모름), sin(어느 석조관 면인지 확실하지 않음), p11eng1(2001년 저장, 눈)
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
    ('amphitheater', 'compare/amphitheater', '1997_구노천극장_마지막모습.jpg', '옛 노천극장 객석 동쪽 끝 너머 비탈',
     '1997년', ANTH97),
]

# 학교 홈페이지 사진: (id, tools/photofit/r96/<이름>.json, 정답 뒤 보이는 제목, 찍은 때, 출처)
BIO98 = '연세대 생물학과 홈페이지(1998년 웨이백 저장본)'
R96 = [
    ('bakyang97', 'bakyang', '백양로 주차 정산소 앞 차로', '1997년 가을 무렵', BIO98),
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
    for qid, name, title, when, credit in R96:
        spec = json.loads((ROOT / 'tools/photofit/r96' / f'{name}.json').read_text())
        c = spec['result']['cam']
        bearing = math.degrees(math.atan2(c['tx'] - c['x'], c['ty'] - c['y'])) % 360
        im = Image.open(ROOT / spec['photo']).convert('RGB')
        im.save(OUT_IMG / f'{qid}.jpg', quality=88, optimize=True, progressive=True)
        items.append({'id': qid, 'x': c['x'], 'y': c['y'], 'bearing': round(bearing, 1),
                      'photo': f'assets/photoquiz/{qid}.jpg', 'w': im.width, 'h': im.height,
                      'title': title, 'when': when, 'credit': credit, 'from': spec['photo'], 'shot': f'r96/{name}'})
    doc = {'_doc': 'tools/photoquiz.py 가 만든다(손으로 고치지 않음). x, y: 정답 자리(캠퍼스 m), '
                   'bearing: 바라보는 방위(북에서 시계 방향, 도)', 'items': items}
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print(f'{len(items)} items → {OUT_JSON.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
