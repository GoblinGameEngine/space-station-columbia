"""
gbfurn.py -- parametric furniture/fixtures for remake interiors (shared code; sizes and
materials are passed per building so each interior is its own).  All pieces are built
into a gblib Part from boxes/cylinders.  pos = (x, y, z floor), yaw in degrees: the piece's
"front" (where a person stands/sits) faces local -Y rotated by yaw.
"""
import math

from mathutils import Vector


def F(pos, yaw):
    a = math.radians(yaw)
    u = Vector((math.cos(a), math.sin(a), 0))
    v = Vector((-math.sin(a), math.cos(a), 0))
    return (Vector(pos), u, v, Vector((0, 0, 1)))


def table(p, pos, yaw, w, d, h, mat, leg=0.05, top=0.035):
    f = F(pos, yaw)
    p.obox(f, (-w / 2, -d / 2, h - top), (w / 2, d / 2, h), mat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - leg - 0.03), sy * (d / 2 - leg - 0.03)
            p.obox(f, (x - leg / 2, y - leg / 2, 0), (x + leg / 2, y + leg / 2, h - top), mat)
    p.obox(f, (-w / 2 + 0.06, -d / 2 + 0.06, h - top - 0.08), (w / 2 - 0.06, -d / 2 + 0.08, h - top), mat)
    p.obox(f, (-w / 2 + 0.06, d / 2 - 0.08, h - top - 0.08), (w / 2 - 0.06, d / 2 - 0.06, h - top), mat)


def round_table(p, pos, r, h, mat):
    p.cylinder((pos[0], pos[1]), r, pos[2] + h - 0.035, pos[2] + h, mat, n=20)
    p.cylinder((pos[0], pos[1]), 0.05, pos[2], pos[2] + h - 0.035, mat, n=10)
    p.cylinder((pos[0], pos[1]), 0.25, pos[2], pos[2] + 0.04, mat, n=12)


def chair(p, pos, yaw, mat, seat=0.45, w=0.42, d=0.42, back=0.9):
    f = F(pos, yaw)
    p.obox(f, (-w / 2, -d / 2, seat - 0.035), (w / 2, d / 2, seat), mat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.03), sy * (d / 2 - 0.03)
            top = back if sy > 0 else seat - 0.035
            p.obox(f, (x - 0.02, y - 0.02, 0), (x + 0.02, y + 0.02, top), mat)
    for z in (seat + 0.18, back - 0.08):
        p.obox(f, (-w / 2 + 0.02, d / 2 - 0.035, z), (w / 2 - 0.02, d / 2 - 0.01, z + 0.06), mat)


def stool(p, pos, mat, seat_mat, h=0.76):
    p.cylinder((pos[0], pos[1]), 0.19, pos[2] + h - 0.06, pos[2] + h, seat_mat, n=14)
    p.cylinder((pos[0], pos[1]), 0.035, pos[2], pos[2] + h - 0.06, mat, n=8)
    p.cylinder((pos[0], pos[1]), 0.2, pos[2], pos[2] + 0.03, mat, n=12)
    p.cylinder((pos[0], pos[1]), 0.17, pos[2] + 0.3, pos[2] + 0.325, mat, n=12)


def bar_counter(p, pos, yaw, length, mat_body, mat_top, mat_rail, h=1.07, d=0.62):
    """Customer side faces local -Y: front panelling, overhanging top, brass foot rail."""
    f = F(pos, yaw)
    p.obox(f, (-length / 2, -d / 2 + 0.08, 0), (length / 2, d / 2, h - 0.05), mat_body)
    p.obox(f, (-length / 2 - 0.05, -d / 2 - 0.06, h - 0.05), (length / 2 + 0.05, d / 2 + 0.02, h), mat_top)
    p.obox(f, (-length / 2, d / 2 - 0.3, 0.8), (length / 2, d / 2 - 0.02, 0.84), mat_body)     # under-shelf (inside the
    #                                                   body: against a wall the back is the wall, 2026-10-07 audit)
    p.obox(f, (-length / 2, -d / 2 + 0.06, 0.02), (length / 2, -d / 2 + 0.08, 0.12), mat_body)  # kick
    for k in range(int(length / 0.6) + 1):
        x = -length / 2 + 0.1 + k * (length - 0.2) / max(1, int(length / 0.6))
        p.obox(f, (x - 0.12, -d / 2 + 0.078, 0.2), (x + 0.12, -d / 2 + 0.082, h - 0.15), mat_top)   # panels
    p.obox(f, (-length / 2, -d / 2 - 0.12, 0.18), (length / 2, -d / 2 - 0.08, 0.22), mat_rail)   # foot rail
    for x in (-length / 2 + 0.2, 0, length / 2 - 0.2):
        p.obox(f, (x - 0.02, -d / 2 - 0.1, 0.0), (x + 0.02, -d / 2 + 0.08, 0.2), mat_rail)


