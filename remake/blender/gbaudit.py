"""
gbaudit.py -- does a built building hold together?  (the user, 2026-10-07: "make sure they are all sealed and do not have
parts clipping outside of the model.  Doors can have glass, but they cannot have manifold holes in them.")

Run by Building.finish on every gbhouse-planned building, on the finished objects (before merging and export):

  sealed   from points inside every room, rays in 26 directions must meet the building (wall, roof, floor, a door leaf,
           glass) before they leave the building's own blocks: a ray that gets out is a hole in the envelope
  clipping no vertex of the furniture or the partitions stands outside the building's walls (the exterior walls'
           inner faces) or above its roof's underside
  doors    every door leaf (not a picket gate) is solid or glass over its whole face: a grid of rays through it all
           meet the leaf, and its solid parts are closed (no open edges outside the glass)

Results go in the raw room manifest ("audit") and print as  AUDIT <id> ok|FAIL leaks=.. clips=.. doors=..
"""
import math

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

DIRS = [Vector((x, y, z)).normalized() for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)]
CLIP_TOL = 0.02          # m a vertex may stand past a wall's inner face (contact, rounding)
SEAL_SLACK = 0.35        # m past the blocks' outer faces a ray may meet the envelope (eaves, sills, trims)
NOT_ENVELOPE = ("furn_", "light", "yard", "fence", "chainlink", "picket", "mailbox", "car", "lot", "tree", "hedge", "sign")


def _world_bm(objs):
    bm = bmesh.new()
    for o in objs:
        if o.type != "MESH" or not o.data.polygons:
            continue
        tmp = bmesh.new()
        tmp.from_mesh(o.data)
        tmp.transform(o.matrix_world)
        me = bpy.data.meshes.new("_audit_tmp")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    return bm


def _blocks(b):
    out = []
    for h in b.houses:
        for bl in h.s.get("blocks", []):
            out.append((h, bl))
    return out


def _block_at(blocks, x, y, inset=0.0):
    for h, bl in blocks:
        x0, y0, x1, y1 = bl["rect"]
        if x0 + inset - 1e-6 <= x <= x1 - inset + 1e-6 and y0 + inset - 1e-6 <= y <= y1 - inset + 1e-6:
            return h, bl
    return None


def _exit_dist(blocks, p, d, z_top):
    """how far along d from p the ray leaves the blocks' footprint (or goes over the roof line / under grade): slab exits
    block to block"""
    t = 0.0
    for _ in range(64):
        q = p + d * t
        if q.z > z_top or q.z < -1.0:
            return t
        hb = _block_at(blocks, q.x, q.y)
        if hb is None:
            return t
        x0, y0, x1, y1 = hb[1]["rect"]
        te = 1e9
        if abs(d.x) > 1e-9:
            te = min(te, ((x1 if d.x > 0 else x0) - q.x) / d.x)
        if abs(d.y) > 1e-9:
            te = min(te, ((y1 if d.y > 0 else y0) - q.y) / d.y)
        if abs(d.z) > 1e-9:
            te = min(te, ((z_top if d.z > 0 else -1.0) - q.z) / d.z)
        t += max(te, 0.0) + 0.01
    return t


def _inside_walls(blocks, x, y, tol):
    """inside the exterior walls' inner faces: in some block, and within its wall thickness of a side only where another
    block abuts that side there (a porch, a wing, the next storey's block)"""
    for h, bl in blocks:
        x0, y0, x1, y1 = bl["rect"]
        if not (x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6):
            continue
        te = h.te - tol
        ok = True
        for side, dist in (("W", x - x0), ("E", x1 - x), ("S", y - y0), ("N", y1 - y)):
            if dist >= te:
                continue
            q = {"W": (x0 - 0.05, y), "E": (x1 + 0.05, y), "S": (x, y0 - 0.05), "N": (x, y1 + 0.05)}[side]
            if _block_at([ob for ob in blocks if ob[1] is not bl], *q) is None:
                ok = False
                break
        if ok:
            return True
    return False


