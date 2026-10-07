#!/usr/bin/env python3
"""where.py -- where everything is on the map, from the data alone: no game, no rendering (the user, 2026-10-06:
"tools for you to know precisely where models are without having to render it visually ... very quickly do checks").

Reads what the game reads: remake/placement.json (every structure: its id, kind, place, turn and footprint),
terrain.json (roads, areas, islands; the 8 m height / water rasters), landcover.png, aerostats.json,
groundcars.json, transit.json. Map terms throughout: s (m round the ring), x (m along the axis, - is north),
h (m above the sea-level datum).

    python3 tools/where.py find TEXT              structures, vehicles, roads, towns, islands, stops whose name has TEXT
    python3 tools/where.py near S X [R]           everything within R m (default 60), nearest first, with bearings
    python3 tools/where.py ground S X             height, water, land cover, area, road under / nearest, town, island
    python3 tools/where.py check [S X R]          problems (the whole world without S X R): structures on a road, in
                                                  water or overlapping; parked vehicles on a road, in a building or water
    python3 tools/where.py town NAME              a settlement's extent, its structures by kind, its roads

The game's own answer, live (drawn bounds, LOD state, what the camera sees): tools/gcmd.py query ...
(scripts/autoload/WorldQuery.gd).
"""
import gzip
import json
import math
import os
import sys
from collections import Counter, defaultdict

GD = os.environ.get("WHERE_GD") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "godot_project", "remake")   # (WHERE_GD: another copy of the data, e.g. an old commit's)
CELL = 50.0
LC = ["grass", "built-up", "meadow", "woods", "field", "grove", "beach", "rock"]
ISLANDS_FALLBACK = [("Gannet Island", -1, 0.05, -8560.0), ("Rook Island", -1, 0.383, -8560.0), ("Thistle Island", -1, 0.717, -8560.0),
                    ("Isla Serena", 1, 0.217, 8560.0), ("Isla Palmar", 1, 0.55, 8560.0), ("Cayo Luna", 1, 0.883, 8560.0)]


