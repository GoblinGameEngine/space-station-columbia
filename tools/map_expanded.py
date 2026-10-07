#!/usr/bin/env python3
"""
map_expanded.py -- the EXPANDED station (radius 3 km, 8 km wall to wall): the same
settlements, water and roads as map_preview.py (the 500 m ring), laid out on the bigger
cylinder.  A draft for the user's approval; map_preview.py stays the authority until then.

  round the ring   every community sits 6x further round (18.85 km circumference): the extra
                   ground between them is farmland; each keeps its own street layout
  along the axis   north (the Marlowe end, -x) to south: a 1 km sea at the end-cap cliffs, 1 km of
                   new farmland, the old land (its banks 500 m further out), the Kettle River and
                   Lake Tamsin 1 km wider, the old land, 1 km of new farmland, a 1 km sea
  water            every lengthwise creek runs on through the new farmland into its sea; new
                   cross-creeks join neighbouring creeks round the ring; the oxbow ponds that sat
                   beside the old channel are gone (they'd be in the widened river)
  roads            highways, county roads and the railway follow the communities out; section
                   roads on a 1-mile grid; the river crossings are new ~1 km bridges

(map_preview.py's own notes follow.)
2D overhead preview of the station ring's settlement /
water / road layout, generated straight from the research rules
(research/generator_rules.md) rather than from the running game.

Why a standalone script: the in-engine FlatMapRenderer tried to rasterise
the fully built 3D world and locked up the laptop (~7GB). A layout map only
needs the layout *rules*, so this computes them directly -- deterministic
(fixed seed), no Godot, a few hundred MB.

The ring is drawn unrolled: horizontal = arc length s (0..18,850 m, the left
and right edges join), vertical = axial x (-4,000 m north wall at the top,
+4,000 m south wall at the bottom). 1 px = 2 m.

Usage:  python3 tools/map_expanded.py OUT.png      (needs pillow + numpy)
"""

import math
import os
import random
import sys

import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "settlegen"))
import centers as CT  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ------------------------------------------------------------------ geometry
R = 10000.0                  # 20 km across since 2026-10-06 (was 3 km radius): positions round the ring scale with it
C = 2 * math.pi * R          # 62,832 m circumference
W = 22400.0                  # wall to wall: each landmass 2.5 km wider, each sea ~5.5 km (room for islands 1.5 km clear)
HW = W / 2
PX = 4.0                     # metres per raster pixel (everything else is in metres; 4 m keeps the rasters in memory)
KS = R / 3000.0              # a position round the ring on the 3 km ring -> this one (the angle is kept)
LAND_GROW = 2500.0           # each landmass this much wider (the user, 2026-10-06: "2.5km to each landmass's width")
K = 1.0 / PX
CW, WH = int(round(C / PX)), int(W / PX)
OFFS = (-C, 0.0, C)          # draw every primitive three times so the seam wraps
OLD_R = 500.0
SS = R / OLD_R               # an old-map arc length -> the expanded ring's
WIDEN = 500.0                # each bank of the river / lake moves out this far (1 km wider)
SEA = 5500.0                 # the end-cap seas (mean: the coasts wander round COAST_MEAN)
SHORE = HW - SEA             # |x| of the land's edge at each sea
SHORE3 = 3000.0              # ... on the 3 km ring's frame (what's set back from it, through XS)

# River harmonic stack -- identical to TerrainHeight.gd (generator_rules §10)
A1, A2, A3 = 150.0, 45.0, 25.0
PHI1, PHI2, PHI3, PHI4 = math.pi / 2, -math.pi / 4, -math.pi / 4, 0.0
CH_HALF = 250.0              # a 500 m river ...
OLD_BANK = 22.5 + WIDEN      # ... in a wide basin: marsh and meadow out to the 1 km-widened banks
BASIN = OLD_BANK - CH_HALF


def XS(x):
    """An across-the-ring position on the 3 km ring's land -> this one: the river and its basin stay as they were, the
    land beyond the banks stretches out to the new coasts (every town, road and creek spreads into the new land)."""
    a = abs(x)
    if a <= OLD_BANK:
        return x
    return math.copysign(OLD_BANK + (a - OLD_BANK) * XK, x)


def XS_inv(x):
    a = abs(x)
    if a <= OLD_BANK:
        return x
    return math.copysign(OLD_BANK + (a - OLD_BANK) / XK, x)


XK = (3100.0 + LAND_GROW - OLD_BANK) / (3100.0 - OLD_BANK)     # (the old mean coast, 3.1 km, moves 2.5 km out)
# Lake per §10: 1,000 m x 300 m, necked 100-150 m at both ends
# Lake Tamsin, expanded north: the south (Harrow Falls) shore stays 650 m off the centreline; the new
# north shore reaches ~1.7 km out; ~2.6 km long round the ring with long smooth necks
LAKE_S, LAKE_HALF_LEN, LAKE_NECK = math.pi / 4 * R, 1400.0, 800.0
LAKE_HW_S, LAKE_HW_N = 150.0 + WIDEN, 1700.0
H_BLUFF, Z1 = 18.0, 10.0     # §16

rng = random.Random(1234)


def rx(s):
    th = np.asarray(s, dtype=np.float64) / R
    env = A1 * (1 + 0.3 * np.sin(2 * th + PHI4))
    return env * np.sin(6 * th + PHI1) + A2 * np.sin(13 * th + PHI2) + A3 * np.sin(th + PHI3)


def rxf(s):
    return float(rx(s))


def rcx(s):
    """River centreline blended into the lake's centre where the lake is."""
    return float(lake_params(s)[1])


def wrap_d(ds):
    return (ds + C / 2) % C - C / 2


def lake_params(s):
    """-> (t taper 0..1, centre x, half-width toward -x, half-width toward +x)."""
    s = np.asarray(s, dtype=np.float64)
    d = wrap_d(s - LAKE_S)
    a = np.abs(d)
    t = np.clip((LAKE_HALF_LEN - a) / LAKE_NECK, 0, 1)
    t = t * t * (3 - 2 * t)
    cx = rx(s) * (1 - t)
    # one irregular shore (-x, the new north shore: coves and points), one cleaner bluff shore (+x) -- §16
    hw_top = CH_HALF + (LAKE_HW_N - CH_HALF + 70 * np.sin(d / 230.0) + 35 * np.sin(d / 97.0 + 1.3)
                        + 12 * np.sin(d / 31.0)) * t
    hw_bot = CH_HALF + (LAKE_HW_S - CH_HALF + 6 * np.sin(d / 63.0 + 0.4)) * t
    return t, cx, hw_top, hw_bot


def water_edges(s):
    """(top edge x, bottom edge x) of the river/lake at s."""
    t, cx, ht, hb = lake_params(s)
    r = cx                      # == rx(s) outside the lake
    top = np.where(t > 0, np.minimum(r - CH_HALF, cx - ht), r - CH_HALF)
    bot = np.where(t > 0, np.maximum(r + CH_HALF, cx + hb), r + CH_HALF)
    return top, bot


# ------------------------------------------------------------------ the sea coasts
# Natural coasts: headlands (rocky cliffs) alternating with crenulate bays (sandy beaches) -- see
# research/coastal_communities/flora_and_coast.md.  |x| of the waterline = COAST_MEAN + a(s); where a(s)
# stands proud it's a headland.  Each coastal community straightens its own stretch (SITES).
COAST_MEAN = XS(3100.0)        # 5.6 km
TAU = 2 * math.pi


def coast_amp(s, sg):
    s = np.asarray(s, dtype=np.float64)
    ph = 0.0 if sg < 0 else 2.1
    # incommensurate bends at several scales: big bays, points, coves, a ragged edge
    return (140 * np.sin(TAU * s / 2600 + ph) + 95 * np.sin(TAU * s / 1130 + 2 * ph + 0.7)
            + 55 * np.sin(TAU * s / 610 + ph + 2.0) + 24 * np.sin(TAU * s / 233 + 3 * ph)
            + 9 * np.sin(TAU * s / 71 + ph + 1.1))


# old town anchors (s0, north?) -- a creek that belongs to a town moves with it
_TOWN_S0 = [(395.0, False), (2130.0, False), (1500.0, True), (2150.0, True), (1050.0, False), (2820.0, False),
            (1250.0, True), (1500.0, False), (650.0, True), (2580.0, True), (2955.0, True)]


def _creek_shift(wps, pond):
    north = wps[0][1] < 0
    s_end = pond[0] if pond else wps[-1][0]
    near = [t for t in _TOWN_S0 if t[1] == north and abs((s_end - t[0] + OLD_R * math.pi) % (2 * OLD_R * math.pi)
                                                         - OLD_R * math.pi) < 450]
    return near[0][0] * (SS - 1) if near else wps[0][0] * (SS - 1)


HAVEN_S = 120 + _creek_shift([(120, -1380), (345, -150)], None) + 45      # Lost Creek's mouth
# name, side (-1 north sea, +1 south sea), s centre, half-length along the coast, waterline |x|,
# shore-road set-back from the waterline
SITES = [
    ("Port Carrow", -1, 10900.0 * KS, 780.0, XS(3200.0), 30.0),
    ("Tern Harbor", -1, 5600.0 * KS, 380.0, XS(3130.0), 110.0),
    ("Brightwater", -1, 16300.0 * KS, 520.0, XS(3150.0), 110.0),
    ("Haven Point", -1, HAVEN_S, 420.0, XS(3130.0), 110.0),
    ("Solana Point", 1, 10600.0 * KS, 820.0, XS(3200.0), 110.0),
    ("Pelican Cove", 1, 14700.0 * KS, 380.0, XS(3130.0), 110.0),
    ("Playa Verde", 1, 4300.0 * KS, 480.0, XS(3150.0), 110.0),
    ("Oceanview", 1, 18000.0 * KS, 580.0, XS(3150.0), 110.0),
]
SITE = {st[0]: st for st in SITES}
BLEND = 700.0


def site_weight(s, sg):
    """0 inside a coastal site's straightened stretch, 1 on the natural coast; and the site's line and
    road set-back blended in."""
    s = np.asarray(s, dtype=np.float64)
    w = np.ones_like(s)
    line = np.zeros_like(s)
    off = np.zeros_like(s)
    for name, side, sc, half, ln, ro in SITES:
        if side != sg:
            continue
        d = np.abs(wrap_d(s - sc))
        t = np.clip((d - half) / BLEND, 0, 1)
        t = t * t * (3 - 2 * t)
        inside = t < w
        line = np.where(inside, ln, line)
        off = np.where(inside, ro, off)
        w = np.minimum(w, t)
    return w, line, off


def coast(s, sg):
    """|x| of the sea's waterline at s on side sg."""
    w, line, _ = site_weight(s, sg)
    return (COAST_MEAN + coast_amp(s, sg)) * w + line * (1 - w)


def coastf(s, sg):
    return float(coast(s, sg))


def is_sea(s, x):
    sg = -1 if x < 0 else 1
    if abs(x) <= coastf(s, sg):
        return False
    if abs(x) > 7000.0 and "ISL" in globals():        # (the islands)
        i, j = idx(s, x)
        return not ISL[j, i]
    return True


def rail_x3(s):
    """the railway on the 3 km ring's frame (the same angle round the ring)"""
    return 960.0 + WIDEN + 60.0 * math.sin(2 * s / R + 1.0)


HF_RAIL_S = 395.0 * SS          # Harrow Falls (a river town, not stretched): the railway keeps its old line past it


def rail_x(s):
    # stretched with the land, except past Harrow Falls, where it bends back (over 3 km) to run along the
    # town's edge as it did (stretched, it stood 1.4 km off and the town lost its station)
    d = abs(float(wrap_d(s - HF_RAIL_S)))
    t = min(1.0, max(0.0, (4500.0 - d) / 3000.0))
    w = t * t * (3 - 2 * t)
    return XS(rail_x3(s)) * (1 - w) + rail_x3(s) * w


def P(s, x):
    """An old-map point (the 3.14 km ring) on the expanded one: 6x further round the ring, and
    500 m further from the river on its own side."""
    ns = s * SS
    return (ns, XS(x + (-WIDEN if x < float(rx(ns)) else WIDEN)))


def fk(m):
    """A filter radius in metres -> whole pixels."""
    return max(1, int(round(m * K)))


def _shift(a, k, axis):
    out = np.zeros_like(a)
    if axis == 0:
        if k > 0:
            out[k:] = a[:-k]
        else:
            out[:k] = a[-k:]
    else:
        if k > 0:
            out[:, k:] = a[:, :-k]
        else:
            out[:, :k] = a[:, -k:]
    return out


def dilate(m, r):
    """Square dilation of a bool mask by r px (separable, doubling steps: fast at any size)."""
    out = m.copy()
    for axis in (0, 1):
        done, step = 0, 1
        while done < r:
            k = min(step, r - done)
            out = out | _shift(out, k, axis) | _shift(out, -k, axis)
            done += k
            step *= 2
    return out


def erode(m, r):
    return ~dilate(~m, r)


# ------------------------------------------------------------------ helpers
def densify(pts, step=4.0):
    out = []
    for (a, b) in zip(pts, pts[1:]):
        n = max(1, int(math.dist(a, b) / step))
        for k in range(n):
            f = k / n
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    out.append(pts[-1])
    return out


def chaikin(pts, it=3, closed=False):
    for _ in range(it):
        new = [] if closed else [pts[0]]
        rng_ = range(len(pts)) if closed else range(len(pts) - 1)
        for i in rng_:
            a, b = pts[i], pts[(i + 1) % len(pts)]
            new.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            new.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        if not closed:
            new.append(pts[-1])
        pts = new
    return pts


