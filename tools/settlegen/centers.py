#!/usr/bin/env python3
"""
centers.py -- procedural strip centres, lifestyle centres and industrial parks for the settlement generator
(research/urban_layout/07_centers_and_industry.md: why each element is where it is; measured examples in
research/urban_layout/centers/).

Every generator is a pure function of (site, kind, rng): no globals, no neighbour queries (the procgen principles:
determinism and locality). Units are metres in the town's local frame: u along the frontage road, v away from it
(the road edge is at v = site.v0; the back of the site is v1). A plan is a dict of lists:

  buildings  {poly, kind (map_expanded BCOL kind), role, tenant, storeys, depth, docks}
  areas      {poly, kind (AREA_COL kind: parking, lot, plaza, lawn, pool)}
  lines      {pts, cls (street / alley), what}
  marks      {at, text}
  stats      the numbers the plan was built to (GLA, stalls, ratio, coverage) for the checks

place(town, plan) writes a plan into a map_expanded Town. Tenant categories only -- never brand names (the
catalog rule: research/buildings, remake/research/CATALOG_SPEC.md).
"""
import math
import random

FT = 0.3048
SQFT = 0.092903
STALL = 32.0                      # m2 of parking field per stall, aisles included (300-350 sq ft gross)
BAY = 24 * FT                     # the in-line bay module


# ------------------------------------------------------------------ sites and plans
class Site:
    """A rectangle in the town frame: u0..u1 along the frontage road, v0 (road edge) .. v1 (back).
    side_road: 'u0' or 'u1' if a cross street runs along that end (a corner site), else None."""
    def __init__(self, u0, u1, v0, v1, side_road=None):
        self.u0, self.u1, self.v0, self.v1, self.side_road = u0, u1, v0, v1, side_road

    @property
    def w(self):
        return self.u1 - self.u0

    @property
    def d(self):
        return self.v1 - self.v0


