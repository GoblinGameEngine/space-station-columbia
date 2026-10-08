"""
gbhouse.py -- spec-driven house/small-building builder for the remake.

A house script describes ITS real example as data (blocks, rooms, doors, windows, stairs,
porches, chimneys, fireplaces) and this module turns that into geometry with gblib:
exterior walls with real openings (gable ends follow the roof), partitions derived from the
room layout, floors with stair holes, flat/sloped ceilings, gable/hip/shed roofs, porches,
fireplaces, and a furnished interior per room type.  Shared code, per-building data.

Coordinates: metres, origin = centre of the main block at grade, +X east, +Y north.
Rects are (x0, y0, x1, y1) measured to OUTSIDE faces of exterior walls and to the
CENTRE LINES of partitions (the way plans are dimensioned).
"""
import math

from mathutils import Vector

import gbfurn as fu
import gblib as g

EPS = 0.03


def _union(iv):
    iv = sorted(iv)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1] + 1e-3:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _subtract(interval, cuts):
    a, b = interval
    pieces = [(a, b)]
    for c0, c1 in cuts:
        nxt = []
        for p0, p1 in pieces:
            if c1 <= p0 + 1e-4 or c0 >= p1 - 1e-4:
                nxt.append((p0, p1))
                continue
            if c0 > p0 + 1e-4:
                nxt.append((p0, c0))
            if c1 < p1 - 1e-4:
                nxt.append((c1, p1))
        pieces = nxt
    return [p for p in pieces if p[1] - p[0] > 0.05]


def stair_zones(spec):
    """Plan rects (footprint, foot, head) of every stair in a spec, before the House is built --
    for generators placing doors added after the floor plan."""
    h = House.__new__(House)
    h.s = spec
    return [(G["footprint"], G["foot"], G["head"], G["floor"]) for G in (h._stair_geom(st) for st in spec.get("stairs", []))]


