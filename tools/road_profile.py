#!/usr/bin/env python3
"""Road grading (SSC-RS 1 §8, research/roads/grading.md): every road's longitudinal profile, held to
the maximum grade of its class, written into remake/terrain.json for MapTerrain to grade the ground to.

Before this, a road simply took the raw terrain's height under its centreline, so where it crossed a
bluff it climbed the bluff: grades of 30-100 %, and "cliffs" no car can drive.  Here:

  1. Every road (and the railway) is sampled every STEP m along its centreline.  Samples of
     different roads within JOIN m of each other (junctions, crossings, the highway where it runs
     down a town's main street) are linked, so the whole network is one graph and a junction has
     one height.
  2. Each link may climb at most g * length, g the class's maximum grade (the lower of the two at a
     junction) -- AASHTO Green Book / TxDOT RDM Table 4-11 values, in GRADE below.
  3. The heights are the best fit to the terrain under that limit: the midpoint of the upper and
     lower envelopes U(i) = min_j (base_j + g-distance(j, i)) and L(i) = max_j (...) -- each found
     with one Dijkstra pass.  That midpoint is the grade-limited profile with the least largest
     cut or fill (McShane-Whitney), and cutting and filling alike is how roads are built.
  4. Crests and sags are rounded into vertical curves (a running mean over each road, VC m long:
     about 3 x the design speed in mph, in feet -- TxDOT's preferred minimum; averaging keeps every
     grade within its limit).
  5. Small crossings (placement.json, kind "crossing") are level decks: each is pinned at the higher
     of its two approaches, and the road ramps to it at no more than its grade.  Samples over the
     great rivers under the great bridges carry no terrain (the bridge climbs from the graded banks).

Writes, per road and for the railway, "prof": heights every "prof_step" m of arc length from its
first point; and "decks": {crossing id: deck height}.
    python3 tools/road_profile.py            (after placement.py; then rerun the bakes)
"""
import gzip
import heapq
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GD = os.path.join(HERE, "..", "godot_project", "remake")
STEP = 4.0
JOIN = 3.0
PIN_OUT = 5.0          # m past each end of a small bridge the road is held level with its deck
LANDING = 12.0         # m either side of a junction held to LANDING_GRADE (a flat approach to the intersection)
LANDING_GRADE = 0.03   # desirable at an intersection (Green Book)...
LANDING_MAX = 0.06     # ...and at most, where holding to the desirable would cut or fill more than RELAX_AT
RELAX_AT = 2.5
# class -> (maximum grade, design speed mph, context) -- see research/roads/grading.md
GRADE = {
    "hwy": (0.05, 55, "rural arterial, rolling"),
    "county": (0.07, 45, "rural collector, rolling"),
    "gravel": (0.10, 30, "rural local, rolling"),
    "main": (0.07, 30, "urban arterial, rolling"),
    "street": (0.08, 25, "urban local (all terrain)"),
    "alley": (0.08, 15, "urban local (all terrain)"),
    "rail": (0.015, 60, "mainline railway (AREMA)"),
}
VC_FT_PER_MPH = 3.0


