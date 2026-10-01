#!/usr/bin/env python3
"""Build the station's lawbooks of the street: godot_project/remake/law/*.json (the engine) and
research/law/*.md (to read), from tools/law/canon_law.py and the bible's settlements.

    python3 tools/law/make_law.py

Also derives each city's street cross-sections (cross_sections in ordinances.json), which
tools/street_rules.py applies to the map's roads.
"""
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bible"))
import canon_law as LAW  # noqa: E402
import canon_world as WO  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
OUT = os.path.join(ROOT, "godot_project", "remake", "law")
DOCS = os.path.join(ROOT, "research", "law")
PARK = 2.4            # m: a parking lane (8 ft)
LANE_MIN = 2.9        # m: the narrowest travel lane we accept beside parking


def tier(pop):
    for name, lo in LAW.TIERS:
        if pop >= lo:
            return name
    return "hamlet"


def cross_sections(c):
    """The city's street cross-sections, by class and context: carriageway (curb to curb, parking
    included), parking sides, tree lawn and walk widths (m)."""
    st = c["streets"]
    p = c["parking"]["residential"]
    sw = c["sidewalks"]

    def parking_for(cc):
        """The ordinance's sides, but never so many that a travel lane falls under LANE_MIN (our
        drivers keep to their own lanes: no yield streets)."""
        legal = 2 if cc >= p["both_sides_min_m"] - 0.01 else (1 if cc >= p["one_side_min_m"] - 0.01 else 0)
        fits = 2 if cc - 2 * PARK >= 2 * LANE_MIN else (1 if cc - PARK >= 2 * 2.75 else 0)
        return min(legal, fits)
    main_cc = st["main_curb_to_curb_m"]
    local_cc = st["local_curb_to_curb_m"]
    sub = LAW.SUBDIVISION["local_street"]
    xs = {
        "main/core": {"w": main_cc, "park": 2, "lawn": 0.0, "walk": sw["core_min_m"], "angle": bool(c["parking"].get("angle_parking"))},
        "main/town": {"w": main_cc, "park": 2, "lawn": 0.0, "walk": sw["core_min_m"] * 0.8, "angle": False},
        "street/core": {"w": max(local_cc, 2 * LANE_MIN + 2 * PARK), "park": 2, "lawn": 0.0, "walk": sw["core_min_m"] * 0.8, "angle": False},
        "street/town": {"w": local_cc, "park": parking_for(local_cc), "lawn": sw["tree_lawn_m"], "walk": sw["residential_walk_m"], "angle": False},
        "street/subdivision": {"w": sub["pavement_back_to_back_m"], "park": parking_for(sub["pavement_back_to_back_m"]), "lawn": 1.2, "walk": 1.5, "angle": False},
        "county/town": {"w": 8.0, "park": 0, "lawn": sw["tree_lawn_m"], "walk": sw["residential_walk_m"], "angle": False},
        "county/core": {"w": 8.0, "park": 0, "lawn": 0.0, "walk": sw["core_min_m"] * 0.8, "angle": False},
        "hwy/town": {"w": 12.0, "park": 0, "lawn": sw["tree_lawn_m"], "walk": sw["residential_walk_m"], "angle": False},
        "hwy/core": {"w": 12.0, "park": 0, "lawn": 0.0, "walk": sw["core_min_m"] * 0.8, "angle": False},
        "alley": {"w": 3.0, "park": 0, "lawn": 0.0, "walk": 0.0, "angle": False},
        "rural": {"w": None, "park": 0, "lawn": 0.0, "walk": 0.0, "angle": False},
    }
    for k, v in xs.items():
        if v["w"] is not None:
            v["w"] = round(v["w"], 2)
            v["walk"] = round(v["walk"], 2)
            v["lawn"] = round(v["lawn"], 2)
            v["travel_lane"] = round((v["w"] - v["park"] * PARK) / 2.0, 2)
            assert v["travel_lane"] >= 1.4, (c["id"], k, v)
    return xs


