"""
groundcar.py -- the station's ground vehicles (the user's references, ~/Downloads/car 1*.jpg and
grok-image-5f061cc2*.jpg), two variants:

  pod   a small electric people-mover: a white shell with a blue band and black skirt, a wrap-round
        blue-tinted windscreen, big side glass, sliding double doors each side, white-and-blue
        seats, and inside a white dash with a blue light strip, a screen and a yoke wheel (car 1
        cockpit.jpg); left-hand drive
  van   a retro-futurist 1970s-style minibus: a mustard lower body with a woodgrain side panel
        in chrome trim, a white upper body and roof, a long window band, a silver grille with quad
        round headlights and a blue light line, white-wall tyres with chrome hubcaps, tan seats
        in three rows; a sliding side door each side behind the front seats

  flatpak run org.blender.Blender -b --factory-startup --python <abs groundcar.py> -- VARIANT OUT_GLB [RENDER_PREFIX]

Blender Z up, the nose toward +Y (glTF -Z, Godot's forward).  Metres; z = 0 is where the tyres
touch the ground.  The rig (names are the contract with remake/scripts/vehicles/ground_vehicle.gd):
  wheel_{FL,FR,BL,BR}   the wheels, pivot at the hub: spin about local X; the front pair steer about Z
  steering_wheel        the driver's wheel / yoke, pivot at its hub: turns about its local Y (column)
  door_{L,R}{n}         sliding door leaves, closed; n odd slides toward the nose, even toward the tail
  seat_pilot, seat_*    where sitters' hips go, facing +Y;  exit_{L,R} outside each doorway
"""
import math
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
VARIANT = argv[0] if argv else "pod"
OUT = argv[1] if len(argv) > 1 else "/tmp/%s.glb" % VARIANT
RENDER = argv[2] if len(argv) > 2 else None
TAU = math.tau

CFG = {
    "pod": dict(A=0.95, BF=2.0, BR=1.95, H=2.35, N=5.0, BASE=0.26, FLOOR=0.42, WR=0.36, WW=0.24, WY=(1.32, -1.3),
                TRACK=0.80, WIN=(1.12, 2.08), DOOR_Y=-0.12, DOOR_HW=0.62, DOOR_SLIDE=0.6,
                SCREEN_Z=(0.9, 2.18), SCREEN_Y=(1.97, 1.18), SEAT_Y=0.72, REAR_Y=(-1.25,), DRIVER_X=-0.42),
    "van": dict(A=1.0, BF=2.6, BR=2.55, H=2.42, N=6.0, BASE=0.3, FLOOR=0.55, WR=0.4, WW=0.26, WY=(1.72, -1.62),
                TRACK=0.84, WIN=(1.28, 2.1), DOOR_Y=0.72, DOOR_HW=0.55, DOOR_SLIDE=1.05,
                SCREEN_Z=(1.25, 2.1), SCREEN_Y=(2.5, 2.2), SEAT_Y=1.5, REAR_Y=(-0.25, -1.55), DRIVER_X=-0.48),
}[VARIANT]
A, BF, BR, H, N = CFG["A"], CFG["BF"], CFG["BR"], CFG["H"], CFG["N"]
BASE, FLOOR, WR = CFG["BASE"], CFG["FLOOR"], CFG["WR"]
WIN0, WIN1 = CFG["WIN"]
DOOR_Y, DOOR_HW = CFG["DOOR_Y"], CFG["DOOR_HW"]

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


def wood_texture():
    # walnut veneer: long grain along u, darker streaks, a faint gloss variation
    w, h = 1024, 256
    rng = np.random.default_rng(3)
    u = np.linspace(0, 1, w)[None, :]
    v = np.linspace(0, 1, h)[:, None]
    grain = np.sin(v * 180 + 6 * np.sin(u * 7 + v * 3) + 2.5 * np.sin(u * 23)) * 0.5 + 0.5
    noise = rng.standard_normal((h, w)) * 0.04
    t = 0.55 + 0.3 * grain ** 3 + noise
    r, g, b = 0.36 * t, 0.2 * t, 0.1 * t
    return image("walnut", w, h, np.stack([r, g, b, np.ones_like(t)], -1))


