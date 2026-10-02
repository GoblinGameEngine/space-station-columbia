"""
sw180.py -- the SW180 station wagon class: its body loft (the two shells' surfaces), its frame rings and its
slots. Pure Python (no Blender), shared by kit/standards.py (the standard the game reads) and the wagon
builders (remake/blender/wagon/...). research/vehicles/wagon/WAGON.md has the why; research/vehicles/
MODULAR_VEHICLES.md the rules.

THE LOFT GRID (the method that makes a car body sealed by construction):
  - Each shell is a loft: a list of stations along the car (y, Blender: + forward), and at each station a loop
    of points round the body with the SAME count everywhere (the profile's breakpoints are fixed indices).
  - The grid's cells are (station interval i, loop interval s). Every panel is a set of whole cells; every
    opening (door, window, arch, lid) is a rectangle of cells; so neighbours share vertices exactly and the
    seal can't open. The builder asserts every cell belongs to exactly one component.
  - The interior loop has the same breakpoints as the exterior (offset by INT_OFF) plus the floor and the
    wheel-housing humps: exterior index k on the right is interior k + 3 (see ext_s / int_s).
  - A reveal joins the same rectangle's boundary on the two shells: equal vertex counts by construction.
  - The ends are flat caps (nose, tail; the interior's firewall and tail wall), triangulated from the end
    loop, so they share its vertices too.
The class fixes the loft; a maker's style (Carrow, ...) is materials, trim, lamps, fittings and how cells are
split into components inside a slot -- so an SW180 door from any maker fits any SW180 wagon.

Coordinates: Blender (X right, Y forward, Z up), metres; z = 0 the ground, y = 0 midway between the axles of the
Carrow Keel K-28 board (wheelbase 2.8, axles y = +-1.4, wheel r 0.32, deck top 0.50).
"""
import math

# ---------------------------------------------------------------- fixed heights and widths
SKIRT = 0.30          # the body's lower edge
SILL = 0.58           # the rocker top: the door apertures' bottom
ARCH_TOP = 0.85       # the wheel arches' top
BELT = 1.05           # the shoulder crease: two-tone break, the side glass's foot
HEAD = 1.90           # the side glass's head: the door apertures' top
CANT = 1.99           # the roof's edge
CROWN = 2.055         # the roof's top (the car is 2.06 m tall)
FLOOR = 0.55          # the cabin floor (deck 0.50 + 0.05)
HEADLINER = 2.00      # the cabin ceiling at the middle
WO = 0.93             # outer half width at the shoulder (1.86 m)
INT_OFF = 0.06        # the cavity between the shells (the frame's tubes are in it)
AXLES = (1.40, -1.40)
ARCH_HALF = 0.42      # half the arch's length (wheel r 0.32 + 0.10)
WELL_X = 0.45         # the wheel well's inner wall (clear of the board's wheel pod, x 0.48..1.08)
HUMP_Z = 0.90         # the wheel housing's top inside the cabin
TOE = 1.15            # the cowl / firewall: the windscreen's foot
PILLAR = 0.09         # the A-pillar's height across (its tube runs inside it, behind the windscreen's reveal)
HEADER = 0.38         # the windscreen's head
LID = (2.16, 1.20)    # the frunk lid: front edge, hinge line
NOSE = 2.28           # the nose cap
TAIL = -2.36          # the tail cap (the hatch is in it)
TAIL_IN = -2.30       # the interior's tail wall
DOORS = {"front": (0.92, 0.0), "rear": (-0.12, -0.92)}   # apertures (y front, y back), sill to head
QUARTER = (-1.00, -2.08)                                    # the rear quarter window
HATCH = {"half_w": 0.74, "z": (0.62, 1.94), "corner": 0.10, "glass": {"half_w": 0.64, "z": (1.10, 1.86), "corner": 0.07}}

# ---------------------------------------------------------------- stations (every edge of every slot; descending y)
ARCH_R = 0.50                       # the arches are round: radius about a centre 0.35 up over the axle
ARCH_ZC = ARCH_TOP - ARCH_R
_ARC = [0.42, 0.36, 0.27, 0.15, 0.0, -0.15, -0.27, -0.36]
STATIONS = sorted({round(v, 4) for v in [NOSE, 2.26, 2.22, LID[0], 2.10, LID[1], TOE, 0.979, DOORS["front"][0], 0.414, HEADER,
                                         DOORS["front"][1], DOORS["rear"][0], DOORS["rear"][1], -0.981, QUARTER[0], -1.821,
                                         QUARTER[1], -2.20, -2.26, TAIL_IN, TAIL]
                   + [ax + d for ax in AXLES for d in _ARC + [-0.42]]}, reverse=True)
