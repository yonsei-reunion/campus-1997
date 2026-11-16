"""새 소식(releases.json) 한 날짜의 요약을 메타모아 업데이트 소식으로 올린다.

    python3 tools/metamoa_update.py                  # 어제(한국 시각) 새 소식
    python3 tools/metamoa_update.py --date 2026-11-15
    python3 tools/metamoa_update.py --text "직접 쓴 소식"
    python3 tools/metamoa_update.py --dry-run         # 올리지 않고 글만 보임

공간 키는 METAMOA_KEY, 공간 id 는 METAMOA_SPACE_ID 에서 읽는다(.envrc,
Actions secret). 키가 없으면 올리지 않고 끝낸다.

메타모아 한도: 24시간에 한 번, 200자 · 세 줄, 링크는 이 사이트만.
24시간이 안 돼 거절되면(429) 남은 시간이 두 시간 안일 때만 기다렸다
다시 올린다(전날 실행이 밀린 경우). 더 길면 실패로 치지 않고 끝낸다.
"""
import argparse, datetime, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
RELEASES = ROOT / 'web/public/data/releases.json'
SITE = 'https://yonsei-1997.benelog.net/'
LIMIT = 200


def compose(entry):
    m, d = int(entry['date'][5:7]), int(entry['date'][8:10])
    items = list(entry.get('summary') or [])
    link = f"{SITE}news.html?d={entry['date']}"
    while items:
        # 항목 안에 「·」 「,」가 있어 항목 사이는 「 / 」
        head = f"{m}월 {d}일 새 소식: " + ' / '.join(items)
        for text in (f'{head}\n{link}', head):
            if len(text) <= LIMIT:
                return text
        items.pop()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='YYYY-MM-DD (기본: 어제, 한국 시각)')
    ap.add_argument('--text', help='새 소식 대신 이 글을 올림')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    if a.text:
        text = a.text.strip()
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
    if len(text) > LIMIT or text.count('\n') > 2:
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
                 'Content-Type': 'application/json'},
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
