#!/usr/bin/env python3
"""Every road's line made drivable (the user, 2026-10-09: "write an algorithm to correctly fix all of the roads and
paths including the minor ones ... every road must be traversable by every passenger vehicle"). What the road survey
(RoadSurvey: 1,692 surveyor cars over 1,227 km, research/roads/survey) found wrong with the lines themselves, fixed for
every road of every class, in godot_project/remake/terrain.json:

  1. de-stairing   a road traced off a raster zig-zags: points 2-4 m apart turning +-63 degrees at each (Grey Ledges Rd,
                   7,800 corners under an 8 m radius on the streets alone). Each road is simplified (Douglas-Peucker, TOL
                   m) -- its true line kept, the staircase gone -- then resampled to at most SEG m;
  2. rounding      every corner tighter than its class's least radius (MIN_R) becomes an arc (as tight as its legs
                   allow, never tighter than a car turns where they allow it);
  3. joining       a road that stops JOIN_MIN..JOIN_MAX m short of another, heading for it, is carried on to meet it
                   (the survey's "dangling_end");
  5. easing       no stretch of a road turns tighter than MIN_R: one that does is pulled smooth (see ease_bends);
  4. bridges       a great bridge's road laid straight across its span, eased back to its own line over EASE m each side
                   (GreatBridges builds the span straight between its ends; the road went on curving under it -- at the
                   Maumee Narrows Bridge 7 m off the deck, its right lane in the water: the survey's 110 "flooded").
Junctions are left where they are: any point within PROTECT m of another road keeps its place, so every road still meets
the ones it met. Run after tools/map_expanded.py, before placement.py (tools/regen_world.sh: step road_fix).
    python3 tools/road_fix.py [--dry]
"""
import json
import math
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GD = os.path.join(ROOT, "godot_project", "remake")
TOL = 0.7
SEG = 6.0
PROTECT = 4.0          # m: a point this near another road is at a junction (road_profile joins within 3 m): it stays
MIN_GAP = 1.0           # m: points closer than this to the last are jitter (kept: the ends)
SPIKE = 2.6             # rad: a turn sharper than this (~150 degrees) is a spike back on itself
JOIN_MIN, JOIN_MAX = 2.5, 12.0
JOIN_NEAR = 8.0
EASE = 40.0
MIN_R = {"hwy": 60.0, "county": 35.0, "main": 15.0, "gravel": 15.0, "street": 8.0, "alley": 6.0}
CELL = 32.0
DENSE = 1.5            # m: a bend's points while it's eased
DRIFT = 6.0            # m: the most an eased point moves off its road's own line (0.45 rmin: a right angle's arc --
DRIFT_MAX = 8.0        #    a gravel road's 15 m -- up to this)