INT_STATIONS = [y for y in STATIONS if TAIL_IN <= y <= TOE]

# ---------------------------------------------------------------- the profile: exterior half loop, right side
# index: 0 skirt, 1 sill, 2 arch, 3 belt, 4, 5, 6 head, 7, 8 cant, 9, 10 roof, 11, 12 crown
E = {"skirt": 0, "sill": 1, "arch": 2, "belt": 3, "head": 6, "cant": 8, "roof": 10, "crown": 12}
NE = 13               # points per half; the full exterior loop is 25 (0..12 right, 13..24 left, 24 - k)
NI = 30               # the interior loop (closed): 0 floor middle, 1..3 right hump, 4..15 right E1..crown, 16..26 left, 27..29 left hump


def arch_z(y):
    """The arch's edge height at y (round, about the axle); ARCH_TOP away from the arches."""
    for ax in AXLES:
        d = abs(y - ax)
        if d <= ARCH_HALF + 1e-6:
            return ARCH_ZC + math.sqrt(max(0.0, ARCH_R * ARCH_R - d * d))
    return ARCH_TOP


def side_x(z):
    """The cabin side's half width at height z (tumblehome above the belt)."""
    if z <= BELT:
        return WO if z >= SILL else WO - 0.03 * (SILL - z) / (SILL - SKIRT)
    if z <= HEAD:
        return WO - 0.06 * (z - BELT) / (HEAD - BELT)
    return WO - 0.06 - 0.07 * (z - HEAD) / (CANT - HEAD)


def a_line(y):
    """The windscreen's side edge height (the A-pillar's line) at y, from the cowl to the header."""
    return 1.07 + (TOE - y) / (TOE - HEADER) * (CANT - 1.07)


def hood_z(y):
    """The fender top / hood edge, from the cowl back to the lid's front, and the nose's lip."""
    if y <= LID[1]:
        return BELT
    t = (y - LID[1]) / (LID[0] - LID[1])
    z = BELT - 0.12 * min(1.0, t)
    if y > LID[0]:
        z -= 0.04 * ((y - LID[0]) / (NOSE - LID[0])) ** 2
    return z


def plan(y):
    """The plan view's taper at the ends (rounded corners): the scale on x."""
    if y > 2.10:
        return 1.0 - 0.10 * ((y - 2.10) / (NOSE - 2.10)) ** 2
    if y < -2.20:
        return 1.0 - 0.06 * ((-2.20 - y) / (-2.20 - TAIL)) ** 2
    return 1.0


def _roof_arc(cx, cz, crown_z):
    """The points 9..12 across a top from the edge (cx, cz) to the middle: a gentle camber."""
    out = []
    for f in (0.825, 0.5625, 0.275, 0.0):              # (x fractions of the cabin's 0.66 / 0.45 / 0.22 / 0 over 0.80)
        x = cx * f
        z = cz + (crown_z - cz) * (1.0 - f * f)
        out.append((x, z))
    return out


