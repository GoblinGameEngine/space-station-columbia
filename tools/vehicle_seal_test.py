#!/usr/bin/env python3
"""The seal test for modular vehicle bodies (research/vehicles/MODULAR_VEHICLES.md, the user's hard rule:
"zero gaps between panels at all times").

    python3 tools/vehicle_seal_test.py godot_project/remake/vehicles/tram/carrow_tram_mid.blueprint.json [...]

Assembles a body from its blueprint exactly as the game does (the component pack and catalog, each placement
at its anchor) and casts rays from points throughout the cabin, in many directions, against
  - the exterior shell alone (exterior panels; glazing, door leaves and door glass close their openings;
    the platform closes the bottom), and
  - the interior shell alone (interior panels; the same closures).
Each must seal on its own: a ray that gets out is a gap, reported with where it escaped. Allowed openings:
the joint portals (closed by the bellows to the next section).
"""
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..", "godot_project")
CLOSERS = {"glazing", "door_glass", "door_leaf", "reveal"}      # (the reveals join the two shells: part of both)
INTERIOR = {"lining_bay", "door_head_lining", "ceiling_bay", "floor", "podium", "end_lining", "cap_lining"}
EXTERIOR = {"side_bay", "door_head", "roof_bay", "end_portal", "end_cap", "wheel_well", "underpan"}


def res(p):
    return os.path.join(ROOT, p.replace("res://", ""))


def load_body(bp_path):
    bp = json.load(open(bp_path))
    std = bp["standard"]
    cats = {}
    cdir = os.path.join(ROOT, "remake", "vehicles", "components", std)
    packs = {}
    for f in os.listdir(cdir):
        if f.endswith(".catalog.json"):
            c = json.load(open(os.path.join(cdir, f)))
            for k, v in c["components"].items():
                v["pack"] = c["pack"]
                cats[k] = v
    tris = {}                                   # role set -> list of (n, 3, 3) arrays
    by_role = {}
    for mid, cid, anchor in bp["placements"]:
        e = cats[cid]
        if e["pack"] not in packs:
            packs[e["pack"]] = open(res(e["pack"]), "rb").read()
        data = packs[e["pack"]]
        for m, (off, n) in e["mats"].items():
            pos = np.frombuffer(data, dtype="<f4", count=n * 3, offset=off).reshape(-1, 3).copy()
            pos[:, 2] += anchor
            by_role.setdefault(e["role"], []).append((mid, pos.reshape(-1, 3, 3)))
    return bp, by_role


def gather(by_role, roles):
    parts = [t for r in roles for _, t in by_role.get(r, [])]
    return np.concatenate(parts) if parts else np.zeros((0, 3, 3))


def platform(bp):
    """The board's deck closes the bottom between the sills (two triangles at its top)."""
    z0 = -float(bp.get("length_front", 4.2)) - 0.1
    z1 = float(bp.get("length_back", 4.2)) + 0.1
    a, b, c, d = (-1.3, 0.49, z0), (1.3, 0.49, z0), (1.3, 0.49, z1), (-1.3, 0.49, z1)
    return np.array([[a, b, c], [a, c, d]], dtype=np.float32)


def fib_dirs(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = math.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)], 1).astype(np.float32)


