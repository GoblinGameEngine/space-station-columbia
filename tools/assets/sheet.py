#!/usr/bin/env python3
"""Contact sheets for review: an asset's reference views (and renders, if any) tiled in one image.

    python3 tools/assets/sheet.py <id> [<id>...] [--renders] [-o out.png]

Each tile is labelled with the asset id and view. Several ids make one sheet (rows of assets).
"""
import argparse
import os

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF = os.path.join(ROOT, "reference", "grok")
ORDER = ["side", "front", "rear", "top", "three_quarter"]


def tiles(aid, renders):
    d = os.path.join(REF, aid)
    out = []
    for v in ORDER:
        p = os.path.join(d, v + ".jpg")
        if os.path.exists(p):
            out.append((v, p))
    if renders:
        b = os.path.join(d, "build")
        for v in ("r_side_overlay", "r_34", "r_front", "r_rear"):
            p = os.path.join(b, v + ".png")
            if os.path.exists(p):
                out.append((v, p))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--renders", action="store_true")
    ap.add_argument("-o", default=None)
    ap.add_argument("--tile", type=int, default=300)
    a = ap.parse_args()
    rows = [(i, tiles(i, a.renders)) for i in a.ids]
    cols = max(len(t) for _, t in rows) if rows else 1
    T = a.tile
    sheet = Image.new("RGB", (cols * T, len(rows) * (T * 3 // 4 + 16)), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    for r, (aid, ts) in enumerate(rows):
        for c, (v, p) in enumerate(ts):
            im = Image.open(p).convert("RGB")
            im.thumbnail((T - 4, T * 3 // 4 - 4))
            x, y = c * T + 2, r * (T * 3 // 4 + 16) + 14
            sheet.paste(im, (x, y))
            dr.text((x, y - 13), "%s / %s" % (aid, v), fill=(0, 0, 0))
    out = a.o or os.path.join(REF, "_sheet_%s.png" % ("_".join(a.ids)[:60]))
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
