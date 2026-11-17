"""새 소식(releases.json) 한 날짜의 요약을 메타모아 업데이트 소식으로 올린다.

    python3 tools/metamoa_update.py                  # 어제(한국 시각) 새 소식
    python3 tools/metamoa_update.py --date 2026-11-15
    python3 tools/metamoa_update.py --text "직접 쓴 소식"
    python3 tools/metamoa_update.py --dry-run         # 올리지 않고 글만 보임

공간 키는 METAMOA_KEY, 공간 id 는 METAMOA_SPACE_ID 에서 읽는다(.envrc,
Actions secret). 키가 없으면 올리지 않고 끝낸다.

메타모아 한도: 24시간에 한 번, 200자 · 세 줄, 링크는 이 사이트만.
요약 항목은 줄마다 나눈다(세 줄이 넘으면 이웃 항목끼리 묶음).
24시간이 안 돼 거절되면(429) 남은 시간이 두 시간 안일 때만 기다렸다
다시 올린다(전날 실행이 밀린 경우). 더 길면 실패로 치지 않고 끝낸다.
"""
import argparse, datetime, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
RELEASES = ROOT / 'web/public/data/releases.json'
SITE = 'https://yonsei-1997.benelog.net/'
# Cloudflare 가 Python-urllib 기본 User-Agent 를 막는다(403, error code 1010)
USER_AGENT = 'campus-1997-metamoa/1.0'
LIMIT = 200
MAX_LINES = 3


def compose(entry):
    """요약 항목을 줄마다. 세 줄이 넘으면 이웃 항목을 「 / 」로 묶어 세 줄로.

    공간 페이지는 줄바꿈을 그대로 보이지만 주소는 링크가 되지 않아
    새 소식 주소는 넣지 않는다(세 줄을 항목에 쓴다).
    """
    m, d = int(entry['date'][5:7]), int(entry['date'][8:10])
    items = list(entry.get('summary') or [])
    while items:
        best = None
        for lines in split_lines(items, MAX_LINES):
            lines[0] = f'{m}월 {d}일 · {lines[0]}'
            text = '\n'.join(lines)
            key = max(map(len, lines))
            if len(text) <= LIMIT and (best is None or key < best[0]):
                best = (key, text)
        if best:
            return best[1]
        items.pop()
    return None


def split_lines(items, n):
    """항목을 순서대로 n 줄 안으로 묶는 모든 방법(줄 안은 「 / 」)."""
    if len(items) <= n:
        yield list(items)
        return
    if n == 1:
        yield [' / '.join(items)]
        return
    for k in range(1, len(items) - n + 2):
        for rest in split_lines(items[k:], n - 1):
            yield [' / '.join(items[:k])] + rest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='YYYY-MM-DD (기본: 어제, 한국 시각)')
    ap.add_argument('--text', help='새 소식 대신 이 글을 올림')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    if a.text:
        # Actions 입력 칸은 한 줄이라 「\\n」 을 줄바꿈으로
        text = a.text.strip().replace('\\n', '\n')
    else:
        today = datetime.datetime.now(ZoneInfo('Asia/Seoul')).date()
        date = a.date or (today - datetime.timedelta(days=1)).isoformat()
        entry = next((e for e in json.loads(RELEASES.read_text())
                      if e['date'] == date), None)
        if not entry:
            print(f'{date} 새 소식이 없어 올리지 않음')
            return
        text = compose(entry)
        if not text:
            sys.exit(f'{date} 요약이 비었거나 {LIMIT}자를 넘음')
    if len(text) > LIMIT or text.count('\n') >= MAX_LINES:
        sys.exit(f'{LIMIT}자 · 세 줄을 넘음:\n{text}')
    print(text)
    if a.dry_run:
        return

    key = os.environ.get('METAMOA_KEY', '').strip()
    space = os.environ.get('METAMOA_SPACE_ID', '').strip()
    if not key or not space:
        print('METAMOA_KEY · METAMOA_SPACE_ID 가 없어 올리지 않음')
        return
    for attempt in (1, 2):
        code, body, wait = post(space, key, text)
        print(f'HTTP {code} {body}')
        if code == 201:
            return
        if code == 400 and 'link' in body and '\n' in text:
            # 링크를 다른 사이트로 읽어 거절하면 링크 줄을 빼고 한 번 더
            text = text.rsplit('\n', 1)[0]
            print(f'링크를 빼고 다시 올림:\n{text}')
            code, body, wait = post(space, key, text)
            print(f'HTTP {code} {body}')
            if code == 201:
                return
        if code != 429:
            sys.exit(1)
        if attempt == 2 or wait is None or wait > MAX_WAIT:
            print('24시간 안에 이미 올림: 건너뜀')
            return
        print(f'{wait}초 뒤 다시 올림')
        time.sleep(wait + 30)


MAX_WAIT = 2 * 3600


def post(space, key, text):
    req = urllib.request.Request(
        f'https://metamoa.com/api/update/{space}',
        data=json.dumps({'text': text}, ensure_ascii=False).encode(),
        headers={'Authorization': f'Bearer {key}',
                 'Content-Type': 'application/json',
                 'User-Agent': USER_AGENT},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode(), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        wait = e.headers.get('Retry-After')
        try:
            wait = int(json.loads(body).get('retry_after', wait))
        except (ValueError, TypeError, AttributeError):
            wait = int(wait) if wait and wait.isdigit() else None
        return e.code, body, wait


if __name__ == '__main__':
    main()
