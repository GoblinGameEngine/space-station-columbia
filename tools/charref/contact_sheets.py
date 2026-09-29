#!/usr/bin/env python3
"""Contact sheets of the reference stills: one image per film (a grid of its stills, numbered), for
studying character design at a glance.  Reads reference/ghibli/stills/<film>NNN.jpg (local-only,
gitignored), writes reference/ghibli/sheets/<film>.jpg.

    python3 tools/charref/contact_sheets.py [film ...]
"""
import os
import re
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "reference", "ghibli"))
SRC, OUT = os.path.join(ROOT, "stills"), os.path.join(ROOT, "sheets")
TW, TH, COLS = 384, 208, 5


def films():
    return sorted({re.sub(r"\d+\.jpg$", "", f) for f in os.listdir(SRC) if f.endswith(".jpg")})


def sheet(film):
    files = sorted(f for f in os.listdir(SRC) if re.fullmatch(re.escape(film) + r"\d+\.jpg", f))
    rows = (len(files) + COLS - 1) // COLS
    im = Image.new("RGB", (COLS * TW, rows * TH), (20, 20, 20))
    d = ImageDraw.Draw(im)
    for i, f in enumerate(files):
        t = Image.open(os.path.join(SRC, f)).convert("RGB")
        t.thumbnail((TW - 4, TH - 4))
        x, y = (i % COLS) * TW + 2, (i // COLS) * TH + 2
        im.paste(t, (x, y))
        d.rectangle((x, y, x + 34, y + 16), fill=(0, 0, 0))
        d.text((x + 3, y + 2), f[len(film):-4], fill=(255, 255, 0))
    os.makedirs(OUT, exist_ok=True)
    im.save(os.path.join(OUT, film + ".jpg"), quality=82)
    return len(files)


if __name__ == "__main__":
    for f in sys.argv[1:] or films():
        print(f, sheet(f))
