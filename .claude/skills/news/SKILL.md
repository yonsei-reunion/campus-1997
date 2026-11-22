---
name: news
description: 게임의 「새 소식」(web/public/data/releases.json)에 바뀐 내용을 적는다. CLAUDE.md 「새 소식」의 형식 · 카테고리 순서 · 문장 규칙을 점검표로 삼고, 그날의 요약을 100자 안으로 다시 보고, 전 · 후 캡처를 tools/snapshots.mjs --spec 과 전 · 후 worktree 로 찍어 web/public/assets/news/ 에 넣는다. 「새 소식에 적어줘」, 「releases.json 갱신」, 「전후 사진 넣어줘」, 게임에 보이는 변경을 끝내고 push 하기 전에 쓴다.
---

# 새 소식 쓰기

게임 안 「새 소식」 창과 `news.html`(날짜마다 `news.html?d=<날짜>`)이 `web/public/data/releases.json` 을 `web/src/notes.js` 로 그린다. 규칙의 원문은 `CLAUDE.md` 「새 소식」이다.

- 도구: `.claude/skills/news/check_news.py`(규칙 점검), `.claude/skills/news/pair.py`(전 · 후 그림 붙이기)
- `$S`: 스크래치 폴더

## 순서

1. **무엇을 적을지 모은다.** 이번에 바뀐 것 가운데 **게임에서 보이거나 겪는 것**과 자료(reference · 고증 문서)만. 커밋 목록이 아니라 「무엇이 어떻게 달라졌나」로. 구현 방법 · 이슈 번호 · 측정 방법의 긴 설명은 넣지 않는다(고증은 `reference/고증/`, 구현은 커밋 메시지).
2. **지금 파일을 본다.**
   ```bash
   python3 .claude/skills/news/check_news.py        # 맨 위 날짜의 요약 글자 수, 다음 그림 번호, HEAD 와 달라진 날짜
   git diff --stat -- web/public/data/releases.json # 다른 세션이 고치는 중인지
   ```
   - 오늘 날짜의 항목이 이미 있으면(다른 세션 · 앞선 작업) 새로 만들지 않고 그 `groups` 에 더한다. 없으면 배열 **맨 위**에 새 날짜를 넣는다.
   - 다른 세션이 이 파일을 고쳐 둔 채면(커밋 안 된 변경) 그 줄은 건드리지 않고 내 줄만 더한다. 커밋은 `shared-commit` 스킬의 「섞인 파일」 길로.
3. **카테고리에 나눠 적는다.** 이름과 순서는 아래 그대로, 그날 없는 것은 뺀다.

   | # | 카테고리 | 들어가는 것 |
   |---|---|---|
   | 1 | 사람 | 캐릭터, 옷차림, 인사 · 대화 |
   | 2 | 건물 | 외관, 현관 · 계단, 새로 넣거나 뺀 건물, 이름 |
   | 3 | 땅 · 정원 | 지형, 앞마당, 정원, 화단 |
   | 4 | 백양로 | 길의 자리 · 높이, 현수막, 길가 나무 · 잔디, 차, 초소 |
   | 5 | 시설 | 농구장, 분수, 정구장, 공중전화 |
   | 6 | 추억 카드 | |
   | 7 | 화면 · 조작 | 계절, 시점, 이름표, 모바일 조작, 창 |
   | 8 | 걷기 · 충돌 | |
   | 9 | 성능 | |
   | 10 | 자료 | reference 폴더, 고증 문서 |

   - 어디에 둘지 애매하면 지난 날짜에서 같은 종류를 어디에 두었는지 본다(예: 캠퍼스 찻길의 노면 칠 · 길가 나무는 「백양로」, 신호 기둥은 「시설」).
4. **문장을 다듬는다.**
   - 한 항목에 한 가지, 명사형으로 끝낸다(「~을 없앰」, 「~로」). 「~했습니다」 · 마침표 없음.
   - 쉼표로 셋 넘게 이어지거나 대상 · 부분이 여럿이면 하위 목록으로: 건물 · 장소마다 한 항목(`{ "text": "장소", "items": [...] }`), 그 아래 「부분: 내용」(벽 · 현관 · 지붕 · 자리 …). 두 단계가 기본, 꼭 필요할 때만 세 단계.
   - 바뀐 값은 「전 → 후」(「다섯 단 → 열여섯 단」, 「20.6 m → 12 m」). 높이는 해발.
   - 자료는 항목 끝 괄호에 짧게: 「(1996년 단체사진)」, 「(2009년 거리뷰)」. 장소 항목에 한 번 적으면 그 아래 줄마다 되풀이하지 않는다.
   - 「사진대로」 · 「자료:」 같은 같은 말을 항목마다 되풀이하지 않는다.
   - 같은 날 앞서 적은 항목을 이번 일이 뒤집었으면 덧붙이지 않고 그 항목을 고쳐 쓴다(틀린 그림은 뺀다).
