#!/usr/bin/env python3
"""make_rooms.py -- what every room of every building is for, and who belongs in it (the user, 2026-10-07: "every single
building needs a purpose, every house needs residents, every shop needs workers and every store needs shoppers ...
each and every room ... generate it on the fly while in-game").  The contract with the story engine (deck-ea session):
memory ssc-occupancy-contract, research/lives/07_occupancy.md.

    ~/.venvs/ssc-assets/bin/python tools/rooms/make_rooms.py [SETTLEMENT ...]      (default: every settlement with raw plans)

Reads the raw plans the Blender build writes (remake/rooms/raw/<id>.json: rooms, doors, stairs, storeys, the furniture
placed in each room), the catalog records, placement.json and the place types (npc_places.json).  Writes one manifest per
settlement, godot_project/remake/rooms/<Settlement>.json, that the game's NpcOccupancy reads -- DATA, no geometry: a
cluster that isn't loaded is answered from it as well as one that is.

Per building:
  purpose   "dwelling" or the place type of its business(es)
  rooms     rid -> use, floor, z [floor, ceiling] and rect [x0, z0, x1, z1] in the glb's frame (x right, z back), unit,
            access (private / common / public / staff), beds and seats (from the furniture placed there), containers
            [{cid, type, at, owner}] and work stations
  doors     [{node, rooms [a, b | "outside"], ext, lock}]: node is the glb's door_<name> prefix; lock is a rule the game
            evaluates (residents / hours / staff / manager / open)
  units     uid -> dwelling (households) | business (place type, posts) | common, its rooms, its DELIVERY point (a door +
            who signs for it)
  posts     (business units) the rostered jobs: {post "<uid>:<role>:<n>", role, room, shift [h0, h1] (a night shift runs
            past 24 and belongs to the day it starts), days "mon-fri" | "mon-sat" | "daily", off [two weekdays] for rota
            posts, relief true where a post exists only to cover others' days off}
Nothing here depends on the world seed: who fills each post, who sleeps in each bed, which posts stand vacant is the
game's (NpcOccupancy), from the seed and the journal.
"""
import json
import math
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "remake", "rooms", "raw")
CAT = os.path.join(ROOT, "remake", "catalog")
GD = os.path.join(ROOT, "godot_project", "remake")
OUT = os.path.join(GD, "rooms")
TYPES = json.load(open(os.path.join(GD, "characters", "npc_places.json")))["types"]
SETTLE = json.load(open(os.path.join(GD, "characters", "npc_settlements.json")))
DWELLING_KINDS = {"house", "farmhouse", "cottage", "beachhouse", "bungalow", "shingle", "singlehouse", "rowhouse", "townhouse", "condo"}

# a room's use, from its plan type (and fit-out)
USE = {"bed": "bedroom", "bedroom": "bedroom", "living": "living", "sitting": "living", "dining": "dining", "kitchen": "kitchen",
       "bath": "bath", "hall": "hall", "closet": "closet", "laundry": "laundry", "shop": "sales", "stock": "stockroom",
       "office": "office", "ward": "ward", "nurse": "nurse_station", "lobby": "lobby", "classroom": "classroom", "nave": "nave",
       "fellowship": "hall", "council": "chamber", "jail": "cells", "library": "reading_room", "po_lobby": "lobby",
       "sorting_room": "workroom", "waiting_room": "waiting", "bar": "bar", "store": "sales", "restaurant": "dining_room"}
FITOUT_USE = {"stockroom": "stockroom", "office": "office", "lobby": "lobby", "guest_room": "guest_room", "machine_floor": "work_floor",
              "classroom": "classroom", "ward": "ward", "nurse_station": "nurse_station", "nave": "nave", "jail": "cells",
              "sorting_room": "workroom", "waiting_room": "waiting", "council": "chamber", "fellowship": "hall"}
