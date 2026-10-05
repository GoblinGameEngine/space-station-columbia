"""
specs.py -- the fleet's class standards (kit/loft.py specs), their makers' base styles, and the variant types
built on each (research/vehicles/FLEET_BODIES.md; the package numbers in research/vehicles/FMVSS.md).

PACKAGE RULES (all passenger classes): the floor is the board's deck + 0.05 = 0.55 m; the front H-point 0.30
above the heel (0.85 m); the belt (the side glass's foot) H-point + 0.42 -- high, as FMVSS 214's side-impact
structure and FMVSS 226's ejection mitigation have pushed every modern car's (the wagon, a 1970s design, has it
at H-point + 0.20); headroom H-point to headliner >= 1.13 m for our tallest people (2.08 m); headlamp centres
0.56-1.37 m (FMVSS 108), tail lamps 0.38-1.83 m, bumpers in the Part 581 zone (0.41-0.51 m).
Coordinates: Blender's (y forward, z up), y = 0 midway between the board's outer axles.
"""

H_FRONT = 0.85                      # the front H-point's height (deck 0.50 + floor 0.05 + H30 0.30)
BELT_OVER_H = 0.42                  # the belt above the H-point (FMVSS 214 / 226: a high belt)


def belt_for(h=H_FRONT):
    return round(h + BELT_OVER_H, 3)


# ---------------------------------------------------------------- the palettes
# name: (sRGB, roughness, metallic, emission sRGB or None, emission strength, alpha)
BASE_PALETTE = {
    "paint": ((60, 104, 96), 0.3, 0.15, None, 0, 1), "paint2": ((232, 224, 204), 0.32, 0.05, None, 0, 1),
    "black": ((30, 31, 34), 0.5, 0.1, None, 0, 1), "chrome": ((210, 212, 216), 0.1, 1.0, None, 0, 1),
    "rubber": ((24, 24, 26), 0.85, 0.0, None, 0, 1), "glass": ((170, 196, 204), 0.05, 0.0, None, 0, 0.25),
    "glass_dark": ((40, 46, 52), 0.08, 0.4, None, 0, 1), "lining": ((200, 190, 170), 0.7, 0.0, None, 0, 1),
    "headliner": ((228, 222, 206), 0.8, 0.0, None, 0, 1), "carpet": ((70, 62, 56), 0.95, 0.0, None, 0, 1),
    "seat": ((120, 70, 44), 0.85, 0.0, None, 0, 1), "dash": ((52, 46, 42), 0.6, 0.0, None, 0, 1),
    "gauge": ((236, 228, 204), 0.4, 0.0, (255, 214, 150), 0.3, 1), "tub": ((58, 58, 60), 0.8, 0.0, None, 0, 1),
    "wood": ((128, 74, 40), 0.45, 0.0, None, 0, 1), "sign": ((250, 240, 200), 0.4, 0.0, (255, 240, 190), 1.0, 1),
    "livery1": ((240, 240, 236), 0.35, 0.05, None, 0, 1), "livery2": ((200, 40, 36), 0.35, 0.05, None, 0, 1),
    "lamp_head": ((255, 250, 236), 0.3, 0.0, (255, 248, 230), 3.0, 1), "lamp_drl": ((255, 250, 240), 0.3, 0.0, (255, 250, 240), 1.2, 1),
    "lamp_tail": ((190, 18, 14), 0.4, 0.0, (255, 30, 20), 1.6, 1), "lamp_brake": ((190, 18, 14), 0.4, 0.0, (255, 30, 20), 0.0, 1),
    "lamp_amber": ((236, 140, 24), 0.4, 0.0, (255, 150, 30), 0.0, 1), "lamp_reverse": ((236, 236, 236), 0.4, 0.0, (255, 255, 255), 0.0, 1),
    "lcd": ((150, 168, 118), 0.5, 0.0, (120, 170, 90), 0.35, 1),        # (the Steward's monochrome dot-matrix: black on green)
    "lamp_red": ((200, 20, 20), 0.3, 0.0, (255, 30, 30), 0.0, 1), "lamp_blue": ((20, 60, 220), 0.3, 0.0, (40, 90, 255), 0.0, 1), "lamp_green": ((20, 170, 60), 0.3, 0.0, (40, 255, 90), 0.0, 1),
}


def palette(**over):
    p = dict(BASE_PALETTE)
    for k, v in over.items():
        p[k] = v if isinstance(v, tuple) and len(v) == 6 else (v, BASE_PALETTE[k][1], BASE_PALETTE[k][2], None, 0, 1)
    return p


# ---------------------------------------------------------------- the classes
SEDAN = {
    "id": "SD180", "cls": "sedan", "board": "carrow_k28",
    "about": "four-door, three-box saloons on the Carrow Keel K-28 (2.8 m): 1.84 m wide, 4.76 m long, 2.04 m tall",
    "nose": 2.36, "tail": -2.40, "half_w": 0.92, "skirt": 0.30, "sill": 0.58, "floor": 0.55,
    "belt": belt_for(), "head": 1.90, "cant": 1.98, "crown": 2.04, "headliner": 1.99,
    "front": {"kind": "hood", "toe": 1.12, "header": 0.34, "screen_base": belt_for() + 0.02, "lid": (2.20, 1.20), "hood_drop": 0.30},
    "rear": {"kind": "trunk", "tail_in": -2.30, "c_top": -0.78, "c_foot": -1.60, "deck_z": belt_for() - 0.02, "lid": (-1.64, -2.30),
             "deck_drop": 0.06},
    "doors": [{"id": "F", "y0": 0.92, "y1": 0.0}, {"id": "B", "y0": -0.10, "y1": -0.92}],
    "seats": [{"y": 0.18, "z": 0.85, "xs": [-0.38, 0.38], "w": 0.50}, {"y": -0.66, "z": 0.87, "xs": [-0.40, 0.0, 0.40], "w": 0.40, "bench": True}],
    "head_lamp_z": 0.78, "tail_lamp_z": 1.02, "bumper_z": 0.46,
}


def hatch(hw, z0, z1, ghw, gz0, gz1):
    return {"half_w": hw, "z": (z0, z1), "corner": 0.10, "glass": {"half_w": ghw, "z": (gz0, gz1), "corner": 0.07}}


H_SUV = 0.89                        # SUVs sit higher above the same floor (H30 0.34)
CROSSOVER = {
    "id": "CU185", "cls": "crossover_suv", "board": "carrow_k28",
    "about": "five-door crossovers on the Carrow Keel K-28: 1.86 m wide, 4.64 m long, 2.12 m tall",
    "nose": 2.30, "tail": -2.34, "half_w": 0.93, "skirt": 0.32, "sill": 0.58, "floor": 0.55,
    "belt": belt_for(H_SUV), "head": 1.98, "cant": 2.06, "crown": 2.12, "headliner": 2.07,
    "front": {"kind": "hood", "toe": 1.12, "header": 0.30, "screen_base": belt_for(H_SUV) + 0.02, "lid": (2.14, 1.20), "hood_drop": 0.24},
    "rear": {"kind": "hatch", "tail_in": -2.26, "hatch": hatch(0.70, 0.72, 1.97, 0.62, 1.40, 1.92)},
    "doors": [{"id": "F", "y0": 0.92, "y1": 0.0}, {"id": "B", "y0": -0.10, "y1": -0.92}],
    "windows": [{"id": "Q", "y0": -1.00, "y1": -2.04}],
    "seats": [{"y": 0.18, "z": H_SUV, "xs": [-0.38, 0.38], "w": 0.50}, {"y": -0.66, "z": H_SUV + 0.02, "xs": [-0.40, 0.0, 0.40], "w": 0.40, "bench": True}],
    "head_lamp_z": 0.86, "tail_lamp_z": 1.22, "bumper_z": 0.48,
}

FULLSIZE = {
    "id": "FS200", "cls": "full_size_suv", "board": "harrow_h31",
    "about": "three-row five-door SUVs on the Harrow Ladder H-31 (3.1 m): 1.96 m wide, 5.20 m long, 2.14 m tall",
    "nose": 2.58, "tail": -2.62, "half_w": 0.98, "skirt": 0.33, "sill": 0.58, "floor": 0.55,
    "belt": belt_for(H_SUV), "head": 2.00, "cant": 2.08, "crown": 2.14, "headliner": 2.09,
    "front": {"kind": "hood", "toe": 1.24, "header": 0.42, "screen_base": belt_for(H_SUV) + 0.02, "lid": (2.42, 1.30), "hood_drop": 0.16},
    "rear": {"kind": "hatch", "tail_in": -2.54, "hatch": hatch(0.76, 0.72, 1.99, 0.66, 1.40, 1.94)},
    "doors": [{"id": "F", "y0": 1.06, "y1": 0.12}, {"id": "B", "y0": 0.02, "y1": -0.98}],
    "windows": [{"id": "Q", "y0": -1.06, "y1": -2.30}],
    "seats": [{"y": 0.36, "z": H_SUV, "xs": [-0.40, 0.40], "w": 0.52}, {"y": -0.52, "z": H_SUV + 0.02, "xs": [-0.42, 0.0, 0.42], "w": 0.42, "bench": True},
              {"y": -1.42, "z": H_SUV + 0.04, "xs": [-0.36, 0.36], "w": 0.46, "bench": True}],
    "head_lamp_z": 0.90, "tail_lamp_z": 1.24, "bumper_z": 0.48,
}

PICKUP = {
    "id": "PU190", "cls": "pickup_truck", "board": "harrow_h31",
    "about": "crew-cab pickups on the Harrow Ladder H-31: a five-seat cab and a 1.66 m bed; 1.96 m wide, 5.20 m long",
    "nose": 2.58, "tail": -0.94, "half_w": 0.98, "skirt": 0.33, "sill": 0.58, "floor": 0.55,
    "belt": belt_for(H_SUV), "head": 1.98, "cant": 2.06, "crown": 2.12, "headliner": 2.07, "tail_taper": 0.02,
    "front": {"kind": "hood", "toe": 1.24, "header": 0.42, "screen_base": belt_for(H_SUV) + 0.02, "lid": (2.42, 1.30), "hood_drop": 0.14},
    "rear": {"kind": "wall", "tail_in": -0.88, "back_window": {"half_w": 0.55, "z": (1.44, 1.90), "corner": 0.06}},
    "doors": [{"id": "F", "y0": 1.06, "y1": 0.20}, {"id": "B", "y0": 0.10, "y1": -0.70}],
    "cargo": {"kind": "bed", "y0": -0.94, "y1": -2.62, "half_w": 0.98, "floor_z": 0.62, "rail_z": 1.27, "rear": "tailgate"},
    "seats": [{"y": 0.40, "z": H_SUV, "xs": [-0.40, 0.40], "w": 0.52}, {"y": -0.40, "z": H_SUV + 0.02, "xs": [-0.42, 0.0, 0.42], "w": 0.42, "bench": True}],
    "head_lamp_z": 0.90, "tail_lamp_z": 1.00, "bumper_z": 0.50,
}

H_SPORT = 0.82
COUPE = {
    "id": "CP165", "cls": "coupe", "board": "solana_l25",
    "about": "two-seat coupes on the Solana Lattice L-25 (2.5 m): 1.78 m wide, 4.18 m long, 1.98 m tall",
    "nose": 2.08, "tail": -2.10, "half_w": 0.89, "skirt": 0.30, "sill": 0.56, "floor": 0.55,
    "belt": belt_for(H_SPORT), "head": 1.86, "cant": 1.93, "crown": 1.98, "headliner": 1.93,
    "front": {"kind": "hood", "toe": 0.98, "header": 0.12, "screen_base": belt_for(H_SPORT) + 0.02, "lid": (1.92, 1.06), "hood_drop": 0.30},
    "rear": {"kind": "trunk", "tail_in": -2.02, "c_top": -0.45, "c_foot": -1.30, "deck_z": belt_for(H_SPORT) - 0.02, "lid": (-1.34, -2.02)},
    "doors": [{"id": "F", "y0": 0.80, "y1": -0.30}],
    "seats": [{"y": -0.10, "z": H_SPORT, "xs": [-0.37, 0.37], "w": 0.50}],
    "head_lamp_z": 0.74, "tail_lamp_z": 1.00, "bumper_z": 0.45,
}