def first_hit(orig, dirs, tri):
    """Möller-Trumbore, all rays against all triangles (chunked): the nearest hit distance per ray (inf: none)."""
    best = np.full(len(dirs), np.inf, dtype=np.float32)
    v0, e1, e2 = tri[:, 0], tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    for s in range(0, len(tri), 4000):
        a0, a1, a2 = v0[s:s + 4000], e1[s:s + 4000], e2[s:s + 4000]
        p = np.cross(dirs[:, None, :], a2[None])                     # (R, T, 3)
        det = np.einsum("rtk,tk->rt", p, a1)
        ok = np.abs(det) > 1e-9
        inv = np.where(ok, 1.0 / np.where(ok, det, 1), 0)
        tv = orig - a0                                               # (T, 3)
        u = np.einsum("rtk,tk->rt", p, tv) * inv
        q = np.cross(tv[None], a1[None])                              # (1, T, 3)
        v = np.einsum("rk,rtk->rt", dirs, np.broadcast_to(q, p.shape)) * inv
        t = np.einsum("tk,tk->t", a2, q[0])[None] * inv
        hit = ok & (u >= -1e-4) & (v >= -1e-4) & (u + v <= 1 + 1e-4) & (t > 1e-4)
        t = np.where(hit, t, np.inf)
        best = np.minimum(best, t.min(1))
    return best


def escapes(bp, tri, pts, dirs):
    out = []
    pw = 0.64
    for o in pts:
        o = np.asarray(o, dtype=np.float32)
        t = first_hit(o, dirs, tri)
        for k in np.nonzero(~np.isfinite(t))[0]:
            d = dirs[k]
            # where it leaves the body's box
            ts = []
            for ax, lim in ((0, 1.35), (1, 3.1), (2, 4.95)):
                if abs(d[ax]) > 1e-6:
                    for sgn in (-1, 1):
                        tt = (sgn * lim - o[ax]) / d[ax] if ax != 1 else ((lim if sgn > 0 else 0.0) - o[ax]) / d[ax]
                        if tt > 0:
                            ts.append(tt)
            p = o + d * min(ts)
            # out through a portal (to the next section's bellows) is allowed: where the ray crosses the end plane
            through = False
            for zend, is_portal in ((-4.2, bp["kind"] != "front"), (4.2, bp["kind"] != "rear")):
                if is_portal and abs(d[2]) > 1e-6:
                    tt = (zend - o[2]) / d[2]
                    if tt > 0:
                        q = o + d * tt
                        if abs(q[0]) < pw and 0.55 <= q[1] <= 2.62:
                            through = True
            if through:
                continue
            out.append((tuple(np.round(o, 2)), tuple(np.round(d, 2)), tuple(np.round(p, 2))))
    return out


def main():
    paths = sys.argv[1:] or [os.path.join(ROOT, "remake/vehicles/tram/carrow_tram_%s.blueprint.json" % k) for k in ("front", "mid", "rear")]
    dirs = fib_dirs(int(os.environ.get("SEAL_DIRS", "600")))
    total = 0
    for path in paths:
        bp, by_role = load_body(path)
        roles = set(by_role)
        unknown = roles - CLOSERS - INTERIOR - EXTERIOR - {"seat", "stanchion", "fittings", "ramp", "roof_fairing"}
        zf, zb = -float(bp["length_front"]), float(bp["length_back"])
        # points in the cabin itself (clear of the wheel housings, which are outside the shell)
        pts = [(x, y, z) for x in (-0.55, 0.0, 0.55) for y in (0.9, 1.8, 2.5) for z in np.linspace(zf + 0.5, zb - 0.5, int(os.environ.get("SEAL_ROWS", "7")))]
        for name, shell in (("exterior", EXTERIOR), ("interior", INTERIOR)):
            tri = np.concatenate([gather(by_role, shell | CLOSERS), platform(bp)])
            esc = escapes(bp, tri, pts, dirs)
            total += len(esc)
            print("%-6s %-8s %6d triangles: %s" % (bp["kind"], name, len(tri), "SEALED" if not esc else "%d rays escape" % len(esc)))
            # group the escapes by where they get out
            spots = {}
            for o, d, p in esc:
                key = (round(p[0] * 4) / 4, round(p[1] * 4) / 4, round(p[2] * 2) / 2)
                spots[key] = spots.get(key, 0) + 1
            for key, n in sorted(spots.items(), key=lambda kv: -kv[1])[:12]:
                print("        out near x %5.2f  y %4.2f  z %5.2f   (%d rays)" % (key[0], key[1], key[2], n))
        if unknown:
            print("        (roles in neither shell: %s)" % ", ".join(sorted(unknown)))
    print("TOTAL ESCAPES", total)
    sys.exit(1 if total else 0)


