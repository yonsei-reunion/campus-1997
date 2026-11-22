---
name: agent-round
description: 여러 이슈 · 구역을 worktree 에이전트들에게 나눠 맡기는 병렬 라운드를 통합자로서 운영한다. 공통 brief.md, 에이전트마다 자기 스크래치 · vite 포트 · cacheDir, Blender 잠금, 통합 브랜치(integ-*)에 받는 대로 얹기, 생성 파일과 releases.json 은 통합 뒤 한 번, push 는 맨 끝에 한 번, worktree 정리는 자기 id 만. 「에이전트로 나눠서 진행해줘」, 「병렬로 처리」, 「이슈들 한꺼번에」, 「라운드 돌려줘」 같은 말에 쓴다.
---

# 병렬 에이전트 라운드

규칙은 `CLAUDE.md` 「여러 세션」에 있다. 에이전트 여럿은 토큰을 한꺼번에 많이 쓰니 사용자가 병렬로 하자고 했을 때만 연다. 통합자(이 세션)는 직접 재거나 고치기보다 나누고, 받고, 합치고, 확인한다.

- `$S`: 이 세션의 스크래치 폴더(절대 경로로 brief 에 적는다)
- 에이전트의 worktree 는 `.claude/worktrees/agent-<id>`, 브랜치는 `worktree-agent-<id>`. **다른 세션의 에이전트도 같은 폴더를 쓴다**
- worktree 들은 refs 를 함께 쓰므로 통합 브랜치 `integ-<라운드 이름>` 이 모든 에이전트에게 보인다

## 1. 준비

1. **범위를 정한다.**
   ```bash
   gh issue list --state open --limit 80 --json number,title,labels --jq '.[] | "\(.number)\t\([.labels[].name]|join(","))\t\(.title)"'
   git -c core.quotepath=false status --short          # 다른 세션이 고치는 중인 파일
   git worktree list                                   # 다른 세션의 에이전트 · 통합 worktree
   ```
   - `blocked` 가 아닌 이슈, 남은 줄을 가진 자료로 끝낼 수 있는 이슈를 고른다. 한 에이전트에 한 이슈나 한 구역(같은 파일 · 같은 함수를 둘이 고치지 않게).
   - 같은 트리의 다른 세션이 맡은 파일 · 이슈는 brief 에서 뺀다. 물을 수 있으면 먼저 묻는다.
   - 나누기 전에 몇 분, **새 자료**를 직접 찾아본다(새 사진 묶음 하나가 「지상 사진 필요」 줄 여럿을 자료 작업으로 바꾼다).
   - 여러 에이전트가 같은 목록 · 같은 파일에 덧붙일 일이면 통합자가 먼저 작은 정리를 해 둔다(각자 **목록 끝에 한 덩이**만 더하면 되게). 온 세상을 옮기는 변환(높이 기준 등)은 맨 마지막에, 다른 에이전트가 다 들어온 뒤에 한다.
2. **스크래치를 차린다.**
   ```
   $S/brief.md                     공통 지시
   $S/agents.txt                   이름 · 이슈 · 포트 · 에이전트 id, 받은 기록(LANDED …), 사용자의 중간 지시
   $S/agents/<이름>/               에이전트마다 자기 폴더(progress.txt, vite.mjs, 스크립트, 캡처, 댓글 초안)
   $S/agents/<이름>/report_by_integrator.md    돌아온 보고를 통합자가 그 자리에서 받아 적은 것
   $S/blender.lock                 Blender 잠금 파일
   $S/integ/                       통합 worktree
   ```
   에이전트끼리 한 폴더를 쓰게 하면 서로의 스크립트를 덮어쓴다.
3. **통합 worktree 와 브랜치.**
   ```bash
   git fetch -q origin
   git worktree add -b integ-<이름> $S/integ origin/main
   ln -s "$PWD/web/node_modules" $S/integ/web/node_modules; ln -s "$PWD/.venv" $S/integ/.venv; ln -s "$PWD/assets_src" $S/integ/assets_src
   ```
