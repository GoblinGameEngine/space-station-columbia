"""
components.py -- the vehicle component library writer (research/vehicles/MODULAR_VEHICLES.md).

A vehicle builder (e.g. remake/blender/tram/carrow_tram.py) makes its body as modules -- every panel, pane,
door leaf, seat, roof bay a separate kit Mesh -- and hands each to a Library with its labels:

  standard  the class standard it is built to (kit/standards.py): what it fits
  role      what it is (side_bay, glazing, door_leaf, roof_bay, seat ...)
  slot      the standard's slot it fills (door, bay_short, roof ...) or "free" (seats, fittings: placed anywhere
            on the floor / walls)
  side      R, L or C
  style     the maker's look ("carrow"): free within the slot's envelope

The Library writes, under godot_project/remake/vehicles/components/<standard>/:
  <style>.pack            every component's triangles: per material, float32 positions then normals
                          (Godot frame: x right, y up, z back; local: z measured from the slot's start)
  <style>.catalog.json    every component: id, labels, interface key, materials -> [byte offset, vertex count],
                          collision boxes (local), hp, mass, how it breaks; and the style's palette
and, per vehicle part, a blueprint (<name>.blueprint.json): the standard, the ring stations, and the placements
-- [instance id, component id, anchor (Godot z of the slot's start)] -- plus doors, markers and lengths.

Identical components (same labels, same geometry to 1 mm) are written once: a window bay used on three
sections is one component placed three times.
"""
import hashlib
import json
import os
import struct

import bmesh


def g(v):
    """Blender (x, y, z) -> Godot (x, z, -y)."""
    return (v[0], v[2], -v[1])


class Library:
    def __init__(self, std, style, palette, out_root):
        self.std = std
        self.style = style
        self.palette = palette
        self.dir = os.path.join(out_root, std["id"])
        os.makedirs(self.dir, exist_ok=True)
        self.comps = {}              # id -> catalog entry
        self.data = bytearray()
        self.by_hash = {}

    def add(self, mesh, mod, role, slot, side, anchor_y, mat_keys):
        """A module as a component: its triangles moved into the slot's frame (anchor_y: the slot's start,
        Blender y, the end nearest +y). Returns the component id."""
        bm = mesh.bm.copy()
        smooth = mod.get("smooth", False)                   # (a curved part -- an envelope, a duct: vertex normals, kept
        if smooth:                                          #  flat where faces meet at more than 40 degrees)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.normal_update()
        groups = {}
        for f in bm.faces:
            m = mat_keys[f.material_index]
            n = f.normal
            lst = groups.setdefault(m, [[], []])
            vs = [lp.vert.co for lp in f.loops]
            ns = [n] * 3
            if smooth:
                ns = []
                for lp in f.loops:
                    acc = n.copy() * 0.0
                    for of in lp.vert.link_faces:
                        if of.normal.dot(n) > 0.766:
                            acc += of.normal * of.calc_area()
                    ns.append(acc.normalized() if acc.length > 1e-9 else n)
            for i in (0, 2, 1):                             # (Godot's front faces are clockwise)
                v, nn = vs[i], ns[i]
                p = g((v.x, v.y - anchor_y, v.z))
                lst[0].append(p)
                lst[1].append(g((nn.x, nn.y, nn.z)))
        bm.free()
        if not groups:
            return None
        h = hashlib.blake2b(digest_size=5)
        h.update(("%s|%s|%s|%s" % (role, slot, side, self.style)).encode())
        for m in sorted(groups):
            h.update(m.encode())
            for p in groups[m][0]:
                h.update(("%.3f,%.3f,%.3f;" % p).encode())
        boxes = []
        for b in mod.get("boxes", []):
            cx, cy, cz, sx, sy, sz = b
            gc = g((cx, cy - anchor_y, cz))
            boxes.append([round(gc[0], 4), round(gc[1], 4), round(gc[2], 4), sx, sz, sy])
        key = h.hexdigest()
        if key in self.by_hash:
            return self.by_hash[key]
        span = max(0.0, max(-p[2] for m in groups for p in groups[m][0]))      # (how far it reaches along the slot)
        cid = "%s.%s.%s.%s.%s.%s" % (self.std["id"], role, slot, side, self.style, key[:6])
        mats = {}
        for m in sorted(groups):
            pos, nor = groups[m]
            off = len(self.data)
            for p in pos:
                self.data += struct.pack("<3f", *p)
            for n in nor:
                self.data += struct.pack("<3f", *n)
            mats[m] = [off, len(pos)]
        self.comps[cid] = {
            "id": cid, "standard": self.std["id"], "class": self.std["class"], "role": role, "slot": slot, "side": side,
            "style": self.style, "interface": "%s/%s/%s/%s" % (self.std["id"], role, slot, side),
            "reach": round(span, 3), "mats": mats, "boxes": boxes,
            "hp": mod.get("hp", 100), "mass_kg": mod.get("mass_kg", 10), "breaks": mod.get("breaks", "detach"),
            "tolerance": self.std["tolerance"].get(role, 0.08),
        }
        self.by_hash[key] = cid
        return cid

    def write(self):
        # (each file written whole, then moved into place: a game reading the library never sees half of one)
        tmp = os.path.join(self.dir, "." + self.style + ".pack.tmp")
        with open(tmp, "wb") as f:
            f.write(bytes(self.data))
        os.replace(tmp, os.path.join(self.dir, self.style + ".pack"))
        cat = {"_about": "Vehicle component library (remake/blender/kit/components.py; research/vehicles/MODULAR_VEHICLES.md)",
               "standard": self.std["id"], "class": self.std["class"], "style": self.style,
               "pack": "res://remake/vehicles/components/%s/%s.pack" % (self.std["id"], self.style),
               "palette": self.palette, "components": self.comps}
        tmp = os.path.join(self.dir, "." + self.style + ".catalog.tmp")
        with open(tmp, "w") as f:
            json.dump(cat, f, indent=1)
        os.replace(tmp, os.path.join(self.dir, self.style + ".catalog.json"))
        return len(self.comps), len(self.data)


def write_blueprint(path, bp):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(bp, f, indent=1)
    os.replace(tmp, path)
