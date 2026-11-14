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
형식과 쓰는 규칙은 [`CLAUDE.md`](CLAUDE.md) 에 있습니다. 캡처는 `web/public/assets/news/` 에만 둡니다.

## README · 문집 캡처

README 의 게임 화면(「사진과 비교」의 오른쪽 칸, 「게임 화면」, 맨 위 그림), 고증 문서가 가리키는 `docs/screenshots/`, 문집 사이트(`../yonsei-anthology/src/content/memories.md`)의
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
| `docs/` | README · 고증 문서에 쓰는 캡처 · 비교 사진 (모두 지금 게임 화면, 옛 화면은 새 소식에만) |
| `docs/compare/` | README 「사진과 비교」의 사진(`<이름>_photo.jpg`)과 같은 자리의 게임 화면(`<이름>_game.jpg`), 표의 왼쪽 · 오른쪽 칸에 하나씩 |
| `docs/game/` | README 맨 위 그림과 「게임 화면」의 캡처 |
| `docs/screenshots/` | `reference/고증.md` 가 가리키는 대상 가운데 `docs/compare/` 에 짝이 없는 것의 게임 화면 |
| `docs/reference/` | 고증 문서의 측정 그림(단면, 중심선 오차 막대) |

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
| `player.js` · `touch.js` | 걷기 · 카메라(등 뒤 3인칭, 눈높이 1인칭) · 충돌, 모바일 스틱 |
| `birdseye.js` | 캠퍼스 위로 날아가기 |
| `characters.js` · `armpose.js` · `life.js` · `talk.js` | 사람 모델과 애니메이션, 팔 IK, 군중 · 차 · 현수막 · 초소, 말풍선 대사 |
| `town.js` | 정문 밖: 성산로 · 철둑 · 창천동 · 신촌 로터리 모델을 장면에 넣음, 성산로 · 연세로 · 로터리의 차와 시내버스, 신호등 |
| `hoops.js` | 농구공 |
| `audio.js` | 소리: Web Audio 합성(바람 · 나뭇잎 · 새 · 분수 · 차 · 발소리 · 농구공 · 물보라), 카메라가 듣는 자리 |
| `birthday.js` | 활천대 앞 생일 축하(두 학생, 들어 올려 분수로) |
| `water/fountain.js` | 활천대 분수 물(Ultra Water) |
| `ui.js` · `labels.js` · `places.js` · `news.js` · `notes.js` | 화면 UI, 건물 이름표, 추억 카드, 새 소식 |
| `loading.js` | 첫 화면의 불러오기: 퍼센트 막대, 기다리는 동안의 삐삐 암호 · 캠퍼스 이야기 카드 |

## 구현 방식

### 지형과 배치

- OpenStreetMap 건물 외곽선과 도로, Copernicus GLO-30 고도 자료(건물을 걷어 냄, `tools/fetch_terrain.py`)로 캠퍼스를 만듭니다(`tools/build_campus.py`).
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
  - 청동(언더우드 동상의 몸, 독수리와 바위)은 정밀 원형을 빚어 가벼운 메시에 굽습니다(`blender/sculpt.py`).
    - 원형: 겹친 덩어리를 복셀 격자에서 합치고 주름 · 깃 · 점토 자국을 눌러 넣은 백만 삼각형대의 메시
    - 게임: 1만 ~ 1.5만 삼각형의 메시(`data/statues/<이름>.npz`)에 원형의 굴곡을 노멀맵으로, 풍화(하늘 보는 면과 빗물 길의 녹청, 골의 그을음, 닳은 모서리의 금속)를 색 · ORM 맵으로(`web/public/assets/textures/statues/`, 1024 px 세 장씩)
    - 재질: `materials.json` 의 `maps`(`bronze_underwood`, `bronze_eagle`). 노멀맵은 glTF 관례(OpenGL)라 웹에서 `normalScale.y = −1`
- 나머지 200여 동은 절차적 생성기 `blender/generic.py` 가 실제 외곽선 위에 세웁니다.
  - 창호(창틀 · 문설주 · 창대), 층 밴드, 파라펫, 옥상 설비, 녹색 방수 옥상, 물탱크, 상점 간판
  - 창의 7 %쯤은 미서기 한 짝을 열어 두고, 드물게 에어컨을 붙입니다(`blender/windows.py`)
  - 벽에는 선홈통, 땅을 따라 층지는 기단 띠, 뒷문과 환기구를, 동네 집 옥상에는 TV 안테나를 답니다(`blender/backs.py`, 고증 3.20). 건물 id로 씨앗을 준 자기 난수만 써서 `generic.py` 의 난수 순서는 그대로입니다.
  - 건물마다 현관(`porch`)이 있고 자리는 `build_campus.py` `_entry`. 1996년 졸업 앨범 사진의 현관들을 따랐습니다.
  - 계단은 걸어 오를 수 있는 보이지 않는 `walk_stairs` 메시를 따로 냅니다.
- 건물 · 랜드마크의 정점에는 `blender/bake.py` 가 AO, 처마 아래 비 자국, 햇빛 여부를 구워 `COLOR_0` 으로 내보냅니다. 웹은 이를 `bake` 속성으로 읽습니다.

### 정문 밖

