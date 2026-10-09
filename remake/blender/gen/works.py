"""
works.py -- catalog records of kind 'industrial', 'tower', 'bigbox', 'strip' and 'vacant' -> Building.

  industrial  multi-storey brick/metal works: office front, machine floor, upper lofts, a stair bay,
              loading dock; smokestack / roof monitor / water tank from the components words.
              grain_elevator: a crib elevator (driveway, ladder up the leg to the bin-top gallery,
              scale office) or a steel-bin co-op (bins, leg tower, scale office).
  tower       water towers (standpipe / tin_man / multi_leg_tank / spheroid / fluted_column) with a
              climbable ladder and a pump house you can walk into.
  bigbox      one huge sales floor with checkout lanes, back room and dock, parking lot, pylon sign.
  strip       a row of storefronts under a canopy (or a single pad store), parking, pylon sign.
  vacant      the record's `former` traits built closed: a boarded store, or a boarded works.
"""
import math

from common import (dget, Palette, WALL_TEX, brick_for, clamp, hexcol, lib_building, rng, std_materials, darken, g, FONT_SANS,
                    FONT_SERIF, ft)
import gbhouse as gh
import gbfurn as fu
import shopfit
import store
import json
import os
from common import INVENTORY


def inventory_parts(rid):
    """The record's extra inventory footprints (e.g. an elevator's bin annexes) in building-local
    coordinates, matching remake/tools/placement.py: the building's front (local +y) points along
    f = unit vector from the structure's (x, s) to the midpoint of front_edge, and its right (local
    +x) is r = (x: fs, s: -fx).  So a map offset (dx, ds) is local x = dx*fs - ds*fx, local
    y = dx*fx + ds*fs.  (front_edge points are (s, x).)"""
    try:
        with open(INVENTORY) as f:
            inv = json.load(f)
    except OSError:
        return []
    st = next((s for s in inv.get("structures", []) if s["id"] == rid), None)
    if not st or not st.get("parts") or not st.get("front_edge"):
        return []
    (s0, x0), (s1, x1) = st["front_edge"]
    fs, fx = (s0 + s1) / 2 - st["s"], (x0 + x1) / 2 - st["x"]
    n = math.hypot(fs, fx) or 1.0
    fs, fx = fs / n, fx / n
    out = []
    for pt in st["parts"]:
        ds, dx = pt["s"] - st["s"], pt["x"] - st["x"]
        out.append((dx * fs - ds * fx, dx * fx + ds * fs, pt["w"], pt["d"]))
    return out

TE = 0.35


def materials(b, tr, cond="kept"):
    pal = Palette(b)
    col = tr.get("colors", {}) or {}
    body = col.get("body") or "#8e4a36"
    std_materials(pal, trim=col.get("trim") or "#d8d2c4", door=col.get("accent") or "#3a3a36")
    shopfit.shop_materials(pal)
    walls = tr.get("walls", "brick")
    wear = {"kept": 1.0, "worn": 0.88, "shabby": 0.75, "boarded": 0.68}.get(cond, 1.0)
    if walls == "brick":
        pal.surf("ext", brick_for(hexcol(body)), rough=0.9)
    elif walls == "metal":
        pal.surf("ext", "corrugated_rusty" if cond in ("shabby", "boarded") else "corrugated", rough=0.5, metal=0.6)
    elif walls == "concrete":
        pal.surf("ext", "concrete", rough=0.9)
    else:
        pal.surf("ext", WALL_TEX.get(walls, "drop_siding"), darken(hexcol(body), wear), rough=0.8)
    pal.surf("roof", "metal_roof", "#8a8c8e", rough=0.6, metal=0.4)
    pal.surf("roof_m", "concrete", rough=0.95)
    pal.surf("floor", "concrete", rough=0.9)
    pal.surf("plaster", "brick_painted" if walls == "brick" else "paint", "#e2ddd2", rough=0.9)
    pal.surf("ceiling", "weathered_board", rough=0.9)
    pal.surf("found", "concrete", rough=0.9)
    pal.surf("wood", "weathered_board", rough=0.9)
    pal.surf("bin_metal", "corrugated", rough=0.45, metal=0.7)
    pal.solid("roof_under", (0.45, 0.44, 0.42), rough=0.8)
    pal.solid("sign_board", hexcol(col.get("accent") or "#1e2a3a"), rough=0.5)
    pal.solid("paint_band", hexcol(col.get("accent") or "#f0ece0"), rough=0.6)
    pal.solid("tank_paint", hexcol(dget(tr, "paint").get("color") or "#9cb0bc"), rough=0.5, metal=0.2)
    pal.solid("letters_dark", (0.08, 0.08, 0.1), rough=0.5)
    pal.solid("yellow", (0.95, 0.75, 0.1), rough=0.5)
    return pal


def stoops(spec, FL, skip=()):
    """Steps outside exterior doors (the floor is FL above grade); `skip` names doors that open at
    grade level (driveways, docks)."""
    from institution import add_stoops
    add_stoops(spec, FL, skip=tuple(skip))


