#!/usr/bin/env python3
"""catalog_tokens.py -- seed token files from the existing catalog (remake/catalog/<ID>.json, CATALOG_SPEC.md) so the
annotator only adds what the photos show (research/buildings/TOKENS.md, METHOD.md §4).

  skeleton(cid)                 the record's traits mapped to the token vocabulary, its photos, place and year
  complete(cid, add=, drop=, floors=, notes=, lot=, why=, ...)   apply the annotator's corrections and write
                                 research/buildings/regions/<region>/tokens/CAT-<cid>.json
  ids(region_states, kinds)     the catalog IDs whose example is in the region's states

  python3 tools/buildings/catalog_tokens.py list great_lakes [kind]   # IDs to do, not yet tokenized
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CAT = os.path.join(ROOT, "remake", "catalog")
REF = os.path.join(ROOT, "remake", "reference")
REGIONS = {"great_lakes": {"OH", "MI", "IN", "IL", "WI", "MN", "PA", "NY", "ON"}}
EXCLUDE = {"great_lakes": ("HVN-",)}             # (Montauk NY: the Atlantic shore, not the Great Lakes)

FORM = {"i_house": "i_house", "gable_front": "gable_front", "upright_and_wing": "upright_and_wing", "foursquare": "foursquare",
        "bungalow": "bungalow", "workers_cottage": "workers_cottage", "queen_anne": "queen_anne_irregular",
        "italianate": "italianate_cube", "cape_cod": "cape_cod", "ranch": "ranch", "minimal_traditional": "minimal_traditional",
        "side_gable_cottage": "side_gable_cottage", "shotgun": "shotgun", "dutch_colonial": "two_storey_colonial",
        "tudor_revival": "side_gable_cottage", "split_level": "split_level", "american_small_house": "american_small_house",
        "prairie_box": "prairie_box", "contemporary_beach": "builder_contemporary", "nantucket_cape": "cape_cod",
        "california_bungalow": "bungalow", "shingle_style": "queen_anne_irregular", "spanish_revival": "side_gable_cottage"}
STYLE = {"queen_anne": "queen_anne", "italianate": "italianate", "dutch_colonial": "dutch_colonial", "tudor_revival": "tudor_revival",
         "bungalow": "craftsman", "foursquare": "vernacular", "prairie_box": "prairie", "spanish_revival": "spanish_revival",
         "shingle_style": "shingle", "contemporary_beach": "contemporary"}
WALL = {"cast_iron_front": "cast_iron", "frame_false_front": "clapboard", "glass_modern": "glass", "block": "concrete_block",
        "metal": "metal_panel", "frame": "clapboard", "concrete": "concrete"}
CHIM = {"center": "ridge_centre", "left_end": "end_interior", "right_end": "end_interior", "rear": "rear",
        "exterior_left": "end_exterior", "exterior_right": "end_exterior"}
GARAGE = {"none": "none", "detached_1": "detached_rear", "detached_2": "detached_rear", "attached_1": "attached_side",
          "attached_2": "attached_side", "carport": "carport"}
FENCE = {"picket": "fence_picket", "chainlink": "fence_chainlink", "iron": "fence_iron", "split_rail": "fence_split_rail",
         "hedge": "hedge", "privacy": "fence_privacy"}
STOREYS = {1: "1", 1.5: "1.5", 2: "2", 2.5: "2.5", 3: "3", 4: "4", 5: "5"}


def band(y):
    if not y:
        return None
    y = int(y)
    for lim, b in ((1830, "pioneer_pre1850"), (1860, "canal_1830_1860"), (1890, "railroad_1860_1900"), (1920, "streetcar_1890_1930"),
                   (1945, "interwar_1920_1945"), (1965, "postwar_1945_1965"), (1990, "suburban_1965_1990"), (2010, "late_1990_2010")):
        if y < lim:
            return b
    return "current_2010_on"


def state_of(place):
    return place.split(",")[-1].strip()[:2] if place else ""


def ids(region="great_lakes", kinds=None):
    out = []
    for f in sorted(os.listdir(CAT)):
        if not f.endswith(".json") or f.startswith("_"):
            continue
        try:
            r = json.load(open(os.path.join(CAT, f)))
        except Exception:
            continue
        if r["id"].startswith(EXCLUDE.get(region, ())):
            continue
        if state_of(r.get("example", {}).get("place", "")) in REGIONS[region] and (not kinds or r.get("kind") in kinds):
            out.append(r["id"])
    return out


def done(region="great_lakes"):
    d = os.path.join(ROOT, "research", "buildings", "regions", region, "tokens")
    return {f[4:-5] for f in os.listdir(d) if f.startswith("CAT-")}


def skeleton(cid):
    r = json.load(open(os.path.join(CAT, cid + ".json")))
    t = r.get("traits", {}) or {}
    k = r.get("kind")
    tok = []
    add = tok.append
    use = {"house": "house", "cottage": "house", "store": "mixed_use" if t.get("upper_use") not in (None, "none", "storage") else "store",
           "church": "church", "civic": "civic", "school": "school", "industrial": "industrial", "vacant": "store", "strip": "strip_center",
           "bigbox": "big_box"}.get(k)
    if use:
        add("use:" + use)
    a = t.get("archetype")
    if a in FORM:
        add("form:" + FORM[a])
    if a in STYLE:
        add("style:" + STYLE[a])
    st = t.get("storeys")
    if st in STOREYS:
        add("storeys:" + STOREYS[st])
    def obj(v):                                      # (some records -- farm, waterfront -- give a plain string)
        return v if isinstance(v, dict) else {"type": v} if isinstance(v, str) else {}
    roof = obj(t.get("roof"))
    if roof.get("type") in ("gable", "hip", "gambrel", "cross_gable", "pyramid", "shed", "flat"):
        add("roof:" + roof["type"])
    p = roof.get("pitch_deg")
    if p:
        add("pitch:" + ("low" if p < 18 else "mid" if p < 33 else "steep" if p < 48 else "very_steep"))
    if roof.get("material") in ("asphalt_shingle", "wood_shingle", "slate", "tile"):
        add("roof_mat:" + roof["material"])
    elif roof.get("material") == "metal":
        add("roof_mat:metal_standing_seam")
    for d in (t.get("dormers") if isinstance(t.get("dormers"), list) else [])[:1]:
        if isinstance(d, dict) and d.get("type") in ("gable", "shed", "hip", "eyebrow"):
            add("dormer:" + d["type"])
    po = obj(t.get("porch"))
    if po.get("type") in ("none", "stoop", "front_full", "front_partial", "wrap", "enclosed", "side", "recessed"):
        add("porch:" + po["type"])
    if po.get("posts") in ("turned", "square", "tapered_on_piers", "iron", "columns"):
        add("porch_post:" + po["posts"])
    if po.get("rail") in ("none", "spindle", "solid", "lattice"):
        add("rail:" + po["rail"])
    w = t.get("walls") or t.get("facade")
    if w:
        add("wall:" + WALL.get(w, w))
    if t.get("foundation") in ("fieldstone", "brick", "concrete_block", "poured_concrete", "cut_stone"):
        add("foundation:" + t["foundation"])
    win = obj(t.get("windows"))
    if win.get("type") in ("1over1", "2over2", "6over6", "4over1", "3over1_craftsman", "casement", "picture", "sliding"):
        add("window:" + win["type"])
    if win.get("shutters"):
        add("ornament:shutters")
    ch = t.get("chimneys") if isinstance(t.get("chimneys"), list) else []
    if len(ch) > 1:
        add("chimney:multiple")
    elif ch:
        add("chimney:" + CHIM.get(ch[0], "end_interior"))
    if t.get("garage") in GARAGE:
        add("garage:" + GARAGE[t["garage"]])
    fence = obj(t.get("yard")).get("fence")
    if fence in FENCE:
        add("bound_side:" + FENCE[fence])
    if t.get("cornice") in ("bracketed_metal", "corbelled_brick", "parapet_stepped", "parapet_flat", "pediment", "none"):
        add("cornice:" + t["cornice"])
    if t.get("condition") in ("kept", "worn", "shabby", "boarded"):
        add("condition:" + t["condition"])
    if k == "store":
        add("form:" + ("one_part_commercial" if st == 1 else "two_part_commercial"))
        add("setting:main_street")
    if k == "church":
        add("form:nave_and_tower")
    if k in ("civic",):
        add("form:civic_block")
    if k == "school":
        add("form:school_block")
    if k == "industrial":
        add("form:factory_block")
    tok = list(dict.fromkeys(tok))
    ex = r.get("example", {})
    imgs = []
    mp = os.path.join(REF, cid, "sources.json")
    srcs = json.load(open(mp))["files"] if os.path.exists(mp) else []
    has_photo = any(e.get("kind", "photo") in ("photo", "photos") for e in srcs)
    for e in srcs:                                   # (photos; measured drawings when a record has no photo)
        if (e.get("kind", "photo") in ("photo", "photos") or not has_photo) and os.path.exists(os.path.join(REF, cid, e["file"])):
            imgs.append({"file": "remake/reference/%s/%s" % (cid, e["file"]),
                         "view": "front_34" if e.get("kind", "photo") in ("photo", "photos") else "drawing_elevation", "source": e.get("source", ""),
                         "url": e.get("record") or e.get("url", ""), "license": e.get("license", ""), "author": (e.get("author") or "")[:120],
                         "caption": (e.get("caption") or "")[:200]})
    yb = t.get("year_built") or ex.get("year")
    return {"id": "CAT-" + cid, "catalog_id": cid, "images": imgs,
            "place": {"town": ex.get("place", "").split(",")[0], "state": state_of(ex.get("place", "")), "band": band(yb),
                      "source_title": ex.get("title", "")},
            "year_built": yb, "tokens": tok, "brief": r.get("brief", ""), "catalog": {"kind": k, "archetype": a}}


def complete(cid, add=(), drop=(), floors=(), notes="", lot=None, why=(), transect=None, view=None, image=0, confidence="high",
             region="great_lakes"):
    t = skeleton(cid)
    drop_fams = {d[:-1] for d in drop if d.endswith(":")}
    t["tokens"] = [x for x in t["tokens"] if x not in drop and x.split(":")[0] not in drop_fams]
    for a in add:
        fam = a.split(":")[0]
        if fam in ("form", "storeys", "roof", "pitch", "porch", "wall", "window", "condition", "garage", "use", "style", "door_pos", "symmetry", "bays"):
            t["tokens"] = [x for x in t["tokens"] if x.split(":")[0] != fam]
        t["tokens"].append(a)
    t["tokens"] = list(dict.fromkeys(t["tokens"]))
    if transect:
        t["place"]["transect"] = transect
    if t["images"]:
        im = t["images"][min(image, len(t["images"]) - 1)]
        if view:
            im["view"] = view
        t["images"] = [im] + [x for x in t["images"] if x is not im]
    t["facade"] = {"faces": "street", "floors": list(floors), "notes": notes}
    t["lot"] = lot or {}
    t["why"] = [{"token": w[0], "cause": w[1], "ref": w[2], "note": w[3]} for w in why]
    t["confidence"] = confidence
    t["annotator"] = "claude 2026-10-05 (from catalog traits + photo)"
    out = os.path.join(ROOT, "research", "buildings", "regions", region, "tokens", "CAT-%s.json" % cid)
    json.dump(t, open(out, "w"), indent=1)
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["list"]:
        region = sys.argv[2]
        kinds = sys.argv[3:] or None
        dn = done(region)
        todo = [i for i in ids(region, kinds) if i not in dn]
        print(len(todo))
        print(" ".join(todo[:80]))