def audit(b):
    blocks = _blocks(b)
    if not blocks:
        return None
    bpy.context.view_layer.update()              # (the leaves' hinge placements are in matrix_world only after this)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    env = [o for o in meshes if not o.name.lower().startswith(NOT_ENVELOPE)]
    bm = _world_bm(env)
    tree = BVHTree.FromBMesh(bm)
    z_top = max(bl.get("wall_top", 3.0) for _, bl in blocks) + 12.0
    res = {"leaks": [], "clips": [], "doors": []}
    # --- sealed
    for h in b.houses:
        for r in h.s.get("rooms", []):
            x0, y0, x1, y1 = r["rect"]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            hb = _block_at(blocks, cx, cy)
            if hb is None:
                continue
            fl = r.get("floor", 0)
            floors = hb[1]["floors"]
            if fl >= len(floors):
                continue
            fz, cz = floors[fl]
            ins = 0.35
            # (off the room's centre lines: a double door's leaves meet there with a few mm between them)
            xs = [x0 + ins, cx + 0.13, x1 - ins] if x1 - x0 > 2 * ins + 0.3 else [cx + 0.07]
            ys = [y0 + ins, cy + 0.11, y1 - ins] if y1 - y0 > 2 * ins + 0.3 else [cy + 0.07]
            bad = 0
            first = None
            for x in xs:
                for y in ys:
                    top = min(cz, h.roof_under(hb[1], x, y)) - 0.25      # (under the roof AT the point: an attic room's
                    if top < fz + 0.3:                                    #  sides run under the slope)
                        continue
                    for z in sorted({min(fz + 1.0, top), top}):
                        p = Vector((x, y, z))
                        if tree.find_nearest(p, 0.05)[0] is not None:
                            continue                     # (inside a wall or a stair: not a room point)
                        for d in DIRS:
                            lim = _exit_dist(blocks, p, d, z_top) + SEAL_SLACK
                            hit = tree.ray_cast(p, d, lim)
                            if hit[0] is None:
                                bad += 1
                                if first is None:
                                    first = ([round(v, 2) for v in p], [round(v, 2) for v in d])
            if bad:
                res["leaks"].append({"room": r["name"], "floor": fl, "rays": bad, "e.g.": first})
    bm.free()
    # --- clipping: furniture and partitions inside the walls and under the roof
    for o in meshes:
        n = o.name.lower()
        if not (n.startswith("furn_") or n.startswith("partitions")):
            continue
        worst, count = 0.0, 0
        mw = o.matrix_world
        for v in o.data.vertices:
            q = mw @ v.co
            hb = _block_at(blocks, q.x, q.y, inset=0.0)
            over = 0.0
            if hb is None:
                over = 1.0                               # (outside every block's outer face)
            else:
                h, bl = hb
                if not _inside_walls(blocks, q.x, q.y, CLIP_TOL):
                    over = max(over, 0.01)              # (in the exterior wall, or through it)
                ru = h.roof_under(bl, q.x, q.y)
                if q.z > ru + CLIP_TOL:
                    over = max(over, q.z - ru)
            if over > 0:
                count += 1
                worst = max(worst, over)
        if count:
            res["clips"].append({"part": o.name, "verts": count, "worst_m": round(worst, 3)})
    # --- doors: solid or glass over the whole face, closed solids
    for o in meshes:
        n = o.name.lower()
        if not n.startswith("door_") or "gate" in n:
            continue
        me = o.data
        if not me.vertices:
            continue
        xs = [v.co.x for v in me.vertices]
        ys = [v.co.y for v in me.vertices]
        zs = [v.co.z for v in me.vertices]
        ext = (max(xs) - min(xs), max(ys) - min(ys))
        # the leaf's face spans its two long local axes; rays go along the short one
        along_x = ext[0] < ext[1]
        lb = bmesh.new()
        lb.from_mesh(me)
        lt = BVHTree.FromBMesh(lb)
        a0, a1 = (min(ys), max(ys)) if along_x else (min(xs), max(xs))
        z0, z1 = min(zs), max(zs)
        holes = total = 0
        u = a0 + 0.03
        while u < a1 - 0.03:
            z = z0 + 0.04
            while z < z1 - 0.04:
                if along_x:
                    p, d = Vector((min(xs) - 0.3, u, z)), Vector((1, 0, 0))
                else:
                    p, d = Vector((u, min(ys) - 0.3, z)), Vector((0, 1, 0))
                total += 1
                if lt.ray_cast(p, d, 1.0)[0] is None:
                    holes += 1
                z += 0.05
            u += 0.05
        mats = me.materials
        glass = {m.name for k, m in b.mats.items() if "glass" in k}
        open_edges = 0
        for e in lb.edges:
            if e.is_boundary:
                f = e.link_faces[0]
                mn = mats[f.material_index].name if f.material_index < len(mats) and mats[f.material_index] else ""
                if mn not in glass:
                    open_edges += 1
        lb.free()
        if holes or open_edges:
            res["doors"].append({"door": o.name, "holes": holes, "of": total, "open_edges": open_edges})
    res["ok"] = not (res["leaks"] or res["clips"] or res["doors"])
    return res
