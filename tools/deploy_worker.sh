#!/usr/bin/env bash
# Cloudflare Worker y97-notes(notes-worker: 캠퍼스 쪽지의 쓰기 다리, 전체 순위의 판정, 메타모아 접속자 수)를 배포한다.
#
#   tools/deploy_worker.sh             배포
#   tools/deploy_worker.sh --dry-run   묶기만 해 보고 올리지 않음
#   tools/deploy_worker.sh --deps      Worker 를 이루는 파일 목록(tools/worker_deps.mjs)
#   tools/deploy_worker.sh --force     아래 검사를 건너뛰고 배포
#
# main 에 push 하면 .github/workflows/worker.yml 이 Worker 를 이루는 파일이 바뀌었을 때 이 스크립트로 배포한다.
# 손으로 돌리는 것은 급할 때나 Actions 가 안 될 때다.
#
# 검사(손으로 돌릴 때): Worker 를 이루는 파일이 origin/main 과 같아야 한다. 게임(GitHub Pages)은 origin/main 으로
# 나가므로, 아직 push 하지 않은 판정 자료(다른 세션이 고치는 중인 것도)를 올리면 게임과 Worker 가 어긋나 그 판은
# 「올릴 수 없는 판」이 된다. Actions 안(CI=true)에서는 받은 커밋이 곧 push 된 것이라 검사하지 않는다.
#
# 인증: 로컬은 `npx wrangler login` 한 계정, Actions 는 CLOUDFLARE_API_TOKEN · CLOUDFLARE_ACCOUNT_ID.
# Worker 의 secret(DOLT_TOKEN · RANK_KEY · GA_SA · METAMOA_KEY)은 배포로 바뀌지 않는다(npx wrangler secret put).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRANGLER="wrangler@4"
URL="https://y97-notes.habit-chain-worker.workers.dev"
dry=0 force=0
for a in "$@"; do
  case "$a" in
    --dry-run) dry=1 ;;
    --force) force=1 ;;
    --deps) exec node "$ROOT/tools/worker_deps.mjs" ;;
    -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "모르는 인자: $a" >&2; exit 2 ;;
  esac
done

cd "$ROOT"
mapfile -t deps < <(node tools/worker_deps.mjs)
echo "Worker 를 이루는 파일 ${#deps[@]}개"

dirty=0
if [ "${CI:-}" != "true" ]; then
  git fetch -q origin main
  mapfile -t off < <(git diff --name-only origin/main -- "${deps[@]}")
  mapfile -t new < <(git ls-files --others --exclude-standard -- "${deps[@]}")
  if [ "${#off[@]}" -gt 0 ] || [ "${#new[@]}" -gt 0 ]; then
    dirty=1
    echo "origin/main($(git rev-parse --short origin/main))과 다른 파일:" >&2
    printf '  %s\n' "${off[@]}" "${new[@]}" >&2
    if [ "$dry" = 0 ] && [ "$force" = 0 ]; then
      echo "배포하지 않음(push 한 뒤 다시, 또는 --force)" >&2
      exit 1
    fi
  else
    echo "origin/main($(git rev-parse --short origin/main))과 같음"
  fi
fi

cd "$ROOT/notes-worker"
if [ "$dry" = 1 ]; then
  out="$(mktemp -d)"
  npx --yes "$WRANGLER" deploy --dry-run --outdir "$out"
  echo "묶음: $(du -sh "$out" | cut -f1) ($out)"
  exit 0
fi
# 배포 메시지에 커밋 해시를 남긴다: worker.yml 이 「떠 있는 배포 뒤로 바뀐 파일」을 볼 때의 기준.
# origin/main 과 다른 채(--force) 올렸으면 해시가 아닌 말을 남겨 다음 push 때 Actions 가 다시 배포하게 한다
if [ "${CI:-}" = "true" ]; then msg="$(git -C "$ROOT" rev-parse HEAD)"; else msg="$(git -C "$ROOT" rev-parse origin/main)"; fi
[ "$dirty" = 1 ] && msg="forced, not on origin/main"
npx --yes "$WRANGLER" deploy --message "$msg"

# 떠 있는지: 5xx 나 연결 실패면 배포가 깨진 것
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$URL/" || true)"
echo "$URL → HTTP $code"
case "$code" in 5*|000) echo "Worker 가 답하지 않음" >&2; exit 1 ;; esac
