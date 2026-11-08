---
name: update-snapshots
description: README(「사진과 비교」의 게임 화면, 「게임 화면」, 맨 위 그림)와 이웃 저장소 yonsei-anthology 의 memories.md 에 들어가는 게임 캡처를 지금 게임으로 다시 찍는다. 카메라는 tools/snapshots.json 에 있고 tools/snapshots.mjs 가 찍는다. 「README 캡처 다시」, 「스냅샷 업데이트」, 「비교 사진 다시 찍어」, 건물을 고친 뒤 캡처를 맞출 때 쓴다.
---

# 스냅샷 업데이트

README 와 문집 사이트(`../yonsei-anthology/src/content/memories.md`)의 게임 화면을 한 번에 다시 찍는다.

- 카메라 · 창 크기 · 계절 · 저장할 곳: `tools/snapshots.json` (맨 위 `_doc` 에 항목 설명)
- 찍기: `tools/snapshots.mjs` (Playwright Chromium, 떠 있는 vite 개발 서버에 붙음)
- 줄이고 붙여 JPEG 로 쓰기 · 검토 그림: `tools/snapshots_compose.py` (PIL)

| 이름 | 저장할 곳 | 쓰는 곳 |
|---|---|---|
| `compare/<이름>` | `docs/compare/<이름>_game.jpg` | README 「사진과 비교」의 오른쪽 칸 (왼쪽 `_photo.jpg` 는 그대로) |
| `compare/<이름>_1`, `_2` + grid | `docs/compare/<이름>_game.jpg` | 사진 두 장을 위아래로 둔 칸(2003년 사진) |
| `game/<이름>` | `docs/game/<이름>.jpg` | README 맨 위 그림과 「게임 화면」 |
| `compare/baekyangro`, `game/autumn_banners`, `anthology/underwood` | `../yonsei-anthology/src/content/memory-campus1997-2/3/4.jpg` | 문집 「1997년 신촌 캠퍼스 산책」 갤러리(1 은 실제 사진이라 찍지 않음) |

## 순서

1. **생성 파일이 최신인지 본다.** 건물 · 나무 · 땅을 고쳤는데 GLB 나 해 그림자를 다시 만들지 않았으면 캡처가 옛 모습이다. `TECH_NOTE.md` 「빌드」의 순서(`build_campus.py` → `blender/build.py -- landmarks` · `buildings` → `bake_sun_shadows.mjs`)대로 먼저 만든다.
2. **개발 서버를 띄운다.** 같은 작업 트리에서 다른 세션이 vite 를 띄워 두었으면 그 포트를 써도 된다. 새로 띄울 때:
   ```bash
   cd web && npx vite --port 5197 --strictPort      # 백그라운드로
   ```
   여러 vite 가 같은 `web/node_modules/.vite` 를 쓰면 three.js 가 두 번 실릴 수 있다. 그럴 땐 추적하지 않는 설정 파일로 자기 `cacheDir` 를 준다:
   `import base from './vite.config.js'; export default (e) => { const c = base(e); return { ...c, cacheDir: '<임시 폴더>/vitecache' }; };`
   그리고 `npx vite --config <그 파일> --port <포트> --strictPort`. 끝나면 `pgrep -fa "vite"` 로 pid 를 찾아 `kill <pid>` (`pkill -f` 는 자기 셸까지 죽인다).
3. **찍는다.**
   ```bash
   node tools/snapshots.mjs --port 5197                         # 전부 (약 5분)
   node tools/snapshots.mjs --port 5197 --only compare/library,game/   # 이름 또는 앞부분만
   ```
   찍은 PNG 는 `--raw` 폴더(기본 임시 폴더 `y97-snapshots`)에 남고, 끝에 compose 가 `out` 경로로 쓴다. `failed shader programs` 나 `console errors` 가 찍히면 먼저 고친다. 폰 경로 확인은 `--query '?touch' --no-compose`.
