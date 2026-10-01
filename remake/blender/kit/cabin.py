"""kit.cabin -- an EXTRAPOLATED interior for an enclosed vehicle (car, van, truck cab, machine cab, boat
cabin) built from its exterior references alone, with no Grok interior views (the user's call,
2026-09-30: "extrapolate interiors... if we don't like it we can use grok again"). Vehicles with
Grok interior views go through kit.transit instead.

From the side view's detected windows: the beltline (the windows' bottom), the cabin's length, the
windscreen (forward from the front window until the roof line drops to the beltline) and the rear
window (the same, backwards). Then:
  - the hull is hollowed under the roof line from the floor to the windscreen (over the wheels the
    floor rises clear of the arches), and its inside faces lined;
  - the side windows, windscreen and rear window are cut open and glazed (tinted glass);
  - inside: carpet, seats in rows to the vehicle's seat count (cushion, raked back, headrest, pleated
    upholstery), a dash with a gauge panel, and the steering wheel on the left (traffic keeps right);
  - markers seat_driver, seat_<n> (a sitter's hips, facing +Y).
Colours: a 1970s scheme per vehicle (tan, ox-blood, navy, avocado, charcoal), grey vinyl for work
vehicles. Textures (pleats, gauges, carpet) are drawn here in numpy.

Without usable windows the plain hull is built (logged INTERIOR none).
"""
import hashlib
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import core, hull

SHELL = 0.06
SCHEMES = {
    "tan": dict(seat=(176, 140, 96), liner=(226, 215, 192), dash=(92, 72, 54), carpet=(112, 90, 66)),
    "oxblood": dict(seat=(124, 42, 42), liner=(222, 208, 192), dash=(62, 32, 32), carpet=(84, 42, 40)),
    "navy": dict(seat=(54, 66, 106), liner=(212, 214, 222), dash=(42, 48, 72), carpet=(52, 60, 86)),
    "avocado": dict(seat=(114, 122, 58), liner=(226, 220, 192), dash=(72, 74, 42), carpet=(86, 90, 50)),
    "charcoal": dict(seat=(58, 58, 62), liner=(204, 204, 200), dash=(42, 42, 44), carpet=(62, 62, 64)),
    "vinyl": dict(seat=(92, 96, 100), liner=(196, 198, 196), dash=(52, 54, 56), carpet=(70, 72, 74)),
}
CAR = ["tan", "oxblood", "navy", "avocado", "charcoal"]
NO_CABIN = {"motorcycle", "scooter_moped", "mobility_scooter", "excavator"}   # open machines; the excavator's cut wrecked it
WORK = {"commercial", "farm", "industry", "emergency", "civic", "rail", "station"}


def scheme_for(an):
    if an.get("category", "") in WORK:
        return "vinyl"
    h = int(hashlib.md5(an["id"].encode()).hexdigest(), 16)
    return CAR[h % len(CAR)]


# -- textures (sRGB 0..1, numpy) ---------------------------------------------------------------------
def _rgba(c, a=1.0):
    return np.array([c[0] / 255, c[1] / 255, c[2] / 255, a], np.float32)


def tex_pleats(name, col):
    w = h = 64
    x = np.arange(w)[None, :].repeat(h, 0)
    shade = 0.86 + 0.14 * np.cos(2 * np.pi * x / 16.0)
    shade[:, (x[0] % 16) == 0] *= 0.7                      # the stitched seams
    img = np.ones((h, w, 4), np.float32) * _rgba(col)
    img[..., :3] *= shade[..., None]
    img[:6, :, :3] *= 0.8                                   # a welt along the top
    return core.image(name, w, h, img)


def tex_carpet(name, col):
    rng = np.random.default_rng(7)
    w = h = 64
    n = rng.normal(1.0, 0.07, (h, w)).astype(np.float32)
    img = np.ones((h, w, 4), np.float32) * _rgba(col)
    img[..., :3] *= n[..., None]
    return core.image(name, w, h, np.clip(img, 0, 1))


