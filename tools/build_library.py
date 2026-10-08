#!/usr/bin/env python3
"""build_library.py [-j N] [--prefix P ...] [--force] -- build every catalog record that is its own model (a record with
"model" pointing at another is placed as that one: tools/settlegen/city.py library_key) and has no glb newer than its
record, in N parallel Blender batches (each builds, audits and writes its LODs: build_record.py).  Logs per batch in
reference/tmp/build_logs/; a summary of what failed at the end (rerun picks up only what is missing).

  ~/.venvs/ssc-assets/bin/python tools/build_library.py -j 4 --prefix SOL- --prefix HF-
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, "remake", "catalog")
OUT = os.path.join(ROOT, "godot_project", "remake", "buildings")
LOGS = os.environ.get("BUILD_LOGS") or os.path.join(ROOT, "reference", "tmp", "build_logs")
BATCH = 40                       # records per Blender run (a fresh Blender every so often: its memory creeps)


def todo(prefixes, force):
    out = []
    for p in sorted(glob.glob(os.path.join(CAT, "*.json"))):
        rid = os.path.basename(p)[:-5]
        if prefixes and not any(rid.startswith(x) for x in prefixes):
            continue
        try:
            rec = json.load(open(p))
        except Exception:
            continue
        if not rec.get("generated", "").startswith("tools/settlegen ("):
            continue
        if rec.get("model", rid) != rid:
            continue                                  # placed as another record's model
        glb = os.path.join(OUT, rid + ".glb")
        lod = os.path.join(OUT, rid + ".lod3.glb")
        if not force and os.path.exists(glb) and os.path.exists(lod) and os.path.getmtime(glb) >= os.path.getmtime(p):
            continue
        out.append(rid)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=4)
    ap.add_argument("--prefix", action="append", default=[])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    ids = todo(a.prefix, a.force)
    print(f"{len(ids)} records to build", flush=True)
    if a.list or not ids:
        return
    os.makedirs(LOGS, exist_ok=True)
    script = os.path.join(ROOT, "remake", "blender", "build_record.py")
    batches = [ids[i:i + BATCH] for i in range(0, len(ids), BATCH)]
    running = []
    failed = []
    done = 0
    t0 = time.time()
    n = 0
    while batches or running:
        while batches and len(running) < a.j:
            b = batches.pop(0)
            n += 1
            log = open(os.path.join(LOGS, f"batch_{n:04d}.log"), "w")
            p = subprocess.Popen(["flatpak", "run", "org.blender.Blender", "-b", "--factory-startup", "--python", script, "--"] + b,
                                 stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
            running.append((p, b, log, n))
        time.sleep(2)
        for r in list(running):
            p, b, log, k = r
            if p.poll() is None:
                continue
            running.remove(r)
            log.close()
            txt = open(log.name).read()
            bad = [ln.split()[1] for ln in txt.splitlines() if ln.startswith("FAILED ") and len(ln.split()) == 2]
            if p.returncode != 0 and "BUILT " not in txt:
                bad = b                                # Blender itself died: the whole batch
            failed += bad
            done += len(b)
            el = time.time() - t0
            print(f"batch {k}: {len(b) - len(bad)}/{len(b)} ok  [{done}/{len(ids)}, {el / 60:.0f} min, "
                  f"~{el / done * (len(ids) - done) / 60:.0f} min left]", flush=True)
    print(f"DONE {len(ids) - len(failed)} built, {len(failed)} failed: {' '.join(failed[:60])}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
