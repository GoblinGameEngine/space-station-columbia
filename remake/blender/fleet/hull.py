"""
hull.py -- the fleet's boats: a hull loft (a V hull's section at each station: keel, garboard, chine, topside,
sheer, then the deck's camber to the centreline), its liner inside (the frames -- ribs -- in the cavity between),
the deck with a cockpit opening, the transom, a rubbing strake; a wheelhouse and the boat's working gear as tokens.
research/vehicles/FLEET_BODIES.md. Coordinates: Blender (y forward, z up); z = 0 the waterline, y = 0 midships.
"""
import math

NH = 8                     # points per half section: keel, garboard, chine, topside, sheer, deck edge, deck mid, crown


class Hull:
    def __init__(self, S):
        self.S = S
        self.L = S["length"]
        self.bow, self.stern = self.L / 2, -self.L / 2
        self.beam = S["beam"] / 2
        self.draft = S["draft"]                 # keel below the waterline
        self.free = S["freeboard"]              # sheer above the waterline (midships)
        self.dead = math.radians(S.get("deadrise", 14))
        self.square = S.get("square_bow", False)
        self.double = S.get("double_ender", False)
        self.t = min(0.12, max(0.04, 0.008 * self.L))   # (the frames' depth, hull to liner: deeper as boats grow -- a ferry's
                                                        #  straight frames between curved stations brushed a 4 cm cavity's skin)
        n = S.get("stations", 14)
        self.ys = [self.stern + (self.bow - self.stern) * k / n for k in range(n + 1)]
        self.ys = sorted(set([round(y, 4) for y in self.ys] + [round(v, 4) for v in S.get("extra", [])]), reverse=True)

    def half_beam(self, y):
        t = (y - self.stern) / (self.bow - self.stern)
        if self.square:
            f = 1.0 if t < 0.92 else 1.0 - 0.25 * ((t - 0.92) / 0.08)
            return self.beam * f
        if t > 0.55:
            f = math.sqrt(max(0.0, 1.0 - ((t - 0.55) / 0.45) ** 2))
        elif self.double and t < 0.45:
            f = math.sqrt(max(0.0, 1.0 - ((0.45 - t) / 0.45) ** 2))
        else:
            f = 1.0 if t > 0.15 else 0.86 + 0.14 * t / 0.15
        return max(0.01, self.beam * f)

    def keel_z(self, y):
        t = (y - self.stern) / (self.bow - self.stern)
        z = -self.draft
        if t > 0.6 and not self.square:
            z += (self.draft + self.free * 0.6) * ((t - 0.6) / 0.4) ** 2
        if self.double and t < 0.4:
            z += (self.draft + self.free * 0.5) * ((0.4 - t) / 0.4) ** 2
        if self.square and t > 0.92:
            z += (self.draft + 0.2) * ((t - 0.92) / 0.08)
        return z

    def sheer_z(self, y):
        t = (y - self.stern) / (self.bow - self.stern)
        return self.free + self.S.get("sheer_spring", 0.25) * (t - 0.4) ** 2 / 0.36 * (1 if t > 0.4 else 0.3)

    def half(self, y):
        """[(x, z)] * NH at station y (the right half, the keel first)."""
        b = self.half_beam(y)
        zk, zs = self.keel_z(y), self.sheer_z(y)
        zc = min(zs - 0.05, zk + b * math.tan(self.dead) + 0.02)        # the chine
        cam = self.S.get("camber", 0.06)
        # (a true V: the bottom straight from keel to chine, so the floor brace between them stays in the hull's cavity --
        #  with the garboard below that line, the brace rose through the liner into the open hull)
        pts = [(0.0, zk), (b * 0.30, zk + (zc - zk) * 0.30 / 0.92), (b * 0.92, zc), (b * 0.99, (zc + zs) / 2), (b, zs),
               (b * 0.82, zs + cam * 0.35), (b * 0.42, zs + cam * 0.85), (0.0, zs + cam)]
        return pts

    def loop(self, y):
        h = self.half(y)
        return h + [(-x, z) for x, z in reversed(h[1:-1])]            # the keel .. sheer R .. crown .. sheer L .. (closed: 14)

    def inner(self, y):
        """The liner: the hull drawn in by its thickness (the frames' cavity between)."""
        out = []
        for k, (x, z) in enumerate(self.half(y)):
            if k <= 4:
                out.append((max(0.0, x - self.t), z + (self.t if k <= 2 else 0.0)))
            else:
                out.append((max(0.0, x - self.t * (1 if k == 5 else 0.5)), z - self.t))
        return out

    def drawn(self, f, y):
        """f (half or inner) as the hull is drawn at y: straight between its stations (the smooth curve itself bulges
        past those flats toward the ends, and a frame on it stood out through them)."""
        ys = self.ys
        for a, b in zip(ys, ys[1:]):
            if b - 1e-9 <= y <= a + 1e-9:
                t = (a - y) / ((a - b) or 1.0)
                return [(pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t) for pa, pb in zip(f(a), f(b))]
        return f(y)

    def rings(self):
        """Frames: one every 0.6 m, each joint in the cavity between the hull and its liner (as drawn)."""
        out = []
        n = max(2, int(self.L / 0.6))
        for k in range(1, n):
            y = self.stern + self.L * k / n
            o, i = self.drawn(self.half, y), self.drawn(self.inner, y)
            mid = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(o, i)]
            J = {"floor": (0.0, mid[0][1]), "skirt": mid[1], "sill": mid[2], "belt": mid[3], "head": mid[4], "cant": mid[5], "roof": mid[6], "crown": (0.0, mid[7][1])}
            ck = self.S.get("cockpit")
            if ck and ck[1] <= y <= ck[0]:              # (in the cockpit there's no deck: the deck's joints go into the side deck)
                J["cant"] = J["roof"] = ((mid[4][0] + mid[5][0]) / 2, (mid[4][1] + mid[5][1]) / 2)
            joints = []
            for nm in ["skirt_R", "sill_R", "belt_R", "head_R", "cant_R", "roof_R", "crown", "roof_L", "cant_L", "head_L", "belt_L", "sill_L", "skirt_L", "floor_C"]:
                base, _, side = nm.partition("_")
                x, z = J[base]
                joints.append([nm, round(-x if side == "L" else x, 4), round(z, 4)])
            out.append({"y": round(y, 4), "joints": joints})
        return out


