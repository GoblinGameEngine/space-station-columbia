"""
space.py -- the spacecraft's and the spoke elevator's own tokens (research/vehicles/aerostat/AEROSTATS.md, "Space").

Their crew and passenger spaces are ordinary fleet bodies (kit/loft.py + fleet/builder.py) on a Steward keel: both
shells, reveals, doors, the tube frame between, seats. What makes each a spacecraft hangs off that body as equipment
tokens, each its own component:
  the passenger shuttle   wings (heat-tiled under), the tail fin, the manoeuvring pods, the main engines, the gear
  the supply freighter    the stacked cargo pods behind its cockpit, their spine, the drive section and its bells
  the cargo mule          the thruster pods, two manipulator arms, the dorsal fin and rail, the nose lamps
  the spoke elevator car  the rail trucks under it, the guide shoes on its roof, the ring of lamps, the finial
Coordinates: Blender (y forward, z up); z = 0 the ground under the keel's skids.
"""
import math

from mathutils import Matrix, Vector

TAU = 2 * math.pi
X, R = Matrix.Translation, Matrix.Rotation


def bell(me, c, r, ln, m_out="chrome", m_in="black", axis=Vector((0, -1, 0))):
    """A rocket or thruster bell: a throat, the flared skirt, a dark inside, opening along `axis`."""
    rot = Vector((0, 1, 0)).rotation_difference(axis).to_matrix().to_4x4()
    xf = X(c) @ rot
    me.lathe([(0.0, r * 0.45), (ln * 0.25, r * 0.38), (ln * 0.6, r * 0.62), (ln, r)], m_out, n=20, xf=xf)
    me.lathe([(ln, r * 0.96), (ln * 0.6, r * 0.58), (ln * 0.3, r * 0.36), (ln * 0.25, 0.0001)], m_in, n=20, xf=xf)


def foil(me, root, tip, thick, m_top, m_bot, m_edge=None, up=Vector((0, 0, 1))):
    """A wing or fin: root and tip are (leading-edge point, trailing-edge point) pairs; a lens-section aerofoil between
    them, `up` its thickness direction. The front fifth is the edge material (a coloured leading edge)."""
    rows = []
    for (le, te), t in ((root, thick), (tip, thick * 0.45)):
        le, te = Vector(le), Vector(te)
        sec = []
        for k in range(9):
            u = k / 8
            p = le + (te - le) * u
            w = t * math.sin(math.pi * min(1.0, 0.08 + u * 0.95)) * (1.0 - 0.3 * u)
            sec.append((p, w, u))
        rows.append(sec)
    for side, m in ((1, m_top), (-1, m_bot)):
        for k in range(8):
            (pa, wa, ua), (pb, wb, ub) = rows[0][k], rows[0][k + 1]
            (qa, va, _), (qb, vb, _) = rows[1][k], rows[1][k + 1]
            mm = m_edge if (m_edge and ua < 0.2 and side > 0) else m
            q = [pa + up * wa * side, pb + up * wb * side, qb + up * vb * side, qa + up * va * side]
            me.face(q if side > 0 else list(reversed(q)), mm)
    for row, sg in ((rows[0], -1), (rows[1], 1)):           # (the tip's and the root's closing faces)
        ring = [p + up * w for p, w, _ in row] + [p - up * w for p, w, _ in reversed(row)]
        me.face(ring if sg > 0 else list(reversed(ring)), m_top)


# ----------------------------------------------------------------------------------------------- the shuttle
def wings(b, S, st):
    me = b.mod("wings", "equipment", "wings", "C", hp=3000, mass=1800)
    L = b.L
    y0, y1, span, z = S["wing"]
    for sx in (1, -1):
        x0 = sx * (L.half_w - L.spec.get("tuck", 0.0) * 0.6 - 0.05)
        root = ((x0, y0, z), (x0, y1, z))
        tip = ((sx * span, y1 + 2.6, z + 0.25), (sx * span, y1 + 0.4, z + 0.25))
        foil(me, root, tip, 0.22, "paint", "black", "livery2")
        me.box((sx * (span - 0.05), y1 + 1.4, z + 0.32), (0.04, 0.12, 0.04), "lamp_red" if sx < 0 else "lamp_green")
    b.marker("wing_tip_R", (span, y1 + 1.4, z + 0.3))


