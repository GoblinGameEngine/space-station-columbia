#!/usr/bin/env python3
"""fleet_test.py -- the body tests (tools/vehicle_seal_test.py) over every fleet blueprint, one line each:
both shells sealed round the cabin, no frame tube in view from outside, nothing drawn across an opening.

    ~/.venvs/ssc-assets/bin/python tools/fleet_test.py [type ...]      # default: every godot_project/remake/vehicles/fleet/*.blueprint.json

Exit status 1 if any vehicle fails. Details for one: the seal test itself (TUBES=1 / CROSS=1 for the others).
"""
import contextlib
import math
import glob
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vehicle_seal_test as v  # noqa: E402
import numpy as np  # noqa: E402

FLEET = os.path.join(HERE, "..", "godot_project", "remake", "vehicles", "fleet")


def seal(path, dirs):
    bp, by = v.load_body(path)
    pts = [tuple(p) for p in bp.get("cabin_points", [])]
    out = []
    for shell in (v.EXTERIOR, v.INTERIOR):
        tri = np.concatenate([v.gather(by, shell | v.CLOSERS), v.platform(bp)])
        out.append(len(v.escapes(bp, tri, pts, dirs)))
    return out


def main():
    names = [n for n in sys.argv[1:] if not n.startswith("-")]
    if "--wheels" in sys.argv:                             # (just the wheel check: fast)
        paths = [os.path.join(FLEET, n + ".blueprint.json") for n in names] if names else sorted(glob.glob(os.path.join(FLEET, "*.blueprint.json")))
        bad = 0
        for p in paths:
            c = wheel_clash(p)
            bad += bool(c)
            if c:
                print("%-22s WHEELS CLASH  %s" % (os.path.basename(p)[:-15], ", ".join("%s/%s(%d)" % (x[0], x[1], x[2]) for x in c[:6])), flush=True)
        print("%d of %d clear" % (len(paths) - bad, len(paths)))
        sys.exit(1 if bad else 0)
    paths = [os.path.join(FLEET, n + ".blueprint.json") for n in names] if names else sorted(glob.glob(os.path.join(FLEET, "*.blueprint.json")))
    dirs = v.fib_dirs(600)
    bad = 0
    for p in paths:
        name = os.path.basename(p).replace(".blueprint.json", "")
        ext, inn = seal(p, dirs)
        with contextlib.redirect_stdout(io.StringIO()):
            tubes = v.tube_test(p)
            cross = v.crossing_test(p)
        clash = wheel_clash(p)
        ok = not (ext or inn or tubes or cross or clash)
        bad += not ok
        print("%-22s %s   exterior %s  interior %s  tubes seen %d  crossings %d  wheel clashes %d %s" % (
            name, "PASS" if ok else "FAIL", "sealed" if not ext else "%d out" % ext, "sealed" if not inn else "%d out" % inn, tubes, cross,
            len(clash), ", ".join("%s(%d)" % (c[0], c[2]) for c in clash[:4])), flush=True)
    print("%d of %d pass" % (len(paths) - bad, len(paths)))
    sys.exit(1 if bad else 0)




# ---------------------------------------------------------------- wheels: no tyre may pass through the body
PLATFORMS = os.path.join(HERE, "..", "godot_project", "remake", "vehicles", "chassis", "platforms.json")
WHEEL_OK = {"wheel_well", "underpan", "wheel", "frame_shown"}      # (the wells are round the tyres by design)


def wheel_clash(path, margin=0.02, steer_deg=35.0):
    """Points of the body inside a tyre's swept volume (a front wheel turned through its lock): [(component, n)]."""
    import json as _j
    bp, by = v.load_body(path)
    if bp.get("board", "none") == "none":
        return []
    boards = {b["id"]: b for b in _j.load(open(PLATFORMS))["boards"]}
    B = boards[bp["board"]]
    r, track = B["wheel_r"], B["track_m"]
    wm = [m for m in B["modules"] if m["id"].startswith("wheel_")]
    w = (0.32 if r >= 0.35 else 0.24) if B.get("family") == "steward" else (wm[0]["size"][0] if wm else 0.2)
    out = []
    for role, items in by.items():
        if role in WHEEL_OK:
            continue
        for mid, tris in items:
            pts = tris.reshape(-1, 3)
            cen = tris.mean(axis=1)
            mids = (tris[:, [0, 1, 2]] + tris[:, [1, 2, 0]]) / 2
            P = np.concatenate([pts, cen, mids.reshape(-1, 3)])
            hits = 0
            for a in B["axles"]:
                zc = -a["y"]                                  # (Godot z of the axle)
                for sx in (1, -1):
                    cx = sx * track / 2
                    angs = np.radians(np.linspace(-steer_deg, steer_deg, 7)) if a.get("steer") else [0.0]
                    for ang in angs:
                        d = P - np.array([cx, r, zc])
                        ca, sa = math.cos(ang), math.sin(ang)
                        ax = d[:, 0] * ca - d[:, 2] * sa       # (across the tyre: along its axle)
                        az = d[:, 0] * sa + d[:, 2] * ca
                        rad = np.sqrt(d[:, 1] ** 2 + az ** 2)
                        hits += int(np.sum((np.abs(ax) < w / 2 + margin) & (rad < r + margin)))
            if hits:
                out.append((mid, role, hits))
    return out


if __name__ == "__main__":
    main()
