#!/usr/bin/env python3
"""sheet.py OUT LABEL=remake/reference/rel/path ... -- a 2x2 contact sheet of reference images for annotation."""
import sys
from PIL import Image, ImageDraw
args = sys.argv[2:]
S = Image.new("RGB", (1400, 1050))
for i, a in enumerate(args[:4]):
    lab, f = a.split("=", 1)
    im = Image.open(f).convert("RGB"); im.thumbnail((700, 525))
    S.paste(im, ((i % 2) * 700, (i // 2) * 525)); ImageDraw.Draw(S).text(((i % 2) * 700 + 6, (i // 2) * 525 + 6), lab, fill=(255, 255, 0))
S.save(sys.argv[1])
