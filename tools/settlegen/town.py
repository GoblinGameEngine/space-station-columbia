#!/usr/bin/env python3
"""
town.py -- a whole town laid out from the research rules (first use: Calder, the user's 2026-10-06 request: "a 1:1
scale city of 7,000 people ... an Elementary School, High School, Hospital, four properly sized strip malls in town
and three in the surrounding countryside ... a small downtown section with the Post Office, city hall, police
station and fire department").

What it follows (research/urban_layout/README.md "what the engine should be"; research/buildings/LOTS.md §5):
  * era bands (the user's decision 1): the town grows outward in bands, each with its own streets, lot widths,
    setbacks, alleys and parking -- rail-era core grid, streetcar and interwar extensions, postwar curvilinear
    loops, 1970s culs-de-sac, 1990s-2010s subdivisions. (The bands are styles and plats; the station's own history
    dates them -- research decision 2.)
  * plat by era, not by house: streets first, then lots along every frontage, then a building per lot
  * lot width and depth by band (LOTS.md §5.1), setbacks by band median +-20 % and the same along a block face
    (03_compatibility), side gaps at the code minimum, alleys in the old grid (LOTS.md §1)
  * uses by the research: commerce on Main Street and the highway frontage (02, space syntax), the depot and
    industry on the rail (07), schools at neighbourhood-unit spacing (02 Perry), shopping centres at arterial
    corners sized by catchment (07, tools/settlegen/centers.py), the hospital on the highway
  * deterministic: a pure function of (config, seed); the only outside input is `blocked(u, v)` (water)

Coordinates: metres in the town frame. u along Main Street, v across it (v = 0 on Main; the caller maps (u, v) to
the ring). Every lot is a polygon with its FRONT EDGE FIRST (the side on its street), the map inventory's
convention.

    plan = plan_town(cfg, rng, blocked)  ->  {"streets": [...], "lots": [...], "areas": [...], "marks": [...],
                                             "centres": [...], "stats": {...}}
"""
import math
import random

import centers as CT

FT = 0.3048
ROW = {"main": 24.0, "street": 20.0, "collector": 24.0, "drive": 18.0, "court": 16.0, "alley": 6.0}   # rights of way
CAR = {"main": "main", "street": "street", "collector": "street", "drive": "street", "court": "street", "alley": "alley"}

# lot rules per band (LOTS.md §2 measured, §5 rules): width range, depth, setback range, alley, token band
BANDS = {
    "rail":      dict(w=(15.0, 18.5), d=(40.0, 42.5), sb=(4.0, 6.0), alley=True, band="railroad_1860_1900", years=(1868, 1899)),
    "streetcar": dict(w=(12.0, 15.0), d=(38.0, 42.5), sb=(3.5, 5.0), alley=True, band="streetcar_1890_1930", years=(1895, 1929)),
    "interwar":  dict(w=(16.0, 20.0), d=(36.0, 40.0), sb=(5.5, 7.5), alley=False, band="interwar_1920_1945", years=(1922, 1942)),
    "postwar":   dict(w=(21.0, 25.0), d=(36.0, 41.0), sb=(8.0, 10.0), alley=False, band="postwar_1945_1965", years=(1947, 1964)),
    "suburban":  dict(w=(28.0, 38.0), d=(40.0, 48.0), sb=(10.0, 14.0), alley=False, band="suburban_1965_1990", years=(1966, 1989)),
    "late":      dict(w=(22.0, 27.0), d=(34.0, 38.0), sb=(7.5, 9.5), alley=False, band="late_1990_2010", years=(1991, 2009)),
    "current":   dict(w=(20.0, 23.0), d=(32.0, 35.0), sb=(6.0, 7.5), alley=False, band="current_2010_on", years=(2011, 2024)),
}


# ------------------------------------------------------------------ geometry
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _len(a):
    return math.hypot(a[0], a[1])


def densify(pts, step=4.0):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.ceil(_len(_sub(b, a)) / step)))
        for k in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
    return out


