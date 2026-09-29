"""Onion skin and filmstrip from frames saved by npc_lineup.gd's `anim` view: the animator's light
table, for judging arcs, spacing and overlap.
  python3 tools/charref/onion.py /tmp/anim.png [every]   (reads /tmp/anim_00.png ...)"""
import sys
from pathlib import Path
from PIL import Image, ImageChops

base = Path(sys.argv[1])
every = int(sys.argv[2]) if len(sys.argv) > 2 else 3
frames = sorted(base.parent.glob(base.stem + "_[0-9][0-9].png"))
imgs = [Image.open(f).convert("RGB") for f in frames[::every]]
w, h = imgs[0].size
# onion: darken-blend every picked frame over the first (the figure is darker than the sky)
onion = imgs[0]
for im in imgs[1:]:
    onion = ImageChops.darker(onion, im)
onion.save(base.with_name(base.stem + "_onion.png"))
# filmstrip: crop round the moving figure (the middle band) and tile
strip = Image.new("RGB", (len(imgs) * w // 4, h // 2))
for i, im in enumerate(imgs):
    strip.paste(im.resize((w // 4, h // 2)), (i * w // 4, 0))
strip.save(base.with_name(base.stem + "_strip.png"))
print(len(frames), "frames;", len(imgs), "used")
