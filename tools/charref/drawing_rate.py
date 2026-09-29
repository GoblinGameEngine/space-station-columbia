"""How Ghibli times drawings: in each key-animation clip, how long each drawing is held (on ones,
twos, threes...).  A frame 'repeats' when it is nearly identical to the one before (mean absolute
difference below a threshold at low resolution); runs of repeats give the hold lengths.
Clips with moving cameras (every frame differs) show as 'ones' and are reported separately.
  python3 tools/charref/drawing_rate.py [kind ...]      kinds: walk_cycle running character_acting fabric
Writes research/animation/data/drawing_rate.json."""
import collections, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SAK = ROOT / "reference" / "ghibli" / "sakuga"
OUT = ROOT / "research" / "animation" / "data" / "drawing_rate.json"
W, H = 96, 54


def frames(path):
    cmd = ["ffmpeg", "-loglevel", "error", "-i", str(path), "-vf", f"scale={W}:{H}", "-pix_fmt", "gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, timeout=300).stdout
    n = len(raw) // (W * H)
    return np.frombuffer(raw[: n * W * H], np.uint8).reshape(n, H, W).astype(np.float32)


def holds(fr, thr=1.2):
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    runs, cur = [], 1
    for x in d:
        if x < thr:
            cur += 1
        else:
            runs.append(cur)
            cur = 1
    runs.append(cur)
    return runs, float(np.median(d))


def main():
    kinds = sys.argv[1:] or ["walk_cycle", "running", "character_acting"]
    idx = json.loads((SAK / "index.json").read_text())
    out = {}
    for kind in kinds:
        agg = collections.Counter()
        per = []
        for pid, v in idx.items():
            if kind not in v["kinds"] or not str(v["file"]).endswith((".mp4", ".webm", ".mov")):
                continue
            try:
                fr = frames(SAK / v["file"])
            except Exception:
                continue
            if len(fr) < 24:
                continue
            runs, med = holds(fr)
            c = collections.Counter(min(r, 6) for r in runs)
            frames_in = {k: k * n for k, n in c.items()}
            tot = sum(frames_in.values())
            share = {k: frames_in[k] / tot for k in frames_in}
            per.append({"clip": pid, "film": v["film"], "share": {str(k): round(s, 3) for k, s in sorted(share.items())}})
            if share.get(1, 0) < 0.8:                  # skip clips that are all ones (pans, camera moves)
                agg.update({k: frames_in[k] for k in frames_in})
        tot = sum(agg.values())
        out[kind] = {"clips": len(per), "frame_share_by_hold": {str(k): round(agg[k] / tot, 3) for k in sorted(agg)} if tot else {},
                     "clips_detail": per}
        print(kind, len(per), "clips; share of screen time by hold length (static-camera clips):", out[kind]["frame_share_by_hold"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
