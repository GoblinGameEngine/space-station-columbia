"""
townhouse.py -- catalog records of kind 'townhouse' -> Building: a row of attached two-storey town houses (the
"missing middle" of research/urban_layout/01_zoning.md; Calder's newest streets mix them in -- tools/settlegen/town.py).

Plan (x across the lot, +y = street, origin at the lot centre): one block holds `units` houses side by side behind
party walls. Each unit has a 1.0 m stair hall along its party wall from the front door to the back, the living room
in front and the kitchen behind downstairs; upstairs a front bedroom, a bath, and a back bedroom. A stoop at every
door, a front walk per unit, a gable roof along the row.

Traits: units (2-8), unit_w_ft, depth_ft, walls, colors{body, trim, accent, roof}, roof{pitch_deg}, year_built,
condition.
"""
import math

from common import clamp, dget, lib_building, rng
import gbhouse as gh
import house as H

TE, TI = 0.15, 0.1
STAIR_W = 0.95


def build(rec):
    rid = rec["id"]
    tr = rec.get("traits", {}) or {}
    rnd = rng(rid)
    lot = rec.get("lot", {"w": 42.0, "d": 20.0})
    lot_w, lot_d = lot["w"], lot["d"]
    n = int(clamp(tr.get("units") or 6, 2, 8))
    uw = clamp((tr.get("unit_w_ft") or 22) * 0.3048, 5.6, (lot_w - 2.0) / n)
    D = clamp((tr.get("depth_ft") or 36) * 0.3048, 8.5, max(8.5, lot_d - 6.0))
    W = uw * n
    b = lib_building(rid)
    H.house_materials(b, tr, tr.get("condition", "kept"))
    fl1, h = 0.45, 2.6
    floors = [(fl1, fl1 + h), (fl1 + h + 0.3, fl1 + 2 * h + 0.2)]
    wall_top = floors[-1][1] + 0.12
    y1 = lot_d / 2 - 3.2                      # the stoops and a short front yard
    y0 = y1 - D
    x0 = -W / 2
    pitch = clamp(dget(tr, "roof").get("pitch_deg") or 30, 18, 45)
    roof = dict(type="gable", pitch=pitch, eave_oh=0.4, rake_oh=0.25, thick=0.15, ridge="x")
    spec = dict(t_ext=TE, t_int=TI, era="modern",
                mats=dict(ext="siding", int="plaster", roof="roof", roof_under="roof_under", found="found", floor="floor",
                          ceiling="plaster", trim="trim", door="door", fascia="trim", porch="porch", post="trim", furn="furniture"),
                blocks=[dict(name="main", rect=(x0, y0, x0 + W, y1), floors=floors, wall_top=wall_top, found_top=fl1 - 0.05,
                             roof=roof)],
                rooms=[], doors=[], windows=[], stairs=[], rails=[], porches=[], chimneys=[], fireplaces=[])
    rooms, doors, wins = spec["rooms"], spec["doors"], spec["windows"]
    rise = floors[1][0] - floors[0][0]
    ns = max(12, math.ceil(rise / 0.19))
    run = clamp((D - 2 * TE - 2.0) / ns, 0.22, 0.26)
    ym = y0 + D * 0.48
    yb = ym - 2.2                             # the upstairs bath behind the front bedroom
    for k in range(n):
        ux0, ux1 = x0 + uw * k, x0 + uw * (k + 1)
        mirror = k % 2 == 1                   # (mirror pairs: the stair halls share the party wall between them)
        if not mirror:
            hx0, hx1 = ux0, ux0 + STAIR_W + 0.1
            rx0, rx1 = hx1, ux1
        else:
            hx0, hx1 = ux1 - STAIR_W - 0.1, ux1
            rx0, rx1 = ux0, hx0
        sx = hx0 + 0.05 if not mirror else hx1 - 0.05 - STAIR_W
        spec["stairs"].append(dict(start=(sx, y1 - TE - 1.0), dir=(0, -1), width=STAIR_W, n=ns, run=run, floor=0, to_floor=1,
                                   rail_side="right" if not mirror else "left"))
        u = f"U{k}"
        rooms += [dict(name=f"{u}HALL", unit=u, rect=(hx0, y0, hx1, y1), type="hall"),
                  dict(name=f"{u}LR", unit=u, rect=(rx0, ym, rx1, y1), type="living"),
                  dict(name=f"{u}KIT", unit=u, rect=(rx0, y0, rx1, ym), type="kitchen", floor_mat="lino"),
                  dict(name=f"{u}HALL1", unit=u, floor=1, rect=(hx0, y0, hx1, y1), type="hall"),
                  dict(name=f"{u}BR1", unit=u, floor=1, rect=(rx0, ym, rx1, y1), type="bed"),
                  dict(name=f"{u}BATH", unit=u, floor=1, rect=(rx0, yb, rx1, ym), type="bath", floor_mat="hextile"),
                  dict(name=f"{u}BR2", unit=u, floor=1, rect=(rx0, y0, rx1, yb), type="bed")]
        dx = hx1 if not mirror else hx0               # the hall's room-side wall
        doors += [dict(name=f"{u}front", at=((hx0 + hx1) / 2, y1), w=0.9, ext=True, glazed=(0.2, 0.55, 0.8, 0.9)),
                  dict(name=f"{u}back", at=((rx0 + rx1) / 2, y0), w=0.85, ext=True, glazed=(0.15, 0.5, 0.85, 0.9)),
                  dict(name=f"{u}lr", at=(dx, ym + min(1.4, (y1 - ym) / 2)), w=0.9, cased=True),
                  dict(name=f"{u}kit", at=(dx, y0 + min(1.2, (ym - y0) / 2)), w=0.85, swing_into=f"{u}KIT"),
                  dict(name=f"{u}br1", floor=1, at=(dx, ym + 0.9), w=0.8, swing_into=f"{u}BR1"),
                  dict(name=f"{u}bath", floor=1, at=(dx, (yb + ym) / 2), w=0.75, swing_into=f"{u}BATH"),
                  dict(name=f"{u}br2", floor=1, at=(dx, y0 + 1.0), w=0.8, swing_into=f"{u}BR2")]
        # windows: the room side of the front and back walls, both floors; the end units' side walls too
        cx = (rx0 + rx1) / 2
        for fk in (0, 1):
            wins.append(dict(at=(cx, y1), floor=fk, w=min(1.6, rx1 - rx0 - 1.0) if fk == 0 else 1.0, sill=0.9, h=1.4, kind="dh", cols=2))
            wins.append(dict(at=(cx + (0.9 if fk == 0 else 0.0), y0), floor=fk, w=0.9, sill=1.0, h=1.2, kind="dh", cols=2))
        for side_x, end in ((x0, k == 0), (x0 + W, k == n - 1)):
            if end:
                for fk in (0, 1):
                    wins.append(dict(at=(side_x, (y0 + ym) / 2 + 0.5), floor=fk, w=0.9, sill=0.9, h=1.3, kind="dh", cols=2))
                    wins.append(dict(at=(side_x, (ym + y1) / 2), floor=fk, w=0.9, sill=0.9, h=1.3, kind="dh", cols=2))
    # a stoop at every door
    for d in doors:
        if not d.get("ext"):
            continue
        x, y = d["at"]
        oy = 1 if abs(y - y1) < 0.01 else -1
        spec["porches"].append(dict(rect=(x - 0.85, min(y, y + oy * 1.3), x + 0.85, max(y, y + oy * 1.3)), z=fl1 - 0.02, post_top=fl1,
                                    posts=[], beam=False, skirt_mat="found",
                                    steps=dict(at=(x, y + oy * 1.3), dir=(0, oy), width=1.3, mat="found")))
    gh.House(b, spec).build()
    # front walks to the sidewalk
    p = b.part("walks-col")
    for d in doors:
        if d.get("ext") and abs(d["at"][1] - y1) < 0.01:
            x = d["at"][0]
            p.box((x - 0.55, y1 + 1.9, -0.02), (x + 0.55, lot_d / 2, 0.03), "sidewalk", sides="Z")
    return b
