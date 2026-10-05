"""
aero.py -- the aerostats' own tokens (research/vehicles/aerostat/AEROSTATS.md): the envelope, its fins, the ducted
fans and their booms and pylons, the gondola's suspension, the cargo aerostat's sling frame and legs, the rescue
aerostat's winch and markings.

The gondola itself is an ordinary fleet body (kit/loft.py + fleet/builder.py) on a Steward keel (a board with landing
skids, no wheels): both shells, reveals, doors, the tube frame between, the seats -- every rule of the road fleet.
What flies it hangs off that body as equipment tokens, each its own component.

A class's spec["aero"] gives the numbers:
  env      (length, radius, y of its middle, z of its axis)      stripes  [(elevation deg, half width deg), ...]
  bands    [(t0, t1), ...] round bands (t: 0 the tail .. 1 the nose)   cap  t past which the nose is the band colour
  fins     (t0, t1, span, tip chord share, sweep)                 fin_band  (s0, s1): a band across the fins
  fans     [(x, y, z, radius, mount)], mount "env" (a pylon up to the envelope) | "boom" (a boom to the gondola's tail)
  struts   [(x, y)] gondola roof points strutted up to the envelope; mast: y of a mast on the centre line (or None)
  sling    (half width, y0, y1, z) the cargo frame's top rail; legs [y, ...]: the A-legs from the envelope down to it
Coordinates: Blender (y forward, z up); z = 0 the ground under the keel's skids.
"""
import math

from mathutils import Matrix, Vector

TAU = 2 * math.pi


def env_r(t, R):
    """The envelope's radius at t (0 the tail point, 1 the nose): a blunt ellipsoidal nose, a long full middle, a
    tapering tail cone -- the classic non-rigid airship."""
    if t >= 0.70:
        u = (t - 0.70) / 0.30
        return R * math.sqrt(max(0.0, 1.0 - u ** 2.2))
    if t >= 0.38:
        return R * (0.985 + 0.015 * math.sin(math.pi * (t - 0.38) / 0.32))
    u = t / 0.38
    return R * (1.0 - (1.0 - u) ** 1.7) ** 0.75


def env_pt(A, t, ang, rr=None):
    L, R, yc, zc = A["env"]
    r = env_r(t, R) if rr is None else rr
    return Vector((r * math.sin(ang), yc - L / 2 + L * t, zc + r * math.cos(ang)))


def _stripe(A, t, ang):
    """The livery at a point of the envelope (ang from the top, clockwise seen from behind): band colour or not."""
    elev = 90.0 - math.degrees(abs(((ang + math.pi) % TAU) - math.pi))       # (degrees above the equator, either side)
    for e, w in A.get("stripes", []):
        if abs(elev - e) <= w:
            return True
    for t0, t1 in A.get("bands", []):
        if t0 <= t <= t1:
            return True
    return t >= A.get("cap", 9.0)


def envelope(b, A, st):
    me = b.mod("envelope", "envelope", "envelope", "C", hp=4000, mass=180, breaks="detach")
    b.MODS["envelope"]["smooth"] = True
    # (round: 56 even steps plus every stripe's two edges, both sides -- a stripe narrower than a step never vanishes)
    angs = {round(TAU * k / 56, 5) for k in range(56)}
    for e, w in A.get("stripes", []):
        for el in (e - w, e + w):
            angs |= {round(math.radians(90 - el), 5), round(math.radians(270 + el) % TAU, 5)}
    angs = sorted(angs)
    n = len(angs)
    ts = [0.0, 0.004, 0.012, 0.025, 0.045, 0.07] + [0.07 + k * 0.025 for k in range(1, 37)]
    ts = sorted({round(min(1.0, t), 4) for t in ts} | {1.0} | {t for bd in A.get("bands", []) for t in bd} | ({A["cap"]} if "cap" in A else set()))
    rings = [[env_pt(A, t, a) for a in angs] for t in ts]
    for i in range(len(ts) - 1):
        for k in range(n):
            a1 = angs[(k + 1) % n] + (TAU if k == n - 1 else 0.0)
            tm, am = (ts[i] + ts[i + 1]) / 2, (angs[k] + a1) / 2
            m = "livery2" if _stripe(A, tm, am) else "livery1"
            me.face([rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]], m)
    # (the seams: the gores' thin welts, and the nose's mooring cone)
    L, R, yc, zc = A["env"]
    me.lathe([(0.0, 0.10), (0.18, 0.07), (0.30, 0.0001)], "chrome", n=16, xf=Matrix.Translation((0, yc + L / 2 - 0.08, zc)))
    b.marker("mooring_cone", (0, yc + L / 2 + 0.2, zc))