BOATS = {
    # length, beam, draft, freeboard, deadrise; cockpit (y0, y1) or None; wheelhouse (y0, y1, half w, height) or None; colours; gear
    "rowboat_dinghy": dict(length=3.5, beam=1.4, draft=0.15, freeboard=0.45, deadrise=10, cockpit=(1.2, -1.55), colours=((236, 234, 228), (40, 92, 150)), gear=["oars", "thwarts"]),
    "canoe_kayak": dict(length=4.8, beam=0.9, draft=0.12, freeboard=0.30, deadrise=8, double_ender=True, cockpit=(1.6, -1.6), colours=((190, 40, 30), (190, 40, 30)), gear=["paddles", "thwarts"]),
    "fishing_skiff": dict(length=5.0, beam=1.9, draft=0.25, freeboard=0.55, deadrise=12, cockpit=(1.4, -2.3), colours=((236, 234, 228), (60, 120, 60)), gear=["outboard", "console", "thwarts"]),
    "pedal_boat": dict(length=2.5, beam=1.5, draft=0.15, freeboard=0.40, deadrise=6, square_bow=True, cockpit=(0.6, -0.9), colours=((236, 234, 228), (236, 186, 30)), gear=["paddlewheel", "thwarts", "canopy_boat"]),
    "personal_watercraft": dict(length=3.3, beam=1.2, draft=0.20, freeboard=0.40, deadrise=18, cockpit=None, colours=((236, 234, 228), (40, 110, 200)), gear=["saddle_boat", "handlebar_boat"]),
    "rescue_board": dict(length=3.2, beam=0.7, draft=0.05, freeboard=0.10, deadrise=4, cockpit=None, colours=((236, 186, 30), (200, 30, 30)), gear=[]),
    "sailboat": dict(length=9.0, beam=3.0, draft=0.6, freeboard=1.0, deadrise=16, cockpit=(-2.0, -4.0), wheelhouse=(1.2, -1.9, 0.95, 0.55), colours=((236, 234, 228), (30, 60, 110)), gear=["mast_sails"]),
    "pontoon_boat": dict(length=7.5, beam=2.6, draft=0.35, freeboard=0.60, deadrise=4, square_bow=True, cockpit=(3.2, -3.4), colours=((210, 212, 216), (40, 110, 90)), gear=["pontoons", "fence", "bimini", "outboard"]),
    "cabin_cruiser": dict(length=12.0, beam=4.0, draft=0.9, freeboard=1.4, deadrise=18, cockpit=(-2.5, -5.6), wheelhouse=(3.0, -2.4, 1.5, 1.7), colours=((236, 234, 228), (40, 42, 46)), gear=["rail"]),
    "lobster_boat": dict(length=11.0, beam=3.8, draft=1.0, freeboard=1.3, deadrise=14, cockpit=(-0.5, -5.2), wheelhouse=(2.8, -0.4, 1.4, 1.9), colours=((236, 234, 228), (40, 92, 150)), gear=["pot_hauler", "traps"]),
    "coast_guard_boat": dict(length=10.0, beam=3.2, draft=0.8, freeboard=1.3, deadrise=20, cockpit=(-1.5, -4.6), wheelhouse=(2.4, -1.4, 1.3, 1.9), colours=((236, 234, 228), (200, 60, 30)), gear=["rail", "lightbar_boat"]),
    "workboat_tug": dict(length=15.0, beam=5.0, draft=1.6, freeboard=1.5, deadrise=12, cockpit=(-3.0, -7.2), wheelhouse=(3.5, -2.5, 1.9, 2.6), colours=((40, 42, 46), (190, 40, 30)), gear=["tug_fenders", "towing_bitt"]),
    "trawler": dict(length=20.0, beam=6.0, draft=2.4, freeboard=2.2, deadrise=16, cockpit=(-3.0, -9.6), wheelhouse=(6.0, -2.8, 2.4, 3.0), colours=((30, 60, 110), (190, 40, 30)), gear=["gallows", "net_drum"]),
    "ferry": dict(length=45.0, beam=12.0, draft=2.4, freeboard=2.4, deadrise=6, square_bow=True, double_ender=True, cockpit=(18.0, -18.0), wheelhouse=(4.0, -4.0, 3.5, 3.0), colours=((236, 234, 228), (40, 92, 150)), gear=["ferry_ramps", "rail"], stations=24),
    "barge": dict(length=40.0, beam=11.0, draft=2.2, freeboard=1.2, deadrise=2, square_bow=True, cockpit=(17.5, -17.5), colours=((90, 70, 50), (40, 42, 46)), gear=[], stations=20),
}