- 성산로, 경의선 철둑과 연세로 굴다리, 창천동(고증 4.8). 자리는 `tools/gate_town.py`(`build_campus.py` 가 부름), 모양은 `blender/town.py`, 차는 `web/src/town.js`.
- 철도 선형과 창천동의 길 · 건물 외곽선은 `tools/fetch_gate_osm.py` 가 받은 `data/raw/osm_gate_south.json`(OSM API 의 상자 하나).
- 동네 집 1,600여 동은 상자와 모임지붕뿐이고 아틀라스 한 장(`town_atlas.jpg`: 띠 하나가 벽 한 층, 가로로 반복)으로 그립니다. 320 m 칸마다 한 메시.
- 철둑 비탈은 땅의 재질(`terrain_drape`)로 그리고, 둑 메시(`town_bank_*`)는 걷는 면 목록에 넣어 둑의 나무가 그 위에 섭니다.
- 성산로의 차는 먼 거리용 모델(`car_*_far`)을 한 메시로 합치고 재질 색을 정점에 적어 한 대가 draw call 하나입니다(바퀴는 돌지 않음). 백양로의 차는 그대로.
- 정문 앞 연석 안쪽에 보이지 않는 충돌 띠(`campus.json` `colliders`)가 있어 차도로는 나가지 못합니다.
- 땅 지도 밖의 근경 지형은 낮은 곳을 먼 도시와 같은 회색으로 칠합니다(`terrain.js`).

### 신촌 로터리

- 굴다리 남쪽 연세로에서 신촌 로터리까지(고증 4.10). 자리는 `tools/sinchon_rotary.py`(`build_campus.py` 가 `gate_town.layout` 뒤에 부름), 모양은 `blender/town.py`(`signs2` · `entrances`), 차 · 신호는 `web/src/town.js`.
- 길 선형 · 건물 외곽선 · 지하철 출입구는 `tools/fetch_rotary_osm.py` 가 받은 `data/raw/osm_rotary.json`(건물 관계는 바깥 고리마다 한 외곽선, id 10¹² + 관계 id × 10 + k).
- 땅: 5 m 격자(±800 m) 남쪽에 같은 방법의 조각 `terrain_south.bin`(x −600 ~ 400, y −1200 ~ −800 m, `campus.json` `terrain.south`). 웹 `Heightfield.setPatch` · `makeSouthTerrain`, Blender `common.ground` 가 읽고, 격자를 읽는 셰이더 가운데 벽의 흙 튐은 격자만, 해 그림자 높이(`bakedshadow.js` `sunTerrainH`)는 조각도 씁니다.
- 땅 칠: 캠퍼스 땅 지도 밖은 따로 그린 `ground_splat_town.png`(`campus.json` `tsplat`, 0.5 m: R 아스팔트, G 보도, B 지하철 계단 구멍). 칠하지 않은 곳(가운데 섬)은 잔디.
- 무작위: `random.Random(4802)` 하나. 4.8의 집 가운데 새 길에 걸리는 것은 `b[6] = −층수` 로 남겨 Blender 가 모양을 그대로 뽑고 그리지는 않음. 새 나무는 `trees` 끝에.
- 연세로 가게 줄(`yro_rows`, `random.Random(4805)`): 1996년 사진에서 읽은 집(`YRO_FIXED`)과 사진의 층수 섞임(`YRO_MIX`). 전 줄은 같은 흐름으로 뽑아 `b[6] < 0` 으로 두고, 새 줄은 `blocks` 끝에 더해 다른 집 · OSM 상자 · 채운 집과 Blender 의 집 모양 흐름이 그대로.
- 세로 간판(`town.vsigns`, `yro_wall_signs`)과 축제 현수막(`town.banner`)은 `blender/town.py` `yro_signs` · `yro_banner`, 아틀라스 `sign_yonseiro.png`(`make_textures.py sign_yonseiro`: 128 × 468 px 칸 16개 밑에 현수막 띠).
- 걷기: 성산로 북쪽 연석의 충돌 띠(`gate_town.py`)를 건널목 자리까지 이어서 연세로 · 로터리로는 건너가지 못합니다. 그 띠의 북쪽 가장자리(`campus.json` `town.limit`)보다 남쪽으로는 하늘 시점 · 지도 · 출발 목록에서도 내려서지 않고 정문에 섭니다(`main.js` `beyondGate`).
- 차: `town.lanes` 의 `stops` 가 [s, 신호 묶음, 단계]. 차마다 앞 16 m 안의 다른 길 차와 걷는 사람을 봄(성산로끼리는 전처럼 같은 길만). 신호 주기는 `town.signals`, 신호등은 `town.heads`.
- 연세로 보도의 사람은 `town.walks` 위의 두 번째 `Crowd`(`main.js` `townCrowd`, 씨앗 11, 폰 6명). 시점이 연세로에서 200 m 안일 때만 갱신합니다.
- 차는 시점에서 400 m 안의 것만 움직이고 서로를 봅니다(`town.js` `Street` `WAKE`). 나머지는 제자리에 서서 그리지 않습니다. 신호등도 380 m 밖이면 그리지 않고, 불빛 색은 바뀔 때만 올립니다.

### 걷기

- 충돌: 건물 외곽선(`main.js`. 지붕 있는 건물 · 체육관은 모델과 같은 최소 직사각형, 광혜원은 벽만), `campus.json` `colliders`, 나무 · 관목 · 소품 · 차의 원. 메시의 벽 · 기둥 · 낮은 턱은 걷는 사람 둘레의 광선(`player.js` `pushFromWalls`).
- 내려놓기: 하늘 시점 이름표의 「여기서 걷기」, 지도, 출발할 곳은 모두 `Colliders.walkOut` 을 거침. 0.5 m 격자로 충돌 사이 틈을 따라 30 m 밖까지 걸어 나갈 수 있는지 보고, 못 나가면 가장 가까운 나갈 수 있는 자리로. 내려놓을 자리가 건물 · 랜드마크 지붕 밑이면 그것도 막힌 것으로 봄(`main.js` `underRoof`).
- 이름표의 「여기서 걷기」는 출발할 곳 목록(`places.js`)과 같은 자리, 곧 현관 앞에서 문을 바라봄. 정문은 걷기의 출발점.
- 정문에서 걸어 들어갈 수 없는 곳(충돌 상자 기준 8 m² 넘는 것 19곳): 언더우드관 · 연희관 앞 정원의 회양목 울타리 잔디 칸, 정문 안 표석 화단(180 m²), 대강당 북쪽 주차장의 나무 섬, 진달래동산 덤불 틈. 모두 원래 들어가지 않는 꽃밭이라 그대로 두고 내려놓지만 않음.

