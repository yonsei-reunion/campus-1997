"""web/public/data/releases.json 이 CLAUDE.md 「새 소식」 규칙에 맞는지 본다(고치지 않고 알리기만 함).

  python3 .claude/skills/news/check_news.py                 # 맨 위 날짜를 자세히, 나머지는 HEAD 와 견주기만
  python3 .claude/skills/news/check_news.py 2026-11-21      # 그 날짜를 자세히
  python3 .claude/skills/news/check_news.py --all           # 모든 날짜를 자세히(옛 항목의 경고가 많이 나옴)

「틀림」(종료 코드 1): json 이 깨짐, 날짜 순서 · 중복, title, 카테고리 이름 · 순서 · 중복, 요약 100자 넘김, 없는 그림 파일,
  assets/news/ 밖의 그림, 빈 캡션, 세 단계 넘는 하위 목록, 손대지 않은 날짜의 글자가 HEAD 와 달라짐(파일을 통째로 다시 씀)
「볼 것」(종료 코드 0): 요약 항목 수(둘 ~ 다섯), 요약이 한 줄이 아님, 「~다.」로 끝나는 항목, 쉼표 셋 넘는 항목, 이슈 번호,
  HEAD 와 내용이 달라진 다른 날짜, 어느 날짜도 가리키지 않는 그림 파일
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
REL = 'web/public/data/releases.json'
ORDER = ['사람', '건물', '땅 · 정원', '백양로', '시설', '추억 카드', '화면 · 조작', '걷기 · 충돌', '성능', '자료']
bad, note = [], []


def spans(src):
    """맨 위 배열의 항목마다 (항목, 원문 글자)"""
    dec, i, out = json.JSONDecoder(), src.index('[') + 1, []
    while True:
        while src[i] in ' \t\r\n,':
            i += 1
        if src[i] == ']':
            return out
        e, j = dec.raw_decode(src, i)
        out.append((e, src[i:j]))
        i = j


def items(tag, its, depth=1):
    if depth > 3:
        bad.append('%s: 하위 목록이 세 단계를 넘음' % tag)
    for it in its:
        text = it if isinstance(it, str) else it.get('text', '')
        if not isinstance(it, str):
            if set(it) - {'text', 'items'} or not it.get('items'):
                bad.append('%s: 묶는 항목은 text 와 items 만: %s' % (tag, text[:30]))
            items(tag, it.get('items', []), depth + 1)
        if re.search(r'(다|요)\.?$', text.strip()) or text.strip().endswith('.'):
            note.append('%s: 명사형으로 끝나지 않음: …%s' % (tag, text.strip()[-24:]))
        if text.count(',') > 3:
            note.append('%s: 쉼표 %d개(하위 목록으로 나눌지): %s…' % (tag, text.count(','), text[:30]))
        if re.search(r'#\d', text):
            note.append('%s: 이슈 번호: %s…' % (tag, text[:40]))


def entry(e, raw):
    d = e.get('date', '?')
    s = e.get('summary')
    if not isinstance(s, list) or not s:
        bad.append('%s: summary 가 목록이 아님' % d)
    else:
        n = sum(len(x) for x in s)
        print('%s 요약 %d항목 %d자: %s' % (d, len(s), n, ' / '.join(s)))
        if n > 100:
            bad.append('%s: 요약 %d자(100자 안쪽으로)' % (d, n))
        if not 2 <= len(s) <= 5:
            note.append('%s: 요약 항목 %d개(두세 개, 많아야 다섯)' % (d, len(s)))
        if not re.search(r'"summary": \[[^\n]*\],?\n', raw):
            note.append('%s: "summary" 가 한 줄이 아님(이 파일의 관례)' % d)
    cats = [g.get('category') for g in e.get('groups', [])]
    for c in cats:
        if c not in ORDER:
            bad.append('%s: 없는 카테고리 「%s」' % (d, c))
    known = [c for c in cats if c in ORDER]
    if len(set(known)) != len(known):
        bad.append('%s: 같은 카테고리가 두 번' % d)
    if known != sorted(known, key=ORDER.index):
        bad.append('%s: 카테고리 순서 %s' % (d, ' → '.join(known)))
    for g in e.get('groups', []):
        tag = '%s 「%s」' % (d, g.get('category'))
        if set(g) - {'category', 'items', 'images'}:
            bad.append('%s: 모르는 키 %s' % (tag, sorted(set(g) - {'category', 'items', 'images'})))
        items(tag, g.get('items', []))
        for im in g.get('images', []):
            src = im.get('src', '')
            if not src.startswith('assets/news/'):
                bad.append('%s: 그림이 assets/news/ 밖: %s' % (tag, src))
            elif not os.path.exists(os.path.join(ROOT, 'web/public', src)):
                bad.append('%s: 그림 파일 없음: %s' % (tag, src))
            if not im.get('alt', '').strip():
                bad.append('%s: 캡션(alt) 없음: %s' % (tag, src))


def main(argv):
    src = open(os.path.join(ROOT, REL), encoding='utf-8').read()
    try:
        sp = spans(src)
    except (ValueError, IndexError) as ex:
        print('틀림: json 을 읽지 못함:', ex)
        return 1
    dates = [e.get('date') for e, _ in sp]
    if dates != sorted(dates, reverse=True) or len(set(dates)) != len(dates):
        bad.append('날짜가 새것부터가 아니거나 겹침: %s' % ' '.join(str(d) for d in dates[:6]))
    for e, _ in sp:
        if 'title' in e:
            bad.append('%s: title 을 쓰지 않음' % e.get('date'))
        if set(e) - {'date', 'summary', 'groups', 'title'}:
            bad.append('%s: 모르는 키 %s' % (e.get('date'), sorted(set(e) - {'date', 'summary', 'groups'})))
    want = dates if '--all' in argv else [a for a in argv if not a.startswith('-')] or dates[:1]
    for e, raw in sp:
        if e.get('date') in want:
            entry(e, raw)
    for w in want:
        if w not in dates:
            bad.append('%s: 그 날짜가 없음' % w)
    # HEAD 와 견줌: 손대지 않은 날짜는 글자 하나 달라지면 안 됨
    try:
        head = {e.get('date'): (e, raw) for e, raw in spans(subprocess.check_output(
            ['git', '-C', ROOT, 'show', 'HEAD:' + REL], text=True, encoding='utf-8'))}
    except (subprocess.CalledProcessError, ValueError, IndexError):
        head = {}
    for e, raw in sp:
        d = e.get('date')
        if d not in head:
            print('%s: HEAD 에 없는 새 날짜' % d)
        elif head[d][0] != e:
            (print if d in want else note.append)('%s: HEAD 와 내용이 다름%s' % (d, '' if d in want else '(다른 세션이 고치는 중이거나 손댄 것인지 볼 것)'))
        elif head[d][1] != raw:
            bad.append('%s: 내용은 같은데 글자가 달라짐(json.dump 로 통째로 다시 썼는지)' % d)
    used = {im.get('src', '').split('/')[-1] for e, _ in sp for g in e.get('groups', []) for im in g.get('images', [])}
    news = os.path.join(ROOT, 'web/public/assets/news')
    loose = sorted(f for f in os.listdir(news) if f not in used)
    if loose:
        note.append('어느 날짜도 가리키지 않는 그림 %d개: %s' % (len(loose), ' '.join(loose[:8]) + (' …' if len(loose) > 8 else '')))
    nums = [int(m.group(1)) for m in (re.match(r'(\d+)', f) for f in os.listdir(news)) if m]
    print('그림 번호: 지금 가장 큰 번호 %d → 다음 %d (폴더의 파일 기준. 다른 세션의 추적 안 된 파일도 셈)' % (max(nums), max(nums) + 1))
    for b in bad:
        print('틀림:', b)
    for n in note:
        print('볼 것:', n)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
