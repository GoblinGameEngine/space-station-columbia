#!/usr/bin/env python3
"""Prototype and calibration for the story engine's knowledge propagation
(research/psychology/06_story_engine_framework.md, section 4).

The problem: a player action should reach people by word of mouth (friend of a friend of a friend),
but our people exist only when met and nothing about them is stored. The answer here: make every
"would u tell v about event e?" coin and every "how long until they talk?" delay a pure hash of
(world seed, e, u, v). Then the whole spread is fixed in advance -- Kempe, Kleinberg & Tardos
(2003), Claim 2.3: under the independent-cascade model a node is reached iff a path of "live"
edges leads to it from the seeds -- and any one person's knowledge can be computed alone, on
contact, by a short backwards search, agreeing exactly with what a full simulation would give.

This script:
  1. builds a settlement's social graph from social foci (Feld 1981): households, workplaces,
     streets, school classes, clubs/congregations -- ties arise inside foci, weighted by homophily,
     sorted into Dunbar layers (5 / 15 / 50 / 150);
  2. spreads an event from its witnesses EAGERLY (forward, over everyone) and LAZILY (backwards
     from one asker at a time, hop-limited), and checks they agree for every person;
  3. prints calibration: share of the settlement that knows, by hop and by days, for events of
     different weight; and the cost of a lazy query (nodes touched).

    python3 tools/story/propagation_proto.py [seed] [population]
"""
import hashlib
import heapq
import math
import random
import sys
from collections import defaultdict

MAX_HOPS = 3                     # Christakis & Fowler's "three degrees" as a design horizon
LAYER_STRENGTH = {5: 0.9, 15: 0.7, 50: 0.45, 150: 0.25, "pub": 1.0}   # tie strength by Dunbar layer
LAYER_DAYS = {5: 0.15, 15: 0.6, 50: 2.5, 150: 8.0, "pub": 1.5}         # mean days between talks, by layer
PUBLIC = -1                      # the public channel (noticeboard, pub talk, station news): a
                                 # virtual witness beside everyone, open only to weighty events
HEARSAY = 0.75                   # salience kept per retelling


def h01(*parts):
    """A deterministic uniform [0,1) from any parts -- the 'coin' (stands in for fnv1a+splitmix)."""
    d = hashlib.blake2b("|".join(map(str, parts)).encode(), digest_size=8).digest()
    return int.from_bytes(d, "little") / 2 ** 64


# -- a settlement from social foci -------------------------------------------------------------

def build(seed, n):
    rng = random.Random(seed)
    people = []
    for i in range(n):
        age = rng.choice([rng.randint(0, 17), rng.randint(18, 64), rng.randint(18, 64), rng.randint(65, 90)])
        people.append({"id": i, "age": age, "E": rng.betavariate(4, 4), "A": rng.betavariate(4, 4),
                       "C": rng.betavariate(4, 4), "H": rng.betavariate(4, 4), "occ": rng.randrange(12)})
    foci = []
    i = 0
    while i < n:                                          # households of 1-5
        k = min(n - i, rng.choice([1, 2, 2, 3, 3, 4, 5]))
        foci.append(("household", list(range(i, i + k)), 1.0, 5))
        i += k
    for s in range(0, n, 40):                             # streets
        foci.append(("street", list(range(s, min(n, s + 40))), 0.08, 50))
    adults = [p["id"] for p in people if 18 <= p["age"] < 65]
    rng.shuffle(adults)
    for w in range(0, len(adults), 15):                   # workplaces of ~15
        foci.append(("work", adults[w:w + 15], 0.35, 15))
    kids = sorted([p["id"] for p in people if p["age"] < 18], key=lambda j: people[j]["age"])
    for c in range(0, len(kids), 20):                     # school classes by age
        foci.append(("class", kids[c:c + 20], 0.3, 15))
    for c in range(8):                                    # clubs / congregations / the pub
        members = [p["id"] for p in people if rng.random() < 0.08 + 0.1 * p["E"]]
        foci.append(("club", members, 0.06, 50))
    edges = {}                                             # (u,v) u<v -> layer

    def sim(a, b):                                         # homophily (McPherson et al. 2001)
        pa, pb = people[a], people[b]
        return math.exp(-abs(pa["age"] - pb["age"]) / 15.0) * (1.2 if pa["occ"] == pb["occ"] else 1.0)

    for kind, members, p_tie, layer in foci:
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                a, b = sorted((members[x], members[y]))
                if kind == "household" or h01(seed, "tie", kind, a, b) < p_tie * sim(a, b):
                    old = edges.get((a, b))
                    edges[(a, b)] = min(old, layer) if old else layer
    # acquaintance layer: a few weak ties across foci (weak ties bridge -- Granovetter 1973)
    for a in range(n):
        for _ in range(8):
            b = int(h01(seed, "weak", a, _) * n)
            if b != a:
                key = tuple(sorted((a, b)))
                edges.setdefault(key, 150)
    adj = defaultdict(list)
    for (a, b), layer in edges.items():
        adj[a].append((b, layer))
        adj[b].append((a, layer))
    return people, adj


# -- one hop: will u tell v, and when ------------------------------------------------------------

