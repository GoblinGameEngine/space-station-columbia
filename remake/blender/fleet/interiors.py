"""
interiors.py -- the fittings that make a cabin complete (research/vehicles/INTERIORS.md; the user, 2026-10-05: "All of the
vehicles need complete interiors"). Each is its own token, built on the shell the loft and builder made:

  every cabin      door cards on every door (armrest, pull cup, window crank, a chrome strip -- carried by the door),
                   pedals, a rear-view mirror, sun visors, a dome lamp, a centre console between two front seats
  by type          grab poles and ceiling rails (buses, trolleys, trains, the elevator car), luggage racks (trains, the
                   shuttle's overhead bins), a stretcher and the medics' cabinets (ambulance, rescue aerostat), cargo
                   shelving (service, parcel and delivery vans, the mail truck), a serving counter (food and ice-cream
                   trucks), a casket deck (hearse), a partition (limousine), a bed, dinette and galley (motorhome, camper)

Coordinates: Blender (y forward, z up), the builder's frame.
"""
import math

from mathutils import Matrix, Vector

SIDES = ("R", "L")


def _x_in(b, y, z):
    """The cabin's inner face (the lining) at y, z."""
    L = b.L
    return b.surf_x(y, z) - getattr(L, "int_off", 0.06) - 0.012


def _wells(L):
    """The wheel housings inside the body: [(y front, y back, x inner, z top)] (none when the wheels are outside it)."""
    if getattr(L, "wheels_out", False) or not hasattr(L, "arch_half"):
        return []
    return [(ax + L.arch_half + 0.04, ax - L.arch_half - 0.04, L.well_x - 0.05, L.hump_z() + 0.03) for ax in getattr(L, "axles", [])]


def wbox(me, L, c, half, m):
    """A box that keeps off the wheel housings: where it reaches out over a well and down below the housing's top, it
    is cut there and stands on the housing instead (a cabinet over the arch, as in a real van)."""
    x0, x1 = abs(c[0]) - half[0], abs(c[0]) + half[0]
    yt, yb, zb, zt = c[1] + half[1], c[1] - half[1], c[2] - half[2], c[2] + half[2]
    cut = [w for w in _wells(L) if x1 > w[2] and zb < w[3] and w[0] > yb and w[1] < yt]
    if not cut:
        me.box(c, half, m)
        return
    edges, y = [], yt                                      # (the spans clear of the wells, then over each well)
    for w in sorted(cut, key=lambda w: -w[0]):
        if w[0] < y:
            edges.append((y, w[0], zb))
        edges.append((min(y, w[0]), max(yb, w[1]), w[3]))
        y = max(yb, w[1])
    if y > yb:
        edges.append((y, yb, zb))
    for a, b_, z0 in edges:
        if a - b_ > 0.02 and zt - z0 > 0.02:
            me.box((c[0], (a + b_) / 2, (z0 + zt) / 2), (half[0], (a - b_) / 2, (zt - z0) / 2), m)


def in_well(L, x, y):
    return any(abs(x) > w[2] and w[1] <= y <= w[0] for w in _wells(L))


