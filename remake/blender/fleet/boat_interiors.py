"""
boat_interiors.py -- a boat's fittings (the user, 2026-10-05: "All of the vehicles need complete interiors, that includes the
boats"): the helm in a wheelhouse (a pedestal chair, the console, the wheel and the live dials -- the road fleet's driver's
station, Builder.station, research/vehicles/INTERIORS.md), the wheelhouse behind it (a settee and a chart table; a ferry's
saloon of benches), and the cockpit (a sole to stand on, benches along its sides; the pontoon boat's helm console).

Coordinates: Blender (y forward, z up), the hull's frame (fleet/hull.py). `b` is build_boat's namespace (mod, GAUGES,
MARKERS, marker: enough of a Builder for its station()).
"""
import math

from mathutils import Matrix, Vector

from builder import Builder

SEATED = ("sailboat", "cabin_cruiser", "coast_guard_boat", "pontoon_boat")     # (cockpits with benches; the rest work decks)


def chair(me, H, z_floor, m="seat"):
    """A helm chair on its pedestal: H is its H-point."""
    me.box((H.x, H.y + 0.18, H.z - 0.07), (0.24, 0.24, 0.06), m)                    # the cushion
    back = Matrix.Translation((H.x, H.y - 0.08, H.z - 0.02)) @ Matrix.Rotation(math.radians(14), 4, "X")
    me.box((0, 0, 0.30), (0.23, 0.06, 0.30), m, xf=back)
    me.pipe([Vector((H.x, H.y + 0.15, z_floor)), Vector((H.x, H.y + 0.15, H.z - 0.13))], 0.04, "chrome", n=10)
    me.lathe([(0.0, 0.22), (0.03, 0.20), (0.04, 0.0001)], "black", n=14, xf=Matrix.Translation((H.x, H.y + 0.15, z_floor + 0.04)) @
             Matrix.Rotation(-math.pi / 2, 4, "X"))
    for sx in (1, -1):                                                                 # (its arms)
        me.box((H.x + sx * 0.25, H.y + 0.12, H.z + 0.14), (0.03, 0.18, 0.025), m)


def console(me, H, c, rear, front, half, z_floor, cap):
    """The helm console from the wheel's dash face to `front`: its top under the helmsman's sight line (6.5 deg down to its
    front edge, as the road fleet's dash), a fascia over the knees, a toe-kick block ahead of them."""
    eye = H + Vector((0, -0.05, 0.68))
    top = min(c.z + 0.10, eye.z - math.tan(math.radians(6.5)) * max(0.3, front - eye.y), cap)
    if front <= rear + 0.05:
        return
    me.box((0, (front + rear) / 2, top - 0.05), (half, (front - rear) / 2, 0.05), "dash")
    fb = H.z + 0.22
    me.box((0, rear + 0.06, (top - 0.10 + fb) / 2), (half - 0.02, 0.06, max(0.03, (top - 0.10 - fb) / 2)), "dash")
    kick = max(rear + 0.12, front - 0.28)
    me.box((0, (front + kick) / 2, (z_floor + top - 0.1) / 2), (half - 0.02, (front - kick) / 2, (top - 0.1 - z_floor) / 2), "dash")


def boat_helm(b, H, y0, hw, z0, sill):
    """A wheelhouse's helm: the chair at H (the registry's seat), the wheel and binnacle (the dials live in the game), the
    console out to the front wall under the windows."""
    me = b.mod("helm", "dash", "helm", hp=400, mass=60)
    c, rear = Builder.station(b, me, H, True)
    console(me, H, c, rear, y0 - 0.06, min(0.55, hw - 0.10), z0, sill - 0.02)
    chair(me, H, z0)