class House:
    def __init__(self, b, spec):
        self.b, self.s = b, spec
        self.m = dict(ext="siding", int="plaster", roof="roof", roof_under="trim", found="found", floor="floor",
                      ceiling="plaster", trim="trim", door="door", fascia="trim", porch="porch", post="trim",
                      furn="furniture", brass="brass")
        self.m.update(spec.get("mats", {}))
        self.te = spec.get("t_ext", 0.15)
        self.ti = spec.get("t_int", 0.1)
        self.frames = []                 # (kind, frame, a, b, floor_z...) for placing doors/windows
        self.swing_zones = []            # (x0, y0, x1, y1, floor): plan area each door leaf sweeps
        self.shell = b.part("shell-col")
        self.parts = b.part("partitions-col")

    # ---------------------------------------------------------------- geometry queries
    def block_of(self, x, y):
        for bl in self.s["blocks"]:
            x0, y0, x1, y1 = bl["rect"]
            if x0 - EPS <= x <= x1 + EPS and y0 - EPS <= y <= y1 + EPS:
                return bl
        return None

    def room(self, name):
        return next(r for r in self.s["rooms"] if r["name"] == name)

    def room_at(self, x, y, floor):
        for r in self.s["rooms"]:
            x0, y0, x1, y1 = r["rect"]
            if r.get("floor", 0) == floor and x0 < x < x1 and y0 < y < y1:
                return r
        return None

    def roof_under(self, bl, x, y):
        """Underside height of a block's roof at (x, y) (inf where no roof limits it)."""
        rf = bl.get("roof")
        if not rf:
            return 1e9
        x0, y0, x1, y1 = bl["rect"]
        tn = math.tan(math.radians(rf.get("pitch", 0)))
        th = rf.get("thick", 0.15) / math.cos(math.radians(rf.get("pitch", 0)))
        wt = bl["wall_top"]
        if rf["type"] == "flat":
            return wt - rf.get("thick", 0.25)
        if rf["type"] in ("gable", "gambrel"):
            if rf["ridge"] == "x":
                d = min(y - y0, y1 - y)
            else:
                d = min(x - x0, x1 - x)
            if rf["type"] == "gambrel":
                return wt + gambrel_rise(d, (y1 - y0) if rf["ridge"] == "x" else (x1 - x0), rf) - th
            return wt + d * tn - th
        if rf["type"] == "hip":
            d = min(x - x0, x1 - x, y - y0, y1 - y)
            return wt + d * tn - th
        if rf["type"] == "shed":
            hi = rf["high"]            # side letter of the high wall
            span = (y1 - y0) if hi in "NS" else (x1 - x0)
            d = {"N": y1 - y, "S": y - y0, "E": x1 - x, "W": x - x0}[hi]
            return wt + (span - d) * tn - th
        return 1e9

    # ---------------------------------------------------------------- exterior walls
    def _block_edges(self, bl):
        x0, y0, x1, y1 = bl["rect"]
        return {"S": ((x0, y0), (x1, y0)), "E": ((x1, y0), (x1, y1)), "N": ((x1, y1), (x0, y1)), "W": ((x0, y1), (x0, y0))}

    def _abs_shared(self, bl, side):
        """Absolute intervals (x for N/S edges, y for E/W edges) where another block abuts this edge."""
        (a, c) = self._block_edges(bl)[side]
        horiz = abs(a[1] - c[1]) < 1e-6
        lo_e, hi_e = (min(a[0], c[0]), max(a[0], c[0])) if horiz else (min(a[1], c[1]), max(a[1], c[1]))
        line = a[1] if horiz else a[0]
        cuts = []
        for ob in self.s["blocks"]:
            if ob is bl:
                continue
            ox0, oy0, ox1, oy1 = ob["rect"]
            if horiz and (abs(oy0 - line) < EPS or abs(oy1 - line) < EPS):
                lo, hi = max(lo_e, ox0), min(hi_e, ox1)
            elif not horiz and (abs(ox0 - line) < EPS or abs(ox1 - line) < EPS):
                lo, hi = max(lo_e, oy0), min(hi_e, oy1)
            else:
                continue
            if hi > lo:
                cuts.append((lo, hi))
        return _union(cuts)

    def _shared_with(self, bl, side):
        """[((s0, s1), other block)]: the stretches of this side another block abuts, as parameters from the edge's start"""
        (a, c) = self._block_edges(bl)[side]
        horiz = abs(a[1] - c[1]) < 1e-6
        lo_e, hi_e = (min(a[0], c[0]), max(a[0], c[0])) if horiz else (min(a[1], c[1]), max(a[1], c[1]))
        line = a[1] if horiz else a[0]
        a0 = a[0] if horiz else a[1]
        sgn = 1 if ((c[0] - a[0]) if horiz else (c[1] - a[1])) > 0 else -1
        out = []
        for ob in self.s["blocks"]:
            if ob is bl:
                continue
            ox0, oy0, ox1, oy1 = ob["rect"]
            if horiz and (abs(oy0 - line) < EPS or abs(oy1 - line) < EPS):
                lo, hi = max(lo_e, ox0), min(hi_e, ox1)
            elif not horiz and (abs(ox0 - line) < EPS or abs(ox1 - line) < EPS):
                lo, hi = max(lo_e, oy0), min(hi_e, oy1)
            else:
                continue
            if hi - lo > 0.05:
                out.append((tuple(sorted(((lo - a0) * sgn, (hi - a0) * sgn))), ob))
        return out

    def _shared(self, bl, side):
        """Shared intervals as parameters along the edge measured from its start point a."""
        (a, c) = self._block_edges(bl)[side]
        horiz = abs(a[1] - c[1]) < 1e-6
        a0 = a[0] if horiz else a[1]
        sgn = 1 if ((c[0] - a[0]) if horiz else (c[1] - a[1])) > 0 else -1
        return _union([tuple(sorted(((lo - a0) * sgn, (hi - a0) * sgn))) for (lo, hi) in self._abs_shared(bl, side)])

    def _exterior_on_line(self, axis, c):
        """Absolute intervals of real exterior wall lying on the line x=c (axis 'x') or y=c."""
        out = []
        for bl in self.s["blocks"]:
            x0, y0, x1, y1 = bl["rect"]
            for side, (a, cc) in self._block_edges(bl).items():
                horiz = abs(a[1] - cc[1]) < 1e-6
                if axis == "x" and not horiz and abs(a[0] - c) < EPS:
                    out += _subtract((y0, y1), self._abs_shared(bl, side))
                if axis == "y" and horiz and abs(a[1] - c) < EPS:
                    out += _subtract((x0, x1), self._abs_shared(bl, side))
        return _union(out)

    def _openings_on(self, a, c, t, floors_z, exterior=True):
        """Doors/windows whose 'at' point sits on segment a->c. Returns (openings, owners)."""
        o, u, w_in, L = g.wall_frame(a, c)
        ops, own = [], []
        for kind in ("windows", "doors"):
            if kind == "windows" and not exterior:
                continue
            for it in self.s.get(kind, []):
                if kind == "doors" and exterior != it.get("ext", False):
                    continue
                p = Vector((it["at"][0], it["at"][1], 0))
                rel = p - o
                along = rel.dot(u)
                off = rel.dot(w_in)
                if abs(off) > max(t, 0.12) + 0.05 or along < -0.05 or along > L + 0.05:
                    continue
                if exterior and not (-0.05 <= off <= t + 0.05):
                    continue
                if it.get("floor", 0) >= len(floors_z):
                    continue            # an upper-floor opening on a line a lower block shares
                fz = floors_z[it.get("floor", 0)]
                w = it["w"]
                if kind == "windows":
                    sill, head = fz + it["sill"], fz + it["sill"] + it["h"]
                else:
                    sill, head = fz, fz + it.get("h", 2.03)
                ops.append(dict(off=along - w / 2, w=w, sill=sill, head=head))
                own.append((kind, it))
        return ops, own

    def build_exterior(self):
        for bl in self.s["blocks"]:
            fz = [f[0] for f in bl["floors"]]
            rf = bl.get("roof", {})
            z0 = bl.get("found_top", fz[0] - 0.05)
            x0, y0, x1, y1 = bl["rect"]
            # foundation band
            self.shell.box((x0 - 0.02, y0 - 0.02, -g.FOUND_DEPTH), (x1 + 0.02, y1 + 0.02, z0), self.m["found"], sides="xXyY")
            for side, (a, c) in self._block_edges(bl).items():
                L = math.dist(a, c)
                keep = _subtract((0.0, L), self._shared(bl, side))
                gable_end = rf.get("type") in ("gable", "gambrel") and ((rf["ridge"] == "x" and side in "EW") or
                                                                         (rf["ridge"] == "y" and side in "NS"))
                shed_rise = rf.get("type") == "shed" and side not in (rf["high"], {"N": "S", "S": "N", "E": "W", "W": "E"}[rf["high"]])
                for (s0, s1) in keep:
                    u = Vector((c[0] - a[0], c[1] - a[1], 0)) / L
                    pa = (a[0] + u.x * s0, a[1] + u.y * s0)
                    pc = (a[0] + u.x * s1, a[1] + u.y * s1)
                    ops, own = self._openings_on(pa, pc, self.te, fz, exterior=True)
                    mats = (bl.get("ext", self.m["ext"]), self.m["int"])
                    if gable_end or shed_rise:
                        top = (lambda uu, pa=pa, u=u: self.roof_under(bl, pa[0] + u.x * uu, pa[1] + u.y * uu)
                               + rf.get("thick", 0.15) / math.cos(math.radians(rf["pitch"])) - 0.02)
                        fr = g.wall_profile(self.shell, pa, pc, z0, top, self.te, ops, *mats)
                    else:
                        fr = g.wall(self.shell, pa, pc, z0, bl["wall_top"], self.te, ops, *mats)
                    self.frames.append(dict(frame=fr, a=pa, c=pc, t=self.te, ops=ops, own=own, ext=True, block=bl))
                # where a LOWER block abuts this side, the wall still has to close this block above it (the audit found a
                # school's two-storey gym wing open for its whole width over the classroom block's flat roof)
                for (s0, s1), ob in self._shared_with(bl, side):
                    o_top = ob["wall_top"]
                    if o_top >= bl["wall_top"] - 0.05 and not (gable_end or shed_rise):
                        continue
                    u = Vector((c[0] - a[0], c[1] - a[1], 0)) / L
                    pa = (a[0] + u.x * s0, a[1] + u.y * s0)
                    pc = (a[0] + u.x * s1, a[1] + u.y * s1)
                    mats = (bl.get("ext", self.m["ext"]), self.m["int"])
                    if gable_end or shed_rise:
                        top = (lambda uu, pa=pa, u=u: self.roof_under(bl, pa[0] + u.x * uu, pa[1] + u.y * uu)
                               + rf.get("thick", 0.15) / math.cos(math.radians(rf["pitch"])) - 0.02)
                        g.wall_profile(self.shell, pa, pc, o_top, top, self.te, [], *mats)
                    else:
                        g.wall(self.shell, pa, pc, o_top, bl["wall_top"], self.te, [], *mats)
            # corner boards (frame houses)
            if bl.get("corner_boards", True) and bl.get("ext", self.m["ext"]) in ("siding", "siding_w"):
                for (cx, cy) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                    sx = 1 if cx > (x0 + x1) / 2 else -1
                    sy = 1 if cy > (y0 + y1) / 2 else -1
                    self.shell.box((min(cx, cx + sx * 0.025) - (0.1 if sx < 0 else 0), min(cy, cy + sy * 0.025) - (0.1 if sy < 0 else 0), z0),
                                   (max(cx, cx + sx * 0.025) + (0.1 if sx > 0 else 0), max(cy, cy + sy * 0.025) + (0.1 if sy > 0 else 0),
                                    bl["wall_top"] - 0.22), self.m["trim"])        # stop below the eave soffit

    # ---------------------------------------------------------------- partitions (from rooms)
    def build_partitions(self):
        blocks = self.s["blocks"]
        nfloors = max(len(bl["floors"]) for bl in blocks)
        # junction lines between blocks become interior walls on every shared floor
        for fl in range(nfloors):
            lines = {}
            open_edges = {}
            for r in self.s["rooms"]:
                if r.get("floor", 0) == fl and r.get("open_plan_to"):
                    # an alcove open to its room (bay, inglenook, landing): no wall along the edge it
                    # shares with that room -- its other edges keep their walls
                    x0, y0, x1, y1 = r["rect"]
                    tx0, ty0, tx1, ty1 = self.room(r["open_plan_to"])["rect"]
                    for (ax, c, a0, a1, tc_list, t0, t1) in (("x", x0, y0, y1, (tx0, tx1), ty0, ty1), ("x", x1, y0, y1, (tx0, tx1), ty0, ty1),
                                                             ("y", y0, x0, x1, (ty0, ty1), tx0, tx1), ("y", y1, x0, x1, (ty0, ty1), tx0, tx1)):
                        if any(abs(c - tc) < EPS for tc in tc_list) and min(a1, t1) - max(a0, t0) > 0.05:
                            open_edges.setdefault((ax, round(c, 2)), []).append((max(a0, t0), min(a1, t1)))
            for r in self.s["rooms"]:
                if r.get("floor", 0) != fl or r.get("open_plan_to"):
                    continue
                x0, y0, x1, y1 = r["rect"]
                for (key, iv) in ((("x", round(x0, 2)), (y0, y1)), (("x", round(x1, 2)), (y0, y1)),
                                  (("y", round(y0, 2)), (x0, x1)), (("y", round(y1, 2)), (x0, x1))):
                    lines.setdefault(key, []).append(iv)
            for (axis, c), ivs in lines.items():
                ext = self._exterior_on_line(axis, c) + open_edges.get((axis, c), [])
                for (s0, s1) in _union(ivs):
                    for (p0, p1) in _subtract((s0, s1), _union(ext)):
                        self._partition(axis, c, p0, p1, fl)

    def _stair_geom(self, st):
        """Normalise a stair spec.  type 'straight' (default): one flight from start along dir.
        type 'dogleg': flight A from start along dir to a half landing, flight B back beside it on
        the `turn` side ('left' = +side, the default) -- a compact stair for shallow plans.
        Returns flights (start, d, side, width, n, run, z0, z1), the landing box, the upper-floor hole,
        the foot / head landing zones and the footprint (all plan rects x0, y0, x1, y1)."""
        d = Vector((st["dir"][0], st["dir"][1], 0)).normalized()
        side = Vector((-d.y, d.x, 0))
        p0 = Vector((st["start"][0], st["start"][1], 0))
        fl, tf = st.get("floor", 0), st.get("to_floor", st.get("floor", 0) + 1)
        bl = self.block_of(p0.x + d.x * 0.5 + side.x * 0.3, p0.y + d.y * 0.5 + side.y * 0.3) or self.block_of(p0.x, p0.y)
        z0 = bl["floors"][fl][0] if fl >= 0 else st["z0"]
        z1 = bl["floors"][tf][0] if "z1" not in st else st["z1"]
        w, n, run = st["width"], st["n"], st["run"]

        def rect(pts):
            return (min(q.x for q in pts), min(q.y for q in pts), max(q.x for q in pts), max(q.y for q in pts))

        def zone(a0, a1, s0, s1):
            return rect([p0 + d * a + side * c for a in (a0, a1) for c in (s0, s1)])
        if st.get("type", "straight") == "dogleg":
            sg = 1.0 if st.get("turn", "left") == "left" else -1.0
            gap, land = st.get("gap", 0.08), st.get("landing", 1.0)
            n1 = (n + 1) // 2           # the lower flight takes an odd riser, so flight B lands at/behind the start
            n2 = n - n1
            L1, L2 = n1 * run, n2 * run
            zl = z0 + (z1 - z0) * n1 / n
            s_lo, s_hi = (0.0, 2 * w + gap) if sg > 0 else (-(w + gap), w)
            a_start = p0
            # B climbs back from the landing's near edge; g.stairs' start is the flight's left edge
            b_start = p0 + d * L1 + side * ((2 * w + gap) if sg > 0 else -gap)
            flights = [dict(start=a_start, d=d, side=side, width=w, n=n1, run=run, z0=z0, z1=zl),
                       dict(start=b_start, d=-d, side=-side, width=w, n=n2, run=run, z0=zl, z1=z1)]
            landing = (zone(L1, L1 + land, s_lo, s_hi), zl)
            # flight B tops out L1 - L2 (0 or one run) past the start: the floor reaches out to meet it
            hole = zone(L1 - L2, L1 + land, s_lo, s_hi)
            b_lo, b_hi = (w + gap, 2 * w + gap) if sg > 0 else (-(w + gap), -gap)
            foot = zone(-0.9, 0.0, 0.0, w)
            head = zone(L1 - L2 - 0.9, L1 - L2, b_lo, b_hi)
            footprint = zone(0.0, L1 + land, s_lo, s_hi)
            arrival = ("B", b_lo, b_hi)
            span = (s_lo, s_hi, L1 + land)
        else:
            L = n * run
            flights = [dict(start=p0, d=d, side=side, width=w, n=n, run=run, z0=z0, z1=z1)]
            landing = None
            hole = zone(0.0, L, 0.0, w)
            foot = zone(-0.9, 0.0, 0.0, w)
            head = zone(L, L + 0.9, 0.0, w)
            footprint = hole
            arrival = None
            span = (0.0, w, L)
        return dict(flights=flights, landing=landing, hole=hole, foot=foot, head=head, footprint=footprint,
                    floor=fl, to_floor=tf, z0=z0, z1=z1, d=d, side=side, p0=p0, arrival=arrival, span=span)

    def _stair_under(self, x, y, fl):
        """Underside of any flight rising from floor fl over (x, y) -- partitions stop below it."""
        z = 1e9
        for st in self.s.get("stairs", []):
            if st.get("floor", 0) != fl:
                continue
            G = self._stair_geom(st)
            for f in G["flights"]:
                rel = Vector((x, y, 0)) - f["start"]
                L = f["n"] * f["run"]
                along, across = rel.dot(f["d"]), rel.dot(f["side"])
                if -0.1 <= along <= L + 0.1 and -0.1 <= across <= f["width"] + 0.1:
                    z = min(z, f["z0"] + (f["z1"] - f["z0"]) * max(0.0, along) / L - 0.08)
            if G["landing"]:
                (lx0, ly0, lx1, ly1), zl = G["landing"]
                if lx0 - 0.1 <= x <= lx1 + 0.1 and ly0 - 0.1 <= y <= ly1 + 0.1:
                    z = min(z, zl - 0.25)
        return z

    def _partition(self, axis, c, p0, p1, fl):
        # trim ends that run into exterior walls
        te, ti = self.te, self.ti
        bl = self.block_of(c if axis == "x" else (p0 + p1) / 2, (p0 + p1) / 2 if axis == "x" else c)
        if bl is None:
            return
        # every block the line runs along or bounds (a junction between two blocks lies on both)
        mid = (c, (p0 + p1) / 2) if axis == "x" else ((p0 + p1) / 2, c)
        on = [ob for ob in self.s["blocks"]
              if ob["rect"][0] - EPS <= mid[0] <= ob["rect"][2] + EPS and ob["rect"][1] - EPS <= mid[1] <= ob["rect"][3] + EPS]
        if any(fl >= len(ob["floors"]) for ob in on):
            return              # (above the lower block: this block's own upper exterior wall closes the line there)
        for ob in on:           # trim ends that run into any of their exterior walls
            bx0, by0, bx1, by1 = ob["rect"]
            lo_lim, hi_lim = (by0, by1) if axis == "x" else (bx0, bx1)
            if abs(p0 - lo_lim) < EPS:
                p0 += te
            if abs(p1 - hi_lim) < EPS:
                p1 -= te
        if p1 - p0 < 0.1:
            return
        fz, cz = bl["floors"][fl]
        cz = min([cz] + [ob["floors"][fl][1] for ob in on])
        if axis == "x":
            a, cc = (c + ti / 2, p0), (c + ti / 2, p1)
        else:
            a, cc = (p0, c - ti / 2), (p1, c - ti / 2)
        ops, own = self._openings_on(a, cc, ti, [f[0] for f in bl["floors"]], exterior=False)
        ops = [o for o, (k, it) in zip(ops, own) if it.get("floor", 0) == fl]
        own = [(k, it) for (k, it) in own if it.get("floor", 0) == fl]
        o, u, w_in, L = g.wall_frame(a, cc)
        top = lambda uu: min([cz, self._stair_under(a[0] + u.x * uu, a[1] + u.y * uu, fl)]
                             + [self.roof_under(ob, a[0] + u.x * uu, a[1] + u.y * uu) for ob in on])
        fr = g.wall_profile(self.parts, a, cc, fz, top, ti, ops, self.m["int"], self.m["int"])
        self.frames.append(dict(frame=fr, a=a, c=cc, t=ti, ops=ops, own=own, ext=False, block=bl, floor=fl))

    # ---------------------------------------------------------------- openings
    def fit_openings(self):
        b = self.b
        for f in self.frames:
            fr = f["frame"]
            o, u, w_in, up = fr
            for op, (kind, it) in zip(f["ops"], f["own"]):
                if kind == "windows":
                    k = it.get("kind", "dh")
                    if k == "glassblock":
                        b.part("glassblock").obox(fr, (op["off"], f["t"] * 0.3, op["sill"]), (op["off"] + op["w"], f["t"] * 0.7,
                                                  op["head"]), "glassblock")
                        continue
                    g.window(b, "windows", fr, op["off"], op["w"], op["sill"], op["head"], f["t"],
                             sash_rows=1 if k in ("fixed", "picture") else 2, sash_cols=it.get("cols", 1),
                             glass_name="glass", casing=it.get("casing", 0.1), mats={"trim": self.m["trim"]})
                    if it.get("shutters"):
                        g.shutter_pair(b.part("trim"), fr, op["off"], op["w"], op["sill"], op["head"], it.get("shutter_mat", "shutter"))
                    if it.get("head_cap", False):
                        b.part("trim").obox(fr, (op["off"] - 0.13, -0.06, op["head"] + 0.1), (op["off"] + op["w"] + 0.13, 0.0,
                                            op["head"] + 0.17), self.m["trim"])
                else:
                    # which way does it swing?  toward the named room / inward for exterior doors
                    mid = o + u * (op["off"] + op["w"] / 2)
                    if it.get("swing_into"):
                        rc = self.room(it["swing_into"])["rect"]
                        tgt = Vector(((rc[0] + rc[2]) / 2, (rc[1] + rc[3]) / 2, 0))
                        swing_in = (tgt - mid).dot(w_in) > 0
                    else:
                        swing_in = not it.get("out", False) if f["ext"] else True
                    if not it.get("cased"):
                        # record the swept quarter-circles (as their bounding box) so furnish() keeps them clear
                        n_leaves = it.get("leaves", 1)
                        reach = (op["w"] - 0.07) / n_leaves + 0.7      # leaf + a 0.6 m clear landing beyond it
                        face = o + w_in * f["t"] if swing_in else o
                        side = w_in if swing_in else -w_in
                        pts = [face + u * (op["off"] - 0.05) , face + u * (op["off"] + op["w"] + 0.05)]
                        pts += [q + side * reach for q in pts]
                        self.swing_zones.append((min(q.x for q in pts), min(q.y for q in pts), max(q.x for q in pts),
                                                 max(q.y for q in pts), it.get("floor", 0)))
                    hinge_far = it.get("hinge_far")
                    if hinge_far is None and not it.get("cased") and it.get("leaves", 1) == 1:
                        # hang the leaf so that, open, it doesn't lie across a stair's foot or head landing
                        side_v = w_in if swing_in else -w_in
                        face_v = o + w_in * f["t"] if swing_in else o
                        lw = op["w"] - 0.07

                        def leaf_clearance(hinge_a):
                            """Gap between the open leaf and the nearest stair landing on this floor."""
                            hp = face_v + u * hinge_a
                            pts = [hp + u * e_ for e_ in (-0.03, 0.03)] + [hp + u * e_ + side_v * lw for e_ in (-0.03, 0.03)]
                            bx = (min(q.x for q in pts), min(q.y for q in pts), max(q.x for q in pts), max(q.y for q in pts))
                            gaps = [math.hypot(max(0.0, z[0] - bx[2], bx[0] - z[2]), max(0.0, z[1] - bx[3], bx[1] - z[3]))
                                    for z in self._stair_zones(landings_only=True) if z[4] == it.get("floor", 0)]
                            return min(gaps, default=9.0)
                        near, far = leaf_clearance(op["off"] + 0.035), leaf_clearance(op["off"] + op["w"] - 0.035)
                        # a leaf closer than a body's width (0.5 m) to a landing blocks the way onto it:
                        # hang it on whichever jamb leaves more room
                        hinge_far = near < 0.5 and far > near + 0.05
                        if hinge_far:
                            print(f"door {it['name']}: hung on the far jamb (clears the stair landing)")
                    g.door(b, "doorframe", fr, op["off"], op["w"], op["head"], f["t"], it["name"], swing_in=swing_in,
                           leaves=0 if it.get("cased") else it.get("leaves", 1), panels=it.get("panels"), mat=it.get("mat", self.m["door"]),
                           locked=it.get("locked", False), threshold_z=op["sill"], glazed=it.get("glazed"),
                           trim=self.m["trim"], hinge_far=bool(hinge_far))
                    if it.get("transom"):
                        g.transom(b, fr, op["off"], op["w"], op["head"], op["head"] + it["transom"], f["t"], trim=self.m["trim"])
                    if it.get("sidelights"):
                        sl = it["sidelights"]
                        for xs in (op["off"] - sl, op["off"] + op["w"]):
                            g.window(b, "windows", fr, xs, sl, op["sill"] + 0.3, op["head"], f["t"], sash_rows=1, sash_cols=1,
                                     glass_name="glass", casing=0.04, mats={"trim": self.m["trim"]})

    # ---------------------------------------------------------------- floors, ceilings, stairs
    def build_floors(self):
        fl_part = self.b.part("floors-col")
        te = self.te
        holes_by_floor = {}
        for st in self.s.get("stairs", []):
            G = self._stair_geom(st)
            hx0, hy0, hx1, hy1 = G["hole"]
            holes_by_floor.setdefault(G["to_floor"], []).append((hx0, hx1, hy0, hy1))
        for bl in self.s["blocks"]:
            x0, y0, x1, y1 = bl["rect"]
            for i, (fz, cz) in enumerate(bl["floors"]):
                holes = [h for h in holes_by_floor.get(i, []) if x0 < (h[0] + h[1]) / 2 < x1 and y0 < (h[2] + h[3]) / 2 < y1]
                # the slab runs to the block edge: under exterior walls it is hidden, and where the edge
                # is shared with another block (porch, wing) it meets that block's floor -- an inset
                # there left a gap across the doorway
                g.floor_with_holes(fl_part, x0, x1, y0, y1, fz, 0.25 if i else 0.1, holes,
                                   self.m["floor"], self.m["ceiling"])
                # ceiling: flat where the roof leaves room, else the roof underside does the job
                top_floor = i == len(bl["floors"]) - 1
                if not top_floor:
                    continue
                rf = bl.get("roof", {})
                cx0, cy0, cx1, cy1 = x0 + te, y0 + te, x1 - te, y1 - te
                if rf.get("type") in ("gable", "gambrel") and bl.get("habitable_attic", False):
                    # the flat ceiling covers only the middle, where the roof underside is above it;
                    # out toward the eaves the sloped roof underside is the ceiling
                    span = (y1 - y0) if rf["ridge"] == "x" else (x1 - x0)
                    d_in = 0.0
                    while d_in < span / 2 and (self.roof_under(bl, x0 + d_in, (y0 + y1) / 2) if rf["ridge"] == "y"
                                               else self.roof_under(bl, (x0 + x1) / 2, y0 + d_in)) < cz:
                        d_in += 0.02
                    if rf["ridge"] == "x":
                        cy0, cy1 = max(cy0, y0 + d_in), min(cy1, y1 - d_in)
                    else:
                        cx0, cx1 = max(cx0, x0 + d_in), min(cx1, x1 - d_in)
                if cx1 > cx0 and cy1 > cy0:
                    fl_part.box((cx0, cy0, cz), (cx1, cy1, cz + 0.02), self.m["ceiling"], sides="z")
            # intermediate ceilings under upper floors are the undersides of the floor slabs (built above)
            for i, (fz, cz) in enumerate(bl["floors"][:-1]):
                nfz = bl["floors"][i + 1][0]
                if nfz - 0.25 > cz + 0.01:
                    holes = [h for h in holes_by_floor.get(i + 1, []) if x0 < (h[0] + h[1]) / 2 < x1 and y0 < (h[2] + h[3]) / 2 < y1]
                    g.floor_with_holes(fl_part, x0 + te, x1 - te, y0 + te, y1 - te, cz + 0.02, 0.02, holes, self.m["ceiling"],
                                       self.m["ceiling"])
        # special floor finishes per room (kitchen linoleum, bath tile ...)
        for r in self.s["rooms"]:
            fin = r.get("floor_mat")
            if not fin:
                continue
            bl = self.block_of((r["rect"][0] + r["rect"][2]) / 2, (r["rect"][1] + r["rect"][3]) / 2)
            fz = bl["floors"][r.get("floor", 0)][0]
            x0, y0, x1, y1 = self._clear(r)
            self.b.part("floor_finish").face([(x0, y0, fz + 0.003), (x1, y0, fz + 0.003), (x1, y1, fz + 0.003), (x0, y1, fz + 0.003)], fin)

    def build_stairs(self):
        for rl in self.s.get("rails", []):
            pts = rl["pts"]
            mid = (sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts))
            bl = self.block_of(*pts[0]) or self.block_of(*mid) or self.s["blocks"][0]
            g.spindle_rail(self.b.part("well_rails-col"), rl["pts"], bl["floors"][rl.get("floor", 1)][0], 0.9, 0.12, self.m["door"])
        for i, st in enumerate(self.s.get("stairs", [])):
            G = self._stair_geom(st)
            rp = self.b.part("stair_rail-col")
            for j, f in enumerate(G["flights"]):
                o = f["start"]
                g.stairs(self.b, f"stair_{i}_{j}", (o.x, o.y, f["z0"]), (f["d"].x, f["d"].y), f["width"], f["z1"] - f["z0"],
                         f["n"], f["run"], self.m["floor"], self.m["trim"])
            if G["landing"]:
                (lx0, ly0, lx1, ly1), zl = G["landing"]
                self.b.part(f"stair_{i}_landing-col").box((lx0, ly0, zl - 0.2), (lx1, ly1, zl), self.m["floor"],
                                                          mats={"z": self.m["ceiling"]})
            if not st.get("rail", True):
                continue
            # the open side of a straight flight (rail_side, default right); both outer sides of a dogleg
            if len(G["flights"]) == 1:
                f = G["flights"][0]
                sides = [f["width"] if st.get("rail_side", "right") == "left" else 0.0]
                rails = [(f, c) for c in sides]
            else:
                fa, fb = G["flights"]
                rails = [(fa, 0.0 if st.get("turn", "left") == "left" else fa["width"]),
                         (fb, 0.0 if st.get("turn", "left") == "left" else fb["width"])]
            for f, c in rails:
                self._flight_rail(rp, f, c)
            if G["landing"]:
                # guard the far edge of the half landing
                zl = G["landing"][1]
                s_lo, s_hi, a_far = G["span"]
                far = [G["p0"] + G["d"] * a_far + G["side"] * t_ for t_ in (s_lo, s_hi)]
                g.spindle_rail(rp, [(q.x, q.y) for q in far], zl, 0.9, 0.12, self.m["door"])

    def _flight_rail(self, rp, f, c):
        """Balusters + raking handrail along one side (offset c across the flight) of a flight."""
        d, side = f["d"], f["side"]
        edge = f["start"] + side * c
        rh = (f["z1"] - f["z0"]) / f["n"]
        L = f["n"] * f["run"]
        for k in range(f["n"]):
            z = f["z0"] + (k + 1) * rh
            for fr in (0.25, 0.75):
                p = edge + d * ((k + fr) * f["run"])
                top = f["z0"] + rh + 0.88 + ((k + fr) * f["run"]) * (f["z1"] - f["z0"] - rh) / L
                rp.box((p.x - 0.016, p.y - 0.016, z), (p.x + 0.016, p.y + 0.016, top), self.m["door"])
        g.raking_rail(rp, edge + Vector((0, 0, f["z0"] + rh + 0.9)), edge + d * L + Vector((0, 0, f["z1"] + 0.9)), self.m["door"])
        rp.box((edge.x - 0.05, edge.y - 0.05, f["z0"]), (edge.x + 0.05, edge.y + 0.05, f["z0"] + rh + 0.98), self.m["door"])

    # ---------------------------------------------------------------- roofs, porches, chimneys
    def build_roofs(self):
        for bl in self.s["blocks"]:
            rf = bl.get("roof")
            if not rf:
                continue
            x0, y0, x1, y1 = bl["rect"]
            p = self.b.part(f"roof_{bl.get('name', 'b')}-col")
            under = rf.get("under", self.m["roof_under"] if not bl.get("habitable_attic") else self.m["int"])
            if rf["type"] == "gable":
                if rf["ridge"] == "y":
                    zr = g.gable_roof(p, x0, x1, y0, y1, bl["wall_top"], rf["pitch"], rf.get("eave_oh", 0.3), rf.get("rake_oh", 0.25),
                                      rf.get("thick", 0.15), self.m["roof"], under, ridge_axis="y", fascia=self.m["fascia"])
                    p.box(((x0 + x1) / 2 - 0.08, y0 - rf.get("rake_oh", 0.25), zr + 0.02), ((x0 + x1) / 2 + 0.08,
                          y1 + rf.get("rake_oh", 0.25), zr + 0.08), self.m["roof"])
                else:
                    zr = g.gable_roof_x(p, x0, x1, y0, y1, bl["wall_top"], rf["pitch"], rf.get("eave_oh", 0.3),
                                        rf.get("rake_oh", 0.25), rf.get("thick", 0.15), self.m["roof"], under, fascia=self.m["fascia"])
                    p.box((x0 - rf.get("rake_oh", 0.25), (y0 + y1) / 2 - 0.08, zr + 0.02), (x1 + rf.get("rake_oh", 0.25),
                          (y0 + y1) / 2 + 0.08, zr + 0.08), self.m["roof"])
            elif rf["type"] == "hip":
                hip_roof(p, x0, x1, y0, y1, bl["wall_top"], rf["pitch"], rf.get("eave_oh", 0.4), rf.get("thick", 0.15),
                         self.m["roof"], under, self.m["fascia"])
            elif rf["type"] == "flat":
                wt, th, oh = bl["wall_top"], rf.get("thick", 0.25), rf.get("eave_oh", 0.0)
                p.box((x0 - oh, y0 - oh, wt - th), (x1 + oh, y1 + oh, wt), rf.get("membrane", self.m["roof"]),
                      mats={"z": under, **{k: self.m["fascia"] for k in "xXyY"}})
                ph = rf.get("parapet", 0.0)
                if ph > 0:
                    pm = rf.get("parapet_mat", bl.get("ext", self.m["ext"]))
                    t = self.te
                    for (a, c) in (((x0, y0), (x1, y0 + t)), ((x0, y1 - t), (x1, y1)), ((x0, y0), (x0 + t, y1)), ((x1 - t, y0), (x1, y1))):
                        p.box((a[0], a[1], wt), (c[0], c[1], wt + ph), pm)
                    cp = rf.get("coping", self.m["trim"])
                    for (a, c) in (((x0 - 0.04, y0 - 0.04), (x1 + 0.04, y0 + t + 0.04)), ((x0 - 0.04, y1 - t - 0.04), (x1 + 0.04, y1 + 0.04)),
                                   ((x0 - 0.04, y0 - 0.04), (x0 + t + 0.04, y1 + 0.04)), ((x1 - t - 0.04, y0 - 0.04), (x1 + 0.04, y1 + 0.04))):
                        p.box((a[0], a[1], wt + ph), (c[0], c[1], wt + ph + 0.06), cp)
            elif rf["type"] == "gambrel":
                gambrel_roof(p, x0, x1, y0, y1, bl["wall_top"], rf, self.m["roof"], under, self.m["fascia"])
            elif rf["type"] == "shed":
                shed_roof(p, x0, x1, y0, y1, bl["wall_top"], rf["pitch"], rf["high"], rf.get("eave_oh", 0.3), rf.get("thick", 0.12),
                          self.m["roof"], under, self.m["fascia"])

    def build_porches(self):
        for i, po in enumerate(self.s.get("porches", [])):
            p = self.b.part(f"porch_{i}-col")
            x0, y0, x1, y1 = po["rect"]
            z = po["z"]
            p.box((x0, y0, z - 0.15), (x1, y1, z), self.m["porch"], mats={k: self.m["trim"] for k in "xXyY"})
            if po.get("skirt", True):
                p.box((x0 + 0.05, y0 + 0.05, -g.FOUND_DEPTH), (x1 - 0.05, y1 - 0.05, z - 0.15), po.get("skirt_mat", self.m["trim"]), sides="xXyY")
            top = po["post_top"]
            for (px, py) in po.get("posts", []):
                style = po.get("post_style", "square")
                if style == "tuscan":
                    g.column(p, px, py, z, top, 0.11, self.m["post"])
                elif style == "battered":
                    ped = po.get("pedestal", 0.9)
                    p.box((px - 0.22, py - 0.22, z), (px + 0.22, py + 0.22, z + ped), po.get("pedestal_mat", self.m["found"]))
                    p.cylinder((px, py), 0.2, z + ped, top - 0.12, self.m["post"], n=4, r1=0.12)
                    p.box((px - 0.18, py - 0.18, top - 0.12), (px + 0.18, py + 0.18, top), self.m["post"])
                else:
                    w = po.get("post_w", 0.1)
                    p.box((px - w / 2, py - w / 2, z), (px + w / 2, py + w / 2, top), self.m["post"])
            if po.get("beam", True) and po.get("posts"):
                xs = [q[0] for q in po["posts"]]
                ys = [q[1] for q in po["posts"]]
                if max(xs) - min(xs) > max(ys) - min(ys):
                    p.box((min(xs) - 0.1, ys[0] - 0.08, top - 0.02), (max(xs) + 0.1, ys[0] + 0.08, top + 0.2), self.m["trim"])
                else:
                    p.box((xs[0] - 0.08, min(ys) - 0.1, top - 0.02), (xs[0] + 0.08, max(ys) + 0.1, top + 0.2), self.m["trim"])
            for seg in po.get("rails", []):
                if po.get("rail_style") == "balustrade":
                    g.spindle_rail(p, seg, z, 0.8, 0.14, po.get("rail_mat", self.m["trim"]))
                elif po.get("rail_style") == "lattice":
                    for a, c in zip(seg, seg[1:]):
                        lattice_panel(p, a, c, z, z + 2.0, self.m["trim"])
                else:
                    g.spindle_rail(p, seg, z, 0.8, 0.1, self.m["trim"])
            st = po.get("steps")
            if st:
                d = Vector((st["dir"][0], st["dir"][1], 0)).normalized()
                side = Vector((-d.y, d.x, 0))
                n = max(1, round(z / 0.18))
                for k in range(n):
                    zz = z - (k + 1) * z / n
                    c0 = Vector((st["at"][0], st["at"][1], 0)) + d * (k * 0.28) - side * st["width"] / 2
                    c1 = c0 + d * 0.28 + side * st["width"]
                    p.box((min(c0.x, c1.x), min(c0.y, c1.y), -g.FOUND_DEPTH), (max(c0.x, c1.x), max(c0.y, c1.y), zz + z / n), st.get("mat", self.m["porch"]))
            rf = po.get("roof")
            if rf:
                rp = self.b.part(f"porch_{i}_roof-col")
                oh = rf.get("oh", 0.25)
                if rf["type"] == "shed":
                    hs = rf["high"]
                    zh, zl = rf["high_z"], rf["low_z"]
                    if hs == "S":
                        q = [(x0 - oh, y1 + oh, zl), (x1 + oh, y1 + oh, zl), (x1 + oh, y0, zh), (x0 - oh, y0, zh)]
                    elif hs == "N":
                        q = [(x1 + oh, y0 - oh, zl), (x0 - oh, y0 - oh, zl), (x0 - oh, y1, zh), (x1 + oh, y1, zh)][::-1]
                    elif hs == "E":
                        q = [(x0 - oh, y0 - oh, zl), (x1, y0 - oh, zh), (x1, y1 + oh, zh), (x0 - oh, y1 + oh, zl)]
                    else:
                        q = [(x1 + oh, y1 + oh, zl), (x0, y1 + oh, zh), (x0, y0 - oh, zh), (x1 + oh, y0 - oh, zl)]
                    nrm = (Vector(q[1]) - Vector(q[0])).cross(Vector(q[2]) - Vector(q[0]))
                    if nrm.z < 0:
                        q = q[::-1]
                    rp.face(q, self.m["roof"])
                    rp.face([(v[0], v[1], v[2] - 0.1) for v in q[::-1]], self.m["trim"])
                elif rf["type"] == "hip":
                    hip_roof(rp, x0, x1, y0, y1, rf["z"], rf["pitch"], oh, 0.12, self.m["roof"], self.m["trim"], self.m["fascia"])
            if po.get("ceiling_light"):
                self.b.empty("light_porch", ((x0 + x1) / 2, (y0 + y1) / 2, po["post_top"] - 0.1))

    def build_chimneys(self):
        for i, ch in enumerate(self.s.get("chimneys", [])):
            p = self.b.part("chimneys-col")
            x, y = ch["at"]
            w, d = ch.get("w", 0.55), ch.get("d", 0.55)
            p.box((x - w / 2, y - d / 2, ch["z0"]), (x + w / 2, y + d / 2, ch["top"]), ch.get("mat", "chimney"))
            p.box((x - w / 2 - 0.04, y - d / 2 - 0.04, ch["top"] - 0.1), (x + w / 2 + 0.04, y + d / 2 + 0.04, ch["top"]), ch.get("mat", "chimney"))

    def build_fireplaces(self):
        for fp in self.s.get("fireplaces", []):
            r = self.room(fp["room"])
            bl = self.block_of(*fp["at"])
            fz, cz = bl["floors"][r.get("floor", 0)]
            n = Vector((fp["facing"][0], fp["facing"][1], 0)).normalized()
            s = Vector((-n.y, n.x, 0))
            base = Vector((fp["at"][0], fp["at"][1], 0))
            p = self.b.part("fireplaces-col")
            bw, bd = fp.get("w", 1.5), fp.get("d", 0.4)
            top = min(cz, self.roof_under(bl, *fp["at"]))
            for (s0, s1, z0, z1) in ((-bw / 2, -0.42, fz, top), (0.42, bw / 2, fz, top), (-0.42, 0.42, fz + 0.82, top)):
                F = (base + Vector((0, 0, 0)), s, n, Vector((0, 0, 1)))
                p.obox(F, (s0, 0.0, z0), (s1, bd, z1), fp.get("mat", self.m["int"]))
            F = (base, s, n, Vector((0, 0, 1)))
            p.obox(F, (-0.42, 0.0, fz), (0.42, 0.05, fz + 0.82), fp.get("firebox", "chimney"))
            yaw = math.degrees(math.atan2(-n.x, n.y)) + 180
            fu.mantel(p, (base.x + n.x * bd, base.y + n.y * bd, fz), yaw, 1.6,
                      self.m["trim"], fp.get("firebox", "chimney"), h=1.3, d=0.1, opening=(0.84, 0.82))
            self.b.empty("light_fire", (base.x + n.x * (bd + 0.2), base.y + n.y * (bd + 0.2), fz + 0.3))

    # ---------------------------------------------------------------- furnishing
    def _clear(self, r):
        """Room rect shrunk to wall faces (exterior walls te, partitions ti/2)."""
        x0, y0, x1, y1 = r["rect"]
        bl = self.block_of((x0 + x1) / 2, (y0 + y1) / 2)
        bx0, by0, bx1, by1 = bl["rect"]

        def ins(v, edge):
            return self.te if abs(v - edge) < EPS else self.ti / 2
        return (x0 + ins(x0, bx0), y0 + ins(y0, by0), x1 - ins(x1, bx1), y1 - ins(y1, by1))

    def _wall_slots(self, r):
        """For each of the room's 4 sides: (start point, direction, inward normal, length, blocked intervals)."""
        x0, y0, x1, y1 = self._clear(r)
        fl = r.get("floor", 0)
        sides = {"S": ((x0, y0), (1, 0), (0, 1), x1 - x0), "N": ((x1, y1), (-1, 0), (0, -1), x1 - x0),
                 "W": ((x0, y1), (0, -1), (1, 0), y1 - y0), "E": ((x1, y0), (0, 1), (-1, 0), y1 - y0)}
        out = {}
        for k, (p0, d, n, L) in sides.items():
            blocked = []
            for kind in ("doors", "windows"):
                for it in self.s.get(kind, []):
                    if it.get("floor", 0) != fl:
                        continue
                    px, py = it["at"]
                    # distance of opening centre to this wall line
                    dist = abs((px - p0[0]) * n[0] + (py - p0[1]) * n[1])
                    if dist > 0.35:
                        continue
                    along = (px - p0[0]) * d[0] + (py - p0[1]) * d[1]
                    if -0.5 <= along <= L + 0.5:
                        pad = 0.5 if kind == "doors" else 0.05
                        blocked.append((along - it["w"] / 2 - pad, along + it["w"] / 2 + pad, kind, it))
            for fp in self.s.get("fireplaces", []):
                if fp["room"] == r["name"]:
                    px, py = fp["at"]
                    dist = abs((px - p0[0]) * n[0] + (py - p0[1]) * n[1])
                    if dist < 0.6:
                        along = (px - p0[0]) * d[0] + (py - p0[1]) * d[1]
                        blocked.append((along - 1.1, along + 1.1, "fireplace", fp))
            out[k] = dict(p0=Vector((p0[0], p0[1], 0)), d=Vector((d[0], d[1], 0)), n=Vector((n[0], n[1], 0)), L=L, blocked=blocked)
        return out

    def _place(self, slots, w, tall, used, prefer=None, fits=None):
        """Find a free interval of width w on some wall; tall items also avoid windows.
        fits(sl, centre) -> bool rejects spots without headroom (under-eave walls)."""
        order = prefer or sorted(slots, key=lambda k: -slots[k]["L"])
        for k in order:
            sl = slots[k]
            cuts = [(a, b) for (a, b, kind, it) in sl["blocked"] if kind == "doors" or kind == "fireplace" or tall]
            cuts += used.get(k, [])
            free = _subtract((0.05, sl["L"] - 0.05), _union(cuts))
            free = sorted([f for f in free if f[1] - f[0] >= w], key=lambda f: -(f[1] - f[0]))
            for f in free:
                centre = (f[0] + f[1]) / 2
                if fits and not fits(sl, centre):
                    continue
                used.setdefault(k, []).append((centre - w / 2 - 0.05, centre + w / 2 + 0.05))
                return sl, centre
        return None, None

    def _stair_zones(self, landings_only=False):
        """Plan rects (x0, y0, x1, y1, floor): each stair's foot landing (lower floor) and head landing
        (upper floor), plus its footprint on both floors unless landings_only."""
        out = []
        pad = 0.05
        for st in self.s.get("stairs", []):
            G = self._stair_geom(st)
            items = [(G["foot"], G["floor"]), (G["head"], G["to_floor"])]
            if not landings_only:
                items += [(G["footprint"], G["floor"]), (G["footprint"], G["to_floor"])]
            for (x0, y0, x1, y1), fl in items:
                out.append((x0 - pad, y0 - pad, x1 + pad, y1 + pad, fl))
        return out

    def check_stairs(self):
        """Warn when a stair's foot or head landing (0.9 m) isn't clear floor inside the walls."""
        for st in self.s.get("stairs", []):
            G = self._stair_geom(st)
            for name, (x0, y0, x1, y1) in (("foot", G["foot"]), ("head", G["head"])):
                for q in ((x0 + 0.1, y0 + 0.1), (x1 - 0.1, y1 - 0.1), (x0 + 0.1, y1 - 0.1), (x1 - 0.1, y0 + 0.1)):
                    bl = self.block_of(*q)
                    if not bl or not (bl["rect"][0] + self.te - 0.02 <= q[0] <= bl["rect"][2] - self.te + 0.02 and
                                      bl["rect"][1] + self.te - 0.02 <= q[1] <= bl["rect"][3] - self.te + 0.02):
                        print(f"WARNING stair in {self.b.name} at {st['start']}: its {name} landing runs outside the walls")
                        break

    def _stair_keepouts(self):
        """Keep furniture off each flight and its landings."""
        self.swing_zones += self._stair_zones()

    def _hits_swing(self, x0, y0, x1, y1, fl):
        return any(x0 < zx1 and zx0 < x1 and y0 < zy1 and zy0 < y1
                   for (zx0, zy0, zx1, zy1, zf) in self.swing_zones if zf == fl)

    def _walkways(self, r, half=0.45):
        """Plan rects (x0, y0, x1, y1) of a clear walk between every pair of the room's doorways: out
        from each door square to its wall, then an L (doors on adjacent walls) or a Z (opposite walls)."""
        x0, y0, x1, y1 = r["rect"]
        fl = r.get("floor", 0)
        ends = []
        for d in self.s.get("doors", []):
            if d.get("floor", 0) != fl:
                continue
            ax, ay = d["at"]
            if abs(ax - x0) < 0.02 or abs(ax - x1) < 0.02:
                if y0 - 0.01 <= ay <= y1 + 0.01:
                    ends.append(("v", ax, ay))
            elif abs(ay - y0) < 0.02 or abs(ay - y1) < 0.02:
                if x0 - 0.01 <= ax <= x1 + 0.01:
                    ends.append(("h", ax, ay))
        out = []

        def seg(p, q):
            out.append((min(p[0], q[0]) - half, min(p[1], q[1]) - half, max(p[0], q[0]) + half, max(p[1], q[1]) + half))
        for i in range(len(ends)):
            for j in range(i + 1, len(ends)):
                (ka, ax, ay), (kb, bx, by) = ends[i], ends[j]
                if ka == "v" and kb == "v":
                    mx = (ax + bx) / 2
                    seg((ax, ay), (mx, ay)); seg((mx, ay), (mx, by)); seg((mx, by), (bx, by))
                elif ka == "h" and kb == "h":
                    my = (ay + by) / 2
                    seg((ax, ay), (ax, my)); seg((ax, my), (bx, my)); seg((bx, my), (bx, by))
                elif ka == "v":
                    seg((ax, ay), (bx, ay)); seg((bx, ay), (bx, by))
                else:
                    seg((ax, ay), (ax, by)); seg((ax, by), (bx, by))
        # clipped to the room, so they only keep this room's furniture out of the way
        return [(max(a, x0), max(b_, y0), min(c, x1), min(e, y1)) for (a, b_, c, e) in out]

    def _clear_centre(self, cx, cy, hw, hd, fl, room):
        """Shift a free-standing group (half-extents hw, hd) off any door swing, staying inside room."""
        x0, y0, x1, y1 = room
        if not self._hits_swing(cx - hw, cy - hd, cx + hw, cy + hd, fl):
            return cx, cy
        best = None
        for step in [k * 0.1 for k in range(1, 25)]:
            for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx * step, cy + dy * step
                if nx - hw < x0 + 0.05 or nx + hw > x1 - 0.05 or ny - hd < y0 + 0.05 or ny + hd > y1 - 0.05:
                    continue
                if not self._hits_swing(nx - hw, ny - hd, nx + hw, ny + hd, fl):
                    best = (nx, ny)
                    break
            if best:
                return best
        return None

    def furnish(self):
        b, m = self.b, self.m
        fm = m["furn"]
        for r in self.s["rooms"]:
            typ = r.get("type")
            if (not typ and not callable(r.get("fitout"))) or r.get("no_furnish"):
                continue
            b._room = (r["name"], r.get("floor", 0))      # (the furniture recorder files what follows under it)
            bl = self.block_of((r["rect"][0] + r["rect"][2]) / 2, (r["rect"][1] + r["rect"][3]) / 2)
            fz, cz = bl["floors"][r.get("floor", 0)]
            x0, y0, x1, y1 = self._clear(r)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            p = b.part(f"furn_{r['name']}-col")
            self.swing_zones += [w_ + (r.get("floor", 0),) for w_ in self._walkways(r)]
            slots = self._wall_slots(r)
            used = {}

            def headroom(pt):
                return min(cz, self.roof_under(bl, pt.x, pt.y)) - fz

            def against(w, d, tall, fn, prefer=None, h=None):
                h_req = h if h is not None else (1.9 if tall else 0.95)

                def fits(sl, c):
                    back = sl["p0"] + sl["d"] * c + sl["n"] * 0.05
                    ends = [back + sl["d"] * (w / 2), back - sl["d"] * (w / 2)]
                    if not all(headroom(q) >= h_req + 0.05 for q in [back] + ends):
                        return False
                    corners = ends + [q + sl["n"] * (d + 0.02) for q in ends]
                    # (the front under the roof too: against an inner wall the slope can fall away from it)
                    if not all(headroom(q) >= h_req + 0.05 for q in corners[2:]):
                        return False
                    # (and inside the room: a 2 m bed doesn't go across a 1.9 m room, through the far wall)
                    if not all(x0 - 0.01 <= q.x <= x1 + 0.01 and y0 - 0.01 <= q.y <= y1 + 0.01 for q in corners):
                        return False
                    return not self._hits_swing(min(q.x for q in corners), min(q.y for q in corners),
                                                max(q.x for q in corners), max(q.y for q in corners), r.get("floor", 0))
                sl, c = self._place(slots, w, tall, used, prefer, fits)
                if sl is None:
                    return None
                pos = sl["p0"] + sl["d"] * c + sl["n"] * (d / 2 + 0.02)
                yaw = math.degrees(math.atan2(sl["n"].x, -sl["n"].y))
                fn((pos.x, pos.y, fz), yaw)
                return pos, sl

            era = self.s.get("era", "modern")
            low = min(cz, self.roof_under(bl, cx, cy)) - fz < 2.0
            if callable(r.get("fitout")):
                # custom fit-out (shops, offices, halls...): gets the same placement helpers
                r["fitout"](self, r, p, against, (x0, y0, x1, y1), fz, cz)
            elif typ == "bed":
                bw = 1.4 if (x1 - x0) * (y1 - y0) > 9 else 1.0
                res = against(bw + 0.9, 2.05, False, lambda pos, yaw: (fu.bed(p, pos, yaw, bw, 1.95, fm, r.get("linen", "quilt")),),
                              h=1.25)                       # (its headboard stands ~1.1 m: under an attic's slope it clipped)
                against(1.0, 0.5, not low, lambda pos, yaw: fu.dresser(p, pos, yaw, 1.0, 0.5, 0.85, fm, m["brass"],
                                                                        mirror_mat=None if low else "glass"))
                against(0.5, 0.45, False, lambda pos, yaw: fu.chair(p, pos, yaw, fm))
            elif typ == "living":
                against(2.0, 0.9, False, lambda pos, yaw: fu.sofa(p, pos, yaw, 2.0, r.get("uph", "upholstery"), fm))
                against(0.9, 0.85, False, lambda pos, yaw: fu.armchair(p, pos, yaw, r.get("uph", "upholstery"), fm))
                if era == "modern":
                    against(1.3, 0.45, False, lambda pos, yaw: tv_stand(p, pos, yaw, fm, "tv"))
                else:
                    against(0.8, 0.45, False, lambda pos, yaw: fu.radio(p, pos, yaw, fm, "burlap"))
                against(0.9, 0.35, True, lambda pos, yaw: fu.shelves(p, pos, yaw, 0.9, 0.35, 1.8, 5, fm))
                tc = self._clear_centre(cx, cy, 0.55, 0.3, r.get("floor", 0), (x0, y0, x1, y1))
                if tc:
                    fu.table(p, (tc[0], tc[1], fz), 0, 1.0, 0.5, 0.45, fm)
                rug(p, cx, cy, fz, min(2.4, x1 - x0 - 1.0), min(1.7, y1 - y0 - 1.0), r.get("rug", "rug"))
            elif typ == "sitting":
                against(0.9, 0.85, False, lambda pos, yaw: fu.armchair(p, pos, yaw, r.get("uph", "upholstery"), fm))
                against(0.9, 0.85, False, lambda pos, yaw: fu.armchair(p, pos, yaw, r.get("uph", "upholstery"), fm))
                against(1.2, 0.6, False, lambda pos, yaw: fu.desk(p, pos, yaw, fm, m["brass"], w=1.2, d=0.6))
                against(0.9, 0.35, True, lambda pos, yaw: fu.shelves(p, pos, yaw, 0.9, 0.35, 1.8, 5, fm))
            elif typ == "dining":
                tw, td = (1.6, 0.9) if (x1 - x0) > (y1 - y0) else (0.9, 1.6)
                hw, hd = (tw / 2, 0.9) if tw > td else (0.9, td / 2)
                tc = self._clear_centre(cx, cy, hw, hd, r.get("floor", 0), (x0, y0, x1, y1))
                if tc:
                    tx, ty = tc
                    fu.table(p, (tx, ty, fz), 0, tw, td, 0.76, fm)
                    if tw > td:
                        for ox in (-0.45, 0.45):
                            fu.chair(p, (tx + ox, ty - 0.65, fz), 180, fm)
                            fu.chair(p, (tx + ox, ty + 0.65, fz), 0, fm)
                    else:
                        for oy in (-0.45, 0.45):
                            fu.chair(p, (tx - 0.65, ty + oy, fz), 90, fm)
                            fu.chair(p, (tx + 0.65, ty + oy, fz), -90, fm)
                against(1.4, 0.5, False, lambda pos, yaw: fu.dresser(p, pos, yaw, 1.4, 0.5, 0.9, fm, m["brass"], drawers=2))
                rug(p, cx, cy, fz, min(2.6, x1 - x0 - 0.8), min(2.0, y1 - y0 - 0.8), r.get("rug", "rug"))
            elif typ == "kitchen":
                against(0.78, 0.68, False, lambda pos, yaw: fu.range_stove(p, pos, yaw, "enamel", "iron", w=0.76, d=0.66))
                against(1.8, 0.62, False, lambda pos, yaw: fu.sink_counter(p, pos, yaw, 1.8, r.get("cab", fm), "counter_top", "steel"))
                against(0.8, 0.72, True, lambda pos, yaw: fu.fridge(p, pos, yaw, "enamel", "steel"))
                against(1.2, 0.62, False, lambda pos, yaw: base_cabinets(p, pos, yaw, 1.2, r.get("cab", fm), "counter_top"))
                tc = self._clear_centre(cx, cy, 1.05, 0.45, r.get("floor", 0), (x0, y0, x1, y1)) if (x1 - x0) * (y1 - y0) > 9 else None
                if tc:
                    fu.table(p, (tc[0], tc[1], fz), 0, 1.1, 0.8, 0.76, fm)
                    for (ox, yaw) in ((-0.8, -90), (0.8, 90)):
                        fu.chair(p, (tc[0] + ox, tc[1], fz), yaw, fm)
            elif typ == "bath":
                against(1.55, 0.78, False, lambda pos, yaw: tub(p, pos, yaw, "enamel"))
                against(0.5, 0.7, False, lambda pos, yaw: fu.toilet(p, pos, yaw, "china", "china"))
                against(0.7, 0.5, False, lambda pos, yaw: vanity(p, pos, yaw, fm, "china", "steel"))
            elif typ == "hall":
                against(0.5, 0.45, False, lambda pos, yaw: fu.coat_rack(p, (pos[0], pos[1], fz), fm))
            elif typ == "laundry":
                against(0.7, 0.7, False, lambda pos, yaw: appliance(p, pos, yaw, "enamel", 0.9))
                against(0.7, 0.7, False, lambda pos, yaw: appliance(p, pos, yaw, "enamel", 0.9))
            elif typ == "closet":
                cw = min(1.2, max(0.5, max(x1 - x0, y1 - y0) - 0.2))
                sh = max(0.6, min(1.8, headroom(Vector((cx, cy, 0))) - 0.15))
                against(cw, 0.4, False, lambda pos, yaw: fu.shelves(p, pos, yaw, cw, 0.4, sh, 3, fm), h=sh)
            if not r.get("no_light"):
                lz = min(cz, self.roof_under(bl, cx, cy)) - 0.25
                b.empty(f"light_locked_{typ}" if r.get("locked") else f"light_{typ}", (cx, cy, lz))

    def build(self):
        self.b.plans.append(self.s)
        self.b.houses.append(self)
        for bl in self.s["blocks"]:
            self.b.massing.append(dict(rect=bl["rect"], top=bl["wall_top"], mat=bl.get("ext", self.m["ext"])))
        self.build_exterior()
        self.build_partitions()
        self.fit_openings()
        self.build_floors()
        self.build_stairs()
        self.build_roofs()
        self.build_porches()
        self.build_chimneys()
        self.build_fireplaces()
        self.check_stairs()
        if self.s.get("furnish", True):
            self._stair_keepouts()
            self.furnish()
            self.b._room = None