# ------------------------------------------------------------------ industrial
def build_works(rec, tr, boarded=False):
    rid = rec["id"]
    rnd = rng(rid)
    names = rec.get("names") or {}
    lot = rec.get("lot") or {"w": 30.0, "d": 25.0}
    lot_w, lot_d = lot["w"], lot["d"]
    b = lib_building(rid)
    cond = "boarded" if boarded else tr.get("condition", "kept")
    materials(b, tr, cond)
    comps = " ".join(str(c) for c in (tr.get("components") or [])).lower()
    # an industrial park's building (research/jobs, urban_layout/07): one tall bay up to 120 x 80 m, the office across
    # its front, docks behind
    shed = tr.get("form") == "shed"
    storeys = 1 if shed else int(clamp(tr.get("storeys") or 2, 1, 5))
    W = clamp(lot_w - 6.0, 12.0, 120.0 if shed else 60.0)
    D = clamp(lot_d - 8.0, 10.0, 80.0 if shed else 34.0)
    if shed and tr.get("bldg_w"):
        W = clamp(float(tr["bldg_w"]), 12.0, min(120.0, lot_w - 4.0))
        D = clamp(float(tr["bldg_d"]), 10.0, min(80.0, lot_d - 4.0))
    x0, x1 = -W / 2, W / 2
    y1 = lot_d / 2 - 4.0
    y0 = y1 - D
    FL = 1.2 if shed else 0.35                 # (a shed's floor at dock height)
    H = 7.5 if shed else 4.4
    floors = [(FL, FL + H)]
    for k in range(1, storeys):
        fz = floors[-1][1] + 0.4
        floors.append((fz, fz + 3.8))
    wall_top = floors[-1][1] + 0.4
    apartments = "apartment" in comps or "loft" in comps
    rooms, doors, wins = [], [], []
    # stair tower against the -x wall: a dog-leg per storey, stacked; every floor's rooms open off
    # the landing zone at the front of the bay (the flights and their well fill the rest of it)
    sb1 = x0 + TE + 2.4
    stairs = []
    front_y = y1 - TE - 0.65          # centre of the 1.3 m landing zone at the front of the bay
    if storeys > 1:
        rooms.append(dict(name="STAIRS", rect=(x0, y0, sb1, y1), type=None, no_furnish=True))
        for k in range(1, storeys):
            rise = floors[k][0] - floors[k - 1][0]
            n = math.ceil(rise / 0.19)
            n += n % 2
            stairs.append(dict(type="dogleg", start=(x0 + TE + 0.05, y1 - TE - 1.3), dir=(0, -1), width=1.0, n=n, run=0.25,
                               landing=1.0, turn="left", floor=k - 1, to_floor=k, rail=True))
        for k in range(1, storeys):
            rooms.append(dict(name=f"SH{k}", floor=k, rect=(x0, y0, sb1, y1), type=None, no_furnish=True))
        doors.append(dict(name="stair_door", at=(x0 + TE + 1.6, y1), w=0.95, ext=True, out=True, locked=boarded))
    # ground floor: office across the front, machine floor behind
    gx0 = sb1 if storeys > 1 else x0
    oy = y1 - 4.5
    rooms.append(dict(name="OFFICE", rect=(gx0, oy, x1, y1), type="office", fitout=shopfit.fitout_for("office" if not boarded else "vacant", rnd)))
    rooms.append(dict(name="FLOOR", rect=(gx0, y0, x1, oy), type="shop",
                      fitout=shopfit.fitout_for("machine_floor" if not boarded else "vacant", rnd)))
    doors.append(dict(name="office_floor", at=((gx0 + x1) / 2 + 1.5, oy), w=0.95, swing_into="FLOOR"))
    doors.append(dict(name="front", at=((gx0 + x1) / 2, y1), w=1.6, ext=True, leaves=2, glazed=(0.12, 0.45, 0.88, 0.92), transom=0.5,
                      locked=boarded))
    if storeys > 1:
        doors.append(dict(name="stair_office", at=(sb1, front_y), w=0.9, swing_into="OFFICE"))
    # freight doors on the rear wall (hinged pairs), a loading dock outside
    nd = max(1, int((x1 - gx0) / (12.0 if shed else 9.0)))
    for i in range(nd):
        doors.append(dict(name=f"freight{i}", at=(gx0 + (x1 - gx0) * (i + 0.5) / nd, y0), w=3.0, h=3.2, ext=True, leaves=2, out=True,
                          panels=[(0.1, 0.5, 0.9, 0.9), (0.1, 0.08, 0.9, 0.45)]))
    # upper floors: lofts (open work floors) or apartments in a converted mill
    for k in range(1, storeys):
        if apartments:
            nb = max(1, int((x1 - sb1) / 6.0))
            # a corridor along the front wall's inner face, level with the stair landing
            cy0 = y1 - 1.6
            rooms.append(dict(name=f"UC{k}", floor=k, rect=(sb1, cy0, x1, y1), type=None, open_plan_to=f"SH{k}"))
            for j in range(nb):
                a0, a1 = sb1 + (x1 - sb1) * j / nb, sb1 + (x1 - sb1) * (j + 1) / nb
                ym = (y0 + cy0) / 2
                rooms.append(dict(name=f"AF{k}_{j}", floor=k, rect=(a0, ym, a1, cy0), type="living"))
                rooms.append(dict(name=f"AB{k}_{j}", floor=k, rect=(a0, y0, a1, ym), type="bed"))
                doors.append(dict(name=f"af{k}_{j}", floor=k, at=((a0 + a1) / 2, cy0), w=0.9, swing_into=f"AF{k}_{j}"))
                doors.append(dict(name=f"ab{k}_{j}", floor=k, at=((a0 + a1) / 2 + 0.8, ym), w=0.9, swing_into=f"AB{k}_{j}"))
        else:
            rooms.append(dict(name=f"LOFT{k}", floor=k, rect=(sb1, y0, x1, y1), type="shop",
                              fitout=shopfit.fitout_for("stockroom" if (boarded or k % 2 == 0) else "machine_floor", rnd)))
            doors.append(dict(name=f"loft{k}", floor=k, at=(sb1, front_y), w=0.95, swing_into=f"LOFT{k}"))
    # regular window grid (segmental-arch brick openings approximated by head caps)
    for k, (fz, cz) in enumerate(floors):
        for (a, c) in (((x1, y1), (x0, y1)), ((x0, y0), (x1, y0)), ((x0, y1), (x0, y0)), ((x1, y0), (x1, y1))):
            Lw = math.dist(a, c)
            n = max(1, int((Lw - 1.0) / (6.0 if shed else 2.4)))
            for j in range(n):
                t = (j + 0.5) / n
                p = (a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t)
                if any(math.dist(p, d["at"]) < d["w"] / 2 + 0.6 + 0.4 for d in doors if d.get("floor", 0) == k or d.get("ext")):
                    continue
                if shed:            # a clerestory band high in the bay's walls
                    wins.append(dict(at=p, floor=k, w=2.4, sill=4.6, h=1.6, kind="picture", cols=3))
                    continue
                wins.append(dict(at=p, floor=k, w=1.2, sill=1.0, h=min(2.4, cz - fz - 1.3), kind="dh", cols=3, head_cap=True))
    spec = dict(t_ext=TE, t_int=0.2, era="old",
                mats=dict(ext="ext", int="plaster", roof="roof_m", roof_under="roof_under", found="found", floor="floor",
                          ceiling="ceiling", trim="trim", door="door", fascia="trim", porch="concrete", post="trim", furn="furniture"),
                blocks=[dict(name="works", rect=(x0, y0, x1, y1), floors=floors, wall_top=wall_top, found_top=FL - 0.05,
                             roof=dict(type="flat", thick=0.35, parapet=0.9, coping="trim"))],
                rooms=rooms, doors=doors, windows=wins, stairs=stairs, rails=[], porches=[], chimneys=[], fireplaces=[])
    stoops(spec, FL, skip=[d["name"] for d in doors if d["name"].startswith("freight")])
    gh.House(b, spec).build()
    p = b.part("works_trim-col")
    if boarded:
        for w_ in wins:
            if w_.get("floor", 0) == 0:
                x, y = w_["at"]
                hw = w_["w"] / 2 + 0.05
                fz = floors[0][0]
                if abs(y - y1) < 0.01:
                    p.box((x - hw, y1 + 0.01, fz + w_["sill"] - 0.05), (x + hw, y1 + 0.05, fz + w_["sill"] + w_["h"] + 0.05), "plywood")
                elif abs(y - y0) < 0.01:
                    p.box((x - hw, y0 - 0.05, fz + w_["sill"] - 0.05), (x + hw, y0 - 0.01, fz + w_["sill"] + w_["h"] + 0.05), "plywood")
    # loading dock along the rear
    p.box((gx0 + 0.5, y0 - 2.5, 0.0), (x1 - 0.5, y0, FL - 0.02), "concrete")
    # smokestack / roof monitor / tank
    if any(w in comps for w in ("chimney", "smokestack", "stack", "boiler")) or tr.get("use") in ("foundry", "power_plant", "brickworks"):
        p.cylinder((x1 + 2.0, y0 + 3.0), 1.1, 0.0, wall_top + 12.0, "ext", n=16, r1=0.7)
    if any(w in comps for w in ("monitor", "clerestory", "sawtooth")):
        mx0, mx1 = gx0 + 2.0, x1 - 2.0
        p.box((mx0, (y0 + y1) / 2 - 2.0, wall_top), (mx1, (y0 + y1) / 2 + 2.0, wall_top + 1.6), "ext")
        gh.hip_roof(p, mx0 - 0.2, mx1 + 0.2, (y0 + y1) / 2 - 2.2, (y0 + y1) / 2 + 2.2, wall_top + 1.6, 15, 0.2, 0.12, "roof", "trim", "trim")
    if "tank" in comps or "water tower" in comps:
        tx, ty = x1 - 4.0, y0 + 4.0
        for dx in (-1.2, 1.2):
            for dy in (-1.2, 1.2):
                p.box((tx + dx - 0.1, ty + dy - 0.1, wall_top), (tx + dx + 0.1, ty + dy + 0.1, wall_top + 4.0), "wood")
        p.cylinder((tx, ty), 1.9, wall_top + 4.0, wall_top + 7.0, "wood", n=16)
    # painted name band on the parapet
    nm = (names.get("sign") or names.get("name") or "").upper()
    main = nm.split(" - ")[0].split(" · ")[0][:36]
    if main:
        band_z = wall_top - 0.1
        p.box((x0 + 1.0, y1 + 0.01, band_z - 0.2), (x1 - 1.0, y1 + 0.03, band_z + 0.75), "paint_band")
        g.text_mesh(b, "sign_works", main, clamp((W - 3.0) / max(10, len(main)) * 1.4, 0.3, 0.7), (0.0, y1 + 0.035, band_z + 0.1),
                    math.pi, "letters_dark", extrude=0.005, font=FONT_SANS)
    # gravel yard, rail spur, fence
    yd = b.part("yard-col")
    yd.box((-lot_w / 2, -lot_d / 2, -0.02), (lot_w / 2, y0 - 2.5, 0.03), "gravel", sides="Z")
    if "rail" in comps:
        yd.box((-lot_w / 2, y0 - 6.0, 0.0), (lot_w / 2, y0 - 3.6, 0.18), "gravel")
        for rx in (-0.72, 0.72):
            yd.box((-lot_w / 2, y0 - 4.8 + rx - 0.04, 0.18), (lot_w / 2, y0 - 4.8 + rx + 0.04, 0.32), "steel")
    b.part("walk-col").box((-1.0, y1 + 1.2, -0.02), (1.0, lot_d / 2, 0.03), "sidewalk", sides="Z")
    return b