def tail_fin(b, S, st):
    me = b.mod("tail_fin", "equipment", "tail_fin", "C", hp=1500, mass=500)
    L = b.L
    y0, y1, h = S["fin"]
    zc = L.crown - 0.05
    foil(me, ((0, y0, zc), (0, y1, zc)), ((0, y1 + 1.6, zc + h), (0, y1 + 0.2, zc + h)), 0.20, "paint", "paint", "livery2", up=Vector((1, 0, 0)))
    for k, zz in enumerate((zc + h * 0.55, zc + h * 0.62)):     # (two livery bands across it)
        me.box((0, y1 + 0.9 + (y0 - y1) * 0.25 * (1 - zz / (zc + h)), zz), (0.11, 1.0, 0.04), "livery2")


def oms_pods(b, S, st):
    me = b.mod("oms_pods", "equipment", "oms_pods", "C", hp=1500, mass=700)
    L = b.L
    y0, y1 = S["fin"][0], L.tail
    for sx in (1, -1):
        x = sx * (L.half_w * 0.55)
        z = L.crown - 0.25
        me.lathe([(0.0, 0.0001), (0.8, 0.55), (2.5, 0.75), (y0 - y1 + 0.4, 0.75), (y0 - y1 + 0.6, 0.55)], "paint", n=20,
                 xf=X((x, y0 + 0.5, z)) @ R(math.pi, 4, "Z"))
        bell(me, Vector((x, y1 - 0.05, z)), 0.42, 0.8, "livery2", "black")


def main_engines(b, S, st):
    me = b.mod("main_engines", "equipment", "main_engines", "C", hp=2000, mass=1500)
    L = b.L
    zc = (L.floor + L.crown) / 2
    me.box((0, L.tail - 0.02, zc), (L.half_w * 0.75, 0.04, (L.crown - L.floor) * 0.38), "black")    # (the base heat shield)
    for x, z, r in ((0.0, zc + 0.55, 0.62), (-0.9, zc - 0.45, 0.62), (0.9, zc - 0.45, 0.62)):
        bell(me, Vector((x, L.tail - 0.06, z)), r, 1.3, "chrome", "black")


def landing_gear(b, S, st):
    me = b.mod("landing_gear", "equipment", "landing_gear", "C", hp=1500, mass=600)
    L = b.L
    for x, y, n in S["gear"]:
        for sx in ((1, -1) if x else (1,)):
            for k in range(n):
                wy = y + (k - (n - 1) / 2) * 0.62
                me.pipe([Vector((sx * x, wy, L.skirt + 0.1)), Vector((sx * x, wy, 0.42))], 0.07, "chrome", n=10)
                for dx in (0.18, -0.18):
                    me.lathe([(-0.12, 0.20), (-0.12, 0.38), (-0.10, 0.42), (0.10, 0.42), (0.12, 0.38), (0.12, 0.20)], "rubber", n=18,
                             xf=X((sx * x + dx, wy, 0.42)) @ R(math.pi / 2, 4, "Z"))
                    me.lathe([(-0.13, 0.0001), (-0.13, 0.20), (0.13, 0.20), (0.13, 0.0001)], "chrome", n=14, xf=X((sx * x + dx, wy, 0.42)) @ R(math.pi / 2, 4, "Z"))


def nose_cap(b, S, st):
    """The shuttle's nose: a blunt heat-shield cap over the front face, its band of livery behind."""
    me = b.mod("nose_cap", "equipment", "nose_cap", "C", hp=1200, mass=200)
    L = b.L
    zc = (L.skirt + L.screen_base) / 2
    h = (L.screen_base - L.skirt) / 2
    me.lathe([(0.0, h * 1.05), (0.25, h * 1.0), (0.55, h * 0.8), (0.75, h * 0.5), (0.85, 0.0001)], S.get("nose_m", "livery2"), n=24,
             xf=X((0, L.nose - 0.2, zc)) @ Matrix.Scale(1.0, 4) @ Matrix(((L.half_w / h * 0.62, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))))


