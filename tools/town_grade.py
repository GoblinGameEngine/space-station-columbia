#!/usr/bin/env python3
"""Town grading: every settlement's ground smoothed into one gentle surface, so its streets, lots and
sidewalks sit on it instead of in cut-and-fill trenches and on terraced pads (the user, 2026-10-01:
"the ground the cities has become jagged and uneven ... if it does not [make sense], smooth it").

    python3 tools/town_grade.py [--check]

Run after the LAST tools/road_profile.py pass (it reads the roads' graded profiles and fits the town's
ground to them), then road_furniture.py. Never re-run road_profile.py after it: a profile regraded on
the graded ground no longer matches it, and the streets end up in trenches (Port Carrow's sat 1.9 m
down) -- run road_profile.py, then this, again. It rewrites godot_project/remake/terrain_base.bin.gz from the
ungraded terrain_base_raw.bin.gz (made from the base the first time, and again whenever
map_expanded.py has rewritten terrain.json, which drops the "town_grade" stamp).

Method (research/roads/town_grade.md): a town's ground is graded to its streets, as a real town's
is -- not each street cut and filled into the hillside on its own (that is what made the trenches,
embankments and terraced lots). Each town's footprint is its structures' lots and its streets,
widened by BUFFER. The correction the streets need (their graded height minus the natural ground)
is held fixed under every carriageway in the town, and spread smoothly between them by solving
Laplace's equation (a membrane stretched over the streets), falling to nothing at the edge of the
footprint + FADE and near water (SHORE: the banks, the water levels and the bridges' ends were set
against the natural ground). --check prints each town's grading before and after.
"""
import gzip
import json
import math
import os
import shutil
import sys

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
GD = os.path.join(ROOT, "godot_project", "remake")
SIGMA = 26.0            # m: the smoothing radius (a block and a half of lots)
BUFFER = 28.0           # m round each structure's lot and each street
FADE = 48.0             # m over which the graded town meets the untouched country
SHORE = 14.0            # m from any water: left alone
MAX_GRADE = 0.10        # the steepest a town's ground may be after grading (a steep town street, 10 %)
TOWN_CLS = ("main", "street", "alley")


def gauss_kernel(sig_cells):
    r = int(math.ceil(sig_cells * 3))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sig_cells) ** 2)
    return k / k.sum()


def blur(a, w, sig_cells):
    """A weighted Gaussian blur (normalised convolution): only cells with weight count."""
    k = gauss_kernel(sig_cells)
    num = a * w
    den = w.copy()
    for axis in (0, 1):
        num = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), axis, num)
        den = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), axis, den)
    return np.where(den > 1e-6, num / np.maximum(den, 1e-6), a)


def dilate(m, n):
    out = m.copy()
    for _ in range(n):
        o = out.copy()
        o[1:, :] |= out[:-1, :]
        o[:-1, :] |= out[1:, :]
        o[:, 1:] |= out[:, :-1]
        o[:, :-1] |= out[:, 1:]
        out = o
    return out


def slope_cap(h, mask, step, g, iters=60):
    """Relax h so no neighbouring pair inside mask differs by more than g * step."""
    lim = g * step
    for _ in range(iters):
        changed = False
        for dy, dx in ((0, 1), (1, 0)):
            a = h[: h.shape[0] - dy, : h.shape[1] - dx]
            b = h[dy:, dx:]
            ma = mask[: h.shape[0] - dy, : h.shape[1] - dx] & mask[dy:, dx:]
            d = b - a
            over = ma & (np.abs(d) > lim)
            if over.any():
                changed = True
                fix = (np.abs(d) - lim) * 0.5 * np.sign(d) * over
                a += fix
                b -= fix
        if not changed:
            break
    return h


