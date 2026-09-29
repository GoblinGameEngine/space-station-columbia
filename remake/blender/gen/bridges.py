"""
bridges.py -- crossing records (MAJOR-*, SMALL-*, CULVERT-*, RAIL-*) -> Building.

Convention: the road (or track) runs along local +y through the origin, its surface at z = 0 at
both ends; the stream / obstacle runs along x.  Abutments and piers go down well below the bed so
the crossing can be dropped onto any terrain cut.  No creek terrain is built: the map provides it.
"""
import math
import os

from common import ROOT, clamp, ft, g, FONT_SANS
import gbbridge as gbr

INV = None


def inventory_crossing(rid):
    global INV
    if INV is None:
        import json
        INV = {c["id"]: c for c in json.load(open(os.path.join(ROOT, "remake", "inventory", "map_inventory.json")))["crossings"]}
    return INV.get(rid, {})


def truss(b, span, width, height, panels, kind, z=0.0, name="truss", yc=0.0):
    """Through truss (Pratt / Parker / camelback): two trusses at x = +-width/2, floor beams, deck,
    top lateral + sway bracing and portal struts (clearance 4.6 m)."""
    p = b.part(f"{name}-col")
    pl = span / panels
    y0 = yc - span / 2
    ye = yc + span / 2

    def top_z(k):
        if kind in ("through_truss_parker", "camelback") and panels >= 5:
            t = k / panels
            return z + height * (0.78 + 0.22 * math.sin(math.pi * t))
        return z + height
    for sx in (-1, 1):
        x = sx * width / 2
        p.box((x - 0.18, y0, z - 0.45), (x + 0.18, ye, z + 0.05), "truss")                # bottom chord
        for k in range(1, panels):
            yk = y0 + k * pl
            gbr.strut(p, (x, yk, z), (x, yk, top_z(k)), 0.22, 0.2, "truss")               # verticals
        for k in range(1, panels - 1):
            ya, yb = y0 + k * pl, y0 + (k + 1) * pl
            gbr.strut(p, (x, ya, top_z(k)), (x, yb, top_z(k + 1)), 0.4, 0.3, "truss")    # top chord
        gbr.strut(p, (x, y0, z), (x, y0 + pl, top_z(1)), 0.4, 0.3, "truss")              # inclined end posts
        gbr.strut(p, (x, ye, z), (x, ye - pl, top_z(panels - 1)), 0.4, 0.3, "truss")
        for k in range(1, panels - 1):                                                    # diagonals toward the centre
            ya, yb = y0 + k * pl, y0 + (k + 1) * pl
            if yb <= yc + 0.01:
                gbr.strut(p, (x, ya, top_z(k)), (x, yb, z), 0.12, 0.12, "truss")
            else:
                gbr.strut(p, (x, yb, top_z(k + 1)), (x, ya, z), 0.12, 0.12, "truss")
    for k in range(1, panels):                                                            # top struts + x-bracing
        yk = y0 + k * pl
        gbr.strut(p, (-width / 2, yk, top_z(k)), (width / 2, yk, top_z(k)), 0.18, 0.18, "truss")
    for yp in (y0 + pl, ye - pl):                                                         # portals
        p.box((-width / 2, yp - 0.12, z + 4.7), (width / 2, yp + 0.12, z + 5.2), "truss")
    for k in range(panels + 1):                                                           # floor beams under the deck
        yk = y0 + k * pl
        p.box((-width / 2 - 0.2, yk - 0.15, z - 0.9), (width / 2 + 0.2, yk + 0.15, z - 0.35), "truss")
    return top_z


def deck(b, L, width, z=0.0, mat="asphalt", thick=0.3, name="deck"):
    p = b.part(f"{name}-col")
    p.box((-width / 2, -L / 2, z - thick), (width / 2, L / 2, z), mat, mats={"z": "concrete_old"})
    for sx in (-1, 1):
        p.box((sx * width / 2 - (0.3 if sx > 0 else 0.0), -L / 2, z), (sx * width / 2 + (0.3 if sx < 0 else 0.0), L / 2, z + 0.25),
              "concrete")
    return p