def tex_gauges(name, col):
    w, h = 128, 64
    img = np.ones((h, w, 4), np.float32) * _rgba(col)
    img[..., :3] *= 0.6
    yy, xx = np.mgrid[0:h, 0:w]
    for cx in (34, 94):
        r = np.hypot(xx - cx, yy - 32)
        img[r < 24] = _rgba((236, 228, 206))               # the dial
        img[(r > 22) & (r < 24.5)] = _rgba((180, 170, 140))  # chrome bezel
        ang = np.arctan2(yy - 32, xx - cx)
        for k in range(9):                                  # ticks
            a = math.radians(210 - k * 30)
            m = (r > 17) & (r < 21) & (np.abs(np.angle(np.exp(1j * (ang + a)))) < 0.05)
            img[m] = _rgba((40, 40, 40))
        t = np.linspace(0, 16, 40)
        a = math.radians(130 if cx < 64 else 200)
        for tt in t:                                        # the needle
            px, py = int(cx + tt * math.cos(a)), int(32 - tt * math.sin(a))
            img[max(0, py - 1):py + 1, max(0, px - 1):px + 1] = _rgba((200, 60, 30))
    img = img[::-1]                                         # Blender images start at the bottom row
    return core.image(name, w, h, img)


# -- build -----------------------------------------------------------------------------------------
def build(an, out_glb, render_prefix=None):
    aid = an["id"]
    L, W, H = an["size_m"]
    sv = an["views"]["side"]
    outline = [tuple(p) for p in sv["outline_m"]]
    ys = [p[0] for p in outline]
    ymin, ymax = min(ys), max(ys)

    # the hull is the side view cut by the front and rear views: its roof is never above theirs
    ends = [an["views"][v] for v in ("front", "rear") if v in an["views"] and an["views"][v].get("outline_m")]
    view_top = min([max(p[1] for p in e["outline_m"]) for e in ends] or [99.0])
    roof_cap = [99.0]

    def roof(y):
        """The roof line without things on the roof (a taxi sign, a beacon, an exhaust stack): never
        more than a little above the top of the windows."""
        return min(_top(y), roof_cap[0], view_top)

    def _top(y):
        return min(_top_side(y), view_top)

    def _top_side(y):
        best = None
        for (y0, z0), (y1, z1) in zip(outline, outline[1:] + outline[:1]):
            if (y0 - y) * (y1 - y) <= 0 and y0 != y1:
                z = z0 + (z1 - z0) * (y - y0) / (y1 - y0)
                best = z if best is None else max(best, z)
        return best if best is not None else 0.0

    wins = [w for w in sv.get("windows_m", []) if w[1] - w[0] > 0.15 and w[3] - w[2] > 0.12]
    if wins:                                                # the main window line: bottoms near the median
        z0s = sorted(w[2] for w in wins)
        med = z0s[len(z0s) // 2]
        wins = [w for w in wins if abs(w[2] - med) < 0.35 and w[2] > H * 0.3]
    if not wins and an.get("seats", 0) >= 1 and H < 2.3 and an.get("category", "") in ("household", "emergency", "commercial", "civic"):
        # none drawn clearly enough to find: extrapolate the glass from the shape -- the beltline at 60%
        # of the roof's height, side windows along the roof's plateau, split by a B-pillar if long
        # the roof: the highest level held for 1.2 m (a light bar or sign on it doesn't count)
        top = max(min(_top(ymin + (ymax - ymin) * k / 200 - 0.6), _top(ymin + (ymax - ymin) * k / 200 + 0.6)) for k in range(201))
        plateau = [ymin + (ymax - ymin) * k / 200 for k in range(201) if _top(ymin + (ymax - ymin) * k / 200) > top - 0.12]
        roof_cap[0] = top + 0.02
        if plateau:
            p0, p1 = min(plateau) + 0.08, max(plateau) - 0.08
            zb, zt = top * 0.6, top - 0.1
            if p1 - p0 > 1.6:
                mid = (p0 + p1) / 2
                wins = [[p0, mid - 0.06, zb, zt], [mid + 0.06, p1, zb, zt]]
            elif p1 - p0 > 0.4:
                wins = [[p0, p1, zb, zt]]
            print("WINDOWS extrapolated", aid, len(wins))
    if aid in NO_CABIN:
        wins = []
    if not wins or an.get("seats", 0) < 1:
        print("INTERIOR none", aid, "(no windows found)" if not wins else "(no seats)")
        return hull.build(an, out_glb, render_prefix)
    roof_cap[0] = max(w[3] for w in wins) + 0.22
    wtop = max(w[3] for w in wins) - 0.03           # the glass line along the top of the windows
    belt = min(w[2] for w in wins)
    cy0, cy1 = min(w[0] for w in wins), max(w[1] for w in wins)
    yws = None
    y = cy1
    while y < min(ymax, cy1 + 2.4):
        if roof(y) < belt + 0.12:
            yws = y
            break
        y += 0.05
    yws = yws if yws is not None else min(ymax - 0.15, cy1 + 0.3)
    yrw = None
    y = cy0
    while y > max(ymin, cy0 - 1.8):
        if roof(y) < belt + 0.12:
            yrw = y
            break
        y -= 0.05
    y_back = yrw if yrw is not None else cy0 - 0.15
    print("CABIN", aid, "belt %.2f cy0 %.2f cy1 %.2f yws %.2f yrw %s wtop %.2f" % (belt, cy0, cy1, yws, yrw, wtop))
    fl = max(0.25, belt - 0.68)
    fv = an["views"].get("front") or an["views"].get("rear")
    hws = [r[1] for r in fv["halfwidth_by_z"] if fl + 0.2 <= r[0] <= belt] if fv else []
    xh = min(W / 2, min(hws) if hws else W / 2)
    xi = xh - 0.07
    wheels = sv.get("wheels_m", [])

    def floor_at(y):
        f = fl
        for wy, wz, r in wheels:
            if abs(y - wy) < r + 0.12:
                f = max(f, wz + r + 0.04)
        return f

    def cut(body):
        # 1. the cabin, hollow under the roof line (over the wheels the floor rises clear of the arches)
        bot, top = [], []
        y = y_back + 0.05
        while y <= yws:
            t = roof(y) - SHELL
            if t > floor_at(y) + 0.3:
                bot.append((y, floor_at(y)))
                top.append((y, t))
            y += 0.1
        if len(bot) >= 2:
            cab = hull.prism("cabin", bot + list(reversed(top)), "x", xh - SHELL)
            if fv and len(fv.get("outline_m", [])) >= 3:
                # the cabin narrows with the body above the beltline (the greenhouse): the front
                # outline, SHELL in from each side, keeps the pillars and the roof's edges
                inset = [(math.copysign(max(0.0, abs(X) - SHELL), X), Z) for X, Z in fv["outline_m"]]
                cab = hull.intersect(cab, hull.prism("cabin_front", inset, "y", L))
            _diff(body, cab, "cabin")
        # 2. the side windows, the windscreen and the rear window cut open
        for i, w in enumerate(wins):                        # through each side wall only, under the roof
            zt = min(w[3], min(roof(w[0]), roof(w[1])) - SHELL - 0.05)
            if zt - w[2] < 0.12:
                continue
            for side in (1, -1):
                xa, xb = sorted((side * (xh - 0.25), side * W))
                _diff(body, _box("win%d%s" % (i, "R" if side > 0 else "L"), xa, xb, w[0], w[1], w[2], zt), "window")
        if wtop > belt + 0.2:
            _diff(body, _box("windscreen", -(xh - 0.12), xh - 0.12, cy1 - 0.05, yws + 0.35, belt + 0.05, wtop), "windscreen")
            if yrw is not None:
                _diff(body, _box("rear_window", -(xh - 0.12), xh - 0.12, yrw - 0.35, cy0 + 0.05, belt + 0.05, wtop), "rear window")
        return body

    ctx = hull.make(an, cut_windows=cut)
    body = ctx["body"]
    sch = SCHEMES[scheme_for(an)]
    mats = dict(ctx["mats"])
    mats.update({
        "glass": core.mat("glass", core.lin((120, 150, 165)), rough=0.05),
        "liner": core.mat("liner", core.lin(sch["liner"]), rough=0.8),
        "seat": core.mat("seat", rough=0.7, tex=tex_pleats(aid + "_seat", sch["seat"])),
        "seat_plain": core.mat("seat_plain", core.lin(sch["seat"]), rough=0.7),
        "carpet": core.mat("carpet", rough=0.95, tex=tex_carpet(aid + "_carpet", sch["carpet"])),
        "dash": core.mat("dash", core.lin(sch["dash"]), rough=0.6),
        "gauges": core.mat("gauges", rough=0.4, tex=tex_gauges(aid + "_gauges", sch["dash"])),
        "chrome": core.mat("chrome", core.lin((200, 200, 205)), rough=0.25, metal=0.9),
        "black": core.mat("black_rubber", core.lin((30, 30, 32)), rough=0.7),
    })
    glass = mats["glass"]
    glass.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.32
    glass.surface_render_method = "BLENDED"
    glass.use_backface_culling = False
    # the hull's inside is lining
    me = body.data
    me.materials.append(mats["liner"])
    li = len(me.materials) - 1
    for poly in me.polygons:
        c, n = poly.center, poly.normal
        if abs(c.x) < xh - 0.01 and y_back - 0.1 < c.y < yws + 0.1 and floor_at(c.y) - 0.02 < c.z < roof(c.y) - SHELL + 0.02:
            if n.x * (1 if c.x > 0 else -1) < -0.5 or abs(n.z) > 0.7 or abs(n.y) > 0.7:
                poly.material_index = li
    m = core.Mesh(aid + "_cabin", mats)
    # glazing
    for w in wins:
        zt = min(w[3], min(roof(w[0]), roof(w[1])) - SHELL - 0.05)
        if zt - w[2] < 0.12:
            continue
        zc = (w[2] + zt) / 2
        x = hull.wheel_halfwidth(an, zc, W) - 0.025
        for side in (1, -1):
            q = [Vector((side * x, w[0], w[2])), Vector((side * x, w[1], w[2])), Vector((side * x, w[1], zt)), Vector((side * x, w[0], zt))]
            m.face(q, "glass")
    xg = xh - 0.12
    if wtop > belt + 0.2:
        # the windscreen's top is where the roof line comes down to the window tops
        yt = cy1
        while yt < yws and _top(yt) > wtop + 0.04:
            yt += 0.02
        yb = max(yt + 0.02, yws - 0.02)
        m.face([Vector((-xg, yt, wtop)), Vector((xg, yt, wtop)), Vector((xg, yb, belt + 0.06)), Vector((-xg, yb, belt + 0.06))], "glass")
        if yrw is not None:
            yt2 = cy0
            while yt2 > yrw and _top(yt2) > wtop + 0.04:
                yt2 -= 0.02
            m.face([Vector((-xg, min(yrw + 0.02, yt2 - 0.02), belt + 0.06)), Vector((xg, min(yrw + 0.02, yt2 - 0.02), belt + 0.06)), Vector((xg, yt2, wtop)), Vector((-xg, yt2, wtop))], "glass")
    # carpet
    ya, yb2 = y_back + 0.1, yws - 0.35
    m.face([Vector((-xi, ya, fl + 0.005)), Vector((xi, ya, fl + 0.005)), Vector((xi, yb2, fl + 0.005)), Vector((-xi, yb2, fl + 0.005))], "carpet",
           [(0, 0), (2 * xi / 0.5, 0), (2 * xi / 0.5, (yb2 - ya) / 0.5), (0, (yb2 - ya) / 0.5)])
    # the dash, its gauges and the steering wheel (on the left)
    sloped = (yws - cy1) > 0.4
    dash_back = yws - (0.55 if sloped else 0.4)
    dz0, dz1 = fl + 0.32, belt + 0.03
    m.box((0, (dash_back + yws) / 2, (dz0 + dz1) / 2), (xi, (yws - dash_back) / 2, (dz1 - dz0) / 2), "dash")
    xd = -xi * 0.52
    m.face([Vector((xd + 0.2, dash_back - 0.003, dz1 - 0.2)), Vector((xd - 0.2, dash_back - 0.003, dz1 - 0.2)),
            Vector((xd - 0.2, dash_back - 0.003, dz1 - 0.02)), Vector((xd + 0.2, dash_back - 0.003, dz1 - 0.02))], "gauges",
           [(1, 0), (0, 0), (0, 1), (1, 1)])
    hub = Vector((xd, dash_back - 0.22, belt - 0.06))
    tilt = Matrix.Rotation(math.radians(-25), 3, "X")
    ring = [hub + tilt @ Vector((0.19 * math.cos(t), 0, 0.19 * math.sin(t))) for t in np.linspace(0, math.tau, 25)]
    m.pipe(ring, 0.017, "black", n=8, caps=False)
    for a in (0.0, math.pi, -math.pi / 2):
        m.pipe([hub, hub + tilt @ Vector((0.18 * math.cos(a), 0, 0.18 * math.sin(a)))], 0.012, "chrome", n=6)
    m.pipe([hub, Vector((xd, dash_back + 0.05, belt - 0.16))], 0.025, "black", n=8)
    # seats: rows back from the front one, to the seat count
    seats_left = int(an.get("seats", 1))
    y_row = max(dash_back - (0.72 if sloped else 0.62), y_back + 0.4)     # a short cab: the front row still fits
    markers = []
    row = 0
    while seats_left > 0 and y_row > y_back + 0.12:       # (a back row's seatback tucks under the rear window)
        cap = 2 if row == 0 else (3 if 2 * xi > 1.45 else 2)
        if row == 0 and seats_left == 1:
            cap = 1
        k = min(cap, seats_left)
        width = min(0.52, (2 * xi - 0.12) / max(k, 2))
        if row == 0:
            xs = [xd, -xd][:k] if 2 * xi > 1.0 else [0.0]          # driver on the left; a narrow cab: one seat in the middle
        elif k == 1:
            xs = [0.0]
        else:
            a0, a1 = -xi + 0.06 + width / 2, xi - 0.06 - width / 2
            xs = [a0 + (a1 - a0) * j / (k - 1) for j in range(k)]
        fz = fl
        room = min(roof(y_row - 0.3), roof(y_row + 0.2)) - SHELL - 0.08 - fz      # floor to the lining overhead
        for j, x in enumerate(xs):
            _seat(m, x, y_row, fz, width, room)
            markers.append(("seat_driver" if row == 0 and j == 0 else "seat_%d" % len(markers), Vector((x, y_row - 0.02, fz + 0.36))))
        seats_left -= k
        row += 1
        y_row -= 0.85
    interior = m.obj(parent=body)
    for name, loc in markers:
        core.empty(name, loc, body)
    print("INTERIOR extrapolated", aid, scheme_for(an), len(markers), "seats", len(wins), "windows",
          "windscreen" if wtop > belt + 0.2 else "", "rear window" if yrw is not None and wtop > belt + 0.2 else "")
    hull.finish(ctx, out_glb, render_prefix)
    if render_prefix:
        sc, cam = core.render_setup()
        core.render_persp(render_prefix + "_cabin.png", cam, (0, (y_back + yws) / 2, fl + 0.5),
                          (-W * 1.6, (y_back + yws) / 2 + 1.0, belt + 1.4), 1000, 700, 35)


def _seat(m, x, y, fz, width, room):
    """A seat on the floor at fz; the back (and its headrest, if there's room) kept under the lining."""
    hw = width / 2 - 0.02
    sh = fz + 0.34
    m.box((x, y, sh - 0.06), (hw, 0.24, 0.07), "seat")                          # cushion
    bh = max(0.18, min(0.3, (room - 0.36) / 2))                                  # half the back's height
    back = Matrix.Translation(Vector((x, y - 0.26, sh + bh))) @ Matrix.Rotation(-0.22, 4, "X")
    m.box((0, 0, 0), (hw, 0.06, bh), "seat", back)                               # raked back
    if room > 0.36 + 2 * bh + 0.2:
        m.box((0, 0.0, bh + 0.12), (hw * 0.6, 0.05, 0.09), "seat_plain", back)  # headrest
    m.box((x, y - 0.05, fz + 0.12), (hw * 0.8, 0.18, 0.12), "black")             # the frame under it


def _box(name, x0, x1, y0, y1, z0, z1):
    bm = __import__("bmesh").new()
    vs = [bm.verts.new(p) for p in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
    for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        bm.faces.new([vs[i] for i in f])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    core.col().objects.link(ob)
    return ob


def _diff(body, cutter, what):
    """Boolean difference; a cut that wrecks the shell is undone (and logged)."""
    keep = body.data.copy()
    mod = body.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    if len(body.data.polygons) < max(6, len(keep.polygons) * 0.5):
        print("CUT_SKIPPED", what)
        old = body.data
        body.data = keep
        bpy.data.meshes.remove(old)
    else:
        bpy.data.meshes.remove(keep)
