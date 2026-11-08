# 카카오 로드뷰 측정 (재창조 전 백양로)

공사 전 로드뷰(2008년 8월 · 2010년 12월 · 2011년 4월)에서 방위를 읽어, 바뀌지 않은 건물을 기준으로 파노라마 · 조형물 · 차도의 자리를 푸는 도구입니다. [#82](https://github.com/yonsei-reunion/campus-1997/issues/82)에서 썼습니다.

| 파일 | 하는 일 |
|---|---|
| `rv.mjs` | 헤드리스 로드뷰: `near` · `info` · `shots` · `past`(옛 파노라마를 비교 화면으로) |
| `osm_overlay.mjs` | 카카오 지도 · 스카이뷰에 OSM 외곽선을 겹쳐 그림 |
| `ruler.py` | 화면에서 화소 열을 읽는 자 달린 크롭(`crop`) · 쌓기(`stack`) · 모음(`sheet`) |
| `bearings.py` | 읽은 화소와 그 방위의 기록 |
| `resect.py` | 카카오 방위를 쓰지 않는 후방교회: 파노라마 · 독수리상 · 활천대 · 차도 |
| `pw.mjs` | playwright 찾기, 게임 좌표 ↔ 위경도 |

## 측정할 때

- **각도**: 뷰어는 화면 방향 각도의 소수점을 버립니다(258.3 · 258.6 · 258.9°가 모두 258°). `rv.mjs`는 정수 각도로 겨누고 그 값을 출력합니다.
  - 화소의 방위 = 각도 + atan((x − 694) / f)
  - f = 783 px(줌 3), 약 458 px(줌 0), 1388 × 900 화면 기준
  - 기울기는 0으로 둡니다. 그래야 세로 모서리가 곧게 보입니다
- **카카오 방위 · 위치 값을 믿지 않음**
  - 카카오 북쪽은 파노라마마다 최대 약 5° 틀립니다
  - 위치 값도 몇 m 틀립니다. 2011년 궤적은 지금(공사 뒤) OSM 보행로와 ±0.6 m로 겹쳐, 옛 파노라마를 지금 길 위에 다시 맞춰 놓았을 수 있습니다
  - 그래서 한 화면 안 두 대상 사이의 각만 쓰고, 파노라마마다 방위를 미지수로 풉니다(`resect.py`)
- **옛 파노라마**
  - 2010년 12월 백양로 id는 주소로도 `setPanoId`로도 열리지 않습니다. `rv.mjs past`가 날짜 슬라이더와 비교 화면으로 엽니다
  - 이때 카카오는 옛 파노라마의 자리로 지금 노드의 자리를 돌려줍니다. 실제로는 몇 m 떨어져 있으니(187 노드의 2010년 것은 약 6 m 동쪽) 랜드마크로 자리를 풉니다
- **모서리 판독**
  - 3배 크롭으로 읽습니다. 도서관 남쪽 면에도 아치가 있어 작은 화면에서는 동쪽 면과 헷갈립니다
  - 도서관 남쪽에는 2000년대 건물(학술정보원, 게임에는 없음)이 서 있습니다
  - 학생회관은 2011년에 나무와 공사 그물에 가렸습니다
  - 기준으로 쓴 OSM 외곽선(도서관, 제1공학관, 백주년기념관)은 스카이뷰 지붕과 1 m 안에서 겹칩니다(`osm_overlay.mjs`)
- **화면 캡처**: 저장소 밖(스크래치 폴더)에 쓰고 커밋하지 않습니다(CLAUDE.md 「고증 자료」). 출처에는 파노라마 id와 촬영 연월을 적습니다.

## 예

```sh
node tools/roadview/rv.mjs info 1017220175                     # 2011년 파노라마와 옛 파노라마 목록
node tools/roadview/rv.mjs shots spec.json /tmp/rv             # spec: [{"pano":1017220187,"look":[-85.4,-71.1],"zoom":3}]
node tools/roadview/rv.mjs past 1017220175 2010 /tmp/rv e:pan:282:3
python3 tools/roadview/ruler.py crop /tmp/rv/x.png /tmp/c.png 640 60 860 420 3
node tools/roadview/osm_overlay.mjs /tmp/ov.png -96 -26 1 sky   # 도서관 둘레 스카이뷰
uv run --with numpy --with scipy python tools/roadview/resect.py --past
uv run --with numpy --with scipy python tools/roadview/resect.py p187
```

`resect.py`의 모형(`--model`)은 셋입니다.
- `two`: 남쪽(169 ~ 175) · 북쪽(178 ~ 187) 묶음이 따로 이동
- `one`: 이동 하나
- `drift`: 이동이 길을 따라 선형으로 바뀜

`--drop 175:C12`처럼 판독을 하나씩 빼 볼 수 있습니다.