def screen_texture():
    # the dash display: a dark panel, five app tiles with icons, a clock line (car 1 cockpit.jpg)
    w, h = 512, 192
    img = np.zeros((h, w, 4), np.float32)
    img[..., :3] = (0.02, 0.03, 0.06)
    img[..., 3] = 1.0
    yy, xx = np.mgrid[0:h, 0:w]
    yu = h - 1 - yy
    for k in range(5):
        cx = 60 + k * 98
        r = np.hypot(xx - cx, yu - 95)
        img[(np.abs(r - 26) < 2.5), :3] = (0.45, 0.7, 1.0)
        img[(r < 9), :3] = (0.6, 0.8, 1.0)
        img[(yu > 40) & (yu < 48) & (np.abs(xx - cx) < 28), :3] = (0.5, 0.6, 0.75)
        img[(np.abs(xx - (cx + 49)) < 1) & (yu > 30) & (yu < 150), :3] = (0.15, 0.2, 0.3)
    img[(yu > 160) & (yu < 170) & (np.abs(xx - 256) < 40), :3] = (0.7, 0.8, 0.95)
    return image("carscreen", w, h, img)


def white_img():
    return image("white", 4, 4, np.ones((4, 4, 4)))


if VARIANT == "pod":
    M = {
        "body": mat("body_white", (0.88, 0.89, 0.91), rough=0.28),
        "accent": mat("body_blue", (0.16, 0.3, 0.6), rough=0.3),
        "skirt": mat("skirt_black", (0.03, 0.035, 0.04), rough=0.5),
        "roof": mat("roof_white", (0.9, 0.91, 0.93), rough=0.3),
        "wood": mat("panel_silver", (0.7, 0.71, 0.72), rough=0.3, metal=0.3),
        "seat": mat("seat_white", (0.85, 0.85, 0.86), rough=0.6),
        "cushion": mat("seat_blue", (0.2, 0.35, 0.66), rough=0.6),
        "dash": mat("dash_white", (0.86, 0.87, 0.88), rough=0.45),
    }
else:
    M = {
        "body": mat("body_mustard", (0.72, 0.52, 0.12), rough=0.3),
        "accent": mat("body_white", (0.9, 0.89, 0.85), rough=0.3),
        "skirt": mat("skirt_mustard", (0.62, 0.45, 0.1), rough=0.35),
        "roof": mat("roof_white", (0.92, 0.91, 0.87), rough=0.3),
        "wood": mat("woodgrain", (1, 1, 1), rough=0.35, tex=wood_texture()),
        "seat": mat("seat_tan", (0.66, 0.53, 0.38), rough=0.6),
        "cushion": mat("seat_tan2", (0.6, 0.47, 0.33), rough=0.65),
        "dash": mat("dash_tan", (0.45, 0.36, 0.26), rough=0.5),
    }
M.update({
    "chrome": mat("chrome", (0.82, 0.83, 0.85), rough=0.2, metal=0.45),
    "glass": mat("glass", (0.06, 0.14, 0.32) if VARIANT == "pod" else (0.04, 0.05, 0.06), rough=0.05, alpha=0.55 if VARIANT == "pod" else 0.35),
    "dark": mat("dark_trim", (0.05, 0.055, 0.06), rough=0.45),
    "rubber": mat("tyre", (0.025, 0.025, 0.028), rough=0.85),
    "wall": mat("whitewall", (0.9, 0.9, 0.88), rough=0.6),
    "hub": mat("hubcap", (0.86, 0.87, 0.88) if VARIANT == "pod" else (0.78, 0.79, 0.8), rough=0.3, metal=0.3 if VARIANT == "van" else 0.0),
    "floor": mat("floor", (0.2, 0.21, 0.22), rough=0.8),
    "liner": mat("liner", (0.8, 0.8, 0.8) if VARIANT == "pod" else (0.85, 0.8, 0.7), rough=0.6),
    "screen": mat("screen", (0.02, 0.02, 0.02), rough=0.2, emit=screen_texture(), emit_strength=1.4),
    "led": mat("led_blue", (0.4, 0.7, 1.0), rough=0.3, emit=image("ledb", 4, 4, np.tile([0.4, 0.75, 1.0, 1.0], (4, 4, 1))), emit_strength=3.0),
    "lamp": mat("headlamp", (0.95, 0.95, 0.9), rough=0.2, emit=white_img(), emit_strength=2.5),
    "tail": mat("taillamp", (0.6, 0.05, 0.04), rough=0.3, emit=image("red", 4, 4, np.tile([0.8, 0.05, 0.03, 1.0], (4, 4, 1))), emit_strength=1.5),
    "amber": mat("amber", (0.9, 0.5, 0.1), rough=0.3),
})
M_LIST = list(M.keys())


# ------------------------------------------------------------------ mesh helper
class Mesh:
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

    def lathe_x(self, prof, m, n=28, xf=Matrix()):
        """prof: [(x, r)] along the axle (x), revolved about it -- for wheels."""
        rings = [[xf @ Vector((x, r * math.cos(TAU * k / n), r * math.sin(TAU * k / n))) for k in range(n)] for x, r in prof]
        for i in range(len(rings) - 1):
            for k in range(n):
                self.face([rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]], m)

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