4. **`$S/brief.md` 를 쓴다.** 지난 라운드의 brief 가 스크래치에 남아 있으면 그것에서 시작한다. 들어갈 절:
   - **시작**: 첫 단계 `git -C <worktree> fetch -q && git -C <worktree> reset --hard integ-<이름>`. 공유 트리에서는 아무것도 고치거나 커밋하지 않는다. `cd` 대신 절대 경로 · `git -C`. worktree 에 `web/node_modules` · `.venv` · `assets_src` 심볼릭 링크. 자기 스크래치 `$S/agents/<이름>/` 와 `progress.txt`(잰 값 · 결정 · 남은 일을 계속 고쳐 씀: 다른 모델이 이어받을 수 있게).
   - **먼저 읽을 것**: `CLAUDE.md` 전부, `TECH_NOTE.md` 「에셋 파이프라인」, `reference/고증.md` 와 맡은 곳의 고증 파일, 맡은 이슈의 본문 · 댓글 전부, 일에 맞는 스킬(`regen` · `walk-probe` · `aerial-measure` · `news`).
   - **목표**: 줄마다 끝은 (가) 게임에 옮김 / 결론 → 고증 파일에 근거 · 잔차, 「남은 한계」 줄을 빼거나 줄임, (다) 일부 좁혀짐 → 고증에 적고 줄을 고침, (나) 새 자료가 꼭 있어야 함 → 그 줄의 「찾아본 곳」에 이번에 본 곳. 「찾았지만 게임에 안 옮김」으로 남기지 않는다.
   - **도구**: vite 는 자기 포트 · 자기 `cacheDir`(아래), 끌 때는 `ss -ltnp | grep :<포트>` 의 pid 로, rebase 뒤에는 다시 띄움. Blender 는 `flock -w 900 $S/blender.lock blender …`, 로그에서 `Traceback` 을 grep. 브라우저를 쓰면 자기 탭만.
   - **지킬 것**: 자리 값은 `build_campus.py` 에서, 심기가 흔들리지 않게(늦은 방식 먼저, 다시 만든 뒤 `.claude/skills/regen/diff_campus.py` 로 목록을 인덱스로 비교), 높이는 해발 · `datum.up*`, **생성 파일(GLB, `campus.json` 두 벌, 땅 지도 · 해 그림자 PNG, 잎 아틀라스)과 `releases.json` 은 커밋하지 않음**(자기 worktree 에서 만들어 확인은 함), 커밋은 자기 소스 · 문서만 이름으로(`-A` 금지) · 덩어리마다 · 메시지 규칙(`.claude/skills/shared-commit/check_msg.py`), 끝나기 전 `git rebase integ-<이름>`, **push · 이슈 만들기 · 댓글 · 라벨은 하지 않음**.
   - **확인**: 전 · 후 화면(`tools/snapshots.mjs --spec`), 고친 곳 걷기, `?touch` 에서 셰이더 에러 없음.
   - **보고 형식**: 브랜치 + 커밋 해시, 줄마다 (가)/(다)/(나) 한 줄, 바꾼 파일, 다시 만드는 명령과 심기 비교 결과, 새 소식 항목 초안과 전 · 후 PNG · 카메라 spec 경로, 이슈 댓글 초안(`$S/agents/<이름>/comment_<이슈>.md`, 커밋은 `<<sha:커밋 제목 앞부분>>` 자리표시), 다른 에이전트와 겹칠 위험.
   - **이번 라운드의 표**: `| 이름 | 이슈 | 포트 | 곳 |` 과 겹침 주의.
   - vite 설정(에이전트가 `$S/agents/<이름>/vite.mjs` 로 만든다. `web/node_modules` 를 함께 쓰는 vite 들이 같은 `.vite` 캐시를 고쳐 쓰면 three.js 가 두 번 실린다):
     ```js
     import base from '<worktree>/web/vite.config.js';
     export default (e) => { const c = typeof base === 'function' ? base(e) : base; return { ...c, cacheDir: '<$S>/agents/<이름>/vitecache', server: { ...(c.server || {}), fs: { allow: ['/home', '/tmp'] } } }; };
     ```
     `cd <worktree>/web && npx vite --config <그 파일> --port <포트> --strictPort` (서브셸 · 백그라운드. 띄우기 전 `ss -ltnp | grep :<포트>`).
5. **띄운다.** `Agent` 도구에 `isolation: "worktree"`, 에이전트마다 짧은 지시(「`$S/brief.md` 를 읽고 표의 <이름> 줄을 맡아라」 + 그 일에만 있는 것). 돌려받은 에이전트 id 를 곧바로 `$S/agents.txt` 에 적는다(정리와 이어 시키기에 쓴다).

## 2. 도는 동안

