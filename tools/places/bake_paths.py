#!/usr/bin/env python3
"""Bake the walking network: the road polylines (remake/terrain.json) as a graph of junctions,
and every building's door attached to its nearest road -- the routes people take between home,
work and the shops (NpcLife.route).

    python3 tools/places/bake_paths.py

Writes godot_project/remake/characters/npc_paths.json:
  nodes  [[s, x], ...]                         junctions and dead ends
  edges  [[n0, n1, road, u0, u1, length], ...] a stretch of road `road` (terrain.json roads index)
                                               between polyline parameters u0 < u1 (vertex k + t);
                                               road -1: a bridge deck, straight from n0 to n1
  attach {building id: [edge, u, metres]}      where the building's door meets the network
Junctions: shared vertices, and road ends that meet another road within SNAP m (T-junctions).
Highways are included (the shoulder: towns are joined only by them); RERUN after the road map changes.
"""
import json
import math
import os
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
CIRC = math.tau * json.load(open(os.path.join(ROOT, "godot_project", "remake", "terrain.json")))["R"]      # (the ring's radius from the map)
SNAP = 4.0
LANE_SNAP = 25.0
ATTACH = 80.0
CELL = 50.0
WALK = {"street", "main", "alley", "gravel", "county", "hwy"}


def wrap(ds):
    return (ds + CIRC / 2) % CIRC - CIRC / 2


def door(b):
    yaw = b["yaw"]
    fz = b["fmin"][1]
    fx = (b["fmin"][0] + b["fmax"][0]) * 0.5
    d = -fz + 1.2
    return ((b["s"] + math.cos(yaw) * d + math.sin(yaw) * fx) % CIRC, b["x"] - math.sin(yaw) * d + math.cos(yaw) * fx)


