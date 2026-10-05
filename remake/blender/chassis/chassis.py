"""
chassis.py -- the boards (vehicle platforms) from godot_project/remake/vehicles/chassis/platforms.json
(tools/vehicles/platforms.py): the Steward's board, pattern HMP-1, and the three works' boards (the Harrow
Ladder, the Carrow Keel, the Solana Lattice). Canon: tools/bible/canon_industry.py; research:
research/vehicles/skateboard_chassis.md.

  flatpak run org.blender.Blender -b --factory-startup --python <abs chassis.py> -- PLATFORMS_JSON OUT_DIR RENDER_DIR [ids...]

Every module of a board is its own object, named by its module id, carrying its data as glTF extras
(module, kind, mass_kg, hp, attach): the unit of interchange and of destruction. Wheels are named for
the game's rig (wheel_FL, wheel_FR, wheel_BL, wheel_BR, wheel_M1L ...), pivot at the hub, spin about
local X, children of their corner (or pod). Blender Z up, the front toward +Y (Godot -Z), metres,
z = 0 at the ground.

The looks (the user, 2026-10-01): the Steward's board sleek and organic with minimal use of material --
a bone-like printed lattice, everything grown where the loads go; the works' boards the same body
form made of tube frames that carry their motors, batteries and electronics, mid-21st-century
cottage industry at scale -- welds, lugs, crates, bolts and paint.
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
SPEC, OUT_DIR, RENDER_DIR = argv[0], argv[1], argv[2]
ONLY = set(argv[3:])
TAU = math.tau

# ---------------------------------------------------------------- materials
M = {}


def mats():
    M.clear()
    M.update({
        # the Steward: bone, pearl, a soft glow at the seams
        "bone": mat("bone", lin((222, 218, 206)), rough=0.32, metal=0.15),
        "pearl": mat("pearl", lin((236, 234, 228)), rough=0.22, metal=0.25),
        "cell": mat("cell", lin((150, 156, 160)), rough=0.4, metal=0.3),
        "glow": mat("glow", lin((150, 220, 230)), rough=0.3, emit=lin((120, 210, 225)), emit_strength=2.0),
        # common
        "tyre": mat("tyre", lin((32, 32, 34)), rough=0.85),
        "rim_dark": mat("rim_dark", lin((70, 72, 76)), rough=0.45, metal=0.6),
        "steel": mat("steel", lin((120, 122, 126)), rough=0.4, metal=0.8),
        "copper": mat("copper", lin((184, 110, 64)), rough=0.35, metal=0.9),
        "rubber": mat("rubber", lin((40, 40, 40)), rough=0.9),
        "pcb": mat("pcb", lin((40, 110, 60)), rough=0.5),
        # Harrow: red oxide and black
        "oxide": mat("oxide", lin((118, 44, 30)), rough=0.75),
        "black": mat("black", lin((22, 22, 24)), rough=0.6, metal=0.2),
        "galv": mat("galv", lin((150, 152, 150)), rough=0.55, metal=0.7),
        # Carrow: navy, bronze, a polished keel
        "navy": mat("navy", lin((24, 36, 66)), rough=0.35, metal=0.3),
        "bronze": mat("bronze", lin((150, 104, 52)), rough=0.3, metal=0.9),
        "polish": mat("polish", lin((190, 192, 196)), rough=0.12, metal=1.0),
        "cream": mat("cream", lin((232, 222, 196)), rough=0.4),
        # Solana: sun yellow, cream, teal lugs
        "sun": mat("sun", lin((236, 186, 40)), rough=0.35, metal=0.2),
        "teal": mat("teal", lin((30, 128, 128)), rough=0.3, metal=0.5),
        "alu": mat("alu", lin((196, 200, 204)), rough=0.3, metal=0.9),
    })


# ---------------------------------------------------------------- helpers
def X_AXIS():
    """lathe's local +Y onto +X (wheels and motors that spin about X)."""
    return Matrix.Rotation(-math.pi / 2, 4, "Z")


def obj_for(mesh, name, origin, root, data=None, smooth=True):
    ob = mesh.obj(origin=Vector(origin), smooth=smooth, parent=root)
    ob.name = name
    if data:
        for k, v in data.items():
            if isinstance(v, (int, float, str)):
                ob[k] = v
    return ob


def mod_data(m):
    return {"module": m["id"], "kind": m["kind"], "mass_kg": m["mass_kg"], "hp": m["hp"], "attach": m["attach"] or ""}


def bezier(p0, p1, p2, n=10):
    return [tuple(Vector(p0) * (1 - t) ** 2 + Vector(p1) * 2 * (1 - t) * t + Vector(p2) * t * t) for t in (i / (n - 1) for i in range(n))]


def bone_pipe(me, a, b, r0, r1, m, bulge=0.0, side=Vector((0, 0, 1)), n=12, seg=16):
    """A tapering curved strut from a to b, thicker at the ends (a grown, topology-optimised look)."""
    a, b = Vector(a), Vector(b)
    mid = (a + b) / 2 + side * bulge
    pts = bezier(a, mid, b, seg)
    radii = []
    for i in range(seg):
        t = i / (seg - 1)
        base = r0 * (1 - t) + r1 * t
        radii.append(base * (1.0 - 0.45 * math.sin(math.pi * t)) * (1.0 + 0.6 * max(0.0, 1 - 6 * min(t, 1 - t))))   # waisted like bone, flared at the roots
    me.pipe(pts, 0, m, n=n, radii=radii)