# ------------------------------------------------------------------ roof helpers
def gambrel_rise(d, span, rf):
    """Height of a gambrel roof's top above the wall plate at distance d in from an eave:
    a steep lower slope (pitch_lower, default 60) to the knee (knee_frac of the half span, default
    0.45), then the shallow upper slope (pitch, default 25) to the ridge."""
    half = span / 2
    a = half * rf.get("knee_frac", 0.45)
    t1, t2 = math.tan(math.radians(rf.get("pitch_lower", 60))), math.tan(math.radians(rf.get("pitch", 25)))
    d = max(0.0, min(d, half))
    return d * t1 if d <= a else a * t1 + (d - a) * t2


def gambrel_roof(p, x0, x1, y0, y1, wt, rf, mat_top, mat_under, fascia):
    """Gambrel (barn) roof over the rectangle; ridge along rf['ridge'] ('x' or 'y')."""
    ridge = rf.get("ridge", "y")
    span = (x1 - x0) if ridge == "y" else (y1 - y0)
    oh, rake, th = rf.get("eave_oh", 0.3), rf.get("rake_oh", 0.25), rf.get("thick", 0.15)
    half = span / 2
    knee = half * rf.get("knee_frac", 0.45)
    t1 = math.tan(math.radians(rf.get("pitch_lower", 60)))
    prof = [(-oh, -oh * t1), (knee, gambrel_rise(knee, span, rf)), (half, gambrel_rise(half, span, rf))]
    prof = prof + [(span - u, z) for (u, z) in reversed(prof[:-1])]
    a0, a1 = ((y0, y1) if ridge == "y" else (x0, x1))
    a0, a1 = a0 - rake, a1 + rake
    c0 = x0 if ridge == "y" else y0

    def P(u, a, z):
        return (c0 + u, a, wt + z) if ridge == "y" else (a, c0 + u, wt + z)
    for (u0, z0), (u1, z1) in zip(prof, prof[1:]):
        top = [P(u0, a0, z0), P(u1, a0, z1), P(u1, a1, z1), P(u0, a1, z0)]
        if ridge == "y":
            top = top[::-1]
        p.face(top if ridge == "y" else top, mat_top)
        bot = [(q[0], q[1], q[2] - th) for q in top]
        p.face(bot[::-1], mat_under)
    for a, flip in ((a0, ridge == "y"), (a1, ridge != "y")):
        outer = [P(u, a, z) for (u, z) in prof]
        inner = [P(u, a, z - th) for (u, z) in prof]
        for q0, q1, r0, r1 in zip(outer, outer[1:], inner, inner[1:]):
            quad = [q0, q1, r1, r0]
            p.face(quad[::-1] if flip else quad, fascia)
    for u, z in (prof[0], prof[-1]):
        q = [P(u, a0, z), P(u, a1, z), P(u, a1, z - th), P(u, a0, z - th)]
        p.face(q if (u < half) == (ridge == "y") else q[::-1], fascia)