PUBLIC_USES = {"sales", "lobby", "waiting", "nave", "dining_room", "bar", "reading_room", "chamber", "classroom", "ward", "hall_public"}
STAFF_USES = {"stockroom", "office", "nurse_station", "workroom", "work_floor", "cells", "kitchen_staff"}
# fit-out / record business type -> the game's place type
PLACE = {"pizza": "restaurant", "brewpub": "bar", "pool_hall": "bar", "nail_salon": "beauty_salon", "pharmacy": "drug_store",
         "dollar": "variety_store", "discount": "variety_store", "dry_goods": "clothing", "shoe_store": "clothing",
         "feed_seed": "hardware", "auto_parts": "hardware", "appliance_repair": "repair_shop", "shoe_repair": "repair_shop",
         "video_rental": "variety_store", "tax_office": "insurance_office", "real_estate": "insurance_office", "pet": "variety_store",
         "art_gallery": "bookstore", "music_store": "variety_store", "gas_station": "charge_stop", "ice_cream": "cafe",
         "newspaper": "print_shop", "tavern_hotel": "hotel", "guest_room": "hotel", "motel": "motel", "office": "insurance_office",
         "machine_floor": "factory", "po_lobby": "post_office", "sorting_room": "post_office", "council": "town_hall",
         "jail": "police_fire", "ward": "hospital", "nurse_station": "hospital", "classroom": "school", "nave": "church",
         "fellowship": "church", "library": "library", "waiting_room": "doctor_office"}
CIVIC_USE = {"city_hall": "town_hall", "police": "police_fire", "fire_station": "police_fire", "post_office": "post_office",
             "library": "library", "depot": "transit_station", "hospital": "hospital", "clinic": "doctor_office",
             "elementary": "school", "high_school": "school", "gym": "school", "creamery": "factory", "farm_equipment": "repair_shop",
             "feed_mill": "mill", "grain_elevator": "grain_elevator", "lumber_yard": "warehouse", "machine_shop": "machine_works",
             "warehouse": "warehouse", "yacht_club": "restaurant", "restrooms": "park_pavilion", "courthouse": "courthouse",
             "custom_house": "admin_center", "opera_house": "community_hall", "college": "college", "roundhouse": "machine_works",
             "mill": "mill"}
# furniture -> what it offers
BED = {"bed"}
SEAT = {"chair": 1, "armchair": 1, "sofa": 3, "bench": 3, "stool": 1, "booth": 4, "barber_chair": 1, "_table_set": 4, "_pupil_desk": 1}
CONTAINER = {"dresser": "dresser", "desk": "desk", "safe": "safe", "file_cabinet": "file_cabinet", "cash_register": "register",
             "display_case": "display_case", "fridge": "fridge", "base_cabinets": "cabinets", "shelves": "shelves", "stocked_shelves": "shelves",
             "washstand": "washstand", "vanity": "vanity", "teller_counter": "teller_drawer", "_cabinet": "cabinet", "coat_rack": "coat_rack",
             "mantel": "mantel", "po_boxes": "po_boxes"}
STATION = {"cash_register": "till", "desk": "desk", "bar_counter": "counter", "teller_counter": "teller", "barber_chair": "chair",
           "exam_table": "exam", "range_stove": "stove", "_machine": "machine", "nurse_station": "station", "car_lift": "bay",
           "press": "press", "sink_counter": "sink"}
# role -> the rooms it works in, best first
ROLE_ROOMS = {"shop_clerk": ["sales"], "shopkeeper": ["sales", "office"], "cashier": ["sales"], "waiter": ["dining_room", "sales", "bar"],
              "bartender": ["bar", "sales"], "cook": ["kitchen", "sales", "dining_room"], "baker": ["kitchen", "sales"],
              "clerk": ["office", "lobby", "sales"], "janitor": ["hall", "lobby", "sales", "*"], "nurse": ["ward", "nurse_station"],
              "care_aide": ["ward"], "doctor": ["ward", "office", "nurse_station"], "teacher": ["classroom"], "librarian": ["reading_room"],
              "pastor": ["nave", "office"], "police": ["office", "cells", "lobby"], "firefighter": ["*"], "postal_worker": ["workroom", "lobby"],
              "factory_hand": ["work_floor", "*"], "mechanic": ["work_floor", "*"], "driver": ["*"], "banker": ["office", "sales"],
              "lawyer": ["office"], "agent": ["office"], "dentist": ["office", "sales"], "pharmacist": ["sales"], "barber": ["sales"],
              "hotel_worker": ["lobby", "guest_room", "office"], "editor": ["office"], "builder": ["*"], "farmer": ["*"], "farmhand": ["*"],
              "dock_worker": ["*"], "fisher": ["*"]}
FRONT_ROLES = ["shop_clerk", "cashier", "waiter", "bartender", "nurse", "clerk", "hotel_worker", "teacher", "librarian", "postal_worker",
               "police", "shopkeeper", "barber"]
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def hours_of(t):
    h = t.get("hours", {})
    def hh(s):
        a, b = s.split(":")
        return int(a) + int(b) / 60.0
    o, c = hh(h.get("open", "09:00")), hh(h.get("close", "17:00"))
    if c <= o:
        c += 24.0
    return o, c, h.get("days", "mon-fri")


