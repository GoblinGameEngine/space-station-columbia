"""
aerostat_lod.py -- the aerostat seen from afar (godot_project/remake/vehicles/aerostat_lod.glb): one
mesh of a few hundred faces in the full model's proportions (remake/blender/vehicles/aerostat.py's
constants, copied): the balloon, the cabin's colour bands (slate belly, white band, dark windows,
white roof), the four fan ducts and the A-frame posts. RemakeAerostat shows it past its LOD distance.

  flatpak run org.blender.Blender -b --factory-startup --python <abs aerostat_lod.py> -- OUT_GLB
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import core  # noqa: E402
from kit.core import Mesh, lin, mat  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0]
A, B, N = 1.2, 2.3, 4.0
H = 2.45
BELLY_TOP, BAND_TOP, WIN_TOP, ROOF0 = 0.78, 1.02, 2.05, 2.12
BALLOON_R = 2.4
BALLOON_C = (0.0, 0.0, H + 0.62 + BALLOON_R)
FAN_R, FAN_Z, FAN_H = 0.62, 0.16, 0.46
FAN_C = [(1.8, 1.75), (-1.8, 1.75), (1.8, -1.75), (-1.8, -1.75)]

core.reset()
M = {"fabric": mat("fabric", lin((236, 232, 220)), rough=0.7), "slate": mat("slate", lin((70, 90, 110)), rough=0.5),
     "white": mat("white", lin((240, 240, 236)), rough=0.4), "glass": mat("glass", lin((40, 52, 60)), rough=0.15, metal=0.3),
     "duct": mat("duct", lin((50, 55, 60)), rough=0.5), "frame": mat("frame", lin((180, 180, 185)), rough=0.4, metal=0.6)}
me = Mesh("aerostat_lod", M)
# the balloon: 12 x 8
rings = []
for i in range(9):
    v = math.pi * i / 8
    ring = []
    for j in range(12):
        u = 2 * math.pi * j / 12
        ring.append((BALLOON_C[0] + BALLOON_R * math.sin(v) * math.cos(u), BALLOON_C[1] + BALLOON_R * math.sin(v) * math.sin(u), BALLOON_C[2] + BALLOON_R * math.cos(v)))
    rings.append(ring)
me.quad_strip(rings, "fabric", closed=True)
# the cabin: a superellipse prism in bands, 16 round
def plan(k, n=16):
    t = 2 * math.pi * k / n
    c, s = math.cos(t), math.sin(t)
    return (A * math.copysign(abs(c) ** (2 / N), c), B * math.copysign(abs(s) ** (2 / N), s))
for z0, z1, m in ((0.0, BELLY_TOP, "slate"), (BELLY_TOP, BAND_TOP, "white"), (BAND_TOP, WIN_TOP, "glass"), (WIN_TOP, ROOF0, "white")):
    rows = [[(x, y, z0) for x, y in (plan(k) for k in range(16))], [(x, y, z1) for x, y in (plan(k) for k in range(16))]]
    me.quad_strip(rows, m, closed=True)
roof = [[(x, y, ROOF0) for x, y in (plan(k) for k in range(16))], [(x * 0.8, y * 0.85, H) for x, y in (plan(k) for k in range(16))]]
me.quad_strip(roof, "white", closed=True)
me.face([(x * 0.8, y * 0.85, H) for x, y in (plan(k) for k in range(16))], "white")
me.face(list(reversed([(x, y, 0.0) for x, y in (plan(k) for k in range(16))])), "slate")
# the fan ducts, 8-sided
for fx, fy in FAN_C:
    me.lathe([(-FAN_H / 2, FAN_R * 0.85), (FAN_H / 2, FAN_R * 0.85)], "duct", n=8,
             xf=Matrix.Translation((fx, fy, FAN_Z + FAN_H / 2)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    me.lathe([(-FAN_H / 2, FAN_R), (FAN_H / 2, FAN_R)], "duct", n=8,
             xf=Matrix.Translation((fx, fy, FAN_Z + FAN_H / 2)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
# the A-frame posts up to the balloon
for sx in (-1, 1):
    for sy in (-1, 1):
        me.pipe([(sx * A * 0.6, sy * B * 0.5, H - 0.1), (sx * 0.9, sy * 1.0, BALLOON_C[2] - BALLOON_R * 0.92)], 0.04, "frame", n=4)
root = core.empty("aerostat_lod", (0, 0, 0))
ob = me.obj(origin=Vector((0, 0, 0)), smooth=False, parent=root)
ob.name = "lod"
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_apply=True, export_yup=True)
print("AEROSTAT LOD", len(ob.data.polygons), "faces")
