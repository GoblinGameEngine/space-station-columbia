"""
gblib.py -- Blender-side building library for the clean-sheet remake.

Shared *code* only: each building's geometry, dimensions and materials come from
its own spec/real-world example (remake/research/, remake/reference/). Imported by
the per-building scripts in remake/blender/buildings/ and run headless:

    flatpak run org.blender.Blender -b --factory-startup --python <abs path to building script>

Conventions (what the Godot side -- remake/godot scripts -- relies on):
  * Blender Z-up, metres, origin at the structure's reference point on grade.
    glTF export converts to Godot's Y-up.
  * Object name suffix "-col"      -> Godot builds trimesh static collision, keeps mesh.
    Object name suffix "-colonly"  -> collision only (stair ramps, invisible blockers).
  * "door_<id>__<sign>"            -> a hinged leaf; object origin ON the hinge axis at the
    bottom of the leaf, leaf extends along local +X.  <sign> is "p" or "n": the sign of
    rotation about the up axis that swings it open the correct way (from the plan's swing).
    A leading "L" in id (e.g. door_front__p__locked) marks a locked door.
  * "light_<kind>"                 -> an empty where Godot places a light.
  * Textures come from remake/textures/<set>/<name>_{albedo,normal,rough}.png.
"""

import hashlib
import json
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

FT = 0.3048
# foundations, porch skirts, steps and piers run this far below grade (z = 0) so a building set
# on sloping or elevated terrain never shows a gap under it: the low side just buries less
FOUND_DEPTH = 4.0
IN = 0.0254


def ft(feet=0.0, inches=0.0):
    return feet * FT + inches * IN


# ------------------------------------------------------------------ scene / materials
CURRENT = None          # the Building being built (build_record's furniture recorder logs into it)
ROOMS_RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rooms", "raw")


def _jsonable(v):
    if isinstance(v, (str, int, bool)) or v is None:
        return v
    if isinstance(v, float):
        return round(v, 3)
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items() if not callable(x)}
    if hasattr(v, "to_tuple"):
        return [round(float(x), 3) for x in v]
    return None