def shifts_for(o, c):
    """the shift templates a place's hours need (contract: <=10 h one, <=16 h early + late, 24 h three)"""
    L = c - o
    if L >= 23.9:
        return [(7.0, 15.0), (15.0, 23.0), (23.0, 31.0)]
    if L <= 10.0:
        return [(o - 0.5, c + 0.25)]
    m = o + L / 2
    return [(o - 0.5, m + 0.5), (m - 0.5, c + 0.25)]


def posts_for(uid, ptype, rooms_by_use):
    """the rostered posts of a business unit: every role's headcount spread over the shifts, a weekly rota for the places
    open more than five days, relief posts wherever a shift on some day would have no one at the front"""
    t = TYPES.get(ptype)
    if not t:
        return []
    o, c, days = hours_of(t)
    if days in ("never",):
        return []
    sh = shifts_for(o, c)
    weights = [0.45, 0.33, 0.22] if len(sh) == 3 else ([0.55, 0.45] if len(sh) == 2 else [1.0])
    posts = []

    def room_for(role, k=0):
        for u in ROLE_ROOMS.get(role, ["*"]):
            if u == "*":
                break
            if rooms_by_use.get(u):
                return rooms_by_use[u][k % len(rooms_by_use[u])]      # (the night nurses spread over the wards)
        for u in ("sales", "lobby", "office", "work_floor", "hall"):
            if rooms_by_use.get(u):
                return rooms_by_use[u][0]
        return next((v[0] for v in rooms_by_use.values() if v), None)
    rota = days in ("daily", "mon-sat", "seasonal")
    for role, n in t.get("jobs", {}).items():
        n = int(n)
        if n <= 0:
            continue
        managerial = role in ("shopkeeper", "doctor", "pastor", "lawyer", "banker", "dentist", "librarian", "editor")
        # headcount per shift: managers work days; the rest spread by the shift weights, each shift at least one when the
        # headcount allows
        if managerial or len(sh) == 1:
            per = [n] + [0] * (len(sh) - 1)
        else:
            per = [max(1 if n >= len(sh) else 0, round(n * w)) for w in weights]
            while sum(per) > n:
                per[per.index(max(per))] -= 1
            while sum(per) < n:
                per[0] += 1
        k = 0
        for si, cnt in enumerate(per):
            for j in range(cnt):
                p = {"post": f"{uid}:{role}:{k}", "role": role, "room": room_for(role, j), "shift": [round(sh[si][0], 2), round(sh[si][1], 2)],
                     "days": "mon-fri" if (days == "mon-fri" or managerial and days != "daily") else days}
                if rota and not managerial:
                    a = (j * 2 + si * 3 + k) % 7                   # two days off in a row, spread across the shift's posts
                    p["off"] = [DAYS[a], DAYS[(a + 1) % 7]]
                posts.append(p)
                k += 1
    # cover: every shift on every open day has someone at the front
    front = next((r for r in FRONT_ROLES if r in t.get("jobs", {})), next(iter(t.get("jobs", {})), None))
    if front:
        open_days = {"daily": DAYS, "seasonal": DAYS, "mon-sat": DAYS[:6], "mon-fri": DAYS[:5]}.get(days, DAYS[:5])
        k = sum(1 for p in posts if p["role"] == front)
        for si, s in enumerate(sh):
            for d in open_days:
                on = [p for p in posts if p["shift"] == [round(s[0], 2), round(s[1], 2)] and
                      (p["days"] == "daily" or d in {"mon-fri": DAYS[:5], "mon-sat": DAYS[:6]}.get(p["days"], DAYS)) and d not in p.get("off", [])]
                if not on:
                    a = (DAYS.index(d) + 2) % 7
                    posts.append({"post": f"{uid}:{front}:{k}", "role": front, "room": room_for(front, k),
                                  "shift": [round(s[0], 2), round(s[1], 2)], "days": days if days != "mon-fri" else "mon-fri",
                                  "off": [DAYS[a], DAYS[(a + 1) % 7]], "relief": True})
                    k += 1
    return posts


def glb_rect(r):
    x0, y0, x1, y1 = r["rect"]
    return [round(x0, 2), round(-y1, 2), round(x1, 2), round(-y0, 2)]