def ext_half(y):
    """The exterior's right half loop at station y: [(x, z)] * 13."""
    s = plan(y)
    az = arch_z(y)
    pts = [(side_x(SKIRT), SKIRT), (side_x(SILL), SILL), (side_x(az), az)]
    if y > TOE:                                         # the hood zone: everything above the fender top is the hood
        hz = hood_z(y)
        bx = side_x(BELT)
        pts.append((bx, hz))
        pts += [(bx - 0.004, hz + 0.001), (bx - 0.008, hz + 0.002), (bx - 0.02, hz + 0.004), (bx - 0.05, hz + 0.008)]
        cx, cz = bx - 0.11, hz + 0.015                  # the lid's edge (the gutter is between belt and here)
        pts.append((cx, cz))
        pts += _roof_arc(cx, cz, hz + 0.05)
    else:
        pts.append((side_x(BELT), BELT))
        if y > HEADER:                                  # the A-pillar zone
            cz = a_line(y)
            hz = max(BELT, min(HEAD, cz - PILLAR))
        else:
            cz, hz = CANT, HEAD
        for f in (1.0 / 3, 2.0 / 3):
            z = BELT + (hz - BELT) * f
            pts.append((side_x(z), z))
        pts.append((side_x(hz), hz))
        hx = side_x(hz)
        cx = hx - 0.07 * min(1.0, (cz - hz) / (CANT - HEAD))
        pts.append((hx + (cx - hx) * 0.45, hz + (cz - hz) * 0.72))      # (the drip rail's round)
        pts.append((cx, cz))
        crown = cz + (CROWN - CANT)
        if y < -2.20:
            crown -= 0.02 * ((-2.20 - y) / (-2.20 - TAIL)) ** 2
        pts += _roof_arc(cx, cz, crown)
    assert len(pts) == NE, (y, len(pts))
    return [(x * s, z) for x, z in pts]


def ext_loop(y):
    h = ext_half(y)
    return h + [(-x, z) for x, z in reversed(h[:-1])]        # 25 points, skirt R .. crown .. skirt L


def ext_s(k, side):
    """The exterior loop index of half-profile index k on a side."""
    return k if side == "R" else 2 * (NE - 1) - k


def int_s(k, side):
    """The interior loop index of exterior half-profile index k (>= 1) on a side."""
    return k + 3 if side == "R" else NI - (k + 3)


def _in_well(y):
    """Inside a wheel housing's length (the interior's hump is up). The housings' ends are pairs of stations
    1 mm apart (0.98 | 0.979, -0.98 | -0.981, -1.82 | -1.821) so the hump's end walls stand upright."""
    return 0.98 - 1e-6 <= y <= 1.82 + 1e-6 or -1.82 - 1e-6 <= y <= -0.981 + 1e-6


def int_half(y):
    """The interior's right half loop at station y: floor middle, the hump (flat on the floor outside the wheel
    housings), then the exterior's breakpoints 1..12 offset in by INT_OFF."""
    hump = HUMP_Z if _in_well(y) else FLOOR
    out = [(0.0, FLOOR), (WELL_X - 0.03, FLOOR), (WELL_X - 0.03, hump), (side_x(SILL) - INT_OFF - 0.005, hump)]
    eh = ext_half(y)
    s = plan(y)
    for k in range(1, NE):
        x, z = eh[k]
        x /= s
        if k <= E["head"]:                                       # (the side: straight in)
            xi, zi = x - INT_OFF, z
        elif k == NE - 1:
            xi, zi = 0.0, z - (CROWN - HEADLINER)
        else:                                                    # (the roof: down by the roof's cavity, in at the cant)
            xi = max(0.0, x - INT_OFF * (1.0 if k <= E["cant"] else 0.5))
            zi = z - (CROWN - HEADLINER) * (0.6 if k <= E["cant"] else 1.0)
        if k <= E["arch"]:
            zi = max(zi, hump)
        out.append((xi * s, zi))
    return out


def int_loop(y):
    h = int_half(y)                                      # 16 points: 0 floor middle .. 15 crown
    left = [(-x, z) for x, z in reversed(h[1:-1])]       # 14 points: E11 L .. hump L (no floor middle, no crown)
    loop = h + left
    assert len(loop) == NI, len(loop)
    return loop


# ---------------------------------------------------------------- the frame
# rings (y) at the slot edges, set back where a member would show at an opening's edge (the header and cowl
# tubes are under the roof and the cowl panel; the B- and D-posts inside their pillars; the nose and tail
# hoops in the end cavities). The front door's leading hoop is 0.955, not on the jamb (0.92): a jamb step would move
# its A-pillar joints forward along the sloping pillar, up out of it and into the windscreen.
FRAME_RINGS = [2.25, 2.18, 1.82, 1.175, 0.98, 0.955, 0.41, 0.36, 0.0, -0.12, -0.92, -1.82, -2.12, -2.33]
RING_NAMES = ["skirt_R", "sill_R", "belt_R", "head_R", "cant_R", "roof_R", "crown", "roof_L", "cant_L", "head_L",
              "belt_L", "sill_L", "skirt_L", "floor_C"]