def _fin(me, A, ang, mats):
    """One fin at angle ang round the tail: a thin lofted aerofoil from root (sunk into the envelope) to tip."""
    L, R, yc, zc = A["env"]
    t0, t1, span, tipk, sweep = A["fins"]
    s0, s1 = A.get("fin_band", (9, 9))
    d = Vector((math.sin(ang), 0, math.cos(ang)))
    side = Vector((math.cos(ang), 0, -math.sin(ang)))
    th = 0.035 * span + 0.02
    rows = []
    nsp = 6
    for j in range(nsp + 1):
        s = j / nsp
        ya = yc - L / 2 + L * t0 + L * (t1 - t0) * (1 - tipk) * s * 0.9       # (the trailing edge: the tip chord shorter)
        yb = yc - L / 2 + L * t1 - sweep * s
        root_r = min(env_r(t0, R), env_r(t1, R)) - 0.06
        r = root_r + (span + 0.06) * s
        tt = th * (1 - 0.6 * s)
        sec = []
        for k in range(9):
            u = k / 8
            y = yb + (ya - yb) * u
            w = tt * math.sin(math.pi * min(1.0, u * 1.15)) if u < 0.98 else 0.002
            sec.append((y, w))
        ring = [d * r + Vector((0, y, zc)) + side * w for y, w in sec] + [d * r + Vector((0, y, zc)) - side * w for y, w in reversed(sec[1:-1])]
        rows.append((s, ring))
    for (sa, ra), (sb, rb) in zip(rows, rows[1:]):
        m = mats[1] if s0 <= (sa + sb) / 2 <= s1 else mats[0]
        n = len(ra)
        for k in range(n):
            me.face([ra[k], ra[(k + 1) % n], rb[(k + 1) % n], rb[k]], m)
    me.face(list(rows[-1][1]), mats[0])


def fins(b, A, st):
    me = b.mod("fins", "equipment", "fins", "C", hp=900, mass=60)
    for ang in A.get("fin_angles", (0.0, math.pi / 2, math.pi, 3 * math.pi / 2)):
        _fin(me, A, ang, ("livery1", "livery2"))
    if A.get("stabiliser_rods"):                         # (the rescue's: a slim boom along each horizontal fin's tip)
        L, R, yc, zc = A["env"]
        t0, t1, span, tipk, sweep = A["fins"]
        for sx in (1, -1):
            r = min(env_r(t0, R), env_r(t1, R)) + span
            y0, y1 = yc - L / 2 + L * t1 - sweep + 0.4, yc - L / 2 + L * t0 - 0.9
            me.lathe([(0.0, 0.0001), (0.25, 0.09), (0.6, 0.11), (y0 - y1 - 0.5, 0.11), (y0 - y1, 0.0001)], "livery1", n=12,
                     xf=Matrix.Translation((sx * r, y1, zc)))


def ducted_fan(me, c, r, ln, paint, band, n_blades=12, axis=Vector((0, 1, 0))):
    """A ducted fan: a thick duct (lip, outer skin, inner wall), a striped band, the rotor (spinner, blades), three
    stators, the tail cone, a chrome guard ring at the lip. Built along +y, turned to `axis`."""
    rot = Vector((0, 1, 0)).rotation_difference(axis).to_matrix().to_4x4()
    xf = Matrix.Translation(c) @ rot
    h = ln / 2
    t = max(0.05, r * 0.12)
    outer = [(h, r + t * 0.35), (h - 0.03, r + t * 0.8), (h - ln * 0.25, r + t), (-h + ln * 0.3, r + t * 0.9), (-h, r + t * 0.45)]
    inner = [(-h, r + 0.004), (-h + ln * 0.3, r - t * 0.05), (h - ln * 0.2, r - t * 0.1), (h - 0.02, r)]
    prof = outer + inner + [outer[0]]
    me.lathe(prof[:3], "chrome", n=28, xf=xf)
    me.lathe(prof[2:4], band, n=28, xf=xf)
    me.lathe(prof[3:], paint, n=28, xf=xf)
    # the rotor
    me.lathe([(h * 0.5, 0.0001), (h * 0.35, r * 0.12), (0.0, r * 0.2), (-h * 0.2, r * 0.2)], "chrome", n=16, xf=xf)
    for k in range(n_blades):
        a = TAU * k / n_blades
        pts = []
        for s, tw in ((0.2, 0.55), (1.0, 0.25)):
            rr = r * s if s < 1 else r - 0.015
            for e in (-1, 1):
                ca = a + e * (0.30 if s < 1 else 0.17)          # (broad, overlapping blades: a solid rotor from in front)
                pts.append(Vector((rr * math.cos(ca), e * tw * 0.12 * ln * (1 if s < 1 else 0.6), rr * math.sin(ca))))
        q = [pts[0], pts[1], pts[3], pts[2]]
        me.face([xf @ p for p in q], "chrome")
        me.face([xf @ p for p in reversed(q)], "chrome")
    me.lathe([(-h * 0.55, 0.0001), (-h * 0.55, r * 0.99)], "black", n=28, xf=xf)          # (the dark of the duct behind the rotor)
    for k in range(3):                                   # the stators behind the rotor, and the tail cone
        a = TAU * k / 3 + 0.4
        me.pipe([xf @ Vector((r * 0.18 * math.cos(a), -h * 0.45, r * 0.18 * math.sin(a))), xf @ Vector((r * math.cos(a), -h * 0.45, r * math.sin(a)))],
                0.02, "black", n=6)
    me.lathe([(-h * 0.2, r * 0.2), (-h * 0.8, r * 0.12), (-h * 1.05, 0.0001)], paint, n=16, xf=xf)
    me.lathe([(h + 0.01, r * 0.98), (h + 0.01, r * 1.02)], "chrome", n=28, xf=xf)     # (the guard ring, the lip's bright edge)


