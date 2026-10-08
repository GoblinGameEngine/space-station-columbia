"""
shopfit.py -- interior fit-outs for commercial rooms, one recipe per business type (the `type`
words of CATALOG_SPEC.md's store vocabulary).

A recipe is called from gbhouse.House.furnish through a room's `fitout` hook:
    recipe(ctx)   ctx = Fit(house, room, part, against, rect, fz, cz, rnd)
Wall pieces go through `against` (keeps door swings, windows for tall pieces, headroom); free-standing
islands through Fit.island (kept off door swings and stair landings).  The street is at +y (the
room's N wall), so tall wall pieces avoid it.
"""
import math

import gbfurn as fu
import gbhouse as gh

GOODS = ["goods0", "goods1", "goods2", "goods3", "goods4", "goods5", "goods6"]


def shop_materials(pal):
    """Colours for stock on shelves + fixture finishes used by the recipes."""
    for i, c in enumerate(((0.62, 0.18, 0.12), (0.15, 0.3, 0.55), (0.85, 0.72, 0.3), (0.2, 0.45, 0.25), (0.9, 0.88, 0.8),
                           (0.55, 0.35, 0.2), (0.7, 0.72, 0.74))):
        pal.solid(f"goods{i}", c, rough=0.6)
    pal.solid("formica", (0.82, 0.8, 0.74), rough=0.35)
    pal.solid("felt", (0.08, 0.35, 0.16), rough=0.95)
    pal.solid("leather", (0.35, 0.12, 0.08), rough=0.55)
    pal.solid("chrome_s", (0.8, 0.82, 0.85), rough=0.15, metal=1.0)
    pal.solid("screen", (0.92, 0.92, 0.9), rough=0.8)
    pal.solid("cooler_body", (0.9, 0.9, 0.88), rough=0.3)
    pal.solid("black", (0.04, 0.04, 0.04), rough=0.5)
    pal.solid("screen_lit", (0.3, 0.6, 0.9), rough=0.2, emission=(0.3, 0.6, 0.9))


class Fit:
    def __init__(self, house, room, p, against, rect, fz, cz, rnd):
        self.h, self.r, self.p, self.against, self.rect, self.fz, self.cz, self.rnd = house, room, p, against, rect, fz, cz, rnd
        self.fl = room.get("floor", 0)

    def far(self):
        """(y of the wall opposite the room's entrance, +1/-1 pointing from it into the room).
        Rooms record their entry side ('S' = the -y wall, default; 'N' = the +y wall)."""
        x0, y0, x1, y1 = self.rect
        return (y1, -1.0) if self.r.get("entry", "S") == "S" else (y0, 1.0)

    @property
    def w(self):
        return self.rect[2] - self.rect[0]

    @property
    def d(self):
        return self.rect[3] - self.rect[1]

    def island(self, cx, cy, hw, hd, fn):
        """Free-standing piece centred near (cx, cy); nudged off door swings; skipped if it can't fit."""
        c = self.h._clear_centre(cx, cy, hw, hd, self.fl, self.rect)
        if c:
            fn((c[0], c[1], self.fz))
            self.h.swing_zones.append((c[0] - hw - 0.45, c[1] - hd - 0.45, c[0] + hw + 0.45, c[1] + hd + 0.45, self.fl))
        return c

    def wall(self, w, d, tall, fn, prefer=None):
        return self.against(w, d, tall, fn, prefer=prefer)

    def aisle_rows(self, n_max, piece_w, piece_d, fn, y_from=0.25, y_to=0.75):
        """Parallel island rows across the room between fractions y_from..y_to of its depth."""
        x0, y0, x1, y1 = self.rect
        rows = max(1, min(n_max, int((y_to - y_from) * self.d / (piece_d + 1.3))))
        for k in range(rows):
            cy = y0 + self.d * (y_from + (y_to - y_from) * (k + 0.5) / rows)
            self.island((x0 + x1) / 2, cy, piece_w / 2, piece_d / 2, lambda pos: fn(pos))


# ------------------------------------------------------------------ fixture pieces
def cooler(p, pos, yaw, w, body="cooler_body", glass="glass", goods=GOODS, seed=0):
    """Upright glass-door drinks/dairy cooler (front = local -Y)."""
    f = fu.F(pos, yaw)
    p.obox(f, (-w / 2, -0.35, 0), (w / 2, 0.35, 2.0), body)
    p.obox(f, (-w / 2 + 0.05, -0.36, 0.15), (w / 2 - 0.05, -0.34, 1.85), glass)
    import random
    r = random.Random(seed)
    for k in range(4):
        z = 0.25 + k * 0.42
        x = -w / 2 + 0.1
        while x < w / 2 - 0.15:
            ww = r.uniform(0.08, 0.14)
            p.obox(f, (x, -0.25, z), (x + ww, 0.2, z + r.uniform(0.18, 0.3)), goods[r.randrange(len(goods))])
            x += ww + 0.02


def gondola(p, pos, yaw, length, h, goods=GOODS, seed=0, mat="furniture"):
    """Double-sided island shelving (both long faces stocked)."""
    fu.stocked_shelves(p, (pos[0] + math.cos(math.radians(yaw + 90)) * 0.22, pos[1] + math.sin(math.radians(yaw + 90)) * 0.22, pos[2]),
                       yaw + 180, length, 0.42, h, 4, mat, goods, seed=seed)
    fu.stocked_shelves(p, (pos[0] - math.cos(math.radians(yaw + 90)) * 0.22, pos[1] - math.sin(math.radians(yaw + 90)) * 0.22, pos[2]),
                       yaw, length, 0.42, h, 4, mat, goods, seed=seed + 1)


def clothes_rack(p, pos, yaw, length, mat="chrome_s", cloth=GOODS, seed=0):
    f = fu.F(pos, yaw)
    for x in (-length / 2, length / 2):
        p.obox(f, (x - 0.02, -0.02, 0), (x + 0.02, 0.02, 1.4), mat)
    p.obox(f, (-length / 2, -0.015, 1.35), (length / 2, 0.015, 1.39), mat)
    import random
    r = random.Random(seed)
    x = -length / 2 + 0.06
    while x < length / 2 - 0.06:
        p.obox(f, (x, -0.25, 0.55), (x + 0.03, 0.25, 1.33), cloth[r.randrange(len(cloth))])
        x += 0.06


def barber_chair(p, pos, yaw, mat="leather", metal="chrome_s"):
    f = fu.F(pos, yaw)
    p.cylinder((pos[0], pos[1]), 0.25, pos[2], pos[2] + 0.08, metal, n=12)
    p.cylinder((pos[0], pos[1]), 0.07, pos[2] + 0.08, pos[2] + 0.45, metal, n=8)
    p.obox(f, (-0.28, -0.3, 0.45), (0.28, 0.25, 0.6), mat)
    p.obox(f, (-0.28, 0.2, 0.6), (0.28, 0.3, 1.25), mat)
    p.obox(f, (-0.32, -0.3, 0.6), (-0.26, 0.2, 0.8), metal)
    p.obox(f, (0.26, -0.3, 0.6), (0.32, 0.2, 0.8), metal)
    p.obox(f, (-0.2, -0.65, 0.15), (0.2, -0.3, 0.2), metal)


def mirror_station(p, pos, yaw, w, mat="formica", mirror="mirror"):
    f = fu.F(pos, yaw)
    p.obox(f, (-w / 2, -0.25, 0.75), (w / 2, 0.05, 0.85), mat)
    p.obox(f, (-w / 2, -0.05, 0.0), (w / 2, 0.05, 0.75), mat)
    p.obox(f, (-w / 2 + 0.05, 0.02, 1.0), (w / 2 - 0.05, 0.05, 1.9), mirror)


def booth(p, pos, yaw, mat="vinyl_red", table_mat="formica", frame="chrome_s"):
    """Diner booth: two benches facing across a table (table axis along local x)."""
    f = fu.F(pos, yaw)
    for s in (-1, 1):
        y0 = s * 0.55
        p.obox(f, (-0.6, min(y0, y0 + s * 0.5), 0), (0.6, max(y0, y0 + s * 0.5), 0.45), mat)
        yb = s * 1.0
        p.obox(f, (-0.6, min(yb, yb + s * 0.1), 0), (0.6, max(yb, yb + s * 0.1), 1.1), mat)
    p.obox(f, (-0.55, -0.4, 0.72), (0.55, 0.4, 0.76), table_mat)
    p.obox(f, (-0.05, -0.05, 0), (0.05, 0.05, 0.72), frame)


