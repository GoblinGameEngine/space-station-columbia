#!/usr/bin/env python3
"""calder.py -- Calder's configuration for town.py: where it stands, its names (streets, centres, institutions),
and a preview.  (the user, 2026-10-06: "Name the town and name the streets and name the shopping centers.")

Calder (pop. 7,000) stands on US 30 and the Ring Line between Bellhaven and Pruett, on the southland's open
farmland. Named for Ines Calder, the southland's first district physician, whose infirmary at the crossing of the
Ring Line and the section road (VY 186) the town grew round -- which is why it has the southland's hospital.

    python3 tools/settlegen/calder.py OUT.png        # the plan alone (no map), for checking
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town as TW  # noqa: E402

R = 10000.0                                   # (the 20 km ring, 2026-10-06)
SECTION_S = 3600.0 + 14 * 1609.0              # the section line s = 26,126 (map_expanded SECTION_S) is a town street
S0 = SECTION_S + 134.0                        # Calder's centre round the ring, between Cedar Ford and Pruett
GRID_U0 = SECTION_S - S0
OLD_BANK, XK = 522.5, (3100.0 + 2500.0 - 522.5) / (3100.0 - 522.5)   # (map_expanded.XS: the land stretched 2.5 km)


def XS(x):
    a = abs(x)
    return x if a <= OLD_BANK else math.copysign(OLD_BANK + (a - OLD_BANK) * XK, x)


def rail_x(s):                                # (map_expanded.rail_x)
    return XS(1460.0 + 60.0 * math.sin(2 * s / R + 1.0))


X0 = rail_x(S0) - 90.0                        # Main Street (US 30) 90 m north of the tracks, as Bellhaven and Pruett


def rail_v(u):                                # the frame: x = X0 - v (v grows north, toward the river)
    return X0 - rail_x(S0 + u)


NAMES = {
    "town": "Calder",
    "main": "Main St",
    # parallel to Main, north: numbered (the Ohio convention, tools/street_names.py)
    "north_streets": ["1st St", "2nd St", "3rd St", "4th St", "5th St"],
    "south_streets": ["Railroad Ave", "S 2nd St", "S 3rd St"],
    # cross streets, west to east: trees, then the founders and the southland's families (the bible's lineages)
    "cross": ["Linden St", "Walnut St", "Maple St", "Calder Ave", "Infirmary St", "Kessler St", "Pruett St", "Bellhaven St", "Okafor St"],
    "cross_w": ["Hickory St", "Ash St"],
    "cross_e": ["Sycamore St", "Tamarack St", "Chestnut St", "Spruce St", "Hollis St"],
    "south_road": "Calder Rd",
    "north_road": "River Rd",
    "ridge": "Bluff Dr",
    "south_collector": "Southview Dr",
    "west_road": "Deer Creek Rd",
    "east_road": "Birch Run Rd",
    "courts": ["Heron Ct", "Kestrel Ct", "Lark Ct", "Plover Ct", "Wren Ct", "Goldfinch Ct", "Meadowlark Ct", "Bluebird Ct",
               "Cardinal Ct", "Clover Ct", "Juniper Ct"],
    "loops": ["Orchard Dr", "Fox Run Dr", "Harvest Dr", "Prairie Dr", "Windmill Dr", "Sunfield Dr"],
    "square": "Infirmary Square",
    "hospital": "Calder Memorial Hospital",
    "clinic": "Southland Medical Arts",
    "elementary": "Ines Calder Elementary",
    "high_school": "Southland High School",
    "park": "Ring Line Park",
    "cemetery": "Greenlawn Cemetery",
    "apartments": "Southview Commons Apartments",
    "apartments2": "Deer Creek Apartments",
    "seniors": "Infirmary Court (senior apartments)",
    "apartments3": "Ring Line Apartments",
    "townhouses": "Fieldstone Townhomes",
    "townhouses2": "Birch Run Townhomes",
    "late_streets": ["Cornflower Ln", "Thistle Ln", "Sorrel Way", "Prairie Smoke Way"],
    # the shopping centres: two on US 30 at the town's entries, two convenience strips at collector corners
    "centres": ["Calder Commons", "Westgate Plaza", "Southview Center", "Bluff Shoppes"],
    # and the three in the countryside round it
    "country": ["Birch Run Plaza", "Deer Creek Corners", "Pruett Crossroads"],
}

CFG = dict(seed=186, names=NAMES, rail_v=rail_v, grid_u0=GRID_U0, bounds=(-760.0, 1060.0, -1100.0, 720.0), churches=6,
           townhouse_share={"late": 0.25, "current": 0.4}, apartment_share={"late": 0.08, "current": 0.14})


def plan(blocked=lambda u, v: False):
    return TW.plan_town(CFG, random.Random(CFG["seed"]), blocked)


# ------------------------------------------------------------------ structures: the plan as the map's buildings
KIND = {"house": "house", "duplex": "house", "two_flat": "house", "townhouse": "townhouse", "apartment": "condo", "store": "store",
        "gas_station": "strip", "motel": "motel", "works": "industrial", "elevator": "industrial", "water_tower": "tower",
        "church": "church", "city_hall": "civic", "police": "civic", "fire_station": "civic", "post_office": "civic", "library": "civic",
        "depot": "civic", "hospital": "civic", "hospital_wing": "civic", "clinic": "civic", "elementary": "school",
        "high_school": "school", "high_school_wing": "school", "fieldhouse": "school", "bigbox": "bigbox", "strip_row": "strip",
        "pad": "strip"}


def ring(u, v):
    return (S0 + u, X0 - v)


def _trim_front(poly, by):
    """Move a lot's front edge back by `by` m (the house generator puts the house just behind its record's front)."""
    (a, b_, c, d) = poly
    nx, ny = d[0] - a[0], d[1] - a[1]
    L = math.hypot(nx, ny) or 1.0
    nx, ny = nx / L * by, ny / L * by
    return [(a[0] + nx, a[1] + ny), (b_[0] + nx, b_[1] + ny), c, d]


def _dims(poly):
    return math.dist(poly[0], poly[1]), math.dist(poly[1], poly[2])


def _number(l):
    """A street address: hundreds by the block from the centre (Main St / Calder Ave), odd and even sides."""
    (a, b_) = l["poly"][0], l["poly"][1]
    cu, cv = (a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2
    along_u = abs(b_[0] - a[0]) > abs(b_[1] - a[1])
    coord = (cu - GRID_U0) if along_u else cv
    blk = int(abs(coord) // 112.0)
    within = int((abs(coord) % 112.0) / 112.0 * 48)
    side = l["poly"][3][1] - a[1] if along_u else l["poly"][3][0] - a[0]
    return 100 * (blk + 1) + 2 * within + (1 if side > 0 else 0)


def centre_structures(c, frame, era):
    """A shopping centre plan's buildings as structures: each anchor / junior a big box, consecutive in-line bays
    merged into rows of up to 8 stores (one canopy, one pylon), each pad on its own. The record's lot reaches from the
    building's back (+3 m) to its share of the parking in front (the generators lay the lot in front of the doors)."""
    out = []
    bl = c["plan"]["buildings"]
    rows, cur = [], []
    for b in bl:
        if b.get("role") == "inline":
            cur.append(b)
            if len(cur) == 8:
                rows.append(cur)
                cur = []
        else:
            if cur:
                rows.append(cur)
                cur = []
            rows.append([b])
    if cur:
        rows.append(cur)
    for grp in rows:
        b0 = grp[0]
        role = b0.get("role")
        u0 = min(q[0] for b in grp for q in b["poly"])
        u1 = max(q[0] for b in grp for q in b["poly"])
        vf = min(q[1] for b in grp for q in b["poly"])
        vb = max(q[1] for b in grp for q in b["poly"])
        if role in ("anchor", "junior"):
            use, park = "bigbox", 18.0
        elif role == "inline":
            use, park = "strip_row", 12.0
        else:
            use, park = "pad", 12.0
        poly_l = [(u0 - 2, vf - park), (u1 + 2, vf - park), (u1 + 2, vb + 3), (u0 - 2, vb + 3)]
        stores = [{"tenant": b.get("tenant")} for b in grp]
        out.append(dict(use=use, poly=[frame(u, v) for u, v in poly_l], stores_t=[b.get("tenant") for b in grp], centre=c["name"],
                        era=era, band="suburban", label=c["name"] if role == "anchor" else None))
    return out


