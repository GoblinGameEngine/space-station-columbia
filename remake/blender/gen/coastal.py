"""
coastal.py -- generators for the coastal kinds of CATALOG_SPEC_COASTAL.md.

  hotel / condo       mid- and high-rise lodging: a double-loaded corridor block (gbhouse spec), the
                      lower floors fitted out (lobby, restaurant or shops, guest rooms), the floors above
                      those sealed behind drawn curtains; balconies per the traits; roof sign.
  motel               rooms in a row, each with its own door off an open gallery; exterior stair;
                      office at one end; neon pylon / roof sign.
  arcade / stand /    one-storey boardwalk frontage buildings: an open (roll-up) front across the lot,
  kiosk / bait        arcade cabinets or a food counter inside, a full-width sign board, awning.
  pavilion            posts under a hip / pyramid roof, open sides, benches.
  lifeguard           a chair on a sled, or a hut on braced legs with a ramp.
  lighthouse          tapered banded tower, gallery, glazed lantern, optional keeper's house.
  ride                ferris wheel, go-kart speedway, wave swinger, drop tower, dark ride, carousel (no roller coasters).
  stack / monument    a boiler chimney; a column or obelisk.
  cannery, fishhouse, icehouse, shed, boatyard, warehouse
                      the works builder, stood on pile bents when on_pilings / over the water.

Everything founds deep (spec rule 4): building foundations go FOUND_DEPTH down (gbhouse) and
anything on piles carries them PILE_DEPTH below grade (the bed, where it's over the water).
Layout convention as the other generators: x across the lot, +y = the street / boardwalk front.
"""
import math

from common import (Palette, WALL_TEX, brick_for, clamp, darken, dget, hexcol, lib_building, rng, std_materials, g, FONT_SANS,
                    FONT_SERIF)
import gbhouse as gh
import institution as inst
import shopfit
import works

TE, TI = 0.3, 0.12
PILE_DEPTH = 12.0


# ------------------------------------------------------------------ materials
def materials(b, tr):
    pal = Palette(b)
    col = tr.get("colors", {}) or {}
    body = col.get("body") or "#e8e2d4"
    std_materials(pal, trim=col.get("trim") or "#f4f1e8", door=col.get("accent") or "#2f4a5a")
    shopfit.shop_materials(pal)
    walls = tr.get("walls", "stucco")
    if walls == "glass_curtain":
        pal.solid("ext", hexcol(body), rough=0.08, metal=0.6)
    else:
        tex = WALL_TEX.get(walls, "stucco")
        if walls == "brick":
            tex = brick_for(hexcol(body))
        pal.surf("ext", tex, hexcol(body), rough=0.8)
    pal.surf("plaster", "drywall", "#eeeeea", rough=0.85)
    rmat = dget(tr, "roof").get("material") if isinstance(tr.get("roof"), dict) else tr.get("roof")
    pal.surf("roof", "roof_asphalt", hexcol(col.get("roof") or "#6a6a66"), rough=0.85)
    if rmat in ("hip_tile", "tile"):
        pal.solid("roof", hexcol(col.get("roof") or "#b0582f"), rough=0.7)
    pal.surf("roof_m", "concrete", rough=0.95)
    pal.surf("floor", "carpet", "#6a6a78", rough=0.95)
    pal.surf("ceiling", "acoustic", rough=0.8)
    pal.surf("found", "concrete", rough=0.9)
    pal.surf("deck", "floor_painted", "#a09a90", rough=0.8)
    pal.surf("boards", "barn_board", "#9a8468", rough=0.85)
    pal.solid("roof_under", (0.5, 0.5, 0.48), rough=0.8)
    pal.solid("curtain", (0.32, 0.3, 0.28), rough=0.9)
    pal.solid("accent", hexcol(col.get("accent") or "#2f6f8f"), rough=0.5)
    pal.solid("sign_board", hexcol(col.get("accent") or "#1e2a3a"), rough=0.5)
    pal.solid("awning", hexcol(col.get("accent") or "#2f6f8f"), rough=0.9)
    pal.solid("pool", (0.2, 0.55, 0.75), rough=0.05)
    pal.solid("rail_white", (0.92, 0.92, 0.9), rough=0.4)
    pal.solid("pile", (0.36, 0.3, 0.24), rough=0.9)
    pal.solid("neon_r", (1.0, 0.2, 0.15), emission=(1.0, 0.25, 0.2))
    pal.solid("neon_b", (0.3, 0.6, 1.0), emission=(0.3, 0.6, 1.0))
    pal.solid("neon_y", (1.0, 0.85, 0.3), emission=(1.0, 0.85, 0.3))
    pal.solid("bulb", (1.0, 0.95, 0.8), emission=(1.0, 0.9, 0.7))
    pal.solid("gold", (0.8, 0.62, 0.22), rough=0.3, metal=0.9)
    return pal


def _spec(rect, floors, wall_top, roof, FL):
    return dict(t_ext=TE, t_int=TI, era="modern",
                mats=dict(ext="ext", int="plaster", roof="roof" if roof.get("type") != "flat" else "roof_m", roof_under="roof_under",
                          found="found", floor="floor", ceiling="ceiling", trim="trim", door="door", fascia="trim", porch="deck",
                          post="trim", furn="furniture"),
                blocks=[dict(name="main", rect=rect, floors=floors, wall_top=wall_top, found_top=FL - 0.05, roof=roof)],
                rooms=[], doors=[], windows=[], stairs=[], rails=[], porches=[], chimneys=[], fireplaces=[])


def _roof(tr, flat_default=True):
    r = tr.get("roof")
    if isinstance(r, dict):
        r = r.get("type")
    if r in ("hip", "hip_tile", "mansard"):
        return dict(type="hip", pitch=22 if r != "mansard" else 55, eave_oh=0.6, thick=0.2)
    if r in ("gable", "shed_angled", "butterfly") and not flat_default:
        return dict(type="gable", pitch=18, eave_oh=0.6, rake_oh=0.3, thick=0.15, ridge="x")
    return dict(type="flat", thick=0.35, parapet=0.9, coping="stone")


def _sign_text(b, name, text, x, y, z, width, mat="white_text", font=FONT_SANS, yaw=math.pi, max_size=1.2):
    if not text:
        return
    size = clamp(width / max(4, len(text)) * 1.5, 0.12, max_size)
    g.text_mesh(b, name, text[:40], size, (x, y, z), yaw, mat, extrude=0.03, font=font)


def _piles(p, rect, z_top, spacing=3.0, r=0.18, mat="pile"):
    """Pile bents under a deck: rows every `spacing` m, carried PILE_DEPTH below grade."""
    x0, y0, x1, y1 = rect
    nx = max(1, int((x1 - x0) / spacing))
    ny = max(1, int((y1 - y0) / spacing))
    for i in range(nx + 1):
        for j in range(ny + 1):
            px = x0 + 0.3 + (x1 - x0 - 0.6) * i / nx
            py = y0 + 0.3 + (y1 - y0 - 0.6) * j / ny
            p.cylinder((px, py), r, -PILE_DEPTH, z_top, mat, n=8)