### 재질

- 재질 정의는 `blender/materials.json` 한 곳입니다(= `web/public/data/materials.json`). Blender 는 미리보기용, 웹은 `MeshStandardMaterial` 로 다시 만듭니다.
- GLB 에는 형상 · UV · 재질 **이름**만 들어 있습니다. UV 는 미터 단위이고 `tile` 이 미터/반복입니다.
- PBR 텍스처는 Poly Haven(`tools/fetch_polyhaven.py`, `tools/prepare_web_textures.py`).

### 수목

- `blender/vegetation.py` 가 가지 골격 + 잎 카드로 일곱 수종을 만듭니다. 어린 느티나무 · 벚나무는 따로 만든 모델입니다.
- 수관 구형 노멀과 버텍스 AO, 계절별 잎 아틀라스(`tools/make_textures.py`).
- 230 m 밖의 나무는 실행 중에 렌더링한 임포스터(교차 판 + 위에서 본 판)로 바꿉니다(`world.js` `Forest`).
- 나무 · 임포스터 · 덤불 · 소품 · 세워 둔 차 · 먼 산 숲은 종류마다 InstancedMesh 하나로 캠퍼스 전체에 퍼져 있어, `world.js` `KitCuller` 가 넓힌 시야 안의 인스턴스만 버퍼 앞에 모아 그립니다. 정적 그림자 캐시와 해 그림자 굽기는 전체를 그립니다.
- 줄기와 잎은 카메라 가까이에서 디더링으로 비쳐 보이고, 고품질 화면에서는 TAA 가 점무늬를 고르게 섞습니다.
- 담쟁이는 잎 카드마다 위상과 매달린 길이를 정점에 담아 흔듭니다.
- 다듬은 관목 · 생울타리 · 꽃은 `blender/shrubs.py`: 다듬은 윤곽의 몸통(모서리 둥근 상자, 회전체)에 몸통 안에서 비스듬히 솟은 잔가지 카드.
  - 몸통은 이음매 없는 잎 무늬와 노멀 맵을 월드 좌표에서 세 방향으로 비춰 입힘(`web/src/hedges.js`, 폰은 색만): 한 줄로 겹친 생울타리 토막이 한 무늬로 이어짐
  - 카드는 뿌리 쪽 몸통의 노멀과 그늘을 받아 겉면과 같은 밝기, 뒷면을 볼 때도 노멀을 뒤집지 않음
  - 잎 · 꽃은 Poly Haven 「Periwinkle Plant」 스캔을 잘라 실제 크기로 다시 칠함(`tools/make_shrub_textures.py`)
  - 25 m 밖은 가벼운 모델 `<종류>_far.glb`(`shrubs.far_version`: 카드 셋에 하나, 몸통 40 %)

### 사람

- Quaternius 의 CC0 모듈러 캐릭터를 `blender/characters.py` 가 부품을 섞고 1997년 옷차림으로 칠해 14명을 만듭니다(sim-office 의 `tools/office-characters.py` 를 고쳐 씀). 키는 실제 크기(남 1.73 m, 여 1.61 m).
- 애니메이션은 남녀 리그 파일 둘(`rig-umc.glb` · `rig-women.glb`, 각 약 250 KB)에 들어 있습니다. 서기 · 걷기 · 뛰기 · 앉기는 모션 캡처를 리그에 옮긴 것입니다(`blender/mocap.py`, 자료는 `tools/fetch_mocap.py` 가 `assets_src/mocap/` 에 받음).
  - 클립: `walk-slow` · `walk` · `walk-fast`(남 0.80 · 1.38 · 1.60 m/s, 여 0.76 · 1.14 · 1.52 m/s) · `sprint`, `idle` · `idle-shift`(체중 이동) · `idle-look`(두리번) · `idle-fold`(팔짱) · `talk` · `phone`, `sit` · `sit-talk`. 손 흔들기(`emote-yes`) · 손 뻗기(`interact-right`)는 팩의 것, 고개 젓기(`emote-no`)는 `idle` 첫 자세에서 만듦
  - 원본과 구간은 `mocap.py` `CLIPS`(`characters.py -- --list` 가 표로 찍음). 남자 걸음은 CMU, 여자 걸음은 ACCAD, 서 있는 클립은 100STYLE · ACCAD, 앉기 · 대화는 Quaternius Universal Animation Library
  - 옮기는 법: 뼈마다 원본의 월드 회전을 휴지 자세 차이만큼 보정해 복사. 엉덩이 높이와 발 자리는 다리 길이 비로 줄이고, `Foot` · `PT`(Root 의 자식)를 원본 발목 궤적에서 직접 키한 뒤 다리를 2뼈 IK로 풂. 디딤 구간에서는 발을 땅에 고정. 치수는 빌드할 때의 휴지 뼈대에서 읽어, 비례(`BUILD`)를 바꿔도 다시 맞음
  - 걷기 · 뛰기는 제자리 주기(좌우 한 걸음씩, 양 끝을 섞어 이음)이고 모두 같은 발에서 시작. 클립마다의 지면 속도는 리그 extras `speeds`(JSON 문자열)
  - 서 있는 클립 15 fps, 걸음 24 fps, 뛰기 30 fps 로 재표본(걸음을 20 fps 로 하면 키 사이에서 정강이 끝과 `Foot` 뼈가 12 mm까지 벌어짐)
  - 클립을 고치거나 더한 뒤에는 사람 GLB에 리그의 액션을 입혀 디딤 구간의 발 미끄럼 · 발 높이 · 이음매 · 손목이 몸통에 드는 프레임을 재고, 앞 · 옆 연속 프레임을 렌더해 봄
