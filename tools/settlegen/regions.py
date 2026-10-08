#!/usr/bin/env python3
"""regions.py -- the two coasts' building styles over the Great Lakes records (the user, 2026-10-07: the North Sea's towns
"New England", the South Sea's "California ... houses and buildings with tile roofs and stucco walls ... only for coastal
towns, cities, and nearby settlements. It will transition to the great lakes aesthetic toward the river";
research/terrain_and_cities/README.md sections 3 and 4).

    apply(rec, region, r)   -- re-style a records.make_record() record for "ne" or "ca" ("gl" is left as made)

California (Spanish Colonial Revival, Mission Revival, Monterey; Santa Barbara's El Pueblo Viejo, San Clemente): smooth
stucco (white, cream, sand, pale pastels), red clay barrel-tile roofs at low pitch, deep-set dark-wood windows and doors,
wrought iron; one-storey Spanish bungalows and two-storey Monterey houses; mission parapets on the commercial and civic
buildings.  New England (Cape Cod, saltbox, Federal/colonial, Greek Revival, Shingle Style; coastal Maine, Marblehead):
white or grey clapboard and weathered cedar shingle, steep dark roofs (asphalt, wood shingle, some slate), granite
foundations, white trim, black or green shutters, brick for downtown blocks.
"""

CA_BODY = ["#f4f0e6", "#efe6d2", "#e9dcc2", "#f2e8dc", "#e6d4bb", "#f0e2cf", "#ead9c8", "#f3eadb", "#e4cfb2", "#efd9c4",
           "#e8d8c0", "#f6f1e7", "#dcc7a6", "#e9d6c8"]
CA_TRIM = ["#3b2a1e", "#4a3324", "#2f3b2a", "#5a3a28", "#2e2a26"]          # dark wood, iron
CA_ACCENT = ["#2f5e5a", "#6a2c22", "#1f4a6e", "#8a4a20", "#2c4a2e"]        # door / shutter accents (tile, glaze colours)
NE_BODY_CLAP = ["#f6f5f0", "#f2f1ea", "#e9e8e2", "#d9dcd8", "#c9cfcf", "#f1ead2", "#e8dcc0", "#8a2e24", "#2f3e52", "#5b6b5a",
                "#f4f2e8", "#e6e2d8"]
NE_SHINGLE = ["#8a8378", "#7d776d", "#9a9184", "#6f6a62"]                  # weathered cedar greys
NE_TRIM = ["#f7f6f0", "#f4f3ec", "#ffffff"]
NE_ACCENT = ["#1d1f22", "#24382a", "#3a2a24", "#1f2e44", "#7a1f1a"]       # black / green shutters, red and navy doors

CA_HOUSE = {"spanish_revival": 6, "california_bungalow": 3, "ranch": 2, "minimal_traditional": 0.6}
NE_HOUSE = {"cape_cod": 5, "i_house": 3, "gable_front": 2.5, "shingle_style": 1.5, "nantucket_cape": 1.5, "dutch_colonial": 0.6,
            "foursquare": 0.8}


def _wpick(r, w):
    tot = sum(w.values())
    x = r.random() * tot
    for k, v in w.items():
        x -= v
        if x <= 0:
            return k
    return k


ISLE_BODY = ["#f8f7f2", "#f6f4ec", "#eef2f4", "#f3ede0", "#e9f0e6", "#f5e9e4", "#eef0f6", "#fbf5e6"]      # whites and soft pastels
ISLE_TRIM = ["#ffffff", "#f7f6f0"]
ISLE_ACCENT = ["#1f4a33", "#244d3a", "#1a3d2c", "#2b4f6e"]                                      # the island's green shutters


def apply(rec, region, r):
    if region == "isle":
        return _isle(rec, r)
    if region not in ("ca", "ne"):
        return rec
    k = rec.get("kind")
    tr = rec.setdefault("traits", {})
    rec["region"] = region
    if k == "house":
        _house(tr, region, r)
    elif k in ("store",):
        _store(tr, region, r)
    elif k in ("condo", "townhouse"):
        _multi(tr, region, r)
    elif k in ("civic", "school", "church"):
        _civic(tr, region, r, k)
    elif k == "clubhouse" and region == "ca":
        tr.update(archetype="spanish_revival", walls="stucco", roof={"type": "hip", "pitch_deg": 20, "material": "clay_tile"},
                  colors={"body": r.choice(CA_BODY), "trim": r.choice(CA_TRIM), "accent": r.choice(CA_ACCENT)})
    elif k in ("strip", "bigbox"):
        tr["region"] = region
        if region == "ca":
            tr["walls"] = "stucco"
            tr["roof_trim"] = "clay_tile"
    return rec