def railing(b, L, width, style, z=0.0, name="rail", mat="concrete"):
    p = b.part(f"{name}-col")
    for sx in (-1, 1):
        x = sx * (width / 2 - 0.15)
        if style == "concrete_balustrade":
            p.box((x - 0.15, -L / 2, z + 0.25), (x + 0.15, L / 2, z + 0.35), "concrete")
            p.box((x - 0.18, -L / 2, z + 0.95), (x + 0.18, L / 2, z + 1.1), "concrete")
            k = -L / 2 + 0.2
            while k < L / 2 - 0.1:
                p.box((x - 0.07, k - 0.06, z + 0.35), (x + 0.07, k + 0.06, z + 0.95), "concrete")
                k += 0.3
        elif style == "open_parapet":
            p.box((x - 0.15, -L / 2, z + 0.25), (x + 0.15, L / 2, z + 1.0), "concrete")
        elif style == "solid_parapet":
            p.box((x - 0.2, -L / 2, z), (x + 0.2, L / 2, z + 0.85), mat)                           # solid wall
            p.box((x - 0.26, -L / 2 - 0.1, z + 0.85), (x + 0.26, L / 2 + 0.1, z + 1.0), "concrete")   # coping
        elif style == "lattice":
            for zz in (z + 0.3, z + 1.05):
                p.box((x - 0.05, -L / 2, zz), (x + 0.05, L / 2, zz + 0.08), "truss")
            k = -L / 2
            while k < L / 2:
                gbr.strut(p, (x, k, z + 0.3), (x, min(L / 2, k + 0.35), z + 1.1), 0.05, 0.02, "truss")
                gbr.strut(p, (x, min(L / 2, k + 0.35), z + 0.3), (x, k, z + 1.1), 0.05, 0.02, "truss")
                k += 0.35
        elif style == "pipe_rail":
            for zz in (z + 0.55, z + 1.0):
                p.box((x - 0.03, -L / 2, zz), (x + 0.03, L / 2, zz + 0.06), "guardrail")
            k = -L / 2
            while k <= L / 2:
                p.box((x - 0.04, k - 0.04, z), (x + 0.04, k + 0.04, z + 1.06), "guardrail")
                k += 2.0
        else:
            gbr.guardrail(b, [(x, -L / 2), (x, L / 2)], z=z, name=f"{name}_{'e' if sx > 0 else 'w'}")


def sign_text(v):
    """A record's sign / plate text for display: '' for placeholders ('none', 'none (unnamed
    ditch)', 'n/a'), and without parenthetical notes ('Pine Creek (stenciled on headwall)')."""
    if not v:
        return ""
    s = str(v).strip()
    if s.lower().startswith(("none", "no ", "n/a", "unknown", "unmarked")):
        return ""
    import re
    return re.sub(r"\s*\([^)]*\)", "", s).strip()


def railing_style(tr, default):
    """The railing trait, refined by railing_detail: the vocabulary has no solid-parapet word, so
    solid parapets / headwalls are recorded as open_parapet with a detail saying 'solid'."""
    style = tr.get("railing") or default
    det = str(tr.get("railing_detail") or "").lower()
    if style == "open_parapet" and ("solid" in det or "headwall" in det or "wall" in det and "open" not in det):
        return "solid_parapet"
    return style


