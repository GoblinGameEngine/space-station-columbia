"""
decals.py -- where each type's decals go (tools/assets/decals.py makes the images; research/vehicles/TEXTURES.md).

A decal is [image, position, normal (out of the surface), up (the image's top), width, height, tint or None], in the
Blender frame (y forward, z up); the blueprint carries them in the Godot frame and the game projects each one onto
the body (a Decal node riding with it). "plate" and "num" are picked per vehicle in the game (plate_0..7, num_01..24).
"""

WHITE, BLACK, NAVY, RED, GOLD = (250, 250, 250), (24, 24, 26), (24, 40, 82), (190, 30, 30), (214, 170, 40)

# type -> what it wears: (where, image or word, tint); where: side, rear, chevrons, star, envelope, hull, num
LIVERIES = {
    "fire_engine": [("side", "FIRE DEPT", GOLD), ("chevrons",), ("num", None, WHITE)],
    "ladder_truck": [("side", "FIRE DEPT", GOLD), ("chevrons",), ("num", None, WHITE)],
    "fire_chief_car": [("side", "FIRE DEPT", GOLD)],
    "police_car": [("side", "MARSHAL", NAVY), ("num", None, NAVY)],
    "police_suv": [("side", "MARSHAL", NAVY), ("num", None, NAVY)],
    "taxi": [("side", "TAXI", BLACK), ("num", None, BLACK)],
    "ambulance": [("side", "AMBULANCE", (30, 90, 200)), ("star",), ("rear", "AMBULANCE", (30, 90, 200))],   # (blue: its stripe is red)
    "mail_truck": [("side", "POST", NAVY)],
    "school_bus": [("side", "SCHOOL BUS", BLACK), ("rear", "SCHOOL BUS", BLACK), ("num", None, BLACK)],
    "transit_bus": [("num", None, WHITE)],
    "public_works_pickup": [("side", "PUBLIC WORKS", BLACK)],
    "lifeguard_truck": [("side", "LIFEGUARD", RED)],
    "tram_maintenance_car": [("side", "TRAMWAYS", BLACK), ("chevrons",)],
    "garbage_truck": [("side", "SANITATION", WHITE), ("chevrons",)],
    "recycling_truck": [("side", "RECYCLING", WHITE), ("chevrons",)],
    "armored_truck": [("side", "SECURE TRANSIT", GOLD)],
    "paratransit_van": [("side", "PARATRANSIT", NAVY)],
    "hotel_shuttle": [("side", "HOTEL SHUTTLE", NAVY)],
    "ice_cream_truck": [("side", "ICE CREAM", RED)],
    "parcel_van": [("side", "PARCELS", BLACK)],
    "tow_truck": [("chevrons",)], "street_sweeper": [("chevrons",)], "yard_tug": [("chevrons",)], "dump_truck": [("chevrons",)],
    "box_truck": [("chevrons",)], "semi_truck": [("chevrons",)], "mobile_crane": [("chevrons",)], "cement_mixer": [("chevrons",)],
    "coast_guard_boat": [("hull", "COAST GUARD", WHITE)],
    "rescue_aerostat": [("envelope", "RESCUE", RED)],
    "cargo_aerostat": [("envelope", "FREIGHT", (40, 100, 92))],
    "passenger_shuttle": [("side", "COLUMBIA", (24, 110, 110))],
}


def word_image(w):
    return "word_" + w.replace(" ", "_")


def aspect(word):
    return 0.82 * len(word) * 0.8 + 0.3            # (decals.py: 0.8 h a glyph and 0.1 h tracking, 0.12 h pad a side)