- **보고가 오면 그 자리에서** `$S/agents/<이름>/report_by_integrator.md` 로 받아 적는다(에이전트는 보고용 `.md` 를 못 쓸 수 있고, 통합자의 맥락은 마지막 에이전트가 오기 전에 요약된다).
- **통합 브랜치에 얹는다.** 에이전트가 `integ-<이름>` 위로 rebase 해 왔으면 fast-forward:
  ```bash
  git -C $S/integ merge --ff-only worktree-agent-<id>      # 안 되면 git -C $S/integ cherry-pick <해시>…
  git -C $S/integ grep -nIE '^(<{7}|>{7}|\|{7})( |$)'       # 충돌 표시가 커밋되지 않았는지(아무것도 안 나와야 함)
  python3 .claude/skills/shared-commit/check_msg.py -C $S/integ origin/main..HEAD
  ```
  - 충돌은 거의 언제나 같은 표의 줄(「남은 한계」 표, `reference/고증.md` 목록, `reference/출처.txt`)이다: 양쪽 줄을 다 살린다. 푼 파일은 **이름으로** `git add` 하고, 표시가 0 개인지 따로 확인한 뒤 `cherry-pick --continue`. 풀이 스크립트가 실패했는데 `&&` 뒤가 이어져 표시가 커밋된 적이 있다.
  - 두 에이전트가 키를 더한 json(`tools/cars97_new.json`)은 `git show :1:<파일>` · `:2:` · `:3:` 을 읽어 키로 합친다.
  - 얹은 뒤 본다: 같은 이름의 `def` / `function` 이 둘 생기지 않았는지, 새 건물 id(99xxxx)가 겹치지 않는지, 한 에이전트가 만든 새 생성 에셋(새 GLB · 텍스처)이 다른 worktree 에 없어 로딩이 깨지지 않는지(`$S/shared/` 에 두고 모두에게 알림).
- **얹을 때마다 알린다.** 같은 파일을 만지는 도는 에이전트에게 `SendMessage`: 「마지막 커밋 전에 `git rebase integ-<이름>`, 충돌은 스스로」. 그러면 뒤의 것들이 대부분 fast-forward 다.
- **보고를 읽고 다시 시킨다.** 첫 보고에는 거의 언제나 「찾았지만 안 옮김」이 있다. (나)로 적힌 줄이 정말 자료 문제인지도 본다. 그 에이전트를 `SendMessage` 로 이어 시킨다(새로 띄우지 않는다). 에이전트마다 두 번 도는 것으로 잡는다.
- **중간에 바뀐 규칙 · 사용자의 말 · 다른 에이전트가 찾은 사실**(기준이 되는 사진의 찍은 때, 경계에서의 높이)은 `brief.md` 를 고치고 도는 에이전트 모두에게 바로 전한다. 받은 것은 `$S/agents.txt` 에 한 줄씩 남긴다.
- **다른 세션이 main 에 push 했으면** 스크래치 worktree 에서 시험 rebase 로 충돌을 먼저 본다. 글의 충돌이 없어도 **뜻의 충돌**을 본다: 그 세션의 diff 에서 내 에이전트가 옮긴 상수 · 자리를 grep 한다. 통합 브랜치를 실제로 다시 쓰는 것은 에이전트 대부분이 들어온 뒤에, 옛 끝을 `integ-<이름>-pre-<해시>` 로 남기고, 남은 에이전트에게 「`git rebase --onto integ-<이름> integ-<이름>-pre-<해시>`」.
- **사용량 한도로 에이전트가 모두 죽으면** 일은 worktree 와 `progress.txt` 에 남아 있다. `SendMessage` 로 그 id 를 이어 시키거나, 새 에이전트에게 그 worktree 로 가서 `progress.txt` 부터 읽으라고 넘긴다(그래서 덩어리마다 커밋하고 `progress.txt` 를 쓰게 한다).
- 지난 라운드 에이전트의 늦은 알림이 오면 그 브랜치가 main 에 들었는지 제목으로 확인하고 넘어간다.

## 3. 통합과 끝

1. **모두 들어온 뒤 한 번 다시 만든다.** `$S/integ` 에서 `regen` 스킬 그대로(Blender 는 `flock` 으로. 에이전트가 아직 도는 동안 시험 삼아 돌려도 되지만, 남은 것을 얹는 것은 그 빌드가 끝난 뒤에: Blender 가 부분마다 `blender/*.py` 를 읽는다). `origin/main` 의 `campus.json` 과 `diff_campus.py` 로 견준다.
2. **합쳐서 확인한다.** 따로는 되던 것이 함께는 깨질 수 있다.
   - 빌드 로그의 `Traceback`, 게임의 `failed shader programs` · 콘솔 에러(`?touch` 도)
   - 고친 곳 걷기(`walk-probe` 스킬), 많이 더했으면 폰 경로의 삼각형 수
   - 에이전트가 자기 브랜치의 배치에 맞춘 카메라가 다른 에이전트의 변경 뒤에도 대상을 보는지
