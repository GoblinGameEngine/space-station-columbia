"""
loft.py -- a road vehicle's class standard, generated from a spec: the body loft (the exterior and interior
profiles at every station), the tube frame's rings, the slots, the closers' hinges and the damage settings.
It is kit/sw180.py (the Carrow wagon's standard, written by hand) made general, so every class is a spec
(remake/blender/vehicles/fleet_specs.py) rather than a module of code. research/vehicles/FLEET_BODIES.md.

Coordinates: Blender (X right, Y forward, Z up), metres; z = 0 the ground, y = 0 midway between the board's
outer axles.

THE PROFILE. A loop of 13 points per half (skirt, sill, arch, belt, 2 between, head, drip, cant, 4 across the
roof to the crown), the same count at every station, so the loft is a grid and every panel a rectangle of its
cells (sealed by construction). Along the car the top changes by zone:
  front  "hood"  (a bonnet: the top is the hood from the cowl to the nose, a frunk lid in it), or
         "flat"  (cab-forward: the windscreen starts low just behind the nose);
  middle the greenhouse: side glass from the belt to the head, the roof above; the A-pillar's line from the
         windscreen's foot to the header; on a "trunk" rear the C-pillar's line from the roof down to the deck;
  rear   "hatch" (the roof runs to the tail; a top-hinged hatch in the tail), "trunk" (a sloped rear window
         and a deck with a lid), or "wall" (a cab's back wall, with a back window; a cargo module behind).
"""
import json
import math
import os

PLATFORMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "godot_project", "remake",
                         "vehicles", "chassis", "platforms.json")
E = {"skirt": 0, "sill": 1, "arch": 2, "belt": 3, "head": 6, "cant": 8, "roof": 10, "crown": 12}
NE = 13
NI = 30
RING_NAMES = ["skirt_R", "sill_R", "belt_R", "head_R", "cant_R", "roof_R", "crown", "roof_L", "cant_L", "head_L",
              "belt_L", "sill_L", "skirt_L", "floor_C"]
_ARC = [0.92, 0.80, 0.60, 0.33, 0.0, -0.33, -0.60, -0.80]          # (fractions of arch_half: the round arches)


def tyre_w(B):
    """The board's tyre width (its wheel modules' size)."""
    for m in B["modules"]:
        if m["id"].startswith("wheel_"):
            return 0.32 if B.get("family") == "steward" and B["wheel_r"] >= 0.35 else (0.24 if B.get("family") == "steward" else m["size"][0])
    return 0.2


def board(bid):
    for b in json.load(open(PLATFORMS))["boards"]:
        if b["id"] == bid:
            return b
    raise KeyError(bid)


E_HIGH = {"skirt": 0, "arch": 1, "sill": 2, "belt": 3, "head": 6, "cant": 8, "roof": 10, "crown": 12}


