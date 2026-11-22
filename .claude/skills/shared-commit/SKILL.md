---
name: shared-commit
description: 여러 Claude 세션이 같은 작업 트리를 쓰는 이 저장소에서 자기 변경만 골라 커밋하고 origin main 에 push 한다. 자기 파일만 git add <경로>, 다른 세션의 변경이 같은 파일에 섞였거나 main 이 앞서 있으면 임시 worktree 에서 자기 변경만 다시 적용해 커밋 → push → 공유 트리에서 git reset --mixed. 커밋 메시지 규칙(모든 줄 80자, 접두어 · 이슈 번호 · 서명 줄 없음)도 검사한다. 「커밋해줘」, 「push 해줘」, 「내 것만 커밋」, 라운드 끝에 main 에 올릴 때 쓴다.
---

# 공유 트리에서 자기 변경만 커밋

규칙은 `CLAUDE.md` 「여러 세션」 · 「커밋과 이슈」에 있다. 같은 작업 트리(와 같은 인덱스)를 다른 세션이 함께 쓰므로, **내가 고치지 않은 것은 커밋하지도, 되돌리지도, stage 를 풀지도 않는다.**

- `$S`: 이 세션의 스크래치 폴더
- 다른 worktree 를 다룰 때는 `cd` 하지 않고 `git -C <경로>` 를 쓴다(`cd` 는 세션의 작업 폴더를 옮긴다)
- 한글 경로가 따옴표로 묶여 나오면 `git -c core.quotepath=false status --short`

## 순서

1. **무엇이 내 것인지 가른다.**
   ```bash
   git fetch -q origin
   git status -sb                                  # main 이 origin/main 보다 뒤인지(behind)도 여기서 보인다
   git diff --cached --name-only                   # 다른 세션이 stage 해 둔 것이 있는지
   git diff -- <내가 고친 파일>                     # 덩어리마다 내 것인지 읽는다
   ```
   - 내가 고친 파일 목록은 기억이 아니라 이 세션에서 실제로 쓴 파일로 만든다. 모르는 변경은 다른 세션의 것이다.
   - 커밋하지 않는 것: `next-session.md`(추적하지 않는 파일), `.envrc`, `.claude/settings.local.json`, 스크래치의 캡처 · 로그, 저장소에 넣지 않기로 한 사진(로드뷰 · 항공사진 조각: `CLAUDE.md` 「고증 자료」).
   - 에이전트로 일하는 중이면 생성 파일(GLB, `campus.json`, 해 그림자 PNG, 잎 아틀라스)과 `releases.json` 은 커밋하지 않는다(통합자가 한 번 다시 만든다).
2. **길을 고른다.**
   - (가) 내 파일에 다른 세션의 변경이 없고 `main` 이 `origin/main` 과 같다 → 3번(공유 트리에서 바로).
   - (나) 같은 파일에 다른 세션의 변경이 섞였거나 `origin/main` 이 앞서 있다 → 4번(임시 worktree).
   - 다른 세션이 stage 해 둔 파일이 있어도 (가)로 갈 수 있다. 3번의 `git commit … -- <경로>` 는 준 경로만 커밋하고 남의 stage 는 그대로 둔다.
3. **(가) 공유 트리에서 바로.**
   ```bash
   git add <경로> <경로>                            # 파일 이름으로만. -A · `.` · 폴더 통째로는 쓰지 않는다
   git diff --cached --stat                        # 내 파일이 다 들었는지(남의 것이 보여도 풀지 않는다)
   python3 .claude/skills/shared-commit/check_msg.py --file $S/msg.txt
   git commit -F $S/msg.txt -- <경로> <경로>        # 경로를 주면 그 파일만 커밋된다(남이 stage 해 둔 것은 그대로 남음)
   python3 .claude/skills/shared-commit/check_msg.py
   git push origin main
   ```
   - `index.lock` 에러는 다른 세션의 git 이 도는 중이다. 잠깐 뒤 다시 한다. 잠금 파일을 지우지 않는다.
   - push 가 거절되면(다른 세션이 먼저 올림) 강제로 밀지 않는다. 방금 한 커밋은 그대로 두고, 4번의 임시 worktree 에서 `origin/main` 위에 `cherry-pick` 해 올린 뒤 5번으로 맞춘다.