def door_cards(b):
    """On each door's inner face: a padded card with an armrest, a pull cup, the window crank and a chrome strip at the
    belt -- 1970s vinyl over board. Each card rides on its door (the closer's parts)."""
    L = b.L
    for sd in SIDES:
        sx = 1 if sd == "R" else -1
        for d in b.doors_on(sd):
            cid = d["id"] + sd
            cl = next((c for c in b.CLOSERS if c["id"] == cid), None)
            if cl is None:
                continue
            mid = "card_" + cid
            me = b.mod(mid, "leaf_trim", "card_" + d["id"], sd, hp=80, mass=2)
            y0, y1 = d["y0"] - 0.06, d["y1"] + 0.06
            ym = (y0 + y1) / 2
            zb = L.belt - 0.04
            x = _x_in(b, ym, zb - 0.25) * sx
            ln = (y0 - y1)
            me.box((x - sx * 0.004, ym, zb - 0.02), (0.006, ln / 2, 0.012), "chrome")                     # the belt strip
            me.box((x - sx * 0.03, y1 + ln * 0.35, zb - 0.24), (0.035, min(0.22, ln * 0.3), 0.03), "seat")  # the armrest
            me.box((x - sx * 0.012, y1 + ln * 0.35, zb - 0.17), (0.012, 0.06, 0.02), "black")              # the pull cup
            cr = Vector((x - sx * 0.02, y0 - 0.12, zb - 0.12))                                              # the window crank
            me.lathe([(0.0, 0.03), (0.01, 0.03), (0.012, 0.0001)], "chrome", n=10, xf=Matrix.Translation(cr) @ Matrix.Rotation(sx * math.pi / 2, 4, "Z"))
            me.pipe([cr, cr + Vector((-sx * 0.02, 0, -0.06))], 0.006, "chrome", n=5)
            me.box((x - sx * 0.006, ym, zb - 0.14), (0.004, ln / 2 - 0.06, 0.07), "seat")                  # the vinyl insert
            me.box((x - sx * 0.005, ym, zb - 0.42), (0.004, ln / 2 - 0.04, 0.10), "carpet")                # the kick panel
            cl["parts"].append(mid)


def driver_bits(b, st):
    """The pedals, the rear-view mirror, the sun visors, the dome lamp, and the console between two front seats."""
    L = b.L
    dm = [m for m in b.MARKERS if m[0] == "seat_driver"]
    if not dm or not hasattr(L, "toe"):
        return
    H = Vector(dm[0][1])
    me = b.mod("cockpit", "dash", "cockpit", "C", hp=200, mass=6)
    py = min(H.y + 0.80, L.toe - 0.10)                                       # the pedals, at the toe board
    for dx_, w in ((0.13, 0.035), (-0.06, 0.06)):                            # accelerator, brake
        p = Vector((H.x + dx_, py, L.floor + 0.10))
        me.box(tuple(p), (w, 0.02, 0.07), "rubber", xf=Matrix.Translation(p) @ Matrix.Rotation(-0.6, 4, "X") @ Matrix.Translation(-p))
        me.pipe([p + Vector((0, 0.02, 0.06)), p + Vector((0, 0.12, 0.28))], 0.008, "black", n=5)
    hdr = getattr(L, "header", L.toe)
    zt = getattr(L, "headliner", L.crown) - 0.03
    m = Vector((0.0, hdr - 0.12, zt - 0.10))                                 # the mirror on its stalk
    me.pipe([m + Vector((0, 0.02, 0.10)), m], 0.008, "black", n=5)
    me.box(tuple(m), (0.12, 0.012, 0.035), "black")
    me.box(tuple(m - Vector((0, 0.013, 0))), (0.11, 0.002, 0.028), "chrome")
    hw = getattr(L, "half_w", 1.0) - getattr(L, "int_off", 0.06) - 0.08
    for sx in (1, -1):                                                       # the visors, folded up
        me.box((sx * min(0.42, hw * 0.5), hdr - 0.14, zt - 0.015), (min(0.17, hw * 0.4), 0.09, 0.012), "lining")
    lc = [k for k in b.MARKERS if k[0] == "light_cabin"]
    if lc:
        me.box(tuple(Vector(lc[0][1]) + Vector((0, 0, 0.02))), (0.09, 0.05, 0.012), "lining")
    rows = st.get("seats", L.spec.get("seats", []))
    if rows and len(rows[0]["xs"]) == 2 and abs(rows[0]["xs"][0] - rows[0]["xs"][1]) > 0.75:
        y0, y1 = min(L.toe - 0.3, H.y + 0.55), H.y - 0.30                      # the console between them
        me.box((0.0, (y0 + y1) / 2, L.floor + 0.18), (0.10, (y0 - y1) / 2, 0.18), "dash")
        me.box((0.0, (y0 + y1) / 2 - 0.1, L.floor + 0.37), (0.085, (y0 - y1) / 2 - 0.12, 0.01), "seat")
        k = Vector((0.0, y0 - 0.12, L.floor + 0.36))
        me.pipe([k, k + Vector((0, -0.02, 0.12))], 0.008, "chrome", n=5)                  # the drive selector
        me.lathe([(0.0, 0.025), (0.03, 0.02), (0.04, 0.0001)], "black", n=10, xf=Matrix.Translation(k + Vector((0, -0.02, 0.12))) @ Matrix.Rotation(-math.pi / 2, 4, "X"))