def fans(b, A, st):
    L, R, yc, zc = A["env"]
    paint, band = A.get("fan_paint", ("livery1", "livery2"))
    for k, (x, y, z, r, mount) in enumerate(A["fans"]):
        for sx in ((1, -1) if x else (1,)):
            sd = "C" if not x else ("R" if sx > 0 else "L")
            mid = "fan_%d%s" % (k, sd if x else "")
            me = b.mod(mid, "equipment", "fan_%d" % k, sd, hp=600, mass=40)
            b.MODS[mid]["smooth"] = True
            c = Vector((sx * x, y, z))
            ducted_fan(me, c, r, r * A.get("fan_len", 1.25), paint, band)
            b.marker("fan_%d%s" % (k, sd if x else ""), tuple(c))
            if mount == "env":                            # a pylon up to the envelope's flank
                t = (y - (yc - L / 2)) / L
                ang = math.atan2(sx * x, z - zc) if x else math.pi
                er = env_r(min(0.99, max(0.01, t)), R)
                top = env_pt(A, t, ang, er - 0.15)
                foot = c + (top - c).normalized() * (r + 0.05)
                me.pipe([foot, top], 0.07, paint, n=10)
                me.pipe([foot + Vector((0, 0.25, 0)), top + Vector((0, 0.4, 0))], 0.04, "chrome", n=8)
            else:                                         # a boom forward to the gondola's tail quarter
                B = b.L
                y0 = B.tail_in + 0.35
                root = Vector((sx * (B.half_w - 0.12), y0, B.head - 0.10))
                foot = c + Vector((-sx * (r + 0.05), 0, 0)) if abs(c.x) > abs(root.x) + 0.3 else c + Vector((0, r * 0.5, 0))
                me.pipe([root, (root + foot) / 2 + Vector((0, 0, 0.12)), foot], 0.07, "livery1", n=10)
                me.lathe([(0.0, 0.14), (0.20, 0.14)], "chrome", n=14, xf=Matrix.Translation(root - Vector((0, 0.1, 0))))


