"""
store.py -- a catalog record of kind 'store' (a commercial block of 1-3 storefronts) -> Building.

Layout (x across the lot, +y = street, origin at the lot centre).  The block fills the lot width
(party walls) and stops short of the rear alley.  Ground floor: one bay per storefront, each a
sales room (fit-out by business type, gen/shopfit.py) in front of a stock room with a WC and an
alley door.  With upper floors, a stair bay beside the storefronts has its own street door and a
straight flight (a second, parallel flight per extra storey); upstairs a cross-corridor at the
stair head serves front and rear rooms (apartments / offices / lodge hall / hotel rooms / storage).
"""
import math

from common import (Palette, brick_for, clamp, hexcol, lib_building, rng, std_materials, darken, g, FONT_SANS, FONT_SERIF,
                    sign_board)
import gbhouse as gh
import shopfit

TE, TI = 0.3, 0.12            # masonry fronts / party walls, frame partitions
STAIR_W = 1.05


def facade_materials(b, tr, cond):
    pal = Palette(b)
    col = tr.get("colors", {}) or {}
    trim = col.get("trim") or "#e8e2d2"
    std_materials(pal, trim=trim, door=col.get("accent") or "#3a2a1e")
    shopfit.shop_materials(pal)
    fac = tr.get("facade", "brick")
    body = col.get("body") or ("#8e4a36" if fac == "brick" else "#d8d0c0")
    wear = {"kept": 1.0, "worn": 0.9, "shabby": 0.78, "boarded": 0.7}.get(cond, 1.0)
    if fac in ("brick", "cast_iron_front"):
        pal.surf("facade", brick_for(hexcol(body)), rough=0.85)
    elif fac == "stone":
        pal.surf("facade", "limestone", rough=0.85)
    elif fac == "frame_false_front":
        pal.surf("facade", "drop_siding", darken(hexcol(body), wear), rough=0.7)
    elif fac == "block":
        pal.surf("facade", "block", rough=0.9)
    else:                                         # stucco, glass_modern
        pal.surf("facade", "stucco", darken(hexcol(body), wear), rough=0.8)
    pal.surf("party", "brick_common" if fac != "frame_false_front" else "drop_siding",
             darken(hexcol(body), wear) if fac == "frame_false_front" else None, rough=0.9)
    pal.surf("roof_m", "concrete", rough=0.95)
    pal.surf("tile", "roof_clay", rough=0.8)                  # (the California shore's pent roofs and copings)
    pal.surf("floor", "floor_maple" if tr.get("year_built", 1900) < 1940 else "vct", rough=0.45)
    pal.surf("plaster", "plaster", "#efe9dc", rough=0.85)
    pal.surf("ceiling", "tin_ceiling" if tr.get("year_built", 1900) < 1935 else "acoustic", rough=0.5)
    pal.surf("found", "limestone", rough=0.9)
    pal.surf("shopfront", "paint_gloss", col.get("accent") or "#2e3a2e", rough=0.35)
    pal.solid("awning", hexcol(col.get("accent") or "#7a2020"), rough=0.9)
    pal.solid("sign_board", hexcol(col.get("accent") or "#1e2a3a"), rough=0.5)
    pal.solid("gold", (0.8, 0.62, 0.22), rough=0.3, metal=0.9)
    pal.solid("neon_r", (1.0, 0.2, 0.15), emission=(1.0, 0.2, 0.15))
    pal.solid("neon_b", (0.3, 0.6, 1.0), emission=(0.3, 0.6, 1.0))
    pal.solid("roof_under", (0.5, 0.5, 0.48), rough=0.8)
    return pal


