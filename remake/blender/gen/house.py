"""
house.py -- a catalog record of kind 'house' (or a farmstead's farmhouse) -> gbhouse spec -> Building.

Plans (x across the lot, +y toward the street, origin at the lot centre):
  * storeys >= 1.5: SIDE-HALL plan.  A 2.2 m hall along one side wall holds a straight stair
    (1 m) with a 1.2 m corridor beside it the full depth on both floors; rooms fill the rest of
    the width in one or two columns.  Two columns get an upstairs cross-corridor so every bedroom
    opens off a hall.  A plan too shallow for a straight flight uses a dog-leg filling the hall.
  * storeys == 1: HALL plan.  Living room + kitchen in one column, a 1.1 m hall, bedrooms and a
    bath in the other; narrow houses (< 7.5 m) get a SHOTGUN line of rooms.
Stairs always keep 0.9 m clear landings at foot and head (gbhouse.check_stairs warns otherwise).
"""
import math

from common import (dget, FT, WALL_TEX, ROOF_TEX, FOUND_TEX, Palette, brick_for, clamp, hexcol, lib_building, rng,
                    std_materials, ft, lum, darken, g, FONT_SANS)
import gbhouse as gh

TE, TI = 0.15, 0.1
HALL_W = 2.2
STAIR_W = 1.0


# ------------------------------------------------------------------ materials
def house_materials(b, tr, cond):
    pal = Palette(b)
    col = tr.get("colors", {}) or {}
    body = col.get("body") or "#e8e2d4"
    trim = col.get("trim") or "#f4f1e8"
    accent = col.get("accent") or "#4a5a48"
    roofc = col.get("roof") or "#555350"
    std_materials(pal, trim=trim, door=accent if lum(hexcol(accent)) < 0.6 else "#5a3a26")
    walls = tr.get("walls", "clapboard")
    tex = WALL_TEX.get(walls, "clapboard")
    if walls == "brick":
        tex = brick_for(hexcol(body))
    wear = {"kept": 1.0, "worn": 0.9, "shabby": 0.78, "boarded": 0.7}.get(cond, 1.0)
    tint = darken(hexcol(body), wear)
    pal.surf("siding", tex, tint, rough=0.7)
    rtex = ROOF_TEX.get(dget(tr, "roof").get("material", "asphalt_shingle"), "roof_asphalt")
    pal.surf("roof", rtex, darken(hexcol(roofc), wear), rough=0.85)
    pal.surf("found", FOUND_TEX.get(tr.get("foundation", "concrete_block"), "block"), rough=0.9)
    pal.surf("shutter", "paint", accent, rough=0.5)
    pal.surf("porch", "floor_painted", "#8a8a84" if cond != "kept" else "#9a9892", rough=0.7)
    era = tr.get("year_built", 1920)
    pal.surf("floor", "floor_oak" if era < 1945 else "floor_maple", rough=0.45)
    pal.surf("plaster", "plaster" if era < 1945 else "drywall", "#f1ece0" if era < 1945 else "#eeeeea", rough=0.85)
    pal.surf("carpet", "carpet", "#8a7e6a", rough=0.95)
    pal.surf("beadboard", "beadboard", "#e8e4da", rough=0.5)
    pal.surf("chimney", "brick_common", rough=0.85)
    pal.solid("roof_under", (0.55, 0.52, 0.48), rough=0.8)
    return pal


# ------------------------------------------------------------------ geometry helpers
def storey_heights(tr):
    era = tr.get("year_built", 1920)
    fnd = tr.get("foundation", "concrete_block")
    fl1 = 0.3 if tr.get("archetype") in ("ranch", "split_level") and era >= 1950 else (0.75 if era < 1915 else 0.55)
    if fnd in ("fieldstone", "cut_stone") and era < 1900:
        fl1 = 0.85
    h = 2.9 if era < 1915 else (2.75 if era < 1945 else 2.44)
    return fl1, h


def covered_by_other_block(p, spec, own, margin=0.6):
    """Is wall point p (on block `own`'s outline) within margin of another block (a wing/garage
    built against that wall)?"""
    for ob in spec["blocks"]:
        if ob is own:
            continue
        x0, y0, x1, y1 = ob["rect"]
        if x0 - margin <= p[0] <= x1 + margin and y0 - margin <= p[1] <= y1 + margin:
            return True
    return False


def windows_for(spec, wall_segments, floor_z_rel, h, sill, kind, cols, shutters, avoid, spacing=2.4, floor=0, own=None):
    """Evenly spaced windows along each (a, c) exterior wall segment, clear of door points and of
    any stretch of wall another block (wing, garage) covers."""
    for (a, c) in wall_segments:
        L = math.dist(a, c)
        n = max(0, int((L - 0.6) / spacing))
        if n == 0 and L >= 1.6:
            n = 1
        for k in range(n):
            t = (k + 0.5) / n
            p = (a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t)
            if any(math.dist(p, q) < 1.1 for q in avoid):
                continue
            if own is not None and covered_by_other_block(p, spec, own):
                continue
            spec["windows"].append(dict(at=p, floor=floor, w=0.85 if kind != "picture" else 1.6, sill=sill, h=h, cols=cols,
                                        kind=kind, shutters=shutters))


def split(a0, a1, fracs):
    """Cut [a0, a1] at the given cumulative fractions -> list of (lo, hi)."""
    pts = [a0] + [a0 + (a1 - a0) * f for f in fracs] + [a1]
    return list(zip(pts, pts[1:]))


# ------------------------------------------------------------------ plans
def plan_side_hall(spec, W, D, x0, y0, fl, st, mirror, rnd, tr):
    """Two-level side-hall plan in the block [x0, x0+W] x [y0, y0+D]."""
    x1, y1 = x0 + W, y0 + D
    # will a straight flight fit front-to-back?  If not, a dog-leg (2 x 0.95 m) goes in a wider hall
    # so a 1.2 m corridor still runs beside it to every room
    rise0 = fl[1][0] - fl[0][0]
    n0 = max(12, math.ceil(rise0 / 0.195))
    dog = n0 * 0.205 + 1.9 > D - 2 * TE
    hall_w = 3.25 if dog else HALL_W
    # hall on the left (mirror: right)
    hx0, hx1 = (x0, x0 + hall_w) if not mirror else (x1 - hall_w, x1)
    rx0, rx1 = (hx1, x1) if not mirror else (x0, hx0)
    two_cols = (rx1 - rx0) >= 7.2
    cx = (rx0 + rx1) / 2
    col_a = (rx0, cx) if not mirror else (cx, rx1)          # column next to the hall
    col_b = (cx, rx1) if not mirror else (rx0, cx)
    if not two_cols:
        col_a = (rx0, rx1)
    # stair: straight along the outer wall side of the hall when deep enough, else dog-leg
    fz, cz = fl[0]
    rise = fl[1][0] - fz
    n = max(12, math.ceil(rise / 0.195))
    run = 0.24
    clear = D - 2 * TE
    L = n * run
    while L + 1.9 > clear and run > 0.205:
        run -= 0.01
        L = n * run
    sx = hx0 + TE + 0.02 if not mirror else hx1 - TE - STAIR_W - 0.02
    if L + 1.9 <= clear:
        start_y = y1 - TE - 1.0
        # for dir (0,-1) a flight's width runs toward +x from its start (left) edge; the rail goes on
        # the corridor side: +x edge ('left' in gbhouse terms) for a left hall, the start edge when mirrored
        stair = dict(start=(sx, start_y), dir=(0, -1), width=STAIR_W, n=n, run=run, floor=0, to_floor=1,
                     rail_side="left" if not mirror else "right")
        stair_kind = "straight"
    else:
        start_y = y1 - TE - 1.0
        # lanes [outer wall | B arrival | gap | A departure | corridor]: for dir (0,-1) flight A spans
        # start..start+0.95 along +x; B lies on the `turn` side (left = +x, right = -x) past a 0.08 gap
        if not mirror:
            sx_d = hx0 + TE + 0.02 + 0.95 + 0.08          # B on the -x (wall) side
            turn = "right"
        else:
            sx_d = hx1 - TE - 0.02 - 2 * 0.95 - 0.08      # B on the +x (wall) side
            turn = "left"
        stair = dict(type="dogleg", start=(sx_d, start_y), dir=(0, -1), width=0.95, n=n, run=0.25, landing=1.0, turn=turn,
                     floor=0, to_floor=1, rail=True)
        stair_kind = "dogleg"
    spec["stairs"].append(stair)
    # --- ground floor rooms
    rooms, doors = spec["rooms"], spec["doors"]
    rooms.append(dict(name="HALL", rect=(hx0, y0, hx1, y1), type="hall"))
    deep = D >= 8.5
    ym = y0 + D * (0.45 if not deep else 0.55)
    ym2 = y0 + D * 0.28
    corridor_x = (hx1 - 0.6) if not mirror else (hx0 + 0.6)        # a point in the hall corridor (beside the stair)
    part_x = hx1 if not mirror else hx0                               # hall | rooms partition
    if two_cols:
        rooms += [dict(name="LR", rect=(col_a[0], ym, col_a[1], y1), type="living"),
                  dict(name="PARLOR", rect=(col_b[0], ym, col_b[1], y1), type="sitting"),
                  dict(name="DR", rect=(col_a[0], y0, col_a[1], ym), type="dining"),
                  dict(name="KIT", rect=(col_b[0], y0, col_b[1], ym), type="kitchen", floor_mat="lino")]
        mid_x = cx
        doors += [dict(name="hall_lr", at=(part_x, (ym + y1) / 2), w=1.2, cased=True),
                  dict(name="lr_parlor", at=(mid_x, (ym + y1) / 2), w=1.3, cased=True),
                  dict(name="hall_dr", at=(part_x, (y0 + ym) / 2), w=0.9, swing_into="DR"),
                  dict(name="dr_kit", at=(mid_x, (y0 + ym) / 2), w=0.85, swing_into="KIT")]
        back_x = (col_b[0] + col_b[1]) / 2
        back_room = "KIT"
    else:
        if deep:
            rooms += [dict(name="LR", rect=(col_a[0], ym, col_a[1], y1), type="living"),
                      dict(name="DR", rect=(col_a[0], ym2, col_a[1], ym), type="dining"),
                      dict(name="KIT", rect=(col_a[0], y0, col_a[1], ym2), type="kitchen", floor_mat="lino")]
            doors += [dict(name="hall_lr", at=(part_x, (ym + y1) / 2), w=1.2, cased=True),
                      dict(name="lr_dr", at=((col_a[0] + col_a[1]) / 2, ym), w=1.3, cased=True),
                      dict(name="hall_kit", at=(part_x, (y0 + ym2) / 2), w=0.85, swing_into="KIT")]
        else:
            rooms += [dict(name="LR", rect=(col_a[0], ym, col_a[1], y1), type="living"),
                      dict(name="KIT", rect=(col_a[0], y0, col_a[1], ym), type="kitchen", floor_mat="lino")]
            doors += [dict(name="hall_lr", at=(part_x, (ym + y1) / 2), w=1.2, cased=True),
                      dict(name="hall_kit", at=(part_x, (y0 + ym) / 2), w=0.85, swing_into="KIT")]
        back_x = (col_a[0] + col_a[1]) / 2
        back_room = "KIT"
    # front door into the hall corridor; back door from the kitchen
    doors.append(dict(name="front", at=(corridor_x, y1), w=0.9, ext=True,
                      glazed=(0.2, 0.55, 0.8, 0.9) if rnd.random() < 0.6 else None))
    doors.append(dict(name="back", at=(back_x, y0), w=0.85, ext=True, glazed=(0.15, 0.5, 0.85, 0.9)))
    # --- upper floor
    up_attic = fl[1][1] - fl[1][0] < 2.35
    rooms.append(dict(name="HALL2", floor=1, rect=(hx0, y0, hx1, y1), type=None))
    if two_cols:
        cy0, cy1 = (y0 + y1) / 2 - 0.6, (y0 + y1) / 2 + 0.6
        corr_x0, corr_x1 = (hx1, x1) if not mirror else (x0, hx0)
        rooms += [dict(name="HALLX", floor=1, rect=(corr_x0, cy0, corr_x1, cy1), type=None, no_light=True, open_plan_to="HALL2"),
                  dict(name="BR1", floor=1, rect=(col_a[0], cy1, col_a[1], y1), type="bed"),
                  dict(name="BR2", floor=1, rect=(col_b[0], cy1, col_b[1], y1), type="bed"),
                  dict(name="BATH", floor=1, rect=(col_a[0], y0, col_a[1], cy0), type="bath", floor_mat="hextile"),
                  dict(name="BR3", floor=1, rect=(col_b[0], y0, col_b[1], cy0), type="bed")]
        doors += [dict(name="br1", floor=1, at=((col_a[0] + col_a[1]) / 2, cy1), w=0.8, swing_into="BR1"),
                  dict(name="br2", floor=1, at=((col_b[0] + col_b[1]) / 2, cy1), w=0.8, swing_into="BR2"),
                  dict(name="bath", floor=1, at=((col_a[0] + col_a[1]) / 2, cy0), w=0.75, swing_into="BATH"),
                  dict(name="br3", floor=1, at=((col_b[0] + col_b[1]) / 2, cy0), w=0.8, swing_into="BR3")]
    else:
        yb = y0 + min(2.4, D * 0.3)
        yf = y0 + D * 0.55
        rooms += [dict(name="BR1", floor=1, rect=(col_a[0], yf, col_a[1], y1), type="bed"),
                  dict(name="BR2", floor=1, rect=(col_a[0], yb, col_a[1], yf), type="bed"),
                  dict(name="BATH", floor=1, rect=(col_a[0], y0, col_a[1], yb), type="bath", floor_mat="hextile")]
        doors += [dict(name="br1", floor=1, at=(part_x, (yf + y1) / 2), w=0.8, swing_into="BR1"),
                  dict(name="br2", floor=1, at=(part_x, (yb + yf) / 2), w=0.8, swing_into="BR2"),
                  dict(name="bath", floor=1, at=(part_x, (y0 + yb) / 2), w=0.75, swing_into="BATH")]
    if stair_kind == "straight":
        # guard the upstairs edge of the well on the corridor side
        wx = sx + STAIR_W + 0.03 if not mirror else sx - 0.03
        spec["rails"].append(dict(floor=1, pts=[(wx, start_y - L + 0.05), (wx, start_y - 0.05)]))
    else:
        # the dog-leg's well edge along the corridor (flight A's open side)
        well = (n + 1) // 2 * 0.25 + 1.0
        wx = sx_d + 0.95 + 0.03 if not mirror else sx_d - 0.03
        spec["rails"].append(dict(floor=1, pts=[(wx, start_y - well + 0.05), (wx, start_y - 0.05)]))
    return dict(front_door=(corridor_x, y1), back_door=(back_x, y0), part_x=part_x, stair=stair, up_attic=up_attic)