5. **파일에 넣는다. 글로 고친다.** `Edit` 로 그 자리에 줄을 넣는다. 파일 전체를 `json.dump` 로 다시 쓰지 않는다(옛 날짜의 손으로 맞춘 줄바꿈이 모두 바뀐다).
   ```json
   {
     "date": "2026-11-22",
     "summary": ["큰 변화 하나", "큰 변화 둘"],
     "groups": [
       {
         "category": "건물",
         "items": [
           "짧은 항목",
           {
             "text": "묶는 항목 (자료)",
             "items": [
               "부분: 전 → 후",
               "부분: 내용"
             ]
           }
         ],
         "images": [
           { "src": "assets/news/527_name.jpg", "alt": "무엇을 어디서 본 것, 전 · 후" }
         ]
       }
     ]
   }
   ```
   - 들여쓰기 2칸, `"summary"` 배열과 `images` 의 `{ "src": …, "alt": … }` 는 한 줄.
   - `title` 은 쓰지 않는다(날짜만 보이고 내용은 카테고리가 나눈다).
   - 스크립트로 넣어야 할 만큼 많으면 맨 위 항목 하나만 읽어 고쳐 쓰고(`json.JSONDecoder().raw_decode`) 나머지 글자는 그대로 이어 붙인다.
6. **요약을 다시 본다.** `summary` 는 그날의 큰 변화만 짧은 항목 두세 개(많아야 다섯), 모두 합쳐 100자 안쪽. 한 줄로 길게 잇지 않는다. 같은 날짜에 항목을 더했으면 요약도 다시 고른다. 다른 세션이 그날 쓴 요약 글자도 100자에 든다.
7. **전 · 후 캡처.** 눈에 보이는 변화마다 한 장(변화가 작거나 화면으로 안 보이면 넣지 않는다).
   1. 카메라를 임시 spec 으로 적는다(저장소 밖, `out` 없이). 형식은 `tools/snapshots.json` 과 같다.
      ```json
      { "shots": [ { "name": "jk_east", "cam": { "x": -146.2, "y": -58.5, "h": 37.65, "tx": -149.0, "ty": -35.0, "th": 37.6, "fov": 58 }, "size": [1100, 1000] } ] }
      ```
      전 · 후를 같은 spec 으로 찍는다. 땅 높이가 바뀌는 곳은 카메라에 절대 높이(`h` · `th`, 해발)를 쓴다: `dh` · `tdh`(그 자리 땅 위)는 땅과 함께 움직여 전 · 후 화면이 어긋난다. `tools/snapshots.json` 에 그 대상의 카메라가 이미 있으면 그것을 옮겨 쓴다.
   2. 「전」의 게임을 따로 띄운다. 고치기 전 커밋의 worktree 와 그것을 내보내는 vite:
      ```bash
      git worktree add --detach $S/wt_before <고치기 전 해시(아직 커밋 전이면 HEAD)>
      ln -s "$PWD/web/node_modules" $S/wt_before/web/node_modules
      ss -ltnp | grep :<전 포트>                      # 비어 있어야 한다
      ```
      vite 둘이 같은 `web/node_modules/.vite` 를 쓰면 three.js 가 두 번 실려 페이지가 끝까지 뜨지 않는다. 「전」 쪽에 자기 `cacheDir` 를 준다. `$S/vite_before.mjs`:
      ```js
      import base from '<$S 의 절대 경로>/wt_before/web/vite.config.js';
      export default (e) => { const c = typeof base === 'function' ? base(e) : base; return { ...c, cacheDir: '<$S 의 절대 경로>/vitecache_before', server: { ...(c.server || {}), fs: { allow: ['/home', '/tmp'] } } }; };
      ```
      ```bash
      (cd $S/wt_before/web && npx vite --config $S/vite_before.mjs --port <전 포트> --strictPort) > $S/vite_before.log 2>&1 &
      ```
      「후」는 지금 트리의 vite(생성 파일을 다시 만든 뒤: `regen` 스킬). 고치기 전에 미리 찍어 둘 수 있으면 worktree 없이 지금 vite 로 「전」을 먼저 찍어도 된다.
   3. 찍는다.
      ```bash
      node tools/snapshots.mjs --port <전 포트> --spec $S/news_spec.json --raw $S/before --no-compose
      node tools/snapshots.mjs --port <후 포트> --spec $S/news_spec.json --raw $S/after --no-compose
      ```
      PNG 는 `<raw>/<이름>.png`(이름의 `/` 는 `__` 로). `failed shader programs` · `console errors` 가 찍히면 그것부터 고친다.
   4. 붙이고 **열어 본다.**
      ```bash
      python3 .claude/skills/news/pair.py $S/before/jk_east.png $S/after/jk_east.png web/public/assets/news/527_jk_east.jpg
      ```
      - 두 장이 같은 자리 · 방향인지, 달라진 것이 한눈에 보이는지, 나무 · 차 · 사람이 가리지 않는지. 달라진 것이 작으면 카메라를 당겨 다시 찍거나 `--crop` 으로 자른다.
      - 세로로 긴 화면은 끝에 `v`(위아래로), 사진과 게임을 견주는 그림은 `--labels 사진,게임`.
   5. 파일 이름은 `<번호>_<영문 이름>.jpg`. 번호는 폴더에서 가장 큰 번호 + 1(`check_news.py` 가 알려 준다. 다른 세션의 아직 커밋 안 된 그림도 세므로 `ls` 로 센 값이다). 폭 1200 px 안팎, 100 ~ 250 KB.
   6. 그림은 **그 내용을 다룬 카테고리**의 `images` 에 넣는다. `alt` 는 캡션(「장기원 기념관 동쪽 발치를 위에서, 전 · 후」).
   7. 끝나면 「전」 vite 를 끄고(`ss -ltnp | grep :<전 포트>` 에서 pid 를 읽어 `kill <pid>`. `pkill -f` 는 쓰지 않는다) `git worktree remove $S/wt_before`.