def meander(pts, amp=14.0, seed=0.0):
    """Perpendicular sine wobble along a densified polyline (creeks)."""
    d = densify(pts, 4.0)
    out, acc = [], 0.0
    for i, p in enumerate(d):
        if i:
            acc += math.dist(d[i - 1], p)
        a = d[max(0, i - 1)]
        b = d[min(len(d) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        fade = min(1.0, acc / 60.0, (len(d) - i) * 4.0 / 60.0)
        o = fade * (amp * math.sin(acc / 47.0 + seed) + 0.45 * amp * math.sin(acc / 19.0 + 2 * seed))
        out.append((p[0] + nx * o, p[1] + ny * o))
    return out


def circle(s, x, r, n=14):
    return [(s + r * math.cos(2 * math.pi * k / n), x + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def ellipse(s, x, a, b, n=28, rot=0.0):
    c, sn = math.cos(rot), math.sin(rot)
    pts = []
    for k in range(n):
        t = 2 * math.pi * k / n
        u, v = a * math.cos(t), b * math.sin(t)
        pts.append((s + u * c - v * sn, x + u * sn + v * c))
    return pts


def hull(points):
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def grow(poly, d):
    cs = sum(p[0] for p in poly) / len(poly)
    cx = sum(p[1] for p in poly) / len(poly)
    out = []
    for p in poly:
        vx, vy = p[0] - cs, p[1] - cx
        L = math.hypot(vx, vy) or 1.0
        out.append((p[0] + vx / L * d, p[1] + vy / L * d))
    return out


def L(p):  # (s, x) -> layer pixel
    return (p[0] * K, (p[1] + HW) * K)


def draw_poly(dr, poly, **kw):
    for o in OFFS:
        dr.polygon([((p[0] + o) * K, (p[1] + HW) * K) for p in poly], **kw)


def draw_line(dr, pts, width=1, **kw):
    w = max(1, int(round(width * K)))
    for o in OFFS:
        dr.line([((p[0] + o) * K, (p[1] + HW) * K) for p in pts], width=w, **kw)


def draw_ellipse(dr, s, x, r, **kw):
    for o in OFFS:
        dr.ellipse([(s + o - r) * K, (x + HW - r) * K, (s + o + r) * K, (x + HW + r) * K], **kw)


def idx(s, x):
    return int(math.floor((s % C) * K)) % CW, min(WH - 1, max(0, int(math.floor((x + HW) * K))))


# ------------------------------------------------------------------ water
S = ((np.arange(CW) + 0.5) * PX)[None, :]
X = ((np.arange(WH) + 0.5) * PX - HW)[:, None].astype(np.float32)
RX = rx(S).astype(np.float32)
T_L, CX_L, HT_L, HB_L = [a.astype(np.float32) for a in lake_params(S)]
TOP_E, BOT_E = [a.astype(np.float32) for a in water_edges(S)]
S = S.astype(np.float32)

WCAT = np.zeros((WH, CW), np.uint8)             # 1 river 2 lake 3 creek 4 pond 5 ditch 6 sea
WCAT[np.abs(X - CX_L) < CH_HALF] = 1
WCAT[(T_L > 0) & (X > CX_L - HT_L) & (X < CX_L + HB_L)] = 2
COAST_N = coast(S, -1).astype(np.float32)                       # |x| of each sea's waterline, per column
COAST_S = coast(S, 1).astype(np.float32)
WCAT[(X < -COAST_N) | (X > COAST_S)] = 6                          # the end-cap seas

# The sea islands (the user, 2026-10-06: "islands big enough to support towns the size of Calder in the seas, three
# each, staggered by none closer than 1.5km from the end cap or mainland").  Each is an oval ~3.4 x 2.1 km (Calder's
# plan is 1.8 x 1.8 km) with a wandering shore that only ever cuts in, so the clearances below are hard limits.
# Left wild for now -- meadow, woods and beaches, no fields or roads -- for the towns to come.
ISLAND_CLEAR = 1500.0
ISLANDS = [  # name, side, s centre, x centre, half-length round the ring, half-width across
    ("Gannet Island", -1, 0.05 * C, -8560.0, 1700.0, 1050.0),
    ("Rook Island", -1, 0.383 * C, -8560.0, 1700.0, 1050.0),
    ("Thistle Island", -1, 0.717 * C, -8560.0, 1700.0, 1050.0),
    ("Isla Serena", 1, 0.217 * C, 8560.0, 1700.0, 1050.0),
    ("Isla Palmar", 1, 0.55 * C, 8560.0, 1700.0, 1050.0),
    ("Cayo Luna", 1, 0.883 * C, 8560.0, 1700.0, 1050.0),
]


def _island_masks():
    """ISL: on an island; ISL_D: metres inland of its shore (an estimate: the oval's own fraction of its half-width)."""
    isl = np.zeros((WH, CW), bool)
    d_in = np.zeros((WH, CW), np.float32)
    for k_, (nm, sg, sc, xc, hs, hx) in enumerate(ISLANDS):
        i0_, i1_ = int((sc - hs - 50) / PX), int((sc + hs + 50) / PX) + 1
        j0_, j1_ = max(0, int((xc - hx - 50 + HW) / PX)), min(WH, int((xc + hx + 50 + HW) / PX) + 1)
        ii_ = np.arange(i0_, i1_) % CW
        ds = ((np.arange(i0_, i1_) + 0.5) * PX - sc)[None, :] / hs
        dx = ((np.arange(j0_, j1_) + 0.5) * PX - HW - xc)[:, None] / hx
        r = np.hypot(ds, dx)
        a = np.arctan2(dx, ds)
        ph = 1.7 * k_
        wob = (0.5 + 0.5 * (0.45 * np.sin(2 * a + ph) + 0.3 * np.sin(5 * a + 2 * ph) + 0.15 * np.sin(11 * a + ph + 1)
                            + 0.1 * np.sin(23 * a + 3 * ph)))          # 0..1
        rn = r / (0.84 + 0.16 * wob)                                     # (the shore cuts in up to 16 %, never out)
        inside = rn < 1.0
        isl[j0_:j1_, ii_] |= inside
        d_in[j0_:j1_, ii_] = np.maximum(d_in[j0_:j1_, ii_], np.where(inside, (1.0 - rn) * hx, 0.0))
        # the user's clearances: 1.5 km from the mainland's waterline and from the end cap
        jj_, iq = np.nonzero(inside)
        xs_ = (j0_ + jj_ + 0.5) * PX - HW
        ss_ = ((i0_ + iq + 0.5) * PX) % C
        gap_cap = HW - np.abs(xs_).max()
        gap_coast = (np.abs(xs_) - coast(ss_, sg)).min()
        assert gap_cap >= ISLAND_CLEAR and gap_coast >= ISLAND_CLEAR, (nm, gap_cap, gap_coast)
        print(f"island {nm}: {inside.sum() * PX * PX / 1e6:.1f} km2, {gap_coast:.0f} m off the mainland, "
              f"{gap_cap:.0f} m off the cap", file=sys.stderr)
    return isl, d_in


ISL, ISL_D = _island_masks()
WCAT[ISL] = 0

# The two great rivers joining the seas to the Kettle (the Lake Erie pattern: the Maumee from the
# north, the Miami from the south into Lake Tamsin's western basin).  Centrelines from the sea to
# the Kettle / the lake, meandering; RIVER_HALF wide each side, in a basin of their own.
RIVER_HALF = 130.0
RIVER_BASIN = 130.0
GREAT_RIVERS = [
    ("Maumee River", [(6450 * KS, -COAST_MEAN - 250)] + [(a * KS, XS(b)) for a, b in ((6300, -2850), (6620, -2450),
                      (6360, -2050), (6720, -1650), (6480, -1250), (6800, -850))] + [(6700 * KS, rxf(6700 * KS))]),
    ("Miami River", [(820 * KS, COAST_MEAN + 250)] + [(a * KS, XS(b)) for a, b in ((1000, 2850), (720, 2450), (1060, 2050),
                     (820, 1650), (1250, 1250), (1330, 700), (1370, 250))]),
]
RIVER_PATHS = []
_ri = Image.new("L", (CW, WH), 0)
_rd = ImageDraw.Draw(_ri)
for _nm, _wp in GREAT_RIVERS:
    _pth = meander(chaikin(_wp, 3), amp=45.0, seed=len(_nm))
    RIVER_PATHS.append((_nm, _pth))
    draw_line(_rd, _pth, fill=1, width=2 * RIVER_HALF, joint="curve")
    for _q in _pth[::3]:
        draw_ellipse(_rd, _q[0], _q[1], RIVER_HALF, fill=1)          # no hairline gaps at the bends
RIVMASK = np.array(_ri) > 0
WCAT[RIVMASK & (WCAT == 0)] = 1

# Named tributary creeks: outer farmland -> (pond) -> river.  2-4 per stretch (§10)
CREEKS_OLD = [
    # name, waypoints (s, x) from the wall end toward the river, pond (s, x, long, half-w) or None
    ("Lost Creek", [(120, -1380), (200, -1150), (330, -900), (300, -560), (345, -150)], None),
    ("Mill Creek", [(980, -1300), (1060, -1080), (1120, -820), (1215, -600), (1238, -330)], (1238, -330, 110, 30)),
    ("Willow Run", [(1760, -1420), (1880, -1180), (1800, -900), (1870, -640), (1860, -470)], (1865, -420, 90, 26)),
    ("Tanner Creek", [(2330, -1250), (2440, -1060), (2390, -850), (2370, -700)], (2360, -520, 120, 34)),
    ("Brush Creek", [(2880, -1400), (2800, -1160), (2760, -930), (2680, -720), (2700, -520)], None),
    ("Cole Creek", [(700, 1350), (790, 1180), (860, 960), (830, 640)], None),
    ("Deer Creek", [(1420, 1400), (1330, 1220), (1290, 980), (1330, 760)], (1322, 500, 95, 28)),
    ("Sauk Creek", [(1780, 1260), (1840, 1100), (1880, 900), (1880, 800)], (1885, 640, 130, 36)),
    ("Heron Creek", [(3030, 1300), (3100, 1130), (3060, 880), (3065, 700)], (3055, 480, 80, 24)),
]


def _expand_creek(name, wps, pond):
    """An old creek on the expanded map: moved round the ring as a piece (its shape kept) -- with
    its town if it has one within 450 m, else 6x round like the rest -- its bank side 500 m out, and
    run on from its old head through the new farmland into the sea."""
    s_c = wps[0][0]
    north = wps[0][1] < 0
    dx = -WIDEN if north else WIDEN
    sg = -1 if north else 1
    shift = _creek_shift(wps, pond)
    pts = [(s + shift, XS(x + dx)) for s, x in wps]
    head = pts[0]
    lead = [(head[0] + 45, sg * (coastf(head[0] + 45, sg) + 80)), (head[0] - 70, sg * XS(SHORE3 - 330)),
            (head[0] + 55, sg * XS(SHORE3 - 700)), (head[0] - 20, sg * (abs(head[1]) + 150))]
    if pond:
        pond = (pond[0] + shift, XS(pond[1] + dx), pond[2], pond[3])
    return (name, lead + pts, pond)


CREEKS = [_expand_creek(*c) for c in CREEKS_OLD]
# Minor unnamed drainage spurs (§10: 1-2 per stretch, dead-end, pure crossing-density filler):
# (creek index, fraction along the creek where it forks, direction (ds, dx), length)
SPURS = [(0, 0.35, (1, -0.4), 220), (2, 0.3, (-1, -0.3), 260), (4, 0.4, (1, -0.5), 200),
         (5, 0.3, (-1, 0.5), 240), (7, 0.25, (1, 0.6), 200), (8, 0.35, (-1, 0.4), 180),
         (3, 0.5, (1, 0.2), 160)]
OXBOWS = []    # Oxbow Lake, Horseshoe Slough and Crane Pond sat beside the old channel: now under the river

creek_img = Image.new("L", (CW, WH), 0)            # value = creek id (1-based)
cdr = ImageDraw.Draw(creek_img)
CREEK_PATHS = []
for ci, (name, wps, pond) in enumerate(CREEKS, start=1):
    wps = list(wps)
    if pond:
        wps.append((pond[0], pond[1]))
        s_end = pond[0] + 12
    else:
        s_end = wps[-1][0] + 10
    wps.append((s_end, rcx(s_end)))
    path = meander(chaikin(wps, 3), amp=13.0, seed=ci * 1.7)
    CREEK_PATHS.append((name, path, pond))
    draw_line(cdr, path, fill=ci, width=7)
    if pond:
        draw_poly(cdr, ellipse(pond[0], pond[1], pond[2] / 2, pond[3], rot=0.25), fill=ci)
SPUR_PATHS = []
for (k, frac, (ds, dx), length) in SPURS:
    base = CREEK_PATHS[k][1][int(len(CREEK_PATHS[k][1]) * frac)]
    n = math.hypot(ds, dx)
    end = (base[0] + ds / n * length, base[1] + dx / n * length)
    mid = ((base[0] + end[0]) / 2 + 25 * dx / n, (base[1] + end[1]) / 2 - 25 * ds / n)
    sp = meander(chaikin([base, mid, end], 2), amp=6.0, seed=k)
    SPUR_PATHS.append(sp)
    draw_line(cdr, sp, fill=k + 1, width=4)
# Cross-creeks: round the ring through the new farmland, joining each lengthwise creek to the next
# on its side (a drainage network, not dead ends)
CROSS_NAMES = ["Linden Run", "Otter Run", "Fox Run", "Quarry Run", "Sedge Run", "Ash Run",
               "Birch Run", "Plum Run", "Cedar Run", "Mink Run", "Elk Run", "Rush Run"]
CROSS_PATHS = []
for sg in (-1, 1):
    side = [(n, pth) for n, pth, _ in CREEK_PATHS if (pth[0][1] < 0) == (sg < 0)]
    side.sort(key=lambda c: c[1][0][0] % C)
    for k in range(len(side)):
        a_path, b_path = side[k][1], side[(k + 1) % len(side)][1]
        xb = sg * XS(SHORE3 - 520 + 140 * math.sin(k * 2.3 + sg))
        a = min(a_path, key=lambda p: abs(p[1] - xb))
        b = min(b_path, key=lambda p: abs(p[1] - xb))
        bs = b[0] if b[0] > a[0] else b[0] + C
        n_mid = max(3, int((bs - a[0]) / 700))
        mids = [(a[0] + (bs - a[0]) * (i + 1) / (n_mid + 1), xb + 110 * math.sin(i * 1.9 + k)) for i in range(n_mid)]
        path = meander(chaikin([a] + mids + [(bs, b[1])], 3), amp=16.0, seed=k * 2.1 + sg)
        cid = len(CREEK_PATHS) + len(CROSS_PATHS) + 1
        CROSS_PATHS.append((CROSS_NAMES[len(CROSS_PATHS) % len(CROSS_NAMES)], path, None))
        draw_line(cdr, path, fill=cid, width=6)
CREEK_PATHS += CROSS_PATHS
CID = np.array(creek_img)
WCAT[(CID > 0) & (WCAT == 0)] = 3
# ponds are category 4 (drawn again so they read as ponds, not creek)
pond_img = Image.new("L", (CW, WH), 0)
pdr = ImageDraw.Draw(pond_img)
for name, path, pond in CREEK_PATHS:
    if pond:
        draw_poly(pdr, ellipse(pond[0], pond[1], pond[2] / 2, pond[3], rot=0.25), fill=1)
OXBOW_POLYS = []
for name, s_c, _ in OXBOWS:
    # cut-off meander loop sitting in the point-bar floodplain
    r_side = -1 if math.sin(6 * s_c / R + PHI1) > 0 else 1   # point bar = inside of the bend
    xc = rxf(s_c) + r_side * 95
    arc = []
    for k in range(13):
        a = math.pi * (0.15 + 0.7 * k / 12)
        arc.append((s_c + 62 * math.cos(a) * 1.4, xc + r_side * 55 * math.sin(a) - r_side * 30))
    inner = [(p[0] * 0.9 + s_c * 0.1, p[1] * 0.9 + xc * 0.1 - r_side * 3) for p in arc]
    poly = arc + list(reversed(inner))
    poly = [(p[0], p[1]) for p in chaikin(poly, 2, closed=True)]
    OXBOW_POLYS.append((name, poly))
    draw_poly(pdr, poly, fill=1)
PND = np.array(pond_img)
WCAT[(PND > 0) & (WCAT == 0)] = 4
WCAT[(PND > 0) & (WCAT == 3)] = 4


def is_water(s, x, buf=False):
    i, j = idx(s, x)
    return WBUF[j, i] if buf else WCAT[j, i] > 0


WBUF = dilate(WCAT > 0, fk(4))


# ------------------------------------------------------------------ settlements
FT = 0.3048
B = 91.0          # 300 ft block (§3)


class Town:
    def __init__(self, name, tier, pop, founding, archetype, s0, x0, axis="s", flip=1, label="up"):
        self.name, self.tier, self.pop = name, tier, pop
        self.founding, self.archetype = founding, archetype
        self.s0, self.x0, self.axis, self.flip, self.label = s0, x0, axis, flip, label
        self.x0_3km = x0         # the anchor on the 3 km ring's land (its old buildings move by x0 - x0_3km more)
        self.streets, self.bldgs, self.areas, self.marks = [], [], [], []
        self.street_names = {}  # index in streets -> its name (a generated town names its own: tools/settlegen)
        self.extra_hull = []
        # waterfront: walks (boardwalks, piers, docks, breakwaters...), decks, buildings over the
        # water, harbour water cut into the land, land built out into the water
        self.walks, self.decks, self.wbldgs, self.water, self.land = [], [], [], [], []
        self.coastal = False
        self.water_v = 0.0
        self.density = 1.0      # scales the houses / storefronts a new town lays per block side

    # local (u along main street, v across it) -> ring (s, x)
    def g(self, u, v):
        if self.axis == "s":
            return (self.s0 + u, self.x0 + self.flip * v)
        return (self.s0 + self.flip * v, self.x0 + u)

    def rect(self, u0, u1, v0, v1):
        return [self.g(u0, v0), self.g(u1, v0), self.g(u1, v1), self.g(u0, v1)]

    def rrect(self, uc, vc, w, d, ang):
        c, s = math.cos(ang), math.sin(ang)
        pts = []
        for du, dv in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)):
            pts.append(self.g(uc + du * c - dv * s, vc + du * s + dv * c))
        return pts

    def street(self, pts_uv, cls="street", name=""):
        if name:
            self.street_names[len(self.streets)] = name
        self.streets.append(([self.g(u, v) for u, v in pts_uv], cls))

    def bld(self, poly, kind, part=False):
        self.bldgs.append((poly, kind, part))

    def area(self, poly, kind):
        self.areas.append((poly, kind))

    def mark(self, u, v, text):
        self.marks.append((self.g(u, v), text))

    # --- building helpers --------------------------------------------------
    def grid(self, us, vs, mains=(), ext_u=None):
        ext_u = ext_u or {}
        for v in vs:
            u0, u1 = ext_u.get(v, (us[0], us[-1]))
            self.street([(u0, v), (u1, v)], "main" if v in mains else "street")
        for u in us:
            self.street([(u, vs[0]), (u, vs[-1])], "street")

    def stores(self, u0, u1, vf, dirn, n, half=7.0, dmin=20, dmax=28, kind="store", vacant=0.0):
        n = max(1, int(round(n * self.density)))
        span = (u1 - u0 - 10) / n
        for k in range(n):
            a = u0 + 5 + span * k
            b = a + span - 0.9
            d = rng.uniform(dmin, dmax)
            va = vf + dirn * half
            kd = "vacant" if rng.random() < vacant else kind
            self.bld(self.rect(a, b, va, va + dirn * d), kd)

    def houses(self, u0, u1, vf, dirn, n, half=5.0, setback=7.0, kind="house"):
        n = max(1, int(round(n * self.density)))
        span = (u1 - u0 - 12) / n
        for k in range(n):
            uc = u0 + 6 + span * (k + 0.5) + rng.uniform(-2.5, 2.5)
            w, d = rng.uniform(10, 13), rng.uniform(9, 12)
            va = vf + dirn * (half + setback + rng.uniform(0, 3))
            self.bld(self.rect(uc - w / 2, uc + w / 2, va, va + dirn * d), kind)

    def res_block(self, u0, u1, v0, v1, n, alley=False):
        self.houses(u0, u1, v0, 1, n)
        self.houses(u0, u1, v1, -1, n)
        if alley:
            vm = (v0 + v1) / 2
            self.street([(u0, vm), (u1, vm)], "alley")

    def civic(self, u0, u1, v0, v1, kind, w, d, text=None, lawn=None, vface=None):
        if lawn:
            self.area(self.rect(u0 + 4, u1 - 4, v0 + 4, v1 - 4), lawn)
        uc = (u0 + u1) / 2
        if vface is None:
            vc = (v0 + v1) / 2
        else:
            vc = vface
        self.bld(self.rect(uc - w / 2, uc + w / 2, vc - d / 2, vc + d / 2), kind)
        if text:
            self.mark(uc, vc, text)

    def school(self, u0, u1, v0, v1, text):
        self.area(self.rect(u0 + 4, u1 - 4, v0 + 4, v1 - 4), "schoolground")
        um = (u0 + u1) / 2
        self.bld(self.rect(u0 + 8, um - 2, v0 + 10, v0 + 42), "school")
        self.area(self.rect(um + 4, u1 - 8, v0 + 10, v1 - 10), "sportsfield")
        self.mark(u0 + 30, v0 + 26, text)

    def church(self, uc, vc, text=None):
        self.bld(self.rect(uc - 8, uc + 8, vc - 13, vc + 13), "church")
        if text:
            self.mark(uc, vc, text)

    def elevator(self, uc, vc, text="Grain Elev."):
        self.bld(self.rect(uc - 7, uc + 7, vc - 9, vc + 9), "industrial")
        for k in range(3):
            self.bld(circle(*self.g(uc + 13 + k * 11, vc), 5.5, 12), "silo", part=True)
        self.mark(uc, vc, text)

    def tower(self, uc, vc, text="Water Tower"):
        self.bld(circle(*self.g(uc, vc), 8, 14), "tower")
        self.mark(uc, vc, text)

    def subdivision(self, uc, vc, a, b, connect, spacing=40.0):
        """Postwar curvilinear loop (§1/§3) with one cul-de-sac, houses facing the loop."""
        n = 40
        loop = [(uc + a * math.cos(2 * math.pi * k / n), vc + b * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
        self.street(loop, "street")
        near = min(loop, key=lambda p: math.dist(p, connect))
        self.street([connect, near], "street")
        per = sum(math.dist(loop[k], loop[k + 1]) for k in range(n))
        m = int(per / spacing)
        for k in range(m):
            t = 2 * math.pi * (k + 0.5) / m
            du, dv = -a * math.sin(t), b * math.cos(t)
            ang = math.atan2(dv, du)
            nu_, nv_ = math.cos(t) / a, math.sin(t) / b
            nl = math.hypot(nu_, nv_)
            nu_, nv_ = nu_ / nl, nv_ / nl
            for side in (1, -1):
                if side == -1 and min(a, b) < 70:
                    continue
                off = 19 * side
                pu, pv = uc + a * math.cos(t) + nu_ * off, vc + b * math.sin(t) + nv_ * off
                if math.dist((pu, pv), connect) < 20 or math.dist((pu, pv), near) < 16:
                    continue
                self.bld(self.rrect(pu, pv, 12, 10, ang), "house")
        # cul-de-sac stub off the far side
        t = math.pi * 0.25
        p0 = (uc + a * math.cos(t), vc + b * math.sin(t))
        p1 = (p0[0] + 45 * math.cos(t), p0[1] + 45 * math.sin(t))
        self.street([p0, p1], "street")
        self.area(circle(*self.g(*p1), 11, 12), "culdesac")
        for dt in (-1.2, 0.0, 1.2):
            q = (p1[0] + 24 * math.cos(t + dt), p1[1] + 24 * math.sin(t + dt))
            self.bld(self.rrect(q[0], q[1], 12, 10, t + dt), "house")

    def geometry_points(self):
        pts = []
        for p, _ in self.streets:
            pts += p
        for p, _, _ in self.bldgs:
            pts += p
        for p, _ in self.areas:
            pts += p
        return pts + self.extra_hull


def build_harrow_falls():
    # City, water/mill-founded on Lake Tamsin's bluff shore -- §7 downtown directly on the
    # water, elongated along the bank; §8 bluff-and-river-valley: industrial terrace on the
    # water, prestige civic on the bluff top, postwar residential on the upland beyond.
    s0 = 395.0 * SS
    _, cx, _, hb = lake_params(s0)
    shore = float(cx + hb)
    t = Town("Harrow Falls", "City", 41800, "Water/mill-founded", "Stable county seat (Tamsin Co.)",
             s0, shore + 42, "s", 1, "down")
    us = [-227.5 + B * i for i in range(6)]
    vs = [0, 91, 182, 273, 364, 455]
    t.grid(us, vs, mains=(0, 91), ext_u={455: (-420, 420)})
    # waterfront strip (between shore and Front St): legacy warehouses + revitalized promenade
    t.area(t.rect(-227.5, 227.5, -40, -6), "promenade")
    for u in (-215, -175):
        t.bld(t.rect(u, u + 30, -34, -9), "industrial")
    t.bld(t.rect(150, 205, -36, -8), "industrial")
    t.mark(177, -22, "Old Mill Lofts")
    t.mark(0, -24, "Riverfront Promenade")
    for i in range(5):
        u0, u1 = us[i], us[i + 1]
        if 1 <= i <= 3:
            t.stores(u0, u1, 0, 1, 4)          # Front St
            t.stores(u0, u1, 91, -1, 4)        # Main St, lake side
            t.stores(u0, u1, 91, 1, 4)         # Main St, bluff side
            t.street([(u0, 45), (u1, 45)], "alley")
        elif i == 0:
            t.civic(u0, u1, 0, 91, "civic", 34, 30, "City Hall", "lawn")
            t.church((u0 + u1) / 2, 140, "St. Brendan's")
            t.houses(u0, u1, 182, -1, 3)
        else:
            t.civic(u0, u1, 0, 91, "civic", 30, 26, "Post Office", "lawn")
            t.civic(u0, u1, 91, 182, "civic", 36, 28, "Carnegie Library", "lawn")
        if 1 <= i <= 3:
            t.houses(u0, u1, 182, -1, 3)
        # bluff rows: pre-war houses with alleys
        if i == 2:
            t.school(u0, u1, 182, 273, "Lincoln Elem.")
        else:
            t.res_block(u0, u1, 182, 273, 3, alley=True)
        if i == 0:
            t.church((u0 + u1) / 2, 318, "First Methodist")
        else:
            t.res_block(u0, u1, 273, 364, 3, alley=True)
    # bluff top: courthouse square (county seat, once per county), hospital, high school
    t.area(t.rect(us[2] + 4, us[3] - 4, 368, 451), "square")
    t.bld(t.rect(-22, 22, 388, 432), "civic")
    t.mark(0, 440, "Tamsin Co. Courthouse")
    t.civic(us[0], us[1], 364, 455, "civic", 45, 62, "Mercy Hospital", "lawn")
    t.school(us[3], us[4] + 91, 364, 455, "HF High")
    t.houses(us[1], us[2], 364, 1, 4)
    t.tower(-330, 420, "Water Tower")
    t.area(t.rect(-420, -300, 180, 330), "cemetery")
    t.mark(-360, 250, "Oakwood Cemetery")
    # postwar upland subdivisions beyond the bluff-top street (= US 30)
    t.subdivision(-120, 560, 115, 58, (-120, 455))
    t.subdivision(150, 555, 95, 52, (150, 455))
    # arterial strip on US 30 east of downtown (§2: small-city tier only): generated centres
    # (tools/settlegen/centers.py; research/urban_layout/07_centers_and_industry.md) -- a supermarket-anchored
    # neighbourhood centre facing the highway from the north, a convenience strip across it
    CT.place(t, CT.strip_center(CT.Site(262, 418, 0, 122), "neighborhood", random.Random("Harrow Falls US30 north")),
             v_road=458, dirn=1, label="Shopping centre")
    CT.place(t, CT.strip_center(CT.Site(262, 362, 0, 86), "convenience", random.Random("Harrow Falls US30 south")),
             v_road=452, dirn=-1, label="Strip mall")
    return t


def build_kessler():
    # City, rail-founded, dead-flat drained plain: rail-corridor spine (§6), no square;
    # water (Sauk Creek + pond) at middle distance as a residential amenity (§7).
    s0 = 2130.0 * SS
    x_main = rail_x(s0) - 95
    t = Town("Kessler", "City", 34500, "Rail-founded", "Stable ag / manufacturing",
             s0, x_main, "s", -1, "up")
    t.x0_3km = rail_x3(s0) - 95
    us = [-227.5 + B * i for i in range(6)]
    vs = [-70, 0, 91, 182, 273, 364]
    t.grid(us, vs, mains=(0,), ext_u={0: (-430, 330), 91: (-330, 227.5), 273: (-330, 227.5)})
    for i in range(5):
        u0, u1 = us[i], us[i + 1]
        if 1 <= i <= 3:
            t.stores(u0, u1, 0, -1, 4)
            t.stores(u0, u1, 0, 1, 4)
            t.stores(u0, u1, 91, -1, 3, dmin=18, dmax=24)
            t.street([(u0, 45), (u1, 45)], "alley")
        elif i == 0:
            t.civic(u0, u1, -70, 0, "civic", 30, 24, "Fire / Police", vface=-35)
            t.church((u0 + u1) / 2, 45, "St. Adalbert's")
        else:
            t.elevator(u0 + 20, -40)
            t.church((u0 + u1) / 2, 45, "Trinity Lutheran")
    # rail side: depot within one block of Main (§9), elevator already on the side street
    t.bld(t.rect(-18, 18, -78, -90), "civic")
    t.mark(0, -84, "Depot")
    # industry beyond the tracks: the #1 employer (§15)
    t.area(t.rect(-200, 60, -110, -250), "lot")
    t.bld(t.rect(-185, -40, -125, -215), "industrial")
    t.mark(-112, -170, "Kessler Works")
    for u in (80, 125, 170):
        t.bld(t.rect(u, u + 34, -120, -175), "industrial")
    for i in range(5):
        u0, u1 = us[i], us[i + 1]
        if i == 2:
            t.civic(u0, u1, 91, 182, "civic", 40, 30, "City Hall", "lawn")
        elif i == 1:
            t.civic(u0, u1, 91, 182, "civic", 32, 26, "Library", "lawn")
        else:
            t.res_block(u0, u1, 91, 182, 3, alley=True)
        if i == 3:
            t.school(u0, u1, 182, 273, "Kessler High")
        else:
            t.res_block(u0, u1, 182, 273, 3, alley=True)
        if i == 0:
            t.civic(u0, u1, 273, 364, "civic", 44, 60, "St. Luke's Hospital", "lawn")
        else:
            t.res_block(u0, u1, 273, 364, 3, alley=i != 2)
    # Sauk Park: creek + pond on the west edge (streets cross the creek -- §10 rule)
    t.area(t.rect(-320, -240, 20, 360), "park")
    t.mark(-270, 300, "Sauk Park")
    t.tower(260, 150, "Water Tower")
    t.subdivision(-40, 450, 150, 55, (-40, 364))
    # arterial strip along US 30 west approach
    t.area(t.rect(-425, -340, 14, 100), "parking")
    t.bld(t.rect(-422, -345, 55, 118), "bigbox")
    t.mark(-383, 86, "Big-box")
    t.bld(t.rect(-425, -380, -14, -36), "strip")
    t.bld(t.rect(-370, -352, -14, -30), "strip")
    t.area(t.rect(-425, -380, -36, -90), "lot")
    t.mark(-400, -62, "Auto dealer")
    return t


def build_town(name, pop, founding, arche, s0, x0, axis, flip, layout, label, vacant=0.0, x0_3km=None):
    t = Town(name, "Town", pop, founding, arche, s0, x0, axis, flip, label)
    if x0_3km is not None:
        t.x0_3km = x0_3km
    us = [-182 + B * i for i in range(5)]           # 4 blocks of Main Street
    if layout == "rail":
        vs = [-70, 0, 91, 182, 273]
        t.grid(us, vs, mains=(0,))
        for i in range(4):
            u0, u1 = us[i], us[i + 1]
            if i in (1, 2):
                t.stores(u0, u1, 0, -1, 4, vacant=vacant)
                t.stores(u0, u1, 0, 1, 4, vacant=vacant)
            elif i == 0:
                t.elevator(u0 + 18, -40)
                t.church((u0 + u1) / 2, 45, None)
            else:
                t.civic(u0, u1, -70, 0, "civic", 26, 22, "Post Office", vface=-35)
                t.civic(u0, u1, 0, 91, "civic", 30, 24, "Town Hall", "lawn")
        t.bld(t.rect(-15, 15, -78, -90), "civic")
        t.mark(0, -84, "Depot")
        res_rows = [(91, 182), (182, 273)]
    else:
        vs = [-182, -91, 0, 91, 182]
        t.grid(us, vs, mains=(0,))
        for i in range(4):
            u0, u1 = us[i], us[i + 1]
            if i == 2:
                # the square block sits on the main-street side; storefronts face it
                kind = "courthouse" if layout == "courthouse" else "green"
                t.area(t.rect(u0 + 4, u1 - 4, 4, 87), "square")
                if kind == "courthouse":
                    t.bld(t.rect(u0 + 26, u1 - 26, 24, 66), "civic")
                    t.mark((u0 + u1) / 2, 45, f"{t.name.split()[0]} Co. Courthouse" if False else "Courthouse")
                else:
                    t.bld(circle(*t.g((u0 + u1) / 2, 45), 6, 10), "civic")
                    t.mark((u0 + u1) / 2, 45, "Town Green")
                t.stores(u0, u1, 0, -1, 4)
                t.stores(u0, u1, 91, 1, 4)
            elif i == 1:
                t.stores(u0, u1, 0, -1, 4)
                t.stores(u0, u1, 0, 1, 4)
            elif i == 3:
                t.stores(u0, u1, 0, -1, 3)
                t.civic(u0, u1, 0, 91, "civic", 28, 24, "Library" if layout == "green" else "Opera House", "lawn")
            else:
                t.civic(u0, u1, -91, 0, "civic", 26, 22, "Post Office", "lawn")
                t.church((u0 + u1) / 2, 45, None)
        res_rows = [(-182, -91), (91, 182)]
    for (v0, v1) in res_rows:
        for i in range(4):
            u0, u1 = us[i], us[i + 1]
            if (v0, i) == (res_rows[0][0], 3):
                t.church((u0 + u1) / 2, (v0 + v1) / 2, None)
                t.houses(u0, u1, v1, -1, 2)
            elif (v0, i) == (res_rows[-1][0], 0):
                t.school(u0, u1, v0, v1, "School")
            else:
                t.houses(u0, u1, v0, 1, 3 if abs(v0) < 100 else 2)
                t.houses(u0, u1, v1, -1, 3 if abs(v1) < 100 else 2)
                if layout != "rail":
                    t.street([(u0, (v0 + v1) / 2), (u1, (v0 + v1) / 2)], "alley")
    return t


def build_marlowe():
    t = build_town("Marlowe", 9100, "Inland / trail", "Stable county seat (Brannock Co.)",
                   1500.0 * SS, XS(-760.0 - WIDEN), "x", 1, "courthouse", "up", x0_3km=-760.0 - WIDEN)
    t.marks = [(p, "Brannock Co. Courthouse" if txt == "Courthouse" else txt) for p, txt in t.marks]
    t.subdivision(-262, 10, 55, 105, (-182, 10))
    t.tower(-230, 60, "Water Tower")
    return t


def build_fenwick():
    t = build_town("Fenwick", 6400, "Inland / trail", "College town",
                   2150.0 * SS, XS(-800.0 - WIDEN), "s", 1, "green", "up", x0_3km=-800.0 - WIDEN)
    # Fenwick College: the settlement's one unmistakable landmark (§17)
    t.area(t.rect(190, 330, -182, 20), "campus")
    for (u, v) in ((210, -160), (270, -160), (210, -60), (275, -60), (240, -10)):
        t.bld(t.rect(u, u + 38, v, v + 26), "civic")
    t.mark(260, -110, "Fenwick College")
    t.street([(182, -91), (330, -91)], "street")
    return t


def build_bellhaven():
    s0 = 1050.0 * SS
    return build_town("Bellhaven", 7200, "Rail-founded", "Stable ag / manufacturing",
                      s0, rail_x(s0) - 95, "s", -1, "rail", "up", x0_3km=rail_x3(s0) - 95)


def build_tamarack():
    s0 = 2820.0 * SS
    t = build_town("Tamarack", 8300, "Rail-founded", "Declining rust-belt",
                   s0, rail_x(s0) - 95, "s", -1, "rail", "up", vacant=0.4, x0_3km=rail_x3(s0) - 95)
    t.area(t.rect(60, 230, -110, -230), "lot")
    t.bld(t.rect(75, 200, -125, -200), "vacant")
    t.mark(137, -165, "Closed foundry")
    return t


def build_village(name, pop, founding, arche, s0, x0, axis, flip, n_stores, label, vs=(-91, 0, 91),
                  blocks=2, school=None, elevator=False, depot=False, vacant=0.0, carnegie=False, x0_3km=None):
    """Village tier (§1): 1-3 block Main Street or bare crossroads, 2-10 residential streets,
    freestanding church/post office within a block of Main (§9)."""
    t = Town(name, "Village", pop, founding, arche, s0, x0, axis, flip, label)
    if x0_3km is not None:
        t.x0_3km = x0_3km
    us = [-B * blocks / 2 + B * i for i in range(blocks + 1)]
    vs = list(vs)
    t.grid(us, vs, mains=(0,))
    core = (blocks - 1) // 2
    two_sided = vs[0] < 0
    n_up = n_stores - n_stores // 2 if two_sided else n_stores
    t.stores(us[core], us[core + 1], 0, 1, n_up, vacant=vacant)
    if two_sided:
        t.stores(us[core], us[core + 1], 0, -1, n_stores // 2, vacant=vacant)
    used = {(core, 0), (core, -91)}
    other = [i for i in range(blocks) if i != core]
    ch = other[0]
    t.church((us[ch] + us[ch + 1]) / 2, 45, None)
    used.add((ch, 0))
    po = other[-1] if len(other) > 1 else ch
    if po != ch:
        t.civic(us[po], us[po + 1], 0, 91, "civic", 16, 14, "Post Office", vface=22)
        used.add((po, 0))
    elif two_sided:
        t.civic(us[po], us[po + 1], -91, 0, "civic", 16, 14, "Post Office", vface=-22)
        used.add((po, -91))
    else:
        t.civic(us[po], us[po + 1], 91, 182, "civic", 16, 14, "Post Office", vface=113)
        used.add((po, 91))
    if carnegie:
        t.civic(us[0], us[1], vs[0], vs[1], "civic", 22, 18, "Carnegie Library", "lawn")
        used.add((0, vs[0]))
    if school:
        a, b_ = us[-2], us[-1]
        t.school(a, b_, vs[-1], vs[-1] + 91, school)
        t.street([(a, vs[-1] + 91), (b_, vs[-1] + 91)], "street")
        t.street([(a, vs[-1]), (a, vs[-1] + 91)], "street")
        t.street([(b_, vs[-1]), (b_, vs[-1] + 91)], "street")
    for i in range(blocks):
        for (v0, v1) in zip(vs, vs[1:]):
            if (i, v0) in used:
                if v0 == 0 and (i, v0) != (po, 0) or (i, v0) == (ch, 0):
                    t.houses(us[i], us[i + 1], v1, -1, 2)
                elif v1 == 0 and v0 != vs[0] or v1 == 0 and not carnegie:
                    t.houses(us[i], us[i + 1], v0, 1, 2)
                continue
            if v1 - v0 < 80:
                continue
            inner = abs(v0) < 100 and abs(v1) < 100
            t.houses(us[i], us[i + 1], v0, 1, 2 if inner else 1)
            t.houses(us[i], us[i + 1], v1, -1, 2 if inner else 1)
    if elevator:
        t.elevator(us[0] + 18, -118, "Grain Elev. (tallest)")
    if depot:
        t.bld(t.rect(-12, 12, -62, -72), "civic")
        t.mark(0, -67, "Depot (museum)")
    return t


# ------------------------------------------------------------------ coastal communities
# Nine new communities on the seas and Lake Tamsin, and the Harrow Falls / Cedar Ford waterfronts --
# laid out from research/coastal_communities/.  Local frame: u along the shore, v toward the water
# (v = 0 the shore road; the waterline at v = the site's set-back).  Walks (boardwalks, piers, docks,
# breakwaters) and buildings standing over the water are kept apart from the land buildings.

def _swalk(t, pts_uv, w, kind):
    t.walks.append(([t.g(u, v) for u, v in pts_uv], w, kind))


def _deck(t, u0, u1, v0, v1, kind="deck"):
    t.decks.append((t.rect(u0, u1, v0, v1), kind))


def _wb(t, u0, u1, v0, v1, kind):
    t.wbldgs.append((t.rect(u0, u1, v0, v1), kind))


def _pier(t, u, v0, v1, w, head=None, kind="pier"):
    """A pier from the shore (v0) out over the water to v1, with an optional T-head (width, depth)."""
    _swalk(t, [(u, v0), (u, v1)], w, kind)
    if head:
        hw, hd = head
        sgn = 1 if v1 > v0 else -1
        _deck(t, u - hw / 2, u + hw / 2, v1, v1 + sgn * hd)


def _stores_v(t, v0, v1, uf, dirn, n, half=6.0, dmin=18, dmax=24, kind="store"):
    """Storefronts along a street that runs in v (a cross street at u = uf)."""
    n = max(1, int(round(n * t.density)))
    span = (abs(v1 - v0) - 8) / n
    lo = min(v0, v1)
    for k in range(n):
        a = lo + 4 + span * k
        b = a + span - 0.9
        d = rng.uniform(dmin, dmax)
        ua = uf + dirn * half
        t.bld([t.g(ua, a), t.g(ua + dirn * d, a), t.g(ua + dirn * d, b), t.g(ua, b)], kind)


def _cottage_blocks(t, us, v_rows, n=4, kind="cottage", alley=False):
    for (v0, v1) in v_rows:
        for i in range(len(us) - 1):
            t.houses(us[i], us[i + 1], v0, -1 if v1 < v0 else 1, n, kind=kind)
            t.houses(us[i], us[i + 1], v1, 1 if v1 < v0 else -1, n, kind=kind)
            if alley:
                t.street([(us[i], (v0 + v1) / 2), (us[i + 1], (v0 + v1) / 2)], "alley")


def coastal_town(site_name, tier, pop, founding, arche):
    name, sg, sc, half, line, ro = SITE[site_name]
    t = Town(name, tier, pop, founding, arche, sc, sg * (line - ro), "s", sg, "down" if sg < 0 else "up")
    t.coastal = True
    t.water_v = ro          # the waterline, in v
    return t


def build_brightwater():
    # Jersey Shore boardwalk town (Ocean City grid, Wildwood motels, Seaside Heights amusement pier)
    t = coastal_town("Brightwater", "Town", 6200, "Resort / excursion railroad", "Seasonal resort (Jersey Shore)")
    t.density = 0.35
    us = [-400 + 80 * i for i in range(11)]
    vs = [0, -85, -170, -255]
    t.grid(us, vs, mains=(-85,))
    _swalk(t, [(-440, 20), (440, 20)], 12, "boardwalk")
    for u in us:
        _swalk(t, [(u, 26), (u, 36)], 4, "boardwalk")                     # stairs to the beach
    t.area(t.rect(-440, 440, 26, t.water_v), "beach")
    for i in range(10):                                                  # the boards' frontage: stands
        t.stores(us[i] + 2, us[i + 1] - 2, 14, -1, 5, half=0, dmin=6, dmax=7,
                 kind="arcade" if i % 3 == 0 else "stand")
    _deck(t, 110, 200, 26, 220, "amusement")                           # Casino Pier / Morey's
    for k in range(6):
        _wb(t, 118 + (k % 3) * 26, 136 + (k % 3) * 26, 60 + (k // 3) * 60, 84 + (k // 3) * 60, "ride")
    t.mark(155, 150, "Amusement Pier")
    for i in range(10):                                                  # motels and hotels on Ocean Ave
        if i == 1:
            t.bld(t.rect(us[i] + 4, us[i + 1] - 4, -8, -62), "civic")
            t.mark((us[i] + us[i + 1]) / 2, -35, "Convention Hall")
            continue
        kind = "motel" if i % 2 else "hotel"
        t.bld(t.rect(us[i] + 6, us[i + 1] - 26, -8, -44), kind)
        t.area(t.rect(us[i + 1] - 22, us[i + 1] - 6, -12, -30), "pool")
    for i in range(10):                                                  # Central Ave: the resort avenue
        t.stores(us[i], us[i + 1], -85, 1, 4, dmin=16, dmax=20)
        t.stores(us[i], us[i + 1], -85, -1, 4, dmin=18, dmax=22)
    for i in range(10):                                                  # cottage blocks
        t.houses(us[i], us[i + 1], -170, 1, 4, kind="cottage")
        t.houses(us[i], us[i + 1], -170, -1, 4, kind="cottage")
        t.houses(us[i], us[i + 1], -255, 1, 4, kind="cottage")
    t.church(-40, -212, "St. Brendan-by-the-Sea")
    t.civic(us[6], us[7], -170, -255, "civic", 24, 18, "Post Office", vface=-190)
    t.civic(us[8], us[9], -170, -255, "school", 50, 30, "Brightwater School", vface=-212)
    t.bld(t.rect(-8, 8, 4, 12), "civic")
    t.mark(0, 8, "Beach Patrol")
    for u in range(-400, 441, 80):                                       # lifeguard stands on the sand
        t.bld(t.rect(u - 1.5, u + 1.5, 70, 73), "lifeguard")
    return t


def build_playa_verde():
    # Florida pier town (Naples / Daytona pier on Main St, Hollywood Broadwalk + bandshell)
    t = coastal_town("Playa Verde", "Town", 5400, "Resort / pier", "West Coast pier town (Oceanside / Pismo Beach)")
    t.density = 0.5
    us = [-360 + 90 * i for i in range(9)]
    vs = [0, -90, -180, -270]
    t.grid(us, vs)
    t.street([(0, 0), (0, -360)], "main")
    _swalk(t, [(-420, 14), (420, 14)], 10, "promenade")                 # the Broadwalk
    t.area(t.rect(-420, 420, 20, t.water_v), "beach")
    _pier(t, 0, 20, 330, 7, head=(34, 14))
    _wb(t, -11, 11, 332, 342, "restaurant")
    _wb(t, 5, 11, 150, 156, "bait")
    for v in (90, 240):
        _wb(t, -4, 4, v, v + 5, "pavilion")
    t.mark(0, 355, "Playa Verde Pier")
    t.area(t.rect(-40, 40, -6, -40), "plaza")
    t.mark(0, -24, "Pier Plaza")
    t.bld(t.rect(-262, -238, 22, 32), "pavilion")
    t.mark(-250, 40, "Bandshell")
    for i in range(8):
        if i in (3, 4):
            continue
        t.bld(t.rect(us[i] + 6, us[i] + 42, -8, -50), "hotel")
        t.bld(t.rect(us[i] + 48, us[i + 1] - 6, -8, -40), "motel")
    _stores_v(t, -8, -86, 0, -1, 4)
    _stores_v(t, -8, -86, 0, 1, 4)
    _stores_v(t, -94, -176, 0, -1, 4)
    _stores_v(t, -94, -176, 0, 1, 4)
    for i in range(8):
        t.houses(us[i], us[i + 1], -90, -1, 3, kind="bungalow")
        t.houses(us[i], us[i + 1], -180, 1, 3, kind="bungalow")
        t.houses(us[i], us[i + 1], -180, -1, 3, kind="bungalow")
        t.houses(us[i], us[i + 1], -270, 1, 3, kind="bungalow")
    t.church(-135, -225, None)
    t.civic(us[5], us[6], -180, -270, "civic", 22, 16, "Town Hall", "lawn")
    return t


def build_oceanview():
    # Virginia Beach oceanfront: boardwalk, a continuous hotel wall, Atlantic Ave one block back
    t = coastal_town("Oceanview", "Town", 9800, "Resort / amusement", "West Coast boardwalk resort (Santa Cruz / Venice / Santa Monica)")
    t.density = 0.45
    us = [-540 + 120 * i for i in range(10)]
    vs = [-55, -145, -235]
    t.grid(us, vs, mains=(-55,))
    _swalk(t, [(-560, 22), (560, 22)], 10, "promenade")                  # concrete boardwalk
    t.area(t.rect(-560, 560, 28, t.water_v), "beach")
    for i in range(9):
        for k in range(2):
            u0 = us[i] + 6 + k * 57
            t.bld(t.rect(u0, u0 + 50, 14, -40), "hotel")
    t.area(t.rect(-30, 30, 14, 28), "plaza")
    t.mark(0, 8, "Neptune Plaza")
    for i in range(9):
        t.stores(us[i], us[i + 1], -55, -1, 5, dmin=18, dmax=24)
        t.stores(us[i], us[i + 1], -145, 1, 4, dmin=18, dmax=22, kind="motel")
        t.houses(us[i], us[i + 1], -145, -1, 4, kind="condo")
        t.houses(us[i], us[i + 1], -235, 1, 4, kind="cottage")
    _pier(t, 420, 28, 300, 6, head=(22, 10))
    _wb(t, 412, 428, 302, 309, "restaurant")
    t.mark(420, 320, "Fishing Pier")
    t.civic(us[4], us[5], -145, -235, "civic", 30, 22, "Oceanfront Visitor Ctr.", vface=-170)
    return t


def _harbour_services(t, u_ice, u_auction, u_rail, u_cg, village_us):
    wv = t.water_v
    t.bld(t.rect(u_ice, u_ice + 26, 20, 48), "icehouse")
    t.mark(u_ice + 13, 56, "Ice House")
    t.bld(t.rect(u_auction, u_auction + 50, 22, 58), "shed")
    t.mark(u_auction + 25, 66, "Fish Auction")
    for k in range(4):
        t.bld(t.rect(u_auction - 60 + k * 14, u_auction - 50 + k * 14, 70, 92), "shed")
    _swalk(t, [(u_rail, 30), (u_rail, wv + 70)], 6, "railway")           # marine railway
    t.bld(t.rect(u_rail - 45, u_rail - 8, 16, 70), "boatyard")
    t.mark(u_rail - 26, 78, "Boatyard")
    t.bld(t.rect(u_cg, u_cg + 34, 18, 56), "civic")
    t.bld(circle(*t.g(u_cg + 44, 30), 4, 10), "lighthouse")
    t.mark(u_cg + 17, 64, "Coast Guard")
    t.bld(t.rect(u_cg - 40, u_cg - 26, 70, 84), "civic")
    t.mark(u_cg - 33, 92, "Harbormaster")
    us = village_us
    t.grid(us, [0, -80, -160])
    for i in range(len(us) - 1):
        t.houses(us[i], us[i + 1], -80, 1, 3, kind="house")
        t.houses(us[i], us[i + 1], -80, -1, 3, kind="house")
        t.houses(us[i], us[i + 1], -160, 1, 3, kind="house")
    t.church((us[1] + us[2]) / 2, -40, None)
    t.stores(us[2], us[3], 0, -1, 3, dmin=14, dmax=18)
    t.mark((us[2] + us[3]) / 2, -30, "Store / Diner / Tavern")


def build_tern_harbor():
    # North Sea fishing village: Lubec/Eastport canneries on the wharves, Gloucester harbour services
    t = coastal_town("Tern Harbor", "Village", 1300, "Fishing / cannery", "Working waterfront")
    t.density = 0.55
    wv = t.water_v
    _swalk(t, [(270, wv), (310, wv + 70), (260, wv + 160), (120, wv + 200), (-10, wv + 205)], 14, "breakwater")
    for u in (-240, -170, -100, -30):
        _pier(t, u, wv - 6, wv + 110, 12, kind="wharf")
        _wb(t, u - 5, u + 5, wv + 20, wv + 50, "fishhouse")
    _pier(t, 210, wv - 6, wv + 55, 6, kind="wharf")
    t.mark(210, wv + 65, "Fuel Dock")
    # the cannery on pilings, its warehouse across the shore road, the conveyor crossover, the stack
    _wb(t, 50, 150, wv - 14, wv + 50, "cannery")
    t.bld(t.rect(60, 140, -12, -52), "warehouse")
    _swalk(t, [(100, -12), (100, wv - 14)], 5, "crossover")
    t.bld(circle(*t.g(160, -24), 3.5, 10), "stack")
    t.mark(100, wv + 62, "Tern Harbor Packing Co.")
    _harbour_services(t, -110, -300, -330, 250, [-300, -200, -100, 0, 100, 200])
    return t


def build_pelican_cove():
    # South Sea fishing village: a short Cannery Row (canneries on the water, warehouses inland,
    # conveyor crossovers over the street), Astoria-style sheds on pilings
    t = coastal_town("Pelican Cove", "Village", 1600, "Fishing / cannery", "Working waterfront")
    t.density = 0.55
    wv = t.water_v
    _swalk(t, [(-330, wv), (-360, wv + 90), (-290, wv + 190), (-120, wv + 215), (20, wv + 210)], 14, "breakwater")
    for (u0, u1) in ((-220, -130), (10, 110)):
        _wb(t, u0, u1, 70, wv + 40, "cannery")
        t.bld(t.rect(u0 + 10, u1 - 10, -12, -52), "warehouse")
        _swalk(t, [((u0 + u1) / 2, -12), ((u0 + u1) / 2, 70)], 5, "crossover")
        t.bld(circle(*t.g(u1 + 8, -24), 3.5, 10), "stack")
    t.mark(-175, wv + 52, "Pacific Packing")
    t.mark(60, wv + 52, "Cove Canning Co.")
    _pier(t, -290, wv - 6, wv + 120, 14, kind="wharf")
    for k in range(3):
        _wb(t, -296, -284, wv + 20 + k * 30, wv + 42 + k * 30, "fishhouse")
    _pier(t, 250, wv - 6, wv + 90, 10, kind="wharf")
    t.mark(250, wv + 100, "Sportfishing")
    _harbour_services(t, 140, -60, 330, -330, [-280, -180, -80, 20, 120, 220])
    t.mark(0, 8, "Cannery Row")
    return t


def build_haven_point():
    # Great Lakes harbour town (Grand Haven / Saugatuck) at Lost Creek's mouth: a channel between twin
    # piers with a lighthouse + catwalk, a marina basin, the riverwalk, Coast Guard, beach, bluff cottages
    t = coastal_town("Haven Point", "Town", 3900, "Inlet harbor / fishing", "East Coast inlet town (Barnegat Light / Montauk)")
    t.density = 0.8
    wv = t.water_v
    t.water.append(t.rect(-32, 32, -70, wv + 4))                          # the channel
    t.water.append(t.rect(-230, -32, -190, -70))                          # the marina basin
    for u in (-44, 44):
        _swalk(t, [(u, wv - 4), (u, wv + 230)], 10, "breakwater")
    _swalk(t, [(44, 8), (44, wv + 200)], 2, "catwalk")
    _wb(t, 38, 50, wv + 190, wv + 202, "lighthouse")
    _wb(t, 36, 52, wv + 212, wv + 228, "lighthouse")
    t.mark(44, wv + 245, "South Pier Lights")
    _swalk(t, [(40, -70), (40, wv - 4)], 6, "boardwalk")                   # the riverwalk
    for k in range(6):
        _swalk(t, [(-220 + k * 32, -70), (-220 + k * 32, -110)], 2, "dock")
    t.street([(-400, 0), (400, 0)], "street")
    t.area(t.rect(60, 400, 10, wv), "beach")
    t.mark(230, 60, "Haven Point State Beach")
    t.area(t.rect(260, 380, -8, -60), "parking")
    t.bld(t.rect(60, 100, 16, 50), "civic")
    t.mark(80, 58, "Coast Guard")
    us = [60, 150, 240, 330]
    t.grid(us, [-30, -120, -210])
    t.street([(40, -30), (60, -30)], "street")
    for i in range(3):
        t.stores(us[i], us[i + 1], -30, -1, 4)
        t.houses(us[i], us[i + 1], -120, 1, 3, kind="house")
        t.houses(us[i], us[i + 1], -120, -1, 3, kind="house")
    t.church(195, -165, None)
    ws = [-520, -430, -340, -250]                                         # bluff cottages west of the marina
    t.grid(ws, [-30, -120, -210])
    for i in range(3):
        t.houses(ws[i], ws[i + 1], -120, 1, 3, kind="cottage")
        t.houses(ws[i], ws[i + 1], -120, -1, 3, kind="cottage")
        t.houses(ws[i], ws[i + 1], -210, 1, 3, kind="cottage")
    t.street([(-250, -30), (-40, -30)], "street")
    t.bld(t.rect(-240, -200, -34, -62), "boatyard")
    t.bld(t.rect(-120, -80, -200, -230), "store")
    t.mark(-130, -60, "Marina")
    return t


def build_port_tamsin():
    # Great Lakes lake town on Lake Tamsin's new north shore (Saugatuck / South Haven): marina and
    # breakwater with a pier light, public beach, small downtown, a grand hotel, bluff cottages
    s0 = LAKE_S + 150
    te = float(water_edges(s0)[0])
    t = Town("Port Tamsin", "Town", 3400, "Lake resort", "Great Lakes bluff resort (Petoskey)", s0, te - 90, "s", 1, "up")
    t.coastal = True
    t.density = 0.6
    t.water_v = 90
    wv = 90
    _swalk(t, [(-330, wv - 5), (-330, wv + 120), (-150, wv + 120)], 10, "breakwater")
    for k in range(5):
        _swalk(t, [(-310 + k * 36, wv - 2), (-310 + k * 36, wv + 80)], 3, "dock")
    _swalk(t, [(-110, wv - 5), (-110, wv + 180)], 8, "pier")
    _wb(t, -116, -104, wv + 170, wv + 182, "lighthouse")
    t.mark(-110, wv + 196, "Pier Light")
    t.area(t.rect(0, 380, 10, wv), "beach")
    t.mark(190, 50, "Tamsin Beach")
    us = [-380, -285, -190, -95, 0, 95, 190, 285, 380]
    t.grid(us, [0, -90, -180], mains=(-90,))
    for i in range(8):
        t.stores(us[i], us[i + 1], -90, 1, 3) if 1 <= i <= 4 else t.houses(us[i], us[i + 1], -90, 1, 3, kind="cottage")
        t.stores(us[i], us[i + 1], -90, -1, 3) if 1 <= i <= 4 else t.houses(us[i], us[i + 1], -90, -1, 3, kind="cottage")
        t.houses(us[i], us[i + 1], -180, 1, 3, kind="cottage")
    t.bld(t.rect(200, 330, -10, -70), "hotel")
    t.mark(265, -40, "Tamsin Grand Hotel")
    t.bld(t.rect(-360, -300, -8, -60), "boatyard")
    t.church(-140, -135, None)
    t.civic(us[4], us[5], -90, -180, "civic", 22, 16, "Post Office", vface=-110)
    return t


def build_port_carrow():
    # North Sea city: Charleston (Grand Model grid, Four Corners, King St, Rainbow Row, the Battery,
    # City Market) + Nantucket (parallel wharves with shingled shacks, cobbled Main St, grey-shingled houses)
    t = coastal_town("Port Carrow", "City", 38600, "Port / whaling", "Port and tourism city (Charleston + Nantucket)")
    t.density = 0.42
    wv = t.water_v
    # the Battery: a point of land with a seawall promenade and a live-oak park
    pt = [(-800, 0), (-805, 90), (-780, 180), (-720, 238), (-650, 245), (-600, 200), (-590, wv)]
    t.land.append([t.g(u, v) for u, v in pt + [(-590, 0)]])
    t.area([t.g(u * 0.97 - 20, v * 0.93) for u, v in pt[1:-1]] + [t.g(-610, 10), t.g(-790, 10)], "park")
    _swalk(t, pt, 8, "promenade")
    t.mark(-695, 120, "The Battery")
    # the wharves (Nantucket) off the wharf street (East Bay St, v = 0)
    for k, u in enumerate((-520, -430, -340, -250, -160, -70, 20)):
        L = 170 if k % 2 else 200
        _pier(t, u, wv - 6, wv + L, 20, kind="wharf")
        for j in range(2):
            _wb(t, u - 8, u + 8, wv + 30 + j * 70, wv + 56 + j * 70, "shingle")
    t.mark(-70, wv + 230, "Straight Wharf")
    _pier(t, 150, wv - 6, wv + 280, 26, kind="wharf")
    _wb(t, 132, 168, wv + 250, wv + 280, "civic")
    t.mark(150, wv + 300, "Ferry Terminal")
    _pier(t, 300, wv - 6, wv + 90, 12, kind="wharf")
    _wb(t, 285, 315, wv + 60, wv + 88, "civic")
    t.mark(300, wv + 104, "Yacht Club")
    # Rainbow Row on the wharf street, merchant rows either side
    t.stores(-320, -140, 0, -1, 14, dmin=15, dmax=16, kind="rowhouse")
    t.mark(-230, -30, "Rainbow Row")
    t.stores(-560, -330, 0, -1, 10, dmin=18, dmax=22)
    t.stores(-130, 60, 0, -1, 8, dmin=18, dmax=22)
    # the Grand Model grid
    us = [-546 + 91 * i for i in range(13)]
    vs = [0, -91, -182, -273, -364, -455]
    t.grid(us, vs, mains=(0,))
    t.street([(0, 0), (0, -455)], "main")                                 # cobbled Main Street
    t.street([(182, 0), (182, -660)], "main")                             # King Street
    _stores_v(t, -8, -86, 0, -1, 4)
    _stores_v(t, -8, -86, 0, 1, 4)
    _stores_v(t, -96, -178, 0, -1, 4)
    _stores_v(t, -96, -178, 0, 1, 4)
    for (v0, v1) in ((-8, -86), (-96, -178), (-187, -269), (-278, -360), (-369, -451), (-460, -560), (-560, -650)):
        _stores_v(t, v0, v1, 182, -1, 4)
        _stores_v(t, v0, v1, 182, 1, 4)
    t.mark(182, -680, "King Street")
    # the Four Corners of Law at Meeting x Broad (u = -91, v = -182)
    for (du, dv, kind, txt) in ((-1, 1, "civic", "City Hall"), (1, 1, "civic", "Courthouse"),
                                (-1, -1, "civic", "Post Office"), (1, -1, "church", "St. Michael's")):
        uc, vc = -91 + du * 26, -182 + dv * 26
        t.bld(t.rect(uc - 17, uc + 17, vc - 16, vc + 16), kind)
        t.mark(uc, vc, txt)
    t.bld(t.rect(-420, -230, -100, -112), "market")
    t.mark(-325, -125, "City Market")
    kinds = ("singlehouse", "shingle")
    for j, (v0, v1) in enumerate(((-91, -182), (-182, -273), (-273, -364), (-364, -455))):
        for i in range(12):
            u0, u1 = us[i], us[i + 1]
            if u0 <= -91 <= u1 and v1 <= -182 <= v0:
                continue
            if u0 <= 0 < u1 or u0 <= 182 < u1:
                continue
            if j == 0 and -420 < u0 < -230:
                continue
            k = kinds[(i + j) % 2]
            t.houses(u0, u1, v0, -1, 3, kind=k)
            t.houses(u0, u1, v1, 1, 3, kind=k)
    t.church(-364 + 45, -318, "Circular Church")
    t.church(273 + 45, -410, "Huguenot Church")
    t.civic(us[9], us[10], -364, -455, "school", 50, 36, "Carrow Academy", "schoolground", vface=-400)
    # the ocean beach and pier east of the wharves
    t.area(t.rect(420, 780, 10, wv + 60), "beach")
    _pier(t, 620, wv + 50, wv + 300, 7, head=(28, 12))
    t.houses(400, 780, 0, -1, 7, kind="beachhouse")
    return t


def build_solana_point():
    # South Sea city: Huntington Beach (wide beach, long pier, Pier Plaza, Main St, Pacific City) +
    # Dana Point (rocky headland, harbour in its lee: breakwater, two marina basins, island + bridge,
    # boatyard, launch ramp, fishing pier, yacht clubs; the bluff-top Lantern District)
    t = coastal_town("Solana Point", "City", 44200, "Resort / oil / harbor", "Beach and harbor city (Huntington Beach + Dana Point)")
    t.density = 0.7
    wv = t.water_v
    t.street([(-820, 0), (820, 0)], "main")                               # the coast highway through town
    # Huntington Beach half
    t.area(t.rect(-800, -80, 10, 34), "parking")
    t.area(t.rect(-800, -80, 34, wv), "beach")
    _pier(t, -420, 34, 560, 9, head=(32, 16))
    _wb(t, -432, -408, 562, 574, "restaurant")
    _wb(t, -426, -414, 300, 308, "lifeguard")
    t.mark(-420, 595, "Solana Pier")
    t.area(t.rect(-465, -375, 4, 34), "plaza")
    t.mark(-420, 20, "Pier Plaza")
    t.street([(-420, 0), (-420, -450)], "main")
    t.mark(-420, -470, "Main Street")
    us = [-780 + 90 * i for i in range(8)]
    vs = [-100, -200, -300, -400]
    t.grid(us, vs)
    for (v0, v1) in ((-8, -96), (-104, -196), (-204, -296)):
        _stores_v(t, v0, v1, -420, -1, 4)
        _stores_v(t, v0, v1, -420, 1, 4)
    t.area(t.rect(-360, -160, -8, -92), "plaza")
    for k in range(5):
        t.bld(t.rect(-350 + k * 38, -318 + k * 38, -14, -40), "store")
    t.bld(t.rect(-340, -180, -60, -86), "store")
    t.mark(-260, -52, "Pacific City")
    t.bld(t.rect(-560, -462, -8, -80), "hotel")
    t.mark(-511, -44, "The Strand")
    for i in range(7):
        for (v0, v1) in ((-100, -200), (-200, -300), (-300, -400)):
            if us[i] <= -420 < us[i + 1] or us[i] >= -360 and v0 == -100 and us[i] < -160:
                continue
            t.houses(us[i], us[i + 1], v0, -1, 3, kind="beachhouse")
            t.houses(us[i], us[i + 1], v1, 1, 3, kind="beachhouse")
    # the headland
    t.land.append([t.g(u, v) for u, v in chaikin([(-90, 0), (-60, 180), (-30, 300), (20, 385), (80, 405),
                                                         (140, 360), (170, 250), (180, 0)], 2)])
    t.area([t.g(u, v) for u, v in chaikin([(-40, 80), (-20, 250), (40, 350), (110, 350), (140, 240), (140, 80)], 2)], "park")
    t.mark(55, 250, "Headlands Park")
    # the harbour: breakwater off the headland, basins, island, boatyard
    _swalk(t, [(150, 380), (380, 360), (620, 330), (760, 270)], 16, "breakwater")
    t.street([(180, 40), (800, 40)], "street")
    for k in range(12):
        t.bld(t.rect(200 + k * 30, 222 + k * 30, 48, 74), "store")
    t.mark(380, 88, "Mariners Village")
    for (u0, u1) in ((200, 410), (570, 780)):
        _swalk(t, [(u0, wv + 30), (u1, wv + 30)], 3, "dock")
        for u in range(u0 + 10, u1, 22):
            _swalk(t, [(u, wv + 30), (u, wv + 85)], 1.5, "dock")
    t.land.append(t.rect(430, 550, wv + 40, wv + 110))
    _swalk(t, [(490, 80), (490, wv + 40)], 10, "bridge")
    t.bld(t.rect(440, 500, wv + 50, wv + 100), "hotel")
    t.bld(t.rect(510, 545, wv + 55, wv + 95), "civic")
    t.mark(490, wv + 125, "Harbor Island")
    t.bld(t.rect(700, 790, 48, 100), "boatyard")
    _swalk(t, [(680, 60), (680, wv + 30)], 12, "ramp")
    t.mark(745, 112, "Shipyard")
    _pier(t, 185, 90, wv + 120, 5)
    # the Lantern District on the bluff
    ls = [200, 290, 380, 470, 560, 650, 740]
    t.grid(ls, [-60, -150, -240, -330])
    t.street([(470, 40), (470, -380)], "main")
    t.mark(470, -400, "Golden Lantern")
    for (v0, v1) in ((-68, -142), (-158, -232)):
        _stores_v(t, v0, v1, 470, -1, 3)
        _stores_v(t, v0, v1, 470, 1, 3)
    for i in range(6):
        t.houses(ls[i], ls[i + 1], -240, 1, 3, kind="house")
        t.houses(ls[i], ls[i + 1], -240, -1, 3, kind="house")
        t.houses(ls[i], ls[i + 1], -330, 1, 3, kind="house")
    t.bld(t.rect(210, 330, -8, -52), "hotel")
    t.bld(t.rect(600, 720, -8, -52), "hotel")
    return t


def build_victory_bay():
    # Put-in-Bay on South Bass Island, Lake Erie's western basin: a village round its harbour -- ferry
    # and marina docks, the waterfront park (DeRivera Park), a strip of bars and shops, the
    # Perry's Victory column on the isthmus, cottages, a winery, a lighthouse on the western point
    s0, x0 = LAKE_S - 706.0, -600.0                  # (on Perry Island, 706 m west of the lake's middle)
    t = Town("Victory Bay", "Village", 900, "Island resort", "Great Lakes island village (Put-in-Bay)", s0, x0, "s", 1, "up")
    t.coastal = True
    t.water_v = 45
    isle = chaikin([(-330, 60), (-360, -80), (-280, -250), (-120, -330), (80, -320), (240, -260),
                    (330, -140), (360, 10), (300, 70), (180, 50), (60, 75), (-80, 60), (-200, 80)], 3, closed=True)
    t.land.append([t.g(u, v) for u, v in isle])
    t.street([(-230, 0), (230, 0)], "street")
    _pier(t, -60, 40, 140, 14, kind="wharf")
    t.mark(-60, 155, "Ferry Dock")
    for k in range(6):
        _swalk(t, [(30 + k * 26, 44), (30 + k * 26, 110)], 3, "dock")
    t.area(t.rect(-40, 90, -8, -46), "park")
    t.mark(25, -28, "Waterfront Park")
    t.street([(-200, -70), (200, -70)], "main")
    t.stores(-200, 200, -70, 1, 8, dmin=16, dmax=20, kind="store")
    t.stores(-200, 200, -70, -1, 8, dmin=16, dmax=22, kind="store")
    t.mark(0, -110, "Bars & shops (Delaware Ave)")
    t.bld(circle(*t.g(270, -40), 9, 16), "monument")
    t.mark(270, -70, "Perry's Victory Column")
    for u in (-240, -150, -60, 30, 120):
        t.street([(u, -70), (u, -230)], "street")
    t.street([(-240, -150), (120, -150)], "street")
    t.street([(-240, -230), (120, -230)], "street")
    for (u0, u1) in ((-240, -150), (-150, -60), (-60, 30), (30, 120)):
        t.houses(u0, u1, -150, 1, 2, kind="cottage")
        t.houses(u0, u1, -150, -1, 2, kind="cottage")
        t.houses(u0, u1, -230, 1, 2, kind="cottage")
    t.bld(t.rect(150, 230, -150, -200), "store")
    t.mark(190, -210, "Winery")
    t.bld(circle(*t.g(-330, -40), 4, 10), "lighthouse")
    t.mark(-330, -70, "West Point Light")
    t.bld(t.rect(-220, -170, -20, -50), "civic")
    t.mark(-195, -60, "Town Hall")
    return t


def add_harrow_falls_waterfront(t):
    # the boardwalk along the lakefront and the pier (research/coastal_communities/boardwalks_and_piers.md)
    _swalk(t, [(-440, -46), (440, -46)], 10, "boardwalk")
    _pier(t, 45.5, -46, -376, 10, head=(64, 26))
    t.bld(t.rect(25, 66, -8, -40), "pavilion")
    t.mark(45.5, -24, "Pier Pavilion")
    for v in (-120, -200):
        for du in (-11, 7):
            _wb(t, 45.5 + du, 45.5 + du + 4, v - 4, v, "kiosk")
    _wb(t, 37.5, 53.5, -244, -256, "pavilion")
    _wb(t, 54, 60, -262, -268, "bait")
    _wb(t, 31, 37, -262, -266, "shed")
    _wb(t, 58, 74, -380, -398, "restaurant")
    _wb(t, 17, 30, -380, -394, "civic")
    t.wbldgs.append((circle(*t.g(45.5, -389), 5, 12), "pavilion"))
    _swalk(t, [(45.5, -402), (45.5, -414)], 6, "dock")
    t.mark(45.5, -430, "Harrow Falls Pier")


def add_cedar_ford_boardwalk(t):
    # across the Kettle River's marsh basin to the river: a boardwalk, a viewing / fishing platform,
    # a marsh-edge loop and a small nature centre
    _swalk(t, [(0, -8), (0, -318)], 5, "boardwalk")
    _deck(t, -14, 14, -318, -340)
    _swalk(t, [(-150, -48), (150, -48)], 4, "boardwalk")
    t.bld(t.rect(-160, -136, -52, -70), "civic")
    t.mark(0, -360, "Kettle Marsh Boardwalk")


def build_all():
    towns = [build_harrow_falls(), build_kessler(), build_marlowe(), build_bellhaven(),
             build_fenwick(), build_tamarack()]
    # villages -------------------------------------------------------------
    s_cf = 1250.0 * SS
    # Cedar Ford: mill village, core within one block of the Kettle (§7 village rule, 1-in-3/4
    # villages are water-founded); "Water St." is the first street back from the bank (§8)
    top_edge = rxf(s_cf) - OLD_BANK                 # the draft's bank: the village stays put; the basin lies below it
    cf = build_village("Cedar Ford", 1150, "Water/mill-founded", "Stable ag / manufacturing",
                       s_cf, top_edge - 62, "s", -1, 4, "up", vs=(0, 91, 182),
                       school="Cedar Ford-Pruett Consol.")
    cf.stores(-91, 0, 0, -1, 2)
    cf.bld(cf.rect(20, 52, -12, -42), "industrial")
    cf.mark(36, -27, "Grist Mill")
    cf.mark(-60, 0, "Water St.")
    pr = build_village("Pruett", 820, "Rail-founded", "Stable ag / manufacturing",
                       1500.0 * SS, rail_x(1500.0 * SS) - 80, "s", -1, 4, "down", vs=(-55, 0, 91),
                       elevator=True, depot=True, x0_3km=rail_x3(1500.0 * SS) - 80)
    du = build_village("Dunmore Crossing", 480, "Inland / crossroads", "Stable ag / manufacturing",
                       650.0 * SS, XS(-800.0 - WIDEN), "x", 1, 3, "up", x0_3km=-800.0 - WIDEN)
    lo = build_village("Loomis Grove", 390, "Inland / crossroads", "Declining rust-belt",
                       2580.0 * SS, XS(-1250.0 - WIDEN), "s", 1, 3, "down", vacant=0.5, x0_3km=-1250.0 - WIDEN)
    ha = build_village("Haskins Corner", 2600, "Inland / trail", "Growing exurban",
                       2955.0 * SS, XS(-640.0 - WIDEN), "s", 1, 8, "up", vs=(-182, -91, 0, 91, 182), blocks=3,
                       school="Haskins Elem. + Jr. High", carnegie=True, x0_3km=-640.0 - WIDEN)
    ha.subdivision(0, -290, 105, 48, (0, -182))
    return towns + [cf, pr, du, lo, ha]


# Calder (the user, 2026-10-06): a whole town generated from the research rules (tools/settlegen/town.py, calder.py) --
# every building its own catalog record (tools/settlegen/records.py), written by --game-data below
def build_calder():
    import calder as CAL
    t = Town("Calder", "Town", 7000, "Rail-founded", "Stable ag / the southland's hospital town", CAL.S0, CAL.X0, "s", -1, "up")
    p = CAL.plan(lambda u, v: is_water(*t.g(u, v), buf=True))
    uv = lambda poly: [t.g(u, v) for u, v in poly]
    for st in p["streets"]:
        t.street(st["pts"], st["cls"], st["name"])
    for a in p["areas"]:
        t.area(uv(a["poly"]), a["kind"])
    for c in p["centres"]:
        f = (lambda c_: (lambda u, v: (u, c_["v_road"] + c_["dirn"] * v)))(c)
        # (the centre's own lanes -- aisles, fire lane, entry drives, service lane -- stay part of its paved lot,
        #  not town streets: as streets they boxed the store rows in and placement left the rows out)
        for a in c["plan"]["areas"]:
            t.area(uv([f(*q) for q in a["poly"]]), a["kind"])
    for (q, txt) in p["marks"]:
        t.mark(q[0], q[1], txt)
    # the three countryside centres round it (07: at rural crossroads and the coast highway junction)
    import town as TW
    rnd = random.Random(CAL.CFG["seed"] + 3)

    def coast_road_x(s_):
        w_, line_, off_ = site_weight(np.array([s_]), 1)
        return float(coast(np.array([s_]), 1)[0] - (300.0 * w_[0] + off_[0] * (1 - w_[0])))
    country = []
    for (name, kind, s_c, x_road, dirn, era) in ((CAL.NAMES["country"][0], "convenience", CAL.SECTION_S + 80.0, coast_road_x(CAL.SECTION_S + 80.0), -1, 1988),
                                                  (CAL.NAMES["country"][1], "neighborhood", CAL.SECTION_S - 1609.0 - 175.0, XS(1800.0), 1, 1974),
                                                  (CAL.NAMES["country"][2], "convenience", CAL.SECTION_S + 1609.0 + 80.0, XS(1800.0), 1, 1996)):
        c = TW.country_centre(kind, name, rnd)
        c["era"] = era
        frame = (lambda sc, xr, dn: (lambda u, v: (sc + u, xr + dn * v)))(s_c, x_road, dirn)
        for a in c["plan"]["areas"]:
            t.area([frame(*q) for q in a["poly"]], a["kind"])
        t.marks.append((frame(0.0, -30.0), name))
        country.append((c, frame))
    t.calder_structs = CAL.structures(p, country)
    for e in t.calder_structs:
        t.bld(e["poly"], CAL.KIND.get(e["use"], "store"))
    t.density = 1.0
    return t


TOWNS = build_all()

# No buildings are added or lost in the expansion: each community's structures are exactly those of
# the current map (remake/inventory/map_inventory_pre_expansion.json -- same ids, same footprints), moved as a
# piece with its town: 6x further round the ring, 500 m further from the river.
OLD_S0 = {"Harrow Falls": 395.0, "Kessler": 2130.0, "Marlowe": 1500.0, "Fenwick": 2150.0, "Bellhaven": 1050.0,
          "Tamarack": 2820.0, "Cedar Ford": 1250.0, "Pruett": 1500.0, "Dunmore Crossing": 650.0,
          "Loomis Grove": 2580.0, "Haskins Corner": 2955.0}
import json as _json
# (read from the frozen pre-expansion copy: --game-data rewrites map_inventory.json at the new positions)
_INV = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remake", "inventory",
                                    "map_inventory_pre_expansion.json")))


def _inv_poly(st, ds, dx):
    if st.get("front_edge"):
        p0, p1 = st["front_edge"]
        cs, cx = st["s"], st["x"]
        pts = [tuple(p0), tuple(p1), (2 * cs - p0[0], 2 * cx - p0[1]), (2 * cs - p1[0], 2 * cx - p1[1])]
    else:
        pts = circle(st["s"], st["x"], st["w"] / 2, 14)
    return [(q[0] + ds, q[1] + dx) for q in pts]


for _t in TOWNS:
    _ds = OLD_S0[_t.name] * (SS - 1)
    _dx = (-WIDEN if _t.x0 < 0 else WIDEN) + (_t.x0 - _t.x0_3km)     # (the town's move into the new land too)
    _t.bldgs = []
    for _st in _INV["structures"]:
        if _st["settlement"] != _t.name:
            continue
        _t.bldgs.append((_inv_poly(_st, _ds, _dx), _st["kind"], False))
        for _pt in _st["parts"]:
            _t.bldgs.append((_inv_poly(_pt, _ds, _dx), "silo", True))

_TN = {t.name: t for t in TOWNS}
add_harrow_falls_waterfront(_TN["Harrow Falls"])
add_cedar_ford_boardwalk(_TN["Cedar Ford"])
TOWNS += [build_port_carrow(), build_tern_harbor(), build_brightwater(), build_haven_point(),
          build_solana_point(), build_pelican_cove(), build_playa_verde(), build_oceanview(), build_victory_bay(),
          build_port_tamsin(), build_calder()]

# harbour water cut into the land, and land built out into the water (the Battery, a headland,
# Harbor Island): painted into the water raster
def _poly_mask(polys):
    im = Image.new("L", (CW, WH), 0)
    d_ = ImageDraw.Draw(im)
    for poly in polys:
        draw_poly(d_, poly, fill=1)
    return np.array(im) > 0


_LANDM = _poly_mask([p_ for t in TOWNS for p_ in t.land])
WCAT[_LANDM & ((WCAT == 6) | (WCAT == 2) | (WCAT == 1))] = 0
WCAT[_poly_mask([p_ for t in TOWNS for p_ in t.water])] = 7       # 7 harbour / channel
WBUF = dilate(WCAT > 0, fk(4))

# ------------------------------------------------------------------ global roads
ROADS = []   # (pts, cls, name)


def road(pts, cls, name="", smooth=2, closed=False):
    if smooth:
        pts = chaikin(pts, smooth, closed)
    if closed:
        pts = pts + [pts[0]]
    ROADS.append((densify(pts, 6.0), cls, name))


T = {t.name: t for t in TOWNS}
# SR 14 -- port-side loop through the port-side settlements' main streets
sr14 = [T["Dunmore Crossing"].g(0, 0), P(900, -780), T["Marlowe"].g(0, 0), P(1830, -760),
        T["Fenwick"].g(-182, 0), T["Fenwick"].g(182, 0), P(2600, -720), T["Haskins Corner"].g(0, 0),
        (C + 450 * KS, XS(-1400)), (C + 1100 * KS, XS(-2200)), (C + 2500 * KS, XS(-2300)), (C + 3500 * KS, XS(-1750))]
road([(p[0], p[1]) for p in sr14] + [(T["Dunmore Crossing"].g(0, 0)[0] + C, T["Dunmore Crossing"].g(0, 0)[1])], "hwy", "SR 14",
     smooth=2)
# US 30 -- starboard loop; bypasses Harrow Falls' downtown along the bluff-top street
hf = T["Harrow Falls"]
us30 = [hf.g(-420, 455), hf.g(420, 455), P(820, 770), T["Bellhaven"].g(-182, 0), T["Bellhaven"].g(182, 0),
        T["Calder"].g(-760, 0), T["Calder"].g(1060, 0),
        T["Pruett"].g(-91, 0), T["Pruett"].g(91, 0), T["Kessler"].g(-430, 0), T["Kessler"].g(330, 0),
        P(2520, 880), T["Tamarack"].g(-182, 0), T["Tamarack"].g(182, 0), P(3142 - 80, 900),
        (hf.g(-420, 455)[0] + C, hf.g(-420, 455)[1])]
road(us30, "hwy", "US 30", smooth=2)
# river crossings -- a handful of big bridges (§10: small crossings must outnumber these)
# (each crossing of the widened river is a new ~1 km bridge)
road([hf.g(-227.5, 91), P(80, 380), P(-160, 340), P(-160, -300), P(-200, -620)], "county", "Lakeshore Rd", 2)
road([P(650, -700), P(930, -380), P(930, 380), P(900, 740)], "county", "Outlet Rd", 2)
# (Ford Rd's river bridge lands at Calder's River Rd since Calder was built, 2026-10-06; it once ran on across
#  that farmland to Bellhaven -- Calder's streets and US 30 carry it on now)
import calder as _CAL  # noqa: E402
road([T["Cedar Ford"].g(0, 0), P(1250, 300), T["Calder"].g(_CAL.GRID_U0, 760.0)], "county", "Ford Rd", 2)   # (River Rd's north end)
road([T["Marlowe"].g(182, 0), P(1610, 200), T["Pruett"].g(0, 91)], "county", "Brannock Pike", 2)
road([T["Fenwick"].g(91, 182), P(2270, 250), T["Kessler"].g(91, 364)], "county", "College Rd", 2)
# the coast roads: round each sea, through every coastal town on its shore road (Ocean Rd on the
# North Sea; the Coast Highway on the South Sea, PCH-style)
for _sg, _cls, _nm in ((-1, "county", "Ocean Rd"), (1, "hwy", "Coast Hwy")):
    _ss = np.arange(0.0, C + 1.0, 120.0)
    _w, _line, _off = site_weight(_ss, _sg)
    _ro = 300.0 * _w + _off * (1 - _w)
    _cst = coast(_ss, _sg)
    _pl = [(float(a), _sg * float(c - r)) for a, c, r in zip(_ss, _cst, _ro)]
    # round the ring and back to its start: the last 600 m ease onto the start's line, so the loop
    # closes without a jog at the seam
    _gap = _pl[0][1] - _pl[-1][1]
    _pl = [(a, x + _gap * max(0.0, 1.0 - (C - a) / 600.0) ** 2) for a, x in _pl] + [(C, _pl[0][1])]
    road(_pl, _cls, _nm, smooth=1)
# connectors from the coastal cities and lake town to the highways
_pc, _sp, _pt, _hp = T["Port Carrow"], T["Solana Point"], T["Port Tamsin"], T["Haven Point"]
road([_pc.g(182, -660), (_pc.g(182, -660)[0] + 60, XS(-2200)), P(1830, -760)], "county", "Carrow Pike", 2)
road([_sp.g(-420, -450), (_sp.g(-420, -450)[0] + 80, XS(2300)), (_sp.g(-420, -450)[0] + 300, XS(1600))], "county", "Main St Ext.", 2)
road([_pt.g(0, -180), (_pt.g(0, -180)[0], XS(-2280))], "county", "Tamsin Rd", 1)
road([_hp.g(195, -210), (_hp.g(195, -210)[0] + 40, XS(-2300)), (_hp.g(195, -210)[0] + 150, XS(-1500))], "county", "Haven Rd", 2)

# settlement footprints (for clipping section roads / farmland)
# Built-up area = the settlement's own streets/buildings/lots grown by ~25 m (organic edge,
# unlike a convex hull that swallows farmland between an L-shaped layout's arms).
FOOT, TMASK = {}, {}                 # TMASK: name -> (i0, j0, mask of its window)
fp_acc = np.zeros((WH, CW), bool)
for t in TOWNS:
    pts = t.geometry_points()
    s_lo, s_hi = min(p[0] for p in pts) - 80, max(p[0] for p in pts) + 80
    x_lo, x_hi = min(p[1] for p in pts) - 80, max(p[1] for p in pts) + 80
    i0, j0 = int(s_lo * K), max(0, int((x_lo + HW) * K))
    i1, j1 = int(s_hi * K) + 1, min(WH, int((x_hi + HW) * K) + 1)
    m = Image.new("L", (i1 - i0, j1 - j0), 0)
    md = ImageDraw.Draw(m)
    tp = lambda q: ((q[0] * K) - i0, (q[1] + HW) * K - j0)
    for p, cls in t.streets:
        md.line([tp(q) for q in p], fill=255, width=max(1, int(12 * K)))
    for p, _, _ in t.bldgs:
        md.polygon([tp(q) for q in p], fill=255)
    for p, _ in t.areas:
        md.polygon([tp(q) for q in p], fill=255)
    tm = erode(dilate(np.array(m) > 0, fk(20)), fk(10))
    TMASK[t.name] = (i0, j0, tm)
    ii = np.arange(i0, i1) % CW
    fp_acc[j0:j1][:, ii] |= tm
    FOOT[t.name] = pts
FP = fp_acc
fp_buf = dilate(FP, fk(30))

# floodplain / bluff terrain (§8/§16) -----------------------------------------
th = S / R
b = np.tanh(1.5 * np.sin(6 * th + PHI1)) / np.tanh(1.5)
b = b * (1 - T_L) + 1.0 * T_L                 # lake: bluff on the +x (Harrow Falls) shore
side = np.where(X < CX_L, -1.0, 1.0).astype(np.float32)
dist = np.where(X < TOP_E, TOP_E - X, np.where(X > BOT_E, X - BOT_E, 0.0)).astype(np.float32)
w_cut = (0.5 * (1 + b * side)).astype(np.float32)
del side                                       # (the 20 km ring's rasters are 88 M px: float64 temporaries go early)
d0_cut = 60 * (1 - T_L) + 140 * T_L
d0 = (230 - (230 - d0_cut) * w_cut + BASIN * (1 - T_L)).astype(np.float32)   # the valley walls stand back past the basin
Lb = (160 - 85 * w_cut).astype(np.float32)
H = H_BLUFF * (1 + 0.3 * np.sin(2 * th + PHI4))
ELEV = (H * np.maximum(0, np.tanh((dist - d0) / Lb)) - Z1 * np.cos(th - math.pi / 4)
        + 1.2 * np.sin(S / 97 + X / 131) + 0.8 * np.sin(X / 53 - S / 211)).astype(np.float32)
del Lb, H
ELEV_INLAND = ELEV.copy()                                        # (woods follow the inland slopes only)
# the coasts: distance inland from each sea's waterline; headlands (proud of the mean line, outside
# the towns' straightened stretches) end in rocky cliffs, the bays in sandy beaches
_wn, _, _ = site_weight(S[0], -1)
_ws, _, _ = site_weight(S[0], 1)
def _headw(amp, lo, hi, w):
    t_ = np.clip((amp - lo) / (hi - lo), 0, 1)
    return (t_ * t_ * (3 - 2 * t_)) * np.clip((w - 0.8) / 0.2, 0, 1)
def _amp_big(s_, sg):
    # the headlands' large-scale shape only (the coast's small ripples don't make or unmake a cliff)
    ph = 0.0 if sg < 0 else 2.1
    return (140 * np.sin(TAU * s_ / 2600 + ph) + 95 * np.sin(TAU * s_ / 1130 + 2 * ph + 0.7)
            + 55 * np.sin(TAU * s_ / 610 + ph + 2.0))
HEADW_N = _headw(_amp_big(S[0], -1), 40, 110, _wn)[None, :].astype(np.float32)     # 0..1: how much a headland
HEADW_S = _headw(_amp_big(S[0], 1), 130, 210, _ws)[None, :].astype(np.float32)    # (the South Sea: mostly beaches)
HEAD_N = HEADW_N > 0.5
HEAD_S = HEADW_S > 0.5
DCOAST = np.where(X < 0, COAST_N + X, COAST_S - X)                 # metres inland of the waterline
HEADLAND = np.where(X < 0, HEAD_N, HEAD_S)
_u = np.clip(DCOAST / 400.0, 0.0, 1.0)
_u = _u * _u * (3 - 2 * _u)
_hw = np.where(X < 0, HEADW_N, HEADW_S)
ELEV = (_hw * (ELEV + 22.0 * (1 - np.clip(DCOAST / 500.0, 0, 1))) + (1 - _hw) * ELEV * _u).astype(np.float32)
del _hw
_rv = dilate(RIVMASK, fk(RIVER_BASIN))                                    # the great rivers' valleys
ELEV = np.where(_rv, ELEV * 0.15, np.where(dilate(_rv, fk(260)), ELEV * 0.55, ELEV)).astype(np.float32)
del _rv
# the islands: beaches round a low rolling upland (to ~14-22 m), cut into the sea by DCOAST like the mainland's coasts
_isn = (1.6 * np.sin(S / 173 + X / 211) + 1.1 * np.sin(X / 97 - S / 139) + 0.6 * np.sin(S / 41 + X / 59)).astype(np.float32)
_isu = np.clip(ISL_D / 450.0, 0, 1)
_isu = _isu * _isu * (3 - 2 * _isu)
ELEV = np.where(ISL, 0.6 + 16.0 * _isu + _isn * _isu, ELEV).astype(np.float32)
DCOAST = np.where(ISL, ISL_D, DCOAST)
HEADLAND = HEADLAND & ~ISL
del _isn, _isu
del _u
WATER = WCAT > 0
BASIN_M = (~WATER) & (dist > 0) & (dist < BASIN) & (T_L < 0.5)          # the river's wide basin
_rb = dilate(RIVMASK, fk(RIVER_BASIN))
BASIN_M |= _rb & ~WATER                                                   # and the great rivers' basins
FLOOD = ((~WATER) & (dist < d0 * 0.85) & (w_cut < 0.5) & (dist > 0)) | BASIN_M
MARSH = (BASIN_M & (dist < BASIN * 0.55)) | (dilate(RIVMASK, fk(55)) & ~WATER)
del d0, BASIN_M, _rb
BEACH = (~WATER) & (DCOAST > 0) & (DCOAST < 75) & ~HEADLAND
CLIFF = (~WATER) & (DCOAST > 0) & (DCOAST < 24) & HEADLAND


def in_blocked(s, x, buf=False):
    i, j = idx(s, x)
    if is_sea(s, x + (30 if x > 0 else -30)):
        return True
    return (fp_buf if buf else FP)[j, i]


# Section-line county roads (Midwest PLSS grid, compressed ~3.5x per the KCD "adjusted
# realistic map" rule, §17).  They stop at the bluff/floodplain unless they're a bridge road.
SECTION_S = list(np.arange(180 * SS, C, 1609.0))          # a 1-mile grid round the ring
SECTION_X = [XS(-1250 - WIDEN), XS(1300 + WIDEN), XS(-SHORE3 + 450), XS(SHORE3 - 450)]


_GRB = dilate(RIVMASK, fk(RIVER_BASIN + 40))


def near_great_river(s, x):
    """In a great river or its basin: section roads stop here (the highways and county roads bridge it)."""
    i, j = idx(s, x)
    return _GRB[j, i]


def clip_runs(pts, bad):
    runs, cur = [], []
    for p in pts:
        if bad(p):
            if len(cur) > 1:
                runs.append(cur)
            cur = []
        else:
            cur.append(p)
    if len(cur) > 1:
        runs.append(cur)
    return runs


def near_river(p):
    top, bot = water_edges(p[0])
    return float(top) - 150 < p[1] < float(bot) + 150


_CREEK_NEAR = dilate((WCAT == 3) | (WCAT == 4), fk(10))


def _creek_run(pts):
    """How much of a line lies along a creek (a section road must cross creeks, not follow one)."""
    n = 0
    for p in pts:
        i, j = idx(*p)
        n += bool(_CREEK_NEAR[j, i])
    return n


def big_water(s, x):
    """Sea, harbour, the great rivers and the lake -- what a section road stops at (a creek it bridges)."""
    i, j = idx(s, x)
    return is_sea(s, x) or WCAT[j, i] in (1, 2, 7)


for s in SECTION_S:
    # the surveyed line, nudged (as a real section road jogs) off any creek that runs along it
    best = None
    for off in (0.0, 25.0, -25.0, 45.0, -45.0, 65.0, -65.0):
        pts = densify([(s + off, -COAST_MEAN - 300), (s + off, COAST_MEAN + 300)], 3.0)
        sc = _creek_run(pts)
        if best is None or sc < best[0] - 12:
            best = (sc, pts)
    for run in clip_runs(best[1], lambda p: near_river(p) or in_blocked(*p) or near_great_river(*p)):
        if math.dist(run[0], run[-1]) > 60:
            ROADS.append((run, "gravel", ""))
for x in SECTION_X:
    pts = densify([(0, x), (C, x)], 3.0)
    for run in clip_runs(pts, lambda p: in_blocked(*p) or big_water(*p)):
        if math.dist(run[0], run[-1]) > 60:
            ROADS.append((run, "gravel", ""))

# Every road end joins another road (SSC road standard §6: tools/road_network.py) -- the roads and
# every town's streets as one network; an end with nowhere to go gets a turning circle
from road_network import Network
_bi = Image.new("L", (CW, WH), 0)
_bd = ImageDraw.Draw(_bi)
for t in TOWNS:
    for poly, _, _ in t.bldgs:
        draw_poly(_bd, poly, fill=1)
_BLD = dilate(np.array(_bi) > 0, fk(3))
del _bi, _bd


def _road_clear(s, x):
    i, j = idx(s, x)
    return not (_BLD[j, i] or big_water(s, x))


_NET_ROADS = [[list(pts), cls, nm] for pts, cls, nm in ROADS]
_NET_TOWN = []
for t in TOWNS:
    for k, (p, cls) in enumerate(t.streets):
        _NET_TOWN.append((t, k, len(_NET_ROADS)))
        _NET_ROADS.append([densify(list(p), 6.0), cls, t.street_names.get(k, "")])
_culs = [(sum(q[0] for q in poly) / len(poly), sum(q[1] for q in poly) / len(poly))
         for t in TOWNS for poly, kind in t.areas if kind == "culdesac"]
_net = Network(_NET_ROADS, C, _road_clear, {"hwy": 12, "county": 8, "gravel": 6, "main": 11, "street": 7, "alley": 3}, _culs)
_net.join_all(["hwy", "county", "main", "street", "gravel", "alley"])
_n_town0 = len(_NET_ROADS)
_net.connect_islands(name_of=lambda p: min(TOWNS, key=lambda t: math.dist(t.g(0, 0), p)).name + " Rd")
ROADS[:] = [(r[0], r[1], r[2]) for r in _NET_ROADS[:len(ROADS)]] + [(r[0], r[1], r[2]) for r in _NET_ROADS[_n_town0:]]
for t, k, n in _NET_TOWN:
    t.streets[k] = (_NET_ROADS[n][0], _NET_ROADS[n][1])
TURNS = _net.turns
print(f"road network: {_net.log}", file=sys.stderr)

# Rail -- one closed loop on the starboard side (rail-spine towns + Pruett + Kessler sit on it)
RAIL = [(s, rail_x(s)) for s in np.arange(0, C + 5, 5.0)]

# ------------------------------------------------------------------ road mask / building filter
ROAD_W = {"hwy": 12, "county": 8, "gravel": 6, "main": 11, "street": 7, "alley": 3}
rm_img = Image.new("L", (CW, WH), 0)
rmd = ImageDraw.Draw(rm_img)
for pts, cls, _ in ROADS:
    draw_line(rmd, pts, fill=1, width=ROAD_W[cls] + 2)
draw_line(rmd, RAIL, fill=1, width=8)
RMASK = np.array(rm_img) > 0


def bld_ok(poly):
    cs = sum(p[0] for p in poly) / len(poly)
    cx = sum(p[1] for p in poly) / len(poly)
    # each corner tested 3 m in from itself: the masks are 4 m pixels, and a building at its set-back from a
    # road would otherwise touch the road's pixel
    def _in(p):
        d = math.hypot(p[0] - cs, p[1] - cx)
        k = min(3.0, d * 0.5) / d if d > 0 else 0.0
        return (p[0] + (cs - p[0]) * k, p[1] + (cx - p[1]) * k)
    for p in [_in(q) for q in poly] + [(cs, cx)]:
        i, j = idx(*p)
        if WBUF[j, i] or RMASK[j, i] or is_sea(*p):
            return False
    return True


dropped = 0                       # kept regardless (they're the current map's): counted as conflicts
CONFLICTS = []
for t in TOWNS:
    if t.coastal or t.name in ("Harrow Falls", "Cedar Ford"):
        # new buildings (the coastal towns, the new waterfront pieces) are laid out fresh: any that
        # land on water or a road are dropped
        continue
    for (poly, kind, part) in t.bldgs:
        if not part and not bld_ok(poly):
            dropped += 1
            CONFLICTS.append((t.name, kind, poly[0]))
NEW_DROPPED = 0
for t in TOWNS:
    if not t.coastal:
        continue
    keep = []
    for b_ in t.bldgs:
        if b_[2] or bld_ok(b_[0]):
            keep.append(b_)
        else:
            NEW_DROPPED += 1
            if "--why" in sys.argv:
                _c = (sum(q[0] for q in b_[0]) / len(b_[0]), sum(q[1] for q in b_[0]) / len(b_[0]))
                _i, _j = idx(*_c)
                print(f"   DROP {t.name} {b_[1]} at s={_c[0]:.0f} x={_c[1]:.0f}: water={bool(WBUF[_j, _i])} "
                      f"road={bool(RMASK[_j, _i])} sea={is_sea(*_c)}", file=sys.stderr)
    t.bldgs = keep

# ------------------------------------------------------------------ farmland: fields, ditches, farmsteads
FARM = (~FP) & (~WATER) & (~FLOOD) & (~BEACH) & (~CLIFF) & (~ISL)
rng_np = np.random.default_rng(7)
# Farmland, organically (research/coastal_communities -- and Iowa / Illinois practice): the PLSS
# mile-square SECTIONS the section roads outline, each split by its owners into quarters (160 ac),
# halves (80 ac) or forties (40 ac); corn and soybeans in rotation on most of it, hay, pasture,
# small grain and set-aside (CRP) grass on the rest; contour strips on the slopes; an occasional
# centre pivot; woodlots in odd corners and windbreak tree lines along some boundaries.
SEC = 1609.0
SEC_S0, SEC_X0 = 180.0 * SS, XS(1300.0 + WIDEN)    # the grid the section roads run on


def _h(a, b_, c_):
    hh = (a.astype(np.int64) * 73856093) ^ (b_.astype(np.int64) * 19349663) ^ (np.int64(c_) * 83492791 if np.isscalar(c_) else c_.astype(np.int64) * 83492791)
    hh = (hh ^ (hh >> 13)) * 1274126177
    return (hh ^ (hh >> 16)) & 0x7FFFFFFF


# terrain splits: some quarters are farmed as bottom land and upland, the line following the ground
_ec = ELEV[::16, ::16].astype(np.float32)
for _ax in (0, 1):
    for _i in range(3):
        _ec = (np.roll(_ec, 4, _ax) + np.roll(_ec, -4, _ax) + np.roll(_ec, 8, _ax) + np.roll(_ec, -8, _ax) + _ec) / 5


def _farm_band(r0, r1):
    """the farmland of raster rows r0..r1 (in bands: done whole, its int64 hashes alone outgrow the Deck's memory)"""
    _su = (S.astype(np.float64) - SEC_S0) / SEC
    _sx = (X[r0:r1].astype(np.float64) - SEC_X0) / SEC
    SEC_I = np.broadcast_to(np.floor(_su), (r1 - r0, CW)).astype(np.int32)
    SEC_J = np.broadcast_to(np.floor(_sx), (r1 - r0, CW)).astype(np.int32)
    _u = np.broadcast_to(_su - np.floor(_su), (r1 - r0, CW)).astype(np.float32)
    _v = np.broadcast_to(_sx - np.floor(_sx), (r1 - r0, CW)).astype(np.float32)
    # the section roads stay straight, but the owners' lines inside a section wander (old fence rows
    # bent round wet spots, knolls and the creeks) -- a smooth warp that vanishes at the section roads
    _Sf = np.broadcast_to(S, (r1 - r0, CW)).astype(np.float32)
    _Xf = np.broadcast_to(X[r0:r1], (r1 - r0, CW)).astype(np.float32)
    _wu = (0.045 * np.sin(_Xf / 173.0 + 1.3) + 0.03 * np.sin(_Xf / 71.0 + _Sf / 263.0)) * np.sin(math.pi * _u)
    _wv = (0.045 * np.sin(_Sf / 191.0 + 0.4) + 0.03 * np.sin(_Sf / 67.0 - _Xf / 241.0)) * np.sin(math.pi * _v)
    del _Sf, _Xf
    _uw = np.clip(_u + _wu, 0, 0.9999)
    _vw = np.clip(_v + _wv, 0, 0.9999)
    del _wu, _wv
    _q = ((_uw >= 0.5).astype(np.int32) * 2 + (_vw >= 0.5))
    _uq = (_uw * 2) % 1.0
    _vq = (_vw * 2) % 1.0
    del _uw, _vw
    # bilinear back up to full resolution, a band of rows at a time (a blocky upsample saw-tooths the lines)
    _low = np.empty((r1 - r0, CW), bool)
    _fx = np.arange(CW, dtype=np.float32) / 16.0
    _x0 = np.minimum(_fx.astype(np.int32), _ec.shape[1] - 1)
    _x1 = np.minimum(_x0 + 1, _ec.shape[1] - 1)
    _tx = _fx - _x0
    for _r in range(r0, r1):
        _fy = _r / 16.0
        _y0 = min(int(_fy), _ec.shape[0] - 1)
        _y1 = min(_y0 + 1, _ec.shape[0] - 1)
        _ty = _fy - _y0
        _row = (_ec[_y0, _x0] * (1 - _tx) + _ec[_y0, _x1] * _tx) * (1 - _ty) + (_ec[_y1, _x0] * (1 - _tx) + _ec[_y1, _x1] * _tx) * _ty
        _low[_r - r0] = ELEV[_r] < _row - 0.3
    del _fx, _x0, _x1, _tx
    _mode = _h(SEC_I, SEC_J, _q) % 100
    _sub = np.where(_mode < 18, 0, np.where(_mode < 34, 1 + (_uq >= 0.5), np.where(_mode < 50, 3 + (_vq >= 0.5),
                   np.where(_mode < 72, 9 + _low, 5 + (_uq >= 0.5) * 2 + (_vq >= 0.5)))))
    del _low
    PARCEL = _h(SEC_I, SEC_J, _q * 16 + _sub)
    del _mode
    _pc = PARCEL % 100
    CROP = np.select([_pc < 38, _pc < 72, _pc < 80, _pc < 88, _pc < 94], [0, 1, 3, 4, 2], 5).astype(np.uint8)   # 0 corn 1 soy 2 grain 3 hay 4 pasture 5 CRP
    # centre pivots: a circle of crop, the quarter's corners left to grass
    _piv = (_h(SEC_I, SEC_J, _q + 50) % 100) < 4
    _rp = np.hypot(_uq - 0.5, _vq - 0.5)
    CROP = np.where(_piv & (_rp > 0.48), np.uint8(4 + (_pc % 2)), np.where(_piv, np.uint8(_pc % 2), CROP))
    # contour strips where the ground slopes: row crop and hay alternating along the contours
    _ra, _rb_ = max(0, r0 - 1), min(WH, r1 + 1)
    _gy, _gx = [g_[r0 - _ra:r0 - _ra + (r1 - r0)] for g_ in np.gradient(ELEV[_ra:_rb_], PX)]
    _slope = np.hypot(_gx, _gy)
    del _gy, _gx
    _strip = (_slope > 0.035) & (CROP <= 1) & ~_piv
    CROP = np.where(_strip & ((np.floor(ELEV[r0:r1] / 1.6).astype(np.int32) % 2) == 1), np.uint8(3), CROP)
    del _slope, _strip
    VARIANT = ((PARCEL >> 8) % 4).astype(np.uint8)
    ROWS_S = ((PARCEL >> 12) & 1).astype(bool)
    FIELD_G = (CROP + 8 * VARIANT).astype(np.uint8)
    # woodlots in some quarters' outer corners, and windbreak tree lines along some section / quarter lines
    _wl = (_h(SEC_I, SEC_J, _q + 99) % 100) < 7
    _cu = np.where(_uq < 0.5, 0.18, 0.82)
    _cv = np.where(_vq < 0.5, 0.18, 0.82)
    _wob = 1 + 0.18 * np.sin(np.arctan2(_vq - _cv, _uq - _cu) * 3 + (PARCEL % 7))
    WOODLOT = _wl & (np.hypot((_uq - _cu) * 1.3, _vq - _cv) < 0.2 * _wob)
    del _wl, _cu, _cv, _wob
    _du = np.minimum(np.abs(_u - 0.5), np.minimum(_u, 1 - _u)) * SEC            # metres to the nearest s-running line
    _dv = np.minimum(np.abs(_v - 0.5), np.minimum(_v, 1 - _v)) * SEC
    _line_s = np.round(_su * 2).astype(np.int32)
    _line_x = np.round(_sx * 2).astype(np.int32)
    HEDGE = ((_du < 4.0) & ((_h(np.broadcast_to(_line_s, (r1 - r0, CW)), SEC_J, 7) % 100) < 30)) | \
            ((_dv < 4.0) & ((_h(SEC_I, np.broadcast_to(_line_x, (r1 - r0, CW)), 11) % 100) < 30))
    del _du, _dv, _line_s, _line_x, _u, _v, _uq, _vq, _q, _rp, _pc, _su, _sx
    CROP_COLS = np.array([[96, 142, 52], [168, 196, 88], [222, 196, 118], [132, 188, 96], [150, 170, 108], [180, 170, 120]], np.float32)
    _var = np.array([0.9, 0.97, 1.03, 1.1], np.float32)
    _rowc = np.where(ROWS_S, np.broadcast_to(S, (r1 - r0, CW)), np.broadcast_to(X[r0:r1], (r1 - r0, CW)))
    _rowm = 1 + 0.035 * np.sin(_rowc * (TAU / 7.0)) * (CROP <= 2)
    FIELDC = np.clip(CROP_COLS[CROP] * (_var[VARIANT] * _rowm)[..., None], 0, 255).astype(np.uint8)
    del _rowc, _rowm
    return CROP, FIELD_G, FIELDC, WOODLOT, HEDGE


CROP = np.zeros((WH, CW), np.uint8)
FIELD_G = np.zeros((WH, CW), np.uint8)
FIELDC = np.zeros((WH, CW, 3), np.uint8)
WOODLOT = np.zeros((WH, CW), bool)
HEDGE = np.zeros((WH, CW), bool)
for _b0 in range(0, WH, 400):
    _b1 = min(WH, _b0 + 400)
    CROP[_b0:_b1], FIELD_G[_b0:_b1], FIELDC[_b0:_b1], WOODLOT[_b0:_b1], HEDGE[_b0:_b1] = _farm_band(_b0, _b1)
del _ec
fid = FIELD_G

# ditches: parallel to the ring (along s) at the field-band edges, each draining into the
# nearest named creek (field ditch -> creek -> river, never ditch straight into the river)
dt_img = Image.new("L", (CW, WH), 0)
ddr = ImageDraw.Draw(dt_img)
DITCHES = []
for name, path, pond in CREEK_PATHS:
    xs = [p[1] for p in path]
    lo, hi = min(xs), max(xs)
    for xb in np.arange(-HW + 160, HW, 160.0):
        if not (lo + 30 < xb < hi - 30):
            continue
        near = min(path, key=lambda p: abs(p[1] - xb))
        for dirn in (-1, 1):
            if rng.random() < 0.15:
                continue
            length = rng.uniform(170, 380)
            pts = densify([(near[0] + dirn * 8, xb), (near[0] + dirn * length, xb)], 3.0)
            run = []
            for p in pts:
                i, j = idx(*p)
                if not FARM[j, i] or RMASK[j, i] and len(run) > 40:
                    break
                run.append(p)
            if len(run) > 20:
                DITCHES.append(run)
                draw_line(ddr, run, fill=1, width=3)
DT = np.array(dt_img) > 0
WCAT[DT & (WCAT == 0)] = 5

FARMSTEADS = []
tries = 0
while len(FARMSTEADS) < 34 and tries < 20000:
    tries += 1
    pts, cls, _ = rng.choice([r for r in ROADS if r[1] in ("gravel", "county", "hwy")])
    p = rng.choice(pts)
    horiz = abs(pts[-1][1] - pts[0][1]) < abs(pts[-1][0] - pts[0][0])
    off = rng.choice((-1, 1)) * rng.uniform(30, 45)
    c = (p[0], p[1] + off) if horiz else (p[0] + off, p[1])
    if any(math.dist(c, f) < 900 for f in FARMSTEADS):
        continue
    ok = True
    for ds in (-45, 0, 45):
        for dx in (-45, 0, 45):
            i, j = idx(c[0] + ds, c[1] + dx)
            if not FARM[j, i] or fp_buf[j, i] or WBUF[j, i] or (RMASK[j, i] and (ds or dx) == 0):
                ok = False
    if ok:
        FARMSTEADS.append(c)


def farmstead_polys(c):
    s, x = c
    sg = 1 if rng.random() < 0.5 else -1
    return [
        ([(s - 6, x - 5), (s + 6, x - 5), (s + 6, x + 5), (s - 6, x + 5)], "house"),
        ([(s + 18, x - 9 * sg), (s + 40, x - 9 * sg), (s + 40, x + 18 * sg), (s + 18, x + 18 * sg)], "barn"),
        (circle(s + 48, x + 4 * sg, 4.5, 10), "silo"),
        ([(s - 30, x + 12 * sg), (s - 12, x + 12 * sg), (s - 12, x + 32 * sg), (s - 30, x + 32 * sg)], "shed"),
    ]


# ------------------------------------------------------------------ raster composite
print("compositing terrain...", file=sys.stderr)
img = np.zeros((WH, CW, 3), np.uint8)
# irregular pasture paddocks round every farmstead (behind the buildings, following no grid)
_pd = Image.new("L", (CW, WH), 0)
_pdd = ImageDraw.Draw(_pd)
for k_, c_ in enumerate(FARMSTEADS):
    rr = 90 + 50 * ((k_ * 37) % 7) / 6
    pts_ = [(c_[0] + (rr + 25 * math.sin(a_ * 3 + k_)) * math.cos(a_), c_[1] + (rr * 0.7 + 20 * math.sin(a_ * 2 + k_)) * math.sin(a_))
            for a_ in np.linspace(0, TAU, 24, endpoint=False)]
    draw_poly(_pdd, pts_, fill=1)
PADDOCK = (np.array(_pd) > 0) & FARM
del _pd
CROP[PADDOCK] = 4
FIELD_G[PADDOCK] = 4 + 8 * 2
FIELDC[PADDOCK] = (140, 168, 98)
img[:] = FIELDC
img[FLOOD] = (212, 230, 195)
img[MARSH] = (178, 208, 172)
img[MARSH & (rng_np.random((WH, CW), dtype=np.float32) < 0.25)] = (140, 180, 150)
img[BEACH] = (240, 226, 180)
img[CLIFF] = (150, 140, 126)
# woods: riparian strips along creeks, steep bluff faces, never on settlements/fields' roads
gy, gx = np.gradient(ELEV_INLAND, PX)
slope = np.hypot(gx, gy)
del ELEV_INLAND
gy, gx = np.gradient(ELEV, PX)
creek_band = dilate((WCAT == 3) | (WCAT == 4), fk(9))
WOODS = (((slope > 0.11) & (w_cut > 0.5)) | creek_band | ((WOODLOT | HEDGE) & FARM)) & ~WATER & ~FP & ~RMASK
_isw = ISL & (ISL_D > 90) & ((np.sin(S / 157 + X / 233) + np.sin(X / 119 - S / 181) + 0.7 * np.sin(S / 61)) > 0.6)
WOODS |= _isw & ~RMASK                                                   # (the islands: woods in clumps over meadow)
img[ISL & ~BEACH & ~WOODS] = (212, 230, 195)
img[WOODS] = (134, 173, 109)
speck = rng_np.random((WH, CW), dtype=np.float32) < 0.10
img[WOODS & speck] = (96, 140, 78)
img[FP] = (236, 231, 221)
wcols = {1: (93, 159, 216), 2: (93, 159, 216), 3: (90, 154, 214), 4: (91, 155, 213), 5: (104, 160, 214),
         6: (66, 128, 196), 7: (78, 140, 204)}
for k, col in wcols.items():
    img[WCAT == k] = col
# hillshade (NW light, 5x vertical exaggeration) + 4 m contours -- in row bands (the 20 km ring: 88 M px)
ex = 5.0
lx, ly, lz = -0.5, -0.5, 0.707
_foot = (WCAT == 6) & dilate(CLIFF, fk(10)) & (rng_np.random((WH, CW), dtype=np.float32) < 0.18)
img[_foot] = (96, 92, 86)
del _foot, slope
for _b0 in range(0, WH, 400):
    _b1 = min(WH, _b0 + 400)
    nx, ny = -gx[_b0:_b1] * ex, -gy[_b0:_b1] * ex
    shade = (nx * lx + ny * ly + lz) / np.sqrt(nx * nx + ny * ny + 1.0)
    shade = np.clip(0.80 + 0.55 * (shade - 0.707), 0.55, 1.12)
    shade[WATER[_b0:_b1]] = 1.0
    img[_b0:_b1] = np.clip(img[_b0:_b1] * shade[..., None], 0, 255).astype(np.uint8)
del gx, gy, nx, ny, shade
band = np.floor(ELEV / 4.0).astype(np.int16)
cont = np.zeros_like(WATER)
cont[:, 1:] |= band[:, 1:] != band[:, :-1]
cont[1:, :] |= band[1:, :] != band[:-1, :]
del band
cont &= ~WATER & ~FP
img[cont] = (img[cont] * 0.6 + np.array([140, 110, 70]) * 0.4).astype(np.uint8)

layer = Image.fromarray(img, "RGB")
dr = ImageDraw.Draw(layer)

# ------------------------------------------------------------------ vector layers
AREA_COL = {"park": (170, 214, 145), "square": (190, 226, 165), "lawn": (205, 229, 186),
            "promenade": (178, 220, 150), "schoolground": (214, 232, 196), "sportsfield": (150, 200, 118),
            "parking": (200, 200, 200), "lot": (212, 210, 204), "cemetery": (190, 212, 170),
            "campus": (208, 230, 190), "culdesac": (250, 250, 250),
            "beach": (242, 230, 188), "plaza": (228, 222, 210), "pool": (120, 196, 232)}
for t in TOWNS:
    for poly, kind in t.areas:
        draw_poly(dr, poly, fill=AREA_COL[kind], outline=(150, 150, 140) if kind in ("parking", "lot") else None)
        if kind == "cemetery":
            cs = sum(p[0] for p in poly) / 4
            cx = sum(p[1] for p in poly) / 4
            for k in range(24):
                a, b_ = cs + rng.uniform(-45, 45), cx + rng.uniform(-60, 60)
                draw_line(dr, [(a - 2, b_), (a + 2, b_)], fill=(110, 120, 100), width=1)
                draw_line(dr, [(a, b_ - 3), (a, b_ + 3)], fill=(110, 120, 100), width=1)
for c in FARMSTEADS:   # windbreak grove behind each farmstead
    draw_ellipse(dr, c[0] - 8, c[1], 26, fill=(120, 160, 98))

# roads: casing pass, bridge pass, fill pass
CASE = {"hwy": (140, 88, 20), "county": (150, 130, 80), "gravel": (176, 156, 108), "main": (130, 130, 130),
        "street": (160, 160, 160), "alley": (185, 180, 170)}
FILL = {"hwy": (245, 180, 60), "county": (255, 240, 190), "gravel": (234, 220, 180), "main": (255, 255, 255),
        "street": (252, 252, 250), "alley": (222, 218, 210)}
ALL_ROADS = [(pts, cls) for pts, cls, _ in ROADS]
for t in TOWNS:
    ALL_ROADS += [(densify(p, 3.0), c) for p, c in t.streets]
order = ["alley", "gravel", "street", "county", "main", "hwy"]
ALL_ROADS.sort(key=lambda r: order.index(r[1]))

# --- bridge / culvert detection: walk every road and the rail over the water raster
BRIDGES = {"major": [], "small": [], "culvert": [], "rail": []}
CREEK_XING = {name: 0 for name, _, _ in CREEK_PATHS}


def scan(pts, cls, is_rail=False):
    d = densify(pts, PX)
    run = []
    for p in d + [None]:
        cat = 0
        if p is not None:
            i, j = idx(*p)
            cat = WCAT[j, i]
        if cat:
            run.append((p, cat, CID[j, i] if cat in (3, 4) else 0))
        elif run:
            cats = {r[1] for r in run}
            a, b_ = run[0][0], run[-1][0]
            if is_rail:
                BRIDGES["rail"].append((a, b_))
            elif cats & {1, 2}:
                BRIDGES["major"].append((a, b_, cls))
            elif cats & {3, 4}:
                BRIDGES["small"].append((a, b_, cls))
            else:
                BRIDGES["culvert"].append((a, b_, cls))
            for cid in {r[2] for r in run if r[2]}:
                CREEK_XING[CREEK_PATHS[cid - 1][0]] += 1
            run = []


for pts, cls in ALL_ROADS:
    if cls != "alley":
        scan(pts, cls)
scan(RAIL, "rail", is_rail=True)

for pts, cls in ALL_ROADS:
    draw_line(dr, pts, fill=CASE[cls], width=ROAD_W[cls] + (2 if cls != "alley" else 0), joint="curve")
for a, b_, cls in BRIDGES["major"]:
    draw_line(dr, [a, b_], fill=(25, 25, 25), width=ROAD_W[cls] + 8)
for a, b_, cls in BRIDGES["small"]:
    draw_line(dr, [a, b_], fill=(60, 60, 60), width=ROAD_W[cls] + 5)
for pts, cls in ALL_ROADS:
    draw_line(dr, pts, fill=FILL[cls], width=ROAD_W[cls], joint="curve")
for a, b_, r_, cls in TURNS:
    draw_ellipse(dr, a, b_, r_, fill=FILL[cls])
for a, b_, cls in BRIDGES["culvert"]:
    m = ((a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2)
    draw_ellipse(dr, m[0], m[1], 2.2, fill=(40, 70, 120))
# rail: black line with white dashes
draw_line(dr, RAIL, fill=(40, 40, 40), width=5)
for k in range(0, len(RAIL) - 1, 2):
    draw_line(dr, [RAIL[k], RAIL[k + 1]], fill=(250, 250, 250), width=2)
for a, b_ in BRIDGES["rail"]:
    draw_line(dr, [a, b_], fill=(20, 20, 20), width=11)
    draw_line(dr, [a, b_], fill=(40, 40, 40), width=5)

# waterfront: decks, walks (boardwalks, piers, docks, breakwaters...), then buildings over the water
WALK = {"boardwalk": ((120, 84, 50), (184, 140, 92)), "pier": ((110, 78, 48), (176, 132, 86)),
        "wharf": ((100, 72, 44), (160, 120, 80)), "promenade": ((150, 140, 125), (232, 222, 200)),
        "dock": ((90, 66, 42), (168, 128, 84)), "breakwater": ((80, 78, 74), (140, 136, 128)),
        "catwalk": ((150, 20, 20), (205, 50, 45)), "crossover": ((70, 70, 70), (130, 130, 130)),
        "railway": ((40, 40, 40), (90, 90, 90)), "bridge": ((90, 90, 90), (200, 200, 200)),
        "ramp": ((120, 120, 120), (190, 190, 190))}
DECK_COL = {"deck": (176, 132, 86), "amusement": (232, 200, 120)}
for t in TOWNS:
    for poly, kind in t.decks:
        draw_poly(dr, poly, fill=DECK_COL[kind], outline=(110, 78, 48))
for t in TOWNS:
    for pts, w, kind in t.walks:
        case, fill = WALK[kind]
        draw_line(dr, pts, fill=case, width=w + 2)
for t in TOWNS:
    for pts, w, kind in t.walks:
        case, fill = WALK[kind]
        draw_line(dr, pts, fill=fill, width=w)

# buildings
BCOL = {"house": (118, 100, 84), "store": (165, 70, 58), "vacant": (222, 212, 205), "civic": (47, 85, 151),
        "church": (111, 66, 160), "school": (217, 130, 43), "industrial": (88, 88, 88), "silo": (150, 160, 165),
        "tower": (61, 111, 143), "bigbox": (192, 96, 58), "strip": (200, 120, 80), "barn": (168, 50, 42),
        "shed": (138, 138, 122),
        "hotel": (214, 120, 150), "motel": (236, 150, 190), "arcade": (240, 180, 40), "stand": (250, 210, 90),
        "cottage": (150, 120, 96), "bungalow": (160, 128, 96), "beachhouse": (170, 150, 120), "condo": (190, 160, 170),
        "rowhouse": (230, 110, 120), "singlehouse": (200, 170, 120), "shingle": (132, 132, 128),
        "cannery": (70, 90, 110), "warehouse": (100, 110, 120), "fishhouse": (120, 120, 110), "icehouse": (160, 190, 210),
        "boatyard": (110, 100, 90), "lighthouse": (220, 40, 40), "pavilion": (250, 245, 230), "restaurant": (200, 90, 60),
        "lifeguard": (240, 60, 40), "market": (190, 150, 110), "stack": (60, 60, 60), "ride": (230, 80, 160),
        "kiosk": (240, 200, 90), "bait": (90, 140, 90), "monument": (235, 232, 220),
        "townhouse": (215, 120, 110)}
for t in TOWNS:
    for poly, kind, _ in t.bldgs:
        draw_poly(dr, poly, fill=BCOL[kind], outline=(40, 30, 25) if kind != "vacant" else (140, 70, 60))
FS_POLYS = []          # what was drawn, per farmstead (farmstead_polys draws its side at random)
for t in TOWNS:
    for poly, kind in t.wbldgs:
        draw_poly(dr, poly, fill=BCOL[kind], outline=(40, 30, 25))
for c in FARMSTEADS:
    FS_POLYS.append(farmstead_polys(c))
    for poly, kind in FS_POLYS[-1]:
        draw_poly(dr, poly, fill=BCOL[kind], outline=(40, 30, 25))

# ------------------------------------------------------------------ labels (on the layer)
FD = "/usr/share/fonts/noto/"


def font(name, size):
    return ImageFont.truetype(FD + name, size)


F_CITY, F_TOWN, F_VIL = font("NotoSerif-Bold.ttf", 110), font("NotoSerif-Bold.ttf", 80), font("NotoSerif-Bold.ttf", 60)
F_SUB = font("NotoSans-Italic.ttf", 34)
F_MARK = font("NotoSans-Regular.ttf", 17)
F_WATER = font("NotoSerif-Italic.ttf", 44)
F_CREEK = font("NotoSans-Italic.ttf", 30)


def text(dr_, xy, s, f, fill, anchor="mm", halo=(255, 255, 255), sw=4):
    for o in OFFS:
        dr_.text(((xy[0] + o) * K, (xy[1] + HW) * K), s, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=halo)


for t in TOWNS:
    for (p, txt) in t.marks:
        text(dr, p, txt, F_MARK, (30, 30, 30), sw=3)

for name, path, pond in CREEK_PATHS:
    p = path[len(path) // 4]
    text(dr, (p[0] + 30, p[1]), name, F_CREEK, (30, 80, 150), anchor="lm", sw=3)
for name, poly in OXBOW_POLYS:
    cs = sum(p[0] for p in poly) / len(poly)
    cx = sum(p[1] for p in poly) / len(poly)
    text(dr, (cs, cx + (40 if cx > rxf(cs) else -40)), name, F_CREEK, (30, 80, 150), sw=3)
text(dr, (LAKE_S + 250, -1000), "LAKE TAMSIN", F_CITY, (25, 70, 140), halo=(200, 225, 245))
text(dr, (LAKE_S - 706.0, -300), "PERRY ISLAND", F_WATER, (25, 70, 140), halo=(200, 225, 245))
for _nm, _pth in RIVER_PATHS:
    _p = _pth[len(_pth) // 2]
    text(dr, _p, _nm.upper(), F_TOWN, (25, 70, 140), halo=(225, 238, 250))
for s in (1150, 1700, 2450, 2900):
    text(dr, (s * SS, rxf(s * SS)), "KETTLE RIVER", F_CITY, (25, 70, 140), halo=(225, 238, 250))
for s in (2000, 7000, 12000, 17000):
    text(dr, (s * KS, -HW + 900), "NORTH SEA", F_CITY, (235, 245, 255), halo=(40, 90, 150))
    text(dr, (s * KS, HW - 900), "SOUTH SEA", F_CITY, (235, 245, 255), halo=(40, 90, 150))
for _nm, _sg, _sc, _xc, _hs, _hx in ISLANDS:
    text(dr, (_sc, _xc), _nm.upper(), F_TOWN, (40, 60, 30), halo=(225, 238, 215))
text(dr, P(1060, 1080), "C&NW Railroad", F_CREEK, (40, 40, 40), sw=3)
text(dr, P(2400, -660), "SR 14", F_SUB, (140, 88, 20), sw=3)
text(dr, P(2560, 915), "US 30", F_SUB, (140, 88, 20), sw=3)

for t in TOWNS:
    xs = [p[0] for p in FOOT[t.name]]
    ys = [p[1] for p in FOOT[t.name]]
    cs = (min(xs) + max(xs)) / 2
    f = {"City": F_CITY, "Town": F_TOWN, "Village": F_VIL}[t.tier]
    sub = f"{t.tier} · pop. {t.pop:,} · {t.founding}"
    if t.label == "up":
        y = min(ys) - 44 - (f.size * 0.62 + F_SUB.size) * PX
        text(dr, (cs, y), t.name.upper() if t.tier == "City" else t.name, f, (20, 20, 20), sw=6)
        text(dr, (cs, y + (f.size * 0.62 + F_SUB.size * 0.8) * PX), sub, F_SUB, (60, 60, 60), sw=4)
    else:
        y = max(ys) + 30 + f.size * 0.55 * PX
        text(dr, (cs, y), t.name.upper() if t.tier == "City" else t.name, f, (20, 20, 20), sw=6)
        text(dr, (cs, y + (f.size * 0.62 + F_SUB.size * 0.8) * PX), sub, F_SUB, (60, 60, 60), sw=4)

# ------------------------------------------------------------------ page: title, frame, legend
M_L, M_T, M_B, LEG = 70, 200, 150, 820
page = Image.new("RGB", (M_L + CW + 40 + LEG, M_T + WH + M_B), (246, 243, 236))
page.paste(layer, (M_L, M_T))
pd = ImageDraw.Draw(page)
F_T = font("NotoSerif-Bold.ttf", 64)
F_T2 = font("NotoSans-Regular.ttf", 26)
F_L = font("NotoSans-Regular.ttf", 24)
F_LB = font("NotoSans-Bold.ttf", 26)
F_S = font("NotoSans-Regular.ttf", 21)
pd.text((M_L, 40), "Goblin Engine — Expanded Station Overhead Map (DRAFT for approval)", font=F_T, fill=(25, 25, 25))
pd.text((M_L, 125), f"Radius {R / 1000:.0f} km · ring unrolled: {C:,.0f} m circumference (left/right edges join) × {W:,.0f} m wall "
        f"to wall · 1 px = {PX:.0f} m · communities spaced {SS:.0f}× round the ring · each land 2.5 km wider · "
        f"{SEA / 1000:.1f} km seas at the end caps, three islands in each (tools/map_expanded.py)", font=F_T2, fill=(70, 70, 70))
pd.rectangle([M_L - 2, M_T - 2, M_L + CW + 1, M_T + WH + 1], outline=(30, 30, 30), width=3)
# walls + seam annotations
pd.text((M_L + CW / 2, M_T - 22), "NORTH END-CAP CLIFFS — Marlowe end  (x = −6,000 m)", font=F_LB, fill=(90, 90, 90), anchor="mm")
pd.text((M_L + CW / 2, M_T + WH + 26), "SOUTH END-CAP CLIFFS — Kessler end  (x = +6,000 m)", font=F_LB, fill=(90, 90, 90), anchor="mm")
for k in range(0, 19000, 1000):
    xx = M_L + k * K
    if k * K <= CW:
        pd.line([xx, M_T + WH, xx, M_T + WH + 10], fill=(30, 30, 30), width=2)
        pd.text((xx, M_T + WH + 58), f"s={k:,} m", font=F_S, fill=(90, 90, 90), anchor="mm")
pd.text((M_L - 10, M_T + WH / 2), "◀ seam", font=F_S, fill=(90, 90, 90), anchor="rm")
# scale bar
sx, sy = M_L + 40, M_T + WH + 95
pd.rectangle([sx, sy, sx + 1000 * K, sy + 12], outline=(20, 20, 20), width=2)
pd.rectangle([sx, sy, sx + 500 * K, sy + 12], fill=(20, 20, 20))
pd.text((sx + 1000 * K + 20, sy + 6), "1 km", font=F_S, fill=(20, 20, 20), anchor="lm")

# legend ----------------------------------------------------------------------
lx, ly = M_L + CW + 50, M_T
pd.text((lx, ly), "Legend", font=F_T2, fill=(20, 20, 20))
ly += 50


def leg_line(label, fill, case, w):
    global ly
    pd.line([lx, ly + 12, lx + 70, ly + 12], fill=case, width=w + 2)
    pd.line([lx, ly + 12, lx + 70, ly + 12], fill=fill, width=w)
    pd.text((lx + 90, ly + 12), label, font=F_L, fill=(30, 30, 30), anchor="lm")
    ly += 38


def leg_box(label, fill, outline=(40, 30, 25)):
    global ly
    pd.rectangle([lx + 20, ly + 2, lx + 50, ly + 24], fill=fill, outline=outline)
    pd.text((lx + 90, ly + 12), label, font=F_L, fill=(30, 30, 30), anchor="lm")
    ly += 38


leg_line("US / State highway", FILL["hwy"], CASE["hwy"], 12)
leg_line("County road (paved)", FILL["county"], CASE["county"], 8)
leg_line("Section road (gravel)", FILL["gravel"], CASE["gravel"], 6)
leg_line("Main Street", FILL["main"], CASE["main"], 10)
leg_line("Local street / alley", FILL["street"], CASE["street"], 6)
pd.line([lx, ly + 12, lx + 70, ly + 12], fill=(40, 40, 40), width=5)
for k in range(0, 70, 10):
    pd.line([lx + k, ly + 12, lx + k + 5, ly + 12], fill=(250, 250, 250), width=2)
pd.text((lx + 90, ly + 12), "Railroad", font=F_L, fill=(30, 30, 30), anchor="lm")
ly += 38
leg_line("Major bridge (river / lake)", FILL["county"], (25, 25, 25), 14)
leg_line("Small bridge (creek / pond)", FILL["street"], (60, 60, 60), 11)
pd.ellipse([lx + 30, ly + 7, lx + 40, ly + 17], fill=(40, 70, 120))
pd.text((lx + 90, ly + 12), "Culvert (road over farm ditch)", font=F_L, fill=(30, 30, 30), anchor="lm")
ly += 44
leg_box("River / lake / pond", wcols[1], None)
leg_box("Sea (end caps) / harbour", wcols[6], None)
leg_box("Sandy beach", (240, 226, 180), None)
leg_box("Rocky cliffs (headlands)", (150, 140, 126), None)
leg_box("River basin marsh", (178, 208, 172), None)
leg_line("Boardwalk / pier / wharf", WALK["boardwalk"][1], WALK["boardwalk"][0], 10)
leg_line("Breakwater / jetty", WALK["breakwater"][1], WALK["breakwater"][0], 10)
leg_line("Creek (named) / farm ditch", wcols[3], wcols[5], 5)
leg_box("Floodplain (park, not buildable)", (212, 230, 195), None)
leg_box("Woods (bluff faces, creek banks)", (134, 173, 109), None)
leg_box("Cropland (field patchwork)", (205, 220, 143), None)
leg_box("Built-up area", (236, 231, 221), (180, 180, 170))
leg_box("Park / square / promenade", AREA_COL["park"], None)
pd.text((lx + 90, ly + 12), "Contours every 4 m, hillshade 5×", font=F_L, fill=(30, 30, 30), anchor="lm")
pd.line([lx + 10, ly + 12, lx + 60, ly + 12], fill=(160, 130, 90), width=2)
ly += 50
for label, k in (("House", "house"), ("Storefront", "store"), ("Vacant / derelict", "vacant"),
                 ("Civic (hall, courthouse, library...)", "civic"), ("Church", "church"), ("School", "school"),
                 ("Industrial / mill / elevator", "industrial"), ("Highway commercial", "bigbox"),
                 ("Barn (farmstead)", "barn"), ("Hotel / motel", "hotel"), ("Arcade / boardwalk stand", "arcade"),
                 ("Cottage / beach house", "cottage"), ("Row house (Rainbow Row)", "rowhouse"),
                 ("Cannery / fish house", "cannery"), ("Lighthouse / lifeguard stand", "lighthouse"),
                 ("Pavilion / bandshell", "pavilion")):
    leg_box(label, BCOL[k], (140, 70, 60) if k == "vacant" else (40, 30, 25))

# stats
ly += 20
pd.text((lx, ly), "Settlements (lore population)   structures", font=F_LB, fill=(20, 20, 20))
ly += 44
total = 0
for t in sorted(TOWNS, key=lambda t: ("City", "Town", "Village").index(t.tier)):
    n = sum(1 for _, _, part in t.bldgs if not part) + len(t.wbldgs)
    total += n
    pd.text((lx, ly), f"{t.name}", font=F_LB, fill=(20, 20, 20))
    pd.text((lx + LEG - 70, ly), f"{n}", font=F_LB, fill=(20, 20, 20), anchor="ra")
    ly += 30
    pd.text((lx + 16, ly), f"{t.tier}, {t.pop:,} — {t.archetype}", font=F_S, fill=(80, 80, 80))
    ly += 32
nfs = len(FARMSTEADS)
pd.text((lx, ly + 6), f"Farmsteads: {nfs} (x4 bldgs)   Total structures: {total + nfs * 4}", font=F_LB, fill=(20, 20, 20))
ly += 50
pd.text((lx, ly), f"Bridges: {len(BRIDGES['major'])} major · {len(BRIDGES['small'])} small creek "
        f"· {len(BRIDGES['rail'])} rail", font=F_S, fill=(60, 60, 60))
ly += 30
pd.text((lx, ly), f"Culverts: {len(BRIDGES['culvert'])} · Creeks: {len(CREEK_PATHS) - len(CROSS_PATHS)} + {len(CROSS_PATHS)} cross · "
        f"Ponds/oxbows: {sum(1 for c in CREEK_PATHS if c[2]) + len(OXBOWS)}", font=F_S, fill=(60, 60, 60))

out = sys.argv[1] if len(sys.argv) > 1 else "station_map.png"
page.save(out)

# ------------------------------------------------------------------ validation report
print(f"saved {out}  {page.size}")
print(f"structures: {total} in settlements + {nfs} farmsteads; {dropped} sit on water / a road now "
      f"(new coastal buildings dropped on water/roads: {NEW_DROPPED}):")
for name, kind, q in CONFLICTS:
    print(f"   CONFLICT {name} {kind} at s={q[0]:.0f} x={q[1]:.0f}")
for t in TOWNS:
    n = sum(1 for _, _, part in t.bldgs if not part) + len(t.wbldgs)
    xs = [p[0] for p in FOOT[t.name]]
    ys = [p[1] for p in FOOT[t.name]]
    print(f"  {t.name:17s} {t.tier:8s} {n:4d} bldgs  s {min(xs):7.0f}..{max(xs):7.0f}  x {min(ys):6.0f}..{max(ys):6.0f}")
names = list(FOOT)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        a0, b0, ma = TMASK[names[i]]
        a1, b1, mb = TMASK[names[j]]
        full_a = np.zeros((WH, CW), bool)
        if abs(a0 - a1) * PX > 3000:
            continue
        full_a[b0:b0 + ma.shape[0]][:, np.arange(a0, a0 + ma.shape[1]) % CW] = ma
        ov = int(full_a[b1:b1 + mb.shape[0]][:, np.arange(a1, a1 + mb.shape[1]) % CW][mb].sum() * PX * PX)
        if ov:
            print(f"  OVERLAP {names[i]} / {names[j]}: {ov} m^2")
print("bridges:", {k: len(v) for k, v in BRIDGES.items()})
for a, b_, cls in BRIDGES["major"]:
    print(f"  major {cls:7s} s={a[0]:.0f} x={a[1]:.0f} len={math.dist(a, b_):.0f}")
print("creek crossings (roads+rail, need >=2):", CREEK_XING)

# ------------------------------------------------------------------ inventory export
# `--inventory FILE`: every structure on the map as JSON, the master list the building /
# bridge research works from (remake/inventory/).
# `--coastal-inventory FILE`: the NEW structures only (the coastal communities, the Harrow Falls and
# Cedar Ford waterfront pieces, every boardwalk / pier / wharf / breakwater, the great bridges) -- the
# list the coastal catalog works from (remake/inventory/coastal_inventory.json).  The game's own
# inventory (map_inventory.json) is untouched.
PREFIX = {"Port Carrow": "PCR", "Solana Point": "SOL", "Tern Harbor": "TRN", "Pelican Cove": "PEL",
          "Brightwater": "BRW", "Haven Point": "HVN", "Playa Verde": "PLV", "Oceanview": "OCV",
          "Port Tamsin": "PTM", "Victory Bay": "VBY", "Harrow Falls": "HFW", "Cedar Ford": "CFW"}
COAST_OF = {"Port Carrow": "east", "Tern Harbor": "east", "Brightwater": "east", "Haven Point": "east",
            "Solana Point": "west", "Pelican Cove": "west", "Playa Verde": "west", "Oceanview": "west",
            "Port Tamsin": "greatlakes", "Victory Bay": "greatlakes", "Harrow Falls": "greatlakes", "Cedar Ford": "greatlakes"}
if "--coastal-inventory" in sys.argv:
    import json

    def _info(poly):
        cs = sum(p_[0] for p_ in poly) / len(poly)
        cx = sum(p_[1] for p_ in poly) / len(poly)
        if len(poly) == 4:
            w = math.dist(poly[0], poly[1])
            d = math.dist(poly[1], poly[2])
            ang = math.degrees(math.atan2(poly[1][1] - poly[0][1], poly[1][0] - poly[0][0]))
            fe = [[round(poly[0][0], 1), round(poly[0][1], 1)], [round(poly[1][0], 1), round(poly[1][1], 1)]]
        else:
            r_ = max(math.dist((cs, cx), p_) for p_ in poly)
            w = d = 2 * r_
            ang, fe = 0.0, None
        return {"s": round(cs % C, 1), "x": round(cx, 1), "w": round(w, 1), "d": round(d, 1),
                "angle_deg": round(ang, 1), "front_edge": fe}

    OLD_IDS = {st_["settlement"]: 0 for st_ in _INV["structures"]}
    ci = {"settlements": [], "structures": [], "walks": [], "bridges": []}
    for t in TOWNS:
        if t.name not in PREFIX:
            continue
        pre = PREFIX[t.name]
        new_town = t.coastal
        if new_town:
            ci["settlements"].append({"name": t.name, "tier": t.tier, "pop": t.pop, "founding": t.founding,
                                      "archetype": t.archetype, "coast": COAST_OF[t.name], "id_prefix": pre})
        # land buildings: all of a new town's; for Harrow Falls / Cedar Ford only the pieces added now
        n = 0
        items = []
        if new_town:
            items = [(poly, kind, False) for poly, kind, part in t.bldgs if not part]
        else:
            old_n = sum(1 for st_ in _INV["structures"] if st_["settlement"] == t.name)
            mains = [(poly, kind) for poly, kind, part in t.bldgs if not part]
            items = [(poly, kind, False) for poly, kind in mains[old_n:]]
        items += [(poly, kind, True) for poly, kind in t.wbldgs]
        for poly, kind, over_water in items:
            n += 1
            inf = _info(poly)
            best, label = 40.0, None
            for p_, txt in t.marks:
                dd = math.dist(p_, (inf["s"], inf["x"])) if abs(p_[0] - inf["s"]) < C / 2 else 1e9
                if dd < best:
                    best, label = dd, txt
            ci["structures"].append({"id": f"{pre}-{n:03d}", "settlement": t.name, "coast": COAST_OF[t.name],
                                     "kind": kind, "label": label, "over_water": over_water, **inf})
        for k, (pts, w, kind) in enumerate(t.walks, 1):
            ci["walks"].append({"id": f"{pre}-W{k:02d}", "settlement": t.name, "coast": COAST_OF[t.name], "kind": kind,
                                "width_m": w, "pts": [[round(a % C, 1), round(b_, 1)] for a, b_ in pts],
                                "length_m": round(sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)), 1)})
        for k, (poly, kind) in enumerate(t.decks, 1):
            inf = _info(poly)
            ci["walks"].append({"id": f"{pre}-D{k:02d}", "settlement": t.name, "coast": COAST_OF[t.name], "kind": kind + "_deck", **inf})
    for k, (a, b_, cls) in enumerate(BRIDGES["major"], 1):
        s_m, x_m = (a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2
        i, j = idx(s_m, x_m)
        over = "Kettle River" if abs(x_m - rxf(s_m)) < 400 else ("Maumee River" if x_m < 0 else "Miami River")
        ci["bridges"].append({"id": f"XBR-{k:02d}", "road_class": cls, "over": over, "s": round(s_m % C, 1), "x": round(x_m, 1),
                              "water_span_m": round(math.dist(a, b_), 1),
                              "ends": [[round(a[0] % C, 1), round(a[1], 1)], [round(b_[0] % C, 1), round(b_[1], 1)]]})
    for k, (a, b_) in enumerate(BRIDGES["rail"], 1):
        s_m, x_m = (a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2
        if math.dist(a, b_) > 60:
            ci["bridges"].append({"id": f"XRR-{k:02d}", "road_class": "rail", "over": "Miami River", "s": round(s_m % C, 1),
                                  "x": round(x_m, 1), "water_span_m": round(math.dist(a, b_), 1)})
    out_ci = sys.argv[sys.argv.index("--coastal-inventory") + 1]
    with open(out_ci, "w") as f:
        json.dump(ci, f, indent=1)
    print(f"coastal inventory: {len(ci['structures'])} structures, {len(ci['walks'])} walks/decks, "
          f"{len(ci['bridges'])} great bridges -> {out_ci}")

# `--game-data`: the approved map into the game (godot_project/remake/): the terrain as rasters the
# game samples directly (so it matches this map exactly), land cover, the terrain.json features, and
# the inventory (every existing structure at its new place under its own id, the farmsteads, every
# crossing with the existing bridge model that fits it).
if "--game-data" in sys.argv:
    import gzip
    import json
    GD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "godot_project", "remake")
    for _v in ("img", "FIELDC", "layer", "page", "CROP", "HEDGE", "WOODLOT", "w_cut", "ISL_D", "DCOAST", "cont", "speck"):
        globals().pop(_v, None)                      # (the drawing's rasters: the 20 km ring needs the memory back)
    RS = 2                                           # raster step: 2 px of this map = 8 m (the 20 km ring: 7,854 x 2,800
    #                                                  -- the landcover texture fits an 8,192 px GPU limit; ~200 MB of rasters in game)
    # --- water level: the Kettle and the lake from their banks, the great rivers stepping down to
    # the sea, the sea and harbours flat
    col = np.arange(CW)

    def _row(xm):
        return np.clip(((xm + HW) * K).astype(np.int64), 0, WH - 1)
    te, be = TOP_E[0], BOT_E[0]
    bank_lo = np.minimum(ELEV[_row(te - 6.0), col], ELEV[_row(be + 6.0), col]) - 0.4
    lvl_k = bank_lo.copy()
    for sh in range(1, 21):                                   # a running minimum over +-40 m
        lvl_k = np.minimum(lvl_k, np.minimum(np.roll(bank_lo, sh), np.roll(bank_lo, -sh)))
    # Lake Tamsin stands at one level (its lowest bank), blending into the Kettle's through the necks
    tl = T_L[0]
    lake_lvl = float(lvl_k[tl > 0.5].min())
    lvl_k = lvl_k * (1 - tl) + lake_lvl * tl
    LEVEL = np.full((WH, CW), -9999.0, np.float32)
    kettle = ((WCAT == 1) | (WCAT == 2)) & ~RIVMASK
    LEVEL[kettle] = np.broadcast_to(lvl_k[None, :], LEVEL.shape)[kettle]
    SEA_LEVEL = -0.5
    LEVEL[(WCAT == 6) | (WCAT == 7)] = SEA_LEVEL
    riv_lev = np.full((WH, CW), -9999.0, np.float32)
    jj, ii = np.nonzero(RIVMASK & (WCAT == 1))
    ps_px = ii * PX + PX / 2
    px_px = jj * PX + PX / 2 - HW
    best_d = np.full(len(ii), 1e18)
    for nm, pth in RIVER_PATHS:
        # the path runs from the sea to the Kettle / lake: walk it from the inland end, never rising
        # toward the sea, never above its banks
        pts = list(reversed(pth))
        i_, j_ = idx(*pts[0])
        prev = float(lvl_k[i_])
        levels = []
        for k_, (ps, px_) in enumerate(pts):
            a = pts[max(0, k_ - 1)]
            b_ = pts[min(len(pts) - 1, k_ + 1)]
            dv = np.array([b_[0] - a[0], b_[1] - a[1]])
            nrm = np.array([-dv[1], dv[0]]) / (np.hypot(*dv) or 1.0)
            banks = [ELEV[idx(ps + nrm[0] * sg_ * (RIVER_HALF + 10), px_ + nrm[1] * sg_ * (RIVER_HALF + 10))[::-1]]
                     for sg_ in (-1, 1)]
            frac = k_ / (len(pts) - 1)
            lv = min(prev, float(min(banks)) - 0.4, float(lvl_k[i_]) * (1 - frac) + SEA_LEVEL * frac + 0.3)
            levels.append(lv)
            prev = lv
        levels = [float(np.mean(levels[max(0, k_ - 6):k_ + 7])) for k_ in range(len(levels))]   # smooth along the river
        # each river pixel takes the level of its nearest centreline point
        for k_, (ps, px_) in enumerate(pts):
            dd = (wrap_d(ps_px - ps)) ** 2 + (px_px - px_) ** 2
            better = dd < best_d
            best_d = np.where(better, dd, best_d)
            riv_lev[jj[better], ii[better]] = levels[k_]
    LEVEL[RIVMASK & (WCAT == 1)] = riv_lev[RIVMASK & (WCAT == 1)]
    # --- bed depth below the water level: deepening from each shore
    def _depth(mask, radius_m, maxd):
        bl = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(radius_m * K)), np.float32)
        bl = np.clip((bl - np.float32(127.5)) / np.float32(127.5), 0, 1) ** np.float32(0.7)
        return np.where(mask, np.float32(0.4) + np.float32(maxd) * bl, np.float32(0.0)).astype(np.float32)
    DEPTH = _depth(kettle, 60, 6.0)
    np.maximum(DEPTH, _depth(RIVMASK & (WCAT == 1), 40, 4.0), out=DEPTH)
    np.maximum(DEPTH, _depth((WCAT == 6) | (WCAT == 7), 180, 18.0), out=DEPTH)
    # --- land cover (classes as before + 6 beach, 7 rock / cliff)
    cls_ = np.zeros((WH, CW), np.uint8)
    cls_[FARM] = 4
    cls_[FLOOD] = 2
    cls_[ISL] = 2                                     # (the islands: meadow under the woods)
    cls_[WOODS] = 3
    cls_[FP] = 1
    wb = Image.new("L", (CW, WH), 0)
    wbd = ImageDraw.Draw(wb)
    for c_ in FARMSTEADS:
        draw_ellipse(wbd, c_[0] - 8, c_[1], 26, fill=1)
    cls_[np.array(wb) > 0] = 5
    cls_[BEACH] = 6
    cls_[CLIFF] = 7
    cls_[WCAT > 0] = 0
    lc = np.stack([cls_, FIELD_G, np.zeros_like(cls_)], -1)[::RS, ::RS]        # G: crop + 8 * shade variant
    Image.fromarray(lc, "RGB").save(os.path.join(GD, "landcover.png"), optimize=True)

    def _save(name, arr, dt):
        with gzip.open(os.path.join(GD, name), "wb", compresslevel=6) as f:
            f.write(np.ascontiguousarray(arr[::RS, ::RS]).astype(dt).tobytes())
    # water surfaces as merged rectangles (s0, s1, x0, x1, level) over the 4 m raster: each column's
    # runs of water at one level (0.1 m steps) extend across the next columns while they stay the same
    LV4 = LEVEL[::RS, ::RS]
    q = np.where(LV4 > -9000, np.round(LV4 * 10).astype(np.int32), -99999)
    rects, open_ = [], {}
    step = PX * RS
    ncol = q.shape[1]
    for ci in range(ncol + 1):
        runs = set()
        if ci < ncol:
            colv = q[:, ci]
            j = 0
            n_ = len(colv)
            while j < n_:
                if colv[j] == -99999:
                    j += 1
                    continue
                v = colv[j]
                k2 = j
                while k2 + 1 < n_ and colv[k2 + 1] == v:
                    k2 += 1
                runs.add((j, k2, int(v)))
                j = k2 + 1
        for key in list(open_):
            if key not in runs or ci - open_[key] >= 16:           # at most 16 columns (64 m) per rect
                j0, j1, v = key
                rects.append([round(open_[key] * step, 1), round(ci * step, 1), round(j0 * step - HW, 1),
                              round((j1 + 1) * step - HW, 1), v / 10.0])
                del open_[key]
        for key in runs:
            if key not in open_:
                open_[key] = ci
    json.dump({"step_m": step, "rects": rects}, open(os.path.join(GD, "water_rects.json"), "w"))
    print("water rects:", len(rects))
    _save("terrain_base.bin.gz", ELEV, np.float16)
    _save("terrain_level.bin.gz", LEVEL, np.float16)
    _save("terrain_depth.bin.gz", DEPTH, np.float16)
    NX, NY = CW // RS + (1 if CW % RS else 0), WH // RS + (1 if WH % RS else 0)
    ter = {"version": 2, "R": R, "W": W, "raster": {"step_m": PX * RS, "nx": int(NX), "ny": int(NY), "x0": -HW,
                                                    "base": "terrain_base.bin.gz", "level": "terrain_level.bin.gz",
                                                    "depth": "terrain_depth.bin.gz", "dtype": "float16", "no_water": -9999.0},
           "landcover_step_m": PX * RS, "sea_level": SEA_LEVEL,
           "islands": [{"name": nm, "side": sg, "s": round(sc, 1), "x": xc, "half_s": hs, "half_x": hx}
                       for nm, sg, sc, xc, hs, hx in ISLANDS],
           "creeks": [{"name": n, "hw": 3.5, "depth": 1.1, "pts": [[round(a % C, 1), round(b_, 1)] for a, b_ in path]}
                      for n, path, pond in CREEK_PATHS]
                     + [{"name": "spur", "hw": 2.0, "depth": 0.7, "pts": [[round(a % C, 1), round(b_, 1)] for a, b_ in sp]}
                        for sp in SPUR_PATHS],
           "ponds": [{"name": n, "s": pond[0] % C, "x": pond[1], "a": pond[2] / 2, "b": pond[3], "rot": 0.25, "depth": 1.8}
                     for n, path, pond in CREEK_PATHS if pond],
           "oxbows": [],
           "ditches": [{"s0": round(min(p_[0] for p_ in run), 1), "s1": round(max(p_[0] for p_ in run), 1),
                        "x": round(run[0][1], 1), "hw": 1.5, "depth": 0.6} for run in DITCHES],
           "roads": [{"cls": cls, "w": ROAD_W[cls], "name": nm, "pts": [[round(a, 1), round(b_, 1)] for a, b_ in pts]}
                     for pts, cls, nm in ROADS]
                    + [dict({"cls": cls, "w": ROAD_W[cls], "town": t.name, "pts": [[round(a, 1), round(b_, 1)] for a, b_ in pts]},
                            **({"name": t.street_names[k]} if k in t.street_names else {}))
                       for t in TOWNS for k, (pts, cls) in enumerate(t.streets)],
           "rail": {"w": 8, "pts": [[round(a, 1), round(b_, 1)] for a, b_ in RAIL]},
           "turns": [{"s": round(a % C, 1), "x": round(b_, 1), "r": round(r_, 1), "cls": c_} for a, b_, r_, c_ in TURNS],
           "areas": [{"kind": kind, "town": t.name, "poly": [[round(a, 1), round(b_, 1)] for a, b_ in poly]}
                     for t in TOWNS for poly, kind in t.areas]}
    json.dump(ter, open(os.path.join(GD, "terrain.json"), "w"), indent=0)
    # --- the inventory: existing structures at their new places, farmsteads, crossings
    def _ri(poly):
        cs = sum(p_[0] for p_ in poly) / len(poly)
        cx = sum(p_[1] for p_ in poly) / len(poly)
        if len(poly) == 4:
            w = math.dist(poly[0], poly[1])
            d = math.dist(poly[1], poly[2])
            ang = math.degrees(math.atan2(poly[1][1] - poly[0][1], poly[1][0] - poly[0][0]))
            fe = [[round(poly[0][0] % C, 1), round(poly[0][1], 1)], [round(poly[1][0] % C, 1), round(poly[1][1], 1)]]
        else:
            w = d = 2 * max(math.dist((cs, cx), p_) for p_ in poly)
            ang, fe = 0.0, None
        return {"s": round(cs % C, 1), "x": round(cx, 1), "w": round(w, 1), "d": round(d, 1), "angle_deg": round(ang, 1), "front_edge": fe}
    inv = {"settlements": _INV["settlements"], "structures": [], "farmsteads": [], "crossings": []}
    by_town = {}
    for st_ in _INV["structures"]:
        by_town.setdefault(st_["settlement"], []).append(st_)
    for t in TOWNS:
        if t.coastal or t.name not in by_town:
            continue
        mains = [poly for poly, kind, part in t.bldgs if not part]
        for st_, poly in zip(by_town[t.name], mains):
            _ds = OLD_S0[t.name] * (SS - 1)
            _dx = (-WIDEN if t.x0 < 0 else WIDEN) + (t.x0 - t.x0_3km)
            parts = [dict(pt_, s=round((pt_["s"] + _ds) % C, 1), x=round(pt_["x"] + _dx, 1), front_edge=None) for pt_ in st_["parts"]]
            inv["structures"].append({**st_, **_ri(poly), "parts": parts})
    # a generated town (Calder): its structures under their generated ids, and each one's catalog record
    for t in TOWNS:
        if not hasattr(t, "calder_structs"):
            continue
        import calder as CAL
        inv["settlements"] = inv["settlements"] + [{"name": t.name, "tier": t.tier, "pop": t.pop, "founding": t.founding,
                                                    "archetype": t.archetype}]
        for e in t.calder_structs:
            inv["structures"].append({"id": e["id"], "settlement": t.name, "kind": CAL.KIND.get(e["use"], "store"), "label": e.get("label"),
                                      **_ri(e["poly"]), "parts": []})
        print("Calder records:", CAL.write_records(t.calder_structs), file=sys.stderr)
    for k_, c_ in enumerate(FARMSTEADS, 1):
        parts = []
        for poly, kind in FS_POLYS[k_ - 1]:
            ss_, xs_ = [q[0] for q in poly], [q[1] for q in poly]
            parts.append({"part": kind, "s": round(((min(ss_) + max(ss_)) / 2) % C, 1), "x": round((min(xs_) + max(xs_)) / 2, 1),
                          "w": round(max(ss_) - min(ss_), 1), "d": round(max(xs_) - min(xs_), 1)})
        inv["farmsteads"].append({"id": f"FARM-{k_:02d}", "s": round(c_[0] % C, 1), "x": round(c_[1], 1),
                                  "structures": ["farmhouse", "barn", "silo", "machine shed"], "parts": parts})
    # crossings: each takes the existing bridge model of its type whose span fits best (unused ones first)
    old_x = {}
    _bld = os.path.join(GD, "buildings")
    for c_ in _INV["crossings"]:
        if os.path.exists(os.path.join(_bld, c_["id"] + ".glb")):       # only models that exist
            old_x.setdefault(c_["type"], []).append(c_)
    used = set()
    n_by = {}
    for kind in ("small", "culvert", "rail", "major"):
        for item in BRIDGES[kind]:
            a, b_ = item[0], item[1]
            cls = item[2] if len(item) > 2 else "rail"
            span = math.dist(a, b_)
            s_m, x_m = (a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2
            n_by[kind] = n_by.get(kind, 0) + 1
            rid = f"{kind.upper()}-{n_by[kind]:02d}"
            model = None
            if kind in ("small", "culvert") or (kind == "rail" and span < 80):
                pool = old_x.get(kind if kind != "rail" else "rail", [])
                cands = sorted(pool, key=lambda o: (o["id"] in used, abs(o["span_m"] - span)))
                if cands:
                    model = cands[0]["id"]
                    used.add(model)
            inv["crossings"].append({"id": rid, "type": kind, "road_class": cls, "model": model,
                                     "s": round(s_m % C, 1), "x": round(x_m, 1), "span_m": round(span, 1),
                                     "ends": [[round(a[0] % C, 1), round(a[1], 1)], [round(b_[0] % C, 1), round(b_[1], 1)]]})
    json.dump(inv, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remake", "inventory",
                                     "map_inventory.json"), "w"), indent=1)
    print(f"game data: rasters {NX}x{NY} @ {PX * RS} m, {len(inv['structures'])} structures, "
          f"{len(inv['farmsteads'])} farmsteads, {len(inv['crossings'])} crossings "
          f"({sum(1 for c_ in inv['crossings'] if c_['model'])} on existing models)")

if "--inventory" in sys.argv:
    sys.exit("map_expanded.py: use --game-data (the map is approved) or --coastal-inventory")
    import json

    def rect_info(poly):
        cs = sum(p[0] for p in poly) / len(poly)
        cx = sum(p[1] for p in poly) / len(poly)
        if len(poly) == 4:
            w = math.dist(poly[0], poly[1])
            d = math.dist(poly[1], poly[2])
            ang = math.degrees(math.atan2(poly[1][1] - poly[0][1], poly[1][0] - poly[0][0]))
        else:
            r = max(math.dist((cs, cx), p) for p in poly)
            w = d = 2 * r
            ang = 0.0
        return {"s": round(cs, 1), "x": round(cx, 1), "w": round(w, 1), "d": round(d, 1),
                "angle_deg": round(ang, 1), "front_edge": [list(map(lambda v: round(v, 1), poly[0])),
                                                            list(map(lambda v: round(v, 1), poly[1]))]
                if len(poly) == 4 else None}

    inv = {"settlements": [], "structures": [], "farmsteads": [], "crossings": []}
    for t in TOWNS:
        inv["settlements"].append({"name": t.name, "tier": t.tier, "pop": t.pop, "founding": t.founding,
                                   "archetype": t.archetype})
        mains = [(p, txt) for p, txt in t.marks]
        n = 0
        parents = [b for b in t.bldgs if not b[2]]
        for poly, kind, part in t.bldgs:
            info = rect_info(poly)
            if part:
                continue
            n += 1
            label = None
            best = 35.0
            for p, txt in mains:
                dd = math.dist(p, (info["s"], info["x"]))
                if dd < best and txt not in ("Water St.", "Riverfront Promenade", "Sauk Park", "Town Green",
                                             "Oakwood Cemetery", "Strip mall", "Big-box", "Auto dealer"):
                    best, label = dd, txt
            sid = f"{''.join(w[0] for w in t.name.split()).upper()}-{n:03d}"
            parts = [rect_info(pp) for pp, kk, pt in t.bldgs if pt
                     and math.dist((rect_info(pp)["s"], rect_info(pp)["x"]), (info["s"], info["x"])) < 50]
            inv["structures"].append({"id": sid, "settlement": t.name, "kind": kind, "label": label,
                                      **info, "parts": parts})
    for k, c in enumerate(FARMSTEADS, 1):
        parts = []
        for poly, kind in FS_POLYS[k - 1]:
            ss, xs = [q[0] for q in poly], [q[1] for q in poly]
            parts.append({"part": {"house": "house", "barn": "barn", "silo": "silo", "shed": "shed"}[kind],
                          "s": round((min(ss) + max(ss)) / 2, 1), "x": round((min(xs) + max(xs)) / 2, 1),
                          "w": round(max(ss) - min(ss), 1), "d": round(max(xs) - min(xs), 1)})
        inv["farmsteads"].append({"id": f"FARM-{k:02d}", "s": round(c[0], 1), "x": round(c[1], 1),
                                  "structures": ["farmhouse", "barn", "silo", "machine shed"], "parts": parts})
    for kind in ("major", "small", "culvert", "rail"):
        for k, item in enumerate(BRIDGES[kind], 1):
            a, b_ = item[0], item[1]
            cls = item[2] if len(item) > 2 else "rail"
            s_m, x_m = (a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2
            i, j = idx(s_m, x_m)
            cid = CID[j, i]
            over = {1: "Kettle River", 2: "Lake Tamsin"}.get(int(WCAT[j, i]), None)
            if not over and cid:
                over = CREEK_PATHS[cid - 1][0]
            inv["crossings"].append({"id": f"{kind.upper()}-{k:02d}", "type": kind, "road_class": cls,
                                     "s": round(s_m, 1), "x": round(x_m, 1),
                                     "span_m": round(math.dist(a, b_), 1), "over": over or "farm ditch",
                                     "ends": [[round(a[0], 1), round(a[1], 1)], [round(b_[0], 1), round(b_[1], 1)]]})
    if "--terrain" in sys.argv:
        # the terrain model's data for the game (MapTerrain.gd): its closed-form parameters, and the
        # water features this preview draws from polylines -- creeks, spurs, ponds, oxbows, ditches
        ter = {"R": R, "W": W,
               "river": {"A": [A1, A2, A3], "phi": [PHI1, PHI2, PHI3, PHI4], "ch_half": CH_HALF, "bed_half": 12.0, "depth": 2.5},
               "lake": {"s": LAKE_S, "half_len": LAKE_HALF_LEN, "hw": LAKE_HW, "neck": LAKE_NECK, "depth": 4.5, "shelf": 20.0},
               "bluff": {"H": H_BLUFF, "Z1": Z1},
               "creeks": [{"name": n, "hw": 3.5, "depth": 1.1, "pts": [[round(a, 1), round(b_, 1)] for a, b_ in path]}
                          for n, path, pond in CREEK_PATHS]
                         + [{"name": "spur", "hw": 2.0, "depth": 0.7, "pts": [[round(a, 1), round(b_, 1)] for a, b_ in sp]}
                            for sp in SPUR_PATHS],
               "ponds": [{"name": n, "s": pond[0], "x": pond[1], "a": pond[2] / 2, "b": pond[3], "rot": 0.25, "depth": 1.8}
                         for n, path, pond in CREEK_PATHS if pond],
               "oxbows": [{"name": n, "depth": 1.5, "poly": [[round(a, 1), round(b_, 1)] for a, b_ in poly]} for n, poly in OXBOW_POLYS],
               "ditches": [{"s0": round(min(p_[0] for p_ in run), 1), "s1": round(max(p_[0] for p_ in run), 1),
                            "x": round(run[0][1], 1), "hw": 1.5, "depth": 0.6} for run in DITCHES],
               # roads and streets as drawn (width = the map's ROAD_W), the railway, and the towns'
               # areas (lawns, parking, squares...) -- the game grades and surfaces them
               "roads": [{"cls": cls, "w": ROAD_W[cls], "name": nm, "pts": [[round(a, 1), round(b_, 1)] for a, b_ in pts]}
                         for pts, cls, nm in ROADS]
                        + [{"cls": cls, "w": ROAD_W[cls], "town": t.name, "pts": [[round(a, 1), round(b_, 1)] for a, b_ in pts]}
                           for t in TOWNS for pts, cls in t.streets],
               "rail": {"w": 8, "pts": [[round(a, 1), round(b_, 1)] for a, b_ in RAIL]},
               "areas": [{"kind": kind, "town": t.name, "poly": [[round(a, 1), round(b_, 1)] for a, b_ in poly]}
                         for t in TOWNS for poly, kind in t.areas]}
        ter_path = sys.argv[sys.argv.index("--terrain") + 1]
        with open(ter_path, "w") as f:
            json.dump(ter, f, indent=0)
        # land cover at 2 m / px (s across, x down from -HW): R = class, G = field id (farm fields)
        #   1 built-up (settlement footprint)  2 floodplain meadow  3 woods  4 farm field
        #   5 farmstead windbreak grove        0 anything else (grass, rough)
        cls_ = np.zeros((WH, CW), np.uint8)
        cls_[FARM] = 4
        cls_[FLOOD] = 2
        cls_[WOODS] = 3
        cls_[FP] = 1
        wb = Image.new("L", (CW, WH), 0)
        wbd = ImageDraw.Draw(wb)
        for c in FARMSTEADS:
            draw_ellipse(wbd, c[0] - 8, c[1], 26, fill=1)
        cls_[np.array(wb) > 0] = 5
        cls_[WCAT > 0] = 0
        lc = np.stack([cls_, (fid % 97).astype(np.uint8), np.zeros_like(cls_)], -1)[::2, ::2]
        Image.fromarray(lc, "RGB").save(os.path.join(os.path.dirname(ter_path), "landcover.png"), optimize=True)
        print(f"terrain: {len(ter['creeks'])} creeks/spurs, {len(ter['ponds'])} ponds, {len(ter['oxbows'])} oxbows, "
              f"{len(ter['ditches'])} ditches")
    out_inv = sys.argv[sys.argv.index("--inventory") + 1]
    with open(out_inv, "w") as f:
        json.dump(inv, f, indent=1)
    print(f"inventory: {len(inv['structures'])} structures, {len(inv['farmsteads'])} farmsteads, "
          f"{len(inv['crossings'])} crossings -> {out_inv}")