def attic_door_height(spec, fl, ridge, W, D):
    """Leaf height for attic doors that swing out under the slope: the roof must clear the leaf's
    whole sweep (hall edge + 0.8 m toward the eave)."""
    bl = spec["blocks"][0]
    rf = bl["roof"]
    half = (D if ridge == "x" else W) / 2
    d_eave = half - (HALL_W / 2 + 0.8)
    under = bl["wall_top"] + d_eave * math.tan(math.radians(rf["pitch"])) - rf.get("thick", 0.15) / math.cos(math.radians(rf["pitch"]))
    return clamp(under - fl[1][0] - 0.08, 1.9, 2.03)


def plan_attic(spec, W, D, x0, y0, fl, ridge, rnd, mirror):
    """1.5-storey plan: the hall and its straight stair run along the RIDGE (the only place with
    headroom upstairs), rooms on both sides tuck under the slopes."""
    x1, y1 = x0 + W, y0 + D
    rooms, doors = spec["rooms"], spec["doors"]
    rise = fl[1][0] - fl[0][0]
    n = max(12, math.ceil(rise / 0.195))
    hw = HALL_W / 2
    adh = attic_door_height(spec, fl, ridge, W, D)
    back_out = False
    if ridge == "y":
        L_avail = D - 2 * TE - 1.9
        run = clamp(L_avail / n, 0.205, 0.24)
        L = n * run
        cx = (x0 + x1) / 2
        hx0, hx1 = cx - hw, cx + hw
        sx = hx0 + 0.03 if not mirror else hx1 - 0.03 - STAIR_W
        start_y = y1 - TE - 1.0
        spec["stairs"].append(dict(start=(sx, start_y), dir=(0, -1), width=STAIR_W, n=n, run=run, floor=0, to_floor=1,
                                   rail_side="left" if not mirror else "right"))
        corr = (hx1 - 0.55) if not mirror else (hx0 + 0.55)
        ym = y0 + D * 0.5
        yb = y0 + min(2.2, D * 0.3)
        rooms += [dict(name="HALL", rect=(hx0, y0, hx1, y1), type="hall"),
                  dict(name="LR", rect=(x0, ym, hx0, y1), type="living"),
                  dict(name="KIT", rect=(x0, y0, hx0, ym), type="kitchen", floor_mat="lino"),
                  dict(name="BR1", rect=(hx1, yb, x1, y1), type="bed"),
                  dict(name="BATH", rect=(hx1, y0, x1, yb), type="bath", floor_mat="hextile"),
                  dict(name="HALL2", floor=1, rect=(hx0, y0, hx1, y1), type=None),
                  dict(name="BR2", floor=1, rect=(x0, y0, hx0, y1), type="bed"),
                  dict(name="BR3", floor=1, rect=(hx1, y0, x1, y1), type="bed")]
        # ground-floor doors on the flight's side open off the clear bands in front of its foot and
        # behind its top end; the other side's open off the corridor
        y_foot, y_end = start_y + 0.5, (y0 + TE + start_y - L) / 2
        doors += [dict(name="hall_lr", at=(hx0, y_foot if not mirror else (ym + y1) / 2), w=0.9 if not mirror else 1.2, cased=True),
                  dict(name="hall_kit", at=(hx0, y_end if not mirror else (y0 + ym) / 2), w=0.85, swing_into="KIT"),
                  dict(name="br1", at=(hx1, y_foot if mirror else (yb + y1) / 2), w=0.8, swing_into="BR1"),
                  dict(name="bath", at=(hx1, y_end if mirror else (y0 + yb) / 2), w=0.75, swing_into="BATH"),
                  # the room on the flight's side opens off the head landing (the well fills the hall beside it)
                  dict(name="br2", floor=1, at=(hx0, start_y - L - 0.45 if not mirror else y0 + D * 0.3), w=0.75, h=adh,
                       swing_into="BR2"),
                  dict(name="br3", floor=1, at=(hx1, start_y - L - 0.45 if mirror else y0 + D * 0.3), w=0.75, h=adh,
                       swing_into="BR3")]
        wx = sx + STAIR_W + 0.03 if not mirror else sx - 0.03
        spec["rails"].append(dict(floor=1, pts=[(wx, start_y - L + 0.05), (wx, start_y - 0.05)]))
        # unmirrored, hall_kit opens off the band behind the flight, near the back wall: the back door
        # goes to the kitchen's far side, clear of that leaf -- or, in a kitchen too narrow for both,
        # out of the hall's own back end (swinging out onto the stoop)
        front, back = (corr, y1), ((x0 + hx0) / 2, y0)
        if not mirror:
            back = (x0 + TE + 0.55, y0) if hx0 - x0 >= 2.6 else ((hx0 + hx1) / 2, y0)
            back_out = hx0 - x0 < 2.6
    else:
        L_avail = W - 2 * TE - 1.9
        run = clamp(L_avail / n, 0.205, 0.24)
        L = n * run
        cy = (y0 + y1) / 2
        hy0, hy1 = cy - hw, cy + hw
        # flight along +x (-x when mirrored) in the rear half of the hall band; a flight's width runs
        # from its start (left) edge toward side = (-dir.y, dir.x): +y for +x, -y for -x.  The rail
        # goes on the front (corridor) edge.
        if not mirror:
            start, sd, rail_side = (x0 + TE + 1.0, hy0 + 0.03), (1, 0), "left"
        else:
            start, sd, rail_side = (x1 - TE - 1.0, hy0 + 0.03 + STAIR_W), (-1, 0), "right"
        spec["stairs"].append(dict(start=start, dir=sd, width=STAIR_W, n=n, run=run, floor=0, to_floor=1,
                                   rail_side=rail_side))
        xm = x0 + W * (0.52 if not mirror else 0.48)
        xb = x1 - min(2.2, W * 0.28) if not mirror else x0 + min(2.2, W * 0.28)
        lr = (x0, hy1, xm, y1) if not mirror else (xm, hy1, x1, y1)
        br1 = (xm, hy1, x1, y1) if not mirror else (x0, hy1, xm, y1)
        kit = (x0, y0, xm, hy0) if not mirror else (xm, y0, x1, hy0)
        bath = (xb, y0, x1, hy0) if not mirror else (x0, y0, xb, hy0)
        br2 = (xm, y0, xb, hy0) if not mirror else (xb, y0, xm, hy0)
        rooms += [dict(name="HALL", rect=(x0, hy0, x1, hy1), type="hall"),
                  dict(name="LR", rect=lr, type="living"), dict(name="BR1", rect=br1, type="bed"),
                  dict(name="KIT", rect=kit, type="kitchen", floor_mat="lino"),
                  dict(name="BATH", rect=bath, type="bath", floor_mat="hextile"), dict(name="BR2", rect=br2, type="bed"),
                  dict(name="HALL2", floor=1, rect=(x0, hy0, x1, hy1), type=None),
                  dict(name="BR3", floor=1, rect=(x0, hy1, x1, y1), type="bed"),
                  dict(name="BR4", floor=1, rect=(x0, y0, x1, hy0), type="bed")]
        # doors off the hall band stay clear of the flight (which occupies its rear half)
        doors += [dict(name="hall_lr", at=((lr[0] + lr[2]) / 2, hy1), w=1.2, cased=True),
                  dict(name="br1", at=((br1[0] + br1[2]) / 2, hy1), w=0.8, swing_into="BR1"),
                  dict(name="br3", floor=1, at=((x0 + x1) / 2 + (1.2 if not mirror else -1.2), hy1), w=0.75, h=adh, swing_into="BR3")]
        # rear rooms open off the hall beyond the stair's foot/head ends
        foot_x = x0 + TE + 0.5 if not mirror else x1 - TE - 0.5
        head_x = start[0] + sd[0] * (L + 0.5)
        doors += [dict(name="hall_kit", at=(foot_x, hy0), w=0.85, swing_into="KIT"),
                  dict(name="br4", floor=1, at=(head_x, hy0), w=0.75, h=adh, swing_into="BR4"),
                  dict(name="bath", at=((bath[0] + bath[2]) / 2, hy0), w=0.75, swing_into="BATH"),
                  dict(name="br2", at=((br2[0] + br2[2]) / 2, hy0), w=0.8, swing_into="BR2")]
        wy = hy0 + 0.03 + STAIR_W + 0.03
        spec["rails"].append(dict(floor=1, pts=[(min(start[0], start[0] + sd[0] * L) + 0.05, wy),
                                                (max(start[0], start[0] + sd[0] * L) - 0.05, wy)]))
        front, back = (((lr[0] + lr[2]) / 2 + 0.6), y1), ((kit[0] + kit[2]) / 2, y0)
    doors.append(dict(name="front", at=front, w=0.9, ext=True, glazed=(0.2, 0.55, 0.8, 0.9) if rnd.random() < 0.6 else None))
    doors.append(dict(name="back", at=back, w=0.85, ext=True, glazed=(0.15, 0.5, 0.85, 0.9), out=back_out))
    return dict(front_door=front, back_door=back)