8. **점검한다.**
   ```bash
   python3 .claude/skills/news/check_news.py
   git diff -- web/public/data/releases.json | head -80
   ```
   - 「틀림」이 없어야 한다. 「볼 것」은 읽고 판단한다(다른 세션이 고친 날짜, 쉼표 많은 항목 …).
   - diff 가 오늘 날짜의 줄에만 있어야 한다. 옛 날짜가 통째로 바뀌어 보이면 파일을 다시 쓴 것이다: 되돌리고 글로 넣는다.
   - 떠 있는 게임의 「새 소식」 창이나 `http://localhost:<포트>/news.html?d=<날짜>` 로 한 번 본다(목록이 겹겹이 제대로 접히는지, 그림이 뜨는지).
9. **커밋.** `releases.json` 과 새 그림을 함께(`shared-commit` 스킬). 에이전트로 일하는 중이면 커밋하지 않고 항목 초안과 캡처 경로를 보고에 적는다(통합자가 한 번에 넣는다).

## 그림에 쓸 수 있는 것

- 게임 화면은 언제나 된다. 옛 화면(「전」)은 여기 `web/public/assets/news/` 에만 남긴다. `docs/` 에 사본을 두지 않는다.
- 참고 사진을 나란히 놓을 때는 저장소에 넣어도 되는 사진만(`CLAUDE.md` 「고증 자료」: 라이선스가 분명한 것, 학교 홈페이지 · 연세춘추 · 문집 사진). 로드뷰 · 거리뷰 화면, 항공사진 원본 스캔의 조각은 새 소식에도 넣지 않는다.
- 얼굴을 알아볼 수 있는 사람이 크게 찍힌 사진은 빼거나 잘라 낸다.

## 알려진 함정

- **요약 100자**는 `sum(len(항목))` 으로 센다(`check_news.py`). 이미 100자인 날에 더할 때는 항목을 바꿔 써야 한다.
- **가까운 면을 잘라 찍는 카메라**(spec 의 `eval` 로 `camera.near` 를 바꾸는 것)는 여러 장을 이어 찍으면 늦게 걸려 틀린 그림이 나온다. 그 한 장만 `--only <이름>` 으로 다시 찍는다.
- **`eval` 로 바꾼 상태**(재질 숨기기 등)는 다음 장에도 남는다. `setTimeout` 으로 되돌리거나 그 장을 맨 끝에 둔다.
- rebase · checkout 한 트리를 내보내던 vite 는 다시 띄운다.
- 지운 그림(`git rm`)을 일찍 stage 해 두면 다른 커밋에 딸려 간다. 새 소식 커밋 직전에 한다.
