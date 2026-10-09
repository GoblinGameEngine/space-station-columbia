#!/usr/bin/env python3
"""
city.py -- any settlement laid out at 1:1 from its spec (the user, 2026-10-07: "begin recreating the towns and cities and
settlements according to our new 1:1 scale. Each city needs its own aesthetic and flavor ... Any settlement of more than
9,000 people will have its own defining characteristics and landmarks"; research/terrain_and_cities/README.md and
research/urban_layout/).  Calder (town.py, calder.py) was the first; this is its general form.

What it does, in the order a real town grew:
  1. the core: Main Street through the centre on the flattest ground, a downtown of blocks sized to the population,
     the civic heart the region builds (a New England green, a California plaza, a Midwest courthouse square)
  2. the grid carried outward over the land (rail-era and streetcar plats near, interwar beyond) -- straight over the
     hills, as Seattle, Duluth and Pittsburgh did: a link too steep for its class becomes PUBLIC STAIRS (<= 60%,
     Pittsburgh's steps reach ~70%), steeper still is left out; slopes over 25% stay wooded (hillside ordinances)
  3. lots along every frontage nearest first, uses by distance from the centre (stores and mixed-use blocks downtown,
     walk-up apartments, rows and two-flats around it, houses beyond), each lot's slope checked, until the
     settlement's households are housed
  4. postwar curvilinear drives and courts at the edge where the grid ends, strip centres on the arterials (centers.py)
  5. institutions by the research's ratios (schools by the neighbourhood unit, fire stations by coverage, churches),
     industry on the rail or the water, the harbour's wharves, and the LANDMARKS the spec names on their sites
Deterministic: a pure function of (spec, seed); the map supplies blocked(u, v) (water, the rail) and height(u, v).

    plan = plan_city(spec, blocked, height) -> {"streets", "stairs", "lots", "areas", "marks", "centres", "landmarks", "stats"}
"""
import math
import os
import random

import centers as CT
import town as TW
from town import BANDS, ROW, Planner, densify, rect, wavy

TW.USE_W.update({"apartment_big": (60.0, 72.0), "apartment_court": (36.0, 44.0), "two_flat": (10.0, 12.5)})
HH_SIZE = 2.45
GRADE = {"main": 0.08, "street": 0.15, "collector": 0.12, "drive": 0.15, "court": 0.15, "alley": 0.15}
STAIR_MAX = 0.60
LOT_SLOPE_MAX = 0.25
UNITS = {"house": 1, "duplex": 2, "two_flat": 2, "townhouse": 6, "apartment": 12, "apartment_big": 24, "apartment_court": 8}


def _grade_runs(pts, height, cls):
    """split a street into runs: ("road", pts) where its grade stays within its class's limit, ("stair", pts) where it's
    too steep for a road but walkable steps would do, nothing where it's steeper still"""
    P = densify(pts, 10.0)
    hs = [height(*p) for p in P]
    lim = GRADE.get(cls, 0.15)
    kinds = []
    for i in range(len(P) - 1):
        L = math.dist(P[i], P[i + 1]) or 1.0
        g = abs(hs[i + 1] - hs[i]) / L
        kinds.append("road" if g <= lim else ("stair" if g <= STAIR_MAX else None))
    # a short steep pitch (<= 30 m) inside a road run is graded through (a cut), not stepped
    for i, k in enumerate(kinds):
        if k == "stair":
            j = i
            while j < len(kinds) and kinds[j] == "stair":
                j += 1
            if (j - i) * 10.0 <= 30.0 and i > 0 and j < len(kinds) and kinds[i - 1] == "road" and kinds[j] == "road":
                for q in range(i, j):
                    kinds[q] = "road"
    runs, cur, ck = [], [P[0]], kinds[0] if kinds else None
    for i, k in enumerate(kinds):
        if k == ck:
            cur.append(P[i + 1])
        else:
            if ck and len(cur) > 1:
                runs.append((ck, cur))
            cur, ck = [P[i], P[i + 1]], k
    if ck and len(cur) > 1:
        runs.append((ck, cur))
    return runs


def _lot_slope(poly, height):
    hs = [height(*p) for p in poly]
    cu = sum(p[0] for p in poly) / len(poly)
    cv = sum(p[1] for p in poly) / len(poly)
    span = max(math.dist(poly[0], poly[2]), 1.0)
    return (max(hs + [height(cu, cv)]) - min(hs + [height(cu, cv)])) / span


class _HeightGrid:
    """the ground sampled once on an 8 m grid over the plan (the relief is costly per point): bilinear lookups"""
    def __init__(self, height, U, V, step=8.0):
        import numpy as np
        self.np = np
        self.u0, self.v0, self.st = -U - 80, -V - 80, step
        nu, nv = int((2 * U + 160) / step) + 2, int((2 * V + 160) / step) + 2
        self.h = np.zeros((nv, nu), dtype=np.float32)
        try:
            uu = np.arange(nu, dtype=np.float32) * step + self.u0
            vv = np.arange(nv, dtype=np.float32) * step + self.v0
            self.h[:] = height(uu[None, :], vv[:, None])
        except Exception:
            for j in range(nv):
                for i in range(nu):
                    self.h[j, i] = height(self.u0 + i * step, self.v0 + j * step)

    def __call__(self, u, v):
        fu, fv = (u - self.u0) / self.st, (v - self.v0) / self.st
        i, j = int(fu), int(fv)
        if i < 0 or j < 0 or i >= self.h.shape[1] - 1 or j >= self.h.shape[0] - 1:
            return 0.0
        tu, tv = fu - i, fv - j
        h = self.h
        return float((h[j, i] * (1 - tu) + h[j, i + 1] * tu) * (1 - tv) + (h[j + 1, i] * (1 - tu) + h[j + 1, i + 1] * tu) * tv)


