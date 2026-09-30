#!/usr/bin/env python3
"""Rotoscope a walk from dual-view reference footage (a side panel and a front panel shot at once,
dark bodysuit on a white grid): per frame, the silhouette's head, shoulders, lean and feet, then
folded onto one gait cycle (0 = right heel strike) as mean curves.

    roto/bin/python tools/charref/roto_walk.py video.mp4 out_prefix [side_x0,x1 front_x0,x1]

Writes out_prefix.csv (per frame), out_prefix_cycle.json (curves by phase, in fractions of body
height and degrees) and out_prefix_check.jpg (the measurements drawn on sampled frames).

Measures (front panel): head x, shoulder-line tilt (+: the figure's right shoulder up), apparent
shoulder width (narrows as the chest twists), chest x.  (side panel): head top y (bob), head x
ahead of the pelvis (lean), stride (feet apart) -> contacts.  Right vs left step: at contact, the
leading foot is nearer the front camera, so lower in the front image.
"""
import json
import sys

import cv2
import numpy as np


def mask_of(img):
    b, g, r = [img[..., i].astype(int) for i in range(3)]
    gray = (r + g + b) / 3
    grid = (r > 150) & (r - g > 40)                # the red/pink grid
    fg = (gray < 185) & ~grid
    fg = fg.astype(np.uint8) * 255
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg)
    if n <= 1:
        return None
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return lab == k


