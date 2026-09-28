# Loading time (2026-09-25)

## Measured, before and after
Timeline marks from RemakeStation (`LOAD ...` lines), on the Steam Deck, dev build:

| Piece | Before | After | What changed |
|---|---|---|---|
| Roads (ribbons, curbs, shoulders, markings) | 73 s | 0.9 s | baked |
| Terrain, all tiers | 35 s | 7.9 s | far tier baked; near tiles on workers |
| Structures (LOD chain, merged districts) | 29 s | 6.5 s | merged LOD2/LOD3 cells and size classes baked; LOD2/3 files loaded for landmarks only |
| Walks (boardwalks, piers...) | 10 s | 0.5 s | baked |
| Trees | 8 s | 0.5 s | baked as MultiMesh buffers (one array per cell, no per-tree calls) |
| Small water (main thread) | 1.9 s | 0.05 s | baked |
| Terrain setup (main thread) | 1.7 s | 0.5 s | only the tile underfoot is built before the first frame |
| **Launch to fully loaded** | **~80 s** | **12.0 s** (exported: **10.8 s**) | |

## How
Everything above was deterministic work redone at every launch, much of it GDScript running per
vertex or per tree. The standard remedy is to do it once, offline, and save the result as binary
resources:
- `remake/tools/bake_world.gd` writes `res://remake/baked/*.res`, about 57 MB in total, compressed.
- Each file is a `BakedMeshes` resource (`scripts/world/BakedMeshes.gd`) stamped with the MD5 of every
  file its builder reads, plus a builder version.
- A builder uses its bake only while the stamp matches. Otherwise it warns and builds live, so a stale
  bake can never be shown.
- Save the mesh *resources*, not scene nodes holding procedural meshes: Godot issue #91385 crashes on
  the latter.

While the loading screen is up:
- `StationGeo.loading` is true, and the builders that spread work over frames to keep the game smooth
  may take 60 ms frames.
- 3D rendering is switched off behind the splash (`Viewport.disable_3d`), so the GPU isn't drawing
  what nobody sees.
- The splash stays up until everything is in, at most 90 s.

**Rerun the bakes after any change to the map, road furniture, placement or walks:**
```
godot4 --headless --path . --script res://remake/tools/bake_world.gd -- roads terrain trees walks water
godot4 --path . --script res://remake/tools/bake_world.gd -- structures
```
The structures bake needs the real renderer: the headless dummy renderer keeps no mesh data.
Rerun the far-side bake after that, as before.

Stamps only name files the export carries as they are (JSON, `.bin.gz`). `landcover.png` isn't one of them: it is regenerated together with `terrain.json` and the height rasters, which the stamps already cover.

## Further options, by expected value
1. **Godot 4.4+.** Done 2026-09-28: 4.7.2 (4.5.2 and 4.6.3 crash on concurrent threaded and main-thread loads). Ubershaders and pipeline precompilation remove the shader-compile
   hitches (our worst frame is still ~150 ms, the first time things are drawn). Pipelines can
   precompile while the loading screen is up. 4.5 also brings general performance work. It's an
   engine upgrade, so test everything after it.
2. **Near terrain tiles (T0/T1, ~0.4 s of GDScript each).** Bake T1 for the whole ring (8 m grid,
   ~40 MB), or port `_gen` and `MapTerrain.elevation` to a GDExtension (C++). The latter makes every
   height query ~20–50× faster: streaming, cars and trees would all benefit.
3. **Structures (6.5 s).** 1,679 LOD1 scenes are loaded and instantiated one by one. Packing them
   into per-district scenes (one file and one instance per district, not per building) would cut
   files and nodes.
4. **Ground vehicles and aerostats (4 s and 3 s).** Instantiate the parked ones lazily near the
   player, like the building detail streamer, instead of all at once.
5. **Draw calls (1,500–2,700 in towns).** The roads are ~6,000 meshes in 100 m cells for fine
   detail. Merging each cell's paint, kerb and shoulder into one multi-surface mesh would drop
   nodes and calls.

## Sources
- Godot docs, Reducing stutter from shader (pipeline) compilations (4.5):
  https://docs.godotengine.org/en/4.5/tutorials/performance/pipeline_compilations.html
- Ubershaders and pipeline pre-compilation, PR #90400: https://github.com/godotengine/godot/pull/90400
- Godot rendering priorities, September 2024: https://godotengine.org/article/rendering-priorities-september-2024/
- Saving procedural MeshInstance3D crashes, issue #91385: https://github.com/godotengine/godot/issues/91385
- ResourceSaver (4.4): https://docs.godotengine.org/en/4.4/classes/class_resourcesaver.html