def main():
    check = "--check" in sys.argv
    ter_path = os.path.join(GD, "terrain.json")
    ter = json.load(open(ter_path))
    rs = ter["raster"]
    nx, ny, step, x0 = rs["nx"], rs["ny"], rs["step_m"], rs["x0"]
    C = 2 * math.pi * ter["R"]
    base_p = os.path.join(GD, rs["base"])
    raw_p = os.path.join(GD, "terrain_base_raw.bin.gz")
    if "town_grade" not in ter or not os.path.exists(raw_p):
        shutil.copyfile(base_p, raw_p)                    # the ungraded base (fresh from map_expanded)
    load = lambda p: np.frombuffer(gzip.open(p).read(), np.float16).astype(np.float32).reshape(ny, nx)
    B = load(raw_p)
    L = load(os.path.join(GD, rs["level"]))
    water = L > -9000.0
    near_water = dilate(water, int(math.ceil(SHORE / step)))
    places = json.load(open(os.path.join(GD, "placement.json")))["structures"]
    towns = {}
    for e in places:
        if e.get("settlement") and e["kind"] != "crossing" and not e.get("over_water"):
            towns.setdefault(e["settlement"], []).append(e)
    out = B.copy()
    report = []
    for town, ents in sorted(towns.items()):
        ss = np.array([e["s"] for e in ents])
        xs = np.array([e["x"] for e in ents])
        # the town's window (s wraps: centre it on the median)
        sm = float(np.median(ss))
        ds = (ss - sm + C / 2) % C - C / 2
        pad = BUFFER + FADE + 3 * SIGMA
        i0 = int(math.floor((sm + ds.min() - pad) / step))
        i1 = int(math.ceil((sm + ds.max() + pad) / step))
        j0 = max(0, int(math.floor((xs.min() - pad - x0) / step)))
        j1 = min(ny, int(math.ceil((xs.max() + pad - x0) / step)))
        ii = np.arange(i0, i1) % nx
        win = B[j0:j1][:, ii]
        wwat = near_water[j0:j1][:, ii]
        S = (np.arange(i0, i1) + 0.5) * step                    # cell centres (s unwrapped near sm)
        X = x0 + (np.arange(j0, j1) + 0.5) * step
        foot = np.zeros(win.shape, bool)
        for e in ents:
            r = max(math.hypot(e["max"][0] - e["min"][0], e["max"][2] - e["min"][2]) * 0.5, 6.0) + BUFFER
            es = sm + ((e["s"] - sm + C / 2) % C - C / 2)
            ci = slice(max(0, int((es - r) / step) - i0), max(0, int((es + r) / step) - i0 + 1))
            cj = slice(max(0, int((e["x"] - r - x0) / step) - j0), max(0, int((e["x"] + r - x0) / step) - j0 + 1))
            sub_s, sub_x = np.meshgrid(S[ci], X[cj])
            foot[cj, ci] |= (sub_s - es) ** 2 + (sub_x - e["x"]) ** 2 <= r * r
        # the town's streets
        for rd in ter["roads"]:
            if rd["cls"] not in TOWN_CLS:
                continue
            for a, b in zip(rd["pts"], rd["pts"][1:]):
                as_ = sm + ((a[0] - sm + C / 2) % C - C / 2)
                if not (S[0] <= as_ <= S[-1] and X[0] <= a[1] <= X[-1]):
                    continue
                bs = as_ + ((b[0] - a[0] + C / 2) % C - C / 2)
                n = max(1, int(math.hypot(bs - as_, b[1] - a[1]) / step))
                for t in np.linspace(0, 1, n + 1):
                    ps, px = as_ + (bs - as_) * t, a[1] + (b[1] - a[1]) * t
                    ci, cj = int(ps / step) - i0, int((px - x0) / step) - j0
                    if 0 <= ci < foot.shape[1] and 0 <= cj < foot.shape[0]:
                        foot[cj, ci] = True
        foot = dilate(foot, int(BUFFER / step / 2)) & ~wwat
        # the weight: 1 on the footprint, fading out over FADE, 0 near water
        fade_n = int(FADE / step)
        w = foot.astype(np.float32)
        ring = foot.copy()
        for k in range(1, fade_n + 1):
            nxt = dilate(ring, 1)
            w[nxt & ~ring] = 1.0 - k / (fade_n + 1)
            ring = nxt
        w = w * (~wwat)
        w = w * w * (3 - 2 * w)                                   # smoothstep
        # the streets' graded heights: the correction (graded - natural) fixed under each carriageway
        fix = np.zeros(win.shape, bool)
        corr = np.zeros(win.shape, np.float32)
        pstep = float(ter.get("prof_step", 4.0))
        for rd in ter["roads"]:
            zp = rd.get("prof")
            if not zp or rd["cls"] not in TOWN_CLS + ("county", "hwy"):
                continue
            pts = rd["pts"]
            cum = [0.0]
            for q0, q1 in zip(pts, pts[1:]):
                cum.append(cum[-1] + math.hypot((q1[0] - q0[0] + C / 2) % C - C / 2, q1[1] - q0[1]))
            hw = rd["w"] * 0.5
            for k in range(len(pts) - 1):
                a, b = pts[k], pts[k + 1]
                as_ = sm + ((a[0] - sm + C / 2) % C - C / 2)
                if not (S[0] - 40 <= as_ <= S[-1] + 40 and X[0] - 40 <= a[1] <= X[-1] + 40):
                    continue
                bs = as_ + ((b[0] - a[0] + C / 2) % C - C / 2)
                seg = math.hypot(bs - as_, b[1] - a[1])
                if seg < 1e-6:
                    continue
                ts, tx = (bs - as_) / seg, (b[1] - a[1]) / seg
                c0 = cum[k] if k < len(cum) else 0.0
                for u in np.arange(0.0, seg + 1e-6, step * 0.5):
                    zi = (c0 + u) / pstep
                    z0 = int(min(max(math.floor(zi), 0), len(zp) - 1))
                    z1 = min(z0 + 1, len(zp) - 1)
                    if zp[z0] < -9000 or zp[z1] < -9000:
                        continue
                    h = zp[z0] + (zp[z1] - zp[z0]) * min(max(zi - z0, 0.0), 1.0)
                    for v in np.arange(-hw, hw + 1e-6, step * 0.5):
                        ps, px = as_ + ts * u - tx * v, a[1] + tx * u + ts * v
                        ci, cj = int(ps / step) - i0, int((px - x0) / step) - j0
                        if 0 <= ci < win.shape[1] and 0 <= cj < win.shape[0] and foot[cj, ci]:
                            fix[cj, ci] = True
                            corr[cj, ci] = h - win[cj, ci]
        # the membrane: Laplace inside the footprint + fade, 0 at its edge and near water
        dom = dilate(foot, fade_n) & ~wwat
        cfield = corr.copy()
        free = dom & ~fix
        for _ in range(2500):
            avg = 0.25 * (np.roll(cfield, 1, 0) + np.roll(cfield, -1, 0) + np.roll(cfield, 1, 1) + np.roll(cfield, -1, 1))
            cfield = np.where(free, avg, np.where(fix, corr, 0.0))
        out_win = win + cfield * dom

        def slopes(h):
            gy, gx = np.gradient(h, step)
            g = np.hypot(gx, gy)[foot]
            return (float(np.mean(g)), float(np.percentile(g, 95))) if g.size else (0.0, 0.0)
        b0, b1 = slopes(win), slopes(out_win)
        report.append((town, int(foot.sum()), b0, b1, float(np.abs(out_win - win)[foot].max()) if foot.any() else 0.0))
        for col, i in enumerate(ii):
            out[j0:j1, i] = np.where(dom[:, col], out_win[:, col], out[j0:j1, i])
    for town, n, b0, b1, dmax in report:
        print("%-16s %6d cells  slope mean %.3f -> %.3f   p95 %.3f -> %.3f   most changed %.1f m" % (town, n, b0[0], b1[0], b0[1], b1[1], dmax))
    if check:
        return
    with gzip.open(base_p, "wb", compresslevel=6) as f:
        f.write(out.astype(np.float16).tobytes())
    ter["town_grade"] = {"sigma_m": SIGMA, "buffer_m": BUFFER, "fade_m": FADE, "shore_m": SHORE, "max_grade": MAX_GRADE,
                         "raw": "terrain_base_raw.bin.gz", "towns": len(report)}
    json.dump(ter, open(ter_path, "w"), separators=(",", ":"))
    print("town grading written: %s" % base_p)


if __name__ == "__main__":
    main()