# ------------------------------------------------------------------ hotels and condominiums
def build_lodging(rec):
    rid, tr, names = rec["id"], rec.get("traits", {}) or {}, rec.get("names", {}) or {}
    rnd = rng(rid)
    kind = rec.get("kind", "hotel")
    lot = rec.get("lot", {"w": 40.0, "d": 30.0})
    lot_w, lot_d = lot["w"], lot["d"]
    b = lib_building(rid)
    materials(b, tr)
    storeys = int(clamp(tr.get("storeys") or 4, 1, 24))
    form = tr.get("form", "slab")
    W = clamp(lot_w - 4.0, 10.0, 70.0)
    if form == "tower":
        W = min(W, 28.0)
    D = clamp(lot_d - 7.0, 9.0, 17.0)
    y1 = lot_d / 2 - 4.0
    y0 = y1 - D
    x0, x1 = -W / 2, W / 2
    FL, H = 0.45, 3.0
    floors = [(FL, FL + 3.8)]
    for _ in range(1, storeys):
        fz = floors[-1][1] + 0.35
        floors.append((fz, fz + H - 0.35))
    wall_top = floors[-1][1] + 0.35
    roof = _roof(tr)
    spec = _spec((x0, y0, x1, y1), floors, wall_top, roof, FL)
    n_int = storeys                             # every floor fitted out: every room has its guests (2026-10-07)
    nroom = max(2, int(W / 4.2))
    guest = [(1.0, "bed", "guest_room")] * nroom
    gf = tr.get("ground_floor", "lobby")
    if gf == "shops":
        g_front = [(1.0, "store", "souvenir"), (1.0, "store", "beachwear"), (1.0, "store", "ice_cream")]
    elif gf == "lobby_restaurant":
        g_front = [(2.0, "restaurant", "diner"), (1.0, "office", "motel")]
    else:
        g_front = [(1.0, "office", "motel"), (1.0, "bar", "bar")]
    bands = [(g_front, [(1.0, "office", "office"), (0.7, "bath", None), (1.0, "stock", "stockroom")])]
    for _ in range(1, n_int):
        bands.append((guest, guest))
    (c0, c1), _ = inst.corridor_plan(spec, (x0, y0, x1, y1), floors[:n_int], bands, rnd)
    spec["doors"].append(dict(name="main_entry", at=(0.0, y1), w=2.4, h=2.6, ext=True, leaves=2, glazed=(0.05, 0.05, 0.95, 0.95)))
    spec["doors"].append(dict(name="exit_w", at=(x0, (c0 + c1) / 2 + 0.6), w=1.0, ext=True, out=True))
    spec["doors"].append(dict(name="exit_e", at=(x1, (c0 + c1) / 2 + 0.6), w=1.0, ext=True, out=True))
    # balconies: every floor above the lobby, on the front; balcony doors out of the fitted-out rooms
    bal = tr.get("balconies", "none")
    bd = 1.6
    if bal != "none":
        for k in range(1, storeys):
            fz = floors[k][0]
            if bal == "continuous":
                segs = [(x0, x1)]
            else:
                pitch = W / nroom
                segs = [(x0 + pitch * i + 0.5, x0 + pitch * (i + 1) - 0.5) for i in range(nroom)]
            for (sa, sb) in segs:
                spec["porches"].append(dict(rect=(sa, y1, sb, y1 + bd), z=fz - 0.02, post_top=fz, posts=[], beam=False, skirt=False,
                                            rails=[[(sa, y1), (sa, y1 + bd), (sb, y1 + bd), (sb, y1)]], rail_mat="rail_white"))
            if k < n_int:
                for r in spec["rooms"]:
                    if r.get("floor") == k and r["rect"][3] >= y1 - 0.01 and r.get("type") == "bed":
                        cx = (r["rect"][0] + r["rect"][2]) / 2
                        spec["doors"].append(dict(name=f"bal_{r['name']}", floor=k, at=(cx, y1), w=0.9, ext=True,
                                                  glazed=(0.05, 0.05, 0.95, 0.95)))
    avoid = [(d["at"], d.get("floor", 0)) for d in spec["doors"]]
    inst.windows_all(spec, (x0, y0, x1, y1), floors, avoid, sill=0.6, h=1.8, spacing=2.1)
    inst.add_stoops(spec, FL)
    gh.House(b, spec).build()
    p = b.part("lodging_ext-col")
    # the sealed upper floors: a curtain box just inside the walls
    if storeys > n_int:
        z0 = floors[n_int][0]
        p.box((x0 + TE + 0.35, y0 + TE + 0.35, z0), (x1 - TE - 0.35, y1 - TE - 0.35, wall_top - 0.4), "curtain")
    # entrance canopy
    p.box((-3.0, y1, floors[0][1] - 0.6), (3.0, y1 + 3.2, floors[0][1] - 0.35), "accent")
    for sx in (-2.8, 2.8):
        p.cylinder((sx, y1 + 3.0), 0.08, 0.0, floors[0][1] - 0.6, "steel", n=8)
    # roof sign and rooftop pool
    sign = (names.get("sign") or names.get("name") or "").upper()
    top = wall_top + (0.9 if roof["type"] == "flat" else 0.3)
    if sign:
        sw = min(W - 2.0, 3.0 + len(sign) * 0.9)
        p.box((-sw / 2, y1 - 0.5, top), (sw / 2, y1 - 0.3, top + 2.4), "sign_board")
        _sign_text(b, "sign_roof", sign, 0.0, y1 - 0.29, top + 0.7, sw - 1.0, mat="neon_y", max_size=1.6)
    if tr.get("pool") == "rooftop" and roof["type"] == "flat":
        p.box((x0 + 2.0, y0 + 2.0, wall_top), (x0 + 12.0, y0 + 8.0, wall_top + 0.1), "pool")
    elif tr.get("pool") == "deck" and lot_d / 2 - y1 > 3.5:
        p.box((x1 - 12.0, y1 + 4.0, -0.3), (x1 - 2.0, min(lot_d / 2 - 0.5, y1 + 9.0), 0.02), "pool")
    _site_walk(b, 0.0, y1, lot_d, width=3.0)
    return b