def side_box(b):
    """Where a flank's lettering goes: the cargo body's middle, or the body's below the windows. (y, z, length, height, x)."""
    L = b.L
    C = L.spec.get("cargo") or {}
    if C and C.get("kind") in ("box", "tank"):
        top = C.get("top_z") or (C.get("tank_z", 2.0) + C.get("tank_r", 0.5) * 0.5)
        return (C["y0"] + C["y1"]) / 2, (C["floor_z"] + top) / 2, (C["y0"] - C["y1"]) * 0.8, (top - C["floor_z"]) * 0.45, C["half_w"]
    toe = getattr(L, "toe", L.nose)
    tail = getattr(L, "tail_in", L.tail)
    y = (toe + tail) / 2
    z = getattr(L, "belt", 1.2) - 0.22
    return y, z, (toe - tail) * 0.7, 0.20, None


def place(b, vtype, plates=True):
    """The type's decals for its blueprint (Blender frame)."""
    L = b.L
    out = []
    C = L.spec.get("cargo") or {}
    road = plates and not L.spec.get("aero") and L.spec.get("space") is None and getattr(L, "axles", [])
    if road:
        rear_y = C["y1"] if C else L.tail
        if not L.spec.get("trailer"):
            out.append(["plate", (0.0, L.nose + 0.012, L.spec.get("bumper_z", 0.5) + 0.14), (0, 1, 0), (0, 0, 1), 0.52, 0.11, None])
        out.append(["plate", (0.0, rear_y - 0.012, max(0.45, L.spec.get("tail_lamp_z", 1.0) - 0.30)), (0, -1, 0), (0, 0, 1), 0.52, 0.11, None])
    # (the instruments are real now: the binnacle's live dials, Builder.station -> the blueprint's "gauges")
    for item in LIVERIES.get(vtype, []):
        where = item[0]
        if where in ("side", "star", "num"):
            y, z, ln, hh, xo = side_box(b)
            for sx in (1, -1):
                x = xo if xo is not None else b.surf_x(y, z)
                n = (sx, 0, 0)
                if where == "side":
                    w = min(ln, hh * aspect(item[1]))
                    h = w / aspect(item[1])
                    out.append([word_image(item[1]), (sx * (x + 0.01), y, z), n, (0, 0, 1), w, h, item[2]])
                elif where == "star":
                    out.append(["star_of_life", (sx * (x + 0.01), y - ln * 0.62, z), n, (0, 0, 1), hh * 1.6, hh * 1.6, None])
                else:                               # a fleet number, ahead of the lettering
                    out.append(["num", (sx * (x + 0.01), y + ln * 0.6, z), n, (0, 0, 1), hh * 1.4, hh * 1.1, item[2]])
        elif where in ("rear", "chevrons"):
            rear_y = (C["y1"] if C else L.tail) - 0.012
            hw = (C.get("half_w") if C else L.half_w) or 1.0
            if where == "rear":
                h = 0.16
                out.append([word_image(item[1]), (0.0, rear_y, (L.spec.get("tail_lamp_z", 1.0) + 0.45)), (0, -1, 0), (0, 0, 1),
                            min(hw * 1.6, h * aspect(item[1])), h, item[2]])
            else:
                out.append(["chevrons", (0.0, rear_y, 0.80), (0, -1, 0), (0, 0, 1), hw * 1.8, 0.28, None])
        elif where == "envelope":
            el, er, ey, ez = L.spec["aero"]["env"]
            h = er * 0.32
            for sx in (1, -1):
                out.append([word_image(item[1]), (sx * er * 0.99, ey, ez), (sx, 0, 0), (0, 0, 1), h * aspect(item[1]), h, item[2]])
    return out


def hull(H, vtype):
    """A boat's: its name of service along the topsides, midships."""
    out = []
    for item in LIVERIES.get(vtype, []):
        if item[0] == "hull":
            z = H.free * 0.55
            h = max(0.18, H.free * 0.30)
            for sx in (1, -1):
                out.append([word_image(item[1]), (sx * (H.half_beam(0.0) + 0.01), 0.0, z), (sx, 0, 0), (0, 0, 1), h * aspect(item[1]), h, item[2]])
    return out
