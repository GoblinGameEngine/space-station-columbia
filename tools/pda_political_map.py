#!/usr/bin/env python3
"""The Navigation app's political map (godot_project/ui/pda/map_political.png), in the Communicator's
four LCD greys: 8 m a pixel, north (the bow, x = -4000) at the top, s (round the ring) to the right.

  land white; water light grey; town limits (each settlement's built-up area) dark grey outlined in
  black; roads black (highways two pixels); each large city's jurisdiction -- the settlements that
  follow its law (research/law/03_settlements.md) and the country nearest them -- its own sparse dot
  pattern, with a dashed boundary between jurisdictions. Names, tram lines, stops and the player are
  drawn live by the app over it.

    python3 tools/pda_political_map.py        (after tools/law/make_law.py and the map pipeline)
"""
import gzip
import json
import math
import os

import numpy as np
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GD = os.path.join(ROOT, "godot_project", "remake")
OUT = os.path.join(ROOT, "godot_project", "ui", "pda", "map_political.png")
MPP = 8.0
K, D, L, W = 0, 85, 170, 255
# each jurisdiction's dot pattern: (spacing, offset x, offset y, diagonal)
PATTERN = {"port_carrow": (6, 0, 0, False), "kessler": (6, 3, 3, True), "solana_point": (5, 1, 2, False),
           "harrow_falls": (7, 2, 5, True), "brightwater": (4, 0, 2, False), "oceanview": (8, 4, 1, True)}


def main():
    ter = json.load(open(os.path.join(GD, "terrain.json")))
    C = 2 * math.pi * ter["R"]
    rs = ter["raster"]
    nx, ny, step, x0 = rs["nx"], rs["ny"], rs["step_m"], rs["x0"]
    lvl = np.frombuffer(gzip.open(os.path.join(GD, rs["level"])).read(), np.float16).reshape(ny, nx)
    w = int(round(C / MPP))
    h = int(round(8000.0 / MPP))
    # water: the level raster resampled
    ys = ((np.arange(h) + 0.5) * MPP / step).astype(int).clip(0, ny - 1)
    xs = ((np.arange(w) + 0.5) * MPP / step).astype(int) % nx
    water = (lvl[ys][:, xs] > -9000)
    img = np.full((h, w), W, np.uint8)
    # jurisdictions: nearest settlement's governing city
    sets = json.load(open(os.path.join(GD, "law", "settlements.json")))["settlements"]
    cent = [(r["centre"][0], r["centre"][1], r["governed_by"]) for r in sets if r.get("centre")]
    S = (np.arange(w) + 0.5) * MPP
    X = (np.arange(h) + 0.5) * MPP - 4000.0
    best = np.full((h, w), np.inf)
    jur = np.full((h, w), -1, np.int16)
    cities = sorted(PATTERN)
    for cs, cx, gov in cent:
        ds = (S[None, :] - cs + C / 2) % C - C / 2
        d2 = ds * ds + (X[:, None] - cx) ** 2
        m = d2 < best
        best[m] = d2[m]
        jur[m] = cities.index(gov)
    yy, xx = np.mgrid[0:h, 0:w]
    for i, cid in enumerate(cities):
        sp, ox, oy, diag = PATTERN[cid]
        if diag:
            dots = ((xx + yy + ox) % sp == 0) & ((yy + oy) % sp == 0)
        else:
            dots = ((xx + ox) % sp == 0) & ((yy + oy) % sp == 0)
        img[(jur == i) & dots & ~water] = D
    # jurisdiction boundaries, dashed
    edge = np.zeros((h, w), bool)
    edge[:, 1:] |= jur[:, 1:] != jur[:, :-1]
    edge[1:, :] |= jur[1:, :] != jur[:-1, :]
    dash = ((xx + yy) // 3) % 2 == 0
    img[edge & dash & ~water] = K
    img[water] = L
    # town limits: each settlement's structures, widened 30 m
    pl = json.load(open(os.path.join(GD, "placement.json")))["structures"]
    town = np.zeros((h, w), bool)
    r = int(30 / MPP)
    for e in pl:
        if not e.get("settlement") or e["kind"] == "crossing":
            continue
        i, j = int(e["s"] % C / MPP), int((e["x"] + 4000) / MPP)
        town[max(0, j - r):j + r + 1, max(0, i - r):i + r + 1] = True
    for _ in range(2):                                   # close the gaps between blocks
        t = town.copy()
        t[1:, :] |= town[:-1, :]
        t[:-1, :] |= town[1:, :]
        t[:, 1:] |= town[:, :-1]
        t[:, :-1] |= town[:, 1:]
        town = t
    rim = town & ~(np.roll(town, 1, 0) & np.roll(town, -1, 0) & np.roll(town, 1, 1) & np.roll(town, -1, 1))
    img[town & ~water] = D
    img[rim] = K
    # roads
    for rd in ter["roads"]:
        thick = 1 if rd["cls"] != "hwy" else 2
        pts = rd["pts"]
        for a, b in zip(pts, pts[1:]):
            ds = (b[0] - a[0] + C / 2) % C - C / 2
            n = max(1, int(math.hypot(ds, b[1] - a[1]) / (MPP * 0.5)))
            for t in range(n + 1):
                s = (a[0] + ds * t / n) % C
                x = a[1] + (b[1] - a[1]) * t / n
                i, j = int(s / MPP) % w, int((x + 4000) / MPP)
                if 0 <= j < h:
                    img[j:j + thick, i:i + thick] = K
    Image.fromarray(img, "L").convert("RGBA").save(OUT)
    print("political map %dx%d -> %s" % (w, h, OUT))


if __name__ == "__main__":
    main()
