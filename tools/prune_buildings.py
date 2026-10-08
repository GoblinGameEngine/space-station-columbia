#!/usr/bin/env python3
"""prune_buildings.py OLD_COASTAL_INVENTORY [--go] -- the built models (glb, LODs, mats sidecar) and catalog records of the
settlements the 1:1 regeneration replaced (tools/settlegen/towns.py, 2026-10-07): every id the old inventories gave a
regenerated town -- remake/inventory/map_inventory_pre_expansion.json, and the coastal inventory as it was before the run
(OLD_COASTAL_INVENTORY) -- that the new inventories neither place nor use as a model.  Lists what it would remove;
--go removes it.  Nothing else in remake/buildings is touched (hand-built models, crossings, farms, Calder, vehicles).
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "settlegen"))
import towns as TS  # noqa: E402

BLD = os.path.join(ROOT, "godot_project", "remake", "buildings")
CAT = os.path.join(ROOT, "remake", "catalog")
INV = os.path.join(ROOT, "remake", "inventory")


def main():
    old_ci = json.load(open(sys.argv[1]))
    go = "--go" in sys.argv
    replaced = {s["name"] for s in TS.SPECS}
    old = set()
    for st in json.load(open(os.path.join(INV, "map_inventory_pre_expansion.json")))["structures"]:
        if st.get("settlement") in replaced:
            old.add(st["id"])
    for st in old_ci["structures"]:
        if st.get("settlement") in replaced:
            old.add(st["id"])
    keep = set()
    for path in ("map_inventory.json", "coastal_inventory.json"):
        inv = json.load(open(os.path.join(INV, path)))
        for st in inv.get("structures", []):
            keep.add(st["id"])
            if st.get("model"):
                keep.add(st["model"])
        for c in inv.get("crossings", []):
            keep.add(c.get("id"))
            keep.add(c.get("model"))
    gone = sorted(old - keep)
    files = []
    for rid in gone:
        files += glob.glob(os.path.join(BLD, glob.escape(rid) + ".glb"))
        files += glob.glob(os.path.join(BLD, glob.escape(rid) + ".lod[123].glb"))
        files += glob.glob(os.path.join(BLD, glob.escape(rid) + ".glb.import"))
        files += glob.glob(os.path.join(BLD, glob.escape(rid) + ".lod[123].glb.import"))
        files += glob.glob(os.path.join(BLD, glob.escape(rid) + ".mats.json"))
        rec = os.path.join(CAT, rid + ".json")
        if os.path.exists(rec):
            try:
                gen = json.load(open(rec)).get("generated", "")
            except Exception:
                gen = ""
            if not gen.startswith("tools/settlegen ("):       # (a regenerated record of the same id is the new one)
                files.append(rec)
    mb = sum(os.path.getsize(f) for f in files) / 1e6
    print(f"{len(old)} old ids of the replaced towns, {len(gone)} no longer used: {len(files)} files, {mb:.0f} MB")
    for f in files[:12]:
        print("  ", os.path.relpath(f, ROOT))
    if go:
        for f in files:
            os.remove(f)
        print("removed")


if __name__ == "__main__":
    main()
