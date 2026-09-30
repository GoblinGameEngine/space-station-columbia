#!/usr/bin/env python3
"""Prototype: informal roles emerge from traits + network position, and a settlement's cohesion
depends on whether its critical informal roles are filled (research/roles/05_roles_in_the_engine.md).

Johnson, Boster & Palinkas (2003): coherent (core-periphery) crews had consensus that critical
informal roles were filled -- expressive leadership above all; factionalised crews lacked it,
above all the instrumental leader. Johnson: crews need leaders, clowns, peacemakers, counsellors,
storytellers. Palinkas: clique crews had worse mood than core-periphery crews.

For several generated settlements this script: builds the social graph from foci
(propagation_proto), finds groups (deterministic label propagation), computes each person's
emergent roles from tokens + position, checks the critical roles, and derives W.cohesion and the
settlement's clique structure -- the mechanic the engine will use (and the vacancies the player
can fill).

    python3 tools/story/roles_proto.py [seed] [settlements]
"""
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import propagation_proto as pp  # noqa: E402

CRITICAL = ["leader_task", "leader_heart", "clown", "peacemaker", "confidant"]


def groups(adj, n, seed):
    """Deterministic label propagation over social ties (work, neighbours, clubs: layers 15/50 --
    households excluded, or every 'group' is just a family): the settlement's cliques."""
    lab = list(range(n))
    order = sorted(range(n), key=lambda i: pp.h01(seed, "lp", i))
    for _ in range(12):
        changed = 0
        for i in order:
            c = Counter()
            for v, l in adj[i]:
                if l in (15, 50):
                    c[lab[v]] += pp.LAYER_STRENGTH[l]
            if c:
                best = max(c.items(), key=lambda kv: (kv[1], -kv[0]))[0]
                if best != lab[i]:
                    lab[i] = best
                    changed += 1
        if not changed:
            break
    return lab


def run(seed, n=300):
    rng = random.Random(seed)
    people, adj = pp.build(seed, n)
    for p in people:
        p["humour"] = rng.betavariate(4, 4)
        p["agency"] = 0.5 * rng.betavariate(4, 4) + 0.5 * p["E"]
        p["communion"] = 0.5 * p["A"] + 0.5 * rng.betavariate(4, 4)
    lab = groups(adj, n, seed)
    size = Counter(lab)
    big = set(g for g, s in size.items() if s >= 8)
    deg = [len([1 for _, l in adj[i] if l != 150]) for i in range(n)]
    span = [len({lab[v] for v, l in adj[i] if lab[v] in big and l != 5} | ({lab[i]} if lab[i] in big else set())) for i in range(n)]
    adults = [i for i in range(n) if people[i]["age"] >= 18]
    roles = defaultdict(list)

    def top(score, rid, k=1, floor=0.0, margin=0.03):
        ranked = sorted(adults, key=lambda i: -score(i))
        if not ranked or score(ranked[0]) < floor:
            return
        # consensus: the best clearly stands out (Johnson: agreement that the role is filled)
        if len(ranked) > 1 and score(ranked[0]) < score(ranked[1]) * (1 + margin):
            roles["contested:" + rid].append(ranked[0])
            return
        for i in ranked[:k]:
            roles[rid].append(i)

    md = max(deg) or 1
    top(lambda i: people[i]["agency"] * people[i]["C"] * (0.4 + deg[i] / md), "leader_task", floor=0.12)
    top(lambda i: people[i]["communion"] * people[i]["A"] * (0.4 + deg[i] / md), "leader_heart", floor=0.12)
    top(lambda i: people[i]["humour"] * people[i]["E"] * span[i], "clown", floor=0.9)
    top(lambda i: people[i]["A"] * people[i]["H"] * span[i], "peacemaker", floor=0.9)
    top(lambda i: people[i]["A"] * (1 - (0.5 + 0.9 * people[i]["E"] - 0.3 * people[i]["C"] * people[i]["H"]) / 1.4) * (0.4 + deg[i] / md), "confidant", floor=0.08)
    cut = sorted(span[i] for i in adults)[int(0.95 * len(adults))]     # brokers: the top 5% by groups spanned
    for i in adults:
        if span[i] >= max(3, cut):
            roles["broker"].append(i)
        if deg[i] <= 1:
            roles["loner"].append(i)
        if (0.5 + 0.9 * people[i]["E"] - 0.3 * people[i]["C"] * people[i]["H"]) > 1.15 and deg[i] >= 6:
            roles["gossip"].append(i)
    filled = [r for r in CRITICAL if roles.get(r)]
    vacant = [r for r in CRITICAL if not roles.get(r)]
    cohesion = len(filled) / len(CRITICAL)
    # structure: share of strong ties that cross groups (low = cliquish), and the largest group's share
    cross = sum(1 for i in range(n) for v, l in adj[i] if l in (15, 50) and lab[v] != lab[i]) / max(1, sum(1 for i in range(n) for _, l in adj[i] if l in (15, 50)))
    core = max(size.values()) / n
    sizes = sorted((s for g, s in size.items() if g in big), reverse=True)
    return dict(seed=seed, sizes=sizes, groups=len(big), core=core, cross=cross, filled=filled, vacant=vacant,
                contested=[k.split(":")[1] for k in roles if k.startswith("contested:")], cohesion=cohesion,
                brokers=len(roles["broker"]), loners=len(roles["loner"]), gossips=len(roles["gossip"]))


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    print("settlement  groups(sizes)            cross-ties  cohesion  vacant critical roles (contested)")
    rows = [run(seed * 100 + s) for s in range(k)]
    for r in rows:
        print("  %5d      %-24s  %3.0f%%      %.1f     %s%s   brokers %d loners %d gossips %d" % (
            r["seed"], "%d %s" % (r["groups"], r["sizes"][:5]), 100 * r["cross"], r["cohesion"], ", ".join(r["vacant"]) or "none",
            (" (contested: %s)" % ", ".join(r["contested"])) if r["contested"] else "", r["brokers"], r["loners"], r["gossips"]))
    print("\nThe engine: W.cohesion = share of critical informal roles filled by consensus. Low cohesion ->"
          "\ncliques around leisure places, more stress (Palinkas), feud/rivalry arcs favoured; each vacant or"
          "\ncontested role is a story hook the player can fill (be the clown, the peacemaker, the one who leads).")


if __name__ == "__main__":
    main()