def structures(p, country=()):
    """Every structure in map order, with its id (C-001...), ring polygon (front edge first), lot and use."""
    from records import TENANT_TYPE
    out = []
    for l in p["lots"]:
        poly = l["poly"]
        if l["use"] in ("house", "duplex", "two_flat"):
            trim = max(0.0, min(float(l.get("setback", 4.0)) - 3.0, _dims(poly)[1] - 20.0))
            poly = _trim_front(poly, trim)
        lw, ld = _dims(poly)
        e = dict(use=l["use"], band=l["band"], poly=[ring(u, v) for u, v in poly], lot_w=lw, lot_d=ld, face=l.get("face"),
                 label=l.get("label"), units=l.get("units"), alley=l["band"] in ("rail", "streetcar"),
                 number=_number(l) if l["use"] in ("house", "duplex", "two_flat") else None)
        out.append(e)
    eras = {"Calder Commons": 1994, "Westgate Plaza": 1968, "Southview Center": 1979, "Bluff Shoppes": 2006}
    for c in p["centres"]:
        frame = (lambda c_: (lambda u, v: ring(u, c_["v_road"] + c_["dirn"] * v)))(c)
        out += centre_structures(c, frame, eras.get(c["name"], 1985))
    for c, frame in country:
        out += centre_structures(c, frame, c.get("era", 1990))
    rnd = random.Random(CFG["seed"] + 7)
    for k, e in enumerate(out, 1):
        e["id"] = "C-%03d" % k
        if "stores_t" in e:
            e["stores"] = []
            for t in e.pop("stores_t"):
                typ = TENANT_TYPE.get(t, "variety_store")
                e["stores"].append({"type": typ, "tenant": t})
        if "lot_w" not in e:
            e["lot_w"], e["lot_d"] = math.dist(e["poly"][0], e["poly"][1]), math.dist(e["poly"][1], e["poly"][2])
    return out


