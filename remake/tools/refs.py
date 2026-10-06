#!/usr/bin/env python3
"""
refs.py -- reference-photo research tool for the clean-sheet building remake.

Sources (both chosen because their reuse terms are clear):
  * Library of Congress HABS/HAER/HALS -- US-government survey records of real
    American buildings/bridges: photographs, *measured drawings* (plans,
    elevations, sections) and a written data report.  Public domain.
  * Wikimedia Commons -- everything HABS doesn't cover (post-1950 commercial,
    small-town streetscapes).  Each file's license/author is recorded.

Every download lands in remake/reference/<STRUCTURE-ID>/ with a sources.json
manifest (url, license, author, caption) so attribution travels with the file.

  refs.py loc-search "grain elevator" [--state illinois] [-n 20]
  refs.py loc-fetch ITEM_ID STRUCTURE_ID            # e.g. il0569 P-008
  refs.py commons-search "Wyoming Illinois depot" [-n 20]
  refs.py commons-fetch "File:Foo.jpg" STRUCTURE_ID
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REF = os.path.join(ROOT, "reference")
UA = "GoblinEngineRemake/0.1 (reference research; contact via github.com/GoblinGameEngine)"
LOC_COLL = "https://www.loc.gov/collections/historic-american-buildings-landscapes-and-engineering-records/"
MAX_W = 1920          # a standard Wikimedia thumbnail width (others are rendered on demand and rate-limited)


_last = [0.0]


def get(url, binary=False, tries=4):
    if "wikimedia.org" in url:
        # Wikimedia asks automated clients to stay slow; they 429 bursts
        wait = 3.0 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except Exception as e:  # noqa: BLE001 -- network flakiness, retry then give up
            if k == tries - 1:
                raise
            # (Wikimedia's 429 "too many requests": back off a minute or more, not seconds)
            time.sleep((60 + 60 * k) if "429" in str(e) else (5 + 10 * k))


def manifest_add(sid, entry):
    d = os.path.join(REF, sid)
    os.makedirs(d, exist_ok=True)
    mp = os.path.join(d, "sources.json")
    m = json.load(open(mp)) if os.path.exists(mp) else {"structure": sid, "files": []}
    m["files"] = [f for f in m["files"] if f["file"] != entry["file"]] + [entry]
    json.dump(m, open(mp, "w"), indent=1)


# ------------------------------------------------------------------ Library of Congress
def loc_search(q, state=None, n=20):
    params = {"q": q, "fo": "json", "c": str(n), "at": "results,pagination"}
    if state:
        params["q"] = f"{q} {state}"
    d = get(LOC_COLL + "?" + urllib.parse.urlencode(params))
    out = []
    for r in d.get("results", []):
        m = re.search(r"/item/([a-z0-9]+)/", r.get("url", ""))
        out.append({"id": m.group(1) if m else r.get("url"), "title": r.get("title"),
                    "date": r.get("date"), "url": r.get("url")})
    return d.get("pagination", {}).get("of", 0), out


def loc_fetch(item, sid):
    d = get(f"https://www.loc.gov/item/{item}/?fo=json")
    it = d["item"]
    dest = os.path.join(REF, sid)
    os.makedirs(dest, exist_ok=True)
    json.dump({"title": it.get("title"), "notes": it.get("notes"), "date": it.get("date"),
               "location": it.get("location"), "url": f"https://www.loc.gov/item/{item}/",
               "rights": it.get("rights_advisory")},
              open(os.path.join(dest, f"loc_{item}_record.json"), "w"), indent=1)
    got = 0
    for res in d.get("resources", []):
        for group in res.get("files", []):
            pdfs = [f for f in group if f.get("mimetype") == "application/pdf"]
            jpgs = [f for f in group if "jpeg" in (f.get("mimetype") or "") or "jpg" in (f.get("mimetype") or "")]
            tifs = [f for f in group if f.get("mimetype") == "image/tiff"]
            is_sheet = any("/sheet/" in (f.get("url") or "") for f in group)
            pick = None
            if is_sheet and tifs:
                # measured drawings: the bilevel TIFF master is small (<1MB) and ~10k px --
                # the 1024px JPEG is too coarse to read dimensions off
                pick = tifs[0]
            elif jpgs:
                ok = [f for f in jpgs if (f.get("width") or 0) <= MAX_W]
                pick = max(ok or jpgs, key=lambda f: f.get("width") or 0)
            elif pdfs:
                pick = pdfs[0]
            if not pick:
                continue
            url = pick["url"]
            m = re.search(r"/(photos|sheet|data|color|photo)/([^/]+)$", url)
            kind = m.group(1) if m else "file"
            name = f"loc_{item}_{kind}_{os.path.basename(url)}"
            if name.endswith(".tif"):
                name = name[:-4] + ".png"
            path = os.path.join(dest, name)
            if not os.path.exists(path):
                data = get(url, binary=True)
                if url.endswith(".tif"):
                    import io
                    from PIL import Image
                    im = Image.open(io.BytesIO(data)).convert("L")
                    im.thumbnail((4000, 4000), Image.LANCZOS)
                    im.save(path, optimize=True)
                else:
                    open(path, "wb").write(data)
                time.sleep(0.4)
            got += 1
            manifest_add(sid, {"file": name, "source": "Library of Congress HABS/HAER",
                               "record": f"https://www.loc.gov/item/{item}/", "url": url,
                               "title": it.get("title"), "kind": "drawing" if kind == "sheet" else kind,
                               "license": "Public domain (US government work; no known restrictions)"})
    return it.get("title"), got


# ------------------------------------------------------------------ Wikimedia Commons
API = "https://commons.wikimedia.org/w/api.php"


def commons_search(q, n=20):
    p = {"action": "query", "format": "json", "generator": "search", "gsrsearch": q, "gsrnamespace": "6",
         "gsrlimit": str(n), "prop": "imageinfo", "iiprop": "url|size|extmetadata"}
    d = get(API + "?" + urllib.parse.urlencode(p))
    out = []
    for pg in sorted(d.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0)):
        ii = (pg.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        out.append({"title": pg["title"], "w": ii.get("width"), "h": ii.get("height"),
                    "license": md.get("LicenseShortName", {}).get("value"),
                    "desc": re.sub("<[^>]+>", "", md.get("ImageDescription", {}).get("value", ""))[:160]})
    return out


def commons_fetch(title, sid):
    p = {"action": "query", "format": "json", "titles": title, "prop": "imageinfo",
         "iiprop": "url|size|extmetadata", "iiurlwidth": str(MAX_W)}
    d = get(API + "?" + urllib.parse.urlencode(p))
    pg = next(iter(d["query"]["pages"].values()))
    ii = pg["imageinfo"][0]
    md = ii.get("extmetadata", {})
    url = ii.get("thumburl") or ii["url"]
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", title.replace("File:", ""))
    name = "commons_" + base
    if url.lower().endswith((".jpg", ".jpeg")) and not name.lower().endswith((".jpg", ".jpeg")):
        name = os.path.splitext(name)[0] + ".jpg"      # thumbnails of TIFF/PDF come back as JPEG
    dest = os.path.join(REF, sid)
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, name)
    if not os.path.exists(path):
        data = get(url, binary=True)          # fetch first: a failed download must not leave a 0-byte file
        with open(path, "wb") as f:
            f.write(data)
    manifest_add(sid, {"file": name, "source": "Wikimedia Commons", "record": ii.get("descriptionurl"),
                       "url": url, "title": title, "kind": "photo",
                       "license": md.get("LicenseShortName", {}).get("value"),
                       "author": re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "")),
                       "caption": re.sub("<[^>]+>", "", md.get("ImageDescription", {}).get("value", ""))[:500]})
    return name


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("loc-search"); a.add_argument("q"); a.add_argument("--state"); a.add_argument("-n", type=int, default=20)
    a = sub.add_parser("loc-fetch"); a.add_argument("item"); a.add_argument("sid")
    a = sub.add_parser("commons-search"); a.add_argument("q"); a.add_argument("-n", type=int, default=20)
    a = sub.add_parser("commons-fetch"); a.add_argument("title"); a.add_argument("sid")
    args = ap.parse_args()
    if args.cmd == "loc-search":
        total, rs = loc_search(args.q, args.state, args.n)
        print(f"{total} results")
        for r in rs:
            print(f"  {r['id']:10s} {r['title'][:120]}")
    elif args.cmd == "loc-fetch":
        title, n = loc_fetch(args.item, args.sid)
        print(f"{args.sid}: {n} files from {title}")
    elif args.cmd == "commons-search":
        for r in commons_search(args.q, args.n):
            print(f"  [{r['license']}] {r['w']}x{r['h']} {r['title']}  -- {r['desc'][:90]}")
    elif args.cmd == "commons-fetch":
        print(commons_fetch(args.title, args.sid))


if __name__ == "__main__":
    sys.exit(main())