def suspension(b, A, st):
    """Struts from the gondola's roof up to the envelope (telescopic: a tube and a ram), and the centre mast."""
    me = b.mod("suspension", "equipment", "suspension", "C", hp=1500, mass=80)
    B = b.L
    L, R, yc, zc = A["env"]
    for x, y in A.get("struts", []):
        for sx in (1, -1):
            foot = Vector((sx * x, y, B.crown - 0.06))
            t = (y + (0.5 if y > yc else -0.5) - (yc - L / 2)) / L
            top = env_pt(A, t, math.pi - sx * 0.55, env_r(t, R) - 0.12)
            mid = foot + (top - foot) * 0.55
            me.pipe([foot, mid], 0.055, "livery1", n=10)
            me.pipe([mid - (top - foot).normalized() * 0.15, top], 0.035, "chrome", n=8)
            me.lathe([(0.0, 0.10), (0.06, 0.10)], "chrome", n=12, xf=Matrix.Translation(foot) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    if A.get("mast") is not None:
        y = A["mast"]
        t = (y - (yc - L / 2)) / L
        top = zc - env_r(t, R) + 0.15
        me.lathe([(0.0, 0.16), (0.08, 0.13), (top - B.crown, 0.11)], "livery1", n=14,
                 xf=Matrix.Translation((0, y, B.crown - 0.04)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    if A.get("saddle"):                                   # (a gondola slung tight under the envelope: its saddle)
        y0, y1 = B.toe - 0.3, B.tail_in + 0.3
        for y in (y0, (y0 + y1) / 2, y1):
            t = (y - (yc - L / 2)) / L
            bot = zc - env_r(t, R) + 0.1
            for sx in (1, -1):
                me.pipe([Vector((sx * 0.7, y, B.crown - 0.05)), Vector((sx * 1.0, y, bot))], 0.06, "livery2", n=8)
        me.box((0, (y0 + y1) / 2, B.crown + 0.05), (0.9, (y0 - y1) / 2, 0.08), "livery2")


def sling(b, A, st):
    """The cargo aerostat's sling frame: a deep box-section rectangle under it all (it lands on its feet), cross
    beams, the hook rail with its hooks, corner pulleys; A-legs from the envelope's flanks down to it; chains."""
    me = b.mod("sling", "equipment", "sling", "C", hp=3000, mass=900)
    hw, y0, y1, z = A["sling"]
    L, R, yc, zc = A["env"]
    d = 0.32
    for sx in (1, -1):
        me.box((sx * hw, (y0 + y1) / 2, z - d / 2), (0.16, (y0 - y1) / 2, d / 2), "livery1")
        me.box((sx * (hw + 0.165), (y0 + y1) / 2, z - d / 2), (0.006, (y0 - y1) / 2 - 0.3, d * 0.25), "livery2")
    for y in (y0, y1):
        me.box((0, y, z - d / 2), (hw + 0.16, 0.16, d / 2), "livery1")
        for sx in (1, -1):
            me.lathe([(-0.12, 0.22), (0.12, 0.22)], "chrome", n=16, xf=Matrix.Translation((sx * (hw + 0.30), y, z - d / 2)) @ Matrix.Rotation(math.pi / 2, 4, "Z"))
    k = y1 + 1.2
    while k < y0 - 1.0:                                  # cross beams and the hooks on them
        me.box((0, k, z - 0.12), (hw - 0.1, 0.08, 0.10), "livery1")
        for sx in (-0.6, 0.0, 0.6):
            hx = sx * hw
            me.pipe([Vector((hx, k, z - 0.22)), Vector((hx, k, z - 0.45)), Vector((hx + 0.08, k, z - 0.55)), Vector((hx + 0.16, k, z - 0.45))], 0.025, "chrome", n=6)
        k += 2.4
    for sx in (1, -1):                                   # the feet it lands on
        for y in (y0 - 0.4, y1 + 0.4):
            me.box((sx * hw, y, z - d - 0.10), (0.20, 0.30, 0.10), "rubber")
    for y in A.get("legs", []):                          # the A-legs: two members a side from the envelope's flank
        t = (y - (yc - L / 2)) / L
        for sx in (1, -1):
            top = env_pt(A, t, math.pi - sx * 1.05, env_r(t, R) - 0.15)
            ft = Vector((sx * hw, y, z))
            for dy in (0.9, -0.9):
                me.pipe([top, ft + Vector((0, dy, 0))], 0.11, "livery1", n=10)
            me.box((sx * hw * 0.98, y, (top.z + z) / 2), (0.05, 0.9, 0.05), "livery2")
            me.lathe([(-0.1, 0.18), (0.1, 0.18)], "chrome", n=14, xf=Matrix.Translation(ft) @ Matrix.Rotation(math.pi / 2, 4, "Z"))
            for dy in (0.6, -0.6):                         # (the chains: a sagging run of links)
                p0, p1 = top + Vector((0, dy, -0.3)), Vector((sx * hw * 0.6, y + dy * 2, z))
                pts = [p0 + (p1 - p0) * (i / 8) + Vector((0, 0, -0.35 * math.sin(math.pi * i / 8))) for i in range(9)]
                me.pipe(pts, 0.018, "chrome", n=5)
    b.marker("sling_hook", (0, (y0 + y1) / 2, z - 0.55))


def winch(b, A, st):
    """The rescue hoist: an arm over the side door, the drum, the cable, the hook."""
    me = b.mod("winch", "equipment", "winch", "R", hp=400, mass=60)
    B = b.L
    d = next(d for d in B.doors if d.get("kind") == "slide")
    y = (d["y0"] + d["y1"]) / 2
    x = B.half_w - 0.05
    z = B.crown - 0.02
    me.box((x - 0.25, y, z + 0.10), (0.20, 0.25, 0.12), "livery2")
    me.pipe([Vector((x - 0.1, y, z + 0.18)), Vector((x + 0.55, y, z + 0.18)), Vector((x + 0.65, y, z + 0.05))], 0.05, "chrome", n=8)
    me.lathe([(-0.12, 0.10), (0.12, 0.10)], "black", n=14, xf=Matrix.Translation((x + 0.62, y, z - 0.02)) @ Matrix.Rotation(math.pi / 2, 4, "Z"))
    # (stowed: the hook drawn up under the drum, clear above the door's head; the game pays the cable out)
    me.pipe([Vector((x + 0.62, y, z - 0.12)), Vector((x + 0.62, y, z - 0.22))], 0.008, "black", n=5)
    me.pipe([Vector((x + 0.62, y, z - 0.22)), Vector((x + 0.62, y, z - 0.30)), Vector((x + 0.70, y, z - 0.34)), Vector((x + 0.76, y, z - 0.27))], 0.02, "chrome", n=6)
    b.marker("winch_hook", (x + 0.62, y, z - 0.34))


def cross(b, A, st):
    """The red cross on each flank (aft of the windows) and on the nose under the screen."""
    me = b.mod("cross", "trim", "cross", "C", hp=60, mass=1)
    B = b.L
    y, z, s = A["cross"]
    for sx in (1, -1):
        xs = b.surf_x(y, z) + 0.004
        for (hy, hz) in ((s, s * 0.32), (s * 0.32, s)):
            me.face([(sx * xs, y + hy * sx, z - hz), (sx * xs, y - hy * sx, z - hz), (sx * xs, y - hy * sx, z + hz), (sx * xs, y + hy * sx, z + hz)], "livery2")


def lamps(b, A, st):
    """The aerostat's lights: navigation lamps (red left, green right as the sea's -- here red/white), the anti-collision
    beacon on the envelope's belly and top, the round courtesy lamps along the gondola's foot."""
    me = b.mod("aero_lamps", "lamp", "aero_lamps", "C", hp=60, mass=2)
    L, R, yc, zc = A["env"]
    for t, ang in ((0.55, 0.0), (0.55, math.pi)):
        p = env_pt(A, t, ang, env_r(t, R) + 0.02)
        me.lathe([(0.0, 0.10), (0.05, 0.09), (0.10, 0.0001)], "lamp_red", n=12, xf=Matrix.Translation(p) @ Matrix.Rotation(-math.pi / 2 if ang == 0 else math.pi / 2, 4, "X"))
        b.marker("light_beacon", tuple(p))
    B = b.L
    n = A.get("foot_lamps", 0)
    for sx in (1, -1):
        for k in range(n):
            y = B.toe - 0.6 - k * (B.toe - B.tail_in - 1.2) / max(1, n - 1)
            z = B.skirt + 0.12
            x = b.surf_x(y, z) + 0.002
            me.lathe([(0.0, 0.045), (0.015, 0.035), (0.02, 0.0001)], "lamp_red" if n and k % 2 else "lamp_reverse", n=10,
                     xf=Matrix.Translation((sx * x, y, z)) @ Matrix.Rotation(-sx * math.pi / 2, 4, "Z"))


def ladder(b, A, st):
    """A boarding ladder hung under the crew door (the cargo gondola stands high on its frame)."""
    me = b.mod("ladder", "equipment", "ladder", "R", hp=200, mass=12)
    B = b.L
    d = B.doors[0]
    y = (d["y0"] + d["y1"]) / 2
    x = B.half_w + 0.06
    z0, z1 = A["sling"][3] + 0.1, B.sill
    for dy in (-0.22, 0.22):
        me.pipe([Vector((x, y + dy, z1)), Vector((x + 0.25, y + dy, z0))], 0.025, "chrome", n=6)
    k = 0.3
    while k < z1 - z0:
        f = k / (z1 - z0)
        me.pipe([Vector((x + 0.25 * (1 - f), y - 0.22, z0 + k)), Vector((x + 0.25 * (1 - f), y + 0.22, z0 + k))], 0.018, "chrome", n=6)
        k += 0.3


KINDS = {"envelope": envelope, "fins": fins, "ducted_fans": fans, "suspension": suspension, "sling": sling, "winch": winch,
         "rescue_cross": cross, "aero_lamps": lamps, "boarding_ladder": ladder}


def equipment(b, kind, st):
    fn = KINDS.get(kind)
    if fn is None:
        return False
    fn(b, b.L.spec.get("aero", {}), st)
    return True
