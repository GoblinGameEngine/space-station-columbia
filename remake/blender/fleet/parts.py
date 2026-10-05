"""
parts.py -- the fleet's small unpowered and single-track vehicles as token recipes: bikes, scooters, chairs, carts,
strollers, trolleys. They ride on no board: their tube frame IS their structure and shows on purpose (the style), so
each is a list of tokens -- the frame, each wheel, the seat, the basket, the handlebar -- built from a few primitives.

A recipe returns [(token id, role, slot, side, [primitives])], a primitive being one of
  ("tube", [points], radius, material)          ("box", centre, half sizes, material)
  ("wheel", centre, radius, width, material)    ("disc", centre, radius, thickness, material)   (a disc in the x-plane)
  ("lathe", profile, centre, material, axis)    axis "x" | "y" | "z": the profile's along-axis
  ("seat", centre, (half w, half l), material)  ("wire", centre, half sizes, material)   (a wire basket: an open box of rods)
Coordinates: Blender (y forward, z up); y = 0 at the middle of the wheelbase.
"""
import math

V = None    # (mathutils.Vector, set by the builder)


def W(c, r, w=0.035, m="rubber"):
    return ("wheel", c, r, w, m)


def T(pts, r=0.016, m="paint"):
    return ("tube", pts, r, m)


def B(c, h, m="paint"):
    return ("box", c, h, m)


def bicycle_like(wb, r, frame_m="paint", rider=0.78, bar=1.00, basket=None, rear_rack=False, tri=False, child=False):
    yf, yb = wb / 2, -wb / 2
    bb = (0, -0.05 * wb, r * 0.95)
    seat = (0, yb + wb * 0.33, rider)
    head = (0, yf - 0.12 * wb / 1.05, bar - 0.12)
    out = [("frame", "frame_shown", "frame", "C", [
        T([bb, seat], 0.016, frame_m), T([seat, head], 0.016, frame_m), T([bb, head], 0.019, frame_m),
        T([bb, (0.05, yb, r), seat], 0.010, frame_m), T([bb, (-0.05, yb, r), seat], 0.010, frame_m),
        T([head, (0, yf, r)], 0.014, "chrome"), B(bb, (0.04, 0.04, 0.04), "black")])]
    out.append(("bars", "equipment", "handlebar", "C", [T([(-0.26, head[1] + 0.04, bar), (0, head[1], bar - 0.02), (0.26, head[1] + 0.04, bar)], 0.012, "chrome"),
                                                         T([head, (0, head[1], bar - 0.02)], 0.013, "chrome")]))
    out.append(("saddle", "seat", "saddle", "C", [B((0, seat[1], seat[2] + 0.04), (0.08, 0.13, 0.03), "seat")]))
    if tri:                                                 # an adult tricycle: two rear wheels on an axle, a basket between
        out.append(("wheel_F", "wheel", "wheel_F", "C", [W((0, yf, r), r)]))
        out.append(("wheel_B", "wheel", "wheel_B", "C", [W((-0.32, yb, r), r), W((0.32, yb, r), r), T([(-0.32, yb, r), (0.32, yb, r)], 0.014, "chrome")]))
        out.append(("basket", "equipment", "basket", "C", [("wire", (0, yb, r + 0.30), (0.26, 0.22, 0.15), "chrome")]))
    else:
        out.append(("wheel_F", "wheel", "wheel_F", "C", [W((0, yf, r), r)]))
        out.append(("wheel_B", "wheel", "wheel_B", "C", [W((0, yb, r), r)]))
    if basket:
        out.append(("basket_F", "equipment", "basket", "C", [("wire", (0, yf + basket[0], basket[1]), (0.18, 0.15, 0.12), "chrome")]))
    if rear_rack:
        out.append(("rack", "equipment", "rack", "C", [B((0, yb + 0.12, r * 2 + 0.06), (0.10, 0.20, 0.01), "black")]))
    if child:
        out.append(("stabilisers", "equipment", "stabilisers", "C", [W((-0.20, yb, r * 0.45), r * 0.45, 0.02), W((0.20, yb, r * 0.45), r * 0.45, 0.02),
                                                                     T([(-0.20, yb, r * 0.45), (0.20, yb, r * 0.45)], 0.008, "chrome")]))
    return out


