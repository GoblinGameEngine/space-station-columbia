"""terrain_relief.py -- the station's hills and small mountains (the user, 2026-10-07: "Add tall rocky hills and smooth
rolling hills around the map. Leave Calder as it is ... Harrow Falls should be a hilly city ... a natural waterfall ...
from a spring on a tall nearby rocky hill, perhaps one the city is built around ... At this scale we can have small
mountains. I will let you decide the maximum height."  research/terrain_and_cities/README.md).

Heights in metres, added to tools/map_expanded.py's bluff-and-valley terrain before the coasts and river valleys shape it:

  rolling   everywhere on land: long smooth swells, 10-40 m (the north's glacial drumlins, the south's grassy coast-range
            foothills), eased down in the towns' centres
  massifs   the hand-placed RELIEF list: small mountains (300-450 m, the highest MAX_PEAK) and rocky hills (90-220 m) in the
            town-free uplands between the trunk roads and the coasts; a ridged, faceted profile (rock faces, gullies) for
            "rocky", a rounded one for "smooth"
  Harrow    Harrow Hill: a granite knob ~150 m over Lake Tamsin that Harrow Falls wraps round; the spring near its top and
            the falls on its lake face are HARROW (the map draws Harrow Run from them)
  flat      Calder (the user: "that town can be flat") and the towns' downtown cores: FLAT zones scale the relief to 0

Station frame: s metres round the ring (0..C), x metres along the axis (- north, + south).  Pure functions of (s, x):
the same anywhere they're asked (map, roads, towns, the game's tools).
"""
import math

import numpy as np

C = 2 * math.pi * 10000.0
MAX_PEAK = 450.0              # the highest summit: "small mountains" (gravity there still 95.5% of the floor's)

# (name, s, x, peak m, half-length along s, half-width along x, profile, ridge direction (rad, 0 = along s))
RELIEF = [
    # the North Sea's granite highlands (Acadia, Camden Hills: mountains standing near the sea)
    ("Mount Carrow", 32600.0, -3850.0, 450.0, 2300.0, 1150.0, "rocky", 0.15),
    ("Gannet Ridge", 47600.0, -3900.0, 360.0, 2100.0, 1000.0, "rocky", -0.10),
    ("Tern Mountain", 21400.0, -3800.0, 310.0, 1700.0, 950.0, "rocky", 0.25),
    # the South Sea's coast range (Santa Lucia, Santa Ynez: rounded grassy ridges, rock only in their crests)
    ("Sierra Playa", 17700.0, 3850.0, 420.0, 2300.0, 1050.0, "smooth", -0.08),
    ("Sierra Pelican", 45900.0, 3800.0, 380.0, 2000.0, 1000.0, "smooth", 0.12),
    # rocky hills
    ("Ledge Hill", 3900.0, -3900.0, 190.0, 900.0, 700.0, "rocky", 0.6),
    ("Haven Knob", 15600.0, -4150.0, 140.0, 650.0, 520.0, "rocky", -0.4),
    ("Grey Ledges", 27100.0, -4300.0, 210.0, 1000.0, 650.0, "rocky", 0.3),
    ("Fenwick Hill", 40100.0, -3950.0, 170.0, 800.0, 620.0, "rocky", -0.2),
    ("Saddleback", 57200.0, -3950.0, 220.0, 1100.0, 700.0, "rocky", 0.5),
    ("Loma Alta", 3100.0, 3950.0, 200.0, 1100.0, 700.0, "smooth", 0.2),
    ("Cerro Kessler", 38900.0, 3900.0, 170.0, 900.0, 650.0, "smooth", -0.3),
    ("Tamarack Butte", 52200.0, 3850.0, 160.0, 700.0, 600.0, "rocky", 0.4),
    ("Loma Verde", 61900.0, 3800.0, 190.0, 1000.0, 680.0, "smooth", -0.1),
]
# Harrow Hill: Harrow Falls' own (the town's downtown lies on the lake terrace below its lake face)
HARROW = {"name": "Harrow Hill", "s": 8250.0, "x": 1480.0, "peak": 150.0, "rs": 520.0, "rx": 430.0,
          # the spring, high on its north-west shoulder; Harrow Run falls from the cliff's lip to the lake terrace
          "spring": (8150.0, 1330.0), "lip": (8060.0, 1150.0), "foot": (8030.0, 1060.0), "mouth": (7990.0, 960.0)}
