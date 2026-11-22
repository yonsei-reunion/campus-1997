"""이슈 댓글 · 새 이슈 본문 초안(md)을 올리기 전에 본다: 링크가 가리키는 것이 push 된 main 에 있는지.

  python3 .claude/skills/close-issue/check_comment.py <초안.md> [초안.md …] [--ref origin/main]

「틀림」(종료 코드 1)
- blob/main/<경로> 링크의 파일이 --ref(기본 origin/main)에 없음
- 고증 파일 링크 바로 뒤에 적은 「절 · 줄 이름」이 그 파일에 글자 그대로 없음
- commit/<해시> 링크의 커밋이 --ref 에 들어 있지 않음(아직 push 하지 않았거나 다시 쓴 해시)
- 채우지 않은 자리표시 <<…>>, 충돌 표시
「볼 것」
- 「사진 A」를 링크 없이 적음(GitHub 에서 읽는 사람은 어느 사진인지 모름)
- 통합자에게 한 말이 남음(「닫아도 됨」, 「권함」, 에이전트 이름처럼 보이는 것)
- 숫자가 많은 표(잰 값은 고증 파일에 두고 링크로)
"""
import re
import subprocess
import sys
import urllib.parse

REPO = 'https://github.com/yonsei-reunion/campus-1997/'


def git(*a):
    return subprocess.run(['git'] + list(a), capture_output=True, text=True)


def check(path, ref):
    t = open(path, encoding='utf-8').read()
    bad, note = [], []
    link = re.compile(r'\]\(' + re.escape(REPO) + r'blob/main/([^)\s]+)\)((?:\s*「[^」]+」(?:\s*·)?)*)')
    for m in link.finditer(t):
        rel = urllib.parse.unquote(m.group(1)).split('#')[0]
        if git('cat-file', '-e', '%s:%s' % (ref, rel)).returncode:
            bad.append('없는 파일: %s' % rel)
            continue
        if rel.endswith('.md'):
            body = git('show', '%s:%s' % (ref, rel)).stdout
            for q in re.findall(r'「([^」]+)」', m.group(2)):
                if q not in body:
                    bad.append('%s 에 「%s」 가 없음' % (rel.split('/')[-1], q))
    for h in set(re.findall(re.escape(REPO) + r'commit/([0-9a-f]{7,40})', t)):
        if git('merge-base', '--is-ancestor', h, ref).returncode:
            bad.append('%s 에 없는 커밋: %s' % (ref, h))
    for ph in set(re.findall(r'<<[^>\n]+>>', t)):
        bad.append('자리표시가 남음: %s' % ph)
    if re.search(r'(?m)^(<{7}|\|{7}|>{7})( |$)', t):
        bad.append('충돌 표시')
    for m in re.finditer(r'사진 A', t):
        if not re.search(r'\[[^\]]*$', t[max(0, m.start() - 60):m.start()]):       # (링크 글 안이 아님)
            note.append('「사진 A」에 링크 없음(%d번째 줄)' % (t.count('\n', 0, m.start()) + 1))
            break
    for w in ('닫아도 됨', '닫지 말고', '권함', '통합자'):
        if w in t:
            note.append('통합자에게 한 말로 보임: 「%s」' % w)
    rows = [l for l in t.split('\n') if l.startswith('|') and len(re.findall(r'\d+\.\d+', l)) >= 3]
    if len(rows) >= 3:
        note.append('숫자가 많은 표 %d줄(잰 값은 고증 파일에 두고 링크로)' % len(rows))
    print('%s  %s' % (path, 'OK' if not bad else '틀림 %d' % len(bad)))
    for b in bad:
        print('    틀림:', b)
    for n in note:
        print('    볼 것:', n)
    return len(bad)


def main(argv):
    ref = 'origin/main'
    if '--ref' in argv:
        i = argv.index('--ref')
        ref = argv[i + 1]
        del argv[i:i + 2]
    if not argv:
        sys.exit(__doc__)
    return 1 if sum(check(p, ref) for p in argv) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
