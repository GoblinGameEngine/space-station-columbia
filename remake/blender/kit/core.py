"""kit.core -- shared Blender helpers for the station's assets (bpy; run inside Blender).

Conventions (the game's contract, as in groundcar.py and bicycle.py): Blender Z up, the front toward
+Y (glTF -Z, Godot's forward), X to the right; metres; z = 0 where the wheels (or the keel) touch.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

TAU = math.tau


def reset():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for x in list(coll):
            coll.remove(x)


def col():
    return bpy.context.scene.collection


def lin(c):
    """sRGB 0-255 -> linear 0-1."""
    return tuple(((x / 255.0 + 0.055) / 1.055) ** 2.4 if x / 255.0 > 0.04045 else x / 255.0 / 12.92 for x in c)


def image(name, w, h, rgba):
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(rgba, dtype=np.float32).ravel())
    img.pack()
    return img


def load_image(path, name):
    img = bpy.data.images.load(path)
    img.name = name
    img.pack()
    return img


def mat(name, color=(1, 1, 1), rough=0.5, metal=0.0, tex=None, alpha_tex=False, emit=None, emit_strength=1.2):
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
        p.inputs["Emission Strength"].default_value = emit_strength
    return m


class Mesh:
    """bmesh builder with per-face materials (indices into the shared list `mats`) and UVs."""

    def __init__(self, name, mats):
        self.name = name
        self.mats = mats                      # dict name -> material (order fixes the indices)
        self.keys = list(mats)
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def face(self, pts, m, uvs=None):
        vs = [self.bm.verts.new(p) for p in pts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self.keys.index(m)
        if uvs:
            for lp, uv in zip(f.loops, uvs):
                lp[self.uv].uv = uv
        return f

    def quad_strip(self, rows, m, closed=False, uv=None):
        """rows: list of point lists (same length); faces between consecutive rows."""
        n = len(rows[0])
        for i in range(len(rows) - 1):
            for k in range(n if closed else n - 1):
                k2 = (k + 1) % n
                uvs = None
                if uv:
                    uvs = [uv(i, k), uv(i + 1, k), uv(i + 1, k2 if k2 else n), uv(i, k2 if k2 else n)]
                self.face([rows[i][k], rows[i + 1][k], rows[i + 1][k2], rows[i][k2]], m, uvs)

    def pipe(self, pts, r, m, n=10, caps=True, radii=None):
        pts = [Vector(p) for p in pts]
        rings, ref = [], None
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
                self.face([rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]], m)
        if caps:
            self.face(list(reversed(rings[0])), m)
            self.face(rings[-1], m)

    def box(self, c, half, m, xf=Matrix()):
        x0, y0, z0 = c[0] - half[0], c[1] - half[1], c[2] - half[2]
        x1, y1, z1 = c[0] + half[0], c[1] + half[1], c[2] + half[2]
        q = [xf @ Vector(p) for p in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
        for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            self.face([q[i] for i in f], m, [(0, 0), (1, 0), (1, 1), (0, 1)])

    def lathe(self, prof, m, n=16, xf=Matrix(), cap_end=False, cap_start=False):
        """prof: [(along, r)] revolved about local +Y, then placed by xf."""
        rings = [[xf @ Vector((r * math.cos(TAU * k / n), a, r * math.sin(TAU * k / n))) for k in range(n)] for a, r in prof]
        for i in range(len(rings) - 1):
            for k in range(n):
                self.face([rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % n], rings[i][(k + 1) % n]], m)
        if cap_end:
            self.face(list(rings[-1]), m)
        if cap_start:
            self.face(list(reversed(rings[0])), m)

    def obj(self, origin=Vector(), smooth=False, parent=None):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-6)
        bmesh.ops.translate(self.bm, verts=self.bm.verts, vec=-origin)
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        for key in self.keys:
            me.materials.append(self.mats[key])
        for p in me.polygons:
            p.use_smooth = smooth
        ob = bpy.data.objects.new(self.name, me)
        col().objects.link(ob)
        ob.location = origin
        if parent:
            attach(ob, parent)
        return ob


def attach(child, parent):
    """Parent keeping the child where it is in the world."""
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.1
    col().objects.link(e)
    e.location = loc
    if parent:
        attach(e, parent)
    return e


def export(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_yup=True, export_image_format="AUTO")


def render_setup():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
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
        col().objects.link(L)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    col().objects.link(cam)
    sc.camera = cam
    return sc, cam


def render_ortho(path, cam, axis, centre, scale, w, h):
    """axis: 'side' (looking along -X, front to the right), 'front' (looking along -Y), 'rear', 'top'."""
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = w, h
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    c = Vector(centre)
    if axis == "side":
        cam.location = c + Vector((60, 0, 0))
        cam.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    elif axis == "front":
        cam.location = c + Vector((0, 60, 0))
        cam.rotation_euler = (math.pi / 2, 0, math.pi)
    elif axis == "rear":
        cam.location = c + Vector((0, -60, 0))
        cam.rotation_euler = (math.pi / 2, 0, 0)
    else:
        cam.location = c + Vector((0, 0, 60))
        cam.rotation_euler = (0, 0, math.pi / 2)
    cam.data.clip_end = 200
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_persp(path, cam, target, loc, w=1000, h=700, lens=40):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = w, h
    cam.data.type = "PERSP"
    cam.data.lens = lens
    cam.data.clip_end = 2000
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_interior(path, cam, target, loc, w=1000, h=700, lens=16, energy=60.0):
    """A wide shot inside a cabin, lit by a lamp at the camera (the roof keeps the sun out)."""
    lamp = bpy.data.objects.new("ilamp", bpy.data.lights.new("ilamp", "POINT"))
    lamp.data.energy = energy
    lamp.data.shadow_soft_size = 0.5
    lamp.location = Vector(loc)
    col().objects.link(lamp)
    render_persp(path, cam, target, loc, w, h, lens)
    bpy.data.objects.remove(lamp, do_unlink=True)