def hip_roof(p, x0, x1, y0, y1, z_eave, pitch, oh, thick, mat_top, mat_under, fascia):
    tn = math.tan(math.radians(pitch))
    X0, X1, Y0, Y1 = x0 - oh, x1 + oh, y0 - oh, y1 + oh
    ze = z_eave - oh * tn
    w, l = X1 - X0, Y1 - Y0
    h = min(w, l) / 2 * tn
    zr = ze + h
    if w >= l:
        r0, r1 = (X0 + l / 2, (Y0 + Y1) / 2), (X1 - l / 2, (Y0 + Y1) / 2)
    else:
        r0, r1 = ((X0 + X1) / 2, Y0 + w / 2), ((X0 + X1) / 2, Y1 - w / 2)
    A, B, C, D = (X0, Y0, ze), (X1, Y0, ze), (X1, Y1, ze), (X0, Y1, ze)
    R0, R1 = (r0[0], r0[1], zr), (r1[0], r1[1], zr)
    if w >= l:
        faces = [[A, B, R1, R0], [B, C, R1], [C, D, R0, R1], [D, A, R0]]
    else:
        faces = [[A, B, R0], [B, C, R1, R0], [C, D, R1], [D, A, R0, R1]]
    for f in faces:
        f = [tuple(v) for v in f]
        # de-duplicate degenerate quads (square pyramid)
        uniq = []
        for v in f:
            if not uniq or math.dist(v, uniq[-1]) > 1e-4:
                uniq.append(v)
        if len(uniq) > 2 and math.dist(uniq[0], uniq[-1]) < 1e-4:
            uniq.pop()
        p.face(uniq, mat_top, uvs=None)
        p.face([(v[0], v[1], v[2] - thick) for v in reversed(uniq)], mat_under)
    for (a, c) in ((A, B), (B, C), (C, D), (D, A)):
        p.face([a, c, (c[0], c[1], c[2] - thick), (a[0], a[1], a[2] - thick)][::-1], fascia)
    return zr


