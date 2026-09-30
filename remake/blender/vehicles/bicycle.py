"""
bicycle.py -- the station's everyday bicycle (research/lives/06_vehicles.md `bicycle`, priority 1), built
from Grok's reference images (remake/blender/vehicles/bicycle_brief.md; the images in the gitignored
reference/grok/bicycle/): a step-through city bike in sea blue-teal with cream fenders, chainguard and
rack, cream-wall balloon tyres, chrome bars and rims, a tan leather sprung saddle and grips, a wicker
basket over the front wheel and a round headlamp. Pedal-powered only (canon: every vehicle is electric
or pedal).

  flatpak run org.blender.Blender -b --factory-startup --python <abs bicycle.py> -- OUT_GLB [RENDER_PREFIX] [REF_SIDE_IMAGE]

Dimensions are measured off the side elevation (bicycle_img1.jpg): 26-inch wheels (0.68 m over the
tyres) give 0.001988 m per pixel; wheelbase 1.10 m, bottom bracket 0.29 m up, saddle top 0.91 m,
grips 1.10 m, bar 0.64 m wide (front elevation).

Blender Z up, the front toward +Y (glTF -Z, Godot's forward); metres; z = 0 where the tyres touch.
The rig (names are the contract with the game):
  wheel_F, wheel_B     pivot at the hub; spin about local X
  steer                the fork, front wheel, bars, basket, lamp and front fender; pivot on the
                       head tube, turning about its local Z (the steering axis, 17 deg back from vertical)
  cranks               pivot at the bottom bracket, spin about local X; children pedal_L, pedal_R
                       (counter-rotate them to keep the pedals level)
  kickstand            pivot at its mount; folds up about local X (down = parked)
  seat_rider           where the rider's hips go (on the saddle), facing +Y
  grip_L, grip_R       hand targets;  foot targets are the pedals
"""
import math
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/tmp/bicycle.glb"
RENDER = argv[1] if len(argv) > 1 else None
REF = argv[2] if len(argv) > 2 else None
TAU = math.tau
S = 0.68 / 342.0                  # metres per reference pixel
CX, GY = 661.5, 641.0             # the reference's centre between the hubs, and its ground line


def P(x, y, side=0.0):
    """A point from the side elevation's pixels (x right = forward, y down) -> Blender (X side, Y fwd, Z up)."""
    return Vector((side, (x - CX) * S, (GY - y) * S))


for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
col = bpy.context.scene.collection


# ------------------------------------------------------------------ textures (drawn here, packed in the GLB)
def image(name, w, h, rgba):
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(rgba, dtype=np.float32).ravel())
    img.pack()
    return img


def lin(c):
    return tuple(((x / 255.0 + 0.055) / 1.055) ** 2.4 if x / 255.0 > 0.04045 else x / 255.0 / 12.92 for x in c)


def tyre_texture():
    # u: round the wheel (one tread block repeat per 1/96); v: round the tyre's section, 0 = tread centre
    w, h = 2048, 128
    u = np.linspace(0, 1, w, endpoint=False)[None, :]
    v = np.linspace(0, 1, h, endpoint=False)[:, None]
    d = np.minimum(v, 1 - v)                                   # 0 at the tread, 0.5 at the rim side
    rng = np.random.default_rng(5)
    dark = np.array(lin((58, 58, 60)))
    cream = np.array(lin((222, 208, 178)))
    blocks = ((np.floor(u * 96 + np.where(d < 0.1, 0, 0.5)) % 2) == 0) & (d < 0.2)
    base = np.where(blocks[..., None], dark * 0.75, dark)
    band = (d > 0.26) & (d < 0.42)                             # the cream wall
    img = np.where(band[..., None], cream, base)
    img = img * (1 + rng.standard_normal((h, w, 1)) * 0.03)
    return image("tyre_tread", w, h, np.concatenate([np.clip(img, 0, 1), np.ones((h, w, 1))], -1))


