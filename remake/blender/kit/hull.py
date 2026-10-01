"""kit.hull -- a solid-bodied asset from its reference views: a visual hull (the intersection of the
side, front, rear and top silhouettes, each extruded across the body), the reference images
projected onto it through one texture atlas, and rigged wheels whose outer faces carry the drawn
hubcaps. Input: reference/grok/<id>/analysis.json (tools/assets/analyze.py).

Rig: wheel_<F|B|M1..><L|R> (pivot at the hub, spin about local X); body named <id>.
"""
import math

import bmesh
import bpy
from mathutils import Vector

from . import core

TAU = math.tau


def _signed_area(poly):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))


def prism(name, poly, axis, extent):
    """A polygon (2D) extruded through +-extent along axis: 'x' (poly = (Y, Z)), 'y' (poly = (X, Z)),
    'z' (poly = (X, Y))."""
    if _signed_area(poly) < 0:
        poly = list(reversed(poly))

    def p3(a, b, t):
        if axis == "x":
            return (t, a, b)
        if axis == "y":
            return (a, t, b)
        return (a, b, t)
    bm = bmesh.new()
    lo = [bm.verts.new(p3(a, b, -extent)) for a, b in poly]
    hi = [bm.verts.new(p3(a, b, extent)) for a, b in poly]
    n = len(poly)
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([lo[i], lo[j], hi[j], hi[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    core.col().objects.link(ob)
    return ob


def intersect(a, b):
    mod = a.modifiers.new("hull", "BOOLEAN")
    mod.operation = "INTERSECT"
    mod.solver = "EXACT"
    mod.object = b
    bpy.context.view_layer.objects.active = a
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(b)
    return a


class Proj:
    """Maps model points to atlas UVs through one reference view."""

    def __init__(self, an, view):
        v = an["views"][view]
        self.view = view
        self.s = v["scale"]
        self.sy = v.get("scale_y", self.s)
        self.sz = v.get("scale_z", self.s)
        x0, y0, x1, y1 = v["bbox"]
        self.cx, self.cy, self.y1 = (x0 + x1) / 2, (y0 + y1) / 2, y1
        r = an["atlas"]["rects"][view]
        self.c0x, self.c0y = r["crop"][0], r["crop"][1]
        self.k, self.X, self.Y, self.A = r["k"], r["X"], r["Y"], r["atlas"]

    def px(self, p):
        s, sz = self.sy, self.sz
        if self.view == "side":
            return self.cx + p.y / s, self.y1 - p.z / sz
        if self.view == "front":
            return self.cx - p.x / s, self.y1 - p.z / sz
        if self.view == "rear":
            return self.cx + p.x / s, self.y1 - p.z / sz
        return self.cx + p.y / s, self.cy + p.x / s

    def uv(self, p):
        x, y = self.px(p)
        return ((x - self.c0x) * self.k + self.X) / self.A, 1.0 - ((y - self.c0y) * self.k + self.Y) / self.A


def _dims(me):
    if not me.vertices:
        return (0.0, 0.0, 0.0)
    cs = [v.co for v in me.vertices]
    return tuple(max(c[i] for c in cs) - min(c[i] for c in cs) for i in range(3))


def wheel_halfwidth(an, z, W):
    fv = an["views"].get("front") or an["views"].get("rear")
    if not fv:
        return W / 2
    rows = fv["halfwidth_by_z"]
    best = min(rows, key=lambda r: abs(r[0] - z))
    return best[1]


def make(an, body_rough=0.45, cut_windows=None):
    """The textured hull and its rigged wheels; returns a context dict (body, mats, proj, wheels).
    cut_windows(body) -- an optional hook run on the raw hull before texturing (transit)."""
    core.reset()
    aid = an["id"]
    L, W, H = an["size_m"]
    V = an["views"]
    atlas = core.load_image(an["atlas"]["file"], aid + "_atlas")
    mats = {"atlas": core.mat(aid + "_body", tex=atlas, rough=body_rough), "tyre": core.mat("tyre", core.lin((38, 38, 40)), rough=0.85),
            "under": core.mat("underside", core.lin((34, 34, 36)), rough=0.9)}
    ext = max(L, W, H) * 0.75 + 1.0
    body = prism(aid, [tuple(p) for p in V["side"]["outline_m"]], "x", min(ext, W * 0.5 + 0.3))
    for v, axis in (("front", "y"), ("rear", "y"), ("top", "z")):
        if v in V and len(V[v].get("outline_m", [])) >= 3:
            other = prism(aid + "_" + v, [tuple(p) for p in V[v]["outline_m"]], axis, ext)
            keep = body.data.copy()
            before = _dims(keep)
            try:
                body = intersect(body, other)
            except Exception as e:
                print("HULL_WARN", v, e)
            after = _dims(body.data)
            # that view's outline didn't fit (the boolean collapsed the body): keep the hull without it
            if len(body.data.polygons) < 6 or any(a < b * 0.6 for a, b in zip(after, before)):
                print("HULL_WARN", v, "collapsed the hull", before, after, "; skipped")
                old = body.data
                body.data = keep
                bpy.data.meshes.remove(old)
            else:
                bpy.data.meshes.remove(keep)
    if cut_windows:
        body = cut_windows(body)
    me = body.data
    if len(me.polygons) == 0:
        raise RuntimeError("empty hull")
    me.materials.clear()
    me.materials.append(mats["atlas"])
    me.materials.append(mats["under"])
    proj = {v: Proj(an, v) for v in ("side", "front", "rear", "top") if v in V and v in an["atlas"]["rects"]}
    # the top of the side silhouette at each Y: upward faces without a top view sample the body colour
    # a little below it (not the edge, where the drawing's highlight sits)
    outl = V["side"]["outline_m"]
    ys = [p[0] for p in outl]
    ymin, ymax = min(ys), max(ys)
    tops = []
    for i in range(201):
        y = ymin + (ymax - ymin) * i / 200
        zs = []
        for a, b in zip(outl, outl[1:] + outl[:1]):
            if (a[0] - y) * (b[0] - y) <= 0 and a[0] != b[0]:
                t = (y - a[0]) / (b[0] - a[0])
                zs.append(a[1] + t * (b[1] - a[1]))
        tops.append(max(zs) if zs else 0.0)
    dz = 0.045 * H

    def top_z(y):
        i = int(round((y - ymin) / max(1e-6, ymax - ymin) * 200))
        return tops[min(max(i, 0), 200)]
    bm = bmesh.new()
    bm.from_mesh(me)
    uvl = bm.loops.layers.uv.new("UVMap")
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        if abs(n.x) >= 0.6:
            pv = "side"
        elif n.y >= 0.35 and "front" in proj:
            pv = "front"
        elif n.y <= -0.35 and "rear" in proj:
            pv = "rear"
        elif n.z > 0:
            if "top" not in proj:
                f.material_index = 0
                for lp in f.loops:
                    c = lp.vert.co
                    lp[uvl].uv = proj["side"].uv(Vector((0, c.y, min(c.z, top_z(c.y) - dz))))
                continue
            pv = "top"
        elif n.z < -0.5:
            f.material_index = 1
            continue
        else:
            pv = "side"
        f.material_index = 0
        P = proj[pv]
        for lp in f.loops:
            lp[uvl].uv = P.uv(lp.vert.co)
    bm.to_mesh(me)
    bm.free()
    # wheels
    wl = sorted(V["side"].get("wheels_m", []), key=lambda w: -w[0])
    sp = proj["side"]
    for i, (wy, wz, r) in enumerate(wl):
        tag = "F" if i == 0 else ("B" if i == len(wl) - 1 else "M%d" % i)
        tw = max(0.06, min(0.5, 0.42 * r))
        hx = max(tw, wheel_halfwidth(an, wz, W) - tw / 2 - 0.01)
        for side in (1, -1):
            m = core.Mesh("wheel_%s%s" % (tag, "R" if side > 0 else "L"), mats)
            hub = Vector((side * hx, wy, wz))
            n = 28
            outer = [hub + Vector((side * tw / 2, r * math.cos(TAU * k / n), r * math.sin(TAU * k / n))) for k in range(n)]
            inner = [hub + Vector((-side * tw / 2, r * math.cos(TAU * k / n), r * math.sin(TAU * k / n))) for k in range(n)]
            for k in range(n):
                k2 = (k + 1) % n
                m.face([outer[k], inner[k], inner[k2], outer[k2]] if side > 0 else [outer[k], outer[k2], inner[k2], inner[k]], "tyre")
            disc = outer if side > 0 else list(reversed(outer))
            m.face(disc, "atlas", [sp.uv(Vector((0, p.y, p.z))) for p in disc])
            m.face(list(reversed(inner)) if side > 0 else inner, "tyre")
            m.obj(origin=hub, parent=body)
    return {"body": body, "mats": mats, "proj": proj, "wheels": wl, "top_z": top_z, "an": an}


def build(an, out_glb, render_prefix=None, body_rough=0.45):
    ctx = make(an, body_rough)
    finish(ctx, out_glb, render_prefix)


def finish(ctx, out_glb, render_prefix=None):
    an = ctx["an"]
    aid = an["id"]
    L, W, H = an["size_m"]
    V = an["views"]
    core.export(out_glb)
    try:
        nf = len(ctx["body"].data.polygons)
    except ReferenceError:
        nf = -1
    print("ASSET_EXPORTED", aid, out_glb, nf, "faces", len(ctx["wheels"]), "wheels")
    if render_prefix:
        sc, cam = core.render_setup()
        sv = V["side"]
        x0, y0, x1, y1 = sv["bbox"]
        s = sv["scale"]
        w, h = sv["w"], sv["h"]
        centre = (0, (w / 2 - (x0 + x1) / 2) * s, (y1 - h / 2) * s)
        core.render_ortho(render_prefix + "_side.png", cam, "side", centre, max(w, h) * s, w, h)
        core.render_persp(render_prefix + "_34.png", cam, (0, 0, H * 0.45), (-L * 0.75 - 2, L * 0.8 + 2, H * 0.9 + L * 0.25))
        if "front" in V:
            fv = V["front"]
            fx0, fy0, fx1, fy1 = fv["bbox"]
            fs = fv["scale"]
            core.render_ortho(render_prefix + "_front.png", cam, "front", ((fv["w"] / 2 - (fx0 + fx1) / 2) * -fs, 0, (fy1 - fv["h"] / 2) * fs),
                              max(fv["w"], fv["h"]) * fs, fv["w"], fv["h"])
        print("ASSET_RENDERED", aid)
