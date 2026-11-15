"""대운동장 북쪽 언덕 (서문 남쪽의 숲 언덕, 두 봉우리; #189, reference/고증/4.12_대운동장.md 「북쪽 언덕」).
tools/build_campus.py 가 부른다.

    took, info = fieldhill97.grade(Hn, X, Y, FIXED, halls, fill)     # 심기가 끝난 뒤, 다른 늦은 블록들 다음
    fieldhill97.woods(oval)                                           # 숲 바닥을 칠하고 나무를 채울 자리
    fieldhill97.bare()                                                # 언덕 위 맨땅 길 (땅 지도에 칠함)

Frames: campus metres, x east, y north.  Every absolute height is above sea level (해발), taken up to the working
datum (해발 + tilt: tools/datum.py) where it is read: GRID at its nodes (GRID_X0, GRID_Y0, GRID_D).

What the game had: the base terrain (Copernicus GLO-30 with the buildings opened away, 2.8) as one smooth slope
from 연희동 (44 - 48 m) down to the oval, bare lawn behind the oval's rows of trees: (-450, -113) 48.0 m,
(-415, -80) 45.3 m.  What the 1:5000 survey (2006 · 2024) and the 1997-07-28 scans (26/16 · 26/15, the only pair that
reaches it) have: a wooded hill of two tops, an L open to the south-east.

- the survey's spot heights on the tops: (-450.1, -112.9) 55.57 m (2006) · (-454.5, -114.4) 55.58 m (2024), and
  (-421.0, -81.4) 54.77 m (2006) · (-414.2, -79.8) 55.45 m (2024); the 50 m contour round both in the two editions
  alike, the 45 and 40 m of 2006 round the whole hill
- the scans see the ground at the first top (55.7 m, corr 0.9: 0.1 m off the spot), along the level track cut into
  its north side (53.4 - 53.8 m on five points), on the drive and the lawn of the houses on its north-west shoulder
  (44.8 - 49.8 m), on the bare patches of its east foot (40.1 - 41.6 m) and on the way up out of the oval's north end
  (33.8 m at the oval -> 36.5 -> 39.0 - 39.3 m at 서문's road): 44 points, all within 0.4 m of the surface below; the
  rest is crowns edge to edge
- not as in 1997: the survey's straight 35 and 40 m legs north of the oval's north end (x > -392, y -92 .. -135: the
  halls built there later, FIELD_GONE; the scans have 34.2 - 34.6 m where 2006 has 40) are left out, the scans' points
  used instead.  South-west of the straight 40 / 45 m leg (-507, -113) -> (-463, -150) the 2006 edition has a bowl
  under 40 m north of 학군단 (2024 a walled yard at 37 m): the scans have crowns 60 - 66 m high there (26 - 31 m over that
  bowl, 16 - 22 m over the game's ground), so the bowl may have been cut after 1997: not laid, the game's ground stays

GRID: a minimum-curvature surface (2.5 m, a little tension) through the 2006 contours (1.25 m apart along them), the
two editions' spot heights and the scans' 44 points, at the game's 5 m nodes, centimetres.  Contours rms 0.41 m, spots
0.1 m, the scans' points 0.4 m.  Laid in HILL: drawn along where it meets the game's ground on the north, west and
south-west (연희동's slope north of it stands 3 - 7 m over the survey and is not touched here), to the oval and to 서문's
road on the south and east; eased round it over RING m.  The trees and shrubs stand on whatever ground is under them.
Nothing here draws from build_campus.py's `rng`.
"""
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from scipy import ndimage

import datum