LIMO = {
    "id": "LM220", "cls": "limousine", "board": "carrow_k36",
    "about": "six-door limousines on the Carrow Keel K-36 (3.6 m): 1.86 m wide, 5.64 m long",
    "nose": 2.78, "tail": -2.86, "half_w": 0.93, "skirt": 0.30, "sill": 0.58, "floor": 0.55,
    "belt": belt_for(), "head": 1.90, "cant": 1.98, "crown": 2.04, "headliner": 1.99,
    "front": {"kind": "hood", "toe": 1.50, "header": 0.72, "screen_base": belt_for() + 0.02, "lid": (2.62, 1.60), "hood_drop": 0.28},
    "rear": {"kind": "trunk", "tail_in": -2.76, "c_top": -0.98, "c_foot": -1.90, "deck_z": belt_for() - 0.02, "lid": (-1.94, -2.76)},
    "doors": [{"id": "F", "y0": 1.30, "y1": 0.42}, {"id": "B", "y0": -0.24, "y1": -1.18}],
    "windows": [{"id": "M", "y0": 0.32, "y1": -0.14}],
    "seats": [{"y": 0.56, "z": H_FRONT, "xs": [-0.38, 0.38], "w": 0.50}, {"y": -0.86, "z": H_FRONT + 0.02, "xs": [-0.40, 0.0, 0.40], "w": 0.42, "bench": True}],
    "head_lamp_z": 0.78, "tail_lamp_z": 1.02, "bumper_z": 0.46,
}

HEARSE = dict(LIMO, **{
    "id": "HR220", "cls": "hearse", "about": "hearses on the Carrow Keel K-36: a long glasshouse and a rear deck behind the cab",
    "head": 1.94, "cant": 2.04, "crown": 2.10, "headliner": 2.05,
    "rear": {"kind": "hatch", "tail_in": -2.78, "hatch": hatch(0.72, 0.66, 1.93, 0.62, 1.40, 1.88)},
    "doors": [{"id": "F", "y0": 1.30, "y1": 0.42}],
    "windows": [{"id": "L", "y0": 0.32, "y1": -2.40}],
    "seats": [{"y": 0.56, "z": H_FRONT, "xs": [-0.38, 0.38], "w": 0.50}],
})

H_VAN = 0.95
VAN = {
    "id": "VN230", "cls": "van", "board": "steward_broad",
    "about": "forward-control vans on the Steward board, broad (3.75 m): 2.12 m wide, 6.20 m long, 2.52 m tall, standing room",
    "nose": 2.95, "tail": -3.25, "half_w": 1.06, "skirt": 0.36, "sill": 0.58, "floor": 0.55,
    "belt": belt_for(H_VAN), "head": 2.05, "cant": 2.44, "crown": 2.52, "headliner": 2.47, "nose_round": 0.22, "cant_in": 0.05,
    "front": {"kind": "flat", "toe": 2.80, "header": 2.40, "screen_base": belt_for(H_VAN) + 0.02, "hood_drop": 0.10},
    "rear": {"kind": "hatch", "tail_in": -3.17, "barn": {"half_w": 0.86, "z": (0.62, 2.30), "corner": 0.03, "glass_z": (1.52, 2.12)}},
    "doors": [{"id": "F", "y0": 1.32, "y1": 0.52}, {"id": "S", "y0": 0.30, "y1": -1.20, "sides": "R", "kind": "slide"}],
    "windows": [{"id": "W1", "y0": 0.30, "y1": -1.20, "sides": "L"}, {"id": "W2", "y0": -1.30, "y1": -2.90}],
    "seats": [{"y": 0.95, "z": H_VAN, "xs": [-0.45, 0.45], "w": 0.55}], "dash_y": 1.82,
    "head_lamp_z": 0.95, "tail_lamp_z": 1.10, "bumper_z": 0.52,
}
VAN_SEATS = VAN["seats"] + [{"y": -0.05, "z": H_VAN, "xs": [-0.55, 0.0, 0.55], "w": 0.50, "bench": True},
                            {"y": -0.85, "z": H_VAN, "xs": [-0.55, 0.0, 0.55], "w": 0.50, "bench": True},
                            {"y": -1.65, "z": H_VAN, "xs": [-0.55, 0.0, 0.55], "w": 0.50, "bench": True},
                            {"y": -2.45, "z": H_VAN, "xs": [-0.55, 0.0, 0.55], "w": 0.50, "bench": True}]


# ---- the heavy trucks: one cab-over cab, a cargo module per type (each a standard of its own)
H_TRUCK = 1.70
HEAVY_CAB = {
    "cls": "heavy_truck", "board": "steward_heavy", "high_floor": True, "heavy": True,
    "nose": 4.42, "tail": 2.30, "half_w": 1.24, "skirt": 0.42, "sill": 1.32, "floor": 1.30,
    "belt": belt_for(H_TRUCK), "head": 2.62, "cant": 2.86, "crown": 2.96, "headliner": 2.90, "nose_round": 0.25, "tail_taper": 0.02,
    "front": {"kind": "flat", "toe": 4.30, "header": 3.92, "screen_base": belt_for(H_TRUCK) + 0.02, "hood_drop": 0.10},
    "rear": {"kind": "wall", "tail_in": 2.36, "back_window": {"half_w": 0.60, "z": (2.20, 2.55), "corner": 0.05}},
    "doors": [{"id": "F", "y0": 3.62, "y1": 2.66}],
    "seats": [{"y": 2.95, "z": H_TRUCK, "xs": [-0.62, 0.0, 0.62], "w": 0.55}], "dash_y": 3.90,
    "head_lamp_z": 0.95, "tail_lamp_z": 1.20, "bumper_z": 0.60,
}


def heavy(sid, cls, cargo, about):
    d = dict(HEAVY_CAB)
    d.update({"id": sid, "cls": cls, "cargo": cargo, "about": about})
    return d


BOX = {"kind": "box", "y0": 2.30, "y1": -4.55, "half_w": 1.24, "floor_z": 1.30, "top_z": 3.45, "rear": "rollup"}
HEAVIES = [
    heavy("HB250", "box_truck", BOX, "box trucks: a cab-over cab and a 6.85 m box with a roll-up door, on the Steward heavy board"),
    heavy("HR250", "refrigerated_truck", dict(BOX, rear="barn"), "refrigerated box trucks: an insulated box, twin rear doors, a reefer unit"),
    heavy("HG250", "garbage_truck", dict(BOX, top_z=3.30, rear="hopper", y1=-4.35), "refuse trucks: a compactor body with a lifting rear hopper"),
    heavy("HY250", "recycling_truck", dict(BOX, top_z=3.20, rear="hopper", y1=-4.35), "recycling trucks: a compactor body and a side-loading arm"),
    heavy("HD250", "dump_truck", {"kind": "dump", "y0": 2.30, "y1": -4.40, "half_w": 1.24, "floor_z": 1.30, "rail_z": 2.40, "rear": "tailgate"},
          "dump trucks: an open tipping body with a tailgate"),
    heavy("HF250", "fire_engine", dict(BOX, top_z=2.95, rear="closed", y1=-4.50,
                                       doors=[{"id": "C1", "y0": 1.90, "y1": 0.90}, {"id": "C2", "y0": 0.40, "y1": -0.60},
                                              {"id": "C3", "y0": -1.40, "y1": -2.40}, {"id": "C4", "y0": -3.30, "y1": -4.20}]),
          "fire engines (pumpers): a body of roll-up compartments, a hose bed on top, ground ladders"),
    heavy("HL250", "ladder_truck", dict(BOX, top_z=2.60, rear="closed", y1=-4.50,
                                        doors=[{"id": "C1", "y0": 1.90, "y1": 0.90}, {"id": "C2", "y0": -2.60, "y1": -3.60}]),
          "aerial ladder trucks: a low compartment body under a turntable ladder"),
    heavy("HS250", "street_sweeper", dict(BOX, top_z=2.90, y1=-1.80, rear="hopper"), "street sweepers: a hopper body, side brooms and a pickup broom"),
    heavy("HT250", "milk_tanker", {"kind": "tank", "y0": 2.30, "y1": -4.50, "half_w": 1.10, "floor_z": 1.30, "tank_r": 0.95, "tank_z": 2.35},
          "milk tankers: an insulated stainless tank on a cradle"),
    heavy("HX250", "semi_truck", {"kind": "deck", "y0": 2.30, "y1": -4.30, "half_w": 1.10, "floor_z": 1.30, "rail_z": 1.30, "rear": "none"},
          "semi tractors: a cab-over cab and a deck with a fifth wheel"),
]

H_BUS = 0.97


def bus_windows():
    out = [{"id": "D", "y0": 4.40, "y1": 3.70, "sides": "L"}]
    y = 3.56
    k = 0
    while y - 0.76 > -4.70:
        out.append({"id": "W%d" % k, "y0": round(y, 3), "y1": round(y - 0.76, 3)})
        y -= 0.86
        k += 1
    return out


SCHOOL_BUS = {
    "id": "BS300", "cls": "school_bus", "board": "steward_heavy", "heavy": True,
    "about": "school buses on the Steward heavy board: 2.48 m wide, 9.8 m long, low floor; FMVSS 217 / 220 / 221 / 222",
    "nose": 4.85, "tail": -4.95, "half_w": 1.24, "skirt": 0.40, "sill": 0.58, "floor": 0.55,
    "belt": belt_for(H_BUS), "head": 2.12, "cant": 2.55, "crown": 2.68, "headliner": 2.62, "nose_round": 0.25, "cant_in": 0.06,
    "front": {"kind": "flat", "toe": 4.72, "header": 4.30, "screen_base": belt_for(H_BUS) + 0.02, "hood_drop": 0.08},
    "rear": {"kind": "hatch", "tail_in": -4.87, "barn": {"half_w": 0.40, "z": (0.62, 1.92), "corner": 0.03, "glass_z": (1.42, 1.86)}},
    "doors": [{"id": "E", "y0": 4.52, "y1": 3.66, "sides": "R", "kind": "slide"}],
    "windows": bus_windows(),
    "seats": [{"y": 3.95, "z": H_BUS, "xs": [-0.70], "w": 0.50}] +
             [{"y": round(2.95 - 0.71 * k, 3), "z": H_BUS, "xs": [-0.78, -0.36, 0.36, 0.78], "w": 0.40, "bench": True} for k in range(11)],
    "dash_y": 4.42, "head_lamp_z": 0.95, "tail_lamp_z": 1.10, "bumper_z": 0.55,
}

CLASSES = {c["id"]: c for c in [SEDAN, CROSSOVER, FULLSIZE, PICKUP, COUPE, LIMO, HEARSE, VAN] + HEAVIES + [SCHOOL_BUS]}