def motorcycle(scooter=False):
    wb, r = (1.30, 0.26) if scooter else (1.45, 0.32)
    yf, yb = wb / 2, -wb / 2
    out = [("frame", "frame_shown", "frame", "C", [T([(0, yb + 0.25, r + 0.15), (0, 0.1, r + 0.2), (0, yf - 0.25, r + 0.55)], 0.03, "black"),
                                                    T([(0, yf - 0.25, r + 0.55), (0, yf, r)], 0.025, "chrome")])]
    out.append(("pack", "equipment", "pack", "C", [B((0, 0.05, r + 0.18), (0.14, 0.30, 0.16), "black")]))
    if scooter:
        out.append(("bodywork", "side_bay", "bodywork", "C", [B((0, yb + 0.30, r + 0.42), (0.17, 0.32, 0.18), "paint"), B((0, 0.15, r + 0.06), (0.16, 0.30, 0.04), "paint"),
                                                               B((0, yf - 0.18, r + 0.45), (0.17, 0.08, 0.42), "paint")]))
        seat_c = (0, yb + 0.30, r + 0.64)
    else:
        out.append(("tank", "side_bay", "tank", "C", [B((0, 0.25, r + 0.55), (0.14, 0.24, 0.10), "paint")]))
        out.append(("fairing", "end_cap", "nose", "C", [B((0, yf - 0.18, r + 0.70), (0.18, 0.06, 0.16), "paint")]))
        seat_c = (0, -0.18, r + 0.50)
    out.append(("seat", "seat", "seat", "C", [B(seat_c, (0.13, 0.28, 0.05), "seat")]))
    out.append(("bars", "equipment", "handlebar", "C", [T([(-0.36, yf - 0.20, r + 0.80), (0.36, yf - 0.20, r + 0.80)], 0.014, "chrome")]))
    out.append(("wheel_F", "wheel", "wheel_F", "C", [W((0, yf, r), r, 0.10)]))
    out.append(("wheel_B", "wheel", "wheel_B", "C", [W((0, yb, r), r, 0.13)]))
    out.append(("head_lamps", "lamp", "head_lamp", "C", [("lathe", [(0.0, 0.08), (0.03, 0.07), (0.035, 0.0001)], (0, yf - 0.10, r + 0.70), "lamp_head", "y")]))
    out.append(("tail_lamps", "lamp", "tail_lamp", "C", [B((0, yb - 0.08, r + 0.45), (0.06, 0.02, 0.025), "lamp_tail")]))
    return out


def chair(manual=True):
    out = [("frame", "frame_shown", "frame", "C", [])]
    fr = out[0][4]
    for sx in (1, -1):
        x = sx * 0.26
        fr += [T([(x, 0.25, 0.20), (x, -0.20, 0.50), (x, -0.25, 0.95)], 0.012, "chrome"), T([(x, 0.25, 0.20), (x, 0.30, 0.50)], 0.012, "chrome"),
               T([(x, -0.20, 0.50), (x, 0.25, 0.50)], 0.012, "chrome")]
    out.append(("seat", "seat", "seat", "C", [B((0, 0.02, 0.50), (0.22, 0.22, 0.02), "black"), B((0, -0.22, 0.75), (0.22, 0.02, 0.22), "black")]))
    out.append(("wheels", "wheel", "wheels", "C", [W((sx * 0.30, -0.10, 0.30), 0.30, 0.03) for sx in (1, -1)] +
                [("disc", (sx * 0.34, -0.10, 0.30), 0.27, 0.01, "chrome") for sx in (1, -1)] + [W((sx * 0.22, 0.28, 0.07), 0.07, 0.03) for sx in (1, -1)]))
    return out


def rollator():
    fr = []
    for sx in (1, -1):
        x = sx * 0.26
        fr += [T([(x, 0.25, 0.10), (x, 0.0, 0.90)], 0.013, "paint"), T([(x, -0.25, 0.10), (x, 0.0, 0.90)], 0.013, "paint"),
               T([(x, -0.05, 0.88), (x, -0.20, 0.92)], 0.016, "rubber")]
    return [("frame", "frame_shown", "frame", "C", fr), ("seat", "seat", "seat", "C", [B((0, 0.0, 0.55), (0.24, 0.16, 0.02), "black")]),
            ("basket", "equipment", "basket", "C", [("wire", (0, 0.0, 0.42), (0.20, 0.12, 0.08), "chrome")]),
            ("wheels", "wheel", "wheels", "C", [W((sx * 0.27, sy * 0.25, 0.10), 0.10, 0.03) for sx in (1, -1) for sy in (1, -1)])]


def stroller():
    fr = [T([(sx * 0.24, 0.30, 0.10), (sx * 0.24, -0.05, 0.55), (sx * 0.24, -0.35, 1.05)], 0.012, "chrome") for sx in (1, -1)]
    fr += [T([(sx * 0.24, -0.30, 0.12), (sx * 0.24, -0.05, 0.55)], 0.012, "chrome") for sx in (1, -1)]
    fr.append(T([(-0.24, -0.35, 1.05), (0.24, -0.35, 1.05)], 0.016, "rubber"))
    return [("frame", "frame_shown", "frame", "C", fr),
            ("bassinet", "seat", "seat", "C", [B((0, 0.0, 0.62), (0.22, 0.30, 0.10), "paint")]),
            ("hood", "roof_bay", "hood", "C", [("lathe", [(0.0, 0.0001), (0.05, 0.22), (0.30, 0.24), (0.31, 0.0001)], (0, -0.20, 0.72), "paint2", "y")]),
            ("wheels", "wheel", "wheels", "C", [W((sx * 0.26, 0.30, 0.10), 0.10, 0.03) for sx in (1, -1)] + [W((sx * 0.26, -0.30, 0.14), 0.14, 0.03) for sx in (1, -1)])]


