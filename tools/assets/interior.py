#!/usr/bin/env python3
"""Measure a vehicle's interior from Grok's interior views (run in ~/.venvs/ssc-assets):

    ~/.venvs/ssc-assets/bin/python tools/assets/interior.py <ids> [--debug]

  interior_plan   the roof-off plan (front to the right): the seats, found as the colour cluster
                  that makes the most seat-sized blobs, in metres in the model frame (x right,
                  y forward, the side outline's length); a floor patch from the aisle -> floor.jpg
  interior_aisle  the view down the aisle: colours of the seats, floor, walls and ceiling

Writes reference/grok/<id>/interior.json (read by remake/blender/kit/transit.py) and, with
--debug, _dbg_interior.jpg with the seats drawn on the plan.
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import analyze as A

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF = os.path.join(ROOT, "reference", "grok")


def rgb(c):
    return [int(c[2]), int(c[1]), int(c[0])]


def aisle_colours(img):
    """Median colours of fixed regions of a symmetrical view down the aisle."""
    h, w = img.shape[:2]

    def med(x0, x1, y0, y1):
        r = img[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)].reshape(-1, 3)
        return rgb(np.median(r, axis=0))
    return {
        "seat": med(0.02, 0.16, 0.86, 0.98),
        "floor": med(0.45, 0.55, 0.88, 0.99),
        "ceiling": med(0.30, 0.40, 0.01, 0.07),
        "wall": med(0.0, 0.03, 0.30, 0.45),
    }


def plan_seats(img, an, debug_path=None):
    L, W, H = an["size_m"]
    ys = [p[0] for p in an["views"]["side"]["outline_m"]]
    ymin, ymax = min(ys), max(ys)
    m, bg = A.silhouette(img)
    x0, y0, x1, y1 = A.bbox(m)
    s = (ymax - ymin) / max(1, x1 - x0)                  # metres per pixel
    cy = (y0 + y1) / 2

    def to_m(px, py):
        return (py - cy) * s, ymin + (px - x0) * s       # model x (right side = image bottom), y (forward)
    # the cabin: inside the outline, away from the rim
    rim = max(3, int(0.12 / s))
    inner = cv2.erode(m, np.ones((rim * 2 + 1, rim * 2 + 1), np.uint8))
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    pts = lab[inner > 0]
    if len(pts) < 500:
        return [], None, s
    # the seat colour: of a few colour clusters in the cabin, the one that makes the most seat-sized blobs
    k = 6
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    sample = pts[np.random.default_rng(1).choice(len(pts), min(len(pts), 40000), replace=False)]
    _, _, centres = cv2.kmeans(sample, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    lbl = np.argmin(np.linalg.norm(lab[:, :, None, :] - centres[None, None, :, :], axis=3), axis=2)
    best_seats = []
    for c in range(k):
        mk = ((lbl == c) & (inner > 0)).astype(np.uint8)
        mk = cv2.morphologyEx(mk, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, _, st, cen = cv2.connectedComponentsWithStats(mk, 8)
        seats = []
        for i in range(1, n):
            bw, bh = st[i, cv2.CC_STAT_WIDTH] * s, st[i, cv2.CC_STAT_HEIGHT] * s      # along y, across x
            fill = st[i, cv2.CC_STAT_AREA] / max(1, st[i, cv2.CC_STAT_WIDTH] * st[i, cv2.CC_STAT_HEIGHT])
            if 0.06 <= bw <= 0.85 and 0.3 <= bh <= 1.35 and fill > 0.45:
                xm, ym = to_m(cen[i][0], cen[i][1])
                seats.append([round(xm, 3), round(ym, 3), round(bh, 3), round(bw, 3)])
        if len(seats) > len(best_seats):
            best_seats = seats
    # floor: the aisle down the middle, between the seat rows
    floor = None
    if best_seats:
        sy = sorted(p[1] for p in best_seats)
        ya, yb = sy[len(sy) // 4], sy[3 * len(sy) // 4]
        pa, pb = int(x0 + (ya - ymin) / s), int(x0 + (yb - ymin) / s)
        half = max(4, int(0.18 / s))
        patch = img[int(cy) - half:int(cy) + half, min(pa, pb):max(pa, pb)]
        if patch.size and patch.shape[1] > 2 * half:
            floor = patch
    if debug_path:
        dbg = img.copy()
        for x, y, w, dd in best_seats:
            px, py = x0 + (y - ymin) / s, cy + x / s
            cv2.rectangle(dbg, (int(px - dd / s / 2), int(py - w / s / 2)), (int(px + dd / s / 2), int(py + w / s / 2)), (0, 0, 255), 2)
        cv2.imwrite(debug_path, dbg)
    return best_seats, floor, s


def rows(seats, tol=0.4):
    """Seat rows from the detected seats (often partial): [y, left?, right?] per row, front first."""
    out = []
    for x, y, w, dd in sorted(seats, key=lambda p: -p[1]):
        if out and abs(out[-1][0] - y) < tol:
            r = out[-1]
            r[3].append(y)
            r[0] = sum(r[3]) / len(r[3])
            r[1] = r[1] or x < -0.15
            r[2] = r[2] or x > 0.15
        else:
            out.append([y, bool(x < -0.15), bool(x > 0.15), [y]])
    return [[round(float(r[0]), 3), bool(r[1]), bool(r[2])] for r in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    for aid in a.ids:
        d = os.path.join(REF, aid)
        an = json.load(open(os.path.join(d, "analysis.json")))
        out = {"id": aid}
        ai = cv2.imread(os.path.join(d, "interior_aisle.jpg"))
        if ai is not None:
            out["colours"] = aisle_colours(ai)
        pl = cv2.imread(os.path.join(d, "interior_plan.jpg"))
        if pl is not None:
            seats, floor, s = plan_seats(pl, an, os.path.join(d, "_dbg_interior.jpg") if a.debug else None)
            out["seats"] = seats
            out["rows"] = rows(seats)
            if floor is not None:
                fp = os.path.join(d, "floor.jpg")
                cv2.imwrite(fp, floor, [cv2.IMWRITE_JPEG_QUALITY, 90])
                out["floor_tex"] = fp
                out["floor_tex_m"] = [round(floor.shape[1] * s, 3), round(floor.shape[0] * s, 3)]     # along y, across x
        json.dump(out, open(os.path.join(d, "interior.json"), "w"), indent=1)
        print("%-22s seats %3d  colours %s  floor %s" % (aid, len(out.get("seats", [])), "yes" if "colours" in out else "no", "yes" if "floor_tex" in out else "no"))


if __name__ == "__main__":
    main()