4. **(나) 임시 worktree 에서 자기 변경만 다시 적용.**
   ```bash
   git worktree add --detach $S/wt_commit origin/main
   ```
   - 통째로 내 것인 파일: `cp --parents <경로> $S/wt_commit/` (공유 트리 루트에서). 지운 파일은 `git -C $S/wt_commit rm <경로>`.
   - 섞인 파일: `git diff -- <경로> > $S/mine.patch` 에서 남의 덩어리를 지운 뒤 `git -C $S/wt_commit apply $S/mine.patch`. 덩어리를 가르기 어려우면 worktree 의 그 파일에 내 수정만 손으로 다시 넣는다.
   - 이미 공유 트리의 `main` 에 커밋해 둔 것을 옮길 때: `git -C $S/wt_commit cherry-pick <해시>…`
   ```bash
   git -C $S/wt_commit status --short              # 내 변경만인지
   git -C $S/wt_commit diff                        # 한 번 더 읽는다
   git -C $S/wt_commit add <경로> <경로>
   python3 .claude/skills/shared-commit/check_msg.py --file $S/msg.txt
   git -C $S/wt_commit commit -F $S/msg.txt
   python3 .claude/skills/shared-commit/check_msg.py -C $S/wt_commit origin/main..HEAD
   git -C $S/wt_commit push origin HEAD:main
   NEW=$(git -C $S/wt_commit rev-parse HEAD)
   ```
   - 코드 · 데이터를 손으로 다시 넣었으면 push 전에 그 worktree 에서 확인한다(문법, `python3 -m json.tool`, 필요하면 빌드). 충돌을 풀었으면 `git -C $S/wt_commit grep -nIE '^(<{7}|>{7}|\|{7})( |$)'` 가 비어야 한다.
   - push 가 거절되면 `git -C $S/wt_commit fetch -q origin && git -C $S/wt_commit rebase origin/main` 뒤 다시 본다. 강제 push 는 하지 않는다.
5. **공유 트리를 새 main 에 맞춘다(4번으로 올렸을 때).** `git merge --ff-only` 는 더러운 파일 하나만 겹쳐도 거절하므로 이렇게 한다.
   ```bash
   OLD=$(git rev-parse HEAD)
   export LC_ALL=C                                                    # (sort · comm 이 한글 경로를 바이트 순서로 보게: 아래 설명)
   Q="git -c core.quotepath=false"                                    # (한글 경로가 따옴표 없이 나오게)
   $Q diff --name-only $OLD $NEW | sort > $S/up.txt                   # 위에서 바뀐 파일(내 것 포함)
   $Q diff --name-only --diff-filter=D $OLD $NEW | sort > $S/gone.txt # 그 가운데 위에서 지워진 것
   $Q diff --name-only HEAD | sort > $S/dirty.txt                     # 공유 트리에서 더러운 파일(reset 하기 전에 받아 둔다)
   # (1) 위에서도 바뀌고 여기서도 더러운 파일: reset 하기 전에 세 갈래로 합친다
   for f in $(comm -12 $S/up.txt $S/dirty.txt); do
     git show $OLD:$f > $S/base; git show $NEW:$f > $S/new
     git merge-file $f $S/base $S/new || echo "충돌: $f"
   done
   # (2) HEAD 와 인덱스만 옮긴다. 작업 파일은 그대로
   git reset --mixed $NEW
   # (3) 여기서 깨끗했던 파일을 새 내용으로(지워진 것은 빼고)
   for f in $(comm -23 $S/up.txt $S/dirty.txt | comm -23 - $S/gone.txt); do git checkout $NEW -- $f; done
   git -c core.quotepath=false status --short                          # 남은 것은 다른 세션의 변경뿐이어야 한다
   git diff --stat                                                     # 위의 변경이 거꾸로(되돌린 것처럼) 보이는 파일이 없어야 한다
   ```
   - 이 묶음은 한 번의 셸 호출로 돌린다(`LC_ALL` · `OLD` · `Q` 가 이어져야 한다). `LC_ALL=C` 가 없으면 `comm` 이 한글 이름 둘을 같은 줄로 보고 빠뜨려, (3)에서 그 파일이 옛 내용으로 남는다.
   - (1)의 `merge-file` 은 작업 파일(지금 것) · 옛 HEAD · 새 HEAD 를 합친다. 양쪽에 똑같이 든 내 변경은 한 번만 남고, 남의 변경과 위의 변경이 함께 남는다. 「충돌」이 찍힌 파일은 남의 줄을 살리는 쪽으로 손으로 푼다. 경로에 빈칸이 있으면 `for` 대신 한 파일씩 한다.
   - GLB · PNG 같은 생성 파일이 (1)에 걸리면 합치지 않는다. 그 세션에 알리고, 내 것이면 `git checkout $NEW -- <경로>` 로 맞춘다.
   - 위에서 지워진 파일(`$S/gone.txt` 에 든 것)은 reset 뒤 추적 안 됨(`??`)으로 남는다. `dirty.txt` 에 없던 것만 지운다.
   - 다른 세션이 stage 해 두었던 파일은 `reset --mixed` 로 stage 가 풀린다(작업 파일은 그대로, 새 파일은 `??` 로). 그 세션에 알린다.
   - 내 파일이 `status` 에 남아 있으면 `git diff -- <경로>` 로 무엇이 다른지 본다(남의 변경이면 그대로 둔다).
   - 3번에서 공유 트리의 `main` 에 커밋한 뒤 push 가 거절되어 4번으로 `cherry-pick` 해 올렸을 때도 같다(`OLD` 가 그 커밋).
