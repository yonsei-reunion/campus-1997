---
name: regen
description: 생성 파일(campus.json 두 벌, 지형, 땅 지도, GLB, 해 그림자)을 소스에서 다시 만든다. tools/build_campus.py → blender/build.py -- landmarks → buildings → landmarks → tools/bake_sun_shadows.mjs 의 순서와, 앞뒤 확인(vite 포트, 다른 세션의 Blender, 나무 · 관목 · 소품 · 차를 자리로 비교, Y97_WORK_DUMP 대조, materials.json 웹 사본, WebP · 폰용 텍스처)을 한 번에 한다. 「다시 만들어」, 「생성 파일 갱신」, 「GLB 다시 빌드」, 「해 그림자 다시 구워」, build_campus.py · blender/ 를 고친 뒤 게임에 반영할 때 쓴다.
---

# 생성 파일 다시 만들기

규칙은 `CLAUDE.md` 「생성 파일과 다시 만들기」, 전체 명령은 `TECH_NOTE.md` 「에셋 파이프라인 (다시 빌드하기)」에 있다. 여기는 그 순서를 따라 하는 절차다.

- `$S`: 이 세션의 스크래치 폴더(로그 · 기준 파일을 둘 곳. 저장소 안에 두지 않는다)
- 전부 저장소 루트에서 돌린다. `build_campus.py` 는 약 1분, Blender 세 번(`landmarks` · `buildings` · `landmarks`)은 다른 일이 없을 때 8분쯤, 굽기는 30초쯤

## 무엇을 돌릴지

| 고친 것 | 돌릴 것 |
|---|---|
| `tools/build_campus.py` 와 그것이 부르는 `tools/*97.py` · `gate_town.py` · `sinchon_rotary.py` · `muak.py` … (자리 · 땅 · 심기 · 차) | `build_campus.py` → 아래 Blender 부분 가운데 그 데이터를 읽는 것 → 굽기 |
| 일반 건물(`blender/generic.py`), 건물 목록 · 외곽 · 층수 | `-- buildings` (크게 바꿨으면 `landmarks` → `buildings` → `landmarks`) |
| 랜드마크 건물 · 데크 · 계단 · 옹벽 · 주차선 · 노면 칠(`blender/landmarks.py`, `campus.json` 의 `parking` · `road_paint` · `med_west` …) | `-- landmarks` |
| 백양로 단면 · 연석(`blender/road.py`) | `-- road` (`baekyangro.glb`, `road_meta.json`) |
| 정문 밖 동네 · 연세로 · 로터리(`blender/town.py`) | `-- town` (`campus_town.glb` · `campus_town_ground.glb` · `props/bus.glb`) |
| 관목(`blender/shrubs.py`) / 소품 / 차 | `-- shrubs` / `-- props` / `-- cars` |
| 청동 조각상의 원형(`blender/sculpt.py` · `statues.py`) | `-- statues`(하나에 2 ~ 3분) → `-- landmarks` |
| 간판 · 현수막 · 잎 아틀라스(`tools/make_textures.py`) | `.venv/bin/python tools/make_textures.py <이름>` (이름을 꼭 준다) |
| `blender/materials.json` | `.venv/bin/python tools/prepare_web_textures.py` (웹 사본을 다시 씀) |

- **인자 없는 `blender/build.py` 와 `-- veg`, 이름 없는 `make_textures.py` 는 돌리지 않는다.** 나무와 잎 아틀라스는 씨앗이 `hash(str)` 라 프로세스마다 달라, 모든 나무가 바뀐다. 새 나무 · 새 아틀라스만 이름으로 만든다.
- 그림자를 지는 것이나 걷는 면이 바뀌면 마지막에 꼭 굽는다.

## 순서

