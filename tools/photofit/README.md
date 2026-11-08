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

```sh
uv run --with numpy --with scipy --with shapely --with pillow --with DracoPy python tools/photofit/roll94.py
uv run --with numpy --with scipy --with shapely --with pillow --with DracoPy python tools/photofit/run_fit.py tools/photofit/a94.json /tmp/cam94.json
python3 tools/photofit/gutter94.py
```

주의
- 출력하는 `rms`는 가중 잔차 제곱합을 자유도로 나눈 값의 제곱근입니다(단순 화소 rms가 아님). 표준편차도 모형 안의 값입니다.
- 기준점의 출처가 섞여 있습니다.
  - 도서관 · 과학관: 지붕 꼭짓점이라, 지붕 높이 1 m가 동서 약 1.8 m로 옮겨 갑니다
  - 학생회관: 게임 모델의 모서리입니다
  - 제1공학관: 사진 A에서 잰 1997년 외곽선입니다
- roll을 풀면 2.0°가 나오고 과학관 지붕의 세로 잔차가 사라집니다(`roll94.py`).
- 차도는 초점 거리에 따라 흔들리지만, 기준점과 같은 깊이의 독수리상은 덜 흔들립니다.