def dark_torso(img, near):
    """The bodysuit alone (dark, the bare arms and neck excluded): the component nearest `near`."""
    gray = img.astype(int).mean(axis=2)
    d = (gray < 95).astype(np.uint8) * 255
    d = cv2.morphologyEx(d, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(d)
    if n <= 1:
        return None
    best = max(range(1, n), key=lambda k: stats[k, cv2.CC_STAT_AREA] - 3.0 * abs(cent[k][0] - near[0]) - 3.0 * abs(cent[k][1] - near[1]))
    return lab == best


def shoulder_line(t, H):
    """Tilt of the torso's top edge (the straps over the shoulders): a line fitted to the top y of
    each column across the outer parts of the upper torso.  Returns (tilt deg, +: image-right end
    higher), the two end points, the top-edge width."""
    ys, xs = np.nonzero(t)
    top = ys.min()
    band = t[top:top + int(0.12 * H)]
    cols = np.nonzero(band.any(axis=0))[0]
    x0, x1 = cols.min(), cols.max()
    w = x1 - x0
    sel = [x for x in range(x0, x1 + 1) if abs(x - (x0 + x1) / 2) > 0.18 * w]
    yt = [top + np.argmax(band[:, x]) for x in sel]
    k, c = np.polyfit(sel, yt, 1)
    tilt = -np.degrees(np.arctan(k))                 # image y grows down
    return tilt, (x0, k * x0 + c), (x1, k * x1 + c), w


def span_at(m, y, xc):
    """The run of mask pixels on row y containing (or nearest) xc."""
    xs = np.nonzero(m[y])[0]
    if xs.size == 0:
        return None
    runs = np.split(xs, np.nonzero(np.diff(xs) > 1)[0] + 1)
    best = min(runs, key=lambda r: 0 if r[0] <= xc <= r[-1] else min(abs(r[0] - xc), abs(r[-1] - xc)))
    return best[0], best[-1]


def measure_front(m, img=None):
    ys, xs = np.nonzero(m)
    top, bot = ys.min(), ys.max()
    H = bot - top
    head = m[top:top + int(0.1 * H)]
    hx = np.nonzero(head)[1].mean()
    # the neck: the narrowest span below the head; the shoulders: the top of the torso either side
    widths = []
    for y in range(top + int(0.08 * H), top + int(0.2 * H)):
        s = span_at(m, y, hx)
        widths.append((s[1] - s[0]) if s else 999)
    neck = top + int(0.08 * H) + int(np.argmin(widths))
    yc = neck + int(0.07 * H)                      # chest, just under the shoulders
    s = span_at(m, yc, hx)
    cx = (s[0] + s[1]) / 2
    half = (s[1] - s[0]) / 2
    pts = []
    for sx in (cx - 0.72 * half, cx + 0.72 * half):
        col = m[neck - int(0.02 * H):yc, int(round(sx))]
        on = np.nonzero(col)[0]
        pts.append(neck - int(0.02 * H) + (on[0] if on.size else col.size))
    # image left is the figure's right (they face the camera)
    tilt = np.degrees(np.arctan2(pts[1] - pts[0], 1.44 * half))   # + : figure's right shoulder up
    sw = 2 * half
    if img is not None:
        t = dark_torso(img, (cx, yc))
        if t is not None:
            tl, pa, pb, w = shoulder_line(t, H)
            tilt = -tl                               # image-right is the figure's left: + = figure's right up
            pts = [pa[1], pb[1]]
            cx = (pa[0] + pb[0]) / 2
            half = (pb[0] - pa[0]) / 2
            sw = w
    # feet: lowest points on each half of the bottom band
    band = m[bot - int(0.06 * H):bot + 1]
    by, bx = np.nonzero(band)
    mid = cx
    lo_l = by[bx < mid].max() if (bx < mid).any() else 0      # image-left foot = figure's right
    lo_r = by[bx >= mid].max() if (bx >= mid).any() else 0
    return dict(f_top=top, f_H=H, f_hx=hx, f_cx=cx, f_sw=sw, f_tilt=tilt, f_neck=neck,
                f_shR=(cx - half, pts[0]), f_shL=(cx + half, pts[1]),
                f_footR=lo_l, f_footL=lo_r)


def measure_side(m):
    ys, xs = np.nonzero(m)
    top, bot = ys.min(), ys.max()
    H = bot - top
    head = m[top:top + int(0.1 * H)]
    hx = np.nonzero(head)[1].mean()
    py = top + int(0.52 * H)                       # the pelvis band
    s = span_at(m, py, hx)
    px = (s[0] + s[1]) / 2 if s else hx
    cy = top + int(0.25 * H)                       # the chest band (arms may overlap: use the span nearest the head)
    s2 = span_at(m, cy, hx)
    cxs = (s2[0] + s2[1]) / 2 if s2 else hx
    band = m[bot - int(0.05 * H):bot + 1]
    bx = np.nonzero(band)[1]
    stride = (bx.max() - bx.min()) if bx.size else 0
    return dict(s_top=top, s_H=H, s_hx=hx, s_px=px, s_cx=cxs, s_stride=stride, s_py=py, s_cy=cy)


def main():
    video, out = sys.argv[1], sys.argv[2]
    sx = [int(v) for v in (sys.argv[3] if len(sys.argv) > 3 else "10,290").split(",")]
    fx = [int(v) for v in (sys.argv[4] if len(sys.argv) > 4 else "348,630").split(",")]
    cap = cv2.VideoCapture(video)
    rows = []
    frames = []
    prev = None
    i = 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        img = img[..., ::-1]                        # BGR -> RGB
        side = img[:, sx[0]:sx[1]]
        front = img[:, fx[0]:fx[1]]
        # skip repeated frames (slow motion by duplication)
        small = cv2.resize(img, (80, 45)).astype(int)
        if prev is not None and np.abs(small - prev).mean() < 0.8:
            i += 1
            continue
        prev = small
        ms, mf = mask_of(side), mask_of(front)
        if ms is None or mf is None:
            i += 1
            continue
        try:
            r = dict(frame=i, **measure_side(ms), **measure_front(mf, front))
        except (ValueError, TypeError, IndexError):
            i += 1
            continue
        rows.append(r)
        frames.append((i, img.copy()))
        i += 1
    # the body height: the median standing height (side panel top-to-feet)
    H = float(np.median([r["s_H"] for r in rows]))
    # keep frames where the figure is whole (its height near the median) -- drops turns and the edges
    keep = [r for r in rows if abs(r["s_H"] - H) < 0.08 * H and abs(r["f_H"] - np.median([q["f_H"] for q in rows])) < 0.08 * H]
    # contacts: local maxima of the stride
    st = np.array([r["s_stride"] for r in keep], float)
    st = np.convolve(st, np.ones(3) / 3, mode="same")
    contacts = [k for k in range(2, len(st) - 2) if st[k] >= st[k - 2:k + 3].max() and st[k] > 0.55 * st.max()]
    # dedupe neighbours
    cc = []
    for k in contacts:
        if not cc or k - cc[-1] > 3:
            cc.append(k)
    # which foot leads: nearer the front camera = lower in the image
    leads = ["R" if keep[k]["f_footR"] > keep[k]["f_footL"] else "L" for k in cc]
    # phase: 0 at a right contact, 0.5 at the left, interpolated by frame between contacts;
    # only pairs of successive contacts that alternate feet count
    phase = [None] * len(keep)
    for a in range(len(cc) - 1):
        k0, k1 = cc[a], cc[a + 1]
        if leads[a] == leads[a + 1] or k1 - k0 > 40:
            continue
        p0 = 0.0 if leads[a] == "R" else 0.5
        for k in range(k0, k1):
            phase[k] = (p0 + 0.5 * (k - k0) / (k1 - k0)) % 1.0
    # curves, per frame, as fractions of height / degrees, relative to each cycle's mean
    def feat(r):
        return {
            "bob": -(r["s_top"]) / H,                         # head height (up +)
            "head_fwd": (r["s_hx"] - r["s_px"]) / H,          # head ahead of the pelvis (side)
            "chest_fwd": (r["s_cx"] - r["s_px"]) / H,
            "head_lat": (r["f_hx"] - r["f_cx"]) / H,          # head vs chest, screen x (front)
            "chest_lat": r["f_cx"] / H,                       # the chest's sway (front)
            "sh_tilt": r["f_tilt"],
            "sh_width": r["f_sw"] / H,
        }
    bins = 20
    acc = {}
    for k, r in enumerate(keep):
        if phase[k] is None:
            continue
        b = int(phase[k] * bins) % bins
        for name, v in feat(r).items():
            acc.setdefault(name, [[] for _ in range(bins)])[b].append(v)
    curves = {}
    for name, bl in acc.items():
        means = [float(np.mean(x)) if x else None for x in bl]
        known = [m for m in means if m is not None]
        mu = float(np.mean(known)) if known else 0.0
        curves[name] = [None if m is None else round(m - mu, 5) for m in means]
        curves[name + "_mean"] = round(mu, 5)
    json.dump({"video": video, "height_px": H, "contacts": [(keep[k]["frame"], leads[j]) for j, k in enumerate(cc)],
               "frames_used": sum(p is not None for p in phase), "bins": bins, "curves": curves},
              open(out + "_cycle.json", "w"), indent=1)
    with open(out + ".csv", "w") as f:
        f.write("frame,phase," + ",".join(feat(keep[0]).keys()) + "\n")
        for k, r in enumerate(keep):
            f.write("%d,%s,%s\n" % (r["frame"], "" if phase[k] is None else "%.3f" % phase[k],
                                    ",".join("%.5f" % v for v in feat(r).values())))
    # a check sheet: the measurements drawn on 12 frames through one cycle
    byframe = dict(frames)
    picks = [k for k in range(len(keep)) if phase[k] is not None][:48:4]
    tiles = []
    for k in picks:
        r = keep[k]
        img = np.ascontiguousarray(byframe[r["frame"]][..., ::-1])
        o = fx[0]
        for key in ("f_shR", "f_shL"):
            x, y = r[key]
            cv2.circle(img, (int(o + x), int(y)), 4, (0, 200, 0), -1)
        cv2.line(img, (int(o + r["f_shR"][0]), int(r["f_shR"][1])), (int(o + r["f_shL"][0]), int(r["f_shL"][1])), (0, 200, 0), 2)
        cv2.circle(img, (int(o + r["f_hx"]), int(r["f_top"]) + 8), 4, (255, 0, 0), -1)
        cv2.circle(img, (int(sx[0] + r["s_hx"]), int(r["s_top"]) + 8), 4, (255, 0, 0), -1)
        cv2.circle(img, (int(sx[0] + r["s_px"]), int(r["s_py"])), 4, (0, 0, 255), -1)
        cv2.putText(img, "ph %.2f tilt %+.1f" % (phase[k], r["f_tilt"]), (300, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        tiles.append(cv2.resize(img, (480, 270)))
    if tiles:
        while len(tiles) % 4:
            tiles.append(np.full_like(tiles[0], 255))
        sheet = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)])
        cv2.imwrite(out + "_check.jpg", sheet)
    print("frames %d kept %d phased %d contacts %s" % (len(rows), len(keep), sum(p is not None for p in phase), "".join(leads)))


if __name__ == "__main__":
    main()