def ring_at(y):
    """The frame's joints at y: in the cavity, half way between the shells (where there's no interior -- the
    hood, the nose -- just inside the skin)."""
    e = ext_half(y)
    has_in = TAIL_IN - 0.05 <= y <= TOE
    i = int_half(min(TOE, max(TAIL_IN, y))) if has_in else None

    def pillar():
        """The A-pillar's tube: the middle of its outer strip (head..cant), 1.8 cm in."""
        (hx, hz), (cx, cz) = e[E["head"]], e[E["cant"]]
        dx, dz = cx - hx, cz - hz
        L = math.hypot(dx, dz) or 1.0
        nx, nz = -abs(dz) / L, -abs(dx) / L
        return [round((hx + cx) / 2 + nx * 0.018, 4), round((hz + cz) / 2 + nz * 0.018, 4)]

    def mid(k):
        xe, ze = e[k]
        if k in (E["head"], E["cant"]) and HEADER < y <= TOE:
            return pillar()
        if k in (E["head"], E["cant"]) and TOE < y < TOE + 0.05:      # (the cowl's ring: under the belt, hidden)
            return [round(e[E["belt"]][0] - 0.04, 4), round(BELT - 0.06, 4)]
        if i is None and k > E["belt"]:                  # (the hood: under the gutter strip, outside the frunk tub)
            if k <= E["cant"]:
                return [round(e[E["belt"]][0] - 0.05, 4), round(e[E["belt"]][1] - 0.02, 4)]
            return [round(xe, 4), round(ze - 0.04, 4)]
        if k == E["skirt"]:                              # (up off the lower edge, inside the skirt)
            return [round(xe - 0.035, 4), round(ze + 0.035, 4)]
        if i is None and k == E["belt"]:                 # (the hood zone's fender top: under it)
            return [round(xe - 0.035, 4), round(ze - 0.03, 4)]
        if i is None or k < E["belt"]:
            nx, nz = (0.035, 0.0) if k <= E["head"] else (0.03, 0.03)
            return [round(max(0.0, xe - nx) if xe > 0 else 0.0, 4), round(ze - nz, 4)]
        xi, zi = i[k + 3]
        return [round((xe + xi) / 2, 4), round((ze + zi) / 2, 4)]
    b, h = mid(E["belt"]), mid(E["head"])
    if i is not None and not HEADER < y <= TOE:            # (off the glass's edges: under the skin and the rail band)
        b[1] = round(BELT - 0.025, 4)
        h[1] = round(HEAD + 0.025, 4)
    sl = mid(E["sill"])
    if not _in_well(y):                                  # (in the floor slab: the floor's cross members stay under it)
        sl[1] = round(FLOOR - 0.025, 4)
    pts = {"skirt": mid(E["skirt"]), "sill": sl, "belt": b, "head": h,
           "cant": mid(E["cant"]), "roof": mid(E["roof"]), "crown": mid(E["crown"])}
    out = []
    for nm in RING_NAMES:
        if nm == "floor_C":
            out.append([nm, 0.0, 0.515])
            continue
        base, _, side = nm.partition("_")
        x, z = pts[base]
        out.append([nm, -x if side == "L" else x, z])
    return out


