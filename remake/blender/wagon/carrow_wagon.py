"""
carrow_wagon.py -- the Carrow station wagon, built to the SW180 class standard (remake/blender/kit/sw180.py) as
library components the game assembles on the tube frame (research/vehicles/MODULAR_VEHICLES.md;
research/vehicles/wagon/WAGON.md). Styled after the catalogue's Grok references (reference/grok/station_wagon/:
a cream 1970s estate with woodgrain panels in chrome frames, a chrome belt, roof rails) made futurist: a short
wedge bonnet over a frunk, flush glass, round projector eyes in a dark nose band, pixel tail bars.

  flatpak run org.blender.Blender -b --factory-startup --python <abs carrow_wagon.py> -- OUT_DIR RENDER_DIR

Writes the SW180 standard, the components (godot_project/remake/vehicles/components/SW180/carrow.*), the blueprint
OUT_DIR/carrow_wagon.blueprint.json, a preview OUT_DIR/carrow_wagon_preview.glb, and renders.

THE LOFT GRID. Both shells are the class's lofts: stations along the car x a fixed loop of points round it. Every
panel, opening and reveal is a rectangle of the grid's cells, so neighbours share their vertices exactly: sealed
by construction (cover() asserts every cell is used exactly once). Closers (doors, hatch, lid) are drawn 3 mm in
from their apertures on the outside (the shut line) and exact on the inside (the seal).
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import core  # noqa: E402
from kit.core import Mesh, lin, mat  # noqa: E402
from kit import standards  # noqa: E402
from kit import components  # noqa: E402
from kit import sw180 as W  # noqa: E402

STD = standards.WAGON
STYLE = "carrow"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_DIR, RENDER_DIR = argv[0], argv[1]
TAU = math.tau
GAP = 0.003                     # the shut line round a closer (outside)

Y = W.STATIONS                  # descending
YI = W.INT_STATIONS
EXT = [W.ext_loop(y) for y in Y]
INT = {y: W.int_loop(y) for y in YI}
NS_E = len(EXT[0]) - 1          # exterior cells across (open loop): 24
NS_I = W.NI                     # interior cells across (closed loop): 30

# ---------------------------------------------------------------- materials (the style's palette)
M = {}
PALETTE = {}
MAT_SPECS = [
    # name, sRGB, roughness, metallic, emission sRGB or None, emission strength, alpha
    ("cream", (234, 226, 204), 0.32, 0.05, None, 0, 1), ("wood", (128, 74, 40), 0.45, 0.0, None, 0, 1),
    ("chrome", (210, 212, 216), 0.1, 1.0, None, 0, 1), ("black", (30, 31, 34), 0.5, 0.1, None, 0, 1),
    ("rubber", (24, 24, 26), 0.85, 0.0, None, 0, 1), ("glass", (170, 196, 204), 0.05, 0.0, None, 0, 0.25),
    ("glass_dark", (40, 46, 52), 0.08, 0.4, None, 0, 1), ("lining", (214, 200, 172), 0.7, 0.0, None, 0, 1),
    ("headliner", (236, 230, 214), 0.8, 0.0, None, 0, 1), ("carpet", (96, 64, 44), 0.95, 0.0, None, 0, 1),
    ("seat", (176, 92, 44), 0.85, 0.0, None, 0, 1), ("dash", (70, 50, 38), 0.6, 0.0, None, 0, 1),
    ("gauge", (236, 228, 204), 0.4, 0.0, (255, 214, 150), 0.3, 1), ("tub", (58, 58, 60), 0.8, 0.0, None, 0, 1),
    ("lamp_head", (255, 250, 236), 0.3, 0.0, (255, 248, 230), 3.0, 1), ("lamp_drl", (255, 250, 240), 0.3, 0.0, (255, 250, 240), 1.2, 1),
    ("lamp_tail", (190, 18, 14), 0.4, 0.0, (255, 30, 20), 1.6, 1), ("lamp_brake", (190, 18, 14), 0.4, 0.0, (255, 30, 20), 0.0, 1),
    ("lamp_amber", (236, 140, 24), 0.4, 0.0, (255, 150, 30), 0.0, 1), ("lamp_reverse", (236, 236, 236), 0.4, 0.0, (255, 255, 255), 0.0, 1),
]


def mats():
    M.clear()
    PALETTE.clear()
    for name, rgb, rough, metal, emit, es, alpha in MAT_SPECS:
        if emit:
            M[name] = mat(name, lin(rgb), rough=rough, metal=metal, emit=lin(emit), emit_strength=max(es, 0.001))
        else:
            M[name] = mat(name, lin(rgb), rough=rough, metal=metal)
        PALETTE[name] = {"albedo": [round(c / 255.0, 4) for c in rgb], "rough": rough, "metal": metal,
                         "emit": [round(c / 255.0, 4) for c in emit] if emit else None, "emit_strength": es, "alpha": alpha}
    g = M["glass"]
    g.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.25
    g.surface_render_method = "BLENDED"
    for m in M.values():
        m.use_backface_culling = False


# ---------------------------------------------------------------- modules
MODS = {}          # id -> {role, slot, side, hp, mass_kg, breaks, boxes}
MESH = {}
MARKERS = []


def mod(mid, role, slot, side, hp=300, mass=8.0, breaks="detach"):
    if mid not in MODS:
        MODS[mid] = dict(role=role, slot=slot, side=side, hp=hp, mass_kg=mass, breaks=breaks, boxes=[])
        MESH[mid] = Mesh(mid, M)
    return MESH[mid]


def marker(name, loc, rot=0.0):
    MARKERS.append((name, tuple(round(c, 4) for c in loc), rot))


# ---------------------------------------------------------------- the loft
def iy(y):
    for i, v in enumerate(Y):
        if abs(v - y) < 1e-6:
            return i
    raise KeyError(y)


def ext_pt(i, s):
    x, z = EXT[i][s]
    return (x, Y[i], z)


def int_pt(y, s):
    x, z = INT[y][s % NS_I]
    return (x, y, z)


def loop_at(shell, y):
    """The loop at any y (linear between stations: the loft's own surface)."""
    ys = Y if shell == "ext" else YI
    for k in range(len(ys) - 1):
        if ys[k + 1] - 1e-9 <= y <= ys[k] + 1e-9:
            a = EXT[iy(ys[k])] if shell == "ext" else INT[ys[k]]
            b = EXT[iy(ys[k + 1])] if shell == "ext" else INT[ys[k + 1]]
            t = 0.0 if ys[k] == ys[k + 1] else (ys[k] - y) / (ys[k] - ys[k + 1])
            return [(xa + (xb - xa) * t, za + (zb - za) * t) for (xa, za), (xb, zb) in zip(a, b)]
    raise ValueError(y)


def sample(shell, y, s):
    """A point on a shell at y and loop parameter s (float)."""
    lp = loop_at(shell, y)
    n = len(lp)
    k = int(math.floor(s))
    f = s - k
    if shell == "ext" and k >= n - 1:
        k, f = n - 2, 1.0
    (xa, za), (xb, zb) = lp[k % n], lp[(k + 1) % n]
    return (xa + (xb - xa) * f, y, za + (zb - za) * f)


def rows_between(ys, y0, y1):
    return [y for y in ys if y1 - 1e-9 <= y <= y0 + 1e-9]


USED = {"ext": {}, "int": {}}          # (station y, s) cell -> module id


def cells(me, mid, shell, y0, y1, s0, s1, matf, holes=(), outward=True):
    """The cells of a shell between stations y0 > y1 and loop indices s0 < s1 (interior: may wrap), minus holes
    [(y0, y1, s0, s1)]; matf(s, y, z) -> material."""
    ys = Y if shell == "ext" else YI
    rs = rows_between(ys, y0, y1)
    n = NS_E if shell == "ext" else NS_I
    for a, b in zip(rs, rs[1:]):
        for s in range(s0, s1):
            sm = s % n
            if any(h[1] - 1e-9 <= b and a <= h[0] + 1e-9 and h[2] <= s and s + 1 <= h[3] for h in holes):
                continue
            key = (round(a, 4), sm)
            assert key not in USED[shell], ("cell used twice", shell, key, USED[shell][key], mid)
            USED[shell][key] = mid
            if shell == "ext":
                p = [(ext_pt(iy(a), sm)), ext_pt(iy(b), sm), ext_pt(iy(b), sm + 1), ext_pt(iy(a), sm + 1)]
            else:
                p = [int_pt(a, sm), int_pt(b, sm), int_pt(b, sm + 1), int_pt(a, sm + 1)]
            zc = sum(q[2] for q in p) / 4
            m = matf(s, (a + b) / 2, zc)
            me.face(list(reversed(p)) if (shell == "ext") == outward else p, m)


def cover_check():
    """Every cell of both shells belongs to exactly one component (the rest are the openings)."""
    want_holes = {"ext": [], "int": []}
    for shell, ys, n in (("ext", Y, NS_E), ("int", YI, NS_I)):
        miss = []
        for a in ys[:-1]:
            for s in range(n):
                if (round(a, 4), s) not in USED[shell]:
                    miss.append((round(a, 3), s))
        want_holes[shell] = miss
    return want_holes


def rect_ring(shell, y0, y1, s0, s1):
    """A rectangle's boundary on a shell, as a closed loop with no repeats: the front row s0 -> s1-1, the s1 column
    front to back, the back row s1-1 -> s0+1, the s0 column back to front (without its front corner)."""
    ys = Y if shell == "ext" else YI
    rs = rows_between(ys, y0, y1)
    out = [sample(shell, rs[0], s) for s in range(s0, s1)]
    out += [sample(shell, y, s1) for y in rs]
    out += [sample(shell, rs[-1], s) for s in range(s1 - 1, s0, -1)]
    out += [sample(shell, y, s0) for y in reversed(rs[1:])]
    return out


def patch(me, shell, y0, y1, s0, s1, matf, inset=0.0, outward=True, edges=(1, 1, 1, 1)):
    """A grid patch (not counted in the cover: closers), optionally pulled in by inset along the surface at the
    edges flagged (front, back, s0, s1)."""
    ys = Y if shell == "ext" else YI
    rs = rows_between(ys, y0, y1)
    if inset:
        rs = [y0 - inset * edges[0]] + rs[1:-1] + [y1 + inset * edges[1]]
    cols = []
    for s in range(s0, s1 + 1):
        cols.append(s)
    grid = []
    for y in rs:
        row = []
        for s in cols:
            sf = float(s)
            if inset and s == s0 and edges[2]:
                a, b = sample(shell, y, s), sample(shell, y, s + 1)
                sf = s + inset / max(1e-6, math.dist(a, b))
            if inset and s == s1 and edges[3]:
                a, b = sample(shell, y, s), sample(shell, y, s - 1)
                sf = s - inset / max(1e-6, math.dist(a, b))
            row.append(sample(shell, y, sf))
        grid.append(row)
    for r in range(len(grid) - 1):
        for c in range(len(cols) - 1):
            p = [grid[r][c], grid[r + 1][c], grid[r + 1][c + 1], grid[r][c + 1]]
            zc = sum(q[2] for q in p) / 4
            m = matf(cols[c], (rs[r] + rs[r + 1]) / 2, zc)
            me.face(list(reversed(p)) if (shell == "ext") == outward else p, m)
    return grid


def strip(me, a, b, m, flip=False):
    """Quads between two loops of equal length (closed)."""
    n = len(a)
    assert n == len(b), (n, len(b))
    for k in range(n):
        q = [a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]]
        me.face(list(reversed(q)) if flip else q, m)


