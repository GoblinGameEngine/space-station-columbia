"""kit.transit -- a vehicle people ride inside (road tram, buses, train car, sightseeing trolley): the
hull (kit.hull) with the detected windows cut through and glazed, an interior lining with window
openings, a floor, seats, grab poles and strap rails, and the markers the game uses to seat and
stand riders. The road tram is split at its joint into two articulated sections.

Markers (empties): seat_<n> (a sitter's hips; local +Y = facing), stand_<n> (a standing rider's
feet) with strap_<n> (the hand on the strap above), door_<n> (inside the doorway) and exit_<n>
(outside it, on the right/kerb side), seat_driver. Sections: section_0 (front), section_1 (rear),
each with its origin at the joint; the game bends the joint about Z.
"""
import json
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import core, hull

TAU = math.tau
SHELL = 0.08            # roof and wall thickness (m)
CLEAR = 2.2             # the least floor-to-ceiling height in the passenger area (m)
MODULE = 1.2            # articulated: a joint module's length between its two pivots (m)
GAP = 0.45              # the bellows gap at each pivot (m)
COVE = 0.3              # the lining's chamfer from the walls into the ceiling (m)

# per vehicle: floor height, door positions (fractions of the length from the rear; right side),
# the driver's cab length at the front, seating ('transverse' 2+2 rows, 'longitudinal' benches along
# the walls, 'benches' full-width open benches), the articulation joint (fraction) or None, open sides
CFG = {
    "tram": dict(floor=0.36, doors=[0.13, 0.41, 0.6, 0.88], cab=1.6, seating="transverse", joints=[0.25, 0.5, 0.75], open=False),
    "transit_bus": dict(floor=0.38, doors=[0.47, 0.84], cab=1.8, seating="transverse", joints=[], open=False),
    "school_bus": dict(floor=0.75, doors=[0.8], cab=2.5, seating="benches2", joints=[], open=False),
    "passenger_train": dict(floor=1.15, doors=[0.22, 0.78], cab=2.6, seating="transverse", joints=[], open=False),
    "sightseeing_trolley": dict(floor=0.62, doors=[], cab=1.7, seating="benches", joints=[], open=True),
}


