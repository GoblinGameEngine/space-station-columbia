"""kit.cutout -- an open, wiry asset (cart, chair, stroller, small bike) from its reference views as
alpha-cut panels: the side view on two panels at the measured half-width (one panel down the middle
for narrow things), the front and rear views across the ends, the top view (when drawn) across the
top. The wheels found on the side view are cut out of the panels and replaced by real wheels: a tyre
ring plus the drawn disc (spokes, hubcap) as an alpha texture, so they can turn.

Rig: wheel_<F|B|M#><L|R|C> (pivot at the hub, spin about local X).
"""
import math

import bpy
from mathutils import Vector

from . import core
from .hull import Proj

TAU = math.tau


def build(an, out_glb, render_prefix=None):
    core.reset()
    aid = an["id"]
    L, W, H = an["size_m"]
    V = an["views"]
    atlas = core.load_image(an["atlas"]["file"], aid + "_atlas")
    mats = {"cut": core.mat(aid + "_cut", tex=atlas, alpha_tex=True, rough=0.5), "tyre": core.mat("tyre", core.lin((40, 40, 42)), rough=0.85)}
    sv = V["side"]
    sp = Proj(an, "side")
    x0, y0, x1, y1 = sv["bbox"]
    s = sv["scale"]
    ymin, ymax = (x0 - (x0 + x1) / 2) * s, (x1 - (x0 + x1) / 2) * s
    zmax = (y1 - y0) * s
    narrow = W < 0.75 or W < 0.3 * L
    fv = V.get("front") or V.get("rear")
    if fv:
        rows = [r[1] for r in fv["halfwidth_by_z"] if r[1] > 0]
        rows.sort()
        hw = rows[int(len(rows) * 0.7)] if rows else W / 2
    else:
        hw = W / 2
    m = core.Mesh(aid, mats)

    def side_panel(x):
        pts = [Vector((x, ymin, 0.0)), Vector((x, ymax, 0.0)), Vector((x, ymax, zmax)), Vector((x, ymin, zmax))]
        m.face(pts, "cut", [sp.uv(p) for p in pts])
        m.face(list(reversed(pts)), "cut", [sp.uv(p) for p in reversed(pts)])
    xs = [0.0] if narrow else [-hw * 0.92, hw * 0.92]
    for x in xs:
        side_panel(x)
    for v, yy in (("front", ymax * 0.97), ("rear", ymin * 0.97)):
        if v in V and v in an["atlas"]["rects"]:
            P = Proj(an, v)
            vb = V[v]["bbox"]
            vs = V[v]["scale"]
            hx = (vb[2] - vb[0]) * vs / 2
            hz = (vb[3] - vb[1]) * vs
            if narrow:
                yy = 0.0 if v == "front" else None
                if yy is None:
                    continue
            pts = [Vector((-hx, yy, 0.0)), Vector((hx, yy, 0.0)), Vector((hx, yy, hz)), Vector((-hx, yy, hz))]
            m.face(pts, "cut", [P.uv(p) for p in pts])
            m.face(list(reversed(pts)), "cut", [P.uv(p) for p in reversed(pts)])
    if "top" in V and "top" in an["atlas"]["rects"]:
        P = Proj(an, "top")
        z = zmax * 0.98
        tb = V["top"]["bbox"]
        ts = V["top"]["scale"]
        hx = (tb[3] - tb[1]) * ts / 2
        pts = [Vector((-hx, ymin, z)), Vector((-hx, ymax, z)), Vector((hx, ymax, z)), Vector((hx, ymin, z))]
        m.face(pts, "cut", [P.uv(p) for p in pts])
        m.face(list(reversed(pts)), "cut", [P.uv(p) for p in reversed(pts)])
    body = m.obj()
    # wheels
    wl = sorted(sv.get("wheels_m", []), key=lambda w: -w[0])
    # spinning wheels only when the detection is plausible; otherwise the drawn wheels stay on the panels
    if not (2 <= len(wl) <= 4 and wl[0][0] - wl[-1][0] > 0.35 * L):
        wl = []
    for i, (wy, wz, r) in enumerate(wl):
        tag = "F" if i == 0 else ("B" if i == len(wl) - 1 else "M%d" % i)
        tw = max(0.02, min(0.2, 0.3 * r))
        for x in (xs if not narrow else [0.0]):
            sfx = "C" if narrow else ("R" if x > 0 else "L")
            wm = core.Mesh("wheel_%s%s" % (tag, sfx), mats)
            hub = Vector((x, wy, wz))
            n = 24
            ring_o = [hub + Vector((tw / 2, r * math.cos(TAU * k / n), r * math.sin(TAU * k / n))) for k in range(n)]
            ring_i = [hub + Vector((-tw / 2, r * math.cos(TAU * k / n), r * math.sin(TAU * k / n))) for k in range(n)]
            ring_o2 = [hub + Vector((tw / 2, r * 0.82 * math.cos(TAU * k / n), r * 0.82 * math.sin(TAU * k / n))) for k in range(n)]
            ring_i2 = [hub + Vector((-tw / 2, r * 0.82 * math.cos(TAU * k / n), r * 0.82 * math.sin(TAU * k / n))) for k in range(n)]
            for k in range(n):
                k2 = (k + 1) % n
                wm.face([ring_o[k], ring_i[k], ring_i[k2], ring_o[k2]], "tyre")
                wm.face([ring_o2[k], ring_o[k], ring_o[k2], ring_o2[k2]], "tyre")
                wm.face([ring_i[k], ring_i2[k], ring_i2[k2], ring_i[k2]], "tyre")
            disc = [hub + Vector((0, r * 0.82 * math.cos(TAU * k / n), r * 0.82 * math.sin(TAU * k / n))) for k in range(n)]
            wm.face(disc, "cut", [sp.uv(Vector((0, p.y, p.z))) for p in disc])
            wm.face(list(reversed(disc)), "cut", [sp.uv(Vector((0, p.y, p.z))) for p in reversed(disc)])
            wm.obj(origin=hub, parent=body)
    core.export(out_glb)
    print("ASSET_EXPORTED", aid, out_glb, "cutout", len(wl), "wheels")
    if render_prefix:
        sc, cam = core.render_setup()
        w, h = sv["w"], sv["h"]
        core.render_ortho(render_prefix + "_side.png", cam, "side", (0, (w / 2 - (x0 + x1) / 2) * s, (y1 - h / 2) * s), max(w, h) * s, w, h)
        core.render_persp(render_prefix + "_34.png", cam, (0, 0, H * 0.45), (-L * 1.1 - 1.2, L * 1.1 + 1.2, H * 1.0 + 0.6))
        print("ASSET_RENDERED", aid)