def strip_open(me, a, b, m, flip=False):
    n = len(a)
    assert n == len(b), (n, len(b))
    for k in range(n - 1):
        q = [a[k], a[k + 1], b[k + 1], b[k]]
        me.face(list(reversed(q)) if flip else q, m)


def dedupe(loop):
    out = []
    for p in loop:
        if not out or math.dist(out[-1], p) > 1e-5:
            out.append(p)
    if len(out) > 1 and math.dist(out[0], out[-1]) < 1e-5:
        out.pop()
    return out


def cap(me, outer, holes, m, normal_y):
    """A flat end (y constant) filled between its outer loop and holes; faces facing normal_y (+1 front)."""
    loops = [dedupe(outer)] + [dedupe(h) for h in holes]
    flat = [p for lp in loops for p in lp]
    tris = tessellate_polygon([[Vector((p[0], p[2], 0.0)) for p in lp] for lp in loops])
    for t in tris:
        q = [flat[t[0]], flat[t[1]], flat[t[2]]]
        n = Vector(q[1]) - Vector(q[0])
        n = n.cross(Vector(q[2]) - Vector(q[0]))
        if n.y * normal_y < 0:
            q = [q[0], q[2], q[1]]
        me.face(q, m)


def rounded_rect(hw, z0, z1, r, y, n=4):
    """A rounded rectangle in the plane y (x across, z up), counter-clockwise seen from behind (-y): fixed count."""
    pts = []
    for cx, cz, a0 in ((hw - r, z0 + r, -90), (hw - r, z1 - r, 0), (-hw + r, z1 - r, 90), (-hw + r, z0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), y, cz + r * math.sin(a)))
    return pts