def pool_table(p, pos, yaw, felt="felt", wood="furn_dark"):
    f = fu.F(pos, yaw)
    for x in (-1.1, 1.1):
        for y in (-0.55, 0.55):
            p.obox(f, (x - 0.07, y - 0.07, 0), (x + 0.07, y + 0.07, 0.65), wood)
    p.obox(f, (-1.3, -0.72, 0.65), (1.3, 0.72, 0.8), wood)
    p.obox(f, (-1.15, -0.57, 0.8), (1.15, 0.57, 0.81), felt)


def teller_counter(p, x0, x1, y, fz, mat="furn_dark", brass="brass", glass="glass"):
    """Bank counter across the room with brass teller grilles; customers on the +y side."""
    p.box((x0, y - 0.35, fz), (x1, y + 0.35, fz + 1.1), mat)
    p.box((x0, y - 0.4, fz + 1.1), (x1, y + 0.4, fz + 1.15), "formica")
    n = max(2, int((x1 - x0) / 1.5))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        p.box((x - 0.03, y + 0.3, fz + 1.15), (x + 0.03, y + 0.36, fz + 2.1), brass)
    p.box((x0, y + 0.3, fz + 2.05), (x1, y + 0.36, fz + 2.1), brass)
    p.box((x0, y + 0.32, fz + 1.5), (x1, y + 0.34, fz + 2.05), glass)


def washer(p, pos, yaw, mat="enamel", door="chrome_s"):
    f = fu.F(pos, yaw)
    p.obox(f, (-0.33, -0.33, 0), (0.33, 0.33, 0.9), mat)
    p.obox(f, (-0.2, -0.34, 0.35), (0.2, -0.33, 0.75), door)
    p.obox(f, (-0.33, 0.22, 0.9), (0.33, 0.33, 1.05), mat)


def car_lift(p, pos, yaw, mat="goods2", metal="steel"):
    f = fu.F(pos, yaw)
    for x in (-1.3, 1.3):
        p.obox(f, (x - 0.15, -0.2, 0), (x + 0.15, 0.2, 3.0), mat)
    for y in (-0.6, 0.6):
        p.obox(f, (-1.25, y - 0.08, 0.1), (1.25, y + 0.08, 0.2), metal)


def office_set(p, pos, yaw, mat="furniture", chair_mat="leather"):
    fu.desk(p, pos, yaw, mat, "brass")
    a = math.radians(yaw)
    fu.chair(p, (pos[0] - math.sin(a) * 0.75, pos[1] + math.cos(a) * 0.75, pos[2]), yaw + 180, chair_mat)


def file_cabinet(p, pos, yaw, mat="steel"):
    f = fu.F(pos, yaw)
    p.obox(f, (-0.23, -0.35, 0), (0.23, 0.35, 1.32), mat)
    for k in range(4):
        p.obox(f, (-0.08, -0.36, 0.2 + k * 0.32), (0.08, -0.35, 0.24 + k * 0.32), "brass")


def exam_table(p, pos, yaw, mat="leather", frame="steel"):
    f = fu.F(pos, yaw)
    p.obox(f, (-0.3, -0.9, 0), (0.3, 0.9, 0.7), frame)
    p.obox(f, (-0.33, -0.95, 0.7), (0.33, 0.95, 0.82), mat)


def pizza_oven(p, pos, yaw, mat="steel"):
    f = fu.F(pos, yaw)
    for k in range(2):
        p.obox(f, (-0.75, -0.45, 0.3 + k * 0.55), (0.75, 0.45, 0.8 + k * 0.55), mat)
        p.obox(f, (-0.5, -0.46, 0.45 + k * 0.55), (0.5, -0.45, 0.65 + k * 0.55), "black")
    for x in (-0.7, 0.7):
        p.obox(f, (x - 0.04, -0.4, 0), (x + 0.04, 0.4, 0.3), mat)


def piano(p, pos, yaw, mat="furn_dark"):
    f = fu.F(pos, yaw)
    p.obox(f, (-0.75, -0.3, 0), (0.75, 0.3, 1.3), mat)
    p.obox(f, (-0.7, -0.55, 0.7), (0.7, -0.3, 0.75), mat)
    p.obox(f, (-0.65, -0.56, 0.75), (0.65, -0.35, 0.77), "enamel")


def press(p, pos, yaw, mat="iron"):
    f = fu.F(pos, yaw)
    p.obox(f, (-0.8, -0.6, 0), (0.8, 0.6, 1.1), mat)
    p.cylinder((pos[0], pos[1]), 0.3, pos[2] + 1.1, pos[2] + 1.6, mat, n=12)


# ------------------------------------------------------------------ recipes
def _register(ctx, side_pref=("E", "W", "S")):
    """Checkout counter + register along a side wall near the front."""
    def put(pos, yaw):
        fu.display_case(ctx.p, pos, yaw, 1.8, "furniture", "glass")
        a = math.radians(yaw)
        fu.cash_register(ctx.p, (pos[0] + math.sin(a) * 0.1, pos[1] - math.cos(a) * 0.1, pos[2] + 0.95), yaw + 180, "brass", "black")
    ctx.wall(1.8, 0.6, False, put, prefer=list(side_pref))


def _wall_stock(ctx, n, w=2.0, prefer=("W", "E", "S"), seed=0):
    for k in range(n):
        ctx.wall(w, 0.45, True, lambda pos, yaw, k=k: fu.stocked_shelves(ctx.p, pos, yaw, w, 0.42, 2.1, 5, "furniture", GOODS,
                                                                         seed=seed + k), prefer=list(prefer))


def grocery(ctx):
    _register(ctx)
    for k in range(2):
        ctx.wall(1.8, 0.7, True, lambda pos, yaw, k=k: cooler(ctx.p, pos, yaw, 1.8, seed=k), prefer=["S", "W", "E"])
    _wall_stock(ctx, 3)
    ctx.aisle_rows(3, min(ctx.w - 3.2, 4.0), 0.9, lambda pos: gondola(ctx.p, pos, 0, min(ctx.w - 3.2, 4.0), 1.6, seed=7))


def variety_store(ctx):
    _register(ctx)
    _wall_stock(ctx, 4, seed=20)
    ctx.aisle_rows(3, min(ctx.w - 3.2, 4.0), 0.9, lambda pos: gondola(ctx.p, pos, 0, min(ctx.w - 3.2, 4.0), 1.5, seed=21))


def hardware(ctx):
    _register(ctx)
    ctx.wall(2.4, 0.5, False, lambda pos, yaw: fu.bin_row(ctx.p, pos, yaw, 6, "furniture", ["steel", "iron", "goods6", "brass"]),
             prefer=["W", "E"])
    _wall_stock(ctx, 3, seed=30)
    ctx.aisle_rows(2, min(ctx.w - 3.2, 3.6), 0.9, lambda pos: gondola(ctx.p, pos, 0, min(ctx.w - 3.2, 3.6), 1.8, seed=31))


def drug_store(ctx):
    # soda fountain along one side, pharmacy counter across the back, shelves between
    ctx.wall(4.0, 0.7, False, lambda pos, yaw: fu.bar_counter(ctx.p, pos, yaw, 4.0, "formica", "formica", "chrome_s", h=1.0),
             prefer=["E", "W"])
    ctx.wall(2.4, 0.6, False, lambda pos, yaw: fu.display_case(ctx.p, pos, yaw, 2.4, "furniture", "glass"), prefer=["S"])
    _wall_stock(ctx, 3, seed=40, prefer=("W", "S", "E"))
    x0, y0, x1, y1 = ctx.rect
    for k in range(4):
        ctx.island(x1 - 1.4, y0 + ctx.d * 0.4 + k * 0.7, 0.2, 0.2, lambda pos: fu.stool(ctx.p, pos, "chrome_s", "vinyl_red"))


def diner(ctx):
    x0, y0, x1, y1 = ctx.rect
    ctx.wall(min(5.0, ctx.d * 0.6), 0.7, False,
             lambda pos, yaw: fu.bar_counter(ctx.p, pos, yaw, min(5.0, ctx.d * 0.6), "formica", "formica", "chrome_s", h=1.0),
             prefer=["E", "W"])
    ctx.wall(2.0, 0.72, False, lambda pos, yaw: fu.range_stove(ctx.p, pos, yaw, "steel", "iron", w=1.2), prefer=["S"])
    ctx.wall(1.2, 0.72, False, lambda pos, yaw: fu.fryer(ctx.p, pos, yaw, "steel", "goods2"), prefer=["S"])
    n = max(1, int((ctx.d - 3.0) / 2.2))
    for k in range(n):
        ctx.island(x0 + 1.25, y0 + 1.8 + k * 2.2, 0.62, 1.05, lambda pos: booth(ctx.p, pos, 0))