class Loft:
    def __init__(self, spec):
        S = self.spec = spec
        self.high = S.get("high_floor", False)               # (a cab over its wheels: the arch is below the door sill)
        self.E = E_HIGH if self.high else E
        self.id = S["id"]
        B = self.board = board(S["board"])
        self.deck = 0.50
        self.mount_x = B["mount_x_m"]
        self.wheel_r = B["wheel_r"]
        self.axles = [a["y"] for a in B["axles"]]
        self.track = B["track_m"]
        self.tyre_w = tyre_w(B)
        # the wheel well's inner wall: clear of the pods / corners (their inner faces)
        pods = [m for m in B["modules"] if m["id"].startswith(("pod_", "corner_")) and m["id"][-1] in "LR"]
        inner = min(abs(m["pos"][0]) - m["size"][0] / 2 for m in pods) if pods else self.track / 2 - 0.30
        tw = tyre_w(B)
        sweep = self.track / 2 - (tw / 2 * math.cos(math.radians(35)) + self.wheel_r * math.sin(math.radians(35))) - 0.06   # (a steered tyre's inner corner)
        steers = any(a.get("steer") for a in B["axles"])
        self.well_x = S.get("well_x", round(min(inner - 0.03, self.track / 2 - self.wheel_r * 0.45 - 0.16, sweep if steers else 9.0), 3))
        self.arch_half = S.get("arch_half", round(self.wheel_r + 0.10, 3))
        self.arch_r = S.get("arch_r", round(self.wheel_r + 0.18, 3))
        for k in ("nose", "tail", "half_w", "skirt", "sill", "floor", "belt", "head", "cant", "crown", "headliner"):
            setattr(self, k, S[k])
        self.arch_top = S.get("arch_top", round(self.wheel_r * 2 + 0.21, 3))
        self.wheels_out = S.get("wheels_outside", False)    # (a body narrower than its track: no arches, no wells -- a tractor's)
        if self.wheels_out:
            self.arch_top = round(S["sill"] + 0.002, 4)
        self.arch_zc = self.arch_top - self.arch_r
        self.int_off = S.get("int_off", 0.06)
        self.tumble = S.get("tumble", 0.06)                   # the side leans in this much from the belt to the head
        self.cant_in = S.get("cant_in", 0.07)                 # and this much more from the head to the cant
        self.pillar = S.get("pillar", 0.09)
        F = self.front = S["front"]
        R = self.rear = S["rear"]
        self.toe, self.header = F["toe"], F["header"]
        self.screen_base = F.get("screen_base", self.belt + 0.02)
        self.lid = tuple(F["lid"]) if F.get("lid") else None
        self.tail_in = R["tail_in"]
        self.cab_end = R["c_foot"] if R["kind"] == "trunk" else self.tail_in
        self.doors = S["doors"]
        self.windows = S.get("windows", [])
        self._stations()

    # ------------------------------------------------------------ the shape
    def arch_z(self, y):
        if getattr(self, "wheels_out", False):
            return self.arch_top
        for ax in self.axles:
            d = abs(y - ax)
            if d <= self.arch_half + 1e-6:
                return self.arch_zc + math.sqrt(max(0.0, self.arch_r ** 2 - d * d))
        return self.arch_top

    def side_x(self, z):
        WO = self.half_w
        if z <= self.belt:
            tuck = self.spec.get("tuck")                    # (a rounded hull below the belt -- an aerostat's gondola)
            if tuck:
                return WO - tuck * ((self.belt - z) / max(1e-6, self.belt - self.skirt)) ** 1.8
            return WO if z >= self.sill else WO - 0.03 * (self.sill - z) / max(1e-6, self.sill - self.skirt)
        if z <= self.head:
            return WO - self.tumble * (z - self.belt) / max(1e-6, self.head - self.belt)
        return WO - self.tumble - self.cant_in * (z - self.head) / max(1e-6, self.cant - self.head)

    def a_line(self, y):
        """The windscreen's side edge (the A-pillar's line) from the toe to the header."""
        return self.screen_base + (self.toe - y) / (self.toe - self.header) * (self.cant - self.screen_base)

    def c_line(self, y):
        """A trunk rear's C-pillar line: from the roof's edge at c_top down to the deck at c_foot."""
        R = self.rear
        return self.cant + (R["c_top"] - y) / (R["c_top"] - R["c_foot"]) * (R["deck_z"] + 0.02 - self.cant)

    def hood_z(self, y):
        """The fender top over the front: the screen's foot at the cowl, falling to the nose's lip."""
        F = self.front
        top = self.screen_base - 0.02
        if y <= self.toe:
            return top
        t = (y - self.toe) / max(1e-6, self.nose - self.toe)
        return top - F.get("hood_drop", 0.12) * min(1.0, t) - 0.04 * max(0.0, (t - 0.9) / 0.1) ** 2

    def deck_z(self, y):
        R = self.rear
        t = (R["c_foot"] - y) / max(1e-6, R["c_foot"] - self.tail)
        return R["deck_z"] - R.get("deck_drop", 0.05) * t - 0.04 * max(0.0, (t - 0.9) / 0.1) ** 2

    def plan(self, y):
        if self.spec.get("plan") == "round":                # (a round cabin -- the spoke elevator's: a circle in plan,
            h = (self.nose - self.tail) / 2                 #  its ends flattened to round_min for the end faces)
            u = (y - (self.nose + self.tail) / 2) / h
            return max(self.spec.get("round_min", 0.40), math.sqrt(max(0.0, 1.0 - u * u)))
        f0 = self.nose - self.spec.get("nose_round", 0.18)
        r0 = self.tail + self.spec.get("tail_round", 0.16)
        if y > f0:
            return 1.0 - self.spec.get("nose_taper", 0.10) * ((y - f0) / (self.nose - f0)) ** 2
        if y < r0:
            return 1.0 - self.spec.get("tail_taper", 0.06) * ((r0 - y) / (r0 - self.tail)) ** 2
        return 1.0

    def zone(self, y):
        """'hood' (in front of the cowl), 'deck' (behind a trunk's C-pillar foot), else 'green'."""
        if y > self.toe + 1e-9:
            return "hood"
        if self.rear["kind"] == "trunk" and y < self.rear["c_foot"] - 1e-9:
            return "deck"
        return "green"

    def _roof_arc(self, cx, cz, crown_z):
        return [(cx * f, cz + (crown_z - cz) * (1.0 - f * f)) for f in (0.825, 0.5625, 0.275, 0.0)]

    def ext_half(self, y):
        s = self.plan(y)
        az = self.arch_z(y)
        if self.high:
            pts = [(self.side_x(self.skirt), self.skirt), (self.side_x(az), az), (self.side_x(self.sill), self.sill)]
        else:
            pts = [(self.side_x(self.skirt), self.skirt), (self.side_x(self.sill), self.sill), (self.side_x(az), az)]
        E = self.E
        zn = self.zone(y)
        if zn != "green":                                     # a bonnet or a deck: the top is a lid over a tub
            hz = self.hood_z(y) if zn == "hood" else self.deck_z(y)
            bx = self.side_x(self.belt)
            pts.append((bx, hz))
            pts += [(bx - 0.004, hz + 0.001), (bx - 0.008, hz + 0.002), (bx - 0.02, hz + 0.004), (bx - 0.05, hz + 0.008)]
            cx, cz = bx - 0.11, hz + 0.015
            pts.append((cx, cz))
            pts += self._roof_arc(cx, cz, hz + 0.05)
        else:
            pts.append((self.side_x(self.belt), self.belt))
            cz, hz = self.cant, self.head
            if self.header < y <= self.toe:
                cz = self.a_line(y)
            elif self.rear["kind"] == "trunk" and y < self.rear["c_top"]:
                cz = self.c_line(y)
            if cz < self.cant:
                hz = max(self.belt, min(self.head, cz - self.pillar))
            for f in (1.0 / 3, 2.0 / 3):
                z = self.belt + (hz - self.belt) * f
                pts.append((self.side_x(z), z))
            pts.append((self.side_x(hz), hz))
            hx = self.side_x(hz)
            cx = hx - self.cant_in * min(1.0, (cz - hz) / max(1e-6, self.cant - self.head))
            pts.append((hx + (cx - hx) * 0.45, hz + (cz - hz) * 0.72))
            pts.append((cx, cz))
            crown = cz + (self.crown - self.cant)
            pts += self._roof_arc(cx, cz, crown)
        assert len(pts) == NE, (y, len(pts))
        return [(x * s, z) for x, z in pts]

    def ext_loop(self, y):
        h = self.ext_half(y)
        return h + [(-x, z) for x, z in reversed(h[:-1])]

    def in_well(self, y):
        if getattr(self, "wheels_out", False):
            return False
        return any(ax - self.arch_half - 1e-6 <= y <= ax + self.arch_half + 1e-6 for ax in self.axles)

    def hump_z(self):
        return round(max(self.floor, self.arch_top + 0.05), 3)

    def int_half(self, y):
        hump = self.hump_z() if self.in_well(y) else self.floor
        out = [(0.0, self.floor), (self.well_x - 0.03, self.floor), (self.well_x - 0.03, hump),
               (self.side_x(self.sill) - self.int_off - 0.005, hump)]
        eh = self.ext_half(y)
        s = self.plan(y)
        drop = self.crown - self.headliner
        E = self.E
        for k in range(1, NE):
            x, z = eh[k]
            x /= s
            if k <= E["head"]:
                xi, zi = x - self.int_off, z
            elif k == NE - 1:
                xi, zi = 0.0, z - drop
            else:
                xi = max(0.0, x - self.int_off * (1.0 if k <= E["cant"] else 0.5))
                zi = z - drop * (0.6 if k <= E["cant"] else 1.0)
            if k <= E["arch"]:
                zi = max(zi, hump)
            if self.high and k == E["sill"]:                  # (a cab-over cab's lining meets its floor's edge: no slot under the sill)
                zi = hump
            out.append((xi * s, zi))
        return out

    def int_loop(self, y):
        h = self.int_half(y)
        loop = h + [(-x, z) for x, z in reversed(h[1:-1])]
        assert len(loop) == NI
        return loop

    @staticmethod
    def ext_s(k, side):
        return k if side == "R" else 2 * (NE - 1) - k

    @staticmethod
    def int_s(k, side):
        return k + 3 if side == "R" else NI - (k + 3)

    # ------------------------------------------------------------ stations (every edge; descending y)
    def _stations(self):
        ys = {self.nose, self.nose - 0.02, self.nose - 0.06, self.nose - self.spec.get("nose_round", 0.18),
              self.toe, self.header, self.tail_in, self.tail, self.tail + 0.06, self.tail + self.spec.get("tail_round", 0.16)}
        if self.lid:
            ys |= set(self.lid)
        R = self.rear
        if R["kind"] == "trunk":
            ys |= {R["c_top"], R["c_foot"]} | set(R["lid"])
        for d in self.doors:
            ys |= {d["y0"], d["y1"]}
        for w in self.windows:
            ys |= {w["y0"], w["y1"]}
        for ax in ([] if self.wheels_out else self.axles):
            if self.nose > ax > self.tail:
                ys |= {ax + self.arch_half * f for f in _ARC} | {ax + self.arch_half, ax - self.arch_half}
                for e in (ax + self.arch_half + 0.001, ax - self.arch_half - 0.001):     # (the hump's upright end walls)
                    if self.toe > e > self.cab_end:
                        ys.add(e)
        bl = self.board["length_m"] / 2 - 0.04              # (the underpan's risers at the board's ends: the end pans reach them)
        ys |= {min(self.nose, bl), max(self.tail, -bl)}
        for y in self.spec.get("extra_stations", []):
            ys.add(y)
        if self.spec.get("plan") == "round":
            h = (self.nose - self.tail) / 2
            ys |= {round((self.nose + self.tail) / 2 + h * math.sin(math.pi / 2 * k / 12), 4) for k in range(-12, 13)}
        ys = sorted({round(v, 4) for v in ys if self.tail - 1e-6 <= v <= self.nose + 1e-6}, reverse=True)
        self.stations = ys
        self.int_stations = [y for y in ys if self.cab_end <= y <= self.toe]

    # ------------------------------------------------------------ the frame
    def frame_rings(self):
        """Rings at the slot edges, set into the pillars and posts (never on a jamb: a jamb step on a sloping
        pillar lifts its joints out into the glass), in the end cavities, and no more than 0.9 m apart."""
        # (the header's two: one in the A-pillar, one just behind it, so the cant rail runs level over the doors)
        want = [self.nose - 0.03, self.toe + 0.025, self.header + 0.03, self.header - 0.02, self.tail_in - 0.03, self.tail + 0.03]
        if self.lid:
            want.append(self.lid[0] - 0.03)
        for ax in ([] if self.wheels_out else self.axles):
            want += [ax + self.arch_half + 0.02, ax - self.arch_half - 0.02]
        for d in self.doors:
            want += [d["y0"] + 0.035, d["y1"] - 0.035]
        R = self.rear
        if R["kind"] == "trunk":
            # (likewise at the C-pillar's top; one more down it, so its tube follows the narrow sloping strip)
            want += [R["c_top"] + 0.02, R["c_top"] - 0.03, R["c_foot"] + 0.025, R["c_foot"] - 0.03]
            y = R["c_top"] - 0.23
            while y > R["c_foot"] + 0.12:
                want.append(y)
                y -= 0.2
        want = sorted({round(v, 3) for v in want if self.tail < v < self.nose}, reverse=True)
        out = []
        for v in want:                                  # (merge near twins)
            if out and out[-1] - v < 0.04:
                continue
            out.append(v)
        filled = [out[0]]
        for v in out[1:]:
            gap = filled[-1] - v
            n = int(math.ceil(gap / 0.9))
            for k in range(1, n):
                filled.append(round(filled[-1] - gap / n, 3) if k == 1 else round(filled[-1] - gap / n, 3))
            filled.append(v)
        # (the fill must not land on a door's jamb or inside a window's band edge)
        res = []
        for v in filled:
            for d in self.doors:
                if abs(v - d["y0"]) < 0.03 or abs(v - d["y1"]) < 0.03:
                    v = d["y0"] + 0.035 if abs(v - d["y0"]) < 0.03 else d["y1"] - 0.035
            if not res or abs(res[-1] - v) >= 0.04:
                res.append(round(v, 3))
        return res

    def ring_at(self, y):
        e = self.ext_half(y)
        has_in = self.cab_end - (0.0 if self.rear["kind"] == "trunk" else 0.05) <= y <= self.toe   # (a trunk is outside)
        i = self.int_half(min(self.toe, max(self.cab_end, y))) if has_in else None
        R = self.rear
        E = self.E
        in_a = self.header < y <= self.toe
        in_c = R["kind"] == "trunk" and R["c_foot"] + 0.05 <= y < R["c_top"]
        c_foot = R["kind"] == "trunk" and R["c_foot"] <= y < R["c_foot"] + 0.05      # (the C-pillar's foot: under the deck edge)

        def pillar():
            (hx, hz), (cx, cz) = e[E["head"]], e[E["cant"]]
            dx, dz = cx - hx, cz - hz
            L = math.hypot(dx, dz) or 1.0
            nx, nz = -abs(dz) / L, -abs(dx) / L
            ins = self.spec.get("pillar_inset", 0.018)   # (deeper on a steep screen: the band slopes across the tube)
            return [round((hx + cx) / 2 + nx * ins, 4), round((hz + cz) / 2 + nz * ins, 4)]

        def mid(k):
            xe, ze = e[k]
            if k in (E["head"], E["cant"]) and (in_a or in_c):
                return pillar()
            if k in (E["head"], E["cant"]) and (self.toe < y < self.toe + 0.05 or c_foot):
                return [round(e[E["belt"]][0] - 0.03, 4), round(self.belt - 0.06, 4)]   # (clear of the pillar's lining too)
            if i is None and k > E["belt"]:
                if k <= E["cant"]:
                    return [round(e[E["belt"]][0] - 0.05, 4), round(e[E["belt"]][1] - 0.02, 4)]
                return [round(xe, 4), round(ze - 0.04, 4)]
            if k == E["skirt"]:
                if xe - 0.035 <= self.mount_x:                  # (a body narrower than its board -- a tractor's -- hangs its
                    return [round(xe - 0.035, 4), round(max(ze + 0.035, self.deck + 0.02), 4)]   # skirt past the deck: its
                return [round(xe - 0.035, 4), round(ze + 0.035, 4)]                              # frame's foot stays on it)
            if self.high and k == E["sill"]:                     # (the cab's floor edge: in the floor slab)
                return [round(xe - 0.035, 4), round(self.floor - 0.025, 4)]
            if i is None and k == E["belt"]:
                return [round(xe - 0.035, 4), round(ze - 0.03, 4)]
            if i is None or k < E["belt"]:
                nx, nz = (0.035, 0.0) if k <= E["head"] else (0.03, 0.03)
                return [round(max(0.0, xe - nx) if xe > 0 else 0.0, 4), round(ze - nz, 4)]
            xi, zi = i[k + 3]
            return [round((xe + xi) / 2, 4), round((ze + zi) / 2, 4)]
        b, h = mid(E["belt"]), mid(E["head"])
        if i is not None and not (in_a or in_c or c_foot):
            b[1] = round(self.belt - 0.025, 4)
            h[1] = round(self.head + 0.025, 4)
        elif in_c or c_foot:
            b[1] = round(self.belt - 0.025, 4)
        sl = mid(E["sill"])
        if not self.in_well(y):
            sl[1] = round(self.floor - 0.025, 4)
            if self.spec.get("tuck"):                       # (a tucked hull is narrower down there: keep the joint inside it)
                sl[0] = round(min(sl[0], self.side_x(sl[1]) * self.plan(y) - 0.04), 4)
        pts = {"skirt": mid(E["skirt"]), "sill": sl, "belt": b, "head": h,
               "cant": mid(E["cant"]), "roof": mid(E["roof"]), "crown": mid(E["crown"])}
        # (a side joint at least 2.2 cm inside the skin -- a tube's radius and a little -- where the ends taper)
        for base in ("skirt", "sill", "belt", "head"):
            xe = e[E[base]][0]
            pts[base] = [round(min(pts[base][0], xe - 0.022), 4), pts[base][1]]
        out = []
        for nm in RING_NAMES:
            if nm == "floor_C":
                fz = self.deck + 0.015 if self.skirt < self.deck + 0.1 else self.skirt + 0.035   # (a body standing high over its
                out.append([nm, 0.0, round(fz, 4)])                                                # deck -- a rail cab's: over its belly)
                continue
            base, _, side = nm.partition("_")
            x, z = pts[base]
            out.append([nm, -x if side == "L" else x, z])
        return out

    # ------------------------------------------------------------ the standard (written for the game)
    def standard(self):
        S = self.spec
        R = self.rear
        rings = [{"y": y, "joints": self.ring_at(y)} for y in self.frame_rings()]
        rings += S.get("cargo_rings", [])
        rings.sort(key=lambda r: -r["y"])
        tops = [[self.header, self.toe, "screen"]]
        if self.lid:
            tops.append([self.lid[1], self.lid[0], "lid"])
        if R["kind"] == "trunk":
            tops.append([R["c_foot"], R["c_top"], "backlight"])
            tops.append([R["lid"][1], R["lid"][0], "trunk"])
        tops += S.get("cargo_tops", [])
        slots = {"door_" + d["id"]: [d["y0"], d["y1"]] for d in self.doors}
        slots.update({"window_" + w["id"]: [w["y0"], w["y1"]] for w in self.windows})
        heavy = S.get("heavy", False)
        return {
            "id": self.id, "class": S["cls"], "about": S.get("about", ""), "board": S["board"],
            "outer_half_width": self.half_w, "inner_half_width": self.half_w - self.int_off,
            "deck": self.deck, "floor": self.floor, "ceiling": self.headliner, "skirt": self.skirt, "sill": self.sill,
            "belt": self.belt, "window": [self.belt, self.head], "cant": self.cant, "crown": self.crown,
            "arch_top": self.arch_top, "door": {"head": self.head, "apertures": {d["id"]: [d["y0"], d["y1"]] for d in self.doors}},
            "axles": list(self.axles), "arch_half": self.arch_half, "arch_r": self.arch_r, "arch_zc": self.arch_zc,
            "no_arch": self.wheels_out,                       # (wheels outside the body: it has no arches)
            "nose": self.nose, "tail": self.tail, "toe": self.toe, "header": self.header,
            "front": self.front, "rear": self.rear, "stations": self.stations,
            "ring": self.ring_at(min(self.toe, max(self.cab_end, (self.toe + self.cab_end) / 2))),
            "rings": rings, "end_inset": 0.0, "top_openings": tops,
            "tubes": {"main_d": 0.034 if heavy else 0.028, "brace_d": 0.026 if heavy else 0.022, "material": "frame_tube",
                      "exposed_inside": [], "exposed_outside": []},
            "bolted": ["sill_R", "sill_L", "floor_C"], "stringers": RING_NAMES, "slots": slots,
            "frame": ({"yield_strain": 0.012, "plastic": 0.85, "dent_stiffness": 160000.0, "min_energy": 4000.0, "max_dent": 0.40}
                      if heavy else
                      {"yield_strain": 0.012, "plastic": 0.85, "dent_stiffness": 90000.0, "min_energy": 2500.0, "max_dent": 0.35}),
            "detach_count": 3, "detach_share": 0.3, "pair_min": 0.25,
            # (the car calibration of SW180: panels crumple with the soft frame and stay on; glass and lamps break)
            "tolerance": {"glazing": 0.012, "door_glass": 0.012, "hatch_glass": 0.012, "door_leaf": 0.06, "hatch": 0.06,
                          "frunk_lid": 0.06, "trunk_lid": 0.06, "side_bay": 0.16, "roof_bay": 0.06, "end_cap": 0.16,
                          "trim": 0.20, "lining_bay": 0.08, "ceiling_bay": 0.08, "end_lining": 0.08, "floor": 1.0,
                          "wheel_well": 0.15, "underpan": 0.12, "reveal": 0.08, "seat": 0.15, "fittings": 0.10, "dash": 0.10,
                          "lamp": 0.02, "frunk_tub": 0.35, "cargo_wall": 0.12, "cargo_lining": 0.12, "cargo_floor": 1.0,
                          "equipment": 0.25, "leaf_trim": 0.06},
        }