def blob(me, c, r, m, n=12):
    """A node: a squashed sphere."""
    prof = [(-r + 2 * r * i / 8, r * math.sin(math.pi * i / 8) + 1e-4) for i in range(9)]
    me.lathe(prof, m, n=n, xf=Matrix.Translation(Vector(c)) @ Matrix.Diagonal((1, 1, 0.8, 1)))


def helix(me, c, r, h, turns, wire, m, axis="z"):
    pts = []
    n = int(turns * 12)
    for i in range(n + 1):
        t = i / n
        a = TAU * turns * t
        p = Vector((r * math.cos(a), r * math.sin(a), h * (t - 0.5)))
        if axis == "y":
            p = Vector((p.x, p.z, p.y))
        pts.append(tuple(Vector(c) + p))
    me.pipe(pts, wire, m, n=6, caps=False)


def rounded_rect_loop(w, l, rad, z, n=6):
    pts = []
    for cx, cy, a0 in ((w / 2 - rad, l / 2 - rad, 0), (-w / 2 + rad, l / 2 - rad, 90), (-w / 2 + rad, -l / 2 + rad, 180), (w / 2 - rad, -l / 2 + rad, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a), z))
    return pts


def wheel(name, pos, r, w, style, parent):
    me = Mesh(name, M)
    rim_r = r * (0.62 if style != "solana" else 0.66)
    tyre = [(-w / 2, rim_r), (-w / 2, r * 0.9), (-w / 2 * 0.9, r * 0.98), (0, r), (w / 2 * 0.9, r * 0.98), (w / 2, r * 0.9), (w / 2, rim_r)]
    me.lathe(tyre, "tyre", n=32, xf=X_AXIS())
    me.lathe([(-w / 2 * 0.9, rim_r * 0.98), (w / 2 * 0.9, rim_r * 0.98)], "tyre", n=32, xf=X_AXIS())
    if style == "steward":           # a smooth aero disc, pearl, with a glowing hub ring
        me.lathe([(w * 0.42, rim_r), (w * 0.47, rim_r * 0.7), (w * 0.5, rim_r * 0.25), (w * 0.5, 0.0001)], "pearl", n=32, xf=X_AXIS())
        me.lathe([(-w * 0.42, rim_r), (-w * 0.47, rim_r * 0.7), (-w * 0.5, rim_r * 0.25), (-w * 0.5, 0.0001)], "pearl", n=32, xf=X_AXIS())
        me.lathe([(w * 0.505, rim_r * 0.3), (w * 0.505, rim_r * 0.22)], "glow", n=24, xf=X_AXIS())
    else:                            # a pressed steel wheel and a hubcap
        col = {"harrow": "black", "carrow": "bronze", "solana": "cream"}[style]
        me.lathe([(w * 0.35, rim_r), (w * 0.38, rim_r * 0.75), (w * 0.3, rim_r * 0.4), (w * 0.3, 0.0001)], col, n=24, xf=X_AXIS())
        me.lathe([(-w * 0.35, rim_r), (-w * 0.38, rim_r * 0.75), (-w * 0.3, rim_r * 0.4), (-w * 0.3, 0.0001)], col, n=24, xf=X_AXIS())
        cap = "polish" if style == "carrow" else "steel"
        me.lathe([(w * 0.3, rim_r * 0.4), (w * 0.4, rim_r * 0.3), (w * 0.43, 0.0001)], cap, n=16, xf=X_AXIS())
        for k in range(5):           # lug nuts
            a = TAU * k / 5
            me.box((w * 0.33, math.cos(a) * rim_r * 0.5, math.sin(a) * rim_r * 0.5), (0.012, 0.012, 0.012), "steel")
    ob = me.obj(origin=Vector((0, 0, 0)), smooth=True)
    ob.name = name
    ob.location = Vector(pos)
    core.attach(ob, parent)
    return ob


