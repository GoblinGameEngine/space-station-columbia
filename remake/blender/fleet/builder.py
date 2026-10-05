"""
builder.py -- a road vehicle's body as library components, from its class standard (kit/loft.py) and a style:
the generic form of remake/blender/wagon/carrow_wagon.py (research/vehicles/FLEET_BODIES.md).

THE LOFT GRID. Both shells are the class's lofts: stations along the vehicle x a fixed loop of points round it.
Every panel, opening and reveal is a rectangle of the grid's cells, so neighbours share their vertices exactly:
sealed by construction (cover_check() lists the cells no component took: they must be the openings). Closers
(doors, hatch, lids) are drawn 3 mm in from their apertures on the outside (the shut line), exact inside.

TOKENS. Everything a variation may swap is its own component in its own slot: every panel, pane, closer, reveal,
lining, seat; and the dressing -- lamps, grille, bumpers, mirrors, belt mouldings, inlays and liveries, roof
equipment -- each in a named slot ("lamp/head", "livery/fender", "equipment/roof" ...), never merged into a panel.
A variant (a police car on the sedan) adds or swaps only its tokens and its palette (research/vehicles/TOKENS.md).
"""
import math

from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon

from kit.core import Mesh
from kit import loft as LOFT

TAU = math.tau
GAP = 0.003
SIDES = ("R", "L")
E = LOFT.E


