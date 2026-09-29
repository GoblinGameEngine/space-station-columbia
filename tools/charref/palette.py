"""Measure the colours of the Ghibli reference stills (reference/ghibli/stills) so the character
generator's palette rules come from data: per film, k-means in CIE Lab over every still, plus the
spread of saturation and value.  Writes reference/ghibli/palette.json (the numbers) and
reference/ghibli/palettes/<film>.png (swatch strips, widest cluster first).
usage: python3 tools/charref/palette.py [film ...]"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2] / "reference" / "ghibli"
SRC, OUT = ROOT / "stills", ROOT / "palettes"
K, SIDE, SEED = 16, 96, 1


def srgb_to_lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    xyz /= np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)


def lab_to_srgb(lab):
    fy = (lab[:, 0] + 16) / 116
    f = np.stack([fy + lab[:, 1] / 500, fy, fy - lab[:, 2] / 200], 1)
    xyz = np.where(f > 0.2069, f ** 3, (f - 16 / 116) / 7.787) * np.array([0.95047, 1.0, 1.08883])
    c = xyz @ np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]]).T
    c = np.where(c > 0.0031308, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055, 12.92 * c)
    return np.clip(c * 255, 0, 255).round().astype(int)


def kmeans(x, k, iters=30):
    rng = np.random.default_rng(SEED)
    c = x[rng.choice(len(x), 1)]
    for _ in range(k - 1):                              # k-means++ seeding
        d = ((x[:, None] - c[None]) ** 2).sum(-1).min(1)
        c = np.vstack([c, x[rng.choice(len(x), 1, p=d / d.sum())]])
    for _ in range(iters):
        lab = ((x[:, None] - c[None]) ** 2).sum(-1).argmin(1)
        c = np.array([x[lab == i].mean(0) if (lab == i).any() else c[i] for i in range(k)])
    return c, np.bincount(lab, minlength=k) / len(x)


def hsv_stats(rgb):
    mx, mn = rgb.max(1), rgb.min(1)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    v = mx / 255.0
    q = lambda a: [round(float(t), 3) for t in np.percentile(a, [10, 25, 50, 75, 90])]
    return {"sat_p10_25_50_75_90": q(s), "val_p10_25_50_75_90": q(v),
            "share_sat_over_0.7": round(float((s > 0.7).mean()), 4)}


def film(slug):
    px = []
    for f in sorted(SRC.glob(f"{slug}[0-9][0-9][0-9].jpg")):
        px.append(np.asarray(Image.open(f).convert("RGB").resize((SIDE, SIDE * 9 // 16)), float).reshape(-1, 3))
    rgb = np.vstack(px)
    sub = rgb[np.random.default_rng(SEED).choice(len(rgb), min(len(rgb), 60000), replace=False)]
    c, w = kmeans(srgb_to_lab(sub), K)
    order = np.argsort(-w)
    cols = lab_to_srgb(c[order])
    OUT.mkdir(exist_ok=True)
    strip = Image.new("RGB", (800, 60))
    x = 0
    for col, wt in zip(cols, w[order]):
        wd = max(1, round(800 * wt))
        strip.paste(tuple(int(v) for v in col), (x, 0, min(800, x + wd), 60))
        x += wd
    strip.save(OUT / f"{slug}.png")
    return {"stills": len(px), **hsv_stats(sub),
            "clusters": [{"hex": "#%02x%02x%02x" % tuple(col), "lab": [round(float(v), 1) for v in lab], "share": round(float(wt), 4)}
                         for col, lab, wt in zip(cols, c[order], w[order])]}


if __name__ == "__main__":
    slugs = sys.argv[1:] or sorted({f.stem[:-3] for f in SRC.glob("*.jpg")})
    path = ROOT / "palette.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    for s in slugs:
        data[s] = film(s)
        d = data[s]
        print(f"{s:12} {d['stills']:3} stills  sat median {d['sat_p10_25_50_75_90'][2]:.2f}  val median {d['val_p10_25_50_75_90'][2]:.2f}  vivid {d['share_sat_over_0.7']:.1%}")
    path.write_text(json.dumps(data, indent=1))