def spokes_texture():
    # a disc: 36 laced spokes from a flanged hub to the rim, transparent between
    n = 512
    yy, xx = np.mgrid[0:n, 0:n]
    x = (xx + 0.5) / n * 2 - 1
    y = (yy + 0.5) / n * 2 - 1
    r = np.hypot(x, y)
    a = np.zeros((n, n))
    rim_r, hub_r = 0.97, 0.12
    for k in range(36):
        th = TAU * k / 36
        hub = np.array([math.cos(th), math.sin(th)]) * hub_r
        lead = th + (0.7 if k % 2 else -0.7)                    # tangent lacing: cross-three look
        tip = np.array([math.cos(lead), math.sin(lead)]) * rim_r
        dv = tip - hub
        t = np.clip(((x - hub[0]) * dv[0] + (y - hub[1]) * dv[1]) / (dv @ dv), 0, 1)
        dist = np.hypot(x - hub[0] - t * dv[0], y - hub[1] - t * dv[1])
        a = np.maximum(a, np.clip(1.6 - dist * n / 2.2, 0, 1))
    a = np.maximum(a, (r < hub_r + 0.03).astype(float))
    a[r > 0.99] = 0
    rgb = np.ones((n, n, 3)) * np.array(lin((205, 208, 212)))[None, None, :]
    return image("spokes", n, n, np.concatenate([rgb, a[..., None]], -1))