1. **앞 확인.**
   ```bash
   git status --short                                    # 생성 파일이 이미 바뀌어 있으면 다른 세션이 만드는 중일 수 있음
   ps -eo pid,etime,args | grep -E "[b]lender -b|[b]uild_campus\.py"   # 다른 세션의 빌드(읽기만. 죽이지 않는다)
   ss -ltnp | grep -E ':5[0-9]{3} '                      # 떠 있는 vite 포트
   ```
   - 빌드가 보이면 어느 트리의 것인지 본다: `readlink /proc/<pid>/cwd`(다른 worktree 의 것이면 상관없다). 같은 트리에서 Blender 나 `build_campus.py` 가 도는 중이면 끝나기를 기다리거나, 스크래치 worktree(`git worktree add --detach $S/wt HEAD` 뒤 `.venv` · `assets_src` · `web/node_modules` 를 심볼릭 링크)에서 만든다. 두 빌드가 같은 GLB · `campus.json` 을 함께 쓰면 반쯤 쓴 파일을 서로 읽는다.
   - 에이전트 여럿이 Blender 를 돌리는 라운드에서는 `flock -w 900 <라운드 스크래치>/blender.lock blender …` 로 감싼다(`agent-round` 스킬).
   - 기준을 떠 둔다: `git show HEAD:web/public/data/campus.json > $S/campus_head.json`
2. **(심기에 닿는 것을 고쳤으면) 고치기 전 소스의 작업면 덤프를 받아 둔다.** 고치기 전이면 지금 트리에서, 이미 고쳤으면 HEAD 의 스크래치 worktree 에서:
   ```bash
   Y97_WORK_DUMP=$S/dump_before .venv/bin/python tools/build_campus.py > $S/build_before.log 2>&1
   ```
   worktree 에서 돌리면 출력도 그 worktree 안에 쓰이므로 공유 트리는 그대로다.
3. **`build_campus.py`.**
   ```bash
   Y97_WORK_DUMP=$S/dump_after .venv/bin/python tools/build_campus.py > $S/build.log 2>&1; tail -5 $S/build.log
   ```
   `data/campus.json` · `web/public/data/campus.json` · `terrain_*.bin` · `data/terrain_*.npy` · `ground_splat.png` 등 땅 지도 · `data/debug_map.png` 를 쓴다. 로그의 `traffic tilt` · `wheel tracks off the asphalt` 줄이 새로 늘지 않았는지 본다.
4. **심기가 흔들리지 않았는지 본다(Blender 를 돌리기 전에).**
   ```bash
   python3 .claude/skills/regen/diff_campus.py --old $S/campus_head.json --near <x>,<y>,<r>      # 해발 campus.json 끼리
   .venv/bin/python .claude/skills/regen/diff_campus.py --old $S/dump_before --new $S/dump_after --near <x>,<y>,<r>   # 작업면 덤프끼리(지형 npy 도)
   ```
   - `--near` 는 고친 곳의 가운데와 반지름(여러 번 줄 수 있음). 「먼 변화」가 0 이어야 한다.
   - 나무는 **같은 인덱스**가 같은 나무여야 한다. 웹이 목록 순서로 모델(`<수종>_0/_1`)을 골라(`web/src/world.js` Forest) 가운데 하나가 빠지면 그 뒤 나무가 모두 다른 모델이 되고 해 그림자가 캠퍼스 전체에서 바뀐다. 옮길 때는 제자리에서 값만 고치고, 새 나무는 목록 맨 끝에 더하고, 빼는 나무는 `DROP_TREES`(끝의 나무와 바꿔 넣음)로.
   - 관목 · 소품 · 차는 웹이 순서로 고르지 않아, 같은 것이 한 칸씩 밀리기만 한 것은 화면이 같다(오토바이 색만 순서를 탄다). 그래도 고친 곳에서 먼 자리 · 종류가 달라졌으면 난수가 흔들린 것이다.
   - 덤프는 `build_campus.py` 의 `Y97_WORK_DUMP` 줄에서 쓰인다. 그 줄 뒤에 더해지는 것(걷기 막이 `walkguard97.colliders()` 등)은 덤프에 없으니 마지막 `campus.json` 끼리도 견준다.
   - 흔들렸으면 Blender 로 넘어가지 말고 소스를 고친다. 길은 `CLAUDE.md` 의 규칙(`PAV_PRE` / `ASPH_PRE` 뒤, `GONE_1997`, 뽑는 횟수 지키기)과, 심기가 끝난 뒤 덧붙이는 「늦은 방식」(땅 칠 · `Hn` 을 `# Save` 직전에, 나무는 제자리에서)이다.