GRID_X0, GRID_Y0, GRID_D = -505.0, -160.0, 5.0      # (the grid's south-west node, spacing: the game's 5 m nodes)
GRID = np.array([[int(v) for v in r.split()] for r in """
3612 3574 3551 3540 3537 3531 3508 3448 3392 3393 3407 3389 3362 3353 3351 3350 3349 3346 3343 3340 3338 3335 3333 3330 3327 3325 3322 3320 3317 3314 3312 3309 3307
3594 3553 3534 3534 3546 3559 3555 3510 3479 3524 3540 3474 3403 3359 3347 3347 3346 3345 3342 3339 3337 3334 3331 3329 3326 3324 3321 3318 3316 3313 3311 3308 3305
3567 3528 3518 3535 3573 3626 3683 3741 3824 3879 3799 3650 3506 3407 3355 3342 3342 3342 3341 3338 3336 3333 3330 3328 3325 3322 3320 3317 3315 3312 3309 3307 3304
3535 3504 3509 3551 3624 3725 3854 4009 4140 4186 4101 3906 3697 3527 3413 3352 3337 3337 3337 3337 3334 3332 3329 3326 3324 3321 3319 3316 3313 3311 3308 3306 3302
3507 3488 3517 3591 3706 3854 4029 4211 4357 4443 4440 4267 3995 3754 3563 3432 3356 3337 3333 3333 3332 3331 3328 3325 3323 3320 3317 3315 3312 3310 3307 3304 3300
3494 3495 3557 3676 3843 4048 4263 4461 4626 4733 4738 4620 4390 4102 3838 3627 3474 3386 3340 3328 3327 3328 3327 3324 3321 3319 3316 3314 3311 3308 3305 3302 3299
3513 3540 3651 3833 4074 4338 4566 4781 4962 5036 4985 4862 4699 4492 4220 3938 3706 3530 3411 3341 3321 3321 3323 3323 3320 3318 3315 3312 3310 3306 3303 3300 3303
3580 3645 3827 4095 4399 4656 4860 5058 5214 5271 5213 5073 4911 4751 4566 4308 4028 3791 3589 3434 3342 3316 3315 3317 3317 3315 3313 3310 3307 3304 3301 3304 3325
3716 3839 4128 4460 4731 4933 5098 5256 5386 5454 5434 5334 5150 4944 4778 4592 4356 4114 3878 3657 3481 3360 3322 3310 3309 3309 3307 3305 3304 3307 3311 3330 3363
3951 4166 4546 4847 5043 5166 5268 5367 5455 5523 5556 5552 5426 5170 4956 4794 4620 4424 4207 3984 3767 3572 3420 3337 3323 3322 3319 3313 3312 3338 3356 3376 3416
4332 4577 4928 5175 5292 5292 5314 5359 5406 5470 5533 5563 5529 5348 5137 4971 4823 4672 4505 4315 4105 3879 3644 3493 3445 3434 3422 3396 3366 3380 3408 3433 3483
4617 4829 5066 5220 5267 5207 5189 5210 5260 5346 5443 5497 5500 5410 5264 5121 4988 4867 4741 4594 4413 4196 3944 3726 3642 3626 3609 3566 3511 3486 3479 3515 3575
4691 4831 4959 5025 5038 5014 5010 5030 5086 5199 5328 5417 5453 5422 5342 5243 5142 5044 4941 4820 4662 4439 4127 3899 3848 3860 3846 3790 3747 3727 3681 3664 3703
4640 4725 4816 4923 4968 4939 4929 4955 4988 5083 5227 5346 5412 5422 5391 5341 5285 5223 5143 5028 4859 4595 4275 4074 4041 4082 4067 3979 3928 3948 3938 3843 3843
4560 4615 4687 4822 4895 4886 4882 4903 4942 5028 5176 5305 5383 5413 5415 5405 5395 5382 5341 5240 5052 4736 4386 4209 4184 4214 4190 4090 4005 4004 3954 3897 3932
4503 4545 4617 4717 4787 4809 4825 4865 4931 5030 5178 5293 5357 5385 5399 5417 5446 5484 5496 5411 5221 4898 4481 4308 4294 4306 4273 4176 4080 4028 3964 3938 3981
4477 4503 4563 4639 4693 4718 4745 4815 4937 5077 5206 5284 5308 5313 5326 5357 5408 5482 5549 5475 5304 5024 4596 4414 4413 4402 4351 4268 4177 4105 4049 4029 4053
4455 4476 4522 4582 4616 4618 4624 4694 4871 5056 5169 5214 5190 5167 5179 5213 5265 5333 5390 5366 5269 5092 4777 4568 4524 4481 4427 4358 4275 4202 4149 4128 4138
4422 4447 4488 4537 4548 4510 4467 4478 4582 4755 4916 4995 4952 4929 4955 4993 5036 5085 5133 5148 5130 5072 4918 4722 4606 4528 4488 4436 4360 4291 4242 4220 4222
4368 4395 4433 4472 4454 4385 4317 4285 4302 4366 4462 4555 4593 4627 4674 4724 4771 4818 4864 4903 4939 4957 4899 4776 4661 4574 4529 4483 4419 4361 4319 4298 4297
4282 4304 4325 4333 4297 4231 4171 4134 4127 4148 4191 4246 4297 4353 4405 4452 4502 4553 4605 4665 4739 4802 4808 4754 4677 4608 4555 4503 4453 4408 4376 4359 4359
4155 4164 4180 4176 4124 4065 4026 4004 4002 4013 4034 4064 4103 4153 4188 4205 4236 4283 4341 4419 4528 4638 4697 4692 4654 4610 4564 4515 4473 4438 4414 4403 4406
4015 4005 4036 4042 3977 3914 3883 3874 3881 3897 3918 3945 3981 4029 4042 4012 4012 4041 4093 4179 4312 4466 4572 4597 4588 4578 4554 4516 4479 4451 4434 4430 4437
""".strip().splitlines()], float) / 100.0
GRID = np.round(GRID + datum.tilt(*np.meshgrid(GRID_X0 + GRID_D * np.arange(GRID.shape[1]),
                                               GRID_Y0 + GRID_D * np.arange(GRID.shape[0]))), 2)
