# 스팀슨관 폭: 로드뷰 후방교회 (#247, 끝나지 않음)

`reference/고증/3.5.3_스팀슨관_앞_계단과_길.md` 「서쪽 찻길 로드뷰와 2013년 실측 평면」 · 「앞길 로드뷰」의 판독 도구입니다.
작업 폴더 `$ST_WORK`(기본 `/tmp/stimson_rv`) 의 `st/` 에 파노라마를 받습니다(저장소에 넣지 않음).

```sh
export ST_WORK=/tmp/stimson_rv; T=tools/roadview/stimson
# 서쪽 찻길의 지난 파노라마(지금 노드에서) + 2010년 12월 앞길 걸음(id 로 바로 열림)
node tools/roadview/yonsei_ro/paths.mjs 1212398696 1212398699 1212398702 1212397650 1212397654 \
  1212397657 1212397663 1212397666 1212397669 1212397672 > $ST_WORK/st/paths.jsonl
node tools/roadview/yonsei_ro/paths.mjs 1016786678 1016786679 1016786680 1016786681 1016786682 \
  1016786683 1016786684 1016786685 1016786686 >> $ST_WORK/st/paths.jsonl
YRO_WORK=$ST_WORK/st python3 -I tools/roadview/yonsei_ro/fetch.py 2008,2010,2011
python3 $T/over.py 1016786685                                  # 예상 열을 찍은 개관 o_<pano>.png
python3 $T/tilt.py --len 18 1016786683 1016786684 1016786685 1016786686 ...   # up.json (opencv 필요)
python3 $T/batch.py $T/readings.txt sheet.png                  # 서쪽 찻길 판독 → readings.json
python3 $T/batch.py $T/front.txt sheet.png                     # 앞길: 기준점 · 박공 가운데
python3 $T/edge.py $T/front_edges.txt edges.png                # 앞길: 남쪽 박공 모서리
.venv/bin/python $T/solve.py --up --tsig 1.0 --oneW --only 683,684,685,686   # 앞길 그물
```

| 파일 | 하는 일 |
|---|---|
| `feat.py` | 기준점(스팀슨관 네 모서리를 u · v 로, 아펜젤러관 · 언더우드관 모서리)과 파노라마 목록 |
| `crop.py` · `multi.py` · `xm.py` | 자 달린 확대(한 장 · 한 장 여러 곳 · 여러 장) |
| `over.py` · `pred.py` | 카카오 자리 · 방위로 낸 예상 열(수 m · 수 ° 틀리니 찾는 데만) |
| `batch.py` | 세로 모서리를 행마다 밝기 경계로 읽어 직선 맞춤, `manual` 은 눈으로 읽은 값 |
| `edge.py` | 세로 모서리를 한 직선으로: 열 · 기움을 함께 훑어 평균 기울기가 가장 큰 선. 기움을 기울기가 주는 값 ±0.01 로 묶을 수 있음 |
| `tilt.py` | 세로 선분(LSD)으로 파노라마의 기울기. 앞길 장은 `--len 18`(45 면 선분이 한쪽에만 있어 기울기가 몇 도씩 흔들림) |
| `solve.py` | 파노라마마다 자리 · 방위 · 기울기 둘, 뒷벽 · 앞벽 자리, 굴뚝을 함께 푸는 방위 그물. `--up` 은 기울기를 `up.json` 쪽으로(±`--tsig`°), `--us` 는 스팀슨관을 길이 방향으로 풂 |

- `readings.txt`: 서쪽 찻길(2026-11-25). 장마다 쓸 만한 점이 1 ~ 3개라 그물이 닫히지 않음(남동 · 북서 모서리가 담쟁이 · 가지에 가림)
- `front.txt` · `front_edges.txt`: 앞길 683 ~ 686(2026-11-26). 남쪽 끝 벽 사이 11.9 ~ 12.2 ± 0.3 m 이나 스캔의 처마로 낸 값과 어긋나 결론 나지 않음
- 다음: 같은 그물을 폭을 아는 아펜젤러관에 써서 방법을 확인(정원 파노라마 1016786661 · 663 · 687, 앞길 장)
