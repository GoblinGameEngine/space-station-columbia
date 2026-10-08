#!/usr/bin/env python3
"""
texgen.py -- procedural, tileable PBR textures for the clean-sheet remake.

Nothing here is derived from the old asset set: every texture is generated from
code (numpy noise + explicit construction geometry: board exposure, brick bond,
shingle coursing ...) so each building can get its own variant (paint colour,
weathering, board width) by changing parameters, not by copying files.

Each material writes  <out>/<name>_albedo.png, _normal.png, _rough.png
(1024^2, tileable; normal map is OpenGL/glTF convention, +Y up).

  texgen.py OUT_DIR SET          -- SET is a named recipe list in RECIPES below
"""

import inspect
import json
import math
import os
import sys

import numpy as np
from PIL import Image

N = 1024


def rng(seed):
    return np.random.default_rng(seed)


def fbm(seed, scale, octaves=4, size=N):
    """Periodic fractal noise in [0,1]: white noise low-passed in frequency space."""
    r = rng(seed)
    out = np.zeros((size, size))
    amp, tot = 1.0, 0.0
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    for o in range(octaves):
        cut = (2 ** o) / scale
        spec = np.fft.fft2(r.standard_normal((size, size)))
        spec *= np.exp(-(f / cut) ** 2)
        layer = np.real(np.fft.ifft2(spec))
        layer = (layer - layer.min()) / (np.ptp(layer) + 1e-9)
        out += amp * layer
        tot += amp
        amp *= 0.5
    return out / tot


def stretch_noise(seed, sx, sy, size=N):
    """Anisotropic periodic noise (wood grain): long in x, short in y."""
    r = rng(seed)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    spec = np.fft.fft2(r.standard_normal((size, size)))
    spec *= np.exp(-((fx * sx) ** 2 + (fy * sy) ** 2))
    n = np.real(np.fft.ifft2(spec))
    return (n - n.min()) / (np.ptp(n) + 1e-9)


def normal_from_height(h, strength):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    nx, ny, nz = -gx, gy, np.ones_like(h)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / L, ny / L, nz / L], -1)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def save(out, name, albedo, height, rough, nstrength=6.0):
    os.makedirs(out, exist_ok=True)
    a = np.clip(albedo, 0, 1)
    Image.fromarray((a * 255).astype(np.uint8), "RGB").save(f"{out}/{name}_albedo.png", optimize=True)
    Image.fromarray(normal_from_height(height, nstrength * N / 1024), "RGB").save(f"{out}/{name}_normal.png", optimize=True)
    Image.fromarray((np.clip(rough, 0, 1) * 255).astype(np.uint8), "L").save(f"{out}/{name}_rough.png", optimize=True)