5. **Blender.** 고친 것에 맞는 부분만, 로그를 남기고, `Traceback` 을 찾는다(Blender 는 파이썬 에러에도 0 으로 끝난다).
   ```bash
   blender -b --factory-startup --python blender/build.py -- landmarks > $S/bl_landmarks.log 2>&1
   blender -b --factory-startup --python blender/build.py -- buildings > $S/bl_buildings.log 2>&1
   blender -b --factory-startup --python blender/build.py -- landmarks > $S/bl_landmarks2.log 2>&1
   grep -n "Traceback" -A 8 $S/bl_*.log
   ```
   - 일반 건물과 랜드마크는 서로의 그림자를 상대의 마지막 GLB 에서 읽어 굽는다. 한쪽만 조금 고쳤으면 그쪽 한 번, 그림자가 달라질 만큼이면 `landmarks` → `buildings` → `landmarks`.
   - `export_glb` 가 Draco 압축(`tools/draco_glb.mjs`)과 160 m 칸 나누기(`tools/split_glb.mjs`)를 부른다. `cd web && npm install` 이 되어 있어야 한다.
   - `noao` 를 더하면 굽기를 건너뛴다(모양만 빨리 볼 때. 커밋할 것은 `noao` 없이).
6. **해 그림자 · 걷는 면 높이를 굽는다.** vite 가 이 트리를 내보내고 있어야 한다.
   ```bash
   ss -ltnp | grep :<포트>                               # 띄우기 직전에 다시 본다(다른 세션이 그 사이 잡을 수 있음)
   (cd web && npx vite --port <포트> --strictPort) > $S/vite.log 2>&1      # 새로 띄울 때(백그라운드로). 다른 vite 가 떠 있으면 자기 cacheDir 를: update-snapshots 스킬
   curl -sI http://localhost:<포트>/assets/models/campus_landmarks.glb | grep -i content-length; ls -l web/public/assets/models/campus_landmarks.glb
   node tools/bake_sun_shadows.mjs <포트> > $S/bake.log 2>&1; tail -3 $S/bake.log
   ```
   - `Content-Length` 가 디스크의 파일과 다르면 그 vite 는 다른 트리나 옛 파일을 내보내는 것이다. rebase · checkout 뒤에는 vite 를 다시 띄운다(바뀐 파일을 index.html 로 돌려줘 `Unexpected token '<'` 로 굽기가 실패한다).
   - `web/public/assets/textures/sun_shadow.png` · `sun_ground.png` 를 쓴다.
   - 끌 때는 `ss -ltnp | grep :<포트>` 에서 pid 를 읽어 `kill <pid>`. `pkill -f` · `pgrep -f … | xargs kill` 은 자기 셸까지 죽인다.
7. **뒤 확인.**
   - 화면: `node tools/snapshots.mjs --port <포트> --spec <고친 곳의 카메라 json> --raw $S/shots --no-compose` 로 찍어 **열어 본다**. 폰 경로도 한 번: `--query '?touch'`. `failed shader programs` · `console errors` 가 찍히면 고친다.
   - 해 그림자: `git diff --stat -- web/public/assets/textures/sun_shadow.png` 만으로는 모른다. 고친 곳 밖의 덩어리가 있는지 그림 차이로 본다(`scipy.ndimage.label`). 1 ~ 40 px 짜리 먼 점들은 연석 줄이 1 ~ 2 cm 옮겨 생기는 것이라 괜찮고, 캠퍼스 전체가 바뀌었으면 나무 순서가 밀린 것이다(4번으로).
   - 걷기: 땅 · 계단 · 데크를 고쳤으면 `walk-probe` 스킬.
   - `tools/photofit/.cache/lm_verts.npz` 는 랜드마크 GLB 의 꼭짓점 사본인데 GLB 의 날짜를 보지 않는다. `-- landmarks` 를 돌렸으면 지운다(다음에 읽을 때 다시 만들어짐). 다른 에이전트가 사진 맞춤을 돌리는 중이면 지우지 말고 임시 파일에 새로 써서 `os.replace` 로 바꾼다.
   - 재질: `python3 -c "import json;a=json.load(open('blender/materials.json'));b=json.load(open('web/public/data/materials.json'));print(a==b, set(a)-set(b))"` 가 `True set()` 이어야 한다. 웹 사본에 없는 재질은 게임에서 자홍색이다. `blender/materials.json` 은 손으로 맞춘 형식이라 json.dump 로 다시 쓰지 않고 글로 덧붙인다.
   - 텍스처: 잎 · 낙엽 PNG 를 손으로 고쳤으면 `python tools/webp_textures.py`, PBR 텍스처 · 하늘을 고쳤으면 `python tools/mobile_textures.py`(둘 다 인자 없이 돌리면 없거나 낡은 것만 다시 만든다. `git status` 로 `tools/webp_sources.json` · `tools/mobile_sources.json` 이 함께 바뀌었는지 본다).
   - README · 고증의 화면이 달라졌으면 `update-snapshots` 스킬.