def settlement_centres():
    pl = json.load(open(os.path.join(ROOT, "godot_project", "remake", "placement.json")))["structures"]
    C = 2 * math.pi * 3000.0
    by = {}
    for e in pl:
        if e.get("settlement"):
            by.setdefault(e["settlement"], []).append(e)
    out = {}
    for name, es in by.items():
        sm = statistics.median(e["s"] for e in es)
        ds = [(e["s"] - sm + C / 2) % C - C / 2 for e in es]
        out[name] = (round((sm + statistics.median(ds)) % C, 1), round(statistics.median(e["x"] for e in es), 1))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(DOCS, exist_ok=True)
    errors = []
    cities = {c["id"]: c for c in LAW.CITIES}
    sets = {s["id"]: s for s in WO.SETTLEMENTS if s["id"] != "countryside"}
    for sid, cid, _ in LAW.GOVERNED:
        if sid not in sets:
            errors.append("governed: unknown settlement %s" % sid)
        if cid not in cities:
            errors.append("governed: unknown city %s" % cid)
    for c in LAW.CITIES:
        if c["id"] not in sets:
            errors.append("city not a settlement: %s" % c["id"])
        if c["state"] not in LAW.STATE:
            errors.append("city %s: state %s" % (c["id"], c["state"]))
    gov = {sid: (cid, why) for sid, cid, why in LAW.GOVERNED}
    for sid in sets:
        if sid not in cities and sid not in gov:
            errors.append("settlement %s governed by no city" % sid)
    if errors:
        print("\n".join("ERROR " + e for e in errors))
        sys.exit(1)
    centres = settlement_centres()
    C = 2 * math.pi * 3000.0
    table = []
    for sid, s in sets.items():
        cid, why = (sid, "its own large city") if sid in cities else gov[sid]
        here = centres.get(s["name"])
        there = centres.get(cities[cid]["name"])
        dist = None
        if here and there:
            dist = round(math.hypot((here[0] - there[0] + C / 2) % C - C / 2, here[1] - there[1]) / 1000.0, 2)
        t = tier(s["pop"])
        table.append({"id": sid, "name": s["name"], "pop": s["pop"], "tier": t, "region": s["region"], "governed_by": cid,
                      "law_of": cities[cid]["basis_city"], "state": cities[cid]["state"], "distance_km": dist, "ties": why,
                      "centre": here, "fast_travel": t in LAW.FAST_TRAVEL_TIERS})
    table.sort(key=lambda r: -r["pop"])
    ords = {"_about": "The station's street ordinances (tools/law/canon_law.py; research/law/). Each city's rules are the station's own law modelled on its basis city; the state baselines quote the Ohio Revised Code.",
            "state": LAW.STATE, "cities": [dict(c, cross_sections=cross_sections(c)) for c in LAW.CITIES],
            "subdivision": LAW.SUBDIVISION, "park_lane_m": PARK,
            "tram_stop_zone": LAW.TRAM_STOP_ZONE}
    files = {"ordinances": ords, "settlements": {"settlements": table, "tiers": LAW.TIERS, "fast_travel_tiers": list(LAW.FAST_TRAVEL_TIERS)},
             "signs": {"signs": [dict(zip(("code", "name", "legend", "colours", "use"), s)) for s in LAW.SIGNS],
                       "transit_flags": {c["id"]: c["transit"] for c in LAW.CITIES}},
             "zoning": LAW.ZONING, "building_code": LAW.BUILDING_CODE, "design": {"rules": LAW.DESIGN_RULES, "scholarship": LAW.SCHOLARSHIP}}
    for k, v in files.items():
        with open(os.path.join(OUT, k + ".json"), "w") as f:
            json.dump(v, f, indent=1, ensure_ascii=False)
    write_docs(ords, table, files)
    print("law: %d cities, %d settlements (%d fast-travel), %d signs" % (len(LAW.CITIES), len(table), sum(r["fast_travel"] for r in table), len(LAW.SIGNS)))