if __name__ == "__main__" and not os.environ.get("TUBES"):
    main()


# -- the tubes: never visible from outside --------------------------------------------------------------------
def frame_beams(bp, by_role, std):
    """The tube frame as the game builds it (TubeFrame.build): [a, b, diameter] in the section frame."""
    ring = std["ring"]
    names = [r[0] for r in ring]
    zs = list(bp["stations"])
    openings = {"R": [], "L": []}
    for d in bp["doors"]:
        openings[d["side"]].append((d["z"] - d["width"] / 2, d["z"] + d["width"] / 2, "door"))
    for mid, tris in by_role.get("glazing", []):
        side = "R" if tris[:, :, 0].mean() > 0.3 else ("L" if tris[:, :, 0].mean() < -0.3 else None)
        if side:
            openings[side].append((tris[:, :, 2].min(), tris[:, :, 2].max(), "window"))

    for ax in std["axles"]:
        for sd in ("R", "L"):
            openings[sd].append((-ax - std["arch_half"], -ax + std["arch_half"], "arch"))

    def touches(side, z0, z1, kind):
        return any(k == kind and min(z0, z1) < hi + 0.02 and max(z0, z1) > lo - 0.02 for lo, hi, k in openings.get(side, []))

    def open_at(side, z, kind):
        m = -0.03 if kind == "window" else 0.02
        return any(k == kind and lo + m < z < hi - m for lo, hi, k in openings.get(side, []))

    def jamb(side, z):
        for lo, hi, k in openings.get(side, []):
            if k == "door":
                if abs(z - lo) < 0.03:
                    return -0.035
                if abs(z - hi) < 0.03:
                    return 0.035
        return 0.0
    nodes = []
    n = len(ring)
    for ri, z in enumerate(zs):
        tip = False
        for nm, x, y in ring:
            if tip:
                x, y = x * 0.78, 0.45 + (y - 0.45) * 0.9
            zz = z
            if ri == 0 or ri == len(zs) - 1:
                zz += std.get("end_inset", 0.0) * (1 if ri == 0 else -1)
            if not tip and (nm.startswith("belt") or nm.startswith("head")) and len(nm) > 5:
                zz += jamb(nm[-1], z)
            nodes.append((x, y, zz))
    idx = names.index
    chain = ["skirt_R", "sill_R", "belt_R", "head_R", "cant_R", "roof_R", "crown", "roof_L", "cant_L", "head_L", "belt_L", "sill_L", "skirt_L"]
    segs = [(idx(chain[i]), idx(chain[i + 1])) for i in range(len(chain) - 1)] + [(idx("sill_L"), idx("floor_C")), (idx("floor_C"), idx("sill_R"))]
    md, bd = std["tubes"]["main_d"], std["tubes"]["brace_d"]
    beams = []
    for ri, z in enumerate(zs):
        for a, b in segs:
            na, nb = names[a], names[b]
            side = "R" if na.endswith("_R") or nb.endswith("_R") else ("L" if na.endswith("_L") or nb.endswith("_L") else "C")
            pair = {na.split("_")[0], nb.split("_")[0]}
            post, band, above = pair == {"sill", "belt"}, pair == {"belt", "head"}, pair == {"head", "cant"}
            if side != "C" and (post or band or above) and open_at(side, z, "door"):
                continue
            if side != "C" and band and open_at(side, z, "window"):
                continue
            if side != "C" and (pair & {"skirt", "sill"}) and open_at(side, z, "arch"):
                continue
            beams.append((ri * n + a, ri * n + b, md))
        if ri == 0:
            continue
        zm = (zs[ri - 1] + z) / 2
        for j in range(n):
            nm = names[j]
            if (nm.startswith("belt") or nm.startswith("head")) and open_at(nm[-1], zm, "door"):
                continue
            if (nm.startswith("skirt") or nm.startswith("sill")) and len(nm) > 5 and touches(nm[-1], zs[ri - 1], z, "arch"):
                continue
            beams.append(((ri - 1) * n + j, ri * n + j, md))
        for a, b in (("roof_R", "crown"), ("crown", "roof_L")):
            beams.append(((ri - 1) * n + idx(a), ri * n + idx(b), bd))
        if not touches("R", zs[ri - 1], z, "arch"):
            beams.append(((ri - 1) * n + idx("sill_R"), ri * n + idx("floor_C"), bd))
        if not touches("L", zs[ri - 1], z, "arch"):
            beams.append(((ri - 1) * n + idx("floor_C"), ri * n + idx("sill_L"), bd))
        for sd in ("R", "L"):
            if not open_at(sd, zm, "door") and not touches(sd, zs[ri - 1], z, "arch"):
                beams.append(((ri - 1) * n + idx("sill_" + sd), ri * n + idx("belt_" + sd), bd))
    return [(np.array(nodes[a]), np.array(nodes[b]), d) for a, b, d in beams]