# ------------------------------------------------------------------ the shell
def half_len(z, front):
    """How far the body reaches fore (front) or aft at height z: the nose's windscreen slope."""
    if front:
        z0, z1 = CFG["SCREEN_Z"]
        y0, y1 = CFG["SCREEN_Y"]
        if z <= z0:
            d = max(0.0, (BASE + 0.25 - z) / 0.25)              # the bumper's rounded underside
            return BF * (1.0 - 0.06 * d * d)
        if z <= z1:
            return y0 + (y1 - y0) * (z - z0) / (z1 - z0)
        d = min(1.0, (z - z1) / (H - z1))
        return y1 - 0.12 * (1.0 - math.sqrt(max(0.0, 1.0 - d * d)))
    d_lo = max(0.0, (BASE + 0.22 - z) / 0.22)
    d_hi = max(0.0, (z - (H - 0.12)) / 0.12)
    return BR * (1.0 - 0.05 * d_lo * d_lo) - 0.12 * (1.0 - math.sqrt(max(0.0, 1.0 - d_hi * d_hi)))


def half_w(z):
    d_lo = max(0.0, (BASE + 0.18 - z) / 0.18)
    k = 1.0 - 0.05 * d_lo * d_lo
    if z > WIN0:                                               # the greenhouse leans in
        k -= 0.05 * (z - WIN0) / (H - WIN0)
    if z > H - 0.12:                                           # the roof's rounded edge down to a flat top
        d = (z - (H - 0.12)) / 0.12
        k *= 1.0 - 0.12 * (1.0 - math.sqrt(max(0.0, 1.0 - d * d)))
    return A * k


def plan(t, z):
    c, s = math.cos(t), math.sin(t)
    B = half_len(z, s >= 0.0)
    return (half_w(z) * math.copysign(abs(c) ** (2.0 / N), c), B * math.copysign(abs(s) ** (2.0 / N), s))


def wrap(t):
    return (t + math.pi) % TAU - math.pi


def t_at_y(y, right):
    B = BF if y >= 0 else BR
    t = math.asin(min(1.0, (abs(y) / B) ** (N / 2.0)))
    t = math.copysign(t, y)
    return t if right else math.pi - t


def in_iv(t, ivs):
    t = wrap(t)
    for a, b in ivs:
        lo, hi = min(wrap(a), wrap(b)), max(wrap(a), wrap(b))
        if hi - lo > math.pi:
            if t >= hi or t <= lo:
                return True
        elif lo <= t <= hi:
            return True
    return False


door_iv, side_glass, pillars = [], [], []
for right in (True, False):
    door_iv.append([t_at_y(DOOR_Y - DOOR_HW, right), t_at_y(DOOR_Y + DOOR_HW, right)])
if VARIANT == "pod":
    for right in (True, False):
        side_glass.append([t_at_y(DOOR_Y + DOOR_HW + 0.1, right), t_at_y(BF - 0.35, right)])
        side_glass.append([t_at_y(DOOR_Y - DOOR_HW - 0.1, right), t_at_y(-BR + 0.3, right)])
else:
    # the van's long band: panes between chrome pillars every ~0.8 m, doors and all
    edges = [BF - 0.45, DOOR_Y + DOOR_HW + 0.08, DOOR_Y - DOOR_HW - 0.08, -0.25, -1.05, -1.8, -BR + 0.3]
    for right in (True, False):
        for a, b in zip(edges[:-1], edges[1:]):
            if a <= DOOR_Y + DOOR_HW + 0.05 and b >= DOOR_Y - DOOR_HW - 0.05:
                continue
            side_glass.append([t_at_y(a - 0.04, right), t_at_y(b + 0.04, right)])
            pillars += [t_at_y(a, right), t_at_y(b, right)]

ts = {round(wrap(TAU * k / 200.0), 6) for k in range(200)}
for a, b in door_iv + side_glass:
    ts.add(round(wrap(a), 6))
    ts.add(round(wrap(b), 6))
for yb in (BF - 0.35, -BR + 0.3, BF - 0.45):
    for right in (True, False):
        ts.add(round(wrap(t_at_y(yb, right)), 6))
ts = sorted(ts)
_merged = [ts[0]]
for t in ts[1:]:
    if t - _merged[-1] > 0.004:
        _merged.append(t)