# ---------------------------------------------------------------- the Steward's board
def steward_span(m, b, root):
    me = Mesh(m["id"], M)
    W, L, T = m["size"]
    cx, cy, cz = m["pos"]
    zt, zb = cz + T / 2, cz - T / 2
    rx = W / 2 - 0.10                                   # the mount rail line (the Pattern)
    y0, y1 = cy - L / 2, cy + L / 2
    # the side rails: smooth, waisted between the span joints, fat at the nodes
    for sx in (-1, 1):
        pts, radii = [], []
        for i in range(9):
            t = i / 8
            pts.append((sx * (rx + 0.015 * math.sin(math.pi * t)), y0 + L * t, zt - 0.045))
            radii.append(0.045 - 0.012 * math.sin(math.pi * t))
        me.pipe(pts, 0, "bone", n=12, radii=radii)
        blob(me, (sx * rx, y1, zt - 0.045), 0.06, "bone")
        me.lathe([(0, 0.035), (0.012, 0.03), (0.016, 0.0001)], "pearl", n=12, xf=Matrix.Translation((sx * rx, y1, zt - 0.045)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))   # the Pattern boss
        # the lower chord, inboard
        me.pipe([(sx * (rx - 0.18), y0, zb + 0.03), (sx * (rx - 0.2), cy, zb + 0.025), (sx * (rx - 0.18), y1, zb + 0.03)], 0, "bone", n=10, radii=[0.03, 0.022, 0.03])
        # webs: grown struts rail -> chord and rail -> centre, crossing like trabeculae
        bone_pipe(me, (sx * rx, y1, zt - 0.05), (sx * (rx - 0.2), cy, zb + 0.03), 0.032, 0.022, "bone", bulge=0.07, side=Vector((sx, 0, 0.3)).normalized())
        bone_pipe(me, (sx * rx, y0, zt - 0.05), (sx * (rx - 0.2), cy, zb + 0.03), 0.032, 0.022, "bone", bulge=0.07, side=Vector((sx, 0, 0.3)).normalized())
        bone_pipe(me, (sx * rx, y1, zt - 0.045), (sx * 0.12, cy, zt - 0.02), 0.034, 0.024, "bone", bulge=0.06, side=Vector((0, 1, 0.15)).normalized())
        bone_pipe(me, (sx * rx, y0, zt - 0.045), (sx * 0.12, cy, zt - 0.02), 0.034, 0.024, "bone", bulge=0.06, side=Vector((0, -1, 0.15)).normalized())
        blob(me, (sx * (rx - 0.2), cy, zb + 0.03), 0.045, "bone")
    # the spine node and its cross members (arched: the deck's top face is the mounting face)
    blob(me, (0, cy, zt - 0.02), 0.085, "bone")
    for sx in (-1, 1):
        blob(me, (sx * 0.12, cy, zt - 0.02), 0.05, "bone")
    bone_pipe(me, (-0.12, cy, zt - 0.02), (0.12, cy, zt - 0.02), 0.03, 0.03, "bone", bulge=0.01)
    bone_pipe(me, (-rx, y1, zt - 0.045), (rx, y1, zt - 0.045), 0.03, 0.03, "bone", bulge=-0.025)
    # the sealed cells: a smooth pebble filling the lattice, set low
    cw, cl, ch = W - 0.42, L - 0.08, T * 0.55
    rows = []
    for i in range(9):
        t = i / 8
        y = y0 + 0.04 + cl * t
        k = 1.0 - 0.18 * (2 * t - 1) ** 6
        ring = []
        for j in range(20):
            a = TAU * j / 20
            ca, sa = math.cos(a), math.sin(a)
            ring.append((cw / 2 * k * math.copysign(abs(ca) ** 0.35, ca), y, cz - T * 0.12 + ch / 2 * k * math.copysign(abs(sa) ** 0.5, sa)))
        rows.append(ring)
    me.quad_strip(rows, "cell", closed=True)
    me.box((0, cy, cz - T * 0.12 + ch / 2 + 0.002), (cw / 2 - 0.04, 0.004, 0.002), "glow")    # the seam light
    return obj_for(me, m["id"], (cx, cy, cz), root, mod_data(m))


def steward_cap(m, b, root):
    me = Mesh(m["id"], M)
    W, L, T = m["size"]
    cx, cy, cz = m["pos"]
    sgn = 1 if m["end"] == "front" else -1
    y_j = cy - sgn * L / 2                            # the joint with the first/last span
    rows = []
    for i in range(10):
        t = i / 9
        y = y_j + sgn * L * t
        k = math.sqrt(max(1e-4, 1 - t ** 2.2))
        ring = []
        for j in range(24):
            a = TAU * j / 24
            ca, sa = math.cos(a), math.sin(a)
            ring.append((W / 2 * k * math.copysign(abs(ca) ** 0.3, ca), y, cz + T / 2 * (0.4 + 0.6 * k) * math.copysign(abs(sa) ** 0.45, sa)))
        rows.append(ring)
    if sgn < 0:
        rows = [list(reversed(r)) for r in rows]
    me.quad_strip(rows, "pearl", closed=True)
    me.box((0, y_j + sgn * L * 0.55, cz + T * 0.12), (W * 0.3, 0.004, 0.012), "glow")           # the running light
    return obj_for(me, m["id"], (cx, cy, cz), root, mod_data(m))


PATTERN_TOP = 0.50


def steward_skid(m, b, root):
    """A keel's landing skid: a runner, its toes swept up, on two sprung legs grown from the deck's rail."""
    me = Mesh(m["id"], M)
    cx, cy, cz = m["pos"]
    L = m["size"][1]
    r = 0.035
    pts = [(cx, cy + L / 2 + 0.10, cz + 0.16), (cx, cy + L / 2, cz + 0.02)] + [(cx, cy + L / 2 - L * k / 6, cz - 0.05) for k in range(1, 6)] + \
          [(cx, cy - L / 2, cz + 0.02), (cx, cy - L / 2 - 0.08, cz + 0.12)]
    me.pipe(pts, r, "bone", n=12)
    zt = PATTERN_TOP - 0.06
    for ly in m["legs"]:
        bone_pipe(me, (cx, cy + ly, cz - 0.02), (cx * 0.85, cy + ly + 0.10, zt), 0.03, 0.04, "bone", bulge=0.03, side=Vector((0, 1, 0)))
        blob(me, (cx, cy + ly, cz - 0.03), 0.05, "bone")
        me.lathe([(0, 0.045), (0.12, 0.045)], "pearl", n=12, xf=Matrix.Translation((cx * 0.92, cy + ly + 0.05, cz + 0.12)) @ Matrix.Rotation(-math.pi / 2.3, 4, "X"))
    return obj_for(me, m["id"], (cx, cy, cz), root, mod_data(m))


