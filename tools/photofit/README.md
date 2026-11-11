# 1994년 항공 사진의 카메라 맞춤

`reference/1994_캠퍼스_항공사진_전경.jpg` 의 카메라를 게임 좌표에서 최소제곱으로 풀고, 백양로 차도와 독수리상의 자리를 역투영합니다(`reference/고증.md` 2.2.1, [#82](https://github.com/yonsei-reunion/campus-1997/issues/82)).

| 파일 | 하는 일 |
|---|---|
| `a94.json` | 기준점(건물 모서리 · 지붕선 · 회양목 띠 폭)과 그 화소, 펼친 면에 두 번 인쇄된 띠(x 1505 px부터 136 px 빼서 씀). `fix`의 `"5": 0`이 roll 고정 |
| `e94.json` | 백양로 회양목 띠 양쪽 화소 짝(차도 가운데를 역투영) |
| `scene.py` | 게임 장면: `campus.json`, `terrain_near.bin`, 랜드마크 GLB 꼭짓점. `.cache/`는 GLB를 다시 만들면 지웁니다 |
| `cam.py` · `fit.py` · `road.py` · `glb.py` | 카메라 모형, 맞춤, 역투영, GLB 읽기 |
| `run_fit.py` · `sens.py` | 맞춤 하나, 민감도(초점 고정 · 반씩 나눔 · 하나씩 뺌) |
| `roll94.py` · `longf94.py` · `dist94.py` | roll 고정/자유, 긴 초점 강제, 렌즈 왜곡 k1. 독수리상 기둥 발치(1307, 1195 px)의 자리도 함께 냄 |
| `gutter94.py` | 두 번 인쇄된 띠가 똑같은지 확인 |
| `fountain94.py` | 독수리상 · 활천대 기둥 발치(1307, 1195 · 1299.6, 1243 px)를 역투영해 두 조형물이 게임 자리에서 옮겨 간 양을 견줌 |
| `mapfit.py` · `map90.json` · `map94.json` · `map95.json` | 1990 · 1994 · 1995년 캠퍼스 지도(입체 그림)를 건물 남쪽 발치로 게임 좌표에 맞춤(사영 + 매끈한 박판 보정). `fit`은 잔차 표, `warp`은 지도의 한 구역을 게임 좌표로 펴고 `campus.json`의 길 · 건물을 겹침. 1995년은 1990년과 같은 그림이라 번호 자리로 옮겨 씀(`reference/고증/2.3` 「1997년 길과 지도」) |

```sh
uv run --with numpy --with scipy --with shapely --with pillow --with DracoPy python tools/photofit/roll94.py
uv run --with numpy --with scipy --with shapely --with pillow --with DracoPy python tools/photofit/run_fit.py tools/photofit/a94.json /tmp/cam94.json
python3 tools/photofit/gutter94.py
.venv/bin/python tools/photofit/mapfit.py fit tools/photofit/map94.json
.venv/bin/python tools/photofit/mapfit.py warp tools/photofit/map90.json -200,-180,-40,-20 4 /tmp/map90_libsw.png
```

주의
- 출력하는 `rms`는 가중 잔차 제곱합을 자유도로 나눈 값의 제곱근입니다(단순 화소 rms가 아님). 표준편차도 모형 안의 값입니다.
- 기준점의 출처가 섞여 있습니다.
  - 도서관 · 과학관: 지붕 꼭짓점이라, 지붕 높이 1 m가 동서 약 1.8 m로 옮겨 갑니다
  - 학생회관: 게임 모델의 모서리입니다
  - 제1공학관: 1997년 외곽선(`reference/고증.md` 3.8: 남동 모서리는 로드뷰, 북쪽 끝은 OSM)입니다. 남동 지붕 모서리의 높이는 모형의 옥탑 꼭대기입니다
- roll을 풀면 2.0°가 나오고 과학관 지붕의 세로 잔차가 사라집니다(`roll94.py`).
- 도서관 남동 모서리 위는 (1197, 1021)에서 (1182, 1020)으로 고쳤습니다. 전 화소는 동쪽 면이 비스듬히 보이는 띠에 찍혀 있었고, 기둥 대칭으로 다시 읽었습니다. 고친 뒤 rms 3.8 → 2.9, 독수리상 서쪽 4.6 → 4.1 m, 차도는 독수리상 앞에서 −0.3 → +0.3 m입니다.
- 차도는 초점 거리에 따라 흔들리지만, 기준점과 같은 깊이의 독수리상은 덜 흔들립니다.
