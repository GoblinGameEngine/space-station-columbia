"""
carrow_tram.py -- the Carrow Coach Company's road tram body, in three section kinds (front, mid, rear),
each bolted onto a Steward tram board (godot_project/remake/vehicles/chassis/steward_tram.glb). Built
from Grok's tram references as a design reference, not a template (reference/grok/tram/: side,
three_quarter, front, rear, interior_aisle): cream and sea-teal, rounded ends with a big windscreen,
round lamps, chrome strips, roof fairings; Carrow's bronze for the badge and the keel line.

  flatpak run org.blender.Blender -b --factory-startup --python <abs carrow_tram.py> -- OUT_DIR RENDER_DIR

Writes OUT_DIR/carrow_tram_{front,mid,rear}.glb and OUT_DIR/carrow_tram.json (the modules: every
panel, pane, door leaf, seat and roof bay a separate object with its collision boxes, mass and hit
points -- the unit of destruction -- plus the doors, ramps and lights), and renders.

The user's rules (2026-10-01): the player can stand and walk inside (floor to ceiling >= 2.2 m, an
aisle about 1 m wide, open portals at the joints); the doors work; the windows are transparent;
several doors a side, of which the curbside (right) ones open by themselves at stops; one driver's
seat at the front; headlights and tail lights; the body is destructible.

Section frame = the board's: Blender Z up, +Y forward, X right, metres, z = 0 the ground, y = 0
midway between the axles (y = +-2.25). The Pattern's deck top is z = 0.50; the floor is on it.
Markers (empties): seat_*, seat_driver, stand_* / strap_*, exit_<door>, doorway_<door>,
light_head_*, light_tail_*, light_brake, light_cabin_*, light_dest.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import core  # noqa: E402
from kit.core import Mesh, lin, mat  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_DIR, RENDER_DIR = argv[0], argv[1]
TAU = math.tau

# ---------------------------------------------------------------- dimensions
WO = 1.275                  # outer half width (2.55 m)
WI = 1.215                  # inner half width
FLOOR = 0.55                # floor top (the deck is at 0.50)
CEIL = 2.80                 # the ceiling: 2.25 m of headroom
SKIRT = 0.30                # the skirt's lower edge
BELT = 1.05                 # the belt line (chrome strip): skirt below, the teal window band above
WIN0, WIN1 = 1.15, 2.30     # window sill and head
CANT = 2.62                 # the cant rail: the side meets the roof
HL = 4.2                    # the portal faces / the body's ends, either side of the middle
NOSE = 0.66                 # the nose's reach past HL (front and rear)
DOOR_W = 1.24
DOOR_H = 2.55               # door head (z); the opening starts at the floor
AXLES = (2.25, -2.25)
ARCH = 0.62                 # half the wheel arch's length
HOUSING = (0.66, 1.05)      # the wheel housings / podiums: |x| from 0.66 to the wall, up to z 1.05
AISLE_X = 0.21              # the aisle's centre line (2+1 seating: pairs on the left, singles on the right)
PORTAL = (0.64, 2.62)       # the joint portal: half width, head

DOORS = {                   # per section kind and side: door centres (y)
    "front": {"R": [3.45, 0.0], "L": [0.0, -3.45]},
    "mid": {"R": [3.45, 0.0], "L": [0.0, -3.45]},
    "rear": {"R": [0.0, -3.45], "L": [3.45, 0.0]},
}

# ---------------------------------------------------------------- materials
M = {}


def mats():
    M.clear()
    M.update({
        "cream": mat("cream", lin((232, 226, 206)), rough=0.35, metal=0.05),
        "teal": mat("teal", lin((52, 128, 124)), rough=0.35, metal=0.05),
        "chrome": mat("chrome", lin((205, 208, 212)), rough=0.12, metal=1.0),
        "bronze": mat("bronze", lin((160, 112, 56)), rough=0.3, metal=0.9),
        "rubber": mat("rubber", lin((28, 28, 30)), rough=0.85),
        "glass": mat("glass", lin((170, 196, 200)), rough=0.05, metal=0.0),
        "lining": mat("lining", lin((236, 232, 218)), rough=0.6),
        "cove": mat("cove", lin((58, 136, 132)), rough=0.5),
        "floor": mat("floor", lin((206, 200, 184)), rough=0.8),
        "ceiling": mat("ceiling", lin((240, 238, 230)), rough=0.6),
        "seat": mat("seat", lin((48, 132, 128)), rough=0.8),
        "shell": mat("shell", lin((228, 222, 204)), rough=0.4),
        "dash": mat("dash", lin((40, 52, 58)), rough=0.5),
        "gauge": mat("gauge", lin((236, 230, 210)), rough=0.4),
        "lamp_ceiling": mat("lamp_ceiling", lin((255, 252, 240)), emit=lin((255, 250, 235)), emit_strength=1.5),
        "lamp_head": mat("lamp_head", lin((255, 250, 230)), emit=lin((255, 246, 220)), emit_strength=3.0),
        "lamp_tail": mat("lamp_tail", lin((200, 20, 16)), emit=lin((255, 30, 20)), emit_strength=2.0),
        "lamp_amber": mat("lamp_amber", lin((240, 140, 20)), emit=lin((255, 150, 20)), emit_strength=1.2),
        "dest": mat("dest", lin((40, 30, 10)), emit=lin((255, 170, 40)), emit_strength=1.4),
        "glass_dark": mat("glass_dark", lin((60, 78, 84)), rough=0.15, metal=0.3),
        "tyre": mat("tyre", lin((30, 30, 32)), rough=0.85),
    })
    g = M["glass"]
    g.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.22
    g.surface_render_method = "BLENDED"
    for m in M.values():
        m.use_backface_culling = False


# ---------------------------------------------------------------- modules (the unit of destruction)
MODS = {}          # id -> {kind, hp, mass_kg, breaks, boxes: [[cx, cy, cz, sx, sy, sz]] (Blender frame)}
MESH = {}          # id -> Mesh


def mod(mid, kind, hp, mass, breaks="detach"):
    if mid not in MODS:
        MODS[mid] = dict(kind=kind, hp=hp, mass_kg=mass, breaks=breaks, boxes=[])
        MESH[mid] = Mesh(mid, M)
    return MESH[mid]


def box(mid, x0, x1, y0, y1, z0, z1, m, collide=True):
    me = MESH[mid]
    me.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (abs(x1 - x0) / 2, abs(y1 - y0) / 2, abs(z1 - z0) / 2), m)
    if collide:
        MODS[mid]["boxes"].append([round((x0 + x1) / 2, 4), round((y0 + y1) / 2, 4), round((z0 + z1) / 2, 4),
                                   round(abs(x1 - x0), 4), round(abs(y1 - y0), 4), round(abs(z1 - z0), 4)])


def wall(mid, sx, y0, y1, z0, z1, outer="cream", inner="lining", collide=True):
    """A piece of side wall: the outer skin and the inner lining (one collision box)."""
    xo, xm, xi = sx * WO, sx * (WO - 0.025), sx * WI
    box(mid, xm, xo, y0, y1, z0, z1, outer, collide=False)
    if z1 > FLOOR + 0.01:
        box(mid, xi, xm, y0, y1, max(z0, FLOOR), z1, inner if z0 >= BELT - 0.01 or inner != "lining" else "lining", collide=False)
    if collide:
        MODS[mid]["boxes"].append([round(sx * (WO + WI) / 2, 4), round((y0 + y1) / 2, 4), round((z0 + z1) / 2, 4), round(WO - WI, 4), round(abs(y1 - y0), 4), round(z1 - z0, 4)])


MARKERS = []       # (name, location, z rotation)


def marker(name, loc, rot=0.0):
    MARKERS.append((name, tuple(loc), rot))


# ---------------------------------------------------------------- the body's cross-section (outer)
def profile_half():
    """(x, z) from the skirt up the right side, over the roof to the centre line."""
    pts = [(WO, SKIRT), (WO, 2.30), (WO - 0.012, 2.48), (WO - 0.05, CANT)]
    for i in range(1, 9):
        a = math.radians(90 * i / 8)
        pts.append((0.0 + (WO - 0.05) * max(0.0, math.cos(a)) ** 0.65 if i < 8 else 0.0, CANT + 0.40 * max(0.0, math.sin(a)) ** 0.8))
    return pts


def profile_ring():
    h = profile_half()
    right = h
    left = [(-x, z) for x, z in reversed(h[:-1])]
    bottom = [(-WO + 2 * WO * i / 6, SKIRT) for i in range(1, 6)]
    return right + left + bottom          # closed: right side up, roof, left side down, along the bottom


# ---------------------------------------------------------------- the section
def section(kind):
    MODS.clear()
    MESH.clear()
    MARKERS.clear()
    front_end = HL if kind != "front" else HL
    has_nose, has_tail = kind == "front", kind == "rear"
    y_hi = HL                                # the sides run between the end faces; noses/tails go beyond
    y_lo = -HL
    doors = DOORS[kind]

    # --- the floor (structural) and the wheel housings / podiums
    mod("floor", "floor", 5000, 420, breaks="none")
    box("floor", -WI, WI, y_lo - (NOSE - 0.12 if has_tail else 0), y_hi + (NOSE - 0.12 if has_nose else 0), 0.50, FLOOR, "floor")
    for ai, ay in enumerate(AXLES):
        for s, sx in (("L", -1), ("R", 1)):
            mid = "podium_%d%s" % (ai, s)
            mod(mid, "podium", 1500, 60, breaks="none")
            box(mid, sx * HOUSING[0], sx * WI, ay - ARCH - 0.04, ay + ARCH + 0.04, FLOOR, HOUSING[1], "shell")
            box(mid, sx * (HOUSING[0] - 0.01), sx * (HOUSING[0] + 0.02), ay - ARCH - 0.04, ay + ARCH + 0.04, HOUSING[1] - 0.04, HOUSING[1], "chrome", collide=False)

    # --- the sides: bays between the doors, windows in each bay
    for s, sx in (("L", -1), ("R", 1)):
        dys = sorted(doors[s])
        cuts = [(dy - DOOR_W / 2, dy + DOOR_W / 2) for dy in dys]
        segs = []
        cur = y_lo
        for a, b in cuts:
            segs.append((cur, a))
            cur = b
        segs.append((cur, y_hi))
        # doorways: the skirt step below, the header above, the leaves, the ramp
        for di, dy in enumerate(dys):
            did = "%s%d" % (s, di)
            a, b = dy - DOOR_W / 2, dy + DOOR_W / 2
            hid = "doorhead_%s" % did
            mod(hid, "panel", 260, 30)
            wall(hid, sx, a, b, SKIRT, FLOOR - 0.02, outer="cream", inner="cream")
            wall(hid, sx, a, b, DOOR_H, CANT, outer="teal", inner="cove")
            box(hid, sx * (WO - 0.02), sx * (WO + 0.012), a - 0.02, b + 0.02, DOOR_H - 0.03, DOOR_H, "chrome", collide=False)
            for li, (l0, l1, sy) in enumerate(((a, dy, -1), (dy, b, 1))):
                lid = "door_%s_%s" % (did, "ab"[li])
                mod(lid, "door_leaf", 220, 38)
                xo = sx * (WO - 0.005)
                box(lid, xo - sx * 0.05, xo, l0 + 0.01, l1 - 0.01, FLOOR, DOOR_H - 0.01, "teal")
                gy0, gy1 = l0 + 0.09, l1 - 0.09
                for gz0, gz1 in ((0.95, 1.55), (1.65, 2.42)):          # the leaves' windows
                    gid = "glass_%s_%s_%d" % (did, "ab"[li], int(gz0 * 10))
                    mod(gid, "glass", 60, 6, breaks="shatter")
                    box(gid, xo - sx * 0.035, xo + sx * 0.004, gy0, gy1, gz0, gz1, "glass")
                box(lid, xo + sx * 0.002, xo + sx * 0.012, (l0 + l1) / 2 + sy * 0.12 - 0.01, (l0 + l1) / 2 + sy * 0.12 + 0.01, 1.0, 2.0, "chrome", collide=False)
            marker("exit_%s" % did, (sx * (WO + 1.0), dy, 0.0), math.pi / 2 * -sx)
            marker("doorway_%s" % did, (sx * (WI - 0.35), dy, FLOOR), math.pi / 2 * sx)
            rid = "ramp_%s" % did
            mod(rid, "ramp", 400, 30, breaks="none")
            # the fold-out ramp, drawn deployed: from the sill out and down to just above the kerb
            me = MESH[rid]
            x0, x1 = sx * (WO + 0.01), sx * (WO + 0.95)
            z0, z1 = FLOOR - 0.03, 0.12
            for k, (ya, yb) in enumerate(((a + 0.08, b - 0.08),)):
                me.face([(x0, ya, z0), (x1, ya, z1), (x1, yb, z1), (x0, yb, z0)][::(1 if sx > 0 else -1)], "rubber")
                me.face([(x0, ya, z0 - 0.02), (x0, yb, z0 - 0.02), (x1, yb, z1 - 0.02), (x1, ya, z1 - 0.02)][::(1 if sx > 0 else -1)], "chrome")
            # inside: stanchions either side of the doorway
            for yy in (a - 0.06, b + 0.06):
                sid = "stanchion_%s_%d" % (did, int(yy * 100))
                mod(sid, "stanchion", 150, 4)
                MESH[sid].pipe([(sx * (WI - 0.12), yy, FLOOR), (sx * (WI - 0.12), yy, 2.45), (sx * (WI - 0.3), yy, 2.6)], 0.018, "chrome", n=10)
                MODS[sid]["boxes"].append([round(sx * (WI - 0.12), 4), round(yy, 4), round((FLOOR + 2.45) / 2, 4), 0.04, 0.04, round(2.45 - FLOOR, 4)])
        # window bays
        for si, (y0, y1) in enumerate(segs):
            length = y1 - y0
            if length < 0.05:
                continue
            bid = "side_%s_%d" % (s, si)
            mod(bid, "panel", 320, 70)
            # the skirt, with wheel arches cut where an axle is under this bay
            pieces = [(y0, y1)]
            for ay in AXLES:
                nxt = []
                for p0, p1 in pieces:
                    if p1 <= ay - ARCH or p0 >= ay + ARCH:
                        nxt.append((p0, p1))
                    else:
                        if p0 < ay - ARCH:
                            nxt.append((p0, ay - ARCH))
                        if p1 > ay + ARCH:
                            nxt.append((ay + ARCH, p1))
                        a0, a1 = max(p0, ay - ARCH), min(p1, ay + ARCH)
                        wall(bid, sx, a0, a1, 1.0, BELT, outer="cream", inner="shell")
                        # the arch's lip
                        MESH[bid].pipe([(sx * (WO + 0.01), a0, 1.0), (sx * (WO + 0.01), a1, 1.0)], 0.012, "chrome", n=6, caps=True)
                pieces = nxt
            for p0, p1 in pieces:
                wall(bid, sx, p0, p1, SKIRT, BELT, outer="cream", inner="lining")
            # Carrow's keel line in bronze, and the chrome belt
            MESH[bid].pipe([(sx * (WO + 0.006), y0, SKIRT + 0.04), (sx * (WO + 0.006), y1, SKIRT + 0.04)], 0.008, "bronze", n=6)
            MESH[bid].pipe([(sx * (WO + 0.008), y0, BELT), (sx * (WO + 0.008), y1, BELT)], 0.012, "chrome", n=6)
            # the window band
            n = max(1, int((length - 0.12) / 1.25)) if length > 0.9 else 0
            pil = 0.12
            if n == 0:
                wall(bid, sx, y0, y1, BELT, CANT, outer="teal", inner="cove")
            else:
                ww = (length - (n + 1) * pil) / n
                wall(bid, sx, y0, y1, BELT, WIN0, outer="teal", inner="lining")
                wall(bid, sx, y0, y1, WIN1, CANT, outer="teal", inner="cove")
                for k in range(n + 1):
                    py = y0 + k * (ww + pil)
                    wall(bid, sx, py, py + pil, WIN0, WIN1, outer="teal", inner="lining")
                for k in range(n):
                    wy0 = y0 + pil + k * (ww + pil)
                    gid = "glass_%s_%d_%d" % (s, si, k)
                    mod(gid, "glass", 70, 14, breaks="shatter")
                    box(gid, sx * (WO - 0.03), sx * (WO - 0.015), wy0, wy0 + ww, WIN0, WIN1, "glass")
                    # rubber gaskets
                    for zz in (WIN0, WIN1):
                        MESH[bid].pipe([(sx * (WO + 0.004), wy0, zz), (sx * (WO + 0.004), wy0 + ww, zz)], 0.01, "rubber", n=5)
            # the cove light inside, above the windows
            box(bid, sx * (WI - 0.08), sx * WI, y0, y1, 2.42, 2.50, "lamp_ceiling", collide=False)

    # --- the roof and ceiling, in bays
    ring = profile_half()
    n_roof = 6
    for ri in range(n_roof):
        y0 = y_lo + (y_hi - y_lo) * ri / n_roof
        y1 = y_lo + (y_hi - y_lo) * (ri + 1) / n_roof
        rid = "roof_%d" % ri
        mod(rid, "roof", 450, 90)
        me = MESH[rid]
        roof_pts = [p for p in ring if p[1] >= CANT - 0.001]
        full = [(-x, z) for x, z in reversed(roof_pts[1:])] + roof_pts
        full = list(reversed(full))
        rows = [[(x, y0, z) for x, z in full], [(x, y1, z) for x, z in full]]
        me.quad_strip(rows, "cream")
        MODS[rid]["boxes"].append([0.0, round((y0 + y1) / 2, 4), round(CANT + 0.2, 4), round(WO * 2, 4), round(y1 - y0, 4), 0.4])
        # the ceiling, with its light panel down the middle, and the grab rails
        box(rid, -WI, WI, y0, y1, CEIL, CEIL + 0.03, "ceiling", collide=False)
        box(rid, -0.28, 0.28, y0 + 0.06, y1 - 0.06, CEIL - 0.012, CEIL, "lamp_ceiling", collide=False)
        for rx in (-0.32, 0.72):
            me.pipe([(rx, y0, 2.45), (rx, y1, 2.45)], 0.016, "chrome", n=8, caps=False)
            for k in range(3):
                yy = y0 + (y1 - y0) * (k + 0.5) / 3
                me.pipe([(rx, yy, 2.45), (rx, yy, 2.80)], 0.008, "chrome", n=5)
    # roof fairings (Carrow's smooth covers over the roof ducts)
    fid = "fairings"
    mod(fid, "roof_fairing", 300, 80)
    for fy, fl in ((1.6, 2.6), (-2.0, 2.0)):
        rows = []
        for i in range(10):
            t = i / 9
            y = fy - fl / 2 + fl * t
            k = math.sqrt(max(0.0001, 1 - (2 * t - 1) ** 4))
            ring2 = []
            for j in range(14):
                a = math.pi * j / 13
                ring2.append((0.75 * k * math.cos(a), y, 2.98 + 0.001 + 0.22 * k * max(0.0, math.sin(a)) ** 0.7))
            rows.append(ring2)
        MESH[fid].quad_strip(rows, "cream")
        MODS[fid]["boxes"].append([0.0, fy, 3.08, 1.5, fl, 0.22])

    # --- the ends: a portal (joint side) or the nose / tail
    ends = []
    if kind == "front":
        ends = [("nose", 1), ("portal", -1)]
    elif kind == "rear":
        ends = [("portal", 1), ("tail", -1)]
    else:
        ends = [("portal", 1), ("portal", -1)]
    for what, sy in ends:
        y_face = sy * HL
        if what == "portal":
            pid = "endwall_%s" % ("F" if sy > 0 else "B")
            mod(pid, "endwall", 900, 120)
            pw, ph = PORTAL
            for x0, x1 in ((-WI, -pw), (pw, WI)):
                box(pid, x0, x1, y_face - sy * 0.06 if sy > 0 else y_face, y_face if sy > 0 else y_face + 0.06, SKIRT, CANT, "lining")
            box(pid, -pw, pw, min(y_face, y_face - sy * 0.06), max(y_face, y_face - sy * 0.06), ph, CANT + 0.2, "lining")
            # the outer face: teal band and cream, a rubber diaphragm flange round it
            me = MESH[pid]
            for x0, x1 in ((-WO, -pw - 0.05), (pw + 0.05, WO)):
                me.box(((x0 + x1) / 2, y_face + sy * 0.005, (SKIRT + BELT) / 2), (abs(x1 - x0) / 2, 0.006, (BELT - SKIRT) / 2), "cream")
                me.box(((x0 + x1) / 2, y_face + sy * 0.005, (BELT + CANT) / 2), (abs(x1 - x0) / 2, 0.006, (CANT - BELT) / 2), "teal")
            loop = []
            for i in range(25):
                a = TAU * i / 24
                loop.append((math.copysign(min(1.0, abs(math.cos(a)) ** 0.25), math.cos(a)) * (WO - 0.06), y_face + sy * 0.03,
                             1.62 + math.copysign(min(1.0, abs(math.sin(a)) ** 0.25), math.sin(a)) * 1.28))
            me.pipe(loop, 0.035, "rubber", n=8, caps=False)
            # portal frame
            me.pipe([(-pw, y_face, FLOOR), (-pw, y_face, ph), (pw, y_face, ph), (pw, y_face, FLOOR)], 0.03, "chrome", n=8)
            marker("portal_%s" % ("F" if sy > 0 else "B"), (0, y_face, FLOOR))
        else:
            cap(what, sy)

    # --- seats
    seat_n = [0]
    stand_n = [0]

    def seat(x, y, width, facing=0.0, z_base=FLOOR, sid_hint=""):
        sid = "seat_%d" % seat_n[0]
        mod("seatmod_%d" % seat_n[0], "seat", 120, 22)
        me = MESH["seatmod_%d" % seat_n[0]]
        rot = Matrix.Rotation(facing, 4, "Z")
        c = Vector((x, y, 0))

        def bx(dx0, dx1, dy0, dy1, dz0, dz1, m, coll=False):
            p0 = rot @ Vector((dx0, dy0, 0))
            p1 = rot @ Vector((dx1, dy1, 0))
            me.box((c.x + (p0.x + p1.x) / 2, c.y + (p0.y + p1.y) / 2, z_base + (dz0 + dz1) / 2),
                   (abs(p1.x - p0.x) / 2, abs(p1.y - p0.y) / 2, (dz1 - dz0) / 2), m)
            if coll:
                MODS["seatmod_%d" % seat_n[0]]["boxes"].append([round(c.x + (p0.x + p1.x) / 2, 4), round(c.y + (p0.y + p1.y) / 2, 4), round(z_base + (dz0 + dz1) / 2, 4),
                                                                round(abs(p1.x - p0.x), 4), round(abs(p1.y - p0.y), 4), round(dz1 - dz0, 4)])
        hw = width / 2
        bx(-hw + 0.04, hw - 0.04, -0.18, 0.16, 0.0, 0.36, "shell", coll=True)       # the pedestal
        bx(-hw, hw, -0.22, 0.24, 0.36, 0.45, "seat")                               # the cushion
        bx(-hw, hw, -0.30, -0.22, 0.40, 1.02, "shell", coll=True)                  # the back's shell
        bx(-hw + 0.03, hw - 0.03, -0.22, -0.20, 0.50, 0.98, "seat")                # its cushion
        p = rot @ Vector((0, -0.29, 0))
        q0 = rot @ Vector((-hw + 0.04, 0, 0))
        q1 = rot @ Vector((hw - 0.04, 0, 0))
        me.pipe([(c.x + q0.x + p.x, c.y + q0.y + p.y, z_base + 1.0), (c.x + q0.x + p.x, c.y + q0.y + p.y, z_base + 1.1),
                 (c.x + q1.x + p.x, c.y + q1.y + p.y, z_base + 1.1), (c.x + q1.x + p.x, c.y + q1.y + p.y, z_base + 1.0)], 0.014, "chrome", n=6)
        places = [0.0] if width < 0.6 else [-width / 4, width / 4]
        for off in places:
            q = rot @ Vector((off, 0.02, 0))
            marker("seat_%d" % seat_n[0] if len(places) == 1 else "seat_%d%s" % (seat_n[0], "ab"[places.index(off)]), (c.x + q.x, c.y + q.y, z_base + 0.45), facing)
        seat_n[0] += 1

    def clear(y, half, side):
        """Is there room for a seat at y on this side (no door, housing, cab or end in the way)?"""
        for dy in doors[side]:
            if abs(y - dy) < DOOR_W / 2 + half + 0.25:
                return False
        for ay in AXLES:
            if abs(y - ay) < ARCH + 0.04 + half:
                return False
        lo = y_lo + 0.35 + half
        hi = y_hi - 0.35 - half
        if kind == "front":
            hi = 3.5 - half
        return lo <= y <= hi

    for side, x, w in (("L", -WI + 0.47, 0.88), ("R", WI - 0.25, 0.46)):
        y = y_hi - 0.5
        while y > y_lo + 0.3:
            if clear(y, 0.3, side):
                seat(x, y, w)
                y -= 0.78
            else:
                y -= 0.1
    # podium seats over the housings, facing the aisle
    for ay in AXLES:
        for side, sx in (("L", -1), ("R", 1)):
            for dy in (-0.27, 0.27):
                seat(sx * (WI - 0.28), ay + dy, 0.46, facing=math.pi / 2 * sx, z_base=HOUSING[1])
    # standing places down the aisle, under the right-hand rail
    y = y_hi - 0.6
    while y > y_lo + 0.5:
        if kind == "front" and y > 3.4:
            y -= 0.8
            continue
        marker("stand_%d" % stand_n[0], (AISLE_X, y, FLOOR))
        marker("strap_%d" % stand_n[0], (0.52, y + 0.05, 1.86))
        stand_n[0] += 1
        y -= 0.8
    # the strap loops themselves (on the rails)
    sid = "straps"
    mod(sid, "fittings", 200, 8, breaks="none")
    for rx in (-0.32, 0.72):
        yy = y_lo + 0.4
        while yy < y_hi - 0.3:
            MESH[sid].pipe([(rx, yy, 2.45), (rx, yy, 2.0)], 0.006, "cream", n=4, caps=False)
            MESH[sid].lathe([(-0.012, 0.06), (0.012, 0.06)], "cream", n=10, xf=Matrix.Translation((rx, yy, 1.94)))
            yy += 0.5
    # lights inside
    marker("light_cabin_0", (0, y_hi * 0.5, CEIL - 0.1))
    marker("light_cabin_1", (0, y_lo * 0.5, CEIL - 0.1))

    # --- the cab (front): the driver's seat, the dash with gauges and a Wire slot, a half partition
    if kind == "front":
        cid = "cab"
        mod(cid, "cab", 400, 90)
        box(cid, -WI, -0.2, 3.62, 3.68, FLOOR, 1.55, "teal")                     # the partition, behind the driver
        box(cid, -WI, 0.9, 4.48, 4.75, FLOOR, 1.18, "dash")                       # the dash
        me = MESH[cid]
        for k, gx in enumerate((-0.95, -0.72, -0.49)):                           # gauges: speed, charge, motors
            me.lathe([(0, 0.075), (0.012, 0.075), (0.012, 0.0001)], "gauge", n=20,
                     xf=Matrix.Translation((gx, 4.47, 1.05)) @ Matrix.Rotation(math.pi, 4, "Z"))
            me.pipe([(gx, 4.455, 1.05), (gx + 0.04 * math.cos(0.6 + k), 4.455, 1.05 + 0.04 * math.sin(0.6 + k))], 0.004, "rubber", n=4)
            me.lathe([(0, 0.082), (0.016, 0.082)], "chrome", n=20, xf=Matrix.Translation((gx, 4.475, 1.05)) @ Matrix.Rotation(math.pi, 4, "Z"))
        box(cid, -0.30, -0.12, 4.44, 4.48, 0.96, 1.01, "rubber", collide=False)     # the Wire slot (a set slides in here)
        box(cid, -0.29, -0.13, 4.43, 4.44, 0.965, 1.005, "dash", collide=False)
        me.lathe([(-0.02, 0.19), (0.02, 0.19)], "rubber", n=24, xf=Matrix.Translation((-0.70, 4.32, 1.22)) @ Matrix.Rotation(-1.1, 4, "X"))   # the wheel
        me.pipe([(-0.70, 4.32, 1.22), (-0.70, 4.47, 0.95)], 0.025, "dash", n=8)
        seat(-0.70, 3.95, 0.52)
        # rename the last seat's marker to the driver's
        name, loc, rot = MARKERS[-1]
        MARKERS[-1] = ("seat_driver", loc, rot)
    return MODS, MESH, MARKERS


def cap(what, sy):
    """The nose (front) or tail (rear): a loft from the body's section to a raked end face, with the
    windscreen or the rear window as glass, lamps, the bumper and the destination sign."""
    nose = what == "nose"
    cid = what
    mod(cid, "endcap", 900, 180)
    gid = "glass_%s" % ("windscreen" if nose else "rearwindow")
    mod(gid, "glass", 120, 30, breaks="shatter")
    y0 = sy * HL
    ring0 = profile_ring()
    # the end face outline: a rounded rectangle, a little narrower and lower
    n = len(ring0)
    cx, cz = 0.0, 1.62

    def end_outline(a):
        hw, z0, z1, rad = WO - 0.24, SKIRT + 0.10, 2.80, 0.62
        dx, dz = math.cos(a), math.sin(a)
        best = None
        for t in [i / 400 * 3.0 for i in range(1, 401)]:
            x, z = cx + dx * t, cz + dz * t
            inside = abs(x) <= hw and z0 <= z <= z1
            if inside and z > z1 - rad and abs(x) > hw - rad:
                inside = (abs(x) - (hw - rad)) ** 2 + (z - (z1 - rad)) ** 2 <= rad * rad
            if not inside:
                return (cx + dx * (t - 0.0075), cz + dz * (t - 0.0075))
            best = (x, z)
        return best

    angs = [math.atan2(z - cz, x - cx) for x, z in ring0]
    ring1 = [end_outline(a) for a in angs]

    def rake(z):
        return NOSE - 0.14 * ((z - SKIRT) / 2.6) ** 2

    rows = []
    for i in range(7):
        t = i / 6
        e = math.sin(t * math.pi / 2)
        row = []
        for (x0, z0), (x1, z1) in zip(ring0, ring1):
            bulge = math.sin(t * math.pi) * 0.04
            x = x0 + (x1 - x0) * e ** 1.6 + math.copysign(bulge, x0)
            z = z0 + (z1 - z0) * e ** 1.6 + (bulge if z0 > 1.62 else 0.0)
            row.append((x, y0 + sy * rake(z) * (1 - math.cos(t * math.pi / 2)) ** 0.8 if i else y0, z))
        rows.append(row)
    me = MESH[cid]
    for i in range(len(rows) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            q = [rows[i][k], rows[i + 1][k], rows[i + 1][k2], rows[i][k2]]
            zc = sum(p[2] for p in q) / 4
            m = "teal" if BELT < zc < CANT and abs(sum(p[0] for p in q) / 4) > 0.3 else "cream"
            me.face(q if sy > 0 else q[::-1], m)
    # the end face, in horizontal bands; the window band's middle is glass
    face_z = [SKIRT + 0.10, 0.62, BELT, (1.25 if nose else 1.35), (2.40 if nose else 2.30), 2.56, 2.80]
    win_hw = 0.86 if nose else 0.68

    def half_w(z):
        hw, z1, rad = WO - 0.24, 2.80, 0.62
        if z > z1 - rad:
            return hw - rad + math.sqrt(max(0.0, rad * rad - (z - (z1 - rad)) ** 2))
        return hw

    def fy(z):
        return y0 + sy * rake(z)

    for bi in range(len(face_z) - 1):
        za, zb = face_z[bi], face_z[bi + 1]
        steps = 4 if za > 2.4 else 1
        for st in range(steps):
            z0 = za + (zb - za) * st / steps
            z1 = za + (zb - za) * (st + 1) / steps
            w0, w1 = half_w(z0), half_w(z1)
            band_mat = "teal" if bi in (2, 3, 4) else "cream"
            if bi == 3:                     # the window band: pillars either side, glass between
                for sxx in (-1, 1):
                    q = [(sxx * win_hw, fy(z0), z0), (sxx * w0, fy(z0), z0), (sxx * w1, fy(z1), z1), (sxx * win_hw, fy(z1), z1)]
                    me.face(q if (sy > 0) == (sxx > 0) else q[::-1], "teal")
                gq = [(-win_hw, fy(z0) - sy * 0.01, z0), (win_hw, fy(z0) - sy * 0.01, z0), (win_hw, fy(z1) - sy * 0.01, z1), (-win_hw, fy(z1) - sy * 0.01, z1)]
                MESH[gid].face(gq if sy > 0 else gq[::-1], "glass")
                MODS[gid]["boxes"].append([0.0, round(fy((z0 + z1) / 2), 4), round((z0 + z1) / 2, 4), round(win_hw * 2, 4), 0.05, round(z1 - z0, 4)])
                me.pipe([(-win_hw, fy(z0), z0), (win_hw, fy(z0), z0), (win_hw, fy(z1), z1), (-win_hw, fy(z1), z1), (-win_hw, fy(z0), z0)], 0.018, "rubber", n=6, caps=False)
            else:
                q = [(-w0, fy(z0), z0), (w0, fy(z0), z0), (w1, fy(z1), z1), (-w1, fy(z1), z1)]
                me.face(q if sy > 0 else q[::-1], band_mat)
    # the end's collision: the face, and the cab's sides
    yf = fy(1.6)
    MODS[cid]["boxes"].append([0.0, round(yf - sy * 0.04, 4), 1.6, round((WO - 0.24) * 2, 4), 0.08, 2.4])
    for sxx in (-1, 1):
        MODS[cid]["boxes"].append([round(sxx * (WO - 0.05), 4), round(y0 + sy * NOSE / 2, 4), 1.6, 0.1, round(NOSE, 4), 2.6])
    MODS[cid]["boxes"].append([0.0, round(y0 + sy * NOSE / 2, 4), round(CANT + 0.15, 4), round(WO * 2, 4), round(NOSE, 4), 0.3])
    # the ceiling inside the end
    me.box((0, y0 + sy * NOSE * 0.35, 2.58), (0.84, NOSE * 0.35, 0.012), "ceiling")
    # chrome bumper, lamps, badge, destination sign
    zb = 0.55
    me.pipe([(-WO + 0.15, fy(zb) + sy * 0.05, zb), (WO - 0.15, fy(zb) + sy * 0.05, zb)], 0.035, "chrome", n=10)
    me.pipe([(-WO + 0.15, fy(zb) + sy * 0.05, zb), (-WO + 0.08, y0 + sy * 0.3, zb)], 0.035, "chrome", n=10)
    me.pipe([(WO - 0.15, fy(zb) + sy * 0.05, zb), (WO - 0.08, y0 + sy * 0.3, zb)], 0.035, "chrome", n=10)
    lamp_mat = "lamp_head" if nose else "lamp_tail"
    lamps = [(-0.82, 0.86), (0.82, 0.86)] + ([(0.0, 0.80)] if nose else [])
    for li, (lx, lz) in enumerate(lamps):
        p = Vector((lx, fy(lz), lz))
        me.lathe([(0, 0.105), (0.02, 0.105), (0.025, 0.0001)], "chrome", n=20, xf=Matrix.Translation(p) @ Matrix.Rotation(0.0 if sy > 0 else math.pi, 4, "Z"))
        me.lathe([(0.0, 0.085), (0.03, 0.06), (0.04, 0.0001)], lamp_mat, n=20, xf=Matrix.Translation(p + Vector((0, sy * 0.012, 0))) @ Matrix.Rotation(0.0 if sy > 0 else math.pi, 4, "Z"))
        tag = ("L", "R", "C")[li]
        marker(("light_head_%s" if nose else "light_tail_%s") % tag, (lx, fy(lz) + sy * 0.06, lz), 0.0 if nose else math.pi)
    for sxx in (-1, 1):                                                       # amber corner lamps
        p = Vector((sxx * (WO - 0.2), fy(1.0), 1.0))
        me.lathe([(0.0, 0.04), (0.02, 0.03), (0.025, 0.0001)], "lamp_amber", n=12, xf=Matrix.Translation(p) @ Matrix.Rotation(0.0 if sy > 0 else math.pi, 4, "Z"))
    if not nose:
        me.box((0, fy(2.52) + sy * 0.02, 2.52), (0.25, 0.012, 0.035), "lamp_tail")   # the high brake lamp
        marker("light_brake", (0, fy(2.52) + sy * 0.08, 2.52), math.pi)
    # the Carrow badge: a bronze ring with a keel
    p = Vector((0, fy(1.15) + sy * 0.008, 1.15))
    me.lathe([(0, 0.07), (0.012, 0.07), (0.012, 0.05), (0.004, 0.0001)], "bronze", n=20, xf=Matrix.Translation(p) @ Matrix.Rotation(0.0 if sy > 0 else math.pi, 4, "Z"))
    # the destination sign above the window
    me.box((0, fy(2.53) + sy * 0.01, 2.53), (0.55, 0.012, 0.09), "rubber")
    me.box((0, fy(2.53) + sy * 0.02, 2.53), (0.52, 0.006, 0.07), "dest")
    marker("light_dest_%s" % ("F" if nose else "B"), (0, fy(2.53) + sy * 0.1, 2.53))


def build(kind):
    core.reset()
    mats()
    mods, meshes, markers = section(kind)
    root = core.empty("carrow_tram_%s" % kind, (0, 0, 0))
    for mid, me in meshes.items():
        if not me.bm.faces:
            continue
        ob = me.obj(origin=Vector((0, 0, 0)), smooth=False, parent=root)
        ob.name = mid
        ob["module"] = mid
        ob["hp"] = mods[mid]["hp"]
    for name, loc, rot in markers:
        e = core.empty(name, loc, root)
        e.rotation_euler = (0, 0, rot)
    return root, mods, markers


def build_lod(kind):
    """The section seen from afar (past TramSection.LOD_NEAR): one mesh, body and running gear
    together (the user: the chassis integrated, no separate model): the outer shell as a lofted
    profile with the teal window band and dark glass, the roof, the rounded ends with their lamps,
    and the four wheels -- a few hundred faces."""
    core.reset()
    mats()
    root = core.empty("carrow_tram_%s_lod" % kind, (0, 0, 0))
    me = Mesh("lod", M)
    y0 = -HL - (NOSE if kind == "rear" else 0.0)
    y1 = HL + (NOSE if kind == "front" else 0.0)
    prof = [(WO, SKIRT), (WO, BELT), (WO, WIN0), (WO, WIN1), (WO - 0.05, CANT), (0.9, CANT + 0.32), (0.0, CANT + 0.40)]
    full = prof + [(-x, z) for x, z in reversed(prof[:-1])]
    # the sides and roof, end to end, coloured by band
    ends_in = 0.55
    for i in range(len(full) - 1):
        (xa, za), (xb, zb) = full[i], full[i + 1]
        zm = (za + zb) / 2
        m = "glass_dark" if WIN0 <= zm <= WIN1 and abs(xa) > 1.0 else ("teal" if BELT <= zm <= CANT and abs(xa) > 1.0 else "cream")
        ya = y0 + (ends_in if kind == "rear" else 0.0)
        yb = y1 - (ends_in if kind == "front" else 0.0)
        q = [(xa, ya, za), (xa, yb, za), (xb, yb, zb), (xb, ya, zb)]
        me.face(q if xa >= 0 or xb > 0 else q, m)
    # the ends: a portal end is a flat cap; the nose / tail tapers in and carries the glass and lamps
    for end, sy in ((y1, 1), (y0, -1)):
        tip = (kind == "front" and sy > 0) or (kind == "rear" and sy < 0)
        yi = end - sy * (ends_in if tip else 0.0)
        ring_in = [(x, yi, z) for x, z in full]
        if tip:
            ring_out = [(x * 0.82, end, SKIRT + 0.1 + (z - SKIRT) * 0.93) for x, z in full]
            me.quad_strip([ring_in, ring_out], "cream")
            cap = list(reversed(ring_out)) if sy > 0 else ring_out
            me.face(cap, "cream")
            me.face([(-0.8, end + sy * 0.01, 1.3 if sy > 0 else 1.4), (0.8, end + sy * 0.01, 1.3 if sy > 0 else 1.4),
                     (0.8, end + sy * 0.01, 2.35), (-0.8, end + sy * 0.01, 2.35)][::sy], "glass_dark")
            lamp = "lamp_head" if kind == "front" else "lamp_tail"
            for lx in (-0.75, 0.75):
                me.face([(lx - 0.1, end + sy * 0.015, 0.78), (lx + 0.1, end + sy * 0.015, 0.78), (lx + 0.1, end + sy * 0.015, 0.94),
                         (lx - 0.1, end + sy * 0.015, 0.94)][::sy], lamp)
            me.face([(-0.5, end + sy * 0.015, 2.45), (0.5, end + sy * 0.015, 2.45), (0.5, end + sy * 0.015, 2.6),
                     (-0.5, end + sy * 0.015, 2.6)][::sy], "dest")
        else:
            me.face(list(reversed(ring_in)) if sy > 0 else ring_in, "rubber")
    # the bottom, and the wheels (simple 12-sided discs, from the board: radius 0.48, track 2.2)
    me.face([(-WO, y0, SKIRT), (WO, y0, SKIRT), (WO, y1, SKIRT), (-WO, y1, SKIRT)], "rubber")
    for ay in AXLES:
        for sx in (-1, 1):
            me.lathe([(-0.16, 0.0001), (-0.16, 0.48), (0.16, 0.48), (0.16, 0.0001)], "tyre", n=12,
                     xf=Matrix.Translation((sx * 1.1, ay, 0.48)) @ Matrix.Rotation(-math.pi / 2, 4, "Z"))
    ob = me.obj(origin=Vector((0, 0, 0)), smooth=False, parent=root)
    ob.name = "lod"
    return ob


def export(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_yup=True, export_extras=True)


def to_godot_box(b):
    cx, cy, cz, sx, sy, sz = b
    return [cx, cz, -cy, sx, sz, sy]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RENDER_DIR, exist_ok=True)
    spec = {"_about": "Carrow Coach Company road tram bodies (remake/blender/tram/carrow_tram.py). Boxes are in the section's Godot frame "
                      "(x right, y up, z back): [cx, cy, cz, sx, sy, sz]. Each section bolts onto godot_project/remake/vehicles/chassis/steward_tram.glb.",
            "maker": "carrow_coach_company", "board": "steward_tram", "floor_y": FLOOR, "ceiling_y": CEIL, "half_width": WO, "half_length": HL, "nose": NOSE,
            "portal": {"half_width": PORTAL[0], "head": PORTAL[1]}, "axles_z": [-a for a in AXLES], "sections": {}}
    for kind in ("front", "mid", "rear"):
        root, mods, markers = build(kind)
        export(os.path.join(OUT_DIR, "carrow_tram_%s.glb" % kind))
        doors = []
        for side in ("R", "L"):
            for di, dy in enumerate(sorted(DOORS[kind][side])):
                did = "%s%d" % (side, di)
                sx = 1 if side == "R" else -1
                doors.append({"id": did, "side": side, "curbside": side == "R", "z": -dy, "width": DOOR_W,
                              "leaves": [{"node": "door_%s_a" % did, "open": [0.07 * sx, 0.0, DOOR_W / 2 - 0.04]},
                                         {"node": "door_%s_b" % did, "open": [0.07 * sx, 0.0, -(DOOR_W / 2 - 0.04)]}],
                              "glass": ["glass_%s_%s_%d" % (did, l, z) for l in "ab" for z in (9, 16)],
                              "ramp": "ramp_%s" % did,
                              "ramp_box": {"from": [sx * (WO + 0.01), FLOOR - 0.03], "to": [sx * (WO + 0.95), 0.12], "z": -dy, "width": DOOR_W - 0.16}})
        spec["sections"][kind] = {
            "glb": "res://remake/vehicles/tram/carrow_tram_%s.glb" % kind,
            "length_front": HL + (NOSE if kind == "front" else 0.0), "length_back": HL + (NOSE if kind == "rear" else 0.0),
            "modules": {k: dict(v, boxes=[to_godot_box(b) for b in v["boxes"]]) for k, v in mods.items()},
            "doors": doors,
            "seats": sum(1 for n, _, _ in markers if n.startswith("seat_") and n != "seat_driver"),
        }
        # renders
        sc, cam = core.render_setup()
        pre = os.path.join(RENDER_DIR, "carrow_tram_%s" % kind)
        core.render_persp(pre + "_34.png", cam, (0, 0, 1.5), (9.5, 10.5, 5.0), 1400, 900, lens=40)
        core.render_persp(pre + "_34l.png", cam, (0, 0, 1.5), (-9.5, -10.5, 4.0), 1400, 900, lens=40)
        core.render_ortho(pre + "_side.png", cam, "side", (0, 0, 1.6), 11.0, 1400, 600)
        core.render_persp(pre + "_inside.png", cam, (0.2, 4.0 if kind != "front" else 4.6, 1.5), (0.2, -3.8, 1.65), 1400, 900, lens=24)
        build_lod(kind)
        export(os.path.join(OUT_DIR, "carrow_tram_%s_lod.glb" % kind))
        spec["sections"][kind]["lod_glb"] = "res://remake/vehicles/tram/carrow_tram_%s_lod.glb" % kind
        print("TRAM built", kind, len(mods), "modules", spec["sections"][kind]["seats"], "seats")
    with open(os.path.join(OUT_DIR, "carrow_tram.json"), "w") as f:
        json.dump(spec, f, indent=1)


main()