- 게임 쪽(`characters.js` `locomotion`): 이동 속도에 가장 가까운 걸음 클립을 고르고(속도가 그 클립의 0.78 ~ 1.28배를 벗어날 때만 바꿈) 재생 속도를 맞춰 발이 미끄러지지 않습니다. 걸음끼리 · 뛰기로 넘어갈 때는 걸음의 같은 지점에서 이어 받습니다. 서 있을 때는 `a.stand` 의 클립을 틉니다.
- 머리와 얼굴은 팩의 것을 그대로 쓰지 않고 `characters.py` 「1997 heads」가 다시 만듭니다.
  - 얼굴형: 두개골이 온전한 머리 하나(남 Worker, 여 Adventurer)를 한 단계 세분하고 면을 눅임. 코는 짧게(높이 · 콧대 · 콧방울은 사람마다), 긴 턱은 줄이고 볼 ~ 턱을 넓혀 둥글게
  - 눈 · 눈썹 · 입: 형상이 아니라 선 그림. `blender/faces.py` 가 14명의 얼굴을 아틀라스 한 장(`people/faces.png`, 1024², 4 × 4칸, RGBA 87 KB)에 그림
    - 얼굴 앞면의 면만 자기 칸의 UV, 나머지(몸 · 옷 · 머리카락 · 안경)는 빈 칸. GLB 에는 피부 부품에만 `TEXCOORD_0`(16비트)
    - 그림의 색은 정점 색에 곱하는 값(선은 피부를 어둡게), 알파는 흰자(0 = 흰색). 그래서 군중의 피부색을 바꿔도 선이 따라감
    - 윗눈꺼풀 한 줄, 흰자 위의 짙은 눈동자와 반사 점, 눈썹 한 줄, 작은 입 한 줄. 눈은 실제보다 조금 큼(가로 3.1 cm, 치수는 고증 4.9)
    - 그림만 고칠 때: `blender -b --factory-startup --python blender/characters.py -- faces` (GLB 는 그대로)
  - 사람마다 눈꺼풀(홑꺼풀 · 속쌍꺼풀 · 쌍꺼풀) · 눈꼬리 · 눈썹(굵기 · 길이 · 꼭대기 · 꺾임 · 꼬리) · 코 · 입꼬리 · 턱 폭을 달리함(`PEOPLE` 의 `face`). 교수님 · 교직원은 주름 선
  - 머리카락: 정수리에서 내려오는 62열의 껍질(앞머리 6°, 관자놀이 ~ 귀 둘레 4°, 뒤 7 ~ 10°). 방위마다 끝 높이 · 두께를 준 표(`HAIR_STYLES`)가 5:5 · 6:4 · 2:8 가르마의 긴 앞머리 · 투블럭컷(긴 윗머리 껍질 아래에 짧게 친 속 껍질 `under`) · 앞을 세워 넘긴 짧은 머리 · 긴 생머리 · 귀 뒤로 넘긴 단발 · 쇼트커트 · 윗머리만 묶은 긴 머리를 만듦. 브릿지는 몇 열만 다른 재질로. 늘어진 부분은 안쪽 면이 있고, 가려진 두피는 지움. 비틀린 사각형은 바깥으로 접히는 대각선으로 나눔(안으로 접히면 피부가 비침)
  - 안경: 14명 모두 한 벌(가는 테 형상, 두께 2.4 mm). 쓰는지는 게임이 정함(아래). 같은 안경을 앞에서 본 선 그림을 작은 아틀라스(`people/faces_rims.png`, 512², 같은 4 × 4칸)에 따로 그림
  - 옷: 한 벌이 한 색인 팩의 옷에서 줄무늬 · 깃 · 긴소매 · 치마는 `PEOPLE` 의 `paint` 가 T 자세의 상자로 잘라 다른 재질로 칠함(고증 4.11). 상자에 닿는 면만 자름
  - 티셔츠의 깃: 품을 넓힐 때 목 둘레는 그대로 두고, 팩의 높은 테를 낮춤(`loosen` 의 `COLLAR`)
  - 신발: 흰 운동화의 옆 줄 · 뒤꿈치 · 끈(`trainers`), 캔버스화의 고무 앞코 · 끈(`canvas`)도 `paint` 로
  - 재질 이름은 Skin · Hair · Glasses(+ Band · Bridge), 칠한 곳은 Stripe · Stripe2 · Collar · Skirt, 신발은 Bar-feet · Lace-feet · Sole-feet. 모두 `Head` 뼈에 붙어 가방 맞춤 · 팔 IK 는 전과 같음. 턱 아래로 늘어진 긴 머리는 끝으로 갈수록 `Neck` · `Chest` 를 따름(`hair_follow`, 뒤쪽은 목덜미부터): 고개를 저어도 등에 걸친 끝은 그대로
  - 한 명 약 6,500 ~ 7,900 삼각형
- 몸과 자세(고증 4.13): 팩의 몸을 그대로 쓰되 휴지 자세를 고칩니다(`characters.py` `relax_fingers`). 리그와 14명이 같은 값을 써서 클립이 그대로 맞습니다.
  - 손: 손가락 마디 2 ~ 4를 굽힌 모양이 휴지 자세(`FINGER_CURL`). 1번 뼈는 손허리뼈라 그대로. 클립에 손가락 채널은 없음
  - 비례(`BUILD`): 어깨 관절을 바깥으로, 위팔 · 아래팔을 1.06배, 남자의 고관절과 발(`Foot` · `PT`: Root 의 자식)을 안으로. 옮기는 뼈는 부모 꼬리에서 떼고(`use_connect`), 자세를 메시에 적용한 뒤 휴지 자세로 삼음
  - 손은 손목에서 0.88배, 손가락은 첫 마디에서 다시 0.88배(자세 뼈의 크기로). 목 · 여자 허리는 뼈는 두고 메시만 넓힘(`shape_body`: 가중치가 아니라 높이와 목 축에서의 거리로, 머리 · 몸 · 깃이 함께 움직이게)
  - 팔: 팩의 손 흔들기 · 손 뻗기 클립에서 쉬는 쪽 위팔을 몸 쪽으로, 여자는 아래팔을 길이 축으로(`ARMS_IN`, `arms_in` 이 키마다 다시 씀)
  - 고칠 때 빨리 보기: `-- <id> rigs` 로 빌드(한 명 3초)하고, 사람 GLB에 리그의 액션을 입혀 Workbench 로 렌더