def plan_one_storey(spec, W, D, x0, y0, rnd, tr, mirror):
    x1, y1 = x0 + W, y0 + D
    rooms, doors = spec["rooms"], spec["doors"]
    if W < 7.5 and D < 8.0:
        # small narrow cottage: living room across the front, kitchen + bath behind
        ym = y0 + D * 0.52
        bath_w = min(1.9, W * 0.4)
        bx = (x1 - bath_w, x1) if not mirror else (x0, x0 + bath_w)
        kx = (x0, bx[0]) if not mirror else (bx[1], x1)
        rooms += [dict(name="LR", rect=(x0, ym, x1, y1), type="living"),
                  dict(name="KIT", rect=(kx[0], y0, kx[1], ym), type="kitchen", floor_mat="lino"),
                  dict(name="BATH", rect=(bx[0], y0, bx[1], ym), type="bath", floor_mat="hextile")]
        doors += [dict(name="lr_kit", at=((kx[0] + kx[1]) / 2, ym), w=0.85, swing_into="KIT"),
                  dict(name="kit_bath", at=((bx[0] if not mirror else bx[1]), (y0 + ym) / 2), w=0.7, swing_into="BATH")]
        front = ((x0 + x1) / 2, y1)
        back = ((kx[0] + kx[1]) / 2, y0)
        doors.append(dict(name="front", at=front, w=0.9, ext=True, glazed=(0.2, 0.55, 0.8, 0.9)))
        doors.append(dict(name="back", at=back, w=0.85, ext=True, glazed=(0.15, 0.5, 0.85, 0.9)))
        return dict(front_door=front, back_door=back)
    if W < 7.5:
        # shotgun / narrow cottage: a line of rooms front to back, doors along one side
        ys = [y0 + D * f for f in (0.0, 0.3, 0.62, 1.0)]
        bath_w = min(1.8, W * 0.35)
        bx = (x1 - bath_w, x1) if not mirror else (x0, x0 + bath_w)
        rooms += [dict(name="LR", rect=(x0, ys[2], x1, ys[3]), type="living"),
                  dict(name="BR1", rect=(x0, ys[1], x1, ys[2]), type="bed"),
                  dict(name="KIT", rect=((bx[1] if mirror else x0), ys[0], (x1 if mirror else bx[0]), ys[1]), type="kitchen", floor_mat="lino"),
                  dict(name="BATH", rect=(bx[0], ys[0], bx[1], ys[1]), type="bath", floor_mat="hextile")]
        dx = x0 + 0.9 if not mirror else x1 - 0.9
        kx = (x0 + (bx[0] if not mirror else x1)) / 2 if not mirror else (bx[1] + x1) / 2
        doors += [dict(name="lr_br1", at=(dx, ys[2]), w=0.8, swing_into="BR1"),
                  dict(name="br1_kit", at=(dx, ys[1]), w=0.8, swing_into="KIT"),
                  dict(name="kit_bath", at=((bx[0] if not mirror else bx[1]), (ys[0] + ys[1]) / 2), w=0.7, swing_into="BATH")]
        front = ((x0 + x1) / 2 + (0.8 if not mirror else -0.8), y1)
        back = (kx, y0)
        doors.append(dict(name="front", at=front, w=0.9, ext=True, glazed=(0.2, 0.55, 0.8, 0.9)))
        doors.append(dict(name="back", at=back, w=0.85, ext=True, glazed=(0.15, 0.5, 0.85, 0.9)))
        return dict(front_door=front, back_door=back)
    # hall plan: [LR / KIT] | hall | [BR1 / BATH / BR2]
    left_w = clamp(W * 0.46, 3.2, 5.5)
    hall_w = 1.1
    if not mirror:
        la, ha, ra = (x0, x0 + left_w), (x0 + left_w, x0 + left_w + hall_w), (x0 + left_w + hall_w, x1)
    else:
        la, ha, ra = (x1 - left_w, x1), (x1 - left_w - hall_w, x1 - left_w), (x0, x1 - left_w - hall_w)
    ym = y0 + D * 0.52
    bath_d = clamp(D * 0.24, 1.7, 2.4)
    yb0 = y0 + (D - bath_d) * 0.5
    yb1 = yb0 + bath_d
    hall_y0 = y0 + 0.9 if D > 7 else y0
    rooms += [dict(name="LR", rect=(la[0], ym, la[1], y1), type="living"),
              dict(name="KIT", rect=(la[0], y0, la[1], ym), type="kitchen", floor_mat="lino"),
              dict(name="HALL", rect=(ha[0], hall_y0, ha[1], y1 - 0.0), type="hall", no_furnish=True),
              dict(name="BR1", rect=(ra[0], yb1, ra[1], y1), type="bed"),
              dict(name="BATH", rect=(ra[0], yb0, ra[1], yb1), type="bath", floor_mat="hextile"),
              dict(name="BR2", rect=(ra[0], y0, ra[1], yb0), type="bed")]
    if hall_y0 > y0:
        rooms.append(dict(name="CL", rect=(ha[0], y0, ha[1], hall_y0), type="closet"))
        doors.append(dict(name="cl", at=((ha[0] + ha[1]) / 2, hall_y0), w=0.7, swing_into="CL"))     # out of the narrow hall
    lx = la[1] if not mirror else la[0]
    rx = ra[0] if not mirror else ra[1]
    doors += [dict(name="lr_hall", at=(lx, y1 - 1.2), w=0.9, cased=True),
              dict(name="hall_kit", at=(lx, (hall_y0 + ym) / 2 if (hall_y0 + ym) / 2 < ym - 0.5 else ym - 0.6), w=0.85, swing_into="KIT"),
              dict(name="br1", at=(rx, (yb1 + y1) / 2), w=0.8, swing_into="BR1"),
              dict(name="bath", at=(rx, (yb0 + yb1) / 2), w=0.75, swing_into="BATH"),
              dict(name="br2", at=(rx, max(hall_y0 + 0.5, (y0 + yb0) / 2)), w=0.8, swing_into="BR2")]
    front = ((la[0] + la[1]) / 2 + (0.6 if not mirror else -0.6), y1)
    back = ((la[0] + la[1]) / 2, y0)
    doors.append(dict(name="front", at=front, w=0.9, ext=True, glazed=(0.2, 0.55, 0.8, 0.9)))
    doors.append(dict(name="back", at=back, w=0.85, ext=True, glazed=(0.15, 0.5, 0.85, 0.9)))
    return dict(front_door=front, back_door=back)


# ------------------------------------------------------------------ build
ARCH = {
    # archetype: (default storeys, roof type, ridge, pitch, attic habitable for 1.5)
    "i_house": (2, "gable", "x", 35), "gable_front": (2, "gable", "y", 40), "upright_and_wing": (2, "gable", "y", 40),
    "foursquare": (2, "hip", None, 28), "bungalow": (1.5, "gable", "x", 30), "workers_cottage": (1.5, "gable", "y", 40),
    "queen_anne": (2, "hip", None, 40), "italianate": (2, "hip", None, 22), "cape_cod": (1.5, "gable", "x", 45),
    "ranch": (1, "hip", None, 22), "minimal_traditional": (1, "gable", "x", 30), "side_gable_cottage": (1, "gable", "x", 35),
    "shotgun": (1, "gable", "y", 35), "dutch_colonial": (2, "gambrel", "x", 25), "tudor_revival": (1.5, "gable", "y", 50),
    "split_level": (1, "hip", None, 22), "american_small_house": (1, "gable", "x", 35), "prairie_box": (2, "hip", None, 20),
    # the coasts (CATALOG_SPEC_COASTAL.md)
    "raised_beach_house": (2, "gable", "x", 30), "contemporary_beach": (2, "shed", None, 18), "shingle_style": (2, "gable", "y", 42),
    "nantucket_cape": (1.5, "gable", "x", 45), "charleston_single": (2, "gable", "y", 35), "lowcountry": (1.5, "hip", None, 30),
    "california_bungalow": (1, "gable", "x", 25), "spanish_revival": (1, "gable", "x", 20), "a_frame": (1.5, "gable", "y", 55),
    "cottage_lake": (1, "gable", "x", 32),
}
RAISED_ARCH = ("raised_beach_house",)