def hop(seed, ev, people, u, v, layer, hops_before):
    """-> delay in days if u tells v about ev (the edge is 'live'), else None.  Pure function."""
    salience = ev["weight"] * (HEARSAY ** hops_before)        # hearsay loses interest each hop
    if u == PUBLIC:
        p = min(0.9, max(0.0, ev["weight"] - 0.75) * (0.5 + 0.6 * people[v]["E"]))   # who hears it about
    else:
        pu = people[u]
        gossip = 0.5 + 0.9 * pu["E"] - 0.3 * pu["C"] * pu["H"]      # talkative vs discreet
        p = min(0.97, salience * gossip * LAYER_STRENGTH[layer])
    if h01(seed, "tell", ev["id"], u, v) >= p:
        return None
    return -math.log(1.0 - h01(seed, "delay", ev["id"], u, v)) * LAYER_DAYS[layer]


def neighbours(adj, u, n):
    if u == PUBLIC:
        return [(v, "pub") for v in range(n)]
    return adj[u] + [(PUBLIC, "pub")]


def eager(seed, ev, people, adj):
    """Forward, over everyone: earliest arrival by any path of <= MAX_HOPS live edges."""
    n = len(people)
    seeds = ev["witnesses"] + [PUBLIC]
    best = {w: (0.0, 0, None) for w in seeds}                 # node -> (time, hops, told_by)
    frontier = {w: 0.0 for w in seeds}
    for h in range(MAX_HOPS):                                 # hop-layered relaxation
        nxt = {}
        for u, tu in frontier.items():
            for v, layer in neighbours(adj, u, n):
                if v == PUBLIC:
                    continue                                  # nobody tells the noticeboard
                d = hop(seed, ev, people, u, v, layer, h)
                if d is None:
                    continue
                t = tu + d
                if v not in best or t < best[v][0]:
                    best[v] = (t, h + 1, u)
                    if v not in nxt or t < nxt[v]:
                        nxt[v] = t
        # a node can also relay what it got by a longer-but-faster path at this depth
        frontier = nxt
    return best


def lazy(seed, ev, people, adj, x):
    """Backwards from one person: the earliest time x heard, who told them, over how many hops --
    touching only x's neighbourhood.  -> ((time, hops, told_by) or None, nodes touched)."""
    n = len(people)
    wit = set(ev["witnesses"]) | {PUBLIC}
    if x in wit:
        return (0.0, 0, None), 1
    touched = 1
    # paths ending at x with k hops: search suffixes backwards; hop index from the source is
    # MAX_HOPS-length dependent, so enumerate by total length L = 1..MAX_HOPS
    best = None
    # suffix[node] = (time from node to x along the suffix, first-teller-after-node) for suffixes
    # of length m, where node's hop index = L - m
    for L in range(1, MAX_HOPS + 1):
        suffix = {x: (0.0, None)}
        for m in range(1, L + 1):                         # extend backwards; teller u at index L-m
            nxt = {}
            for v, (tv, _) in suffix.items():
                for u, layer in neighbours(adj, v, n) if v != PUBLIC else []:
                    touched += 1
                    d = hop(seed, ev, people, u, v, layer, L - m)
                    if d is None:
                        continue
                    t = tv + d
                    if u not in nxt or t < nxt[u][0]:
                        nxt[u] = (t, v)
            suffix = nxt
        for w in wit:
            if w in suffix:
                t = suffix[w][0]
                if best is None or t < best[0]:
                    best = (t, L, None)
    return best, touched


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    people, adj = build(seed, n)
    deg = [len(adj[i]) for i in range(n)]
    layers = defaultdict(int)
    for i in range(n):
        for _, l in adj[i]:
            layers[l] += 1
    print("settlement: %d people, mean ties %.1f (layers: %s)" % (
        n, sum(deg) / n, ", ".join("%d:%.1f" % (l, layers[l] / n) for l in sorted(layers))))
    rng = random.Random(seed)
    for weight, name in [(0.35, "minor (a rude word)"), (0.7, "notable (a theft)"), (1.2, "major (a rescue / a fire)")]:
        ev = {"id": "%s-%d" % (name[:5], weight * 100), "weight": weight, "witnesses": rng.sample(range(n), 3)}
        full = eager(seed, ev, people, adj)
        mism = 0
        cost = []
        for x in range(n):
            got, touched = lazy(seed, ev, people, adj, x)
            cost.append(touched)
            e = full.get(x)
            if (got is None) != (e is None) or (got and abs(got[0] - e[0]) > 1e-9):
                mism += 1
        full.pop(PUBLIC, None)
        by_day = [sum(1 for t, _, _ in full.values() if t <= d) / n for d in (1, 3, 7, 30)]
        by_hop = defaultdict(int)
        for t, hp, _ in full.values():
            by_hop[hp] += 1
        print("\n%s: knows within 1/3/7/30 days: %s" % (name, " / ".join("%.0f%%" % (100 * f) for f in by_day)))
        print("  by hops from a witness: %s" % ", ".join("%d:%d" % (k, by_hop[k]) for k in sorted(by_hop)))
        print("  lazy vs eager disagreements: %d of %d; lazy query touches median %d, max %d edges" % (
            mism, n, sorted(cost)[n // 2], max(cost)))


if __name__ == "__main__":
    main()