# flat zones (s, x, r_flat, r_fade): Calder stays as it is; downtown cores ease the rolling swells (not the massifs)
FLAT = [("Calder", 26315.0, 2430.0, 2600.0, 3600.0)]
TOWN_CORES = [("Solana Point", 35226.0, 5495.0, 44200), ("Port Carrow", 36330.0, -5560.0, 38600), ("Kessler", 42609.0, 2058.0, 34500),
              ("Oceanview", 60005.0, 5469.0, 9800), ("Marlowe", 30004.0, -2030.0, 9100), ("Tamarack", 56406.0, 2118.0, 8300),
              ("Bellhaven", 21011.0, 2045.0, 7200), ("Fenwick", 43019.0, -2060.0, 6400), ("Brightwater", 54342.0, -5521.0, 6200),
              ("Playa Verde", 14331.0, 5451.0, 5400), ("Haven Point", 12447.0, -5444.0, 3900), ("Port Tamsin", 7998.0, -1935.0, 3400),
              ("Haskins Corner", 59113.0, -1837.0, 2600), ("Pelican Cove", 48943.0, 5513.0, 1600), ("Tern Harbor", 18599.0, -5512.0, 1300),
              ("Pruett", 29988.0, 2359.0, 820), ("Dunmore Crossing", 13009.0, -2059.0, 480), ("Loomis Grove", 51596.0, -2937.0, 390),
              ("Cedar Ford", 24974.0, -674.0, 1150), ("Harrow Falls", 7900.0, 934.0, 41800)]


def wrap(d):
    return (d + C / 2) % C - C / 2


def _hash01(*a):
    h = 2166136261
    for v in a:
        for ch in str(v).encode():
            h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return h / 2 ** 32


def _lattice(i, j, seed):
    """a value in [-1, 1] per lattice point (integer hash, vectorised)"""
    with np.errstate(over="ignore"):
        h = (np.asarray(i).astype(np.int64) * 73856093) ^ (np.asarray(j).astype(np.int64) * 19349663) ^ (int(seed) * 83492791)
        h = (h ^ (h >> 13)) * 1274126177
        h = h ^ (h >> 16)
    return ((h & 0xFFFF).astype(np.float32) / 32767.5 - 1.0)


def _vnoise(s, x, cell, seed):
    """2-D gradient (Perlin) noise in about [-1, 1], its lattice turned by a seed-chosen angle (no grid-aligned features);
    seamless round the ring: the turned lattice is tiled along s with whole periods"""
    ang = 2 * math.pi * _hash01("ang", seed)
    ca, sa = math.cos(ang), math.sin(ang)
    n_s = max(1, int(round(C / cell)))
    cs = C / n_s
    # (s wraps: map it to an angle on the ring and back so the lattice period divides C; turn only the local offsets)
    S = np.asarray(s, dtype=np.float64) % C
    X = np.asarray(x, dtype=np.float64)
    u = S / cs
    v = X / cell + 1000.0
    # a shear by the angle keeps whole periods along s (u wraps at n_s) while breaking the axis alignment
    v2 = v + (u * sa * 0.5)
    u2 = u + (v * sa * 0.5) * ca
    i0 = np.floor(u2).astype(np.int64)
    j0 = np.floor(v2).astype(np.int64)
    fu = (u2 - i0).astype(np.float32)
    fv = (v2 - j0).astype(np.float32)

    def grad(i, j, du, dv):
        g = _lattice(i % n_s, j, seed) * math.pi
        return np.cos(g) * du + np.sin(g) * dv
    n00 = grad(i0, j0, fu, fv)
    n10 = grad(i0 + 1, j0, fu - 1, fv)
    n01 = grad(i0, j0 + 1, fu, fv - 1)
    n11 = grad(i0 + 1, j0 + 1, fu - 1, fv - 1)
    wu = fu * fu * fu * (fu * (fu * 6 - 15) + 10)
    wv = fv * fv * fv * (fv * (fv * 6 - 15) + 10)
    nx0 = n00 + (n10 - n00) * wu
    nx1 = n01 + (n11 - n01) * wu
    return ((nx0 + (nx1 - nx0) * wv) * 1.41).astype(np.float32)


