#!/usr/bin/env python3
"""Road furniture by the Space Station Columbia road standard (research/roads/SSC_ROAD_STANDARD.md).

Reads the game's roads (godot_project/remake/terrain.json), the placed structures (placement.json)
and the land cover (landcover.png: built-up area) and writes godot_project/remake/road_furniture.json,
which MapRoads (markings, curbs and gutters, gravel shoulders) and RoadFurniture (signs, signals,
level crossings) build in the game:

  ctx      per road, one letter per centreline point: r rural / t town / c core (§1)
  jn       per road, one letter per point: 1 where the point is inside another road (a junction:
           no curb, no line)
  lines    painted lines: road, point range, sideways offset, colour, width, dash (§3)
  bars     painted quads (stop lines, crosswalk bars): 4 corners (s, x)
  decals   textured road markings (RXR): centre, heading, size, atlas cell
  signs    type (an atlas cell), position, facing, mounting height, optional text (§4)
  xings    rail level crossings: position, road heading, rail heading, protection level (§5)
  signals  junctions with traffic signals: centre and each approach's heading

Run after tools/map_expanded.py --game-data and remake/tools/placement.py:
    python3 tools/road_furniture.py
It also draws the sign face atlas (godot_project/remake/textures/road_signs.png).
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GD = os.path.join(ROOT, "godot_project", "remake")
R = json.load(open(os.path.join(GD, "terrain.json")))["R"]          # (the ring's radius from the map)
C = 2 * math.pi * R
HW = json.load(open(os.path.join(GD, "terrain.json")))["W"] / 2 if os.path.exists(os.path.join(GD, "terrain.json")) else 6000.0
RANK = {"alley": 0, "gravel": 1, "street": 2, "county": 3, "main": 4, "hwy": 5}
PAVED = ("street", "county", "main", "hwy")
LIMIT = {"hwy": (60, 90), "county": (50, 70), "main": (40, 40), "street": (40, 60), "gravel": (60, 60), "alley": (15, 15)}

# the sign atlas: 8 x 8 cells of 256 px (tools/sign_atlas.py).  name -> (cell, width m, height m, back cell)
CELL_PX = 256
SIGNS = {}


def wd(a):
    return (a + C / 2) % C - C / 2


def dist(a, b):
    return math.hypot(wd(b[0] - a[0]), b[1] - a[1])


def unit(a, b):
    v = (wd(b[0] - a[0]), b[1] - a[1])
    L = math.hypot(*v) or 1.0
    return (v[0] / L, v[1] / L)


def right_of(t):
    """The driver's right, travelling along t (s, x): facing +s the right is +x (StationGeo frames)."""
    return (-t[1], t[0])


def yaw_facing(f):
    """A sign's yaw so its face (local -z) looks along f (s, x) -- placement.py's convention."""
    return math.atan2(-f[1], f[0])


def add(p, v, k=1.0):
    return (p[0] + v[0] * k, p[1] + v[1] * k)


# ------------------------------------------------------------------ data
T = json.load(open(os.path.join(GD, "terrain.json")))
PL = json.load(open(os.path.join(GD, "placement.json")))["structures"]
ROADS = T["roads"]
RAIL = [tuple(p) for p in T["rail"]["pts"]]
LC = np.array(Image.open(os.path.join(GD, "landcover.png")))[:, :, 0]
LC_STEP = T.get("landcover_step_m", 4.0)

# structure density: counts in 10 m cells, summed over a 300 m square (the standard's 150 m circle,
# thresholds scaled by the square's larger area)
DC = 10.0
NS, NX = int(math.ceil(C / DC)), int(2 * HW / DC)
dens = np.zeros((NX, NS), np.int32)
for e in PL:
    if e["kind"] in ("crossing",):
        continue
    i = int((e["s"] % C) / DC) % NS
    j = min(NX - 1, max(0, int((e["x"] + HW) / DC)))
    dens[j, i] += 1
_k = 15
_pad = np.concatenate([dens[:, -_k:], dens, dens[:, :_k]], axis=1)
_cs = np.cumsum(np.cumsum(np.pad(_pad, ((1, 0), (1, 0))), axis=0), axis=1)


def density(s, x):
    i = int((s % C) / DC) % NS + _k
    j = int((x + HW) / DC)
    j0, j1 = max(0, j - _k), min(NX, j + _k + 1)
    i0, i1 = i - _k, i + _k + 1
    return int(_cs[j1, i1] - _cs[j0, i1] - _cs[j1, i0] + _cs[j0, i0])


def built_up(s, x):
    i = int((s % C) / LC_STEP) % LC.shape[1]
    j = min(LC.shape[0] - 1, max(0, int((x + HW) / LC_STEP)))
    return LC[j, i] == 1


def context(s, x):
    n = density(s, x)
    if n >= 32:
        return "c"
    if n >= 8 or built_up(s, x):
        return "t"
    return "r"


# settlements: centre and size (for town signs and signals)
TOWNS = {}
for e in PL:
    t = e.get("settlement")
    if not t or e["kind"] == "crossing":
        continue
    TOWNS.setdefault(t, []).append(e)