def main(dry, after_placement=False):
    path = os.path.join(GD, "terrain.json")
    ter = json.load(open(path))
    # after placement.py (which snaps roads onto their crossings, and that leaves kinks): only clean and round, the
    # crossings' decks held where they are
    decks = []
    sites = {}                                               # the buildings by 32 m cell (after placement: easing keeps off them)
    if after_placement:
        for e in json.load(open(os.path.join(GD, "placement.json")))["structures"]:
            if e.get("kind") == "crossing" and "deck" in e:
                decks.append(e)
            elif "fmin" in e and e.get("kind") != "crossing":
                sites.setdefault((int((e["s"] % (2 * math.pi * ter["R"])) // 32.0), int(e["x"] // 32.0)), []).append(e)
    C = 2 * math.pi * ter["R"]
    wrap = lambda d: (d + C / 2) % C - C / 2
    roads = ter["roads"]

    # the points of every road by cell (for "near another road")
    def build_grid():
        g = {}
        for ri, rd in enumerate(roads):
            for k, p in enumerate(rd["pts"]):
                g.setdefault((int((p[0] % C) // CELL), int(p[1] // CELL)), []).append((ri, k))
        return g

    def segs_near(g, p, r, skip):
        """(distance, road, projected point, segment direction) to the nearest segment of each other road within r"""
        out = {}
        ci, cj = int((p[0] % C) // CELL), int(p[1] // CELL)
        rr = int(math.ceil(r / CELL))
        n = int(math.ceil(C / CELL))
        for di in range(-rr, rr + 1):
            for dj in range(-rr, rr + 1):
                for ri, k in g.get(((ci + di) % n, cj + dj), ()):
                    if ri == skip:
                        continue
                    pts = roads[ri]["pts"]
                    for k2 in (k - 1, k):
                        if k2 < 0 or k2 + 1 >= len(pts):
                            continue
                        a, b = pts[k2], pts[k2 + 1]
                        bs, bx = wrap(b[0] - a[0]), b[1] - a[1]
                        ps, px = wrap(p[0] - a[0]), p[1] - a[1]
                        l2 = bs * bs + bx * bx or 1e-9
                        t = max(0.0, min(1.0, (ps * bs + px * bx) / l2))
                        d = math.hypot(ps - bs * t, px - bx * t)
                        if d <= r and (ri not in out or d < out[ri][0]):
                            L = math.sqrt(l2)
                            out[ri] = (d, ri, (a[0] + bs * t, a[1] + bx * t), (bs / L, bx / L))
        return sorted(out.values())

    def pinned_at(q, ri):
        """at a junction (another road within PROTECT m) or on a crossing's deck: a point that keeps its place"""
        if segs_near(grid, (q[0] % C, q[1]), PROTECT, ri):
            return True
        for e in decks:
            ds_, dx_ = wrap(q[0] - e["s"]), q[1] - e["x"]
            if abs(ds_) < 60 and abs(dx_) < 60:
                c_, sn_ = math.cos(e["yaw"]), math.sin(e["yaw"])
                lx = dx_ * c_ + ds_ * sn_
                lz = dx_ * sn_ - ds_ * c_
                if e["fmin"][0] - 1 <= lx <= e["fmax"][0] + 1 and e["fmin"][1] - 3 <= lz <= e["fmax"][1] + 3:
                    return True
        return False

    def on_site(q, hw):
        """a building's footprint within hw of q"""
        ci, cj = int((q[0] % C) // 32.0), int(q[1] // 32.0)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for e in sites.get(((ci + di) % int(math.ceil(C / 32.0)), cj + dj), ()):
                    ds_, dx_ = wrap(q[0] - e["s"]), q[1] - e["x"]
                    c_, sn_ = math.cos(e["yaw"]), math.sin(e["yaw"])
                    lx = dx_ * c_ + ds_ * sn_
                    lz = dx_ * sn_ - ds_ * c_
                    if e["fmin"][0] - hw <= lx <= e["fmax"][0] + hw and e["fmin"][1] - hw <= lz <= e["fmax"][1] + hw:
                        return True
        return False

    def turn_rate(a, b, c):
        """the turn at b (rad per m) between its legs"""
        d1 = (b[0] - a[0], b[1] - a[1])
        d2 = (c[0] - b[0], c[1] - b[1])
        th = abs(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1]))
        return th / max(0.5 * (math.hypot(*d1) + math.hypot(*d2)), 1e-6)

    def ease_bends(line, rmin, ri, hw=0.0):
        rd_cls = roads[ri].get("cls")
        """5: no bend tighter than rmin anywhere along the line (the survey's 2,661 "bend", 2026-10-09: the corner fillets
        above shrink to fit short legs, and a line of short legs turns tighter than any one corner shows). The stretches
        that turn too fast are cut to DENSE m, their points pulled toward their neighbours' middle (each pass spreads the
        turn over more of the line: the radius grows) until none turns faster than 1/rmin -- a junction's or a deck's
        point held, none moved more than DRIFT m off the road's own line -- then thinned back (Douglas-Peucker, 5 cm)."""
        lim = 1.0 / rmin
        n = len(line)
        if n < 3 or all(turn_rate(line[k - 1], line[k], line[k + 1]) <= lim * 1.05 for k in range(1, n - 1)):
            return line
        # densified to <= DENSE m
        pts = [line[0]]
        for q in line[1:]:
            a = pts[-1]
            L = math.hypot(q[0] - a[0], q[1] - a[1])
            m = int(math.ceil(L / DENSE))
            for i in range(1, m + 1):
                pts.append((a[0] + (q[0] - a[0]) * i / m, a[1] + (q[1] - a[1]) * i / m))
        n = len(pts)
        held = [k == 0 or k == n - 1 or pinned_at(pts[k], ri) for k in range(n)]
        why = ["pin" if h_ else "" for h_ in held]
        home = list(pts)
        pts = [list(q) for q in pts]
        look = range(2, n - 2)
        for _ in range(400):
            bad = [k for k in look if not held[k] and (
                turn_rate(pts[k - 2], pts[k], pts[k + 2]) > lim or turn_rate(pts[k - 1], pts[k], pts[k + 1]) > lim)]
            if not bad:
                break
            look = sorted({j for k in bad for j in range(max(2, k - 3), min(n - 2, k + 4))})
            for k in bad:
                for j in (k - 1, k, k + 1):
                    if held[j]:
                        continue
                    mx = 0.5 * (pts[j - 1][0] + pts[j + 1][0])
                    my = 0.5 * (pts[j - 1][1] + pts[j + 1][1])
                    was = (pts[j][0], pts[j][1])
                    pts[j][0] += 0.5 * (mx - pts[j][0])
                    pts[j][1] += 0.5 * (my - pts[j][1])
                    if sites and on_site(pts[j], hw) and not on_site(was, hw):
                        pts[j][0], pts[j][1] = was           # (into a building: it stays)
                        held[j] = True
                        why[j] = "site"
                    elif math.hypot(pts[j][0] - home[j][0], pts[j][1] - home[j][1]) > min(DRIFT_MAX, max(DRIFT, 0.45 * rmin)):
                        held[j] = True                       # (as far off its line as it may go)
                        why[j] = "drift"
        stats["eased"] += 1
        stats["still_tight"] += sum(1 for k in range(2, n - 2) if not held[k] and turn_rate(pts[k - 2], pts[k], pts[k + 2]) > lim * 1.1)
        for k in range(2, n - 2):
            if held[k] and turn_rate(pts[k - 2], pts[k], pts[k + 2]) > lim * 1.1:
                stats["tight_held"] += 1
                stats["tight_" + why[k] + "_" + str(rd_cls)] = stats.get("tight_" + why[k] + "_" + str(rd_cls), 0) + 1
        # thinned: every held point kept, the rest to within 5 cm
        keep = [held[k] for k in range(n)]

        anchors = [k for k in range(n) if keep[k]]
        todo = list(zip(anchors, anchors[1:]))
        while todo:
            i, j = todo.pop()
            if j <= i + 1:
                continue
            a, b = pts[i], pts[j]
            bs, bx = b[0] - a[0], b[1] - a[1]
            L = math.hypot(bs, bx) or 1e-9
            far, fk = -1.0, -1
            for k in range(i + 1, j):
                d = abs((pts[k][0] - a[0]) * bx - (pts[k][1] - a[1]) * bs) / L
                if d > far:
                    far, fk = d, k
            if far > 0.05 or L > SEG:
                if far <= 0.05:
                    fk = (i + j) // 2                        # (straight but too long a leg: halved)
                keep[fk] = True
                todo += [(i, fk), (fk, j)]
        return [tuple(pts[k]) for k in range(n) if keep[k]]

    grid = build_grid()
    stats = {"eased": 0, "still_tight": 0, "tight_held": 0, "points_before": sum(len(r["pts"]) for r in roads), "rounded": 0, "joined": 0, "bridges": 0, "destaired": 0}

    # 1 + 2: each road's own line (unwrapped from its first point), its junction points pinned
    for ri, rd in enumerate(roads):
        pts = rd["pts"]
        if len(pts) < 3 or rd.get("cls") == "rail":
            continue
        u = [(pts[0][0], pts[0][1])]
        for q in pts[1:]:
            u.append((u[-1][0] + wrap(q[0] - u[-1][0]), q[1]))
        # jitter (points under MIN_GAP apart) and spikes (turning back on itself) out -- but never a point at a junction:
        # a spur out to a junction and back is how some roads meet the next (the map's Camino Real, Ledgewood Ct): taking
        # its tip off cut 30 neighbourhoods off the network (bake_paths: components 23 -> 34, Tamarack's 515 junctions)
        at_jn = {k for k, q in enumerate(u) if segs_near(grid, (q[0] % C, q[1]), PROTECT, ri)}
        clean = [u[0]]
        cj = [True]
        for k in range(1, len(u) - 1):
            q = u[k]
            if k in at_jn or math.hypot(q[0] - clean[-1][0], q[1] - clean[-1][1]) >= MIN_GAP:
                clean.append(q)
                cj.append(k in at_jn)
        clean.append(u[-1])
        cj.append(True)
        changed = True
        while changed and len(clean) > 2:
            changed = False
            for k in range(1, len(clean) - 1):
                if cj[k]:
                    continue
                a, b, c = clean[k - 1], clean[k], clean[k + 1]
                d1 = (b[0] - a[0], b[1] - a[1])
                d2 = (c[0] - b[0], c[1] - b[1])
                if abs(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1])) > SPIKE:
                    del clean[k]
                    del cj[k]
                    changed = True
                    break
        u = clean
        pts = [[q[0] % C, q[1]] for q in u]
        pinned = [False] * len(u)
        pinned[0] = pinned[-1] = True
        for k, q in enumerate(pts):
            if segs_near(grid, q, PROTECT, ri):
                pinned[k] = True
            for e in decks:                                  # (on a crossing's deck or its approach slab)
                ds_, dx_ = wrap(q[0] - e["s"]), q[1] - e["x"]
                if abs(ds_) < 60 and abs(dx_) < 60:
                    c_, sn_ = math.cos(e["yaw"]), math.sin(e["yaw"])
                    lx = dx_ * c_ + ds_ * sn_
                    lz = dx_ * sn_ - ds_ * c_
                    if e["fmin"][0] - 1 <= lx <= e["fmax"][0] + 1 and e["fmin"][1] - 3 <= lz <= e["fmax"][1] + 3:
                        pinned[k] = True
        # Douglas-Peucker between pinned points
        keep = [False] * len(u)
        for k in range(len(u)):
            keep[k] = pinned[k]

        def dp(i, j):
            if j <= i + 1:
                return
            a, b = u[i], u[j]
            bs, bx = b[0] - a[0], b[1] - a[1]
            L = math.hypot(bs, bx) or 1e-9
            far, fk = -1.0, -1
            for k in range(i + 1, j):
                d = abs((u[k][0] - a[0]) * bx - (u[k][1] - a[1]) * bs) / L
                if d > far:
                    far, fk = d, k
            if far > TOL:
                keep[fk] = True
                dp(i, fk)
                dp(fk, j)
        anchors = [k for k in range(len(u)) if keep[k]]
        if not after_placement:
            for i, j in zip(anchors, anchors[1:]):
                dp(i, j)
        else:
            keep = [True] * len(u)
        v = [u[k] for k in range(len(u)) if keep[k]]
        vp = [pinned[k] for k in range(len(u)) if keep[k]]
        if len(v) < len(u):
            stats["destaired"] += 1
        # rounding: each unpinned corner tighter than MIN_R, as an arc
        rmin = MIN_R.get(rd.get("cls"), 8.0)
        out = [v[0]]
        outp = [True]
        for k in range(1, len(v) - 1):
            a, b, c = v[k - 1], v[k], v[k + 1]
            d1 = (b[0] - a[0], b[1] - a[1])
            d2 = (c[0] - b[0], c[1] - b[1])
            l1, l2 = math.hypot(*d1), math.hypot(*d2)
            if l1 < 1e-6 or l2 < 1e-6:
                continue
            th = abs(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1]))
            if vp[k] or th < 0.08:
                out.append(b)
                outp.append(vp[k])
                continue
            tan_d = min(rmin * math.tan(th / 2), 0.48 * min(l1, l2))
            rad = tan_d / math.tan(th / 2)
            if rad >= rmin * 0.999 and th < 0.2:
                out.append(b)
                outp.append(False)
                continue
            u1 = (d1[0] / l1, d1[1] / l1)
            u2 = (d2[0] / l2, d2[1] / l2)
            p0 = (b[0] - u1[0] * tan_d, b[1] - u1[1] * tan_d)
            p1 = (b[0] + u2[0] * tan_d, b[1] + u2[1] * tan_d)
            cross = d1[0] * d2[1] - d1[1] * d2[0]
            nrm = (-u1[1], u1[0]) if cross > 0 else (u1[1], -u1[0])
            cen = (p0[0] + nrm[0] * rad, p0[1] + nrm[1] * rad)
            a0 = math.atan2(p0[1] - cen[1], p0[0] - cen[0])
            a1 = math.atan2(p1[1] - cen[1], p1[0] - cen[0])
            sw = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            m = max(2, int(math.ceil(abs(sw) * rad / 2.0)))
            for i in range(m + 1):
                ang = a0 + sw * i / m
                out.append((cen[0] + math.cos(ang) * rad, cen[1] + math.sin(ang) * rad))
                outp.append(False)
            stats["rounded"] += 1
        out.append(v[-1])
        outp.append(True)
        # long legs resampled to SEG m (the profile and the meshes like points along a road)
        res = [out[0]]
        for q in out[1:]:
            a = res[-1]
            L = math.hypot(q[0] - a[0], q[1] - a[1])
            n = int(L // SEG)
            for i in range(1, n + 1):
                f = i * SEG / L
                if L - i * SEG > 1.0:
                    res.append((a[0] + (q[0] - a[0]) * f, a[1] + (q[1] - a[1]) * f))
            if math.hypot(q[0] - res[-1][0], q[1] - res[-1][1]) > 0.2:
                res.append(q)
        res = ease_bends(res, rmin, ri, float(rd.get("w", 6.0)) * 0.5)
        if len(res) >= 2:                                    # (a stub of a road that would collapse keeps its line)
            rd["pts"] = [[round(q[0] % C, 2), round(q[1], 2)] for q in res]

    # 3: the ends that stop short of a road they're heading for
    grid = build_grid()
    for ri, rd in enumerate(roads):                       # (after placement too: its snapping leaves a few short)
        pts = rd["pts"]
        if len(pts) < 2 or rd.get("cls") == "rail":
            continue
        for end in (0, -1):
            tip = pts[end]
            prev = pts[1] if end == 0 else pts[-2]
            hd = (wrap(tip[0] - prev[0]), tip[1] - prev[1])
            L = math.hypot(*hd)
            if L < 1e-6:
                continue
            hd = (hd[0] / L, hd[1] / L)
            near = [n_ for n_ in segs_near(grid, tip, JOIN_MAX, ri) if roads[n_[1]].get("cls") != "rail"]
            if not near or near[0][0] < JOIN_MIN:
                continue                                     # (joined already, or nothing near)
            d, rj, q, _ = near[0]
            to = (wrap(q[0] - tip[0]), q[1] - tip[1])
            if (to[0] * hd[0] + to[1] * hd[1]) / max(d, 1e-6) < (0.7 if d > JOIN_NEAR else 0.0):
                continue                                     # (not heading for it: a dead end beside a road -- but one
                                                             #  within JOIN_NEAR m meets it however it points: Lakeshore Rd
                                                             #  6.4 m short of S 3rd St, its bridge cut off from the town)
            newp = [round(q[0] % C, 2), round(q[1], 2)]
            if end == 0:
                pts.insert(0, newp)
            else:
                pts.append(newp)
            stats["joined"] += 1

    # 4: the great bridges' roads straight across their spans
    br_path = os.path.join(GD, "bridges.json")
    bridges = json.load(open(br_path))["bridges"] if os.path.exists(br_path) and not after_placement else []
    for br in bridges:
        if br.get("road_class") == "rail" or str(br.get("id", "")).startswith("XRR"):
            continue
        A, B = br["ends"]
        ab = (wrap(B[0] - A[0]), B[1] - A[1])
        Lb = math.hypot(*ab)
        if Lb < 1.0:
            continue
        ax = (ab[0] / Lb, ab[1] / Lb)
        nx = (-ax[1], ax[0])
        # the road it carries: the one passing nearest both ends
        best, bri = 1e9, -1
        for ri, rd in enumerate(roads):
            if rd.get("cls") == "rail":
                continue
            da = min((math.hypot(wrap(p[0] - A[0]), p[1] - A[1]) for p in rd["pts"]), default=1e9)
            if da > 160:
                continue
            db = min((math.hypot(wrap(p[0] - B[0]), p[1] - B[1]) for p in rd["pts"]), default=1e9)
            if da + db < best:
                best, bri = da + db, ri
        if bri < 0:
            continue
        # the stretch between the points nearest the two ends becomes the span itself -- however far the road curved
        # between them (at the Maumee Narrows, 53 m off the 541 m span)
        rp = roads[bri]["pts"]
        ka = min(range(len(rp)), key=lambda k: math.hypot(wrap(rp[k][0] - A[0]), rp[k][1] - A[1]))
        kb = min(range(len(rp)), key=lambda k: math.hypot(wrap(rp[k][0] - B[0]), rp[k][1] - B[1]))
        lo, hi = min(ka, kb), max(ka, kb)
        P0, P1 = (A, B) if ka <= kb else (B, A)
        span = []
        n_ = max(1, int(Lb // SEG))
        for i in range(n_ + 1):
            f = i / n_
            span.append([round((P0[0] + wrap(P1[0] - P0[0]) * f) % C, 2), round(P0[1] + (P1[1] - P0[1]) * f, 2)])
        roads[bri]["pts"] = rp[:lo] + span + rp[hi + 1:]
        moved = True
        for p in roads[bri]["pts"]:
            rel = (wrap(p[0] - A[0]), p[1] - A[1])
            along = rel[0] * ax[0] + rel[1] * ax[1]
            off = rel[0] * nx[0] + rel[1] * nx[1]
            if along < -EASE or along > Lb + EASE or abs(off) > 25.0 or 0.0 <= along <= Lb:
                continue                                     # (the span itself is already on the line)
            w = 1.0 if 0.0 <= along <= Lb else 0.5 + 0.5 * math.cos(math.pi * (-along if along < 0 else along - Lb) / EASE)
            if abs(off) * w < 0.02:
                continue
            p[0] = round((p[0] - nx[0] * off * w) % C, 2)
            p[1] = round(p[1] - nx[1] * off * w, 2)
            moved = True
        stats["bridges"] += moved

    stats["points_after"] = sum(len(r["pts"]) for r in roads)
    print("road_fix:", stats)
    if not dry:
        json.dump(ter, open(path, "w"), indent=0)


if __name__ == "__main__":
    main("--dry" in sys.argv, "--after-placement" in sys.argv)
