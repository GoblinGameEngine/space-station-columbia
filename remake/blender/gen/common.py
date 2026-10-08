"""
common.py -- shared pieces for the catalog generators (remake/blender/gen/*).

A catalog record (remake/catalog/<ID>.json, see remake/research/CATALOG_SPEC.md) describes one
real-world example as traits; each kind's generator turns the traits into a Building using the
shared texture library ("lib" set, remake/textures/lib) tinted per building.
"""
import hashlib
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import gblib as g  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CATALOG = os.path.join(ROOT, "remake", "catalog")
LIB = os.path.join(ROOT, "remake", "textures", "lib")
OUT_DIR = os.path.join(ROOT, "godot_project", "remake", "buildings")
INVENTORY = os.path.join(ROOT, "remake", "inventory", "map_inventory.json")

with open(os.path.join(LIB, "set.json")) as _f:
    TILES = json.load(_f)["tile_m"]

FT = g.FT


def ft(v):
    return v * FT


def load_record(rid):
    with open(os.path.join(CATALOG, rid + ".json")) as f:
        return json.load(f)


def out_path(rid):
    return os.path.join(OUT_DIR, rid + ".glb")


def rng(rid, salt=""):
    """Deterministic per-structure randomness (same record -> same building)."""
    return random.Random(int(hashlib.sha1((rid + salt).encode()).hexdigest()[:12], 16))


def dget(tr, key):
    """A trait that should be an object; tolerate records that give a bare word (e.g. roof: "dome")."""
    v = (tr or {}).get(key)
    return v if isinstance(v, dict) else ({"type": v} if isinstance(v, str) else {})


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def hexcol(h, default="#dddddd"):
    try:
        return g.hex_rgb(h or default)
    except (ValueError, TypeError):
        return g.hex_rgb(default)


def darken(rgb, k):
    return tuple(c * k for c in rgb)


def lum(rgb):
    return 0.3 * rgb[0] + 0.59 * rgb[1] + 0.11 * rgb[2]


# ------------------------------------------------------------------ trait -> library texture
WALL_TEX = {"clapboard": "clapboard", "drop_siding": "drop_siding", "wood_shingle": "wall_shingle",
            "stucco": "stucco", "half_timber": "stucco", "asbestos_shingle": "asbestos", "aluminum": "aluminum",
            "vinyl": "vinyl", "board_and_batten": "board_batten", "log": "logs", "stone": "limestone",
            "brick": "brick_red", "block": "block", "metal": "corrugated", "concrete": "concrete",
            "cast_iron_front": "brick_red", "frame_false_front": "drop_siding", "glass_modern": "stucco",
            "fiber_cement": "clapboard_wide", "shingle": "wall_shingle", "cedar_shingle": "wall_shingle", "wood": "board_batten",
            "frame": "clapboard", "glass_curtain": "stucco", "tabby": "stucco", "granite": "granite", "granite_pink": "granite_pink",
            "adobe": "stucco", "smooth_stucco": "stucco"}
PAINTABLE = {"clapboard", "clapboard_wide", "drop_siding", "wall_shingle", "stucco", "asbestos", "aluminum", "vinyl",
             "board_batten", "paint", "paint_gloss", "barn_board", "floor_painted", "beadboard", "plaster", "drywall",
             "roof_asphalt", "metal_roof", "brick_painted", "carpet", "fabric"}
ROOF_TEX = {"asphalt_shingle": "roof_asphalt", "wood_shingle": "roof_wood", "slate": "roof_slate", "metal": "metal_roof",
            "tile": "roof_clay", "clay_tile": "roof_clay", "barrel_tile": "roof_clay", "clay_tile_old": "roof_clay_old"}
FOUND_TEX = {"fieldstone": "fieldstone", "brick": "brick_common", "concrete_block": "block", "poured_concrete": "concrete",
             "cut_stone": "limestone", "piles": "concrete", "slab": "concrete"}
BRICKS = [("brick_red", (0.56, 0.29, 0.21)), ("brick_brown", (0.43, 0.27, 0.2)), ("brick_buff", (0.79, 0.67, 0.49)),
          ("brick_cream", (0.87, 0.82, 0.68)), ("brick_dark", (0.31, 0.19, 0.16)), ("brick_common", (0.61, 0.35, 0.26))]


def brick_for(rgb):
    """Nearest library brick to a trait colour."""
    return min(BRICKS, key=lambda t: sum((a - b) ** 2 for a, b in zip(t[1], rgb)))[0]


