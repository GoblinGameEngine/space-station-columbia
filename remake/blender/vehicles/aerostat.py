"""
aerostat.py -- the station's air vehicle: an aerostat, a cabin slung under a fabric lift balloon, with
four ducted fans at the corners (from the user's reference sheet, ~/Downloads/grok-image-*.jpg).

  flatpak run org.blender.Blender -b --factory-startup --python <abs aerostat.py> -- OUT_GLB [RENDER_PREFIX]

Blender Z up, the nose toward +Y (glTF -Z, Godot's forward).  Metres; the cabin floor is at FLOOR.
Nodes the game drives (the vehicle rig -- names are the contract with the flight controller):
  door_{R,L}{1,2}      sliding pocket doors, closed; open = slid DOOR_SLIDE m along +-Y (inside the
                       hull, behind the side windows)
  engine_{FR,FL,BR,BL} a ducted fan on its pivot: rotate about local X to tilt its thrust fore/aft
                       (0 = straight down, lift; + = nose-down tilt, thrust forward)
  engine_*/rotor_*     the fan's rotor: spin about local Z
  seat_pilot, seat_passenger, seat_rear_{L,C,R}   empties where a sitter's hips go, facing -Y (glTF)
  exit_{R,L}           empties outside each doorway, where a player steps out
Everything else is merged per material.

  cabin   2.4 m wide x 4.6 m long x 2.45 m tall: a rounded-rectangle (superellipse) shell -- slate
          blue belly, white band, a wrap-round window band, a silver roof -- with a sliding double
          pocket door each side; inside, the pilot's seat (right) with dash, screen and yoke, a
          passenger seat, a rear bench, grab rails, a ceiling light
  lift    a 4.8 m fabric balloon, gores meeting at a rosette on the nose axis, on an A-frame and
          four cables from the roof rails
  fans    four ducted fans at the belly corners, each tilting on a trunnion at the end of its arm,
          a caster underneath
"""
import math
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/tmp/aerostat.glb"
RENDER = argv[1] if len(argv) > 1 else None

A, B, N = 1.2, 2.3, 4.0              # plan half-width (x), half-length (y), superellipse exponent
H = 2.45                             # cabin height
FLOOR = 0.35
BELLY_TOP = 0.78                     # slate blue below
BAND_TOP = 1.02                      # white band, then the window band
WIN_TOP = 2.05
ROOF0 = 2.12                         # the roof starts curving in
DOOR_HW = 0.65                       # half the door opening
DOOR_Y = -0.15                       # its centre, a little aft: the front seats sit clear ahead of it
CHIN_Y = DOOR_Y + DOOR_HW + 0.1      # from here to the nose the floor and belly are clear acrylic
SEAT_Y = 1.05                        # the front seats' centre: wholly ahead of the doorway
REAR_Y = -1.75                       # the rear bench's
DOOR_SLIDE = 0.62                    # how far a leaf slides open (into its pocket behind a side window)
BALLOON_R = 2.4
BALLOON_C = Vector((0.0, 0.0, H + 0.62 + BALLOON_R))
FAN_R = 0.62
FAN_C = [("FR", 1.8, 1.75), ("FL", -1.8, 1.75), ("BR", 1.8, -1.75), ("BL", -1.8, -1.75)]
FAN_Z = 0.16                         # duct bottom
FAN_H = 0.46                         # duct height; the pivot is at its middle

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
col = bpy.context.scene.collection


# ------------------------------------------------------------------ materials and textures
def image(name, w, h, rgba):
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(rgba, dtype=np.float32).ravel())
    img.pack()
    return img