def steward_pod(m, b, root):
    me = Mesh(m["id"], M)
    cx, cy, cz = m["pos"]
    r = m["wheel_r"]
    sx = -1 if m["side"] == "L" else 1
    zt = 0.5
    deck_x = sx * b["mount_x_m"]
    hub = Vector((cx, cy, cz))
    inb = hub - Vector((sx * (0.24 if r < 0.35 else 0.30) / 2 + sx * 0.07, 0, 0))
    # the motor capsule (axial flux: wide and flat), inboard of the wheel
    me.lathe([(-0.09, 0.0001), (-0.085, r * 0.45), (-0.04, r * 0.62), (0.05, r * 0.62), (0.09, r * 0.45), (0.1, 0.0001)], "pearl", n=28,
             xf=Matrix.Translation(inb) @ X_AXIS())
    # the swing arms: two grown wishbones to the deck
    for dy in (-0.22, 0.22):
        bone_pipe(me, inb + Vector((0, dy * 0.3, -r * 0.2)), (deck_x - sx * 0.12, cy + dy * 1.3, zt - 0.11), 0.045, 0.034, "bone", bulge=0.06, side=Vector((0, 0, -1)))
        bone_pipe(me, inb + Vector((0, dy * 0.2, r * 0.32)), (deck_x, cy + dy, zt - 0.045), 0.04, 0.03, "bone", bulge=0.05, side=Vector((0, 0, 1)))
    blob(me, tuple(inb + Vector((0, 0, r * 0.32))), 0.05, "bone")
    blob(me, tuple(inb + Vector((0, 0, -r * 0.2))), 0.055, "bone")
    # the active strut, a smooth sleeve
    me.pipe(bezier(tuple(inb + Vector((-sx * 0.02, 0, r * 0.5))), tuple(inb + Vector((-sx * 0.18, 0, r * 0.55))), (deck_x - sx * 0.1, cy, zt - 0.02), 10), 0, "pearl", n=14,
            radii=[0.05 - 0.015 * i / 9 for i in range(10)])
    # the fender: a thin shell over the top of the tyre
    tw = 0.24 if r < 0.35 else 0.32
    rows = []
    for i in range(33):
        t = i / 32
        a = math.radians(-35 + 190 * t)
        taper = math.sin(math.pi * t) ** 0.6
        half = (tw / 2 + 0.03) * (0.35 + 0.65 * taper)
        thick = 0.006 + 0.012 * taper
        rad = r + 0.045
        ring = []
        for j in range(9):                          # a lens-shaped section: thin at the edges
            u = -1 + 2 * j / 8
            off = thick * (1 - u * u)
            ring.append((cx + sx * 0.0 + u * half, cy + (rad + off) * math.cos(a), cz + (rad + off) * math.sin(a)))
        for j in range(9):
            u = 1 - 2 * j / 8
            off = -thick * (1 - u * u)
            ring.append((cx + u * half, cy + (rad + off) * math.cos(a), cz + (rad + off) * math.sin(a)))
        rows.append(ring)
    me.quad_strip(rows, "bone", closed=True)
    # the fender's stem: grown into the strut
    bone_pipe(me, (cx - sx * (tw / 2 + 0.02), cy - r * 0.35, cz + r * 0.85), tuple(inb + Vector((0, -r * 0.2, r * 0.45))), 0.022, 0.03, "bone", bulge=0.02, side=Vector((-sx, 0, 0)))
    me.box((cx, cy + (r + 0.07) * math.cos(math.radians(55)), cz + (r + 0.07) * math.sin(math.radians(55))), (0.06, 0.004, 0.004), "glow")
    ob = obj_for(me, m["id"], (cx, cy, cz), root, mod_data(m))
    wheel(m["wheel"], (cx + sx * 0.01, cy, cz), r, 0.24 if r < 0.35 else 0.32, "steward", ob)
    return ob