ts = _merged
z_marks = [BASE, FLOOR, WIN0, WIN1, CFG["SCREEN_Z"][0], CFG["SCREEN_Z"][1], 0.55, 0.62, 0.78, 0.9, 1.12, 1.18]
zs = sorted({round(z, 4) for z in list(np.linspace(BASE, H - 0.12, 26)) + list(np.linspace(H - 0.12, H, 5)) + z_marks if BASE <= z <= H})
_zm = [zs[0]]
for z in zs[1:]:
    if z - _zm[-1] > 0.012:
        _zm.append(z)
zs = _zm


def wheel_cut(p):
    """Is shell point p inside a wheel arch (seen from the side), at the sides?"""
    for wy in CFG["WY"]:
        if abs(p.x) > A * 0.62 and (p.y - wy) ** 2 + (p.z - WR) ** 2 < (WR + 0.07) ** 2:
            return True
    return False


def side_zone(zc, tc, yc):
    """The material of the painted shell at height zc (and y, for the van's woodgrain)."""
    if VARIANT == "pod":
        if zc < 0.5:
            return "skirt"
        if zc < 0.72:
            return "accent"
        return "body" if zc < H - 0.14 else "roof"
    if zc < 0.42:
        return "skirt"
    if 0.62 < zc < 1.1 and abs(math.cos(tc)) > 0.55 and -BR + 0.35 < yc < BF - 1.05:
        return "wood"
    if zc < WIN0 - 0.04:
        return "body"
    return "accent" if zc < H - 0.12 else "roof"


body = Mesh("body")
glass = Mesh("body_glass")
ring = [[Vector((*plan(t, z), z)) for t in ts] for z in zs]
nt = len(ts)
for i in range(len(zs) - 1):
    zc = 0.5 * (zs[i] + zs[i + 1])
    for j in range(nt):
        t0, t1 = ts[j], ts[(j + 1) % nt]
        tc = wrap(t0 + wrap(t1 - t0) * 0.5)
        q = [ring[i][j], ring[i][(j + 1) % nt], ring[i + 1][(j + 1) % nt], ring[i + 1][j]]
        cen = sum(q, Vector()) / 4.0
        if wheel_cut(cen):
            continue
        if FLOOR - 0.05 <= zc <= WIN1 + 0.02 and in_iv(tc, door_iv):
            continue                                            # the doorway
        sz0, sz1 = CFG["SCREEN_Z"]
        front = math.sin(tc) > 0.0
        if front and sz0 <= zc <= sz1 and abs(math.cos(tc)) < (0.975 if VARIANT == "pod" else 0.9):
            glass.face(q, "glass")                              # the windscreen, wrapping round
            continue
        if WIN0 <= zc <= WIN1 and in_iv(tc, side_glass):
            glass.face(q, "glass")
            continue
        if VARIANT == "pod" and WIN0 <= zc <= WIN1 and not front and math.sin(tc) < -0.97:
            glass.face(q, "glass")                              # the rear window
            continue
        m = side_zone(zc, tc, cen.y)
        if m == "wood":
            body.face(q, m, uvs=[(v.y * 0.6, v.z * 2.0) for v in q])
        else:
            body.face(q, m)
body.face(list(reversed(ring[0])), "skirt")
body.face(ring[-1], "roof")                                    # the flat roof panel (a convex superellipse)
body.obj(smooth=False, solidify=0.035)
glass.obj()

# ------------------------------------------------------------------ trim: arches, bumpers, lamps, pillars, door frames
trim = Mesh("trim")
for wy in CFG["WY"]:
    for sx in (-1, 1):
        # the arch's liner: a half-ring under the cut
        n = 14
        for k in range(n):
            a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
            r = WR + 0.07
            p0 = Vector((sx * (A - 0.02), wy + r * math.cos(a0), WR + r * math.sin(a0)))
            p1 = Vector((sx * (A - 0.02), wy + r * math.cos(a1), WR + r * math.sin(a1)))
            trim.face([p0, p1, p1 + Vector((-sx * 0.28, 0, 0)), p0 + Vector((-sx * 0.28, 0, 0))], "dark")
            if VARIANT == "van":                                   # a chrome lip round the arch
                trim.tube(p0 + Vector((sx * 0.01, 0, 0)), p1 + Vector((sx * 0.01, 0, 0)), 0.015, "chrome", n=5)