def cafe(ctx):
    x0, y0, x1, y1 = ctx.rect
    ctx.wall(3.0, 0.6, False, lambda pos, yaw: fu.display_case(ctx.p, pos, yaw, 3.0, "furniture", "glass"), prefer=["S", "E"])
    ctx.wall(1.2, 0.4, True, lambda pos, yaw: fu.shelves(ctx.p, pos, yaw, 1.2, 0.35, 1.8, 5, "furniture"), prefer=["S", "W"])
    for i, (fx, fy) in enumerate(((0.3, 0.7), (0.7, 0.7), (0.3, 0.45), (0.7, 0.45))):
        ctx.island(x0 + ctx.w * fx, y0 + ctx.d * fy, 0.9, 0.9, lambda pos: _table_set(ctx.p, pos))


def _table_set(p, pos, n=4, mat="furniture"):
    fu.round_table(p, pos, 0.4, 0.75, mat)
    for a in range(n):
        ang = a * 2 * math.pi / n
        fu.chair(p, (pos[0] + 0.65 * math.cos(ang), pos[1] + 0.65 * math.sin(ang), pos[2]), math.degrees(ang) - 90, mat)


def bar(ctx):
    L = min(5.5, ctx.d * 0.6)
    ctx.wall(L, 0.55, True, lambda pos, yaw: fu.back_bar(ctx.p, pos, yaw, L, "furn_dark", "mirror", "bottle"), prefer=["E", "W"])
    x0, y0, x1, y1 = ctx.rect
    cx = x1 - 1.9                      # the bar runs parallel to the back bar, 1.9 m off the wall
    ctx.island(cx, (y0 + y1) / 2, 0.35, L / 2, lambda pos: fu.bar_counter(ctx.p, pos, 90, L, "furn_dark", "furn_dark", "brass"))
    for k in range(int(L / 0.65)):
        ctx.island(cx - 0.75, (y0 + y1) / 2 - L / 2 + 0.35 + k * 0.65, 0.2, 0.2, lambda pos: fu.stool(ctx.p, pos, "iron", "vinyl_red"))
    ctx.island(x0 + 1.6, y0 + ctx.d * 0.3, 1.4, 0.8, lambda pos: pool_table(ctx.p, pos, 0))
    ctx.island(x0 + 1.2, y0 + ctx.d * 0.72, 0.9, 0.9, lambda pos: _table_set(ctx.p, pos))


def pool_hall(ctx):
    x0, y0, x1, y1 = ctx.rect
    rows = max(1, int((ctx.d - 1.5) / 3.2))
    cols = max(1, int((ctx.w - 1.0) / 3.4))
    for i in range(cols):
        for j in range(rows):
            ctx.island(x0 + ctx.w * (i + 0.5) / cols, y0 + 1.6 + j * 3.2, 1.45, 0.8, lambda pos: pool_table(ctx.p, pos, 90 if ctx.w < 4 else 0))
    ctx.wall(1.2, 0.3, True, lambda pos, yaw: fu.shelves(ctx.p, pos, yaw, 1.2, 0.1, 1.6, 2, "furn_dark"), prefer=["W", "E"])


def bank(ctx):
    x0, y0, x1, y1 = ctx.rect
    teller_counter(ctx.p, x0 + 0.1, x1 - 0.1 - 1.0, y0 + ctx.d * 0.45, ctx.fz)
    ctx.wall(1.0, 0.8, True, lambda pos, yaw: fu.safe(ctx.p, pos, yaw, "iron", "brass"), prefer=["S"])
    for k in range(2):
        ctx.island(x0 + ctx.w * (0.3 + 0.4 * k), y0 + ctx.d * 0.2, 0.75, 0.6, lambda pos: office_set(ctx.p, pos, 0))
    ctx.island((x0 + x1) / 2, y0 + ctx.d * 0.75, 0.6, 0.35, lambda pos: fu.table(ctx.p, pos, 0, 1.1, 0.6, 1.05, "furn_dark"))
    ctx.wall(2.0, 0.6, False, lambda pos, yaw: fu.bench(ctx.p, pos, yaw, 2.0, "furn_dark"), prefer=["W", "E"])


def barber(ctx):
    x0, y0, x1, y1 = ctx.rect
    n = max(1, min(3, int((ctx.d - 2.0) / 1.8)))
    for k in range(n):
        ctx.wall(1.3, 0.35, False, lambda pos, yaw: mirror_station(ctx.p, pos, yaw, 1.3), prefer=["E"])
        # (the footrest reaches 0.65 m toward the mirror: the chair's half-size across is that, not its seat's)
        ctx.island(x1 - 1.3, y0 + 1.4 + k * 1.8, 0.7, 0.35, lambda pos: barber_chair(ctx.p, pos, 90))
    ctx.wall(2.4, 0.6, False, lambda pos, yaw: fu.bench(ctx.p, pos, yaw, 2.4, "furniture"), prefer=["W"])
    ctx.wall(0.6, 0.45, False, lambda pos, yaw: fu.coat_rack(ctx.p, (pos[0], pos[1], ctx.fz), "furniture"), prefer=["W", "S"])


def beauty_salon(ctx):
    barber(ctx)
    x0, y0, x1, y1 = ctx.rect
    ctx.island(x0 + 1.2, y0 + 1.2, 0.4, 0.5, lambda pos: _hood_dryer(ctx.p, pos))


def _hood_dryer(p, pos):
    fu.chair(p, pos, 180, "vinyl_red")
    p.cylinder((pos[0], pos[1] + 0.1), 0.03, pos[2], pos[2] + 1.3, "chrome_s", n=6)
    p.cylinder((pos[0], pos[1] + 0.05), 0.25, pos[2] + 1.2, pos[2] + 1.55, "cooler_body", n=12)


def dry_goods(ctx):
    _register(ctx)
    _wall_stock(ctx, 4, seed=50)
    x0, y0, x1, y1 = ctx.rect
    for k in range(2):
        ctx.island((x0 + x1) / 2, y0 + ctx.d * (0.35 + 0.3 * k), 1.0, 0.45, lambda pos: fu.table(ctx.p, pos, 0, 2.0, 0.9, 0.8, "furniture"))


def clothing(ctx):
    _register(ctx)
    x0, y0, x1, y1 = ctx.rect
    for k in range(3):
        ctx.island(x0 + ctx.w * (0.3 + 0.4 * (k % 2)), y0 + ctx.d * (0.3 + 0.2 * k), 0.8, 0.3,
                   lambda pos, k=k: clothes_rack(ctx.p, pos, 0, 1.6, seed=k))
    _wall_stock(ctx, 2, seed=60)
    ctx.wall(0.8, 0.4, True, lambda pos, yaw: fu.dresser(ctx.p, pos, yaw, 0.8, 0.4, 1.8, "furniture", "brass", mirror_mat="mirror"),
             prefer=["S", "W"])