def build(rec):
    try:
        return _build(rec)
    except ValueError as e:
        print(f"NOTE {rec['id']}: {e}; building it as one storey")
        rec = dict(rec, traits=dict(rec.get("traits") or {}, storeys=1))
        return _build(rec)


def _build(rec):
    rid = rec["id"]
    tr = rec.get("traits", {}) or {}
    names = rec.get("names", {}) or {}
    rnd = rng(rid)
    cond = tr.get("condition", "kept")
    arch = tr.get("archetype", "gable_front")
    d_storeys, d_roof, d_ridge, d_pitch = ARCH.get(arch, ARCH["gable_front"])
    storeys = tr.get("storeys") or d_storeys
    # raised on piles (flood code): the living floors lifted a storey's worth above the grade; a three-
    # storey shore house is two living floors over its raised base
    raised = arch in RAISED_ARCH or tr.get("foundation") == "piles" or storeys >= 3
    if storeys >= 3:
        storeys = 2
    roof_tr = dget(tr, "roof")
    rtype = roof_tr.get("type") or d_roof
    cross_gables = 0
    if rtype in ("cross_gable",):
        rtype = "gable"
        cross_gables = 2 if arch == "tudor_revival" else 1
    elif arch == "queen_anne" and rtype in ("gable", "hip"):
        cross_gables = 1
    if rtype == "pyramid":
        rtype = "hip"
    pitch = clamp(roof_tr.get("pitch_deg") or d_pitch, 14, 55)
    lot = rec.get("lot", {"w": 12.0, "d": 10.0})
    lot_w, lot_d = lot["w"], lot["d"]
    if rid.startswith("FARM-"):
        # a farmstead's barn and shed stand ~12 m off the house's sides (map_preview.farmstead_polys):
        # keep the house's own yard inside that
        lot_w, lot_d = min(lot_w, 22.0), min(lot_d, 22.0)
    porch_tr = dget(tr, "porch") or {"type": "stoop"}
    ptype = porch_tr.get("type", "stoop")
    stacked = ptype == "stacked" or (raised and storeys >= 2 and ptype in ("front", "front_full", "wrap"))
    if ptype in ("stacked", "front"):
        ptype = "front_full"
    porch_d = {"none": 1.0, "stoop": 1.0, "front_full": 2.2, "front_partial": 2.0, "wrap": 2.2, "enclosed": 2.0,
               "side": 1.0, "recessed": 1.4}.get(ptype, 1.2)      # none/side: the front door still gets a stoop
    garage = tr.get("garage", "none") or "none"
    gar_w = {"detached_1": 3.8, "detached_2": 6.2, "attached_1": 3.6, "attached_2": 6.0, "carport": 3.2}.get(garage, 0.0)
    # footprint: fit the lot (1 m side yards, the porch + a walk/steps band in front, 1.5 m behind)
    side_room = lot_w - 2.0 - (gar_w + 0.8 if garage.startswith("attached") or garage == "carport" else 0.0)
    W = clamp(ft(tr.get("main_w_ft") or 26), 5.2, max(5.2, side_room))
    fl1, h = storey_heights(tr)
    if raised:
        fl1 = 1.85                 # ~6 ft over grade: the base (lattice-skirted piles) below the first floor
    # front band: the porch steps' run (0.28 m per 0.18 m riser), a 0.9 m landing at their foot and a
    # front fence; a lot too shallow for that (a 2-storey house needs 5.8 m) gets no fence
    run = max(1, round(fl1 / 0.18)) * 0.28
    fenced = (dget(tr, "yard").get("fence", "none") not in ("none", None)
              and lot_d - porch_d - (run + 1.3) - 1.2 >= (5.8 if storeys >= 1.5 else 5.5))
    band = max(1.6, run + (1.3 if fenced else 0.4))
    D = clamp(ft(tr.get("main_d_ft") or 30), 5.5, max(5.5, lot_d - porch_d - band - 1.2))
    if garage.startswith("detached") and lot_d - (D + porch_d + band) < 6.2 + 3.6 + 0.4:
        garage = "carport" if lot_w - W - 2.0 >= 3.4 else "none"
        gar_w = 3.2 if garage == "carport" else 0.0
    if garage.startswith("attached") and lot_w - 2.0 - W < gar_w + 0.3:
        garage = "none"
    if storeys >= 1.5 and D < 5.8:
        D = min(max(D, 5.8), lot_d - porch_d - band - 0.6)
    mirror = rnd.random() < 0.5
    # main block rectangle: centred, shifted away from an attached garage; front at yf
    yf = lot_d / 2 - porch_d - band
    y0 = yf - D
    x0 = -W / 2
    if gar_w and garage != "none":
        x0 = -W / 2 - (gar_w + 0.4) / 2 * (1 if not mirror else -1)
    else:
        wing_tr = tr.get("wing") if isinstance(tr.get("wing"), dict) else {}
        if wing_tr.get("side") in ("left", "right"):
            # a side wing: slide the main block toward the far side of the lot (down to a 0.6 m side yard)
            # just enough to make room for the wing
            need = max(2.8, ft(wing_tr.get("w_ft") or 12))
            shift = clamp(need - (lot_w / 2 - W / 2 - 0.6), 0.0, lot_w / 2 - W / 2 - 0.6)
            x0 = -W / 2 + (shift if wing_tr["side"] == "left" else -shift)
    x1 = x0 + W
    b = lib_building(rid)
    house_materials(b, tr, cond)
    fz0, cz0 = fl1, fl1 + h
    floors = [(fz0, cz0)]
    habitable_attic = False
    if storeys >= 1.5:
        fz1 = cz0 + 0.3
        if storeys >= 2:
            floors.append((fz1, fz1 + h - 0.1))
            wall_top = fz1 + h
        else:
            floors.append((fz1, fz1 + 2.4))
            wall_top = fz1 + 1.0            # knee wall; rooms live under the roof
            habitable_attic = True
    else:
        wall_top = cz0 + 0.12
    ridge = roof_tr.get("ridge") or d_ridge or ("x" if W >= D else "y")
    if rtype in ("gable", "gambrel") and storeys == 1.5 and ridge is None:
        ridge = "x"
    roof = dict(type=rtype, pitch=pitch, eave_oh=0.35 if tr.get("year_built", 1920) < 1945 else 0.45, rake_oh=0.25, thick=0.15)
    if rtype in ("gable", "gambrel"):
        roof["ridge"] = ridge or "x"
        if habitable_attic and roof["ridge"] == "x" and D < 6.2:
            roof["ridge"] = "y"
        if habitable_attic and rtype == "gable":
            roof["pitch"] = max(pitch, 42)
    if rtype == "shed":
        roof["high"] = "N"
    if rtype == "flat" and arch in ("ranch", "prairie_box"):
        roof.update(eave_oh=1.1, thick=0.3)             # Prairie / Usonian: a thin slab cantilevered out deep
    elif rtype == "flat":
        roof.update(parapet=0.3, eave_oh=0.0)            # Moderne and the rest: a parapet, no overhang
    elif arch == "prairie_box" or (arch == "ranch" and pitch <= 22):
        roof["eave_oh"] = 1.0                            # the deep eaves that make the low Prairie/ranch outline
    spec = dict(t_ext=TE, t_int=TI, era="old" if tr.get("year_built", 1920) < 1940 else "modern",
                mats=dict(ext="siding", int="plaster", roof="roof", roof_under="roof_under", found="found", floor="floor",
                          ceiling="plaster", trim="trim", door="door", fascia="trim", porch="porch", post="trim", furn="furniture"),
                blocks=[dict(name="main", rect=(x0, y0, x1, yf), floors=floors, wall_top=wall_top, found_top=fl1 - 0.05,
                             roof=roof, habitable_attic=habitable_attic)],
                rooms=[], doors=[], windows=[], stairs=[], rails=[], porches=[], chimneys=[], fireplaces=[])
    if storeys >= 2:
        info = plan_side_hall(spec, W, D, x0, y0, floors, None, mirror, rnd, tr)
    elif storeys >= 1.5:
        # the attic stair runs along the ridge: it needs n x 0.205 m + both 0.9 m landings of clear length
        need = math.ceil((floors[1][0] - floors[0][0]) / 0.195) * 0.205 + 1.9 + 2 * TE
        ridge_ = roof.get("ridge") or ("x" if W >= D else "y")
        if (W if ridge_ == "x" else D) < need:
            ridge_ = "y" if ridge_ == "x" else "x"
        if (W if ridge_ == "x" else D) < need:
            raise ValueError("footprint too small for a 1.5-storey attic stair")      # caller retries as 1 storey
        roof["ridge"] = ridge_
        if rtype in ("gable", "gambrel", "hip"):
            # raise the knee wall until the slope clears a 1.9 m attic door's sweep (see attic_door_height)
            half = (D if ridge_ == "x" else W) / 2
            tp = math.tan(math.radians(roof["pitch"]))
            knee = fz1 + 1.98 - (half - (HALL_W / 2 + 0.8)) * tp + roof["thick"] / math.cos(math.radians(roof["pitch"]))
            wall_top = max(wall_top, min(knee, fz1 + 1.8))
            spec["blocks"][0]["wall_top"] = wall_top
        info = plan_attic(spec, W, D, x0, y0, floors, ridge_, rnd, mirror)
    else:
        info = plan_one_storey(spec, W, D, x0, y0, rnd, tr, mirror)
    # ---- a double house (units: 2) gets its second family's door beside the first, into the next front room
    if tr.get("units") == 2:
        fx = info["front_door"][0]
        for x2 in (fx + 1.5, fx - 1.5):
            if any(r.get("floor", 0) == 0 and r.get("type") not in ("hall", None) and abs(r["rect"][3] - yf) < 0.01
                   and r["rect"][0] + 0.6 <= x2 <= r["rect"][2] - 0.6 for r in spec["rooms"]):
                spec["doors"].append(dict(name="front2", at=(x2, yf), w=0.9, ext=True, glazed=(0.2, 0.55, 0.8, 0.9)))
                break
    # ---- rear or side wing (one storey, kitchen/den)
    wing = tr.get("wing")
    if wing and isinstance(wing, dict):
        ww = clamp(ft(wing.get("w_ft") or 14), 3.0, W - 0.6)
        wd = clamp(ft(wing.get("d_ft") or 12), 2.8, 4.5)
        wside = wing.get("side", "rear")
        if wside == "rear" and y0 - wd > -lot_d / 2 + 0.8:
            wx0 = x0 + (0.0 if not mirror else W - ww)
            spec["blocks"].append(dict(name="wing", rect=(wx0, y0 - wd, wx0 + ww, y0), floors=[(fl1, fl1 + h)],
                                       wall_top=fl1 + h + 0.12, found_top=fl1 - 0.05,
                                       roof=dict(type="gable", ridge="y", pitch=min(pitch, 35), eave_oh=0.3, rake_oh=0.2, thick=0.14)))
            spec["rooms"].append(dict(name="WING", rect=(wx0, y0 - wd, wx0 + ww, y0), type="laundry" if rnd.random() < 0.5 else "sitting"))
            # the door through to the wing: nearest the wing's middle, clear of the main stair and its landings
            zones = [z for zs in gh.stair_zones(spec) for z in zs[:3] if zs[3] == 0]
            cands = sorted((wx0 + 0.6 + 0.1 * k for k in range(int((ww - 1.2) / 0.1) + 1)), key=lambda x: abs(x - (wx0 + ww / 2)))
            wdx = next((x for x in cands if all(x + 0.55 < z[0] or x - 0.55 > z[2] or y0 + 1.0 < z[1] or y0 - 0.1 > z[3]
                                                    for z in zones)), wx0 + ww / 2)
            spec["doors"].append(dict(name="wing", at=(wdx, y0), w=0.85, swing_into="WING"))
            # the main back door goes if the wing now covers its spot (the wing has its own door out)
            spec["doors"] = [d_ for d_ in spec["doors"] if d_["name"] != "back" or not (wx0 - 0.6 <= d_["at"][0] <= wx0 + ww + 0.6)]
            spec["doors"].append(dict(name="wing_out", at=(wx0 + (0.6 if not mirror else ww - 0.6) + 0.3, y0 - wd), w=0.85, ext=True,
                                      glazed=(0.15, 0.5, 0.85, 0.9)))
        elif wside in ("left", "right"):
            sgn = -1 if wside == "left" else 1
            if (garage.startswith("attached") or garage == "carport") and sgn == (1 if not mirror else -1):
                sgn = -sgn                  # that side is the garage's
            room_side = (x0 + lot_w / 2 - 0.6) if sgn < 0 else (lot_w / 2 - 0.6 - x1)
            ww2 = clamp(ft(wing.get("w_ft") or 12), 2.8, max(2.8, room_side))
            if room_side >= 2.8:
                wx0, wx1 = (x0 - ww2, x0) if sgn < 0 else (x1, x1 + ww2)
                wy0 = y0 + D * 0.25
                spec["blocks"].append(dict(name="wing", rect=(wx0, wy0, wx1, yf - 0.6), floors=[(fl1, fl1 + h)],
                                           wall_top=fl1 + h + 0.12, found_top=fl1 - 0.05,
                                           roof=dict(type="gable", ridge="x", pitch=min(pitch, 38), eave_oh=0.3, rake_oh=0.2, thick=0.14)))
                spec["rooms"].append(dict(name="WING", rect=(wx0, wy0, wx1, yf - 0.6), type="sitting"))
                jx = x0 if sgn < 0 else x1
                # the door through: nearest the wing's middle, into a ground-floor room, clear of the stair
                zones = [z for zs in gh.stair_zones(spec) for z in zs[:3] if zs[3] == 0]
                wl = yf - 0.6 - wy0
                cands = sorted((wy0 + 0.6 + 0.1 * k for k in range(int((wl - 1.2) / 0.1) + 1)), key=lambda y: abs(y - (wy0 + wl / 2)))
                jy = next((y for y in cands
                           if any(r.get("floor", 0) == 0 and r["name"] != "WING" and r["rect"][0] - 0.01 <= jx <= r["rect"][2] + 0.01
                                  and r["rect"][1] + 0.55 <= y <= r["rect"][3] - 0.55 for r in spec["rooms"])
                           and all(y + 0.55 < z[1] or y - 0.55 > z[3] or jx + 1.0 < z[0] or jx - 1.0 > z[2] for z in zones)), None)
                if jy is not None:
                    spec["doors"].append(dict(name="wing", at=(jx, jy), w=0.9, swing_into="WING"))
                else:
                    spec["blocks"].pop()
                    spec["rooms"].pop()
    # ---- porch
    fd = info["front_door"]
    pz = fl1 - 0.12
    if ptype in ("front_full", "wrap", "front_partial", "enclosed", "recessed") and porch_d > 0:
        if ptype == "front_partial":
            px0, px1 = (fd[0] - 1.6, fd[0] + 1.6)
            px0, px1 = max(px0, x0), min(px1, x1)
        else:
            px0, px1 = x0, x1
        prect = (px0, yf, px1, yf + porch_d)
        post_style = {"turned": "square", "square": "square", "tapered_on_piers": "battered", "iron": "square",
                      "columns": "tuscan"}.get(porch_tr.get("posts", "square"), "square")
        top = fl1 + min(h - 0.1, 2.5)
        nposts = max(2, int((px1 - px0) / 2.4) + 1)
        posts = [(px0 + 0.15 + (px1 - px0 - 0.3) * k / (nposts - 1), yf + porch_d - 0.15) for k in range(nposts)]
        rails = []
        if porch_tr.get("rail", "spindle") != "none":
            rails = [[posts[k], posts[k + 1]] for k in range(len(posts) - 1)
                     if not (posts[k][0] < fd[0] < posts[k + 1][0])]
        po = dict(rect=prect, z=pz, post_top=top, posts=posts, rails=rails, post_style=post_style,
                  rail_style="balustrade" if porch_tr.get("rail") == "solid" else None, pedestal=0.9, pedestal_mat="found",
                  steps=dict(at=(fd[0], yf + porch_d), dir=(0, 1), width=1.3, mat="porch"),
                  roof=dict(type="shed", high="S", high_z=top + 0.45, low_z=top + 0.12, oh=0.25), ceiling_light=True)
        spec["porches"].append(po)
        if stacked and len(floors) >= 2:
            # a deck on the upper floor over the porch (its floor is the porch's ceiling), with its own
            # door out from the upper floor
            uz = floors[1][0] - 0.12
            po.pop("roof", None)
            po["post_top"] = uz - 0.15
            po["ceiling_light"] = False
            utop = floors[1][0] + min(floors[1][1] - floors[1][0] - 0.1, 2.5)
            upo = dict(rect=prect, z=uz, post_top=utop, posts=posts, rails=[[posts[k], posts[k + 1]] for k in range(len(posts) - 1)],
                       post_style=post_style, skirt=False,
                       roof=dict(type="shed", high="S", high_z=utop + 0.45, low_z=utop + 0.12, oh=0.25) if rtype != "flat" else None,
                       ceiling_light=True)
            if upo["roof"] is None:
                upo.pop("roof")
            spec["porches"].append(upo)
            spec["doors"].append(dict(name="deck", at=(fd[0], yf), floor=1, w=0.9, ext=True, glazed=(0.1, 0.6, 0.9, 0.95)))
        if raised:
            po["skirt_mat"] = "trim"
            po["rail_style"] = po.get("rail_style")
        if ptype == "wrap":
            wside_x = x1 if not mirror else x0
            wr = (x1, yf - D * 0.55, x1 + 2.0, yf + porch_d) if not mirror else (x0 - 2.0, yf - D * 0.55, x0, yf + porch_d)
            if abs(wside_x) + 2.2 < lot_w / 2:
                spec["porches"].append(dict(rect=wr, z=pz, post_top=top, posts=[((wr[2] - 0.15) if not mirror else (wr[0] + 0.15), wr[1] + 0.15),
                                                                                  ((wr[2] - 0.15) if not mirror else (wr[0] + 0.15), (wr[1] + wr[3]) / 2)],
                                            rails=[], post_style=post_style, pedestal=0.9, pedestal_mat="found",
                                            roof=dict(type="shed", high="W" if not mirror else "E", high_z=top + 0.45, low_z=top + 0.12, oh=0.25)))
    else:
        # stoop: a small landing with steps at the front door
        spec["porches"].append(dict(rect=(fd[0] - 0.8, yf, fd[0] + 0.8, yf + 1.0), z=pz, post_top=pz, posts=[], beam=False,
                                    steps=dict(at=(fd[0], yf + 1.0), dir=(0, 1), width=1.2, mat="concrete"), skirt_mat="found"))
    # upright-and-wing: a "side" porch sits in the angle, across the front of a set-back side wing, with
    # the wing's own door onto it
    side_wing = next((bl for bl in spec["blocks"] if bl["name"] == "wing" and bl["rect"][3] < yf - 0.3
                      and (bl["rect"][2] <= x0 + 0.01 or bl["rect"][0] >= x1 - 0.01)), None)
    if ptype == "side" and side_wing:
        wx0_, wy0_, wx1_, wy1_ = side_wing["rect"]
        prect = (wx0_, wy1_, wx1_, wy1_ + 1.9)
        top = fl1 + min(h - 0.1, 2.5)
        post_style = {"turned": "square", "square": "square", "tapered_on_piers": "battered", "iron": "square",
                      "columns": "tuscan"}.get(porch_tr.get("posts", "square"), "square")
        posts = [(wx0_ + 0.15, prect[3] - 0.15), (wx1_ - 0.15, prect[3] - 0.15)]
        spec["porches"].append(dict(rect=prect, z=pz, post_top=top, posts=posts, rails=[], post_style=post_style,
                                    pedestal=0.9, pedestal_mat="found",
                                    steps=dict(at=((wx0_ + wx1_) / 2 + (0.8 if wx0_ >= x1 - 0.01 else -0.8), prect[3]),
                                               dir=(0, 1), width=1.1, mat="porch"),
                                    roof=dict(type="shed", high="S", high_z=top + 0.45, low_z=top + 0.12, oh=0.25)))
        spec["doors"].append(dict(name="wing_front", at=((wx0_ + wx1_) / 2, wy1_), w=0.85, ext=True, glazed=(0.2, 0.55, 0.8, 0.9)))
    bd = info["back_door"]
    back_on_main = any(d_["name"] == "back" for d_ in spec["doors"])
    if back_on_main:
        spec["porches"].append(dict(rect=(bd[0] - 0.7, bd[1] - 1.0, bd[0] + 0.7, bd[1]), z=pz, post_top=pz, posts=[], beam=False,
                                    steps=dict(at=(bd[0], bd[1] - 1.0), dir=(0, -1), width=1.1, mat="concrete"), skirt_mat="found"))
    for d_ in spec["doors"]:
        if d_["name"] == "wing_out":
            spec["porches"].append(dict(rect=(d_["at"][0] - 0.7, d_["at"][1] - 1.0, d_["at"][0] + 0.7, d_["at"][1]), z=pz, post_top=pz,
                                        posts=[], beam=False, steps=dict(at=(d_["at"][0], d_["at"][1] - 1.0), dir=(0, -1), width=1.1,
                                                                         mat="concrete"), skirt_mat="found"))
    # ---- windows: every exterior wall segment of every block (ground floor + upper floor when full height)
    wtype = dget(tr, "windows").get("type", "1over1")
    shutters = bool(dget(tr, "windows").get("shutters", False))
    cols = 1 if wtype in ("1over1", "picture", "sliding", "casement") else (2 if wtype in ("2over2",) else 3)
    doors_pts = [d_["at"] for d_ in spec["doors"]]
    for bl in spec["blocks"]:
        bx0, by0, bx1, by1 = bl["rect"]
        segs_all = [((bx0, by0), (bx1, by0)), ((bx1, by1), (bx0, by1)), ((bx0, by1), (bx0, by0)), ((bx1, by0), (bx1, by1))]
        segs = []
        for (a, c) in segs_all:
            # skip walls shared with another block
            mid = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
            shared = any(ob is not bl and ob["rect"][0] - 0.01 <= mid[0] <= ob["rect"][2] + 0.01 and ob["rect"][1] - 0.01 <= mid[1] <= ob["rect"][3] + 0.01
                         for ob in spec["blocks"])
            if not shared:
                segs.append((a, c))
        wh = 1.45 if tr.get("year_built", 1920) < 1945 else 1.3
        windows_for(spec, segs, 0, wh, 0.8, "dh", cols, shutters, doors_pts, floor=0, own=bl)
        if len(bl["floors"]) > 1 and not bl.get("habitable_attic"):
            windows_for(spec, segs, 1, wh - 0.05, 0.8, "dh", cols, shutters, [], floor=1, own=bl)
        elif bl.get("habitable_attic"):
            # gable ends only (the eave walls are knee walls)
            rd = bl["roof"].get("ridge", "x")
            ends = [s_ for s_ in segs if (abs(s_[0][0] - s_[1][0]) < 0.01) == (rd == "x")]
            windows_for(spec, ends, 1, 1.1, 0.6, "dh", cols, False, [], spacing=3.0, floor=1, own=bl)
    # a picture window for mid-century living rooms
    if wtype == "picture" or (tr.get("year_built", 1920) >= 1945 and rnd.random() < 0.5):
        lr = [r for r in spec["rooms"] if r["name"] == "LR"]
        if lr:
            rx0_, ry0_, rx1_, ry1_ = lr[0]["rect"]
            if abs(ry1_ - yf) < 0.01 and rx1_ - rx0_ > 2.6:
                cxw = (rx0_ + rx1_) / 2
                if abs(cxw - fd[0]) > 1.6:
                    spec["windows"] = [w_ for w_ in spec["windows"] if not (w_.get("floor", 0) == 0 and abs(w_["at"][1] - yf) < 0.01 and rx0_ < w_["at"][0] < rx1_)]
                    spec["windows"].append(dict(at=(cxw, yf), w=2.0, sill=0.7, h=1.5, kind="picture", cols=3, floor=0))
    # ---- chimneys + a fireplace in the living room for older / fancier houses
    ch_list = tr.get("chimneys") or []
    top_z = wall_top + (W / 2 if roof.get("ridge", "x") == "y" else D / 2) * math.tan(math.radians(roof["pitch"])) + 0.9
    for i_ch, chn in enumerate(ch_list[:2]):
        # every chimney stands against an exterior wall, 0.4 m of its 0.55 m outside the face, so
        # no stack ever lands in a room, hall or door swing
        if chn in ("left_end", "exterior_left"):
            at = (x0 - 0.2, y0 + D * 0.5)
        elif chn in ("right_end", "exterior_right"):
            at = (x1 + 0.2, y0 + D * 0.5)
        elif chn == "center":
            at = ((x0 + x1) / 2 + (1.2 if not mirror else -1.2), y0 - 0.2)
        else:
            at = ((x0 + x1) / 2 + (0.8 if i_ch else -0.8), y0 - 0.2)
        # slide along its wall to the nearest spot 1.3 m clear of every door (and its stoop); none: no chimney
        along_x = at[1] < y0
        lo, hi = (x0 + 0.5, x1 - 0.5) if along_x else (y0 + 0.5, yf - 0.5)
        c0 = at[0] if along_x else at[1]
        spots = sorted((lo + 0.1 * k for k in range(int((hi - lo) / 0.1) + 1)), key=lambda c: abs(c - c0))
        c = next((c for c in spots if all(math.dist((c, at[1]) if along_x else (at[0], c), d_["at"]) >= 1.3
                                          for d_ in spec["doors"] if d_.get("floor", 0) == 0)), None)
        if c is None:
            continue
        at = (c, at[1]) if along_x else (at[0], c)
        spec["windows"] = [w_ for w_ in spec["windows"] if math.dist(w_["at"], at) > 0.9]
        spec["chimneys"].append(dict(at=at, w=0.55, d=0.55, z0=0.0, top=top_z))
    # a corner turret hides the upstairs windows it stands over
    tw_tr = tr.get("tower") if isinstance(tr.get("tower"), dict) else ({"position": "front_corner"} if tr.get("turret") else None)
    if tw_tr and tw_tr.get("position", "front_corner") == "front_corner":
        tcx, tcy, tr_ = turret_at(x0, x1, yf, mirror)
        spec["windows"] = [w_ for w_ in spec["windows"] if w_.get("floor", 0) == 0 or math.dist(w_["at"], (tcx, tcy)) > tr_ + 0.6]
    # ---- build the house
    house = gh.House(b, spec)
    house.build()
    # ---- front cross gables (Tudor / Queen Anne): steep gables flush with the front wall, their
    # ridges running back into the main roof
    if cross_gables and (roof["type"] == "hip" or roof.get("ridge") == "x"):
        cp = b.part("cross_gables-col")
        tw_side = (x1 if not mirror else x0) if (tr.get("turret") or (isinstance(tr.get("tower"), dict)
                                                  and tr["tower"].get("position", "front_corner") == "front_corner")) else None
        for k in range(cross_gables):
            gw = min(4.2, (x1 - x0) * (0.42 if cross_gables == 1 else 0.3))
            # one gable: off-centre, away from a corner turret; two: a big and a small one
            t = 0.3 if (tw_side is None or tw_side == x1) else 0.7
            if cross_gables == 2:
                t, gw = (0.28, gw) if k == 0 else (0.72, gw * 0.75)
            gcx = x0 + (x1 - x0) * (t if not mirror else 1 - t)
            gx0, gx1 = gcx - gw / 2, gcx + gw / 2
            gp = min(62.0, roof["pitch"] + (15.0 if arch == "tudor_revival" else 5.0))
            depth = min((yf - y0) / 2, gw / 2 * math.tan(math.radians(gp)) / max(0.3, math.tan(math.radians(roof["pitch"]))))
            peak = wall_top + gw / 2 * math.tan(math.radians(gp))
            for fy in (yf + 0.001, yf + 0.002):
                tri = [(gx0, fy, wall_top), (gx1, fy, wall_top), (gcx, fy, peak)]
                cp.face(tri if fy < yf + 0.0015 else list(reversed(tri)), "siding")
            g.gable_roof(cp, gx0, gx1, yf - depth, yf, wall_top, gp, 0.3, 0.3, 0.12, "roof", "roof_under",
                         ridge_axis="y", fascia="trim")
    # ---- towers, turrets and cupolas (exterior: above the porch roof and the eaves, clear of the rooms)
    towers(b, tr, x0, x1, y0, yf, floors, wall_top, roof, fl1 + min(h - 0.1, 2.5) + 0.55, mirror)
    # ---- dormers (exterior: small gabled boxes on the roof)
    dms = [(dm.get("side", "front") if isinstance(dm, dict) else "front") for dm in (tr.get("dormers") or [])[:3]]
    tw_c = isinstance(tr.get("tower"), dict) and tr["tower"].get("position") == "front_center"
    for k_dm, side in enumerate(dms):
        if roof["type"] not in ("gable", "gambrel", "hip"):
            break
        if side not in ("front", "rear"):
            continue
        # spread evenly along the side (a front-centre tower takes the middle)
        same = [i for i, s_ in enumerate(dms) if s_ == side]
        n_dm, i_dm = len(same), same.index(k_dm)
        slots = [(x0 + (x1 - x0) * (j + 1) / (n_dm + 1)) for j in range(n_dm)]
        if tw_c and side == "front":
            slots = [x0 + (x1 - x0) * t for t in (0.2, 0.8, 0.35)][:n_dm]
        yy = yf if side == "front" else y0
        zb = wall_top + 0.4
        dx0 = slots[i_dm] - 0.8
        inset = 0.9 * (1 if side == "front" else -1)
        dp = b.part("dormers-col")
        yA, yB = sorted((yy - inset, yy - inset * 0.1))
        dp.box((dx0, yA, zb), (dx0 + 1.6, yB, zb + 1.2), "siding")
        # dormer window in the dormer's outer face (frame: origin at one corner, u along the face, w_in inward)
        fo = g.Vector(((dx0 + 1.6) if side == "front" else dx0, yB if side == "front" else yA, 0))
        fu_ = g.Vector((-1, 0, 0)) if side == "front" else g.Vector((1, 0, 0))
        fw = g.Vector((0, -1, 0)) if side == "front" else g.Vector((0, 1, 0))
        g.window(b, "dormer_windows", (fo, fu_, fw, g.Vector((0, 0, 1))), 0.4, 0.8, zb + 0.25, zb + 1.0, 0.05,
                 sash_rows=2, sash_cols=1, glass_name="glass", mats={"trim": "trim"})
        g.gable_roof(dp, dx0 - 0.1, dx0 + 1.7, yA - 0.1, yB + 0.1, zb + 1.2, 40, 0.1, 0.05, 0.1, "roof", "trim", ridge_axis="y", fascia="trim")
    # ---- yard: walk, steps to the street, mailbox with the family name, fence, garage, extras
    yback = min(bl["rect"][1] for bl in spec["blocks"])       # a rear wing pushes the back yard back
    yard(b, rec, tr, names, lot_w, lot_d, x0, x1, yback, yf, porch_d, fd, garage, gar_w, mirror, rnd, fl1, fenced)
    return b