def rect(u0, u1, v0, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def new_plan():
    return {"buildings": [], "areas": [], "lines": [], "marks": [], "stats": {}}


# ------------------------------------------------------------------ tenants (07 §2, §3)
TENANTS = {
    "convenience": ["convenience_store", "nail_salon", "dry_cleaner", "takeout_pizza", "takeout_chinese", "tax_preparer",
                    "phone_store", "laundromat", "insurance_agent", "liquor_party_store", "barber", "dollar_store", "video_rental"],
    "neighborhood_anchor": ["supermarket"],
    "neighborhood_junior": ["drugstore", "hardware_store", "discount_variety"],
    "neighborhood_inline": ["bank_branch", "hair_salon", "dentist", "takeout_pizza", "pet_supply", "video_rental", "dry_cleaner",
                            "nail_salon", "fitness_studio", "optician", "mail_and_ship", "family_restaurant", "liquor_party_store"],
    "community_anchor": ["discount_department_store", "supermarket", "home_furnishings"],
    "community_junior": ["drugstore", "shoe_store", "apparel_discount", "craft_store", "electronics", "books", "sporting_goods",
                         "auto_parts", "pet_supply"],
    "community_inline": ["mattress_store", "hair_salon", "mobile_phone", "sandwich_shop", "cards_and_gifts", "nail_salon",
                         "tanning_salon", "rent_to_own", "bank_branch", "chinese_buffet", "optician", "fabric_store"],
    "power_anchor": ["home_improvement", "warehouse_club", "discount_department_store", "electronics_superstore",
                     "office_supply", "sporting_goods_superstore", "bed_and_bath", "off_price_apparel", "pet_superstore", "toy_superstore"],
    "power_inline": ["mattress_store", "mobile_phone", "sandwich_shop", "nail_salon", "cards_and_gifts"],
    "pad": ["fast_food_drive_thru", "coffee_drive_thru", "bank_drive_thru", "pharmacy_drive_thru", "sit_down_chain_restaurant",
            "auto_service_quick_lube", "gas_station"],
    "lifestyle_anchor": ["cinema", "bookstore", "upscale_department_store"],
    "lifestyle_inline": ["apparel_specialty", "shoe_specialty", "home_goods_boutique", "jewelry", "cosmetics", "cafe",
                         "restaurant_patio", "ice_cream", "toy_specialty", "outdoor_gear", "electronics_showroom", "fitness_studio",
                         "eyewear", "bakery", "wine_bar"],
    "lifestyle_upper": ["apartments", "offices", "medical_offices"],
    "manufacturing": ["machine_shop", "metal_fabrication", "plastics_molding", "food_processing", "printing", "packaging",
                      "furniture_manufacturing", "tool_and_die", "electronics_assembly", "brewery"],
    "warehouse": ["wholesale_distributor", "third_party_logistics", "building_supply", "beverage_distributor", "moving_and_storage"],
    "bulk_distribution": ["retail_distribution_center", "ecommerce_fulfillment", "grocery_distribution_center"],
    "flex": ["contractor_office_shop", "lab", "showroom", "small_tech", "medical_device", "sign_maker", "hvac_contractor"],
    "contractor_yard": ["landscaper", "excavating", "roofing", "equipment_rental", "concrete_contractor"],
    "self_storage": ["self_storage"],
    "truck_terminal": ["freight_terminal"],
}


def pick(rng, key, used=None):
    pool = TENANTS[key]
    if used is not None:
        fresh = [t for t in pool if t not in used] or pool
        t = rng.choice(fresh)
        used.add(t)
        return t
    return rng.choice(pool)


# ------------------------------------------------------------------ strip centres (07 §2)
STRIP = {   # anchors: [(sqft range, depth ft range)], juniors, inline depth ft, inline count, pads, stalls per 1000, era form
    "convenience": {"anchors": [], "juniors": [], "inline_depth": (55, 70), "inline": (4, 10), "pads": (0, 1), "ratio": 4.0},
    "neighborhood": {"anchors": [((45000, 65000), (180, 220))], "juniors": [((10000, 15000), (90, 120))], "inline_depth": (65, 90),
                     "inline": (8, 18), "pads": (1, 3), "ratio": 4.5},
    "community": {"anchors": [((80000, 120000), (240, 300)), ((50000, 65000), (190, 220))],
                  "juniors": [((20000, 35000), (120, 160))] * 3, "inline_depth": (70, 100), "inline": (10, 24), "pads": (2, 4), "ratio": 4.0},
    "power": {"anchors": [((90000, 140000), (260, 320)), ((30000, 50000), (150, 200)), ((25000, 45000), (140, 180)),
                          ((25000, 40000), (140, 180))],
              "juniors": [((15000, 25000), (110, 140))] * 2, "inline_depth": (70, 90), "inline": (3, 8), "pads": (2, 4), "ratio": 4.5},
}


def strip_site(kind, rng):
    """A site the size this kind of centre needs (07 §1 acreage): (frontage m, depth m)."""
    return {"convenience": (rng.uniform(60, 95), rng.uniform(50, 70)), "neighborhood": (rng.uniform(200, 280), rng.uniform(150, 190)),
            "community": (rng.uniform(330, 450), rng.uniform(200, 260)), "power": (rng.uniform(450, 600), rng.uniform(260, 330))}[kind]


def strip_center(site, kind="neighborhood", rng=None):
    """A strip centre on a site facing its frontage road (07 §2): the store row at the back, anchors at the ends
    (the dumbbell) with their aisles pointing at their doors, in-line bays between, a covered walk, the parking
    field in front sized to the stall ratio, pads with drive-throughs at the road edge, a rear service lane,
    entry drives (the main one centred on the main anchor), a perimeter landscape strip, a pond, the pylon sign."""
    rng = rng or random.Random(0)
    P = STRIP[kind]
    plan = new_plan()
    used = set()
    lane, buffer_back, walk, edge = 9.0, 3.0, 4.5, 4.5           # service lane, rear buffer, the walk, road landscape strip
    # the units: (role, tenant, width m, depth m)
    units = []
    akey = {"neighborhood": "neighborhood", "community": "community", "power": "power"}.get(kind)
    for (a, d) in P["anchors"]:
        area = rng.uniform(*a) * SQFT
        dep = rng.uniform(*d) * FT
        units.append(["anchor", pick(rng, akey + "_anchor", used), area / dep, dep])
    for (a, d) in P["juniors"][:rng.randint(len(P["juniors"]) // 2, len(P["juniors"]))] if P["juniors"] else []:
        area = rng.uniform(*a) * SQFT
        dep = rng.uniform(*d) * FT
        units.append(["junior", pick(rng, akey + "_junior" if akey != "power" else "power_anchor", used), area / dep, dep])
    ndep = rng.uniform(*P["inline_depth"]) * FT
    n_inline = rng.randint(*P["inline"])
    ikey = {"convenience": "convenience", "neighborhood": "neighborhood_inline", "community": "community_inline",
            "power": "power_inline"}[kind]
    inline = []
    for _ in range(n_inline):
        bays = rng.choice((1, 1, 1, 2, 2, 3))
        inline.append(["inline", pick(rng, ikey), bays * BAY, ndep])
    # the order along the row: an anchor at each end (dumbbell), juniors next to anchors, in-line in the middle
    anchors = [u for u in units if u[0] == "anchor"]
    juniors = [u for u in units if u[0] == "junior"]
    left, right = [], []
    for k, a in enumerate(anchors):
        (left if k % 2 == 0 else right).append(a)
    for k, j in enumerate(juniors):
        (left if k % 2 == 1 else right).append(j)
    if kind == "convenience" and inline:
        inline[0][1] = "convenience_store"                      # (the end cap: the convenience anchor)
    row = left + inline + list(reversed(right))
    # fit the row: straight if it fits the frontage, else an L along the side road, else drop in-line bays
    maxdep = max(u[3] for u in row)
    room = site.w - 2 * edge
    total = sum(u[2] for u in row)
    # fit the frontage the way developers do: an L round a corner if there is a cross street; else drop in-line
    # bays, then juniors, then make the anchors deeper and narrower (a deeper box keeps its floor area)
    can_L = site.side_road is not None and site.d > 150
    limit = room * (1.6 if can_L else 1.0)
    while sum(u[2] for u in left + inline + right) > limit and len(inline) > (2 if kind != "convenience" else 3):
        inline.pop(len(inline) // 2)
    for side in (right, left):
        while sum(u[2] for u in left + inline + right) > limit and any(u[0] == "junior" for u in side):
            side.remove(next(u for u in side if u[0] == "junior"))
    max_dep = max(20.0, site.d - 9 - 3 - 4.5 - 4.5 - 30)          # (lane, buffer, walk, edge, the least parking)
    over = sum(u[2] for u in left + inline + right) - limit
    for u in sorted(left + right, key=lambda u: -u[2]):
        if over <= 0:
            break
        area = u[2] * u[3]
        nw = max(u[2] - over, area / max_dep, 25.0)
        over -= u[2] - nw
        u[2], u[3] = nw, min(max_dep, area / nw)
    while sum(u[2] for u in left + inline + right) > limit and inline:
        inline.pop()
    row = left + inline + list(reversed(right))
    maxdep = max(u[3] for u in row)
    total = sum(u[2] for u in row)
    form = "straight" if total <= room else "L"
    # (the row stands where the parking it needs ends: the required field at the stall ratio, plus the pad band;
    #  a deeper site keeps its back as buffer and stormwater -- 07 §2; measured centres run 4-5 per 1,000)
    gla_est = sum(u[2] * u[3] for u in row)
    need = gla_est / SQFT / 1000 * P["ratio"] * STALL
    pads_est = (1 if P["pads"][1] else 0) * 38.0
    park_d = need / max(40.0, room - (maxdep if form == "L" else 0)) * 1.08
    v_front = min(site.v1 - buffer_back - lane - maxdep, site.v0 + edge + pads_est + 4 + park_d + walk)
    min_park = 18.0 if kind == "convenience" else 30.0          # (one double-loaded bay of stalls at the least)
    v_front = max(v_front, site.v0 + edge + min_park + walk)
    room_d = site.v1 - buffer_back - lane - v_front               # (a shallow site: shallower shops)
    if room_d < maxdep:
        for u in row:
            u[3] = min(u[3], max(12.0, room_d))
        maxdep = max(u[3] for u in row)
        v_front = min(v_front, site.v1 - buffer_back - lane - maxdep)
    v_back = v_front + maxdep
    placed = []
    if form == "straight":
        u = site.u0 + edge + (room - total) / 2
        for role, ten, w, d in row:
            placed.append((role, ten, (u, u + w, v_front, v_front + d)))
            u += w
    else:                                                       # the L: the long leg along the back, the short leg down the side
        side_u1 = site.side_road != "u0"                        # (the short leg goes down the end away from the cross street)
        back_len = room - maxdep
        u = site.u0 + edge if side_u1 else site.u0 + edge + maxdep
        leg = []
        for role, ten, w, d in row:
            if (u + w <= site.u0 + edge + back_len + (0 if side_u1 else maxdep)) and not leg:
                placed.append((role, ten, (u, u + w, v_front, v_front + d)))
                u += w
            else:
                leg.append((role, ten, w, d))
        vv = v_front - walk
        for role, ten, w, d in leg:                             # (down the side: width runs along v, depth along u)
            if vv - w < site.v0 + 4.5 + 38 + 12:                  # (the leg stops above the pad band at the road)
                break
            uu1 = site.u1 - edge if side_u1 else site.u0 + edge + d
            placed.append((role, ten, (uu1 - d, uu1, vv - w, vv)))
            vv -= w
    gla = 0.0
    for role, ten, (a, b, c, d_) in placed:
        kindm = "bigbox" if role in ("anchor", "junior") else "strip"
        area = (b - a) * (d_ - c)
        gla += area
        plan["buildings"].append({"poly": rect(a, b, c, d_), "kind": kindm, "role": role, "tenant": ten, "storeys": 1,
                                  "depth": round(min(b - a, d_ - c), 1)})
    us = [p[2][0] for p in placed] + [p[2][1] for p in placed]
    ua, ub = min(us), max(us)
    # the covered walk and the fire lane in front of the row
    plan["areas"].append({"poly": rect(ua, ub, v_front - walk, v_front), "kind": "plaza"})
    # the service lane behind
    plan["lines"].append({"pts": [(ua - 6, v_back + lane / 2), (ub + 6, v_back + lane / 2)], "cls": "alley", "what": "service_lane"})
    # pads at the road edge (15,000 sq ft lots; 3-6k sq ft buildings with a drive-through lane)
    n_pads = rng.randint(*P["pads"]) if site.w > 120 else 0
    main_anchor = next((p for p in placed if p[0] == "anchor"), placed[len(placed) // 2] if placed else None)
    entry_u = (main_anchor[2][0] + main_anchor[2][1]) / 2 if main_anchor else (site.u0 + site.u1) / 2
    entries = [entry_u]
    if site.w > 160:
        entries.append(site.u0 + 25 if abs(entry_u - site.u0) > abs(entry_u - site.u1) else site.u1 - 25)
    pad_d = 38.0
    pad_slots = []
    u = site.u0 + edge + 4
    while u + 36 < site.u1 - edge and len(pad_slots) < n_pads:
        if all(abs((u + 18) - e) > 30 for e in entries):
            pad_slots.append(u)
            u += 48
        else:
            u += 12
    pad_band = pad_d if pad_slots else 0.0
    for pu in pad_slots:
        ten = pick(rng, "pad", used)
        bw, bd = (rng.uniform(16, 22), rng.uniform(14, 20)) if ten != "gas_station" else (14, 10)
        v0p = site.v0 + edge + 6
        plan["buildings"].append({"poly": rect(pu + 6, pu + 6 + bw, v0p + 6, v0p + 6 + bd), "kind": "restaurant" if "restaurant" in ten or "fast_food" in ten or "coffee" in ten else "strip",
                                  "role": "pad", "tenant": ten, "storeys": 1, "depth": round(min(bw, bd), 1)})
        plan["areas"].append({"poly": rect(pu, pu + 36, site.v0 + edge, site.v0 + edge + pad_d), "kind": "parking"})
        if "drive" in ten or ten == "gas_station":               # (the drive-through lane wraps the building)
            plan["lines"].append({"pts": [(pu + 3, v0p + 3), (pu + 3, v0p + bd + 10), (pu + bw + 10, v0p + bd + 10),
                                          (pu + bw + 10, v0p + 3)], "cls": "alley", "what": "drive_thru"})
    # the parking field: between the walk and the pads / landscape strip
    pv0 = site.v0 + edge + pad_band + (4 if pad_band else 0)
    pv1 = v_front - walk
    if form == "L":
        legs = [p for p in placed if p[2][1] - p[2][0] < p[2][3] - p[2][2] and p[0] in ("anchor", "junior", "inline")]
        pu1 = min([p[2][0] for p in placed if p[2][2] < v_front - 1] + [site.u1 - edge]) - walk if site.side_road != "u0" else site.u1 - edge
        pu0 = site.u0 + edge if site.side_road != "u0" else max([p[2][1] for p in placed if p[2][2] < v_front - 1] + [site.u0 + edge]) + walk
    else:
        pu0, pu1 = site.u0 + edge, site.u1 - edge
    if pv1 - pv0 > 10:
        plan["areas"].append({"poly": rect(pu0, pu1, pv0, pv1), "kind": "parking"})
        # aisles perpendicular to the row (they point at the anchors' doors), a double-loaded module of 60 ft
        mod = 60 * FT
        u = pu0 + mod / 2
        while u < pu1 - mod / 4:
            plan["lines"].append({"pts": [(u, pv0), (u, pv1)], "cls": "alley", "what": "aisle"})
            u += mod
        # landscape islands at the aisle ends (a modern code: every 10-15 stalls)
        u = pu0 + mod
        while u < pu1 - 2:
            plan["areas"].append({"poly": rect(u - 1.2, u + 1.2, pv0, pv0 + 5.5), "kind": "lawn"})
            u += mod
    stalls = max(0.0, (pu1 - pu0) * (pv1 - pv0)) / STALL + len(pad_slots) * 30 * 36 / STALL * 0.5
    # entries and the drive along the walk
    for e in entries:
        plan["lines"].append({"pts": [(e, site.v0), (e, pv1)], "cls": "street", "what": "entry_drive"})
    plan["lines"].append({"pts": [(pu0, pv1 - 4), (pu1, pv1 - 4)], "cls": "alley", "what": "fire_lane"})
    # perimeter landscape strip on the road and the pond in a back corner
    plan["areas"].append({"poly": rect(site.u0, site.u1, site.v0, site.v0 + edge), "kind": "lawn"})
    if site.v1 - (v_back + lane) > 12:                         # (the rest of a deep site: buffer, trees, stormwater)
        plan["areas"].append({"poly": rect(site.u0, site.u1, v_back + lane + 2, site.v1), "kind": "lawn"})
    corner_u = site.u0 + 4 if (ua - site.u0) > (site.u1 - ub) else site.u1 - 4 - 30
    if (ua - site.u0 > 34) or (site.u1 - ub > 34):
        plan["areas"].append({"poly": rect(corner_u, corner_u + 30, v_back + lane - 30, v_back + lane), "kind": "pool"})
    plan["marks"].append({"at": (entries[0] + 8, site.v0 + 3), "text": "pylon sign"})
    plan["stats"] = {"type": kind, "form": form, "gla_sqft": round(gla / SQFT), "stalls": round(stalls),
                     "stalls_per_1000": round(stalls / (gla / SQFT / 1000), 2) if gla else 0, "target_ratio": P["ratio"],
                     "pads": len(pad_slots), "units": len(placed), "site_acres": round(site.w * site.d / 4046.9, 1),
                     "coverage": round(gla / (site.w * site.d), 3)}
    return plan


# ------------------------------------------------------------------ lifestyle centre (07 §2, open-air main street)
def lifestyle_center(site, rng=None, upper_floors=True):
    """An open-air 'main street' centre: a pedestrian street (with slow traffic and angle parking) running back from
    the frontage road, two-storey shop blocks either side (standard boxes, varied fronts), mid-block passages to the
    parking behind, a green at the middle, an evening anchor (cinema or bookstore) terminating the vista, restaurant
    pads at the road corners. Upper floors: apartments or offices (the newer town-centre form)."""
    rng = rng or random.Random(0)
    plan = new_plan()
    used = set()
    uc = (site.u0 + site.u1) / 2
    street_w, block_d = 18.0, rng.uniform(24, 32)
    v_start, v_end = site.v0 + 40, site.v1 - 70
    plan["lines"].append({"pts": [(uc, site.v0), (uc, v_end + 10)], "cls": "street", "what": "main_street"})
    plan["areas"].append({"poly": rect(uc - street_w / 2 - 4, uc + street_w / 2 + 4, v_start, v_end), "kind": "plaza"})
    green_v = (v_start + v_end) / 2
    gla = 0.0
    for sx in (-1, 1):
        u_in = uc + sx * (street_w / 2 + 4)
        u_out = u_in + sx * block_d
        v = v_start
        while v < v_end - 15:
            if abs(v - green_v) < 22:                           # (the green: the street widens into a square)
                v = green_v + 22
                continue
            run = rng.uniform(45, 75)
            run = min(run, v_end - v)
            # shop fronts in the block: 25-40 ft each
            vv = v
            while vv < v + run - 6:
                fw = min(rng.uniform(25, 40) * FT * (2 if rng.random() < 0.25 else 1), v + run - vv)
                a, b = sorted((u_in, u_out))
                plan["buildings"].append({"poly": rect(a, b, vv, vv + fw), "kind": "store", "role": "inline",
                                          "tenant": pick(rng, "lifestyle_inline"), "storeys": 2 if upper_floors else 1,
                                          "upper": pick(rng, "lifestyle_upper") if upper_floors else None, "depth": block_d})
                gla += (b - a) * fw
                vv += fw
            v += run + 8                                        # (a mid-block passage to the parking)
        # the parking behind each row: about 5 per 1,000 sq ft of the side's shops (07 §2)
        side_gla = sum((abs(bb_["poly"][1][0] - bb_["poly"][0][0]) * abs(bb_["poly"][2][1] - bb_["poly"][1][1]))
                       for bb_ in plan["buildings"] if (bb_["poly"][0][0] - uc) * sx > 0) * (2 if upper_floors else 1)
        pw = min(abs((site.u0 + 6 if sx < 0 else site.u1 - 6) - u_out),
                 max(30.0, side_gla / SQFT / 1000 * 5.0 * STALL / (v_end - v_start + 40)))
        a, b = sorted((u_out + sx * 6, u_out + sx * (6 + pw)))
        plan["areas"].append({"poly": rect(a, b, v_start - 20, v_end + 20), "kind": "parking"})
        plan["lines"].append({"pts": [((a + b) / 2, site.v0), ((a + b) / 2, v_end + 20)], "cls": "alley", "what": "parking_drive"})
    plan["areas"].append({"poly": rect(uc - street_w / 2 - 14, uc + street_w / 2 + 14, green_v - 20, green_v + 20), "kind": "park"})
    plan["marks"].append({"at": (uc, green_v), "text": "the green"})
    # the anchor at the head of the street
    aw, ad = rng.uniform(45, 60), rng.uniform(40, 55)
    plan["buildings"].append({"poly": rect(uc - aw / 2, uc + aw / 2, v_end + 12, v_end + 12 + ad), "kind": "bigbox", "role": "anchor",
                              "tenant": pick(rng, "lifestyle_anchor", used), "storeys": 2, "depth": ad})
    gla += aw * ad
    # restaurant pads at the two road corners of the street
    for sx in (-1, 1):
        u0 = uc + sx * (street_w / 2 + 10)
        a, b = sorted((u0, u0 + sx * 22))
        plan["buildings"].append({"poly": rect(a, b, site.v0 + 8, site.v0 + 26), "kind": "restaurant", "role": "pad",
                                  "tenant": "restaurant_patio", "storeys": 1, "depth": 18})
    plan["areas"].append({"poly": rect(site.u0, site.u1, site.v0, site.v0 + 5), "kind": "lawn"})
    stalls = sum(abs(a["poly"][1][0] - a["poly"][0][0]) * abs(a["poly"][2][1] - a["poly"][1][1])
                 for a in plan["areas"] if a["kind"] == "parking") / STALL
    plan["stats"] = {"type": "lifestyle", "gla_sqft": round(gla / SQFT), "stalls": round(stalls),
                     "stalls_per_1000": round(stalls / (gla / SQFT / 1000), 2) if gla else 0,
                     "site_acres": round(site.w * site.d / 4046.9, 1)}
    return plan


# ------------------------------------------------------------------ industrial parks (07 §3)
# building types: (office share, depth m range, coverage target, truck court m, loading, tenant key, map kind)
IND = {
    "manufacturing": {"depth": (40, 80), "court": 37, "load": "rear", "office_front": 12, "lot_w": (55, 120), "kind": "industrial"},
    "warehouse": {"depth": (45, 85), "court": 40, "load": "rear", "office_front": 8, "lot_w": (60, 140), "kind": "warehouse"},
    "bulk_distribution": {"depth": (100, 170), "court": 57, "load": "cross", "office_front": 0, "lot_w": (220, 360), "kind": "warehouse"},
    "flex": {"depth": (25, 36), "court": 25, "load": "rear", "office_front": 0, "lot_w": (40, 90), "kind": "industrial"},
    "contractor_yard": {"depth": (14, 22), "court": 0, "load": "yard", "office_front": 0, "lot_w": (45, 80), "kind": "shed"},
    "self_storage": {"depth": (9, 9), "court": 0, "load": "units", "office_front": 0, "lot_w": (90, 130), "kind": "shed"},
    "truck_terminal": {"depth": (20, 28), "court": 40, "load": "both_long", "office_front": 0, "lot_w": (150, 220), "kind": "warehouse"},
}
MIX = {   # era -> building-type weights (07 §3: rail districts, the postwar park, the logistics park)
    "rail": {"manufacturing": 6, "warehouse": 3, "contractor_yard": 1},
    "postwar": {"manufacturing": 4, "warehouse": 3, "flex": 2, "contractor_yard": 2, "self_storage": 1, "truck_terminal": 1},
    "logistics": {"bulk_distribution": 4, "warehouse": 3, "flex": 2, "truck_terminal": 1, "self_storage": 1},
}


def _wpick(rng, weights):
    tot = sum(weights.values())
    r = rng.uniform(0, tot)
    for k, w in weights.items():
        r -= w
        if r <= 0:
            return k
    return k


def industrial_park(site, era="postwar", rng=None):
    """A planned industrial park (07 §3): one entrance from the frontage road, a spine collector to a loop at the
    back (trucks circulate without turning round), lots on both sides of the spine cut to their building type; each
    building parallel to its road with the office and car parking in front (the address), the truck court and docks
    behind (cross-dock: courts on both long sides), trailer stalls, a lawn setback with trees; contractor yards fenced,
    self-storage in rows; a detention pond by the entrance; for the 'rail' era a spur along the back with
    rail-served buildings."""
    rng = rng or random.Random(0)
    plan = new_plan()
    road_w, setback = 12.0, rng.uniform(12, 18)
    loop_v = site.v1 - 60
    n_sp = max(1, round(site.w / {"rail": 240.0, "postwar": 230.0, "logistics": 420.0}[era]))   # (measured: New Berlin's roads
    #  run every 150-250 m; lots back to back ~100-120 m deep; logistics deeper for the bulk boxes)
    pitch = site.w / n_sp
    spines = [site.u0 + pitch * (k + 0.5) for k in range(n_sp)]
    uc = spines[0]
    for sp in spines:
        plan["lines"].append({"pts": [(sp, site.v0 if sp == uc else site.v0 + 60), (sp, loop_v)], "cls": "street", "what": "spine"})
    plan["lines"].append({"pts": [(spines[0], loop_v), (spines[-1], loop_v)] if n_sp > 1 else [(site.u0 + 40, loop_v), (site.u1 - 40, loop_v)],
                          "cls": "street", "what": "loop"})
    if n_sp > 1:                                              # (a front frontage road links the spines inside the entrance)
        plan["lines"].append({"pts": [(spines[0], site.v0 + 60), (spines[-1], site.v0 + 60)], "cls": "street", "what": "front_road"})
    if era == "rail":
        plan["lines"].append({"pts": [(site.u0, site.v1 - 6), (site.u1, site.v1 - 6)], "cls": "alley", "what": "rail_spur"})
    pond = (uc + road_w / 2 + 4, uc + road_w / 2 + 48, site.v0 + 6, site.v0 + 46)
    plan["areas"].append({"poly": rect(*pond), "kind": "pool"})
    plan["marks"].append({"at": (uc, site.v0 + 3), "text": "park sign"})
    built, lot_area = 0.0, 0.0
    weights = MIX[era]
    for sp, sx in [(sp, sx) for sp in spines for sx in (-1, 1)]:   # lots along each spine, each side, back to back
        uc = sp
        u_road = uc + sx * road_w / 2
        u_far = (sp - pitch / 2 + 2) if sx < 0 else (sp + pitch / 2 - 2)
        depth_avail = abs(u_far - u_road)
        first = site.v0 + (50 if (sp == spines[0] and sx > 0) else 8) if n_sp == 1 else site.v0 + 66
        v = first if not (sp == spines[0] and sx > 0) else site.v0 + 50 + (16 if n_sp > 1 else 0)
        while v < loop_v - 30:
            t = _wpick(rng, weights)
            T = IND[t]
            lw = min(rng.uniform(*T["lot_w"]), loop_v - 12 - v)
            if lw < 40:
                break
            bd = min(rng.uniform(*T["depth"]), depth_avail - setback - 18 - T["court"] - 6)
            if bd < 8:
                t, T = "contractor_yard", IND["contractor_yard"]
                bd = rng.uniform(*T["depth"])
            lot_area += lw * depth_avail
            # the frame across the lot, from the spine outward: setback lawn, car parking, building, truck court, buffer
            def U(off):
                return u_road + sx * off
            plan["areas"].append({"poly": rect(*sorted((U(0), U(setback))), v + 2, v + lw - 2), "kind": "lawn"})
            if t == "self_storage":
                rows_u = U(setback)
                k = 0
                while abs(rows_u - u_road) + 9 < depth_avail - 4:
                    a, b = sorted((rows_u, rows_u + sx * 9))
                    plan["buildings"].append({"poly": rect(a, b, v + 6, v + lw - 6), "kind": "shed", "role": "storage_row",
                                              "tenant": "self_storage", "storeys": 1, "depth": 9})
                    built += 9 * (lw - 12)
                    rows_u += sx * (9 + 8)
                    k += 1
                plan["areas"].append({"poly": rect(*sorted((U(setback), U(depth_avail - 2))), v + 2, v + lw - 2), "kind": "lot"})
                v += lw
                continue
            park_d = 18.0 if t not in ("contractor_yard",) else 8.0
            b0 = setback + park_d
            if T["load"] == "cross":                            # (cross-dock: a court in front too; cars at the ends)
                b0 = setback + T["court"]
            plan["areas"].append({"poly": rect(*sorted((U(setback), U(b0))), v + 4, v + lw - 4),
                                  "kind": "parking" if T["load"] != "cross" else "lot"})
            bw = lw - rng.uniform(16, 28)
            a, b = sorted((U(b0), U(b0 + bd)))
            plan["buildings"].append({"poly": rect(a, b, v + (lw - bw) / 2, v + (lw + bw) / 2), "kind": T["kind"], "role": t,
                                      "tenant": pick(rng, t), "storeys": 1, "depth": round(bd, 1),
                                      "docks": max(0, int(bw * bd / 930)) if T["court"] else 0,
                                      "loading": T["load"]})
            built += bw * bd
            if T["court"]:                                      # the truck court behind (and trailer stalls along its back)
                c0, c1 = sorted((U(b0 + bd), U(b0 + bd + T["court"])))
                plan["areas"].append({"poly": rect(c0, c1, v + 4, v + lw - 4), "kind": "lot"})
            if T["load"] == "yard":                             # (the contractor's fenced yard behind the shop)
                c0, c1 = sorted((U(b0 + bd + 2), U(depth_avail - 4)))
                plan["areas"].append({"poly": rect(c0, c1, v + 4, v + lw - 4), "kind": "lot"})
            v += lw
    plan["stats"] = {"type": "industrial_park", "era": era, "buildings": len(plan["buildings"]),
                     "built_sqft": round(built / SQFT), "coverage": round(built / (site.w * site.d), 3),
                     "site_acres": round(site.w * site.d / 4046.9, 1),
                     "mix": {k: sum(1 for b in plan["buildings"] if b["role"] == k) for k in IND}}
    return plan


# ------------------------------------------------------------------ into the map
def place(town, plan, v_road=0.0, dirn=1, label=None):
    """Write a plan into a map_expanded Town. The plan's v runs away from its frontage road; the road's edge lies at
    the town's v = v_road and the site extends toward +v (dirn 1) or -v (dirn -1)."""
    def g(u, v):
        return town.g(u, v_road + dirn * v)
    for a in plan["areas"]:
        town.area([g(u, v) for u, v in a["poly"]], a["kind"])
    for ln in plan["lines"]:
        town.street([(u, v_road + dirn * v) for u, v in ln["pts"]], "alley" if ln["cls"] == "alley" else "street")
    for b in plan["buildings"]:
        town.bld([g(u, v) for u, v in b["poly"]], b["kind"])
    if label:
        us = [u for b in plan["buildings"] for u, _ in b["poly"]]
        vs = [v for b in plan["buildings"] for _, v in b["poly"]]
        town.mark((min(us) + max(us)) / 2, v_road + dirn * (max(vs) + 8), label)
    return plan["stats"]