4. **본다.** 반드시 이미지를 열어 확인한다.
   ```bash
   python3 tools/snapshots_compose.py --sheet /tmp/y97-sheet.jpg            # 사진 | 게임 짝 전부
   python3 tools/snapshots_compose.py --sheet /tmp/y97-sheet.jpg library,union
   ```
   - 사진과 같은 자리 · 방향인지(건물 모서리, 창 줄, 지붕선의 자리), 나무 · 차 · 사람이 앞을 가리지 않는지
   - `game/` 은 UI(미니맵 · 버튼)가 보이고, 추억 카드 · 지도 · 「E 슛!」 안내가 떠 있는지
5. **카메라를 고칠 때**는 `tools/snapshots.json` 만 고친다(아래 「카메라 맞추기」). 한 장만 다시: `--only <이름>`.
6. **사진과 차이가 큰 곳**이 보이면 캡처만 바꾸고 끝내지 말고, 사용자에게 알리거나(요청 범위면) 외부 자료(연세춘추 · 학교 기록 · 옛 사진)를 찾아 건물을 고친 뒤 다시 찍는다. 근거는 `reference/고증.md`, 바뀐 내용은 새 소식(`CLAUDE.md` 규칙).
7. **커밋한다.**
   - 이 저장소: `docs/compare/*_game.jpg`, `docs/game/*.jpg`, 고쳤으면 `tools/snapshots.json`. 다른 세션이 같은 트리에서 일하고 있으면 내 파일만 `git add <경로>` 로. 메시지는 `CLAUDE.md` 의 커밋 규칙(80자, 접두사 없음, attribution 줄 없음). README 의 그림 경로가 그대로면 README 는 안 바뀐다.
   - 문집 저장소 `../yonsei-anthology`: `src/content/memory-campus1997-*.jpg` 만 바뀐다. `memories.md` 의 `<img width height>` 가 그림 크기와 같아야 하므로 크기를 바꾸면 그 값도 고친다. 그 저장소는 push 하면 GitHub Pages 로 배포되니 사용자가 push 를 원할 때 `git -C ../yonsei-anthology push origin main`.

## 카메라 맞추기

- `cam`(하늘 카메라)은 `x y` 와 높이 `dh`(그 자리 땅 위 m) 또는 `h`(절대 m), 바라보는 점 `tx ty` 와 `tdh` 또는 `th`, 세로 화각 `fov`. 캠퍼스 좌표는 x = 동, y = 북(m). 건물 자리는 `web/public/data/campus.json` 의 `buildings[].footprint`, 랜드마크는 `landmarks[].pos`.
- 사진과 맞추는 법: 사진에서 보이는 두 건물(또는 건물 모서리 둘)의 좌우 순서와 겹침으로 카메라가 선 쪽을 정하고, 바라보는 점을 사진 한가운데 있는 것에 둔 뒤, 크기는 `fov`, 올려다보는 정도는 `tdh` 로 맞춘다. 사람 눈높이 사진은 `dh` 1.6 ~ 1.7.
- 창 크기 `size` 는 사진의 가로세로 비에 가깝게, 저장 폭의 1.3 ~ 1.5배로 찍어 줄이면 계단 현상이 적다.
- `walk`(걷기)는 `x y yaw`(0 = 북, 동쪽으로 돌면 음수: 백양로를 따라 북쪽은 약 −0.26)와 등 뒤 카메라 `dist lift orbit`. 랜드마크 반지름(`landmarks[].r`) 안에 서야 `KeyE` 로 추억 카드가 열린다.
- 후보 카메라 여러 개를 비교할 때는 같은 형식의 임시 json(저장소 밖, `out` 없이)을 만들어 `node tools/snapshots.mjs --spec <그 파일> --raw <폴더> --no-compose` 로 찍어 보고, 맞는 값을 `snapshots.json` 에 옮긴다.

## 새 캡처를 더할 때

- README 에 새 「사진과 비교」 줄을 넣으면 `docs/compare/<이름>_photo.jpg`(사진, 폭 900 안팎)를 두고 `snapshots.json` 에 `compare/<이름>` 을 더한다. 출처는 `reference/출처.txt`, README 「출처 · 라이선스」.
- 문집이나 다른 문서에 쓰는 그림도 같은 파일에 `out` 경로만 달리해 더한다. 경로는 저장소 루트 기준이고, 폴더가 없으면 건너뛴다(이웃 저장소를 받지 않은 환경).
