#!/usr/bin/env python3
"""Build catalogued assets from their Grok references: analyse, build in Blender (in parallel),
overlay the side render on the reference, write review sheets.

    python3 tools/assets/build.py [ids...] [--family hull] [--workers 4] [--no-analyse] [--sheets]

GLBs go to godot_project/remake/vehicles/<id>.glb; renders and overlays to
reference/grok/<id>/build/; a status line per asset to reference/grok/_build.log; review sheets of
five assets each to reference/grok/_review_<n>.png with --sheets.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))
import catalog

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF = os.path.join(ROOT, "reference", "grok")
OUTDIR = os.path.join(ROOT, "godot_project", "remake", "vehicles")
PY = os.path.expanduser("~/.venvs/ssc-assets/bin/python")
BLENDER = ["flatpak", "run", "org.blender.Blender", "-b", "--factory-startup", "--python", os.path.join(ROOT, "remake", "blender", "build_asset.py"), "--"]


def overlay(aid):
    from PIL import Image
    b = os.path.join(REF, aid, "build")
    r = os.path.join(b, "r_side.png")
    if not os.path.exists(r):
        return
    a = Image.open(r).convert("RGB")
    ref = Image.open(os.path.join(REF, aid, "side.jpg")).convert("RGB").resize(a.size)
    Image.blend(ref, a, 0.5).save(os.path.join(b, "r_side_overlay.png"))


def build_one(aid):
    fam = catalog.ASSETS[aid][0]
    an = os.path.join(REF, aid, "analysis.json")
    if not os.path.exists(an):
        return aid, "no analysis"
    b = os.path.join(REF, aid, "build")
    os.makedirs(b, exist_ok=True)
    out = os.path.join(OUTDIR, aid + ".glb")
    t0 = time.time()
    r = subprocess.run(BLENDER + [aid, an, out, os.path.join(b, "r"), fam], capture_output=True, text=True, timeout=1200)
    log = r.stdout + r.stderr
    open(os.path.join(b, "blender.log"), "w").write(log)
    ok = "ASSET_EXPORTED" in log
    if ok:
        overlay(aid)
    line = [l for l in log.splitlines() if l.startswith("ASSET_EXPORTED")]
    err = [l for l in log.splitlines() if "Error" in l or "Traceback" in l]
    return aid, ("ok %.0fs %s" % (time.time() - t0, line[0].split(" ", 3)[-1] if line else "")) if ok else ("FAILED " + " | ".join(err[-3:]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--family")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-analyse", action="store_true")
    ap.add_argument("--sheets", action="store_true")
    a = ap.parse_args()
    ids = a.ids or [k for k, v in catalog.ASSETS.items() if v[0] != "existing" and (not a.family or v[0] == a.family)]
    ids = [i for i in ids if os.path.exists(os.path.join(REF, i, "side.jpg"))]
    if not a.no_analyse:
        r = subprocess.run([PY, os.path.join(ROOT, "tools", "assets", "analyze.py")] + ids, capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode:
            print(r.stderr[-2000:])
    logf = open(os.path.join(REF, "_build.log"), "a")
    with ThreadPoolExecutor(a.workers) as ex:
        for f in as_completed([ex.submit(build_one, i) for i in ids]):
            aid, st = f.result()
            print("%-24s %s" % (aid, st), flush=True)
            logf.write("%s %s %s\n" % (time.strftime("%H:%M:%S"), aid, st))
    if a.sheets:
        for n in range(0, len(ids), 5):
            subprocess.run([sys.executable, os.path.join(ROOT, "tools", "assets", "sheet.py")] + ids[n:n + 5] +
                           ["--renders", "--tile", "300", "-o", os.path.join(REF, "_review_%03d.png" % (n // 5))])


if __name__ == "__main__":
    main()