# ------------------------------------------------------------------ apartment buildings ("condo": tools/settlegen's walk-ups)
def build_apartments(rec):
    """A walk-up apartment block (the user, 2026-10-07: every house needs residents, every room people): a double-loaded
    corridor on every floor, stairs at both ends, and the record's traits.units dwellings laid along it -- each a real
    home: kitchen and bath on the corridor side, a hall, the living room and 1-3 bedrooms on the windows.  Every room
    carries its unit ("A<floor><F|R><n>"); the entrance vestibule is mid-front on the ground floor."""
    rid, tr = rec["id"], rec.get("traits", {}) or {}
    rnd = rng(rid)
    lot = rec.get("lot", {"w": 40.0, "d": 30.0})
    lot_w, lot_d = lot["w"], lot["d"]
    b = lib_building(rid)
    materials(b, tr)
    storeys = int(clamp(tr.get("storeys") or 3, 1, 8))
    want = int(tr.get("units") or storeys * 4)
    W = clamp(lot_w - 4.0, 14.0, 70.0)
    D = clamp(lot_d - 7.0, 12.0, 17.0)
    y1 = lot_d / 2 - 4.0
    y0 = y1 - D
    x0, x1 = -W / 2, W / 2
    FL, H = 0.45, 3.0
    floors = [(FL, FL + H - 0.35)]
    for _ in range(1, storeys):
        fz = floors[-1][1] + 0.35
        floors.append((fz, fz + H - 0.35))
    wall_top = floors[-1][1] + 0.35
    roof = _roof(tr)
    spec = _spec((x0, y0, x1, y1), floors, wall_top, roof, FL)
    (c0, c1), _ = inst.corridor_plan(spec, (x0, y0, x1, y1), floors, [([], [])] * storeys, rnd)
    # the stairs stand in the corridor along its rear edge at both ends: no rear-band door there
    spans = []
    for st in spec["stairs"]:
        sx = st["start"][0]
        L = st["n"] * st["run"]
        spans.append((min(sx, sx + st["dir"][0] * L) - 1.0, max(sx, sx + st["dir"][0] * L) + 1.0))
    per_floor = max(2, math.ceil(want / storeys))
    side_n = max(1, math.ceil(per_floor / 2))
    VEST = 2.6
    rooms, doors = spec["rooms"], spec["doors"]
    made = 0
    for k in range(storeys):
        for band in ("F", "R"):
            if band == "F" and k == 0:
                segs = [(x0, -VEST / 2), (VEST / 2, x1)]
                rooms.append(dict(name="VEST", floor=0, rect=(-VEST / 2, c1, VEST / 2, y1), type="hall", open_plan_to="COR0"))
                n_seg = [max(1, side_n // 2), max(1, side_n - side_n // 2)]
            else:
                segs = [(x0, x1)]
                n_seg = [side_n]
            yc, ye = (c1, y1) if band == "F" else (c0, y0)
            sg = 1.0 if band == "F" else -1.0
            Dd = abs(ye - yc)
            ds = clamp(Dd * 0.34, 2.3, 2.8)                    # kitchen + bath strip on the corridor
            dh = 1.15                                          # the unit's hall
            for (sa, sb), n in zip(segs, n_seg):
                bw = (sb - sa) / n
                for i in range(n):
                    bx0, bx1 = sa + i * bw, sa + (i + 1) * bw
                    u = f"A{k}{band}{i + (0 if sa < 0 or k > 0 else n_seg[0])}"

                    def yr(a, c):                              # depth a..c from the corridor wall -> a y range
                        return (yc + sg * a, yc + sg * c) if sg > 0 else (yc + sg * c, yc + sg * a)
                    sy0, sy1 = yr(0.0, ds)
                    hy0, hy1 = yr(ds, ds + dh)
                    wy0, wy1 = yr(ds + dh, Dd)
                    # service strip: kitchen on the side whose corridor wall is clear of the stairs
                    kw = clamp(bw * 0.58, 2.4, bw - 1.8)
                    k_left = True
                    if band == "R":
                        mid_l, mid_r = bx0 + kw / 2, bx1 - kw / 2
                        if any(a_ < mid_l < b_ for a_, b_ in spans) and not any(a_ < mid_r < b_ for a_, b_ in spans):
                            k_left = False
                    kx = (bx0, bx0 + kw) if k_left else (bx1 - kw, bx1)
                    tx = (bx0 + kw, bx1) if k_left else (bx0, bx1 - kw)
                    nb = 1 if bw < 7.5 else (2 if bw < 10.5 else 3)
                    lw = max(3.6, bw * (0.42 if nb > 1 else 0.55))
                    while nb > 1 and (bw - lw) / nb < 2.7:
                        nb -= 1
                    rooms += [dict(name=f"{u}KIT", unit=u, floor=k, rect=(kx[0], sy0, kx[1], sy1), type="kitchen", floor_mat="lino"),
                              dict(name=f"{u}BATH", unit=u, floor=k, rect=(tx[0], sy0, tx[1], sy1), type="bath", floor_mat="hextile"),
                              dict(name=f"{u}HALL", unit=u, floor=k, rect=(bx0, hy0, bx1, hy1), type="hall"),
                              dict(name=f"{u}LR", unit=u, floor=k, rect=(bx0, wy0, bx0 + lw, wy1), type="living")]
                    bwid = (bw - lw) / nb
                    for j in range(nb):
                        rooms.append(dict(name=f"{u}BR{j + 1}", unit=u, floor=k, rect=(bx0 + lw + j * bwid, wy0, bx0 + lw + (j + 1) * bwid, wy1),
                                          type="bed"))
                    ex = (kx[0] + kx[1]) / 2
                    if band == "R" and any(a_ < ex < b_ for a_, b_ in spans):
                        ex = kx[1] - 0.7 if k_left else kx[0] + 0.7
                    e_hall, e_win = (hy0 if sg > 0 else hy1), (hy1 if sg > 0 else hy0)
                    doors += [dict(name=f"{u}entry", floor=k, at=(ex, yc), w=0.9, swing_into=f"{u}KIT", locked=True),
                              dict(name=f"{u}kit", floor=k, at=((kx[0] + kx[1]) / 2, e_hall), w=0.9, cased=True),
                              dict(name=f"{u}bath", floor=k, at=((tx[0] + tx[1]) / 2, e_hall), w=0.75, swing_into=f"{u}BATH"),
                              dict(name=f"{u}lr", floor=k, at=(bx0 + lw / 2, e_win), w=0.9, cased=True)]
                    for j in range(nb):
                        doors.append(dict(name=f"{u}br{j + 1}", floor=k, at=(bx0 + lw + (j + 0.5) * bwid, e_win), w=0.8,
                                          swing_into=f"{u}BR{j + 1}"))
                    made += 1
    if made < want:
        print(f"APARTMENTS {rid}: {made} of {want} units fit")
    spec["doors"].append(dict(name="main_entry", at=(0.0, y1), w=1.8, h=2.4, ext=True, leaves=2, glazed=(0.05, 0.05, 0.95, 0.95)))
    spec["doors"].append(dict(name="exit_w", at=(x0, (c0 + c1) / 2 + 0.6), w=1.0, ext=True, out=True))
    spec["doors"].append(dict(name="exit_e", at=(x1, (c0 + c1) / 2 + 0.6), w=1.0, ext=True, out=True))
    avoid = [(d["at"], d.get("floor", 0)) for d in spec["doors"]]
    inst.windows_all(spec, (x0, y0, x1, y1), floors, avoid, sill=0.9, h=1.4, spacing=2.4)
    inst.add_stoops(spec, FL)
    gh.House(b, spec).build()
    p = b.part("lodging_ext-col")
    p.box((-1.8, y1, floors[0][1] - 0.4), (1.8, y1 + 1.8, floors[0][1] - 0.2), "accent")      # entrance canopy
    _site_walk(b, 0.0, y1, lot_d, width=2.0)
    return b


def _site_walk(b, x, y1, lot_d, width=2.0):
    w = b.part("walk-col")
    w.box((x - width / 2, y1, -0.02), (x + width / 2, lot_d / 2, 0.03), "sidewalk", sides="Z")


# ------------------------------------------------------------------ motels
def build_motel(rec):
    rid, tr, names = rec["id"], rec.get("traits", {}) or {}, rec.get("names", {}) or {}
    rnd = rng(rid)
    lot = rec.get("lot", {"w": 48.0, "d": 36.0})
    lot_w, lot_d = lot["w"], lot["d"]
    b = lib_building(rid)
    materials(b, tr)
    storeys = int(clamp(tr.get("storeys") or 2, 1, 3))
    W = clamp(lot_w - 6.0, 12.0, 60.0)
    D = 8.5
    y1 = lot_d / 2 - 12.0 if lot_d > 26 else lot_d / 2 - 5.0           # a car court in front
    y0 = y1 - D
    x0, x1 = -W / 2, W / 2
    FL, H = 0.3, 2.7
    floors = [(FL, FL + H)]
    for _ in range(1, storeys):
        fz = floors[-1][1] + 0.35
        floors.append((fz, fz + H))
    wall_top = floors[-1][1] + 0.3
    roof = _roof(tr, flat_default=tr.get("roof") in ("flat", None))
    spec = _spec((x0, y0, x1, y1), floors, wall_top, roof, FL)
    n = max(2, int(W / 3.9))
    step = W / n
    for k in range(storeys):
        for i in range(n):
            rx0, rx1 = x0 + i * step, x0 + (i + 1) * step
            name = f"U{k}_{i}"
            office = (k == 0 and i == 0)
            spec["rooms"].append(dict(name=name, floor=k, rect=(rx0, y0, rx1, y1), type="office" if office else "bed", entry="N",
                                      fitout=shopfit.fitout_for("motel" if office else "guest_room", rnd)))
            spec["doors"].append(dict(name=f"d{name}", floor=k, at=(rx0 + step * 0.3, y1), w=0.9, ext=True, swing_into=name,
                                      locked=not office and rnd.random() < 0.5))
            spec["windows"].append(dict(at=(rx0 + step * 0.68, y1), floor=k, w=1.4, sill=0.9, h=1.2, kind="picture", cols=1))
            spec["windows"].append(dict(at=((rx0 + rx1) / 2, y0), floor=k, w=0.6, sill=1.5, h=0.6, kind="picture", cols=1))
    # the gallery: a walk at each level along the front, posts carrying the one above, a stair at the end
    gd = 1.8
    gal = tr.get("gallery", "front")
    for k in range(storeys):
        fz = floors[k][0]
        upper = k + 1 < storeys
        top = floors[k + 1][0] - 0.2 if upper else floors[k][1] + 0.1
        posts = [(x0 + 0.2 + (W - 0.4) * i / max(1, n), y1 + gd - 0.15) for i in range(n + 1)]
        po = dict(rect=(x0, y1, x1, y1 + gd), z=fz - 0.02, post_top=top, posts=posts, beam=True, post_w=0.14,
                  rails=[[(x0, y1 + gd), (x1, y1 + gd)]] if k > 0 else [], rail_mat="rail_white", skirt=k == 0)
        if not upper and roof["type"] != "flat":
            po["roof"] = dict(type="shed", high="S", high_z=top + 0.35, low_z=top + 0.05, oh=0.3)
        spec["porches"].append(po)
    gh.House(b, spec).build()
    if storeys > 1:
        for k in range(1, storeys):
            rise = floors[k][0] - floors[k - 1][0]
            nr = math.ceil(rise / 0.18)
            g.stairs(b, f"gallery_stair_{k}-col", (x1 + 0.05, y1 + 0.3 + (k - 1) * 1.1, floors[k - 1][0] - 0.02), (1, 0) if k % 2 else (-1, 0),
                     1.0, rise, nr, 0.27, "deck", "trim")
    p = b.part("motel_ext-col")
    # the sign: a neon pylon at the street, or a sign on the roof
    sign = (names.get("sign") or names.get("name") or "MOTEL").upper()
    style = tr.get("signage", "neon_pylon")
    if style == "neon_pylon":
        sx, sy = x0 + 1.5, lot_d / 2 - 1.2
        p.box((sx - 0.2, sy - 0.2, 0.0), (sx + 0.2, sy + 0.2, 6.0), "steel")
        p.box((sx - 2.6, sy - 0.25, 4.0), (sx + 2.6, sy + 0.25, 7.2), "sign_board")
        _sign_text(b, "sign_pylon", sign.split(" - ")[0], sx, sy + 0.26, 5.2, 4.8, mat="neon_r", yaw=math.pi)
        if "VACANCY" in sign:
            _sign_text(b, "sign_vacancy", "VACANCY", sx, sy + 0.26, 4.3, 2.4, mat="neon_b", yaw=math.pi)
    else:
        p.box((-5.0, y1 - 0.3, wall_top + 0.3), (5.0, y1 - 0.1, wall_top + 1.8), "sign_board")
        _sign_text(b, "sign_roof", sign.split(" - ")[0], 0.0, y1 - 0.09, wall_top + 0.8, 9.0, mat="neon_r")
    if tr.get("style") == "doo_wop":
        # the upswept roof blade over the office end and plastic palms by the pool
        p.face([(x0 - 1.0, y1 + gd + 1.0, wall_top + 0.3), (x0 + 6.0, y1 + gd + 1.0, wall_top + 2.8),
                (x0 + 6.0, y0 - 0.5, wall_top + 2.8), (x0 - 1.0, y0 - 0.5, wall_top + 0.3)], "accent")
    if tr.get("pool"):
        px0, py0 = x1 - 12.0, y1 + gd + 2.5
        p.box((px0, py0, -0.3), (px0 + 9.0, min(lot_d / 2 - 2.0, py0 + 5.0), 0.02), "pool")
    # the car court
    w = b.part("court-col")
    w.box((x0, y1 + gd, -0.02), (x1, lot_d / 2, 0.02), "asphalt", sides="Z")
    return b


# ------------------------------------------------------------------ boardwalk frontage: arcades, stands, kiosks
def build_stand(rec):
    rid, tr, names = rec["id"], rec.get("traits", {}) or {}, rec.get("names", {}) or {}
    rnd = rng(rid)
    kind = rec.get("kind", "stand")
    lot = rec.get("lot", {"w": 10.0, "d": 6.0})
    lot_w, lot_d = lot["w"], lot["d"]
    b = lib_building(rid)
    materials(b, tr)
    use = tr.get("use") or ("arcade" if kind == "arcade" else "food")
    shelter = use == "shelter"
    W = clamp(tr.get("width_m") or lot_w, 3.0, lot_w) - 0.6
    if kind == "kiosk":
        W = min(W, 5.0)
    D = clamp(lot_d - 0.6, 2.5, 14.0)
    x0, x1 = -W / 2, W / 2
    y1 = lot_d / 2 - 0.3
    y0 = y1 - D
    FL, H = 0.15, 3.4 if kind == "arcade" else 2.8
    floors = [(FL, FL + H)]
    wall_top = FL + H + 0.25
    roof = _roof(tr) if kind != "kiosk" else dict(type="hip", pitch=25, eave_oh=0.5, thick=0.15)
    spec = _spec((x0, y0, x1, y1), floors, wall_top, roof, FL)
    recipe = {"arcade": "arcade", "games": "arcade", "food": "snack_stand", "souvenir": "souvenir",
              "shelter": "lifeguard_hut"}.get(use, "variety_store")
    # a long frontage is split into bays (each its own concession), a stock room behind
    nb = max(1, int(W / 8.0)) if kind != "kiosk" else 1
    for i in range(nb):
        bx0, bx1 = x0 + W * i / nb, x0 + W * (i + 1) / nb
        rec_i = recipe if i == 0 or recipe == "arcade" else ["snack_stand", "souvenir", "arcade"][i % 3]
        spec["rooms"].append(dict(name=f"BAY{i}", rect=(bx0, y0, bx1, y1), type="store", entry="N",
                                  fitout=shopfit.fitout_for(rec_i, rnd)))
        if i > 0:
            spec["doors"].append(dict(name=f"bay{i}", at=(bx0, (y0 + y1) / 2), w=0.9, swing_into=f"BAY{i}"))
        # the open front: a wide roll-up opening (door with no leaf) or a service window over a counter
        if tr.get("open_front", True) and not shelter:
            spec["doors"].append(dict(name=f"front{i}", at=((bx0 + bx1) / 2, y1), w=min(bx1 - bx0 - 1.0, 6.0), h=2.6, ext=True,
                                      cased=True))
        else:
            spec["doors"].append(dict(name=f"front{i}", at=((bx0 + bx1) / 2, y1), w=0.9, ext=True, glazed=(0.1, 0.5, 0.9, 0.95)))
    spec["doors"].append(dict(name="back", at=(x0 + 1.2, y0), w=0.9, ext=True, out=True))
    gh.House(b, spec).build()
    p = b.part("stand_ext-col")
    # awning over the front and the sign board across the whole fascia
    p.face([(x0, y1 + 1.6, wall_top - 1.2), (x1, y1 + 1.6, wall_top - 1.2), (x1, y1, wall_top - 0.5), (x0, y1, wall_top - 0.5)], "awning")
    sign = (names.get("sign") or names.get("name") or "").upper()
    ss = tr.get("sign_style", "painted_board")
    board_h = 1.3 if kind == "arcade" else 1.0
    p.box((x0, y1, wall_top - 0.3), (x1, y1 + 0.25, wall_top + board_h), "sign_board")
    _sign_text(b, "sign_front", sign.split(" - ")[0], 0.0, y1 + 0.26, wall_top + 0.1, min(W - 1.0, 14.0),
               mat={"neon": "neon_r", "marquee": "neon_y"}.get(ss, "white_text"), max_size=0.9)
    if ss == "marquee":
        for i in range(int(W / 0.5)):
            p.cylinder((x0 + 0.25 + i * 0.5, y1 + 0.27), 0.06, wall_top + board_h - 0.12, wall_top + board_h - 0.02, "bulb", n=6)
            p.cylinder((x0 + 0.25 + i * 0.5, y1 + 0.27), 0.06, wall_top - 0.28, wall_top - 0.18, "bulb", n=6)
    if kind == "arcade":
        for i in range(max(1, int(W / 2.5))):
            b.empty(f"light_arcade_{i}", (x0 + 1.2 + i * 2.5, (y0 + y1) / 2, FL + H - 0.2))
    return b


def build_pavilion(rec):
    rid, tr, names = rec["id"], rec.get("traits", {}) or {}, rec.get("names", {}) or {}
    lot = rec.get("lot", {"w": 10.0, "d": 10.0})
    b = lib_building(rid)
    materials(b, tr)
    W = clamp(min(lot["w"], lot["d"]) - 1.0, 4.0, 40.0)
    p = b.part("pavilion-col")
    z = 0.45
    form = tr.get("form", "octagon")
    if form == "rectangle":
        hw, hd = (lot["w"] - 1.0) / 2, (lot["d"] - 1.0) / 2
    else:
        hw = hd = W / 2
    p.box((-hw, -hd, -1.5), (hw, hd, z), "deck")
    npost = 8 if form != "rectangle" else max(4, int(hw * 2 / 3.5))
    top = z + 3.2
    if form == "rectangle":
        pts = [(-hw + 0.3 + (2 * hw - 0.6) * i / (npost - 1), s * (hd - 0.3)) for i in range(npost) for s in (-1, 1)]
    else:
        pts = [(math.cos(a) * (hw - 0.3), math.sin(a) * (hd - 0.3)) for a in [i * math.pi * 2 / npost for i in range(npost)]]
    for (px, py) in pts:
        p.cylinder((px, py), 0.14, z, top, "trim", n=10)
    if tr.get("iron_lace"):
        for (px, py) in pts:
            p.box((px - 0.5, py - 0.05, top - 0.6), (px + 0.5, py + 0.05, top - 0.5), "iron")
    roof = tr.get("roof", "hip")
    if roof in ("dome", "pagoda") or form in ("octagon", "round"):
        g.pyramid_roof(p, 0.0, 0.0, max(hw, hd) + 0.6, top, top + (4.0 if roof == "pagoda" else 2.6), 0.0, "roof", "roof_under")
    else:
        gh.hip_roof(p, -hw - 0.5, hw + 0.5, -hd - 0.5, hd + 0.5, top, 28, 0.1, 0.15, "roof", "trim", "trim")
    g.stairs(b, "pav_step-col", (-0.6, -hd - 0.9, 0.0), (0, 1), 1.2, z, 3, 0.3, "deck")
    import gbfurn as fu
    for i, (px, py) in enumerate(pts[:6]):
        fu.bench(p, (px * 0.8, py * 0.8, z), math.degrees(math.atan2(py, px)) + 90, 1.4, "furniture")
    nm = (names.get("name") or "").upper()
    if nm:
        _sign_text(b, "sign_pav", nm, 0.0, hd + 0.1, top - 0.3, 2 * hw - 1.0, mat="black_text", max_size=0.3, font=FONT_SERIF)
    return b


# ------------------------------------------------------------------ lifeguard stands
def build_lifeguard(rec):
    rid, tr, names = rec["id"], rec.get("traits", {}) or {}, rec.get("names", {}) or {}
    b = lib_building(rid)
    pal = materials(b, tr)
    paint = dget(tr, "paint")
    pal.solid("cabin", hexcol(paint.get("cabin") or "#ffffff"), rough=0.6)
    pal.solid("legs", hexcol(paint.get("legs") or "#ffffff"), rough=0.7)
    pal.solid("ltrim", hexcol(paint.get("trim") or "#1f3f7a"), rough=0.5)
    p = b.part("lifeguard-col")
    if tr.get("type", "chair") == "chair":
        # the Jersey chair: a sled, a braced frame, a seat for two 2 m up, the umbrella socket
        for sx in (-0.8, 0.8):
            p.box((sx - 0.08, -1.2, 0.0), (sx + 0.08, 1.2, 0.15), "legs")
            p.box((sx - 0.07, -0.6, 0.15), (sx + 0.07, -0.46, 2.2), "legs")
            p.box((sx - 0.07, 0.46, 0.15), (sx + 0.07, 0.6, 2.0), "legs")
        for z in (0.6, 1.2):
            p.box((-0.8, 0.46, z), (0.8, 0.6, z + 0.12), "legs")
        p.box((-0.9, -0.6, 2.0), (0.9, 0.6, 2.08), "legs")
        p.box((-0.9, -0.62, 2.08), (0.9, -0.5, 2.9), "legs")
        _sign_text(b, "sign_chair", (names.get("sign") or "").split(" - ")[0][:14], 0.0, -0.63, 2.4, 1.6, mat="ltrim", yaw=0.0,
                   max_size=0.14)
        p.cylinder((0.0, -0.4), 0.03, 2.0, 4.2, "steel", n=6)
        g.pyramid_roof(p, 0.0, -0.4, 1.2, 3.9, 4.25, 0.0, "awning", "awning")
        for k in range(5):
            p.box((-0.6, 0.6 + k * 0.001, 0.3 + k * 0.4), (0.6, 0.75, 0.35 + k * 0.4), "legs")
        _piles(b.part("lifeguard_footing"), (-0.9, -1.2, 0.9, 1.2), -0.5, spacing=1.8, r=0.08, mat="legs")
        return b
    # the tower hut: braced legs, a platform with a rail, a cabin with windows, a roof, a ramp
    hz = 2.2
    for sx in (-1.2, 1.2):
        for sy in (-1.2, 1.2):
            p.cylinder((sx, sy), 0.1, -3.0, hz, "legs", n=8)
    for sx in (-1.2, 1.2):
        p.face([(sx, -1.2, 0.3), (sx, 1.2, hz - 0.3), (sx, 1.2, hz - 0.1), (sx, -1.2, 0.5)], "legs")
    p.box((-1.6, -1.6, hz), (1.6, 1.6, hz + 0.15), "deck")
    g.spindle_rail(p, [(-1.6, -1.6), (1.6, -1.6), (1.6, 1.6)], hz + 0.15, 1.0, 0.25, "ltrim")
    p.box((-1.1, -0.6, hz + 0.15), (1.1, 1.3, hz + 2.4), "cabin")
    p.box((-0.9, -0.62, hz + 1.2), (0.9, -0.6, hz + 2.0), "glass")
    p.box((1.1, -0.4, hz + 1.2), (1.12, 1.1, hz + 2.0), "glass")
    p.box((-1.12, -0.4, hz + 1.2), (-1.1, 1.1, hz + 2.0), "glass")
    num = str(tr.get("tower_number") or "")
    if num:
        g.text_mesh(b, "sign_num", num, 0.7, (0.0, 1.31, hz + 0.6), 0.0, "black_text", extrude=0.02, font=FONT_SANS)
    g.pyramid_roof(p, 0.0, 0.35, 1.7, hz + 2.4, hz + 3.1, 0.0, "ltrim", "cabin")
    if tr.get("ramp", True):
        g.stairs(b, "hut_stair-col", (-1.6, 1.6 + 0.0, 0.0), (0, -1), 0.9, hz, math.ceil(hz / 0.2), 0.3, "legs")
    return b


# ------------------------------------------------------------------ lighthouses
def build_lighthouse(rec):
    rid, tr, names = rec["id"], rec.get("traits", {}) or {}, rec.get("names", {}) or {}
    b = lib_building(rid)
    pal = materials(b, tr)
    paint = tr.get("paint") or {}
    if isinstance(paint, str):
        paint = {"body": paint}
    bands = paint.get("bands") or [paint.get("body") or "#ffffff", paint.get("band") or "#b02a2a"]
    for i, c in enumerate(bands[:4]):
        pal.solid(f"band{i}", hexcol(c) if isinstance(c, str) and c.startswith("#") else (0.9, 0.9, 0.88), rough=0.6)
    typ = tr.get("type", "conical_tower")
    Hh = clamp(tr.get("height_m") or 20.0, 6.0, 50.0)
    p = b.part("lighthouse-col")
    if typ == "skeletal":
        for a in range(4):
            ang = a * math.pi / 2 + math.pi / 4
            p.face([(math.cos(ang) * 3.0, math.sin(ang) * 3.0, 0.0), (math.cos(ang) * 1.0, math.sin(ang) * 1.0, Hh),
                    (math.cos(ang) * 1.1, math.sin(ang) * 1.1, Hh), (math.cos(ang) * 3.2, math.sin(ang) * 3.2, 0.0)], "band0")
            p.cylinder((math.cos(ang) * 3.0, math.sin(ang) * 3.0), 0.3, -8.0, 0.2, "found", n=8)
        p.cylinder((0, 0), 0.6, 0.0, Hh, "band1", n=10)
    else:
        r0, r1 = (Hh * 0.13, Hh * 0.08) if typ != "pierhead_cylinder" else (Hh * 0.1, Hh * 0.1)
        n = len(bands[:4]) if typ != "pierhead_cylinder" else 1
        segs = 8
        for k in range(segs):
            za, zb = Hh * k / segs, Hh * (k + 1) / segs
            ra, rb = r0 + (r1 - r0) * k / segs, r0 + (r1 - r0) * (k + 1) / segs
            p.cylinder((0, 0), ra, za, zb, f"band{k % n}", n=20, r1=rb)
        p.cylinder((0, 0), r0 + 1.0, -8.0, 0.3, "found", n=20)
        p.box((-0.5, -r0 - 0.05, 0.3), (0.5, -r0 + 0.05, 2.4), "door")
    # gallery, lantern, cap
    rg = (r1 if typ != "skeletal" else 1.2) + 0.9
    p.cylinder((0, 0), rg, Hh, Hh + 0.2, "iron", n=20)
    g.spindle_rail(p, [(math.cos(a) * rg, math.sin(a) * rg) for a in [i * math.pi * 2 / 16 for i in range(17)]], Hh + 0.2, 1.0, 0.3, "iron")
    if tr.get("lantern", True):
        rl = rg - 0.9
        p.cylinder((0, 0), rl, Hh + 0.2, Hh + 0.9, "iron", n=16)
        p.cylinder((0, 0), rl - 0.05, Hh + 0.9, Hh + 2.6, "glass", n=16)
        p.cylinder((0, 0), 0.35, Hh + 1.2, Hh + 2.2, "bulb", n=10)
        p.cylinder((0, 0), rl + 0.15, Hh + 2.6, Hh + 3.5, "iron", n=16, r1=0.1)
        b.empty("light_beacon", (0.0, 0.0, Hh + 1.7))
    if tr.get("keeper_house"):
        k = b.part("keeper-col")
        kx = rg + 5.0
        k.box((kx - 4.0, -3.5, -1.5), (kx + 4.0, 3.5, 3.2), "ext")
        gh.hip_roof(k, kx - 4.4, kx + 4.4, -3.9, 3.9, 3.2, 35, 0.1, 0.15, "roof", "trim", "trim")
        k.box((kx - 0.5, -3.52, 0.2), (kx + 0.5, -3.48, 2.3), "door")
    return b


# ------------------------------------------------------------------ amusement rides
def build_ride(rec):
    rid, tr, names = rec["id"], rec.get("traits", {}) or {}, rec.get("names", {}) or {}
    rnd = rng(rid)
    b = lib_building(rid)
    pal = materials(b, tr)
    pal.solid("ride_white", (0.92, 0.92, 0.9), rough=0.4, metal=0.3)
    pal.solid("ride_red", (0.75, 0.1, 0.1), rough=0.4)
    pal.solid("ride_blue", (0.12, 0.3, 0.7), rough=0.4)
    pal.solid("ride_yellow", (0.95, 0.75, 0.15), rough=0.4)
    typ = tr.get("type", "ferris_wheel")
    lot = rec.get("lot", {"w": 18.0, "d": 24.0})
    p = b.part("ride-col")
    # every ride stands on the pier deck: its own platform (pile-founded where over the water)
    hw, hd = lot["w"] / 2 - 0.5, lot["d"] / 2 - 0.5
    p.box((-hw, -hd, 0.0), (hw, hd, 0.3), "deck")
    if tr.get("pile_depth_m") or rec.get("over_water"):
        _piles(b.part("ride_piles"), (-hw, -hd, hw, hd), 0.0)
    cols = ["ride_red", "ride_blue", "ride_yellow", "ride_white"]
    if typ == "ferris_wheel":
        R = min(20.0, hd * 1.6)
        cz = R + 2.5
        for sx in (-2.0, 2.0):
            for sy in (-R * 0.45, R * 0.45):
                p.face([(sx, sy, 0.3), (sx, 0.0, cz), (sx, 0.0, cz + 0.4), (sx, sy + (0.5 if sy < 0 else -0.5), 0.3)], "ride_white")
        n = 24
        for i in range(n):
            a0, a1 = i * 2 * math.pi / n, (i + 1) * 2 * math.pi / n
            for sx in (-1.4, 1.4):
                rim = [(sx, math.cos(a0) * R, cz + math.sin(a0) * R), (sx, math.cos(a1) * R, cz + math.sin(a1) * R),
                       (sx, math.cos(a1) * (R - 0.5), cz + math.sin(a1) * (R - 0.5)), (sx, math.cos(a0) * (R - 0.5), cz + math.sin(a0) * (R - 0.5))]
                spoke = [(sx, 0.0, cz - 0.12), (sx, 0.0, cz + 0.12), (sx, math.cos(a0) * R, cz + math.sin(a0) * R + 0.12),
                         (sx, math.cos(a0) * R, cz + math.sin(a0) * R - 0.12)]
                for q in (rim, spoke):                      # both faces: the wheel is seen from either side
                    p.face(q, "ride_white")
                    p.face(q[::-1], "ride_white")
            gy, gz = math.cos(a0) * R, cz + math.sin(a0) * R
            p.box((-1.1, gy - 0.9, gz - 2.2), (1.1, gy + 0.9, gz - 0.4), cols[i % 4])
            p.box((-0.05, gy - 0.05, gz - 0.4), (0.05, gy + 0.05, gz), "steel")
            p.cylinder((1.45, math.cos(a0) * R), 0.12, gz - 0.05, gz + 0.05, "bulb", n=6)
        p.box((-1.6, -0.4, cz - 0.4), (1.6, 0.4, cz + 0.4), "steel")
    elif typ in ("go_karts", "coaster"):
        # a go-kart speedway (no roller coasters on the station): a figure-eight track of asphalt with a
        # tyre barrier and a low fence, a timing hut, a bulb-lit start gantry, karts in the pits
        pal.solid("tyre", (0.05, 0.05, 0.05), rough=0.9)
        R = min(hw, hd / 2) - 1.5
        for cyc in (-1, 1):
            cy = cyc * (hd - R - 1.0)
            n = 28
            for i in range(n):
                a0, a1 = i * 2 * math.pi / n, (i + 1) * 2 * math.pi / n
                ro, ri = R, R - 4.0
                q = [(math.cos(a0) * ro, cy + math.sin(a0) * ro, 0.32), (math.cos(a1) * ro, cy + math.sin(a1) * ro, 0.32),
                     (math.cos(a1) * ri, cy + math.sin(a1) * ri, 0.32), (math.cos(a0) * ri, cy + math.sin(a0) * ri, 0.32)]
                p.face(q[::-1], "asphalt")
                for rr in (ro + 0.3, ri - 0.3):
                    p.cylinder((math.cos(a0) * rr, cy + math.sin(a0) * rr), 0.3, 0.3, 0.75, "tyre", n=8)
                p.box((math.cos(a0) * (ro + 0.8) - 0.03, cy + math.sin(a0) * (ro + 0.8) - 0.03, 0.3),
                      (math.cos(a0) * (ro + 0.8) + 0.03, cy + math.sin(a0) * (ro + 0.8) + 0.03, 1.4), "chainlink")
        for k in range(6):
            kx, ky = -1.5 + (k % 3) * 1.4, -hd + 1.5 + (k // 3) * 2.0
            p.box((kx - 0.55, ky - 0.9, 0.35), (kx + 0.55, ky + 0.9, 0.75), cols[k % 4])
            p.box((kx - 0.3, ky - 0.1, 0.75), (kx + 0.3, ky + 0.4, 1.0), "black")
        p.box((hw - 3.5, -1.5, 0.3), (hw - 0.5, 1.5, 2.8), "ext")
        p.box((hw - 3.6, -1.6, 2.8), (hw - 0.4, 1.6, 3.0), "accent")
        for sx in (-R + 0.5, -R + 4.5):
            p.box((sx - 0.1, -0.1, 0.3), (sx + 0.1, 0.1, 4.0), "ride_white")
        p.box((-R + 0.4, -0.2, 3.8), (-R + 4.6, 0.2, 4.4), "ride_red")
        for i in range(8):
            p.cylinder((-R + 0.7 + i * 0.5, 0.22), 0.07, 4.0, 4.15, "bulb", n=6)
    elif typ == "swings":
        H = 12.0
        p.cylinder((0, 0), 0.6, 0.3, H, "ride_white", n=12)
        p.cylinder((0, 0), 5.5, H, H + 1.2, "ride_yellow", n=24, r1=1.0)
        for i in range(24):
            a = i * 2 * math.pi / 24
            x, y = math.cos(a) * 6.0, math.sin(a) * 6.0
            p.box((x - 0.02, y - 0.02, H - 5.0), (x + 0.02, y + 0.02, H), "steel")
            p.box((x - 0.3, y - 0.3, H - 5.3), (x + 0.3, y + 0.3, H - 5.0), cols[i % 4])
            p.cylinder((math.cos(a) * 5.4, math.sin(a) * 5.4), 0.1, H + 0.1, H + 0.3, "bulb", n=6)
        p.cylinder((0, 0), 7.5, 0.3, 0.6, "deck", n=24)
    elif typ == "drop_tower":
        H = 45.0
        for a in range(3):
            ang = a * 2 * math.pi / 3
            p.box((math.cos(ang) * 0.8 - 0.2, math.sin(ang) * 0.8 - 0.2, 0.3), (math.cos(ang) * 0.8 + 0.2, math.sin(ang) * 0.8 + 0.2, H), "ride_white")
        p.cylinder((0, 0), 2.2, 6.0, 7.2, "ride_red", n=16)
        for i in range(12):
            a = i * 2 * math.pi / 12
            p.box((math.cos(a) * 2.4 - 0.3, math.sin(a) * 2.4 - 0.3, 5.5), (math.cos(a) * 2.4 + 0.3, math.sin(a) * 2.4 + 0.3, 7.0), "ride_blue")
        for k in range(10):
            p.cylinder((0, 0), 1.05, 4.0 + k * 4.2, 4.2 + k * 4.2, "bulb", n=10)
        p.cylinder((0, 0), 1.4, H, H + 2.0, "ride_red", n=12, r1=0.5)
    elif typ == "carousel":
        R = min(hw, hd) - 0.5
        p.cylinder((0, 0), R, 0.3, 0.7, "deck", n=28)
        p.cylinder((0, 0), 1.2, 0.7, 4.2, "mirror", n=12)
        for i in range(36):
            a = i * 2 * math.pi / 36
            rr = R - 1.0 - (i % 3) * 1.4
            x, y = math.cos(a) * rr, math.sin(a) * rr
            p.cylinder((x, y), 0.04, 0.7, 4.2, "gold", n=6)
            p.box((x - 0.15, y - 0.55, 1.5 + (i % 2) * 0.3), (x + 0.15, y + 0.55, 2.2 + (i % 2) * 0.3), cols[i % 4])
        p.cylinder((0, 0), R + 0.3, 4.2, 4.8, "ride_red", n=28)
        g.pyramid_roof(p, 0.0, 0.0, R + 0.3, 4.8, 7.0, 0.0, "ride_yellow", "ride_white")
        for i in range(28):
            a = i * 2 * math.pi / 28
            p.cylinder((math.cos(a) * (R + 0.32), math.sin(a) * (R + 0.32)), 0.08, 4.4, 4.6, "bulb", n=6)
    else:                                       # dark ride: a show building with a painted facade
        W, D = hw * 2 - 1.0, hd * 2 - 1.0
        p.box((-W / 2, -D / 2, 0.3), (W / 2, D / 2, 8.0), "ext")
        p.face([(-W / 2 - 1.0, D / 2 + 0.3, 0.3), (W / 2 + 1.0, D / 2 + 0.3, 0.3), (W / 2 + 2.0, D / 2 + 0.3, 11.0), (0.0, D / 2 + 0.3, 13.0),
                (-W / 2 - 2.0, D / 2 + 0.3, 11.0)][::-1], "accent")
        for sx in (-W / 4, W / 4):
            p.box((sx - 1.2, D / 2 + 0.25, 0.3), (sx + 1.2, D / 2 + 0.35, 2.8), "black")
        nm = (names.get("name") or "").upper()
        _sign_text(b, "sign_dark", nm, 0.0, D / 2 + 0.36, 8.5, W, mat="neon_y", yaw=math.pi, max_size=1.2)
    return b


def build_stack(rec):
    rid, tr = rec["id"], rec.get("traits", {}) or {}
    b = lib_building(rid)
    pal = materials(b, tr)
    Hh = clamp(tr.get("height_m") or 30.0, 8.0, 80.0)
    p = b.part("stack-col")
    mat = "stack_m"
    if tr.get("material", "brick") == "brick":
        pal.surf(mat, "brick_common", rough=0.85)
    else:
        pal.solid(mat, (0.4, 0.4, 0.4), rough=0.6, metal=0.4)
    p.box((-2.2, -2.2, -4.0), (2.2, 2.2, 1.5), "found")
    p.cylinder((0, 0), 1.6, 1.5, Hh, mat, n=16, r1=1.0)
    p.cylinder((0, 0), 1.25, Hh, Hh + 0.6, mat, n=16)
    return b


def build_monument(rec):
    rid, tr, names = rec["id"], rec.get("traits", {}) or {}, rec.get("names", {}) or {}
    b = lib_building(rid)
    materials(b, tr)
    Hh = clamp(tr.get("height_m") or 20.0, 3.0, 110.0)
    p = b.part("monument-col")
    p.box((-6.0, -6.0, -3.0), (6.0, 6.0, 0.6), "stone")
    p.box((-4.5, -4.5, 0.6), (4.5, 4.5, 1.2), "stone")
    if tr.get("type", "column") == "obelisk":
        p.cylinder((0, 0), 2.6, 1.2, Hh * 0.93, "stone", n=4, r1=1.8)
        g.pyramid_roof(p, 0.0, 0.0, 1.3, Hh * 0.93, Hh, 0.0, "stone", "stone")
    else:
        p.box((-3.2, -3.2, 1.2), (3.2, 3.2, 6.0), "stone")
        p.cylinder((0, 0), 2.2, 6.0, Hh - 5.0, "stone", n=24, r1=1.9)
        p.box((-2.8, -2.8, Hh - 5.0), (2.8, 2.8, Hh - 3.8), "stone")
        p.cylinder((0, 0), 1.3, Hh - 3.8, Hh - 1.0, "stone", n=16)
        p.cylinder((0, 0), 1.0, Hh - 1.0, Hh, "bulb", n=16, r1=0.6)
    nm = (names.get("name") or "").upper()
    _sign_text(b, "sign_mon", nm, 0.0, -4.52, 0.7, 8.0, mat="black_text", yaw=0.0, max_size=0.35, font=FONT_SERIF)
    return b


# ------------------------------------------------------------------ waterfront industry
def build_waterfront_works(rec):
    tr = dict(rec.get("traits") or {})
    use = tr.get("use") or rec.get("kind")
    tr.setdefault("components", [])
    if rec.get("kind") == "stack":
        return build_stack(rec)
    b = works.build_works(rec, tr)
    if tr.get("on_pilings") or rec.get("over_water"):
        lot = rec.get("lot", {"w": 20.0, "d": 20.0})
        hw, hd = lot["w"] / 2 - 0.3, lot["d"] / 2 - 0.3
        Palette(b).solid("pile", (0.36, 0.3, 0.24), rough=0.9)
        _piles(b.part("works_piles"), (-hw, -hd, hw, hd), 0.2)
    return b


# ------------------------------------------------------------------ dispatch
def build(rec):
    kind = rec.get("kind")
    if kind == "condo":
        return build_apartments(rec)
    if kind == "hotel":
        return build_lodging(rec)
    if kind == "motel":
        return build_motel(rec)
    if kind in ("arcade", "stand", "kiosk", "bait"):
        return build_stand(rec)
    if kind in ("pavilion", "bandstand"):
        return build_pavilion(rec)
    if kind == "lifeguard":
        return build_lifeguard(rec)
    if kind == "lighthouse":
        return build_lighthouse(rec)
    if kind == "ride":
        return build_ride(rec)
    if kind == "monument":
        return build_monument(rec)
    return build_waterfront_works(rec)
