#!/usr/bin/env python3
"""fleet_test.py -- the body tests (tools/vehicle_seal_test.py) over every fleet blueprint, one line each:
both shells sealed round the cabin, no frame tube in view from outside, nothing drawn across an opening.

    ~/.venvs/ssc-assets/bin/python tools/fleet_test.py [type ...]      # default: every godot_project/remake/vehicles/fleet/*.blueprint.json

Exit status 1 if any vehicle fails. Details for one: the seal test itself (TUBES=1 / CROSS=1 for the others).
"""
import contextlib
import json
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
    if "--view" in sys.argv:                               # (the driver's forward view: fast)
        paths = [os.path.join(FLEET, n + ".blueprint.json") for n in names] if names else sorted(glob.glob(os.path.join(FLEET, "*.blueprint.json")))
        bad = 0
        for p in paths:
            r = forward_view(p)
            if r is None:
                print("%-24s no driver's seat" % os.path.basename(p)[:-15], flush=True)
                continue
            ok = r[0] >= VIEW_ALL and r[1] >= VIEW_CORE
            bad += not ok
            print("%-24s %s  forward view clear %3.0f %%, ahead %3.0f %%  (eye %s)" % (os.path.basename(p)[:-15], "ok  " if ok else "POOR",
                  r[0] * 100, r[1] * 100, r[2]), flush=True)
        print("%d of %d clear" % (len(paths) - bad, len(paths)))
        sys.exit(1 if bad else 0)
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




# ---------------------------------------------------------------- the driver's forward view (the user, 2026-10-05: "a usable,
# largely unobstructed forward view from the driver's seat")
VIEW_ALL, VIEW_CORE = 0.70, 0.90      # clear shares needed: across the whole fan (side pillars count), and straight ahead
EYE = 0.72                            # m from the seat marker (the H-point) up to the eye (RemakeAirVehicle.seat_eye)
REGISTRY = os.path.join(FLEET, "fleet_bodies.json")


def forward_view(path):
    """From the driver's eye: a fan of rays ahead -- 40 deg either side, 6 deg down to 10 up -- against everything opaque
    (glass is clear) out to 8 m. (clear share of the fan, clear share of the core: 20 deg either side, 3 down to 6 up)."""
    bp, by = v.load_body(path)
    eye = None
    for nm, loc, *_ in bp.get("markers", []):
        if nm == "seat_driver":
            eye = np.array(loc, np.float32)
    if eye is None:
        t = os.path.basename(path)[:-15]
        info = json.load(open(REGISTRY))["types"].get(t, {})
        if info.get("seat"):
            eye = np.array(info["seat"], np.float32)
    if eye is None:
        return None
    eye = eye + np.array([0, EYE, 0], np.float32)
    opaque = set(by) - {"glazing", "door_glass", "hatch_glass", "ramp"}
    tri = v.gather(by, opaque)
    dirs, core = [], []
    for el in np.linspace(-6, 10, 9):
        for az in np.linspace(-40, 40, 21):
            e, a = math.radians(el), math.radians(az)
            dirs.append([math.sin(a) * math.cos(e), math.sin(e), -math.cos(a) * math.cos(e)])
            core.append(abs(az) <= 20 and -3 <= el <= 6)
    dirs = np.array(dirs, np.float32)
    hit = v.first_hit(eye, dirs, tri)
    clear = ~(hit < 8.0)
    core = np.array(core)
    return float(clear.mean()), float(clear[core].mean()), [round(float(c), 2) for c in eye]


if __name__ == "__main__":
    main()