FZ = 0.62 if VARIANT == "pod" else 0.42
if VARIANT == "pod":
    trim.box((-A * 0.9, BF - 0.08, 0.6), (A * 0.9, BF + 0.02, 0.86), "wood")                       # the silver nose panel
    trim.box((-A * 0.88, BF - 0.05, 0.88), (A * 0.88, BF + 0.01, 0.905), "led")                   # the light strip
    for sx in (-1, 1):
        trim.box((sx * A * 0.55, BF - 0.06, 0.8), (sx * A * 0.85, BF + 0.015, 0.86), "lamp")
        trim.box((sx * A * 0.6 - 0.15, -BR - 0.02, 0.95), (sx * A * 0.6 + 0.15, -BR + 0.03, 1.02), "tail")
        # a white running light along the side at the band's top
        trim.box((sx * (A + 0.005) - 0.01, -BR + 0.4, 0.73), (sx * (A + 0.005) + 0.01, BF - 0.5, 0.745), "led")
else:
    # chrome bumpers, the silver grille panel with its quad lamps, the blue line, amber markers
    for yb, s in ((BF + 0.02, 1), (-BR - 0.02, -1)):
        trim.box((-A * 0.88, yb - s * 0.1, 0.36), (A * 0.88, yb + s * 0.03, 0.5), "chrome")
    trim.box((-A * 0.62, BF - 0.05, 0.58), (A * 0.62, BF + 0.015, 0.98), "chrome")
    trim.box((-A * 0.8, BF - 0.05, 1.0), (A * 0.8, BF + 0.02, 1.02), "led")
    trim.box((-A * 0.8, BF - 0.05, 0.54), (A * 0.8, BF + 0.02, 0.555), "led")
    for sx in (-1, 1):
        for k in range(2):
            cx = sx * (A * 0.68 + k * 0.18)
            trim.lathe_x([(0.0, 0.0), (0.0, 0.085), (0.03, 0.085), (0.03, 0.0)], "lamp", n=18,
                         xf=Matrix.Translation((cx, BF + 0.01, 0.76)) @ Matrix.Rotation(math.pi / 2, 4, "Z"))
            trim.lathe_x([(0.0, 0.1), (0.035, 0.1), (0.035, 0.085)], "chrome", n=18,
                         xf=Matrix.Translation((cx, BF, 0.76)) @ Matrix.Rotation(math.pi / 2, 4, "Z"))
        trim.box((sx * A * 0.93 - 0.05, BF - 0.2, 0.6), (sx * A * 0.93 + 0.05, BF - 0.05, 0.68), "amber")
        trim.box((sx * A * 0.7 - 0.12, -BR - 0.03, 0.62), (sx * A * 0.7 + 0.12, -BR + 0.02, 0.9), "tail")
        # chrome beading round the wood panel, and a mirror on its arm
        for z in (0.61, 1.11):
            trim.box((sx * (A + 0.004) - 0.008, -BR + 0.33, z - 0.012), (sx * (A + 0.004) + 0.008, BF - 1.03, z + 0.012), "chrome")
        trim.tube((sx * A * 0.95, BF - 0.55, 1.3), (sx * (A + 0.22), BF - 0.45, 1.42), 0.015, "chrome", n=6)
        trim.box((sx * (A + 0.2) - 0.05, BF - 0.5, 1.36), (sx * (A + 0.2) + 0.05, BF - 0.44, 1.52), "chrome")
    for sx in (-1, 1):                                          # wipers
        trim.tube((sx * 0.1, BF - 0.08, 1.22), (sx * 0.72, BF - 0.2, 1.3), 0.012, "dark", n=5)
    # the band's chrome pillars
    for t in pillars:
        p0 = Vector((*plan(t, WIN0), WIN0))
        p1 = Vector((*plan(t, WIN1), WIN1))
        n_ = Vector((math.copysign(0.012, p0.x), 0, 0))
        trim.tube(p0 + n_, p1 + n_, 0.028, "chrome", n=6)
# door frames (jambs and head) both sides, and boarding steps
for right in (True, False):
    sx = 1 if right else -1
    xo = half_w(FLOOR + 0.5) + 0.005
    for e in (-1, 1):
        y = DOOR_Y + e * DOOR_HW
        trim.box((min(sx * (xo - 0.12), sx * xo), y - 0.03, FLOOR - 0.05), (max(sx * (xo - 0.12), sx * xo), y + 0.03, WIN1 + 0.03), "dark")
    trim.box((min(sx * (xo - 0.12), sx * xo), DOOR_Y - DOOR_HW, WIN1), (max(sx * (xo - 0.12), sx * xo), DOOR_Y + DOOR_HW, WIN1 + 0.06), "dark")
    trim.box((min(sx * (xo - 0.12), sx * (xo + 0.18)), DOOR_Y - DOOR_HW + 0.05, FLOOR * 0.5 - 0.02),
             (max(sx * (xo - 0.12), sx * (xo + 0.18)), DOOR_Y + DOOR_HW - 0.05, FLOOR * 0.5 + 0.02), "chrome")       # the step
