#!/usr/bin/env python3
"""Parking lots (the user, 2026-10-01: "Create parking lots in city centers and Park-And-Ride lots
outside of city centers with regular tram stops").

    python3 tools/parking_lots.py

Run after remake/tools/placement.py, tools/street_rules.py and remake/tools/bake_transit.gd (it reads
remake/transit.json for the park-and-ride stops), and before tools/road_furniture.py (which paints
the stalls and puts up the P, PARK & RIDE and accessible-parking signs).

  downtown       one public lot near the middle of each large city: behind the street wall, never
                 at a corner (research/law DESIGN_RULES), set back behind a downtown street's sidewalk
  park & ride    a lot at each park-and-ride tram stop (TransitNet._park_and_ride), on the kerbside,
                 its entrance within DESIGN_RULES park_and_ride walk_to_stop_max_m of the stop

Lots are terrain.json areas of kind "parking" with a "lot" record: {type, town, city, spaces,
accessible, rows: [[u0, u1, v_front, depth, facing]] (the stall rows in the lot's own frame), access
(s, x), dir (along), stop}. Idempotent: lots it made before are removed first.
Stalls 9 x 18 ft (2.75 x 5.5 m), 90-degree, two-way aisles 24 ft (7.3 m); 1 accessible stall per 25
(ADA / IBC 1106), at the row end nearest the entrance (research/law/06_zoning_and_building.md).
"""
import gzip
import json
import math
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
GD = os.path.join(ROOT, "godot_project", "remake")
STALL_W, STALL_D, AISLE = 2.75, 5.5, 7.3
DEPTH = 2 * (2 * STALL_D + AISLE)          # two bays: stall + aisle + stall, twice (36.6 m)
DOWNTOWN_W, PNR_W = 44.0, 66.0              # along the street
GAP = 2.0                                   # behind the back of the sidewalk