def _noise(s, x, scale, seed, octaves=4, lac=2.03, gain=0.5):
    """fractal value noise in about [-1, 1]"""
    out = None
    amp, cell, tot = 1.0, float(scale), 0.0
    for o in range(octaves):
        n = _vnoise(s, x, cell, int(seed) * 31 + o * 977)
        out = n * amp if out is None else out + n * amp
        tot += amp
        amp *= gain
        cell /= lac
    return (out / tot).astype(np.float32)


def _ridged(s, x, scale, seed, octaves=5):
    """ridged multifractal in [0, 1]: sharp crests, branching gullies (granite ridges)"""
    out = None
    amp, cell, w, tot = 1.0, float(scale), 1.0, 0.0
    for o in range(octaves):
        n = 1.0 - np.abs(_vnoise(s, x, cell, int(seed) * 53 + o * 1213))
        n = n * n * w
        w = np.clip(n * 1.6, 0, 1)
        out = n * amp if out is None else out + n * amp
        tot += amp
        amp *= 0.5
        cell /= 2.1
    return (out / tot).astype(np.float32)


def _flat_weight(s, x):
    """1 where relief stands at full height, 0 in a flat zone (Calder)"""
    w = np.ones(np.broadcast(s, x).shape, dtype=np.float32)
    for _, fs, fx, r0, r1 in FLAT:
        d = np.sqrt(wrap(s - fs) ** 2 + (x - fx) ** 2)
        t = np.clip((d - r0) / (r1 - r0), 0, 1)
        w = np.minimum(w, (t * t * (3 - 2 * t)).astype(np.float32))
    return w


def _core_weight(s, x):
    """the rolling swells ease down in a town's centre (a downtown wants level ground); 0.25 at the very core"""
    w = np.ones(np.broadcast(s, x).shape, dtype=np.float32)
    for _, ts, tx, pop in TOWN_CORES:
        r0 = 150.0 + 3.0 * math.sqrt(pop)
        r1 = r0 * 2.2
        d = np.sqrt(wrap(s - ts) ** 2 + (x - tx) ** 2)
        t = np.clip((d - r0) / (r1 - r0), 0, 1)
        w = np.minimum(w, (0.25 + 0.75 * t * t * (3 - 2 * t)).astype(np.float32))
    return w


def _massif(s, x, m):
    name, ms, mx, peak, rs, rx, prof, ang = m
    ds, dx = wrap(s - ms), x - mx
    if np.all(np.abs(ds) > rs * 2.4) or np.all(np.abs(dx) > rx * 2.4):
        return None
    seed = int(_hash01(name) * 100000)
    # an irregular outline: the ellipse's radius warped by noise round it (a range, not an egg)
    c, sn = math.cos(ang), math.sin(ang)
    wu = 0.35 * min(rs, rx)
    ds2 = ds + wu * _noise(s, x, 0.6 * min(rs, rx), seed + 1, octaves=3)
    dx2 = dx + wu * _noise(s, x, 0.6 * min(rs, rx), seed + 2, octaves=3)
    u = (ds2 * c + dx2 * sn) / rs
    v = (-ds2 * sn + dx2 * c) / rx
    r = np.sqrt(u * u + v * v)
    # long foothill skirts out to r 1.8 (a mountain rises out of its hills), the steep body within r 1
    t = np.clip(1.0 - r / 1.8, 0, 1)
    skirt = (t * t * (3 - 2 * t)) ** 1.6
    # spurs and valleys radiating from the crest down the flanks (the drainage a mountain has), wandering a little
    th = np.arctan2(v, u)
    nsp = 7 + int(5 * _hash01(name, "spurs"))
    spur = 0.5 + 0.5 * np.cos(nsp * th + 1.8 * _noise(s, x, 0.7 * min(rs, rx), seed + 5, octaves=2))
    flank = np.clip((r - 0.15) * 2.0, 0, 1)
    sp = 1.0 - 0.32 * flank * (1.0 - spur) ** 1.5
    if prof == "rocky":
        env = np.clip(1.0 - r, 0, 1)
        env = 0.78 * env ** 1.15 + 0.22 * skirt
        rid = _ridged(s, x, 0.6 * min(rs, rx), seed + 3, octaves=4)
        crest = np.exp(-(v * v) * 2.5)
        h = peak * env * sp * (0.45 + 0.55 * (0.6 * crest + 0.4 * rid))
        # granite breaks in shelves: a ledged profile on the steep flanks
        step = 7.0 + 5.0 * _hash01(name, "step")
        h = h - 0.12 * (h - np.floor(h / step) * step) * np.clip(env * 2.5 - 0.2, 0, 1)
    else:
        env = np.clip(1.0 - r * r, 0, 1)
        env = 0.75 * env * env * (3 - 2 * env) + 0.25 * skirt
        spur = 0.5 + 0.5 * _noise(s, x, 0.5 * min(rs, rx), seed + 4, octaves=3, gain=0.4)
        crest = np.exp(-(v * v) * 1.6)
        h = peak * env * sp * (0.45 + 0.4 * crest + 0.15 * spur)
    return (h / max(1e-3, 1.0)).astype(np.float32)