# where GRID is laid (clockwise from the west): the hill inside the line where the surface meets the game's ground
# (north-west and north: behind the houses on its shoulder; south-west: the straight leg over the bowl), 서문's road
# and the oval on the east and south (their nodes stay: FIXED)
HILL = Polygon([(-497.0, -112.0), (-502.0, -104.0), (-501.0, -97.0), (-493.0, -89.0), (-483.0, -83.0), (-472.0, -76.0),
                (-462.0, -69.0), (-450.0, -64.0), (-435.0, -59.0), (-420.0, -58.0), (-405.0, -62.0), (-397.0, -66.0),
                (-388.0, -68.0), (-380.0, -70.0), (-374.0, -76.0), (-360.0, -78.0), (-352.0, -80.0), (-347.0, -88.0),
                (-347.0, -100.0), (-350.0, -108.0), (-352.0, -118.0), (-380.0, -128.0), (-410.0, -142.0), (-432.0, -154.0),
                (-452.0, -162.0), (-456.0, -142.0), (-461.0, -136.0), (-470.0, -130.0), (-480.0, -122.0), (-488.0, -117.0)])
RING = 12.0                       # eased out (harmonic) this far round HILL
HALL_PAD = 7.1                    # the houses' feet that stay (their floors read the nodes round their corners)
# The woods (the scans: crowns edge to edge over the hill and over the bowl north of 학군단 down to its yard and the
# house west of it): the woods' floor painted, trees filled in clear of the ones already there.  Not the grounds of
# the four houses on the north-west shoulder (their lawn and drive: lawn as it is; the houses are not built)
BOWL = Polygon([(-497.0, -112.0), (-488.0, -117.0), (-480.0, -122.0), (-470.0, -130.0), (-461.0, -136.0), (-456.0, -142.0),
                (-454.0, -156.0), (-478.0, -168.0), (-500.0, -176.0), (-516.0, -164.0), (-533.0, -150.0), (-531.0, -118.0),
                (-512.0, -108.0)])
GROUNDS = Polygon([(-512.0, -86.0), (-510.0, -66.0), (-440.0, -64.0), (-443.0, -101.0), (-461.0, -102.0), (-483.0, -101.0),
                   (-498.0, -94.0)])
# the level track cut into the first top's north side (3 m of bare earth from its west end round to the east house's
# yard; 53.4 - 53.8 m), and the footpaths the scans show in the woods: along the ridge from the first top to the
# clearing on the second and on north-east down to the houses by 서문, and one west of the first top
TRACK = [(-488.5, -105.5), (-488.0, -108.5), (-484.0, -110.0), (-476.0, -110.0), (-468.0, -109.0), (-461.0, -106.5),
         (-455.5, -103.0), (-452.0, -98.5)]
