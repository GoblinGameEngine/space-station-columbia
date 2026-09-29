#!/usr/bin/env python3
"""
placement.py -- the map's placement manifest for the remake buildings.

  python3 remake/tools/placement.py      -> godot_project/remake/placement.json

Joins remake/inventory/map_inventory.json (where everything stands on the ring: arc position s,
axial position x, facing) with the built glbs (godot_project/remake/buildings/<ID>.glb) and writes
one entry per placeable structure:

  {"id", "kind", "settlement", "glb", "s", "x", "yaw", "min": [x, y, z], "max": [x, y, z],
   "fmin": [x, z], "fmax": [x, z]}      (fmin/fmax: the massing footprint, from the LOD2)

yaw (radians) turns the building about the floor's up axis so its front (glb local -z, Blender +y)
faces the right way: forward on the ring is +s, right is +x, so a front pointing along (ds, dx)
needs yaw = atan2(-dx, ds) (RingCoords.place_on_ring's convention).  min/max are the merged
visual mesh's bounds in the glb's own frame (Godot axes; y up, foundations reach below 0): the
placer samples the terrain over that footprint and far-away stand-ins use it as their box.

Structures come from the settlements' inventory entries (front = the side facing their front_edge),
farmsteads from their exported parts (the house faces away from the barn, everything else faces the
house), crossings from their road ends (the road runs along the glb's local forward axis).
Entries whose glb isn't built yet are listed on stderr and skipped.
"""
import json
import math
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INV = os.path.join(ROOT, "remake", "inventory", "map_inventory.json")
CINV = os.path.join(ROOT, "remake", "inventory", "coastal_inventory.json")
BLD = os.path.join(ROOT, "godot_project", "remake", "buildings")
OUT = os.path.join(ROOT, "godot_project", "remake", "placement.json")


# the Pruett slice was modelled before the catalog, under its own names: inventory id -> its glbs
# (several share a lot side by side along the front)
ALIAS = {"P-001": ["P-STORE", "P-TAVERN"], "P-002": ["P-CHURCH"], "P-003": ["P-PO"], "P-004": ["P-HOUSE1"],
         "P-005": ["P-HOUSE2"], "P-006": ["P-HOUSE3"], "P-007": ["P-HOUSE4"], "P-008": ["P-ELEV"], "P-009": ["P-DEPOT"]}


def glb_bounds(path, any_mesh=False):
    """Bounds of the *_visual mesh (union of its primitives' POSITION accessors), glb frame; with
    any_mesh, of every mesh (a .lod2.glb's single massing mesh)."""
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack("<I", data[12:16])[0]
    j = json.loads(data[20:20 + n])
    lo, hi = [1e9] * 3, [-1e9] * 3
    for node in j["nodes"]:
        if "mesh" not in node or not (any_mesh or node.get("name", "").endswith("_visual")):
            continue
        t = node.get("translation", [0, 0, 0])
        for prim in j["meshes"][node["mesh"]]["primitives"]:
            acc = j["accessors"][prim["attributes"]["POSITION"]]
            for k in range(3):
                lo[k] = min(lo[k], acc["min"][k] + t[k])
                hi[k] = max(hi[k], acc["max"][k] + t[k])
    return (lo, hi) if lo[0] < 1e9 else None


def yaw_facing(ds, dx):
    return math.atan2(-dx, ds)


def road_heading(s, x, reach=15.0):
    """(ds, dx) along the road nearest (s, x), from remake/terrain.json -- for a crossing whose ends
    don't give its road's direction (a culvert, a span of 0: both ends at one point)."""
    ter = road_heading.ter
    if ter is None:
        ter = road_heading.ter = json.load(open(os.path.join(ROOT, "godot_project", "remake", "terrain.json")))
    C = 2 * math.pi * ter["R"]
    wrap = lambda d: (d + C / 2) % C - C / 2
    best, hd = reach, None
    for rd in ter["roads"]:
        pts = rd["pts"]
        for a, b in zip(pts, pts[1:]):
            bs, bx = wrap(b[0] - a[0]), b[1] - a[1]
            ps, px = wrap(s - a[0]), x - a[1]
            l2 = bs * bs + bx * bx
            if l2 < 1e-9:
                continue
            t = max(0.0, min(1.0, (ps * bs + px * bx) / l2))
            d = math.hypot(ps - bs * t, px - bx * t)
            if d < best:
                best, hd = d, (bs, bx)
    return hd


