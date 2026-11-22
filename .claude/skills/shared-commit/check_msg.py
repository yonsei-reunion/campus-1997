"""커밋 메시지가 CLAUDE.md 「커밋과 이슈」 규칙에 맞는지 본다.

  python3 .claude/skills/shared-commit/check_msg.py                  # origin/main..HEAD 의 커밋
  python3 .claude/skills/shared-commit/check_msg.py <범위나 리비전>   # 예: origin/main..integ-x, -3, <해시>^!
  python3 .claude/skills/shared-commit/check_msg.py --file msg.txt   # 커밋하기 전의 메시지 파일
  python3 .claude/skills/shared-commit/check_msg.py -C <worktree> origin/main..HEAD   # 다른 worktree 의 커밋

보는 것
- 모든 줄 80자 안(글자 수: awk · wc 는 한글을 바이트로 세므로 여기서 셈)
- 첫 줄: 비어 있지 않고, conventional commit 접두어(feat: · fix: · chore: …)가 없음. 둘째 줄은 빈 줄
- 이슈 번호(#12, Fixes #12)가 어디에도 없음
- 서명 · 세션 줄(Co-Authored-By, Claude-Session, claude.ai 링크, Generated with)이 없음
- 충돌 표시(<<<<<<<, |||||||, >>>>>>>)가 없음
어긋나면 줄마다 적고 종료 코드 1.
"""
import re
import subprocess
import sys

PREFIX = re.compile(r'^(feat|fix|chore|docs|doc|refactor|test|tests|style|perf|build|ci|revert|wip)(\([^)]*\))?!?:', re.I)
ISSUE = re.compile(r'#\d')
SIGN = re.compile(r'co-authored-by|claude-session|claude\.ai|generated with|noreply@anthropic', re.I)
MARK = re.compile(r'^(<{7}|\|{7}|>{7})( |$)')


def check(name, text):
    lines = text.rstrip('\n').split('\n')
    bad = []
    if not lines[0].strip():
        bad.append('첫 줄이 비었음')
    if PREFIX.match(lines[0]):
        bad.append('접두어: %s' % lines[0][:40])
    if len(lines) > 1 and lines[1].strip():
        bad.append('둘째 줄이 빈 줄이 아님')
    for i, l in enumerate(lines, 1):
        if len(l) > 80:
            bad.append('%d번째 줄 %d자: %s…' % (i, len(l), l[:30]))
        if ISSUE.search(l):
            bad.append('%d번째 줄에 이슈 번호: %s' % (i, l[:60]))
        if SIGN.search(l):
            bad.append('%d번째 줄에 서명 · 세션 줄: %s' % (i, l[:60]))
        if MARK.match(l):
            bad.append('%d번째 줄에 충돌 표시' % i)
    print('%s  %s' % (name, 'OK' if not bad else lines[0][:50]))
    for b in bad:
        print('    ' + b)
    return len(bad)


def main(argv):
    git = ['git']
    if argv[:1] == ['-C']:
        git, argv = ['git', '-C', argv[1]], argv[2:]
    if argv[:1] == ['--file']:
        return 1 if check(argv[1], open(argv[1]).read()) else 0
    rng = argv or ['origin/main..HEAD']
    hs = subprocess.check_output(git + ['log', '--format=%H'] + rng, text=True).split()
    if not hs:
        print('커밋 없음:', ' '.join(rng))
        return 0
    n = 0
    for h in hs:
        n += check(h[:8], subprocess.check_output(git + ['log', '-1', '--format=%B', h], text=True))
    print('%d 커밋, 어긋난 곳 %d' % (len(hs), n))
    return 1 if n else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