def _pyramid(p, cx, cy, hw, z0, z1, mat):
    """Square pyramid roof (half-width hw at the eave z0, apex at z1)."""
    q = [(cx - hw, cy - hw, z0), (cx + hw, cy - hw, z0), (cx + hw, cy + hw, z0), (cx - hw, cy + hw, z0)]
    apex = (cx, cy, z1)
    for k in range(4):
        p.face([q[k], q[(k + 1) % 4], apex], mat)
    p.face(list(reversed(q)), mat)


def _windows_around(p, c, r, n, z0, z1, every=2):
    """Tall glazed panes on every `every`-th face of an n-sided tower of radius r (flat-to-flat)."""
    for k in range(0, n, every):
        a = 2 * math.pi * (k + 0.5) / n
        f = (g.Vector((c[0] + math.cos(a) * (r + 0.01), c[1] + math.sin(a) * (r + 0.01), 0)),
             g.Vector((-math.sin(a), math.cos(a), 0)), g.Vector((math.cos(a), math.sin(a), 0)), g.Vector((0, 0, 1)))
        pw = min(0.7, 2 * r * math.tan(math.pi / n) - 0.25)
        p.obox(f, (-pw / 2 - 0.05, 0.0, z0 - 0.05), (pw / 2 + 0.05, 0.04, z1 + 0.05), "trim")
        p.obox(f, (-pw / 2, 0.04, z0), (pw / 2, 0.06, z1), "glass")


