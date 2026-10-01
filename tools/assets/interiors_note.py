#!/usr/bin/env python3
"""Write tools/assets/INTERIORS.md: how each vehicle's interior was made (read from the build logs in
reference/grok/<id>/build/blender.log). Run after a build:  python3 tools/assets/interiors_note.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import catalog

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = json.load(open(os.path.join(ROOT, "godot_project", "remake", "characters", "npc_vehicles.json")))["vehicles"]
OPEN = {"motorcycle", "scooter_moped", "mobility_scooter", "riding_mower", "parks_mower", "atv", "utv", "forklift", "utility_tractor",
        "fishing_skiff", "canoe_kayak", "sailboat", "pontoon_boat", "personal_watercraft", "pedal_boat", "bumper_car", "eva_sled",
        "utility_cart", "rowboat_dinghy"}

grok, hand, extra, none_open, none_enclosed = [], [], [], [], []
for aid, (fam, look, views) in catalog.ASSETS.items():
    name = V[aid]["name"]
    if fam == "transit":
        grok.append(aid)
        continue
    if fam == "existing":
        hand.append(aid)
        continue
    if not V[aid].get("seats"):
        continue
    if fam == "frame":
        none_open.append(aid)
        continue
    log = os.path.join(ROOT, "reference", "grok", aid, "build", "blender.log")
    txt = open(log).read() if os.path.exists(log) else ""
    line = next((l for l in txt.splitlines() if l.startswith("INTERIOR")), "")
    if line.startswith("INTERIOR extrapolated"):
        p = line.split()
        est = "estimated from the shape" if ("WINDOWS extrapolated " + aid) in txt else "found in the drawing"
        extra.append((aid, p[3], p[4], est))
    elif aid in OPEN:
        none_open.append(aid)
    else:
        none_enclosed.append(aid)

md = ["# Vehicle interiors: how each was made", "",
      "Written by `tools/assets/interiors_note.py` from the build logs. The user's call (2026-09-30): interiors are **extrapolated** from the "
      "exterior references where Grok made no interior views; any we don't like go back to Grok (`grok_refs.py <id> --views "
      "interior_section,interior_plan,interior_aisle,interior_layout`, then build them as `transit`-style interiors).", "",
      "## From Grok's interior views (%d)" % len(grok), "", ", ".join("`%s`" % a for a in grok), "",
      "## Hand-built with the model (%d)" % len(hand), "", ", ".join("`%s`" % a for a in hand) + " (remake/blender/vehicles; the bicycle has none)", "",
      "## Extrapolated (%d): kit/cabin.py" % len(extra), "",
      "Glazing cut into the windows, the cabin hollowed and lined, carpet, seats in rows to the seat count, a dash with gauges and the "
      "wheel on the left, in a 1970s scheme (grey vinyl for work vehicles).", "",
      "| vehicle | scheme | seats | windows |", "|---|---|---|---|"]
md += ["| `%s` | %s | %s | %s |" % e for e in extra]
md += ["", "## No interior", "",
       "**Open, the seats are part of the model (%d):** %s" % (len(none_open), ", ".join("`%s`" % a for a in none_open)), "",
       "**Enclosed, no windows found or the cut failed: candidates for Grok interior views (%d):** %s" % (len(none_enclosed), ", ".join("`%s`" % a for a in none_enclosed)), ""]
open(os.path.join(ROOT, "tools", "assets", "INTERIORS.md"), "w").write("\n".join(md))
print("grok %d, hand %d, extrapolated %d, open %d, enclosed without %d" % (len(grok), len(hand), len(extra), len(none_open), len(none_enclosed)))