# ---------------------------------------------------------------- the base styles (one per class) and the types
DARK = {"lower": "paint", "upper": "black", "roof": "paint2", "sail": "black"}
STYLES = {
    "SD180": {"name": "carrow_saloon", "type": "sedan", "palette": palette(paint=(64, 98, 120), paint2=(64, 98, 120)), "panel": DARK,
              "head_lamp": "quad", "grille": "slots", "tail_lamp": "bar", "belt_trim": "chrome", "bumper": "chrome", "mirror": "chrome", "handle": "chrome"},
    "CU185": {"name": "carrow_trek", "type": "crossover_suv", "palette": palette(paint=(96, 112, 72), paint2=(226, 218, 196)), "panel": DARK,
              "head_lamp": "rect", "grille": "slots", "tail_lamp": "pixel", "bumper": "black", "mirror": "black", "handle": "black", "roof_rails": True},
    "FS200": {"name": "harrow_ranger", "type": "full_size_suv", "palette": palette(paint=(110, 40, 36), paint2=(110, 40, 36)), "panel": DARK,
              "head_lamp": "round", "grille": "slots", "tail_lamp": "pixel", "belt_trim": "chrome", "bumper": "chrome", "mirror": "chrome",
              "handle": "chrome", "roof_rails": True},
    "PU190": {"name": "harrow_workhorse", "type": "pickup_truck", "palette": palette(paint=(176, 56, 36), paint2=(176, 56, 36)),
              "panel": dict(DARK, cargo="paint"), "head_lamp": "round", "grille": "slots", "tail_lamp": "pixel", "bumper": "chrome",
              "mirror": "chrome", "handle": "chrome", "rail": "black"},
    "CP165": {"name": "solana_spark", "type": "sports_car", "palette": palette(paint=(210, 80, 40), paint2=(30, 31, 34)),
              "panel": {"lower": "paint", "upper": "black", "roof": "paint2", "sail": "black"}, "head_lamp": "projector", "grille": "band",
              "tail_lamp": "pixel", "bumper": "body", "mirror": "black", "handle": "black"},
    "LM220": {"name": "carrow_majestic", "type": "limousine", "palette": palette(paint=(20, 20, 24), paint2=(20, 20, 24)), "panel": DARK,
              "head_lamp": "quad", "grille": "slots", "tail_lamp": "bar", "belt_trim": "chrome", "bumper": "chrome", "mirror": "chrome", "handle": "chrome"},
    "HR220": {"name": "carrow_solace", "type": "hearse", "palette": palette(paint=(40, 40, 44), paint2=(40, 40, 44)), "panel": DARK,
              "head_lamp": "quad", "grille": "slots", "tail_lamp": "pixel", "belt_trim": "chrome", "bumper": "chrome", "mirror": "chrome",
              "handle": "chrome", "equipment": ["landau_bars"], "blank_windows": ["L"]},   # (a landau body: the irons on a blind quarter)
    "VN230": {"name": "carrow_courier", "type": "delivery_van", "palette": palette(paint=(236, 234, 228), paint2=(236, 234, 228)),
              "panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint"}, "head_lamp": "round", "grille": "slots",
              "tail_lamp": "pixel", "bumper": "black", "mirror": "black", "handle": "black", "blank_windows": ["W1", "W2"]},
    "BS300": {"name": "carrow_scholar", "type": "school_bus", "palette": palette(paint=(243, 169, 1), paint2=(236, 234, 228), livery2=(28, 28, 28)),
              "panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint"}, "head_lamp": "round", "grille": None,
              "tail_lamp": "pixel", "bumper": "black", "mirror": "black", "handle": "black",
              "livery": {"m": "livery2", "z": (0.92, 0.98)},
              "equipment": ["stop_arm", "crossview_mirrors", "school_warning", "roof_hatches"]},
}
TRUCK_PANEL = {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint", "cargo": "paint2"}
for sid, cls, paint, paint2, eq in (("HB250", "box_truck", (40, 70, 110), (236, 234, 228), []),
                                    ("HR250", "refrigerated_truck", (236, 234, 228), (236, 234, 228), ["reefer_unit"]),
                                    ("HG250", "garbage_truck", (60, 110, 60), (60, 110, 60), []),
                                    ("HY250", "recycling_truck", (30, 90, 150), (30, 90, 150), ["side_arm"]),
                                    ("HD250", "dump_truck", (220, 160, 30), (90, 90, 92), []),
                                    ("HF250", "fire_engine", (180, 24, 24), (180, 24, 24), ["lightbar", "hose_bed", "fire_ladders"]),
                                    ("HL250", "ladder_truck", (180, 24, 24), (180, 24, 24), ["lightbar", "aerial_ladder"]),
                                    ("HS250", "street_sweeper", (236, 234, 228), (236, 140, 24), ["beacon", "sweeper_brushes"]),
                                    ("HT250", "milk_tanker", (236, 234, 228), (210, 212, 216), []),
                                    ("HX250", "semi_truck", (30, 60, 110), (30, 60, 110), ["fifth_wheel"])):
    STYLES[sid] = {"name": "harrow_" + cls, "type": cls, "palette": palette(paint=paint, paint2=paint2),
                   "panel": dict(TRUCK_PANEL, cargo="paint2" if cls != "milk_tanker" else "chrome"), "head_lamp": "rect", "grille": "slots",
                   "tail_lamp": "pixel", "bumper": "black", "mirror": "black", "handle": "black", "rail": "black", "equipment": eq,
                   "bar_colours": ("lamp_red", "lamp_red") if "fire" in cls or "ladder" in cls else ("lamp_red", "lamp_blue")}
STYLES["HF250"]["livery"] = {"m": "livery1", "z": (2.18, 2.26)}
STYLES["HL250"]["livery"] = {"m": "livery1", "z": (2.18, 2.26)}

# variant types: a type built on a class by swapping or adding tokens and its palette
VARIANTS = {
    "SD180": [
        {"type": "luxury_sedan", "name": "carrow_regent", "palette": dict(paint=(26, 26, 30), paint2=(26, 26, 30), seat=(150, 110, 70)),
         "rebuild": {"head_lamp": "projector", "grille": "band"}, "inlay": {"m": "wood", "frame": "chrome", "z": (0.70, None)}},
        {"type": "company_car", "name": "carrow_fleet", "palette": dict(paint=(150, 152, 156), paint2=(150, 152, 156)),
         "rebuild": {"belt_trim": "black", "bumper": "black", "mirror": "black"}},
        {"type": "police_car", "name": "civic_police", "palette": dict(paint=(26, 28, 32), paint2=(236, 236, 232)),
         "rebuild": {"belt_trim": "black", "bumper": "black", "mirror": "black"},
         "livery": {"m": "livery1", "z": (0.62, None)}, "equipment": ["lightbar", "push_bar", "spotlight"]},
        {"type": "taxi", "name": "civic_cab", "palette": dict(paint=(236, 186, 30), paint2=(236, 186, 30), livery2=(28, 28, 28)),
         "livery": {"m": "livery2", "z": (0.98, 1.06)}, "equipment": ["taxi_sign"]},
        {"type": "fire_chief_car", "name": "civic_fire_chief", "palette": dict(paint=(176, 24, 24), paint2=(236, 236, 232)),
         "rebuild": {"belt_trim": "black", "bumper": "black"}, "livery": {"m": "livery1", "z": (0.96, 1.04)}, "equipment": ["lightbar"],
         "bar_colours": ("lamp_red", "lamp_red")},
    ],
    "FS200": [
        {"type": "police_suv", "name": "civic_police_suv", "palette": dict(paint=(26, 28, 32), paint2=(236, 236, 232)),
         "rebuild": {"belt_trim": "black", "bumper": "black", "mirror": "black"},
         "livery": {"m": "livery1", "z": (0.62, None)}, "equipment": ["lightbar", "push_bar"]},
    ],
    "PU190": [
        {"type": "public_works_pickup", "name": "civic_works", "palette": dict(paint=(236, 120, 24), paint2=(236, 120, 24)),
         "rebuild": {"bumper": "black", "mirror": "black"}, "equipment": ["beacon", "bed_rack", "toolbox"]},
        {"type": "tow_truck", "name": "civic_tow", "palette": dict(paint=(236, 234, 228), paint2=(30, 60, 110)),
         "rebuild": {"bumper": "black"}, "equipment": ["lightbar", "wheel_lift"], "bar_colours": ("lamp_amber", "lamp_amber")},
        {"type": "utility_bucket_truck", "name": "civic_utility", "palette": dict(paint=(236, 234, 228), paint2=(236, 234, 228)),
         "rebuild": {"bumper": "black"}, "equipment": ["beacon", "bucket_boom"]},
    ],
    "CP165": [
        {"type": "convertible", "name": "solana_breeze", "palette": dict(paint=(40, 92, 150), paint2=(196, 176, 140)),
         "equipment": ["soft_top_bows"]},
    ],
    "VN230": [
        {"type": "parcel_van", "name": "carrow_parcel", "palette": dict(paint=(110, 76, 46), paint2=(110, 76, 46), livery1=(236, 186, 30)),
         "livery": {"m": "livery1", "z": (1.05, 1.13)}},
        {"type": "service_van", "name": "carrow_service", "palette": dict(paint=(236, 234, 228)), "equipment": ["ladder_rack", "beacon"]},
        {"type": "paratransit_van", "name": "carrow_access", "palette": dict(paint=(236, 234, 228), livery2=(40, 80, 160)),
         "blank_windows": [], "reshell": ["pane_", "seats_"], "seats": VAN_SEATS, "livery": {"m": "livery2", "z": (0.98, 1.08)},
         "equipment": ["dest_sign"]},
        {"type": "ambulance", "name": "civic_ambulance", "palette": dict(paint=(240, 240, 236), livery2=(200, 30, 30)),
         "livery": {"m": "livery2", "z": (1.00, 1.14)}, "equipment": ["lightbar"], "bar_colours": ("lamp_red", "lamp_red")},
        {"type": "hotel_shuttle", "name": "carrow_shuttle", "palette": dict(paint=(110, 30, 40), paint2=(226, 218, 196)),
         "blank_windows": [], "reshell": ["pane_", "seats_"], "seats": VAN_SEATS, "rebuild": {"belt_trim": "chrome"}, "equipment": ["dest_sign"]},
        {"type": "food_truck", "name": "carrow_kitchen", "palette": dict(paint=(40, 140, 130), livery2=(236, 186, 30)),
         "blank_windows": ["W1", "W2"], "equipment": ["awning", "menu"]},
        {"type": "ice_cream_truck", "name": "carrow_creamery", "palette": dict(paint=(240, 236, 236), livery2=(236, 130, 170)),
         "livery": {"m": "livery2", "z": (0.98, 1.20)}, "equipment": ["awning", "cone_sign"]},
        {"type": "mail_truck", "name": "civic_post", "palette": dict(paint=(240, 240, 236), livery1=(30, 60, 140), livery2=(200, 30, 30)),
         "driver": "R", "reshell": ["seats_", "dash"], "livery": {"m": "livery2", "z": (1.00, 1.06)}},
        {"type": "armored_truck", "name": "civic_vault", "palette": dict(paint=(70, 80, 70), paint2=(70, 80, 70)),
         "rebuild": {"bumper": "black"}},
    ],
}

# ======================================================================== the remainder, part 1: road types (2026-10-02)
FLATBED = dict(PICKUP, **{"id": "PF190", "cls": "farm_pickup_flatbed",
                          "about": "crew-cab flatbeds on the Harrow Ladder H-31: the pickup's cab and a stake-sided deck over the wheels",
                          "cargo": {"kind": "deck", "y0": -0.94, "y1": -2.62, "half_w": 0.98, "floor_z": 1.00, "rail_z": 1.00, "rear": "none"}})
HEAVIES += [
    heavy("HK250", "grain_truck", {"kind": "dump", "y0": 2.30, "y1": -4.50, "half_w": 1.24, "floor_z": 1.30, "rail_z": 2.90, "rear": "tailgate"},
          "grain trucks: a tall open grain body with a tailgate and a tarp bow"),
    heavy("HM250", "cement_mixer", {"kind": "deck", "y0": 2.30, "y1": -4.40, "half_w": 1.20, "floor_z": 1.30, "rail_z": 1.30, "rear": "none"},
          "concrete mixers: a deck carrying the revolving drum and its chute"),
    heavy("HC250", "mobile_crane", {"kind": "deck", "y0": 2.30, "y1": -4.40, "half_w": 1.24, "floor_z": 1.30, "rail_z": 1.30, "rear": "none"},
          "truck cranes: a deck with a slewing telescopic boom and outriggers"),
    heavy("HW250", "tram_maintenance_car", dict(BOX, top_z=2.70, rear="barn", y1=-2.20),
          "tram maintenance cars: a tool box body and a wire-tower platform on the roof"),
]
MOTORHOME = dict(SCHOOL_BUS, **{
    "id": "MH300", "cls": "motorhome", "about": "motorhomes on the Steward heavy board: a coach body, an entry door, a few windows",
    "doors": [{"id": "E", "y0": 1.10, "y1": 0.30, "sides": "R", "kind": "slide"}, {"id": "F", "y0": 4.40, "y1": 3.70, "sides": "L"}],
    "windows": [{"id": "C", "y0": 4.40, "y1": 3.70, "sides": "R"}, {"id": "W0", "y0": 2.30, "y1": 1.30}, {"id": "W1", "y0": -0.20, "y1": -1.50},
                {"id": "W2", "y0": -3.20, "y1": -4.40}],
    "rear": {"kind": "wall", "tail_in": -4.87, "back_window": {"half_w": 0.80, "z": (1.60, 2.10), "corner": 0.06}},
    "seats": [{"y": 3.95, "z": H_BUS, "xs": [-0.62, 0.62], "w": 0.55}, {"y": 2.0, "z": H_BUS, "xs": [-0.70, -0.30], "w": 0.40, "bench": True},
              {"y": 0.9, "z": H_BUS, "xs": [-0.70, -0.30], "w": 0.40, "bench": True}],
})


def transit_windows():
    out = [{"id": "D", "y0": 4.40, "y1": 3.70, "sides": "L"}]
    y = 3.56
    k = 0
    while y - 1.10 > -4.70:
        if not (y > 0.60 and y - 1.10 < 1.95):          # (the middle door's span on the right: the left keeps its windows)
            out.append({"id": "W%d" % k, "y0": round(y, 3), "y1": round(y - 1.10, 3)})
        else:
            out.append({"id": "W%d" % k, "y0": round(y, 3), "y1": round(y - 1.10, 3), "sides": "L"})
        y -= 1.20
        k += 1
    return out


TRANSIT_BUS = dict(SCHOOL_BUS, **{
    "id": "TB300", "cls": "transit_bus", "about": "low-floor transit buses on the Steward heavy board: front and centre doors, a destination sign",
    "doors": [{"id": "E", "y0": 4.52, "y1": 3.66, "sides": "R", "kind": "slide"}, {"id": "M", "y0": 1.90, "y1": 0.66, "sides": "R", "kind": "slide"}],
    "windows": transit_windows(),
    "rear": {"kind": "wall", "tail_in": -4.87, "back_window": {"half_w": 0.90, "z": (1.70, 2.20), "corner": 0.06}},
    "seats": [{"y": 3.95, "z": H_BUS, "xs": [-0.70], "w": 0.50}] +
             [{"y": round(y, 3), "z": H_BUS, "xs": [-0.78, -0.36, 0.36, 0.78], "w": 0.40, "bench": True} for y in (0.3, -0.5, -1.3, -2.1, -2.9, -3.7)] +
             [{"y": 3.0, "z": H_BUS, "xs": [-0.78, -0.36], "w": 0.40, "bench": True}, {"y": 2.2, "z": H_BUS, "xs": [-0.78, -0.36], "w": 0.40, "bench": True}],
})
CLASSES.update({c["id"]: c for c in [FLATBED, MOTORHOME, TRANSIT_BUS] + HEAVIES[-4:]})

STYLES["PF190"] = dict(STYLES["PU190"], name="harrow_farmhand", type="farm_pickup_flatbed", palette=palette(paint=(70, 90, 60), paint2=(70, 90, 60)),
                       equipment=["stakes"])
for sid, cls, paint, paint2, eq in (("HK250", "grain_truck", (150, 40, 32), (150, 40, 32), ["tarp_bows"]),
                                    ("HM250", "cement_mixer", (236, 234, 228), (236, 140, 24), ["mixer_drum"]),
                                    ("HC250", "mobile_crane", (236, 186, 30), (236, 186, 30), ["crane_boom", "beacon"]),
                                    ("HW250", "tram_maintenance_car", (236, 140, 24), (236, 140, 24), ["wire_tower", "beacon"])):
    STYLES[sid] = {"name": "harrow_" + cls, "type": cls, "palette": palette(paint=paint, paint2=paint2), "panel": dict(TRUCK_PANEL),
                   "head_lamp": "rect", "grille": "slots", "tail_lamp": "pixel", "bumper": "black", "mirror": "black", "handle": "black",
                   "rail": "black", "equipment": eq}
STYLES["MH300"] = {"name": "carrow_wayfarer", "type": "motorhome", "palette": palette(paint=(236, 230, 214), paint2=(236, 230, 214), livery2=(150, 90, 50)),
                   "panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint"}, "head_lamp": "rect", "grille": "slots",
                   "tail_lamp": "pixel", "bumper": "chrome", "mirror": "black", "handle": "chrome", "livery": {"m": "livery2", "z": (0.80, 1.10)},
                   "equipment": ["ac_units", "side_awning"]}
