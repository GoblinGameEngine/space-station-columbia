"""Measure figure proportions on the reference stills (ghibli_style.md 5).

  python3 tools/charref/measure.py grid omoide050 [x0 y0 x1 y1]   crop + labelled pixel grid -> scratch png
  python3 tools/charref/measure.py add omoide050 "Taeko" adult f 812 402 1336 [note]
                                        (label, age class, sex, head-top y, chin y, feet y)
  python3 tools/charref/measure.py summary

Only standing, roughly upright figures seen whole and near side-on to the camera.  The measurements
(coordinates, no image content) go to research/characters/data/proportions.csv, which is committed."""
import csv, statistics, sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
STILLS = ROOT / "reference" / "ghibli" / "stills"
CSV = ROOT / "research" / "characters" / "data" / "proportions.csv"
OUT = Path("/tmp/claude-1000/measure") if Path("/tmp/claude-1000").exists() else ROOT / "reference" / "ghibli" / "measure"
COLS = ["still", "label", "age", "sex", "top", "chin", "feet", "heads", "note"]


def grid(still, box=None):
    im = Image.open(STILLS / f"{still}.jpg").convert("RGB")
    if box:
        im = im.crop(box)
    x0, y0 = (box[0], box[1]) if box else (0, 0)
    step = 50 if max(im.size) > 900 else 10 if max(im.size) < 300 else 25
    k = max(1, int(900 // max(im.size)))            # small crops are enlarged; labels stay in still pixels
    w, h = im.size
    im = im.resize((w * k, h * k), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for x in range((x0 // step + 1) * step, x0 + w, step):
        big = x % (step * 4) == 0
        d.line([((x - x0) * k, 0), ((x - x0) * k, im.height)], fill=(255, 255, 0) if big else (0, 255, 255), width=1)
        d.text(((x - x0) * k + 2, 2), str(x), fill=(255, 255, 0) if big else (0, 255, 255))
    for y in range((y0 // step + 1) * step, y0 + h, step):
        big = y % (step * 4) == 0
        d.line([(0, (y - y0) * k), (im.width, (y - y0) * k)], fill=(255, 255, 0) if big else (0, 255, 255), width=1)
        d.text((2, (y - y0) * k + 2), str(y), fill=(255, 255, 0) if big else (0, 255, 255))
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{still}_{x0}_{y0}.png"
    im.save(p)
    print(p, im.size, "grid", step)


def rows():
    if not CSV.exists():
        return []
    with CSV.open() as f:
        return list(csv.DictReader(f))


def add(still, label, age, sex, top, chin, feet, note=""):
    top, chin, feet = float(top), float(chin), float(feet)
    r = rows()
    r = [x for x in r if not (x["still"] == still and x["label"] == label)]
    r.append({"still": still, "label": label, "age": age, "sex": sex, "top": top, "chin": chin, "feet": feet,
              "heads": round((feet - top) / (chin - top), 2), "note": note})
    CSV.parent.mkdir(parents=True, exist_ok=True)
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(r)
    print(label, "heads tall:", r[-1]["heads"])


def summary():
    by = {}
    for r in rows():
        by.setdefault((r["age"], r["sex"]), []).append(float(r["heads"]))
    for (age, sex), v in sorted(by.items()):
        print(f"{age:8} {sex}  n={len(v):2}  mean {statistics.mean(v):.2f}  min {min(v):.2f}  max {max(v):.2f}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "grid":
        grid(a[1], tuple(int(v) for v in a[2:6]) if len(a) >= 6 else None)
    elif a[0] == "add":
        add(*a[1:])
    else:
        summary()
