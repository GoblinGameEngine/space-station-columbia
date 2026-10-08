#!/usr/bin/env python3
"""Street names for every town street (the subdivision rules call for a street-name sign, D3-1, at every
intersection, and most of the map's streets had none). Ohio town conventions:

  - each town's longest main street is MAIN ST; its other main streets take the old commercial names
    (Front, Market, High, Water, Broadway, Mill, Harbor -- by the town's character)
  - streets running with Main are numbered by their distance from it, either side: 1st, 2nd ... (N 1st /
    S 1st when Main has streets on both sides)
  - cross streets take, in order along Main, the trees and then the founders' and great families'
    surnames (the bible's lineages): Elm St, Oak St ... Carrow St, Okafor St
  - a subdivision's loop is a Drive or Circle and its stub a Court, named for a bird, a lake word or a
    family (Heron Dr, Wren Ct)
  - alleys stay unnamed (MUTCD: an alley needs no name sign)
Names are unique within a town; roads already named (SR 14, Lakeshore Rd ...) keep theirs.

    python3 tools/street_names.py        (after tools/street_rules.py; then road_furniture.py)
"""
import hashlib
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bible"))
import canon_lineages as LI  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
GD = os.path.join(ROOT, "godot_project", "remake")
TREES = ["Elm", "Oak", "Maple", "Walnut", "Cherry", "Chestnut", "Locust", "Spruce", "Pine", "Sycamore", "Hickory", "Ash", "Linden",
         "Birch", "Poplar", "Beech", "Willow", "Cedar", "Buckeye", "Tamarack"]
MAIN_ALT = ["Front", "Market", "High", "Water", "Broadway", "Mill", "Harbor", "Church", "Court", "Union"]
SUB_WORDS = ["Heron", "Wren", "Lark", "Kestrel", "Tern", "Plover", "Bluebird", "Cardinal", "Goldfinch", "Meadowlark", "Shoreline",
             "Lakeview", "Bayview", "Driftwood", "Sandpiper", "Juniper", "Clover", "Fox Run", "Orchard", "Mill Pond"]
ORD = lambda n: "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def h(*k):
    return int(hashlib.blake2b("|".join(map(str, k)).encode(), digest_size=6).hexdigest(), 16)


def main():
    ter_p = os.path.join(GD, "terrain.json")
    ter = json.load(open(ter_p))
    C = 2 * math.pi * ter["R"]
    wrap = lambda d: (d + C / 2) % C - C / 2
    families = [l["surname"] for l in LI.LINEAGES if " " not in l["surname"] and "-" not in l["surname"]]
    places = json.load(open(os.path.join(GD, "placement.json")))["structures"]
    centre = {}
    for e in places:
        if e.get("settlement"):
            centre.setdefault(e["settlement"], []).append((e["s"], e["x"]))
    for k, v in centre.items():
        s0 = v[0][0]
        centre[k] = (s0 + sum(wrap(p[0] - s0) for p in v) / len(v), sum(p[1] for p in v) / len(v))
    town_of = {}
    for ri, rd in enumerate(ter["roads"]):
        if rd["cls"] not in ("street", "main") or rd.get("xs") in (None, "rural"):
            continue
        mid = rd["pts"][len(rd["pts"]) // 2]
        best = min(centre.items(), key=lambda kv: math.hypot(wrap(kv[1][0] - mid[0]), kv[1][1] - mid[1]))
        town_of[ri] = best[0]
    by_town = defaultdict(list)
    for ri, t in town_of.items():
        by_town[t].append(ri)
    named = 0
    for town, ris in sorted(by_town.items()):
        used = {ter["roads"][r]["name"] for r in ris if ter["roads"][r].get("name")}

        nxt = {}

        def take(name):
            # (a numbered street's second run is "5th St Ext", its third "5th St Ext 2": it was " Ext" every time, a
            # loop without end once the 1:1 towns needed a third; and the counter starts where it left off)
            base = name
            k = nxt.get(base, 2)
            while name in used:
                if base[0].isdigit():
                    name = base + " Ext" if k == 2 else "%s Ext %d" % (base, k - 1)
                else:
                    name = "%s %d" % (base, k)
                k += 1
            nxt[base] = k
            used.add(name)
            return name

        def length(rd):
            return sum(math.hypot(wrap(b[0] - a[0]), b[1] - a[1]) for a, b in zip(rd["pts"], rd["pts"][1:]))

        def direction(rd):
            a, b = rd["pts"][0], rd["pts"][-1]
            ds, dx = wrap(b[0] - a[0]), b[1] - a[1]
            L = math.hypot(ds, dx) or 1.0
            return (ds / L, dx / L)
        mains = sorted([r for r in ris if ter["roads"][r]["cls"] == "main"], key=lambda r: -length(ter["roads"][r]))
        if mains:
            main_rd = ter["roads"][mains[0]]
        else:
            main_rd = max((ter["roads"][r] for r in ris), key=length)
        md = direction(main_rd)
        mn = (-md[1], md[0])
        m0 = main_rd["pts"][len(main_rd["pts"]) // 2]
        for k, r in enumerate(mains):
            rd = ter["roads"][r]
            if not rd.get("name"):
                rd["name"] = take("Main St" if k == 0 else "%s St" % MAIN_ALT[(k - 1 + h(town)) % len(MAIN_ALT)])
                named += 1
        # the rest: subdivision streets, then streets with Main (numbered) or across it (trees, families)
        para, cross = [], []
        for r in ris:
            rd = ter["roads"][r]
            if rd.get("name"):
                continue
            mid = rd["pts"][len(rd["pts"]) // 2]
            off = wrap(mid[0] - m0[0]) * mn[0] + (mid[1] - m0[1]) * mn[1]
            along = wrap(mid[0] - m0[0]) * md[0] + (mid[1] - m0[1]) * md[1]
            if rd.get("xs") == "street/subdivision":
                closed = math.hypot(wrap(rd["pts"][0][0] - rd["pts"][-1][0]), rd["pts"][0][1] - rd["pts"][-1][1]) < 5.0
                word = SUB_WORDS[h(town, r) % len(SUB_WORDS)] if h(town, r, "f") % 3 else families[h(town, r) % len(families)]
                suffix = ("Dr" if h(town, r, "d") % 2 else "Cir") if closed else ("Ct" if length(rd) < 120 else "Way")
                rd["name"] = take("%s %s" % (word, suffix))
                named += 1
                continue
            d = direction(rd)
            if abs(d[0] * md[0] + d[1] * md[1]) > 0.8:
                para.append((off, r))
            else:
                cross.append((along, r))
        sides = {s for s in (1 if o > 0 else -1 for o, _ in para)}
        for sg in (1, -1):
            row = sorted([(abs(o), r) for o, r in para if (o > 0) == (sg > 0)])
            n = 0
            last = None
            for o, r in row:
                if last is None or o - last > 25.0:
                    n += 1
                last = o
                pre = ("N " if sg < 0 else "S ") if len(sides) > 1 else ""
                ter["roads"][r]["name"] = take("%s%s St" % (pre, ORD(n)))
                named += 1
        pool = TREES + families[h(town) % 7:] + families[:h(town) % 7]
        for k, (a, r) in enumerate(sorted(cross)):
            ter["roads"][r]["name"] = take("%s St" % pool[k % len(pool)] if k < len(pool) else "%s Ave" % pool[k % len(pool)])
            named += 1
    json.dump(ter, open(ter_p, "w"), indent=0)
    print("street names: %d streets named in %d towns" % (named, len(by_town)))


if __name__ == "__main__":
    main()