def col(hexs):
    hexs = hexs.lstrip("#")
    return np.array([int(hexs[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def tint(base, var):
    return base[None, None, :] * var[..., None]


# ------------------------------------------------------------------ recipes
def clapboard(out, name, paint="#f2efe6", exposure_m=0.1016, tile_m=1.0, weather=0.35, seed=1):
    """Lap siding: each course is a wedge (thin top, thick butt) with a shadow line."""
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    courses = tile_m / exposure_m
    t = (y / exposure_m) % 1.0                        # 0 = top of course, 1 = butt
    h = t * 0.8 + 0.0 * x                             # wedge
    shadow = np.clip((t - 0.93) / 0.07, 0, 1)
    grain = stretch_noise(seed, 3, 60)
    paint_c = col(paint)
    wear = fbm(seed + 1, 90) ** 2 * weather
    streak = stretch_noise(seed + 2, 400, 4).T ** 3 * weather       # vertical run-off streaks
    # board butt joints, staggered per course
    ci = np.floor(y / exposure_m)
    joint_x = (ci * 0.37 % 1.0) * tile_m
    joint = np.exp(-((((x - joint_x) + tile_m / 2) % tile_m - tile_m / 2) / 0.003) ** 2)
    v = 1.0 - 0.10 * grain * weather - 0.35 * shadow - 0.08 * joint - 0.25 * wear - 0.3 * streak
    albedo = tint(paint_c, v) * (1 - wear[..., None] * 0.5) + wear[..., None] * 0.5 * col("#8a7a66")[None, None, :]
    h = h - 0.6 * shadow - 0.12 * joint + 0.05 * grain
    rough = 0.55 + 0.35 * wear + 0.05 * grain
    save(out, name, albedo, h, rough, 10)
    assert courses > 0


def cedar_shingles(out, name, base="#7d7468", exposure_m=0.127, tile_m=1.0, seed=2):
    """Sawn cedar shingles, weathered silver-grey, random widths, staggered keyways."""
    r = rng(seed)
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    ci = np.floor(y / exposure_m).astype(int)
    t = (y / exposure_m) % 1.0
    ncourse = int(round(tile_m / exposure_m))
    shade = np.zeros((N, N))
    gap = np.zeros((N, N))
    for c in range(ncourse + 1):
        edges, s = [], r.uniform(0, 0.2)
        while s < tile_m:
            edges.append(s)
            s += r.uniform(0.08, 0.25)
        rows = ci[:, 0] == (c % ncourse)
        if not rows.any():
            continue
        e = np.array(edges)
        idxs = np.searchsorted(e, x[0], side="right")
        sh = r.uniform(0.75, 1.05, len(e) + 1)[idxs]
        dist = np.min(np.abs(((x[0][None, :] - e[:, None]) + tile_m / 2) % tile_m - tile_m / 2), 0)
        shade[rows, :] = sh[None, :]
        gap[rows, :] = np.exp(-(dist / 0.004) ** 2)[None, :]
    grain = stretch_noise(seed + 3, 4, 90).T
    butt = np.clip((t - 0.9) / 0.1, 0, 1)
    moss = np.clip(fbm(seed + 4, 60) - 0.62, 0, 1) * 2.5
    v = shade * (0.85 + 0.2 * grain) * (1 - 0.45 * butt) * (1 - 0.7 * gap)
    albedo = tint(col(base), v) * (1 - moss[..., None]) + moss[..., None] * col("#5d6b45")[None, None, :] * v[..., None]
    h = t * 0.6 + 0.15 * grain - 0.5 * gap - 0.4 * butt
    save(out, name, albedo, h, 0.85 + 0.1 * grain, 8)


def fieldstone(out, name, base="#8f8676", mortar="#b8b0a0", tile_m=1.0, seed=3):
    """Rubble fieldstone foundation: Voronoi stones in mortar."""
    r = rng(seed)
    pts = r.uniform(0, 1, (38, 2))
    yy, xx = np.mgrid[0:N, 0:N] / N
    d1 = np.full((N, N), 9.0)
    d2 = np.full((N, N), 9.0)
    idx = np.zeros((N, N), int)
    for k, (px, py) in enumerate(pts):
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                d = np.hypot((xx - px - ox) * 1.0, (yy - py - oy) * 1.3)
                closer = d < d1
                d2 = np.where(closer, d1, np.minimum(d2, d))
                idx = np.where(closer, k, idx)
                d1 = np.where(closer, d, d1)
    edge = d2 - d1
    stone_v = r.uniform(0.7, 1.15, len(pts))[idx]
    n = fbm(seed + 1, 40)
    is_mortar = edge < 0.012
    v = stone_v * (0.8 + 0.4 * n)
    warm = r.uniform(-0.06, 0.06, len(pts))[idx]
    tints = np.stack([1 + warm, 1 + warm * 0.4, 1 - warm * 0.6], -1)
    albedo = np.where(is_mortar[..., None], col(mortar)[None, None, :] * (0.85 + 0.2 * n[..., None]),
                      col(base)[None, None, :] * v[..., None] * tints)
    h = np.clip(edge * 25, 0, 1) ** 0.5 + 0.2 * n
    save(out, name, albedo, h, np.where(is_mortar, 0.95, 0.8), 14)


def brick(out, name, base="#8e4a36", mortar="#c9bfae", course_m=0.0667, brick_m=0.2032, tile_m=1.0,
          header_every=6, seed=4):
    """Common bond brick: stretcher courses with a header course every Nth."""
    r = rng(seed)
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    ci = np.floor(y / course_m).astype(int)
    unit = np.where(ci % header_every == 0, brick_m / 2, brick_m)
    off = np.where(ci % 2 == 0, 0.0, unit / 2)
    bx = (x + off) / unit
    bi = np.floor(bx).astype(int)
    tx, ty = bx % 1.0, (y / course_m) % 1.0
    mj = 0.01 / unit / 1.0
    joint = (tx < mj) | (ty < 0.15)
    key = (bi * 7919 + ci * 104729) % 997
    bv = r.uniform(0.75, 1.15, 997)[key]
    burn = r.uniform(0, 1, 997)[key] > 0.9
    n = fbm(seed + 1, 30)
    brickc = col(base)[None, None, :] * (bv * (0.85 + 0.25 * n))[..., None]
    brickc = np.where(burn[..., None], brickc * 0.6, brickc)
    albedo = np.where(joint[..., None], col(mortar)[None, None, :] * (0.9 + 0.1 * n[..., None]), brickc)
    h = np.where(joint, 0.0, 1.0) + 0.1 * n
    save(out, name, albedo, h, np.where(joint, 0.95, 0.85), 10)


def planks(out, name, base="#a67c4e", board_m=0.1397, tile_m=2.0, worn=0.3, seed=5, painted=None):
    """Tongue-and-groove pine floor: boards along x, random end joints, grain, traffic wear."""
    r = rng(seed)
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    bi = np.floor(y / board_m).astype(int)
    nb = int(round(tile_m / board_m)) + 1
    lens = r.uniform(0.9, 2.4, nb)
    offs = r.uniform(0, 2, nb)
    seg = np.floor((x + offs[bi % nb]) / lens[bi % nb]).astype(int)
    key = (bi * 131 + seg * 17) % 499
    bv = r.uniform(0.78, 1.12, 499)[key]
    t = (y / board_m) % 1.0
    endpos = ((x + offs[bi % nb]) / lens[bi % nb]) % 1.0
    seam = (t < 0.035) | (endpos < 0.004)
    grain = stretch_noise(seed + 1, 2, 120)
    rings = 0.5 + 0.5 * np.sin(grain * 40 + key * 0.3)
    wear = fbm(seed + 2, 200) * worn
    c = col(painted) if painted else col(base)
    v = bv * (0.82 + 0.18 * rings) * (1 + 0.25 * wear)
    albedo = c[None, None, :] * v[..., None]
    albedo = np.where(seam[..., None], albedo * 0.45, albedo)
    h = np.where(seam, 0.0, 1.0) + 0.15 * rings
    save(out, name, albedo, h, 0.55 + 0.25 * wear + 0.1 * rings, 5)


def plaster(out, name, base="#ece6d8", seed=6, stains=0.15):
    n = fbm(seed, 25)
    s = np.clip(fbm(seed + 1, 300) - 0.55, 0, 1) * stains * 4
    albedo = col(base)[None, None, :] * (0.95 + 0.05 * n[..., None]) * (1 - 0.3 * s[..., None])
    save(out, name, albedo, n * 0.2, 0.9 + 0.05 * n, 2)


def beadboard(out, name, base="#8a6a44", board_m=0.0889, tile_m=1.0, seed=7, vertical=True):
    """Beaded tongue-and-groove wainscot."""
    u = (np.arange(N) + 0.5)[None, :] / N * tile_m
    t = (u / board_m) % 1.0
    bead = np.exp(-((t - 0.5) / 0.03) ** 2)
    joint = t < 0.03
    grain = stretch_noise(seed, 120, 2) if vertical else stretch_noise(seed, 2, 120)
    v = (0.85 + 0.2 * grain) * (1 - 0.35 * bead) * np.where(joint, 0.5, 1.0)
    albedo = col(base)[None, None, :] * v[..., None]
    h = np.where(joint, 0.0, 1.0) - 0.4 * bead + 0.05 * grain
    if not vertical:
        albedo, h = albedo.transpose(1, 0, 2), h.T
    save(out, name, np.broadcast_to(albedo, (N, N, 3)), np.broadcast_to(h, (N, N)), 0.45 + 0.1 * grain, 6)


def paint_flat(out, name, base, rough=0.5, seed=8, var=0.04):
    n = fbm(seed, 40)
    albedo = col(base)[None, None, :] * (1 - var + var * 2 * n[..., None])
    save(out, name, albedo, n * 0.1, rough + 0.05 * n, 1)


def wood_varnish(out, name, base="#6b4428", seed=9):
    grain = stretch_noise(seed, 2, 160)
    rings = 0.5 + 0.5 * np.sin(grain * 55)
    albedo = col(base)[None, None, :] * (0.75 + 0.3 * rings[..., None])
    save(out, name, albedo, rings * 0.2, 0.35 + 0.1 * rings, 2)


def cast_iron(out, name, seed=10):
    n = fbm(seed, 20)
    rust = np.clip(fbm(seed + 1, 60) - 0.6, 0, 1) * 2
    albedo = col("#2a2a2a")[None, None, :] * (0.8 + 0.4 * n[..., None]) * (1 - rust[..., None]) + \
        rust[..., None] * col("#6e3b22")[None, None, :]
    save(out, name, albedo, n * 0.3, 0.6 + 0.3 * rust, 3)


def checker_lino(out, name, a="#e8e2d0", b_="#2f3a4a", tile=0.2286, tile_m=0.9144, seed=22):
    """9-inch linoleum/VCT checkerboard with scuffing."""
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    c = ((np.floor(x / tile) + np.floor(y / tile)) % 2).astype(bool)
    n = fbm(seed, 50)
    sc = np.clip(fbm(seed + 1, 300) - 0.6, 0, 1) * 1.5
    joint = ((x / tile) % 1 < 0.006) | ((y / tile) % 1 < 0.006)
    albedo = np.where(c[..., None], col(b_)[None, None, :], col(a)[None, None, :]) * (0.92 + 0.1 * n[..., None]) * (1 - 0.25 * sc[..., None])
    albedo = np.where(joint[..., None], albedo * 0.7, albedo)
    save(out, name, albedo, np.where(joint, 0, 1.0), 0.35 + 0.3 * sc, 2)


def dirt(out, name, base="#5e4a36", seed=23):
    n = fbm(seed, 30)
    pebbles = np.clip(fbm(seed + 1, 400) - 0.7, 0, 1) * 3
    albedo = col(base)[None, None, :] * (0.75 + 0.4 * n[..., None]) + pebbles[..., None] * 0.15
    save(out, name, albedo, n + pebbles * 0.5, 0.95 - 0.1 * pebbles, 5)


def vinyl_siding(out, name, base="#f2f2ee", exposure_m=0.1016, tile_m=1.0, seed=70):
    """Double-4" vinyl lap siding: crisp, uniform, faint woodgrain emboss, no paint wear."""
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    t = (y / exposure_m) % 1.0
    grain = stretch_noise(seed, 2, 80)
    shadow = np.clip((t - 0.95) / 0.05, 0, 1)
    v = 1.0 - 0.3 * shadow - 0.03 * grain + 0 * y
    albedo = np.broadcast_to(tint(col(base), v), (N, N, 3))
    save(out, name, albedo, np.broadcast_to(t * 0.5 - shadow + 0.03 * grain, (N, N)), np.full((N, N), 0.45), 8)


def asphalt_shingles(out, name, base="#3b3a38", exposure_m=0.127, tab_m=0.3048, tile_m=1.0, seed=71):
    """3-tab asphalt shingles with granule noise and tab keyways."""
    r = rng(seed)
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    ci = np.floor(y / exposure_m).astype(int)
    t = (y / exposure_m) % 1.0
    off = (ci % 2) * tab_m / 2
    key = (((x + off) / tab_m) % 1.0) < 0.02
    tabv = r.uniform(0.85, 1.12, 997)[((np.floor((x + off) / tab_m).astype(int) * 31 + ci * 17) % 997)]
    gran = rng(seed + 1).random((N, N))
    v = tabv * (0.85 + 0.25 * gran) * np.where(key & (t > 0.35), 0.4, 1.0) * (1 - 0.35 * np.clip((t - 0.9) / 0.1, 0, 1))
    albedo = tint(col(base), v)
    h = t * 0.5 + 0.2 * gran - np.where(key & (t > 0.35), 0.5, 0)
    save(out, name, albedo, h, 0.9 + 0.05 * gran, 6)


def acoustic_tile(out, name, base="#ecebe6", tile=0.6096, tile_m=1.2192, seed=72):
    """2x4 lay-in ceiling tile with fissured pattern and a white T-bar grid."""
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    grid = ((x / tile) % 1 < 0.02) | ((y / (tile * 2)) % 1 < 0.01)
    fis = np.clip(fbm(seed, 180) - 0.55, 0, 1) * 3
    albedo = col(base)[None, None, :] * (1 - 0.35 * fis[..., None])
    albedo = np.where(grid[..., None], col("#f7f7f5")[None, None, :], albedo)
    save(out, name, albedo, np.where(grid, 1.0, 0.6 - fis * 0.3), np.where(grid, 0.4, 0.95), 4)


def vct(out, name, base="#cbbfa6", fleck="#8c8070", tile=0.3048, tile_m=1.2192, seed=73):
    """12" vinyl composition tile with directional flecks."""
    r = rng(seed)
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    joint = ((x / tile) % 1 < 0.004) | ((y / tile) % 1 < 0.004)
    tv = r.uniform(0.94, 1.06, 99)[(np.floor(x / tile) * 7 + np.floor(y / tile) * 13).astype(int) % 99]
    fl = stretch_noise(seed + 1, 30, 3) > 0.68
    albedo = np.where(fl[..., None], col(fleck)[None, None, :], col(base)[None, None, :]) * tv[..., None]
    albedo = np.where(joint[..., None], albedo * 0.8, albedo)
    save(out, name, albedo, np.where(joint, 0, 1.0), 0.35 + 0.1 * fl, 2)


def concrete(out, name, base="#a7a49c", seed=74):
    n = fbm(seed, 60)
    pits = np.clip(fbm(seed + 1, 500) - 0.72, 0, 1) * 3
    albedo = col(base)[None, None, :] * (0.88 + 0.2 * n[..., None]) * (1 - 0.3 * pits[..., None])
    save(out, name, albedo, n * 0.3 - pits * 0.3, 0.85 + 0.1 * n, 3)


def wallpaper(out, name, ground="#e8dfc8", ink="#9a7f62", stripe="#d9cdb0", repeat_m=0.4572, tile_m=0.9144, seed=100,
              motif="floral"):
    """Period wallpaper: stripes + a repeating sprig/floral motif (drawn with Gaussian blobs)."""
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    base = np.broadcast_to(col(ground)[None, None, :], (N, N, 3)).copy()
    st = (((x / (repeat_m / 2)) % 1.0) < 0.12)
    base = np.where(np.broadcast_to(st[..., None], (N, N, 3)), col(stripe)[None, None, :], base)
    ink_c = col(ink)
    m = np.zeros((N, N))
    rep = repeat_m
    for (cx, cy, sc) in ((0.25, 0.25, 1.0), (0.75, 0.75, 1.0)):
        for (dx, dy, r) in ((0, 0, 0.05), (0.07, 0.03, 0.03), (-0.06, 0.04, 0.03), (0.0, -0.08, 0.025), (0.03, 0.09, 0.02)):
            px, py = (cx + dx * sc) * rep, (cy + dy * sc) * rep
            dxv = ((x - px + rep / 2) % rep) - rep / 2
            dyv = ((y - py + rep / 2) % rep) - rep / 2
            m = np.maximum(m, np.exp(-((dxv ** 2 + dyv ** 2) / (r * rep) ** 2)))
    if motif == "none":
        m *= 0
    age = fbm(seed, 40)
    albedo = base * (1 - 0.6 * m[..., None]) + ink_c[None, None, :] * 0.6 * m[..., None]
    albedo *= (0.93 + 0.08 * age[..., None])
    save(out, name, albedo, m * 0.1, np.full((N, N), 0.8), 1)


def hex_tile(out, name, a="#f2f1ec", grout="#b9b6ad", size=0.0254, tile_m=0.3048, seed=101):
    """1" hexagonal mosaic floor tile (period bathrooms)."""
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m / size
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m / size
    # axial hex grid distance
    q = x * 2 / 3
    r_ = -x / 3 + np.sqrt(3) / 3 * y
    # cube round
    cx_, cz = q, r_
    cy_ = -cx_ - cz
    rx_, ry_, rz = np.round(cx_), np.round(cy_), np.round(cz)
    dx, dy, dz = np.abs(rx_ - cx_), np.abs(ry_ - cy_), np.abs(rz - cz)
    d = np.maximum(np.maximum(dx, dy), dz)
    grout_m = d > 0.42
    n = fbm(seed, 50)
    albedo = np.where(grout_m[..., None], col(grout)[None, None, :], col(a)[None, None, :] * (0.95 + 0.05 * n[..., None]))
    save(out, name, albedo, np.where(grout_m, 0.0, 1.0), np.where(grout_m, 0.9, 0.2), 3)


def asbestos_shingle(out, name, base="#d9d6cc", course_m=0.2921, width_m=0.6096, tile_m=1.2192, seed=130):
    """Asbestos-cement siding shingles (12"x24", ~11.5" exposure): wavy butt edge, stipple, staggered."""
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    ci = np.floor(y / course_m).astype(int)
    off = (ci % 2) * width_m / 2
    t = (y / course_m) % 1.0
    wave = 0.02 * np.sin((x + off) / width_m * 2 * np.pi * 6)
    butt = np.clip((t + wave - 0.94) / 0.06, 0, 1)
    joint = (((x + off) / width_m) % 1.0) < 0.004
    stip = rng(seed).random((N, N))
    tv = rng(seed + 1).uniform(0.92, 1.05, 997)[(np.floor((x + off) / width_m).astype(int) * 13 + ci * 7) % 997]
    v = tv * (0.9 + 0.12 * stip) * (1 - 0.35 * butt) * np.where(joint, 0.6, 1.0)
    albedo = tint(col(base), v)
    save(out, name, albedo, t * 0.4 - butt * 0.4 + 0.1 * stip - joint * 0.3, 0.8 + 0.1 * stip, 7)


def corrugated(out, name, base="#9ea3a4", pitch_m=0.0762, sheet_w=0.66, sheet_h=2.44, tile_m=2.44, rust=0.35, seed=200,
               vertical=True):
    """Galvanised corrugated sheet: sine corrugation, lapped sheet seams, nail rows, rust run-off."""
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    wave = np.sin(x / pitch_m * 2 * np.pi)
    seam_v = ((x / sheet_w) % 1.0) < 0.012
    seam_h = ((y / sheet_h) % 1.0) < 0.01
    nails = (((x / pitch_m) % 1.0) < 0.12) & ((((y / (sheet_h / 4)) % 1.0) < 0.012))
    spang = fbm(seed, 30)
    streak = stretch_noise(seed + 1, 3, 200).T if False else stretch_noise(seed + 1, 200, 3)
    rs = np.clip(streak - (1 - rust), 0, 1) * 2.5 + np.clip(fbm(seed + 2, 120) - 0.75, 0, 1) * 2 * rust
    rs = np.clip(rs, 0, 1)
    v = (0.82 + 0.18 * (0.5 + 0.5 * wave)) * (0.9 + 0.15 * spang)
    albedo = tint(col(base), v) * (1 - rs[..., None]) + rs[..., None] * col("#7a4a2a")[None, None, :] * v[..., None]
    albedo = np.where((seam_v | seam_h)[..., None], albedo * 0.7, albedo)
    albedo = np.where(nails[..., None], albedo * 0.5, albedo)
    h = 0.5 + 0.5 * wave
    if not vertical:
        albedo, h, rs = albedo.transpose(1, 0, 2), h.T, rs.T
    save(out, name, albedo, h, 0.45 + 0.4 * rs, 14)


def ashlar(out, name, base="#a89a82", mortar="#8d8578", tile_m=2.0, seed=240):
    """Random-coursed rock-faced ashlar (railroad arch masonry)."""
    r = rng(seed)
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    heights = []
    t = 0.0
    while t < tile_m - 0.1:
        h = r.choice([0.3, 0.4, 0.5])
        heights.append((t, min(tile_m, t + h)))
        t += h
    stone_id = np.zeros((N, N), int)
    joint = np.zeros((N, N), bool)
    sid = 0
    for (c0, c1) in heights:
        rows = (y[:, 0] >= c0) & (y[:, 0] < c1)
        edges, s_ = [0.0], r.uniform(0.0, 0.3)
        while s_ < tile_m:
            edges.append(s_)
            s_ += r.uniform(0.5, 1.2)
        e = np.array(edges)
        idx = np.searchsorted(e, x[0], side="right") + sid
        sid += len(e) + 2
        stone_id[rows, :] = idx[None, :]
        dist = np.min(np.abs(((x[0][None, :] - e[:, None]) + tile_m / 2) % tile_m - tile_m / 2), 0)
        joint[rows, :] = (dist < 0.012)[None, :]
        joint[rows & ((np.abs(y[:, 0] - c0) < 0.012) | (np.abs(y[:, 0] - c1) < 0.012)), :] = True
    sv = r.uniform(0.8, 1.15, sid + 10)[stone_id]
    rock = fbm(seed + 1, 25)
    albedo = np.where(joint[..., None], col(mortar)[None, None, :], col(base)[None, None, :] * (sv * (0.8 + 0.35 * rock))[..., None])
    h = np.where(joint, 0.0, 0.6 + 0.4 * rock)
    save(out, name, albedo, h, np.where(joint, 0.95, 0.85), 16)


def clay_tile(out, name, base="#b5583a", tile_w=0.22, course_m=0.33, tile_m=1.32, seed=250):
    """Mission / Spanish clay barrel tile (the California shore's roofs, 2026-10-07): pans and caps alternating across the
    roof, courses down it, every tile its own fired colour (terracotta, some darker, a few lighter), a shadow under each
    course's lower edge."""
    r = rng(seed)
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    ncol = int(round(tile_m / tile_w))
    w = tile_m / ncol
    col_i = np.floor(x / w).astype(int) % ncol
    fx = (x / w) % 1.0
    cap = (col_i % 2 == 0)
    # a cap is convex (high in its middle), a pan concave (low in its middle) and sits a little lower
    prof = np.where(cap, np.sin(np.pi * fx) * 1.0, 0.35 - 0.3 * np.sin(np.pi * fx))
    course = np.floor(y / course_m).astype(int)
    fy = (y / course_m) % 1.0
    # each course's tile is a touch fatter at its lower (exposed) end; a dark lap shadow at the lower edge
    taper = 0.85 + 0.15 * fy
    h = prof * taper
    lap = np.clip((fy - 0.9) / 0.1, 0, 1)
    h = h - 0.35 * lap
    tid = (course * 97 + np.floor(x / w).astype(int)) % 4096
    tv = r.uniform(0.82, 1.12, 4096)[tid]
    dark = r.random(4096)[tid] < 0.08
    grain = fbm(seed + 1, 60)
    c = col(base)[None, None, :] * (tv * (0.9 + 0.2 * grain))[..., None]
    c = np.where(dark[..., None], c * 0.72, c)
    c = c * (1.0 - 0.5 * lap[..., None]) * (0.55 + 0.5 * prof[..., None])        # (the barrel: lit crowns, shaded troughs)
    save(out, name, np.clip(c, 0, 1), np.clip(h, 0, 1), np.clip(0.75 + 0.15 * grain, 0, 1), 14)


def granite(out, name, base="#9c958e", mortar="#7d7872", tile_m=2.0, seed=251, pink=0.0):
    """Coursed granite (the North Sea's stone: wharves, customs house, foundations, sea walls): rock-faced ashlar with the
    stone's black-and-white speckle and a faint pink feldspar cast."""
    ashlar(out, name, base=base, mortar=mortar, tile_m=tile_m, seed=seed)
    a = np.asarray(Image.open(os.path.join(out, name + "_albedo.png"))).astype(np.float32) / 255.0
    r = rng(seed + 7)
    sp = r.random((N, N))
    a = np.where((sp < 0.05)[..., None], a * 0.45, a)
    a = np.where((sp > 0.96)[..., None], np.minimum(1, a * 1.35), a)
    if pink:
        a = a * (1.0 + pink * np.array([0.08, -0.02, -0.03]))[None, None, :]
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out, name + "_albedo.png"))


def gravel(out, name, base="#7c7870", seed=241, size=35):
    n1 = fbm(seed, size, octaves=2)
    n2 = rng(seed + 1).random((N, N))
    pebble = np.clip(fbm(seed + 2, size * 2) - 0.45, 0, 1) * 2
    albedo = col(base)[None, None, :] * (0.7 + 0.35 * n1[..., None] + 0.15 * n2[..., None])
    save(out, name, albedo, pebble + 0.2 * n2, 0.9 + 0.05 * n2, 10)


def asphalt(out, name, base="#3c3b3a", seed=242, patches=0.3):
    n = rng(seed).random((N, N))
    f = fbm(seed + 1, 80)
    patch = np.clip(fbm(seed + 2, 250) - (1 - patches), 0, 1) * 2
    cracks = np.clip(stretch_noise(seed + 3, 200, 2) - 0.93, 0, 1) * 10
    albedo = col(base)[None, None, :] * (0.85 + 0.2 * n[..., None] + 0.15 * f[..., None]) * (1 - 0.25 * patch[..., None]) * (1 - 0.5 * np.clip(cracks, 0, 1)[..., None])
    save(out, name, albedo, n * 0.2 - cracks * 0.3, 0.88 + 0.05 * n, 4)


def grass(out, name, base="#4f6b2c", seed=270):
    n1 = fbm(seed, 60)
    n2 = rng(seed + 1).random((N, N))
    blades = stretch_noise(seed + 2, 1.5, 12)
    dry = np.clip(fbm(seed + 3, 200) - 0.6, 0, 1) * 1.5
    albedo = col(base)[None, None, :] * (0.75 + 0.35 * n1[..., None] + 0.12 * n2[..., None] + 0.1 * blades[..., None])
    albedo = albedo * (1 - dry[..., None]) + dry[..., None] * col("#8a8045")[None, None, :]
    save(out, name, albedo, blades * 0.5 + n2 * 0.2, np.full((N, N), 0.95), 4)



def bedrock(out, name, tile_m=12.0, seed=610):
    """Sedimentary cliff face (the station end-wall bluffs): horizontal strata 0.15-1.6 m thick --
    buff limestone, tan sandstone, thin dark shale partings -- with bedding-plane cracks, vertical
    joints that step from bed to bed, ledge lips and weathering.  Periodic both ways (tile_m)."""
    r = rng(seed)
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    # beds from the top down until the tile is full (the last one absorbs the remainder)
    beds, t = [], 0.0
    while t < tile_m - 0.2:
        kind = r.choice(["lime", "lime", "sand", "shale"], p=[0.35, 0.25, 0.25, 0.15])
        th = {"lime": r.uniform(0.4, 1.6), "sand": r.uniform(0.3, 1.2), "shale": r.uniform(0.12, 0.35)}[kind]
        beds.append((t, min(tile_m, t + th), kind))
        t += th
    base_col = {"lime": col("#b9ae95"), "sand": col("#a88a66"), "shale": col("#5f5a52")}
    albedo = np.zeros((N, N, 3))
    h = np.zeros((N, N))
    rough = np.zeros((N, N))
    wobble = (fbm(seed + 1, 120, octaves=3) - 0.5) * 0.12            # beds aren't ruler-straight
    yy = y + wobble
    grain = fbm(seed + 2, 18)
    pits = np.clip(fbm(seed + 3, 40) - 0.55, 0, 1) * 2
    for k, (c0, c1, kind) in enumerate(beds):
        m = (yy >= c0) & (yy < c1)
        tone = r.uniform(0.85, 1.12)
        v = (yy - c0) / max(1e-3, c1 - c0)                              # 0 at the bed's top, 1 at its base
        # each bed is proud at its base (a small ledge lip) and recessed under the next bed's lip
        prof = {"lime": 0.75 + 0.25 * v, "sand": 0.6 + 0.3 * v, "shale": 0.25 + 0.1 * v}[kind]
        albedo[m] = (base_col[kind] * tone)[None, :] * (0.78 + 0.3 * grain[m])[:, None]
        h[m] = prof[m] + 0.15 * grain[m] - 0.25 * pits[m]
        rough[m] = 0.9 if kind == "shale" else 0.82
    # vertical joints: sparse (2-6 m), wandering, fading in and out; each bed has its own set, so
    # they step from bed to bed instead of running through like mortar
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    xw = x + (fbm(seed + 6, 60, octaves=3) - 0.5) * 0.5                # wander
    fade = fbm(seed + 7, 90)
    jdist = np.full((N, N), 9.0)
    for (c0, c1, kind) in beds:
        if kind == "shale" or r.random() < 0.5:
            continue
        rows = (yy[:, 0] >= c0) & (yy[:, 0] < c1)
        xs, s_ = [], r.uniform(0, 3.0)
        while s_ < tile_m:
            xs.append(s_)
            s_ += r.uniform(3.0, 9.0)
        e = np.array(xs)
        d = np.min(np.abs(((xw[rows, :][None] - e[:, None, None]) + tile_m / 2) % tile_m - tile_m / 2), 0)
        jdist[rows, :] = np.minimum(jdist[rows, :], d)
    jw = 0.02 + 0.05 * fade                                          # joint half-width varies 2-7 cm
    joint = np.clip(1 - jdist / jw, 0, 1) * np.clip(fade * 2 - 0.3, 0, 1)
    round_j = np.clip(1 - jdist / (jw + 0.12), 0, 1)                    # rounded, darker lips beside it
    # bedding planes: darkness and width vary along the bed
    bdist = np.full((N, N), 9.0)
    for (c0, c1, kind) in beds:
        bdist = np.minimum(bdist, np.abs(yy - c0))
    bw = 0.015 + 0.05 * fbm(seed + 8, 70)
    bed_line = np.clip(1 - bdist / bw, 0, 1) * (0.4 + 0.6 * fbm(seed + 9, 50))
    round_b = np.clip(1 - bdist / (bw + 0.1), 0, 1)
    dark = np.clip(np.maximum(joint, bed_line), 0, 1)
    albedo = albedo * (1 - 0.3 * dark[..., None]) * (1 - 0.1 * np.maximum(round_j, round_b)[..., None])
    h = h - 0.4 * dark - 0.15 * np.maximum(round_j, round_b)
    # tonal banding within the beds (fine laminae), then large-scale mottling, weathering streaks
    # down the face, lichen on the proud limestone
    lam = stretch_noise(seed + 11, 25, 1.5)
    albedo = albedo * (0.88 + 0.22 * lam[..., None])
    mottle = fbm(seed + 10, 350, octaves=3)
    albedo = albedo * (0.84 + 0.3 * mottle[..., None])
    streak = np.clip(stretch_noise(seed + 4, 3, 90) - 0.6, 0, 1) * 1.5
    lichen = np.clip(fbm(seed + 5, 60) - 0.7, 0, 1) * 2.5
    albedo = albedo * (1 - 0.25 * streak[..., None])
    albedo = albedo * (1 - lichen[..., None]) + lichen[..., None] * col("#8e9a78")[None, None, :]
    save(out, name, albedo, h, rough, 22)


def scree(out, name, tile_m=4.0, seed=620):
    """Talus at the cliff foot: broken limestone and sandstone blocks in fine rubble."""
    n = rng(seed).random((N, N))
    blocks = fbm(seed + 1, 22, octaves=2)
    cells = np.clip(blocks - 0.52, 0, 1) * 3
    tone = np.where(fbm(seed + 2, 90) > 0.5, 1.0, 0.0)
    base = col("#a99d86")[None, None, :] * (1 - tone[..., None]) + col("#9a8266")[None, None, :] * tone[..., None]
    albedo = base * (0.62 + 0.4 * cells[..., None] + 0.12 * n[..., None])
    save(out, name, albedo, cells + 0.15 * n, 0.92 + 0.05 * n, 14)


# ------------------------------------------------------------------ library-only recipes
def carpet(out, name, base="#8a8478", seed=300, loop=0.5):
    n = fbm(seed, 300) * 0.6 + fbm(seed + 1, 60) * 0.4
    albedo = col(base)[None, None, :] * (0.85 + 0.25 * n[..., None])
    save(out, name, albedo, n * loop, np.full((N, N), 0.95), 3)


def board_batten(out, name, base="#f2f2f2", board_m=0.3048, batten_m=0.0635, tile_m=1.2192, seed=301, weather=0.25):
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    t = (x / board_m) % 1.0
    bat = t < batten_m / board_m
    grain = stretch_noise(seed, 120, 2)
    wear = fbm(seed + 1, 80) * weather
    v = (0.9 + 0.1 * grain) * np.where(bat, 1.0, 0.93) * (1 - 0.3 * wear)
    albedo = col(base)[None, None, :] * v[..., None]
    edge = np.exp(-((t - batten_m / board_m) / 0.01) ** 2) + np.exp(-(t / 0.01) ** 2)
    h = np.where(bat, 1.0, 0.0) + 0.05 * grain
    albedo = albedo * (1 - 0.3 * edge[..., None])
    save(out, name, np.broadcast_to(albedo, (N, N, 3)), np.broadcast_to(h, (N, N)), 0.6 + 0.2 * wear, 6)


def concrete_block(out, name, base="#a9a69e", mortar="#8f8c84", tile_m=1.2192, seed=302):
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    bh, bw = 0.2032, 0.4064
    row = np.floor(y / bh)
    tx = ((x + (row % 2) * bw / 2) / bw) % 1.0
    ty = (y / bh) % 1.0
    joint = (tx < 0.025) | (ty < 0.05)
    n = fbm(seed, 200)
    albedo = np.where(joint[..., None], col(mortar)[None, None, :], col(base)[None, None, :] * (0.88 + 0.2 * n[..., None]))
    h = np.where(joint, 0.0, 1.0) + 0.1 * n
    save(out, name, albedo, h, 0.9 + 0.05 * n, 5)


def stucco(out, name, base="#f0ede6", seed=303):
    n = fbm(seed, 350) * 0.7 + fbm(seed + 1, 40) * 0.3
    albedo = col(base)[None, None, :] * (0.9 + 0.12 * n[..., None])
    save(out, name, albedo, n, 0.9 + 0.05 * n, 8)


def log_wall(out, name, base="#7a5a3a", chink="#cfc6b0", log_m=0.3, tile_m=1.2, seed=304):
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    t = (y / log_m) % 1.0
    round_ = np.sqrt(np.clip(1 - (2 * t - 1) ** 2, 0, 1))
    grain = stretch_noise(seed, 2, 90)
    ch = round_ < 0.35
    albedo = np.where(ch[..., None], col(chink)[None, None, :],
                      col(base)[None, None, :] * (0.6 + 0.4 * round_[..., None]) * (0.85 + 0.2 * grain[..., None]))
    save(out, name, np.broadcast_to(albedo, (N, N, 3)), np.broadcast_to(round_ + 0.05 * grain, (N, N)), np.full((N, N), 0.8), 10)


def tin_ceiling(out, name, base="#e9e6de", tile_m=0.6096, seed=305):
    y = (np.arange(N) + 0.5)[:, None] / N * tile_m
    x = (np.arange(N) + 0.5)[None, :] / N * tile_m
    u, v = (x / (tile_m / 2)) % 1.0, (y / (tile_m / 2)) % 1.0
    d = np.maximum(np.abs(u - 0.5), np.abs(v - 0.5))
    ring = np.exp(-((d - 0.42) / 0.02) ** 2) + 0.6 * np.exp(-((d - 0.3) / 0.02) ** 2)
    dome = np.exp(-(((u - 0.5) ** 2 + (v - 0.5) ** 2) / 0.02))
    h = ring + dome
    n = fbm(seed, 50)
    albedo = col(base)[None, None, :] * (0.9 + 0.08 * n[..., None]) * (1 - 0.15 * ring[..., None])
    save(out, name, albedo, h, 0.4 + 0.1 * n, 8)


def upholstery(out, name, base="#9a8e7c", seed=306, weave_m=0.004):
    y = (np.arange(N) + 0.5)[:, None] / N * 0.5
    x = (np.arange(N) + 0.5)[None, :] / N * 0.5
    w = np.sin(x / weave_m * np.pi) * np.sin(y / weave_m * np.pi)
    n = fbm(seed, 80)
    albedo = col(base)[None, None, :] * (0.85 + 0.1 * w[..., None] + 0.1 * n[..., None])
    save(out, name, albedo, 0.5 + 0.5 * w, np.full((N, N), 0.95), 2)

RECIPES = {
    # shared library for the catalog builders: neutral (near-white) paintable surfaces are tinted
    # per building (Building.mat(tint=...)); natural finishes carry their own colour
    "lib": [
        (clapboard, "clapboard", dict(paint="#f2f2f2", seed=401, weather=0.25)),
        (clapboard, "clapboard_wide", dict(paint="#f2f2f2", exposure_m=0.1524, seed=402, weather=0.2)),
        (clapboard, "drop_siding", dict(paint="#f2f2f2", exposure_m=0.1397, seed=403, weather=0.3)),
        (vinyl_siding, "vinyl", dict(base="#f4f4f4", seed=404)),
        (vinyl_siding, "aluminum", dict(base="#f4f4f4", exposure_m=0.2032, seed=405)),
        (cedar_shingles, "wall_shingle", dict(base="#e8e8e8", seed=406)),
        (asbestos_shingle, "asbestos", dict(base="#f0f0f0", seed=407)),
        (board_batten, "board_batten", dict(seed=408)),
        (stucco, "stucco", dict(seed=409)),
        (paint_flat, "paint", dict(base="#f4f4f4", rough=0.5, seed=410)),
        (paint_flat, "paint_gloss", dict(base="#f4f4f4", rough=0.25, seed=411)),
        (plaster, "plaster", dict(base="#f4f2ee", seed=412, stains=0.06)),
        (paint_flat, "drywall", dict(base="#f6f6f4", rough=0.8, seed=413, var=0.015)),
        (beadboard, "beadboard", dict(base="#f0f0f0", seed=414)),
        (asphalt_shingles, "roof_asphalt", dict(base="#9a9a98", seed=415)),
        (cedar_shingles, "roof_wood", dict(base="#8a7c6a", seed=416)),
        (cedar_shingles, "roof_slate", dict(base="#4a4e55", exposure_m=0.2032, seed=417)),
        (corrugated, "metal_roof", dict(base="#dcdcdc", pitch_m=0.4572, rust=0.1, seed=418)),
        (corrugated, "corrugated", dict(base="#b8bcbd", rust=0.3, seed=419)),
        (corrugated, "corrugated_rusty", dict(base="#9c9a94", rust=0.8, seed=420)),
        (brick, "brick_red", dict(base="#8e4a36", seed=421)),
        (brick, "brick_brown", dict(base="#6e4634", mortar="#b9ae9c", seed=422)),
        (brick, "brick_buff", dict(base="#c9aa7c", mortar="#d8cfbf", seed=423)),
        (brick, "brick_cream", dict(base="#ddd0ae", mortar="#e6dfcf", seed=424)),
        (brick, "brick_dark", dict(base="#4e3028", mortar="#9a9080", seed=425)),
        (brick, "brick_common", dict(base="#9c5a42", mortar="#b0a590", header_every=6, seed=426)),
        (brick, "brick_painted", dict(base="#e6e2da", mortar="#dedad2", seed=427)),
        (fieldstone, "fieldstone", dict(seed=428)),
        (ashlar, "limestone", dict(base="#c2b69a", mortar="#a89d86", seed=429)),
        (ashlar, "sandstone", dict(base="#a8805e", mortar="#8e7058", seed=430)),
        (clay_tile, "roof_clay", dict(seed=450)),
        (clay_tile, "roof_clay_old", dict(base="#9c4a34", seed=451)),
        (granite, "granite", dict(seed=452)),
        (granite, "granite_pink", dict(base="#a8968c", seed=453, pink=1.0)),
        (concrete, "concrete", dict(seed=431)),
        (concrete_block, "block", dict(seed=432)),
        (log_wall, "logs", dict(seed=433)),
        (planks, "floor_oak", dict(base="#a57c52", seed=434)),
        (planks, "floor_pine", dict(base="#b98e5c", worn=0.45, seed=435)),
        (planks, "floor_maple", dict(base="#c9a57a", board_m=0.057, worn=0.2, seed=436)),
        (planks, "floor_painted", dict(base="#f0f0f0", painted="#e8e8e8", worn=0.5, seed=437)),
        (planks, "barn_board", dict(base="#f0f0f0", painted="#e8e8e8", board_m=0.254, worn=0.7, seed=438, tile_m=2.4)),
        (planks, "weathered_board", dict(base="#8a8278", board_m=0.254, worn=0.8, seed=439, tile_m=2.4)),
        (wood_varnish, "wood_dark", dict(base="#4e3220", seed=440)),
        (wood_varnish, "wood_medium", dict(base="#7a5234", seed=441)),
        (wood_varnish, "wood_light", dict(base="#b08a60", seed=442)),
        (checker_lino, "lino_checker", dict(seed=443)),
        (checker_lino, "lino_red", dict(a="#e8e2d0", b_="#8a2a22", seed=444)),
        (vct, "vct", dict(seed=445)),
        (vct, "terrazzo", dict(base="#d8d2c6", fleck="#6a6258", tile=1.2192, seed=446)),
        (hex_tile, "hex_tile", dict(seed=447)),
        (acoustic_tile, "acoustic", dict(seed=448)),
        (tin_ceiling, "tin_ceiling", dict(seed=449)),
        (carpet, "carpet", dict(base="#f0f0f0", seed=450)),
        (upholstery, "fabric", dict(base="#f0f0f0", seed=451)),
        (wallpaper, "wallpaper_floral", dict(seed=452)),
        (wallpaper, "wallpaper_blue", dict(ground="#d9dfe6", ink="#5a6f8c", stripe="#c9d2dc", seed=453)),
        (wallpaper, "wallpaper_green", dict(ground="#dfe3cf", ink="#6b7a4a", stripe="#cfd6bc", seed=454)),
        (wallpaper, "wallpaper_rose", dict(ground="#ecdcd6", ink="#9a5a5a", stripe="#e0cbc4", seed=455)),
        (wallpaper, "wallpaper_stripe", dict(ground="#e9e2cc", ink="#e9e2cc", stripe="#b89f7a", motif="none", seed=456)),
        (cast_iron, "cast_iron", dict(seed=457)),
        (paint_flat, "chrome", dict(base="#d8dadc", rough=0.15, seed=458, var=0.02)),
        (asphalt, "asphalt", dict(seed=459)),
        (gravel, "gravel", dict(seed=460)),
        (concrete, "sidewalk", dict(base="#b3aea3", seed=461)),
        (grass, "grass", dict(seed=462)),
        (dirt, "dirt", dict(seed=463)),
    ],
    "p-site": [
        (grass, "grass", dict(seed=271)),
        (asphalt, "asphalt", dict(seed=272, patches=0.4)),
        (gravel, "gravel_road", dict(base="#8f8672", seed=273, size=25)),
        (concrete, "sidewalk", dict(base="#b3aea3", seed=274)),
        (gravel, "ballast", dict(seed=275)),
        (planks, "ties", dict(base="#4d3f33", worn=0.6, seed=276, board_m=0.23, tile_m=2.6)),
        (wood_varnish, "bark", dict(base="#4a3a2c", seed=277)),
        (grass, "leaves", dict(base="#3f5a22", seed=278)),
    ],
    "cliff": [
        (bedrock, "bedrock", dict()),
        (scree, "scree", dict()),
    ],
    "p-bridges": [
        (paint_flat, "truss", dict(base="#5f6b63", rough=0.55, seed=251, var=0.08)),
        (concrete, "concrete", dict(base="#a9a498", seed=252)),
        (concrete, "concrete_old", dict(base="#9a968c", seed=253)),
        (ashlar, "ashlar", dict(seed=254)),
        (brick, "arch_brick", dict(base="#7e3f2c", seed=255)),
        (gravel, "ballast", dict(seed=256)),
        (asphalt, "asphalt", dict(seed=257)),
        (planks, "ties", dict(base="#4d3f33", worn=0.6, seed=258, board_m=0.23, tile_m=2.6)),
        (gravel, "creekbed", dict(base="#6d6453", seed=259, size=20)),
        (dirt, "bank", dict(base="#5a5236", seed=260)),
        (paint_flat, "guardrail", dict(base="#b7bbbd", rough=0.35, seed=261)),
        (grass, "grass", dict(seed=271)),      # p-site's grass (same seed), so crossings meet the site seamlessly
    ],
    "p-depot": [
        (asbestos_shingle, "siding", dict(base="#dcd6c3", seed=221)),
        (asphalt_shingles, "roof", dict(base="#4f4a44", seed=222)),
        (brick, "platform", dict(base="#8a4632", mortar="#a79d8b", course_m=0.1, brick_m=0.2032, header_every=99, seed=223)),
        (concrete, "found", dict(seed=224)),
        (paint_flat, "trim", dict(base="#e4dccb", rough=0.5, seed=225)),
        (paint_flat, "rr_red", dict(base="#7a2a1e", rough=0.5, seed=226)),
        (planks, "floor", dict(base="#8c6a45", worn=0.7, seed=227, board_m=0.0889)),
        (planks, "freight_floor", dict(base="#7a6552", worn=0.9, seed=228, board_m=0.1524)),
        (beadboard, "beadboard", dict(base="#a8875c", seed=229)),
        (plaster, "plaster", dict(base="#ded5bc", seed=230, stains=0.25)),
        (wood_varnish, "door", dict(base="#5b3d24", seed=231)),
        (wood_varnish, "furniture", dict(base="#6b4a2c", seed=232)),
        (cast_iron, "iron", dict(seed=233)),
    ],
    "p-elev": [
        (corrugated, "metal", dict(seed=201, rust=0.4)),
        (corrugated, "metal_roof", dict(base="#8f9596", seed=202, rust=0.5, vertical=True)),
        (planks, "driveway", dict(base="#7d6a52", worn=0.8, seed=203, board_m=0.2032, tile_m=3.0)),
        (planks, "wood_int", dict(base="#8a6a44", worn=0.4, seed=204, board_m=0.1524)),
        (concrete, "concrete", dict(seed=205)),
        (clapboard, "office_siding", dict(paint="#e8e4d6", exposure_m=0.1016, weather=0.5, seed=206)),
        (asphalt_shingles, "office_roof", dict(base="#4b4540", seed=207)),
        (paint_flat, "trim", dict(base="#e9e6de", rough=0.5, seed=208)),
        (paint_flat, "sign_panel", dict(base="#f0ede4", rough=0.6, seed=209)),
        (plaster, "office_wall", dict(base="#ddd6c2", seed=210, stains=0.3)),
        (planks, "office_floor", dict(base="#8e6b43", worn=0.7, seed=211, board_m=0.0889)),
        (wood_varnish, "door", dict(base="#54402c", seed=212)),
        (wood_varnish, "furniture", dict(base="#5a3f28", seed=213)),
        (cast_iron, "iron", dict(seed=214)),
    ],
    "p-house2": [
        (clapboard, "siding", dict(paint="#d8cfb4", exposure_m=0.0762, weather=0.25, seed=141)),
        (asphalt_shingles, "roof", dict(base="#4a3f36", seed=142)),
        (brick, "found", dict(base="#8b4a34", seed=143)),
        (paint_flat, "trim", dict(base="#f1ede2", rough=0.45, seed=144)),
        (planks, "floor", dict(base="#9a6d3c", worn=0.25, seed=145, board_m=0.0572)),
        (plaster, "plaster", dict(base="#e8e0cc", seed=146)),
        (checker_lino, "lino", dict(a="#f0ece0", b_="#20242c", seed=147)),
        (hex_tile, "hextile", dict(seed=148)),
        (planks, "porch", dict(base="#7d6b58", painted="#6f6a63", worn=0.5, seed=149, board_m=0.0889)),
        (wood_varnish, "door", dict(base="#5a3c22", seed=150)),
        (wood_varnish, "furniture", dict(base="#6a4428", seed=151)),
        (brick, "chimney", dict(base="#8a4833", seed=152)),
        (cast_iron, "iron", dict(seed=153)),
    ],
    "p-house3": [
        (clapboard, "siding", dict(paint="#eeeeea", exposure_m=0.1143, weather=0.15, seed=161)),
        (asphalt_shingles, "roof", dict(base="#3c3a39", seed=162)),
        (concrete, "found", dict(base="#b1ab9f", seed=163)),
        (paint_flat, "trim", dict(base="#f4f4f0", rough=0.45, seed=164)),
        (planks, "floor", dict(base="#b38a55", worn=0.2, seed=165, board_m=0.0572)),
        (plaster, "plaster", dict(base="#ece6d6", seed=166)),
        (vct, "lino", dict(base="#d6cfbd", fleck="#9a8f7a", seed=167)),
        (hex_tile, "hextile", dict(a="#ffffff", seed=168)),
        (planks, "porch", dict(base="#8b8f8e", painted="#6e7577", worn=0.4, seed=169, board_m=0.0889)),
        (wood_varnish, "door", dict(base="#4e3320", seed=170)),
        (wood_varnish, "furniture", dict(base="#7b5534", seed=171)),
        (brick, "chimney", dict(base="#93503a", seed=172)),
        (cast_iron, "iron", dict(seed=173)),
    ],
    "p-house4": [
        (asbestos_shingle, "siding", dict(base="#dcdad2", seed=181)),
        (asphalt_shingles, "roof", dict(base="#55504a", seed=182)),
        (brick, "found", dict(base="#8a4d38", seed=183)),
        (paint_flat, "trim", dict(base="#ecebe6", rough=0.45, seed=184)),
        (planks, "floor", dict(base="#a07a4a", worn=0.35, seed=185, board_m=0.0572)),
        (plaster, "plaster", dict(base="#e6e2d6", seed=186)),
        (vct, "lino", dict(base="#c9c3b0", fleck="#7c7563", seed=187)),
        (hex_tile, "hextile", dict(seed=188)),
        (concrete, "porch", dict(seed=189)),
        (wood_varnish, "door", dict(base="#6b4a2e", seed=190)),
        (wood_varnish, "furniture", dict(base="#5d4029", seed=191)),
        (brick, "chimney", dict(base="#8e4a36", seed=192)),
        (cast_iron, "iron", dict(seed=193)),
    ],
    "p-house1": [
        (clapboard, "siding", dict(paint="#f3f1e9", exposure_m=0.1016, weather=0.35, seed=111)),
        (cedar_shingles, "roof", dict(base="#6f675d", seed=112)),
        (fieldstone, "foundation", dict(base="#958d7e", seed=113)),
        (paint_flat, "trim", dict(base="#f6f4ee", rough=0.45, seed=114)),
        (paint_flat, "shutter", dict(base="#2d4632", rough=0.55, seed=115)),
        (planks, "floor", dict(base="#a8804f", worn=0.4, seed=116, board_m=0.1397)),
        (plaster, "plaster", dict(base="#efe9da", seed=117, stains=0.1)),
        (wallpaper, "wallpaper_a", dict(seed=118)),
        (wallpaper, "wallpaper_b", dict(ground="#dfe3d4", ink="#6f7f63", stripe="#d2d8c4", seed=119)),
        (wallpaper, "wallpaper_c", dict(ground="#e9dcd4", ink="#9a5f58", stripe="#dfcfc5", seed=120)),
        (checker_lino, "lino", dict(a="#e7e2d3", b_="#3f5a45", seed=121)),
        (hex_tile, "hextile", dict(seed=122)),
        (planks, "porch", dict(base="#8b8f8e", painted="#80878a", worn=0.5, seed=123, board_m=0.0889)),
        (wood_varnish, "door", dict(base="#6e4b2e", seed=124)),
        (wood_varnish, "furniture", dict(base="#5f3f26", seed=125)),
        (brick, "chimney", dict(base="#8e4b35", seed=126)),
        (cast_iron, "iron", dict(seed=127)),
    ],
    "p-po": [
        (brick, "brick", dict(base="#8f3f2c", mortar="#b9b1a4", course_m=0.0667, brick_m=0.2032, header_every=99, seed=81)),
        (vinyl_siding, "vinyl", dict(seed=82)),
        (asphalt_shingles, "roof", dict(seed=83)),
        (acoustic_tile, "ceiling", dict(seed=84)),
        (vct, "vct_lobby", dict(seed=85)),
        (vct, "vct_work", dict(base="#b9b8b2", fleck="#7d7d78", seed=86)),
        (concrete, "concrete", dict(seed=87)),
        (plaster, "drywall", dict(base="#e9e6dc", seed=88, stains=0.05)),
        (paint_flat, "aluminum", dict(base="#c9ccce", rough=0.35, seed=89)),
        (paint_flat, "trim", dict(base="#f4f4f0", rough=0.45, seed=90)),
        (wood_varnish, "counter", dict(base="#7a5634", seed=91)),
        (paint_flat, "steel_door", dict(base="#6a7a86", rough=0.45, seed=92)),
    ],
    "p-store": [
        (clapboard, "siding", dict(paint="#f1eee4", exposure_m=0.1016, weather=0.3, seed=51)),
        (clapboard, "siding_wing", dict(paint="#e9e6da", exposure_m=0.1143, weather=0.45, seed=52)),
        (cedar_shingles, "roof", dict(base="#71695f", seed=53)),
        (fieldstone, "foundation", dict(base="#8d8577", seed=54)),
        (paint_flat, "trim", dict(base="#f5f3ec", rough=0.45, seed=55)),
        (paint_flat, "shopfront", dict(base="#2b3f33", rough=0.45, seed=56)),
        (planks, "floor", dict(base="#9c7446", worn=0.6, seed=57, board_m=0.0889)),
        (planks, "porch", dict(base="#8b8f8e", painted="#7c8281", worn=0.5, seed=58, board_m=0.0889)),
        (plaster, "plaster", dict(base="#e9e2cf", seed=59, stains=0.2)),
        (beadboard, "beadboard", dict(base="#b8a37e", seed=60, board_m=0.0889)),
        (wood_varnish, "counter", dict(base="#5b3b22", seed=61)),
        (wood_varnish, "door", dict(base="#4d3321", seed=62)),
        (wood_varnish, "furniture", dict(base="#6c4a2d", seed=63)),
        (brick, "chimney", dict(base="#8c4a34", seed=64)),
        (checker_lino, "lino", dict(a="#e4dcc6", b_="#7a2e26", seed=65)),
        (cast_iron, "iron", dict(seed=66)),
        (planks, "ceiling", dict(base="#e8e0cb", painted="#ebe4d0", worn=0.0, seed=67, board_m=0.0889)),
    ],
    "p-tavern": [
        (brick, "brick", dict(base="#9a5238", mortar="#cfc3ad", header_every=7, seed=31)),
        (brick, "brick_arch", dict(base="#874530", mortar="#cfc3ad", course_m=0.0667, brick_m=0.1016, seed=32)),
        (cedar_shingles, "roof", dict(base="#6b645c", exposure_m=0.127, seed=33)),
        (fieldstone, "foundation", dict(base="#9c9486", seed=34)),
        (paint_flat, "trim", dict(base="#f2efe6", rough=0.5, seed=35)),
        (planks, "porch", dict(base="#8b8f8e", painted="#7f8584", worn=0.5, seed=36, board_m=0.0889)),
        (planks, "floor", dict(base="#a07645", worn=0.55, seed=37, board_m=0.1524)),
        (plaster, "plaster", dict(base="#ede3c8", seed=38, stains=0.3)),
        (wood_varnish, "bar", dict(base="#4a2c18", seed=39)),
        (wood_varnish, "door", dict(base="#5c3b24", seed=40)),
        (paint_flat, "shutter", dict(base="#2f4a35", rough=0.55, seed=41)),
        (clapboard, "siding", dict(paint="#ece8dc", exposure_m=0.1143, weather=0.45, seed=42)),
        (checker_lino, "lino", dict(seed=43)),
        (dirt, "dirt", dict(seed=44)),
        (cast_iron, "iron", dict(seed=45)),
        (wood_varnish, "furniture", dict(base="#6e4a2c", seed=46)),
        (planks, "ceiling", dict(base="#e6dcc4", painted="#e9e0c9", worn=0.0, seed=47, board_m=0.1016)),
    ],
    "p-church": [
        (clapboard, "siding", dict(paint="#f4f2ea", exposure_m=0.1016, weather=0.25, seed=11)),
        (cedar_shingles, "roof", dict(base="#77716a", seed=12)),
        (fieldstone, "foundation", dict(seed=13)),
        (brick, "chimney", dict(base="#8a4632", seed=14)),
        (planks, "floor", dict(base="#b08850", worn=0.45, seed=15, board_m=0.1397)),
        (plaster, "wall", dict(base="#efebe0", seed=16)),
        (beadboard, "wainscot", dict(base="#7a5634", seed=17)),
        (paint_flat, "trim", dict(base="#f7f5ef", rough=0.45)),
        (wood_varnish, "pew", dict(base="#6a4526", seed=18)),
        (wood_varnish, "door", dict(base="#5a3a22", seed=19)),
        (cast_iron, "iron", dict(seed=20)),
        (planks, "ceiling", dict(base="#e9e4d6", painted="#ece8dc", worn=0.0, seed=21, board_m=0.0889)),
    ],
}


def main():
    """texgen.py OUTDIR SET  -- one set;  texgen.py --missing  -- every set not generated yet
    (into remake/textures/<set>)."""
    if sys.argv[1] == "--missing":
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "textures")
        for setname in RECIPES:
            out = os.path.join(root, setname)
            if not os.path.exists(os.path.join(out, "set.json")):
                os.makedirs(out, exist_ok=True)
                print("texgen", setname, flush=True)
                sys.argv = [sys.argv[0], out, setname]
                main()
        return
    out, setname = sys.argv[1], sys.argv[2]
    made, tiles = [], {}
    for fn, name, kw in RECIPES[setname]:
        if not os.path.exists(os.path.join(out, name + "_rough.png")):      # resume a partly generated set
            fn(out, name, **kw)
        made.append(name)
        p = inspect.signature(fn).parameters
        tiles[name] = kw.get("tile_m", p["tile_m"].default if "tile_m" in p else 2.0)
        print("  ", name, flush=True)
    json.dump({"set": setname, "materials": made, "tile_m": tiles}, open(os.path.join(out, "set.json"), "w"), indent=0)


if __name__ == "__main__":
    main()