def shed_roof(p, x0, x1, y0, y1, z_wall, pitch, high, oh, thick, mat_top, mat_under, fascia):
    tn = math.tan(math.radians(pitch))
    span = (y1 - y0) if high in "NS" else (x1 - x0)
    zl, zh = z_wall, z_wall + span * tn
    X0, X1, Y0, Y1 = x0 - oh, x1 + oh, y0 - oh, y1 + oh
    zlo, zhi = zl - oh * tn, zh + oh * tn
    if high == "N":
        q = [(X0, Y0, zlo), (X1, Y0, zlo), (X1, Y1, zhi), (X0, Y1, zhi)]
    elif high == "S":
        q = [(X0, Y0, zhi), (X1, Y0, zhi), (X1, Y1, zlo), (X0, Y1, zlo)]
    elif high == "E":
        q = [(X0, Y0, zlo), (X1, Y0, zhi), (X1, Y1, zhi), (X0, Y1, zlo)]
    else:
        q = [(X0, Y0, zhi), (X1, Y0, zlo), (X1, Y1, zlo), (X0, Y1, zhi)]
    p.face(q, mat_top)
    p.face([(v[0], v[1], v[2] - thick) for v in reversed(q)], mat_under)
    for k in range(4):
        a, c = q[k], q[(k + 1) % 4]
        p.face([a, (a[0], a[1], a[2] - thick), (c[0], c[1], c[2] - thick), c], fascia)
    return zhi


