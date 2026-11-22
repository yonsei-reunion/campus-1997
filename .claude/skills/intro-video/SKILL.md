---
name: intro-video
description: 게임 소개 영상(약 3분, 1920 × 1080)을 지금 게임으로 다시 찍는다. 장면은 tools/trailer/intro_segments.js, 녹화는 intro.mjs(프레임) · intro_audio.mjs(게임의 소리), 잇기 · 배경 음악은 intro_video.py. 신촌 로터리에서 정문 · 백양로를 지나 독수리상까지 날아가 한 바퀴 돌고 성구의 걷는 화면으로 내려오기, 대자보, 벚꽃 · 낙엽, 주인공 열세 명, 사진과 게임의 대비(동상 · 흉상 · 건물), 활천대 생일(「고마워!」까지) · 농구장, 쪽지, 미니 게임, 참고 자료 통계 · 출처 · 제보 · Thanks to. 「소개 영상 다시 찍어줘」, 「영상에 장면 더해줘」, 「치지직에 올릴 영상」, 게임을 크게 고친 뒤 영상을 맞출 때 쓴다.
---

# 소개 영상

게임을 소개하는 영상 `trailer/intro.mp4`(git 밖: `.gitignore` 의 `trailer/*.mp4`)를 다시 만든다.

- 장면의 내용(카메라 · 자막 · 게임 조작): `tools/trailer/intro_segments.js`
- 자막 층과 도우미: `tools/trailer/intro_page.js`
- 프레임 녹화: `tools/trailer/intro.mjs` (Playwright Chromium, 30 fps 고정)
- 게임의 소리 녹음: `tools/trailer/intro_audio.mjs` (응원가 · 바람과 새소리 · 분수)
- 잇기 · 배경 음악 · MP4: `tools/trailer/intro_video.py` (순서와 자르는 곳은 맨 위 `CLIPS`)

## 순서

1. **생성 파일이 최신인지 본다**(GLB · 해 그림자: `/regen`). 영상은 그 순간의 게임 그대로다.
2. **빌드한 사본을 띄운다.** 개발 서버(vite)는 다른 세션이 `web/` 을 고치면 페이지를 다시 불러 찍던 장면이 끊긴다.
   ```bash
   W=<작업 폴더>            # 저장소 밖(스크래치)
   ss -ltnp | grep :5231   # 다른 세션이 쓰는 포트인지
   cd web && npx vite build --outDir $W/dist --emptyOutDir && npx vite preview --outDir $W/dist --port 5231 --strictPort   # 백그라운드로
   ```
3. **구도를 본다**(장면을 고쳤을 때). `--every N` 은 N 프레임마다 한 장만 저장한다.
   ```bash
   node tools/trailer/intro.mjs $W/prev --seg heroes,compare --every 20
   montage $W/prev/heroes/*.jpg -tile 6x -geometry 640x360+2+2 $W/prev/heroes_sheet.jpg    # 그리고 그 그림을 본다
   ```
   한 항목만: `--arg '{"only":["p10"]}'`(heroes: 주인공 id, compare · games: 그 장면의 key, info: 쪽 번호).
4. **찍는다**(전체 약 6,200 프레임, 15 ~ 20분). 백그라운드로 돌리고 로그를 본다.
   ```bash
   node tools/trailer/intro.mjs $W/take > $W/take/log.txt 2>&1
   ```
   - 페이지가 죽으면(GPU 프로세스가 가끔 죽는다) 브라우저를 다시 띄워 그 장면을 처음부터 찍는다(네 번까지). 끝에 `FAILED:` 가 있으면 그 장면만 `--seg` 로 다시.
   - 찍는 동안 `intro_page.js` · `intro_segments.js` 를 고치지 않는다(장면마다 페이지에 다시 넣는다).
   - 게임 페이지 하나가 메모리 3 GB쯤을 쓴다. 다른 헤드리스 페이지(소리 녹음, 스냅샷)와 함께 돌리지 않는다.
5. **소리를 녹음한다**(프레임 녹화가 끝난 뒤, 약 3분).
   ```bash
   node tools/trailer/intro_audio.mjs $W/take
   ```
6. **잇는다.**
   ```bash
   .venv/bin/python tools/trailer/intro_video.py $W/take trailer/intro.mp4
   ```
   길이와 장면마다의 구간을 찍어 준다. 3분 안팎인지 본다.
7. **본다.** 반드시 프레임을 뽑아 확인한다.
   ```bash
   ffmpeg -y -loglevel error -i trailer/intro.mp4 -vf "fps=1/4,scale=480:-1,tile=8x6" $W/sheet.jpg   # 4초마다 한 장
   ffmpeg -y -loglevel error -ss 75 -i trailer/intro.mp4 -frames:v 1 $W/f75.jpg                        # 그 초의 온 화면
   ```
   - 자막이 화면 밖으로 나가거나 게임의 안내 버튼 · 창과 겹치지 않는지, 앞 장면의 글자가 남지 않는지
   - 주인공이 건물을 등지고 서 있는지(생울타리 · 벽 속에 서지 않는지), 사진과 게임의 대비에서 같은 대상이 보이는지
   - 미니 게임마다 카운트다운이 아니라 플레이 화면이 나오는지, 쪽지가 벽 · 기둥에 붙는지
   - 소리: `ffmpeg -i trailer/intro.mp4 -af volumedetect -f null -` 로 크기(평균 −20 dB 안팎), 구간마다의 크기는 `intro_video.py` 가 쓴 `$W/take/intro.wav` 로