def cart(kind):
    """Carts and trolleys."""
    if kind == "shopping_cart":
        return [("basket", "frame_shown", "basket", "C", [("wire", (0, 0.05, 0.75), (0.26, 0.42, 0.22), "chrome")]),
                ("frame", "frame_shown", "frame", "C", [T([(sx * 0.24, 0.45, 0.12), (sx * 0.24, -0.35, 0.12), (sx * 0.26, -0.45, 1.0)], 0.012, "chrome") for sx in (1, -1)] +
                 [T([(-0.27, -0.45, 1.0), (0.27, -0.45, 1.0)], 0.016, "paint")]),
                ("wheels", "wheel", "wheels", "C", [W((sx * 0.24, sy * 0.40, 0.06), 0.06, 0.03) for sx in (1, -1) for sy in (1, -1)])]
    if kind == "hand_truck":
        return [("frame", "frame_shown", "frame", "C", [T([(sx * 0.18, -0.05, 0.12), (sx * 0.18, -0.12, 1.25)], 0.014, "paint") for sx in (1, -1)] +
                 [T([(-0.18, -0.12, 1.25), (0.18, -0.12, 1.25)], 0.014, "paint"), B((0, 0.08, 0.04), (0.18, 0.12, 0.01), "chrome")]),
                ("wheels", "wheel", "wheels", "C", [W((sx * 0.22, -0.08, 0.12), 0.12, 0.05) for sx in (1, -1)])]
    if kind == "pallet_jack":
        return [("forks", "frame_shown", "forks", "C", [B((sx * 0.20, 0.35, 0.06), (0.08, 0.55, 0.03), "paint") for sx in (1, -1)]),
                ("pump", "equipment", "pump", "C", [B((0, -0.25, 0.20), (0.18, 0.10, 0.14), "paint"), T([(0, -0.25, 0.32), (0, -0.55, 1.15)], 0.016, "black"),
                                                     T([(-0.12, -0.55, 1.15), (0.12, -0.55, 1.15)], 0.014, "black")]),
                ("wheels", "wheel", "wheels", "C", [W((sx * 0.20, 0.82, 0.04), 0.04, 0.06) for sx in (1, -1)] + [W((0, -0.25, 0.09), 0.09, 0.10)])]
    if kind == "wheelbarrow":
        return [("tray", "frame_shown", "tray", "C", [("wire", (0, 0.05, 0.50), (0.30, 0.40, 0.14), "paint")]),
                ("frame", "frame_shown", "frame", "C", [T([(sx * 0.22, 0.55, 0.20), (sx * 0.28, -0.70, 0.55)], 0.016, "black") for sx in (1, -1)] +
                 [T([(sx * 0.22, -0.25, 0.35), (sx * 0.22, -0.30, 0.0)], 0.012, "black") for sx in (1, -1)]),
                ("wheels", "wheel", "wheels", "C", [W((0, 0.60, 0.20), 0.20, 0.08)])]
    if kind == "luggage_cart":
        return [("frame", "frame_shown", "frame", "C", [B((0, 0.0, 0.25), (0.32, 0.65, 0.02), "chrome")] +
                 [T([(sx * 0.30, sy * 0.62, 0.25), (sx * 0.30, sy * 0.62, 1.80)], 0.016, "chrome") for sx in (1, -1) for sy in (1, -1)] +
                 [T([(-0.30, sy * 0.62, 1.80), (0.30, sy * 0.62, 1.80)], 0.016, "chrome") for sy in (1, -1)] +
                 [T([(sx * 0.30, 0.62, 1.80), (sx * 0.30, -0.62, 1.80)], 0.016, "chrome") for sx in (1, -1)]),
                ("carpet", "trim", "carpet", "C", [B((0, 0.0, 0.28), (0.30, 0.62, 0.01), "carpet")]),
                ("wheels", "wheel", "wheels", "C", [W((sx * 0.28, sy * 0.55, 0.10), 0.10, 0.04) for sx in (1, -1) for sy in (1, -1)])]
    if kind == "housekeeping_cart":
        return [("body", "side_bay", "body", "C", [B((0, 0.0, 0.62), (0.26, 0.60, 0.50), "paint"), B((0, 0.0, 1.13), (0.27, 0.61, 0.01), "black")]),
                ("bag", "equipment", "bag", "C", [B((0, -0.70, 0.70), (0.22, 0.10, 0.45), "livery1")]),
                ("wheels", "wheel", "wheels", "C", [W((sx * 0.24, sy * 0.52, 0.07), 0.07, 0.04) for sx in (1, -1) for sy in (1, -1)])]
    if kind == "hospital_gurney":
        return [("frame", "frame_shown", "frame", "C", [T([(sx * 0.30, sy * 0.85, 0.12), (sx * 0.30, -sy * 0.40, 0.80)], 0.016, "chrome") for sx in (1, -1) for sy in (1, -1)]),
                ("mattress", "seat", "mattress", "C", [B((0, 0.0, 0.86), (0.32, 0.98, 0.06), "livery1")]),
                ("rails", "equipment", "rails", "C", [T([(sx * 0.34, 0.6, 1.0), (sx * 0.34, -0.6, 1.0)], 0.012, "chrome") for sx in (1, -1)]),
                ("wheels", "wheel", "wheels", "C", [W((sx * 0.30, sy * 0.85, 0.07), 0.07, 0.04) for sx in (1, -1) for sy in (1, -1)])]
    if kind == "food_cart":
        return [("body", "side_bay", "body", "C", [B((0, 0.0, 0.70), (0.42, 0.85, 0.45), "paint"), B((0, 0.0, 1.16), (0.43, 0.86, 0.01), "chrome")]),
                ("umbrella", "roof_bay", "umbrella", "C", [T([(0, 0.0, 1.16), (0, 0.0, 2.05)], 0.02, "chrome"),
                                                          ("lathe", [(0.0, 1.00), (0.25, 0.0001)], (0, 0.0, 1.90), "livery2", "z")]),
                ("sign", "equipment", "sign", "C", [B((0, 0.86, 0.80), (0.38, 0.01, 0.20), "sign")]),
                ("wheels", "wheel", "wheels", "C", [W((sx * 0.45, -0.30, 0.25), 0.25, 0.05) for sx in (1, -1)] + [W((0, 0.80, 0.08), 0.08, 0.04)])]
    if kind == "child_wagon":
        return [("tray", "side_bay", "tray", "C", [("wire", (0, 0.0, 0.32), (0.25, 0.48, 0.12), "paint")]),
                ("handle", "equipment", "handle", "C", [T([(0, 0.48, 0.25), (0, 1.05, 0.65)], 0.012, "black"), T([(-0.08, 1.05, 0.65), (0.08, 1.05, 0.65)], 0.015, "black")]),
                ("wheels", "wheel", "wheels", "C", [W((sx * 0.22, sy * 0.38, 0.10), 0.10, 0.04) for sx in (1, -1) for sy in (1, -1)])]
    raise KeyError(kind)