- 바지(고증 4.13): 팩의 바지를 넓히지 않고 다시 재단합니다(`cut_trousers`, `CUTS`). 빌드한 휴지 자세에서 바지 면을 1 cm마다 잘라 바깥 · 안 · 앞 · 뒤 윤곽을 재고, 팽팽히 당긴 선에 여유를 더한 네 선 사이로 단면을 맞춥니다. 재단은 남녀마다 일자 · 와이드 · 정장이고, 와이드를 입는 사람은 `PEOPLE` 의 `cut='wide'`.
  - 바지의 정점마다 다리에서의 자리를 정점 속성 `_LEG`(4바이트: 앞뒤, 안팎, 높이, 바지인지)로 내보냄. 바지가 없는 부품에서는 뺌
- 그늘: `occlude` 가 정점마다 자기 몸에 가리는 정도를 구워 정점 속성 `_OCC`(바이트 0 ~ 255)로 내보냅니다. Blender 임포터가 정규화된 사용자 속성을 읽지 못해 정규화하지 않았습니다.
- 단색 부품을 정점 색 메시 하나로 합쳐 한 명당 draw call 1번(재질 하나에 얼굴 아틀라스 한 장). 화면 밖이면 그리지 않습니다.
  - 정점 속성 `part`(거칠기, 갈래: 옷 0 · 피부 1 · 머리카락 2 · 딱딱한 것 3, 그늘). 가방(`bags.js`)은 딱딱한 것, 그늘 0
  - 눈 깜박임: 얼굴 칸의 눈 자리를 피부로 덮고 속눈썹 선을 그림(셰이더). 사람마다의 박자는 속성 `glass` 에 함께(안경 0 ~ 2 + 4 × 박자 0 ~ 15 + 64 × 청바지 워싱 0 ~ 3), 시계는 바람의 `uWindT`
  - 셰이더(`characters.js` `PERSON_MAT`): 그늘, 옷의 물빛 · 보풀 빛 · 주름, 피부 윤기, 머리카락 가닥. 주름과 가닥은 텍스처가 아니라 휴지 자세의 자리(`vRest`)로 그린 높이를 화면 미분으로 범프. 폰은 주름 · 가닥 없이
  - 바지: 속성 `leg`(모델의 `_LEG`)로 솔기 · 밑단 · 허리띠 · 주머니 선과 청바지 워싱을 그림. 워싱의 세기는 바지 색이 `JEANS` 의 어느 것인지로(`washOf`, 군중은 `crowdLook` 의 색). 폰도 같음
- 군중 행동(걷기, 멈춤, 무리, 인사, 벤치에 앉기, 공중전화 줄)은 `life.js`, 대사는 `talk.js`.
  - 서 있는 사람은 6 ~ 16초마다 서 있는 클립을 바꿉니다(`POSES`: 서기 · 체중 이동 · 두리번 · 팔짱, 줄 선 사람은 두리번이 많음). 서 있는 클립끼리는 0.9초에 걸쳐 넘어갑니다(클립마다 발 자리가 다름)
  - 자기 대사가 떠 있는 동안은 `talk`(앉은 사람은 `sit-talk`), 공중전화 칸의 사람은 `phone`. 손에 가방을 든 사람은 `talk` · 팔짱을 하지 않고, 통화하는 사람은 손가방을 들지 않음
- 군중은 사람마다 키 · 몸집 · 옷 색 · 피부색 · 머리색 · 안경을 달리합니다(`characters.js` `crowdLook`). 얼굴의 선은 그림이 피부색에 곱해져 따라가고, 안경은 열에 셋(교수님은 일곱)이 씁니다. 색만 다른 지오메트리를 따로 두고 나머지 버퍼(인덱스도)는 함께 씁니다. 인덱스는 안경의 삼각형을 맨 뒤에 두어, 안경을 안 쓴 사람은 그 앞까지만 그립니다. 주인공 · 운전자 · 생일 장면의 두 학생은 모델 그대로입니다.
- 먼 안경: 테가 화면에서 `RIM_PX` 픽셀(폰 1.2, 데스크톱 0.35)보다 가늘어지면 형상은 그리지 않고(`rimLod`, 거리와 화면 높이로 사람마다), 얼굴에 `faces_rims.png` 의 선을 밉맵으로 그립니다(가까이서부터 서서히). 누가 어떤 테를 쓰는지는 속성 `glass`(0 없음 · 1 금속 · 2 뿔테). 폰은 안티에일리어싱이 없어 1픽셀보다 가는 테가 프레임마다 켜졌다 꺼졌습니다
- 앉은 사람은 `sit` 클립의 엉덩이 높이를 재서 벤치 앉는 면(0.43 m)에 맞추고, 머리는 앉을 때의 자세에서 돌립니다.

### 소리

- `audio.js` 가 잡음 버퍼와 오실레이터로 모든 소리를 합성합니다. 녹음 파일이 없어 내려받을 것도, 라이선스도 없습니다.
- 듣는 자리는 카메라입니다. 분수 · 차 · 새 · 다른 사람의 발소리는 `PannerNode` 로 제자리에서 들립니다.
- 내 발소리는 걷기 · 뛰기 클립에서 발 뼈가 내려오는 순간에 내고, 땅 종류는 `ground_splat.png`(포장 · 흙 · 잔디)에서 읽습니다.
- 다른 모듈은 콜백으로 알립니다: `birds.onTakeOff`, `ball.onSound`, `birthday.onSplash`.
- 크기를 맞출 때는 헤드리스 Chromium(`--autoplay-policy=no-user-gesture-required`)에서 `sound.tap`(AnalyserNode)을 녹음해 대역별 크기를 잽니다.

