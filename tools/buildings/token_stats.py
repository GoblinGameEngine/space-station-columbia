#!/usr/bin/env python3
"""token_stats.py REGION [FAMILY_A FAMILY_B] -- counts every token family in a region's corpus, or cross-tabulates
two families (e.g. form band, roof form, door_pos form). The tables are the generator's probabilities
(research/buildings/TOKENS.md)."""
import collections, glob, json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def load(region):
    for p in sorted(glob.glob(os.path.join(ROOT, "research", "buildings", "regions", region, "tokens", "*.json"))):
        t = json.load(open(p))
        fams = collections.defaultdict(list)
        for k in ("band", "transect", "state"):              # (the place block's fields count as tokens too)
            if t.get("place", {}).get(k):
                fams[k].append(t["place"][k])
        for tok in t.get("tokens", []):
            f, _, v = tok.partition(":")
            fams[f].append(v)
        yield t, fams


def main():
    region = sys.argv[1] if len(sys.argv) > 1 else "great_lakes"
    rows = list(load(region))
    print("%d buildings" % len(rows))
    if len(sys.argv) >= 4:
        a, b = sys.argv[2], sys.argv[3]
        tab = collections.Counter()
        for _, f in rows:
            for x in f.get(a, ["-"]):
                for y in f.get(b, ["-"]):
                    tab[(x, y)] += 1
        for (x, y), n in sorted(tab.items(), key=lambda kv: (kv[0][0], -kv[1])):
            print("%-26s %-26s %d" % (x, y, n))
        return
    allc = collections.defaultdict(collections.Counter)
    for _, f in rows:
        for fam, vals in f.items():
            for v in vals:
                allc[fam][v] += 1
    for fam in sorted(allc):
        print("%-20s %s" % (fam, ", ".join("%s %d" % kv for kv in allc[fam].most_common())))


if __name__ == "__main__":
    main()