trim.obj(smooth=False)

# ------------------------------------------------------------------ sliding doors
LEAF_X = A - 0.1
leaves = [(1, 1), (2, -1)] if VARIANT == "pod" else [(2, 1)]   # odd leaves toward the nose (+Y), even toward the tail   # (n, direction of the leaf from the door centre)
for right in (True, False):
    sx = 1 if right else -1
    for n_, dirn in leaves:
        leaf = Mesh("door_%s%d" % ("R" if right else "L", n_))
        w_ = DOOR_HW if VARIANT == "pod" else 2 * DOOR_HW
        lo_y, hi_y = (sorted([0.0, dirn * w_]) if VARIANT == "pod" else (-DOOR_HW, DOOR_HW))
        if VARIANT == "pod":                                     # black framed glass, like the reference
            leaf.box((-0.025, lo_y, FLOOR), (0.025, hi_y, WIN1 - 0.02), "dark")
            leaf.face([Vector((sx * 0.03, lo_y + 0.05, FLOOR + 0.1)), Vector((sx * 0.03, hi_y - 0.05, FLOOR + 0.1)),
                       Vector((sx * 0.03, hi_y - 0.05, WIN1 - 0.08)), Vector((sx * 0.03, lo_y + 0.05, WIN1 - 0.08))], "glass")
            hy = (hi_y - 0.08) if dirn > 0 else (lo_y + 0.08)
            leaf.tube(Vector((sx * 0.04, hy, FLOOR + 0.7)), Vector((sx * 0.04, hy, FLOOR + 1.1)), 0.012, "chrome", n=6)
        else:                                                    # painted to match, wood panel, a window
            leaf.box((-0.025, lo_y, FLOOR - 0.12), (0.025, hi_y, 0.61), "body")
            leaf.box((-0.03, lo_y, 0.61), (0.03, hi_y, 1.11), "wood")
            leaf.box((-0.025, lo_y, 1.11), (0.025, hi_y, WIN0), "body")
            leaf.box((-0.025, lo_y, WIN0), (0.025, lo_y + 0.05, WIN1), "accent")
            leaf.box((-0.025, hi_y - 0.05, WIN0), (0.025, hi_y, WIN1), "accent")
            leaf.box((-0.025, lo_y, WIN1 - 0.03), (0.025, hi_y, WIN1 + 0.02), "accent")
            leaf.face([Vector((sx * 0.03, lo_y + 0.05, WIN0)), Vector((sx * 0.03, hi_y - 0.05, WIN0)),
                       Vector((sx * 0.03, hi_y - 0.05, WIN1 - 0.03)), Vector((sx * 0.03, lo_y + 0.05, WIN1 - 0.03))], "glass")
            leaf.box((sx * 0.03 - 0.01, hi_y - 0.25, 1.2), (sx * 0.03 + 0.01, hi_y - 0.1, 1.23), "chrome")
        ob = leaf.obj(smooth=False)
        ob.location = (sx * LEAF_X, DOOR_Y, 0.0)

# ------------------------------------------------------------------ interior
inner = Mesh("interior")
fy0, fy1 = -BR + 0.15, BF - 0.35
inner.box((-A + 0.1, fy0, FLOOR - 0.08), (A - 0.1, fy1, FLOOR), "floor")
for yy in np.arange(fy0 + 0.2, fy1 - 0.1, 0.14):
    inner.box((-A + 0.25, yy - 0.01, FLOOR), (A - 0.25, yy + 0.01, FLOOR + 0.005), "dark")
# the headliner and a light
inner.box((-A + 0.12, fy0, H - 0.14), (A - 0.12, fy1, H - 0.1), "liner")
inner.box((-0.3, -0.6, H - 0.15), (0.3, 0.6, H - 0.14), "lamp")


def seat(m, x, y, w=0.52, back=0.78):
    """A seat facing +Y, hips at (x, y, FLOOR + 0.48)."""
    base = Matrix.Translation((x, y, FLOOR))
    m.box((-w * 0.4, -0.2, 0.0), (w * 0.4, 0.2, 0.3), "dark", xf=base)
    m.box((-w * 0.5, -0.24, 0.3), (w * 0.5, 0.26, 0.44), "seat", xf=base)
    m.box((-w * 0.45, -0.2, 0.44), (w * 0.45, 0.24, 0.5), "cushion", xf=base)
    bk = base @ Matrix.Translation((0, -0.24, 0.44)) @ Matrix.Rotation(math.radians(14), 4, "X")   # the back reclines (toward -Y)
    m.box((-w * 0.5, -0.1, 0.0), (w * 0.5, 0.04, back), "seat", xf=bk)
    m.box((-w * 0.42, 0.04, 0.12), (w * 0.42, 0.06, back - 0.12), "cushion", xf=bk)
    m.box((-0.13, -0.08, back + 0.04), (0.13, 0.04, back + 0.24), "seat", xf=bk)