def leather_texture():
    w, h = 512, 512
    rng = np.random.default_rng(7)
    g = rng.standard_normal((h // 4, w // 4))
    g = np.kron(g, np.ones((4, 4)))
    g = (g + np.roll(g, 1, 0) + np.roll(g, 1, 1) + np.roll(g, 2, 0)) / 4
    base = np.array(lin((178, 118, 70)))
    img = base[None, None, :] * (1 + 0.07 * g[..., None])
    yy, xx = np.mgrid[0:h, 0:w]
    for cx, cy in [(60, 256), (452, 256), (256, 60), (256, 452)]:            # rivets
        rr = np.hypot(xx - cx, yy - cy)
        img[rr < 9] = np.array(lin((190, 190, 195)))
        img[(rr >= 9) & (rr < 12)] *= 0.7
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    img[edge < 10] *= 0.8                                                    # darker stitched edge
    return image("saddle_leather", w, h, np.concatenate([np.clip(img, 0, 1), np.ones((h, w, 1))], -1))


def wicker_texture():
    # an over-under weave: horizontal weavers over vertical stakes, with a rolled rim row at the top
    w, h = 512, 512
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    row = np.floor(yy / 16)
    stake = np.floor(xx / 24)
    over = ((row + stake) % 2) == 0
    fy = (yy % 16) / 16
    fx = (xx % 24) / 24
    weaver = 0.55 + 0.45 * np.sin(fy * math.pi)                              # the round of each weaver
    stake_shade = 0.6 + 0.4 * np.sin(fx * math.pi)
    shade = np.where(over, weaver, 0.75 * stake_shade * weaver)
    base = np.array(lin((176, 146, 92)))
    img = base[None, None, :] * shade[..., None]
    rim = yy < 40
    img[rim] = base * (0.6 + 0.4 * np.abs(np.sin((xx[rim] + yy[rim]) / 9.0)))[..., None]
    rng = np.random.default_rng(9)
    img *= 1 + rng.standard_normal((h, w, 1)) * 0.04
    return image("wicker", w, h, np.concatenate([np.clip(img, 0, 1), np.ones((h, w, 1))], -1))


def pedal_texture():
    w, h = 128, 64
    img = np.tile(np.array(lin((30, 30, 32))), (h, w, 1))
    yy, xx = np.mgrid[0:h, 0:w]
    img[(np.abs(yy - 32) < 9) & (np.abs(xx - 64) < 30)] = np.array(lin((235, 140, 30)))   # the amber reflector
    img[(yy % 10) < 2] *= 0.6                                                              # the grip ridges
    return image("pedal", w, h, np.concatenate([img, np.ones((h, w, 1))], -1))


def mat(name, color, rough=0.5, metal=0.0, tex=None, alpha_tex=False, emit=None):
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
        if alpha_tex:
            nt.links.new(t.outputs["Alpha"], p.inputs["Alpha"])
            m.surface_render_method = "DITHERED"
            m.use_backface_culling = False
    if emit is not None:
        p.inputs["Emission Color"].default_value = (*emit, 1.0)
        p.inputs["Emission Strength"].default_value = 1.2
    return m


M = {
    "paint": mat("paint_seablue", lin((74, 128, 140)), rough=0.35),
    "cream": mat("enamel_cream", lin((226, 214, 186)), rough=0.4),
    "chrome": mat("chrome", lin((214, 216, 220)), rough=0.18, metal=0.9),
    "tyre": mat("tyre", (1, 1, 1), rough=0.85, tex=tyre_texture()),
    "spokes": mat("spokes", (1, 1, 1), rough=0.3, metal=0.6, tex=spokes_texture(), alpha_tex=True),
    "leather": mat("leather", (1, 1, 1), rough=0.55, tex=leather_texture()),
    "wicker": mat("wicker", (1, 1, 1), rough=0.8, tex=wicker_texture()),
    "black": mat("black", lin((24, 24, 26)), rough=0.6),
    "pedal": mat("pedal", (1, 1, 1), rough=0.6, tex=pedal_texture()),
    "lens": mat("lamp_lens", lin((245, 242, 228)), rough=0.1, emit=lin((255, 250, 225))),
    "red": mat("reflector_red", lin((190, 25, 20)), rough=0.3, emit=lin((120, 10, 8))),
}
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

    def pipe(self, pts, r, m, n=10, caps=True, radii=None):
        """A tube swept along a polyline (rings follow the averaged tangent; parallel transport keeps it
        from twisting)."""
        pts = [Vector(p) for p in pts]
        rings = []
        ref = None
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            if ref is None:
                ref = t.orthogonal().normalized()
            ref = (ref - t * ref.dot(t)).normalized()
            b = t.cross(ref)
            rr = radii[i] if radii else r
            rings.append([p + (ref * math.cos(TAU * k / n) + b * math.sin(TAU * k / n)) * rr for k in range(n)])
        for i in range(len(rings) - 1):
            for k in range(n):
                self.face([rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]], m,
                          [(k / n, i / (len(rings) - 1)), ((k + 1) / n, i / (len(rings) - 1)), ((k + 1) / n, (i + 1) / (len(rings) - 1)), (k / n, (i + 1) / (len(rings) - 1))])
        if caps:
            self.face(list(reversed(rings[0])), m)
            self.face(rings[-1], m)

    def box(self, c, half, m, xf=Matrix()):
        (x0, y0, z0) = (c[0] - half[0], c[1] - half[1], c[2] - half[2])
        (x1, y1, z1) = (c[0] + half[0], c[1] + half[1], c[2] + half[2])
        q = [xf @ Vector(p) for p in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
        for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            self.face([q[i] for i in f], m, [(0, 0), (1, 0), (1, 1), (0, 1)])

    def lathe(self, prof, m, n=16, xf=Matrix(), cap_end=False):
        """prof: [(along, r)] revolved about local +Y (then placed by xf)."""
        rings = [[xf @ Vector((r * math.cos(TAU * k / n), a, r * math.sin(TAU * k / n))) for k in range(n)] for a, r in prof]
        for i in range(len(rings) - 1):
            for k in range(n):
                self.face([rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % n], rings[i][(k + 1) % n]], m)
        if cap_end:
            self.face(list(rings[-1]), m)

    def obj(self, origin=Vector(), smooth=True, parent=None):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-6)
        bmesh.ops.translate(self.bm, verts=self.bm.verts, vec=-origin)
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        for key in M_LIST:
            me.materials.append(M[key])
        for p in me.polygons:
            p.use_smooth = smooth
        ob = bpy.data.objects.new(self.name, me)
        col.objects.link(ob)
        ob.location = origin
        if parent:
            attach(ob, parent)
        return ob


def attach(child, parent):
    """Parent keeping the child where it is in the world (Blender's matrices must be current first)."""
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def arc(c, r, a0, a1, n, side=0.0):
    """Points round a circle in the side plane (angle 0 = forward, 90 = up), at lateral offset side."""
    return [Vector((side, c.y + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c.z + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))) for i in range(n + 1)]


def bez(p0, p1, p2, n=10):
    return [p0 * (1 - t) ** 2 + p1 * 2 * t * (1 - t) + p2 * t * t for t in (i / n for i in range(n + 1))]


def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.05
    col.objects.link(e)
    e.location = loc
    if parent:
        attach(e, parent)
    return e