### 자동차

- `blender/cars.py`. 단면을 몇 cm 마다 이어 붙이는 로프트 방식으로 차체 · 범퍼를 만들고, 램프는 차체 표면 위에 깔아 둥근 모서리를 따라 휩니다.
- 운전석의 인물이 꼿꼿이 앉으므로 차는 실제보다 7 % 크게 내보냅니다(`CAR_SCALE`).
- 도장은 클리어코트 재질, 바퀴는 달린 거리만큼 굴러가고 감속하면 브레이크등이 켜집니다.
- 세워 둔 차는 20 m 밖에서 `car_<종류>_far.glb` 로 그립니다(`build.py` 의 `cars` 단계): 10° 안으로 굽은 면을 재질 경계 안에서 합치고 바퀴만 접어, 삼각형이 5분의 1.
- 달리는 차의 길은 두 고리입니다(`tools/build_campus.py` `TR_E` · `TR_W` · `TRAFFIC` → `campus.json` `traffic.loops`, `web/src/main.js` 가 백양로 두 차로에 이음): 백양로 → 삼거리에서 오른쪽으로 용재관 옆 · 성암관 동쪽 · 대우관 별관 동쪽을 돌아 대우관 뒤 주차장, 또는 왼쪽으로 스팀슨관 서쪽 길 · 화단 섬 · 한경관 앞을 지나 핀슨관 옆 주차 칸 → 같은 길의 반대쪽으로 정문까지(고증 2.9).
  - 빈 주차 칸마다 차로 하나를 만듭니다(`loops[].stalls`: 고리에서 꺾는 점 `i`, 칸으로 드는 길 `a`, 후진해 나오는 길 `b`, 고리로 돌아오는 점 `j`). 차는 칸에 섰다가(`lane.stops`) 후진해(`lane.rev`) 나옵니다.
  - 차로가 달라도 자기 길 앞에 선 차를 기다립니다(`web/src/life.js` `Traffic.update` 의 「The car in the way」). 길을 고치면 헤드리스로 2 ~ 3분 돌려 오래 멈춘 차가 없는지 봅니다.
  - `Path.setLimits`: 구간마다의 제한 빠르기에 굽은 곳(옆 가속도)과 미리 줄이는 거리를 더한 1 m 간격 표. `Path.setTracks`: 두 바퀴 자리의 땅 높이.
  - 차는 네 바퀴 자리의 땅에 맞춰 앞뒤 · 좌우로 기웁니다(`life.js` `Traffic`, 세워 둔 차의 `parkedMatrix` 와 같은 식). 5 m 지형 격자는 비탈을 가로지르는 길을 옆으로 기울게 담으므로, 바퀴 자리가 지나는 격자 칸의 꼭짓점을 길 가운데 높이로 맞춥니다(`TR_LEVEL`). 빌드가 좌우 기울기 4° 넘는 구간을 찍습니다.
  - 길을 고치면 빌드 끝의 `traffic: wheel tracks off the asphalt` 가 0인지 봅니다(바퀴 자리가 아스팔트 밖으로 나가는 점).
  - 정문 밖 한 자리에서 한 바퀴가 끝나고 시작하므로, 나간 차는 숨겼다가 몇 초 뒤 들여보냅니다(`c.away`). 걷는 사람이 차로를 건너면 기다립니다.

### 분수

- Ultra Water(`web/src/water/ultra-water/`)의 FFT 물결 시뮬레이션과 바닥 빛무늬를 분수 크기(64² 격자, 4.5 m ~ 19 cm 네 층)로 줄여 씁니다(`web/src/water/fountain.js`).
- 바닥 · 벽은 같은 셰이더에서 굴절된 시선으로 레이트레이스합니다.
- 분수가 화면에 보이고 70 m 안쪽일 때만 계산합니다.

### 로딩 화면

- `loading.js` 가 진행률을 두 가지로 잽니다.
  - 받기: 모델 · 데이터는 `fetchCounted` 가 스트림을 읽으며 바이트를 세고(`world.js` `prefetch`, `main.js` `json` · `bin`), 텍스처는 `<img>` 로 받으므로 개수 × 평균 크기(`materials.js` `texCount`)로 셉니다. 데스크톱 기준 모델 · 데이터 25 MB, 텍스처 29 MB.
  - 처리: `main.js` 의 `progress(label, weight)`. 가중치는 그 단계가 데스크톱에서 걸리는 시간(1 = 0.01초)이고 합이 `STEPS` 입니다.
- 받기의 몫은 망 속도로 정합니다. 처음 2초(또는 받기가 그 전에 끝나면 전체)의 속도로 받는 시간을 어림해 `받는 시간 / (받는 시간 + WORK_S)` 로 둡니다. 캐시된 방문은 거의 처리, 느린 망은 거의 받기입니다.
- 마지막 「첫 장면을 그리는 중」(약 2초)은 셰이더 · 그림자를 한꺼번에 올리느라 페이지가 멈춥니다. 막대는 `transform` 전환으로만 움직여(`loading.coast`) 그동안에도 흘러갑니다.
- 모델을 더하거나 단계가 바뀌면 `window.__y97.loading.state.marks`(단계마다의 시각)로 가중치와 `STEPS`, `WORK_S` 를 다시 맞춥니다.
- 대기 카드(`#waitbox`)는 삐삐 퀴즈입니다. 뜻을 보이면 삐삐 화면(`<input inputmode="numeric">`)에 번호를 누르고, 자릿수가 차면 맞는지 봅니다(폰 숫자 자판에는 Enter 가 없음). 맞혀야 다음 문제로 가고, 두 번 틀릴 때마다 답의 숫자 하나를 화면에 흐리게 보입니다. 문제는 `loading.js` 의 `CODES` 입니다.
  - 데스크톱에서는 첫 화면 어디서든 숫자를 치면 삐삐 화면으로 들어갑니다.
  - 걷기를 시작할 수 있게 되면 카드는 접힙니다. 숫자를 한 번이라도 눌렀으면(`.played`) 남습니다.