def kick_scooter():
    return [("deck", "frame_shown", "deck", "C", [B((0, -0.05, 0.08), (0.07, 0.32, 0.015), "black"), T([(0, 0.30, 0.08), (0, 0.38, 0.95)], 0.016, "chrome")]),
            ("bars", "equipment", "handlebar", "C", [T([(-0.20, 0.38, 0.95), (0.20, 0.38, 0.95)], 0.014, "black")]),
            ("wheels", "wheel", "wheels", "C", [W((0, 0.40, 0.08), 0.08, 0.03), W((0, -0.40, 0.08), 0.08, 0.03)])]


def skateboard():
    return [("deck", "frame_shown", "deck", "C", [B((0, 0.0, 0.09), (0.11, 0.40, 0.006), "wood")]),
            ("trucks", "equipment", "trucks", "C", [B((0, sy * 0.27, 0.06), (0.09, 0.02, 0.015), "chrome") for sy in (1, -1)]),
            ("wheels", "wheel", "wheels", "C", [W((sx * 0.09, sy * 0.27, 0.03), 0.03, 0.03) for sx in (1, -1) for sy in (1, -1)])]


def surrey():
    """A surrey: a four-wheel pedal car, two benches side by side with pedals, a fringed canopy."""
    out = [("frame", "frame_shown", "frame", "C", [T([(sx * 0.55, 1.10, 0.30), (sx * 0.55, -1.10, 0.30)], 0.022, "paint") for sx in (1, -1)] +
            [T([(-0.55, sy, 0.30), (0.55, sy, 0.30)], 0.02, "paint") for sy in (1.0, 0.0, -1.0)]),
           ("benches", "seat", "benches", "C", [B((0, sy, 0.62), (0.55, 0.20, 0.04), "seat") for sy in (0.35, -0.55)] +
            [B((0, sy - 0.20, 0.85), (0.55, 0.03, 0.22), "seat") for sy in (0.35, -0.55)]),
           ("canopy", "roof_bay", "canopy", "C", [B((0, 0.0, 1.95), (0.70, 1.15, 0.02), "livery2")] +
            [T([(sx * 0.62, sy * 1.0, 0.30), (sx * 0.62, sy * 1.0, 1.93)], 0.015, "chrome") for sx in (1, -1) for sy in (1, -1)]),
           ("bars", "equipment", "handlebar", "C", [T([(-0.25, 0.75, 0.95), (0.25, 0.75, 0.95)], 0.014, "chrome"), T([(-0.2, 0.75, 0.95), (-0.2, 1.0, 0.30)], 0.014, "chrome")]),
           ("wheels", "wheel", "wheels", "C", [W((sx * 0.62, sy * 1.0, 0.28), 0.28, 0.05) for sx in (1, -1) for sy in (1, -1)])]
    return out


def cargo_bike():
    out = bicycle_like(1.75, 0.33, rider=0.85, bar=1.05)
    out.append(("box", "side_bay", "cargo_box", "C", [("wire", (0, 0.55, 0.42), (0.30, 0.32, 0.18), "wood")]))
    return out