def build_grain_elevator(rec, tr, boarded=False):
    rid = rec["id"]
    rnd = rng(rid)
    names = rec.get("names") or {}
    lot = rec.get("lot") or {"w": 14.0, "d": 18.0}
    b = lib_building(rid)
    cond = "boarded" if boarded else tr.get("condition", "kept")
    tr2 = dict(tr)
    tr2.setdefault("walls", "metal")
    materials(b, tr2, cond)
    comps = " ".join(str(c) for c in (tr.get("components") or [])).lower()
    steel = "steel" in comps or "bin" in comps and tr.get("year_built", 1950) >= 1950 or tr.get("walls") == "metal" and "crib" not in comps
    W, D = clamp(lot["w"] - 3.0, 7.0, 11.0), clamp(lot["d"] - 5.0, 9.0, 13.0)
    x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2
    DRV = 1.9
    EAVE = 14.0 if not steel else 6.0
    FL = 0.05
    rooms = [dict(name="DRIVE", rect=(-DRV, y0, DRV, y1), type=None, no_furnish=True)]
    doors = [dict(name="drive_n", at=(0.0, y1), w=2 * DRV - 0.3, h=4.0, ext=True, leaves=2, out=True, panels=[(0.08, 0.08, 0.92, 0.92)]),
             dict(name="drive_s", at=(0.0, y0), w=2 * DRV - 0.3, h=4.0, ext=True, leaves=2, out=True, panels=[(0.08, 0.08, 0.92, 0.92)])]
    spec = dict(t_ext=0.15, t_int=0.15, era="old",
                mats=dict(ext="ext", int="wood", roof="roof", roof_under="roof_under", found="found", floor="wood", ceiling="wood",
                          trim="trim", door="wood", fascia="trim", porch="concrete", post="trim", furn="furniture"),
                blocks=[dict(name="elev", rect=(x0, y0, x1, y1), floors=[(FL, 4.2)], wall_top=EAVE, found_top=0.0,
                             roof=dict(type="gable", ridge="y", pitch=35, eave_oh=0.3, rake_oh=0.2, thick=0.15))],
                rooms=rooms, doors=doors, windows=[], stairs=[], rails=[], porches=[], chimneys=[], fireplaces=[])
    # scale office annex on the east side, or the west when the bin parts stand to the east
    parts = inventory_parts(rid)
    east = not (parts and sum(pp[0] for pp in parts) > 0)
    ox0, ox1, oy0, oy1 = (x1, x1 + 4.2, y0 + 1.0, y0 + 6.0) if east else (x0 - 4.2, x0, y0 + 1.0, y0 + 6.0)
    spec["blocks"].append(dict(name="office", rect=(ox0, oy0, ox1, oy1), floors=[(0.35, 2.9)], wall_top=3.1, found_top=0.3,
                               roof=dict(type="shed", high="W" if east else "E", pitch=12, eave_oh=0.3, thick=0.12)))
    rooms.append(dict(name="SCALEOFF", rect=(ox0, oy0, ox1, oy1), type="office", fitout=shopfit.fitout_for("office", rnd)))
    doors.append(dict(name="office", at=((ox0 + ox1) / 2, oy1), w=0.9, ext=True, locked=boarded))
    spec["windows"].append(dict(at=(ox1 if east else ox0, (oy0 + oy1) / 2), w=1.0, sill=1.0, h=1.2, kind="dh", cols=2))
    stoops(spec, 0.35, skip=("drive_n", "drive_s"))
    gh.House(b, spec).build()
    p = b.part("elevator-col")
    # bins either side of the driveway (solid crib), overhead bin above it (driveway ceiling)
    for sx in (-1, 1):
        xa, xb = sorted((sx * DRV, sx * (W / 2 - 0.15)))
        p.box((xa, y0 + 0.15, 0.05), (xb, y1 - 0.15, EAVE - 0.2), "wood")
    LX, LY = 0.9, y1 - 2.2
    p.box((-DRV, y0 + 0.15, 4.2), (LX - 0.45, y1 - 0.15, EAVE - 0.2), "wood")
    p.box((LX - 0.45, y0 + 0.15, 4.2), (DRV, LY - 0.45, EAVE - 0.2), "wood")
    p.box((LX - 0.45, LY + 0.45, 4.2), (DRV, y1 - 0.15, EAVE - 0.2), "wood")
    # the leg (boot to head) and the ladder beside it, climbable to the bin-top gallery
    p.box((LX - 0.4, LY - 1.3, 0.0), (LX + 0.25, LY - 0.55, EAVE + 2.0), "wood")
    gallery_z = EAVE - 0.15
    p.box((x0 + 0.15, y0 + 0.15, gallery_z - 0.1), (LX - 0.45, y1 - 0.15, gallery_z), "wood")
    p.box((LX + 0.45, y0 + 0.15, gallery_z - 0.1), (x1 - 0.15, y1 - 0.15, gallery_z), "wood")
    p.box((LX - 0.45, y0 + 0.15, gallery_z - 0.1), (LX + 0.45, LY - 0.45, gallery_z), "wood")
    lad = b.part("ladder_leg")
    for side in (-0.22, 0.22):
        lad.box((LX + side - 0.025, LY + 0.28, 0.05), (LX + side + 0.025, LY + 0.33, gallery_z + 1.1), "iron")
    z = 0.3
    while z < gallery_z + 1.0:
        lad.box((LX - 0.22, LY + 0.29, z), (LX + 0.22, LY + 0.32, z + 0.03), "iron")
        z += 0.3
    b.empty("light_drive", (0.0, 0.0, 3.8))
    b.empty("light_gallery", (x0 + 1.5, 0.0, gallery_z + 2.0))
    # steel bins (inventory parts / components) beside the elevator
    # bins stand on the record's inventory parts when it has them (their footprints beside the
    # elevator on the map); otherwise three beside the -x wall
    if parts:
        spots = [(px, py, clamp(min(pw, pd) / 2 - 0.2, 2.5, 6.0)) for (px, py, pw, pd) in parts]
    elif steel or "bin" in comps:
        spots = [(x0 - 6.0, y0 + 5.0 + (i - 1) * 11.0, 5.0) for i in range(3)]
    else:
        spots = []
    nbin = len(spots)
    # slip-formed concrete bins (walls "concrete" / "concrete bin" components) are taller, plain
    # cylinders with a flat cap and a gallery house along the top; steel bins get the cone roof
    concrete = tr.get("walls") == "concrete" or "concrete bin" in comps
    for (cx, cy, r) in spots:
        if concrete:
            p.cylinder((cx, cy), r, 0.0, EAVE + 4.0, "concrete", n=28)
            p.cylinder((cx, cy), r + 0.15, EAVE + 4.0, EAVE + 4.3, "concrete", n=28)
            continue
        p.cylinder((cx, cy), r, 0.0, 12.0, "bin_metal", n=28)
        for k in range(8):
            rr = r * (1 - k / 8)
            p.cylinder((cx, cy), rr + 0.05, 12.0 + k * 0.45, 12.0 + (k + 1) * 0.45, "bin_metal", n=28)
    if concrete and nbin:
        # the enclosed gallery over the bins (and on to the head house), carrying the grain
        xs = [c[0] for c in spots] + [0.0]
        ys = [c[1] for c in spots] + [0.0]
        if max(xs) - min(xs) >= max(ys) - min(ys):           # bins in a row along x
            gx0, gx1, gy0, gy1 = min(xs) - 1.2, max(xs) + 1.2, sum(ys[:-1]) / nbin - 1.3, sum(ys[:-1]) / nbin + 1.3
        else:
            gx0, gx1, gy0, gy1 = sum(xs[:-1]) / nbin - 1.3, sum(xs[:-1]) / nbin + 1.3, min(ys) - 1.2, max(ys) + 1.2
        p.box((gx0, gy0, EAVE + 4.3), (gx1, gy1, EAVE + 6.5), "ext")
        gh.hip_roof(p, gx0 - 0.2, gx1 + 0.2, gy0 - 0.2, gy1 + 0.2, EAVE + 6.5, 18, 0.15, 0.1, "roof", "trim", "trim")
    # company sign on the elevator's street face
    nm = (names.get("sign") or names.get("name") or "").upper()
    parts_ = [t.strip() for t in nm.replace("·", "-").split(" - ") if t.strip()]
    if parts_:
        p.box((x0 + 0.4, y1 + 0.01, EAVE - 4.0), (x1 - 0.4, y1 + 0.04, EAVE - 1.0), "paint_band")
        for i, t in enumerate(parts_[:3]):
            g.text_mesh(b, f"sign_elev_{i}", t[:24], clamp((W - 1.2) / max(8, len(t[:24])) * 1.4, 0.2, 0.55) * (1.0 if i == 0 else 0.6),
                        (0.0, y1 + 0.045, EAVE - 1.7 - i * 0.8), math.pi, "letters_dark", extrude=0.005, font=FONT_SANS)
    return b