def lattice_panel(p, a, c, z0, z1, mat, spacing=0.12):
    A, C = Vector((a[0], a[1], 0)), Vector((c[0], c[1], 0))
    L = (C - A).length
    u = (C - A).normalized()
    v = Vector((-u.y, u.x, 0))
    F = (A, u, v, Vector((0, 0, 1)))
    h = z1 - z0
    k = -h
    while k < L:
        # diagonal slats both ways, clipped roughly to the panel box
        for sgn in (1, -1):
            s0 = max(0.0, k) if sgn > 0 else max(0.0, k)
            s1 = min(L, k + h)
            if s1 - s0 > 0.05:
                p.obox(F, (s0, -0.01, z0 + (s0 - k) * (1 if sgn > 0 else 0) + (0 if sgn > 0 else (k + h - s1))),
                       (s0 + 0.03, 0.01, z0 + min(h, (s1 - k))), mat)
        k += spacing * 3
    p.obox(F, (0, -0.02, z1 - 0.05), (L, 0.02, z1), mat)
    p.obox(F, (0, -0.02, z0), (L, 0.02, z0 + 0.05), mat)


# ------------------------------------------------------------------ small furniture not in gbfurn
def tv_stand(p, pos, yaw, mat, screen_mat):
    f = fu.F(pos, yaw)
    p.obox(f, (-0.65, -0.22, 0), (0.65, 0.22, 0.55), mat)
    p.obox(f, (-0.55, 0.0, 0.58), (0.55, 0.05, 1.2), screen_mat)
    p.obox(f, (-0.1, -0.05, 0.55), (0.1, 0.1, 0.58), screen_mat)


