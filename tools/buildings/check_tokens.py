#!/usr/bin/env python3
"""check_tokens.py REGION -- validate research/buildings/regions/REGION/tokens/*.json against vocab.json
(research/buildings/TOKENS.md). Reports unknown families/values, malformed facade grids, why-entries pointing at
tokens the file doesn't have."""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GRID = {"W", "Wp", "Wb", "Wd", "D", "G", "S", "E", "T", ".", "C", "|", "P", "N"}   # (TOKENS.md, "The facade grid")


def main():
    region = sys.argv[1] if len(sys.argv) > 1 else "great_lakes"
    V = json.load(open(os.path.join(HERE, "vocab.json")))
    files = sorted(glob.glob(os.path.join(ROOT, "research", "buildings", "regions", region, "tokens", "*.json")))
    bad = 0
    for p in files:
        t = json.load(open(p))
        errs = []
        for tok in t.get("tokens", []):
            fam, _, val = tok.partition(":")
            if fam not in V or fam.startswith("_"):
                errs.append("unknown family %s" % tok)
            elif val not in V[fam]:
                errs.append("unknown value %s" % tok)
        have = set(t.get("tokens", []))
        for w in t.get("why", []):
            if w.get("cause") not in V["cause"]:
                errs.append("unknown cause %s" % w.get("cause"))
            if w.get("token") not in have:
                errs.append("why names a token not in tokens: %s" % w.get("token"))
        for im in t.get("images", []):
            if im.get("view") not in V["view"]:
                errs.append("unknown view %s" % im.get("view"))
            if im.get("file") and not os.path.exists(os.path.join(ROOT, im["file"])):
                errs.append("missing image %s" % im["file"])
        for row in t.get("facade", {}).get("floors", []):
            odd = [b for b in row.split() if b not in GRID]
            if odd:
                errs.append("facade grid has %s" % " ".join(sorted(set(odd))))
        if errs:
            bad += 1
            print(os.path.basename(p))
            for e in errs:
                print("   ", e)
    print("%d files, %d with problems" % (len(files), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
