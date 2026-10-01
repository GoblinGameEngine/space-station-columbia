#!/usr/bin/env python3
"""Street rules: every road gets its legal cross-section from the ordinances of the city whose law
its settlement follows (tools/law -> godot_project/remake/law/ordinances.json): the carriageway
(travel lanes plus any parking lanes), which sides may be parked on, the tree lawn and the sidewalk
(the user, 2026-10-01: wider streets for on-street parking where permitted; sidewalks; "place them in
our cities as required and recommended").

    python3 tools/street_rules.py [--stats]

Run after map_expanded.py --game-data and before remake/tools/placement.py (which then moves the
buildings clear of the new widths: kerb, lawn and walk). Idempotent: widths come from each road's
class, never from its last width.

Each road in terrain.json gets:
  w        the carriageway, kerb to kerb (m)
  hl, hr   its half widths left / right of the road's line (the line runs down the middle of the
           travel lanes; a parking lane widens the side it's on)
  park     [left, right]: parking lanes (0/1)
  lawn     tree lawn width (m), each side;  walk  sidewalk width (m), each side (0: none)
  xs       the cross-section used ("street/town", ...);  city  the governing city id;  ctx  c/t/r
Facing along the road's points, right is (-dx, ds) in (s, x) (SSC road standard: we drive on the right).
"""
import json
import math
import os
import sys
from collections import Counter

ROOT = os.path.join(os.path.dirname(__file__), "..")
GD = os.path.join(ROOT, "godot_project", "remake")
SAMPLE = 20.0           # m between a road's context samples
CORE_N, TOWN_N, R_CTX = 25, 6, 150.0     # SSC road standard §1: structures within 150 m
SET_R = 260.0           # m: a road belongs to the settlement of the structures within this
G = 50.0