def rug(p, cx, cy, z, w, d, mat):
    if w > 0.6 and d > 0.6:
        p.face([(cx - w / 2, cy - d / 2, z + 0.006), (cx + w / 2, cy - d / 2, z + 0.006), (cx + w / 2, cy + d / 2, z + 0.006),
                (cx - w / 2, cy + d / 2, z + 0.006)], mat)


def base_cabinets(p, pos, yaw, length, body_mat, top_mat, d=0.62):
    f = fu.F(pos, yaw)
    p.obox(f, (-length / 2, -d / 2, 0.1), (length / 2, d / 2, 0.88), body_mat)
    p.obox(f, (-length / 2 - 0.02, -d / 2 - 0.03, 0.88), (length / 2, d / 2, 0.92), top_mat)
    for k in range(int(length / 0.45)):
        x = -length / 2 + 0.03 + k * 0.45
        p.obox(f, (x, -d / 2 - 0.01, 0.15), (x + 0.42, -d / 2, 0.82), body_mat)
    # wall cabinets
    p.obox(f, (-length / 2, d / 2 - 0.33, 1.45), (length / 2, d / 2, 2.15), body_mat)


def tub(p, pos, yaw, mat):
    f = fu.F(pos, yaw)
    p.obox(f, (-0.75, -0.37, 0), (0.75, 0.37, 0.55), mat)
    p.obox(f, (-0.65, -0.27, 0.2), (0.65, 0.27, 0.551), mat)