class Building:
    def __init__(self, name, texdir):
        global CURRENT
        bpy.ops.wm.read_factory_settings(use_empty=True)
        CURRENT = self
        self.plans = []                  # the gbhouse specs built into it (rooms, doors, stairs, blocks)
        self.houses = []                 # (and their gbhouse.House builders: the audit asks them about walls and roofs)
        self.audit = None
        self.furniture = []              # every furnishing call: {item, room, floor, pos, yaw, parent}
        self._room = None                # (the room being furnished, while gbhouse furnishes it)
        self._furn_stack = []
        self.name = name
        self.texdir = texdir
        self.sink_ground = True          # see Part.sink_ground_contacts (off for site/terrain pieces)
        self.mat_defs = {}               # blender material name -> definition (the .mats.json sidecar)
        self.mats = {}
        self.tile = {}          # material -> metres per texture repeat (for UV projection)
        self.objs = {}
        self.massing = []                # solid blocks for the distance versions (gbhouse registers them)
        self.lods = True                 # export <id>.lod1/2/3.glb beside the glb (gblod)
        self.root = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(self.root)

    # -- materials --------------------------------------------------------
    def mat(self, key, tex=None, color=(0.8, 0.8, 0.8), rough=0.6, metal=0.0, tile_m=1.0,
            alpha=None, emission=None, tint=None):
        """tex: texture name in this building's texture set; tint multiplies a texture (a neutral
        library texture painted any colour); color is used when there is no texture."""
        if key in self.mats:
            return key
        # materials are shared across every building: the glb carries only a content-derived name,
        # and Godot builds the material once from the definition in <building>.mats.json and the
        # shared texture library (godot_project/remake/textures/<set>/<tex>_*.webp)
        tex_rel = None
        if tex:
            tex_rel = os.path.basename(os.path.normpath(self.texdir)) + "/" + tex
        d = {"tex": tex_rel, "tint": [round(c, 4) for c in tint] if tint else None,
             "color": None if tex else [round(c, 4) for c in color], "rough": round(rough, 3), "metal": round(metal, 3),
             "alpha": alpha, "emission": [round(c, 4) for c in emission] if emission else None}
        mname = "M_" + hashlib.sha1(json.dumps(d, sort_keys=True).encode()).hexdigest()[:12]
        self.mat_defs[mname] = d
        m = bpy.data.materials.new(mname)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        if tex:
            base = os.path.join(self.texdir, tex)
            img = nt.nodes.new("ShaderNodeTexImage")
            img.image = bpy.data.images.load(base + "_albedo.png")
            if tint:
                mul = nt.nodes.new("ShaderNodeMix")
                mul.data_type = "RGBA"
                mul.blend_type = "MULTIPLY"
                mul.inputs["Factor"].default_value = 1.0
                nt.links.new(img.outputs["Color"], mul.inputs[6])
                mul.inputs[7].default_value = (*[srgb_to_linear(c) for c in tint], 1.0)     # tint is sRGB
                nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
            else:
                nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
            rimg = nt.nodes.new("ShaderNodeTexImage")
            rimg.image = bpy.data.images.load(base + "_rough.png")
            rimg.image.colorspace_settings.name = "Non-Color"
            nt.links.new(rimg.outputs["Color"], bsdf.inputs["Roughness"])
            nimg = nt.nodes.new("ShaderNodeTexImage")
            nimg.image = bpy.data.images.load(base + "_normal.png")
            nimg.image.colorspace_settings.name = "Non-Color"
            nmap = nt.nodes.new("ShaderNodeNormalMap")
            nt.links.new(nimg.outputs["Color"], nmap.inputs["Color"])
            nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
        if alpha is not None:
            bsdf.inputs["Alpha"].default_value = alpha
            m.surface_render_method = "BLENDED"
        if emission:
            bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 2.0
        self.mats[key] = m
        self.tile[key] = tile_m
        return key

    # -- objects ----------------------------------------------------------
    def part(self, name, parent=None):
        """Get/create an accumulating mesh object (bmesh until finish())."""
        if name not in self.objs:
            self.objs[name] = Part(self, name, parent)
        return self.objs[name]

    def empty(self, name, loc, parent=None):
        e = bpy.data.objects.new(name, None)
        e.location = loc
        e.parent = parent or self.root
        bpy.context.scene.collection.objects.link(e)
        return e

    def finish(self, out_glb):
        for p in list(self.objs.values()):
            p.sink_ground_contacts()
            p.to_object()
        if self.houses:
            import gbaudit
            self.audit = gbaudit.audit(self)
            a = self.audit or {}
            print("AUDIT %s %s leaks=%d clips=%d doors=%d" % (os.path.splitext(os.path.basename(out_glb))[0], "ok" if a.get("ok") else "FAIL",
                                                         len(a.get("leaks", [])), len(a.get("clips", [])), len(a.get("doors", []))))
        if self.lods:
            import gblod
            self.lod_tris = gblod.export_lods(self, out_glb)
            print(f"LODS {os.path.basename(out_glb)} {self.lod_tris}")
        self.merge_meshes()
        os.makedirs(os.path.dirname(out_glb), exist_ok=True)
        bpy.ops.object.select_all(action="SELECT")
        # no images in the glb: textures come from the shared library (see mat())
        bpy.ops.export_scene.gltf(filepath=out_glb, export_format="GLB", export_yup=True,
                                  export_apply=True, export_extras=True, export_image_format="NONE")
        used = {m.name for ob in bpy.data.objects if ob.type == "MESH" for m in ob.data.materials if m}
        with open(os.path.splitext(out_glb)[0] + ".mats.json", "w") as f:
            json.dump({k: v for k, v in sorted(self.mat_defs.items()) if k in used}, f, indent=0)
        # the working .blend stays OUT of godot_project: Godot 4.3 tries to import .blend files
        # through an external Blender and stalls the whole import when it can't find one
        blend = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out",
                             os.path.splitext(os.path.basename(out_glb))[0] + ".blend")
        os.makedirs(os.path.dirname(blend), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=blend)
        self.write_rooms_raw(os.path.splitext(os.path.basename(out_glb))[0])
        print(f"EXPORTED {out_glb}")

    def write_rooms_raw(self, rid):
        """The plan as built (remake/rooms/raw/<id>.json): rooms, doors, stairs, storeys and the furniture placed in
        each room, in the plan frame (metres; x east, y north, z up; origin the main block's centre at grade -- the
        glb's x, -z, y).  tools/rooms/make_rooms.py turns it into the game's room manifest."""
        if not self.plans:
            return
        keep_room = ("name", "floor", "rect", "type", "entry", "open_plan_to", "no_furnish", "no_light", "unit")
        keep_door = ("name", "floor", "at", "w", "ext", "cased", "glazed", "h", "between")
        plans = []
        for s_ in self.plans:
            rooms = []
            for r in s_.get("rooms", []):
                d = {k: _jsonable(r[k]) for k in keep_room if k in r}
                fk = getattr(r.get("fitout"), "_kind", None)
                if fk:
                    d["fitout"] = fk
                rooms.append(d)
            plans.append({"blocks": [{"name": bl.get("name"), "rect": _jsonable(bl["rect"]), "floors": _jsonable(bl["floors"]),
                                      "wall_top": _jsonable(bl.get("wall_top"))} for bl in s_.get("blocks", [])],
                          "rooms": rooms,
                          "doors": [{k: _jsonable(d[k]) for k in keep_door if k in d} for d in s_.get("doors", [])],
                          "stairs": [_jsonable({k: v for k, v in st.items() if not callable(v)}) for st in s_.get("stairs", [])]})
        os.makedirs(ROOMS_RAW, exist_ok=True)
        with open(os.path.join(ROOMS_RAW, rid + ".json"), "w") as f:
            json.dump({"id": rid, "plans": plans, "furniture": self.furniture, "audit": self.audit}, f, separators=(",", ":"))


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgb(h):
    """'#rrggbb' -> sRGB floats."""
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _is_special(ob):
    """Objects Godot wires by name (door leaves, ladders, lights) stay separate, with their subtree."""
    while ob is not None:
        n = ob.name
        if n.startswith("door_") or n.startswith("ladder_") or n.startswith("light_"):
            return True
        ob = ob.parent
    return False


def _join(obs, name):
    obs = [o for o in obs if o.type == "MESH" and len(o.data.polygons)]
    if not obs:
        return None
    keep = obs[0]
    with bpy.context.temp_override(active_object=keep, selected_editable_objects=obs, selected_objects=obs):
        bpy.ops.object.join()
    keep.name = name
    keep.data.name = name
    return keep