STYLES["TB300"] = {"name": "carrow_metro", "type": "transit_bus", "palette": palette(paint=(236, 234, 228), paint2=(236, 234, 228), livery2=(30, 110, 90)),
                   "panel": {"lower": "paint", "upper": "black", "roof": "paint2", "sail": "black"}, "head_lamp": "round", "grille": None,
                   "tail_lamp": "pixel", "bumper": "black", "mirror": "black", "handle": "black", "livery": {"m": "livery2", "z": (0.62, 1.30)},
                   "equipment": ["dest_sign_front", "ac_units"]}
VARIANTS["SD180"].append({"type": "unmarked_car", "name": "civic_unmarked", "palette": dict(paint=(60, 62, 66), paint2=(60, 62, 66)),
                          "rebuild": {"belt_trim": "black", "bumper": "black", "mirror": "black"}, "equipment": ["spotlight"]})
VARIANTS["PU190"] += [
    {"type": "lifeguard_truck", "name": "civic_lifeguard", "palette": dict(paint=(236, 186, 30), paint2=(200, 30, 30)), "rebuild": {"bumper": "black"},
     "equipment": ["lightbar", "bed_rack", "rescue_boards"], "bar_colours": ("lamp_red", "lamp_amber")},
    {"type": "brush_truck", "name": "civic_brush", "palette": dict(paint=(180, 24, 24), paint2=(180, 24, 24)), "rebuild": {"bumper": "black"},
     "equipment": ["lightbar", "water_tank"], "bar_colours": ("lamp_red", "lamp_red")},
    {"type": "hi_rail_truck", "name": "civic_hirail", "palette": dict(paint=(236, 120, 24), paint2=(236, 120, 24)), "rebuild": {"bumper": "black"},
     "equipment": ["beacon", "rail_gear", "toolbox"]},
]
VARIANTS.setdefault("HX250", []).append({"type": "yard_tug", "name": "harrow_yard", "palette": dict(paint=(236, 186, 30), paint2=(236, 186, 30)),
                                         "equipment": ["beacon"]})
VARIANTS.setdefault("TB300", []).append({"type": "sightseeing_trolley", "name": "carrow_trolley",
                                         "palette": dict(paint=(110, 30, 40), paint2=(226, 218, 196), livery2=(128, 74, 40)),
                                         "rebuild": {"belt_trim": "chrome", "bumper": "chrome"}, "equipment": ["trolley_bell"]})

# ======================================================================== the remainder, part 2: trailers (Harrow running gear)
def trailer(sid, cls, board, cargo, about):
    return {"id": sid, "cls": cls, "board": board, "trailer": True, "cargo": cargo, "about": about}


def vents(y0, y1, n, w):
    step = (y0 - y1) / n
    return [{"id": "V%d" % k, "y0": round(y0 - k * step, 3), "y1": round(y0 - k * step - w, 3)} for k in range(n)]


TRAILERS = [
    trailer("TU250", "utility_trailer", "harrow_tr25", {"kind": "bed", "y0": 1.25, "y1": -1.30, "half_w": 0.66, "floor_z": 0.62, "rail_z": 0.98,
                                                        "rear": "tailgate", "no_arch": True, "fenders": True, "skirt": 0.50},
            "single-axle utility trailers: an open bed between fendered wheels"),
    trailer("TB500", "boat_trailer", "harrow_tr50", {"kind": "deck", "y0": 2.50, "y1": -2.50, "half_w": 0.55, "floor_z": 0.66, "rail_z": 0.66,
                                                     "rear": "none", "no_arch": True, "skirt": 0.52},
            "tandem boat trailers: a keel deck, carpeted bunks and a winch post"),
    trailer("TC500", "camper_trailer", "harrow_tr50", {"kind": "box", "y0": 2.50, "y1": -2.50, "half_w": 1.15, "floor_z": 0.62, "top_z": 2.75,
                                                       "rear": "closed", "win_z": (1.30, 2.10),
                                                       "windows": [{"id": "W1", "y0": 1.90, "y1": 0.95}, {"id": "W2", "y0": -0.90, "y1": -1.80, "sides": "L"}],
                                                       "doors": [{"id": "E", "y0": -0.88, "y1": -1.68, "sides": "R", "kind": "hinge"}]},   # (aft of the axles)
            "caravans: a lined box with windows and an entry door, on tandem gear"),
    trailer("TL500", "livestock_trailer", "harrow_tr50", {"kind": "box", "y0": 2.50, "y1": -2.60, "half_w": 1.10, "floor_z": 0.62, "top_z": 2.40,
                                                          "rear": "barn", "win_z": (1.55, 2.15), "vents": vents(2.30, -2.40, 5, 0.70)},
            "livestock trailers: a box of slatted vents, twin rear doors"),
    trailer("TS150", "semi_trailer_dry", "harrow_ts150", {"kind": "box", "y0": 7.40, "y1": -7.50, "half_w": 1.30, "floor_z": 1.25, "top_z": 4.05,
                                                          "rear": "barn"}, "dry van semi trailers: a 14.9 m box, twin rear doors"),
    trailer("TR150", "semi_trailer_reefer", "harrow_ts150", {"kind": "box", "y0": 7.40, "y1": -7.50, "half_w": 1.30, "floor_z": 1.25, "top_z": 4.05,
                                                             "rear": "barn"}, "refrigerated semi trailers: an insulated box and a reefer unit"),
    trailer("TW150", "low_loader", "harrow_ts150", {"kind": "deck", "y0": 7.40, "y1": -7.50, "half_w": 1.30, "floor_z": 1.10, "rail_z": 1.10,
                                                    "rear": "none", "no_arch": True},
            "low loaders: a flat machinery deck with ramps"),
]
CLASSES.update({t["id"]: t for t in TRAILERS})
for sid, cls, paint, paint2, eq in (("TU250", "utility_trailer", (40, 42, 46), (40, 42, 46), []),
                                    ("TB500", "boat_trailer", (150, 152, 156), (150, 152, 156), ["bunks"]),
                                    ("TC500", "camper_trailer", (236, 230, 214), (236, 230, 214), []),
                                    ("TL500", "livestock_trailer", (190, 192, 196), (190, 192, 196), []),
                                    ("TS150", "semi_trailer_dry", (236, 234, 228), (236, 234, 228), []),
                                    ("TR150", "semi_trailer_reefer", (236, 234, 228), (236, 234, 228), ["reefer_unit"]),
                                    ("TW150", "low_loader", (236, 186, 30), (40, 42, 46), ["ramps"])):
    STYLES[sid] = {"name": "harrow_" + cls, "type": cls, "palette": palette(paint=paint, paint2=paint2),
                   "panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint", "cargo": "paint"},
                   "rail": "black", "equipment": eq}

