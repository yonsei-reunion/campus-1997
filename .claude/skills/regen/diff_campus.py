"""다시 만든 campus.json 을 전의 것과 견준다: 나무 · 관목 · 소품 · 차는 목록의 자리(인덱스)로, 나머지는 키마다 달라진 잎의 수로.

  python3 .claude/skills/regen/diff_campus.py [--old <기준>] [--new <새것>] [--near x,y,r ...] [--show 15]

  --old   기준(기본 HEAD). 셋 가운데 하나
          - git 리비전: git show <리비전>:web/public/data/campus.json
          - campus.json 파일
          - Y97_WORK_DUMP 폴더(campus.json 과 terrain_*.npy: 작업면의 결과)
  --new   새것(기본 web/public/data/campus.json). 파일이나 Y97_WORK_DUMP 폴더
  --near  고친 곳: 가운데 x,y 와 반지름 r(m). 여러 번 줄 수 있다. 전 · 후 자리가 모두 그 밖인 변화를 「먼 변화」로 센다
  --show  먼 변화를 목록마다 몇 줄까지 보일지

- 웹은 나무의 모델을 목록 순서로 고르므로(web/src/world.js Forest), 집합이 아니라 같은 인덱스끼리 견준다.
  가운데에서 하나가 빠지거나 끼면 그 뒤 인덱스가 모두 「바뀜」으로 나온다: 그것이 찾으려는 흔들림이다.
- 두 쪽이 모두 폴더면 terrain_*.npy 도 견준다(달라진 마디 수와 가장 큰 차).
- 해발인 campus.json 과 작업면인 덤프를 섞어 견주지 않는다(높이가 모두 다르게 나옴).
--near 를 주었고 먼 변화가 있으면 종료 코드 1.
"""
import argparse
import glob
import json
import math
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
REL = 'web/public/data/campus.json'
KEYS = ('trees', 'shrubs', 'props', 'cars')


def load(src):
    if os.path.isdir(src):
        return json.load(open(os.path.join(src, 'campus.json')))
    if os.path.exists(src):
        return json.load(open(src))
    return json.loads(subprocess.check_output(['git', '-C', ROOT, 'show', '%s:%s' % (src, REL)]))


def leaves(v, out):
    if isinstance(v, dict):
        for k in sorted(v):
            out.append(('k', k))
            leaves(v[k], out)
    elif isinstance(v, list):
        out.append(('n', len(v)))
        for x in v:
            leaves(x, out)
    else:
        out.append(v)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--old', default='HEAD')
    ap.add_argument('--new', default=os.path.join(ROOT, REL))
    ap.add_argument('--near', action='append', default=[])
    ap.add_argument('--show', type=int, default=15)
    argv, raw = [], sys.argv[1:]
    while raw:                                   # (-76,95,60 처럼 음수로 시작하는 값을 옵션으로 읽지 않게)
        v = raw.pop(0)
        argv.append(v + '=' + raw.pop(0) if v == '--near' and raw else v)
    a = ap.parse_args(argv)
    near = [tuple(float(v) for v in s.split(',')) for s in a.near]
    old, new = load(a.old), load(a.new)

    def far(e):
        return not any(math.hypot(e[1] - x, e[2] - y) <= r for x, y, r in near)

    bad = 0
    for k in KEYS:
        o, n = old.get(k, []), new.get(k, [])
        m = min(len(o), len(n))
        rows = [(i, o[i], n[i]) for i in range(m) if o[i] != n[i]]
        rows += [(i, o[i], None) for i in range(m, len(o))] + [(i, None, n[i]) for i in range(m, len(n))]
        kind = sum(1 for _, p, q in rows if p and q and p[0] != q[0])
        moved = sum(1 for _, p, q in rows if p and q and p[0] == q[0] and p[1:3] != q[1:3])
        other = sum(1 for _, p, q in rows if p and q and p[0] == q[0] and p[1:3] == q[1:3])
        print('%-6s %d -> %d   같은 인덱스에서 바뀜 %d (종류 %d, 자리 %d, 그 밖의 값 %d), 끝에서 빠짐 %d, 끝에 더함 %d'
              % (k, len(o), len(n), kind + moved + other, kind, moved, other, max(len(o) - m, 0), max(len(n) - m, 0)))
        if not near:
            continue
        fr = [(i, p, q) for i, p, q in rows if all(far(e) for e in (p, q) if e)]
        bad += len(fr)
        print('       먼 변화 %d' % len(fr))
        for i, p, q in fr[:a.show]:
            print('         [%d] %s -> %s' % (i, json.dumps(p, ensure_ascii=False), json.dumps(q, ensure_ascii=False)))
        if len(fr) > a.show:
            print('         … %d 줄 더' % (len(fr) - a.show))
    print('그 밖의 키(달라진 것만)')
    same = 0
    for k in sorted(set(old) | set(new)):
        if k in KEYS:
            continue
        if k not in old or k not in new:
            print('  %-20s %s' % (k, '새로 생김' if k not in old else '없어짐'))
            continue
        if old[k] == new[k]:
            same += 1
            continue
        lo, ln = leaves(old[k], []), leaves(new[k], [])
        size = '수 %d -> %d, ' % (len(old[k]), len(new[k])) if isinstance(old[k], (list, dict)) and len(old[k]) != len(new[k]) else ''
        diff = '잎 %d -> %d' % (len(lo), len(ln)) if len(lo) != len(ln) else '잎 %d 가운데 %d 다름' % (len(lo), sum(1 for p, q in zip(lo, ln) if p != q))
        print('  %-20s %s%s' % (k, size, diff))
    print('  (같은 키 %d)' % same)
    if os.path.isdir(a.old) and os.path.isdir(a.new):
        import numpy as np
        for f in sorted(glob.glob(os.path.join(a.old, 'terrain_*.npy'))):
            g = os.path.join(a.new, os.path.basename(f))
            if not os.path.exists(g):
                print('  %s: 새것에 없음' % os.path.basename(f))
                continue
            p, q = np.load(f), np.load(g)
            if p.shape != q.shape:
                print('  %s: 크기 %s -> %s' % (os.path.basename(f), p.shape, q.shape))
            else:
                d = np.abs(p.astype(float) - q)
                print('  %s: 달라진 마디 %d, 가장 큰 차 %.3f m' % (os.path.basename(f), int((d > 0).sum()), float(d.max())))
    return 1 if near and bad else 0


if __name__ == '__main__':
    sys.exit(main())
