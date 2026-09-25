"""The road network's joins (Space Station Columbia road standard SSC-RS 1, §6 -- research/roads/).

Every road end is made to meet another road at a real junction:
  snap      an end already on or beside another road is run on to that road's centreline
  extend    an end short of a road (a ray along its own heading hits one within REACH m, or the
            nearest road is within NEAR m) is carried on to it, if the way is clear -- no building,
            no sea, great river or lake (creeks are fine: the bridge scan gives them a small bridge)
  turn      an end with nowhere to go (a road stopped by a great river's basin, a town street at the
            sea) ends in a turning circle -- the only dead end the standard allows

Roads are [pts, cls, name] lists (pts: (s, x) tuples); the ring's seam is handled with wrapped
differences, and a join across it keeps its s continuous (s may run past C, as the map's own do).
"""
import math

CELL = 20.0
NEAR = 60.0            # an end this close to a road joins it
REACH = 320.0          # a ray along the end's heading reaches this far
OWN_SKIP = 80.0        # a road's own points this far back along it from the end don't count
SNAP_PAD = 2.0         # an end within the other road's half width + this is already on it


class Network:
    def __init__(self, roads, C, clear, widths, dead_ends=()):
        """roads: [[pts, cls, name], ...] (mutated in place).  clear(s, x) -> bool: may a new road
        piece pass here.  widths: cls -> carriageway width."""
        self.roads, self.C, self.clear, self.W = roads, C, clear, widths
        self.dead_ends = list(dead_ends)   # (s, x): planned cul-de-sacs -- an end there stays
        self.grid = {}
        self.keys = {}             # road -> the grid cells holding its points
        self.turns = []            # (s, x, r, cls): turning circles
        self.log = {"snap": 0, "extend": 0, "turn": 0, "ok": 0}
        for i in range(len(roads)):
            self._index(i)

    # ------------------------------------------------------------------ geometry
    def wd(self, a):
        return (a + self.C / 2) % self.C - self.C / 2

    def _key(self, p):
        return int(math.floor((p[0] % self.C) / CELL)), int(math.floor(p[1] / CELL))

    def _index(self, i, start=0):
        pts = self.roads[i][0]
        ks = self.keys.setdefault(i, set())
        for k in range(start, len(pts)):
            key = self._key(pts[k])
            self.grid.setdefault(key, []).append((i, k))
            ks.add(key)

    def _arc_from_end(self, pts, k, end):
        """Arc length along the road from its `end` (0 = first point, -1 = last) to point k (approx.)."""
        n = len(pts)
        j = k if end == 0 else n - 1 - k
        if j <= 0:
            return 0.0
        step = self._len(pts) / max(1, n - 1)
        return j * step

    def _len(self, pts):
        return sum(math.hypot(self.wd(b[0] - a[0]), b[1] - a[1]) for a, b in zip(pts, pts[1:]))

    def nearest(self, p, reach, skip=None):
        """(distance, point on the centreline (s continuous with p), road index) of the nearest
        road point within reach; skip = (road, end) ignores that road's own last OWN_SKIP m."""
        best = (1e18, None, None)
        ci, cj = self._key(p)
        r = int(math.ceil(reach / CELL))
        ncol = int(math.ceil(self.C / CELL))
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                for i, k in self.grid.get(((ci + di) % ncol, cj + dj), ()):
                    pts = self.roads[i][0]
                    if skip and i == skip[0] and self._arc_from_end(pts, k, skip[1]) < OWN_SKIP:
                        continue
                    for k2 in (k - 1, k):
                        if k2 < 0 or k2 + 1 >= len(pts):
                            continue
                        if skip and i == skip[0] and self._arc_from_end(pts, k2, skip[1]) < OWN_SKIP:
                            continue
                        d, q = self._seg(p, pts[k2], pts[k2 + 1])
                        if d < best[0]:
                            best = (d, q, i)
        return best

    def _seg(self, p, a, b):
        bx, by = self.wd(b[0] - a[0]), b[1] - a[1]
        px, py = self.wd(p[0] - a[0]), p[1] - a[1]
        L2 = bx * bx + by * by or 1e-9
        t = max(0.0, min(1.0, (px * bx + py * by) / L2))
        qx, qy = bx * t, by * t
        d = math.hypot(px - qx, py - qy)
        # the point, with s continuous with p
        return d, (p[0] + (qx - px), a[1] + qy)

    def _way_clear(self, a, b, skip_first=4.0):
        L = math.hypot(self.wd(b[0] - a[0]), b[1] - a[1])
        n = max(1, int(L / 2.0))
        for k in range(n + 1):
            t = k / n
            if t * L < skip_first:
                continue
            p = (a[0] + self.wd(b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            if not self.clear(*p):
                return False
        return True

    def _ray(self, e, u, i_self, end):
        """First road the ray from e along u meets within REACH: (distance along, hit point)."""
        t = 6.0
        while t <= REACH:
            p = (e[0] + u[0] * t, e[1] + u[1] * t)
            d, q, j = self.nearest(p, 20.0, skip=(i_self, end))
            if j is not None and d <= self.W[self.roads[j][1]] * 0.5:
                return t, q
            t += 3.0
        return None

    # ------------------------------------------------------------------ joins
    def join_all(self, order):
        """Every road end, the more important classes first (a lesser road joins a greater one)."""
        idxs = sorted(range(len(self.roads)), key=lambda i: order.index(self.roads[i][1]))
        for i in idxs:
            for end in (0, -1):
                self._join(i, end)
        return self

    def _join(self, i, end):
        pts, cls, _ = self.roads[i]
        if len(pts) < 2:
            return
        e = pts[end]
        if any(math.hypot(self.wd(e[0] - c[0]), e[1] - c[1]) < 18.0 for c in self.dead_ends):
            self.log["ok"] += 1
            return
        # heading out of the end (over the last ~12 m)
        back = pts[min(len(pts) - 1, 3)] if end == 0 else pts[max(0, len(pts) - 4)]
        u = (self.wd(e[0] - back[0]), e[1] - back[1])
        L = math.hypot(*u) or 1.0
        u = (u[0] / L, u[1] / L)
        d, q, j = self.nearest(e, NEAR + 20.0, skip=(i, end))
        if j is not None and d <= self.W[self.roads[j][1]] * 0.5 + SNAP_PAD:
            if d > 0.3:
                self._append(i, end, [q])
                self.log["snap"] += 1
            else:
                self.log["ok"] += 1
            return
        # the heading ray first (a road carried straight on reads best), then the nearest road
        hit = self._ray(e, u, i, end)
        if hit and hit[0] <= max(NEAR * 1.5, d * 2.5 if j is not None else REACH) and self._way_clear(e, hit[1]):
            self._append(i, end, self._fill(e, hit[1]))
            self.log["extend"] += 1
            return
        if j is not None and d <= NEAR and self._way_clear(e, q):
            self._append(i, end, self._fill(e, q))
            self.log["extend"] += 1
            return
        if hit and self._way_clear(e, hit[1]):
            self._append(i, end, self._fill(e, hit[1]))
            self.log["extend"] += 1
            return
        self.turns.append((e[0] % self.C, e[1], max(9.0, self.W[cls] * 1.4), cls))
        self.log["turn"] += 1

    def _fill(self, a, b, step=6.0):
        L = math.hypot(self.wd(b[0] - a[0]), b[1] - a[1])
        n = max(1, int(L / step))
        return [(a[0] + self.wd(b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1)]

    def _append(self, i, end, new):
        pts = self.roads[i][0]
        if end == 0:
            self.roads[i][0] = list(reversed(new)) + list(pts)
            # the whole road's indices shift: reindex it
            for key in self.keys.pop(i, ()):
                self.grid[key] = [(a, k) for a, k in self.grid[key] if a != i]
            self._index(i)
        else:
            n0 = len(pts)
            self.roads[i][0] = list(pts) + list(new)
            self._index(i, n0)

    # ------------------------------------------------------------------ islands
    def components(self):
        """Road index -> component id (roads meeting within their half widths are joined)."""
        parent = list(range(len(self.roads)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for i, (pts, cls, _) in enumerate(self.roads):
            for p in pts[::2] + [pts[-1]]:
                ci, cj = self._key(p)
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        for j, k in self.grid.get((ci + di, cj + dj), ()):
                            if j == i or find(j) == find(i):
                                continue
                            q = self.roads[j][0][k]
                            if math.hypot(self.wd(q[0] - p[0]), q[1] - p[1]) < (self.W[cls] + self.W[self.roads[j][1]]) * 0.5 + 4.0:
                                parent[find(j)] = find(i)
        return [find(i) for i in range(len(self.roads))]

    def connect_islands(self, max_len=1500.0, name_of=None):
        """Every group of roads cut off from the main network gets the shortest clear road to it."""
        import numpy as np
        comp = self.components()
        size = {}
        for i, c in enumerate(comp):
            size[c] = size.get(c, 0.0) + self._len(self.roads[i][0])
        main = max(size, key=size.get)
        added = 0
        # the smallest first, each to the nearest road not its own (an island village's stray street
        # joins its village; a village joins the main network where a clear way exists)
        for c in sorted(size, key=size.get):
            if c == main:
                continue
            mine = [i for i, cc in enumerate(comp) if cc == c]
            ipts = [p for i in mine for p in self.roads[i][0][::2]]
            others = np.array([p for i, cc in enumerate(comp) if cc != c for p in self.roads[i][0][::2]])
            owner = [cc for i, cc in enumerate(comp) if cc != c for p in self.roads[i][0][::2]]
            cands = []
            for p in ipts:
                ds = (others[:, 0] - p[0] + self.C / 2) % self.C - self.C / 2
                d = np.hypot(ds, others[:, 1] - p[1])
                near = np.nonzero(d <= max_len)[0]
                for k in near[np.argsort(d[near])][:40:4]:
                    cands.append((float(d[k]), p, (p[0] + float(ds[k]), float(others[k, 1])), owner[k]))
            cands.sort(key=lambda t: t[0])
            for d, p, q, joined in cands[:600]:
                if self._way_clear(p, q, skip_first=0.0):
                    cls = "street" if d < 150 else "county"
                    self.roads.append([[p] + self._fill(p, q), cls, name_of(p) if name_of else ""])
                    self._index(len(self.roads) - 1)
                    added += 1
                    for i in mine:                    # it now belongs to what it joined
                        comp[i] = joined
                    break
        self.log["island_links"] = added
        self.log["islands"] = len(size) - 1
        return self