def plan_city(spec, blocked=lambda u, v: False, height=lambda u, v: 0.0):
    rng = random.Random(spec.get("seed", 1))
    pop = spec["pop"]
    H_target = pop / HH_SIZE
    tier = spec.get("tier", "town")
    region = spec.get("region", "gl")
    # the plan's reach either way along Main (a waterfront town runs further along its shore)
    U = spec.get("half_u", (600.0 + 13.0 * math.sqrt(pop)) * (1.35 if spec.get("waterfront") else 1.0))
    V = spec.get("half_v", 450.0 + 13.0 * math.sqrt(pop))
    height = _HeightGrid(height, U, V)
    cfg = {"bounds": (-U, U, -V, V), "seed": spec.get("seed", 1)}
    pl = Planner(cfg, rng, blocked)
    pl.stairs = []
    pl.landmarks = []
    reserved = []                                                    # sites the streets go round
    N = spec.get("names") or {}
    names = _Namer(spec, rng)
    core = spec.get("core_u", 90.0 + 2.2 * math.sqrt(pop))           # downtown's half-length along Main
    BK_U, BK_V = (100.0, 84.0) if tier == "city" else (110.0, 92.0)
    R_grid = spec.get("grid_r", core * (2.8 if tier == "city" else 2.4) + 120.0)
    SU = spec.get("stretch_u", 1.6 if spec.get("waterfront") else 1.0)     # (u / SU, v / 0.8: the town's shape)
    pl.SU = SU
    rail_v = spec.get("rail_v")
    if rail_v:
        pl.occ.line([(u, rail_v(u)) for u in range(int(-U) - 60, int(U) + 61, 10)], 26.0)
    # the old town's outline: a grid this far out, ragged (the plats were filed one at a time)
    ph = [rng.uniform(0, 2 * math.pi) for _ in range(3)]

    def in_grid(u, v):
        a = math.atan2(v / 0.8, u / SU)
        r = R_grid * (1.0 + 0.16 * math.sin(3 * a + ph[0]) + 0.09 * math.sin(5 * a + ph[1]))
        return math.hypot(u / SU, v / 0.8) <= r

    def in_reserved(u, v):
        return any(r[0] <= u <= r[1] and r[2] <= v <= r[3] for r in reserved)

    streets = []

    def lay(pts, cls, name, keep=lambda u, v: True):
        """a street over the ground: the runs its grade allows, stairs where only steps will do (none through a
        reserved site, the water, or outside `keep`)"""
        out = []
        bad = lambda u, v: blocked(u, v) or in_reserved(u, v) or not keep(u, v)
        for kind, run in _grade_runs(pts, height, cls):
            for seg in _dry_runs(densify(run, 6.0), bad):
                if math.dist(seg[0], seg[-1]) < 25.0:
                    continue
                if kind == "road":
                    out.append(pl.street(seg, cls, name))
                    streets.append((seg, cls, name))
                else:
                    pl.stairs.append({"pts": seg, "name": f"{name} Steps" if name else "City Steps"})
                    pl.occ.line(seg, 4.0)
        return out

    def reserve(u0, u1, v0, v1, kind=None, use=None, label=None, lm=None):
        poly = rect(u0, u1, v0, v1)
        reserved.append((min(u0, u1), max(u0, u1), min(v0, v1), max(v0, v1)))
        pl.site(poly, kind)
        if use:
            l = pl.lot(poly, use, "interwar", setback=6.0, depth=abs(v1 - v0), width=abs(u1 - u0), institution=True, label=label)
            l["zone"] = "civic"
        if lm:
            pl.landmarks.append(dict(lm, poly=poly))
        return poly

    # ================= the civic heart =================
    heart = spec.get("heart") or {"ne": "green", "ca": "plaza", "gl": "square"}.get(region, "square")
    hu = spec.get("heart_u", 0.0)
    h0 = ROW["main"] / 2 + ROW["street"] / 2
    if heart == "square":
        # the courthouse square (Upper South / Midwest county seat): a whole block, the courthouse alone in it, business
        # blocks facing it on four sides
        reserve(hu - BK_U / 2 + 10, hu + BK_U / 2 - 10, ROW["main"] / 2 + 1, BK_V - ROW["street"] / 2 - 1, "square",
                lm={"kind": spec.get("square_landmark", "courthouse"), "label": N.get("courthouse") or f"{spec['name']} Courthouse"})
    elif heart == "green":
        # the New England common, the meetinghouse (white church) and town hall on its edges
        reserve(hu - BK_U + 10, hu + BK_U - 10, ROW["main"] / 2 + 1, BK_V * 1.0, "green",
                lm={"kind": "common", "label": N.get("green") or f"{spec['name']} Common"})
        reserve(hu + BK_U - 6, hu + BK_U + 22, BK_V * 0.3, BK_V * 0.3 + 36, use="church", label=N.get("meetinghouse") or "First Parish Church",
                lm={"kind": "meetinghouse", "label": N.get("meetinghouse") or "First Parish Church"})
    elif heart == "plaza":
        reserve(hu - BK_U * 0.45, hu + BK_U * 0.45, ROW["main"] / 2 + 1, BK_V * 0.9, "plaza",
                lm={"kind": "plaza", "label": N.get("plaza") or "Plaza"})
    # landmark sites the spec places itself (u, v, size, area, kind...)
    for lm in spec.get("landmarks", []):
        if "at" in lm:
            u_, v_ = lm["at"]
            w_, d_ = lm.get("size", (30.0, 30.0))
            reserve(u_ - w_ / 2, u_ + w_ / 2, v_ - d_ / 2, v_ + d_ / 2, lm.get("area"), lm=lm)
        elif "path" in lm:
            pl.landmarks.append(dict(lm))
    # landmarks the spec places "near" something: a free, flat-enough site searched outward from that anchor
    from records import LANDMARK_RECIPE
    anchors = dict(spec.get("anchors") or {})
    anchors.setdefault("heart", (hu + BK_U * 1.1, BK_V * 0.5))
    anchors.setdefault("downtown", (core * 0.5, BK_V * 0.6))
    anchors.setdefault("edge", (R_grid * 0.95, R_grid * 0.3))
    if rail_v:
        anchors.setdefault("rail", (120.0, rail_v(120.0) + (40.0 if rail_v(120.0) < 0 else -40.0)))
    for lm in spec.get("landmarks", []):
        if "at" in lm or lm["kind"] not in LANDMARK_RECIPE:
            continue
        a = anchors.get(lm.get("near"), anchors["downtown"])
        w_, d_ = lm.get("size", (34.0, 30.0))
        for tri in range(200):                           # (out to ~170 m: a works' 220 m site clear of the station beside it)
            ang = tri * 2.4
            r = 0.0 if tri == 0 else 12.0 * math.sqrt(tri)
            cu, cv = a[0] + r * math.cos(ang), a[1] + r * math.sin(ang)
            poly = rect(cu - w_ / 2, cu + w_ / 2, cv - d_ / 2, cv + d_ / 2)
            # (the whole rectangle clear of every reserved site: its corners and centre alone let Kessler Works' 220 m
            # site swallow the station and the roundhouse sited before it)
            if not (pl.inside(poly) and pl.dry(poly)) or any(r[0] < cu + w_ / 2 and cu - w_ / 2 < r[1] and r[2] < cv + d_ / 2
                                                             and cv - d_ / 2 < r[3] for r in reserved):
                continue
            if lm.get("near") not in ("summit", "hill") and _lot_slope(poly, height) > 0.15:
                continue
            reserve(cu - w_ / 2, cu + w_ / 2, cv - d_ / 2, cv + d_ / 2, None, lm=lm)
            break
    # institutions: big sites take whole blocks of the grid (or a neighbourhood's centre); the streets go round them
    placed = _place_institutions(pl, _institutions(spec, pop, tier), core, BK_U, BK_V, R_grid, height, blocked, rng, reserve, in_reserved)
    # ================= the network =================
    # Main (the arterial through the centre), the cross arterial, a ring road round the old town, radial collectors
    lay([(-U, 0.0), (U, 0.0)], "main", N.get("main") or "Main St")
    lay([(0.0, -V), (0.0, V)], "collector", N.get("cross_main") or names.cross(0.0))
    ring_pts = [(SU * R_grid * 1.12 * math.cos(2 * math.pi * k / 72), 0.8 * R_grid * 1.12 * math.sin(2 * math.pi * k / 72)) for k in range(73)]
    lay(ring_pts, "collector", N.get("ring") or "Ridgeway Blvd" if spec.get("hilly") else "Boulevard")
    n_rad = 6 if tier == "city" else 4
    for k in range(n_rad):
        a = 2 * math.pi * (k + 0.5) / n_rad + ph[2] * 0.1
        lay([(SU * R_grid * 0.6 * math.cos(a), R_grid * 0.48 * math.sin(a)), (U * 1.05 * math.cos(a), V * 1.05 * math.sin(a))], "collector",
            names.radial(k))
    # the old town's grid inside its ragged outline
    us = [k * BK_U for k in range(-int(U / BK_U), int(U / BK_U) + 1)]
    vs = [k * BK_V for k in range(-int(V / BK_V), int(V / BK_V) + 1)]
    for v in vs:
        if abs(v) > 1:
            lay([(-U, v), (U, v)], "street", names.parallel(v), keep=in_grid)
    for u in us:
        if abs(u) > 1:
            lay([(u, -V), (u, V)], "street", names.cross(u), keep=in_grid)
    for v in vs:
        for a_, b_ in zip(us, us[1:]):
            mid = (a_ + b_) / 2
            if math.hypot(mid, (v + BK_V / 2) / 0.8) < core * 1.9:
                lay([(a_, v + BK_V / 2), (b_, v + BK_V / 2)], "alley", "", keep=in_grid)
    # ================= the waterfront: beach, boardwalk, pier, wharves, marina, club, launch, light =================
    pl.walks, pl.wbldgs = [], []
    if spec.get("waterfront") or spec.get("coast") or spec.get("lake"):
        waterfront(pl, spec, blocked, U, V, rng, wet=spec.get("wet"))
        for b in pl.wbldgs:
            if b.get("land"):
                pl.occ.poly(b["poly"])
    # ================= lots: block face by block face, nearest the centre first =================
    hh = 0.0
    faces = []
    for pts, cls, name in streets:
        if cls == "alley":
            continue
        for seg in _block_faces(pts, BK_U if abs(pts[0][1] - pts[-1][1]) < abs(pts[0][0] - pts[-1][0]) else BK_V):
            faces.append((seg, cls, name))
    faces.sort(key=lambda f: math.hypot(*f[0][len(f[0]) // 2]))
    for pts, cls, name in faces:
        m = pts[len(pts) // 2]
        d = math.hypot(m[0] / SU, m[1] / 0.8)
        if hh >= H_target and d > core * 1.3:
            continue
        zone = _zone(d, core, tier)
        if not in_grid(*m) and zone in ("downtown", "inner"):
            zone = "middle"
        band = _band(d, core)
        if spec.get("upscale") and zone == "inner":
            zone = "upscale_inner"                           # (round the island's harbour: residences and terraces)
        elif spec.get("upscale") and zone != "downtown":
            band, zone = "estate", "estate"                  # (the rest of the island: estates)
        for side in (1, -1):
            for l in pl.frontage(pts, side, band, cls, use_fn=_use_fn(zone, tier, region, rng, cls), start=3.0, end=3.0):
                if _lot_slope(l["poly"], height) > LOT_SLOPE_MAX:
                    l["drop"] = True
                    continue
                l["zone"] = zone
                hh += _households(l)
    pl.lots = [l for l in pl.lots if not l.get("drop")]
    # ================= beyond the grid: neighbourhood pods of curving drives and courts =================
    if hh < H_target:
        hh = _pods(pl, spec, U, V, R_grid, H_target, hh, height, blocked, rng, lay, names)
    if tier in ("city", "town") and pop > 4000:
        _centres(pl, spec, U, V, rng)
    # ================= jobs: office blocks downtown, industrial parks at the edge (research/jobs) =================
    # (its own random stream, after everything else: the plan up to here is what it was without it)
    jobs = _jobs_pass(pl, spec, U, V, core, height, blocked)
    # the homes those lots had (flats over the shops, apartment blocks) built again as pods at the edge: the town keeps
    # its people (the user, 2026-10-08: "Do we still have the 240k population?")
    # (taller blocks on lots the town already has -- the inner apartments, nearest the heart, built a storey up to twice
    # the flats; a second round of pods laid its drives over the first's houses)
    lost = jobs.get("hh_lost", 0.0)
    ups = sorted([l for l in pl.lots if l["use"] in ("apartment", "apartment_court") and l.get("zone") in ("downtown", "inner", "middle")],
                 key=lambda l: math.hypot(sum(q[0] for q in l["poly"]) / 4, sum(q[1] for q in l["poly"]) / 4))
    for l in ups:
        if lost <= 0:
            break
        lost -= UNITS["apartment_big"] - UNITS[l["use"]]
        l["use"] = "apartment_big"
    hh -= max(0.0, lost)
    jobs["hh_unrestored"] = max(0.0, lost)
    stats = {"households": round(hh), "target": round(H_target), "lots": len(pl.lots), "streets": len(pl.streets),
             "stairs": len(pl.stairs), "landmarks": len(pl.landmarks), "institutions": placed}
    stats["walks"] = len(pl.walks)
    stats["jobs"] = jobs
    stats["waterfront_bldgs"] = len(pl.wbldgs)
    return {"streets": pl.streets, "stairs": pl.stairs, "lots": pl.lots, "areas": pl.areas, "marks": pl.marks,
            "centres": pl.centres, "landmarks": pl.landmarks, "walks": pl.walks, "wbldgs": pl.wbldgs, "parks": pl.parks, "stats": stats}


def _block_faces(pts, blk):
    """a long street cut into block-length faces (each face zoned for itself)"""
    P = densify(pts, 4.0)
    out, cur, L = [], [P[0]], 0.0
    for a, b in zip(P, P[1:]):
        cur.append(b)
        L += math.dist(a, b)
        if L >= blk:
            out.append(cur)
            cur, L = [b], 0.0
    if len(cur) > 1 and L > 20.0:
        out.append(cur)
    return out


def _pods(pl, spec, U, V, R_grid, H_target, hh, height, blocked, rng, lay, names):
    """postwar to current subdivisions in the sectors between the radials beyond the grid: concentric curving drives
    following the land, linked out to the collectors, houses both sides, a park in each pod; ring after ring until
    everyone's housed"""
    k = 0
    SU = getattr(pl, "SU", 1.0)
    wob = [rng.uniform(0, 2 * math.pi) for _ in range(4)]
    for ring_ in range(1, 40):
        r = R_grid * 1.12 + 95.0 * ring_
        if r > max(U / SU, V / 0.8) * 1.02:
            break
        band = "postwar" if ring_ <= 2 else ("suburban" if ring_ <= 5 else "late")
        if spec.get("upscale"):
            band = "estate"
        n = max(6, int(2 * math.pi * r / 330.0))
        for j in range(n):
            gap = 14.0 / r                                   # (a 14 m break between pods, whatever the radius)
            a0 = 2 * math.pi * j / n + gap
            a1 = 2 * math.pi * (j + 1) / n - gap
            amp = 9.0 + 3.0 * rng.random()
            pts = []
            # each sector's ring wanders in and out (the pods were platted one at a time, not by compass)
            stag = 26.0 * math.sin(3 * (a0 + a1) / 2 + wob[0]) + 18.0 * math.sin(7 * (a0 + a1) / 2 + wob[1] + ring_)
            for t in range(13):
                a = a0 + (a1 - a0) * t / 12
                rr = r + stag + amp * math.sin(t / 12 * math.pi * 2 + ring_)
                pts.append((SU * rr * math.cos(a), 0.8 * rr * math.sin(a)))
            roads = lay(pts, "drive", names.drive(k))
            # courts off the drive, every ~130 m, toward the next ring (the 1960s-90s cul-de-sac)
            for road in list(roads):
                P_ = densify(road, 4.0)
                for c_ in range(1, int(len(P_) * 4.0 / 130.0)):
                    p0 = P_[min(len(P_) - 1, int(c_ * 130.0 / 4.0))]
                    L0 = math.hypot(p0[0], p0[1]) or 1.0
                    dirx, diry = p0[0] / L0, p0[1] / L0
                    roads += lay([(p0[0] + dirx * 12, p0[1] + diry * 12), (p0[0] + dirx * 62, p0[1] + diry * 62)], "court", "")
            for road in roads:
                for sd in (1, -1):
                    for l in pl.frontage(road, sd, band, "drive", use_fn=_use_fn("outer", spec.get("tier", "town"), spec.get("region", "gl"), rng, "drive")):
                        if _lot_slope(l["poly"], height) > LOT_SLOPE_MAX:
                            l["drop"] = True
                            continue
                        l["zone"] = "outer"
                        hh += _households(l)
            k += 1
            # a short link out to the next ring or the collector
            if j % 2 == 0:
                a = (a0 + a1) / 2
                lay([(SU * r * math.cos(a), 0.8 * r * math.sin(a)), (SU * (r + 95.0) * math.cos(a), 0.8 * (r + 95.0) * math.sin(a))], "drive", "")
            if hh >= H_target:
                break
        if hh >= H_target:
            break
    pl.lots = [l for l in pl.lots if not l.get("drop")]
    return hh


# ------------------------------------------------------------------ helpers
def _dry_runs(pts, blocked):
    runs, cur = [], []
    for p in pts:
        if blocked(*p):
            if len(cur) > 1:
                runs.append(cur)
            cur = []
        else:
            cur.append(p)
    if len(cur) > 1:
        runs.append(cur)
    return runs


def _street_dist(pts):
    m = pts[len(pts) // 2]
    return min(math.hypot(*m), math.hypot(*pts[0]), math.hypot(*pts[-1]))


def _zone(d, core, tier):
    if d <= core:
        return "downtown"
    if d <= core * (1.9 if tier == "city" else 1.6):
        return "inner"
    if d <= core * (3.0 if tier == "city" else 2.6):
        return "middle"
    return "outer"


def _band(d, core):
    if d <= core * 1.2:
        return "rail"
    if d <= core * 2.0:
        return "streetcar"
    if d <= core * 3.0:
        return "interwar"
    if d <= core * 4.2:
        return "postwar"
    return "suburban"


def _use_fn(zone, tier, region, rng, cls):
    def pick(weights):
        tot = sum(weights.values())
        r = rng.random() * tot
        for k, w in weights.items():
            r -= w
            if r <= 0:
                return k
        return k
    if zone == "estate":
        return lambda k: "house"
    if zone == "upscale_inner":
        return lambda k: pick({"townhouse": 2.0, "apartment": 1.6, "house": 1.6})
    if zone == "downtown":
        if cls == "main" or rng.random() < 0.55:
            return lambda k: "store" if rng.random() < 0.88 else ("apartment" if tier == "city" else "store")
        return lambda k: pick({"store": 4, "apartment": 3 if tier == "city" else 1, "apartment_big": 1.5 if tier == "city" else 0,
                               "townhouse": 0.6})
    if zone == "inner":
        w = {"apartment": 3.0, "apartment_big": 1.2, "apartment_court": 1.6 if region == "ca" else 0.5, "townhouse": 1.4, "two_flat": 2.2,
             "duplex": 1.0, "house": 3.0} if tier == "city" else {"apartment": 0.8, "townhouse": 0.6, "two_flat": 1.0, "duplex": 0.8, "house": 6.0}
        return lambda k: pick(w)
    if zone == "middle":
        w = {"house": 6.0, "duplex": 1.6, "two_flat": 1.4, "townhouse": 0.6, "apartment_court": 0.8 if region == "ca" else 0.2,
             "apartment": 1.2} if tier == "city" else {"house": 8.0, "duplex": 1.0, "two_flat": 0.8, "apartment": 0.2,
                                                         "apartment_court": 0.4 if region == "ca" else 0.0}
        return lambda k: pick(w)
    if tier == "city":
        return lambda k: pick({"house": 8.5, "duplex": 1.0, "townhouse": 0.4, "apartment": 0.25})
    return lambda k: "house" if rng.random() < 0.93 else "duplex"


def _households(l):
    u = l["use"]
    if u == "store":
        return 1.5                                   # (flats above the shops)
    return UNITS.get(u, 1)


def _institutions(spec, pop, tier):
    """the research's ratios: an elementary school per ~5,000 people (Perry's unit), a high school per ~15,000, a fire
    station per ~12,000 (coverage), churches per ~1,800, a library, the post office, city hall, police, a hospital in a
    city; the spec may add or take away"""
    out = [("city_hall", 1), ("post_office", 1), ("library", 1 if pop > 2500 else 0), ("police", 1 if pop > 2000 else 0),
           ("fire_station", max(1, round(pop / 12000))), ("elementary", max(1, round(pop / 5000))),
           ("high_school", max(1 if pop > 4000 else 0, round(pop / 15000))), ("church", max(1, round(pop / 1800))),
           ("hospital", 1 if pop > 20000 else 0), ("clinic", 1 if 4000 < pop <= 20000 else 0)]
    extra = spec.get("institutions", {})
    d = dict(out)
    d.update(extra)
    return [(k, n) for k, n in d.items() if n > 0]


SITE_SIZE = {"city_hall": (40, 30), "post_office": (30, 26), "library": (30, 26), "police": (34, 26), "fire_station": (30, 26),
             "elementary": (190, 150), "high_school": (300, 230), "church": (26, 36), "hospital": (130, 110), "clinic": (40, 30)}
SITE_AREA = {"elementary": "schoolground", "high_school": "schoolground", "hospital": "campus"}


def _place_institutions(pl, insts, core, BK_U, BK_V, R_grid, height, blocked, rng, reserve, in_reserved):
    """civic buildings round the core's edge, schools at the neighbourhoods' centres and the hospital out toward the
    arterial: each on the first free, flat-enough site of a spiral of candidates out from where it belongs; a big site
    takes whole blocks (the streets go round it)"""
    placed = {}
    for kind, n in insts:
        for k in range(n):
            w, d = SITE_SIZE.get(kind, (30, 30))
            if kind in ("city_hall", "post_office", "library", "police", "church") and k == 0:
                r0 = core * 0.45
            elif kind == "elementary":
                r0 = R_grid * (0.55 + 0.35 * (k % 3))
            elif kind in ("high_school", "hospital"):
                r0 = R_grid * (0.9 + 0.3 * k)
            else:
                r0 = core * (0.9 + 0.7 * k)
            ok = False
            for tri in range(80):
                a = rng.random() * 2 * math.pi
                r = r0 * (1.0 + 0.05 * tri)
                cu, cv = r * math.cos(a), r * math.sin(a) * 0.8
                if abs(cv) < 30:                                    # (not astride Main)
                    cv = 30 + d / 2 if cv >= 0 else -30 - d / 2
                u0, u1, v0, v1 = cu - w / 2, cu + w / 2, cv - d / 2, cv + d / 2
                poly = rect(u0, u1, v0, v1)
                if not (pl.inside(poly) and pl.dry(poly)) or _lot_slope(poly, height) > 0.12:
                    continue
                if any(in_reserved(*q) for q in poly + [(cu, cv)]):
                    continue
                if any(blocked(cu + du, cv + dv) for du in (-w / 2, 0, w / 2) for dv in (-d / 2, 0, d / 2)):
                    continue
                reserve(u0, u1, v0, v1, SITE_AREA.get(kind), use=kind)
                ok = True
                break
            placed[kind] = placed.get(kind, 0) + (1 if ok else 0)
    return placed


def _edge_tracts(pl, spec, U, V, H_target, hh, height, blocked, rng, streets, lay):
    """postwar and later subdivisions beyond the grid: curving drives along the contour, each with houses both sides"""
    k = 0
    for ring_ in range(1, 6):
        for side in (1, -1):
            v_ = side * (V - 90.0 * ring_ + 40.0)
            pts = wavy(-U + 60, U - 60, v_, 10.0 + 4 * ring_, 380.0, 0.9 * ring_ + side)
            for road in lay(pts, "drive", spec.get("names", {}).get("drives", ["Ridge Dr", "Hillcrest Dr", "Valley View Dr", "Meadow Ln",
                                                                                "Overlook Dr", "Summit Ave", "Laurel Dr", "Cedar Ln",
                                                                                "Sunset Dr", "Bayview Dr"])[k % 10]):
                for sd in (1, -1):
                    for l in pl.frontage(road, sd, "postwar" if ring_ < 3 else "suburban", "drive", use_fn=lambda q: "house"):
                        if _lot_slope(l["poly"], height) > LOT_SLOPE_MAX:
                            l["drop"] = True
                            continue
                        l["zone"] = "outer"
                        hh += 1
            k += 1
            if hh >= H_target:
                pl.lots = [l for l in pl.lots if not l.get("drop")]
                return hh
    pl.lots = [l for l in pl.lots if not l.get("drop")]
    return hh


# research/jobs: the occupations people hold (the lives bake, 2026-10-08) as shares of a town's population -- the works'
# trades (factory hands, mechanics, drivers, dock workers, builders) ~9 %, the offices' (clerks, bankers, lawyers,
# editors beyond the upstairs offices) ~3.5 %; at 45 and 28 m2 of floor a job (planning densities)
IND_SHARE, OFF_SHARE = 0.09, 0.035
IND_M2, OFF_M2 = 45.0, 28.0
IND_COVER = 0.36


def _strip(pts, w):
    """a thin rectangle round a two-point line (the occupancy test of a connector street)"""
    (a, b), (c, d) = pts
    L = math.hypot(c - a, d - b) or 1.0
    nx, ny = -(d - b) / L * w / 2, (c - a) / L * w / 2
    return [(a + nx, b + ny), (c + nx, d + ny), (c - nx, d - ny), (a - nx, b - ny)]


def _jobs_pass(pl, spec, U, V, core, height, blocked):
    """office blocks: the downtown store lots nearest the heart become office blocks (lot.use "office", storeys by the
    town's size) until the town's office floor is met; industrial parks: centers.industrial_park sites fronting Main past
    the shopping centres, sized to the works' trades (one or two), their spine and loop streets laid as streets"""
    rng = random.Random(spec.get("seed", 1) * 7919 + 101)
    pop = spec["pop"]
    tier = spec.get("tier", "town")
    pl.parks = []
    out = {"office_lots": 0, "office_m2": 0, "parks": 0, "ind_m2": 0}
    if pop < 2000:
        return out
    # -- offices
    need = pop * OFF_SHARE * OFF_M2
    storeys = (6, 10) if pop > 30000 else ((4, 6) if pop > 8000 else (3, 4))
    cand = [l for l in pl.lots if l["use"] == "store" and l.get("zone") == "downtown"]
    cand.sort(key=lambda l: math.hypot(*(sum(q[i] for q in l["poly"]) / len(l["poly"]) for i in (0, 1))))
    got = 0.0
    for l in cand[1::2]:                                 # (every other one: the street keeps its shops between)
        if got >= need:
            break
        w = math.dist(l["poly"][0], l["poly"][1])
        d = math.dist(l["poly"][1], l["poly"][2])
        if w < 14.0 or d < 18.0:
            continue
        n = rng.randint(*storeys)
        out["hh_lost"] = out.get("hh_lost", 0.0) + _households(l)
        l["use"] = "office"
        l["storeys"] = n
        got += min(w, 40.0) * min(d - 3.5, 30.0) * (n - 1) * 0.8
        out["office_lots"] += 1
    out["office_m2"] = round(got)
    # -- industrial parks
    need = pop * IND_SHARE * IND_M2 / IND_COVER                 # (site m2)
    era = "rail" if spec.get("rail") else "postwar"
    n_parks = 2 if need > 250000 else 1
    each = need / n_parks
    left = n_parks
    st_pts = [q for st in pl.streets for q in st["pts"][::3]]
    for frac in (1.0, 0.7, 0.5, 0.35, 0.25):
        if left <= 0:
            break
        d = min(380.0, max(150.0, math.sqrt(each * frac) * 0.8))
        w = each * frac / d
        # every free, dry, flat rectangle of this size on a 40 m grid, the farthest from the heart first (industry at the
        # edge); its front (v0) toward the town's middle, a frontage street along it joined to the nearest street
        cands = []
        for iu in range(int(-U / 40), int(U / 40) + 1):
            for iv in range(int(-V / 40), int(V / 40) + 1):
                cu, cv = iu * 40.0, iv * 40.0
                if math.hypot(cu / max(U, 1), cv / max(V, 1)) < 0.45:
                    continue
                cands.append((-math.hypot(cu / max(U, 1), cv / max(V, 1)) + rng.random() * 0.05, cu, cv))
        cands.sort()
        for _, cu, cv in cands:
            if left <= 0:
                break
            side = 1 if cv >= 0 else -1                        # (the site runs away from Main: its front faces the middle)
            ua, ub = cu - w / 2, cu + w / 2
            va = abs(cv) - d / 2
            if va < ROW["main"] / 2 + 2.0:
                continue
            poly = rect(ua, ub, side * va, side * (va + d)) if side > 0 else rect(ua, ub, side * (va + d), side * va)
            if not (pl.inside(poly) and pl.occ.free(poly, shrink=1.0) and pl.dry(poly)):
                continue
            if any(blocked(ua + (ub - ua) * i / 6, side * (va + d * j / 4)) for i in range(7) for j in range(5)):
                continue
            if _lot_slope(poly, height) > 0.06:
                continue
            # the frontage street along the front, 8 m out, and a connector straight to the nearest street
            fv = side * (va - 8.0)
            front = [(ua, fv), (ub, fv)]
            mid = ((ua + ub) / 2, fv)
            near = min(st_pts, key=lambda q: math.dist(q, mid)) if st_pts else None
            if near is None or math.dist(near, mid) > 260.0:
                continue
            conn = [mid, near]
            # (the frontage street and the connector on free ground too: unchecked, they ran through whole rows of houses
            # -- 6,000 buildings left out across the map, 2026-10-08)
            if not pl.occ.free(_strip(front, 12.0), shrink=0.5):
                continue
            if math.dist(near, mid) > 14.0:
                a_ = (mid[0] + (near[0] - mid[0]) * 6.0 / math.dist(near, mid), mid[1] + (near[1] - mid[1]) * 6.0 / math.dist(near, mid))
                b_ = (near[0] - (near[0] - mid[0]) * 8.0 / math.dist(near, mid), near[1] - (near[1] - mid[1]) * 8.0 / math.dist(near, mid))
                if not pl.occ.free(_strip([a_, b_], 8.0), shrink=0.5):
                    continue
            plan = CT.industrial_park(CT.Site(0.0, ub - ua, 0.0, d), era, rng)
            fr = (lambda ua_, sd, va_: (lambda u, v: (ua_ + u, sd * (va_ + v))))(ua, side, va)
            pl.street(front, "street", spec["name"] + " Industrial Way")
            if math.dist(near, mid) > 6.0:
                pl.street(conn, "street", spec["name"] + " Industrial Way")
            for ln in plan["lines"]:
                pl.street([fr(*q) for q in ln["pts"]], "alley" if ln["cls"] == "alley" else "street", spec["name"] + " Industrial Way")
            pl.occ.poly(poly)
            pl.parks.append({"name": f"{spec['name']} {['Industrial Park', 'Works District'][len(pl.parks) % 2]}", "plan": plan,
                             "frame": (ua, side, va), "era": era})
            out["parks"] += 1
            out["ind_m2"] += plan["stats"]["built_sqft"] * 0.0929
            left -= 1
    # -- the old works district: where the parks fall short (a city built out to its edge), store and apartment lots by
    # the rail -- or round downtown's edge -- become multi-storey works lofts (urban_layout/07 §4: "the old district along
    # the rail and river, inside the town"; the retail traded out, the user's leave, 2026-10-08)
    short = pop * IND_SHARE * IND_M2 - out["ind_m2"]
    rail_v = spec.get("rail_v")
    if short > 4000.0:
        def cen(l):
            return (sum(q[0] for q in l["poly"]) / len(l["poly"]), sum(q[1] for q in l["poly"]) / len(l["poly"]))

        def near_rail(l):
            c = cen(l)
            return abs(c[1] - rail_v(c[0])) if rail_v else abs(math.hypot(c[0] / max(core, 1.0), c[1] / max(core * 0.8, 1.0)) - 1.15) * core
        cand = [l for l in pl.lots if l["use"] in ("store", "apartment", "apartment_big") and l.get("zone") in ("downtown", "inner")]
        cand.sort(key=near_rail)
        n_l = 0
        for l in cand:
            if short <= 0 or n_l >= (150 if pop > 30000 else 80):
                break
            w = math.dist(l["poly"][0], l["poly"][1])
            d = math.dist(l["poly"][1], l["poly"][2])
            if w < 16.0 or d < 22.0 or rng.random() < 0.35:   # (not every lot: the street keeps some of its life)
                continue
            n = rng.choice([3, 4, 4, 5])
            out["hh_lost"] = out.get("hh_lost", 0.0) + _households(l)
            l["use"] = "works_loft"
            l["storeys"] = n
            short -= min(w - 6.0, 60.0) * min(d - 8.0, 34.0) * n * 0.85
            n_l += 1
        out["lofts"] = n_l
        out["ind_m2"] = round(pop * IND_SHARE * IND_M2 - max(short, 0.0))
    out["ind_m2"] = round(out["ind_m2"])
    return out


def _centres(pl, spec, U, V, rng):
    kinds = ["community", "neighborhood", "convenience"] if spec["pop"] > 20000 else ["neighborhood", "convenience"]
    for k, kind in enumerate(kinds):
        u0 = (U - 320.0) * (1 if k % 2 == 0 else -1)
        if u0 < 0:
            u0, u1 = u0, u0 + 200.0
        else:
            u1 = u0 + 200.0
        d = CT.strip_site(kind, rng)[1]
        site = CT.Site(min(u0, u1), max(u0, u1), ROW["main"] / 2, ROW["main"] / 2 + d, None)
        poly = rect(min(u0, u1), max(u0, u1), ROW["main"] / 2, ROW["main"] / 2 + d)
        if not (pl.inside(poly) and pl.dry(poly) and pl.occ.free(poly, shrink=0.5)):
            continue
        plan = CT.strip_center(site, kind, rng)
        pl.occ.poly(poly)
        pl.centres.append({"name": f"{spec['name']} {['Plaza', 'Commons', 'Corners', 'Square'][k % 4]}", "kind": kind, "plan": plan,
                           "v_road": 0.0, "dirn": 1, "u": (min(u0, u1), max(u0, u1))})


class _Namer:
    """street names by the region's habits: New England's Elm / Pleasant / School / Water; California's Spanish names
    (Calle, Avenida) beside the trees and the presidents; the Midwest's numbered streets and the founders"""
    NE = ["Water St", "Front St", "Elm St", "Pleasant St", "School St", "Church St", "High St", "Union St", "Federal St", "Pearl St",
          "Winter St", "Spring St", "Middle St", "Fore St", "Exchange St", "Cumberland Ave", "Congress St", "Chestnut St", "Oak St",
          "Pine St", "Maple St", "Summer St", "Granite St", "Ocean Ave", "Washington St", "Prospect St", "Mechanic St", "Free St"]
    CA = ["Calle Real", "Avenida del Mar", "State St", "Anacapa St", "Calle Mayor", "Paseo Nuevo", "Mission St", "Avenida Granada",
          "De la Guerra St", "Carrillo St", "Figueroa St", "Cota St", "Haley St", "Ortega St", "Cabrillo Blvd", "Avenida Pico",
          "Calle Las Palmas", "Olive St", "Laguna St", "Garden St", "Santa Rosa St", "Victoria St", "Arrellaga St", "Micheltorena St"]
    GL = ["Market St", "Water St", "Railroad Ave", "Court St", "Locust St", "Walnut St", "Chestnut St", "Elm St", "Oak St",
          "Maple St", "Cherry St", "Pine St", "Spruce St", "Mulberry St", "Hickory St", "Sycamore St", "Buckeye St", "Lincoln Ave",
          "Jefferson St", "Madison St", "Monroe St", "Jackson St", "Grant Ave", "Garfield Ave"]

    def __init__(self, spec, rng):
        self.spec = spec
        base = {"ne": self.NE, "ca": self.CA}.get(spec.get("region", "gl"), self.GL)
        self.pool = list(base)
        rng.shuffle(self.pool)
        self.used = {}
        self.k = 0

    def _take(self, key):
        if key not in self.used:
            self.used[key] = self.pool[self.k % len(self.pool)] if self.k < len(self.pool) else f"{self.k + 1}th St"
            self.k += 1
        return self.used[key]

    def parallel(self, v):
        n = int(round(abs(v) / 90.0))
        if self.spec.get("region") == "gl" and n <= 9:
            return ("N " if v > 0 else "S ") + ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"][n - 1] + " St"
        return self._take(("p", round(v)))

    def cross(self, u):
        return self._take(("c", round(u)))

    def radial(self, k):
        r = {"ne": ["Shore Rd", "Ledge Rd", "Old County Rd", "Back Cove Rd", "Pond Rd", "Mill Rd"],
             "ca": ["Camino Real", "Canyon Rd", "Avenida Las Lomas", "Mesa Dr", "Ranch Rd", "Arroyo Rd"]}.get(self.spec.get("region"),
             ["Mill Rd", "County Line Rd", "Pike Rd", "Plank Rd", "Station Rd", "Orchard Rd"])
        return r[k % len(r)]

    def drive(self, k):
        r = {"ne": ["Bayview Dr", "Spruce Ln", "Highland Ave", "Ledgewood Dr", "Birch Rd", "Harbor View Dr", "Juniper Ln", "Cliff St",
                    "Fern Ln", "Larch Dr", "Hemlock Dr", "Osprey Ln", "Heron Way", "Woodland Rd", "Puffin Ln", "Lighthouse Rd"],
             "ca": ["Vista del Mar", "Calle Serena", "Via Sol", "Avenida Las Brisas", "Calle Arroyo", "Via Montana", "Paseo Del Sol",
                    "Camino Laguna", "Via Verde", "Calle Bonita", "Via Escondida", "Avenida Cielo", "Calle Pacifica", "Via Corona",
                    "Paseo Real", "Calle Luna"]}.get(self.spec.get("region"),
             ["Meadow Ln", "Hillcrest Dr", "Valley View Dr", "Orchard Dr", "Fox Run", "Prairie Dr", "Willow Dr", "Sunset Dr",
              "Ridge Rd", "Cardinal Dr", "Robin Ln", "Clover Ln", "Briarwood Dr", "Timber Ln", "Harvest Dr", "Brookside Dr"])
        return r[k % len(r)] if k < len(r) else r[k % len(r)].replace(" Dr", " Ct").replace(" Ln", " Ct")


# ------------------------------------------------------------------ structures for the records
KIND = {"house": "house", "duplex": "house", "two_flat": "house", "townhouse": "townhouse", "apartment": "condo", "apartment_big": "condo",
        "apartment_court": "condo", "store": "store", "church": "church", "city_hall": "civic", "police": "civic", "fire_station": "civic",
        "post_office": "civic", "library": "civic", "hospital": "civic", "clinic": "civic", "elementary": "school", "high_school": "school",
        "college": "school"}


def _trim_front(poly, by):
    (a, b_, c, d) = poly
    nx, ny = d[0] - a[0], d[1] - a[1]
    L = math.hypot(nx, ny) or 1.0
    nx, ny = nx / L * by, ny / L * by
    return [(a[0] + nx, a[1] + ny), (b_[0] + nx, b_[1] + ny), c, d]


def _number(poly, blk=100.0):
    a, b_ = poly[0], poly[1]
    cu, cv = (a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2
    along_u = abs(b_[0] - a[0]) > abs(b_[1] - a[1])
    coord = cu if along_u else cv
    side = poly[3][1] - a[1] if along_u else poly[3][0] - a[0]
    return 100 * (int(abs(coord) // blk) + 1) + 2 * int((abs(coord) % blk) / blk * 48) + (1 if side > 0 else 0)


HEART_LANDMARKS = ("courthouse", "courthouse_tower", "city_hall_deco")


def _bbox(poly):
    return (min(q[0] for q in poly), max(q[0] for q in poly), min(q[1] for q in poly), max(q[1] for q in poly))


def _overlap(a, b):
    return min(a[1], b[1]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[2], b[2])


def _on_rail(bb, spec, margin=10.0):
    """the box reaches within margin m of the town's railway (rail towns: spec rail_v(u))"""
    rv = spec.get("rail_v")
    if not rv:
        return False
    for k in range(9):
        u = bb[0] + (bb[1] - bb[0]) * k / 8
        v = rv(u)
        if bb[2] - margin < v < bb[3] + margin:
            return True
    return False


def _site_clear(bb, street_pts, margin=12.0):
    """no street within margin m of the box (its kerb and sidewalk clear of the building)"""
    return not any(bb[0] - margin < q[0] < bb[1] + margin and bb[2] - margin < q[1] < bb[3] + margin for q in street_pts)
HEART_INSET = 12.0          # m of lawn round a courthouse in its square (and round any site BIG_SITE m long: a works' yard)
BIG_SITE = 100.0
MEETING_SHIFT = 36.0        # m the meetinghouse moves back onto the green (its reserve ran BK_U-6..BK_U+22 over the cross street)


def structures(p, spec, uv, region_at=None):
    """every building of a plan in map order: lots (front edge first), shopping centres, landmarks; ids <PREFIX>-0001..."""
    import calder as CAL
    out = []
    # the meetinghouse is its landmark only (its reserve also made a plain church lot: two churches built into each other)
    meeting = {lm.get("label") for lm in p["landmarks"] if lm.get("kind") == "meetinghouse"}
    for l in p["lots"]:
        poly = l["poly"]
        if l["use"] in ("house", "duplex", "two_flat"):
            trim = max(0.0, min(float(l.get("setback", 4.0)) - 3.0, math.dist(poly[1], poly[2]) - 20.0))
            poly = _trim_front(poly, trim)
        ring = uv(poly)
        lw, ld = math.dist(ring[0], ring[1]), math.dist(ring[1], ring[2])
        units = l.get("units") or UNITS.get(l["use"])
        if l["use"] == "church" and l.get("label") in meeting:
            out.append(dict(_skip=True))                  # (numbered, then left out: the ids after it keep their models)
            continue
        e = dict(use=l["use"], band=l["band"], poly=ring, lot_w=lw, lot_d=ld, face=l.get("face"), label=l.get("label"),
                 units=units, alley=l["band"] in ("rail", "streetcar"), zone=l.get("zone"),
                 number=_number(l["poly"]) if l["use"] in ("house", "duplex", "two_flat") else None,
                 kind=KIND.get(l["use"], "store"))
        if l["use"] in ("apartment", "apartment_big", "apartment_court"):
            e["use"] = "apartment"
            e["storeys"] = {"apartment": 3, "apartment_big": 4, "apartment_court": 2}[l["use"]]
        if l["use"] == "office":
            e["storeys"] = l["storeys"]
            e["kind"] = "store"
        if l["use"] == "works_loft":
            e["use"], e["role"], e["storeys"], e["era"], e["kind"] = "industry", "manufacturing", l["storeys"], "rail", "industrial"
        out.append(e)
    for c in p["centres"]:
        frame = (lambda c_: (lambda u, v: uv([(u, c_["v_road"] + c_["dirn"] * v)])[0]))(c)
        for e in CAL.centre_structures(c, frame, 1985):
            e["kind"] = CAL.KIND.get(e["use"], "strip")
            out.append(e)
    from records import LANDMARK_RECIPE
    street_pts = [q for st in p["streets"] for q in densify(st["pts"], 4.0)]
    # 1. each landmark's site as built
    sites = {}
    for n_, lm in enumerate(p["landmarks"]):
        if "poly" not in lm:
            continue
        poly = lm["poly"]
        if not lm.get("ring"):
            us_, vs_ = [q[0] for q in poly], [q[1] for q in poly]
            cu, cv = (min(us_) + max(us_)) / 2, (min(vs_) + max(vs_)) / 2
            if lm["kind"] in HEART_LANDMARKS or max(max(us_) - min(us_), max(vs_) - min(vs_)) >= BIG_SITE:
                # the courthouse stands in its square, a lawn all round: the square is the whole block, streets on every
                # side (built to the block's edge it stood in all four: placement left every one out, 2026-10-07)
                m = min(HEART_INSET, 0.2 * (max(us_) - min(us_)), 0.2 * (max(vs_) - min(vs_)))
                poly = [(q[0] + (m if q[0] < cu else -m), q[1] + (m if q[1] < cv else -m)) for q in poly]
            elif lm["kind"] == "meetinghouse":
                # on the green's far end, not across the cross street at the block's end (its reserve straddled it)
                poly = [(q[0] - MEETING_SHIFT, q[1]) for q in poly]
        sites[n_] = poly
    # 2. landmark buildings sited "near" the same anchor (Kessler's works, station and roundhouse by the rail; Oceanview's
    # carousel on its casino): the largest first, each smaller one steps aside -- the nearest spot along u (a rail landmark
    # keeps to the rail, a beach one to the beach), then across, clear of the plan's streets, the railway and the others
    # -- or, with nowhere clear, stays (placement settles it)
    blds = [n_ for n_, lm in enumerate(p["landmarks"]) if n_ in sites and not lm.get("ring") and lm["kind"] in LANDMARK_RECIPE]
    blds.sort(key=lambda n_: -((_bbox(sites[n_])[1] - _bbox(sites[n_])[0]) * (_bbox(sites[n_])[3] - _bbox(sites[n_])[2])))
    taken_lm = []
    for n_ in blds:
        bb = _bbox(sites[n_])
        hit = [b_ for b_ in taken_lm if _overlap(bb, b_)]
        if hit:
            ou = max(min(bb[1], b_[1]) - max(bb[0], b_[0]) for b_ in hit)
            ov = max(min(bb[3], b_[3]) - max(bb[2], b_[2]) for b_ in hit)
            cands = sorted({(sg * (ou + 6.0 + k * 12.0), 0.0) for sg in (1, -1) for k in range(25)}
                           | {(0.0, sg * (ov + 6.0 + k * 12.0)) for sg in (1, -1) for k in range(4)},
                           key=lambda c: abs(c[0]) + abs(c[1]))
            for du, dv in cands:
                nb = (bb[0] + du, bb[1] + du, bb[2] + dv, bb[3] + dv)
                if _site_clear(nb, street_pts) and not _on_rail(nb, spec) and not any(_overlap(nb, o_) for o_ in taken_lm):
                    sites[n_] = [(q[0] + du, q[1] + dv) for q in sites[n_]]
                    bb = nb
                    break
        taken_lm.append(bb)
    # 3. in the plan's order (the ids follow it)
    for n_, lm in enumerate(p["landmarks"]):
        if n_ not in sites or lm["kind"] not in LANDMARK_RECIPE:
            continue                                      # (open spaces and waterfront pieces: areas and walks, not buildings)
        poly = sites[n_]
        ring = poly if isinstance(poly[0], (list, tuple)) and lm.get("ring") else uv(poly)
        out.append(dict(use="landmark", landmark=lm["kind"], label=lm.get("label"), poly=ring, lot_w=math.dist(ring[0], ring[1]),
                        lot_d=math.dist(ring[1], ring[2]), band="interwar", kind="landmark"))
    for b in p.get("wbldgs", []):
        ring = uv(b["poly"])
        out.append(dict(use=b["kind"], label=b.get("label"), poly=ring, lot_w=math.dist(ring[0], ring[1]), lot_d=math.dist(ring[1], ring[2]),
                        band="interwar", kind=b["kind"], over_water=not b.get("land"), members=b.get("members"), slips=b.get("slips"),
                        area_m2=b.get("area_m2")))
    # 4. the industrial parks' buildings -- last, so every id before them is what it was (research/jobs); each ring from
    # its front edge, the side facing its spine road (the office and car park are in front, the docks behind)
    for pk in p.get("parks", []):
        ua, side, va = pk["frame"]
        spines = [ln["pts"][0][0] for ln in pk["plan"]["lines"] if ln.get("what") == "spine"]
        for b in pk["plan"]["buildings"]:
            us_ = [q[0] for q in b["poly"]]
            vs_ = [q[1] for q in b["poly"]]
            a_, b_, c_, d_ = min(us_), max(us_), min(vs_), max(vs_)
            sp = min(spines, key=lambda s_: min(abs(s_ - a_), abs(s_ - b_))) if spines else a_
            if abs(sp - a_) <= abs(sp - b_):
                loc = [(a_, d_), (a_, c_), (b_, c_), (b_, d_)]
            else:
                loc = [(b_, c_), (b_, d_), (a_, d_), (a_, c_)]
            ring = uv([(ua + u, side * (va + v)) for u, v in loc])
            out.append(dict(use="industry", role=b.get("role"), tenant=b.get("tenant"), poly=ring, lot_w=math.dist(ring[0], ring[1]),
                            lot_d=math.dist(ring[1], ring[2]), band="postwar", kind="industrial", park=pk["name"], era=pk["era"]))
    pre = spec.get("prefix") or spec["name"][:3].upper()
    for k, e in enumerate(out, 1):
        e["id"] = "%s-%04d" % (pre, k)
    out = [e for e in out if not e.get("_skip")]
    for e in out:
        if "stores_t" in e:
            from records import TENANT_TYPE
            e["stores"] = [{"type": TENANT_TYPE.get(t, "variety_store"), "tenant": t} for t in e.pop("stores_t")]
        if region_at:
            e["region"] = region_at(e["poly"])
    return out


# ------------------------------------------------------------------ the waterfront (research/waterfront/README.md)
def club_scale(pop, resort):
    """research/waterfront 4: members 0.2-0.3 % of a working city (1-2 % of a resort / summer town), floor 80; slips
    0.3 a member for a marina club; clubhouse 120 m2 + 0.7 m2 a member"""
    members = max(80, int(pop * (0.012 if resort else 0.005)))
    return members, int(members * 0.32), 120.0 + 0.7 * members


def _shore(blocked, U, V, step=10.0):
    """the shore in the plan frame: for each u, the first v (walking from 0 toward -V) that is water; None where dry"""
    out = {}
    u = -U
    while u <= U:
        v = 0.0
        hit = None
        while v > -V:
            if blocked(u, v):
                hit = v
                break
            v -= step
        out[round(u)] = hit
        u += step
    return out


def waterfront(pl, spec, blocked, U, V, rng, wet=None):
    """the waterfront the town's kind calls for, laid along the real shore: walks (boardwalks, promenades, piers,
    wharves, docks, beach stairs and ramps), over-water buildings, the beach, the marina, the yacht club, the launch, the
    light.  wet(u, v): the water itself (blocked is water + other towns; the waterfront wants only the water)"""
    wet = wet or blocked
    tier, region, arch = spec.get("tier", "town"), spec.get("region", "gl"), spec.get("archetype", "")
    pl.walks = getattr(pl, "walks", [])
    pl.wbldgs = getattr(pl, "wbldgs", [])
    sh = _shore(wet, U, V)
    us = sorted(u for u, v in sh.items() if v is not None)
    if len(us) < 6:
        return
    # the town's stretch of shore (within the downtown and inner zones along u)
    reach = min(U, 90.0 + 2.2 * math.sqrt(spec["pop"])) * (3.2 if tier == "city" else 2.6)
    line = [(u, sh[u]) for u in us if abs(u) <= reach]
    if len(line) < 6:
        return
    beachy = region == "ca" or arch in ("resort_town", "boardwalk_resort", "pier_town", "lake_resort") or spec.get("lake")
    harbor = region == "ne" or arch in ("port_city", "harbor_city", "inlet_harbor", "fishing_village", "island_village")
    W_bw = {"city": 14.0, "town": 9.0, "village": 4.0}[tier]
    beach_w = {"ca": 70.0, "ne": 30.0, "gl": 45.0, "isle": 40.0}.get(region, 45.0) if beachy else 0.0
    # 1. the beach and its boardwalk / promenade at the back of it
    if beachy:
        walk = [(u, v + beach_w) for u, v in line]
        pl.walks.append({"pts": walk, "w": W_bw, "kind": "boardwalk" if region != "ca" or arch == "boardwalk_resort" else "promenade"})
        beach = [(u, v - 20.0) for u, v in line] + [(u, v + beach_w - W_bw / 2) for u, v in reversed(line)]
        pl.areas.append({"poly": beach, "kind": "beach"})
        pl.occ.poly(beach)                                   # (no lots on the sand)
        pl.occ.line(walk, W_bw + 4.0)
        # stairs at every block (~100 m), ADA ramps every ~550 m, comfort stations every ~1 km (README 1)
        L = 0.0
        last_s = last_r = last_c = -1e9
        for (u0, v0), (u1, v1) in zip(walk, walk[1:]):
            L += math.dist((u0, v0), (u1, v1))
            if L - last_s >= 100.0:
                pl.walks.append({"pts": [(u1, v1 - W_bw / 2), (u1, v1 - W_bw / 2 - 9.0)], "w": 2.4, "kind": "beach_stair"})
                last_s = L
            if L - last_r >= 550.0:
                pl.walks.append({"pts": [(u1 + 4, v1 - W_bw / 2), (u1 + 4, v1 - W_bw / 2 - 16.0)], "w": 2.0, "kind": "beach_ramp"})
                last_r = L
            if L - last_c >= 1000.0:
                pl.wbldgs.append({"poly": rect(u1 - 6, u1 + 6, v1 + W_bw / 2 + 2, v1 + W_bw / 2 + 12), "kind": "comfort_station", "land": True})
                last_c = L
    # 2. the pier (landmark "pier"): straight out from the shore nearest the centre; foot / neck / mid / head (README 2)
    for lm in spec.get("landmarks", []):
        if lm["kind"] != "pier":
            continue
        L = lm.get("length", 300.0)
        u0 = min(us, key=lambda u: abs(u - 60.0))
        v0 = sh[u0] + beach_w
        w = 9.0 if L < 400 else 11.0
        pl.walks.append({"pts": [(u0, v0), (u0, sh[u0] - L)], "w": w, "kind": "pier", "label": lm.get("label")})
        pl.wbldgs.append({"poly": rect(u0 - 22, u0 - 8, v0 + 2, v0 + 16), "kind": "restaurant", "land": True, "label": "Pier Grill"})
        pl.wbldgs.append({"poly": rect(u0 + 8, u0 + 16, v0 + 2, v0 + 10), "kind": "bait", "land": True})
        pl.wbldgs.append({"poly": rect(u0 + 18, u0 + 26, v0 + 2, v0 + 12), "kind": "lifeguard", "land": True})
        mid = sh[u0] - L * 0.55
        pl.walks.append({"pts": [(u0 - 9, mid), (u0 + 9, mid)], "w": 18.0, "kind": "pier_platform"})
        pl.wbldgs.append({"poly": rect(u0 - 3, u0 + 3, mid - 3, mid + 3), "kind": "kiosk"})
        head = sh[u0] - L
        hw = 16.0 if L >= 400 else 12.0
        pl.walks.append({"pts": [(u0 - hw, head), (u0 + hw, head)], "w": hw * 2, "kind": "pier_head"})
        pl.wbldgs.append({"poly": rect(u0 - 9, u0 + 9, head - 7, head + 7), "kind": "restaurant", "label": lm.get("head_label", "End of the Pier Diner")})
    # 3. a harbour's wharves along the cove (New England ports and fishing towns): every ~85 m a wharf, sheds on it
    if harbor and region != "ca":
        n = 0
        for u in us:
            if abs(u) > reach * 0.55 or (u % 85) > 10 or sh[u] is None:
                continue
            Lw = rng.uniform(60, 150) if tier == "city" else rng.uniform(40, 90)
            ww = rng.uniform(14, 20)
            v0 = sh[u] + 4
            pl.walks.append({"pts": [(u, v0), (u, sh[u] - Lw)], "w": ww, "kind": "wharf"})
            for k in range(int(Lw / 30)):
                cv = sh[u] - 12 - k * 30
                pl.wbldgs.append({"poly": rect(u - ww / 2 + 1, u + ww / 2 - 1, cv - 9, cv), "kind": rng.choice(["fishhouse", "shed", "fishhouse", "shingle"])})
            n += 1
        if tier == "city":
            u = min(us, key=lambda q: abs(q - reach * 0.35))
            pl.walks.append({"pts": [(u, sh[u] + 4), (u, sh[u] - 180)], "w": 60.0, "kind": "fish_pier", "label": "Fish Pier"})
            pl.wbldgs.append({"poly": rect(u - 25, u + 25, sh[u] - 120, sh[u] - 60), "kind": "cannery", "label": "Fish Pier Cold Storage"})
    # 4. the marina, its yacht club and the launch (README 3 and 4): at the quieter end of the stretch
    if spec.get("waterfront") and tier in ("city", "town") or harbor:
        resort = arch in ("boardwalk_resort", "resort_town", "lake_resort", "pier_town") or tier == "village"
        members, slips, club_m2 = club_scale(spec["pop"], resort)
        end_u = max(us) if (sum(1 for u in us if u > 0) >= sum(1 for u in us if u < 0)) else min(us)
        mu = min((u for u in us if abs(u) <= reach), key=lambda u: abs(u - 0.75 * end_u if end_u > 0 else u - 0.75 * end_u))
        mv = sh[mu]
        # docks: a main float parallel to the shore 25 m out, fingers every 4.5 m
        span = min(260.0, slips * 4.5 / 2 + 40)
        pl.walks.append({"pts": [(mu, mv + 2), (mu, mv - 25)], "w": 3.0, "kind": "dock"})
        pl.walks.append({"pts": [(mu - span / 2, mv - 25), (mu + span / 2, mv - 25)], "w": 3.0, "kind": "dock"})
        f = mu - span / 2 + 3
        while f < mu + span / 2 - 3:
            pl.walks.append({"pts": [(f, mv - 26), (f, mv - 37)], "w": 1.0, "kind": "finger"})
            pl.walks.append({"pts": [(f, mv - 24), (f, mv - 13)], "w": 1.0, "kind": "finger"})
            f += 4.5
        side = math.sqrt(club_m2) * 1.25
        cu = mu - span / 2 - side / 2 - 10
        name = {"ne": f"{spec['name']} Yacht Club", "ca": f"{spec['name']} Yacht Club", "gl": f"{spec['name']} Yacht Club"}.get(region, f"{spec['name']} Yacht Club")
        pl.wbldgs.append({"poly": rect(cu - side / 2, cu + side / 2, mv + 6, mv + 6 + side), "kind": "clubhouse", "land": True, "label": name,
                          "members": members, "slips": slips, "area_m2": round(club_m2)})
        pl.areas.append({"poly": rect(cu - side / 2 - 30, cu - side / 2 - 4, mv + 4, mv + 40), "kind": "dry_sail"})
        # the launch: lanes by tier (city 3, town 2, village 1), 30-40 trailer stalls a lane
        lanes = {"city": 3, "town": 2, "village": 1}[tier]
        lu = mu + span / 2 + 20
        pl.areas.append({"poly": rect(lu, lu + 4.2 * lanes, mv + 18, mv - 14), "kind": "boat_ramp"})
        pl.walks.append({"pts": [(lu - 2, mv + 4), (lu - 2, mv - 18)], "w": 2.0, "kind": "courtesy_dock"})
        stalls = lanes * 35
        rows = max(1, int(math.ceil(stalls / 20)))
        pl.areas.append({"poly": rect(lu - 10, lu + 64, mv + 22, mv + 22 + rows * 30), "kind": "trailer_parking"})
        pl.occ.poly(rect(lu - 10, lu + 64, mv + 4, mv + 22 + rows * 30))
        pl.occ.poly(rect(cu - side / 2 - 30, cu + side / 2, mv + 4, mv + 8 + side))
    # 5. the light: on the most seaward shore point at the stretch's end (the cove's arm, the sheltering point)
    for lm in spec.get("landmarks", []):
        if lm["kind"] in ("lighthouse", "breakwater_light"):
            far = min(line, key=lambda p: p[1])
            pl.wbldgs.append({"poly": rect(far[0] - 4, far[0] + 4, far[1] - 2, far[1] + 6), "kind": "lighthouse", "label": lm.get("label"),
                              "land": True})


# ------------------------------------------------------------------ records and the model library
def library_key(rec):
    """what makes two buildings the same model (the user, 2026-10-07: "you can reuse some buildings"; 55,000 unique models
    would be ~230 GB): kind, region, form, size class; colours and names are not in it (the first record of a key is built,
    the rest are placed as it)"""
    k = rec.get("kind")
    tr = rec.get("traits") or {}
    lot = rec.get("lot") or {}
    reg = rec.get("region", "gl")
    b2 = lambda v, q: int(round((v or 0) / q))
    if k == "house":
        roof = tr.get("roof") or {}
        porch = (tr.get("porch") or {}).get("type")
        return ("house", reg, tr.get("archetype"), tr.get("storeys"), tr.get("walls"), roof.get("material"), roof.get("type"), porch,
                tr.get("garage"), tr.get("units", 1), b2(lot.get("w"), 3.0), b2(lot.get("d"), 6.0))
    if k == "townhouse":
        return ("townhouse", reg, tr.get("units"), tr.get("walls"), b2(lot.get("w"), 4.0))
    if k == "condo":
        return ("condo", reg, tr.get("storeys"), tr.get("units"), tr.get("walls"), tr.get("form"), b2(lot.get("w"), 6.0), b2(lot.get("d"), 6.0))
    return None                                          # (stores, civic, landmarks, centres: each its own model -- signs, names)


LIB_CAP = int(os.environ.get("SSC_LIB_CAP", "40") or 0)   # models per group before lots take the nearest fitting one (0: no
                                                          # cap: ~24,000 models, ~110 GB; 40: ~5,400)


def _lib_group(key):
    """the coarse kind a capped library shares across: a house's region, form and storeys; a row's or a block's region"""
    return key[:4] if key[0] == "house" else key[:2]


def _library_fit(library, key, rec):
    """with LIB_CAP set and the key's group full: the group's model whose lot fits this one best -- never one built for a lot
    wider (by over 1.5 m) or deeper (by over 3 m) than this, so it can't reach over the lot line; None: build a new one"""
    if not LIB_CAP:
        return None
    grp = library.get("__groups__", {}).get(_lib_group(key), [])
    if len(grp) < LIB_CAP:
        return None
    lot = rec.get("lot") or {}
    w, d = float(lot.get("w") or 0), float(lot.get("d") or 0)
    best, cost = None, 1e9
    for mw, md, mid in grp:
        if mw > w + 1.5 or md > d + 3.0 or w - mw > 6.0 or d - md > 15.0:
            continue
        c = (w - mw) / 3.0 + (d - md) / 6.0
        if c < cost:
            best, cost = mid, c
    return best


def write_records(structs, town, seed, out_dir=None, library=None):
    """a record per structure; library: {key: model id} shared across towns (a model built for one town is placed in the next)"""
    import json
    import os
    import records as RC
    out_dir = out_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "remake", "catalog")
    rules = RC.Rules(seed)
    library = library if library is not None else {}
    built = reused = 0
    for e in structs:
        if e.get("stores"):
            r = RC.rnd_for(seed, e["id"], "names")
            e["stores"] = [dict(RC.business(r, st["type"], rules.surnames, town, [town, "Main Street", "Harbor", "Bay", "Point", "Hill"]),
                                tenant=st["tenant"]) for st in e["stores"]]
        rec = RC.make_record(e, rules, town, seed)
        if e.get("over_water"):
            rec.setdefault("traits", {})["over_water"] = True
        key = library_key(rec)
        if key is not None:
            model = library.get(key) or _library_fit(library, key, rec)
            if model:
                rec["model"] = model
                e["model"] = model
                reused += 1
            else:
                library[key] = rec["id"]
                lot = rec.get("lot") or {}
                library.setdefault("__groups__", {}).setdefault(_lib_group(key), []).append(
                    (float(lot.get("w") or 0), float(lot.get("d") or 0), rec["id"]))
                built += 1
        else:
            built += 1
        # (unchanged records keep their file and its time: tools/build_library.py rebuilds what's newer than its glb)
        txt = json.dumps(rec, indent=1)
        fp = os.path.join(out_dir, rec["id"] + ".json")
        if not os.path.exists(fp) or open(fp).read() != txt:
            with open(fp, "w") as f:
                f.write(txt)
    return built, reused
