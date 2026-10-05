"""
build.py -- build the fleet's bodies: for each class standard (fleet/specs.py), its base type and the variant
types built on it, as library components and blueprints the game assembles on the tube frame.

  flatpak run org.blender.Blender -b --factory-startup --python <abs build.py> -- OUT_ROOT RENDER_DIR [STD ...]

OUT_ROOT is godot_project/remake/vehicles. Writes:
  standards/<STD>.json                     the class standard
  components/<STD>/<style>.pack|.catalog.json  the base style's components; each variant's own tokens and palette
  fleet/<type>.blueprint.json              each type's placements (its tokens), closers, markers
  fleet/fleet_bodies.json                  the registry the game reads (type -> blueprint, board, hull, seats)
and renders to RENDER_DIR. research/vehicles/FLEET_BODIES.md, research/vehicles/TOKENS.md.
"""
import copy
import json
import math
import os
import sys

import bpy  # noqa: F401
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from kit import core  # noqa: E402
from kit.core import lin, mat  # noqa: E402
from kit import components  # noqa: E402
from kit import loft as LOFT  # noqa: E402
from kit import standards  # noqa: E402
import specs  # noqa: E402
from builder import Builder  # noqa: E402
import decals as DC  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_ROOT, RENDER_DIR = argv[0], argv[1]
ONLY = set(argv[2:])


def materials(pal):
    M = {}
    P = {}
    for name, (rgb, rough, metal, emit, es, alpha) in pal.items():
        if emit:
            M[name] = mat(name, lin(rgb), rough=rough, metal=metal, emit=lin(emit), emit_strength=max(es, 0.001))
        else:
            M[name] = mat(name, lin(rgb), rough=rough, metal=metal)
        P[name] = {"albedo": [round(c / 255.0, 4) for c in rgb], "rough": rough, "metal": metal,
                   "emit": [round(c / 255.0, 4) for c in emit] if emit else None, "emit_strength": es, "alpha": alpha}
    g = M["glass"]
    g.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.25
    g.surface_render_method = "BLENDED"
    for m in M.values():
        m.use_backface_culling = False
    return M, P


def g(v):
    return [round(c, 4) for c in components.g(v)]


def decals_out(ds):
    """A type's decals (fleet/decals.py) in the Godot frame: [image, position, normal, up, width, height, tint 0..1 or None]."""
    return [[d[0], g(d[1]), g(d[2]), g(d[3]), round(d[4], 3), round(d[5], 3), [round(c / 255.0, 3) for c in d[6]] if d[6] else None]
            for d in ds]


def to_library(b, lib, mids):
    keys = list(b.M)
    places = []
    for mid in mids:
        me = b.MESH[mid]
        if not me.bm.verts:
            continue
        mo = b.MODS[mid]
        anchor = max(v.co.y for v in me.bm.verts)
        xs = [v.co.x for v in me.bm.verts]
        ys = [v.co.y for v in me.bm.verts]
        zs = [v.co.z for v in me.bm.verts]
        mo["boxes"] = [[round((min(xs) + max(xs)) / 2, 4), round((min(ys) + max(ys)) / 2, 4), round((min(zs) + max(zs)) / 2, 4),
                        round(max(0.02, max(xs) - min(xs)), 4), round(max(0.02, max(ys) - min(ys)), 4), round(max(0.02, max(zs) - min(zs)), 4)]]
        cid = lib.add(me, mo, mo["role"], mo["slot"], mo["side"], anchor, keys)
        if cid:
            places.append([mid, cid, round(-anchor, 4)])
    return places


def closers_out(cl):
    out, doors = [], []
    for c in cl:
        e = {"id": c["id"], "kind": c["kind"], "side": c["side"], "parts": c["parts"]}
        if c["kind"] == "slide":
            e["hinge"] = [0, 0, 0]
            e["axis"] = [0, 1, 0]
            e["open_deg"] = 0
            e["slide"] = [c["slide"][0], c.get("lift", 0.0), -c["slide"][1]]   # (Godot: x, up, z = -Blender y)
        else:
            p0, p1 = Vector(c["hinge"][0]), Vector(c["hinge"][1])
            e["hinge"] = g(p0)
            e["axis"] = [round(v, 5) for v in components.g((p1 - p0).normalized())]
            e["open_deg"] = c["open_deg"]
        out.append(e)
        if c["kind"] in ("door", "slide", "roll") and "y0" in c:
            dd = {"id": c["id"], "side": c["side"], "z": round(-(c["y0"] + c["y1"]) / 2, 4), "width": round(c["y0"] - c["y1"], 4)}
            for k in ("sill", "head"):                       # (a cargo door's own opening, where it isn't the cab's)
                if k in c:
                    dd[k] = round(c[k], 4)
            doors.append(dd)
    return out, doors


def dress(b, st, var=None):
    """The dressing tokens: lamps, bumpers, mirrors, mouldings, overlays, equipment (a variant: only its own)."""
    rb = (var or {}).get("rebuild", {})
    full = var is None
    if full or any(k in rb for k in ("head_lamp", "grille", "tail_lamp", "bezel")):
        b.lamps(st)
    if full or "bumper" in rb:
        b.bumpers(st)
    if full or "mirror" in rb:
        b.mirrors(st)
    if full or "belt_trim" in rb:
        b.belt_mouldings(st)
        b.door_belts(st)
    if full and st.get("roof_rails"):
        b.roof_rails(st)
    for key, prefix, role in (("inlay", "inlay", "trim"), ("livery", "livery", "trim")):
        o = (var or st).get(key)
        if o:
            z0, z1 = o["z"]
            b.panel_overlays(prefix, role, o["m"], z0, z1 if z1 is not None else b.L.belt - 0.05, frame=o.get("frame"))
    for e in (var or st).get("equipment", []):
        b.equipment(e, dict(st, **(var or {})))


