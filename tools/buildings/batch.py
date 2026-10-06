#!/usr/bin/env python3
"""batch.py OUT.png ID ID ID ID -- a contact sheet of four catalog records' first photos, and their skeleton tokens
(catalog_tokens.skeleton) printed compactly, for the annotator (METHOD.md §4)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog_tokens as C
from PIL import Image, ImageDraw
out, ids = sys.argv[1], sys.argv[2:6]
S = Image.new("RGB", (1400, 1050))
for i, arg in enumerate(ids):
    cid, _, k = arg.partition("@")                 # (ID@n: show the record's n-th photo)
    k = int(k or 0)
    s = C.skeleton(cid)
    print("%s | %s %s | %s | %s" % (cid, s["place"]["town"], s["place"]["state"], s["year_built"], s["place"]["source_title"][:60]))
    print("   " + " ".join(t.split(":")[1] if t.split(":")[0] in ("use",) else t for t in s["tokens"]))
    if s["images"]:
        im = Image.open(os.path.join(C.ROOT, s["images"][min(k, len(s["images"]) - 1)]["file"])).convert("RGB")
        im.thumbnail((700, 525))
        S.paste(im, ((i % 2) * 700, (i // 2) * 525))
    ImageDraw.Draw(S).text(((i % 2) * 700 + 6, (i // 2) * 525 + 6), arg, fill=(255, 255, 0))
S.save(out)