def mat(name, color, rough=0.5, metal=0.0, alpha=1.0, tex=None, emit=None, emit_strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1.0)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if tex is not None:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = tex
        nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    if emit is not None:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = emit
        nt.links.new(t.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = emit_strength
    if alpha < 1.0:
        p.inputs["Alpha"].default_value = alpha
        m.surface_render_method = "BLENDED"
        m.use_backface_culling = False
    return m


def fabric_texture():
    # white envelope fabric: a faint weave, a seam down every gore (meridians, 16) and round the
    # equator; u runs round the balloon's nose axis, v pole to pole
    w, h = 2048, 1024
    u = (np.arange(w) + 0.5) / w
    v = (np.arange(h) + 0.5) / h
    uu, vv = np.meshgrid(u, v)
    rng = np.random.default_rng(7)
    base = 0.9 + 0.025 * rng.standard_normal((h, w))
    base += 0.012 * np.sin(uu * w * 0.9) * np.sin(vv * h * 0.9)
    gore = np.abs(((uu * 16.0) + 0.5) % 1.0 - 0.5) * (w / 16.0)          # px to the nearest seam
    seam = np.clip(1.0 - gore / 3.0, 0.0, 1.0)
    eq = np.clip(1.0 - np.abs(vv - 0.5) * h / 2.0, 0.0, 1.0)
    bulge = np.sin(np.pi * (((uu * 16.0) % 1.0)))                         # each gore puffs out between seams
    shade = base * (0.9 + 0.1 * bulge) * (1.0 - 0.38 * np.maximum(seam, eq))
    # the tape either side of each seam sits a touch proud: a lighter edge
    shade += 0.03 * np.clip(1.0 - np.abs(gore - 4.0) / 1.5, 0.0, 1.0)
    shade = np.clip(shade, 0.0, 1.0)
    rgba = np.stack([shade * 0.97, shade * 0.975, shade, np.ones_like(shade)], axis=-1)
    return image("fabric", w, h, rgba)


def screen_texture():
    # the pilot's display: three dark panels -- a green trace, a round airspeed gauge, level bars
    w, h = 768, 256
    img = np.zeros((h, w, 4), dtype=np.float32)
    img[..., :3] = (0.015, 0.025, 0.03)
    img[..., 3] = 1.0
    yy, xx = np.mgrid[0:h, 0:w]
    y_up = h - 1 - yy                                    # Blender images start at the bottom row
    for x0 in (0, 256, 512):                             # panel borders
        img[((xx - x0) % 256 < 3) | ((xx - x0) % 256 > 252) | (y_up < 3) | (y_up > 252), :3] = (0.2, 0.22, 0.24)
    # trace
    tx = xx[:, :240]
    trace = 150 + 38 * np.sin(tx / 14.0) * np.cos(tx / 41.0)
    m = (np.abs(y_up[:, :240] - trace) < 2.2) & (tx > 14)
    img[:, :240][m, :3] = (0.3, 0.95, 0.45)
    for k in range(5):                                   # small readouts under it
        img[(y_up > 40 + k * 14) & (y_up < 46 + k * 14) & (xx > 20) & (xx < 60 + 25 * ((k * 7) % 4)), :3] = (0.55, 0.7, 0.6)
    # gauge
    r = np.hypot(xx - 384, y_up - 128)
    ang = np.arctan2(y_up - 128, xx - 384)
    img[(np.abs(r - 90) < 3) & (ang > -0.6), :3] = (0.75, 0.8, 0.85)
    img[(np.abs(r - 90) < 5) & (ang > 0.4) & (ang < 2.6), :3] = (0.3, 0.9, 0.5)
    img[(r < 22) & (r > 18), :3] = (0.9, 0.9, 0.95)
    # level bars
    for k in range(6):
        y0 = 200 - k * 30
        ln = 60 + ((k * 53) % 150)
        img[(y_up > y0) & (y_up < y0 + 10) & (xx > 540) & (xx < 540 + ln), :3] = (0.3, 0.85, 0.45) if k % 3 else (0.9, 0.75, 0.25)
    return image("screen", w, h, img)


M = {
    "white": mat("body_white", (0.86, 0.87, 0.89), rough=0.3),
    "blue": mat("body_blue", (0.16, 0.24, 0.42), rough=0.35),
    # satin, not mirror: the station has no sky for a full metal to reflect, and renders it black
    "silver": mat("silver", (0.8, 0.81, 0.83), rough=0.3, metal=0.35),
    "glass": mat("glass", (0.03, 0.05, 0.07), rough=0.05, alpha=0.32),
    "acrylic": mat("acrylic", (0.7, 0.8, 0.85), rough=0.05, alpha=0.14),      # the clear floor and chin
    "seat": mat("seat_leather", (0.03, 0.03, 0.035), rough=0.55),
    "floor": mat("floor", (0.18, 0.19, 0.2), rough=0.8),
    "dash": mat("dash", (0.72, 0.73, 0.75), rough=0.35),
    "dark": mat("dark_trim", (0.05, 0.055, 0.06), rough=0.45),
    "screen": mat("screen", (0.02, 0.02, 0.02), rough=0.2, emit=screen_texture(), emit_strength=1.6),
    "fabric": mat("balloon_fabric", (1, 1, 1), rough=0.7, tex=fabric_texture()),
    "cable": mat("cable", (0.2, 0.21, 0.22), rough=0.4, metal=0.3),
    "rubber": mat("rubber", (0.02, 0.02, 0.02), rough=0.8),
    "fan": mat("fan_metal", (0.58, 0.6, 0.63), rough=0.4, metal=0.35),
    "lamp": mat("cabin_lamp", (0.9, 0.9, 0.85), rough=0.3, emit=image("lamp", 4, 4, np.ones((4, 4, 4))), emit_strength=2.0),
    "liner": mat("liner", (0.62, 0.63, 0.65), rough=0.6),
}
M_LIST = list(M.keys())


# ------------------------------------------------------------------ mesh helpers
class Mesh:
    """Faces with a material key each, turned into one object."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def face(self, pts, m, uvs=None):
        vs = [self.bm.verts.new(p) for p in pts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = M_LIST.index(m)
        if uvs:
            for lp, uv in zip(f.loops, uvs):
                lp[self.uv].uv = uv
        return f

    def box(self, lo, hi, m, xf=Matrix()):
        (x0, y0, z0), (x1, y1, z1) = lo, hi
        c = [xf @ Vector(p) for p in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                      (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
        for q in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            self.face([c[i] for i in q], m)

    def tube(self, p0, p1, r, m, n=8, caps=True):
        p0, p1 = Vector(p0), Vector(p1)
        d = (p1 - p0).normalized()
        a = d.orthogonal().normalized()
        b = d.cross(a)
        ring0 = [p0 + (a * math.cos(TAU * k / n) + b * math.sin(TAU * k / n)) * r for k in range(n)]
        ring1 = [p + (p1 - p0) for p in ring0]
        for k in range(n):
            self.face([ring0[k], ring0[(k + 1) % n], ring1[(k + 1) % n], ring1[k]], m)
        if caps:
            self.face(list(reversed(ring0)), m)
            self.face(ring1, m)

    def lathe(self, prof, c, m, n=40, flip=False):
        """prof: [(r, z)] bottom to top; revolved about the vertical through c."""
        rings = [[Vector((c[0] + r * math.cos(TAU * k / n), c[1] + r * math.sin(TAU * k / n), z)) for k in range(n)]
                 for r, z in prof]
        for i in range(len(rings) - 1):
            for k in range(n):
                q = [rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]]
                self.face(list(reversed(q)) if flip else q, m)

    def obj(self, smooth=True, solidify=0.0, parent=None):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-5)
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        for key in M_LIST:
            me.materials.append(M[key])
        for p in me.polygons:
            p.use_smooth = smooth
        ob = bpy.data.objects.new(self.name, me)
        col.objects.link(ob)
        if solidify:
            s = ob.modifiers.new("solid", "SOLIDIFY")
            s.thickness = solidify
            s.offset = -1.0
        if parent:
            ob.parent = parent
        return ob


TAU = math.tau


# ------------------------------------------------------------------ cabin shell
def plan(t, k=1.0):
    c, s = math.cos(t), math.sin(t)
    return (A * k * math.copysign(abs(c) ** (2.0 / N), c), B * k * math.copysign(abs(s) ** (2.0 / N), s))


def t_side(y, right=True):
    """Angle on the plan where a long side reaches y."""
    t = math.asin(min(1.0, (abs(y) / B) ** (N / 2.0)))
    t = math.copysign(t, y)
    return t if right else math.pi - t


def t_end(x, front=True):
    """Angle on the plan where an end reaches x."""
    t = math.acos(min(1.0, (abs(x) / A) ** (N / 2.0)))
    if x < 0:
        t = math.pi - t
    return t if front else -t


def profile(z):
    """Plan scale at height z: a rounded belly, near-straight sides, a domed roof."""
    if z < BELLY_TOP + 0.12:
        d = (BELLY_TOP + 0.12 - z) / (BELLY_TOP + 0.12)
        return (1.0 - d ** 2.4) ** (1.0 / 2.4)
    if z < ROOF0:
        return 1.0 - 0.035 * (z - BELLY_TOP - 0.12) / (ROOF0 - BELLY_TOP - 0.12)
    d = min(1.0, (z - ROOF0) / (H - ROOF0))
    return 0.965 * (1.0 - d ** 2.2) ** (1.0 / 2.2)


def wrap(t):
    return (t + math.pi) % TAU - math.pi


# glass and the door openings as angle intervals round the plan (in window band heights)
PILLAR = 0.05
glass_iv, door_iv = [], []
for right in (True, False):
    door_iv.append(sorted([t_side(DOOR_Y - DOOR_HW, right), t_side(DOOR_Y + DOOR_HW, right)]))
    glass_iv.append(sorted([t_side(DOOR_Y + DOOR_HW + 0.12, right), t_side(B - 0.55, right)]))
    glass_iv.append(sorted([t_side(DOOR_Y - DOOR_HW - 0.12, right), t_side(-(B - 0.55), right)]))
for front in (True, False):
    for sx in (1, -1):
        glass_iv.append(sorted([t_end(sx * PILLAR, front), t_end(sx * 0.9, front)]))           # the big panes
        side_t = t_side((1 if front else -1) * (B - 0.47), sx > 0)
        glass_iv.append(sorted([t_end(sx * 0.98, front), side_t], key=lambda a: a) if abs(wrap(t_end(sx * 0.98, front) - side_t)) < 1.0 else [0, 0])
glass_iv = [[wrap(a), wrap(b)] for a, b in glass_iv]
door_iv = [[wrap(a), wrap(b)] for a, b in door_iv]


def in_iv(t, ivs):
    t = wrap(t)
    for a, b in ivs:
        lo, hi = min(a, b), max(a, b)
        if hi - lo > math.pi:                           # an interval across the +-pi seam
            if t >= hi or t <= lo:
                return True
        elif lo <= t <= hi:
            return True
    return False


# perimeter samples: an even spread plus every interval boundary, so window edges fall on the grid
ts = {round(wrap(TAU * k / 160.0), 6) for k in range(160)}
for a, b in glass_iv + door_iv:
    ts.add(round(a, 6))
    ts.add(round(b, 6))
for right in (True, False):                             # where the chin glazing starts
    ts.add(round(wrap(t_side(CHIN_Y, right)), 6))
ts = sorted(ts)
zs = sorted({round(z, 4) for z in list(np.linspace(0.0, BELLY_TOP + 0.12, 14)) + list(np.linspace(BELLY_TOP + 0.12, ROOF0, 18))
             + list(np.linspace(ROOF0, H, 10)) + [FLOOR, BELLY_TOP, BAND_TOP, WIN_TOP]})
zs[0] = 0.02                                            # a small flat underside, not a point

body = Mesh("cabin")
glass = Mesh("cabin_glass")
ring = [[Vector((*plan(t, profile(z)), z)) for t in ts] for z in zs]
nt = len(ts)
for i in range(len(zs) - 1):
    zc = 0.5 * (zs[i] + zs[i + 1])
    for j in range(nt):
        t0, t1 = ts[j], ts[(j + 1) % nt]
        tc = wrap(t0 + wrap(t1 - t0) * 0.5)
        q = [ring[i][j], ring[i][(j + 1) % nt], ring[i + 1][(j + 1) % nt], ring[i + 1][j]]
        if FLOOR <= zc <= WIN_TOP and in_iv(tc, door_iv):
            continue                                        # the doorway
        if BAND_TOP <= zc <= WIN_TOP and in_iv(tc, glass_iv):
            glass.face(q, "glass")
            continue
        if zc < BELLY_TOP and zs[i] >= 0.05 and sum(v.y for v in q) / 4.0 > CHIN_Y:
            glass.face(q, "acrylic")                        # the chin: see down past your feet
            continue
        m = "blue" if zc < BELLY_TOP else ("white" if zc < ROOF0 else "silver")
        body.face(q, m)
# the underside cap
body.face(list(reversed(ring[0])), "blue")
cabin = body.obj(solidify=0.045)
glass.obj()

# ------------------------------------------------------------------ doorways: jambs, sills, pocket doors
LEAF_X = 1.0                         # the leaves run on a track this far out, inside the hull
trim = Mesh("trim")
for right in (True, False):
    sx = 1 if right else -1
    xo = plan(0.0)[0] + 0.01                                    # the hull's side
    lo_x, hi_x = sorted([sx * (LEAF_X - 0.04), sx * xo])
    for e in (-1, 1):                                           # jambs: a portal from hull to track
        y = DOOR_Y + e * DOOR_HW
        trim.box((lo_x, y - 0.04 if e > 0 else y, FLOOR), (hi_x, y if e > 0 else y + 0.04, WIN_TOP), "silver")
    trim.box((lo_x, DOOR_Y - DOOR_HW, WIN_TOP - 0.04), (hi_x, DOOR_Y + DOOR_HW, WIN_TOP + 0.02), "silver")  # head
    s_lo, s_hi = sorted([sx * 0.88, sx * (xo + 0.02)])
    trim.box((s_lo, DOOR_Y - DOOR_HW, FLOOR - 0.03), (s_hi, DOOR_Y + DOOR_HW, FLOOR + 0.005), "silver")     # step plate
    # a boarding step outside the doorway, on two brackets (the game walks it as a ramp)
    p_lo, p_hi = sorted([sx * (xo - 0.02), sx * (xo + 0.34)])
    trim.box((p_lo, DOOR_Y - 0.5, 0.15), (p_hi, DOOR_Y + 0.5, 0.19), "silver")
    for by in (DOOR_Y - 0.4, DOOR_Y + 0.4):
        trim.box((min(sx * (xo - 0.02), sx * (xo + 0.06)), by - 0.02, 0.15),
                 (max(sx * (xo - 0.02), sx * (xo + 0.06)), by + 0.02, FLOOR - 0.02), "silver")
    # the track the leaves hang from, running back into both pockets
    t_lo, t_hi = sorted([sx * (LEAF_X - 0.05), sx * (LEAF_X + 0.05)])
    trim.box((t_lo, DOOR_Y - 1.24, WIN_TOP + 0.02), (t_hi, DOOR_Y + 1.24, WIN_TOP + 0.06), "dark")
# a silver strip along the window band's sill and head, all round the outside
for z in (BAND_TOP, WIN_TOP):
    k = profile(z) + 0.004
    for j in range(nt):
        t0, t1 = ts[j], ts[(j + 1) % nt]
        tc = wrap(t0 + wrap(t1 - t0) * 0.5)
        if in_iv(tc, door_iv):
            continue
        p0, p1 = Vector((*plan(t0, k), z)), Vector((*plan(t1, k), z))
        o0, o1 = Vector((*plan(t0, k + 0.012), z)), Vector((*plan(t1, k + 0.012), z))
        trim.face([p0, p1, o1 + Vector((0, 0, 0.025)), o0 + Vector((0, 0, 0.025))], "silver")
        trim.face([o0 + Vector((0, 0, 0.025)), o1 + Vector((0, 0, 0.025)), p1 + Vector((0, 0, 0.05)), p0 + Vector((0, 0, 0.05))], "silver")
# pillars between the panes
for a, b in glass_iv:
    for t in (a, b):
        if abs(t) < 1e-6:
            continue
        p0 = Vector((*plan(t, profile(BAND_TOP) + 0.01), BAND_TOP))
        p1 = Vector((*plan(t, profile(WIN_TOP) + 0.01), WIN_TOP))
        trim.tube(p0, p1, 0.03, "silver", n=6)
trim.obj()

for right in (True, False):
    sx = 1 if right else -1
    for k, ys in ((1, 1), (2, -1)):
        leaf = Mesh("door_%s%d" % ("R" if right else "L", k))
        lo_y, hi_y = sorted([0.0, ys * DOOR_HW])
        # frame, a white kick panel, glass above -- built about x = 0, placed on the track
        leaf.box((-0.022, lo_y, FLOOR), (0.022, hi_y, FLOOR + 0.55), "white")
        leaf.box((-0.03, lo_y, FLOOR), (0.03, lo_y + 0.05, WIN_TOP - 0.04), "silver")
        leaf.box((-0.03, hi_y - 0.05, FLOOR), (0.03, hi_y, WIN_TOP - 0.04), "silver")
        leaf.box((-0.03, lo_y, WIN_TOP - 0.09), (0.03, hi_y, WIN_TOP - 0.04), "silver")
        leaf.box((-0.03, lo_y, FLOOR + 0.52), (0.03, hi_y, FLOOR + 0.57), "silver")
        leaf.face([Vector((0, lo_y + 0.05, FLOOR + 0.57)), Vector((0, hi_y - 0.05, FLOOR + 0.57)),
                   Vector((0, hi_y - 0.05, WIN_TOP - 0.09)), Vector((0, lo_y + 0.05, WIN_TOP - 0.09))], "glass")
        # a grab handle on the inner face near the meeting edge
        hy = (hi_y - 0.12) if ys > 0 else (lo_y + 0.12)
        leaf.tube(Vector((-sx * 0.03, hy, FLOOR + 0.9)), Vector((-sx * 0.03, hy, FLOOR + 1.3)), 0.014, "silver", n=6)
        ob = leaf.obj(smooth=False)
        ob.location = (sx * LEAF_X, DOOR_Y, 0.0)

# ------------------------------------------------------------------ interior
inner = Mesh("interior")
def floor_half_width(y):
    k = profile(FLOOR) - 0.02
    return A * k * max(0.0, 1.0 - (abs(y) / (B * k)) ** N) ** (1.0 / N)


# the floor in strips across the cabin: a ribbed mat aft of CHIN_Y, acrylic ahead of it
yk = B * (profile(FLOOR) - 0.02)
ys_ = sorted(set(list(np.linspace(-yk, yk, 40)) + [CHIN_Y]))
for y0, y1 in zip(ys_[:-1], ys_[1:]):
    w0, w1 = floor_half_width(y0), floor_half_width(y1)
    m = "acrylic" if y0 >= CHIN_Y - 1e-6 else "floor"
    inner.face([Vector((-w0, y0, FLOOR)), Vector((w0, y0, FLOOR)), Vector((w1, y1, FLOOR)), Vector((-w1, y1, FLOOR))], m)
for yy in np.arange(-yk + 0.3, CHIN_Y - 0.05, 0.12):          # ribs on the mat
    w = floor_half_width(yy) - 0.1
    inner.box((-w, yy - 0.012, FLOOR), (w, yy + 0.012, FLOOR + 0.006), "dark")
# the acrylic's frame: a sill across at the chin line, ribs across and along, and a keel
fy1 = yk - 0.05
inner.box((-floor_half_width(CHIN_Y), CHIN_Y - 0.03, FLOOR - 0.01), (floor_half_width(CHIN_Y), CHIN_Y + 0.03, FLOOR + 0.02), "silver")
for yy in np.arange(CHIN_Y + 0.45, fy1, 0.45):
    w = floor_half_width(yy)
    inner.box((-w, yy - 0.02, FLOOR - 0.01), (w, yy + 0.02, FLOOR + 0.015), "silver")
for xx in (-0.5, 0.0, 0.5):
    inner.box((xx - 0.02, CHIN_Y, FLOOR - 0.01), (xx + 0.02, fy1, FLOOR + 0.015), "silver")
# small rubber pads for the front sitters' feet, on the frame ahead of each seat
for sx_ in (-0.5, 0.5):
    for fx in (-0.13, 0.13):
        inner.box((sx_ + fx - 0.075, SEAT_Y + 0.5, FLOOR + 0.015), (sx_ + fx + 0.075, SEAT_Y + 0.78, FLOOR + 0.04), "rubber")
        inner.box((sx_ + fx - 0.02, SEAT_Y + 0.5, FLOOR - 0.01), (sx_ + fx + 0.02, SEAT_Y + 0.78, FLOOR + 0.015), "silver")


def bucket_seat(m, x, y, xf_yaw=0.0):
    """A bucket seat on a pedestal, facing +Y, hips at (x, y, FLOOR + 0.5)."""
    base = Matrix.Translation((x, y, FLOOR)) @ Matrix.Rotation(xf_yaw, 4, "Z")
    m.box((-0.12, -0.15, 0.0), (0.12, 0.15, 0.3), "silver", xf=base)                           # pedestal
    m.box((-0.27, -0.26, 0.3), (0.27, 0.26, 0.4), "dark", xf=base)                             # pan
    m.box((-0.25, -0.24, 0.4), (0.25, 0.25, 0.5), "seat", xf=base)                             # cushion
    for sxs in (-1, 1):                                                                        # bolsters
        m.box((sxs * 0.25 - 0.04, -0.24, 0.4), (sxs * 0.25 + 0.04, 0.25, 0.56), "seat", xf=base)
    back = base @ Matrix.Translation((0, -0.24, 0.45)) @ Matrix.Rotation(math.radians(12), 4, "X")   # reclined (toward -Y)
    m.box((-0.26, -0.1, 0.0), (0.26, 0.02, 0.72), "seat", xf=back)
    m.box((-0.13, -0.09, 0.76), (0.13, 0.03, 0.98), "seat", xf=back)                          # headrest
    m.box((-0.04, -0.06, 0.7), (0.04, -0.02, 0.78), "silver", xf=back)
    for sxs in (-1, 1):                                                                        # armrests
        m.box((sxs * 0.3 - 0.035, -0.2, 0.6), (sxs * 0.3 + 0.035, 0.18, 0.66), "seat", xf=base)
        m.box((sxs * 0.3 - 0.015, -0.05, 0.4), (sxs * 0.3 + 0.015, 0.0, 0.6), "silver", xf=base)


bucket_seat(inner, 0.5, SEAT_Y)                             # the pilot's, on the right as in the reference
bucket_seat(inner, -0.5, SEAT_Y)
# the rear bench: three cushions, three back pads
inner.box((-0.85, REAR_Y - 0.23, FLOOR), (0.85, REAR_Y + 0.23, FLOOR + 0.38), "dark")
for cx in (-0.56, 0.0, 0.56):
    inner.box((cx - 0.27, REAR_Y - 0.21, FLOOR + 0.38), (cx + 0.27, REAR_Y + 0.25, FLOOR + 0.52), "seat")
    rot = Matrix.Translation((cx, REAR_Y - 0.21, FLOOR + 0.52)) @ Matrix.Rotation(math.radians(10), 4, "X")
    inner.box((-0.27, -0.06, 0.02), (0.27, 0.08, 0.66), "seat", xf=rot)
# the dash: a curved top across the nose, a dark fascia under it
dash_z1 = BAND_TOP + 0.1
for j in range(nt):
    t0, t1 = ts[j], ts[(j + 1) % nt]
    if not (0.6 < t0 < math.pi - 0.6 and 0.6 < t1 < math.pi - 0.6):
        continue
    k0 = profile(BAND_TOP) - 0.04
    a0, a1 = Vector((*plan(t0, k0), dash_z1)), Vector((*plan(t1, k0), dash_z1))
    b0, b1 = Vector((*plan(t0, k0 - 0.2), dash_z1 - 0.02)), Vector((*plan(t1, k0 - 0.2), dash_z1 - 0.02))
    c0, c1 = Vector((b0.x, b0.y, dash_z1 - 0.3)), Vector((b1.x, b1.y, dash_z1 - 0.3))
    inner.face([b1, b0, a0, a1], "dash")
    inner.face([c1, c0, b0, b1], "liner")
sy = plan(math.pi / 2, profile(BAND_TOP) - 0.24)[1]
# the pilot's display, in a raised hood on the right
scr = Matrix.Translation((0.45, sy, dash_z1 - 0.02)) @ Matrix.Rotation(math.radians(-20), 4, "X")
inner.box((-0.5, -0.02, -0.04), (0.5, 0.08, 0.33), "dash", xf=scr)
inner.face([scr @ Vector((-0.46, -0.025, 0.0)), scr @ Vector((0.46, -0.025, 0.0)),
            scr @ Vector((0.46, -0.025, 0.29)), scr @ Vector((-0.46, -0.025, 0.29))], "screen",
           uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
# a button block beside it
for bx in range(2):
    for bz in range(3):
        inner.box((0.97 + bx * 0.07, sy - 0.05, dash_z1 + 0.03 + bz * 0.07), (1.02 + bx * 0.07, sy, dash_z1 + 0.08 + bz * 0.07), "dark")
# the yoke: a column out of the fascia, a hub, a bar and two upright horns
yc = Vector((0.5, sy - 0.42, dash_z1 - 0.08))
inner.tube(Vector((0.5, sy - 0.05, dash_z1 - 0.16)), yc + Vector((0, 0.05, 0)), 0.035, "silver", n=10)
inner.box((-0.09, -0.04, -0.07), (0.09, 0.04, 0.05), "dark", xf=Matrix.Translation(yc))
inner.box((-0.05, -0.045, -0.03), (0.05, -0.04, 0.02), "screen", xf=Matrix.Translation(yc))
for sxs in (-1, 1):
    inner.tube(yc + Vector((0.08 * sxs, 0, -0.02)), yc + Vector((0.2 * sxs, 0, -0.03)), 0.022, "silver", n=8)
    inner.tube(yc + Vector((0.2 * sxs, 0, -0.03)), yc + Vector((0.23 * sxs, -0.02, 0.16)), 0.026, "silver", n=8)
    inner.box((-0.025, -0.025, 0.0), (0.025, 0.025, 0.03), "dark", xf=Matrix.Translation(yc + Vector((0.23 * sxs, -0.02, 0.16))))
# ceiling: a light panel, the hatch's inner frame, grab rails along both sides
cz = H - 0.2
inner.box((-0.42, -1.25, cz), (0.42, 1.25, cz + 0.03), "liner")
inner.face([Vector((-0.38, -1.2, cz - 0.001)), Vector((-0.38, 1.2, cz - 0.001)), Vector((0.38, 1.2, cz - 0.001)),
            Vector((0.38, -1.2, cz - 0.001))], "lamp")
for sxs in (-1, 1):
    x = sxs * 0.82
    inner.tube(Vector((x, -1.5, WIN_TOP - 0.02)), Vector((x, 1.5, WIN_TOP - 0.02)), 0.018, "silver", n=8)
    for yy in (-1.4, 0.0, 1.4):
        inner.tube(Vector((x, yy, WIN_TOP - 0.02)), Vector((x * 0.93, yy, H - 0.12)), 0.012, "silver", n=6)
inner.obj(smooth=False)

# seat and exit points for the game
for name, loc in (("seat_pilot", (0.5, SEAT_Y, FLOOR + 0.5)), ("seat_passenger", (-0.5, SEAT_Y, FLOOR + 0.5)),
                  ("seat_rear_L", (-0.56, REAR_Y, FLOOR + 0.52)), ("seat_rear_C", (0.0, REAR_Y, FLOOR + 0.52)),
                  ("seat_rear_R", (0.56, REAR_Y, FLOOR + 0.52)), ("exit_R", (1.75, DOOR_Y, 0.0)), ("exit_L", (-1.75, DOOR_Y, 0.0))):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    col.objects.link(e)

# ------------------------------------------------------------------ roof frame, A-frame, balloon
rig = Mesh("rig")
RX, RY, RZ = 0.72, 1.5, H - 0.06
corners = [Vector((sx * RX, sy_ * RY, RZ)) for sx, sy_ in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
for k in range(4):
    rig.tube(corners[k], corners[(k + 1) % 4], 0.03, "silver")
    rig.tube(corners[k] - Vector((0, 0, 0.12)), corners[k], 0.025, "silver")
rig.box((-0.32, -0.32, H - 0.1), (0.32, 0.32, H + 0.03), "dark")          # the roof hatch
top = BALLOON_C.z - BALLOON_R * 0.97
for sy_ in (-0.45, 0.45):
    apex = Vector((0.0, sy_, top))
    rig.tube(Vector((RX, sy_ * 1.6, RZ)), apex, 0.035, "silver")
    rig.tube(Vector((-RX, sy_ * 1.6, RZ)), apex, 0.035, "silver")
rig.tube(Vector((0, -0.55, top)), Vector((0, 0.55, top)), 0.045, "silver")
rig.box((-0.25, -0.35, top), (0.25, 0.35, top + 0.08), "silver")         # the saddle under the envelope
for c in corners:
    d = Vector((math.copysign(0.78, c.x), math.copysign(0.3, c.y), -0.55)).normalized()
    hp = BALLOON_C + d * BALLOON_R
    rig.tube(c, hp, 0.012, "cable", n=5)
    rig.box((-0.06, -0.06, -0.03), (0.06, 0.06, 0.03), "cable", xf=Matrix.Translation(hp))
rig.obj()

bm = bmesh.new()
bm.loops.layers.uv.new("UVMap")                                 # calc_uvs fills the active layer: it must exist
bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=28, radius=BALLOON_R, calc_uvs=True)
me = bpy.data.meshes.new("balloon")
bm.to_mesh(me)
me.materials.append(M["fabric"])
for p in me.polygons:
    p.use_smooth = True
balloon = bpy.data.objects.new("balloon", me)
col.objects.link(balloon)
balloon.location = BALLOON_C
balloon.rotation_euler = (math.radians(-90), 0.0, 0.0)          # its poles on the nose axis: the rosette faces forward

# ------------------------------------------------------------------ ducted fans: body-fixed arms and gear, tilting engines
arms = Mesh("arms")
PIVOT_Z = FAN_Z + FAN_H * 0.5
for name, fx, fy in FAN_C:
    sx = math.copysign(1.0, fx)
    pin = Vector((fx - sx * (FAN_R + 0.1), fy, PIVOT_Z))                   # the inner trunnion bearing
    root_ = Vector((sx * plan(0.0, profile(PIVOT_Z))[0] * 0.92, fy * 0.82, PIVOT_Z))
    arms.tube(root_, pin, 0.06, "silver", n=10)
    # the bearing housing, its axis along x
    arms.tube(pin - Vector((sx * 0.02, 0, 0)), pin + Vector((sx * 0.08, 0, 0)), 0.09, "fan", n=14)
    # landing leg and caster under the bearing
    arms.tube(pin, Vector((pin.x, pin.y, 0.14)), 0.03, "dark", n=6)
    arms.tube(Vector((pin.x - 0.035, pin.y, 0.07)), Vector((pin.x + 0.035, pin.y, 0.07)), 0.07, "rubber", n=12)
arms.obj()

for name, fx, fy in FAN_C:
    sx = math.copysign(1.0, fx)
    eng = bpy.data.objects.new("engine_" + name, None)
    eng.location = (fx, fy, PIVOT_Z)
    col.objects.link(eng)
    duct = Mesh("duct_" + name)
    z0, z1 = -FAN_H * 0.5, FAN_H * 0.5
    duct.lathe([(FAN_R - 0.1, z0 + 0.02), (FAN_R - 0.04, z0), (FAN_R, z0 + 0.06), (FAN_R, z1 - 0.04), (FAN_R - 0.03, z1),
                (FAN_R - 0.08, z1 - 0.01), (FAN_R - 0.1, z1 - 0.06), (FAN_R - 0.1, z0 + 0.02)], (0, 0), "fan", n=44)
    duct.lathe([(FAN_R - 0.004, -0.06), (FAN_R + 0.006, -0.06), (FAN_R + 0.006, -0.02), (FAN_R - 0.004, -0.02)], (0, 0), "blue", n=44)
    for a in (0.0, math.pi / 2):                                            # stator cross and motor pod
        d = Vector((math.cos(a), math.sin(a), 0)) * (FAN_R - 0.1)
        duct.tube(Vector((0, 0, z0 + 0.1)) - d, Vector((0, 0, z0 + 0.1)) + d, 0.022, "fan", n=6)
    duct.lathe([(0.0, z0 + 0.05), (0.1, z0 + 0.08), (0.12, z0 + 0.2), (0.12, z0 + 0.28)], (0, 0), "fan", n=20)
    # trunnion pins both sides, on the tilt axis (x)
    for side in (-1, 1):
        duct.tube(Vector((side * (FAN_R - 0.02), 0, 0)), Vector((side * (FAN_R + 0.1), 0, 0)), 0.045, "silver", n=10)
    dob = duct.obj()
    dob.parent = eng
    rotor = Mesh("rotor_" + name)
    rotor.lathe([(0.0, 0.0), (0.12, 0.0), (0.12, 0.04), (0.09, 0.12), (0.045, 0.16), (0.0, 0.17)], (0, 0), "silver", n=20)
    for k in range(8):
        a = TAU * k / 8
        rot = Matrix.Rotation(a, 4, "Z") @ Matrix.Rotation(math.radians(28), 4, "X")
        rotor.box((0.1, -0.05, -0.007), (FAN_R - 0.12, 0.05, 0.007), "fan", xf=Matrix.Translation((0, 0, 0.03)) @ rot)
    rob = rotor.obj(smooth=False)
    rob.parent = eng
    rob.location = (0, 0, z0 + 0.28)

# ------------------------------------------------------------------ export
root = bpy.data.objects.new("aerostat", None)
col.objects.link(root)
for ob in list(col.objects):
    if ob is not root and ob.parent is None:
        ob.parent = root
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_apply=True, export_yup=True)
print("AEROSTAT_EXPORTED", OUT)

# ------------------------------------------------------------------ preview renders (optional)
if RENDER:
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = sc.render.resolution_y = 900
    try:
        sc.eevee.taa_render_samples = 32
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.93, 0.94, 0.96, 1)
    bg.inputs[1].default_value = 0.75
    sc.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 2.6
    sun.rotation_euler = (math.radians(40), math.radians(15), math.radians(30))
    col.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    col.objects.link(cam)
    sc.camera = cam
    # right-side doors open, as on the reference sheet; the fans tilted a little to show they pivot
    bpy.data.objects["door_R1"].location.y += DOOR_SLIDE
    bpy.data.objects["door_R2"].location.y -= DOOR_SLIDE
    centre = Vector((0, 0, 3.4))

    def shoot(tag, az, el, dist, lens=50, tgt=centre):
        cam.data.lens = lens
        d = Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)), math.cos(math.radians(az)) * math.cos(math.radians(el)),
                    math.sin(math.radians(el))))
        cam.location = tgt + d * dist
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = "%s_%s.png" % (RENDER, tag)
        bpy.ops.render.render(write_still=True)

    shoot("front", 0, 8, 17)
    shoot("side", 90, 8, 17)
    shoot("q_left", 215, 22, 16)
    shoot("q_right", 35, 22, 16)
    for name, _, _ in FAN_C:
        bpy.data.objects["engine_" + name].rotation_euler.x = math.radians(-30)   # thrust tilted aft: flying forward
    shoot("tilt", 120, 12, 9, tgt=Vector((0, 0, 1.0)))
    for name, _, _ in FAN_C:
        bpy.data.objects["engine_" + name].rotation_euler.x = 0.0
    shoot("door", 60, 6, 6.5, lens=35, tgt=Vector((0.4, 0.2, 1.2)))
    # the pilot's view from the right seat
    L = bpy.data.objects.new("cabin_light", bpy.data.lights.new("cabin_light", "POINT"))
    L.data.energy = 40
    L.location = (0, 0, H - 0.5)
    col.objects.link(L)
    cam.data.lens = 16
    cam.location = (0.5, SEAT_Y - 0.05, FLOOR + 1.22)
    cam.rotation_euler = (math.radians(80), 0, 0)
    bg.inputs[0].default_value = (0.55, 0.72, 0.92, 1)
    sc.render.filepath = "%s_pilot.png" % RENDER
    bpy.ops.render.render(write_still=True)
    cam.location = (0.0, REAR_Y + 0.4, FLOOR + 1.35)
    cam.rotation_euler = (math.radians(76), 0, 0)
    sc.render.filepath = "%s_cabin.png" % RENDER
    bpy.ops.render.render(write_still=True)
    print("AEROSTAT_RENDERED")
