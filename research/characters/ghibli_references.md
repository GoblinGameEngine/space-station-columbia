# Reference material: what we have locally and where it came from

Everything here lives in `reference/`, which is **gitignored**: it is copyrighted
material kept for study on this machine only, never committed or shipped. The scripts
that fetch and process it are in `tools/charref/` (committed), so the set can be rebuilt on
another machine.

| folder | what | amount | source / tool |
|---|---|---|---|
| `reference/ghibli/stills/` | official production stills, `<film>NNN.jpg`, 1920×1038 | 1,200 (50 × 24 films), 314 MB | Studio Ghibli's own gallery, `https://www.ghibli.jp/gallery/<film>NNN.jpg`. The studio offers these "常識の範囲でご自由にお使いください" ("feel free to use within common sense") |
| `reference/ghibli/sheets/` | contact sheets, 50 stills per film, numbered | 24 | `tools/charref/contact_sheets.py` |
| `reference/ghibli/palette.json`, `palettes/` | measured colour statistics and 16-colour Lab k-means palettes per film, swatch strips | 24 films | `tools/charref/palette.py` |
| `reference/ghibli/video/` | official trailers, 720p, with yt-dlp `.info.json` | 20 films, 186 MB | official studio and distributor channels via yt-dlp |
| `reference/ghibli/frames/<trailer>/` | key frames at scene changes (ffmpeg `select='gt(scene,0.35)'`), 640 px | 908 | the command below |
| `reference/ghibli/sakuga/<film>/` + `index.json` | key-animation clips tagged character_acting, walk_cycle, running, fabric; top-scored, ≤ 30 MB each; index with tags, animator credit, post link | up to 10 per film per kind, 16 films (still downloading at the time of writing) | Sakugabooru API, `tools/charref/sakuga.py` |
| `reference/papers/` | PDFs: Motomura GDC 2015; Petrovic 2000; Sunshine-Hill & Badler 2010; Riedl (alibi); Talk of the Town (GAP3 ch. 37); GAP1 ch. 43; Bates 1994; Crombie 2021 | 8, 18 MB | see `ghibli_scholarship.md` |

Film slugs: aya (Earwig), baron (The Cat Returns), chihiro (Spirited Away), ged (Tales from
Earthsea), howl, kaguyahime, karigurashi (Arrietty), kazetachinu (The Wind Rises), kimitachi
(The Boy and the Heron), kokurikozaka (From Up on Poppy Hill), laputa, majo (Kiki), marnie,
mimi (Whisper of the Heart), mononoke, nausicaa, omoide (Only Yesterday), ponyo, porco,
redturtle, tanuki (Pom Poko), totoro, umi (Ocean Waves), yamada (My Neighbors the Yamadas).
Grave of the Fireflies is not in the studio gallery.

**Rebuild on another machine:**
```
# stills: 50 per film
for f in aya baron chihiro ged howl kaguyahime karigurashi kazetachinu kimitachi kokurikozaka laputa majo \
         marnie mimi mononoke nausicaa omoide ponyo porco redturtle tanuki totoro umi yamada; do
  for i in $(seq -w 1 50); do curl -sf -o reference/ghibli/stills/$f$(printf %03d $((10#$i))).jpg \
    https://www.ghibli.jp/gallery/$f$(printf %03d $((10#$i))).jpg; done; done
python3 tools/charref/contact_sheets.py
python3 tools/charref/palette.py
python3 tools/charref/sakuga.py              # --per N --max-mb M
# trailers: yt-dlp -f 'bv*[height<=720]+ba/b[height<=720]' --write-info-json "ytsearch1:<film> official trailer"
# key frames:
ffmpeg -i trailer.mp4 -vf "select='gt(scene,0.35)',scale=640:-2" -vsync vfr -q:v 3 frames/%03d.jpg
```

## Where to look for what

| need | where |
|---|---|
| ordinary townspeople, working clothes, crowds | majo (Kiki) 003, 009, 014, 017, 022, 029, 031, 045, 049; omoide; kokurikozaka; mimi; chihiro 004 |
| uniforms and role clothing | chihiro 018, 026, 028 (bathhouse); majo 015 (police), 045 (dock/overalls) |
| elders and caricature | chihiro 016–017 (Yubaba); laputa (Dola); majo 031; totoro (Granny) |
| children | totoro, ponyo, majo 016 (Tombo), chihiro 001 |
| body variety | chihiro 004 (father), majo 040 (Ursula), porco |
| faces, close-ups, expression | majo 008, 013, 044; chihiro 021–023, 036, 046 |
| hair in motion | nausicaa, howl, chihiro 036 (underwater), sakuga `fabric` clips |
| walking and running | sakuga `walk_cycle`, `running`; ghibli_style.md §4 |
| colour | `palette.json`; ghibli_style.md §2.2 |
| watercolour / non-cel look | kaguyahime, yamada (outliers in every palette measure) |

Web galleries worth knowing (not downloaded):
- the Studio Ghibli gallery (https://www.ghibli.jp/gallery/), plus the works index
  (https://www.ghibli.jp/works/);
- the Layout Designs exhibition write-ups at halcyonrealms.com (parts I and II), with layout
  drawings including characters.