6. **뒷정리와 알림.**
   ```bash
   git worktree remove $S/wt_commit                 # 내가 만든 그 경로만
   git log --oneline -3 origin/main
   ```
   - 같은 트리의 다른 세션 · 에이전트에 연락할 수 있으면 main 이 옮겨졌다고 알린다(해시와 바뀐 파일).
   - worktree 를 지울 때 `.claude/worktrees/agent-*` 를 glob 으로 돌지 않는다. 다른 세션의 돌고 있는 에이전트가 거기 있다. 내가 띄운 id 의 것만, `git -C <그 worktree> status --short` 로 커밋 안 된 것이 없는지 본 뒤 지운다.
   - 이슈를 다 했으면 `close-issue` 스킬.

## 커밋 메시지

- 모든 줄 80자 안(글자 수). `awk` · `wc` 는 한글을 바이트로 세니 `check_msg.py` 로 센다.
- 첫 줄: 무엇을 바꿨는지 한 줄. `feat:` · `fix:` 같은 접두어 없음. 빈 줄 뒤 본문은 왜 · 어떻게를 짧은 문단이나 「- 」 목록으로.
- 이슈 번호(`#12`, `Fixes #12`)를 적지 않는다. 이슈에는 push 뒤 댓글로 커밋 링크를 단다.
- 서명 · 세션 줄(`Co-Authored-By`, `Claude-Session:`, claude.ai 링크)을 넣지 않는다.
- 잰 값 · 사진 출처 같은 긴 설명은 `reference/고증/` 이나 새 소식에 두고 되풀이하지 않는다.
- 메시지는 파일로 써서 `git commit -F` 로 준다(셸 따옴표 안의 한글 · 「」 가 깨지지 않게).

실제 커밋 하나(576528ba):

```
장기원 기념관 동쪽 면: v 4.75 → 3.95 (몸체 폭 10.15 m)

1996년 겨울 네 장(동쪽 코스 27/16 · 27/17 은 사진 면 가장자리에 동쪽 면이
찍힘)의 난간 윗선을 함께 풀고, 1:5000 수치지형도 2005년판의 폭으로 견줌.
서쪽 면 · 남쪽 끝 · 북쪽 끝은 그대로. 동쪽 띠 · 포장 길 · 동쪽 문은 면을
따라 함께 옮겨지고, 띠의 가 · 옹벽 · 나무는 따로 읽은 자리 그대로.
고증 3.16 「변의 자리」 · 크기와 남은 한계 줄을 새 값으로 고침.
```

## 알려진 함정

- **`git add -A <폴더>` 는 쓰지 않는다.** 심볼릭 링크(`web/node_modules`)와 낡은 생성 파일이 함께 올라간 적이 있다. 충돌을 풀 때도 푼 파일을 이름으로 더한다.
- **`git stash` 는 남의 변경을 건드린다.** 꼭 써야 하면 `git stash push -- <내가 다룰 파일>` 로 파일을 정해서, 곧바로 `git stash pop` 한다. 경로 없는 `git stash` · `git checkout .` · `git restore .` · `git clean` 은 하지 않는다.
- **지운 그림을 일찍 stage 해 두면** 다음 커밋에 딸려 들어간다. 삭제는 그것이 속한 커밋 직전에 stage 한다.
- **원격은 SSH.** `git remote -v` 가 `git@github.com:…` 이 아니면 SSH 주소로 바꾼 뒤 push 한다. HTTPS 인증이 실패하면 바로 SSH 로.
- **이웃 저장소**(`../yonsei-anthology`)의 그림이 바뀌었으면 그 저장소에서 따로 커밋한다. push 하면 배포되니 사용자가 원할 때만.
- 브랜치 `main` 에 바로 올린다(이 저장소의 관례). 통합 브랜치(`integ-*`)는 `agent-round` 스킬.