def _boxes_obj(name, boxes):
    bm = bmesh.new()
    for (x0, x1, y0, y1, z0, z1) in boxes:
        vs = [bm.verts.new(p) for p in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
        for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            bm.faces.new([vs[i] for i in f])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    core.col().objects.link(ob)
    return ob


def build(an, out_glb, render_prefix=None):
    aid = an["id"]
    cfg = CFG[aid]
    L, W, H = an["size_m"]
    sv = an["views"]["side"]
    wins = [w for w in sv.get("windows_m", []) if w[1] - w[0] > 0.12 and w[3] - w[2] > 0.12]
    ys = [p[0] for p in sv["outline_m"]]
    ymin, ymax = min(ys), max(ys)
    # only the passenger area's windows are cut (the end windscreens stay painted on)
    wins = [w for w in wins if w[0] > ymin + 0.5 and w[1] < ymax - cfg["cab"] - 0.05]
    if len(wins) < 3:                                   # detection failed: a regular band of windows
        z0, z1 = cfg["floor"] + 0.85, min(H - 0.45, cfg["floor"] + 1.95)
        y = ymin + 0.6
        wins = []
        while y + 1.1 < ymax - cfg["cab"]:
            wins.append([y, y + 1.1, z0, z1])
            y += 1.3

    fl = cfg["floor"]
    outline = [tuple(p) for p in sv["outline_m"]]

    def roof(y):
        """The top of the side outline at y (the roof line)."""
        best = None
        for (y0, z0), (y1, z1) in zip(outline, outline[1:] + outline[:1]):
            if (y0 - y) * (y1 - y) <= 0 and y0 != y1:
                z = z0 + (z1 - z0) * (y - y0) / (y1 - y0)
                best = z if best is None else max(best, z)
        return best if best is not None else H
    # the inside face of the walls: the narrowest body half-width over the cabin's height (the
    # overall width includes the mirrors, which would put the liner outside the body)
    hws = [r[1] for v in ("front", "rear") if v in an["views"] for r in an["views"][v]["halfwidth_by_z"]
           if fl + 0.3 <= r[0] <= fl + 1.8]
    xh = min(W / 2, min(hws) if hws else W / 2)        # the hull's half-width at the cabin
    xi = xh - 0.1                                       # the lining

    def cut(body):
        # hollow the hull: the cabin is cut out under the roof line (the shell stays SHELL thick), so
        # the inside is open from the floor to the roof all the way along
        prof_b, prof_t = [], []
        y = ymin + 0.3
        while y <= ymax - 0.3:
            top = roof(y) - SHELL
            if top > fl + 0.6:
                prof_b.append((y, fl))
                prof_t.append((y, top))
            y += 0.2
        if len(prof_b) >= 2:
            cab = hull.prism("cabin", prof_b + list(reversed(prof_t)), "x", xh - 0.05)
            keep = body.data.copy()
            mod = body.modifiers.new("cabin", "BOOLEAN")
            mod.operation = "DIFFERENCE"
            mod.solver = "EXACT"
            mod.object = cab
            bpy.context.view_layer.objects.active = body
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(cab)
            if len(body.data.polygons) < 6:
                print("HOLLOW_FAILED", aid)
                old = body.data
                body.data = keep
                bpy.data.meshes.remove(old)
            else:
                bpy.data.meshes.remove(keep)
        if cfg["open"]:
            # open-sided: everything between the waist and the roof goes, pillars at the ends and middle
            zc0, zc1 = cfg["floor"] + 0.55, H - 0.35
            boxes = []
            y = ymin + 0.5
            seg = (ymax - ymin - 1.0 - cfg["cab"]) / 3
            for i in range(3):
                boxes.append((-W, W, y + 0.08, y + seg - 0.08, zc0, zc1))
                y += seg
        else:
            boxes = [(-W, W, w[0], w[1], w[2], w[3]) for w in wins]
        # one opening at a time: a cut that wrecks the shell (overlapping or degenerate boxes) is skipped
        bpy.context.view_layer.objects.active = body
        for i, b in enumerate(boxes):
            keep = body.data.copy()
            cutter = _boxes_obj("window_%d" % i, [b])
            mod = body.modifiers.new("win", "BOOLEAN")
            mod.operation = "DIFFERENCE"
            mod.solver = "EXACT"
            mod.object = cutter
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(cutter)
            if len(body.data.polygons) < len(keep.polygons) * 0.5 or len(body.data.polygons) < 6:
                print("WINDOW_SKIPPED", i, b)
                old = body.data
                body.data = keep
                bpy.data.meshes.remove(old)
            else:
                bpy.data.meshes.remove(keep)
        return body

    ctx = hull.make(an, cut_windows=cut)
    body = ctx["body"]
    top_z = ctx["top_z"]
    mats = dict(ctx["mats"])
    # the interior as Grok drew it (tools/assets/interior.py): seat rows, colours, a floor texture
    ip = os.path.join(os.path.dirname(an["atlas"]["file"]), "interior.json")
    inside = json.load(open(ip)) if os.path.exists(ip) else {}
    col = inside.get("colours", {})
    liner_c = tuple(min(255, int(c * 1.4)) for c in col["ceiling"]) if "ceiling" in col else (222, 214, 196)
    floor_tex = None
    if inside.get("floor_tex"):
        ft = core.load_image(inside["floor_tex"], aid + "_floor")
        px = list(ft.pixels[:])
        mean = [sum(px[i::4]) / (len(px) / 4) * 255 for i in range(3)]       # sRGB-ish 0..255
        fc = col.get("floor")
        if fc is None or sum((mean[i] - fc[i]) ** 2 for i in range(3)) ** 0.5 < 60:
            floor_tex = ft
    ftw, fth = inside.get("floor_tex_m", [1.0, 1.0])
    mats.update({
        "glass": core.mat("glass", core.lin((150, 175, 185)), rough=0.05),
        "liner": core.mat("liner", core.lin(liner_c), rough=0.7),
        "floor": core.mat("floor", core.lin(tuple(col.get("floor", (92, 96, 98)))), rough=0.85, tex=floor_tex),
        "seat": core.mat("seat", core.lin(tuple(col.get("seat", (44, 120, 128)))), rough=0.75),
        "lamp": core.mat("lamp", core.lin((255, 250, 235)), rough=0.4, emit=(1.0, 0.97, 0.9), emit_strength=2.0),
        "pole": core.mat("pole", core.lin((214, 200, 120)), rough=0.3, metal=0.8),
        "strap": core.mat("strap", core.lin((40, 40, 42)), rough=0.6),
    })
    # the hull's own inside (the hollowed cabin's walls, roof and floor) is lining, not the outside paint
    me = body.data
    me.materials.append(mats["liner"])
    li = len(me.materials) - 1
    for poly in me.polygons:
        c, nrm = poly.center, poly.normal
        in_cabin = abs(c.x) < xh - 0.01 and fl - 0.02 < c.z < roof(c.y) - SHELL + 0.02 and ymin + 0.25 < c.y < ymax - 0.25
        facing_in = (nrm.x * (1 if c.x > 0 else -1) < -0.5) or abs(nrm.z) > 0.7 or abs(nrm.y) > 0.7
        if in_cabin and facing_in:
            poly.material_index = li
    glass = mats["glass"]
    glass.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.28
    glass.surface_render_method = "BLENDED"
    glass.use_backface_culling = False
    y_rear, y_front = ymin + 0.35, ymax - cfg["cab"]

    def ceil(y):
        return roof(y) - SHELL - 0.03
    # the passenger area ends where the roof comes down below the clearance
    while y_rear < y_front and ceil(y_rear) < fl + CLEAR:
        y_rear += 0.1
    while y_front > y_rear and ceil(y_front) < fl + CLEAR:
        y_front -= 0.1
    low = min(ceil(y_rear + (y_front - y_rear) * k / 40) for k in range(41)) - fl
    print("CLEARANCE", aid, "%.2f m floor to ceiling at the lowest (min %.1f)" % (low, CLEAR), "" if low >= CLEAR - 0.01 else "TOO LOW")
    m = core.Mesh(aid + "_interior", mats)
    # floor and ceiling in strips (the ceiling follows the roof)
    n = max(4, int((y_front - y_rear) / 0.6))
    for i in range(n):
        a = y_rear + (y_front - y_rear) * i / n
        b = y_rear + (y_front - y_rear) * (i + 1) / n
        m.face([Vector((-xi, a, fl)), Vector((xi, a, fl)), Vector((xi, b, fl)), Vector((-xi, b, fl))], "floor",
               [(-xi / fth, a / ftw), (xi / fth, a / ftw), (xi / fth, b / ftw), (-xi / fth, b / ftw)])
        if not cfg["open"] and i % 2 == 0:              # a lamp panel down the middle of the ceiling
            c = (a + b) / 2
            m.box((0, c, ceil(c) - 0.02), (0.18, (b - a) * 0.8, 0.015), "lamp")
        cx = xi - (0 if cfg["open"] else COVE)
        m.face([Vector((-cx, b, ceil(b))), Vector((cx, b, ceil(b))), Vector((cx, a, ceil(a))), Vector((-cx, a, ceil(a)))], "liner")
    # the side linings with window openings (strips between window edges)
    if not cfg["open"]:
        # the lining's openings: the drawn panes merged into window bays (mullions closer than 0.4 m
        # make one opening), so from inside the windows read as the wide bays Grok drew
        iw = []
        for w in sorted(wins):
            if iw and w[0] - iw[-1][1] < 0.4:
                iw[-1] = [iw[-1][0], max(iw[-1][1], w[1]), min(iw[-1][2], w[2]), max(iw[-1][3], w[3])]
            else:
                iw.append(list(w))
        edges = sorted({y_rear, y_front} | {w[0] for w in iw if y_rear < w[0] < y_front} | {w[1] for w in iw if y_rear < w[1] < y_front})
        for a, b in zip(edges, edges[1:]):
            mid = (a + b) / 2
            holes = sorted([(w[2], w[3]) for w in iw if w[0] <= mid <= w[1]])
            zs, z = [], fl
            for h0, h1 in holes:
                if h0 > z:
                    zs.append((z, h0))
                z = max(z, h1)
            top = min(ceil(a), ceil(b)) - COVE
            if top > z:
                zs.append((z, top))
            for side in (1, -1):
                x = side * xi
                for z0, z1 in zs:
                    q = [Vector((x, a, z0)), Vector((x, b, z0)), Vector((x, b, z1)), Vector((x, a, z1))]
                    m.face(q if side < 0 else list(reversed(q)), "liner")
                # the cove up to the ceiling, and a band in the seat colour under the windows
                q = [Vector((x, a, ceil(a) - COVE)), Vector((x, b, ceil(b) - COVE)), Vector((x - side * COVE, b, ceil(b))), Vector((x - side * COVE, a, ceil(a)))]
                m.face(q if side < 0 else list(reversed(q)), "liner")
                if holes:
                    sz = holes[0][0]
                    q = [Vector((x - side * 0.005, a, sz - 0.12)), Vector((x - side * 0.005, b, sz - 0.12)), Vector((x - side * 0.005, b, sz)), Vector((x - side * 0.005, a, sz))]
                    m.face(q if side < 0 else list(reversed(q)), "seat")
        # glazing in every window, both sides
        for w in wins:
            for side in (1, -1):
                x = side * (W / 2 - 0.04)
                q = [Vector((x, w[0], w[2])), Vector((x, w[1], w[2])), Vector((x, w[1], w[3])), Vector((x, w[0], w[3]))]
                m.face(q, "glass")
        # end walls
        for y, flip in ((y_rear, False), (y_front, True)):
            q = [Vector((-xi, y, fl)), Vector((xi, y, fl)), Vector((xi, y, ceil(y))), Vector((-xi, y, ceil(y)))]
            m.face(list(reversed(q)) if flip else q, "liner")
    # seating, poles, straps, markers
    door_ys = [ymin + (ymax - ymin) * f for f in cfg["doors"]]
    markers = []
    seat_n = stand_n = 0

    yjs = [ymin + (ymax - ymin) * f for f in cfg["joints"]]       # joint module centres, rear to front

    def near_door(y, pad=0.85):
        if any(abs(y - yj) < MODULE / 2 + GAP / 2 + 0.4 for yj in yjs):     # the joint modules: no seats
            return True
        return any(abs(y - d) < pad for d in door_ys)

    def seat(x, y, facing, width=0.45):
        nonlocal seat_n
        sh = fl + 0.45
        hw = width / 2 - 0.02
        m.box((x, y, sh - 0.05), (hw, 0.22, 0.06), "seat")                      # cushion
        tilt = Matrix.Rotation(-0.16 * facing, 4, "X")
        back = Matrix.Translation(Vector((x, y - 0.25 * facing, sh + 0.34))) @ tilt
        m.box((0, 0, 0), (hw, 0.045, 0.34), "seat", back)                        # backrest, leaning back
        m.pipe([back @ Vector((-hw, -0.02 * facing, 0.37)), back @ Vector((hw, -0.02 * facing, 0.37))], 0.014, "pole", n=8)  # grab rail
        m.box((x, y - 0.05 * facing, fl + 0.2), (0.04, 0.04, 0.2), "pole")       # pedestal
        markers.append(("seat_%d" % seat_n, Vector((x, y - 0.05 * facing, sh + 0.02)), 0.0 if facing > 0 else math.pi))
        seat_n += 1

    # the rows: as drawn on Grok's plan (kept inside the cabin, off the doors and the joint, 0.7 m
    # apart at least), else every 0.82 m
    rows = []
    for ry, left, right in sorted(inside.get("rows", []), key=lambda r: r[0]):
        if y_rear + 0.35 < ry < y_front - 0.35 and not near_door(ry) and (not rows or ry - rows[-1] >= 0.7):
            rows.append(ry)
    if len(rows) < 3:
        rows, y = [], y_rear + 0.5
        while y < y_front - 0.4:
            if not near_door(y):
                rows.append(y)
            y += 0.82
    for y in rows:
        if True:
            if cfg["seating"] in ("benches", "benches2"):
                full = cfg["seating"] == "benches"
                cols = [-xi + 0.3 + k * 0.48 for k in range(int((2 * xi - 0.3) / 0.48))] if full else [-xi + 0.28, -xi + 0.76, xi - 0.76, xi - 0.28]
                for x in cols:
                    seat(x, y, 1, 0.46)
            else:
                for x in (-xi + 0.28, -xi + 0.74, xi - 0.74, xi - 0.28):
                    seat(x, y, 1)
    # poles at the doors and down the aisle, a strap rail each side of the aisle
    if not cfg["open"]:
        for d in door_ys:
            for dy in (-0.75, 0.75):
                m.pipe([Vector((0.45, d + dy, fl)), Vector((0.45, d + dy, ceil(d + dy)))], 0.018, "pole", n=8)
        rail_z = lambda yy: ceil(yy) - 0.06
        for x in (-0.35, 0.35):
            pts = [Vector((x, yy, rail_z(yy))) for yy in [y_rear + 0.4 + (y_front - y_rear - 0.8) * k / 12 for k in range(13)]]
            m.pipe(pts, 0.016, "pole", n=8, caps=False)
            yy = y_rear + 0.6
            while yy < y_front - 0.4:
                top = rail_z(yy)
                m.pipe([Vector((x, yy, top)), Vector((x, yy, top - 0.22))], 0.008, "strap", n=5)
                m.box((x, yy, top - 0.27), (0.015, 0.05, 0.05), "strap")
                markers.append(("stand_%d" % stand_n, Vector((x * 0.6, yy, fl)), 0.0))
                markers.append(("strap_%d" % stand_n, Vector((x, yy, top - 0.27)), 0.0))
                stand_n += 1
                yy += 1.2
    for i, d in enumerate(door_ys):
        markers.append(("door_%d" % i, Vector((xi - 0.4, d, fl)), -math.pi / 2))
        markers.append(("exit_%d" % i, Vector((W / 2 + 0.7, d, 0.0)), -math.pi / 2))
    markers.append(("seat_driver", Vector((-0.5, ymax - cfg["cab"] * 0.55, fl + 0.5)), 0.0))
    interior = m.obj(parent=body)
    for name, loc, rz in markers:
        e = core.empty(name, loc, body)
        e.rotation_euler = (0, 0, rz)
    wy = sorted(w[0] for w in ctx["wheels"]) if len(ctx["wheels"]) >= 2 else [ymin + 1.0, ymax - 1.0]
    if yjs:
        # articulation: sections and short joint modules, alternating, front to back. Each body's lead
        # and trail pivots are the points the game keeps on the road: near the nose, the joints, near
        # the tail; GAP/2 either side of every joint pivot is left open for the bellows.
        piv = [ymax - 1.0]                                  # the end sections steer from near the nose and tail
        for yj in sorted(yjs, reverse=True):
            piv += [yj + MODULE / 2, yj - MODULE / 2]
        piv.append(ymin + 1.0)
        spec = []
        for k in range(len(piv) - 1):
            lead, trail = piv[k], piv[k + 1]
            spec.append((lead, trail, None if k == 0 else lead - GAP / 2, None if k == len(piv) - 2 else trail + GAP / 2))
        rib(aid, mats, xh, fl, min(roof(y) for y in yjs), body)
        split_bodies(aid, body, spec)
    else:
        # one body: the couplers lead and trail (trains couple end to end)
        core.empty("pivot_lead", Vector((0, ymax + 0.4, 0)), body)
        core.empty("pivot_trail", Vector((0, ymin - 0.4, 0)), body)
    hull.finish(ctx, out_glb, render_prefix)
    if render_prefix:                                   # the view down the aisle, to hold against Grok's
        sc, cam = core.render_setup()
        core.render_persp(render_prefix + "_aisle.png", cam, (0, y_front, fl + 1.25), (0, y_rear + 0.2, fl + 1.6), 1000, 700, 16)
    print("TRANSIT", aid, seat_n, "seats", stand_n, "standing places", len(wins), "windows")


def rib(aid, mats, xh, fl, top, parent):
    """One bellows rib (the game strings several across each joint gap): a rounded rubber ring the
    hull's section at the joint, with a floor slat."""
    m = core.Mesh("bellows_rib", mats)
    x0, z0, z1 = xh - 0.03, fl - 0.22, top - 0.06
    def loop(inset, n=6):
        r = 0.35 - inset
        a, b, c0, c1 = -x0 + inset, x0 - inset, z0 + inset, z1 - inset
        pts = []
        for cx, cz, a0 in ((b - r, c1 - r, 0), (a + r, c1 - r, 90), (a + r, c0 + r, 180), (b - r, c0 + r, 270)):
            for k in range(n + 1):
                t = math.radians(a0 + 90 * k / n)
                pts.append((cx + r * math.cos(t), cz + r * math.sin(t)))
        return pts
    out, inn = loop(0.0), loop(0.09)
    d = 0.06
    n = len(out)
    for i in range(n):
        j = (i + 1) % n
        for y, flip in ((-d, False), (d, True)):
            q = [Vector((out[i][0], y, out[i][1])), Vector((out[j][0], y, out[j][1])), Vector((inn[j][0], y, inn[j][1])), Vector((inn[i][0], y, inn[i][1]))]
            m.face(list(reversed(q)) if flip else q, "strap")
        q = [Vector((out[i][0], -d, out[i][1])), Vector((out[i][0], d, out[i][1])), Vector((out[j][0], d, out[j][1])), Vector((out[j][0], -d, out[j][1]))]
        m.face(q, "strap")
        q = [Vector((inn[i][0], -d, inn[i][1])), Vector((inn[j][0], -d, inn[j][1])), Vector((inn[j][0], d, inn[j][1])), Vector((inn[i][0], d, inn[i][1]))]
        m.face(q, "liner")
    m.box((0, 0, fl - 0.02), (x0 - 0.1, 0.16, 0.02), "floor")
    return m.obj(parent=parent)


def split_bodies(aid, body, spec):
    """Cut the vehicle across its length into bodies body_0 (front), body_1, ...: spec is a list of
    (lead_y, trail_y, cut_front_y | None, cut_back_y | None) per body. Every mesh child is bisected;
    empties and wheels go to the body they fall in. Bodies keep the model origin; pivot_lead and
    pivot_trail empties mark where the game puts them on the road. The bellows_rib goes to body_1."""
    bpy.context.view_layer.update()
    root = core.empty(aid, Vector((0, 0, 0)))
    bods = [core.empty("body_%d" % k, Vector((0, 0, 0)), root) for k in range(len(spec))]
    ribo = [c for c in body.children if c.name.startswith("bellows_rib")]
    meshes = [body] + [c for c in body.children if c.type == "MESH" and not c.name.startswith("wheel_") and c not in ribo]
    for ob in meshes:
        for k, (lead, trail, cf, cb) in enumerate(spec):
            dup = ob.copy()
            dup.data = ob.data.copy()
            dup.parent = None
            dup.matrix_world = ob.matrix_world.copy()
            core.col().objects.link(dup)
            bm = bmesh.new()
            bm.from_mesh(dup.data)
            inv = dup.matrix_world.inverted()
            no = (inv.to_3x3() @ Vector((0, 1, 0))).normalized()
            if cf is not None:      # keep y < cf
                bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=inv @ Vector((0, cf, 0)), plane_no=no, clear_outer=True)
            if cb is not None:      # keep y > cb
                bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=inv @ Vector((0, cb, 0)), plane_no=no, clear_inner=True)
            bm.to_mesh(dup.data)
            bm.free()
            dup.name = "%s_%d" % (ob.name, k)
            core.attach(dup, bods[k])
    others = [c for c in body.children if not (c.type == "MESH" and not c.name.startswith("wheel_")) or c in ribo]
    for c in others:
        y = c.matrix_world.translation.y
        mw = c.matrix_world.copy()
        c.parent = None
        c.matrix_world = mw
        k = 1 if c in ribo else next((k for k, sp in enumerate(spec) if (sp[3] is None or y > sp[3]) and (sp[2] is None or y < sp[2])), 0)
        core.attach(c, bods[k])
    for k, (lead, trail, cf, cb) in enumerate(spec):
        core.empty("pivot_lead", Vector((0, lead, 0)), bods[k])
        core.empty("pivot_trail", Vector((0, trail, 0)), bods[k])
    for ob in meshes:
        bpy.data.objects.remove(ob)