def build(rec, vacant=False):
    """vacant: a closed store (the record's `former` traits): display windows boarded, shop doors
    locked, stock rooms and upstairs emptied; the alley doors still open."""
    rid = rec["id"]
    tr = rec.get("traits", {}) or {}
    rnd = rng(rid)
    cond = tr.get("condition", "kept")
    if vacant:
        cond = rec.get("traits_condition", "boarded")
    lot = rec.get("lot", {"w": 19.3, "d": 23.6})
    lot_w, lot_d = lot["w"], lot["d"]
    fronts = (tr.get("storefronts") or [])[:3] or [{"business": "Main Street Mercantile", "type": "variety_store",
                                                    "sign": "MERCANTILE", "sign_style": "flat_board"}]
    # an office block (research/jobs: downtown lots turned to offices): 4-12 storeys, each floor one tenant (unit O<k>)
    office = tr.get("form") == "office_block"
    storeys = int(clamp(tr.get("storeys") or 2, 1, 12 if office else 3))
    upper = tr.get("upper_use") or ("apartments" if storeys > 1 else "none")
    if office:
        upper = "offices"
    if storeys == 1:
        upper = "none"
    year = tr.get("year_built", 1900)
    b = lib_building(rid)
    facade_materials(b, tr, cond)
    # ---- block rectangle
    W = min(lot_w - 0.1, 40.0 if office else 24.0)
    D = clamp(lot_d - 3.5, 10.0, 30.0 if office else 26.0)
    x0, x1 = -W / 2, W / 2
    y1 = lot_d / 2 - 0.3
    y0 = y1 - D
    FL1 = 0.2
    H1 = 4.0 if year < 1945 else 3.6
    HU = 3.3 if year < 1945 else 3.0
    floors = [(FL1, FL1 + H1)]
    for k in range(1, storeys):
        fz = floors[-1][1] + 0.35
        floors.append((fz, fz + HU))
    wall_top = floors[-1][1] + 0.3
    parapet = {"parapet_stepped": 1.4, "pediment": 1.2, "bracketed_metal": 0.9, "corbelled_brick": 0.9,
               "parapet_flat": 0.8, "none": 0.4}.get(tr.get("cornice", "parapet_flat"), 0.8)
    if tr.get("facade") == "frame_false_front":
        parapet = 2.2
    # ---- bays: stair bay (if upstairs) + storefront bays
    has_up = upper != "none"
    # stair bay against a party wall: wall + flight(s) + a 1.2 m passage (2 storeys) / second lane (3)
    stair_bay_w = TE + ((STAIR_W + 1.25) if storeys == 2 else (2 * STAIR_W + 0.35 if storeys >= 3 else 0.0))
    if not has_up:
        stair_bay_w = 0.0
    mirror = rnd.random() < 0.5
    if not mirror:
        sb = (x0, x0 + stair_bay_w)
        shops_x = (x0 + stair_bay_w, x1)
    else:
        sb = (x1 - stair_bay_w, x1)
        shops_x = (x0, x1 - stair_bay_w)
    n = len(fronts)
    bw = (shops_x[1] - shops_x[0]) / n
    if bw < 4.2 and n > 1:
        fronts = fronts[:max(1, int((shops_x[1] - shops_x[0]) / 4.2))]
        n = len(fronts)
        bw = (shops_x[1] - shops_x[0]) / n
    spec = dict(t_ext=TE, t_int=TI, era="old" if year < 1940 else "modern",
                mats=dict(ext="facade", int="plaster", roof="roof_m", roof_under="roof_under", found="found", floor="floor",
                          ceiling="ceiling", trim="trim", door="door", fascia="trim", porch="concrete", post="trim",
                          furn="furniture"),
                blocks=[dict(name="block", rect=(x0, y0, x1, y1), floors=floors, wall_top=wall_top, found_top=FL1 - 0.05,
                             roof=dict(type="flat", thick=0.3, parapet=parapet, coping="trim"))],
                rooms=[], doors=[], windows=[], stairs=[], rails=[], porches=[], chimneys=[], fireplaces=[])
    rooms, doors, wins = spec["rooms"], spec["doors"], spec["windows"]
    shop_d = D * 0.68
    ys = y1 - shop_d
    fronts_info = []
    for i, sf in enumerate(fronts):
        bx0 = shops_x[0] + bw * i
        bx1 = bx0 + bw
        name = f"SHOP{i}"
        btype = sf.get("type", "variety_store")
        rooms.append(dict(name=name, rect=(bx0, ys, bx1, y1), type="shop",
                          fitout=shopfit.fitout_for("vacant_storefront" if vacant else btype, rnd)))
        # stock room behind, with a WC in one rear corner: the stock room is the bay minus a 1.6 m
        # column; that column is an alcove open to it, with the WC at its alley end
        wc_w = 1.6
        wcx = (bx1 - wc_w, bx1) if i % 2 == 0 else (bx0, bx0 + wc_w)
        if bw >= 4.0 and ys - y0 >= 3.2:
            main_x = (bx0, wcx[0]) if i % 2 == 0 else (wcx[1], bx1)
            rooms.append(dict(name=f"BACK{i}", rect=(main_x[0], y0, main_x[1], ys), type="stock",
                              fitout=shopfit.fitout_for("stockroom", rnd)))
            rooms.append(dict(name=f"BACKX{i}", rect=(wcx[0], y0 + 1.7, wcx[1], ys), type=None, no_light=True,
                              open_plan_to=f"BACK{i}"))
            rooms.append(dict(name=f"WC{i}", rect=(wcx[0], y0, wcx[1], y0 + 1.7), type="bath", floor_mat="hextile"))
            doors.append(dict(name=f"wc{i}", at=((wcx[0] + wcx[1]) / 2, y0 + 1.7), w=0.7, swing_into=f"WC{i}"))
        else:
            rooms.append(dict(name=f"BACK{i}", rect=(bx0, y0, bx1, ys), type="stock", fitout=shopfit.fitout_for("stockroom", rnd)))
        doors.append(dict(name=f"shop{i}_back", at=((bx0 + bx1) / 2 + (0.8 if i % 2 == 0 else -0.8), ys), w=0.9,
                          swing_into=f"BACK{i}"))
        # storefront: centred glazed door (double when wide), display windows over bulkheads, transom band
        dcx = (bx0 + bx1) / 2
        dw = 1.6 if bw >= 6.0 else 0.95
        doors.append(dict(name=f"front{i}", at=(dcx, y1), w=dw, h=2.3, ext=True, leaves=2 if dw > 1.2 else 1,
                          glazed=(0.1, 0.3, 0.9, 0.92), panels=[(0.1, 0.06, 0.9, 0.26)], transom=0.5, locked=vacant))
        side_w = (bw - dw) / 2 - 0.55
        if side_w > 0.8:
            for sx in (-1, 1):
                cxw = dcx + sx * (dw / 2 + 0.3 + side_w / 2)
                wins.append(dict(at=(cxw, y1), w=side_w, sill=0.55, h=2.45, kind="picture", cols=max(1, int(side_w / 1.3)),
                                 casing=0.05))
        # alley door
        doors.append(dict(name=f"back{i}", at=((bx0 + bx1) / 2 + (-1.2 if i % 2 == 0 else 1.2), y0), w=0.9, ext=True))
        fronts_info.append((sf, bx0, bx1, dcx, dw))
    # interior walls between bays: rooms' shared edges make them; bays connect only for one business spanning two bays
    # ---- stair bay and upper floors
    if has_up:
        rooms.append(dict(name="STAIRHALL", rect=(sb[0], y0, sb[1], y1), type=None, no_furnish=True))
        sdx = (sb[0] + sb[1]) / 2
        doors.append(dict(name="street_up", at=(sdx if storeys == 3 else (sb[1] - 0.6 if not mirror else sb[0] + 0.6), y1), w=0.95,
                          ext=True, glazed=(0.15, 0.45, 0.85, 0.92), transom=0.5))
        doors.append(dict(name="stair_alley", at=(sdx, y0), w=0.9, ext=True))
        y_at = y1 - TE - 1.0                               # where the next flight starts
        for k in range(1, storeys):
            rise = floors[k][0] - floors[k - 1][0]
            nr = math.ceil(rise / 0.19)
            run = 0.25
            L = nr * run
            lane = (k - 1) % 2
            sx0 = (sb[0] + TE + 0.05 + lane * (STAIR_W + 0.2)) if not mirror else (sb[1] - TE - 0.05 - STAIR_W - lane * (STAIR_W + 0.2))
            if lane == 0:
                st = dict(start=(sx0, y_at), dir=(0, -1), width=STAIR_W, n=nr, run=run, floor=k - 1, to_floor=k,
                          rail_side="left" if not mirror else "right")
                y_at -= L
                if k == 1:
                    top_y = y_at
            else:
                # the next flight climbs back toward the street from the last one's head (the two lanes alternate up the
                # building); dir (0, 1): width runs toward -x from the start edge, so start on the lane's +x side
                st = dict(start=(sx0 + STAIR_W, y_at), dir=(0, 1), width=STAIR_W,
                          n=nr, run=run, floor=k - 1, to_floor=k, rail_side="right" if not mirror else "left")
                y_at += L
            spec["stairs"].append(st)
        # upper floors: corridor band at the first flight's head, rooms in front of and behind it
        cy1 = top_y
        cy0 = top_y - 1.4
        for k in range(1, storeys):
            rooms.append(dict(name=f"UHALL{k}", floor=k, rect=(sb[0], y0, sb[1], y1), type=None, no_furnish=True))
            ux0, ux1 = shops_x
            rooms.append(dict(name=f"UCOR{k}", floor=k, rect=(ux0, cy0, ux1, cy1), type=None, no_light=False,
                              open_plan_to=f"UHALL{k}"))
            nb = max(1, int((ux1 - ux0) / (6.5 if office else 5.0)))
            uw = (ux1 - ux0) / nb
            for j in range(nb):
                a0, a1 = ux0 + uw * j, ux0 + uw * (j + 1)
                ft_, bk_ = f"UF{k}_{j}", f"UB{k}_{j}"
                if upper == "offices":
                    rooms.append(dict(name=ft_, floor=k, rect=(a0, cy1, a1, y1), type="office",
                                      fitout=shopfit.fitout_for("office", rnd)))
                    rooms.append(dict(name=bk_, floor=k, rect=(a0, y0, a1, cy0), type="office",
                                      fitout=shopfit.fitout_for("office", rnd)))
                    if office:
                        rooms[-1]["unit"] = rooms[-2]["unit"] = f"O{k}"     # (the floor's one tenant)
                elif upper == "storage":
                    rooms.append(dict(name=ft_, floor=k, rect=(a0, cy1, a1, y1), type="stock",
                                      fitout=shopfit.fitout_for("stockroom", rnd)))
                    rooms.append(dict(name=bk_, floor=k, rect=(a0, y0, a1, cy0), type="stock",
                                      fitout=shopfit.fitout_for("stockroom", rnd)))
                elif upper == "hotel_rooms":
                    rooms.append(dict(name=ft_, floor=k, rect=(a0, cy1, a1, y1), type="bed"))
                    rooms.append(dict(name=bk_, floor=k, rect=(a0, y0, a1, cy0), type="bed"))
                else:           # apartments; a lodge hall takes the whole front instead
                    rooms.append(dict(name=ft_, floor=k, rect=(a0, cy1, a1, y1), type="living"))
                    rooms.append(dict(name=bk_, floor=k, rect=(a0, y0, a1, cy0), type="bed" if j % 2 else "kitchen",
                                      floor_mat=None if j % 2 else "lino"))
                doors.append(dict(name=f"uf{k}_{j}", floor=k, at=((a0 + a1) / 2, cy1), w=0.85, swing_into=ft_))
                doors.append(dict(name=f"ub{k}_{j}", floor=k, at=((a0 + a1) / 2, cy0), w=0.85, swing_into=bk_))
            if upper == "lodge_hall":
                # replace the front rooms of the top floor with one hall
                rooms[:] = [r for r in rooms if not (r.get("floor", 0) == k and r["name"].startswith("UF"))]
                doors[:] = [d for d in doors if not (d.get("floor", 0) == k and d["name"].startswith("uf"))]
                rooms.append(dict(name=f"LODGE{k}", floor=k, rect=(ux0, cy1, ux1, y1), type="lodge",
                                  fitout=shopfit.fitout_for("funeral_home", rnd)))
                doors.append(dict(name=f"lodge{k}", floor=k, at=((ux0 + ux1) / 2, cy1), w=1.6, leaves=2, swing_into=f"LODGE{k}"))
            # upper windows across the front and rear
            nwin = max(2, int(W / (1.8 if office else 2.2)))
            for j in range(nwin):
                wx = x0 + W * (j + 0.5) / nwin
                if office:
                    # an office floor's regular grid, front and back (Chicago windows on the old ones)
                    wins.append(dict(at=(wx, y1), floor=k, w=1.3, sill=0.8, h=2.0, kind="dh", cols=2 if year < 1945 else 1,
                                     head_cap=year < 1945))
                    wins.append(dict(at=(wx, y0), floor=k, w=1.3, sill=0.8, h=2.0, kind="dh", cols=1))
                    continue
                wins.append(dict(at=(wx, y1), floor=k, w=0.95, sill=0.75, h=1.9, kind="dh", cols=1, head_cap=True))
                if j % 2 == 0:
                    wins.append(dict(at=(wx, y0), floor=k, w=0.9, sill=0.8, h=1.6, kind="dh", cols=1))
        # well rails upstairs on the corridor side of each flight
        for st in spec["stairs"]:
            fl_up = st["to_floor"]
            L = st["n"] * st["run"]
            sx0_, sy0 = st["start"]
            if st["dir"][1] < 0:
                wx = sx0_ + STAIR_W + 0.03 if not mirror else sx0_ - 0.03
                spec["rails"].append(dict(floor=fl_up, pts=[(wx, sy0 - L + 0.05), (wx, sy0 - 0.05)]))
    # rear ground-floor windows (small, high)
    for (sf, bx0, bx1, dcx, dw) in fronts_info:
        wins.append(dict(at=((bx0 + bx1) / 2 + (1.0 if bx1 - bx0 > 5 else 0.0), y0), w=0.9, sill=1.4, h=1.0, kind="dh", cols=2))
    if vacant:
        # boarded: plywood over the display windows and the upper sashes, the upstairs emptied
        for r in rooms:
            if r.get("floor", 0) > 0 and r.get("type") is not None:
                r["type"] = None
                r.pop("fitout", None)
            elif r.get("floor", 0) == 0:
                r["locked"] = True           # behind the locked shop doors (the reach check skips light_locked_*)
    house = gh.House(b, spec)
    house.build()
    if vacant:
        ply = b.part("boards-col")
        for w_ in wins:
            if abs(w_["at"][1] - y1) < 0.01:
                fz = floors[w_.get("floor", 0)][0]
                cx_, hw_ = w_["at"][0], w_["w"] / 2 + 0.06
                ply.box((cx_ - hw_, y1 + 0.01, fz + w_["sill"] - 0.05), (cx_ + hw_, y1 + 0.05, fz + w_["sill"] + w_["h"] + 0.05), "plywood")
    facade_dressing(b, tr, rec, fronts_info, x0, x1, y0, y1, floors, wall_top, parapet, sb if has_up else None, rnd)
    site(b, lot_w, lot_d, x0, x1, y0, y1, rnd, [d["at"][0] for d in spec["doors"] if d.get("ext") and d["at"][1] < y0 + 0.01])
    return b