def md_table(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return out


def write_docs(ords, table, files):
    W = lambda name, lines: open(os.path.join(DOCS, name), "w").write("\n".join(lines) + "\n")
    W("README.md", [
        "# The station's laws of the street", "",
        "Built by `tools/law/make_law.py` from `tools/law/canon_law.py`; the engine reads `godot_project/remake/law/*.json`.",
        "These pages are the source for the in-game lawbooks and legal system to come.", "",
        "| page | what |", "|---|---|",
        "| [01_state.md](01_state.md) | the state baselines (Ohio Revised Code; Indiana for Oceanview) |",
        "| [02_cities.md](02_cities.md) | the six large cities' ordinances: parking, sidewalks, streets, speeds, transit stop flags |",
        "| [03_settlements.md](03_settlements.md) | every settlement, its tier, the city whose law it follows, and fast-travel |",
        "| [04_signs.md](04_signs.md) | the sign catalogue (MUTCD codes) and each city's transit stop flag |",
        "| [05_subdivisions.md](05_subdivisions.md) | the Regional Planning Boards' subdivision rules |",
        "| [06_zoning_and_building.md](06_zoning_and_building.md) | zoning districts and the building code tokens |",
        "| [07_planning_literature.md](07_planning_literature.md) | walkable, urban and suburban development: the scholarship and the rules taken from it |", "",
        "## Sources and their weight",
        "- **Fetched (2026-10-01):** the Ohio Revised Code from codes.ohio.gov (4511.21, 4511.68, 4511.69, 711.05, 711.10, 729.01, 3781.01); the MUTCD's Part 2B (FHWA); Wikipedia's pages on walkability, New Urbanism, suburbanisation, transit-oriented development, the cul-de-sac and Jacobs's book.",
        "- **Not reachable:** the cities' codified ordinances. Municode and American Legal refuse automated readers, and the session's web-search budget ran out. Each city's variant is therefore **the station's own law**, modelled on what its basis city is known for and on common Ohio and Indiana municipal practice. Nothing here claims to quote a real city ordinance.",
        "- **From knowledge (marked):** the Indiana Code baselines; the model building codes' numbers (IBC/IRC as adopted by Ohio and Indiana: the ICC texts are copyrighted); subdivision and zoning values in the range Ohio and Indiana regulations use.",
        "- A later pass with web search can check the city rules against the real ordinances and replace any that should follow them more closely."])
    L = ["# 1. The state baselines", ""]
    for k, st in ords["state"].items():
        L += ["## %s" % st["name"], "", "**Speeds:** %s" % ", ".join("%s %s" % (a, b) for a, b in st["speed"].items()), "",
              "**No parking (%s):**" % st.get("no_parking_source", ""), ""]
        L += ["- %s%s" % (n.replace("_", " "), (" -- %.1f m" % d) if d else "") for n, d in st["no_parking"]]
        L += ["", "**Parking position:** %s" % json.dumps(st["parking_position"], ensure_ascii=False), "",
              "**Sidewalks:** %s" % st["sidewalks"]["duty"], "", "**Subdivisions:** %s" % json.dumps(st["subdivision"], ensure_ascii=False), "",
              "**Building:** %s" % json.dumps(st["building"], ensure_ascii=False), ""]
    W("01_state.md", L)
    L = ["# 2. The six large cities", "", "Each city's rules are the station's own, modelled on its basis city (see README).", ""]
    for c in ords["cities"]:
        p = c["parking"]
        L += ["## %s (law modelled on %s; %s)" % (c["name"], c["basis_city"], c["code"]), "", c["character"] + ".", "",
              "**Transit:** %s. Stop flag: %s (%s)." % (c["transit"]["authority"], c["transit"]["stop_flag"], c["transit"]["shape"]), "",
              "**Downtown parking (%s):** meters %s, %s, %d-hour limit, %s." % (p["code_section"], "yes" if p["downtown"]["meters"] else "no", p["downtown"]["hours"], p["downtown"]["limit_h"], p["downtown"]["pay"]),
              "**Residential parking:** both sides where the street is %.1f m or wider, one side from %.1f m, none narrower; overnight %s; at most %d hours; sweeping: %s." % (
                  p["residential"]["both_sides_min_m"], p["residential"]["one_side_min_m"], "allowed" if p["residential"]["overnight"] else "no", p["residential"]["max_hours"], p["residential"]["sweeping"]),
              "**Special:** " + "; ".join(p["special"]) + ".", "**Angle parking:** %s. **Permit zones:** %s." % ("yes" if p["angle_parking"] else "no", ", ".join(p["permit_zones"]) or "none"), "",
              "**Sidewalks (%s):** downtown at least %.1f m from kerb to building; residential %.1f m walks behind a %.1f m tree lawn; %s." % (
                  c["sidewalks"]["code_section"], c["sidewalks"]["core_min_m"], c["sidewalks"]["residential_walk_m"], c["sidewalks"]["tree_lawn_m"], c["sidewalks"]["required"]), "",
              "**Speeds (km/h):** %s" % ", ".join("%s %s" % kv for kv in c["speed"].items()), "", "**Cross-sections:**", ""]
        L += md_table([(k, v["w"], v.get("travel_lane", "-"), v["park"], v["lawn"], v["walk"], "angle" if v["angle"] else "") for k, v in c["cross_sections"].items() if v["w"]],
                      ["street / context", "kerb to kerb m", "travel lane m", "parking sides", "tree lawn m", "walk m", ""])
        L.append("")
    z = LAW.TRAM_STOP_ZONE
    L += ["## Every city: tram stop zones", "", "No stopping or parking within %.1f m either side of a tram stop, on %s; %s; %s. Basis: %s." % (
        z["half_length_m"], "both kerbs" if z["both_kerbs"] else "the stop's kerb", z["sign"], z["paint"], z["basis"]), ""]
    W("02_cities.md", L)
    W("03_settlements.md", ["# 3. Settlements and the law they follow", "",
                            "Tiers: city 20,000+; town 10,000+; village 4,000+; hamlet below. Fast travel (the Navigation app) serves the two largest tiers, at their tram stops.", ""] +
      md_table([(r["name"], r["pop"], r["tier"], r["region"], r["governed_by"].replace("_", " ").title(), r["law_of"], r["distance_km"] or "-", r["ties"], "yes" if r["fast_travel"] else "")
                for r in table], ["settlement", "population", "tier", "region", "follows", "law modelled on", "km", "ties", "fast travel"]))
    L = ["# 4. Signs", "", "All signs follow the US standard (MUTCD codes); legends in the station's metric.", ""]
    L += md_table([(s["code"], s["name"], s["legend"], s["colours"], s["use"]) for s in files["signs"]["signs"]], ["code", "name", "legend", "colours", "use"])
    L += ["", "## Transit stop flags (each city's authority's own design)", ""]
    L += md_table([(cid, f["authority"], f["stop_flag"], f["shape"], " ".join(f["colours"])) for cid, f in files["signs"]["transit_flags"].items()],
                  ["city", "authority", "flag", "shape", "colours"])
    W("04_signs.md", L)
    sub = LAW.SUBDIVISION
    L = ["# 5. Subdivisions", "", sub["_about"], ""]
    for k, v in sub.items():
        if k.startswith("_"):
            continue
        L.append("- **%s:** %s" % (k.replace("_", " "), json.dumps(v, ensure_ascii=False)))
    W("05_subdivisions.md", L)
    L = ["# 6. Zoning and the building code", "", LAW.ZONING["_about"], ""]
    L += md_table([(k, v["use"], v.get("front_m", "-"), v.get("side_m", "-"), v.get("rear_m", "-"), v.get("max_height_m", "-"), v.get("max_coverage", "-")) for k, v in LAW.ZONING["districts"].items()],
                  ["district", "use", "front m", "side m", "rear m", "height m", "coverage"])
    L += ["", "## Building code tokens", "", LAW.BUILDING_CODE["_about"], ""]
    for k, v in LAW.BUILDING_CODE.items():
        if not k.startswith("_"):
            L.append("- **%s:** %s" % (k, json.dumps(v, ensure_ascii=False)))
    W("06_zoning_and_building.md", L)
    L = ["# 7. The planning literature", ""]
    for k, rows in LAW.SCHOLARSHIP.items():
        L += ["## %s development" % k.title(), ""] + md_table(rows, ["author / year", "work", "what we take"]) + [""]
    L += ["## Rules the generator applies", ""] + ["- **%s:** %s" % (k, json.dumps(v, ensure_ascii=False)) for k, v in LAW.DESIGN_RULES.items() if not k.startswith("_")]
    W("07_planning_literature.md", L)


if __name__ == "__main__":
    main()