### 농구

- 림 · 그물 · 백보드는 코트 모델(`blender/landmarks.py`)에, 공 물리는 `hoops.js`, 두 손 IK 는 `armpose.js`.

### 렌더링

- three.js PBR, HDRI 하늘과 환경광. 환경 이미지의 해 원반은 지우고 그 빛은 그림자가 드는 `DirectionalLight` 로 옮겼습니다(`blender/sky_bake.py`, `main.js`).
- 지형 스플랫 셰이더: 잔디 · 아스팔트 · 보도블록 · 흙과 마른 잔디 층(`ground_dry.png`).
- 그림자
  - 4096² 섀도 맵. 해는 고정이므로 정적인 것은 캐시하고 매 프레임엔 가까운 사람 · 차만 그립니다(`shadows.js`).
  - 캠퍼스 전체의 땅 그림자를 한 장으로 구워 둡니다(`bakedshadow.js`, `tools/bake_sun_shadows.mjs`). 섀도 맵 밖과 폰에서 씁니다.
    - 캠퍼스 칸(x −440 ~ 560, y −505 ~ 745 m, 31 cm)의 동쪽에 정문 밖 · 연세로 · 신촌 로터리(x −845 ~ 701, y −1195 ~ −505 m)를 70 cm 텍셀로 세 조각 내어 위아래로 붙였습니다(3968 × 4000, 밉맵까지 21 MB). 재질마다 텍스처를 하나 더 읽지 않게 한 장에 둡니다.
    - 그 땅 높이는 근경 격자와 그 남쪽 조각(`terrain_south.bin`)으로 읽습니다.
  - 폰은 섀도 맵이 일부 GPU 드라이버를 죽여서 끄고 블롭 그림자를 씁니다.
  - 데스크톱 HQ 는 PCSS(해의 시직경에 따른 부드러운 반영).
- 대기: 높이 안개와 구름 그림자를 모든 재질에 셰이더 패치로 넣습니다(`materials.js` `ATMOS`).
- 후처리(`post.js`): N8AO → TAA(서브픽셀 지터 · 깊이 재투영) 또는 SMAA → 두 단계 블룸 → 1997 필름 → AgX 톤매핑. 폰은 `RenderPass` + 4x MSAA 만.
- 셰이더 패치는 `materials.js` `patchShader` 로 쌓습니다. 캐시 키를 함께 관리해 같은 프로그램이 여러 번 컴파일되지 않게 합니다.
- 폰은 텍스처를 1024 이하로 줄여 올립니다(2K 세트는 밉맵 포함 약 1 GB).

### 성능: 정문 밖 · 신촌 로터리

2026-11-11. 헤드리스 Chromium(인텔 GPU, ANGLE Vulkan)에서 CPU를 4배 느리게 하고, 시점마다 60 프레임을 `record.step` 으로 넘기며 1픽셀을 읽어 GPU까지 끝낸 시간을 쟀습니다. 폰 경로는 `?touch`(960 × 432 px, 배율 1.5). 두 번씩 번갈아 잰 중앙값이며, 다른 세션이 함께 돌아 프레임 시간은 ±30 % 흔들립니다. 실제 폰(Pixel)의 fps 는 아직 재지 못했습니다.

정문 밖 · 로터리가 더한 것(폰 경로, draw call · 삼각형 · GPU 시간):

| 시점 | 정문 밖 전 (45a5e52) | 로터리 전 (4689e2c) | 로터리 뒤 (ade09d1) |
|---|---|---|---|
| 정문에서 남쪽 | 30 · 33만 · 12.8 ms | 71 · 48만 · 15.4 ms | 99 · 66만 · 17.6 ms |
| 하늘에서 정문 위 | 30 · 31만 · 10.6 ms | 82 · 49만 · 10.9 ms | 107 · 72만 · 15.8 ms |
| 백양로 가운데 · 언더우드관 앞 | 1,228 · 568 call | 1,279 · 588 call | 1,274 · 592 call |

캠퍼스 안 시점에서는 정문 밖이 그려지지 않고(320 m 칸 메시가 시야 밖), CPU 쪽 일만 남아 있었습니다. 그것을 줄인 결과(한 프레임, CPU 4배):

| | 전 | 뒤 |
|---|---|---|
| 차 갱신, 언더우드관 앞 (폰 27대 · 데스크톱 67대) | 0.21 · 0.65 ms | 0.02 · 0.01 ms |
| 차 갱신, 정문 앞 (폰) | 0.26 ms | 0.06 ms |
| 연세로 사람 갱신, 언더우드관 앞 | 0.08 ms | 0 |
| 충돌 밀어내기 한 번, 정문 앞 · 언더우드관 앞 | 0.27 · 0.29 ms | 0.0007 · 0.004 ms |
| 언더우드관 앞 draw call (신호등) | 592 | 589 |

