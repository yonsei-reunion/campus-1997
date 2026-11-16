"""메타모아 이벤트를 보고, 올리고, 지운다(첫 화면 「이벤트」 줄).

    python3 tools/metamoa_event.py list
    python3 tools/metamoa_event.py add --title "1분 슛 겨루기 주간" \\
        --start "2026-12-01 00:00" --end "2026-12-07 24:00" \\
        [--desc "대강당 앞 농구장"] [--daily 21:00-22:00] [--url "?game=shoot"]
    python3 tools/metamoa_event.py delete <id>

시각은 한국 시각(+09:00). 공간 키는 METAMOA_KEY, 공간 id 는 METAMOA_SPACE_ID
(.envrc, Actions secret). 소유자 확인이 된 공간만 된다.

메타모아 한도: 제목 30자, 설명 40자(링크 없이), 기간 31일까지, 끝나지 않은 것
다섯 개까지. 주소는 이 사이트 안만.
"""
import argparse, datetime, json, os, sys, urllib.error, urllib.request

SITE = 'https://yonsei-1997.benelog.net/'
# Cloudflare 가 Python-urllib 기본 User-Agent 를 막는다(403, error code 1010)
USER_AGENT = 'campus-1997-metamoa/1.0'
KST = datetime.timezone(datetime.timedelta(hours=9))


def call(method, path, body=None):
    key = os.environ.get('METAMOA_KEY', '').strip()
    space = os.environ.get('METAMOA_SPACE_ID', '').strip()
    if not key or not space:
        sys.exit('METAMOA_KEY · METAMOA_SPACE_ID 가 없음')
    req = urllib.request.Request(
        f'https://metamoa.com/api/space/{space}/events{path}',
        data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None,
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json',
                 'User-Agent': USER_AGENT},
        method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        try:
            return e.code, json.loads(text)
        except ValueError:
            return e.code, {'body': text}


def when(text):
    """「YYYY-MM-DD HH:MM」(한국 시각, 24:00 은 다음 날 0시) → ISO 8601 +09:00"""
    day, _, hm = text.strip().partition(' ')
    h, m = map(int, (hm or '00:00').split(':'))
    t = datetime.datetime.fromisoformat(day).replace(tzinfo=KST) + datetime.timedelta(hours=h, minutes=m)
    return t


def show(e):
    s = datetime.datetime.fromisoformat(e['starts_at'].replace('Z', '+00:00')).astimezone(KST)
    t = datetime.datetime.fromisoformat(e['ends_at'].replace('Z', '+00:00')).astimezone(KST)
    daily = f" 매일 {e['daily_from']}-{e['daily_to']}" if e.get('daily_from') else ''
    print(f"#{e['id']} {e['title']} | {s:%Y-%m-%d %H:%M} ~ {t:%Y-%m-%d %H:%M}{daily}"
          f"{' | ' + e['desc'] if e.get('desc') else ''}{' | ' + e['url'] if e.get('url') else ''}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list')
    a = sub.add_parser('add')
    a.add_argument('--title', required=True)
    a.add_argument('--start', required=True, help='YYYY-MM-DD HH:MM (한국 시각)')
    a.add_argument('--end', required=True, help='YYYY-MM-DD HH:MM (한국 시각)')
    a.add_argument('--desc')
    a.add_argument('--daily', help='매일 열리는 시각 HH:MM-HH:MM')
    a.add_argument('--url', help='이 사이트 안의 주소(전체 주소나 「?game=shoot」 같은 뒷부분)')
    a.add_argument('--dry-run', action='store_true')
    d = sub.add_parser('delete')
    d.add_argument('id', type=int)
    o = ap.parse_args()

    if o.cmd == 'list':
        code, body = call('GET', '')
        if code != 200:
            sys.exit(f'HTTP {code} {body}')
        for e in body.get('events', []):
            show(e)
        if not body.get('events'):
            print('끝나지 않은 이벤트 없음')
        return

    if o.cmd == 'delete':
        code, body = call('DELETE', f'/{o.id}')
        print(f'HTTP {code} {body}')
        if code != 200:
            sys.exit(1)
        return

    start, end = when(o.start), when(o.end)
    errors = []
    if len(o.title) > 30:
        errors.append(f'제목 {len(o.title)}자: 30자 넘음')
    if o.desc and (len(o.desc) > 40 or 'http' in o.desc or 'www.' in o.desc):
        errors.append('설명은 40자까지, 링크 없이')
    if not start < end or end - start > datetime.timedelta(days=31):
        errors.append('끝은 시작 뒤, 31일 안')
    body = {'title': o.title, 'starts_at': start.isoformat(), 'ends_at': end.isoformat()}
    if o.desc:
        body['desc'] = o.desc
    if o.daily:
        body['daily_from'], _, body['daily_to'] = o.daily.partition('-')
    if o.url:
        url = o.url if o.url.startswith('http') else SITE + o.url.lstrip('/')
        if not url.startswith(SITE):
            errors.append(f'주소는 {SITE} 안만')
        body['url'] = url
    if errors:
        sys.exit('\n'.join(errors))
    print(json.dumps(body, ensure_ascii=False))
    if o.dry_run:
        return
    code, res = call('POST', '', body)
    if code != 201:
        sys.exit(f'HTTP {code} {res}')
    print('HTTP 201')
    show(res['event'])


if __name__ == '__main__':
    main()