def main():
    terr = json.load(open(os.path.join(ROOT, "godot_project", "remake", "terrain.json")))
    roads = terr["roads"]
    walk = [i for i, r in enumerate(roads) if r["cls"] in WALK]
    grid = defaultdict(list)                       # cell -> [(road, seg)]
    for i in walk:
        p = roads[i]["pts"]
        for k in range(len(p) - 1):
            a, b = p[k], p[k + 1]
            s0 = a[0]
            s1 = a[0] + wrap(b[0] - a[0])
            for cs in range(math.floor((min(s0, s1) - SNAP) / CELL), math.floor((max(s0, s1) + SNAP) / CELL) + 1):
                for cx in range(math.floor((min(a[1], b[1]) - SNAP) / CELL), math.floor((max(a[1], b[1]) + SNAP) / CELL) + 1):
                    grid[(cs % round(CIRC / CELL + 0.5), cx)].append((i, k))
    ncs = round(CIRC / CELL + 0.5)

    def nearest(pt, skip=None, maxd=SNAP, cells=1, streets_only=False):
        best = None
        cs, cx = math.floor((pt[0] % CIRC) / CELL), math.floor(pt[1] / CELL)
        seen = set()
        for i in range(-cells, cells + 1):
            for j in range(-cells, cells + 1):
                for (ri, k) in grid.get(((cs + i) % ncs, cx + j), []):
                    if (ri, k) in seen or ri == skip or (streets_only and roads[ri]["cls"] == "hwy"):
                        continue
                    seen.add((ri, k))
                    a, b = roads[ri]["pts"][k], roads[ri]["pts"][k + 1]
                    abx, aby = wrap(b[0] - a[0]), b[1] - a[1]
                    px, py = wrap(pt[0] - a[0]), pt[1] - a[1]
                    L2 = abx * abx + aby * aby
                    t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, (px * abx + py * aby) / L2))
                    d = math.hypot(px - abx * t, py - aby * t)
                    if d <= maxd and (best is None or d < best[0]):
                        best = (d, ri, k + t)
        return best

    # split parameters per road: its ends, plus where other roads' ends meet it
    splits = {i: {0.0, float(len(roads[i]["pts"]) - 1)} for i in walk}
    end_at = {}                                    # (road, end u) -> (other road, u) it joins
    for i in walk:
        p = roads[i]["pts"]
        for u in (0.0, float(len(p) - 1)):
            q = p[int(u)]
            hit = nearest(q, skip=i) or nearest(q, skip=i, maxd=LANE_SNAP)       # farm lanes that stop short
            if hit:
                splits[hit[1]].add(round(hit[2], 4))
                end_at[(i, u)] = (hit[1], round(hit[2], 4))

    # crossings: roads that cross mid-segment (a street over the highway) join there too
    xs = 0
    for cell, segs in grid.items():
        for m in range(len(segs)):
            ri, k = segs[m]
            a, b = roads[ri]["pts"][k], roads[ri]["pts"][k + 1]
            d1 = (wrap(b[0] - a[0]), b[1] - a[1])
            for n in range(m + 1, len(segs)):
                rj, l = segs[n]
                if rj == ri:
                    continue
                c, e = roads[rj]["pts"][l], roads[rj]["pts"][l + 1]
                d2 = (wrap(e[0] - c[0]), e[1] - c[1])
                ac = (wrap(c[0] - a[0]), c[1] - a[1])
                den = d1[0] * d2[1] - d1[1] * d2[0]
                if abs(den) < 1e-9:
                    continue
                t = (ac[0] * d2[1] - ac[1] * d2[0]) / den
                u = (ac[0] * d1[1] - ac[1] * d1[0]) / den
                if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
                    ua, ub = round(k + t, 4), round(l + u, 4)
                    if ua not in splits[ri] or ub not in splits[rj]:
                        xs += 1
                    splits[ri].add(ua)
                    splits[rj].add(ub)

    # bridges: their decks aren't in the road list; join the roads at the two ends
    links = []
    for br in json.load(open(os.path.join(ROOT, "godot_project", "remake", "bridges.json")))["bridges"]:
        hs = [nearest(e, maxd=40.0) for e in br["ends"]]
        if all(hs):
            for h in hs:
                splits[h[1]].add(round(h[2], 4))
            links.append([(h[1], round(h[2], 4)) for h in hs])

    def pos(ri, u):
        p = roads[ri]["pts"]
        k = min(int(u), len(p) - 2)
        t = u - k
        a, b = p[k], p[k + 1]
        return ((a[0] + wrap(b[0] - a[0]) * t) % CIRC, a[1] + (b[1] - a[1]) * t)

    # nodes: merge positions within 0.5 m (shared vertices and snapped ends)
    nodes = []
    nidx = {}

    def node_at(pt):
        key = (round(pt[0] / 1.0), round(pt[1] / 1.0))
        for dk in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
            kk = ((key[0] + dk[0]) % round(CIRC), key[1] + dk[1])
            for n in nidx.get(kk, []):
                if math.hypot(wrap(nodes[n][0] - pt[0]), nodes[n][1] - pt[1]) < 1.0:
                    return n
        nodes.append([round(pt[0], 2), round(pt[1], 2)])
        nidx.setdefault((key[0] % round(CIRC), key[1]), []).append(len(nodes) - 1)
        return len(nodes) - 1

    def seglen(ri, u0, u1):
        n = 0.0
        pts = [pos(ri, u0)] + [roads[ri]["pts"][k] for k in range(math.floor(u0) + 1, math.ceil(u1))] + [pos(ri, u1)]
        for a, b in zip(pts, pts[1:]):
            n += math.hypot(wrap(b[0] - a[0]), b[1] - a[1])
        return n

    edges = []
    by_road = defaultdict(list)
    for i in walk:
        us = sorted(splits[i])
        for u0, u1 in zip(us, us[1:]):
            if u1 - u0 < 1e-4:
                continue
            e0 = end_at.get((i, u0))
            e1 = end_at.get((i, u1))
            n0 = node_at(pos(*e0) if e0 else pos(i, u0))
            n1 = node_at(pos(*e1) if e1 else pos(i, u1))
            edges.append([n0, n1, i, round(u0, 4), round(u1, 4), round(seglen(i, u0, u1), 2)])
            by_road[i].append(len(edges) - 1)

    for a, b in links:
        n0, n1 = node_at(pos(*a)), node_at(pos(*b))
        if n0 != n1:
            edges.append([n0, n1, -1, 0.0, 1.0, round(math.hypot(wrap(nodes[n1][0] - nodes[n0][0]), nodes[n1][1] - nodes[n0][1]), 2)])

    # doors -> the nearest walkable road
    structs = json.load(open(os.path.join(ROOT, "godot_project", "remake", "placement.json")))["structures"]
    attach = {}
    far = 0
    for b in structs:
        d = door(b)
        hit = nearest(d, maxd=ATTACH, cells=2, streets_only=True)
        if not hit:
            far += 1
            continue
        _, ri, u = hit
        e = next(ei for ei in by_road[ri] if edges[ei][3] - 1e-6 <= u <= edges[ei][4] + 1e-6)
        attach[b["id"]] = [e, round(u, 4), round(hit[0], 1)]

    # connectivity report
    par = list(range(len(nodes)))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for e in edges:
        par[find(e[0])] = find(e[1])
    comp = defaultdict(int)
    for n in range(len(nodes)):
        comp[find(n)] += 1
    big = max(comp.values())
    out = {"_about": "Walking network (junction graph over terrain.json roads) and door attachments. tools/places/bake_paths.py; read by NpcLife.",
           "nodes": nodes, "edges": edges, "attach": attach}
    with open(os.path.join(ROOT, "godot_project", "remake", "characters", "npc_paths.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("crossings %d" % xs)
    print("roads %d walkable, %d bridges; nodes %d, edges %d; components %d (largest %d nodes); doors attached %d, beyond %d m %d"
          % (len(walk), len(links), len(nodes), len(edges), len(comp), big, len(attach), ATTACH, far))


if __name__ == "__main__":
    main()
