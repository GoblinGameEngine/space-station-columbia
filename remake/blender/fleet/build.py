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
            e["slide"] = [c["slide"][0], 0.0, -c["slide"][1]]            # (Godot: x, y, z = -Blender y)
        else:
            p0, p1 = Vector(c["hinge"][0]), Vector(c["hinge"][1])
            e["hinge"] = g(p0)
            e["axis"] = [round(v, 5) for v in components.g((p1 - p0).normalized())]
            e["open_deg"] = c["open_deg"]
        out.append(e)
        if c["kind"] in ("door", "slide") and "y0" in c:
            doors.append({"id": c["id"], "side": c["side"], "z": round(-(c["y0"] + c["y1"]) / 2, 4), "width": round(c["y0"] - c["y1"], 4)})
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
    ln = L.nose - L.tail
    d = max(ln, 4.0)
    core.render_persp(pre + "_34.png", cam, (0, 0.1, 1.0), (d * 1.05, d * 1.35, 2.7), 1100, 720, lens=40)
    core.render_persp(pre + "_34rear.png", cam, (0, -0.3, 1.0), (-d * 1.0, -d * 1.4, 2.5), 1100, 720, lens=40)
    core.render_ortho(pre + "_side.png", cam, "side", (0, (L.nose + L.tail) / 2, L.crown / 2 + 0.1), ln + 0.8, 1100, 560)


def build_class(sid, registry):
    spec = specs.CLASSES[sid]
    st = specs.STYLES[sid]
    L = LOFT.Loft(spec)
    std = L.standard()
    core.reset()
    M, PAL = materials(st["palette"])
    b = Builder(L, M)
    holes = b.body(st)
    b.closers(st)
    b.wells_and_pan(st)
    b.cabin(st)
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
              "length_front": L.nose, "length_back": -L.tail,
              "platform": {"half_w": round(L.mount_x + 0.02, 3), "y": 0.49, "z": [-L.board["length_m"] / 2, L.board["length_m"] / 2]},
              "cabin_points": b.cabin_points(),
              "markers": [[nm, g(loc), round(rot, 4)] for nm, loc, rot in mk]}
        path = os.path.join(fleet_dir, vtype + ".blueprint.json")
        components.write_blueprint(path, bp)
        registry[vtype] = {"blueprint": "res://remake/vehicles/fleet/%s.blueprint.json" % vtype, "standard": sid, "style": style,
                           "board": spec["board"], "phys": vtype, "half_w": L.half_w, "height": L.crown, "nose": L.nose, "tail": L.tail,
                           "floor": L.floor, "driver": spec.get("driver", "L")}
        return bp

    blueprint(st["type"], st["name"], places, base_closers, base_markers)
    root = core.empty(st["type"], (0, 0, 0))
    for mid, me in b.MESH.items():
        if me.bm.faces:
            ob = me.obj(origin=Vector((0, 0, 0)), smooth=False, parent=root)
            ob.name = mid
    renders(st["type"], L)
    # ---- the variants: their own tokens and palette on the base components
    for var in specs.VARIANTS.get(sid, []):
        vst = dict(st)
        vst.update(var.get("rebuild", {}))
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
        vb.cabin(vst)
        shell = set(vb.MESH)
        dress(vb, vst, var)
        own = [m for m in vb.MESH if m not in shell]
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
        dress(rb, vst)
        for mid, me in rb.MESH.items():
            if mid in keep and mid not in vb.MESH and me.bm.faces:
                ob = me.obj(origin=Vector((0, 0, 0)), smooth=False, parent=root)
                ob.name = mid + "_r"
        renders(var["type"], L)
        print("%s variant %s: %d own tokens" % (sid, var["type"], len(vplaces)))


def main():
    os.makedirs(RENDER_DIR, exist_ok=True)
    reg_path = os.path.join(OUT_ROOT, "fleet", "fleet_bodies.json")
    registry = {}
    if os.path.exists(reg_path):
        registry = json.load(open(reg_path)).get("types", {})
    for sid in specs.CLASSES:
        if ONLY and sid not in ONLY:
            continue
        build_class(sid, registry)
    os.makedirs(os.path.dirname(reg_path), exist_ok=True)
    with open(reg_path, "w") as f:
        json.dump({"_about": "Fleet bodies: road vehicle type -> its blueprint, board and package (remake/blender/fleet/build.py)",
                   "types": registry}, f, indent=1)


main()
