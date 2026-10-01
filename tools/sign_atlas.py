#!/usr/bin/env python3
"""The Space Station Columbia sign faces (road standard §4-5) as one atlas for RoadFurniture.gd:
godot_project/remake/textures/road_signs.png, 8 x 8 cells of 256 px, transparent round each shape.
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
         "back_oct", "back_tri", "back_rect", "back_diamond", "back_disc", "back_crossbuck", "back_shield", "back_plate",
         # parking and transit (MUTCD R7 / R8 / D4 / D9 / W14; research/law/04_signs.md)
         "no_parking", "no_parking_tram", "parking_2h", "parking_3h", "pay_station", "tow_away", "emergency_route", "flood_route",
         "accessible", "park_ride", "parking_guide", "no_outlet", "school", "back_tall", "back_pennant", "back_square",
         "tram_port_carrow", "tram_kessler", "tram_solana_point", "tram_harrow_falls", "tram_brightwater", "tram_oceanview"]
TRAM_FLAG = {   # the cities' transit authorities' own stop flags (tools/law/canon_law.py CITIES transit)
    "tram_port_carrow": ("rect", (29, 43, 79), (255, 255, 255), (154, 107, 52), "PCLT"),
    "tram_kessler": ("roundel", (179, 27, 27), (255, 255, 255), (34, 34, 34), "CAT"),
    "tram_solana_point": ("pennant", (236, 185, 40), (17, 17, 17), (30, 128, 128), "SMT"),
    "tram_harrow_falls": ("shield", (47, 107, 58), (255, 255, 255), (122, 44, 30), "KVT"),
    "tram_brightwater": ("disc", (31, 138, 138), (242, 230, 200), (192, 57, 43), "BBT"),
    "tram_oceanview": ("square", (226, 113, 29), (255, 255, 255), (31, 78, 140), "OCT"),
}


def tram_symbol(d, cx, cy, sc, col):
    """A tram seen from the front: the rounded body, the windscreen, two lamps (the station's)."""
    w, h = 60 * sc, 78 * sc
    d.rounded_rectangle([(cx - w / 2) * SS, (cy - h / 2) * SS, (cx + w / 2) * SS, (cy + h / 2) * SS], 14 * sc * SS, fill=col)
    bg = (0, 0, 0, 0)
    d.rounded_rectangle([(cx - w / 2 + 8 * sc) * SS, (cy - h / 2 + 12 * sc) * SS, (cx + w / 2 - 8 * sc) * SS, (cy - 2 * sc) * SS], 6 * sc * SS, fill=bg)
    for lx in (-1, 1):
        d.ellipse([(cx + lx * 16 * sc - 6 * sc) * SS, (cy + 18 * sc - 6 * sc) * SS, (cx + lx * 16 * sc + 6 * sc) * SS, (cy + 18 * sc + 6 * sc) * SS], fill=bg)
    d.rectangle([(cx - w / 2 + 4 * sc) * SS, (cy + h / 2) * SS, (cx - w / 2 + 14 * sc) * SS, (cy + h / 2 + 8 * sc) * SS], fill=col)
    d.rectangle([(cx + w / 2 - 14 * sc) * SS, (cy + h / 2) * SS, (cx + w / 2 - 4 * sc) * SS, (cy + h / 2 + 8 * sc) * SS], fill=col)



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
    elif name in ("no_parking", "no_parking_tram", "parking_2h", "parking_3h", "pay_station", "tow_away", "accessible", "back_tall"):
        # the R7 family: a tall white rectangle (12 x 18 in), black border; legends in red (prohibitions) or green
        box = (56, 4, 200, 252)
        if name == "back_tall":
            d.rounded_rectangle([v * SS for v in box], 6 * SS, fill=GREY)
        else:
            d.rounded_rectangle([v * SS for v in box], 6 * SS, fill=WHITE)
            d.rounded_rectangle([v * SS for v in (60, 8, 196, 248)], 5 * SS, outline=BLACK, width=3 * SS)
            arrow = lambda y, col: (d.line(P([(84, y), (172, y)]), fill=col, width=7 * SS),
                                    d.polygon(P([(76, y), (96, y - 14), (96, y + 14)]), fill=col),
                                    d.polygon(P([(180, y), (160, y - 14), (160, y + 14)]), fill=col))
            if name == "no_parking":
                text(d, (128, 50), "NO", 40, RED)
                text(d, (128, 96), "PARKING", 26, RED)
                text(d, (128, 136), "ANY", 30, RED)
                text(d, (128, 172), "TIME", 30, RED)
                arrow(220, RED)
            elif name == "no_parking_tram":
                text(d, (128, 40), "NO", 36, RED)
                text(d, (128, 78), "PARKING", 24, RED)
                tram_symbol(d, 128, 150, 0.9, BLACK)
                arrow(225, RED)
            elif name in ("parking_2h", "parking_3h"):
                text(d, (128, 52), name[-2], 64, GREEN)
                text(d, (128, 96), "HOUR", 28, GREEN)
                text(d, (128, 128), "PARKING", 24, GREEN)
                text(d, (128, 166), "8AM-6PM", 22, GREEN)
                arrow(218, GREEN)
            elif name == "pay_station":
                text(d, (128, 70), "PAY", 46, GREEN)
                text(d, (128, 120), "STATION", 26, GREEN)
                arrow(190, GREEN)
            elif name == "tow_away":
                text(d, (128, 90), "TOW-", 40, RED)
                text(d, (128, 140), "AWAY", 40, RED)
                text(d, (128, 186), "ZONE", 40, RED)
            elif name == "accessible":
                d.rectangle([v * SS for v in (80, 30, 176, 130)], fill=(20, 60, 160))
                text(d, (128, 80), "\u267f", 70, WHITE)
                text(d, (128, 166), "RESERVED", 22, GREEN)
                text(d, (128, 198), "PARKING", 22, GREEN)
    elif name in ("emergency_route", "flood_route"):
        box = (40, 30, 216, 226)
        d.rectangle([v * SS for v in box], fill=WHITE)
        d.rectangle([v * SS for v in (40, 30, 216, 96)], fill=RED)
        d.rectangle([v * SS for v in box], outline=BLACK, width=3 * SS)
        text(d, (128, 63), "EMERGENCY" if name == "emergency_route" else "FLOOD", 24 if name == "emergency_route" else 34, WHITE)
        text(d, (128, 130), "ROUTE", 34, BLACK)
        text(d, (128, 180), "NO PARKING", 22, RED)
        text(d, (128, 206), "WHEN DECLARED", 14, BLACK)
    elif name in ("park_ride", "parking_guide", "back_square"):
        box = (24, 40, 232, 216)
        if name == "back_square":
            d.rounded_rectangle([v * SS for v in box], 10 * SS, fill=GREY)
        elif name == "park_ride":
            d.rounded_rectangle([v * SS for v in box], 10 * SS, fill=GREEN)
            d.rounded_rectangle([v * SS for v in (30, 46, 226, 210)], 8 * SS, outline=WHITE, width=3 * SS)
            text(d, (100, 92), "PARK &", 30, WHITE)
            text(d, (100, 134), "RIDE", 34, WHITE)
            tram_symbol(d, 186, 120, 0.7, WHITE)
            text(d, (128, 186), "TRAM", 24, WHITE)
        else:
            d.rounded_rectangle([v * SS for v in box], 10 * SS, fill=(20, 60, 160))
            text(d, (128, 128), "P", 120, WHITE)
    elif name == "no_outlet":
        dia = [(128, 2), (254, 128), (128, 254), (2, 128)]
        d.polygon(P(dia), fill=BLACK)
        d.polygon(P([(128, 10), (246, 128), (128, 246), (10, 128)]), fill=YEL)
        text(d, (128, 108), "NO", 40, BLACK)
        text(d, (128, 150), "OUTLET", 30, BLACK)
    elif name == "school":
        pent = [(128, 4), (250, 90), (250, 252), (6, 252), (6, 90)]
        d.polygon(P(pent), fill=BLACK)
        d.polygon(P([(128, 14), (242, 94), (242, 244), (14, 244), (14, 94)]), fill=(200, 230, 30))
        for cx in (96, 160):
            d.ellipse([(cx - 14) * SS, 96 * SS, (cx + 14) * SS, 124 * SS], fill=BLACK)
            d.polygon(P([(cx - 18, 128), (cx + 18, 128), (cx + 22, 200), (cx - 22, 200)]), fill=BLACK)
            d.line(P([(cx - 10, 200), (cx - 16, 232)]), fill=BLACK, width=8 * SS)
            d.line(P([(cx + 10, 200), (cx + 16, 232)]), fill=BLACK, width=8 * SS)
    elif name == "back_pennant":
        d.polygon(P([(40, 6), (216, 6), (216, 200), (128, 250), (40, 200)]), fill=GREY)
    elif name in TRAM_FLAG:
        shape, bg, fg, acc, tag = TRAM_FLAG[name]
        if shape == "rect":
            d.rectangle([v * SS for v in (40, 6, 216, 250)], fill=bg)
            d.ellipse([v * SS for v in (68, 40, 188, 160)], outline=fg, width=6 * SS)
            tram_symbol(d, 128, 100, 0.8, fg)
            d.rectangle([v * SS for v in (40, 226, 216, 250)], fill=acc)
            text(d, (128, 196), tag, 30, fg)
        elif shape == "roundel":
            d.ellipse([v * SS for v in (14, 14, 242, 242)], fill=WHITE)
            d.ellipse([v * SS for v in (14, 14, 242, 242)], outline=bg, width=26 * SS)
            d.rectangle([v * SS for v in (4, 104, 252, 152)], fill=bg)
            tram_symbol(d, 128, 128, 0.42, fg)
            text(d, (128, 196), tag, 26, acc)
        elif shape == "pennant":
            d.polygon(P([(40, 6), (216, 6), (216, 200), (128, 250), (40, 200)]), fill=bg)
            tram_symbol(d, 128, 92, 0.85, fg)
            text(d, (128, 176), tag, 30, acc)
        elif shape == "shield":
            d.polygon(P([(40, 6), (216, 6), (216, 150), (128, 250), (40, 150)]), fill=bg)
            tram_symbol(d, 128, 80, 0.8, fg)
            d.rectangle([v * SS for v in (40, 140, 216, 172)], fill=fg)
            text(d, (128, 157), tag, 24, bg)
            d.polygon(P([(40, 6), (216, 6), (216, 20), (40, 20)]), fill=acc)
        elif shape == "disc":
            d.ellipse([v * SS for v in (6, 6, 250, 250)], fill=fg)
            d.ellipse([v * SS for v in (16, 16, 240, 240)], fill=bg)
            tram_symbol(d, 128, 110, 0.85, fg)
            text(d, (128, 196), tag, 30, acc)
        else:
            d.rectangle([v * SS for v in (14, 14, 242, 242)], fill=bg)
            tram_symbol(d, 128, 100, 0.85, fg)
            d.rectangle([v * SS for v in (14, 186, 242, 242)], fill=acc)
            text(d, (128, 214), tag, 30, fg)
    return im.resize((N, N), Image.LANCZOS)


def main():
    atlas = Image.new("RGBA", (8 * N, 8 * N), (0, 0, 0, 0))
    for k, name in enumerate(CELLS):
        atlas.alpha_composite(cell(name), ((k % 8) * N, (k // 8) * N))
    atlas.save(OUT)
    print(f"sign atlas: {len(CELLS)} faces -> {OUT}")


if __name__ == "__main__":
    main()