DX = CFG["DRIVER_X"]
SY = CFG["SEAT_Y"]
seat(inner, DX, SY)
seat(inner, -DX, SY)
seats = [("seat_pilot", (DX, SY)), ("seat_passenger", (-DX, SY))]
for k, ry in enumerate(CFG["REAR_Y"]):
    for c_, cx in enumerate((-0.52, 0.0, 0.52) if VARIANT == "van" else (-0.4, 0.4)):
        seat(inner, cx, ry, w=0.5 if VARIANT == "van" else 0.56)
        seats.append(("seat_r%d_%d" % (k, c_), (cx, ry)))
# the dash across the nose (white with a blue light strip in the pod; tan in the van)
dz = CFG["SCREEN_Z"][0] + 0.02
dy = half_len(dz, True) - 0.2
inner.box((-A + 0.12, dy - 0.45, dz - 0.35), (A - 0.12, dy, dz), "dash")
inner.box((-A + 0.12, dy - 0.47, dz - 0.03), (A - 0.12, dy - 0.45, dz), "led" if VARIANT == "pod" else "chrome")
if VARIANT == "pod":
    inner.box((0.2, dy - 0.3, dz), (0.7, dy - 0.05, dz + 0.004), "dark")                 # the vent grille
    for k in range(8):
        inner.box((0.22, dy - 0.28 + k * 0.03, dz + 0.004), (0.68, dy - 0.27 + k * 0.03, dz + 0.008), "liner")
# the display hood in front of the driver, and the screen in it
scr = Matrix.Translation((DX, dy - 0.3, dz)) @ Matrix.Rotation(math.radians(-15), 4, "X")
inner.box((-0.28, -0.02, -0.02), (0.28, 0.06, 0.2), "dash", xf=scr)
inner.face([scr @ Vector((-0.25, -0.025, 0.02)), scr @ Vector((0.25, -0.025, 0.02)), scr @ Vector((0.25, -0.025, 0.18)),
            scr @ Vector((-0.25, -0.025, 0.18))], "screen", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
# the steering column
col_top = Vector((DX, dy - 0.62, dz - 0.05))
inner.tube(Vector((DX, dy - 0.4, dz - 0.25)), col_top, 0.035, "dark", n=8)
# the rear wall / tailgate trim and wheel-arch boxes inside
for wy in CFG["WY"]:
    for sx in (-1, 1):
        inner.box((sx * (A - 0.12) - 0.001 * sx, wy - WR - 0.1, FLOOR), (sx * (A - 0.4), wy + WR + 0.1, FLOOR + 0.2), "floor")
inner.obj(smooth=False)

# the steering wheel on its own node: a yoke for the pod, a round wheel for the van
sw = Mesh("steering_wheel")
if VARIANT == "pod":
    sw.box((-0.08, -0.03, -0.07), (0.08, 0.03, 0.06), "dash")
    sw.box((-0.02, -0.035, -0.01), (0.02, -0.03, 0.01), "led")
    pts = [(-0.18, -0.05), (-0.2, 0.07), (-0.1, 0.12), (0.1, 0.12), (0.2, 0.07), (0.18, -0.05), (0.08, -0.13), (-0.08, -0.13)]
    for k in range(len(pts)):
        a, b = pts[k], pts[(k + 1) % len(pts)]
        sw.tube(Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1])), 0.022, "cushion" if k in (0, 5, 6, 7) else "dash", n=8)
    for sxs in (-1, 1):
        sw.tube(Vector((sxs * 0.07, 0, 0.0)), Vector((sxs * 0.18, 0, -0.03)), 0.018, "dash", n=6)
else:
    n = 20
    for k in range(n):
        a0, a1 = TAU * k / n, TAU * (k + 1) / n
        sw.tube(Vector((0.19 * math.cos(a0), 0, 0.19 * math.sin(a0))), Vector((0.19 * math.cos(a1), 0, 0.19 * math.sin(a1))), 0.016, "dark", n=6)
    for a in (math.pi / 2 + 0.2, -math.pi / 2 - 0.2, -0.1 + math.pi, 0.1):
        sw.tube(Vector((0, 0, 0)), Vector((0.19 * math.cos(a), 0, 0.19 * math.sin(a))) * 0.95, 0.012, "chrome", n=5)
    sw.tube(Vector((0, -0.03, 0)), Vector((0, 0.03, 0)), 0.05, "chrome", n=12)