# ---------------------------------------------------------------- index helpers (sw180's loop layout)
def es(k, side):
    return W.ext_s(k, side)


def ins(k, side):
    return W.int_s(k, side)


def side_rng(k0, k1, side, shell="ext"):
    """A loop index range [s0, s1) for half-profile indices k0 < k1 on a side."""
    f = es if shell == "ext" else ins
    a, b = f(k0, side), f(k1, side)
    return (min(a, b), max(a, b))


E = W.E
SIDES = ("R", "L")


# ---------------------------------------------------------------- the body
def body():
    yF, yR = W.DOORS["front"], W.DOORS["rear"]
    ax_f = (W.AXLES[0] + W.ARCH_HALF, W.AXLES[0] - W.ARCH_HALF)
    ax_r = (W.AXLES[1] + W.ARCH_HALF, W.AXLES[1] - W.ARCH_HALF)
    lid0, lid1 = W.LID
    cream = lambda s, y, z: "cream"                              # noqa: E731
    black = lambda s, y, z: "black"                              # noqa: E731

    # the nose (the rounded front, cap and all) and the cowl
    me = mod("nose", "end_cap", "nose", "C", hp=500, mass=14)
    cells(me, "nose", "ext", W.NOSE, lid0, 0, NS_E, cream)
    me = mod("cowl", "trim", "cowl", "C", hp=200, mass=3)
    cells(me, "cowl", "ext", lid1, W.TOE, es(E["cant"], "R"), es(E["cant"], "L"), black)
    # the windscreen, the A-pillars and the sails
    me = mod("screen", "glazing", "screen", "C", hp=60, mass=14, breaks="shatter")
    cells(me, "screen", "ext", W.TOE, W.HEADER, es(E["cant"], "R"), es(E["cant"], "L"), lambda s, y, z: "glass")
    for sd in SIDES:
        me = mod("a_pillar_" + sd, "trim", "a_pillar", sd, hp=400, mass=3)
        cells(me, "a_pillar_" + sd, "ext", W.TOE, W.HEADER, *side_rng(E["head"], E["cant"], sd), cream)
        me = mod("sail_" + sd, "trim", "sail", sd, hp=300, mass=2)
        cells(me, "sail_" + sd, "ext", W.TOE, yF[0], *side_rng(E["belt"], E["head"], sd), black)
        # the front fender: below the belt from the nose to the door, the gutter strip over the hood zone
        me = mod("fender_" + sd, "side_bay", "fender", sd, hp=400, mass=9)
        lo = side_rng(E["skirt"], E["belt"], sd)
        cells(me, "fender_" + sd, "ext", lid0, yF[0], *lo, cream, holes=[(ax_f[0], ax_f[1]) + side_rng(E["skirt"], E["arch"], sd)])
        cells(me, "fender_" + sd, "ext", lid0, W.TOE, *side_rng(E["belt"], E["cant"], sd), cream)
        # the rocker under the doors and the B-post between them
        me = mod("b_post_" + sd, "side_bay", "b_post", sd, hp=600, mass=10)
        cells(me, "b_post_" + sd, "ext", yF[0], yR[1], *side_rng(E["skirt"], E["sill"], sd), cream)
        cells(me, "b_post_" + sd, "ext", yF[1], yR[0], *side_rng(E["sill"], E["belt"], sd), cream)
        cells(me, "b_post_" + sd, "ext", yF[1], yR[0], *side_rng(E["belt"], E["head"], sd), black)
        # the rear quarter: below the belt to the tail, the C- and D-pillars round the quarter glass
        me = mod("quarter_" + sd, "side_bay", "quarter", sd, hp=400, mass=10)
        cells(me, "quarter_" + sd, "ext", yR[1], W.TAIL_IN, *side_rng(E["skirt"], E["belt"], sd), cream,
              holes=[(ax_r[0], ax_r[1]) + side_rng(E["skirt"], E["arch"], sd)])
        cells(me, "quarter_" + sd, "ext", yR[1], W.TAIL_IN, *side_rng(E["belt"], E["head"], sd), black,
              holes=[(W.QUARTER[0], W.QUARTER[1]) + side_rng(E["belt"], E["head"], sd)])
        me = mod("quarter_glass_" + sd, "glazing", "quarter_glass", sd, hp=40, mass=6, breaks="shatter")
        cells(me, "quarter_glass_" + sd, "ext", W.QUARTER[0], W.QUARTER[1], *side_rng(E["belt"], E["head"], sd), lambda s, y, z: "glass")
    # the roof: the rails' band and the top, in two bays
    for mid, y0, y1 in (("roof_front", W.HEADER, yR[1]), ("roof_rear", yR[1], W.TAIL_IN)):
        me = mod(mid, "roof_bay", mid, "C", hp=500, mass=12)
        cells(me, mid, "ext", y0, y1, es(E["head"], "R"), es(E["head"], "L"), cream)
    # the tail (its rounded lip and the end face round the hatch)
    me = mod("tail", "end_cap", "tail", "C", hp=500, mass=14)
    cells(me, "tail", "ext", W.TAIL_IN, W.TAIL, 0, NS_E, cream)

    # ---- the interior shell
    def lin_(s, y, z):
        return "lining"
    me = mod("floor", "floor", "floor", "C", hp=2000, mass=20)
    cells(me, "floor", "int", W.TOE, W.TAIL_IN, ins(1, "L"), NS_I + ins(1, "R"), lambda s, y, z: "carpet")
    for sd in SIDES:
        me = mod("kick_" + sd, "lining_bay", "sail", sd, hp=200, mass=3)
        cells(me, "kick_" + sd, "int", W.TOE, yF[0], *side_rng(E["sill"], E["head"], sd, "int"), lin_)
        me = mod("a_trim_" + sd, "lining_bay", "a_pillar", sd, hp=200, mass=1.5)
        cells(me, "a_trim_" + sd, "int", W.TOE, W.HEADER, *side_rng(E["head"], E["cant"], sd, "int"), lin_)
        me = mod("b_trim_" + sd, "lining_bay", "b_post", sd, hp=200, mass=2)
        cells(me, "b_trim_" + sd, "int", yF[1], yR[0], *side_rng(E["sill"], E["head"], sd, "int"), lin_)
        me = mod("quarter_trim_" + sd, "lining_bay", "quarter", sd, hp=200, mass=4)
        cells(me, "quarter_trim_" + sd, "int", yR[1], W.TAIL_IN, *side_rng(E["sill"], E["head"], sd, "int"), lin_,
              holes=[(W.QUARTER[0], W.QUARTER[1]) + side_rng(E["belt"], E["head"], sd, "int")])
    for mid, y0, y1 in (("headliner_front", W.HEADER, yR[1]), ("headliner_rear", yR[1], W.TAIL_IN)):
        me = mod(mid, "ceiling_bay", mid.replace("headliner", "roof"), "C", hp=200, mass=3)
        cells(me, mid, "int", y0, y1, ins(E["head"], "R"), ins(E["head"], "L"), lambda s, y, z: "headliner")

    # ---- the ends: the nose and tail faces, the firewall, the tail wall; the hatch outline in the tail
    nose_loop = [ext_pt(0, s) for s in range(NS_E + 1)]
    sk = nose_loop[0]
    bottom_n = [(-0.60, W.NOSE, W.SKIRT), (0.60, W.NOSE, W.SKIRT)]
    cap(MESH["nose"], nose_loop + bottom_n, [], "cream", 1)
    it = iy(W.TAIL)
    tail_loop = [ext_pt(it, s) for s in range(NS_E + 1)] + [(-0.60, W.TAIL, W.SKIRT), (0.60, W.TAIL, W.SKIRT)]
    H = W.HATCH
    hz0, hz1 = H["z"][0], 1.90
    h_out = rounded_rect(H["half_w"], hz0, hz1, 0.12, W.TAIL)
    h_in = rounded_rect(H["half_w"], hz0, hz1, 0.12, W.TAIL_IN)
    cap(MESH["tail"], tail_loop, [h_out], "cream", -1)
    fw = [int_pt(W.TOE, s) for s in range(NS_I)]
    me = mod("firewall", "end_lining", "firewall", "C", hp=800, mass=8)
    cap(me, fw, [], "dash", -1)
    tw = [int_pt(W.TAIL_IN, s) for s in range(NS_I)]
    me = mod("tail_wall", "end_lining", "tail", "C", hp=300, mass=4)
    cap(me, tw, [h_in], "lining", 1)

    # ---- the reveals (each opening's return from the skin to the lining: part of both shells)
    def reveal(mid, slot, side, y0, y1, k0, k1, m="black"):
        me = mod(mid, "reveal", slot, side, hp=300, mass=2)
        a = rect_ring("ext", y0, y1, *side_rng(k0, k1, side))
        b = rect_ring("int", y0, y1, *side_rng(k0, k1, side, "int"))
        strip(me, a, b, m)
    for sd in SIDES:
        reveal("jamb_front_" + sd, "door_front", sd, yF[0], yF[1], E["sill"], E["head"], "cream")
        reveal("jamb_rear_" + sd, "door_rear", sd, yR[0], yR[1], E["sill"], E["head"], "cream")
        reveal("reveal_quarter_" + sd, "quarter_glass", sd, W.QUARTER[0], W.QUARTER[1], E["belt"], E["head"])
    me = mod("reveal_screen", "reveal", "screen", "C", hp=300, mass=2)
    a = rect_ring("ext", W.TOE, W.HEADER, es(E["cant"], "R"), es(E["cant"], "L"))
    b = rect_ring("int", W.TOE, W.HEADER, ins(E["cant"], "R"), ins(E["cant"], "L"))
    strip(me, a, b, "black")
    me = mod("jamb_hatch", "reveal", "hatch", "C", hp=300, mass=2)
    strip(me, h_out, h_in, "cream")

    holes = cover_check()
    return holes


