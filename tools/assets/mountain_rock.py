#!/usr/bin/env python3
"""mountain_rock.py -- the end-cap mountains' rock (godot_project/remake/scripts/cap_mountains.gd, shaders/mountain_rock.gdshader).

The user, 2026-10-06: "The texture is also wrong, it should be more natural like a mountain." The first version (vertical
joints at regular spacing, long streaks) read as planks. This one is weathered granite-and-limestone mountain rock:
  * grain at several scales (crystals, pitting, lumps)
  * a crack network from cellular noise: big blocks split into smaller ones, edges that wander, each block its own
    shade and rounded off toward its cracks -- a weathered, fractured face
  * lichen and weathering patches (grey-green, ochre, dark) in blotches, not stripes
  * desert-varnish streaks, short and broken, only where water runs down
Tileable (wraps both ways), neutral in colour: the mesh's vertex colours carry the strata, and the shader adds a large
macro tint (mountain_macro: hundreds of metres) so the repeat never shows at the mountains' scale.

    ~/.venvs/ssc-assets/bin/python tools/assets/mountain_rock.py     # -> godot_project/remake/cliffs/mountain_*
"""
import os

import numpy as np
from PIL import Image

N = 1024
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "godot_project", "remake", "cliffs")   # (tracked: remake/textures is gitignored)


def noise(n, fx, fy, seed):
    """Tileable value noise on an n x n grid: fx x fy random cells, smoothly upsampled (wraps both ways)."""
    g = np.random.default_rng(seed).random((fy, fx))
    ys = np.arange(n) * fy / n
    xs = np.arange(n) * fx / n
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    ty, tx = ys - y0, xs - x0
    ty, tx = ty * ty * (3 - 2 * ty), tx * tx * (3 - 2 * tx)
    y1, x1 = (y0 + 1) % fy, (x0 + 1) % fx
    a = g[np.ix_(y0, x0)] * (1 - tx) + g[np.ix_(y0, x1)] * tx
    b = g[np.ix_(y1, x0)] * (1 - tx) + g[np.ix_(y1, x1)] * tx
    return a * (1 - ty)[:, None] + b * ty[:, None]


def fbm(n, f, octaves, seed, aniso=1.0):
    out = np.zeros((n, n))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        fx = max(1, int(f * 2 ** o))
        fy = max(1, int(f * 2 ** o / aniso))
        out += amp * noise(n, fx, fy, seed + o * 7)
        tot += amp
        amp *= 0.55
    return out / tot


def worley(n, cells, seed, sy=1.0, warp=None):
    """Tileable cellular noise: (F1, F2, id of the nearest cell) per pixel, with jittered points in a cells x cells
    grid (wrapping). sy < 1 stretches the cells vertically (rock in tall blocks)."""
    rng = np.random.default_rng(seed)
    pts = rng.random((cells, cells, 2))
    ys, xs = np.mgrid[0:n, 0:n] / n * cells
    if warp is not None:                                         # (jagged edges: the coordinates wander)
        xs = xs + warp[0] * cells
        ys = ys + warp[1] * cells
    cy, cx = np.floor(ys).astype(int), np.floor(xs).astype(int)
    f1 = np.full((n, n), 9.0)
    f2 = np.full((n, n), 9.0)
    idx = np.zeros((n, n), np.int64)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            gy, gx = cy + dy, cx + dx
            p = pts[gy % cells, gx % cells]
            px, py = gx + p[..., 0], gy + p[..., 1]
            d = np.sqrt((px - xs) ** 2 + ((py - ys) * sy) ** 2)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            idx = np.where(closer, (gy % cells) * cells + (gx % cells), idx)
            f1 = np.where(closer, d, f1)
    return f1, f2, idx