RECIPES = {
    "motorcycle": lambda: motorcycle(False), "scooter_moped": lambda: motorcycle(True),
    "child_bicycle": lambda: bicycle_like(0.75, 0.20, rider=0.55, bar=0.70, child=True),
    "cargo_bike": cargo_bike, "adult_tricycle": lambda: bicycle_like(1.10, 0.30, rider=0.80, bar=1.02, tri=True, basket=(0.12, 0.85)),
    "kick_scooter": kick_scooter, "skateboard": skateboard, "surrey_bike": surrey,
    "manual_wheelchair": lambda: chair(True), "rollator": rollator, "baby_stroller": stroller,
    "child_wagon": lambda: cart("child_wagon"), "shopping_cart": lambda: cart("shopping_cart"), "hand_truck": lambda: cart("hand_truck"),
    "pallet_jack": lambda: cart("pallet_jack"), "wheelbarrow": lambda: cart("wheelbarrow"), "luggage_cart": lambda: cart("luggage_cart"),
    "housekeeping_cart": lambda: cart("housekeeping_cart"), "hospital_gurney": lambda: cart("hospital_gurney"), "food_cart": lambda: cart("food_cart"),
}
COLOURS = {"motorcycle": (30, 31, 34), "scooter_moped": (90, 160, 150), "child_bicycle": (40, 110, 200), "cargo_bike": (60, 120, 60),
           "adult_tricycle": (150, 30, 40), "kick_scooter": (40, 110, 200), "skateboard": (128, 74, 40), "surrey_bike": (190, 40, 30),
           "manual_wheelchair": (40, 42, 46), "rollator": (40, 92, 150), "baby_stroller": (60, 70, 90), "child_wagon": (190, 40, 30),
           "shopping_cart": (190, 40, 30), "hand_truck": (236, 140, 24), "pallet_jack": (236, 140, 24), "wheelbarrow": (60, 120, 60),
           "luggage_cart": (210, 212, 216), "housekeeping_cart": (236, 234, 228), "hospital_gurney": (210, 212, 216), "food_cart": (40, 140, 130)}


# ---------------------------------------------------------------- the air and the space (2026-10-02)
def aerostat(L, R, gondola, colour_m="paint", rescue=False):
    """An aerostat: the envelope (a lathe), its fins, the gondola under it (walls, windows, a roof), ducted fans."""
    gl, gw, gh = gondola
    zc = gh + 1.6 + R
    prof = [(-L / 2, 0.0001), (-L / 2 + R * 0.25, R * 0.55), (-L / 2 + R * 0.8, R * 0.92), (0.0, R), (L / 2 - R * 0.9, R * 0.9), (L / 2 - R * 0.3, R * 0.5), (L / 2, 0.0001)]
    out = [("envelope", "roof_bay", "envelope", "C", [("lathe", prof, (0, 0, zc), colour_m, "y")]),
           ("fins", "equipment", "fins", "C", [B((0, -L / 2 + R * 0.6, zc + R * 0.8), (0.04, R * 0.5, R * 0.5), "paint2"),
                                                B((0, -L / 2 + R * 0.6, zc - R * 0.8), (0.04, R * 0.5, R * 0.5), "paint2"),
                                                B((R * 0.8, -L / 2 + R * 0.6, zc), (R * 0.5, R * 0.5, 0.04), "paint2"),
                                                B((-R * 0.8, -L / 2 + R * 0.6, zc), (R * 0.5, R * 0.5, 0.04), "paint2")]),
           ("rigging", "frame_shown", "rigging", "C", [T([(sx * gw * 0.9, sy * gl * 0.45, gh + 0.4), (sx * R * 0.5, sy * L * 0.25, zc - R * 0.85)], 0.012, "black")
                                                      for sx in (1, -1) for sy in (1, -1)]),
           ("gondola", "cab", "gondola", "C", [B((0, 0, gh * 0.35 + 0.4), (gw, gl / 2, gh * 0.35), "paint2"), B((0, 0, gh + 0.42), (gw, gl / 2, 0.03), "paint2"),
                                               B((0, gl / 2 - 0.1, gh * 0.85 + 0.4), (gw - 0.05, 0.10, gh * 0.15), "paint2")]),
           ("gondola_glass", "glazing", "gondola", "C", [B((0, 0, gh * 0.82 + 0.4), (gw + 0.005, gl / 2 + 0.005, gh * 0.12), "glass_dark")]),
           ("fans", "equipment", "fans", "C", [("lathe", [(-0.25, 0.42), (0.25, 0.42), (0.25, 0.36), (-0.25, 0.36)], (sx * (gw + 0.7), -gl * 0.2, gh * 0.6 + 0.4), "black", "y")
                                               for sx in (1, -1)] + [T([(sx * gw, -gl * 0.2, gh * 0.6 + 0.4), (sx * (gw + 0.6), -gl * 0.2, gh * 0.6 + 0.4)], 0.04, "black")
                                                                     for sx in (1, -1)]),
           ("skids", "frame_shown", "skids", "C", [T([(sx * gw * 0.8, gl / 2, 0.05), (sx * gw * 0.8, -gl / 2, 0.05)], 0.04, "black") for sx in (1, -1)] +
            [T([(sx * gw * 0.8, sy * gl * 0.35, 0.05), (sx * gw * 0.8, sy * gl * 0.35, 0.40)], 0.03, "black") for sx in (1, -1) for sy in (1, -1)])]
    if rescue:
        out.append(("winch", "equipment", "winch", "C", [B((gw + 0.15, 0.3, gh + 0.2), (0.12, 0.2, 0.12), "livery2"), T([(gw + 0.15, 0.3, gh + 0.1), (gw + 0.6, 0.3, gh + 0.4)], 0.02, "chrome")]))
        out.append(("beacon", "lamp", "beacon", "C", [B((0, 0, gh + 0.48), (0.12, 0.12, 0.04), "lamp_red")]))
    return out