def write_records(structs, out_dir=None):
    import json
    import records as RC
    out_dir = out_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "remake", "catalog")
    rules = RC.Rules(CFG["seed"])
    n = 0
    for e in structs:
        if e.get("stores"):
            r = RC.rnd_for(CFG["seed"], e["id"], "names")
            e["stores"] = [dict(RC.business(r, st["type"], rules.surnames, "Calder", ["Calder", "Southland", "Ring Line", e.get("centre", "")
                                                                                  .split()[0]]), tenant=st["tenant"]) for st in e["stores"]]
        rec = RC.make_record(e, rules, "Calder", CFG["seed"])
        txt = json.dumps(rec, indent=1)                     # (unchanged: the file and its time stay -- build_library)
        fp = os.path.join(out_dir, rec["id"] + ".json")
        if not os.path.exists(fp) or open(fp).read() != txt:
            with open(fp, "w") as f:
                f.write(txt)
        n += 1
    return n


def preview(p, out):
    from PIL import Image, ImageDraw
    u0, u1, v0, v1 = CFG["bounds"]
    k = 0.5
    W, H = int((u1 - u0 + 120) / k), int((v1 - v0 + 120) / k)
    im = Image.new("RGB", (W, H), (210, 222, 190))
    d = ImageDraw.Draw(im)
    tx = lambda q: ((q[0] - u0 + 60) / k, (v1 + 60 - q[1]) / k)
    AC = {"square": (190, 220, 170), "park": (150, 200, 130), "schoolground": (200, 215, 170), "sportsfield": (120, 180, 100),
          "parking": (170, 170, 170), "campus": (205, 205, 195), "cemetery": (160, 190, 150), "lawn": (185, 215, 160),
          "culdesac": (120, 120, 120)}
    for a in p["areas"]:
        d.polygon([tx(q) for q in a["poly"]], fill=AC.get(a["kind"], (200, 200, 200)))
    for c in p["centres"]:
        for a in c["plan"]["areas"]:
            d.polygon([tx((q[0], c["v_road"] + c["dirn"] * q[1])) for q in a["poly"]], fill=(175, 175, 175))
        for b in c["plan"]["buildings"]:
            d.polygon([tx((q[0], c["v_road"] + c["dirn"] * q[1])) for q in b["poly"]], fill=(200, 80, 80))
    COL = {"house": (240, 236, 226), "store": (200, 90, 70), "church": (140, 100, 180), "works": (120, 110, 100)}
    for l in p["lots"]:
        d.polygon([tx(q) for q in l["poly"]], fill=COL.get(l["use"], (90, 120, 200)), outline=(150, 150, 150))
        d.line([tx(l["poly"][0]), tx(l["poly"][1])], fill=(40, 40, 40), width=2)
    W_ = {"main": 11, "street": 7, "alley": 3}
    for s in p["streets"]:
        d.line([tx(q) for q in s["pts"]], fill=(90, 90, 90), width=max(1, int(W_[s["cls"]] / k)))
    for (q, t) in p["marks"]:
        d.text(tx(q), t, fill=(0, 0, 0))
    im.save(out)


if __name__ == "__main__":
    p = plan()
    print(p["stats"])
    if "--records" in sys.argv:
        st = structures(p)
        print("records written:", write_records(st), "(town only; map_expanded --game-data writes the countryside centres' too)")
    elif len(sys.argv) > 1:
        preview(p, sys.argv[1])