def _merge_meshes(self):
    """One visual mesh (one surface per material) + one collision-only mesh per building: a few
    draw calls and one static body instead of a node per part.  '-col' parts are both visual and
    collision; '-colonly' parts are collision only."""
    root = self.root
    vis, col = [], []
    for ob in list(bpy.data.objects):
        if ob.type != "MESH" or _is_special(ob):
            continue
        if ob.name.endswith("-colonly"):
            col.append(ob)
            continue
        if ob.name.endswith("-col"):
            dup = ob.copy()
            dup.data = ob.data.copy()
            bpy.context.scene.collection.objects.link(dup)
            dup.name = ob.name[:-4] + "_c"
            col.append(dup)
            ob.name = ob.name[:-4]
        vis.append(ob)
    for ob in vis + col:                      # bake parenting into world transforms before joining
        mw = ob.matrix_world.copy()
        ob.parent = None
        ob.matrix_world = mw
    v = _join(vis, self.name + "_visual")
    c = _join(col, self.name + "_collision-colonly")
    for ob in (v, c):
        if ob:
            mw = ob.matrix_world.copy()
            ob.parent = root
            ob.matrix_world = mw
    if c:
        c.data.materials.clear()
        while c.data.uv_layers:                # collision needs positions only
            c.data.uv_layers.remove(c.data.uv_layers[0])


Building.merge_meshes = _merge_meshes


class Part:
    def __init__(self, b, name, parent=None):
        self.b, self.name = b, name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.verify()
        self.mat_keys = []
        self.parent = parent
        self.origin = Vector((0, 0, 0))
        self.rot_z = 0.0

    def _mi(self, key):
        if key not in self.mat_keys:
            self.mat_keys.append(key)
        return self.mat_keys.index(key)

    def face(self, pts, mat, uvs=None):
        vs = [self.bm.verts.new(Vector(p) - self.origin) for p in pts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self._mi(mat)
        tile = self.b.tile.get(mat, 1.0)
        if uvs is None:
            f.normal_update()
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for loop in f.loops:
                w = Vector(loop.vert.co) + self.origin
                if ax == 0:
                    uv = (w.y * (1 if n.x > 0 else -1), w.z)
                elif ax == 1:
                    uv = (w.x * (-1 if n.y > 0 else 1), w.z)
                else:
                    uv = (w.x, w.y)
                loop[self.uv].uv = (uv[0] / tile, uv[1] / tile)
        else:
            for loop, uv in zip(f.loops, uvs):
                loop[self.uv].uv = (uv[0] / tile, uv[1] / tile)
        return f

    def box(self, lo, hi, mat, sides=None, mats=None):
        """Axis-aligned box. sides: subset of 'xXyYzZ' to emit (default all).
        Corners are sorted per axis: a box given hi < lo would otherwise come out inside-out
        (faces pointing inward -- invisible from outside and no collision from above)."""
        x0, x1 = sorted((lo[0], hi[0]))
        y0, y1 = sorted((lo[1], hi[1]))
        z0, z1 = sorted((lo[2], hi[2]))
        s = sides or "xXyYzZ"
        m = mats or {}
        if "x" in s:
            self.face([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], m.get("x", mat))
        if "X" in s:
            self.face([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], m.get("X", mat))
        if "y" in s:
            self.face([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], m.get("y", mat))
        if "Y" in s:
            self.face([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], m.get("Y", mat))
        if "z" in s:
            self.face([(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], m.get("z", mat))
        if "Z" in s:
            self.face([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], m.get("Z", mat))

    def obox(self, frame, lo, hi, mat, mats=None):
        """Box in a local frame (origin o, unit axes u, v, w): lo/hi are (u, v, w) extents."""
        o, u, v, w = frame
        x0, x1 = sorted((lo[0], hi[0]))       # sorted so a swapped lo/hi can't turn it inside-out
        y0, y1 = sorted((lo[1], hi[1]))
        z0, z1 = sorted((lo[2], hi[2]))

        def P(a, bb, c):
            return tuple(o + u * a + v * bb + w * c)
        m = mats or {}
        quads = {
            "u0": [P(x0, y1, z0), P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1)],
            "u1": [P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)],
            "v0": [P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)],
            "v1": [P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1)],
            "w0": [P(x0, y1, z0), P(x1, y1, z0), P(x1, y0, z0), P(x0, y0, z0)],
            "w1": [P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)],
        }
        for k, q in quads.items():
            self.face(q, m.get(k, mat))

    def cylinder(self, c, r, z0, z1, mat, n=16, caps=True, r1=None):
        r1 = r if r1 is None else r1
        ring0 = [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n), z0) for k in range(n)]
        ring1 = [(c[0] + r1 * math.cos(2 * math.pi * k / n), c[1] + r1 * math.sin(2 * math.pi * k / n), z1) for k in range(n)]
        circ = 2 * math.pi * max(r, r1)
        for k in range(n):
            a, bq = k, (k + 1) % n
            u0, u1 = circ * k / n, circ * (k + 1) / n
            self.face([ring0[a], ring0[bq], ring1[bq], ring1[a]], mat, uvs=[(u0, z0), (u1, z0), (u1, z1), (u0, z1)])
        if caps:
            self.face(list(reversed(ring0)), mat)
            self.face(ring1, mat)

    def prism(self, pts2d, z0, z1, mat, caps=True):
        n = len(pts2d)
        for k in range(n):
            a, bq = pts2d[k], pts2d[(k + 1) % n]
            self.face([(a[0], a[1], z0), (bq[0], bq[1], z0), (bq[0], bq[1], z1), (a[0], a[1], z1)], mat)
        if caps:
            self.face([(p[0], p[1], z0) for p in reversed(pts2d)], mat)
            self.face([(p[0], p[1], z1) for p in pts2d], mat)

    def sink_ground_contacts(self):
        """Whatever stands on grade (box bottoms, step and platform sides, posts, skirts) is carried
        down to -FOUND_DEPTH, so the building can sit on uneven or raised ground with no gap.  Only
        vertices at z ~ 0 that touch no upward-facing face move: ground and terrain surfaces stay."""
        if not self.b.sink_ground:
            return
        self.bm.normal_update()
        for v in self.bm.verts:
            wz = v.co.z + self.origin.z
            if abs(wz) < 0.03 and v.link_faces and not any(f.normal.z > 0.5 for f in v.link_faces):
                v.co.z = -FOUND_DEPTH - self.origin.z

    def to_object(self):
        me = bpy.data.meshes.new(self.name)
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=0.0005)
        self.bm.to_mesh(me)
        self.bm.free()
        for k in self.mat_keys:
            me.materials.append(self.b.mats[k])
        ob = bpy.data.objects.new(self.name, me)
        ob.location = self.origin
        ob.rotation_euler = (0, 0, self.rot_z)
        ob.parent = self.parent or self.b.root
        bpy.context.scene.collection.objects.link(ob)
        return ob