# ======================================================================== the remainder, part 3: open light vehicles (Solana micro boards)
def light(sid, cls, board, cargo, open_, about):
    return {"id": sid, "cls": cls, "board": board, "trailer": True, "cargo": cargo, "open": open_, "about": about}


LIGHTS = [
    light("LG165", "golf_cart", "solana_m16",
          {"kind": "bed", "y0": 1.20, "y1": -1.25, "half_w": 0.62, "floor_z": 0.42, "rail_z": 0.72, "rear": "closed", "skirt": 0.28},
          {"seats": [{"y": -0.10, "z": 0.72, "xs": [-0.28, 0.28], "w": 0.50, "bench": True}], "controls": "wheel",
           "cowl": {"y0": 1.20, "y1": 0.68, "z1": 0.98}, "canopy": {"y0": 0.70, "y1": -0.95, "z": 1.85}, "extras": ["bag_rack"]},
          "golf carts: a two-seat tub under a canopy"),
    light("LU165", "utility_cart", "solana_m16",
          {"kind": "bed", "y0": 1.20, "y1": -1.25, "half_w": 0.62, "floor_z": 0.42, "rail_z": 0.72, "rear": "closed", "skirt": 0.28},
          {"seats": [{"y": 0.15, "z": 0.72, "xs": [-0.28, 0.28], "w": 0.50, "bench": True}], "controls": "wheel",
           "cowl": {"y0": 1.20, "y1": 0.80, "z1": 0.98}, "canopy": {"y0": 0.80, "y1": -0.20, "z": 1.85}, "bed": (-0.30, -1.20), "extras": ["rear_bed"]},
          "the Steward's utility carts: two seats under a canopy, a load bed"),
    light("LH165", "hydroponics_harvest_cart", "solana_m16",
          {"kind": "bed", "y0": 1.00, "y1": -1.00, "half_w": 0.24, "floor_z": 0.42, "rail_z": 0.66, "rear": "closed", "skirt": 0.28, "no_arch": True},
          {"seats": [{"y": 0.35, "z": 0.72, "xs": [0.0], "w": 0.44}], "controls": "tiller", "driver": "C", "extras": ["crates"]},
          "hydroponics harvest carts: a narrow tub, a perch seat, crates"),
    light("LV200", "utv", "solana_m20",
          {"kind": "bed", "y0": 1.35, "y1": -1.36, "half_w": 0.72, "floor_z": 0.48, "rail_z": 0.88, "rear": "closed", "skirt": 0.34},
          {"seats": [{"y": 0.05, "z": 0.86, "xs": [-0.32, 0.32], "w": 0.50}], "controls": "wheel",
           "cowl": {"y0": 1.35, "y1": 0.72, "z1": 1.12}, "cage": (0.62, -0.42, 1.95), "bed": (-0.48, -1.32), "extras": ["rear_bed"]},
          "utility vehicles: two seats in a roll cage, a tipping bed"),
    light("LP200", "parks_mower", "solana_m20",
          {"kind": "bed", "y0": 1.45, "y1": -1.42, "half_w": 0.70, "floor_z": 0.48, "rail_z": 0.80, "rear": "closed", "skirt": 0.34},
          {"seats": [{"y": -0.20, "z": 0.95, "xs": [0.0], "w": 0.50}], "controls": "wheel", "driver": "C",
           "cowl": {"y0": 1.30, "y1": 0.40, "z1": 1.05}, "extras": ["mower_deck", "rops"]},
          "park mowers: a seat over a wide cutting deck, a roll bar"),
    light("LR120", "riding_mower", "solana_m12",
          {"kind": "bed", "y0": 0.90, "y1": -0.90, "half_w": 0.48, "floor_z": 0.44, "rail_z": 0.66, "rear": "closed", "skirt": 0.30},
          {"seats": [{"y": -0.35, "z": 0.84, "xs": [0.0], "w": 0.44}], "controls": "wheel", "driver": "C",
           "cowl": {"y0": 0.90, "y1": 0.05, "z1": 0.78}, "extras": ["mower_deck"]},
          "riding mowers: a hood, a seat, a cutting deck between the wheels"),
    light("LA120", "atv", "solana_m12",
          {"kind": "bed", "y0": 0.90, "y1": -0.92, "half_w": 0.50, "floor_z": 0.46, "rail_z": 0.70, "rear": "closed", "skirt": 0.32},
          {"seats": [{"y": -0.20, "z": 0.92, "xs": [0.0], "saddle": True}], "controls": "bar", "driver": "C",
           "cowl": {"y0": 0.90, "y1": 0.30, "z1": 0.86}, "extras": ["racks"]},
          "all-terrain vehicles: a saddle, handlebars, racks fore and aft"),
    light("LK100", "go_kart", "solana_m10",
          {"kind": "bed", "y0": 0.80, "y1": -0.80, "half_w": 0.52, "floor_z": 0.24, "rail_z": 0.44, "rear": "closed", "skirt": 0.14},
          {"seats": [{"y": -0.20, "z": 0.40, "xs": [0.0], "w": 0.42, "back": 30}], "controls": "wheel", "driver": "C",
           "cowl": {"y0": 0.72, "y1": 0.25, "z1": 0.50}, "extras": ["kart_bumpers"]},
          "go-karts: a low tub, a bucket seat, bumpers"),
    light("LB100", "bumper_car", "solana_m10",
          {"kind": "bed", "y0": 0.80, "y1": -0.80, "half_w": 0.58, "floor_z": 0.24, "rail_z": 0.58, "rear": "closed", "skirt": 0.14},
          {"seats": [{"y": -0.15, "z": 0.50, "xs": [0.0], "w": 0.50}], "controls": "wheel", "driver": "C",
           "cowl": {"y0": 0.72, "y1": 0.25, "z1": 0.70}, "extras": ["bumper_ring"]},
          "bumper cars: a round tub in a rubber ring, a pole to the ceiling grid"),
    light("LS060", "mobility_scooter", "solana_m06",
          {"kind": "bed", "y0": 0.55, "y1": -0.55, "half_w": 0.32, "floor_z": 0.26, "rail_z": 0.40, "rear": "closed", "skirt": 0.14},
          {"seats": [{"y": -0.18, "z": 0.70, "xs": [0.0], "w": 0.46}], "controls": "tiller", "driver": "C", "extras": ["basket"]},
          "mobility scooters: a floor pan, a swivel seat, a tiller and a basket"),
    light("LC060", "power_wheelchair", "solana_m06",
          {"kind": "bed", "y0": 0.55, "y1": -0.55, "half_w": 0.32, "floor_z": 0.26, "rail_z": 0.40, "rear": "closed", "skirt": 0.14},
          {"seats": [{"y": -0.05, "z": 0.62, "xs": [0.0], "w": 0.46}], "controls": "joystick", "driver": "C", "extras": ["armrests"]},
          "power wheelchairs: a seat with armrests over the board, a joystick"),
]
CLASSES.update({t["id"]: t for t in LIGHTS})
for sid, cls, paint, roof in (("LG165", "golf_cart", (236, 234, 228), (40, 92, 70)), ("LU165", "utility_cart", (236, 186, 30), (236, 186, 30)),
                              ("LH165", "hydroponics_harvest_cart", (236, 234, 228), (60, 150, 90)), ("LV200", "utv", (96, 112, 72), (96, 112, 72)),
                              ("LP200", "parks_mower", (60, 120, 60), (60, 120, 60)), ("LR120", "riding_mower", (190, 40, 30), (190, 40, 30)),
                              ("LA120", "atv", (176, 56, 36), (176, 56, 36)), ("LK100", "go_kart", (236, 140, 24), (236, 140, 24)),
                              ("LB100", "bumper_car", (40, 110, 200), (40, 110, 200)), ("LS060", "mobility_scooter", (150, 30, 40), (150, 30, 40)),
                              ("LC060", "power_wheelchair", (40, 42, 46), (40, 42, 46))):
    STYLES[sid] = {"name": "solana_" + cls, "type": cls, "palette": palette(paint=paint, paint2=roof),
                   "panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint", "cargo": "paint"}, "rail": "black", "equipment": []}

# ======================================================================== the remainder, part 4: farm and site machines
H_FARM = 0.95
TRACTOR = {
    "id": "FT225", "cls": "utility_tractor", "board": "steward_farm5", "wheels_outside": True,
    "about": "utility tractors on the Steward farm board: a narrow bonnet and a glass cab between big equal wheels",
    "nose": 2.25, "tail": -1.55, "half_w": 0.50, "skirt": 0.40, "sill": 0.58, "floor": 0.55,
    "belt": belt_for(H_FARM), "head": 2.25, "cant": 2.40, "crown": 2.48, "headliner": 2.43, "nose_round": 0.20, "cant_in": 0.05, "tumble": 0.03,
    "front": {"kind": "hood", "toe": -0.05, "header": -0.40, "screen_base": belt_for(H_FARM) + 0.02, "lid": (2.10, 0.10), "hood_drop": 0.22},
    "rear": {"kind": "wall", "tail_in": -1.49, "back_window": {"half_w": 0.38, "z": (1.50, 2.15), "corner": 0.05}},
    "pillar_inset": 0.03,
    "doors": [{"id": "F", "y0": -0.12, "y1": -0.44}],                 # (ends ahead of the rear mudguard: an open door clears it)
    "windows": [{"id": "Q", "y0": -0.54, "y1": -1.40}],
    "seats": [{"y": -0.78, "z": H_FARM, "xs": [0.0], "w": 0.52}], "driver": "C",
    "head_lamp_z": 1.00, "tail_lamp_z": 1.20, "bumper_z": 0.55,
}
ROWCROP = dict(TRACTOR, **{"id": "FR375", "cls": "row_crop_tractor", "board": "steward_farm7", "about": "row-crop tractors on the long farm board",
                           "nose": 3.05, "tail": -2.30, "half_w": 0.50,
                           "front": {"kind": "hood", "toe": 0.40, "header": 0.02, "screen_base": belt_for(H_FARM) + 0.02, "lid": (2.90, 0.55), "hood_drop": 0.22},
                           "rear": {"kind": "wall", "tail_in": -2.24, "back_window": {"half_w": 0.38, "z": (1.50, 2.15), "corner": 0.05}},
                           "doors": [{"id": "F", "y0": 0.33, "y1": -0.60}], "windows": [{"id": "Q", "y0": -0.70, "y1": -2.10}],
                           "seats": [{"y": -0.40, "z": H_FARM, "xs": [0.0], "w": 0.52}]})