def main():
    stats = "--stats" in sys.argv
    ter_p = os.path.join(GD, "terrain.json")
    ter = json.load(open(ter_p))
    C = 2 * math.pi * ter["R"]
    wrap = lambda d: (d + C / 2) % C - C / 2
    law = json.load(open(os.path.join(GD, "law", "ordinances.json")))
    sets = json.load(open(os.path.join(GD, "law", "settlements.json")))["settlements"]
    gov = {r["name"]: r["governed_by"] for r in sets}
    xs_by_city = {c["id"]: c["cross_sections"] for c in law["cities"]}
    park_w = float(law["park_lane_m"])
    places = json.load(open(os.path.join(GD, "placement.json")))["structures"]
    grid = {}
    for e in places:
        if e["kind"] == "crossing":
            continue
        grid.setdefault((int((e["s"] % C) // G), int(e["x"] // G)), []).append(e)

    def near(s, x, r):
        out = []
        k = int(math.ceil(r / G))
        ci, cj = int((s % C) // G), int(x // G)
        for i in range(-k, k + 1):
            for j in range(-k, k + 1):
                for e in grid.get(((ci + i) % int(C // G + 1), cj + j), []):
                    if math.hypot(wrap(e["s"] - s), e["x"] - x) <= r:
                        out.append(e)
        return out
    culs = [(sum(p[0] for p in a["poly"]) / len(a["poly"]), sum(p[1] for p in a["poly"]) / len(a["poly"])) for a in ter["areas"] if a["kind"] == "culdesac"]
    tally = Counter()
    for rd in ter["roads"]:
        cls = rd["cls"]
        pts = rd["pts"]
        # context and settlement along the road
        ctxs, towns = [], []
        right_n, left_n = 0, 0
        for a, b in zip(pts, pts[1:]):
            ds, dx = wrap(b[0] - a[0]), b[1] - a[1]
            L = math.hypot(ds, dx)
            if L < 1e-6:
                continue
            for t in range(0, int(L // SAMPLE) + 1):
                u = min(t * SAMPLE, L)
                s, x = a[0] + ds / L * u, a[1] + dx / L * u
                n = len(near(s, x, R_CTX))
                ctxs.append("c" if n >= CORE_N else ("t" if n >= TOWN_N else "r"))
                es = near(s, x, SET_R)
                tw = Counter(e["settlement"] for e in es if e.get("settlement"))
                towns.append(tw.most_common(1)[0][0] if tw else None)
                for e in near(s, x, 35.0):
                    side = wrap(e["s"] - s) * (-dx / L) + (e["x"] - x) * (ds / L)
                    if side > 0:
                        right_n += 1
                    else:
                        left_n += 1
        cc = Counter(ctxs)
        ctx = "c" if cc["c"] >= max(1, len(ctxs) * 0.3) else ("t" if cc["t"] + cc["c"] >= max(1, len(ctxs) * 0.4) else "r")
        town = Counter(t for t in towns if t).most_common(1)
        town = town[0][0] if town else None
        city = gov.get(town) if town else None
        closed = math.hypot(wrap(pts[0][0] - pts[-1][0]), pts[0][1] - pts[-1][1]) < 5.0
        subdiv = cls == "street" and (closed or any(min(math.hypot(wrap(p[0] - cs), p[1] - cx) for p in (pts[0], pts[-1])) < 30.0 for cs, cx in culs))
        if cls == "alley":
            key = "alley"
        elif city is None or ctx == "r" or cls == "gravel":
            key = "rural"
        elif cls == "main":
            key = "main/core" if ctx == "c" else "main/town"
        elif cls == "street":
            key = "street/subdivision" if subdiv else ("street/core" if ctx == "c" else "street/town")
        elif cls in ("county", "hwy"):
            key = "%s/%s" % (cls, "core" if ctx == "c" else "town")
        else:
            key = "rural"
        xs = (xs_by_city.get(city) or {}).get(key) if city else None
        base_w = {"hwy": 12, "county": 8, "gravel": 6, "main": 11, "street": 7, "alley": 3}[cls]
        if key == "rural" or not xs or not xs.get("w"):
            w, park, lawn, walk = base_w, [0, 0], 0.0, 0.0
        else:
            w, n_park, lawn, walk = float(xs["w"]), int(xs["park"]), float(xs["lawn"]), float(xs["walk"])
            if n_park == 2:
                park = [1, 1]
            elif n_park == 1:
                park = [0, 1] if right_n >= left_n else [1, 0]       # the side with more doors
            else:
                park = [0, 0]
        travel = (w - (park[0] + park[1]) * park_w) / 2.0
        rd["w"] = round(w, 2)
        rd["hl"] = round(travel + park[0] * park_w, 2)
        rd["hr"] = round(travel + park[1] * park_w, 2)
        rd["park"] = park
        rd["lawn"] = round(lawn, 2)
        rd["walk"] = round(walk, 2)
        rd["xs"] = key
        rd["city"] = city
        rd["ctx"] = ctx
        tally[key] += 1
        tally["parked sides"] += park[0] + park[1]
    # cul-de-sac turnarounds to the subdivision rule (40 ft pavement radius): the turning circle and
    # its area
    r_min = float(law["subdivision"]["cul_de_sac"]["turnaround_pavement_radius_m"])
    for t in ter.get("turns", []):
        if any(math.hypot(wrap(t["s"] - cs), t["x"] - cx) < 30.0 for cs, cx in culs) and t.get("r", 0) < r_min:
            t["r"] = round(r_min, 2)
            tally["turnarounds widened"] += 1
    for a in ter["areas"]:
        if a["kind"] != "culdesac":
            continue
        cs = sum(q[0] for q in a["poly"]) / len(a["poly"])
        cx = sum(q[1] for q in a["poly"]) / len(a["poly"])
        r0 = max(math.hypot(wrap(q[0] - cs), q[1] - cx) for q in a["poly"])
        if r0 < r_min:
            k = r_min / r0
            a["poly"] = [[round(cs + wrap(q[0] - cs) * k, 2), round(cx + (q[1] - cx) * k, 2)] for q in a["poly"]]
    json.dump(ter, open(ter_p, "w"), indent=0)
    print("street rules: " + ", ".join("%s %d" % kv for kv in sorted(tally.items())))


if __name__ == "__main__":
    main()