def main():
    ter_p = os.path.join(GD, "terrain.json")
    ter = json.load(open(ter_p))
    C = 2 * math.pi * ter["R"]
    wrap = lambda d: (d + C / 2) % C - C / 2
    rs = ter["raster"]
    nx, ny, step, x0 = rs["nx"], rs["ny"], rs["step_m"], rs["x0"]
    import numpy as np
    lvl = np.frombuffer(gzip.open(os.path.join(GD, rs["level"])).read(), np.float16).reshape(ny, nx)
    places = json.load(open(os.path.join(GD, "placement.json")))["structures"]
    sets = {r["name"]: r for r in json.load(open(os.path.join(GD, "law", "settlements.json")))["settlements"]}
    cities = {c["id"]: c for c in json.load(open(os.path.join(GD, "law", "ordinances.json")))["cities"]}
    transit = json.load(open(os.path.join(GD, "transit.json")))["lines"] if os.path.exists(os.path.join(GD, "transit.json")) else []
    ter["areas"] = [a for a in ter["areas"] if "lot" not in a]          # (idempotent)

    def footprints():
        out = []
        for e in places:
            if e["kind"] == "crossing":
                continue
            c, s_ = math.cos(e["yaw"]), math.sin(e["yaw"])
            pts = [(e["s"] + lx * s_ - lz * c, e["x"] + lx * c + lz * s_) for lx in (e["fmin"][0], e["fmax"][0]) for lz in (e["fmin"][1], e["fmax"][1])]
            out.append((e["s"], e["x"], max(math.hypot(wrap(p[0] - e["s"]), p[1] - e["x"]) for p in pts)))
        return out
    FP = footprints()

    def segs():
        out = []
        for ri, rd in enumerate(ter["roads"]):
            verge = rd.get("lawn", 0.0) + rd.get("walk", 0.0)
            for a, b in zip(rd["pts"], rd["pts"][1:]):
                out.append((a, b, max(rd.get("hl", rd["w"] / 2), rd.get("hr", rd["w"] / 2)) + verge, ri))
        return out
    SEGS = segs()

    def seg_dist(p, a, b):
        ds, dx = wrap(b[0] - a[0]), b[1] - a[1]
        L2 = ds * ds + dx * dx or 1e-9
        t = max(0.0, min(1.0, (wrap(p[0] - a[0]) * ds + (p[1] - a[1]) * dx) / L2))
        return math.hypot(wrap(p[0] - a[0]) - ds * t, p[1] - a[1] - dx * t)

    def rect(c, u, W, D):
        n = (-u[1], u[0])
        return [(c[0] + u[0] * a + n[0] * b, c[1] + u[1] * a + n[1] * b) for a, b in ((-W / 2, -D / 2), (W / 2, -D / 2), (W / 2, D / 2), (-W / 2, D / 2))]

    def free(c, u, W, D, front_road):
        n = (-u[1], u[0])
        # sample the lot: no building within 3 m, no road (but its own) through it, no water
        for a in [-W / 2 + k * W / 6 for k in range(7)]:
            for b in [-D / 2 + k * D / 4 for k in range(5)]:
                p = (c[0] + u[0] * a + n[0] * b, c[1] + u[1] * a + n[1] * b)
                i, j = int((p[0] % C) / step) % nx, int((p[1] - x0) / step)
                if not (0 <= j < ny) or lvl[j, i] > -9000:
                    return False
                for s_, x_, r in FP:
                    if math.hypot(wrap(s_ - p[0]), x_ - p[1]) < r + 3.0:
                        return False
                for a_, b_, hw, ri in SEGS:
                    if abs(wrap(a_[0] - p[0])) > 120 and abs(wrap(b_[0] - p[0])) > 120:
                        continue
                    if seg_dist(p, a_, b_) < hw + (0.5 if ri == front_road else 1.5):
                        return False
        for a in ter["areas"]:
            ac = (sum(q[0] for q in a["poly"]) / len(a["poly"]), sum(q[1] for q in a["poly"]) / len(a["poly"]))
            if math.hypot(wrap(ac[0] - c[0]), ac[1] - c[1]) < max(W, D) * 0.6:
                return False
        return True

    def lot(kind, town, city, c, u, W, stop=None):
        n = (-u[1], u[0])
        rows = []
        v = -DEPTH / 2
        for bay in range(2):
            rows.append([round(-W / 2 + 1.0, 2), round(W / 2 - 1.0, 2), round(v, 2), STALL_D, -1])
            rows.append([round(-W / 2 + 1.0, 2), round(W / 2 - 1.0, 2), round(v + STALL_D + AISLE, 2), STALL_D, 1])
            v += 2 * STALL_D + AISLE
        per_row = int((W - 2.0) / STALL_W)
        spaces = per_row * len(rows)
        access = (c[0] + n[0] * (-DEPTH / 2 - 1.0), c[1] + n[1] * (-DEPTH / 2 - 1.0))
        return {"kind": "parking", "town": town, "poly": [[round(p[0] % C, 2), round(p[1], 2)] for p in rect(c, u, W, DEPTH)],
                "lot": {"type": kind, "town": town, "city": city, "spaces": spaces, "accessible": max(1, math.ceil(spaces / 25)),
                        "centre": [round(c[0] % C, 2), round(c[1], 2)], "dir": [round(u[0], 4), round(u[1], 4)], "w": W, "d": DEPTH,
                        "rows": rows, "per_row": per_row, "access": [round(access[0] % C, 2), round(access[1], 2)], "stop": stop}}

    made = []
    # downtown lots
    for cid, city in cities.items():
        st = sets.get(city["name"])
        if not st or not st.get("centre"):
            continue
        cen = st["centre"]
        best = None
        for ri, rd in enumerate(ter["roads"]):
            if not rd.get("xs", "").endswith("core") and rd.get("xs") not in ("main/town",):
                continue
            pts = rd["pts"]
            for k in range(1, len(pts) - 2):                 # never at an end (a corner)
                a, b = pts[k], pts[k + 1]
                if math.hypot(wrap(a[0] - cen[0]), a[1] - cen[1]) > 320:
                    continue
                ds, dx = wrap(b[0] - a[0]), b[1] - a[1]
                L = math.hypot(ds, dx)
                if L < 1e-6:
                    continue
                u = (ds / L, dx / L)
                for side in (1, -1):
                    n = (-u[1] * side, u[0] * side)
                    edge = (rd["hr"] if side > 0 else rd["hl"]) + rd.get("lawn", 0) + rd.get("walk", 0)
                    c = (a[0] + n[0] * (edge + GAP + DEPTH / 2), a[1] + n[1] * (edge + GAP + DEPTH / 2))
                    d = math.hypot(wrap(c[0] - cen[0]), c[1] - cen[1])
                    if best and d >= best[0]:
                        continue
                    uu = u if side > 0 else (-u[0], -u[1])
                    if free(c, uu, DOWNTOWN_W, DEPTH, ri):
                        best = (d, c, uu)
        if best:
            made.append(lot("downtown", city["name"], cid, best[1], best[2], DOWNTOWN_W))
    # park-and-ride lots at their stops
    for l in transit:
        for sp in l["stops"]:
            if not sp.get("pnr"):
                continue
            p = (sp["s"], sp["x"])
            L = math.hypot(*sp["dir"]) or 1.0
            u = (sp["dir"][0] / L, sp["dir"][1] / L)
            town = sp["town"]
            gov = sets.get(town, {}).get("governed_by")
            # the road under the stop, for the setback
            near = min(SEGS, key=lambda sg: seg_dist(p, sg[0], sg[1]))
            ok = None
            for side in (1, -1):                              # the kerbside first (we drive on the right)
                n = (-u[1] * side, u[0] * side)
                for shift in (0, 20, -20, 40, -40, 60, -60):
                    c = (p[0] + u[0] * shift + n[0] * (near[2] + GAP + DEPTH / 2 + 2.0), p[1] + u[1] * shift + n[1] * (near[2] + GAP + DEPTH / 2 + 2.0))
                    uu = u if side > 0 else (-u[0], -u[1])
                    if free(c, uu, PNR_W, DEPTH, near[3]):
                        ok = (c, uu)
                        break
                if ok:
                    break
            if ok:
                made.append(lot("park_and_ride", town, gov, ok[0], ok[1], PNR_W, stop=sp["name"]))
            else:
                print("no room for the park & ride at %s" % sp["name"])
    ter["areas"] += made
    json.dump(ter, open(ter_p, "w"), indent=0)
    for m in made:
        print("%-14s %-16s %3d spaces (%d accessible)%s" % (m["lot"]["type"], m["town"], m["lot"]["spaces"], m["lot"]["accessible"],
                                                         ("  at " + m["lot"]["stop"]) if m["lot"]["stop"] else ""))


if __name__ == "__main__":
    main()
