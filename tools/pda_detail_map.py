#!/usr/bin/env python3
"""The PDA's detailed map: 4 m / px, four greys, over the whole ring (s across from 0, x down from -HALF_LEN), cut
into TILE px squares (godot_project/ui/pda/detail/d_I_J.png -- the 20 km ring whole would be 15,708 px wide, past
what small GPUs take; PdaMapTiles draws them), and the Station Map's overview (ui/pda/map_overview.png, OVER_W px
wide).  Drawn from the map data, not the far-side picture, so it stays crisp on the LCD:

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

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.join(os.path.dirname(__file__), "..", "godot_project")
GD = os.path.join(ROOT, "remake")
OUT = os.path.join(ROOT, "ui", "pda", "detail")
M = 4.0                                       # m per pixel
TILE = 2048                                   # px per tile side (scripts/ui/PdaMapTiles.gd)
OVER_W = 228


def main():
    ter = json.load(open(os.path.join(GD, "terrain.json")))
    rs = ter["raster"]
    nx, ny, x0, step = rs["nx"], rs["ny"], rs["x0"], rs["step_m"]
    C = 2 * math.pi * ter["R"]
    HW = ter["W"] / 2
    W_PX, H_PX = math.ceil(C / M), math.ceil(ter["W"] / M)
    lvl = np.frombuffer(gzip.open(os.path.join(GD, rs["level"])).read(), np.float16).reshape(ny, nx)
    lc = np.asarray(Image.open(os.path.join(GD, "landcover.png")))[..., 0]
    lc_step = ter.get("landcover_step_m", step)
    # each map pixel's raster cells (the rasters are coarser than the map: nearest)
    ci = np.minimum((np.arange(W_PX) * M / step).astype(np.int64), nx - 1)
    rj = np.clip(((np.arange(H_PX) * M - HW - x0) / step).astype(np.int64), 0, ny - 1)
    lci = np.minimum((np.arange(W_PX) * M / lc_step).astype(np.int64), lc.shape[1] - 1)
    lrj = np.clip(((np.arange(H_PX) * M) / lc_step).astype(np.int64), 0, lc.shape[0] - 1)
    out = np.full((H_PX, W_PX), 255, np.uint8)
    for r0 in range(0, H_PX, 512):
        r1 = min(H_PX, r0 + 512)
        cls = lc[lrj[r0:r1]][:, lci]
        wet = lvl[rj[r0:r1]][:, ci].astype(np.float32) > -9000.0
        out[r0:r1] = np.where(wet, 85, np.where(np.isin(cls, (3, 5)), 170, 255))
    img = Image.fromarray(out, "L")
    d = ImageDraw.Draw(img)
    px = lambda s, x: ((s % C) / M, (x + HW) / M)
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
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):                 # (a smaller ring leaves no stale tiles behind)
        if f.startswith("d_") and f.endswith(".png"):
            os.remove(os.path.join(OUT, f))
    n = 0
    for i in range(0, W_PX, TILE):
        for j in range(0, H_PX, TILE):
            img.crop((i, j, min(W_PX, i + TILE), min(H_PX, j + TILE))).save(
                os.path.join(OUT, "d_%d_%d.png" % (i // TILE, j // TILE)), optimize=True)
            n += 1
    # the overview: a 4 m pixel is far below one of its pixels -- the darkest grey that covers a fifth of it
    oh = round(OVER_W * H_PX / W_PX)
    a = np.asarray(img)
    fs, fx = W_PX / OVER_W, H_PX / oh
    ov = np.full((oh, OVER_W), 255, np.uint8)
    for j in range(oh):
        band = a[int(j * fx):max(int(j * fx) + 1, int((j + 1) * fx))]
        for i in range(OVER_W):
            cell = band[:, int(i * fs):max(int(i * fs) + 1, int((i + 1) * fs))]
            for lv in (0, 85, 170):
                if (cell <= lv).mean() > (0.2 if lv else 0.08):
                    ov[j, i] = lv
                    break
    Image.fromarray(ov, "L").save(os.path.join(ROOT, "ui", "pda", "map_overview.png"), optimize=True)
    print("PDA detail map:", (W_PX, H_PX), n, "tiles;", "overview", (OVER_W, oh),
          {lv: round(float((a == lv).mean()), 3) for lv in (0, 85, 170, 255)})


if __name__ == "__main__":
    main()