def arc(cu, cv, r, a0, a1, n=24):
    return [(cu + r * math.cos(a0 + (a1 - a0) * k / n), cv + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


def ellipse(cu, cv, a, b, n=48):
    return [(cu + a * math.cos(2 * math.pi * k / n), cv + b * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]


def rect(u0, u1, v0, v1):
    """A rectangle with its front edge first: the v0 side (put the street side at v0)."""
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def poly_area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


class Occupancy:
    """A 2 m raster of the town frame: streets' rights of way, the rail, lots and sites mark it; a new lot must find
    its cells free (the occupancy test keeps lots off each other at corners and on the inside of curves)."""
    def __init__(self, u0, u1, v0, v1, cell=2.0):
        import numpy as np
        from PIL import Image, ImageDraw
        self.np, self.Image, self.ImageDraw = np, Image, ImageDraw
        self.u0, self.v0, self.cell = u0, v0, cell
        self.W, self.H = int((u1 - u0) / cell) + 1, int((v1 - v0) / cell) + 1
        self.img = Image.new("L", (self.W, self.H), 0)
        self.dr = ImageDraw.Draw(self.img)
        self.arr = None

    def _px(self, p):
        return ((p[0] - self.u0) / self.cell, (p[1] - self.v0) / self.cell)

    def line(self, pts, width):
        self.arr = None
        # (PIL draws a line a cell wider than asked and off-centre: one cell less keeps the right of way true)
        self.dr.line([self._px(p) for p in pts], fill=255, width=max(1, int(round(width / self.cell)) - 1), joint="curve")
        for p in pts[:: max(1, len(pts) - 1)]:
            r = width / 2 / self.cell
            x, y = self._px(p)
            self.dr.ellipse([x - r, y - r, x + r, y + r], fill=255)

    def poly(self, poly):
        self.arr = None
        self.dr.polygon([self._px(p) for p in poly], fill=255)

    def free(self, poly, shrink=1.6):
        """All the polygon's cells free (shrunk 1.6 m: neighbours share their lot lines, and the raster's even-width
        lines sit a cell off-centre)."""
        np = self.np
        if self.arr is None:
            self.arr = np.asarray(self.img)
        cu = sum(p[0] for p in poly) / len(poly)
        cv = sum(p[1] for p in poly) / len(poly)
        q = []
        for p in poly:
            d = _sub(p, (cu, cv))
            L = _len(d) or 1.0
            q.append((p[0] - d[0] / L * shrink, p[1] - d[1] / L * shrink))
        xs = [self._px(p)[0] for p in q]
        ys = [self._px(p)[1] for p in q]
        x0, x1 = int(math.floor(min(xs))), int(math.ceil(max(xs)))
        y0, y1 = int(math.floor(min(ys))), int(math.ceil(max(ys)))
        if x0 < 0 or y0 < 0 or x1 >= self.W or y1 >= self.H:
            return False
        m = self.Image.new("L", (x1 - x0 + 1, y1 - y0 + 1), 0)
        self.ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in zip(xs, ys)], fill=1)
        mm = np.asarray(m) > 0
        return not bool((self.arr[y0:y1 + 1, x0:x1 + 1][mm] > 0).any())


# ------------------------------------------------------------------ the planner
class Planner:
    def __init__(self, cfg, rng, blocked):
        self.cfg, self.rng, self.blocked = cfg, rng, blocked
        u0, u1, v0, v1 = cfg["bounds"]
        self.bounds = cfg["bounds"]
        self.occ = Occupancy(u0 - 60, u1 + 60, v0 - 60, v1 + 60)
        self.streets, self.lots, self.areas, self.marks, self.centres = [], [], [], [], []
        self.face_rules = {}

    # --- network
    def street(self, pts, cls, name, smooth=False):
        pts = densify(pts, 3.0) if not smooth else densify(pts, 2.0)
        self.streets.append({"pts": pts, "cls": CAR[cls], "row": cls, "name": name})
        self.occ.line(pts, ROW[cls])
        return pts

    def site(self, poly, kind=None):
        self.occ.poly(poly)
        if kind:
            self.areas.append({"poly": poly, "kind": kind})

    def mark(self, u, v, text):
        self.marks.append(((u, v), text))

    # --- lots
    def inside(self, poly):
        u0, u1, v0, v1 = self.bounds
        return all(u0 <= p[0] <= u1 and v0 <= p[1] <= v1 for p in poly)

    def dry(self, poly):
        cu = sum(p[0] for p in poly) / len(poly)
        cv = sum(p[1] for p in poly) / len(poly)
        return not any(self.blocked(p[0], p[1]) for p in poly + [(cu, cv)])

    def lot(self, poly, use, band, **kw):
        e = dict(poly=poly, use=use, band=band)
        e.update(kw)
        self.lots.append(e)
        self.occ.poly(poly)
        return e

    def frontage(self, pts, side, bandk, row, use_fn=None, depth=None, sb=None, face=None, start=6.0, end=6.0,
                 width_fn=None, max_lots=None, extra=None, on_lot=None):
        """Lots along one side of a street polyline (side +1: left of its direction, -1 right). Each lot's front
        edge sits on the right-of-way line; widths from the band, the setback the same along the face
        (03_compatibility: a block face keeps one setback, +-0.5 m)."""
        B = BANDS[bandk]
        rng = self.rng
        P = densify(pts, 1.0)
        cum = [0.0]
        for a, b in zip(P, P[1:]):
            cum.append(cum[-1] + _len(_sub(b, a)))
        total = cum[-1]
        face_sb = sb if sb is not None else rng.uniform(*B["sb"])
        dep = depth if depth is not None else rng.uniform(*B["d"])
        off = ROW[row] / 2
        out = []
        t = start
        k = 0

        def at(dist):
            i = min(len(P) - 2, max(0, next((j for j in range(len(cum) - 1) if cum[j + 1] >= dist), len(P) - 2)))
            a, b = P[i], P[i + 1]
            f = (dist - cum[i]) / max(1e-6, cum[i + 1] - cum[i])
            p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            # the tangent over +-6 m (smooth on curves)
            ia = max(0, i - 6)
            ib = min(len(P) - 1, i + 7)
            tv = _sub(P[ib], P[ia])
            L = _len(tv) or 1.0
            return p, (tv[0] / L, tv[1] / L)
        while t < total - end:
            use = use_fn(k) if use_fn else "house"
            if use is None:                      # (a list of uses that has run out: the frontage ends)
                break
            w = width_fn(k) if width_fn else (rng.uniform(*USE_W[use]) if use in USE_W else rng.uniform(*B["w"]))
            if t + w > total - end:
                break
            p, tg = at(t + w / 2)
            nrm = (-tg[1] * side, tg[0] * side)
            fa = (p[0] + nrm[0] * off - tg[0] * w / 2, p[1] + nrm[1] * off - tg[1] * w / 2)
            fb = (p[0] + nrm[0] * off + tg[0] * w / 2, p[1] + nrm[1] * off + tg[1] * w / 2)
            d0 = dep * rng.uniform(0.96, 1.04) if depth is None else dep
            poly = None
            # a lot that doesn't fit at its band's depth is made shallower (down to 22 m) before it's given up:
            # squeezed blocks get shallow lots, as real plats do between converging streets
            for d in (d0, d0 * 0.86, d0 * 0.74, d0 * 0.62):
                if d < 22.0 and d < d0:
                    break
                ca = (fb[0] + nrm[0] * d, fb[1] + nrm[1] * d)
                cb = (fa[0] + nrm[0] * d, fa[1] + nrm[1] * d)
                # front edge first, ordered so the front faces the street (left-to-right as seen from it)
                q = [fa, fb, ca, cb] if side > 0 else [fb, fa, cb, ca]
                if self.inside(q) and self.dry(q) and self.occ.free(q):
                    poly = q
                    break
            if poly is not None:
                e = self.lot(poly, use, bandk, setback=round(min(face_sb, d * 0.3) + rng.uniform(-0.5, 0.5), 2), depth=round(d, 1),
                             width=round(w, 1), face=face, **(extra or {}))
                if use in UNITS:
                    e["units"] = UNITS[use]
                if on_lot:
                    on_lot(e)
                out.append(e)
                k += 1
                t += w
                if max_lots and k >= max_lots:
                    break
            else:
                t += 2.0
        return out


USE_W = {"townhouse": (40.0, 46.0), "duplex": (16.0, 20.0), "apartment": (48.0, 56.0)}   # frontage a multi-unit lot takes
UNITS = {"townhouse": 6, "apartment": 12}


def _both(pl, pts, bandk, row, **kw):
    a = pl.frontage(pts, 1, bandk, row, **kw)
    b = pl.frontage(pts, -1, bandk, row, **kw)
    return a + b


# ------------------------------------------------------------------ the town
def wavy(u0, u1, v, amp, wl, ph, step=20.0):
    """A gently curving street along u (postwar and later tracts: FHA 'curvilinear' streets, 05 Boeing's eras)."""
    n = max(2, int((u1 - u0) / step))
    return [(u0 + (u1 - u0) * k / n, v + amp * math.sin(2 * math.pi * (u0 + (u1 - u0) * k / n) / wl + ph)) for k in range(n + 1)]


def plan_town(cfg, rng=None, blocked=lambda u, v: False):
    rng = rng or random.Random(cfg.get("seed", 1))
    pl = Planner(cfg, rng, blocked)
    N = cfg["names"]
    rail_v = cfg["rail_v"]                   # v of the railway's centreline at u
    U0, U1, V0, V1 = cfg["bounds"]
    G0 = cfg["grid_u0"]
    # 300 ft blocks between the street lines (LOTS §1: the chain plat): 300 + 66 ft = 112 m centre to centre, so a
    # half-block lot is 125 ft (38-43 m) deep behind a 66 ft street and on a 16-20 ft alley
    BK = 112.0
    us = [G0 + BK * k for k in range(-3, 6)]          # -470 .. 426 for G0 = -134
    vn = [BK * k for k in range(6)]                   # Main (0) .. 560
    two_flat = lambda p_dup, p_flat: (lambda k: "duplex" if rng.random() < p_dup else ("two_flat" if rng.random() < p_flat else "house"))

    # ================= phase 1: the network, the rail, the big sites =================
    rail_pts = [(u, rail_v(u)) for u in range(int(U0) - 60, int(U1) + 61, 10)]
    pl.occ.line(rail_pts, 26.0)
    pl.street([(U0 - 40, 0), (U1 + 40, 0)], "main", N["main"])          # Main Street: US 30 through the town
    # the old town (north of Main): the rail-era plat
    for i, v in enumerate(vn[1:], 1):
        pl.street([(us[0], v), (us[-1], v)], "street", N["north_streets"][i - 1])
    for i, u in enumerate(us):
        pl.street([(u, 0), (u, vn[-1])], "street", N["cross"][i])
    for v in vn[:-1]:
        for a, b in zip(us, us[1:]):
            pl.street([(a, v + BK / 2), (b, v + BK / 2)], "alley", "")
    # the interwar wings: the plat carried on past the old town at both ends, behind the highway centres
    ww = [us[0] - 2 * BK, us[0] - BK]
    we = [us[-1] + BK * k for k in range(1, 6)]
    for v in vn[2:]:
        pl.street([(ww[0], v), (us[0], v)], "street", N["north_streets"][int(round(v / BK)) - 1])
    for v in vn[3:]:
        pl.street([(us[-1], v), (we[-1], v)], "street", N["north_streets"][int(round(v / BK)) - 1])
    for j, u in enumerate(ww):
        pl.street([(u, vn[2]), (u, vn[-1])], "street", N["cross_w"][j])
    for j, u in enumerate(we):
        pl.street([(u, vn[3]), (u, vn[-1])], "street", N["cross_e"][j])
    # the bluff: a collector along the top, courts toward the view
    ridge = densify([(U0 + 30, 640.0), (G0, 636.0), (U1 - 30, 642.0)], 20.0)
    pl.street(ridge, "collector", N["ridge"])
    pl.street([(G0, vn[-1]), (G0, V1 + 40)], "collector", N["north_road"])
    for u in (us[0], us[-1], ww[0], we[-1]):
        pl.street([(u, vn[-1]), (u, 638.0)], "street", "")
    # the South Side: Railroad Ave along the tracks, the workers' grid behind it
    vs_s = [-175.0, -287.0, -399.0]
    for i, v in enumerate(vs_s):
        pl.street([(us[0], v), (us[-1], v)], "street", N["south_streets"][i])
    for i, u in enumerate(us):
        if u != G0:
            pl.street([(u, vs_s[0]), (u, vs_s[-1])], "street", N["cross"][i])
    for v in vs_s[1:]:
        for a, b in zip(us, us[1:]):
            pl.street([(a, v + BK / 2), (b, v + BK / 2)], "alley", "")
    # Calder Road (the section line) from Main across the tracks to the coast; the collectors round the town
    pl.street([(G0, 0), (G0, V0 - 40)], "collector", N["south_road"])
    south = densify([(U0 + 30, -650.0), (G0, -650.0), (U1 - 30, -650.0)], 20.0)
    pl.street(south, "collector", N["south_collector"])
    pl.street([(U0 + 30, 0.0), (U0 + 30, V0 + 20)], "collector", N["west_road"])
    pl.street([(U1 - 30, 0.0), (U1 - 30, V0 + 20)], "collector", N["east_road"])
    # postwar tracts: curving streets between the South Side and Southview Dr, and on its west and east ends
    post = []
    for k, (u0_, u1_, v_) in enumerate(((us[0], us[-1], -500.0), (us[0], us[-1], -590.0),
                                       (U0 + 30, us[0], -170.0), (U0 + 30, us[0], -265.0))):
        pts = wavy(u0_, u1_, v_, 9.0, 340.0, k * 1.3)
        post.append(pl.street(pts, "drive", N["loops"][k]))
    for u in (us[1], us[3] + BK, us[5], us[7]):
        pl.street([(u, vs_s[-1]), (u, -650.0)], "drive", "")
    pl.street([(U0 + 30 + 120, -100.0), (U0 + 30 + 120, -380.0)], "drive", N["loops"][4])
    # 1990s-2010s subdivisions beyond Southview Dr: curving parallels, collectors' links, a court at each end
    late = []
    for k, v_ in enumerate((-745.0, -840.0, -935.0, -1030.0)):
        pts = wavy(U0 + 30, U1 - 30, v_, 14.0, 420.0, 0.7 * k)
        late.append(pl.street(pts, "drive", N["late_streets"][k]))
    for u in (U0 + 260, G0 + 300, G0 + 640, U1 - 220):
        pl.street([(u, -650.0), (u, -1030.0)], "drive", "")
    # sites that stand apart from the plat
    hu0, hu1 = U1 - 175, U1 - 45                           # the hospital campus on US 30 at the east entry
    pl.site(rect(hu0, hu1, 13, 300), "campus")
    eu0 = U0 + 60                                           # the elementary school's grounds (Perry: the unit's centre)
    pl.site(rect(eu0, eu0 + 200, -330, -560), "schoolground")
    hs0 = us[-1] + 140                                      # the high school campus: buildings, stadium, fields
    pl.site(rect(hs0, U1 - 45, -150, -620), "schoolground")
    # the shopping centres in town (07): the community centre and the neighbourhood centre on US 30 at the two
    # entries (the strongest frontage -- 02 bid-rent, space syntax); convenience strips at collector corners
    def centre(kind, u0, u1, v_road, dirn, name, row, depth_max=None):
        d = CT.strip_site(kind, rng)[1]
        if depth_max:
            d = min(d, depth_max)
        site = CT.Site(u0, u1, ROW[row] / 2, ROW[row] / 2 + d, None)
        plan = CT.strip_center(site, kind, rng)
        pl.occ.poly(rect(u0, u1, v_road + dirn * site.v0, v_road + dirn * site.v1))
        pl.centres.append({"name": name, "kind": kind, "plan": plan, "v_road": v_road, "dirn": dirn, "u": (u0, u1)})
        pl.mark((u0 + u1) / 2, v_road + dirn * (site.v1 + 6), name)
    centre("community", us[-1] + 14, hu0 - 14, 0.0, 1, N["centres"][0], "main", depth_max=BK * 3 - 40)
    centre("neighborhood", U0 + 45, us[0] - 14, 0.0, 1, N["centres"][1], "main", depth_max=BK * 2 - 24)
    centre("convenience", G0 + 14, G0 + 104, -650.0, -1, N["centres"][2], "collector")
    centre("convenience", G0 + 14, G0 + 104, 636.0, -1, N["centres"][3], "collector")

    # ================= phase 2: the civic heart, downtown, the institutions =================
    civ = {}
    cu0, cu1 = us[3], us[4]                                 # the block behind Main at the section line
    sq = rect(cu0 + 10, cu1 - 10, BK + 10, 2 * BK - 10)
    pl.areas.append({"poly": sq, "kind": "square"})
    pl.occ.poly(sq)
    civ["city_hall"] = pl.lot(rect(cu0 + 24, cu1 - 24, BK + 30, BK + 72), "city_hall", "rail", label="City Hall", setback=8.0)
    pl.mark((cu0 + cu1) / 2, 1.5 * BK, N["square"])
    # police and fire on the block east of the square, facing the cross street (fire: its apron to the street)
    civ["police"] = pl.lot([(cu1 + 10, BK + 12), (cu1 + 10, BK + 46), (cu1 + 46, BK + 46), (cu1 + 46, BK + 12)], "police",
                           "interwar", label="Police Station", setback=3.0)
    civ["fire"] = pl.lot([(cu1 + 10, BK + 58), (cu1 + 10, BK + 100), (cu1 + 50, BK + 100), (cu1 + 50, BK + 58)], "fire_station",
                         "interwar", label="Fire Department", setback=9.0)
    # the post office and the library on the block west of the square
    civ["post_office"] = pl.lot([(cu0 - 10, BK + 12), (cu0 - 10, BK + 50), (cu0 - 50, BK + 50), (cu0 - 50, BK + 12)],
                                "post_office", "interwar", label="Post Office", setback=6.0)
    civ["library"] = pl.lot([(cu0 - 10, BK + 60), (cu0 - 10, BK + 98), (cu0 - 46, BK + 98), (cu0 - 46, BK + 60)], "library",
                            "streetcar", label="Library", setback=6.0)
    # the depot on the tracks at the foot of Calder Ave, the elevator up the line
    dv = rail_v(G0 + 50) + 20
    civ["depot"] = pl.lot(rect(G0 + 22, G0 + 76, dv, dv + 13), "depot", "rail", label="Depot", setback=2.0)
    ev = rail_v(us[1]) - 20
    civ["elevator"] = pl.lot([(us[1] - 40, ev), (us[1] + 30, ev), (us[1] + 30, ev - 32), (us[1] - 40, ev - 32)], "elevator", "rail",
                             label="Grain Elevator", setback=0.0)
    # downtown: two-part blocks on both sides of Main for four blocks, built to the lot line with party walls
    dt = [us[2], us[3], us[4], us[5], us[6]]
    widths = lambda k: rng.choice((7.6, 7.6, 7.6, 9.1, 9.1, 12.2, 12.2, 15.2))
    for a, b in zip(dt, dt[1:]):
        pl.frontage([(a, 0.0), (b, 0.0)], 1, "rail", "main", use_fn=lambda k: "store", depth=28.0, sb=0.0, start=10.5, end=10.5,
                    width_fn=widths, face="main_n")
        pl.frontage([(b, 0.0), (a, 0.0)], 1, "rail", "main", use_fn=lambda k: "store", depth=26.0, sb=0.0, start=10.5, end=10.5,
                    width_fn=widths, face="main_s")
    # churches on corners near the centre
    for (u, v, sg) in ((us[2], 2 * BK, 1), (us[5], 3 * BK, -1), (us[1], BK, 1), (us[6], 4 * BK, -1), (us[5], vs_s[0], 1),
                       (us[7], 2 * BK, 1))[:cfg.get("churches", 6)]:
        v0_ = v + 11 if v > 0 else v - 11
        poly = rect(u + 11, u + 43, v0_, v0_ + (40 if v > 0 else -40)) if sg > 0 else rect(u - 43, u - 11, v0_, v0_ + (40 if v > 0 else -40))
        if pl.occ.free(poly):
            pl.lot(poly, "church", "rail", setback=6.0)
    wt = rect(us[1] + 16, us[1] + 42, 4 * BK + 14, 4 * BK + 40)
    if pl.occ.free(wt):
        pl.lot(wt, "water_tower", "interwar", label="Water Tower", setback=0.0)
    # the hospital: the main block, a later wing, the clinic, parking (a community hospital, 25-50 beds)
    pl.areas.append({"poly": rect(hu0 + 4, hu1 - 4, 18, 70), "kind": "parking"})
    pl.lot(rect(hu0 + 20, hu0 + 82, 84, 128), "hospital", "suburban", label=N["hospital"], setback=14.0)
    pl.lot(rect(hu0 + 20, hu0 + 72, 136, 170), "hospital_wing", "late", label=N["hospital"] + " (east wing)", setback=0.0)
    pl.lot(rect(hu0 + 20, hu0 + 70, 184, 220), "clinic", "late", label=N["clinic"], setback=0.0)
    pl.areas.append({"poly": rect(hu0 + 90, hu1 - 6, 84, 290), "kind": "parking"})
    pl.mark(hu0 + 65, 106, N["hospital"])
    # the elementary school and the high school
    pl.lot(rect(eu0 + 20, eu0 + 100, -352, -400), "elementary", "postwar", label=N["elementary"], setback=16.0)
    pl.areas.append({"poly": rect(eu0 + 115, eu0 + 192, -345, -550), "kind": "sportsfield"})
    pl.mark(eu0 + 60, -380, N["elementary"])
    pl.lot(rect(hs0 + 20, hs0 + 92, -175, -222), "high_school", "suburban", label=N["high_school"], setback=22.0)
    pl.lot(rect(hs0 + 102, hs0 + 164, -175, -217), "high_school_wing", "suburban", label=N["high_school"] + " (arts and trades)", setback=22.0)
    pl.lot(rect(hs0 + 20, hs0 + 80, -232, -272), "fieldhouse", "suburban", label=N["high_school"] + " Fieldhouse", setback=0.0)
    pl.areas.append({"poly": rect(hs0 + 180, U1 - 55, -165, -345), "kind": "sportsfield"})       # the stadium and track
    pl.areas.append({"poly": rect(hs0 + 20, hs0 + 170, -290, -470), "kind": "sportsfield"})      # baseball and softball
    pl.areas.append({"poly": rect(hs0 + 180, U1 - 55, -360, -470), "kind": "sportsfield"})       # practice fields
    pl.areas.append({"poly": rect(hs0 + 20, U1 - 55, -485, -610), "kind": "parking"})
    pl.mark(hs0 + 90, -200, N["high_school"])
    # the town park on the old grid, the cemetery at the west edge, the manufactured-home park by the tracks
    park = rect(us[6] + 10, us[7] - 10, 3 * BK + 10, 4 * BK - 10)
    if pl.occ.free(park):
        pl.site(park, "park")
        pl.mark((us[6] + us[7]) / 2, 3.5 * BK, N["park"])
    cem = rect(ww[0] + 10, us[0] - 10, 4 * BK + 10, 5 * BK - 10)
    if pl.occ.free(cem):
        pl.site(cem, "cemetery")
        pl.mark((ww[0] + us[0]) / 2, 4.5 * BK, N["cemetery"])

    # ================= phase 3: the plats, band by band =================
    # the old town north of Main: rail band near the centre, streetcar beyond; a share of old houses are doubles or
    # two-flats (the town's earliest rentals, 03 filtering)
    for v in vn[1:]:
        for a, b in zip(us, us[1:]):
            bandk = "rail" if abs((a + b) / 2 - G0) < 2.2 * BK and v <= 2 * BK else "streetcar"
            dep = BK / 2 - ROW["street"] / 2 - ROW["alley"] / 2 - 0.6
            pl.frontage([(a, v), (b, v)], 1, bandk, "street", start=10.5, end=10.5, face=f"n{v}:{a}", use_fn=two_flat(0.12, 0.08), depth=dep)
            pl.frontage([(b, v), (a, v)], 1, bandk, "street", start=10.5, end=10.5, face=f"s{v}:{a}", use_fn=two_flat(0.12, 0.08), depth=dep)
    for u in us:
        pl.frontage([(u, 0), (u, vn[-1])], 1, "streetcar", "street", start=10.5, end=10.5, depth=28.0)
        pl.frontage([(u, vn[-1]), (u, 0)], 1, "streetcar", "street", start=10.5, end=10.5, depth=28.0)
    # the South Side: rail works along Railroad Ave (backing onto the tracks), workers' houses behind
    for a, b in zip(us, us[1:]):
        dep = max(24.0, min(60.0, (rail_v((a + b) / 2) - 14) - (vs_s[0] + ROW["street"] / 2)))
        pl.frontage([(b, vs_s[0]), (a, vs_s[0])], -1, "rail", "street", use_fn=lambda k: "works", depth=dep,
                    sb=6.0, start=10.5, end=10.5, width_fn=lambda k: rng.uniform(34, 56))
    for v in vs_s:
        for a, b in zip(us, us[1:]):
            if v != vs_s[0]:
                pl.frontage([(a, v), (b, v)], 1, "streetcar", "street", start=10.5, end=10.5, use_fn=two_flat(0.1, 0.06),
                            depth=BK / 2 - ROW["street"] / 2 - ROW["alley"] / 2 - 0.6)
            pl.frontage([(b, v), (a, v)], 1, "streetcar", "street", start=10.5, end=10.5, use_fn=two_flat(0.1, 0.06),
                        depth=BK / 2 - ROW["street"] / 2 - ROW["alley"] / 2 - 0.6)
    for u in us:
        pl.frontage([(u, vs_s[0]), (u, vs_s[-1])], 1, "streetcar", "street", start=10.5, end=10.5, depth=28.0)
        pl.frontage([(u, vs_s[-1]), (u, vs_s[0])], 1, "streetcar", "street", start=10.5, end=10.5, depth=28.0)
    # the interwar wings
    for v in vn[2:]:
        for a, b in zip(ww + [us[0]], ww[1:] + [us[0]]):
            if a < b:
                pl.frontage([(a, v), (b, v)], 1, "interwar", "street", start=10.5, end=10.5, depth=BK / 2 - ROW["street"] / 2 - 0.6)
                pl.frontage([(b, v), (a, v)], 1, "interwar", "street", start=10.5, end=10.5, depth=BK / 2 - ROW["street"] / 2 - 0.6)
    for v in vn[3:]:
        for a, b in zip([us[-1]] + we, we):
            pl.frontage([(a, v), (b, v)], 1, "interwar", "street", start=10.5, end=10.5, depth=BK / 2 - ROW["street"] / 2 - 0.6)
            pl.frontage([(b, v), (a, v)], 1, "interwar", "street", start=10.5, end=10.5, depth=BK / 2 - ROW["street"] / 2 - 0.6)
    for u in ww + we + [us[0], us[-1]]:
        pl.frontage([(u, 0), (u, vn[-1])], 1, "interwar", "street", start=10.5, end=10.5, depth=32.0)
        pl.frontage([(u, vn[-1]), (u, 0)], 1, "interwar", "street", start=10.5, end=10.5, depth=32.0)
    # the bluff: suburban lots on the collector, both sides, the north side's backs to the woods
    pl.frontage(list(reversed(ridge)), 1, "suburban", "collector", start=12.0, end=12.0, depth=40.0)
    pl.frontage(ridge, 1, "suburban", "collector", start=12.0, end=12.0, depth=36.0)
    # garden apartments and town houses (one common parcel each, no inner lot lines -- LOTS §5.6) where the
    # collectors meet: the apartments' share of the housing (02, 01 missing middle)
    apts = 0
    for (u0_, v0_, kind, n_b, units, label) in ((G0 + 20, -662.0, "apartment", 4, 16, N["apartments"]),
                                                 (G0 - 210, -662.0, "townhouse", 4, 6, N["townhouses"]),
                                                 (U0 + 60, -662.0, "apartment", 4, 16, N["apartments2"]),
                                                 (G0 + 340, -662.0, "apartment", 3, 24, N["seniors"]),
                                                 (us[-1] + 20, -662.0, "townhouse", 4, 6, N["townhouses2"])):
        w_ = n_b * 44.0 + 10
        site_ = rect(u0_, u0_ + w_, v0_, v0_ - 70)
        if not pl.occ.free(site_):
            continue
        pl.site(site_, "lawn")
        for k in range(n_b):
            ua = u0_ + 6 + k * 44
            pl.lots.append(dict(poly=rect(ua, ua + 38, v0_ - 8, v0_ - 34), use=kind, band="suburban" if kind == "apartment" else "current",
                                setback=0.0, units=units))
            apts += units
        pl.areas.append({"poly": rect(u0_ + 4, u0_ + w_ - 4, v0_ - 42, v0_ - 66), "kind": "parking"})
        pl.mark(u0_ + w_ / 2, v0_ - 20, label)
    # the postwar tracts
    for pts in post:
        pl.frontage(pts, 1, "postwar", "drive", start=12.0, end=12.0)
        pl.frontage(list(reversed(pts)), 1, "postwar", "drive", start=12.0, end=12.0)
    # the late subdivisions (late band near Southview, current at the town's edge)
    # (the newest streets mix town-house rows in with the houses: the 2010s' missing-middle infill, 01)
    for k, pts in enumerate(late):
        bandk = "late" if k < 2 else "current"
        p_th = cfg.get("townhouse_share", {}).get(bandk, 0.0)
        p_ap = cfg.get("apartment_share", {}).get(bandk, 0.0)
        uf = (lambda p, q: (lambda j: (lambda r: "apartment" if r < q else ("townhouse" if r < q + p else "house"))(rng.random())))(p_th, p_ap)
        pl.frontage(pts, 1, bandk, "drive", start=12.0, end=12.0, use_fn=uf)
        pl.frontage(list(reversed(pts)), 1, bandk, "drive", start=12.0, end=12.0, use_fn=uf)
    # garden apartments on the ground between Main and the tracks east of downtown (cheap land beside the rail: 02
    # bid-rent's nuisance discount), two rows of buildings round a parking court
    ue0 = us[6] + 230
    ue1 = U1 - 190
    vb = max(rail_v(ue0), rail_v(ue1)) + 16
    if ue1 - ue0 > 120 and -14 - vb > 70:
        site_ = rect(ue0, ue1, -14, vb)
        if pl.occ.free(site_):
            pl.site(site_, "lawn")
            nb = int((ue1 - ue0 - 10) / 46)
            for k in range(nb):
                ua = ue0 + 8 + k * 46
                for (va, vb_) in ((-22, -46), (vb + 26, vb + 2)):
                    pl.lots.append(dict(poly=rect(ua, ua + 38, va, vb_), use="apartment", band="suburban", setback=0.0, units=12))
            pl.areas.append({"poly": rect(ue0 + 4, ue1 - 4, -52, vb + 32), "kind": "parking"})
            pl.mark((ue0 + ue1) / 2, (vb - 14) / 2, N["apartments3"])
    # every remaining collector frontage
    for pts_ in (south, list(reversed(south))):
        pl.frontage(pts_, 1, "postwar", "collector", start=12.0, end=12.0)
    for (pts_, bandk) in (([(G0, vs_s[-1]), (G0, -650.0)], "postwar"), ([(G0, -650.0), (G0, V0 + 20)], "late"),
                          ([(U0 + 30, -20.0), (U0 + 30, V0 + 20)], "postwar"), ([(U1 - 30, -20.0), (U1 - 30, V0 + 20)], "postwar")):
        pl.frontage(pts_, 1, bandk, "collector", start=12.0, end=12.0)
        pl.frontage(list(reversed(pts_)), 1, bandk, "collector", start=12.0, end=12.0)
    # the highway frontage that's left: pads, a motel, gas, a bank, a funeral home (each once or twice)
    hwy_list = ["gas_station", "fast_food", "bank", "auto_repair", "motel", "funeral_home", "diner", "farm_supply",
                "car_wash", "fast_food", "gas_station", "insurance", "auto_parts", "tavern"]
    hwy_n = [0]

    def hwy_uses_at(k):
        return hwy_list[hwy_n[0]] if hwy_n[0] < len(hwy_list) else None
    for pts_ in ([(U0 + 30, 0), (dt[0], 0)], [(dt[-1], 0), (U1 - 30, 0)]):
        for side_pts in (pts_, list(reversed(pts_))):
            got = pl.frontage(side_pts, 1, "postwar", "main", use_fn=hwy_uses_at, depth=42.0, sb=12.0, start=12.0, end=12.0,
                              width_fn=lambda k: rng.uniform(30, 44), max_lots=max(0, len(hwy_list) - hwy_n[0]) or 1,
                              on_lot=lambda e: hwy_n.__setitem__(0, hwy_n[0] + 1))
    pl.lots = [l for l in pl.lots if not (l["use"] == "house" and l.get("face") is None and l["band"] == "postwar"
                                           and abs(sum(p[1] for p in l["poly"]) / 4) < 60 and abs(sum(p[1] for p in l["poly"][:2]) / 2) < 14)]
    pl.stats = stats(pl)
    return {"streets": pl.streets, "lots": pl.lots, "areas": pl.areas, "marks": pl.marks, "centres": pl.centres,
            "stats": pl.stats, "civic": civ}


# ------------------------------------------------------------------ the countryside centres
def country_centre(kind, name, rng):
    """A centre on a rural crossroads (the plan in its own frame: u along the frontage road, v away from it)."""
    w, d = CT.strip_site(kind, rng)
    site = CT.Site(-w / 2, w / 2, ROW["collector"] / 2, ROW["collector"] / 2 + d, "u0")
    return {"name": name, "kind": kind, "plan": CT.strip_center(site, kind, rng)}


# ------------------------------------------------------------------ the numbers
HH = {"house": 1, "duplex": 2, "two_flat": 2, "apartment": 12, "townhouse": 6, "store": 1}
HH_SIZE = 2.4             # persons per household (a Midwestern small town)


def stats(pl):
    from collections import Counter
    c = Counter(l["use"] for l in pl.lots)
    units = 0
    for l in pl.lots:
        if l["use"] in ("house", "duplex", "two_flat"):
            units += HH.get(l["use"], 1)
        elif l["use"] in ("apartment", "townhouse"):
            units += l.get("units", HH[l["use"]])
        elif l["use"] == "store":
            units += 2                                 # (two flats over each downtown store: the upper floors' use)
    by_band = Counter(l["band"] for l in pl.lots if l["use"] == "house")
    return {"lots": len(pl.lots), "uses": dict(c), "dwelling_units": units, "population_est": round(units * HH_SIZE),
            "houses_by_band": dict(by_band), "streets": len(pl.streets),
            "street_km": round(sum(sum(_len(_sub(b, a)) for a, b in zip(s["pts"], s["pts"][1:])) for s in pl.streets) / 1000, 1)}