def main():
    n = N
    rng = np.random.default_rng(2752)
    grain = fbm(n, 16, 6, 1)                                   # crystals and pitting
    lumps = fbm(n, 5, 4, 41)                                   # knobs and hollows
    # domain warp (two scales): edges wander and kink, as joints do
    wx = (fbm(n, 4, 4, 71) - 0.5) * 0.05 + (fbm(n, 14, 3, 73) - 0.5) * 0.012
    wy = (fbm(n, 4, 4, 75) - 0.5) * 0.05 + (fbm(n, 14, 3, 79) - 0.5) * 0.012
    f1, f2, cid = worley(n, 6, 11, sy=0.6, warp=(wx, wy))
    g1, g2, gid = worley(n, 15, 23, sy=0.75, warp=(wx * 1.5, wy * 1.5))
    width = 0.03 + 0.07 * fbm(n, 5, 3, 91)                     # (cracks open and close along their length)
    edge_big = np.clip(1.0 - (f2 - f1) / width, 0, 1) ** 1.5 * np.clip((fbm(n, 4, 3, 93) - 0.3) * 3.0, 0, 1)
    edge_small = np.clip(1.0 - (g2 - g1) / (width * 0.5), 0, 1) ** 2 * np.clip((fbm(n, 7, 3, 99) - 0.45) * 4.0, 0, 1)
    cracks = np.maximum(edge_big, 0.6 * edge_small)
    # each block a flat facet, tilted its own way (angular rock, not cushions)
    ys, xs = np.mgrid[0:n, 0:n] / n
    ang = rng.random(6 * 6) * np.pi * 2
    slope = rng.random(6 * 6) * 0.35
    facet = (np.cos(ang)[cid] * xs * 6 + np.sin(ang)[cid] * ys * 6) % 1.0 * slope[cid]
    ang2 = rng.random(15 * 15) * np.pi * 2
    facet2 = (np.cos(ang2)[gid] * xs * 15 + np.sin(ang2)[gid] * ys * 15) % 1.0 * 0.12
    block_tone = rng.random(6 * 6)[cid] * 0.18 - 0.09 + rng.random(15 * 15)[gid] * 0.08 - 0.04
    bevel = facet + facet2
    # weathering: soft patches
    lichen_g = np.clip((fbm(n, 8, 5, 601) - 0.56) * 3.0, 0, 1) ** 1.5
    lichen_o = np.clip((fbm(n, 6, 5, 607) - 0.60) * 3.0, 0, 1) ** 1.5
    stain = np.clip((fbm(n, 4, 4, 613) - 0.5) * 2.5, 0, 1)
    varnish = np.clip((fbm(n, 20, 3, 619, aniso=4.0) - 0.6) * 3.0, 0, 1) * (fbm(n, 5, 2, 623) > 0.5)
    height = 0.5 * bevel + 0.3 * grain + 0.25 * lumps - 0.6 * cracks
    v = 0.55 + 0.18 * (grain - 0.5) + 0.14 * (lumps - 0.5) + block_tone + 0.22 * (bevel - 0.12) - 0.42 * cracks \
        - 0.14 * stain - 0.10 * varnish
    alb = np.stack([v * 1.0, v * 0.96, v * 0.90], -1)          # (warm grey: the vertex colours carry the strata)
    alb = alb * (1 - 0.45 * lichen_g[..., None]) + 0.45 * lichen_g[..., None] * np.array([0.45, 0.50, 0.38])
    alb = alb * (1 - 0.35 * lichen_o[..., None]) + 0.35 * lichen_o[..., None] * np.array([0.62, 0.52, 0.32])
    alb = np.clip(alb, 0.04, 1.0)
    Image.fromarray((alb * 255).astype(np.uint8)).save(os.path.join(OUT, "mountain_albedo.webp"), quality=92)
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 5.0
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 5.0
    nrm = np.stack([-dx, dy, np.ones_like(dx)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(OUT, "mountain_normal.webp"), quality=92)
    rough = np.clip(0.9 + 0.06 * (grain - 0.5) - 0.2 * varnish, 0, 1)
    Image.fromarray((rough * 255).astype(np.uint8)).save(os.path.join(OUT, "mountain_rough.webp"), quality=92)
    # the macro tint: broad colour fields over hundreds of metres (sampled at ~1/700 m by the shader)
    m = 512
    t1 = fbm(m, 3, 5, 801)
    t2 = fbm(m, 5, 4, 809)
    macro = np.stack([0.5 + 0.45 * (t1 - 0.5) + 0.15 * (t2 - 0.5), 0.5 + 0.40 * (t1 - 0.5) + 0.05 * (t2 - 0.5),
                      0.5 + 0.30 * (t1 - 0.5) - 0.10 * (t2 - 0.5)], -1)
    Image.fromarray((np.clip(macro, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, "mountain_macro.webp"), quality=92)
    print("mountain rock ->", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