# ----------------------------------------------------------------------------------------------- the freighter
def cargo_pods(b, S, st):
    """Stacked cargo pods behind the cockpit: rounded boxes, each with its hatch, latch and hazard stripes."""
    L = b.L
    y0, n, (cols, rows), (pw, ph, pl) = S["pods"]
    me = b.mod("pod_spine", "equipment", "pod_spine", "C", hp=4000, mass=2000)
    ymax, ymin = y0, y0 - n * (pl + 0.15)
    zc = S.get("pod_z", L.crown / 2 + 0.3)
    for sx in (1, -1):
        for sz in (1, -1):
            me.pipe([Vector((sx * 0.35, ymax + 0.4, zc + sz * 0.35)), Vector((sx * 0.35, ymin, zc + sz * 0.35))], 0.09, "chrome", n=10)
    for i in range(n):
        y = y0 - i * (pl + 0.15) - pl / 2
        mp = b.mod("pods_%d" % i, "cargo_wall", "pods_%d" % i, "C", hp=2000, mass=900)
        for cx in range(cols):
            for rz in range(rows):
                x = (cx - (cols - 1) / 2) * (pw + 0.12)
                z = zc + (rz - (rows - 1) / 2) * (ph + 0.12)
                m = "paint" if (i + cx + rz) % 3 else "paint2"
                rounded_box(mp, (x, y, z), (pw / 2, pl / 2, ph / 2), 0.14, m)
                sx = 1 if x >= 0 else -1
                xo = x + sx * pw / 2 + 0.004
                if abs(x) + pw / 2 > 0.3:                  # (an outer face: its hatch and latch)
                    mp.box((xo, y, z), (0.008, pl * 0.18, ph * 0.32), "paint2" if m == "paint" else "paint")
                    mp.box((xo + sx * 0.01, y - pl * 0.1, z), (0.01, 0.04, 0.05), "chrome")
                if rz == 0:
                    for k in range(5):                     # (the hazard stripes along its foot)
                        mp.box((x, y - pl * 0.35 + k * pl * 0.17, z - ph / 2 - 0.003), (pw * 0.35, 0.04, 0.003), "lamp_amber" if k % 2 else "black")


def rounded_box(me, c, h, r, m, n=4):
    """A box with rounded long edges (its section round-cornered, its ends flat): a pod, a cab block."""
    cx, cy, cz = c
    hx, hy, hz = h
    loop = []
    for qx, qz, a0 in ((1, 1, 0.0), (-1, 1, 0.5), (-1, -1, 1.0), (1, -1, 1.5)):
        for k in range(n + 1):
            a = math.pi * (a0 + 0.5 * k / n)
            loop.append((cx + qx * (hx - r) + r * math.cos(a), cz + qz * (hz - r) + r * math.sin(a)))
    a_, b_ = [Vector((x, cy + hy, z)) for x, z in loop], [Vector((x, cy - hy, z)) for x, z in loop]
    m_ = len(loop)
    for k in range(m_):
        me.face([a_[k], b_[k], b_[(k + 1) % m_], a_[(k + 1) % m_]], m)
    me.face(list(reversed(a_)), m)
    me.face(b_, m)


