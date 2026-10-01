#!/usr/bin/env python3
"""Measure an asset's Grok reference views for the Blender builders (runs in ~/.venvs/ssc-assets).

    ~/.venvs/ssc-assets/bin/python tools/assets/analyze.py <id> [<id>...] [--debug]

For each view in reference/grok/<id>/: key out the flat grey background -> the silhouette mask;
its bounding box; the outline as a polygon in metres (model frame: X right, Y forward, Z up; the
vehicle's real size from npc_vehicles.json sets the scale); on the side view the wheels (Hough
circles kept only where they sit inside the silhouette at its bottom); the main colours. Then one
texture atlas per asset (side on top, front / rear / top below) with the background bled out so
seams never show grey, and the pixel -> atlas UV mapping for each view.

Writes reference/grok/<id>/analysis.json and atlas.jpg (and debug overlays with --debug).
"""
import argparse
import json
import math
import os

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF = os.path.join(ROOT, "reference", "grok")
VEH = json.load(open(os.path.join(ROOT, "godot_project", "remake", "characters", "npc_vehicles.json")))["vehicles"]
VIEWS = ["side", "front", "rear", "top", "three_quarter"]
SIZE_OVERRIDE = {"passenger_train": [25.0, 3.0, 4.2]}      # the reference is one car of the set
NO_WHEELS = {"lobster_boat", "trawler", "fishing_skiff", "rowboat_dinghy", "canoe_kayak", "sailboat", "pontoon_boat", "cabin_cruiser",
             "personal_watercraft", "ferry", "workboat_tug", "barge", "pedal_boat", "coast_guard_boat", "rescue_board", "cargo_aerostat",
             "rescue_aerostat", "passenger_shuttle", "supply_freighter", "cargo_mule", "eva_sled", "spoke_elevator_car"}
# drawn facing left (front to the image's left): the side and top views are mirrored before measuring
FLIP = {"semi_trailer_reefer", "hearse", "limousine", "utility_trailer", "boat_trailer", "manual_wheelchair", "baby_stroller", "hay_baler", "plough_disc",
        "livestock_trailer", "kiddie_train"}
import sys as _sys
_sys.path.insert(0, os.path.dirname(__file__))
import catalog


