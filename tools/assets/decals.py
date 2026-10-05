#!/usr/bin/env python3
"""decals.py -- the fleet's generic decals (research/vehicles/TEXTURES.md, "Decals"): small RGBA images the game
projects onto a vehicle's panels (Decal nodes riding with its body), placed by the Blender pipeline (the blueprint's
"decals"). Generic so one image serves many: lettering is white, tinted in the game by each livery; plates, gauges,
chevrons and the star of life keep their own colours.

    ~/.venvs/ssc-assets/bin/python tools/assets/decals.py     # -> godot_project/remake/vehicles/decals/

Canon: the station's police are the Marshals (research/bible/03_history.md); plates read COLUMBIA and the year of the
voyage, VY. Words and numbers are listed in WORDS / NUMBERS (the pipeline asks for them by name: word_<WORD>).
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
OUT = os.path.join(ROOT, "godot_project", "remake", "vehicles", "decals")
FONT = os.path.join(ROOT, "godot_project", "assets", "fonts", "DejaVuSans-Bold.ttf")
WORDS = ["FIRE DEPT", "MARSHAL", "TAXI", "AMBULANCE", "POST", "SCHOOL BUS", "RESCUE", "PUBLIC WORKS", "COAST GUARD",
         "LIFEGUARD", "TRAMWAYS", "SANITATION", "RECYCLING", "SECURE TRANSIT", "PARATRANSIT", "HOTEL SHUTTLE", "ICE CREAM",
         "PARCELS", "FREIGHT", "COLUMBIA", "FARM", "WORKS"]
NUMBERS = 24


def font(px):
    return ImageFont.truetype(FONT, px)


def fit_text(text, h, pad=0.12):
    """White lettering on clear, its height h px, as wide as it needs (a little tracking)."""
    f = font(int(h * 0.8))
    w = int(f.getlength(text) + h * 0.1 * len(text)) + int(h * pad * 2)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = h * pad
    for ch in text:
        d.text((x, h * 0.08), ch, font=f, fill=(255, 255, 255, 255))
        x += f.getlength(ch) + h * 0.1
    return im


def plate(n, rng):
    """A Columbia plate: cream, a navy rim, COLUMBIA across the top, two letters and four figures, VY at the foot."""
    w, h = 520, 110
    im = Image.new("RGBA", (w, h), (236, 230, 210, 255))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((3, 3, w - 4, h - 4), radius=10, outline=(24, 40, 82, 255), width=6)
    d.text((w / 2, 18), "COLUMBIA", font=font(16), fill=(24, 40, 82, 255), anchor="mm")
    reg = "%s%s %04d" % (chr(65 + rng.randrange(26)), chr(65 + rng.randrange(26)), rng.randrange(10000))
    d.text((w / 2, 64), reg, font=font(54), fill=(20, 22, 28, 255), anchor="mm")
    d.text((w / 2, 98), "VY 500", font=font(12), fill=(24, 40, 82, 255), anchor="mm")
    return im


def gauges():
    """The instrument cluster: a speedometer and a charge gauge, ticks and needles, on a dark face."""
    w, h = 512, 200
    im = Image.new("RGBA", (w, h), (24, 24, 26, 255))
    d = ImageDraw.Draw(im)
    for cx, r, ticks, needle in ((150, 86, 12, 0.35), (380, 70, 8, 0.7)):
        d.ellipse((cx - r, 100 - r, cx + r, 100 + r), fill=(236, 228, 204, 255), outline=(150, 150, 150, 255), width=4)
        for k in range(ticks + 1):
            a = math.radians(225 - 270 * k / ticks)
            d.line((cx + math.cos(a) * r * 0.78, 100 - math.sin(a) * r * 0.78, cx + math.cos(a) * r * 0.93, 100 - math.sin(a) * r * 0.93),
                   fill=(30, 30, 30, 255), width=4)
        a = math.radians(225 - 270 * needle)
        d.line((cx, 100, cx + math.cos(a) * r * 0.8, 100 - math.sin(a) * r * 0.8), fill=(200, 40, 30, 255), width=5)
        d.ellipse((cx - 8, 92, cx + 8, 108), fill=(30, 30, 30, 255))
    d.rectangle((250, 160, 280, 175), fill=(60, 200, 90, 255))             # (a lamp: ready)
    return im


def dial(kind):
    """A dial face for the binnacle's live gauges: a 270-degree sweep from 225 deg (lower left) clockwise to -45 (lower
    right); the game turns the needle over it. speed: 0-160 km/h; battery: E to F, the last fifth red."""
    S = 512
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c, R = S / 2, S / 2 - 6
    d.ellipse((6, 6, S - 6, S - 6), fill=(236, 230, 210, 255), outline=(170, 170, 170, 255), width=10)
    def at(frac, rr):
        a = math.radians(225 - 270 * frac)
        return c + math.cos(a) * rr, c - math.sin(a) * rr
    if kind == "speed":
        for k in range(0, 33):
            f = k / 32
            major = k % 4 == 0
            d.line((*at(f, R * (0.70 if major else 0.78)), *at(f, R * 0.88)), fill=(25, 25, 28, 255), width=8 if major else 4)
            if major:
                d.text(at(f, R * 0.56), str(k * 5), font=font(40), fill=(25, 25, 28, 255), anchor="mm")
        d.text((c, c + R * 0.42), "km/h", font=font(34), fill=(60, 60, 64, 255), anchor="mm")
    else:
        d.arc((c - R * 0.80, c - R * 0.80, c + R * 0.80, c + R * 0.80), 135, 135 + 54, fill=(200, 40, 30, 255), width=30)   # (low: red)
        for k in range(0, 9):
            f = k / 8
            d.line((*at(f, R * 0.70), *at(f, R * 0.88)), fill=(25, 25, 28, 255), width=8 if k % 4 == 0 else 4)
        d.text(at(0.0, R * 0.56), "E", font=font(60), fill=(25, 25, 28, 255), anchor="mm")
        d.text(at(0.5, R * 0.52), "1/2", font=font(44), fill=(25, 25, 28, 255), anchor="mm")
        d.text(at(1.0, R * 0.56), "F", font=font(60), fill=(25, 25, 28, 255), anchor="mm")
        d.text((c, c + R * 0.62), "CHARGE", font=font(30), fill=(60, 60, 64, 255), anchor="mm")
    return im


def star_of_life():
    s = 256
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bar = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(bar).rounded_rectangle((s * 0.40, s * 0.06, s * 0.60, s * 0.94), radius=8, fill=(30, 90, 200, 255))
    for k in range(3):
        im = Image.alpha_composite(im, bar.rotate(60 * k, resample=Image.BICUBIC))
    d = ImageDraw.Draw(im)
    d.line((s / 2, s * 0.25, s / 2, s * 0.78), fill=(255, 255, 255, 255), width=6)        # (the staff of Asclepius, simply)
    d.arc((s * 0.42, s * 0.30, s * 0.58, s * 0.46), 90, 270, fill=(255, 255, 255, 255), width=5)
    d.arc((s * 0.42, s * 0.44, s * 0.58, s * 0.60), 270, 90, fill=(255, 255, 255, 255), width=5)
    return im


def chevrons():
    """Rear-marking chevrons: alternating orange and black at 45 degrees."""
    w, h = 512, 128
    im = Image.new("RGBA", (w, h), (20, 20, 22, 255))
    d = ImageDraw.Draw(im)
    for k in range(-4, 12):
        x = k * 64
        d.polygon([(x, h), (x + 32, h), (x + 32 + h, 0), (x + h, 0)], fill=(236, 140, 24, 255))
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(2752)
    for n in range(8):
        plate(n, rng).save(os.path.join(OUT, "plate_%d.png" % n))
    dial("speed").save(os.path.join(OUT, "dial_speed.png"))
    dial("battery").save(os.path.join(OUT, "dial_battery.png"))
    star_of_life().save(os.path.join(OUT, "star_of_life.png"))
    chevrons().save(os.path.join(OUT, "chevrons.png"))
    for wd in WORDS:
        fit_text(wd, 128).save(os.path.join(OUT, "word_%s.png" % wd.replace(" ", "_")))
    for k in range(1, NUMBERS + 1):
        fit_text("%02d" % k, 128).save(os.path.join(OUT, "num_%02d.png" % k))
    print("decals:", len(os.listdir(OUT)))


if __name__ == "__main__":
    main()