def drive_section(b, S, st):
    me = b.mod("drive", "equipment", "drive", "C", hp=5000, mass=6000)
    L = b.L
    y, ln, hw, hh, zc = S["drive"]
    rounded_box(me, (0, y - ln / 2, zc), (hw, ln / 2, hh), 0.3, "paint2")
    for sx in (1, -1):
        me.box((sx * (hw + 0.005), y - ln * 0.45, zc + hh * 0.2), (0.01, ln * 0.18, hh * 0.25), "black")       # (the radiator vents)
        for k in range(6):
            me.box((sx * (hw + 0.012), y - ln * 0.33 - k * 0.12, zc + hh * 0.2), (0.006, 0.03, hh * 0.22), "paint")
        for k in range(4):                                  # (status lamps)
            me.lathe([(0.0, 0.05), (0.02, 0.0001)], "lamp_amber" if k < 2 else "lamp_blue", n=10,
                     xf=X((sx * (hw + 0.004), y - 0.3 - k * 0.18, zc + hh - 0.2)) @ R(-sx * math.pi / 2, 4, "Z"))
    for x, z in ((0.0, zc + hh * 0.55), (0.0, zc - hh * 0.55), (hw * 0.55, zc), (-hw * 0.55, zc)):
        bell(me, Vector((x, y - ln - 0.02, z)), hh * 0.32, hh * 0.7, "wood", "black")


# ----------------------------------------------------------------------------------------------- the cargo mule
def thruster_pods(b, S, st):
    me = b.mod("thruster_pods", "equipment", "thruster_pods", "C", hp=1500, mass=500)
    L = b.L
    for x, z, r, ln in S["thrusters"]:
        for sx in (1, -1):
            y1 = L.tail + 0.6
            me.lathe([(0.0, 0.0001), (0.35, r * 0.85), (0.6, r), (ln - 0.3, r), (ln, r * 0.7)], "livery2", n=18, xf=X((sx * x, y1, z)))
            for k, f in enumerate((0.3, 0.38)):
                me.lathe([(ln * f, r * 1.01), (ln * f + 0.08, r * 1.01)], "paint", n=18, xf=X((sx * x, y1, z)))
            bell(me, Vector((sx * x, y1 - 0.02, z)), r * 0.6, r * 0.9, "chrome", "black")
            for f in (0.3, 0.7):                            # (its two pylons, the body's flank out to the pod)
                me.pipe([Vector((sx * (L.half_w - 0.05), y1 + ln * f, z)), Vector((sx * (x - r * 0.9), y1 + ln * f, z))], 0.07, "chrome", n=8)


def manipulators(b, S, st):
    """Two jointed arms on the right flank: shoulder, upper arm, elbow, forearm, wrist, a two-finger gripper."""
    me = b.mod("manipulators", "equipment", "manipulators", "R", hp=900, mass=300)
    L = b.L
    x = L.half_w + 0.12
    for (ys, zs), (ye, ze), (yw, zw) in S["arms"]:
        pts = [Vector((x, ys, zs)), Vector((x + 0.05, ye, ze)), Vector((x + 0.1, yw, zw))]
        for a, c in zip(pts, pts[1:]):
            mid_ = (a + c) / 2
            d = c - a
            ang = math.atan2(d.z, d.y)
            me.box(tuple(mid_), (0.07, d.length / 2, 0.11), "paint", xf=X(mid_) @ R(ang, 4, "X") @ X(-mid_))
            me.box(tuple(mid_ + Vector((0.075, 0, 0))), (0.004, d.length * 0.3, 0.06), "livery2", xf=X(mid_) @ R(ang, 4, "X") @ X(-mid_))
        for p in pts:
            me.lathe([(-0.10, 0.13), (0.10, 0.13)], "livery2", n=14, xf=X(p) @ R(math.pi / 2, 4, "Z"))
        w = pts[-1]
        for dz in (0.07, -0.07):
            me.pipe([w, w + Vector((0.0, 0.22, dz)), w + Vector((0.0, 0.34, dz * 0.5))], 0.025, "chrome", n=6)


def dorsal(b, S, st):
    me = b.mod("dorsal", "equipment", "dorsal", "C", hp=400, mass=40)
    L = b.L
    y = L.tail_in + 0.9
    foil(me, ((0, y, L.crown - 0.03), (0, y - 1.0, L.crown - 0.03)), ((0, y - 0.7, L.crown + 0.55), (0, y - 1.05, L.crown + 0.55)), 0.06,
         "paint", "paint", "livery2", up=Vector((1, 0, 0)))
    for sx in (1, -1):                                      # (the grab rail along the roof)
        me.pipe([Vector((sx * 0.45, L.tail_in + 0.3, L.crown - 0.02)), Vector((sx * 0.45, L.tail_in + 0.4, L.crown + 0.12)),
                 Vector((sx * 0.45, L.header - 0.3, L.crown + 0.12)), Vector((sx * 0.45, L.header - 0.4, L.crown - 0.02))], 0.022, "chrome", n=6)


