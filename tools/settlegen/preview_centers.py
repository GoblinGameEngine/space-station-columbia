#!/usr/bin/env python3
"""preview_centers.py OUT.png -- draw generated plans (tools/settlegen/centers.py) for review: strip centres of
each kind, a lifestyle centre, industrial parks of each era. 1 px = 0.5 m. The road is at the bottom of each panel."""
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import centers as C
from PIL import Image, ImageDraw

AREA = {"parking": (205, 205, 205), "lot": (185, 182, 175), "plaza": (232, 226, 212), "lawn": (196, 224, 176),
        "pool": (120, 180, 220), "park": (160, 210, 140)}
BLD = {"bigbox": (192, 96, 58), "strip": (210, 130, 90), "restaurant": (200, 90, 60), "store": (165, 70, 58),
       "industrial": (95, 95, 95), "warehouse": (110, 120, 132), "shed": (140, 140, 122)}


def draw(plan, site, label, scale=0.5):
    W, H = int(site.w / scale) + 20, int(site.d / scale) + 40
    im = Image.new("RGB", (W, H), (236, 240, 228))
    dr = ImageDraw.Draw(im)
    T = lambda u, v: (10 + (u - site.u0) / scale, H - 30 - (v - site.v0) / scale)            # noqa: E731
    dr.rectangle([0, H - 30, W, H], fill=(90, 90, 90))                                         # (the frontage road)
    for a in plan["areas"]:
        dr.polygon([T(*p) for p in a["poly"]], fill=AREA[a["kind"]])
    for ln in plan["lines"]:
        dr.line([T(*p) for p in ln["pts"]], fill=(250, 250, 250) if ln["cls"] == "street" else (150, 150, 150),
                width=int(12 / scale / 2) if ln["cls"] == "street" else 3)
    for b in plan["buildings"]:
        dr.polygon([T(*p) for p in b["poly"]], fill=BLD[b["kind"]], outline=(40, 30, 25))
        if b["role"] in ("anchor", "junior", "pad", "manufacturing", "warehouse", "bulk_distribution", "flex", "truck_terminal"):
            xs = [T(*p) for p in b["poly"]]
            cx, cy = sum(x for x, _ in xs) / 4, sum(y for _, y in xs) / 4
            dr.text((cx - 30, cy - 5), b["tenant"][:18], fill=(255, 255, 255))
    dr.text((8, 6), label + "  " + " ".join("%s=%s" % kv for kv in plan["stats"].items() if k_ok(kv[0])), fill=(0, 0, 0))
    return im


def k_ok(k):
    return k in ("type", "form", "gla_sqft", "stalls_per_1000", "pads", "coverage", "site_acres", "era", "built_sqft")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "centers_preview.png"
    panels = []
    for kind, (w, d), sr in (("convenience", (90, 70), None), ("neighborhood", (260, 190), "u1"), ("community", (420, 260), "u0"),
                             ("power", (520, 330), None)):
        s = C.Site(0, w, 0, d, sr)
        panels.append(draw(C.strip_center(s, kind, random.Random(7)), s, kind))
    s = C.Site(0, 300, 0, 330)
    panels.append(draw(C.lifestyle_center(s, random.Random(3)), s, "lifestyle"))
    for era in ("rail", "postwar", "logistics"):
        s = C.Site(0, 520, 0, 620)
        panels.append(draw(C.industrial_park(s, era, random.Random(11)), s, "industrial " + era, scale=0.8))
    Wt = max(p.width for p in panels)
    rows, row, x = [], [], 0
    for p in panels:
        if x + p.width > 2400 and row:
            rows.append(row); row, x = [], 0
        row.append(p); x += p.width + 10
    rows.append(row)
    Ht = sum(max(p.height for p in r) + 10 for r in rows)
    S = Image.new("RGB", (2400, Ht), (255, 255, 255))
    y = 0
    for r in rows:
        x = 0
        for p in r:
            S.paste(p, (x, y)); x += p.width + 10
        y += max(p.height for p in r) + 10
    S.save(out)
    print(out, S.size)


if __name__ == "__main__":
    main()