BACKHOE = dict(ROWCROP, **{"id": "FB375", "cls": "backhoe_loader", "about": "backhoe loaders on the long farm board: a loader in front, a backhoe behind"})
CLASSES.update({c["id"]: c for c in (TRACTOR, ROWCROP, BACKHOE)})
HEAVIES2 = [
    heavy("HH250", "combine_harvester", dict(BOX, top_z=3.70, rear="closed", y1=-4.00), "combine harvesters: a cab-over cab, a grain tank body, a header in front"),
    heavy("HP250", "crop_sprayer", {"kind": "tank", "y0": 2.30, "y1": -3.80, "half_w": 1.05, "floor_z": 1.30, "tank_r": 0.85, "tank_z": 2.25},
          "self-propelled sprayers: a cab, a tank, booms folded along the sides"),
]
CLASSES.update({c["id"]: c for c in HEAVIES2})
IMPLEMENTS = [
    trailer("IG500", "grain_cart", "harrow_tr50", {"kind": "bed", "y0": 2.50, "y1": -2.50, "half_w": 1.25, "floor_z": 0.70, "rail_z": 2.60, "rear": "closed"},
            "grain carts: a tall open hopper with a folding auger"),
    trailer("IW500", "hay_wagon", "harrow_tr50", {"kind": "deck", "y0": 2.50, "y1": -2.50, "half_w": 1.20, "floor_z": 0.95, "rail_z": 0.95, "rear": "none", "no_arch": True},
            "hay wagons: a flat deck with end racks and bales"),
    trailer("IM500", "manure_spreader", "harrow_tr50", {"kind": "bed", "y0": 2.40, "y1": -2.40, "half_w": 1.05, "floor_z": 0.70, "rail_z": 1.55, "rear": "none"},
            "manure spreaders: an open box with beaters across its rear"),
    trailer("IB250", "hay_baler", "harrow_tr25", {"kind": "box", "y0": 1.25, "y1": -1.30, "half_w": 0.66, "floor_z": 0.62, "top_z": 1.75, "rear": "closed", "no_arch": True},
            "hay balers: a bale chamber, a pickup reel and a chute"),
    trailer("IP500", "planter_drill", "harrow_tr50", {"kind": "deck", "y0": 2.50, "y1": -2.50, "half_w": 0.80, "floor_z": 0.90, "rail_z": 0.90, "rear": "none", "no_arch": True},
            "planters: a folded toolbar of row units on tandem gear"),
    trailer("ID250", "plough_disc", "harrow_tr25", {"kind": "deck", "y0": 1.25, "y1": -1.30, "half_w": 0.60, "floor_z": 0.70, "rail_z": 0.70, "rear": "none", "no_arch": True},
            "disc harrows: two gangs of discs on a transport axle"),
]
CLASSES.update({t["id"]: t for t in IMPLEMENTS})
SITE = [
    light("SK165", "skid_steer", "solana_m16",
          {"kind": "bed", "y0": 1.20, "y1": -1.15, "half_w": 0.60, "floor_z": 0.42, "rail_z": 0.80, "rear": "closed", "skirt": 0.28},
          {"seats": [{"y": -0.25, "z": 0.86, "xs": [0.0], "w": 0.50}], "controls": "bar", "driver": "C", "canopy": {"y0": 0.40, "y1": -0.95, "z": 1.95},
           "cage": (0.40, -0.95, 1.92), "extras": ["loader_arms"]},
          "skid-steer loaders: a caged seat between lifting arms and a bucket"),
    light("SF165", "forklift", "solana_m16",
          {"kind": "bed", "y0": 1.20, "y1": -1.15, "half_w": 0.58, "floor_z": 0.42, "rail_z": 0.70, "rear": "closed", "skirt": 0.28},
          {"seats": [{"y": -0.30, "z": 0.95, "xs": [0.0], "w": 0.50}], "controls": "wheel", "driver": "C", "canopy": {"y0": 0.35, "y1": -0.85, "z": 2.10},
           "extras": ["mast"]},
          "forklifts: a seat under an overhead guard, a mast and forks, a counterweight"),
]
CLASSES.update({t["id"]: t for t in SITE})
EXCAVATOR = trailer("SE820", "excavator", "steward_heavy", {"kind": "deck", "y0": 3.60, "y1": -3.60, "half_w": 1.10, "floor_z": 1.15, "rail_z": 1.15,
                                                              "rear": "none", "no_arch": True},
                    "excavators: crawler tracks, a slewing house with its cab, boom, stick and bucket")
CLASSES[EXCAVATOR["id"]] = EXCAVATOR

FARM_PANEL = {"lower": "paint", "upper": "black", "roof": "paint2", "sail": "black", "cargo": "paint"}
STYLES["FT225"] = {"name": "steward_tiller", "type": "utility_tractor", "palette": palette(paint=(60, 120, 60), paint2=(236, 234, 228)), "panel": FARM_PANEL,
                   "head_lamp": "rect", "grille": "slots", "tail_lamp": "pixel", "bumper": "black", "mirror": "black", "handle": "black",
                   "equipment": ["fenders_big", "hitch3", "beacon"]}
STYLES["FR375"] = dict(STYLES["FT225"], name="steward_furrow", type="row_crop_tractor", palette=palette(paint=(190, 40, 30), paint2=(236, 234, 228)))
STYLES["FB375"] = dict(STYLES["FT225"], name="steward_delver", type="backhoe_loader", palette=palette(paint=(236, 186, 30), paint2=(236, 186, 30)),
                       equipment=["fenders_big", "loader", "backhoe", "beacon"])
STYLES["HH250"] = {"name": "steward_reaper", "type": "combine_harvester", "palette": palette(paint=(60, 120, 60), paint2=(236, 234, 228)),
                   "panel": dict(TRUCK_PANEL, cargo="paint"), "head_lamp": "rect", "grille": "slots", "tail_lamp": "pixel", "bumper": "black", "mirror": "black",
                   "handle": "black", "rail": "black", "equipment": ["header", "auger", "beacon"]}
STYLES["HP250"] = dict(STYLES["HH250"], name="steward_mister", type="crop_sprayer", palette=palette(paint=(236, 234, 228), paint2=(60, 120, 60)),
                       panel=dict(TRUCK_PANEL, cargo="paint2"), equipment=["spray_booms", "beacon"])
for sid, cls, paint, eq in (("IG500", "grain_cart", (60, 120, 60), ["auger"]), ("IW500", "hay_wagon", (128, 74, 40), ["hay_racks"]),
                            ("IM500", "manure_spreader", (190, 40, 30), ["beaters"]), ("IB250", "hay_baler", (60, 120, 60), ["pickup"]),
                            ("IP500", "planter_drill", (236, 186, 30), ["planter"]), ("ID250", "plough_disc", (190, 40, 30), ["discs"])):
    STYLES[sid] = {"name": "harrow_" + cls, "type": cls, "palette": palette(paint=paint, paint2=paint),
                   "panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint", "cargo": "paint"}, "rail": "black", "equipment": eq}
for sid, cls, paint in (("SK165", "skid_steer", (236, 186, 30)), ("SF165", "forklift", (236, 140, 24))):
    STYLES[sid] = {"name": "solana_" + cls, "type": cls, "palette": palette(paint=paint, paint2=(40, 42, 46)),
                   "panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint", "cargo": "paint"}, "rail": "black", "equipment": []}
STYLES["SE820"] = {"name": "steward_digger", "type": "excavator", "palette": palette(paint=(236, 186, 30), paint2=(236, 186, 30)),
                   "panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint", "cargo": "black"}, "rail": "black",
                   "equipment": ["tracks", "excavator_house"]}

# ======================================================================== the remainder, part 5: rail (Steward rail boards, standard gauge)
def rail_windows():
    out = []
    k = 0
    for a, b in ((11.30, 7.75), (5.85, -5.85), (-7.75, -11.80)):
        y = a
        while y - 1.15 >= b - 1e-6:
            out.append({"id": "W%d" % k, "y0": round(y, 3), "y1": round(y - 1.15, 3)})
            y -= 1.35
            k += 1
    return out


H_RAIL = 1.70
PASSENGER_CAR = {
    "id": "PR250", "cls": "passenger_train", "board": "steward_rail32", "wheels_outside": True, "heavy": True,
    "about": "passenger cars on the Steward rail board: a cab at one end, two sliding doors a side, a standing-height saloon",
    "nose": 12.35, "tail": -12.35, "half_w": 1.48, "skirt": 1.00, "sill": 1.25, "floor": 1.25,
    "belt": belt_for(H_RAIL), "head": 3.00, "cant": 3.55, "crown": 3.90, "headliner": 3.78, "nose_round": 0.30, "tail_round": 0.10, "tail_taper": 0.02,
    "front": {"kind": "flat", "toe": 12.15, "header": 11.70, "screen_base": belt_for(H_RAIL) + 0.02, "hood_drop": 0.10},
    "rear": {"kind": "wall", "tail_in": -12.27, "back_window": {"half_w": 0.40, "z": (2.20, 2.90), "corner": 0.05}},
    "doors": [{"id": "D1", "y0": 7.55, "y1": 6.05, "kind": "slide"}, {"id": "D2", "y0": -6.05, "y1": -7.55, "kind": "slide"}],
    "windows": rail_windows(),
    "seats": [{"y": 11.35, "z": H_RAIL, "xs": [-0.70], "w": 0.55}] +
             [{"y": round(y, 3), "z": H_RAIL, "xs": [-1.0, -0.55, 0.55, 1.0], "w": 0.44, "bench": True}
              for y in [10.4, 9.5, 8.6] + [5.2 - 0.9 * k for k in range(12)] + [-8.6, -9.5, -10.4, -11.3]],
    "dash_y": 11.85, "head_lamp_z": 1.30, "tail_lamp_z": 1.40, "bumper_z": 1.05,
    "markers": [["pivot_lead", (0, 9.7, 0.5)], ["pivot_trail", (0, -9.7, 0.5)], ["exit_0", (1.9, 6.8, 0.0)], ["exit_1", (-1.9, -6.8, 0.0)]],
}
LOCOMOTIVE = heavy("RL280", "freight_locomotive", {"kind": "box", "y0": 6.20, "y1": -8.40, "half_w": 1.10, "floor_z": 1.30, "top_z": 3.70, "rear": "closed",
                                                   "doors": [{"id": "C1", "y0": 4.0, "y1": 2.8}, {"id": "C2", "y0": -2.0, "y1": -3.2}]},
                   "freight locomotives: a cab and a long hood on the Steward rail board")
LOCOMOTIVE.update({"board": "steward_rail22", "wheels_outside": True, "nose": 8.40, "tail": 6.25, "half_w": 1.48, "skirt": 1.00, "sill": 1.32, "floor": 1.30,
                   "high_floor": False, "front": {"kind": "flat", "toe": 8.28, "header": 7.85, "screen_base": belt_for(H_TRUCK) + 0.02, "hood_drop": 0.10},
                   "rear": {"kind": "wall", "tail_in": 6.31, "back_window": {"half_w": 0.40, "z": (2.20, 2.55), "corner": 0.05}},
                   "doors": [{"id": "F", "y0": 7.70, "y1": 6.95}], "seats": [{"y": 7.25, "z": H_TRUCK, "xs": [-0.62, 0.62], "w": 0.55}], "dash_y": 7.95,
                   "markers": [["pivot_lead", (0, 6.0, 0.5)], ["pivot_trail", (0, -6.0, 0.5)]]})
LOCOMOTIVE["cargo"]["y0"] = 6.25
FREIGHT = [
    trailer("RB220", "boxcar", "steward_rail22", {"kind": "box", "y0": 8.45, "y1": -8.45, "half_w": 1.50, "floor_z": 1.25, "top_z": 4.30, "rear": "closed",
                                                  "doors": [{"id": "S", "y0": 1.0, "y1": -1.0}]}, "boxcars: a box with a sliding door a side"),
    trailer("RH220", "covered_hopper", "steward_rail22", {"kind": "box", "y0": 8.45, "y1": -8.45, "half_w": 1.55, "floor_z": 1.25, "top_z": 4.20, "rear": "closed"},
            "covered hoppers: a closed body, roof hatches, chutes under"),
    trailer("RT220", "tank_car", "steward_rail22", {"kind": "tank", "y0": 8.45, "y1": -8.45, "half_w": 1.45, "floor_z": 1.25, "tank_r": 1.40, "tank_z": 2.75},
            "tank cars: a tank on the rail board"),
    trailer("RF220", "flatcar", "steward_rail22", {"kind": "deck", "y0": 8.45, "y1": -8.45, "half_w": 1.50, "floor_z": 1.25, "rail_z": 1.25, "rear": "none"},
            "flatcars: a flat deck with stake pockets"),
    trailer("RR220", "reefer_car", "steward_rail22", {"kind": "box", "y0": 8.45, "y1": -8.45, "half_w": 1.50, "floor_z": 1.25, "top_z": 4.30, "rear": "closed",
                                                      "doors": [{"id": "S", "y0": 0.9, "y1": -0.9}]}, "refrigerated boxcars: an insulated box, a reefer unit"),
]
for t in FREIGHT:
    t["markers"] = [["pivot_lead", (0, 6.0, 0.5)], ["pivot_trail", (0, -6.0, 0.5)]]