# ---------------------------------------------------------------- the closers (moving: doors, hatch, lid)
CLOSERS = []


def door(sd, which):
    y0, y1 = W.DOORS[which]
    did = ("F" if which == "front" else "B") + sd
    lid = "door_%s" % did
    me = mod(lid, "door_leaf", "door_" + which, sd, hp=700, mass=22)
    s_lo = side_rng(E["sill"], E["belt"], sd)
    # the outer skin (in by the shut line), its inner trim (exact: the seal), the shut faces between
    g_out = patch(me, "ext", y0, y1, *s_lo, lambda s, y, z: "cream", inset=GAP,
                  edges=(1, 1, 1, 0) if sd == "R" else (1, 1, 0, 1))
    g_in = patch(me, "int", y0, y1, *side_rng(E["sill"], E["belt"], sd, "int"), lambda s, y, z: "lining")
    # (the leaf's outline: outer and inner, the same count; along the bottom, the ends and the top)
    def outline(g):
        top = g[0]
        return [r[0] for r in g] + g[-1][1:] + [r[-1] for r in reversed(g)][1:] + list(reversed(top))[1:-1]
    oo, ii = outline(g_out), outline(g_in)
    strip(me, oo, ii, "cream")
    # the glass above the belt: flush, exact to the aperture (frameless)
    gid = "glass_" + did
    mg = mod(gid, "door_glass", "door_" + which, sd, hp=40, mass=5, breaks="shatter")
    patch(mg, "ext", y0, y1, *side_rng(E["belt"], E["head"], sd), lambda s, y, z: "glass")
    # the window's sill on the door (the belt's top: from the glass foot to the trim's top) -- closed by the strip
    # above; the chrome belt and the woodgrain inlay
    inlay(me, "ext", y0 - 0.05, y1 + 0.05, 0.66, W.BELT - 0.05, sd)
    belt_rod(me, y0 - GAP, y1 + GAP, sd)
    # the pull handle (flush) and the interior pull
    hy = y1 + 0.12
    sx = 1 if sd == "R" else -1
    me.box((sx * (surf_x(hy, W.BELT - 0.03) + 0.004), hy, W.BELT - 0.03), (0.006, 0.07, 0.010), "chrome")
    me.box((sx * (W.WO - W.INT_OFF - 0.03), hy + 0.08, 0.98), (0.03, 0.10, 0.02), "dash")
    # the hinge: the leaf's front edge, at the skin, a vertical axis leaned in 2 degrees at the top
    hx = W.side_x(0.9) * (1 if sd == "R" else -1)
    p0 = (hx, y0, 0.70)
    p1 = (hx - sx * 0.02, y0, 1.30)
    CLOSERS.append({"id": did, "kind": "door", "which": which, "side": sd, "parts": [lid, gid],
                    "hinge": [p0, p1], "open_deg": STD["closers"]["door_" + which]["open_deg"] * (1 if sd == "R" else -1),
                    "y0": y0, "y1": y1})
    # where a person stands to get in, and the grab handles
    marker("stand_%s" % did, (sx * (W.WO + 0.45), (y0 + y1) / 2 - 0.15, 0.0))
    marker("grab_%s" % did, (sx * (W.WO - 0.10), (y0 + y1) / 2, W.HEAD - 0.08))