def shuttle():
    """A passenger shuttle: a lifting body with a cockpit, a cabin of portholes, fins and engine bells."""
    out = [("hull", "side_bay", "hull", "C", [("lathe", [(-15.0, 3.2), (-12.0, 3.6), (0.0, 3.8), (8.0, 3.2), (13.0, 1.8), (15.0, 0.0001)], (0, 0, 4.0), "paint", "y")]),
           ("wings", "equipment", "wings", "C", [("box", (sx * 5.5, -6.0, 3.0), (3.5, 5.0, 0.20), "paint2") for sx in (1, -1)]),
           ("fin", "equipment", "fin", "C", [B((0, -12.0, 8.5), (0.15, 2.5, 2.5), "paint2")]),
           ("cockpit", "glazing", "cockpit", "C", [B((0, 11.5, 5.4), (1.2, 1.2, 0.5), "glass_dark")]),
           ("portholes", "glazing", "portholes", "C", [("disc", (sx * 3.72, y, 4.6), 0.30, 0.04, "glass_dark") for sx in (1, -1) for y in range(-9, 8, 2)]),
           ("engines", "equipment", "engines", "C", [("lathe", [(0.0, 0.6), (1.4, 1.1), (1.5, 1.1)], (sx * 1.6, -15.0, 4.0 + sz * 1.2), "black", "y")
                                                     for sx in (1, -1) for sz in (1, -1)]),
           ("gear", "frame_shown", "gear", "C", [T([(sx * 2.5, y, 0.0), (sx * 2.5, y, 1.5)], 0.15, "chrome") for sx in (1, -1) for y in (6.0, -8.0)])]
    return out