# ------------------------------------------------------------------ key points (reference pixels)
HUB_B, HUB_F = P(385, 470), P(938, 470)
BB = P(618, 497)
SEAT_TOP = P(537, 262)              # the seat tube's top (the clamp)
SADDLE = P(522, 188)
HEAD_LO, HEAD_HI = P(848, 292), P(821, 180)
STEM_TOP = P(809, 92)
R_TYRE, R_RIM, TYRE_T = 0.34, 0.305, 0.028
HALF_BAR = 0.32

frame = Mesh("frame")
# the step-through's two curved main tubes, the seat tube, stays and brace
frame.pipe(bez(P(833, 214), P(700, 250), P(596, 414)), 0.018, "paint", n=12)                 # the upper, swooping tube
frame.pipe(bez(P(852, 262), P(760, 360), P(630, 478)), 0.019, "paint", n=12)                 # the lower tube to the bracket
frame.pipe([BB, SEAT_TOP], 0.017, "paint", n=12)
frame.pipe([P(743, 255), P(739, 376)], 0.011, "paint")                                        # the brace between the main tubes
frame.pipe([HEAD_LO + (HEAD_LO - HEAD_HI) * 0.08, HEAD_HI], 0.022, "paint", n=14)             # the head tube
for side in (-0.045, 0.045):
    frame.pipe([BB + Vector((side * 0.7, 0, 0)), HUB_B + Vector((side, 0, 0))], 0.011, "paint")               # chainstays
    frame.pipe([P(545, 300, side * 0.5), HUB_B + Vector((side, 0, 0))], 0.009, "paint")                          # seat stays
frame.lathe([(-0.045, 0.03), (0.045, 0.03)], "paint", n=12, xf=Matrix.Translation(BB) @ Matrix.Rotation(math.pi / 2, 4, "Z"))  # the bottom bracket shell
# the rear rack (cream): the deck rails, the struts to the axle and the stays to the seat tube
for side in (-0.055, 0.055):
    frame.pipe([P(262, 268, side), P(462, 272, side)], 0.008, "cream")
    frame.pipe([P(325, 272, side), HUB_B + Vector((side * 1.1, 0, 0))], 0.007, "cream")
    frame.pipe([P(420, 272, side), HUB_B + Vector((side * 1.1, 0.02, 0))], 0.007, "cream")
frame.pipe([P(462, 272, 0.055), P(505, 300, 0.02)], 0.007, "cream")
frame.pipe([P(462, 272, -0.055), P(505, 300, -0.02)], 0.007, "cream")
for yy in (0.0, 0.33, 0.66, 1.0):
    a = P(262 + 200 * yy, 268 + 4 * yy)
    frame.pipe([a + Vector((-0.055, 0, 0)), a + Vector((0.055, 0, 0))], 0.006, "cream")
# the rear fender: a shallow channel round the wheel, and its tail light and reflector
def fender(mesh, c, a0, a1, r=R_TYRE + 0.022, w=0.058):
    prof = [(-w / 2, -0.012), (-w * 0.3, 0.0), (w * 0.3, 0.0), (w / 2, -0.012)]
    n = 30
    rows = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        radial = Vector((0, math.cos(a), math.sin(a)))
        rows.append([Vector((x, 0, 0)) + c + radial * (r + dz) for x, dz in prof])
    for i in range(n):
        for k in range(len(prof) - 1):
            mesh.face([rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k]], "cream")
            mesh.face([rows[i][k + 1], rows[i][k], rows[i + 1][k], rows[i + 1][k + 1]], "cream")   # both sides
fender(frame, HUB_B, 43, 172)
frame.box(P(226, 360), (0.018, 0.012, 0.016), "red")
frame.box(P(279, 288), (0.02, 0.008, 0.012), "red")
# the chainguard: a cream plate along the top run, and a ring round the chainring
guard = [P(400, 452, 0.05), P(572, 445, 0.05), P(572, 468, 0.05), P(400, 474, 0.05)]
frame.face(guard, "cream")
frame.face(list(reversed(guard)), "cream")
ring_pts = arc(BB, 0.112, 0, 360, 32, 0.05)
ring_in = arc(BB, 0.085, 0, 360, 32, 0.05)
for i in range(32):
    frame.face([ring_pts[i], ring_pts[i + 1], ring_in[i + 1], ring_in[i]], "cream")
    frame.face([ring_in[i], ring_in[i + 1], ring_pts[i + 1], ring_pts[i]], "cream")