# ------------------------------------------------------------------ water towers
def build_tower(rec, tr):
    rid = rec["id"]
    rnd = rng(rid)
    lot = rec.get("lot") or {"w": 16.0, "d": 16.0}
    b = lib_building(rid)
    materials(b, dict(tr, walls="brick"), "kept")
    typ = tr.get("type", "multi_leg_tank")
    paint = dget(tr, "paint")
    letter = (paint.get("lettering") or (rec.get("names") or {}).get("name") or "").upper()[:16]
    p = b.part("tower-col")
    # pump house (walk-in) at the lot's street side; the tank stands behind it; one fence round the lot
    hy1 = lot["d"] / 2 - 3.2
    spec = dict(t_ext=0.25, t_int=0.12, era="old",
                mats=dict(ext="ext", int="plaster", roof="roof", roof_under="roof_under", found="found", floor="floor", ceiling="plaster",
                          trim="trim", door="door", fascia="trim", porch="concrete", post="trim", furn="furniture"),
                blocks=[dict(name="pump", rect=(-2.4, hy1 - 3.0, 2.4, hy1), floors=[(0.3, 3.0)], wall_top=3.2, found_top=0.25,
                             roof=dict(type="hip", pitch=25, eave_oh=0.4, thick=0.15))],
                rooms=[dict(name="PUMP", rect=(-2.4, hy1 - 3.0, 2.4, hy1), type="shop", fitout=shopfit.fitout_for("machine_floor", rnd))],
                doors=[dict(name="pump", at=(0.0, hy1), w=0.95, ext=True)],
                windows=[dict(at=(-2.4, hy1 - 1.5), w=0.9, sill=1.0, h=1.2, kind="dh", cols=2),
                         dict(at=(2.4, hy1 - 1.5), w=0.9, sill=1.0, h=1.2, kind="dh", cols=2)],
                stairs=[], rails=[], porches=[], chimneys=[], fireplaces=[])
    stoops(spec, 0.3)
    gh.House(b, spec).build()
    space = (hy1 - 3.4) - (-lot["d"] / 2 + 1.0)          # depth left behind the pump house for the tank
    tank_fit = max(3.0, space / 2 - 0.3)
    cy = -lot["d"] / 2 + 1.0 + space / 2
    if typ == "standpipe":
        r, h = min(5.0, tank_fit), 26.0
        p.cylinder((0.0, cy), r, 0.0, h, "tank_paint", n=32)
        p.cylinder((0.0, cy), r + 0.1, h, h + 0.3, "tank_paint", n=32)
        tank_z, tank_r, lad_top = h - 3.0, r, h + 0.3
        ladder_x, ladder_y = r + 0.35, cy
    else:
        tank_z = 28.0
        tank_r = min({"tin_man": 4.5, "spheroid": 5.5, "fluted_column": 5.0}.get(typ, 5.5), tank_fit + 1.0)
        if typ == "multi_leg_tank":
            for a in range(6):
                ang = a * math.pi / 3
                lx, ly = math.cos(ang) * tank_r * 0.95, cy + math.sin(ang) * tank_r * 0.95
                p.cylinder((lx, ly), 0.3, 0.0, tank_z, "tank_paint", n=8, r1=0.22)
            p.cylinder((0.0, cy), 0.7, 0.0, tank_z, "tank_paint", n=12)
            p.cylinder((0.0, cy), tank_r + 0.8, tank_z - 0.15, tank_z, "steel", n=24)             # balcony
            ladder_x, ladder_y = tank_r * 0.95 + 0.4, cy
        else:
            p.cylinder((0.0, cy), 1.8 if typ != "fluted_column" else 2.6, 0.0, tank_z, "tank_paint", n=20)
            ladder_x, ladder_y = 2.2 if typ != "fluted_column" else 3.0, cy
        # tank body: stacked rings approximating a sphere / ellipsoid
        for k in range(10):
            a0, a1 = -math.pi / 2 + k * math.pi / 10, -math.pi / 2 + (k + 1) * math.pi / 10
            rr = tank_r * max(0.15, (math.cos(a0) + math.cos(a1)) / 2)
            p.cylinder((0.0, cy), rr, tank_z + tank_r * 0.7 * (1 + math.sin(a0)), tank_z + tank_r * 0.7 * (1 + math.sin(a1)), "tank_paint", n=28)
        lad_top = tank_z
    # climbable ladder up the side
    lad = b.part("ladder_tower")
    for side in (-0.22, 0.22):
        lad.box((ladder_x - 0.03, ladder_y + side - 0.025, 0.0), (ladder_x + 0.03, ladder_y + side + 0.025, lad_top + 1.0), "steel")
    z = 0.3
    while z < lad_top + 0.9:
        lad.box((ladder_x - 0.02, ladder_y - 0.22, z), (ladder_x + 0.02, ladder_y + 0.22, z + 0.03), "steel")
        z += 0.3
    # town name painted on the tank facing the street
    if letter:
        g.text_mesh(b, "sign_tower", letter, clamp(tank_r * 1.6 / max(4, len(letter)), 0.4, 1.4),
                    (0.0, cy + tank_r + 0.06, tank_z + tank_r * 0.7), math.pi, "white_text", extrude=0.05, font=FONT_SANS)
    # chain-link fence round the lot, a gate in front of the pump house door
    lw, ld = lot["w"] / 2 - 0.3, lot["d"] / 2 - 0.3
    gh.chainlink_fence(b, [(lw, ld), (-lw, ld), (-lw, -ld), (lw, -ld), (lw, ld)], 1.8, gate=(0, lw - 0.6, 1.2))
    b.part("walk-col").box((-0.6, hy1 + 1.2, -0.02), (0.6, ld, 0.03), "sidewalk", sides="Z")
    return b


