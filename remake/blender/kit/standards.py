"""
standards.py -- the vehicle class standards: the dimensions every body component of a class is built to,
so that components mix and match within a class whatever their maker's style (the user, 2026-10-01:
"A tram door will not fit on a hatchback, but it will fit on another tram with a different art style").

A standard fixes, for its class:
  - the frame: the cross-section profile of the structural rings (the nodes every panel hangs on) and how
    rings are spaced (one at every slot boundary);
  - the slots: the named openings along the sides, the roof, the ends and the floor, with their sizes --
    a component declares the slot it fills, and fits any vehicle of the class with that slot;
  - the fixed heights: floor, belt, window band, cant rail, the door aperture, the portal.
Style (colours, mouldings, lamp shapes, seat design) is the maker's: free, as long as the component stays
inside its slot's envelope and fastens at the slot's mount nodes.

Coordinates: Blender's (X right, Y forward, Z up), metres; z = 0 the ground, y = 0 midway between a
section's axles. The game turns them into Godot's (x, z, -y).

Read by the Blender builders (remake/blender/...) and written to JSON for the game
(godot_project/remake/vehicles/standards/<id>.json) by write_json().
"""
import json
import os

ROAD_TRAM = {
    "id": "RT255",
    "class": "road_tram",
    "about": "articulated road tram sections on the Steward tram board (2.55 m wide, 8.4 m between portals)",
    "board": "steward_tram",
    # fixed heights and widths (m)
    "outer_half_width": 1.275,
    "inner_half_width": 1.215,
    "deck": 0.50,
    "floor": 0.55,
    "ceiling": 2.80,
    "skirt": 0.30,
    "belt": 1.05,
    "window": [1.15, 2.30],
    "cant": 2.62,
    "crown": 3.02,
    "half_length": 4.2,
    "nose_reach": 0.66,
    "portal": {"half_width": 0.64, "head": 2.62},
    "door": {"width": 1.24, "head": 2.55},
    "axles": [2.25, -2.25],
    "arch_half": 0.62,
    # the frame: a welded tube space frame (the makers' cottage craft, after the British tube-frame builders),
    # bolted to the board at its sills and floor. Each ring's joints (x, z) -- the tubes' centrelines, inside
    # the wall between the exterior skin and the interior lining -- right side up, over the roof, down the left,
    # and the floor's middle
    "ring": [
        ["skirt_R", 1.245, 0.36], ["sill_R", 1.245, 0.515], ["belt_R", 1.245, 1.05], ["head_R", 1.24, 2.38],
        ["cant_R", 1.16, 2.70], ["roof_R", 0.88, 2.875], ["crown", 0.0, 2.95], ["roof_L", -0.88, 2.875],
        ["cant_L", -1.16, 2.70], ["head_L", -1.24, 2.38], ["belt_L", -1.245, 1.05], ["sill_L", -1.245, 0.515],
        ["skirt_L", -1.245, 0.36], ["floor_C", 0.0, 0.515],
    ],
    # the shells the tubes sit between (the joints above are inside the cavity with a margin for the tubes)
    "exterior": {"skin_x": 1.275, "shoulder": [[2.30, 1.275], [2.48, 1.263], [2.62, 1.225]], "sill_pan_x": 1.10},
    "interior": {"lining_x": 1.215, "cove": {"from_z": 2.30, "rx": 0.40, "rz": 0.50}, "ceiling": 2.80, "end_gap": 0.06},
    "end_inset": 0.03,                                 # the end hoops stand this far in, inside the end cavity
    "tubes": {"main_d": 0.030, "brace_d": 0.024, "material": "frame_tube",
              "exposed_inside": [], "exposed_outside": []},          # (a style may show tubes on purpose: list the members)
    # the ring's members (closed: each node to the next) and which nodes the chassis holds (bolted to the board)
    "bolted": ["sill_R", "sill_L", "floor_C"],
    # longitudinal members between rings, by node; "belt" is broken across a door aperture
    "stringers": ["skirt_R", "sill_R", "belt_R", "head_R", "cant_R", "roof_R", "crown", "roof_L", "cant_L", "head_L", "belt_L", "sill_L", "skirt_L", "floor_C"],
    # the slots along each side (m, along y): a section's side is a run of these, ends to ends
    "side_slots": {"end": 0.13, "door": 1.24, "bay_short": 2.21, "bay_long": 3.58},
    "roof_slot": 1.40,
    # the frame's steel: how much a member takes before it bends for good, and how far it can bend
    # the frame's steel: how much a member takes before it bends for good, and how a blow dents it -- the
    # energy (J) a metre of dent takes (a 1.5 t car at 30 km/h, half its closing energy absorbed: ~13 cm),
    # the least that dents at all, the deepest dent
    "frame": {"yield_strain": 0.012, "plastic": 0.85, "dent_stiffness": 200000.0, "min_energy": 4000.0, "max_dent": 0.45},
    # a panel comes off when this many of its fastenings (pairs of nearby mount joints) are torn past its
    # tolerance -- or this share of them, if fewer (a dent tears a patch of a big panel); glass at the first
    "detach_count": 3,
    "detach_share": 0.3,
    # how much strain at its mounts each role takes before it comes off (or breaks)
    "tolerance": {"glazing": 0.012, "door_glass": 0.012, "door_leaf": 0.05, "side_bay": 0.03, "door_head": 0.03,
                  "roof_bay": 0.03, "roof_fairing": 0.03, "lining_bay": 0.045, "door_head_lining": 0.045, "ceiling_bay": 0.05,
                  "end_lining": 0.045, "cap_lining": 0.045, "wheel_well": 0.10, "reveal": 0.04, "end_portal": 0.035,
                  "end_cap": 0.035, "seat": 0.15, "stanchion": 0.10, "fittings": 0.10, "podium": 0.20, "floor": 1.0,
                  "cab": 0.12, "ramp": 0.08},
}

STANDARDS = {s["id"]: s for s in (ROAD_TRAM,)}


def write_json(std, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, std["id"] + ".json"), "w") as f:
        json.dump(std, f, indent=1)