def inlay(me, shell, y0, y1, z0, z1, sd, avoid=()):
    """A woodgrain panel in a chrome frame, 3 mm proud of the skin (on its own panel, never across an opening)."""
    sx = 1 if sd == "R" else -1
    nz = 6
    ny = max(2, int((y0 - y1) / 0.12))
    grid = []
    for a in range(ny + 1):
        y = y0 - (y0 - y1) * a / ny
        row = []
        zt = min(z1, W.hood_z(y) - 0.05) if y > W.TOE else z1
        for b in range(nz + 1):
            z = z0 + (zt - z0) * b / nz
            row.append((sx * (surf_x(y, z) + 0.004), y, z))
        grid.append(row)
    for a in range(ny):
        for b in range(nz):
            q = [grid[a][b], grid[a + 1][b], grid[a + 1][b + 1], grid[a][b + 1]]
            me.face(q if sd == "L" else list(reversed(q)), "wood")
    ring = [r[0] for r in grid] + grid[-1][1:] + [r[-1] for r in reversed(grid)][1:] + list(reversed(grid[0]))[1:]
    me.pipe([Vector(p) + Vector((sx * 0.002, 0, 0)) for p in ring], 0.007, "chrome", n=6, caps=False)


def surf_x(y, z):
    """The exterior side's half width at (y, z), below the head (from the loft)."""
    lp = loop_at("ext", y)
    for k in range(E["head"]):
        (xa, za), (xb, zb) = lp[k], lp[k + 1]
        if za - 1e-9 <= z <= zb + 1e-9 and zb > za:
            return xa + (xb - xa) * (z - za) / (zb - za)
    return lp[E["belt"]][0]


def belt_rod(me, y0, y1, sd):
    sx = 1 if sd == "R" else -1
    n = max(2, int((y0 - y1) / 0.1))
    pts = []
    for k in range(n + 1):
        y = y0 - (y0 - y1) * k / n
        z = (W.hood_z(y) if y > W.TOE else W.BELT) - 0.012
        pts.append(Vector((sx * (surf_x(y, z) + 0.006), y, z)))
    me.pipe(pts, 0.008, "chrome", n=6)


def hatch():
    H = W.HATCH
    hz0, hz1 = H["z"][0], 1.90
    me = mod("hatch", "hatch", "hatch", "C", hp=700, mass=26)
    o = rounded_rect(H["half_w"] - GAP, hz0 + GAP, hz1 - GAP, 0.12 - GAP, W.TAIL)
    i = rounded_rect(H["half_w"], hz0, hz1, 0.12, W.TAIL_IN)
    G = H["glass"]
    go = rounded_rect(G["half_w"], G["z"][0], G["z"][1], G["corner"], W.TAIL)
    gi = rounded_rect(G["half_w"], G["z"][0], G["z"][1], G["corner"], W.TAIL_IN)
    strip(me, o, go, "cream")                      # the outer skin round the glass
    strip(me, i, gi, "lining", flip=True)          # the inner trim
    strip(me, o, i, "cream")                       # the shut face
    strip(me, go, gi, "black")                     # the window's reveal
    mg = mod("hatch_glass", "hatch_glass", "hatch", "C", hp=40, mass=8, breaks="shatter")
    cap(mg, go, [], "glass", -1)
    # the woodgrain lower panel in its chrome frame, the handle, the high brake lamp
    y = W.TAIL - 0.004
    q = [(-0.62, y, 0.70), (0.62, y, 0.70), (0.62, y, 1.04), (-0.62, y, 1.04)]
    me.face(q, "wood")
    me.pipe([Vector(p) + Vector((0, -0.002, 0)) for p in q + [q[0]]], 0.007, "chrome", n=6, caps=False)
    me.box((0, y - 0.01, 1.07), (0.08, 0.01, 0.015), "chrome")
    me.box((0, W.TAIL - 0.006, 1.875), (0.22, 0.006, 0.012), "lamp_brake")
    marker("light_brake_high", (0, W.TAIL - 0.05, 1.875), math.pi)
    hz = 1.96
    CLOSERS.append({"id": "hatch", "kind": "hatch", "side": "C", "parts": ["hatch", "hatch_glass"],
                    "hinge": [(-0.6, W.TAIL + 0.02, hz), (0.6, W.TAIL + 0.02, hz)], "open_deg": -STD["closers"]["hatch"]["open_deg"]})
    marker("stand_hatch", (0, W.TAIL - 0.55, 0.0), math.pi)


def frunk():
    lid0, lid1 = W.LID
    s0, s1 = es(E["cant"], "R"), es(E["cant"], "L")
    me = mod("frunk_lid", "frunk_lid", "lid", "C", hp=600, mass=12)
    g = patch(me, "ext", lid0, lid1, s0, s1, lambda s, y, z: "cream", inset=GAP)
    # its underside 4 cm down, and the shut faces
    under = [[(p[0], p[1], p[2] - 0.04) for p in row] for row in g]
    for r in range(len(under) - 1):
        for c in range(len(under[0]) - 1):
            me.face([under[r][c], under[r + 1][c], under[r + 1][c + 1], under[r][c + 1]], "tub")

    def outline(gg):
        return [r[0] for r in gg] + gg[-1][1:] + [r[-1] for r in reversed(gg)][1:] + list(reversed(gg[0]))[1:-1]
    strip(me, outline(g), outline(under), "cream")
    # the tub: walls down from the opening to a shelf above the wheel housings, then the well between them
    tub = mod("frunk_tub", "frunk_tub", "lid", "C", hp=400, mass=10)
    rim = rect_ring("ext", lid0, lid1, s0, s1)
    shelf = [(p[0], p[1], W.ARCH_TOP + 0.03) for p in rim]
    strip(tub, rim, shelf, "tub")
    yb0, yb1 = lid0 - 0.04, lid1 + 0.04
    x0 = W.WELL_X - 0.03
    zs = W.ARCH_TOP + 0.03
    box_top = [(x0, yb1, zs), (x0, yb0, zs), (-x0, yb0, zs), (-x0, yb1, zs)]
    cap(tub, shelf, [box_top], "tub", 0)
    zf = W.FLOOR
    box_bot = [(x, y, zf) for x, y, _ in box_top]
    strip(tub, box_top, box_bot, "tub")
    tub.face(box_bot, "tub")
    CLOSERS.append({"id": "frunk", "kind": "lid", "side": "C", "parts": ["frunk_lid"],
                    "hinge": [(-0.6, lid1, W.BELT + 0.01), (0.6, lid1, W.BELT + 0.01)], "open_deg": STD["closers"]["lid"]["open_deg"]})
    marker("stand_frunk", (0, W.NOSE + 0.55, 0.0))
    marker("light_frunk", (0, (lid0 + lid1) / 2, W.ARCH_TOP + 0.08))