# ------------------------------------------------------------------ retail
def build_retail(rec, tr):
    """Big box (one tenant, huge floor) or strip centre (a row of stores / a single pad)."""
    rid = rec["id"]
    rnd = rng(rid)
    kind = rec.get("kind")
    names = rec.get("names") or {}
    lot = rec.get("lot") or {"w": 85.0, "d": 22.0}
    lot_w, lot_d = lot["w"], lot["d"]
    b = lib_building(rid)
    era = tr.get("era", 1985)
    tr2 = dict(tr, walls="block" if era < 1975 else "stucco")
    materials(b, tr2, "kept")
    pal = Palette(b)
    pal.surf("ext", "block" if era < 1975 else "stucco", "#d8d0c0", rough=0.85)
    pal.solid("canopy", (0.75, 0.72, 0.66), rough=0.6)
    pal.surf("floor", "vct", rough=0.35)
    pal.surf("ceiling", "acoustic", rough=0.7)
    stores = (tr.get("stores") or [])[:8] or [{"business": "Store", "type": "variety_store", "sign": "STORE"}]
    park_d = 18.0 if kind == "bigbox" else 12.0
    if lot_d < 20:
        park_d = min(park_d, lot_d * 0.35)
    W = clamp(lot_w - 4.0, 12.0, 140.0 if kind == "bigbox" else 120.0)      # (a community centre's anchor: ~115 m)
    D = clamp(lot_d - park_d - 3.0, 9.0, 80.0 if kind == "bigbox" else 42.0)
    x0, x1 = -W / 2, W / 2
    y1 = lot_d / 2 - park_d
    y0 = y1 - D
    FL = 0.15
    H = 5.0 if kind == "bigbox" else 3.8
    spec = dict(t_ext=0.3, t_int=0.15, era="modern",
                mats=dict(ext="ext", int="plaster", roof="roof_m", roof_under="roof_under", found="found", floor="floor", ceiling="ceiling",
                          trim="trim", door="door", fascia="trim", porch="concrete", post="trim", furn="furniture"),
                blocks=[dict(name="retail", rect=(x0, y0, x1, y1), floors=[(FL, FL + H)], wall_top=FL + H + 0.8, found_top=FL - 0.05,
                             roof=dict(type="flat", thick=0.35, parapet=0.9 if kind == "bigbox" else 0.6, coping="trim"))],
                rooms=[], doors=[], windows=[], stairs=[], rails=[], porches=[], chimneys=[], fireplaces=[])
    rooms, doors, wins = spec["rooms"], spec["doors"], spec["windows"]
    if kind == "bigbox":
        by = y0 + 7.0
        rooms.append(dict(name="SALES", rect=(x0, by, x1, y1), type="shop", fitout=bigbox_fitout(rnd, stores[0].get("type", "discount"))))
        rooms.append(dict(name="BACK", rect=(x0, y0, x1 - 8.0, by), type="stock", fitout=shopfit.fitout_for("stockroom", rnd)))
        rooms.append(dict(name="OFFICES", rect=(x1 - 8.0, y0 + 2.5, x1, by), type="office", fitout=shopfit.fitout_for("office", rnd)))
        rooms.append(dict(name="WC", rect=(x1 - 8.0, y0, x1, y0 + 2.5), type="bath", floor_mat="hextile"))
        doors += [dict(name="entry_in", at=(-4.0, y1), w=2.0, ext=True, leaves=2, glazed=(0.05, 0.05, 0.95, 0.95)),
                  dict(name="entry_out", at=(4.0, y1), w=2.0, ext=True, leaves=2, glazed=(0.05, 0.05, 0.95, 0.95)),
                  dict(name="sales_back", at=(x0 + 6.0, by), w=2.0, leaves=2, swing_into="BACK"),
                  dict(name="sales_off", at=(x1 - 4.0, by), w=0.95, swing_into="OFFICES"),
                  dict(name="wc", at=(x1 - 8.0, y0 + 1.25), w=0.8, swing_into="WC")]
        for i in range(3):
            doors.append(dict(name=f"dock{i}", at=(x0 + 6.0 + i * 5.0, y0), w=3.0, h=3.4, ext=True, leaves=2, out=True,
                              panels=[(0.08, 0.08, 0.92, 0.92)]))
        for sx in (-1, 1):
            wins.append(dict(at=(sx * 10.0, y1), w=6.0, sill=0.5, h=2.6, kind="picture", cols=4))
        fronts = [(stores[0], -8.0, 8.0)]
    else:
        n = len(stores)
        bw = W / n
        fronts = []
        for i, st in enumerate(stores):
            bx0, bx1 = x0 + bw * i, x0 + bw * (i + 1)
            yb = y0 + min(4.0, D * 0.3)
            rooms.append(dict(name=f"SHOP{i}", rect=(bx0, yb, bx1, y1), type="shop", fitout=shopfit.fitout_for(st.get("type", "variety_store"), rnd)))
            rooms.append(dict(name=f"BACK{i}", rect=(bx0, y0, bx1, yb), type="stock", fitout=shopfit.fitout_for("stockroom", rnd)))
            dx = (bx0 + bx1) / 2 + (bw * 0.25 if bw > 8 else 0.0)
            doors.append(dict(name=f"front{i}", at=(dx, y1), w=1.0, ext=True, glazed=(0.05, 0.05, 0.95, 0.95),
                              locked=st.get("type") == "vacant"))
            doors.append(dict(name=f"shop{i}_back", at=((bx0 + bx1) / 2 - (1.0 if bw > 5 else 0.0), yb), w=0.9, swing_into=f"BACK{i}"))
            doors.append(dict(name=f"back{i}", at=((bx0 + bx1) / 2 + (1.0 if bw > 5 else 0.0), y0), w=0.9, ext=True))
            ww = bw - 2.6
            if ww > 1.0:
                wins.append(dict(at=(dx - 0.9 - ww / 2 if dx - 0.9 - ww / 2 > bx0 + 0.3 else dx + 0.9 + ww / 2, y1), w=min(ww, bw - 2.2),
                                 sill=0.45, h=2.3, kind="picture", cols=max(1, int(ww / 1.5))))
            fronts.append((st, bx0, bx1))
    gh.House(b, spec).build()
    p = b.part("retail_trim-col")
    # canopy along the front, sign letters on the fascia above each store
    p.box((x0 - 0.3, y1, FL + H - 0.4), (x1 + 0.3, y1 + 2.6, FL + H - 0.2), "canopy")
    for cx in [x0 + (W * k / max(1, int(W / 6))) for k in range(int(W / 6) + 1)]:
        p.box((cx - 0.08, y1 + 2.3, 0.0), (cx + 0.08, y1 + 2.46, FL + H - 0.4), "steel")
    p.box((x0 - 0.3, y1 - 0.05, 0.0), (x1 + 0.3, y1 + 2.6, FL - 0.01), "sidewalk")
    for i, (st, bx0, bx1) in enumerate(fronts):
        text = (st.get("sign") or st.get("business") or "").upper().replace("·", "-").split(" - ")[0].strip()[:24]
        if not text:
            continue
        size = clamp((bx1 - bx0 - 0.8) / max(5, len(text)) * 1.4, 0.25, 1.2 if kind == "bigbox" else 0.5)
        g.text_mesh(b, f"sign_store{i}", text, size, ((bx0 + bx1) / 2, y1 + 2.63, FL + H - 0.35), math.pi,
                    "vinyl_red" if i % 2 == 0 else "letters_dark", extrude=0.05, font=FONT_SANS)
    # parking lot: asphalt, stall lines, light poles, a pylon sign with every tenant
    lotp = b.part("parking-col")
    lotp.box((-lot_w / 2, y1 + 2.6, -0.02), (lot_w / 2, lot_d / 2, 0.03), "asphalt", sides="Z")
    nst = int(W / 2.8)
    for k in range(nst + 1):
        sx = x0 + k * 2.8
        lotp.box((sx - 0.05, y1 + 4.0, 0.03), (sx + 0.05, y1 + 9.5, 0.035), "white_text")
    for k in range(max(1, int(lot_w / 25))):
        lx = -lot_w / 2 + 12.0 + k * 25.0
        lotp.cylinder((lx, lot_d / 2 - 3.0), 0.12, 0.0, 9.0, "steel", n=8)
        lotp.box((lx - 0.6, lot_d / 2 - 3.2, 9.0), (lx + 0.6, lot_d / 2 - 2.8, 9.2), "steel")
        b.empty("light_lot", (lx, lot_d / 2 - 3.0, 8.8))
    pyl_x = x1 - 2.0 if lot_w > 20 else x1 + 1.0
    pyl_y = lot_d / 2 - 1.5
    lotp.box((pyl_x - 0.25, pyl_y - 0.25, 0.0), (pyl_x + 0.25, pyl_y + 0.25, 6.0), "steel")
    title = (names.get("sign") or names.get("name") or "").upper()[:22]
    ph = 1.0 + 0.55 * min(6, len(fronts))
    lotp.box((pyl_x - 1.6, pyl_y - 0.2, 6.0), (pyl_x + 1.6, pyl_y + 0.2, 6.0 + ph), "white_text")
    if title:
        g.text_mesh(b, "sign_pylon", title, clamp(3.0 / max(6, len(title)) * 1.4, 0.15, 0.4), (pyl_x, pyl_y + 0.21, 6.0 + ph - 0.45), math.pi,
                    "vinyl_red", extrude=0.02, font=FONT_SANS)
    for i, (st, bx0, bx1) in enumerate(fronts[:6]):
        t = (st.get("business") or "FOR LEASE").upper()[:20]
        g.text_mesh(b, f"sign_pylon_{i}", t, 0.16, (pyl_x, pyl_y + 0.21, 6.0 + ph - 0.95 - i * 0.5), math.pi, "letters_dark",
                    extrude=0.01, font=FONT_SANS)
    if kind == "strip" and len(stores) == 1 and stores[0].get("type") in ("gas_station", "discount", "variety_store") and lot_d >= 14:
        # a pad store: fuel islands under a canopy in the lot
        cy_ = (y1 + 2.6 + lot_d / 2) / 2
        lotp.box((-4.5, cy_ - 2.5, 4.4), (4.5, cy_ + 2.5, 4.8), "canopy")
        for cx in (-3.5, 3.5):
            lotp.box((cx - 0.15, cy_ - 0.15, 0.0), (cx + 0.15, cy_ + 0.15, 4.4), "steel")
            fu.gas_pump(lotp, (cx, cy_ + 0.6, 0.1), 180, "vinyl_red", "white_text", "chrome_s", "black")
    return b