def main():
    ter_path = os.path.join(GD, "terrain.json")
    ter = json.load(open(ter_path))
    R = ter["R"]
    C = 2 * math.pi * R
    rs = ter["raster"]
    nx, ny, step, x0 = rs["nx"], rs["ny"], rs["step_m"], rs["x0"]

    def raster(name):
        return np.frombuffer(gzip.open(os.path.join(GD, name)).read(), np.float16).astype(np.float32).reshape(ny, nx)
    BASE = raster(rs["base"])
    LEVEL = raster(rs["level"])

    def bil(buf, s, x):
        fx = (s % C) / step - 0.5
        fy = (x - x0) / step - 0.5
        i0 = math.floor(fx)
        j0 = min(max(math.floor(fy), 0), ny - 2)
        tx = fx - i0
        ty = min(max(fy - j0, 0.0), 1.0)
        i0 %= nx
        i1 = (i0 + 1) % nx
        a = buf[j0, i0] * (1 - tx) + buf[j0, i1] * tx
        b = buf[j0 + 1, i0] * (1 - tx) + buf[j0 + 1, i1] * tx
        return float(a * (1 - ty) + b * ty)

    def level(s, x):
        fx = int((s % C) / step)
        fy = min(max(int((x - x0) / step), 0), ny - 1)
        return float(LEVEL[fy, fx % nx])

    def wrap(d):
        return (d + C / 2) % C - C / 2

    roads = list(ter["roads"]) + [dict(ter["rail"], cls="rail")]
    # ---- 1. samples
    nodes = []            # (s, x, road index, k)
    first = []            # road -> its first node index
    for ri, rd in enumerate(roads):
        pts = rd["pts"]
        cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            cum.append(cum[-1] + math.hypot(wrap(b[0] - a[0]), b[1] - a[1]))
        total = cum[-1]
        n = max(1, math.ceil(total / STEP))
        first.append(len(nodes))
        seg = 0
        for k in range(n + 1):
            u = min(k * STEP, total)
            while seg < len(pts) - 2 and cum[seg + 1] < u:
                seg += 1
            L = cum[seg + 1] - cum[seg]
            t = 0.0 if L < 1e-6 else (u - cum[seg]) / L
            a, b = pts[seg], pts[seg + 1]
            nodes.append((a[0] + wrap(b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, ri, k))
        rd["_n"] = n + 1
        rd["_total"] = total
    N = len(nodes)
    S = np.array([n_[0] for n_ in nodes])
    X = np.array([n_[1] for n_ in nodes])
    RI = np.array([n_[2] for n_ in nodes])
    g_of = np.array([GRADE[roads[r]["cls"]][0] for r in RI])
    base = np.array([bil(BASE, S[i], X[i]) for i in range(N)])

    # ---- the great bridges' water spans and the small crossings
    free = np.zeros(N, bool)
    bridges = json.load(open(os.path.join(GD, "bridges.json")))["bridges"]
    for br in bridges:
        (sa, xa), (sb, xb) = br["ends"]
        ds, dx = wrap(sb - sa), xb - xa
        L = math.hypot(ds, dx)
        us = (wrap(S - sa) * ds + (X - xa) * dx) / L
        off = np.abs(wrap(S - sa) * dx - (X - xa) * ds) / L
        free |= (us > -2) & (us < L + 2) & (off < 100)         # (a road may wander off the bridge's straight line over the water)
    great = free.copy()
    wet = np.array([level(S[i], X[i]) > -9000 and level(S[i], X[i]) > base[i] - 0.05 for i in range(N)])
    print("samples %d, under great bridges %d, wet elsewhere %d" % (N, free.sum(), (wet & ~free).sum()))
    free |= wet
    pl = json.load(open(os.path.join(GD, "placement.json")))["structures"]
    crossings = [e for e in pl if e["kind"] == "crossing"]
    cross_of = np.full(N, -1)
    for ci, e in enumerate(crossings):
        c, sn = math.cos(e["yaw"]), math.sin(e["yaw"])
        ds, dx = wrap(S - e["s"]), X - e["x"]
        lx = dx * c + ds * sn
        lz = dx * sn - ds * c
        cx = (e["fmin"][0] + e["fmax"][0]) * 0.5
        hw = (e["fmax"][0] - e["fmin"][0]) * 0.5
        # the deck and PIN_OUT m past each end level with it: the profile's samples are STEP apart,
        # so the ramp down to the road starts clear of the model, not part-way along its deck
        inside = (np.abs(lx - cx) < hw + 1.0) & (lz > e["fmin"][1] - PIN_OUT) & (lz < e["fmax"][1] + PIN_OUT)
        cross_of[inside] = ci
    free |= cross_of >= 0

    # ---- links: along each road, and between roads' samples within JOIN m
    adj = [[] for _ in range(N)]

    def link(i, j, same_height=False):
        d = math.hypot(wrap(S[j] - S[i]), X[j] - X[i])
        w = 0.0 if same_height else min(g_of[i], g_of[j]) * max(d, 0.05)
        adj[i].append((j, w))
        adj[j].append((i, w))
    cell = {}
    for i in range(N):
        cell.setdefault((int((S[i] % C) // JOIN), int(X[i] // JOIN)), []).append(i)
    ncs = int(C // JOIN) + 1
    joins = 0
    junction = np.zeros(N, bool)
    for (cs, cx), members in cell.items():
        for dcs in (-1, 0, 1):
            for dcx in (-1, 0, 1):
                other = cell.get(((cs + dcs) % ncs, cx + dcx))
                if not other:
                    continue
                for i in members:
                    for j in other:
                        if j <= i:
                            continue
                        # a road meeting itself (a ring road closing at the seam, a loop) is a
                        # junction too -- not its own next samples
                        if RI[i] == RI[j] and abs(int(nodes[i][3]) - int(nodes[j][3])) * STEP <= 4 * JOIN:
                            continue
                        if math.hypot(wrap(S[j] - S[i]), X[j] - X[i]) <= JOIN:
                            link(i, j, same_height=True)       # one height across a junction
                            junction[i] = junction[j] = True
                            joins += 1
    print("junction links", joins)
    # the approaches: within LANDING m of a junction along its own road, no steeper than LANDING_GRADE
    near_j = np.zeros(N, bool)
    for ri, rd in enumerate(roads):
        f0, n = first[ri], rd["_n"]
        js = np.nonzero(junction[f0:f0 + n])[0]
        if len(js):
            k = np.arange(n)
            dmin = np.min(np.abs(k[:, None] - js[None, :]), axis=1) * STEP
            near_j[f0:f0 + n] = dmin <= LANDING
    join_adj = [list(a) for a in adj]

    def build(relaxed):
        """The links: the junctions' (fixed above) and each road's, landings held to their grade."""
        out = [list(a) for a in join_adj]
        for ri, rd in enumerate(roads):
            f0 = first[ri]
            for k in range(rd["_n"] - 1):
                i, j = f0 + k, f0 + k + 1
                d = math.hypot(wrap(S[j] - S[i]), X[j] - X[i])
                g = min(g_of[i], g_of[j])
                if near_j[i] and near_j[j]:
                    g = min(g, LANDING_MAX if (relaxed[i] or relaxed[j]) else LANDING_GRADE)
                out[i].append((j, g * max(d, 0.05)))
                out[j].append((i, g * max(d, 0.05)))
        return out
    relaxed = np.zeros(N, bool)
    adj = build(relaxed)

    def envelope(init, sign):
        """sign +1: U(i) = min_j (init_j + dist); sign -1: L(i) = max_j (init_j - dist)."""
        dist = np.full(N, np.inf)
        heap = []
        for i in range(N):
            if np.isfinite(init[i]):
                dist[i] = sign * init[i]
                heap.append((dist[i], i))
        heapq.heapify(heap)
        while heap:
            d, i = heapq.heappop(heap)
            if d > dist[i]:
                continue
            for j, w in adj[i]:
                nd = d + w
                if nd < dist[j]:
                    dist[j] = nd
                    heapq.heappush(heap, (nd, j))
        return sign * dist

    src = np.where(free, np.inf, base)
    for attempt in range(2):
        U = envelope(src, 1)
        Lo = envelope(src, -1)
        ok = np.isfinite(U) & np.isfinite(Lo)
        z = np.where(ok, (U + Lo) * 0.5, base)
        # landings that cost too much earthwork at the desirable grade get the most allowed instead
        big = near_j & ok & ~free & (np.abs(z - base) > RELAX_AT)
        if attempt == 1 or not big.any():
            break
        relaxed |= big
        # and the rest of each such landing (the whole approach, not just its worst sample)
        for ri, rd in enumerate(roads):
            f0, n = first[ri], rd["_n"]
            seg = relaxed[f0:f0 + n].copy()
            for k in np.nonzero(seg)[0]:
                a, b = max(0, k - int(LANDING / STEP) * 2), min(n, k + int(LANDING / STEP) * 2 + 1)
                relaxed[f0 + a:f0 + b] |= near_j[f0 + a:f0 + b]
        print("landings relaxed to %d %%: %d samples" % (LANDING_MAX * 100, relaxed.sum()))
        adj = build(relaxed)
    dev = np.abs(z - base)[~free & ok]
    print("fit: largest cut/fill %.1f m, mean %.2f m, over 2 m: %d samples" % (dev.max(), dev.mean(), (dev > 2).sum()))

    # ---- 4. vertical curves: a running mean over each road
    def smooth(z, skip):
        out = z.copy()
        for ri, rd in enumerate(roads):
            f0, n = first[ri], rd["_n"]
            gv, mph, _ = GRADE[rd["cls"]]
            half = max(1, int(round(VC_FT_PER_MPH * mph * 0.3048 / STEP / 2)))
            seg = z[f0:f0 + n]
            pad = np.concatenate([np.full(half, seg[0]), seg, np.full(half, seg[-1])])
            ker = np.ones(2 * half + 1) / (2 * half + 1)
            sm = np.convolve(pad, ker, "valid")
            keep = skip[f0:f0 + n]
            out[f0:f0 + n] = np.where(keep, seg, sm)
        return out
    z = smooth(z, np.zeros(N, bool))

    def repair(z):
        """The nearest heights (least largest change) that keep every limit again: smoothing each
        road on its own can pull a junction's roads apart."""
        U = envelope(z, 1)
        Lo = envelope(z, -1)
        return (U + Lo) * 0.5
    z = repair(z)

    # ---- 5. crossings: level decks at the higher approach, the roads ramping to them.  One at a time,
    # each within what the ones already set allow (two crossings close together on one road can't
    # each take their own approaches' height when those differ by more than the grade between them
    # allows): U / L are the pinned decks' grade envelopes, grown crossing by crossing.
    decks = {}
    unbuilt = []
    Up = np.full(N, np.inf)
    Lp = np.full(N, -np.inf)

    def grow(env, idx, value, sign):
        """Lower env (sign +1: the upper envelope) / raise it (sign -1) from the nodes idx held at
        value, as far as it changes anything."""
        heap = []
        for i in idx:
            v = sign * value
            if v < sign * env[i]:
                env[i] = value
                heap.append((v, i))
        heapq.heapify(heap)
        while heap:
            d, i = heapq.heappop(heap)
            if d > sign * env[i]:
                continue
            for j, w in adj[i]:
                nd = d + w
                if nd < sign * env[j]:
                    env[j] = sign * nd
                    heapq.heappush(heap, (nd, j))
    order = sorted(range(len(crossings)), key=lambda ci: -{"hwy": 6, "main": 5, "county": 4, "street": 3, "gravel": 2}.get(
        crossings[ci].get("road_class") or "", 0))
    for ci in order:
        e = crossings[ci]
        idx = np.nonzero(cross_of == ci)[0]
        if len(idx) == 0:
            continue
        near = set()
        for i in idx:
            for j, _ in adj[i]:
                if cross_of[j] != ci:
                    near.add(j)
        natural = float(max([z[j] for j in near] or [z[i] for i in idx]))
        lo, hi = float(Lp[idx].max()), float(Up[idx].min())
        if lo > hi + 0.01:
            # it can't lie level between the decks already set without the road between them
            # going past its grade: left out -- its road crosses on a buried culvert
            unbuilt.append(e["id"])
            cross_of[idx] = -1
            continue
        deck = min(max(natural, lo), hi)
        decks[e["id"]] = round(deck, 2)
        grow(Up, idx, deck, 1)
        grow(Lp, idx, deck, -1)
    z = np.minimum(np.maximum(z, Lp), Up)
    off = [(abs(float(z[np.nonzero(cross_of == ci)[0]].max() - decks[e["id"]])), e["id"]) for ci, e in enumerate(crossings)
           if e["id"] in decks]
    off += [(abs(float(z[np.nonzero(cross_of == ci)[0]].min() - decks[e["id"]])), e["id"]) for ci, e in enumerate(crossings)
            if e["id"] in decks]
    worst_off = max(off)
    print("crossings: road off its deck by at most %.3f m (%s)" % worst_off)
    for o, cid in sorted(off, reverse=True)[:8]:
        if o > 0.05:
            print("   %s off by %.2f" % (cid, o))

    # ---- checks and output
    worst = []
    for ri, rd in enumerate(roads):
        f0, n = first[ri], rd["_n"]
        seg = z[f0:f0 + n]
        if n > 1:
            gr = np.abs(np.diff(seg))[~(great[f0:f0 + n - 1] | great[f0 + 1:f0 + n])] / STEP
        if n > 1 and len(gr):
            lim = GRADE[rd["cls"]][0]
            if gr.max() > lim * 1.02 + 1e-3:
                worst.append((gr.max() / lim, rd.get("name") or rd.get("town"), rd["cls"], float(gr.max())))
        # over a great river the road is carried by its great bridge: no ground height there
        gfree = great[f0:f0 + n]
        prof = [-9999.0 if gfree[k] else round(float(v), 2) for k, v in enumerate(seg)]
        tgt = ter["rail"] if rd["cls"] == "rail" and ri == len(roads) - 1 else ter["roads"][ri]
        tgt["prof"] = prof
        rd.pop("_n", None)
        rd.pop("_total", None)
    ter["prof_step"] = STEP
    ter["decks"] = decks
    worst.sort(reverse=True)
    print("roads over their grade (the last sample to a road's end is shorter than STEP):", len(worst))
    for w in worst[:10]:
        print("  %.2fx  %s (%s) %.1f %%" % (w[0], w[1], w[2], w[3] * 100))
    json.dump(ter, open(ter_path, "w"), indent=0)
    if unbuilt:
        # (placement.py placed them; they come out here, the only place their grading is known)
        pl_path = os.path.join(GD, "placement.json")
        pld = json.load(open(pl_path))
        pld["structures"] = [e for e in pld["structures"] if e["id"] not in unbuilt]
        json.dump(pld, open(pl_path, "w"), indent=0)
        print("crossings that can't lie level within the grade, left out:", " ".join(unbuilt))
    print("wrote", ter_path, "decks:", len(decks))


if __name__ == "__main__":
    main()
