#!/usr/bin/env python3
"""The road surface a car meets on each crossing model: rays straight down onto the model's
collision mesh (its *_collision-colonly node) along its road -- the middle of its width, and
CAR_HW either side -- from one end of its footprint to the other.  Reports the highest rise
between neighbouring samples (a step a car can't take) and the surface at each end.

    python3 remake/tools/crossing_profile.py [MODEL ...]      (default: every crossing in placement.json)

glTF axes: y up, the road along z (Blender's +Y is glTF -Z).
"""
import json
import os
import struct
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BLD = os.path.join(ROOT, "godot_project", "remake", "buildings")
STEP = 0.25
CAR_HW = 0.8


def collision_tris(path):
    d = open(path, "rb").read()
    n = struct.unpack("<I", d[12:16])[0]
    j = json.loads(d[20:20 + n])
    off = 20 + n
    bl = struct.unpack("<I", d[off:off + 4])[0]
    bin_ = d[off + 8:off + 8 + bl]

    def acc(i):
        a = j["accessors"][i]
        bv = j["bufferViews"][a["bufferView"]]
        comp = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8}[a["componentType"]]
        ncomp = {"SCALAR": 1, "VEC3": 3, "VEC2": 2, "VEC4": 4}[a["type"]]
        start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        arr = np.frombuffer(bin_, comp, a["count"] * ncomp, start)
        return arr.reshape(-1, ncomp) if ncomp > 1 else arr
    tris = []
    for node in j["nodes"]:
        if "mesh" not in node or "col" not in node["name"].lower():
            continue
        for p in j["meshes"][node["mesh"]]["primitives"]:
            v = acc(p["attributes"]["POSITION"]).astype(np.float64)
            if "translation" in node:
                v = v + np.array(node["translation"])
            idx = acc(p["indices"]).astype(np.int64).reshape(-1, 3) if "indices" in p else np.arange(len(v)).reshape(-1, 3)
            tris.append(v[idx])
    return np.concatenate(tris) if tris else np.zeros((0, 3, 3))


def surface(tris, x, z, top=3.0):
    """The highest collision surface under (x, z) no higher than top, or None."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    # barycentric in the xz plane
    v0 = c[:, [0, 2]] - a[:, [0, 2]]
    v1 = b[:, [0, 2]] - a[:, [0, 2]]
    v2 = np.array([x, z]) - a[:, [0, 2]]
    d00 = (v0 * v0).sum(1)
    d01 = (v0 * v1).sum(1)
    d11 = (v1 * v1).sum(1)
    d20 = (v2 * v0).sum(1)
    d21 = (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    ok = np.abs(den) > 1e-12
    u = np.where(ok, (d11 * d20 - d01 * d21) / np.where(ok, den, 1), -1)
    v = np.where(ok, (d00 * d21 - d01 * d20) / np.where(ok, den, 1), -1)
    inside = ok & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6)
    y = a[:, 1] + u * (c[:, 1] - a[:, 1]) + v * (b[:, 1] - a[:, 1])
    y = y[inside & (y <= top)]
    return float(y.max()) if len(y) else None


def profile(model, zmin, zmax, xc=0.0):
    tris = collision_tris(os.path.join(BLD, model + ".glb"))
    rows = []
    z = zmin
    while z <= zmax + 1e-6:
        hs = [surface(tris, xc + dx, z) for dx in (-CAR_HW, 0.0, CAR_HW)]
        rows.append((round(z, 2), [None if h is None else round(h, 2) for h in hs]))
        z += STEP
    return rows


def main(models):
    pl = json.load(open(os.path.join(ROOT, "godot_project", "remake", "placement.json")))["structures"]
    seen = {}
    for e in pl:
        if e["kind"] == "crossing" and (not models or e["model"] in models) and e["model"] not in seen:
            seen[e["model"]] = e
    bad = 0
    for m, e in sorted(seen.items()):
        # glTF z is minus the footprint's local z (Godot's -z is the model's +Y road direction)
        rows = profile(m, -e["fmax"][1], -e["fmin"][1], xc=(e["fmin"][0] + e["fmax"][0]) * 0.5)
        worst = 0.0
        where = None
        prev = None
        for z, hs in rows:
            h = max([v for v in hs if v is not None], default=None)
            if h is not None and prev is not None and h - prev > worst:
                worst, where = h - prev, z
            if h is not None:
                prev = h
        ends = (rows[0][1][1], rows[-1][1][1])
        flag = "STEP" if worst > 0.2 else "ok"
        bad += flag != "ok"
        print(f"{m:12s} {flag:4s} worst rise {worst:.2f} m at z {where}, ends {ends}, top {max((max([v for v in hs if v is not None], default=-9) for _, hs in rows)):.2f}")
    print(f"{len(seen)} models, {bad} with a step")


if __name__ == "__main__":
    main(sys.argv[1:])