# ---------------------------------------------------------------- the wells and the underpan
def wells_and_pan():
    for tag, (ya, yb) in (("front", (W.AXLES[0] + W.ARCH_HALF, W.AXLES[0] - W.ARCH_HALF)),
                          ("rear", (W.AXLES[1] + W.ARCH_HALF, W.AXLES[1] - W.ARCH_HALF))):
        for sd in SIDES:
            sx = 1 if sd == "R" else -1
            me = mod("well_%s_%s" % (tag, sd), "wheel_well", "well_" + tag, sd, hp=600, mass=5)
            rs = rows_between(Y, ya, yb)
            ks = [es(k, sd) for k in (E["skirt"], E["sill"], E["arch"])]
            for y in (ya, yb):                       # (the end walls: the arch's foot in to the housing's wall)
                outer = [ext_pt(iy(y), k) for k in ks]
                me.face(outer + [(sx * W.WELL_X, y, W.ARCH_TOP), (sx * W.WELL_X, y, W.SKIRT)], "rubber")
            top_o = [ext_pt(iy(y), ks[2]) for y in rs]
            top_i = [(sx * W.WELL_X, y, W.ARCH_TOP) for y in rs]
            strip_open(me, top_o, top_i, "rubber", flip=(sd == "L"))
            wall_t = [(sx * W.WELL_X, y, W.ARCH_TOP) for y in rs]
            wall_b = [(sx * W.WELL_X, y, W.SKIRT) for y in rs]
            strip_open(me, wall_t, wall_b, "rubber", flip=(sd == "L"))
            # the arch's black lip, following the opening (on the well: the well is allowed in the arch)
            lip = [Vector(ext_pt(iy(ya), ks[0]))] + [Vector(ext_pt(iy(ya), k)) for k in ks[1:]] + \
                  [Vector(ext_pt(iy(y), ks[2])) for y in rs[1:-1]] + [Vector(ext_pt(iy(yb), k)) for k in reversed(ks)]
            me.pipe([p + Vector((sx * 0.006, 0, 0)) for p in lip], 0.012, "rubber", n=6)
    # the sill pans (the skirt in to the board's deck edge), the end pans and risers
    me = mod("underpan", "underpan", "underpan", "C", hp=800, mass=16)
    arches = [(W.AXLES[0] + W.ARCH_HALF, W.AXLES[0] - W.ARCH_HALF), (W.AXLES[1] + W.ARCH_HALF, W.AXLES[1] - W.ARCH_HALF)]
    for sd in SIDES:
        sx = 1 if sd == "R" else -1
        for a, b in zip(Y, Y[1:]):
            if any(y1 - 1e-9 <= b and a <= y0 + 1e-9 for y0, y1 in arches):
                continue
            pa, pb = ext_pt(iy(a), es(E["skirt"], sd)), ext_pt(iy(b), es(E["skirt"], sd))
            ra = [pa, (sx * 0.60, a, W.SKIRT), (sx * 0.60, a, 0.505)]
            rb = [pb, (sx * 0.60, b, W.SKIRT), (sx * 0.60, b, 0.505)]
            strip_open(me, ra, rb, "rubber", flip=(sd == "L"))
    for y_end, y_riser in ((W.NOSE, 2.16), (W.TAIL, -2.20)):
        rs = rows_between(Y, max(y_end, y_riser), min(y_end, y_riser))
        rows = [[(-0.60, y, W.SKIRT), (0.60, y, W.SKIRT)] for y in rs]
        strip_open(me, [r[0] for r in rows], [r[1] for r in rows], "rubber")
        me.face([(-0.60, y_riser, W.SKIRT), (0.60, y_riser, W.SKIRT), (0.60, y_riser, 0.505), (-0.60, y_riser, 0.505)], "rubber")