def back_bar(p, pos, yaw, length, mat, mirror_mat, glass_mat, h=2.4, d=0.5):
    f = F(pos, yaw)
    p.obox(f, (-length / 2, -d / 2, 0), (length / 2, d / 2, 0.95), mat)                 # base cabinet
    p.obox(f, (-length / 2 - 0.03, -d / 2 - 0.03, 0.95), (length / 2 + 0.03, d / 2, 0.99), mat)
    p.obox(f, (-length / 2, d / 2 - 0.08, 0.99), (length / 2, d / 2, h), mat)           # back panel
    p.obox(f, (-length / 2 + 0.2, d / 2 - 0.09, 1.25), (length / 2 - 0.2, d / 2 - 0.08, 2.05), mirror_mat)
    for z in (1.15, 1.5):                                                               # bottle shelves
        p.obox(f, (-length / 2 + 0.1, d / 2 - 0.3, z), (length / 2 - 0.1, d / 2 - 0.08, z + 0.025), mat)
    p.obox(f, (-length / 2 - 0.05, -0.05, h - 0.1), (length / 2 + 0.05, d / 2, h), mat)  # crown
    for x in (-length / 2, length / 2 - 0.1):
        p.obox(f, (x, 0.0, 0.99), (x + 0.1, d / 2, h - 0.1), mat)                         # columns
    # bottles
    n = int((length - 0.4) / 0.11)
    for s, z in enumerate((0.99, 1.175, 1.525)):
        for k in range(n):
            if (k * 7 + s * 3) % 5 == 0:
                continue
            x = -length / 2 + 0.25 + k * 0.11
            c = f[0] + f[1] * x + f[2] * (d / 2 - 0.2)
            p.cylinder((c.x, c.y), 0.035, f[0].z + z, f[0].z + z + 0.26 - (k % 3) * 0.03, glass_mat, n=8, r1=0.02)


