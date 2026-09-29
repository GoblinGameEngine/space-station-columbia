#!/usr/bin/env python3
"""The vehicle crash sound: godot_project/remake/audio/crash.wav (22.05 kHz, mono, 16-bit, like the
game's other sounds).  Synthesised, not sampled, so it can be regenerated and tuned:

  thump    the body's hit: a low sine falling 110 -> 38 Hz, decaying over ~0.35 s
  crunch   panels buckling: a train of micro-impacts over the first ~0.25 s, each exciting a set of
           inharmonic sheet-metal modes (300 Hz - 4 kHz, decaying 40-250 ms) plus a burst of noise
  scrape   the tail: band-passed noise sliding off over ~0.6 s
  debris   bits of trim and glass settling: short bright grains scattered from 0.15 to 1.1 s

The game plays it louder and lower-pitched for a harder hit (air_vehicle.gd, _impact).
Run:  python3 tools/crash_sound.py
"""
import wave
from pathlib import Path

import numpy as np

SR = 22050
DUR = 1.6
OUT = Path(__file__).resolve().parent.parent / "godot_project/remake/audio/crash.wav"
rng = np.random.default_rng(1983)
t = np.arange(int(SR * DUR)) / SR


def biquad_bandpass(x, f0, q):
    """RBJ band-pass (constant 0 dB peak gain)."""
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) / (2 * q)
    b0, b1, b2 = alpha, 0.0, -alpha
    a0, a1, a2 = 1 + alpha, -2 * np.cos(w0), 1 - alpha
    b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, xi in enumerate(x):
        yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, xi, y1, yi
        y[i] = yi
    return y


def one_pole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, xi in enumerate(x):
        acc = (1 - a) * xi + a * acc
        y[i] = acc
    return y


out = np.zeros_like(t)

# thump: pitch falls as the structure gives
f = 38 + 72 * np.exp(-t / 0.07)
phase = 2 * np.pi * np.cumsum(f) / SR
out += 0.9 * np.sin(phase) * np.exp(-t / 0.12) * (1 - np.exp(-t / 0.002))

# crunch: micro-impacts, denser and harder at the start
modes = [(310, 0.25), (447, 0.2), (690, 0.16), (905, 0.12), (1340, 0.09), (1720, 0.07),
         (2310, 0.05), (2980, 0.04), (3870, 0.03)]
hits = np.sort(np.concatenate([[0.0], rng.uniform(0.0, 0.26, 22) ** 1.6]))
for k, h in enumerate(hits):
    amp = 0.55 * np.exp(-h / 0.12) * rng.uniform(0.5, 1.0)
    tt = t - h
    on = tt >= 0
    for fm, dec in modes:
        fm_j = fm * rng.uniform(0.94, 1.06)
        env = np.exp(-np.where(on, tt, 0) / dec) * on
        out += amp * 0.22 * np.sin(2 * np.pi * fm_j * tt + rng.uniform(0, 6.28)) * env
    # each hit's own click of noise
    n = int(SR * 0.012)
    i0 = int(h * SR)
    burst = rng.normal(0, 1, n) * np.exp(-np.arange(n) / (SR * 0.003))
    out[i0:i0 + n] += amp * 0.5 * burst[: len(out) - i0]

# scrape: band-passed noise, its centre sliding down
noise = rng.normal(0, 1, len(t))
scr = biquad_bandpass(noise, 1600, 1.4) * 0.6 + biquad_bandpass(noise, 700, 2.0) * 0.5
out += 0.35 * scr * np.exp(-np.maximum(t - 0.05, 0) / 0.22) * (t > 0.02)

# debris: bright short grains
for _ in range(34):
    g0 = rng.uniform(0.15, 1.1) ** 1.2
    fg = rng.uniform(2500, 6500)
    tt = t - g0
    on = (tt >= 0) & (tt < 0.08)
    amp = 0.12 * np.exp(-g0 / 0.45) * rng.uniform(0.3, 1.0)
    out += amp * np.sin(2 * np.pi * fg * tt) * np.exp(-np.where(on, tt, 0) / 0.012) * on

# a touch of low-pass body so it isn't all fizz, then fades and normalise
out = 0.75 * out + 0.25 * one_pole_lp(out, 2500) * 2.0
out *= np.minimum(1.0, (DUR - t) / 0.25)
out = np.tanh(out * 1.3)
out /= np.max(np.abs(out)) / 0.95
pcm = (out * 32767).astype("<i2")
with wave.open(str(OUT), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(OUT, f"{DUR} s")