# ---------------------------------------------------------------- the standard (written for the game)
def standard():
    rings = [{"y": y, "joints": ring_at(y)} for y in FRAME_RINGS]
    return {
        "id": "SW180",
        "class": "station_wagon",
        "about": "five-door station wagons on a 2.8 m car board (Carrow Keel K-28): 1.86 m wide, 4.64 m long, 2.06 m tall; "
                 "research/vehicles/wagon/WAGON.md. The body loft is the class's (remake/blender/kit/sw180.py): every SW180 "
                 "component fits every SW180 wagon",
        "board": "carrow_k28",
        "outer_half_width": WO, "inner_half_width": WO - INT_OFF,
        "deck": 0.50, "floor": FLOOR, "ceiling": HEADLINER, "skirt": SKIRT, "sill": SILL, "belt": BELT,
        "window": [BELT, HEAD], "cant": CANT, "crown": CROWN, "arch_top": ARCH_TOP,
        "door": {"head": HEAD, "apertures": {k: list(v) for k, v in DOORS.items()}},
        "axles": list(AXLES), "arch_half": ARCH_HALF, "arch_r": ARCH_R, "arch_zc": ARCH_ZC,
        "nose": NOSE, "tail": TAIL, "toe": TOE, "header": HEADER, "lid": list(LID), "hatch": HATCH, "quarter": list(QUARTER),
        "stations": STATIONS,
        # the frame: a ring of joints at each of these stations (they differ along the car: the nose, the hood,
        # the screen, the cabin); the same 14 names round every ring
        "ring": ring_at(-0.5),
        "rings": rings,
        "end_inset": 0.0,                                    # (the end rings above already stand in the end cavities)
        # the tops that are open: no member across the windscreen or the frunk lid
        "top_openings": [[HEADER, TOE, "screen"], [LID[1], LID[0], "lid"]],
        "tubes": {"main_d": 0.028, "brace_d": 0.022, "material": "frame_tube", "exposed_inside": [], "exposed_outside": []},
        "bolted": ["sill_R", "sill_L", "floor_C"],
        "stringers": RING_NAMES,
        # the slots: what fills them (a component declares its slot; the interface key standard/role/slot/side)
        "slots": {
            "nose": [NOSE, LID[0]], "lid": list(LID), "cowl": [LID[1], TOE], "fender": [LID[0], DOORS["front"][0]],
            "sail": [TOE, DOORS["front"][0]], "a_pillar": [TOE, HEADER], "screen": [TOE, HEADER],
            "door_front": list(DOORS["front"]), "b_post": [DOORS["front"][0], DOORS["rear"][1]], "door_rear": list(DOORS["rear"]),
            "quarter": [DOORS["rear"][1], TAIL_IN], "quarter_glass": list(QUARTER), "roof_front": [HEADER, DOORS["rear"][1]],
            "roof_rear": [DOORS["rear"][1], TAIL_IN], "tail": [TAIL_IN, TAIL], "hatch": [TAIL_IN, TAIL],
            "well_front": [AXLES[0] + ARCH_HALF, AXLES[0] - ARCH_HALF], "well_rear": [AXLES[1] + ARCH_HALF, AXLES[1] - ARCH_HALF],
            "underpan": [NOSE, TAIL], "floor": [TOE, TAIL_IN], "firewall": [TOE, TOE], "head_lamp": [NOSE, NOSE - 0.2],
            "tail_lamp": [TAIL + 0.1, TAIL],
        },
        # the closers: how each opens (hinge axis, Blender frame; degrees); a closer from any SW180 wagon swings the same
        "closers": {
            "door_front": {"hinge": "front edge", "axis_y": DOORS["front"][0], "open_deg": 68, "detents": [35, 68]},
            "door_rear": {"hinge": "front edge", "axis_y": DOORS["rear"][0], "open_deg": 70, "detents": [35, 70]},
            "hatch": {"hinge": "roof's rear edge", "axis_z": HATCH["z"][1] + 0.05, "open_deg": 88},
            "lid": {"hinge": "cowl", "axis_y": LID[1], "open_deg": 60},
        },
        "frame": {"yield_strain": 0.012, "plastic": 0.85, "dent_stiffness": 90000.0, "min_energy": 2500.0, "max_dent": 0.35},
        "detach_count": 3,
        "detach_share": 0.3,
        "pair_min": 0.25,     # m: fastenings judged over 25 cm and more (the nose hoops are 7 cm apart)
        # (a car's panels crumple with its soft frame -- 28 cm at 30 km/h into a wall -- and stay on: calibrated in
        # the game, wall crashes at 30 / 50 / 70 km/h: the lamps break / the windscreen and fenders come off too)
        "tolerance": {"glazing": 0.012, "door_glass": 0.012, "hatch_glass": 0.012, "door_leaf": 0.06, "hatch": 0.06, "frunk_lid": 0.06,
                      "side_bay": 0.16, "roof_bay": 0.06, "end_cap": 0.16, "trim": 0.20, "lining_bay": 0.08, "ceiling_bay": 0.08,
                      "end_lining": 0.08, "floor": 1.0, "wheel_well": 0.15, "underpan": 0.12, "reveal": 0.08, "seat": 0.15,
                      "fittings": 0.10, "dash": 0.10, "lamp": 0.02, "frunk_tub": 0.35},
    }