KIDDIE = light("KT100", "kiddie_train", "solana_m16",
               {"kind": "bed", "y0": 1.22, "y1": -1.22, "half_w": 0.55, "floor_z": 0.42, "rail_z": 0.70, "rear": "closed", "skirt": 0.28},
               {"seats": [{"y": -0.40, "z": 0.72, "xs": [0.0], "w": 0.44}], "controls": "wheel", "driver": "C", "cowl": {"y0": 1.10, "y1": 0.10, "z1": 1.10},
                "canopy": {"y0": 0.05, "y1": -1.10, "z": 1.75}, "extras": ["smokestack"]},
               "kiddie trains: a little locomotive on a micro board")
CLASSES.update({c["id"]: c for c in [PASSENGER_CAR, LOCOMOTIVE, KIDDIE] + FREIGHT})
STYLES["PR250"] = {"name": "steward_coach", "type": "passenger_train", "palette": palette(paint=(210, 212, 216), paint2=(150, 152, 156), livery2=(40, 92, 150)),
                   "panel": {"lower": "paint", "upper": "black", "roof": "paint2", "sail": "black"}, "head_lamp": "round", "grille": None,
                   "tail_lamp": "pixel", "bumper": "black", "mirror": "black", "handle": "black", "livery": {"m": "livery2", "z": (1.60, 1.90)},
                   "equipment": ["dest_sign_front"], "blank_windows": []}
STYLES["RL280"] = {"name": "steward_hauler", "type": "freight_locomotive", "palette": palette(paint=(190, 40, 30), paint2=(40, 42, 46)),
                   "panel": dict(TRUCK_PANEL, cargo="paint"), "head_lamp": "round", "grille": "slots", "tail_lamp": "pixel", "bumper": "black",
                   "mirror": "black", "handle": "black", "rail": "black", "equipment": []}
for sid, cls, paint, eq in (("RB220", "boxcar", (150, 60, 40), []), ("RH220", "covered_hopper", (150, 152, 156), ["roof_hatches_car"]),
                            ("RT220", "tank_car", (40, 42, 46), []), ("RF220", "flatcar", (90, 70, 50), ["stake_pockets"]),
                            ("RR220", "reefer_car", (236, 234, 228), ["reefer_unit"])):
    STYLES[sid] = {"name": "steward_" + cls, "type": cls, "palette": palette(paint=paint, paint2=paint),
                   "panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint", "cargo": "paint"}, "rail": "black", "equipment": eq}
STYLES["KT100"] = {"name": "solana_kiddie", "type": "kiddie_train", "palette": palette(paint=(190, 40, 30), paint2=(40, 92, 150)),
                   "panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint", "cargo": "paint"}, "rail": "black", "equipment": []}

EXCAVATOR["machine"] = True

# ======================================================================== the aerostats (2026-10-04)
# The Steward's gift (VY 405): an envelope, ducted fans, and a gondola built as any fleet body -- both shells, the tube
# frame, reveals, doors -- on a Steward keel (spans and landing skids, no wheels). The envelope, fins, fans, struts, a
# cargo sling are equipment tokens (fleet/aero.py). Interiors keep the 2.2 m floor-to-headliner rule.
# research/vehicles/aerostat/AEROSTATS.md; references reference/grok/{rescue,cargo}_aerostat.
AERO_GONDOLA = {
    "skirt": 0.40, "sill": 0.58, "floor": 0.55, "belt": 1.30, "head": 2.40, "cant": 2.78, "crown": 2.92, "headliner": 2.82,
    "nose_round": 0.85, "tail_round": 0.70, "cant_in": 0.12, "tumble": 0.10, "tuck": 0.24, "pillar_inset": 0.03, "pillar": 0.13, "wheels_outside": True,
    "head_lamp_z": 0.95, "tail_lamp_z": 1.10, "bumper_z": 0.50, "driver": "L",
}
RESCUE_AERO = dict(AERO_GONDOLA, **{
    "id": "AR700", "cls": "rescue_aerostat", "board": "steward_keel8",
    "about": "rescue aerostats: a 16 m envelope, four ducted fans, a glazed 6.9 m gondola (stretcher, crew of four) on a Steward keel",
    "nose": 3.45, "tail": -3.45, "half_w": 1.20,
    "front": {"kind": "flat", "toe": 3.20, "header": 2.70, "screen_base": 1.32, "hood_drop": 0.10},
    "rear": {"kind": "wall", "tail_in": -3.38, "back_window": {"half_w": 0.45, "z": (1.55, 2.20), "corner": 0.06}},
    "doors": [{"id": "F", "y0": 2.55, "y1": 1.80}, {"id": "S", "y0": 0.85, "y1": -0.65, "sides": "R", "kind": "slide"}],
    "windows": [{"id": "W0", "y0": 1.70, "y1": 0.95}, {"id": "W1", "y0": 0.85, "y1": -0.65, "sides": "L"}, {"id": "W2", "y0": -0.75, "y1": -2.55}],
    "seats": [{"y": 2.15, "z": 0.95, "xs": [-0.50, 0.50], "w": 0.55}, {"y": -2.05, "z": 0.95, "xs": [-0.62, 0.62], "w": 0.50}],
    "dash_y": 2.85,
    "aero": {"env": (16.0, 2.5, -1.2, 6.32), "stripes": [(40, 3.5), (0, 4.5), (-42, 3.5)],
             "fins": (0.05, 0.22, 1.5, 0.55, 0.5), "fin_band": (0.55, 0.75), "stabiliser_rods": True,
             "fans": [(1.55, -1.6, 3.55, 0.55, "env"), (2.55, -3.9, 2.20, 0.50, "boom")],
             "struts": [(0.85, 2.0), (0.85, -2.6)], "mast": -0.9, "cross": (-3.0, 0.95, 0.28), "foot_lamps": 5},
})
CARGO_AERO = dict(AERO_GONDOLA, **{
    "id": "AC820", "cls": "cargo_aerostat", "board": "steward_keel10",
    "about": "heavy-lift aerostats: a 34 m envelope, four big ducted fans, a crew gondola slung tight under it, a sling frame on A-legs",
    "nose": 4.10, "tail": -4.10, "half_w": 1.20,
    "front": {"kind": "flat", "toe": 3.85, "header": 3.35, "screen_base": 1.32, "hood_drop": 0.10},
    "rear": {"kind": "wall", "tail_in": -4.03, "back_window": {"half_w": 0.45, "z": (1.55, 2.20), "corner": 0.06}},
    "doors": [{"id": "F", "y0": 3.15, "y1": 2.40}],
    "windows": [{"id": "W1", "y0": 2.30, "y1": 0.30}, {"id": "W2", "y0": 0.20, "y1": -1.80}, {"id": "W3", "y0": -1.90, "y1": -3.40}],
    "seats": [{"y": 2.75, "z": 0.95, "xs": [-0.50, 0.50], "w": 0.55}, {"y": -2.6, "z": 0.95, "xs": [-0.62, 0.62], "w": 0.50}],
    "dash_y": 3.50,
    "aero": {"env": (34.0, 4.7, -1.0, 7.87), "stripes": [(32, 2.5), (-36, 2.5)], "bands": [(0.24, 0.29), (0.66, 0.71)], "cap": 0.93,
             "fins": (0.04, 0.21, 3.6, 0.55, 1.2), "fin_band": (0.0, 0.14),
             "fans": [(5.68, 6.5, 5.27, 1.30, "env"), (5.68, -9.0, 5.27, 1.30, "env")], "fan_len": 1.9,
             "saddle": True, "sling": (4.2, 6.5, -8.5, -2.6), "legs": [4.0, -6.0]},
})
CLASSES.update({c["id"]: c for c in (RESCUE_AERO, CARGO_AERO)})
AERO_PANEL = {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint"}
STYLES["AR700"] = {"name": "steward_mercy", "type": "rescue_aerostat",
                   "palette": palette(paint=(232, 222, 196), paint2=(232, 222, 196), livery1=(240, 240, 236), livery2=(200, 36, 32)),
                   "panel": AERO_PANEL, "head_lamp": "round", "grille": None, "tail_lamp": "pixel", "bumper": "none", "mirror": "none",
                   "handle": "chrome", "belt_trim": "chrome", "rail": "black",
                   "equipment": ["envelope", "fins", "ducted_fans", "suspension", "winch", "rescue_cross", "aero_lamps"]}
STYLES["AC820"] = {"name": "steward_burden", "type": "cargo_aerostat",
                   "palette": palette(paint=(232, 222, 196), paint2=(78, 150, 140), livery1=(232, 224, 204), livery2=(78, 150, 140)),
                   "panel": AERO_PANEL, "head_lamp": "round", "grille": None, "tail_lamp": "pixel", "bumper": "none", "mirror": "none",
                   "handle": "chrome", "belt_trim": "chrome", "rail": "black", "livery": {"m": "livery2", "z": (0.62, 0.80)},
                   "equipment": ["envelope", "fins", "ducted_fans", "suspension", "sling", "boarding_ladder", "aero_lamps"]}

# ======================================================================== the spacecraft and the spoke elevator (2026-10-04)
# Bodies to the same rules (both shells, the frame, reveals, 2.2 m inside) on Steward keels; what makes each a spacecraft
# is equipment (fleet/space.py). References: reference/grok/{passenger_shuttle,supply_freighter,cargo_mule,spoke_elevator_car}.
SPACE_BODY = {"skirt": 0.45, "sill": 0.58, "floor": 0.55, "pillar_inset": 0.03, "pillar": 0.13, "wheels_outside": True,
              "head_lamp_z": 0.95, "tail_lamp_z": 1.10, "bumper_z": 0.50, "driver": "L"}
SHUTTLE = dict(SPACE_BODY, **{
    "id": "SP300", "cls": "passenger_shuttle", "board": "steward_keel36",
    "about": "passenger shuttles (the port to orbit): a 29 m lifting body, a delta wing, 48 seats behind a two-seat flight deck",
    "nose": 14.6, "tail": -14.6, "half_w": 2.10, "belt": 1.55, "head": 2.05, "cant": 2.75, "crown": 3.20, "headliner": 2.92,
    "tuck": 0.50, "cant_in": 0.45, "tumble": 0.15, "nose_round": 2.6, "nose_taper": 0.55, "tail_round": 1.0, "tail_taper": 0.10,
    "front": {"kind": "hood", "toe": 11.8, "header": 11.0, "screen_base": 1.80, "hood_drop": 0.95},
    "rear": {"kind": "wall", "tail_in": -14.52, "back_window": {"half_w": 0.30, "z": (2.30, 2.55), "corner": 0.05}},
    "doors": [{"id": "F", "y0": 10.9, "y1": 10.2}, {"id": "P", "y0": 9.7, "y1": 8.75}],
    "windows": [{"id": "P%02d" % k, "y0": round(8.25 - k * 1.05, 3), "y1": round(8.25 - k * 1.05 - 0.50, 3)} for k in range(15)],
    "seats": [{"y": 11.2, "z": 0.95, "xs": [-0.55, 0.55], "w": 0.55}] +
             [{"y": round(7.9 - k * 0.95, 3), "z": 0.95, "xs": [-1.45, -0.85, 0.85, 1.45], "w": 0.50} for k in range(12)],
    "dash_y": 11.6,
    "render": (-15.5, 8.2),
    "space": {"wing": (2.0, -12.5, 9.0, 0.95), "fin": (-9.5, -14.0, 5.0), "gear": [(0.0, 10.0, 1), (2.4, -6.0, 2)]},
})
FREIGHTER = dict(SPACE_BODY, **{
    "id": "SF600", "cls": "supply_freighter", "board": "steward_keel8",
    "about": "supply freighters: a rounded cockpit, six bays of stacked cargo pods on a spine, the drive section and its bells",
    "nose": 3.40, "tail": -3.40, "half_w": 1.50, "belt": 1.35, "head": 2.25, "cant": 2.70, "crown": 2.95, "headliner": 2.82,
    "tuck": 0.25, "cant_in": 0.20, "tumble": 0.08, "nose_round": 0.9, "tail_round": 0.4,
    "front": {"kind": "flat", "toe": 3.10, "header": 2.70, "screen_base": 1.37, "hood_drop": 0.10},
    "rear": {"kind": "wall", "tail_in": -3.33, "back_window": {"half_w": 0.40, "z": (1.60, 2.20), "corner": 0.05}},
    "doors": [{"id": "F", "y0": 1.60, "y1": 0.80}],
    "windows": [{"id": "W1", "y0": 0.60, "y1": -1.00}, {"id": "W2", "y0": -1.10, "y1": -2.60}],
    "seats": [{"y": 2.20, "z": 0.95, "xs": [-0.55, 0.55], "w": 0.55}, {"y": -1.80, "z": 0.95, "xs": [-0.70, 0.70], "w": 0.50}],
    "dash_y": 2.95,
    "render": (-30.0, 6.0),
    "space": {"pods": (-3.75, 6, (2, 3), (2.2, 1.6, 3.2)), "pod_z": 3.0, "drive": (-23.9, 6.0, 2.6, 2.8, 3.0)},
})
MULE = dict(SPACE_BODY, **{
    "id": "SM450", "cls": "cargo_mule", "board": "steward_keel8",
    "about": "cargo mules: a stubby tug, a glazed flight deck, thruster pods, two manipulator arms for the port's handling",
    "nose": 3.30, "tail": -3.30, "half_w": 1.25, "belt": 1.50, "head": 2.30, "cant": 2.60, "crown": 2.85, "headliner": 2.78,
    "tuck": 0.15, "cant_in": 0.15, "tumble": 0.06, "nose_round": 0.9, "tail_round": 0.4,
    "front": {"kind": "hood", "toe": 2.00, "header": 1.50, "screen_base": 1.55, "hood_drop": 0.25},
    "rear": {"kind": "wall", "tail_in": -3.23, "back_window": {"half_w": 0.40, "z": (1.70, 2.20), "corner": 0.05}},
    "doors": [{"id": "F", "y0": 1.20, "y1": 0.40, "sides": "L"}],
    "windows": [{"id": "W1", "y0": 0.30, "y1": -1.20, "sides": "L"}, {"id": "W2", "y0": -1.40, "y1": -2.60}],
    "seats": [{"y": 0.90, "z": 0.95, "xs": [-0.45, 0.45], "w": 0.55}],
    "dash_y": 1.75,
    "space": {"thrusters": [(1.35, 2.20, 0.45, 2.6), (1.35, 0.85, 0.40, 2.4)],
              "arms": [((0.2, 1.9), (1.4, 2.4), (2.6, 1.5)), ((0.0, 1.2), (1.4, 0.8), (2.5, 0.95))],
              "lamps": [(0.55, 1.0, 0.13, "lamp_head"), (0.0, 1.15, 0.18, "lamp_head"), (0.32, 0.75, 0.08, "lamp_amber")]},
})
ELEVATOR = dict(SPACE_BODY, **{
    "id": "EE600", "cls": "spoke_elevator_car", "board": "steward_keel7",
    "about": "spoke elevator cars (the floor to the axis): a round cabin 5.8 m across, benches round it, standing room for thirty",
    "nose": 2.90, "tail": -2.90, "half_w": 2.90, "plan": "round", "round_min": 0.42, "skirt": 0.40,
    "belt": 1.30, "head": 2.30, "cant": 2.70, "crown": 3.10, "headliner": 2.85, "cant_in": 0.30, "tumble": 0.0,
    "front": {"kind": "flat", "toe": 2.80, "header": 2.62, "screen_base": 1.32, "hood_drop": 0.05},
    "rear": {"kind": "wall", "tail_in": -2.84, "back_window": {"half_w": 0.70, "z": (1.40, 2.20), "corner": 0.08}},
    "doors": [{"id": "D", "y0": 0.80, "y1": -0.80, "sides": "R", "kind": "slide"}],
    "windows": [{"id": "W1", "y0": 2.20, "y1": 1.00}, {"id": "W2", "y0": -1.00, "y1": -2.20}, {"id": "W3", "y0": 0.80, "y1": -0.80, "sides": "L"}],
    "seats": [{"y": 1.75, "z": 0.95, "xs": [-1.6, -1.0, 1.0, 1.6], "w": 0.50, "bench": True},
              {"y": -1.75, "z": 0.95, "xs": [-1.6, -1.0, 1.0, 1.6], "w": 0.50, "bench": True}],
    "dash_y": 2.60, "space": {},
})
CLASSES.update({c["id"]: c for c in (SHUTTLE, FREIGHTER, MULE, ELEVATOR)})
SPACE_STYLE = {"panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint"}, "head_lamp": "round", "grille": None,
               "tail_lamp": "pixel", "bumper": "none", "mirror": "none", "handle": "chrome", "belt_trim": "chrome", "rail": "black"}