def renders(name, L):
    sc, cam = core.render_setup()
    pre = os.path.join(RENDER_DIR, name)
    C = L.spec.get("cargo") or {}
    tail = C.get("y1", L.tail)
    ln = L.nose - tail
    mid = (L.nose + tail) / 2
    h = max(L.crown, C.get("top_z") or 0, C.get("rail_z") or 0)
    if L.spec.get("render"):                                # (what hangs past the body: a freighter's pods, a fin)
        tail, h = L.spec["render"]
        ln, mid = L.nose - tail, (L.nose + tail) / 2
    A = L.spec.get("aero")
    if A:                                                   # (an aerostat: frame the envelope and what hangs under it)
        el, er, ey, ez = A["env"]
        ln, mid, h = el, ey, ez + er
        low = A["sling"][3] - 0.5 if A.get("sling") else 0.0
        d = ln * 1.1
        zm = (h + low) / 2
        core.render_persp(pre + "_34.png", cam, (0, mid, zm), (d * 0.85, mid + d * 1.0, zm + d * 0.35), 1100, 720, lens=40)
        core.render_persp(pre + "_34rear.png", cam, (0, mid, zm), (-d * 0.8, mid - d * 1.05, zm + d * 0.3), 1100, 720, lens=40)
        core.render_ortho(pre + "_side.png", cam, "side", (0, mid, zm), ln + 1.5, 1100, 640)
        core.render_ortho(pre + "_front.png", cam, "front", (0, mid, zm), max(2 * er + 6.0, (h - low + 1.5) * 900 / 640), 900, 640)
        return
    d = max(ln, 4.2) * 1.15
    core.render_persp(pre + "_34.png", cam, (0, mid, h * 0.45), (d * 0.85, mid + d * 1.1, h + 1.2), 1100, 720, lens=40)
    core.render_persp(pre + "_34rear.png", cam, (0, mid, h * 0.45), (-d * 0.8, mid - d * 1.15, h + 1.0), 1100, 720, lens=40)
    core.render_ortho(pre + "_side.png", cam, "side", (0, mid, h / 2 + 0.1), ln + 0.8, 1100, 560)