def _rows(L, st):
    return st.get("seats", L.spec.get("seats", []))


def grab_poles(b, st, racks=False, bins=False):
    """Grab poles at the aisle's edge in front of every other row (between it and the row ahead), a rail along the
    ceiling each side of the aisle; racks for luggage over the windows (a train's), or closed bins (the shuttle's)."""
    L = b.L
    rows = _rows(L, st)[1:]
    if not rows:
        return
    me = b.mod("fit_poles", "fittings", "grab_poles", "C", hp=300, mass=20)
    zt = getattr(L, "headliner", L.crown) - 0.02
    ax = max(0.15, min(abs(x) - r.get("w", 0.5) / 2 for r in rows for x in r["xs"]) - 0.02)   # (the aisle's edge)
    ys = [r["y"] for r in rows]
    for k, r in enumerate(sorted(rows, key=lambda r: -r["y"])):
        if k % 2 == 0:
            for sx in (1, -1):
                if any(x * sx > 0 for x in r["xs"]):
                    me.pipe([Vector((sx * ax, r["y"] + 0.49, L.floor)), Vector((sx * ax, r["y"] + 0.49, zt))], 0.018, "chrome", n=8)
    for sx in (1, -1):
        me.pipe([Vector((sx * ax, max(ys) + 0.5, zt - 0.10)), Vector((sx * ax, min(ys) - 0.4, zt - 0.10))], 0.016, "chrome", n=8)
    if racks or bins:
        me2 = b.mod("fit_racks", "fittings", "racks", "C", hp=200, mass=30)
        y0, y1 = max(ys) + 0.45, min(ys) - 0.45
        for sx in (1, -1):
            x = (_x_in(b, (y0 + y1) / 2, L.head - 0.05) - 0.06) * sx            # (the wall leans in over the head)
            if bins:                                                          # a closed overhead bin, its door a shade lighter
                me2.box((x - sx * 0.26, (y0 + y1) / 2, zt - 0.20), (0.22, (y0 - y1) / 2, 0.16), "lining")
                me2.box((x - sx * 0.485, (y0 + y1) / 2, zt - 0.22), (0.006, (y0 - y1) / 2 - 0.02, 0.13), "paint2")
            else:                                                             # an open rack of rods on brackets
                for k in range(5):
                    me2.pipe([Vector((x - sx * (0.06 + k * 0.07), y0, L.head + 0.08)), Vector((x - sx * (0.06 + k * 0.07), y1, L.head + 0.08))],
                             0.008, "chrome", n=5)
                y = y1
                while y < y0:
                    me2.pipe([Vector((x, y, L.head + 0.22)), Vector((x - sx * 0.36, y, L.head + 0.08))], 0.012, "chrome", n=6)
                    y += 1.2


def rear_area(b, st=None):
    """The space behind the front seats and ahead of any rows behind them: (y front, y back, floor) -- for a van's or
    an ambulance's fittings."""
    L = b.L
    dm = [m for m in b.MARKERS if m[0] == "seat_driver"]
    yf = (dm[0][1][1] - 0.45) if dm else L.toe - 1.0
    yb = getattr(L, "tail_in", L.tail) + 0.15
    for r in (_rows(L, st)[1:] if st is not None else []):          # (no st: the caller lays out round the rows itself)
        if r["y"] < yf:
            yb = max(yb, r["y"] + 0.55)
    return yf, yb, L.floor