STYLES["SP300"] = dict(SPACE_STYLE, name="steward_skylark", type="passenger_shuttle",
                       palette=palette(paint=(236, 232, 214), paint2=(236, 232, 214), livery2=(24, 110, 110)),
                       livery={"m": "livery2", "z": (1.40, 2.20)}, equipment=["wings", "tail_fin", "oms_pods", "main_engines", "landing_gear"])
STYLES["SF600"] = dict(SPACE_STYLE, name="steward_packhorse", type="supply_freighter",
                       palette=palette(paint=(170, 172, 176), paint2=(226, 220, 196), livery2=(226, 220, 196)),
                       panel={"lower": "paint2", "upper": "paint2", "roof": "paint2", "sail": "paint2"}, equipment=["cargo_pods", "drive_section"])
STYLES["SM450"] = dict(SPACE_STYLE, name="steward_mule", type="cargo_mule",
                       palette=palette(paint=(240, 236, 226), paint2=(240, 236, 226), livery2=(226, 110, 30)),
                       livery={"m": "livery2", "z": (0.75, 0.90)}, equipment=["thruster_pods", "manipulators", "dorsal", "nose_lamps", "beacon"])
STYLES["EE600"] = dict(SPACE_STYLE, name="steward_ascender", type="spoke_elevator_car",
                       palette=palette(paint=(236, 226, 200), paint2=(236, 226, 200)), equipment=["guide_rollers", "rim_lamps"])

# ======================================================================== the city car and the minivan (2026-10-04)
# The last of the road fleet: the pod and the minibus that were hand-built (remake/blender/vehicles/groundcar.py),
# now modular bodies to the same rules, keeping their looks: the pod's white shell, blue band and sliding doors, the
# minibus's mustard and woodgrain, white roof, quad lamps.
CITY_POD = {
    "id": "CP200", "cls": "city_car", "board": "solana_l25",
    "about": "city cars (pods) on the Solana Light L-25: 1.90 m wide, 3.98 m long, 2.35 m tall, four seats, sliding doors both sides",
    "nose": 2.00, "tail": -1.98, "half_w": 0.95, "skirt": 0.30, "sill": 0.58, "floor": 0.55,
    "belt": belt_for(), "head": 2.06, "cant": 2.24, "crown": 2.35, "headliner": 2.29, "nose_round": 0.35, "tail_round": 0.30, "cant_in": 0.06,
    "front": {"kind": "flat", "toe": 1.80, "header": 1.10, "screen_base": belt_for() + 0.02, "hood_drop": 0.12},
    "rear": {"kind": "wall", "tail_in": -1.90, "back_window": {"half_w": 0.62, "z": (1.40, 2.00), "corner": 0.06}},
    "doors": [{"id": "S", "y0": 0.50, "y1": -0.75, "kind": "slide"}],
    "windows": [{"id": "WF", "y0": 1.00, "y1": 0.60}, {"id": "W2", "y0": -0.85, "y1": -1.62}],
    "seats": [{"y": 0.80, "z": 0.85, "xs": [-0.40, 0.40], "w": 0.50}, {"y": -1.20, "z": 0.87, "xs": [-0.38, 0.38], "w": 0.48, "bench": True}],
    "dash_y": 1.55, "head_lamp_z": 0.78, "tail_lamp_z": 1.02, "bumper_z": 0.46,
}
MINIBUS = {
    "id": "MV260", "cls": "minivan", "board": "carrow_k36",
    "about": "minivans (the 1970s minibus) on the Carrow Keel K-36: 2.00 m wide, 5.22 m long, 2.42 m tall, three rows",
    "nose": 2.62, "tail": -2.60, "half_w": 1.00, "skirt": 0.32, "sill": 0.58, "floor": 0.55,
    "belt": belt_for(H_VAN), "head": 2.12, "cant": 2.32, "crown": 2.42, "headliner": 2.36, "nose_round": 0.25, "cant_in": 0.06,
    "front": {"kind": "flat", "toe": 2.40, "header": 2.05, "screen_base": belt_for(H_VAN) + 0.02, "hood_drop": 0.10},
    "rear": {"kind": "wall", "tail_in": -2.53, "back_window": {"half_w": 0.70, "z": (1.45, 2.10), "corner": 0.06}},
    "doors": [{"id": "F", "y0": 1.30, "y1": 0.55}, {"id": "S", "y0": 0.45, "y1": -0.60, "sides": "R", "kind": "slide"}],
    "windows": [{"id": "WF", "y0": 2.00, "y1": 1.40}, {"id": "W1", "y0": 0.45, "y1": -0.60, "sides": "L"}, {"id": "W2", "y0": -0.70, "y1": -1.35},
                {"id": "W3", "y0": -1.45, "y1": -2.35}],
    "seats": [{"y": 0.95, "z": H_VAN, "xs": [-0.48, 0.48], "w": 0.52},
              {"y": -0.45, "z": H_VAN, "xs": [-0.52, 0.0, 0.52], "w": 0.48, "bench": True},
              {"y": -1.65, "z": H_VAN, "xs": [-0.52, 0.0, 0.52], "w": 0.48, "bench": True}],
    "dash_y": 1.75, "head_lamp_z": 0.90, "tail_lamp_z": 1.05, "bumper_z": 0.48,
}
CLASSES.update({c["id"]: c for c in (CITY_POD, MINIBUS)})
STYLES["CP200"] = {"name": "solana_hopper", "type": "city_car", "palette": palette(paint=(240, 240, 236), paint2=(240, 240, 236), livery2=(60, 100, 170)),
                   "panel": {"lower": "paint", "upper": "paint", "roof": "paint2", "sail": "paint"}, "head_lamp": "rect", "grille": None,
                   "tail_lamp": "pixel", "bumper": "black", "mirror": "black", "handle": "black", "livery": {"m": "livery2", "z": (0.80, 0.94)}}
STYLES["MV260"] = {"name": "carrow_jamboree", "type": "minivan", "palette": palette(paint=(196, 154, 58), paint2=(240, 236, 226)),
                   "panel": {"lower": "paint", "upper": "paint2", "roof": "paint2", "sail": "paint2"}, "head_lamp": "round", "grille": "band",
                   "tail_lamp": "pixel", "bumper": "chrome", "mirror": "chrome", "handle": "chrome", "belt_trim": "chrome",
                   "inlay": {"m": "wood", "frame": "chrome", "z": (0.62, None)}}
