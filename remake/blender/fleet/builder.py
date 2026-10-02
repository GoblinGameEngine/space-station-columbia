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
        self.L = L = loft
        self.M = M
        self.Y = L.stations
        self.YI = L.int_stations
        self.EXT = [L.ext_loop(y) for y in self.Y]
        self.INT = {y: L.int_loop(y) for y in self.YI}
        self.NS_E = len(self.EXT[0]) - 1
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
        for ax in L.axles:
            a, b = ax + L.arch_half, ax - L.arch_half
            if b < y0 and a > y1:
                assert y1 - 1e-6 <= b and a <= y0 + 1e-6, ("an arch runs out of its panel", sd, ax, y0, y1)
                out.append((a, b) + self.side_rng(E["skirt"], E["arch"], sd))
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
        roof_end = R["c_top"] if R["kind"] == "trunk" else rear_start
        self.panels = {"R": [], "L": []}
        for sd in SIDES:
            ds = self.doors_on(sd)
            for d in ds:
                assert d["y0"] <= L.toe + 1e-6, ("a door starts ahead of the cowl", d)
            first = ds[0]["y0"] if ds else rear_start
            # the fender: below the belt from the nose to the first door, the gutter band over the hood zone
            if front_end > first + 1e-6:
                mid = "fender_" + sd
                me = self.mod(mid, "side_bay", "fender", sd, hp=400, mass=9)
                self.cells(me, mid, "ext", front_end, first, *self.side_rng(E["skirt"], E["belt"], sd), lower,
                           holes=self.arch_holes(sd, front_end, first))
                if front_end > L.toe + 1e-6:
                    self.cells(me, mid, "ext", front_end, L.toe, *self.side_rng(E["belt"], E["cant"], sd), lower)
                self.panels[sd].append((mid, front_end, first))
            if L.toe > first + 1e-6:
                mid = "sail_" + sd
                me = self.mod(mid, "trim", "sail", sd, hp=300, mass=2)
                self.cells(me, mid, "ext", L.toe, first, *self.side_rng(E["belt"], E["head"], sd), sailm)
            mid = "a_pillar_" + sd
            me = self.mod(mid, "trim", "a_pillar", sd, hp=400, mass=3)
            self.cells(me, mid, "ext", L.toe, L.header, *self.side_rng(E["head"], E["cant"], sd), upper)
            # the doors' rockers, the posts between doors, the quarter behind the last
            for i, d in enumerate(ds):
                mid = "rocker_%s_%s" % (d["id"], sd)
                me = self.mod(mid, "side_bay", "rocker_" + d["id"], sd, hp=500, mass=5)
                self.cells(me, mid, "ext", d["y0"], d["y1"], *self.side_rng(E["skirt"], E["sill"], sd), lower)
                nxt = ds[i + 1]["y0"] if i + 1 < len(ds) else None
                if nxt is not None and d["y1"] > nxt + 1e-6:
                    self.side_panel(sd, "post_%d" % i, "post_%d" % i, d["y1"], nxt, lower, upper)
            last = ds[-1]["y1"] if ds else first
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
        self.cells(me, "floor", "int", L.toe, L.cab_end, self.ins(1, "L"), self.NS_I + self.ins(1, "R"), lambda s, y, z: "carpet")
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
        # the side windows' panes (fixed, flush)
        for w in L.windows:
            for sd in SIDES:
                if sd in w.get("sides", "RL"):
                    mid = "glass_%s_%s" % (w["id"], sd)
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
            if not (L.nose > ya and yb > L.tail):
                continue
            for sd in SIDES:
                sx = 1 if sd == "R" else -1
                mid = "well_%d_%s" % (n, sd)
                me = self.mod(mid, "wheel_well", "well_%d" % n, sd, hp=600, mass=5)
                rs = self.rows_between(self.Y, ya, yb)
                ks = [self.es(k, sd) for k in (E["skirt"], E["sill"], E["arch"])]
                for y in (ya, yb):
                    outer = [self.ext_pt(self.iy(y), k) for k in ks]
                    me.face(outer + [(sx * L.well_x, y, L.arch_top), (sx * L.well_x, y, L.skirt)], "rubber")
                top_o = [self.ext_pt(self.iy(y), ks[2]) for y in rs]
                top_i = [(sx * L.well_x, y, L.arch_top) for y in rs]
                self.strip_open(me, top_o, top_i, "rubber", flip=(sd == "L"))
                wall_t = [(sx * L.well_x, y, L.arch_top) for y in rs]
                wall_b = [(sx * L.well_x, y, L.skirt) for y in rs]
                self.strip_open(me, wall_t, wall_b, "rubber", flip=(sd == "L"))
                lip = [Vector(self.ext_pt(self.iy(ya), ks[0]))] + [Vector(self.ext_pt(self.iy(ya), k)) for k in ks[1:]] + \
                      [Vector(self.ext_pt(self.iy(y), ks[2])) for y in rs[1:-1]] + [Vector(self.ext_pt(self.iy(yb), k)) for k in reversed(ks)]
                me.pipe([p + Vector((sx * 0.006, 0, 0)) for p in lip], 0.012, "rubber", n=6)
        me = self.mod("underpan", "underpan", "underpan", "C", hp=800, mass=16)
        arches = [(ax + L.arch_half, ax - L.arch_half) for ax in L.axles]
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
        ty = L.tail - 0.004
        tz = L.spec.get("tail_lamp_z", 1.0)
        assert 0.38 <= tz <= 1.83
        hole = R.get("hatch") or R.get("barn") or R.get("back_window")
        tl = self.mod("tail_lamps", "lamp", "tail_lamp", "C", hp=60, mass=3, breaks="shatter")
        edge = self.face_x(L.tail, tz) - 0.02
        x0 = max(edge - 0.16, (hole["half_w"] + 0.02) if hole and hole["z"][0] < tz + 0.25 else 0.0)
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
            self.marker("light_tail_" + nm, (xm, L.tail - 0.05, tz), math.pi)
            self.marker("light_reverse_" + nm, (xm, L.tail - 0.05, tz - 0.15), math.pi)
            self.marker("light_ind_B" + nm, (xm, L.tail - 0.05, tz + 0.15), math.pi)
        # the centre high-mounted stop lamp
        if R["kind"] == "trunk":
            cy, cz = R["c_foot"] - 0.02, L.deck_z(R["c_foot"]) + 0.03
        else:
            cy, cz = L.tail - 0.006, (hole["z"][1] + 0.06) if hole else L.head + 0.02
        tl.box((0, cy, cz), (0.18, 0.006, 0.012), "lamp_brake")
        self.marker("light_brake_high", (0, cy - 0.04, cz), math.pi)
        # side markers: amber near the front, red near the back, on their panels (their own token)
        sm = self.mod("side_markers", "lamp", "side_marker", "C", hp=40, mass=0.4, breaks="shatter")
        for sd in SIDES:
            sx = 1 if sd == "R" else -1
            for yy, m in ((L.nose - 0.20, "lamp_amber"), (L.tail + 0.20, "lamp_tail")):
                z = min(L.arch_top + 0.05, L.belt - 0.08)
                sm.box((sx * (self.surf_x(yy, z) + 0.004), yy, z), (0.004, 0.04, 0.015), m)
        # identification and clearance lamps on wide vehicles
        if L.half_w * 2 >= 2.032:
            il = self.mod("id_lamps", "lamp", "id_lamp", "C", hp=40, mass=0.6, breaks="shatter")
            for yy, m, sg in ((L.header - 0.02, "lamp_amber", 1), (L.tail + 0.02, "lamp_tail", -1)):
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
        m = {"chrome": "chrome", "black": "black", "body": st["panel"]["lower"]}[st.get("bumper", "chrome")]
        for yy, sg, slot in ((L.nose, 1, "bumper_front"), (L.tail, -1, "bumper_rear")):
            bm = self.mod(slot, "trim", slot, "C", hp=900, mass=10)
            bm.box((0, yy + sg * 0.045, bz), (w, 0.04, 0.07), m)
            bm.box((0, yy + sg * 0.087, bz), (w - 0.02, 0.004, 0.018), "rubber")
            for sx in (1, -1):
                bm.box((sx * w, yy + sg * 0.005, bz), (0.05, 0.045, 0.065), m)

    def mirrors(self, st):
        """Outside mirrors on both sides (FMVSS 111: the driver's is required; a passenger-side one on these)."""
        L = self.L
        my = min(L.toe - 0.06, self.doors_on("L")[0]["y0"] + 0.06 if self.doors_on("L") else L.toe - 0.06)
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
        rows = S["seats"]
        n = 0
        drv = S.get("driver", "L")
        for r, row in enumerate(rows):
            mid = "seats_%d" % r
            me = self.mod(mid, "seat", "row_%d" % r, "C", hp=300, mass=18 * len(row["xs"]))
            for k, x in enumerate(row["xs"]):
                self.seat(me, x, row["y"], row["z"], row.get("w", 0.50), bench=row.get("bench", False))
                if r == 0 and ((x < 0) == (drv == "L")) and not any(m[0] == "seat_driver" for m in self.MARKERS):
                    self.marker("seat_driver", (x, row["y"], row["z"]))
                else:
                    n += 1
                    self.marker("seat_%d" % n, (x, row["y"], row["z"]))
        dx = [m for m in self.MARKERS if m[0] == "seat_driver"][0][1]
        me = self.mod("dash", "dash", "dash", "C", hp=400, mass=14)
        top = L.top_z(L.toe) - 0.04 if hasattr(L, "top_z") else self.top_z(L.toe) - 0.04
        yd = L.toe - 0.15
        hw = L.half_w - L.int_off - 0.08
        me.box((0, yd, top), (hw, 0.14, 0.05), "dash")
        me.box((0, yd - 0.12, top - 0.10), (hw - 0.02, 0.05, 0.09), "dash")
        me.box((dx[0], yd - 0.16, top + 0.02), (0.17, 0.05, 0.05), "dash")
        for gx in (dx[0] - 0.07, dx[0] + 0.07):
            me.lathe([(0.0, 0.045), (0.004, 0.045), (0.005, 0.0001)], "gauge", n=16, xf=Matrix.Translation((gx, yd - 0.215, top + 0.02)))
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
