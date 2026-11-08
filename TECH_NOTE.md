# 기술 노트

이 저장소를 개발 · 유지보수하는 사람을 위한 문서입니다. 게임 소개와 조작법은 [`README.md`](README.md), 3D 그래픽의 일반 개념은
[`3D_GRAPHICS.md`](3D_GRAPHICS.md), 건물 · 길의 근거 자료는 [`reference/고증.md`](reference/고증.md) 에 있습니다.

## 실행과 배포

```bash
cd web
npm install
npm run dev          # http://localhost:5197
npm run build        # web/dist 정적 사이트
```

- `main` 에 올리면 `.github/workflows/pages.yml` 이 GitHub Pages(http://yonsei-1997.benelog.net/)에 다시 배포합니다.
- PC 브라우저에서 모바일 화면을 시험하려면 주소 끝에 `?touch` 를 붙입니다.
- 조작과 카메라는 sim-office 와 같은 방식(3인칭 걷기, 「마을 둘러보기」식 날아가기)입니다.

## 새 소식

게임 안 「새 소식」 창과 `news.html`(날짜마다 `#2026-11-06` 같은 주소)은 같은 데이터 `web/public/data/releases.json` 을 `web/src/notes.js` 로 그립니다.
형식과 쓰는 규칙은 [`CLAUDE.md`](CLAUDE.md) 에 있습니다. 캡처는 `docs/screenshots/` 와 `web/public/assets/news/` 에 둡니다.

## README · 문집 캡처

README 의 게임 화면(「사진과 비교」의 오른쪽 칸, 「게임 화면」, 맨 위 그림)과 문집 사이트(`../yonsei-anthology/src/content/memories.md`)의
게임 캡처는 `tools/snapshots.json` 의 카메라로 한 번에 다시 찍습니다. 건물을 고친 뒤에는 같은 카메라로 다시 찍어 사진과 비교합니다.

```bash
cd web && npx vite --port 5197                     # 다른 터미널
node tools/snapshots.mjs --port 5197               # 전부, 또는 --only compare/library,game/
python3 tools/snapshots_compose.py --sheet /tmp/sheet.jpg   # 사진 | 게임 짝을 한 장에 모아 검토
```

순서와 카메라 맞추는 법은 Claude Code 스킬 [`.claude/skills/update-snapshots`](.claude/skills/update-snapshots/SKILL.md) 에 있습니다.

## 저장소 구조

| 경로 | 내용 |
|---|---|
| `web/src/` | 게임 코드(three.js). 아래 「모듈」 참고 |
| `web/public/data/` | 빌드된 데이터: `campus.json`(건물 · 길 · 나무 · 장소), 지형 `terrain_*.bin`, `materials.json`, `sky.json`, `releases.json` |
| `web/public/assets/` | GLB 모델, 텍스처, HDRI, 새 소식 캡처 |
| `blender/` | Blender 파이썬 스크립트. 모든 3D 에셋을 생성해 GLB 로 내보냄 |
| `tools/` | 자료 내려받기, 캠퍼스 데이터 빌드, 텍스처 만들기, 그림자 베이크, 소개 영상 |
| `data/` | 중간 데이터(지형 npy, 원본 OSM) |
| `assets_src/` | 내려받은 원본 텍스처 · HDRI · 캐릭터 팩 |
| `reference/` | 1997년 사진과 고증 문서 |
| `docs/` | README 에 쓰는 캡처 · 비교 사진 |
| `docs/compare/` | README 「사진과 비교」의 사진(`<이름>_photo.jpg`)과 같은 자리의 게임 화면(`<이름>_game.jpg`), 표의 왼쪽 · 오른쪽 칸에 하나씩 |
| `docs/game/` | README 맨 위 그림과 「게임 화면」의 캡처 |

### 모듈 (`web/src/`)

| 파일 | 역할 |
|---|---|
| `main.js` | 로딩, 렌더러 · 조명 · 장면 구성, 프레임 루프 |
| `materials.js` | 재질 라이브러리, 셰이더 패치(바람 · 베이크 · PCSS · 대기), 계절 |
| `terrain.js` | 근경 · 원경 지형, 원경 도시 · 숲, 하늘 돔 |
| `world.js` | GLB 로딩, 재질 바인딩, 정적 메시 병합, 인스턴싱, 나무 LOD(임포스터) |
| `grass.js` · `litter.js` | 카메라 주위의 풀, 계절별 떨어진 잎 |
| `shadows.js` · `bakedshadow.js` · `blobs.js` | 실시간 그림자 캐시, 구운 땅 그림자, 폰용 블롭 그림자 |
| `post.js` | 후처리: N8AO → TAA/SMAA → 블룸 → 1997 필름 → 출력 |
| `player.js` · `touch.js` | 걷기 · 카메라 · 충돌, 모바일 스틱 |
| `birdseye.js` | 캠퍼스 위로 날아가기 |
| `characters.js` · `armpose.js` · `life.js` · `talk.js` | 사람 모델과 애니메이션, 팔 IK, 군중 · 차 · 현수막 · 초소, 말풍선 대사 |
| `hoops.js` | 농구공 |
| `water/fountain.js` | 활천대 분수 물(Ultra Water) |
| `ui.js` · `labels.js` · `places.js` · `news.js` · `notes.js` | 화면 UI, 건물 이름표, 추억 카드, 새 소식 |

## 구현 방식

### 지형과 배치

- OpenStreetMap 건물 외곽선과 도로, AWS Terrarium 고도 자료로 캠퍼스를 만듭니다(`tools/build_campus.py`).
- 건물 이름 · 층수 · 재료 · 색은 `build_campus.py` 의 건물 표 `B` 와 `LANDMARKS` 에 있습니다. 고증이 틀린 곳은 여기만 고쳐 다시 빌드합니다.
- 5 m 고도 격자가 건물 앞을 비탈로 뭉개는 곳은 `FORECOURTS` 로 앞마당을 평평하게 다듬습니다.
- 숲과 큰 건물 위에서 높게 나오는 고도 자료 탓에 한경길 북쪽 언덕은 1997년 항공 사진에 맞춰 6 m 낮췄습니다(고증 3.5.1).
- 좌표: 캠퍼스 좌표는 x = 동, y = 북(m). three.js 월드는 (x, 높이, −y).

### 백양로

- 1997년 항공 사진(`reference/1997_백양로_항공사진.jpg`)의 카메라를 역산해 길의 자리 · 폭 · 화단섬 · 현수막 · 초소 · 나무 높이를 사진에서 재어 옮겼습니다(고증 2장).
- 높이는 재창조 설계 보고서의 종단면도(`tools/build_campus.py`, `blender/road.py`).
- 날아가기의 「1997 사진 시점」은 그 역산한 카메라입니다.

### 건물

- 랜드마크는 `blender/landmarks.py` 에서 직접 모델링합니다(건물마다의 근거는 고증 3장). 동상은 `blender/statues.py`.
- 나머지 200여 동은 절차적 생성기 `blender/generic.py` 가 실제 외곽선 위에 세웁니다.
  - 창호(창틀 · 문설주 · 창대), 층 밴드, 파라펫, 옥상 설비, 녹색 방수 옥상, 물탱크, 상점 간판
  - 창의 7 %쯤은 미서기 한 짝을 열어 두고, 드물게 에어컨을 붙입니다(`blender/windows.py`)
  - 건물마다 현관(`porch`)이 있고 자리는 `build_campus.py` `_entry`. 1996년 졸업 앨범 사진의 현관들을 따랐습니다.
  - 계단은 걸어 오를 수 있는 보이지 않는 `walk_stairs` 메시를 따로 냅니다.
- 건물 · 랜드마크의 정점에는 `blender/bake.py` 가 AO, 처마 아래 비 자국, 햇빛 여부를 구워 `COLOR_0` 으로 내보냅니다. 웹은 이를 `bake` 속성으로 읽습니다.

### 재질

- 재질 정의는 `blender/materials.json` 한 곳입니다(= `web/public/data/materials.json`). Blender 는 미리보기용, 웹은 `MeshStandardMaterial` 로 다시 만듭니다.
- GLB 에는 형상 · UV · 재질 **이름**만 들어 있습니다. UV 는 미터 단위이고 `tile` 이 미터/반복입니다.
- PBR 텍스처는 Poly Haven(`tools/fetch_polyhaven.py`, `tools/prepare_web_textures.py`).

### 수목

- `blender/vegetation.py` 가 가지 골격 + 잎 카드로 일곱 수종을 만듭니다. 어린 느티나무 · 벚나무는 따로 만든 모델입니다.
- 수관 구형 노멀과 버텍스 AO, 계절별 잎 아틀라스(`tools/make_textures.py`).
- 230 m 밖의 나무는 실행 중에 렌더링한 임포스터(교차 판 + 위에서 본 판)로 바꿉니다(`world.js` `Forest`).
- 줄기와 잎은 카메라 가까이에서 디더링으로 비쳐 보이고, 고품질 화면에서는 TAA 가 점무늬를 고르게 섞습니다.
- 담쟁이는 잎 카드마다 위상과 매달린 길이를 정점에 담아 흔듭니다.
- 다듬은 관목 · 생울타리 · 꽃은 `blender/shrubs.py`: 다듬은 윤곽의 몸통(모서리 둥근 상자, 회전체)에 몸통 안에서 비스듬히 솟은 잔가지 카드.
  - 몸통은 이음매 없는 잎 무늬와 노멀 맵을 월드 좌표에서 세 방향으로 비춰 입힘(`web/src/hedges.js`, 폰은 색만): 한 줄로 겹친 생울타리 토막이 한 무늬로 이어짐
  - 카드는 뿌리 쪽 몸통의 노멀과 그늘을 받아 겉면과 같은 밝기, 뒷면을 볼 때도 노멀을 뒤집지 않음
  - 잎 · 꽃은 Poly Haven 「Periwinkle Plant」 스캔을 잘라 실제 크기로 다시 칠함(`tools/make_shrub_textures.py`)

### 사람

- Quaternius 의 CC0 모듈러 캐릭터를 `blender/characters.py` 가 부품을 섞고 1997년 옷차림으로 칠해 14명을 만듭니다(sim-office 의 `tools/office-characters.py` 를 고쳐 씀). 키는 실제 크기(남 1.73 m, 여 1.61 m).
- 애니메이션은 남녀 리그 파일 둘에 들어 있고, 이동 속도에 맞춰 재생 속도를 바꿔 발이 미끄러지지 않습니다.
- 단색 부품을 정점 색 메시 하나로 합쳐 한 명당 draw call 1번. 화면 밖이면 그리지 않습니다.
- 군중 행동(걷기, 멈춤, 무리, 인사)은 `life.js`, 대사는 `talk.js`.

### 자동차

- `blender/cars.py`. 단면을 몇 cm 마다 이어 붙이는 로프트 방식으로 차체 · 범퍼를 만들고, 램프는 차체 표면 위에 깔아 둥근 모서리를 따라 휩니다.
- 운전석의 인물이 꼿꼿이 앉으므로 차는 실제보다 7 % 크게 내보냅니다(`CAR_SCALE`).
- 도장은 클리어코트 재질, 바퀴는 달린 거리만큼 굴러가고 감속하면 브레이크등이 켜집니다.

### 분수

- Ultra Water(`web/src/water/ultra-water/`)의 FFT 물결 시뮬레이션과 바닥 빛무늬를 분수 크기(64² 격자, 4.5 m ~ 19 cm 네 층)로 줄여 씁니다(`web/src/water/fountain.js`).
- 바닥 · 벽은 같은 셰이더에서 굴절된 시선으로 레이트레이스합니다.
- 분수가 화면에 보이고 70 m 안쪽일 때만 계산합니다.

### 농구

- 림 · 그물 · 백보드는 코트 모델(`blender/landmarks.py`)에, 공 물리는 `hoops.js`, 두 손 IK 는 `armpose.js`.

### 렌더링

- three.js PBR, HDRI 하늘과 환경광. 환경 이미지의 해 원반은 지우고 그 빛은 그림자가 드는 `DirectionalLight` 로 옮겼습니다(`blender/sky_bake.py`, `main.js`).
- 지형 스플랫 셰이더: 잔디 · 아스팔트 · 보도블록 · 흙과 마른 잔디 층(`ground_dry.png`).
- 그림자
  - 4096² 섀도 맵. 해는 고정이므로 정적인 것은 캐시하고 매 프레임엔 가까운 사람 · 차만 그립니다(`shadows.js`).
  - 캠퍼스 전체의 땅 그림자를 한 장으로 구워 둡니다(`bakedshadow.js`, `tools/bake_sun_shadows.mjs`). 섀도 맵 밖과 폰에서 씁니다.
  - 폰은 섀도 맵이 일부 GPU 드라이버를 죽여서 끄고 블롭 그림자를 씁니다.
  - 데스크톱 HQ 는 PCSS(해의 시직경에 따른 부드러운 반영).
- 대기: 높이 안개와 구름 그림자를 모든 재질에 셰이더 패치로 넣습니다(`materials.js` `ATMOS`).
- 후처리(`post.js`): N8AO → TAA(서브픽셀 지터 · 깊이 재투영) 또는 SMAA → 두 단계 블룸 → 1997 필름 → AgX 톤매핑. 폰은 `RenderPass` + 4x MSAA 만.
- 셰이더 패치는 `materials.js` `patchShader` 로 쌓습니다. 캐시 키를 함께 관리해 같은 프로그램이 여러 번 컴파일되지 않게 합니다.
- 폰은 텍스처를 1024 이하로 줄여 올립니다(2K 세트는 밉맵 포함 약 1 GB).

## 에셋 파이프라인 (다시 빌드하기)

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy shapely pillow
python3 tools/fetch_polyhaven.py textures 1k <이름…>   # CC0 텍스처/모델/HDRI 내려받기 (assets_src/)
python3 tools/fetch_terrain.py near && python3 tools/fetch_terrain.py far
.venv/bin/python tools/build_campus.py            # OSM + 지형 -> data/campus.json, 지형 bin, 스플랫맵
.venv/bin/python tools/make_textures.py           # 잎 아틀라스, 은행잎 · 벚꽃잎 타일, 간판, 정문 현판
.venv/bin/python tools/make_shrub_textures.py     # 관목 · 꽃의 겉면과 잔가지 아틀라스 (먼저 fetch_polyhaven.py models 2k periwinkle_plant)
.venv/bin/python tools/prepare_web_textures.py    # PBR 텍스처 -> web/public
blender -b --factory-startup --python blender/build.py            # 모든 GLB 빌드
blender -b --factory-startup --python blender/build.py -- blend   # + 편집용 assets_src/yonsei1997_campus.blend
blender -b --factory-startup --python blender/sky_bake.py         # 하늘 텍스처, 태양 방향, 해를 지운 환경광
node tools/bake_sun_shadows.mjs <포트>   # (web 에서 npx vite 를 띄운 뒤) 폰용 구운 해 그림자 · 걷는 면 높이
blender -b --factory-startup --python blender/characters.py       # 사람 14명 + 리그 2개 (assets_src/quaternius/ 필요)
```

- `blender/build.py` 에 `buildings landmarks road veg shrubs props polyhaven` 을 인자로 주면 그 부분만 다시 빌드합니다(`shrubs`: 나무를 빼고 관목만). `noao` 를 더하면 베이크를 건너뜁니다.
- 순서가 있습니다: 일반 건물과 랜드마크는 서로의 그림자를 상대의 마지막 GLB 에서 읽어 굽습니다. 한쪽을 크게 바꿨으면 `landmarks` → `buildings` → `landmarks` 로 돕니다. 그림자를 지거나 걷는 면이 바뀌면 마지막에 `bake_sun_shadows.mjs`.
- `bake_sun_shadows.mjs` 는 Playwright 의 Chromium 이 필요합니다(`npx playwright install chromium`).

## 소개 영상

`tools/trailer/` 는 게임 화면을 한 프레임씩 렌더링해 65초 영상(1920×1080, 30fps)을 만듭니다.
버드 아이뷰로 날다가 백양로로 내려가 걷고, 독수리상과 언더우드 동상을 둘러본 뒤 언더우드관 정원 위로 물러나며 끝납니다.

```bash
python3 tools/trailer/frame_server.py /tmp/frames-dir/frames &   # 프레임 받는 로컬 서버 (127.0.0.1:8765)
# npm run dev 로 띄운 게임의 브라우저 콘솔에 tools/trailer/record.js 를 붙여 넣고 끝날 때까지 기다림
python3 tools/trailer/make_video.py /tmp/frames-dir trailer/campus1997_trailer.mp4   # 자막을 넣어 MP4로
```

## 커밋과 이슈

커밋 메시지 · 이슈 댓글 규칙은 [`CLAUDE.md`](CLAUDE.md) 에 있습니다.