# the chain (a dark loop under the guard) and the lock box on the seat stay
chain = arc(BB, 0.1, 90, 270, 12, 0.03) + arc(HUB_B, 0.04, 270, 450, 8, 0.03)
frame.pipe(chain + [chain[0]], 0.004, "black", n=5, caps=False)
LOCK = P(510, 330, 0.03)
frame.box(Vector((0, 0, 0)), (0.02, 0.05, 0.035), "black", xf=Matrix.Translation(LOCK) @ Matrix.Rotation(-0.6, 4, "X"))
# the saddle: seat post, sprung rails, springs and the leather top
frame.pipe([SEAT_TOP, SADDLE + Vector((0, 0.012, -0.05))], 0.0135, "chrome")
frame.pipe([SADDLE + Vector((0, 0.08, -0.03)), SADDLE + Vector((0, -0.1, -0.035))], 0.006, "chrome")
for side in (-0.045, 0.045):                                                                   # the rear coil springs
    c = SADDLE + Vector((side, -0.085, -0.045))
    frame.pipe([c + Vector((0.012 * math.cos(t), 0.012 * math.sin(t), -0.05 + 0.1 * (t / (8 * math.pi)))) for t in np.linspace(0, 8 * math.pi, 40)], 0.0025, "chrome", n=5)
saddle_prof = [(-0.13, 0.085), (-0.09, 0.09), (-0.03, 0.075), (0.03, 0.045), (0.09, 0.025), (0.13, 0.018)]
rows = []
for y, hw in saddle_prof:
    rows.append([SADDLE + Vector((hw * math.cos(t), y, 0.014 * math.sin(t) + 0.012 - 0.03 * (abs(math.cos(t)) ** 3))) for t in np.linspace(0, math.pi, 9)])
for i in range(len(rows) - 1):
    for k in range(len(rows[0]) - 1):
        uv = lambda ii, kk: (kk / (len(rows[0]) - 1), ii / (len(rows) - 1))
        frame.face([rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1]], "leather", [uv(i, k), uv(i + 1, k), uv(i + 1, k + 1), uv(i, k + 1)])
bottom = [SADDLE + Vector((hw * c_, y, -0.012)) for y, hw in saddle_prof for c_ in (1,)] + [SADDLE + Vector((-hw, y, -0.012)) for y, hw in reversed(saddle_prof)]
frame.face(bottom, "leather")
frame_ob = frame.obj()

# ------------------------------------------------------------------ the wheels
def wheel(name, hub):
    w = Mesh(name)
    maj, mi = R_TYRE - TYRE_T, TYRE_T
    nu, nv = 64, 10
    for i in range(nu):
        for j in range(nv):
            def pt(ii, jj):
                a, b = TAU * ii / nu, TAU * jj / nv
                rr = maj + mi * math.cos(b)
                return hub + Vector((mi * math.sin(b) * 1.1, rr * math.cos(a), rr * math.sin(a)))
            uvs = [(i / nu, j / nv), ((i + 1) / nu, j / nv), ((i + 1) / nu, (j + 1) / nv), (i / nu, (j + 1) / nv)]
            w.face([pt(i, j), pt(i + 1, j), pt(i + 1, j + 1), pt(i, j + 1)], "tyre", uvs)
    rim = [hub + Vector((0, R_RIM * math.cos(TAU * k / 48), R_RIM * math.sin(TAU * k / 48))) for k in range(49)]
    for side in (-0.012, 0.012):
        w.pipe([p + Vector((side, 0, 0)) for p in rim], 0.008, "chrome", n=6, caps=False)
    disc = [hub + Vector((0, R_RIM * math.cos(TAU * k / 32), R_RIM * math.sin(TAU * k / 32))) for k in range(32)]
    uvd = [(0.5 + 0.5 * math.cos(TAU * k / 32) * 0.99, 0.5 + 0.5 * math.sin(TAU * k / 32) * 0.99) for k in range(32)]
    w.face(disc, "spokes", uvd)
    w.lathe([(-0.05, 0.012), (-0.03, 0.022), (0.03, 0.022), (0.05, 0.012)], "chrome", n=12, xf=Matrix.Translation(hub) @ Matrix.Rotation(math.pi / 2, 4, "Z"))
    return w.obj(origin=hub)