def freighter():
    out = [("truss", "frame_shown", "truss", "C", [T([(sx * 3.0, -28.0, 10 + sz * 3.0), (sx * 3.0, 28.0, 10 + sz * 3.0)], 0.35, "chrome") for sx in (1, -1) for sz in (1, -1)] +
            [T([(-3.0, y, 7.0), (3.0, y, 13.0)], 0.2, "chrome") for y in range(-26, 27, 4)]),
           ("pods", "cargo_wall", "pods", "C", [B((sx * 6.0, y, 10.0), (2.6, 3.6, 2.6), "paint" if (y // 8) % 2 else "paint2") for sx in (1, -1) for y in range(-24, 25, 8)]),
           ("bridge", "cab", "bridge", "C", [B((0, 29.5, 10.0), (4.0, 2.5, 3.5), "paint"), B((0, 32.0, 11.0), (3.0, 0.1, 1.0), "glass_dark")]),
           ("drive", "equipment", "drive", "C", [("lathe", [(0.0, 4.0), (6.0, 6.5), (7.0, 6.5)], (0, -30.0, 10.0), "black", "y")]),
           ("radiators", "equipment", "radiators", "C", [B((sx * 10.0, -10.0, 10.0), (3.0, 8.0, 0.08), "paint2") for sx in (1, -1)])]
    return out


def eva_sled():
    """The EVA sled (reference/grok/eva_sled): a rounded hull platform, the thruster tower at its back (four bells), a
    seat and a control stand, a robot arm on the deck, rails, lamps on posts, sprung landing pads."""
    def bell(c, r=0.16):
        return ("lathe", [(0.0, r * 0.55), (-0.12, r * 0.5), (-0.28, r * 0.8), (-0.42, r)], c, "paint", "y")
    hull = [B((0, 0.1, 0.55), (0.80, 1.45, 0.14), "paint2"), B((0, 1.52, 0.52), (0.70, 0.10, 0.11), "paint2"),
            B((0, 0.1, 0.70), (0.72, 1.35, 0.012), "black")]
    hull += [B((sx * 0.805, 0.1, 0.56), (0.008, 1.40, 0.03), "paint") for sx in (1, -1)]
    tower = [B((0, -1.20, 1.30), (0.78, 0.28, 0.75), "paint2"), B((0, -0.915, 1.30), (0.70, 0.01, 0.64), "chrome"),
             B((0, -0.90, 1.05), (0.30, 0.01, 0.22), "paint"), B((0, -0.89, 1.05), (0.24, 0.006, 0.16), "black")]
    tower += [B((sx * 0.79, -1.20, 1.30), (0.01, 0.20, 0.70), "paint") for sx in (1, -1)]
    tower += [B((0, -1.20, 2.06), (0.70, 0.22, 0.012), "paint")]
    bells = [bell((x, -1.49, z)) for x in (-0.38, 0.38) for z in (0.95, 1.68)]
    bells += [("lathe", [(0.0, 0.12), (-0.08, 0.12)], (x, -1.49, z), "chrome", "y") for x in (-0.38, 0.38) for z in (0.95, 1.68)]
    seat = [("seat", (0, -0.55, 0.88), (0.27, 0.24), "seat"), B((0, -0.78, 1.20), (0.26, 0.05, 0.32), "seat"),
            B((0, -0.55, 0.78), (0.20, 0.20, 0.08), "black")]
    stand = [B((0, 0.25, 0.95), (0.24, 0.16, 0.24), "paint2"), B((0, 0.13, 1.12), (0.20, 0.06, 0.06), "black")]
    stand += [("disc", (x, 0.08, 1.14), 0.025, 0.02, "lamp_amber") for x in (-0.12, -0.04, 0.04, 0.12)]
    arm = [("lathe", [(0.0, 0.26), (0.06, 0.26), (0.10, 0.18), (0.16, 0.18)], (0.2, 0.95, 0.72), "paint2", "z"),
           T([(0.2, 0.95, 0.9), (0.15, 0.75, 1.55)], 0.085, "paint2"), T([(0.15, 0.75, 1.55), (0.2, 1.45, 1.95)], 0.07, "paint2"),
           T([(0.2, 1.45, 1.95), (0.2, 1.85, 1.9)], 0.05, "paint2"),
           ("disc", (0.15, 0.75, 1.55), 0.11, 0.18, "paint"), ("disc", (0.2, 1.45, 1.95), 0.09, 0.15, "paint"),
           T([(0.2, 1.85, 1.92), (0.2, 2.02, 2.0)], 0.018, "chrome"), T([(0.2, 1.85, 1.88), (0.2, 2.02, 1.80)], 0.018, "chrome"),
           T([(0.22, 1.05, 1.2), (0.22, 1.08, 1.45)], 0.03, "paint")]
    small = [T([(-0.55, -0.85, 1.4), (-0.45, -0.55, 1.75), (-0.40, -0.25, 1.70)], 0.035, "paint2"), ("disc", (-0.45, -0.55, 1.75), 0.06, 0.08, "paint")]
    rails = [T([(-0.75, -0.95, 0.72), (-0.75, -0.9, 1.1), (-0.75, 0.5, 1.1), (-0.75, 0.55, 0.72)], 0.025, "chrome"),
             T([(0.78, 1.5, 0.62), (0.85, 1.0, 0.62), (0.85, -0.9, 0.62)], 0.022, "chrome")]
    lamps = [T([(-0.6, -1.2, 2.06), (-0.6, -1.2, 2.25)], 0.03, "paint"), ("lathe", [(0.0, 0.11), (0.04, 0.11), (0.05, 0.0001)], (-0.6, -1.12, 2.32), "lamp_head", "y"),
             T([(0.65, 1.45, 0.69), (0.65, 1.45, 0.88)], 0.03, "paint"), ("lathe", [(0.0, 0.09), (0.04, 0.09), (0.05, 0.0001)], (0.65, 1.53, 0.95), "lamp_head", "y")]
    pads = []
    for x in (-0.55, 0.55):
        for y in (-1.05, 0.0, 1.05):
            pads += [T([(x, y, 0.41), (x, y, 0.22)], 0.035, "chrome"), ("lathe", [(0.0, 0.07), (0.10, 0.09), (0.18, 0.13), (0.20, 0.0001)], (x, y, 0.24), "paint", "z")]
    return [("hull", "cargo_floor", "hull", "C", hull), ("tower", "cab", "tower", "C", tower), ("bells", "equipment", "thrusters", "C", bells),
            ("seat", "seat", "seat", "C", seat), ("stand", "dash", "stand", "C", stand), ("arm", "equipment", "arm", "C", arm),
            ("arm_small", "equipment", "arm_small", "C", small), ("rails", "frame_shown", "rails", "C", rails), ("lamps", "lamp", "lamps", "C", lamps),
            ("pads", "wheel", "pads", "C", pads)]


def cargo_mule():
    return [("body", "cargo_wall", "body", "C", [B((0, 0, 1.0), (0.95, 1.4, 0.9), "paint")]),
            ("frame", "frame_shown", "frame", "C", [T([(sx * 1.0, sy * 1.45, 0.1), (sx * 1.0, sy * 1.45, 1.95)], 0.05, "black") for sx in (1, -1) for sy in (1, -1)]),
            ("thrusters", "equipment", "thrusters", "C", [("lathe", [(0.0, 0.18), (0.25, 0.25)], (sx * 1.05, sy * 1.5, 1.0), "black", "x") for sx in (1, -1) for sy in (1, -1)]),
            ("lamps", "lamp", "lamps", "C", [B((sx * 0.6, 1.42, 1.6), (0.12, 0.02, 0.06), "lamp_head") for sx in (1, -1)]),
            ("grapples", "equipment", "grapples", "C", [T([(sx * 0.5, 1.45, 0.5), (sx * 0.7, 2.0, 0.3)], 0.04, "chrome") for sx in (1, -1)])]


def elevator_car():
    out = [("cab", "side_bay", "cab", "C", [B((0, 0, 0.05), (3.0, 3.0, 0.05), "paint"), B((0, 0, 2.95), (3.0, 3.0, 0.05), "paint")] +
            [B((sx * 2.97, 0, 1.5), (0.03, 3.0, 1.45), "paint") for sx in (1, -1)] + [B((0, -2.97, 1.5), (3.0, 0.03, 1.45), "paint")]),
           ("windows", "glazing", "windows", "C", [B((sx * 2.99, 0, 1.7), (0.01, 2.6, 0.8), "glass_dark") for sx in (1, -1)]),
           ("doors", "door_leaf", "doors", "C", [B((sx * 0.75, 2.97, 1.45), (0.74, 0.03, 1.4), "chrome") for sx in (1, -1)]),
           ("rails", "equipment", "guide_rails", "C", [B((sx * 3.1, 0, 1.5), (0.06, 0.2, 1.6), "black") for sx in (1, -1)]),
           ("benches", "seat", "benches", "C", [B((sx * 2.6, 0, 0.5), (0.3, 2.4, 0.04), "seat") for sx in (1, -1)]),
           ("sign", "dash", "dest_sign", "C", [B((0, 2.9, 2.75), (1.0, 0.04, 0.12), "lcd")])]
    return out


def travel_lift():
    """The boatyard's travel lift (reference/grok/travel_lift): a box-section gantry on four legs, its top frame with the
    yard's name boards, pulleys and blocks, the slings hanging in loops between, the control and power boxes, the
    wheels on their forks (the front pair steers)."""
    hx, hy, top = 3.4, 4.6, 8.6
    beams = []
    for sx in (1, -1):
        for sy in (1, -1):
            beams.append(B((sx * hx, sy * hy, (0.95 + top) / 2), (0.22, 0.22, (top - 0.95) / 2), "paint"))
        beams.append(B((sx * hx, 0, top), (0.26, hy + 0.26, 0.30), "paint"))
        beams.append(B((sx * (hx + 0.265), 0, top), (0.01, hy * 0.6, 0.18), "paint2"))
        beams.append(B((sx * (hx + 0.27), 0, top + 0.20), (0.008, hy + 0.2, 0.025), "paint2"))
        beams.append(B((sx * hx, 0, 1.4), (0.18, hy, 0.18), "paint"))
    for sy in (1, -1):
        beams.append(B((0, sy * hy, top), (hx + 0.26, 0.26, 0.30), "paint"))
        beams.append(B((0, sy * (hy + 0.265), top), (hx * 0.6, 0.01, 0.18), "paint2"))
    pulleys, slings = [], []
    for sx in (1, -1):
        for y in (2.0, 0.7, -0.7, -2.0):
            pulleys += [("disc", (sx * (hx - 0.05), y, top - 0.55), 0.20, 0.08, "chrome"), T([(sx * (hx - 0.05), y, top - 0.30), (sx * (hx - 0.05), y, top - 0.35)], 0.03, "black")]
            slings.append(T([(sx * (hx - 0.05), y, top - 0.75), (sx * (hx - 0.05), y, 2.6)], 0.012, "chrome"))
            slings.append(T([(sx * (hx - 0.05), y, 2.6), (sx * (hx - 0.5), y, 1.4), (sx * 1.6, y, 0.95), (0.0, y, 0.85)], 0.05, "paint"))
            slings.append(("disc", (sx * (hx - 0.05), y, 2.55), 0.07, 0.10, "chrome"))
    for y in (2.0, 0.7, -0.7, -2.0):
        slings.append(T([(-1.6, y, 0.95), (0.0, y, 0.85), (1.6, y, 0.95)], 0.05, "paint"))
    boxes = [B((hx + 0.45, hy - 0.6, 2.3), (0.22, 0.40, 0.55), "paint2"), B((hx + 0.68, hy - 0.6, 2.4), (0.01, 0.12, 0.10), "black"),
             B((-hx - 0.40, hy - 0.2, 1.6), (0.18, 0.28, 0.30), "chrome"), B((-hx - 0.59, hy - 0.2, 1.6), (0.01, 0.08, 0.10), "lamp_amber"),
             T([(hx + 0.45, hy - 0.6, 1.75), (hx + 0.2, hy - 0.6, 1.2), (hx, hy - 0.3, 1.0)], 0.02, "black")]
    lamps = [("lathe", [(0.0, 0.08), (0.05, 0.06), (0.06, 0.0001)], (x, y, top - 0.32), "lamp_head", "z") for x in (-2.0, 0.0, 2.0) for y in (hy, -hy)]
    wheels = []
    for sx in (1, -1):
        for sy in (1, -1):
            x, y = sx * hx, sy * hy
            wheels += [B((x, y, 0.98), (0.30, 0.30, 0.05), "black"), T([(x, y + 0.15, 0.95), (x, y + 0.15, 0.55)], 0.06, "paint"),
                       T([(x, y - 0.15, 0.95), (x, y - 0.15, 0.55)], 0.06, "paint")]
            wheels.append(W((x, y, 0.48), 0.48, 0.30))
    return [("gantry", "frame_shown", "gantry", "C", beams), ("pulleys", "equipment", "pulleys", "C", pulleys),
            ("slings", "equipment", "slings", "C", slings), ("controls", "equipment", "controls", "C", boxes),
            ("lamps", "lamp", "lamps", "C", lamps), ("wheels", "wheel", "wheels", "C", wheels)]


RECIPES.update({"eva_sled": eva_sled, "travel_lift": travel_lift})
COLOURS.update({"passenger_shuttle": (236, 234, 228), "supply_freighter": (150, 152, 156),
                "eva_sled": (226, 110, 30), "cargo_mule": (236, 140, 24), "spoke_elevator_car": (210, 212, 216), "travel_lift": (40, 92, 150)})