def _house(tr, region, r):
    st = tr.get("storeys", 1)
    if region == "ca":
        arch = _wpick(r, CA_HOUSE)
        if arch == "spanish_revival" and r.random() < 0.3:
            st = 2                                              # (the two-storey Monterey: a balconied front)
            tr["balcony"] = "monterey"
        elif arch in ("spanish_revival", "california_bungalow", "ranch") or st == 1.5:
            st = 1                                              # (a 16-24 degree tile roof has no half-storey under it)
        tr["archetype"] = arch
        tr["storeys"] = st
        tr["walls"] = "stucco" if r.random() < 0.9 else "board_and_batten"
        roof = tr.setdefault("roof", {})
        roof["material"] = "clay_tile" if r.random() < 0.9 else "clay_tile_old"
        roof["pitch_deg"] = r.randint(16, 24)
        roof["type"] = "hip" if arch == "ranch" and r.random() < 0.5 else ("gable" if r.random() < 0.7 else "hip")
        c = tr.setdefault("colors", {})
        c["body"] = r.choice(CA_BODY)
        c["trim"] = r.choice(CA_TRIM)
        c["accent"] = r.choice(CA_ACCENT)
        c["roof"] = "#a8492f"
        tr["porch"] = {"type": r.choice(["stoop", "front_partial", "stoop"]), "posts": "square", "rail": "none"}
        tr["dormers"] = []
        tr["chimneys"] = [] if r.random() < 0.5 else ["exterior_left"]
        tr["foundation"] = "slab"
        tr["form_token"] = arch
    else:
        arch = _wpick(r, NE_HOUSE)
        if arch in ("cape_cod", "nantucket_cape"):
            st = 1.5
        elif arch in ("i_house", "shingle_style", "gable_front", "foursquare", "dutch_colonial"):
            st = 2
        tr["archetype"] = arch
        tr["storeys"] = st
        shingle = arch in ("shingle_style", "nantucket_cape") or r.random() < 0.3
        tr["walls"] = "cedar_shingle" if shingle else "clapboard"
        roof = tr.setdefault("roof", {})
        roof["material"] = _wpick(r, {"asphalt_shingle": 6, "wood_shingle": 2.5, "slate": 1})
        roof["pitch_deg"] = r.randint(38, 50) if arch != "foursquare" else r.randint(26, 32)
        roof["type"] = {"dutch_colonial": "gambrel", "foursquare": "hip"}.get(arch, "gable")
        c = tr.setdefault("colors", {})
        c["body"] = r.choice(NE_SHINGLE) if shingle else r.choice(NE_BODY_CLAP)
        c["trim"] = r.choice(NE_TRIM)
        c["accent"] = r.choice(NE_ACCENT)
        c["roof"] = r.choice(["#2e2e30", "#3a3836", "#4a4440", "#2f3438"])
        tr["foundation"] = "cut_stone"                          # (granite)
        tr["windows"] = dict(tr.get("windows", {}), shutters=r.random() < 0.6)
        tr["form_token"] = arch


def _store(tr, region, r):
    if region == "ca":
        tr["facade"] = "stucco"
        tr["cornice"] = r.choice(["mission_parapet", "tile_roof", "parapet_flat", "tile_roof"])
        tr["colors"] = dict(tr.get("colors", {}), body=r.choice(CA_BODY))
        tr["arcade"] = r.random() < 0.35                        # (State Street's arcaded blocks)
        tr["roof_trim"] = "clay_tile"
    else:
        tr["facade"] = "brick" if r.random() < 0.65 else "clapboard"
        tr["cornice"] = r.choice(["corbelled_brick", "bracketed_metal", "parapet_flat"]) if tr["facade"] == "brick" else "bracketed_wood"
        tr["colors"] = dict(tr.get("colors", {}), body=r.choice(["#8e4a36", "#7a4232", "#9c5a42"] if tr["facade"] == "brick" else NE_BODY_CLAP))


def _multi(tr, region, r):
    if region == "ca":
        tr["walls"] = "stucco"
        tr["roof"] = {"type": "hip" if r.random() < 0.5 else "gable", "material": "clay_tile", "pitch_deg": r.randint(16, 22)}
        tr["colors"] = dict(tr.get("colors", {}), body=r.choice(CA_BODY), trim=r.choice(CA_TRIM), roof="#a8492f")
        if tr.get("storeys", 3) <= 2 and r.random() < 0.6:
            tr["form"] = "court"                                # (the bungalow court / courtyard apartments)
    else:
        tr["walls"] = r.choice(["brick", "clapboard", "brick"])
        tr["colors"] = dict(tr.get("colors", {}), body=r.choice(NE_BODY_CLAP if tr["walls"] == "clapboard" else ["#8e4a36", "#7a4232"]))