def _harrow(s, x):
    H = HARROW
    ds, dx = wrap(s - H["s"]), x - H["x"]
    r = np.sqrt((ds / H["rs"]) ** 2 + (dx / H["rx"]) ** 2)
    # a dome with a steep lake face: the -x (lake) side drops in a cliff, the inland sides slope away
    lake_side = np.clip(-dx / H["rx"], 0, 1)
    sharp = 1.0 + 2.2 * lake_side
    body = np.clip(1.0 - r, 0, 1)
    h = H["peak"] * body ** (1.0 / sharp) * np.where(r < 1.0, 1.0, 0.0)
    # the cliff: within ~25 m of the lip line the ground falls away (the falls drop over it)
    lip_r = 0.62
    cliff = np.clip((r - lip_r) / 0.06, 0, 1) * lake_side
    h = h * (1.0 - 0.75 * cliff)
    ridge = _ridged(s, x, 160.0, 777, octaves=4)
    return (h * (0.85 + 0.15 * ridge)).astype(np.float32)


def relief(s, x):
    """the height (m) the hills and mountains add at (s, x): float32 array of broadcast(s, x)"""
    s = np.asarray(s, dtype=np.float32)
    x = np.asarray(x, dtype=np.float32)
    # rolling swells: north glacial (shorter, hummocky), south foothills (longer, smoother)
    roll_n = 18.0 * _noise(s, x, 1400.0, 11, octaves=5, gain=0.5) + 10.0
    roll_s = 26.0 * _noise(s, x, 2400.0, 23, octaves=4, gain=0.42) + 13.0
    k = np.clip((x + 600.0) / 1200.0, 0, 1)                     # (the two styles blend across the river)
    k = k * k * (3 - 2 * k)
    roll = (roll_n * (1 - k) + roll_s * k).astype(np.float32)
    roll = np.maximum(roll, 0.0) * _core_weight(s, x)
    h = roll
    for m in RELIEF:
        mh = _massif(s, x, m)
        if mh is not None:
            h = np.maximum(h, mh + 0.5 * roll)
    h = np.maximum(h, _harrow(s, x))
    return (h * _flat_weight(s, x)).astype(np.float32)


def rocky(s, x, h=None, slope=None):
    """where bare rock shows: the rocky massifs' steep faces and crests, Harrow Hill's lake face (a mask for land cover)"""
    s = np.asarray(s, dtype=np.float32)
    x = np.asarray(x, dtype=np.float32)
    out = np.zeros(np.broadcast(s, x).shape, dtype=bool)
    for m in RELIEF:
        name, ms, mx, peak, rs, rx, prof, ang = m
        d = np.sqrt((wrap(s - ms) / rs) ** 2 + ((x - mx) / rx) ** 2)
        near = d < (0.75 if prof == "rocky" else 0.35)
        out |= near
    H = HARROW
    out |= np.sqrt((wrap(s - H["s"]) / H["rs"]) ** 2 + ((x - H["x"]) / H["rx"]) ** 2) < 0.7
    if slope is not None:
        out &= slope > 0.45
        out |= slope > 0.9
    return out


def harrow_run():
    """Harrow Run's course: the spring, over the lip (the falls), down the gorge to the lake: [(s, x)]"""
    H = HARROW
    return [H["spring"], ((H["spring"][0] + H["lip"][0]) / 2, (H["spring"][1] + H["lip"][1]) / 2), H["lip"], H["foot"], H["mouth"]]