def build_trailer(sid, registry):
    """A trailer: only a cargo module on Harrow running gear (kit/loft.py TrailerLoft)."""
    spec = specs.CLASSES[sid]
    st = specs.STYLES[sid]
    L = LOFT.TrailerLoft(spec)
    C = spec["cargo"]
    std = L.standard()
    core.reset()
    M, PAL = materials(st["palette"])
    b = Builder(L, M)
    rr, tt = b.cargo_rings(C)
    std["rings"], std["ring"], std["top_openings"] = rr, rr[0]["joints"], tt
    b.cargo(C, st)
    for nm, loc in spec.get("markers", []):
        b.marker(nm, loc)
    O = spec.get("open")
    if O:                                                 # (an open light vehicle: its seats, controls, cowl, canopy)
        b.open_parts(O, st)
    elif not spec.get("machine"):                         # (a trailer's lamps and guard; not a machine's)
        b.trailer_dress(st)
    for e in st.get("equipment", []):
        b.equipment(e, st)
    standards.write_json(std, os.path.join(OUT_ROOT, "standards"))
    lib = components.Library(std, st["name"], PAL, os.path.join(OUT_ROOT, "components"))
    places = to_library(b, lib, list(b.MESH))
    n, size = lib.write()
    print("%s %s: %d components, %d KiB" % (sid, st["name"], n, size // 1024))
    clo, doors = closers_out(b.CLOSERS)
    fleet_dir = os.path.join(OUT_ROOT, "fleet")
    os.makedirs(fleet_dir, exist_ok=True)
    vtype = st["type"]
    components.write_blueprint(os.path.join(fleet_dir, vtype + ".blueprint.json"), {
        "_about": "%s on the %s standard (a trailer; remake/blender/fleet/build.py)" % (vtype, sid),
        "type": vtype, "standard": sid, "class": spec["cls"], "style": st["name"], "kind": "car" if O else "trailer", "board": spec["board"],
        "stations": [round(-r["y"], 4) for r in std["rings"]], "placements": places, "doors": doors, "closers": clo,
        "length_front": L.nose, "length_back": -L.tail,
        "platform": {"half_w": round(L.mount_x + 0.02, 3), "y": round(L.board.get("deck_top_m", 0.50) - 0.01, 3), "z": [-L.board["length_m"] / 2, L.board["length_m"] / 2]},
        "cabin_points": [], "markers": [[nm, g(loc), round(rot, 4)] for nm, loc, rot in b.MARKERS],
        "decals": decals_out(DC.place(b, vtype))})
    registry[vtype] = {"blueprint": "res://remake/vehicles/fleet/%s.blueprint.json" % vtype, "standard": sid, "style": st["name"],
                       "board": spec["board"], "phys": vtype, "half_w": C["half_w"], "height": L.crown, "nose": L.nose, "tail": L.tail,
                       "floor": C["floor_z"], "driver": O.get("driver", "L") if O else "none", "trailer": not O}
    root = core.empty(vtype, (0, 0, 0))
    for mid, me in b.MESH.items():
        if me.bm.faces:
            ob = me.obj(origin=Vector((0, 0, 0)), smooth=False, parent=root)
            ob.name = mid
    renders(vtype, L)


def build_class(sid, registry):
    spec = specs.CLASSES[sid]
    if spec.get("trailer"):
        return build_trailer(sid, registry)
    st = specs.STYLES[sid]
    L = LOFT.Loft(spec)
    std = L.standard()
    core.reset()
    M, PAL = materials(st["palette"])
    b = Builder(L, M)
    C = spec.get("cargo")
    if C:                                                   # (the cargo module's frame rings join the cab's)
        rr, tt = b.cargo_rings(C)
        std["rings"] = sorted(std["rings"] + rr, key=lambda r: -r["y"])
        std["top_openings"] = std["top_openings"] + tt
        if C["kind"] in ("bed", "dump", "deck"):           # (an open bed's frame shows, as an open tub's does: the user, 2026-10-02)
            std["frame_shown_y"] = [C["y1"], C["y0"]]
    holes = b.body(st)
    b.closers(st)
    b.wells_and_pan(st)
    if C:
        b.cargo(C, st)
    b.cabin(st)
    for nm, loc in spec.get("markers", []):               # (a class's own markers: a rail car's bogie pivots, its exits)
        b.marker(nm, loc)
    base_shell = set(b.MESH)
    dress(b, st)
    print("%s OPEN CELLS: ext %d, int %d" % (sid, len(holes["ext"]), len(holes["int"])))
    comp_root = os.path.join(OUT_ROOT, "components")
    standards.write_json(std, os.path.join(OUT_ROOT, "standards"))
    lib = components.Library(std, st["name"], PAL, comp_root)
    places = to_library(b, lib, list(b.MESH))
    n, size = lib.write()
    print("%s %s: %d components, %d KiB" % (sid, st["name"], n, size // 1024))
    base_closers = copy.deepcopy(b.CLOSERS)
    base_markers = list(b.MARKERS)
    fleet_dir = os.path.join(OUT_ROOT, "fleet")
    os.makedirs(fleet_dir, exist_ok=True)

    def blueprint(vtype, style, pl, cl, mk):
        clo, doors = closers_out(cl)
        bp = {"_about": "%s on the %s standard (remake/blender/fleet/build.py; research/vehicles/FLEET_BODIES.md)" % (vtype, sid),
              "type": vtype, "standard": sid, "class": spec["cls"], "style": style, "kind": "car", "board": spec["board"],
              "stations": [round(-r["y"], 4) for r in std["rings"]], "placements": pl, "doors": doors, "closers": clo,
              "length_front": L.nose, "length_back": -(C["y1"] if C else L.tail),
              "platform": {"half_w": round(L.mount_x + 0.02, 3), "y": round(L.board.get("deck_top_m", 0.50) - 0.01, 3), "z": [-L.board["length_m"] / 2, L.board["length_m"] / 2]},
              "cabin_points": b.cabin_points(),
              "markers": [[nm, g(loc), round(rot, 4)] for nm, loc, rot in mk],
              "decals": decals_out(DC.place(b, vtype))}
        path = os.path.join(fleet_dir, vtype + ".blueprint.json")
        components.write_blueprint(path, bp)
        registry[vtype] = {"blueprint": "res://remake/vehicles/fleet/%s.blueprint.json" % vtype, "standard": sid, "style": style,
                           "board": spec["board"], "phys": vtype, "half_w": max(L.half_w, C.get("half_w", 0) if C else 0),
                           "height": max(L.crown, (C.get("top_z") or C.get("rail_z") or 0) if C else 0), "nose": L.nose, "tail": C["y1"] if C else L.tail,
                           "floor": L.floor, "driver": spec.get("driver", "L")}
        A = spec.get("aero")
        if A:                                               # (an aerostat: it flies -- RemakeFleetAerostat -- on these)
            registry[vtype]["air"] = True
            registry[vtype]["aero"] = {"env": list(A["env"]), "sling": list(A["sling"]) if A.get("sling") else None}
            registry[vtype]["ground"] = round(A["sling"][3] - 0.52, 3) if A.get("sling") else 0.0
        elif spec.get("space") is not None:                 # (a spacecraft, the spoke elevator: it flies -- RemakeFleetAerostat)
            registry[vtype]["air"] = True
            registry[vtype]["aero"] = {"env": None, "sling": None}
        return bp

    blueprint(st["type"], st["name"], places, base_closers, base_markers)
    root = core.empty(st["type"], (0, 0, 0))
    for mid, me in b.MESH.items():
        if me.bm.faces:
            ob = me.obj(origin=Vector((0, 0, 0)), smooth=bool(b.MODS[mid].get("smooth")), parent=root)
            ob.name = mid
    renders(st["type"], L)
    # ---- the variants: their own tokens and palette on the base components
    for var in specs.VARIANTS.get(sid, []):
        vst = dict(st)
        vst.update(var.get("rebuild", {}))
        for k in ("blank_windows", "driver"):
            if k in var:
                vst[k] = var[k]
        vst["panel"] = dict(st["panel"], **var.get("panel", {}))
        if "bar_colours" in var:
            vst["bar_colours"] = var["bar_colours"]
        vpal = dict(st["palette"])
        vpal.update(specs.palette(**var.get("palette", {})))
        for k in var.get("palette", {}):
            vpal[k] = specs.palette(**{k: var["palette"][k]})[k]
        core.reset()
        VM, VP = materials(vpal)
        vb = Builder(L, VM)
        vb.body(vst)
        vb.closers(vst)
        vb.wells_and_pan(vst)
        if C:
            vb.cargo(C, vst)
        vb.cabin(vst)
        shell = set(vb.MESH)
        dress(vb, vst, var)
        own = [m for m in vb.MESH if m not in shell or any(m.startswith(p) for p in var.get("reshell", []))]
        vlib = components.Library(std, var["name"], VP, comp_root)
        vplaces = to_library(vb, vlib, own)
        vlib.write()
        replaced = {p[0] for p in vplaces}
        pl = [p for p in places if p[0] not in replaced] + vplaces
        cl = copy.deepcopy(base_closers)
        for c in cl:
            vc = next((x for x in vb.CLOSERS if x["id"] == c["id"]), None)
            if vc:
                for p in vc["parts"]:
                    if p not in c["parts"]:
                        c["parts"].append(p)
        mk = {m[0]: m for m in base_markers}
        for m in vb.MARKERS:
            mk[m[0]] = m
        blueprint(var["type"], var["name"], pl, cl, list(mk.values()))
        # the variant's look: the shell from the base, with its own palette, plus its tokens
        for mid in vb.MESH:
            if mid in shell or mid in replaced:
                continue
        root = core.empty(var["type"], (0, 0, 0))
        keep = {p[0] for p in pl}
        for mid, me in vb.MESH.items():
            if mid in keep and me.bm.faces:
                ob = me.obj(origin=Vector((0, 0, 0)), smooth=False, parent=root)
                ob.name = mid
        # (the base dressing the variant keeps: rebuild it in the variant's materials for the render only)
        rb = Builder(L, VM)
        rb.body(vst)
        rb.closers(vst)
        if C:
            rb.cargo(C, vst)
        dress(rb, vst)
        for mid, me in rb.MESH.items():
            if mid in keep and mid not in vb.MESH and me.bm.faces:
                ob = me.obj(origin=Vector((0, 0, 0)), smooth=False, parent=root)
                ob.name = mid + "_r"
        renders(var["type"], L)
        print("%s variant %s: %d own tokens" % (sid, var["type"], len(vplaces)))


def build_parts(vtype, registry):
    """A small unpowered or single-track vehicle from its token recipe (fleet/parts.py): no board; its tube frame is
    its structure and shows on purpose."""
    import types as _types
    from mathutils import Matrix
    from kit.core import Mesh
    import parts as P
    core.reset()
    pal = specs.palette(paint=P.COLOURS.get(vtype, (150, 152, 156)), paint2=(236, 234, 228))
    M, PAL = materials(pal)
    b = _types.SimpleNamespace(M=M, MESH={}, MODS={})
    X, R = Matrix.Translation, Matrix.Rotation
    core_pt = None
    lo, hi = [9, 9, 9], [-9, -9, -9]
    wheels_at, seat_at = [], None
    for tid, role, slot, side, prims in P.RECIPES[vtype]():
        for pr in prims:                                    # (its wheels and its seat: what the game drives it on and from)
            if pr[0] == "wheel":
                wheels_at.append([round(pr[1][0], 3), round(pr[1][2], 3), round(-pr[1][1], 3), round(pr[2], 3)])
            if role == "seat" and seat_at is None and pr[0] in ("seat", "box"):
                seat_at = [round(pr[1][0], 3), round(pr[1][2], 3), round(-pr[1][1], 3)]
        me = Mesh(tid, M)
        b.MESH[tid] = me
        b.MODS[tid] = dict(role=role, slot=slot, side=side, hp=150, mass_kg=3.0, breaks="detach", boxes=[])
        for pr in prims:
            k = pr[0]
            if k == "tube":
                me.pipe(pr[1], pr[2], pr[3], n=8)
            elif k == "box":
                me.box(pr[1], pr[2], pr[3])
                if core_pt is None or role == "frame_shown":
                    core_pt = core_pt or pr[1]
            elif k == "wheel":
                c, r, w, m = pr[1], pr[2], pr[3], pr[4]
                xf = X(c) @ R(math.pi / 2, 4, "Z")
                me.lathe([(-w / 2, r * 0.55), (-w / 2, r * 0.92), (-w * 0.4, r), (w * 0.4, r), (w / 2, r * 0.92), (w / 2, r * 0.55)], m, n=20, xf=xf)
                me.lathe([(-w * 0.3, 0.0001), (-w * 0.3, r * 0.55), (w * 0.3, r * 0.55), (w * 0.3, 0.0001)], "chrome", n=14, xf=xf)
            elif k == "disc":
                c, r, t, m = pr[1], pr[2], pr[3], pr[4]
                me.lathe([(-t / 2, 0.0001), (-t / 2, r), (t / 2, r), (t / 2, 0.0001)], m, n=20, xf=X(c) @ R(math.pi / 2, 4, "Z"))
            elif k == "lathe":
                prof, c, m, ax = pr[1], pr[2], pr[3], pr[4]
                rot = {"y": Matrix(), "x": R(math.pi / 2, 4, "Z"), "z": R(-math.pi / 2, 4, "X")}[ax]
                me.lathe(prof, m, n=16, xf=X(c) @ rot)
            elif k == "wire":                          # an open box of rods
                (cx, cy, cz), (hx, hy, hz), m = pr[1], pr[2], pr[3]
                cs = [(cx + sx * hx, cy + sy * hy, cz + sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
                for a_, b_ in ((0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)):
                    me.pipe([cs[a_], cs[b_]], 0.006, m, n=5)
                n = max(2, int(hy * 2 / 0.06))
                for i in range(n + 1):
                    y = cy - hy + 2 * hy * i / n
                    for sx in (-1, 1):
                        me.pipe([(cx + sx * hx, y, cz - hz), (cx + sx * hx, y, cz + hz)], 0.003, m, n=4)
                    me.pipe([(cx - hx, y, cz - hz), (cx + hx, y, cz - hz)], 0.003, m, n=4)
        for v in me.bm.verts:
            for i in range(3):
                lo[i], hi[i] = min(lo[i], v.co[i]), max(hi[i], v.co[i])
    core_pt = core_pt or ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)
    sid = "PX" + vtype.upper()[:6]
    joints = [[nm, 0.0 if nm in ("crown", "floor_C") else (0.002 if nm.endswith("_R") else -0.002), round(core_pt[2], 4)] for nm in LOFT.RING_NAMES]
    rings = [{"y": round(core_pt[1] + 0.004, 4), "joints": joints}, {"y": round(core_pt[1] - 0.004, 4), "joints": joints}]
    for r in rings:
        r["joints"] = [[j[0], j[1], j[2]] for j in r["joints"]]
    std = {"id": sid, "class": vtype, "about": "%s: a token recipe (remake/blender/fleet/parts.py), no board, its frame shown" % vtype, "board": "none",
           "outer_half_width": hi[0], "inner_half_width": hi[0], "deck": lo[2], "floor": lo[2], "skirt": lo[2], "sill": lo[2], "belt": lo[2],
           "window": [lo[2], hi[2]], "cant": hi[2], "crown": hi[2], "arch_top": 0.0, "door": {"head": hi[2], "apertures": {}}, "axles": [],
           "arch_half": 0.0, "arch_r": 0.0, "arch_zc": 0.0, "nose": hi[1], "tail": lo[1], "toe": hi[1], "header": hi[1], "front": {"kind": "none"},
           "rear": {"kind": "none"}, "stations": [], "ring": joints, "rings": rings, "end_inset": 0.0, "top_openings": [], "slots": {}, "frame_shown": True,
           "tubes": {"main_d": 0.006, "brace_d": 0.005, "material": "frame_tube", "exposed_inside": [], "exposed_outside": []},
           "bolted": ["sill_R", "sill_L", "floor_C"], "stringers": LOFT.RING_NAMES,
           "frame": {"yield_strain": 0.012, "plastic": 0.85, "dent_stiffness": 20000.0, "min_energy": 400.0, "max_dent": 0.15},
           "detach_count": 2, "detach_share": 0.3, "pair_min": 0.05,
           "tolerance": {"frame_shown": 0.3, "wheel": 0.3, "seat": 0.3, "equipment": 0.3, "side_bay": 0.3, "roof_bay": 0.3, "end_cap": 0.3, "lamp": 0.05, "trim": 0.3}}
    standards.write_json(std, os.path.join(OUT_ROOT, "standards"))
    style = "parts_" + vtype
    lib = components.Library(std, style, PAL, os.path.join(OUT_ROOT, "components"))
    places = to_library(b, lib, list(b.MESH))
    lib.write()
    fleet_dir = os.path.join(OUT_ROOT, "fleet")
    components.write_blueprint(os.path.join(fleet_dir, vtype + ".blueprint.json"), {
        "_about": "%s: a token recipe (remake/blender/fleet/parts.py)" % vtype, "type": vtype, "standard": sid, "class": vtype, "style": style,
        "kind": "prop", "board": "none", "frame_shown": True, "stations": [r["y"] * -1 for r in rings], "placements": places, "doors": [], "closers": [],
        "length_front": hi[1], "length_back": -lo[1], "platform": {"half_w": 0.0, "y": -1.0, "z": [0.0, 0.0]}, "cabin_points": [], "markers": []})
    registry[vtype] = {"blueprint": "res://remake/vehicles/fleet/%s.blueprint.json" % vtype, "standard": sid, "style": style, "board": "none",
                       "phys": vtype, "half_w": round(hi[0], 3), "height": round(hi[2], 3), "nose": round(hi[1], 3), "tail": round(lo[1], 3),
                       "floor": round(lo[2], 3), "driver": "C", "wheels": wheels_at, "seat": seat_at}
    if not wheels_at:                                     # (no wheels -- the EVA sled on its pads: it flies)
        registry[vtype]["air"] = True
    root = core.empty(vtype, (0, 0, 0))
    for mid, me in b.MESH.items():
        if me.bm.faces:
            ob = me.obj(origin=Vector((0, 0, 0)), smooth=False, parent=root)
            ob.name = mid
    sc, cam = core.render_setup()
    ln = max(hi[1] - lo[1], hi[2]) + 0.5
    core.render_persp(os.path.join(RENDER_DIR, vtype + "_34.png"), cam, (0, (hi[1] + lo[1]) / 2, hi[2] * 0.45),
                      (ln * 1.2, (hi[1] + lo[1]) / 2 + ln * 1.5, hi[2] + ln * 0.6), 900, 640, lens=40)
    print("PARTS %s: %d tokens" % (vtype, len(places)))


def waterline(H):
    """The hull's outline where it meets the water (z = 0), the right half bow to stern, in the Godot frame ([x, z]): the
    game masks the water inside it (a boat displaces it; none shows within its shell)."""
    out = []
    for y in H.ys:
        pts = H.half(y)
        for (xa, za), (xb, zb) in zip(pts[:5], pts[1:5]):
            if za <= 0.0 <= zb and zb > za:
                x = xa + (xb - xa) * (0.0 - za) / (zb - za)
                out.append([round(max(0.0, x - 0.01), 3), round(-y, 3)])
                break
    return out


def build_boat(vtype, registry):
    """A boat (fleet/hull.py): hull panels outside, a liner inside, the frames (ribs) between; the deck and its cockpit;
    the transom; a wheelhouse; the gear."""
    import types as _types
    from mathutils import Matrix
    from mathutils.geometry import tessellate_polygon
    from kit.core import Mesh
    import hull as HL
    S = dict(HL.BOATS[vtype])
    H = HL.Hull(S)
    c1, c2 = S["colours"]
    core.reset()
    M, PAL = materials(specs.palette(paint=c1, paint2=c2))
    b = _types.SimpleNamespace(M=M, MESH={}, MODS={})
    X, R = Matrix.Translation, Matrix.Rotation

    def mod(mid, role, slot, side="C", hp=600, mass=20):
        if mid not in b.MESH:
            b.MESH[mid] = Mesh(mid, M)
            b.MODS[mid] = dict(role=role, slot=slot, side=side, hp=hp, mass_kg=mass, breaks="detach", boxes=[])
        return b.MESH[mid]
    ys = H.ys
    ck = S.get("cockpit")
    wh = S.get("wheelhouse")
    cuts = sorted({ys[0], ys[-1]} | ({ck[0], ck[1]} if ck else set()) | ({wh[0], wh[1]} if wh else set()), reverse=True)
    ys = sorted(set(ys) | set(cuts), reverse=True)

    def zone(y):
        for i in range(len(cuts) - 1):
            if cuts[i + 1] - 1e-6 <= y <= cuts[i] + 1e-6:
                return i
        return 0
    OUT = {y: H.half(y) for y in ys}
    INN = {y: H.inner(y) for y in ys}
    bands = (("bottom", 0, 2, "side_bay", "paint2"), ("topside", 2, 4, "side_bay", "paint"), ("sidedeck", 4, 5, "roof_bay", "paint"), ("deck", 5, 7, "roof_bay", "paint"))
    for a, bb in zip(ys, ys[1:]):
        zi = zone((a + bb) / 2)
        in_ck = ck and ck[1] - 1e-6 <= bb and a <= ck[0] + 1e-6
        for name, k0, k1, role, mat in bands:
            for sx, sd in ((1, "R"), (-1, "L")):
                if name == "deck" and in_ck:
                    continue
                me = mod("%s_%d_%s" % (name, zi, sd), role, "%s_%d" % (name, zi), sd, hp=900, mass=40)
                mi = mod("liner_%s_%d_%s" % (name, zi, sd), "lining_bay", "%s_%d" % (name, zi), sd, hp=300, mass=10)
                for k in range(k0, k1):
                    for src, mm, flip in ((OUT, me, False), (INN, mi, True)):
                        pa, pb = src[a], src[bb]
                        q = [(sx * pa[k][0], a, pa[k][1]), (sx * pb[k][0], bb, pb[k][1]), (sx * pb[k + 1][0], bb, pb[k + 1][1]), (sx * pa[k + 1][0], a, pa[k + 1][1])]
                        if (sx < 0) != flip:
                            q.reverse()
                        mm.face(q, mat if not flip else "lining")
    if ck:                                                   # the cockpit's coaming: the deck's edge down to the liner's
        me = mod("coaming", "reveal", "cockpit", hp=600, mass=15)
        rows = [y for y in ys if ck[1] - 1e-6 <= y <= ck[0] + 1e-6]
        for sx in (1, -1):
            for a, bb in zip(rows, rows[1:]):
                q = [(sx * OUT[a][5][0], a, OUT[a][5][1]), (sx * OUT[bb][5][0], bb, OUT[bb][5][1]), (sx * INN[bb][5][0], bb, INN[bb][5][1]), (sx * INN[a][5][0], a, INN[a][5][1])]
                me.face(q if sx > 0 else list(reversed(q)), "paint")
        for y in (ck[0], ck[1]):
            o, i = OUT[y], INN[y]
            ring_o = [(o[k][0], y, o[k][1]) for k in (5, 6, 7)] + [(-o[k][0], y, o[k][1]) for k in (6, 5)]
            ring_i = [(i[k][0], y, i[k][1]) for k in (5, 6, 7)] + [(-i[k][0], y, i[k][1]) for k in (6, 5)]
            for k in range(4):
                me.face([ring_o[k], ring_o[k + 1], ring_i[k + 1], ring_i[k]], "paint")
    # the transom (and a square bow's face), outer and inner, and the rim between
    for y, sg, nm in ((ys[-1], -1, "transom"), (ys[0], 1, "stem")):
        me = mod(nm, "end_cap", nm, hp=900, mass=30)
        lo, li = H.loop(y), [(x, z) for x, z in INN[y]] + [(-x, z) for x, z in reversed(INN[y][1:-1])]
        for loop, m in ((lo, "paint"), (li, "lining")):
            flat = [(x, y, z) for x, z in loop]
            tris = tessellate_polygon([[Vector((x, z, 0.0)) for x, z in loop]])
            for t in tris:
                q = [flat[t[0]], flat[t[1]], flat[t[2]]]
                n = (Vector(q[1]) - Vector(q[0])).cross(Vector(q[2]) - Vector(q[0]))
                if n.y * sg < 0:
                    q = [q[0], q[2], q[1]]
                me.face(q, m)
    # the rubbing strake along the sheer
    me = mod("strake", "trim", "strake", hp=300, mass=8)
    for sx in (1, -1):
        me.pipe([Vector((sx * (OUT[y][4][0] + 0.02), y, OUT[y][4][1] - 0.03)) for y in ys], 0.035, "black", n=6)
    # the wheelhouse: walls, windows all round, a roof
    if wh:
        # (2026-10-05: hollow, the helm inside it looking out -- it was a solid block round the helmsman)
        y0, y1, hw, hh = wh
        z0 = H.sheer_z((y0 + y1) / 2) + 0.05
        sill = z0 + min(0.95, hh * 0.40)                     # the window band: the helmsman's eye (z0 + 1.2) in it;
        head = max(sill + 0.10, z0 + hh - 0.12)              # a sailboat's low coachroof: a strip of ports
        t = 0.05
        me = mod("wheelhouse", "cab", "wheelhouse", hp=900, mass=200)
        me.box((0, (y0 + y1) / 2, z0 - 0.02), (hw, (y0 - y1) / 2, 0.03), "wood")                    # its sole
        me.box((0, (y0 + y1) / 2, z0 + hh + 0.04), (hw + 0.10, (y0 - y1) / 2 + 0.10, 0.04), "paint2")  # its roof
        for sx in (1, -1):                                   # the sides: below the sill, over the head
            me.box((sx * (hw - t / 2), (y0 + y1) / 2, (z0 + sill) / 2), (t / 2, (y0 - y1) / 2, (sill - z0) / 2), "paint")
            me.box((sx * (hw - t / 2), (y0 + y1) / 2, (head + z0 + hh) / 2), (t / 2, (y0 - y1) / 2, (z0 + hh - head) / 2), "paint")
            for y in (y0 - 0.04, y1 + 0.04):                 # corner posts
                me.box((sx * (hw - t / 2), y, (sill + head) / 2), (t / 2, 0.04, (head - sill) / 2), "paint")
        me.box((0, y0 - t / 2, (z0 + sill) / 2), (hw, t / 2, (sill - z0) / 2), "paint")              # the front, below its windows
        me.box((0, y0 - t / 2, (head + z0 + hh) / 2), (hw, t / 2, (z0 + hh - head) / 2), "paint")
        for x in (-hw / 3, hw / 3):                          # the front's two mullions
            me.box((x, y0 - t / 2, (sill + head) / 2), (0.03, t / 2, (head - sill) / 2), "paint")
        for sx in (1, -1):                                   # the back: a doorway in the middle
            me.box((sx * (hw + 0.45) / 2, y1 + t / 2, z0 + hh / 2), ((hw - 0.45) / 2, t / 2, hh / 2), "paint")
        me.box((0, y1 + t / 2, z0 + hh - 0.15), (0.45, t / 2, 0.15), "paint")
        gl = mod("wheelhouse_glass", "glazing", "wheelhouse", hp=60, mass=20)
        gl.box((0, y0 - t / 2, (sill + head) / 2), (hw - 0.02, 0.006, (head - sill) / 2), "glass")
        for sx in (1, -1):
            gl.box((sx * (hw - t / 2), (y0 + y1) / 2, (sill + head) / 2), (0.006, (y0 - y1) / 2 - 0.08, (head - sill) / 2), "glass")
        me.box((0, y0 - 0.45, z0 + 0.95), (0.40, 0.18, 0.04), "dash")                              # the helm console
        me.lathe([(-0.02, 0.18), (0.02, 0.18)], "black", n=16, xf=X((0, y0 - 0.62, z0 + 1.05)) @ R(math.pi / 2.6, 4, "X"))
    # the gear
    for gname in S.get("gear", []):
        me = mod(gname, "equipment", gname, hp=300, mass=40)
        mid_y = (ys[0] + ys[-1]) / 2
        sz = H.sheer_z(mid_y)
        if gname == "oars":
            for sx in (1, -1):
                me.pipe([Vector((sx * 0.2, 0.2, sz)), Vector((sx * 1.4, -0.4, sz - 0.2))], 0.02, "wood", n=6)
        elif gname == "paddles":
            me.pipe([Vector((-0.9, 0.2, sz + 0.1)), Vector((0.9, 0.2, sz + 0.1))], 0.018, "wood", n=6)
            for sx in (1, -1):
                me.box((sx * 0.95, 0.2, sz + 0.1), (0.12, 0.01, 0.06), "wood")
        elif gname == "thwarts":
            tys = [0.5, -0.6] if H.L < 4 else [1.0, 0.0, -1.0]
            if S.get("helm") == "tiller":                    # (the helmsman's: the aft thwart, by the tiller)
                tys = [y for y in tys if y > H.stern + 1.2] + [H.stern + 0.75]
            for y in tys:
                me.box((0, y, H.sheer_z(y) - 0.12), (H.half_beam(y) - 0.06, 0.12, 0.02), "wood")
        elif gname == "outboard":
            me.box((0, ys[-1] - 0.20, sz + 0.05), (0.15, 0.18, 0.25), "black")
            me.box((0, ys[-1] - 0.24, sz - 0.55), (0.04, 0.06, 0.40), "black")
        elif gname == "tiller_outboard":                     # an outboard on the transom, its tiller arm forward to the helm
            yt = ys[-1]
            zt = H.sheer_z(yt)
            me.box((0, yt - 0.10, zt + 0.02), (0.05, 0.10, 0.06), "black")                     # (the transom clamp)
            me.lathe([(0.0, 0.16), (0.12, 0.18), (0.40, 0.17), (0.55, 0.0001)], "black", n=12,
                     xf=X((0, yt - 0.30, zt + 0.22)) @ R(math.pi, 4, "Z"))                  # the powerhead's cowl
            me.box((0, yt - 0.26, zt - 0.30), (0.04, 0.07, 0.38), "black")                      # the leg
            me.box((0, yt - 0.26, zt - 0.70), (0.05, 0.12, 0.06), "black")                      # the cavitation plate
            arm = 0.55 + min(0.25, H.L * 0.03)                                                 # (an extension on a longer hull)
            me.pipe([Vector((0, yt - 0.12, zt + 0.16)), Vector((0.08, yt + arm, zt + 0.12))], 0.022, "black", n=8)
            me.pipe([Vector((0.08, yt + arm, zt + 0.12)), Vector((0.10, yt + arm + 0.14, zt + 0.12))], 0.03, "rubber", n=8)
        elif gname == "tiller_rudder":                       # a sailboat's transom-hung rudder and its long wooden tiller
            yt = ys[-1]
            zt = H.sheer_z(yt)
            me.box((0, yt - 0.06, zt - 0.6), (0.03, 0.22, 0.75), "paint2")
            me.pipe([Vector((0, yt + 0.05, zt + 0.10)), Vector((0.05, yt + 1.25, zt + 0.25))], 0.03, "wood", n=8)
        elif gname == "tiller_lever":                        # a pedal boat's steering lever, between the two seats
            me.pipe([Vector((0, 0.0, sz - 0.20)), Vector((0, 0.05, sz + 0.25))], 0.018, "chrome", n=8)
            me.lathe([(0.0, 0.03), (0.08, 0.03)], "rubber", n=10, xf=X((0, 0.05, sz + 0.25)) @ R(-math.pi / 2, 4, "X"))
        elif gname == "console":
            me.box((0, 0.1, sz - 0.05), (0.30, 0.25, 0.45), "paint2")
            me.box((0, 0.2, sz + 0.45), (0.28, 0.02, 0.15), "glass_dark")
        elif gname == "paddlewheel":
            me.lathe([(-0.25, 0.30), (0.25, 0.30)], "paint2", n=12, xf=X((0, ys[-1] + 0.2, sz - 0.05)) @ R(math.pi / 2, 4, "Z"))
        elif gname == "canopy_boat" or gname == "bimini":
            yy0, yy1 = (0.4, -0.8) if gname == "canopy_boat" else (1.0, -1.5)
            me.box((0, (yy0 + yy1) / 2, sz + 1.3), (H.beam - 0.1, (yy0 - yy1) / 2, 0.02), "paint2")
            for sx in (1, -1):
                for yy in (yy0, yy1):
                    me.pipe([Vector((sx * (H.beam - 0.12), yy, sz)), Vector((sx * (H.beam - 0.12), yy, sz + 1.3))], 0.015, "chrome", n=6)
        elif gname == "saddle_boat":
            me.box((0, -0.4, sz + 0.20), (0.18, 0.55, 0.10), "seat")
        elif gname == "handlebar_boat":
            me.pipe([Vector((-0.30, 0.42, sz + 0.30)), Vector((0.30, 0.42, sz + 0.30))], 0.016, "black", n=6)   # (below the rider's
            me.box((0, 0.58, sz + 0.12), (0.12, 0.12, 0.06), "paint2")                                     #  eye line)
        elif gname == "mast_sails":
            me.pipe([Vector((0, 1.5, sz)), Vector((0, 1.5, sz + 12.0))], 0.07, "chrome", n=10)
            me.pipe([Vector((0, 1.5, sz + 1.6)), Vector((0, -2.8, sz + 1.6))], 0.05, "chrome", n=8)
            me.face([(0, 1.45, sz + 1.7), (0, -2.75, sz + 1.7), (0, 1.45, sz + 11.5)], "livery1")
            me.face([(0, 1.6, sz + 2.0), (0, 1.6, sz + 11.0), (0, ys[0] - 0.2, sz + 1.9)], "livery1")   # (a high-cut jib: the
                                                                                                          #  helm sees under it)
        elif gname == "pontoons":
            for sx in (1, -1):
                me.lathe([(-H.L / 2 + 0.2, 0.0001), (-H.L / 2 + 0.6, 0.30), (H.L / 2 - 0.8, 0.30), (H.L / 2 - 0.1, 0.0001)], "chrome", n=16,
                         xf=X((sx * (H.beam - 0.35), 0, -0.05)))
        elif gname == "fence":                               # (low enough that the helm sees over it)
            for sx in (1, -1):
                me.box((sx * (H.beam - 0.05), 0, sz + 0.33), (0.02, H.L / 2 - 0.4, 0.28), "paint2")
            me.box((0, ys[0] - 0.45, sz + 0.33), (H.beam - 0.05, 0.02, 0.28), "paint2")
        elif gname == "rail":
            for sx in (1, -1):
                me.pipe([Vector((sx * (H.half_beam(y) - 0.08), y, H.sheer_z(y) + 0.75)) for y in ys[1:-1]], 0.018, "chrome", n=6)
        elif gname == "lightbar_boat":
            me.box((0, wh[1] + 0.5, H.sheer_z(0) + wh[3] + 0.18), (0.6, 0.12, 0.05), "lamp_red")
        elif gname == "pot_hauler":
            me.pipe([Vector((H.beam - 0.25, -0.8, sz)), Vector((H.beam - 0.2, -0.8, sz + 1.6)), Vector((H.beam + 0.1, -1.1, sz + 1.8))], 0.05, "chrome", n=8)
            me.lathe([(-0.1, 0.18), (0.1, 0.18)], "black", n=12, xf=X((H.beam - 0.3, -0.8, sz + 0.5)))
        elif gname == "traps":
            for k in range(6):
                me.box(((k % 3 - 1) * 0.65, -3.0 - (k // 3) * 0.75, sz - 0.35), (0.28, 0.32, 0.20), "livery2")
        elif gname == "tug_fenders":
            me.lathe([(0.0, 0.0001), (0.0, 0.45), (2.0, 0.45), (2.0, 0.0001)], "rubber", n=12, xf=X((0, ys[0] - 0.1, H.sheer_z(ys[0]) - 0.6)) @ R(math.pi / 2, 4, "Z") @ X((-1.0, 0, 0)))
            for sx in (1, -1):
                me.pipe([Vector((sx * (H.half_beam(y) + 0.10), y, H.sheer_z(y) - 0.45)) for y in ys[1:-1]], 0.22, "rubber", n=8)
        elif gname == "towing_bitt":
            me.box((0, ys[-1] + 2.0, sz + 0.35), (0.30, 0.30, 0.35), "black")
        elif gname == "gallows":
            for sx in (1, -1):
                me.pipe([Vector((sx * (H.beam - 0.3), ys[-1] + 1.2, sz)), Vector((sx * (H.beam - 0.3), ys[-1] + 1.2, sz + 4.0)),
                         Vector((sx * (H.beam - 1.2), ys[-1] + 1.2, sz + 4.4))], 0.12, "paint2", n=8)
        elif gname == "net_drum":
            me.lathe([(-1.6, 0.6), (1.6, 0.6)], "livery2", n=14, xf=X((0, ys[-1] + 3.5, sz + 1.0)) @ R(math.pi / 2, 4, "Z"))
        elif gname == "ferry_ramps":
            for y, sg in ((ys[0], 1), (ys[-1], -1)):
                me.box((0, y + sg * 0.8, H.sheer_z(y) - 0.2), (3.5, 0.8, 0.08), "black")
    rings = H.rings()
    sid = "BT" + vtype.upper()[:6]
    std = {"id": sid, "class": vtype, "about": "%s: a hull loft (remake/blender/fleet/hull.py)" % vtype, "board": "none", "boat": True,
           "outer_half_width": H.beam, "inner_half_width": H.beam - H.t, "deck": 0.0, "floor": -H.draft, "skirt": -H.draft, "sill": 0.0, "belt": 0.0,
           "window": [0.0, H.free], "cant": H.free, "crown": H.free, "arch_top": 0.0, "door": {"head": H.free, "apertures": {}}, "axles": [],
           "arch_half": 0.0, "arch_r": 0.0, "arch_zc": 0.0, "nose": H.bow, "tail": H.stern, "toe": H.bow, "header": H.bow, "front": {"kind": "none"},
           "rear": {"kind": "none"}, "stations": ys, "ring": rings[len(rings) // 2]["joints"], "rings": rings, "end_inset": 0.0,
           "top_openings": [[ck[1], ck[0], "cockpit"]] if ck else [], "slots": {},
           "tubes": {"main_d": 0.022, "brace_d": 0.018, "material": "frame_tube", "exposed_inside": [], "exposed_outside": []},
           "bolted": ["floor_C"], "stringers": LOFT.RING_NAMES,
           "frame": {"yield_strain": 0.012, "plastic": 0.85, "dent_stiffness": 80000.0, "min_energy": 2500.0, "max_dent": 0.3},
           "detach_count": 3, "detach_share": 0.3, "pair_min": 0.25,
           "tolerance": {"side_bay": 0.16, "roof_bay": 0.10, "lining_bay": 0.10, "end_cap": 0.16, "reveal": 0.10, "trim": 0.2, "equipment": 0.25, "cab": 0.15, "glazing": 0.012}}
    standards.write_json(std, os.path.join(OUT_ROOT, "standards"))
    style = "hull_" + vtype
    lib = components.Library(std, style, PAL, os.path.join(OUT_ROOT, "components"))
    places = to_library(b, lib, list(b.MESH))
    lib.write()
    components.write_blueprint(os.path.join(OUT_ROOT, "fleet", vtype + ".blueprint.json"), {
        "_about": "%s: a boat (remake/blender/fleet/hull.py)" % vtype, "type": vtype, "standard": sid, "class": vtype, "style": style, "kind": "boat",
        "board": "none", "stations": [-r["y"] for r in rings], "placements": places, "doors": [], "closers": [],
        "length_front": H.bow, "length_back": -H.stern, "platform": {"half_w": 0.0, "y": -9.0, "z": [0.0, 0.0]}, "cabin_points": [], "markers": [],
        "decals": decals_out(DC.hull(H, vtype))})
    registry[vtype] = {"blueprint": "res://remake/vehicles/fleet/%s.blueprint.json" % vtype, "standard": sid, "style": style, "board": "none",
                       "phys": vtype, "half_w": H.beam, "height": H.free + (wh[3] if wh else 0.3), "nose": H.bow, "tail": H.stern, "floor": -H.draft,
                       "driver": "C", "boat": True, "ground": round(-H.draft, 3),
                       "hull": {"sheer": round(H.free, 3), "draft": H.draft, "t": round(H.t, 3), "wheelhouse": list(wh) if wh else None,
                                "cockpit": list(ck) if ck else None, "waterline": waterline(H)},
                       # (the helm, Godot frame: a tiller's helmsman on the aft thwart, to port of the handle; a paddler in
                       #  the stern seat; a pedaller at the lever; else at the front of the wheelhouse, or the cockpit's aft end)
                       "seat": ([-round(H.beam * 0.62, 3), round(H.sheer_z(H.stern + 1.8) + 0.32, 3), round(-(H.stern + 1.8), 3)]
                                if vtype == "sailboat" else           # (a sailboat's helmsman sits up on the cockpit coaming,
                                                                      #  outboard: he sees over the coachroof)
                                [-0.28, round(H.sheer_z(H.stern + 0.6) - 0.22, 3), round(-(H.stern + 0.75), 3)]
                                if S.get("helm") == "tiller" else
                                [0.0, round(H.sheer_z(H.stern + 0.7) - 0.25, 3), round(-(H.stern + 0.7), 3)] if S.get("helm") == "paddle" else
                                [-0.35, round(H.sheer_z(0) - 0.15, 3), 0.0] if S.get("helm") == "lever" else
                                [0.0, round(H.sheer_z(0) + 0.5, 3), round(-(wh[0] - 0.6), 3)] if wh else
                                [0.0, round(H.sheer_z(0) + (0.15 if "fence" in S.get("gear", []) else -0.25), 3),
                                 round(-((ck[1] + 0.6) if ck else 0.0), 3)])}
    root = core.empty(vtype, (0, 0, 0))
    for mid, me in b.MESH.items():
        if me.bm.faces:
            ob = me.obj(origin=Vector((0, 0, 0)), smooth=False, parent=root)
            ob.name = mid
    sc, cam = core.render_setup()
    ln = H.L
    core.render_persp(os.path.join(RENDER_DIR, vtype + "_34.png"), cam, (0, 0, H.free * 0.5), (ln * 0.75, ln * 0.95, ln * 0.45 + 2), 1000, 680, lens=40)
    print("BOAT %s: %d tokens, %d frames" % (vtype, len(places), len(rings)))


def save_registry(reg_path, registry):
    os.makedirs(os.path.dirname(reg_path), exist_ok=True)
    with open(reg_path, "w") as f:
        json.dump({"_about": "Fleet bodies: road vehicle type -> its blueprint, board and package (remake/blender/fleet/build.py)",
                   "types": registry}, f, indent=1)


def main():
    os.makedirs(RENDER_DIR, exist_ok=True)
    reg_path = os.path.join(OUT_ROOT, "fleet", "fleet_bodies.json")
    registry = {}
    if os.path.exists(reg_path):
        registry = json.load(open(reg_path)).get("types", {})
    import parts as P
    for sid in specs.CLASSES:
        if ONLY and sid not in ONLY:
            continue
        build_class(sid, registry)
        save_registry(reg_path, registry)                  # (after each: a later failure loses nothing)
    for vt in P.RECIPES:
        if ONLY and vt not in ONLY and "PARTS" not in ONLY:
            continue
        build_parts(vt, registry)
        save_registry(reg_path, registry)                  # (after each: a later failure loses nothing)
    import hull as HL
    for vt in HL.BOATS:
        if ONLY and vt not in ONLY and "BOATS" not in ONLY:
            continue
        build_boat(vt, registry)
        save_registry(reg_path, registry)                  # (after each: a later failure loses nothing)
    os.makedirs(os.path.dirname(reg_path), exist_ok=True)
    with open(reg_path, "w") as f:
        json.dump({"_about": "Fleet bodies: road vehicle type -> its blueprint, board and package (remake/blender/fleet/build.py)",
                   "types": registry}, f, indent=1)


main()