def bed(p, pos, yaw, w, l, frame_mat, linen_mat, head_h=1.2):
    """Head against local +Y."""
    f = F(pos, yaw)
    p.obox(f, (-w / 2, -l / 2, 0.25), (w / 2, l / 2, 0.33), frame_mat)
    p.obox(f, (-w / 2 + 0.02, -l / 2 + 0.02, 0.33), (w / 2 - 0.02, l / 2 - 0.05, 0.55), linen_mat)
    p.obox(f, (-w / 2 + 0.1, l / 2 - 0.45, 0.55), (w / 2 - 0.1, l / 2 - 0.1, 0.65), linen_mat)
    p.obox(f, (-w / 2, l / 2 - 0.05, 0), (w / 2, l / 2, head_h), frame_mat)
    p.obox(f, (-w / 2, -l / 2, 0), (w / 2, -l / 2 + 0.05, 0.75), frame_mat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.obox(f, (sx * w / 2 - 0.03, sy * l / 2 - 0.03, 0), (sx * w / 2 + 0.03, sy * l / 2 + 0.03, 0.3), frame_mat)


def dresser(p, pos, yaw, w, d, h, mat, knob_mat, drawers=3, mirror_mat=None):
    f = F(pos, yaw)
    p.obox(f, (-w / 2, -d / 2, 0.08), (w / 2, d / 2, h), mat)
    p.obox(f, (-w / 2 - 0.02, -d / 2 - 0.02, h), (w / 2 + 0.02, d / 2 + 0.01, h + 0.03), mat)
    for k in range(drawers):
        z0 = 0.12 + k * (h - 0.16) / drawers
        z1 = z0 + (h - 0.16) / drawers - 0.03
        p.obox(f, (-w / 2 + 0.03, -d / 2 - 0.012, z0), (w / 2 - 0.03, -d / 2, z1), mat)
        for kx in (-w / 4, w / 4):
            p.obox(f, (kx - 0.02, -d / 2 - 0.03, (z0 + z1) / 2 - 0.015), (kx + 0.02, -d / 2 - 0.012, (z0 + z1) / 2 + 0.015), knob_mat)
    if mirror_mat:
        p.obox(f, (-w / 2 + 0.1, d / 2 - 0.04, h + 0.03), (w / 2 - 0.1, d / 2 - 0.01, h + 0.8), mat)
        p.obox(f, (-w / 2 + 0.15, d / 2 - 0.045, h + 0.08), (w / 2 - 0.15, d / 2 - 0.04, h + 0.75), mirror_mat)


def washstand(p, pos, yaw, mat, china_mat):
    f = F(pos, yaw)
    p.obox(f, (-0.38, -0.22, 0.05), (0.38, 0.22, 0.78), mat)
    p.obox(f, (-0.38, 0.17, 0.78), (0.38, 0.22, 0.95), mat)
    c = f[0] + f[1] * 0 + f[2] * 0
    p.cylinder((c.x, c.y), 0.2, f[0].z + 0.78, f[0].z + 0.86, china_mat, n=16, r1=0.24)      # basin
    c2 = f[0] + f[1] * 0.1
    p.cylinder((c2.x, c2.y), 0.08, f[0].z + 0.8, f[0].z + 1.05, china_mat, n=12, r1=0.06)     # pitcher


def shelves(p, pos, yaw, w, d, h, n, mat):
    f = F(pos, yaw)
    for sx in (-w / 2, w / 2 - 0.025):
        p.obox(f, (sx, -d / 2, 0), (sx + 0.025, d / 2, h), mat)
    p.obox(f, (-w / 2, d / 2 - 0.01, 0), (w / 2, d / 2, h), mat)
    for k in range(n):
        z = 0.08 + k * (h - 0.1) / max(1, n - 1)
        p.obox(f, (-w / 2, -d / 2, z), (w / 2, d / 2, z + 0.025), mat)


def keg(p, pos, mat, band_mat, lying=False):
    if lying:
        # approximated as an upright barrel's silhouette laid on a cradle -- kept upright here
        pass
    p.cylinder((pos[0], pos[1]), 0.24, pos[2], pos[2] + 0.55, mat, n=14)
    for z in (0.08, 0.47):
        p.cylinder((pos[0], pos[1]), 0.25, pos[2] + z, pos[2] + z + 0.03, band_mat, n=14)


def range_stove(p, pos, yaw, body_mat, top_mat, w=0.9, d=0.7):
    f = F(pos, yaw)
    p.obox(f, (-w / 2, -d / 2, 0.1), (w / 2, d / 2, 0.9), body_mat)
    p.obox(f, (-w / 2, -d / 2, 0.9), (w / 2, d / 2, 0.93), top_mat)
    p.obox(f, (-w / 2, d / 2 - 0.08, 0.93), (w / 2, d / 2, 1.2), body_mat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = f[0] + f[1] * (sx * w / 4) + f[2] * (sy * d / 5)
            p.cylinder((c.x, c.y), 0.1, f[0].z + 0.93, f[0].z + 0.95, top_mat, n=12)
    p.obox(f, (-w / 2 + 0.08, -d / 2 - 0.01, 0.2), (w / 2 - 0.08, -d / 2, 0.7), top_mat)     # oven door


def fryer(p, pos, yaw, body_mat, oil_mat):
    f = F(pos, yaw)
    p.obox(f, (-0.3, -0.35, 0), (0.3, 0.35, 0.9), body_mat)
    p.obox(f, (-0.25, -0.25, 0.86), (0.25, 0.25, 0.9), oil_mat)
    p.obox(f, (-0.3, 0.3, 0.9), (0.3, 0.35, 1.25), body_mat)


def sink_counter(p, pos, yaw, length, body_mat, top_mat, basin_mat, d=0.6):
    f = F(pos, yaw)
    p.obox(f, (-length / 2, -d / 2, 0.1), (length / 2, d / 2, 0.88), body_mat)
    p.obox(f, (-length / 2 - 0.02, -d / 2 - 0.03, 0.88), (length / 2, d / 2, 0.92), top_mat)
    p.obox(f, (-0.3, -0.2, 0.75), (0.3, 0.2, 0.921), basin_mat)
    p.obox(f, (-0.02, 0.18, 0.92), (0.02, 0.22, 1.2), basin_mat)
    p.obox(f, (-0.02, 0.05, 1.16), (0.02, 0.22, 1.2), basin_mat)
    for k in range(int(length / 0.45)):
        x = -length / 2 + 0.03 + k * 0.45
        p.obox(f, (x, -d / 2 - 0.01, 0.15), (x + 0.42, -d / 2, 0.82), body_mat)


def fridge(p, pos, yaw, body_mat, handle_mat, w=0.75, d=0.7, h=1.75):
    f = F(pos, yaw)
    p.obox(f, (-w / 2, -d / 2, 0), (w / 2, d / 2, h), body_mat)
    p.obox(f, (-w / 2 + 0.03, -d / 2 - 0.005, h * 0.62), (w / 2 - 0.03, -d / 2, h * 0.63), handle_mat)
    p.obox(f, (w / 2 - 0.1, -d / 2 - 0.04, h * 0.66), (w / 2 - 0.07, -d / 2, h * 0.9), handle_mat)


def bench(p, pos, yaw, length, mat, back=True):
    f = F(pos, yaw)
    p.obox(f, (-length / 2, -0.2, 0.42), (length / 2, 0.2, 0.46), mat)
    for x in (-length / 2 + 0.05, length / 2 - 0.1):
        p.obox(f, (x, -0.18, 0), (x + 0.05, 0.18, 0.42), mat)
    if back:
        p.obox(f, (-length / 2, 0.16, 0.46), (length / 2, 0.2, 0.9), mat)


def coat_rack(p, pos, mat):
    p.cylinder((pos[0], pos[1]), 0.025, pos[2], pos[2] + 1.8, mat, n=8)
    p.cylinder((pos[0], pos[1]), 0.22, pos[2], pos[2] + 0.03, mat, n=10)
    for a in range(4):
        ang = a * math.pi / 2
        x, y = pos[0] + 0.12 * math.cos(ang), pos[1] + 0.12 * math.sin(ang)
        p.box((min(pos[0], x) - 0.01, min(pos[1], y) - 0.01, pos[2] + 1.7), (max(pos[0], x) + 0.01, max(pos[1], y) + 0.01, pos[2] + 1.72), mat)


def mantel(p, pos, yaw, w, mat, firebox_mat, h=1.25, d=0.22, opening=(0.8, 0.8)):
    """Greek Revival pilaster-and-shelf mantel (Hassler Tavern sheet 2 details) around a firebox."""
    f = F(pos, yaw)
    ow, oh = opening
    p.obox(f, (-w / 2, -d, 0), (-ow / 2, 0, h - 0.1), mat)
    p.obox(f, (ow / 2, -d, 0), (w / 2, 0, h - 0.1), mat)
    p.obox(f, (-ow / 2, -d, oh), (ow / 2, 0, h - 0.1), mat)
    p.obox(f, (-w / 2 - 0.06, -d - 0.08, h - 0.1), (w / 2 + 0.06, 0, h), mat)
    p.obox(f, (-ow / 2, -0.02, 0), (ow / 2, 0.35, oh), firebox_mat)       # firebox back
    p.obox(f, (-ow / 2 - 0.1, -d - 0.35, -0.005), (ow / 2 + 0.1, -d, 0.01), firebox_mat)   # hearth


def stocked_shelves(p, pos, yaw, w, d, h, n, mat, goods_mats, seed=0, fill=0.8):
    """Wall shelving loaded with varied goods (boxes, cans, jars) -- deterministic per seed."""
    import random
    r = random.Random(seed)
    shelves(p, pos, yaw, w, d, h, n, mat)
    f = F(pos, yaw)
    for k in range(n - 1):
        z0 = 0.08 + k * (h - 0.1) / max(1, n - 1) + 0.025
        gap = (h - 0.1) / max(1, n - 1) - 0.06
        x = -w / 2 + 0.05
        while x < w / 2 - 0.1:
            gw = r.uniform(0.06, 0.2)
            if r.random() < fill:
                gh = min(gap, r.uniform(0.08, 0.3))
                gd = r.uniform(0.1, d - 0.05)
                m = r.choice(goods_mats)
                if r.random() < 0.35:
                    c = f[0] + f[1] * (x + gw / 2) + f[2] * (d / 2 - gd / 2 - 0.02)
                    p.cylinder((c.x, c.y), min(gw, gd) / 2, f[0].z + z0, f[0].z + z0 + gh, m, n=8)
                else:
                    p.obox(f, (x, d / 2 - gd - 0.02, z0), (x + gw, d / 2 - 0.02, z0 + gh), m)
            x += gw + 0.01


def display_case(p, pos, yaw, length, mat, glass_mat, h=0.95, d=0.6):
    """Store counter with a glazed front/top display (customer side local -Y)."""
    f = F(pos, yaw)
    p.obox(f, (-length / 2, -d / 2, 0), (length / 2, d / 2, 0.35), mat)
    p.obox(f, (-length / 2, -d / 2, 0.35), (length / 2, -d / 2 + 0.03, h), glass_mat)
    p.obox(f, (-length / 2, -d / 2, h - 0.02), (length / 2, d / 2, h), glass_mat)
    p.obox(f, (-length / 2, d / 2 - 0.05, 0.35), (length / 2, d / 2, h), mat)
    for x in (-length / 2, length / 2 - 0.04):
        p.obox(f, (x, -d / 2, 0.35), (x + 0.04, d / 2, h), mat)
    p.obox(f, (-length / 2 + 0.05, -d / 2 + 0.05, 0.6), (length / 2 - 0.05, d / 2 - 0.08, 0.62), mat)


def cash_register(p, pos, yaw, body_mat, key_mat):
    f = F(pos, yaw)
    p.obox(f, (-0.22, -0.2, 0), (0.22, 0.2, 0.18), body_mat)
    p.obox(f, (-0.2, -0.05, 0.18), (0.2, 0.2, 0.42), body_mat)
    p.obox(f, (-0.18, -0.2, 0.18), (0.18, -0.05, 0.24), key_mat)
    p.obox(f, (-0.15, 0.0, 0.42), (0.15, 0.12, 0.52), key_mat)


def barrel(p, pos, mat, band_mat, h=0.8, r=0.28, lid_mat=None):
    p.cylinder((pos[0], pos[1]), r * 0.9, pos[2], pos[2] + h, mat, n=14, r1=r * 0.9)
    p.cylinder((pos[0], pos[1]), r, pos[2] + h * 0.3, pos[2] + h * 0.7, mat, n=14)
    for z in (0.08, 0.45, 0.82):
        p.cylinder((pos[0], pos[1]), r * 0.95, pos[2] + h * z - 0.015, pos[2] + h * z + 0.015, band_mat, n=14)
    if lid_mat:
        p.cylinder((pos[0], pos[1]), r * 0.92, pos[2] + h, pos[2] + h + 0.02, lid_mat, n=14)


def potbelly_stove(p, pos, mat):
    x, y, z = pos
    p.cylinder((x, y), 0.22, z + 0.12, z + 0.35, mat, n=16)
    p.cylinder((x, y), 0.3, z + 0.35, z + 0.8, mat, n=16)
    p.cylinder((x, y), 0.24, z + 0.8, z + 1.0, mat, n=16, r1=0.12)
    p.cylinder((x, y), 0.07, z + 1.0, z + 2.3, mat, n=10)
    for a in range(4):
        ang = math.pi / 4 + a * math.pi / 2
        p.box((x + 0.18 * math.cos(ang) - 0.025, y + 0.18 * math.sin(ang) - 0.025, z), (x + 0.18 * math.cos(ang) + 0.025,
              y + 0.18 * math.sin(ang) + 0.025, z + 0.13), mat)


def platform_scale(p, pos, yaw, mat, metal_mat):
    f = F(pos, yaw)
    p.obox(f, (-0.3, -0.4, 0), (0.3, 0.4, 0.12), mat)
    p.obox(f, (-0.05, 0.3, 0.12), (0.05, 0.4, 1.1), metal_mat)
    p.obox(f, (-0.3, 0.33, 1.0), (0.3, 0.38, 1.05), metal_mat)


def sack_stack(p, pos, yaw, cols, rows, layers, mat):
    f = F(pos, yaw)
    for L in range(layers):
        for c in range(cols):
            for r_ in range(rows):
                off = 0.1 if L % 2 else 0.0
                x0 = -cols * 0.3 + c * 0.6 + off
                y0 = -rows * 0.21 + r_ * 0.42
                p.obox(f, (x0, y0, L * 0.16), (x0 + 0.56, y0 + 0.38, L * 0.16 + 0.15), mat)


def bin_row(p, pos, yaw, n, mat, fill_mats):
    """Open-topped hardware bins (nails, bolts) on a stand."""
    f = F(pos, yaw)
    p.obox(f, (-n * 0.2, -0.25, 0), (n * 0.2, 0.25, 0.7), mat)
    for k in range(n):
        x0 = -n * 0.2 + k * 0.4
        p.obox(f, (x0 + 0.02, -0.23, 0.7), (x0 + 0.38, 0.23, 0.9), mat)
        p.obox(f, (x0 + 0.04, -0.21, 0.8), (x0 + 0.36, 0.21, 0.86), fill_mats[k % len(fill_mats)])


def desk(p, pos, yaw, mat, knob_mat, w=1.4, d=0.75):
    f = F(pos, yaw)
    p.obox(f, (-w / 2, -d / 2, 0.72), (w / 2, d / 2, 0.76), mat)
    p.obox(f, (-w / 2, -d / 2 + 0.02, 0), (-w / 2 + 0.45, d / 2, 0.72), mat)
    p.obox(f, (w / 2 - 0.45, -d / 2 + 0.02, 0), (w / 2, d / 2, 0.72), mat)
    p.obox(f, (-w / 2 + 0.45, d / 2 - 0.03, 0.3), (w / 2 - 0.45, d / 2, 0.72), mat)
    for side in (-1, 1):
        for k in range(3):
            x = side * (w / 2 - 0.225)
            z = 0.1 + k * 0.2
            p.obox(f, (x - 0.02, -d / 2 - 0.02, z + 0.08), (x + 0.02, -d / 2, z + 0.1), knob_mat)


def safe(p, pos, yaw, mat, dial_mat):
    f = F(pos, yaw)
    p.obox(f, (-0.4, -0.35, 0.08), (0.4, 0.35, 1.2), mat)
    p.obox(f, (-0.35, -0.37, 0.15), (0.35, -0.35, 1.13), mat)
    p.obox(f, (-0.06, -0.4, 0.75), (0.06, -0.37, 0.87), dial_mat)
    for x in (-0.35, 0.3):
        p.obox(f, (x, -0.3, 0), (x + 0.05, 0.3, 0.08), mat)


def toilet(p, pos, yaw, china_mat, seat_mat):
    f = F(pos, yaw)
    p.obox(f, (-0.18, -0.25, 0), (0.18, 0.2, 0.38), china_mat)
    p.obox(f, (-0.2, -0.3, 0.38), (0.2, 0.2, 0.42), seat_mat)
    p.obox(f, (-0.23, 0.2, 0.38), (0.23, 0.38, 0.8), china_mat)


def sofa(p, pos, yaw, w, mat, frame_mat):
    f = F(pos, yaw)
    p.obox(f, (-w / 2, -0.45, 0.1), (w / 2, 0.45, 0.45), mat)
    p.obox(f, (-w / 2, 0.25, 0.45), (w / 2, 0.45, 0.9), mat)
    for x in (-w / 2, w / 2 - 0.15):
        p.obox(f, (x, -0.45, 0.45), (x + 0.15, 0.45, 0.65), mat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.obox(f, (sx * (w / 2 - 0.08) - 0.03, sy * 0.38 - 0.03, 0), (sx * (w / 2 - 0.08) + 0.03, sy * 0.38 + 0.03, 0.1), frame_mat)


def armchair(p, pos, yaw, mat, frame_mat):
    sofa(p, pos, yaw, 0.85, mat, frame_mat)


def radio(p, pos, yaw, mat, cloth_mat):
    """Floor-standing console radio (1930s-40s)."""
    f = F(pos, yaw)
    p.obox(f, (-0.35, -0.2, 0), (0.35, 0.2, 1.05), mat)
    p.obox(f, (-0.25, -0.21, 0.35), (0.25, -0.2, 0.8), cloth_mat)
    p.obox(f, (-0.2, -0.22, 0.85), (0.2, -0.2, 0.95), cloth_mat)


def gas_pump(p, pos, yaw, body_mat, globe_mat, chrome_mat, hose_mat):
    """Tall 1930s-style visible-register gasoline pump with a lighted globe on top."""
    f = F(pos, yaw)
    p.obox(f, (-0.3, -0.25, 0), (0.3, 0.25, 0.15), chrome_mat)
    p.obox(f, (-0.25, -0.2, 0.15), (0.25, 0.2, 1.75), body_mat)
    p.obox(f, (-0.18, -0.21, 1.0), (0.18, -0.2, 1.4), chrome_mat)            # dial face
    c = f[0]
    p.cylinder((c.x, c.y), 0.06, c.z + 1.75, c.z + 1.9, chrome_mat, n=10)
    p.cylinder((c.x, c.y), 0.2, c.z + 1.9, c.z + 2.3, globe_mat, n=16)
    p.obox(f, (0.25, -0.05, 0.9), (0.3, 0.05, 1.3), hose_mat)
    p.obox(f, (0.3, -0.03, 0.55), (0.34, 0.03, 1.3), hose_mat)