def wheelhouse_fit(b, H, y0, y1, hw, z0, hh, ferry=False):
    """Behind the helm: a settee down the port side and a chart table to starboard; a ferry's saloon -- rows of benches
    each side of an aisle to the doorway aft."""
    yb, ye = H.y - 0.55, y1 + 0.12
    if yb - ye < 0.7:
        return
    me = b.mod("fit_wheelhouse", "fittings", "wheelhouse_fit", hp=300, mass=120)
    xi = hw - 0.06                                                                      # (the walls' inner face)
    if ferry:
        y = yb - 0.25
        while y - 0.55 > ye:
            for sx in (1, -1):
                x0, x1 = 0.65, xi - 0.05
                xm, h = sx * (x0 + x1) / 2, (x1 - x0) / 2
                me.box((xm, y - 0.22, z0 + 0.40), (h, 0.22, 0.05), "seat")                # the seat
                me.box((xm, y - 0.46, z0 + 0.70), (h, 0.04, 0.28), "seat")                # its back
                me.box((xm, y - 0.30, z0 + 0.18), (h - 0.05, 0.12, 0.18), "dash")         # its base
            y -= 0.90
        return
    zs = z0 + 0.42
    me.box((-(xi - 0.24), (yb + ye) / 2, zs), (0.23, (yb - ye) / 2, 0.06), "seat")           # the settee
    me.box((-(xi - 0.24), (yb + ye) / 2, (z0 + zs - 0.06) / 2), (0.21, (yb - ye) / 2 - 0.02, (zs - 0.06 - z0) / 2), "wood")
    me.box((-(xi - 0.04), (yb + ye) / 2, zs + 0.28), (0.04, (yb - ye) / 2, 0.24), "seat")     # its back, on the wall
    if hw > 0.9:
        ln = min(0.45, (yb - ye) / 2)
        yc = yb - ln
        me.box((xi - 0.30, yc, z0 + 0.82), (0.28, ln, 0.025), "wood")                          # the chart table
        me.box((xi - 0.30, yc, z0 + 0.84), (0.22, ln * 0.7, 0.002), "paint2")                  # (its chart)
        me.box((xi - 0.30, yc, (z0 + 0.80) / 2 + z0 / 2), (0.26, ln - 0.03, 0.40), "wood")


def x_at(loop, z):
    """The half-width of the hull's inner loop (keel up to the deck edge) at height z; 0 below its keel."""
    for k in range(5):
        (xa, za), (xb, zb) = loop[k], loop[k + 1]
        if za - 1e-9 <= z <= zb + 1e-9 and zb > za:
            return xa + (xb - xa) * (z - za) / (zb - za)
    return 0.0 if z < loop[0][1] else loop[4][0]


def cockpit_fit(b, H, S, vtype, ck, INN):
    """The cockpit's sole (floorboards at the bottom of a small boat's), benches along its sides, and the pontoon boat's
    helm console. Returns the sole's height (the game stands people on it), or None."""
    if vtype in ("ferry", "barge", "canoe_kayak", "pedal_boat"):
        return None
    sheer = H.sheer_z((ck[0] + ck[1]) / 2)
    rows = sorted([y for y in INN if ck[1] - 1e-6 <= y <= ck[0] + 1e-6], reverse=True)
    if vtype == "pontoon_boat":
        zs = sheer - 0.40                                                                      # (a deck on its pontoons)
    elif H.free >= 0.9:
        zs = sheer - min(0.85, H.free * 0.6)
    else:
        zs = min(INN[y][0][1] for y in rows) + 0.10                                            # (floorboards)
    me = b.mod("cockpit_sole", "floor", "cockpit_sole", hp=800, mass=60)
    for a, bb in zip(rows, rows[1:]):
        xa, xb = x_at(INN[a], zs) - 0.01, x_at(INN[bb], zs) - 0.01
        if xa <= 0.02 and xb <= 0.02:
            continue
        me.face([(-xb, bb, zs), (xb, bb, zs), (xa, a, zs), (-xa, a, zs)], "wood")
    if vtype not in SEATED:
        return zs
    fb = b.mod("fit_cockpit", "fittings", "cockpit_fit", hp=300, mass=60)
    zt = zs + 0.45
    y0, y1 = ck[0] - 0.25, ck[1] + 0.30
    if vtype == "pontoon_boat":                                                                 # (lounges forward of the helm)
        y1 = -1.8
    xi = min(min(x_at(INN[y], zt), x_at(INN[y], zs + 0.05)) for y in rows if y1 - 0.3 <= y <= y0 + 0.3) - 0.03
    if vtype == "pontoon_boat":
        xi = min(xi, H.beam - 0.12 - 0.06)                                                     # (inside the bimini's posts)
    if xi > 0.55 and y0 - y1 > 0.6:
        for sx in (1, -1):
            fb.box((sx * (xi - 0.21), (y0 + y1) / 2, zt - 0.05), (0.21, (y0 - y1) / 2, 0.05), "seat")
            fb.box((sx * (xi - 0.21), (y0 + y1) / 2, (zs + zt - 0.10) / 2), (0.19, (y0 - y1) / 2 - 0.02, (zt - 0.10 - zs) / 2), "paint2")
            fb.box((sx * (xi - 0.03), (y0 + y1) / 2, zt + 0.22), (0.03, (y0 - y1) / 2, 0.20), "seat")
    if vtype == "pontoon_boat":                                                                 # the helm: the registry's seat
        Hp = Vector((0.0, ck[1] + 0.6, H.sheer_z(0) + 0.28))
        me2 = b.mod("helm", "dash", "helm", hp=400, mass=60)
        c, rear = Builder.station(b, me2, Hp, True)
        console(me2, Hp, c, rear, rear + 0.45, 0.42, zs, 10.0)
        chair(me2, Hp, zs)
    return zs
