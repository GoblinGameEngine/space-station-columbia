#!/usr/bin/env python3
"""fetch_corpus.py REGION [--list] -- collect a region's reference photos from curated Wikimedia Commons categories
(research/buildings/regions/REGION/corpus.json) into remake/reference/corpus_REGION_<bucket>/, each with its
sources.json (licence, author, caption) via remake/tools/refs.py. Deterministic: the same seed picks the same files.
--list prints what it would take without downloading. Method: research/buildings/METHOD.md."""
import hashlib, json, os, sys, urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "remake", "tools"))
import refs  # noqa: E402

API = "https://commons.wikimedia.org/w/api.php"
OK = ("public domain", "cc0", "cc by", "cc-by", "pd")


def members(cat, depth=1):
    out, cont = [], {}
    while True:
        p = {"action": "query", "format": "json", "list": "categorymembers", "cmtitle": cat, "cmlimit": "200",
             "cmtype": "file|subcat"}
        p.update(cont)
        d = refs.get(API + "?" + urllib.parse.urlencode(p))
        for m in d.get("query", {}).get("categorymembers", []):
            if m["ns"] == 6 and m["title"].lower().endswith((".jpg", ".jpeg")):
                out.append(m["title"])
            elif m["ns"] == 14 and depth > 0:
                out += members(m["title"], depth - 1)
        if "continue" not in d:
            return out
        cont = {"cmcontinue": d["continue"]["cmcontinue"]}


def licence(title):
    p = {"action": "query", "format": "json", "titles": title, "prop": "imageinfo", "iiprop": "extmetadata"}
    d = refs.get(API + "?" + urllib.parse.urlencode(p))
    pg = next(iter(d["query"]["pages"].values()))
    md = (pg.get("imageinfo") or [{}])[0].get("extmetadata", {})
    return md.get("LicenseShortName", {}).get("value", "")


def main():
    region = sys.argv[1] if len(sys.argv) > 1 else "great_lakes"
    dry = "--list" in sys.argv
    only = {a for a in sys.argv[2:] if not a.startswith("-")}          # (bucket names: just these)
    C = json.load(open(os.path.join(ROOT, "research", "buildings", "regions", region, "corpus.json")))
    refs.MAX_W = C.get("max_w", 1280)
    for B in C["buckets"]:
        if only and B["bucket"] not in only:
            continue
        pool = []
        if B.get("search"):                               # (a search bucket: files at seeded random offsets of the hits)
            import random
            rng = random.Random("%d:%s" % (C["seed"], B["bucket"]))
            tot = refs.get(API + "?" + urllib.parse.urlencode({"action": "query", "format": "json", "list": "search",
                           "srsearch": B["search"], "srnamespace": "6", "srlimit": "1"}))["query"]["searchinfo"]["totalhits"]
            for off in sorted(rng.sample(range(0, min(tot, 9900)), B["n"] * 2)):
                d = refs.get(API + "?" + urllib.parse.urlencode({"action": "query", "format": "json", "list": "search",
                             "srsearch": B["search"], "srnamespace": "6", "srlimit": "1", "sroffset": str(off)}))
                pool += [r["title"] for r in d["query"]["search"] if r["title"].lower().endswith((".jpg", ".jpeg"))]
        for cat in B.get("cats", []):
            try:
                pool += members(cat)
            except Exception as e:                # (a missing category is skipped, not fatal)
                print("  skip", cat, e)
        pool = sorted(set(pool), key=lambda t: hashlib.sha1(("%d:%s" % (C["seed"], t)).encode()).hexdigest())
        sid = "corpus_%s_%s" % (region, B["bucket"])
        got = 0
        for t in pool:
            if got >= B["n"]:
                break
            lic = licence(t)
            if not lic.lower().startswith(OK):
                continue
            print("  %-16s %-14s %s" % (B["bucket"], lic, t))
            if not dry:
                try:
                    refs.commons_fetch(t, sid)
                except Exception as e:
                    print("    failed", e)
                    continue
            got += 1
        print("%s: %d of %d (pool %d)" % (B["bucket"], got, B["n"], len(pool)))


if __name__ == "__main__":
    main()