def silhouette(img):
    h, w = img.shape[:2]
    border = np.concatenate([img[:8].reshape(-1, 3), img[-8:].reshape(-1, 3), img[:, :8].reshape(-1, 3), img[:, -8:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    spread = np.percentile(np.linalg.norm(border.astype(float) - bg, axis=1), 99)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(float)
    bg_lab = cv2.cvtColor(bg.reshape(1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(float)[0, 0]
    d = np.linalg.norm(lab - bg_lab, axis=2)
    thr = max(10.0, spread * 0.9 + 5)
    m = (d > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    # a drawn ground line or shadow streak (thin and horizontal) is not the object: it would set the
    # ground and the length wrong
    thin = m & ~cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((6, 1), np.uint8))
    rows = thin.sum(axis=1)
    for y in np.nonzero(rows > m.shape[1] * 0.05)[0]:
        m[y][thin[y] > 0] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab_img, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    big = max(stats[1:, cv2.CC_STAT_AREA]) if n > 1 else 0
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= max(150, big * 0.004):
            keep[lab_img == i] = 1
    # fill holes (the background seen through windows stays: only enclosed specks are filled)
    filled = keep.copy()
    cnts, hier = cv2.findContours(keep, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is not None:
        for i, c in enumerate(cnts):
            if hier[0][i][3] >= 0 and cv2.contourArea(c) < big * 0.02:
                cv2.drawContours(filled, [c], -1, 1, -1)
    return filled, bg


def bbox(m):
    ys, xs = np.nonzero(m)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def wheels(img, m, bb, length_px):
    """Wheels stand on the ground: find where the silhouette touches its lowest line (one contact
    patch per wheel), then the best circle standing on each patch (Hough, loosely), checked to lie
    inside the silhouette; a patch with no circle gets a radius from the dark tyre band above it."""
    x0, y0, x1, y1 = bb
    hgt = y1 - y0
    H, Wd = m.shape
    low = np.full(Wd, -1)
    cols = np.nonzero(m.any(axis=0))[0]
    for x in cols:
        low[x] = np.nonzero(m[:, x])[0].max()
    ground = low.max()
    touch = (low >= ground - max(3, hgt * 0.012))
    runs, start = [], None
    for x in range(Wd + 1):
        t = x < Wd and touch[x]
        if t and start is None:
            start = x
        if not t and start is not None:
            if x - start >= 2:
                runs.append((start, x - 1))
            start = None
    # merge runs closer than a few px (a tread pattern breaks contact)
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] < max(3, hgt * 0.008):
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    rmin, rmax = max(5, int(hgt * 0.05)), max(10, int(min(hgt * 0.6, length_px * 0.25)))
    out = []
    for a, b in merged:
        cx_run = (a + b) / 2
        if b - a > hgt * 0.9:          # a flat bottom (a skirt, a hull), not a tyre
            continue
        # the tyre's lower arc is the silhouette's bottom edge: fit a circle to it (Kasa), widening
        # the window to ~0.75 r as the estimate grows
        half = max(4.0, (b - a) / 2 + 2)
        fit = None
        for _ in range(6):
            xs = np.arange(int(cx_run - half), int(cx_run + half) + 1)
            xs = xs[(xs >= 0) & (xs < Wd)]
            xs = xs[low[xs] >= 0]
            if len(xs) < 5:
                break
            ys = low[xs].astype(float)
            A = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]
            bb_ = xs ** 2 + ys ** 2
            c, *_ = np.linalg.lstsq(A, bb_, rcond=None)
            cx, cy = c[0], c[1]
            r = math.sqrt(max(1.0, c[2] + cx * cx + cy * cy))
            if not (rmin <= r <= rmax):
                break
            fit = (float(cx), float(cy), float(r))
            new_half = 0.75 * r
            if abs(new_half - half) < 1:
                break
            half = new_half
        if fit is None:
            continue
        out.append([fit[0], fit[1], fit[2], 0.0])
    # the wheels of one axle line share a radius when they are close (cars, trucks): snap near-equal radii
    if len(out) >= 2:
        rs = sorted(w[2] for w in out)
        med = rs[len(rs) // 2]
        for w in out:
            if abs(w[2] - med) < 0.15 * med:
                w[1] = ground - med
                w[2] = med
    return out


def main_line(ws, Hh):
    """The windows along the main window line (as kit.cabin uses them): bottoms near the median, in the
    upper body, big enough."""
    ws = [w for w in ws if w[1] - w[0] > 0.15 and w[3] - w[2] > 0.12 and w[2] > Hh * 0.3]
    if not ws:
        return []
    z0s = sorted(w[2] for w in ws)
    med = z0s[len(z0s) // 2]
    return [w for w in ws if abs(w[2] - med) < 0.35]


def car_windows(img, m, bb, s, sz, bg, L, Hh):
    """Cars, trucks and cabs: of several glass tests, the set with the most glass along the main line."""
    sets = [windows(img, m, bb, s, sz, bg, L, Hh, t, long_) for t in (18, 12) for long_ in (False, True)]
    sets.append(windows(img, m, bb, s, sz, bg, L, Hh))
    return max(sets, key=lambda ws: sum((w[1] - w[0]) * (w[3] - w[2]) for w in main_line(ws, Hh)))


def windows(img, m, bb, s, sz, bg, L, Hh, tight=0, long_=False):
    """Glazing on a side view (transit): pale, low-chroma regions inside the silhouette, close to the
    background tone, in the upper body -- rectangles in metres (y0, y1, z0, z1)."""
    x0, y0, x1, y1 = bb
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(float)
    bg_lab = cv2.cvtColor(np.array(bg, np.uint8).reshape(1, 1, 3), cv2.COLOR_BGR2LAB).astype(float)[0, 0]
    chroma = np.hypot(lab[..., 1] - 128, lab[..., 2] - 128)
    if tight:       # (cars and trucks: white or cream paint is as pale as glass; glass keeps the background's tone)
        glass = ((np.abs(lab[..., 0] - bg_lab[0]) < tight) & (chroma < 12)).astype(np.uint8)
    else:
        glass = ((np.linalg.norm(lab - bg_lab, axis=2) < 32) & (chroma < 14) & (lab[..., 0] > 120)).astype(np.uint8)
    inner = cv2.erode(m, np.ones((5, 5), np.uint8))
    glass &= inner
    hgt = y1 - y0
    glass[: int(y0 + hgt * 0.04)] = 0
    glass[int(y0 + hgt * 0.72):] = 0
    glass = cv2.morphologyEx(glass, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    glass = cv2.morphologyEx(glass, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, labs, st, _ = cv2.connectedComponentsWithStats(glass, 8)
    out = []
    area_min = (x1 - x0) * hgt * 0.0015
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < area_min or w < 6 or h < 6 or a < 0.55 * w * h:
            continue
        cx = (x0 + x1) / 2
        if w * s > (0.6 if long_ else 0.3) * L or h * sz > 0.45 * Hh:    # pale paint, not glass (a car's glass can run long)
            continue
        out.append([(x - cx) * s, (x + w - cx) * s, (y1 - (y + h)) * sz, (y1 - y) * sz])
    out.sort()
    return out


def outline(m, simplify=0.004):
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cnts, key=cv2.contourArea)
    eps = simplify * cv2.arcLength(c, True)
    return cv2.approxPolyDP(c, eps, True)[:, 0, :].astype(float)


def colours(img, m, k=5):
    px = img[m > 0].reshape(-1, 3).astype(np.float32)
    if len(px) > 20000:
        px = px[np.random.default_rng(1).choice(len(px), 20000, replace=False)]
    _, lab, cen = cv2.kmeans(px, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(lab.ravel(), minlength=k)
    order = np.argsort(-counts)
    return [[int(cen[i][2]), int(cen[i][1]), int(cen[i][0]), round(float(counts[i] / counts.sum()), 3)] for i in order]


def bleed(img, m, ring=24):
    """Fill the background near the silhouette with the silhouette's edge colours (so texture seams
    and slightly-off hull edges never show the grey background)."""
    out = img.copy()
    inv = (m == 0).astype(np.uint8)
    near = cv2.dilate(m, np.ones((ring * 2 + 1, ring * 2 + 1), np.uint8)) & inv
    out = cv2.inpaint(out, near, 5, cv2.INPAINT_TELEA)
    return out


def analyse(aid, debug=False):
    d = os.path.join(REF, aid)
    L, W, Hh = SIZE_OVERRIDE.get(aid, VEH[aid]["size_m"])
    family = catalog.ASSETS[aid][0]
    res = {"id": aid, "size_m": [L, W, Hh], "family": family, "views": {},
           "seats": int(VEH[aid].get("seats", 0) or 0), "category": VEH[aid].get("category", "")}
    imgs = {}
    for v in VIEWS:
        p = os.path.join(d, v + ".jpg")
        if not os.path.exists(p):
            continue
        img = cv2.imread(p)
        if aid in FLIP and v in ("side", "top"):
            img = cv2.flip(img, 1)
        m, bg = silhouette(img)
        if family != "frame":
            # a solid body: everything inside its outline is body (a white box on a pale ground keys out
            # in pieces, so bridge the gaps first)
            x0, y0, x1, y1 = bbox(m)
            k = max(9, int(max(x1 - x0, y1 - y0) * 0.03)) | 1
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
            # inside = silhouette above, below, left and right (a pale panel's outline with gaps still
            # fills; the open space under the body between wheels has nothing below it and stays open)
            b = m > 0
            up, down = np.maximum.accumulate(b, 0), np.maximum.accumulate(b[::-1], 0)[::-1]
            lf, rt = np.maximum.accumulate(b, 1), np.maximum.accumulate(b[:, ::-1], 1)[:, ::-1]
            m = (b | (up & down & lf & rt)).astype(np.uint8)
            cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            m = np.zeros_like(m)
            cv2.drawContours(m, cnts, -1, 1, -1)
        bb = bbox(m)
        x0, y0, x1, y1 = bb
        wpx, hpx = x1 - x0 + 1, y1 - y0 + 1
        info = {"file": p, "w": img.shape[1], "h": img.shape[0], "bbox": bb, "bg": [int(c) for c in bg[::-1]]}
        if v == "side":
            s = L / wpx
            no_wheels = aid in NO_WHEELS
            # a drawing whose height disagrees with the real size by >15% is stretched to it
            sz = s if abs(hpx * s / Hh - 1) <= 0.15 else Hh / hpx
            info["scale_y"], info["scale_z"] = s, sz
            wl = [] if no_wheels else wheels(img, m, bb, wpx)
            info["wheels_px"] = wl
            info["wheels_m"] = [[(cx - (x0 + x1) / 2) * s, (y1 - cy) * sz, r * sz] for cx, cy, r, _ in wl]
            body = m.copy()
            for cx, cy, r, _ in wl:
                cv2.circle(body, (int(cx), int(cy)), int(r * 1.03), 0, -1)
            poly = outline(body if body.sum() > m.sum() * 0.5 else m)
            info["outline_m"] = [[(px - (x0 + x1) / 2) * s, (y1 - py) * sz] for px, py in poly]          # (Y, Z)
            info["height_m"] = hpx * sz
            info["drawn_height_m"] = hpx * s
            if family == "transit":
                info["windows_m"] = windows(img, m, bb, s, sz, bg, L, Hh)
            elif family == "hull":
                info["windows_m"] = car_windows(img, m, bb, s, sz, bg, L, Hh)
        elif v in ("front", "rear"):
            s = W / wpx
            side_h = res["views"].get("side", {}).get("height_m", Hh)
            sz = s if abs(hpx * s / side_h - 1) <= 0.15 else side_h / hpx
            info["scale_y"], info["scale_z"] = s, sz
            # symmetric: average the left and right half-widths at each height
            poly = outline(m)
            sign = -1 if v == "front" else 1                                    # front: the viewer's right is the vehicle's left (-X)
            info["outline_m"] = [[sign * (px - (x0 + x1) / 2) * s, (y1 - py) * sz] for px, py in poly]   # (X, Z)
            info["height_m"] = hpx * sz
            rows = []
            for k in range(41):
                yy = int(y1 - (hpx - 1) * k / 40)
                xs = np.nonzero(m[yy])[0]
                rows.append([(y1 - yy) * sz, ((xs.max() - xs.min() + 1) * s / 2) if len(xs) else 0.0])
            info["halfwidth_by_z"] = rows
        elif v == "top":
            s = L / wpx
            info["scale_y"], info["scale_z"] = s, s
            poly = outline(m)
            info["outline_m"] = [[(py - (y0 + y1) / 2) * s, (px - (x0 + x1) / 2) * s] for px, py in poly]   # (X, Y): image up = -X
        else:
            s = None
        info["scale"] = s
        info["colours"] = colours(img, m)
        res["views"][v] = info
        if family == "frame":
            rgba = np.dstack([img, (cv2.GaussianBlur(m.astype(np.float32), (3, 3), 0.8) * 255).astype(np.uint8)])
            imgs[v] = (rgba, bb)
        else:
            imgs[v] = (bleed(img, m) if v != "three_quarter" else img, bb)
        if debug:
            dbg = img.copy()
            dbg[m == 0] = (dbg[m == 0] * 0.4).astype(np.uint8)
            for cx, cy, r, _ in info.get("wheels_px", []):
                cv2.circle(dbg, (int(cx), int(cy)), int(r), (0, 0, 255), 2)
            cv2.imwrite(os.path.join(d, "_dbg_%s.jpg" % v), dbg)
    # the atlas: side across the top, then front / rear / top in a row (each crop padded 4%)
    A = 2048 if L > 8 else 1024
    atlas = np.zeros((A, A, 4), np.uint8) if family == "frame" else np.full((A, A, 3), 128, np.uint8)
    rects = {}

    def place(v, X, Y, Wd, Ht):
        img, (x0, y0, x1, y1) = imgs[v]
        pad = int(0.04 * max(x1 - x0, y1 - y0))
        cx0, cy0 = max(0, x0 - pad), max(0, y0 - pad)
        cx1, cy1 = min(img.shape[1], x1 + pad + 1), min(img.shape[0], y1 + pad + 1)
        crop = img[cy0:cy1, cx0:cx1]
        k = min(Wd / crop.shape[1], Ht / crop.shape[0])
        tw, th = max(1, int(crop.shape[1] * k)), max(1, int(crop.shape[0] * k))
        atlas[Y:Y + th, X:X + tw] = cv2.resize(crop, (tw, th), interpolation=cv2.INTER_AREA)
        # px (in the original image) -> atlas uv: u = (px - cx0) * k + X, v from the top
        rects[v] = {"crop": [cx0, cy0, cx1, cy1], "k": k, "X": X, "Y": Y, "atlas": A}
    if "side" in imgs:
        place("side", 0, 0, A, A // 2)
    others = [v for v in ("front", "rear", "top") if v in imgs]
    for i, v in enumerate(others):
        cw = A // max(3, len(others))
        place(v, i * cw, A // 2 + 4, cw - 4, A // 2 - 8)
    if family == "frame":
        cv2.imwrite(os.path.join(d, "atlas.png"), atlas)
        res["atlas"] = {"file": os.path.join(d, "atlas.png"), "size": A, "rects": rects, "alpha": True}
    else:
        cv2.imwrite(os.path.join(d, "atlas.jpg"), atlas, [cv2.IMWRITE_JPEG_QUALITY, 88])
        res["atlas"] = {"file": os.path.join(d, "atlas.jpg"), "size": A, "rects": rects}
    json.dump(res, open(os.path.join(d, "analysis.json"), "w"), indent=1)
    sv = res["views"].get("side", {})
    return "%-22s side %s wheels %d  h %.2f m (spec %.2f)" % (aid, "ok" if sv else "MISSING", len(sv.get("wheels_m", [])), sv.get("height_m", 0), Hh)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    for i in a.ids:
        try:
            print(analyse(i, a.debug))
        except Exception as e:
            print("%-22s ERROR %s" % (i, e))