def turret_at(x0, x1, yf, mirror):
    """Centre and radius of a front-corner turret (the corner away from the entry side)."""
    return (x1 - 0.35 if not mirror else x0 + 0.35), yf - 0.35, 1.15


def towers(b, tr, x0, x1, y0, yf, floors, wall_top, roof, porch_roof_z, mirror):
    """Queen Anne corner turrets, Italianate front towers and rooftop cupolas (traits tower / turret /
    cupola).  Exterior only: a corner turret is corbelled out above the porch roof, a front tower rises
    from the eave on the front wall, a cupola sits on the roof's peak -- none reaches into a room."""
    tw = tr.get("tower") if isinstance(tr.get("tower"), dict) else ({"position": "front_corner", "top": "spire"}
                                                                    if tr.get("turret") else None)
    tan_p = math.tan(math.radians(roof.get("pitch", 35)))
    peak = wall_top + (min(x1 - x0, yf - y0) / 2) * tan_p
    if tw:
        p = b.part("tower-col")
        if tw.get("position", "front_corner") == "front_corner":
            # octagonal turret engaging the front corner away from the entry side
            cx, cy, r = turret_at(x0, x1, yf, mirror)
            z0 = max(porch_roof_z, floors[1][0] - 0.4 if len(floors) > 1 else wall_top - 1.2)
            z1 = max(wall_top + 1.2, peak - 0.6)
            p.cylinder((cx, cy), r * 0.55, z0 - 0.7, z0, "trim", n=8, r1=r)          # corbel
            p.cylinder((cx, cy), r, z0, z1, "siding", n=8)
            p.cylinder((cx, cy), r + 0.08, z1, z1 + 0.18, "trim", n=8)
            if tw.get("top", "spire") == "spire":
                p.cylinder((cx, cy), r + 0.2, z1 + 0.18, z1 + 0.18 + 2.8 * r, "roof", n=8, r1=0.03)
            else:
                p.cylinder((cx, cy), r + 0.2, z1 + 0.18, z1 + 0.18 + 0.9 * r, "roof", n=8, r1=0.3)
            _windows_around(p, (cx, cy), r * math.cos(math.pi / 8), 8, z0 + 0.5, min(z0 + 1.9, z1 - 0.3))
        else:
            # square tower centred on the front wall, rising from the eave
            hw = 1.2
            cx = (x0 + x1) / 2
            z0, z1 = wall_top - 0.3, max(peak + 1.0, wall_top + 3.0)
            p.box((cx - hw, yf - 2 * hw + 0.1, z0), (cx + hw, yf + 0.1, z1), "siding")
            p.box((cx - hw - 0.12, yf - 2 * hw, z1), (cx + hw + 0.12, yf + 0.22, z1 + 0.25), "trim")
            for sx in (-1, 1):
                pf = (g.Vector((cx + sx * 0.5, yf + 0.11, 0)), g.Vector((1, 0, 0)), g.Vector((0, 1, 0)), g.Vector((0, 0, 1)))
                p.obox(pf, (-0.3, 0.0, z1 - 1.6), (0.3, 0.04, z1 - 0.4), "trim")
                p.obox(pf, (-0.25, 0.04, z1 - 1.55), (0.25, 0.06, z1 - 0.45), "glass")
            top = tw.get("top", "flat")
            if top == "gable":
                g.gable_roof(p, cx - hw - 0.2, cx + hw + 0.2, yf - 2 * hw - 0.1, yf + 0.3, z1 + 0.25, 45, 0.1, 0.1, 0.1,
                             "roof", "trim", ridge_axis="y", fascia="trim")
            elif top == "spire":
                p.prism([(cx - hw - 0.15, yf - 2 * hw - 0.05), (cx + hw + 0.15, yf - 2 * hw - 0.05),
                         (cx + hw + 0.15, yf + 0.25), (cx - hw - 0.15, yf + 0.25)], z1 + 0.25, z1 + 0.3, "trim")
                _pyramid(p, cx, yf - hw + 0.1, hw + 0.15, z1 + 0.3, z1 + 0.3 + 3.2, "roof")
            else:
                p.box((cx - hw - 0.25, yf - 2 * hw - 0.15, z1 + 0.25), (cx + hw + 0.25, yf + 0.35, z1 + 0.4), "trim")
    if tr.get("cupola") and roof.get("type") in ("hip", "gable", "gambrel"):
        # square belvedere on the peak, glazed all round under a low hip
        p = b.part("cupola-col")
        cx, cy = (x0 + x1) / 2, (y0 + yf) / 2
        hw = min(1.4, (min(x1 - x0, yf - y0)) * 0.2)
        z0, z1 = peak - 0.9, peak + 1.3
        p.box((cx - hw, cy - hw, z0), (cx + hw, cy + hw, z1), "siding")
        for (fx, fy, ux, uy) in ((0, 1, 1, 0), (0, -1, -1, 0), (1, 0, 0, -1), (-1, 0, 0, 1)):
            pf = (g.Vector((cx + fx * (hw + 0.01), cy + fy * (hw + 0.01), 0)), g.Vector((ux, uy, 0)),
                  g.Vector((fx, fy, 0)), g.Vector((0, 0, 1)))
            p.obox(pf, (-hw + 0.25, 0.0, peak + 0.1), (hw - 0.25, 0.04, z1 - 0.2), "glass")
        p.box((cx - hw - 0.25, cy - hw - 0.25, z1), (cx + hw + 0.25, cy + hw + 0.25, z1 + 0.15), "trim")
        _pyramid(p, cx, cy, hw + 0.3, z1 + 0.15, z1 + 0.75, "roof")