def build(rec):
    rid = rec["id"]
    tr = rec.get("traits") or {}
    names = rec.get("names") or {}
    inv = inventory_crossing(rid)
    b = g.Building(rid, os.path.join(ROOT, "remake", "textures", "p-bridges"))
    gbr.bridge_materials(b)
    b.mat("sign_blue", color=(0.05, 0.12, 0.35), rough=0.5)
    b.mat("plate", color=(0.45, 0.33, 0.18), rough=0.35, metal=0.9)
    b.mat("black", color=(0.04, 0.04, 0.04), rough=0.5)
    b.mat("timber", tex="ties", tile_m=2.6)
    btype = tr.get("bridge_type", "steel_stringer")
    # model_spans: the record asks for only part of a longer example to be modelled
    spans = int(clamp(tr.get("model_spans") or tr.get("spans") or 1, 1, 14))
    span_each = ft(tr.get("span_ft") or 40)
    total = inv.get("span_m") or span_each * spans
    total = clamp(total, 3.0, 120.0)
    span_each = total / spans
    road = inv.get("road_class", "county")
    is_rail = btype in ("steel_girder_rail", "deck_girder", "timber_trestle") or inv.get("type") == "rail"
    width = ft(tr.get("width_ft") or 0) or {"hwy": 9.0, "county": 7.0, "main": 10.0, "street": 8.0, "gravel": 5.5, "rail": 4.2}.get(road, 7.0)
    width = clamp(width, 4.0, 12.0)
    bed = -{"major": 7.0, "small": 3.5, "culvert": 2.2, "rail": 5.0}.get(inv.get("type", "small"), 3.5)
    deep = -g.FOUND_DEPTH - 3.0
    L = total
    # abutments at both ends (deep), piers between spans
    for s in (-1, 1):
        p = b.part(f"abut_{'n' if s > 0 else 's'}-col")
        y = s * L / 2
        p.box((-width / 2 - 0.8, min(y, y + s * 2.5), deep), (width / 2 + 0.8, max(y, y + s * 2.5), -0.3),
              "ashlar" if btype in ("stone_arch", "timber_trestle") or tr.get("year", 1950) < 1910 else "concrete_old")
        for sx in (-1, 1):                                           # wingwalls
            p.box((sx * (width / 2 + 0.3), min(y, y + s * 5.0), deep), (sx * (width / 2 + 0.8), max(y, y + s * 5.0), 0.1), "concrete_old")
    for k in range(1, spans):
        y = -L / 2 + k * span_each
        p = b.part(f"pier_{k}-col")
        if btype == "timber_trestle":
            for x in (-1.5, -0.5, 0.5, 1.5):
                p.box((x - 0.15, y - 0.15, bed - 1.0), (x + 0.15, y + 0.15, -0.35), "timber")
            p.box((-2.0, y - 0.2, -0.6), (2.0, y + 0.2, -0.3), "timber")
        else:
            p.box((-width / 2 - 0.3, y - 0.6, deep), (width / 2 + 0.3, y + 0.6, -0.35), "ashlar" if btype == "stone_arch" else "concrete_old")
    # the structure
    if btype in ("through_truss_pratt", "through_truss_parker", "camelback"):
        h = clamp(ft(tr.get("height_ft") or 22), 5.5, 9.0)
        panels = int(clamp(tr.get("panels") or round(span_each / 6.0), 4, 14))
        for k in range(spans):
            yc = -L / 2 + (k + 0.5) * span_each
            truss(b, span_each, width + 0.6, h, panels, btype, name=f"truss{k}", yc=yc)
        deck(b, L, width)
        railing(b, L, width, "pipe_rail")
    elif btype in ("pony_truss", "warren_pony"):
        h = clamp(ft(tr.get("height_ft") or 8), 1.8, 3.0)
        panels = int(clamp(tr.get("panels") or round(span_each / 3.5), 4, 12))
        gbr.pony_truss(b, span_each if spans == 1 else L, width + 0.4, h, panels)
        deck(b, L, width)
    elif btype in ("steel_stringer", "deck_girder", "steel_girder_rail", "concrete_t_beam", "concrete_slab"):
        d_ = b.part("superstructure-col")
        nb = 5 if not is_rail else 2
        for i in range(nb):
            x = -width / 2 + 0.6 + (width - 1.2) * i / max(1, nb - 1)
            mat = "truss" if btype in ("steel_stringer", "deck_girder", "steel_girder_rail") else "concrete_old"
            dep = 1.8 if btype == "deck_girder" else (0.9 if btype != "concrete_slab" else 0.0)
            if dep > 0:
                d_.box((x - 0.2, -L / 2, -0.3 - dep), (x + 0.2, L / 2, -0.3), mat)
        if is_rail:
            gbr.track(b, -L / 2 - 6.0, L / 2 + 6.0, 0.0)
            railing(b, L, width, "pipe_rail")
        else:
            deck(b, L, width)
            railing(b, L, width, railing_style(tr, "concrete_balustrade" if btype.startswith("concrete") else "guardrail"))
    elif btype in ("stone_arch", "concrete_arch"):
        rise = clamp(span_each / 2, 1.2, 12.0)
        # one barrel per span (arch_barrel builds it centred on y = 0: shift each to its span)
        for k in range(spans):
            # the barrel's crown stays under the deck (a long span's semicircle is taller than its
            # rise cap: springing it from the bed drove the crown up through the road)
            gbr.arch_barrel(b, span_each, 0.0, width + 1.0, min(bed if rise < -bed else -rise - 0.9, -span_each / 2 - 1.3),
                            ring_mat="ashlar" if btype == "stone_arch" else "concrete_old",
                            face_mat="ashlar" if btype == "stone_arch" else "concrete_old", name=f"arch{k}")
            yc = -L / 2 + (k + 0.5) * span_each
            for part in (f"arch{k}-col", f"arch{k}_face-col"):
                if part in b.objs:
                    for v in b.part(part).bm.verts:
                        v.co.y += yc
        deck(b, L, width, mat="asphalt" if not is_rail else "ballast")
        railing(b, L, width, railing_style(tr, "open_parapet"), mat="ashlar" if btype == "stone_arch" else "concrete")
        if is_rail:
            gbr.track(b, -L / 2 - 6.0, L / 2 + 6.0, 0.0)
    elif btype in ("box_culvert", "pipe_culvert"):
        # road on fill over the culvert: pavement across, headwalls with the barrel(s) under it
        pv = b.part("pavement-col")
        pv.box((-width / 2 - 1.0, -6.0, -0.3), (width / 2 + 1.0, 6.0, 0.0), "asphalt" if not is_rail else "ballast",
               mats={"z": "concrete_old"})
        cell = clamp(total if total < 4.0 else total / 2, 1.2, 3.6)
        cells = 1 if total < 4.0 else 2
        if btype == "box_culvert":
            # barrel along x (under the road's full width + shoulders), cells side by side along y
            gbr.box_culvert(b, cells, cell, min(cell, -bed - 0.5), width + 6.0, width, bed)
        else:
            # pipes carry the stream along x under the road (which runs along y); headwalls at the
            # pipe ends face +-x.  (They used to run along y, parallel to the road.)
            cp = b.part("pipe-col")
            r = clamp(cell / 2, 0.5, 1.5)
            r = min(r, max(0.3, (-0.5 - bed) / 2))      # buried under the pavement, not up through it
            xe = (width + 6.0) / 2
            for c in range(cells):
                cy = (c - (cells - 1) / 2) * (2 * r + 0.8)
                for i in range(16):
                    a0, a1 = 2 * math.pi * i / 16, 2 * math.pi * (i + 1) / 16
                    P = lambda a, x, rr: (x, cy + rr * math.cos(a), bed + r + rr * math.sin(a))
                    cp.face([P(a0, -xe, r), P(a1, -xe, r), P(a1, xe, r), P(a0, xe, r)], "concrete_old")
            hw = cells * r + (cells - 1) * 0.4 + 1.2
            cys = [(c - (cells - 1) / 2) * (2 * r + 0.8) for c in range(cells)]
            for s in (-1, 1):
                x_a, x_b = s * xe - 0.2, s * xe + 0.2
                cp.box((x_a, -hw, bed + 2 * r), (x_b, hw, 0.2), "concrete")          # over the pipe mouths
                edges = [-hw] + [e for cy_ in cys for e in (cy_ - r, cy_ + r)] + [hw]
                for k in range(0, len(edges), 2):                                    # beside / between them
                    cp.box((x_a, edges[k], bed), (x_b, edges[k + 1], bed + 2 * r), "concrete")
        gbr.guardrail(b, [(-width / 2 - 0.6, -8.0), (-width / 2 - 0.6, 8.0)], name="gr_w")
        gbr.guardrail(b, [(width / 2 + 0.6, -8.0), (width / 2 + 0.6, 8.0)], name="gr_e")
    elif btype == "timber_trestle":
        tp = b.part("trestle-col")
        n = max(2, int(L / 4.0))
        for k in range(n + 1):
            y = -L / 2 + k * L / n
            for x in (-1.2, -0.4, 0.4, 1.2):
                tp.box((x - 0.14, y - 0.14, bed - 1.0), (x + 0.14, y + 0.14, -0.6), "timber")
            tp.box((-1.8, y - 0.2, -0.6), (1.8, y + 0.2, -0.3), "timber")
        for x in (-0.8, 0.8):
            tp.box((x - 0.2, -L / 2, -0.3), (x + 0.2, L / 2, 0.0), "timber")
        gbr.track(b, -L / 2 - 6.0, L / 2 + 6.0, 0.0)
    else:
        deck(b, L, width)
        railing(b, L, width, "guardrail")
    # approach pavement at both ends, name signs and the builder's plate
    ap = b.part("approach-col")
    for s in (-1, 1):
        y = s * L / 2
        if not is_rail:
            ap.box((-width / 2, min(y, y + s * 8.0), -0.3), (width / 2, max(y, y + s * 8.0), 0.0), "asphalt", mats={"z": "concrete_old"})
    over = sign_text(inv.get("over")) or sign_text(names.get("sign"))
    sign = (sign_text(names.get("sign")) or over).upper()
    if sign and not is_rail:
        for s in (-1, 1):
            gbr.post_sign(b, f"namesign_{'n' if s > 0 else 's'}", s * (width / 2 + 1.2), s * (L / 2 + 6.0), 0.0 if s < 0 else math.pi,
                          [(sign[:22], 0.16)], board=(max(1.2, len(sign[:22]) * 0.11), 0.4), board_mat="sign_blue",
                          text_mat="sign_white", height=1.6)
    # regulatory signs from the record (e.g. WEIGHT LIMIT 10 TONS), white boards at both approaches
    extra = [sign_text(e).upper() for e in (names.get("extra_signs") or []) if sign_text(e)]
    if extra and not is_rail:
        for s in (-1, 1):
            gbr.post_sign(b, f"extrasign_{'n' if s > 0 else 's'}", -s * (width / 2 + 1.2), s * (L / 2 + 4.5), 0.0 if s < 0 else math.pi,
                          [(e[:20], 0.12) for e in extra[:3]], board=(max(0.9, max(len(e[:20]) for e in extra[:3]) * 0.085), 0.25 + 0.2 * len(extra[:3])),
                          board_mat="sign_white", text_mat="sign_black", height=1.6)
    # raised sidewalks with a curb along both edges of the deck
    if tr.get("sidewalks") and not is_rail:
        sw = b.part("sidewalks-col")
        for sx in (-1, 1):
            xa, xb = sorted((sx * (width / 2 - 0.3), sx * (width / 2 - 1.8)))
            sw.box((xa, -L / 2, 0.0), (xb, L / 2, 0.18), "concrete")
    plate = sign_text(names.get("plate"))
    if plate:
        parts = [t.strip() for t in str(plate).replace("·", "-").split(" - ") if t.strip()][:3]
        pp = b.part("plate-col")
        pz = 1.2
        py = -L / 2 + 0.6
        pp.box((width / 2 + 0.05, py - 0.45, pz), (width / 2 + 0.09, py + 0.45, pz + 0.6), "plate")
        for i, t in enumerate(parts):
            g.text_mesh(b, f"sign_plate_{i}", t[:28], 0.045 if i else 0.06, (width / 2 + 0.095, py, pz + 0.45 - i * 0.14), -math.pi / 2,
                        "black", extrude=0.002, font=FONT_SANS)
    return b
