"""Measure how Ghibli's cel shadow colour relates to the lit colour, per material, from the stills.

In a box around one material (a face, a sleeve, a skirt), cel paint is a few flat colours: the lit
tone and the shadow tone are the two largest clusters that pass the material's filter.  For each pair
the tool records the shift from lit to shade: hue rotation, saturation ratio, value ratio, and Lab
deltas.  Those numbers drive the shade-colour rule in the character shader (ghibli_style.md 2.2).

  python3 tools/charref/shade_pairs.py add majo006 Kiki skin 900 120 1060 265
  python3 tools/charref/shade_pairs.py add majo006 Kiki cloth 850 280 1100 800
  python3 tools/charref/shade_pairs.py summary
  python3 tools/charref/shade_pairs.py show majo006 900 120 1060 265     (clusters found, to check a box)

kinds: skin (hue 0-50 deg, sat 0.1-0.65, value > 0.35), hair, cloth (no filter).
Results (colours only, no image content) go to research/characters/data/shade_pairs.csv."""
import colorsys, csv, statistics, sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from palette import srgb_to_lab, kmeans                        # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
STILLS = ROOT / "reference" / "ghibli" / "stills"
CSV = ROOT / "research" / "characters" / "data" / "shade_pairs.csv"
COLS = ["still", "label", "kind", "box", "lit", "shade", "share_lit", "share_shade", "dhue", "sat_ratio", "val_ratio", "dL", "da", "db"]


def hsv(c):
    return colorsys.rgb_to_hsv(*(np.asarray(c) / 255.0))


def ok(kind, c):
    h, s, v = hsv(c)
    if kind == "skin":
        return (h * 360 <= 50 or h * 360 >= 345) and 0.10 <= s <= 0.65 and v > 0.35
    return True


def clusters(still, box, k=6):
    im = Image.open(STILLS / f"{still}.jpg").convert("RGB").crop(box)
    px = np.asarray(im, float).reshape(-1, 3)
    if len(px) > 40000:
        px = px[np.random.default_rng(1).choice(len(px), 40000, replace=False)]
    lab = srgb_to_lab(px)
    c, w = kmeans(lab, k)
    rgb = []
    for i in range(k):                                          # the mean sRGB of each cluster's pixels
        m = ((lab[:, None] - c[None]) ** 2).sum(-1).argmin(1) == i
        rgb.append(px[m].mean(0) if m.any() else np.zeros(3))
    order = np.argsort(-w)
    return [(rgb[i], float(w[i]), c[i]) for i in order]


def pair(kind, cl):
    """The two biggest clusters passing the filter, with similar hue (the same paint lit and shaded)."""
    cand = [x for x in cl if ok(kind, x[0]) and x[1] > 0.04]
    for i, a in enumerate(cand):
        for b in cand[i + 1:]:
            ha, hb = hsv(a[0])[0] * 360, hsv(b[0])[0] * 360
            dh = (hb - ha + 180) % 360 - 180
            lit, sh = (a, b) if a[2][0] > b[2][0] else (b, a)
            dl = lit[2][0] - sh[2][0]
            dab = float(np.hypot(*(sh[2][1:] - lit[2][1:])))
            # the same paint lit and shaded: a real value step (not two near-equal tones, not paint vs
            # line or hair), and a modest move in a/b (a shadow tints; it doesn't change the colour)
            if (abs(dh) < 60 or min(hsv(a[0])[1], hsv(b[0])[1]) < 0.12) and 6 < dl < 38 and dab < 16:
                return lit, sh
    return None


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(round(v)) for v in c)


def add(still, label, kind, *box):
    box = tuple(int(v) for v in box)
    p = pair(kind, clusters(still, box))
    if not p:
        print("no lit/shade pair found: try a tighter box (show)")
        return
    lit, sh = p
    hl, sl, vl = hsv(lit[0])
    hs, ss, vs = hsv(sh[0])
    r = {"still": still, "label": label, "kind": kind, "box": " ".join(map(str, box)), "lit": hexc(lit[0]), "shade": hexc(sh[0]),
         "share_lit": round(lit[1], 3), "share_shade": round(sh[1], 3),
         "dhue": round(((hs - hl) * 360 + 180) % 360 - 180, 1), "sat_ratio": round(ss / max(sl, 1e-3), 3),
         "val_ratio": round(vs / max(vl, 1e-3), 3), "dL": round(float(sh[2][0] - lit[2][0]), 1),
         "da": round(float(sh[2][1] - lit[2][1]), 1), "db": round(float(sh[2][2] - lit[2][2]), 1)}
    rows = [x for x in load() if not (x["still"] == still and x["label"] == label and x["kind"] == kind)]
    rows.append(r)
    CSV.parent.mkdir(parents=True, exist_ok=True)
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"{label:10} {kind:5} lit {r['lit']} shade {r['shade']}  dhue {r['dhue']:+6.1f}  sat x{r['sat_ratio']:.2f}  val x{r['val_ratio']:.2f}  dLab ({r['dL']:+.0f} {r['da']:+.0f} {r['db']:+.0f})")


def load():
    if not CSV.exists():
        return []
    with CSV.open() as f:
        return list(csv.DictReader(f))


def summary():
    by = {}
    for r in load():
        by.setdefault(r["kind"], []).append(r)
    for kind, rs in by.items():
        f = lambda k: [float(x[k]) for x in rs]
        med = lambda k: statistics.median(f(k))
        print(f"{kind:5} n={len(rs):2}  dhue median {med('dhue'):+.1f} (range {min(f('dhue')):+.0f}..{max(f('dhue')):+.0f})  "
              f"sat x{med('sat_ratio'):.2f}  val x{med('val_ratio'):.2f}  dL {med('dL'):+.0f}  da {med('da'):+.1f}  db {med('db'):+.1f}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "add":
        add(*a[1:])
    elif a[0] == "show":
        for rgb, w, lab in clusters(a[1], tuple(int(v) for v in a[2:6])):
            h, s, v = hsv(rgb)
            print(f"{hexc(rgb)} share {w:.2f}  hue {h * 360:5.1f} sat {s:.2f} val {v:.2f}  L {lab[0]:.0f}")
    else:
        summary()