class World:
    def __init__(self):
        self.ter = json.load(open(os.path.join(GD, "terrain.json")))
        self.R = self.ter["R"]
        self.C = 2 * math.pi * self.R
        self.HW = self.ter["W"] / 2
        self.st = json.load(open(os.path.join(GD, "placement.json")))["structures"]
        self.by_id = {e["id"]: e for e in self.st}
        self.parked = []
        for fn, key, cat in (("aerostats.json", "aerostats", "aerostat"), ("groundcars.json", "groundcars", "ground vehicle")):
            p = os.path.join(GD, fn)
            if os.path.exists(p):
                for v in json.load(open(p))[key]:
                    self.parked.append({"id": v["id"], "cat": cat, "kind": v.get("kind", cat), "s": v["s"], "x": v["x"],
                                        "yaw": v.get("yaw", 0.0), "where": v.get("where", "")})
        self.islands = self.ter.get("islands") or [{"name": n, "side": sg, "s": f * self.C, "x": x, "half_s": 1700.0, "half_x": 1050.0}
                                                   for n, sg, f, x in ISLANDS_FALLBACK]
        tp = os.path.join(GD, "transit.json")
        self.stops = []
        if os.path.exists(tp):
            for l in json.load(open(tp))["lines"]:
                for sp in l.get("stops", []):
                    if "s" in sp:
                        self.stops.append({"name": sp["name"], "line": l["name"], "s": sp["s"], "x": sp["x"]})
        wp = os.path.join(GD, "walks.json")
        self.walks = json.load(open(wp))["walks"] if os.path.exists(wp) else []
        self._cat = {}
        self._rasters = None
        self._lc = None
        # spatial grids
        self.sgrid = defaultdict(list)
        for e in self.st:
            for c in self._cells(e["s"], e["x"], 30.0):
                self.sgrid[c].append(e)
        self.rgrid = defaultdict(list)
        for ri, rd in enumerate(self.ter["roads"]):
            hw = max(rd.get("hl", rd["w"] / 2), rd.get("hr", rd["w"] / 2))
            pts = rd["pts"]
            for a, b in zip(pts, pts[1:]):
                for c in self._cells((a[0] + b[0]) / 2 if abs(b[0] - a[0]) < self.C / 2 else a[0], (a[1] + b[1]) / 2,
                                     math.hypot(self.wrap(b[0] - a[0]), b[1] - a[1]) / 2 + hw + 2):
                    self.rgrid[c].append((a, b, hw, rd.get("name", ""), rd["cls"], ri))
        rail = self.ter.get("rail", {}).get("pts", [])
        for a, b in zip(rail, rail[1:]):
            for c in self._cells(a[0], a[1], 12.0):
                self.rgrid[c].append((a, b, 3.0, "the Ring Line", "rail", -1))

    def wrap(self, d):
        return (d + self.C / 2) % self.C - self.C / 2

    def dist(self, s0, x0, s1, x1):
        return math.hypot(self.wrap(s1 - s0), x1 - x0)

    def bearing(self, s0, x0, s1, x1):
        return math.degrees(math.atan2(self.wrap(s1 - s0), -(x1 - x0))) % 360.0     # north (-x) 0, east (+s) 90

    def _cells(self, s, x, r):
        n = int(math.ceil(self.C / CELL))
        for i in range(int(math.floor((s - r) / CELL)), int(math.floor((s + r) / CELL)) + 1):
            for j in range(int(math.floor((x - r) / CELL)), int(math.floor((x + r) / CELL)) + 1):
                yield (i % n, j)

    # --- the ground
    def rasters(self):
        if self._rasters is None:
            import numpy as np
            rs = self.ter["raster"]
            ny, nx = rs["ny"], rs["nx"]
            load = lambda f: np.frombuffer(gzip.open(os.path.join(GD, rs[f])).read(), np.float16).reshape(ny, nx)
            self._rasters = (rs, load("base"), load("level"), load("depth"))
        return self._rasters

    def _rc(self, s, x):
        rs = self.rasters()[0]
        i = int((s % self.C) / rs["step_m"]) % rs["nx"]
        j = min(rs["ny"] - 1, max(0, int((x - rs["x0"]) / rs["step_m"])))
        return j, i

    def height(self, s, x):
        """(ground h, water level or None, water depth) from the rasters (8 m; the game grades roads finer)"""
        rs, base, lvl, dep = self.rasters()
        j, i = self._rc(s, x)
        lv = float(lvl[j, i])
        return float(base[j, i]) - float(dep[j, i]), (lv if lv > -9000 else None), float(dep[j, i])

    def landcover(self, s, x):
        if self._lc is None:
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = None
            import numpy as np
            self._lc = np.asarray(Image.open(os.path.join(GD, "landcover.png")))
        st = self.ter.get("landcover_step_m", self.ter["raster"]["step_m"])
        i = int((s % self.C) / st) % self._lc.shape[1]
        j = min(self._lc.shape[0] - 1, max(0, int((x + self.HW) / st)))
        return int(self._lc[j, i, 0]), int(self._lc[j, i, 1])

    def roads_near(self, s, x, r=CELL):
        """[(distance from the centreline, half width, name, cls)] nearest first"""
        out = {}
        for c in self._cells(s, x, r):
            for a, b, hw, name, cls, ri in self.rgrid.get(c, ()):
                bs, bx = self.wrap(b[0] - a[0]), b[1] - a[1]
                ps, px = self.wrap(s - a[0]), x - a[1]
                L2 = bs * bs + bx * bx or 1e-9
                t = max(0.0, min(1.0, (ps * bs + px * bx) / L2))
                d = math.hypot(ps - bs * t, px - bx * t)
                k = (ri, name)
                if d <= r and (k not in out or d < out[k][0]):
                    out[k] = (d, hw, name, cls)
        return sorted(out.values())

    def area_at(self, s, x):
        for a in self.ter["areas"]:
            if point_in(self, (s, x), a["poly"]):
                return "%s (%s)" % (a["kind"], a.get("town", ""))
        return None

    def island_at(self, s, x):
        for il in self.islands:
            if (self.wrap(s - il["s"]) / il["half_s"]) ** 2 + ((x - il["x"]) / il["half_x"]) ** 2 <= 1.0:
                return il["name"]
        return None

    # --- the structures
    def footprint(self, e, shrink=0.0):
        c, sn = math.cos(e["yaw"]), math.sin(e["yaw"])
        fmin, fmax = e.get("fmin", e.get("min")), e.get("fmax", e.get("max"))
        zi = 1 if len(fmin) == 2 else 2
        pts = []
        for lx, lz in ((fmin[0] + shrink, fmin[zi] + shrink), (fmax[0] - shrink, fmin[zi] + shrink),
                       (fmax[0] - shrink, fmax[zi] - shrink), (fmin[0] + shrink, fmax[zi] - shrink)):
            pts.append((e["s"] + lx * sn - lz * c, e["x"] + lx * c + lz * sn))
        return pts

    def structures_near(self, s, x, r):
        seen = {}
        for c in self._cells(s, x, r):
            for e in self.sgrid.get(c, ()):
                d = self.dist(s, x, e["s"], e["x"])
                if d <= r:
                    seen[e["id"]] = (d, e)
        return sorted(seen.values(), key=lambda t: t[0])

    def structure_at(self, s, x, margin=0.0):
        for d, e in self.structures_near(s, x, 60.0):
            if e["kind"] != "crossing" and point_in(self, (s, x), self.footprint(e, -margin)):
                return e
        return None

    def catalog(self, sid):
        """a structure's catalog record (remake/catalog/<id>.json): its traits say if it stands on pilings"""
        if sid not in self._cat:
            p = os.path.join(GD, "..", "..", "remake", "catalog", sid + ".json")
            self._cat[sid] = json.load(open(p)) if os.path.exists(p) else {}
        return self._cat[sid]

    def on_deck(self, s, x, margin=3.0):
        """the pier, wharf, boardwalk or deck (walks.json) under (s, x), if any"""
        for wk in self.walks:
            if wk.get("rect"):                 # [centre s, centre x, length along s, depth along x]
                cs, cx, ls, lx = wk["rect"]
                if abs(self.wrap(s - cs)) <= ls / 2 + margin and abs(x - cx) <= lx / 2 + margin:
                    return wk["id"]
                continue
            pts = wk["pts"]
            for a, b in zip(pts, pts[1:]):
                bs, bx = self.wrap(b[0] - a[0]), b[1] - a[1]
                ps, px = self.wrap(s - a[0]), x - a[1]
                if abs(ps) > abs(bs) + 200 and abs(self.wrap(s - b[0])) > 200:
                    continue
                t = max(0.0, min(1.0, (ps * bs + px * bx) / (bs * bs + bx * bx or 1e-9)))
                if math.hypot(ps - bs * t, px - bx * t) <= wk.get("w", 4) / 2 + margin:
                    return wk["id"]
        return None

    def town_of(self, s, x):
        best, bd = None, 1e18
        for d, e in self.structures_near(s, x, 1500.0):
            if e.get("settlement") and d < bd:
                best, bd = e["settlement"], d
        return best, bd