def socket(m, b, root):
    me = Mesh(m["id"], M)
    cx, cy, cz = m["pos"]
    me.lathe([(0, 0.09), (0.012, 0.085), (0.02, 0.05), (0.022, 0.0001)], "pearl", n=20, xf=Matrix.Translation((cx, cy, cz - 0.02)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    me.lathe([(0.0225, 0.03), (0.0225, 0.02)], "glow", n=16, xf=Matrix.Translation((cx, cy, cz - 0.02)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    return obj_for(me, m["id"], (cx, cy, cz), root, mod_data(m))


# ---------------------------------------------------------------- shared tube-frame parts
def boxmod(m, root, colour, fins=0, ribs=0, holes=0):
    me = Mesh(m["id"], M)
    (cx, cy, cz), (w, l, h) = m["pos"], m["size"]
    me.box((cx, cy, cz), (w / 2, l / 2, h / 2), colour)
    for i in range(fins):                       # cooling fins along the top
        x = cx - w / 2 + w * (i + 0.5) / fins
        me.box((x, cy, cz + h / 2 + 0.015), (0.004, l / 2 - 0.02, 0.015), "black" if colour != "black" else "steel")
    for i in range(ribs):                       # stiffening ribs round a crate
        y = cy - l / 2 + l * (i + 0.5) / ribs
        me.box((cx, y, cz), (w / 2 + 0.006, 0.008, h / 2 + 0.006), "black")
    for i in range(holes):                      # the Pattern's mount holes
        y = cy - l / 2 + 0.15 + i * 0.75
        if y > cy + l / 2 - 0.1:
            break
        me.box((cx, y, cz + h / 2 + 0.001), (0.018, 0.018, 0.002), "black")
    return obj_for(me, m["id"], (cx, cy, cz), root, mod_data(m), smooth=False)


def controller(m, root, colour):
    me = Mesh(m["id"], M)
    (cx, cy, cz), (w, l, h) = m["pos"], m["size"]
    me.box((cx, cy, cz), (w / 2, l / 2, h / 2), colour)
    for i in range(9):
        x = cx - w / 2 + w * (i + 0.5) / 9
        me.box((x, cy, cz + h / 2 + 0.02), (0.003, l / 2 - 0.015, 0.02), "steel")
    me.box((cx - w / 2 - 0.004, cy, cz), (0.004, l / 2 * 0.6, h / 2 * 0.5), "pcb")       # the Thirty-Two's edge, through a slot
    for i in range(4):                         # cable glands
        me.lathe([(0, 0.012), (0.03, 0.012)], "rubber", n=8, xf=Matrix.Translation((cx - w / 2 + 0.05 + i * 0.06, cy + l / 2, cz - h * 0.2)) @ Matrix.Rotation(0, 4, "Z"))
    return obj_for(me, m["id"], (cx, cy, cz), root, mod_data(m), smooth=False)


def wishbones(me, hub, inner_x, y, r, sx, m_arm, m_spring, coil=True):
    for dz, spread in ((-r * 0.35, 0.18), (r * 0.25, 0.14)):
        tip = (hub.x - sx * 0.06, y, hub.z + dz)
        me.pipe([tip, (inner_x, y + spread, hub.z + dz + 0.03)], 0.016, m_arm, n=8)
        me.pipe([tip, (inner_x, y - spread, hub.z + dz + 0.03)], 0.016, m_arm, n=8)
    me.box((hub.x - sx * 0.07, y, hub.z), (0.03, 0.05, r * 0.4), m_arm)                     # the upright
    if coil:
        top = Vector((inner_x + sx * 0.05, y, 0.48))
        bot = Vector((hub.x - sx * 0.12, y, hub.z - r * 0.25))
        mid = (top + bot) / 2
        d = (top - bot)
        # a coil-over standing along the strut line
        n, turns, rr = 0, 6, 0.045
        pts = []
        for i in range(72):
            t = i / 71
            a = TAU * turns * t
            ax = d.normalized()
            u = ax.orthogonal().normalized()
            v = ax.cross(u)
            pts.append(tuple(bot + d * (0.1 + 0.8 * t) + (u * math.cos(a) + v * math.sin(a)) * rr))
        me.pipe(pts, 0.008, m_spring, n=6, caps=False)
        me.pipe([tuple(bot), tuple(top)], 0.02, "black", n=8)


# ---------------------------------------------------------------- Harrow
def harrow_module(m, b, root):
    k = m["kind"]
    if k == "harrow_rail":
        return boxmod(m, root, "oxide")
    if k in ("harrow_cross", "harrow_outrigger"):
        return boxmod(m, root, "oxide")
    if k == "mount_rail":
        return boxmod(m, root, "black", holes=12)
    if k == "harrow_crate":
        ob = boxmod(m, root, "galv", ribs=4)
        return ob
    if k == "controller":
        return controller(m, root, "black")
    me = Mesh(m["id"], M)
    (cx, cy, cz), (w, l, h) = m["pos"], m["size"]
    if k == "harrow_motor":                        # a fat induction motor lying fore-and-aft, finned
        me.lathe([(-l / 2, 0.0001), (-l / 2, h * 0.38), (-l / 2 + 0.03, h / 2), (l / 2 - 0.03, h / 2), (l / 2, h * 0.38), (l / 2, 0.0001)], "oxide", n=24,
                 xf=Matrix.Translation((cx, cy, cz)))
        for i in range(10):
            me.lathe([(0, h / 2 + 0.018), (0.006, h / 2 + 0.018)], "black", n=24, xf=Matrix.Translation((cx, cy - l / 2 + 0.06 + i * (l - 0.12) / 9, cz)))
        me.box((cx, cy + l / 2 - 0.05, cz + h / 2 + 0.03), (0.07, 0.04, 0.03), "black")     # terminal box
        me.pipe([(cx, cy - l / 2, cz), (cx, cy - l / 2 - 0.18, cz - 0.01)], 0.03, "steel")   # the prop shaft stub
    elif k == "harrow_diff":                       # the pumpkin
        me.lathe([(-0.12, 0.0001), (-0.11, 0.09), (-0.04, 0.15), (0.06, 0.14), (0.12, 0.06), (0.13, 0.0001)], "black", n=24,
                 xf=Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(math.pi, 4, "Z"))
        for sx in (-1, 1):                         # half-shafts out to the hubs
            me.pipe([(cx + sx * 0.1, cy, cz), (sx * (b["track_m"] / 2 - 0.16), b["axles"][1]["y"], cz)], 0.022, "steel")
    elif k == "harrow_dedion":
        me.pipe([(-w / 2, cy, cz - 0.02), (-w * 0.2, cy - 0.06, cz - 0.05), (w * 0.2, cy - 0.06, cz - 0.05), (w / 2, cy, cz - 0.02)], 0.04, "oxide", n=12)
    elif k == "harrow_leaf":                       # semi-elliptic, seven leaves
        for i in range(7):
            ln = l * (1 - i * 0.11)
            pts = [(cx, cy - ln / 2 + ln * t, cz - 0.02 * i - 0.06 * (1 - (2 * t - 1) ** 2) + 0.06) for t in (j / 10 for j in range(11))]
            me.pipe(pts, 0.006, "black", n=4)
        me.box((cx, cy, cz - 0.02), (0.04, 0.05, 0.04), "steel")                      # the U-bolt pad
    elif k == "harrow_front_corner":
        sx = 1 if cx > 0 else -1
        hub = Vector((sx * b["track_m"] / 2, cy, b["wheel_r"]))
        wishbones(me, hub, sx * 0.50, cy, b["wheel_r"], sx, "oxide", "black")
        me.lathe([(-0.05, 0.0001), (-0.05, 0.15), (0.03, 0.16), (0.03, 0.0001)], "steel", n=20, xf=Matrix.Translation(hub - Vector((sx * 0.08, 0, 0))) @ X_AXIS())   # drum
    elif k == "harrow_tongue":                     # an A-frame drawbar to a ball coupler, a jockey wheel
        yt = cy + l / 2
        for sx in (-1, 1):
            me.pipe([(sx * w / 2, cy - l / 2, cz), (0, yt - 0.12, cz)], 0.04, "oxide", n=8)
        me.box((0, yt - 0.05, cz), (0.06, 0.10, 0.05), "black")
        me.lathe([(0.0, 0.0001), (0.0, 0.025), (0.04, 0.025), (0.045, 0.0001)], "steel", n=12, xf=Matrix.Translation((0, yt, cz - 0.02)))
        me.pipe([(0.12, yt - 0.35, cz), (0.12, yt - 0.35, 0.12)], 0.025, "steel")
        me.lathe([(-0.03, 0.08), (0.03, 0.08)], "black", n=14, xf=Matrix.Translation((0.12, yt - 0.35, 0.08)) @ X_AXIS())
    elif k == "harrow_kingpin":                    # the upper coupler plate and its pin
        me.box((cx, cy, cz), (w / 2, l / 2, h / 2), "oxide")
        me.lathe([(0.0, 0.0001), (0.0, 0.05), (0.08, 0.05), (0.09, 0.0001)], "steel", n=12, xf=Matrix.Translation((cx, cy + l / 2 - 0.4, cz - 0.10)))
    elif k == "harrow_legs":                       # landing gear, wound up
        for sx in (-1, 1):
            me.box((sx * w / 2, cy, cz + 0.1), (0.06, 0.06, h / 2), "black")
            me.box((sx * w / 2, cy, cz - h / 2 + 0.12), (0.12, 0.12, 0.02), "black")
        me.pipe([(-w / 2, cy, cz + 0.2), (w / 2, cy, cz + 0.2)], 0.02, "steel")
    elif k == "harrow_hub":
        sx = 1 if cx > 0 else -1
        hub = Vector((sx * b["track_m"] / 2, cy, b["wheel_r"]))
        me.lathe([(-0.05, 0.0001), (-0.05, 0.15), (0.03, 0.16), (0.03, 0.0001)], "steel", n=20, xf=Matrix.Translation(hub - Vector((sx * 0.08, 0, 0))) @ X_AXIS())
    return obj_for(me, m["id"], (cx, cy, cz), root, mod_data(m))


# ---------------------------------------------------------------- Carrow
def carrow_module(m, b, root):
    k = m["kind"]
    if k == "controller":
        return controller(m, root, "navy")
    me = Mesh(m["id"], M)
    (cx, cy, cz), (w, l, h) = m["pos"], m["size"]
    if k == "carrow_keel":
        R = w / 2
        prof = [(-l / 2, R * 0.75), (-l / 2 + 0.12, R), (l / 2 - 0.3, R), (l / 2 - 0.05, R * 0.6), (l / 2, 0.0001)]
        me.lathe(prof, "polish", n=32, xf=Matrix.Translation((cx, cy, cz)))
        for i in range(7):                          # bronze bands at the cartridge joints
            y = -l / 2 + 0.25 + i * (l - 0.6) / 6
            me.lathe([(y - 0.02, R + 0.008), (y + 0.02, R + 0.008)], "bronze", n=32, xf=Matrix.Translation((cx, cy, cz)))
        for i in range(12):                         # rivet rows along the seam
            me.box((cx, -l / 2 + 0.2 + i * (l - 0.5) / 11, cz + R + 0.004), (0.01, 0.01, 0.004), "bronze")
    elif k == "carrow_hatch":
        me.lathe([(-0.03, 0.0001), (-0.03, 0.18), (0.02, 0.18), (0.03, 0.15), (0.03, 0.0001)], "bronze", n=28, xf=Matrix.Translation((cx, cy, cz)))
        me.pipe([(cx - 0.08, cy - 0.04, cz), (cx - 0.08, cy - 0.09, cz), (cx + 0.08, cy - 0.09, cz), (cx + 0.08, cy - 0.04, cz)], 0.012, "polish")
        for i in range(8):
            a = TAU * i / 8
            me.box((cx + 0.15 * math.cos(a), cy - 0.035, cz + 0.15 * math.sin(a)), (0.012, 0.01, 0.012), "polish")
    elif k == "carrow_gunwale":
        loop = rounded_rect_loop(w, l, 0.35, cz)
        me.pipe(loop + [loop[0]], 0.03, "navy", n=12, caps=False)
        for i in range(12):                         # the Pattern holes on its top
            y = -l / 2 + 0.3 + i * 0.75
            if y > l / 2 - 0.3:
                break
            for sx in (-1, 1):
                me.box((sx * w / 2, y, cz + 0.031), (0.016, 0.016, 0.002), "bronze")
    elif k == "carrow_rib":
        sx = 1 if cx > 0 else -1
        a = (sx * 0.16, cy, 0.38)
        c = (sx * b["mount_x_m"], cy, 0.47)
        me.pipe(bezier(a, (sx * 0.45, cy, 0.32), c, 10), 0.022, "navy", n=10)
        me.lathe([(-0.02, 0.035), (0.02, 0.035)], "bronze", n=12, xf=Matrix.Translation(a) @ X_AXIS())
    elif k == "carrow_bulkhead":
        me.pipe([(-w / 2, cy, 0.47), (-w / 4, cy, cz - 0.04), (w / 4, cy, cz - 0.04), (w / 2, cy, 0.47)], 0.024, "navy", n=10)
        sy = 1 if cy > 0 else -1
        for sx in (-1, 1):                         # tie rods back to the keel's end
            me.pipe([(sx * w / 4, cy, cz - 0.04), (sx * 0.1, cy - sy * 0.35, 0.38)], 0.016, "navy", n=8)
            me.lathe([(-0.025, 0.034), (0.025, 0.034)], "bronze", n=12, xf=Matrix.Translation((sx * w / 4, cy, cz - 0.04)) @ X_AXIS())
    elif k == "carrow_motor":
        me.lathe([(-w / 2, 0.0001), (-w / 2, h * 0.3), (-w / 2 + 0.03, h / 2), (w / 2 - 0.03, h / 2), (w / 2, h * 0.3), (w / 2, 0.0001)], "navy", n=28,
                 xf=Matrix.Translation((cx, cy, cz)) @ X_AXIS())
        for sx in (-1, 1):
            me.lathe([(0, h / 2 + 0.005), (0.035, h / 2 + 0.005), (0.035, 0.0001)], "bronze", n=28, xf=Matrix.Translation((cx + sx * (w / 2 - 0.035), cy, cz)) @ X_AXIS() @ Matrix.Rotation(math.pi if sx < 0 else 0, 4, "Z"))
            hub_y = b["axles"][0]["y"] if m["id"].endswith("F") else b["axles"][1]["y"]
            hx = sx * (b["track_m"] / 2 - 0.12)
            me.pipe([(cx + sx * w / 2, cy, cz), (hx, hub_y, b["wheel_r"])], 0.02, "steel", n=8)                       # half-shafts
            for t in (0.12, 0.88):                                                                                   # CV boots
                p = Vector((cx + sx * w / 2, cy, cz)).lerp(Vector((hx, hub_y, b["wheel_r"])), t)
                me.lathe([(-0.04, 0.025), (-0.02, 0.04), (0.0, 0.032), (0.02, 0.04), (0.04, 0.025)], "rubber", n=12, xf=Matrix.Translation(p) @ X_AXIS())
    elif k == "carrow_corner":
        sx = 1 if cx > 0 else -1
        hub = Vector((sx * b["track_m"] / 2, cy, b["wheel_r"]))
        wishbones(me, hub, sx * 0.40, cy, b["wheel_r"], sx, "navy", "bronze")
        me.lathe([(-0.02, 0.0001), (-0.02, 0.15), (0.0, 0.15), (0.0, 0.0001)], "steel", n=24, xf=Matrix.Translation(hub - Vector((sx * 0.1, 0, 0))) @ X_AXIS())   # disc
    return obj_for(me, m["id"], (cx, cy, cz), root, mod_data(m))


# ---------------------------------------------------------------- Solana
def solana_module(m, b, root):
    k = m["kind"]
    if k == "mount_rail":
        return boxmod(m, root, "cream", holes=12)
    if k == "controller":
        return controller(m, root, "teal")
    me = Mesh(m["id"], M)
    (cx, cy, cz), (w, l, h) = m["pos"], m["size"]
    if k == "solana_truss":
        zt, zb = cz + h / 2 - 0.02, cz - h / 2 + 0.02
        xt, xb = cx, cx * 0.86
        n = m["panels"]
        ys = [-l / 2 + l * i / n for i in range(n + 1)]
        me.pipe([(xt, ys[0], zt), (xt, ys[-1], zt)], 0.016, "sun", n=10)                        # the top chord
        me.pipe([(xb, ys[0] + l / n / 2, zb), (xb, ys[-1] - l / n / 2, zb)], 0.016, "sun", n=10)  # the bottom chord
        for i in range(n):                         # Warren diagonals, zig-zag
            yb_ = ys[i] + l / n / 2
            me.pipe([(xt, ys[i], zt), (xb, yb_, zb)], 0.0125, "sun", n=8)
            me.pipe([(xb, yb_, zb), (xt, ys[i + 1], zt)], 0.0125, "sun", n=8)
            me.lathe([(-0.035, 0.022), (-0.02, 0.027), (0.02, 0.027), (0.035, 0.022)], "teal", n=12, xf=Matrix.Translation((xb, yb_, zb)))   # lugs
        for y in ys:
            me.lathe([(-0.035, 0.022), (-0.02, 0.027), (0.02, 0.027), (0.035, 0.022)], "teal", n=12, xf=Matrix.Translation((xt, y, zt)))
    elif k == "solana_cross":
        zt, zb = cz + h / 2 - 0.02, cz - h / 2 + 0.02
        me.pipe([(-w / 2, cy, zt), (w / 2, cy, zt)], 0.011, "sun", n=8)
        if m.get("end"):                           # past the bottom chords' ends: the top tube only
            return obj_for(me, m["id"], (cx, cy, cz), root, mod_data(m))
        me.pipe([(-w / 2 * 0.86, cy, zb), (w / 2 * 0.86, cy, zb)], 0.011, "sun", n=8)
        me.pipe([(-w / 2, cy, zt), (0, cy, zb), (w / 2, cy, zt)], 0.009, "sun", n=6)
        me.lathe([(-0.03, 0.02), (0.03, 0.02)], "teal", n=10, xf=Matrix.Translation((0, cy, zb)) @ X_AXIS())
    elif k == "solana_cassette":
        sx = 1 if cx > 0 else -1
        me.box((cx, cy, cz), (w / 2, l / 2, h / 2), "alu")
        for i in range(5):
            me.box((cx, cy - l / 2 + l * (i + 0.5) / 5, cz + h / 2 + 0.002), (w / 2 - 0.03, 0.006, 0.003), "steel")          # ribs
        face = cx + sx * w / 2
        me.box((face + sx * 0.004, cy, cz), (0.004, l / 2 - 0.02, h / 2 - 0.02), "sun")                                      # the end plate
        me.pipe([(face, cy - 0.12, cz), (face + sx * 0.05, cy - 0.1, cz), (face + sx * 0.05, cy + 0.1, cz), (face, cy + 0.12, cz)], 0.011, "teal", n=8)   # the handle
        me.box((face + sx * 0.01, cy, cz + h / 2 - 0.03), (0.003, 0.08, 0.012), "glow")                                          # the charge window
    elif k == "solana_front_corner":
        sx = 1 if cx > 0 else -1
        hub = Vector((sx * b["track_m"] / 2, cy, b["wheel_r"]))
        wishbones(me, hub, sx * 0.50, cy, b["wheel_r"], sx, "sun", "teal")
        me.lathe([(-0.015, 0.0001), (-0.015, 0.13), (0.0, 0.13), (0.0, 0.0001)], "steel", n=20, xf=Matrix.Translation(hub - Vector((sx * 0.09, 0, 0))) @ X_AXIS())
    elif k == "solana_rear_corner":
        sx = 1 if cx > 0 else -1
        hub = Vector((sx * b["track_m"] / 2 - sx * 0.12, b["axles"][1]["y"], b["wheel_r"]))
        pivot = Vector((sx * 0.6, b["axles"][1]["y"] + 0.6, 0.36))
        me.pipe([tuple(pivot), tuple(hub)], 0.022, "sun", n=10)
        me.pipe([tuple(pivot + Vector((0, 0, -0.08))), tuple(hub)], 0.016, "sun", n=8)
        me.lathe([(-0.03, 0.03), (0.03, 0.03)], "teal", n=12, xf=Matrix.Translation(pivot) @ X_AXIS())
        helix(me, tuple(hub + Vector((-sx * 0.02, 0.1, 0.16))), 0.04, 0.2, 5, 0.007, "teal")
    ob = obj_for(me, m["id"], (cx, cy, cz), root, mod_data(m))
    return ob


def hub_motor(m, b, parent):
    """A Solana rear wheel: the wheel round a fat finned hub motor."""
    ob = wheel(m["id"], m["pos"], m["wheel_r"], 0.2, "solana", parent)
    me = Mesh(m["id"] + "_motor", M)
    me.lathe([(-0.07, 0.0001), (-0.07, 0.14), (-0.05, 0.16), (0.05, 0.16), (0.07, 0.14), (0.07, 0.0001)], "teal", n=28, xf=X_AXIS())
    for i in range(12):
        a = TAU * i / 12
        me.box((0, 0.165 * math.cos(a), 0.165 * math.sin(a)), (0.05, 0.006, 0.006), "black")
    mo = me.obj(origin=Vector((0, 0, 0)), smooth=True)
    mo.location = Vector(m["pos"])
    core.attach(mo, ob)
    for k, v in mod_data(m).items():
        ob[k] = v
    return ob


# ---------------------------------------------------------------- the build
def build(b):
    core.reset()
    mats()
    root = core.empty(b["id"], (0, 0, 0))
    root["board"] = b["board"]
    root["maker"] = b["maker"]
    root["mass_kg"] = b["mass_kg"]
    fam = b["family"]
    objs = {}
    corners = {}
    for m in b["modules"]:
        k = m["kind"]
        if k in ("wheel", "wheel_hub_motor"):
            continue
        if fam == "steward":
            fn = {"steward_span": steward_span, "steward_cap": steward_cap, "steward_pod": steward_pod, "pattern_socket": socket,
                  "steward_skid": steward_skid}[k]
            objs[m["id"]] = fn(m, b, root)
        elif fam == "harrow":
            objs[m["id"]] = harrow_module(m, b, root)
        elif fam == "carrow":
            objs[m["id"]] = carrow_module(m, b, root)
        else:
            objs[m["id"]] = solana_module(m, b, root)
        if m["id"].startswith("corner_"):
            corners[m["id"][7:]] = objs[m["id"]]
    for m in b["modules"]:
        if m["kind"] == "wheel":
            wob = wheel(m["id"], m["pos"], m["wheel_r"], 0.2, fam, corners.get(m["id"][6:], root))
            for k, v in mod_data(m).items():
                wob[k] = v
        elif m["kind"] == "wheel_hub_motor":
            hub_motor(m, b, corners.get(m["id"][6:], root))
    # the Pattern's mount points as empties (the body's contract)
    zt = 0.5
    x = b["mount_x_m"]
    n = int((b["length_m"] - 0.4) / 0.75) + 1
    y0 = (n - 1) * 0.75 / 2
    for i in range(n):
        for s, sx in (("L", -1), ("R", 1)):
            core.empty("mount_%d%s" % (i, s), (sx * x, y0 - i * 0.75, zt), root)
    return root


def export(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_yup=True, export_extras=True)


def render(b, prefix):
    sc, cam = core.render_setup()
    L = b["length_m"]
    for o in bpy.data.objects:
        if o.type == "LIGHT":
            o.data.energy *= 1.1
    core.render_persp(prefix + "_34.png", cam, (0, 0, 0.35), (L * 0.95, L * 1.05, L * 0.62), 1400, 900, lens=50)
    core.render_persp(prefix + "_34r.png", cam, (0, 0, 0.3), (-L * 0.9, -L * 0.95, L * 0.5), 1400, 900, lens=50)
    core.render_ortho(prefix + "_side.png", cam, "side", (0, 0, 0.5), L * 1.12, 1400, 500)
    core.render_ortho(prefix + "_top.png", cam, "top", (0, 0, 0), L * 1.12, 1400, 700)


def main():
    spec = json.load(open(SPEC))
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RENDER_DIR, exist_ok=True)
    for b in spec["boards"]:
        if ONLY and b["id"] not in ONLY:
            continue
        build(b)
        export(os.path.join(OUT_DIR, b["id"] + ".glb"))
        render(b, os.path.join(RENDER_DIR, b["id"]))
        print("CHASSIS built", b["id"], len(bpy.data.objects), "objects")


main()