- 충돌: 칸 안 콜라이더가 정문 앞 175개(연세로 둘레 얇은 상자), 언더우드관 앞 1,181개(관목 · 나무) → 3개, 236개를 상자로 거른 뒤 몇 개. 충돌 상자 5,038 → 90개.
- 땅 조각 `terrain_south`: 정점 1.6만 · 삼각형 3.2만, draw call 하나(땅 재질, 시야 밖이면 빠짐), 파일 65 KB.
- `ground_splat_town.png`: 파일 32 KB, GPU 데스크톱 8.9 MB · 폰 5.5 MB(1008 × 1024로 줄임, 밉맵 포함).
- 구운 해 그림자에 정문 밖을 더한 뒤: GPU 17.1 → 21.2 MB(밉맵 포함), 파일 2.2 → 2.5 MB.
- 정문 밖 GLB: 0.59 MB(로터리 전) → 1.19 MB. 연세로 세로 간판 · 현수막: draw call +3, 삼각형 +1천.
- 같은 날 정문을 28 m 북쪽으로 옮기고 성산로를 열 차로로, 로터리에 정류장 · 서 있는 사람을 더한 뒤(폰 경로, 정문 y −412 m에서 남쪽): 125 call · 68만, 하늘에서 정문 위 103 call · 72만.
  정문 밖 사람은 폰 22명(걷는 6, 로터리 앞에 서 있는 16), 데스크톱 79명이고, 시점 190 m 안에서만 장면에 듭니다.
- 땅 셰이더가 읽는 텍스처: 폰 17 → 14개, 데스크톱 18 → 15개(로터리의 `uTSplat` 로 16개를 넘었었음). WebGL 2가 보장하는 것은 16개라, 16개만 주는 GPU(ANGLE D3D11 · Metal, GLES 안드로이드 다수)에서는 땅 셰이더가 컴파일되지 않을 수 있었습니다.
  - 잔디 · 흙 · 아스팔트 · 보도블록의 법선 넷(x, y만 읽음), 숲 바닥 색, 잔디 밝기를 GPU에서 세 장으로 묶음(`terrain.js` `groundPacks`, `materials.js` `packTextures`). 잔디 블레이드(`grass.js`) · 길가 잔디(`verge.js`)도 묶은 잔디 밝기를 읽음
  - 원본 이미지는 라이브러리 재질(잔디 · 흙 · 아스팔트 · 보도블록)이 함께 써서 GPU에 남으므로 묶은 장은 그 위에 더해짐: 법선은 원본의 절반(1024 px, 폰 512 px), GPU 데스크톱 +28 MB · 폰 +3 MB(밉맵 포함, 숲 바닥 원본 6 MB를 뺀 값)
  - 화면은 전과 같음(같은 카메라의 전 · 후 차이: 잔디 화면 평균 0.3, 99 % 3 / 255)

## 에셋 파이프라인 (다시 빌드하기)

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy shapely pillow
python3 tools/fetch_polyhaven.py textures 1k <이름…>   # CC0 텍스처/모델/HDRI 내려받기 (assets_src/)
.venv/bin/python tools/fetch_terrain.py near && .venv/bin/python tools/fetch_terrain.py far   # Copernicus GLO-30 (data/raw/copernicus/, git 밖)
.venv/bin/python tools/build_campus.py            # OSM + 지형 -> data/campus.json, 지형 bin, 스플랫맵
.venv/bin/python tools/make_textures.py           # 잎 아틀라스, 은행잎 · 벚꽃잎 타일, 간판, 정문 현판, 정문 밖 동네 아틀라스 · 연세로 간판 · 로터리 방향 표지
.venv/bin/python tools/make_shrub_textures.py     # 관목 · 꽃의 겉면과 잔가지 아틀라스 (먼저 fetch_polyhaven.py models 2k periwinkle_plant)
.venv/bin/python tools/prepare_web_textures.py    # PBR 텍스처 -> web/public
blender -b --factory-startup --python blender/build.py            # 모든 GLB 빌드
blender -b --factory-startup --python blender/build.py -- blend   # + 편집용 assets_src/yonsei1997_campus.blend
blender -b --factory-startup --python blender/sky_bake.py         # 하늘 텍스처, 태양 방향, 해를 지운 환경광
node tools/bake_sun_shadows.mjs <포트>   # (web 에서 npx vite 를 띄운 뒤) 폰용 구운 해 그림자 · 걷는 면 높이
python3 tools/fetch_mocap.py                                      # 사람 리그의 모션 캡처 원본 (assets_src/mocap/, 33 MB)
blender -b --factory-startup --python blender/characters.py       # 사람 14명 + 리그 2개 (assets_src/quaternius/ · assets_src/mocap/ 필요)
blender -b --factory-startup --python blender/build.py -- statues   # 청동 조각상의 원형 → 메시 · 텍스처 (assets_src/blender-human-base-meshes/ 필요, 출처.txt)
```

- `blender/build.py` 에 `buildings statues landmarks road town veg shrubs props cars polyhaven` 을 인자로 주면 그 부분만 다시 빌드합니다(`statues`: 청동 조각상의 원형을 빚어 메시와 텍스처로 구움, 하나에 2 ~ 3분. `landmarks` 는 구운 메시를 읽기만 하니 원형을 고쳤으면 `statues` → `landmarks`, `town`: 정문 밖 `campus_town.glb` 와 시내버스 `props/bus.glb`, `shrubs`: 나무를 빼고 관목만, `cars`: 다른 소품을 빼고 차만). `noao` 를 더하면 베이크를 건너뜁니다.
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

활천대 생일 영상(약 40초)은 `reference/활천대_공사전_연세대블로그.jpg` 에서 같은 카메라의 게임 화면으로 번지듯 바뀐 뒤 `birthday.js` 의 장면을 찍습니다.
던지는 순간은 게임 시간을 늦춰 슬로 모션으로 찍고, 소리(분수 · 물보라 · 오르골 「생일 축하합니다」)는 합성합니다.

```bash
node tools/trailer/birthday.mjs /tmp/bday --port 5197                    # (web 에서 npx vite 를 띄운 뒤) 게임 프레임
python3 tools/trailer/birthday_video.py /tmp/bday trailer/birthday.mp4   # 사진 → 게임 전환, 자막, 소리
```

## 커밋과 이슈

커밋 메시지 · 이슈 댓글 규칙은 [`CLAUDE.md`](CLAUDE.md) 에 있습니다.