class Palette:
    """Library materials on one Building: surf() for textured (optionally tinted) surfaces,
    solid() for plain colours.  Keys are the names the builders pass around."""

    def __init__(self, b):
        self.b = b

    def surf(self, key, tex, tint=None, rough=0.6, metal=0.0, alpha=None):
        t = hexcol(tint) if isinstance(tint, str) else tint
        return self.b.mat(key, tex=tex, tile_m=TILES.get(tex, 1.0), tint=t if tex in PAINTABLE else None,
                          rough=rough, metal=metal, alpha=alpha)

    def solid(self, key, rgb, rough=0.6, metal=0.0, alpha=None, emission=None):
        if isinstance(rgb, str):
            rgb = tuple(g.srgb_to_linear(c) for c in hexcol(rgb))
        return self.b.mat(key, color=rgb, rough=rough, metal=metal, alpha=alpha, emission=emission)


def lib_building(rid):
    return g.Building(rid, LIB)


def std_materials(pal, trim="#f2efe6", door="#5a3a26"):
    """The plain materials the shared builders reference by fixed name."""
    s = pal.solid
    for k, c, r in (("brass", (0.75, 0.6, 0.28), 0.3), ("threshold", (0.5, 0.48, 0.44), 0.8),
                    ("enamel", (0.93, 0.93, 0.9), 0.3), ("steel", (0.7, 0.72, 0.74), 0.35),
                    ("china", (0.96, 0.96, 0.94), 0.2), ("counter_top", (0.78, 0.74, 0.66), 0.4),
                    ("quilt", (0.6, 0.25, 0.22), 0.9), ("rug", (0.45, 0.2, 0.18), 0.95), ("tv", (0.05, 0.05, 0.06), 0.2),
                    ("burlap", (0.6, 0.5, 0.35), 0.95), ("mail_black", (0.08, 0.08, 0.08), 0.4),
                    ("white_text", (0.95, 0.95, 0.95), 0.5), ("black_text", (0.03, 0.03, 0.03), 0.5),
                    ("car_paint", (0.35, 0.05, 0.06), 0.3), ("tire", (0.05, 0.05, 0.05), 0.9),
                    ("chainlink", (0.62, 0.64, 0.66), 0.4), ("iron", (0.12, 0.12, 0.12), 0.5), ("bottle", (0.2, 0.35, 0.18), 0.1),
                    ("vinyl_red", (0.55, 0.06, 0.06), 0.4), ("plywood", (0.62, 0.5, 0.33), 0.8), ("rope", (0.55, 0.48, 0.36), 0.9),
                    ("green_leaf", (0.12, 0.25, 0.07), 0.9), ("bark", (0.18, 0.13, 0.09), 0.9)):
        s(k, c, rough=r, metal=0.9 if k in ("brass", "steel", "chainlink") else 0.0)
    s("glass", (0.72, 0.8, 0.84), rough=0.05, alpha=0.2)
    s("glassblock", (0.75, 0.82, 0.85), rough=0.2, alpha=0.6)
    s("mirror", (0.8, 0.82, 0.85), rough=0.05, metal=1.0)
    pal.surf("trim", "paint", trim, rough=0.45)
    pal.surf("door", "paint_gloss", door, rough=0.35)
    pal.surf("furniture", "wood_medium", rough=0.4)
    pal.surf("furn_dark", "wood_dark", rough=0.4)
    pal.surf("furn_light", "wood_light", rough=0.45)
    pal.surf("upholstery", "fabric", "#6f7f64", rough=0.95)
    pal.surf("lino", "lino_checker", rough=0.35)
    pal.surf("hextile", "hex_tile", rough=0.3)
    pal.surf("concrete", "concrete", rough=0.9)
    pal.surf("sidewalk", "sidewalk", rough=0.9)
    pal.surf("asphalt", "asphalt", rough=0.9)
    pal.surf("gravel", "gravel", rough=0.95)
    pal.surf("stone", "limestone", rough=0.85)


def sign_board(b, part, frame, text_lines, board_w, board_h, board_mat, text_mat, name, depth=0.04, font=None):
    """A flat sign board in a wall frame (o, u, w_in, up) with lettering on its outer face.
    frame origin = board's bottom-centre on the outer wall face; lettering faces -w_in (outwards)."""
    o, u, w_in, up = frame
    F = (o, u, w_in, up)
    part.obox(F, (-board_w / 2, -depth, 0.0), (board_w / 2, 0.0, board_h), board_mat)
    n = len(text_lines)
    for i, (txt, size) in enumerate(text_lines):
        z = board_h * (1 - (i + 0.5) / n)
        p = o + up * (z - size * 0.35) - w_in * (depth + 0.004)
        yaw = math.atan2(-w_in.x, w_in.y)            # text faces -Y at yaw 0; turn it to face out (-w_in)
        g.text_mesh(b, f"{name}_{i}", txt, size, tuple(p), yaw, text_mat, extrude=0.004, font=font)


FONT_SANS = "/run/host/usr/share/fonts/noto/NotoSans-Bold.ttf"
FONT_SERIF = "/run/host/usr/share/fonts/noto/NotoSerif-Bold.ttf"
