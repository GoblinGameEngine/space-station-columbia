"""Fetch motion reference from Sakugabooru (key-animation clips) into reference/ghibli/sakuga/<film>/,
with index.json describing each clip (film, motion kinds, tags, animator credit in the source field).
Local reference only -- /reference/ is gitignored.  Resumable: files already there are skipped, and
the index is written after every query.
usage: python3 tools/charref/sakuga.py [--per N] [--max-mb M] [film_tag ...]"""
import argparse, json, os, time, urllib.parse, urllib.request
from pathlib import Path

FILMS = ["spirited_away", "princess_mononoke", "my_neighbor_totoro", "kiki's_delivery_service", "howl's_moving_castle",
         "ponyo", "porco_rosso", "laputa:_castle_in_the_sky", "arrietty", "the_wind_rises",
         "the_tale_of_the_princess_kaguya", "when_marnie_was_there", "the_boy_and_the_heron", "whisper_of_the_heart",
         "only_yesterday", "pom_poko"]
KINDS = ["character_acting", "walk_cycle", "running", "fabric"]
ROOT = Path(__file__).resolve().parents[2] / "reference" / "ghibli" / "sakuga"
UA = {"User-Agent": "Mozilla/5.0 (goblin-engine reference fetch)"}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=10, help="best-scored clips per film and kind")
    ap.add_argument("--max-mb", type=float, default=30)
    ap.add_argument("films", nargs="*")
    a = ap.parse_args()
    ipath = ROOT / "index.json"
    index = json.loads(ipath.read_text()) if ipath.exists() else {}
    for film in a.films or FILMS:
        d = ROOT / film.replace(":", "").replace("'", "")
        d.mkdir(parents=True, exist_ok=True)
        for kind in KINDS:
            try:
                posts = json.loads(get("https://www.sakugabooru.com/post.json?limit=100&tags="
                                       + urllib.parse.quote(f"{film} {kind} order:score")))
            except Exception as e:
                print("ERR", film, kind, e, flush=True)
                continue
            got = 0
            for p in posts:
                if got >= a.per:
                    break
                pid, url = str(p["id"]), p.get("file_url")
                if not url or (p.get("file_size") or 0) > a.max_mb * 1e6:
                    continue
                got += 1
                if pid in index:
                    if kind not in index[pid]["kinds"]:
                        index[pid]["kinds"].append(kind)
                    continue
                path = d / f"{pid}.{url.rsplit('.', 1)[-1]}"
                if not path.exists():
                    try:
                        data = get(url)
                        path.write_bytes(data)
                        time.sleep(0.5)
                    except Exception as e:
                        print("ERR dl", pid, e, flush=True)
                        continue
                index[pid] = {"film": film, "kinds": [kind], "tags": p.get("tags"), "source": p.get("source"),
                              "score": p.get("score"), "file": str(path.relative_to(ROOT)),
                              "post": f"https://www.sakugabooru.com/post/show/{pid}"}
            ipath.write_text(json.dumps(index, indent=1))
            print(film, kind, f"{got} of {len(posts)}", flush=True)
    print("clips", len(index))


if __name__ == "__main__":
    main()