8. **커밋.** 생성 파일은 소스 커밋과 따로, 맨 끝에 한 번(`shared-commit` 스킬). 흔히 바뀌는 것:
   `data/campus.json`, `data/debug_map.png`, `data/entrances_generic.json`, `data/terrain_*.npy`, `web/public/data/campus.json` · `entrances.json` · `terrain_*.bin` · `road_meta.json`, `web/public/assets/models/*.glb`(과 `props/` · `veg/`), `web/public/assets/textures/ground_*.png` · `sun_shadow.png` · `sun_ground.png`. `web/public/assets/models/campus/`(칸 파일)는 git 밖이다. `git status --short` 로 실제 바뀐 것만 이름으로 더한다.

## 알려진 함정

- **자리 · 회전 값은 json 이 아니라 `build_campus.py` 에서 고친다.** `campus.json` 두 벌은 모두 그것이 쓴다.
- **전역 `rng` 하나.** 새 땅 · 길 하나가 캠퍼스 전체 나무를 옮길 수 있다. 무엇이 처음 갈렸는지 찾을 때는 고친 것을 하나씩 떼어 스크래치 worktree 에서 돌려 본다(빌드는 결정적이다).
- **길 · 건물을 옮길 때**는 옛 자리를 `*_RNG` 로 남겨 판단(심을지 · 뺄지)에만 쓰고 새 자리에 놓는 방식이 `build_campus.py` 에 여러 번 쓰였다(`BLINE_RNG` · `layers_rng` · `DROP_TREES` 를 grep). 동네(`gate_town.py` · `sinchon_rotary.py` · `blender/town.py`)는 제 난수 흐름이 따로 있지만 규칙은 같다.
- **작업면.** `build_campus.py` · `blender/` 안의 높이는 작업면(해발 + `datum.tilt`), `campus.json` · `data/terrain_*.npy` · GLB 는 해발이다. 소스에 적는 절대 높이는 해발로 적고 `datum.up*` 로 올린다. `campus.json` 에 절대 높이 필드를 새로 더했으면 `datum.heights()` 에 한 줄 더한다(빠뜨리면 그 숫자만 작업면 값으로 남는다).
- **건물 목록 가운데를 넣고 빼면** 그 뒤 일반 건물의 색 · 옥상 물건이 바뀐다(`blender/build.py` 의 `random.Random(1997)` 하나). 뺄 때는 `GONE_1997`(→ `rnd_ghosts`)로. 새로 지어 넣는 건물의 id(99xxxx)는 쓰기 전에 `grep -rn <그 id> tools/` 로 비어 있는지 본다(겹치면 한 건물이 소리 없이 덮인다).
- **다른 세션이 생성 파일을 먼저 push 했으면** 내 생성 파일을 버리고(`git checkout -- <생성 파일>`) 새 main 위에서 소스만 얹어 한 번 다시 만든다. 생성 파일은 병합하지 않는다.
- 스크래치 worktree 에서 `tools/snapshots.mjs` 를 돌리면 이웃 저장소(`../yonsei-anthology`)의 그림은 건너뛴다.
