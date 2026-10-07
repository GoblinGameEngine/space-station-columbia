#!/usr/bin/env python3
"""Bake the place index: every building's working and visiting units, each given a place type.

    python3 tools/places/bake_places.py [--seed 7]

Reads godot_project/remake/placement.json, the repo-root catalog (remake/catalog/<model>.json) and
npc_places.json; writes godot_project/remake/characters/npc_place_index.json. RERUN after any change
to placement, the catalog or npc_places.

Units: a store's storefronts (one unit each) and its upper floor (offices, a lodge hall, hotel
rooms, flats); a civic building's use; a works' use; a church, school, farm, hotel, motel, stand...
Fixed buildings keep their type (a church is a church). **Flexible units** (storefronts, upstairs
offices) get their purpose procedurally, per settlement: each type's demand (per1000) is scaled to
the settlement's flexible units, about 8% are left vacant, and units are filled greedily, largest
deficit first, with a bonus for the catalog signage's type (it is only a hint; the story may re-sign
a shop later). Deterministic: the order is a hash of (seed, unit id).
"""
import argparse
import hashlib
import json
import math
import os
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
CH = os.path.join(ROOT, "godot_project", "remake", "characters")
CIRC = math.tau * json.load(open(os.path.join(ROOT, "godot_project", "remake", "terrain.json")))["R"]      # (the ring's radius from the map)
VACANCY = 0.08
HINT_BONUS = 1.5
HH_SIZE = 2.5

FIXED_KIND = {"church": "church", "school": "school", "hotel": "hotel", "motel": "motel", "farm": "farm", "restaurant": "restaurant",
              "ride": "amusement", "lifeguard": "lighthouse", "lighthouse": "lighthouse", "vacant": "vacant", "arcade": "arcade",
              "cannery": "cannery", "boatyard": "boatyard", "icehouse": "ice_plant", "fishhouse": "fish_house", "warehouse": "warehouse",
              "industrial": "factory", "civic": "community_hall", "pavilion": "park_pavilion", "kiosk": "food_stand", "stand": "food_stand",
              "bait": "sporting_goods", "shed": "fish_house"}
SHELL_OF_KIND = {"church": "church", "school": "school", "hotel": "hotel", "motel": "motel", "farm": "farmstead", "restaurant": "restaurant_building",
                 "ride": "kiosk", "lifeguard": "tower", "lighthouse": "tower", "vacant": "storefront", "arcade": "storefront", "cannery": "waterfront_works",
                 "boatyard": "waterfront_works", "icehouse": "waterfront_works", "fishhouse": "waterfront_works", "warehouse": "warehouse",
                 "industrial": "industrial_shed", "civic": "civic_hall", "pavilion": "pavilion", "kiosk": "kiosk", "stand": "kiosk", "bait": "kiosk",
                 "shed": "waterfront_works", "bigbox": "big_box", "strip": "strip_unit", "store": "storefront"}
SKIP = {"crossing", "monument", "stack", "tower"}
# uses that mean "no one works or shops here"
NO_USE = {"shelter"}


def h01(*parts):
    return int.from_bytes(hashlib.blake2b("|".join(map(str, parts)).encode(), digest_size=8).digest(), "little") / 2 ** 64


def door(b):
    """NpcHouseholds.door: the middle of the footprint's front edge, 1.2 m out (s, x)."""
    yaw = b["yaw"]
    fz = b["fmin"][1]
    fx = (b["fmin"][0] + b["fmax"][0]) * 0.5
    front = (math.cos(yaw), -math.sin(yaw))
    right = (math.sin(yaw), math.cos(yaw))
    d = -fz + 1.2
    return [round((b["s"] + front[0] * d + right[0] * fx) % CIRC, 2), round(b["x"] + front[1] * d + right[1] * fx, 2)]