def medical(b, st):
    """A stretcher on its cot along the left of the rear, the medics' cabinets along the right, an oxygen bottle, a
    monitor on the wall."""
    L = b.L
    yf, yb, f = rear_area(b, st)
    if yf - yb < 1.6:
        return
    me = b.mod("fit_medical", "fittings", "medical", "C", hp=300, mass=80)
    hw = getattr(L, "half_w", 1.0) - getattr(L, "int_off", 0.06)
    cx, ln = -hw + 0.42, min(1.95, yf - yb - 0.2)
    yc = yb + 0.1 + ln / 2
    wbox(me, L, (cx, yc, f + 0.58), (0.29, ln / 2, 0.06), "seat")                     # the mattress
    wbox(me, L, (cx, yc + ln / 2 - 0.25, f + 0.70), (0.27, 0.22, 0.08), "seat")       # (its raised head)
    for sx in (1, -1):
        me.pipe([Vector((cx + sx * 0.28, yc - ln / 2, f + 0.50)), Vector((cx + sx * 0.28, yc + ln / 2, f + 0.50))], 0.015, "chrome", n=6)
        for sy in (1, -1):
            me.pipe([Vector((cx + sx * 0.25, yc + sy * (ln / 2 - 0.15), f + 0.04)), Vector((cx + sx * 0.25, yc + sy * (ln / 2 - 0.15), f + 0.50))],
                    0.015, "chrome", n=6)
            me.lathe([(-0.02, 0.04), (0.02, 0.04)], "rubber", n=10, xf=Matrix.Translation((cx + sx * 0.25, yc + sy * (ln / 2 - 0.15), f + 0.04)) @
                     Matrix.Rotation(math.pi / 2, 4, "Z"))
    x = hw - 0.25                                                                # the cabinets: a base, lockers over
    ya, yz = yf - 0.32, yb + 0.1
    wbox(me, L, (x, (ya + yz) / 2, f + 0.45), (0.2, (ya - yz) / 2, 0.45), "paint2")
    wbox(me, L, (x - 0.05, (ya + yz) / 2, L.headliner - 0.24), (0.16, (ya - yz) / 2, 0.18), "paint2")
    k = yz + 0.2
    while k < ya - 0.1:
        wbox(me, L, (x - 0.205, k, f + 0.70), (0.004, 0.02, 0.06), "chrome")
        k += 0.45
    me.lathe([(0.0, 0.09), (0.8, 0.09), (0.9, 0.04)], "paint", n=12,                     # the oxygen, upright at its end
             xf=Matrix.Translation((x, yf - 0.15, f + 0.92)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    wbox(me, L, (x - 0.18, yc, getattr(L, "belt", f + 0.9) + 0.25), (0.02, 0.18, 0.13), "black")    # the monitor
    wbox(me, L, (x - 0.20, yc, getattr(L, "belt", f + 0.9) + 0.25), (0.002, 0.15, 0.10), "lcd")


def shelves(b, st):
    """Cargo shelving along both walls of the rear: uprights and three shelves a side."""
    L = b.L
    yf, yb, f = rear_area(b, st)
    if yf - yb < 1.0:
        return
    me = b.mod("fit_shelves", "fittings", "shelves", "C", hp=300, mass=60)
    hw = getattr(L, "half_w", 1.0) - getattr(L, "int_off", 0.06)
    top = getattr(L, "headliner", f + 1.7) - 0.15
    for sx in (1, -1):
        x = sx * (hw - 0.20)
        for k in range(3):
            z = f + 0.35 + k * (top - f - 0.35) / 2.2
            wbox(me, L, (x, (yf + yb) / 2, z), (0.19, (yf - yb) / 2 - 0.1, 0.012), "chrome")
        y = yb + 0.1
        while y <= yf - 0.1:
            wbox(me, L, (sx * (hw - 0.02), y, (f + top) / 2), (0.015, 0.015, (top - f) / 2), "black")
            wbox(me, L, (sx * (hw - 0.38), y, (f + top) / 2), (0.015, 0.015, (top - f) / 2), "black")
            y += 0.6


def counter(b, st):
    """A serving counter along the right of the rear, under its hatch: a worktop, the cabinets under it, a griddle and
    a chill box; a shelf along the left."""
    L = b.L
    yf, yb, f = rear_area(b, st)
    if yf - yb < 1.2:
        return
    me = b.mod("fit_counter", "fittings", "counter", "C", hp=300, mass=120)
    hw = getattr(L, "half_w", 1.0) - getattr(L, "int_off", 0.06)
    zc = f + 0.90
    wbox(me, L, (hw - 0.30, (yf + yb) / 2, (f + zc) / 2), (0.28, (yf - yb) / 2 - 0.1, (zc - f) / 2), "paint2")
    wbox(me, L, (hw - 0.30, (yf + yb) / 2, zc + 0.015), (0.30, (yf - yb) / 2 - 0.08, 0.015), "chrome")
    wbox(me, L, (hw - 0.30, yf - 0.45, zc + 0.04), (0.22, 0.25, 0.012), "black")
    wbox(me, L, (-hw + 0.30, (yf + yb) / 2, (f + zc) / 2), (0.28, 0.4, (zc - f) / 2), "chrome")
    wbox(me, L, (-hw + 0.12, (yf + yb) / 2, zc + 0.45), (0.10, (yf - yb) / 2 - 0.1, 0.012), "chrome")


def casket_deck(b, st):
    """A hearse's casket deck: a low platform on rollers the length of the rear, its brass rails."""
    L = b.L
    yf, yb, f = rear_area(b, st)
    me = b.mod("fit_casket", "fittings", "casket_deck", "C", hp=200, mass=40)
    me.box((0, (yf + yb) / 2, f + 0.06), (0.42, (yf - yb) / 2 - 0.05, 0.06), "wood")
    for sx in (1, -1):
        me.pipe([Vector((sx * 0.40, yf - 0.05, f + 0.16)), Vector((sx * 0.40, yb + 0.05, f + 0.16))], 0.012, "chrome", n=6)


def partition(b, st):
    """A limousine's partition behind the driver: a panel to the belt, glass over it."""
    L = b.L
    dm = [m for m in b.MARKERS if m[0] == "seat_driver"]
    if not dm:
        return
    y = dm[0][1][1] - 0.40
    hw = L.half_w - L.int_off - 0.02
    me = b.mod("fit_partition", "fittings", "partition", "C", hp=200, mass=30)
    me.box((0, y, (L.floor + L.belt) / 2), (hw, 0.03, (L.belt - L.floor) / 2), "wood")
    gl = b.mod("fit_partition_glass", "fittings", "partition_glass", "C", hp=40, mass=8, breaks="shatter")
    gl.box((0, y, (L.belt + L.headliner) / 2), (hw - 0.02, 0.006, (L.headliner - L.belt) / 2 - 0.02), "glass")


def living(b, st, C=None):
    """A motorhome's or a camper's: a bed across the back, a dinette (a table between two benches) ahead of it, the
    galley (a counter with its sink and hob) along the right."""
    L = b.L
    if C:
        yf, yb, f, hw, top = C["y0"] - 0.15, C["y1"] + 0.15, C["floor_z"], C["half_w"] - 0.08, C.get("top_z", C["floor_z"] + 2.0) - 0.1
    else:
        yf, yb, f = rear_area(b)
        hw, top = L.half_w - L.int_off - 0.02, L.headliner
    if yf - yb < 2.2:
        return
    me = b.mod("fit_living", "fittings", "living", "C", hp=300, mass=150)
    wbox(me, L, (0, yb + 0.95, f + 0.30), (hw - 0.02, 0.95, 0.30), "paint2")                      # the bed's base
    wbox(me, L, (0, yb + 0.95, f + 0.66), (hw - 0.06, 0.92, 0.06), "seat")                        # its mattress
    yd = yb + 2.2 + 0.55
    if yd + 0.6 < yf:
        x = -hw + 0.38
        wbox(me, L, (x, yd, f + 0.72), (0.34, 0.40, 0.025), "wood")                               # the dinette's table
        me.pipe([Vector((x, yd, f)), Vector((x, yd, f + 0.70))], 0.03, "chrome", n=8)
        for sy in (1, -1):
            wbox(me, L, (x, yd + sy * 0.62, f + 0.22), (0.36, 0.20, 0.22), "seat")
            wbox(me, L, (x, yd + sy * 0.80, f + 0.62), (0.36, 0.04, 0.22), "seat")
    yg0, yg1 = min(yf, yb + 4.2), yb + 2.1
    if yg0 - yg1 > 0.8:
        wbox(me, L, (hw - 0.30, (yg0 + yg1) / 2, f + 0.45), (0.29, (yg0 - yg1) / 2, 0.45), "wood")  # the galley
        wbox(me, L, (hw - 0.30, (yg0 + yg1) / 2, f + 0.915), (0.30, (yg0 - yg1) / 2 + 0.01, 0.015), "paint2")
        wbox(me, L, (hw - 0.30, yg0 - 0.30, f + 0.925), (0.18, 0.18, 0.006), "black")             # the hob
        me.lathe([(0.0, 0.14), (0.12, 0.14), (0.12, 0.0001)], "chrome", n=14, xf=Matrix.Translation((hw - 0.30, yg1 + 0.35, f + 0.935)) @
                 Matrix.Rotation(-math.pi / 2, 4, "X"))                                         # the sink (down into the top)
        wbox(me, L, (hw - 0.25, (yg0 + yg1) / 2, top - 0.25), (0.22, (yg0 - yg1) / 2, 0.20), "wood")  # its lockers above


def crew_stowage(b, st):
    """A cargo gondola's: a fold-down crew bench along the port wall, stowage lockers along the starboard one (slings,
    strops, the winch's spares)."""
    L = b.L
    yf, yb, f = rear_area(b, st)
    if yf - yb < 1.0:
        return
    me = b.mod("fit_crew", "fittings", "crew_stowage", "C", hp=300, mass=80)
    hw = L.half_w - L.int_off - 0.04
    wbox(me, L, (-(hw - 0.22), (yf + yb) / 2, f + 0.44), (0.21, (yf - yb) / 2 - 0.1, 0.04), "seat")
    for y in (yf - 0.2, yb + 0.2):
        me.pipe([Vector((-(hw - 0.05), y, f + 0.42)), Vector((-(hw - 0.40), y, f + 0.42)), Vector((-(hw - 0.40), y, f))], 0.015, "chrome", n=6)
    wbox(me, L, (-(hw - 0.03), (yf + yb) / 2, f + 0.78), (0.03, (yf - yb) / 2 - 0.1, 0.22), "seat")
    wbox(me, L, (hw - 0.25, (yf + yb) / 2, f + 0.60), (0.24, (yf - yb) / 2 - 0.1, 0.60), "paint2")
    k = yb + 0.35
    while k < yf - 0.2:
        wbox(me, L, (hw - 0.495, k, f + 0.62), (0.004, 0.02, 0.08), "chrome")
        k += 0.6


BY_TYPE = {
    "transit_bus": grab_poles, "sightseeing_trolley": grab_poles, "hotel_shuttle": grab_poles, "paratransit_van": grab_poles,
    "school_bus": grab_poles, "spoke_elevator_car": grab_poles,
    "passenger_train": lambda b, st: grab_poles(b, st, racks=True), "passenger_shuttle": lambda b, st: grab_poles(b, st, bins=True),
    "ambulance": medical, "rescue_aerostat": medical,
    "service_van": shelves, "parcel_van": shelves, "delivery_van": shelves, "mail_truck": shelves,
    "food_truck": counter, "ice_cream_truck": counter,
    "cargo_aerostat": crew_stowage, "supply_freighter": crew_stowage, "cargo_mule": crew_stowage, "hearse": casket_deck, "limousine": partition, "motorhome": living,
}


def fit(b, st, vtype, var=None):
    """Every cabin's fittings (the base type's build; a variant that moves the driver rebuilds the cockpit), then the
    type's own (a variant's replace the base type's: their modules are fit_*)."""
    if not getattr(b.L, "doors", None) and not any(m[0] == "seat_driver" for m in b.MARKERS):
        return
    if var is None:
        door_cards(b)
    if var is None or "driver" in var:
        driver_bits(b, st)
    fn = BY_TYPE.get(vtype)
    if fn:
        fn(b, st)