def block_floor(blocks, r):
    x0, y0, x1, y1 = r["rect"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    fl = r.get("floor", 0)
    for bl in blocks:
        bx0, by0, bx1, by1 = bl["rect"]
        if bx0 - 0.05 <= cx <= bx1 + 0.05 and by0 - 0.05 <= cy <= by1 + 0.05 and fl < len(bl["floors"]):
            return bl["floors"][fl]
    return None


def rooms_of_door(rooms, d):
    """the rooms either side of a door: those on its floor whose outline passes through its point"""
    x, y = d["at"][0], d["at"][1]
    fl = d.get("floor", 0)
    out = []
    for r in rooms:
        if r.get("floor", 0) != fl:
            continue
        x0, y0, x1, y1 = r["rect"]
        on_v = (abs(x - x0) < 0.25 or abs(x - x1) < 0.25) and y0 - 0.05 <= y <= y1 + 0.05
        on_h = (abs(y - y0) < 0.25 or abs(y - y1) < 0.25) and x0 - 0.05 <= x <= x1 + 0.05
        if on_v or on_h:
            out.append(r["name"])
    return out


def business_type(rec, fit):
    tr = rec.get("traits") or {}
    if fit and fit not in ("stockroom", "office", "lobby", "guest_room") and fit in PLACE or fit in TYPES:
        return PLACE.get(fit, fit)
    if tr.get("use") in CIVIC_USE:
        return CIVIC_USE[tr["use"]]
    if fit in PLACE:
        return PLACE[fit]
    return None


def building(rid, raw, rec, pl):
    kind = rec.get("kind", "house")
    plans = raw["plans"]
    rooms, doors = [], []
    seen = Counter()
    for k, p in enumerate(plans):
        for r in p["rooms"]:
            r = dict(r)
            seen[r["name"]] += 1
            if seen[r["name"]] > 1:
                r["name"] = f"{r['name']}~{seen[r['name']]}"
            r["_plan"] = k
            rooms.append(r)
        for d in p["doors"]:
            d = dict(d)
            d["_plan"] = k
            doors.append(d)
    furn = raw.get("furniture", [])
    leaves = [f for i, f in enumerate(furn) if not any(g.get("parent") == i for g in furn)]
    by_room = defaultdict(list)
    for f in furn:
        by_room[(f["room"], f.get("floor", 0))].append(f)
    tr = rec.get("traits") or {}
    dwelling_bldg = kind in DWELLING_KINDS or (kind == "farm" and rid.endswith("-house"))
    out_rooms = {}
    tagged = any(r.get("unit") not in (None, "common") for r in rooms)
    # --- units: generator tags first (townhouses U<k>, apartments A..), then store bays, then the whole building
    for r in rooms:
        typ, fit = r.get("type"), r.get("fitout")
        use = FITOUT_USE.get(fit) or USE.get(typ) or ("hall" if typ is None else typ)
        if fit and fit not in FITOUT_USE and typ in ("shop", "store", None, "office", "bar") and not use in ("office",):
            use = "sales"
        unit = r.get("unit")
        name = r["name"]
        if unit is None:
            if name.startswith(("COR", "STAIR", "UHALL", "UCOR", "STAIRHALL", "VEST", "SHALL", "LANDING")) or \
                    (name.startswith(("SH", "UC")) and typ is None):
                unit = "common"
            elif dwelling_bldg:
                # a house is one home; where its generator laid out several (doubles, rows, flats), what's left over --
                # the garage, the cellar -- is the building's, shared
                unit = "common" if tagged else "H"
            elif name.startswith(("SHOP", "BACK", "WC", "BAY")) and name.rstrip("0123456789X").rstrip("~") in ("SHOP", "BACK", "BACKX", "WC", "BAY"):
                unit = "B" + "".join(ch for ch in name if ch.isdigit())[:2] or "B0"
            elif name.startswith(("UF", "UB", "AF", "AB")) and typ in ("bed", "living", "kitchen", "bath"):
                unit = "F" + name[2:].split("_")[0] + "_" + name.split("_")[-1]
            elif name.startswith(("UF", "UB")) and typ == "office":
                unit = "O" + name[2:]
            else:
                unit = "B0"
        z = block_floor(plans[r["_plan"]]["blocks"], r) or [0.0, 2.6]
        fl = r.get("floor", 0)
        rf = by_room.get((r["name"].split("~")[0], fl), [])
        beds = [[f["pos"][0], f["pos"][2], -f["pos"][1], f["yaw"]] for f in rf if f["item"] in BED and f.get("pos")]
        seats = sum(SEAT.get(f["item"], 0) for f in rf)
        conts, stations = [], []
        for i, f in enumerate(rf):
            if f["item"] in CONTAINER and f.get("pos"):
                conts.append({"cid": f"{r['name']}:{CONTAINER[f['item']]}{sum(1 for c in conts if c['type'] == CONTAINER[f['item']])}",
                              "type": CONTAINER[f["item"]], "at": [f["pos"][0], f["pos"][2], -f["pos"][1]]})
            if f["item"] in STATION and f.get("pos"):
                stations.append({"type": STATION[f["item"]], "at": [f["pos"][0], f["pos"][2], -f["pos"][1]], "yaw": f["yaw"]})
        if use == "closet" and not conts:
            conts.append({"cid": f"{r['name']}:wardrobe0", "type": "wardrobe", "at": None})
        out_rooms[r["name"]] = {"use": use, "floor": fl, "z": [round(z[0], 2), round(z[1], 2)], "rect": glb_rect(r), "unit": unit,
                                "fitout": fit, "beds": beds, "seats": seats, "containers": conts, "stations": stations,
                                "area": round((r["rect"][2] - r["rect"][0]) * (r["rect"][3] - r["rect"][1]), 1)}
    # --- units
    units = defaultdict(lambda: {"rooms": []})
    for rn, r in out_rooms.items():
        units[r["unit"]]["rooms"].append(rn)
    hh_total = int(pl.get("households", 0) or 0)
    dwell_units = []
    for uid, u in units.items():
        uses = Counter(out_rooms[rn]["use"] for rn in u["rooms"])
        if uid == "common":
            u["type"] = "common"
        elif uses.get("bedroom") or (uses.get("living") and uses.get("kitchen")):
            u["type"] = "dwelling"
            u["bedrooms"] = uses.get("bedroom", 0)
            dwell_units.append(uid)
        else:
            u["type"] = "business"
            fits = Counter(out_rooms[rn]["fitout"] for rn in u["rooms"] if out_rooms[rn]["fitout"])
            ptype = None
            for fit, _ in fits.most_common():
                ptype = business_type(rec, fit)
                if ptype and ptype in TYPES:
                    break
            if not ptype:
                ptype = business_type(rec, None)
            if not ptype:
                stores = tr.get("stores") or []
                if stores:
                    st = stores[min(len(stores) - 1, int("".join(ch for ch in uid if ch.isdigit()) or 0))]
                    ptype = PLACE.get(st.get("type"), st.get("type"))
            u["place"] = ptype if ptype in TYPES else (ptype or "insurance_office")
    # households per dwelling unit: one each (a generator's unit); a single-plan multi-family house shares its rooms
    for uid in dwell_units:
        units[uid]["households"] = 1
    if dwelling_bldg and len(dwell_units) == 1 and hh_total > 1:
        units[dwell_units[0]]["households"] = hh_total
    # access
    for rn, r in out_rooms.items():
        ut = units[r["unit"]]["type"]
        if ut == "dwelling":
            r["access"] = "private"
        elif ut == "common":
            r["access"] = "common" if dwell_units else "public"
        else:
            r["access"] = "public" if r["use"] in PUBLIC_USES or r["use"] == "hall" else ("staff" if r["use"] in STAFF_USES or r["use"] in ("bath", "kitchen") else "public")
    # --- doors
    out_doors = []
    for d in doors:
        rs = rooms_of_door([r for r in rooms if r["_plan"] == d["_plan"]], d)
        ext = bool(d.get("ext"))
        if ext:
            rs = rs[:1] + ["outside"]
        side = [out_rooms[x] for x in rs if x in out_rooms]
        types_ = {units[s["unit"]]["type"] for s in side}
        accs = {s["access"] for s in side}
        if "dwelling" in types_:
            # the unit's own entrance and its inside doors
            lock = "residents" if (ext or "common" in {s["unit"] for s in side} or len({s["unit"] for s in side}) > 1) else "open"
            if not ext and any(s["use"] == "bath" for s in side):
                lock = "privacy"
        elif "business" in types_:
            if "staff" in accs and "public" in accs or (ext and "staff" in accs and "public" not in accs):
                lock = "staff"
            elif any(s["use"] == "office" and s["containers"] and any(c["type"] == "safe" for c in s["containers"]) for s in side):
                lock = "manager"
            elif ext:
                lock = "hours"
            else:
                lock = "open"
        else:
            lock = "hours" if ext and not dwell_units else ("residents" if ext else "open")
        out_doors.append({"node": "door_" + d["name"], "rooms": rs, "ext": ext, "floor": d.get("floor", 0),
                          "at": [round(d["at"][0], 2), round(-d["at"][1], 2)], "lock": lock})
    # --- delivery points and posts
    for uid, u in units.items():
        if u["type"] == "common":
            continue
        own = set(u["rooms"])
        # the unit's own door: off the shared hall where it has one (a flat), else an outside door at ground level
        to_common = [d for d in out_doors if own & set(d["rooms"]) and "common" in {out_rooms[x]["unit"] for x in d["rooms"] if x in out_rooms}]
        outside = [d for d in out_doors if own & set(d["rooms"]) and d["ext"] and d["floor"] == 0]
        outside.sort(key=lambda d: ("front" not in d["node"] and "entry" not in d["node"] and "main" not in d["node"], "back" in d["node"]))
        cand = to_common + outside if u["type"] == "dwelling" else outside + to_common
        if u["type"] == "dwelling":
            u["delivery"] = {"door": cand[0]["node"] if cand else None, "to": "resident"}
            u["containers"] = {"owner": "household"}
        else:
            rbu = defaultdict(list)
            for rn in u["rooms"]:
                rbu[out_rooms[rn]["use"]].append(rn)
            u["posts"] = posts_for(f"{rid}/{uid}", u["place"], rbu)
            front = next((p["role"] for p in u["posts"] if p["role"] in FRONT_ROLES), u["posts"][0]["role"] if u["posts"] else None)
            pub = [d for d in cand if d["lock"] in ("hours", "open")] or cand
            u["delivery"] = {"door": pub[0]["node"] if pub else None, "to": f"on_duty:{front}" if front else "owner"}
    # container owners
    for rn, r in out_rooms.items():
        u = units[r["unit"]]
        for c in r["containers"]:
            if u["type"] == "dwelling":
                c["owner"] = "occupant" if r["use"] == "bedroom" or c["type"] in ("dresser", "wardrobe") else "household"
            elif u["type"] == "business":
                c["owner"] = "role:manager" if c["type"] in ("safe", "file_cabinet") else ("post" if c["type"] in ("desk", "register", "teller_drawer") else "business")
            else:
                c["owner"] = "public" if c["type"] == "po_boxes" else "building"
    purposes = sorted({u.get("place") for u in units.values() if u["type"] == "business"} | ({"dwelling"} if dwell_units else set()))
    return {"kind": kind, "purpose": purposes, "rooms": out_rooms, "doors": out_doors, "units": dict(units),
            "audit_ok": (raw.get("audit") or {}).get("ok")}


def main(towns):
    placement = {e["id"]: e for e in json.load(open(os.path.join(GD, "placement.json")))["structures"]}
    by_town = defaultdict(dict)
    missing = Counter()
    for eid, e in placement.items():
        if e["kind"] == "crossing":
            continue
        town = e.get("settlement") or "_country"
        if towns and town not in towns:
            continue
        model = e.get("model") or eid
        rp = os.path.join(RAW, model + ".json")
        cp = os.path.join(CAT, model + ".json")
        if not os.path.exists(rp) or not os.path.exists(cp):
            missing[town] += 1
            continue
        by_town[town][eid] = building(eid, json.load(open(rp)), json.load(open(cp)), e)
    os.makedirs(OUT, exist_ok=True)
    for town, blds in sorted(by_town.items()):
        units = Counter(u["type"] for b in blds.values() for u in b["units"].values())
        posts = sum(len(u.get("posts", [])) for b in blds.values() for u in b["units"].values())
        beds = sum(len(r["beds"]) for b in blds.values() for r in b["rooms"].values())
        no_purpose = [i for i, b in blds.items() if not b["purpose"]]
        with open(os.path.join(OUT, town + ".json"), "w") as f:
            json.dump({"_about": "Rooms, units, doors, posts of every building in " + town + " (tools/rooms/make_rooms.py; read by NpcOccupancy)",
                       "settlement": town, "buildings": blds}, f, separators=(",", ":"))
        print(f"{town}: {len(blds)} buildings, units {dict(units)}, posts {posts}, beds {beds}"
              + (f"; NO PURPOSE: {' '.join(no_purpose[:12])}" if no_purpose else "") + (f"; {missing[town]} without raw plans" if missing[town] else ""))


if __name__ == "__main__":
    main(set(sys.argv[1:]))