def _pent(p, x0, x1, y, z, depth, drop, mat, t=0.08):
    """a closed sloping slab from the wall line y (at height z) out to y + depth (z - drop): top, underside, ends, eave"""
    a, b_ = (x0, y, z), (x1, y, z)
    c, d = (x1, y + depth, z - drop), (x0, y + depth, z - drop)
    a2, b2, c2, d2 = [(q[0], q[1], q[2] - t) for q in (a, b_, c, d)]
    p.face([a, b_, c, d], mat)                     # top (the tiles)
    p.face([d2, c2, b2, a2], "trim")               # underside
    p.face([d, c, c2, d2], "trim")                 # eave edge
    p.face([a, d, d2, a2], "trim")                 # ends
    p.face([c, b_, b2, c2], "trim")
    p.face([b_, a, a2, b2], "trim")                # (against the wall)


def facade_dressing(b, tr, rec, fronts_info, x0, x1, y0, y1, floors, wall_top, parapet, sb, rnd):
    """Cornice, sign band + signs, awnings, pilasters, hours lettering."""
    p = b.part("facade_trim-col")
    H1 = floors[0][1]
    band0, band1 = H1 - 0.55, H1 + 0.25              # sign band between storefront head and upper floor
    cornice = tr.get("cornice", "parapet_flat")
    top = wall_top + parapet
    # storefront cornice (a projecting cap over the storefronts and the sign band)
    p.box((x0, y1, band1), (x1, y1 + 0.18, band1 + 0.14), "trim")
    # pilasters between bays
    for (sf, bx0, bx1, dcx, dw) in fronts_info:
        for x in (bx0, bx1):
            p.box((x - 0.22, y1, 0.0), (x + 0.22, y1 + 0.12, band0), "shopfront" if tr.get("facade") != "brick" else "facade")
    # main cornice
    if cornice == "bracketed_metal":
        p.box((x0 - 0.05, y1, top - 0.45), (x1 + 0.05, y1 + 0.45, top - 0.1), "trim")
        k = x0 + 0.3
        while k < x1 - 0.2:
            p.box((k - 0.08, y1, top - 0.85), (k + 0.08, y1 + 0.38, top - 0.45), "trim")
            k += 1.1
    elif cornice == "corbelled_brick":
        for i in range(3):
            p.box((x0, y1, top - 0.6 + i * 0.12), (x1, y1 + 0.05 + i * 0.05, top - 0.48 + i * 0.12), "facade")
    elif cornice == "parapet_stepped":
        cx = (x0 + x1) / 2
        p.box((cx - (x1 - x0) * 0.2, y1 - 0.3, top), (cx + (x1 - x0) * 0.2, y1, top + 0.6), "facade")
        p.box((cx - (x1 - x0) * 0.1, y1 - 0.3, top + 0.6), (cx + (x1 - x0) * 0.1, y1, top + 1.1), "facade")
    elif cornice == "pediment":
        cx = (x0 + x1) / 2
        hw = (x1 - x0) * 0.3
        p.face([(cx - hw, y1 + 0.02, top), (cx + hw, y1 + 0.02, top), (cx, y1 + 0.02, top + 1.2)], "trim")
    elif cornice == "mission_parapet":
        import institution
        institution.mission_parapet(p, x0, x1, y1, top, t=0.3, wall="facade")
    elif cornice == "tile_roof":
        # a clay-tile pent roof along the parapet (Santa Barbara's State Street): a closed slab, sloping out and down
        _pent(p, x0, x1, y1, top - 0.15, 1.0, 0.45, "tile")
    # signs
    font = FONT_SERIF if rec.get("traits", {}).get("year_built", 1900) < 1935 else FONT_SANS
    for i, (sf, bx0, bx1, dcx, dw) in enumerate(fronts_info):
        full = (sf.get("sign") or sf.get("business") or "").upper()
        parts = [t.strip() for t in full.replace(" -- ", " - ").split(" - ") if t.strip()]
        text = parts[0] if parts else full
        sub_text = " \u00b7 ".join(parts[1:])
        style = sf.get("sign_style", "flat_board")
        bwid = bx1 - bx0 - 0.6
        size = clamp(bwid / max(6, len(text)) * 1.35, 0.14, 0.42)
        lines = [(text, size)] + ([(sub_text, clamp(bwid / max(8, len(sub_text)) * 1.3, 0.07, size * 0.55))] if sub_text else [])
        frame = (g.Vector((dcx, y1 + 0.12, band0)), g.Vector((-1, 0, 0)), g.Vector((0, -1, 0)), g.Vector((0, 0, 1)))
        if style in ("flat_board", "painted_wall", "neon", "awning_lettering", "window_lettering"):
            sign_board(b, p, frame, lines, bwid, band1 - band0 - 0.05, "sign_board",
                       "neon_r" if style == "neon" else "gold", f"sign_front{i}", font=font)
        if style == "projecting":
            sign_board(b, p, frame, lines, bwid, band1 - band0 - 0.05, "sign_board", "gold", f"sign_front{i}", font=font)
            # blade sign on a bracket, lettered both faces
            bx = bx0 + 0.4
            p.box((bx - 0.03, y1, H1 + 0.9), (bx + 0.03, y1 + 1.3, H1 + 0.96), "iron")
            p.box((bx - 0.04, y1 + 0.2, H1 - 0.3), (bx + 0.04, y1 + 1.2, H1 + 0.85), "sign_board")
            for sgn, yaw in ((1, math.pi / 2), (-1, -math.pi / 2)):
                g.text_mesh(b, f"sign_blade{i}_{sgn}", text[:12], min(0.14, 0.95 / max(4, len(text[:12])) * 1.6), (bx + sgn * 0.045, y1 + 0.7, H1 + 0.25), yaw, "gold",
                            extrude=0.004, font=font)
        if sf.get("awning") or style == "awning_lettering":
            aw = b.part(f"awning{i}")
            q = [(bx0 + 0.25, y1 + 0.05, band0 - 0.05), (bx1 - 0.25, y1 + 0.05, band0 - 0.05),
                 (bx1 - 0.25, y1 + 1.4, band0 - 0.7), (bx0 + 0.25, y1 + 1.4, band0 - 0.7)]
            aw.face(q[::-1], "awning")
            aw.face(q, "awning")
            aw.box((bx0 + 0.25, y1 + 1.38, band0 - 0.95), (bx1 - 0.25, y1 + 1.42, band0 - 0.7), "awning")
            if style == "awning_lettering":
                g.text_mesh(b, f"sign_awning{i}", text[:24], 0.13, (dcx, y1 + 1.43, band0 - 0.9), math.pi, "white_text",
                            extrude=0.003, font=FONT_SANS)
        # hours / extra lettering on the door glass side panel
        extras = [e for e in (sf.get("extra_signs") or []) if isinstance(e, str)][:2]
        for j, e in enumerate(extras):
            g.text_mesh(b, f"sign_extra{i}_{j}", e[:30], 0.05, (dcx + dw / 2 + 0.55, y1 + 0.01, 1.5 - j * 0.1), math.pi,
                        "white_text", extrude=0.002, font=FONT_SANS)
        if style == "window_lettering":
            # gold leaf on the display-window glass (inside face), the sub-line under it
            wx = dcx - dw / 2 - 0.3 - max(0.8, (bx1 - bx0 - dw) / 4)
            g.text_mesh(b, f"sign_window{i}", text[:22], min(0.13, 1.6 / max(6, len(text[:22])) * 1.5), (wx, y1 - 0.02, 2.2),
                        math.pi, "gold", extrude=0.002, font=font)
            if sub_text:
                g.text_mesh(b, f"sign_window{i}b", sub_text[:34], 0.06, (wx, y1 - 0.02, 2.0), math.pi, "gold", extrude=0.002,
                            font=FONT_SANS)
    # building name / date block in the parapet
    nm = (rec.get("names") or {}).get("block_name") or ""
    yr = rec.get("traits", {}).get("year_built")
    if nm or yr:
        g.text_mesh(b, "sign_block", (nm.upper() + "  " if nm else "") + (str(yr) if yr else ""), 0.22,
                    ((x0 + x1) / 2, y1 + 0.02, wall_top + parapet * 0.35), math.pi, "trim", extrude=0.03, font=FONT_SERIF)


def site(b, lot_w, lot_d, x0, x1, y0, y1, rnd, rear_doors=()):
    """Sidewalk across the front, alley apron behind with trash cans (kept clear of the back doors)."""
    s = b.part("sidewalk-col")
    s.box((-lot_w / 2, y1, -0.02), (lot_w / 2, lot_d / 2, 0.12), "sidewalk", sides="Zy")
    a = b.part("alley-col")
    a.box((-lot_w / 2, -lot_d / 2, -0.02), (lot_w / 2, y0, 0.03), "concrete", sides="Z")
    placed = 0
    cx = x0 + 0.6
    while placed < 2 and cx < x1 - 0.6:
        if all(abs(cx - dx) > 1.3 for dx in rear_doors):
            a.cylinder((cx, y0 - 0.45), 0.3, 0.03, 0.95, "steel", n=12)
            placed += 1
            cx += 0.75
        else:
            cx += 0.4