swo = sw.obj(smooth=False)
swo.location = col_top
swo.rotation_euler = (math.radians(-25), 0, 0)

for name, (x, y) in seats:
    e = bpy.data.objects.new(name, None)
    e.location = (x, y, FLOOR + 0.48)
    col.objects.link(e)
for sx, tag in ((1, "R"), (-1, "L")):
    e = bpy.data.objects.new("exit_" + tag, None)
    e.location = (sx * (A + 0.9), DOOR_Y, 0.0)
    col.objects.link(e)

# ------------------------------------------------------------------ wheels
WW = CFG["WW"]
for tag, wy in (("F", CFG["WY"][0]), ("B", CFG["WY"][1])):
    for sx, side in ((-1, "L"), (1, "R")):
        piv = bpy.data.objects.new("wheel_%s%s" % (tag, side), None)
        piv.location = (sx * CFG["TRACK"], wy, WR)
        col.objects.link(piv)
        w = Mesh("tyre_%s%s" % (tag, side))
        o = sx * WW * 0.5                                     # the outer face's x
        prof = [(-o, WR * 0.66), (-o * 1.02, WR * 0.9), (-o * 0.9, WR), (o * 0.9, WR), (o * 1.02, WR * 0.9), (o, WR * 0.66)]
        w.lathe_x(prof, "rubber", n=30)
        if VARIANT == "van":                                     # the whitewall band on the outer face
            w.lathe_x([(o * 1.03, WR * 0.7), (o * 1.03, WR * 0.84)], "wall", n=30)
        # the hub: a domed cap (the pod's plain white discs, the van's chrome dish with a boss)
        cap = [(o, WR * 0.66), (o * 1.05, WR * 0.6), (o * 1.12, WR * 0.4), (o * 1.15, 0.0)] if VARIANT == "pod" else \
              [(o, WR * 0.66), (o * 1.08, WR * 0.5), (o * 1.08, WR * 0.2), (o * 1.25, WR * 0.14), (o * 1.25, 0.0)]
        w.lathe_x(cap, "hub", n=30)
        w.lathe_x([(-o, WR * 0.66), (-o * 0.8, 0.0)], "dark", n=20)
        if VARIANT == "pod":                                     # a spoke mark so the spin shows
            w.box((o * 1.13 - 0.004, -0.025, WR * 0.15), (o * 1.13 + 0.004, 0.025, WR * 0.5), "accent")
        wo = w.obj()
        wo.parent = piv

# ------------------------------------------------------------------ export
root = bpy.data.objects.new(VARIANT, None)
col.objects.link(root)
for ob in list(col.objects):
    if ob is not root and ob.parent is None:
        ob.parent = root
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_apply=True, export_yup=True)
print("CAR_EXPORTED", VARIANT, OUT)

if RENDER:
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1000, 700
    try:
        sc.eevee.taa_render_samples = 32
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.9, 0.91, 0.93, 1)
    bg.inputs[1].default_value = 0.8
    sc.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(45), math.radians(10), math.radians(35))
    col.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    col.objects.link(cam)
    sc.camera = cam
    for d_ in bpy.data.objects:
        if d_.name.startswith("door_L"):
            d_.location.y += (CFG["DOOR_SLIDE"] if d_.name.endswith("2") else -CFG["DOOR_SLIDE"])
    centre = Vector((0, 0, 1.0))

    def shoot(tag, az, el, dist, lens=50, tgt=centre):
        cam.data.lens = lens
        d = Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)), math.cos(math.radians(az)) * math.cos(math.radians(el)),
                    math.sin(math.radians(el))))
        cam.location = tgt + d * dist
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = "%s_%s.png" % (RENDER, tag)
        bpy.ops.render.render(write_still=True)

    shoot("q_front", 320, 12, 9.5)
    shoot("q_rear", 140, 14, 9.5)
    shoot("side", 270, 4, 10)
    L = bpy.data.objects.new("cabin_light", bpy.data.lights.new("cabin_light", "POINT"))
    L.data.energy = 30
    L.location = (0, 0, H - 0.4)
    col.objects.link(L)
    cam.data.lens = 18
    cam.location = (DX, SY - 0.05, FLOOR + 1.2)
    cam.rotation_euler = (math.radians(82), 0, 0)
    sc.render.filepath = "%s_driver.png" % RENDER
    bpy.ops.render.render(write_still=True)
    print("CAR_RENDERED")