TOWN_C = {}
for t, es in TOWNS.items():
    cs = sum(math.cos(e["s"] / R) for e in es)
    sn = sum(math.sin(e["s"] / R) for e in es)
    TOWN_C[t] = ((math.atan2(sn, cs) % (2 * math.pi)) * R, sum(e["x"] for e in es) / len(es), len(es))


def nearest_town(p):
    return min(TOWN_C, key=lambda t: dist(p, TOWN_C[t][:2]))


# ------------------------------------------------------------------ spatial index of road points
G = 30.0
grid = {}
for ri, rd in enumerate(ROADS):
    for k, p in enumerate(rd["pts"]):
        grid.setdefault((int((p[0] % C) // G), int(p[1] // G)), []).append((ri, k))
NCOL = int(math.ceil(C / G))


def near_roads(p, reach):
    """[(distance, road, k, projected point)] per road: its nearest segment within reach."""
    best = {}
    ci, cj = int((p[0] % C) // G), int(p[1] // G)
    r = int(math.ceil(reach / G))
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            for ri, k in grid.get(((ci + di) % NCOL, cj + dj), ()):
                pts = ROADS[ri]["pts"]
                for k2 in (k - 1, k):
                    if k2 < 0 or k2 + 1 >= len(pts):
                        continue
                    a, b = pts[k2], pts[k2 + 1]
                    bx, by = wd(b[0] - a[0]), b[1] - a[1]
                    px, py = wd(p[0] - a[0]), p[1] - a[1]
                    L2 = bx * bx + by * by or 1e-9
                    t = max(0.0, min(1.0, (px * bx + py * by) / L2))
                    d = math.hypot(px - bx * t, py - by * t)
                    if d <= reach and (ri not in best or d < best[ri][0]):
                        best[ri] = (d, ri, k2 + (1 if t > 0.5 else 0), (p[0] + bx * t - px, a[1] + by * t))
    return sorted(best.values())


def heading(ri, k):
    pts = ROADS[ri]["pts"]
    return unit(pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)])


def parallel(ri, k, rj, kj):
    a, b = heading(ri, k), heading(rj, kj)
    return abs(a[0] * b[1] - a[1] * b[0]) < 0.3


# ------------------------------------------------------------------ overlaps
# where two roads run on top of each other (a highway through a town on its main street), the
# higher class (then the earlier road) owns the stretch: the other is hidden there (no ribbon,
# kerb, line or junction) -- DUP per road, one letter per point
DUP = []
for ri, rd in enumerate(ROADS):
    dp = []
    for k, p in enumerate(rd["pts"]):
        on = "0"
        for d, rj, kj, q in near_roads(p, 6.0):
            if rj == ri or d > max(2.5, min(rd["w"], ROADS[rj]["w"]) * 0.3):
                continue
            if (RANK[ROADS[rj]["cls"]], -rj) > (RANK[rd["cls"]], -ri) and parallel(ri, k, rj, kj):
                on = "1"
                break
        dp.append(on)
    DUP.append("".join(dp))

# ------------------------------------------------------------------ per point: context, junction flag
CTX, JN = [], []
for ri, rd in enumerate(ROADS):
    ctx, jn = [], []
    for k, p in enumerate(rd["pts"]):
        ctx.append(context(*p))
        on = "0"
        for d, rj, kj, q in near_roads(p, 14.0):
            if rj != ri and DUP[rj][kj] == "0" and d < ROADS[rj]["w"] * 0.5 + 1.5 and not (
                    DUP[ri][k] == "0" and parallel(ri, k, rj, kj) and d < 3.0):
                on = "1"
                break
        jn.append(on)
    # smooth the context: no runs shorter than 60 m (a lone house doesn't make a town)
    s_ = "".join(ctx)
    CTX.append(s_)
    JN.append("".join(jn))


def smooth_ctx(s_, min_run=10):
    out = list(s_)
    k = 0
    while k < len(out):
        j = k
        while j < len(out) and out[j] == out[k]:
            j += 1
        if j - k < min_run and k > 0:
            for q in range(k, j):
                out[q] = out[k - 1]
        k = j
    return "".join(out)


CTX = [smooth_ctx(c) for c in CTX]

# ------------------------------------------------------------------ junctions
# every place two roads meet: an end on another road, or two roads crossing
raw = []
for ri, rd in enumerate(ROADS):
    pts = rd["pts"]
    for k, p in enumerate(pts):
        if DUP[ri][k] == "1":
            continue
        for d, rj, kj, q in near_roads(p, 8.0):
            if rj <= ri or DUP[rj][kj] == "1":
                continue
            if d < 3.0 and not parallel(ri, k, rj, kj):
                raw.append((q, ri, k, rj, kj))
# cluster within 14 m
JUNCS = []
for q, ri, k, rj, kj in raw:
    for J in JUNCS:
        if dist(J["p"], q) < 14.0:
            J["roads"].setdefault(ri, k)
            J["roads"].setdefault(rj, kj)
            break
    else:
        JUNCS.append({"p": q, "roads": {ri: k, rj: kj}})


def arm_dirs(ri, k, p):
    """Directions (unit, away from the junction) of the road's arms at point k: one each way it goes on."""
    pts = ROADS[ri]["pts"]
    arms = []
    for step in (1, -1):
        j, run = k, 0.0
        while 0 <= j + step < len(pts) and run < 15.0:
            run += dist(pts[j], pts[j + step])
            j += step
        if run >= 10.0 and DUP[ri][j] == "0":
            arms.append((unit(p, pts[j]), j))
    return arms


for J in JUNCS:
    J["arms"] = []
    for ri, k in J["roads"].items():
        for u, j in arm_dirs(ri, k, J["p"]):
            J["arms"].append({"road": ri, "k": k, "u": u, "cls": ROADS[ri]["cls"]})
    J["ctx"] = context(*J["p"])

# ------------------------------------------------------------------ rail crossings
RG = {}
for k, p in enumerate(RAIL):
    RG.setdefault((int((p[0] % C) // G), int(p[1] // G)), []).append(k)


def rail_near(p, reach=6.0):
    ci, cj = int((p[0] % C) // G), int(p[1] // G)
    best = (1e9, None)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for k in RG.get(((ci + di) % NCOL, cj + dj), ()):
                if k + 1 >= len(RAIL):
                    continue
                a, b = RAIL[k], RAIL[k + 1]
                bx, by = wd(b[0] - a[0]), b[1] - a[1]
                px, py = wd(p[0] - a[0]), p[1] - a[1]
                L2 = bx * bx + by * by or 1e-9
                t = max(0.0, min(1.0, (px * bx + py * by) / L2))
                d = math.hypot(px - bx * t, py - by * t)
                if d < best[0]:
                    best = (d, k, (p[0] + bx * t - px, a[1] + by * t))
    return best if best[0] <= reach else None


# crossings: bridge spans over the rail are handled by the crossings (rail bridges carry the rail over
# water, not over roads), so every road meeting the rail meets it at grade
XINGS = []
for ri, rd in enumerate(ROADS):
    if rd["cls"] == "alley":
        continue
    pts = rd["pts"]
    k = 0
    while k < len(pts):
        hit = rail_near(pts[k], 3.5)
        if hit:
            p = hit[2]
            if not any(dist(p, x["p"]) < 25 for x in XINGS):
                u = unit(pts[max(0, k - 2)], pts[min(len(pts) - 1, k + 2)])
                ru = unit(RAIL[hit[1]], RAIL[min(len(RAIL) - 1, hit[1] + 1)])
                ctx = context(*p)
                cls = rd["cls"]
                if cls == "hwy" or ctx == "c" or cls == "main":
                    lvl = "G"
                elif cls == "county" or (cls == "street" and ctx == "t"):
                    lvl = "L"
                else:
                    lvl = "P"
                XINGS.append({"p": p, "road": ri, "k": k, "u": u, "ru": ru, "level": lvl, "cls": cls, "ctx": ctx,
                              "w": rd["w"]})
            k += 6
        k += 1

# ------------------------------------------------------------------ outputs
LINES, BARS, DECALS, SIGNS_OUT, SIGNALS = [], [], [], [], []


def sign(kind, p, face, ctx, text=None, h=None, plate=None):
    SIGNS_OUT.append({"t": kind, "s": round(p[0] % C, 2), "x": round(p[1], 2), "yaw": round(yaw_facing(face), 4),
                      "h": h if h is not None else (2.1 if ctx != "r" else 1.5), **({"txt": text} if text else {}),
                      **({"plate": plate} if plate else {})})


def side_half(p, travel, half_w):
    """The half width to the right-hand kerb for traffic along `travel` at p: a road with a parking
    lane on one side is wider on that side (tools/street_rules.py hl / hr)."""
    nr = near_roads(p, max(half_w, 3.0) + 2.0)
    if not nr:
        return half_w
    d, ri, k, _ = nr[0]
    rd = ROADS[ri]
    if "hr" not in rd:
        return half_w
    h = heading(ri, min(k, len(rd["pts"]) - 2))
    along = h[0] * travel[0] + h[1] * travel[1] >= 0.0
    return float(rd["hr"] if along else rd["hl"])


def verge_point(p, travel, half_w, ctx, back=0.0):
    """Where a sign for traffic travelling along `travel` stands: on its right-hand verge -- 0.6 m
    behind the kerb in town (in the tree lawn or on the kerb side of the sidewalk, MUTCD 2A.19), 2.2 m
    off a rural road's edge."""
    hw = side_half(p, travel, half_w)
    off = hw + (0.6 if ctx != "r" else 2.2)
    return add(add(p, right_of(travel), off), travel, -back)


def point_along(ri, k, u_sign, dist_m):
    """The centreline point dist_m from point k along the road (u_sign +1 forward / -1 back)."""
    pts = ROADS[ri]["pts"]
    j, run = k, 0.0
    while 0 <= j + u_sign < len(pts) and run < dist_m:
        run += dist(pts[j], pts[j + u_sign])
        j += u_sign
    return j, run


# junction control -------------------------------------------------------------------------------
N_STOP = N_YIELD = N_ALLWAY = N_SIG = 0
for J in JUNCS:
    arms = [a for a in J["arms"] if a["cls"] != "alley"]
    if len(arms) < 2:
        continue
    top = max(RANK[a["cls"]] for a in arms)
    ctx = J["ctx"]
    classes = {a["cls"] for a in arms}
    town = nearest_town(J["p"])
    big = TOWN_C[town][2] >= 100 and dist(J["p"], TOWN_C[town][:2]) < 700
    signal = ctx == "c" and big and len(arms) >= 3 and bool(classes & {"main", "street"}) and bool(classes & {"hwy", "county"})
    allway = not signal and len(arms) >= 3 and (
        (ctx == "c" and len({RANK[a["cls"]] for a in arms}) == 1 and top >= RANK["street"])
        or classes >= {"main", "county"})
    if signal:
        SIGNALS.append({"s": round(J["p"][0] % C, 2), "x": round(J["p"][1], 2),
                        "arms": [[round(a["u"][0], 4), round(a["u"][1], 4), ROADS[a["road"]]["w"]] for a in arms]})
        N_SIG += 1
    for a in arms:
        rd = ROADS[a["road"]]
        # the crossing road's half width: where this arm's traffic stops
        other = max((ROADS[b["road"]]["w"] for b in arms if b["road"] != a["road"]), default=8)
        control = None
        if signal:
            control = "signal"
        elif allway:
            control = "allway"
        elif RANK[a["cls"]] < top and not (a["cls"] == "gravel" and top == RANK["gravel"]):
            control = "stop"
        elif a["cls"] == "street" and top == RANK["street"] and ctx != "r":
            # street meets street: the approach with fewer buildings along it yields
            pa = add(J["p"], a["u"], 60)
            if density(*pa) < density(*J["p"]) * 0.5:
                control = "yield"
        if control is None:
            continue
        travel = (-a["u"][0], -a["u"][1])            # approaching the junction
        back = other * 0.5 + 2.0
        stop_c = add(J["p"], a["u"], back)
        if control in ("stop", "allway", "yield"):
            sp = verge_point(J["p"], travel, rd["w"] * 0.5, ctx, back=back + 0.5)
            sign("yield" if control == "yield" else "stop", sp, a["u"], ctx,
                 plate="allway" if control == "allway" else None)
            if control == "yield":
                N_YIELD += 1
            elif control == "allway":
                N_ALLWAY += 1
            else:
                N_STOP += 1
        if control != "yield" and a["cls"] in PAVED:
            # stop line across the approach lane (the right half of the road for its traffic)
            r_ = right_of(travel)
            w = 0.4
            q0 = add(stop_c, r_, 0.1)
            q1 = add(stop_c, r_, rd["w"] * 0.5 - (0.3 if ctx == "r" else 0.2))
            BARS.append({"c": "w", "q": [list(add(q0, a["u"], -w / 2)), list(add(q1, a["u"], -w / 2)),
                                          list(add(q1, a["u"], w / 2)), list(add(q0, a["u"], w / 2))]})
        # stop ahead on fast approaches
        lim = LIMIT[a["cls"]][1 if ctx == "r" else 0]
        if control == "stop" and lim >= 70:
            sp = verge_point(add(J["p"], a["u"], 90), travel, rd["w"] * 0.5, "r")
            sign("stop_ahead", sp, a["u"], "r")
        elif control == "stop" and ctx == "r" and a["cls"] != "gravel":
            sp = verge_point(add(J["p"], a["u"], 80), travel, rd["w"] * 0.5, "r")
            sign("junction", sp, a["u"], "r")
        # crosswalks at town / core junctions of the bigger roads
        if ctx != "r" and top >= RANK["county"] and a["cls"] in PAVED:
            cw = add(J["p"], a["u"], other * 0.5 + 2.2 + 1.5)       # the crosswalk's middle, 1.5 m out
            n_ = right_of(a["u"])
            half = rd["w"] * 0.5
            if ctx == "c":
                # zebra: bars along the traffic, 0.5 m wide every 1 m across the road, 3 m long
                y = -half + 0.5
                while y < half - 0.4:
                    c0 = add(cw, n_, y)
                    BARS.append({"c": "w", "q": [list(add(add(c0, a["u"], -1.5), n_, -0.25)), list(add(add(c0, a["u"], -1.5), n_, 0.25)),
                                                  list(add(add(c0, a["u"], 1.5), n_, 0.25)), list(add(add(c0, a["u"], 1.5), n_, -0.25))]})
                    y += 1.0
            else:
                for side in (-1.5, 1.5):
                    c0 = add(cw, a["u"], side)
                    BARS.append({"c": "w", "q": [list(add(add(c0, a["u"], -0.15), n_, -half)), list(add(add(c0, a["u"], -0.15), n_, half)),
                                                  list(add(add(c0, a["u"], 0.15), n_, half)), list(add(add(c0, a["u"], 0.15), n_, -half))]})
    # street name blades at town / core junctions of named roads
    if ctx != "r":
        names = sorted({ROADS[a["road"]].get("name") for a in arms if ROADS[a["road"]].get("name")})
        if names:
            a = arms[0]
            sp = verge_point(J["p"], (-a["u"][0], -a["u"][1]), ROADS[a["road"]]["w"] * 0.5, ctx,
                             back=max(ROADS[b["road"]]["w"] for b in arms) * 0.5 + 3.0)
            sign("blade", sp, a["u"], ctx, text=" / ".join(n.upper() for n in names), h=2.6)

# centre and edge lines, speed limits, curve warnings, town entries ---------------------------------
NO_PASS = 60.0


def bend_at(pts, k, span=13):
    """Heading change (deg) over +-span points (~80 m at 6 m)."""
    if k - span < 0 or k + span >= len(pts):
        return 0.0
    a = unit(pts[k - span], pts[k])
    b = unit(pts[k], pts[k + span])
    return math.degrees(math.acos(max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))))


# points near a junction / crossing / bridge (no passing)
jpts = [J["p"] for J in JUNCS if len(J["arms"]) >= 3] + [x["p"] for x in XINGS]
for e in PL:
    if e["kind"] == "crossing":
        jpts.append((e["s"], e["x"]))
JG = {}
for p in jpts:
    JG.setdefault((int((p[0] % C) // 60), int(p[1] // 60)), []).append(p)


def near_conflict(p):
    ci, cj = int((p[0] % C) // 60), int(p[1] // 60)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for q in JG.get(((ci + di) % int(math.ceil(C / 60)), cj + dj), ()):
                if dist(p, q) < NO_PASS:
                    return True
    return False


def runs(flags):
    """[(value, k0, k1)] runs of equal values."""
    out = []
    k = 0
    while k < len(flags):
        j = k
        while j + 1 < len(flags) and flags[j + 1] == flags[k]:
            j += 1
        out.append((flags[k], k, j))
        k = j + 1
    return out


PARK_W = 2.4
NO_PARK_JN = 9.2        # m: no parking within 30 ft of the stop sign / signal at a junction (ORC 4511.68)
# tram stop zones (research/law 02_cities.md): no parking on either kerb within the zone of a stop
_TP = os.path.join(GD, "transit.json")
TRAM_STOPS = [(sp["s"], sp["x"]) for l in (json.load(open(_TP))["lines"] if os.path.exists(_TP) else []) for sp in l["stops"]]
_LAWJ = json.load(open(os.path.join(GD, "law", "ordinances.json")))
STOP_ZONE = float(_LAWJ.get("tram_stop_zone", {}).get("half_length_m", 45.72))


def in_stop_zone(p, margin=0.0):
    return any(dist(p, q) < STOP_ZONE + margin for q in TRAM_STOPS)


N_STOPZ = {"zones_signed": 0}
for ri, rd in enumerate(ROADS):
    park = rd.get("park", [0, 0])
    if not any(park) or rd["cls"] in ("alley", "gravel"):
        continue
    pts = rd["pts"]
    near_j = []
    for k, p in enumerate(pts):
        nj = JN[ri][k] == "1" or DUP[ri][k] == "1"
        if not nj:
            for jdist in (NO_PARK_JN,):
                a_, _ = point_along(ri, k, 1, jdist)
                b_, _ = point_along(ri, k, -1, jdist)
                if JN[ri][a_] == "1" or JN[ri][b_] == "1":
                    nj = True
        near_j.append("-" if nj else ("Z" if in_stop_zone(p) else "P"))
    # the zone's ends: R7-107 (NO PARKING, tram symbol) on each parked kerb, facing the traffic
    # on that kerb, where a parking run meets the zone
    for k in range(1, len(pts)):
        a_, b_ = near_j[k - 1], near_j[k]
        if (a_ == "Z") == (b_ == "Z") or "-" in (a_, b_):
            continue
        kz = k if b_ == "Z" else k - 1
        h = heading(ri, min(kz, len(pts) - 2))
        for side, travel in ((1, h), (0, (-h[0], -h[1]))):     # the right kerb for traffic along the points, the left against
            if not park[side]:
                continue
            sign("no_parking_tram", verge_point(pts[kz], travel, rd["w"] * 0.5, CTX[ri][kz]), (-travel[0], -travel[1]), CTX[ri][kz])
            N_STOPZ["zones_signed"] += 1
    for v, k0, k1 in runs(near_j):
        if v != "P" or k1 - k0 < 1:
            continue
        if park[1]:
            LINES.append({"r": ri, "a": k0, "b": k1, "off": round(rd["hr"] - PARK_W, 2), "c": "w", "w": 0.1})
        if park[0]:
            LINES.append({"r": ri, "a": k0, "b": k1, "off": round(-(rd["hl"] - PARK_W), 2), "c": "w", "w": 0.1})
for ri, rd in enumerate(ROADS):
    cls, pts, ctx = rd["cls"], rd["pts"], CTX[ri]
    if cls not in ("hwy", "county", "main"):
        continue
    hw = rd["w"] * 0.5
    # the centre: per point D (double solid) or B (broken)
    cen = []
    for k, p in enumerate(pts):
        if JN[ri][k] == "1" or DUP[ri][k] == "1":
            cen.append("-")
        elif cls == "main" or ctx[k] != "r" or near_conflict(p) or bend_at(pts, k, 8) > 15.0:
            cen.append("D")
        else:
            cen.append("B")
    for v, k0, k1 in runs(cen):
        if v == "-" or k1 - k0 < 1:
            continue
        if v == "D":
            for off in (-0.1, 0.1):
                LINES.append({"r": ri, "a": k0, "b": k1, "off": off, "c": "y", "w": 0.1})
        else:
            LINES.append({"r": ri, "a": k0, "b": k1, "off": 0.0, "c": "y", "w": 0.1, "dash": [3.0, 6.0]})
    # edges: rural hwy / county solid white; main streets the parking lines
    edge = []
    for k in range(len(pts)):
        edge.append("-" if (JN[ri][k] == "1" or DUP[ri][k] == "1") else ("E" if (ctx[k] == "r" and cls != "main") else "-"))
    for v, k0, k1 in runs(edge):
        if v == "-" or k1 - k0 < 1:
            continue
        if v == "E":
            off = (3.65 if cls == "hwy" else hw - 0.3)
            wdt = 0.15 if cls == "hwy" else 0.1
        else:
            off, wdt = hw - 2.2, 0.1
        for sg in (-1, 1):
            LINES.append({"r": ri, "a": k0, "b": k1, "off": sg * off, "c": "w", "w": wdt})
    # cat's eyes on rural highways (stud positions along the centre)
# speed limits, town entries, route markers, curve warnings (both directions)
N_SPEED = N_TOWN = N_CURVE = 0
for ri, rd in enumerate(ROADS):
    cls, pts, ctx = rd["cls"], rd["pts"], CTX[ri]
    if cls not in PAVED and cls != "gravel":
        continue
    hw = rd["w"] * 0.5
    L = len(pts)
    for direction in (1, -1):
        rng = range(L) if direction == 1 else range(L - 1, -1, -1)
        run_m = 0.0
        last_ctx = None
        last_sign_m = -1e9
        last_curve_m = -1e9
        prev = None
        for k in rng:
            p = pts[k]
            if prev is not None:
                run_m += dist(prev, p)
            prev = p
            c = "r" if ctx[k] == "r" else "t"
            j = min(L - 1, max(0, k + direction))
            travel = unit(p, pts[j]) if j != k else None
            if travel is None:
                continue
            if JN[ri][k] == "1" or DUP[ri][k] == "1":
                continue
            if cls in ("hwy", "county"):
                # entering / leaving a town: speed limit (and the town's name on entry)
                if last_ctx is not None and c != last_ctx and run_m - last_sign_m > 150:
                    lim = LIMIT[cls][0 if c == "t" else 1]
                    sp = verge_point(p, travel, hw, c)
                    sign(f"speed_{lim}", sp, (-travel[0], -travel[1]), c)
                    N_SPEED += 1
                    last_sign_m = run_m
                    if c == "t":
                        town = nearest_town(p)
                        pop = int(round(TOWN_C[town][2] * 2.6, -1))
                        sp2 = verge_point(p, travel, hw, "r", back=-25.0)
                        sign("town", sp2, (-travel[0], -travel[1]), "r", text=f"{town.upper()}\nPOP {pop:,}", h=1.4)
                        N_TOWN += 1
                    else:
                        nm = rd.get("name")
                        if nm in ("SR 14", "US 30", "Coast Hwy"):
                            sp2 = verge_point(p, travel, hw, "r", back=-40.0)
                            sign({"SR 14": "route_sr14", "US 30": "route_us30", "Coast Hwy": "route_coast"}[nm], sp2,
                                 (-travel[0], -travel[1]), "r")
                elif c == "r" and run_m - last_sign_m > 1500:
                    lim = LIMIT[cls][1]
                    sign(f"speed_{lim}", verge_point(p, travel, hw, c), (-travel[0], -travel[1]), c)
                    N_SPEED += 1
                    last_sign_m = run_m
            last_ctx = c
            # curve warnings: a bend of 35 deg or more in the next ~80 m, on rural roads
            if c == "r" and cls != "alley" and run_m - last_curve_m > 250:
                ahead = k + direction * 16
                if 0 <= ahead - 13 and ahead + 13 < L:
                    b = bend_at(pts, ahead, 7)
                    if b >= 35.0:
                        # which way: the cross product of the headings
                        a1 = unit(pts[ahead - 7 * direction], pts[ahead])
                        a2 = unit(pts[ahead], pts[ahead + 7 * direction])
                        cr = a1[0] * a2[1] - a1[1] * a2[0]
                        # facing +s, right is +x: a turn toward the right has cross > 0
                        sign("curve_r" if cr > 0 else "curve_l", verge_point(p, travel, hw, c), (-travel[0], -travel[1]), c)
                        N_CURVE += 1
                        last_curve_m = run_m

# rail crossings: signs and markings per approach --------------------------------------------------
for X in XINGS:
    rd = ROADS[X["road"]]
    hw = rd["w"] * 0.5
    for sg in (1, -1):
        u = (X["u"][0] * sg, X["u"][1] * sg)                 # the arm, away from the crossing
        travel = (-u[0], -u[1])
        # stop line 4.5 m from the nearest rail (the track's gauge is 1.5 m; the ballast 4 m)
        # across the rail's skew: measured along the road
        cosk = abs(u[0] * X["ru"][1] - u[1] * X["ru"][0]) or 1.0
        back = (2.0 + 4.5) / max(0.3, cosk)
        if rd["cls"] in PAVED:
            stop_c = add(X["p"], u, back)
            r_ = right_of(travel)
            q0 = add(stop_c, r_, 0.1)
            q1 = add(stop_c, r_, hw - 0.3)
            BARS.append({"c": "w", "q": [list(add(q0, u, -0.2)), list(add(q1, u, -0.2)), list(add(q1, u, 0.2)), list(add(q0, u, 0.2))]})
            if X["ctx"] != "c":
                c_ = add(add(X["p"], u, 30.0), r_, hw * 0.5)
                DECALS.append({"t": "rxr", "s": round(c_[0] % C, 2), "x": round(c_[1], 2), "yaw": round(yaw_facing(u), 4),
                               "w": min(3.2, hw - 0.4), "l": 6.0})
        if X["level"] == "P":
            sp = verge_point(X["p"], travel, hw, X["ctx"], back=back + 1.0)
            sign("crossbuck", sp, u, X["ctx"], h=2.2, plate="stop")
        adv = 150.0 if X["ctx"] == "r" else 60.0
        sign("rr_ahead", verge_point(add(X["p"], u, adv), travel, hw, X["ctx"]), u, X["ctx"])
    X["back"] = round((2.0 + 4.5), 2)

# dead ends: a DEAD END warning where the road leading to a turning circle begins its last stretch
for t in T.get("turns", []):
    c = (t["s"], t["x"])
    for ri, rd in enumerate(ROADS):
        pts = rd["pts"]
        for end, step in ((0, 1), (len(pts) - 1, -1)):
            if dist(pts[end], c) < 2.0:
                j, run = point_along(ri, end, step, 70.0)
                if run < 40.0:
                    continue
                p = pts[j]
                travel = unit(p, pts[end])
                ctx = CTX[ri][j]
                sign("dead_end", verge_point(p, travel, rd["w"] * 0.5, ctx), (-travel[0], -travel[1]), ctx)

# parking, routes and subdivision entrances (research/law: each city's ordinances) ------------------
LAWP = os.path.join(GD, "law", "ordinances.json")
LAW = {c["id"]: c for c in json.load(open(LAWP))["cities"]} if os.path.exists(LAWP) else {}
N_PARK = {"timed": 0, "pay": 0, "no_parking": 0, "route": 0, "no_outlet": 0, "subdiv_speed": 0}
SIGN_EVERY = 60.0
for ri, rd in enumerate(ROADS):
    city = LAW.get(rd.get("city") or "")
    if not city or rd["cls"] in ("alley", "gravel") or rd.get("xs") in (None, "rural"):
        continue
    pts, ctx = rd["pts"], CTX[ri]
    park = rd.get("park", [0, 0])
    core = rd.get("xs", "").endswith("core")
    limit_h = int(city["parking"]["downtown"]["limit_h"])
    for direction, side in ((1, 1), (-1, 0)):         # traffic along the points parks on the right (hr); against them, hl
        rng = range(len(pts)) if direction == 1 else range(len(pts) - 1, -1, -1)
        run_m, last = 0.0, -1e9
        prev = None
        for k in rng:
            p = pts[k]
            if prev is not None:
                run_m += dist(prev, p)
            prev = p
            if JN[ri][k] == "1" or DUP[ri][k] == "1" or run_m - last < SIGN_EVERY:
                continue
            j = min(len(pts) - 1, max(0, k + direction))
            if j == k:
                continue
            travel = unit(p, pts[j])
            face = (-travel[0], -travel[1])
            if park[side] and in_stop_zone(p):
                continue                                  # the tram stop zone has its own R7-107s
            if park[side]:
                if core:
                    sign("parking_%dh" % min(3, max(2, limit_h)), verge_point(p, travel, rd["w"] * 0.5, ctx[k]), face, ctx[k])
                    N_PARK["timed"] += 1
                    if city["parking"]["downtown"]["meters"]:
                        sign("pay_station", verge_point(p, travel, rd["w"] * 0.5, ctx[k], back=-4.0), face, ctx[k], h=1.3)
                        N_PARK["pay"] += 1
                else:
                    continue                              # residential: parking unsigned (unrestricted)
            elif rd["cls"] in ("street", "main"):
                sign("no_parking", verge_point(p, travel, rd["w"] * 0.5, ctx[k]), face, ctx[k])
                N_PARK["no_parking"] += 1
            last = run_m
    # emergency / flood routes: the city's through roads, at their first town stretch each way
    sp_ = " ".join(city["parking"]["special"]).lower()
    route = "flood_route" if "flood route" in sp_ else ("emergency_route" if "emergency route" in sp_ else None)
    if route and rd["cls"] in ("hwy", "county", "main") and rd.get("ctx") in ("t", "c"):
        for k in (min(4, len(pts) - 2), max(1, len(pts) - 5)):
            travel = unit(pts[k], pts[k + 1]) if k == min(4, len(pts) - 2) else unit(pts[k], pts[k - 1])
            sign(route, verge_point(pts[k], travel, rd["w"] * 0.5, ctx[k], back=-8.0), (-travel[0], -travel[1]), ctx[k])
            N_PARK["route"] += 1
# a subdivision's mouth: NO OUTLET (W14-2) and its speed limit, facing traffic turning in
for ri, rd in enumerate(ROADS):
    if rd.get("xs") != "street/subdivision":
        continue
    pts = rd["pts"]
    for end, step in ((0, 1), (len(pts) - 1, -1)):
        if JN[ri][end] != "1":
            continue
        other = [r for d_, r, _, _ in near_roads(pts[end], 12.0) if r != ri and ROADS[r].get("xs") != "street/subdivision"]
        if not other:
            continue
        j, run = point_along(ri, end, step, 18.0)
        travel = unit(pts[end], pts[j])
        sign("no_outlet", verge_point(pts[j], travel, rd["w"] * 0.5, "t"), (-travel[0], -travel[1]), "t")
        j2, _ = point_along(ri, end, step, 40.0)
        sign("speed_40", verge_point(pts[j2], travel, rd["w"] * 0.5, "t"), (-travel[0], -travel[1]), "t")
        N_PARK["no_outlet"] += 1
        N_PARK["subdiv_speed"] += 1
# parking lots (tools/parking_lots.py): stall lines, the P at the entrance, PARK & RIDE on the
# street before a park-and-ride, the accessible stalls' signs
N_LOT = {"lots": 0, "stall_lines": 0, "park_ride": 0}
for A in T["areas"]:
    lt = A.get("lot")
    if not lt:
        continue
    N_LOT["lots"] += 1
    c, u = lt["centre"], lt["dir"]
    n = (-u[1], u[0])
    at = lambda a_, b_: (c[0] + u[0] * a_ + n[0] * b_, c[1] + u[1] * a_ + n[1] * b_)
    acc_left = int(lt["accessible"])
    for ri_, row in enumerate(lt["rows"]):
        u0, u1, v0, depth, facing = row
        k = 0
        a_ = u0
        while a_ <= u1 + 1e-6:
            q = [at(a_ - 0.05, v0), at(a_ + 0.05, v0), at(a_ + 0.05, v0 + depth), at(a_ - 0.05, v0 + depth)]
            BARS.append({"c": "w", "q": [[round(x[0] % C, 2), round(x[1], 2)] for x in q]})
            N_LOT["stall_lines"] += 1
            if ri_ == 0 and acc_left > 0 and a_ + 2.75 <= u1 + 1e-6:
                mid = at(a_ + 1.375, v0 + 0.3)
                sign("accessible", mid, (n[0] * -1, n[1] * -1), "t", h=1.5)
                acc_left -= 1
            a_ += 2.75
            k += 1
    ac = lt["access"]
    sign("parking_guide", (ac[0], ac[1]), (-n[0], -n[1]), "t", h=2.1)
    if lt["type"] == "park_and_ride":
        nr = near_roads((ac[0], ac[1]), 40.0)
        if nr:
            d_, ri_, k_, _ = nr[0]
            for step_ in (1, -1):
                j_, run_ = point_along(ri_, k_, step_, 100.0)
                if run_ < 40.0:
                    continue
                travel = unit(ROADS[ri_]["pts"][j_], ROADS[ri_]["pts"][k_])
                sign("park_ride", verge_point(ROADS[ri_]["pts"][j_], travel, ROADS[ri_]["w"] * 0.5, "t"), (-travel[0], -travel[1]), "t", h=2.1)
                N_LOT["park_ride"] += 1
print("parking and subdivision signs:", N_PARK)
print("parking lots:", N_LOT)
print("tram stop zones:", N_STOPZ)

out = {
    "ctx": CTX,
    "jn": JN,
    "dup": DUP,
    "lines": LINES,
    "bars": BARS,
    "decals": DECALS,
    "signs": SIGNS_OUT,
    "xings": [{"s": round(X["p"][0] % C, 2), "x": round(X["p"][1], 2), "u": [round(v, 4) for v in X["u"]],
               "ru": [round(v, 4) for v in X["ru"]], "level": X["level"], "w": X["w"], "cls": X["cls"], "ctx": X["ctx"]}
              for X in XINGS],
    "signals": SIGNALS,
}
with open(os.path.join(GD, "road_furniture.json"), "w") as f:
    json.dump(out, f, separators=(",", ":"))
lv = {}
for X in XINGS:
    lv[X["level"]] = lv.get(X["level"], 0) + 1
kinds = {}
for s_ in SIGNS_OUT:
    kinds[s_["t"]] = kinds.get(s_["t"], 0) + 1
print(f"junctions {len(JUNCS)}: stop {N_STOP}, yield {N_YIELD}, all-way {N_ALLWAY}, signals {N_SIG}")
print(f"rail crossings {len(XINGS)}: {lv}")
print(f"lines {len(LINES)}, bars {len(BARS)}, decals {len(DECALS)}, signs {len(SIGNS_OUT)}: {kinds}")

if "--stats" in sys.argv:
    import collections
    cc = collections.Counter()
    par = 0
    for J in JUNCS:
        arms = [a for a in J["arms"] if a["cls"] != "alley"]
        cc[(J["ctx"], tuple(sorted(a["cls"] for a in arms)))] += 1
        us = [a["u"] for a in arms]
        if any(abs(u1[0] * u2[1] - u1[1] * u2[0]) < 0.2 and (u1[0] * u2[0] + u1[1] * u2[1]) > 0.8 for i, u1 in enumerate(us) for u2 in us[i + 1:]):
            par += 1
    for k, v in cc.most_common(40):
        print(v, k)
    print("junctions with two arms along each other:", par)
