#!/usr/bin/env python3
"""Grok reference images for the asset catalogue, in parallel.

    python3 tools/assets/grok_refs.py [ids...] [--workers 5] [--force] [--views side,front]

For each asset: the master side elevation (image_gen), then every other view (image_edit from the
master by its absolute path), each its own Grok call so the files are labelled exactly. Images land
in reference/grok/<id>/<view>.jpg (gitignored); the briefs in reference/grok/<id>/<view>.prompt.txt.
Skips views that already exist unless --force. Uses ~/.claude/skills/grok/ask_grok.sh (image mode:
Grok gets only its image tools).
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
ASK = os.path.expanduser("~/.claude/skills/grok/ask_grok.sh")
VEH = json.load(open(os.path.join(ROOT, "godot_project", "remake", "characters", "npc_vehicles.json")))["vehicles"]

UNPOWERED = {"child_bicycle", "cargo_bike", "adult_tricycle", "kick_scooter", "skateboard", "camper_trailer", "utility_trailer", "boat_trailer",
             "manual_wheelchair", "rollator", "baby_stroller", "child_wagon", "shopping_cart", "hand_truck", "pallet_jack", "luggage_cart",
             "housekeeping_cart", "hospital_gurney", "food_cart", "wheelbarrow", "semi_trailer_dry", "semi_trailer_reefer", "grain_cart", "hay_baler",
             "hay_wagon", "planter_drill", "manure_spreader", "plough_disc", "livestock_trailer", "low_loader", "boxcar", "covered_hopper", "tank_car",
             "flatcar", "reefer_car", "rescue_board", "rowboat_dinghy", "canoe_kayak", "barge", "pedal_boat", "surrey_bike", "hydroponics_harvest_cart",
             "sailboat"}
BOATS = {"lobster_boat", "trawler", "fishing_skiff", "rowboat_dinghy", "canoe_kayak", "sailboat", "pontoon_boat", "cabin_cruiser", "personal_watercraft",
         "ferry", "workboat_tug", "barge", "pedal_boat", "coast_guard_boat", "rescue_board"}
AIR = {"cargo_aerostat", "rescue_aerostat", "passenger_shuttle", "supply_freighter", "cargo_mule", "eva_sled"}

STYLE = ("Clean product-illustration style with realistic proportions, crisp edges and gentle painted shading, lit evenly by soft diffuse studio light, "
         "on a flat, plain, light grey background with no floor, no horizon, no scenery and no cast shadow. No people, and no text, letters, numbers or logos anywhere.")


def noun(aid):
    return VEH[aid]["name"].split("(")[0].split("/")[0].strip().lower()


def master_prompt(aid):
    look = catalog.ASSETS[aid][1]
    L, W, Hh = VEH[aid]["size_m"]
    design = "in the friendly 1970s retro-futurist industrial design of a sunny small-town world: soft rounded corners, clean panels, round lamps, cream and chrome accents"
    if aid not in UNPOWERED and aid not in AIR:
        design += ", fully electric, so it has no radiator grille, no exhaust pipes and no fuel cap"
    if aid in BOATS:
        view = ("Shown out of the water in a perfectly flat, exact side view from its right (starboard) side with the bow to the right, like a naval "
                "architect's profile drawing with no perspective, so the whole hull down to the keel is visible, centred with generous empty space around it.")
    elif aid in AIR:
        view = ("Shown in a perfectly flat, exact side view from its right side with the front to the right, like an engineering elevation drawing with no "
                "perspective, centred with generous empty space around it.")
    else:
        view = ("Shown in a perfectly flat, exact side view from its right side, facing right, like an engineering elevation drawing with no perspective: "
                "every wheel is a perfect circle, the front and back faces are not visible at all, and the whole thing is centred with generous empty space around it.")
    return "%s, %s. %s %s" % (look[0].upper() + look[1:], design, view, STYLE)


def edit_prompt(aid, view, master):
    same = "The same %s as in the reference image %s, exactly the same design, colours, parts and proportions, " % (noun(aid), master)
    tail = " Keep the flat, plain, light grey background, the soft even studio light, the clean product-illustration style, no cast shadow and no text."
    if view == "front":
        v = ("now seen perfectly head-on from the front, like a flat engineering front elevation with no perspective, centred, the whole width visible.")
    elif view == "rear":
        v = ("now seen perfectly straight on from the back, like a flat engineering rear elevation with no perspective, centred, the whole width visible.")
    elif view == "top":
        v = ("now seen from directly above, like a flat plan drawing with no perspective, the front pointing to the right, centred, the whole outline visible.")
    elif view == "interior_section":
        v = ("now drawn as a flat cutaway side elevation from its right side with the near wall and the near windows removed, front to the right, "
             "no perspective, exactly the same length, height, wheel and door positions as the reference, showing the whole passenger interior: the floor, "
             "every seat in profile, the ceiling and its lights, grab poles, hanging straps, the far wall with its windows, and the driver's cab. "
             "The ceiling is at least 2.2 metres above the floor everywhere. No people.")
    elif view == "interior_plan":
        v = ("now drawn as a flat plan view from directly above with the roof removed, front pointing to the right, no perspective, exactly the same "
             "length and width as the reference, showing the floor layout: every seat and bench in its place, the aisle, the doorways and the driver's cab, "
             "with the floor colour and pattern clearly visible. No people.")
    elif view == "interior_layout":
        return ("Redraw the reference image %s, this exact roof-off floor plan, as a flat colour-coded layout diagram with exactly the same outline, "
                "size and positions, front still pointing to the right: the floor plain white; every passenger seat drawn as its own solid pure red "
                "(#FF0000) rectangle exactly where that seat is (two seats side by side are two separate red rectangles with a thin white gap), each "
                "seat's backrest as a solid pure blue (#0000FF) strip along the edge it is on; the walls, the driver's cab and every other fitting solid "
                "black; each doorway a solid pure green (#00FF00) rectangle at the wall. No shading, no texture, no outlines, no text, no other colours, "
                "on a plain white background." % master)
    elif view == "interior_aisle":
        v = ("now seen from inside, standing at the back end in the middle of the aisle at eye height and looking straight forward down the whole length "
             "of the empty passenger interior to the driver's cab, a symmetrical one-point perspective: seats on both sides, floor, ceiling panels and "
             "lights, grab poles, straps, the windows. The ceiling is at least 2.2 metres above the floor. No people.")
    else:
        v = "now seen from a three-quarter front-left angle, slightly from above, so the front and the left side are both visible."
    return same + v + tail


def aspect(aid, view):
    L, W, Hh = VEH[aid]["size_m"]
    if view == "side":
        r = L / max(Hh, 0.1)
    elif view in ("front", "rear"):
        r = W / max(Hh, 0.1)
    elif view == "top":
        r = L / max(W, 0.1)
    elif view == "interior_section":
        r = L / max(Hh, 0.1)
    elif view in ("interior_plan", "interior_layout"):
        r = L / max(W, 0.1)
    else:
        return "4:3"
    return "16:9" if r > 1.5 else ("3:2" if r > 1.15 else ("1:1" if r > 0.85 else ("2:3" if r > 0.6 else "9:16")))


def run(aid, view, force=False):
    d = os.path.join(REF, aid)
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, view + ".jpg")
    if os.path.exists(out) and not force:
        return aid, view, "exists", 0.0
    master = os.path.join(d, "interior_plan.jpg" if view == "interior_layout" else "side.jpg")
    if view == "side":
        body = "Use image_gen exactly once with aspect ratio %s and this prompt, verbatim:\n\n%s\n\nMake no other images. Reply with one line." % (aspect(aid, view), master_prompt(aid))
    else:
        body = ("Use image_edit exactly once, with the single reference image at the absolute path %s, and this prompt, verbatim:\n\n%s\n\nMake no other images. Reply with one line."
                % (master, edit_prompt(aid, view, master if view == "interior_layout" else "")))
    pf = os.path.join(d, view + ".prompt.txt")
    open(pf, "w").write(body)
    cost = 0.0
    for attempt in range(2):
        r = subprocess.run([ASK, "-i", "1", "-m", "grok-4.7-build-fast", "-f", pf, "-o", os.path.join(d, view + ".md")], capture_output=True, text=True)
        img = os.path.join(d, view + "_img1.jpg")
        for line in r.stderr.splitlines():
            if "cost_usd:" in line:
                try:
                    cost += float(line.split("cost_usd:")[1].split(";")[0])
                except ValueError:
                    pass
        if os.path.exists(img):
            os.replace(img, out)
            for extra in [p for p in os.listdir(d) if p.startswith(view + "_img")]:
                os.remove(os.path.join(d, extra))
            return aid, view, "ok", cost
        time.sleep(3)
    return aid, view, "FAILED: " + r.stderr[-300:].replace("\n", " "), cost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--views")
    a = ap.parse_args()
    ids = a.ids or [k for k, v in catalog.ASSETS.items() if v[0] != "existing"]
    jobs_side = [(i, "side") for i in ids if (not a.views or "side" in a.views)]
    results = []
    tot = 0.0
    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        # masters first
        for f in as_completed([ex.submit(run, i, v, a.force) for i, v in jobs_side]):
            results.append(f.result())
            tot += results[-1][3]
            print("%-24s %-14s %s" % results[-1][:3], flush=True)
        rest = []
        for i in ids:
            for v in catalog.ASSETS[i][2]:
                if v != "side" and (not a.views or v in a.views.split(",")) and os.path.exists(os.path.join(REF, i, "side.jpg")):
                    rest.append((i, v))
        for f in as_completed([ex.submit(run, i, v, a.force) for i, v in rest]):
            results.append(f.result())
            tot += results[-1][3]
            print("%-24s %-14s %s" % results[-1][:3], flush=True)
    bad = [r for r in results if not r[2] in ("ok", "exists")]
    print("done: %d jobs, %d failed, %.0f s, reported cost $%.2f" % (len(results), len(bad), time.time() - t0, tot))


if __name__ == "__main__":
    main()
