#!/usr/bin/env python3
"""Compare gait curves: rotoscoped references (roto_walk.py *_cycle.json) against the game's own walk
(npc_walk_measure.gd) -- per feature, the peak-to-peak range and the shape correlation with the
reference mean.  Lateral features are mirrored as needed (the reference's image x is the figure's
right; our +x is the figure's left).

    python3 tools/charref/walk_compare.py ours.json ref1_cycle.json [ref2_cycle.json ...]
"""
import json
import math
import sys

FEATS = ["bob", "head_fwd", "head_lat", "chest_lat", "sh_tilt", "sh_width"]
# the reference's image x grows to the figure's LEFT (they face the camera); the game's +x is the
# figure's RIGHT (the left foot is at -x) -- so lateral curves are mirrored for comparison
FLIP = {"head_lat": -1, "chest_lat": -1}


def curve(d, k):
    c = d["curves"].get(k)
    if c is None:
        return None
    # fill gaps by neighbours
    n = len(c)
    out = list(c)
    for i in range(n):
        if out[i] is None:
            a = next((out[(i - j) % n] for j in range(1, n) if c[(i - j) % n] is not None), 0.0)
            b = next((out[(i + j) % n] for j in range(1, n) if c[(i + j) % n] is not None), 0.0)
            out[i] = (a + b) / 2
    return out


def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) or 1.0
    return num / den


def main():
    ours = json.load(open(sys.argv[1]))
    refs = [json.load(open(p)) for p in sys.argv[2:]]
    for k in FEATS:
        o = curve(ours, k)
        rs = [curve(r, k) for r in refs]
        rs = [r for r in rs if r]
        if not o or not rs:
            continue
        o = [v * FLIP.get(k, 1) for v in o]
        ref = [sum(v) / len(v) for v in zip(*rs)]
        scale = 1.0 if k == "sh_tilt" else 1000.0
        unit = "deg" if k == "sh_tilt" else "/1000 H"
        pr = max(ref) - min(ref)
        po = max(o) - min(o)
        print("%-10s ref p-p %6.1f  ours %6.1f %-8s ratio %.2f  shape r=%+.2f" % (
            k, pr * scale, po * scale, unit, po / pr if pr else 0, corr(o, ref)))
        print("   ref  " + " ".join("%+5.1f" % (v * scale) for v in ref))
        print("   ours " + " ".join("%+5.1f" % (v * scale) for v in o))


if __name__ == "__main__":
    main()