# ---------------------------------------------------------------- lamps, bumpers, trim
def lamps_and_trim():
    me = MESH["nose"]
    y = W.NOSE + 0.003
    # the dark glass band, and the projector eyes in chrome rings
    band = [(-0.74, y, 0.70), (0.74, y, 0.70), (0.74, y, 0.85), (-0.74, y, 0.85)]
    lm = mod("head_lamps", "lamp", "head_lamp", "C", hp=60, mass=4, breaks="shatter")
    lm.face(list(reversed(band)), "glass_dark")
    for sx in (1, -1):
        for k, x in enumerate((0.40, 0.58)):
            c = Vector((sx * x, y + 0.004, 0.775))
            T = Matrix.Translation(c)                # (a lathe turns about local +y: the lamp faces forward)
            lm.lathe([(0.0, 0.066), (0.012, 0.064), (0.014, 0.052)], "chrome", n=20, xf=T)
            lm.lathe([(0.0, 0.052), (0.006, 0.045), (0.010, 0.030)], "lamp_drl", n=20, xf=T)
            lm.lathe([(0.008, 0.030), (0.014, 0.020), (0.016, 0.0001)], "lamp_head", n=20, xf=T)
            marker("light_head_%s%d" % ("R" if sx > 0 else "L", k), (sx * x, W.NOSE + 0.05, 0.775))
        lm.box((sx * 0.70, y + 0.004, 0.775), (0.03, 0.004, 0.05), "lamp_amber")
        marker("light_ind_F%s" % ("R" if sx > 0 else "L"), (sx * 0.70, W.NOSE + 0.04, 0.775))
    # the chrome bumpers, front and back, with rubber strips
    for yy, sg in ((W.NOSE, 1), (W.TAIL, -1)):
        bm = mod("bumper_" + ("front" if sg > 0 else "rear"), "trim", "nose" if sg > 0 else "tail", "C", hp=900, mass=10)
        bm.box((0, yy + sg * 0.045, 0.47), (0.82, 0.04, 0.07), "chrome")
        bm.box((0, yy + sg * 0.087, 0.47), (0.80, 0.004, 0.018), "rubber")
        for sx in (1, -1):
            bm.box((sx * 0.80, yy + sg * 0.005, 0.47), (0.05, 0.045, 0.065), "chrome")
    # the tail lamps: pixel bars in the corners outside the hatch
    tl = mod("tail_lamps", "lamp", "tail_lamp", "C", hp=60, mass=3, breaks="shatter")
    y = W.TAIL - 0.004
    for sx in (1, -1):
        x0 = 0.765
        tl.face([(sx * x0, y, 0.92), (sx * 0.86, y, 0.92), (sx * 0.86, y, 1.42), (sx * x0, y, 1.42)][:: -sx], "black")
        for r in range(9):
            for c in range(3):
                z = 0.95 + r * 0.05
                x = x0 + 0.012 + c * 0.03
                m = "lamp_amber" if r == 8 else ("lamp_reverse" if r == 0 else "lamp_tail")
                tl.face([(sx * x, y - 0.003, z), (sx * (x + 0.024), y - 0.003, z), (sx * (x + 0.024), y - 0.003, z + 0.04),
                         (sx * x, y - 0.003, z + 0.04)][:: -sx], m)
        nm = "R" if sx > 0 else "L"
        marker("light_tail_" + nm, (sx * 0.81, W.TAIL - 0.05, 1.2), math.pi)
        marker("light_reverse_" + nm, (sx * 0.81, W.TAIL - 0.05, 0.97), math.pi)
        marker("light_ind_B" + nm, (sx * 0.81, W.TAIL - 0.05, 1.37), math.pi)
    # roof rails (chrome, on the roof, never across an opening)
    rr = MESH["roof_rear"]
    for sx in (1, -1):
        x = sx * 0.56
        z = W.CROWN - 0.012
        rr.pipe([Vector((x, 0.30, z + 0.055)), Vector((x, -2.10, z + 0.055))], 0.014, "chrome", n=8)
        for yy in (0.30, -0.90, -2.10):
            rr.box((x, yy, z + 0.03), (0.018, 0.03, 0.028), "black")
    # mirrors on the sails
    for sd in SIDES:
        sx = 1 if sd == "R" else -1
        me = MESH["sail_" + sd]
        me.pipe([Vector((sx * 0.92, 1.0, 1.12)), Vector((sx * 1.00, 0.98, 1.18))], 0.012, "chrome", n=6)
        me.box((sx * 1.03, 0.97, 1.20), (0.05, 0.035, 0.05), "chrome")
        me.box((sx * 1.03, 0.934, 1.20), (0.045, 0.002, 0.044), "glass_dark")
    # woodgrain inlays and the chrome belt on the fixed panels
    for sd in SIDES:
        inlay(MESH["fender_" + sd], "ext", 2.05, W.AXLES[0] + W.ARCH_HALF + 0.04, 0.66, W.BELT - 0.05, sd)
        inlay(MESH["fender_" + sd], "ext", W.AXLES[0] + W.ARCH_HALF + 0.04, W.DOORS["front"][0] + 0.04, W.ARCH_TOP + 0.04, W.BELT - 0.05, sd)
        inlay(MESH["quarter_" + sd], "ext", W.DOORS["rear"][1] - 0.04, W.AXLES[1] - W.ARCH_HALF - 0.04, W.ARCH_TOP + 0.04, W.BELT - 0.05, sd)
        inlay(MESH["quarter_" + sd], "ext", W.AXLES[1] - W.ARCH_HALF - 0.04, -2.22, 0.66, W.BELT - 0.05, sd)
        belt_rod(MESH["fender_" + sd], 2.12, W.DOORS["front"][0] + 0.004, sd)
        belt_rod(MESH["b_post_" + sd], W.DOORS["front"][1] - 0.004, W.DOORS["rear"][0] + 0.004, sd)
        belt_rod(MESH["quarter_" + sd], W.DOORS["rear"][1] - 0.004, -2.26, sd)
    # the charge flap
    me = MESH["quarter_R"]
    me.box((surf_x(-1.98, 1.0) + 0.003, -1.98, 0.99), (0.002, 0.06, 0.035), "black")


# ---------------------------------------------------------------- the cabin: seats, dash, wheel
def cabin():
    # front seats (buckets), H-points from WAGON.md: y 0.18, z 0.85; the bench behind: y -0.70, z 0.87
    for k, (x, hy, hz) in enumerate(((-0.38, 0.18, 0.85), (0.38, 0.18, 0.85))):
        mid = "seat_front_" + ("L" if x < 0 else "R")
        me = mod(mid, "seat", "free", "L" if x < 0 else "R", hp=300, mass=18)
        seat(me, x, hy, hz, 0.50)
        marker("seat_driver" if x < 0 else "seat_1", (x, hy, hz))
    me = mod("seat_rear", "seat", "free", "C", hp=400, mass=26)
    for x in (-0.40, 0.0, 0.40):
        seat(me, x, -0.70, 0.87, 0.40, bench=True)
    for n, x in enumerate((-0.40, 0.0, 0.40)):
        marker("seat_%d" % (n + 2), (x, -0.70, 0.87))
    # the dash: a slim shelf under the screen, a gauge pod, the two-spoke wheel
    me = mod("dash", "dash", "free", "C", hp=400, mass=14)
    me.box((0, 0.96, 1.00), (0.80, 0.16, 0.06), "dash")
    me.box((0, 0.84, 0.90), (0.78, 0.06, 0.10), "dash")
    me.box((-0.38, 0.80, 1.08), (0.17, 0.05, 0.05), "dash")
    for gx in (-0.45, -0.31):
        me.lathe([(0.0, 0.045), (0.004, 0.045), (0.005, 0.0001)], "gauge", n=16,
                 xf=Matrix.Translation((gx, 0.745, 1.08)))
    c = Vector((-0.38, 0.62, 1.10))
    tilt = Matrix.Rotation(math.radians(68), 4, "X")       # (square to the column: its top leans toward the dash)
    ring = [c + tilt @ Vector((0.19 * math.cos(TAU * k / 24), 0.19 * math.sin(TAU * k / 24), 0)) for k in range(25)]
    me.pipe(ring, 0.014, "black", n=8, caps=False)
    for a in (0.0, math.pi):
        me.pipe([c, c + tilt @ Vector((0.19 * math.cos(a), 0.19 * math.sin(a) * 0.3 - 0.05, 0))], 0.012, "chrome", n=6)
    me.pipe([c, c + Vector((0, 0.25, -0.10))], 0.025, "black", n=8)
    marker("steering", tuple(c))
    marker("light_cabin", (0, -0.4, W.HEADLINER - 0.04))