# ------------------------------------------------------------------ walls with openings
def wall_frame(a, b):
    """Frame for a wall running a->b (2D, outer face), inward normal to the LEFT of a->b."""
    a3, b3 = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
    u = (b3 - a3).normalized()
    w_in = Vector((-u.y, u.x, 0))
    return a3, u, w_in, (b3 - a3).length


def wall(part, a, b, z0, z1, t, openings, mat_out, mat_in, mat_reveal=None):
    """Solid wall from a to b (outer face line), thickness t toward the left (interior).
    openings: [dict(off=, w=, sill=, head=)] -- off/w along the wall, sill/head as z.
    Built as boxes around the openings (no booleans), so reveals are real faces."""
    o, u, w_in, length = wall_frame(a, b)
    up = Vector((0, 0, 1))
    frame = (o, u, w_in, up)          # local (along, depth, z)
    mr = mat_reveal or mat_out
    mats = {"v0": mat_out, "v1": mat_in, "u0": mr, "u1": mr, "w0": mr, "w1": mr}
    # vertical strips between all opening edges; each strip is solid from z0 to z1 minus the
    # openings over it -- so openings stacked above one another (a door under a frieze window)
    # are both real holes
    cuts = sorted(set(round(c, 5) for c in [0.0, length] + [op["off"] for op in openings] +
                      [op["off"] + op["w"] for op in openings] if 0.0 <= c <= length))
    for u0, u1 in zip(cuts, cuts[1:]):
        if u1 - u0 < 1e-4:
            continue
        um = (u0 + u1) / 2
        holes = sorted([(op["sill"], op["head"]) for op in openings if op["off"] <= um <= op["off"] + op["w"]])
        zc = z0
        for h0, h1 in holes:
            if h0 > zc + 1e-4:
                part.obox(frame, (u0, 0, zc), (u1, t, min(h0, z1)), mat_out, mats)
            zc = max(zc, h1)
        if zc < z1 - 1e-4:
            part.obox(frame, (u0, 0, zc), (u1, t, z1), mat_out, mats)
    return frame


def gable_infill(part, a, b, z_eave, z_ridge, t, mat_out, mat_in):
    """Triangular gable-end wall above the eave line (a->b outer face)."""
    o, u, w_in, length = wall_frame(a, b)
    up = Vector((0, 0, 1))
    mid = length / 2
    P = lambda x, d, z: tuple(o + u * x + w_in * d + up * z)
    part.face([P(0, 0, z_eave), P(length, 0, z_eave), P(mid, 0, z_ridge)], mat_out)
    part.face([P(length, t, z_eave), P(0, t, z_eave), P(mid, t, z_ridge)], mat_in)


def gable_roof(part, x0, x1, y0, y1, z_eave, pitch_deg, overhang_eave, overhang_rake, thick, mat_top,
               mat_under, ridge_axis="y", fascia=None):
    """Two sloped slabs meeting at the ridge. Ridge runs along ridge_axis over the rectangle."""
    if ridge_axis == "y":
        span = x1 - x0
        run = span / 2 + overhang_eave
        rise_run = math.tan(math.radians(pitch_deg))
        z_ridge = z_eave + span / 2 * rise_run
        zl = z_eave - overhang_eave * rise_run
        ya, yb = y0 - overhang_rake, y1 + overhang_rake
        xm = (x0 + x1) / 2
        slope_len = math.hypot(run, run * rise_run)
        for side in (-1, 1):
            xe = xm + side * (span / 2 + overhang_eave)
            nx, nz = side * math.sin(math.radians(pitch_deg)), math.cos(math.radians(pitch_deg))
            dz = thick / nz if nz else thick
            top = [(xe, ya, zl), (xm, ya, z_ridge), (xm, yb, z_ridge), (xe, yb, zl)]
            if side == 1:
                top = [top[1], top[0], top[3], top[2]]
            uvs = [(0, 0), (0, slope_len), (yb - ya, slope_len), (yb - ya, 0)] if side == -1 else \
                [(0, slope_len), (0, 0), (yb - ya, 0), (yb - ya, slope_len)]
            part.face(top, mat_top, uvs=uvs)
            bot = [(p[0], p[1], p[2] - dz) for p in top]
            part.face(list(reversed(bot)), mat_under)
            # eave edge (fascia) and rake edges
            e0, e1 = (xe, ya, zl), (xe, yb, zl)
            part.face([e0, e1, (e1[0], e1[1], e1[2] - dz), (e0[0], e0[1], e0[2] - dz)] if side == 1 else
                      [e1, e0, (e0[0], e0[1], e0[2] - dz), (e1[0], e1[1], e1[2] - dz)], fascia or mat_under)
            for yy, flip in ((ya, side == 1), (yb, side == -1)):
                q = [(xe, yy, zl), (xm, yy, z_ridge), (xm, yy, z_ridge - dz), (xe, yy, zl - dz)]
                part.face(list(reversed(q)) if flip else q, fascia or mat_under)
        return z_ridge
    raise NotImplementedError("ridge_axis x: rotate the plan instead")


