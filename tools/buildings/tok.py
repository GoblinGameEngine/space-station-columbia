#!/usr/bin/env python3
"""tok.py -- write a token file (research/buildings/TOKENS.md) from a compact spec, filling the image block (source,
licence, author, caption) from the image folder's sources.json so attribution travels with the tokens.
Used by the annotator: tok.write("GL-0001", "corpus_x/file.jpg", "front_34", {...})."""
import json, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def image(rel, view):
    d, f = os.path.split(rel)
    src = {}
    mp = os.path.join(ROOT, "remake", "reference", d, "sources.json")
    if os.path.exists(mp):
        src = next((e for e in json.load(open(mp))["files"] if e["file"] == f), {})
    return {"file": "remake/reference/" + rel, "view": view, "source": src.get("source", ""), "url": src.get("record") or src.get("url", ""),
            "license": src.get("license", ""), "author": src.get("author", "")[:120], "caption": src.get("caption", "")[:200]}


def write(tid, images, spec, region="great_lakes"):
    t = {"id": tid, "images": [image(r, v) for r, v in images]}
    t.update(spec)
    t.setdefault("annotator", "claude 2026-10-05")
    out = os.path.join(ROOT, "research", "buildings", "regions", region, "tokens", tid + ".json")
    json.dump(t, open(out, "w"), indent=1)
    return out