def dist(a, b):
    ds = (a[0] - b[0] + CIRC / 2) % CIRC - CIRC / 2
    return math.hypot(ds, a[1] - b[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    places = json.load(open(os.path.join(CH, "npc_places.json")))
    types = places["types"]
    settle = json.load(open(os.path.join(CH, "npc_settlements.json")))
    structs = json.load(open(os.path.join(ROOT, "godot_project", "remake", "placement.json")))["structures"]
    hint = {}
    for tid, t in types.items():
        for hname in t["hints"]:
            hint.setdefault(hname.lower(), tid)
    # settlements: centres of the named ones; unnamed buildings belong to the nearest
    cen = defaultdict(list)
    for b in structs:
        if b.get("settlement"):
            cen[b["settlement"]].append((b["s"], b["x"]))
    centre = {}
    for k, v in cen.items():
        ang = math.atan2(sum(math.sin(s / CIRC * math.tau) for s, _ in v), sum(math.cos(s / CIRC * math.tau) for s, _ in v))
        centre[k] = ((ang / math.tau * CIRC) % CIRC, sum(x for _, x in v) / len(v))

    def home_of(b):
        if b.get("settlement"):
            return b["settlement"]
        return min(centre, key=lambda k: dist(centre[k], (b["s"], b["x"])))

    # buildings with a room manifest (tools/rooms/make_rooms.py): their units, place types and posts ARE the model's
    # (its fit-out), not a procedural guess
    manifest = {}
    rdir = os.path.join(ROOT, "godot_project", "remake", "rooms")
    if os.path.isdir(rdir):
        for fn in os.listdir(rdir):
            if fn.endswith(".json") and not fn.startswith("_"):          # (_solved.json: NpcOccupancy's cache)
                manifest.update(json.load(open(os.path.join(rdir, fn)))["buildings"])

    def world(b, lx, lz, out_m=0.0):
        c, sn = math.cos(b["yaw"]), math.sin(b["yaw"])
        s_, x_ = b["s"] + lx * sn - lz * c, b["x"] + lx * c + lz * sn
        if out_m:
            ds, dx = s_ - b["s"], x_ - b["x"]
            L = math.hypot(ds, dx) or 1.0
            s_, x_ = s_ + ds / L * out_m, x_ + dx / L * out_m
        return [round(s_ % CIRC, 2), round(x_, 2)]

    pop = Counter()
    units = []
    for b in structs:
        st = home_of(b)
        kind = b["kind"]
        m = manifest.get(b["id"])
        if m is not None:
            dwell = [u for u in m["units"].values() if u["type"] == "dwelling"]
            pop[st] += sum(u.get("households", 1) for u in dwell) * HH_SIZE
            area = max(1.0, (b["fmax"][0] - b["fmin"][0]) * (b["fmax"][1] - b["fmin"][1]))
            for uid, u in sorted(m["units"].items()):
                if u["type"] == "common" or (u["type"] == "dwelling" and kind in settle["buildings"]):
                    continue
                dname = (u.get("delivery") or {}).get("door")
                dd = next((d for d in m["doors"] if d["node"] == dname), None)
                door_at = world(b, dd["at"][0], dd["at"][1], 1.2 if dd["ext"] else 0.0) if dd else door(b)
                if u["type"] == "dwelling":
                    units.append(dict(building=b["id"], settlement=st, door=door_at, uid="%s/%s" % (b["id"], uid), shell="upper_apartment",
                                      type="residence", hint=None, jobs={}, manifest=True))
                    continue
                jobs = Counter(p_["role"] for p_ in u.get("posts", []))
                units.append(dict(building=b["id"], settlement=st, door=door_at, uid="%s/%s" % (b["id"], uid),
                                  shell=SHELL_OF_KIND.get(kind, "storefront"), type=u["place"], hint=None, jobs=dict(jobs), manifest=True))
            continue
        if kind in settle["buildings"] and not (kind == "farm" and b["id"].startswith("FARM-") and not b["id"].endswith("-house")):
            pop[st] += b.get("households", settle["buildings"][kind]["households"]) * HH_SIZE
        f = os.path.join(ROOT, "remake", "catalog", "%s.json" % b["model"])
        tr = json.load(open(f)).get("traits", {}) if os.path.exists(f) else {}
        area = max(1.0, (b["fmax"][0] - b["fmin"][0]) * (b["fmax"][1] - b["fmin"][1]))
        base = dict(building=b["id"], settlement=st, door=door(b), area=round(area))

        def add(shell, typ=None, hnt=None, n=None):
            units.append(dict(base, uid="%s/%d" % (b["id"], sum(1 for u in units if u["building"] == b["id"])), shell=shell, type=typ, hint=hnt,
                              flexible=typ is None))

        if kind in SKIP:
            continue
        if kind in ("store", "strip", "bigbox"):
            sfs = tr.get("storefronts") or [{}]
            for sf in sfs:
                add(SHELL_OF_KIND[kind], None, hint.get(str(sf.get("type", "")).lower()))
            up = tr.get("upper_use")
            if up == "offices":
                add("upper_office", None, None)
            elif up == "lodge_hall":
                add("upper_hall", "community_hall")
            elif up == "hotel_rooms":
                add("hotel", "hotel")
            elif up == "apartments":
                for _ in sfs:
                    add("upper_apartment", "residence")
            continue
        if kind == "farm" and b["id"].startswith("FARM-") and not b["id"].endswith("-barn"):
            continue                                        # a farm's work is at its barn (NpcHouseholds.is_home: its house)
        if kind in settle["buildings"] and kind not in ("farm", "fishhouse"):
            continue                                        # homes: NpcHouseholds
        use = str(tr.get("use") or "")
        if use in NO_USE:
            add(SHELL_OF_KIND[kind], "park_pavilion")
            continue
        typ = hint.get(use.lower()) or FIXED_KIND.get(kind)
        if typ is None:
            continue
        if SHELL_OF_KIND[kind] not in types[typ]["shells"] and not (kind in ("kiosk", "stand", "pavilion", "arcade", "bait")):
            typ = FIXED_KIND.get(kind, typ)
        add(SHELL_OF_KIND[kind], typ)

    # a college town's largest school is its college
    for st, kind in settle["settlements"].items():
        if kind != "college_town":
            continue
        sch = [u for u in units if u["settlement"] == st and u["type"] == "school"]
        if sch:
            max(sch, key=lambda u: u["area"])["type"] = "college"

    # flexible units: demand-driven, per settlement
    pool = {tid: t for tid, t in types.items() if t["per1000"] > 0 and not t["station"]}
    for st in sorted({u["settlement"] for u in units}):
        flex = [u for u in units if u["settlement"] == st and u.get("flexible")]
        if not flex:
            continue
        n = len(flex)
        # demand from residents, then scaled to the units the town has (main streets serve visitors
        # and the countryside too)
        w = {tid: t["per1000"] for tid, t in pool.items()}
        tot = sum(w.values())
        target = {tid: v / tot * n * (1 - VACANCY) for tid, v in w.items()}
        target["vacant"] = n * VACANCY
        have = Counter()
        for u in sorted(flex, key=lambda u: h01(a.seed, "order", u["uid"])):
            best, bs = None, -1e9
            for tid in list(pool) + ["vacant"]:
                if u["shell"] not in types[tid]["shells"]:
                    continue
                sc = (target.get(tid, 0.0) - have[tid]) + (HINT_BONUS if tid == u["hint"] else 0.0) + 0.05 * h01(a.seed, u["uid"], tid)
                if sc > bs:
                    best, bs = tid, sc
            u["type"] = best or "vacant"
            have[u["type"]] += 1

    # jobs: the registry's staffing, scaled for big works by footprint (a manifest's posts are already its staffing)
    for u in units:
        if u.pop("manifest", False):
            continue
        t = types[u["type"]]
        k = 1.0
        if t["category"] == "industry":
            k = min(3.0, max(0.5, u["area"] / 1500.0))
        u["jobs"] = {o: max(1, round(c * k)) for o, c in t["jobs"].items()}
        del u["flexible"]
        del u["area"]

    summ = {}
    for st in sorted({u["settlement"] for u in units}):
        us = [u for u in units if u["settlement"] == st]
        summ[st] = dict(population=round(pop[st]), units=len(us), jobs=sum(sum(u["jobs"].values()) for u in us if u["type"] != "residence"),
                        types=dict(Counter(u["type"] for u in us).most_common()))
    out = {"_about": "Place units (storefronts, offices, halls, works...) with their procedural place type. Generated by "
                     "tools/places/bake_places.py from placement.json + remake/catalog + npc_places.json; read by NpcPlaces.",
           "seed": a.seed, "units": units, "settlements": summ}
    with open(os.path.join(CH, "npc_place_index.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"))
    tc = Counter(u["type"] for u in units)
    print("%d units; %d types used" % (len(units), len(tc)))
    print(", ".join("%s %d" % kv for kv in tc.most_common()))
    kept = sum(1 for u in units if u.get("hint") and u["hint"] == u["type"])
    print("signage hints kept: %d of %d" % (kept, sum(1 for u in units if u.get("hint"))))
    for st, s in sorted(summ.items(), key=lambda kv: -kv[1]["population"])[:8]:
        print("  %-16s pop %4d  units %3d  jobs %4d" % (st, s["population"], s["units"], s["jobs"]))
    print("total pop %d, jobs %d" % (sum(pop.values()), sum(s["jobs"] for s in summ.values())))


if __name__ == "__main__":
    main()
