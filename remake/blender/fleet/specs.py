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
    "lamp_red": ((200, 20, 20), 0.3, 0.0, (255, 30, 30), 0.0, 1), "lamp_blue": ((20, 60, 220), 0.3, 0.0, (40, 90, 255), 0.0, 1),
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

CLASSES = {"SD180": SEDAN}

# ---------------------------------------------------------------- the base styles (one per class) and the types
STYLES = {
    "SD180": {"name": "carrow_saloon", "type": "sedan", "phys": "sedan",
              "palette": palette(paint=(64, 98, 120), paint2=(64, 98, 120)),
              "panel": {"lower": "paint", "upper": "black", "roof": "paint2", "sail": "black"},
              "head_lamp": "quad", "grille": "slots", "tail_lamp": "bar", "belt_trim": "chrome", "bumper": "chrome",
              "mirror": "chrome", "handle": "chrome"},
}

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
}