def point_in(w, q, poly):
    ref = poly[0][0]
    pl = [(ref + w.wrap(p[0] - ref), p[1]) for p in poly]
    qs, qx = ref + w.wrap(q[0] - ref), q[1]
    inside = False
    for (a0, a1), (b0, b1) in zip(pl, pl[1:] + pl[:1]):
        if (a1 > qx) != (b1 > qx) and qs < (b0 - a0) * (qx - a1) / (b1 - a1) + a0:
            inside = not inside
    return inside


def polys_overlap(w, a, b):
    return any(point_in(w, p, b) for p in a) or any(point_in(w, p, a) for p in b)


def describe(w, e):
    return "structure %-10s %-14s %-18s s %8.1f x %8.1f yaw %5.2f  %4.0f x %3.0f m, %4.1f m tall" % (
        e["id"], e["kind"], e.get("settlement") or "", e["s"], e["x"], e["yaw"],
        e["fmax"][0] - e["fmin"][0] if "fmax" in e else 0, e["fmax"][1] - e["fmin"][1] if "fmax" in e else 0,
        e["max"][1] if "max" in e else 0)


# --------------------------------------------------------------------------- the commands
def cmd_find(w, text):
    t = text.lower()
    n = 0
    for e in w.st:
        if t in e["id"].lower() or t == e["kind"].lower():
            print(describe(w, e))
            n += 1
    for v in w.parked:
        if t in v["id"].lower() or t in v["kind"].lower():
            print("%-9s %-24s %-12s s %8.1f x %8.1f (%s)" % (v["cat"], v["id"], v["kind"], v["s"], v["x"], v["where"]))
            n += 1
    names = Counter()
    for rd in w.ter["roads"]:
        nm = rd.get("name", "")
        if nm and t in nm.lower() and names[nm] == 0:
            p = rd["pts"][len(rd["pts"]) // 2]
            print("road      %-24s %-12s mid s %8.1f x %8.1f, %d pts, %.0f m wide" % (nm, rd["cls"], p[0], p[1], len(rd["pts"]), rd["w"]))
            names[nm] += 1
            n += 1
    towns = defaultdict(list)
    for e in w.st:
        if e.get("settlement") and t in e["settlement"].lower():
            towns[e["settlement"]].append(e)
    for nm, es in towns.items():
        ss = [e["s"] for e in es]
        ref = ss[0]
        ss = [ref + w.wrap(v - ref) for v in ss]
        xs = [e["x"] for e in es]
        print("town      %-24s %d structures, s %.0f..%.0f x %.0f..%.0f" % (nm, len(es), min(ss) % w.C, max(ss) % w.C, min(xs), max(xs)))
        n += 1
    for il in w.islands:
        if t in il["name"].lower():
            print("island    %-24s centre s %.1f x %.1f, %.0f x %.0f m" % (il["name"], il["s"], il["x"], 2 * il["half_s"], 2 * il["half_x"]))
            n += 1
    for sp in w.stops:
        if t in sp["name"].lower():
            print("stop      %-30s %-18s s %8.1f x %8.1f" % (sp["name"], sp["line"], sp["s"], sp["x"]))
            n += 1
    if n == 0:
        print("nothing matches '%s'" % text)


def cmd_near(w, s, x, r):
    rows = []
    for d, e in w.structures_near(s, x, r):
        rows.append((d, "%5.0f m @%3.0f deg  %s" % (d, w.bearing(s, x, e["s"], e["x"]), describe(w, e))))
    for v in w.parked:
        d = w.dist(s, x, v["s"], v["x"])
        if d <= r:
            rows.append((d, "%5.0f m @%3.0f deg  %-9s %-24s %-12s s %8.1f x %8.1f" % (d, w.bearing(s, x, v["s"], v["x"]), v["cat"], v["id"], v["kind"], v["s"], v["x"])))
    for sp in w.stops:
        d = w.dist(s, x, sp["s"], sp["x"])
        if d <= r:
            rows.append((d, "%5.0f m @%3.0f deg  stop      %s (%s)" % (d, w.bearing(s, x, sp["s"], sp["x"]), sp["name"], sp["line"])))
    rows.sort()
    print("%d things within %.0f m of s %.1f x %.1f:" % (len(rows), r, s, x))
    for _, line in rows:
        print(line)
    rds = w.roads_near(s, x, r)
    if rds:
        print("roads: " + "; ".join("%s %s %.0f m" % (c, n or "(unnamed)", d) for d, hw, n, c in rds[:8]))


def cmd_ground(w, s, x):
    h, lv, dep = w.height(s, x)
    print("ground at s %.1f x %.1f: h %.2f (8 m raster)" % (s, x, h))
    if lv is not None:
        print("water: level %.2f, %s" % (lv, ("%.2f m deep" % (lv - h)) if lv > h else "dry"))
    cls, g = w.landcover(s, x)
    print("land cover: %s%s" % (LC[cls] if cls < len(LC) else cls, " (crop %d)" % g if cls == 4 else ""))
    print("area: %s" % (w.area_at(s, x) or "-"))
    rds = w.roads_near(s, x)
    if rds:
        d, hw, n, c = rds[0]
        print("road: %s %s, %.1f m from its centreline (half width %.1f) -- %s" % (c, n or "(unnamed)", d, hw, "ON it" if d <= hw else "off it by %.1f m" % (d - hw)))
    else:
        print("road: none within %.0f m" % CELL)
    st = w.structure_at(s, x)
    if st:
        print("inside the footprint of %s" % describe(w, st))
    town, td = w.town_of(s, x)
    print("town: %s" % ("%s (%.0f m to its nearest building)" % (town, td) if town else "none within 1.5 km"))
    il = w.island_at(s, x)
    if il:
        print("island: %s" % il)
    if abs(x) > w.HW:
        print("past the end wall (|x| > %.0f)" % w.HW)


def cmd_check(w, s=None, x=None, r=None):
    if s is None:
        es = [e for e in w.st]
        pv = list(w.parked)
        where = "the whole world"
    else:
        es = [e for d, e in w.structures_near(s, x, r)]
        pv = [v for v in w.parked if w.dist(s, x, v["s"], v["x"]) <= r]
        where = "%.0f m of s %.1f x %.1f" % (r, s, x)
    es = [e for e in es if e["kind"] != "crossing" and "fmin" in e]
    issues = defaultdict(list)
    for e in es:
        fp = w.footprint(e, 0.3)
        roads = set()
        wet = 0
        for p in fp:
            for d, hw, n, c in w.roads_near(p[0], p[1], 30.0):
                if d < hw - 0.3:
                    roads.add("%s %s" % (c, n or "(unnamed)"))
            h, lv, dep = w.height(p[0], p[1])
            if lv is not None and lv > h + 0.05:
                wet += 1
        if roads:
            issues["on a road"].append("%s  on %s" % (describe(w, e), ", ".join(sorted(roads))))
        if wet:
            tr = w.catalog(e["id"]).get("traits", {})
            deck = w.on_deck(e["s"], e["x"])
            if not (tr.get("on_pilings") or tr.get("pile_depth_m")) and not deck:
                issues["in water"].append("%s  %d of 4 corners under water (no pilings, on no pier or wharf)" % (describe(w, e), wet))
    done = set()
    for e in es:
        a = w.footprint(e, 1.0)          # (pulled in 1 m: the drawn bounds take in cornices, awnings and stoops)
        for d, f in w.structures_near(e["s"], e["x"], 80.0):
            if f is e or f["kind"] == "crossing" or "fmin" not in f or (f["id"], e["id"]) in done:
                continue
            done.add((e["id"], f["id"]))
            if polys_overlap(w, a, w.footprint(f, 1.0)):
                depth = 1.0                      # how deep: the most both can be pulled in and still overlap
                for k in (2.0, 3.0, 5.0, 8.0):
                    if polys_overlap(w, w.footprint(e, k), w.footprint(f, k)):
                        depth = k
                issues["overlapping"].append((depth, "%s (%s) and %s (%s): overlap by more than %.0f m" % (e["id"], e["kind"], f["id"], f["kind"], depth)))
    for v in pv:
        rds = w.roads_near(v["s"], v["x"], 20.0)
        if rds and rds[0][0] < rds[0][1] - 2.6 and v["cat"] != "aerostat":     # (the kerb lane, 2.4 m, is parking)
            issues["parked in a traffic lane"].append("%s %s at s %.1f x %.1f: on %s %s" % (v["cat"], v["id"], v["s"], v["x"], rds[0][3], rds[0][2]))
        st = w.structure_at(v["s"], v["x"])
        if st:
            issues["parked in a building"].append("%s %s at s %.1f x %.1f: inside %s (%s)" % (v["cat"], v["id"], v["s"], v["x"], st["id"], st["kind"]))
        h, lv, dep = w.height(v["s"], v["x"])
        if lv is not None and lv > h + 0.2:
            issues["parked in water"].append("%s %s at s %.1f x %.1f: %.1f m deep" % (v["cat"], v["id"], v["s"], v["x"], lv - h))
    for i, a in enumerate(pv):
        for b in pv[i + 1:]:
            if w.dist(a["s"], a["x"], b["s"], b["x"]) < 2.0:
                issues["parked on top of each other"].append("%s and %s" % (a["id"], b["id"]))
    if "overlapping" in issues:
        issues["overlapping"] = [t[1] for t in sorted(issues["overlapping"], key=lambda t: -t[0])]
    total = sum(len(v) for v in issues.values())
    print("checked %d structures and %d parked vehicles in %s: %d problems" % (len(es), len(pv), where, total))
    for k, v in issues.items():
        print("\n%s: %d" % (k.upper(), len(v)))
        for line in v[:40]:
            print("  " + line)
        if len(v) > 40:
            print("  ... %d more" % (len(v) - 40))


def cmd_town(w, name):
    es = [e for e in w.st if (e.get("settlement") or "").lower() == name.lower()]
    if not es:
        print("no settlement '%s' (try: find %s)" % (name, name))
        return
    ref = es[0]["s"]
    ss = [ref + w.wrap(e["s"] - ref) for e in es]
    xs = [e["x"] for e in es]
    print("%s: %d structures, s %.0f..%.0f x %.0f..%.0f (centre s %.0f x %.0f)" % (es[0]["settlement"], len(es), min(ss) % w.C, max(ss) % w.C,
                                                                                min(xs), max(xs), (sum(ss) / len(ss)) % w.C, sum(xs) / len(xs)))
    print("by kind: " + ", ".join("%s %d" % kv for kv in Counter(e["kind"] for e in es).most_common()))
    cs, cx = (sum(ss) / len(ss)) % w.C, sum(xs) / len(xs)
    r = max(max(ss) - min(ss), max(xs) - min(xs)) / 2 + 50
    names = Counter()
    for d, hw, n, c in w.roads_near(cs, cx, r):
        if n:
            names[(c, n)] += 1
    print("roads: " + ", ".join("%s (%s)" % (n, c) for (c, n) in sorted(names)))


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    w = World()
    op = a[0]
    f = lambda i, d=None: float(a[i]) if len(a) > i else d
    if op == "find":
        cmd_find(w, " ".join(a[1:]))
    elif op == "near":
        cmd_near(w, f(1), f(2), f(3, 60.0))
    elif op == "ground":
        cmd_ground(w, f(1), f(2))
    elif op == "check":
        if len(a) >= 3:
            cmd_check(w, f(1), f(2), f(3, 150.0))
        else:
            cmd_check(w)
    elif op == "town":
        cmd_town(w, " ".join(a[1:]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
