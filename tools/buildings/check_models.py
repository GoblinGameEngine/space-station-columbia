#!/usr/bin/env python3
"""check_models.py -- mesh-level checks on the game's building models (the user, 2026-10-09: "You need to have tools that
you can use to check that every model is manifold"). Reads the shipped glbs in godot_project/remake/buildings (numpy, no
Blender), so it checks exactly what the game draws. Complements remake/blender/gbaudit.py, which runs at build time on
the plan (rooms sealed, furniture inside the walls, door leaves solid) and passes on all 8,085 planned buildings.

Each building's visual mesh is welded by position (glTF splits a vertex wherever its normal or UV changes) and cut into
pieces (connected parts: a window's sash, a chair, a wall run). Per piece:

  open_solid     a piece that isn't flat but has open edges: a hole in a solid (a box missing a face)
  nonmanifold    an edge shared by more than two triangles (a fin, two solids welded along an edge)
  inside_out     a closed piece whose volume is negative: its faces wound inward (dark, lit from inside)
  flipped        triangles whose winding disagrees with their own vertex normals (lit wrong)
Per mesh:
  degenerate     zero-area triangles (waste; break normals and collision)
  duplicate      the same triangle twice, same way round (z-fighting)
  zfight         two triangles of DIFFERENT pieces in one plane, facing the same way, overlapping (flicker)
  bad_number     a NaN or infinite coordinate
Open flat pieces (glass, decals, floor finishes, one-sided planes) are counted, not flagged.

    python3 tools/buildings/check_models.py [ID ...] [--all] [--lods] [--jobs N] [--report PATH]

Writes a JSON report (default reference/tmp/model_check.json): per building its counts and the worst places (positions
in the glb frame), and prints a summary by defect and by building family.
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glbmesh import Glb, components, weld, world_prims  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
BUILDINGS = os.path.join(ROOT, "godot_project", "remake", "buildings")
REPORT = os.path.join(ROOT, "reference", "tmp", "model_check.json")
FLAT_TOL = 0.002        # m: a piece this close to one plane is a sheet (open edges are fine)
AREA_EPS = 1e-8         # m^2: below this a triangle is degenerate
ZF_PLANE = 0.002        # m: two faces this close to the same plane z-fight
DEFECTS = ("open_solid", "nonmanifold", "inside_out", "flipped", "degenerate", "duplicate", "zfight", "bad_number")


def check(path):
    g = Glb(path)
    Ps, Ns, Is, Ms = [], [], [], []
    base = 0
    for node, mesh, P, N, U, I, mat in world_prims(g, lambda n: not n.endswith("-colonly") and "collision" not in n):
        Ps.append(P)
        Ns.append(N if N is not None else np.zeros_like(P))
        Is.append(I + base)
        Ms.append(np.full(len(I), len(Ms)))
        base += len(P)
    out = {"id": os.path.basename(path)[:-4], "counts": Counter(), "where": defaultdict(list), "pieces": 0, "sheets": 0, "tris": 0}
    if not Ps:
        return out
    P = np.concatenate(Ps)
    N = np.concatenate(Ns)
    I = np.concatenate(Is)
    out["tris"] = int(len(I))
    c = out["counts"]
    w = out["where"]

    def note(kind, n, at=None):
        c[kind] += int(n)
        if at is not None and len(w[kind]) < 6:
            w[kind].append([round(float(v), 2) for v in at])

    bad = ~np.isfinite(P).all(1)
    if bad.any():
        note("bad_number", bad.sum(), [0, 0, 0])
        P = np.nan_to_num(P)
    W = weld(P)
    T = W[I]                                                  # triangles over welded vertices
    a, b, cc = P[I[:, 0]], P[I[:, 1]], P[I[:, 2]]
    fn = np.cross(b - a, cc - a)
    area2 = np.linalg.norm(fn, axis=1)
    degen = (area2 < 2 * AREA_EPS) | (T[:, 0] == T[:, 1]) | (T[:, 1] == T[:, 2]) | (T[:, 0] == T[:, 2])
    if degen.any():
        note("degenerate", degen.sum(), a[degen][0])
    ok = ~degen
    # duplicates: the same three welded vertices, same winding (rotations of one triangle are the same triangle)
    rot = np.argmin(T, axis=1)
    canon = np.stack([T[np.arange(len(T)), rot], T[np.arange(len(T)), (rot + 1) % 3], T[np.arange(len(T)), (rot + 2) % 3]], 1)
    _, first, cnt = np.unique(canon[ok], axis=0, return_index=True, return_counts=True)
    dup = cnt > 1
    if dup.any():
        note("duplicate", (cnt[dup] - 1).sum(), a[ok][first[dup][0]])
    # flipped: the face normal against its vertices' normals
    unit = fn / np.maximum(area2[:, None], 1e-12)
    vn = N[I[:, 0]] + N[I[:, 1]] + N[I[:, 2]]
    has_vn = np.linalg.norm(vn, axis=1) > 0.5
    flip = ok & has_vn & (np.einsum("ij,ij->i", unit, vn) < -0.3)
    if flip.any():
        note("flipped", flip.sum(), a[flip][0])
    # pieces over the welded topology
    T2 = T[ok]
    lab = components(T2, int(W.max()) + 1)
    plab = lab[T2[:, 0]]
    # edges: each undirected welded edge's uses one way round against the other. In a closed, consistently wound surface
    # they balance (two solids that touch along an edge use it twice each way: still balanced); an edge used more one
    # way than the other is open -- a hole's rim -- or a fin.
    nvw = int(W.max()) + 1
    e = np.concatenate([T2[:, [0, 1]], T2[:, [1, 2]], T2[:, [2, 0]]])
    fwd = e[:, 0] < e[:, 1]
    key = np.minimum(e[:, 0], e[:, 1]) * nvw + np.maximum(e[:, 0], e[:, 1])
    uk, inv = np.unique(key, return_inverse=True)
    bal = np.zeros(len(uk), np.int64)
    np.add.at(bal, inv, np.where(fwd, 1, -1))
    uses = np.bincount(inv)
    edge_piece = np.concatenate([plab, plab, plab])
    open_e = bal[inv] != 0
    nm_e = (uses[inv] > 2) & (bal[inv] != 0)                    # (more than two faces, and not in balanced pairs)
    pieces = np.unique(plab)
    out["pieces"] = int(len(pieces))
    Pw = np.zeros((nvw, 3))
    Pw[W] = P
    open_by = Counter(edge_piece[open_e].tolist())
    nm_by = Counter(edge_piece[nm_e].tolist())
    tri_order = np.argsort(plab, kind="stable")
    cuts = np.flatnonzero(np.diff(plab[tri_order])) + 1
    for grp in np.split(tri_order, cuts):
        pc = int(plab[grp[0]])
        vids = np.unique(T2[grp])
        pts = Pw[vids]
        ctr = pts.mean(0)
        if len(pts) >= 3:
            sv = np.linalg.svd(pts - ctr, full_matrices=False, compute_uv=False)
            thick = sv[-1] / max(np.sqrt(len(pts)), 1.0) * 2.0
        else:
            thick = 0.0
        flat = thick < FLAT_TOL
        if flat:
            out["sheets"] += 1
            continue
        if open_by.get(pc):
            note("open_solid", 1, ctr)
            out.setdefault("open_edges", 0)
            out["open_edges"] += open_by[pc] // 3 or 1
        if nm_by.get(pc):
            note("nonmanifold", 1, ctr)
        if not open_by.get(pc):
            tri = T2[grp]
            v0, v1, v2 = Pw[tri[:, 0]], Pw[tri[:, 1]], Pw[tri[:, 2]]
            vol = np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0
            if vol < -1e-6:
                note("inside_out", 1, ctr)
    # z-fighting: a triangle whose centroid lies inside a triangle of ANOTHER piece in the same plane, facing the same way
    okI = np.flatnonzero(ok)
    if len(okI):
        un = unit[okI]
        A, B, Cc = a[okI], b[okI], cc[okI]
        cen = (A + B + Cc) / 3.0
        dpl = np.einsum("ij,ij->i", un, cen)
        nq = np.round(un * 50).astype(np.int64)                 # (normals to ~1 degree)
        dq = np.round(dpl / ZF_PLANE).astype(np.int64)
        gk = {}
        for i, kk in enumerate(zip(nq[:, 0], nq[:, 1], nq[:, 2], dq)):
            gk.setdefault(kk, []).append(i)
        zf = 0
        for kk, idx in gk.items():
            if len(idx) < 2:
                continue
            idx = np.array(idx)
            pcs = plab[idx]
            if len(np.unique(pcs)) < 2:
                continue
            # in-plane frame
            n0 = un[idx[0]]
            ax = np.cross(n0, [0.0, 1.0, 0.0] if abs(n0[1]) < 0.9 else [1.0, 0.0, 0.0])
            ax /= np.linalg.norm(ax)
            ay = np.cross(n0, ax)
            def uv(X):
                return np.stack([X @ ax, X @ ay], 1)
            a2, b2, c2, m2 = uv(A[idx]), uv(B[idx]), uv(Cc[idx]), uv(cen[idx])
            lo = np.minimum(np.minimum(a2, b2), c2)
            hi = np.maximum(np.maximum(a2, b2), c2)
            for ii in range(len(idx)):
                cand = np.flatnonzero((pcs != pcs[ii]) & (lo[:, 0] <= m2[ii, 0]) & (hi[:, 0] >= m2[ii, 0])
                                      & (lo[:, 1] <= m2[ii, 1]) & (hi[:, 1] >= m2[ii, 1]))
                if not len(cand):
                    continue
                p = m2[ii]
                v0 = b2[cand] - a2[cand]
                v1 = c2[cand] - a2[cand]
                v2 = p - a2[cand]
                den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
                den = np.where(np.abs(den) < 1e-12, 1e-12, den)
                l1 = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
                l2 = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
                inside = (l1 > 0.01) & (l2 > 0.01) & (l1 + l2 < 0.99)
                if inside.any():
                    zf += 1
                    if len(w["zfight"]) < 6:
                        w["zfight"].append([round(float(v), 2) for v in cen[idx[ii]]])
        if zf:
            c["zfight"] += zf
    return out


def run(path):
    try:
        r = check(path)
        r["counts"] = dict(r["counts"])
        r["where"] = dict(r["where"])
        return r
    except Exception as ex:                                  # noqa: BLE001 -- a broken file is a finding, not a crash
        return {"id": os.path.basename(path)[:-4], "error": repr(ex), "counts": {}, "where": {}}


def main(argv):
    ids = [a for a in argv if not a.startswith("--")]
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 3
    report = argv[argv.index("--report") + 1] if "--report" in argv else REPORT
    lods = "--lods" in argv
    if "--jobs" in argv:
        ids.remove(str(jobs))
    if "--report" in argv:
        ids.remove(report)
    if "--all" in argv or not ids:
        files = sorted(f for f in os.listdir(BUILDINGS) if f.endswith(".glb") and (lods or ".lod" not in f))
    else:
        files = [i if i.endswith(".glb") else i + ".glb" for i in ids]
    paths = [os.path.join(BUILDINGS, f) for f in files]
    t0 = time.time()
    with Pool(jobs) as pool:
        res = pool.map(run, paths, chunksize=4)
    tot = Counter()
    fam = defaultdict(Counter)
    bad_b = Counter()
    for r in res:
        for k, v in r["counts"].items():
            tot[k] += v
            fam[r["id"].split("-")[0]][k] += v
            bad_b[k] += 1
    os.makedirs(os.path.dirname(report), exist_ok=True)
    json.dump({"checked": len(res), "seconds": round(time.time() - t0, 1), "totals": dict(tot), "buildings_with": dict(bad_b),
               "buildings": res}, open(report, "w"), separators=(",", ":"))
    print("checked %d models in %.0f s -> %s" % (len(res), time.time() - t0, report))
    errs = [r for r in res if "error" in r]
    for d in DEFECTS:
        print("  %-12s %8d   in %5d buildings" % (d, tot.get(d, 0), bad_b.get(d, 0)))
    print("  sheets (open flat pieces, fine) %d of %d pieces" % (sum(r.get("sheets", 0) for r in res), sum(r.get("pieces", 0) for r in res)))
    if errs:
        print("  unreadable: %d (%s)" % (len(errs), errs[0]["error"][:80]))
    worst = sorted(res, key=lambda r: -sum(r["counts"].get(d, 0) for d in DEFECTS[:4]))[:8]
    print("worst:", ", ".join("%s %s" % (r["id"], dict(r["counts"])) for r in worst if r["counts"]))


if __name__ == "__main__":
    main(sys.argv[1:])