def yard(b, rec, tr, names, lot_w, lot_d, x0, x1, y0, yf, porch_d, fd, garage, gar_w, mirror, rnd, fl1, fenced):
    front = lot_d / 2
    walk = b.part("walk-col")
    walk.box((fd[0] - 0.55, yf + porch_d + 0.9, -0.02), (fd[0] + 0.55, front, 0.03), "sidewalk", sides="Z")
    fam = names.get("family") or "Smith"
    num = str(names.get("house_number") or rnd.randint(100, 999))
    gh.mailbox(b, (fd[0] + 1.5 if fd[0] + 2.2 < lot_w / 2 else fd[0] - 1.5, front - 0.4, 0.0), 0.0, fam.upper()[:14], num,
               "mail_black", "trim", "white_text")
    # house number beside the front door
    g.text_mesh(b, "sign_house_number", num, 0.12, (fd[0] + 0.75, yf + 0.02, fl1 + 1.7), math.pi, "black_text", extrude=0.01,
                font=FONT_SANS)
    yd = dget(tr, "yard")
    fence = yd.get("fence", "none") if fenced else "none"
    fy = front - 0.25
    if fence == "picket":
        gh.picket_fence(b, [(-lot_w / 2 + 0.2, fy), (lot_w / 2 - 0.2, fy)], 1.0, "trim", name="front_fence",
                        gate=(0, fd[0] + lot_w / 2 - 0.2 - 0.55, 1.1))
    elif fence == "chainlink":
        gh.chainlink_fence(b, [(-lot_w / 2 + 0.2, fy), (lot_w / 2 - 0.2, fy)], 1.1, gate=(0, fd[0] + lot_w / 2 - 0.2 - 0.55, 1.1))
    elif fence in ("iron", "split_rail", "privacy"):
        gh.picket_fence(b, [(-lot_w / 2 + 0.2, fy), (lot_w / 2 - 0.2, fy)], 1.1 if fence != "privacy" else 1.8,
                        "iron" if fence == "iron" else "furn_light", name="front_fence", gate=(0, fd[0] + lot_w / 2 - 0.2 - 0.55, 1.1),
                        spacing=0.13 if fence == "iron" else 0.11)
    elif fence == "hedge":
        hp = b.part("hedge-col")
        for sx0, sx1 in ((-lot_w / 2 + 0.3, fd[0] - 0.8), (fd[0] + 0.8, lot_w / 2 - 0.3)):
            if sx1 - sx0 > 0.4:
                hp.box((sx0, fy - 0.35, 0.0), (sx1, fy + 0.25, 0.95), "green_leaf")
    # the side and rear lot lines (research/buildings/LOTS.md §3, §5.5: fronts open; one side fenced or hedged from
    # behind the house's front to the back; the rear line a fence, hedge or tree belt). Each lot draws its rear line
    # and ONE side line -- the one away from its driveway -- so neighbours don't double their shared fence.
    side_k, rear_k = yd.get("side", "none") or "none", yd.get("rear", "none") or "none"
    drive_left = garage != "none" and mirror
    sx_ = (lot_w / 2 - 0.15) if drive_left else (-lot_w / 2 + 0.15)
    yb_ = -lot_d / 2 + 0.15
    ys_ = min(yf - 1.0, lot_d / 2 - 3.0)
    for kind_, pts_ in ((side_k, [(sx_, ys_), (sx_, yb_)]), (rear_k, [(-lot_w / 2 + 0.15, yb_), (lot_w / 2 - 0.15, yb_)])):
        if kind_ == "none" or math.dist(*pts_) < 2.0:
            continue
        nm_ = "side_fence" if pts_[0][0] == pts_[1][0] else "rear_fence"
        if kind_ == "chainlink":
            gh.chainlink_fence(b, pts_, 1.2, name=nm_)
        elif kind_ == "privacy":
            gh.picket_fence(b, pts_, 1.8, "furn_light", name=nm_, spacing=0.105)
        elif kind_ == "picket":
            gh.picket_fence(b, pts_, 1.0, "trim", name=nm_)
        elif kind_ in ("hedge", "tree_line"):
            hp = b.part(f"{nm_}_hedge-col")
            hh_ = 1.5 if kind_ == "hedge" else 2.8
            (ax_, ay_), (bx_, by_) = pts_
            hp.box((min(ax_, bx_) - 0.35, min(ay_, by_) - 0.35, 0.0), (max(ax_, bx_) + 0.35, max(ay_, by_) + 0.35, hh_), "green_leaf")
    # garage
    gd = 6.2
    if garage.startswith("detached") and y0 - 4.0 - gd < -lot_d / 2 + 0.4:
        garage = "none"
    if garage.startswith("detached"):
        gw = 3.6 if garage == "detached_1" else 6.0
        gx0 = (x1 - gw) if not mirror else x0
        gy1 = max(y0 - 4.2, -lot_d / 2 + 0.4 + gd)      # clear of the back stoop and the carriage doors' swing
        garage_building(b, (gx0, gy1 - gd, gx0 + gw, gy1), 2 if garage == "detached_2" else 1, rnd)
        dp = b.part("driveway-col")
        dx0, dx1 = gx0 + 0.3, gx0 + gw - 0.3
        if not (dx1 < x0 - 0.2 or dx0 > x1 + 0.2):
            # the house is in the way: run the driveway down the side yard instead
            side_x = (x1 + 0.3, lot_w / 2 - 0.2) if not mirror else (-lot_w / 2 + 0.2, x0 - 0.3)
            if side_x[1] - side_x[0] >= 2.4:
                dp.box((side_x[0], gy1, -0.02), (side_x[1], front, 0.03), "concrete", sides="Z")
        else:
            dp.box((dx0, gy1, -0.02), (dx1, front, 0.03), "concrete", sides="Z")
    elif garage.startswith("attached") or garage == "carport":
        gw = gar_w
        gx0 = (x1 + 0.0) if not mirror else (x0 - gw)
        if garage == "carport":
            cp = b.part("carport-col")
            for (px, py) in ((gx0 + 0.15, yf - 0.3), (gx0 + gw - 0.15, yf - 0.3), (gx0 + 0.15, yf - 5.0), (gx0 + gw - 0.15, yf - 5.0)):
                cp.box((px - 0.06, py - 0.06, 0.0), (px + 0.06, py + 0.06, 2.4), "steel")
            cp.box((gx0 - 0.1, yf - 5.3, 2.4), (gx0 + gw + 0.1, yf, 2.5), "trim")
        else:
            garage_building(b, (gx0, yf - 6.4, gx0 + gw, yf - 0.4), 2 if garage == "attached_2" else 1, rnd,
                            side_door_x=gx0 + gw if not mirror else gx0)
        b.part("driveway-col").box((gx0 + 0.2, yf - 0.4, -0.02), (gx0 + gw - 0.2, front, 0.03), "concrete", sides="Z")
    # extras in the back yard: a row clear of the back stoops (and their doors' swing) and the garage
    extras = yd.get("extras") or []
    taken = []
    if garage.startswith("detached"):      # the garage, its apron and a side-yard driveway
        taken.append((gx0 - 0.5 if not mirror else -lot_w / 2, gy1 - gd - 0.5, gx0 + gw + 0.5 if mirror else lot_w / 2, gy1 + 1.8))
    for ex in extras[:3]:
        hx, hy = EXTRA_HALF.get(ex, (0.8, 0.8))
        cy = min(y0 - 3.2 - hy, -lot_d / 2 + 0.6 + hy + rnd.uniform(0.0, 1.5))
        if cy - hy < -lot_d / 2 + 0.3 or cy + hy > y0 - 3.2:
            continue
        for cx in (-lot_w / 2 + 0.6 + hx, lot_w / 2 - 0.6 - hx, 0.0):
            r = (cx - hx, cy - hy, cx + hx, cy + hy)
            if all(r[2] < t[0] or r[0] > t[2] or r[3] < t[1] or r[1] > t[3] for t in taken):
                taken.append(r)
                yard_extra(b, ex, (cx, cy), rnd)
                break