class TrailerLoft(Loft):
    """A trailer: no cab, only a cargo module on unpowered running gear (the Harrow trailer boards). It stands in for
    the loft wherever the builder's cargo, lamps and equipment ask for the board's numbers."""

    def __init__(self, spec):
        self.spec = S = spec
        self.id = S["id"]
        self.high = False
        self.E = E
        B = self.board = board(S["board"])
        self.deck = B.get("deck_top_m", 0.50)                # (a micro board has its own, lower deck)
        self.mount_x = B["mount_x_m"]
        self.wheel_r = B["wheel_r"]
        self.axles = [a["y"] for a in B["axles"]]
        self.track = B["track_m"]
        self.tyre_w = tyre_w(B)
        self.well_x = max(0.08, self.track / 2 - self.wheel_r * 0.4 - 0.16)
        if str(S["board"]).startswith("solana_m"):          # (a micro board's little wheels: a car's 21 cm of travel over them
            self.arch_half = round(self.wheel_r + 0.06, 3)  #  put the arch above a kart's or a chair's whole body)
            self.arch_r = round(self.wheel_r + 0.08, 3)
            self.arch_top = round(self.wheel_r * 2 + 0.08, 3)
        else:
            self.arch_half = round(self.wheel_r + 0.10, 3)
            self.arch_r = round(self.wheel_r + 0.18, 3)
            self.arch_top = round(self.wheel_r * 2 + 0.21, 3)
        self.arch_zc = self.arch_top - self.arch_r
        C = S["cargo"]
        self.half_w = C["half_w"]
        self.skirt = C.get("skirt", 0.36)
        self.floor = C["floor_z"]
        self.nose = C["y0"]
        self.tail = C["y1"]
        self.crown = C.get("top_z") or C.get("rail_z") or (C.get("tank_z", 1.0) + C.get("tank_r", 0.5))
        self.no_cab = True
        self.doors, self.windows = [], []
        self.stations, self.int_stations = [], []
        self.front = {"kind": "none"}
        self.rear = {"kind": "none"}
        self.toe = self.header = self.nose
        self.tail_in = self.cab_end = self.tail

    def arch_z(self, y):
        for ax in self.axles:
            d = abs(y - ax)
            if d <= self.arch_half + 1e-6:
                return self.arch_zc + math.sqrt(max(0.0, self.arch_r ** 2 - d * d))
        return self.arch_top

    def standard(self):
        S = self.spec
        return {"id": self.id, "class": S["cls"], "about": S.get("about", ""), "board": S["board"], "trailer": True,
                "outer_half_width": self.half_w, "inner_half_width": self.half_w - 0.06, "deck": self.deck, "floor": self.floor,
                "skirt": self.skirt, "sill": self.floor, "belt": self.floor, "window": [self.floor, self.crown], "cant": self.crown,
                "crown": self.crown, "arch_top": self.arch_top, "door": {"head": self.crown, "apertures": {}}, "axles": list(self.axles),
                "arch_half": self.arch_half, "arch_r": self.arch_r, "arch_zc": self.arch_zc, "nose": self.nose, "tail": self.tail,
                "toe": self.nose, "header": self.nose, "front": self.front, "rear": self.rear, "stations": [], "ring": [], "rings": [],
                "end_inset": 0.0, "top_openings": [], "slots": {}, "no_arch": bool(S["cargo"].get("no_arch")),
                "frame_shown": bool(S.get("open")) or S["cargo"]["kind"] in ("bed", "dump", "deck"),   # (an open tub's frame shows by design: the user, 2026-10-02)
                "tubes": {"main_d": 0.030, "brace_d": 0.024, "material": "frame_tube", "exposed_inside": [], "exposed_outside": []},
                "bolted": ["sill_R", "sill_L", "floor_C"], "stringers": RING_NAMES,
                "frame": {"yield_strain": 0.012, "plastic": 0.85, "dent_stiffness": 120000.0, "min_energy": 3000.0, "max_dent": 0.35},
                "detach_count": 3, "detach_share": 0.3, "pair_min": 0.25,
                "tolerance": {"cargo_wall": 0.12, "cargo_lining": 0.12, "cargo_floor": 1.0, "equipment": 0.25, "lamp": 0.02, "trim": 0.20,
                              "hatch": 0.06, "hatch_glass": 0.012, "glazing": 0.012, "door_leaf": 0.06, "leaf_trim": 0.06}}