wheel_B = wheel("wheel_B", HUB_B)
attach(wheel_B, frame_ob)

# ------------------------------------------------------------------ the steering assembly
axis = (HEAD_HI - HEAD_LO).normalized()
steer = Mesh("steer")
crown = HEAD_LO + axis * -0.03
for side in (-0.048, 0.048):                                                                   # the fork blades, raked forward
    steer.pipe(bez(crown + Vector((side * 0.6, 0, 0)), crown + Vector((side, 0.0, -0.12)), HUB_F + Vector((side, 0.0, 0.0)), 8), 0.011, "paint")
steer.pipe([crown + Vector((-0.05, 0, 0)), crown + Vector((0.05, 0, 0))], 0.013, "paint")
steer.pipe([HEAD_HI, STEM_TOP], 0.0125, "chrome")                                              # the stem
bar = bez(Vector((0, 0.0, 0)), Vector((0, 0.02, 0.005)), Vector((0, 0.0, 0)), 2)
# the swept-back bar: forward from the stem, out, and back to the grips
bar_pts = [STEM_TOP + Vector((0, 0.02, 0.0))]
for side in (-1, 1):
    pts = [STEM_TOP + Vector((0.0, 0.02, 0.0)), STEM_TOP + Vector((side * 0.1, 0.03, 0.01)), STEM_TOP + Vector((side * 0.2, -0.02, 0.0)),
           STEM_TOP + Vector((side * 0.26, -0.09, -0.01)), STEM_TOP + Vector((side * HALF_BAR, -0.14, -0.01))]
    steer.pipe(pts, 0.011, "chrome", caps=False)
    g0 = STEM_TOP + Vector((side * 0.225, -0.105, -0.01))
    g1 = STEM_TOP + Vector((side * HALF_BAR, -0.14, -0.01))
    steer.pipe([g0, g1], 0.016, "leather", n=10)                                               # the grip
    steer.pipe([g0 + Vector((0, 0.03, -0.015)), g0 + Vector((side * 0.08, 0.06, -0.035))], 0.005, "chrome")   # the brake lever
steer.lathe([(0.0, 0.026), (0.012, 0.026), (0.022, 0.012)], "chrome", n=14,
            xf=Matrix.Translation(STEM_TOP + Vector((-0.12, 0.02, 0.03))) @ Matrix.Rotation(-math.pi / 2, 4, "X"), cap_end=True)   # the bell
# the basket on its bracket and struts, the headlamp under it
bk_lo, bk_hi = P(920, 256), P(920, 128)
bk_c = P(920, 190)
bw_top, bw_bot, bd_top, bd_bot = 0.19, 0.16, 0.16, 0.13
corners = lambda z, hw, hd: [Vector((-hw, bk_c.y - hd, z)), Vector((hw, bk_c.y - hd, z)), Vector((hw, bk_c.y + hd, z)), Vector((-hw, bk_c.y + hd, z))]
lo_c, hi_c = corners(bk_lo.z, bw_bot, bd_bot), corners(bk_hi.z, bw_top, bd_top)
for k in range(4):
    a, b, c_, d = lo_c[k], lo_c[(k + 1) % 4], hi_c[(k + 1) % 4], hi_c[k]
    steer.face([a, b, c_, d], "wicker", [(0, 0), (1, 0), (1, 1), (0, 1)])
    steer.face([d, c_, b, a], "wicker", [(0, 1), (1, 1), (1, 0), (0, 0)])
steer.face(list(reversed(lo_c)), "wicker", [(0, 0), (1, 0), (1, 1), (0, 1)])
steer.pipe(hi_c + [hi_c[0]], 0.011, "wicker", n=6, caps=False)                                  # the rolled rim
for side in (-0.06, 0.06):
    steer.pipe([Vector((side, bk_c.y - 0.02, bk_lo.z)), HUB_F + Vector((side * 0.9, 0.0, 0))], 0.005, "chrome")
steer.pipe([Vector((0, bk_c.y - 0.12, bk_lo.z + 0.01)), crown + Vector((0, 0.02, 0.02))], 0.007, "chrome")
lamp = P(985, 267)
steer.lathe([(-0.045, 0.0), (-0.045, 0.02), (-0.03, 0.036), (0.02, 0.04), (0.035, 0.04)], "chrome", n=18,
            xf=Matrix.Translation(lamp))