def pyramid_roof(part, cx, cy, half, z_base, z_apex, overhang, mat_top, mat_under):
    h = half + overhang
    pts = [(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)]
    slope_z = (z_apex - z_base) / half
    zb = z_base - overhang * slope_z
    for k in range(4):
        a, b = pts[k], pts[(k + 1) % 4]
        L = math.dist(a, b)
        sl = math.hypot(h, z_apex - zb)
        part.face([(a[0], a[1], zb), (b[0], b[1], zb), (cx, cy, z_apex)], mat_top, uvs=[(0, 0), (L, 0), (L / 2, sl)])
    part.face([(p[0], p[1], zb) for p in reversed(pts)], mat_under)


# ------------------------------------------------------------------ windows / doors
def window(b, part_name, frame, off, w, sill, head, t, sash_rows=2, sash_cols=2, mats=None, casing=0.1,
           glass_name=None):
    """Double-hung window in a wall opening (frame from wall()): casing, sill, two sashes
    with muntin grid (rows x cols panes per sash), glass as a separate see-through part."""
    mats = mats or {}
    trim = mats.get("trim", "trim")
    o, u, w_in, up = frame
    pt = b.part(part_name)
    F = (o, u, w_in, up)
    # exterior casing (flat boards proud of the siding) + head cap + sill
    pt.obox(F, (off - casing, -0.025, sill), (off, 0.0, head + casing), trim)
    pt.obox(F, (off + w, -0.025, sill), (off + w + casing, 0.0, head + casing), trim)
    pt.obox(F, (off - casing - 0.02, -0.045, head + casing), (off + w + casing + 0.02, 0.0, head + casing + 0.04), trim)
    pt.obox(F, (off - casing, -0.06, sill - 0.04), (off + w + casing, t * 0.35, sill), trim)
    # interior casing
    pt.obox(F, (off - casing * 0.8, t, sill - 0.05), (off, t + 0.02, head + casing * 0.8), trim)
    pt.obox(F, (off + w, t, sill - 0.05), (off + w + casing * 0.8, t + 0.02, head + casing * 0.8), trim)
    pt.obox(F, (off - casing * 0.8, t, head), (off + w + casing * 0.8, t + 0.02, head + casing * 0.8), trim)
    pt.obox(F, (off - casing, t, sill - 0.02), (off + w + casing, t + 0.05, sill), trim)
    # jamb liners
    d0, d1 = t * 0.3, t * 0.55
    fw = 0.045
    pt.obox(F, (off, d0, sill), (off + fw, d1 + 0.04, head), trim)
    pt.obox(F, (off + w - fw, d0, sill), (off + w, d1 + 0.04, head), trim)
    pt.obox(F, (off, d0, head - fw), (off + w, d1 + 0.04, head), trim)
    # sashes: lower (interior plane) and upper (exterior plane), meeting rail at mid height
    mid = (sill + head) / 2
    rail = 0.05
    for (z0, z1, dd) in ((sill, mid + rail / 2, d1 - 0.035), (mid - rail / 2, head - fw, d0 + 0.005)):
        x0, x1 = off + fw, off + w - fw
        pt.obox(F, (x0, dd, z0), (x1, dd + 0.035, z0 + rail), trim)
        pt.obox(F, (x0, dd, z1 - rail), (x1, dd + 0.035, z1), trim)
        pt.obox(F, (x0, dd, z0), (x0 + rail, dd + 0.035, z1), trim)
        pt.obox(F, (x1 - rail, dd, z0), (x1, dd + 0.035, z1), trim)
        for c in range(1, sash_cols):
            xm = x0 + (x1 - x0) * c / sash_cols
            pt.obox(F, (xm - 0.011, dd + 0.005, z0), (xm + 0.011, dd + 0.03, z1), trim)
        for r in range(1, sash_rows):
            zm = z0 + (z1 - z0) * r / sash_rows
            pt.obox(F, (x0, dd + 0.005, zm - 0.011), (x1, dd + 0.03, zm + 0.011), trim)
        g = b.part(glass_name or (part_name + "_glass"))
        P = lambda a, d, z: tuple(o + u * a + w_in * d + up * z)
        gd = dd + 0.017
        g.face([P(x0, gd, z0), P(x1, gd, z0), P(x1, gd, z1), P(x0, gd, z1)], "glass")
        g.face([P(x1, gd, z0), P(x0, gd, z0), P(x0, gd, z1), P(x1, gd, z1)], "glass")