TRACK_W = 3.2
PATHS = [[(-455.0, -115.0), (-448.0, -112.5), (-440.0, -107.0), (-433.5, -98.5), (-428.0, -92.0), (-422.0, -85.0),
          (-416.0, -80.0), (-406.0, -75.0), (-395.0, -70.5), (-384.0, -67.0), (-376.5, -63.5)],
         [(-490.0, -127.5), (-482.0, -125.5), (-471.0, -122.5), (-462.0, -118.5), (-455.0, -115.0)]]
PATH_W = 1.4
# the way up out of the oval's north end to 서문's road (trodden bare, east of the scaffold frame), and the open
# scrub east of it down to the road (no crowns in the scans: lawn as it is, no trees)
WAY_UP = [(-360.5, -112.0), (-357.0, -103.0), (-353.5, -96.0), (-351.5, -92.0), (-347.0, -87.0), (-343.0, -80.0), (-340.0, -75.5)]
WAY_UP_W = 2.2
EAST_OPEN = Polygon([(-364.0, -118.0), (-361.0, -104.0), (-357.0, -95.0), (-355.0, -88.0), (-351.0, -80.0), (-345.0, -73.0),
                     (-333.0, -73.0), (-333.0, -122.0)])
TOP2 = Polygon([(-418.5, -78.0), (-413.5, -77.0), (-412.5, -81.5), (-417.5, -83.0)])     # (the clearing on the second top)


def grid_z(x, y):
    """GRID, bilinear (on the working datum)"""
    x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    z = ndimage.map_coordinates(GRID, [(y.ravel() - GRID_Y0) / GRID_D, (x.ravel() - GRID_X0) / GRID_D], order=1, mode='nearest')
    return z.reshape(x.shape) if x.ndim else float(z[0])


def grade(Hn, X, Y, FIXED, halls, fill):
    """GRID in HILL, eased round it (fill: harmonic_fill).  halls: the outlines of the houses that stay.  FIXED nodes
    (the oval, 서문's road and paths) stay.  Returns the nodes set (to be FIXED) and a summary"""
    H0 = Hn.copy()
    stay = shapely.contains_xy(unary_union([h.buffer(HALL_PAD) for h in halls]), X, Y) if halls else np.zeros(X.shape, bool)
    core = shapely.contains_xy(HILL, X, Y) & ~FIXED & ~stay
    Hn[core] = grid_z(X, Y)[core]
    free = shapely.contains_xy(HILL.buffer(RING), X, Y) & ~core & ~FIXED & ~stay
    if free.any():
        fill(free)
    d = Hn - H0
    info = dict(core=int(core.sum()), eased=int(free.sum()),
                moved=(int((np.abs(d) > 0.05).sum()), round(float(d.min()), 1), round(float(d.max()), 1)),
                tops=(round(float(Hn[core].max()), 2),))
    return core | free, info


def bare():
    """the bare earth on the hill: the track, the footpaths and the clearing on the second top"""
    return [LineString(TRACK).buffer(TRACK_W / 2, cap_style='round')] + \
        [LineString(p).buffer(PATH_W / 2, cap_style='flat') for p in PATHS] + [TOP2] + \
        [LineString(WAY_UP).buffer(WAY_UP_W / 2, cap_style='flat')]


def woods(oval, halls=()):
    """where the woods' floor is painted and the trees are filled in: HILL and BOWL off the oval (3 m), the houses'
    grounds, the open scrub at the east foot, the bare earth (1 m) and the houses that stay"""
    w = unary_union([HILL, BOWL]).difference(unary_union([oval.buffer(3.0), GROUNDS, EAST_OPEN] + [g.buffer(1.0) for g in bare()] +
                                                         [h.buffer(3.0) for h in halls]))
    return [g for g in (w.geoms if hasattr(w, 'geoms') else [w]) if g.geom_type == 'Polygon' and g.area > 30.0]
