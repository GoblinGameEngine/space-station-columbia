#!/usr/bin/env python3
"""The PDA's detailed map (godot_project/ui/pda/map_detail.png): 4 m / px, four greys, in the
far-side frame NavMap and the Station Map read it in (FARSIDE_W x FARSIDE_H = 18,944 x 8,192 m: s
across from 0, x down from -4,096). Drawn from the map data, not the far-side picture, so it stays
crisp on the LCD:

  white   open ground and fields          85  water (rivers, lake, ponds, sea)
  170     woods and groves                  0   roads (their own width) and buildings

    python3 tools/pda_detail_map.py      (after any map, road or placement change)
"""
import gzip
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(__file__), "..", "godot_project")
GD = os.path.join(ROOT, "remake")
M = 4.0                                       # m per pixel
W_PX, H_PX, Y0 = 4736, 2048, -4096.0          # the far-side frame at 4 m / px


def main():
    ter = json.load(open(os.path.join(GD, "terrain.json")))
    rs = ter["raster"]
    nx, ny, x0 = rs["nx"], rs["ny"], rs["x0"]
    C = 2 * math.pi * ter["R"]
    lvl = np.frombuffer(gzip.open(os.path.join(GD, rs["level"])).read(), np.float16).reshape(ny, nx)
    lc = np.asarray(Image.open(os.path.join(GD, "landcover.png")))[..., 0]
    out = np.full((H_PX, W_PX), 255, np.uint8)
    r0 = int((x0 - Y0) / M)                   # the rasters' first row in the frame
    cols = np.arange(W_PX) % nx               # (the frame runs a little past the seam: wrap)
    cls = lc[:, cols]
    grey = np.isin(cls, (3, 5))
    wet = lvl[:, cols].astype(np.float32) > -9000.0
    block = np.where(wet, 85, np.where(grey, 170, 255)).astype(np.uint8)
    out[r0:r0 + ny] = block
    img = Image.fromarray(out, "L")
    d = ImageDraw.Draw(img)
    px = lambda s, x: ((s % C) / M, (x - Y0) / M)
    for rd in ter["roads"]:
        wpx = max(1, int(round(float(rd.get("w", 6)) / M)))
        pts = rd["pts"]
        for a, b in zip(pts, pts[1:]):
            pa, pb = px(*a), px(*b)
            if abs(pa[0] - pb[0]) > W_PX / 2:
                continue                      # (across the seam)
            d.line([pa, pb], fill=0, width=wpx)
    for e in json.load(open(os.path.join(GD, "placement.json")))["structures"]:
        if e["kind"] == "crossing" or "fmin" not in e:
            continue
        c, s_ = math.cos(e["yaw"]), math.sin(e["yaw"])
        poly = [px(e["s"] + lx * s_ - lz * c, e["x"] + lx * c + lz * s_)
                for lx, lz in ((e["fmin"][0], e["fmin"][1]), (e["fmax"][0], e["fmin"][1]), (e["fmax"][0], e["fmax"][1]), (e["fmin"][0], e["fmax"][1]))]
        if max(p[0] for p in poly) - min(p[0] for p in poly) < W_PX / 2:
            d.polygon(poly, fill=0)
    img.save(os.path.join(ROOT, "ui", "pda", "map_detail.png"), optimize=True)
    a = np.asarray(img)
    print("map_detail.png", img.size, {lv: round(float((a == lv).mean()), 3) for lv in (0, 85, 170, 255)})


if __name__ == "__main__":
    main()