def tube_test(path):
    bp, by_role = load_body(path)
    std = json.load(open(os.path.join(ROOT, "remake/vehicles/standards/%s.json" % bp["standard"])))
    beams = frame_beams(bp, by_role, std)
    # everything opaque hides a tube (both shells, reveals, doors, fittings); glass is see-through -- a tube
    # in view from outside through a window counts as seen
    opaque = set(by_role) - {"glazing", "door_glass", "ramp"}
    tri = np.concatenate([gather(by_role, opaque), platform(bp)])
    dirs = fib_dirs(160)
    seen = []
    for a, b, d in beams:
        ax = b - a
        L = np.linalg.norm(ax)
        if L < 1e-4:
            continue
        t = ax / L
        u = np.cross(t, [0, 1, 0] if abs(t[1]) < 0.9 else [1, 0, 0])
        u /= np.linalg.norm(u)
        v = np.cross(t, u)
        for s in (0.2, 0.5, 0.8):
            for k in range(4):
                ang = math.pi / 2 * k
                p = (a + ax * s + (u * math.cos(ang) + v * math.sin(ang)) * (d / 2)).astype(np.float32)
                hit = first_hit(p, dirs, tri)
                esc = ~np.isfinite(hit)
                # (out through a portal into the bellows isn't outside)
                ok = []
                for kk in np.nonzero(esc)[0]:
                    dd = dirs[kk]
                    through = False
                    for zend, is_portal in ((-4.2, bp["kind"] != "front"), (4.2, bp["kind"] != "rear")):
                        if is_portal and abs(dd[2]) > 1e-6:
                            tt = (zend - p[2]) / dd[2]
                            if tt > 0:
                                q = p + dd * tt
                                if abs(q[0]) < 0.64 and 0.55 <= q[1] <= 2.62:
                                    through = True
                    if not through:
                        ok.append(kk)
                if ok:
                    seen.append((tuple(np.round(p, 3)), len(ok)))
    print("%-6s tubes: %d members, %s" % (bp["kind"], len(beams), "HIDDEN from outside" if not seen else "%d points visible from outside" % len(seen)))
    for p, nrays in sorted(seen, key=lambda e: -e[1])[:12]:
        print("        tube point %s seen along %d directions" % (p, nrays))
    return len(seen)


if __name__ == "__main__" and os.environ.get("TUBES"):
    n = sum(tube_test(p) for p in (sys.argv[1:] or [os.path.join(ROOT, "remake/vehicles/tram/carrow_tram_%s.blueprint.json" % k) for k in ("front", "mid", "rear")]))
    print("TUBE POINTS SEEN", n)