def vanity(p, pos, yaw, mat, basin_mat, tap_mat):
    f = fu.F(pos, yaw)
    p.obox(f, (-0.35, -0.24, 0), (0.35, 0.24, 0.82), mat)
    p.obox(f, (-0.37, -0.26, 0.82), (0.37, 0.25, 0.86), basin_mat)
    p.obox(f, (-0.3, 0.2, 1.1), (0.3, 0.24, 1.75), "glass")
    p.obox(f, (-0.02, 0.12, 0.86), (0.02, 0.2, 1.0), tap_mat)


def appliance(p, pos, yaw, mat, h):
    f = fu.F(pos, yaw)
    p.obox(f, (-0.34, -0.33, 0), (0.34, 0.33, h), mat)
    p.obox(f, (-0.32, -0.34, h - 0.15), (0.32, -0.33, h - 0.02), "steel")


# ------------------------------------------------------------------ site: fences, gates, mailboxes
def picket_fence(b, pts, h, mat, name="fence", gate=None, spacing=0.11):
    """Picket fence along a polyline.  gate=(segment_index, offset_m, width_m): that stretch gets a
    real swinging gate (a door_* leaf, so Godot opens it like any door)."""
    p = b.part(f"{name}-col")
    for si, (a, c) in enumerate(zip(pts, pts[1:])):
        A, C = Vector((a[0], a[1], 0)), Vector((c[0], c[1], 0))
        L = (C - A).length
        u = (C - A).normalized()
        v = Vector((-u.y, u.x, 0))
        F = (A, u, v, Vector((0, 0, 1)))
        gap = None
        if gate and gate[0] == si:
            gap = (gate[1], gate[1] + gate[2])
        runs = [(0.0, L)] if not gap else [(0.0, gap[0]), (gap[1], L)]
        for (r0, r1) in runs:
            if r1 - r0 < 0.05:
                continue
            for z in (0.2, h - 0.25):
                p.obox(F, (r0, 0.02, z), (r1, 0.06, z + 0.08), mat)
            k = r0 + 0.04
            while k < r1 - 0.04:
                p.obox(F, (k - 0.035, -0.01, 0.05), (k + 0.035, 0.01, h - 0.08), mat)
                p.obox(F, (k - 0.02, -0.01, h - 0.08), (k + 0.02, 0.01, h), mat)
                k += spacing
            for post in (r0, r1):
                p.obox(F, (post - 0.045, -0.02, 0), (post + 0.045, 0.09, h + 0.1), mat)
        if gap:
            hinge = A + u * (gap[0] + 0.03)
            leaf = b.part(f"door_{name}_gate__p")
            leaf.origin = Vector((0, 0, 0))
            Fl = (Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
            gw = gate[2] - 0.06
            for z in (0.2, h - 0.25):
                leaf.obox(Fl, (0, 0.02, z), (gw, 0.06, z + 0.08), mat)
            k = 0.05
            while k < gw - 0.03:
                leaf.obox(Fl, (k - 0.035, -0.01, 0.08), (k + 0.035, 0.01, h - 0.08), mat)
                leaf.obox(Fl, (k - 0.02, -0.01, h - 0.08), (k + 0.02, 0.01, h - 0.02), mat)
                k += spacing
            leaf.obox(Fl, (0.02, 0.02, 0.25), (gw - 0.02, 0.05, h - 0.3), mat)          # diagonal brace (flattened)
            leaf.origin = Vector((hinge.x, hinge.y, 0.0))
            leaf.rot_z = math.atan2(u.y, u.x)


def mailbox(b, pos, facing_deg, name_text, number_text, body_mat, post_mat, text_mat, part="mailbox-col"):
    """Rural/curbside post-mounted mailbox with the family name and house number."""
    p = b.part(part)
    f = fu.F(pos, facing_deg)
    p.obox(f, (-0.05, -0.05, 0), (0.05, 0.05, 1.05), post_mat)
    p.obox(f, (-0.12, -0.25, 1.05), (0.12, 0.25, 1.28), body_mat)
    c = f[0]
    ang = math.radians(facing_deg)
    side = Vector((math.cos(ang), math.sin(ang), 0))
    for sgn in (1, -1):
        loc = c + side * (0.125 * sgn) + Vector((0, 0, 1.16))
        g.text_mesh(b, f"sign_mailbox_{name_text}_{sgn}", name_text, 0.055, tuple(loc),
                    ang + (math.pi / 2 if sgn > 0 else -math.pi / 2), text_mat, extrude=0.002,
                    font="/run/host/usr/share/fonts/noto/NotoSans-Bold.ttf")
    g.text_mesh(b, f"sign_housenum_{number_text}", number_text, 0.07, tuple(c + Vector((0, 0, 0.9)) - f[2] * 0.06),
                ang, text_mat, extrude=0.002, font="/run/host/usr/share/fonts/noto/NotoSans-Bold.ttf")


def std_house_materials(b, textures, tiles=None):
    """Register a house texture set (texgen names) + the plain materials every house uses."""
    tiles = tiles or {}
    default_tile = {"floor": 2.0, "plaster": 2.0, "porch": 2.0, "found": 1.2, "foundation": 1.2, "lino": 0.9144,
                    "hextile": 0.3048, "iron": 0.5, "wallpaper_a": 0.9144, "siding": 1.0}
    for name in textures:
        b.mat(name, tex=name, tile_m=tiles.get(name, default_tile.get(name, 1.0)))
    for k, c, r in (("brass", (0.75, 0.6, 0.28), 0.3), ("threshold", (0.5, 0.48, 0.44), 0.8), ("enamel", (0.93, 0.93, 0.9), 0.3),
                    ("steel", (0.7, 0.72, 0.74), 0.35), ("china", (0.96, 0.96, 0.94), 0.2), ("counter_top", (0.78, 0.74, 0.66), 0.4),
                    ("upholstery", (0.35, 0.42, 0.33), 0.9), ("quilt", (0.6, 0.25, 0.22), 0.9), ("rug", (0.45, 0.2, 0.18), 0.95),
                    ("tv", (0.05, 0.05, 0.06), 0.2), ("burlap", (0.6, 0.5, 0.35), 0.95), ("mail_black", (0.08, 0.08, 0.08), 0.4),
                    ("white_text", (0.95, 0.95, 0.95), 0.5), ("shutter", (0.18, 0.28, 0.2), 0.55), ("car_paint", (0.35, 0.05, 0.06), 0.3),
                    ("tire", (0.05, 0.05, 0.05), 0.9), ("chainlink", (0.62, 0.64, 0.66), 0.4)):
        b.mat(k, color=c, rough=r, metal=0.9 if k in ("brass", "steel", "chainlink") else 0.0)
    b.mat("glass", color=(0.72, 0.8, 0.84), rough=0.05, alpha=0.2)
    b.mat("glassblock", color=(0.75, 0.82, 0.85), rough=0.2, alpha=0.6)


def chainlink_fence(b, pts, h, name="chainlink", gate=None):
    """Galvanised chain-link fence: pipe posts, top rail, semi-transparent mesh.  gate as picket_fence."""
    p = b.part(f"{name}-col")
    b.mat("mesh", color=(0.6, 0.62, 0.64), rough=0.4, alpha=0.35)
    for si, (a, c) in enumerate(zip(pts, pts[1:])):
        A, C = Vector((a[0], a[1], 0)), Vector((c[0], c[1], 0))
        L = (C - A).length
        u = (C - A).normalized()
        v = Vector((-u.y, u.x, 0))
        F = (A, u, v, Vector((0, 0, 1)))
        gap = (gate[1], gate[1] + gate[2]) if gate and gate[0] == si else None
        runs = [(0.0, L)] if not gap else [(0.0, gap[0]), (gap[1], L)]
        for r0, r1 in runs:
            if r1 - r0 < 0.05:
                continue
            p.obox(F, (r0, -0.02, h - 0.04), (r1, 0.02, h), "chainlink")
            mesh = b.part(f"{name}_mesh")
            P = lambda s, z: tuple(A + u * s + Vector((0, 0, z)))
            mesh.face([P(r0, 0.05), P(r1, 0.05), P(r1, h - 0.04), P(r0, h - 0.04)], "mesh")
            mesh.face([P(r1, 0.05), P(r0, 0.05), P(r0, h - 0.04), P(r1, h - 0.04)], "mesh")
            n = max(1, int((r1 - r0) / 3.0))
            for k in range(n + 1):
                s_ = r0 + (r1 - r0) * k / n
                p.cylinder(tuple(A + u * s_)[:2], 0.03, 0, h + 0.05, "chainlink", n=8)
        if gap:
            hinge = A + u * (gap[0] + 0.03)
            leaf = b.part(f"door_{name}_gate__p")
            Fl = (Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
            gw = gate[2] - 0.06
            for (x0, x1, z0, z1) in ((0, 0.04, 0.05, h - 0.05), (gw - 0.04, gw, 0.05, h - 0.05), (0, gw, h - 0.09, h - 0.05),
                                     (0, gw, 0.05, 0.09)):
                leaf.obox(Fl, (x0, -0.02, z0), (x1, 0.02, z1), "chainlink")
            leaf.face([(0.04, 0, 0.09), (gw - 0.04, 0, 0.09), (gw - 0.04, 0, h - 0.09), (0.04, 0, h - 0.09)], "mesh")
            leaf.face([(gw - 0.04, 0, 0.09), (0.04, 0, 0.09), (0.04, 0, h - 0.09), (gw - 0.04, 0, h - 0.09)], "mesh")
            leaf.origin = Vector((hinge.x, hinge.y, 0.0))
            leaf.rot_z = math.atan2(u.y, u.x)


def car(b, pos, yaw, name="car"):
    """A parked sedan silhouette (for garages/driveways)."""
    p = b.part(f"{name}-col")
    f = fu.F(pos, yaw)
    p.obox(f, (-0.9, -2.3, 0.3), (0.9, 2.3, 0.85), "car_paint")
    p.obox(f, (-0.8, -1.0, 0.85), (0.8, 1.1, 1.35), "car_paint")
    p.obox(f, (-0.78, -0.95, 0.9), (0.78, 1.05, 1.3), "glass")
    for sx in (-1, 1):
        for sy in (-1.4, 1.4):
            c = f[0] + f[1] * (sx * 0.8) + f[2] * sy
            p.obox(fu.F((c.x, c.y, f[0].z), yaw), (-0.1, -0.33, 0.0), (0.1, 0.33, 0.66), "tire")
