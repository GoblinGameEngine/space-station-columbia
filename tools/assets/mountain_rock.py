#!/usr/bin/env python3
"""mountain_rock.py -- the end-cap mountains' rock (godot_project/remake/scripts/cap_mountains.gd): a tileable massive
cliff rock -- vertical joints, weathering streaks running down the face (desert varnish), coarse grain, faint
bedding -- as albedo, normal and roughness (1024 px, tiles 1:1). Neutral in colour: the mesh's vertex colours carry
the sandstone-to-limestone tones. The bluff's striped bedrock suits a 150 m sedimentary bluff; a 1.5 km sheer wall
needs the vertical structure of Yosemite or Zion walls.

    ~/.venvs/ssc-assets/bin/python tools/assets/mountain_rock.py      # -> godot_project/remake/cliffs/mountain_*
"""
import os

import numpy as np
from PIL import Image

N = 1024
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "godot_project", "remake", "cliffs")   # (tracked: remake/textures is gitignored)
rng = np.random.default_rng(2752)


def noise(fx, fy, seed):
    """Tileable value noise: a random grid of fx x fy cells, smoothly upsampled (wraps both ways)."""
    g = np.random.default_rng(seed).random((fy, fx))
    ys = np.arange(N) * fy / N
    xs = np.arange(N) * fx / N
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    ty, tx = ys - y0, xs - x0
    ty, tx = ty * ty * (3 - 2 * ty), tx * tx * (3 - 2 * tx)
    y1, x1 = (y0 + 1) % fy, (x0 + 1) % fx
    a = g[np.ix_(y0, x0)] * (1 - tx) + g[np.ix_(y0, x1)] * tx
    b = g[np.ix_(y1, x0)] * (1 - tx) + g[np.ix_(y1, x1)] * tx
    return a * (1 - ty)[:, None] + b * ty[:, None]


def fbm(f, octaves, seed, aniso=1.0):
    out = np.zeros((N, N))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        fx = int(f * 2 ** o)
        fy = max(1, int(f * 2 ** o / aniso))
        out += amp * noise(fx, fy, seed + o)
        tot += amp
        amp *= 0.5
    return out / tot


def main():
    grain = fbm(8, 6, 1)                                   # coarse grain and lichen-ish mottling
    slabs = fbm(3, 2, 41)                                  # big blocks of lighter and darker rock
    streak = fbm(24, 4, 11, aniso=6.0)                     # long vertical streaks (aniso: stretched down the face)
    bedding = 0.5 + 0.5 * np.sin(np.linspace(0, 6 * np.pi, N))[:, None] * np.ones((1, N))
    # vertical joints: dark cracks at jittered spacing, wandering a little
    joints = np.zeros((N, N))
    wander = (fbm(6, 2, 21, aniso=6.0) - 0.5) * 30            # (slow, gentle wander down the face)
    for x0 in np.cumsum(rng.integers(110, 260, 7)):
        x0 = x0 % N
        xs = (x0 + wander[:, x0 % N]).astype(int) % N
        for w in range(-2, 3):
            joints[np.arange(N), (xs + w) % N] = np.maximum(joints[np.arange(N), (xs + w) % N], 0.8 - abs(w) / 3.0)
    joints *= (fbm(6, 3, 31, aniso=0.3) > 0.42)            # (joints break up and restart)
    height = 0.55 * grain + 0.25 * streak + 0.06 * bedding - 0.35 * joints
    # albedo: neutral warm grey, varnish streaks darker and browner, joints dark
    v = 0.78 + 0.16 * (grain - 0.5) + 0.22 * (slabs - 0.5) - 0.28 * np.clip(streak - 0.55, 0, 1) * 2 - 0.35 * joints + 0.03 * (bedding - 0.5)
    v = np.clip(v, 0.25, 1.0)
    alb = np.stack([v * 1.0, v * 0.96, v * 0.9], -1)
    var = np.clip(streak - 0.55, 0, 1)[..., None] * np.array([0.0, -0.05, -0.1])
    alb = np.clip(alb + var, 0, 1)
    Image.fromarray((alb * 255).astype(np.uint8)).save(os.path.join(OUT, "mountain_albedo.webp"), quality=92)
    # normal from height (wrap-around differences)
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 3.0
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 3.0
    nrm = np.stack([-dx, dy, np.ones_like(dx)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(OUT, "mountain_normal.webp"), quality=92)
    rough = np.clip(0.85 + 0.1 * (grain - 0.5) - 0.15 * np.clip(streak - 0.6, 0, 1), 0, 1)
    Image.fromarray((rough * 255).astype(np.uint8)).save(os.path.join(OUT, "mountain_rough.webp"), quality=92)
    print("mountain rock ->", OUT)


if __name__ == "__main__":
    main()