def shoe_store(ctx):
    _register(ctx)
    _wall_stock(ctx, 4, seed=70)
    x0, y0, x1, y1 = ctx.rect
    for k in range(4):
        ctx.island(x0 + ctx.w * 0.5 + (k % 2 - 0.5) * 1.3, y0 + ctx.d * (0.35 + 0.15 * (k // 2)), 0.3, 0.3,
                   lambda pos: fu.chair(ctx.p, pos, 180, "leather"))


def jeweler(ctx):
    for k in range(3):
        ctx.wall(2.0, 0.6, False, lambda pos, yaw: fu.display_case(ctx.p, pos, yaw, 2.0, "furn_dark", "glass"), prefer=["E", "W", "S"])
    ctx.wall(1.0, 0.8, True, lambda pos, yaw: fu.safe(ctx.p, pos, yaw, "iron", "brass"), prefer=["S"])
    x0, y0, x1, y1 = ctx.rect
    ctx.island((x0 + x1) / 2, y0 + ctx.d * 0.5, 1.0, 0.35, lambda pos: fu.display_case(ctx.p, pos, 0, 2.0, "furn_dark", "glass"))


def furniture_store(ctx):
    x0, y0, x1, y1 = ctx.rect
    ctx.island(x0 + ctx.w * 0.3, y0 + ctx.d * 0.65, 1.0, 0.45, lambda pos: fu.sofa(ctx.p, pos, 180, 2.0, "upholstery", "furniture"))
    ctx.island(x0 + ctx.w * 0.7, y0 + ctx.d * 0.65, 0.45, 0.45, lambda pos: fu.armchair(ctx.p, pos, 180, "upholstery", "furniture"))
    ctx.island(x0 + ctx.w * 0.5, y0 + ctx.d * 0.4, 0.8, 0.45, lambda pos: fu.table(ctx.p, pos, 0, 1.6, 0.9, 0.76, "furn_dark"))
    ctx.island(x0 + ctx.w * 0.3, y0 + ctx.d * 0.2, 1.0, 1.0, lambda pos: fu.bed(ctx.p, pos, 0, 1.4, 1.95, "furniture", "quilt"))
    ctx.wall(1.0, 0.5, True, lambda pos, yaw: fu.dresser(ctx.p, pos, yaw, 1.0, 0.5, 0.9, "furniture", "brass"), prefer=["E", "W"])
    _register(ctx, ("S", "E"))


def appliance_repair(ctx):
    _register(ctx)
    for k in range(3):
        ctx.wall(0.7, 0.7, False, lambda pos, yaw: gh.appliance(ctx.p, pos, yaw, "enamel", 0.9 + 0.4 * (k % 2)), prefer=["W", "E"])
    ctx.wall(2.4, 0.75, False, lambda pos, yaw: fu.table(ctx.p, pos, yaw, 2.4, 0.75, 0.9, "furn_light"), prefer=["S"])
    ctx.wall(1.3, 0.45, False, lambda pos, yaw: gh.tv_stand(ctx.p, pos, yaw, "furniture", "tv"), prefer=["W", "E"])


def bakery(ctx):
    ctx.wall(3.0, 0.6, False, lambda pos, yaw: fu.display_case(ctx.p, pos, yaw, 3.0, "furniture", "glass"), prefer=["E", "W"])
    ctx.wall(1.6, 0.8, False, lambda pos, yaw: pizza_oven(ctx.p, pos, yaw), prefer=["S"])
    _wall_stock(ctx, 1, w=1.6, seed=80, prefer=("S", "W"))
    x0, y0, x1, y1 = ctx.rect
    ctx.island((x0 + x1) / 2, y0 + ctx.d * 0.3, 0.9, 0.45, lambda pos: fu.table(ctx.p, pos, 0, 1.8, 0.9, 0.9, "formica"))
    _register(ctx, ("W", "E"))


def butcher(ctx):
    ctx.wall(3.0, 0.7, False, lambda pos, yaw: cooler(ctx.p, pos, yaw, 3.0, seed=90), prefer=["E", "W"])
    ctx.wall(2.0, 0.7, False, lambda pos, yaw: fu.table(ctx.p, pos, yaw, 2.0, 0.7, 0.9, "furn_light"), prefer=["S"])
    ctx.wall(1.0, 0.8, False, lambda pos, yaw: fu.platform_scale(ctx.p, pos, yaw, "enamel", "steel"), prefer=["W", "S"])
    _register(ctx, ("W", "E"))


def feed_seed(ctx):
    ctx.wall(2.0, 1.3, False, lambda pos, yaw: fu.sack_stack(ctx.p, pos, yaw, 3, 2, 4, "burlap"), prefer=["W", "E", "S"])
    ctx.wall(2.0, 1.3, False, lambda pos, yaw: fu.sack_stack(ctx.p, pos, yaw, 3, 2, 3, "burlap"), prefer=["S", "W", "E"])
    ctx.wall(1.0, 0.8, False, lambda pos, yaw: fu.platform_scale(ctx.p, pos, yaw, "furniture", "steel"), prefer=["E", "W"])
    _wall_stock(ctx, 1, seed=100)
    _register(ctx)


def auto_parts(ctx):
    _register(ctx)
    _wall_stock(ctx, 4, seed=110, prefer=("S", "W", "E"))
    ctx.aisle_rows(2, min(ctx.w - 3.2, 3.6), 0.9, lambda pos: gondola(ctx.p, pos, 0, min(ctx.w - 3.2, 3.6), 1.8, seed=111))


def office(ctx, n=2, waiting=True):
    x0, y0, x1, y1 = ctx.rect
    for k in range(n):
        ctx.island(x0 + ctx.w * (0.3 + 0.4 * (k % 2)), y0 + ctx.d * (0.3 + 0.3 * (k // 2)), 0.75, 0.9,
                   lambda pos: office_set(ctx.p, pos, 180))
    for k in range(2):
        ctx.wall(0.46, 0.7, True, lambda pos, yaw: file_cabinet(ctx.p, pos, yaw), prefer=["S", "W", "E"])
    ctx.wall(0.9, 0.35, True, lambda pos, yaw: fu.shelves(ctx.p, pos, yaw, 0.9, 0.35, 1.9, 5, "furniture"), prefer=["W", "E", "S"])
    if waiting:
        ctx.wall(1.8, 0.6, False, lambda pos, yaw: fu.bench(ctx.p, pos, yaw, 1.8, "furniture"), prefer=["W", "E"])


def doctor_office(ctx):
    office(ctx, n=1)
    x0, y0, x1, y1 = ctx.rect
    ctx.island(x0 + ctx.w * 0.3, y0 + ctx.d * 0.25, 0.35, 0.95, lambda pos: exam_table(ctx.p, pos, 0))


def dentist(ctx):
    office(ctx, n=1)
    x0, y0, x1, y1 = ctx.rect
    ctx.island(x0 + ctx.w * 0.35, y0 + ctx.d * 0.25, 0.35, 0.5, lambda pos: barber_chair(ctx.p, pos, 0, mat="goods4"))


def newspaper(ctx):
    office(ctx, n=3, waiting=False)
    x0, y0, x1, y1 = ctx.rect
    ctx.island(x0 + ctx.w * 0.5, y0 + 1.0, 0.8, 0.6, lambda pos: press(ctx.p, pos, 0))


def print_shop(ctx):
    x0, y0, x1, y1 = ctx.rect
    ctx.island(x0 + ctx.w * 0.35, y0 + ctx.d * 0.35, 0.8, 0.6, lambda pos: press(ctx.p, pos, 0))
    ctx.wall(2.2, 0.75, False, lambda pos, yaw: fu.table(ctx.p, pos, yaw, 2.2, 0.75, 0.9, "furn_light"), prefer=["E", "W"])
    _wall_stock(ctx, 2, seed=120)
    _register(ctx)


def bookstore(ctx):
    _register(ctx)
    for k in range(5):
        ctx.wall(1.2, 0.35, True, lambda pos, yaw, k=k: fu.stocked_shelves(ctx.p, pos, yaw, 1.2, 0.33, 2.1, 6, "furn_dark",
                                                                            GOODS, seed=130 + k), prefer=["W", "E", "S"])
    x0, y0, x1, y1 = ctx.rect
    ctx.island((x0 + x1) / 2, y0 + ctx.d * 0.5, 0.8, 0.45, lambda pos: fu.table(ctx.p, pos, 0, 1.6, 0.9, 0.76, "furniture"))
    ctx.island(x0 + ctx.w * 0.25, y0 + ctx.d * 0.25, 0.45, 0.45, lambda pos: fu.armchair(ctx.p, pos, 0, "leather", "furn_dark"))


def laundromat(ctx):
    x0, y0, x1, y1 = ctx.rect
    for side in ("W", "E"):
        for k in range(int((ctx.d - 2.0) / 0.75)):
            ctx.wall(0.7, 0.7, False, lambda pos, yaw, k=k: washer(ctx.p, pos, yaw), prefer=[side])
    ctx.island((x0 + x1) / 2, y0 + ctx.d * 0.45, 0.9, 0.4, lambda pos: fu.table(ctx.p, pos, 0, 1.8, 0.8, 0.9, "formica"))
    ctx.island((x0 + x1) / 2, y0 + ctx.d * 0.72, 1.0, 0.3, lambda pos: fu.bench(ctx.p, pos, 180, 2.0, "vinyl_red"))


def florist(ctx):
    ctx.wall(2.4, 0.7, False, lambda pos, yaw: cooler(ctx.p, pos, yaw, 2.4, goods=["green_leaf", "goods0", "goods2", "goods4"],
                                                      seed=140), prefer=["S", "E"])
    x0, y0, x1, y1 = ctx.rect
    for k in range(3):
        ctx.island(x0 + ctx.w * (0.3 + 0.2 * k), y0 + ctx.d * 0.55, 0.3, 0.3,
                   lambda pos: ctx.p.cylinder((pos[0], pos[1]), 0.25, pos[2], pos[2] + 0.5, "green_leaf", n=10))
    ctx.wall(2.0, 0.75, False, lambda pos, yaw: fu.table(ctx.p, pos, yaw, 2.0, 0.75, 0.9, "furniture"), prefer=["W"])
    _register(ctx, ("E", "W"))


def pizza(ctx):
    ctx.wall(1.6, 0.9, False, lambda pos, yaw: pizza_oven(ctx.p, pos, yaw), prefer=["S"])
    ctx.wall(2.4, 0.6, False, lambda pos, yaw: fu.bar_counter(ctx.p, pos, yaw, 2.4, "formica", "formica", "chrome_s", h=1.0),
             prefer=["E", "W"])
    x0, y0, x1, y1 = ctx.rect
    n = max(1, int((ctx.d - 3.0) / 2.2))
    for k in range(n):
        ctx.island(x0 + 1.25, y0 + 1.8 + k * 2.2, 0.62, 1.05, lambda pos: booth(ctx.p, pos, 0))


def sporting_goods(ctx):
    _register(ctx)
    _wall_stock(ctx, 3, seed=150)
    x0, y0, x1, y1 = ctx.rect
    ctx.island(x0 + ctx.w * 0.5, y0 + ctx.d * 0.45, 0.8, 0.3, lambda pos: clothes_rack(ctx.p, pos, 0, 1.6, seed=151))
    ctx.wall(1.2, 0.7, False, lambda pos, yaw: cooler(ctx.p, pos, yaw, 1.2, goods=["goods3", "goods1"], seed=152), prefer=["S"])


def thrift_store(ctx):
    clothing(ctx)
    _wall_stock(ctx, 2, seed=160)


def video_rental(ctx):
    _register(ctx)
    for k in range(4):
        ctx.wall(1.6, 0.3, True, lambda pos, yaw, k=k: fu.stocked_shelves(ctx.p, pos, yaw, 1.6, 0.28, 1.9, 7, "black",
                                                                            GOODS, seed=170 + k), prefer=["W", "E", "S"])
    ctx.aisle_rows(2, min(ctx.w - 3.2, 3.0), 0.7, lambda pos: gondola(ctx.p, pos, 0, min(ctx.w - 3.2, 3.0), 1.5, seed=175, mat="black"))


def music_store(ctx):
    _register(ctx)
    for k in range(2):
        ctx.wall(1.6, 0.65, False, lambda pos, yaw: piano(ctx.p, pos, yaw), prefer=["W", "E"])
    _wall_stock(ctx, 2, seed=180, prefer=("S",))


def shoe_repair(ctx):
    _register(ctx)
    ctx.wall(2.2, 0.75, False, lambda pos, yaw: fu.table(ctx.p, pos, yaw, 2.2, 0.75, 0.9, "furn_light"), prefer=["S", "E"])
    _wall_stock(ctx, 2, w=1.2, seed=190)
    ctx.wall(1.6, 0.6, False, lambda pos, yaw: fu.bench(ctx.p, pos, yaw, 1.6, "furniture"), prefer=["W"])


def movie_theater(ctx):
    x0, y0, x1, y1 = ctx.rect
    # screen on the rear wall facing the street end; rows face it
    # hung above door height: the shop's back door is in that wall
    ctx.p.box((x0 + 0.5, y0 + 0.05, ctx.fz + 2.3), (x1 - 0.5, y0 + 0.1, ctx.fz + max(2.9, min(4.0, ctx.cz - ctx.fz - 0.3))), "screen")
    theater_rows_back(ctx)


def theater_rows_back(ctx):
    """Rows of seats facing the rear (-y) wall where the screen is."""
    x0, y0, x1, y1 = ctx.rect
    cx = (x0 + x1) / 2
    for k in range(40):
        y = y0 + 3.5 + k * 0.95
        if y > y1 - 2.0:
            break
        for (a, c) in ((x0 + 0.9, cx - 0.6), (cx + 0.6, x1 - 0.9)):
            n = int((c - a) / 0.55)
            for i in range(n):
                sx = a + (i + 0.5) * (c - a) / n
                if ctx.h._hits_swing(sx - 0.25, y - 0.25, sx + 0.25, y + 0.3, ctx.fl):
                    continue
                f = fu.F((sx, y, ctx.fz), 0)
                ctx.p.obox(f, (-0.24, -0.25, 0.0), (0.24, 0.25, 0.45), "black")
                ctx.p.obox(f, (-0.22, -0.2, 0.4), (0.22, 0.25, 0.5), "vinyl_red")
                ctx.p.obox(f, (-0.22, 0.2, 0.4), (0.22, 0.28, 1.0), "vinyl_red")


def gas_station(ctx):
    _register(ctx)
    _wall_stock(ctx, 2, seed=200)
    ctx.wall(1.8, 0.7, False, lambda pos, yaw: cooler(ctx.p, pos, yaw, 1.8, seed=201), prefer=["S", "W"])
    ctx.aisle_rows(1, min(ctx.w - 3.2, 3.0), 0.9, lambda pos: gondola(ctx.p, pos, 0, min(ctx.w - 3.2, 3.0), 1.4, seed=202))


def auto_repair(ctx):
    x0, y0, x1, y1 = ctx.rect
    ctx.island((x0 + x1) / 2, (y0 + y1) / 2, 1.5, 0.5, lambda pos: car_lift(ctx.p, pos, 90))
    ctx.wall(2.4, 0.75, False, lambda pos, yaw: fu.table(ctx.p, pos, yaw, 2.4, 0.75, 0.9, "steel"), prefer=["S", "W"])
    ctx.wall(1.2, 0.5, True, lambda pos, yaw: fu.shelves(ctx.p, pos, yaw, 1.2, 0.45, 2.0, 4, "steel"), prefer=["W", "E"])
    ctx.wall(0.9, 0.9, False, lambda pos, yaw: fu.barrel(ctx.p, pos, "goods1", "steel"), prefer=["E", "S"])


def funeral_home(ctx):
    x0, y0, x1, y1 = ctx.rect
    rows = max(2, int((ctx.d - 3.0) / 1.0))
    for k in range(rows):
        for side in (-1, 1):
            ctx.island((x0 + x1) / 2 + side * ctx.w * 0.22, y0 + 2.2 + k * 1.0, 0.9, 0.3,
                       lambda pos: fu.bench(ctx.p, pos, 0, 1.6, "furn_dark"))
    ctx.wall(2.2, 0.8, False, lambda pos, yaw: fu.table(ctx.p, pos, yaw, 2.2, 0.8, 0.8, "furn_dark"), prefer=["S"])


def motel(ctx):
    x0, y0, x1, y1 = ctx.rect
    ctx.wall(2.4, 0.6, False, lambda pos, yaw: fu.display_case(ctx.p, pos, yaw, 2.4, "furn_dark", "glass"), prefer=["S", "E"])
    ctx.wall(0.9, 0.3, True, lambda pos, yaw: fu.shelves(ctx.p, pos, yaw, 0.9, 0.2, 1.6, 6, "furn_dark"), prefer=["S", "W"])
    ctx.island(x0 + ctx.w * 0.35, y0 + ctx.d * 0.6, 1.0, 0.45, lambda pos: fu.sofa(ctx.p, pos, 180, 2.0, "vinyl_red", "chrome_s"))


def insurance_office(ctx):
    office(ctx, n=2)


def law_office(ctx):
    office(ctx, n=2)
    for k in range(3):
        ctx.wall(1.0, 0.35, True, lambda pos, yaw: fu.stocked_shelves(ctx.p, pos, yaw, 1.0, 0.33, 2.1, 6, "furn_dark", GOODS, seed=210 + k),
                 prefer=["W", "E", "S"])


def real_estate(ctx):
    office(ctx, n=2)


def tavern_hotel(ctx):
    bar(ctx)


def vacant_storefront(ctx):
    x0, y0, x1, y1 = ctx.rect
    ctx.island(x0 + ctx.w * 0.3, y0 + ctx.d * 0.4, 0.6, 0.6, lambda pos: fu.sack_stack(ctx.p, pos, 0, 2, 2, 1, "plywood"))
    ctx.wall(1.2, 0.5, True, lambda pos, yaw: fu.shelves(ctx.p, pos, yaw, 1.2, 0.45, 1.8, 3, "furniture"), prefer=["W"])


def stockroom(ctx):
    _wall_stock(ctx, 3, w=1.8, seed=220, prefer=("S", "W", "E"))
    x0, y0, x1, y1 = ctx.rect
    ctx.island(x0 + ctx.w * 0.4, y0 + ctx.d * 0.5, 0.6, 0.6, lambda pos: fu.sack_stack(ctx.p, pos, 0, 2, 2, 2, "plywood"))


# ------------------------------------------------------------------ institutional rooms
def classroom(ctx):
    x0, y0, x1, y1 = ctx.rect
    # teacher's end at the room's -x end; rows of pupils' desks face it
    ctx.p.box((x0 + 0.02, y0 + 0.8, ctx.fz + 0.8), (x0 + 0.05, y1 - 0.8, ctx.fz + 2.0), "black")
    ctx.p.box((x0 + 0.02, y0 + 0.8, ctx.fz + 0.76), (x0 + 0.12, y1 - 0.8, ctx.fz + 0.8), "furniture")
    ctx.island(x0 + 1.3, (y0 + y1) / 2, 0.4, 0.75, lambda pos: office_set(ctx.p, pos, -90))
    # desks in rows with walkable aisles (0.7 m between desk columns, 0.5 m behind each chair)
    cols = max(2, int((ctx.d - 1.6) / 1.3))
    rows = max(2, int((ctx.w - 3.4) / 1.55))          # desk + chair is 0.84 m deep: 0.7 m aisles
    for i in range(rows):
        for j in range(cols):
            cx = x0 + 3.0 + i * 1.55
            cy = y0 + 1.2 + j * ((ctx.d - 2.4) / max(1, cols - 1))
            if cx > x1 - 0.7:
                continue
            ctx.island(cx, cy, 0.3, 0.3, lambda pos: _pupil_desk(ctx.p, pos))
    ctx.wall(1.2, 0.35, True, lambda pos, yaw: fu.shelves(ctx.p, pos, yaw, 1.2, 0.33, 1.8, 5, "furniture"), prefer=["E"])


def _pupil_desk(p, pos, mat="furn_light", frame="iron"):
    f = fu.F(pos, -90)
    p.obox(f, (-0.28, -0.2, 0.68), (0.28, 0.2, 0.72), mat)
    p.obox(f, (-0.25, -0.02, 0), (0.25, 0.02, 0.68), frame)
    p.obox(f, (-0.2, 0.3, 0.42), (0.2, 0.62, 0.46), mat)
    p.obox(f, (-0.2, 0.6, 0.46), (0.2, 0.64, 0.85), mat)


def lobby(ctx):
    for side in ("W", "E"):
        ctx.wall(2.0, 0.6, False, lambda pos, yaw: fu.bench(ctx.p, pos, yaw, 2.0, "furn_dark"), prefer=[side])


def council(ctx):
    x0, y0, x1, y1 = ctx.rect
    yf, sgn = ctx.far()
    cx = (x0 + x1) / 2
    ctx.island(cx, yf + sgn * 1.4, 2.2, 0.45, lambda pos: fu.table(ctx.p, pos, 0, 4.4, 0.9, 0.76, "furn_dark"))
    for k in range(5):
        ctx.island(cx - 1.8 + k * 0.9, yf + sgn * 0.75, 0.25, 0.25, lambda pos: fu.chair(ctx.p, pos, 180 if sgn < 0 else 0, "leather"))
    rows = max(1, int((ctx.d - 4.5) / 1.1))
    for k in range(rows):
        for side in (-1, 1):
            ctx.island(cx + side * ctx.w * 0.22, yf + sgn * (3.2 + k * 1.1), 0.9, 0.3,
                       lambda pos: fu.bench(ctx.p, pos, 180 if sgn > 0 else 0, 1.6, "furn_dark"))


def courtroom(ctx):
    x0, y0, x1, y1 = ctx.rect
    yf, sgn = ctx.far()
    cx = (x0 + x1) / 2
    face = 180 if sgn < 0 else 0          # the judge faces the room
    ctx.island(cx, yf + sgn * 0.9, 1.5, 0.45, lambda pos: fu.bar_counter(ctx.p, pos, face, 3.0, "furn_dark", "furn_dark", "brass", h=1.3))
    ctx.island(cx, yf + sgn * 0.45, 0.3, 0.3, lambda pos: fu.chair(ctx.p, pos, face, "leather"))
    ctx.island(x0 + 1.2, yf + sgn * 2.4, 0.6, 1.2, lambda pos: fu.bench(ctx.p, pos, 90, 2.4, "furn_dark"))       # jury box
    for k in range(2):
        ctx.island(cx + (k - 0.5) * 2.6, yf + sgn * 3.4, 0.8, 0.4, lambda pos: fu.table(ctx.p, pos, 0, 1.6, 0.8, 0.76, "furn_dark"))
    rows = max(1, int((ctx.d - 6.0) / 1.1))
    for k in range(rows):
        for side in (-1, 1):
            ctx.island(cx + side * ctx.w * 0.22, yf + sgn * (5.0 + k * 1.1), 0.9, 0.3,
                       lambda pos: fu.bench(ctx.p, pos, face + 180, 1.6, "furn_dark"))


def library(ctx):
    x0, y0, x1, y1 = ctx.rect
    for k in range(6):
        ctx.wall(1.5, 0.35, True, lambda pos, yaw, k=k: fu.stocked_shelves(ctx.p, pos, yaw, 1.5, 0.33, 2.1, 6, "furn_dark", GOODS,
                                                                            seed=300 + k), prefer=["W", "E", "S"])
    n = max(1, int((ctx.w - 3.0) / 2.2))
    for i in range(n):
        ctx.island(x0 + 1.8 + i * 2.2, y0 + ctx.d * 0.3, 0.45, 1.0, lambda pos, i=i: gondola(ctx.p, pos, 90, 2.0, 1.9, seed=310 + i,
                                                                                            mat="furn_dark"))
    for i in range(max(1, n - 1)):
        ctx.island(x0 + 2.6 + i * 2.6, y0 + ctx.d * 0.7, 1.2, 0.9, lambda pos: _reading_table(ctx.p, pos))
    ctx.wall(2.4, 0.7, False, lambda pos, yaw: fu.bar_counter(ctx.p, pos, yaw, 2.4, "furn_dark", "furn_dark", "brass", h=1.0),
             prefer=["E", "W"])


def _reading_table(p, pos):
    fu.table(p, pos, 0, 2.0, 0.9, 0.76, "furn_dark")
    for sx in (-0.5, 0.5):
        for sy, yaw in ((-0.7, 0), (0.7, 180)):
            fu.chair(p, (pos[0] + sx, pos[1] + sy, pos[2]), yaw, "furn_dark")


def ward(ctx):
    x0, y0, x1, y1 = ctx.rect
    n = max(1, int((ctx.w - 0.6) / 1.6))
    for i in range(n):
        ctx.wall(1.0, 2.05, False, lambda pos, yaw: fu.bed(ctx.p, pos, yaw, 0.95, 1.95, "steel", "white_text", head_h=1.0),
                 prefer=["S", "N"])
    ctx.wall(0.5, 0.45, False, lambda pos, yaw: fu.chair(ctx.p, pos, yaw, "steel"), prefer=["E", "W"])


def nurse_station(ctx):
    x0, y0, x1, y1 = ctx.rect
    ctx.island((x0 + x1) / 2, (y0 + y1) / 2, 1.2, 0.35, lambda pos: fu.bar_counter(ctx.p, pos, 0, 2.4, "formica", "formica", "steel", h=1.05))
    office(ctx, n=1, waiting=False)


def fire_bay(ctx):
    x0, y0, x1, y1 = ctx.rect
    n = max(1, int(ctx.w / 4.5))
    for i in range(n):
        ctx.island(x0 + ctx.w * (i + 0.5) / n, (y0 + y1) / 2, 1.2, 3.8, lambda pos: _fire_engine(ctx.p, pos))
    ctx.wall(2.0, 0.5, True, lambda pos, yaw: fu.shelves(ctx.p, pos, yaw, 2.0, 0.45, 2.0, 4, "steel"), prefer=["S"])
    for k in range(4):
        ctx.wall(0.5, 0.4, True, lambda pos, yaw: fu.coat_rack(ctx.p, (pos[0], pos[1], ctx.fz), "steel"), prefer=["W", "E"])


def _fire_engine(p, pos, body="vinyl_red", chrome="chrome_s"):
    f = fu.F(pos, 90)
    p.obox(f, (-3.6, -1.1, 0.45), (3.6, 1.1, 2.2), body)
    p.obox(f, (2.2, -1.12, 1.2), (3.55, 1.12, 2.1), "glass")
    for x in (-2.6, 2.4):
        for y in (-1.1, 1.1):
            p.obox(f, (x - 0.45, y - 0.15, 0.0), (x + 0.45, y + 0.15, 0.9), "tire")
    p.obox(f, (-3.4, -1.15, 2.2), (2.0, 1.15, 2.35), chrome)


def jail(ctx):
    x0, y0, x1, y1 = ctx.rect
    ctx.p.box((x0, (y0 + y1) / 2 - 0.03, ctx.fz), (x1 - 1.2, (y0 + y1) / 2 + 0.03, ctx.fz + 2.2), "iron")
    for k in range(int((x1 - 1.2 - x0) / 0.15)):
        ctx.p.box((x0 + k * 0.15, (y0 + y1) / 2 - 0.03, ctx.fz), (x0 + k * 0.15 + 0.03, (y0 + y1) / 2 + 0.03, ctx.fz + 2.2), "iron")
    ctx.wall(1.95, 0.8, False, lambda pos, yaw: fu.bench(ctx.p, pos, yaw, 1.95, "steel", back=False), prefer=["S"])


def auditorium(ctx):
    x0, y0, x1, y1 = ctx.rect
    # stage at the -y end
    ctx.p.box((x0 + 0.2, y0, ctx.fz), (x1 - 0.2, y0 + min(4.0, ctx.d * 0.25), ctx.fz + 0.9), "floor")
    cx = (x0 + x1) / 2
    y = y0 + min(4.0, ctx.d * 0.25) + 1.6
    while y < y1 - 1.5:
        for (a, c) in ((x0 + 0.9, cx - 0.7), (cx + 0.7, x1 - 0.9)):
            n = int((c - a) / 0.55)
            for i in range(n):
                sx = a + (i + 0.5) * (c - a) / n
                if ctx.h._hits_swing(sx - 0.25, y - 0.25, sx + 0.25, y + 0.3, ctx.fl):
                    continue
                f = fu.F((sx, y, ctx.fz), 0)
                ctx.p.obox(f, (-0.24, -0.25, 0.0), (0.24, 0.25, 0.45), "black")
                ctx.p.obox(f, (-0.22, -0.2, 0.4), (0.22, 0.25, 0.5), "vinyl_red")
                ctx.p.obox(f, (-0.22, 0.2, 0.4), (0.22, 0.28, 1.0), "vinyl_red")
        y += 0.95


def gym(ctx):
    x0, y0, x1, y1 = ctx.rect
    for xx in (x0 + 0.4, x1 - 0.4):
        ctx.p.box((xx - 0.05, (y0 + y1) / 2 - 0.9, ctx.fz + 2.75), (xx + 0.05, (y0 + y1) / 2 + 0.9, ctx.fz + 3.8), "screen")
        ctx.p.cylinder((xx + (0.4 if xx < (x0 + x1) / 2 else -0.4), (y0 + y1) / 2), 0.23, ctx.fz + 3.04, ctx.fz + 3.06, "goods0", n=12)
    for k in range(3):
        ctx.p.box((x0 + 2.0, y1 - 0.5 - k * 0.45, ctx.fz), (x1 - 2.0, y1 - 0.05 - k * 0.45, ctx.fz + 0.45 * (k + 1)), "furn_light")


def cafeteria(ctx):
    x0, y0, x1, y1 = ctx.rect
    for i in range(max(1, int((ctx.w - 1.0) / 2.6))):
        for j in range(max(1, int((ctx.d - 3.0) / 2.2))):
            ctx.island(x0 + 1.8 + i * 2.6, y0 + 2.6 + j * 2.2, 1.1, 0.9, lambda pos: _reading_table(ctx.p, pos))
    ctx.wall(3.0, 0.7, False, lambda pos, yaw: fu.bar_counter(ctx.p, pos, yaw, 3.0, "steel", "steel", "chrome_s", h=0.95), prefer=["S"])


def nave(ctx):
    """Church nave: altar/chancel at -y, pews both sides of a centre aisle facing it."""
    x0, y0, x1, y1 = ctx.rect
    ch = min(3.2, ctx.d * 0.22)
    ctx.p.box((x0 + 0.3, y0, ctx.fz), (x1 - 0.3, y0 + ch, ctx.fz + 0.35), "floor")
    ctx.p.box(((x0 + x1) / 2 - 0.9, y0 + 0.5, ctx.fz + 0.35), ((x0 + x1) / 2 + 0.9, y0 + 1.2, ctx.fz + 1.3), "furn_dark")   # altar
    ctx.p.box((x0 + 0.8, y0 + ch - 0.9, ctx.fz + 0.35), (x0 + 1.6, y0 + ch - 0.2, ctx.fz + 1.5), "furn_dark")               # pulpit
    ctx.p.box(((x0 + x1) / 2 - 0.05, y0 + 0.2, ctx.fz + 1.8), ((x0 + x1) / 2 + 0.05, y0 + 0.26, ctx.fz + 3.2), "brass")      # cross
    ctx.p.box(((x0 + x1) / 2 - 0.45, y0 + 0.2, ctx.fz + 2.7), ((x0 + x1) / 2 + 0.45, y0 + 0.26, ctx.fz + 2.8), "brass")
    cx = (x0 + x1) / 2
    y = y0 + ch + 1.2
    while y < y1 - 1.6:
        for (a, c) in ((x0 + 0.5, cx - 0.75), (cx + 0.75, x1 - 0.5)):
            L = c - a
            if L > 0.8:
                f = fu.F(((a + c) / 2, y, ctx.fz), 0)
                ctx.p.obox(f, (-L / 2, -0.25, 0.0), (L / 2, 0.2, 0.45), "furn_dark")
                ctx.p.obox(f, (-L / 2, 0.2, 0.0), (L / 2, 0.28, 0.95), "furn_dark")
        y += 1.0


def fellowship(ctx):
    cafeteria(ctx)


def po_boxes(p, pos, yaw, w, mat="brass", frame="furn_dark"):
    """A wall of brass post-office boxes (front = local -Y)."""
    f = fu.F(pos, yaw)
    p.obox(f, (-w / 2, -0.2, 0), (w / 2, 0.2, 0.3), frame)
    p.obox(f, (-w / 2, -0.2, 0.3), (w / 2, 0.2, 2.1), mat)
    for i in range(int(w / 0.15)):
        p.obox(f, (-w / 2 + i * 0.15, -0.21, 0.3), (-w / 2 + i * 0.15 + 0.012, -0.2, 2.1), frame)


def post_office_lobby(ctx):
    x0, y0, x1, y1 = ctx.rect
    for k in range(2):
        ctx.wall(2.4, 0.4, True, lambda pos, yaw: po_boxes(ctx.p, pos, yaw, 2.4), prefer=["S", "W", "E"])
    ctx.island((x0 + x1) / 2, y0 + 1.6, 0.8, 0.3, lambda pos: fu.table(ctx.p, pos, 0, 1.6, 0.6, 1.05, "furn_dark"))
    lobby(ctx)


def sorting_room(ctx):
    for k in range(3):
        ctx.wall(1.8, 0.45, True, lambda pos, yaw, k=k: fu.stocked_shelves(ctx.p, pos, yaw, 1.8, 0.4, 1.9, 8, "furniture", GOODS,
                                                                            seed=330 + k), prefer=["S", "E", "W"])
    x0, y0, x1, y1 = ctx.rect
    ctx.island((x0 + x1) / 2, (y0 + y1) / 2, 1.0, 0.45, lambda pos: fu.table(ctx.p, pos, 0, 2.0, 0.9, 0.9, "furn_light"))


def waiting_room(ctx):
    lobby(ctx)
    x0, y0, x1, y1 = ctx.rect
    ctx.island((x0 + x1) / 2, (y0 + y1) / 2, 1.0, 0.3, lambda pos: fu.bench(ctx.p, pos, 0, 2.0, "furn_dark"))


def machine_floor(ctx):
    """Industrial floor: machine tools, benches, racks."""
    x0, y0, x1, y1 = ctx.rect
    nx, ny = max(1, int(ctx.w / 4.5)), max(1, int(ctx.d / 4.5))
    for i in range(nx):
        for j in range(ny):
            kind = (i + j) % 3
            ctx.island(x0 + ctx.w * (i + 0.5) / nx, y0 + ctx.d * (j + 0.5) / ny, 1.0, 0.7,
                       lambda pos, kind=kind: _machine(ctx.p, pos, kind))
    for k in range(3):
        ctx.wall(2.4, 0.75, False, lambda pos, yaw: fu.table(ctx.p, pos, yaw, 2.4, 0.75, 0.9, "steel"), prefer=["S", "W", "E"])


def _machine(p, pos, kind, mat="goods3", metal="steel"):
    f = fu.F(pos, 0)
    if kind == 0:                       # lathe
        p.obox(f, (-1.0, -0.3, 0), (1.0, 0.3, 0.9), mat)
        p.obox(f, (-0.9, -0.2, 0.9), (-0.5, 0.2, 1.3), metal)
        p.obox(f, (0.6, -0.15, 0.9), (0.9, 0.15, 1.2), metal)
    elif kind == 1:                     # drill press / mill
        p.obox(f, (-0.4, -0.4, 0), (0.4, 0.4, 0.2), mat)
        p.obox(f, (-0.1, 0.2, 0.2), (0.1, 0.4, 2.0), mat)
        p.obox(f, (-0.35, -0.3, 1.5), (0.35, 0.4, 1.9), mat)
        p.obox(f, (-0.3, -0.3, 0.8), (0.3, 0.2, 0.85), metal)
    else:                               # press / tank
        p.cylinder((pos[0], pos[1]), 0.6, pos[2], pos[2] + 2.2, metal, n=14)


# ------------------------------------------------------------------ the coasts
def _cabinet(p, pos, yaw, body, screen):
    """An upright arcade cabinet: body, lit screen, control deck, marquee."""
    f = fu.F(pos, yaw)
    p.obox(f, (-0.33, -0.4, 0.0), (0.33, 0.35, 1.85), body)
    p.obox(f, (-0.27, -0.42, 1.05), (0.27, -0.4, 1.5), screen)
    p.obox(f, (-0.33, -0.62, 0.85), (0.33, -0.4, 0.95), "black")
    p.obox(f, (-0.33, -0.44, 1.62), (0.33, -0.4, 1.82), screen)


def arcade(ctx):
    """Rows of cabinets along the walls, skee-ball lanes down the middle, a prize counter at the back."""
    ctx.wall(3.0, 0.7, True, lambda pos, yaw: fu.display_case(ctx.p, pos, yaw, 3.0, "furniture", "glass", h=1.0), prefer=["S"])
    for k in range(max(2, int(ctx.w / 0.8))):
        ctx.wall(0.7, 0.8, True, lambda pos, yaw, k=k: _cabinet(ctx.p, pos, yaw, ("vinyl_red", "goods1", "black", "goods3")[k % 4],
                                                               "screen_lit"), prefer=["E", "W", "S"])
    x0, y0, x1, y1 = ctx.rect
    for k in range(max(1, int((ctx.w - 3.0) / 1.2))):
        ctx.island(x0 + 1.5 + k * 1.2, (y0 + y1) / 2, 0.4, 1.6,
                   lambda pos: (ctx.p.box((pos[0] - 0.38, pos[1] - 1.6, pos[2]), (pos[0] + 0.38, pos[1] + 1.6, pos[2] + 0.75), "furn_light"),
                                ctx.p.box((pos[0] - 0.38, pos[1] - 1.6, pos[2] + 0.75), (pos[0] + 0.38, pos[1] - 1.1, pos[2] + 1.9), "vinyl_red")))


def snack_stand(ctx):
    """A boardwalk food stand: counter across the open front, fryers, griddle and fridges behind."""
    L = max(1.5, ctx.w - 1.2)
    ctx.wall(L, 0.7, False, lambda pos, yaw: fu.bar_counter(ctx.p, pos, yaw, L, "formica", "counter_top", "chrome_s", h=1.05),
             prefer=["N"])
    # (their real depths: the fryer and the range are 0.7 m -- declared 0.6 they stood 3-7 cm in the back wall, gbaudit)
    ctx.wall(1.2, 0.72, False, lambda pos, yaw: fu.fryer(ctx.p, pos, yaw, "steel", "goods2"), prefer=["S"])
    ctx.wall(1.2, 0.72, False, lambda pos, yaw: fu.range_stove(ctx.p, pos, yaw, "steel", "iron", w=1.2), prefer=["S"])
    ctx.wall(0.8, 0.7, True, lambda pos, yaw: fu.fridge(ctx.p, pos, yaw, "enamel", "chrome_s"), prefer=["S", "E", "W"])
    ctx.wall(1.6, 0.4, True, lambda pos, yaw: fu.shelves(ctx.p, pos, yaw, 1.6, 0.35, 1.8, 5, "steel"), prefer=["E", "W"])


def guest_room(ctx):
    """A hotel / motel room: a bed or two against the far wall, nightstand, dresser with a TV, an
    armchair by the window."""
    x0, y0, x1, y1 = ctx.rect
    two = ctx.w >= 3.6
    for k in range(2 if two else 1):
        ctx.wall(1.5, 2.1, False, lambda pos, yaw: fu.bed(ctx.p, pos, yaw, 1.4, 2.0, "furn_dark", "quilt"), prefer=["E", "W"])
    ctx.wall(1.4, 0.5, False, lambda pos, yaw: (fu.dresser(ctx.p, pos, yaw, 1.4, 0.5, 0.8, "furn_dark", "brass"),
                                               ctx.p.obox(fu.F(pos, yaw), (-0.4, 0.0, 0.8), (0.4, 0.1, 1.3), "tv")),   # (turned with the dresser)
             prefer=["W", "E", "S"])
    ctx.island(x0 + ctx.w * 0.3, y0 + ctx.d * 0.8, 0.45, 0.45, lambda pos: fu.armchair(ctx.p, pos, 180, "upholstery", "furn_dark"))


def lifeguard_hut(ctx):
    x0, y0, x1, y1 = ctx.rect
    ctx.island((x0 + x1) / 2, (y0 + y1) / 2, 0.3, 0.3, lambda pos: fu.stool(ctx.p, pos, "steel", "vinyl_red", h=0.9))
    ctx.wall(1.0, 0.4, True, lambda pos, yaw: fu.shelves(ctx.p, pos, yaw, 1.0, 0.3, 1.5, 3, "furniture"), prefer=["S", "E", "W"])


RECIPES_INST = {
    "classroom": classroom, "lobby": lobby, "council": council, "courtroom": courtroom, "library": library, "ward": ward,
    "nurse_station": nurse_station, "fire_bay": fire_bay, "jail": jail, "auditorium": auditorium, "gym": gym,
    "cafeteria": cafeteria, "nave": nave, "fellowship": fellowship, "po_lobby": post_office_lobby,
    "sorting_room": sorting_room, "waiting_room": waiting_room, "machine_floor": machine_floor,
}


RECIPES = {
    "grocery": grocery, "variety_store": variety_store, "hardware": hardware, "drug_store": drug_store, "diner": diner,
    "cafe": cafe, "bar": bar, "pool_hall": pool_hall, "bank": bank, "barber": barber, "beauty_salon": beauty_salon,
    "dry_goods": dry_goods, "clothing": clothing, "shoe_store": shoe_store, "jeweler": jeweler, "furniture": furniture_store,
    "appliance_repair": appliance_repair, "bakery": bakery, "butcher": butcher, "feed_seed": feed_seed, "auto_parts": auto_parts,
    "insurance_office": insurance_office, "law_office": law_office, "doctor_office": doctor_office, "dentist": dentist,
    "newspaper": newspaper, "movie_theater": movie_theater, "bookstore": bookstore, "laundromat": laundromat,
    "florist": florist, "pizza": pizza, "sporting_goods": sporting_goods, "thrift_store": thrift_store,
    "video_rental": video_rental, "gas_station": gas_station, "auto_repair": auto_repair, "motel": motel,
    "funeral_home": funeral_home, "tavern_hotel": tavern_hotel, "vacant_storefront": vacant_storefront,
    "music_store": music_store, "print_shop": print_shop, "shoe_repair": shoe_repair, "real_estate": real_estate,
    # bigbox / strip vocabulary
    "discount": variety_store, "pharmacy": drug_store, "pet": variety_store, "dollar": variety_store,
    "nail_salon": beauty_salon, "tax_office": insurance_office, "vacant": vacant_storefront,
    "stockroom": stockroom, "office": office,
}
RECIPES.update(RECIPES_INST)
RECIPES.update({
    "arcade": arcade, "games": arcade, "snack_stand": snack_stand, "food": snack_stand, "guest_room": guest_room,
    "lifeguard_hut": lifeguard_hut,
    # the coastal store vocabulary (CATALOG_SPEC_COASTAL.md) onto the nearest fit-out
    "surf_shop": sporting_goods, "taffy_fudge": bakery, "ice_cream": cafe, "souvenir": variety_store, "t_shirts": clothing,
    "beachwear": clothing, "bike_rental": sporting_goods, "golf_cart_rental": auto_repair, "kayak_rental": sporting_goods,
    "bait_tackle": sporting_goods, "fish_market": butcher, "seafood_restaurant": diner, "raw_bar": bar,
    "boardwalk_fries": snack_stand, "pizza_slice": pizza, "tattoo": barber, "art_gallery": jeweler, "wine_bar": bar,
    "brewpub": bar, "marina_store": grocery, "restaurant": diner, "store": variety_store,
})


def fitout_for(business_type, rnd):
    fn = RECIPES.get(business_type, variety_store)

    def hook(house, room, p, against, rect, fz, cz):
        fn(Fit(house, room, p, against, rect, fz, cz, rnd))
    return hook
