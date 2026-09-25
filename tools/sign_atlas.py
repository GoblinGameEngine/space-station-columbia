#!/usr/bin/env python3
"""The Space Station Columbia sign faces (road standard §4-5) as one atlas for RoadFurniture.gd:
godot_project/remake/textures/road_signs.png, 8 x 4 cells of 256 px, transparent round each shape.
Cell names and each face's back (a grey silhouette of the same shape) are in CELLS below and
mirrored in RoadFurniture.gd's ATLAS table.
    python3 tools/sign_atlas.py
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "godot_project", "remake", "textures", "road_signs.png")
FONT = os.path.join(ROOT, "godot_project", "ui", "pda", "DejaVuSans-Bold.ttf")
N = 256
SS = 4                                     # supersampling
RED, WHITE, BLACK = (190, 20, 30), (245, 245, 240), (18, 18, 18)
YEL, GREEN, GREY = (250, 200, 20), (0, 110, 60), (150, 152, 155)

CELLS = ["stop", "yield", "speed_15", "speed_40", "speed_50", "speed_60", "speed_70", "speed_90",
         "curve_l", "curve_r", "junction", "rr_ahead", "stop_ahead", "crossbuck", "plate_allway", "dead_end",
         "route_sr14", "route_us30", "route_coast", "rxr", "stripes", "green", "lamp_red", "lamp_off",
         "back_oct", "back_tri", "back_rect", "back_diamond", "back_disc", "back_crossbuck", "back_shield", "back_plate"]


def font(px):
    return ImageFont.truetype(FONT, px * SS)


def octagon(c, r):
    return [(c[0] + r * math.cos(math.radians(22.5 + 45 * k)), c[1] + r * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]


def text(d, xy, s, px, fill, anchor="mm"):
    d.text((xy[0] * SS, xy[1] * SS), s, font=font(px), fill=fill, anchor=anchor)


def P(pts):
    return [(x * SS, y * SS) for x, y in pts]


def cell(name):
    im = Image.new("RGBA", (N * SS, N * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (N / 2, N / 2)
    shape = None
    if name in ("stop", "back_oct"):
        shape = octagon(c, 124)
        if name == "back_oct":
            d.polygon(P(shape), fill=GREY)
        else:
            d.polygon(P(shape), fill=WHITE)
            d.polygon(P(octagon(c, 116)), fill=RED)
            text(d, c, "STOP", 72, WHITE)
    elif name in ("yield", "back_tri"):
        tri = [(4, 20), (252, 20), (128, 236)]
        if name == "back_tri":
            d.polygon(P(tri), fill=GREY)
        else:
            d.polygon(P(tri), fill=RED)
            d.polygon(P([(52, 48), (204, 48), (128, 180)]), fill=WHITE)
            text(d, (128, 92), "YIELD", 26, RED)
    elif name.startswith("speed_") or name in ("back_rect",):
        box = (40, 6, 216, 250)
        if name == "back_rect":
            d.rounded_rectangle([v * SS for v in box], 10 * SS, fill=GREY)
        else:
            d.rounded_rectangle([v * SS for v in box], 10 * SS, fill=WHITE)
            d.rounded_rectangle([v * SS for v in (46, 12, 210, 244)], 8 * SS, outline=BLACK, width=4 * SS)
            text(d, (128, 62), "SPEED", 30, BLACK)
            text(d, (128, 96), "LIMIT", 30, BLACK)
            text(d, (128, 166), name.split("_")[1], 84, BLACK)
            text(d, (128, 222), "km/h", 24, BLACK)
    elif name in ("curve_l", "curve_r", "junction", "stop_ahead", "back_diamond", "dead_end"):
        dia = [(128, 2), (254, 128), (128, 254), (2, 128)]
        if name == "back_diamond":
            d.polygon(P(dia), fill=GREY)
        else:
            d.polygon(P(dia), fill=BLACK)
            d.polygon(P([(128, 10), (246, 128), (128, 246), (10, 128)]), fill=YEL)
            if name in ("curve_l", "curve_r"):
                sg = -1 if name == "curve_l" else 1
                # a bent arrow: straight up, then bending to the side
                d.line(P([(128 - sg * 10, 200), (128 - sg * 10, 130)]), fill=BLACK, width=22 * SS)
                pts = [(128 - sg * 10 + sg * (50 - 50 * math.cos(math.radians(90 * k / 12))), 130 - 50 * math.sin(math.radians(90 * k / 12))) for k in range(13)]
                d.line(P(pts), fill=BLACK, width=22 * SS, joint="curve")
                tip = pts[-1]
                d.polygon(P([(tip[0] + sg * 34, tip[1]), (tip[0] - sg * 4, tip[1] - 30), (tip[0] - sg * 4, tip[1] + 30)]), fill=BLACK)
            elif name == "junction":
                d.line(P([(128, 60), (128, 200)]), fill=BLACK, width=24 * SS)
                d.line(P([(62, 128), (194, 128)]), fill=BLACK, width=24 * SS)
            elif name == "stop_ahead":
                d.polygon(P(octagon((128, 110), 44)), fill=RED)
                text(d, (128, 110), "STOP", 20, WHITE)
                d.line(P([(128, 160), (128, 212)]), fill=BLACK, width=16 * SS)
                d.polygon(P([(128, 150), (108, 176), (148, 176)]), fill=BLACK)
            elif name == "dead_end":
                text(d, (128, 108), "DEAD", 38, BLACK)
                text(d, (128, 150), "END", 38, BLACK)
    elif name in ("rr_ahead", "back_disc"):
        if name == "back_disc":
            d.ellipse([4 * SS, 4 * SS, 252 * SS, 252 * SS], fill=GREY)
        else:
            d.ellipse([4 * SS, 4 * SS, 252 * SS, 252 * SS], fill=BLACK)
            d.ellipse([10 * SS, 10 * SS, 246 * SS, 246 * SS], fill=YEL)
            d.line(P([(52, 52), (204, 204)]), fill=BLACK, width=14 * SS)
            d.line(P([(204, 52), (52, 204)]), fill=BLACK, width=14 * SS)
            text(d, (74, 128), "R", 56, BLACK)
            text(d, (182, 128), "R", 56, BLACK)
    elif name in ("crossbuck", "back_crossbuck"):
        # two crossed boards at 45 deg: 1.2 m x 0.23 m each
        for ang in (45, -45):
            a = math.radians(ang)
            u = (math.cos(a), math.sin(a))
            v = (-u[1], u[0])
            L, W = 128, 24
            box = [(128 + u[0] * L * s1 + v[0] * W * s2, 128 + u[1] * L * s1 + v[1] * W * s2) for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            d.polygon(P(box), fill=GREY if name == "back_crossbuck" else RED)
            if name == "crossbuck":
                inner = [(128 + u[0] * (L - 5) * s1 + v[0] * (W - 5) * s2, 128 + u[1] * (L - 5) * s1 + v[1] * (W - 5) * s2)
                         for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                d.polygon(P(inner), fill=WHITE)
        if name == "crossbuck":
            for ang, word in ((45, "RAIL        ROAD"), (-45, "CROSS        ING")):
                t = Image.new("RGBA", (N * SS, N * SS), (0, 0, 0, 0))
                td = ImageDraw.Draw(t)
                td.text((128 * SS, 128 * SS), word, font=font(20), fill=BLACK, anchor="mm")
                t = t.rotate(-ang, resample=Image.BICUBIC)
                im.alpha_composite(t)
    elif name in ("plate_allway", "back_plate"):
        box = (40, 88, 216, 168)
        d.rectangle([v * SS for v in box], fill=GREY if name == "back_plate" else WHITE)
        if name == "plate_allway":
            d.polygon(P([(40, 88), (216, 88), (216, 168), (40, 168)]), fill=RED)
            text(d, (128, 128), "ALL WAY", 34, WHITE)
    elif name.startswith("route_") or name == "back_shield":
        sh = [(40, 20), (216, 20), (216, 150), (128, 236), (40, 150)]
        d.polygon(P(sh), fill=GREY if name == "back_shield" else BLACK)
        if name != "back_shield":
            d.polygon(P([(48, 28), (208, 28), (208, 146), (128, 226), (48, 146)]), fill=WHITE)
            label = {"route_sr14": ("STATE", "14"), "route_us30": ("U.S.", "30"), "route_coast": ("COAST", "HWY")}[name]
            text(d, (128, 62), label[0], 28, BLACK)
            text(d, (128, 132), label[1], 68 if label[1].isdigit() else 46, BLACK)
    elif name == "rxr":
        # the pavement marking: an X with R R, white, stretched along the lane (the quad is 3 x 6 m)
        d.line(P([(40, 20), (216, 236)]), fill=WHITE, width=16 * SS)
        d.line(P([(216, 20), (40, 236)]), fill=WHITE, width=16 * SS)
        text(d, (60, 128), "R", 60, WHITE)
        text(d, (196, 128), "R", 60, WHITE)
    elif name == "stripes":
        for k in range(8):
            d.rectangle([k * 32 * SS, 0, (k + 1) * 32 * SS, N * SS], fill=RED if k % 2 == 0 else WHITE)
    elif name == "green":
        d.rectangle([0, 0, N * SS, N * SS], fill=GREEN)
    elif name == "lamp_red":
        d.rectangle([0, 0, N * SS, N * SS], fill=(255, 40, 30))
    elif name == "lamp_off":
        d.rectangle([0, 0, N * SS, N * SS], fill=(70, 20, 18))
    return im.resize((N, N), Image.LANCZOS)


def main():
    atlas = Image.new("RGBA", (8 * N, 4 * N), (0, 0, 0, 0))
    for k, name in enumerate(CELLS):
        atlas.alpha_composite(cell(name), ((k % 8) * N, (k // 8) * N))
    atlas.save(OUT)
    print(f"sign atlas: {len(CELLS)} faces -> {OUT}")


if __name__ == "__main__":
    main()