def seat(me, x, hy, hz, w, bench=False):
    """A seat with its H-point at (x, hy, hz): the cushion, the back leaned 20 degrees, a head restraint."""
    hw = w / 2 - 0.02
    me.box((x, hy + 0.20, hz - 0.08), (hw, 0.26, 0.07), "seat")
    me.box((x, hy + 0.20, hz - 0.25), (hw * 0.7, 0.20, 0.10), "dash")
    back = Matrix.Translation((x, hy - 0.06, hz - 0.02)) @ Matrix.Rotation(math.radians(20), 4, "X")
    me.box((0, 0, 0.32), (hw, 0.07, 0.32), "seat", xf=back)
    if not bench:
        me.box((0, 0.0, 0.76), (hw * 0.55, 0.06, 0.09), "seat", xf=back)


# ---------------------------------------------------------------- the library and the blueprint
def to_library(lib):
    keys = list(M)
    places = []
    slots = STD["slots"]
    for mid, me in MESH.items():
        if not me.bm.verts:
            continue
        mo = MODS[mid]
        slot = mo["slot"]
        if slot in slots:
            anchor = max(slots[slot])                     # the slot's start: its +y end
        else:
            anchor = max(v.co.y for v in me.bm.verts)
        xs = [v.co.x for v in me.bm.verts]
        ys = [v.co.y for v in me.bm.verts]
        zs = [v.co.z for v in me.bm.verts]
        mo["boxes"] = [[round((min(xs) + max(xs)) / 2, 4), round((min(ys) + max(ys)) / 2, 4), round((min(zs) + max(zs)) / 2, 4),
                        round(max(0.02, max(xs) - min(xs)), 4), round(max(0.02, max(ys) - min(ys)), 4), round(max(0.02, max(zs) - min(zs)), 4)]]
        cid = lib.add(me, mo, mo["role"], slot, mo["side"], anchor, keys)
        if cid:
            places.append([mid, cid, round(-anchor, 4)])
    return places


def g(v):
    return [round(c, 4) for c in components.g(v)]


def cabin_points():
    """Seal-test sample points in the cabin (Godot frame), clear of the wheel housings and the seats' insides."""
    pts = []
    for y in (0.85, 0.5, 0.0, -0.4, -1.0, -1.5, -2.05):
        for x in (-0.3, 0.0, 0.3):
            for z in (1.0, 1.45, 1.85):
                if z < 1.2 and (abs(x) > 0.2 or y < -0.95):
                    continue
                if y > W.HEADER and z > W.a_line(y) - 0.12:      # (under the raked windscreen)
                    continue
                pts.append(g((x, y, z)))
    return pts


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RENDER_DIR, exist_ok=True)
    core.reset()
    mats()
    holes = body()
    for sd in SIDES:
        door(sd, "front")
        door(sd, "rear")
    hatch()
    frunk()
    wells_and_pan()
    lamps_and_trim()
    cabin()
    print("OPEN CELLS (the openings): ext %d, int %d" % (len(holes["ext"]), len(holes["int"])))
    comp_root = os.path.join(OUT_DIR, "..", "components")
    standards.write_json(STD, os.path.join(OUT_DIR, "..", "standards"))
    lib = components.Library(STD, STYLE, PALETTE, comp_root)
    places = to_library(lib)
    n, size = lib.write()
    print("COMPONENTS", n, "unique,", size // 1024, "KiB,", len(places), "placed")
    doors = []
    closers = []
    for c in CLOSERS:
        p0, p1 = Vector(c["hinge"][0]), Vector(c["hinge"][1])
        axis = (p1 - p0).normalized()
        e = {"id": c["id"], "kind": c["kind"], "side": c["side"], "parts": c["parts"], "hinge": g(p0),
             "axis": [round(v, 5) for v in components.g(axis)], "open_deg": c["open_deg"]}
        closers.append(e)
        if c["kind"] == "door":
            doors.append({"id": c["id"], "side": c["side"], "z": round(-(c["y0"] + c["y1"]) / 2, 4), "width": round(c["y0"] - c["y1"], 4),
                          "head": W.HEAD, "sill": W.SILL})
    root = core.empty("carrow_wagon", (0, 0, 0))
    for mid, me in MESH.items():
        if me.bm.faces:
            ob = me.obj(origin=Vector((0, 0, 0)), smooth=False, parent=root)
            ob.name = mid
    for name, loc, rot in MARKERS:
        e = core.empty(name, loc, root)
        e.rotation_euler = (0, 0, rot)
    core.export(os.path.join(OUT_DIR, "carrow_wagon_preview.glb"))
    components.write_blueprint(os.path.join(OUT_DIR, "carrow_wagon.blueprint.json"), {
        "_about": "The Carrow station wagon, assembled in the game from the SW180 component library (research/vehicles/wagon/WAGON.md)",
        "standard": STD["id"], "class": STD["class"], "style": STYLE, "kind": "car", "board": STD["board"],
        "stations": [round(-r["y"], 4) for r in STD["rings"]],
        "placements": places, "doors": doors, "closers": closers,
        "length_front": W.NOSE, "length_back": -W.TAIL,
        "platform": {"half_w": 0.62, "y": 0.49, "z": [-2.2, 2.2]},
        "cabin_points": cabin_points(),
        "markers": [[n, g(loc), round(rot, 4)] for n, loc, rot in MARKERS],
    })
    sc, cam = core.render_setup()
    pre = os.path.join(RENDER_DIR, "carrow_wagon")
    core.render_persp(pre + "_34.png", cam, (0, 0.2, 1.0), (5.2, 6.4, 2.6), 1400, 900, lens=40)
    core.render_persp(pre + "_34rear.png", cam, (0, -0.4, 1.0), (-5.0, -6.6, 2.4), 1400, 900, lens=40)
    core.render_ortho(pre + "_side.png", cam, "side", (0, 0, 1.1), 5.6, 1400, 700)
    core.render_ortho(pre + "_front.png", cam, "front", (0, 0, 1.1), 2.6, 900, 900)
    core.render_ortho(pre + "_rear.png", cam, "rear", (0, 0, 1.1), 2.6, 900, 900)
    print("WAGON built:", len(MESH), "modules,", len(MARKERS), "markers")


main()