def _civic(tr, region, r, kind):
    if region == "ca":
        tr["style"] = "mission_revival" if kind != "school" else "spanish_colonial"
        tr["walls"] = "stucco"
        tr["roof_material"] = "clay_tile"
        tr["colors"] = dict(tr.get("colors", {}), body=r.choice(CA_BODY[:6]))
    else:
        if kind == "church":
            tr["style"] = "colonial_revival"                    # (the white meetinghouse, its steeple)
            tr["walls"] = "clapboard"
            tr["colors"] = dict(tr.get("colors", {}), body="#f7f6f0")
        else:
            tr["style"] = r.choice(["federal", "classical_revival"])
            tr["walls"] = r.choice(["brick", "granite"])


def _isle(rec, r):
    """Victory Bay (the user, 2026-10-07: "decidedly upscale ... the houses larger than the mainland, the shopping centers
    very pretty and ornate. The whole island should share an aesthetic"): the Great Lakes resort island -- Mackinac,
    Harbor Springs: grand white and pastel Victorian and Shingle Style summer cottages, deep wraparound porches, green
    shutters, slate and wood-shingle roofs, turrets; the village's shops ornate painted-wood and cast-iron fronts with
    bracketed cornices and striped awnings"""
    k = rec.get("kind")
    tr = rec.setdefault("traits", {})
    rec["region"] = "isle"
    if k == "house":
        arch = _wpick(r, {"queen_anne": 5, "shingle_style": 4, "italianate": 1.5, "i_house": 1})
        tr["archetype"] = arch
        tr["storeys"] = 2 if arch != "i_house" else 2
        tr["main_w_ft"] = int(min(70, (tr.get("main_w_ft") or 34) * 1.45))
        tr["main_d_ft"] = int(min(56, (tr.get("main_d_ft") or 32) * 1.35))
        tr["walls"] = "cedar_shingle" if arch == "shingle_style" else "clapboard"
        tr["roof"] = {"type": {"queen_anne": "cross_gable", "italianate": "hip"}.get(arch, "gable"), "pitch_deg": r.randint(38, 50),
                      "material": _wpick(r, {"slate": 3, "wood_shingle": 3, "asphalt_shingle": 1})}
        tr["porch"] = {"type": "wrap", "posts": "turned", "rail": "spindle"}
        tr["colors"] = {"body": r.choice(ISLE_BODY) if arch != "shingle_style" else "#8a8378", "trim": r.choice(ISLE_TRIM),
                        "accent": r.choice(ISLE_ACCENT), "roof": r.choice(["#3c4048", "#4a4440", "#2f3438"])}
        tr["windows"] = dict(tr.get("windows", {}), shutters=True)
        tr["garage"] = "detached_2"
        tr["condition"] = "kept"
        tr["yard"] = dict(tr.get("yard", {}), fence="picket", extras=["garden", "gazebo"])
        tr["form_token"] = arch
    elif k in ("store", "market"):
        tr["facade"] = r.choice(["frame_false_front", "cast_iron_front", "frame_false_front"])
        tr["cornice"] = "bracketed_metal"
        tr["colors"] = dict(tr.get("colors", {}), body=r.choice(ISLE_BODY), trim="#ffffff", accent=r.choice(ISLE_ACCENT))
        tr["awning_style"] = "striped"
        tr["condition"] = "kept"
        for sf in tr.get("storefronts", []) or []:
            sf["awning"] = True
            sf["sign_style"] = "flat_board"
    elif k in ("condo", "townhouse"):
        # the harbour's residences: painted clapboard terraces and summer-hotel-style blocks, slate roofs, porches
        tr["walls"] = "clapboard"
        tr["roof"] = {"type": "gable" if k == "townhouse" else "hip", "pitch_deg": r.randint(34, 44), "material": "slate"}
        tr["colors"] = dict(tr.get("colors", {}), body=r.choice(ISLE_BODY), trim=r.choice(ISLE_TRIM), accent=r.choice(ISLE_ACCENT),
                            roof="#3c4048")
        tr["windows"] = dict(tr.get("windows", {}), shutters=True)
        tr["porch"] = {"type": "full", "posts": "turned", "rail": "spindle"}
        tr["condition"] = "kept"
    elif k in ("church", "civic", "clubhouse"):
        tr["walls"] = "clapboard" if k != "civic" else tr.get("walls", "clapboard")
        tr["colors"] = dict(tr.get("colors", {}), body="#f8f7f2", trim="#ffffff", accent=r.choice(ISLE_ACCENT))
    return rec
