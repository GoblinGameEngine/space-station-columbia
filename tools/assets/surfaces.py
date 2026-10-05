#!/usr/bin/env python3
"""surfaces.py -- the fleet's generic surface textures (research/vehicles/TEXTURES.md): a small library of tileable
grey surfaces that every vehicle shares, tinted in the game by each style's palette colour and projected in the
vehicle's own frame (object-space triplanar: no UVs), the way large-world games reuse a few tiling materials across
thousands of assets instead of painting each one.

    ~/.venvs/ssc-assets/bin/python tools/assets/surfaces.py     # -> godot_project/remake/textures/surfaces/

Each surface: <name>_albedo.png (grey, around mid-light so the palette's colour reads true), <name>_normal.png (from
its height field, OpenGL convention), <name>_rough.png (a multiplier on the material's roughness). 512 px, tiling:
every field is built from periodic noise (filtered white noise in the frequency domain wraps seamlessly).
"""
import os

import numpy as np
from PIL import Image

N = 512
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "godot_project", "remake", "textures", "surfaces")
rng = np.random.default_rng(2752)


def noise(f0, f1=None, aniso=(1.0, 1.0)):
    """Periodic band-limited noise, frequencies f0..f1 cycles per tile; aniso stretches it (grain, brushing)."""
    f1 = f1 or f0 * 2
    w = rng.standard_normal((N, N))
    F = np.fft.fft2(w)
    fy = np.fft.fftfreq(N)[:, None] * N * aniso[1]
    fx = np.fft.fftfreq(N)[None, :] * N * aniso[0]
    r = np.sqrt(fx ** 2 + fy ** 2)
    band = np.exp(-((np.log(r + 1e-6) - np.log((f0 * f1) ** 0.5)) / (0.5 * np.log(f1 / f0 + 1.001))) ** 2)
    out = np.real(np.fft.ifft2(F * band))
    return (out - out.mean()) / (out.std() + 1e-9)


def grid(n, width):
    """1 on lines every N/n px (both axes), tiling."""
    y, x = np.mgrid[0:N, 0:N]
    p = N / n
    d = np.minimum(np.minimum(x % p, p - x % p), np.minimum(y % p, p - y % p))
    return np.clip(1.0 - d / width, 0, 1)


def normal_from(h, strength):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    n = np.stack([-gx, gy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def save(name, albedo, height, rough, nstrength):
    os.makedirs(OUT, exist_ok=True)
    a = (np.clip(albedo, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(np.stack([a] * 3, -1)).save(os.path.join(OUT, name + "_albedo.png"))
    Image.fromarray(normal_from(height, nstrength)).save(os.path.join(OUT, name + "_normal.png"))
    r = (np.clip(rough, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(np.stack([r] * 3, -1)).save(os.path.join(OUT, name + "_rough.png"))
    print("%-8s albedo %.2f..%.2f  rough %.2f..%.2f" % (name, albedo.min(), albedo.max(), rough.min(), rough.max()))


def main():
    # paint: orange peel, a faint speckle; nearly flat in tone (the palette is the colour)
    peel = noise(40, 90)
    save("paint", 0.93 + 0.025 * noise(6, 20) + 0.01 * noise(120, 250), peel, 0.85 + 0.08 * noise(10, 30) + 0.05 * peel, 0.5)
    # plastic: a fine moulded stipple
    st = noise(150, 250)
    save("plastic", 0.90 + 0.03 * st + 0.02 * noise(8, 20), st, 0.9 + 0.08 * st, 2.0)
    # brushed: long streaks one way
    br = noise(30, 200, aniso=(25.0, 1.0))
    save("brushed", 0.88 + 0.06 * br, br * 0.3, 0.7 + 0.25 * br, 1.0)
    # rubber: a matte, slightly mottled compound, a moulded block tread
    tread = grid(16, 3.0)
    save("rubber", 0.85 + 0.04 * noise(20, 60) - 0.10 * tread, -tread * 2.0 + 0.2 * noise(60, 120), 0.95 + 0.04 * noise(40, 80), 1.5)
    # fabric: a plain weave
    y, x = np.mgrid[0:N, 0:N]
    weave = np.sin(x * 2 * np.pi / 8) * np.sin(y * 2 * np.pi / 8)
    save("fabric", 0.86 + 0.06 * weave + 0.03 * noise(10, 30), weave * 1.5 + 0.3 * noise(80, 160), 0.95 + 0.04 * weave, 1.2)
    # canvas: a coarse weave and stitched seams (the envelopes' gores, a canopy's panels)
    cw = np.sin(x * 2 * np.pi / 6) * np.sin(y * 2 * np.pi / 6)
    seam = grid(2, 2.5)
    save("canvas", 0.90 + 0.04 * cw + 0.03 * noise(6, 18) - 0.12 * seam, cw * 0.8 - seam * 3.0, 0.9 + 0.05 * cw, 1.0)
    # wood: long grain, rings drifting across, the odd darker figure
    g = noise(2, 6, aniso=(1.0, 12.0))
    rings = np.sin((x / N * 2 * np.pi * 9) + 2.5 * g)
    save("wood", 0.70 + 0.15 * rings + 0.06 * noise(20, 80, aniso=(1.0, 12.0)), rings * 0.6 + 0.4 * noise(100, 200, aniso=(1.0, 12.0)),
         0.75 + 0.15 * rings * 0.5, 1.5)
    # vinyl: a pebbled leathercloth (linings, headliners, dash tops)
    peb = np.abs(noise(40, 70))
    save("vinyl", 0.90 + 0.04 * peb + 0.02 * noise(5, 15), -peb, 0.85 + 0.1 * peb, 2.2)
    # carpet: dense random loops
    cp = noise(150, 256)
    save("carpet", 0.82 + 0.08 * cp + 0.04 * noise(10, 30), cp, 1.0 - 0.02 * cp, 2.5)
    # bone: the Steward's printed alloy, smooth and faintly organic
    bo = noise(4, 12) + 0.3 * noise(30, 60)
    save("bone", 0.92 + 0.03 * bo, bo * 0.4, 0.6 + 0.1 * bo, 1.0)


if __name__ == "__main__":
    main()