def panel_leaf(b, name, width, height, thick, mat, panels, origin, direction, parent=None, rails=0.11, glazed=None):
    """A panelled door leaf as its own object. origin = hinge-axis bottom point (3D),
    direction = unit 2D vector from hinge toward the latch edge (leaf's local +X).
    panels: list of (x0, z0, x1, z1) fractions of the leaf face for raised panels."""
    p = b.part(name, parent)
    p.origin = Vector(origin)
    p.rot_z = math.atan2(direction[1], direction[0])
    # build in leaf-local coords, then rotate: bmesh verts are relative to origin already,
    # so build around (0,0,0) with +X along the leaf and apply the rotation at object level.
    o = Vector((0, 0, 0))
    F = (o, Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    p.origin = Vector((0, 0, 0))      # temporarily build in local space
    if glazed:
        # stile-and-rail frame around a glass light (storefront / kitchen / porch doors)
        gx0, gz0, gx1, gz1 = width * glazed[0], height * glazed[1], width * glazed[2], height * glazed[3]
        for (a0, a1, c0, c1) in ((0.003, gx0, 0.005, height - 0.003), (gx1, width - 0.003, 0.005, height - 0.003),
                                 (gx0, gx1, 0.005, gz0), (gx0, gx1, gz1, height - 0.003)):
            p.obox(F, (a0, -thick / 2, c0), (a1, thick / 2, c1), mat)
        for yy in (-0.004, 0.004):
            p.face([(gx0, yy, gz0), (gx1, yy, gz0), (gx1, yy, gz1), (gx0, yy, gz1)][:: 1 if yy < 0 else -1], "glass")
    else:
        p.obox(F, (0.003, -thick / 2, 0.005), (width - 0.003, thick / 2, height - 0.003), mat)
    for (fx0, fz0, fx1, fz1) in panels:
        a0, a1, c0, c1 = width * fx0, width * fx1, height * fz0, height * fz1
        m = 0.022                                                    # bolection moulding width
        for s in (-1, 1):
            face = thick / 2 * s
            # raised field sits back, the moulding frame stands proud -> readable shadow lines
            y0, y1 = sorted((face, face + s * 0.006))
            p.obox(F, (a0 + m, y0, c0 + m), (a1 - m, y1, c1 - m), mat)
            y0, y1 = sorted((face, face + s * 0.016))
            for (u0, u1, v0, v1) in ((a0, a1, c0, c0 + m), (a0, a1, c1 - m, c1), (a0, a0 + m, c0, c1), (a1 - m, a1, c0, c1)):
                p.obox(F, (u0, y0, v0), (u1, y1, v1), "trim_door" if "trim_door" in p.b.mats else mat)
    # knob
    kx = width - 0.07
    for s in (-1, 1):
        y = s * (thick / 2 + 0.03)
        p.obox(F, (kx - 0.025, min(y, s * thick / 2), 0.93), (kx + 0.025, max(y, s * thick / 2), 0.98), "brass")
    p.origin = Vector(origin)
    return p


def door(b, frame_part, frame, off, w, head, t, name, swing_in=True, leaves=1, panels=None, mat="door",
         locked=False, threshold_z=0.0, casing=0.1, trim="trim", leaf_thick=0.045, glazed=None, hinge_far=False):
    """Door opening fitted with casing + 1 or 2 hinged leaves (separate objects).
    swing_in: opens toward the wall frame's interior side (w_in).
    hinge_far: a single leaf hangs on the far jamb (off + w) instead of the near one."""
    o, u, w_in, up = frame
    fp = b.part(frame_part)
    F = frame
    # casings both faces + head
    fp.obox(F, (off - casing, -0.025, threshold_z), (off, 0, head + casing), trim)
    fp.obox(F, (off + w, -0.025, threshold_z), (off + w + casing, 0, head + casing), trim)
    fp.obox(F, (off - casing - 0.02, -0.05, head + casing), (off + w + casing + 0.02, 0, head + casing + 0.05), trim)
    fp.obox(F, (off - casing, t, threshold_z), (off, t + 0.02, head + casing), trim)
    fp.obox(F, (off + w, t, threshold_z), (off + w + casing, t + 0.02, head + casing), trim)
    fp.obox(F, (off - casing, t, head), (off + w + casing, t + 0.02, head + casing), trim)
    fp.obox(F, (off, 0, head - 0.04), (off + w, t, head), trim)                 # head jamb
    fp.obox(F, (off, 0, threshold_z), (off + 0.035, t, head), trim)
    fp.obox(F, (off + w - 0.035, 0, threshold_z), (off + w, t, head), trim)
    # the threshold is the walkable floor across the wall thickness: give it collision
    b.part("thresholds-col").obox(F, (off, -0.03, threshold_z - 0.02), (off + w, t, threshold_z + 0.015), "threshold")
    panels = [(0.15, 0.55, 0.85, 0.92), (0.15, 0.1, 0.85, 0.45)] if panels is None else panels
    leaf_depth = t * 0.25 if not swing_in else t * 0.75
    if leaves == 0:                     # cased opening: trim only, no leaf
        return []
    lw = (w - 0.07) / leaves
    ids = []
    for k in range(leaves):
        if k == 0 and not (hinge_far and leaves == 1):
            hinge_a = off + 0.035
            dir_u = 1
        else:
            hinge_a = off + w - 0.035
            dir_u = -1
        hinge = o + u * hinge_a + w_in * leaf_depth + up * (threshold_z + 0.015)
        d = u * dir_u
        # sign of rotation about +Z that swings the latch edge toward the swing side
        swing_side = w_in if swing_in else -w_in
        rot = Vector((-d.y, d.x, 0))
        sign = "p" if rot.dot(swing_side) > 0 else "n"
        nm = f"door_{name}{'_' + 'LR'[k] if leaves == 2 else ''}__{sign}{'__locked' if locked else ''}"
        panel_leaf(b, nm, lw, head - threshold_z - 0.03, leaf_thick, mat, panels, hinge, (d.x, d.y), glazed=glazed)
        ids.append(nm)
    return ids


# ------------------------------------------------------------------ stairs / rails / text
def raking_rail(part, p0, p1, mat, w=0.06, h=0.05):
    """A straight bar (handrail) from 3D point p0 to p1, w wide and h deep, oriented along it."""
    a, c = Vector(p0), Vector(p1)
    u = (c - a)
    L = u.length
    u.normalize()
    v = Vector((0, 0, 1)).cross(u)
    if v.length < 1e-6:
        v = Vector((1, 0, 0))
    v.normalize()
    wv = u.cross(v)
    part.obox((a, u, v, wv), (0, -w / 2, -h / 2), (L, w / 2, h / 2), mat)


def stairs(b, name, start, direction, width, rise_total, n_risers, run, mat, stringer_mat=None):
    """Straight flight. start = (x,y,z) of the bottom nosing centre line's left edge;
    direction = unit 2D run direction. Adds a matching invisible ramp for walking."""
    d = Vector((direction[0], direction[1], 0)).normalized()
    side = Vector((-d.y, d.x, 0))
    o = Vector(start)
    F = (o, d, side, Vector((0, 0, 1)))
    p = b.part(name)
    rh = rise_total / n_risers
    for k in range(n_risers):
        p.obox(F, (k * run, 0, k * rh), ((k + 1) * run + 0.02, width, (k + 1) * rh), mat)
    sm = stringer_mat or mat
    L = n_risers * run
    depth = 0.28                                   # stringer board depth measured vertically
    for s0 in (-0.04, width):
        s1 = s0 + 0.04
        P = lambda a, c, z: tuple(o + d * a + side * c + Vector((0, 0, z)))
        prof = [(0, 0), (L, rise_total), (L, max(0.0, rise_total - depth)), (min(L, depth * L / rise_total), 0)]
        for (a0, z0), (a1, z1) in zip(prof, prof[1:] + prof[:1]):
            p.face([P(a0, s0, z0), P(a1, s0, z1), P(a1, s1, z1), P(a0, s1, z0)], sm)
        p.face([P(a, s0, z) for a, z in reversed(prof)], sm)
        p.face([P(a, s1, z) for a, z in prof], sm)
    ramp = b.part(name + "_ramp-colonly")
    L = n_risers * run
    P = lambda a, c, z: tuple(o + d * a + side * c + Vector((0, 0, z)))
    ramp.face([P(0, 0, 0), P(L, 0, rise_total), P(L, width, rise_total), P(0, width, 0)], mat)
    ramp.face([P(0, width, 0), P(L, width, rise_total), P(L, 0, rise_total), P(0, 0, 0)], mat)


def spindle_rail(p, pts, z0, height, spacing, mat, post_every=None, rail_w=0.06):
    """Railing along a 2D polyline: bottom rail, top rail, square spindles."""
    for a, c in zip(pts, pts[1:]):
        A, C = Vector((a[0], a[1], 0)), Vector((c[0], c[1], 0))
        L = (C - A).length
        u = (C - A).normalized()
        v = Vector((-u.y, u.x, 0))
        F = (A, u, v, Vector((0, 0, 1)))
        p.obox(F, (0, -rail_w / 2, z0 + height - 0.05), (L, rail_w / 2, z0 + height), mat)
        p.obox(F, (0, -0.03, z0 + 0.05), (L, 0.03, z0 + 0.1), mat)
        n = max(1, int(L / spacing))
        for k in range(n + 1):
            s = L * k / n
            p.obox(F, (s - 0.018, -0.018, z0 + 0.1), (s + 0.018, 0.018, z0 + height - 0.05), mat)


def text_mesh(b, name, text, size, loc, rot_z, mat, extrude=0.004, font=None, parent=None, align="CENTER"):
    """Real lettering: a Blender text object converted to a mesh (signs, plates, names)."""
    cu = bpy.data.curves.new(name + "_crv", type="FONT")
    cu.body = text
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align
    cu.align_y = "CENTER"
    fp = font or "/run/host/usr/share/fonts/noto/NotoSerif-Bold.ttf"
    if os.path.exists(fp):
        cu.font = bpy.data.fonts.load(fp, check_existing=True)
    tmp = bpy.data.objects.new(name + "_tmp", cu)
    bpy.context.scene.collection.objects.link(tmp)
    tmp.location = loc
    tmp.rotation_euler = (math.pi / 2, 0, rot_z)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    ob = bpy.data.objects.new(name, me)
    ob.matrix_world = tmp.matrix_world.copy()
    bpy.data.objects.remove(tmp)
    me.materials.clear()
    me.materials.append(b.mats[mat])
    ob.parent = parent or b.root
    ob.matrix_parent_inverse = (parent or b.root).matrix_world.inverted()
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ------------------------------------------------------------------ profile walls, floors, trims
def wall_profile(part, a, b, z0, top, t, openings, mat_out, mat_in, mat_reveal=None, mat_top=None):
    """Wall a->b whose top follows top(u) (u = distance along the wall), e.g. a gable end.
    Built as vertical strips between opening edges; each strip is solid from z0 to top(u)
    minus the openings -- so gable-end windows, attic vents etc. are real holes."""
    o, u, w_in, length = wall_frame(a, b)
    up = Vector((0, 0, 1))
    mr = mat_reveal or mat_out
    mt = mat_top or mr
    cuts = sorted({0.0, length} | {op["off"] for op in openings} | {op["off"] + op["w"] for op in openings})
    # also split at any kink of the top profile (ridge) so slanted tops stay planar
    for k in range(1, 16):
        cuts.append(length * k / 16)
    cuts = sorted(set(round(c, 5) for c in cuts))
    P = lambda x, d, z: tuple(o + u * x + w_in * d + up * z)
    for u0, u1 in zip(cuts, cuts[1:]):
        if u1 - u0 < 1e-4:
            continue
        um = (u0 + u1) / 2
        holes = sorted([(op["sill"], op["head"]) for op in openings if op["off"] <= um <= op["off"] + op["w"]])
        spans, zc = [], z0
        for s0, s1 in holes:
            if s0 > zc:
                spans.append((zc, s0, False))
            zc = max(zc, s1)
        spans.append((zc, None, True))
        for zb, zt, to_top in spans:
            t0 = top(u0) if to_top else zt
            t1 = top(u1) if to_top else zt
            if min(t0, t1) <= zb + 1e-4:
                continue
            part.face([P(u0, 0, zb), P(u1, 0, zb), P(u1, 0, t1), P(u0, 0, t0)], mat_out)
            part.face([P(u1, t, zb), P(u0, t, zb), P(u0, t, t0), P(u1, t, t1)], mat_in)
            part.face([P(u0, 0, t0), P(u1, 0, t1), P(u1, t, t1), P(u0, t, t0)], mt)       # top / head
            part.face([P(u1, 0, zb), P(u0, 0, zb), P(u0, t, zb), P(u1, t, zb)], mr)        # bottom / sill
            # reveal faces only where a strip edge borders an opening or the wall end
            for ue, sgn in ((u0, -1), (u1, 1)):
                te = t0 if ue == u0 else t1
                border = ue in (0.0, length) or any(abs(ue - op["off"]) < 1e-4 or abs(ue - op["off"] - op["w"]) < 1e-4
                                                     for op in openings)
                if border:
                    q = [P(ue, 0, zb), P(ue, t, zb), P(ue, t, te), P(ue, 0, te)]
                    part.face(q if sgn < 0 else list(reversed(q)), mr)
    return (o, u, w_in, up)


def gable_top(length, z_eave, z_ridge):
    return lambda uu: z_eave + (z_ridge - z_eave) * (1 - abs(uu - length / 2) / (length / 2))


def floor_with_holes(part, x0, x1, y0, y1, z, thick, holes, mat_top, mat_under):
    """Floor slab over [x0,x1]x[y0,y1] with rectangular holes (stair wells), split on a grid."""
    xs = sorted({x0, x1} | {h[0] for h in holes} | {h[1] for h in holes})
    ys = sorted({y0, y1} | {h[2] for h in holes} | {h[3] for h in holes})
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            cx, cy = (xa + xb) / 2, (ya + yb) / 2
            if any(h[0] < cx < h[1] and h[2] < cy < h[3] for h in holes):
                continue
            part.box((xa, ya, z - thick), (xb, yb, z), mat_top, mats={"z": mat_under}, sides="zZ")
    for (hx0, hx1, hy0, hy1) in holes:        # well edges
        part.box((hx0, hy0, z - thick), (hx1, hy1, z), mat_under, sides="xXyY")


def shutter_pair(part, frame, off, w, sill, head, mat, depth=-0.04):
    """Louvered shutters either side of a window (flat panels with slat ridges)."""
    sw = w / 2
    for (s0, s1) in ((off - sw - 0.02, off - 0.02), (off + w + 0.02, off + w + sw + 0.02)):
        part.obox(frame, (s0, depth - 0.03, sill), (s1, depth, head), mat)
        n = int((head - sill) / 0.06)
        for k in range(n):
            z = sill + 0.05 + k * (head - sill - 0.1) / n
            part.obox(frame, (s0 + 0.04, depth - 0.045, z), (s1 - 0.04, depth - 0.03, z + 0.022), mat)


def lintel(part, frame, off, w, head, mat, h=0.2, over=0.08, depth=-0.012):
    """Flat brick jack-arch / stone lintel over an opening, a touch proud of the wall."""
    part.obox(frame, (off - over, depth, head), (off + w + over, 0.0, head + h), mat)


def transom(b, frame, off, w, z0, z1, t, trim="trim", lights=4):
    """Fixed glazed transom over a door, divided into `lights`."""
    p = b.part("windows")
    o, u, w_in, up = frame
    d = t * 0.4
    p.obox(frame, (off, d, z0), (off + w, d + 0.05, z0 + 0.04), trim)
    for k in range(1, lights):
        x = off + w * k / lights
        p.obox(frame, (x - 0.012, d, z0), (x + 0.012, d + 0.05, z1), trim)
    g = b.part("glass")
    P = lambda a, dd, z: tuple(o + u * a + w_in * dd + up * z)
    g.face([P(off, d + 0.025, z0 + 0.04), P(off + w, d + 0.025, z0 + 0.04), P(off + w, d + 0.025, z1), P(off, d + 0.025, z1)], "glass")
    g.face([P(off + w, d + 0.025, z0 + 0.04), P(off, d + 0.025, z0 + 0.04), P(off, d + 0.025, z1), P(off + w, d + 0.025, z1)], "glass")


class _SwapXY:
    """Proxy Part that mirrors x<->y (and fixes winding) -- lets y-ridge helpers build x-ridge roofs."""
    def __init__(self, part):
        self.p = part

    def face(self, pts, mat, uvs=None):
        sw = [(q[1], q[0], q[2]) for q in pts][::-1]
        return self.p.face(sw, mat, uvs=None if uvs is None else list(uvs)[::-1])


def gable_roof_x(part, x0, x1, y0, y1, z_eave, pitch_deg, overhang_eave, overhang_rake, thick, mat_top, mat_under,
                 fascia=None):
    """Gable roof with the ridge along X (eaves on the north/south sides)."""
    return gable_roof(_SwapXY(part), y0, y1, x0, x1, z_eave, pitch_deg, overhang_eave, overhang_rake, thick,
                      mat_top, mat_under, ridge_axis="y", fascia=fascia)


def column(part, x, y, z0, z1, r, mat, n=14):
    """Tuscan porch column: plinth, tapered shaft, necking and square abacus."""
    part.box((x - r * 1.25, y - r * 1.25, z0), (x + r * 1.25, y + r * 1.25, z0 + 0.06), mat)
    part.cylinder((x, y), r * 1.1, z0 + 0.06, z0 + 0.12, mat, n=n)
    part.cylinder((x, y), r, z0 + 0.12, z1 - 0.16, mat, n=n, r1=r * 0.85)
    part.cylinder((x, y), r * 0.95, z1 - 0.16, z1 - 0.08, mat, n=n)
    part.box((x - r * 1.2, y - r * 1.2, z1 - 0.08), (x + r * 1.2, y + r * 1.2, z1), mat)