class Builder:
    def __init__(self, loft, M):
        global E
        E = loft.E                                         # (the loft's index map: a high floor reorders the sill and arch)
        self.L = L = loft
        self.M = M
        self.Y = L.stations
        self.YI = L.int_stations
        self.EXT = [L.ext_loop(y) for y in self.Y]
        self.INT = {y: L.int_loop(y) for y in self.YI}
        self.NS_E = len(self.EXT[0]) - 1 if self.EXT else 0
        self.NS_I = LOFT.NI
        self.MODS = {}
        self.MESH = {}
        self.MARKERS = []
        self.CLOSERS = []
        self.USED = {"ext": {}, "int": {}}

    # ------------------------------------------------------------ modules
    def mod(self, mid, role, slot, side, hp=300, mass=8.0, breaks="detach"):
        if mid not in self.MODS:
            self.MODS[mid] = dict(role=role, slot=slot, side=side, hp=hp, mass_kg=mass, breaks=breaks, boxes=[])
            self.MESH[mid] = Mesh(mid, self.M)
        return self.MESH[mid]

    def marker(self, name, loc, rot=0.0):
        self.MARKERS.append((name, tuple(round(c, 4) for c in loc), rot))

    # ------------------------------------------------------------ the loft
    def iy(self, y):
        for i, v in enumerate(self.Y):
            if abs(v - y) < 1e-6:
                return i
        raise KeyError(y)

    def ext_pt(self, i, s):
        x, z = self.EXT[i][s]
        return (x, self.Y[i], z)

    def int_pt(self, y, s):
        x, z = self.INT[y][s % self.NS_I]
        return (x, y, z)

    def loop_at(self, shell, y):
        ys = self.Y if shell == "ext" else self.YI
        for k in range(len(ys) - 1):
            if ys[k + 1] - 1e-9 <= y <= ys[k] + 1e-9:
                a = self.EXT[self.iy(ys[k])] if shell == "ext" else self.INT[ys[k]]
                b = self.EXT[self.iy(ys[k + 1])] if shell == "ext" else self.INT[ys[k + 1]]
                t = 0.0 if ys[k] == ys[k + 1] else (ys[k] - y) / (ys[k] - ys[k + 1])
                return [(xa + (xb - xa) * t, za + (zb - za) * t) for (xa, za), (xb, zb) in zip(a, b)]
        raise ValueError((shell, y))

    def sample(self, shell, y, s):
        lp = self.loop_at(shell, y)
        n = len(lp)
        k = int(math.floor(s))
        f = s - k
        if shell == "ext" and k >= n - 1:
            k, f = n - 2, 1.0
        (xa, za), (xb, zb) = lp[k % n], lp[(k + 1) % n]
        return (xa + (xb - xa) * f, y, za + (zb - za) * f)

    @staticmethod
    def rows_between(ys, y0, y1):
        return [y for y in ys if y1 - 1e-9 <= y <= y0 + 1e-9]

    def cells(self, me, mid, shell, y0, y1, s0, s1, matf, holes=(), outward=True):
        ys = self.Y if shell == "ext" else self.YI
        rs = self.rows_between(ys, y0, y1)
        n = self.NS_E if shell == "ext" else self.NS_I
        for a, b in zip(rs, rs[1:]):
            for s in range(s0, s1):
                sm = s % n
                if any(h[1] - 1e-9 <= b and a <= h[0] + 1e-9 and h[2] <= s and s + 1 <= h[3] for h in holes):
                    continue
                key = (round(a, 4), sm)
                assert key not in self.USED[shell], ("cell used twice", shell, key, self.USED[shell][key], mid)
                self.USED[shell][key] = mid
                if shell == "ext":
                    p = [self.ext_pt(self.iy(a), sm), self.ext_pt(self.iy(b), sm), self.ext_pt(self.iy(b), sm + 1), self.ext_pt(self.iy(a), sm + 1)]
                else:
                    p = [self.int_pt(a, sm), self.int_pt(b, sm), self.int_pt(b, sm + 1), self.int_pt(a, sm + 1)]
                zc = sum(q[2] for q in p) / 4
                me.face(list(reversed(p)) if (shell == "ext") == outward else p, matf(s, (a + b) / 2, zc))

    def cover_check(self):
        out = {}
        for shell, ys, n in (("ext", self.Y, self.NS_E), ("int", self.YI, self.NS_I)):
            out[shell] = [(round(a, 3), s) for a in ys[:-1] for s in range(n) if (round(a, 4), s) not in self.USED[shell]]
        return out

    def rect_ring(self, shell, y0, y1, s0, s1):
        ys = self.Y if shell == "ext" else self.YI
        rs = self.rows_between(ys, y0, y1)
        out = [self.sample(shell, rs[0], s) for s in range(s0, s1)]
        out += [self.sample(shell, y, s1) for y in rs]
        out += [self.sample(shell, rs[-1], s) for s in range(s1 - 1, s0, -1)]
        out += [self.sample(shell, y, s0) for y in reversed(rs[1:])]
        return out

    def patch(self, me, shell, y0, y1, s0, s1, matf, inset=0.0, outward=True, edges=(1, 1, 1, 1), lift=0.0):
        ys = self.Y if shell == "ext" else self.YI
        rs = self.rows_between(ys, y0, y1)
        if inset:
            rs = [y0 - inset * edges[0]] + rs[1:-1] + [y1 + inset * edges[1]]
        grid = []
        for y in rs:
            row = []
            for s in range(s0, s1 + 1):
                sf = float(s)
                if inset and s == s0 and edges[2]:
                    a, b = self.sample(shell, y, s), self.sample(shell, y, s + 1)
                    sf = s + inset / max(1e-6, math.dist(a, b))
                if inset and s == s1 and edges[3]:
                    a, b = self.sample(shell, y, s), self.sample(shell, y, s - 1)
                    sf = s - inset / max(1e-6, math.dist(a, b))
                p = self.sample(shell, y, sf)
                row.append((p[0], p[1], p[2] + lift))
            grid.append(row)
        for r in range(len(grid) - 1):
            for c in range(len(grid[0]) - 1):
                p = [grid[r][c], grid[r + 1][c], grid[r + 1][c + 1], grid[r][c + 1]]
                zc = sum(q[2] for q in p) / 4
                me.face(list(reversed(p)) if (shell == "ext") == outward else p, matf(s0 + c, (rs[r] + rs[r + 1]) / 2, zc))
        return grid

    @staticmethod
    def strip(me, a, b, m, flip=False):
        n = len(a)
        assert n == len(b), (n, len(b))
        for k in range(n):
            q = [a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]]
            me.face(list(reversed(q)) if flip else q, m)

    @staticmethod
    def strip_open(me, a, b, m, flip=False):
        n = len(a)
        assert n == len(b), (n, len(b))
        for k in range(n - 1):
            q = [a[k], a[k + 1], b[k + 1], b[k]]
            me.face(list(reversed(q)) if flip else q, m)

    @staticmethod
    def dedupe(loop):
        out = []
        for p in loop:
            if not out or math.dist(out[-1], p) > 1e-5:
                out.append(p)
        if len(out) > 1 and math.dist(out[0], out[-1]) < 1e-5:
            out.pop()
        return out

    def cap(self, me, outer, holes, m, normal_y):
        loops = [self.dedupe(outer)] + [self.dedupe(h) for h in holes]
        flat = [p for lp in loops for p in lp]
        tris = tessellate_polygon([[Vector((p[0], p[2], 0.0)) for p in lp] for lp in loops])
        for t in tris:
            q = [flat[t[0]], flat[t[1]], flat[t[2]]]
            n = (Vector(q[1]) - Vector(q[0])).cross(Vector(q[2]) - Vector(q[0]))
            if n.y * normal_y < 0:
                q = [q[0], q[2], q[1]]
            me.face(q, m)

    @staticmethod
    def rounded_rect(hw, z0, z1, r, y, n=4, x0=0.0):
        pts = []
        for cx, cz, a0 in ((hw - r, z0 + r, -90), (hw - r, z1 - r, 0), (-hw + r, z1 - r, 90), (-hw + r, z0 + r, 180)):
            for k in range(n + 1):
                a = math.radians(a0 + 90 * k / n)
                pts.append((x0 + cx + r * math.cos(a), y, cz + r * math.sin(a)))
        return pts

    def es(self, k, side):
        return LOFT.Loft.ext_s(k, side)

    def ins(self, k, side):
        return LOFT.Loft.int_s(k, side)

    def side_rng(self, k0, k1, side, shell="ext"):
        f = self.es if shell == "ext" else self.ins
        a, b = f(k0, side), f(k1, side)
        return (min(a, b), max(a, b))

    def surf_x(self, y, z):
        lp = self.loop_at("ext", y)
        for k in range(E["head"]):
            (xa, za), (xb, zb) = lp[k], lp[k + 1]
            if za - 1e-9 <= z <= zb + 1e-9 and zb > za:
                return xa + (xb - xa) * (z - za) / (zb - za)
        return lp[E["belt"]][0]

    def top_z(self, y):
        """The fender / deck top or the belt, at y."""
        return self.loop_at("ext", y)[E["belt"]][1]

    # ============================================================ the body (both shells, partitioned into panels)
    def doors_on(self, sd):
        return sorted([d for d in self.L.doors if sd in d.get("sides", "RL")], key=lambda d: -d["y0"])

    def windows_on(self, sd, y0, y1):
        return [w for w in self.L.windows if sd in w.get("sides", "RL") and w["y0"] <= y0 + 1e-6 and w["y1"] >= y1 - 1e-6]

    def arch_holes(self, sd, y0, y1):
        L = self.L
        out = []
        if getattr(L, "wheels_out", False):
            return out
        for ax in L.axles:
            a, b = ax + L.arch_half, ax - L.arch_half
            if b < y0 and a > y1:
                out.append((min(a, y0), max(b, y1)) + self.side_rng(E["skirt"], E["arch"], sd))
        return out

    def split_long(self, y0, y1, avoid, most=2.6):
        """Split [y0 > y1] into bays no longer than `most`, at stations not inside the `avoid` ranges."""
        if y0 - y1 <= most:
            return [(y0, y1)]
        n = int(math.ceil((y0 - y1) / most))
        cuts = []
        for k in range(1, n):
            want = y0 - (y0 - y1) * k / n
            ok = [y for y in self.Y if y1 + 0.3 < y < y0 - 0.3 and not any(a[1] - 1e-6 < y < a[0] + 1e-6 for a in avoid)
                  and not (cuts and abs(y - cuts[-1]) < 0.3)]
            if ok:
                cuts.append(min(ok, key=lambda y: abs(y - want)))
        edges = [y0] + sorted(set(cuts), reverse=True) + [y1]
        return list(zip(edges, edges[1:]))

    def body(self, st):
        L = self.L
        R = L.rear
        P = st["panel"]                       # material per band: lower, upper (the window band's pillars), roof, sail
        lower = lambda s, y, z: P["lower"]                                   # noqa: E731
        upper = lambda s, y, z: P["upper"]                                   # noqa: E731
        roofm = lambda s, y, z: P["roof"]                                    # noqa: E731
        sailm = lambda s, y, z: P.get("sail", "black")                       # noqa: E731
        glass = lambda s, y, z: "glass"                                      # noqa: E731
        front_end = L.lid[0] if L.lid else round(L.nose - 0.06, 4)
        rear_start = L.tail_in
        cR, cL = self.es(E["cant"], "R"), self.es(E["cant"], "L")
        self.front_end, self.rear_start = front_end, rear_start
        # ---- the nose (cap and all), the hood or cowl, the windscreen
        me = self.mod("nose", "end_cap", "nose", "C", hp=500, mass=14)
        self.cells(me, "nose", "ext", L.nose, front_end, 0, self.NS_E, lower)
        if L.lid:
            if L.lid[1] > L.toe + 1e-6:
                me = self.mod("cowl", "trim", "cowl", "C", hp=200, mass=3)
                self.cells(me, "cowl", "ext", L.lid[1], L.toe, cR, cL, lambda s, y, z: "black")
        elif front_end > L.toe + 1e-6:
            me = self.mod("cowl", "trim", "cowl", "C", hp=200, mass=3)
            self.cells(me, "cowl", "ext", front_end, L.toe, cR, cL, roofm if L.front["kind"] == "flat" else lower)
        me = self.mod("screen", "glazing", "screen", "C", hp=60, mass=14, breaks="shatter")
        self.cells(me, "screen", "ext", L.toe, L.header, cR, cL, glass)
        self.frit()
        roof_end = R["c_top"] if R["kind"] == "trunk" else rear_start
        self.panels = {"R": [], "L": []}
        for sd in SIDES:
            ds = self.doors_on(sd)
            for d in ds:
                assert d["y0"] <= L.toe + 1e-6, ("a door starts ahead of the cowl", d)
            wins = sorted([w["y0"] for w in L.windows if sd in w.get("sides", "RL")], reverse=True)
            first_door = ds[0]["y0"] if ds else rear_start
            first = min(max([first_door] + wins[:1]), L.toe)       # (the first opening on this side, a door or a window)
            # the fender: below the belt from the nose to the first door, the gutter band over the hood zone
            if front_end > first + 1e-6:
                mid = "fender_" + sd
                me = self.mod(mid, "side_bay", "fender", sd, hp=400, mass=9)
                self.cells(me, mid, "ext", front_end, first, *self.side_rng(E["skirt"], E["belt"], sd), lower,
                           holes=self.arch_holes(sd, front_end, first))
                if front_end > L.toe + 1e-6:
                    self.cells(me, mid, "ext", front_end, L.toe, *self.side_rng(E["belt"], E["cant"], sd), lower)
                self.panels[sd].append((mid, front_end, first))
            if first > first_door + 1e-6:                   # (windows ahead of the first door: a side run with their holes)
                avoid = [(w["y0"], w["y1"]) for w in L.windows] + [(ax + L.arch_half, ax - L.arch_half) for ax in L.axles]
                bays = self.split_long(first, first_door, avoid)
                for k, (a, b) in enumerate(bays):
                    name = "fore" if len(bays) == 1 else "fore_%d" % k
                    self.side_panel(sd, name, name, a, b, lower, upper)
            if L.toe > first + 1e-6:
                mid = "sail_" + sd
                me = self.mod(mid, "trim", "sail", sd, hp=300, mass=2)
                self.cells(me, mid, "ext", L.toe, first, *self.side_rng(E["belt"], E["head"], sd), sailm)
            mid = "a_pillar_" + sd
            me = self.mod(mid, "trim", "a_pillar", sd, hp=400, mass=3)
            self.cells(me, mid, "ext", L.toe, L.header, *self.side_rng(E["head"], E["cant"], sd), upper)
            # the doors' rockers, the posts between doors, the quarter behind the last
            for i, d in enumerate(ds):
                for ax in ([] if getattr(L, "wheels_out", False) else L.axles):
                    if not L.high:
                        assert not (ax - L.arch_half < d["y0"] and ax + L.arch_half > d["y1"]), ("a door over an arch needs a high floor", d, ax)
                mid = "rocker_%s_%s" % (d["id"], sd)
                me = self.mod(mid, "side_bay", "rocker_" + d["id"], sd, hp=500, mass=5)
                self.cells(me, mid, "ext", d["y0"], d["y1"], *self.side_rng(E["skirt"], E["sill"], sd), lower,
                           holes=self.arch_holes(sd, d["y0"], d["y1"]))
                nxt = ds[i + 1]["y0"] if i + 1 < len(ds) else None
                if nxt is not None and d["y1"] > nxt + 1e-6:
                    self.side_panel(sd, "post_%d" % i, "post_%d" % i, d["y1"], nxt, lower, upper)
            last = ds[-1]["y1"] if ds else first_door
            if last > rear_start + 1e-6:
                bays = self.split_long(last, rear_start, [(w["y0"], w["y1"]) for w in L.windows] +
                                       [(ax + L.arch_half, ax - L.arch_half) for ax in L.axles])
                for k, (a, b) in enumerate(bays):
                    name = "quarter" if len(bays) == 1 else "quarter_%d" % k
                    self.side_panel(sd, name, name, a, b, lower, upper)
            # the roof-edge band over a trunk's C-pillar
            if R["kind"] == "trunk":
                mid = "c_pillar_" + sd
                me = self.mod(mid, "trim", "c_pillar", sd, hp=400, mass=3)
                self.cells(me, mid, "ext", R["c_top"], R["c_foot"], *self.side_rng(E["head"], E["cant"], sd), upper)
        # ---- the roof (the drip bands and the top) in bays
        for k, (a, b) in enumerate(self.split_long(L.header, roof_end, [], most=1.7)):
            mid = "roof_%d" % k
            me = self.mod(mid, "roof_bay", mid, "C", hp=500, mass=12)
            self.cells(me, mid, "ext", a, b, self.es(E["head"], "R"), self.es(E["head"], "L"), roofm)
        # ---- a trunk's rear window, deck strip and lid opening
        if R["kind"] == "trunk":
            me = self.mod("backlight", "glazing", "backlight", "C", hp=60, mass=10, breaks="shatter")
            self.cells(me, "backlight", "ext", R["c_top"], R["c_foot"], cR, cL, glass)
            if R["c_foot"] > R["lid"][0] + 1e-6:
                me = self.mod("deck", "trim", "deck", "C", hp=300, mass=3)
                self.cells(me, "deck", "ext", R["c_foot"], R["lid"][0], cR, cL, roofm)
        # ---- the tail
        me = self.mod("tail", "end_cap", "tail", "C", hp=500, mass=14)
        self.cells(me, "tail", "ext", rear_start, L.tail, 0, self.NS_E, lower)
        self.interior(st)
        self.ends(st)
        self.reveals(st)
        return self.cover_check()

    def side_panel(self, sd, name, slot, y0, y1, lower, upper):
        """A side panel from y0 to y1: below the belt (its arches cut out), the window band (its windows cut out),
        and over a trunk's deck zone the deck's edge band."""
        L = self.L
        mid = "%s_%s" % (name, sd)
        me = self.mod(mid, "side_bay", slot, sd, hp=400, mass=10)
        self.cells(me, mid, "ext", y0, y1, *self.side_rng(E["skirt"], E["belt"], sd), lower, holes=self.arch_holes(sd, y0, y1))
        R = L.rear
        g0, g1 = y0, y1
        if R["kind"] == "trunk" and y1 < R["c_foot"]:
            g1 = max(y1, R["c_foot"])
            if R["c_foot"] < y0:
                self.cells(me, mid, "ext", min(y0, R["c_foot"]), y1, *self.side_rng(E["belt"], E["cant"], sd), lower)
        if g0 > g1 + 1e-6:
            holes = [(w["y0"], w["y1"]) + self.side_rng(E["belt"], E["head"], sd) for w in self.windows_on(sd, g0, g1)]
            self.cells(me, mid, "ext", g0, g1, *self.side_rng(E["belt"], E["head"], sd), upper, holes=holes)
        self.panels[sd].append((mid, y0, y1))

    def interior(self, st):
        L = self.L
        R = L.rear
        lin = lambda s, y, z: "lining"                                     # noqa: E731
        me = self.mod("floor", "floor", "floor", "C", hp=2000, mass=20)
        # (out to the sill: a cab-over cab's floor edge runs on past the arch's point to meet the lining)
        self.cells(me, "floor", "int", L.toe, L.cab_end, self.ins(E["sill"], "L"), self.NS_I + self.ins(E["sill"], "R"), lambda s, y, z: "carpet")
        for sd in SIDES:
            ds = self.doors_on(sd)
            edges = [L.toe]
            for d in ds:
                edges += [d["y0"], d["y1"]]
            edges.append(L.cab_end)
            spans = []
            for a, b in zip(edges[0::2], edges[1::2]):
                a, b = min(a, L.toe), max(b, L.cab_end)
                if a > b + 1e-6:
                    spans.append((a, b))
            for k, (a, b) in enumerate(spans):
                for j, (aa, bb) in enumerate(self.split_long(a, b, [(w["y0"], w["y1"]) for w in L.windows] +
                                                             [(ax + L.arch_half + 0.002, ax - L.arch_half - 0.002) for ax in L.axles])):
                    mid = "trim_%d_%d_%s" % (k, j, sd)
                    me = self.mod(mid, "lining_bay", "trim_%d_%d" % (k, j), sd, hp=200, mass=3)
                    holes = [(w["y0"], w["y1"]) + self.side_rng(E["belt"], E["head"], sd, "int") for w in self.windows_on(sd, aa, bb)]
                    self.cells(me, mid, "int", aa, bb, *self.side_rng(E["sill"], E["head"], sd, "int"), lin, holes=holes)
            mid = "a_trim_" + sd
            me = self.mod(mid, "lining_bay", "a_pillar", sd, hp=200, mass=1.5)
            self.cells(me, mid, "int", L.toe, L.header, *self.side_rng(E["head"], E["cant"], sd, "int"), lin)
            if R["kind"] == "trunk":
                mid = "c_trim_" + sd
                me = self.mod(mid, "lining_bay", "c_pillar", sd, hp=200, mass=1.5)
                self.cells(me, mid, "int", R["c_top"], R["c_foot"], *self.side_rng(E["head"], E["cant"], sd, "int"), lin)
        roof_end = R["c_top"] if R["kind"] == "trunk" else L.cab_end
        for k, (a, b) in enumerate(self.split_long(L.header, roof_end, [], most=1.7)):
            mid = "headliner_%d" % k
            me = self.mod(mid, "ceiling_bay", "roof_%d" % k, "C", hp=200, mass=3)
            self.cells(me, mid, "int", a, b, self.ins(E["head"], "R"), self.ins(E["head"], "L"), lambda s, y, z: "headliner")

    def rear_hole(self, y, inner=False):
        """The opening in the tail's end face (a hatch, barn doors or a back window): a rounded rectangle."""
        R = self.L.rear
        H = R.get("hatch") or R.get("barn") or R.get("back_window")
        if not H:
            return None
        return self.rounded_rect(H["half_w"], H["z"][0], H["z"][1], H.get("corner", 0.10), y)

    def ends(self, st):
        L = self.L
        R = L.rear
        mount = L.mount_x
        nose_loop = [self.ext_pt(0, s) for s in range(self.NS_E + 1)]
        self.cap(self.MESH["nose"], nose_loop + [(-mount, L.nose, L.skirt), (mount, L.nose, L.skirt)], [], st["panel"]["lower"], 1)
        it = self.iy(L.tail)
        tail_loop = [self.ext_pt(it, s) for s in range(self.NS_E + 1)] + [(-mount, L.tail, L.skirt), (mount, L.tail, L.skirt)]
        hole_o = self.rear_hole(L.tail) if R["kind"] in ("hatch", "wall") else None
        self.cap(self.MESH["tail"], tail_loop, [hole_o] if hole_o else [], st["panel"]["lower"], -1)
        me = self.mod("firewall", "end_lining", "firewall", "C", hp=800, mass=8)
        self.cap(me, [self.int_pt(L.toe, s) for s in range(self.NS_I)], [], "dash", -1)
        me = self.mod("rear_wall", "end_lining", "rear_wall", "C", hp=300, mass=4)
        hole_i = self.rear_hole(L.cab_end) if R["kind"] in ("hatch", "wall") else None
        self.cap(me, [self.int_pt(L.cab_end, s) for s in range(self.NS_I)], [hole_i] if hole_i else [], "lining", 1)
        if hole_o:
            me = self.mod("jamb_rear", "reveal", "rear_opening", "C", hp=300, mass=2)
            self.strip(me, hole_o, hole_i, st["panel"]["lower"] if R.get("hatch") or R.get("barn") else "black")
            if R.get("back_window"):
                mg = self.mod("back_window", "glazing", "back_window", "C", hp=40, mass=6, breaks="shatter")
                self.cap(mg, hole_o, [], "glass", -1)

    def frit(self, band=0.10, inset=0.004):
        """The windscreen's black ceramic frit: an opaque band printed inside the glass along its side edges, as on
        any bonded screen. It hides the A-pillar's tube where the pillar narrows to nothing at the screen's foot (a
        flat-fronted van's is in plain view there). A token of its own (the screen's slot)."""
        L = self.L
        E = L.E
        me = self.mod("screen_frit", "trim", "screen", "C", hp=60, mass=1)
        rows = self.rows_between(self.Y, L.toe, L.header)

        def edge(y):
            eh = L.ext_half(y)
            (cx, cz), (nx, nz) = eh[E["cant"]], eh[E["cant"] + 1]
            d = math.hypot(nx - cx, nz - cz) or 1.0
            ux, uz = (nx - cx) / d, (nz - cz) / d                 # (along the glass, inward from its edge)
            return (cx, cz - inset), (cx + ux * band, cz + uz * band - inset)       # (just under the glass)
        for a, b in zip(rows, rows[1:]):
            (oa, ia), (ob, ib) = edge(a), edge(b)
            for sx in (1, -1):
                q = [(sx * oa[0], a, oa[1]), (sx * ob[0], b, ob[1]), (sx * ib[0], b, ib[1]), (sx * ia[0], a, ia[1])]
                me.face(q, "black")
                me.face(list(reversed(q)), "black")
        # and along its foot, up the glass from the cowl
        slope = (L.a_line(L.toe - 0.01) - L.a_line(L.toe)) / 0.01                  # (the screen's rise per metre run)
        foot = L.toe - min(1.5 * band / math.hypot(1.0, slope), (L.toe - L.header) * 0.3)   # (deeper at the foot, as screens' are)
        lo, hi = L.ext_loop(L.toe), L.ext_loop(foot)
        cR, cL = self.es(E["cant"], "R"), self.es(E["cant"], "L")
        for k in range(cR, cL):
            q = [(lo[k][0], L.toe, lo[k][1] - inset), (lo[k + 1][0], L.toe, lo[k + 1][1] - inset),
                 (hi[k + 1][0], foot, hi[k + 1][1] - inset), (hi[k][0], foot, hi[k][1] - inset)]
            me.face(q, "black")
            me.face(list(reversed(q)), "black")

    def reveals(self, st):
        L = self.L
        R = L.rear

        def reveal(mid, slot, side, y0, y1, k0, k1, m="black"):
            me = self.mod(mid, "reveal", slot, side, hp=300, mass=2)
            a = self.rect_ring("ext", y0, y1, *self.side_rng(k0, k1, side))
            b = self.rect_ring("int", y0, y1, *self.side_rng(k0, k1, side, "int"))
            self.strip(me, a, b, m)
        for sd in SIDES:
            for d in self.doors_on(sd):
                reveal("jamb_%s_%s" % (d["id"], sd), "door_" + d["id"], sd, d["y0"], d["y1"], E["sill"], E["head"], st["panel"]["lower"])
            for w in L.windows:
                if sd in w.get("sides", "RL"):
                    reveal("reveal_%s_%s" % (w["id"], sd), "window_" + w["id"], sd, w["y0"], w["y1"], E["belt"], E["head"])
        cR, cL = self.es(E["cant"], "R"), self.es(E["cant"], "L")
        iR, iL = self.ins(E["cant"], "R"), self.ins(E["cant"], "L")
        for mid, y0, y1 in [("reveal_screen", L.toe, L.header)] + ([("reveal_backlight", R["c_top"], R["c_foot"])] if R["kind"] == "trunk" else []):
            me = self.mod(mid, "reveal", mid[7:], "C", hp=300, mass=2)
            self.strip(me, self.rect_ring("ext", y0, y1, cR, cL), self.rect_ring("int", y0, y1, iR, iL), "black")
        # the side windows' panes: flush glass, or a blank panel (outside and lined inside) -- a token either way
        blank = st.get("blank_windows", ())
        for w in L.windows:
            for sd in SIDES:
                if sd not in w.get("sides", "RL"):
                    continue
                mid = "pane_%s_%s" % (w["id"], sd)
                if blank == "all" or w["id"] in blank or (w["id"] + sd) in blank:
                    me = self.mod(mid, "side_bay", "window_" + w["id"], sd, hp=300, mass=6)
                    self.cells(me, mid, "ext", w["y0"], w["y1"], *self.side_rng(E["belt"], E["head"], sd), lambda s, y, z: st["panel"]["lower"])
                    if w["y0"] <= L.toe and w["y1"] >= L.cab_end:      # (its lining: the inner shell's, a token of its own)
                        mi = self.mod("pane_lining_%s_%s" % (w["id"], sd), "lining_bay", "window_" + w["id"], sd, hp=100, mass=2)
                        self.cells(mi, mid + "_in", "int", w["y0"], w["y1"], *self.side_rng(E["belt"], E["head"], sd, "int"), lambda s, y, z: "lining")
                else:
                    me = self.mod(mid, "glazing", "window_" + w["id"], sd, hp=40, mass=6, breaks="shatter")
                    self.cells(me, mid, "ext", w["y0"], w["y1"], *self.side_rng(E["belt"], E["head"], sd), lambda s, y, z: "glass")

    # ============================================================ closers (moving)
    def door(self, d, sd, st):
        L = self.L
        y0, y1 = d["y0"], d["y1"]
        did = d["id"] + sd
        lid = "door_" + did
        me = self.mod(lid, "door_leaf", "door_" + d["id"], sd, hp=700, mass=22)
        g_out = self.patch(me, "ext", y0, y1, *self.side_rng(E["sill"], E["belt"], sd), lambda s, y, z: st["panel"]["lower"], inset=GAP,
                           edges=(1, 1, 1, 0) if sd == "R" else (1, 1, 0, 1))
        g_in = self.patch(me, "int", y0, y1, *self.side_rng(E["sill"], E["belt"], sd, "int"), lambda s, y, z: "lining")

        def outline(g):
            return [r[0] for r in g] + g[-1][1:] + [r[-1] for r in reversed(g)][1:] + list(reversed(g[0]))[1:-1]
        self.strip(me, outline(g_out), outline(g_in), st["panel"]["lower"])
        gid = "glass_" + did
        mg = self.mod(gid, "door_glass", "door_" + d["id"], sd, hp=40, mass=5, breaks="shatter")
        self.patch(mg, "ext", y0, y1, *self.side_rng(E["belt"], E["head"], sd), lambda s, y, z: "glass")
        sx = 1 if sd == "R" else -1
        # the handle at the trailing edge (sliding doors: the front edge pulls back), the inside pull
        hy = y1 + 0.12 if d.get("kind", "hinge") == "hinge" else y0 - 0.12
        hz = L.belt - 0.06
        parts = [lid, gid]
        tm = self.mod("handle_" + did, "leaf_trim", "handle_" + d["id"], sd, hp=100, mass=0.5)
        tm.box((sx * (self.surf_x(hy, hz) + 0.004), hy, hz), (0.006, 0.07, 0.010), st.get("handle", "chrome"))
        tm.box((sx * (L.half_w - L.int_off - 0.03), hy + 0.08 * (1 if d.get("kind", "hinge") == "hinge" else -1), L.belt - 0.30), (0.03, 0.10, 0.02), "dash")
        parts.append("handle_" + did)
        kind = d.get("kind", "hinge")
        e = {"id": did, "kind": "door" if kind == "hinge" else "slide", "side": sd, "parts": parts, "y0": y0, "y1": y1}
        if kind == "hinge":
            hx = L.side_x(0.9) * sx
            e["hinge"] = [(hx, y0, 0.70), (hx - sx * 0.02, y0, 1.30)]
            e["open_deg"] = d.get("open_deg", 68) * (1 if sd == "R" else -1)
        else:                                             # out 6 cm, then back along the side, past the leaf's own length
            e["slide"] = [round(sx * 0.07, 3), round(-(y0 - y1) - 0.06, 3)]
        self.CLOSERS.append(e)
        self.marker("stand_%s" % did, (sx * (L.half_w + 0.45), (y0 + y1) / 2 - 0.15, 0.0))
        self.marker("grab_%s" % did, (sx * (L.half_w - 0.10), (y0 + y1) / 2, L.head - 0.08))
        return lid

    def lid_over(self, mid, role, slot, y0, y1, st, tub=True, tub_floor=None):
        """A lid in the top between the cants (frunk, trunk): skin, underside, shut faces; its tub below."""
        L = self.L
        s0, s1 = self.es(E["cant"], "R"), self.es(E["cant"], "L")
        me = self.mod(mid, role, slot, "C", hp=600, mass=12)
        g = self.patch(me, "ext", y0, y1, s0, s1, lambda s, y, z: st["panel"]["roof" if role == "trunk_lid" else "lower"], inset=GAP)
        under = [[(p[0], p[1], p[2] - 0.04) for p in row] for row in g]
        for r in range(len(under) - 1):
            for c in range(len(under[0]) - 1):
                me.face([under[r][c], under[r + 1][c], under[r + 1][c + 1], under[r][c + 1]], "tub")

        def outline(gg):
            return [r[0] for r in gg] + gg[-1][1:] + [r[-1] for r in reversed(gg)][1:] + list(reversed(gg[0]))[1:-1]
        self.strip(me, outline(g), outline(under), st["panel"]["lower"])
        if tub:
            tm = self.mod(mid.replace("_lid", "") + "_tub", "frunk_tub", slot, "C", hp=400, mass=10)
            rim = self.rect_ring("ext", y0, y1, s0, s1)
            shelf_z = L.arch_top + 0.03
            shelf = [(p[0], p[1], shelf_z) for p in rim]
            self.strip(tm, rim, shelf, "tub")
            x0 = L.well_x - 0.03
            yb0, yb1 = y0 - 0.04, y1 + 0.04
            box_top = [(x0, yb1, shelf_z), (x0, yb0, shelf_z), (-x0, yb0, shelf_z), (-x0, yb1, shelf_z)]
            self.cap(tm, shelf, [box_top], "tub", 0)
            zf = tub_floor or L.floor
            box_bot = [(x, y, zf) for x, y, _ in box_top]
            self.strip(tm, box_top, box_bot, "tub")
            tm.face(box_bot, "tub")
        return g

    def closers(self, st):
        L = self.L
        R = L.rear
        for sd in SIDES:
            for d in self.doors_on(sd):
                self.door(d, sd, st)
        if L.lid:
            self.lid_over("frunk_lid", "frunk_lid", "lid", L.lid[0], L.lid[1], st)
            self.CLOSERS.append({"id": "frunk", "kind": "lid", "side": "C", "parts": ["frunk_lid"],
                                 "hinge": [(-0.6, L.lid[1], L.hood_z(L.lid[1]) + 0.01), (0.6, L.lid[1], L.hood_z(L.lid[1]) + 0.01)], "open_deg": 60})
            self.marker("stand_frunk", (0, L.nose + 0.55, 0.0))
            self.marker("light_frunk", (0, (L.lid[0] + L.lid[1]) / 2, L.arch_top + 0.08))
        if R["kind"] == "trunk":
            y0, y1 = R["lid"]
            self.lid_over("trunk_lid", "trunk_lid", "trunk", y0, y1, st)
            self.CLOSERS.append({"id": "trunk", "kind": "lid", "side": "C", "parts": ["trunk_lid"],
                                 "hinge": [(-0.6, y0, L.deck_z(y0) + 0.02), (0.6, y0, L.deck_z(y0) + 0.02)], "open_deg": -72})
            self.marker("stand_trunk", (0, L.tail - 0.55, 0.0), math.pi)
        H = R.get("hatch")
        if H:
            self.hatch(H, st)
        B = R.get("barn")
        if B:
            self.barn(B, st)

    def hatch(self, H, st):
        L = self.L
        z0, z1 = H["z"]
        c = H.get("corner", 0.10)
        me = self.mod("hatch", "hatch", "hatch", "C", hp=700, mass=26)
        o = self.rounded_rect(H["half_w"] - GAP, z0 + GAP, z1 - GAP, c - GAP, L.tail)
        i = self.rounded_rect(H["half_w"], z0, z1, c, L.cab_end)
        G = H["glass"]
        go = self.rounded_rect(G["half_w"], G["z"][0], G["z"][1], G.get("corner", 0.07), L.tail)
        gi = self.rounded_rect(G["half_w"], G["z"][0], G["z"][1], G.get("corner", 0.07), L.cab_end)
        self.strip(me, o, go, st["panel"]["lower"])
        self.strip(me, i, gi, "lining", flip=True)
        self.strip(me, o, i, st["panel"]["lower"])
        self.strip(me, go, gi, "black")
        mg = self.mod("hatch_glass", "hatch_glass", "hatch", "C", hp=40, mass=8, breaks="shatter")
        self.cap(mg, go, [], "glass", -1)
        tm = self.mod("handle_hatch", "leaf_trim", "handle_hatch", "C", hp=100, mass=0.5)
        tm.box((0, L.tail - 0.012, G["z"][0] - 0.05), (0.08, 0.01, 0.015), st.get("handle", "chrome"))
        hz = z1 + 0.05
        self.CLOSERS.append({"id": "hatch", "kind": "hatch", "side": "C", "parts": ["hatch", "hatch_glass", "handle_hatch"],
                             "hinge": [(-0.6, L.tail + 0.02, hz), (0.6, L.tail + 0.02, hz)], "open_deg": -88})
        self.marker("stand_hatch", (0, L.tail - 0.55, 0.0), math.pi)

    def barn(self, B, st):
        """Twin rear doors split at the middle, hinged at their outer edges, each with a window."""
        L = self.L
        z0, z1 = B["z"]
        hw = B["half_w"]
        parts_all = []
        for sd, sx in (("R", 1), ("L", -1)):
            mid = "barn_" + sd
            me = self.mod(mid, "hatch", "barn_" + sd, sd, hp=600, mass=24)
            yo, yi = L.tail, L.cab_end
            xa, xb = sx * (GAP if True else 0), sx * (hw - GAP)
            q = lambda x0, x1, y, za, zb: [(x0, y, za), (x1, y, za), (x1, y, zb), (x0, y, zb)]     # noqa: E731
            gz0, gz1 = B.get("glass_z", (z1 - 0.55, z1 - 0.12))
            gx0, gx1 = sx * 0.08, sx * (hw - 0.10)
            o = [(xa, yo, z0 + GAP), (xb, yo, z0 + GAP), (xb, yo, z1 - GAP), (xa, yo, z1 - GAP)]
            i = [(sx * 0.0, yi, z0), (sx * hw, yi, z0), (sx * hw, yi, z1), (sx * 0.0, yi, z1)]
            go = q(gx0, gx1, yo, gz0, gz1)
            gi = q(gx0, gx1, yi, gz0, gz1)
            self.cap(me, o, [go], st["panel"]["lower"], -1)
            self.cap(me, i, [gi], "lining", 1)
            self.strip(me, o, i, st["panel"]["lower"])
            self.strip(me, go, gi, "black")
            mg = self.mod("barn_glass_" + sd, "hatch_glass", "barn_" + sd, sd, hp=40, mass=6, breaks="shatter")
            self.cap(mg, go, [], "glass", -1)
            parts = [mid, "barn_glass_" + sd]
            self.CLOSERS.append({"id": "barn_" + sd, "kind": "door", "side": sd, "parts": parts,
                                 "hinge": [(sx * hw, L.tail + 0.01, z0), (sx * hw, L.tail + 0.01, z1)], "open_deg": 100 * sx})
            parts_all += parts
        self.marker("stand_hatch", (0, L.tail - 0.6, 0.0), math.pi)

    # ============================================================ wells, underpan
    def wells_and_pan(self, st):
        L = self.L
        for n, ax in enumerate(L.axles):
            ya, yb = ax + L.arch_half, ax - L.arch_half
            if not (L.nose > ya and yb > L.tail) or getattr(L, "wheels_out", False):
                continue
            for sd in SIDES:
                sx = 1 if sd == "R" else -1
                mid = "well_%d_%s" % (n, sd)
                me = self.mod(mid, "wheel_well", "well_%d" % n, sd, hp=600, mass=5)
                rs = self.rows_between(self.Y, ya, yb)
                ks = [self.es(k, sd) for k in range(E["skirt"], E["arch"] + 1)]
                for y in (ya, yb):
                    outer = [self.ext_pt(self.iy(y), k) for k in ks]
                    me.face(outer + [(sx * L.well_x, y, L.arch_top), (sx * L.well_x, y, L.skirt)], "rubber")
                top_o = [self.ext_pt(self.iy(y), ks[-1]) for y in rs]
                top_i = [(sx * L.well_x, y, L.arch_top) for y in rs]
                self.strip_open(me, top_o, top_i, "rubber", flip=(sd == "L"))
                wall_t = [(sx * L.well_x, y, L.arch_top) for y in rs]
                wall_b = [(sx * L.well_x, y, L.skirt) for y in rs]
                self.strip_open(me, wall_t, wall_b, "rubber", flip=(sd == "L"))
                lip = [Vector(self.ext_pt(self.iy(ya), ks[0]))] + [Vector(self.ext_pt(self.iy(ya), k)) for k in ks[1:]] + \
                      [Vector(self.ext_pt(self.iy(y), ks[-1])) for y in rs[1:-1]] + [Vector(self.ext_pt(self.iy(yb), k)) for k in reversed(ks)]
                me.pipe([p + Vector((sx * 0.006, 0, 0)) for p in lip], 0.012, "rubber", n=6)
        if L.high and not getattr(L, "wheels_out", False):  # (a cab over its wheels: two steps up, in the arch behind the tyre)
            ax = L.axles[0]
            yb = ax - L.arch_half
            for sd in SIDES:
                sx = 1 if sd == "R" else -1
                me = self.mod("steps_" + sd, "wheel_well", "steps", sd, hp=300, mass=8)
                for z in (0.62, 0.98):
                    xo = L.half_w - 0.02
                    me.box((sx * (L.well_x + xo) / 2, yb + 0.05, z), ((xo - L.well_x) / 2, 0.05, 0.015), "chrome")
                me.box((sx * (L.half_w + 0.02), yb - 0.02, L.floor + 0.55), (0.012, 0.012, 0.35), "chrome")
        me = self.mod("underpan", "underpan", "underpan", "C", hp=800, mass=16)
        arches = [] if getattr(L, "wheels_out", False) else [(ax + L.arch_half, ax - L.arch_half) for ax in L.axles]
        mx = L.mount_x
        for sd in SIDES:
            sx = 1 if sd == "R" else -1
            for a, b in zip(self.Y, self.Y[1:]):
                if any(y1 - 1e-9 <= b and a <= y0 + 1e-9 for y0, y1 in arches):
                    continue
                pa, pb = self.ext_pt(self.iy(a), self.es(E["skirt"], sd)), self.ext_pt(self.iy(b), self.es(E["skirt"], sd))
                ra = [pa, (sx * mx, a, L.skirt), (sx * mx, a, 0.505)]
                rb = [pb, (sx * mx, b, L.skirt), (sx * mx, b, 0.505)]
                self.strip_open(me, ra, rb, "rubber", flip=(sd == "L"))
        bl = L.board["length_m"] / 2
        for y_end, y_riser in ((L.nose, min(L.nose, round(bl - 0.04, 4))), (L.tail, max(L.tail, round(-bl + 0.04, 4)))):
            rs = self.rows_between(self.Y, max(y_end, y_riser), min(y_end, y_riser))
            if len(rs) >= 2:
                rows = [[(-mx, y, L.skirt), (mx, y, L.skirt)] for y in rs]
                self.strip_open(me, [r[0] for r in rows], [r[1] for r in rows], "rubber")
            me.face([(-mx, y_riser, L.skirt), (mx, y_riser, L.skirt), (mx, y_riser, 0.505), (-mx, y_riser, 0.505)], "rubber")

    # ============================================================ dressing: every piece its own token component
    def face_x(self, y, z):
        """The half width of the body's end face at height z (the loop at station y, below the top)."""
        lp = self.loop_at("ext", y)
        best = 0.0
        for k in range(len(lp) // 2):
            (xa, za), (xb, zb) = lp[k], lp[k + 1]
            if min(za, zb) - 1e-9 <= z <= max(za, zb) + 1e-9:
                t = 0.0 if abs(zb - za) < 1e-9 else (z - za) / (zb - za)
                best = max(best, abs(xa + (xb - xa) * t))
        return best

    def lamps(self, st, var=None):
        """Head, indicator, tail, stop, reverse and marker lamps where FMVSS 108 puts them: headlamps' centres 22-54 in
        (0.56-1.37 m) up, as far apart as practicable; tail and stop lamps 15-72 in (0.38-1.83 m); a centre high-mounted
        stop lamp; amber front and red rear side markers; on a vehicle 80 in (2.032 m) or wider, three identification
        lamps and two clearance lamps at each end (amber in front, red behind), as high as practicable."""
        L = self.L
        s = st
        hz = L.spec.get("head_lamp_z", 0.78)
        assert 0.56 <= hz <= 1.37, ("FMVSS 108: headlamp centres 0.56-1.37 m", hz)
        y = L.nose + 0.003
        fx = self.face_x(L.nose, hz) - 0.10
        lm = self.mod("head_lamps", "lamp", "head_lamp", "C", hp=60, mass=4, breaks="shatter")
        kind = s.get("head_lamp", "round")
        if s.get("grille") == "band":
            band = [(-fx - 0.06, y, hz - 0.08), (fx + 0.06, y, hz - 0.08), (fx + 0.06, y, hz + 0.08), (-fx - 0.06, y, hz + 0.08)]
            lm.face(list(reversed(band)), "glass_dark")
        for sx in (1, -1):
            nm = "R" if sx > 0 else "L"
            if kind == "projector":
                xs = (fx - 0.18, fx)
            elif kind == "quad":
                xs = (fx - 0.17, fx)
            else:
                xs = (fx - 0.04,)
            for k, x in enumerate(xs):
                c = Vector((sx * x, y + 0.004, hz))
                T = Matrix.Translation(c)
                if kind in ("projector", "round", "quad"):
                    r = 0.066 if kind != "round" else 0.09
                    lm.lathe([(0.0, r), (0.012, r - 0.002), (0.014, r - 0.014)], s.get("bezel", "chrome"), n=20, xf=T)
                    lm.lathe([(0.0, r - 0.014), (0.006, r - 0.021), (0.010, r * 0.45)], "lamp_drl", n=20, xf=T)
                    lm.lathe([(0.008, r * 0.45), (0.014, r * 0.3), (0.016, 0.0001)], "lamp_head", n=20, xf=T)
                else:                                     # rect: a sealed beam
                    lm.box((sx * x, y + 0.006, hz), (0.11, 0.006, 0.055), s.get("bezel", "chrome"))
                    lm.box((sx * x, y + 0.010, hz), (0.095, 0.004, 0.042), "lamp_head")
                self.marker("light_head_%s%d" % (nm, k), (sx * x, L.nose + 0.05, hz))
            ix = min(fx + 0.10, self.face_x(L.nose, hz) - 0.03)
            lm.box((sx * ix, y + 0.004, hz), (0.025, 0.004, 0.05), "lamp_amber")
            self.marker("light_ind_F%s" % nm, (sx * ix, L.nose + 0.04, hz))
        if s.get("grille") == "slots":
            gm = self.mod("grille", "trim", "grille", "C", hp=200, mass=3)
            for k in range(4):
                gm.box((0, y + 0.006, hz - 0.06 + k * 0.04), (fx - 0.22, 0.004, 0.008), s.get("bezel", "chrome"))
        # the tail lamps: in the corners of the tail face, outside any rear opening
        R = L.rear
        C = L.spec.get("cargo")
        tz = L.spec.get("tail_lamp_z", 1.0)
        assert 0.38 <= tz <= 1.83
        hole = R.get("hatch") or R.get("barn") or R.get("back_window")
        tl = self.mod("tail_lamps", "lamp", "tail_lamp", "C", hp=60, mass=3, breaks="shatter")
        if C:
            ty = C["y1"] - 0.004
            edge = C.get("half_w", L.half_w) - 0.02
            x0 = edge - 0.14
            hole = None
        else:
            ty = L.tail - 0.004
            edge = self.face_x(L.tail, tz) - 0.02
            x0 = max(edge - 0.16, (hole["half_w"] + 0.02) if hole and hole["z"][0] < tz + 0.25 else 0.0)
        rear_y = ty + 0.004
        tall = 0.50 if s.get("tail_lamp", "pixel") != "bar" else 0.10
        for sx in (1, -1):
            nm = "R" if sx > 0 else "L"
            if s.get("tail_lamp", "pixel") == "bar":
                tl.face([(sx * 0.02, ty, tz - 0.05), (sx * edge, ty, tz - 0.05), (sx * edge, ty, tz + 0.05), (sx * 0.02, ty, tz + 0.05)][:: -sx], "lamp_tail")
                tl.face([(sx * (edge - 0.12), ty - 0.002, tz - 0.05), (sx * edge, ty - 0.002, tz - 0.05), (sx * edge, ty - 0.002, tz - 0.02),
                         (sx * (edge - 0.12), ty - 0.002, tz - 0.02)][:: -sx], "lamp_reverse")
            else:
                z0 = tz - tall / 2
                tl.face([(sx * x0, ty, z0), (sx * edge, ty, z0), (sx * edge, ty, z0 + tall), (sx * x0, ty, z0 + tall)][:: -sx], "black")
                rows, cols = 9, max(1, int((edge - x0 - 0.012) / 0.03))
                for r in range(rows):
                    for c in range(cols):
                        z = z0 + 0.03 + r * (tall - 0.04) / rows
                        x = x0 + 0.012 + c * 0.03
                        m = "lamp_amber" if r == rows - 1 else ("lamp_reverse" if r == 0 else "lamp_tail")
                        tl.face([(sx * x, ty - 0.003, z), (sx * (x + 0.024), ty - 0.003, z), (sx * (x + 0.024), ty - 0.003, z + 0.04),
                                 (sx * x, ty - 0.003, z + 0.04)][:: -sx], m)
            xm = sx * (x0 + edge) / 2
            self.marker("light_tail_" + nm, (xm, rear_y - 0.05, tz), math.pi)
            self.marker("light_reverse_" + nm, (xm, rear_y - 0.05, tz - 0.15), math.pi)
            self.marker("light_ind_B" + nm, (xm, rear_y - 0.05, tz + 0.15), math.pi)
        # the centre high-mounted stop lamp
        if C and C.get("top_z"):
            cy, cz = C["y1"] - 0.006, C["top_z"] - 0.08
        elif R["kind"] == "trunk":
            cy, cz = R["c_foot"] - 0.02, L.deck_z(R["c_foot"]) + 0.03
        else:
            cy, cz = L.tail - 0.006, (hole["z"][1] + 0.06) if hole else L.head + 0.02
        tl.box((0, cy, cz), (0.18, 0.006, 0.012), "lamp_brake")
        self.marker("light_brake_high", (0, cy - 0.04, cz), math.pi)
        # side markers: amber near the front, red near the back, on their panels (their own token)
        sm = self.mod("side_markers", "lamp", "side_marker", "C", hp=40, mass=0.4, breaks="shatter")
        for sd in SIDES:
            sx = 1 if sd == "R" else -1
            for yy, m in ((L.nose - 0.20, "lamp_amber"), (rear_y + 0.20, "lamp_tail")):
                z = min(L.arch_top + 0.05, L.belt - 0.08)
                xx = self.surf_x(yy, z) if yy > L.tail else C.get("half_w", L.half_w)
                if C and yy < L.tail:
                    z = max(C["floor_z"] + 0.10, 0.45)
                sm.box((sx * (xx + 0.004), yy, z), (0.004, 0.04, 0.015), m)
        # identification and clearance lamps on wide vehicles
        if L.half_w * 2 >= 2.032:
            il = self.mod("id_lamps", "lamp", "id_lamp", "C", hp=40, mass=0.6, breaks="shatter")
            for yy, m, sg in ((L.header - 0.02, "lamp_amber", 1), (L.tail + 0.02, "lamp_tail", -1)):
                if sg < 0 and C and C.get("top_z"):              # (a box's: on its rear top edge)
                    for k in (-1, 0, 1):
                        il.box((k * 0.22, C["y1"] - 0.02, C["top_z"] - 0.05), (0.03, 0.02, 0.012), m)
                    for sx in (1, -1):
                        il.box((sx * (C["half_w"] - 0.05), C["y1"] - 0.02, C["top_z"] - 0.05), (0.03, 0.02, 0.012), m)
                    continue
                zz = self.loop_at("ext", yy)[E["crown"]][1] + 0.012
                for k in (-1, 0, 1):
                    il.box((k * 0.22, yy, zz), (0.03, 0.02, 0.012), m)
                cx = self.loop_at("ext", yy)[E["cant"]][0] - 0.03
                for sx in (1, -1):
                    il.box((sx * cx, yy, self.loop_at("ext", yy)[E["cant"]][1] + 0.01), (0.03, 0.02, 0.012), m)

    def bumpers(self, st):
        """Bumpers in the Part 581 bumper zone (the face bar 16-20 in = 0.41-0.51 m up), full width less 10 %."""
        L = self.L
        bz = L.spec.get("bumper_z", 0.46)
        w = L.half_w * 0.92
        if st.get("bumper") == "none":                      # (an aerostat's gondola: nothing to bump)
            return
        m = {"chrome": "chrome", "black": "black", "body": st["panel"]["lower"]}[st.get("bumper", "chrome")]
        C = L.spec.get("cargo")
        for yy, sg, slot in ((L.nose, 1, "bumper_front"), (C["y1"] if C else L.tail, -1, "bumper_rear")):
            bm = self.mod(slot, "trim", slot, "C", hp=900, mass=10)
            bm.box((0, yy + sg * 0.045, bz), (w, 0.04, 0.07), m)
            bm.box((0, yy + sg * 0.087, bz), (w - 0.02, 0.004, 0.018), "rubber")
            for sx in (1, -1):
                bm.box((sx * w, yy + sg * 0.005, bz), (0.05, 0.045, 0.065), m)

    def mirrors(self, st):
        """Outside mirrors on both sides (FMVSS 111: the driver's is required; a passenger-side one on these)."""
        L = self.L
        if st.get("mirror") == "none":
            return
        # (ahead of the door's front edge, never on the leaf: the mirror is a fixed token and the door swings away)
        my = min(L.toe - 0.06, self.doors_on("L")[0]["y0"] + 0.11 if self.doors_on("L") else L.toe - 0.06)
        if self.doors_on("L") and my - 0.10 < self.doors_on("L")[0]["y0"]:    # (a door right behind the toe -- a tractor's:
            my = self.doors_on("L")[0]["y0"] + 0.10                         # the mirror stands on the cowl ahead of it)
        mz = L.belt + 0.10
        for sd in SIDES:
            sx = 1 if sd == "R" else -1
            me = self.mod("mirror_" + sd, "trim", "mirror", sd, hp=80, mass=1.5, breaks="detach")
            bx = self.surf_x(my, L.belt - 0.01) * sx
            me.pipe([Vector((bx, my, L.belt + 0.02)), Vector((sx * (L.half_w + 0.08), my - 0.02, mz))], 0.012, st.get("mirror", "chrome"), n=6)
            me.box((sx * (L.half_w + 0.12), my - 0.03, mz + 0.02), (0.06, 0.035, 0.055), st.get("mirror", "chrome"))
            me.box((sx * (L.half_w + 0.12), my - 0.066, mz + 0.02), (0.055, 0.002, 0.05), "glass_dark")

    def belt_mouldings(self, st):
        """A moulding along the belt of each fixed side panel and each door (its own token; never across an opening)."""
        if not st.get("belt_trim"):
            return
        L = self.L
        m = st["belt_trim"]
        for sd in SIDES:
            sx = 1 if sd == "R" else -1
            for mid, y0, y1 in self.panels[sd]:
                me = self.mod("belt_" + mid, "trim", "belt_" + mid.rsplit("_", 1)[0], sd, hp=100, mass=0.5)
                self.belt_rod(me, y0 - 0.004, y1 + 0.004, sx, m)

    def belt_rod(self, me, y0, y1, sx, m):
        n = max(2, int((y0 - y1) / 0.1))
        pts = []
        for k in range(n + 1):
            y = y0 - (y0 - y1) * k / n
            z = self.top_z(y) - 0.012
            pts.append(Vector((sx * (self.surf_x(y, z) + 0.006), y, z)))
        me.pipe(pts, 0.008, m, n=6)

    def overlay(self, me, y0, y1, z0, z1, sx, m, proud=0.004):
        """A flat panel overlay 4 mm proud of the skin (an inlay or a livery stripe)."""
        nz = 4
        ny = max(2, int((y0 - y1) / 0.12))
        grid = []
        for a in range(ny + 1):
            y = y0 - (y0 - y1) * a / ny
            zt = min(z1, self.top_z(y) - 0.05)
            row = [(sx * (self.surf_x(y, z0 + (zt - z0) * b / nz) + proud), y, z0 + (zt - z0) * b / nz) for b in range(nz + 1)]
            grid.append(row)
        for a in range(ny):
            for b in range(nz):
                q = [grid[a][b], grid[a + 1][b], grid[a + 1][b + 1], grid[a][b + 1]]
                me.face(q if sx < 0 else list(reversed(q)), m)
        return grid

    def free_spans(self, y0, y1, z0):
        """[y0 > y1] less the arches when z0 is below an arch top: (a, b, z_floor) pieces."""
        L = self.L
        cuts = [(ax + L.arch_half + 0.04, ax - L.arch_half - 0.04) for ax in L.axles]
        out = []
        y = y0
        for a, b in sorted(cuts, key=lambda c: -c[0]):
            if b >= y or a <= y1:
                continue
            if a < y:
                out.append((y, max(a, y1), z0))
            out.append((min(a, y), max(b, y1), max(z0, L.arch_top + 0.04)))
            y = b
        if y > y1:
            out.append((y, y1, z0))
        return [o for o in out if o[0] - o[1] > 0.15]

    def panel_overlays(self, prefix, role, m, z0, z1, frame=None, doors=True, st=None):
        """An overlay on every fixed side panel (and each door leaf, moving with it): inlays, liveries."""
        L = self.L
        made = {}
        for sd in SIDES:
            sx = 1 if sd == "R" else -1
            for mid, y0, y1 in self.panels[sd]:
                me = self.mod("%s_%s" % (prefix, mid), role, "%s_%s" % (prefix, mid.rsplit("_", 1)[0]), sd, hp=100, mass=0.6)
                for a, b, zz in self.free_spans(y0 - 0.05, y1 + 0.05, z0):
                    if zz < z1 - 0.06:
                        g = self.overlay(me, a, b, zz, z1, sx, m)
                        if frame:
                            ring = [r[0] for r in g] + g[-1][1:] + [r[-1] for r in reversed(g)][1:] + list(reversed(g[0]))[1:]
                            me.pipe([Vector(p) + Vector((sx * 0.002, 0, 0)) for p in ring], 0.007, frame, n=6, caps=False)
            if doors:
                for d in self.doors_on(sd):
                    did = d["id"] + sd
                    pid = "%s_door_%s" % (prefix, did)
                    me = self.mod(pid, "leaf_trim", "%s_door_%s" % (prefix, d["id"]), sd, hp=100, mass=0.6)
                    g = self.overlay(me, d["y0"] - 0.05, d["y1"] + 0.05, max(z0, L.sill + 0.06), z1, sx, m)
                    if frame:
                        ring = [r[0] for r in g] + g[-1][1:] + [r[-1] for r in reversed(g)][1:] + list(reversed(g[0]))[1:]
                        me.pipe([Vector(p) + Vector((sx * 0.002, 0, 0)) for p in ring], 0.007, frame, n=6, caps=False)
                    made[did] = pid
        for c in self.CLOSERS:
            if c["id"] in made:
                c["parts"].append(made[c["id"]])
        return made

    def door_belts(self, st):
        if not st.get("belt_trim"):
            return
        for c in self.CLOSERS:
            if c["kind"] in ("door", "slide") and "y0" in c:
                sx = 1 if c["side"] == "R" else -1
                pid = "belt_door_" + c["id"]
                me = self.mod(pid, "leaf_trim", "belt_door_" + c["id"][:-1], c["side"], hp=100, mass=0.4)
                self.belt_rod(me, c["y0"] - GAP, c["y1"] + GAP, sx, st["belt_trim"])
                c["parts"].append(pid)

    def roof_rails(self, st):
        L = self.L
        rr = self.mod("roof_rails", "equipment", "roof_rails", "C", hp=200, mass=6)
        y0, y1 = L.header - 0.15, (L.rear["c_top"] if L.rear["kind"] == "trunk" else L.tail_in) + 0.15
        for sx in (1, -1):
            x = sx * L.half_w * 0.60
            z = L.crown - 0.012
            rr.pipe([Vector((x, y0, z + 0.055)), Vector((x, y1, z + 0.055))], 0.014, st.get("rails", "chrome"), n=8)
            for yy in (y0, (y0 + y1) / 2, y1):
                rr.box((x, yy, z + 0.03), (0.018, 0.03, 0.028), "black")

    def equipment(self, kind, st):
        """Roof and body equipment tokens (a variant's own): light bars, signs, racks, beacons, push bars."""
        L = self.L
        import aero                                         # (the aerostats' tokens: fleet/aero.py; the spacecraft's
        import space                                        #  and the spoke elevator's: fleet/space.py)
        if aero.equipment(self, kind, st) or space.equipment(self, kind, st):
            return
        rz = L.crown
        ym = (L.header + (L.rear["c_top"] if L.rear["kind"] == "trunk" else L.tail_in)) / 2
        if kind == "lightbar":                              # police, ambulance, tow, fire chief: red / blue / amber
            me = self.mod("lightbar", "equipment", "roof_bar", "C", hp=120, mass=9, breaks="detach")
            y = L.header - 0.45
            me.box((0, y, rz + 0.06), (0.62, 0.13, 0.05), "black")
            cols = st.get("bar_colours", ("lamp_red", "lamp_blue"))
            for k in range(6):
                x = -0.55 + k * 0.22
                me.box((x, y, rz + 0.07), (0.09, 0.12, 0.04), cols[0] if x < 0 else cols[1])
            for sx in (1, -1):
                me.box((sx * 0.5, y, rz + 0.02), (0.03, 0.08, 0.02), "black")
            self.marker("light_bar", (0, y, rz + 0.10))
        elif kind == "beacon":
            me = self.mod("beacon", "equipment", "roof_beacon", "C", hp=60, mass=2)
            me.lathe([(0.0, 0.09), (0.02, 0.09), (0.12, 0.07), (0.14, 0.0001)], "lamp_amber", n=16,
                     xf=Matrix.Translation((0, L.header - 0.6, rz)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
            self.marker("light_beacon", (0, L.header - 0.6, rz + 0.15))
        elif kind == "taxi_sign":
            me = self.mod("taxi_sign", "equipment", "roof_sign", "C", hp=60, mass=3)
            me.box((0, ym, rz + 0.12), (0.30, 0.10, 0.10), "sign")
            me.box((0, ym, rz + 0.02), (0.20, 0.06, 0.02), "black")
        elif kind == "roof_rack":
            me = self.mod("roof_rack", "equipment", "roof_rack", "C", hp=200, mass=12)
            y0, y1 = L.header - 0.2, (L.rear["c_top"] if L.rear["kind"] == "trunk" else L.tail_in) + 0.2
            for sx in (1, -1):
                me.pipe([Vector((sx * L.half_w * 0.7, y0, rz + 0.12)), Vector((sx * L.half_w * 0.7, y1, rz + 0.12))], 0.02, "black", n=6)
            k = 0
            y = y0
            while y > y1:
                me.pipe([Vector((-L.half_w * 0.7, y, rz + 0.12)), Vector((L.half_w * 0.7, y, rz + 0.12))], 0.016, "black", n=6)
                for sx in (1, -1):
                    me.box((sx * L.half_w * 0.7, y, rz + 0.06), (0.015, 0.015, 0.06), "black")
                y -= 0.6
                k += 1
        elif kind == "push_bar":
            me = self.mod("push_bar", "equipment", "push_bar", "C", hp=600, mass=14)
            y = L.nose + 0.13
            for sx in (1, -1):
                me.pipe([Vector((sx * 0.35, y - 0.06, 0.40)), Vector((sx * 0.35, y, 0.45)), Vector((sx * 0.35, y, 0.95))], 0.025, "black", n=8)
            me.pipe([Vector((-0.38, y, 0.92)), Vector((0.38, y, 0.92))], 0.022, "black", n=8)
            me.pipe([Vector((-0.38, y, 0.62)), Vector((0.38, y, 0.62))], 0.022, "black", n=8)
        elif kind == "spotlight":
            me = self.mod("spotlight", "equipment", "spotlight", "L", hp=60, mass=2)
            x = -(self.surf_x(L.toe - 0.1, L.belt + 0.05) + 0.06)
            me.lathe([(0.0, 0.07), (0.12, 0.07), (0.13, 0.0001)], "chrome", n=14,
                     xf=Matrix.Translation((x, L.toe - 0.1, L.belt + 0.12)))
        elif kind == "ladder_rack":
            self.equipment("roof_rack", st)
            me = self.mod("ladder", "equipment", "roof_ladder", "C", hp=150, mass=10)
            y0, y1 = L.header - 0.3, L.tail_in + 0.3
            for sx in (1, -1):
                me.box((sx * 0.22, (y0 + y1) / 2, rz + 0.17), (0.025, (y0 - y1) / 2, 0.02), "chrome")
            y = y0 - 0.1
            while y > y1:
                me.box((0, y, rz + 0.17), (0.22, 0.012, 0.012), "chrome")
                y -= 0.3
        else:
            self.equipment_x(kind, st)

    # ============================================================ the cabin
    def seat(self, me, x, hy, hz, w, bench=False, back_deg=20):
        hw = w / 2 - 0.02
        me.box((x, hy + 0.20, hz - 0.08), (hw, 0.26, 0.07), "seat")
        me.box((x, hy + 0.20, hz - 0.25 if hz - 0.25 > self.L.floor + 0.05 else self.L.floor + 0.06), (hw * 0.7, 0.20, 0.10), "dash")
        back = Matrix.Translation((x, hy - 0.06, hz - 0.02)) @ Matrix.Rotation(math.radians(back_deg), 4, "X")
        me.box((0, 0, 0.32), (hw, 0.07, 0.32), "seat", xf=back)
        if not bench:
            me.box((0, 0.0, 0.76), (hw * 0.55, 0.06, 0.09), "seat", xf=back)

    def cabin(self, st):
        """Seats by rows (H-points from the spec), the dash under the screen's foot, the gauges and the wheel square
        to its column (the column runs forward and down to the dash)."""
        L = self.L
        S = L.spec
        rows = st.get("seats", S["seats"])
        n = 0
        drv = st.get("driver", S.get("driver", "L"))
        for r, row in enumerate(rows):
            mid = "seats_%d" % r
            me = self.mod(mid, "seat", "row_%d" % r, "C", hp=300, mass=18 * len(row["xs"]))
            for k, x in enumerate(row["xs"]):
                hz = row["z"]
                w_ = row.get("w", 0.50)
                if (not getattr(L, "wheels_out", False) and abs(x) + w_ / 2 > L.well_x - 0.05 and
                        any(row["y"] - 0.12 < ax + L.arch_half and row["y"] + 0.48 > ax - L.arch_half for ax in L.axles)):
                    hz = max(hz, L.hump_z() + 0.32)          # (a seat over a wheel housing sits up on it)
                self.seat(me, x, row["y"], hz, w_, bench=row.get("bench", False))
                if r == 0 and ((x < 0) == (drv == "L")) and not any(m[0] == "seat_driver" for m in self.MARKERS):
                    self.marker("seat_driver", (x, row["y"], row["z"]))
                else:
                    n += 1
                    self.marker("seat_%d" % n, (x, row["y"], row["z"]))
        dx = [m for m in self.MARKERS if m[0] == "seat_driver"][0][1]
        me = self.mod("dash", "dash", "dash", "C", hp=400, mass=14)
        top = L.top_z(L.toe) - 0.04 if hasattr(L, "top_z") else self.top_z(L.toe) - 0.04
        yd = S.get("dash_y", L.toe - 0.15)
        hw = L.half_w - L.int_off - 0.08
        me.box((0, yd, top), (hw, 0.14, 0.05), "dash")
        me.box((0, yd - 0.12, top - 0.10), (hw - 0.02, 0.05, 0.09), "dash")
        me.box((dx[0], yd - 0.16, top + 0.02), (0.17, 0.05, 0.05), "dash")
        for gx in (dx[0] - 0.07, dx[0] + 0.07):
            me.lathe([(0.0, 0.045), (0.004, 0.045), (0.005, 0.0001)], "gauge", n=16, xf=Matrix.Translation((gx, yd - 0.215, top + 0.02)))
        # the dot-matrix readout under the gauges (range, charge, the trip: the Steward's monochrome LCD) -- its own token
        rd = self.mod("readout", "dash", "readout", "C", hp=60, mass=0.3, breaks="shatter")
        rd.box((dx[0], yd - 0.213, top - 0.04), (0.075, 0.003, 0.02), "black")
        rd.box((dx[0], yd - 0.217, top - 0.04), (0.068, 0.002, 0.015), "lcd")
        c = Vector((dx[0], dx[1] + 0.44, dx[2] + 0.25))
        tilt = Matrix.Rotation(math.radians(68), 4, "X")
        ring = [c + tilt @ Vector((0.19 * math.cos(TAU * k / 24), 0.19 * math.sin(TAU * k / 24), 0)) for k in range(25)]
        me.pipe(ring, 0.014, "black", n=8, caps=False)
        for a in (0.0, math.pi):
            me.pipe([c, c + tilt @ Vector((0.19 * math.cos(a), 0.19 * math.sin(a) * 0.3 - 0.05, 0))], 0.012, "chrome", n=6)
        me.pipe([c, c + Vector((0, 0.25, -0.10))], 0.025, "black", n=8)
        self.marker("steering", tuple(c))
        self.marker("light_cabin", (0, (L.header + L.cab_end) / 2, L.headliner - 0.04))

    def cabin_points(self):
        L = self.L
        pts = []
        y = L.toe - 0.25
        while y > L.cab_end + 0.2:
            for x in (-0.3, 0.0, 0.3):
                for z in (L.floor + 0.45, L.belt + 0.15, L.headliner - 0.15):
                    if z < L.belt and (abs(x) > 0.2 or L.in_well(y)):
                        continue
                    if L.header < y <= L.toe and z > L.a_line(y) - 0.12:
                        continue
                    if L.rear["kind"] == "trunk" and y < L.rear["c_top"] and z > L.c_line(y) - 0.12:
                        continue
                    pts.append([round(x, 4), round(z, 4), round(-y, 4)])
            y -= 0.45
        return pts

    # ============================================================ cargo modules (behind a cab: bed, box, tank, deck)
    def cargo_stations(self, C):
        L = self.L
        ys = {C["y0"], C["y1"]}
        low = C["floor_z"] < L.arch_top + 0.05 and not C.get("no_arch")
        for w in C.get("windows", []) + C.get("vents", []):
            ys |= {w["y0"], w["y1"]}
        for ax in L.axles:
            if C["y1"] < ax < C["y0"] and low:
                ys |= {ax + L.arch_half * f for f in LOFT._ARC} | {ax + L.arch_half, ax - L.arch_half}
        for d in C.get("doors", []):
            ys |= {d["y0"], d["y1"]}
        n = int(math.ceil((C["y0"] - C["y1"]) / 0.5))
        ys |= {C["y0"] - (C["y0"] - C["y1"]) * k / n for k in range(n + 1)}
        return sorted({round(y, 4) for y in ys}, reverse=True), low

    def cargo_rings(self, C):
        """The cargo module's frame rings (the standard's 14 joints): in its floor slab, walls and roof, and in the
        plinth under it -- every tube inside a cavity."""
        L = self.L
        hw, fz, tz = C["half_w"], C["floor_z"], C.get("top_z", C.get("rail_z"))
        open_top = C["kind"] in ("bed", "dump", "deck", "tank")
        plinth = fz - 0.06 > 0.56
        mx = L.mount_x - 0.03
        ys, _ = self.cargo_stations(C)
        low = fz < L.arch_top + 0.05 and not C.get("no_arch")
        sk = max(L.skirt + 0.04, L.deck + 0.01) if hw - 0.03 <= L.mount_x else L.skirt + 0.04   # (a tub on the deck: its foot on the deck, not through it)
        spans = [(ax + L.arch_half + 0.03, ax - L.arch_half - 0.03) for ax in L.axles if low and C["y1"] < ax < C["y0"]]
        tank = C["kind"] == "tank"
        end = 0.30 if tank else 0.03                        # (a tank's rings start behind its dished ends: in front, a ring
        want = [C["y0"] - end, C["y1"] + end]               #  stood in the dish, outside the tank)
        for a, b in spans:                                  # (rings either side of an arch, never in it)
            want += [a, b]
        y = C["y0"] - end
        while y - 0.9 > C["y1"] + end:
            y -= 0.75
            want.append(y)
        for d in C.get("doors", []):
            want += [d["y0"] + 0.035, d["y1"] - 0.035]
        want = sorted({round(v, 3) for v in want if C["y1"] < v < C["y0"] and not any(b < v < a for a, b in spans)}, reverse=True)
        out_w = []
        for v in want:
            if not out_w or out_w[-1] - v >= 0.05:
                out_w.append(v)
        no_cab = getattr(L, "no_cab", False)
        # the joining ring: the cargo's first, in the middle of its front wall's cavity (on the face its tubes stood half
        # out of it; ahead of it, they climbed to the cargo's height through the air over the cab's roof), no higher and no
        # wider than the cab's own outline at its very tail
        # (2026-10-04: in the cab's own end cavity, so the step from the cab's outline down to a lower cargo's -- a bed, a
        #  tank, a plinth narrower than the cab -- happens inside a closed cavity, not in the air between cab and cargo)
        ty = round(C["y0"] - 0.03, 4) if no_cab else round(L.tail + 0.015, 4)
        if not no_cab:
            out_w = [v for v in out_w if abs(v - ty) >= 0.04]
        want = ([] if no_cab else [ty]) + out_w
        cab = {} if no_cab else {j[0]: (j[1], j[2]) for j in L.ring_at(L.tail + 0.005)}
        rings = []
        for y in want:
            if C["kind"] == "tank":
                r = C["tank_r"]
                cz = C["tank_z"]
                # (low joints in the saddle -- continuous under the tank -- the rest inside the tank itself)
                j = {"skirt": (mx, 0.56), "sill": (mx, fz - 0.03), "belt": (min(r * 0.6, mx), fz + 0.05), "head": (r * 0.5, cz - r * 0.65),
                     "cant": (r * 0.55, cz + r * 0.7), "roof": (r * 0.3, cz + r * 0.85), "crown": (0.0, cz + r * 0.88)}
            elif open_top:
                rz = tz - 0.03
                j = {"skirt": ((mx, 0.56) if plinth else (hw - 0.03, sk)), "sill": ((mx if plinth else hw - 0.03), fz - 0.03),
                     "belt": (hw - 0.03, fz - 0.03), "head": (hw - 0.03, rz), "cant": (hw - 0.03, rz),
                     "roof": (hw * 0.6, fz - 0.03), "crown": (0.0, fz - 0.03)}
                if C["kind"] == "deck":
                    j["belt"] = j["head"] = j["cant"] = (hw - 0.03, fz - 0.03)
                elif low:                                   # (the bed's belt rail runs over its arches)
                    j["belt"] = (hw - 0.03, L.arch_top + 0.045)
            else:
                j = {"skirt": ((mx, 0.56) if plinth else (hw - 0.03, sk)), "sill": ((mx if plinth else hw - 0.03), fz - 0.03),
                     "belt": (hw - 0.03, fz - 0.03), "head": (hw - 0.03, tz - 0.12), "cant": (hw - 0.06, tz - 0.03),
                     "roof": (hw * 0.6, tz - 0.03), "crown": (0.0, tz - 0.03)}
                if low:                                     # (a box's belt rail runs over its arches too, not through them)
                    j["belt"] = (hw - 0.03, L.arch_top + 0.045)
            if not no_cab and y == ty:                       # (the shared plane: no higher, no wider than the cab's own)
                for k in j:
                    cx, cz = cab[k + ("_R" if k not in ("crown",) else "")]
                    j[k] = (min(j[k][0], abs(cx)) if k != "crown" else 0.0, min(j[k][1], cz))
                if plinth:                                   # (its foot in the plinth, not under it)
                    j["skirt"] = (j["skirt"][0], max(j["skirt"][1], 0.535))
            out = []
            on_board = abs(y) <= L.board["length_m"] / 2 - 0.04
            for nm in LOFT.RING_NAMES:
                if nm == "floor_C":                         # (the keel: in the board's deck, or past its end in the floor slab)
                    out.append([nm, 0.0, round(L.deck + 0.015 if on_board else fz - 0.03, 4)])
                    continue
                base, _, side = nm.partition("_")
                x, z = j[base]
                out.append([nm, round(-x if side == "L" else x, 4), round(z, 4)])
            rings.append({"y": y, "joints": out})
        tops = [[C["y1"], round(C["y0"] + 0.035, 4), "cargo"]] if open_top else []
        return rings, tops

    def wall(self, me, x, ys, zfn, m, flip=False, holes=()):
        """A flat side wall at x: cells between successive height rows zfn(y) -> [z0, z1, ...] at stations ys;
        holes [(y0, y1, k0, k1)] skip rows k0..k1 within y0..y1."""
        for a, b in zip(ys, ys[1:]):
            za, zb = zfn(a), zfn(b)
            for k in range(len(za) - 1):
                if any(h[1] - 1e-9 <= b and a <= h[0] + 1e-9 and h[2] <= k < h[3] for h in holes):
                    continue
                q = [(x, a, za[k]), (x, b, zb[k]), (x, b, zb[k + 1]), (x, a, za[k + 1])]
                if abs(za[k + 1] - za[k]) < 1e-6 and abs(zb[k + 1] - zb[k]) < 1e-6:
                    continue
                me.face(q if (x > 0) != flip else list(reversed(q)), m)

    def cargo(self, C, st):
        """A cargo module from C['y0'] (its front, against the cab's back) to C['y1']: kinds 'box' (walls, roof, a rear
        closer), 'bed' / 'dump' (open: walls with a rail, a tailgate), 'tank' (a cylinder on a cradle), 'deck' (a flat
        deck: a fifth wheel, a turntable). Under it a closed plinth down to the board's deck where it rides high."""
        L = self.L
        hw, fz = C["half_w"], C["floor_z"]
        t = 0.06
        y0, y1 = C["y0"], C["y1"]
        ys, low = self.cargo_stations(C)
        pm = st["panel"].get("cargo", st["panel"]["lower"])
        plinth = fz - t > 0.56
        mx = min(L.mount_x + 0.04, L.track / 2 - getattr(L, "tyre_w", 0.2) / 2 - 0.05)    # (inboard of the tyres)
        bot = L.skirt if not plinth else fz - t
        arches = [(min(ax + L.arch_half, y0), max(ax - L.arch_half, y1)) for ax in L.axles if y1 < ax < y0] if low else []   # (clipped to the module)
        arches.sort(key=lambda q: -q[0])
        merged = []
        for a_, b_ in arches:                                # (tandem axles' spans overlap: one housing over both)
            if merged and a_ >= merged[-1][1] - 1e-6:
                merged[-1] = (merged[-1][0], min(merged[-1][1], b_))
            else:
                merged.append((a_, b_))
        arches = merged

        def arch_z(y):
            return L.arch_z(y) if any(b - 1e-6 <= y <= a + 1e-6 for a, b in arches) else None
        kind = C["kind"]
        if plinth:                                          # the closed plinth: fairings inboard of the wheels, end plates
            me = self.mod("cargo_plinth", "cargo_wall", "cargo_plinth", "C", hp=900, mass=40)
            for sx in (1, -1):
                self.wall(me, sx * mx, [y0, y1], lambda y: [0.505, fz - t], "black")
            for yy, sg in ((y0, 1), (y1, -1)):
                q = [(-mx, yy, 0.505), (mx, yy, 0.505), (mx, yy, fz - t), (-mx, yy, fz - t)]
                me.face(q if sg < 0 else list(reversed(q)), "black")
            # its belly pan: a ladder-frame board (a trailer's, a rail car's) has no deck to close it, nor has any board
            # past its own end
            me.face([(-mx, y0, 0.505), (-mx, y1, 0.505), (mx, y1, 0.505), (mx, y0, 0.505)], "black")
        if kind == "tank":
            self.cargo_tank(C, st, ys)
            return
        top = C.get("top_z", C.get("rail_z"))
        # ---- the side walls (outer skin, inner lining) and the wheel housings
        wins = C.get("windows", []) + C.get("vents", [])
        for sd in SIDES:
            sx = 1 if sd == "R" else -1
            me = self.mod("cargo_side_" + sd, "cargo_wall", "cargo_side", sd, hp=900, mass=60)
            # (a door's hole only in the walls it's on: a caravan's door is on one side, and the other wall stood open)
            holes = [(d["y0"], d["y1"], 1, 2) for d in C.get("doors", []) if sd in d.get("sides", "RL")]

            wz = C.get("win_z", (fz + 0.90, top - 0.30))
            mine = [w for w in wins if sd in w.get("sides", "RL")]

            # rows: [bot, (the arch's top,) the doors' sill, (the windows' foot and head,) top] -- a low wall's doors start at
            # the sill too, not down at its foot (an open slot under every door)
            off = 1 if low else 0

            def zo(y):
                az = arch_z(y)
                base = [bot, az if az else bot, max(az if az else bot, fz + 0.15)] if low else [bot, fz + 0.15]
                return base + ([wz[0], wz[1], top] if wins else [top])
            hs = [(a, b, 0, 1) for a, b in arches] + [(h[0], h[1], 1 + off, (2 if not wins else 4) + off) for h in holes] + \
                 [(w["y0"], w["y1"], 2 + off, 3 + off) for w in mine]
            self.wall(me, sx * hw, ys, zo, pm, holes=hs)
            mi = self.mod("cargo_lining_" + sd, "cargo_lining", "cargo_side", sd, hp=300, mass=20)
            tl = top - (t if kind == "box" else 0.0)
            hzA = L.arch_top + 0.04                          # (a wheel housing's top: over the round arch's)

            def zl(y):
                r1 = hzA if any(bb - 1e-6 <= y <= aa + 1e-6 for aa, bb in arches) else fz + 0.15
                return [fz, max(r1, fz + 0.15)] + ([max(wz[0], r1 + 0.05), wz[1], tl] if wins else [tl])
            self.wall(mi, sx * (hw - t), ys, zl, C.get("lining", "lining"), flip=True,
                      holes=[(h[0], h[1], 1, 2 if not wins else 4) for h in holes] + [(w["y0"], w["y1"], 2, 3) for w in mine] +
                            [(aa, bb, 0, 1) for aa, bb in arches])
            for d in C.get("doors", []):                    # (a door's reveal: the cavity between skin and lining stops at the jamb)
                if sd not in d.get("sides", "RL"):
                    continue
                rv = self.mod("cargo_reveal_%s_%s" % (d["id"], sd), "reveal", "cargo_door_" + d["id"], sd, hp=200, mass=2)
                o = [(sx * hw, d["y0"], fz + 0.15), (sx * hw, d["y1"], fz + 0.15), (sx * hw, d["y1"], top), (sx * hw, d["y0"], top)]
                i = [(sx * (hw - t), d["y0"], fz + 0.15), (sx * (hw - t), d["y1"], fz + 0.15), (sx * (hw - t), d["y1"], tl), (sx * (hw - t), d["y0"], tl)]
                self.strip(rv, o, i, "black")
            for w in mine:                                  # (its reveal, and its pane -- glass, or none for a vent)
                rv = self.mod("cargo_reveal_%s_%s" % (w["id"], sd), "reveal", "cargo_window_" + w["id"], sd, hp=200, mass=2)
                o = [(sx * hw, w["y0"], wz[0]), (sx * hw, w["y1"], wz[0]), (sx * hw, w["y1"], wz[1]), (sx * hw, w["y0"], wz[1])]
                i = [(sx * (hw - t), w["y0"], wz[0]), (sx * (hw - t), w["y1"], wz[0]), (sx * (hw - t), w["y1"], wz[1]), (sx * (hw - t), w["y0"], wz[1])]
                self.strip(rv, o, i, "black")
                if w in C.get("windows", []):
                    gp = self.mod("cargo_pane_%s_%s" % (w["id"], sd), "glazing", "cargo_window_" + w["id"], sd, hp=40, mass=4, breaks="shatter")
                    gp.face(o if sx < 0 else list(reversed(o)), "glass")
                else:
                    for k in range(1, 4):                   # (a vent's slats)
                        z = wz[0] + (wz[1] - wz[0]) * k / 4
                        rv.box((sx * (hw - t / 2), (w["y0"] + w["y1"]) / 2, z), (t / 2, (w["y0"] - w["y1"]) / 2, 0.012), pm)
            for a, b in arches:                              # (a wheel housing: its top, inner wall and ends; open below, the tyre in it)
                hz = L.arch_top + 0.04
                wx = self.housing_x(a, b)
                zb = min(fz - t, L.skirt)
                q = [(sx * wx, a, hz), (sx * wx, b, hz), (sx * (hw - t), b, hz), (sx * (hw - t), a, hz)]
                mi.face(q if sx < 0 else list(reversed(q)), "black")
                q = [(sx * wx, a, zb), (sx * wx, b, zb), (sx * wx, b, hz), (sx * wx, a, hz)]
                mi.face(q if sx > 0 else list(reversed(q)), "black")
                for yy, sg in ((a, 1), (b, -1)):
                    q = [(sx * wx, yy, zb), (sx * (hw - t), yy, zb), (sx * (hw - t), yy, hz), (sx * wx, yy, hz)]
                    mi.face(q if sx * sg > 0 else list(reversed(q)), "black")
            if low:                                          # (the arch's wall from the skin in to the housing, and its lip)
                for a, b in arches:
                    rs = [y for y in ys if b - 1e-6 <= y <= a + 1e-6]
                    # the housing's outer wall: the lining's plane from the lip up to the housing's top (between tandem
                    # wheels the lip dips, and the wall cavity lay open into the housing there)
                    hzA_ = L.arch_top + 0.04
                    self.wall(mi, sx * (hw - t), rs, lambda y: [arch_z(y) or bot, hzA_], "black", flip=True)
                    top_o = [(sx * hw, y, arch_z(y)) for y in rs]
                    top_i = [(sx * (hw - t), y, arch_z(y)) for y in rs]
                    self.strip_open(me, top_o, top_i, "rubber", flip=(sd == "L"))
                    for yy in (a, b):
                        me.face([(sx * hw, yy, bot), (sx * hw, yy, arch_z(yy)), (sx * (hw - t), yy, arch_z(yy)), (sx * (hw - t), yy, bot)], "rubber")
            # the rail / top edge between skin and lining
            rm = self.mod("cargo_rail_" + sd, "cargo_wall", "cargo_rail", sd, hp=400, mass=8)
            rz = top if kind != "box" else top
            if kind != "box":
                rm.face([(sx * hw, y0, rz), (sx * hw, y1, rz), (sx * (hw - t), y1, rz), (sx * (hw - t), y0, rz)][:: (1 if sx > 0 else -1)], st.get("rail", "black"))
            # the bottom: skin in to the board (a low module) -- sill pans, as the body's
            if not plinth and hw > L.mount_x + 1e-6:         # (a tub narrower than its board sits on the deck: no pan out to it)
                for a, b in zip(ys, ys[1:]):
                    if any(bb - 1e-9 <= b and a <= aa + 1e-9 for aa, bb in arches):
                        continue
                    me.face([(sx * hw, a, bot), (sx * hw, b, bot), (sx * L.mount_x, b, bot), (sx * L.mount_x, a, bot)][:: (-1 if sx > 0 else 1)], "rubber")
                    me.face([(sx * L.mount_x, a, bot), (sx * L.mount_x, b, bot), (sx * L.mount_x, b, 0.505), (sx * L.mount_x, a, 0.505)], "rubber")
        # ---- the floor (top and slab edge) and the front wall
        fm = self.mod("cargo_floor", "cargo_floor", "cargo_floor", "C", hp=2000, mass=60)
        fmat = C.get("floor_m", "tub")
        if arches:                                          # (notched round the wheel housings)
            wxs = min(self.housing_x(a, b) for a, b in arches)
            fm.face([(-wxs, y0 - t, fz), (wxs, y0 - t, fz), (wxs, y1, fz), (-wxs, y1, fz)], fmat)
            edges = [y0 - t] + [v for ab in sorted(arches, key=lambda q: -q[0]) for v in ab] + [y1]
            for k in range(0, len(edges), 2):
                ya_, yb_ = edges[k], edges[k + 1]
                if ya_ - yb_ > 0.01:
                    for sx in (1, -1):
                        q = [(sx * wxs, ya_, fz), (sx * (hw - t), ya_, fz), (sx * (hw - t), yb_, fz), (sx * wxs, yb_, fz)]
                        fm.face(q if sx < 0 else list(reversed(q)), fmat)
        else:
            fm.face([(-(hw - t), y0 - t, fz), (hw - t, y0 - t, fz), (hw - t, y1, fz), (-(hw - t), y1, fz)], fmat)
        if not plinth:
            ux = min(L.mount_x, hw)
            fm.face([(-ux, y0, fz - t), (ux, y0, fz - t), (ux, y1, fz - t), (-ux, y1, fz - t)], "rubber")
        else:
            fm.face([(-hw, y0, fz - t), (-hw, y1, fz - t), (hw, y1, fz - t), (hw, y0, fz - t)], "black")
            for sx in (1, -1):
                fm.face([(sx * hw, y0, fz - t), (sx * hw, y1, fz - t), (sx * mx, y1, fz - t), (sx * mx, y0, fz - t)], "black")
        me = self.mod("cargo_front", "cargo_wall", "cargo_front", "C", hp=900, mass=30)
        q = [(-hw, y0, bot), (hw, y0, bot), (hw, y0, top), (-hw, y0, top)]
        me.face(list(reversed(q)), pm)
        mi = self.mod("cargo_front_lining", "cargo_lining", "cargo_front", "C", hp=300, mass=10)
        mi.face([(-(hw - t), y0 - t, fz), (hw - t, y0 - t, fz), (hw - t, y0 - t, top - (t if kind == "box" else 0)), (-(hw - t), y0 - t, top - (t if kind == "box" else 0))], C.get("lining", "lining"))
        if kind != "box":
            me.face([(-hw, y0, top), (hw, y0, top), (hw, y0 - t, top), (-hw, y0 - t, top)], st.get("rail", "black"))
        # ---- the roof
        if kind == "box":
            rm = self.mod("cargo_roof", "cargo_wall", "cargo_roof", "C", hp=900, mass=40)
            rm.face([(-hw, y0, top), (hw, y0, top), (hw, y1, top), (-hw, y1, top)], st["panel"].get("cargo_roof", pm))
            ri = self.mod("cargo_ceiling", "cargo_lining", "cargo_roof", "C", hp=200, mass=10)
            ri.face([(-(hw - t), y0 - t, top - t), (-(hw - t), y1, top - t), (hw - t, y1, top - t), (hw - t, y0 - t, top - t)], C.get("lining", "lining"))
        # ---- the rear: a portal with its closer
        self.cargo_rear(C, st, bot, top, pm)
        for d in C.get("doors", []):
            self.cargo_side_door(C, d, st, pm)

    def cargo_rear(self, C, st, bot, top, pm):
        L = self.L
        hw, fz, y1 = C["half_w"], C["floor_z"], C["y1"]
        t = 0.06
        rear = C.get("rear", "tailgate")
        me = self.mod("cargo_rear_frame", "cargo_wall", "cargo_rear", "C", hp=900, mass=20)
        if rear == "closed":                                 # (a closed end: a caravan's back wall, lined)
            me.face([(-hw, y1, bot), (-hw, y1, top), (hw, y1, top), (hw, y1, bot)], pm)
            mi = self.mod("cargo_rear_lining", "cargo_lining", "cargo_rear", "C", hp=300, mass=8)
            mi.face([(-(hw - t), y1 + t, fz), (hw - t, y1 + t, fz), (hw - t, y1 + t, top - t), (-(hw - t), y1 + t, top - t)], "lining")
            return
        if rear in ("tailgate", "none"):
            gz = top
            op = (hw - t, fz, gz)
        else:
            op = (hw - 0.08, fz, top - (0.10 if C["kind"] == "box" else 0.0))
        ow, oz0, oz1 = op
        # the end face round the opening (outer), the jambs in to the lining
        face = [(-hw, y1, bot), (hw, y1, bot), (hw, y1, top), (-hw, y1, top)]
        hole = [(-ow, y1, oz0), (ow, y1, oz0), (ow, y1, oz1), (-ow, y1, oz1)]
        self.cap(me, face, [hole], pm, -1)
        inner = [(-ow, y1 + t, oz0), (ow, y1 + t, oz0), (ow, y1 + t, oz1), (-ow, y1 + t, oz1)]
        self.strip(me, hole, inner, "black")
        if rear == "none":
            return
        parts = []
        if rear == "tailgate":                                # bottom-hinged, opens down flat
            gm = self.mod("tailgate", "hatch", "tailgate", "C", hp=700, mass=30)
            gm.box((0, y1 + t / 2, (oz0 + oz1) / 2), (ow - GAP, t / 2 - 0.004, (oz1 - oz0) / 2 - GAP), pm)
            gm.box((0, y1 - 0.004, oz1 - 0.12), (0.12, 0.004, 0.02), "chrome")
            self.CLOSERS.append({"id": "tailgate", "kind": "hatch", "side": "C", "parts": ["tailgate"],
                                 "hinge": [(-ow, y1 + t / 2, oz0), (ow, y1 + t / 2, oz0)], "open_deg": 90})
        elif rear == "rollup":                                 # a roll-up door: slides up into the roof
            gm = self.mod("rollup", "hatch", "rollup", "C", hp=600, mass=40)
            gm.box((0, y1 + t / 2, (oz0 + oz1) / 2), (ow - GAP, t / 2 - 0.004, (oz1 - oz0) / 2 - GAP), "chrome")
            k = oz0 + 0.12
            while k < oz1 - 0.05:
                gm.box((0, y1 - 0.002, k), (ow - 0.02, 0.003, 0.004), "black")
                k += 0.12
            gm.box((0, y1 - 0.01, oz0 + 0.08), (0.10, 0.01, 0.015), "black")
            self.CLOSERS.append({"id": "rollup", "kind": "roll", "side": "C", "parts": ["rollup"],      # (rolls up into its head)
                                 "hinge": [(-ow, y1 + t / 2, oz1 - GAP), (ow, y1 + t / 2, oz1 - GAP)], "open_deg": 0})
        elif rear == "barn":
            for sd, sx in (("R", 1), ("L", -1)):
                gm = self.mod("cargo_barn_" + sd, "hatch", "cargo_barn_" + sd, sd, hp=600, mass=30)
                gm.box((sx * ow / 2, y1 + t / 2, (oz0 + oz1) / 2), (ow / 2 - GAP, t / 2 - 0.004, (oz1 - oz0) / 2 - GAP), pm)
                gm.box((sx * 0.06, y1 - 0.004, (oz0 + oz1) / 2), (0.012, 0.004, 0.25), "chrome")
                self.CLOSERS.append({"id": "cargo_barn_" + sd, "kind": "door", "side": sd, "parts": ["cargo_barn_" + sd],
                                     "hinge": [(sx * ow, y1, oz0), (sx * ow, y1, oz1)], "open_deg": 100 * sx})
        elif rear == "hopper":                                 # a refuse body's tailgate: the whole rear lifts
            gm = self.mod("hopper", "hatch", "hopper", "C", hp=900, mass=120)
            gm.box((0, y1 - 0.30, (oz0 + oz1) / 2), (hw - 0.02, 0.30, (oz1 - oz0) / 2), pm)
            gm.box((0, y1 - 0.55, oz0 + 0.30), (hw - 0.12, 0.08, 0.20), "black")
            self.CLOSERS.append({"id": "hopper", "kind": "hatch", "side": "C", "parts": ["hopper"],
                                 "hinge": [(-hw, y1, oz1), (hw, y1, oz1)], "open_deg": -55})
        self.marker("stand_cargo", (0, y1 - 0.8, 0.0), math.pi)

    def cargo_side_door(self, C, d, st, pm):
        """A door in a box's side: a roll-up shutter (fire engines' lockers), or a hinged entry door (a caravan's)."""
        hw, fz = C["half_w"], C["floor_z"]
        if d.get("kind") == "hinge":
            for sd in d.get("sides", "R"):
                sx = 1 if sd == "R" else -1
                mid = "cdoor_%s_%s" % (d["id"], sd)
                gm = self.mod(mid, "door_leaf", "cdoor_" + d["id"], sd, hp=500, mass=18)
                z0, z1 = fz + 0.15, C.get("top_z")
                gm.box((sx * (hw - 0.03), (d["y0"] + d["y1"]) / 2, (z0 + z1) / 2), (0.028, (d["y0"] - d["y1"]) / 2 - GAP, (z1 - z0) / 2 - GAP), pm)
                gm.box((sx * (hw + 0.004), d["y1"] + 0.08, (z0 + z1) / 2), (0.006, 0.03, 0.06), "chrome")
                self.CLOSERS.append({"id": mid, "kind": "door", "side": sd, "parts": [mid], "y0": d["y0"], "y1": d["y1"], "sill": z0, "head": z1,
                                     "hinge": [(sx * hw, d["y0"], z0), (sx * hw, d["y0"], z1)], "open_deg": 95 * sx})
            return
        for sd in d.get("sides", "RL"):
            sx = 1 if sd == "R" else -1
            mid = "cdoor_%s_%s" % (d["id"], sd)
            gm = self.mod(mid, "hatch", "cdoor_" + d["id"], sd, hp=500, mass=12)
            z0, z1 = fz + 0.15, C.get("top_z") - 0.0
            gm.box((sx * (hw - 0.03), (d["y0"] + d["y1"]) / 2, (z0 + z1) / 2), (0.028, (d["y0"] - d["y1"]) / 2 - GAP, (z1 - z0) / 2 - GAP), "chrome")
            k = z0 + 0.1
            while k < z1 - 0.05:
                gm.box((sx * (hw + 0.001), (d["y0"] + d["y1"]) / 2, k), (0.002, (d["y0"] - d["y1"]) / 2 - 0.02, 0.003), "black")
                k += 0.1
            self.CLOSERS.append({"id": mid, "kind": "roll", "side": sd, "parts": [mid], "y0": d["y0"], "y1": d["y1"], "sill": z0, "head": z1,
                                 "hinge": [(sx * (hw - 0.03), d["y0"], z1 - GAP), (sx * (hw - 0.03), d["y1"], z1 - GAP)], "open_deg": 0})

    def cargo_tank(self, C, st, ys):
        L = self.L
        r, cz = C["tank_r"], C["tank_z"]
        y0, y1 = C["y0"], C["y1"]
        me = self.mod("tank", "cargo_wall", "tank", "C", hp=1500, mass=400)
        me.lathe([(-(y0 - 0.25), 0.0001), (-(y0 - 0.08), r * 0.75), (-(y0 - 0.02), r * 0.96), (-y0, r)] +
                 [(-y1, r), (-(y1 + 0.02), r * 0.96), (-(y1 + 0.08), r * 0.75), (-(y1 + 0.25), 0.0001)],
                 st["panel"].get("cargo", "chrome"), n=24, xf=Matrix.Translation((0, 0, cz)) @ Matrix.Rotation(math.pi, 4, "Z"))
        cr = self.mod("tank_cradle", "cargo_wall", "tank_cradle", "C", hp=900, mass=60)
        fz = C["floor_z"]
        # the saddle: continuous under the tank, its whole length (the frame's low members run inside it)
        cr.box((0, (y0 + y1) / 2, (fz + cz - r * 0.6) / 2), (r * 0.7, (y0 - y1) / 2, (cz - r * 0.6 - fz) / 2 + 0.02), "black")
        cr.box((0, (y0 + y1) / 2, fz - 0.03), (L.mount_x + 0.04, (y0 - y1) / 2, 0.03), "black")
        wk = self.mod("tank_walk", "equipment", "tank_walk", "C", hp=200, mass=20)
        wk.box((0, (y0 + y1) / 2, cz + r + 0.02), (0.22, (y0 - y1) / 2 - 0.3, 0.015), "black")
        for y in (y0 - 0.6, y1 + 0.6):
            wk.lathe([(0.0, 0.22), (0.10, 0.22), (0.11, 0.0001)], "chrome", n=16,
                     xf=Matrix.Translation((0, y, cz + r - 0.02)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))

    def equipment_x(self, kind, st):
        """The working equipment of the trucks, vans and buses (each its own token)."""
        L = self.L
        C = L.spec.get("cargo") or {}
        X = Matrix.Translation
        if kind == "reefer_unit":                          # a refrigeration unit on the box's front, above the cab
            me = self.mod("reefer", "equipment", "reefer", "C", hp=300, mass=180)
            y = C["y0"] + 0.18
            me.box((0, y, C["top_z"] - 0.45), (0.85, 0.18, 0.40), "paint2")
            for k in range(5):
                me.box((-0.6 + k * 0.3, y + 0.185, C["top_z"] - 0.45), (0.11, 0.004, 0.30), "black")
        elif kind == "hose_bed":                            # a fire body's hose bed: a trough on top, the hose folded in it
            me = self.mod("hose_bed", "equipment", "hose_bed", "C", hp=300, mass=200)
            y0, y1 = C["y0"] - 0.6, C["y1"] + 0.2
            t = C["top_z"]
            me.box((0, (y0 + y1) / 2, t + 0.08), (C["half_w"] - 0.25, (y0 - y1) / 2, 0.08), "black")
            for k in range(6):
                me.box((-0.7 + k * 0.28, (y0 + y1) / 2, t + 0.17), (0.12, (y0 - y1) / 2 - 0.05, 0.03), "livery1")
        elif kind == "fire_ladders":                        # ground ladders racked along the body's side
            me = self.mod("fire_ladders", "equipment", "ladder_rack", "C", hp=200, mass=60)
            for sx in (1, -1):
                x = sx * (C["half_w"] + 0.06)
                z = C["top_z"] - 0.25
                for dz in (0.0, 0.10):
                    me.box((x, (C["y0"] + C["y1"]) / 2, z + dz), (0.02, (C["y0"] - C["y1"]) / 2 - 0.4, 0.02), "chrome")
        elif kind == "aerial_ladder":                       # a turntable and a three-section ladder bedded over the cab
            me = self.mod("aerial", "equipment", "aerial_ladder", "C", hp=900, mass=1800)
            yt = C["y1"] + 1.0
            t = C.get("top_z", C.get("rail_z"))
            me.lathe([(0.0, 0.70), (0.25, 0.70), (0.26, 0.0001)], "paint2", n=24, xf=X((0, yt, t)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
            me.box((0, yt, t + 0.45), (0.40, 0.45, 0.20), "paint")
            y_tip = L.nose - 0.3
            for k, w in enumerate((0.36, 0.30, 0.24)):
                ya = yt + 0.2 + k * 0.6
                for sx in (1, -1):
                    me.box((sx * w, (ya + y_tip) / 2, t + 0.70 + k * 0.10), (0.03, (y_tip - ya) / 2, 0.05), "chrome")
                y = ya + 0.2
                while y < y_tip:
                    me.box((0, y, t + 0.70 + k * 0.10), (w, 0.015, 0.015), "chrome")
                    y += 0.35
        elif kind == "bucket_boom":                         # a utility truck's insulated boom and bucket, stowed forward
            me = self.mod("bucket_boom", "equipment", "boom", "C", hp=600, mass=600)
            y = C["y1"] + 0.5
            t = C.get("rail_z", C.get("top_z"))
            me.lathe([(0.0, 0.30), (0.40, 0.30), (0.41, 0.0001)], "paint2", n=16, xf=X((0, y, t)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
            me.pipe([Vector((0, y, t + 0.45)), Vector((0, L.tail_in + 0.3, L.crown + 0.25))], 0.10, "paint2", n=10)
            me.box((0, L.tail_in + 0.1, L.crown + 0.30), (0.35, 0.35, 0.45), "livery2")
        elif kind == "wheel_lift":                          # a wrecker's boom and wheel lift
            me = self.mod("wrecker", "equipment", "wrecker", "C", hp=700, mass=500)
            y = C["y1"] + 0.6
            t = C.get("rail_z")
            me.box((0, y, t + 0.40), (0.35, 0.35, 0.40), "black")
            me.pipe([Vector((0, y, t + 0.75)), Vector((0, C["y1"] - 0.3, t + 1.10))], 0.09, "paint2", n=10)
            me.box((0, C["y1"] - 0.35, 0.40), (0.70, 0.12, 0.05), "black")
            me.pipe([Vector((0, C["y1"] + 0.2, 0.55)), Vector((0, C["y1"] - 0.35, 0.42))], 0.06, "black", n=8)
        elif kind == "sweeper_brushes":
            me = self.mod("brushes", "equipment", "brushes", "C", hp=200, mass=120)
            for sx in (1, -1):
                me.lathe([(0.0, 0.42), (0.04, 0.42), (0.05, 0.0001)], "lamp_amber", n=20,
                         xf=X((sx * (L.half_w - 0.1), L.nose - 0.55, 0.06)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
            me.lathe([(-0.9, 0.25), (0.9, 0.25)], "black", n=14, xf=X((0, (L.axles[0] + L.axles[1]) / 2 - 0.2, 0.27)) @ Matrix.Rotation(math.pi / 2, 4, "Z"))
        elif kind == "fifth_wheel":
            me = self.mod("fifth_wheel", "equipment", "fifth_wheel", "C", hp=900, mass=300)
            y = (C["y0"] + C["y1"]) / 2 - 0.4
            fz = C["floor_z"]
            me.lathe([(0.0, 0.55), (0.10, 0.55), (0.11, 0.0001)], "black", n=24, xf=X((0, y, fz)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
            me.box((0, y - 0.35, fz + 0.12), (0.08, 0.30, 0.02), "black")
            for sx in (1, -1):
                me.box((sx * 0.5, C["y1"] + 0.3, fz + 0.20), (0.12, 0.12, 0.20), "black")
        elif kind == "side_arm":                            # a recycling truck's side-loading arm
            me = self.mod("side_arm", "equipment", "side_arm", "R", hp=400, mass=300)
            y = C["y0"] - 0.6
            me.box((C["half_w"] + 0.10, y, C["floor_z"] + 0.4), (0.10, 0.25, 0.35), "black")
            me.pipe([Vector((C["half_w"] + 0.15, y, C["floor_z"] + 0.6)), Vector((C["half_w"] + 0.15, y, C["top_z"] - 0.1))], 0.06, "chrome", n=8)
        elif kind in ("awning", "cone_sign", "menu"):       # a serving van: the hatch's awning over the left windows
            if kind == "awning":
                me = self.mod("awning", "equipment", "awning", "L", hp=100, mass=15)
                w = [w for w in L.windows if "L" in w.get("sides", "RL")][0]
                x = -(L.half_w + 0.02)
                z = L.head + 0.05
                me.face([(x, w["y0"], z), (x - 0.55, w["y0"], z - 0.18), (x - 0.55, w["y1"], z - 0.18), (x, w["y1"], z)], "livery2")
                me.box((x - 0.04, (w["y0"] + w["y1"]) / 2, L.belt - 0.02), (0.06, (w["y0"] - w["y1"]) / 2, 0.02), "chrome")
            elif kind == "cone_sign":
                me = self.mod("cone_sign", "equipment", "roof_sign", "C", hp=60, mass=8)
                y = L.header - 0.8
                me.lathe([(0.0, 0.0001), (0.55, 0.16), (0.56, 0.0001)], "wood", n=16, xf=X((0, y, L.crown)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
                me.lathe([(0.0, 0.17), (0.12, 0.20), (0.25, 0.0001)], "livery1", n=16, xf=X((0, y, L.crown + 0.55)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
            else:
                me = self.mod("menu", "equipment", "menu_board", "L", hp=60, mass=4)
                z0, z1 = L.arch_top + 0.04, L.belt - 0.02                 # (above the wheel arch, below the windows)
                me.box((-(L.half_w + 0.01), L.tail_in + 0.6, (z0 + z1) / 2), (0.01, 0.35, (z1 - z0) / 2), "sign")
        elif kind == "dest_sign":                           # a dot-matrix destination sign behind the screen's head
            me = self.mod("dest_sign", "equipment", "dest_sign", "C", hp=60, mass=3, breaks="shatter")
            y = L.header - 0.06
            z = L.headliner - 0.10
            me.box((0, y, z), (0.55, 0.03, 0.08), "black")
            me.box((0, y + 0.032, z), (0.50, 0.002, 0.06), "lcd")
        elif kind == "stop_arm":                            # FMVSS 131: the school bus's stop signal arm, on the driver's side
            me = self.mod("stop_arm", "equipment", "stop_arm", "L", hp=60, mass=3)
            y = L.nose - 1.6
            x = -(L.half_w + 0.04)
            me.lathe([(0.0, 0.23), (0.02, 0.23), (0.025, 0.0001)], "livery2", n=8,
                     xf=X((x, y, L.belt - 0.05)) @ Matrix.Rotation(math.pi / 2, 4, "Z") @ Matrix.Rotation(math.pi / 8, 4, "Y"))
        elif kind == "crossview_mirrors":                   # FMVSS 111: school bus cross-view mirrors on the front corners
            me = self.mod("crossview", "equipment", "crossview_mirrors", "C", hp=80, mass=4)
            for sx in (1, -1):
                base = Vector((sx * (L.half_w - 0.05), L.nose - 0.05, L.belt - 0.10))
                tip = Vector((sx * (L.half_w + 0.10), L.nose + 0.35, L.belt + 0.10))
                me.pipe([base, tip], 0.012, "black", n=6)
                me.lathe([(0.0, 0.10), (0.03, 0.10), (0.05, 0.0001)], "black", n=12, xf=X(tip) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
        elif kind == "school_warning":                      # FMVSS 108: eight-lamp warning system, amber outboard of red, front and rear
            me = self.mod("warning_lamps", "lamp", "warning_lamps", "C", hp=40, mass=2, breaks="shatter")
            for yy, sg in ((L.header + 0.02, 1), (L.tail + 0.004, -1)):
                z = L.cant - 0.12 if sg > 0 else L.head + 0.10
                for sx in (1, -1):
                    for k, m in ((0, "lamp_red"), (1, "lamp_amber")):
                        x = sx * (L.half_w - 0.25 - k * 0.22)
                        me.lathe([(0.0, 0.09), (0.03, 0.08), (0.035, 0.0001)], m, n=14,
                                 xf=X((x, yy, z)) @ Matrix.Rotation(0 if sg > 0 else math.pi, 4, "Z"))
        elif kind == "roof_hatches":                        # FMVSS 217: roof exits, 41 x 41 cm and more
            me = self.mod("roof_hatches", "equipment", "roof_hatches", "C", hp=100, mass=20)
            for y in (L.header - 2.0, L.tail + 2.4):
                me.box((0, y, L.crown + 0.01), (0.30, 0.30, 0.02), "black")
                me.box((0, y, L.crown + 0.03), (0.26, 0.26, 0.01), "livery1")
        elif kind == "landau_bars":
            for sd in SIDES:
                sx = 1 if sd == "R" else -1
                me = self.mod("landau_" + sd, "equipment", "landau", sd, hp=60, mass=1)
                y = L.tail_in + 0.55
                z = (L.belt + L.head) / 2
                pts = [Vector((sx * (self.surf_x(y + 0.3 * math.cos(a), z) + 0.008), y + 0.3 * math.cos(a), z + 0.18 * math.sin(a) * math.cos(a)))
                       for a in [k * math.pi / 10 for k in range(11)]]
                me.pipe(pts, 0.012, "chrome", n=6)
        elif kind == "bed_rack":
            me = self.mod("bed_rack", "equipment", "bed_rack", "C", hp=200, mass=30)
            t = C["rail_z"]
            for y in (C["y0"] - 0.15, C["y1"] + 0.25):
                for sx in (1, -1):
                    me.box((sx * (C["half_w"] - 0.03), y, t + 0.35), (0.025, 0.025, 0.35), "black")
                me.box((0, y, t + 0.70), (C["half_w"], 0.025, 0.025), "black")
            for sx in (1, -1):
                me.box((sx * (C["half_w"] - 0.03), (C["y0"] + C["y1"]) / 2, t + 0.70), (0.025, (C["y0"] - C["y1"]) / 2 - 0.1, 0.025), "black")
        elif kind == "toolbox":
            me = self.mod("toolbox", "equipment", "toolbox", "C", hp=300, mass=40)
            me.box((0, C["y0"] - 0.25, C["rail_z"] + 0.04), (C["half_w"] - 0.02, 0.20, 0.10), "chrome")
        elif kind == "soft_top_bows":
            me = self.mod("top_bows", "equipment", "soft_top", "C", hp=60, mass=2)
            y = L.header - 0.2
            while y > L.rear["c_top"]:
                me.pipe([Vector(self.sample("ext", y, s)) + Vector((0, 0, 0.006)) for s in range(self.es(E["head"], "R"), self.es(E["head"], "L") + 1)],
                        0.008, "black", n=6)
                y -= 0.35
        else:
            self.equipment_y(kind, st)

    def equipment_y(self, kind, st):
        """More working equipment (the remainder's road types)."""
        L = self.L
        C = L.spec.get("cargo") or {}
        X = Matrix.Translation
        if kind == "stakes":                                # a flatbed's stake sides
            me = self.mod("stakes", "equipment", "stakes", "C", hp=200, mass=40)
            t = C["floor_z"]
            for sx in (1, -1):
                y = C["y0"] - 0.1
                while y > C["y1"] + 0.05:
                    me.box((sx * (C["half_w"] - 0.03), y, t + 0.30), (0.025, 0.025, 0.30), "wood")
                    y -= 0.42
                for z in (t + 0.25, t + 0.52):
                    me.box((sx * (C["half_w"] - 0.03), (C["y0"] + C["y1"]) / 2, z), (0.015, (C["y0"] - C["y1"]) / 2 - 0.05, 0.05), "wood")
        elif kind == "tarp_bows":
            me = self.mod("tarp_bows", "equipment", "tarp", "C", hp=100, mass=30)
            t = C["rail_z"]
            y = C["y0"] - 0.3
            while y > C["y1"] + 0.2:
                me.pipe([Vector((-C["half_w"] + 0.03, y, t)), Vector((0, y, t + 0.35)), Vector((C["half_w"] - 0.03, y, t))], 0.02, "black", n=6)
                y -= 1.0
        elif kind == "mixer_drum":                          # the revolving drum, tilted up to the rear, its chute
            me = self.mod("mixer_drum", "equipment", "mixer_drum", "C", hp=900, mass=1500)
            y0, y1 = C["y0"] - 0.4, C["y1"] + 0.4
            fz = C["floor_z"]
            tilt = math.atan2(0.6, y0 - y1)
            T = X((0, y0, fz + 1.1)) @ Matrix.Rotation(math.pi + tilt, 4, "X")
            L0 = y0 - y1
            me.lathe([(0.0, 0.35), (0.5, 1.05), (L0 * 0.55, 1.10), (L0 - 0.4, 0.75), (L0, 0.40), (L0 + 0.01, 0.0001)], "paint2", n=24, xf=T)
            for k in range(6):                              # (the drum's spiral fins, outside: stripes)
                a = k / 6.0
                me.lathe([(L0 * (0.15 + a * 0.7), 1.10), (L0 * (0.15 + a * 0.7) + 0.06, 1.11)], "black", n=24, xf=T)
            for y in (y0 - 0.2, y1 + 0.6):
                me.box((0, y, fz + 0.45), (0.45, 0.08, 0.45), "black")
            me.box((0, C["y1"] - 0.25, fz + 0.9), (0.18, 0.40, 0.04), "chrome")
        elif kind == "crane_boom":
            me = self.mod("crane", "equipment", "crane_boom", "C", hp=1200, mass=4000)
            yt = C["y1"] + 1.4
            fz = C["floor_z"]
            me.lathe([(0.0, 0.90), (0.20, 0.90), (0.21, 0.0001)], "black", n=24, xf=X((0, yt, fz)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
            me.box((0, yt, fz + 0.55), (0.75, 0.80, 0.35), "paint")
            me.box((-0.55, yt + 0.3, fz + 1.05), (0.28, 0.40, 0.30), "glass_dark")
            for k, w in enumerate((0.30, 0.24, 0.18)):      # (the telescopic boom, stowed forward over the cab)
                ya = yt + 0.4 + k * 0.4
                me.box((0.15, (ya + L.nose - 0.2) / 2, fz + 1.05 + k * 0.05 + 0.4), (w, (L.nose - 0.2 - ya) / 2, w * 0.8), "paint")
            for y in (C["y0"] - 0.3, C["y1"] + 0.3):        # (the outriggers, stowed)
                for sx in (1, -1):
                    me.box((sx * (C["half_w"] - 0.1), y, fz - 0.2), (0.12, 0.10, 0.12), "black")
        elif kind == "wire_tower":                          # a tram maintenance car's platform for the overhead
            me = self.mod("wire_tower", "equipment", "wire_tower", "C", hp=600, mass=600)
            t = C["top_z"]
            me.box((0, (C["y0"] + C["y1"]) / 2, t + 0.05), (C["half_w"] - 0.1, (C["y0"] - C["y1"]) / 2 - 0.2, 0.05), "black")
            for sx in (1, -1):
                me.box((sx * (C["half_w"] - 0.12), (C["y0"] + C["y1"]) / 2, t + 0.55), (0.02, (C["y0"] - C["y1"]) / 2 - 0.25, 0.02), "lamp_amber")
                for y in (C["y0"] - 0.3, C["y1"] + 0.3):
                    me.box((sx * (C["half_w"] - 0.12), y, t + 0.30), (0.02, 0.02, 0.25), "lamp_amber")
            me.box((0, (C["y0"] + C["y1"]) / 2, t + 0.9), (0.3, 0.3, 0.4), "chrome")
        elif kind == "ac_units":
            me = self.mod("ac_units", "equipment", "roof_ac", "C", hp=200, mass=60)
            for y in (L.header - 1.5, (L.header + L.tail) / 2, L.tail + 1.6):
                me.box((0, y, L.crown + 0.12), (0.45, 0.35, 0.12), "paint2")
                me.box((0, y, L.crown + 0.245), (0.35, 0.25, 0.005), "black")
        elif kind == "side_awning":
            me = self.mod("side_awning", "equipment", "awning", "R", hp=100, mass=30)
            x = L.half_w + 0.03
            me.box((x, (L.header + L.tail) / 2 - 1.0, L.head + 0.12), (0.05, 1.8, 0.06), "chrome")
        elif kind == "dest_sign_front":                     # the dot-matrix sign over the windscreen, outside
            me = self.mod("dest_sign", "equipment", "dest_sign", "C", hp=60, mass=4, breaks="shatter")
            y = L.header + 0.02
            z = (L.cant + L.crown) / 2 - 0.06
            me.box((0, y, z), (0.80, 0.03, 0.10), "black")
            me.box((0, y + 0.032, z), (0.74, 0.002, 0.07), "lcd")
        elif kind == "rescue_boards":
            me = self.mod("rescue_boards", "equipment", "rescue_boards", "C", hp=100, mass=20)
            t = C["rail_z"] + 0.72
            for k in range(2):
                me.box((0, (C["y0"] + C["y1"]) / 2, t + 0.05 + k * 0.10), (0.30, 1.40, 0.04), "livery2" if k else "lamp_amber")
        elif kind == "water_tank":
            me = self.mod("water_tank", "equipment", "water_tank", "C", hp=400, mass=900)
            fz = C["floor_z"]
            tz = max(fz, L.arch_top + 0.05)                  # (up on the wheel housings)
            me.box((0, (C["y0"] + C["y1"]) / 2 + 0.1, tz + 0.32), (C["half_w"] - 0.12, (C["y0"] - C["y1"]) / 2 - 0.25, 0.32), "paint2")
            me.lathe([(-0.25, 0.30), (0.25, 0.30)], "chrome", n=16, xf=X((0, C["y1"] + 0.35, fz + 0.85)) @ Matrix.Rotation(math.pi / 2, 4, "Z"))
        elif kind == "rail_gear":                           # hi-rail guide wheels, front and rear, raised
            me = self.mod("rail_gear", "equipment", "rail_gear", "C", hp=400, mass=200)
            for y in (L.nose + 0.12, (C.get("y1", L.tail)) - 0.12):
                me.box((0, y, 0.48), (0.70, 0.06, 0.06), "black")
                for sx in (1, -1):
                    me.lathe([(-0.04, 0.17), (0.04, 0.17), (0.05, 0.19), (0.06, 0.19)], "chrome", n=16,
                             xf=X((sx * 0.72, y, 0.40)) @ Matrix.Rotation(math.pi / 2, 4, "Z"))
        elif kind == "trolley_bell":
            me = self.mod("trolley_bell", "equipment", "bell", "C", hp=50, mass=8)
            me.lathe([(0.0, 0.0001), (0.02, 0.06), (0.14, 0.10), (0.16, 0.0001)], "chrome", n=16,
                     xf=X((0, L.nose - 0.05, L.belt + 0.25)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
        else:
            self.equipment_z(kind, st)


    # ============================================================ a trailer's own: lamps and its underride guard
    def trailer_dress(self, st):
        """FMVSS 108 on a trailer: red tail / stop / turn lamps low at the rear corners, red reflex reflectors, amber
        front and red rear side markers, and on one 80 in (2,032 mm) wide or more three identification and two clearance
        lamps high at the rear (amber clearance lamps at the front). FMVSS 224: a rear impact (underride) guard on a
        heavy trailer -- its bottom edge no higher than 560 mm, within 305 mm of the rear."""
        L = self.L
        C = L.spec["cargo"]
        hw, y1, y0 = C["half_w"], C["y1"], C["y0"]
        top = C.get("top_z") or C.get("rail_z")
        tl = self.mod("tail_lamps", "lamp", "tail_lamp", "C", hp=60, mass=3, breaks="shatter")
        tz = max(0.45, min(C["floor_z"] - 0.10, 1.0)) if C["floor_z"] > 0.8 else C["floor_z"] + 0.15
        for sx in (1, -1):
            nm = "R" if sx > 0 else "L"
            tl.box((sx * (hw - 0.14), y1 - 0.01, tz), (0.10, 0.01, 0.05), "lamp_tail")
            tl.box((sx * (hw - 0.30), y1 - 0.01, tz), (0.04, 0.01, 0.04), "lamp_amber")
            tl.box((sx * (hw - 0.02), y1 - 0.01, tz - 0.12), (0.02, 0.008, 0.03), "lamp_tail")
            self.marker("light_tail_" + nm, (sx * (hw - 0.14), y1 - 0.05, tz), math.pi)
            for yy, m in ((y0 - 0.15, "lamp_amber"), (y1 + 0.15, "lamp_tail")):
                tl.box((sx * (hw + 0.004), yy, tz), (0.004, 0.04, 0.015), m)
        if hw * 2 >= 2.032 and top:
            for k in (-1, 0, 1):
                tl.box((k * 0.22, y1 - 0.01, top - 0.06), (0.03, 0.01, 0.012), "lamp_tail")
            for sx in (1, -1):
                tl.box((sx * (hw - 0.05), y1 - 0.01, top - 0.06), (0.03, 0.01, 0.012), "lamp_tail")
                tl.box((sx * (hw - 0.05), y0 + 0.01, top - 0.06), (0.03, 0.01, 0.012), "lamp_amber")
        if C["floor_z"] > 0.9:                              # the underride guard
            gm = self.mod("underride_guard", "trim", "bumper_rear", "C", hp=900, mass=60)
            gm.box((0, y1 + 0.15, 0.50), (hw - 0.10, 0.05, 0.06), "black")
            for sx in (1, -1):
                gm.box((sx * (hw * 0.6), y1 + 0.15, (0.50 + C["floor_z"]) / 2), (0.05, 0.05, (C["floor_z"] - 0.50) / 2), "black")
        if C.get("fenders"):                                 # a small trailer's fenders over wheels outside its box
            fm = self.mod("fenders", "trim", "fenders", "C", hp=200, mass=8)
            for ax in L.axles:
                for sx in (1, -1):
                    x = sx * L.track / 2
                    pts = [Vector((x, ax + (L.wheel_r + 0.06) * math.cos(a), L.wheel_r + (L.wheel_r + 0.06) * math.sin(a)))
                           for a in [k * math.pi / 8 for k in range(9)]]
                    for p0, p1 in zip(pts, pts[1:]):
                        fm.face([p0 + Vector((-0.12, 0, 0)), p0 + Vector((0.12, 0, 0)), p1 + Vector((0.12, 0, 0)), p1 + Vector((-0.12, 0, 0))], "black")

    def trailer_points(self):
        return []

    def equipment_z(self, kind, st):
        L = self.L
        C = L.spec.get("cargo") or {}
        if kind == "bunks":                                 # a boat trailer's carpeted bunks and its winch post
            me = self.mod("bunks", "equipment", "bunks", "C", hp=200, mass=40)
            t = C["floor_z"]
            for sx in (1, -1):
                me.box((sx * 0.42, (C["y0"] + C["y1"]) / 2 - 0.2, t + 0.12), (0.05, (C["y0"] - C["y1"]) / 2 - 0.5, 0.04), "carpet")
                for y in (C["y0"] - 0.8, C["y1"] + 0.6):
                    me.box((sx * 0.42, y, t + 0.05), (0.03, 0.03, 0.06), "black")
            me.box((0, C["y0"] - 0.15, t + 0.35), (0.04, 0.04, 0.35), "black")
            me.lathe([(-0.08, 0.07), (0.08, 0.07)], "chrome", n=14, xf=Matrix.Translation((0, C["y0"] - 0.15, t + 0.62)) @ Matrix.Rotation(math.pi / 2, 4, "Z"))
        elif kind == "roof_hatches_car":
            me = self.mod("roof_hatches", "equipment", "roof_hatches", "C", hp=200, mass=60)
            for k in range(6):
                me.lathe([(0.0, 0.30), (0.08, 0.30), (0.09, 0.0001)], "black", n=12,
                         xf=Matrix.Translation((0, C["y0"] - 1.5 - k * (C["y0"] - C["y1"] - 3.0) / 5, C["top_z"])) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
            for k in range(3):
                me.box((0, C["y0"] - 3 - k * 5.0, C["floor_z"] - 0.3), (0.5, 0.4, 0.3), "paint")
        elif kind == "stake_pockets":
            me = self.mod("stakes", "equipment", "stakes", "C", hp=100, mass=40)
            y = C["y0"] - 0.4
            while y > C["y1"] + 0.3:
                for sx in (1, -1):
                    me.box((sx * (C["half_w"] - 0.03), y, C["floor_z"] + 0.04), (0.03, 0.06, 0.05), "black")
                y -= 1.2
        elif kind == "ramps":                               # a low loader's ramps, stood up at its rear
            me = self.mod("ramps", "equipment", "ramps", "C", hp=400, mass=300)
            t = C["floor_z"]
            for sx in (1, -1):
                me.box((sx * 0.75, C["y1"] + 0.15, t + 0.75), (0.30, 0.06, 0.75), "black")
        else:
            self.equipment_f(kind, st)

    # ============================================================ open light vehicles (a tub on a micro board)
    def open_parts(self, O, st):
        """An open vehicle's parts on its tub (the cargo machinery's open bed): the seats, the controls, a front cowl
        with its lamps, a canopy on posts or a roll cage (tubes shown on purpose: the style), and its extras."""
        L = self.L
        C = L.spec["cargo"]
        hw, y0, y1, fz = C["half_w"], C["y0"], C["y1"], C["floor_z"]
        rail = C["rail_z"]
        X = Matrix.Translation
        # the seats
        drv = O.get("driver", "L")
        for r, row in enumerate(O["seats"]):
            me = self.mod("seats_%d" % r, "seat", "row_%d" % r, "C", hp=200, mass=10 * len(row["xs"]))
            for x in row["xs"]:
                if row.get("saddle"):
                    me.box((x, row["y"], row["z"] - 0.06), (0.16, 0.38, 0.06), "seat")
                else:
                    self.seat(me, x, row["y"], row["z"], row.get("w", 0.48), bench=row.get("bench", False), back_deg=row.get("back", 15))
                if r == 0 and not any(m[0] == "seat_driver" for m in self.MARKERS) and ((drv == "C") or ((x < 0) == (drv == "L"))):
                    self.marker("seat_driver", (x, row["y"], row["z"]))
                else:
                    self.marker("seat_%d" % len(self.MARKERS), (x, row["y"], row["z"]))
        d = [m for m in self.MARKERS if m[0] == "seat_driver"][0][1]
        # the controls
        me = self.mod("controls", "dash", "controls", "C", hp=200, mass=6)
        ctl = O.get("controls", "wheel")
        if ctl == "wheel":
            c = Vector((d[0], d[1] + 0.40, d[2] + 0.22))
            tilt = Matrix.Rotation(math.radians(62), 4, "X")
            ring = [c + tilt @ Vector((0.15 * math.cos(TAU * k / 20), 0.15 * math.sin(TAU * k / 20), 0)) for k in range(21)]
            me.pipe(ring, 0.012, "black", n=8, caps=False)
            me.pipe([c, c + Vector((0, 0.30, -0.18))], 0.02, "black", n=8)
        elif ctl in ("bar", "tiller"):
            c = Vector((d[0], d[1] + (0.45 if ctl == "bar" else 0.55), d[2] + (0.20 if ctl == "bar" else 0.30)))
            me.pipe([c + Vector((-0.30, 0, 0)), c + Vector((-0.12, 0.02, 0.03)), c + Vector((0.12, 0.02, 0.03)), c + Vector((0.30, 0, 0))], 0.014, "black", n=6)
            me.pipe([c + Vector((0, 0.02, 0.03)), Vector((d[0], c.y + 0.20, fz + 0.10))], 0.022, "chrome", n=8)
            for sx in (1, -1):
                me.box(tuple(c + Vector((sx * 0.30, 0, 0))), (0.05, 0.02, 0.02), "rubber")
        else:                                              # a power chair's joystick on its armrest
            c = Vector((d[0] + 0.24, d[1] + 0.20, d[2] + 0.15))
            me.box(tuple(c), (0.04, 0.06, 0.03), "black")
            me.pipe([c, c + Vector((0, 0, 0.07))], 0.008, "black", n=6)
        self.marker("steering", tuple(c))
        rd = self.mod("readout", "dash", "readout", "C", hp=40, mass=0.2, breaks="shatter")
        rd.box((c.x + (0.0 if ctl != "joystick" else 0.0), c.y + 0.06, c.z + 0.05), (0.05, 0.004, 0.02), "lcd")
        # the front cowl: a sloped nose over the front wheels, its lamps in it
        cw = O.get("cowl")
        if cw:
            me = self.mod("cowl", "end_cap", "nose", "C", hp=300, mass=8)
            cy0, cy1, z1 = cw["y0"], cw["y1"], cw["z1"]
            zl = rail
            q = [(-hw, cy0, zl), (hw, cy0, zl), (hw * 0.9, cy0 - 0.05, z1 - 0.06), (-hw * 0.9, cy0 - 0.05, z1 - 0.06)]
            me.face(list(reversed(q)), st["panel"]["lower"])
            me.face([(-hw * 0.9, cy0 - 0.05, z1 - 0.06), (hw * 0.9, cy0 - 0.05, z1 - 0.06), (hw * 0.85, cy1, z1), (-hw * 0.85, cy1, z1)][::-1], st["panel"]["lower"])
            for sx in (1, -1):
                me.face([(sx * hw, cy0, zl), (sx * hw * 0.9, cy0 - 0.05, z1 - 0.06), (sx * hw * 0.85, cy1, z1), (sx * hw, cy1, zl)][:: (1 if sx > 0 else -1)],
                        st["panel"]["lower"])
            me.face([(-hw, cy1, zl), (hw, cy1, zl), (hw * 0.85, cy1, z1), (-hw * 0.85, cy1, z1)], "dash")
            lm = self.mod("head_lamps", "lamp", "head_lamp", "C", hp=40, mass=1, breaks="shatter")
            hz = (zl + z1 - 0.06) / 2
            for sx in (1, -1):
                x = sx * (hw * 0.62)
                lm.lathe([(0.0, 0.06), (0.01, 0.05), (0.012, 0.0001)], "lamp_head", n=16, xf=X((x, cy0 + 0.005, hz)))
                self.marker("light_head_%s0" % ("R" if sx > 0 else "L"), (x, cy0 + 0.05, hz))
        tl = self.mod("tail_lamps", "lamp", "tail_lamp", "C", hp=40, mass=1, breaks="shatter")
        for sx in (1, -1):
            tl.box((sx * (hw - 0.10), y1 - 0.006, rail - 0.08), (0.05, 0.006, 0.03), "lamp_tail")
            self.marker("light_tail_%s" % ("R" if sx > 0 else "L"), (sx * (hw - 0.10), y1 - 0.05, rail - 0.08), math.pi)
        # a canopy on four posts, or a roll cage (exposed tubes: shown on purpose)
        cp = O.get("canopy")
        if cp:
            me = self.mod("canopy", "roof_bay", "canopy", "C", hp=300, mass=12)
            me.box((0, (cp["y0"] + cp["y1"]) / 2, cp["z"]), (hw + 0.04, (cp["y0"] - cp["y1"]) / 2, 0.025), st["panel"]["roof"])
            pm = self.mod("canopy_posts", "equipment", "canopy_posts", "C", hp=300, mass=6)
            for yy in (cp["y0"] - 0.08, cp["y1"] + 0.08):
                for sx in (1, -1):
                    pm.pipe([Vector((sx * (hw - 0.04), yy, rail)), Vector((sx * (hw - 0.02), yy, cp["z"] - 0.02))], 0.018, "chrome", n=8)
        if O.get("cage"):
            me = self.mod("cage", "equipment", "roll_cage", "C", hp=600, mass=25)
            cy0, cy1, cz = O["cage"]
            for sx in (1, -1):
                x = sx * (hw - 0.05)
                me.pipe([Vector((x, cy0, rail)), Vector((x * 0.95, cy0 - 0.25, cz)), Vector((x * 0.95, cy1 + 0.1, cz)), Vector((x, cy1, rail))], 0.024, "black", n=8)
            for yy in (cy0 - 0.25, cy1 + 0.1):
                me.pipe([Vector((-(hw - 0.05) * 0.95, yy, cz)), Vector(((hw - 0.05) * 0.95, yy, cz))], 0.022, "black", n=8)
        for e in O.get("extras", []):
            self.open_extra(e, O, st)

    def open_extra(self, kind, O, st):
        L = self.L
        C = L.spec["cargo"]
        hw, y0, y1, fz, rail = C["half_w"], C["y0"], C["y1"], C["floor_z"], C["rail_z"]
        X = Matrix.Translation
        if kind == "rear_bed":                              # a load bed behind the seats, its own low sides
            me = self.mod("rear_bed", "equipment", "rear_bed", "C", hp=300, mass=25)
            by0, by1 = O["bed"]
            bz = rail + 0.02
            me.box((0, (by0 + by1) / 2, bz), (hw - 0.02, (by0 - by1) / 2, 0.02), "tub")
            for sx in (1, -1):
                me.box((sx * (hw - 0.03), (by0 + by1) / 2, bz + 0.13), (0.02, (by0 - by1) / 2, 0.13), st["panel"]["lower"])
            for yy in (by0, by1):
                me.box((0, yy, bz + 0.13), (hw - 0.02, 0.02, 0.13), st["panel"]["lower"])
        elif kind == "bag_rack":
            me = self.mod("bag_rack", "equipment", "bag_rack", "C", hp=100, mass=6)
            for sx in (1, -1):
                me.pipe([Vector((sx * 0.25, y1 + 0.05, rail)), Vector((sx * 0.25, y1 - 0.12, rail + 0.45))], 0.015, "chrome", n=6)
            me.box((0, y1 - 0.10, rail + 0.10), (0.28, 0.10, 0.015), "black")
        elif kind == "crates":
            me = self.mod("crates", "equipment", "crates", "C", hp=100, mass=20)
            for k in range(2):
                me.box((0, y1 + 0.35 + k * 0.42, rail + 0.15), (hw - 0.08, 0.19, 0.15), "livery1")
        elif kind == "mower_deck":
            me = self.mod("mower_deck", "equipment", "mower_deck", "C", hp=300, mass=60)
            dx = L.track / 2 - getattr(L, "tyre_w", 0.2) / 2 - 0.04          # (between the wheels, clear of them)
            dy = max(0.15, (L.axles[0] - L.axles[1]) / 2 - L.wheel_r - 0.06)
            me.box((0, (L.axles[0] + L.axles[1]) / 2, 0.16), (dx, dy, 0.07), st["panel"]["lower"])
            me.box((dx - 0.06, (L.axles[0] + L.axles[1]) / 2, 0.25), (0.06, min(0.20, dy), 0.04), "black")
        elif kind == "rops":                                # a roll-over protection bar behind the seat
            me = self.mod("rops", "equipment", "rops", "C", hp=400, mass=15)
            yy = O["seats"][0]["y"] - 0.35
            me.pipe([Vector((-(hw - 0.06), yy, rail)), Vector((-(hw - 0.06), yy, 1.65)), Vector((hw - 0.06, yy, 1.65)), Vector((hw - 0.06, yy, rail))],
                    0.026, "black", n=8)
        elif kind == "racks":                               # an ATV's front and rear racks
            me = self.mod("racks", "equipment", "racks", "C", hp=100, mass=6)
            for yy, ln in ((y0 - 0.22, 0.20), (y1 + 0.24, 0.22)):
                me.box((0, yy, rail + 0.10), (hw - 0.05, ln, 0.012), "black")
                for k in range(4):
                    me.box((0, yy - ln + 0.05 + k * (ln * 2 - 0.1) / 3, rail + 0.11), (hw - 0.07, 0.008, 0.008), "black")
        elif kind == "bumper_ring":                         # a bumper car's rubber ring all round, and its pole
            me = self.mod("bumper_ring", "trim", "bumper_ring", "C", hp=900, mass=20)
            rz = max(fz + 0.06, L.wheel_r * 2 + 0.12, L.arch_top + 0.10)   # (over the wheels and clear of their arches)
            pts = [Vector((hw * 1.08 * math.cos(a), (y0 + y1) / 2 + (y0 - y1) * 0.54 * math.sin(a), rz)) for a in [k * TAU / 24 for k in range(25)]]
            me.pipe(pts, 0.07, "rubber", n=10, caps=False)
            pm = self.mod("pole", "equipment", "pole", "C", hp=200, mass=4)
            pm.pipe([Vector((0, y1 + 0.12, rail)), Vector((0, y1 + 0.10, 2.4))], 0.02, "chrome", n=8)
            pm.lathe([(0.0, 0.05), (0.04, 0.05), (0.05, 0.0001)], "chrome", n=10, xf=X((0, y1 + 0.10, 2.4)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
        elif kind == "basket":
            me = self.mod("basket", "equipment", "basket", "C", hp=50, mass=1)
            me.box((0, y0 + 0.02, rail + 0.30), (0.18, 0.12, 0.10), "chrome")
        elif kind == "armrests":
            me = self.mod("armrests", "equipment", "armrests", "C", hp=60, mass=2)
            s0 = O["seats"][0]
            for sx in (1, -1):
                me.box((sx * 0.26, s0["y"] + 0.05, s0["z"] + 0.12), (0.03, 0.18, 0.02), "black")
                me.pipe([Vector((sx * 0.26, s0["y"] - 0.08, s0["z"] - 0.05)), Vector((sx * 0.26, s0["y"] - 0.08, s0["z"] + 0.12))], 0.01, "chrome", n=6)
        elif kind == "smokestack":
            me = self.mod("smokestack", "equipment", "smokestack", "C", hp=60, mass=3)
            me.lathe([(0.0, 0.10), (0.30, 0.10), (0.36, 0.16), (0.40, 0.16)], "black", n=14,
                     xf=X((0, O["cowl"]["y0"] - 0.25, O["cowl"]["z1"])) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
        elif kind == "kart_bumpers":
            me = self.mod("kart_bumpers", "trim", "bumper_front", "C", hp=400, mass=6)
            for yy in (y0 + 0.08, y1 - 0.08):
                me.pipe([Vector((-hw, yy, fz + 0.05)), Vector((hw, yy, fz + 0.05))], 0.03, "black", n=8)

    def equipment_f(self, kind, st):
        """The farm's and the building site's equipment (each its own token)."""
        L = self.L
        C = L.spec.get("cargo") or {}
        X = Matrix.Translation
        R = Matrix.Rotation
        pm = st["panel"]["lower"]
        if kind == "fenders_big":                           # mudguards over a tractor's big wheels
            me = self.mod("fenders", "trim", "fenders", "C", hp=200, mass=20)
            r = L.wheel_r + 0.08
            for ax in L.axles:
                for sx in (1, -1):
                    x = sx * L.track / 2
                    pts = [Vector((0, ax + r * math.cos(a), L.wheel_r + r * math.sin(a))) for a in [math.radians(25 + k * 130 / 8) for k in range(9)]]
                    for p0, p1 in zip(pts, pts[1:]):
                        me.face([p0 + Vector((x - 0.20, 0, 0)), p0 + Vector((x + 0.20, 0, 0)), p1 + Vector((x + 0.20, 0, 0)), p1 + Vector((x - 0.20, 0, 0))], pm)
        elif kind == "hitch3":                              # the three-point hitch at the back
            me = self.mod("hitch3", "equipment", "hitch", "C", hp=400, mass=60)
            y = L.tail - 0.10
            for sx in (1, -1):
                me.pipe([Vector((sx * 0.35, y + 0.05, 0.55)), Vector((sx * 0.40, y - 0.55, 0.45))], 0.03, "black", n=8)
            me.pipe([Vector((0, y + 0.05, 0.95)), Vector((0, y - 0.50, 0.85))], 0.03, "black", n=8)
            me.box((0, y + 0.02, 0.62), (0.08, 0.06, 0.06), "black")
        elif kind == "loader":                              # a front loader: arms from the cab's sides to a bucket
            me = self.mod("loader", "equipment", "loader", "C", hp=900, mass=500)
            yb = L.nose + 0.55
            ya = L.axles[0] + L.wheel_r + 0.25              # (over the front wheels, then down to the bucket ahead of them)
            zt = L.wheel_r * 2 + 0.20
            for sx in (1, -1):
                x = sx * (L.half_w + 0.08)
                me.pipe([Vector((x, L.toe - 0.4, L.belt)), Vector((x, L.axles[0], zt)), Vector((x, ya, zt)), Vector((x, yb - 0.1, 0.70))], 0.06, pm, n=8)
            me.box((0, yb, 0.42), (L.half_w + 0.25, 0.30, 0.32), "black")
            me.box((0, yb + 0.28, 0.14), (L.half_w + 0.25, 0.05, 0.04), "chrome")
        elif kind == "backhoe":                             # a backhoe: boom, stick and bucket folded up behind
            me = self.mod("backhoe", "equipment", "backhoe", "C", hp=900, mass=700)
            y0 = L.tail - 0.25
            me.box((0, y0, 1.0), (0.45, 0.20, 0.35), "black")
            me.pipe([Vector((0, y0 - 0.1, 1.1)), Vector((0, y0 - 0.9, 2.6)), Vector((0, y0 - 1.5, 2.1))], 0.10, pm, n=8)
            me.pipe([Vector((0, y0 - 1.5, 2.1)), Vector((0, y0 - 1.6, 0.9))], 0.08, pm, n=8)
            me.box((0, y0 - 1.55, 0.70), (0.30, 0.22, 0.22), "black")
            for sx in (1, -1):                              # the stabiliser legs
                me.pipe([Vector((sx * 0.5, y0, 0.8)), Vector((sx * 1.05, y0 - 0.1, 0.20))], 0.06, "black", n=8)
                me.box((sx * 1.10, y0 - 0.1, 0.06), (0.18, 0.18, 0.03), "black")
        elif kind == "header":                              # a combine's grain platform: reel and cutter bar, wide
            me = self.mod("header", "equipment", "header", "C", hp=900, mass=1500)
            y = L.nose + 0.75
            w = 2.6
            me.box((0, y, 0.55), (w, 0.55, 0.30), pm)
            me.box((0, y + 0.55, 0.30), (w, 0.08, 0.04), "chrome")
            me.lathe([(-w, 0.40), (w, 0.40)], "lamp_amber", n=10, xf=X((0, y + 0.25, 1.15)) @ R(math.pi / 2, 4, "Z"))
            for sx in (1, -1):
                me.box((sx * w, y, 0.7), (0.05, 0.6, 0.5), pm)
            me.box((0, L.nose + 0.15, 0.95), (0.55, 0.25, 0.35), "black")
        elif kind == "auger":                               # an unloading auger, folded along the side
            me = self.mod("auger", "equipment", "auger", "L", hp=400, mass=200)
            top = C.get("top_z") or C.get("rail_z")
            me.pipe([Vector((-(C["half_w"] - 0.1), C["y1"] + 0.4, top - 0.4)), Vector((-(C["half_w"] + 0.15), C["y0"] - 0.2, top + 0.2))], 0.15,
                    st["panel"].get("cargo", pm), n=10)
        elif kind == "spray_booms":                         # a sprayer's booms, folded up along its sides
            me = self.mod("booms", "equipment", "spray_booms", "C", hp=400, mass=300)
            for sx in (1, -1):
                x = sx * (C["half_w"] + 0.15)
                me.box((x, (C["y0"] + C["y1"]) / 2, C["floor_z"] + 1.1), (0.06, (C["y0"] - C["y1"]) / 2 - 0.2, 0.25), "black")
                for k in range(8):
                    me.box((x, C["y1"] + 0.4 + k * 0.6, C["floor_z"] + 0.8), (0.03, 0.02, 0.06), "chrome")
        elif kind == "hay_racks":
            me = self.mod("hay_racks", "equipment", "hay_racks", "C", hp=200, mass=80)
            t = C["floor_z"]
            for yy in (C["y0"] - 0.05, C["y1"] + 0.05):
                for k in range(5):
                    x = -C["half_w"] + 0.1 + k * (C["half_w"] * 2 - 0.2) / 4
                    me.box((x, yy, t + 0.9), (0.03, 0.03, 0.9), "wood")
                me.box((0, yy, t + 1.78), (C["half_w"], 0.03, 0.03), "wood")
            for k in range(6):                              # a few bales
                me.box(((k % 3 - 1) * 0.75, C["y0"] - 0.8 - (k // 3) * 1.4, t + 0.25), (0.35, 0.55, 0.25), "lamp_amber")
        elif kind == "beaters":                             # a spreader's beaters across its open rear
            me = self.mod("beaters", "equipment", "beaters", "C", hp=400, mass=150)
            for k, z in enumerate((C["floor_z"] + 0.35, C["floor_z"] + 0.85)):
                me.lathe([(-C["half_w"] + 0.08, 0.22), (C["half_w"] - 0.08, 0.22)], "black", n=12, xf=X((0, C["y1"] + 0.25, z)) @ R(math.pi / 2, 4, "Z"))
        elif kind == "pickup":                              # a baler's pickup reel and its bale chute
            me = self.mod("pickup", "equipment", "pickup", "C", hp=300, mass=120)
            me.lathe([(-C["half_w"] - 0.3, 0.25), (C["half_w"] + 0.3, 0.25)], "black", n=12, xf=X((0, C["y0"] + 0.35, 0.40)) @ R(math.pi / 2, 4, "Z"))
            me.box((0, C["y1"] - 0.5, C["floor_z"] + 0.2), (0.5, 0.5, 0.04), "black")
        elif kind == "planter":                             # a planter's toolbar, folded, with its row units
            me = self.mod("planter", "equipment", "planter", "C", hp=500, mass=800)
            t = C["floor_z"]
            me.box((0, C["y1"] + 0.4, t + 0.25), (1.5, 0.12, 0.12), pm)
            for k in range(8):
                x = -1.4 + k * 0.4
                me.box((x, C["y1"] + 0.15, t + 0.05), (0.08, 0.25, 0.30), "black")
                me.box((x, C["y1"] + 0.35, t + 0.55), (0.14, 0.18, 0.18), "lamp_amber")
            for sx in (1, -1):
                me.box((sx * 1.2, (C["y0"] + C["y1"]) / 2, t + 0.9), (0.08, (C["y0"] - C["y1"]) / 2 - 0.5, 0.10), pm)
        elif kind == "discs":                               # a disc harrow's gangs
            me = self.mod("discs", "equipment", "discs", "C", hp=500, mass=600)
            t = C["floor_z"]
            for g, yy in enumerate((C["y0"] - 0.4, C["y1"] + 0.4)):
                for k in range(9):
                    x = -1.6 + k * 0.4
                    me.lathe([(-0.02, 0.0001), (0.0, 0.26), (0.02, 0.0001)], "chrome", n=14,
                             xf=X((x, yy, 0.26)) @ R(math.pi / 2 + (0.2 if g else -0.2), 4, "Z"))
                me.box((0, yy, 0.55), (1.8, 0.05, 0.05), pm)
        elif kind == "mast":                                # a forklift's mast and forks, a counterweight behind
            me = self.mod("mast", "equipment", "mast", "C", hp=700, mass=400)
            y = C["y0"] + 0.12
            for sx in (1, -1):
                me.box((sx * 0.30, y, 1.2), (0.05, 0.05, 1.1), "black")
            for k in (0.2, 1.1, 2.25):
                me.box((0, y, k), (0.34, 0.04, 0.03), "black")
            for sx in (1, -1):
                me.box((sx * 0.22, y + 0.55, 0.12), (0.05, 0.55, 0.025), "chrome")
                me.box((sx * 0.22, y + 0.04, 0.45), (0.05, 0.02, 0.35), "chrome")
            cw = self.mod("counterweight", "equipment", "counterweight", "C", hp=900, mass=900)
            cw.box((0, C["y1"] + 0.20, C["rail_z"] + 0.15), (C["half_w"], 0.22, 0.38), pm)
        elif kind == "loader_arms":                         # a skid steer's arms either side of its cab, its bucket
            me = self.mod("loader_arms", "equipment", "loader_arms", "C", hp=800, mass=300)
            for sx in (1, -1):
                x = sx * (C["half_w"] + 0.06)
                me.pipe([Vector((x, C["y1"] + 0.2, 1.7)), Vector((x, C["y0"] - 0.2, 1.4)), Vector((x, C["y0"] + 0.35, 0.55))], 0.06, pm, n=8)
            me.box((0, C["y0"] + 0.55, 0.30), (C["half_w"] + 0.15, 0.25, 0.25), "black")
        elif kind == "tracks":                              # crawler tracks round the board's wheels
            me = self.mod("tracks", "wheel_well", "tracks", "C", hp=1200, mass=3000)       # (round the wheels, by design)
            ya, yb = L.axles[0] + L.wheel_r + 0.3, L.axles[-1] - L.wheel_r - 0.3
            for sx in (1, -1):
                x = sx * L.track / 2
                me.box((x, (ya + yb) / 2, L.wheel_r), (0.30, (ya - yb) / 2, L.wheel_r + 0.06), "black")
                k = yb
                while k < ya:
                    me.box((x + sx * 0.31, k, L.wheel_r), (0.005, 0.03, L.wheel_r + 0.05), "rubber")
                    k += 0.25
        elif kind == "excavator_house":                     # the slewing house: cab, engine deck, boom, stick, bucket
            me = self.mod("excavator_house", "equipment", "house", "C", hp=1500, mass=6000)
            fz = C["floor_z"]
            me.lathe([(0.0, 1.0), (0.15, 1.0), (0.16, 0.0001)], "black", n=24, xf=X((0, 0.3, fz)) @ R(-math.pi / 2, 4, "X"))
            me.box((0, -0.6, fz + 0.75), (1.20, 1.40, 0.60), pm)
            me.box((-0.70, 1.0, fz + 1.05), (0.48, 0.50, 0.90), "glass_dark")
            me.box((-0.70, 1.0, fz + 1.96), (0.50, 0.52, 0.03), pm)
            me.pipe([Vector((0.35, 1.2, fz + 0.9)), Vector((0.35, 3.6, fz + 3.0)), Vector((0.35, 5.2, fz + 2.2))], 0.16, pm, n=10)
            me.pipe([Vector((0.35, 5.2, fz + 2.2)), Vector((0.35, 5.6, 0.6))], 0.12, pm, n=10)
            me.box((0.35, 5.6, 0.40), (0.45, 0.30, 0.28), "black")
        elif kind == "travel_gantry":                       # (unused: the travel lift is its own build)
            pass


    def housing_x(self, a, b):
        """A wheel housing's inner wall: clear of its tyre's inner face by 6 cm -- of the tyre's whole sweep where its axle
        steers (35 degrees)."""
        L = self.L
        tw = getattr(L, "tyre_w", 0.2)
        x = L.track / 2 - tw / 2 - 0.06
        for ax in L.axles:
            if b - 1e-6 <= ax <= a + 1e-6 and ax == max(L.axles) and len(L.axles) > 1:
                c, sn = math.cos(math.radians(35)), math.sin(math.radians(35))
                x = min(x, L.track / 2 - (tw / 2 * c + L.wheel_r * sn) - 0.04)
        return max(0.05, x)
