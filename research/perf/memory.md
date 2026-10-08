# Memory footprint (2026-10-08)

The 1:1 station has 64,000 structures, 218,000 residents, 135,000 vehicles and 1.5 M road points. Before band
streaming it ran out of memory on the Steam Deck, at about 11 GB. The aim here was the smallest footprint that still
looks the same where you stand. Nothing that can't be seen is kept, and what is kept is packed.

## Measured
The footprint is measured in Solana Point (s 35470, x 5440) after settling. Both columns are system-wide:
- **RSS** is the process's resident memory.
- **GPU** is the driver's VRAM plus GTT, minus the no-game baseline of 598 MB VRAM and 309 MB GTT.
- Godot's own monitors cannot be trusted for the GPU. Vulkan (VMA) memory blocks are not given back once they are
  freed, so the driver's numbers (`/sys/class/drm/card0/device/mem_info_*`) are the real ones.

| | RSS | GPU | Total |
|---|---|---|---|
| Before (morning, after band streaming) | 7.6 GB | ~2.9 GB | ~10.5 GB |
| Columns, bands, 512 px textures | 2.9 GB | ~3.0 GB | 5.9 GB |
| + fine road detail in tiles | 2.8 GB | 2.3 GB | 5.1 GB |
| + packed terrain index, pads, rasters, paths, fleet; vehicle records | 2.77 GB | 2.0 GB | 4.8 GB |
| + LOD2 cells in tiles, sign tiles | 2.87 GB | 2.0 GB | 4.9 GB |
| + malloc tuning (native/memtune) | **1.93 GB** | **2.0 GB** | **3.9 GB** |

At load complete (spawn, before the city) the game was 2.0 GB RSS; now it is 1.5 GB. "Fully loaded" went from 61 s
to 52 s, because the bicycles step took 6.1 s and now takes 0.2 s.

## What was found, and what was done

### 1. Drawn to 300–1,000 m, but kept for a strip 3.4 km by 22 km
Bands of the ring are 2.4 km of s by the whole 22 km width of x. They were right for the coarse meshes and wrong
for everything that fades out near the player.

| Kind | Drawn to | Held before | Fix |
|---|---|---|---|
| Kerbs, sidewalks, paint, decals, shoulders | 320–1,000 m | 730 MB of 820 MB of road buffers | `MapRoads.split_band`: 1.2 km tiles a file, within 1,150 m (`remake/baked/roads_f/`) |
| Structure LOD2 cells | ~600 m (LOD3 past D3) | 162 MB | `RemakeLodClusters.split_band`: 600 m tiles, within 1 km (`remake/baked/structures_t/`) |
| Sign posts and faces | 420 m | 91 MB | `RoadFurniture`: 800 m tiles built within 700 m |

The far-side bake turns these on everywhere for the bands it has in (`MapRoads.fine_everywhere`, `bake_mode`).

### 2. Data as Variants
GDScript Arrays and Dictionaries cost about 24 bytes per element plus the container. That cost is the same whatever
the element holds, whether a float, a small array or a string.
- Terrain grid: 968k `[kind, i, k0, k1]` Arrays became a PackedInt32Array per cell, decoded on demand into a
  two-generation cache (`MapTerrain._items`).
- Water level and depth rasters: 88 MB of halves became 32×32 tiles kept only where they are not uniform
  (`_sparse` / `_sv`, 10 MB). Parity was checked on 400k samples.
- Pads: 64k Arrays plus an id dictionary became a flat PackedFloat64Array plus heights indexed by placement.
- Land cover: RGB8 became RG8, saving 22 MB of CPU memory and about 44 MB as a texture.
- Walking network (`npc_paths.json`, 117 MB and 7 s): packed columns, CSR adjacency and a baked edge grid now live in
  `npc_paths.bin` (52 MB, 0.26 s). It was checked identical on 600 routes and 200 door attachments.
  - The float32 road parameters changed a route by one point, so the parameters stay float64.
- Fleet (`npc_fleet.json`, 135k vehicles, parsed again at every launch): `npc_fleet.bin` stores interned type, kind and
  place.
- Parked vehicles (`VehicleStreamer`): one Dictionary per record became packed records on a 100 m grid. Ground height
  is found only when a vehicle is built. 22k bicycles: 6.1 s to 0.2 s.
  - The old 40-records-a-frame slice took 9 s to reach a bike near a player who had just arrived.

Gotcha: `dict.column.append(x)` on a packed array held in a Dictionary copies the array on every append. The fleet
bake took 124 s with it; it now takes 2.6 s with local arrays.

### 3. The allocator kept what was freed
In a city, RSS was 1.4 GB over Godot's static memory. Of that, 1.15 GB sat in 19 malloc arenas (one per worker
thread), and the rest was big freed blocks inside the heap. glibc's dynamic mmap threshold climbs to 32 MB after the
first frees, so later big buffers come from the heap and their holes are never returned.

`native/memtune` is a GDExtension of 40 lines of C with no Godot headers. It calls `mallopt` as the engine loads it:
- `M_ARENA_MAX 2`
- `M_MMAP_THRESHOLD 256 KB` (fixed; this also turns off the dynamic threshold)
- `M_TRIM_THRESHOLD 8 MB`

The result is the same static memory with 800 MB less RSS and an unchanged frame rate (80–90 fps). It is built with
`zig cc`, from `pip install ziglang` in ~/.venvs/ssc-assets, for x86_64 and arm64. Windows builds leave it out.

### 4. Textures
- The 690 `remake/textures` imports were capped at 512 px (`process/size_limit`). Godot's texture monitor went from
  570 to 430 MB.
- The rest is mostly render targets and shadow maps: two 4096² depth maps at about 64 MB each.

## Still open (biggest first)
- **GTT about 1.7 GB against Godot's 1.34 GB.** That gap is VMA blocks and driver overhead.
- **LOD3 is about 350 vertices a building.** It is 117 MB for the strip, most of it kilometres away along the axis.
  - A "LOD4" of one box per building, or an octahedral impostor per building type, past about 2.5 km would be about
    5–10 MB.
  - Research: Insomniac's IG-Impostor and distant-city LODs; the Godot octahedral impostor plugins.
- **Interiors:** fake them with an interior-mapping shader on LOD1 windows, so that full interiors only ever load when
  you go in.
- **Static memory, 1.35 GB in a city:**
  - place index units: 34 MB of unit dictionaries
  - the people shards (two at a time)
  - LOD1 and LOD0 PackedScenes with their colliders
- **Shadow maps:** the directional map at 2048 would save about 48 MB, at some cost in quality.

## How to measure
- `RemakeStation.mem_line()` prints static, Godot VRAM and RSS at each `LOAD` mark.
- The scratchpad `sysmem.sh` gives RSS plus driver VRAM and GTT.
- For a per-system mesh inventory, walk the scene's MeshInstance3D and MultiMeshInstance3D nodes, deduplicated by
  mesh RID, summing vertices × 32 + indices × 4. That is how the roads were found.
- `/proc/<pid>/smaps` with 64 MB anonymous mappings shows the malloc arenas.