def nose_lamps(b, S, st):
    """Round lamps on the nose face (the mule's), a porthole among them."""
    me = b.mod("nose_lamps", "lamp", "nose_lamps", "C", hp=60, mass=3)
    L = b.L
    y = L.nose + 0.01
    for x, z, r, m in S.get("lamps", []):
        for sx in ((1, -1) if x else (1,)):
            me.lathe([(0.0, r * 1.25), (0.03, r * 1.25), (0.03, r), (0.06, r * 0.6), (0.075, 0.0001)], m, n=16,
                     xf=X((sx * x, y - 0.03, z)))


# ----------------------------------------------------------------------------------------------- the spoke elevator
def guide_rollers(b, S, st):
    """The rail trucks under the floor (a sprung pair of tyred rollers each) and the guide shoes on the roof."""
    me = b.mod("guide_rollers", "equipment", "guide_rollers", "C", hp=1500, mass=300)
    L = b.L
    for x in (-1.2, 1.2):
        for y in (-1.2, 1.2):
            me.box((x, y, 0.30), (0.18, 0.40, 0.08), "black")
            for dy in (0.24, -0.24):
                me.lathe([(-0.07, 0.10), (-0.07, 0.17), (0.07, 0.17), (0.07, 0.10)], "rubber", n=16, xf=X((x, y + dy, 0.17)) @ R(math.pi / 2, 4, "Z"))
                me.lathe([(-0.08, 0.0001), (-0.08, 0.10), (0.08, 0.10), (0.08, 0.0001)], "chrome", n=12, xf=X((x, y + dy, 0.17)) @ R(math.pi / 2, 4, "Z"))
    for ang in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
        x, y = math.sin(ang) * 1.0, math.cos(ang) * 1.0
        me.box((x, y, L.crown + 0.03), (0.10, 0.10, 0.06), "chrome")
        me.lathe([(0.0, 0.06), (0.10, 0.06)], "rubber", n=12, xf=X((x, y, L.crown + 0.12)) @ R(-math.pi / 2, 4, "X"))


def rim_lamps(b, S, st):
    me = b.mod("rim_lamps", "lamp", "rim_lamps", "C", hp=60, mass=3)
    L = b.L
    ys = [y for y in L.stations if L.tail + 0.1 < y < L.nose - 0.1]
    for y in ys[::2]:
        e = L.ext_half(y)
        x, z = e[L.E["cant"]]
        for sx in (1, -1):
            me.lathe([(0.0, 0.05), (0.02, 0.045), (0.035, 0.0001)], "lamp_amber", n=10,
                     xf=X((sx * (x + 0.01), y, z - 0.06)) @ R(-sx * math.pi / 2, 4, "Z"))
    me.lathe([(0.0, 0.14), (0.06, 0.12), (0.14, 0.05), (0.2, 0.0001)], "chrome", n=16, xf=X((0, 0, L.crown - 0.02)) @ R(-math.pi / 2, 4, "X"))


KINDS = {"wings": wings, "tail_fin": tail_fin, "oms_pods": oms_pods, "main_engines": main_engines, "landing_gear": landing_gear,
         "nose_cap": nose_cap, "cargo_pods": cargo_pods, "drive_section": drive_section, "thruster_pods": thruster_pods,
         "manipulators": manipulators, "dorsal": dorsal, "nose_lamps": nose_lamps, "guide_rollers": guide_rollers, "rim_lamps": rim_lamps}


def equipment(b, kind, st):
    fn = KINDS.get(kind)
    if fn is None:
        return False
    fn(b, b.L.spec.get("space", {}), st)
    return True
