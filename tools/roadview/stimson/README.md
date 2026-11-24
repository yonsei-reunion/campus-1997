# 스팀슨관 폭: 서쪽 찻길 로드뷰 후방교회 (#247, 끝나지 않음)

`reference/고증/3.5.3_스팀슨관_앞_계단과_길.md` 「서쪽 찻길 로드뷰와 2013년 실측 평면」의 판독 도구입니다.
작업 폴더 `$ST_WORK`(기본 `/tmp/stimson_rv`) 의 `st/` 에 파노라마를 받습니다(저장소에 넣지 않음).

```sh
export ST_WORK=/tmp/stimson_rv
node tools/roadview/yonsei_ro/paths.mjs 1212398696 1212398699 1212398702 1212397650 1212397654 \
  1212397657 1212397663 1212397666 1212397669 1212397672 > $ST_WORK/st/paths.jsonl
YRO_WORK=$ST_WORK/st python3 -I tools/roadview/yonsei_ro/fetch.py 2008,2010,2011
python3 tools/roadview/stimson/over.py 1016786045          # 예상 열을 찍은 개관 o_<pano>.png
python3 tools/roadview/stimson/batch.py tools/roadview/stimson/readings.txt sheet.png   # 판독 → readings.json
.venv/bin/python tools/roadview/stimson/solve.py --fixvf --oneW
```

| 파일 | 하는 일 |
|---|---|
| `feat.py` | 기준점(스팀슨관 네 모서리를 u · v 로, 아펜젤러관 · 언더우드관 모서리)과 파노라마 목록 |
| `crop.py` · `multi.py` · `xm.py` | 자 달린 확대(한 장 · 한 장 여러 곳 · 여러 장) |
| `over.py` · `pred.py` | 카카오 자리 · 방위로 낸 예상 열(수 m · 수 ° 틀리니 찾는 데만) |
| `batch.py` | 세로 모서리를 행마다 밝기 경계로 읽어 직선 맞춤, `manual` 은 눈으로 읽은 값 |
| `tilt.py` | 세로 선분(LSD)으로 파노라마의 기울기(4 ~ 10°) |
| `solve.py` | 파노라마마다 자리 · 방위 · 기울기 둘, 뒷벽 · 앞벽 자리, 굴뚝을 함께 푸는 방위 그물 |

`readings.txt` 는 2026-11-25 까지 읽은 것입니다. 장마다 쓸 만한 점이 1 ~ 3개라 그물이 아직 닫히지 않습니다(남동 · 북서 모서리가 담쟁이 · 가지에 가림).
앞길(1016786678 ~ 685) 장에서 박공의 먼 뒤 모서리를 더하는 것이 다음 순서입니다.