3. **화면.** `docs/` 는 대상이 실제로 바뀐 카메라만 다시 찍는다(`update-snapshots` 스킬: 전부 찍어 화소 차이로 줄 세우고, 열어 보고, 대상이 안 바뀐 것은 `git checkout` 으로 되돌림). 가까운 면을 자르는 카메라는 `--only` 로 한 장씩.
4. **새 소식.** 에이전트들의 초안을 한 날짜 항목으로(`news` 스킬). 전 · 후는 에이전트들의 spec 을 하나로 합쳐 `origin/main` worktree 의 vite(전)와 `$S/integ` 의 vite(후)에서 두 번에 찍는다. 그날 요약 100자에는 다른 세션이 쓴 것도 든다.
5. **이슈 준비.** 진척 없는 이슈를 바꿀 새 이슈는 **push 전에** 만들고(번호가 있어야 「남은 한계」 칸을 고친다), 이슈 칸 고침 · 생성 파일 · 화면 · 새 소식 커밋을 맨 끝에 둔다.
6. **push 는 한 번, 맨 끝에.**
   ```bash
   git -C $S/integ fetch -q origin
   git -C $S/integ rebase origin/main                  # 그사이 main 이 옮겨졌고 겹치는 파일이 없을 때. 겹치면 2절의 방법으로
   python3 .claude/skills/shared-commit/check_msg.py -C $S/integ origin/main..HEAD
   git -C $S/integ push origin HEAD:main
   NEW=$(git -C $S/integ rev-parse HEAD)
   ```
   공유 트리는 `shared-commit` 스킬 5번(`merge-file` → `reset --mixed $NEW` → `checkout`)으로 맞추고, 같은 트리의 다른 세션에 알린다.
7. **댓글 · 닫기 · 라벨 · `next-session.md`.** `close-issue` 스킬. 에이전트의 댓글 초안은 통합자에게 한 말을 지우고 자리표시를 push 된 해시로 채운 뒤 `.claude/skills/close-issue/check_comment.py` 로 본다.
8. **정리는 자기 id 만.**
   ```bash
   for id in <이 라운드에서 내가 띄운 id 들>; do
     W=.claude/worktrees/agent-$id
     git -C $W status --short --untracked-files=no      # 커밋 안 된 것이 있는지
     git log --oneline main..worktree-agent-$id | cat   # main 에 없는 커밋이 있는지(제목으로 main 에 들었는지 본다)
   done
   git worktree remove .claude/worktrees/agent-<id> && git branch -D worktree-agent-<id>     # 확인한 것만, 하나씩
   git worktree remove $S/integ && git branch -D integ-<이름>
   ```
   - **`.claude/worktrees/agent-*` 를 glob 으로 돌며 지우지 않는다.** 다른 세션의 돌고 있는 에이전트 worktree 를 지운 적이 있다. 잘못 지웠으면 `git fsck --unreachable --no-reflogs` 로 커밋을 찾아 브랜치를 되살리고 그 세션에 바로 알린다.
   - `locked` 로 표시된 worktree(백그라운드 일을 기다리다 끝난 에이전트)는 억지로 지우지 않고 둔다.
   - vite 들을 끈다(포트마다 `ss -ltnp` 의 pid 로).

## 알려진 함정

- `cd .claude/worktrees/<…>` 나 `cd web` 은 통합자 세션의 작업 폴더를 옮긴다. `git -C` 와 서브셸만 쓴다.
- `pgrep -f … | xargs kill` · `pkill -f` 는 그 명령을 돌리는 자기 셸도 잡는다. pid 는 `ss -ltnp | grep :<포트>` 에서 읽는다.
- rebase · checkout 한 트리를 내보내던 vite 는 다시 띄운다(바뀐 파일을 index.html 로 돌려준다).
- 충돌을 풀 때 `git add -A <폴더>` 를 쓰지 않는다(심볼릭 링크와 낡은 생성 파일이 딸려 간다).
- 커밋 메시지의 이슈 번호는 줄 끝만이 아니라 어디든 `#숫자` 로 찾는다. 80자는 글자 수로 센다(`check_msg.py`).
- `tools/photofit/.cache/lm_verts.npz` 는 GLB 를 다시 만들어도 그대로다. 사진 맞춤 에이전트를 띄우기 전에 새로 쓴다(`regen` 스킬).
- 에이전트들이 같은 Chrome 을 쓰면 서로의 탭을 닫지 않게 한다. alert · confirm 을 띄우는 버튼은 누르지 않게 한다.
- `gh issue create` 나 이웃 저장소 push 가 권한으로 막히면 다시 시도하지 말고 사용자에게 알리고 `next-session.md` 에 남긴다.
- 라운드가 세션을 넘기면 `next-session.md` 맨 위에 「라운드 도는 중」과 통합 브랜치 · worktree · `$S` 경로를 적는다.