# half extents (x, y) of the yard extras, for placing them
EXTRA_HALF = {"shed": (1.1, 1.0), "clothesline": (2.05, 0.5), "swing_set": (1.35, 0.75), "garden": (1.5, 1.0),
              "doghouse": (0.55, 0.65), "flagpole": (0.1, 0.1), "birdbath": (0.1, 0.1), "woodpile": (1.0, 0.3),
              "tire_swing": (0.4, 0.8), "above_ground_pool": (1.8, 1.8)}


def garage_building(b, rect, bays, rnd, side_door_x=None):
    """A frame garage with hinged carriage doors (one pair per bay) and a side service door (in the
    wall at side_door_x; an attached garage passes its outer side)."""
    gx0, gy0, gx1, gy1 = rect
    spec = dict(t_ext=0.12, t_int=0.1, era="modern",
                mats=dict(ext="siding", int="siding", roof="roof", roof_under="roof_under", found="concrete", floor="concrete",
                          ceiling="roof_under", trim="trim", door="door", fascia="trim", porch="concrete", post="trim", furn="furniture"),
                blocks=[dict(name="garage", rect=rect, floors=[(0.1, 2.7)], wall_top=2.85, found_top=0.05,
                             roof=dict(type="gable", ridge="y", pitch=28, eave_oh=0.3, rake_oh=0.2, thick=0.12))],
                rooms=[dict(name="GAR", rect=rect, type=None)], doors=[], windows=[], stairs=[], rails=[], porches=[],
                chimneys=[], fireplaces=[], furnish=False)
    bw = (gx1 - gx0) / bays
    for k in range(bays):
        spec["doors"].append(dict(name=f"garage_{k}", at=(gx0 + bw * (k + 0.5), gy1), w=min(2.6, bw - 0.4), h=2.15, ext=True, leaves=2,
                                  out=True, panels=[(0.1, 0.55, 0.9, 0.9), (0.1, 0.1, 0.9, 0.5)]))
    spec["doors"].append(dict(name="garage_side", at=(gx1 if side_door_x is None else side_door_x, (gy0 + gy1) / 2), w=0.8, ext=True))
    spec["windows"].append(dict(at=((gx0 + gx1) / 2, gy0), w=0.8, sill=1.2, h=0.7, kind="dh", cols=2))
    gh.House(b, spec).build()


def yard_extra(b, ex, at, rnd):
    x, y = at
    p = b.part(f"yard_{ex}-col")
    if ex == "shed":
        p.box((x - 1.0, y - 0.9, 0.0), (x + 1.0, y + 0.9, 2.0), "siding")
        g.gable_roof(p, x - 1.1, x + 1.1, y - 1.0, y + 1.0, 2.0, 30, 0.1, 0.1, 0.08, "roof", "trim", ridge_axis="y", fascia="trim")
    elif ex == "clothesline":
        for dx in (-2.0, 2.0):
            p.box((x + dx - 0.04, y - 0.04, 0.0), (x + dx + 0.04, y + 0.04, 1.9), "steel")
            p.box((x + dx - 0.04, y - 0.5, 1.8), (x + dx + 0.04, y + 0.5, 1.86), "steel")
        for dy in (-0.4, 0.0, 0.4):
            p.box((x - 2.0, y + dy - 0.005, 1.84), (x + 2.0, y + dy + 0.005, 1.85), "rope")
    elif ex == "swing_set":
        for dx in (-1.2, 1.2):
            for dy in (-0.7, 0.7):
                p.box((x + dx - 0.04, y + dy - 0.04, 0.0), (x + dx + 0.04, y + dy + 0.04, 2.1), "steel")
        p.box((x - 1.3, y - 0.05, 2.05), (x + 1.3, y + 0.05, 2.15), "steel")
        for sx in (-0.5, 0.5):
            p.box((x + sx - 0.22, y - 0.12, 0.45), (x + sx + 0.22, y + 0.12, 0.5), "vinyl_red")
    elif ex == "garden":
        p.box((x - 1.5, y - 1.0, 0.0), (x + 1.5, y + 1.0, 0.08), "burlap")
        for i in range(10):
            p.box((x - 1.3 + (i % 5) * 0.6, y - 0.6 + (i // 5) * 1.0, 0.08), (x - 1.2 + (i % 5) * 0.6, y - 0.5 + (i // 5) * 1.0, 0.45), "green_leaf")
    elif ex == "doghouse":
        p.box((x - 0.5, y - 0.6, 0.0), (x + 0.5, y + 0.6, 0.8), "siding")
        g.gable_roof(p, x - 0.55, x + 0.55, y - 0.65, y + 0.65, 0.8, 35, 0.05, 0.05, 0.05, "roof", "trim", ridge_axis="y", fascia="trim")
    elif ex == "flagpole":
        p.cylinder((x, y), 0.05, 0.0, 6.0, "steel", n=8, r1=0.03)
    elif ex == "birdbath":
        p.cylinder((x, y), 0.08, 0.0, 0.7, "concrete", n=8)
        p.cylinder((x, y), 0.3, 0.7, 0.8, "concrete", n=12)
    elif ex == "woodpile":
        for i in range(3):
            p.box((x - 1.0, y - 0.3 + i * 0.0, 0.0 + i * 0.3), (x + 1.0, y + 0.3, 0.3 + i * 0.3), "bark")
    elif ex == "tire_swing":
        p.box((x - 0.15, y - 0.15, 0.0), (x + 0.15, y + 0.15, 4.0), "bark")
        p.box((x - 0.05, y + 0.1, 3.2), (x + 0.05, y + 1.4, 3.3), "bark")
        p.cylinder((x, y + 1.3), 0.35, 0.5, 0.75, "tire", n=12)
    elif ex == "above_ground_pool":
        p.cylinder((x, y), 1.8, 0.0, 1.2, "steel", n=20)
    else:
        return
