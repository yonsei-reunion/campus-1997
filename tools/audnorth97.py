"""대강당 북쪽 날개 둘레의 땅 (reference/고증/4.5.1 「북쪽 날개 둘레」).

1997년 7월 항공사진 원본 스캔에서 대강당 앞 윗단의 밝은 마당은 북쪽 날개의 서쪽 벽까지,
날개 북쪽으로는 벽에서 5 ~ 6 m 띠(차 한 대가 섬)까지 한 높이로 이어진다(날개 서쪽 · 북쪽 열두 점이 윗단과 0.2 m 안,
2006년 측량의 면도 0.3 m 안). 게임은 5 m 격자가 그 자리에서 3 ~ 4 m 꺼져 있었고 날개가 그 땅에 섰다. YARD 의 마디를
윗단 높이로 고르고, 둘레 RING m 를 용재관의 평평한 땅 · 윗단 · 동쪽 마당 사이에 매끈하게 잇는다. 북쪽 날개는 땅을 읽어
서므로(blender/landmarks.py auditorium 의 wings) 다음 landmarks 빌드에 윗단 위 두 층으로 선다.
윗단 북쪽 끝(y 95.5) 너머의 길 · 잔디 섬(1997년의 모습은 4.5.1 「남은 한계」)은 건드리지 않는다: NORTH_KEEP.

build_campus.py 가 무작위 심기 뒤에 부른다(나무 · 관목 · 차는 땅을 읽은 뒤). 높이는 그 자리의 땅(작업면)을 받아 쓴다.
"""
import numpy as np
import shapely
from shapely.geometry import Polygon

# 윗단이 이어지는 땅: 윗단의 동쪽 가(x 50) ~ 날개 서쪽 벽, 날개 밑, 날개 북쪽 띠(1997년 수관의 남쪽 가까지), 날개 동쪽 벽 앞 2.5 m.
# 남쪽 변은 대강당 북쪽 벽 안쪽(건물 밑)
YARD = Polygon([(50.0, 57.0), (50.0, 93.5), (54.5, 93.5), (58.0, 87.5), (63.0, 83.5), (68.0, 81.5), (86.0, 79.5), (86.0, 69.0),
                (83.0, 54.5), (59.0, 60.0)])
RING = 12.0
NORTH_KEEP = (57.0, 96.0)           # x 이 값보다 서쪽이고 y 이 값보다 북쪽인 마디는 그대로(윗단 북쪽 끝 너머의 길 · 섬)
# 포장: 윗단의 포장이 날개 서쪽 벽과 날개 북쪽 띠까지(윗단 쪽은 이미 포장된 곳과 겹침, 건물 밑은 build_campus.py 가 뺌).
# 날개 동쪽 마당(사진: 쌓아 둔 것들이 놓인 맨땅)은 그대로
PAVE = Polygon([(48.0, 57.5), (48.0, 93.5), (54.0, 93.5), (57.5, 87.5), (62.5, 83.5), (68.0, 81.0), (84.5, 79.2), (84.5, 71.0),
                (83.2, 70.2), (79.0, 56.0), (59.5, 60.0)])



def grade(Hn, X, Y, FIXED, keep, bank, fill, z):
    """YARD 의 마디를 z(윗단의 작업면 높이)로, 둘레 RING m 를 매끈하게. keep: 건드리지 않을 마디(건물 발치 · 용재관의 평평한
    땅), bank: 앞 블록이 놓았지만 다시 이어도 되는 마디(용재관 둘레 비탈). 돌려주는 것: (정한 마디, 요약)"""
    zone = shapely.contains_xy(YARD, X, Y)
    ring = shapely.contains_xy(YARD.buffer(RING), X, Y) & ~zone & ~keep & ~((X < NORTH_KEEP[0]) & (Y > NORTH_KEEP[1]))
    free = ring & (~FIXED | bank)
    h0 = Hn.copy()
    Hn[zone] = z
    if free.any():
        fill(free)
    d = Hn - h0
    return zone | free, dict(z=round(float(z), 2), nodes=int(zone.sum()), lo=round(float(d[zone].min()), 2),
                             hi=round(float(d[zone].max()), 2), ring=int(free.sum()),
                             ring_lo=round(float(d[free].min()), 2) if free.any() else 0.0,
                             ring_hi=round(float(d[free].max()), 2) if free.any() else 0.0)