def bigbox_fitout(rnd, btype):
    def hook(house, room, p, against, rect, fz, cz):
        ctx = shopfit.Fit(house, room, p, against, rect, fz, cz, rnd)
        x0, y0, x1, y1 = rect
        # checkout lanes along the front
        for i in range(max(2, int((x1 - x0 - 20.0) / 3.0))):
            cx = x0 + 10.0 + i * 3.0
            ctx.island(cx, y1 - 5.0, 0.4, 1.2, lambda pos: _checkout(p, pos))
        # a grid of gondola runs across the floor, a main aisle in the middle
        runs = max(2, int((y1 - 8.0 - y0 - 2.0) / 3.0))
        for j in range(runs):
            yy = y0 + 2.5 + j * 3.0
            for xa, xb in ((x0 + 2.5, (x0 + x1) / 2 - 2.0), ((x0 + x1) / 2 + 2.0, x1 - 2.5)):
                L = xb - xa
                if L > 3.0:
                    ctx.island((xa + xb) / 2, yy, L / 2, 0.45, lambda pos, L=L, j=j: shopfit.gondola(p, pos, 0, L, 1.8, seed=400 + j))
        for k in range(4):
            ctx.wall(3.0, 0.7, True, lambda pos, yaw, k=k: shopfit.cooler(p, pos, yaw, 3.0, seed=410 + k), prefer=["S", "W", "E"])
    return hook


def _checkout(p, pos):
    f = fu.F(pos, 90)
    p.obox(f, (-1.2, -0.4, 0), (1.2, 0.4, 0.9), "formica")
    fu.cash_register(p, (pos[0] + 0.3, pos[1] + 0.8, pos[2] + 0.9), 90, "black", "chrome_s")


# ------------------------------------------------------------------ dispatch
def build(rec):
    kind = rec.get("kind")
    tr = rec.get("traits") or {}
    if kind == "tower":
        return build_tower(rec, tr)
    if kind in ("bigbox", "strip"):
        return build_retail(rec, tr)
    if kind == "vacant":
        former = tr.get("former") or {}
        if former.get("storefronts"):
            rec2 = dict(rec, kind="store", traits=dict(former, condition=tr.get("condition", "boarded")))
            return store.build(rec2, vacant=True)
        use = former.get("use", "factory")
        if use == "grain_elevator":
            return build_grain_elevator(rec, former, boarded=True)
        return build_works(rec, dict(former, colors=tr.get("colors") or former.get("colors")), boarded=True)
    if tr.get("use") == "grain_elevator":
        return build_grain_elevator(rec, tr)
    return build_works(rec, tr)