road_heading.ter = None


ROAD_MARGIN = 1.0      # m past a carriageway's edge a building must stand (the shoulder and a little)
MAX_SHIFT = 30.0


def clear_of_roads(out):
    """A building standing in a road's carriageway (the map's roads and lots come from different
    passes and sometimes overlap) is moved straight back from that road until it's ROAD_MARGIN
    clear -- the least change that gets it out of the way.  Crossings are on their roads by design."""
    ter = json.load(open(os.path.join(ROOT, "godot_project", "remake", "terrain.json")))
    C = 2 * math.pi * ter["R"]
    wrap = lambda d: (d + C / 2) % C - C / 2
    G = 50.0
    grid = {}
    segs = []
    for rd in ter["roads"]:
        pts = rd["pts"]
        for a, b in zip(pts, pts[1:]):
            ds, dx = wrap(b[0] - a[0]), b[1] - a[1]
            L = math.hypot(ds, dx)
            if L < 1e-6:
                continue
            k = len(segs)
            segs.append((a[0] % C, a[1], ds / L, dx / L, L, rd["w"] * 0.5))
            for t in range(0, int(L // G) + 2):
                u = min(t * G, L)
                cs, cx = int(((a[0] + ds / L * u) % C) // G), int((a[1] + dx / L * u) // G)
                for i in (-1, 0, 1):
                    for j in (-1, 0, 1):
                        grid.setdefault(((cs + i) % int(C // G + 1), cx + j), set()).add(k)

    def corners(e):
        c, sn = math.cos(e["yaw"]), math.sin(e["yaw"])
        return [(e["s"] + lx * sn - lz * c, e["x"] + lx * c + lz * sn)
                for lx in (e["min"][0], e["max"][0]) for lz in (e["min"][2], e["max"][2])]
    moved, stuck = 0, []
    for e in out:
        if e["kind"] == "crossing" or e.get("over_water"):
            continue
        home = (e["s"], e["x"])
        total = 0.0
        for it in range(6):
            cs = corners(e)
            reach = max(math.hypot(p[0] - e["s"], p[1] - e["x"]) for p in cs)
            best = None
            keys = set()
            for p in cs + [(e["s"], e["x"])]:
                keys |= grid.get((int((p[0] % C) // G), int(p[1] // G)), set())
            for k in keys:
                sa, xa, ts, tx, L, hw = segs[k]
                ns, nx = -tx, ts
                us = [wrap(p[0] - sa) * ts + (p[1] - xa) * tx for p in cs]
                if max(us) < -hw or min(us) > L + hw:
                    continue                                     # beside the segment, not along it
                vs = [wrap(p[0] - sa) * ns + (p[1] - xa) * nx for p in cs]
                lim = hw + ROAD_MARGIN
                if max(vs) < -lim or min(vs) > lim:
                    continue
                vc = wrap(e["s"] - sa) * ns + (e["x"] - xa) * nx
                shift = (lim - min(vs)) if vc >= 0 else -(max(vs) + lim)
                if best is None or abs(shift) > abs(best[0]):
                    best = (shift, ns, nx)
            if best is None:
                break
            shift, ns, nx = best
            e["s"] = round((e["s"] + ns * shift) % C, 2)
            e["x"] = round(e["x"] + nx * shift, 2)
            total += abs(shift)
            if total > MAX_SHIFT:
                break
        if total > MAX_SHIFT:
            # streets on more than one side of it: no short move clears them all.  It's left out
            # (a road through it is worse than its absence).
            e["s"], e["x"] = home
            stuck.append(e["id"])
        elif total > 0:
            moved += 1
    out[:] = [e for e in out if e["id"] not in stuck]
    print("buildings moved clear of roads: %d%s" % (moved, ("; standing across streets, left out: " + " ".join(stuck)) if stuck else ""))


CAR_CLEAR = 1.25       # m either side of a road's centreline a car needs to get by (half its width and a little)
def snap_crossings(out):
    """Each crossing onto the line it carries (a road; the railway for a RAIL- crossing): its deck's
    two ends on that line's centreline -- the model centred between them and turned along them --
    so the road runs straight on at both ends, not beside the bridge or across its parapet."""
    ter = json.load(open(os.path.join(ROOT, "godot_project", "remake", "terrain.json")))
    C = 2 * math.pi * ter["R"]
    wrap = lambda d: (d + C / 2) % C - C / 2
    lines = [(rd["pts"], False) for rd in ter["roads"]] + [(ter["rail"]["pts"], True)]
    moved = 0
    ends = []
    for e in out:
        if e["kind"] != "crossing" or "deck" not in e:
            continue
        rail = e["id"].startswith("RAIL-")
        best = None
        for pts, is_rail in lines:
            if is_rail != rail:
                continue
            u = 0.0
            for a, b in zip(pts, pts[1:]):
                ds, dx = wrap(b[0] - a[0]), b[1] - a[1]
                L = math.hypot(ds, dx)
                if L < 1e-6:
                    continue
                if abs(wrap(a[0] - e["s"])) < 400 and abs(a[1] - e["x"]) < 400:
                    t = max(0.0, min(1.0, (wrap(e["s"] - a[0]) * ds + (e["x"] - a[1]) * dx) / (L * L)))
                    d = math.hypot(wrap(e["s"] - a[0]) - ds * t, (e["x"] - a[1]) - dx * t)
                    if best is None or d < best[0]:
                        best = (d, pts, u + L * t)
                u += L
        if best is None or best[0] > 25.0:
            continue
        _, pts, u0 = best
        total = sum(math.hypot(wrap(b[0] - a[0]), b[1] - a[1]) for a, b in zip(pts, pts[1:]))
        if u0 - e["deck"][0] * 0.5 < 2.0 or u0 + e["deck"][0] * 0.5 > total - 2.0:
            ends.append(e["id"])                           # at a road's very end: a bridge to nowhere
            continue

        def at(u):
            acc = 0.0
            for a, b in zip(pts, pts[1:]):
                ds, dx = wrap(b[0] - a[0]), b[1] - a[1]
                L = math.hypot(ds, dx)
                if acc + L >= u or b is pts[-1]:
                    t = (u - acc) / L if L > 1e-9 else 0.0
                    return (a[0] + ds * t, a[1] + dx * t)
                acc += L
            return tuple(pts[-1])
        half = e["deck"][0] * 0.5
        A, B = at(max(0.0, u0 - half)), at(u0 + half)
        ds, dx = wrap(B[0] - A[0]), B[1] - A[1]
        if math.hypot(ds, dx) < 0.5:
            continue
        # the footprint's middle across (lx) is where the deck's centre line runs
        yaw = yaw_facing(ds, dx)
        c, sn = math.cos(yaw), math.sin(yaw)
        lx = (e["fmin"][0] + e["fmax"][0]) * 0.5
        ms, mx = A[0] + ds * 0.5, A[1] + dx * 0.5
        ns, nx = (ms - lx * sn) % C, mx - lx * c
        if math.hypot(wrap(ns - e["s"]), nx - e["x"]) > 0.02 or abs(wrap(yaw - e["yaw"])) > 1e-3:
            moved += 1
        e["s"], e["x"], e["yaw"] = round(ns, 2), round(nx, 2), round(yaw, 4)
    out[:] = [e for e in out if e["id"] not in ends]
    print("crossings set onto their roads: %d%s" % (moved, ("; at a road's end, left out: " + " ".join(ends)) if ends else ""))
    # a road that bends on a bridge is eased straight across it: its points over the deck and the
    # approach slabs onto the bridge's axis, and back to the road's own line over the next EASE m
    EASE = 15.0
    eased = 0
    for e in out:
        if e["kind"] != "crossing" or "deck" not in e or e["id"].startswith("RAIL-"):
            continue
        c, sn = math.cos(e["yaw"]), math.sin(e["yaw"])
        lx = (e["fmin"][0] + e["fmax"][0]) * 0.5
        reach = max(abs(e["fmin"][1]), abs(e["fmax"][1]))       # the deck and its approach slabs

        def seg_d(rd):
            best = 1e9
            for a, b in zip(rd["pts"], rd["pts"][1:]):
                if abs(wrap(a[0] - e["s"])) > 300 or abs(a[1] - e["x"]) > 300:
                    continue
                bs, bx = wrap(b[0] - a[0]), b[1] - a[1]
                ps, px = wrap(e["s"] - a[0]), e["x"] - a[1]
                l2 = bs * bs + bx * bx
                t = 0.0 if l2 < 1e-9 else max(0.0, min(1.0, (ps * bs + px * bx) / l2))
                best = min(best, math.hypot(ps - bs * t, px - bx * t))
            return best
        own = min(ter["roads"], key=seg_d)                      # (only the road it carries)
        for rd in [own]:
            pts = rd["pts"]
            hit = False
            for k, p_ in enumerate(pts):
                ds, dx = wrap(p_[0] - e["s"]), p_[1] - e["x"]
                if abs(ds) > reach + EASE + 5 or abs(dx) > reach + EASE + 5:
                    continue
                plx = dx * c + ds * sn - lx                          # across the bridge
                plz = dx * sn - ds * c                              # along it
                if abs(plx) > 6.0 or abs(plz) > reach + EASE:
                    continue
                w = 1.0 if abs(plz) <= reach else 0.5 + 0.5 * math.cos(math.pi * (abs(plz) - reach) / EASE)
                if abs(plx) * w < 0.02:
                    continue
                # move it across by -plx * w (local x in (s, x): (sn, c))
                p_[0] = round(p_[0] - sn * plx * w, 2)
                p_[1] = round(p_[1] - c * plx * w, 2)
                hit = True
            eased += hit
    json.dump(ter, open(os.path.join(ROOT, "godot_project", "remake", "terrain.json"), "w"), indent=0)
    print("roads eased straight across their bridges:", eased)


def crossing_deck(model, inv):
    """(length, width) m of a crossing model's bridge proper -- its deck between the abutments, not the
    approach slabs -- as remake/blender/gen/bridges.py builds it (the same formula)."""
    FT = 0.3048
    clamp = lambda v, lo, hi: max(lo, min(hi, v))
    rp = os.path.join(ROOT, "remake", "catalog", model + ".json")
    tr = (json.load(open(rp)).get("traits") or {}) if os.path.exists(rp) else {}
    ic = next((c for c in inv["crossings"] if c["id"] == model), {})
    spans = int(clamp(tr.get("model_spans") or tr.get("spans") or 1, 1, 14))
    span_each = (tr.get("span_ft") or 40) * FT
    total = clamp(ic.get("span_m") or span_each * spans, 3.0, 120.0)
    road = ic.get("road_class", "county")
    width = (tr.get("width_ft") or 0) * FT or {"hwy": 9.0, "county": 7.0, "main": 10.0, "street": 8.0, "gravel": 5.5,
                                                "rail": 4.2}.get(road, 7.0)
    return total, clamp(width, 4.0, 12.0)


RANK = {"hwy": 6, "main": 5, "county": 4, "street": 3, "gravel": 2, "alley": 1, "rail": 0}


def drop_overlapping_crossings(out, inv_by_id):
    """Two crossings whose footprints overlap (two roads meeting over a creek, or one road's crossing
    listed twice) would stand each in the other's road: keep the one on the greater road (the bigger,
    between equals); the other's road crosses on a culvert under the graded roadway instead."""
    C = 2 * math.pi * 3000.0
    wrap = lambda d: (d + C / 2) % C - C / 2

    def corners(e):
        c, sn = math.cos(e["yaw"]), math.sin(e["yaw"])
        return [(e["s"] + lx * sn - lz * c, e["x"] + lx * c + lz * sn)
                for lx in (e["min"][0], e["max"][0]) for lz in (e["min"][2], e["max"][2])]

    def overlap(a, b):
        ca = corners(a)
        cb = [(a["s"] + wrap(p[0] - a["s"]), p[1]) for p in corners(b)]
        for e in (a, b):
            c, sn = math.cos(e["yaw"]), math.sin(e["yaw"])
            for ax in ((sn, c), (-c, sn)):
                pa = [p[0] * ax[0] + p[1] * ax[1] for p in ca]
                pb = [p[0] * ax[0] + p[1] * ax[1] for p in cb]
                if max(pa) < min(pb) or max(pb) < min(pa):
                    return False
        return True

    def weight(e):
        cr = inv_by_id.get(e["id"], {})
        area = (e["max"][0] - e["min"][0]) * (e["max"][2] - e["min"][2])
        return (RANK.get(cr.get("road_class"), 0), area)
    cross = [e for e in out if e["kind"] == "crossing"]
    gone = set()
    for i, a in enumerate(cross):
        for b in cross[i + 1:]:
            if a["id"] in gone or b["id"] in gone:
                continue
            if abs(wrap(a["s"] - b["s"])) < 100 and abs(a["x"] - b["x"]) < 100 and overlap(a, b):
                lose = b if weight(a) >= weight(b) else a
                gone.add(lose["id"])
                print("crossing %s overlaps %s: %s left out" % (a["id"], b["id"], lose["id"]))
    # a crossing whose model reaches into another road's middle (where two roads part or meet at a
    # creek): that road couldn't get past it -- left out, the road it carried crossing on a culvert
    ter = json.load(open(os.path.join(ROOT, "godot_project", "remake", "terrain.json")))
    segs = []
    for ri, rd in enumerate(ter["roads"]):
        for p0, p1 in zip(rd["pts"], rd["pts"][1:]):
            ds, dx = wrap(p1[0] - p0[0]), p1[1] - p0[1]
            L = math.hypot(ds, dx)
            if L > 1e-6:
                segs.append((ri, p0[0], p0[1], ds / L, dx / L, L))

    def seg_d(s_, x_, g):
        _, sa, xa, ts, tx, L = g
        u = max(0.0, min(L, wrap(s_ - sa) * ts + (x_ - xa) * tx))
        return math.hypot(wrap(s_ - sa) - ts * u, (x_ - xa) - tx * u)
    for e in cross:
        if e["id"] in gone:
            continue
        near = [g for g in segs if abs(wrap(g[1] - e["s"])) < 150 and abs(g[2] - e["x"]) < 150]
        if not near:
            continue
        own = min(near, key=lambda g: seg_d(e["s"], e["x"], g))[0]
        cs = corners(e)
        for g in near:
            if g[0] == own:
                continue
            _, sa, xa, ts, tx, L = g
            us = [wrap(p[0] - sa) * ts + (p[1] - xa) * tx for p in cs]
            vs = [wrap(p[0] - sa) * -tx + (p[1] - xa) * ts for p in cs]
            if max(us) < 0 or min(us) > L or max(vs) < -CAR_CLEAR or min(vs) > CAR_CLEAR:
                continue
            gone.add(e["id"])
            print("crossing %s stands in road %d's way: left out" % (e["id"], g[0]))
            break
    # a small crossing on a great bridge's line (the inventory can give the bank the same creek's
    # crossing too): the great bridge carries the road there
    bpath = os.path.join(ROOT, "godot_project", "remake", "bridges.json")
    for br in (json.load(open(bpath))["bridges"] if os.path.exists(bpath) else []):
        (sa, xa), (sb, xb) = br["ends"]
        ds, dx = wrap(sb - sa), xb - xa
        L = math.hypot(ds, dx)
        for e in cross:
            if e["id"] in gone:
                continue
            vs, vx = wrap(e["s"] - sa), e["x"] - xa
            u = (vs * ds + vx * dx) / L
            lat = abs(vs * dx - vx * ds) / L
            if -60.0 < u < L + 60.0 and lat < 25.0:
                gone.add(e["id"])
                print("crossing %s is on great bridge %s: left out" % (e["id"], br["id"]))
    out[:] = [e for e in out if e["id"] not in gone]


def main():
    inv = json.load(open(INV))
    out, missing = [], []

    def add(rid, kind, settlement, s, x, yaw):
        if rid in ALIAS:
            names = ALIAS[rid]
            bounds = [glb_bounds(os.path.join(BLD, f"{n}.glb")) for n in names]
            widths = [b[1][0] - b[0][0] + 1.0 for b in bounds]
            # side by side along the building's local x (right turns to (cos yaw, sin yaw) in (x, s))
            off = -sum(widths) / 2
            for n, w in zip(names, widths):
                c = off + w / 2
                off += w
                _add(n, kind, settlement, s + math.sin(yaw) * c, x + math.cos(yaw) * c, yaw)
            return
        _add(rid, kind, settlement, s, x, yaw)

    def _add(rid, kind, settlement, s, x, yaw, model=None):
        # model: the glb it uses when that's another structure's (a crossing reusing an existing
        # bridge on the expanded map); the entry keeps its own id
        glb = os.path.join(BLD, f"{model or rid}.glb")
        if not os.path.exists(glb):
            missing.append(rid)
            return
        b = glb_bounds(glb)
        if b is None:
            missing.append(rid + " (no _visual mesh)")
            return
        # the footprint the building stands on: its massing (LOD2, no yard props), else the visual bounds
        lod2 = os.path.join(BLD, f"{model or rid}.lod2.glb")
        f = glb_bounds(lod2, any_mesh=True) if os.path.exists(lod2) else None
        f = f or b
        out.append({"id": rid, "kind": kind, "settlement": settlement, "glb": f"res://remake/buildings/{model or rid}.glb",
                    "model": model or rid,
                    "s": round(s, 2), "x": round(x, 2), "yaw": round(yaw, 4),
                    "min": [round(v, 2) for v in b[0]], "max": [round(v, 2) for v in b[1]],
                    "fmin": [round(f[0][0], 2), round(f[0][2], 2)], "fmax": [round(f[1][0], 2), round(f[1][2], 2)]})

    for st in inv["structures"]:
        (a0, a1), (b0, b1) = st["front_edge"] if st.get("front_edge") else ((st["s"], st["x"]), (st["s"], st["x"] + 1))
        fs, fx = (a0 + b0) / 2 - st["s"], (a1 + b1) / 2 - st["x"]
        add(st["id"], st["kind"], st["settlement"], st["s"], st["x"], yaw_facing(fs, fx))

    # the coast's new communities (tools/map_expanded.py --coastal-inventory); over-water ones stand on
    # the pier deck (the placer puts them on the water level + the deck height, not on the bed)
    cinv = json.load(open(CINV)) if os.path.exists(CINV) else {"structures": []}
    for st in cinv["structures"]:
        (a0, a1), (b0, b1) = st["front_edge"] if st.get("front_edge") else ((st["s"], st["x"]), (st["s"], st["x"] + 1))
        fs, fx = (a0 + b0) / 2 - st["s"], (a1 + b1) / 2 - st["x"]
        n = len(out)
        add(st["id"], st["kind"], st["settlement"], st["s"], st["x"], yaw_facing(fs, fx))
        if st.get("over_water") and len(out) > n:
            out[-1]["over_water"] = True

    for fm in inv["farmsteads"]:
        parts = {p["part"]: p for p in fm.get("parts", [])}
        house = parts.get("house")
        for name, p in parts.items():
            if name == "house":
                barn = parts.get("barn") or p
                ds, dx = p["s"] - barn["s"], p["x"] - barn["x"]
            else:
                ds, dx = house["s"] - p["s"], house["x"] - p["x"]
            add(f"{fm['id']}-{name}", "farm", None, p["s"], p["x"], yaw_facing(ds, dx) if (ds or dx) else 0.0)

    for c in inv["crossings"]:
        (as_, ax), (bs, bx) = c.get("ends") or ((c["s"], c["x"]), (c["s"], c["x"]))
        if c.get("model", c["id"]) is None:
            missing.append(c["id"] + " (no model yet)")
            continue
        # the road runs along the model's local forward axis: the ends give it, or (a culvert, a span
        # of 0 -- both ends at one point) the road it's on
        hd = (bs - as_, bx - ax)
        if math.hypot(*hd) < 0.5:
            hd = road_heading(c["s"], c["x"]) or (1.0, 0.0)
        _add(c["id"], "crossing", None, c["s"], c["x"], yaw_facing(*hd), c.get("model"))
        if out and out[-1]["id"] == c["id"]:
            dl, dw = crossing_deck(c.get("model") or c["id"], inv)
            e_ = out[-1]
            # (no longer than the model as built: some older models are shorter than their record says)
            dl = min(dl, e_["fmax"][1] - e_["fmin"][1])
            e_["deck"] = [round(dl, 2), round(dw, 2)]

    snap_crossings(out)
    drop_overlapping_crossings(out, {c["id"]: c for c in inv["crossings"]})
    clear_of_roads(out)
    with open(OUT, "w") as f:
        json.dump({"structures": out}, f, indent=0)
    # the walks (boardwalks, piers, docks, wharves, breakwaters, promenades...): CoastalWalks builds
    # them in the game along their map lines; their record's traits say how
    walks = []
    for w in cinv.get("walks", []):
        rp = os.path.join(ROOT, "remake", "catalog", w["id"] + ".json")
        tr = json.load(open(rp)).get("traits", {}) if os.path.exists(rp) else {}
        walks.append({"id": w["id"], "kind": w["kind"], "settlement": w["settlement"], "w": w.get("width_m") or tr.get("width_m") or 4,
                      "pts": w.get("pts"), "rect": [w["s"], w["x"], w["w"], w["d"]] if "pts" not in w else None,
                      "traits": {k: tr.get(k) for k in ("deck", "substructure", "rail", "lighting", "benches", "pile_depth_m")}})
    with open(os.path.join(ROOT, "godot_project", "remake", "walks.json"), "w") as f:
        json.dump({"walks": walks}, f, indent=0)
    print(f"walks: {len(walks)}")
    # the great bridges (XBR / XRR records): GreatBridges builds them in the game between the crossing's
    # ends (the map inventory's MAJOR / RAIL crossing at the same place), approaches ramped over the basin
    bridges = []
    for br in cinv.get("bridges", []):
        rp = os.path.join(ROOT, "remake", "catalog", br["id"] + ".json")
        if not os.path.exists(rp):
            continue
        rec = json.load(open(rp))
        cr = min((c for c in inv["crossings"] if c["type"] in ("major", "rail")),
                 key=lambda c: math.hypot(c["s"] - br["s"], c["x"] - br["x"]))
        bridges.append({"id": br["id"], "road_class": br.get("road_class"), "over": br.get("over"), "ends": cr["ends"],
                        "name": (rec.get("names") or {}).get("name"), "traits": rec.get("traits", {})})
    with open(os.path.join(ROOT, "godot_project", "remake", "bridges.json"), "w") as f:
        json.dump({"bridges": bridges}, f, indent=1)
    print(f"bridges: {len(bridges)}")
    print(f"placement: {len(out)} placed -> {OUT}")
    if missing:
        print(f"not built ({len(missing)}): {' '.join(missing)}", file=sys.stderr)


if __name__ == "__main__":
    main()