8. **커밋한다.** 영상은 git 밖이다. 고친 `tools/trailer/intro*` 와 이 스킬, README(통계를 고쳤으면)만 커밋한다(`/shared-commit`).
9. **올릴 글을 준비한다.** 제목 · 설명 · 구간 시각(6 의 출력에서)을 `trailer/intro_upload.txt`(git 밖)에 적고, 썸네일을 찍는다(언더우드관과 정원: `node tools/trailer/intro.mjs $W/take --seg thumb && cp $W/take/thumb/00000.jpg trailer/intro_thumb.jpg`. `extra: true` 인 장면이라 전체 녹화에는 들지 않는다). 치지직 스튜디오(`studio.chzzk.naver.com`)는 Chrome 확장이 막아 두었고 파일 올리기도 10 MB 까지라, 올리는 일은 사용자가 한다.

## 장면을 고칠 때

- 장면 하나 = `seg.<이름> = { n, season?, files?, init(arg), step(i, t) }`. `step` 이 카메라 · 자막을 놓고 `step()`(게임 한 프레임)을 부른다. 끝나는 때가 정해지지 않은 장면은 `{ done: true }` 를 돌려준다. `{ mark: '이름' }` 은 `meta.json` 에 남아 `intro_video.py` 의 `CLIPS` 가 그 때로 자른다(활천대 생일 장면).
- 한 장면 안에서 날아가기 → 걷기로 바꿀 때(`fly`): `step` 안에서 `await toWalk(...)` 하고(그동안 프레임은 저장되지 않음), `walkCam` 으로 앞의 카메라를 이어 받아 게임의 카메라 자리(`player.js` `behindCamera`, 시야각 66)까지 옮긴 뒤 `pl.camOverride = null` 로 놓아준다.
- 미니 게임은 게임 화면을 그대로 두되, 다른 장면과 겹치는 곳(생일 축하의 활천대 앞)은 피한다: 생일 축하는 친구 넷을 다 데려온 상태(`y.bday.friends` · `trail`)를 만들어 백양로 보도를 뛰게 한다.
- 순서 · 길이를 바꾸면 `intro_video.py` 의 `CLIPS` 와 소리의 구간(`span('games')` 등)을 함께 본다.
- 화면은 CSS 1280 × 720 에 기기 화소 비 1.5 로 찍는다(1920 × 1080). 게임의 창 · 안내 버튼 · 말풍선이 영상에서 읽히게 하려는 것이다. 자막은 1920 × 1080 의 화소로 적는다(`#iv` 가 줄여 놓음).
- 자막 뒤의 어두운 그라데이션(`.scrim`)은 왼쪽 아래 모서리에만 둔다. 화면 아래 전체를 덮으면 서 있는 사람이 흐려 보인다.
- 게임의 화면 요소는 `hud('none' | 'bubbles' | 'play' | 'cards' | 'game')` 로 고른다. 게임 화면을 보여 주는 장면(농구 · 쪽지 · 미니 게임)에서는 실제 화면 요소를 남긴다.
- 미니 게임은 제목 화면의 그 버튼을 눌러 시작하고, 코스 창 · 카운트다운은 프레임을 저장하지 않고 넘긴다(`untilDo`). 조작은 `key('KeyW', true)` 로 키를 누른다.
- 쪽지는 실제 서버(DoltHub · Worker)에 닿지 않게 `intro.mjs` 가 가로챈다. 화면의 쪽지는 `MEMO_LIST` 의 지어낸 글이다. 실제 쪽지를 영상에 넣지 않는다.
- 사진과 게임의 대비(`CMP`): 왼쪽 사진, 오른쪽에 같은 비율의 창으로 게임(`camera.setViewOffset`). 카메라는 `tools/snapshots.json` 의 `compare/*` 를 옮겨 적는다(거기서 고치면 여기도). 사진은 저장소에 넣어도 되는 것만(CLAUDE.md 「고증 자료」): 국토지리정보원 항공사진 · 수치지형도, 로드뷰 · 거리뷰 화면은 영상에도 넣지 않는다.
- 참고 자료의 통계(`STATS`)는 README 「고증」의 숫자와 같게 둔다. 다시 셀 때:
  ```bash
  git -c core.quotepath=false ls-tree -r -l HEAD -- reference | grep -iE "\.(jpg|jpeg|png|gif|webp)$" | wc -l      # 저장소의 사진 수
  find reference -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.gif' -o -iname '*.webp' \) -print0 | du -ch --files0-from=- | tail -1
  ls assets_src/aerial_1997 assets_src/aerial_other | grep -E '\.(tif|jpg)$' | sed 's/\.[a-z]*$//' | sort -u | wc -l   # 항공사진 장수
  du -ch assets_src/aerial_*/*.tif assets_src/aerial_*/*.jpg | tail -1; ls assets_src/survey_5000/*.dxf | wc -l; du -ch assets_src/survey_5000/*.dxf | tail -1
  ```
  모두 = 저장소의 사진 + 항공사진 + 수치지형도의 판 수.
- 출처 · 제보 · Thanks to 의 글은 게임의 「자료 출처 · 고마운 분들」 창(`web/index.html` `#credits`)과 같게 둔다.
- 배경 음악은 `intro_video.py` 가 합성하는 이 영상만의 가락이다. 미니 게임 구간에는 게임의 응원 연습 소리(아카라카 구호와 응원가)가 나오고 배경 음악은 쉰다.