steer.lathe([(0.035, 0.036), (0.038, 0.0)], "lens", n=18, xf=Matrix.Translation(lamp))
steer.pipe([lamp + Vector((0, -0.03, -0.035)), Vector((0, bk_c.y - 0.02, bk_lo.z - 0.02))], 0.005, "chrome")
fender(steer, HUB_F, 22, 197)
steer_ob = steer.obj(origin=HEAD_LO)
attach(steer_ob, frame_ob)
# the steering axis: the object's local Z along the head tube (rotate the mesh into that frame)
q = axis.to_track_quat("Z", "Y")
steer_ob.rotation_mode = "QUATERNION"
me = steer_ob.data
me.transform(q.to_matrix().to_4x4().inverted())
steer_ob.rotation_quaternion = q
wheel_F = wheel("wheel_F", HUB_F)
attach(wheel_F, steer_ob)

# ------------------------------------------------------------------ cranks, pedals, kickstand
cr = Mesh("cranks")
cr.lathe([(0.0, 0.0), (0.0, 0.1), (0.004, 0.1), (0.004, 0.0)], "chrome", n=28, xf=Matrix.Translation(BB + Vector((0.03, 0, 0))) @ Matrix.Rotation(math.pi / 2, 4, "Z"))  # chainring
for side, ang in ((0.07, -90), (-0.07, 90)):
    tip = BB + Vector((side, 0.17 * math.cos(math.radians(ang)), 0.17 * math.sin(math.radians(ang))))
    cr.pipe([BB + Vector((side * 0.8, 0, 0)), tip], 0.011, "chrome")
cranks = cr.obj(origin=BB)
attach(cranks, frame_ob)
for side, ang, nm in ((0.07, -90, "pedal_R"), (-0.07, 90, "pedal_L")):
    tip = BB + Vector((side, 0.17 * math.cos(math.radians(ang)), 0.17 * math.sin(math.radians(ang))))
    pm = Mesh(nm)
    pm.box(tip + Vector((math.copysign(0.055, side), 0, 0)), (0.045, 0.03, 0.011), "pedal")
    ped = pm.obj(origin=tip)
    attach(ped, cranks)
ks = Mesh("kickstand")
ks_top = P(600, 505, -0.05)
ks.pipe([ks_top, P(612, 636, -0.09)], 0.008, "chrome")
ks.box(P(612, 636, -0.09), (0.012, 0.025, 0.004), "chrome")
kick = ks.obj(origin=ks_top)
attach(kick, frame_ob)

# ------------------------------------------------------------------ rider targets
empty("seat_rider", SADDLE + Vector((0, -0.03, 0.02)), frame_ob)
empty("grip_L", STEM_TOP + Vector((-0.28, -0.125, -0.01)), steer_ob)
empty("grip_R", STEM_TOP + Vector((0.28, -0.125, -0.01)), steer_ob)

bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_apply=True, export_yup=True)
print("BIKE_EXPORTED", OUT)

if RENDER:
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.64, 0.64, 0.66, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    sc.world = world
    for rot, en in (((0.9, 0.2, 0.6), 3.0), ((1.2, -0.3, -2.4), 1.5)):
        L = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        L.data.energy = en
        L.rotation_euler = rot
        col.objects.link(L)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    col.objects.link(cam)
    sc.camera = cam
    # 0: the reference's side elevation (orthographic, same framing: 1280 px = 1280 * S m)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1280 * S
    cam.location = Vector((3.0, 0.0, (GY - 360) * S))
    cam.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    sc.render.film_transparent = False
    sc.render.filepath = RENDER + "_side.png"
    bpy.ops.render.render(write_still=True)
    # 1: three-quarter front-left, perspective; 2: head-on
    cam.data.type = "PERSP"
    cam.data.lens = 50
    for nm, loc in (("34", Vector((-2.2, 2.4, 1.3))), ("front", Vector((0.0, 3.6, 0.8)))):
        cam.location = loc
        cam.rotation_euler = (Vector((0, 0, 0.55)) - loc).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = RENDER + "_" + nm + ".png"
        bpy.ops.render.render(write_still=True)
    print("BIKE_RENDERED")
